"""What a change's commits contribute, and git's merge of two commits (ADR-057 point 2).

The one home of both in the binary. A reader that walks commits asks here what the
state before each commit is, and judges what it reads against that state by its own
rule: `pkit friction since` a file (COR-062 point 3), the landing check a record or a
rule (ADR-081 point 4). This module reads git and judges nothing.

- **Git's merge of two commits** (`merge`): `git merge-tree --write-tree`, which gives
  a tree and, for a conflict, each path in it. Nothing is checked out. It needs git
  2.38, and a git that cannot run it raises `FrictionCheckError`, never reads as a
  clean merge.
- **The state before a commit** (`prior_state`). For a merge whose other parents each
  lie in the base's history or among the commits walked, it is git's merge of its
  parents, which the caller's `settled` says. So a merge counts only what it adds to
  that merge, and each commit's work is counted once. For any other commit, it is the
  first parent. A commit with no parent has no state before it.
- **A conflicted merge.** Where git's merge of the parents conflicts, the state before
  the commit is git's merges taking one side in every conflict (`-X ours`, `-X
  theirs`). What matches one of those is not the merge's own work. A conflict that is
  not in a file's text has no such merge: a file one side changed and the other
  removed, say. There the parents stand for the two sides, and `PriorState.off_text`
  names the paths git gives.
- **What a commit contributes** (`contributed`): each file it holds otherwise than
  every state before it. `raw_diff` gives one comparison entry by entry, for a reader
  that judges each side.
- **Which commits** (`change_commits`, `first_parent_line`): what a head reaches and a
  tip does not, parents first, or the head's own line back to a commit.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from project_kit.friction_git import SHORT, FrictionCheckError, commit_of, run_git
from project_kit.working_tree import nul_separated

#: The mode a raw diff gives a side that holds no file.
ABSENT = "000000"

#: A file's mode and object in a tree; the mode is `ABSENT` where the tree holds none.
Entry = tuple[str, str]

# `git merge-tree` exits 0 for a clean merge and 1 for one with conflicts.
_MERGED = (0, 1)
# A name that reads as a commit's id, in full or abbreviated.
_HEX = re.compile(r"[0-9a-fA-F]{7,40}")
# Who a stand-in commit of a merge of three or more parents is by. Nothing reads it.
_FOLDED_BY = ("-c", "user.name=pkit", "-c", "user.email=pkit@localhost")


@dataclass(frozen=True)
class Merge:
    """Git's merge of two commits: whether it merged cleanly, its tree, and each path in
    conflict, none where git names none."""

    clean: bool
    tree: str
    conflicted: tuple[str, ...] = ()


@dataclass(frozen=True)
class PriorState:
    """The state before a commit.

    `states` are what the commit is read against, each a tree-ish: one state, or the two
    sides of a conflicted merge, and none for a commit with no parent. `merged` says it
    was read as a merge of its parents. `off_text` names the paths of a conflict outside
    a file's text, `None` where git names none, and `states` are then the parents."""

    states: tuple[str, ...]
    merged: bool = False
    off_text: tuple[str | None, ...] = ()


@dataclass(frozen=True)
class ChangeCommit:
    """One commit of a change: its id, its parents and its subject."""

    commit: str
    parents: tuple[str, ...]
    subject: str


# --- git's merge -----------------------------------------------------------------------


def merge(root: Path, first: str, second: str, *options: str) -> Merge:
    """Git's merge of two commits, `options` given."""
    done = run_git(
        root,
        "merge-tree",
        "--write-tree",
        "-z",
        "--no-messages",
        *options,
        first,
        second,
        accept=(*_MERGED, 128, 129),
    )
    written = done.stdout
    tree = written.split(b"\0", 1)[0].decode().strip()
    # Git also exits 1 for a name it cannot merge, and then writes no tree.
    if done.returncode not in _MERGED or not tree:
        detail = done.stderr.decode("utf-8", "replace").strip().splitlines()
        needs = "a git whose `merge-tree` takes `-X`" if options else "git 2.38 or later"
        raise FrictionCheckError(
            f"`git merge-tree --write-tree {' '.join(options)}` failed — it needs {needs}"
            + (f": {detail[-1]}" if detail else "")
            + "."
        )
    return Merge(done.returncode == 0, tree, () if done.returncode == 0 else _conflicted(written))


def _conflicted(written: bytes) -> tuple[str, ...]:
    """The paths a conflicted `merge-tree -z` lists: `<mode> <object> <stage>\\t<path>`
    after the tree, up to the empty record."""
    records = written.split(b"\0")[1:]
    paths: list[str] = []
    for record in records:
        if not record:
            break
        _meta, tab, path = record.partition(b"\t")
        name = path.decode("utf-8", "surrogateescape")
        if tab and name not in paths:
            paths.append(name)
    return tuple(paths)


def _merge_of(root: Path, parents: Sequence[str], *options: str) -> Merge:
    """Git's merge of `parents`, in order. Git merges two commits at a time, so a merge of
    more is folded, each step's tree standing as a commit of the parents so far."""
    found = merge(root, parents[0], parents[1], *options)
    for index, parent in enumerate(parents[2:], start=2):
        if not found.clean:
            return found
        made = [flag for merged in parents[:index] for flag in ("-p", merged)]
        folded = run_git(root, *_FOLDED_BY, "commit-tree", found.tree, *made, "-m", "fold")
        found = merge(root, folded.stdout.decode().strip(), parent, *options)
    return found


