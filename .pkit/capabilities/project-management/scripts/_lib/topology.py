"""The topology of seats: its file, its one reading, and its check (DEC-059 points 1 to 3).

[project-management:DEC-059-topology-of-seats] has a project that runs agents in
parallel declare a **topology** in its committed configuration for this
capability, ``project/topology.yaml``: a list of seats, and the settings they
share. Each seat has a name, a role, the agent definition its agent follows, an
optional scope, whether it is the organizer seat, and the number of its state
issue (points 2 and 3). A seat's number is its place in the list, counted from
one, retired seats included, so no seat's number moves (point 6).

Three readings
--------------
- :func:`read` is the one reading the commands that act as a seat use. It reads
  the topology from the default branch, at the commit the backbone resolves it
  to (``_lib/default_branch``, COR-054 point 5), and never from the branch or the
  working tree (point 1). The topology it returns names the reference and the
  commit it read. It returns None where that commit declares no topology, or the
  default branch has no commit yet, and raises :class:`Unresolved` where the
  default branch resolves to no commit, or git cannot read the file there.
- :func:`read_working_tree` reads the change's own file: the command that creates
  the seats' state issues writes into it, and the check judges it.
- :func:`read_at` reads the topology at a commit, such as a check's base.

:func:`writers_at` reads the members at the same commit, as the state-issue seam
takes them from its caller ([pkit:ADR-071] points 1 and 3).

One run's snapshot
------------------
:func:`snapshot` builds one run's inputs for both seams ([pkit:ADR-071] points 1
and 8): the topology the default branch holds, the members at its commit, and
this clone's account, key and place (DEC-058 point 5). Its :class:`Snapshot`
reads a seat's holder from the seat's state issue, through the state-issue seam,
the first time the run asks for that seat, and keeps it for the rest of the run.
So one run judges every claim against one state of the seats. Nothing is kept
across runs. The commands that take, release and list seats read it, and so does
instance ownership, which confirms the clone's seat before a command writes
(DEC-059 point 6) and passes each seat's holder to the ownership fold
([pkit:ADR-041] point 7). The time of reading joins it when a claim lapses.

The check
---------
:func:`parse` reports what the file says wrong of itself: a shape the schema
(``schemas/topology.schema.json``) refuses, a seat name used twice, more than one
organizer seat, a seat that names no state issue, and two seats that name one.
:func:`check` adds what needs more than the file: a scope that names a workstream
or a type the project does not declare, a topology under the ``label`` ownership
substrate (point 9), and each seat of the base deleted or moved rather than
retired. :func:`check_change` reads all of it for one run, the base as the
backbone resolves it, with COR-054's override, and says which commit it read.

The file's readings and the check read no GitHub, and write nothing. Every git
call stays in this clone, asking no remote for what it lacks. A snapshot reads
GitHub only through the state-issue seam.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from _lib import default_branch, provenance, state_issues, workstreams
except ImportError:  # pragma: no cover - a test that puts `_lib` itself on the path
    import default_branch  # type: ignore[no-redef]
    import provenance  # type: ignore[no-redef]
    import state_issues  # type: ignore[no-redef]
    import workstreams  # type: ignore[no-redef]

#: The file, relative to the capability root, and its binding tag (COR-023).
TOPOLOGY_RELATIVE = "project/topology.yaml"
BINDING = "project-management:topology"
SCHEMA_VERSION = 1

#: Where the other files the check reads lie, relative to the capability root.
MEMBERS_RELATIVE = "project/members.yaml"
OWNERSHIP_RELATIVE = "project/instance-ownership.yaml"
CLASSIFICATION_RELATIVE = "schemas/classification.yaml"

#: The kind of state a seat's state issue holds (``schemas/state-issues.yaml``).
SEAT_KIND = "seat"

#: The roles a seat takes (DEC-059 point 2).
PLANNER = "planner"
WORKER = "worker"
LEAD = "lead"
ROLES = (PLANNER, WORKER, LEAD)

#: The agent definition a seat follows where it names none (point 8).
DEFAULT_AGENT = "project-manager"

#: The modes in which a seat is released (point 5). Only the tolerant one is built.
TOLERANT = "tolerant"
RELEASE_MODES = (TOLERANT,)

#: A seat's name: lowercase letters, digits and hyphens, at most 40, starting
#: with a letter and ending with no hyphen. The schema holds the same pattern.
NAME_PATTERN = re.compile(r"[a-z](?:[a-z0-9-]{0,38}[a-z0-9])?")
AGENT_PATTERN = re.compile(r"[a-z][a-z0-9-]*")

_TOP_KEYS = frozenset({"schema_version", "pkit_schema", "binds_to", "settings", "seats"})
_SEAT_KEYS = frozenset({"name", "role", "agent", "scope", "organizer", "state_issue", "retired"})
_SCOPE_KEYS = frozenset({"workstreams", "types"})
_SETTINGS_KEYS = frozenset({"release_mode"})

# What a problem is about. A caller tells them apart by these codes.
SHAPE = "shape"
DUPLICATE_SEAT = "duplicate-seat"
ORGANIZERS = "organizers"
NO_STATE_ISSUE = "no-state-issue"
SHARED_STATE_ISSUE = "shared-state-issue"
UNKNOWN_WORKSTREAM = "unknown-workstream"
UNKNOWN_TYPE = "unknown-type"
LABEL_SUBSTRATE = "label-substrate"
SEAT_DELETED = "seat-deleted"
SEAT_MOVED = "seat-moved"
UNRESOLVED = "unresolved"

#: Git's environment for a reading that stays in this clone: a partial clone
#: fetches an object it lacks unless told not to.
_OFFLINE = {"GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": "none"}

#: A git runner: takes the arguments after ``git``, returns what
#: ``subprocess.run`` returns.
Git = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


class Unresolved(Exception):
    """The topology could not be read where it is settled: the default branch
    resolves to no commit, or git cannot read the file there. The message names
    the cause. No clone takes a seat then (DEC-059 point 1, COR-054 point 4)."""


@dataclass(frozen=True)
class Problem:
    """One thing wrong with a topology: its code and a sentence for a person."""

    code: str
    message: str


@dataclass(frozen=True)
class Scope:
    """What narrows a seat's own pool: workstreams, types of the type axis, or
    both (DEC-059 point 7). A Task falls in it where it matches each part named."""

    workstreams: tuple[str, ...] = ()
    types: tuple[str, ...] = ()


@dataclass(frozen=True)
class Seat:
    """One seat of the topology. ``number`` is its place in the list, from one."""

    name: str
    number: int
    role: str
    agent: str = DEFAULT_AGENT
    scope: Scope | None = None
    organizer: bool = False
    state_issue: int | None = None
    retired: bool = False


@dataclass(frozen=True)
class Topology:
    """A topology as one reading found it.

    ``ref`` and ``commit`` name where it was read, and are None for the working
    tree. ``problems`` holds what :func:`parse` found wrong with the file. A seat
    the parse could not read is left out of ``seats``, and the problems say so.
    """

    seats: tuple[Seat, ...] = ()
    release_mode: str = TOLERANT
    problems: tuple[Problem, ...] = ()
    ref: str | None = None
    commit: str | None = None

    def seat(self, name: str) -> Seat | None:
        """The seat named ``name``, the first where two share it, or None."""
        return next((s for s in self.seats if s.name == name), None)

    @property
    def active(self) -> tuple[Seat, ...]:
        """The seats that are not retired, in their order."""
        return tuple(s for s in self.seats if not s.retired)

    @property
    def organizer(self) -> Seat | None:
        """The organizer seat that is not retired, the first where several are."""
        return next((s for s in self.active if s.organizer), None)

    def where(self) -> str:
        """Where this topology was read, in words a line can carry."""
        if self.commit is None:
            return "the working tree"
        return f"{self.ref or 'the default branch'} at {self.commit}"


# ---- the file ---------------------------------------------------------------


def parse(data: object, *, ref: str | None = None, commit: str | None = None) -> Topology:
    """The topology a parsed ``topology.yaml`` declares, with what is wrong with it.

    Reports a shape the schema refuses, a seat name used twice, more than one
    organizer seat, a seat that names no state issue and is not retired, and two
    seats that name one state issue. Never raises on what a hand wrote.
    """
    problems: list[Problem] = []
    if not isinstance(data, dict):
        kind = "nothing" if data is None else type(data).__name__
        problems.append(Problem(SHAPE, f"the file holds {kind}, not a mapping."))
        return Topology(problems=tuple(problems), ref=ref, commit=commit)
    unknown = sorted(str(k) for k in data if k not in _TOP_KEYS)
    if unknown:
        problems.append(
            Problem(SHAPE, f"the file holds keys no topology has: {', '.join(unknown)}.")
        )
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(
            Problem(
                SHAPE,
                f"`schema_version` is {data.get('schema_version')!r}, and this capability "
                f"reads {SCHEMA_VERSION}.",
            )
        )
    release_mode = _settings(data.get("settings"), problems)
    raw = data.get("seats")
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        problems.append(Problem(SHAPE, "`seats` is not a list."))
        raw = []
    seats = [s for s in (_seat(entry, i + 1, problems) for i, entry in enumerate(raw)) if s]
    problems += _across(seats)
    return Topology(tuple(seats), release_mode, tuple(problems), ref, commit)


def _settings(raw: object, problems: list[Problem]) -> str:
    if raw is None:
        return TOLERANT
    if not isinstance(raw, dict):
        problems.append(Problem(SHAPE, "`settings` is not a mapping."))
        return TOLERANT
    unknown = sorted(str(k) for k in raw if k not in _SETTINGS_KEYS)
    if unknown:
        problems.append(Problem(SHAPE, f"`settings` holds keys it has not: {', '.join(unknown)}."))
    mode = raw.get("release_mode", TOLERANT)
    if mode not in RELEASE_MODES:
        problems.append(
            Problem(
                SHAPE,
                f"`settings.release_mode` is {mode!r}: a seat is released only in the "
                f"`{TOLERANT}` mode so far (DEC-059 point 5).",
            )
        )
        return TOLERANT
    return str(mode)


def _seat(entry: object, number: int, problems: list[Problem]) -> Seat | None:
    """Seat ``number`` of the list, or None where it cannot be read."""
    where = f"seat {number}"
    if not isinstance(entry, dict):
        problems.append(Problem(SHAPE, f"{where} is not a mapping."))
        return None
    name = entry.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        problems.append(
            Problem(
                SHAPE,
                f"{where} has the name {name!r}: a seat's name is lowercase letters, digits "
                "and hyphens, at most 40, starting with a letter and ending with no hyphen.",
            )
        )
        return None
    where = f"seat {number} ({name})"
    unknown = sorted(str(k) for k in entry if k not in _SEAT_KEYS)
    if unknown:
        problems.append(Problem(SHAPE, f"{where} holds keys a seat has not: {', '.join(unknown)}."))
    role = entry.get("role")
    if role not in ROLES:
        problems.append(
            Problem(
                SHAPE,
                f"{where} has the role {role!r}, and a seat's role is one of {', '.join(ROLES)}.",
            )
        )
        role = ""
    agent = entry.get("agent", DEFAULT_AGENT)
    if not isinstance(agent, str) or not AGENT_PATTERN.fullmatch(agent):
        problems.append(Problem(SHAPE, f"{where} names the agent {agent!r}, which is no name."))
        agent = DEFAULT_AGENT
    flags = {}
    for key in ("organizer", "retired"):
        value = entry.get(key, False)
        if not isinstance(value, bool):
            problems.append(Problem(SHAPE, f"{where} has `{key}: {value!r}`, not true or false."))
            value = False
        flags[key] = value
    state_issue = entry.get("state_issue")
    if state_issue is not None and (
        isinstance(state_issue, bool) or not isinstance(state_issue, int) or state_issue < 1
    ):
        problems.append(
            Problem(SHAPE, f"{where} names the state issue {state_issue!r}, which is no number.")
        )
        state_issue = None
    return Seat(
        name=name,
        number=number,
        role=str(role),
        agent=agent,
        scope=_scope(entry.get("scope"), where, problems),
        organizer=flags["organizer"],
        state_issue=state_issue,
        retired=flags["retired"],
    )


def _scope(raw: object, where: str, problems: list[Problem]) -> Scope | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        problems.append(Problem(SHAPE, f"{where} has a scope that is not a mapping."))
        return None
    unknown = sorted(str(k) for k in raw if k not in _SCOPE_KEYS)
    if unknown:
        problems.append(
            Problem(SHAPE, f"{where} has a scope with keys a scope has not: {', '.join(unknown)}.")
        )
    parts: dict[str, tuple[str, ...]] = {}
    for key in ("workstreams", "types"):
        value = raw.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            problems.append(
                Problem(SHAPE, f"{where} has a scope whose `{key}` is no list of names.")
            )
            value = []
        parts[key] = tuple(value)
    if not parts["workstreams"] and not parts["types"]:
        problems.append(Problem(SHAPE, f"{where} has a scope that names nothing."))
        return None
    return Scope(parts["workstreams"], parts["types"])


def _across(seats: list[Seat]) -> list[Problem]:
    """What only the seats together show."""
    problems: list[Problem] = []
    seen: dict[str, Seat] = {}
    for seat in seats:
        first = seen.setdefault(seat.name, seat)
        if first is not seat:
            problems.append(
                Problem(
                    DUPLICATE_SEAT,
                    f"seats {first.number} and {seat.number} share the name {seat.name!r}, "
                    "and a seat's name is unique in the topology.",
                )
            )
    organizers = [s for s in seats if s.organizer and not s.retired]
    if len(organizers) > 1:
        named = ", ".join(s.name for s in organizers)
        problems.append(
            Problem(
                ORGANIZERS,
                f"{len(organizers)} seats are the organizer seat ({named}), and at most one is.",
            )
        )
    for seat in seats:
        if seat.state_issue is None and not seat.retired:
            problems.append(
                Problem(
                    NO_STATE_ISSUE,
                    f"seat {seat.number} ({seat.name}) names no state issue, so no clone may "
                    "take it: run `pkit pm create-seats` on this change.",
                )
            )
    holders: dict[int, Seat] = {}
    for seat in seats:
        if seat.state_issue is None:
            continue
        first = holders.setdefault(seat.state_issue, seat)
        if first is not seat:
            problems.append(
                Problem(
                    SHARED_STATE_ISSUE,
                    f"seats {first.name} and {seat.name} both name the state issue "
                    f"#{seat.state_issue}, and each seat has a state issue of its own.",
                )
            )
    return problems


def load(text: str) -> object:
    """``text`` parsed as YAML. Raises ValueError where it is no YAML."""
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError

    try:
        return YAML(typ="safe").load(text)
    except YAMLError as exc:
        raise ValueError(" ".join(str(exc).split())) from exc


def _parse_text(text: str, *, ref: str | None, commit: str | None) -> Topology:
    try:
        data = load(text)
    except ValueError as exc:
        return Topology(
            problems=(Problem(SHAPE, f"the file is no YAML: {exc}"),), ref=ref, commit=commit
        )
    return parse(data, ref=ref, commit=commit)


# ---- the readings -------------------------------------------------------------


def path(capability_root: Path) -> Path:
    """The topology file in the working tree."""
    return capability_root / TOPOLOGY_RELATIVE


def read_working_tree(capability_root: Path) -> Topology | None:
    """The topology the working tree holds, or None where it holds none."""
    file = path(capability_root)
    if not file.is_file():
        return None
    try:
        text = file.read_text(encoding="utf-8")
    except OSError as exc:
        return Topology(problems=(Problem(SHAPE, f"the file cannot be read: {exc}"),))
    return _parse_text(text, ref=None, commit=None)


@dataclass(frozen=True)
class Settled:
    """The commit a run reads settled state at: the default branch's, or a base."""

    ref: str
    commit: str | None


