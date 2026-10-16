"""The forms a kind's structure gives a part or a front-matter field (DEC-001 point 1; RS-SAN-001).

A form is a check on the content of a part or a field, from the closed list
`schemas/artefact-kinds.schema.json` gives. `_lib/structure.py` finds each
part and calls the form its element names; this module reads the part's
content and judges it. What it finds binds at the format rule's status, as
every part does, and a withdrawn artefact is never failed for a form, since a
form may have come after its withdrawal (the check's, `_lib/check.py`).

**A part's list** is read by CommonMark's rules for lists, so that each form
judges what a reader sees as an item. The rules it keeps:

- **An item opens** on a line, indented at most three spaces, that starts with
  a bullet (`-`, `*`, `+`) or a number of up to nine digits and `.` or `)`,
  then a space, a tab or the line's end. A thematic break, such as `- - -`, is
  no item.
- **It runs** over each later line indented at least as far as its content
  starts, blank lines among them. Its content starts after the marker and the
  spaces that follow it, one to four of them. With more than four, the rest
  of the line is code, and the content starts one space after the marker, as
  it does after a marker with nothing after it. An item that opens with
  nothing after its marker ends at a blank line right below it.
- **A line that continues a paragraph stays in it.** A line indented less than
  the item's content, right after a line of the item's text, continues that
  text, unless it opens an item, a heading, a block quote, a fence or a
  thematic break. So a wrapped line indented under its item's text stays in
  the item, even one that starts `2026.`, and one not indented that starts
  `2026. ` opens an item, as a reader sees it. A line that is no paragraph,
  such as a heading, indented code or a line of `=` or `-` under a paragraph,
  leaves nothing to continue. These rules are kept for an item's own lines and
  for the items nested in it, one level deep. A line inside a list nested
  deeper is read as text of the nested item it falls in, so a heading or an
  underline there may let a later, less indented line run on into the item.
- **An item may not interrupt a paragraph** outside a list unless it is a
  bullet or the number 1, and holds text: a line that starts `2.` right below
  a paragraph continues it. A part's label line is a paragraph, so a list
  right below it opens with a bullet or `1.`, or after a blank line. Below a
  block quote, any item opens.
- **Fenced code** is what the body reader takes for it (`structure.py`): a
  fence opens at any indentation, and runs to its closing line. It goes with
  its opening line, into an item or not, and no line inside it opens an item
  or ends one. Here the reading departs from CommonMark, which ends an item,
  and the fence with it, at a line inside the fence indented less than the
  item, and reads a line indented four spaces or more outside an item as code
  or text, never a fence. Comments are already left out.
- **The rest of a part** is the text outside its list: its label's line, and
  the lines in no item, such as a lead sentence or a writer's note.

The **items of a part** are its list's top-level items. Under a label that
opens a list item, `- **Steps:**`, they are the items of the list nested in
that item. The label's item ends where Markdown ends it, so what follows it,
such as a writer's `- **Note:**` beside it, is no item of the part's list.
That item, and the items of any other list in the part, are judged by the
`sentence` form alone, each as its own text.

A **list form** judges only the items, so a line a writer adds outside them
never breaks it. It holds at least one item, or `None.` where its part allows
it. A form that matches the front matter reads nothing where the field it
matches is not of its schema's shape, which the schema reports. The forms,
each with what it reads:

- **`sentence`:** the text holds one sentence. No sentence ends before its
  last word. A sentence ends at a full stop, a question mark or an exclamation
  mark, only where a space, a line end or the text's end follows it, and never
  inside a code span (RS-SAN-001's *How*). In a part that holds a list, each
  item holds it on its own, a nested item apart from the item it sits in, and
  so does the rest of the part, taken as one text. In a front-matter field
  that holds a list, each item holds it.
- **`numbered-steps`:** each item opens with its step's number, and no number
  repeats. A number is an item's own marker, `2.`, or one its text opens with,
  `2.` or `**2.**`. The numbers need not run in sequence, since steps are
  append-only (DEC-001 point 3).
- **`variants`:** the part reads `None.`, or each item opens with a step's
  number and one letter, `2a.` or `**2a.**`. The step is one of those the
  kind's steps part numbers: a use case's *Main path*, or a journey's *Steps*.
  A steps part that numbers none is reported itself, and holds no variant to
  its steps.
- **`steps-match-front-matter`:** one numbered item for each entry of the
  front matter's `steps`, in the same order and numbered from 1. Item n's
  line reads `<id> — <title>`, the n-th id and that use case's title, exactly,
  white space aside. Its line runs to a blank line, a nested item or a
  hand-over. Where the analysis holds no such use case, any text after the id
  and ` — ` will do. Below it, each hand-over opens a line, after any list
  marker, with its label:
  - `**Needs from step N (<id>):**`, where step N is an earlier step of the
    journey and has that id;
  - `**Needs from <id> (outside this journey):**`, where the id is in the
    journey's `relies-on` and is none of its steps.

  Text follows each label, up to the next hand-over, blank line or item. Each
  use case in `relies-on` has a hand-over of its own. A line that opens with
  `**Needs from` is a hand-over, and one that is neither label breaks the form.
- **`outcomes-match-front-matter`:** one item for each entry of the record's
  `outcomes`, in the same order. Item n opens with `**<id> — <outcome>.**` for
  the n-th entry, exactly, and text follows.
- **`gaps-match-outcomes`:** the part reads `None.` and nothing else, or holds
  one item for each gap. Each item opens with a bold label of one or more ids
  of `outcomes`, separated by commas and ended by a colon, `**UC-001,
  JRN-001:**`, and holds `**Resolution:**` with text after it. Each
  `code-regressed` or `gap-found` entry is named in a label, so the part reads
  `None.` only where no outcome is one of the two.
- **`definition`**, a term's front-matter `definition`: a phrase whose first
  word is no article, `a`, `an` or `the`, whose last character is no full
  stop, and that holds no whole word of the term's own `name`, in any case.

What no form checks is whether the words are true: friction flags the artefact
when what it rests on changes, and a person rereads it (DEC-001 point 4).
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

#: The forms, from the closed list the declaration's schema gives.
SENTENCE = "sentence"
NUMBERED_STEPS = "numbered-steps"
VARIANTS = "variants"
STEPS_MATCH = "steps-match-front-matter"
OUTCOMES_MATCH = "outcomes-match-front-matter"
GAPS_MATCH = "gaps-match-outcomes"
DEFINITION = "definition"

#: The forms of a part whose items are the steps a variant branches from.
STEP_FORMS = frozenset({NUMBERED_STEPS, STEPS_MATCH})

#: What a part with nothing to say reads, where its element allows it.
NONE = "None."

#: How a text breaks its form: the `sentence` form's own, and every other form's.
NOT_A_SENTENCE, BREAKS_FORM = "not-a-sentence", "breaks-its-form"

#: What a `sentence` breach in a list's item says of where it is.
IN_AN_ITEM = "in a list, each item holds one sentence"

#: The outcomes a gap names (DEC-001 point 6).
NAMED_BY_A_GAP = ("code-regressed", "gap-found")

#: A row of a part that fenced code opens, and one inside it or closing it.
OPENS_FENCE, IN_FENCE = 1, 2


@dataclass(frozen=True)
class Row:
    """One line of a part: its number in the file, its text — comments left out —
    whether fenced code opens on it (`OPENS_FENCE`) or holds it (`IN_FENCE`), and
    whether it is `lazy`: a line an item's text ran on to, less indented than the item,
    which only continues text."""

    number: int
    text: str
    fence: int = 0
    lazy: bool = False


@dataclass(frozen=True)
class Part:
    """A part's content: the text after its label on the label's line, `lead`, which is
    paragraph text, and the lines below it, `rows`. `line` is where the part is shown:
    its label's or heading's line, or an opening's first line of text. `item` is the
    label's whole line where the label opens a list item, `- **Steps:**`, and empty
    otherwise."""

    line: int
    rows: tuple[Row, ...]
    lead: Row | None = None
    item: str = ""

    @property
    def text(self) -> str:
        return "\n".join(row.text for row in ((self.lead,) if self.lead else ()) + self.rows)


@dataclass(frozen=True)
class Item:
    """One item of a list: the line its marker opens, the number of an ordered item's
    marker (`None` for a bullet), and its content, each row less the indentation its
    content starts at — the first row the text after its marker."""

    line: int
    number: int | None
    rows: tuple[Row, ...]

    @property
    def text(self) -> str:
        return "\n".join(row.text for row in self.rows)


@dataclass(frozen=True)
class Listing:
    """A part's list: its top-level items, the rows in none of them, and the items of
    any other list the part holds (`others`): those beside the list item its label
    opens, which a form that reads the part's list does not judge."""

    items: tuple[Item, ...]
    outside: tuple[Row, ...]
    others: tuple[Item, ...] = ()


