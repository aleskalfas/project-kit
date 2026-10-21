"""An analysis body against its kind's declared structure (DEC-001 point 1; RS-SAN-001).

Each kind's structure is declared once, as data, in this capability's
`schemas/artefact-kinds.yaml`, and read here whole, held to its schema; a
template's text is never read for it. This module reads the declaration and
judges a body's lines against one kind. Which bodies it is given, and whether
what it finds binds, is the check's (`_lib/check.py`): the structure binds at
the status of the format rule, RS-SAN-001.

What a body is made of, precisely:

- **Its lines.** A document's body is its file below the front matter. A
  collection entry's is the lines of its section that the backbone's reading
  gives (`span`), and the collection file's head is its body above the first
  entry's section.
- **What hides a line from the marks.** A fenced code block opens on a line of
  three or more backticks or tildes, at any indentation and after block-quote
  and list markers, and closes on a line holding only as many of the same
  character or more. An HTML comment runs from a `<!--` to the next `-->`, on
  its line or a later one. A `<!--` inside a code span that closes on its line
  opens none, and one in a code span that runs on to the next line does. Code
  is content, and a comment is not.
- **A heading:** a line that opens, with no space before it, with one to six
  `#`, then a space, a tab or the line's end. Its level is the number of `#`,
  and its text the rest of the line without a closing run of `#`.
- **A label:** a bold run, `**<text>:**`, that opens a line with no space
  before it, or opens a top-level list item (`-`, `*`, `+`, or a number and
  `.` or `)`), and whose text the kind declares. Only a declared label is
  one: a bold run the kind does not declare, such as a variant's `**2a.**`, is
  content. Below a label that opens a list item, the part's list is the one
  nested in that item (`_lib/forms.py`).
- **Text is compared** ignoring case, runs of white space and trailing
  punctuation, as living-docs compares a heading.
- **A part's extent.** A label sits one level below the heading it follows. Its
  part runs from the label, the rest of its line included, to the next
  declared label or to a heading of the label's level or above. A heading's
  part runs to the next declared label or to a heading of its level or above.
  An opening runs from below the element listed before it, or from the body's
  start, to the next heading or declared label.
- **A label right before an opening** holds its paragraph alone: its part ends
  at the first blank line below it, outside fenced code and comments, and the
  opening runs from there. So a domain-model view's *Why* and the explanation
  below it are two parts, the explanation with no label (DEC-004 point 2).
- **A part's content:** what it holds besides its label, with comments and
  white space left out.

How a body departs from its kind's structure:

- **missing:** a required element no heading or label of its own is left for
  (one with fixed text chooses first, as it matches fewer), or an opening with
  no content.
- **out of order:** in an ordered structure, an element the body carries only
  before the one listed ahead of it, as living-docs' `formats.departures`.
- **empty:** a part a writer fills, one with a hint, whose content is nothing.
  A heading the stamp writes has no hint, and no content of its own.
- **`None.` refused:** a part whose content is `None.` and nothing else, where
  its element does not allow it, and a front-matter field's text that is
  `None.`, where the field refuses it (`Field.allows_none` false), such as a
  requirement's `applies-to`. A field that allows it, such as a requirement's
  `measure`, is not judged against its form while it reads `None.`. A field that
  says neither is judged by its form alone.
- **not one sentence:** text of the `sentence` form, in a part or in a
  front-matter field, in which a sentence ends before its last word. A part
  is one text, and each item of a front-matter list is one.
- **breaks its form:** a part or a front-matter field that does not hold any
  other form its element names, such as `numbered-steps` or `definition`, and
  a part of the `sentence` form that holds a list. Each breach is its own
  departure, at the line of the item it is in.
- **an undeclared label:** where a project's rule closes the kind's list of
  labels (`Kind.closed`, `_lib/project_structure.py`), a bold run ending in a
  colon that opens a line or a top-level list item, and that no element
  declares, outside a part with a form, fenced code and comments.

The elements are the kind's as it ships them, or as a project's own structure
relabels and tightens them (`_lib/project_structure.py`): an element a project
adds, or makes required, names the rule that asks for it (`Element.rule`).

**A repeated section** (`REPEATED`) is a domain-model view's section for each
concept it explains (DEC-004 point 2): every heading of its level opens one,
which runs to the next. Each is read as a body of its own, its heading then its
parts, and the body above the first is read against the elements before it. The
headings themselves are held to the section's form against the front matter's
`explains` (`forms.headings_match`). A departure inside one names its heading
(`Departure.within`).

What each form reads, and how a part's list is read, is `_lib/forms.py`'s.
Labels and sections a writer adds are never reported: the check judges only
the declared elements. What a writer adds inside a part is that part's
content, though, so it counts toward a `sentence` part's one sentence. A list
form judges only the part's list items, so a line a writer adds outside them
never breaks it.

**A hint left in** (`hints`) is a comment that opens with the hint's mark,
`<!-- pkit:hint`, which the stamp writes as each part's placeholder, and as
the text of each front-matter field a writer fills (`_lib/render.py`). It is
found as a comment is, outside fenced code and outside a code span that
closes on its line, so a body may quote the mark. A mark inside another
comment opens no hint. A field's text is read the same way (`hint_in`).
The placeholder check reports a hint left in whatever the format rule's
status, as it reports any placeholder (DEC-001 point 1). So a field's text
that still holds its hint is never judged against the field's form here.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError, YAMLError

from _lib import forms
from _lib.forms import BREAKS_FORM, NONE, NOT_A_SENTENCE

#: Where each kind's structure is declared, and the schema the declaration fits.
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
KINDS_FILE = SCHEMAS / "artefact-kinds.yaml"
KINDS_SCHEMA = SCHEMAS / "artefact-kinds.schema.json"

#: The kind of a revalidation record, which has no type of its own (DEC-001 point 2).
RECORD = "revalidation-record"

#: The use-case kind, and the permanent id of its part that names what holds before it
#: starts, each line opening with its producers (DEC-001 point 1).
USE_CASE_KIND, PRECONDITIONS = "use-case", "preconditions"

#: An element's types. A repeated section holds parts of its own, once for each entry of
#: a front-matter list (DEC-004 point 2).
HEADING, LABEL, OPENING, REPEATED = "heading", "label", "opening", "repeated"

#: How a body departs from its kind's structure: its parts, and then their forms
#: (`_lib/forms.py`), the `sentence` form's own breach and every other form's.
MISSING, OUT_OF_ORDER, EMPTY, NONE_REFUSED = ("missing", "out-of-order", "empty", "none-refused")

#: A label the kind does not declare, where a project's rule closes its list of labels.
UNDECLARED = "undeclared-label"
FORM_BREACHES = frozenset({NOT_A_SENTENCE, BREAKS_FORM})

#: One line of a body: its number in the file, counted from 1, and its text.
Line = tuple[int, str]

_ATX = re.compile(r"^(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_CLOSING = re.compile(r"(?:^|[ \t]+)#+$")
_QUOTED = r"[ \t]*(?:>[ \t]*)*"
_FENCE = re.compile(
    rf"^{_QUOTED}(?:(?:[-+*]|[0-9]{{1,9}}[.)])[ \t]+(?:>[ \t]*)*)*(`{{3,}}|~{{3,}})(.*)$"
)
_LABEL = re.compile(
    r"^(?P<item>(?:[-+*]|[0-9]{1,9}[.)])[ \t]+)?\*\*(?P<text>[^*\n]+?)\*\*(?P<rest>.*)$"
)
_COMMENT_OPEN, _COMMENT_CLOSE = "<!--", "-->"
_HINT = re.compile(r"<!--[ \t]*pkit:hint\b(?P<said>.*?)(?:-->|$)")
_TRAILING = re.compile(r"[\s.,:;!?]+$")
_PLACEHOLDER = re.compile(r"<[^<>]*>")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1", re.DOTALL)
_FRONT_MATTER_FENCE = re.compile(r"^---[ \t]*$")


class Unreadable(Exception):
    """The declaration gives no reading; the message says why."""


@dataclass(frozen=True)
class Element:
    """One element a kind declares: a heading, a label or an opening, with what a writer
    is told of it. A collection's file head declares no hint, so its `example` is the
    words the stamp writes. `rule` is the project rule that adds the element, or makes
    it required (`_lib/project_structure.py`); `None` for a part as the kind ships it.
    `added` says the project added the element, rather than requiring a shipped one.
    `aliases` are the texts a project relabelled it from, which a body written before
    the relabel may carry (`Kind.as_written`). A repeated section's `parts` are the
    elements each of its sections holds, in order (DEC-004 point 2)."""

    id: str
    type: str
    level: int | None = None
    text: str | None = None
    required: bool = True
    allows_none: bool = False
    form: str | None = None
    hint: str | None = None
    example: str | None = None
    rule: str | None = None
    added: bool = False
    aliases: tuple[str, ...] = ()
    parts: tuple[Element, ...] = ()

    @property
    def filled(self) -> bool:
        """Whether a writer fills the part: an opening always, and a heading or a label
        that has a hint. A heading the stamp writes has none, and a repeated section's
        headings are the stamp's too: its parts are what a writer fills."""
        return self.type == OPENING or (self.hint is not None and self.type != REPEATED)