def settled(capability_root: Path, *, run: Callable[..., Any] = subprocess.run) -> Settled:
    """The default branch's commit, as the backbone resolves it (COR-054 point 5).

    ``commit`` is None where the branch has no commit yet. Raises
    :class:`Unresolved` where the backbone does not answer or the branch
    resolves to no commit.
    """
    try:
        branch = default_branch.read(cwd=repo_root(capability_root), run=run).default_branch
    except default_branch.Unanswered as exc:
        raise Unresolved(str(exc)) from exc
    if branch.commit is not None:
        return Settled(branch.ref or branch.name, branch.commit)
    if branch.unborn:
        return Settled(branch.name, None)
    raise Unresolved(
        f"the default branch `{branch.name}` resolves to no commit"
        + (f": {branch.problem}" if branch.problem else "")
    )


def read(
    capability_root: Path,
    *,
    run: Callable[..., Any] = subprocess.run,
    git: Git | None = None,
) -> Topology | None:
    """The topology the default branch holds: the one the commands that act as a
    seat read (DEC-059 point 1).

    None where that commit declares no topology, or the branch has no commit yet.
    Raises :class:`Unresolved` where the branch resolves to no commit, or git
    cannot read the file there.
    """
    return read_at(capability_root, settled(capability_root, run=run), git=git)


