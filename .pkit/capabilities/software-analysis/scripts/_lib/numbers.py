"""software-analysis' comparison of numbers with the default branch (DEC-001 point 3).

When two lines of work number a new use case or journey the same, the first to
reach the default branch keeps the number, and the other renumbers before
merging. This is where the other finds out: a number the working tree holds
that the default branch took too since this branch left it — its tip holds
it, or its history since the fork gave it a file gone since, as the stamp
counts a number held — where the merge-base, where this branch left the
default branch, held no file with that id.

An artefact is known by its id, never by its path, and a number is read from a
file's name as well as its front matter, on both sides (`Analysis.numbers`):

- **an id moved** within the branch — into an area, say — or on the default
  branch is no collision: the merge-base held it, so neither side took it;
- **this branch's own work, landed** — a parent branch squash-merged or
  rebased onto the default branch while this one was stacked on it — is no
  collision when the default branch's file for the number is, byte for byte,
  a version this branch's history wrote, wherever this branch has moved the
  file since. So is anything two lines of work wrote to the very byte;
- **a file of the same name** as one this branch holds, or its history since
  the fork added, for that number, but other bytes, is a warning: possibly
  this branch's own work landed and edited since — a parent edited after the
  fork, then squash-merged; an edit on the default branch after the squash; a
  conflict resolved in a rebase — or two lines of work that stamped the same
  slug. Merging the default branch in and keeping one file settles the first;
  renumbering, the second. It never fails: which of the two it is, only the
  person knows;
- **a file of another name** is a collision, an error: another line of work
  took the number for its own artefact.

Once the default branch is merged in, a number both took is two files holding
one id, which the validator reports as a duplicate — and so is this branch's
own work landed when it moved the file since: git pairs no rename where the
merge-base holds neither file.

It reads a base, so it answers about a change rather than the tree, and is not
a validator (ADR-058 point 7): `pkit analysis check-numbers` runs it, a line of
its own in a project's check gate, as the friction change check is. A collision
is judged at the merge at hand, so the base is the comparison's (COR-054 point
3): `--base`, else `$PKIT_CHECK_BASE`, else the default branch. Like the change
check it cannot answer without its base — a base that names no commit, or
shares no history with HEAD, fails it with the backbone's reason and fix —
except when the working tree numbers nothing: there is nothing to compare, and
no base is read (point 4) — but for the default branch, when the project has a
numbering setting to check against its history. When the base moved on after
this branch left it — the only case in which it can have taken a number since
— that is reported, never failed, as the change check reports an outdated base.

An id the project's numbering setting frees is free again, and taken by
neither side: the rule is the stamp's, read from one home
(`_lib/numbering.py`), so the two never disagree. Each entry's freed ids are
listed — in the summary, and each file with both commits in `--json` — so a
reviewer sees what the declaration does. An entry naming what is no commit of
the default branch's history, or listing an id its commit does not free, is an
error here, read whenever the project has a setting — numbered here or not —
since this is the check gate's line for numbering; such an entry or id frees
nothing meanwhile. An id a named commit would free that no entry lists is
reported, and stays taken.

Which commits those are the backbone names: `pkit repository base --json`
carries the base, its tip and where this branch left it (COR-054 point 5), so
nothing here resolves a base or computes a merge-base. The base is read at its
tip and at the merge-base through the backbone's discovery at a commit (`pkit
friction artefacts --at`), and its history since the fork as the stamp reads a
history (`_lib/history.py`). Git answers — only for a number both sides took —
which versions of the use-case and journey files this branch's history wrote
since the merge-base, which the default branch's tip holds, and which files
this branch's history added (`backbone.blobs_written`, `backbone.blob_of`,
`backbone.added`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from _lib import backbone, history, numbering
from _lib.findings import ERROR, REPORT, WARNING, Finding, Outcome
from _lib.model import NOUN, NUMBERED, Analysis, Unreadable, kind_numbered

#: The version of the `--json` document.
SCHEMA_VERSION = 1


class CannotCompare(Exception):
    """The numbers cannot be compared; the message says why and what to do."""


@dataclass(frozen=True)
class Base:
    """What the working tree is compared with: the base as named, the commit it
    names, and the merge-base of that commit and HEAD."""

    ref: str
    tip: str
    commit: str

    @property
    def outdated(self) -> bool:
        """The tip is not an ancestor of HEAD: the base moved on after this branch left it."""
        return self.tip != self.commit

    def as_json(self) -> dict[str, Any]:
        return {"ref": self.ref, "tip": self.tip, "commit": self.commit, "outdated": self.outdated}


@dataclass(frozen=True)
class Comparison:
    """The answer: the base compared with, when one was needed, the files whose numbers
    the numbering setting frees, and the outcome."""

    base: Base | None
    outcome: Outcome
    freed: tuple[numbering.Freed, ...] = ()

    def document(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "base": None if self.base is None else self.base.as_json(),
            "freed": [freed.as_json() for freed in self.freed],
            **self.outcome.document(),
        }


@dataclass(frozen=True)
class Theirs:
    """The default branch's files for a number it took since this branch left it — the
    files its tip holds, else the one its history gave the number last — and whether
    its tip holds them."""

    paths: tuple[str, ...]
    held: bool


def compare(root: Path, ref: str | None = None) -> Comparison:
    """Compare the numbers in the working tree at `root` with the base `ref` — without
    one, the base the backbone names: `$PKIT_CHECK_BASE`, else the default branch
    (COR-054). Raises CannotCompare when it cannot answer."""
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        raise CannotCompare(f"the analysis could not be read: {exc}") from exc
    ours = analysis.numbers()
    written = numbering.read(root)
    nothing = "numbers: no use case or journey is numbered here; nothing to compare"
    if not ours and written.unset:
        return Comparison(None, Outcome([f"{nothing}, no base read."]))

    try:
        reading = backbone.settled(root, ref)
    except Unreadable as exc:
        raise CannotCompare(f"the base could not be read: {exc}") from exc
    setting = numbering.resolve(root, written, reading.default_branch)
    numbered = {analysis.places[k] for k in NUMBERED if k in analysis.places}
    freeing = numbering.freeing(root, setting, reading.default_branch.commit, numbered)
    said = _freeing(freeing)
    problems = [*setting.problems, *freeing.problems, *freeing.reports]
    if not ours:
        return Comparison(None, Outcome([f"{nothing}.", *said], problems), freeing.freed)
    base = _resolve(reading.base)
    if not base.outdated:
        line = (
            f"numbers: this branch contains {base.ref} ({base.tip[: backbone.SHORT]}); nothing to "
            f"collide with."
        )
        return Comparison(base, Outcome([line, *said], problems), freeing.freed)
    try:
        on_base = backbone.read_analysis(root, at=base.tip)
        before = backbone.read_analysis(root, at=base.commit).held()
    except Unreadable as exc:
        raise CannotCompare(f"{base.ref} could not be read: {exc}") from exc

    line = (
        f"numbers: compared with {base.ref} ({base.tip[: backbone.SHORT]}; this branch left it at "
        f"{base.commit[: backbone.SHORT]})."
    )
    outdated = Finding(REPORT, analysis.location or ".", f"outdated base: {_outdated(base)}")
    folders = {a.places[k] for a in (analysis, on_base) for k in NUMBERED if k in a.places}
    theirs = _taken(root, base, analysis, on_base, before, folders, set(ours), freeing.files)
    findings = _collisions(root, base, ours, theirs, folders) if theirs else []
    outcome = Outcome([line, *said], [outdated, *problems, *findings])
    return Comparison(base, outcome, freeing.freed)


def _freeing(freeing: numbering.Freeing) -> list[str]:
    """A summary line for each entry of the numbering setting that frees an id, listing
    the ids it frees."""
    return [
        f"numbering: {commit[: backbone.SHORT]} frees {numbering.joined(ids)}, as "
        f"{numbering.NAME} names (DEC-001 point 3)."
        for commit, ids in freeing.ids
        if ids
    ]


def _taken(
    root: Path,
    base: Base,
    analysis: Analysis,
    on_base: Analysis,
    before: set[str],
    folders: set[str],
    ours: set[str],
    freed: Mapping[tuple[str, str], str],
) -> dict[str, Theirs]:
    """Each number of `ours` the default branch took since this branch left it, with its
    file: one its tip holds, else one its history since the fork gave a file gone
    since, as the stamp counts it held (`_lib/history.py`) — never one the merge-base
    held, nor one the numbering setting frees: `freed` names the files it frees, as the
    history's judge reads them (`_lib/numbering.py`)."""
    at_tip = {i: paths for i, paths in on_base.numbers().items() if i in ours and i not in before}
    theirs = {i: Theirs(tuple(sorted(paths)), held=True) for i, paths in at_tip.items()}
    gone = ours - before - set(at_tip)
    if gone:
        since = history.given(root, f"{base.commit}..{base.tip}", folders)
        judge = history.Judge(root, (analysis, on_base), freed)
        for i, number in history.counted(judge, since, gone).items():
            theirs[i] = Theirs((number.path,), held=False)
    return theirs


