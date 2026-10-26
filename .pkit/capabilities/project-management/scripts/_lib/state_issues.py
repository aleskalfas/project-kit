"""The state-issue seam: every read and write of a state issue (DEC-058, ADR-071).

[project-management:DEC-058-state-issues] keeps a piece of shared state that
changes while agents work in a **state issue**: an issue outside the work
hierarchy, whose comments log each change and whose description shows the
current state. [pkit:ADR-071] makes this module the one place that reads and
writes one. No other code reads a state issue's log, builds its marker or writes
its description. It sits beside the ownership seam (``_lib/instance_ownership``,
[pkit:ADR-041]), and neither calls the other. The two share the reader of a
comment log (``_lib/comment_log``) and the audit-log facility's builder and
parser (``_lib/audit_log``), and each keeps a fold of its own.

The marker
----------
A hidden stamp on a line of its own, ``<!-- pkit:state-issue v=1 kind=<kind>
key=<key> -->``, says that an issue is a state issue, of which kind of state and
for which key. Its values are encoded as a stamp's are, so a key may hold any
text. It sits in the first comment and in the description, outside the region
the seam rewrites. The comment's marker decides what a read accepts, and the
description's is the one a listing sees. :func:`read_marker` is the one function
that parses it, and every read of issues tells a state issue by it (ADR-071
point 6). It reads no GitHub.

Reads
-----
:func:`read` finds a state issue by its number. It reads the description and
the whole log, and accepts the issue where the earliest marker comment from an
author who may write names the kind and key. It counts each event comment for
that key whose author may write, and folds them (:func:`fold`): the first claim
on a free state holds, another clone's claim on a held state is void, and stays
void after a release. A read that finds the description's marker gone restores
it, the one write a read makes. :func:`find` reads, in number order, the state
issues the one read of issues (``_lib/issue_list``) left out of a listing of open
issues, where their description's marker names the key. The issue GitHub
numbered first holds the state.

Who may write is the caller's to pass (:class:`Writers`): the members, where the
membership gate is closed, or anyone GitHub records as having write access or
more, where it is open. A :class:`StateRun` asks GitHub once for each author in
a run and keeps the answer. A definite answer of less access, or an author
GitHub no longer has, counts as one who may not write. A call that fails makes
the read incomplete, since dropping a claim could free a held state.

Writes
------
Each change is one comment, built by the audit-log facility and wearing DEC-052's
frame. A claim is a read, the claim's comment and a read again that finds who
holds the state, and the claimant writes nothing more. A release frees the state
its clone holds. A release by force frees whatever holds when it lands, and the
caller checks who may release by force. After each event the seam rewrites the
description's region whole, from the fold of its next read, through the
provenance seam ([pkit:ADR-037]). A write to a closed state issue reopens it
first. :func:`create` makes a new one: a title, the description, then the marker's
comment and the filing comment. :func:`finish` completes a creation left half done.

What it never reads
-------------------
GitHub's search index, the description as the state, a state issue's labels,
type, parent, assignee, milestone or board fields, GitHub's association of an
author, a time, an issue of work, the topology, any configuration and the
clone's runtime file. The caller passes the number, the kind and key, who may
write, the clone's key and place, and the versions the provenance footer names.

Failure-posture neutral: every read and write reports its outcome, and the
caller decides what it means (ADR-071 point 9). A state issue is never an input
to a gate, a move of the lifecycle or the cascade.
"""

from __future__ import annotations

import contextlib
import json
import re
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import unquote

try:
    from _lib import audit_log, comment_log, provenance
    from _lib.body_rules import lines_outside_fences
except ImportError:  # pragma: no cover - a test that puts `_lib` itself on the path
    import audit_log  # type: ignore[no-redef]
    import comment_log  # type: ignore[no-redef]
    import provenance  # type: ignore[no-redef]
    from body_rules import lines_outside_fences  # type: ignore[no-redef]

