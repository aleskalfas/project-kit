"""A change's numbering, checked against its base (COR-058 point 8).

`pkit decisions check-diff` runs it. Validation answers about the project's
state and takes no base (COR-055 point 2), so a check that compares a change
with its base is a command of its own, and a line of its own in a project's
check gate, beside `pkit migrations check-diff`.

**What it compares.** The base comes from the backbone's one resolution
(`default_branch`, COR-054): `--base`, else `$PKIT_CHECK_BASE`, else the
default branch. Two states of it are read:

- **the branch point** (the base's `fork`), where this branch left the base.
  The change's own edits run from there to the working tree, so a branch that
  fell behind is not failed for what the default branch gained meanwhile.
- **the base's tip,** read only for the ids another change took since the
  branch point, and only when the tip moved on.

The head is the working tree's one listing (`working_tree`), and a commit is
read from git's objects (`friction_git.CommitTree`). Which file is a record,
and of which id-space, is `decisions_validate.record_space`'s answer. A record
the project receives by sync is skipped, since it is refined where it is
authored (`is_synced_copy` of the tree's `.pkit/lifecycle/ownership.py`).

**Which records.** A head record is paired with the branch point's record at
its path, else with the one record there of its id-space and id, so a record
renamed by the change keeps its pair. A record the change adds has no pair.
Each record whose text differs from its pair's, and each record the change
adds, is compared. A record the change removes is not.

**How a record is read.** Through `record_points.read_points`, the one reading
of a record's points, and each stub is held to its entry by
`record_points.hold_stubs` (ADR-057 point 2). The check reads point headings
only, except in a record the change converts: one in list form at the branch
point, with point headings at the head (COR-058 point 2). There it pairs each
head point with the list point it came from, by title, then by id, then in
order. Any other record in list form meets only the warning below.

**It fails on**, for each record compared:

- an id the branch point holds or retires that the head neither holds nor
  retires: a point dropped without being retired
- a new id that is not past every id of its series that the branch point holds
  or retires
- a point whose text, read without its id (`RecordPoints.point_text`), sits at
  the head only under another id: a renumbering, or a retirement whose
  successor kept the claim
- a duplicate id, or a heading in a refused form, that the change added
- a retired id without its stub, or a stub without its entry, at the head
- a new entry in `retired-points` whose successor is not a live point at the head
- in a record the change converts, a point whose id differs from the number
  its numbered item showed at the branch point
- a point id another change took on the default branch since the branch point,
  in the same record, that the change takes too. A point the tip holds under
  that id with the head's very text is this change's own work landed, as a
  stacked branch's parent is, and is no clash.
- a record id another change took on the default branch since the branch
  point, for a record the change adds at another path

**It warns of:**

- a point's title at the branch point found at the head under another id, with
  its text changed: likely a renumbering with an edit, which the check cannot
  be sure of
- in a record the change converts, a point whose id differs from the bold
  number or bold label that opened it at the branch point
- a point added to a record in list form, or a new record in list form

Each finding names the record and the id: `<file>#<id>`, or `<file>` for a
record id. The findings on a record's points are errors, and the rest
warnings (COR-058 point 8). A point id another change took is not followed to
what anchors it: no anchor names one point yet (COR-058 point 10).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Protocol

import click

from project_kit import (
    cli_render,
    decisions_validate,
    document_parts,
    lifecycle_ownership,
    record_points,
    working_tree,
)
from project_kit.friction_git import SHORT, CommitTree
from project_kit.record_points import ListForm, ListPoint, PointHeading, RecordPoints
from project_kit.validators import Finding, Severity


class _Tree(Protocol):
    """A state of the repository: the working tree, or one commit."""

    def files(self) -> Sequence[str]: ...

    def read_bytes(self, paths: Sequence[str]) -> Mapping[str, bytes | None]: ...


@dataclass(frozen=True)
class Record:
    """One decision record at one state: where it is, its id-space, its id and its text."""

    rel: str
    space: str
    record_id: str | None
    text: str

    @cached_property
    def points(self) -> RecordPoints:
        """Its points, read once (`record_points.read_points`)."""
        return record_points.read_points(self.text)

    @property
    def name(self) -> str:
        """Its id, or its path when its front matter gives none."""
        return self.record_id or self.rel

    def line(self, start: int) -> int:
        """The line of the file a place in its body sits on, counted from 1."""
        body = self.points.body.text
        return document_parts.body_first_line(self.text, body) + body.count("\n", 0, start)


@dataclass(frozen=True)
class Report:
    """What the check found: the base compared with, the records compared, and the findings,
    errors first."""

    base: str
    fork: str
    tip: str
    compared: int
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> int:
        return sum(1 for finding in self.findings if finding.severity.fails)


def head_records(target_root: Path) -> dict[str, Record]:
    """The records the working tree holds, a record the project receives by sync left out."""
    ownership = lifecycle_ownership.load_ownership(target_root)
    records = _read(
        working_tree.working_tree(target_root), decisions_validate.adr_folder(target_root)
    )
    return {
        rel: record
        for rel, record in records.items()
        if ownership is None or not ownership.is_synced_copy(target_root, rel)
    }


def check(
    target_root: Path, head: Mapping[str, Record], *, base: str, fork: str, tip: str
) -> Report:
    """Compare the records `head` holds with the branch point `fork`, and the ids they take
    with the base's tip `tip` (COR-058 point 8). `base` is the base as named, for the report."""
    adr = decisions_validate.adr_folder(target_root)
    at_fork = _read(CommitTree(target_root, fork), adr)
    at_tip = _read(CommitTree(target_root, tip), adr) if tip != fork else at_fork
    pairs = _pair(head, at_fork)
    compared = [
        record
        for rel, record in sorted(head.items())
        if rel not in pairs or pairs[rel].text != record.text
    ]
    found: list[Finding] = []
    for record in compared:
        before = pairs.get(record.rel)
        own = _points(record, before)
        if tip != fork:
            own += _taken_points(record, before, _tip_pair(record, before, at_tip), base)
            if before is None:
                own += _taken_record(record, at_fork, at_tip, head, base)
        found += sorted(own, key=_by_id)  # stable: one id's findings keep their order
    errors = [finding for finding in found if finding.severity.fails]
    warnings = [finding for finding in found if not finding.severity.fails]
    return Report(base, fork, tip, len(compared), (*errors, *warnings))


