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
    merge of anything but the base included, and a merge of three or more
    parents.
- **Inside the change's answer files.** A file that differs lies inside only
  when it is an answer file the base, where the head left it, does not hold, and
  on the commit's side a regular file. Its path is judged as the tree writes it,
  and a hidden name is none (`_is_answer_path`). A submodule's entry is always
  read, whatever `.gitmodules` says, so a repointed submodule lies outside. An
  answer file removed lies outside, since it takes its answers away (COR-062
  point 8). So does one the base holds, which no change rewrites (point 3), and
  one whose mode changed. Any other file lies outside, with why. What an answer
  file says is the checks' to judge, never this command's.
- **It cannot answer** — and says why, exit 1 — in a shallow clone, where the
  history between the commits may not be here, when a name is no commit or
  the base does not resolve, and when git lacks `merge-tree --write-tree`
  (2.38) or, for a conflicted merge, its `-X` option.

Which commits it walks, git's merges and the state before each commit are read
through the home of what a change's commits contribute (`commit_contributions`,
ADR-057 point 2). What it judges against them is its own. A parent on the head's
own line is an ancestor of the first parent, so git's merge of such a commit's
parents is that first parent, and only the base's history needs asking.

Version 1 of its document counted changes inside the artefacts' `revalidated`
blocks and `revisited` lists, where answers lived before they moved into answer
files (COR-062 point 11). Version 2 counts answer files the change adds, and
nothing in a block.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from project_kit import answer_files, cli_render, default_branch
from project_kit import commit_contributions as contributions
from project_kit.commit_contributions import ABSENT, Entry
from project_kit.friction_check import printable  # the friction group's one escape of a human view
from project_kit.friction_git import (
    SHORT,
    FrictionCheckError,
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
    since = contributions.commit_named(target_root, since_rev, "the commit named")
    head = contributions.commit_named(
        target_root, head_rev or "HEAD", "--head" if head_rev else "HEAD"
    )
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
    if not contributions.is_ancestor(target_root, since, head):
        return _off_the_line(
            found,
            f"{head[:SHORT]} does not descend from {since[:SHORT]}: the branch was rebased "
            f"or force-pushed",
        )
    line = contributions.first_parent_line(target_root, since, head)
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
        prior = _prior_state(target_root, parents, base.tip)
        steps.append(Step(commit, prior.merged))
        for path, why in _contribution(target_root, held, commit, prior):
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


def _base_answer_files(root: Path, head: str, tip: str) -> frozenset[str]:
    """The answer files the base holds where the head left it: those of each merge-base of
    the head and the base's tip, by path. Where several are merge-bases, a file any of
    them holds is the base's, so a file is read as the change's own only where no base
    holds it."""
    done = run_git(root, "merge-base", "--all", head, tip, accept=(0, 1))
    bases = done.stdout.decode().split() if done.returncode == 0 else []
    held: set[str] = set()
    for base in bases:
        # A listing git cannot give fails the run, never reads as a base holding nothing.
        listed = run_git(
            root, "ls-tree", "-z", "--name-only", base, "--", f"{answer_files.FOLDER}/"
        )
        held.update(rel for rel in nul_separated(listed.stdout) if _is_answer_path(rel))
    return frozenset(held)


def _is_answer_path(path: str) -> bool:
    """Whether `path`, exactly as a tree writes it, is an answer file: a YAML file directly
    in the answer folder whose name is no hidden file's. The path is compared as written, so
    a tree entry such as `<folder>/./x.yaml` is no answer file."""
    folder, slash, name = path.rpartition("/")
    return (
        bool(slash)
        and folder == answer_files.FOLDER
        and not name.startswith(".")
        and answer_files.is_answer_file(path)
    )


# --- one commit ----------------------------------------------------------------------


def _prior_state(root: Path, parents: Sequence[str], tip: str) -> contributions.PriorState:
    """The state before a commit with `parents`. Only a merge of two parents can be a merge
    of the base, so what `all_inside` counts stays as its document's version says: a merge
    of more is read against its first parent, as any other commit is."""
    if len(parents) > 2:
        return contributions.PriorState((parents[0],))
    return contributions.prior_state(
        root, parents, settled=lambda parent: contributions.is_ancestor(root, parent, tip)
    )


def _contribution(
    root: Path, held: frozenset[str], commit: str, prior: contributions.PriorState
) -> Sequence[tuple[str | None, str | None]]:
    """What one commit contributes, against the state before it. A merge of the base is
    held against git's merge of its parents, or, where that conflicts, against git's merge
    taking each side of every conflict. A conflict no side settles lies outside."""
    if prior.off_text:
        why = (
            "the merge of the base conflicts on it outside its text, as where one side "
            "changed a file the other removed or renamed"
        )
        return [(path, why) for path in prior.off_text]
    return _against(root, held, commit, prior.states)


def _against(
    root: Path, held: frozenset[str], commit: str, expected: Sequence[str]
) -> list[tuple[str, str | None]]:
    """Each file `commit` holds otherwise than a tree-ish of `expected`, with why it lies
    outside the change's answer files, or `None` where it lies inside them against each."""
    diffs = [dict(contributions.raw_diff(root, tree, commit)) for tree in expected]
    paths: set[str] = set()
    for diff in diffs:
        paths.update(diff)
    judged: list[tuple[str, str | None]] = []
    for path in sorted(paths):
        whys = (_judge(held, path, *diff[path]) for diff in diffs if path in diff)
        judged.append((path, next((why for why in whys if why is not None), None)))
    return judged


def _judge(held: frozenset[str], path: str, before: Entry, after: Entry) -> str | None:
    """Why the change to the file at `path`, from `before` to the commit's `after`, lies
    outside the answer files the change adds, or `None` where it lies inside them."""
    (mode_b, _obj_b), (mode_a, _obj_a) = before, after
    if not _is_answer_path(path):
        return "not an answer file"
    if mode_a == ABSENT:
        return "an answer file removed, which takes its answers away"
    if path in held:
        return "an answer file the base holds, which no change rewrites"
    if mode_a not in _FILE_MODES:
        return "not a regular file"
    if mode_b not in (ABSENT, mode_a):
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
