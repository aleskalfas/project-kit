#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""living-docs capability — friction-report: the whole-repository check's findings, for people.

Renders the backbone's whole-repository friction check (COR-050 point 6) as one
Markdown body a project publishes where a person reads it — a tracking issue its
continuous integration keeps up to date, say — and says how many findings are
outstanding, so the publisher knows whether anything is left to answer.
`_lib/friction_report.py` states what is outstanding and how the body is made:
the same findings always give the same body, and everything the findings carry
is set as inert text.

It reads the check's document — through `pkit friction check --all --json`, or,
with `--report`, from a file that command was written to, so a pipeline that has
already run the check does not run it twice — and refuses one of a version it
does not read, as `fill-doc-check` does. It is a query: read-only, offline,
deterministic; it publishes nothing. Whatever the check found, it exits 0 — the
check reports and never fails (COR-050 point 12).

Usage:
  pkit living-docs friction-report                    the body, from the check run at HEAD
  pkit living-docs friction-report --report <file>    the body, from that file's document
  pkit living-docs friction-report --json             the publication {schema_version,
                                                      outstanding, body}

Exit codes:
  0  rendered, whatever the check found
  1  no document to render: the check gave none, the file holds none, or one of a
     version this capability does not read
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import doc_check, friction_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render the whole-repository friction check's findings as one Markdown body to "
            "publish, and say how many are outstanding. Read-only and offline."
        ),
    )
    parser.add_argument(
        "--report",
        metavar="FILE",
        help="Read the check's document from FILE, written by `pkit friction check --all --json`.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the publication {schema_version, outstanding, body}.",
    )
    args = parser.parse_args()

    try:
        if args.report:
            document = doc_check.parse_friction(
                Path(args.report).read_text(encoding="utf-8"), args.report
            )
        else:
            document = doc_check.read_friction(str(Path.cwd()))
    except OSError as exc:
        print(f"error: {args.report} cannot be read ({exc}); nothing to render.", file=sys.stderr)
        return 1
    except doc_check.NoAnswer as exc:
        print(f"error: {exc}; nothing to render.", file=sys.stderr)
        return 1
    publication = friction_report.publication(document)
    if args.json:
        print(json.dumps(publication, indent=2, ensure_ascii=False))
    else:
        sys.stdout.write(publication["body"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
