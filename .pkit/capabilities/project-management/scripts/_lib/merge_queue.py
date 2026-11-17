"""Whether a PR's base branch merges through a queue, and where the PR stands
in it — the reading the merge verbs take before they merge (#1011,
[project-management:DEC-026-work-ownership-lifecycle]).

A merge queue takes a PR in and makes the merge itself. It builds the merge
the PR would make on top of the base branch and of whatever is queued ahead
of it, runs the base's required checks on that prospective merge commit, and
merges it once they pass, by the queue's own merge method. A PR whose checks
fail there, or that no longer merges cleanly, leaves the queue unmerged.
Merging directly on such a base goes around the queue, so the merge verbs read
this first and hand the PR to the queue (`_lib.pr_merge.land`).

**The reading is the backbone's** ([project-management:DEC-013-branch-and-pr-conventions],
"Merge mechanics"). The backbone's `pkit pull-request` reads GitHub, waits for
the queue's merge, makes the merge requests and deletes a merged PR's head
branch — for these verbs and for the backbone's own release merge alike, so
the mechanic lives once. This module
asks it by subprocess and reads its JSON documents, as `_lib.default_branch`
reads `pkit repository base`; it never queries GitHub for a queue itself.
The command runs with the `gh` environment the adopter's config pins
([project-management:DEC-023-gh-host-and-owner]; `_lib.gh.gh_env`), so a
configured host reaches it.

A :class:`Reading` is the backbone's reading as its document states it —
what GitHub answered, and what the backbone concludes from it (merged, queued,
whether the queue dropped the PR at its current head, the phrase that
describes where it stands) — so pm never derives any of it again. When the
backbone cannot answer — no `pkit`, a backbone that predates the command, a
run past its bound, an answer that is not JSON — the reading is
:class:`Unreadable`, with the cause, as when GitHub cannot be read: nothing
merges on a guess.

**Each document is read by its keys** (ADR-097 point 3): `reading_of`,
`squash_defaults_of`, `wait_line_of`, `outcome_of` and `deletion_of`, one for
each document. A key pm does not read it ignores. A key it reads that is
missing, null where the CLI reference does not print it null, or of another
type, a value it does not know of a set it decides on, and a version other
than :data:`VERSION`, make the document :class:`Unreadable`, never a default
such as false or empty. GitHub's own words a reading passes on — the PR's
state, the queue's merge method and its entry's state — are kept as GitHub
gives them, a word pm does not know among them: pm decides on none of them,
since the backbone's conclusions are its answer.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import IO, Any

from _lib import document_keys as keys
from _lib.gh import gh_env

#: The backbone's pull-request command, and the version of its documents pm
#: reads — another is refused rather than misread.
ARGV = ("pkit", "pull-request")
VERSION = 1
VERSION_KEY = "schema_version"

#: How long pm waits for each of the backbone's answers, by subcommand, in
#: seconds. The backbone bounds each of its own `gh` calls (a reading, a
#: request) and states the longest each subcommand can run, every call at its
#: bound (`pull_request_landing.longest_seconds`): a reading is up to three
#: `gh` reads, when the host knows no merge queues; the squash-commit defaults
#: one; a merge or an enqueue the cross-repository guard, gh's merge request
#: and, when it gets no answer, the readings that settle it — the second no
#: sooner than its window after the request; a dequeue the guard, a reading
#: or two, and up to two requests, each with the readings that settle it; a
#: branch deletion the guard, two readings, the request and a reading again.
#: A test holds each bound here above the backbone's figure with room to
#: start `pkit`, so the backbone's document comes back before pm stops
#: waiting. A run that has not answered by then is ended with everything it
#: started, the `gh` it runs among it.
TIMEOUT_SECONDS: Mapping[str, float] = {
    "read": 90.0,
    "squash-defaults": 60.0,
    "merge": 210.0,
    "enqueue": 210.0,
    "dequeue": 600.0,
    "delete-branch": 180.0,
}

#: A wait is bounded by its own limit — the seconds asked for, else the
#: backbone's cap — plus this margin: the reading the backbone may still take
#: after the limit, the interval before it, and starting `pkit`.
WAIT_MARGIN_SECONDS = 5 * 60.0

# The queue merge method that makes the convention's one squash commit (DEC-013).
SQUASH = "SQUASH"

# The repository's squash-commit defaults the convention needs (DEC-013): the
# queue composes the squash commit from them, not from the merge command.
PR_TITLE = "PR_TITLE"
PR_BODY = "PR_BODY"

# Every squash-commit title and message GitHub names, as the backbone passes
# them on: another is one pm cannot tell the convention's from.
_SQUASH_TITLES = (PR_TITLE, "COMMIT_OR_PR_TITLE")
_SQUASH_MESSAGES = (PR_BODY, "COMMIT_MESSAGES", "BLANK")

# The backbone's wait limits, as its reference states them, for this
# capability's messages: a wait that follows the queue's estimate waits that
# long plus the margin, never longer than the cap. A test holds them equal to
# the backbone's.
ETA_MARGIN_SECONDS = 120.0
MAX_WAIT_SECONDS = 30 * 60.0

# How a wait ended (:class:`Wait`).
MERGED = "merged"
STILL_QUEUED = "queued"
LEFT = "left"
HEAD_MOVED = "head-moved"
_WAIT_ENDS = (MERGED, STILL_QUEUED, LEFT, HEAD_MOVED)

# The lines of a wait's stream, by their `event`: a reading taken, and its end.
_READING_EVENT = "reading"
_END_EVENT = "end"


class Unreadable(Exception):
    """The reading could not be taken; the message says why."""


@dataclass(frozen=True)
class Removal:
    """The queue dropping the PR, as GitHub records it."""

    at: str
    #: Why, in GitHub's words; empty when it gives none.
    reason: str
    #: The PR's head when it was dropped; empty when GitHub does not say.
    head_oid: str


@dataclass(frozen=True)
class Reading:
    """Where a PR stands with its base branch's merge queue, as the backbone
    reads it."""

    #: The base branch merges through a queue.
    has_queue: bool
    #: The queue's merge method (`SQUASH`, `MERGE`, `REBASE`); empty without one.
    merge_method: str = ""
    #: The PR's node ID, which the queue's own mutations take.
    pr_id: str = ""
    #: The PR's state: `OPEN`, `CLOSED` or `MERGED`.
    pr_state: str = ""
    merged_at: str = ""
    #: The PR's head commit.
    head_oid: str = ""
    in_queue: bool = False
    #: The PR's place in the queue, 1 first; None outside it.
    position: int | None = None
    #: The entry's state: `QUEUED`, `AWAITING_CHECKS`, `MERGEABLE`,
    #: `UNMERGEABLE` or `LOCKED`; empty outside the queue.
    entry_state: str = ""
    eta_seconds: int | None = None
    #: Auto-merge holds the PR until its own required checks pass; it enters
    #: the queue then.
    waiting_to_enter: bool = False
    #: The PR has been in a merge queue at some point.
    ever_queued: bool = False
    #: The queue dropping the PR, when that is the queue's last word on it.
    removal: Removal | None = None
    #: The PR has merged.
    merged: bool = False
    #: In the queue, or held by auto-merge until it may enter.
    queued: bool = False
    #: The queue merges by squash.
    squashes: bool = False
    #: The queue dropped the PR at the head it has now, and it has not been
    #: queued or merged since — re-enqueueing it needs `--force`.
    dropped_head: bool = False
    #: Where the PR stands, as one phrase.
    description: str = ""

    def describe(self) -> str:
        """Where the PR stands, as one phrase for a verb's output."""
        return self.description


