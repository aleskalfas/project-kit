"""The friction change check: `pkit friction check` (COR-050 points 5, 6, 7, 11, 12).

Every artefact with an anchor that changed in a pull request must carry one
of three answers in the same pull request (COR-050 point 5): **updated** (its
content changed and its `at` changed), **unchanged** (only `at` changed, with
`outcome: unchanged` and an `unchanged-because` that changed too), or
**deferred** (a deferral for that anchor, by kind and value, was introduced).
An artefact new in the diff counts as revalidated. A change to the artefact's
own anchor list, or a move, needs a revalidation as well. Anything else is
*friction*. The check reads the artefacts, never a pull-request description,
so it works for any tool and locally before a commit.

**Reading the repository — from git alone, never checking anything out.**

- *Head* is the working tree as git sees it: tracked files plus untracked
  ones git does not ignore (`WorkingTree`) — the one listing validation reads
  too (`working_tree`, ADR-057 point 2), so both find the same artefacts in
  the same working tree. *The base* is the merge-base of the base reference
  — the one named, else `$PKIT_CHECK_BASE`, else the default branch, as
  `default_branch` resolves it for every reader (COR-054) — and HEAD, read
  from git objects (`CommitTree`: `git ls-tree`, then `git cat-file
  --batch`, the batch form of `git show <rev>:<path>`).
- *The diff* is `git diff -M --name-status <merge-base>` against the working
  tree, plus untracked files as added — so uncommitted work is part of it, and
  the result says how many paths that was.
- Both sides are discovered through `friction_discovery`'s repository-tree
  seam, each with its own settings, so a place added or removed in the diff
  counts: an artefact appearing in the places is new, one leaving them is
  removed and turns its dependants' anchors dead (COR-050 point 6).

**When an anchor changed** (point 5): a *path* anchor when a changed path
matches it (excluded paths and the artefact's own file ignored); a *record*
anchor when the record's file changed (a pure rename keeps its content); an
*artefact* anchor when the target's **content** changed — its body compared
textually and its own fields compared parsed, never the methodology's
container. The cascade follows: a dependant sees a change only where its
target's content changed, so an `unchanged` revalidation stops it.

**What it reports** (points 7, 11, 12): friction; answers; a bump with
nothing behind it (`at` changed, but no answer stands); dead anchors *of the
pull request* (resolving to nothing at head, and either added in the diff or
with a target the diff removed or moved — dead anchors that were already dead
are the whole-repository check's); an anchor kind no installed component
resolves, separately; an outdated base; front matter that does not parse.
Findings run upstream first along artefact anchors (truth-chain order).

**Modes** (point 12): `warning` reports and exits 0; `enforcing` exits 1 on
friction, dead anchors, unresolved kinds and bumps. An outdated base never
fails. Dormant — counts only, exit 0 — when no place is declared or nothing in
the places carries the container (point 15).

**Resolver limits** (point 2; ADR-057). Capability-registered anchor kinds are
looked up in `registered_anchor_kinds`, where a resolver command that does not
declare the query contract — bounded, deterministic, read-only, needing no
network — is refused (`refuse_resolver_without_query_contract`). No capability
registers a kind yet, so every other kind is unresolved. The residual gap: the
declaration is trusted, not enforced — no layer of this distribution holds a
single command to "no network" (ADR-057 point 4).

The check writes nothing (point 13).
"""

from __future__ import annotations

import heapq
import json
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from fnmatch import fnmatchcase
from functools import cached_property
from pathlib import Path, PurePosixPath
from typing import Any, cast

import click

from project_kit import cli_render, default_branch, refs
from project_kit.backbone_schemas import CONTAINER_KEY
from project_kit.friction_discovery import (
    CORE_ANCHOR_KINDS,  # noqa: F401 — re-exported: the check's public surface
    Anchor,
    Artefact,
    ArtefactKind,
    Discovery,
    FrictionSettings,
    RepositoryTree,
    ResolverCommand,
    discover_artefacts,
    pattern_matcher,
    refuse_resolver_without_query_contract,  # noqa: F401 — re-exported, as above
    registered_anchor_kinds,
    unresolved_kind_reason,
)
from project_kit.working_tree import (
    WorkingTree,  # re-exported: the head side's tree, now the one listing's home
    nul_separated,
)

#: The environment variable that names the base when no reference is given; with
#: neither, the base is the default branch (COR-054 point 3, `default_branch`).
BASE_ENV = default_branch.CHECK_BASE_ENV

#: The mode in which the change check fails (COR-050 point 12).
ENFORCING = "enforcing"

# A capability decision named as a record anchor: `<capability>:DEC-NNN`, with
# or without its slug (the citation form of COR-017).
_CAPABILITY_RECORD = re.compile(r"^([a-z][a-z0-9-]*[a-z0-9]):(DEC-\d+)((?:-[a-z0-9]+)*)$")

# A pure rename keeps a file's content: git's similarity score for it.
_IDENTICAL = 100

# How many characters of a commit the human output shows.
SHORT = 12

# The mode of a link in a git tree.
_LINK_MODE = "120000"


# --- findings ----------------------------------------------------------------


