"""The friction change check: `pkit friction check` (COR-050 points 5, 6, 7, 11, 12).

Every artefact with an anchor that changed in a pull request must carry one
of three answers in the same pull request (COR-050 point 5): **updated** (its
content changed and its `at` changed to a new value), **unchanged** (only
`at` changed to a new value, with `outcome: unchanged` and an
`unchanged-because` that changed too), or **deferred** (a deferral for that
anchor, by kind and value, was introduced). An artefact new in the diff
counts as revalidated, whatever `at` it carries. A change to the artefact's
own anchor list, or a move, needs a revalidation as well. Anything else is
*friction*. The check reads the artefacts, never a pull-request description,
so it works for any tool and locally before a commit.

**An `at` written back** (points 3 and 6; `_Behind`). Where the diff changes
an artefact's `at`, the check asks whether the value is new: one `git log -S`
search of the artefact's file behind the base for the value, and, on a hit,
the walk `check --all` makes (`friction_history`) over the one log from the
base. A value the artefact carried before — the revert of a revalidation —
answers nothing and is no bump: the artefact is judged against that value's
revalidation points instead of the base, asked about every anchor that
differs between them and head, and only a deferral that covers the anchor
answers it. An `at` removed writes back the block's own marker, judged
against the commit that first introduced the block. Likewise a deferral the
diff introduces on an anchor it asks about is searched for: one that puts
back an entry the artefact carried before — the same anchor and reason —
keeps that entry's point, and covers the anchor only as it stood there, and
nothing once a revalidation point reaches it (point 4; `_judge`'s
`covers`). In a shallow clone the walk always runs: a value first carried
inside the clone is read as first carried there, one the file already
carried at the cut answers nothing, and each artefact read to the cut is
named (`history.cut`).

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
- *A head named* (`--head`, `named_head`) is that commit, read from git
  objects as the base is: the merge-base is taken against it, the diff runs
  between the two commits, and the working tree is not read. Its anchor
  kinds are the ones it registers, as the base's are the base's. A resolver
  is a command run in the working tree, never read from a commit, so one runs
  only where the working tree is that commit, and the check refuses anywhere
  else (`_NamedHeadKinds`). What discovery reads from the working tree
  whichever state it walks — which files are synced copies, where a link
  leads — stays the running checkout's.

**When an anchor changed** (point 5) — between the base and head, two states,
so an edit undone within the change is none: a *path* anchor when a changed
path matches it that both sides leave in — each side read under its own
`friction.exclude` (point 7) — the artefact's own file ignored; a *record*
anchor when the record's file changed (a pure rename keeps its content); an
*artefact* anchor when the target's **content** changed — its body compared
textually and its own fields compared parsed, never the methodology's
container. The cascade follows: a dependant sees a change only where its
target's content changed, so an `unchanged` revalidation stops it.

**When `friction.exclude` changed over a path anchor** (point 7;
`exclusion_change`): a narrowing — a file it stands on at head that the base
left out — is always its question; a widening — a file it stood on at the
base that head holds and leaves out — only where the diff changes such a
file too, and is otherwise reported (`left-out`), never owed. A file the
diff removes is a change, never left out. Both are named in one question
with any other change to the anchor. Exclusions cover paths: a record or
artefact anchor is untouched by them. An artefact under an excluded path at
head owes no answer, but what it declares is checked and a change of its
`at` is judged; one the diff lets back in revalidates in the same change, as
a moved one does. A base whose exclusions do not read is read under head's,
and reported.

**What it reports** (points 7, 11, 12): friction; answers; a bump with
nothing behind it (`at` changed, but no answer stands); dead anchors *of the
pull request* (resolving to nothing at head, and either added in the diff or
with a target the diff removed, moved or excluded — dead anchors that were
already dead are the whole-repository check's); an anchor kind no installed
component resolves, separately, where the diff added the anchor or took the
kind's resolver away; an anchor whose resolver gave no answer; a widening
that asks nothing; an outdated base; front matter that does not parse.
Findings run upstream first along artefact anchors (truth-chain order).

**What it lists** (COR-050 point 3 and Implications): every answer the change
wrote — each revalidation, deferral and reason for having no anchors, word for
word — read from each head artefact carrying the block against its base
counterpart (`_written_answers`), with whether the diff asked for it and
whether the check accepts it — `written-back` where it puts back an `at` or a
deferral the artefact carried before. It is the list the person authorising
a merge is shown: derived from the artefacts, never composed.

**Modes** (point 12): `warning` reports and exits 0; `enforcing` exits 1 on
friction, dead anchors, unresolved kinds, a resolver's missing answer and
bumps (`FAILING_KINDS`). An outdated base never fails. Dormant — counts only,
exit 0 — when no place is declared or nothing in the places carries the
container (point 15).

**Resolver limits** (point 2; ADR-057). The anchor kinds capabilities register
(`friction.kinds` in their package metadata) are looked up in
`registered_anchor_kinds`, where a resolver command that does not declare the
query contract — bounded, deterministic, read-only, needing no network — is
refused (`refuse_resolver_without_query_contract`), as is a kind two
capabilities register. A resolver that may run is run once per anchor value
under the query policy (`AnchorKinds`), and answers the files of the working
tree the anchor stands on; the anchor changed in the diff when the diff changed
the content of one of them. A resolver is asked about the head alone, so what
an anchor stood on at the base is not known, and the check fails what it can
lay at the pull request (point 12; `_anchor_problem`): an anchor the diff
added that resolves to nothing or whose kind nothing resolves, and an anchor
the diff kept whose kind the diff left without a resolver that may run — the
base's registrations are read from the base commit. A resolver that gives no
answer fails closed, whoever added the anchor (`no-answer`): the check could
not do its work, and a second run may clear it. An anchor the diff kept whose
resolver names no file is reported, never failed (`dead-unattributed`):
whether the diff removed what it denoted cannot be told, and the
whole-repository check reports it as dead either way. Not a boundary: the
declaration is trusted, not enforced (COR-050 point 2) — no layer of this
distribution holds a single command to "no network" (ADR-057 point 4).

The check writes nothing (point 13).
"""

from __future__ import annotations

import copy
import functools
import heapq
import json
import os
import re
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from fnmatch import fnmatchcase
from functools import cached_property
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple, Self

from project_kit import cli_render, default_branch, refs
from project_kit.backbone_schemas import CONTAINER_KEY
from project_kit.friction_discovery import (
    CORE_ANCHOR_KINDS,
    FRICTION_KEY,
    Anchor,
    AnchorKinds,
    AnchorResolution,
    Artefact,
    ArtefactKind,
    Deferral,
    Discovery,
    FrictionSettings,
    RepositoryTree,
    ResolverCommand,
    content,
    deferral_reason,
    discover_artefacts,
    entry_reason,
    parsed_at,
    pattern_matcher,
    refuse_resolver_without_query_contract,  # noqa: F401 — re-exported: the check's public surface
    registered_anchor_kinds,
    revalidated_field,
    unresolved_kind_reason,
)
from project_kit.friction_git import (
    SHORT,
    BlobReader,
    CommitTree,
    DiffEntry,
    FrictionCheckError,
    commit_of,
    parse_name_status,
    run_git,
)
from project_kit.friction_history import (
    BLOCK,
    Commit,
    Walker,
    read_history,
    reason_word,
    shallow_commits,
)
from project_kit.project_config import project_config_path
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


# How many `git log -S` searches of the history behind the base run at once.
_SEARCHES = max(1, min(8, os.cpu_count() or 1))


# --- findings ----------------------------------------------------------------


class FindingKind(Enum):
    """What a finding is. The values are the `kind` field of the JSON output."""

    FRICTION = "friction"
    ANSWERED = "answered"
    REVALIDATED = "revalidated"
    BUMP = "bump"
    DEAD_ANCHOR = "dead-anchor"
    DEAD_UNATTRIBUTED = "dead-unattributed"  # dead at head, and not known to be the diff's
    UNRESOLVED_KIND = "unresolved-kind"
    NO_ANSWER = "no-answer"  # a registered kind's resolver gave no answer
    LEFT_OUT = "left-out"
    OUTDATED_BASE = "outdated-base"
    UNREADABLE = "unreadable"


#: The findings enforcing mode fails on (COR-050 point 12). An unresolved kind
#: is a dead anchor whose kind nothing resolves, reported separately; a missing
#: answer fails because the check could not tell, and never passes on that.
#:
#: `DEAD_UNATTRIBUTED` is left out on purpose, and this set is the one place that
#: decides it: an anchor of a registered kind the diff kept, whose resolver names
#: no file, is reported and not failed — whether the diff removed what it denoted
#: cannot be told from a resolver asked about the head alone (ADR-057 point 3).
#: Adding the kind here fails it instead; the legend and the failing summary follow
#: this set, so nothing else in the code changes.
FAILING_KINDS = frozenset(
    {
        FindingKind.FRICTION,
        FindingKind.BUMP,
        FindingKind.DEAD_ANCHOR,
        FindingKind.UNRESOLVED_KIND,
        FindingKind.NO_ANSWER,
    }
)