def read_at(capability_root: Path, at: Settled, *, git: Git | None = None) -> Topology | None:
    """The topology the commit ``at`` holds, or None where it holds none.
    Raises :class:`Unresolved` where git cannot read it there."""
    if at.commit is None:
        return None
    text = _text_at(capability_root, at.commit, TOPOLOGY_RELATIVE, git)
    if text is None:
        return None
    return _parse_text(text, ref=at.ref, commit=at.commit)


def writers_at(
    capability_root: Path, at: Settled, *, git: Git | None = None
) -> state_issues.Writers:
    """Who may write on a seat's state issue, as the commit ``at`` holds the
    members ([pkit:ADR-071] point 3): the members' logins where the membership
    gate is closed, and an open gate where the commit names no member.
    Raises :class:`Unresolved` where git cannot read the members there."""
    text = (
        None if at.commit is None else _text_at(capability_root, at.commit, MEMBERS_RELATIVE, git)
    )
    if text is None:
        return state_issues.Writers.open()
    try:
        data = load(text)
    except ValueError as exc:
        raise Unresolved(f"the members at {at.commit} are no YAML: {exc}") from exc
    members = data.get("members") if isinstance(data, dict) else None
    logins = [
        str(m["github_login"])
        for m in (members if isinstance(members, list) else [])
        if isinstance(m, dict) and m.get("github_login")
    ]
    return state_issues.Writers.closed(logins) if logins else state_issues.Writers.open()


