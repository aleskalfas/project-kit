"""The numbers a history gave: the default branch's history, read as the tree is.

An id is never used again (DEC-001 point 3), so a number a file was given
stays held once the file is gone. The backbone reads one state at a time
(`pkit friction artefacts [--at]`), so a history is read in two steps:

- git lists each path a history added under the use-case and journey places,
  with the commit that added it — one `git log`, whatever the history's
  length (`backbone.added`). A rename is a removal and an addition, so every
  name a file had is there, and each carries the number its name gives
  (`id_in_name`), as the stamp names every file;
- a path counts only when the backbone's reading at the commit that added it
  held it as a file of its place — a Markdown file there, not left out by
  `friction.exclude` — the files the tree reading counts (`Judge`). A path
  the working tree or the default branch's tip leaves out now is left out,
  whatever it was. That reading speaks for the path only when the place it
  lies under was the place then: where the place was elsewhere, or not yet —
  the location moved there since, or the capability came later — it cannot
  say, and the path counts.

A number that counts so is freed only by the project's numbering setting: a
file it frees holds no number (`_lib/numbering.py`, which says which files
those are — every file the history gave a number it frees); the judge is given
them, and says which commit freed a number that would have counted
(`freed_by`).

Only what could change an answer is judged: for the stamp, the numbers past
the highest the tree and the tip hold, highest first, until one counts
(`highest`), and the highest of them the setting freed (`freed_past`); for the
number comparison, the numbers the branch holds that the default branch's
history gave since the fork and its tip no longer holds (`counted`). One
reading per commit judged, and none when the history gave no such number. A
reading that fails counts the path too: an id is never used again, so a
number is never freed on a reading that could not be made.

Its blind spot is a file never named after its number, and deleted since.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from _lib import backbone
from _lib.model import PREFIX, Analysis, Unreadable, id_in_name, number_of


@dataclass(frozen=True)
class Given:
    """A number a history gave a file: the id its name carries, the file, and the
    commit that added it."""

    id: str
    path: str
    commit: str


def given(root: Path, revisions: str, folders: Iterable[str]) -> list[Given]:
    """Each number `revisions` gave a file under `folders`, newest first, by its name —
    whether each counts is `Judge`'s to say."""
    return [
        Given(named, path, commit)
        for commit, path in backbone.added(root, revisions, folders)
        if (named := id_in_name(path)) is not None
    ]


class Judge:
    """Whether a number a history gave counts: no present state — the readings in
    `present` — leaves the path out, and the backbone's reading at the commit that
    added the file held it as a file of its place, or cannot say: it failed, or the
    place the path lies under now was not its place then; and the numbering setting
    did not free it — `freed` names each file it frees, by its path and the commit
    that added it, with the commit of the setting that freed it. One reading per
    commit."""

    def __init__(
        self,
        root: Path,
        present: Iterable[Analysis],
        freed: Mapping[tuple[str, str], str] | None = None,
    ) -> None:
        states = tuple(present)
        self._root = root
        self._left_out = frozenset().union(*(state.excluded for state in states))
        self._kind_of_place = {
            place: kind for state in states for kind, place in state.places.items()
        }
        self._freed = dict(freed or {})
        self._at: dict[str, Analysis | None] = {}

    def counts(self, number: Given) -> bool:
        return (number.path, number.commit) not in self._freed and self._held(number)

    def freed_by(self, number: Given) -> str | None:
        """The commit of the numbering setting that freed `number` — it removed the file
        the history gave it, which held it — or `None`."""
        commit = self._freed.get((number.path, number.commit))
        return commit if commit is not None and self._held(number) else None

    def _held(self, number: Given) -> bool:
        """Whether the file the history gave `number` held it, the setting aside."""
        if number.path in self._left_out:
            return False
        state = self._reading(number.commit)
        place = next((p for p in self._kind_of_place if number.path.startswith(f"{p}/")), None)
        if state is None or place is None or state.places.get(self._kind_of_place[place]) != place:
            return True  # a reading that cannot speak for the path never frees its number
        return number.path in state.files

    def _reading(self, commit: str) -> Analysis | None:
        if commit not in self._at:
            try:
                self._at[commit] = backbone.read_analysis(self._root, at=commit)
            except Unreadable:
                self._at[commit] = None
        return self._at[commit]


def highest(judge: Judge, numbers: Sequence[Given], kind: str, above: int) -> Given | None:
    """The highest number of `kind` in `numbers` past `above` that counts, with the file
    it was last given to; `None` when none does."""
    return next((n for n in _past(numbers, kind, above) if judge.counts(n)), None)


def freed_past(
    judge: Judge, numbers: Sequence[Given], kind: str, above: int
) -> tuple[Given, str] | None:
    """The highest number of `kind` in `numbers` past `above` that the numbering setting
    freed, with the commit that freed it; `None` when it freed none."""
    past = _past(numbers, kind, above)
    return next(((n, commit) for n in past if (commit := judge.freed_by(n)) is not None), None)


def _past(numbers: Sequence[Given], kind: str, above: int) -> list[Given]:
    """The numbers of `kind` in `numbers` past `above`, highest first."""
    prefix = f"{PREFIX[kind]}-"
    return sorted(
        (n for n in numbers if n.id.startswith(prefix) and number_of(n.id) > above),
        key=lambda n: -number_of(n.id),  # stable: the newest file first, for one number
    )


def counted(judge: Judge, numbers: Sequence[Given], ids: Iterable[str]) -> dict[str, Given]:
    """Each id of `ids` in `numbers` that counts, with the newest file given it that does."""
    wanted = set(ids)
    found: dict[str, Given] = {}
    for number in numbers:
        if number.id in wanted and number.id not in found and judge.counts(number):
            found[number.id] = number
    return found
