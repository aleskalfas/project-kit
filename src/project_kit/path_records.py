"""The accepted records a path's anchors lead to (#2165).

`pkit refs records-for` goes from a path to the accepted records the anchors tie to it,
the other way from `pkit refs lookup`, which goes from an id to its file. It reads the
one artefact discovery of the working tree (`friction_discovery.discover_artefacts`,
COR-050 point 1) and declares nothing new. Three ties, each read from anchors COR-050
point 2 already decides, in two kinds:

- **Direct.** `record`: a record file a place holds carries a path anchor that matches
  the path, so it ties itself, whole. `artefact`: the path is the file of an artefact
  that carries a record anchor, so it ties that record, whole or the points it names.
- **Through an artefact.** `through`: an artefact carries a path anchor that matches the
  path, and a record anchor. Its path anchors and its record anchors are two lists with
  no pairing, so the tie says only that the artefact rests on the record. The answer
  lists such artefacts apart, each with the records it rests on, the narrowest first.

A path anchor matches as both friction checks match it (`pattern_matcher`). A path
under `friction.exclude` is one no path anchor stands on (COR-050 point 7), so only the
artefact at it ties anything. An artefact the project receives by sync ties nothing,
since its anchors were written for the tree where the methodology is authored (COR-062
point 9). Nor does a path anchor of a record that is not accepted, whose anchors are a
draft's or a replaced record's.

Only accepted records are listed (the acceptance gate in `.pkit/decisions/README.md`).
A superseded record an anchor names stands for each accepted record that replaces it,
named in the successor's `supersedes` or the record's own `superseded_by`. A record
anchor that names no record is the checks' and validation's to report. Artefact anchors,
and anchors of a kind a capability registers, are not followed.

The project's own records come first, then those it receives by sync, as `pkit refs
lookup --json` tells them (`decisions_validate.synced_record_test`).
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, cast

from project_kit import cli_render, document_parts, friction_check, refs
from project_kit import friction_discovery as fd
from project_kit.decisions_validate import discover_decision_records, synced_record_test
from project_kit.record_points import id_series, split_anchor, successors_phrase

#: The version of the document `pkit refs records-for --json` prints.
RECORDS_FOR_VERSION = 1

#: How an artefact ties a record to a path (the module's docstring).
How = Literal["record", "artefact", "through"]

#: The id-spaces in the order records are listed within the project's own and within
#: those received: the project's kinds first, then a capability's, then the core's.
_SPACE_ORDER = ("PRJ", "ADR", "DEC", "COR")

ACCEPTED = "accepted"
SUPERSEDED = "superseded"


@dataclass(frozen=True)
class Record:
    """An accepted record: its id as an anchor names it without its slug (`COR-050`,
    `project-management:DEC-055`), its title, its file relative to the root, and whether
    that file arrives as a synced copy."""

    id: str
    title: str | None
    path: str
    received: bool

    def as_json(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "path": self.path, "received": self.received}


@dataclass(frozen=True)
class Tie:
    """How one artefact ties an accepted record to a path.

    - `how`: `record`, `artefact` or `through` (the module's docstring).
    - `artefact`: the location of the artefact that carries the anchors.
    - `anchor`: the first of its path anchors, in written order, that matches the path;
      `None` for `artefact`, which ties by where the artefact is.
    - `points`: the points of the record its record anchors name, in their order; empty
      where one of them names the record whole, and for `record`.
    - `in_place_of`: the superseded record the anchor names, where `record` replaces it.
    """

    record: Record
    how: How
    artefact: str
    anchor: str | None
    points: tuple[str, ...] = ()
    in_place_of: str | None = None

    @property
    def direct(self) -> bool:
        return self.how != "through"

    def named(self) -> dict[str, Any]:
        """What the tie names of its record, for the document."""
        return {"points": list(self.points), "in_place_of": self.in_place_of}


@dataclass(frozen=True)
class Through:
    """An artefact that anchors the path, by its first matching path anchor, and the ties
    of each accepted record it rests on, in the records' order."""

    artefact: str
    anchor: str
    ties: tuple[Tie, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "artefact": self.artefact,
            "anchor": self.anchor,
            "records": [{**tie.record.as_json(), **tie.named()} for tie in self.ties],
        }


@dataclass(frozen=True)
class PathRecords:
    """The answer for one path: the `friction.exclude` entry it lies under, as written,
    or `None`, and every tie of an accepted record to it."""

    path: str
    excluded_by: str | None
    ties: tuple[Tie, ...]

    @property
    def direct(self) -> tuple[tuple[Record, tuple[Tie, ...]], ...]:
        """Each record tied directly, in the records' order, with its direct ties."""
        grouped: dict[Record, list[Tie]] = {}
        for tie in self.ties:
            if tie.direct:
                grouped.setdefault(tie.record, []).append(tie)
        return tuple(
            (record, tuple(grouped[record])) for record in sorted(grouped, key=_record_order)
        )

    @property
    def through(self) -> tuple[Through, ...]:
        """Each artefact that anchors the path and rests on an accepted record, the one
        resting on the fewest records first: the narrower an artefact, the closer a
        record it rests on is to the path."""
        grouped: dict[tuple[str, str], list[Tie]] = {}
        for tie in self.ties:
            if not tie.direct and tie.anchor is not None:
                grouped.setdefault((tie.artefact, tie.anchor), []).append(tie)
        found = [
            Through(artefact, anchor, tuple(sorted(ties, key=lambda t: _record_order(t.record))))
            for (artefact, anchor), ties in grouped.items()
        ]
        return tuple(sorted(found, key=lambda t: (len(t.ties), t.artefact)))

    def as_json(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "excluded_by": self.excluded_by,
            "direct": [
                {
                    **record.as_json(),
                    "ties": [
                        {"how": t.how, "artefact": t.artefact, "anchor": t.anchor, **t.named()}
                        for t in ties
                    ],
                }
                for record, ties in self.direct
            ],
            "through": [through.as_json() for through in self.through],
        }


@dataclass(frozen=True)
class Answer:
    """What `pkit refs records-for` answers: each path's ties, how many artefacts carry
    anchors at all, and the files in the places whose front matter could not be read, so
    whose anchors were not read."""

    paths: tuple[PathRecords, ...]
    anchored: int
    unreadable: tuple[str, ...] = field(default=())

    def as_json(self) -> dict[str, Any]:
        return {
            "schema_version": RECORDS_FOR_VERSION,
            "anchored": self.anchored,
            "unreadable": list(self.unreadable),
            "paths": [path.as_json() for path in self.paths],
        }


def repository_path(target_root: Path, given: str, cwd: Path) -> str:
    """The repository-relative POSIX path of `given`, read from `cwd` when it is
    relative. It need not exist, since a file about to be written has records too.
    Raises `ValueError`, saying why, for a folder, one written with a trailing slash
    included, and for a path outside the repository."""
    candidate = Path(given) if os.path.isabs(given) else cwd / given
    resolved = Path(os.path.realpath(candidate))
    try:
        rel = resolved.relative_to(target_root.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"{given!r} lies outside the repository") from None
    if rel == "." or resolved.is_dir() or given.endswith(("/", os.sep)):
        raise ValueError(f"{given!r} names a folder: give the files in it")
    return rel


def records_for(target_root: Path, paths: Sequence[str]) -> Answer:
    """The ties of accepted records to each repository-relative path, in the order the
    paths are given (the module's docstring says how)."""
    discovery = fd.discover_artefacts(target_root)
    artefacts = [a for a in discovery.artefacts if not a.received]
    records = _Records(target_root)
    return Answer(
        paths=tuple(_records_for(path, artefacts, discovery.settings, records) for path in paths),
        anchored=sum(1 for a in artefacts if any(a.anchors.values())),
        unreadable=tuple(sorted({u.path for u in discovery.unreadable if u.rule_set is None})),
    )


def render_human(answer: Answer) -> str:
    """What `pkit refs records-for` prints: for each path, the records tied to it directly,
    then the artefacts that anchor it, each with the records it rests on."""
    lines: list[str] = []
    if not answer.anchored:
        lines.append("No artefact in this project carries anchors, so no path leads to a record.")
    if answer.unreadable:
        count = len(answer.unreadable)
        lines.append(
            f"{count} file{'' if count == 1 else 's'} in the declared places could not be "
            "read, so their anchors were not read: `pkit validate` reports "
            f"{'it' if count == 1 else 'them'}."
        )
    for found in answer.paths:
        lines.extend(_path_lines(found))
    return "\n".join(lines) + "\n"


def _path_lines(found: PathRecords) -> Iterator[str]:
    direct, through = found.direct, found.through
    yield cli_render.style(
        "title",
        f"{found.path}: {_count(len(direct), 'record')} tied directly, "
        f"{_count(len(through), 'artefact')} anchoring it",
    )
    if found.excluded_by is not None:
        yield (
            f"  It lies under {found.excluded_by}, which friction.exclude leaves out, "
            "so no path anchor stands on it."
        )
    if not direct and not through:
        yield (
            "  No anchor ties an accepted record to this path. "
            "That is no sign that none governs it."
        )
        return
    if direct:
        yield "  " + cli_render.style("heading", "Tied directly:")
        for record, ties in direct:
            yield f"    {_record_line(record)}"
            yield from (f"      {_direct_line(tie)}" for tie in ties)
    else:
        yield "  No record is tied to it directly."
    if through:
        yield "  " + cli_render.style(
            "heading", "Through the artefacts that anchor it, the narrowest first:"
        )
        for each in through:
            yield (
                f"    {each.artefact}, by {each.anchor}, rests on "
                f"{_count(len(each.ties), 'record')}:"
            )
            yield "      " + "; ".join(_named(tie) for tie in each.ties)


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def _record_line(record: Record) -> str:
    title = f"  {record.title}" if record.title else ""
    received = ", received by sync" if record.received else ""
    return f"{cli_render.style('strong', record.id)}{title}  ({record.path}{received})"


def _direct_line(tie: Tie) -> str:
    named = successors_phrase(tie.points) if tie.points else "whole"
    if tie.in_place_of is not None:
        named += f", in place of {tie.in_place_of}, which it supersedes"
    if tie.how == "record":
        return f"{named}, by its own anchor {tie.anchor}"
    return f"{named}, by {tie.artefact}, the artefact at this path"


def _named(tie: Tie) -> str:
    named = tie.record.id
    if tie.points:
        named += f" {successors_phrase(tie.points)}"
    if tie.in_place_of is not None:
        named += f" (in place of {tie.in_place_of})"
    return named


# --- the reading ------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Found:
    """A record, read once: its id, its file, its title and its status."""

    id: str
    path: str
    title: str | None
    status: Any
    superseded_by: tuple[str, ...] = ()


class _Records:
    """Each record an anchor names, resolved and read once (`refs.resolve_record`), its
    successors where it is superseded, and whether its file arrives as a synced copy."""

    def __init__(self, target_root: Path) -> None:
        self.root = target_root
        self._by_value: dict[str, _Found | None] = {}
        self._by_path: dict[str, _Found | None] = {}
        self._successors: dict[str, list[str]] | None = None
        self._received = synced_record_test(target_root)

    def named(self, value: str) -> _Found | None:
        """The record an anchor's record part names, or `None` where none is found."""
        if value not in self._by_value:
            path = refs.resolve_record(self.root, value)
            rel = None if path is None else _relative(self.root, path)
            self._by_value[value] = None if rel is None else self.at(rel)
        return self._by_value[value]

    def at(self, rel: str) -> _Found | None:
        """The record whose file is `rel`, or `None` where `rel` is no record's file."""
        if rel not in self._by_path:
            record_id = friction_check.record_naming(self.root, rel)
            self._by_path[rel] = None if record_id is None else self._read(record_id, rel)
        return self._by_path[rel]

    def accepted(self, found: _Found | None) -> list[tuple[Record, str | None]]:
        """The accepted record `found` is, or, where it is superseded, each accepted record
        that replaces it, followed through records superseded in turn, with the id it
        stands in place of. Nothing for a record neither accepted nor superseded."""
        if found is None:
            return []
        if found.status == ACCEPTED:
            return [(self.record(found), None)]
        if found.status != SUPERSEDED:
            return []
        stands: list[tuple[Record, str | None]] = []
        seen = {found.id}
        queue = list(self.successors(found))
        while queue:
            successor = self.named(queue.pop(0))
            if successor is None or successor.id in seen:
                continue
            seen.add(successor.id)
            if successor.status == ACCEPTED:
                stands.append((self.record(successor), found.id))
            elif successor.status == SUPERSEDED:
                queue.extend(self.successors(successor))
        return stands

    def record(self, found: _Found) -> Record:
        return Record(found.id, found.title, found.path, self._received(found.path))

    def successors(self, found: _Found) -> list[str]:
        """The ids of the records that replace `found`: those its `superseded_by` names,
        then those whose `supersedes` names it, read once from every record."""
        if self._successors is None:
            self._successors = {}
            for each in discover_decision_records(self.root):
                rel = _relative(self.root, each.path)
                read = None if rel is None else self.at(rel)
                if read is None:
                    continue
                for replaced in self._supersedes(read):
                    self._successors.setdefault(replaced, []).append(read.id)
        return list(dict.fromkeys([*found.superseded_by, *self._successors.get(found.id, [])]))

    def _supersedes(self, found: _Found) -> list[str]:
        text = self._front(found.path).get("supersedes")
        return [_in_space(found.id, value) for value in _texts(text)]

    def _front(self, rel: str) -> dict[str, Any]:
        try:
            text = (self.root / rel).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            return {}
        front, _body, _reason = document_parts.parse_front_matter(text)
        return dict(front) if front is not None else {}

    def _read(self, record_id: str, rel: str) -> _Found | None:
        front = self._front(rel)
        if not front:
            return None
        title = front.get("title")
        return _Found(
            id=record_id,
            path=rel,
            title=title if isinstance(title, str) else None,
            status=front.get("status"),
            superseded_by=tuple(
                _in_space(record_id, v) for v in _texts(front.get("superseded_by"))
            ),
        )


def _texts(value: Any) -> list[str]:
    """A field that names one record, or a list of them, as its texts."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in cast(list[Any], value) if isinstance(item, str)]
    return []


def _in_space(record_id: str, named: str) -> str:
    """A record id a record's own field names, read as an anchor names it: a capability's
    bare `DEC-NNN` within that capability, without its slug."""
    capability, colon, _bare = record_id.rpartition(":")
    if colon and named.startswith("DEC-") and ":" not in named:
        return f"{capability}:{'-'.join(named.split('-')[:2])}"
    return named


def _records_for(
    path: str, artefacts: Iterable[fd.Artefact], settings: fd.FrictionSettings, records: _Records
) -> PathRecords:
    excluded = settings.exclusion(path)
    ties: list[Tie] = []
    for artefact in artefacts:
        own = records.at(artefact.path)
        draft = own is not None and own.status != ACCEPTED
        anchor = None if excluded is not None or draft else _matching(artefact, path)
        at_path = artefact.path == path
        if anchor is None and not at_path:
            continue
        if anchor is not None and own is not None:
            ties.append(Tie(records.record(own), "record", artefact.location, anchor))
        for found, points in _anchored_records(artefact, records):
            for record, in_place_of in records.accepted(found):
                named = () if in_place_of is not None else points
                if at_path:
                    ties.append(
                        Tie(record, "artefact", artefact.location, None, named, in_place_of)
                    )
                if anchor is not None:
                    ties.append(
                        Tie(record, "through", artefact.location, anchor, named, in_place_of)
                    )
    return PathRecords(
        path=path,
        excluded_by=None if excluded is None else excluded.value,
        ties=tuple(_merged(ties)),
    )


def _merged(ties: list[Tie]) -> list[Tie]:
    """One tie for each record, kind and artefact. An artefact that names a record and a
    record it replaces, or two records it replaces, ties it once: whole where either names
    it whole, and in place of a replaced record only where both stand in place of one."""
    merged: dict[tuple[str, str, str], Tie] = {}
    for tie in ties:
        key = (tie.record.id, tie.how, tie.artefact)
        kept = merged.get(key)
        if kept is None:
            merged[key] = tie
            continue
        points = _in_order([*kept.points, *tie.points]) if kept.points and tie.points else ()
        in_place_of = kept.in_place_of if tie.in_place_of is not None else None
        merged[key] = replace(kept, points=points, in_place_of=in_place_of)
    return sorted(merged.values(), key=lambda t: (_record_order(t.record), t.artefact))


def _matching(artefact: fd.Artefact, path: str) -> str | None:
    """The first of the artefact's path anchors, in written order, that matches `path`."""
    return next(
        (value for value in artefact.anchors_of_kind("path") if fd.pattern_matcher(value)(path)),
        None,
    )


def _anchored_records(
    artefact: fd.Artefact, records: _Records
) -> list[tuple[_Found | None, tuple[str, ...]]]:
    """Each record the artefact's record anchors name, once, in written order, with the
    points they name: none where one of them names it whole."""
    named: dict[str, tuple[_Found | None, list[str] | None]] = {}
    for value in artefact.anchors_of_kind("record"):
        record_part, point = split_anchor(value)
        found = records.named(record_part)
        key = found.id if found is not None else record_part
        _kept, points = named.get(key, (found, []))
        named[key] = (found, None if points is None or point is None else [*points, point])
    return [(found, _in_order(points or [])) for found, points in named.values()]


def _in_order(points: Iterable[str]) -> tuple[str, ...]:
    """Points each once, by their series and number (COR-058 point 3), what is no point id
    after them as written."""
    unique = list(dict.fromkeys(points))

    def key(point: str) -> tuple[int, str, int, str]:
        series = id_series(point)
        return (0, series[0], series[1], "") if series is not None else (1, "", 0, point)

    return tuple(sorted(unique, key=key))


def _record_order(record: Record) -> tuple[bool, int, str, int, str]:
    """The project's own first; then PRJ, ADR, each capability's DEC, COR; then by number."""
    capability, _colon, bare = record.id.rpartition(":")
    prefix, _dash, number = bare.partition("-")
    space = _SPACE_ORDER.index(prefix) if prefix in _SPACE_ORDER else len(_SPACE_ORDER)
    return (record.received, space, capability, int(number) if number.isdigit() else 0, record.id)


def _relative(target_root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(target_root.resolve()).as_posix()
    except ValueError:
        return None