def repo_root(capability_root: Path) -> Path:
    """The repository the capability is installed in: ``.pkit/capabilities/<name>``'s
    grandparent's parent."""
    return capability_root.parents[2]


def _text_at(capability_root: Path, commit: str, relative: str, git: Git | None) -> str | None:
    """The text of the capability's file ``relative`` at ``commit``, or None where
    the commit holds no such file. Raises :class:`Unresolved` where git cannot say."""
    root = repo_root(capability_root)
    rel = (capability_root.relative_to(root) / relative).as_posix()
    runner = git or _git(root)
    try:
        listed = runner(["ls-tree", "-z", "--full-tree", "--name-only", commit, "--", rel])
    except OSError as exc:
        raise Unresolved(f"git could not be run ({exc})") from exc
    if listed.returncode != 0:
        raise Unresolved(f"git could not list {rel} at {commit}: {_said(listed)}")
    if rel not in (listed.stdout or "").split("\0"):
        return None
    shown = runner(["cat-file", "blob", f"{commit}:{rel}"])
    if shown.returncode != 0:
        raise Unresolved(f"git could not read {rel} at {commit}: {_said(shown)}")
    return shown.stdout or ""


def _git(root: Path) -> Git:
    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env={**os.environ, **_OFFLINE},
        )

    return run


