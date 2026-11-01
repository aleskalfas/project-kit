#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — obligation: each requirement's fingerprint of its texts
(DEC-006 points 6 and 7).

Each requirement, of each of the three kinds and withdrawn or not, carries `obligation`, a
fingerprint of its statement, its measure and where it holds. This command writes it
from the texts: wherever a requirement holds none, holds one that is no fingerprint, or
holds one that no longer matches its texts under the version of the form it names. A
value that still matches is left as it is, under whatever version it names, so writing
it again never changes it. `_lib/obligation.py` says how the texts are read, and
`pkit analysis validate` holds what it writes, whatever any rule's status.

It reads the analysis in the working tree through the backbone's discovery, `pkit friction
artefacts --json`, each text from its front-matter field, else from the part of its body
with the text's permanent id, as the project's own structures label it, and the forms of
derived link from the capability's package metadata. It writes only the line of the
field, each file whole or not at all, with the file's own line ends, and needs no
network.

Usage:
  pkit analysis obligation [<REQ-id>...] [--dry-run] [--json]

  <REQ-id>    write only the requirements of these ids; every requirement without one
  --dry-run   write nothing, and say what would be written
  --json      print the document: each requirement written, or that would be, with its
              id, its path, the value written, the value it held before (`null` where it
              held none) and its file's text with the value written; how many held
              theirs already; and each requirement that could not be written, and why

Exit codes:
  0  written, or nothing to write
  1  the analysis could not be read, an id names no requirement, or a requirement's texts
     or file could not be read or written; the others are written all the same
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, obligation
from _lib.model import REQUIREMENTS, Unreadable, identity
from _lib.stamp import Refused, refuse_links, write_whole

#: The version of the `--json` document.
SCHEMA_VERSION = 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis obligation",
        description=(
            "Write each requirement's `obligation`, the fingerprint of its statement, its "
            "measure and where it holds (software-analysis DEC-006 points 6 and 7), where it "
            "holds none or one that no longer matches its texts. A value that matches is left "
            "as it is. `pkit analysis validate` holds the field."
        ),
    )
    parser.add_argument("ids", nargs="*", metavar="REQ-id", help="write only these requirements")
    parser.add_argument("--dry-run", action="store_true", help="write nothing")
    parser.add_argument("--json", action="store_true", help="print the document")
    args = parser.parse_args()

    root = backbone.project_root()
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        print(f"error: the analysis could not be read: {exc}; nothing is written.", file=sys.stderr)
        return 1
    requirements = [a for a in analysis.artefacts if a.kind in REQUIREMENTS]
    named = {identity(i) for i in args.ids}
    unknown = sorted(named - {identity(a.id) for a in requirements if a.id})
    if unknown:
        print(
            f"error: no requirement {', '.join(unknown)} in the analysis; nothing is written.",
            file=sys.stderr,
        )
        return 1
    if named:
        requirements = [a for a in requirements if a.id and identity(a.id) in named]

    parted = obligation.kinds(root)
    written: list[dict[str, object]] = []
    problems: list[dict[str, object]] = []
    held = 0
    for artefact in sorted(requirements, key=lambda a: a.path):
        try:
            read, forms = obligation.read(root, artefact, parted)
            verdict = obligation.judged(artefact.fields, read, forms)
        except obligation.NoText as exc:
            problems.append({"id": artefact.id, "path": artefact.path, "why": str(exc)})
            continue
        if verdict.how == obligation.HOLDS:
            held += 1
            continue
        if verdict.how == obligation.UNKNOWN:
            problems.append(
                {
                    "id": artefact.id,
                    "path": artefact.path,
                    "why": obligation.message(verdict, parted.of.get(artefact.kind)),
                }
            )
            continue
        target = root / artefact.path
        try:
            text = _written(target, verdict.wanted)
            if not args.dry_run:
                refuse_links(root, target, artefact.path)
                write_whole(target, text.encode("utf-8"))
        except (obligation.Unwritable, Refused, OSError, UnicodeDecodeError) as exc:
            problems.append({"id": artefact.id, "path": artefact.path, "why": str(exc)})
            continue
        written.append(
            {
                "id": artefact.id,
                "path": artefact.path,
                "value": verdict.wanted,
                "was": artefact.fields.get(obligation.FIELD),
                "text": text,
            }
        )

    if args.json:
        document = {
            "schema_version": SCHEMA_VERSION,
            "dry_run": args.dry_run,
            "written": written,
            "held": held,
            "problems": problems,
        }
        print(json.dumps(document, indent=2, ensure_ascii=False))
    else:
        verb = "would write" if args.dry_run else "wrote"
        for entry in written:
            was = "it held none" if entry["was"] is None else "it no longer matched its texts"
            print(f"{verb} the obligation of {entry['id']} at {entry['path']} ({was})")
        for problem in problems:
            print(f"error: {problem['path']}: {problem['why']}", file=sys.stderr)
        if not requirements:
            print("The analysis holds no requirement, so no obligation is written.")
        elif not written and not problems:
            print(f"Each of {held} requirement(s) holds its obligation; nothing written.")
    return 1 if problems else 0


def _written(target: Path, wanted: str) -> str:
    """The file at `target` with its `obligation` reading `wanted`, in the file's own line
    ends. Raises `obligation.Unwritable` for a file whose line ends are mixed."""
    text = target.read_bytes().decode("utf-8")
    if "\r" in text and not text.count("\r\n") == text.count("\n") == text.count("\r"):
        raise obligation.Unwritable(
            "it has mixed line endings, so no ending can be chosen for the line the field "
            "takes: make them one, then run the command again"
        )
    rewritten = obligation.with_value(text.replace("\r\n", "\n"), wanted)
    return rewritten.replace("\n", "\r\n") if "\r" in text else rewritten


if __name__ == "__main__":
    sys.exit(main())