#: The marker's signature and its version.
MARKER_PREFIX = "pkit:state-issue"
MARKER_VERSION = 1

#: The region of the description the seam rewrites whole.
VIEW_BEGIN = "<!-- pkit:state-view:begin -->"
VIEW_END = "<!-- pkit:state-view:end -->"

#: The kind of the marker's comment in DEC-052's roster.
MARKER_COMMENT_KIND = "state-marker"

#: The event types of a state issue, the audit-log facility's.
CLAIM = "state-claim"
RELEASE = "state-release"
FORCE_RELEASE = "state-force-release"
EVENTS = (CLAIM, RELEASE, FORCE_RELEASE)

#: Access levels GitHub records that count as write access or more.
WRITE_LEVELS = frozenset({"admin", "maintain", "write"})

# Outcomes of a read.
READ = "read"
INCOMPLETE = "incomplete"
NO_STATE_ISSUE = "no-state-issue"
FAILED = "failed"

# Outcomes of a write.
WROTE = "wrote"
ALREADY = "already"
UNCHANGED = "unchanged"
REBUILT = "rebuilt"

# Outcomes of a claim, a release and a creation.
CLAIMED = "claimed"
HELD = "held"
HELD_ELSEWHERE = "held-elsewhere"
LOST = "lost"
RELEASED = "released"
NOTHING = "nothing"
NOT_HOLDER = "not-holder"
CREATED = "created"
FINISHED = "finished"

_KIND = re.compile(r"[a-z][a-z0-9-]*")
_MARKER = re.compile(r"<!--\s*pkit:state-issue((?:\s+[^\s>]+)*)\s*-->")
_ISSUE_URL = re.compile(r"/issues/([0-9]{1,9})\s*$")
# A version is ASCII digits of bounded length, so no marker a hand writes can
# make the reader fail on it.
_NUMBER = re.compile(r"[0-9]{1,6}")

#: A ``gh`` runner: takes the argv, returns what ``subprocess.run`` returns.
Gh = Callable[[list[str]], Any]


# ---- the marker (ADR-071 point 6) ---------------------------------------------


@dataclass(frozen=True)
class Marker:
    """What a state issue's marker names. ``kind`` or ``key`` is empty, and
    ``version`` 0, where a marker carries none."""

    kind: str
    key: str
    version: int

    def names(self, kind: str, key: str) -> bool:
        """Whether this marker is this version's, for ``kind`` and ``key``,
        matched exactly, case included."""
        return self.version == MARKER_VERSION and self.kind == kind and self.key == key


def marker_line(kind: str, key: str) -> str:
    """The marker of the state issue that holds the ``kind`` of state ``key``."""
    if not _KIND.fullmatch(kind):
        raise ValueError(f"a kind of state is lowercase words joined by hyphens: {kind!r}")
    if not key:
        raise ValueError("a state issue's key is not empty")
    return f"<!-- {MARKER_PREFIX} v={MARKER_VERSION} kind={kind} key={audit_log.encode(key)} -->"


def read_marker(text: str) -> Marker | None:
    """The marker in ``text``, a description or a comment, or None.

    A marker counts on a line of its own, outside a fenced code block, so an
    issue of work that quotes one stays an issue of work. A marker of any
    version counts as one, whatever it names, so a later version of the stamp
    still keeps a state issue out of the listings of work.
    """
    for line in lines_outside_fences(text or ""):
        match = _MARKER.fullmatch(line.strip())
        if not match:
            continue
        attrs: dict[str, str] = {}
        for token in match.group(1).split():
            name, sep, value = token.partition("=")
            if sep and name not in attrs:
                attrs[name] = unquote(value)
        version = attrs.get("v", "")
        return Marker(
            kind=attrs.get("kind", ""),
            key=attrs.get("key", ""),
            version=int(version) if _NUMBER.fullmatch(version) else 0,
        )
    return None


def is_state_issue(text: str) -> bool:
    """Whether ``text``, an issue's description, marks its issue a state issue."""
    return read_marker(text) is not None


