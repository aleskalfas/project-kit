"""Where each commit a planned record names sits: on the default branch or off it (DEC-001 point 6).

A planned revalidation record names where the design it reviewed stood, in
`reviewed-against`: one mapping per source. A source in this repository has no
`url`, and its `version` is a commit's full id, or `this change` when the
design lands in the change that adds the record. A commit the default branch
holds stays reachable after a squash merge, so whoever reads the record can
return to the design. A branch's commit does not. This module places each such
commit on the default branch:

- **one way of placing a commit** (`place`). A commit is held when the default
  branch's history, as this clone holds it, reaches it. It is not held when
  that history does not reach it and the clone holds the whole of it, a commit
  the clone lacks included, since a full clone holds every commit of the
  default branch. It is unknown when that history stops short in a shallow
  clone, since the commit may lie beyond the cut. The stamp places a planned
  record's commit the same way, to warn while the record is written;
- **where it looks**: the default branch alone, at the commit the backbone
  resolves it to (`pkit repository base --json`, its `default_branch`; COR-054
  point 5), never a run's base. It reads the clone's history, and asks no
  remote for anything;
- **which records the change adds**: each record whose file the merge-base
  does not hold, the merge-base of the run's base and HEAD — `--base`, else
  `$PKIT_CHECK_BASE`, else the default branch — as the same reading gives it
  (COR-054 point 3). The working tree is read, uncommitted changes included. The
  base says only which records are new;
- **what it finds**: a commit the default branch does not hold, in a record the
  change adds, is an error naming the record and the source. The change that
  adds a record is the one place its pointer can still be fixed. In a record
  the merge-base holds, it is reported and never fails: a record is history and
  is never rewritten, and a history rewrite on the default branch, such as
  removing a secret, takes every older pointer off it. A commit it cannot place
  is reported as unknown and never fails, since the pointers are provenance,
  not a gate;
- **nothing to place**: a working tree with no planned record, or whose planned
  records name no commit of this repository, reads neither the base nor the
  default branch, and says so;
- **no default branch resolved**: it fails, with the backbone's reason and fix
  (COR-054 point 4), and so does a base it cannot compare with.

It reads history beyond the working tree, so it is not a validator (COR-055
point 2), and DEC-001 point 6 keeps it out of validation, since the pointers
are provenance (COR-055 point 1): `pkit analysis check-pointers` runs it, a
line of its own in a project's check gate. A source's form — its keys, a
commit's full id, `this change` — is the record's schema's, which validation
applies. A mapping not of that form is not placed here.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import backbone, markdown, schemas
from _lib.findings import ERROR, REPORT, Finding, Outcome, at
from _lib.model import Unreadable

#: The version of the `--json` document.
SCHEMA_VERSION = 1

#: Where a commit sits on the default branch (DEC-001 point 6).
HELD, NOT_HELD, UNKNOWN = "held", "not-held", "unknown"

#: The trigger of a record that names what it reviewed, and the field it names it in.
PLANNED = "planned"
FIELD = "reviewed-against"


class CannotCheck(Exception):
    """The pointers cannot be placed; the message says why and what to do."""


def place(root: Path, commit: str, tip: str) -> str:
    """Where `commit` sits on the default branch, whose commit is `tip`, as the clone at
    `root` holds its history: `HELD`, `NOT_HELD` or `UNKNOWN` (DEC-001 point 6). It
    asks no remote. Raises `backbone.GitFailed` when git cannot answer."""
    if backbone.holds_commit(root, commit) and backbone.reaches(root, commit, tip):
        return HELD
    return UNKNOWN if backbone.history_cut(root, tip) else NOT_HELD


@dataclass(frozen=True)
class Source:
    """A source of a planned record that names a commit of this repository: the
    record's file, the source's place in `reviewed-against`, its title and the commit."""

    record: str
    index: int
    title: str
    commit: str

    @property
    def location(self) -> str:
        return at(self.record, f"/{FIELD}/{self.index}/version")


@dataclass(frozen=True)
class Placed:
    """A source placed: whether the change adds its record, and where its commit sits."""

    source: Source
    added: bool
    placement: str

    def as_json(self) -> dict[str, Any]:
        return {
            "record": self.source.record,
            "source": self.source.index,
            "title": self.source.title,
            "commit": self.source.commit,
            "added": self.added,
            "placement": self.placement,
        }


@dataclass(frozen=True)
class Checked:
    """The answer: the default branch and the base read, when anything was placed, each
    source placed, and the outcome."""

    branch: backbone.Branch | None
    base: backbone.Base | None
    placed: tuple[Placed, ...]
    outcome: Outcome

    def document(self) -> dict[str, Any]:
        branch, base = self.branch, self.base
        return {
            "schema_version": SCHEMA_VERSION,
            "default_branch": None
            if branch is None
            else {"name": branch.name, "ref": branch.ref, "commit": branch.commit},
            "base": None
            if base is None
            else {"ref": base.ref, "tip": base.tip, "commit": base.fork},
            **self.outcome.document(),
            "pointers": [placed.as_json() for placed in self.placed],
        }


def check(root: Path, ref: str | None = None) -> Checked:
    """Place each commit the planned records in the working tree at `root` name on the
    default branch, the records the change adds read against the base `ref` — without
    one, the base the backbone names: `$PKIT_CHECK_BASE`, else the default branch
    (COR-054). Raises CannotCheck when it cannot answer."""
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        raise CannotCheck(f"the analysis could not be read: {exc}") from exc
    read = _read(root, analysis.records)
    if not read.sources:
        line = (
            f"pointers: {_count(len(read.planned), 'planned record')} here, naming no commit of "
            f"this repository; nothing to place, no base read."
            if read.planned
            else "pointers: no planned revalidation record here; nothing to place, no base read."
        )
        return Checked(None, None, (), Outcome([line, *_skipped(read)], list(read.unread)))

    try:
        reading = backbone.settled(root, ref)
    except Unreadable as exc:
        raise CannotCheck(f"the default branch could not be read: {exc}") from exc
    branch, tip = _branch(reading.default_branch)
    base, fork = _base(reading.base)
    held_before: dict[str, bool] = {}
    placed: list[Placed] = []
    for source in read.sources:
        if source.record not in held_before:
            held_before[source.record] = backbone.blob_of(root, fork, source.record) is not None
        try:
            placement = place(root, source.commit, tip)
        except backbone.GitFailed as exc:
            raise CannotCheck(
                f"{source.commit}, named at {source.location}, could not be placed on "
                f"{branch.ref}: {exc}"
            ) from exc
        placed.append(Placed(source, not held_before[source.record], placement))

    findings = [*read.unread]
    for one in placed:
        found = _finding(root, one, branch, base)
        if found is not None:
            findings.append(found)
    summary = [*_summary(placed, branch, base), *_skipped(read)]
    return Checked(branch, base, tuple(placed), Outcome(summary, findings))


# --- the planned records ---------------------------------------------------------------------


@dataclass(frozen=True)
class _Read:
    """The planned records, the sources naming a commit of this repository, how many
    sources name `this change` and how many lie outside, and the records not read."""

    planned: tuple[str, ...]
    sources: tuple[Source, ...]
    this_change: int
    outside: int
    unread: tuple[Finding, ...]


def _read(root: Path, records: Iterable[str]) -> _Read:
    """Each source of a planned record among `records`, repository-relative, that names a
    commit of this repository, read from the working tree."""
    planned: list[str] = []
    sources: list[Source] = []
    unread: list[Finding] = []
    this_change = outside = 0
    commit = schemas.commit_pattern()
    for rel in records:
        try:
            front, _body = markdown.split((root / rel).read_text(encoding="utf-8"))
            data = markdown.load(front) if front is not None else None
        except (OSError, UnicodeDecodeError, YAMLError):
            data = None
        if not isinstance(data, Mapping):
            unread.append(
                Finding(
                    REPORT,
                    rel,
                    "its front matter cannot be read, so no pointer it names is placed: "
                    "`pkit analysis validate` says why",
                )
            )
            continue
        if data.get("trigger") != PLANNED:
            continue
        planned.append(rel)
        given = data.get(FIELD)
        for index, source in enumerate(given if isinstance(given, list) else []):
            if not isinstance(source, Mapping):
                continue
            version = source.get("version")
            if "url" in source:
                outside += 1
            elif version == schemas.this_change():
                this_change += 1
            elif isinstance(version, str) and commit.match(version):
                title = source.get("title")
                sources.append(Source(rel, index, title if isinstance(title, str) else "", version))
    return _Read(tuple(planned), tuple(sources), this_change, outside, tuple(unread))


# --- what is settled -------------------------------------------------------------------------


def _branch(branch: backbone.Branch) -> tuple[backbone.Branch, str]:
    """The default branch the backbone resolved, and its commit — or CannotCheck saying
    why there is none, with the backbone's fix (COR-054 point 4)."""
    if branch.commit is not None:
        return branch, branch.commit
    if branch.unborn:
        raise CannotCheck(
            f"the default branch {branch.name!r} has no commit yet: no commit can be placed on "
            f"it before its first (COR-054 point 4)"
        )
    raise CannotCheck(
        branch.problem or f"the default branch {branch.name!r} resolves to no commit here."
    )


