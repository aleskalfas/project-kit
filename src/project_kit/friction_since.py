"""`pkit friction since`: what changed since a commit, apart from merges of the base.

The question a change's answers raise for a pull request whose head moved
(COR-062 point 3; ADR-068 point 5).

A pull request's head moves when the change answers again and commits. A reader
that must tell such a move from any other — the landing command of a
work-tracking component, say — asks this command whether every change from
commit `since` to the head, apart from merges of the base, lies inside answer
files the change adds. A change writes its answers only by adding answer files
of its own (COR-062 point 3), so those are the files a round of answers changes.
The answer folder is the backbone's (`answer_files`), so no component reads it
itself. It reads git and writes nothing.

- **The head** is commit `--head`, else HEAD, read from git objects: the
  working tree is not read. **The base** is resolved as every reader resolves
  it (COR-054): `--base`, else `$PKIT_CHECK_BASE`, else the default branch.
  Its tip is read to tell a merge of the base, and the base **where the head
  left it** — each merge-base of the head and that tip — to tell an answer
  file the change adds from one the base holds.
- **The line.** The head must descend from `since`, and `since` must lie on
  the head's own line of commits, its first parents. Otherwise the answer is
  no, with why: the branch was rebased, or `since` reached it only through a
  merge.
- **What each commit on the line contributes.**
  - *A merge of the base* — a merge commit whose second parent is in the
    base tip's history — contributes only what differs from git's clean merge
    of its two parents (`git merge-tree --write-tree`). Where that merge
    conflicts, the commit is held against git's merge taking each side of
    every conflict in a file's text (`-X ours`, `-X theirs`), and must differ
    from both only in answer files the change adds. A conflict that is not in
    a file's text — a file changed on one side and removed on the other, say —
    is a change outside them.
  - *Any other commit* contributes its own diff against its first parent: a
    merge of anything but the base included.
- **Inside the change's answer files.** A file that differs lies inside only
  when it is an answer file (`answer_files.is_answer_file`) the base, where the
  head left it, does not hold, and on the commit's side a regular file. An
  answer file removed lies outside, since it takes its answers away (COR-062
  point 8). So does one the base holds, which no change rewrites (point 3), and
  one whose mode changed. Any other file lies outside, with why. What an answer
  file says is the checks' to judge, never this command's.
- **It cannot answer** — and says why, exit 1 — in a shallow clone, where the
  history between the commits may not be here, when a name is no commit or
  the base does not resolve, and when git lacks `merge-tree --write-tree`
  (2.38) or, for a conflicted merge, its `-X` option.

Version 1 of its document counted changes inside the artefacts' `revalidated`
blocks and `revisited` lists, where answers lived before they moved into answer
files (COR-062 point 11). Version 2 counts answer files the change adds, and
nothing in a block.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from project_kit import answer_files, cli_render, default_branch
from project_kit.friction_check import printable  # the friction group's one escape of a human view
from project_kit.friction_git import (
    SHORT,
    FrictionCheckError,
    commit_of,
    run_git,
)
from project_kit.working_tree import nul_separated

#: The version of the document `render_json` returns, under the rule every reading
#: document of the `friction` group follows: raised when a key a reader relies on
#: changes its meaning or goes, never for a key added. What `all_inside` counts is part
#: of its meaning, since a reader gates on it. Version 1 counted the artefacts'
#: `revalidated` blocks and `revisited` lists; version 2 counts answer files the change
#: adds (COR-062 point 3; ADR-068 point 5).
SINCE_SCHEMA_VERSION = 2

# What a file's mode is, as a tree writes it, when it is a regular file.
_FILE_MODES = frozenset({"100644", "100755"})
# The mode a raw diff gives a side that holds no file.
_ABSENT = "000000"
# `git merge-tree` exits 0 for a clean merge and 1 for one with conflicts.
_MERGED = (0, 1)
# A name that reads as a commit's id, in full or abbreviated.
_HEX = re.compile(r"[0-9a-fA-F]{7,40}")


@dataclass(frozen=True)
class Outside:
    """A change outside the answer files the change adds: the file, the commit that made
    it, and why it lies outside. `path` is `None` for a merge of the base whose conflict
    git names no file of."""

    path: str | None
    commit: str
    why: str


@dataclass(frozen=True)
class Step:
    """One commit on the head's line since `since`, and whether it merges the base."""

    commit: str
    merges_base: bool


@dataclass(frozen=True)
class Since:
    """What changed from `since` to `head`, apart from merges of the base.

    `reason` says why no change can be set inside the change's answer files as a whole —
    the head does not descend from `since`, say — and is `None` otherwise. `inside`
    holds the answer files the change adds that changed, `outside` each change that
    lies elsewhere. What a reader makes of the answer — whether an authorisation for
    `since` covers `head`, say — is the reader's."""

    since: str
    head: str
    base_ref: str
    base_tip: str
    steps: tuple[Step, ...] = ()
    inside: tuple[str, ...] = ()
    outside: tuple[Outside, ...] = ()
    reason: str | None = None

    @property
    def all_inside(self) -> bool:
        """Every change since, apart from merges of the base, lies inside answer files the
        change adds."""
        return self.reason is None and not self.outside


