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
  content.
- **Text is compared** ignoring case, runs of white space and trailing
  punctuation, as living-docs compares a heading.
- **A part's extent.** A label sits one level below the heading it follows. Its
  part runs from the label, the rest of its line included, to the next
  declared label or to a heading of the label's level or above. A heading's
  part runs to the next declared label or to a heading of its level or above.
  An opening runs from below the element listed before it, or from the body's
  start, to the next heading or declared label.
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
  its element does not allow it.
- **not one sentence:** text of the `sentence` form, in a part or in each item
  of a front-matter field, in which a sentence ends before its last word. In a
  part that holds a list, each item holds the form on its own, and so do the
  text before the list and the text after it. A sentence ends at a full stop, a
  question mark or an exclamation mark, only where a space, a line end or the
  text's end follows it, and never inside a code span (RS-SAN-001's *How*).

Labels and sections a writer adds are never reported: the check judges only
the declared elements. What a writer adds inside a part is that part's
content, though, so it counts toward a `sentence` part's one sentence. The
other forms the declaration names are not read here yet.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError, YAMLError

#: Where each kind's structure is declared, and the schema the declaration fits.
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
KINDS_FILE = SCHEMAS / "artefact-kinds.yaml"
KINDS_SCHEMA = SCHEMAS / "artefact-kinds.schema.json"

#: The kind of a revalidation record, which has no type of its own (DEC-001 point 2).
RECORD = "revalidation-record"

#: An element's types, and the form this module reads.
HEADING, LABEL, OPENING = "heading", "label", "opening"
SENTENCE = "sentence"

#: What a part with nothing to say reads, where its element allows it.
NONE = "None."

#: How a body departs from its kind's structure.
MISSING, OUT_OF_ORDER, EMPTY, NONE_REFUSED, NOT_A_SENTENCE = (
    "missing",
    "out-of-order",
    "empty",
    "none-refused",
    "not-a-sentence",
)

#: One line of a body: its number in the file, counted from 1, and its text.
Line = tuple[int, str]

_ATX = re.compile(r"^(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_CLOSING = re.compile(r"(?:^|[ \t]+)#+$")
_QUOTED = r"[ \t]*(?:>[ \t]*)*"
_FENCE = re.compile(
    rf"^{_QUOTED}(?:(?:[-+*]|[0-9]{{1,9}}[.)])[ \t]+(?:>[ \t]*)*)*(`{{3,}}|~{{3,}})(.*)$"
)
_ITEM = re.compile(r"^[ \t]*(?:(?P<bullet>[-+*])|(?P<number>[0-9]{1,9})[.)])(?:[ \t]+|$)")
_LABEL = re.compile(r"^(?:(?:[-+*]|[0-9]{1,9}[.)])[ \t]+)?\*\*(?P<text>[^*\n]+?)\*\*(?P<rest>.*)$")
_COMMENT_OPEN, _COMMENT_CLOSE = "<!--", "-->"
_TRAILING = re.compile(r"[\s.,:;!?]+$")
_PLACEHOLDER = re.compile(r"<[^<>]*>")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1", re.DOTALL)
_SENTENCE_END = re.compile(r"[.?!](?=\s|$)")
_WORD = re.compile(r"\w")
_FRONT_MATTER_FENCE = re.compile(r"^---[ \t]*$")


class Unreadable(Exception):
    """The declaration gives no reading; the message says why."""


@dataclass(frozen=True)
class Element:
    """One element a kind declares: a heading, a label or an opening, with what a writer
    is told of it. A collection's file head declares no hint, so its `example` is the
    words the stamp writes."""

    id: str
    type: str
    level: int | None = None
    text: str | None = None
    required: bool = True
    allows_none: bool = False
    form: str | None = None
    hint: str | None = None
    example: str | None = None

    @property
    def filled(self) -> bool:
        """Whether a writer fills the part: an opening always, and a heading or a label
        that has a hint. A heading the stamp writes has none."""
        return self.type == OPENING or self.hint is not None


@dataclass(frozen=True)
class Field:
    """One front-matter field a writer fills, with its hint, its example and any form."""

    name: str
    hint: str
    example: str
    form: str | None = None


@dataclass(frozen=True)
class Kind:
    """One kind's declared structure: its body's elements — a collection entry's
    section's — in order, whether that order binds, a collection file's head, and the
    front-matter fields a writer fills."""

    name: str
    sections: tuple[Element, ...]
    ordered: bool = True
    head: tuple[Element, ...] = ()
    fields: tuple[Field, ...] = ()

    @property
    def labels(self) -> frozenset[str]:
        """The texts of the labels the kind declares, as they are compared."""
        return frozenset(
            comparable(e.text) for e in (*self.sections, *self.head) if e.type == LABEL and e.text
        )


@dataclass(frozen=True)
class Departure:
    """A declared element a body lacks, carries out of order, leaves empty, fills with
    `None.` where it may not, or fills with more than one sentence where its form is
    `sentence` — at `line` of the file, where the body carries it."""

    element: Element
    how: str
    line: int | None = None


@dataclass(frozen=True)
class FieldDeparture:
    """A front-matter field's text that does not hold the field's form, at `pointer`."""

    field: Field
    how: str
    pointer: str
    text: str


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
            Field(field, value["hint"], value["example"], value.get("form"))
            for field, value in fields.items()
        ),
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
    """A heading, or a declared label, at `index` among a body's lines."""

    index: int
    type: str
    level: int
    text: str
    rest: str = ""