@dataclass(frozen=True)
class Wait:
    """How a wait for the queue's merge ended: `ended` is :data:`MERGED`,
    :data:`STILL_QUEUED` (the time ran out), :data:`LEFT` or
    :data:`HEAD_MOVED`; `reading` is the last reading taken."""

    ended: str
    reading: Reading


#: A request's document's `reason_kind` when the backbone's cross-repository
#: guard refused it, and made no request.
FOREIGN_REPOSITORY = "foreign-repository"

#: A request's document's `reason_kind` when the request got no answer and
#: the backbone settled it by reading: :data:`NOT_MADE`, two readings did not
#: see it made (`accepted` false) — what they saw, not that it was not made,
#: since the service may still apply it; :data:`UNANSWERED`, the PR could not
#: be read since, so whether it was made is not known (`accepted` null) —
#: unconfirmed. A dequeue the service answered whose PR could not be read
#: since is unconfirmed too, :data:`NOT_READ`; one that found the PR merged
#: is not accepted, :data:`HAS_MERGED`.
NOT_MADE = "not-made"
UNANSWERED = "unanswered"
NOT_READ = "unreadable"
HAS_MERGED = "merged"

# The `reason_kind`s that come with a null `accepted`: whether the request
# was made is not known.
_UNCONFIRMED_KINDS = (UNANSWERED, NOT_READ)

