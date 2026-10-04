"""The whole-repository friction check: `pkit friction check --all` (COR-050 points 3–9, 11–13).

Every artefact in the declared places at HEAD is checked, at HEAD, against
its **revalidation point** with the rule of point 5: an anchor has changed
when what it stands on differs between the two. The points come from git,
never from a ledger (point 9), through `friction_history`:

- the *revalidation point* is the commit, renames followed, where the
  artefact first carried the parsed `at` it carries — a version carrying it
  where no parent did, and of which no other such version is an ancestor;
  for an artefact without `at`, the commit that first introduced its block
  (point 3). A commit that writes back a value the artefact carried before —
  the revert of a revalidation — is never the point, nor is one side's
  revalidation where a merge kept the other side's, however recent its date.
  Where versions that do not descend from one another each first carried
  the value, each is a point, and an anchor has changed only where it
  differs from every one. The value is read in whatever spelling YAML's
  timestamp grammar allows (`friction_history.stamps_in`), so restating it
  in another is no revalidation. A move after the point with no revalidation
  is reported, since rename detection may hide earlier changes.
- a *deferral point* is the commit that first introduced the deferral entry,
  by anchor kind and value; rewording its reason does not move it, and an
  entry put back with an anchor and a reason the artefact carried before
  keeps the point of the entry it puts back (point 4). A deferral covers its
  anchor as it stood at its point, and answers nothing once a revalidation
  point reaches it.

**When an anchor changed.** Each anchor is measured from its *answering
states* (`_Judge.answering`): every revalidation point, and its deferral
point where no revalidation point reaches it. The anchor is judged as a
whole (`friction_history.changed_since`, the rule the change check judges
the points of a written-back `at` by): it has changed only where what it
stands on differs from what it stood on at every answering state — at
each, some part of it differs, not necessarily the same — never part by
part. A part differs from a state (`friction_history.differs`) as follows:
a path anchor's files by mode and object — HEAD's from its tree, a state's
from the state's tree objects, read through `git cat-file --batch`
(`TreeReader`) — a record's file and a registered kind's files the same
way, followed across renames; an artefact anchor's target by its content,
read at the state's commit. An edit put back, however many commits made and
undid it, is no change. The commits the history lists only name each
state's candidates — the paths commits after that state touched — and date
the debt: each part is measured from the state it differs from, its origin
the oldest change no commit put back to what it was there
(`friction_history.origin`), and the anchor's debt is dated where it came
to differ from every state — of each state's oldest origin, the newest.

**Reading history — from git alone, per file and bounded.** One `git log
--raw -M -c` from HEAD lists every commit with the paths it touched and each
file's mode and object (`read_history`) — a merge commit with the paths it
changed against every parent, git's combined diff, so what a merge itself
wrote is read like any other commit; everything else is matched in memory.
A file's earlier versions are read through one `git cat-file --batch`
process (`BlobReader`) by object id, each parsed once by the same reading as
the present (`parse_artefacts`) and only where its bytes could hold what the
walk looks for. The walk goes back to where the file, or the entry in it,
was last added, since only there is it known where the value it carries was
first carried.

**What it reports** (points 7, 8, 11, 12), per artefact, upstream first
along artefact anchors: *stale* — an anchor changed since its answering
states, or the artefact moved, or was let back in by `friction.exclude`,
after the point with no revalidation — with its origin (author, date,
change); *deferred* — every deferral, with its point's origin and, in the
human view, its age; *left-out* — a widening of `friction.exclude` since the
point that asks nothing; dead anchors, unresolved kinds and resolvers that
gave no answer, all of them, not only a change's; *over-broad* anchors. An
artefact with an anchor that cannot be resolved — its kind has no resolver
that may run, or its resolver gave no answer — is **not judged**: its state
is `unresolved`, never `current`, as an artefact whose points lie beyond a
shallow clone is `unreachable` (point 2). Then the two measures: unanchored
artefacts within the places — the forgotten ones counted, and those whose
block gives the reason a person accepted them with none
(`unanchored-because`, point 1) listed apart with it, never counted — and
uncovered surface, excluded paths ignored. It never fails (point 12): exit 0
in either mode. Dormant while no place is declared.

**An artefact under an excluded path** (point 7) is left out of the measures
— the unanchored listing and its count — and so of the debt: it is never
judged stale or deferred and has no state. What it declares is still
checked, since a dead anchor is an error and never silence: its dead
anchors, unresolved kinds and over-broad anchors are reported. Whether it is
excluded is read from the artefact, as discovery decided it
(`Artefact.excluded_by`), never by matching its path again.

**Each state under its own exclusions** (point 7). Every answering state is
read under the `friction.exclude` its commit declared — its settings alone,
never a discovery over it (`_Judge.settings_of`) — and HEAD under its own, as
the change check reads its base and head: a deferral point under its own, a
revalidation point under its own. A path anchor's file counts where both
leave it in. Where the exclusions changed between the state and HEAD
(`exclusion_change`), the files the anchor stood on are sought among HEAD's
and every path touched since the state, so no commit's listing is read: a
narrowing — a file it stands on at HEAD that the state left out — is a
change from the commit that let the file in; a widening — a file it stood on
that HEAD leaves out — takes the file as it stood when the newest widening
after the state took it, and is a change where that differs from what it was
at the state, dated from the change before the widening, never from the
widening; otherwise it is reported, against the newest revalidation point.
So a change made while a file was left out never counts where the state or
HEAD leaves it out, and a widening never erases a change nobody answered. An
artefact a narrowing let back in after its point is stale from that commit,
as the change check asked it to revalidate there. A path anchor dead because
a widening left out every file it stood on says so, `excluded since
<commit>`. A state whose exclusions do not read is read under HEAD's and
reported, never read as leaving nothing out.

A shallow clone whose history stops where the file already carries the value
is reported for the artefacts concerned, never guessed at; a value first
carried inside the clone is read as first carried there, and the artefact's
report says the clone was cut (`ArtefactReport.cut`).

The check writes nothing (point 13). The computations it shares with the
change check — discovery, content, the parsed marker, what a path pattern
stands on (`Side.stands_on`), what a dead anchor is, truth-chain order, the
walk to a point — have their one home in `friction_check`,
`friction_discovery` and `friction_history` (ADR-057 point 2).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from project_kit import cli_render
from project_kit.friction_check import (
    ExclusionChange,
    HeadState,
    Listing,
    Side,
    anchors_of,
    counted,
    exclusion_change,
    left_out_message,
    truth_chain_order,
    uncommitted_paths,
)
from project_kit.friction_discovery import (
    CORE_ANCHOR_KINDS,
    HEAD_STATE,
    Anchor,
    AnchorKinds,
    Artefact,
    Discovery,
    FrictionSettings,
    ResolverCommand,
    content,
    deferral_reason,
    discover_artefacts,
    pattern_matcher,
    read_friction_settings,
    registered_anchor_kinds,
)
from project_kit.friction_git import (
    SHORT,
    BlobReader,
    CommitTree,
    FrictionCheckError,
    TreeEntry,
    TreeReader,
    commit_of,
)
from project_kit.friction_history import (
    Commit,
    History,
    MergeEntry,
    Points,
    Version,
    Walker,
    changed,
    changed_since,
    differs,
    origin,
    read_history,
    shallow_commits,
)
from project_kit.project_config import PROJECT_CONFIG_RELPATH

#: The share of the tracked files (excluded paths left out) above which a
#: path anchor is over-broad (COR-050 point 7: "broad enough to match most
#: changes"). *Most* is more than half. The share of files stands in for the
#: share of changes: changes are not spread evenly over files, but the file
#: share is what HEAD alone can answer, deterministically, without guessing
#: at what will change next.
OVER_BROAD_SHARE = 0.5

# The file a state's `friction.exclude` is written in: a commit that changes the
# exclusions touches it (COR-050 point 14).
_CONFIG = PROJECT_CONFIG_RELPATH.as_posix()

#: How the stale finding on an artefact a narrowed `friction.exclude` let back in
#: after its revalidation point opens (COR-050 point 7); like a move's, it names no anchor.
LET_BACK_IN = "let back in by `friction.exclude`"


# --- findings ----------------------------------------------------------------


class RepositoryFindingKind(Enum):
    """What a finding of the whole-repository check is; the `kind` field of the JSON output."""

    STALE = "stale"
    DEFERRED = "deferred"
    LEFT_OUT = "left-out"
    DEAD_ANCHOR = "dead-anchor"
    UNRESOLVED_KIND = "unresolved-kind"  # a kind nothing installed may resolve
    NO_ANSWER = "no-answer"  # a registered kind's resolver gave no answer
    OVER_BROAD = "over-broad"
    UNREACHABLE = "unreachable"
    UNREADABLE = "unreadable"


#: The findings that leave an anchor unresolved: whether what it denotes changed cannot
#: be told, so its artefact is not judged (`ArtefactState.UNRESOLVED`; COR-050 point 2).
UNRESOLVED_KINDS = frozenset(
    {RepositoryFindingKind.UNRESOLVED_KIND, RepositoryFindingKind.NO_ANSWER}
)


class ArtefactState(Enum):
    """What the check found for one artefact with anchors (point 10).

    Two states say the artefact was not judged, and win over the rest:
    `UNREACHABLE` — a point of it lies beyond a shallow clone's history — and
    then `UNRESOLVED` — an anchor of it cannot be resolved (`UNRESOLVED_KINDS`),
    so no reading of it is ever `current`, and no `since` is recorded that the
    unread anchor could predate. Then stale wins over deferred. The stale and
    deferred findings of an unresolved artefact's other anchors are still
    reported.
    """

    CURRENT = "current"
    STALE = "stale"
    DEFERRED = "deferred"
    UNREACHABLE = "unreachable"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class RepositoryFinding:
    """One finding: about an artefact, with the commit it originates in where it has one."""

    kind: RepositoryFindingKind
    message: str
    artefact: str | None = None  # the artefact's id
    location: str | None = None  # `path`, or `path#id` for a collection entry
    anchor: Anchor | None = None
    origin: Commit | None = None

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
            "origin": None if self.origin is None else self.origin.as_json(),
            "message": self.message,
        }


@dataclass(frozen=True)
class ArtefactReport:
    """One checked artefact: its points, as derived from git, and its state.

    `revalidation_points` are every revalidation point, newest first — several
    where lines of work that do not descend from one another each first carried
    the value (COR-050 point 3) — and `revalidation_point` the newest of them,
    the one a finding's message names. `cut` says its file's history reaches a
    shallow clone's cut, so the value it carries was read as first carried
    inside the clone.
    """

    artefact: str
    location: str
    state: ArtefactState
    revalidation_point: Commit | None  # `None` when unreachable
    deferral_points: tuple[tuple[Anchor, Commit | None], ...]  # in written order
    cut: bool = False
    revalidation_points: tuple[Commit, ...] = ()

    def as_json(self) -> dict[str, Any]:
        return {
            "artefact": self.artefact,
            "location": self.location,
            "cut": self.cut,
            "state": self.state.value,
            "revalidation_point": (
                None if self.revalidation_point is None else self.revalidation_point.as_json()
            ),
            "revalidation_points": [point.as_json() for point in self.revalidation_points],
            "deferral_points": [
                {
                    "anchor": {"kind": anchor.kind, "value": anchor.value},
                    "point": None if point is None else point.as_json(),
                }
                for anchor, point in self.deferral_points
            ],
        }


@dataclass(frozen=True)
class AcceptedUnanchored:
    """An artefact with no anchors whose block gives the reason a person accepted it so.

    The unanchored measure lists it apart from the forgotten ones and never
    counts it (COR-050 points 1 and 8). `reason` is its `unanchored-because`,
    whitespace folded.
    """

    artefact: str  # the artefact's id
    location: str  # `path`, or `path#id` for a collection entry
    reason: str

    def as_json(self) -> dict[str, str]:
        return {"artefact": self.artefact, "location": self.location, "reason": self.reason}


@dataclass(frozen=True)
class RepositoryCheck:
    """The outcome of one run of the whole-repository check. It never fails."""

    mode: str  # the mode in effect: shown, since the check fails in neither
    mode_as_written: Any
    dormant: bool
    places: int
    artefacts: int
    carrying: int  # artefacts carrying the container
    head: HeadState | None  # `None` only while dormant
    shallow: bool | None  # `None` only while dormant
    artefact_reports: tuple[ArtefactReport, ...]  # in report order
    findings: tuple[RepositoryFinding, ...]  # in report order
    # Locations of artefacts without anchors and without an accepted reason — the
    # forgotten ones, the only ones counted — excluded ones left out (point 8).
    unanchored: tuple[str, ...]
    # Artefacts without anchors whose block gives the reason they have none: listed
    # apart, never counted (points 1 and 8); excluded ones left out.
    accepted_unanchored: tuple[AcceptedUnanchored, ...]
    excluded: int  # artefacts under an excluded path, left out of the measures (point 7)
    surface: int  # paths of the declared surface at HEAD, excluded ones left out
    uncovered: tuple[str, ...]  # those of them no artefact anchors to (point 8)

    def count(self, kind: RepositoryFindingKind) -> int:
        return sum(1 for f in self.findings if f.kind is kind)

    def state_count(self, state: ArtefactState) -> int:
        return sum(1 for r in self.artefact_reports if r.state is state)

    @property
    def failed(self) -> bool:
        return False

    @property
    def exit_code(self) -> int:
        return 0


class _BlobTree:
    """One commit as discovery reads its settings (`RepositoryTree`): each file on
    request through the check's one `BlobReader`, the listing only if asked for.

    Settings are read from a handful of files — the configuration, the manifest,
    each capability's package metadata — so no `git ls-tree` and no process per
    file is spent on them. A link reads as text that is no mapping, as the
    settings reader reads an unreadable file: the same settings `CommitTree` gives.
    """

    def __init__(self, root: Path, commit: str, blobs: BlobReader) -> None:
        self._root = root
        self._commit = commit
        self._blobs = blobs
        self._listed: Sequence[str] | None = None

    def files(self) -> Sequence[str]:
        if self._listed is None:
            self._listed = CommitTree(self._root, self._commit).files()
        return self._listed

    def read_bytes(self, paths: Sequence[str]) -> Mapping[str, bytes | None]:
        return {rel: self._blobs.read(self._commit, rel) for rel in paths}


def _excludes_nothing(_rel: str) -> bool:
    """A state with no configuration file yet: no path is excluded."""
    return False


# --- points and changes, per artefact ----------------------------------------


@dataclass(frozen=True)
class Change:
    """How a live anchor changed since what answers it (COR-050 points 5 and 9) — since
    one answering state (`_Judge.since`), or since all of them (`_Judge.change`).

    `origin`: the log index of the commit the debt is dated from (`origin`).
    `commits`: the commits behind it — since one state, each after it that
    touched a part of the anchor that differs from what it was there; since
    all of them, those of these after what every state covers, what `explain`
    lists behind the finding with its origin.
    """

    origin: int
    commits: frozenset[int]


@dataclass(frozen=True)
class _Exclusion:
    """What `friction.exclude` changing between one answering state and HEAD did to one
    path anchor (COR-050 point 7), the state read under its own exclusions.

    `moved`: the change itself, the artefact's own names left out
    (`ExclusionChange`). `changed`: of the files it leaves out, each that,
    as it stood when the newest widening after the state took it, differs
    from what it was at the state, with the origin of that change; `touched`,
    the commits behind those. `while_out`: of the files it lets in, each
    changed while it was left out — no change to the anchor, but named — with
    the oldest such commit. `left_by`: the commits that left its files out.
    """

    moved: ExclusionChange
    changed: Mapping[str, int]
    while_out: Mapping[str, int]
    left_by: frozenset[int]
    touched: frozenset[int] = frozenset()

    @property
    def asks(self) -> bool:
        """Whether the change is the anchor's question: it narrows, or a file it
        leaves out changed while the anchor stood on it. A widening over files
        that did not change is reported, never owed."""
        return bool(self.moved.let_in or self.changed)

    def describe(self, commits: Sequence[Commit]) -> str:
        """`ExclusionChange.describe`, each file noted with the change that makes it matter."""
        notes = {
            rel: f"changed since its revalidation point ({commits[index].short})"
            for rel, index in self.changed.items()
        }
        notes.update(
            (rel, f"changed since it was left out ({commits[index].short})")
            for rel, index in self.while_out.items()
        )
        return self.moved.describe(notes)


class _Judge:
    """Applies COR-050 point 5 to one repository state against its history.

    Each state is read under its own exclusions (point 7): a commit's are what
    discovery's settings reader reads from it (`settings_of`), HEAD's are the
    head's — never a discovery over an older commit, since exclusions are all
    that is read from one. The methods that read a state take its log index:
    a revalidation point, or a deferral point no revalidation point reaches
    (`answering`).

    An anchor has changed where, as a whole, it differs from every answering
    state (`change`, by `changed_since`); a part of it differs from one
    (`since`) by its mode and object, for a file — HEAD's from its tree, a
    state's from the state's tree objects, read through `git cat-file
    --batch` (`TreeReader`) — and by its content as the state's commit holds
    it, for an artefact. The commits a history lists only name the
    candidates and date the debt (`origin`).
    """

    def __init__(
        self,
        head: Side,
        tree: CommitTree,
        history: History,
        walker: Walker,
        blobs: BlobReader,
        registry: Mapping[str, ResolverCommand],
    ) -> None:
        self.head = head
        self.head_tree = tree
        self.history = history
        self.walker = walker
        self.blobs = blobs
        self.trees = TreeReader(blobs)
        self.kinds = AnchorKinds(head.root, registry, head.files, HEAD_STATE)
        """The anchor kinds, as HEAD's registrations declare them, and each registered
        kind's anchors as their resolvers answered — once per anchor value for the run
        (COR-050 point 2), each answer read against HEAD's files: a resolver reads the
        files on disk, the one thing here that does, and a path HEAD does not hold —
        uncommitted work — is no answer, never a file with no history."""
        self.unreadable: dict[str, str] = {}
        """The revalidation points whose `friction.exclude` does not read, and why:
        each read under HEAD's instead, and reported (`unreadable_findings`)."""
        self._tracked = frozenset(rel for rel in head.files if not head.excluded(rel))
        self._head_sha = history.commits[0].sha if history.commits else ""
        self._head_config = blobs.read(self._head_sha, _CONFIG) if self._head_sha else None
        self._by_config: dict[bytes | None, FrictionSettings] = {}
        self._settings: dict[str, FrictionSettings] = {}
        self._as_head: dict[int, bool] = {}
        self._trees: dict[str, CommitTree] = {}
        self._matched: dict[str, tuple[frozenset[str], frozenset[str]]] = {}
        self._matching: dict[tuple[str, tuple[str, ...] | None], frozenset[str]] = {}
        self._after: dict[int, frozenset[str]] = {}
        self._moved: dict[tuple[str, int], ExclusionChange] = {}
        self._exclusions: dict[tuple[Anchor, int, frozenset[str]], _Exclusion] = {}
        self._flips: dict[int, tuple[FrictionSettings, list[Callable[[str], bool]]] | None] = {}

    # --- a state under its own exclusions ------------------------------------------

    def settings_of(self, sha: str) -> FrictionSettings:
        """The friction settings the commit `sha` declares, read as discovery reads a
        commit's (`read_friction_settings`); HEAD's are the head's own.

        Only their exclusions are read from them, and those come from the
        configuration file alone: commits holding the same file share one
        reading, so a history of many commits is read once per configuration.
        """
        if sha == self._head_sha:
            return self.head.settings
        found = self._settings.get(sha)
        if found is None:
            config = self.blobs.read(sha, _CONFIG)
            found = self._by_config.get(config)
            if found is None:
                if config is not None and config == self._head_config:
                    found = self.head.settings
                else:
                    root = self.head.root
                    found = read_friction_settings(root, _BlobTree(root, sha, self.blobs))
                self._by_config[config] = found
            self._settings[sha] = found
        return found

    def reads_as_head(self, point: int) -> bool:
        """Whether the revalidation point at `point` is read under HEAD's exclusions:
        it declares the same, or what it declares does not read — then it is recorded
        in `unreadable`, since a state that cannot be read is never read as one that
        leaves nothing out."""
        found = self._as_head.get(point)
        if found is None:
            head = self.head.settings
            sha = self.history.commits[point].sha
            settings = self.settings_of(sha)
            if settings.exclude_unreadable is not None and head.exclude_unreadable is None:
                self.unreadable.setdefault(sha, settings.exclude_unreadable)
            found = self._as_head[point] = (
                head.exclude_unreadable is not None
                or settings.exclude_unreadable is not None
                or settings is head
                or settings.excludes_as(head)
            )
        return found

    def point_settings(self, point: int) -> FrictionSettings:
        """The settings the revalidation point is read under (`reads_as_head`)."""
        if self.reads_as_head(point):
            return self.head.settings
        return self.settings_of(self.history.commits[point].sha)

    def tree(self, sha: str) -> CommitTree:
        found = self._trees.get(sha)
        if found is None:
            found = self._trees[sha] = CommitTree(self.head.root, sha)
        return found

    def matched_at(self, point: int, pattern: str) -> tuple[str, ...]:
        """The files of the revalidation point a path anchor's `pattern` stands on, under
        the point's own exclusions — listed from git objects, for `explain` alone."""
        sha = self.history.commits[point].sha
        return Listing(self.tree(sha).files(), self.point_settings(point)).matching(pattern)

    def stands_on(self, pattern: str, point: int) -> Callable[[str], bool]:
        """Whether a path anchor's `pattern` stands on a file both at the revalidation point
        and at HEAD, each under its own exclusions: a file whose change is the anchor's.
        Only the point's settings are read, never its files."""
        at_head = self.head.stands_on(pattern)
        if self.reads_as_head(point):
            return at_head
        excluded = self.settings_of(self.history.commits[point].sha).excluded
        return lambda rel: at_head(rel) and not excluded(rel)

    def _matched_by(self, pattern: str) -> tuple[frozenset[str], frozenset[str]]:
        """HEAD's files and the history's paths a path anchor's `pattern` matches,
        whatever excludes them — matched once per pattern."""
        found = self._matched.get(pattern)
        if found is None:
            match = pattern_matcher(pattern)
            found = self._matched[pattern] = (
                frozenset(filter(match, self.head.files)),
                frozenset(filter(match, self.history.paths)),
            )
        return found

    def _paths_after(self, point: int) -> frozenset[str]:
        found = self._after.get(point)
        if found is None:
            found = self._after[point] = self.history.paths_after(self.history.ancestors(point))
        return found

    def exclusion_change(self, anchor: Anchor, point: int) -> ExclusionChange:
        """What `friction.exclude` changing from the revalidation point to HEAD did to a
        path anchor (`exclusion_change`); empty for another kind, or where they read alike.

        The files it stood on are sought among HEAD's and every path touched
        since the point: a file the point held that nothing touched since is
        HEAD's still, so no commit's listing is read — and a file added since,
        changed while the anchor stood on it, and left out later is among
        them, its change never erased. The artefact's own names are the
        caller's to leave out (`ExclusionChange.less`).
        """
        if anchor.kind != "path" or self.reads_as_head(point):
            return ExclusionChange()
        key = (anchor.value, point)
        found = self._moved.get(key)
        if found is None:
            at_head, in_history = self._matched_by(anchor.value)
            since = at_head | (in_history & self._paths_after(point))
            before = Listing(since, self.settings_of(self.history.commits[point].sha))
            found = exclusion_change(anchor.value, before, Listing(at_head, self.head.settings))
            self._moved[key] = found
        return found

    def counts(self, index: int, rel: str) -> bool:
        """Whether the commit at `index` changed the file at `rel` as one an anchor stood
        on (COR-050 point 7): some parent of it left the file in — a change made while
        it was left out is not the anchor's — and it did not add the file excluded
        already. A state whose exclusions do not read leaves the file in: a change is
        never dropped for what cannot be told."""
        commit = self.history.commits[index]
        parents = [self.settings_of(parent) for parent in commit.parents]
        if parents and all(
            settings.exclude_unreadable is None and settings.excluded(rel) for settings in parents
        ):
            return False
        return not (self.history.added(index, rel) and self.settings_of(commit.sha).excluded(rel))

    def _flip(self, index: int) -> tuple[FrictionSettings, list[Callable[[str], bool]]] | None:
        """The settings a commit that touched the configuration declares, and whether each
        parent left a path out; `None` where it or every parent does not read."""
        if index in self._flips:
            return self._flips[index]
        commit = self.history.commits[index]
        now = self.settings_of(commit.sha)
        parents = [self.settings_of(parent) for parent in commit.parents]
        readable = [s.excluded for s in parents if s.exclude_unreadable is None]
        found = None
        if now.exclude_unreadable is None and (readable or not parents):
            found = (now, readable or [_excludes_nothing])
        self._flips[index] = found
        return found

    def flips(self, files: Sequence[str], covered: frozenset[int], *, excluded: bool) -> set[int]:
        """The commits outside `covered` whose `friction.exclude` left one of `files` out
        (`excluded`) or let one in, otherwise than every parent of it — a merge only
        where it wrote exclusions no parent had, as a merge's revalidation counts."""
        found: set[int] = set()
        if not files:
            return found
        for index in self.history.touched(_CONFIG):
            flip = None if index in covered else self._flip(index)
            if flip is None:
                continue
            now, parents = flip
            if any(
                now.excluded(rel) == excluded and all(was(rel) != excluded for was in parents)
                for rel in files
            ):
                found.add(index)
        return found

    def exclusion(self, anchor: Anchor, state: int, own: frozenset[str]) -> _Exclusion:
        """What `friction.exclude` changing between the answering state at `state` and HEAD
        did to a path anchor, the state read under its own exclusions (`_Exclusion`).

        A file a widening took from the anchor stands, in the later state, as it
        was when the newest widening after the state took it (COR-050 point 5):
        it is the anchor's question where that differs from what it was at the
        state, dated from the oldest change before the widening still standing
        (`origin`). What changed after, while it was left out, is not the
        anchor's.
        """
        key = (anchor, state, own)
        cached = self._exclusions.get(key)
        if cached is not None:
            return cached
        moved = self.left_out_since(anchor, state, own)
        covered = self.history.ancestors(state)
        sha = self.history.commits[state].sha
        changed: dict[str, int] = {}
        touched: set[int] = set()
        for rel in moved.left_out:
            taken = self.flips((rel,), covered, excluded=True)
            at = min(taken) if taken else None
            reference = (
                self.head_tree.entry(rel)
                if at is None
                else self.trees.entry(self.history.commits[at].sha, rel)
            )
            then = self.trees.entry(sha, rel)
            if not differs(reference, then):
                continue
            before = self.history.ancestors(at) if at is not None else None
            commits = [
                i
                for i in self.history.touched(rel)
                if i not in covered and (before is None or i in before)
            ]
            found = origin(
                self.history,
                commits,
                lambda c, rel=rel, then=then: self._result(c, rel) == then,
            )
            if found is not None:
                changed[rel] = found
                touched.update(commits)
        while_out: dict[str, int] = {}
        for rel in moved.let_in:
            out = [
                i for i in self.history.touched(rel) if i not in covered and not self.counts(i, rel)
            ]
            if out:
                while_out[rel] = max(out)
        left_by = frozenset(self.flips(moved.left_out, covered, excluded=True))
        found_exclusion = _Exclusion(moved, changed, while_out, left_by, frozenset(touched))
        self._exclusions[key] = found_exclusion
        return found_exclusion

    def left_out_since(self, anchor: Anchor, point: int, own: frozenset[str]) -> ExclusionChange:
        """`exclusion_change`, the artefact's own names left out, and of the files it leaves
        out only those the anchor stood on: the point held the file, or a commit since
        changed it while the anchor stood on it (`counts`). A file added already left
        out was never the anchor's, so no widening took it away."""
        moved = self.exclusion_change(anchor, point).less(own)
        if not moved.left_out:
            return moved
        reached = self.history.ancestors(point)
        after = self._paths_after(point)
        sha = self.history.commits[point].sha
        stood = tuple(
            rel
            for rel in moved.left_out
            if rel not in after  # untouched since the point: HEAD's file is the point's
            or self.blobs.read(sha, rel) is not None
            or any(i not in reached and self.counts(i, rel) for i in self.history.touched(rel))
        )
        return replace(moved, left_out=stood)

    def excluding_commit(self, anchor: Anchor, point: int, own: frozenset[str]) -> int | None:
        """For a path anchor dead at HEAD, the first commit after the revalidation point
        that changed `friction.exclude` to leave out files it stood on there, or `None` —
        the exclusion that is why it is dead."""
        left_out = self.left_out_since(anchor, point, own).left_out
        commits = self.flips(left_out, self.history.ancestors(point), excluded=True)
        return max(commits) if commits else None

    def let_back_in(self, artefact: Artefact, reached: frozenset[int]) -> int | None:
        """The first commit no revalidation point reaches (`reached`) whose
        `friction.exclude` let the artefact's file back in (COR-050 point 7), or `None`:
        the change check asked it to revalidate there, as it asks a moved one."""
        commits = self.flips((artefact.path,), reached, excluded=False)
        return max(commits) if commits else None

    def unreadable_findings(self) -> list[RepositoryFinding]:
        """A finding per revalidation point whose `friction.exclude` does not read."""
        found: list[RepositoryFinding] = []
        index = {commit.sha: commit for commit in self.history.commits}
        for sha, reason in sorted(self.unreadable.items()):
            commit = index[sha]
            found.append(
                RepositoryFinding(
                    RepositoryFindingKind.UNREADABLE,
                    f'`friction.exclude` does not read at {commit.short} "{commit.subject}" '
                    f"({reason}): the artefacts revalidated there are read under HEAD's, so a "
                    f"change to it since asks nothing of them",
                    location=_CONFIG,
                    origin=commit,
                )
            )
        return found

    # --- the rule of point 5 ---------------------------------------------------------

    def problem(self, anchor: Anchor) -> RepositoryFinding | None:
        """A dead anchor, an unresolved kind or a missing answer at HEAD (point 7), else
        `None`.

        An anchor of a registered kind is judged by its resolver's answer, read
        against HEAD's files: no answer leaves it unresolved (`NO_ANSWER`) —
        whether it changed cannot be told, so its artefact is not judged
        (point 2; `ArtefactState.UNRESOLVED`) — and an answer naming no file
        leaves it dead, as a dead anchor of a core kind is: the artefact is
        judged on its other anchors.
        """
        reason = self.kinds.unresolved(anchor.kind)
        if reason is not None:
            message = f"nothing installed resolves this kind: {reason}"
            return RepositoryFinding(RepositoryFindingKind.UNRESOLVED_KIND, message, anchor=anchor)
        if anchor.kind not in CORE_ANCHOR_KINDS:
            resolution = self.kinds.resolve(anchor)
            if resolution.no_answer is not None:
                return RepositoryFinding(
                    RepositoryFindingKind.NO_ANSWER,
                    f"its resolver gave no answer, so whether it changed cannot be told: "
                    f"{resolution.no_answer}",
                    anchor=anchor,
                )
            if not resolution.paths:
                return RepositoryFinding(
                    RepositoryFindingKind.DEAD_ANCHOR,
                    "its resolver names no file for it",
                    anchor=anchor,
                )
            return None
        if self.head.resolves(anchor):
            return None
        return RepositoryFinding(
            RepositoryFindingKind.DEAD_ANCHOR, self.head.why_dead(anchor), anchor=anchor
        )

    def over_broad(self, anchor: Anchor) -> RepositoryFinding | None:
        """An anchor standing on more than `OVER_BROAD_SHARE` of the tracked files (point 7):
        a path anchor by the files it matches, an anchor of a registered kind by the
        files its resolver names — the rule is not a kind's. Both are counted among the
        tracked files `friction.exclude` leaves in, the share's whole, so it never passes
        100%. A record or an artefact anchor names one file."""
        if not self._tracked:
            return None
        if anchor.kind == "path":
            matched = sum(map(self.head.stands_on(anchor.value), self.head.files))
            verb, fix = "matches", "narrow it"
        elif anchor.kind not in CORE_ANCHOR_KINDS:
            matched = len(self._tracked.intersection(self.kinds.files(anchor)))
            verb, fix = "stands on", "have its resolver name less, or anchor to a narrower value"
        else:
            return None
        total = len(self._tracked)
        if matched <= total * OVER_BROAD_SHARE:
            return None
        share = round(100 * matched / total)
        message = (
            f"{verb} {matched} of {total} tracked files ({share}%): most changes would make it "
            f"a revalidation, which teaches people to bump the marker blindly — {fix}"
        )
        return RepositoryFinding(RepositoryFindingKind.OVER_BROAD, message, anchor=anchor)

    def matching_paths(self, pattern: str, point: int) -> frozenset[str]:
        """Every path the history touched that `pattern` stands on at the revalidation
        point and at HEAD (`stands_on`): excluded paths left out, each state's own."""
        reading = None
        if not self.reads_as_head(point):
            settings = self.settings_of(self.history.commits[point].sha)
            reading = tuple(sorted(e.resolved for e in settings.exclude))
        key = (pattern, reading)
        found = self._matching.get(key)
        if found is None:
            _at_head, in_history = self._matched_by(pattern)
            found = frozenset(filter(self.stands_on(pattern, point), in_history))
            self._matching[key] = found
        return found

    def touching(
        self, anchor: Anchor, covered: frozenset[int], own: frozenset[str], point: int
    ) -> set[int]:
        """Every commit outside `covered` that touched what a live path, record or
        registered anchor stands on — the candidates a change is sought among, never
        the change itself, which is a difference between two states (`change`).

        A path anchor: each commit that touched a path it stands on at the
        revalidation point and at HEAD, the artefact's own names (`own`) left
        out; where `friction.exclude` changed since the point (`exclusion`),
        each commit that changed a file it leaves out, lets in or that is gone
        while the anchor stood on the file (`counts`), and each that let one of
        its files in. A record anchor: each commit that changed the content of
        the record's file. An anchor of a registered kind: each commit that
        changed the content of a file its resolver says it stands on, followed
        through renames as a record's file is, its artefact's own names left
        out as a path anchor's are. One pass over the history's listing,
        however many there are.
        """
        if anchor.kind == "path":
            touched = {
                index
                for rel in self.matching_paths(anchor.value, point) - own
                for index in self.history.touched(rel)
                if index not in covered
            }
            moved = self.exclusion_change(anchor, point).less(own)
            for rel in moved.left_out + moved.let_in + moved.gone:
                touched.update(
                    index
                    for index in self.history.touched(rel)
                    if index not in covered and self.counts(index, rel)
                )
            return touched | self.flips(moved.let_in, covered, excluded=False)
        return {
            v.index
            for rel in self.files_of(anchor, own)
            for v in self.history.versions(rel)
            if v.index not in covered and v.entry.changes_content
        }

    def files_of(self, anchor: Anchor, own: frozenset[str]) -> tuple[str, ...]:
        """The files at HEAD a record anchor or an anchor of a registered kind stands
        on: the record's file, or what its resolver answers, `own` left out; none for
        another kind, or for one that resolves to nothing."""
        if anchor.kind == "record":
            rel = self.head.record_path(anchor.value)
            return () if rel is None else (rel,)
        return tuple(rel for rel in self.kinds.files(anchor) if rel not in own)

    def answering(self, points: Points, anchor: Anchor) -> tuple[int, ...]:
        """The states an anchor is measured from (COR-050 points 3 and 4): every
        revalidation point, and the anchor's deferral point where no revalidation
        point reaches it — one kept through a revalidation answers nothing."""
        deferral = dict(points.deferrals).get(anchor)
        if deferral is None or deferral in self.history.reached(points.revalidations):
            return points.revalidations
        return (*points.revalidations, deferral)

    def _entry_at(self, state: int, rel: str, names: Sequence[str] = ()) -> TreeEntry | None:
        """The entry of the file `rel` at the state at `state` — under `rel`, else the first
        of its earlier `names` the state holds — `None` where it holds none."""
        sha = self.history.commits[state].sha
        for name in (rel, *names):
            entry = self.trees.entry(sha, name)
            if entry is not None:
                return entry
        return None

    def _result(self, index: int, path: str) -> TreeEntry | None:
        """The entry the commit at `index` left the file at `path` with: `None` where it
        removed it, or moved it away."""
        entry = self.history.entry(index, path)
        return None if entry is None else entry.after

    def change(
        self, anchor: Anchor, answering: Sequence[int], own: frozenset[str]
    ) -> Change | None:
        """Whether a live anchor changed since its `answering` states, and where
        (COR-050 points 3 to 5 and 9).

        The anchor is judged as a whole (`changed_since`, the rule the change
        check judges the points of a written-back `at` by): it has changed only
        where what it stands on differs from what it stood on at every answering
        state — at each some part of it differs, not necessarily the same — never
        part by part. Each state is read on its own (`since`), under its own
        `friction.exclude` (point 7). The debt is dated where the anchor came to
        differ from every state: of each state's origin — the oldest commit from
        which one of its parts has differed, without returning, from what it was
        there (point 9) — the newest. The commits behind it are those after what
        every state covers that touched a part differing from what it was at a
        state: what a deferral postponed is listed behind the deferral, never here.
        """
        readings: dict[int, Change | None] = {}

        def differs_from(state: int) -> bool:
            readings[state] = self.since(anchor, state, own)
            return readings[state] is not None

        if not changed_since(answering, differs_from):
            return None
        found = [reading for reading in readings.values() if reading is not None]
        covered = self.history.reached(answering)
        return Change(
            min(reading.origin for reading in found),
            frozenset(c for reading in found for c in reading.commits if c not in covered),
        )

    def since(self, anchor: Anchor, state: int, own: frozenset[str]) -> Change | None:
        """How a live anchor differs from what it stood on at the answering state at
        `state`: `None` where every part of it stands as it stood there; else the oldest
        origin among the parts that differ (`origin`, each measured from this state) and
        the commits after the state behind them.

        The parts are sought among the paths commits after the state touched: a
        path anchor's files it stands on at the state and at HEAD, each under its
        own exclusions, those a widening took (`exclusion`), those gone under an
        exclusion, and those a narrowing let in, which always count; a record's
        file and a registered kind's files, followed across renames; an artefact's
        content, read at the state's commit. An edit put back is no change.
        """
        if anchor.kind == "artefact":
            target = self.head.find(anchor.value)
            return None if target is None else self._target_since(target, state)
        if anchor.kind == "path":
            return self._path_since(anchor, state, own)
        covered = self.history.ancestors(state)
        origins: list[int] = []
        commits: set[int] = set()
        for rel in self.files_of(anchor, own):
            names = self.history.names(rel)
            touched = {i for name in names for i in self.history.touched(name) if i not in covered}
            if not touched:
                continue  # nothing after the state touched the file: it stands as it stood
            then = self._entry_at(state, rel, names[1:])
            if not differs(self.head_tree.entry(rel), then):
                continue
            found = origin(
                self.history,
                touched,
                lambda c, names=names, then=then: any(
                    self.history.entry(c, name) is not None and self._result(c, name) == then
                    for name in names
                ),
            )
            if found is not None:
                origins.append(found)
                commits.update(touched)
        return Change(max(origins), frozenset(commits)) if origins else None

    def _path_since(self, anchor: Anchor, state: int, own: frozenset[str]) -> Change | None:
        """`since` for a path anchor."""
        covered = self.history.ancestors(state)
        touched_by: dict[str, list[int]] = {}
        for rel in self.matching_paths(anchor.value, state) - own:
            commits = [i for i in self.history.touched(rel) if i not in covered]
            if commits:
                touched_by[rel] = commits
        moved = self.exclusion_change(anchor, state).less(own)
        for rel in moved.gone:
            commits = [
                i for i in self.history.touched(rel) if i not in covered and self.counts(i, rel)
            ]
            if commits:
                touched_by[rel] = commits
        origins: list[int] = []
        behind: set[int] = set()
        for rel, commits in sorted(touched_by.items()):
            now = None if rel in moved.gone else self.head_tree.entry(rel)
            then = self._entry_at(state, rel)
            if not differs(now, then):
                continue
            found = origin(
                self.history,
                commits,
                lambda c, rel=rel, then=then: self._result(c, rel) == then,
            )
            if found is not None:
                origins.append(found)
                behind.update(commits)
        exclusion = self.exclusion(anchor, state, own)
        origins.extend(exclusion.changed.values())
        behind |= exclusion.touched
        if moved.let_in:
            let_in = {
                i
                for rel in moved.let_in
                for i in self.history.touched(rel)
                if i not in covered and self.counts(i, rel)
            } | self.flips(moved.let_in, covered, excluded=False)
            if let_in:
                origins.append(max(let_in))
                behind |= let_in
        return Change(max(origins), frozenset(behind)) if origins else None

    def _target_at(
        self, index: int, target: Artefact, versions: Sequence[Version]
    ) -> tuple[str, dict[str, Any]] | None:
        """`target`'s content as the commit at `index` holds it, read under the file's
        name there — `None` where it holds no such artefact."""
        reached = self.history.ancestors(index)
        version = next((v for v in versions if v.index in reached), None)
        if version is None:
            return None
        sha = self.history.commits[index].sha
        then = self.walker.artefact_in(self.trees.entry(sha, version.path), version.path, target)
        return None if then is None else content(then)

    def _target_since(self, target: Artefact, state: int) -> Change | None:
        """`since` for an artefact anchor: `target`'s content at HEAD against its content at
        the state's commit, never anything in its container."""
        covered = self.history.ancestors(state)
        versions = list(self.history.versions(target.path))
        if all(v.index in covered for v in versions):
            return None  # nothing after the state touched the target's file
        then = self._target_at(state, target, versions)
        if content(target) == then:
            return None
        walker = self.walker
        touched = {
            v.index
            for v in versions
            if v.index not in covered
            and changed(_content_of, walker.same_at(v, target), walker.same_in_parents(v, target))
        }
        by_index = {v.index: v for v in versions}

        def puts_back(index: int) -> bool:
            held = walker.same_at(by_index[index], target)
            return (None if held is None else content(held)) == then

        found = origin(self.history, touched, puts_back)
        if found is None:
            # The content differs, yet no listed commit after the state changed it — a
            # merge took it whole from a side: date it from the newest that touched it.
            outside = [v.index for v in versions if v.index not in covered]
            if not outside:
                return None
            found = min(outside)
            touched = set(outside)
        return Change(found, frozenset(touched))


