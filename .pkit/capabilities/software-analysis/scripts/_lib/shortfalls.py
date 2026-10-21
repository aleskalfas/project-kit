"""What a use case says the system does not do yet (DEC-001 point 1).

A use case describes what the system must do, as the accepted records decide it. Where
the system does not carry out a step or a variant yet, though an accepted record decides
it, the use case says so twice:

- **The box,** for its reader: a callout in the standard syntax, a block quote whose
  first line is `[!WARNING]` and whose next line opens with `**Not built yet:**`. It
  stands at the top level of the use case's *Main path* or *Variants*, the parts whose
  permanent ids are `main-path` and `variants`, right below the item of its step or
  variant, never inside it. It names the issue that tracks building the behaviour, and
  the id of the record that decides it.
- **The entry,** for a tool: one item of the use case's optional `shortfalls`, its step
  or variant (`at`), its issue and its record, as a record anchor of the use case writes
  it. The overview lists every entry of a use case in force (`_lib/overview.py`).

**A box's lines.** Its first line is `[!WARNING]` after the quote's `>`, alone, and its
second opens with `**Not built yet:**`. It runs while lines open with `>`, so a line
that continues its paragraph without one is no part of it. A blank line, or the body's
end, follows it: Markdown reads a line right below a block quote as part of it, so a
step there would show inside the box. Fenced code and comments hold none. A block quote
whose text opens with "Not built yet" in another form, such as under `[!NOTE]` or
without the bold label, is a box out of its form, so no reader sees a shortfall that no
entry lists.

**What the check holds** (`check._shortfalls`), of each use case in force, whatever any
rule's status, since a tool such as the overview reads the entries whatever binds:

- each box is in its form, a blank line below it, and stands at the top level of *Main
  path* or *Variants*, right below an item that opens with its step's number or its
  variant's number and letter;
- each entry's `at` is a step or a variant the body numbers;
- each entry has a box below its step or variant whose text holds the entry's issue as
  written, as a word of its own, and names its record's id: the part before any `#`, a
  capability's `DEC-NNN` without the capability's name. Each box has such an entry. As
  many entries as can be take a box each, so one box fitting two entries leaves none
  without a box that another box would fit;
- each entry's record is one of the use case's record anchors, written alike, and the
  record it names is accepted: its file's front matter says `status: accepted`. Where it
  lies is the backbone's answer, `backbone.record_file`.

A withdrawn use case is history, so none of this is read of it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from _lib import forms, structure
from _lib.model import SHORTFALLS, Artefact

#: The permanent ids of the parts a box stands in: a use case's steps and its variants.
MAIN_PATH, VARIANTS = "main-path", "variants"

#: What opens a box, and what its text opens with (DEC-001 point 1).
CALLOUT = "[!WARNING]"
LABEL = "**Not built yet:**"

#: The shapes an entry's fields take, as the use case's schema gives them: the schema
#: reports any other, and the check reads no entry of a list that holds one.
_AT = re.compile(r"^[1-9][0-9]*[a-z]?$")
_ISSUE = re.compile(r"^\S+$")
_RECORD = re.compile(
    r"^(?:(?:COR|PRJ|ADR)-[0-9]+|[a-z][a-z0-9-]*[a-z0-9]:DEC-[0-9]+(?:-[a-z0-9]+)*)(?:#[^#\s]+)?$"
)

#: A line of a block quote: its indentation, and what follows its first `>` and the one
#: space after it.
_QUOTE = re.compile(r"^(?P<indent>[ \t]*)>[ ]?(?P<rest>.*)$")

#: A record's id as a box names it: `COR-047`, `PRJ-002`, `ADR-061` or `DEC-054`.
_RECORD_ID = re.compile(r"(?:COR|PRJ|ADR|DEC)-[0-9]+")

#: A callout's first line, `[!WARNING]` or another type, after the quote's `>`.
_CALLOUT_LINE = re.compile(r"^\[![A-Za-z]+\]$")

#: A block quote's text that reads like a box's in any form: "Not built yet", bold or not.
_LIKE_A_BOX = re.compile(r"^[*_]*\s*not\s+built\s+yet\b", re.IGNORECASE)

#: Why a block quote that reads like a box is none, and why a box stands where none may.
OUT_OF_FORM = f"it is not in a box's form, `> {CALLOUT}` then `> {LABEL}`"
NO_BLANK_BELOW = "no blank line follows it, so Markdown reads the line below it as part of the box"


@dataclass(frozen=True)
class Entry:
    """One entry of a use case's `shortfalls`: where it is in the list, its step or
    variant as the body numbers it, `4` or `4a`, its issue and its record, as written."""

    index: int
    at: str
    issue: str
    record: str

    @property
    def record_named(self) -> str:
        """The record its value names, its point left out: `COR-047` for `COR-047#2`."""
        return self.record.rpartition("#")[0] if "#" in self.record else self.record

    @property
    def record_id(self) -> str:
        """The record's id as a box names it: `COR-047`, or `DEC-054` for
        `project-management:DEC-054#5`."""
        found = _RECORD_ID.search(self.record_named)
        return found.group(0) if found else self.record_named

    @property
    def place(self) -> str:
        """The step or the variant as a message names it: `step 4` or `variant 4a`."""
        return place(self.at)


def place(at: str) -> str:
    """A step or a variant as a message and the overview name it: `step 4`, `variant 4a`."""
    return f"variant {at}" if at[-1:].isalpha() else f"step {at}"


@dataclass(frozen=True)
class Box:
    """One box in a use case's body: the line its `[!WARNING]` stands on, its text after
    that line, white space folded, the step or variant it stands right below, and, where
    it stands nowhere a box may, why — `at` is then `None`."""

    line: int
    text: str
    at: str | None = None
    misplaced: str | None = None

    def holds(self, issue: str) -> bool:
        """Whether its text holds `issue` as written, as a word of its own: `#1853` is
        not held by `#18530`, nor by `org/repo#1853`."""
        return re.search(rf"(?<![\w#/.:-]){re.escape(issue)}(?![\w/-])", self.text) is not None

    def names(self, record_id: str) -> bool:
        """Whether its text names a record's id, as a word of its own."""
        return re.search(rf"(?<![\w-]){re.escape(record_id)}(?![\w-])", self.text) is not None