def run_since(
    target_root: Path,
    since_rev: str,
    *,
    head_rev: str | None = None,
    base_ref: str | None = None,
    resolved: default_branch.Base | None = None,
) -> Since:
    """What changed from commit `since_rev` to commit `head_rev` — HEAD when `None` —
    apart from merges of the base `base_ref` (else `$PKIT_CHECK_BASE`, else the default
    branch). `resolved` is that base when the caller has read it already
    (`default_branch.settled`), so it is not resolved twice. Raises
    `FrictionCheckError` when it cannot answer."""
    since = _commit(target_root, since_rev, "the commit named")
    head = _commit(target_root, head_rev or "HEAD", "--head" if head_rev else "HEAD")
    if run_git(target_root, "rev-parse", "--is-shallow-repository").stdout.strip() == b"true":
        raise FrictionCheckError(
            "this clone is shallow, so the history between the two commits may not be here; "
            "fetch it (`git fetch --unshallow`) and run again."
        )
    base = resolved or default_branch.base(target_root, base_ref, head_rev=head)
    if base.problem is not None or base.tip is None:
        raise FrictionCheckError(base.problem or f"the base {base.ref!r} names no commit.")
    found = Since(since, head, base.ref, base.tip)
    if since == head:
        return found
    if not _is_ancestor(target_root, since, head):
        return _off_the_line(
            found,
            f"{head[:SHORT]} does not descend from {since[:SHORT]}: the branch was rebased "
            f"or force-pushed",
        )
    line = _first_parent_line(target_root, since, head)
    if not line or line[-1][1][0] != since:
        return _off_the_line(
            found,
            f"{since[:SHORT]} is not on {head[:SHORT]}'s own line of commits: it reached the "
            f"branch only through a merge",
        )
    held = _base_answer_files(target_root, head, base.tip)
    steps: list[Step] = []
    inside: set[str] = set()
    outside: list[Outside] = []
    for commit, parents in reversed(line):
        merges_base = len(parents) == 2 and _is_ancestor(target_root, parents[1], base.tip)
        steps.append(Step(commit, merges_base))
        judged: Sequence[tuple[str | None, str | None]] = (
            _merge_of_base(target_root, held, commit, parents[0], parents[1])
            if merges_base
            else _against(target_root, held, commit, (parents[0],))
        )
        for path, why in judged:
            if why is not None:
                outside.append(Outside(path, commit, why))
            elif path is not None:
                inside.add(path)
    return Since(
        since,
        head,
        base.ref,
        base.tip,
        steps=tuple(steps),
        inside=tuple(sorted(inside - {o.path for o in outside})),
        outside=tuple(outside),
    )


def _off_the_line(found: Since, reason: str) -> Since:
    return Since(found.since, found.head, found.base_ref, found.base_tip, reason=reason)


def _commit(root: Path, rev: str, what: str) -> str:
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


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    done = run_git(root, "merge-base", "--is-ancestor", ancestor, descendant, accept=(0, 1))
    return done.returncode == 0


def _first_parent_line(root: Path, since: str, head: str) -> list[tuple[str, list[str]]]:
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


def _base_answer_files(root: Path, head: str, tip: str) -> frozenset[str]:
    """The answer files the base holds where the head left it: those of each merge-base of
    the head and the base's tip, by path. Where several are merge-bases, a file any of
    them holds is the base's, so a file is read as the change's own only where no base
    holds it."""
    done = run_git(root, "merge-base", "--all", head, tip, accept=(0, 1))
    bases = done.stdout.decode().split() if done.returncode == 0 else []
    return frozenset(
        answer_files.path_of(name) for base in bases for name in answer_files.head_names(root, base)
    )


# --- one commit ----------------------------------------------------------------------


def _merge_of_base(
    root: Path, held: frozenset[str], commit: str, first: str, second: str
) -> Sequence[tuple[str | None, str | None]]:
    """A merge of the base, held against git's clean merge of its parents — or, where
    that merge conflicts, against git's merge taking each side of every conflict."""
    clean, written = _merge_tree(root, first, second)
    if clean:
        return _against(root, held, commit, (_tree_of(written),))
    sides: list[str] = []
    for side in ("ours", "theirs"):
        clean, written = _merge_tree(root, first, second, "-X", side)
        if not clean:
            why = (
                "the merge of the base conflicts on it outside its text, as where one side "
                "changed a file the other removed or renamed"
            )
            named: list[str | None] = [*_conflicted(written)] or [None]
            return [(path, why) for path in named]
        sides.append(_tree_of(written))
    return _against(root, held, commit, tuple(sides))


