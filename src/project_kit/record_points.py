"""A decision record's points (COR-058; ADR-057 point 2).

The one reading of a record's points, over the reading of where a part of a
document lies (`document_parts`). Validation's decisions member calls it
(`decisions_validate.check_points`, COR-058 point 7), and so do the
numbering check (`decisions_check_diff`, COR-058 point 8) and friction, for
an anchor on one point (COR-050 point 5). The conversion (COR-058 point 9)
is to call it. No
other module of the binary reads a record's points, and artefact discovery
does not: a record is read here whether or not a place holds it.

- `read_points` reads one record's text:
  - **the Decision's extent:** the section of the body's first `Decision`
    heading, to the next heading of the same or a higher level.
  - **its point headings** (COR-058 point 1), found in the Decision only:
    `### 5. Title` for a numbered point, `### D1 — Title` for a labelled one,
    a label being letters then a number. Points sit at the level of the
    Decision's first heading in that form, one below the Decision or below the
    group headings that gather them. A heading at another level is no point
    and is not warned of.
  - **its stubs** (COR-058 point 4): headings in point form at the points'
    level whose title is `Retired`.
  - **its misspelt headings:** a heading in the Decision that opens with a
    number or a label in another form, such as `### 16 - Title` or
    `### 5.1 Title`, at the points' level, or at any level while the record
    has no point heading. Validation warns of them (COR-058 point 7).
  - **its retired ids** with their successors, from `retired-points` in its
    front matter (COR-058 points 4 and 6), read forgivingly: what cannot be
    read is named in `retired_problems`, for validation to fail on.
  - **its points in list form** (COR-058 point 2), while it has no point
    heading or stub: the numbered items of a list at the Decision's top
    level or of one numbering that runs across its group headings, and the
    paragraphs that open with a bold number or a bold label, whether the
    bold holds the title (`**5. Title.**`) or only the id (`**5.** Title`,
    `**D1** — Title`). A numbered list inside a point or another sub-section
    holds no points. Whoever converts the record confirms this reading.
- `RecordPoints.ground` gives what a point stands on (COR-050 point 5): its
  section, the record's status, supersession and title fields, its preamble
  (the text before its first section) and Summary, and the Decision's text
  outside every point and stub. A stub is no point, and stands on nothing.
- `RecordPoints.anchored` gives what an anchor on one point finds in the
  record (COR-050 point 7): a live point, an id two live points share, a
  retired id with its successors, a record whose points are a list, or
  nothing. `RecordPoints.standing` gives what a live point stands on as the
  friction checks and the debt listing compare it, one state with another
  (`Standing`). `split_anchor` reads a record anchor's value as its record
  and its point, `COR-058#4`.
- `hold_stubs` holds each stub to its entry in `retired-points`, both ways
  (COR-058 point 6): a retired id with no stub, a stub whose id is not
  retired, and a stub whose sentence differs from the one its entry gives
  (`stub_sentence`).
- `RecordPoints.point_text` gives a point's text read without its id, by which
  the numbering check finds a point under another id (COR-058 point 8).
  `id_series` splits an id into its series and its number, which count apart
  (COR-058 point 3).

An anchor may name one point, and what the point stands on is the
anchors-and-friction record's (COR-050 points 2 and 5, as COR-058 point 10
leaves it). Friction reads the point and what it stands on here and nowhere
else (ADR-057 point 2): the change check and the whole-repository check, at
each state they compare, and validation's friction member, at the working
tree.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, cast

from project_kit.document_parts import Body, Extent, Heading, Line, parse_front_matter
from project_kit.line_breaks import universal_newlines

#: The front-matter field that lists a record's retired ids with their successors.
RETIRED_POINTS_KEY = "retired-points"

#: The title that marks a stub, so no live point takes it (COR-058 point 1).
STUB_TITLE = "Retired"

#: The heading of the section that holds a record's points.
DECISION_TITLE = "Decision"

#: The heading of a summary section, which every point stands on.
SUMMARY_TITLE = "Summary"

#: What sets the point an anchor names apart from its record: `COR-058#4` (COR-050 point 2).
POINT_MARK = "#"

#: The record's own fields every point stands on: its status, supersession and title.
GROUND_FIELDS = ("status", "supersedes", "superseded_by", "title")

# A point heading's title (COR-058 point 1): a number, a full stop and a space, or a
# label — letters then a number — a space, an em dash and a space; then the title.
_NUMBERED = re.compile(r"^(\d+)\. +(\S.*)$")
_LABELLED = re.compile(r"^([A-Za-z]+\d+) — +(\S.*)$")

# A title that opens with a number, or with a label as a whole token.
_OPENS_WITH_ID = re.compile(r"^(?:\d|[A-Za-z]+\d+(?!\w))")

# A point id, as `retired-points` names one: a number, or a label.
_POINT_ID = re.compile(r"^(?:\d+|[A-Za-z]+\d+)$")

# A point id's series and number. Numbers and each series of labels count apart
# (COR-058 point 3); a number's series is the empty prefix.
_SERIES = re.compile(r"^([A-Za-z]*)(\d+)$")

# List form (COR-058 point 2): a numbered item at the start of a line, and a
# paragraph that opens with a bold number — `**5. Title.**` or `**5.** Title` — or a
# bold label — `**D1 — Title.**` or `**D1** — Title`. A bold label alone is no point
# without the em dash after it, so a paragraph opening `**IPv6**` holds none.
_ITEM = re.compile(r"^(\d+)[.)](?:[ \t]+(.*))?$")
_BOLD_POINT = re.compile(
    r"^\*\*(?:(?P<number>\d+)\.(?:[ \t]+|\*\*)"
    r"|(?P<label>[A-Za-z]+\d+)(?:[ \t]+—[ \t]+|\*\*[ \t]+—[ \t]+))"
)

# A bold lead: the text between the first pair of `**`; and the id it may open with.
_BOLD_LEAD = re.compile(r"^\*\*(.+?)\*\*")

# A numbered item's number, as its line opens with it.
_ITEM_NUMBER = re.compile(r"^\d+[.)][ \t]*")
_LEAD_ID = re.compile(r"^(?:\d+\.|[A-Za-z]+\d+(?:[ \t]+—)?)[ \t]*")

# A line that ends a list at once when it opens a line: a bullet or a quote.
_ENDS_A_LIST = re.compile(r"^(?:[-*+][ \t]|>)")


@dataclass(frozen=True)
class PointHeading:
    """A heading in point form at the points' level: a point, or a stub.

    `extent` is its section: its heading and its text, to the next heading of
    the same or a higher level (COR-058 point 1). `group` is the heading that
    gathers it, when its points sit below group headings.
    """

    id: str
    title: str
    extent: Extent
    group: Heading | None = None

    @property
    def is_stub(self) -> bool:
        """Whether its title marks a retired point's stub (COR-058 point 4)."""
        return self.title == STUB_TITLE