@dataclass(frozen=True)
class Reading:
    """What the check reads of a use case's body: its boxes, in order, and the steps and
    variants the body numbers, `4` and `4a`."""

    boxes: tuple[Box, ...]
    numbered: frozenset[str]


def entries(artefact: Artefact) -> list[Entry] | None:
    """A use case's `shortfalls`, in order: empty where it writes none, and `None` where
    the field or an entry is not of its schema's shape, which the schema reports."""
    value = artefact.fields.get(SHORTFALLS)
    if value is None:
        return []
    if not isinstance(value, list):
        return None
    found: list[Entry] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, Mapping) or set(entry) != {"at", "issue", "record"}:
            return None
        at, issue, record = entry["at"], entry["issue"], entry["record"]
        if isinstance(at, bool) or not isinstance(at, int | str):
            return None
        if not (isinstance(issue, str) and isinstance(record, str)):
            return None
        written = str(at)
        if not (_AT.match(written) and _ISSUE.match(issue) and _RECORD.match(record)):
            return None
        found.append(Entry(index, written, issue, record))
    return found


def read(text: str, kind: structure.Kind) -> Reading:
    """The boxes a use case's body holds, wherever they stand, and the steps and variants
    it numbers, its parts found as `kind` gives them."""
    lines = structure.body_lines(text)
    parts = {
        element.id: part
        for element, part in structure.parts(lines, kind)
        if element.id in (MAIN_PATH, VARIANTS) and not element.added
    }
    numbered: set[str] = set()
    below: dict[str, dict[int, str | None]] = {}
    outside: dict[str, set[int]] = {}
    within: dict[str, set[int]] = {}
    for part_id, part in parts.items():
        listed = forms.listing(part)
        if part_id == MAIN_PATH:
            labels = {item.line: str(number) for number, item, _text in forms.steps(part)}
        else:
            labels = {item.line: label for label, item, _text in forms.variants(part)}
        numbered |= set(labels.values())
        below[part_id] = {item.line: labels.get(item.line) for item in listed.items}
        outside[part_id] = {row.number for row in listed.outside}
        within[part_id] = {part.line, *(row.number for row in part.rows)}
    boxes = tuple(
        Box(line, said, misplaced=problem)
        if problem is not None
        else _placed(line, said, parts, below, outside, within)
        for line, said, problem in _found(lines)
    )
    return Reading(boxes, frozenset(numbered))