@dataclass(frozen=True)
class Context:
    """What a form reads besides its part: the artefact's or record's front matter, each
    use case's title by id, the numbers of the steps a variant branches from (`None`
    where the body carries no steps part), and how that part is named."""

    fields: Mapping[str, Any] = field(default_factory=dict)
    titles: Mapping[str, str] = field(default_factory=dict)
    steps: frozenset[int] | None = None
    steps_named: str = "the steps"


@dataclass(frozen=True)
class Breach:
    """How a part breaks its form, at `line`, and what exactly."""

    how: str
    line: int
    detail: str = ""


# --- reading a list --------------------------------------------------------------------------

_MARKER = re.compile(r"^(?P<indent> {0,3})(?P<marker>[-+*]|(?P<number>[0-9]{1,9})[.)])(?P<gap> *)")
_BREAK = re.compile(r"^ {0,3}(?:(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,})$")
_UNDERLINE = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")
_QUOTE = re.compile(r"^ {0,3}>")
_OPENS_BLOCK = re.compile(r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|>)")


def read_list(rows: Sequence[Row], *, after_paragraph: bool = False) -> Listing:
    """The list `rows` hold, read as the module says; `after_paragraph` when the line
    above the first row is paragraph text, as a label's line is."""
    items: list[Item] = []
    outside: list[Row] = []
    current: _Open | None = None
    fenced_in: _Open | None = None  # where the open fence's rows go: an item, or outside
    in_fence = False
    # What paragraph text the row above leaves for a line to continue (`_leaves_paragraph`),
    # whether it is blank, and whether a block quote holds it, whose paragraph no item
    # interrupts.
    paragraph = DIRECT if after_paragraph else NO_PARAGRAPH
    blank, quoted = not after_paragraph, False

    def close() -> None:
        nonlocal current
        if current is not None:
            items.append(current.item())
            current = None

    for row in rows:
        if row.fence == IN_FENCE and in_fence:
            if fenced_in is not None:
                fenced_in.rows.append(_dedented(row, fenced_in.offset))
            else:
                outside.append(row)
            continue
        in_fence = False
        text = row.text.expandtabs(4)
        if not text.strip():
            if current is not None and current.opened_empty and len(current.rows) == 1:
                close()  # an item that opens on an empty line ends at a blank one
            if current is not None:
                current.rows.append(Row(row.number, ""))
            else:
                outside.append(row)
            paragraph, blank, quoted = NO_PARAGRAPH, True, False
            continue
        if row.lazy and (paragraph or quoted) and not blank:
            # A line an item's text ran on to only continues text, read again or not.
            (current.rows if current is not None else outside).append(row)
            continue
        indent = len(text) - len(text.lstrip(" "))
        if current is not None and indent >= current.offset:
            current.rows.append(_dedented(row, current.offset))
            in_fence, fenced_in = row.fence == OPENS_FENCE, current
            above = NO_PARAGRAPH if blank else paragraph
            paragraph, blank = _leaves_paragraph(row, text[current.offset :], above), False
            continue
        interrupting = current is None and bool(paragraph) and not blank and not quoted
        marker = _marker(text, interrupting=interrupting)
        if marker is not None:
            close()
            content, offset, number, code = marker
            current = _Open(row.number, number, offset, [Row(row.number, content, row.fence)])
            in_fence, fenced_in = row.fence == OPENS_FENCE, current
            paragraph = (
                _leaves_paragraph(row, content, NO_PARAGRAPH)
                if content.strip() and not code
                else NO_PARAGRAPH
            )
            blank, quoted = False, False
            continue
        if (
            current is not None
            and paragraph
            and not blank
            and not current.opened_empty
            and _continues_paragraph(row, text)
        ):
            current.rows.append(Row(row.number, text.strip(), lazy=True))
            continue
        close()
        outside.append(row)
        in_fence, fenced_in = row.fence == OPENS_FENCE, None
        if _QUOTE.match(text):
            paragraph, quoted = NO_PARAGRAPH, True
        elif quoted and _continues_paragraph(row, text):
            pass  # a line the quote's paragraph runs on to
        elif paragraph and _UNDERLINE.match(text):
            paragraph = NO_PARAGRAPH  # it underlines the paragraph above as a heading
        else:
            quoted = False
            text_runs_on = _continues_paragraph(row, text) and (paragraph or indent < 4)
            paragraph = DIRECT if text_runs_on else NO_PARAGRAPH
        blank = False
    close()
    return Listing(tuple(items), tuple(outside))