class FindingKind(Enum):
    """What a finding is. The values are the `kind` field of the JSON output."""

    FRICTION = "friction"
    ANSWERED = "answered"
    REVALIDATED = "revalidated"
    BUMP = "bump"
    DEAD_ANCHOR = "dead-anchor"
    UNRESOLVED_KIND = "unresolved-kind"
    OUTDATED_BASE = "outdated-base"
    UNREADABLE = "unreadable"


#: The findings enforcing mode fails on (COR-050 point 12). An unresolved kind
#: is a dead anchor whose kind nothing resolves, reported separately.
FAILING_KINDS = frozenset(
    {
        FindingKind.FRICTION,
        FindingKind.BUMP,
        FindingKind.DEAD_ANCHOR,
        FindingKind.UNRESOLVED_KIND,
    }
)


class Answer(Enum):
    """How an artefact answers a change (COR-050 point 5); `new` counts as revalidated."""

    UPDATED = "updated"
    UNCHANGED = "unchanged"
    DEFERRED = "deferred"
    NEW = "new"


@dataclass(frozen=True)
class Finding:
    """One finding: about an artefact (`artefact`, `location`), or about the run."""

    kind: FindingKind
    message: str
    artefact: str | None = None  # the artefact's id
    location: str | None = None  # `path`, or `path#id` for a collection entry
    anchor: Anchor | None = None
    answer: Answer | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "artefact": self.artefact,
            "location": self.location,
            "kind": self.kind.value,
            "anchor": (
                None
                if self.anchor is None
                else {"kind": self.anchor.kind, "value": self.anchor.value}
            ),
            "answer": None if self.answer is None else self.answer.value,
            "message": self.message,
        }


@dataclass(frozen=True)
class BaseState:
    """What the diff was taken against."""

    ref: str  # the base reference as given
    tip: str  # the commit it names
    commit: str  # the merge-base of the tip and HEAD: what was compared
    outdated: bool  # the tip is not an ancestor of HEAD: the base moved on


@dataclass(frozen=True)
class HeadState:
    commit: str  # HEAD
    uncommitted: int  # paths the working tree changes beyond HEAD, untracked included


@dataclass(frozen=True)
class ChangeCheck:
    """The outcome of one run of the change check."""

    mode: str  # the mode in effect
    mode_as_written: Any  # `friction.mode` as written, `None` when absent
    dormant: bool
    places: int
    artefacts: int
    carrying: int  # artefacts carrying the container
    base: BaseState | None  # `None` only for a dormant run whose base did not resolve
    head: HeadState | None
    findings: tuple[Finding, ...]

    def count(self, kind: FindingKind) -> int:
        return sum(1 for f in self.findings if f.kind is kind)

    @property
    def failing(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.kind in FAILING_KINDS)

    @property
    def failed(self) -> bool:
        return not self.dormant and self.mode == ENFORCING and bool(self.failing)

    @property
    def exit_code(self) -> int:
        return 1 if self.failed else 0


class FrictionCheckError(click.ClickException):
    """The check could not run: no git repository, no commit, a base that does not resolve."""


# --- git ----------------------------------------------------------------------


def run_git(
    root: Path, *args: str, stdin: bytes | None = None, accept: tuple[int, ...] = (0,)
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, input=stdin, capture_output=True, check=False
        )
    except OSError as exc:
        raise FrictionCheckError(f"cannot run git: {exc}") from exc
    if completed.returncode not in accept:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise FrictionCheckError(
            f"`git {args[0]}` failed: {detail or f'exit status {completed.returncode}'}"
        )
    return completed


def commit_of(root: Path, name: str) -> str | None:
    """The commit `name` resolves to, or None."""
    completed = run_git(
        root, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}", accept=(0, 1)
    )
    commit = completed.stdout.decode().strip()
    return commit if completed.returncode == 0 and commit else None


class CommitTree:
    """The files of one commit, read from git objects; nothing is checked out."""

    def __init__(self, root: Path, commit: str) -> None:
        self._root = root
        listed = run_git(root, "ls-tree", "-r", "-z", commit).stdout
        self._blobs: dict[str, tuple[str, str]] = {}  # path -> (mode, object)
        for record in listed.split(b"\0"):
            if not record:
                continue
            meta, _, path = record.partition(b"\t")
            mode, kind, obj = meta.decode().split(" ")
            if kind == "blob":  # a submodule is a commit, not a file of this tree
                self._blobs[path.decode("utf-8", "surrogateescape")] = (mode, obj)
        self._files = tuple(sorted(self._blobs))

    def files(self) -> Sequence[str]:
        return self._files

    def read_bytes(self, paths: Sequence[str]) -> Mapping[str, bytes | None]:
        contents: dict[str, bytes | None] = dict.fromkeys(paths)
        wanted = [
            (rel, self._blobs[rel][1])
            for rel in dict.fromkeys(paths)
            if rel in self._blobs and self._blobs[rel][0] != _LINK_MODE
        ]
        if not wanted:
            return contents
        batch = "".join(f"{obj}\n" for _rel, obj in wanted).encode()
        out = run_git(self._root, "cat-file", "--batch", stdin=batch).stdout
        offset = 0
        for rel, _obj in wanted:
            header_end = out.index(b"\n", offset)
            header = out[offset:header_end].split(b" ")
            if len(header) != 3:  # `<object> missing`: nothing to read
                offset = header_end + 1
                continue
            start = header_end + 1
            size = int(header[2])
            contents[rel] = out[start : start + size]
            offset = start + size + 1
        return contents