# ---- who may write, and one run ------------------------------------------------


@dataclass(frozen=True)
class Writers:
    """Who may write on a state issue, as the caller passes it (ADR-071 point 3).

    Where the membership gate is closed, the members' logins; where it is open,
    anyone GitHub records as having write access or more. The caller says which,
    so the seam never infers the gate's mode.
    """

    gate_open: bool
    logins: frozenset[str] = frozenset()

    @classmethod
    def closed(cls, logins: Iterable[str]) -> Writers:
        return cls(gate_open=False, logins=frozenset(str(x) for x in logins if x))

    @classmethod
    def open(cls) -> Writers:
        return cls(gate_open=True)


class StateRun:
    """One run of one command, from its start to its exit (ADR-071 point 8).

    It holds the ``gh`` runner, who may write, and the versions the provenance
    footer names. It keeps each author's judged access for the run, and nothing
    outlives it.
    """

    def __init__(self, gh: Gh, writers: Writers, versions: Any) -> None:
        self.gh = gh
        self.writers = writers
        self.versions = versions
        self._judged: dict[str, bool] = {}

    def may_write(self, login: str | None) -> tuple[bool | None, str | None]:
        """Whether ``login`` may write: ``(answer, None)``, or ``(None, cause)``
        when the call that would tell failed."""
        if not login:
            return False, None
        if not self.writers.gate_open:
            return login in self.writers.logins, None
        if login in self._judged:
            return self._judged[login], None
        try:
            proc = self.gh(permission_args(login))
        except FileNotFoundError:
            return None, "`gh` is not on PATH"
        if getattr(proc, "returncode", 1) != 0:
            if "HTTP 404" in str(getattr(proc, "stderr", "") or ""):
                self._judged[login] = False
                return False, None
            return None, f"the access of {login} could not be read: {comment_log.said(proc)}"
        try:
            data = json.loads(getattr(proc, "stdout", "") or "")
        except (TypeError, ValueError):
            data = None
        if not isinstance(data, dict) or not (data.get("permission") or data.get("role_name")):
            return None, f"GitHub gave no access level for {login}"
        answer = data.get("permission") in WRITE_LEVELS or data.get("role_name") in WRITE_LEVELS
        self._judged[login] = answer
        return answer, None


def permission_args(login: str) -> list[str]:
    """The ``gh api`` call that reads ``login``'s access to the repository."""
    return ["gh", "api", f"repos/{{owner}}/{{repo}}/collaborators/{login}/permission"]


# ---- the fold (ADR-071 point 4) -------------------------------------------------


@dataclass(frozen=True)
class Holder:
    """The clone that holds the state: the claim's author, the clone's key and
    the place the claim named."""

    account: str
    clone: str
    place: str

    def is_clone(self, account: str, clone: str) -> bool:
        return self.account == account and self.clone == clone


@dataclass(frozen=True)
class StateEvent:
    """One counted event of a state issue's log. ``void`` marks one that
    changed nothing."""

    comment_id: int
    author: str
    type: str
    clone: str
    place: str
    reason: str | None = None
    act: str | None = None
    void: bool = False


@dataclass(frozen=True)
class Fold:
    """The state the counted events give: who holds it, or free, and the
    events, the void ones marked, for a person to read."""

    holder: Holder | None
    events: tuple[StateEvent, ...] = ()

    @property
    def free(self) -> bool:
        return self.holder is None


def fold(events: Iterable[StateEvent]) -> Fold:
    """Fold counted events, in their order, to who holds the state.

    A claim on a free state makes its claimant the holder. A claim by the
    holder's account and key changes nothing, and any other claim on a held
    state is void. A release frees the state where it names the holder's account
    and key, and any other is void. A release by force frees whatever holds when
    it lands. The fold takes no time.
    """
    holder: Holder | None = None
    out: list[StateEvent] = []
    for ev in events:
        void = False
        if ev.type == CLAIM:
            if holder is None:
                holder = Holder(ev.author, ev.clone, ev.place)
            elif not holder.is_clone(ev.author, ev.clone):
                void = True
        elif ev.type == RELEASE:
            if holder is not None and holder.is_clone(ev.author, ev.clone):
                holder = None
            else:
                void = True
        elif ev.type == FORCE_RELEASE:
            if holder is not None:
                holder = None
            else:
                void = True
        else:
            continue
        out.append(replace(ev, void=void))
    return Fold(holder, tuple(out))


