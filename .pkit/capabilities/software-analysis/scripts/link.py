#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — link: the links between terms and views (DEC-004 point 7).

In every analysis that keeps a domain model — its `domain-model/` folder holds a
view — it writes each section's link to its term, right below the section's
heading, and links the first mention of each term in each section to the term's
entry in the glossary: in a view's opening and its sections, and in each glossary
entry below its heading. `_lib/links.py` states what a mention is, and the
safeguards that keep a link from naming the wrong term.

It reads the analysis in the working tree through the backbone's discovery, `pkit
friction artefacts --json`, and takes its data from front matter alone: each term's
name, `noun-forms` and `other-senses`, and each view's `explains`. It reads a body only
to place its links. It writes a file only where its links change, each whole or not
at all, with the file's own line ends, and needs no network. `pkit analysis
validate` holds what it writes, whatever any rule's status.

Usage:
  pkit analysis link    write the links, and name each file written

Exit codes:
  0  written, or nothing to write
  1  the analysis could not be read, or a file could not be read or written
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import analyses, backbone, links
from _lib.model import Unreadable
from _lib.stamp import Refused, refuse_links, write_whole


def main() -> int:
    argparse.ArgumentParser(
        prog="pkit analysis link",
        description=(
            "Write the links between the terms and the views of each analysis that keeps a "
            "domain model (software-analysis DEC-004 point 7): each view section's link to "
            "its term, and the first mention of each term in each section linked to its "
            "glossary entry, in the views and the glossary entries. Writes only where a link "
            "changes; `pkit analysis validate` holds the links."
        ),
    ).parse_args()

    root = backbone.project_root()
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        print(f"error: the analysis could not be read: {exc}; nothing is linked.", file=sys.stderr)
        return 1
    listing = analyses.read(root)
    read: dict[str, str | None] = {}
    crlf: dict[str, bool] = {}
    for rel in links.files(analysis, listing):
        try:
            text = (root / rel).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"error: {rel} could not be read: {exc}; nothing is linked.", file=sys.stderr)
            return 1
        if "\r" in text and not text.count("\r\n") == text.count("\n") == text.count("\r"):
            print(
                f"error: {rel} has mixed line endings, so no ending can be chosen for the lines "
                f"the links add — make them one, then link again; nothing is linked.",
                file=sys.stderr,
            )
            return 1
        crlf[rel] = "\r" in text
        read[rel] = text.replace("\r\n", "\n")
    planned = links.plan(analysis, listing, read)
    written = 0
    for linked in planned:
        if linked.linked == linked.text:
            continue
        target = root / linked.path
        out = linked.linked.replace("\n", "\r\n") if crlf.get(linked.path) else linked.linked
        try:
            refuse_links(root, target, linked.path)
            write_whole(target, out.encode("utf-8"))
        except (Refused, OSError) as exc:
            print(f"error: {linked.path} could not be written: {exc}", file=sys.stderr)
            return 1
        print(f"linked {linked.path} ({len(linked.departures)} link(s) written or mended)")
        written += 1
    if not planned:
        print("No analysis keeps a domain model, so no link is written (DEC-004 point 7).")
    elif not written:
        print("Every link is as it should be; nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