def _base(base: backbone.Base) -> tuple[backbone.Base, str]:
    """The base the backbone named, and where HEAD left it — or CannotCheck saying why
    not: the refusals of the friction change check, in its words, since the backbone
    resolves the base once for both (COR-054 point 5)."""
    if base.problem is not None or base.tip is None or base.fork is None:
        raise CannotCheck(base.problem or f"the base {base.ref!r} cannot be compared.")
    return base, base.fork


# --- what is said ----------------------------------------------------------------------------


def _finding(
    root: Path, placed: Placed, branch: backbone.Branch, base: backbone.Base
) -> Finding | None:
    """What a source placed says: nothing when the default branch holds its commit; an
    error when it does not and the change adds the record; else a report."""
    source = placed.source
    named = f'"{source.title}" names {source.commit[: backbone.SHORT]}'
    if placed.placement == HELD:
        return None
    if placed.placement == UNKNOWN:
        return Finding(
            REPORT,
            source.location,
            f"{named}, which cannot be placed: this clone is shallow, and its history of "
            f"{branch.ref} stops short, so the commit may lie beyond it. Unknown, never a "
            f"failure, since the pointers are provenance (DEC-001 point 6); `git fetch "
            f"--unshallow` reads the whole history",
        )
    lacking = (
        ""
        if backbone.holds_commit(root, source.commit)
        else ", and this clone, which holds all of that branch's history, holds no such commit"
    )
    off = f"{named}, which the default branch, {branch.ref}, does not hold{lacking}"
    if placed.added:
        return Finding(
            ERROR,
            source.location,
            f"{off}: a squash merge leaves a branch's commits off it, so the record could not "
            f"lead back to the design. Name the commit where the design landed on {branch.name}, "
            f"or `{schemas.this_change()}` when the design lands with this record (DEC-001 "
            f"point 6)",
        )
    fork = (base.fork or "")[: backbone.SHORT]
    return Finding(
        REPORT,
        source.location,
        f"{off}. This change does not add the record: {base.ref} held it where this branch "
        f"left it, at {fork}. A record is never rewritten, so this is reported, never failed "
        f"(DEC-001 point 6)",
    )