@dataclass(frozen=True)
class _Body:
    """A body read: each line's number and its content — the line with comments left out,
    a fenced line whole — and its marks, in order."""

    numbers: tuple[int, ...]
    content: tuple[str, ...]
    marks: tuple[_Mark, ...]


def _read(lines: Sequence[Line], labels: frozenset[str]) -> _Body:
    content: list[str] = []
    marks: list[_Mark] = []
    fence: tuple[str, int] | None = None
    in_comment = False
    heading_level = 0
    for index, (_number, line) in enumerate(lines):
        if fence is not None:
            content.append(line)
            if _closes(line, fence):
                fence = None
            continue
        started_in_comment = in_comment
        visible, in_comment = _without_comments(line, in_comment)
        content.append(visible)
        if started_in_comment:
            continue
        opening = _FENCE.match(visible)
        if opening is not None and not (
            opening.group(1).startswith("`") and "`" in opening.group(2)
        ):
            fence = (opening.group(1)[0], len(opening.group(1)))
            content[-1] = line
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
            marks.append(_Mark(index, LABEL, heading_level + 1, label["text"], rest))
    return _Body(tuple(n for n, _ in lines), tuple(content), tuple(marks))


def _without_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    """The line with the text of HTML comments left out, and whether a comment is still
    open at its end."""
    kept: list[str] = []
    at = 0
    while at <= len(line):
        if in_comment:
            end = line.find(_COMMENT_CLOSE, at)
            if end == -1:
                return "".join(kept), True
            at, in_comment = end + len(_COMMENT_CLOSE), False
        else:
            start = _comment_opening(line, at)
            if start == -1:
                kept.append(line[at:])
                break
            kept.append(line[at:start])
            at, in_comment = start + len(_COMMENT_OPEN), True
    return "".join(kept), in_comment


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


def comparable(text: str) -> str:
    """A heading's or a label's text as it is compared: case, runs of white space and
    trailing punctuation ignored."""
    return _TRAILING.sub("", " ".join(text.split())).casefold()


# --- departures -----------------------------------------------------------------------------


def departures(lines: Sequence[Line], kind: Kind, *, head: bool = False) -> list[Departure]:
    """How a body with `lines` departs from `kind`'s structure — its file head's, with
    `head` — in declared order, each element once at most: missing or out of order,
    and otherwise what its content breaks."""
    elements = kind.head if head else kind.sections
    body = _read(lines, kind.labels)
    marked = [i for i, e in enumerate(elements) if e.type != OPENING]
    taken = _taken(body.marks, elements, marked)
    found: dict[int, Departure] = {
        i: Departure(elements[i], MISSING)
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
                (m for m in range(after, len(body.marks)) if _matches(elements[i], body.marks[m])),
                None,
            )
            if nxt is None:
                line = body.numbers[body.marks[at[i]].index]
                found[i] = Departure(elements[i], OUT_OF_ORDER, line)
            else:
                at[i], after = nxt, nxt + 1
    for i, element in enumerate(elements):
        if i in found or not element.filled:
            continue
        if element.type == OPENING:
            start = _after_previous(i, elements, at, body)
            extent = _until_next_mark(start, body)
            text = _text(body, extent)
            if not text.strip():
                if element.required:
                    found[i] = Departure(element, MISSING)
                continue
            line = body.numbers[next(k for k in extent if body.content[k].strip())]
        elif i in at:
            mark = body.marks[at[i]]
            line = body.numbers[mark.index]
            text = "\n".join((mark.rest, _text(body, _extent(mark, body))))
        else:
            continue
        how = judged(text, element)
        if how is not None:
            found[i] = Departure(element, how, line)
    return [found[i] for i in sorted(found)]