@dataclass(frozen=True)
class Field:
    """One front-matter field a writer fills, with its hint, its example, any form, and
    whether it may read `None.` (DEC-001 point 1; DEC-002 point 4): true, it may, false,
    it may not, and `None` where the field says neither, so its form alone judges it."""

    name: str
    hint: str
    example: str
    form: str | None = None
    allows_none: bool | None = None


@dataclass(frozen=True)
class Kind:
    """One kind's declared structure: its body's elements — a collection entry's
    section's — in order, whether that order binds, a collection file's head, the
    front-matter fields a writer fills, and the ids of the elements it retired.
    `shown_as` is the kind's name as its artefacts show it beside their id, such as a
    requirement's `Quality` (DEC-002 point 2), `None` for a kind that shows none.

    A project's own structure changes it (`_lib/project_structure.py`). `closed` names
    the rules that close its list of labels. `delimiting` are the labels of parts a
    project adds that do not bind on the body, which still end the part before them, so
    a part that binds nothing never makes another fail. `as_written` holds a body that
    may predate the project's changes, a record's or a withdrawn artefact's: a relabelled
    part is found by its earlier text too, and a closed list reports nothing."""

    name: str
    sections: tuple[Element, ...]
    ordered: bool = True
    head: tuple[Element, ...] = ()
    fields: tuple[Field, ...] = ()
    retired: frozenset[str] = frozenset()
    closed: tuple[str, ...] = ()
    delimiting: frozenset[str] = frozenset()
    as_written: bool = False
    shown_as: str | None = None

    @property
    def labels(self) -> frozenset[str]:
        """The texts of the labels that mark a part, as they are compared: those the kind
        declares, a repeated section's included, and those `delimiting` gives — with
        `as_written`, each relabelled label's earlier text too."""
        declared = [e for e in (*elements(self), *self.head) if e.type == LABEL and e.text]
        texts = {comparable(e.text or "") for e in declared}
        if self.as_written:
            texts |= {comparable(alias) for e in declared for alias in e.aliases}
        return frozenset(texts | self.delimiting)