# ---- reads (ADR-071 points 2 and 3) ---------------------------------------------


@dataclass(frozen=True)
class StateRead:
    """What one read of a state issue found.

    ``outcome`` is READ, INCOMPLETE (with ``cause``), NO_STATE_ISSUE or FAILED.
    On READ, ``fold`` is the state, ``open`` whether the issue is open and
    ``description`` its body as read. ``restored`` is the outcome of restoring a
    missing marker to the description, where the read did. ``acts`` holds the id
    of every act the log records, for a retry to find its own.
    """

    outcome: str
    number: int
    kind: str
    key: str
    fold: Fold | None = None
    open: bool | None = None
    description: str = ""
    cause: str | None = None
    restored: str | None = None
    acts: frozenset[str] = frozenset()


def read(number: int, kind: str, key: str, run: StateRun) -> StateRead:
    """Read the state issue ``number`` for the ``kind`` of state ``key``."""
    issue, cause = _view(number, run)
    if issue is None:
        return StateRead(FAILED, number, kind, key, cause=cause)
    log = comment_log.read_log(number, run.gh)
    if not log.complete:
        return StateRead(INCOMPLETE, number, kind, key, cause=log.cause)
    accepted, cause = _accepts(log.comments, kind, key, run)
    if cause is not None:
        return StateRead(INCOMPLETE, number, kind, key, cause=cause)
    if not accepted:
        return StateRead(
            NO_STATE_ISSUE,
            number,
            kind,
            key,
            cause=f"#{number} is no state issue for the {kind} {key!r}",
        )
    events, cause = _counted(log.comments, key, run)
    if cause is not None:
        return StateRead(INCOMPLETE, number, kind, key, cause=cause)
    folded = fold(events)
    body = str(issue.get("body") or "")
    restored = None
    marker = read_marker(body)
    if marker is None or not marker.names(kind, key):
        restored = _write_description(number, description(kind, key, folded, run.versions), run)
    acts = frozenset(
        ev.act
        for ev in (audit_log.parse(c.body) for c in log.comments)
        if ev is not None and ev.act
    )
    return StateRead(
        READ,
        number,
        kind,
        key,
        fold=folded,
        open=str(issue.get("state") or "").upper() == "OPEN",
        description=body,
        restored=restored.outcome if restored is not None else None,
        acts=acts,
    )


def _accepts(
    comments: Iterable[comment_log.LogComment], kind: str, key: str, run: StateRun
) -> tuple[bool, str | None]:
    """Whether the earliest marker comment from an author who may write names
    ``kind`` and ``key``; or the cause where an author could not be judged."""
    for comment in comments:
        marker = read_marker(comment.body)
        if marker is None:
            continue
        may, cause = run.may_write(comment.author)
        if cause is not None:
            return False, cause
        if may:
            return marker.names(kind, key), None
    return False, None


def _counted(
    comments: Iterable[comment_log.LogComment], key: str, run: StateRun
) -> tuple[list[StateEvent], str | None]:
    """The events for ``key`` whose author may write, in the log's order."""
    out: list[StateEvent] = []
    for comment in comments:
        ev = audit_log.parse(comment.body)
        if ev is None or ev.type not in EVENTS or ev.get("key") != key:
            continue
        may, cause = run.may_write(comment.author)
        if cause is not None:
            return [], cause
        if not may:
            continue
        out.append(
            StateEvent(
                comment_id=comment.id,
                author=str(comment.author),
                type=ev.type,
                clone=ev.get("clone") or "",
                place=ev.get("place") or "",
                reason=ev.get("reason"),
                act=ev.act,
            )
        )
    return out, None


