"""A page's body: its structure against its kind's (RS-LDOC-004), and its diagrams.

Pages of a kind follow one format, with a template per kind (living-docs
DEC-001 point 3). The part of a format a tool checks is the page's
**structure**: the sections every page of the kind carries, in order where
order matters. Each kind's structure is declared once, in this capability's
`schemas/page-kinds.yaml` — never read out of the template's text — and read
here; the validator checks a page of the kind against it where RS-LDOC-004
binds on the page, as `spaces` reads it from the backbone, and a test checks
every template against it, so neither holds a copy that can drift.

What a **section** is, precisely: a heading written as a line that opens, with
no space before it, with one to six `#`, then a space, a tab or the end of the
line — below the front matter, outside fenced code and outside an HTML
comment. Its level is the number of `#`; its text is the rest of the line
without a closing run of `#`. Nothing else is read as a heading: not an
indented `#` line (under a list item, say), not one inside a block quote, not
an underlined (setext) heading, not an HTML heading (`<h1>`).

What hides a line. A fenced code block opens on a line of three or more
backticks or tildes — at any indentation, and after block-quote and list
markers — and closes on a line that holds, after any indentation and
block-quote markers, only as many of the same character or more; one never
closed runs to the end of the file. An HTML comment opens on a line that
begins with `<!--` and runs to the line holding the next `-->`.

A declared section names its level and, where the kind fixes the wording, its
text. A section without text is one the writer words: a heading with words of
its own satisfies it; an empty heading (`#` alone) and a template's unfilled
`<placeholder>` do not. Text is compared ignoring case, runs of white space
and trailing punctuation (`. , : ; ! ?`). A page may carry sections besides
the declared ones.

The declarations are read whole or not at all: a file that is absent, is not
YAML or does not fit `schemas/page-kinds.schema.json` is `Unreadable`, with
the reason. A kind the file does not list declares no structure.

What a **diagram** is: a fenced code block whose info string's first word is
`mermaid`, read as the headings are, below the front matter and outside an HTML
comment (living-docs DEC-002 point 2). Its text alternative is an `accTitle` and
an `accDescr` inside the fence, each followed by text that is not blank
(RS-LDOC-008; DEC-002 point 8). A line inside the fence is read without the
indentation and block-quote markers before it. `accTitle: <text>` names the
diagram. `accDescr: <text>`, or `accDescr {` opening a block that holds text
before its closing `}`, says what it shows. A Mermaid comment, a line opening
with `%%`, holds neither.

This module imports nothing of the capability's library, so it reads alone.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError, YAMLError

#: Where each kind's structure is declared, and the schema the declaration fits —
#: each relative to this capability's folder.
PAGE_KINDS = Path("schemas") / "page-kinds.yaml"
PAGE_KINDS_SCHEMA = Path("schemas") / "page-kinds.schema.json"

#: The shared method's rule a page's structure applies (DEC-001 point 3).
FORMAT_RULE = "RS-LDOC-004"

#: The shared method's rule a diagram's text alternative applies (DEC-002 point 8).
ALTERNATIVE_RULE = "RS-LDOC-008"

#: The first word of a diagram's info string (DEC-002 point 2).
MERMAID = "mermaid"

#: How a section departs from its kind's structure.
MISSING, OUT_OF_ORDER = "missing", "out-of-order"

_SCHEMA_FILE = Path(__file__).resolve().parents[2] / PAGE_KINDS_SCHEMA

_ATX = re.compile(r"^(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_CLOSING = re.compile(r"(?:^|[ \t]+)#+$")
#: What may stand before a fence on its line: indentation and block-quote markers,
#: and before an opening one list markers too.
_QUOTED = r"[ \t]*(?:>[ \t]*)*"
_FENCE = re.compile(
    rf"^{_QUOTED}(?:(?:[-+*]|[0-9]{{1,9}}[.)])[ \t]+(?:>[ \t]*)*)*(`{{3,}}|~{{3,}})(.*)$"
)
_COMMENT = re.compile(r"^[ \t]*<!--(.*)$")
_COMMENT_END = "-->"
_FRONT_MATTER_FENCE = re.compile(r"^---[ \t]*$")
_PLACEHOLDER = re.compile(r"<[^<>]*>")
_TRAILING = re.compile(r"[\s.,:;!?]+$")
_QUOTE_PREFIX = re.compile(_QUOTED)
_ACC_TITLE = re.compile(r"^accTitle[ \t]*:(.*)$")
_ACC_DESCR = re.compile(r"^accDescr[ \t]*:(.*)$")
_ACC_DESCR_BLOCK = re.compile(r"^accDescr[ \t]*\{(.*)$")


class Unreadable(Exception):
    """The kinds' declaration gives no reading; the message says why."""