# --- the state before a commit ---------------------------------------------------------


def prior_state(
    root: Path, parents: Sequence[str], *, settled: Callable[[str], bool]
) -> PriorState:
    """The state before a commit with `parents`. `settled` says whether a parent lies in
    the base's history or among the commits walked."""
    if not parents:
        return PriorState(())
    if len(parents) == 1 or not all(settled(parent) for parent in parents[1:]):
        return PriorState((parents[0],))
    merged = _merge_of(root, parents)
    if merged.clean:
        return PriorState((merged.tree,), merged=True)
    sides: list[str] = []
    for side in ("ours", "theirs"):
        taken = _merge_of(root, parents, "-X", side)
        if not taken.clean:
            return PriorState(tuple(parents), merged=True, off_text=taken.conflicted or (None,))
        sides.append(taken.tree)
    return PriorState(tuple(sides), merged=True)


# --- what a commit contributes ---------------------------------------------------------


def raw_diff(root: Path, before: str, after: str) -> Iterable[tuple[str, tuple[Entry, Entry]]]:
    """`git diff-tree -r --no-renames` between two tree-ishes: each path, with its mode
    and object on each side. A submodule's entry is never left out, whatever the working
    tree's `.gitmodules` says (`--ignore-submodules=none`)."""
    out = run_git(
        root, "diff-tree", "-r", "-z", "--no-renames", "--ignore-submodules=none", before, after
    ).stdout
    tokens = nul_separated(out)
    for meta, path in zip(tokens[0::2], tokens[1::2], strict=True):
        mode_b, mode_a, obj_b, obj_a, _status = meta.lstrip(":").split(" ")
        yield path, ((mode_b, obj_b), (mode_a, obj_a))


def contributed(root: Path, prior: PriorState, commit: str) -> frozenset[str]:
    """Each file `commit` holds otherwise than every state before it. What matches one
    side of a conflicted merge is not the merge's own work."""
    states = prior.states or (_empty_tree(root),)
    found = frozenset(path for path, _sides in raw_diff(root, states[0], commit))
    for state in states[1:]:
        found &= frozenset(path for path, _sides in raw_diff(root, state, commit))
    return found


def _empty_tree(root: Path) -> str:
    """The tree of no files, in this repository's object format."""
    done = run_git(root, "hash-object", "-t", "tree", "--stdin", stdin=b"")
    return done.stdout.decode().strip()


# --- which commits ---------------------------------------------------------------------


def commit_named(root: Path, rev: str, what: str) -> str:
    """The commit `rev` names, or `FrictionCheckError`, `what` saying where it was named."""
    commit = None if not rev or rev.startswith("-") else commit_of(root, rev)
    if commit is None:
        raise FrictionCheckError(f"{what} {rev!r} names no commit of this repository.")
    if _HEX.fullmatch(rev) and not commit.startswith(rev.lower()):
        # git reads a branch or tag before a short id: one named like a commit's id
        # would stand in for that commit.
        raise FrictionCheckError(
            f"{what} {rev!r} reads as a commit's id but names {commit[:SHORT]}, through a "
            f"branch or tag of that name; name the commit in full."
        )
    return commit


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    done = run_git(root, "merge-base", "--is-ancestor", ancestor, descendant, accept=(0, 1))
    return done.returncode == 0


def first_parent_line(root: Path, since: str, head: str) -> list[tuple[str, list[str]]]:
    """The commits from `head` back to `since` along first parents, each with its
    parents, newest first."""
    listed = run_git(root, "rev-list", "--first-parent", "--parents", f"{since}..{head}")
    line: list[tuple[str, list[str]]] = []
    for text in listed.stdout.decode().splitlines():
        oids = text.split()
        if len(oids) < 2:
            raise FrictionCheckError(f"`git rev-list` listed a commit without parents: {text!r}.")
        line.append((oids[0], oids[1:]))
    return line


def change_commits(root: Path, tip: str, head: str) -> tuple[ChangeCommit, ...]:
    """The commits `head` reaches and `tip` does not, parents before their children, so a
    parallel line and a stacked parent's commits are among them."""
    listed = run_git(
        root,
        "rev-list",
        "--reverse",
        "--topo-order",
        "--no-commit-header",
        "--format=%H%x00%P%x00%s",
        f"{tip}..{head}",
    ).stdout
    found: list[ChangeCommit] = []
    for line in listed.decode("utf-8", "replace").splitlines():
        commit, parents, subject = line.split("\0", 2)
        found.append(ChangeCommit(commit, tuple(parents.split()), subject))
    return tuple(found)


def descendants(commits: Sequence[ChangeCommit], commit: str) -> frozenset[str]:
    """Those of `commits`, parents first, that descend from `commit`."""
    found = {commit}
    for each in commits:
        if found.intersection(each.parents):
            found.add(each.commit)
    return frozenset(found - {commit})


__all__ = [
    "ABSENT",
    "ChangeCommit",
    "Entry",
    "Merge",
    "PriorState",
    "change_commits",
    "commit_named",
    "contributed",
    "descendants",
    "first_parent_line",
    "is_ancestor",
    "merge",
    "prior_state",
    "raw_diff",
]
