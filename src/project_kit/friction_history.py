"""How a point is found, and where a change originates (COR-050 points 3, 4, 5 and 9).

Both friction checks read an artefact's history through this module: the
whole-repository check from HEAD, the change check from its base, where a
change alters an artefact's `at` or brings back a deferral (point 6).

**The one log** (`read_history`). One `git log --raw -M -c` from a commit
lists every commit with the paths it touched — a merge commit with the paths
it changed against every parent, git's combined diff, so what a merge wrote
itself is read like any other commit — and, for each path, the file's mode
and object after the commit and at each parent (`DiffEntry.after`,
`DiffEntry.before`). Everything else is matched in memory: which commits a
point reaches (`History.ancestors`), which commits touched a path
(`History.touched`), a file's names over time (`History.versions`, renames
followed as git's rename detection paired them).

**The revalidation point** (point 3; `Walker.carried`). An artefact's history
is its file's, renames followed, back to where the file was last added — for
a collection entry, back to where the entry was last added to its file. A
*write* of a value is a version that carries it where no parent of its commit
did; the points are the writes no other write is an ancestor of: where the
artefact *first* carried the value. A commit that writes back a value the
artefact carried before — the revert of a revalidation — is a write, and an
earlier write is its ancestor, so it is never a point. Writes on lines of work
that do not descend from one another — a revalidation cherry-picked onto
another line — are each a point. Which came first is read from ancestry,
never from timestamps or the log's date order. Without `at`, the marker is the
block itself.

**The deferral point** (point 4; `Walker.deferral_point`). The newest version
that introduced the entry on the anchor — present there, absent at every
parent — unless that introduction puts back an entry the artefact carried
before, with the same anchor and reason (whitespace folded): then it keeps
the point of the entry it puts back, the introduction of the stretch that
held it, tested again the same way. Rewording within a stretch moves nothing.

**Reading little** (critic G4). A file's versions are parsed once each, by
object id, shared by every artefact in the file; and a version whose bytes
hold none of what the walk looks for — the value, in any spelling YAML's
timestamp grammar allows (`stamps_in`), the block's key, every word of a
deferral's reason (`reason_words`) — carries none of it, so it is never
parsed.

**The times a file's history wrote** (`read_writes`). Where the change check
must tell a written-back `at` from a new one, one `git log -p` of the
artefact's file lists, for every time it ever held, the commits that changed
how often it holds it — `git log -S` for every spelling at once, each time
read as the UTC instant it denotes — so a write-back is never missed for how
its stamp was typed, and one reading serves every artefact of a collection.

**A shallow clone.** The boundary commit is listed as adding every file. A
value — or a deferral entry — the file already carries there has its point
beyond the clone: *unreachable*. Otherwise a value first carried inside the
clone is taken as first carried there, and the reading says the clone was
*cut* (`Carried.cut`).

**When an anchor has changed** (points 3 to 5; `changed_since`). With several
answering states, an anchor has changed only where what it stands on differs,
as a whole, from what it stood on at every one of them: both checks judge an
anchor by that one rule.

**Where a change originates** (point 9; `origin`). Each part of an anchor is
measured from one answering state at a time. Of the commits after that state
that touched the part, those whose result equals the part as it stood there
put it back; the origin is the oldest of the others that no put-back
descends from — so an edit put back and made again is dated from the second
edit — else the newest of them. An anchor's debt is dated where it came to
differ from every answering state: of each state's oldest origin, the
newest. A merge that takes a file whole from one side is not listed for it
(git's combined diff lists only what differs from every parent), so it is
never read as putting the file back, nor as changing it.
"""

from __future__ import annotations

import bisect
import functools
import re
from collections import Counter, OrderedDict
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar

from project_kit.friction_discovery import (
    Anchor,
    Artefact,
    ArtefactKind,
    entry_reason,
    parse_artefacts,
    parsed_at,
)
from project_kit.friction_git import (
    LINK_MODE,
    SHORT,
    BlobReader,
    DiffEntry,
    TreeEntry,
    parse_name_status,
    run_git,
    tree_entry,
)

# A record of the log starts with this byte; the fields inside are NUL-separated.
_RECORD_START = "\x01"
_LOG_FORMAT = f"--format={_RECORD_START}%H%x00%P%x00%an%x00%aI%x00%s"

# The mode of a submodule in a git tree: a commit, never a file to read.
_GITLINK_MODE = "160000"