@dataclass
class _Open:
    line: int
    number: int | None
    offset: int
    rows: list[Row]

    @property
    def opened_empty(self) -> bool:
        """Whether the item opened on a line with nothing after its marker."""
        return not self.rows[0].text.strip() and all(not r.text.strip() for r in self.rows[1:])

    def item(self) -> Item:
        return Item(self.line, self.number, tuple(self.rows))


def _marker(text: str, *, interrupting: bool) -> tuple[str, int, int | None, bool] | None:
    """The content after a list item's marker on `text`, the column its content starts
    at, an ordered item's number, and whether that content is indented code — `None`
    where `text` opens no item. An item that would interrupt a paragraph opens only as
    a bullet or the number 1, and with text."""
    found = _MARKER.match(text)
    if found is None or _BREAK.match(text):
        return None
    start = found.end("marker")
    after = text[start:]
    if after and after[0] != " ":
        return None
    empty = not after.strip()
    number = None if found["number"] is None else int(found["number"])
    if interrupting and (empty or (number is not None and number != 1)):
        return None
    code = not empty and len(found["gap"]) > 4
    offset = start + 1 if empty or code else start + len(found["gap"])
    return ("" if empty else text[offset:]), offset, number, code


def _dedented(row: Row, columns: int) -> Row:
    text = row.text.expandtabs(4)
    lead = len(text) - len(text.lstrip(" "))
    return Row(row.number, text[min(lead, columns) :], row.fence, row.lazy)


