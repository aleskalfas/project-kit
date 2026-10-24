#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — renumber: give a new artefact a free number, with every reference.

When two lines of work number a new use case, journey or requirement the same,
the first to reach the default branch keeps the number, and the other
renumbers before merging (DEC-001 point 3). `pkit analysis check-numbers`
reports the collision, and names this command. It renames the artefact's file,
rewrites its `id` and its heading, and rewrites each mention of the old id in
the repository's analyses — front matter, anchors, prose, links, revalidation
records, and a mention written with another analysis's qualifier, such as
`core:UC-021`. Each overview that names it is drawn anew. `_lib/renumber.py`
states the rules.

It refuses an artefact the default branch holds, since a settled number names
one artefact for good, and a new number the working tree holds, or one not
past what the default branch holds or its history gave. Without `--to`, the
new number is the next free one, as the stamp would give it.

Its effect reaches past the id named, into every file that mentions it, so it
shows its plan first (COR-004): `--dry-run` shows it and writes nothing,
`--yes` writes it, and a terminal is asked. Off a terminal, without either, it
refuses and writes nothing.

Usage:
  pkit analysis renumber <id> [--to <id>] [--base <ref>] [--dry-run | --yes]

`--base <ref>` names a branch the new number is given past too, beside the
default branch, as the stamp's `--base` does; `$PKIT_CHECK_BASE` is never read.

Exit codes:
  0  renumbered, or the plan shown with --dry-run
  1  refused, declined, or a write failed partway — the message says why
  2  a usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, renumber


def main() -> int:
    parser = argparse.ArgumentParser(
        prog=renumber.COMMAND,
        description=(
            "Give a use case, a journey or a requirement this branch numbered a free number "
            "before its change reaches the default branch, with every reference to it in the "
            "repository's analyses (software-analysis DEC-001 point 3)."
        ),
    )
    parser.add_argument("id", help="The id to renumber, such as UC-021.")
    parser.add_argument(
        "--to",
        metavar="ID",
        default=None,
        help=(
            "The new id, past what the default branch holds or its history gave (default: "
            "the next free number)."
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        default=None,
        help="A branch to give the number past too, beside the default branch.",
    )
    consent = parser.add_mutually_exclusive_group()
    consent.add_argument(
        "--dry-run", action="store_true", help="Show what would change, and write nothing."
    )
    consent.add_argument("--yes", action="store_true", help="Write without asking.")
    args = parser.parse_args()

    root = backbone.project_root()
    try:
        planned = renumber.plan(root, args.id, args.to, args.base)
    except renumber.Refused as exc:
        print(f"refused: {exc}; nothing is written.", file=sys.stderr)
        return 1
    print("\n".join(planned.lines()))
    for note in planned.notes:
        print(f"note: {note}")
    if args.dry_run:
        print("dry run: nothing is written.")
        return 0
    if not args.yes:
        again = f"{renumber.COMMAND} {planned.old} --to {planned.new}"
        if not sys.stdin.isatty():
            print(
                f"refused: not on a terminal, so nothing is written — run `{again} --yes` to "
                f"write it, or `{again} --dry-run` to see it again.",
                file=sys.stderr,
            )
            return 1
        reply = input(f"Renumber {planned.old} as {planned.new}? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("declined: nothing is written.", file=sys.stderr)
            return 1
    try:
        written = renumber.apply(root, planned)
    except renumber.Failed as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for warning in written.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(
        f"renumbered {planned.old} as {planned.new}: {len(written.paths)} file(s) changed. Run "
        f"`pkit analysis check-numbers`, then `pkit friction check`."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
