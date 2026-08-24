#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — context-workstream (read verb, pkit ADR-050).

The pm-provided half of the report-context seam: resolve the **current
workstream** from the current branch — `<type>/<N>-<slug>` → issue #N → its
`workstream:*` label (via the ADR-026 axis-label read seam) — and print the
**bare value** (e.g. `cli`) on stdout, or nothing when it cannot be derived.

Invoked by the backbone's report compose **by subprocess through the
capability-command dispatcher** (COR-021), which is exactly why this verb
exists: workstream is pm vocabulary, and the backbone never reads
`workstreams.yaml` or issue labels itself (ADR-050's layering rule). The
caller treats empty output as "omit workstream", so this script **exits 0 on
every miss** and degrades to silence: branch not issue-shaped, capability root
not found, `gh` unavailable/failing, issue unlabelled, or a board-substrate
adopter with no `workstream:*` label. Diagnostics go to stderr only; stdout
carries at most the one value.

One case is NOT a silent miss: an **un-bootstrapped project** is refused (exit
2) by the prerequisite gate every non-exempt pm verb calls (#747). A workstream
read off assumed kit labels would misreport an adopter who remapped them — a
confidently wrong answer, worse than none. stdout stays empty, so the
backbone's consumer (which treats any non-zero exit as "no workstream") sees
the same degrade it always did.

Deliberately **not** membership-gated (unlike `show-issue`): it is a passive
read-only context accessor over the invoker's own branch, and a refusal there
would turn context enrichment into a gate. The prerequisite gate is a different
question — "may this project be operated on at all?" — and applies here as it
does everywhere else.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/context-workstream.py

Or via the dispatcher (per COR-021):
  pkit project-management context-workstream

Exit codes:
  0  the value, or nothing (every derivation miss degrades to silence)
  2  prerequisites unmet (the #747 gate); nothing on stdout
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels, bootstrap_gate  # noqa: E402
from _lib.gh import gh_get_issue, load_adopter_config  # noqa: E402
from _lib.membership import CAPABILITY_NAME, resolve_capability_root  # noqa: E402

#: The issue number embedded in a `<type>/<N>-<slug>` branch name — the same
#: derivation `open-pr` uses on its closing-issue path (DEC-013).
_BRANCH_ISSUE_RE = re.compile(r"^[a-z]+/(\d+)-")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Print the current workstream (branch -> issue -> workstream "
            "label), or nothing when it cannot be derived. Read-only; exits 0 "
            "on every derivation miss, 2 when prerequisites are unmet."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            f"(default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/)."
        ),
    )
    args = parser.parse_args()

    # Resolve the capability root FIRST — before the branch read — so the
    # prerequisite gate below judges the tree this invocation actually targets
    # (`--capability-root` may point elsewhere) rather than one walked up from
    # the cwd. An unresolvable root keeps the documented silence: with no
    # capability installed there is no pm context to report.
    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        return 0

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce(
        "context-workstream", capability_root=capability_root
    ):
        return 2

    issue_number = _issue_number_from_branch(_current_branch())
    if issue_number is None:
        return 0

    config = load_adopter_config(capability_root)
    issue = gh_get_issue(issue_number, config, fields="labels")
    if issue is None:
        return 0

    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    value = axis_labels.read("workstream", labels)
    if value:
        print(value)
    return 0


def _current_branch() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _issue_number_from_branch(branch: str | None) -> int | None:
    if not branch:
        return None
    m = _BRANCH_ISSUE_RE.match(branch)
    return int(m.group(1)) if m else None


if __name__ == "__main__":
    sys.exit(main())
