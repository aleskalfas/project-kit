#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""living-docs capability — new: stamp a page, or a space's definition (DEC-001 points 2 and 4).

- `new page` writes one new page of a declared kind into a declared space, from
  the kind's template: its `reader`, its `kind` and its friction block with the
  anchors given in the front matter, the title in its level-1 heading, every
  other placeholder of the template left for the writer to fill.
- `new space` writes a space's definition when the project creates the space:
  the definition under the definitions location's `rule-sets/`, inheriting
  `living-docs:LDOC` at its current major with the scope that selects the
  space's pages, its path as the space's `definition` in the capability's
  project configuration, and the definitions location, recorded on first use.

Each runs the validator's check before and after its write, and puts back what
it wrote and refuses when the write brings an error the project did not have.
`_lib/stamp.py` states the rules. `--dry-run` makes the checks before the write,
prints each file it would write, and writes nothing.

Usage:
  pkit living-docs new page <file> --space <space> --kind <kind> --reader <id> --title <text>
      [--path <glob>]... [--record <id>]... [--artefact <id>]... [--source <name>]... [--dry-run]
  pkit living-docs new space <space> [--set <NAME>] [--dry-run]

Exit codes:
  0  stamped, or the dry run's checks passed, with any warning on standard error
  1  refused — the message says why and what to do
  2  a usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import stamp
from _lib.declarations import project_root

PAGE, SPACE = "page", "space"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pkit living-docs new",
        description="Stamp a page of a documentation space, or a space's definition "
        "(living-docs DEC-001 points 2 and 4).",
    )
    forms = parser.add_subparsers(dest="form", required=True, metavar="FORM")

    page = forms.add_parser(
        PAGE,
        help="A page of a declared kind in a declared space, from the kind's template.",
        description="Stamp a new page of a declared kind into a declared space, from the "
        "kind's template, with its reader, its kind and its anchors in its front matter.",
    )
    page.add_argument("file", help="The page's path from the repository root, ending .md.")
    page.add_argument("--space", required=True, help="The space the page is of.")
    page.add_argument("--kind", required=True, help="The page's kind, one the capability declares.")
    page.add_argument("--reader", required=True, metavar="ID", help="The reader the page is for.")
    page.add_argument("--title", required=True, metavar="TEXT", help="The page's title.")
    for option, dest, metavar, what in (
        ("--path", "paths", "GLOB", "code or files the page describes"),
        ("--record", "records", "ID", "a decision, or one point of it, the page applies"),
        (
            "--artefact",
            "artefacts",
            "ID",
            "a rule, an analysis artefact, or a section it summarises",
        ),
        ("--source", "sources", "NAME", "a captured source it rests on"),
    ):
        page.add_argument(
            option,
            dest=dest,
            action="append",
            default=[],
            metavar=metavar,
            help=f"An anchor: {what} (repeatable).",
        )
    _dry_run(page)

    space = forms.add_parser(
        SPACE,
        help="A space's definition, written when the project creates the space.",
        description="Write a space's definition, with the scope that selects its pages, and "
        "name it as the space's definition in the capability's project configuration.",
    )
    space.add_argument("space", help="The space's id: user, technical, or one the project adds.")
    space.add_argument(
        "--set",
        dest="set_name",
        metavar="NAME",
        help="The rule set's name (default: the id in upper case, its hyphens dropped).",
    )
    _dry_run(space)
    return parser


def _dry_run(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Make the checks before the write, print each file it would write, write nothing.",
    )


def main() -> int:
    args = _parser().parse_args()
    root = project_root()
    try:
        if args.form == PAGE:
            stamped = stamp.stamp_page(
                root,
                stamp.PageRequest(
                    file=args.file,
                    space=args.space,
                    kind=args.kind,
                    reader=args.reader,
                    title=args.title,
                    paths=tuple(args.paths),
                    records=tuple(args.records),
                    artefacts=tuple(args.artefacts),
                    sources=tuple(args.sources),
                ),
                dry_run=args.dry_run,
            )
        else:
            stamped = stamp.stamp_space(
                root, stamp.SpaceRequest(args.space, args.set_name), dry_run=args.dry_run
            )
    except stamp.Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    if not stamped.written:
        for file in stamped.files:
            print(f"would write {file.path}:")
            print(file.text, end="" if file.text.endswith("\n") else "\n")
            print()
    for note in stamped.notes:
        print(note)
    for warning in stamped.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
