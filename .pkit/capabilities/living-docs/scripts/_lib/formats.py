"""A page's body against the structure its kind declares (RS-LDOC-004).

Pages of a kind follow one format, with a template per kind (living-docs
DEC-001 point 3). The part of a format a tool can check is the page's
**structure**: the sections its body must carry, in order where order
matters. Each kind's structure is declared once, in this capability's
`schemas/page-kinds.yaml` — never inferred from the template's text — and
read here; the validator checks every page of the kind against it, and a test
checks every template against it, so neither holds a copy that can drift.

What a **section** is, precisely: an ATX heading — a line of one to six `#`,
indented at most three spaces, then a space, a tab or the end of the line —
outside a fenced code block and below the front matter. Its level is the
number of `#`; its text is the rest of the line without a closing run of `#`.
An underlined (setext) heading, and a heading inside a block quote or a list
item, is not read. A declared section names its level and, where the kind
fixes the wording, its text; a section without text is one the writer words —
the template's `<placeholder>` heading. Text is compared ignoring case, runs
of white space and trailing punctuation (`. , : ; ! ?`). A page may carry
sections besides the declared ones.

A kind with no declared structure is not checked, and nothing is said about
it. The declarations are read forgivingly: a malformed entry reads as no
structure (the file's shape is `pkit schemas validate`'s, against
`schemas/page-kinds.schema.json`).

This module imports nothing of the capability's library, so it reads alone.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

#: Where each kind's structure is declared, relative to this capability's folder.
PAGE_KINDS = Path("schemas") / "page-kinds.yaml"

#: The shared method's rule a page's structure applies (DEC-001 point 3).
FORMAT_RULE = "RS-LDOC-004"

#: How a section departs from its kind's structure.
MISSING, OUT_OF_ORDER = "missing", "out-of-order"

_ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_CLOSING = re.compile(r"(?:^|[ \t]+)#+$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_FRONT_MATTER_FENCE = re.compile(r"^---[ \t]*$")
_TRAILING = re.compile(r"[\s.,:;!?]+$")


@dataclass(frozen=True)
class Section:
    """One section a kind declares: a heading's level and, when the kind fixes its
    wording, its text."""

    level: int
    text: str | None = None

    def matches(self, heading: Heading) -> bool:
        return heading.level == self.level and (
            self.text is None or _comparable(heading.text) == _comparable(self.text)
        )

    def described(self) -> str:
        if self.text is None:
            return f"a level-{self.level} heading"
        return f"`{'#' * self.level} {self.text}`"


@dataclass(frozen=True)
class Structure:
    """A kind's declared structure: its sections, and whether they come in that order."""

    sections: tuple[Section, ...]
    ordered: bool = True

    def described(self) -> str:
        parts = [section.described() for section in self.sections]
        if len(parts) == 1:
            return parts[0]
        if self.ordered:
            return ", then ".join(parts)
        return f"{', '.join(parts[:-1])} and {parts[-1]}, in any order"


@dataclass(frozen=True)
class Heading:
    """A heading of a page's body: its level, its text, and its line in the file."""

    level: int
    text: str
    line: int


@dataclass(frozen=True)
class Departure:
    """A declared section a page lacks, or carries out of order — then at `line`,
    where the page first carries it."""

    section: Section
    how: str  # MISSING or OUT_OF_ORDER
    line: int | None = None


def read_structures(path: Path) -> dict[str, Structure]:
    """Each kind's declared structure, from the file at `path`; a kind whose entry is
    malformed, and every kind when the file is absent or unparsable, has none."""
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError):
        return {}
    kinds = data.get("kinds") if isinstance(data, Mapping) else None
    if not isinstance(kinds, Mapping):
        return {}
    structures: dict[str, Structure] = {}
    for kind, entry in kinds.items():
        structure = _structure(entry)
        if isinstance(kind, str) and structure is not None:
            structures[kind] = structure
    return structures