class Answer(Enum):
    """How an artefact answers a change (COR-050 point 5); `new` counts as revalidated."""

    UPDATED = "updated"
    UNCHANGED = "unchanged"
    DEFERRED = "deferred"
    NEW = "new"


def _anchor_json(anchor: Anchor | None) -> dict[str, str] | None:
    return None if anchor is None else {"kind": anchor.kind, "value": anchor.value}


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
            "anchor": _anchor_json(self.anchor),
            "answer": None if self.answer is None else self.answer.value,
            "message": self.message,
        }


#: The `answer` of an entry of the answers list that is a reason for having no
#: anchors (COR-050 point 1), beside a revalidation's outcome and `deferred`.
UNANCHORED = "unanchored"


class AnswerStatus(Enum):
    """Whether the check accepts an answer the change wrote. The values are the
    `status` field of an entry of the JSON output's `answers`."""

    STANDS = "stands"  # the check accepts it
    BUMP = "bump"  # `at` changed and the diff does not bear it out: the check's own `bump`
    EDITED = "edited"  # `at` untouched, the outcome or words changed: nothing is answered
    # An `at`, or a deferral, the artefact carried before, written back: the `at` answers
    # nothing, the deferral covers only what the entry it puts back did (COR-050 points 3, 4).
    WRITTEN_BACK = "written-back"


@dataclass(frozen=True)
class KeptDeferral:
    """A deferral a revalidation kept: present at the base and at head, by anchor."""

    anchor: Anchor
    reason: str | None  # its words at head, whitespace folded

    def as_json(self) -> dict[str, Any]:
        return {"anchor": _anchor_json(self.anchor), "reason": self.reason}


@dataclass(frozen=True)
class WrittenAnswer:
    """One answer the change wrote in an artefact's block (`_written_answers`): a
    revalidation, a deferral, or a reason for having no anchors, with its words.

    - `answer`: `updated` or `unchanged` for a revalidation — `None` when its
      `outcome` is neither — `deferred`, or `unanchored`.
    - `anchor`: the deferral's; `None` otherwise. `reason`: the words,
      whitespace folded as the check compares them; `None` where none is written.
    - `kept`: on a revalidation whose `at` changed, each deferral entry at head
      whose anchor the base defers too.
    - `asked`: the diff asked for it — for a revalidation, the diff asked the
      artefact anything and the revalidation stands; for a deferral, the diff
      asked about its anchor, it is introduced in the diff, and no revalidation
      stands.
    - `new`: the artefact has no counterpart at the base.
    """

    artefact: str  # the artefact's id
    location: str  # `path`, or `path#id` for a collection entry
    answer: str | None
    anchor: Anchor | None
    reason: str | None
    kept: tuple[KeptDeferral, ...]
    asked: bool
    status: AnswerStatus
    new: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "artefact": self.artefact,
            "location": self.location,
            "answer": self.answer,
            "anchor": _anchor_json(self.anchor),
            "reason": self.reason,
            "kept": [kept.as_json() for kept in self.kept],
            "asked": self.asked,
            "status": self.status.value,
            "new": self.new,
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
    commit: str  # HEAD, or the commit named with `--head`
    uncommitted: int  # paths the working tree changes beyond HEAD, untracked included
    named: str | None = None  # the revision named with `--head`; `None` reads the working tree

    @property
    def name(self) -> str:
        """How the head is named in what the check says: `HEAD`, or the revision given."""
        return "HEAD" if self.named is None else self.named


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
    answers: tuple[WrittenAnswer, ...] = ()  # what the change wrote, in the check's order
    unreadable: tuple[str, ...] = ()  # head files whose front matter does not parse: not listed
    shallow: bool | None = None  # the clone's history is cut; `None` while dormant
    # Locations of the artefacts whose history behind the base was read to a shallow
    # clone's cut: a value first carried inside the clone is read as first carried there.
    cut: tuple[str, ...] = ()

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


# --- git ----------------------------------------------------------------------
#
# The primitives — `run_git`, `commit_of`, `CommitTree`, `DiffEntry`,
# `parse_name_status` and `FrictionCheckError` — live in `friction_git`, one
# layer down, and are re-exported here as the check's surface.


def head_commit(root: Path) -> str:
    """HEAD's commit; refuses before the first commit, when there is nothing to compare."""
    head = commit_of(root, "HEAD")
    if head is None:
        raise FrictionCheckError(
            "HEAD names no commit yet; the change check compares a branch with its base, "
            "so commit first."
        )
    return head


def named_head(root: Path, rev: str) -> HeadState:
    """The head named with `--head`: the commit `rev` names, read from git objects, with
    nothing uncommitted — the working tree is not read. Refuses a name that is no commit."""
    commit = None if not rev or rev.startswith("-") else commit_of(root, rev)
    if commit is None:
        raise FrictionCheckError(f"--head {rev!r} names no commit of this repository.")
    return HeadState(commit, 0, rev)


def resolve_base(
    root: Path,
    ref: str | None = None,
    *,
    resolved: default_branch.Base | None = None,
    head: HeadState | None = None,
) -> BaseState:
    """The base's commit, its merge-base with HEAD — or with the `head` named
    (`named_head`) — and whether it moved on: `ref`, else `$PKIT_CHECK_BASE`, else the
    default branch — computed once for every reader (`default_branch.base`, COR-054
    point 5). `resolved` is that base when the run has read it already
    (`default_branch.settled`), so it is not resolved twice."""
    if head is None:
        head_commit(root)
    head_rev = "HEAD" if head is None else head.commit  # the commit, as the diff reads it
    found = default_branch.base(root, ref, head_rev=head_rev) if resolved is None else resolved
    if found.problem is not None or found.tip is None or found.fork is None:
        raise FrictionCheckError(found.problem or f"the base {found.ref!r} cannot be compared.")
    return BaseState(ref=found.ref, tip=found.tip, commit=found.fork, outdated=bool(found.outdated))


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


def read_diff(root: Path, base_commit: str, head: HeadState | None = None) -> Diff:
    """`git diff -M --name-status` from the base to the working tree, untracked files
    added — or, for a `head` named (`named_head`), to that commit, the working tree
    left unread."""
    to = () if head is None else (head.commit,)
    raw = run_git(
        root,
        "diff",
        "-M",
        "--name-status",
        "-z",
        "--no-color",
        "--relative",
        base_commit,
        *to,
        "--",
    ).stdout
    entries = parse_name_status(nul_separated(raw))
    if head is not None:
        uncommitted = 0
    else:
        known = {e.path for e in entries}
        entries.extend(DiffEntry("A", rel) for rel in _untracked(root) if rel not in known)
        uncommitted = uncommitted_paths(root)
    return Diff(
        entries=tuple(sorted(entries, key=lambda e: (e.path, e.status))), uncommitted=uncommitted
    )


def _untracked(root: Path) -> list[str]:
    return nul_separated(run_git(root, "ls-files", "-z", "--others", "--exclude-standard").stdout)


def uncommitted_paths(root: Path) -> int:
    """How many paths the working tree changes beyond HEAD, untracked ones included."""
    beyond_head = nul_separated(
        run_git(root, "diff", "--name-only", "-z", "--no-color", "--relative", "HEAD", "--").stdout
    )
    return len(set(beyond_head) | set(_untracked(root)))


# --- one side of the diff -----------------------------------------------------


# How a dead record or artefact anchor resolves to nothing; a path anchor's is `Side.why_dead`.
_RESOLVES_NOTHING = {
    "record": "names no record",
    "artefact": "names no artefact in the declared places",
}