def head_commit(root: Path) -> str:
    """HEAD's commit; refuses before the first commit, when there is nothing to compare."""
    head = commit_of(root, "HEAD")
    if head is None:
        raise FrictionCheckError(
            "HEAD names no commit yet; the change check compares a branch with its base, "
            "so commit first."
        )
    return head


def resolve_base(root: Path, ref: str | None = None) -> BaseState:
    """The base's commit, its merge-base with HEAD, and whether it moved on: `ref`, else
    `$PKIT_CHECK_BASE`, else the default branch — computed once for every reader
    (`default_branch.base`, COR-054 point 5)."""
    head_commit(root)
    found = default_branch.base(root, ref)
    if found.problem is not None or found.tip is None or found.fork is None:
        raise FrictionCheckError(found.problem or f"the base {found.ref!r} cannot be compared.")
    return BaseState(ref=found.ref, tip=found.tip, commit=found.fork, outdated=bool(found.outdated))


@dataclass(frozen=True)
class DiffEntry:
    """One path the diff changes; `old_path` and `score` for a rename."""

    status: str  # git's status letter: A, M, D, R, T, U
    path: str  # the path at head; for a deletion, the removed path
    old_path: str | None = None
    score: int | None = None

    @property
    def changes_content(self) -> bool:
        return not (self.status == "R" and self.score == _IDENTICAL)


@dataclass(frozen=True)
class Diff:
    """The paths changed between the base and the working tree."""

    entries: tuple[DiffEntry, ...]
    uncommitted: int

    @cached_property
    def paths(self) -> frozenset[str]:
        """Every path the diff names, on either side of a rename."""
        named = {e.path for e in self.entries}
        named.update(e.old_path for e in self.entries if e.old_path is not None)
        return frozenset(named)

    @cached_property
    def renamed_from(self) -> dict[str, str]:
        return {e.path: e.old_path for e in self.entries if e.old_path is not None}

    @cached_property
    def by_path(self) -> dict[str, DiffEntry]:
        return {e.path: e for e in self.entries}


def read_diff(root: Path, base_commit: str) -> Diff:
    """`git diff -M --name-status` from the base to the working tree, untracked files added."""
    raw = run_git(
        root, "diff", "-M", "--name-status", "-z", "--no-color", "--relative", base_commit, "--"
    ).stdout
    entries = parse_name_status(nul_separated(raw))
    untracked = _untracked(root)
    known = {e.path for e in entries}
    entries.extend(DiffEntry("A", rel) for rel in untracked if rel not in known)
    return Diff(
        entries=tuple(sorted(entries, key=lambda e: (e.path, e.status))),
        uncommitted=uncommitted_paths(root),
    )


def parse_name_status(tokens: Sequence[str]) -> list[DiffEntry]:
    """The entries of a NUL-separated `--name-status` listing, as `git diff` and `git log` print it.

    A rename or copy is three tokens (`R<score>`, old, new); anything else two
    (status, path). A copy adds its new path and leaves the source alone.
    """
    entries: list[DiffEntry] = []
    index = 0
    while index < len(tokens):
        code = tokens[index]
        letter = code[:1]
        if letter in ("R", "C"):
            old, new = tokens[index + 1], tokens[index + 2]
            index += 3
            if letter == "R":
                score = int(code[1:]) if code[1:].isdigit() else None
                entries.append(DiffEntry("R", new, old, score))
            else:
                entries.append(DiffEntry("A", new))
            continue
        entries.append(DiffEntry(letter, tokens[index + 1]))
        index += 2
    return entries


def _untracked(root: Path) -> list[str]:
    return nul_separated(run_git(root, "ls-files", "-z", "--others", "--exclude-standard").stdout)


def uncommitted_paths(root: Path) -> int:
    """How many paths the working tree changes beyond HEAD, untracked ones included."""
    beyond_head = nul_separated(
        run_git(root, "diff", "--name-only", "-z", "--no-color", "--relative", "HEAD", "--").stdout
    )
    return len(set(beyond_head) | set(_untracked(root)))


# --- anchor kinds and their resolvers ----------------------------------------


# --- one side of the diff -----------------------------------------------------


# How a dead record or artefact anchor resolves to nothing; a path anchor's is `Side.why_dead`.
_RESOLVES_NOTHING = {
    "record": "names no record",
    "artefact": "names no artefact in the declared places",
}


