#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""living-docs capability — fill-doc-check: its contribution to the documentation check.

This capability's filler of the `pkit::work-tracking:doc-check` data point
(DEC-001 point 7; project-management DEC-053 point 4): friction on anchored
pages and uncovered surface, as the point's obligations — one `page-stale` per
page of the spaces the backbone's whole-repository friction check reports
stale, one `code-undocumented` per path of the declared surface that nothing
anchors. A deferred page gives none: its deferral is the answer.
`_lib/doc_check.py` states the shape of each.

The backbone runs it wherever the point resolves — `pkit validate`, `pkit
status`, `pkit connections resolve` — as a query (COR-052 point 6): from the
project root, with `--json` alone and the offline marker set. It takes no
parameter: it reads the repository — HEAD and its history, through `pkit
friction check --all --json`, and which documents are pages, from the working
tree through `pkit friction artefacts --json` — writes nothing and needs no
network. Its `commands:` entry declares what it reads beyond the working tree,
`reads: [history]`, so the backbone's report names the commit HEAD was read
at; it reads no settled state and no base — the base a pull request is
compared with bounds the consumer's diff, never this filler (COR-052 point 6).
History that does not exist yet holds nothing: with no commit it answers `[]`.
History that exists and this clone cannot reach gives no answer: a page whose
friction lies beyond a shallow clone's history exits 1, never with an empty
answer. The contribution is inert while no capability provides the
work-tracking role; nothing here asks.

Usage:
  pkit living-docs fill-doc-check           one line per obligation, for a person
  pkit living-docs fill-doc-check --json    the filler envelope {schema_version, value}

Exit codes:
  0  answered
  1  no answer: the friction check or the places gave no document, or a page's
     friction lies beyond a shallow clone's history — never an empty answer in
     its place
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import doc_check, spaces
from _lib.artefacts import Unreadable
from _lib.declarations import project_root


def obligations(root: Path) -> list[dict[str, Any]]:
    """The point's obligations for the project at `root`. Raises NoAnswer."""
    if not doc_check.has_commit(str(root)):
        return []  # nothing committed: no HEAD to judge, so nothing is owed
    report = doc_check.read_friction(str(root))
    try:
        pages = spaces.pages(root)
    except Unreadable as exc:
        raise doc_check.NoAnswer(f"the pages cannot be told: {exc}") from exc
    return doc_check.obligations(report, pages)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            f"Print friction on anchored pages and uncovered surface as the obligations of the "
            f"{doc_check.POINT} data point (living-docs DEC-001 point 7). Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the filler envelope {schema_version, value}, as the backbone reads it.",
    )
    args = parser.parse_args()

    try:
        value = obligations(project_root())
    except doc_check.NoAnswer as exc:
        print(f"error: {exc}; no obligations can be given.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(doc_check.envelope(value), indent=2, ensure_ascii=False))
        return 0
    print(f"{doc_check.POINT}: {len(value)} {doc_check.SOURCE} obligation(s)")
    for obligation in value:
        subject = obligation.get("path") or obligation["document"]
        print(f"  {obligation['reason']}  {subject} — {obligation['description']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