@dataclass(frozen=True)
class Found:
    """What :func:`find` found for one kind and key.

    ``read`` is the state issue that holds the state, the one GitHub numbered
    first. ``duplicates`` are later state issues for the same key, and
    ``half_done`` the issues whose description is marked with no marker comment,
    a creation left half done.
    """

    outcome: str
    read: StateRead | None = None
    duplicates: tuple[int, ...] = ()
    half_done: tuple[int, ...] = ()
    cause: str | None = None


def find(kind: str, key: str, rows: Iterable[dict[str, Any]], run: StateRun) -> Found:
    """Find the state issue for ``kind`` and ``key`` among ``rows``.

    ``rows`` are the state issues the one read of issues left out of a listing
    of open issues (``IssueListing.state_rows``), each with its ``number`` and
    ``body``. Those whose description's marker names the kind and key are read
    by number, lowest first. A caller that claims lists again
    before it claims, and again when it reads after claiming, and writes only to
    the first (DEC-058 point 2).
    """
    numbers = sorted(
        int(row["number"])
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("number"), int)
        and (read_marker(str(row.get("body") or "")) or Marker("", "", 0)).names(kind, key)
    )
    first: StateRead | None = None
    duplicates: list[int] = []
    half_done: list[int] = []
    for number in numbers:
        found = read(number, kind, key, run)
        if found.outcome in (INCOMPLETE, FAILED) and first is None:
            return Found(found.outcome, cause=found.cause)
        if found.outcome == NO_STATE_ISSUE:
            half_done.append(number)
        elif found.outcome == READ:
            if first is None:
                first = found
            else:
                duplicates.append(number)
    if first is None:
        return Found(NO_STATE_ISSUE, half_done=tuple(half_done))
    return Found(READ, read=first, duplicates=tuple(duplicates), half_done=tuple(half_done))


def _view(number: int, run: StateRun) -> tuple[dict | None, str | None]:
    """The issue's description and whether it is open: one call."""
    try:
        proc = run.gh(["gh", "issue", "view", str(number), "--json", "number,state,body"])
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    if getattr(proc, "returncode", 1) != 0:
        return None, f"#{number} could not be read: {comment_log.said(proc)}"
    try:
        data = json.loads(getattr(proc, "stdout", "") or "")
    except (TypeError, ValueError):
        return None, f"#{number} read as no JSON"
    if not isinstance(data, dict):
        return None, f"#{number} read as no JSON object"
    return data, None


# ---- the description (ADR-071 point 5) ------------------------------------------


def view_text(kind: str, key: str, folded: Fold) -> str:
    """The region of the description: the state the comments give, for a person."""
    lines = [
        "> [!NOTE]",
        f"> This issue holds the state of the {kind} {_code(key)}. Its comments are the"
        " record, and this part shows the state they give.",
        ">",
    ]
    holder = folded.holder
    if holder is None:
        lines.append("> **Free.**")
    else:
        lines.append(
            f"> **Held** by the account {_code(holder.account)}, clone"
            f" {_code(holder.clone)}, at {audit_log.one_line(holder.place) or 'an unnamed place'}."
        )
    return "\n".join(lines)


def description(kind: str, key: str, folded: Fold, versions: Any) -> str:
    """The whole description: the marker, the region and the provenance footer."""
    head = "\n".join(
        [marker_line(kind, key), "", VIEW_BEGIN, view_text(kind, key, folded), VIEW_END]
    )
    return provenance.stamp(head, versions)