class Side:
    """One state of the repository as the check reads it: its files and its artefacts."""

    def __init__(self, root: Path, tree: RepositoryTree, discovery: Discovery) -> None:
        self.root = root
        self.discovery = discovery
        self.files = frozenset(tree.files())

    @property
    def settings(self) -> FrictionSettings:
        return self.discovery.settings

    def excluded(self, path: str) -> bool:
        """Whether `friction.exclude` leaves `path` out: discovery's one decision of it."""
        return self.settings.excluded(path)

    def find(self, reference: str) -> Artefact | None:
        return self.discovery.find(reference)

    def stands_on(self, pattern: str) -> Callable[[str], bool]:
        """Whether a path anchor's `pattern` stands on a file: it matches it, and this
        state's `friction.exclude` does not leave it out (COR-050 points 2 and 7).

        The one rule both checks match a path pattern by: whether an anchor
        resolves, whether a changed path changed it, what it matched in
        history, how broad it is, and which paths of the declared surface
        it anchors — the surface's own patterns are read by it too (point 8).
        """
        match = pattern_matcher(pattern)
        return lambda rel: match(rel) and not self.excluded(rel)

    def matching(self, pattern: str, files: Iterable[str] | None = None) -> tuple[str, ...]:
        """The files a path anchor's `pattern` stands on (`stands_on`), sorted.

        This state's files by default; with `files`, another listing — a
        commit's, or every path a history touched — read under this state's
        exclusions, as the whole-repository check reads history under HEAD's.
        """
        listing = self.files if files is None else files
        return tuple(sorted(filter(self.stands_on(pattern), listing)))

    def left_out(self, pattern: str) -> tuple[str, ...]:
        """The files here a path anchor's `pattern` matches but does not stand on,
        because `friction.exclude` leaves them out (COR-050 point 7), sorted."""
        match = pattern_matcher(pattern)
        return tuple(sorted(rel for rel in self.files if match(rel) and self.excluded(rel)))

    def resolves(self, anchor: Anchor) -> bool:
        """Whether an anchor of a core kind resolves to something here (COR-050 point 7)."""
        if anchor.kind == "path":
            return any(map(self.stands_on(anchor.value), self.files))
        if anchor.kind == "record":
            return self.record_path(anchor.value) is not None
        return self.find(anchor.value) is not None

    def why_dead(self, anchor: Anchor) -> str:
        """How an anchor of a core kind that does not resolve here resolves to nothing.

        A path anchor says which way it is dead (COR-050 point 7): it matches
        no file, or only files `friction.exclude` leaves out — a typo and a
        glob over excluded code read apart.
        """
        if anchor.kind == "path":
            excluded = len(self.left_out(anchor.value))
            return f"matches only excluded files ({excluded})" if excluded else "matches no file"
        return _RESOLVES_NOTHING[anchor.kind]

    def record_path(self, value: str) -> str | None:
        """The file a record anchor names here, through the record resolver, or None."""
        if refs.RECORD_RE.match(value):
            found = refs.resolve_record(self.root, value, files=self.files)
            return None if found is None else found.relative_to(self.root).as_posix()
        match = _CAPABILITY_RECORD.match(value)
        if match is None:
            return None
        capability, number, slug = match.groups()
        directory = f".pkit/capabilities/{capability}/decisions"
        if slug:
            rel = f"{directory}/{number}{slug}.md"
            return rel if rel in self.files else None
        candidates = sorted(
            rel
            for rel in self.files
            if PurePosixPath(rel).parent.as_posix() == directory
            and (
                PurePosixPath(rel).name == f"{number}.md"
                or fnmatchcase(PurePosixPath(rel).name, f"{number}-*.md")
            )
        )
        return candidates[0] if candidates else None


# --- matching an artefact with its base -----------------------------------------


def _key(artefact: Artefact, path: str | None = None) -> tuple[str, str | None]:
    entry = artefact.id if artefact.kind is ArtefactKind.ENTRY else None
    return (artefact.path if path is None else path, entry)


def _has_own_id(artefact: Artefact) -> bool:
    """An entry's key, or a document's own `id` field — an identity that survives a move."""
    if artefact.kind is ArtefactKind.ENTRY:
        return True
    own = artefact.carrier.get("id")
    return isinstance(own, str) and bool(own)


def _counterparts(head: Side, base: Side, diff: Diff) -> dict[int, Artefact]:
    """Each head artefact's base counterpart, by the head artefact's walk index.

    By location first, following the diff's renames; then, for an artefact
    with an identity of its own, by that identity among base artefacts whose
    location is gone at head — a move git did not detect as a rename, or an
    entry moved between collection files. What finds none is new.
    """
    base_by_key: dict[tuple[str, str | None], Artefact] = {}
    for artefact in base.discovery.artefacts:
        base_by_key.setdefault(_key(artefact), artefact)
    matched: dict[int, Artefact] = {}
    claimed: set[int] = set()
    head_artefacts = head.discovery.artefacts
    for index, artefact in enumerate(head_artefacts):
        before = base_by_key.get(_key(artefact, diff.renamed_from.get(artefact.path)))
        if before is not None and id(before) not in claimed:
            matched[index] = before
            claimed.add(id(before))
    head_keys = {_key(a) for a in head_artefacts}
    for index, artefact in enumerate(head_artefacts):
        if index in matched or not _has_own_id(artefact):
            continue
        candidates = [
            b
            for b in base.discovery.artefacts
            if id(b) not in claimed
            and b.kind is artefact.kind
            and b.id == artefact.id
            and _key(b) not in head_keys
        ]
        if len(candidates) == 1:
            matched[index] = candidates[0]
            claimed.add(id(candidates[0]))
    return matched


# --- what the diff says about one artefact ------------------------------------