class ListForm(Enum):
    """How a point is written in a record not yet converted (COR-058 point 2)."""

    ITEM = "item"  # a numbered item, `5. **Title.** …`
    BOLD_NUMBER = "bold-number"  # a paragraph opening `**5. Title.**`
    BOLD_LABEL = "bold-label"  # a paragraph opening `**D1 — Title.**`


@dataclass(frozen=True)
class ListPoint:
    """A point of a record in list form (COR-058 point 2).

    - `id`: for a numbered item, the number Markdown shows: the list's first
      written number, then one more for each item after it. For a bold
      paragraph, the number or label it opens with.
    - `written`: the number or label as the source writes it.
    - `title`: its bold lead, without a closing full stop, or `None` when it
      opens with none.
    - `start`: where its line starts in the body.
    - `end`: where its text ends in the body. A numbered item's text runs to
      the next item, and the last item's to the line that ends the list or to
      its region's end. A bold paragraph's runs to the next bold point of its
      region, or to the region's end. `RecordPoints.list_point_words` reads it.
    """

    id: str
    form: ListForm
    written: str
    title: str | None
    start: int
    end: int


@dataclass(frozen=True)
class PointGround:
    """What a point stands on: its section, the record's own fields that say whether
    and how it binds, and the parts of the record every point stands on.

    `fields` holds those of `GROUND_FIELDS` the record writes, as written.
    `extents` are the point's section first, then, in the body's order, its
    preamble, its Summary section and the Decision's text outside every point
    and stub. An empty part is left out.
    """

    point: PointHeading
    fields: Mapping[str, Any]
    extents: tuple[Extent, ...]