def _continues_paragraph(row: Row, text: str) -> bool:
    """Whether a row may continue the paragraph above it: it opens no other block, a
    heading, a block quote, a fence or a thematic break."""
    return row.fence == 0 and _OPENS_BLOCK.match(text) is None and _BREAK.match(text) is None


#: What paragraph text a row of an item's content leaves for a later line to continue:
#: none, one directly in the item, or one in a block the item nests, a list or a quote.
NO_PARAGRAPH, DIRECT, NESTED = 0, 1, 2


def _leaves_paragraph(row: Row, text: str, above: int) -> int:
    """What paragraph text a row of an item's content leaves, `above` saying what the
    row above it left. A nested item leaves what its own content leaves, as a nested
    paragraph, and so does a block quote with text. An underline below a paragraph
    directly in the item, indented code, a heading, a fence and a thematic break leave
    none. A line below a nested paragraph continues it."""
    if row.fence:
        return NO_PARAGRAPH
    nested_item = _marker(text, interrupting=above == DIRECT)
    if nested_item is not None:
        content, _offset, _number, code = nested_item
        inner = not code and content.strip() and _leaves_paragraph(row, content, NO_PARAGRAPH)
        return NESTED if inner else NO_PARAGRAPH
    if above == DIRECT and _UNDERLINE.match(text):
        return NO_PARAGRAPH
    if not above and len(text) - len(text.lstrip(" ")) >= 4:
        return NO_PARAGRAPH
    quote = _QUOTE.match(text)
    if quote is not None:
        return NESTED if text[quote.end() :].strip() else NO_PARAGRAPH
    if not _continues_paragraph(row, text):
        return NO_PARAGRAPH
    return NESTED if above == NESTED else DIRECT


def listing(part: Part) -> Listing:
    """A part's list, its label's line among the rows outside it. Under a label that
    opens a list item, the part's list is the one nested in that item, and what follows
    the item, such as a writer's `- **Note:**` beside it, is outside the list."""
    if not part.item:
        found = read_list(part.rows, after_paragraph=part.lead is not None)
        lead = (part.lead,) if part.lead is not None else ()
        return Listing(found.items, (*lead, *found.outside))
    outer = read_list((Row(part.line, part.item), *part.rows))
    if not outer.items or outer.items[0].line != part.line:
        return listing(Part(part.line, part.rows, part.lead))
    own, others = outer.items[0], outer.items[1:]
    nested_list = read_list(own.rows[1:], after_paragraph=True)
    lead = (part.lead,) if part.lead is not None else ()
    outside = sorted((*nested_list.outside, *outer.outside), key=lambda row: row.number)
    return Listing(nested_list.items, (*lead, *outside), others)


def nested(item: Item) -> Listing:
    """The list an item's content holds, its own text outside it: a list may open on
    the item's first line, as `- 1. …` nests a numbered item in a bullet."""
    return read_list(item.rows)


# --- judging a part ---------------------------------------------------------------------------


def judge(form: str | None, part: Part, context: Context) -> list[Breach]:
    """How a part with content breaks `form`, each breach at its line; none where it
    holds the form, or where the form is no part's."""
    if form == SENTENCE:
        return _sentence(part)
    if form == NUMBERED_STEPS:
        return _numbered_steps(part)
    if form == VARIANTS:
        return _variants(part, context)
    if form == STEPS_MATCH:
        return _steps_match(part, context)
    if form == OUTCOMES_MATCH:
        return _outcomes_match(part, context)
    if form == GAPS_MATCH:
        return _gaps_match(part, context)
    return []


def judge_none(form: str | None, part: Part, context: Context) -> list[Breach]:
    """How a part that reads `None.`, where its element allows it, breaks `form`: only
    gaps may break it, where an outcome a gap must name is there."""
    if form != GAPS_MATCH:
        return []
    named = [
        f"{artefact}'s outcome is `{outcome}`"
        for artefact, outcome in _outcomes(context)
        if outcome in NAMED_BY_A_GAP
    ]
    if not named:
        return []
    return [
        Breach(
            BREAKS_FORM,
            part.line,
            f"it reads `None.`, though {' and '.join(named)}: each `code-regressed` or "
            f"`gap-found` artefact is named by a gap",
        )
    ]