def _said(proc: Any) -> str:
    lines = [line for line in str(getattr(proc, "stderr", "") or "").splitlines() if line.strip()]
    return lines[-1].strip() if lines else f"exit {getattr(proc, 'returncode', '?')}"


# ---- one run's snapshot (ADR-071 points 1 and 8) ---------------------------------

#: What a seat's state issue says of it: a clone holds it, it is free, or it
#: could not be read, which no reader takes for free.
HELD = "held"
FREE = "free"
UNREAD = "unread"


@dataclass(frozen=True)
class SeatState:
    """Who holds one seat, as this run read it from the seat's state issue.

    ``state`` is HELD, FREE or UNREAD. ``holder`` is the clone that holds it, and
    ``read`` the read that found it. ``cause`` says why an unread seat was not
    read: no state issue named, or a read that did not end."""

    seat: Seat
    state: str
    holder: state_issues.Holder | None = None
    read: state_issues.StateRead | None = None
    cause: str | None = None

    def held_by(self, clone: state_issues.Clone) -> bool:
        """Whether ``clone``, by its account and key, holds the seat."""
        return (
            self.state == HELD
            and self.holder is not None
            and bool(clone.account and clone.key)
            and self.holder.is_clone(clone.account, clone.key)
        )

    def said(self) -> str:
        """The seat's holder, in words a line can carry."""
        if self.state == FREE:
            return "free"
        if self.state == UNREAD or self.holder is None:
            return f"unread ({self.cause})"
        return (
            f"held by @{self.holder.account}, clone {self.holder.clone}, at "
            f"{self.holder.place or 'an unnamed place'}"
        )


