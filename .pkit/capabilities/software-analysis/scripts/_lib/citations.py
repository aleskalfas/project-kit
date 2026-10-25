"""The citations of records and rules in an analysis's prose, and the links they take
(DEC-001 point 13).

**What a citation is** (`_CITATION`), whole, in running text:

- **a record:** `COR-050`, `PRJ-002`, `ADR-065`; a capability's decision with its
  capability's name before it, `software-analysis DEC-001`, possessive or not, or
  `software-analysis:DEC-001`, or in brackets, `[software-analysis:DEC-001]`, with its
  slug or without;
- **its points,** after the record: `point 14`, `point D1`, `points 6 and 9`,
  `points 1, 2 and 4`, or a label alone, `PRJ-002 D1`, `PRJ-002 D1 and D4`;
- **a rule:** `RS-WRITE-005`, `software-analysis:RS-SAN-001` or
  `[software-analysis:RS-SAN-001]`.

No letter, digit, slash, `#` or hyphen joined to a word may join a citation on either
side, so `COR-050-anchors` and `decisions/COR-050` hold none. A possessive's `'s` stays
outside it.

**A capability's decision.** A word right before `DEC-NNN`, possessive or not, is read
as its capability's name, and the citation names no capability where the lookup finds
no decision of that name. A `DEC-NNN` that follows a citation in one list, joined by a
comma or `and`, is the same capability's, as in `project-management DEC-008 and
DEC-029`. Only a `DEC-NNN` with neither is the decision of the capability whose
analysis it is, the analysis's component. Each way to read a citation is a `Reading`,
tried in order: the first whose record the lookup finds is the citation's.

**What it links to,** through the backbone's lookup alone (`backbone.lookup`), never a
folder walked here: a record cited whole, its file; a point, its file and the anchor the
host gives its heading; a rule, its rule set and its heading's anchor. A citation of a
record, of one point or of a rule is one link around the whole citation; in one of
several points, each point's id is a link of its own (`Piece`). Where the record gives
its points no heading, since it writes them as a list, the citation is one link to its
file. A point its record does not hold links to the record, and is noted. A label alone
that is no point of its record is no part of the citation, which cites the record
whole.

**Once in each section:** only the first citation of each target in a section takes a
link, and a citation right after `<!-- pkit:not-a-citation -->`, with nothing but spaces
between, takes none and counts for nothing. A citation that resolves to nothing takes no
link, and is noted (`Note`): the check warns of it.

The citations of one text are found on the text with the links the command writes
taken out, and the spans the caller skips (`_lib/links.py`: code, headings, labels,
comments, other links and markup) never hold one.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

#: The comment that marks the citation right after it as no citation.
ESCAPE = "<!-- pkit:not-a-citation -->"
_ESCAPE = re.compile(r"<!--\s*pkit:not-a-citation\s*-->")

#: A capability's or a component's name; white space within a paragraph; a point's id, a
#: number or a label; a label alone; a rule's id; what may not follow a citation's id;
#: a record's slug; and a possessive's `'s`, an apostrophe of either kind.
_CAP = r"[a-z](?:[a-z0-9-]*[a-z0-9])?"
_SP = r"(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)"
_PID = r"(?:[0-9]+|[A-Z]+[0-9]+)"
_LABEL = r"[A-Z]+[0-9]+"
_RULE = r"RS-[A-Z][A-Z0-9]*-(?:[0-9]{3}|[1-9][0-9]{3,})"
_END = r"(?![\w/#]|-\w)"
_SLUG = r"(?:-[a-z0-9]+)*"
_POSSESSIVE = "(?:['" + chr(0x2019) + "]s)?"

_CITATION = re.compile(
    rf"""
    (?:
        (?<![!\]\w])\[(?P<brcap>{_CAP}):(?P<brule>{_RULE})\](?![(\[])
      | (?<![\w/\#:-])(?:(?P<rcap>{_CAP}):)?(?P<rule>{_RULE}){_END}
      | (?:
            (?<![!\]\w])\[(?P<bcap>{_CAP}):(?P<bdec>DEC-[0-9]+)(?P<bslug>{_SLUG})\](?![(\[])
          | (?<![\w/\#:-])
            (?:
                (?P<ccap>{_CAP}):(?P<cdec>DEC-[0-9]+)(?P<cslug>{_SLUG})
              | (?:(?P<pcap>{_CAP}){_POSSESSIVE}{_SP})?(?P<pdec>DEC-[0-9]+)
              | (?P<core>(?:COR|PRJ|ADR)-[0-9]+)
            )
            {_END}
        )
        (?:{_SP}
            (?:
                point{_SP}(?P<one>{_PID}){_END}
              | points{_SP}(?P<many>
                    {_PID}{_END}(?:,{_SP}{_PID}{_END})*,?{_SP}and{_SP}{_PID}{_END}
                )
              | (?P<labels>
                    {_LABEL}{_END}(?:,{_SP}{_LABEL}{_END})*(?:,?{_SP}and{_SP}{_LABEL}{_END})?
                )
            )
        )?
    )
    """,
    re.X,
)

#: One id inside a list of points.
_ONE_ID = re.compile(rf"(?<![\w-]){_PID}(?![\w-])")

#: What joins two citations of one list: a comma, `and`, or both.
_JOINER = re.compile(rf"^(?:,{_SP}|,?{_SP}and{_SP})$")

#: A link's text that is a point's id alone, and the name of a record's file.
POINT_ID = re.compile(rf"^{_PID}$")
RECORD_FILE = re.compile(r"^(?:COR|PRJ|ADR|DEC)-[0-9]+(?:[-.]|$)")

#: What a note says of a `DEC-NNN` no capability's decision answers, and of a citation
#: the lookup finds nothing for.
NO_CAPABILITY = (
    "it names no capability whose decision the lookup finds: write its capability's name "
    "before it, as in `<capability> DEC-NNN`"
)
NOTHING = "the lookup finds nothing it names"


@dataclass(frozen=True)
class Found:
    """What the lookup answers for one citation: the file, repository-relative, the host's
    anchor of a cited heading, and why it does not resolve, each `None` where there is
    none; and whether the file arrives in the repository as a synced copy, which the
    project receives and does not write. A point its record does not hold has its
    record's file and a problem."""

    path: str | None
    anchor: str | None = None
    problem: str | None = None
    received: bool = False

    @property
    def resolved(self) -> bool:
        return self.path is not None and self.problem is None

    def target(self, from_path: str, *, whole: bool = False) -> str:
        """Where a link to it leads from the file at `from_path`: its heading, or, `whole`,
        its file."""
        assert self.path is not None
        rel = posixpath.relpath(self.path, posixpath.dirname(from_path) or ".")
        return f"{rel}#{self.anchor}" if self.anchor and not whole else rel


@dataclass(frozen=True)
class Piece:
    """One link a citation takes: where its text lies, and what the lookup is asked."""

    start: int
    end: int
    key: str


@dataclass(frozen=True)
class Reading:
    """One way to read a citation: where it starts read so, the record or rule the lookup
    is asked for and where its id ends, the capability it names, if any, its links, and
    whether its points are labels alone, with no `point` before them."""

    start: int
    record: str
    record_end: int
    capability: str | None
    pieces: tuple[Piece, ...]
    labels: bool = False


@dataclass(frozen=True)
class Citation:
    """A citation as written: where it lies, and each way to read it, in order. A
    `DEC-NNN` cited with no capability before it in brackets or a colon gives where its id
    starts, from which it is noted where no reading resolves."""

    start: int
    end: int
    readings: tuple[Reading, ...]
    bare: int | None = None

    @property
    def unresolved_start(self) -> int:
        """Where it starts as noted, where no reading resolves."""
        if self.bare is not None:
            return self.bare
        return self.readings[0].start if self.readings else self.start


@dataclass(frozen=True)
class Wanted:
    """A link the command writes: its text's span, its target, and whether its file is one
    the project receives."""

    start: int
    end: int
    target: str
    received: bool = False


@dataclass(frozen=True)
class Note:
    """A citation that takes no link since it resolves to nothing, or a point its record
    does not hold, and why."""

    start: int
    end: int
    why: str


@dataclass(frozen=True)
class Placed:
    """What the citations of one text want: the links, the notes, and the span of each
    citation, which no mention of a term is read in."""

    links: tuple[Wanted, ...]
    notes: tuple[Note, ...]
    spans: tuple[tuple[int, int], ...]


def found(text: str, skipped: Sequence[tuple[int, int]], component: str | None) -> list[Citation]:
    """The citations in `text`, none in a span of `skipped`, each with its readings, in
    order, for a `DEC-NNN`: of the capability named right before it; else of the one a
    citation right before it in one list names; else of `component`, the analysis's
    own."""
    masked = _masked(text, skipped)
    cited: list[Citation] = []
    carry: tuple[int, str | None] | None = None  # where the last citation ended, its capability
    for match in _CITATION.finditer(masked):
        # A `DEC-NNN` joined to the citation before it is listed with it, whatever word the
        # pattern read before it: `DEC-008 and DEC-029` reads no capability `and`.
        at = match.start("pdec") if match.group("pdec") else match.start()
        joined = carry is not None and _JOINER.match(text[carry[0] : at]) is not None
        citation = _citation(match, joined, carry[1] if joined and carry else None, component)
        cited.append(citation)
        carry = (match.end(), next((r.capability for r in citation.readings if r.capability), None))
    return cited


def _masked(text: str, spans: Iterable[tuple[int, int]]) -> str:
    """`text` with each of `spans` written over by a character no citation holds, its line
    ends kept, so no citation is read across one."""
    chars = list(text)
    for start, end in spans:
        for k in range(start, min(end, len(chars))):
            if chars[k] != "\n":
                chars[k] = "\x00"
    return "".join(chars)


def _citation(
    match: re.Match[str], joined: bool, listed: str | None, component: str | None
) -> Citation:
    """The citation `match` holds, with each way to read it, in order."""
    start, end = match.start(), match.end()
    rule = match.group("brule") or match.group("rule")
    if rule is not None:
        cap = match.group("brcap") or match.group("rcap")
        key = f"{cap}:{rule}" if cap else rule
        return Citation(start, end, (Reading(start, key, end, cap, (Piece(start, end, key),)),))
    if match.group("bdec") or match.group("cdec"):
        cap = match.group("bcap") or match.group("ccap")
        group = "bdec" if match.group("bdec") else "cdec"
        slug = match.group("bslug") or match.group("cslug") or ""
        record_end = match.end("bslug") + 1 if group == "bdec" else match.end("cslug")
        record = f"{cap}:{match.group(group)}{slug}"
        return Citation(start, end, (_reading(match, start, record, record_end, cap),))
    if match.group("core"):
        core = match.group("core")
        return Citation(start, end, (_reading(match, start, core, match.end("core"), None),))
    dec, at = match.group("pdec"), match.start("pdec")
    named = None if joined else match.group("pcap")
    if named:
        reading = _reading(match, start, f"{named}:{dec}", match.end("pdec"), named)
        return Citation(start, end, (reading,), bare=at)
    caps = dict.fromkeys(c for c in ((listed if joined else None), component) if c)
    readings = tuple(_reading(match, at, f"{c}:{dec}", match.end("pdec"), c) for c in caps)
    return Citation(at, end, readings, bare=at)


def _reading(
    match: re.Match[str], start: int, record: str, record_end: int, cap: str | None
) -> Reading:
    """`match` read from `start` as a citation of `record`: one link around it where it
    names the record whole or one point, and one around each id where it names several."""
    end = match.end()
    if match.group("one"):
        piece = Piece(start, end, f"{record}#{match.group('one')}")
        return Reading(start, record, record_end, cap, (piece,))
    group = "many" if match.group("many") else "labels" if match.group("labels") else None
    if group is None:
        return Reading(start, record, record_end, cap, (Piece(start, end, record),))
    labels = group == "labels"
    offset = match.start(group)
    ids = list(_ONE_ID.finditer(match.group(group)))
    if len(ids) == 1:
        piece = Piece(start, end, f"{record}#{ids[0].group()}")
        return Reading(start, record, record_end, cap, (piece,), labels)
    pieces = tuple(
        Piece(offset + i.start(), offset + i.end(), f"{record}#{i.group()}") for i in ids
    )
    return Reading(start, record, record_end, cap, pieces, labels)


def keys(citations: Iterable[Citation]) -> set[str]:
    """What the lookup is asked for `citations`: each reading's record or rule, and each of
    its pieces."""
    asked: set[str] = set()
    for citation in citations:
        for reading in citation.readings:
            asked.add(reading.record)
            asked.update(piece.key for piece in reading.pieces)
    return asked


def chosen(citation: Citation, lookups: Mapping[str, Found]) -> Reading | None:
    """The first reading whose record or rule the lookup finds, `None` where none is."""
    return next((r for r in citation.readings if _of(lookups, r.record).resolved), None)


def _of(lookups: Mapping[str, Found], key: str) -> Found:
    return lookups.get(key) or Found(None, None, f"{key} was not looked up")


def placed(
    text: str,
    skipped: Sequence[tuple[int, int]],
    hidden: Sequence[tuple[int, int]],
    component: str | None,
    lookups: Mapping[str, Found],
    path: str,
    opens: Sequence[int] = (),
) -> Placed:
    """The links the citations of one section's `text` take, from the file at `path`: the
    first citation of each target, none right after the escape; the notes of those that
    resolve to nothing, or name a point their record does not hold; and the span of each
    citation. `skipped` are the spans no citation is read in, and `hidden` the whole lines
    no escape is read on. Each offset of `opens` opens a new section, where each target
    takes its link again."""
    masked = _masked(text, hidden)
    escapes = [m.end() for m in _ESCAPE.finditer(masked)]
    links: list[Wanted] = []
    notes: list[Note] = []
    spans: list[tuple[int, int]] = []
    seen: set[str] = set()
    ahead = sorted(opens)
    for citation in found(text, skipped, component):
        while ahead and citation.start >= ahead[0]:
            ahead.pop(0)
            seen.clear()
        reading = chosen(citation, lookups)
        if reading is not None and reading.labels and not _all_points(reading, lookups):
            # A label alone that is no point of its record is no part of the citation.
            whole = Piece(reading.start, reading.record_end, reading.record)
            reading = Reading(reading.start, reading.record, reading.record_end, None, (whole,))
        start = reading.start if reading is not None else citation.unresolved_start
        stop = reading.pieces[-1].end if reading is not None else citation.end
        spans.append((start, stop))
        before = citation.start
        if any(text[end:before].strip(" \t") == "" for end in escapes if end <= before):
            continue
        if reading is None:
            notes.append(Note(start, citation.end, _unresolved(citation, lookups)))
            continue
        for want, note in _wanted(reading, lookups, path, start, stop):
            if note is not None:
                notes.append(note)
            if want is not None and want.target not in seen:
                seen.add(want.target)
                links.append(want)
    return Placed(tuple(links), tuple(notes), tuple(spans))


def _all_points(reading: Reading, lookups: Mapping[str, Found]) -> bool:
    return all(_of(lookups, piece.key).resolved for piece in reading.pieces)


def _wanted(
    reading: Reading, lookups: Mapping[str, Found], path: str, start: int, stop: int
) -> list[tuple[Wanted | None, Note | None]]:
    """The link of each piece of a reading that resolves, and the note of each point its
    record does not hold, which links to the record. A citation of several points whose
    record gives them no heading is one link to its file."""
    answers = [_of(lookups, piece.key) for piece in reading.pieces]
    if len(answers) > 1 and all(a.resolved and a.anchor is None for a in answers):
        record = _of(lookups, reading.record)
        return [(Wanted(start, stop, record.target(path), record.received), None)]
    out: list[tuple[Wanted | None, Note | None]] = []
    for piece, answer in zip(reading.pieces, answers, strict=True):
        if answer.resolved:
            out.append((Wanted(piece.start, piece.end, answer.target(path), answer.received), None))
            continue
        note = Note(piece.start, piece.end, answer.problem or NOTHING)
        if answer.path is None:
            out.append((None, note))
            continue
        # A point its record does not hold: the record still leads the reader.
        target = answer.target(path, whole=True)
        out.append((Wanted(piece.start, piece.end, target, answer.received), note))
    return out


def _unresolved(citation: Citation, lookups: Mapping[str, Found]) -> str:
    """Why a citation takes no link: a `DEC-NNN` names no capability's decision the lookup
    finds, or the lookup finds no record or rule for it."""
    if citation.bare is not None or not citation.readings:
        return NO_CAPABILITY
    return _of(lookups, citation.readings[0].record).problem or NOTHING


def is_citation(text: str) -> bool:
    """Whether `text`, a link's text, is a citation whole."""
    return _CITATION.fullmatch(text) is not None


def is_cited_link(text: str, target: str) -> bool:
    """Whether a Markdown link with `text` and `target` is one the command writes, or one
    written by hand that it holds as its own: its target a path with no scheme to a
    Markdown file, and its text a citation whole, or a point's id leading into a record's
    file."""
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
        return False
    file, _mark, _anchor = target.partition("#")
    if not file.endswith(".md"):
        return False
    if is_citation(text):
        return True
    named = RECORD_FILE.match(posixpath.basename(file)) is not None
    return POINT_ID.match(text) is not None and named
