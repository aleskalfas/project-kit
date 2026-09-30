"""The whole-repository friction check: `pkit friction check --all` (COR-050 points 3–9, 11–13).

Every artefact in the declared places at HEAD is checked against the current
history with the rule of point 5: an anchor has changed when a commit
reachable from HEAD and not from the artefact's **revalidation point** touched
it. The points come from git, never from a ledger (point 9):

- the *revalidation point* is the last commit, following renames, in which
  the parsed value of `at` changed; for an artefact without `at`, the commit
  that introduced its block (point 3). A move after that point with no
  revalidation is reported, since rename detection may hide earlier changes.
- a *deferral point* is the commit that first introduced the deferral entry,
  by anchor kind and value; rewording its reason does not move it (point 4).
  A deferral covers its anchor up to its point only.

**Reading history — from git alone, per file and bounded.** One `git log
--name-status -M -c` from HEAD lists every commit with the paths it touched
(`read_history`) — a merge commit with the paths it changed against every
parent, git's combined diff, so what a merge itself wrote is read like any
other commit; everything else is matched against that listing in memory:
which commits a point reaches (its ancestors, from the parent lists), each
file's names over time with renames followed (`History.versions`), and which
commits touched a path (`History.touched`). A file's earlier versions are
read, newest first, through one `git cat-file --batch` process (`BlobReader`)
and parsed by the same reading as the present (`parse_artefacts`), each
judged against the file's state at each parent of its commit — what `git
log` diffed it against, never whatever the log lists next — and no blob is
read beyond the oldest point in question: never one log per anchor, never a
file's contents through its history for their own sake.

**What it reports** (points 7, 8, 11, 12), per artefact, upstream first
along artefact anchors: *stale* — an anchor changed after the revalidation
point, beyond what a deferral covers, or the artefact moved after the point
with no revalidation — with its origin, the first such commit (author, date,
change); *deferred* — every deferral, with its point's origin and, in the
human view, its age; dead anchors and unresolved kinds, all of them, not only
a change's; *over-broad* anchors. Then the two measures: unanchored artefacts
within the places and uncovered surface, excluded paths ignored. It never
fails (point 12): exit 0 in either mode. Dormant while no place is declared.

A shallow clone whose history stops before a point is reported for the
artefacts concerned, never guessed at.

The check writes nothing (point 13). The computations it shares with the
change check — discovery, content, the parsed marker, what a path pattern
stands on (`Side.stands_on`), what a dead anchor is, truth-chain order — have
their one home in `friction_check` and `friction_discovery` (ADR-057 point 2).
"""

from __future__ import annotations

import bisect
import json
import subprocess
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from project_kit import cli_render
from project_kit.friction_check import (
    SHORT,
    CommitTree,
    DiffEntry,
    FrictionCheckError,
    HeadState,
    Side,
    anchors_of,
    commit_of,
    content,
    counted,
    deferral_reason,
    parse_name_status,
    parsed_at,
    run_git,
    truth_chain_order,
    uncommitted_paths,
)
from project_kit.friction_discovery import (
    Anchor,
    Artefact,
    ArtefactKind,
    Discovery,
    ResolverCommand,
    discover_artefacts,
    parse_artefacts,
    read_friction_settings,
    registered_anchor_kinds,
    unresolved_kind_reason,
)

#: The share of the tracked files (excluded paths left out) above which a
#: path anchor is over-broad (COR-050 point 7: "broad enough to match most
#: changes"). *Most* is more than half. The share of files stands in for the
#: share of changes: changes are not spread evenly over files, but the file
#: share is what HEAD alone can answer, deterministically, without guessing
#: at what will change next.
OVER_BROAD_SHARE = 0.5

# A record of the log starts with this byte; the fields inside are NUL-separated.
_RECORD_START = "\x01"
_LOG_FORMAT = f"--format={_RECORD_START}%H%x00%P%x00%an%x00%aI%x00%s"


# --- findings ----------------------------------------------------------------


class RepositoryFindingKind(Enum):
    """What a finding of the whole-repository check is; the `kind` field of the JSON output."""

    STALE = "stale"
    DEFERRED = "deferred"
    DEAD_ANCHOR = "dead-anchor"
    UNRESOLVED_KIND = "unresolved-kind"
    OVER_BROAD = "over-broad"
    UNREACHABLE = "unreachable"
    UNREADABLE = "unreadable"


class ArtefactState(Enum):
    """What the check found for one artefact with anchors; stale wins over deferred (point 10)."""

    CURRENT = "current"
    STALE = "stale"
    DEFERRED = "deferred"
    UNREACHABLE = "unreachable"