class Snapshot:
    """One run's reading of the topology, and the inputs both seams take from it
    ([pkit:ADR-071] points 1 and 8).

    It holds the topology the default branch holds, the run of the state-issue
    seam, with the members at the same commit, and this clone by its account,
    key and place. :meth:`state` reads a seat's state issue the first time the
    run asks for it, and keeps what it read until :meth:`learn` replaces it with
    what a write of this run found."""

    def __init__(
        self, topology: Topology, run: state_issues.StateRun, clone: state_issues.Clone
    ) -> None:
        self.topology = topology
        self.run = run
        self.clone = clone
        self._states: dict[str, SeatState] = {}

    def state(self, name: str) -> SeatState | None:
        """Who holds the seat ``name``, or None where the topology has no such seat."""
        seat = self.topology.seat(name)
        if seat is None:
            return None
        if name not in self._states:
            self._states[name] = self._read(seat)
        return self._states[name]

    def states(self) -> tuple[SeatState, ...]:
        """Every seat's state, in the topology's order: one read for each seat."""
        return tuple(s for s in (self.state(seat.name) for seat in self.topology.seats) if s)

    def learn(self, seat: Seat, found: state_issues.StateRead | None) -> SeatState:
        """Keep what a write's last read found of ``seat`` for the rest of the run."""
        state = (
            _seat_state(seat, found)
            if found is not None
            else SeatState(seat, UNREAD, cause="its state issue was not read again")
        )
        self._states[seat.name] = state
        return state

    def _read(self, seat: Seat) -> SeatState:
        if seat.state_issue is None:
            return SeatState(seat, UNREAD, cause="the topology names no state issue for it")
        return _seat_state(
            seat, state_issues.read(seat.state_issue, SEAT_KIND, seat.name, self.run)
        )


def _seat_state(seat: Seat, found: state_issues.StateRead) -> SeatState:
    if found.outcome != state_issues.READ or found.fold is None:
        cause = found.cause or found.outcome
        return SeatState(seat, UNREAD, read=found, cause=cause)
    holder = found.fold.holder
    return SeatState(seat, FREE if holder is None else HELD, holder=holder, read=found)