# Every `reason_kind` each request's document names, beside null: another is
# one pm cannot tell what the request came to by.
_MERGE_KINDS = (FOREIGN_REPOSITORY, NOT_MADE, UNANSWERED)
_REQUEST_KINDS: Mapping[str, tuple[str, ...]] = {
    "merge": _MERGE_KINDS,
    "enqueue": _MERGE_KINDS,
    "dequeue": (*_MERGE_KINDS, HAS_MERGED, NOT_READ),
}


@dataclass(frozen=True)
class Outcome:
    """What a merge request the backbone made came to (`_lib.pr_merge`)."""

    #: True once made; False when not; None when the backbone could not tell
    #: whether it was made (`reason_kind` :data:`UNANSWERED`, or
    #: :data:`NOT_READ` for a dequeue): unconfirmed.
    accepted: bool | None
    #: gh's exit code; None when gh could not be run, or the backbone judged
    #: the request on a reading.
    exit_code: int | None
    #: Why it was not accepted, or why whether it was is not known, in gh's
    #: words or the backbone's.
    reason: str
    #: :data:`FOREIGN_REPOSITORY` when the backbone's cross-repository guard
    #: refused the request, which was then not made; :data:`NOT_MADE` or
    #: :data:`UNANSWERED` when the request got no answer and the backbone
    #: settled it by reading; :data:`NOT_READ` or :data:`HAS_MERGED` for a
    #: dequeue (above); "" otherwise, where the document's is null.
    reason_kind: str = ""
    #: What the backbone's guard compared, as its document states it, for a
    #: message: `verdict` (the comparison alone), and the `anchor` and the
    #: `target`, each null where the guard names none (`_guard`). pm decides
    #: nothing on it. None only for an outcome no document stated.
    guard: Mapping[str, Any] | None = None


#: How the backbone's deletion of a merged PR's head branch ended
#: (:class:`BranchDeletion`): deleted at the head that merged; kept, with why;
#: gone — not there, whoever removed it; refused, the deletion not asked for;
#: or unconfirmed, asked for with no usable answer and no reading since, so
#: whether it was deleted is not known.
DELETED = "deleted"
KEPT = "kept"
GONE = "gone"
REFUSED = "refused"
UNCONFIRMED = "unconfirmed"
_DELETION_ENDS = (DELETED, KEPT, GONE, REFUSED, UNCONFIRMED)

#: The `reason_kind` of a deletion refused because the PR's head is in a fork.
CROSS_REPOSITORY = "cross-repository"