@dataclass(frozen=True)
class Commit:
    """One commit of the history: what git says about it, and the paths it touched."""

    sha: str
    parents: tuple[str, ...]
    author: str
    date: datetime  # the author date
    subject: str
    entries: tuple[DiffEntry, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "commit": self.sha,
            "author": self.author,
            "date": self.date.isoformat(),
            "change": self.subject,
        }

    @property
    def short(self) -> str:
        return self.sha[:SHORT]

    @property
    def day(self) -> str:
        return self.date.astimezone(UTC).date().isoformat()


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
    """One checked artefact: its points, as derived from git, and its state."""

    artefact: str
    location: str
    state: ArtefactState
    revalidation_point: Commit | None  # `None` when unreachable
    deferral_points: tuple[tuple[Anchor, Commit | None], ...]  # in written order

    def as_json(self) -> dict[str, Any]:
        return {
            "artefact": self.artefact,
            "location": self.location,
            "state": self.state.value,
            "revalidation_point": (
                None if self.revalidation_point is None else self.revalidation_point.as_json()
            ),
            "deferral_points": [
                {
                    "anchor": {"kind": anchor.kind, "value": anchor.value},
                    "point": None if point is None else point.as_json(),
                }
                for anchor, point in self.deferral_points
            ],
        }


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
    unanchored: tuple[str, ...]  # locations of artefacts without anchors (point 8)
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


# --- the history, from one log -----------------------------------------------


@dataclass(frozen=True)
class MergeEntry(DiffEntry):
    """A path a merge commit changed against every parent, as git's combined diff lists it.

    What the merge wrote itself — resolving a conflict, or revalidating while
    merging — never what it took from one side, which that side's commits
    carry. `sources` is the file's name at each parent, in parent order;
    `None` where that parent has no such file. The status reads as a single
    commit's would: `A` when no parent has the file, `D` when the merge
    removed it, `R` from `old_path` when every parent has it under that one
    other name, `M` otherwise.
    """

    sources: tuple[str | None, ...] = ()


@dataclass(frozen=True)
class Version:
    """One state of a file in its history: the commit that produced it and the file's name then."""

    index: int  # the commit's position in the log: 0 is the newest
    path: str
    entry: DiffEntry

    @property
    def sources(self) -> tuple[str | None, ...]:
        """The file's name at each parent of the commit, in parent order; `None` where none."""
        entry = self.entry
        if isinstance(entry, MergeEntry):
            return entry.sources
        if entry.status == "A":
            return (None,)
        if entry.status == "R" and entry.old_path is not None:
            return (entry.old_path,)
        return (self.path,)


class History:
    """Every commit reachable from HEAD, newest first, matched in memory.

    The order is the log's `--date-order`: by commit date, but no parent
    before all of its children, so whatever a walk stops at, every descendant
    of it has been seen. Answers three questions without a further `git
    log`: which commits a point reaches (`ancestors`), which commits touched
    a path (`touched`), and what names a file had over time (`versions`,
    renames followed as git's rename detection paired them). A merge commit
    lists only the paths it changed against every parent (`MergeEntry`): what
    it took from one side, that side's commits carry. `shallow` names the
    commits at which a shallow clone's history is cut.
    """

    def __init__(self, commits: Sequence[Commit], shallow: frozenset[str]) -> None:
        self.commits = tuple(commits)
        self.shallow = shallow
        self._index = {c.sha: i for i, c in enumerate(self.commits)}
        self._by_path: list[dict[str, DiffEntry]] = []
        self._touched: dict[str, list[int]] = {}
        for i, commit in enumerate(self.commits):
            by_path: dict[str, DiffEntry] = {}
            for entry in commit.entries:
                by_path.setdefault(entry.path, entry)
                self._touched.setdefault(entry.path, []).append(i)
                if entry.old_path is not None:
                    self._touched.setdefault(entry.old_path, []).append(i)
            self._by_path.append(by_path)
        self.paths: tuple[str, ...] = tuple(sorted(self._touched))
        """Every path any commit touched, sorted."""
        self._ancestors: dict[int, frozenset[int]] = {}

    def touched(self, path: str) -> Sequence[int]:
        """The commits that touched `path`, newest first — either side of a rename counts."""
        return self._touched.get(path, ())

    def ancestors(self, index: int) -> frozenset[int]:
        """The commits the commit at `index` reaches, itself included, within this clone."""
        found = self._ancestors.get(index)
        if found is not None:
            return found
        seen: set[int] = set()
        stack = [index]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for parent in self.commits[current].parents:
                position = self._index.get(parent)
                if position is not None:
                    stack.append(position)
        found = frozenset(seen)
        self._ancestors[index] = found
        return found

    def versions(self, path: str) -> Iterator[Version]:
        """The states of the file now at `path`, newest first, back to where it was added.

        A rename switches to the file's earlier name; a deletion carries no
        state and is skipped; an addition is the last state.
        """
        current = path
        start = 0
        while True:
            indices = self._touched.get(current, [])
            position = bisect.bisect_left(indices, start)
            entry: DiffEntry | None = None
            while position < len(indices):
                entry = self._by_path[indices[position]].get(current)
                if entry is not None:
                    break
                position += 1
            if entry is None:
                return
            index = indices[position]
            start = index + 1
            if entry.status == "D":
                continue
            yield Version(index, current, entry)
            if entry.status == "R" and entry.old_path is not None:
                current = entry.old_path
            elif entry.status == "A":
                return

    def is_cut(self, index: int) -> bool:
        """Whether the commit at `index` is where a shallow clone's history stops."""
        return self.commits[index].sha in self.shallow