class Listing:
    """One state of the repository as `friction.exclude` reads it: its files, and the
    settings whose `exclude` says what it leaves out (COR-050 point 7).

    `settings` are the state's own, unless `read_under` gave it another
    state's — for a state whose own exclusions do not read
    (`FrictionSettings.exclude_unreadable`), which is then read as the state
    it is compared with rather than as one that excludes nothing.
    """

    def __init__(self, files: Iterable[str], settings: FrictionSettings) -> None:
        self.files = frozenset(files)
        self.settings = settings

    def excluded(self, path: str) -> bool:
        """Whether `friction.exclude` leaves `path` out: discovery's one decision of it."""
        return self.settings.excluded(path)

    def read_under(self, settings: FrictionSettings) -> Self:
        """This state, its exclusions read from `settings` instead of its own."""
        found = copy.copy(self)
        found.settings = settings
        return found

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
        exclusions.
        """
        listing = self.files if files is None else files
        return tuple(sorted(filter(self.stands_on(pattern), listing)))

    def left_out(self, pattern: str) -> tuple[str, ...]:
        """The files here a path anchor's `pattern` matches but does not stand on,
        because `friction.exclude` leaves them out (COR-050 point 7), sorted."""
        match = pattern_matcher(pattern)
        return tuple(sorted(rel for rel in self.files if match(rel) and self.excluded(rel)))


class Side(Listing):
    """One state of the repository as the check reads it: its files and its artefacts."""

    def __init__(self, root: Path, tree: RepositoryTree, discovery: Discovery) -> None:
        super().__init__(tree.files(), discovery.settings)
        self.root = root
        self.discovery = discovery

    def find(self, reference: str) -> Artefact | None:
        return self.discovery.find(reference)

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


# How many of an exclusion change's files a message names before counting the rest.
_NAMED = 3


@dataclass(frozen=True)
class ExclusionChange:
    """What `friction.exclude` changing between an earlier and a later state did to
    one path anchor (COR-050 point 7), each sorted.

    - `left_out`: files it stood on in the earlier state that the later one
      holds and leaves out — a widening. A widening is the anchor's question
      only where such a file changed; otherwise it is reported.
    - `let_in`: files it stands on in the later state that the earlier one
      left out — a narrowing, always the anchor's question.
    - `gone`: files it stood on in the earlier state that the later one no
      longer holds, under a path the later one leaves out. A file that is not
      there is not left out, so none is ever named as left out; its removal
      is a change like any other.

    False when it neither leaves out nor lets in a file: the two states leave
    out the same paths, or the change covers none of the anchor's files.
    """

    left_out: tuple[str, ...] = ()
    let_in: tuple[str, ...] = ()
    gone: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.left_out or self.let_in)

    def less(self, own: frozenset[str]) -> ExclusionChange:
        """The change without the artefact's own file under any of its names (`own`)."""
        return ExclusionChange(
            tuple(rel for rel in self.left_out if rel not in own),
            tuple(rel for rel in self.let_in if rel not in own),
            tuple(rel for rel in self.gone if rel not in own),
        )

    def describe(self, notes: Mapping[str, str] | None = None) -> str:
        """`now leaves out a, b`, `now lets in c`, or both — what the change did, each
        file followed by its note in `notes`, where it has one: `now leaves out a,
        which this diff also changes, and b`."""
        notes = notes or {}
        parts: list[str] = []
        for verb, files in (("now leaves out", self.left_out), ("now lets in", self.let_in)):
            if files:
                parts.append(f"{verb} {_noted(files, notes)}")
        return "; ".join(parts)


def _noted(files: Sequence[str], notes: Mapping[str, str]) -> str:
    """`files`, those sharing a note listed together and followed by it, the rest last."""
    groups: dict[str | None, list[str]] = {}
    for rel in files:
        groups.setdefault(notes.get(rel), []).append(rel)
    items = [f"{_listed(named)}, {note}" for note, named in groups.items() if note is not None]
    if None in groups:
        items.append(_listed(groups[None]))
    return ", and ".join(items)


def _listed(paths: Sequence[str]) -> str:
    named = ", ".join(paths[:_NAMED])
    rest = len(paths) - _NAMED
    return f"{named} and {rest} more" if rest > 0 else named


def left_out_message(files: Sequence[str], stood: str, unchanged: str) -> str:
    """A widening that asks nothing, as both checks report it (COR-050 point 7): what
    `friction.exclude` now leaves out that a path anchor stood on — `stood` says
    where — and that none of it changed, `unchanged` saying over what."""
    them = "it" if len(files) == 1 else "them"
    return (
        f"`friction.exclude` now leaves out {counted(len(files), 'file', 'files')} this anchor "
        f"stood on {stood} ({_listed(files)}); no change to {them} {unchanged}"
    )


def exclusion_change(pattern: str, before: Listing, after: Listing) -> ExclusionChange:
    """What `friction.exclude` changing from `before` to `after` did to a path anchor's
    `pattern` (`ExclusionChange`), each state's files read under its own exclusions —
    the one reading both checks give such a change: the change check between the base
    and head, the whole-repository check between the revalidation point and HEAD.

    Nothing moved where the states leave out the same paths, or where either
    state's exclusions do not read (`exclude_unreadable`): what such a state
    leaves out cannot be told, so it is never read as a change.
    """
    if (
        before.settings.exclude_unreadable is not None
        or after.settings.exclude_unreadable is not None
        or before.settings.excludes_as(after.settings)
    ):
        return ExclusionChange()
    match = pattern_matcher(pattern)
    left_out: list[str] = []
    gone: list[str] = []
    for rel in sorted(before.files):
        if match(rel) and not before.excluded(rel) and after.excluded(rel):
            (left_out if rel in after.files else gone).append(rel)
    let_in = sorted(
        rel
        for rel in after.files
        if match(rel) and not after.excluded(rel) and before.excluded(rel)
    )
    return ExclusionChange(tuple(left_out), tuple(let_in), tuple(gone))


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


def _because(artefact: Artefact) -> str | None:
    """`unchanged-because` with its whitespace folded: a re-wrap is not a new justification."""
    value = revalidated_field(artefact, "unchanged-because")
    return " ".join(value.split()) if isinstance(value, str) else None


def anchors_of(artefact: Artefact) -> list[Anchor]:
    return [Anchor(kind, value) for kind, values in artefact.anchors.items() for value in values]


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
    outcome = revalidated_field(artefact, "outcome")
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
    """Whether a live anchor of a core kind changed in the diff (COR-050 point 5).

    A path anchor, when a changed path it stands on at both sides — each read
    under its own exclusions — is not its own file (`_path_reading`).
    """
    if anchor.kind == "path":
        return bool(_path_reading(anchor, own, head, base, diff).changed)
    if anchor.kind == "record":
        rel = head.record_path(anchor.value)
        entry = diff.by_path.get(rel) if rel is not None else None
        return entry is not None and entry.changes_content
    target = head.find(anchor.value)
    before = base.find(anchor.value)
    return target is not None and (before is None or content(target) != content(before))


@dataclass(frozen=True)
class _PathReading:
    """What the diff did to a path anchor (COR-050 points 5 and 7), the artefact's
    own file under either of its names left out.

    `changed`: the files the diff changed that it stands on at both sides, each
    read under its own exclusions — or stood on at the base and removed, where
    head leaves their path out (`ExclusionChange.gone`). `moved`: what the
    diff's `friction.exclude` did to it. `touched`: of `moved`'s files, those
    the diff changes too.
    """

    changed: tuple[str, ...]
    moved: ExclusionChange
    touched: frozenset[str]

    @property
    def asks(self) -> bool:
        """Whether the exclusion change is a question: a narrowing always is, a
        widening where a file it leaves out changes in the diff too."""
        return bool(self.moved.let_in) or any(rel in self.touched for rel in self.moved.left_out)


def _path_reading(
    anchor: Anchor, own: frozenset[str], head: Side, base: Side, diff: Diff
) -> _PathReading:
    moved = exclusion_change(anchor.value, base, head).less(own)
    stood, stands = base.stands_on(anchor.value), head.stands_on(anchor.value)
    changed = tuple(
        sorted(rel for rel in diff.paths - own if stood(rel) and (stands(rel) or rel in moved.gone))
    )
    touched = frozenset(rel for rel in moved.left_out + moved.let_in if rel in diff.paths)
    return _PathReading(changed, moved, touched)


@dataclass(frozen=True)
class _Question:
    """Something in the diff the artefact must answer."""

    subject: str  # how the finding's message opens
    anchor: Anchor | None = None  # a changed anchor; None for the anchor list, a move or a let-in
    topic: str = "anchor"  # what it asks about: `anchor`, `anchors`, `place` or `let-in`

    @property
    def key(self) -> tuple[str, Anchor | None]:
        return (self.topic, self.anchor)


# What a file an exclusion change names says of itself when the diff changes it too.
_ALSO_CHANGED = "which this diff also changes"


@dataclass(frozen=True)
class _Wording:
    """How a question names the earlier state it compares head with: the base, or the
    revalidation point of an `at` the diff writes back (COR-050 point 6)."""

    where: str = "in this diff"  # `changed <where>`
    stood: str = "at the base"  # where a widening's files stood
    unchanged: str = "in this diff"  # over what they did not change
    also: str = _ALSO_CHANGED  # a widened file that changed too
    let_in: str = "this diff's `friction.exclude` lets it back in"


_AGAINST_BASE = _Wording()