def judged(text: str, element: Element) -> str | None:
    """What a part's content breaks — empty, `None.` where its element refuses it, or
    not one sentence where its form is `sentence` — or `None` when it holds."""
    flat = " ".join(text.split())
    if not flat:
        return EMPTY
    if flat == NONE:
        return None if element.allows_none else NONE_REFUSED
    if element.form == SENTENCE and not all(one_sentence(item) for item in _items(text)):
        return NOT_A_SENTENCE
    return None


def _items(text: str) -> list[str]:
    """A part's text as a form reads it: where it holds a list, each item, nested ones
    included, its marker left out, and the text before the list and after it, each on its
    own; otherwise the whole text.

    A line opens an item where it starts with a marker after a blank line, within a list,
    or with a bullet or the number 1, which may interrupt a paragraph. So a wrapped line
    that starts `2026. ` continues its paragraph. Text after a blank line that opens with
    no marker and no indentation ends the list."""
    chunks: list[list[str]] = [[]]
    listed, blank = False, True
    for line in text.split("\n"):
        marker = _ITEM.match(line)
        if marker is not None and (
            blank or listed or marker["bullet"] is not None or int(marker["number"]) == 1
        ):
            chunks.append([line[marker.end() :]])
            listed = True
        elif listed and blank and line.strip() and not line[0].isspace():
            chunks.append([line])
            listed = False
        else:
            chunks[-1].append(line)
        blank = not line.strip()
    return ["\n".join(chunk) for chunk in chunks if "".join(chunk).strip()]


def one_sentence(text: str) -> bool:
    """Whether `text` is one sentence: no sentence ends before its last word. A sentence
    ends at a full stop, a question mark or an exclamation mark, only where a space, a
    line end or the text's end follows the mark; a mark inside a code span ends none
    (RS-SAN-001's *How*). So "e.g." ends one wherever a space follows it."""
    plain = _CODE_SPAN.sub("code", text)
    return not any(_WORD.search(plain, end.end()) for end in _SENTENCE_END.finditer(plain))


def field_departures(fields: Mapping[str, Any], kind: Kind) -> list[FieldDeparture]:
    """Each text of a front-matter field that does not hold the field's form: the field's
    own text, or each item of a list. Only the `sentence` form is read; a value of
    another shape is the kind's schema's to report."""
    found: list[FieldDeparture] = []
    for field in kind.fields:
        if field.form != SENTENCE:
            continue
        value = fields.get(field.name)
        for pointer, text in _texts(field.name, value):
            if text.strip() and not one_sentence(text):
                found.append(FieldDeparture(field, NOT_A_SENTENCE, pointer, text))
    return found


def _texts(name: str, value: object) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield f"/{name}", value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, str):
                yield f"/{name}/{index}", item


def _matches(element: Element, mark: _Mark) -> bool:
    if element.type == LABEL:
        return mark.type == LABEL and comparable(mark.text) == comparable(element.text or "")
    if element.type != HEADING or mark.type != HEADING or mark.level != element.level:
        return False
    if element.text is None:
        return bool(mark.text) and _PLACEHOLDER.fullmatch(mark.text) is None
    return comparable(mark.text) == comparable(element.text)


def _taken(
    marks: Sequence[_Mark], elements: Sequence[Element], marked: Sequence[int]
) -> dict[int, int]:
    """The mark each element takes, by index — one of its own, elements with fixed text
    choosing first, as they match fewer; an element no mark is left for takes none."""
    taken: dict[int, int] = {}
    for i in sorted(marked, key=lambda i: elements[i].text is None):
        free = (m for m in range(len(marks)) if m not in taken.values())
        chosen = next((m for m in free if _matches(elements[i], marks[m])), None)
        if chosen is not None:
            taken[i] = chosen
    return taken


def _extent(mark: _Mark, body: _Body) -> range:
    """The lines below a mark that its part holds: to the next declared label, or to a
    heading of the mark's level or above."""
    end = len(body.content)
    for other in body.marks:
        if other.index <= mark.index:
            continue
        if other.type == LABEL or other.level <= mark.level:
            end = other.index
            break
    return range(mark.index + 1, end)


def _after_previous(i: int, elements: Sequence[Element], at: Mapping[int, int], body: _Body) -> int:
    """The line an opening starts at: below the mark of the nearest element listed before
    it that the body carries, or the body's first."""
    for previous in range(i - 1, -1, -1):
        if previous in at:
            return body.marks[at[previous]].index + 1
    return 0


def _until_next_mark(start: int, body: _Body) -> range:
    end = next((m.index for m in body.marks if m.index >= start), len(body.content))
    return range(start, end)


def _text(body: _Body, extent: range) -> str:
    return "\n".join(body.content[k] for k in extent)