@dataclass(frozen=True)
class Standing:
    """What an anchor on one point stands on at one state, as the friction checks and the
    debt listing compare it (COR-050 point 5).

    - `fields`: those of `GROUND_FIELDS` the record writes, each as YAML reads
      it, written out as JSON with its keys sorted, so a reformatted field is
      no change.
    - `section`: the point's section, its heading and its text.
    - `shared`: the parts of the record every point stands on, its preamble,
      its Summary and the Decision's text outside every point and stub, in the
      body's order, each ending with one line break and set apart by a blank
      line.

    Where the point sits in its record is not compared, so a move changes
    nothing. Two states compare equal when the point stands on the same in
    both.
    """

    fields: tuple[tuple[str, str], ...]
    section: str
    shared: str

    def lines(self) -> list[str]:
        """The standing as lines, for a diff between two states: the point's section,
        then the fields, then the shared parts, each block set apart by a blank line."""
        fields = [f"{key}: {value}" for key, value in self.fields]
        blocks = [self.section, "\n".join(fields) + "\n" if fields else "", self.shared]
        return "\n".join(block for block in blocks if block).splitlines()


class PointState(Enum):
    """What an anchor on one point of a record finds there (COR-050 points 5 and 7)."""

    LIVE = "live"  # one live point has the id
    RETIRED = "retired"  # the record retires the id: it stands on nothing, and is not dead
    AMBIGUOUS = "ambiguous"  # two live points or more share the id
    LIST_FORM = "list-form"  # the record writes its points as a list: none an anchor can name
    MISSING = "missing"  # no point has the id, and the record retires none: a dead anchor


@dataclass(frozen=True)
class AnchoredPoint:
    """One record's answer to an anchor on its point `id` (COR-050 points 5 and 7).

    - `state`: what the anchor finds (`PointState`).
    - `standing`: what it stands on, `None` where it stands on nothing: a
      retired id, or no point with the id. An ambiguous anchor reads the
      first point with the id, as `ground` does.
    - `successors`: a retired id's, from `retired-points`.
    - `sharing`: how many live points have the id.
    """

    id: str
    state: PointState
    standing: Standing | None = None
    successors: tuple[str, ...] = ()
    sharing: int = 0

    @property
    def dead(self) -> bool:
        """Whether the anchor is dead: the record holds no point an anchor can name by
        the id, and retires none (COR-050 point 7)."""
        return self.state in (PointState.MISSING, PointState.LIST_FORM)