def _anchor_question(
    anchor: Anchor,
    own: frozenset[str],
    head: Side,
    base: Side,
    diff: Diff,
    kinds: AnchorKinds,
    wording: _Wording = _AGAINST_BASE,
) -> tuple[_Question | None, str | None]:
    """What the diff asks of a live anchor, or `None`, and for a path anchor what the
    diff's widening of `friction.exclude` took from it when that asks nothing — the
    message of a `left-out` finding (COR-050 points 5 and 7).

    A path anchor's changed files and its exclusion change are both named: a
    widening never hides a change to the same anchor. The exclusion change is a
    question where it narrows, or where a file it leaves out changes in the
    diff too (`_PathReading.asks`); a widening over files the diff leaves alone
    is reported, never owed — what changed under them before the diff is the
    whole-repository check's, as friction already there always is. An anchor
    of a registered kind is asked when the diff changed the content of a file
    its resolver says it stands on, its artefact's own file left out, as a
    path anchor's is; exclusions cover path anchors alone, as for a record.
    `base` is the earlier state, `diff` the diff from it, and `wording` how the
    question names it.
    """
    where = wording.where
    if anchor.kind not in CORE_ANCHOR_KINDS:
        changed = tuple(
            rel
            for rel in kinds.files(anchor)
            if rel not in own and (entry := diff.by_path.get(rel)) is not None
            if entry.changes_content
        )
        if not changed:
            return None, None
        return _Question(f"changed {where} ({_listed(changed)})", anchor), None
    if anchor.kind != "path":
        changed = _anchor_changed(anchor, own, head, base, diff)
        return (_Question(f"changed {where}", anchor) if changed else None), None
    reading = _path_reading(anchor, own, head, base, diff)
    moved = reading.moved
    if not reading.asks:
        note = left_out_message(moved.left_out, wording.stood, wording.unchanged) if moved else None
        question = _Question(f"changed {where}", anchor) if reading.changed else None
        return question, note
    described = moved.describe(dict.fromkeys(reading.touched, wording.also))
    if reading.changed:
        subject = (
            f"changed {where} ({_listed(reading.changed)}), and `friction.exclude` "
            f"changed over it ({described})"
        )
    else:
        subject = f"`friction.exclude` changed over it {where} ({described})"
    return _Question(subject, anchor), None


def _questions(
    artefact: Artefact,
    before: Artefact,
    resolving: Collection[Anchor],
    head: Side,
    earlier: Side,
    diff: Diff,
    kinds: AnchorKinds,
    wording: _Wording,
) -> tuple[list[_Question], list[tuple[Anchor, str]]]:
    """What the diff from an earlier state asks one artefact — `before` is the artefact
    as `earlier` holds it — and, per path anchor, what a widening of `friction.exclude`
    took from it without asking (COR-050 points 5 to 7).

    Each anchor the artefact kept from `before` and that resolves at head
    (`resolving`) is asked where it changed (`_anchor_question`); a changed
    anchor list, a move and a let-in each need a revalidation. An artefact
    under an excluded path at head owes no answer, so nothing asks it anything.
    """
    if artefact.excluded:
        return [], []
    questions: list[_Question] = []
    notes: list[tuple[Anchor, str]] = []
    own = frozenset({artefact.path, before.path})
    earlier_anchors = frozenset(anchors_of(before))
    for anchor in anchors_of(artefact):
        if anchor not in resolving or anchor not in earlier_anchors:
            continue
        question, note = _anchor_question(anchor, own, head, earlier, diff, kinds, wording)
        if question is not None:
            questions.append(question)
        if note is not None:
            notes.append((anchor, note))
    if frozenset(anchors_of(artefact)) != earlier_anchors:
        questions.append(_Question(f"its anchor list changed {wording.where}", topic="anchors"))
    if before.location != artefact.location:
        questions.append(
            _Question(f"it moved here from {before.location} {wording.where}", topic="place")
        )
    if earlier.excluded(before.path):
        questions.append(_Question(wording.let_in, topic="let-in"))
    return questions, notes


# --- the history behind the base ----------------------------------------------------


@dataclass(frozen=True)
class _Point:
    """A revalidation point of an `at` the diff writes back, read as the check reads its
    base: the artefact as it held it, that commit's side, and the diff from it to head."""

    index: int  # its log index in the history behind the base
    commit: Commit
    before: Artefact
    side: Side
    diff: Diff

    @property
    def wording(self) -> _Wording:
        where = (
            f"since its revalidation point {self.commit.short} ({self.commit.day}), whose "
            f"`at` this diff writes back"
        )
        return _Wording(
            where=where,
            stood="at its revalidation point",
            unchanged="since",
            also="which changed since too",
            let_in=f"`friction.exclude` lets it back in {where}",
        )


@dataclass(frozen=True)
class _WrittenBack:
    """An `at` the diff writes back: a value the artefact carried before (COR-050 point 3).

    `points` are that value's revalidation points; empty where a shallow
    clone is cut where the file already carried it — the value answers
    nothing, and the artefact is judged against the base.
    """

    points: tuple[_Point, ...]


@dataclass(frozen=True)
class _PutBack:
    """A deferral the diff puts back, with an anchor and a reason the artefact carried
    before: it keeps the point of the entry it puts back (COR-050 point 4) — `None`
    where that lies beyond a shallow clone."""

    point: int | None
    commit: Commit | None


def _same_file(artefact: Artefact, before: Artefact, diff: Diff) -> bool:
    """Whether head's artefact lives in its base counterpart's file — the same file, or
    one the diff renamed — so the file's history behind the base is the artefact's.
    An entry moved to another collection file, or a document matched by its own id
    across a move git did not pair, starts its history at the move (COR-050 point 3)."""
    return diff.renamed_from.get(artefact.path, artefact.path) == before.path


