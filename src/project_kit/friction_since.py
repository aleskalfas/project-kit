"""`pkit friction since`: what changed since a commit, apart from merges of the base.

The question COR-050 point 3's answers raise for a pull request whose head moved.

A pull request's head moves when a merge of its base leaves its answers stale
and the round that answers them again commits. A reader that must tell such a
move from any other — the landing command of a work-tracking component, say —
asks this command whether every change from commit `since` to the head,
apart from merges of the base, lies inside the text that holds the answers:
`revalidated` blocks (point 3) and `revisited` lists, whose entries a link
asks of its source (point 16). It reads them as the other friction commands
read them, so no component parses them itself. It reads git and writes
nothing.

- **The head** is commit `--head`, else HEAD, read from git objects: the
  working tree is not read. **The base** is resolved as every reader resolves
  it (COR-054): `--base`, else `$PKIT_CHECK_BASE`, else the default branch.
  Only its tip is read, to tell a merge of the base.
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
    from both only inside the blocks and lists. A conflict that is not in a
    file's text — a file changed on one side and removed on the other, say —
    is a change outside them.
  - *Any other commit* contributes its own diff against its first parent: a
    merge of anything but the base included.
- **Inside the blocks and lists.** A file that differs lies inside the
  `revalidated` blocks and `revisited` lists only when it is an artefact's
  file at that commit, by discovery's walk of its places — not a held
  document — on both sides a regular file of one mode, UTF-8 text in one line
  break, with front matter that parses, and the two texts are the same once
  every artefact's `revalidated` and `revisited` keys are taken out of each.
  In block style a key's lines are taken out, so a block or a list added
  whole lies inside. In flow style its characters are replaced by a marker,
  one for each key, so there a block or a list added lies outside. A block or
  a list removed, or emptied, lies outside in either style, since it drops
  its answers. So does a block turned to a value that is no mapping, or a
  list turned to one that is no list. An entry written, rewritten or
  removed within a list lies inside it, as a deferral does within a block.
  Front matter with a YAML anchor lies outside, since through it the text
  of a block or a list could change what an alias repeats outside it. A
  block or a list is found under the keys discovery reads it by, each
  rendered as text (`key_span`). Where two keys on its path are read
  alike, as `1` and `"1"` are, the text taken out could be the entry's
  discovery drops, so the file lies outside. So it does where a mapping on
  the path holds a merge key, `<<` or one tagged `!!merge`, through which
  keys written elsewhere are read as the mapping's own. Anything else is a
  change outside, with why.
- **It cannot answer** — and says why, exit 1 — in a shallow clone, where the
  history between the commits may not be here, when a name is no commit or
  the base does not resolve, when an object cannot be read, as in a partial
  clone, and when git lacks `merge-tree --write-tree` (2.38) or, for a
  conflicted merge, its `-X` option.
"""

from __future__ import annotations

import io
import json
import re
from collections.abc import Iterable, Mapping, Sequence, Sized
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import MappingNode, Node, SequenceNode

from project_kit import cli_render, default_branch
from project_kit.document_parts import split_front_matter
from project_kit.friction_check import printable  # the friction group's one escape of a human view
from project_kit.friction_discovery import (
    DiscoveredFile,
    Discovery,
    discover_artefacts,
)
from project_kit.friction_git import (
    SHORT,
    BlobReader,
    CommitTree,
    FrictionCheckError,
    commit_of,
    run_git,
)
from project_kit.friction_resolve import read_version
from project_kit.line_breaks import line_break, universal_newlines
from project_kit.working_tree import nul_separated

#: The version of the document `render_json` returns, under the rule every reading
#: document of the `friction` group follows: raised when a key a reader relies on
#: changes its meaning or goes, never for a key added. Which keys `all_inside` counts
#: — `revalidated` and `revisited` — is part of its meaning, since a reader gates on it:
#: counting another raises it.
SINCE_SCHEMA_VERSION = 1

# What a file's mode is, as a tree writes it, when its text can be compared.
_FILE_MODES = frozenset({"100644", "100755"})
# The mode a raw diff gives a side that holds no file.
_ABSENT = "000000"
# What a block, or a `revisited` list, written in flow style is replaced by, in both
# texts compared: a marker for each key, so that one never stands in for the other.
_MARKER = "\0revalidated\0"
_LIST_MARKER = "\0revisited\0"
# `git merge-tree` exits 0 for a clean merge and 1 for one with conflicts.
_MERGED = (0, 1)
# A name that reads as a commit's id, in full or abbreviated.
_HEX = re.compile(r"[0-9a-fA-F]{7,40}")


@dataclass(frozen=True)
class Outside:
    """A change outside `revalidated` blocks and `revisited` lists: the
    file, the commit that made it, and why it lies outside. `path` is `None` for a merge
    of the base whose conflict git names no file of."""

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

    `reason` says why no change can be set inside the blocks and lists as a whole — the head
    does not descend from `since`, say — and is `None` otherwise. `inside` holds the
    files whose changes lie only inside `revalidated` blocks and `revisited` lists,
    `outside` each change that does not. What a reader makes of the answer — whether
    an authorisation for `since` covers `head`, say — is the reader's."""

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
        """Every change since, apart from merges of the base, lies inside `revalidated`
        blocks and `revisited` lists."""
        return self.reason is None and not self.outside