@dataclass(frozen=True)
class RecordPoints:
    """One record's points, as `read_points` reads them.

    - `body`: the record's body, read once (`document_parts.Body`).
    - `front_matter`: its front matter, as written, or `{}` when it has none
      that parses to a mapping; `front_matter_problem` says why it does not
      parse, if it does not.
    - `decision`: the Decision's extent, or `None` without a Decision.
    - `level`: the points' level, or `None` while the Decision has no heading
      in point form.
    - `points` and `stubs`: the headings in point form at that level, in the
      body's order, the stubs apart.
    - `misspelt`: the Decision's headings that open with a number or a label
      in a form COR-058 point 1 refuses.
    - `retired`: each retired id with its successors, in written order;
      `retired_problems` names what of `retired-points` could not be read.
    - `list_points`: its points in list form, while it has no point heading
      or stub; once it has one, every numbered list in it is a list.
    """

    body: Body
    front_matter: Mapping[str, Any]
    decision: Extent | None
    level: int | None = None
    points: tuple[PointHeading, ...] = ()
    stubs: tuple[PointHeading, ...] = ()
    misspelt: tuple[Heading, ...] = ()
    retired: Mapping[str, tuple[str, ...]] = field(default_factory=dict[str, tuple[str, ...]])
    retired_problems: tuple[str, ...] = ()
    list_points: tuple[ListPoint, ...] = ()
    front_matter_problem: str | None = None

    @property
    def in_list_form(self) -> bool:
        """Whether its points are written as a list, not yet converted to headings."""
        return bool(self.list_points)

    def point(self, point_id: str) -> PointHeading | None:
        """The live point `point_id` names, the first when two share it, or `None`."""
        return next((point for point in self.points if point.id == point_id), None)

    def stub(self, point_id: str) -> PointHeading | None:
        """The stub of the retired id `point_id`, the first when two share it, or `None`."""
        return next((stub for stub in self.stubs if stub.id == point_id), None)

    def point_text(self, point: PointHeading) -> str:
        """A point's text read without its id (COR-058 point 8): its title, then its
        section after its heading's line, whitespace folded. A point keeps this text
        when only its id changes, so the numbering check finds a renumbered point by it."""
        return " ".join(f"{point.title} {self.point_words(point)}".split())

    def point_words(self, point: PointHeading) -> str:
        """A point's words: its section after its heading's line, whitespace folded."""
        section = self.body.text[point.extent.start : point.extent.end]
        _heading, _break, rest = section.partition("\n")
        return " ".join(rest.split())

    def list_point_words(self, point: ListPoint) -> str:
        """A list point's words: its text without its number and its bold lead,
        whitespace folded. Converting keeps every point's words and makes its bold lead
        its title (COR-058 point 9), so these are the words of the point heading it
        becomes (`point_words`), and the numbering check pairs the two by them."""
        text = self.body.text[point.start : point.end]
        if point.form is ListForm.ITEM:
            text = _ITEM_NUMBER.sub("", text, count=1)
        return " ".join(_BOLD_LEAD.sub("", text.lstrip(), count=1).split())

    def ground(self, point_id: str) -> PointGround | None:
        """What the live point `point_id` stands on, or `None` when no live point has
        that id: a retired id stands on nothing, whatever its stub says."""
        point = self.point(point_id)
        if point is None or self.decision is None:
            return None
        fields = {key: self.front_matter[key] for key in GROUND_FIELDS if key in self.front_matter}
        shared = [self._preamble()]
        summary = self._summary()
        if summary is not None:
            shared.append(summary)
        shared += self._outside_points()
        shared = sorted((e for e in shared if e.end > e.start), key=lambda e: e.start)
        return PointGround(point=point, fields=fields, extents=(point.extent, *shared))

    def standing(self, point_id: str) -> Standing | None:
        """What an anchor on the live point `point_id` stands on, as the checks compare it
        (`Standing`), from `ground`; `None` where it stands on nothing."""
        ground = self.ground(point_id)
        if ground is None:
            return None
        section, *shared = (self.body.text_of(extent) for extent in ground.extents)
        fields = tuple(
            (key, json.dumps(value, sort_keys=True, default=str, ensure_ascii=False))
            for key, value in sorted(ground.fields.items())
        )
        return Standing(fields, section, "\n".join(shared))

    def anchored(self, point_id: str) -> AnchoredPoint:
        """What an anchor on the point `point_id` finds in this record (COR-050 point 7).

        A live point with the id, or several, which makes the anchor ambiguous.
        Else the id the record retires, with its successors. Else, in a record
        whose points are a list, nothing an anchor can name, since a list's
        numbers are not permanent (COR-058 point 9). Else nothing at all.
        """
        sharing = sum(1 for point in self.points if point.id == point_id)
        if sharing:
            state = PointState.LIVE if sharing == 1 else PointState.AMBIGUOUS
            return AnchoredPoint(point_id, state, self.standing(point_id), sharing=sharing)
        if point_id in self.retired:
            return AnchoredPoint(point_id, PointState.RETIRED, successors=self.retired[point_id])
        if self.in_list_form:
            return AnchoredPoint(point_id, PointState.LIST_FORM)
        return AnchoredPoint(point_id, PointState.MISSING)

    def _preamble(self) -> Extent:
        """The text before the record's first section: before its first heading at the
        Decision's level or a higher one, not counting a higher heading that opens the
        body and so titles it. The line breaks around it are left out."""
        assert self.decision is not None and self.decision.heading is not None
        level = self.decision.heading.level
        text, headings = self.body.text, self.body.headings
        if headings and headings[0].level < level and not text[: headings[0].start].strip():
            headings = headings[1:]
        end = next((h.start for h in headings if h.level <= level), len(text))
        start = min(len(text) - len(text.lstrip("\n")), end)
        return Extent(start, start + len(text[start:end].rstrip("\n")))

    def _summary(self) -> Extent | None:
        """The first Summary section at the Decision's level, or `None`."""
        assert self.decision is not None and self.decision.heading is not None
        level = self.decision.heading.level
        for index, heading in enumerate(self.body.headings):
            if heading.level == level and heading.title == SUMMARY_TITLE:
                return self.body.section(index)
        return None

    def _outside_points(self) -> list[Extent]:
        """The Decision's text outside every point and stub: its lead, a group's text
        before its first point, and every sub-section that is neither."""
        assert self.decision is not None
        taken = sorted((p.extent for p in (*self.points, *self.stubs)), key=lambda e: e.start)
        gaps: list[Extent] = []
        cursor = self.decision.start
        for extent in [*taken, Extent(self.decision.end, self.decision.end)]:
            text = self.body.text[cursor : extent.start]
            if text.strip():
                start = cursor + len(text) - len(text.lstrip("\n"))
                gaps.append(Extent(start, cursor + len(text.rstrip("\n"))))
            cursor = max(cursor, extent.end)
        return gaps