def content(artefact: Artefact) -> tuple[str, dict[str, Any]]:
    """An artefact's content (COR-050): its body text and its own fields, never the container."""
    own = {k: v for k, v in artefact.carrier.items() if k != CONTAINER_KEY}
    return artefact.body, own


def _revalidated_field(artefact: Artefact, key: str) -> Any:
    revalidated = artefact.revalidated
    return revalidated.get(key) if isinstance(revalidated, Mapping) else None


def parsed_at(artefact: Artefact) -> Any:
    """The parsed value of `at`: the instant, so a quoting or formatting change is no change."""
    value = _revalidated_field(artefact, "at")
    if not isinstance(value, str):
        return value
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return value.strip()
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else value.strip()


def _because(artefact: Artefact) -> str | None:
    """`unchanged-because` with its whitespace folded: a re-wrap is not a new justification."""
    value = _revalidated_field(artefact, "unchanged-because")
    return " ".join(value.split()) if isinstance(value, str) else None


def anchors_of(artefact: Artefact) -> list[Anchor]:
    return [Anchor(kind, value) for kind, values in artefact.anchors.items() for value in values]


def deferral_reason(artefact: Artefact, anchor: Anchor) -> str:
    """The reason written on the deferral of `anchor`, whitespace folded; `""` when none."""
    deferred: Any = _revalidated_field(artefact, "deferred")
    for deferral in artefact.deferrals:
        if deferral.anchor != anchor or not isinstance(deferred, list):
            continue
        entry = cast(list[Any], deferred)[deferral.index]
        if isinstance(entry, Mapping):
            reason = cast(Mapping[str, Any], entry).get("reason")
            if isinstance(reason, str):
                return " ".join(reason.split())
    return ""


@dataclass(frozen=True)
class _Revalidation:
    """A change of `at` in the diff: the answer it gives, or why it gives none."""

    answer: Answer | None
    bump: str | None = None


def _revalidation(artefact: Artefact, before: Artefact) -> _Revalidation | None:
    """What a change of the parsed `at` answers (COR-050 point 5); `None` when `at` held."""
    at = parsed_at(artefact)
    if at is None or at == parsed_at(before):
        return None
    outcome = _revalidated_field(artefact, "outcome")
    changed = content(artefact) != content(before)
    if outcome == Answer.UPDATED.value:
        if changed:
            return _Revalidation(Answer.UPDATED)
        return _Revalidation(
            None, "`at` changed with `outcome: updated`, but the content did not change"
        )
    if outcome == Answer.UNCHANGED.value:
        if changed:
            return _Revalidation(
                None, "`at` changed with `outcome: unchanged`, but the content changed"
            )
        if _because(artefact) == _because(before):
            return _Revalidation(
                None,
                "`at` changed with `outcome: unchanged`, but `unchanged-because` is the same "
                "as before — say why the content holds against this change",
            )
        return _Revalidation(Answer.UNCHANGED)
    return _Revalidation(None, "`at` changed without an `outcome` of `updated` or `unchanged`")


def _answer_text(answer: Answer, artefact: Artefact, anchor: Anchor | None = None) -> str:
    if answer is Answer.UNCHANGED:
        return f"unchanged — {_because(artefact)}"
    if answer is Answer.DEFERRED and anchor is not None:
        reason = deferral_reason(artefact, anchor)
        return f"deferred — {reason}" if reason else "deferred"
    return answer.value


def _anchor_changed(
    anchor: Anchor, own: frozenset[str], head: Side, base: Side, diff: Diff
) -> bool:
    """Whether a live anchor of a core kind changed in the diff (COR-050 point 5)."""
    if anchor.kind == "path":
        return any(map(head.stands_on(anchor.value), diff.paths - own))
    if anchor.kind == "record":
        rel = head.record_path(anchor.value)
        entry = diff.by_path.get(rel) if rel is not None else None
        return entry is not None and entry.changes_content
    target = head.find(anchor.value)
    before = base.find(anchor.value)
    return target is not None and (before is None or content(target) != content(before))


@dataclass(frozen=True)
class _Question:
    """Something in the diff the artefact must answer."""

    subject: str  # how the finding's message opens
    anchor: Anchor | None = None  # a changed anchor; None for the anchor list or a move


