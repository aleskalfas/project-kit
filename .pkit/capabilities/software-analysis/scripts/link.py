#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — link: an analysis's links (DEC-001 points 13 and 14,
DEC-004 point 7).

In every analysis, it links the first citation of each record, point and rule in each
section of each artefact in force to what it cites: a record's file, a point's
heading, a rule's heading. `_lib/citations.py` states the forms a citation takes, and
`pkit refs lookup --json`, in one call, says where each leads, with the host's anchor
of a heading. A citation that resolves to nothing takes no link, and is named.

In every analysis, it also links the first mention of each artefact by its id in each
section to that artefact: a use case, a journey, a requirement, an actor or a view to its
file, and a term to its glossary entry, by a path from the file. An id alone names an
artefact of its own analysis, and `core:UC-021` one of an analysis it builds on. A bold
label is read for ids, so a journey's seams and a precondition's producers link theirs,
and a journey's step line links its use case's id. An artefact's own id takes no link.

In every analysis that keeps a domain model — its `domain-model/` folder holds a
view — it also writes each section's link to its term, right below the section's
heading, and links the first mention of each term in each section to the term's
entry in the glossary: in a view's opening and its sections, in each glossary entry
below its heading, and in each part of an actor's, a use case's, a journey's and a
requirement's body. A goal, a journey's step lines and an actor's first sentence say
a datum again, and stay plain. Each view ends with its closing section, `## What is
built on these concepts`, which lists under each concept it explains each use case,
journey and requirement whose body links the concept's term. `_lib/links.py` states what a
mention is, and the safeguards that keep a link from naming the wrong term.

It reads the analysis in the working tree through the backbone's discovery, `pkit
friction artefacts --json`, and takes its data from front matter and the declared
structures alone: each term's name, `noun-forms` and `other-senses`, each view's
`explains`, an actor's `summary`, and the labels that open each part, as the project's
own structures relabel and add them, and each artefact's id and file. It reads a body
only to place its links, at the mentions, the citations and the ids its text makes. It
writes a file only where its links change, each whole or not at all, with the file's own
line ends, and needs no network. `pkit analysis validate` holds what it writes, whatever
any rule's status.

Usage:
  pkit analysis link    write the links, and name each file written

Exit codes:
  0  written, or nothing to write
  1  the analysis or the kinds' declared structure could not be read, the citations
     could not be looked up, or a file could not be read or written
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import analyses, backbone, links, structure
from _lib.model import Unreadable
from _lib.stamp import Refused, refuse_links, write_whole


def main() -> int:
    argparse.ArgumentParser(
        prog="pkit analysis link",
        description=(
            "Write the links of the analysis: in every analysis, the first citation of each "
            "record, point and rule in each section linked to what it cites (software-analysis "
            "DEC-001 point 13), and the first mention of each artefact by its id in each "
            "section linked to that artefact (DEC-001 point 14); in each analysis that keeps "
            "a domain model, each view section's link to its term, and the first mention of "
            "each term in each section linked to its glossary entry, in the views, the "
            "glossary entries, and each part of the actors, use cases, journeys and "
            "requirements (DEC-004 point 7). Each view ends with where its concepts are used. "
            "Writes only where a link changes; `pkit analysis validate` holds the links."
        ),
    ).parse_args()

    root = backbone.project_root()
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        print(f"error: the analysis could not be read: {exc}; nothing is linked.", file=sys.stderr)
        return 1
    listing = analyses.read(root)
    try:
        kinds = links.parted(root)
    except structure.Unreadable as exc:
        print(
            f"error: the kinds' declared structure could not be read: {exc}; nothing is linked.",
            file=sys.stderr,
        )
        return 1
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
    try:
        lookups = backbone.lookup(root, links.asked(analysis, listing, read, kinds))
    except Unreadable as exc:
        print(
            f"error: the citations could not be looked up: {exc}; nothing is linked.",
            file=sys.stderr,
        )
        return 1
    planned = links.plan(analysis, listing, read, kinds, lookups)
    written = 0
    for linked in planned:
        for d in linked.departures:
            if d.how == links.UNRESOLVED:
                print(
                    f"note: {linked.path}:{d.line}: `{d.text}` takes no link: {d.wanted} "
                    f"(DEC-001 point 13)"
                )
        mended = [d for d in linked.departures if d.how != links.UNRESOLVED]
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
        print(f"linked {linked.path} ({len(mended)} link(s) written or mended)")
        written += 1
    if not planned:
        print("The analysis holds no artefact in force, so no link is written.")
    elif not written:
        print("Every link is as it should be; nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