def _found(lines: Sequence[structure.Line]) -> list[tuple[int, str, str | None]]:
    """Each block quote among a body's lines, outside fenced code and comments, that reads
    like a box: the line it opens on, its text after a callout's first line, white space
    folded, and what is wrong with its form, `None` where nothing is."""
    rows = structure.rows(lines)
    found: list[tuple[int, str, str | None]] = []
    k = 0
    while k < len(rows):
        opening = _QUOTE.match(rows[k].text) if not rows[k].fence else None
        if opening is None:
            k += 1
            continue
        run = [opening["rest"]]
        end = k + 1
        while end < len(rows):
            quoted = _QUOTE.match(rows[end].text) if not rows[end].fence else None
            if quoted is None:
                break
            run.append(quoted["rest"])
            end += 1
        first = run[0].strip()
        callout = _CALLOUT_LINE.match(first) is not None
        text = " ".join(" ".join(run[1:] if callout else run).split())
        if first == CALLOUT and text.startswith(LABEL):
            below = rows[end] if end < len(rows) else None
            problem = NO_BLANK_BELOW if below is not None and below.text.strip() else None
            found.append((rows[k].number, text, problem))
        elif _LIKE_A_BOX.match(text):
            found.append((rows[k].number, text, OUT_OF_FORM))
        k = end
    return found


def _placed(
    line: int,
    text: str,
    parts: Mapping[str, forms.Part],
    below: Mapping[str, Mapping[int, str | None]],
    outside: Mapping[str, set[int]],
    within: Mapping[str, set[int]],
) -> Box:
    """A box at `line`, with the step or variant it stands right below, or why it stands
    nowhere a box may."""
    part_id = next((p for p in parts if line in within[p]), None)
    if part_id is None:
        return Box(line, text, misplaced="it stands outside the use case's steps and variants")
    if line not in outside[part_id]:
        return Box(line, text, misplaced="it stands inside an item, indented under it")
    above = [item for item in below[part_id] if item < line]
    if not above:
        return Box(line, text, misplaced="it stands above the part's first item")
    at = below[part_id][max(above)]
    if at is None:
        what = "step's number" if part_id == MAIN_PATH else "variant's number and letter"
        return Box(line, text, misplaced=f"the item above it opens with no {what}")
    return Box(line, text, at=at)


def matched(listed: Sequence[Entry], boxes: Sequence[Box]) -> tuple[dict[int, Box], list[Box]]:
    """Each entry's box, by the entry's index, and the boxes no entry takes. An entry fits
    a box below its step or variant whose text holds its issue and names its record's id.
    As many entries as can be take a box each, the earlier entries first: a maximum
    matching. A misplaced box is taken by none."""
    placed = [box for box in boxes if box.at is not None]
    fits = {
        entry.index: [
            i
            for i, box in enumerate(placed)
            if box.at == entry.at and box.holds(entry.issue) and box.names(entry.record_id)
        ]
        for entry in listed
    }
    owner: dict[int, int] = {}

    def take(entry: int, seen: set[int]) -> bool:
        for i in fits[entry]:
            if i in seen:
                continue
            seen.add(i)
            if i not in owner or take(owner[i], seen):
                owner[i] = entry
                return True
        return False

    for entry in listed:
        take(entry.index, set())
    taken = {entry: placed[i] for i, entry in owner.items()}
    return taken, [box for i, box in enumerate(placed) if i not in owner]
