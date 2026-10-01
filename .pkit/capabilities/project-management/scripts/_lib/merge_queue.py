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
the queue's merge and makes the merge requests — for these verbs and for the
backbone's own release merge alike, so the mechanic lives once. This module
asks it by subprocess and reads its JSON documents, as `_lib.default_branch`
reads `pkit repository base`; it never queries GitHub for a queue itself.
The command runs with the `gh` environment the adopter's config pins
([project-management:DEC-023-gh-host-and-owner]; `_lib.gh.gh_env`), so a
configured host reaches it.

A :class:`Reading` is the backbone's reading as its document states it —
what GitHub answered, and what the backbone concludes from it (merged, queued,
whether the queue dropped the PR at its current head, the phrase that
describes where it stands) — so pm never derives any of it again. When the
backbone cannot answer — no `pkit`, a backbone that predates the command, an
answer pm cannot read — the reading is :class:`Unreadable`, with the cause, as
when GitHub cannot be read: nothing merges on a guess.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from _lib.gh import gh_env

#: The backbone's pull-request command, and the version of its documents pm
#: reads — another is refused rather than misread.
ARGV = ("pkit", "pull-request")
VERSION = 1

# The queue merge method that makes the convention's one squash commit (DEC-013).
SQUASH = "SQUASH"

# The repository's squash-commit defaults the convention needs (DEC-013): the
# queue composes the squash commit from them, not from the merge command.
PR_TITLE = "PR_TITLE"
PR_BODY = "PR_BODY"

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


@dataclass(frozen=True)
class Outcome:
    """What a merge request the backbone made came to (`_lib.pr_merge`)."""

    accepted: bool
    #: gh's exit code; None when gh could not be run, or the backbone judged
    #: the request on a reading.
    exit_code: int | None
    #: Why it was not accepted, in gh's words or the backbone's.
    reason: str


def read(pr_number: int, config: dict[str, Any]) -> Reading:
    """Where PR `pr_number` stands with its base branch's merge queue, as the
    backbone reads it for the working directory's repository. Raises
    :class:`Unreadable` when GitHub, or the backbone, cannot answer."""
    document = _first(["read", str(pr_number)], config)
    _raise_unreadable(document)
    reading = decode_reading(document.get("reading"))
    if reading is None:
        raise Unreadable("the backbone's answer names no reading")
    return reading