def _summary(placed: list[Placed], branch: backbone.Branch, base: backbone.Base) -> list[str]:
    """How many commits were placed, and where each sits; how many of their records the
    change adds, and against which base."""
    tip = (branch.commit or "")[: backbone.SHORT]
    fork = (base.fork or "")[: backbone.SHORT]
    states = [p.placement for p in placed]
    records = {p.source.record for p in placed}
    added = {p.source.record for p in placed if p.added}
    named = f"{_count(len(placed), 'commit')} named by {_count(len(records), 'planned record')}"
    return [
        f"pointers: {named}, placed on {branch.ref} ({tip}): {states.count(HELD)} held, "
        f"{states.count(NOT_HELD)} not held, {states.count(UNKNOWN)} unknown.",
        f"pointers: this change adds {len(added)} of those records, read against {base.ref}, which "
        f"this branch left at {fork}.",
    ]


def _skipped(read: _Read) -> list[str]:
    """A line for the sources not placed: those naming the change itself, and those
    outside this repository."""
    parts = []
    if read.this_change:
        parts.append(f"{_count(read.this_change, 'source')} naming `{schemas.this_change()}`")
    if read.outside:
        parts.append(f"{_count(read.outside, 'source')} outside this repository")
    return [f"pointers: not placed: {' and '.join(parts)}."] if parts else []


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" + ("" if number == 1 else "s")