@dataclass(frozen=True)
class Departure:
    """A declared element a body lacks, carries out of order, leaves empty, fills with
    `None.` where it may not, or fills with what breaks its form — at `line` of the
    file, where the body carries it, and with what exactly the form found (`detail`).
    `within` is the heading of the repeated section it lies in, where it lies in one."""

    element: Element
    how: str
    line: int | None = None
    detail: str = ""
    within: str | None = None


def elements(kind: Kind) -> tuple[Element, ...]:
    """Every element of `kind`'s body, in order: each repeated section followed by its
    parts. A collection's file head is not among them."""
    return tuple(found for element in kind.sections for found in (element, *element.parts))


def siblings(kind: Kind, element: Element) -> tuple[Element, ...]:
    """The elements `element` is listed among, as a message places it: the kind's body,
    or one section of a repeated section, its heading then its parts, such as the
    section of each concept a domain-model view explains (DEC-004 point 2)."""
    for repeated in kind.sections:
        if repeated.type != REPEATED:
            continue
        if element in repeated.parts or (element.type == HEADING and element.id == repeated.id):
            return section_elements(repeated)
    return kind.sections


def section_elements(repeated: Element) -> tuple[Element, ...]:
    """The elements of one section of a repeated section: its heading, which the stamp
    writes, then its parts."""
    return (Element(repeated.id, HEADING, level=repeated.level), *repeated.parts)


@dataclass(frozen=True)
class FieldDeparture:
    """A front-matter field's text that does not hold the field's form, at `pointer`,
    and what exactly it breaks (`detail`)."""

    field: Field
    how: str
    pointer: str
    text: str
    detail: str = ""