def read_history(root: Path, head: str) -> History:
    """`git log --name-status -M -c` from `head`: one listing for the whole check.

    `-c` lists a merge commit with the paths it changed against every parent
    — git's combined diff — and `--combined-all-paths` with the file's name
    at each parent; without them a merge lists nothing, and what it wrote
    itself, a revalidation among it, would go unseen. It adds the merges'
    diffs to the same one log, never a further one. `--date-order` keeps
    every parent after all of its children, so the log order the walks rely
    on is a topological one even under skewed clocks.
    `--root` lists the root commit's paths — and a shallow clone's boundary
    commit's, which git shows as a root — whatever `log.showRoot` says.
    """
    raw = run_git(
        root,
        "log",
        "-z",
        "--no-color",
        "--no-decorate",
        "--no-show-signature",
        "--date-order",
        "--root",
        _LOG_FORMAT,
        "--name-status",
        "-M",
        "-c",
        "--combined-all-paths",
        head,
        "--",
    ).stdout
    commits: list[Commit] = []
    for record in raw.decode("utf-8", "surrogateescape").split(_RECORD_START):
        if not record:
            continue
        fields = record.split("\0")
        sha, parents, author, date, subject = fields[:5]
        rest = fields[5:]
        if rest and rest[0].startswith("\n"):
            rest[0] = rest[0][1:]
        tokens = [token for token in rest if token]
        listed = tuple(parents.split())
        entries = (
            _merge_entries(tokens, len(listed)) if len(listed) > 1 else parse_name_status(tokens)
        )
        commits.append(
            Commit(
                sha=sha,
                parents=listed,
                author=author,
                date=datetime.fromisoformat(date),
                subject=subject,
                entries=tuple(entries),
            )
        )
    return History(commits, _shallow_commits(root))


def _merge_entries(tokens: Sequence[str], parents: int) -> list[DiffEntry]:
    """The entries of a merge commit in a NUL-separated combined listing (`MergeEntry`).

    Each is one status letter per parent, the file's name at each parent, and
    its name in the merge: `-c --combined-all-paths --name-status -z`.
    """
    entries: list[DiffEntry] = []
    width = parents + 2
    for start in range(0, len(tokens) - width + 1, width):
        letters = tokens[start]
        named = tokens[start + 1 : start + 1 + parents]
        path = tokens[start + 1 + parents]
        sources = tuple(
            None if letter == "A" else name for letter, name in zip(letters, named, strict=True)
        )
        status, old_path = "M", None
        if all(source is None for source in sources):
            status = "A"
        elif set(letters) == {"D"}:
            status = "D"
        elif set(letters) == {"R"} and len(set(sources)) == 1:
            status, old_path = "R", sources[0]
        entries.append(MergeEntry(status, path, old_path, None, sources))
    return entries


def _shallow_commits(root: Path) -> frozenset[str]:
    """The commits at which a shallow clone is cut; empty for a full clone."""
    shallow = run_git(root, "rev-parse", "--is-shallow-repository").stdout.decode().strip()
    if shallow != "true":
        return frozenset()
    listed = run_git(root, "rev-parse", "--git-path", "shallow").stdout.decode().strip()
    path = Path(listed) if Path(listed).is_absolute() else root / listed
    try:
        return frozenset(line.strip() for line in path.read_text().splitlines() if line.strip())
    except OSError:
        return frozenset()


