#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — list-fixers (DEC-056 points 1 and 2).

Lists the fixers the `pkit::work-tracking:fixers` point declares — which agent
fixes the artefacts of each type — with the project's answer for each, read
from the grant list in `project/config.yaml`: granted, refused, or not asked.
An entry that fails one of DEC-056 point 1's checks says why its agent does not
start. A grant that no entry names is listed with the command that revokes it.

Read-only. The answers it shows are the working tree's; the drift command reads
them at the default branch's commit, so an answer counts once its change merges.

Usage:
  pkit pm list-fixers          one line per type, for a person
  pkit pm list-fixers --json   the same, as one JSON document

Exit codes:
  0  listed
  1  the point does not resolve or cannot be read, or the grant list cannot be read
  2  the capability is not found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import fixers
from _lib.membership import CAPABILITY_NAME, resolve_capability_root

#: The version of the `--json` document; it rises only on a change that breaks a reader.
DOCUMENT_VERSION = 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            f"List the fixers the {fixers.POINT} point declares, with the project's answer "
            "for each (DEC-056). Read-only."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print one JSON document.")
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

    try:
        point = fixers.read_point()
    except fixers.Unreadable as exc:
        print(f"error: the {fixers.POINT} point could not be read: {exc}", file=sys.stderr)
        return 1
    try:
        answers = fixers.answers_of(fixers.load_config(config_path))
    except fixers.Malformed as exc:
        print(f"error: the grant list cannot be read: {exc}", file=sys.stderr)
        return 1
    checked = fixers.check(point, repo_root)
    stale = fixers.stale_grants(point, answers)

    if args.json:
        print(json.dumps(_document(point, checked, answers, stale), indent=2, ensure_ascii=False))
        return 0 if point.resolved else 1
    if not point.resolved:
        print(
            f"[unresolved] {fixers.POINT} does not resolve: {point.why}. No fixer may start.",
            file=sys.stderr,
        )
        for line in point.inert:
            print(f"  inert: {line}", file=sys.stderr)
    elif not point.entries:
        print(f"{fixers.POINT}: no fixer declared ({point.why}).")
    else:
        agents = point.agents
        print(f"{fixers.POINT}: {len(point.entries)} type(s), {len(agents)} agent(s)")
        for agent in agents:
            print(agent)
            for item in checked:
                entry = item.entry
                if entry.agent != agent:
                    continue
                answer = answers.of(agent, entry.type) or "not asked"
                print(f"  {entry.type} ({entry.description}, from {entry.declared_by}): {answer}")
                for problem in item.problems:
                    print(f"    starts no agent: {problem.text}")
    if stale:
        print("Grants no entry names, which start nothing:")
        for agent, artefact_type in stale:
            print(
                f"  {agent}: {artefact_type}. Revoke: {fixers.revoke_line(agent, [artefact_type])}"
            )
    return 0 if point.resolved else 1


def _document(
    point: fixers.Point,
    checked: list[fixers.Checked],
    answers: fixers.Answers,
    stale: list[tuple[str, str]],
) -> dict[str, Any]:
    return {
        "schema_version": DOCUMENT_VERSION,
        "point": fixers.POINT,
        "resolved": point.resolved,
        "why": point.why,
        "inert": list(point.inert),
        "fixers": [
            {
                "agent": agent,
                "types": [
                    {
                        "type": item.entry.type,
                        "description": item.entry.description,
                        "origin": item.entry.origin,
                        "answer": answers.of(agent, item.entry.type),
                        "problems": [
                            {"severity": p.severity, "text": p.text} for p in item.problems
                        ],
                    }
                    for item in checked
                    if item.entry.agent == agent
                ],
            }
            for agent in point.agents
        ],
        "stale": [
            {
                "agent": agent,
                "type": artefact_type,
                "revoke": fixers.revoke_line(agent, [artefact_type]),
            }
            for agent, artefact_type in stale
        ],
    }


if __name__ == "__main__":
    sys.exit(main())