# --- the check ---------------------------------------------------------------------


def run_repository_check(
    target_root: Path, *, registry: Mapping[str, ResolverCommand] | None = None
) -> RepositoryCheck:
    """Run the whole-repository check of HEAD against its history.

    Raises `FrictionCheckError` when it cannot run — outside a git repository,
    or before the first commit — except while dormant, when no place is
    declared and nothing is demanded.
    """
    try:
        head_sha = commit_of(target_root, "HEAD")
    except FrictionCheckError:
        head_sha = None  # not a git repository: dormant demands none (point 15)
    if head_sha is None:
        settings = read_friction_settings(target_root)
        if not settings.places:
            return _dormant(settings.mode_or_default, settings.mode, places=0)
        raise FrictionCheckError(
            "HEAD names no commit (or this is not a git repository); the whole-repository check "
            "reads history, so commit first."
        )
    tree = CommitTree(target_root, head_sha)
    discovery = discover_artefacts(target_root, tree=tree)
    settings = discovery.settings
    if not discovery.places:
        return _dormant(settings.mode_or_default, settings.mode, places=0)

    head = Side(target_root, tree, discovery)
    registry = registered_anchor_kinds(target_root, tree) if registry is None else registry
    history = read_history(target_root, head_sha)
    blobs = BlobReader(target_root)
    try:
        judge = _Judge(head, tree, history, Walker(history, blobs), blobs, registry)
        reports: list[ArtefactReport] = []
        findings: list[RepositoryFinding] = []
        for index in truth_chain_order(discovery):
            artefact = discovery.artefacts[index]
            if artefact.has_friction_block and (anchors_of(artefact) or artefact.deferrals):
                report, found = _check_artefact(artefact, judge)
                if report is not None:
                    reports.append(report)
                findings.extend(found)
        findings.extend(judge.unreadable_findings())
    finally:
        blobs.close()
    for unreadable in sorted(discovery.unreadable, key=lambda u: u.path):
        findings.append(
            RepositoryFinding(
                RepositoryFindingKind.UNREADABLE,
                f"front matter does not parse ({unreadable.reason}); its artefacts cannot be "
                f"checked — `pkit validate` fails on it",
                location=unreadable.path,
            )
        )
    surface, uncovered = _uncovered_surface(head, discovery, judge.kinds)
    unanchored, accepted = _unanchored(discovery)
    return RepositoryCheck(
        mode=settings.mode_or_default,
        mode_as_written=settings.mode,
        dormant=False,
        places=len(discovery.places),
        artefacts=len(discovery.artefacts),
        carrying=len(discovery.with_container),
        head=HeadState(head_sha, uncommitted_paths(target_root)),
        shallow=bool(history.shallow),
        artefact_reports=tuple(reports),
        findings=tuple(findings),
        unanchored=unanchored,
        accepted_unanchored=accepted,
        excluded=sum(1 for a in discovery.artefacts if a.excluded),
        surface=surface,
        uncovered=uncovered,
    )