def _judge(
    artefact: Artefact,
    before: Artefact | None,
    head: Side,
    base: Side,
    diff: Diff,
    registry: Mapping[str, ResolverCommand],
) -> list[Finding]:
    """The findings about one head artefact carrying the `friction` block."""

    def finding(
        kind: FindingKind, message: str, anchor: Anchor | None = None, answer: Answer | None = None
    ) -> Finding:
        return Finding(kind, message, artefact.id, artefact.location, anchor, answer)

    base_anchors = frozenset(anchors_of(before)) if before is not None else frozenset[Anchor]()
    findings: list[Finding] = []
    live: list[Anchor] = []  # anchors kept from the base that resolve at head
    for anchor in anchors_of(artefact):
        added = anchor not in base_anchors
        problem = _anchor_problem(anchor, added, head, base, registry)
        if problem is None:
            if not added:
                live.append(anchor)
            continue
        kind, message = problem
        if message is not None:
            findings.append(finding(kind, message, anchor))

    if before is None:
        message = "new in this diff: counts as revalidated"
        if any(u.path == artefact.path for u in base.discovery.unreadable):
            message += " (its base version's front matter does not parse, so there is no before)"
        findings.append(finding(FindingKind.ANSWERED, message, None, Answer.NEW))
        return findings

    own = frozenset({artefact.path, before.path})
    questions = [
        _Question("changed in this diff", anchor)
        for anchor in live
        if _anchor_changed(anchor, own, head, base, diff)
    ]
    if frozenset(anchors_of(artefact)) != base_anchors:
        questions.append(_Question("its anchor list changed in this diff"))
    if before.location != artefact.location:
        questions.append(_Question(f"it moved here from {before.location} in this diff"))

    revalidation = _revalidation(artefact, before)
    standing = revalidation.answer if revalidation is not None else None
    introduced = {d.anchor for d in artefact.deferrals} - {d.anchor for d in before.deferrals}
    kept = {d.anchor for d in artefact.deferrals} & {d.anchor for d in before.deferrals}
    for question in questions:
        if standing is not None:
            answer = standing
        elif question.anchor is not None and question.anchor in introduced:
            answer = Answer.DEFERRED
        else:
            message = _friction_message(question, question.anchor in kept)
            findings.append(finding(FindingKind.FRICTION, message, question.anchor))
            continue
        message = f"{question.subject}; answered: {_answer_text(answer, artefact, question.anchor)}"
        findings.append(finding(FindingKind.ANSWERED, message, question.anchor, answer))
    if revalidation is not None and revalidation.bump is not None:
        findings.append(finding(FindingKind.BUMP, revalidation.bump))
    if standing is not None and not questions:
        message = f"revalidated with no changed anchor: {_answer_text(standing, artefact)}"
        findings.append(finding(FindingKind.REVALIDATED, message, None, standing))
    return findings


def _anchor_problem(
    anchor: Anchor,
    added: bool,
    head: Side,
    base: Side,
    registry: Mapping[str, ResolverCommand],
) -> tuple[FindingKind, str | None] | None:
    """`None` when the anchor resolves at head; otherwise its finding kind and message.

    The message is `None` when the problem is not the diff's: an anchor that
    was already dead at the base is the whole-repository check's, not this
    check's (COR-050 point 7). A kind nothing resolves is judged the same way.
    """
    reason = unresolved_kind_reason(anchor.kind, registry)
    if reason is not None:
        message = (
            f"nothing installed resolves this kind: {reason}; the anchor was added in this diff"
        )
        return FindingKind.UNRESOLVED_KIND, message if added else None
    if head.resolves(anchor):
        return None
    if added:
        return (
            FindingKind.DEAD_ANCHOR,
            f"{head.why_dead(anchor)}; the anchor was added in this diff",
        )
    if base.resolves(anchor):
        return (
            FindingKind.DEAD_ANCHOR,
            f"{head.why_dead(anchor)}; the diff removed or moved its target",
        )
    return FindingKind.DEAD_ANCHOR, None


def _friction_message(question: _Question, deferral_predates: bool) -> str:
    if question.anchor is None:
        return f"{question.subject}, which needs a revalidation (a new `at`) in the same change"
    if deferral_predates:
        return (
            f"{question.subject} and carries no answer: its deferral predates this diff, so it "
            f"covers only earlier changes — revalidate the artefact"
        )
    return f"{question.subject} and carries no answer: revalidate the artefact, or defer the anchor"


# --- order ---------------------------------------------------------------------


def truth_chain_order(discovery: Discovery) -> list[int]:
    """Artefact indices upstream first along artefact anchors (COR-050 point 11).

    A target comes before every artefact anchored to it; ties keep walk order.
    Members of a cycle — a validation error — and what hangs below them follow
    in walk order, so the order is total and stable either way.
    """
    artefacts = discovery.artefacts
    position = {id(a): i for i, a in enumerate(artefacts)}
    upstream: dict[int, set[int]] = {i: set() for i in range(len(artefacts))}
    downstream: dict[int, set[int]] = {i: set() for i in range(len(artefacts))}
    for index, artefact in enumerate(artefacts):
        for reference in artefact.anchors_of_kind("artefact"):
            target = discovery.find(reference)
            if target is not None and position[id(target)] != index:
                upstream[index].add(position[id(target)])
                downstream[position[id(target)]].add(index)
    waiting = {i: len(ups) for i, ups in upstream.items()}
    ready = [i for i, count in waiting.items() if count == 0]
    heapq.heapify(ready)
    order: list[int] = []
    while ready:
        index = heapq.heappop(ready)
        order.append(index)
        for child in downstream[index]:
            waiting[child] -= 1
            if waiting[child] == 0:
                heapq.heappush(ready, child)
    placed = set(order)
    order.extend(i for i in range(len(artefacts)) if i not in placed)
    return order


# --- the check ---------------------------------------------------------------------