# A time as YAML's timestamp grammar writes one — the grammar the front-matter reader
# resolves an unquoted `at` by; a quoted one validates only as `YYYY-MM-DDTHH:MM:SSZ`,
# which it reads too: the date, then `T`, `t` or whitespace — a line break inside a
# plain scalar included — then the time, month, day and hour with one digit or two; an
# optional fraction; an optional zone, `Z` or an offset. Its groups are the fields.
_STAMP = re.compile(
    rb"(\d{4})-(\d\d?)-(\d\d?)(?:[Tt]|\s+)(\d\d?):(\d\d):(\d\d)(?:\.\d*)?"
    rb"(?:\s*(?:Z|([-+])(\d\d?)(?::?(\d\d))?))?"
)

# How `stamp` writes an instant.
_INSTANT = "%Y-%m-%dT%H:%M:%S"

# The bytes every version carrying a `friction` block holds.
_BLOCK_KEY = b"friction"

# Lines of context `read_writes` reads around each change: a time written across lines,
# its zone on a third, is read whole wherever one of its lines changed.
_CONTEXT = 2

# How many blobs the walker keeps in memory between a prefilter and a parse.
_RECENT = 16

# The shortest word of a deferral's reason worth searching for.
_SHORTEST_WORD = 4


# --- the history, from one log -----------------------------------------------


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

    def parents(self) -> Iterator[tuple[TreeEntry | None, str | None]]:
        """The file at each parent of the commit: its entry there and its name there."""
        before = self.entry.before or (None,) * len(self.sources)
        yield from zip(before, self.sources, strict=False)


class History:
    """Every commit reachable from one commit, newest first, matched in memory.

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

    def position(self, sha: str) -> int | None:
        """The log index of the commit `sha`, or `None` when this history does not list it."""
        return self._index.get(sha)

    def touched(self, path: str) -> Sequence[int]:
        """The commits that touched `path`, newest first — either side of a rename counts."""
        return self._touched.get(path, ())

    def entry(self, index: int, path: str) -> DiffEntry | None:
        """What the commit at `index` did to the file at `path`, or `None` where it did nothing."""
        return self._by_path[index].get(path)

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

    def reached(self, points: Iterable[int]) -> frozenset[int]:
        """The commits any of `points` reaches, the points included."""
        listed = tuple(points)
        if len(listed) == 1:
            return self.ancestors(listed[0])
        found: frozenset[int] = frozenset()
        for point in listed:
            found = found | self.ancestors(point)
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

    def names(self, path: str) -> tuple[str, ...]:
        """Every name the file now at `path` had, newest first, `path` itself first."""
        names = dict.fromkeys([path])
        for version in self.versions(path):
            names.setdefault(version.path)
            names.update(dict.fromkeys(s for s in version.sources if s is not None))
        return tuple(names)

    def is_cut(self, index: int) -> bool:
        """Whether the commit at `index` is where a shallow clone's history stops."""
        return self.commits[index].sha in self.shallow

    def added(self, index: int, path: str) -> bool:
        """Whether the commit at `index` added the file at `path`: no parent of it held one."""
        entry = self._by_path[index].get(path)
        return entry is not None and entry.status == "A"

    def paths_after(self, reached: frozenset[int]) -> frozenset[str]:
        """Every path a commit outside `reached` touched — either side of a rename."""
        return frozenset(
            path
            for index, by_path in enumerate(self._by_path)
            if index not in reached
            for entry in by_path.values()
            for path in (entry.path, entry.old_path)
            if path is not None
        )