@dataclass(frozen=True)
class Section:
    """One section a kind declares: a heading's level and, when the kind fixes its
    wording, its text."""

    level: int
    text: str | None = None

    def matches(self, heading: Heading) -> bool:
        if heading.level != self.level:
            return False
        if self.text is None:
            return heading.worded
        return _comparable(heading.text) == _comparable(self.text)

    def described(self) -> str:
        """The section as a writer writes it."""
        marks = "#" * self.level
        if self.text is not None:
            return f"the section `{marks} {self.text}`"
        if self.level == 1:
            return f"a title written as `{marks} Title`"
        return f"a section written as `{marks} Heading`"


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

    @property
    def worded(self) -> bool:
        """Whether the heading says something of its own: it is not empty, and not a
        template's `<placeholder>` left unfilled."""
        return bool(self.text) and _PLACEHOLDER.fullmatch(self.text) is None


@dataclass(frozen=True)
class Fence:
    """A fenced code block of a page's body: its info string, the line it opens on,
    and the lines it holds, each without the indentation and block-quote markers
    before it."""

    info: str
    line: int
    lines: tuple[str, ...]

    @property
    def language(self) -> str:
        """The info string's first word, or nothing."""
        words = self.info.split()
        return words[0] if words else ""


@dataclass(frozen=True)
class Diagram:
    """A `mermaid` fence of a page's body, at `line`, and whether it carries each
    half of its text alternative (RS-LDOC-008)."""

    line: int
    titled: bool
    described: bool

    @property
    def lacking(self) -> tuple[str, ...]:
        """What its text alternative lacks: `accTitle`, `accDescr`, both or neither."""
        return tuple(
            name
            for name, present in (("accTitle", self.titled), ("accDescr", self.described))
            if not present
        )


@dataclass(frozen=True)
class Departure:
    """A declared section a page lacks, or carries out of order — then at `line`,
    where the page first carries it."""

    section: Section
    how: str  # MISSING or OUT_OF_ORDER
    line: int | None = None


def read_structures(path: Path) -> dict[str, Structure]:
    """Each kind's declared structure, from the declaration at `path`, read whole.
    Raises `Unreadable` when the file is absent, is not YAML, or does not fit the
    declaration's schema."""
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise Unreadable(f"the file cannot be read ({exc.strerror or exc})") from exc
    except UnicodeDecodeError as exc:
        raise Unreadable("the file is not UTF-8 text") from exc
    except YAMLError as exc:
        raise Unreadable(f"the file is not YAML ({_yaml_problem(exc)})") from exc
    schema = Draft202012Validator(json.loads(_SCHEMA_FILE.read_text(encoding="utf-8")))
    errors = sorted(schema.iter_errors(data), key=lambda e: [str(s) for s in e.absolute_path])
    if errors:
        first = errors[0]
        pointer = "/" + "/".join(str(segment) for segment in first.absolute_path)
        raise Unreadable(
            f"the file does not fit {PAGE_KINDS_SCHEMA.as_posix()}: at `{pointer}`, {first.message}"
        )
    return {
        kind: Structure(
            sections=tuple(
                Section(item["level"], item["text"].strip() if "text" in item else None)
                for item in entry["sections"]
            ),
            ordered=entry.get("ordered", True),
        )
        for kind, entry in data["kinds"].items()
    }