def run_change_check(
    target_root: Path,
    base_ref: str | None = None,
    *,
    registry: Mapping[str, ResolverCommand] | None = None,
) -> ChangeCheck:
    """Run the change check of the working tree against the merge-base of `base_ref` —
    without one, `$PKIT_CHECK_BASE`, else the default branch (COR-054 point 3).

    Raises `FrictionCheckError` when it cannot run — outside a git repository,
    before the first commit, or with a base that does not resolve — except
    while dormant, where there is nothing to compare and a missing base is
    only left out of the report.
    """
    head_tree = WorkingTree(target_root)
    head_discovery = discover_artefacts(target_root, tree=head_tree)
    settings = head_discovery.settings
    counts = {
        "places": len(head_discovery.places),
        "artefacts": len(head_discovery.artefacts),
        "carrying": len(head_discovery.with_container),
    }
    if head_discovery.is_dormant:
        dormant_base, dormant_head = _dormant_context(target_root, base_ref)
        return ChangeCheck(
            mode=settings.mode_or_default,
            mode_as_written=settings.mode,
            dormant=True,
            base=dormant_base,
            head=dormant_head,
            findings=(),
            **counts,
        )

    base_state = resolve_base(target_root, base_ref)
    diff = read_diff(target_root, base_state.commit)
    base_tree = CommitTree(target_root, base_state.commit)
    head = Side(target_root, head_tree, head_discovery)
    base = Side(target_root, base_tree, discover_artefacts(target_root, tree=base_tree))
    registry = registered_anchor_kinds(target_root) if registry is None else registry

    findings: list[Finding] = []
    if base_state.outdated:
        findings.append(Finding(FindingKind.OUTDATED_BASE, _outdated_message(base_state)))
    counterparts = _counterparts(head, base, diff)
    for index in truth_chain_order(head_discovery):
        artefact = head_discovery.artefacts[index]
        if artefact.has_friction_block:
            findings.extend(_judge(artefact, counterparts.get(index), head, base, diff, registry))
    for unreadable in sorted(head_discovery.unreadable, key=lambda u: u.path):
        findings.append(
            Finding(
                FindingKind.UNREADABLE,
                f"front matter does not parse ({unreadable.reason}); its artefacts cannot be "
                f"checked — `pkit validate` fails on it",
                location=unreadable.path,
            )
        )
    return ChangeCheck(
        mode=settings.mode_or_default,
        mode_as_written=settings.mode,
        dormant=False,
        base=base_state,
        head=HeadState(head_commit(target_root), diff.uncommitted),
        findings=tuple(findings),
        **counts,
    )


def _dormant_context(root: Path, base_ref: str | None) -> tuple[BaseState | None, HeadState | None]:
    """What a dormant run can say about its base and head; it demands neither (point 15)."""
    try:
        base: BaseState | None = resolve_base(root, base_ref)
    except FrictionCheckError:
        base = None
    try:
        commit = commit_of(root, "HEAD")
        head = None if commit is None else HeadState(commit, uncommitted_paths(root))
    except FrictionCheckError:
        head = None
    return base, head


def _outdated_message(base: BaseState) -> str:
    return (
        f"the base {base.ref} is at {base.tip[:SHORT]}, which is not an ancestor of HEAD: it "
        f"moved on after this branch left it at {base.commit[:SHORT]}; results hold only "
        f"against an up-to-date base — merge or rebase onto {base.ref}, then run again"
    )


# --- output --------------------------------------------------------------------------

#: The version of the document `render_json` returns. A change a reader could break
#: against — a key removed, renamed or given another meaning — raises it; a key added
#: does not. A document without it comes from a backbone that predates it: version 1.
CHANGE_SCHEMA_VERSION = 1