def _unanchored(discovery: Discovery) -> tuple[tuple[str, ...], tuple[AcceptedUnanchored, ...]]:
    """The unanchored measure (COR-050 point 8), in walk order: the locations of the
    artefacts with no anchors and no reason — the forgotten ones — and, apart, those
    whose block gives the reason a person accepted them with none (point 1).
    Excluded artefacts are in neither (point 7)."""
    forgotten: list[str] = []
    accepted: list[AcceptedUnanchored] = []
    for artefact in discovery.artefacts:
        if artefact.excluded or anchors_of(artefact):
            continue
        reason = artefact.unanchored_because
        if reason is None:
            forgotten.append(artefact.location)
        else:
            accepted.append(AcceptedUnanchored(artefact.id, artefact.location, reason))
    return tuple(forgotten), tuple(accepted)


def _dormant(mode: str, mode_as_written: Any, *, places: int) -> RepositoryCheck:
    return RepositoryCheck(
        mode=mode,
        mode_as_written=mode_as_written,
        dormant=True,
        places=places,
        artefacts=0,
        carrying=0,
        head=None,
        shallow=None,
        artefact_reports=(),
        findings=(),
        unanchored=(),
        accepted_unanchored=(),
        excluded=0,
        surface=0,
        uncovered=(),
    )