def _needles(artefact: Artefact, value: Any) -> list[str]:
    """What a file's history must hold somewhere for `value` to have been carried
    before: its canonical UTC form and the `at` as written, or the block's key — a
    needle that holds another left out, since every text holding it holds that one."""
    if value is BLOCK:
        return [FRICTION_KEY]
    found: list[str] = []
    if isinstance(value, datetime) and value.tzinfo is not None:
        found.append(value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S"))
    written = revalidated_field(artefact, "at")
    if isinstance(written, str) and written.strip() and not any(n in written for n in found):
        found.append(written.strip())
    return found or [str(value)]


class _Behind:
    """The history behind the base, read only where a change alters an artefact's `at` or
    brings a deferral back (COR-050 point 6).

    First, where the clone is not shallow, one `git log -S` search of the
    artefact's file for what a carrying would hold (`_seen`): no hit, and the
    value is new. On a hit, the one log from the base (`read_history`), read
    once per run, and the walk `check --all` makes (`friction_history.Walker`).
    In a shallow clone the walk always runs, since only it tells what the cut
    hides; each artefact read without history beyond the cut is listed (`cut`).
    """

    def __init__(self, root: Path, base: BaseState, named: HeadState | None, head: Side) -> None:
        self._root = root
        self._base = base
        self._named = named
        self._head = head
        self.shallow = bool(shallow_commits(root))
        self.cut: list[str] = []
        self._searched: dict[tuple[str, tuple[str, ...]], frozenset[str]] = {}
        self._blobs: BlobReader | None = None
        self._walker: Walker | None = None
        self._states: dict[str, tuple[Side, Diff]] = {}

    def close(self) -> None:
        if self._blobs is not None:
            self._blobs.close()

    @property
    def walker(self) -> Walker:
        if self._walker is None:
            history = read_history(self._root, self._base.commit)
            self._blobs = BlobReader(self._root)
            self._walker = Walker(history, self._blobs)
        return self._walker

    def prefetch(self, pairs: Iterable[tuple[Artefact, Artefact]], diff: Diff) -> None:
        """Run at once the searches `written_back` will make for these (head, base)
        artefacts — those whose `at` the diff changes, in the same file — each its own
        `git log -S` process, so a change revalidating many artefacts waits about as long
        as for one."""
        wanted: list[tuple[str, tuple[str, ...]]] = []
        for artefact, before in pairs:
            at = parsed_at(artefact)
            if at == parsed_at(before) or not _same_file(artefact, before, diff):
                continue
            key = (before.path, tuple(_needles(artefact, BLOCK if at is None else at)))
            if key not in self._searched and key not in wanted:
                wanted.append(key)
        if self.shallow or len(wanted) < 2:
            return

        def search(key: tuple[str, tuple[str, ...]]) -> frozenset[str]:
            return self._search(*key)

        with ThreadPoolExecutor(max_workers=min(len(wanted), _SEARCHES)) as pool:
            for key, commits in zip(wanted, pool.map(search, wanted), strict=True):
                self._searched[key] = commits

    def _seen(self, path: str, needles: Sequence[str]) -> frozenset[str] | None:
        """The commits behind the base that changed how often the file at `path` —
        renames followed, a merge read against each parent — holds one of `needles`:
        empty where none did. `None` in a shallow clone, where only the walk tells what
        the cut hides."""
        if self.shallow:
            return None
        key = (path, tuple(needles))
        if key not in self._searched:
            self._searched[key] = self._search(*key)
        return self._searched[key]

    def _search(self, path: str, needles: Sequence[str]) -> frozenset[str]:
        """`git log -S<needle>` for each needle, a fixed string — git finds one far faster
        than a pattern — and the commits they list."""
        found: set[str] = set()
        for needle in needles:
            listed = run_git(
                self._root,
                "log",
                "-m",
                "--follow",
                "--root",
                "--no-color",
                "--format=%H",
                f"-S{needle}",
                self._base.commit,
                "--",
                path,
            ).stdout
            found.update(listed.decode().split())
        return frozenset(found)

    def _note_cut(self, artefact: Artefact) -> None:
        if artefact.location not in self.cut:
            self.cut.append(artefact.location)

    def written_back(self, artefact: Artefact, before: Artefact, diff: Diff) -> _WrittenBack | None:
        """The `at` the diff writes back for `artefact` (`_WrittenBack`), or `None` where
        `at` held or the value is new. An `at` removed writes back the block's own
        marker: it is judged against the commit that first introduced the block. Only
        the commits the search lists can have written the value, so the walk reads
        no other version (`Walker.carried`)."""
        at = parsed_at(artefact)
        if at == parsed_at(before) or not _same_file(artefact, before, diff):
            return None
        value = BLOCK if at is None else at
        listed = self._seen(before.path, _needles(artefact, value))
        if listed is not None and not listed:
            return None
        history = self.walker.history
        among = (
            None
            if listed is None
            else frozenset(index for sha in listed if (index := history.position(sha)) is not None)
        )
        found = self.walker.carried(before, value, among)
        if found.cut:
            self._note_cut(artefact)
        if found.unreachable:
            return _WrittenBack(())
        if not found.points:
            return None
        return _WrittenBack(tuple(self._point(index, before) for index in found.points))

    def _point(self, index: int, before: Artefact) -> _Point:
        history = self.walker.history
        commit = history.commits[index]
        version = next(v for v in history.versions(before.path) if v.index == index)
        then = self.walker.same_at(version, before)
        side, diff = self.state(commit.sha)
        return _Point(index, commit, before if then is None else then, side, diff)

    def state(self, sha: str) -> tuple[Side, Diff]:
        """The commit `sha` read as the check reads its base, and the diff from it to head;
        exclusions that do not read there are read as head's."""
        found = self._states.get(sha)
        if found is None:
            tree = CommitTree(self._root, sha)
            side = Side(self._root, tree, discover_artefacts(self._root, tree=tree))
            if side.settings.exclude_unreadable is not None:
                side = side.read_under(self._head.settings)
            found = self._states[sha] = (side, read_diff(self._root, sha, self._named))
        return found

    def put_back(
        self, artefact: Artefact, before: Artefact, anchor: Anchor, diff: Diff
    ) -> _PutBack | None:
        """The deferral on `anchor` the diff introduces, where it puts back an entry the
        artefact carried before (`_PutBack`); `None` where it is new."""
        if not _same_file(artefact, before, diff):
            return None
        reason = next(
            (entry_reason(artefact, d) for d in artefact.deferrals if d.anchor == anchor), None
        )
        word = reason_word(reason)
        if word is not None and self._seen(before.path, [word]) == frozenset():
            return None
        found = self.walker.deferral_point(before, anchor, reason)
        if found.cut:
            self._note_cut(artefact)
        if found.unreachable:
            return _PutBack(None, None)
        if found.point is None:
            return None
        return _PutBack(found.point, self.walker.history.commits[found.point])

    def kept_point(self, before: Artefact, anchor: Anchor) -> int | None:
        """The deferral point of the entry on `anchor` the base carries."""
        return self.walker.deferral_point(before, anchor).point

    def points_of(self, before: Artefact) -> tuple[int, ...]:
        """The revalidation points of the `at` the base carries."""
        at = parsed_at(before)
        return self.walker.carried(before, BLOCK if at is None else at).points

    def reaches(self, points: Sequence[int], index: int) -> bool:
        return index in self.walker.history.reached(points)

    def differs_since(
        self,
        index: int,
        anchor: Anchor,
        own: frozenset[str],
        head: Side,
        kinds: AnchorKinds,
    ) -> bool:
        """Whether `anchor` at head differs from what it stood on at the commit at
        `index` (COR-050 point 5), read as the check reads a change from its base."""
        side, diff = self.state(self.walker.history.commits[index].sha)
        question, _note = _anchor_question(anchor, own, head, side, diff, kinds)
        return question is not None


@dataclass(frozen=True)
class _Judged:
    """What the answers list reads of `_judge`'s reading of one artefact: the
    revalidation as judged, whether its `at` is written back, the deferrals put back
    and those that answered a question."""

    revalidation: _Revalidation | None = None
    written_back: bool = False
    put_back: frozenset[Anchor] = frozenset()
    covering: frozenset[Anchor] = frozenset()


def _judge(
    artefact: Artefact,
    before: Artefact | None,
    head: Side,
    base: Side,
    diff: Diff,
    kinds: AnchorKinds,
    resolved_at_base: Callable[[str], bool],
    behind: _Behind,
) -> tuple[list[Finding], list[_Question], _Judged]:
    """The findings about one head artefact carrying the `friction` block, the questions
    the diff asked it — none for a new or an excluded one — and what the answers list
    reads of the judgement (`_written_answers`).

    An artefact under an excluded path at head owes no answer (COR-050 point
    7), as the whole-repository check never judges one stale: nothing in the
    diff asks it anything, and what it declares is still checked — the dead
    anchors and unresolved kinds of the diff — as is a change of its `at`,
    judged like any other, so a marker bumped while excluded is a bump. One
    the diff's `friction.exclude` lets back in must revalidate in the same
    change, as a moved one must (point 3): the base never asked it anything.

    An `at` the diff writes back (point 3; `_Behind.written_back`) answers
    nothing and is no bump: the artefact is judged against that value's
    revalidation points instead of the base, asked about an anchor only where
    every point's reading asks it. A deferral answers a question where it
    covers the anchor (point 4; `covers`).
    """

    def finding(
        kind: FindingKind, message: str, anchor: Anchor | None = None, answer: Answer | None = None
    ) -> Finding:
        return Finding(kind, message, artefact.id, artefact.location, anchor, answer)

    base_anchors = frozenset(anchors_of(before)) if before is not None else frozenset[Anchor]()
    findings: list[Finding] = []
    resolving: set[Anchor] = set()  # the anchors that resolve at head
    for anchor in anchors_of(artefact):
        added = anchor not in base_anchors
        problem = _anchor_problem(anchor, added, head, base, kinds, resolved_at_base)
        if problem is None:
            resolving.add(anchor)
            continue
        kind, message = problem
        if message is not None:
            findings.append(finding(kind, message, anchor))

    if before is None:
        if artefact.excluded:
            return findings, [], _Judged()
        message = "new in this diff: counts as revalidated"
        if any(u.path == artefact.path for u in base.discovery.unreadable):
            message += " (its base version's front matter does not parse, so there is no before)"
        findings.append(finding(FindingKind.ANSWERED, message, None, Answer.NEW))
        return findings, [], _Judged()

    written = behind.written_back(artefact, before, diff)
    points = () if written is None else written.points
    if points:
        readings = [
            _questions(artefact, p.before, resolving, head, p.side, p.diff, kinds, p.wording)
            for p in points
        ]
        asked = {q.key for q in readings[0][0]}
        for found, _notes in readings[1:]:
            asked &= {q.key for q in found}
        questions = [q for q in readings[0][0] if q.key in asked]
        notes = readings[0][1]
        revalidation = None
    else:
        questions, notes = _questions(
            artefact, before, resolving, head, base, diff, kinds, _AGAINST_BASE
        )
        revalidation = None if written is not None else _revalidation(artefact, before)
    standing = revalidation.answer if revalidation is not None else None
    deferred_now = {d.anchor for d in artefact.deferrals}
    deferred_before = {d.anchor for d in before.deferrals}
    introduced = deferred_now - deferred_before
    kept = deferred_now & deferred_before
    put_backs: dict[Anchor, _PutBack | None] = {}
    own = frozenset({artefact.path, before.path})

    def put_back(anchor: Anchor) -> _PutBack | None:
        if anchor not in put_backs:
            put_backs[anchor] = behind.put_back(artefact, before, anchor, diff)
        return put_backs[anchor]

    def covers(anchor: Anchor) -> bool:
        """Whether a deferral answers the question on `anchor` (COR-050 point 4).

        One introduced in the diff covers the anchor as it stands at head —
        unless it puts back an entry the artefact carried before: then, like
        any entry with its point behind the base, it covers the anchor only as
        it stood at that point, and nothing once a revalidation point reaches
        it. An entry kept from the base answers nothing new against the base;
        against the point of a written-back `at`, it covers by the same rule.
        """
        if anchor in introduced:
            back = put_back(anchor)
            if back is None:
                return True
            point = back.point
        elif anchor in kept and points:
            point = behind.kept_point(before, anchor)
        else:
            return False
        if point is None:
            return False
        reaching = [p.index for p in points] if points else list(behind.points_of(before))
        if behind.reaches(reaching, point):
            return False
        return not behind.differs_since(point, anchor, own, head, kinds)

    covering: set[Anchor] = set()
    for question in questions:
        anchor = question.anchor
        if standing is not None:
            answer = standing
        elif anchor is not None and covers(anchor):
            answer = Answer.DEFERRED
            covering.add(anchor)
        else:
            back = put_backs.get(anchor) if anchor is not None else None
            message = _friction_message(
                question, deferral_predates=anchor in kept, back=back, written=bool(points)
            )
            findings.append(finding(FindingKind.FRICTION, message, anchor))
            continue
        message = f"{question.subject}; answered: {_answer_text(answer, artefact, anchor)}"
        findings.append(finding(FindingKind.ANSWERED, message, anchor, answer))
    findings.extend(finding(FindingKind.LEFT_OUT, note, anchor) for anchor, note in notes)
    if revalidation is not None and revalidation.bump is not None:
        findings.append(finding(FindingKind.BUMP, revalidation.bump))
    if standing is not None and not questions:
        message = f"revalidated with no changed anchor: {_answer_text(standing, artefact)}"
        findings.append(finding(FindingKind.REVALIDATED, message, None, standing))
    judged = _Judged(
        revalidation,
        written is not None,
        frozenset(anchor for anchor, back in put_backs.items() if back is not None),
        frozenset(covering),
    )
    return findings, questions, judged


def _anchor_problem(
    anchor: Anchor,
    added: bool,
    head: Side,
    base: Side,
    kinds: AnchorKinds,
    resolved_at_base: Callable[[str], bool],
) -> tuple[FindingKind, str | None] | None:
    """`None` when the anchor resolves at head; otherwise its finding kind and message.

    The message is `None` when the problem is not the diff's: an anchor that
    was already dead at the base is the whole-repository check's, not this
    check's (COR-050 points 7 and 12). A path anchor the diff's
    `friction.exclude` left standing on nothing says so: `…, excluded since
    this diff`.

    A kind nothing resolves at head is the diff's when the diff added the
    anchor, or kept it and took the kind's resolver away — the base could
    resolve the kind (`resolved_at_base`): the capability uninstalled, a
    second registrant added, the declaration or the leaf dropped. One the base
    could not resolve either was already there.

    An anchor of a registered kind is judged by its resolver's answer, which
    is the head's alone — what it stood on at the base is not known:

    - no answer fails closed, whoever added the anchor (`NO_ANSWER`): the
      check cannot tell whether the diff changed what it denotes, and never
      passes on that (COR-050 point 2);
    - an answer naming no file makes an anchor the diff added dead
      (`DEAD_ANCHOR`), and one it kept dead with nobody to lay it at
      (`DEAD_UNATTRIBUTED`) — reported, and failed only if `FAILING_KINDS`
      says so.
    """
    reason = kinds.unresolved(anchor.kind)
    if reason is not None:
        if added:
            return (
                FindingKind.UNRESOLVED_KIND,
                f"nothing installed resolves this kind: {reason}; the anchor was added in this "
                f"diff",
            )
        if resolved_at_base(anchor.kind):
            return (
                FindingKind.UNRESOLVED_KIND,
                f"nothing installed resolves this kind, and this diff took its resolver away: "
                f"{reason}",
            )
        return FindingKind.UNRESOLVED_KIND, None
    if anchor.kind not in CORE_ANCHOR_KINDS:
        resolution = kinds.resolve(anchor)
        if resolution.no_answer is not None:
            return (
                FindingKind.NO_ANSWER,
                f"its resolver gave no answer, so whether this diff changed what it denotes "
                f"cannot be told: {resolution.no_answer} — run again; if it gives none again, "
                f"`pkit sync`, or the resolver needs mending",
            )
        if resolution.paths:
            return None
        if added:
            return (
                FindingKind.DEAD_ANCHOR,
                "its resolver names no file for it; the anchor was added in this diff",
            )
        return (
            FindingKind.DEAD_UNATTRIBUTED,
            "its resolver names no file for it; whether this diff removed what it denoted "
            "cannot be told — the whole-repository check reports it as dead",
        )
    if head.resolves(anchor):
        return None
    if added:
        return (
            FindingKind.DEAD_ANCHOR,
            f"{head.why_dead(anchor)}; the anchor was added in this diff",
        )
    if base.resolves(anchor):
        if anchor.kind == "path" and exclusion_change(anchor.value, base, head).left_out:
            return FindingKind.DEAD_ANCHOR, f"{head.why_dead(anchor)}, excluded since this diff"
        return (
            FindingKind.DEAD_ANCHOR,
            f"{head.why_dead(anchor)}; the diff removed or moved its target",
        )
    return FindingKind.DEAD_ANCHOR, None


def _friction_message(
    question: _Question,
    *,
    deferral_predates: bool,
    back: _PutBack | None = None,
    written: bool = False,
) -> str:
    """What a question nothing answers says: a deferral put back covers only what the
    entry it puts back did (`back`), and a written-back `at` (`written`) answered only
    what its revalidation saw (COR-050 points 3 and 4)."""
    if question.anchor is None:
        return f"{question.subject}, which needs a revalidation (a new `at`) in the same change"
    if back is not None:
        since = "" if back.commit is None else f" (since {back.commit.short})"
        return (
            f"{question.subject} and carries no answer: its deferral repeats one it carried "
            f"before{since}, which covers only what that one did — revalidate the artefact, or "
            f"defer with a new reason"
        )
    if written:
        return (
            f"{question.subject} — that revalidation answered only what it saw; revalidate the "
            f"artefact, or defer the anchor"
        )
    if deferral_predates:
        return (
            f"{question.subject} and carries no answer: its deferral predates this diff, so it "
            f"covers only earlier changes — revalidate the artefact"
        )
    return f"{question.subject} and carries no answer: revalidate the artefact, or defer the anchor"


# --- the answers the change wrote ------------------------------------------------


def _written_outcome(artefact: Artefact) -> str | None:
    """A revalidation's `outcome` as the answers list gives it: `updated` or `unchanged`,
    else `None`."""
    outcome = revalidated_field(artefact, "outcome")
    return outcome if outcome in (Answer.UPDATED.value, Answer.UNCHANGED.value) else None


def _revalidation_fields(artefact: Artefact) -> tuple[Any, Any, str | None]:
    """What a revalidation is listed on: the parsed `at`, the `outcome` and the folded
    `unchanged-because`, an absent one counting as a value."""
    return parsed_at(artefact), revalidated_field(artefact, "outcome"), _because(artefact)


def _reason(artefact: Artefact, deferral: Deferral) -> str | None:
    """The folded reason of one deferral entry, `None` when it has none."""
    return entry_reason(artefact, deferral) or None


def _written_answers(
    artefact: Artefact,
    before: Artefact | None,
    questions: Sequence[_Question],
    judged: _Judged,
) -> list[WrittenAnswer]:
    """The answers the change wrote in one head artefact's block, read against its base
    counterpart `before` (`None` when it has none), the `questions` the diff asked it and
    how the check judged them (`_judge`): its revalidation, its deferrals by anchor, then
    its reason for having no anchors (COR-050 points 1, 3 and 4).

    - A **revalidation** is listed where the parsed `at`, the `outcome` or the
      folded `unchanged-because` differs — an absent one counting as a value, so
      a block added to an existing artefact is listed. Where `at` changed to a
      new value it `stands` or is a `bump`, as the check judges it
      (`_revalidation`), and names each deferral entry it kept; where it was
      written back to a value the artefact carried before, it is
      `written-back` and answers nothing (point 3); where `at` did not change,
      it is `edited`. It is asked for only where it stands.
    - A **deferral** entry is listed where the base defers its anchor in no
      entry (`stands`, or `written-back` where it puts back an entry the
      artefact carried before, point 4), or in none with its folded reason
      (`edited`). Every entry is read, so an anchor deferred twice — a
      validation error (COR-050 point 4) — lists each entry carrying words the
      base did not; of an anchor's entries introduced, the first is the one
      the check reads, asked for where it answered a question.
    - A **reason for having no anchors** is listed where it was added or differs.
    - A **new** artefact lists only what carries words — its `unchanged-because`,
      each deferral entry, its `unanchored-because` — never a bare `at`; nothing
      in it was asked for.

    What the change removed is not listed.
    """

    def entry(
        answer: str | None,
        anchor: Anchor | None,
        reason: str | None,
        *,
        status: AnswerStatus = AnswerStatus.STANDS,
        asked: bool = False,
        kept: tuple[KeptDeferral, ...] = (),
    ) -> WrittenAnswer:
        return WrittenAnswer(
            artefact.id,
            artefact.location,
            answer,
            anchor,
            reason,
            kept,
            asked,
            status,
            new=before is None,
        )

    # By anchor, an anchor's entries in written order (the sort is stable).
    deferrals = sorted(artefact.deferrals, key=lambda d: (d.anchor.kind, d.anchor.value))
    entries: list[WrittenAnswer] = []
    if before is None:
        because = _because(artefact)
        if because is not None:
            entries.append(entry(_written_outcome(artefact), None, because))
        entries.extend(
            entry(Answer.DEFERRED.value, d.anchor, _reason(artefact, d)) for d in deferrals
        )
    else:
        revalidation = judged.revalidation
        reasons_before: dict[Anchor, set[str | None]] = {}
        for deferral in before.deferrals:
            reasons_before.setdefault(deferral.anchor, set()).add(_reason(before, deferral))
        if _revalidation_fields(artefact) != _revalidation_fields(before):
            kept: tuple[KeptDeferral, ...] = ()
            if judged.written_back:
                status = AnswerStatus.WRITTEN_BACK
            elif revalidation is None:
                status = AnswerStatus.EDITED
            else:
                status = AnswerStatus.BUMP if revalidation.answer is None else AnswerStatus.STANDS
                kept = tuple(
                    KeptDeferral(d.anchor, _reason(artefact, d))
                    for d in deferrals
                    if d.anchor in reasons_before
                )
            entries.append(
                entry(
                    _written_outcome(artefact),
                    None,
                    _because(artefact),
                    status=status,
                    asked=bool(questions) and status is AnswerStatus.STANDS,
                    kept=kept,
                )
            )
        introduced: set[Anchor] = set()  # the anchors whose first entry was listed
        for deferral in deferrals:
            anchor = deferral.anchor
            reason = _reason(artefact, deferral)
            carried = reasons_before.get(anchor)
            if carried is None:
                asked = anchor in judged.covering and anchor not in introduced
                introduced.add(anchor)
                status = (
                    AnswerStatus.WRITTEN_BACK if anchor in judged.put_back else AnswerStatus.STANDS
                )
                entries.append(
                    entry(Answer.DEFERRED.value, anchor, reason, status=status, asked=asked)
                )
            elif reason not in carried:
                entries.append(
                    entry(Answer.DEFERRED.value, anchor, reason, status=AnswerStatus.EDITED)
                )
    unanchored = artefact.unanchored_because
    if unanchored is not None and (before is None or unanchored != before.unanchored_because):
        entries.append(entry(UNANCHORED, None, unanchored))
    return entries


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


class _NamedHeadKinds(AnchorKinds):
    """The anchor kinds of a head named with `--head` (`named_head`), and what their
    resolvers answer for it, read against that commit's files and naming it.

    A resolver is a command run in the working tree, which reads what is on disk:
    it is never read from a commit. So one runs only where the working tree is
    the commit named — HEAD at it, nothing uncommitted — and anywhere else the
    check refuses (`FrictionCheckError`) rather than read the disk as that commit.
    Only an anchor whose resolver would run is refused; an anchor of a core kind,
    or of a kind nothing may resolve, reads the same from any checkout.
    """

    def __init__(
        self,
        target_root: Path,
        registry: Mapping[str, ResolverCommand],
        files: Collection[str],
        head: HeadState,
    ) -> None:
        super().__init__(
            target_root, registry, files, f"commit {head.commit[:SHORT]} ({head.name})"
        )
        self._head = head
        self._elsewhere: str | None = None
        self._checked = False

    def resolve(self, anchor: Anchor) -> AnchorResolution:
        if anchor.kind not in CORE_ANCHOR_KINDS and self.unresolved(anchor.kind) is None:
            elsewhere = self._working_tree_elsewhere()
            if elsewhere is not None:
                name = self._head.name
                raise FrictionCheckError(
                    f"--head {name}: the anchor {anchor.kind} {anchor.value!r} is resolved by "
                    f"its capability's command, which runs in the working tree and reads what "
                    f"is there — and the working tree is not {name} ({elsewhere}). Run from a "
                    f"checkout at {name}: HEAD at {self._head.commit[:SHORT]}, nothing "
                    f"uncommitted."
                )
        return super().resolve(anchor)

    def _working_tree_elsewhere(self) -> str | None:
        """How the working tree differs from the commit named, or `None` when it is that
        commit; asked once, when the first resolver would run."""
        if not self._checked:
            self._checked = True
            at = commit_of(self.target_root, "HEAD")
            if at != self._head.commit:
                self._elsewhere = (
                    "HEAD names no commit" if at is None else f"HEAD is at {at[:SHORT]}"
                )
            else:
                uncommitted = uncommitted_paths(self.target_root)
                if uncommitted:
                    self._elsewhere = counted(uncommitted, "uncommitted path", "uncommitted paths")
        return self._elsewhere


class _Counts(NamedTuple):
    """What the head's discovery found: places, artefacts, and those carrying the container."""

    places: int
    artefacts: int
    carrying: int


def run_change_check(
    target_root: Path,
    base_ref: str | None = None,
    *,
    registry: Mapping[str, ResolverCommand] | None = None,
    resolved: default_branch.Base | None = None,
    named: HeadState | None = None,
) -> ChangeCheck:
    """Run the change check of the working tree — or of the commit `named` with `--head`
    (`named_head`), read from git objects — against the merge-base of `base_ref` with it;
    without one, `$PKIT_CHECK_BASE`, else the default branch (COR-054 point 3).
    `resolved` is that base when the caller has read it already (`resolve_base`).
    The anchor kinds are the registry's, the head's read from the package
    metadata on disk — a `named` head's from that commit — and the base's from
    the base commit; a `registry` handed in stands for both. A `named` head's
    resolvers run only where the working tree is that commit (`_NamedHeadKinds`).

    Raises `FrictionCheckError` when it cannot run — outside a git repository,
    before the first commit, or with a base that does not resolve — except
    while dormant, where there is nothing to compare and a missing base is
    only left out of the report.
    """
    head_tree: RepositoryTree = (
        WorkingTree(target_root) if named is None else CommitTree(target_root, named.commit)
    )
    head_discovery = discover_artefacts(target_root, tree=head_tree)
    settings = head_discovery.settings
    counts = _Counts(
        len(head_discovery.places),
        len(head_discovery.artefacts),
        len(head_discovery.with_container),
    )
    if head_discovery.is_dormant:
        dormant_base, dormant_head = _dormant_context(target_root, base_ref, resolved, named)
        return ChangeCheck(
            mode=settings.mode_or_default,
            mode_as_written=settings.mode,
            dormant=True,
            base=dormant_base,
            head=dormant_head,
            findings=(),
            answers=(),
            unreadable=(),
            places=counts.places,
            artefacts=counts.artefacts,
            carrying=counts.carrying,
        )

    base_state = resolve_base(target_root, base_ref, resolved=resolved, head=named)
    diff = read_diff(target_root, base_state.commit, named)
    base_tree = CommitTree(target_root, base_state.commit)
    head = Side(target_root, head_tree, head_discovery)
    base = Side(target_root, base_tree, discover_artefacts(target_root, tree=base_tree))
    if named is None:
        kinds = AnchorKinds(
            target_root,
            registered_anchor_kinds(target_root) if registry is None else registry,
            head.files,
        )
    else:
        kinds = _NamedHeadKinds(
            target_root,
            registered_anchor_kinds(target_root, head_tree) if registry is None else registry,
            head.files,
            named,
        )

    @functools.cache
    def base_registry() -> Mapping[str, ResolverCommand]:
        """The base's registrations, read from the base commit when first asked for."""
        return registered_anchor_kinds(target_root, base_tree) if registry is None else registry

    def resolved_at_base(kind: str) -> bool:
        return unresolved_kind_reason(kind, base_registry()) is None

    head_state = HeadState(head_commit(target_root), diff.uncommitted) if named is None else named
    findings: list[Finding] = []
    if base_state.outdated:
        findings.append(
            Finding(FindingKind.OUTDATED_BASE, _outdated_message(base_state, head_state))
        )
    unreadable = base.settings.exclude_unreadable
    if unreadable is not None:
        # What the base left out cannot be told: read it as head, never as leaving nothing out.
        base = base.read_under(head.settings)
        findings.append(
            Finding(
                FindingKind.UNREADABLE,
                f"`friction.exclude` does not read at the base ({unreadable}); the base is read "
                f"under head's, so a change to it in this diff asks nothing",
                location=_config_path(target_root),
            )
        )
    counterparts = _counterparts(head, base, diff)
    answers: list[WrittenAnswer] = []
    behind = _Behind(target_root, base_state, named, head)
    try:
        behind.prefetch(
            ((head_discovery.artefacts[index], before) for index, before in counterparts.items()),
            diff,
        )
        for index in truth_chain_order(head_discovery):
            artefact = head_discovery.artefacts[index]
            if artefact.has_friction_block:
                before = counterparts.get(index)
                found, questions, judgement = _judge(
                    artefact, before, head, base, diff, kinds, resolved_at_base, behind
                )
                findings.extend(found)
                answers.extend(_written_answers(artefact, before, questions, judgement))
    finally:
        behind.close()
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
        head=head_state,
        findings=tuple(findings),
        answers=tuple(answers),
        unreadable=tuple(sorted({u.path for u in head_discovery.unreadable})),
        shallow=behind.shallow,
        cut=tuple(behind.cut),
        places=counts.places,
        artefacts=counts.artefacts,
        carrying=counts.carrying,
    )