# --- reading and pairing -----------------------------------------------------------


def _read(tree: _Tree, adr: str | None) -> dict[str, Record]:
    """Every record `tree` holds, by path. A file that is not UTF-8 is left out, as
    validation's id pass reports it."""
    spaces: dict[str, str] = {}
    for rel in tree.files():
        space = decisions_validate.record_space(rel, adr)
        if space is not None:
            spaces[rel] = space
    records: dict[str, Record] = {}
    for rel, raw in tree.read_bytes(sorted(spaces)).items():
        if raw is None:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        records[rel] = Record(rel, spaces[rel], decisions_validate.record_id_of(text), text)
    return records


def _pair(head: Mapping[str, Record], other: Mapping[str, Record]) -> dict[str, Record]:
    """For each head record, its record in `other`: at its path, else the one record of
    `other` with its id-space and id that no head record holds at its own path."""
    pairs = {rel: other[rel] for rel in head if rel in other}
    left: dict[tuple[str, str], list[Record]] = {}
    for rel, record in other.items():
        if rel not in head and record.record_id is not None:
            left.setdefault((record.space, record.record_id), []).append(record)
    for rel, record in head.items():
        if rel in pairs or record.record_id is None:
            continue
        found = left.get((record.space, record.record_id), [])
        if len(found) == 1:
            pairs[rel] = found.pop()
    return pairs


def _tip_pair(record: Record, before: Record | None, at_tip: Mapping[str, Record]) -> Record | None:
    """The tip's state of a record: at the head's path; for a record the branch point
    holds, at the branch point's path, else the one tip record of its id-space and id.
    A record the change adds is looked for at its own path only, so another change's
    record of the same id is no state of it."""
    if record.rel in at_tip:
        return at_tip[record.rel]
    if before is None:
        return None
    if before.rel in at_tip:
        return at_tip[before.rel]
    found = [
        other
        for other in at_tip.values()
        if other.record_id is not None
        and (other.space, other.record_id) == (before.space, before.record_id)
    ]
    return found[0] if len(found) == 1 else None


def _headed(points: RecordPoints) -> bool:
    """Whether a record's points are headings (COR-058 point 1)."""
    return points.level is not None


