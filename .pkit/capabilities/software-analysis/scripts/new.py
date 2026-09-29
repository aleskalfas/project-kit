#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — new: stamp an analysis artefact (DEC-001 points 2 to 4).

Writes one artefact from its kind's template under the analysis location — the
`analysis` sub-path of the internal documentation root, recorded the first
time an artefact is placed there (COR-049 point 5):

- a use case, `use-case-model/use-cases/[<area>/]UC-NNN-<slug>.md`, with its
  actor and the actor anchor;
- a journey, `use-case-model/journeys/JRN-NNN-<slug>.md`, with its steps and,
  from them, its use-case anchors;
- an actor, the entry `ACT-<slug>` of `use-case-model/actors.md`;
- a term, the entry `TERM-<slug>` of `glossary.md`.

A use case or journey takes the next free number on the default branch and in
the working tree; `pkit analysis check-numbers` reports a number another
branch took first. `_lib/stamp.py` states the rules.

Usage:
  pkit analysis new use-case <slug> --actor <ACT-id> [--area <area>] [--title <text>]
  pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id>... [--title <text>]
  pkit analysis new actor <slug> [--name <text>]
  pkit analysis new term <slug> [--name <text>]
  each also: [--path <glob>]... [--record <id>]... [--base <ref>]

Exit codes:
  0  stamped
  1  refused — the message says why
  2  a usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, stamp  # noqa: E402
from _lib.model import ACTOR, JOURNEY, TERM, USE_CASE  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pkit analysis new",
        description="Stamp an analysis artefact under the analysis location (software-analysis "
        "DEC-001).",
    )
    kinds = parser.add_subparsers(dest="kind", required=True, metavar="KIND")

    def kind(name: str, help_text: str, title: str) -> argparse.ArgumentParser:
        sub = kinds.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("slug", help="A word naming it: lowercase letters, digits and hyphens.")
        sub.add_argument(
            f"--{title}", dest="title", metavar="TEXT", help=f"Its {title} (default: the slug)."
        )
        sub.add_argument(
            "--path",
            dest="paths",
            action="append",
            default=[],
            metavar="GLOB",
            help="A path anchor: code that makes it true (repeatable).",
        )
        sub.add_argument(
            "--record",
            dest="records",
            action="append",
            default=[],
            metavar="ID",
            help="A record anchor: a decision it relies on (repeatable).",
        )
        sub.add_argument(
            "--base",
            metavar="REF",
            default=None,
            help=f"The default branch whose ids count as taken (default: "
            f"${backbone.BASE_ENV}, else {backbone.DEFAULT_BASE}).",
        )
        return sub

    use_case = kind(USE_CASE, "A use case: one actor's goal and how it is fulfilled.", "title")
    use_case.add_argument("--actor", required=True, metavar="ACT-ID", help="Whose goal it is.")
    use_case.add_argument(
        "--area", metavar="WORD", help="The functional area's folder to put it in."
    )
    journey = kind(JOURNEY, "A journey: one actor's path across several use cases.", "title")
    journey.add_argument("--actor", required=True, metavar="ACT-ID", help="Who takes it.")
    journey.add_argument(
        "--step",
        dest="steps",
        action="append",
        default=[],
        metavar="UC-ID",
        help="A use case it passes through, in order (at least two).",
    )
    kind(ACTOR, "An actor: a named role that uses the system, and its needs.", "name")
    kind(TERM, "A glossary term: a domain word and what it means.", "name")
    return parser


def main() -> int:
    args = _parser().parse_args()
    request = stamp.Request(
        kind=args.kind,
        slug=args.slug,
        title=args.title,
        actor=getattr(args, "actor", None),
        steps=tuple(getattr(args, "steps", ())),
        area=getattr(args, "area", None),
        paths=tuple(args.paths),
        records=tuple(args.records),
    )
    try:
        stamped = stamp.stamp(
            backbone.project_root(), request, args.base or backbone.default_base()
        )
    except stamp.Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    for note in stamped.notes:
        print(note)
    print(f"stamped {stamped.id} at {stamped.location}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