def _check_artefact(
    artefact: Artefact, judge: _Judge
) -> tuple[ArtefactReport | None, list[RepositoryFinding]]:
    """The report and findings about one artefact carrying anchors or deferrals.

    An artefact under an excluded path has no report and no stale or deferred
    finding — it is left out of the debt as of the measures (point 7) — and
    only what it declares is checked: dead anchors, unresolved kinds, missing
    answers and over-broad anchors. An artefact with an anchor that cannot be
    resolved is not judged (`ArtefactState.UNRESOLVED`): what its other
    anchors owe is still found and reported, and its state says the reading
    is not whole.
    """

    def finding(
        kind: RepositoryFindingKind,
        message: str,
        anchor: Anchor | None = None,
        origin: int | None = None,
    ) -> RepositoryFinding:
        commit = None if origin is None else judge.history.commits[origin]
        return RepositoryFinding(kind, message, artefact.id, artefact.location, anchor, commit)

    stale: list[RepositoryFinding] = []
    deferred: list[RepositoryFinding] = []
    problems: list[RepositoryFinding] = []
    broad: list[RepositoryFinding] = []
    live: list[Anchor] = []
    for anchor in anchors_of(artefact):
        problem = judge.problem(anchor)
        if problem is None:
            live.append(anchor)
        else:
            problems.append(finding(problem.kind, problem.message, anchor))
        over = judge.over_broad(anchor)
        if over is not None:
            broad.append(finding(over.kind, over.message, anchor))
    if artefact.excluded:
        return None, problems + broad

    points = judge.walker.points(artefact)
    commits = judge.history.commits
    deferral_points = dict(points.deferrals)
    if points.unreachable is not None or points.revalidation is None:
        what = points.unreachable or "its revalidation point"
        message = (
            f"friction cannot be judged: {what} is not in this clone's history — fetch the "
            f"full history (`git fetch --unshallow`) and run again"
        )
        report = ArtefactReport(
            artefact.id,
            artefact.location,
            ArtefactState.UNREACHABLE,
            None if points.revalidation is None else commits[points.revalidation],
            tuple((a, None if p is None else commits[p]) for a, p in points.deferrals),
            revalidation_points=tuple(commits[p] for p in points.revalidations),
        )
        unreachable = [finding(RepositoryFindingKind.UNREACHABLE, message)]
        return report, unreachable + problems + broad

    point = commits[points.revalidation]
    reached = judge.history.reached(points.revalidations)
    problems = [
        _named_exclusion(judge, found, points.revalidation, points.own_paths) for found in problems
    ]
    for move in points.moves:
        moved = commits[move.index]
        stale.append(
            finding(
                RepositoryFindingKind.STALE,
                f'moved here from {move.entry.old_path} in {moved.short} "{moved.subject}" '
                f"({moved.author}, {moved.day}) after its revalidation point {point.short} "
                f"({point.day}), with no revalidation since — revalidate the artefact",
                origin=move.index,
            )
        )
    let_in = judge.let_back_in(artefact, reached)
    if let_in is not None:
        by = commits[let_in]
        stale.append(
            finding(
                RepositoryFindingKind.STALE,
                f'{LET_BACK_IN} in {by.short} "{by.subject}" ({by.author}, '
                f"{by.day}) after its revalidation point {point.short} ({point.day}), with no "
                f"revalidation since — revalidate the artefact",
                origin=let_in,
            )
        )
    left_out: list[RepositoryFinding] = []
    own = points.own_paths
    for anchor in live:
        deferral_point = deferral_points.get(anchor)
        answering = judge.answering(points, anchor)
        # A widening that asks nothing is reported against the newest revalidation point.
        newest = judge.exclusion(anchor, points.revalidation, own)
        if newest.moved.left_out and not newest.asks:
            left_out.append(_left_out_finding(finding, newest, anchor, commits))
        change = judge.change(anchor, answering, own)
        if change is None:
            continue
        came = commits[change.origin]
        message = (
            f"changed after its revalidation point {point.short} ({point.day}): first in "
            f'{came.short} "{came.subject}" ({came.author}, {came.day}), a change not put '
            f"back since"
        )
        asking = next(
            (found for found in (judge.exclusion(anchor, s, own) for s in answering) if found.asks),
            None,
        )
        if asking is not None:
            message += f"; `friction.exclude` changed over it since ({asking.describe(commits)})"
        if deferral_point is not None:
            message += (
                f"; its deferral at {commits[deferral_point].short} covers only earlier changes"
            )
        message += " — revalidate the artefact, or defer the anchor again"
        stale.append(finding(RepositoryFindingKind.STALE, message, anchor, change.origin))
    for anchor, deferral_point in points.deferrals:
        if deferral_point is None:
            continue
        since = commits[deferral_point]
        reason = deferral_reason(artefact, anchor)
        message = (
            f"deferred{' — ' + reason if reason else ''}; since {since.short} "
            f'"{since.subject}" ({since.author}, {since.day})'
        )
        deferred.append(finding(RepositoryFindingKind.DEFERRED, message, anchor, deferral_point))

    if any(found.kind in UNRESOLVED_KINDS for found in problems):
        state = ArtefactState.UNRESOLVED
    elif stale:
        state = ArtefactState.STALE
    elif deferred:
        state = ArtefactState.DEFERRED
    else:
        state = ArtefactState.CURRENT
    report = ArtefactReport(
        artefact.id,
        artefact.location,
        state,
        point,
        tuple((a, None if p is None else commits[p]) for a, p in points.deferrals),
        cut=points.cut,
        revalidation_points=tuple(commits[p] for p in points.revalidations),
    )
    return report, stale + deferred + left_out + problems + broad