# Every `reason_kind` a deletion's document names, beside null.
_DELETION_KINDS = (
    "tip-moved",
    "open-pull-request",
    "deletion-refused",
    UNANSWERED,
    "not-merged",
    CROSS_REPOSITORY,
    "expect-mismatch",
    NOT_READ,
    FOREIGN_REPOSITORY,
)


@dataclass(frozen=True)
class BranchDeletion:
    """What the backbone's deletion of a merged PR's head branch came to, as
    its document states it (`_lib.pr_merge.delete_branch`)."""

    #: :data:`DELETED`, :data:`KEPT`, :data:`GONE`, :data:`REFUSED` or
    #: :data:`UNCONFIRMED`.
    outcome: str
    #: The head branch, by name; "" when the backbone did not read it.
    branch: str
    #: The branch's tip, when it was kept; "" otherwise.
    tip: str
    #: Why it was kept, refused or unconfirmed, in the backbone's terms
    #: (`tip-moved`, `open-pull-request`, `deletion-refused`, `unanswered`;
    #: :data:`CROSS_REPOSITORY`, `expect-mismatch`, :data:`FOREIGN_REPOSITORY`,
    #: …); "" otherwise.
    reason_kind: str
    #: The same, in words.
    reason: str
    #: The PR's head as the backbone read it — the head it merged at; "" when
    #: it did not read the PR.
    merged_head: str


def read(pr_number: int, config: dict[str, Any]) -> Reading:
    """Where PR `pr_number` stands with its base branch's merge queue, as the
    backbone reads it for the working directory's repository. Raises
    :class:`Unreadable` when GitHub, or the backbone, cannot answer."""
    return reading_of(_first(["read", str(pr_number)], config))


def reading_of(document: Mapping[str, Any]) -> Reading:
    """The reading `pkit pull-request read --json` states. Raises
    :class:`Unreadable` with the backbone's `unreadable`, or when the document
    cannot be read by its keys."""
    _of_version(document)
    _raise_unreadable(document)
    return decode_reading(_value(document, "reading", "the reading"))


def squash_commit_defaults(config: dict[str, Any]) -> tuple[str, str]:
    """The repository's default squash-commit title and message, as GitHub
    names them (`PR_TITLE` or `COMMIT_OR_PR_TITLE`; `PR_BODY`,
    `COMMIT_MESSAGES` or `BLANK`). A merge queue composes its squash commit
    from these and ignores what the merge command asks for. Raises
    :class:`Unreadable` when they cannot be read."""
    return squash_defaults_of(_first(["squash-defaults"], config))


def squash_defaults_of(document: Mapping[str, Any]) -> tuple[str, str]:
    """The squash-commit title and message `pkit pull-request squash-defaults
    --json` states. A name GitHub has not been known to give is no default pm
    can tell the convention's from: :class:`Unreadable`."""
    _of_version(document)
    _raise_unreadable(document)
    try:
        return (
            keys.one_of(document, "title", "", _SQUASH_TITLES),
            keys.one_of(document, "message", "", _SQUASH_MESSAGES),
        )
    except keys.Untold as exc:
        raise Unreadable(
            f"the backbone's answer names no squash-commit defaults pm can read: {exc}"
        ) from None