def _config_path(root: Path) -> str:
    """The backbone configuration file, repository-relative: where `friction.exclude` is."""
    return project_config_path(root).relative_to(root).as_posix()


def _dormant_context(
    root: Path,
    base_ref: str | None,
    resolved: default_branch.Base | None,
    named: HeadState | None = None,
) -> tuple[BaseState | None, HeadState | None]:
    """What a dormant run can say about its base and head; it demands neither (point 15)."""
    try:
        base: BaseState | None = resolve_base(root, base_ref, resolved=resolved, head=named)
    except FrictionCheckError:
        base = None
    if named is not None:
        return base, named
    try:
        commit = commit_of(root, "HEAD")
        head = None if commit is None else HeadState(commit, uncommitted_paths(root))
    except FrictionCheckError:
        head = None
    return base, head


def _outdated_message(base: BaseState, head: HeadState) -> str:
    return (
        f"the base {base.ref} is at {base.tip[:SHORT]}, which is not an ancestor of "
        f"{head.name}: it moved on after this branch left it at {base.commit[:SHORT]}; results "
        f"hold only against an up-to-date base — merge or rebase onto {base.ref}, then run again"
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
        "answers": [answer.as_json() for answer in result.answers],
        "unreadable": list(result.unreadable),
        "history": (
            None if result.shallow is None else {"shallow": result.shallow, "cut": list(result.cut)}
        ),
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


_LEGEND: dict[FindingKind, str] = {
    FindingKind.FRICTION: (
        "an anchor, the anchor list or the artefact's place changed, or `friction.exclude` let "
        "it back in, and no answer stands"
    ),
    FindingKind.ANSWERED: "the artefact answers the change: updated, unchanged, deferred or new",
    FindingKind.REVALIDATED: "revalidated in this diff with no changed anchor",
    FindingKind.BUMP: "`at` changed with nothing behind it",
    FindingKind.DEAD_ANCHOR: "the diff left an anchor resolving to nothing",
    FindingKind.DEAD_UNATTRIBUTED: (
        "an anchor the diff kept resolves to nothing, and whether the diff did it cannot be told"
        + ("" if FindingKind.DEAD_UNATTRIBUTED in FAILING_KINDS else ": reported only")
    ),
    FindingKind.UNRESOLVED_KIND: (
        "an anchor of a kind nothing installed resolves: added in the diff, or its resolver "
        "taken away by it"
    ),
    FindingKind.NO_ANSWER: (
        "a resolver gave no answer, so its anchor could not be checked: a second run may clear it"
    ),
    FindingKind.LEFT_OUT: (
        "`friction.exclude` took files from an anchor and the diff changes none: reported only"
    ),
    FindingKind.UNREADABLE: "front matter, or the base's `friction.exclude`, the check cannot read",
}

_MODE_GLOSS = {
    ENFORCING: "fails on friction, dead anchors, unresolved kinds, missing answers and bumps; an "
    "outdated base only reports",
    "warning": "reports and passes",
}


def render_human(result: ChangeCheck) -> str:
    """The read view: header, findings grouped by artefact upstream first, result, legend,
    and last the answers the change wrote, word for word — what the repository wrote shown
    with any character a terminal would act on escaped (`_shown`)."""
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
            lines.append(f"  {_shown(current or '')}")
        cells = f"{finding.kind.value:{kind_width}}  {_anchor_cell(finding):{anchor_width}}"
        lines.append(f"    {cells}  {_shown(finding.message)}".rstrip())
    for finding in unreadable:
        lines.append(f"  {_shown(finding.location or '')}")
        lines.append(f"    {finding.kind.value:{kind_width}}  {_shown(finding.message)}")

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
            "  pkit friction check --json   the same findings and answers, machine-readable",
            "  pkit validate                the blocks, deferrals and cycles themselves",
            "",
            *_answers_lines(result),
        ]
    )
    return "\n".join(lines) + "\n"