@dataclass
class _Reading:
    """What one run reads more than once: blobs, through one process, and each commit's
    discovery."""

    root: Path
    blobs: BlobReader
    discoveries: dict[str, Discovery] = field(default_factory=dict[str, Discovery])

    def discovery(self, commit: str) -> Discovery:
        """Discovery's walk of the places at `commit`, read once."""
        if commit not in self.discoveries:
            tree = CommitTree(self.root, commit)
            self.discoveries[commit] = discover_artefacts(self.root, tree=tree)
        return self.discoveries[commit]


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
    reading = _Reading(target_root, BlobReader(target_root))
    steps: list[Step] = []
    inside: set[str] = set()
    outside: list[Outside] = []
    try:
        for commit, parents in reversed(line):
            merges_base = len(parents) == 2 and _is_ancestor(target_root, parents[1], base.tip)
            steps.append(Step(commit, merges_base))
            judged: Sequence[tuple[str | None, str | None]] = (
                _merge_of_base(reading, commit, parents[0], parents[1])
                if merges_base
                else _against(reading, commit, (parents[0],))
            )
            for path, why in judged:
                if why is not None:
                    outside.append(Outside(path, commit, why))
                elif path is not None:
                    inside.add(path)
    finally:
        reading.blobs.close()
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


# --- one commit ----------------------------------------------------------------------


def _merge_of_base(
    reading: _Reading, commit: str, first: str, second: str
) -> Sequence[tuple[str | None, str | None]]:
    """A merge of the base, held against git's clean merge of its parents — or, where
    that merge conflicts, against git's merge taking each side of every conflict."""
    clean, written = _merge_tree(reading.root, first, second)
    if clean:
        return _against(reading, commit, (_tree_of(written),))
    sides: list[str] = []
    for side in ("ours", "theirs"):
        clean, written = _merge_tree(reading.root, first, second, "-X", side)
        if not clean:
            why = (
                "the merge of the base conflicts on it outside its text, as where one side "
                "changed a file the other removed or renamed"
            )
            named: list[str | None] = [*_conflicted(written)] or [None]
            return [(path, why) for path in named]
        sides.append(_tree_of(written))
    return _against(reading, commit, tuple(sides))


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
    reading: _Reading, commit: str, expected: Sequence[str]
) -> list[tuple[str, str | None]]:
    """Each file `commit` holds otherwise than a tree-ish of `expected`, with why it lies
    outside the blocks and lists, or `None` where it lies inside them against each."""
    diffs = [dict(_raw_diff(reading.root, tree, commit)) for tree in expected]
    paths: set[str] = set()
    for diff in diffs:
        paths.update(diff)
    judged: list[tuple[str, str | None]] = []
    for path in sorted(paths):
        whys = (_judge(reading, commit, path, *diff[path]) for diff in diffs if path in diff)
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


class _Unreadable(Exception):
    """A text whose `revalidated` blocks and `revisited` lists cannot be told, and why."""


def _judge(reading: _Reading, commit: str, path: str, before: _Entry, after: _Entry) -> str | None:
    """Why the file at `path` lies outside `revalidated` blocks and `revisited` lists
    between `before` and the commit's `after`, or `None` where every difference lies
    inside them."""
    (mode_b, obj_b), (mode_a, obj_a) = before, after
    if mode_b == _ABSENT:
        return "added"
    if mode_a == _ABSENT:
        return "removed"
    if mode_b != mode_a:
        return f"its mode changed ({mode_b} to {mode_a})"
    if mode_a not in _FILE_MODES:
        return "not a regular file"
    discovery = reading.discovery(commit)
    if discovery.holding(path) is not None:
        return "a held document, not an artefact's file"
    found = next((file for file in discovery.files if file.path == path), None)
    if found is None:
        return "not an artefact's file: no declared place holds it"
    texts: list[str] = []
    for obj in (obj_b, obj_a):
        blob = reading.blobs.read_object(obj)
        if blob is None:
            # Never read as an empty file: a partial clone that could not fetch the
            # object would otherwise compare two empty texts as equal.
            raise FrictionCheckError(
                f"{path}: object {obj[:SHORT]} could not be read from this repository; fetch "
                f"it, or run from a full clone, and run again."
            )
        try:
            texts.append(blob.decode("utf-8"))
        except UnicodeDecodeError:
            return "not UTF-8 text"
    breaks = {line_break(text) for text in texts}
    if None in breaks:
        return "it mixes line endings"
    if len(breaks) > 1:
        return "its line endings changed"
    try:
        (one, had, held), (other, has, holds) = (
            _without_blocks(path, found, universal_newlines(text)) for text in texts
        )
    except _Unreadable as exc:
        return str(exc)
    if had - has:
        return "a `revalidated` block was removed from it, which drops an answer"
    if held - holds:
        return "a `revisited` list was removed from it, which drops its answers"
    if one == other:
        return None
    return "it changed outside its `revalidated` blocks and `revisited` lists"