class BlobReader:
    """One `git cat-file --batch` process, answering `<commit>:<path>` requests as they come."""

    def __init__(self, root: Path) -> None:
        try:
            self._process = subprocess.Popen(
                ["git", "cat-file", "--batch"],
                cwd=root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise FrictionCheckError(f"cannot run git: {exc}") from exc

    def read(self, commit: str, path: str) -> bytes | None:
        """The blob at `path` in `commit`, or `None` when the commit holds no file there."""
        if "\n" in path:
            return None
        assert self._process.stdin is not None and self._process.stdout is not None
        try:
            self._process.stdin.write(f"{commit}:{path}\n".encode("utf-8", "surrogateescape"))
            self._process.stdin.flush()
            header = self._process.stdout.readline().split()
            # `<name> missing` or `<name> ambiguous` end in that word; a hit is
            # `<object> <type> <size>`, and neither an object name nor a type
            # holds a space, so a path with spaces cannot be mistaken for one.
            if not header or header[-1] in (b"missing", b"ambiguous") or len(header) != 3:
                return None
            size = int(header[2])
            data = self._process.stdout.read(size)
            self._process.stdout.read(1)  # the newline after the content
        except (OSError, ValueError) as exc:
            raise FrictionCheckError(f"`git cat-file` failed: {exc}") from exc
        return data if header[1] == b"blob" else None

    def close(self) -> None:
        if self._process.stdin is not None:
            self._process.stdin.close()
        self._process.wait()


# --- points and changes, per artefact ----------------------------------------


@dataclass(frozen=True)
class Points:
    """What the walk back through one artefact's file found (COR-050 points 3 and 4)."""

    revalidation: int | None  # the revalidation point's log index; `None` when unreachable
    deferrals: tuple[tuple[Anchor, int | None], ...]  # each deferral's point, in written order
    moves: tuple[Version, ...]  # renames not reached from the revalidation point, unanswered
    own_paths: frozenset[str]  # every name the file had: a change under one is never an anchor's
    unreachable: str | None  # which point the clone's history does not reach, when one


class _Walker:
    """Reads an artefact's earlier versions, newest first and no further than needed."""

    def __init__(self, history: History, blobs: BlobReader) -> None:
        self._history = history
        self._blobs = blobs
        self._parsed: dict[tuple[str, str], list[Artefact]] = {}

    def _artefacts(self, commit: str, path: str, like: Artefact) -> list[Artefact]:
        """The artefacts `path` held in `commit`, read by the same rule as the present."""
        key = (commit, path)
        found = self._parsed.get(key)
        if found is None:
            raw = self._blobs.read(commit, path)
            found = []
            if raw is not None:
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = None
                if text is not None:
                    found, _reason = parse_artefacts(path, like.place, text, rule_set=like.rule_set)
            self._parsed[key] = found
        return found

    def _same(self, commit: str, path: str, artefact: Artefact) -> Artefact | None:
        for candidate in self._artefacts(commit, path, artefact):
            if candidate.kind is not artefact.kind:
                continue
            if artefact.kind is ArtefactKind.DOCUMENT or candidate.id == artefact.id:
                return candidate
        return None

    def same_at(self, version: Version, artefact: Artefact) -> Artefact | None:
        """`artefact` as it was at `version`: the document, or the entry under the same id."""
        return self._same(self._history.commits[version.index].sha, version.path, artefact)

    def same_in_parents(self, version: Version, artefact: Artefact) -> tuple[Artefact | None, ...]:
        """`artefact` as the file stood at each parent of `version`'s commit, in parent order.

        Those are the states `git log` diffed the version against, each read
        under the file's name at that parent; `None` where a parent has no
        such file, and a root's one `None`.
        """
        parents = self._history.commits[version.index].parents
        if not parents:
            return (None,)
        return tuple(
            None if source is None else self._same(parent, source, artefact)
            for parent, source in zip(parents, version.sources, strict=True)
        )

    def points(self, artefact: Artefact) -> Points:
        """Walk back from HEAD until the revalidation point and every deferral point are found.

        Each version is judged against the file's state at each parent of its
        commit: a point is the newest commit, in log order, at which the
        marker — or the deferral entry — differs from every parent's (`_changed`).
        So a version on a merged branch is compared with its own ancestor,
        never with whatever the log lists next; a merge commit that wrote a
        new marker while merging is that marker's point, and one that kept a
        side's marker is not — the side's own commit is. When no listed
        commit shows the change, the point is the commit that added the file.
        Once every point is found the walk goes on without reading a blob,
        for the file's names and its renames.
        """
        at = parsed_at(artefact)

        def marker(version: Artefact | None) -> Any:
            # With `at`, its parsed value; without, whether the block is there (point 3).
            if at is not None:
                return None if version is None else parsed_at(version)
            return version is not None and version.has_friction_block

        wanted = [d.anchor for d in artefact.deferrals]
        pending = set(wanted)
        deferral_points: dict[Anchor, int | None] = {}
        revalidation: int | None = None
        renames: list[Version] = []
        own: set[str] = {artefact.path}
        unreachable: str | None = None
        oldest: Version | None = None

        for version in self._history.versions(artefact.path):
            oldest = version
            own.add(version.path)
            own.update(source for source in version.sources if source is not None)
            if version.entry.status == "R":
                renames.append(version)
            if revalidation is not None and not pending:
                continue  # every point is found: only the names and the renames are still wanted
            if self._history.is_cut(version.index):
                # Its parent is beyond the clone: whether anything changed here cannot be told.
                if revalidation is None:
                    unreachable = "its revalidation point"
                for anchor in pending:
                    unreachable = (
                        unreachable or f"the deferral point of {anchor.kind} {anchor.value}"
                    )
                break
            here = self.same_at(version, artefact)
            before = self.same_in_parents(version, artefact)
            if revalidation is None and _changed(marker, here, before):
                revalidation = version.index
            for anchor in list(pending):
                if _defers(here, anchor) and not any(_defers(p, anchor) for p in before):
                    pending.discard(anchor)
                    deferral_points[anchor] = version.index

        if oldest is None:
            return Points(
                None,
                tuple((a, None) for a in wanted),
                (),
                frozenset(own),
                "the commit that added its file (none in this clone touches it)",
            )
        if unreachable is None:
            # No listed commit shows the change: the file's history, as git's
            # rename detection pairs it, ends first. Its oldest state is the point.
            if revalidation is None:
                revalidation = oldest.index
            for anchor in pending:
                deferral_points[anchor] = oldest.index
        moves: tuple[Version, ...] = ()
        if revalidation is not None:
            reached = self._history.ancestors(revalidation)
            moves = tuple(v for v in renames if v.index not in reached)
        return Points(
            revalidation=revalidation,
            deferrals=tuple((a, deferral_points.get(a)) for a in wanted),
            moves=moves,
            own_paths=frozenset(own),
            unreachable=unreachable,
        )


def _defers(artefact: Artefact | None, anchor: Anchor) -> bool:
    return artefact is not None and any(d.anchor == anchor for d in artefact.deferrals)


def _changed(
    value: Callable[[Artefact | None], Any],
    here: Artefact | None,
    parents: Sequence[Artefact | None],
) -> bool:
    """Whether a commit changed `value`: it differs from its value at every parent of the commit.

    One parent for a single commit. A merge commit changed it only when it
    wrote a value no parent had — one kept from a side is that side's change.
    """
    now = value(here)
    return all(value(parent) != now for parent in parents)


@dataclass(frozen=True)
class Change:
    """The first commit, after what a point covers, in which an anchor's target changed."""

    origin: int  # the log index of that commit


class _Judge:
    """Applies COR-050 point 5 to one repository state against its history."""

    def __init__(
        self,
        head: Side,
        history: History,
        walker: _Walker,
        registry: Mapping[str, ResolverCommand],
    ) -> None:
        self.head = head
        self.history = history
        self.walker = walker
        self.registry = registry
        self._matching: dict[str, frozenset[str]] = {}
        self._tracked = frozenset(rel for rel in head.files if not head.excluded(rel))

    def problem(self, anchor: Anchor) -> RepositoryFinding | None:
        """A dead anchor or an unresolved kind at HEAD (point 7), else `None`."""
        reason = unresolved_kind_reason(anchor.kind, self.registry)
        if reason is not None:
            message = f"nothing installed resolves this kind: {reason}"
            return RepositoryFinding(RepositoryFindingKind.UNRESOLVED_KIND, message, anchor=anchor)
        if self.head.resolves(anchor):
            return None
        return RepositoryFinding(
            RepositoryFindingKind.DEAD_ANCHOR, self.head.why_dead(anchor), anchor=anchor
        )

    def over_broad(self, anchor: Anchor) -> RepositoryFinding | None:
        """A path anchor matching more than `OVER_BROAD_SHARE` of the tracked files (point 7)."""
        if anchor.kind != "path" or not self._tracked:
            return None
        matched = sum(map(self.head.stands_on(anchor.value), self.head.files))
        total = len(self._tracked)
        if matched <= total * OVER_BROAD_SHARE:
            return None
        share = round(100 * matched / total)
        message = (
            f"matches {matched} of {total} tracked files ({share}%): most changes would make it "
            f"a revalidation, which teaches people to bump the marker blindly — narrow it"
        )
        return RepositoryFinding(RepositoryFindingKind.OVER_BROAD, message, anchor=anchor)

    def matching_paths(self, pattern: str) -> frozenset[str]:
        """Every path the history touched that `pattern` covers, excluded paths left out."""
        found = self._matching.get(pattern)
        if found is None:
            found = frozenset(self.head.matching(pattern, self.history.paths))
            self._matching[pattern] = found
        return found

    def changes(self, anchor: Anchor, covered: frozenset[int], own: frozenset[str]) -> set[int]:
        """Every commit outside `covered` that changed a live path or record anchor (point 5).

        A path anchor: each commit that touched a path it stands on in history,
        the artefact's own names (`own`) left out. A record anchor: each commit
        that changed the content of the record's file. One pass over the
        history's listing, however many there are.
        """
        if anchor.kind == "path":
            return {
                index
                for rel in self.matching_paths(anchor.value) - own
                for index in self.history.touched(rel)
                if index not in covered
            }
        rel = self.head.record_path(anchor.value) if anchor.kind == "record" else None
        if rel is None:
            return set()
        return {
            v.index
            for v in self.history.versions(rel)
            if v.index not in covered and v.entry.changes_content
        }

    def change(self, anchor: Anchor, covered: frozenset[int], own: frozenset[str]) -> Change | None:
        """Whether a live anchor of a core kind changed outside `covered`, and where (point 5).

        The first such commit: for a path or a record, the oldest of `changes`.
        """
        if anchor.kind in ("path", "record"):
            after = self.changes(anchor, covered, own)
            return Change(max(after)) if after else None
        target = self.head.find(anchor.value)
        if target is None:
            return None
        return self._content_change(target, covered)

    def _content_change(self, target: Artefact, covered: frozenset[int]) -> Change | None:
        """The first commit outside `covered` that changed `target`'s content, net of later ones."""
        chain = list(self.history.versions(target.path))
        after = [v for v in chain if v.index not in covered]
        if not after:
            return None
        before = next((v for v in chain if v.index in covered), None)
        base = None if before is None else self.walker.same_at(before, target)
        base_content = None if base is None else content(base)
        if content(target) == base_content:
            return None
        for version in reversed(after):  # oldest first
            then = self.walker.same_at(version, target)
            if (None if then is None else content(then)) != base_content:
                return Change(version.index)
        return Change(after[-1].index)


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
    registry = registered_anchor_kinds(target_root) if registry is None else registry
    history = read_history(target_root, head_sha)
    blobs = BlobReader(target_root)
    try:
        judge = _Judge(head, history, _Walker(history, blobs), registry)
        reports: list[ArtefactReport] = []
        findings: list[RepositoryFinding] = []
        for index in truth_chain_order(discovery):
            artefact = discovery.artefacts[index]
            if artefact.has_friction_block and (anchors_of(artefact) or artefact.deferrals):
                report, found = _check_artefact(artefact, judge)
                reports.append(report)
                findings.extend(found)
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
    surface, uncovered = _uncovered_surface(head, discovery)
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
        unanchored=tuple(a.location for a in discovery.artefacts if not anchors_of(a)),
        surface=surface,
        uncovered=uncovered,
    )


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
        surface=0,
        uncovered=(),
    )