def _anchor_cell(finding: Finding) -> str:
    if finding.anchor is None:
        return "—"
    return _shown(f"{finding.anchor.kind} {finding.anchor.value}")


def _shown(text: str) -> str:
    """`text` as the human view prints it: each character that is not printable — a
    control character such as an escape, a bidirectional override, a zero-width
    character — written as its escape (`\\x1b`, `\\u202e`), never raw. Words read
    from an artefact then cannot move the cursor, erase a line or reorder what
    follows on the terminal the list is read on; the JSON document escapes them
    itself."""
    if text.isprintable():
        return text
    return "".join(ch if ch.isprintable() else ascii(ch)[1:-1] for ch in text)


def _answers_lines(result: ChangeCheck) -> list[str]:
    """The closing section: one line per answer the change wrote, its words in full."""
    lines = [
        cli_render.style("heading", "Answers written in this change")
        + cli_render.style("muted", " — read from the artefacts, word for word")
    ]
    lines.extend(f"  {_answer_line(answer)}" for answer in result.answers)
    if not result.answers:
        lines.append("  none")
    if result.unreadable:
        files = counted(len(result.unreadable), "file", "files")
        lines.append(
            f"  {files} whose front matter does not parse could not be read for answers "
            f"(`unreadable` above)"
        )
    return lines


