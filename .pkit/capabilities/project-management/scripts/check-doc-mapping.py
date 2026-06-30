#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "pathspec>=0.12",
# ]
# ///
"""Project-management capability — check-doc-mapping (verb-subject per DEC-020).

Enforce the code->doc mapping (DEC-015 + ADR-019): when a PR's diff touches a
code path a configured rule maps to doc(s), require at least one mapped doc to
also be in the diff — unless an explicit override line in the PR's
`## Doc impact` section names the code path.

ADR-019 framing: this script is the capability-owned *mechanism* — a read-only
check that exits non-zero on an unsatisfied mapping. The real *boundary* is the
adopter wiring it as a required CI status check behind branch protection
(`gh api` / `bash -c` evade any tool-layer check, per ADR-004). At the merge-pr
layer it is only a warning (a speed-bump). The capability ships the mechanism;
the adopter wires the boundary; the residual gap is declared, not hidden.

Configuration in `project/config.yaml` (opt-in, default off — ADR-019 Case A):
  code_path_to_doc_mapping:
    enforce: true            # default false -> advisory: report would-fire, exit 0
    rules:
      - code: "packages/cli/src/commands/registry.ts"   # gitignore-style glob
        docs: ["packages/cli/README.md"]

Use SURGICAL 1:1 couplings (a narrow surface file -> its reference doc). A broad
`tree/** -> README` rule false-positives on most PRs (see the dry-run audit);
keep those advisory (enforce: false) or don't map them. The mandatory
`## Doc impact` section remains the universal hard gate; this adds targeted
enforcement on couplings that genuinely move together.

Diff source: `--base <ref>` (default origin/main). Changed files come from
`git diff --name-only --diff-filter=ACMRT <base>...HEAD` — added/copied/
modified/renamed/type-changed; a *deletion* of a code file does not demand a
doc.

Override (bypassable-with-audit): a line in the PR body's `## Doc impact`
section that names the triggering code path (or the rule's code glob) marks that
rule satisfied — a human-visible, reviewed reason, not a silent skip. PR body
from `--pr-body-file <path>` or, failing that, `gh pr view` resolved from the
current branch.

Exit codes:
  0  all enforced mappings satisfied (or enforce off / no rules / no mapped code touched)
  1  one or more enforced mappings unsatisfied (enforce on)
  2  usage error (bad config, git failure)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pathspec
from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    resolve_capability_root,
)


def _changed_files(base: str) -> list[str] | None:
    """Non-deleted files changed between merge-base(base, HEAD) and HEAD."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRT", f"{base}...HEAD"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        print("error: git not found.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: git diff against {base!r} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _doc_impact_section(body: str) -> str:
    """Return the text of the PR body's `## Doc impact` section (lowercased)."""
    if not body:
        return ""
    lines = body.splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("## "):
            if capture:
                break  # next section ends Doc impact
            capture = stripped.lower().startswith("## doc impact")
            continue
        if capture:
            out.append(line)
    return "\n".join(out).lower()


def _pr_body(args: argparse.Namespace, config: dict) -> str:
    if args.pr_body_file:
        try:
            return Path(args.pr_body_file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"warn: could not read --pr-body-file: {exc}", file=sys.stderr)
            return ""
    # Resolve the PR body from the current branch (CI / local). Best-effort:
    # if there is no PR, overrides simply aren't available.
    proc = gh_run(
        ["gh", "pr", "view", "--json", "body", "-q", ".body"], config, check=False
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout or ""


def _matches(glob: str, path: str) -> bool:
    """gitignore-style match of a single glob against a single path."""
    spec = pathspec.PathSpec.from_lines("gitignore", [glob])
    return spec.match_file(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check the code->doc mapping (DEC-015 + ADR-019). Read-only. "
            "Exits non-zero on an unsatisfied enforced mapping; the real "
            "boundary is wiring this as a required CI status check."
        ),
    )
    parser.add_argument(
        "--base", default="origin/main",
        help="Base ref to diff HEAD against (default: origin/main).",
    )
    parser.add_argument(
        "--pr-body-file", default=None,
        help="File containing the PR body (override source). Default: gh pr view.",
    )
    parser.add_argument(
        "--capability-root", type=Path, default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    config = load_adopter_config(capability_root)
    mapping = config.get("code_path_to_doc_mapping") or {}
    if not isinstance(mapping, dict):
        print(
            "error: code_path_to_doc_mapping must be a mapping with "
            "`enforce:` and `rules:` (per ADR-019).",
            file=sys.stderr,
        )
        return 2
    enforce = bool(mapping.get("enforce", False))
    rules = mapping.get("rules") or []
    if not rules:
        print("check-doc-mapping: no rules configured; skipped.")
        return 0

    changed = _changed_files(args.base)
    if changed is None:
        return 2
    changed_set = set(changed)

    section = _doc_impact_section(_pr_body(args, config))

    mode = "enforce" if enforce else "advisory"
    print(f"check-doc-mapping: {len(rules)} rule(s), {len(changed)} changed file(s), mode={mode}")

    unsatisfied: list[str] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        code_glob = str(rule.get("code", ""))
        docs = rule.get("docs") or []
        if not code_glob or not docs:
            continue
        triggered = sorted(f for f in changed if _matches(code_glob, f))
        if not triggered:
            continue  # this rule's code surface wasn't touched
        doc_touched = any(
            any(_matches(str(d), f) for f in changed_set) for d in docs
        )
        if doc_touched:
            print(f"  ✓ {code_glob} → doc updated")
            continue
        # Override: the Doc-impact section names the glob or a triggering file.
        overridden = bool(section) and (
            code_glob.lower() in section
            or any(t.lower() in section for t in triggered)
        )
        if overridden:
            print(f"  ⊘ {code_glob} → overridden via `## Doc impact` (audited)")
            continue
        docs_str = ", ".join(str(d) for d in docs)
        print(f"  ✗ {code_glob} → {docs_str} (not updated; e.g. {triggered[0]})")
        unsatisfied.append(code_glob)

    if not unsatisfied:
        print("check-doc-mapping: all touched mappings satisfied.")
        return 0

    if enforce:
        print(
            f"\n[refused] {len(unsatisfied)} mapping(s) unsatisfied — update the "
            "mapped doc(s), or add a `## Doc impact` line naming the code path.",
            file=sys.stderr,
        )
        return 1
    print(
        f"\n[advisory] {len(unsatisfied)} mapping(s) would fire under enforce: true. "
        "Set code_path_to_doc_mapping.enforce: true (with surgical rules) to block.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