def read_points(text: str) -> RecordPoints:
    """A decision record's points, read from its text (COR-058 points 1, 2, 4 and 6).

    The one reading of a record's points: the Decision's extent, its points and
    stubs, its misspelt headings, its retired ids with their successors and, in
    a record not yet converted, its points in list form. A point is looked for
    in the Decision only, so a `### 6.` heading in Rationale is never point 6.
    """
    written, body_text, problem = parse_front_matter(text)
    front_matter: Mapping[str, Any] = written if written is not None else {}
    body = Body.read(body_text)
    retired, retired_problems = _retired(front_matter.get(RETIRED_POINTS_KEY))
    decision = _decision(body)
    if decision is None:
        return RecordPoints(
            body=body,
            front_matter=front_matter,
            decision=None,
            retired=retired,
            retired_problems=retired_problems,
            front_matter_problem=problem,
        )
    inside = _headings_inside(body, decision)
    level = next((h.level for _index, h in inside if _point_id(h.title) is not None), None)
    headed: list[PointHeading] = []
    misspelt: list[Heading] = []
    for index, heading in inside:
        if level is not None and heading.level != level:
            continue
        found = _point_id(heading.title)
        if found is None:
            if _OPENS_WITH_ID.match(heading.title):
                misspelt.append(heading)
            continue
        point_id, title = found
        group = _group(body, decision, heading)
        headed.append(PointHeading(point_id, title, body.section(index), group))
    points = tuple(p for p in headed if not p.is_stub)
    stubs = tuple(p for p in headed if p.is_stub)
    return RecordPoints(
        body=body,
        front_matter=front_matter,
        decision=decision,
        level=level,
        points=points,
        stubs=stubs,
        misspelt=tuple(misspelt),
        retired=retired,
        retired_problems=retired_problems,
        list_points=() if headed else _list_points(body, decision),
        front_matter_problem=problem,
    )


def read_points_bytes(raw: bytes) -> RecordPoints | None:
    """`read_points` of a record read as bytes, from disk or from git, whatever its line
    endings; `None` when it is no UTF-8 text."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return read_points(universal_newlines(text))


def split_anchor(value: str) -> tuple[str, str | None]:
    """A record anchor's value as the record it names and the point, if it names one:
    `("COR-050", "11")` for `COR-050#11`, and `("COR-050", None)` for the whole record
    (COR-050 point 2). The value splits at its last `#`, the mark COR-051 point 3 gives
    a part of a record."""
    record, mark, point = value.rpartition(POINT_MARK)
    return (record, point) if mark else (value, None)


def id_series(point_id: str) -> tuple[str, int] | None:
    """A point id's series and number (COR-058 point 3): `("", 5)` for `5`, `("D", 1)`
    for `D1`, or `None` for what is no point id. Numbers and each series of labels
    count apart, so a new id is judged against the ids of its own series."""
    found = _SERIES.match(point_id)
    return (found.group(1), int(found.group(2))) if found else None


def stub_sentence(successors: Sequence[str]) -> str:
    """The one sentence a stub holds, written from its entry's successors (COR-058
    point 4): "Its content is in point 7.", "… in points 7 and 16.", "… in points 7,
    12 and 16.", or "Its content is in no other point." with none."""
    return f"Its content is in {successors_phrase(successors)}."