def rewrite_view(after: StateRead, run: StateRun, *, previous: Fold | None = None) -> str:
    """Rewrite the region whole from the fold of ``after``, a read that followed
    an event, and say what the write did.

    UNCHANGED where the description already shows that state, REBUILT where a
    hand had changed it from what ``previous``, the fold before the event,
    showed, WROTE otherwise, or FAILED. The region is a view, so a failed write
    loses nothing.
    """
    if after.outcome != READ or after.fold is None:
        return FAILED
    if after.restored == WROTE:
        return UNCHANGED
    new = description(after.kind, after.key, after.fold, run.versions)
    current = after.description
    if provenance.strip_footer(current) == provenance.strip_footer(new):
        return UNCHANGED
    hand = previous is not None and provenance.strip_footer(current) != provenance.strip_footer(
        description(after.kind, after.key, previous, run.versions)
    )
    written = _write_description(after.number, new, run)
    if written.outcome != WROTE:
        return FAILED
    return REBUILT if hand else WROTE


# ---- writes (ADR-071 point 5) ---------------------------------------------------


@dataclass(frozen=True)
class Write:
    """What one write did: WROTE, ALREADY (the act had landed) or FAILED."""

    outcome: str
    cause: str | None = None


@dataclass(frozen=True)
class Clone:
    """The clone that writes: its account, its key and where it lies, in words a
    person reads, such as its machine and folder (DEC-058 point 5)."""

    account: str
    key: str
    place: str


@dataclass(frozen=True)
class Outcome:
    """What a claim, a release or a creation did.

    ``holder`` holds the state once the step is over, as its last read found;
    ``freed`` is the holder a release freed. ``view`` is the outcome of the
    region's rewrite, and ``read`` the last read.
    """

    outcome: str
    number: int | None
    holder: Holder | None = None
    freed: Holder | None = None
    cause: str | None = None
    view: str | None = None
    read: StateRead | None = None


def comment_args(number: int, body: str) -> list[str]:
    """The ``gh`` call that posts one comment on a state issue."""
    return ["gh", "issue", "comment", str(number), "--body", body]


def description_args(number: int, path: str) -> list[str]:
    """The ``gh`` call that writes a state issue's description from a file."""
    return ["gh", "issue", "edit", str(number), "--body-file", path]


def create_args(title: str, path: str) -> list[str]:
    """The ``gh`` call that creates a state issue: a title and a description,
    and no type, parent, label, assignee or milestone."""
    return ["gh", "issue", "create", "--title", title, "--body-file", path]


def reopen_args(number: int) -> list[str]:
    return ["gh", "issue", "reopen", str(number)]


def close_args(number: int) -> list[str]:
    return ["gh", "issue", "close", str(number)]


def marker_comment(kind: str, key: str, versions: Any) -> str:
    """The marker's comment, posted first on a new state issue."""
    return "\n".join(
        [
            f"📌 {MARKER_COMMENT_KIND} — this issue holds the {kind} {_code(key)}",
            "",
            marker_line(kind, key),
            audit_log.kind_marker(MARKER_COMMENT_KIND),
            "",
            provenance.render_comment_footer(versions),
        ]
    )


def post_event(
    number: int, ev: audit_log.Event, run: StateRun, *, after_failure: bool = False
) -> Write:
    """Post one event's comment on the state issue ``number``.

    Always posted, whatever the audit projection says (ADR-071 point 5). A retry
    after a failed post passes ``after_failure``: the log is read first, and
    nothing is posted where the act had landed (DEC-044 point 2).
    """
    if ev.type not in EVENTS:
        raise ValueError(f"not a state-issue event: {ev.type!r}")
    if after_failure and ev.act:
        log = comment_log.read_log(number, run.gh)
        if not log.complete:
            return Write(FAILED, log.cause)
        if audit_log.posted((c.body for c in log.comments), ev.act):
            return Write(ALREADY)
    return _run_write(comment_args(number, audit_log.build(ev, versions=run.versions)), run)