def _left_out_finding(
    finding: Callable[..., RepositoryFinding],
    exclusion: _Exclusion,
    anchor: Anchor,
    commits: Sequence[Commit],
) -> RepositoryFinding:
    """A widening since the revalidation point that asks nothing (COR-050 point 7):
    reported, with the commit that first left the files out as its origin."""
    message = left_out_message(exclusion.moved.left_out, "at its revalidation point", "since")
    origin = max(exclusion.left_by) if exclusion.left_by else None
    if origin is not None:
        by = commits[origin]
        message += f', left out in {by.short} "{by.subject}" ({by.author}, {by.day})'
    return finding(RepositoryFindingKind.LEFT_OUT, message, anchor, origin)


def _named_exclusion(
    judge: _Judge, found: RepositoryFinding, point: int, own: frozenset[str]
) -> RepositoryFinding:
    """A dead path anchor's finding, naming the exclusion that killed it where a change
    to `friction.exclude` since the revalidation point left out what it stood on there
    (COR-050 point 7): `…, excluded since <commit> "<change>" (<author>, <date>)`."""
    anchor = found.anchor
    if found.kind is not RepositoryFindingKind.DEAD_ANCHOR or anchor is None:
        return found
    since = judge.excluding_commit(anchor, point, own)
    if since is None:
        return found
    commit = judge.history.commits[since]
    return replace(
        found,
        message=(
            f'{found.message}, excluded since {commit.short} "{commit.subject}" '
            f"({commit.author}, {commit.day})"
        ),
    )