def _held(points: RecordPoints) -> set[str]:
    """The ids a record holds or retires: its point headings' and stubs', its retired
    ids, and in list form its list points'."""
    if _headed(points):
        listed = {p.id for p in (*points.points, *points.stubs)}
    else:
        listed = {p.id for p in points.list_points}
    return listed | set(points.retired)


# --- the change's own edits ----------------------------------------------------------


def _points(record: Record, before: Record | None) -> list[Finding]:
    """A record's points at the head against the branch point."""
    head = record.points
    base = before.points if before is not None else None
    if not _headed(head):
        if base is not None and _headed(base):
            return [*_dropped(record, base, set(head.retired))]
        return [*_list_form(record, base)]
    if base is not None and not _headed(base) and base.list_points:
        return _converted(record, base)
    found: list[Finding] = []
    if base is not None:
        held = {p.id for p in (*head.points, *head.stubs)} | set(head.retired)
        found += _dropped(record, base, held)
        found += _not_past(record, _held(base), held - _held(base))
        found += _moved(record, base)
    found += _added_duplicates(record, base)
    found += _added_refused(record, base)
    found += _stubs(record)
    found += _new_successors(record, base)
    return found


def _dropped(record: Record, base: RecordPoints, held: set[str]) -> Iterator[Finding]:
    """An id the branch point holds or retires that the head neither holds nor retires."""
    for point_id in _sorted(_held(base) - held):
        how = "retires" if point_id in base.retired else "holds"
        yield Finding(
            f"{record.rel}#{point_id}",
            f"{record.name}: the branch point {how} `{point_id}`, and the head neither holds nor "
            f"retires it. A dropped point keeps its id in `retired-points`, with the points that "
            f"took its text, and a stub where it was ({_cite(4)}).",
        )


def _not_past(record: Record, base_ids: set[str], new_ids: Iterable[str]) -> Iterator[Finding]:
    """A new id that is not past every id of its series the branch point holds or retires."""
    for point_id in _sorted(new_ids):
        series = record_points.id_series(point_id)
        if series is None:
            continue
        highest = max(
            (
                s[1]
                for held in base_ids
                if (s := record_points.id_series(held)) and s[0] == series[0]
            ),
            default=0,
        )
        if series[1] > highest:
            continue
        unused = decisions_validate.next_unused(base_ids, point_id)
        yield Finding(
            f"{record.rel}#{point_id}",
            f"{record.name}: the new id `{point_id}` is not past every id of its series the "
            f"branch point holds or retires. A new point takes the next unused number, "
            f"`{unused}`, and no id is reused ({_cite(3)}).",
        )


def _moved(record: Record, base: RecordPoints) -> Iterator[Finding]:
    """A base point whose text sits at the head only under another id, as an error, and
    a base point whose title sits there under another id with its text changed, as a
    warning. A text two base points share is left out, since it names neither."""
    head = record.points
    texts = Counter(base.point_text(point) for point in base.points)
    under: dict[str, list[str]] = {}
    for point in head.points:
        under.setdefault(head.point_text(point), []).append(point.id)
    for point in base.points:
        text = base.point_text(point)
        if texts[text] > 1:
            continue
        ids = under.get(text, [])
        if point.id in ids:
            continue
        if ids:
            yield Finding(
                f"{record.rel}#{point.id}",
                f"{record.name}: the text of point `{point.id}` at the branch point sits at the "
                f"head only under {_listed(ids)}. That is a renumbering, or a retirement whose "
                f"successor kept the claim. A point keeps its id wherever it sits "
                f"({_cite(3)}).",
            )
            continue
        same_id = head.point(point.id)
        if same_id is not None and same_id.title == point.title:
            continue
        titled = [
            other.id
            for other in head.points
            if other.title == point.title
            and other.id != point.id
            and not _titled(base, other.id, point.title)
        ]
        if titled:
            yield Finding(
                f"{record.rel}#{point.id}",
                f"{record.name}: the title of point `{point.id}` at the branch point, "
                f'"{point.title}", sits at the head under {_listed(titled)}, with its text '
                f"changed. That is likely a renumbering with an edit. A point keeps its id "
                f"wherever it sits ({_cite(3)}).",
                severity=Severity.WARNING,
            )


def _titled(points: RecordPoints, point_id: str, title: str) -> bool:
    """Whether the point `point_id` has `title` in `points`."""
    found = points.point(point_id)
    return found is not None and found.title == title