def _answer_line(answer: WrittenAnswer) -> str:
    """`<location>  <answer> [<anchor>] (<flags>) — "<words>"`, every word written, any
    character that is not printable escaped (`_shown`)."""
    what = answer.answer or "no outcome"
    if answer.anchor is not None:
        what += f" {answer.anchor.kind} {answer.anchor.value}"
    flags = ["new"] if answer.new else []
    if not answer.asked:
        flags.append("not asked for")
    if answer.status is AnswerStatus.BUMP:
        flags.append("the diff does not bear it out")
    if answer.status is AnswerStatus.EDITED:
        flags.append("edited without a revalidation")
    if answer.status is AnswerStatus.WRITTEN_BACK:
        flags.append(
            "written back: an `at` it carried before, which answers nothing"
            if answer.anchor is None
            else "written back: an entry it carried before, which covers only what that one did"
        )
    flags.extend(
        f"keeps the deferral of {kept.anchor.kind} {kept.anchor.value}"
        + ("" if kept.reason is None else f' — "{kept.reason}"')
        for kept in answer.kept
    )
    line = f"{answer.location}  {what}"
    if flags:
        line += f" ({'; '.join(flags)})"
    return _shown(line if answer.reason is None else f'{line} — "{answer.reason}"')


def _header_lines(result: ChangeCheck) -> list[str]:
    lines: list[str] = []
    against = "HEAD" if result.head is None else result.head.name
    if result.base is not None:
        lines.append(
            f"  Base: {result.base.ref} at {result.base.commit[:SHORT]}"
            + cli_render.style("muted", f"   (merge-base with {against})")
        )
    if result.head is not None and result.head.named is not None:
        lines.append(
            f"  Head: {result.head.commit[:SHORT]} ({result.head.named})"
            + cli_render.style("muted", "   (--head: the working tree is not read)")
        )
    elif result.head is not None:
        uncommitted = counted(result.head.uncommitted, "uncommitted path", "uncommitted paths")
        working = (
            f"+ working tree, {uncommitted}" if result.head.uncommitted else "(working tree clean)"
        )
        lines.append(f"  Head: {result.head.commit[:SHORT]} {working}")
    if result.shallow:
        read = counted(len(result.cut), "artefact", "artefacts")
        named = f" ({_shown(_listed(result.cut))})" if result.cut else ""
        lines.append(f"  History: shallow — {read} read without history beyond the cut{named}")
    gloss = _MODE_GLOSS.get(result.mode, "")
    lines.append(f"  Mode: {result.mode}" + cli_render.style("muted", f"   ({gloss})"))
    lines.extend(_mode_warning(result))
    for finding in result.findings:
        if finding.kind is FindingKind.OUTDATED_BASE:
            lines.append(f"  ⚠ outdated base: {_shown(finding.message)}")
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
    """What the run found of the kinds enforcing mode fails on (`FAILING_KINDS`), counted."""
    parts = [
        (FindingKind.FRICTION, "friction", "friction"),
        (FindingKind.DEAD_ANCHOR, "dead anchor", "dead anchors"),
        (FindingKind.DEAD_UNATTRIBUTED, "dead anchor kept", "dead anchors kept"),
        (FindingKind.UNRESOLVED_KIND, "unresolved kind", "unresolved kinds"),
        (FindingKind.NO_ANSWER, "missing answer", "missing answers"),
        (FindingKind.BUMP, "bump", "bumps"),
    ]
    return ", ".join(
        counted(result.count(kind), one, many)
        for kind, one, many in parts
        if kind in FAILING_KINDS and result.count(kind)
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