def wait_for_merge(
    pr_number: int,
    config: dict[str, Any],
    *,
    timeout_seconds: float | None,
    on_change: Callable[[Reading], None],
    head_oid: str = "",
) -> Wait:
    """Wait for the queue to merge the PR, as the backbone waits: until it
    merges, leaves the queue, or the time runs out.

    `timeout_seconds` None follows the queue's estimate, plus a margin, within
    a cap; a number is a fixed deadline, and 0 reads once. The backbone
    declares the PR out of the queue only on two readings running, and with
    `head_oid` — the head the caller's gates checked — ends the wait at once
    on a reading at another head (:data:`HEAD_MOVED`). `on_change` is handed
    each reading whose description changed, as the backbone takes it. The
    backbone's run is bounded by the wait's own limit plus
    :data:`WAIT_MARGIN_SECONDS`. Raises :class:`Unreadable` when a reading
    cannot be taken, a line of the wait cannot be read (`wait_line_of`), or
    the wait does not say how it ended.
    """
    args = ["wait", str(pr_number)]
    if head_oid:
        args += ["--head", head_oid]
    if timeout_seconds is not None:
        args += ["--seconds", repr(float(timeout_seconds))]
    limit = MAX_WAIT_SECONDS if timeout_seconds is None else timeout_seconds
    ended: Wait | None = None
    with contextlib.closing(
        _answers(args, config, timeout_seconds=limit + WAIT_MARGIN_SECONDS)
    ) as documents:
        for document in documents:
            line = wait_line_of(document)
            if isinstance(line, Reading):
                on_change(line)
            else:
                ended = line
    if ended is None:
        raise Unreadable("the backbone's wait ended without saying how")
    return ended


def wait_line_of(document: Mapping[str, Any]) -> Reading | Wait:
    """One line of `pkit pull-request wait --json`, by its `event`: the reading
    a `reading` line states, or how the wait ended, from its `end`. Raises
    :class:`Unreadable` with the backbone's `unreadable`, and for a line it
    cannot read by its keys: an `event` pm does not know among them, which
    says nothing pm can wait on."""
    _of_version(document)
    try:
        event = keys.one_of(document, "event", "", (_READING_EVENT, _END_EVENT))
    except keys.Untold as exc:
        raise Unreadable(f"the backbone's wait wrote a line pm cannot read: {exc}") from None
    if event == _READING_EVENT:
        return decode_reading(_value(document, "reading", "the wait's reading"))
    _raise_unreadable(document)
    try:
        how = keys.one_of(document, "ended", "", _WAIT_ENDS)
    except keys.Untold as exc:
        raise Unreadable(f"the backbone's answer says no way the wait ended: {exc}") from None
    return Wait(how, decode_reading(_value(document, "reading", "how the wait ended")))


def request(args: list[str], config: dict[str, Any]) -> Outcome:
    """A merge request the backbone makes (`merge`, `enqueue`, `dequeue`), and
    what it came to (`outcome_of`). Raises :class:`Unreadable` when the
    backbone gives no answer, or one pm cannot read — the request may then
    have been made, or not."""
    return outcome_of(_first(args, config), args[0])


def outcome_of(document: Mapping[str, Any], command: str) -> Outcome:
    """What the request `command` (`merge`, `enqueue` or `dequeue`) came to, as
    its document states it. Raises :class:`Unreadable` when it does not say
    whether the request was accepted, or cannot be read by its keys: a
    `reason_kind` the command's document does not name among them.

    The backbone runs the cross-repository guard before the request; a
    request it refused is not accepted, with `reason_kind`
    :data:`FOREIGN_REPOSITORY` and what the guard compared. A request that
    got no answer the backbone settles by reading: made, accepted; not seen
    made on two readings, not accepted with `reason_kind` :data:`NOT_MADE`;
    the PR not readable since, `accepted` None with `reason_kind`
    :data:`UNANSWERED` — or, for a dequeue the service answered,
    :data:`NOT_READ`: the only answers whose `accepted` is null, which say
    whether it was made is not known."""
    _of_version(document)
    try:
        accepted = keys.flag_or_null(document, "accepted", "")
    except keys.Untold as exc:
        raise Unreadable(
            f"the backbone's answer does not say whether the request was accepted: {exc}"
        ) from None
    try:
        reason_kind = keys.one_of_or_null(document, "reason_kind", "", _REQUEST_KINDS[command])
        outcome = Outcome(
            accepted=accepted,
            exit_code=keys.number_or_null(document, "exit_code", ""),
            reason=keys.text(document, "reason", ""),
            reason_kind=reason_kind or "",
            guard=_guard(keys.mapping(document, "guard", "")),
        )
    except keys.Untold as exc:
        raise Unreadable(
            f"the backbone's answer about the {command} cannot be read: {exc}"
        ) from None
    if accepted is None and reason_kind not in _UNCONFIRMED_KINDS:
        raise Unreadable(
            f"the backbone's answer does not say whether the request was accepted "
            f"(`accepted`: None, `reason_kind`: {reason_kind!r})"
        )
    return outcome