def _added_duplicates(record: Record, base: RecordPoints | None) -> Iterator[Finding]:
    """An id more headings take at the head than at the branch point, where it is two or more."""
    head = record.points
    before = (
        Counter(p.id for p in (*base.points, *base.stubs)) if base is not None else Counter[str]()
    )
    lines: dict[str, list[int]] = {}
    for heading in (*head.points, *head.stubs):
        lines.setdefault(heading.id, []).append(record.line(heading.extent.start))
    for point_id, at in lines.items():
        if len(at) > 1 and len(at) > before[point_id]:
            yield Finding(
                f"{record.rel}#{point_id}",
                f"{record.name}: the change adds a duplicate id. {len(at)} headings take "
                f"`{point_id}`, at lines {_and(str(line) for line in sorted(at))}. A record's ids "
                f"are unique across all its groups ({_cite(1)}).",
            )


def _added_refused(record: Record, base: RecordPoints | None) -> Iterator[Finding]:
    """A heading in a form a point's heading refuses that the head holds more of than the
    branch point."""
    head = record.points
    before = Counter(h.title for h in base.misspelt) if base is not None else Counter[str]()
    for heading in head.misspelt:
        if before[heading.title] > 0:
            before[heading.title] -= 1
            continue
        token = decisions_validate.opening_token(heading.title)
        yield Finding(
            f"{record.rel}#{token}",
            f"{record.name}: the change adds the heading `{'#' * heading.level} "
            f"{heading.title}` at line {record.line(heading.start)}, which opens with `{token}` "
            f"in a form a point's heading refuses. A point's heading is `5. Title` or "
            f"`D1 — Title` ({_cite(1)}).",
        )


def _stubs(record: Record) -> Iterator[Finding]:
    """A retired id without its stub, or a stub without its entry, at the head, as
    `record_points.hold_stubs` finds them. A stub's sentence is validation's to judge."""
    head = record.points
    kind = record_points.StubMismatchKind
    for mismatch in record_points.hold_stubs(head):
        if mismatch.kind is kind.NO_STUB:
            level = head.level or 3
            heading = f"{'#' * level} {decisions_validate.stub_heading(mismatch.id)}"
            message = (
                f"retired point `{mismatch.id}` has no stub at the head. Where the point was, "
                f"write the heading `{heading}` and the sentence "
                f'"{record_points.stub_sentence(head.retired.get(mismatch.id, ()))}"'
            )
        elif mismatch.kind is kind.NOT_RETIRED and mismatch.stub is not None:
            message = (
                f"the stub of `{mismatch.id}` at line {record.line(mismatch.stub.extent.start)} "
                f"has no entry in `retired-points` at the head. Add the entry, with the points "
                f"that took its text"
            )
        else:
            continue
        yield Finding(
            f"{record.rel}#{mismatch.id}",
            f"{record.name}: {message} ({_cite(4)}).",
        )


def _new_successors(record: Record, base: RecordPoints | None) -> Iterator[Finding]:
    """A new entry in `retired-points` whose successor is not a live point at the head."""
    head = record.points
    live = {point.id for point in head.points}
    for retired_id, successors in head.retired.items():
        if base is not None and retired_id in base.retired:
            continue
        for successor in successors:
            if successor in live:
                continue
            yield Finding(
                f"{record.rel}#{retired_id}",
                f"{record.name}: the new entry `{retired_id}` in `retired-points` names "
                f"`{successor}`, which is no live point at the head. A successor is a live point "
                f"when its entry is written ({_cite(5)}).",
            )


def _list_form(record: Record, base: RecordPoints | None) -> Iterator[Finding]:
    """A point added to a record in list form, or a new record in list form, as a warning."""
    listed = len(record.points.list_points)
    if not listed:
        return
    keep = (
        "The decisions README's refining rule lets the list keep working, its later numbers "
        "moving. Or convert the record to point headings by hand first, so every number "
        f"stays for good ({_cite(9)})."
    )
    if base is None:
        yield Finding(
            record.rel,
            f"{record.name} is a new record in list form: its {listed} points are a numbered "
            f"list, or paragraphs that open with a bold number or label. {keep}",
            severity=Severity.WARNING,
        )
    elif listed > len(base.list_points):
        yield Finding(
            record.rel,
            f"{record.name} is in list form, and the change adds a point: {listed} points at "
            f"the head against {len(base.list_points)} at the branch point. {keep}",
            severity=Severity.WARNING,
        )