def _check_artefact(
    artefact: Artefact, judge: _Judge
) -> tuple[ArtefactReport, list[RepositoryFinding]]:
    """The report and findings about one artefact carrying anchors or deferrals."""

    def finding(
        kind: RepositoryFindingKind,
        message: str,
        anchor: Anchor | None = None,
        origin: int | None = None,
    ) -> RepositoryFinding:
        commit = None if origin is None else judge.history.commits[origin]
        return RepositoryFinding(kind, message, artefact.id, artefact.location, anchor, commit)

    points = judge.walker.points(artefact)
    commits = judge.history.commits
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
            tuple(
                (a, None if p is None else commits[p]) for a, p in points.deferrals
            ),
        )
        unreachable = [finding(RepositoryFindingKind.UNREACHABLE, message)]
        return report, unreachable + problems + broad

    point = commits[points.revalidation]
    reached = judge.history.ancestors(points.revalidation)
    for move in points.moves:
        moved = commits[move.index]
        stale.append(
            finding(
                RepositoryFindingKind.STALE,
                f"moved here from {move.entry.old_path} in {moved.short} \"{moved.subject}\" "
                f"({moved.author}, {moved.day}) after its revalidation point {point.short} "
                f"({point.day}), with no revalidation since — revalidate the artefact",
                origin=move.index,
            )
        )
    for anchor in live:
        deferral_point = deferral_points.get(anchor)
        covered = reached
        if deferral_point is not None:
            covered = covered | judge.history.ancestors(deferral_point)
        change = judge.change(anchor, covered, points.own_paths)
        if change is None:
            continue
        origin = commits[change.origin]
        message = (
            f"changed after its revalidation point {point.short} ({point.day}): first in "
            f"{origin.short} \"{origin.subject}\" ({origin.author}, {origin.day})"
        )
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
            f"\"{since.subject}\" ({since.author}, {since.day})"
        )
        deferred.append(finding(RepositoryFindingKind.DEFERRED, message, anchor, deferral_point))

    if stale:
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
    )
    return report, stale + deferred + problems + broad