def read_kinds(path: Path = KINDS_FILE, schema: Path = KINDS_SCHEMA) -> dict[str, Kind]:
    """Each kind's declared structure, read whole from the declaration at `path`.
    Raises `Unreadable` when the file is absent, is not YAML, or does not fit its schema."""
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise Unreadable(f"it cannot be read ({exc.strerror or exc})") from exc
    except UnicodeDecodeError as exc:
        raise Unreadable("it is not UTF-8 text") from exc
    except YAMLError as exc:
        raise Unreadable(f"it is not YAML ({_yaml_problem(exc)})") from exc
    try:
        validator = Draft202012Validator(json.loads(schema.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise Unreadable(f"its schema, {schema.name}, cannot be read ({exc})") from exc
    errors = sorted(validator.iter_errors(data), key=lambda e: [str(s) for s in e.absolute_path])
    if errors:
        first = errors[0]
        pointer = "".join(f"/{segment}" for segment in first.absolute_path)
        raise Unreadable(f"it does not fit {schema.name}: at `{pointer or '/'}`, {first.message}")
    return {name: _kind(name, entry) for name, entry in data["kinds"].items()}


def _kind(name: str, entry: Mapping[str, Any]) -> Kind:
    fields = entry.get("front-matter") or {}
    return Kind(
        name=name,
        sections=tuple(_element(item) for item in entry["sections"]),
        ordered=entry.get("ordered", True),
        head=tuple(_element(item, head=True) for item in entry.get("head") or ()),
        fields=tuple(
            Field(
                field,
                value["hint"],
                value["example"],
                value.get("form"),
                value.get("allows-none"),
            )
            for field, value in fields.items()
        ),
        retired=frozenset(entry.get("retired") or ()),
        shown_as=entry.get("shown-as"),
    )


def _element(item: Mapping[str, Any], *, head: bool = False) -> Element:
    text = item.get("text")
    return Element(
        id=item.get("id", ""),
        type=item.get("type", HEADING),
        level=item.get("level"),
        text=text.strip() if isinstance(text, str) else None,
        required=item.get("required", True),
        allows_none=item.get("allows-none", False),
        form=item.get("form"),
        hint=item.get("hint"),
        example=item.get("stamp") if head else item.get("example"),
        parts=tuple(_element(part) for part in item.get("sections") or ()),
    )


def _yaml_problem(exc: YAMLError) -> str:
    if isinstance(exc, MarkedYAMLError) and exc.problem and exc.problem_mark is not None:
        return f"{exc.problem}, at line {exc.problem_mark.line + 1}"
    return "it does not parse"


# --- a body's lines -------------------------------------------------------------------------


def body_lines(text: str) -> list[Line]:
    """A document's body: its file's lines below the front matter — a leading `---` line
    closed by the next `---` line — each with its number in the file."""
    lines = _lines(text)
    start = 0
    if lines and lines[0].rstrip() == "---":
        closing = next(
            (i for i in range(1, len(lines)) if _FRONT_MATTER_FENCE.match(lines[i])), None
        )
        start = 0 if closing is None else closing + 1
    return [(index + 1, lines[index]) for index in range(start, len(lines))]


def span_lines(text: str, span: tuple[int, int]) -> list[Line]:
    """The lines a span names, `(first, last)` counted from 1 and both included, each with
    its number — as the backbone counts them, every line break read as `\\n`."""
    lines = _lines(text)
    first, last = span
    return [(number, lines[number - 1]) for number in range(first, min(last, len(lines)) + 1)]


def _lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


@dataclass(frozen=True)
class _Mark:
    """A heading, or a declared label, at `index` among a body's lines — a label with
    the text after it on its line, `rest`, and the indentation of the list item it
    opens, `offset`, 0 where it opens a line."""

    index: int
    type: str
    level: int
    text: str
    rest: str = ""
    offset: int = 0


@dataclass(frozen=True)
class _Body:
    """A body read: each line's number and its content — the line with comments left out,
    a fenced line whole — whether fenced code opens on it or holds it (`forms.OPENS_FENCE`,
    `forms.IN_FENCE`), and its marks, in order. `blanks` says of each line whether it ends a
    paragraph: blank as written, outside fenced code and outside a comment."""

    numbers: tuple[int, ...]
    content: tuple[str, ...]
    marks: tuple[_Mark, ...]
    fences: tuple[int, ...] = ()
    blanks: tuple[bool, ...] = ()


def _read(lines: Sequence[Line], labels: frozenset[str]) -> _Body:
    content: list[str] = []
    fences: list[int] = []
    blanks: list[bool] = []
    marks: list[_Mark] = []
    fence: tuple[str, int] | None = None
    in_comment = False
    heading_level = 0
    for index, (_number, line) in enumerate(lines):
        if fence is not None:
            content.append(line)
            fences.append(forms.IN_FENCE)
            blanks.append(False)
            if _closes(line, fence):
                fence = None
            continue
        started_in_comment = in_comment
        visible, in_comment = _without_comments(line, in_comment)
        content.append(visible)
        fences.append(0)
        blanks.append(not line.strip() and not started_in_comment)
        if started_in_comment:
            continue
        opening = _FENCE.match(visible)
        if opening is not None and not (
            opening.group(1).startswith("`") and "`" in opening.group(2)
        ):
            fence = (opening.group(1)[0], len(opening.group(1)))
            content[-1] = line
            fences[-1] = forms.OPENS_FENCE
            continue
        atx = _ATX.match(visible)
        if atx is not None:
            heading_level = len(atx.group(1))
            text = _CLOSING.sub("", (atx.group(2) or "").strip()).strip()
            marks.append(_Mark(index, HEADING, heading_level, text))
            continue
        label = _LABEL.match(visible)
        if label is not None and comparable(label["text"]) in labels:
            rest = label["rest"]
            rest = rest[1:] if rest.startswith(":") else rest
            offset = len((label["item"] or "").expandtabs(4))
            marks.append(_Mark(index, LABEL, heading_level + 1, label["text"], rest, offset))
    numbers = tuple(n for n, _ in lines)
    return _Body(numbers, tuple(content), tuple(marks), tuple(fences), tuple(blanks))


def _without_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    """The line with the text of HTML comments left out, and whether a comment is still
    open at its end."""
    visible, still_open, _openings = _scan(line, in_comment)
    return visible, still_open


def _scan(line: str, in_comment: bool) -> tuple[str, bool, list[int]]:
    """The one reading of a line's comments: the line with their text left out, whether
    a comment is still open at its end, and where each comment that opens on it opens.
    A comment still open from an earlier line hides what comes before its end."""
    kept: list[str] = []
    openings: list[int] = []
    at = 0
    while at <= len(line):
        if in_comment:
            end = line.find(_COMMENT_CLOSE, at)
            if end == -1:
                return "".join(kept), True, openings
            at, in_comment = end + len(_COMMENT_CLOSE), False
        else:
            start = _comment_opening(line, at)
            if start == -1:
                kept.append(line[at:])
                break
            kept.append(line[at:start])
            openings.append(start)
            at, in_comment = start + len(_COMMENT_OPEN), True
    return "".join(kept), in_comment, openings


def _comment_opening(line: str, at: int) -> int:
    """Where the next HTML comment opens on `line`, from `at`, outside a code span that
    closes on the line: a code span's text is literal, so a `<!--` quoted in one opens
    none. A code span that runs on to the next line is not seen here, so a `<!--` in it
    opens a comment. -1 when none opens."""
    spans = [match.span() for match in _CODE_SPAN.finditer(line, at)]
    start = line.find(_COMMENT_OPEN, at)
    while start != -1:
        inside = next((end for first, end in spans if first <= start < end), None)
        if inside is None:
            return start
        start = line.find(_COMMENT_OPEN, inside)
    return -1


def _closes(line: str, fence: tuple[str, int]) -> bool:
    char, length = fence
    return re.match(rf"^{_QUOTED}{re.escape(char)}{{{length},}}[ \t]*$", line) is not None


def hints(lines: Sequence[Line]) -> list[tuple[int, str]]:
    """Each hint left in a body's `lines`: the line it opens on, and what it says. A hint
    is a comment that opens with the hint's mark, found as `_read` finds a comment:
    outside fenced code, and outside a code span that closes on its line. A mark
    inside another comment opens none."""
    found: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    in_comment = False
    for number, line in lines:
        if fence is not None:
            if _closes(line, fence):
                fence = None
            continue
        started_in_comment = in_comment
        visible, in_comment, openings = _scan(line, in_comment)
        opening = None if started_in_comment else _FENCE.match(visible)
        if opening is not None and not (
            opening.group(1).startswith("`") and "`" in opening.group(2)
        ):
            fence = (opening.group(1)[0], len(opening.group(1)))
            continue
        marked = (_HINT.match(line, start) for start in openings)
        found += [(number, hint["said"].strip()) for hint in marked if hint is not None]
    return found


def hint_in(text: str) -> str | None:
    """What the first hint a front-matter field's `text` still holds says, found as
    `hints` finds one in a body, or `None` when it holds none."""
    found = hints(list(enumerate(text.splitlines(), 1)))
    return found[0][1] if found else None


def comparable(text: str) -> str:
    """A heading's or a label's text as it is compared: case, runs of white space and
    trailing punctuation ignored."""
    return _TRAILING.sub("", " ".join(text.split())).casefold()


# --- departures -----------------------------------------------------------------------------


def departures(
    lines: Sequence[Line],
    kind: Kind,
    *,
    head: bool = False,
    fields: Mapping[str, Any] | None = None,
    titles: Mapping[str, str] | None = None,
) -> list[Departure]:
    """How a body with `lines` departs from `kind`'s structure — its file head's, with
    `head` — in declared order: an element missing or out of order, once, and otherwise
    what its content breaks, each breach of its form at its own line. A form that
    matches the front matter reads `fields`, the artefact's or record's own, and a
    journey's steps read each use case's title in `titles`, by id, as a domain-model
    view's sections read each term's name. A kind with a repeated section is read one
    section at a time (`_repeating`)."""
    repeated = next((i for i, e in enumerate(kind.sections) if e.type == REPEATED), None)
    if not head and repeated is not None:
        return _repeating(lines, kind, repeated, fields, titles)
    elements = kind.head if head else kind.sections
    body = _read(lines, kind.labels)
    found, at = _located(body, elements, kind)
    carried = {i: part for i in range(len(elements)) if (part := _part(i, elements, at, body))}
    context = _context(elements, carried, fields, titles)
    for i, element in enumerate(elements):
        if i in found or not element.filled:
            continue
        part = carried.get(i)
        if part is None:
            if element.type == OPENING and element.required:
                found[i] = [Departure(element, MISSING)]
            continue
        breaches = judged(part, element, context)
        if breaches:
            found[i] = [Departure(element, b.how, b.line, b.detail) for b in breaches]
    undeclared = [] if head else _undeclared(body, kind, elements, carried)
    return [departure for i in sorted(found) for departure in found[i]] + undeclared


def _repeating(
    lines: Sequence[Line],
    kind: Kind,
    at: int,
    fields: Mapping[str, Any] | None,
    titles: Mapping[str, str] | None,
) -> list[Departure]:
    """How a body departs from a kind whose element at `at` is a repeated section, a
    domain-model view's section for each concept (DEC-004 point 2). Every heading of the
    section's level, outside fenced code and comments, opens one of its sections, which
    runs to the next. The lines above the first are held to the elements listed before
    the section, and each section to its heading and its parts, each departure in it
    naming its heading. The headings are held to the section's form, and a body with no
    such heading lacks the section."""
    repeated = kind.sections[at]
    body = _read(lines, frozenset())
    starts = [
        (mark.index, mark.text)
        for mark in body.marks
        if mark.type == HEADING and mark.level == repeated.level
    ]
    above = starts[0][0] if starts else len(lines)
    head = dataclasses.replace(kind, sections=kind.sections[:at])
    found = departures(lines[:above], head, fields=fields, titles=titles)
    section = dataclasses.replace(kind, sections=section_elements(repeated))
    for n, (start, text) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        found += [
            dataclasses.replace(departure, within=text)
            for departure in departures(lines[start:end], section, fields=fields, titles=titles)
            if not (departure.element.type == HEADING and departure.element.id == repeated.id)
        ]
    if not starts:
        return found + ([Departure(repeated, MISSING)] if repeated.required else [])
    headings = [(lines[start][0], text) for start, text in starts]
    found += [
        Departure(repeated, b.how, b.line, b.detail)
        for b in forms.headings_match(headings, forms.Context(fields or {}, titles or {}))
    ]
    return found


def parts(lines: Sequence[Line], kind: Kind) -> list[tuple[Element, forms.Part]]:
    """Each part of `kind`'s body that a body with `lines` carries, with its element, in
    declared order, found as `departures` finds it for the same kind. The append-only
    check reads a use case's steps and variants here (`_lib/append_only.py`), with a kind
    of its own making (`append_only._kind`)."""
    elements = kind.sections
    body = _read(lines, kind.labels)
    _found, at = _located(body, elements, kind)
    return [
        (elements[i], part)
        for i in range(len(elements))
        if (part := _part(i, elements, at, body)) is not None
    ]


def _located(
    body: _Body, elements: Sequence[Element], kind: Kind
) -> tuple[dict[int, list[Departure]], dict[int, int]]:
    """Where a body carries each element that a mark opens, by its index among `elements`:
    the mark it takes, and, in an ordered structure, the first after the element listed
    ahead of it. Returns the elements missing or out of order, with their departure, and
    the mark each element takes."""
    marked = [i for i, e in enumerate(elements) if e.type != OPENING]
    taken = _taken(body.marks, elements, marked, kind.as_written)
    found: dict[int, list[Departure]] = {
        i: [Departure(elements[i], MISSING)]
        for i in marked
        if i not in taken and elements[i].required
    }
    at: dict[int, int] = dict(taken)
    if kind.ordered:
        after = 0
        for i in marked:
            if i not in taken:
                continue
            nxt = next(
                (
                    m
                    for m in range(after, len(body.marks))
                    if _matches(elements[i], body.marks[m], kind.as_written)
                ),
                None,
            )
            if nxt is None:
                line = body.numbers[body.marks[at[i]].index]
                found[i] = [Departure(elements[i], OUT_OF_ORDER, line)]
            else:
                at[i], after = nxt, nxt + 1
    return found, at


def _undeclared(
    body: _Body, kind: Kind, elements: Sequence[Element], parts: Mapping[int, forms.Part]
) -> list[Departure]:
    """Where a project's rule closes the kind's list of labels (`kind.closed`), each bold
    run ending in a colon that opens a line or a top-level list item and that no element
    declares, outside fenced code and comments, as a label is read. A part with a form
    is not read for it, so a step's or a seam's bold run stays content. Nor is a
    precondition's opening in a use case's *Preconditions*, which names its producers,
    such as `**From UC-003:**` (DEC-001 point 1)."""
    if not kind.closed or kind.as_written:
        return []
    formed = {
        number
        for i, part in parts.items()
        if elements[i].form is not None
        for number in (part.line, *(row.number for row in part.rows))
    }
    producing = {
        number
        for i, part in parts.items()
        if kind.name == USE_CASE_KIND and elements[i].id == PRECONDITIONS and not elements[i].added
        for number in (part.line, *(row.number for row in part.rows))
    }
    found: list[Departure] = []
    for k, content in enumerate(body.content):
        if body.fences and body.fences[k]:
            continue
        label = _LABEL.match(content)
        if label is None or body.numbers[k] in formed:
            continue
        text = label["text"]
        if not (text.rstrip().endswith(":") or label["rest"].startswith(":")):
            continue
        if comparable(text) in kind.labels:
            continue
        if body.numbers[k] in producing and forms.named_producers(text, label["rest"]):
            continue
        shown = Element("", LABEL, text=text.rstrip().rstrip(":").strip(), rule=kind.closed[0])
        found.append(Departure(shown, UNDECLARED, body.numbers[k], ", ".join(kind.closed)))
    return found


def _part(
    i: int, elements: Sequence[Element], at: Mapping[int, int], body: _Body
) -> forms.Part | None:
    """The part of the element at `i` that the body carries: a label's or a heading's
    lines, the label's line first, or an opening's, which holds text; `None` where the
    body carries none."""
    if elements[i].type == OPENING:
        extent = _until_next_mark(_after_previous(i, elements, at, body), body)
        texts = [k for k in extent if body.content[k].strip()]
        if not texts:
            return None
        return forms.Part(body.numbers[texts[0]], _rows(body, extent))
    if i not in at:
        return None
    mark = body.marks[at[i]]
    line = body.numbers[mark.index]
    lead = forms.Row(line, mark.rest) if mark.type == LABEL else None
    item = body.content[mark.index] if mark.offset else ""
    extent = _extent(mark, body, paragraph=_before_opening(i, elements))
    return forms.Part(line, _rows(body, extent), lead, item)


def _before_opening(i: int, elements: Sequence[Element]) -> bool:
    """Whether the element at `i` is a label listed right before an opening, which holds
    its paragraph alone, such as a domain-model view's *Why* (DEC-004 point 2)."""
    return elements[i].type == LABEL and i + 1 < len(elements) and elements[i + 1].type == OPENING


def _rows(body: _Body, extent: range) -> tuple[forms.Row, ...]:
    """The lines of `extent` as a part's rows, each with its fence mark."""
    return tuple(
        forms.Row(body.numbers[k], body.content[k], body.fences[k] if body.fences else 0)
        for k in extent
    )


def _context(
    elements: Sequence[Element],
    parts: Mapping[int, forms.Part],
    fields: Mapping[str, Any] | None,
    titles: Mapping[str, str] | None,
) -> forms.Context:
    """What the forms read besides each part: the front matter, the use cases' titles, and
    the steps a variant branches from, those of the part whose form lists steps. A steps
    part with no numbered step is reported itself, so no variant is held to it."""
    steps: frozenset[int] | None = None
    named = "the steps"
    for i, element in enumerate(elements):
        if element.form in forms.STEP_FORMS and not element.added and i in parts:
            steps = forms.step_numbers(parts[i]) or None
            named = f"`**{element.text}:**`" if element.type == LABEL else f"`{element.text}`"
            break
    return forms.Context(fields or {}, titles or {}, steps, named)


def judged(part: forms.Part, element: Element, context: forms.Context) -> list[forms.Breach]:
    """What a part's content breaks — empty, `None.` where its element refuses it, or
    its form — each breach at its line; none when it holds."""
    flat = " ".join(part.text.split())
    if not flat:
        return [forms.Breach(EMPTY, part.line)]
    if flat == NONE:
        if not element.allows_none:
            return [forms.Breach(NONE_REFUSED, part.line)]
        return forms.judge_none(element.form, part, context)
    return forms.judge(element.form, part, context)


def field_departures(fields: Mapping[str, Any], kind: Kind) -> list[FieldDeparture]:
    """Each text of a front-matter field that reads `None.` where the field refuses it, or
    does not hold the field's form: the field's own text, or each item of a list. A field
    that allows `None.` and reads it is not judged against its form, and one that says
    neither is judged by its form alone. A value of another shape is the kind's schema's
    to report."""
    found: list[FieldDeparture] = []
    for field in kind.fields:
        value = fields.get(field.name)
        for pointer, text in _texts(field.name, value):
            if not text.strip() or hint_in(text) is not None:
                continue  # a hint left in is the placeholder check's
            if field.allows_none is not None and " ".join(text.split()) == NONE:
                if not field.allows_none:
                    found.append(FieldDeparture(field, NONE_REFUSED, pointer, text))
                continue
            if field.form is None:
                continue
            breach = forms.field_breach(field.form, text, fields)
            if breach is not None:
                how, detail = breach
                found.append(FieldDeparture(field, how, pointer, text, detail))
    return found


def _texts(name: str, value: object) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield f"/{name}", value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, str):
                yield f"/{name}/{index}", item


def _matches(element: Element, mark: _Mark, as_written: bool = False) -> bool:
    """Whether `mark` is the element's: its text, or, `as_written`, an earlier text."""
    texts = {comparable(element.text or "")}
    if as_written:
        texts |= {comparable(alias) for alias in element.aliases}
    if element.type == LABEL:
        return mark.type == LABEL and comparable(mark.text) in texts
    if element.type != HEADING or mark.type != HEADING or mark.level != element.level:
        return False
    if element.text is None:
        return bool(mark.text) and _PLACEHOLDER.fullmatch(mark.text) is None
    return comparable(mark.text) in texts


def _taken(
    marks: Sequence[_Mark],
    elements: Sequence[Element],
    marked: Sequence[int],
    as_written: bool = False,
) -> dict[int, int]:
    """The mark each element takes, by index — one of its own, elements with fixed text
    choosing first, as they match fewer; an element no mark is left for takes none."""
    taken: dict[int, int] = {}
    for i in sorted(marked, key=lambda i: elements[i].text is None):
        free = (m for m in range(len(marks)) if m not in taken.values())
        chosen = next((m for m in free if _matches(elements[i], marks[m], as_written)), None)
        if chosen is not None:
            taken[i] = chosen
    return taken


def _extent(mark: _Mark, body: _Body, *, paragraph: bool = False) -> range:
    """The lines below a mark that its part holds: to the next declared label, or to a
    heading of the mark's level or above. With `paragraph`, a label right before an
    opening, it ends sooner at the first blank line outside fenced code and comments."""
    end = len(body.content)
    for other in body.marks:
        if other.index <= mark.index:
            continue
        if other.type == LABEL or other.level <= mark.level:
            end = other.index
            break
    if paragraph:
        end = next((k for k in range(mark.index + 1, end) if body.blanks[k]), end)
    return range(mark.index + 1, end)


def _after_previous(i: int, elements: Sequence[Element], at: Mapping[int, int], body: _Body) -> int:
    """The line an opening starts at: below the mark of the nearest element listed before
    it that the body carries, or the body's first. Below a label listed right before it,
    the opening starts after the label's paragraph."""
    for previous in range(i - 1, -1, -1):
        if previous in at:
            mark = body.marks[at[previous]]
            if _before_opening(previous, elements):
                return _extent(mark, body, paragraph=True).stop
            return mark.index + 1
    return 0


def _until_next_mark(start: int, body: _Body) -> range:
    end = next((m.index for m in body.marks if m.index >= start), len(body.content))
    return range(start, end)
