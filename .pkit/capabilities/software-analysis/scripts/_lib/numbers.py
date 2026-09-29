"""software-analysis' comparison of numbers with the default branch (DEC-001 point 3).

When two lines of work number a new use case or journey the same, the first to
reach the default branch keeps the number, and the other renumbers before
merging. This is where the other finds out: a use case or journey numbered in
the working tree whose number the default branch's tip gives another file,
where the merge-base — where this branch left the default branch — held no
artefact with that id. A move within the branch (into an area) is not one;
once the default branch is merged in, a number both took is two files holding
one id, which the validator reports as a duplicate.

It reads a base, so it answers about a change rather than the tree, and is not
a validator (ADR-058 point 7): `pkit analysis check-numbers` runs it, a line of
its own in a project's check gate, as the friction change check is. Like that
check it cannot answer without its base — a base that names no commit, or
shares no history with HEAD, fails it — except when the working tree numbers
nothing, where there is nothing to compare. When the base moved on after this
branch left it — the only case in which it can have taken a number since — that
is reported, never failed, as the change check reports an outdated base.

The default branch is read at its tip and at the merge-base through the
backbone's discovery at a commit (`pkit friction artefacts --at`); git answers
only which commits those are.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import backbone, schemas
from _lib.findings import ERROR, REPORT, Finding, Outcome
from _lib.model import NOUN, NUMBERED, Artefact, Unreadable

#: The version of the `--json` document.
SCHEMA_VERSION = 1

#: How many characters of a commit a message shows.
SHORT = 12


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
    """The answer: the base compared with, when one was needed, and the outcome."""

    base: Base | None
    outcome: Outcome

    def document(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "base": None if self.base is None else self.base.as_json(),
            **self.outcome.document(),
        }


def compare(root: Path, ref: str) -> Comparison:
    """Compare the numbers in the working tree at `root` with the default branch `ref`.
    Raises CannotCompare when it cannot answer."""
    try:
        analysis = backbone.read_analysis(root)
    except Unreadable as exc:
        raise CannotCompare(f"the analysis could not be read: {exc}") from exc
    numbered = [
        a
        for a in analysis.artefacts
        if a.kind in NUMBERED and a.id and schemas.id_pattern(a.kind).match(a.id)
    ]
    if not numbered:
        line = f"numbers: no use case or journey is numbered here; nothing to compare with {ref}."
        return Comparison(None, Outcome([line]))

    base = _resolve(root, ref)
    if not base.outdated:
        line = f"numbers: this branch contains {ref} ({base.tip[:SHORT]}); nothing to collide with."
        return Comparison(base, Outcome([line]))
    try:
        on_base = backbone.read_analysis(root, at=base.tip)
        before = {a.id for a in backbone.read_analysis(root, at=base.commit).artefacts}
    except Unreadable as exc:
        raise CannotCompare(f"{ref} could not be read: {exc}") from exc

    line = (
        f"numbers: compared with {ref} ({base.tip[:SHORT]}; this branch left it at "
        f"{base.commit[:SHORT]})."
    )
    outdated = Finding(REPORT, analysis.location or ".", f"outdated base: {_outdated(base)}")
    taken = {a.id: a.path for a in on_base.artefacts if a.kind in NUMBERED and a.id}
    return Comparison(base, Outcome([line], [outdated, *_collisions(numbered, taken, before, ref)]))


def _resolve(root: Path, ref: str) -> Base:
    """The base's commit and its merge-base with HEAD, or CannotCompare saying why not —
    the refusals of the friction change check, for the same reasons."""
    if not ref or ref.startswith("-"):
        raise CannotCompare(f"the base {ref!r} is not a revision name.")
    head = backbone.commit_of(root, "HEAD")
    if head is None:
        raise CannotCompare(
            "HEAD names no commit yet; numbers are compared between a branch and its base, "
            "so commit first."
        )
    tip = backbone.commit_of(root, ref)
    if tip is None:
        raise CannotCompare(
            f"the base {ref!r} does not resolve to a commit in this repository: fetch it "
            f"(e.g. `git fetch origin main`), or name another with --base or "
            f"${backbone.BASE_ENV}."
        )
    fork = backbone.merge_base(root, tip, head)
    if fork is None:
        raise CannotCompare(
            f"HEAD and the base {ref!r} share no history to compare; in a shallow clone, "
            f"fetch the history back to where the branch left the base (e.g. `git fetch "
            f"--unshallow`)."
        )
    return Base(ref=ref, tip=tip, commit=fork)


def _outdated(base: Base) -> str:
    return (
        f"the base {base.ref} is at {base.tip[:SHORT]}, which is not an ancestor of HEAD: it "
        f"moved on after this branch left it at {base.commit[:SHORT]}; numbers were compared "
        f"with its tip — merge or rebase onto {base.ref}, then run again"
    )


def _collisions(
    numbered: list[Artefact], taken: dict[str, str], before: set[str | None], ref: str
) -> list[Finding]:
    """Each number this branch took that `ref` took too, for another file, since this
    branch left it."""
    here: dict[str, set[str]] = defaultdict(set)
    for artefact in numbered:
        here[str(artefact.id)].add(artefact.path)
    return [
        Finding(
            ERROR,
            artefact.location,
            f"{artefact.id} is numbered on {ref} too, for {taken[str(artefact.id)]}, since this "
            f"branch left it: the first to reach the default branch keeps the number, so renumber "
            f"this {NOUN[artefact.kind]} before merging — `pkit analysis new` gives the next free "
            f"one (DEC-001 point 3)",
        )
        for artefact in numbered
        if artefact.id in taken
        and artefact.id not in before
        and taken[str(artefact.id)] not in here[str(artefact.id)]
    ]