def _collisions(
    root: Path, base: Base, ours: dict[str, set[str]], theirs: dict[str, Theirs], folders: set[str]
) -> list[Finding]:
    """Each number both sides took, found against the file the default branch holds or
    gave for it: none for this branch's own work landed byte for byte, a warning for a
    file of a name this branch has for the number, an error for another."""
    written = backbone.blobs_written(root, base.commit, folders)
    names = {i: {_name(p) for p in ours[i]} for i in theirs}
    for number in history.given(root, f"{base.commit}..HEAD", folders):
        if number.id in names:
            names[number.id].add(_name(number.path))
    found: list[Finding] = []
    for i, their in sorted(theirs.items()):
        other = [
            p
            for p in their.paths
            if not their.held or backbone.blob_of(root, base.tip, p) not in written
        ]
        if not other:
            continue  # this branch's own work, landed byte for byte
        path = other[0]
        severity, message = _message(i, path, their.held, _name(path) in names[i], base.ref)
        found += [Finding(severity, here, message) for here in sorted(ours[i])]
    return found


def _message(number: str, path: str, held: bool, same_name: bool, ref: str) -> tuple[str, str]:
    """A finding's severity and message for `number`, which the default branch took for
    `path` — its tip holds it, or its history gave it (`held`)."""
    noun = NOUN[kind_numbered(number)]
    renumber = (
        f"renumber this {noun} before merging — `pkit analysis new` gives the next free one "
        f"(DEC-001 point 3)"
    )
    if held:
        taken = f"{number} is numbered on {ref} too, for {path}, since this branch left it"
        rule = "the first to reach the default branch keeps the number"
    else:
        taken = (
            f"{number} was numbered on {ref} since this branch left it, for {path}, which "
            f"{ref} no longer holds"
        )
        rule = "a number is never used again"
    if same_name:
        return WARNING, (
            f"{taken}, in a file of the name this branch gives it: possibly your own work "
            f"landed — merge {ref} and keep one file; otherwise {renumber}"
        )
    return ERROR, f"{taken}: {rule}, so {renumber}"


def _name(path: str) -> str:
    return PurePosixPath(path).name


def _resolve(named: backbone.Base) -> Base:
    """The base the backbone named — its commit and where HEAD left it — or
    CannotCompare saying why not: the refusals of the friction change check, in its
    words, since the backbone resolves the base once for both (COR-054 point 5)."""
    if named.problem is not None or named.tip is None or named.fork is None:
        raise CannotCompare(named.problem or f"the base {named.ref!r} cannot be compared.")
    return Base(ref=named.ref, tip=named.tip, commit=named.fork)


def _outdated(base: Base) -> str:
    return (
        f"the base {base.ref} is at {base.tip[: backbone.SHORT]}, which is not an ancestor of "
        f"HEAD: it moved on after this branch left it at {base.commit[: backbone.SHORT]}; "
        f"numbers were compared with its tip — merge or rebase onto {base.ref}, then run again"
    )