def successors_phrase(successors: Sequence[str]) -> str:
    """Where a retired point's content went, as its stub's sentence names it (COR-058
    point 4): "point 7", "points 7 and 16", "points 7, 12 and 16", or "no other point"."""
    if not successors:
        return "no other point"
    if len(successors) == 1:
        return f"point {successors[0]}"
    return f"points {', '.join(successors[:-1])} and {successors[-1]}"


class StubMismatchKind(Enum):
    """How a stub and its entry in `retired-points` disagree (COR-058 point 7)."""

    NO_STUB = "no-stub"  # a retired id with no stub
    NOT_RETIRED = "not-retired"  # a stub whose id `retired-points` does not retire
    SENTENCE = "sentence"  # a stub whose sentence differs from its entry's


@dataclass(frozen=True)
class StubMismatch:
    """One place a stub and its entry disagree.

    `stub` is the stub, `None` for a retired id with none. `expected` is the
    sentence the entry gives, and `found` the stub's text after its heading,
    whitespace folded; both are `None` where the stub or the entry is missing.
    """

    kind: StubMismatchKind
    id: str
    stub: PointHeading | None = None
    expected: str | None = None
    found: str | None = None


def hold_stubs(points: RecordPoints) -> tuple[StubMismatch, ...]:
    """Hold each stub to its entry in `retired-points`, both ways (COR-058 point 6).

    The entry is the source: the stub's heading and sentence follow it. Each
    retired id, in the entry's order, needs a stub whose text after its heading
    is the entry's sentence (`stub_sentence`), whitespace folded. Then each stub
    whose id the entry does not retire, in the body's order. Validation and the
    numbering check call it, so the two hold a stub alike.
    """
    mismatches: list[StubMismatch] = []
    for retired_id, successors in points.retired.items():
        stub = points.stub(retired_id)
        if stub is None:
            mismatches.append(StubMismatch(StubMismatchKind.NO_STUB, retired_id))
            continue
        expected = stub_sentence(successors)
        written = _stub_text(points.body, stub)
        if written != expected:
            mismatches.append(
                StubMismatch(StubMismatchKind.SENTENCE, retired_id, stub, expected, written)
            )
    for stub in points.stubs:
        if stub.id not in points.retired:
            written = _stub_text(points.body, stub)
            mismatches.append(
                StubMismatch(StubMismatchKind.NOT_RETIRED, stub.id, stub, None, written)
            )
    return tuple(mismatches)


# --- reading -------------------------------------------------------------------


def _retired(value: Any) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    """The retired ids with their successors, and what could not be read of them.

    A retired id or a successor written as a number reads as its digits. An
    entry whose successors are not a list of ids keeps its id, with the ids it
    does list, so its stub still reads as a stub.
    """
    if value is None:
        return {}, ()
    if not isinstance(value, Mapping):
        return {}, (f"`{RETIRED_POINTS_KEY}` is not a mapping of retired ids to their successors",)
    retired: dict[str, tuple[str, ...]] = {}
    problems: list[str] = []
    for key, successors in cast("Mapping[Any, Any]", value).items():
        retired_id = str(key)
        if not _POINT_ID.match(retired_id):
            problems.append(f"`{retired_id}` in `{RETIRED_POINTS_KEY}` is no point id")
            continue
        items: list[Any] = (
            cast("list[Any]", successors) if isinstance(successors, list) else [successors]
        )
        ids = tuple(str(item) for item in items if _is_id(item))
        if not isinstance(successors, list) or len(ids) != len(items):
            problems.append(
                f"the successors of `{retired_id}` in `{RETIRED_POINTS_KEY}` are not a list of "
                "point ids"
            )
        retired[retired_id] = ids
    return retired, tuple(problems)


def _is_id(item: Any) -> bool:
    return (
        isinstance(item, str | int)
        and not isinstance(item, bool)
        and bool(_POINT_ID.match(str(item)))
    )


def _decision(body: Body) -> Extent | None:
    """The section of the body's first `Decision` heading, or `None`."""
    for index, heading in enumerate(body.headings):
        if heading.title == DECISION_TITLE:
            return body.section(index)
    return None


