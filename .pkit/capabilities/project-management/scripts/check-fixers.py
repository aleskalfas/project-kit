#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — check-fixers (DEC-056 points 1 and 2).

The `project-management:fixers` member of `pkit validate` (COR-055 point 3):
checks each entry of the `pkit::work-tracking:fixers` point, and the grant list
in `project/config.yaml`. Each finding says why a fixer starts no agent:

- **error** — the project's own entry names an agent that is not deployed, or
  the grant list cannot be read. The project can mend both.
- **warning** — the project's own entry names an agent whose deployed definition
  claims paths, or holds a tool that changes existing files or starts agents; a
  grant that no entry names, with the command that revokes it; a capability's
  type that could not be checked, because the type registries could not be read.
- **report** — a capability's entry that names a type not its own, an agent it
  does not ship or that is not deployed, an agent such as above, or that comes
  through a command filler. The project cannot mend these, so they fail nothing
  (COR-055 point 1).

An unresolved point is the `connections` member's finding, so it is only said
in the summary here. A query: read-only and offline, run by `pkit validate` with
`--json` alone. Exempt from the bootstrap gate, as every validator must be.

Usage:
  pkit pm check-fixers           the findings, for a person
  pkit pm check-fixers --json    {"summary": [...], "findings": [...]}, as validation reads it

Exit codes:
  0  answered; without --json, also: no error found
  1  without --json: an error found
  2  the capability is not found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import fixers
from _lib.membership import CAPABILITY_NAME, resolve_capability_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            f"Check the {fixers.POINT} point's entries and the grant list (DEC-056). Read-only."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print the document validation reads.")
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    repo_root = capability_root.parents[2]
    config_path = capability_root / fixers.CONFIG_RELATIVE
    config_location = (
        str(config_path.relative_to(repo_root))
        if config_path.is_relative_to(repo_root)
        else str(config_path)
    )

    summary: list[str] = []
    found: list[fixers.Finding] = []
    try:
        answers = fixers.answers_of(fixers.load_config(config_path))
    except fixers.Malformed as exc:
        answers = fixers.Answers()
        found.append(
            fixers.Finding(
                fixers.ERROR,
                f"{config_location}:/{fixers.CONFIG_KEY}",
                f"the grant list cannot be read, so no fixer may start: {exc}.",
            )
        )
    try:
        point = fixers.read_point()
    except fixers.Unreadable as exc:
        found.append(
            fixers.Finding(fixers.ERROR, fixers.POINT, f"the point could not be read: {exc}.")
        )
        point = None
    if point is not None and not point.resolved:
        summary.append(
            f"{fixers.POINT}: not checked — the point does not resolve ({point.why}); "
            "the `connections` member reports it"
        )
    elif point is not None and not point.entries:
        summary.append(f"{fixers.POINT}: no fixer declared ({point.why})")
        found += fixers.findings(point, [], answers, config_location)
    elif point is not None:
        checked = fixers.check(point, repo_root)
        granted = fixers.startable(checked, answers)
        summary.append(
            f"{fixers.POINT}: {len(point.entries)} type(s) for {len(point.agents)} agent(s); "
            f"{sum(c.startable for c in checked)} pass the checks, {len(granted)} granted"
        )
        found += fixers.findings(point, checked, answers, config_location)

    if args.json:
        # Validation reads the findings, so an answer exits 0 whatever they say: a
        # non-zero exit would be no answer (COR-055 point 6).
        document = {"summary": summary, "findings": [f.as_dict() for f in found]}
        print(json.dumps(document, indent=2, ensure_ascii=False))
        return 0
    for line in summary:
        print(line)
    for finding in found:
        print(f"{finding.severity}  {finding.location}\n  → {finding.message}")
    return 1 if any(f.severity == fixers.ERROR for f in found) else 0


if __name__ == "__main__":
    sys.exit(main())