def render_json(result: ChangeCheck) -> str:
    """The stable machine-readable document other components consume (COR-050 Implications)."""
    document = {
        "schema_version": CHANGE_SCHEMA_VERSION,
        "check": "change",
        "mode": result.mode,
        "dormant": result.dormant,
        "failed": result.failed,
        "base": (
            None
            if result.base is None
            else {
                "ref": result.base.ref,
                "tip": result.base.tip,
                "commit": result.base.commit,
                "outdated": result.base.outdated,
            }
        ),
        "head": (
            None
            if result.head is None
            else {"commit": result.head.commit, "uncommitted_paths": result.head.uncommitted}
        ),
        "counts": {
            "places": result.places,
            "artefacts": result.artefacts,
            "carrying": result.carrying,
            **{kind.value: result.count(kind) for kind in FindingKind},
        },
        "findings": [finding.as_json() for finding in result.findings],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


_LEGEND: dict[FindingKind, str] = {
    FindingKind.FRICTION: (
        "an anchor, the anchor list or the artefact's place changed, and no answer stands"
    ),
    FindingKind.ANSWERED: "the artefact answers the change: updated, unchanged, deferred or new",
    FindingKind.REVALIDATED: "revalidated in this diff with no changed anchor",
    FindingKind.BUMP: "`at` changed with nothing behind it",
    FindingKind.DEAD_ANCHOR: "the diff left an anchor resolving to nothing",
    FindingKind.UNRESOLVED_KIND: "an anchor kind no installed component resolves",
    FindingKind.UNREADABLE: "front matter the check cannot parse",
}

_MODE_GLOSS = {
    ENFORCING: "fails on friction, dead anchors, unresolved kinds and bumps; an outdated base only reports",
    "warning": "reports and passes",
}


def render_human(result: ChangeCheck) -> str:
    """The read view: header, findings grouped by artefact upstream first, result, legend."""
    title = cli_render.style("title", "Friction change check")
    if result.dormant:
        return "\n".join([f"{title} — dormant", "", *_dormant_lines(result)]) + "\n"

    summary = _failing_summary(result) or "nothing to answer"
    lines = [
        f"{title} — {summary}" + cli_render.style("muted", "   (the blocks: pkit validate)"),
        "",
    ]
    lines.extend(_header_lines(result))

    rows = [f for f in result.findings if f.location is not None and f.artefact is not None]
    unreadable = [f for f in result.findings if f.kind is FindingKind.UNREADABLE]
    lines.append("")
    lines.append(
        cli_render.style("heading", "FINDINGS")
        + cli_render.style("muted", " — upstream first along artefact anchors")
    )
    if not rows and not unreadable:
        lines.append("  nothing anchored changed in this diff")
    kind_width = max((len(f.kind.value) for f in rows + unreadable), default=0)
    anchor_width = max((len(_anchor_cell(f)) for f in rows), default=0)
    current: str | None = None
    for finding in rows:
        if finding.location != current:
            current = finding.location
            lines.append(f"  {current}")
        cells = f"{finding.kind.value:{kind_width}}  {_anchor_cell(finding):{anchor_width}}"
        lines.append(f"    {cells}  {finding.message}".rstrip())
    for finding in unreadable:
        lines.append(f"  {finding.location}")
        lines.append(f"    {finding.kind.value:{kind_width}}  {finding.message}")

    lines.extend(["", _result_line(result)])
    shown = [kind for kind in _LEGEND if result.count(kind)]
    if shown:
        width = max(len(kind.value) for kind in shown)
        lines.extend(["", cli_render.style("heading", "Legend")])
        lines.extend(f"  {kind.value:{width}}  {_LEGEND[kind]}" for kind in shown)
    lines.extend(
        [
            "",
            cli_render.style("heading", "Commands"),
            "  pkit friction check --json   the same findings, machine-readable",
            "  pkit validate                the blocks, deferrals and cycles themselves",
        ]
    )
    return "\n".join(lines) + "\n"


def _anchor_cell(finding: Finding) -> str:
    return "—" if finding.anchor is None else f"{finding.anchor.kind} {finding.anchor.value}"


def _header_lines(result: ChangeCheck) -> list[str]:
    lines: list[str] = []
    if result.base is not None:
        lines.append(
            f"  Base: {result.base.ref} at {result.base.commit[:SHORT]}"
            + cli_render.style("muted", "   (merge-base with HEAD)")
        )
    if result.head is not None:
        uncommitted = counted(result.head.uncommitted, "uncommitted path", "uncommitted paths")
        working = (
            f"+ working tree, {uncommitted}" if result.head.uncommitted else "(working tree clean)"
        )
        lines.append(f"  Head: {result.head.commit[:SHORT]} {working}")
    gloss = _MODE_GLOSS.get(result.mode, "")
    lines.append(f"  Mode: {result.mode}" + cli_render.style("muted", f"   ({gloss})"))
    lines.extend(_mode_warning(result))
    for finding in result.findings:
        if finding.kind is FindingKind.OUTDATED_BASE:
            lines.append(f"  ⚠ outdated base: {finding.message}")
    return lines


def _dormant_lines(result: ChangeCheck) -> list[str]:
    if not result.places:
        counts = "no places declared; dormant."
    else:
        counts = (
            f"{result.places} place(s), {result.artefacts} artefact(s), none carrying the "
            f"`{CONTAINER_KEY}` container; dormant."
        )
    lines = [f"  {counts}"]
    if result.base is not None:
        lines.append(f"  Base: {result.base.ref} at {result.base.commit[:SHORT]}")
    lines.extend(_mode_warning(result))
    return lines


def _mode_warning(result: ChangeCheck) -> list[str]:
    """A line when `friction.mode` is not a mode: read as the default, never silently."""
    if result.mode_as_written is None or result.mode_as_written == result.mode:
        return []
    return [
        f"  ⚠ friction.mode {result.mode_as_written!r} is not a mode; read as {result.mode} "
        f"— `pkit validate` fails on it"
    ]


def _failing_summary(result: ChangeCheck) -> str:
    parts = [
        (FindingKind.FRICTION, "friction", "friction"),
        (FindingKind.DEAD_ANCHOR, "dead anchor", "dead anchors"),
        (FindingKind.UNRESOLVED_KIND, "unresolved kind", "unresolved kinds"),
        (FindingKind.BUMP, "bump", "bumps"),
    ]
    return ", ".join(
        counted(result.count(kind), one, many) for kind, one, many in parts if result.count(kind)
    )


def counted(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _result_line(result: ChangeCheck) -> str:
    summary = _failing_summary(result)
    if result.failed:
        return cli_render.style("strong", "Result: failed") + f"   (enforcing: {summary})"
    if summary and result.mode != ENFORCING:
        return (
            cli_render.style("strong", "Result: passed")
            + f"   (warning mode: {summary} reported, not failed)"
        )
    return cli_render.style("strong", "Result: passed") + f"   ({result.mode})"