# --- a record the change converts ----------------------------------------------------


def _converted(record: Record, base: RecordPoints) -> list[Finding]:
    """A record in list form at the branch point whose points are headings at the head.

    Each head point is paired with the list point it came from, and its id is held to the
    number or label a reader saw there. A list point paired with none, and not retired,
    is dropped. A head point paired with none is new, and must be past every id of the
    list.
    """
    head = record.points
    pairs, unpaired_list, unpaired_head = _conversion_pairs(base.list_points, head.points)
    found: list[Finding] = []
    for listed, point in pairs:
        if listed.id == point.id:
            continue
        if listed.form is ListForm.ITEM:
            found.append(
                Finding(
                    f"{record.rel}#{point.id}",
                    f"{record.name}: point `{point.id}` comes from the numbered item that showed "
                    f"`{listed.id}` at the branch point. Converting takes the number a reader "
                    f"sees as the id, so it is `{listed.id}` ({_cite(9)}).",
                )
            )
        else:
            found.append(
                Finding(
                    f"{record.rel}#{point.id}",
                    f"{record.name}: point `{point.id}` comes from the paragraph that opened with "
                    f"the bold `{listed.id}` at the branch point. Converting takes the number or "
                    f"label a reader sees as the id ({_cite(9)}).",
                    severity=Severity.WARNING,
                )
            )
    held = {p.id for p in (*head.points, *head.stubs)} | set(head.retired)
    dropped = {listed.id for listed in unpaired_list} - held
    for point_id in _sorted(dropped):
        found.append(
            Finding(
                f"{record.rel}#{point_id}",
                f"{record.name}: the branch point's list holds `{point_id}`, and the converted "
                f"record neither holds nor retires it. Converting keeps every point's words "
                f"under the number a reader saw ({_cite(9)}).",
            )
        )
    base_ids = {listed.id for listed in base.list_points} | set(base.retired)
    new_ids = {point.id for point in unpaired_head} | (set(head.retired) - base_ids)
    found += _not_past(record, base_ids, new_ids - base_ids)
    found += _added_duplicates(record, base)
    found += _added_refused(record, base)
    found += _stubs(record)
    found += _new_successors(record, base)
    return found


def _conversion_pairs(
    listed: Sequence[ListPoint], headed: Sequence[PointHeading]
) -> tuple[list[tuple[ListPoint, PointHeading]], list[ListPoint], list[PointHeading]]:
    """Each head point with the list point it came from: by title, where one list point
    and one head point have it (a bold lead becomes the title, COR-058 point 9); then by
    id; then the rest in order. Also the list points and head points left unpaired."""
    left_list, left_head = list(listed), list(headed)
    pairs: list[tuple[ListPoint, PointHeading]] = []
    list_titles = Counter(item.title for item in left_list if item.title)
    head_titles = Counter(point.title for point in left_head)
    for item in list(left_list):
        if item.title and list_titles[item.title] == 1 and head_titles[item.title] == 1:
            point = next(point for point in left_head if point.title == item.title)
            pairs.append((item, point))
            left_list.remove(item)
            left_head.remove(point)
    for item in list(left_list):
        point = next((point for point in left_head if point.id == item.id), None)
        if point is not None:
            pairs.append((item, point))
            left_list.remove(item)
            left_head.remove(point)
    paired = min(len(left_list), len(left_head))
    pairs += zip(left_list[:paired], left_head[:paired], strict=True)
    pairs.sort(key=lambda pair: pair[1].extent.start)
    return pairs, left_list[paired:], left_head[paired:]


# --- what the default branch took meanwhile --------------------------------------------


def _taken_points(
    record: Record, before: Record | None, tip: Record | None, base: str
) -> Iterator[Finding]:
    """A point id another change took on the default branch since the branch point, in
    this record, that the change takes too. A record in list form at the head meets only
    the warning on list form, so it is not read here."""
    head = record.points
    if tip is None or not _headed(head):
        return
    forked = _held(before.points) if before is not None else set[str]()
    taken = _held(tip.points) - forked
    added = _held(head) - forked
    for point_id in _sorted(taken & added):
        ours, theirs = head.point(point_id), tip.points.point(point_id)
        if (
            ours is not None
            and theirs is not None
            and head.point_text(ours) == tip.points.point_text(theirs)
        ):
            continue  # this change's own work, landed
        unused = decisions_validate.next_unused(_held(tip.points) | _held(head), point_id)
        yield Finding(
            f"{record.rel}#{point_id}",
            f"{record.name}: another change took `{point_id}` on {base} since this branch left "
            f"it, and this change takes it too. The first to land keeps the number, so move "
            f"this change's point to the next unused, `{unused}`, and its citations with it "
            f"({_cite()}).",
        )