def _guard(guard: Mapping[str, Any]) -> Mapping[str, Any]:
    """What pm says of the backbone's guard where it refused a request: its
    verdict, as the guard words it, and the session's anchor and the target it
    compared, each null where the guard names none. pm decides nothing on them,
    so a verdict it does not know is said as the guard gives it."""
    where = "guard"
    return {
        "verdict": keys.text(guard, "verdict", where),
        "anchor": keys.text_or_null(guard, "anchor", where),
        "target": keys.text_or_null(guard, "target", where),
    }


def deletion(args: list[str], config: dict[str, Any]) -> BranchDeletion:
    """The backbone's deletion of a merged PR's head branch (`delete-branch`,
    with `args` after the subcommand's name), and what it came to
    (`deletion_of`). Raises :class:`Unreadable` when the backbone gives no
    answer, or one pm cannot read — the branch may then have been deleted, or
    not."""
    return deletion_of(_first(["delete-branch", *args], config))


def deletion_of(document: Mapping[str, Any]) -> BranchDeletion:
    """What the deletion came to, as `pkit pull-request delete-branch --json`
    states it. Raises :class:`Unreadable` when the document names no way the
    deletion ended, or cannot be read by its keys: a `reason_kind` it does not
    name among them.

    The backbone runs the cross-repository guard before it reads the PR; a
    deletion it refused there is :data:`REFUSED`, its `reason_kind`
    :data:`FOREIGN_REPOSITORY`."""
    _of_version(document)
    try:
        ended = keys.one_of(document, "outcome", "", _DELETION_ENDS)
    except keys.Untold as exc:
        raise Unreadable(f"the backbone's answer says no way the deletion ended: {exc}") from None
    try:
        return BranchDeletion(
            outcome=ended,
            branch=keys.text_or_null(document, "branch", "") or "",
            tip=keys.text_or_null(document, "tip", "") or "",
            reason_kind=keys.one_of_or_null(document, "reason_kind", "", _DELETION_KINDS) or "",
            reason=keys.text_or_null(document, "reason", "") or "",
            merged_head=keys.text_or_null(document, "merged_head", "") or "",
        )
    except keys.Untold as exc:
        raise Unreadable(
            f"the backbone's answer about the deletion cannot be read: {exc}"
        ) from None


def decode_reading(value: object) -> Reading:
    """The reading a backbone document states, wherever it holds one. Raises
    :class:`Unreadable` when it states none, or one with a field :class:`Reading`
    holds that cannot be read by its key. Read as false or empty when missing,
    a field would fail open: a missing `has_queue` merges around the queue, a
    missing `dropped_head` enqueues a dropped head again. A key the reading
    holds that pm does not read, such as `ahead`, it ignores."""
    if not isinstance(value, Mapping):
        raise Unreadable("the backbone's answer names no reading")
    doc: Mapping[str, Any] = value
    where = "reading"
    try:
        removal = keys.mapping_or_null(doc, "removal", where)
        return Reading(
            has_queue=keys.flag(doc, "has_queue", where),
            merge_method=keys.text(doc, "merge_method", where),
            pr_id=keys.text(doc, "pr_id", where),
            pr_state=keys.text(doc, "pr_state", where),
            merged_at=keys.text(doc, "merged_at", where),
            head_oid=keys.text(doc, "head_oid", where),
            in_queue=keys.flag(doc, "in_queue", where),
            position=keys.number_or_null(doc, "position", where),
            entry_state=keys.text(doc, "entry_state", where),
            eta_seconds=keys.number_or_null(doc, "eta_seconds", where),
            waiting_to_enter=keys.flag(doc, "waiting_to_enter", where),
            ever_queued=keys.flag(doc, "ever_queued", where),
            removal=None if removal is None else _removal(removal, keys.at(where, "removal")),
            merged=keys.flag(doc, "merged", where),
            queued=keys.flag(doc, "queued", where),
            squashes=keys.flag(doc, "squashes", where),
            dropped_head=keys.flag(doc, "dropped_head", where),
            description=keys.text(doc, "description", where),
        )
    except keys.Untold as exc:
        raise Unreadable(f"the backbone's reading cannot be read: {exc}") from None