def _structure(entry: Any) -> Structure | None:
    if not isinstance(entry, Mapping):
        return None
    ordered = entry.get("ordered", True)
    sections = entry.get("sections")
    if not isinstance(ordered, bool) or not isinstance(sections, list) or not sections:
        return None
    read = [_section(item) for item in sections]
    if any(section is None for section in read):
        return None
    return Structure(sections=tuple(s for s in read if s is not None), ordered=ordered)


def _section(item: Any) -> Section | None:
    if not isinstance(item, Mapping):
        return None
    level, text = item.get("level"), item.get("text")
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 6:
        return None
    if text is None:
        return Section(level)
    if not isinstance(text, str) or not text.strip():
        return None
    return Section(level, text.strip())


def headings(text: str) -> list[Heading]:
    """The headings of a Markdown file's body, in order: ATX headings outside fenced
    code, below the front matter, each with its line in the file."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    found: list[Heading] = []
    fence: tuple[str, int] | None = None  # the open fence's character and length
    for index in range(_body_start(lines), len(lines)):
        line = lines[index]
        if fence is not None:
            if _closes(line, fence):
                fence = None
            continue
        opening = _FENCE.match(line)
        if opening is not None and not (
            opening.group(1).startswith("`") and "`" in opening.group(2)
        ):
            fence = (opening.group(1)[0], len(opening.group(1)))
            continue
        atx = _ATX.match(line)
        if atx is not None:
            raw = (atx.group(2) or "").strip()
            found.append(Heading(len(atx.group(1)), _CLOSING.sub("", raw).strip(), index + 1))
    return found


def _body_start(lines: Sequence[str]) -> int:
    """The index of the body's first line: past the front matter — a leading `---`
    line closed by the next `---` line — when there is one."""
    if not lines or lines[0].rstrip() != "---":
        return 0
    for index in range(1, len(lines)):
        if _FRONT_MATTER_FENCE.match(lines[index]):
            return index + 1
    return 0


def _closes(line: str, fence: tuple[str, int]) -> bool:
    char, length = fence
    return re.match(rf"^ {{0,3}}{re.escape(char)}{{{length},}}[ \t]*$", line) is not None


def _comparable(text: str) -> str:
    """A heading's text as sections compare it: case, runs of white space and
    trailing punctuation ignored."""
    return _TRAILING.sub("", " ".join(text.split())).casefold()


def departures(found: Sequence[Heading], structure: Structure) -> list[Departure]:
    """How a body with headings `found` departs from `structure`, in declared order.

    Each declared section takes a heading of its own: a section is **missing** when
    no heading is left that it matches — sections with fixed text choose first, as
    they match fewer. Of an ordered structure, a section the body carries is **out
    of order** when no heading after the one the previous section took matches it;
    the departure names the line where the page first carries it."""
    missing = _unmatched(found, structure.sections)
    result = {index: Departure(structure.sections[index], MISSING) for index in missing}
    if structure.ordered:
        after = 0
        for index, section in enumerate(structure.sections):
            if index in missing:
                continue
            at = next(
                (i for i in range(after, len(found)) if section.matches(found[i])),
                None,
            )
            if at is None:
                first = next(h for h in found if section.matches(h))
                result[index] = Departure(section, OUT_OF_ORDER, first.line)
            else:
                after = at + 1
    return [result[index] for index in sorted(result)]


def _unmatched(found: Sequence[Heading], sections: Sequence[Section]) -> set[int]:
    """The indices of the sections no heading of their own is left for."""
    taken: set[int] = set()
    unmatched: set[int] = set()
    for index in sorted(range(len(sections)), key=lambda i: sections[i].text is None):
        heading = next(
            (i for i, h in enumerate(found) if i not in taken and sections[index].matches(h)),
            None,
        )
        if heading is None:
            unmatched.add(index)
        else:
            taken.add(heading)
    return unmatched