def _uncovered_surface(
    head: Side, discovery: Discovery, kinds: AnchorKinds
) -> tuple[int, tuple[str, ...]]:
    """How many paths the declared surface holds at HEAD, and those no artefact anchors to.

    The surface is what the project and its capabilities say ought to be
    described (COR-050 point 8), excluded paths left out. A path is anchored
    when any artefact's path anchor stands on it (`Side.stands_on`), a record
    anchor names it, an artefact anchor names the artefact it holds, or the
    resolver of a registered kind answers it for an anchor (`AnchorKinds.files`).
    """
    surface: set[str] = set()
    for declared in head.settings.surface:
        surface.update(filter(head.stands_on(declared.resolved), head.files))
    if not surface:
        return 0, ()
    anchored: set[str] = set()
    for artefact in discovery.artefacts:
        for anchor in anchors_of(artefact):
            if anchor.kind == "path":
                anchored.update(filter(head.stands_on(anchor.value), surface))
            elif anchor.kind == "record":
                rel = head.record_path(anchor.value)
                if rel is not None:
                    anchored.add(rel)
            elif anchor.kind == "artefact":
                target = head.find(anchor.value)
                if target is not None:
                    anchored.add(target.path)
            else:
                anchored.update(kinds.files(anchor))
    return len(surface), tuple(sorted(surface - anchored))


# --- one artefact, with the commits behind each finding ------------------------------
#
# `pkit friction explain` judges one artefact exactly as the check does — through
# `_check_artefact`, on a judge built as `run_repository_check` builds it — and adds,
# per finding, the commits behind it, read from the same history by the same rules,
# and per path anchor the files it stands on, matched by the rule the check decides
# a dead anchor by (`Side.matching`), each state under its own `friction.exclude`,
# with those HEAD's leaves out.


@dataclass(frozen=True)
class CommitBehind:
    """One commit behind a finding, and the paths behind the finding it touched.

    `paths`, sorted — what a reader limits the commit to. A path anchor: the
    paths it stands on in history that the commit touched, the artefact's own
    file under any of its names left out (`_Judge.matching_paths` less the
    walk's own paths) — exactly what the check reads as the anchor's change,
    which the anchor's `AnchorFiles` are not — and the configuration file
    where the commit changed `friction.exclude` over the anchor's files. A
    record or artefact anchor: the file it names, under the names the commit
    touched. A move: the artefact's file under both its names. Either side of
    a rename counts, as the check counts it.
    """

    commit: Commit
    paths: tuple[str, ...]

    def as_json(self) -> dict[str, Any]:
        return {**self.commit.as_json(), "paths": list(self.paths)}


@dataclass(frozen=True)
class TracedFinding:
    """A finding of the whole-repository check about one artefact, and the commits behind it.

    `commits` are oldest first, each with the paths behind the finding it
    touched (`CommitBehind`). Stale on an anchor: every commit after what the
    answering states cover that touched a part of the anchor differing from
    what it was at a state, and the finding's origin; stale by a move: the
    rename. Deferred: the changes the deferral postpones —
    after the revalidation point, up to the deferral point; none for a dead
    anchor, whose deferral postpones no friction (COR-050 point 4) since the
    anchor is an error (point 7). A dead `path` anchor: where its files went —
    for each path it matched in history, the last commit that touched it,
    whether before or after the revalidation point, so an anchor revalidated
    over while dead still shows its deletions, and each commit since the point
    that changed `friction.exclude` to leave its files out; a dead record or
    artefact anchor names no file whose history could be read. Any other
    finding, or an artefact whose points lie beyond a shallow clone: none.
    """

    finding: RepositoryFinding
    commits: tuple[CommitBehind, ...]


@dataclass(frozen=True)
class AnchorFiles:
    """The files a path anchor stands on at the revalidation point and at HEAD, and
    the files at HEAD its glob covers that `friction.exclude` leaves out.

    Each sorted. `point` and `head` are matched as the check decides a dead
    anchor (`Side.matching`) — never as it decides a changed one, which reads
    the paths commits touched, the artefact's own file left out (a finding's
    commits carry those). Each state is read under its own exclusions, as the
    check reads it (COR-050 point 7): `point` under the revalidation point's
    `friction.exclude`, so an anchor an exclusion added since killed still
    shows what it stood on; `head` and `excluded` under HEAD's. `point` is
    `None` when there is no revalidation point to read: it lies beyond a
    shallow clone's history, or the artefact is under an excluded path and has
    no points. `head` is empty for a dead anchor, and `excluded`
    (`Side.left_out`) says whether it is dead by a typo — nothing excluded
    either — or by a glob that covers only excluded files.
    """

    point: tuple[str, ...] | None
    head: tuple[str, ...]
    excluded: tuple[str, ...]

    def as_json(self) -> dict[str, list[str] | None]:
        return {
            "point": None if self.point is None else list(self.point),
            "head": list(self.head),
            "excluded": list(self.excluded),
        }


@dataclass(frozen=True)
class ArtefactCheck:
    """One artefact at HEAD, judged as the whole-repository check judges it.

    `report` is `None` when there is nothing to judge — no `friction` block, or
    neither anchors nor deferrals, the artefacts the check passes over — and
    `findings` and `files` are then empty. It is `None` too for an artefact
    under an excluded path, which is never judged stale or deferred; `findings`
    are then what the check reports of its declarations. Otherwise both are the
    check's own for this artefact, the findings in its order. Whenever it is
    judged, `files` holds each path anchor's files (`AnchorFiles`) — with no
    point's for an excluded artefact, which has no points.
    """

    head: HeadState
    shallow: bool
    artefact: Artefact  # as it stands at HEAD
    report: ArtefactReport | None
    findings: tuple[TracedFinding, ...]
    files: Mapping[Anchor, AnchorFiles] = field(default_factory=dict[Anchor, AnchorFiles])


