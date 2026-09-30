"""software-analysis' comparison of numbers with the default branch (DEC-001 point 3).

When two lines of work number a new use case or journey the same, the first to
reach the default branch keeps the number, and the other renumbers before
merging. This is where the other finds out: a use case or journey numbered in
the working tree whose number the default branch's tip holds too, where the
merge-base — where this branch left the default branch — held no file with
that id, and where the default branch's file for it is no version of a file
this branch's own history wrote.

An artefact is known by its id, never by its path:

- **an id moved** within the branch — into an area, say — or on the default
  branch is no collision: the merge-base held it, so neither side took it;
- **two lines of work stamping the same slug** at the same path collide,
  though the paths are one: each took the number for its own artefact;
- **this branch's own work, landed** — a parent branch squash-merged or
  rebased onto the default branch while this one was stacked on it — is no
  collision, wherever this branch has moved the file since: the default
  branch's file for the number is, byte for byte, a version this branch's
  history wrote. So is anything two lines of work wrote to the very byte,
  which git merges as one file.

Once the default branch is merged in, a number both took is two files holding
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
backbone's discovery at a commit (`pkit friction artefacts --at`), a file's
number read from its front matter or else its name (`id_in_name`), as the
stamp counts it. Git answers which commits those are, and which versions of
the use-case and journey files this branch's history wrote since the
merge-base and the default branch's tip holds (`backbone.blobs_written`,
`backbone.blob_of`) — asked only for a number both sides took.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import backbone, schemas
from _lib.findings import ERROR, REPORT, Finding, Outcome
from _lib.model import NOUN, NUMBERED, Analysis, Artefact, Unreadable, id_in_name, identity

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
        before = backbone.read_analysis(root, at=base.commit).held()
    except Unreadable as exc:
        raise CannotCompare(f"{ref} could not be read: {exc}") from exc

    line = (
        f"numbers: compared with {ref} ({base.tip[:SHORT]}; this branch left it at "
        f"{base.commit[:SHORT]})."
    )
    outdated = Finding(REPORT, analysis.location or ".", f"outdated base: {_outdated(base)}")
    # Each number taken since this branch left the base, by what it stands for, as the
    # stamp and the validator compare ids; the ids numbered here are those the id
    # schema admits, each its own identity already.
    taken = {i: path for i, path in _holders(on_base).items() if i not in before}
    both = {str(a.id) for a in numbered if a.id in taken}
    folders = {a.places[k] for a in (analysis, on_base) for k in NUMBERED if k in a.places}
    ours = backbone.blobs_written(root, base.commit, folders) if both else set()
    theirs = {i: taken[i] for i in both if backbone.blob_of(root, base.tip, taken[i]) not in ours}
    return Comparison(base, Outcome([line], [outdated, *_collisions(numbered, theirs, ref)]))


def _holders(analysis: Analysis) -> dict[str, str]:
    """Each use case's or journey's number the analysis holds, and the file holding it:
    by its front matter's id, else by the number its name carries — as the stamp
    counts a number held."""
    holders = {
        named: path
        for path, kind in analysis.files.items()
        if kind in NUMBERED and (named := id_in_name(path)) is not None
    }
    holders.update(
        {identity(a.id): a.path for a in analysis.artefacts if a.kind in NUMBERED and a.id}
    )
    return holders


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


def _collisions(numbered: list[Artefact], theirs: dict[str, str], ref: str) -> list[Finding]:
    """Each number this branch took that `ref` took too, since this branch left it, for
    an artefact of another line of work: `theirs`, each with the file holding it."""
    return [
        Finding(
            ERROR,
            artefact.location,
            f"{artefact.id} is numbered on {ref} too, for {theirs[str(artefact.id)]}, since this "
            f"branch left it: the first to reach the default branch keeps the number, so renumber "
            f"this {NOUN[artefact.kind]} before merging — `pkit analysis new` gives the next free "
            f"one (DEC-001 point 3)",
        )
        for artefact in numbered
        if artefact.id in theirs
    ]