def _removal(removal: Mapping[str, Any], where: str) -> Removal:
    return Removal(
        at=keys.text(removal, "at", where),
        reason=keys.text(removal, "reason", where),
        head_oid=keys.text(removal, "head_oid", where),
    )


def _first(args: list[str], config: dict[str, Any]) -> dict[str, Any]:
    """The backbone's one document for `args`, read once its run has ended."""
    documents = list(_answers(args, config))
    if not documents:
        raise Unreadable(f"`{' '.join([*ARGV, *args[:1]])}` gave no answer")
    return documents[0]


def _of_version(document: Mapping[str, Any]) -> None:
    """Refuse a document of another version than :data:`VERSION`, or of none:
    the pull-request documents carried theirs from their first release."""
    version = document.get(VERSION_KEY)
    if type(version) is not int or version != VERSION:
        raise Unreadable(f"the backbone answered schema_version {version!r}; pm reads {VERSION}")


def _value(document: Mapping[str, Any], key: str, what: str) -> Any:
    """The value at `key` of the document itself, null included."""
    try:
        return keys.value(document, key, "")
    except keys.Untold as exc:
        raise Unreadable(f"the backbone's answer names no {what}: {exc}") from None


def _raise_unreadable(document: Mapping[str, Any]) -> None:
    """Raise :class:`Unreadable` with why the backbone could not read GitHub,
    where its document says (`unreadable`, null where it could)."""
    try:
        unreadable = keys.text_or_null(document, "unreadable", "")
    except keys.Untold as exc:
        raise Unreadable(f"the backbone's answer cannot be read: {exc}") from None
    if unreadable is not None:
        raise Unreadable(unreadable or "the backbone could not read GitHub, and gave no reason")


# The two streams of a run, as `_answers` tells their lines apart.
_STDOUT = "stdout"
_STDERR = "stderr"

# A line on the backbone's standard error that is a warning, passed on even
# when it answered: the router's notices (`pkit: …` — running the installed
# tool rather than the project's own, say) and lines marked as warnings.
_WARNING = re.compile(r"(pkit: |\[warn\] |warn(ing)?: )", re.IGNORECASE)

# The warnings passed on in this run, each once however many answers carry it.
_passed_on: set[str] = set()


