"""Where a part of a document lies (ADR-057 point 2).

The one reading of a Markdown document's body. Every module of the binary
that cuts a part of a document calls it, so they all find the same parts:

- `split_front_matter` — a text's front matter and its body, line breaks read
  universally (`universal_newlines`), so a file written with `\\r\\n` has the
  body the same file written with `\\n` has. `parse_front_matter` parses the
  front matter too, and says why it does not parse (`yaml_reason`).
  `body_first_line` is the line of the text the body opens on, from which a
  part's lines are counted.
- `Body` — a body read once: its headings outside fenced code
  (`body_headings`), and where each part lies, as an `Extent` of the body:
  - **a section** runs from its heading to the next heading of the same or a
    higher level (`Body.section`). It is found by its id, the first heading
    that opens with the id as a whole token (`Body.section_by_id`,
    `heading_opens_with`), or by its slug (`Body.sections_by_slug`,
    `heading_slug`), which may name more than one heading.
  - **the lead** is the body before its first heading, not counting a
    first-level heading that opens it (`Body.lead`). Such a title is part of
    the lead's text.
  - a part's text (`Body.text_of`) and the lines of the file it spans
    (`Body.span_of`), from the same extent, so a reader of the span reads
    exactly the text that is compared.

Artefact discovery cuts a collection entry's section with it
(`friction_discovery`), and the rule-set reader lists a rule-set file's sections
with it (`rule_sets`). The home of a record's points reads a record's
Decision with it (`record_points`).

An artefact anchor may name a document's section by its heading's slug, or its
lead by a bare `#` (COR-050 point 2). The one reading of such an anchor
(`artefact_parts`) finds the section by `sections_by_slug` and the lead by
`lead`, here, so the checks, validation and the artefacts document cut the same
part (ADR-057 point 2).
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit.backbone_schemas import as_written
from project_kit.line_breaks import universal_newlines

_FRONT_MATTER_FENCE = re.compile(r"^---[ \t]*$", re.MULTILINE)

# A line opening fenced code, or closing it: three backticks or three tildes,
# indented at most three spaces.
_CODE_FENCE = re.compile(r"^[ \t]{0,3}(```|~~~)")

# An ATX heading: its `#`s, then its title, any closing `#`s left out.
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")

# What continues an id past a heading's opening characters: a word character, or a hyphen or
# a dot joined to one — so `uc-login` is not the id opening `uc-login-sso` or `uc-login.v2`.
_ID_CONTINUES = re.compile(r"\w|[-.]\w")

# ruamel.yaml is untyped; the loaded value is judged where it is read.
_yaml: Any = YAML(typ="safe")


def split_front_matter(text: str) -> tuple[str | None, str]:
    """(front-matter YAML, body) for a Markdown text; `(None, text)` when it has none.

    Front matter is a leading `---` line closed by the next `---` line. Line
    endings are read universally first (`universal_newlines`), so a text
    written with `\\r\\n` has the front matter the same text written with `\\n`
    has, and both parts — `text` too, when there is none — come back with `\\n`
    line breaks: the one reading of a file's front matter and body. The YAML
    is returned as text so the caller can report a parse failure against the
    file.
    """
    text = universal_newlines(text)
    if not text.startswith("---"):
        return None, text
    first_line_end = text.find("\n")
    if first_line_end == -1 or text[:first_line_end].rstrip() != "---":
        return None, text
    closing = _FRONT_MATTER_FENCE.search(text, first_line_end + 1)
    if closing is None:
        return None, text
    return text[first_line_end + 1 : closing.start()], text[closing.end() :].lstrip("\n")


def parse_front_matter(text: str) -> tuple[Mapping[str, Any] | None, str, str | None]:
    """A text's front matter as written when it is a mapping, its body, and why the
    front matter does not parse, if it does not: `(front_matter, body, reason)`.

    Both are read with `\\n` line breaks, whatever the text's
    (`split_front_matter`). Front matter that is absent, or not a mapping, gives
    `None` with no reason. YAML dates and non-text keys are rendered back to their
    written form (`backbone_schemas.as_written`).
    """
    front_matter, body = split_front_matter(text)
    if front_matter is None:
        return None, body, None
    try:
        data = _yaml.load(io.StringIO(front_matter))
    except YAMLError as exc:
        return None, body, yaml_reason(exc)
    except (TypeError, ValueError, KeyError) as exc:
        return None, body, _unbuilt(exc)
    if not isinstance(data, Mapping):
        return None, body, None
    return cast("Mapping[str, Any]", as_written(data)), body, None


def _unbuilt(exc: Exception) -> str:
    """Why YAML did not parse where ruamel fails outside its own errors: a complex key
    holding a mapping, `? [{a: 1}]`, is no key a mapping can hold (`TypeError`), and a
    tag on text it cannot convert, `!!int x` or `!!bool x`, builds no value (`ValueError`,
    `KeyError`)."""
    return f"cannot build a value from it: {type(exc).__name__}: {exc}"


def yaml_reason(exc: YAMLError) -> str:
    """Why YAML did not parse: the problem, with its line and column when it has them."""
    problem = getattr(exc, "problem", None) or next(iter(str(exc).splitlines()), "") or "invalid"
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        return f"{problem} at line {mark.line + 1} col {mark.column + 1}"
    return str(problem)


def body_first_line(text: str, body: str) -> int:
    """The line of `text` its body opens on, counted from 1.

    The body is a suffix of the text read with `\\n` line breaks, opening at a
    line's start (`split_front_matter`), so the line breaks before it are the
    text's less the body's own.
    """
    return universal_newlines(text).count("\n") - body.count("\n") + 1


@dataclass(frozen=True)
class Heading:
    """One heading of a Markdown body, outside fenced code."""

    level: int  # how many `#` open it
    title: str  # the text after them, stripped
    start: int  # where its line starts in the body


@dataclass(frozen=True)
class Line:
    """One line of a Markdown body outside fenced code, without its line break."""

    start: int  # where it starts in the body
    text: str


@dataclass(frozen=True)
class SectionSpan:
    """The lines of a file a part spans, counted from 1, both included.

    Lines are the file's text read with every line break as `\\n`
    (`split_front_matter`), so a file written with `\\r\\n` has the lines one
    written with `\\n` has. Joined with `\\n`, with one `\\n` after the last,
    they are the part's text (`Body.text_of`).
    """

    first_line: int
    last_line: int


@dataclass(frozen=True)
class Extent:
    """Where a part lies in a body.

    `start` is where its first line starts. `end` is the end of its text,
    before the line breaks that end it, so an empty part has `end == start`.
    `heading` is the heading that opens a section, and `None` for the lead.
    """

    start: int
    end: int
    heading: Heading | None = None


def _scan(body: str) -> Iterator[tuple[int, str, bool]]:
    """Every line of `body`: where it starts, its text, and whether it lies outside
    fenced code. A line that opens or closes a fence lies inside it.

    A line opening with three backticks or three tildes, indented at most three
    spaces, opens a fence. The next line opening with the same marker closes it,
    and a fence never closed runs to the end of the body.
    """
    fence: str | None = None
    start = 0
    for line in body.split("\n"):
        marker = _CODE_FENCE.match(line)
        if marker is not None:
            fence = None if fence == marker.group(1) else (fence or marker.group(1))
            yield start, line, False
        else:
            yield start, line, fence is None
        start += len(line) + 1


def body_headings(body: str) -> tuple[Heading, ...]:
    """The headings of a Markdown body, in order, fenced code skipped.

    The one reading of a body's sections. A heading inside fenced code opens no
    section and ends none, for any reader (`_scan` says where fenced code lies).
    """
    found: list[Heading] = []
    for start, line, outside in _scan(body):
        if outside:
            heading = _HEADING.match(line)
            if heading is not None:
                found.append(Heading(len(heading.group(1)), heading.group(2).strip(), start))
    return tuple(found)


def heading_opens_with(title: str, part_id: str) -> bool:
    """Whether a heading's title opens with `part_id` as a whole token.

    The id must be followed by the end of the title, whitespace, or
    punctuation that does not continue an id (`_ID_CONTINUES`).
    """
    return title.startswith(part_id) and not _ID_CONTINUES.match(title, len(part_id))


def heading_slug(title: str) -> str:
    """A heading's slug: its title in lower case, with every character but letters,
    digits, spaces and hyphens dropped, and each space made a hyphen.

    The rule is pkit's own, since Markdown hosts differ at the edges, such as two
    headings with one slug. A title made only of other characters has an empty
    slug, which names no heading.
    """
    kept = (ch for ch in title.lower() if ch.isalpha() or ch.isdigit() or ch in " -")
    return "".join(kept).replace(" ", "-")


@dataclass(frozen=True)
class Body:
    """A Markdown body read once: its text and its headings outside fenced code.

    Read it with `Body.read`. Every part is found from `headings`, so a heading
    inside fenced code is no part's heading and ends no part.
    """

    text: str
    headings: tuple[Heading, ...]

    @classmethod
    def read(cls, text: str) -> Body:
        """`text`, a body with `\\n` line breaks (`split_front_matter`), read once."""
        return cls(text, body_headings(text))

    def lines(self) -> Iterator[Line]:
        """Every line outside fenced code, in order. A fence's own lines are left out."""
        for start, line, outside in _scan(self.text):
            if outside:
                yield Line(start, line)

    def section(self, index: int) -> Extent:
        """The section the heading `headings[index]` opens: to the next heading of
        the same or a higher level, or to the end of the body."""
        heading = self.headings[index]
        end = next(
            (later.start for later in self.headings[index + 1 :] if later.level <= heading.level),
            len(self.text),
        )
        return self._extent(heading.start, end, heading)

    def section_by_id(self, part_id: str) -> Extent | None:
        """The section headed by `part_id`, or `None`: the first heading that opens
        with the id as a whole token (`heading_opens_with`) opens it."""
        for index, heading in enumerate(self.headings):
            if heading_opens_with(heading.title, part_id):
                return self.section(index)
        return None

    def sections_by_slug(self, slug: str) -> tuple[Extent, ...]:
        """Every section whose heading's slug is `slug` (`heading_slug`), in order.

        More than one makes the slug ambiguous, which is the caller's to judge.
        An empty slug names no heading.
        """
        if not slug:
            return ()
        return tuple(
            self.section(index)
            for index, heading in enumerate(self.headings)
            if heading_slug(heading.title) == slug
        )

    def lead(self) -> Extent:
        """The body before its first heading, not counting a first-level heading that
        opens it. The line breaks before it are left out, as those after it are.
        Empty when the body opens with any other heading."""
        headings = self.headings
        if headings and headings[0].level == 1 and not self.text[: headings[0].start].strip():
            headings = headings[1:]
        end = headings[0].start if headings else len(self.text)
        start = min(len(self.text) - len(self.text.lstrip("\n")), end)
        return self._extent(start, end, None)

    def text_of(self, extent: Extent) -> str:
        """A part's text: its lines, each followed by one line break; empty for an
        empty part."""
        if extent.end <= extent.start:
            return ""
        return self.text[extent.start : extent.end] + "\n"

    def span_of(self, extent: Extent, body_line: int) -> SectionSpan | None:
        """The lines of the file a part spans, or `None` for an empty part.

        `body_line` is the line of the file the body opens on (`body_first_line`).
        """
        if extent.end <= extent.start:
            return None
        first_line = body_line + self.text.count("\n", 0, extent.start)
        return SectionSpan(first_line, first_line + self.text.count("\n", extent.start, extent.end))

    def _extent(self, start: int, end: int, heading: Heading | None) -> Extent:
        """From `start` to `end`, the line breaks that end it left out."""
        return Extent(start, start + len(self.text[start:end].rstrip("\n")), heading)


def entry_section(body: str, entry_id: str) -> str:
    """The body section headed by `entry_id` (COR-050 point 1), or `""`.

    The first heading that opens with the id (`heading_opens_with`) opens the
    section. It runs to the next heading of the same or a higher level. Both
    are read by `body_headings`, so a heading inside fenced code is neither.
    The line breaks that end it are read as one.
    """
    read = Body.read(body)
    extent = read.section_by_id(entry_id)
    return "" if extent is None else read.text_of(extent)