def _yaml_problem(exc: YAMLError) -> str:
    if isinstance(exc, MarkedYAMLError) and exc.problem and exc.problem_mark is not None:
        return f"{exc.problem}, at line {exc.problem_mark.line + 1}"
    return "it does not parse"


def headings(text: str) -> list[Heading]:
    """The headings of a Markdown file's body, in order, each with its line in the
    file: what the module's opening says a section is."""
    return _read(text)[0]


def fences(text: str) -> list[Fence]:
    """The fenced code blocks of a Markdown file's body, in order: what the module's
    opening says hides a line, outside an HTML comment."""
    return _read(text)[1]


def diagrams(text: str) -> list[Diagram]:
    """The diagrams of a Markdown file's body, in order, each with what it carries
    of its text alternative: what the module's opening says a diagram is."""
    return [_alternative(fence) for fence in fences(text) if fence.language == MERMAID]


def _read(text: str) -> tuple[list[Heading], list[Fence]]:
    """The headings and the fenced code blocks of a Markdown file's body, each in order."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    found: list[Heading] = []
    blocks: list[Fence] = []
    fence: tuple[str, int] | None = None  # the open fence's character and length
    opened: tuple[str, int] = ("", 0)  # the open fence's info string and line
    held: list[str] = []
    in_comment = False
    for index in range(_body_start(lines), len(lines)):
        line = lines[index]
        if fence is not None:
            if _closes(line, fence):
                blocks.append(Fence(opened[0], opened[1], tuple(held)))
                fence = None
            else:
                held.append(_QUOTE_PREFIX.sub("", line, count=1))
            continue
        if in_comment:
            in_comment = _COMMENT_END not in line
            continue
        opening = _FENCE.match(line)
        if opening is not None and not (
            opening.group(1).startswith("`") and "`" in opening.group(2)
        ):
            fence = (opening.group(1)[0], len(opening.group(1)))
            opened, held = (opening.group(2).strip(), index + 1), []
            continue
        comment = _COMMENT.match(line)
        if comment is not None:
            in_comment = _COMMENT_END not in comment.group(1)
            continue
        atx = _ATX.match(line)
        if atx is not None:
            raw = (atx.group(2) or "").strip()
            found.append(Heading(len(atx.group(1)), _CLOSING.sub("", raw).strip(), index + 1))
    if fence is not None:  # a fence never closed runs to the end of the file
        blocks.append(Fence(opened[0], opened[1], tuple(held)))
    return found, blocks


def _alternative(fence: Fence) -> Diagram:
    """What a `mermaid` fence carries of its text alternative: an `accTitle` and an
    `accDescr`, each followed by text that is not blank."""
    titled = described = False
    block: list[str] | None = None  # an `accDescr {` block's text, while it is open
    for line in fence.lines:
        if block is not None:
            closing = line.find("}")
            block.append(line if closing < 0 else line[:closing])
            if closing >= 0:
                described = described or bool("".join(block).strip())
                block = None
            continue
        stripped = line.strip()
        title = _ACC_TITLE.match(stripped)
        if title is not None:
            titled = titled or bool(title.group(1).strip())
            continue
        description = _ACC_DESCR.match(stripped)
        if description is not None:
            described = described or bool(description.group(1).strip())
            continue
        opening = _ACC_DESCR_BLOCK.match(stripped)
        if opening is not None:
            rest = opening.group(1)
            closing = rest.find("}")
            if closing >= 0:
                described = described or bool(rest[:closing].strip())
            else:
                block = [rest]
    return Diagram(fence.line, titled, described)


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
    return re.match(rf"^{_QUOTED}{re.escape(char)}{{{length},}}[ \t]*$", line) is not None


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
