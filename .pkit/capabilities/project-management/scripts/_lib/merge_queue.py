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
backbone cannot answer — no `pkit`, a backbone that predates the command, a
run past its bound, an answer pm cannot read, a reading without a field a
decision rests on — the reading is :class:`Unreadable`, with the cause, as
when GitHub cannot be read: nothing merges on a guess.
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

from _lib.gh import gh_env

#: The backbone's pull-request command, and the version of its documents pm
#: reads — another is refused rather than misread.
ARGV = ("pkit", "pull-request")
VERSION = 1

#: How long pm waits for each of the backbone's answers, by subcommand, in
#: seconds: a reading or the squash-commit defaults is one `gh` read, two
#: when the host knows no merge queues; a merge or an enqueue is gh's merge
#: request; a dequeue is a reading, the request and a reading again. A run
#: that has not answered by then is ended with everything it started.
TIMEOUT_SECONDS: Mapping[str, float] = {
    "read": 60.0,
    "squash-defaults": 60.0,
    "merge": 120.0,
    "enqueue": 120.0,
    "dequeue": 180.0,
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
    return decode_reading(document.get("reading"))


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
    each reading whose description changed, as the backbone takes it. The
    backbone's run is bounded by the wait's own limit plus
    :data:`WAIT_MARGIN_SECONDS`. Raises :class:`Unreadable` when a reading
    cannot be taken, or the wait does not say how it ended.
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
            if document.get("event") == "reading":
                on_change(decode_reading(document.get("reading")))
                continue
            _raise_unreadable(document)
            how = document.get("ended")
            if how not in (MERGED, STILL_QUEUED, LEFT, HEAD_MOVED):
                raise Unreadable(
                    f"the backbone's answer says no way the wait ended (`ended`: {how!r})"
                )
            ended = Wait(str(how), decode_reading(document.get("reading")))
    if ended is None:
        raise Unreadable("the backbone's wait ended without saying how")
    return ended


def request(args: list[str], config: dict[str, Any]) -> Outcome:
    """A merge request the backbone makes (`merge`, `enqueue`, `dequeue`), and
    what it came to. Raises :class:`Unreadable` when the backbone gives no
    answer, or one that does not say whether the request was accepted — the
    request may then have been made, or not."""
    document = _first(args, config)
    accepted = document.get("accepted")
    if not isinstance(accepted, bool):
        raise Unreadable(
            f"the backbone's answer does not say whether the request was accepted "
            f"(`accepted`: {accepted!r})"
        )
    exit_code = document.get("exit_code")
    return Outcome(
        accepted=accepted,
        exit_code=exit_code if isinstance(exit_code, int) else None,
        reason=str(document.get("reason") or ""),
    )


# The fields of a reading a decision rests on, and their type. Read as false
# or empty when missing, each would fail open — a missing `has_queue` merges
# around the queue, a missing `dropped_head` enqueues a dropped head again —
# so a reading without one, or with one of another type, is no reading.
_DECIDING: Mapping[str, type] = {
    "has_queue": bool,
    "merged": bool,
    "queued": bool,
    "dropped_head": bool,
    "head_oid": str,
}


def decode_reading(value: object) -> Reading:
    """The reading a backbone document states. Raises :class:`Unreadable` when
    it states none, or lacks a field a decision rests on (`has_queue`,
    `merged`, `queued`, `dropped_head`, `head_oid`) or carries one of another
    type."""
    if not isinstance(value, Mapping):
        raise Unreadable("the backbone's answer names no reading")
    doc: Mapping[str, Any] = value
    for key, kind in _DECIDING.items():
        if key not in doc:
            raise Unreadable(f"the backbone's reading has no `{key}`")
        if not isinstance(doc[key], kind):
            raise Unreadable(
                f"the backbone's reading has a `{key}` that is not a {kind.__name__}: {doc[key]!r}"
            )
    removal = doc.get("removal")
    return Reading(
        has_queue=doc["has_queue"],
        merge_method=_text(doc.get("merge_method")),
        pr_id=_text(doc.get("pr_id")),
        pr_state=_text(doc.get("pr_state")),
        merged_at=_text(doc.get("merged_at")),
        head_oid=doc["head_oid"],
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
        merged=doc["merged"],
        queued=doc["queued"],
        squashes=doc.get("squashes") is True,
        dropped_head=doc["dropped_head"],
        description=_text(doc.get("description")),
    )


def _first(args: list[str], config: dict[str, Any]) -> dict[str, Any]:
    """The backbone's one document for `args`, read once its run has ended."""
    documents = list(_answers(args, config))
    if not documents:
        raise Unreadable(f"`{' '.join([*ARGV, *args[:1]])}` gave no answer")
    return documents[0]


def _raise_unreadable(document: Mapping[str, Any]) -> None:
    unreadable = document.get("unreadable")
    if unreadable:
        raise Unreadable(str(unreadable))


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
    bound, a document that is not JSON or of another version.
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
    """One line of the backbone's answer, as a document of the version pm reads."""
    try:
        document = json.loads(line)
    except ValueError:
        raise Unreadable(f"{command}: its answer is not JSON") from None
    version = document.get("schema_version") if isinstance(document, dict) else None
    if version != VERSION:
        raise Unreadable(f"{command} answered schema_version {version!r}; pm reads {VERSION}")
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


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