def step_numbers(part: Part) -> frozenset[int]:
    """The numbers of a steps part's items, as a variant names them."""
    return frozenset(number for number, _item, _text in steps(part) if number)


def steps(part: Part) -> list[tuple[int, Item, str]]:
    """Each item of a steps part that opens with its step's number, as `numbered-steps`
    reads it, in order: the number, the item, and its text after the number, white space
    folded."""
    found: list[tuple[int, Item, str]] = []
    for item in listing(part).items:
        number, rest = _numbered(item)
        if number is not None:
            found.append((number, item, _after(rest, item)))
    return found


def variants(part: Part) -> list[tuple[str, Item, str]]:
    """Each item of a variants part that opens with a step's number and a letter, as
    `variants` reads it, in order: the label, `2a`, its letter in lower case, the item,
    and its text after the label, white space folded."""
    found: list[tuple[str, Item, str]] = []
    for item in listing(part).items:
        lettered = _lettered(item)
        if lettered is not None:
            step, letter, rest = lettered
            found.append((f"{step}{letter.lower()}", item, _after(rest, item)))
    return found


def _lettered(item: Item) -> tuple[int, str, str] | None:
    """A variant's step number and letter, `2a.` or `**2a.**`, as its item opens with
    them, and its first row's text after them; `None` for an item that does not open so."""
    first = item.rows[0].text if item.rows else ""
    opening = _VARIANT.match(first)
    if opening is None:
        return None
    step = int(opening["bold"] or opening["plain"])
    return step, opening["b"] or opening["p"], first[opening.end() :]


def _after(rest: str, item: Item) -> str:
    """An item's text after its number or label, `rest` on its first row: every row, white
    space folded."""
    return " ".join(" ".join([rest, *(row.text for row in item.rows[1:])]).split())


def _sentence(part: Part) -> list[Breach]:
    return [
        Breach(NOT_A_SENTENCE, line, IN_AN_ITEM if line != part.line else "")
        for line, text in _texts(listing(part), part.line)
        if text.strip() and not one_sentence(text)
    ]


def _texts(found: Listing, line: int) -> Iterator[tuple[int, str]]:
    """Each text a `sentence` part holds: the rows outside its lists, taken as one, and
    each item's own text, apart from the items nested in it — an item of the part's
    list or of another list in the part alike."""
    yield line, "\n".join(row.text for row in found.outside)
    for item in (*found.items, *found.others):
        yield from _texts(nested(item), item.line)


def _where_a_list_goes(listed: Listing) -> str:
    """Where a part's list must stand to be read as one, as a message advises it: under
    the label's own list item, where a list stands beside that item, and otherwise
    where it opens."""
    if listed.others:
        return (
            "indent the list under the label's own list item, as far in as the label's "
            "text, since a list beside that item is no part of it"
        )
    return (
        "start the list with `1.` or a bullet, or after a blank line, since a line that "
        "opens `2.` right below a paragraph continues it"
    )


def _reads_none(part: Part) -> str:
    """How a part with no item stands to `None.`: it reads more, or it does not read it."""
    if " ".join(part.text.split()).startswith(NONE):
        return "reads more than `None.`, which stands alone where there is nothing to say"
    return "does not read `None.`"


def _numbered_steps(part: Part) -> list[Breach]:
    listed = listing(part)
    items = listed.items
    if not items:
        return [
            Breach(
                BREAKS_FORM,
                part.line,
                "it holds no numbered step: write each step as a numbered list item, "
                f"such as `1. The analyst chooses Export.`, and {_where_a_list_goes(listed)}",
            )
        ]
    found: list[Breach] = []
    first: dict[int, int] = {}
    for item in items:
        number, _rest = _numbered(item)
        if number is None:
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    "the item opens with no step's number, such as `2.`",
                )
            )
        elif number in first:
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    f"step {number} is numbered twice, at lines {first[number]} and "
                    f"{item.line}: no number repeats",
                )
            )
        else:
            first[number] = item.line
    return found


_NUMBERED = re.compile(r"^(?:\*\*(?P<bold>[0-9]{1,9})[.)]\*\*|(?P<plain>[0-9]{1,9})[.)])(?=\s|$)")
_VARIANT = re.compile(
    r"^(?:\*\*(?P<bold>[0-9]{1,9})(?P<b>[A-Za-z])\.\*\*|(?P<plain>[0-9]{1,9})(?P<p>[A-Za-z])\.)(?=\s|$)"
)