def claim(
    number: int, kind: str, key: str, clone: Clone, run: StateRun, *, act: str | None = None
) -> Outcome:
    """Claim the state for ``clone``: a read, the claim's comment, a read again.

    No comment is posted where the first read finds the state held, by this
    clone (HELD) or another (HELD_ELSEWHERE). Otherwise the second read says
    whether this clone holds it (CLAIMED) or another clone claimed first (LOST).
    The claimant writes no further event, whatever that read finds.
    """
    first = read(number, kind, key, run)
    if first.outcome != READ or first.fold is None:
        return Outcome(first.outcome, number, cause=first.cause, read=first)
    holder = first.fold.holder
    if holder is not None:
        held = holder.is_clone(clone.account, clone.key)
        return Outcome(HELD if held else HELD_ELSEWHERE, number, holder=holder, read=first)
    ev = audit_log.event(CLAIM, key=key, clone=clone.key, place=clone.place, id=act)
    return _post_and_reread(first, ev, clone, run, success=CLAIMED)


def release(
    number: int, kind: str, key: str, clone: Clone, run: StateRun, *, act: str | None = None
) -> Outcome:
    """Release the state ``clone`` holds. NOTHING where it is free, and
    NOT_HOLDER, with no write, where another clone holds it."""
    first = read(number, kind, key, run)
    if first.outcome != READ or first.fold is None:
        return Outcome(first.outcome, number, cause=first.cause, read=first)
    holder = first.fold.holder
    if holder is None:
        return Outcome(NOTHING, number, read=first)
    if not holder.is_clone(clone.account, clone.key):
        return Outcome(NOT_HOLDER, number, holder=holder, read=first)
    ev = audit_log.event(RELEASE, key=key, clone=clone.key, place=clone.place, id=act)
    return _post_and_reread(first, ev, clone, run, success=RELEASED, freed=holder)


def force_release(
    number: int,
    kind: str,
    key: str,
    clone: Clone,
    reason: str,
    run: StateRun,
    *,
    act: str | None = None,
) -> Outcome:
    """Release the state by force, with its reason, whoever holds it.

    The caller checks first that its author may release by force (DEC-059 point
    5). The holder is read just before the write, so a holder that changes in
    between is the one it frees. NOTHING where the state is free.
    """
    if not reason.strip():
        raise ValueError("a release by force carries its reason")
    first = read(number, kind, key, run)
    if first.outcome != READ or first.fold is None:
        return Outcome(first.outcome, number, cause=first.cause, read=first)
    holder = first.fold.holder
    if holder is None:
        return Outcome(NOTHING, number, read=first)
    ev = audit_log.event(
        FORCE_RELEASE, key=key, clone=clone.key, place=clone.place, reason=reason.strip(), id=act
    )
    return _post_and_reread(first, ev, clone, run, success=RELEASED, freed=holder)


def _post_and_reread(
    first: StateRead,
    ev: audit_log.Event,
    clone: Clone,
    run: StateRun,
    *,
    success: str,
    freed: Holder | None = None,
) -> Outcome:
    number = first.number
    if first.open is False:
        reopened = _run_write(reopen_args(number), run)
        if reopened.outcome != WROTE:
            return Outcome(FAILED, number, cause=reopened.cause, read=first)
    posted = post_event(number, ev, run)
    second = read(number, first.kind, first.key, run)
    landed = second.outcome == READ and ev.act in second.acts
    if posted.outcome == FAILED and not landed:
        return Outcome(FAILED, number, cause=posted.cause, read=second)
    if second.outcome != READ or second.fold is None:
        return Outcome(
            second.outcome,
            number,
            freed=freed,
            cause=f"the {ev.type} was posted, but the read after it did not end: {second.cause}",
            read=second,
        )
    view = rewrite_view(second, run, previous=first.fold)
    holder = second.fold.holder
    outcome = success
    if ev.type == CLAIM and not (holder is not None and holder.is_clone(clone.account, clone.key)):
        outcome = LOST
    return Outcome(outcome, number, holder=holder, freed=freed, view=view, read=second)