def _without_blocks(
    path: str, found: DiscoveredFile, text: str
) -> tuple[str, frozenset[str], frozenset[str]]:
    """`text` with every artefact's `revalidated` and `revisited` keys taken out — in
    block style their lines, in flow style their characters, each replaced by its key's
    marker — with the locations of the artefacts that carry a block, and of those that
    carry a list. `_Unreadable` where the blocks and lists cannot be told apart from the
    rest: front matter that does not parse, a block or list whose keys cannot be told
    as discovery reads them (`key_span`), or front matter with a YAML anchor, through
    which their text could change what lies outside them."""
    version = read_version(path, found, text)
    if isinstance(version, str):
        raise _Unreadable(version)
    if _anchored(text):
        raise _Unreadable(
            "its front matter uses a YAML anchor, through which text inside a "
            "`revalidated` block or a `revisited` list can change what lies outside it"
        )
    # A block emptied — `revalidated:` with no value, `{}` or `null` — drops its answer
    # as a block removed does, so it carries none, and so does one that is no mapping.
    # So it is with a `revisited` list, whose entries are its answers (COR-050 point 16):
    # one emptied, or no list, carries none. An entry removed from a list, as a deferral
    # removed from a block, is a change inside it.
    carriers = frozenset(
        version.artefacts[key].location
        for key, stamp in version.stamps.items()
        if _holds(stamp.value, Mapping)
    )
    lists = frozenset(
        version.artefacts[key].location
        for key, stamp in version.revisits.items()
        if _holds(stamp.value, list)
    )
    spans = [
        *((stamp, _MARKER) for stamp in version.stamps.values()),
        *((stamp, _LIST_MARKER) for stamp in version.revisits.values()),
    ]
    for stamp, marker in sorted(spans, key=lambda item: -item[0].start):
        start = text.rfind("\n", 0, stamp.start) + 1
        if stamp.flow or text[start : stamp.start].strip():
            text = text[: stamp.start] + marker + text[stamp.end :]
            continue
        newline = text.find("\n", max(stamp.end - 1, stamp.start))
        stop = len(text) if newline == -1 else newline + 1
        text = text[:start] + text[stop:]
    return text, carriers, lists


def _holds(value: object, form: type) -> bool:
    """Whether a block's or a list's `value` is of its `form` — a mapping, a list — and
    holds something: else it carries no answer."""
    return isinstance(value, form) and len(cast("Sized", value)) > 0


def _anchored(text: str) -> bool:
    """Whether the front matter of `text` gives any node a YAML anchor — the only way
    an alias, or a merge key naming one, can repeat a value elsewhere. A merge key with
    its value written in place repeats nothing, and one on the path to a block or a
    list is refused where the block or list is found (`key_span`)."""
    front_matter, _body = split_front_matter(text)
    if front_matter is None:
        return False
    composer: Any = YAML()  # ruamel's composer is untyped
    try:
        root: Node | None = composer.compose(io.StringIO(front_matter))
    except YAMLError:
        return True
    stack: list[Node] = [] if root is None else [root]
    seen: set[int] = set()
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if getattr(node, "anchor", None) is not None:
            return True
        held: Any = getattr(node, "value", None)
        if isinstance(node, MappingNode):
            pairs = cast("list[tuple[Node, Node]]", held)
            stack.extend(part for pair in pairs for part in pair)
        elif isinstance(node, SequenceNode):
            stack.extend(cast("list[Node]", held))
    return False


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
    """Whether every change since lies inside `revalidated` blocks and `revisited` lists,
    and each that does not.
    A path, a reason and a parser's message quoting a file are the author's words, so each
    is printed escaped, as the change check's human view prints them (`printable`)."""
    since, head = found.since[:SHORT], found.head[:SHORT]
    base = printable(found.base_ref)
    title = cli_render.style("title", "Friction since")
    lines = [f"{title} — {since} to {head}, apart from merges of {base}", ""]
    if found.reason is not None:
        lines.append(f"  Not all inside the blocks and lists: {printable(found.reason)}.")
    elif not found.steps:
        lines.append("  Nothing changed: the two commits are one.")
    else:
        merges = sum(1 for step in found.steps if step.merges_base)
        lines.append(f"  {len(found.steps)} commit(s), {merges} of them merging {base}.")
        for path in found.inside:
            lines.append(
                f"  {printable(path)} — changed only inside `revalidated` blocks and "
                f"`revisited` lists"
            )
        for change in found.outside:
            where = printable(change.path) if change.path else "(the merge)"
            why = printable(change.why)
            lines.append(f"  {where} — outside, in {change.commit[:SHORT]}: {why}")
        lines.append("")
        lines.append(
            "  Every change lies inside `revalidated` blocks and `revisited` lists."
            if found.all_inside
            else "  Not all inside the blocks and lists: a change lies outside them."
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