def _uncovered_surface(head: Side, discovery: Discovery) -> tuple[int, tuple[str, ...]]:
    """How many paths the declared surface holds at HEAD, and those no artefact anchors to.

    The surface is what the project and its capabilities say ought to be
    described (COR-050 point 8), excluded paths left out. A path is anchored
    when any artefact's path anchor stands on it (`Side.stands_on`), a record
    anchor names it, or an artefact anchor names the artefact it holds.
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
    return len(surface), tuple(sorted(surface - anchored))


# --- one artefact, with the commits behind each finding ------------------------------
#
# `pkit friction explain` judges one artefact exactly as the check does — through
# `_check_artefact`, on a judge built as `run_repository_check` builds it — and adds,
# per finding, the commits behind it, read from the same history by the same rules,
# and per path anchor the files it stands on, matched by the rule the check decides
# a dead anchor by (`Side.matching`), with those `friction.exclude` leaves out.


@dataclass(frozen=True)
class CommitBehind:
    """One commit behind a finding, and the paths behind the finding it touched.

    `paths`, sorted — what a reader limits the commit to. A path anchor: the
    paths it stands on in history that the commit touched, the artefact's own
    file under any of its names left out (`_Judge.matching_paths` less the
    walk's own paths) — exactly what the check reads as the anchor's change,
    which the anchor's `AnchorFiles` are not. A record or artefact anchor: the
    file it names, under the names the commit touched. A move: the artefact's
    file under both its names. Either side of a rename counts, as the check
    counts it.
    """

    commit: Commit
    paths: tuple[str, ...]

    def as_json(self) -> dict[str, Any]:
        return {**self.commit.as_json(), "paths": list(self.paths)}


@dataclass(frozen=True)
class TracedFinding:
    """A finding of the whole-repository check about one artefact, and the commits behind it.

    `commits` are oldest first, each with the paths behind the finding it
    touched (`CommitBehind`). Stale on an anchor: every commit outside what
    the points cover that changed the anchor, the finding's origin among them;
    stale by a move: the rename. Deferred: the changes the deferral postpones —
    after the revalidation point, up to the deferral point. A dead `path`
    anchor: every commit after the revalidation point that touched a path it
    matched — how its files went; a dead record or artefact anchor names no
    file whose history could be read. Any other finding, or an artefact whose
    points lie beyond a shallow clone: none.
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
    commits carry those). Both states are read under HEAD's exclusions, the
    rule the check reads history by. `point` is `None` when the revalidation
    point lies beyond a shallow clone's history. `head` is empty for a dead
    anchor, and `excluded` (`Side.left_out`) says whether it is dead by a
    typo — nothing excluded either — or by a glob that covers only excluded
    files.
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
    `findings` and `files` are then empty. Otherwise both are the check's own
    for this artefact, the findings in its order, and `files` holds each path
    anchor's files (`AnchorFiles`).
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
        return ArtefactCheck(head, bool(_shallow_commits(target_root)), artefact, None, ())
    registry = registered_anchor_kinds(target_root) if registry is None else registry
    history = read_history(target_root, head_sha)
    blobs = BlobReader(target_root)
    try:
        side = Side(target_root, tree, discovery)
        judge = _Judge(side, history, _Walker(history, blobs), registry)
        report, findings = _check_artefact(artefact, judge)
        traced = _traced(artefact, judge, findings)
    finally:
        blobs.close()
    files = _anchor_files(target_root, side, artefact, report.revalidation_point)
    return ArtefactCheck(head, bool(history.shallow), artefact, report, traced, files)