def squash_commit_defaults(config: dict[str, Any]) -> tuple[str, str]:
    """The repository's default squash-commit title and message, as GitHub
    names them (`PR_TITLE` or `COMMIT_OR_PR_TITLE`; `PR_BODY`,
    `COMMIT_MESSAGES` or `BLANK`). A merge queue composes its squash commit
    from these and ignores what the merge command asks for. Raises
    :class:`Unreadable` when they cannot be read."""
    document = _first(["squash-defaults"], config)
    _raise_unreadable(document)
    title, message = document.get("title"), document.get("message")
    if not (isinstance(title, str) and isinstance(message, str)):
        raise Unreadable("the backbone's answer names no squash-commit defaults")
    return title, message


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
    each reading whose description changed, as the backbone takes it. Raises
    :class:`Unreadable` when a reading cannot be taken.
    """
    args = ["wait", str(pr_number)]
    if head_oid:
        args += ["--head", head_oid]
    if timeout_seconds is not None:
        args += ["--seconds", repr(float(timeout_seconds))]
    for document in _answers(args, config):
        if document.get("event") == "reading":
            reading = decode_reading(document.get("reading"))
            if reading is not None:
                on_change(reading)
            continue
        _raise_unreadable(document)
        ended = document.get("ended")
        reading = decode_reading(document.get("reading"))
        if ended not in (MERGED, STILL_QUEUED, LEFT, HEAD_MOVED) or reading is None:
            raise Unreadable("the backbone's answer says no way the wait ended")
        return Wait(str(ended), reading)
    raise Unreadable("the backbone's wait ended without saying how")


def request(args: list[str], config: dict[str, Any]) -> Outcome:
    """A merge request the backbone makes (`merge`, `enqueue`, `dequeue`), and
    what it came to. Raises :class:`Unreadable` when the backbone gives no
    answer — the request may then not have been made."""
    document = _first(args, config)
    exit_code = document.get("exit_code")
    return Outcome(
        accepted=document.get("accepted") is True,
        exit_code=exit_code if isinstance(exit_code, int) else None,
        reason=str(document.get("reason") or ""),
    )


def decode_reading(value: object) -> Reading | None:
    """The reading a backbone document states, or None when it states none."""
    if not isinstance(value, Mapping):
        return None
    doc: Mapping[str, Any] = value
    removal = doc.get("removal")
    return Reading(
        has_queue=doc.get("has_queue") is True,
        merge_method=_text(doc.get("merge_method")),
        pr_id=_text(doc.get("pr_id")),
        pr_state=_text(doc.get("pr_state")),
        merged_at=_text(doc.get("merged_at")),
        head_oid=_text(doc.get("head_oid")),
        in_queue=doc.get("in_queue") is True,
        position=_int_or_none(doc.get("position")),
        entry_state=_text(doc.get("entry_state")),
        eta_seconds=_int_or_none(doc.get("eta_seconds")),
        waiting_to_enter=doc.get("waiting_to_enter") is True,
        ever_queued=doc.get("ever_queued") is True,
        removal=(
            Removal(
                at=_text(removal.get("at")),
                reason=_text(removal.get("reason")),
                head_oid=_text(removal.get("head_oid")),
            )
            if isinstance(removal, Mapping)
            else None
        ),
        merged=doc.get("merged") is True,
        queued=doc.get("queued") is True,
        squashes=doc.get("squashes") is True,
        dropped_head=doc.get("dropped_head") is True,
        description=_text(doc.get("description")),
    )


def _first(args: list[str], config: dict[str, Any]) -> dict[str, Any]:
    """The backbone's one document for `args`."""
    for document in _answers(args, config):
        return document
    raise Unreadable(f"`{' '.join([*ARGV, *args[:1]])}` gave no answer")


def _raise_unreadable(document: Mapping[str, Any]) -> None:
    unreadable = document.get("unreadable")
    if unreadable:
        raise Unreadable(str(unreadable))


def _answers(args: list[str], config: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Run `pkit pull-request <args> --json` and yield each document it writes,
    as it writes it — a wait writes one per reading that changed.

    Raises :class:`Unreadable`, naming the cause, when the backbone gives no
    readable answer: no `pkit`, a backbone that predates the command, a
    document that is not JSON or of another version.
    """
    argv = [*ARGV, *args, "--json"]
    command = f"`{' '.join([*ARGV, *args[:1]])}`"
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=gh_env(config),
        )
    except FileNotFoundError as exc:
        raise Unreadable(f"{command}: `pkit` is not on PATH ({exc})") from exc
    except OSError as exc:
        raise Unreadable(f"{command} could not be run ({exc})") from exc
    answered = False
    with proc:
        assert proc.stdout is not None and proc.stderr is not None
        for line in proc.stdout:
            if not line.strip():
                continue
            try:
                document = json.loads(line)
            except ValueError:
                proc.kill()
                raise Unreadable(f"{command}: its answer is not JSON") from None
            version = document.get("schema_version") if isinstance(document, dict) else None
            if version != VERSION:
                proc.kill()
                raise Unreadable(
                    f"{command} answered schema_version {version!r}; pm reads {VERSION}"
                )
            answered = True
            yield document
        stderr = proc.stderr.read()
    if answered:
        return
    if "No such command" in stderr:
        raise Unreadable(
            f"{command}: the installed backbone predates it — upgrade it (`pkit upgrade`)"
        )
    said = [line.strip() for line in stderr.splitlines() if line.strip()]
    raise Unreadable(
        f"{command} exited {proc.returncode}" + (f": {said[-1]}" if said else " with no answer")
    )


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