def create(kind: str, key: str, title: str, run: StateRun) -> Outcome:
    """Create a state issue for ``kind`` and ``key``, then finish it.

    The issue takes ``title``, for people, and the description, and no type,
    parent, label, assignee or milestone. The marker's comment is posted first,
    and DEC-041's filing comment after it.
    """
    body = description(kind, key, Fold(None), run.versions)
    proc, cause = _with_file(body, lambda path: run.gh(create_args(title, path)))
    if proc is None or getattr(proc, "returncode", 1) != 0:
        return Outcome(FAILED, None, cause=cause or comment_log.said(proc))
    match = _ISSUE_URL.search(str(getattr(proc, "stdout", "") or "").strip())
    if match is None:
        return Outcome(FAILED, None, cause="`gh issue create` printed no issue's URL")
    done = finish(int(match.group(1)), kind, key, run)
    return replace(done, outcome=CREATED) if done.outcome == FINISHED else done


def finish(number: int, kind: str, key: str, run: StateRun) -> Outcome:
    """Finish a creation left half done: post the marker's comment where none
    from an author who may write is there, and the filing comment where it is
    missing. NO_STATE_ISSUE where an earlier marker comment names another key."""
    log = comment_log.read_log(number, run.gh)
    if not log.complete:
        return Outcome(INCOMPLETE, number, cause=log.cause)
    accepted, cause = _accepts(log.comments, kind, key, run)
    if cause is not None:
        return Outcome(INCOMPLETE, number, cause=cause)
    if not accepted:
        if any(read_marker(c.body) for c in log.comments if _authored_by_writer(c, run)):
            return Outcome(NO_STATE_ISSUE, number, cause=f"#{number} holds another state")
        posted = _run_write(comment_args(number, marker_comment(kind, key, run.versions)), run)
        if posted.outcome != WROTE:
            return Outcome(FAILED, number, cause=posted.cause)
    if not any(provenance.FILING_MARKER in c.body for c in log.comments):
        filing = provenance.render_filing_comment(run.versions)
        posted = _run_write(comment_args(number, filing), run)
        if posted.outcome != WROTE:
            return Outcome(FINISHED, number, cause=f"the filing comment failed: {posted.cause}")
    return Outcome(FINISHED, number)


def _authored_by_writer(comment: comment_log.LogComment, run: StateRun) -> bool:
    may, _cause = run.may_write(comment.author)
    return bool(may)


def close(number: int, run: StateRun) -> Write:
    """Close a state issue whose state has left use, as its caller says."""
    return _run_write(close_args(number), run)


def _write_description(number: int, body: str, run: StateRun) -> Write:
    proc, cause = _with_file(body, lambda path: run.gh(description_args(number, path)))
    if proc is None:
        return Write(FAILED, cause)
    return _outcome(proc)


def _with_file(body: str, call: Callable[[str], Any]) -> tuple[Any, str | None]:
    """Run ``call`` with the path of a file that holds ``body``, as every
    body write does (``--body-file``)."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(body)
        path = f.name
    try:
        return call(path), None
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    finally:
        with contextlib.suppress(OSError):
            Path(path).unlink()


def _run_write(argv: list[str], run: StateRun) -> Write:
    try:
        proc = run.gh(argv)
    except FileNotFoundError:
        return Write(FAILED, "`gh` is not on PATH")
    return _outcome(proc)


def _outcome(proc: Any) -> Write:
    if getattr(proc, "returncode", 1) == 0:
        return Write(WROTE)
    return Write(FAILED, comment_log.said(proc))


def _code(value: str) -> str:
    """A value as a code span on one line, so no value starts a line of its
    own ahead of a marker."""
    return audit_log.code(value)


def runner(config: dict[str, Any]) -> Gh:
    """A ``gh`` runner through the gh helper (DEC-023), for a caller to pass."""

    def run(argv: list[str]) -> Any:
        try:
            from _lib.gh import gh_run
        except ImportError:  # pragma: no cover
            from gh import gh_run  # type: ignore[no-redef]
        return gh_run(argv, config, check=False)

    return run