def run_artefact_check(
    target_root: Path,
    select: Callable[[Discovery], Artefact],
    *,
    registry: Mapping[str, ResolverCommand] | None = None,
) -> ArtefactCheck | None:
    """The whole-repository check of the one artefact `select` picks from HEAD's artefacts.

    `None` while dormant: no place is declared at HEAD. Raises
    `FrictionCheckError` when the check cannot run, as `run_repository_check`
    does, and whatever `select` raises when it names no artefact. Writes
    nothing (COR-050 point 13).
    """
    try:
        head_sha = commit_of(target_root, "HEAD")
    except FrictionCheckError:
        head_sha = None
    if head_sha is None:
        if not read_friction_settings(target_root).places:
            return None
        raise FrictionCheckError(
            "HEAD names no commit (or this is not a git repository); the whole-repository check "
            "reads history, so commit first."
        )
    tree = CommitTree(target_root, head_sha)
    discovery = discover_artefacts(target_root, tree=tree)
    if not discovery.places:
        return None
    artefact = select(discovery)
    head = HeadState(head_sha, uncommitted_paths(target_root))
    if not (artefact.has_friction_block and (anchors_of(artefact) or artefact.deferrals)):
        return ArtefactCheck(head, bool(shallow_commits(target_root)), artefact, None, ())
    registry = registered_anchor_kinds(target_root, tree) if registry is None else registry
    history = read_history(target_root, head_sha)
    blobs = BlobReader(target_root)
    try:
        side = Side(target_root, tree, discovery)
        judge = _Judge(side, tree, history, Walker(history, blobs), blobs, registry)
        report, findings = _check_artefact(artefact, judge)
        traced = _traced(artefact, judge, findings)
        point = None if report is None else _index_of(history, report)
        files = _anchor_files(judge, artefact, point)
    finally:
        blobs.close()
    return ArtefactCheck(head, bool(history.shallow), artefact, report, traced, files)


def _index_of(history: History, report: ArtefactReport) -> int | None:
    """The log index of a report's revalidation point, `None` when it has none."""
    point = report.revalidation_point
    if point is None:
        return None
    return next((i for i, c in enumerate(history.commits) if c.sha == point.sha), None)


def _anchor_files(
    judge: _Judge, artefact: Artefact, point: int | None
) -> dict[Anchor, AnchorFiles]:
    """Each path anchor's files at the revalidation point and at HEAD, and those
    `friction.exclude` leaves out at HEAD (`AnchorFiles`).

    The point's files are listed from git objects, once, and only when the
    artefact has a path anchor; each state is matched under its own exclusions
    (`_Judge.matched_at`).
    """
    anchors = [anchor for anchor in anchors_of(artefact) if anchor.kind == "path"]
    if not anchors:
        return {}
    head = judge.head
    return {
        anchor: AnchorFiles(
            None if point is None else judge.matched_at(point, anchor.value),
            head.matching(anchor.value),
            head.left_out(anchor.value),
        )
        for anchor in anchors
    }


def _traced(
    artefact: Artefact, judge: _Judge, findings: Sequence[RepositoryFinding]
) -> tuple[TracedFinding, ...]:
    """Each finding with the commits behind it (see `TracedFinding`)."""
    if artefact.excluded:  # only its declarations were checked: nothing lies behind them
        return tuple(TracedFinding(f, ()) for f in findings)
    history = judge.history
    points = judge.walker.points(artefact)  # the check's walk again: its blobs are cached
    if points.unreachable is not None or points.revalidation is None:
        return tuple(TracedFinding(f, ()) for f in findings)
    point, own = points.revalidation, points.own_paths
    position = {commit.sha: index for index, commit in enumerate(history.commits)}
    reached = history.reached(points.revalidations)
    deferral_points = {anchor: at for anchor, at in points.deferrals if at is not None}
    let_in = judge.let_back_in(artefact, reached)
    traced: list[TracedFinding] = []
    for finding in findings:
        anchor = finding.anchor
        answering = points.revalidations if anchor is None else judge.answering(points, anchor)
        behind: set[int] = set()
        configured: set[int] = set()  # commits behind it through `friction.exclude`
        if finding.kind is RepositoryFindingKind.STALE and finding.origin is not None:
            came = position[finding.origin.sha]
            behind.add(came)
            if anchor is None and came == let_in:
                configured.add(came)
            elif anchor is not None:
                change = judge.change(anchor, answering, own)
                if change is not None:
                    behind.update(change.commits)
                for state in answering if anchor.kind == "path" else ():
                    exclusion = judge.exclusion(anchor, state, own)
                    after = history.ancestors(state)
                    configured.update(judge.flips(exclusion.moved.let_in, after, excluded=False))
                    if exclusion.asks:
                        configured.update(exclusion.left_by)
        elif finding.kind is RepositoryFindingKind.LEFT_OUT and anchor is not None:
            configured.update(judge.exclusion(anchor, point, own).left_by)
        elif (
            finding.kind is RepositoryFindingKind.DEAD_ANCHOR
            and anchor is not None
            and anchor.kind == "path"
        ):
            removed, excluding = _where_it_went(judge, anchor, own, point)
            behind.update(removed)
            configured.update(excluding)
        elif (
            finding.kind is RepositoryFindingKind.DEFERRED
            and anchor in deferral_points
            and judge.problem(anchor) is None
        ):
            postponed = history.ancestors(deferral_points[anchor])
            changed = _changes(judge, anchor, reached, own, point)
            behind.update(index for index in changed if index in postponed)
        behind |= configured
        touched = (
            _touched_by(history, _paths_behind(judge, anchor, own, answering), behind)
            if behind
            else {}
        )
        if anchor is None and let_in in configured:
            touched.pop(let_in, None)  # a let-in changed the configuration, not the artefact
        for index in configured:
            # A commit that changed the exclusions over the anchor's files touched none of
            # them: the configuration file is the change it made.
            touched.setdefault(index, set()).add(_CONFIG)
        commits = tuple(
            CommitBehind(history.commits[index], tuple(sorted(touched.get(index, ()))))
            for index in sorted(behind, reverse=True)
        )
        traced.append(TracedFinding(finding, commits))
    return tuple(traced)


def _paths_behind(
    judge: _Judge, anchor: Anchor | None, own: frozenset[str], states: Sequence[int]
) -> frozenset[str]:
    """Every path whose change a finding on `anchor` reads (`CommitBehind`), measured
    from the answering `states`.

    A path anchor's paths are the check's own at each state
    (`_Judge.matching_paths`, and the files an exclusion change since it left
    out, let in or found gone, less `own`); a record or artefact anchor's the
    names of the file it names; a registered kind's the names of each file its
    resolver answers, less `own`; a move's (no anchor) the artefact's own names.
    """
    if anchor is None:
        return own
    if anchor.kind == "path":
        paths: set[str] = set()
        for state in states:
            moved = judge.exclusion_change(anchor, state)
            paths.update(judge.matching_paths(anchor.value, state))
            paths.update(moved.left_out + moved.let_in + moved.gone)
        return frozenset(paths) - own
    if anchor.kind == "artefact":
        target = judge.head.find(anchor.value)
        return frozenset() if target is None else _names(judge.history, target.path)
    names = frozenset[str]().union(
        *(_names(judge.history, rel) for rel in judge.files_of(anchor, own))
    )
    return names if anchor.kind == "record" else names - own


def _names(history: History, path: str) -> frozenset[str]:
    """Every name the file now at `path` had in `history`, renames followed."""
    names = {path}
    for version in history.versions(path):
        names.add(version.path)
        names.update(source for source in version.sources if source is not None)
    return frozenset(names)


def _touched_by(history: History, paths: frozenset[str], commits: set[int]) -> dict[int, set[str]]:
    """Of `paths`, those each of `commits` touched, by commit — one pass over their history."""
    touched: dict[int, set[str]] = {}
    for rel in paths:
        for index in history.touched(rel):
            if index in commits:
                touched.setdefault(index, set()).add(rel)
    return touched


def _where_it_went(
    judge: _Judge, anchor: Anchor, own: frozenset[str], point: int
) -> tuple[set[int], set[int]]:
    """Where a dead path anchor's files went: for each path it matched in history, the
    artefact's own names left out, the last commit that touched it — its removal, or its
    rename away — wherever that lies against the revalidation point; and, apart, each
    commit since the point that changed `friction.exclude` to leave its files out."""
    removed = {
        judge.history.touched(rel)[0] for rel in judge.matching_paths(anchor.value, point) - own
    }
    left_out = judge.left_out_since(anchor, point, own).left_out
    return removed, judge.flips(left_out, judge.history.ancestors(point), excluded=True)


def _changes(
    judge: _Judge, anchor: Anchor, covered: frozenset[int], own: frozenset[str], point: int
) -> set[int]:
    """Every commit outside `covered` that touched a live anchor's target — what a
    deferral postpones, listed behind a deferred finding (COR-050 point 4).

    A path or a record: `_Judge.touching`. An artefact: each commit at which
    the target's content differs from its content at every parent of the
    commit (`changed`).
    """
    if anchor.kind == "artefact":
        target = judge.head.find(anchor.value)
        if target is None:
            return set()
        walker = judge.walker
        return {
            version.index
            for version in judge.history.versions(target.path)
            if version.index not in covered
            and changed(
                _content_of,
                walker.same_at(version, target),
                walker.same_in_parents(version, target),
            )
        }
    return judge.touching(anchor, covered, own, point)


def _content_of(artefact: Artefact | None) -> tuple[str, dict[str, Any]] | None:
    return None if artefact is None else content(artefact)


# --- output --------------------------------------------------------------------------

#: The version of the document `render_json` returns. A change a reader could break
#: against — a key removed, renamed or given another meaning — raises it; a key added
#: does not. A document without it comes from a backbone that predates it: version 1.
REPOSITORY_SCHEMA_VERSION = 1