def _merge_tree(root: Path, first: str, second: str, *options: str) -> tuple[bool, bytes]:
    """Git's merge of two commits, `options` given: whether it merged cleanly, and what
    `merge-tree --write-tree -z` wrote — the tree, then each conflicted path."""
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
    if done.returncode not in _MERGED:
        detail = done.stderr.decode("utf-8", "replace").strip().splitlines()
        needs = "a git whose `merge-tree` takes `-X`" if options else "git 2.38 or later"
        raise FrictionCheckError(
            f"`git merge-tree --write-tree {' '.join(options)}` failed — it needs {needs}"
            + (f": {detail[-1]}" if detail else "")
            + "."
        )
    return done.returncode == 0, done.stdout


def _tree_of(written: bytes) -> str:
    return written.split(b"\0", 1)[0].decode().strip()


def _conflicted(written: bytes) -> list[str]:
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
    return paths


def _against(
    root: Path, held: frozenset[str], commit: str, expected: Sequence[str]
) -> list[tuple[str, str | None]]:
    """Each file `commit` holds otherwise than a tree-ish of `expected`, with why it lies
    outside the change's answer files, or `None` where it lies inside them against each."""
    diffs = [dict(_raw_diff(root, tree, commit)) for tree in expected]
    paths: set[str] = set()
    for diff in diffs:
        paths.update(diff)
    judged: list[tuple[str, str | None]] = []
    for path in sorted(paths):
        whys = (_judge(held, path, *diff[path]) for diff in diffs if path in diff)
        judged.append((path, next((why for why in whys if why is not None), None)))
    return judged


#: A file's mode and object in a tree; the mode is `_ABSENT` where the tree holds none.
_Entry = tuple[str, str]


def _raw_diff(root: Path, before: str, after: str) -> Iterable[tuple[str, tuple[_Entry, _Entry]]]:
    """`git diff-tree -r --no-renames` between two tree-ishes: each path, with its mode
    and object on each side."""
    out = run_git(root, "diff-tree", "-r", "-z", "--no-renames", before, after).stdout
    tokens = nul_separated(out)
    for meta, path in zip(tokens[0::2], tokens[1::2], strict=True):
        mode_b, mode_a, obj_b, obj_a, _status = meta.lstrip(":").split(" ")
        yield path, ((mode_b, obj_b), (mode_a, obj_a))


def _judge(held: frozenset[str], path: str, before: _Entry, after: _Entry) -> str | None:
    """Why the change to the file at `path`, from `before` to the commit's `after`, lies
    outside the answer files the change adds, or `None` where it lies inside them."""
    (mode_b, _obj_b), (mode_a, _obj_a) = before, after
    if not answer_files.is_answer_file(path):
        return "not an answer file"
    if mode_a == _ABSENT:
        return "an answer file removed, which takes its answers away"
    if path in held:
        return "an answer file the base holds, which no change rewrites"
    if mode_a not in _FILE_MODES:
        return "not a regular file"
    if mode_b not in (_ABSENT, mode_a):
        return f"its mode changed ({mode_b} to {mode_a})"
    return None


# --- output --------------------------------------------------------------------------


def render_json(found: Since) -> str:
    """The stable machine-readable answer: keys sorted, the same bytes for the same state."""
    document = {
        "schema_version": SINCE_SCHEMA_VERSION,
        "report": "since",
        "since": found.since,
        "head": found.head,
        "base": {"ref": found.base_ref, "tip": found.base_tip},
        "all_inside": found.all_inside,
        "reason": found.reason,
        "commits": [{"commit": s.commit, "merges_base": s.merges_base} for s in found.steps],
        "inside": list(found.inside),
        "outside": [{"path": o.path, "commit": o.commit, "why": o.why} for o in found.outside],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def render_human(found: Since) -> str:
    """Whether every change since lies inside answer files the change adds, and each that
    does not. A path and a reason are the author's words, so each is printed escaped, as
    the change check's human view prints them (`printable`)."""
    since, head = found.since[:SHORT], found.head[:SHORT]
    base = printable(found.base_ref)
    title = cli_render.style("title", "Friction since")
    lines = [f"{title} — {since} to {head}, apart from merges of {base}", ""]
    if found.reason is not None:
        lines.append(f"  Not all inside the change's answer files: {printable(found.reason)}.")
    elif not found.steps:
        lines.append("  Nothing changed: the two commits are one.")
    else:
        merges = sum(1 for step in found.steps if step.merges_base)
        lines.append(f"  {len(found.steps)} commit(s), {merges} of them merging {base}.")
        for path in found.inside:
            lines.append(f"  {printable(path)} — an answer file this change adds")
        for change in found.outside:
            where = printable(change.path) if change.path else "(the merge)"
            why = printable(change.why)
            lines.append(f"  {where} — outside, in {change.commit[:SHORT]}: {why}")
        lines.append("")
        lines.append(
            "  Every change lies inside answer files this change adds."
            if found.all_inside
            else "  Not all inside the change's answer files: a change lies outside them."
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "SINCE_SCHEMA_VERSION",
    "Outside",
    "Since",
    "Step",
    "render_human",
    "render_json",
    "run_since",
]