def _numbered(item: Item) -> tuple[int | None, str]:
    """An item's step number — its own marker's, or one its text opens with, plain or
    bold — and its first row's text after that number."""
    first = item.rows[0].text if item.rows else ""
    if item.number is not None:
        return item.number, first
    found = _NUMBERED.match(first)
    if found is None:
        return None, first
    return int(found["bold"] or found["plain"]), first[found.end() :].lstrip()


def _variants(part: Part, context: Context) -> list[Breach]:
    listed = listing(part)
    items = listed.items
    if not items:
        return [
            Breach(
                BREAKS_FORM,
                part.line,
                f"it holds no variant, and {_reads_none(part)}: write each variant as a list "
                f"item that opens with its step's number and a letter, such as `- **2a.** …`, "
                f"and {_where_a_list_goes(listed)}",
            )
        ]
    found: list[Breach] = []
    for item in items:
        lettered = _lettered(item)
        if lettered is None:
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    "the item opens with no step's number and letter, such as `2a.`",
                )
            )
            continue
        step, letter, _rest = lettered
        if context.steps is not None and step not in context.steps:
            label = f"{step}{letter}"
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    f"variant {label} branches from step {step}, which {context.steps_named} "
                    f"does not hold",
                )
            )
    return found


_HANDOVER = re.compile(r"^(?:(?:[-+*]|[0-9]{1,9}[.)])[ \t]+)?(?P<label>\*\*Needs from\b.*)$")
_FROM_STEP = re.compile(r"^\*\*Needs from step (?P<step>[0-9]+) \((?P<id>[^()\s]+)\):\*\*")
_FROM_OUTSIDE = re.compile(r"^\*\*Needs from (?P<id>[^()\s]+) \(outside this journey\):\*\*")


def _steps_match(part: Part, context: Context) -> list[Breach]:
    steps = _ids(context.fields.get("steps"))
    if steps is None:
        return []  # the journey's schema reports `steps` that is no list of ids
    relies_on = _ids(context.fields.get("relies-on")) or []
    items = listing(part).items
    found: list[Breach] = []
    outside_named: set[str] = set()
    for n, item in enumerate(items, start=1):
        if n > len(steps):
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    f"the item is step {n}, and `steps` lists {len(steps)}: one numbered "
                    f"item for each of its entries",
                )
            )
            continue
        number, _first = _numbered(item)
        expected = _step_line(steps[n - 1], context.titles)
        written = _step_text(item)
        if number != n:
            numbered = "opens with no number" if number is None else f"is numbered {number}"
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    f"step {n} {numbered}: the steps are numbered from 1, in order",
                )
            )
        if not _is_step_line(written, steps[n - 1], context.titles):
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    f"step {n} reads `{_shown(written)}`, where it is `{expected}`: the "
                    f"{_ordinal(n)} id of `steps` and that use case's title, exactly",
                )
            )
        for line, label, rest in _handovers(item):
            breach = _handover(n, line, label, rest, steps, relies_on)
            if breach is not None:
                found.append(breach)
            if (outside := _FROM_OUTSIDE.match(label)) is not None:
                outside_named.add(outside["id"])
    for n in range(len(items) + 1, len(steps) + 1):
        found.append(
            Breach(
                BREAKS_FORM,
                part.line,
                f"it holds {len(items)} step(s), and `steps` lists {len(steps)}: step {n}, "
                f"`{n}. {_step_line(steps[n - 1], context.titles)}`, has no line",
            )
        )
    for use_case in relies_on:
        if use_case not in outside_named:
            found.append(
                Breach(
                    BREAKS_FORM,
                    part.line,
                    f"`relies-on` lists {use_case}, and no hand-over names it: write "
                    f"`**Needs from {use_case} (outside this journey):**` under the step "
                    f"that needs it",
                )
            )
    return found


def _ids(value: object) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return None
    return list(value)


def _step_line(use_case: str, titles: Mapping[str, str]) -> str:
    title = titles.get(use_case)
    return f"{use_case} — {title}" if title is not None else f"{use_case} — <its title>"


def _is_step_line(written: str, use_case: str, titles: Mapping[str, str]) -> bool:
    title = titles.get(use_case)
    if title is not None:
        return written == " ".join(f"{use_case} — {title}".split())
    opening = f"{use_case} — "
    return written.startswith(opening) and bool(written[len(opening) :].strip())


def _step_text(item: Item) -> str:
    """A step's line: its item's first paragraph, its number left out, up to a blank
    line, a nested item or a hand-over, white space runs read as one space."""
    _number_of, first = _numbered(item)
    lines = [first]
    for row in item.rows[1:]:
        text = row.text.expandtabs(4)
        if not text.strip() or _opens_item(text) or _HANDOVER.match(text.strip()):
            break
        lines.append(text)
    return " ".join(" ".join(lines).split())


def _opens_item(text: str) -> bool:
    """Whether a line below a paragraph opens an item: a bullet, or the number 1, with a
    space after it — so a wrapped line that starts `-based` or `2026.` does not."""
    return _marker(text, interrupting=True) is not None