def _anchor_files(
    target_root: Path, head: Side, artefact: Artefact, point: Commit | None
) -> dict[Anchor, AnchorFiles]:
    """Each path anchor's files at the revalidation point and at HEAD, and those
    `friction.exclude` leaves out at HEAD (`AnchorFiles`).

    The point's files are listed from git objects, once, and only when the
    artefact has a path anchor; both states are matched under HEAD's exclusions.
    """
    anchors = [anchor for anchor in anchors_of(artefact) if anchor.kind == "path"]
    if not anchors:
        return {}
    listed = None if point is None else CommitTree(target_root, point.sha).files()
    return {
        anchor: AnchorFiles(
            None if listed is None else head.matching(anchor.value, listed),
            head.matching(anchor.value),
            head.left_out(anchor.value),
        )
        for anchor in anchors
    }


def _traced(
    artefact: Artefact, judge: _Judge, findings: Sequence[RepositoryFinding]
) -> tuple[TracedFinding, ...]:
    """Each finding with the commits behind it (see `TracedFinding`)."""
    history = judge.history
    points = judge.walker.points(artefact)  # the check's walk again: its blobs are cached
    if points.unreachable is not None or points.revalidation is None:
        return tuple(TracedFinding(f, ()) for f in findings)
    position = {commit.sha: index for index, commit in enumerate(history.commits)}
    reached = history.ancestors(points.revalidation)
    deferral_points = {anchor: point for anchor, point in points.deferrals if point is not None}
    traced: list[TracedFinding] = []
    for finding in findings:
        anchor = finding.anchor
        behind: set[int] = set()
        if finding.kind is RepositoryFindingKind.STALE and finding.origin is not None:
            behind.add(position[finding.origin.sha])
            if anchor is not None:
                covered = reached
                if anchor in deferral_points:
                    covered = covered | history.ancestors(deferral_points[anchor])
                behind.update(_changes(judge, anchor, covered, points.own_paths))
        elif (
            finding.kind is RepositoryFindingKind.DEAD_ANCHOR
            and anchor is not None
            and anchor.kind == "path"
        ):
            behind.update(_changes(judge, anchor, reached, points.own_paths))
        elif (
            finding.kind is RepositoryFindingKind.DEFERRED
            and anchor in deferral_points
            and judge.problem(anchor) is None
        ):
            postponed = history.ancestors(deferral_points[anchor])
            behind.update(
                index
                for index in _changes(judge, anchor, reached, points.own_paths)
                if index in postponed
            )
        touched = _touched_by(history, _paths_behind(judge, anchor, points.own_paths), behind)
        commits = tuple(
            CommitBehind(history.commits[index], tuple(sorted(touched.get(index, ()))))
            for index in sorted(behind, reverse=True)
        )
        traced.append(TracedFinding(finding, commits))
    return tuple(traced)