def render_json(result: RepositoryCheck) -> str:
    """The stable machine-readable document, in the change check's style (COR-050 Implications)."""
    document = {
        "schema_version": REPOSITORY_SCHEMA_VERSION,
        "check": "repository",
        "mode": result.mode,
        "dormant": result.dormant,
        "failed": result.failed,
        "head": (
            None
            if result.head is None
            else {"commit": result.head.commit, "uncommitted_paths": result.head.uncommitted}
        ),
        "history": None if result.shallow is None else {"shallow": result.shallow},
        "counts": {
            "places": result.places,
            "artefacts": result.artefacts,
            "carrying": result.carrying,
            "checked": len(result.artefact_reports),
            "excluded": result.excluded,
            "surface": result.surface,
            **{kind.value: result.count(kind) for kind in RepositoryFindingKind},
        },
        "states": {state.value: result.state_count(state) for state in ArtefactState},
        "artefacts": [report.as_json() for report in result.artefact_reports],
        "findings": [finding.as_json() for finding in result.findings],
        "measures": {
            "unanchored": list(result.unanchored),
            "accepted_unanchored": [entry.as_json() for entry in result.accepted_unanchored],
            "uncovered_surface": list(result.uncovered),
        },
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


_LEGEND: dict[RepositoryFindingKind, str] = {
    RepositoryFindingKind.STALE: (
        "an anchor differs from what it stood on at the revalidation point, or the artefact "
        "moved or was let back in, with no answer"
    ),
    RepositoryFindingKind.DEFERRED: "friction deliberately postponed, since its deferral point",
    RepositoryFindingKind.LEFT_OUT: (
        "`friction.exclude` took files from an anchor, none changed since the point: owes nothing"
    ),
    RepositoryFindingKind.DEAD_ANCHOR: "an anchor resolving to nothing",
    RepositoryFindingKind.UNRESOLVED_KIND: (
        "an anchor of a kind nothing installed resolves: its artefact is not judged"
    ),
    RepositoryFindingKind.NO_ANSWER: (
        "a resolver gave no answer for an anchor: its artefact is not judged — run again"
    ),
    RepositoryFindingKind.OVER_BROAD: (
        f"an anchor standing on more than {round(100 * OVER_BROAD_SHARE)}% of the tracked files"
    ),
    RepositoryFindingKind.UNREACHABLE: "a point beyond this clone's history",
    RepositoryFindingKind.UNREADABLE: (
        "front matter, or a revalidation point's `friction.exclude`, the check cannot read"
    ),
}


def render_human(result: RepositoryCheck, *, now: datetime | None = None) -> str:
    """The read view: header, findings grouped by artefact upstream first, measures, legend."""
    now = datetime.now(UTC) if now is None else now
    title = cli_render.style("title", "Friction whole-repository check")
    if result.dormant:
        return "\n".join([f"{title} — dormant", "", *_dormant_lines(result)]) + "\n"

    lines = [
        f"{title} — {_summary(result) or 'nothing stale or deferred'}"
        + cli_render.style("muted", "   (reports only; the blocks: pkit validate)"),
        "",
        *_header_lines(result),
        "",
        cli_render.style("heading", "FINDINGS")
        + cli_render.style("muted", " — upstream first along artefact anchors"),
    ]
    rows = [f for f in result.findings if f.location is not None and f.artefact is not None]
    unreadable = [f for f in result.findings if f.kind is RepositoryFindingKind.UNREADABLE]
    if not rows and not unreadable:
        lines.append("  nothing to report")
    kind_width = max((len(f.kind.value) for f in rows + unreadable), default=0)
    anchor_width = max((len(_anchor_cell(f)) for f in rows), default=0)
    points: dict[str | None, ArtefactReport] = {r.location: r for r in result.artefact_reports}
    current: str | None = None
    for finding in rows:
        if finding.location != current:
            current = finding.location
            lines.append(f"  {current}{_point_note(points.get(current))}")
        message = finding.message
        if finding.kind is RepositoryFindingKind.DEFERRED and finding.origin is not None:
            message += f", {_age(now, finding.origin.date)}"
        cells = f"{finding.kind.value:{kind_width}}  {_anchor_cell(finding):{anchor_width}}"
        lines.append(f"    {cells}  {message}".rstrip())
    for finding in unreadable:
        lines.append(f"  {finding.location}")
        lines.append(f"    {finding.kind.value:{kind_width}}  {finding.message}")

    lines.extend(["", *_measure_lines(result)])
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
            "  pkit friction check --all --json   the same report, machine-readable",
            "  pkit friction check                the change check: working tree against base",
            "  pkit validate                      the blocks, deferrals and cycles themselves",
        ]
    )
    return "\n".join(lines) + "\n"


def _anchor_cell(finding: RepositoryFinding) -> str:
    return "—" if finding.anchor is None else f"{finding.anchor.kind} {finding.anchor.value}"


def _point_note(report: ArtefactReport | None) -> str:
    if report is None or report.revalidation_point is None:
        return ""
    point = report.revalidation_point
    cut = "; the clone is cut before it" if report.cut else ""
    return cli_render.style("muted", f"   (revalidation point {point.short}, {point.day}{cut})")


def _age(now: datetime, then: datetime) -> str:
    days = (now.astimezone(UTC) - then.astimezone(UTC)).days
    if days <= 0:
        return "today"
    return f"{counted(days, 'day', 'days')} ago"


def _header_lines(result: RepositoryCheck) -> list[str]:
    lines: list[str] = []
    if result.head is not None:
        lines.append(f"  Head: {result.head.commit[:SHORT]}")
        if result.head.uncommitted:
            lines.append(
                f"  ⚠ {counted(result.head.uncommitted, 'uncommitted path', 'uncommitted paths')} "
                f"not read: the check reads HEAD and its history — commit first to include them"
            )
    if result.shallow:
        lines.append(
            "  History: shallow clone — a value the clone's first commit already carries is "
            "unreachable, never guessed; one first carried inside the clone is read as first "
            "carried there, and its artefact says the clone was cut"
        )
    else:
        lines.append("  History: full")
    lines.append(
        f"  Mode: {result.mode}"
        + cli_render.style("muted", "   (reports only: the whole-repository check never fails)")
    )
    lines.extend(_mode_warning(result))
    return lines


def _dormant_lines(result: RepositoryCheck) -> list[str]:
    return ["  no places declared; dormant.", *_mode_warning(result)]


def _mode_warning(result: RepositoryCheck) -> list[str]:
    if result.mode_as_written is None or result.mode_as_written == result.mode:
        return []
    return [
        f"  ⚠ friction.mode {result.mode_as_written!r} is not a mode; read as {result.mode} "
        f"— `pkit validate` fails on it"
    ]


def _measure_lines(result: RepositoryCheck) -> list[str]:
    lines = [
        cli_render.style("heading", "MEASURES")
        + cli_render.style("muted", " — reported, never failed (COR-050 point 8)")
    ]
    measured = result.artefacts - result.excluded
    unanchored = f"  Unanchored artefacts: {len(result.unanchored)} of {measured} in the places"
    accepted = result.accepted_unanchored
    notes: list[str] = []
    if accepted:
        notes.append(f"{len(accepted)} accepted with a reason, listed apart")
    if result.excluded:
        notes.append(
            f"excluded paths left out: {counted(result.excluded, 'artefact', 'artefacts')}"
        )
    if notes:
        unanchored += f" ({'; '.join(notes)})"
    lines.append(unanchored)
    lines.extend(f"    {location}" for location in result.unanchored)
    if accepted:
        lines.append(f"  Accepted unanchored: {len(accepted)}, not counted — each with its reason")
        width = max(len(entry.location) for entry in accepted)
        lines.extend(f"    {entry.location:{width}}  {entry.reason}" for entry in accepted)
    if result.surface:
        surface = f"{len(result.uncovered)} of {result.surface} paths in the declared surface"
    else:
        surface = "no surface declared"
    lines.append(f"  Uncovered surface: {surface}")
    lines.extend(f"    {rel}" for rel in result.uncovered)
    return lines


def _summary(result: RepositoryCheck) -> str:
    parts = [
        (RepositoryFindingKind.STALE, "stale", "stale"),
        (RepositoryFindingKind.DEFERRED, "deferred", "deferred"),
        (RepositoryFindingKind.LEFT_OUT, "left-out anchor", "left-out anchors"),
        (RepositoryFindingKind.DEAD_ANCHOR, "dead anchor", "dead anchors"),
        (RepositoryFindingKind.UNRESOLVED_KIND, "unresolved kind", "unresolved kinds"),
        (RepositoryFindingKind.NO_ANSWER, "missing answer", "missing answers"),
        (RepositoryFindingKind.OVER_BROAD, "over-broad anchor", "over-broad anchors"),
        (RepositoryFindingKind.UNREACHABLE, "unreachable", "unreachable"),
    ]
    return ", ".join(
        counted(result.count(kind), one, many) for kind, one, many in parts if result.count(kind)
    )


def _result_line(result: RepositoryCheck) -> str:
    states = ", ".join(
        f"{result.state_count(state)} {state.value}"
        for state in ArtefactState
        if result.state_count(state)
    )
    checked = counted(len(result.artefact_reports), "artefact", "artefacts")
    detail = f"{checked} checked" + (f": {states}" if states else "")
    return cli_render.style("strong", "Result: reported") + f"   ({detail})"


__all__ = [
    "LET_BACK_IN",
    "OVER_BROAD_SHARE",
    "REPOSITORY_SCHEMA_VERSION",
    "UNRESOLVED_KINDS",
    "AcceptedUnanchored",
    "AnchorFiles",
    "ArtefactCheck",
    "ArtefactReport",
    "ArtefactState",
    "BlobReader",
    "Commit",
    "CommitBehind",
    "History",
    "MergeEntry",
    "RepositoryCheck",
    "RepositoryFinding",
    "RepositoryFindingKind",
    "TracedFinding",
    "Version",
    "read_history",
    "render_human",
    "render_json",
    "run_artefact_check",
    "run_repository_check",
]