def _headings_inside(body: Body, decision: Extent) -> list[tuple[int, Heading]]:
    """The headings within the Decision, its own left out, each with its index."""
    return [
        (index, heading)
        for index, heading in enumerate(body.headings)
        if decision.start < heading.start < decision.end
    ]


def _point_id(title: str) -> tuple[str, str] | None:
    """`(id, title)` of a heading in point form, or `None` (COR-058 point 1)."""
    found = _NUMBERED.match(title) or _LABELLED.match(title)
    return (found.group(1), found.group(2).strip()) if found else None


def _group(body: Body, decision: Extent, point: Heading) -> Heading | None:
    """The heading that gathers a point: the nearest one before it, within the
    Decision, at a level above the point's."""
    gathering: Heading | None = None
    for heading in body.headings:
        if heading.start >= point.start:
            break
        if decision.start < heading.start and heading.level < point.level:
            gathering = heading
    return gathering


# --- list form (COR-058 point 2) ---------------------------------------------------


@dataclass(frozen=True)
class _List:
    """One numbered list at the start of lines: its items, in order."""

    region: int  # the index of the region it sits in
    items: tuple[ListPoint, ...]

    @property
    def first(self) -> int:
        return int(self.items[0].id)

    @property
    def last(self) -> int:
        return int(self.items[-1].id)


def _list_points(body: Body, decision: Extent) -> tuple[ListPoint, ...]:
    """The points of a record not yet converted (COR-058 point 2).

    The Decision splits into regions: its lead, before its first sub-heading,
    then the text under each heading within it. A paragraph that opens with a
    bold number or a bold label holds a point wherever it sits. A numbered list
    holds points when it sits in the lead before any such paragraph, or when its
    numbering runs on, list after list, across the group headings one below the
    Decision: a run that continues the lead's list, or that spans two groups or
    more. Any other numbered list sits inside a point or another sub-section,
    and holds none.
    """
    assert decision.heading is not None
    group_level = decision.heading.level + 1
    regions = _regions(body, decision)
    found: list[ListPoint] = []
    in_groups: list[_List] = []
    lead_last: int | None = None
    for number, (heading, lines, end) in enumerate(regions):
        bold_seen = False
        bolds: list[ListPoint] = []
        for construct in _constructs(lines, end):
            if isinstance(construct, ListPoint):
                bolds.append(construct)
                bold_seen = True
            elif bold_seen:
                continue  # a list inside a bold point
            elif heading is None:
                found.extend(construct.items)
                lead_last = construct.last
            elif heading.level == group_level:
                in_groups.append(replace(construct, region=number))
        for index, bold in enumerate(bolds):  # each runs to the next, the last to the end
            stop = bolds[index + 1].start if index + 1 < len(bolds) else end
            found.append(replace(bold, end=stop))
    found.extend(item for run in _runs(in_groups, lead_last) for item in run.items)
    return tuple(sorted(found, key=lambda point: point.start))


def _runs(lists: Sequence[_List], lead_last: int | None) -> Iterator[_List]:
    """The lists in group regions whose numbering runs on across the groups.

    A list whose first number is one past the last of the lead's list starts the
    run that continues the lead, and each list one past that run's last joins it.
    That run holds points. Any other list joins the latest other run it continues,
    its first number one past the run's last, or starts a run of its own. Such a
    run holds points when it spans two regions or more. So a sub-section's steps
    never join the lead's numbering, whatever comes after them.
    """
    seeded: list[_List] = []
    runs: list[list[_List]] = []
    for found in lists:
        last = seeded[-1].last if seeded else lead_last
        if last is not None and found.first == last + 1:
            seeded.append(found)
            continue
        for members in reversed(runs):
            if found.first == members[-1].last + 1:
                members.append(found)
                break
        else:
            runs.append([found])
    yield from seeded
    for members in runs:
        if len({member.region for member in members}) > 1:
            yield from members