def _answers(
    args: list[str], config: dict[str, Any], *, timeout_seconds: float | None = None
) -> Iterator[dict[str, Any]]:
    """Run `pkit pull-request <args> --json` and yield each document it writes,
    as it writes it — a wait writes one per reading that changed.

    Standard output and standard error are read as they come, so neither
    fills while the other is read to its end, and a warning on standard error
    is passed on whether or not a document came back. The run is bounded —
    by `timeout_seconds`, else by its subcommand's (:data:`TIMEOUT_SECONDS`) —
    and runs in a session of its own, so a run past its bound, or left when
    its reader stops, is ended with everything it started: a `gh` request
    still running would otherwise go on after pm has read the PR to decide.

    Raises :class:`Unreadable`, naming the cause, when the backbone gives no
    readable answer: no `pkit`, a `pkit` without the command, a run past its
    bound, a line that is not a JSON object.
    """
    argv = [*ARGV, *args, "--json"]
    command = f"`{' '.join([*ARGV, *args[:1]])}`"
    bound = TIMEOUT_SECONDS[args[0]] if timeout_seconds is None else timeout_seconds
    env = gh_env(config)
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise Unreadable(f"{command}: `pkit` is not on PATH ({exc})") from exc
    except OSError as exc:
        raise Unreadable(f"{command} could not be run ({exc})") from exc
    lines: queue.Queue[tuple[str, str | None]] = queue.Queue()
    for name, stream in ((_STDOUT, proc.stdout), (_STDERR, proc.stderr)):
        threading.Thread(target=_pump, args=(name, stream, lines), daemon=True).start()
    deadline = time.monotonic() + bound
    said: list[str] = []
    answered = False
    try:
        open_streams = 2
        while open_streams:
            try:
                name, line = lines.get(timeout=max(0.0, deadline - time.monotonic()))
            except queue.Empty:
                raise Unreadable(
                    f"{command} gave no answer within {bound:g} s, and was stopped"
                ) from None
            if line is None:
                open_streams -= 1
            elif name == _STDERR:
                said.append(line.strip())
                _pass_on(line)
            elif line.strip():
                document = _document(line, command)
                answered = True
                yield document
        returncode = proc.wait(timeout=max(1.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        raise Unreadable(f"{command} did not end within {bound:g} s, and was stopped") from None
    finally:
        _end(proc, answered=answered)
    if answered:
        return
    if any("No such command" in line for line in said):
        raise Unreadable(
            f"{command}: the `pkit` that ran — {_which(env)} — has no such command, so this "
            "project's backbone is older than project-management needs. Upgrade the backbone "
            "(`pkit upgrade`), or put a `pkit` that has the command first on PATH"
        )
    said = [line for line in said if line]
    raise Unreadable(
        f"{command} exited {returncode}" + (f": {said[-1]}" if said else " with no answer")
    )


def _pump(name: str, stream: IO[str] | None, lines: queue.Queue[tuple[str, str | None]]) -> None:
    """Put each line of `stream` on `lines` as it comes, then `None` at its end."""
    if stream is None:
        lines.put((name, None))
        return
    try:
        for line in stream:
            lines.put((name, line))
    except (OSError, ValueError):  # the stream broke under the reader
        pass
    finally:
        lines.put((name, None))
        stream.close()


def _document(line: str, command: str) -> dict[str, Any]:
    """One line of the backbone's answer, as a JSON object: each reading refuses
    one of another version than pm reads (`_of_version`)."""
    try:
        document = json.loads(line)
    except ValueError:
        raise Unreadable(f"{command}: its answer is not JSON") from None
    if not isinstance(document, dict):
        raise Unreadable(f"{command}: its answer is not a document")
    return document


def _pass_on(line: str) -> None:
    """Say a warning the backbone wrote on standard error, once per run."""
    text = line.strip()
    if _WARNING.match(text) and text not in _passed_on:
        _passed_on.add(text)
        print(text, file=sys.stderr, flush=True)


def _end(proc: subprocess.Popen[str], *, answered: bool) -> None:
    """End the run and everything it started, if it has not ended by itself.

    The run leads a session of its own, so one signal to its process group
    reaches what it started — a `gh` request among them. A run that ended by
    itself without answering has its group swept too: what it left running
    could still act on the PR.
    """
    running = proc.poll() is None
    if running or not answered:
        _kill_group(proc)
    proc.wait()


def _kill_group(proc: subprocess.Popen[str]) -> None:
    if hasattr(os, "killpg"):
        with contextlib.suppress(ProcessLookupError, PermissionError):  # the group has ended
            os.killpg(proc.pid, signal.SIGKILL)
    elif proc.poll() is None:  # no process groups on this platform
        proc.kill()


def _which(env: Mapping[str, str]) -> str:
    """The `pkit` a run finds on `env`'s PATH, as a path."""
    return shutil.which(ARGV[0], path=env.get("PATH")) or "not found on PATH"