def read_history(root: Path, head: str) -> History:
    """`git log --raw -M -c` from `head`: one listing for the whole reading.

    `-c` lists a merge commit with the paths it changed against every parent
    — git's combined diff — and `--combined-all-paths` with the file's name
    at each parent; without them a merge lists nothing, and what it wrote
    itself, a revalidation among it, would go unseen. `--raw` gives each
    path's mode and object after the commit and at each parent, so whether a
    commit put a file back is read from the log, never asked of git again.
    `--date-order` keeps every parent after all of its children, so the log
    order the walks rely on is a topological one even under skewed clocks.
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
        "--raw",
        "--no-abbrev",
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
        tokens = [token for token in fields[5:] if token]
        if tokens and tokens[0].startswith("\n"):
            tokens[0] = tokens[0][1:]
        commits.append(
            Commit(
                sha=sha,
                parents=tuple(parents.split()),
                author=author,
                date=datetime.fromisoformat(date),
                subject=subject,
                entries=tuple(_raw_entries(tokens)),
            )
        )
    return History(commits, shallow_commits(root))


def _raw_entries(tokens: Sequence[str]) -> list[DiffEntry]:
    """The entries of one commit in a NUL-separated `--raw` listing.

    A single commit's entry is `:<mode> <mode> <object> <object> <status>`
    and its path — two paths for a rename or copy; a merge's, under `-c
    --combined-all-paths`, starts with one colon per parent, gives a mode and
    an object per parent and for the merge, a status letter per parent, then
    the file's name at each parent and in the merge. A copy adds its new path
    and leaves the source alone, as `parse_name_status` reads it.
    """
    entries: list[DiffEntry] = []
    index = 0
    while index < len(tokens):
        meta = tokens[index]
        parents = len(meta) - len(meta.lstrip(":"))
        fields = meta[parents:].split(" ")
        if parents == 0:  # not a raw listing: read it as names and statuses
            return parse_name_status(tokens[index:])
        if parents > 1:
            entries.append(_merge_entry(fields, tokens[index + 1 : index + 2 + parents], parents))
            index += parents + 2
            continue
        old_mode, new_mode, old_obj, new_obj, code = fields[:5]
        letter = code[:1]
        before = (tree_entry(old_mode, old_obj),)
        after = tree_entry(new_mode, new_obj)
        if letter in ("R", "C"):
            old, new = tokens[index + 1], tokens[index + 2]
            index += 3
            if letter == "R":
                score = int(code[1:]) if code[1:].isdigit() else None
                entries.append(DiffEntry("R", new, old, score, after, before))
            else:
                entries.append(DiffEntry("A", new, None, None, after, (None,)))
            continue
        entries.append(DiffEntry(letter, tokens[index + 1], None, None, after, before))
        index += 2
    return entries


def _merge_entry(fields: Sequence[str], named: Sequence[str], parents: int) -> MergeEntry:
    """One path of a merge commit's combined raw listing (`MergeEntry`)."""
    modes = fields[: parents + 1]
    objects = fields[parents + 1 : 2 * parents + 2]
    letters = fields[2 * parents + 2]
    path = named[parents]
    sources = tuple(
        None if letter == "A" else name
        for letter, name in zip(letters, named[:parents], strict=True)
    )
    before = tuple(
        tree_entry(mode, obj) for mode, obj in zip(modes[:parents], objects[:parents], strict=True)
    )
    status, old_path = "M", None
    if all(source is None for source in sources):
        status = "A"
    elif set(letters) == {"D"}:
        status = "D"
    elif set(letters) == {"R"} and len(set(sources)) == 1:
        status, old_path = "R", sources[0]
    after = tree_entry(modes[parents], objects[parents])
    return MergeEntry(status, path, old_path, None, after, before, sources)


def shallow_commits(root: Path) -> frozenset[str]:
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


# --- the times a file's history wrote ------------------------------------------------

# Every byte a time `_STAMP` reads can be written with: a cut between two others leaves
# no time on both sides of it.
_STAMP_BYTES = frozenset(b"0123456789-+:.TtZ \t\r\n\f\v")


# How many bytes `_shared` compares at a time before it narrows down.
_STRIDE = 4096


def _shared(a: bytes, b: bytes) -> int:
    """How many bytes `a` and `b` share at their start: compared a stride at a time, then
    narrowed down by halving the stride that differs."""
    limit = min(len(a), len(b))
    low = 0
    while low + _STRIDE <= limit and a[low : low + _STRIDE] == b[low : low + _STRIDE]:
        low += _STRIDE
    high = min(low + _STRIDE, limit)
    while low < high:  # a[:low] == b[:low] holds throughout
        mid = (low + high + 1) // 2
        low, high = (mid, high) if a[low:mid] == b[low:mid] else (low, mid - 1)
    return low


def _apart(was: bytes, now: bytes) -> tuple[bytes, bytes]:
    """`was` and `now` without what they share at either end, each cut moved off any byte
    a time can be written with: a time on the shared stretch is held as often by both,
    and none straddles a cut, so how often each time is held differs between the two
    exactly as between the whole texts — read in a fraction of the bytes where one line
    holds a whole collection's front matter."""
    start = _shared(was, now)
    while start and was[start - 1] in _STAMP_BYTES:
        start -= 1
    finish = min(_shared(was[::-1], now[::-1]), len(was) - start, len(now) - start)
    while finish and was[len(was) - finish] in _STAMP_BYTES:
        finish -= 1
    return was[start : len(was) - finish], now[start : len(now) - finish]


@dataclass(frozen=True)
class Writes:
    """Which commits of a file's history changed how often it holds each time, and its
    block's key (`read_writes`): only those can have written a value there, since a
    write makes the file hold it once more.

    `stamps` maps each instant (`stamp`) to those commits; `block` lists the commits
    that changed how often the file holds the block's key.
    """

    stamps: Mapping[str, frozenset[str]]
    block: frozenset[str]

    def of(self, value: Any) -> frozenset[str] | None:
        """The commits that can have written `value` — a parsed `at`, or `BLOCK` — into
        the file, empty where none can; `None` for a value no reading tells, an `at` that
        is no aware time, which the walk alone can judge."""
        if value is BLOCK:
            return self.block
        if isinstance(value, datetime) and value.tzinfo is not None:
            return self.stamps.get(stamp(value), frozenset())
        return None


def read_writes(root: Path, head: str, path: str) -> Writes:
    """`git log -p` of the file at `path` from `head` — renames followed, a merge diffed
    against each parent, the root's whole file read as added — read for the times it
    writes (`Writes`).

    What `git log -S` lists for one fixed spelling, for every time and every spelling
    at once: each hunk is read as the two slices of the file it shows, before and
    after, and a commit is listed for a time where the two hold it a different number
    of times, each time read as the instant it denotes (`stamps_in`) — so a stamp
    reformatted in place is no write, and one typed with a space, a lowercase `t` or
    unpadded fields is found as readily as the canonical form. Each change is read
    with `_CONTEXT` lines around it, so a time written across lines is read whole.
    One process serves every artefact of the file.
    """
    raw = run_git(
        root,
        "log",
        "-m",
        "--follow",
        "--root",
        "-p",
        f"-U{_CONTEXT}",
        "--text",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--no-show-signature",
        f"--format={_RECORD_START}%H",
        head,
        "--",
        path,
    ).stdout
    stamps: dict[str, set[str]] = {}
    block: set[str] = set()
    sha = ""
    before: list[bytes] = []
    after: list[bytes] = []

    def hunk_read() -> None:
        if not before and not after:
            return
        was, now = b"\n".join(before), b"\n".join(after)
        before.clear()
        after.clear()
        if was.count(_BLOCK_KEY) != now.count(_BLOCK_KEY):
            block.add(sha)
        was, now = _apart(was, now)
        net = stamps_in(now)
        net.subtract(stamps_in(was))
        for instant, count in net.items():
            if count:
                stamps.setdefault(instant, set()).add(sha)

    in_hunk = False
    for line in raw.split(b"\n"):
        if line.startswith(_RECORD_START.encode()):
            hunk_read()
            sha, in_hunk = line[1:].decode(), False
        elif line.startswith(b"@@"):
            hunk_read()
            in_hunk = True
        elif not in_hunk:
            continue  # a file's header lines
        elif line.startswith(b"diff "):  # no line of a hunk starts so: the next file's header
            hunk_read()
            in_hunk = False
        elif line.startswith(b" "):
            before.append(line[1:])
            after.append(line[1:])
        elif line.startswith(b"-"):
            before.append(line[1:])
        elif line.startswith(b"+"):
            after.append(line[1:])
    hunk_read()
    return Writes({k: frozenset(v) for k, v in stamps.items()}, frozenset(block))


# --- what the walk finds -------------------------------------------------------


#: The marker of an artefact without `at`: its `friction` block, there or not (point 3).
BLOCK = object()


@dataclass(frozen=True)
class Carried:
    """Where a file first carried a value (`Walker.carried`).

    `points`: the log indices of the first carryings, newest first — the
    writes no other write is an ancestor of; empty where no listed version
    carries the value. `unreachable`: the file already carries it where a
    shallow clone's history is cut, so where it was first carried is beyond
    the clone. `cut`: the file's history reaches the cut, so a value first
    carried inside the clone is read as first carried there.
    """

    points: tuple[int, ...]
    unreachable: bool = False
    cut: bool = False


@dataclass(frozen=True)
class Deferred:
    """Where a deferral entry has its point (`Walker.deferral_point`).

    `point`: the log index of the deferral point, or `None` — none found, or
    beyond the clone. `unreachable`: the entry is already there where a
    shallow clone's history is cut. `cut`: the file's history reaches the
    cut, so an entry it held before the cut is not known.
    """

    point: int | None
    unreachable: bool = False
    cut: bool = False


@dataclass(frozen=True)
class Points:
    """What the walk back through one artefact's file found (COR-050 points 3 and 4)."""

    revalidations: tuple[int, ...]  # the revalidation points' log indices, newest first
    deferrals: tuple[tuple[Anchor, int | None], ...]  # each deferral's point, in written order
    moves: tuple[Version, ...]  # renames no revalidation point reaches, unanswered
    own_paths: frozenset[str]  # every name the file had: a change under one is never an anchor's
    unreachable: str | None  # which point the clone's history does not reach, when one
    cut: bool = False  # the file's history reaches a shallow clone's cut

    @property
    def revalidation(self) -> int | None:
        """The newest revalidation point, or `None` when the clone does not reach one."""
        return self.revalidations[0] if self.revalidations else None


@dataclass(frozen=True)
class _Parsed:
    """The artefacts one version of a file holds: its document, and its entries by id."""

    document: Artefact | None
    entries: dict[str, Artefact]


@dataclass(frozen=True)
class _Bytes:
    """What the prefilter reads from one blob without parsing it."""

    stamps: frozenset[str]  # each time written in it, as the instant it denotes (`stamp`)
    block: bool  # it holds the block's key


def stamp(value: datetime) -> str:
    """An aware time as the prefilters compare one: the UTC instant, `YYYY-MM-DDTHH:MM:SS`."""
    return value.astimezone(UTC).strftime(_INSTANT)


@functools.lru_cache(maxsize=65536)
def _instant(fields: tuple[bytes, ...]) -> str | None:
    """The instant a time `_STAMP` read denotes, its fields given, as `stamp` writes one;
    `None` where they name no time (a thirteenth month, say). One written with no zone is
    read as UTC: it is never an aware `at`, so that reading errs only toward a parse."""
    year, month, day, hour, minute, second, sign, hours, minutes = fields
    try:
        instant = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    except ValueError:
        return None
    if sign:
        offset = timedelta(hours=int(hours), minutes=int(minutes or 0))
        instant = instant - offset if sign == b"+" else instant + offset
    return instant.strftime(_INSTANT)


def stamps_in(data: bytes) -> Counter[str]:
    """Each time `data` writes in a spelling YAML's timestamp grammar allows — `T`, `t` or
    whitespace between date and time, fields padded or not, a fraction, any zone — as the
    instant it denotes (`stamp`), counted: whatever spelling an `at` was typed in, the
    prefilters find it."""
    found: Counter[str] = Counter()
    for fields, count in Counter(_STAMP.findall(data)).items():
        instant = _instant(fields)
        if instant is not None:
            found[instant] += count
    return found


def reason_words(reason: str | None) -> tuple[str, ...]:
    """The words of a deferral's reason every text carrying it holds: those written in plain
    ASCII with no quote or backslash, so no escaped or quoted form can hide one, and of at
    least `_SHORTEST_WORD` characters — each once, the longest first; none where none is."""
    if not reason:
        return ()
    words = {
        word
        for word in reason.split()
        if len(word) >= _SHORTEST_WORD and word.isascii() and not any(ch in word for ch in "\"'\\")
    }
    return tuple(sorted(words, key=lambda word: (-len(word), word)))


def carrier(value: Any) -> Callable[[Artefact | None], bool]:
    """Whether a version of an artefact carries the value a walk looks for: its parsed
    `at`, or, for `BLOCK`, its `friction` block (COR-050 point 3)."""
    if value is BLOCK:
        return lambda artefact: artefact is not None and artefact.has_friction_block
    return lambda artefact: artefact is not None and parsed_at(artefact) == value


class Walker:
    """Reads an artefact's earlier versions, each parsed once, and no more than needed."""

    def __init__(self, history: History, blobs: BlobReader) -> None:
        self.history = history
        self._blobs = blobs
        self._parsed: dict[tuple[str, str], _Parsed] = {}
        self._bytes: dict[str, _Bytes] = {}
        self._recent: OrderedDict[str, bytes | None] = OrderedDict()

    # --- one version --------------------------------------------------------------

    def _read(self, obj: str) -> bytes | None:
        """The blob `obj` names; the last few kept, so a prefilter and a parse read it once."""
        if obj in self._recent:
            self._recent.move_to_end(obj)
            return self._recent[obj]
        raw = self._blobs.read_object(obj)
        self._recent[obj] = raw
        if len(self._recent) > _RECENT:
            self._recent.popitem(last=False)
        return raw

    def _scan(self, obj: str) -> _Bytes:
        found = self._bytes.get(obj)
        if found is None:
            raw = self._read(obj) or b""
            found = _Bytes(frozenset(stamps_in(raw)), _BLOCK_KEY in raw)
            self._bytes[obj] = found
        return found

    def may_carry(self, state: TreeEntry | None, value: Any) -> bool:
        """Whether the blob of `state` could carry `value`: `False` only where its bytes
        hold no spelling of it (`stamps_in`), so it is never parsed to find out."""
        if state is None or state[0] in (LINK_MODE, _GITLINK_MODE):
            return False
        if value is BLOCK:
            return self._scan(state[1]).block
        if isinstance(value, datetime) and value.tzinfo is not None:
            return stamp(value) in self._scan(state[1]).stamps
        return True  # a value no prefilter reads: parse to tell

    def holds(self, state: TreeEntry | None, words: Sequence[str]) -> bool:
        """Whether the blob of `state` holds every one of `words` — any blob does where
        there are none."""
        if state is None or state[0] in (LINK_MODE, _GITLINK_MODE):
            return False
        if not words:
            return True
        raw = self._read(state[1]) or b""
        return all(word.encode() in raw for word in words)

    def artefact_in(self, state: TreeEntry | None, path: str, like: Artefact) -> Artefact | None:
        """`like` as the blob of `state` holds it at `path`: the document, or the entry under
        the same id — read by the same rule as the present (`parse_artefacts`)."""
        if state is None or state[0] in (LINK_MODE, _GITLINK_MODE):
            return None
        key = (state[1], path)
        found = self._parsed.get(key)
        if found is None:
            raw = self._read(state[1])
            artefacts: list[Artefact] = []
            if raw is not None:
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = None
                if text is not None:
                    artefacts, _reason = parse_artefacts(
                        path, like.place, text, rule_set=like.rule_set
                    )
            document = next((a for a in artefacts if a.kind is ArtefactKind.DOCUMENT), None)
            entries: dict[str, Artefact] = {}
            for artefact in artefacts:
                if artefact.kind is ArtefactKind.ENTRY:
                    entries.setdefault(artefact.id, artefact)
            found = self._parsed[key] = _Parsed(document, entries)
        if like.kind is ArtefactKind.DOCUMENT:
            return found.document
        return found.entries.get(like.id)

    def same_at(self, version: Version, artefact: Artefact) -> Artefact | None:
        """`artefact` as it was at `version`: the document, or the entry under the same id."""
        return self.artefact_in(self._after(version), version.path, artefact)

    def same_in_parents(self, version: Version, artefact: Artefact) -> tuple[Artefact | None, ...]:
        """`artefact` as the file stood at each parent of `version`'s commit, in parent order.

        Those are the states `git log` diffed the version against, each read
        under the file's name at that parent; `None` where a parent has no
        such file, and a root's one `None`.
        """
        return tuple(
            None if source is None else self.artefact_in(state, source, artefact)
            for state, source in version.parents()
        )

    def _after(self, version: Version) -> TreeEntry | None:
        return version.entry.after

    # --- the revalidation point ---------------------------------------------------

    def carried(self, like: Artefact, value: Any, among: frozenset[int] | None = None) -> Carried:
        """Where the file of `like` first carried `value` — a parsed `at`, or `BLOCK` —
        for the artefact `like` names (COR-050 point 3; see the module docstring).

        The walk goes back to where the file was last added; for a collection
        entry, where a write has an earlier carrying of the value among its
        ancestors, back to where the entry was last added to the file, so a
        value it carried before it was removed and restored is no earlier
        carrying. `among`, where given, are the only commits that can have
        written the value — those the file's reading lists for it
        (`read_writes`), since a write changes how often the file holds it — so
        no other version is read.
        """
        holds_value = carrier(value)

        def carries(state: TreeEntry | None, path: str | None) -> bool:
            if path is None or not self.may_carry(state, value):
                return False
            return holds_value(self.artefact_in(state, path, like))

        versions = list(self.history.versions(like.path))
        writes: list[int] = []
        cut = False
        for version in versions:
            at_cut = self.history.is_cut(version.index)
            if among is not None and not at_cut and version.index not in among:
                continue
            here = carries(self._after(version), version.path)
            if at_cut:
                # Listed as added, its parent beyond the clone: what came before cannot be told.
                if here:
                    return Carried((), unreachable=True, cut=True)
                cut = True
                break
            if here and not any(carries(state, source) for state, source in version.parents()):
                writes.append(version.index)
        points = self._first(writes)
        if like.kind is ArtefactKind.ENTRY and len(points) < len(writes):
            gone = self._entry_gone(versions, like, writes[0])
            if gone is not None:
                points = self._first([w for w in writes if w < gone])
        return Carried(tuple(points), cut=cut)

    def _first(self, writes: Sequence[int]) -> list[int]:
        """Of `writes`, those no other write is an ancestor of, newest first."""
        return sorted(
            w for w in writes if not any(o != w and o in self.history.ancestors(w) for o in writes)
        )

    def _entry_gone(self, versions: Sequence[Version], like: Artefact, newest: int) -> int | None:
        """The newest version, older than the write at `newest`, that holds no entry under
        the id `like` names — where the entry was last absent from its file before it was
        added again — or `None`. Read from the bytes alone: a version whose blob does not
        hold the id holds no such entry; one that holds it is taken to hold the entry,
        which errs only toward reading a value as carried before."""
        for version in versions:
            if version.index > newest and not self.holds(self._after(version), (like.id,)):
                return version.index
        return None

    # --- the deferral point -------------------------------------------------------

    def deferral_point(self, like: Artefact, anchor: Anchor, reason: str | None = None) -> Deferred:
        """The deferral point of the entry on `anchor` in the file of `like` (COR-050 point 4;
        see the module docstring).

        Without `reason`, the entry the newest version carries. With `reason`
        — an entry this history does not hold yet, put back on top of it — the
        point of the entry it puts back: `Deferred(None)` where no version
        carries an entry on `anchor` with that reason, so it puts nothing back.
        """
        versions = list(self.history.versions(like.path))
        cut = bool(versions) and self.history.is_cut(versions[-1].index)

        def present(state: TreeEntry | None, path: str | None) -> bool:
            if path is None or state is None:
                return False
            found = self.artefact_in(state, path, like)
            return found is not None and any(d.anchor == anchor for d in found.deferrals)

        def carrying(state: TreeEntry | None, path: str, wanted: str | None) -> bool:
            if not self.holds(state, reason_words(wanted)):
                return False
            found = self.artefact_in(state, path, like)
            return found is not None and any(
                d.anchor == anchor and entry_reason(found, d) == wanted for d in found.deferrals
            )

        def introduction(within: frozenset[int] | None) -> int | None:
            """The newest version introducing the entry, among `within` where given; `-1`
            where the stretch reaches the cut."""
            for version in versions:
                if within is not None and version.index not in within:
                    continue
                if not present(self._after(version), version.path):
                    continue
                if self.history.is_cut(version.index):
                    return -1
                if not any(present(state, source) for state, source in version.parents()):
                    return version.index
            return None

        def newest_carrying(
            within: frozenset[int] | None, wanted: str | None, but: int
        ) -> int | None:
            for version in versions:
                if version.index == but or (within is not None and version.index not in within):
                    continue
                if carrying(self._after(version), version.path, wanted):
                    return version.index
            return None

        if reason is None:
            start = introduction(None)
        else:
            held = newest_carrying(None, reason, -1)
            if held is None:
                return Deferred(None, cut=cut)
            start = introduction(self.history.ancestors(held))
        while True:
            if start is None:
                return Deferred(None, cut=cut)
            if start == -1:
                return Deferred(None, unreachable=True, cut=True)
            at = next(v for v in versions if v.index == start)
            here = self.artefact_in(self._after(at), at.path, like)
            wanted = (
                next(
                    (entry_reason(here, d) for d in here.deferrals if d.anchor == anchor),
                    None,
                )
                if here is not None
                else None
            )
            held = newest_carrying(self.history.ancestors(start), wanted, start)
            if held is None:
                return Deferred(start, cut=cut)
            start = introduction(self.history.ancestors(held))

    # --- both, for one artefact ---------------------------------------------------

    def points(self, artefact: Artefact) -> Points:
        """The revalidation points and every deferral point of `artefact`, from its file's
        history back to where it was last added (COR-050 points 3 and 4), its file's
        names, and the renames no revalidation point reaches (`Points.moves`)."""
        at = parsed_at(artefact)
        value = BLOCK if at is None else at
        versions = list(self.history.versions(artefact.path))
        own: set[str] = {artefact.path}
        renames: list[Version] = []
        for version in versions:
            own.add(version.path)
            own.update(source for source in version.sources if source is not None)
            if version.entry.status == "R":
                renames.append(version)
        wanted = [d.anchor for d in artefact.deferrals]
        if not versions:
            return Points(
                (),
                tuple((a, None) for a in wanted),
                (),
                frozenset(own),
                "the commit that added its file (none in this clone touches it)",
            )
        found = self.carried(artefact, value)
        unreachable = "its revalidation point" if found.unreachable else None
        revalidations = found.points
        if not revalidations and unreachable is None:
            # No listed version shows the value: the file's history, as git's rename
            # detection pairs it, ends first. Its oldest state is the point.
            revalidations = (versions[-1].index,)
        deferrals: list[tuple[Anchor, int | None]] = []
        for anchor in wanted:
            deferred = self.deferral_point(artefact, anchor)
            if deferred.unreachable:
                unreachable = unreachable or f"the deferral point of {anchor.kind} {anchor.value}"
            point = deferred.point
            if point is None and not deferred.unreachable:
                point = versions[-1].index
            deferrals.append((anchor, point))
        moves: tuple[Version, ...] = ()
        if revalidations:
            reached = self.history.reached(revalidations)
            moves = tuple(v for v in renames if v.index not in reached)
        return Points(
            revalidations=revalidations,
            deferrals=tuple(deferrals),
            moves=moves,
            own_paths=frozenset(own),
            unreachable=unreachable,
            cut=found.cut and unreachable is None,
        )


def changed(
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


# --- whether a part of an anchor differs, and since when -------------------------

# A state an anchor is judged against: a commit's log index, or a reading of one.
_State = TypeVar("_State")


def differs(later: TreeEntry | None, earlier: TreeEntry | None) -> bool:
    """Whether a file differs between two states: there in one and not the other, or with
    another mode or object (COR-050 point 5) — so an edit put back is no difference."""
    return later != earlier


def changed_since(states: Iterable[_State], differs_from: Callable[[_State], bool]) -> bool:
    """Whether an anchor has changed since the states that answer it (COR-050 points 3 to
    5): only where what it stands on differs, as a whole, from what it stood on at every
    one of them — at each, some part of it differs, never necessarily the same part.

    The one rule both checks judge an anchor with several answering states by: the
    change check, the points of an `at` a change writes back (and a deferral's point
    no revalidation point reaches); the whole-repository check, every answering state.
    `differs_from` says whether what the anchor stands on now differs from a state.
    """
    return all(differs_from(state) for state in states)


def origin(
    history: History, touched: Iterable[int], puts_back: Callable[[int], bool]
) -> int | None:
    """Where a change to one part of what an anchor stands on originates, measured from
    one answering state (COR-050 point 9).

    `touched`: the commits after that state that touched the part. `puts_back`:
    whether a commit's result is the part as it stood at that state. The origin
    is the oldest commit that does not put it back and that no put-back descends
    from — the oldest change still standing — else, after an unusual merge, the
    newest commit that touched it; `None` where none did. Order among commits
    that do not descend from one another only dates the debt. A merge that took
    the part whole from one side is not among `touched` (git's combined diff
    lists only what differs from every parent), so it is never read as putting
    the part back: an edit it undid still dates the debt.
    """
    commits = sorted(set(touched))
    if not commits:
        return None
    put_back = [c for c in commits if puts_back(c)]
    standing = [
        c
        for c in commits
        if c not in put_back and not any(c in history.ancestors(r) for r in put_back)
    ]
    return max(standing) if standing else commits[0]


__all__ = [
    "BLOCK",
    "Carried",
    "Commit",
    "Deferred",
    "History",
    "MergeEntry",
    "Points",
    "Version",
    "Walker",
    "Writes",
    "carrier",
    "changed",
    "changed_since",
    "differs",
    "origin",
    "read_history",
    "read_writes",
    "reason_words",
    "shallow_commits",
    "stamp",
    "stamps_in",
]