def place(capability_root: Path) -> str:
    """Where this clone lies, in words a person reads: its machine and its folder
    (DEC-058 point 5)."""
    try:
        machine = socket.gethostname() or "an unnamed machine"
    except OSError:
        machine = "an unnamed machine"
    return f"{machine}:{repo_root(capability_root)}"


def snapshot(
    capability_root: Path,
    *,
    gh: state_issues.Gh,
    account: str | None,
    key: str | None,
    run: Callable[..., Any] = subprocess.run,
    git: Git | None = None,
    versions: Any = None,
) -> Snapshot | None:
    """This run's snapshot, or None where the default branch declares no topology.

    ``gh`` runs each call of the state-issue seam, and ``account`` and ``key``
    are this clone's GitHub account and its key, where it has them. The members
    who may write on a seat's state issue are read at the commit the topology was
    read at. Raises :class:`Unresolved` where the default branch, or the
    members there, cannot be read."""
    topology = read(capability_root, run=run, git=git)
    if topology is None:
        return None
    at = Settled(topology.ref or "the default branch", topology.commit)
    writers = writers_at(capability_root, at, git=git)
    state_run = state_issues.StateRun(
        gh, writers, versions if versions is not None else provenance.read_versions(capability_root)
    )
    clone = state_issues.Clone(account or "", key or "", place(capability_root))
    return Snapshot(topology, state_run, clone)


# ---- the check -----------------------------------------------------------------


def check(
    topology: Topology | None,
    *,
    base: Topology | None,
    workstreams_declared: Iterable[str],
    types: Iterable[str],
    substrate: str,
) -> list[Problem]:
    """Every problem of ``topology``, the change's, against ``base``, the topology
    it would replace.

    Adds to the parse's problems a scope naming a workstream or a type not
    declared, a topology under the ``label`` substrate, and each seat of the base
    deleted or moved rather than retired. A change that removes the file deletes
    every seat of the base.
    """
    problems = list(topology.problems) if topology is not None else []
    known_workstreams = set(workstreams_declared)
    known_types = set(types)
    seats = topology.seats if topology is not None else ()
    for seat in seats:
        if seat.scope is None:
            continue
        for name in seat.scope.workstreams:
            if name not in known_workstreams:
                problems.append(
                    Problem(
                        UNKNOWN_WORKSTREAM,
                        f"seat {seat.number} ({seat.name}) has a scope naming the workstream "
                        f"{name!r}, which `{workstreams.WORKSTREAMS_RELATIVE}` does not declare.",
                    )
                )
        for name in seat.scope.types:
            if name not in known_types:
                problems.append(
                    Problem(
                        UNKNOWN_TYPE,
                        f"seat {seat.number} ({seat.name}) has a scope naming the type {name!r}, "
                        f"which the type axis does not hold ({', '.join(sorted(known_types))}).",
                    )
                )
    if topology is not None and substrate == "label":
        problems.append(
            Problem(
                LABEL_SUBSTRATE,
                f"`{OWNERSHIP_RELATIVE}` selects the `label` substrate, and a topology keeps its "
                "ownership in the comment log, since a label cannot carry what a claim names "
                "(DEC-059 point 9): select `comment`, or remove the file.",
            )
        )
    if base is not None:
        problems += changes_against(base, topology)
    return problems


def changes_against(base: Topology, topology: Topology | None) -> list[Problem]:
    """Each seat of ``base`` that ``topology`` deleted or moved rather than retired.

    A seat that leaves the topology stays in its list, marked retired, and new
    seats are added at the end, so no seat's number moves (DEC-059 point 6).
    Renaming a seat retires it and adds a new one.
    """
    problems: list[Problem] = []
    for seat in base.seats:
        now = topology.seat(seat.name) if topology is not None else None
        if now is None:
            problems.append(
                Problem(
                    SEAT_DELETED,
                    f"seat {seat.number} ({seat.name}) of {base.where()} is gone. A seat "
                    "that leaves the topology stays in it, marked `retired: true`, and a "
                    "renamed seat is retired, with its new name added at the end.",
                )
            )
        elif now.number != seat.number:
            problems.append(
                Problem(
                    SEAT_MOVED,
                    f"seat {seat.name} moved from place {seat.number} of {base.where()} to "
                    f"place {now.number}, and a seat's number is its place: add new seats "
                    "at the end, and retire a seat rather than remove it.",
                )
            )
    return problems


