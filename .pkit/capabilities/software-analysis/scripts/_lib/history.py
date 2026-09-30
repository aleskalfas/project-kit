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
  whatever it was.

Only what could change the stamp's answer is judged: the numbers past the
highest the tree and the tip hold, highest first, until one counts. One
reading per commit judged, and none when the history gave no number past the
tree's and the tip's. A reading that fails counts the path:
an id is never used again, so a number is never freed on a reading that
could not be made.

Its blind spot is a file never named after its number, and deleted since.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
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
    """Whether a number a history gave counts: the backbone's reading at the commit
    that added the file held it as a file of its place, and no present state — the
    readings in `present` — leaves the path out. One reading per commit asked."""

    def __init__(self, root: Path, present: Iterable[Analysis]) -> None:
        self._root = root
        self._left_out = frozenset().union(*(state.excluded for state in present))
        self._at: dict[str, Analysis | None] = {}

    def counts(self, number: Given) -> bool:
        if number.path in self._left_out:
            return False
        if number.commit not in self._at:
            try:
                self._at[number.commit] = backbone.read_analysis(self._root, at=number.commit)
            except Unreadable:
                self._at[number.commit] = None
        state = self._at[number.commit]
        return state is None or number.path in state.files


def highest(judge: Judge, numbers: Sequence[Given], kind: str, above: int) -> Given | None:
    """The highest number of `kind` in `numbers` past `above` that counts, with the file
    it was last given to; `None` when none does."""
    prefix = f"{PREFIX[kind]}-"
    past = sorted(
        (n for n in numbers if n.id.startswith(prefix) and number_of(n.id) > above),
        key=lambda n: -number_of(n.id),  # stable: the newest file first, for one number
    )
    return next((n for n in past if judge.counts(n)), None)