def _regions(body: Body, decision: Extent) -> list[tuple[Heading | None, list[Line], int]]:
    """The Decision's lead, then the text under each heading within it, each with
    its lines outside fenced code and where it ends: at the next heading within the
    Decision, or at the Decision's end. The Decision's heading line is no region's."""
    inside = [heading for _index, heading in _headings_inside(body, decision)]
    bounds = [heading.start for heading in inside] + [decision.end]
    regions: list[tuple[Heading | None, list[Line], int]] = [(None, [], bounds[0])]
    regions += [(heading, [], end) for heading, end in zip(inside, bounds[1:], strict=True)]
    for line in body.lines():
        if not decision.start < line.start < decision.end:
            continue
        if any(line.start == heading.start for heading in inside):
            continue  # a heading's own line
        region = sum(1 for bound in bounds[:-1] if bound <= line.start)
        regions[region][1].append(line)
    return regions


def _constructs(lines: Sequence[Line], end: int) -> Iterator[ListPoint | _List]:
    """A region's bold points and numbered lists, in order; the region ends at `end`.

    A list runs while its items follow one another, across blank lines and
    indented lines. A line at its start that is not an item ends it after a
    blank line, and at once when it opens a bullet, a quote or a bold point.
    An item's text runs to the next item, and the last one's to the line that
    ends the list, or to the region's end. A bold point is a paragraph's first
    line, so it follows a blank line or opens the region. Its text's end is set
    by the caller, which knows the next bold point.
    """
    items: list[ListPoint] = []
    blank_before = True
    index = 0
    while index < len(lines):
        line = lines[index]
        text = line.text
        item = _ITEM.match(text)
        if item is not None:
            start = int(item.group(1)) if not items else int(items[0].written)
            items.append(
                ListPoint(
                    id=str(start + len(items)),
                    form=ListForm.ITEM,
                    written=item.group(1),
                    title=_title(_paragraph(lines, index, (item.group(2) or ""))),
                    start=line.start,
                    end=end,
                )
            )
        elif text.strip() and not text[0].isspace():
            ends_now = bool(_ENDS_A_LIST.match(text) or _BOLD_POINT.match(text))
            if items and (blank_before or ends_now):
                yield _ended(items, line.start)
                items = []
            if blank_before:
                bold = _bold_point(lines, index)
                if bold is not None:
                    yield bold
        blank_before = not text.strip()
        index += 1
    if items:
        yield _ended(items, end)


def _ended(items: Sequence[ListPoint], end: int) -> _List:
    """A numbered list whose items' text each runs to the next item, the last to `end`."""
    ends = [item.start for item in items[1:]] + [end]
    return _List(
        region=0,
        items=tuple(replace(item, end=stop) for item, stop in zip(items, ends, strict=True)),
    )


def _bold_point(lines: Sequence[Line], index: int) -> ListPoint | None:
    """The point a paragraph opening with a bold number or a bold label holds, or `None`.

    Its title is its bold lead after the id, without a closing full stop, or `None`
    when the bold holds only the id.
    """
    line = lines[index]
    found = _BOLD_POINT.match(line.text)
    if found is None:
        return None
    number: str | None = found.group("number")
    point_id: str = number or found.group("label")
    lead = _BOLD_LEAD.match(_paragraph(lines, index, line.text))
    title = None
    if lead is not None:
        title = _LEAD_ID.sub("", lead.group(1).strip(), count=1).strip()
        title = title.removesuffix(".").strip() or None
    return ListPoint(
        id=point_id,
        form=ListForm.BOLD_NUMBER if number is not None else ListForm.BOLD_LABEL,
        written=point_id,
        title=title,
        start=line.start,
        end=line.start + len(line.text),
    )


def _paragraph(lines: Sequence[Line], index: int, first: str) -> str:
    """A paragraph's text, its lines joined by spaces: `first`, then each line after
    `lines[index]` up to a blank line or another item."""
    found = [first.strip()]
    for line in lines[index + 1 :]:
        if not line.text.strip() or _ITEM.match(line.text):
            break
        found.append(line.text.strip())
    return " ".join(found)


def _title(paragraph: str) -> str | None:
    """A numbered item's bold lead, without its closing full stop, or `None`."""
    lead = _BOLD_LEAD.match(paragraph)
    if lead is None:
        return None
    return lead.group(1).strip().removesuffix(".").strip() or None


def _stub_text(body: Body, stub: PointHeading) -> str:
    """A stub's text after its heading line, whitespace folded."""
    section = body.text[stub.extent.start : stub.extent.end]
    _heading, _break, rest = section.partition("\n")
    return " ".join(rest.split())