@dataclass(frozen=True)
class Report:
    """What one run of the check found.

    ``topology`` is the change's, None where the working tree holds none.
    ``base`` is where the base was read, or None where it could not be, and
    ``notes`` say what the run could not judge and why.
    """

    topology: Topology | None
    base: Settled | None
    problems: tuple[Problem, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def failed(self) -> bool:
        return bool(self.problems)


def check_change(
    capability_root: Path,
    explicit_base: str | None = None,
    *,
    run: Callable[..., Any] = subprocess.run,
    git: Git | None = None,
) -> Report:
    """Check the working tree's topology against its base.

    The base is the default branch, or the base named for this run, on the
    command line or by a pipeline (COR-054 point 3), as the backbone resolves
    it. Where the working tree holds a topology and the base cannot be
    resolved, the check fails: it never compares with a guess. Where the
    working tree holds none, an unresolved base is noted, and nothing fails.
    """
    topology = read_working_tree(capability_root)
    notes: list[str] = []
    problems: list[Problem] = []
    at: Settled | None = None
    base_topology: Topology | None = None
    try:
        at = _base(capability_root, explicit_base, run)
        base_topology = read_at(capability_root, at, git=git)
    except Unresolved as exc:
        at = None
        if topology is not None:
            problems.append(
                Problem(
                    UNRESOLVED,
                    f"the base could not be read, so no seat is checked against it: {exc}",
                )
            )
        else:
            notes.append(
                f"the base could not be read, so a topology this change removes is not seen: {exc}"
            )
    if at is not None and at.commit is None:
        notes.append(f"the base `{at.ref}` has no commit yet, so there is nothing to compare with.")
    if topology is None and base_topology is None:
        return Report(None, at, tuple(problems), tuple(notes))
    declared = workstreams.read_declared(capability_root)
    problems += check(
        topology,
        base=base_topology,
        workstreams_declared=workstreams.slug_set(declared.parse) if declared else (),
        types=type_values(capability_root),
        substrate=ownership_substrate(capability_root),
    )
    return Report(topology, at, tuple(problems), tuple(notes))


def _base(capability_root: Path, explicit: str | None, run: Callable[..., Any]) -> Settled:
    try:
        reading = default_branch.read(explicit, cwd=repo_root(capability_root), run=run)
    except default_branch.Unanswered as exc:
        raise Unresolved(str(exc)) from exc
    base = reading.base
    if base.tip is not None:
        return Settled(base.ref, base.tip)
    if explicit is None and reading.default_branch.unborn:
        return Settled(base.ref, None)
    raise Unresolved(
        f"the base `{base.ref}` resolves to no commit"
        + (f": {base.problem}" if base.problem else "")
    )


def type_values(capability_root: Path) -> frozenset[str]:
    """The values of the type axis (``schemas/classification.yaml``), or none
    where the schema cannot be read."""
    try:
        data = load((capability_root / CLASSIFICATION_RELATIVE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    axes = data.get("axes") if isinstance(data, dict) else None
    axis = axes.get("type") if isinstance(axes, dict) else None
    values = axis.get("values") if isinstance(axis, dict) else None
    return frozenset(str(v) for v in values) if isinstance(values, list) else frozenset()


def ownership_substrate(capability_root: Path) -> str:
    """The ownership substrate the working tree selects (DEC-043 point 2):
    ``comment`` unless ``project/instance-ownership.yaml`` says ``label``."""
    file = capability_root / OWNERSHIP_RELATIVE
    try:
        data = load(file.read_text(encoding="utf-8")) if file.is_file() else None
    except (OSError, ValueError):
        data = None
    substrate = data.get("substrate") if isinstance(data, dict) else None
    return "label" if substrate == "label" else "comment"