def _paths_behind(judge: _Judge, anchor: Anchor | None, own: frozenset[str]) -> frozenset[str]:
    """Every path whose change a finding on `anchor` reads (`CommitBehind`).

    A path anchor's paths are the check's own (`_Judge.matching_paths`, less
    `own`); a record or artefact anchor's the names of the file it names; a
    move's (no anchor) the artefact's own names.
    """
    if anchor is None:
        return own
    if anchor.kind == "path":
        return judge.matching_paths(anchor.value) - own
    if anchor.kind == "record":
        rel = judge.head.record_path(anchor.value)
    else:
        target = judge.head.find(anchor.value)
        rel = None if target is None else target.path
    return frozenset() if rel is None else _names(judge.history, rel)


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


def _changes(
    judge: _Judge, anchor: Anchor, covered: frozenset[int], own: frozenset[str]
) -> set[int]:
    """Every commit outside `covered` that changed a live anchor's target (COR-050 point 5),
    or that touched a path a dead path anchor matched in history.

    A path or a record: `_Judge.changes`, whose oldest is the check's own
    origin, so the rule is the check's. An artefact: each commit at which the
    target's content differs from its content at every parent of the commit
    (`_changed`) — the check asks only whether the content at HEAD differs
    from the content the point saw.
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
            and _changed(
                _content_of,
                walker.same_at(version, target),
                walker.same_in_parents(version, target),
            )
        }
    return judge.changes(anchor, covered, own)


def _content_of(artefact: Artefact | None) -> tuple[str, dict[str, Any]] | None:
    return None if artefact is None else content(artefact)


# --- output --------------------------------------------------------------------------


def render_json(result: RepositoryCheck) -> str:
    """The stable machine-readable document, in the change check's style (COR-050 Implications)."""
    document = {
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
            "surface": result.surface,
            **{kind.value: result.count(kind) for kind in RepositoryFindingKind},
        },
        "states": {state.value: result.state_count(state) for state in ArtefactState},
        "artefacts": [report.as_json() for report in result.artefact_reports],
        "findings": [finding.as_json() for finding in result.findings],
        "measures": {
            "unanchored": list(result.unanchored),
            "uncovered_surface": list(result.uncovered),
        },
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


_LEGEND: dict[RepositoryFindingKind, str] = {
    RepositoryFindingKind.STALE: (
        "an anchor changed after the revalidation point, or the artefact moved, with no answer"
    ),
    RepositoryFindingKind.DEFERRED: "friction deliberately postponed, since its deferral point",
    RepositoryFindingKind.DEAD_ANCHOR: "an anchor resolving to nothing",
    RepositoryFindingKind.UNRESOLVED_KIND: "an anchor kind no installed component resolves",
    RepositoryFindingKind.OVER_BROAD: (
        f"a path anchor matching more than {round(100 * OVER_BROAD_SHARE)}% of the tracked files"
    ),
    RepositoryFindingKind.UNREACHABLE: "a point beyond this clone's history",
    RepositoryFindingKind.UNREADABLE: "front matter the check cannot parse",
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
    return cli_render.style("muted", f"   (revalidation point {point.short}, {point.day})")


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
            "  History: shallow clone — a point beyond it is reported as unreachable, never guessed"
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
    lines.append(
        f"  Unanchored artefacts: {len(result.unanchored)} of {result.artefacts} in the places"
    )
    lines.extend(f"    {location}" for location in result.unanchored)
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
        (RepositoryFindingKind.DEAD_ANCHOR, "dead anchor", "dead anchors"),
        (RepositoryFindingKind.UNRESOLVED_KIND, "unresolved kind", "unresolved kinds"),
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
    "OVER_BROAD_SHARE",
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