def _taken_record(
    record: Record,
    at_fork: Mapping[str, Record],
    at_tip: Mapping[str, Record],
    head: Mapping[str, Record],
    base: str,
) -> Iterator[Finding]:
    """A record id another change took on the default branch since the branch point, for a
    record this change adds. A tip record of the id at this record's own path is this
    change's own work, landed."""
    if record.record_id is None:
        return
    key = (record.space, record.record_id)
    if any((other.space, other.record_id) == key for other in at_fork.values()):
        return  # the branch point holds the id already: validation's duplicate, not a clash
    others = sorted(
        other.rel
        for other in at_tip.values()
        if (other.space, other.record_id) == key and other.rel != record.rel
    )
    if not others:
        return
    yield Finding(
        record.rel,
        f"{record.name}: another change took the record id `{record.record_id}` on {base} "
        f"since this branch left it, at {_listed(others)}. The first to land keeps the "
        f"number, so renumber this record to `{_next_record_id(record, at_tip, head)}` "
        f"({_cite()}).",
    )


def _next_record_id(record: Record, *states: Mapping[str, Record]) -> str:
    """One past the highest record number of `record`'s id-space in `states`, written
    with as many digits as its own id."""
    assert record.record_id is not None
    prefix, _dash, digits = record.record_id.partition("-")
    numbers = [
        int(other.record_id.partition("-")[2])
        for state in states
        for other in state.values()
        if other.space == record.space
        and other.record_id is not None
        and other.record_id.partition("-")[2].isdigit()
    ]
    return f"{prefix}-{max(numbers, default=0) + 1:0{len(digits)}d}"


# --- the report ------------------------------------------------------------------------


def print_report(report: Report) -> None:
    """The records compared and the base, then each finding, errors first."""
    where = f"{report.base} ({report.tip[:SHORT]}; this branch left it at {report.fork[:SHORT]})"
    if report.tip == report.fork:
        where = f"{report.base} (this branch left it at {report.fork[:SHORT]})"
    if not report.compared:
        click.echo(f"  No decision record differs from {where}; nothing to check.")
        return
    errors = report.errors
    click.echo(
        "  "
        + cli_render.style(
            "strong",
            f"Compared {report.compared} decision record(s) with {where}: {errors} error(s) and "
            f"{len(report.findings) - errors} warning(s) in their numbering ({_cite()}).",
        )
    )
    for finding in report.findings:
        click.echo(f"    {finding.severity.value:<9}{finding.location}")
        click.echo(f"      → {finding.message}")


# --- helpers ---------------------------------------------------------------------------


def _sorted(ids: Iterable[str]) -> list[str]:
    """Ids by series, then number; what is no point id last, as written."""
    return sorted(ids, key=_id_key)


def _id_key(point_id: str) -> tuple[int, str, int, str]:
    series = record_points.id_series(point_id)
    return (0, series[0], series[1], "") if series else (1, "", 0, point_id)


def _by_id(finding: Finding) -> tuple[int, str, int, str]:
    """A record's finding by the id it names: the record's own finding first."""
    _rel, hash_sign, point_id = finding.location.partition("#")
    return _id_key(point_id) if hash_sign else (-1, "", 0, "")


def _cite(*points: int) -> str:
    """The points of COR-058 a finding rests on, with point 8, the check's own."""
    cited = sorted({*points, 8})
    if len(cited) == 1:
        return "COR-058 point 8"
    return f"COR-058 points {_and(str(point) for point in cited)}"


def _listed(ids: Sequence[str]) -> str:
    """`` `a` ``, `` `a` and `b` ``, `` `a`, `b` and `c` ``."""
    return _and(f"`{point_id}`" for point_id in ids)


def _and(items: Iterable[str]) -> str:
    listed = list(items)
    return listed[0] if len(listed) == 1 else f"{', '.join(listed[:-1])} and {listed[-1]}"