def _handovers(item: Item) -> Iterator[tuple[int, str, str]]:
    """Each hand-over under a step: its line, its label's line from the label on, and
    the text that follows the label — to the next hand-over, blank line or item."""
    rows = item.rows[1:]
    for index, row in enumerate(rows):
        opening = _HANDOVER.match(row.text.strip())
        if opening is None:
            continue
        label = opening["label"]
        closed = re.match(r"^\*\*.*?:\*\*", label)
        said = [label[closed.end() :] if closed else ""]
        for later in rows[index + 1 :]:
            text = later.text.strip()
            if not text or _opens_item(text) or _HANDOVER.match(text):
                break
            said.append(text)
        yield row.number, label, " ".join(said)


def _handover(
    n: int, line: int, label: str, rest: str, steps: Sequence[str], relies_on: Sequence[str]
) -> Breach | None:
    """What a hand-over under step `n` breaks: its label's shape, the step or use case
    it names, or no text after its label."""
    from_step, from_outside = _FROM_STEP.match(label), _FROM_OUTSIDE.match(label)
    if from_step is not None:
        step, use_case = int(from_step["step"]), from_step["id"]
        if not 1 <= step < n:
            return Breach(
                BREAKS_FORM,
                line,
                f"a hand-over under step {n} needs from step {step}, which is no earlier "
                f"step of the journey",
            )
        if steps[step - 1] != use_case:
            return Breach(
                BREAKS_FORM,
                line,
                f"a hand-over under step {n} names step {step} as {use_case}, where step "
                f"{step} is {steps[step - 1]}",
            )
    elif from_outside is not None:
        use_case = from_outside["id"]
        if use_case in steps:
            return Breach(
                BREAKS_FORM,
                line,
                f"a hand-over under step {n} names {use_case} outside this journey, though "
                f"it is a step of it: name it `**Needs from step N ({use_case}):**`",
            )
        if use_case not in relies_on:
            return Breach(
                BREAKS_FORM,
                line,
                f"a hand-over under step {n} names {use_case} outside this journey, and "
                f"`relies-on` does not list it",
            )
    else:
        return Breach(
            BREAKS_FORM,
            line,
            f"a hand-over under step {n} opens `{_shown(label)}`, which is neither "
            f"`**Needs from step N (<id>):**` nor `**Needs from <id> (outside this journey):**`",
        )
    if not _WORD.search(rest):
        return Breach(
            BREAKS_FORM,
            line,
            f"a hand-over under step {n} says nothing after its label: say what it receives, "
            f"and how that can break",
        )
    return None


def _outcomes(context: Context) -> list[tuple[str, str]]:
    """A record's outcomes, in order; none where they are no mapping of ids to outcomes,
    which the record's schema reports."""
    outcomes = context.fields.get("outcomes")
    if not isinstance(outcomes, Mapping):
        return []
    return [(str(key), str(value)) for key, value in outcomes.items()]


def _outcomes_match(part: Part, context: Context) -> list[Breach]:
    if not isinstance(context.fields.get("outcomes"), Mapping):
        return []
    entries = _outcomes(context)
    items = listing(part).items
    found: list[Breach] = []
    for n, item in enumerate(items, start=1):
        if n > len(entries):
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    f"the item is the {_ordinal(n)}, and `outcomes` holds {len(entries)}: one "
                    f"item for each of its entries",
                )
            )
            continue
        opening = _outcome_label(*entries[n - 1])
        text = item.text
        if not text.startswith(opening):
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    f"item {n} opens `{_shown(text)}`, where the {_ordinal(n)} entry of "
                    f"`outcomes` gives `{opening}`: one item for each entry, in its order",
                )
            )
        elif not _WORD.search(text[len(opening) :]):
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    f"item {n} gives no reason after `{opening}`",
                )
            )
    for n in range(len(items) + 1, len(entries) + 1):
        found.append(
            Breach(
                BREAKS_FORM,
                part.line,
                f"it holds {len(items)} item(s), and `outcomes` holds {len(entries)}: "
                f"`{_outcome_label(*entries[n - 1])}` has none",
            )
        )
    return found


def _outcome_label(artefact: str, outcome: str) -> str:
    return f"**{artefact} — {outcome}.**"


_GAP_LABEL = re.compile(r"^\*\*(?P<ids>[^*\n]+?):\*\*")
_RESOLUTION = re.compile(r"\*\*Resolution:\*\*(?P<after>.*)", re.DOTALL)


