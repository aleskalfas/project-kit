"""The domain model's views, and each term's link to its section (DEC-004).

A domain-model view explains a group of related concepts, one section for each,
headed by its term's name, and lists those terms in its front matter's
`explains`, in the order of its sections (point 2). Its id is `VIEW-` and the
slug its file's name gives after its number (point 4). It anchors exactly the
terms `explains` lists, which the stamp writes from the list (point 5).

**One view for each term.** No two views in force of one analysis explain one
term (point 5). A withdrawn view explains nothing: no term links to it, and it
counts for no term's one view (`explaining`).

**The term's link** (point 7). A term a view in force explains links to that
view's section on it, on an unlabelled line under the term's heading in the
glossary, before its first part, where a reader reads the term. The stamp
writes it, and the check holds it equal to the view, whatever any rule's
status. A term no view explains carries none.

- **The line** reads `Explained in [<view id>](<file>#<slug>).` (`link`): the
  view's file as a path from the glossary's folder, such as
  `domain-model/010-orders-and-payments.md`, and the slug of its section's
  heading, the term's name, as COR-050 point 2 makes it. It depends on the
  view's file's name and the term's name alone, so a retitled view changes no
  link.
- **Where it is read** (`link_lines`): the lines of the term's section, as the
  backbone spans it, below its heading and above its first part, a line that
  opens with a bold label. Of these, a line that holds a link into a
  `domain-model/` folder is a link to the domain model, however it is worded.
- **Where it is written** (`linked`): right below the heading, a blank line
  before it, in place of a link the section holds already.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Mapping, Sequence

from _lib import forms
from _lib.model import EXPLAINS, TERM, VIEW, Analysis, Artefact

#: What a term's link opens with, before the link itself.
OPENING = "Explained in"

#: A Markdown link into a `domain-model/` folder, as a term's link to its view is.
_INTO = re.compile(r"\]\((?:\./)?(?:[^()\s]*/)?domain-model/[^()\s]*\)")

#: A line that opens a part of a term's section: a bold label opening the line, or a list
#: item it opens, or a heading.
_PART = re.compile(r"^(?:(?:[-+*]|[0-9]{1,9}[.)])[ \t]+)?\*\*[^*\n]+?\*\*|^#{1,6}(?:[ \t]|$)")


def explained(view: Artefact) -> list[str]:
    """The term ids a view's `explains` lists, as written; none where it is no list."""
    listed = view.fields.get(EXPLAINS)
    if not isinstance(listed, list):
        return []
    return [value for value in listed if isinstance(value, str)]


def explaining(analysis: Analysis) -> dict[tuple[str | None, str], list[Artefact]]:
    """Each view in force that explains a term, by the folder of the analysis it lies in
    and the term's id, in the order of their paths. A withdrawn view explains nothing
    (DEC-004 point 5)."""
    found: dict[tuple[str | None, str], list[Artefact]] = {}
    for view in sorted(analysis.of_kind(VIEW), key=lambda v: v.path):
        if view.withdrawn:
            continue
        for term in dict.fromkeys(explained(view)):
            found.setdefault((view.folder, term), []).append(view)
    return found


def link(glossary: str, view_id: str, view_path: str, name: str) -> str:
    """The line that links a term, named `name`, of the glossary at `glossary` to its
    section in the view `view_id`, whose file is at `view_path` (DEC-004 point 7)."""
    target = posixpath.relpath(view_path, posixpath.dirname(glossary) or ".")
    return f"{OPENING} [{view_id}]({target}#{forms.heading_slug(name)})."


def link_lines(lines: Sequence[tuple[int, str]]) -> list[tuple[int, str]]:
    """Each line of a term's section, `lines` as the backbone spans it, its heading first,
    that links to the domain model: below the heading and above the first part, a line
    holding a Markdown link into a `domain-model/` folder."""
    found: list[tuple[int, str]] = []
    for number, text in lines[1:]:
        if _PART.match(text):
            break
        if _INTO.search(text):
            found.append((number, text))
    return found


def linked(text: str, spans: Mapping[tuple[int, int], str]) -> str:
    """The glossary `text`, LF line ends, with each term's link written: for each section
    `spans` gives, by its first and last line, the line to write right below its
    heading, in place of the first link the section holds, and any other link it holds
    taken out."""
    lines = text.split("\n")
    for (first, last), line in sorted(spans.items(), reverse=True):
        section = [(n, lines[n - 1]) for n in range(first, min(last, len(lines)) + 1)]
        held = [n for n, _text in link_lines(section)]
        if held:
            lines[held[0] - 1] = line
            for n in sorted(held[1:], reverse=True):
                del lines[n - 1]
        else:
            lines[first:first] = ["", line]
    return "\n".join(lines)


def term_name(analysis: Analysis, term_id: str) -> str | None:
    """A term's name, by its id; `None` where the analysis holds no such term, or one with
    no name."""
    term = analysis.of(term_id, TERM)
    name = term.fields.get("name") if term is not None else None
    return name if isinstance(name, str) and name else None