def _gaps_match(part: Part, context: Context) -> list[Breach]:
    if not isinstance(context.fields.get("outcomes"), Mapping):
        return []
    entries = _outcomes(context)
    known = {artefact for artefact, _outcome in entries}
    items = listing(part).items
    if not items:
        return [
            Breach(
                BREAKS_FORM,
                part.line,
                f"it holds no gap, and {_reads_none(part)}: write each gap as a list item "
                f"that opens with the ids it affects, such as `- **UC-007:** …`",
            )
        ]
    found: list[Breach] = []
    named: set[str] = set()
    for item in items:
        label = _GAP_LABEL.match(item.text)
        if label is None:
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    "the gap opens with no bold label of the ids it affects, such as "
                    "`**UC-007, JRN-001:**`",
                )
            )
        else:
            ids = [piece.strip() for piece in label["ids"].split(",")]
            unknown = [i for i in ids if i and i not in known]
            named.update(i for i in ids if i in known)
            if not any(ids):
                found.append(
                    Breach(BREAKS_FORM, item.line, "the gap's label names no id: name each id")
                )
            elif not all(ids):
                found.append(
                    Breach(
                        BREAKS_FORM,
                        item.line,
                        f"the gap's label, `**{label['ids']}:**`, leaves an id out between "
                        f"its commas: name each id once, separated by commas",
                    )
                )
            if unknown:
                found.append(
                    Breach(
                        BREAKS_FORM,
                        item.line,
                        f"the gap names {', '.join(f'`{i}`' for i in unknown)}, which "
                        f"`outcomes` does not list: a gap names artefacts the record covers",
                    )
                )
        resolution = _RESOLUTION.search(item.text)
        if resolution is None or not _WORD.search(resolution["after"]):
            found.append(
                Breach(
                    BREAKS_FORM,
                    item.line,
                    "the gap holds no `**Resolution:**` with text after it: say what "
                    "resolved it or carries its fix",
                )
            )
    for artefact, outcome in entries:
        if outcome in NAMED_BY_A_GAP and artefact not in named:
            found.append(
                Breach(
                    BREAKS_FORM,
                    part.line,
                    f"{artefact}'s outcome is `{outcome}`, and no gap names it",
                )
            )
    return found


# --- a front-matter field's text ---------------------------------------------------------------

_CODE_SPAN = re.compile(r"(`+)(.+?)\1", re.DOTALL)
_SENTENCE_END = re.compile(r"[.?!](?=\s|$)")
_WORD = re.compile(r"\w")
_WORDS = re.compile(r"\w+")
_ARTICLES = frozenset({"a", "an", "the"})


def one_sentence(text: str) -> bool:
    """Whether `text` is one sentence: no sentence ends before its last word. A sentence
    ends at a full stop, a question mark or an exclamation mark, only where a space, a
    line end or the text's end follows the mark; a mark inside a code span ends none
    (RS-SAN-001's *How*). So "e.g." ends one wherever a space follows it."""
    plain = _CODE_SPAN.sub("code", text)
    return not any(_WORD.search(plain, end.end()) for end in _SENTENCE_END.finditer(plain))


def field_breach(form: str | None, text: str, fields: Mapping[str, Any]) -> tuple[str, str] | None:
    """How a front-matter field's text breaks `form`, and what exactly; `None` where it
    holds it, or where the form is no field's. `fields` is the artefact's own, for the
    name a definition never repeats."""
    if form == SENTENCE:
        return None if one_sentence(text) else (NOT_A_SENTENCE, "")
    if form == DEFINITION:
        problems = definition_problems(text, fields.get("name"))
        return (BREAKS_FORM, ", and ".join(problems)) if problems else None
    return None


def definition_problems(text: str, name: object) -> list[str]:
    """What a term's definition breaks of the `definition` form: its first word an
    article, its last character a full stop, a whole word of the term's `name` in it."""
    phrase = text.strip()
    problems: list[str] = []
    words = phrase.split()
    first = words[0].strip("*_\"'`([") if words else ""
    if first.casefold() in _ARTICLES:
        problems.append(f"it opens with an article, `{first}`")
    if phrase.endswith("."):
        problems.append("it ends with a full stop")
    if isinstance(name, str):
        own = {word.casefold() for word in _WORDS.findall(name)}
        held = [w for w in dict.fromkeys(_WORDS.findall(phrase)) if w.casefold() in own]
        if held:
            shown = ", ".join(f"`{w}`" for w in held)
            problems.append(f"it holds {shown}, a word of the term's name")
    return problems


# --- shown in a message ------------------------------------------------------------------------


def _shown(text: str, most: int = 60) -> str:
    """A text as a message quotes it: its first line, cut to `most` characters."""
    line = text.strip().split("\n", 1)[0]
    return line if len(line) <= most else line[: most - 1].rstrip() + "…"


def _ordinal(n: int) -> str:
    """`n` as an ordinal: `1st`, `2nd`, `11th`."""
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
