"""The session whose shell runs a command, and whether a recorded process runs, as the
backbone gives them ([pkit:ADR-103]; [pkit:ADR-100] point 9).

A seat's loop records the session that runs it by the name the backbone gives its
process, and asks later whether a recorded process still runs
([project-management:DEC-084-seat-session-address] points 1 to 3). The capability reads
no process itself, and names no harness: every reading comes from the backbone's
commands, through `pkit`, and this module only reads their documents
([pkit:ADR-103] point 1):

- :func:`session` runs ``pkit harness session --json``: whether a harness session runs
  this command, whether its harness gives messaging, its process's name and its
  messaging address, and each message's reply address in that address's form.
- :func:`read` runs ``pkit recorded-process read --json`` for the names given, and
  answers each *running*, *ended* or *cannot tell*.
- :func:`compare` runs ``pkit recorded-process compare --json``: whether two names
  name one process.

A name is stored and passed whole, and never parsed here. A document that cannot be
read, a version this module does not know and a value of a set it does not know each
read as *cannot tell*, and a session as none found (ADR-097 point 3).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, cast

try:
    from _lib import backbone
    from _lib import document_keys as keys
except ImportError:  # pragma: no cover - `scripts/_lib/` itself on sys.path
    import backbone  # type: ignore[no-redef]
    import document_keys as keys  # type: ignore[no-redef]

SESSION_ARGV = ("pkit", "harness", "session", "--json")
READ_ARGV = ("pkit", "recorded-process", "read", "--json")
COMPARE_ARGV = ("pkit", "recorded-process", "compare", "--json")
#: The version of the documents this module reads; another is no answer.
VERSION = 1
#: How long a call waits for the backbone, which reads only local state.
TIMEOUT = 30

#: Whether a recorded process runs, as the backbone answers it.
RUNNING = "running"
ENDED = "ended"
CANNOT_TELL = "cannot-tell"
STATES = frozenset({RUNNING, ENDED, CANNOT_TELL})

#: Whether two names name one process.
ONE = "one"
TWO = "two"
ANSWERS = frozenset({ONE, TWO, CANNOT_TELL})

Runner = Callable[..., subprocess.CompletedProcess[str]]


# ---- the session ---------------------------------------------------------------------


@dataclass(frozen=True)
class Reply:
    """A message's reply address as given, and in the form of a session's messaging
    address, None with why where it has none."""

    given: str
    address: str | None
    why: str | None = None


@dataclass(frozen=True)
class Session:
    """The harness session whose shell runs this command, as the backbone gives it.

    ``found`` says whether a session runs this command, and ``why`` why not.
    ``messaging`` says whether its harness gives messaging between sessions.
    ``process`` is its process's name, and ``address`` its messaging address, each
    None with why."""

    found: bool
    why: str | None = None
    messaging: bool = False
    process: str | None = None
    process_why: str | None = None
    address: str | None = None
    address_why: str | None = None
    replies: tuple[Reply, ...] = ()


def session(replies: Sequence[str] = (), *, run: Runner | None = None) -> Session:
    """The session whose shell runs this command, and each of ``replies`` in its
    address's form, as ``pkit harness session`` gives them."""
    argv = [*SESSION_ARGV, *(f"--reply={r}" for r in replies)]
    document, why = _ask(argv, None, run)
    if document is None:
        return Session(False, why)
    try:
        return session_of(document)
    except keys.Untold as exc:
        return Session(False, f"the document of `pkit harness session` could not be read: {exc}")


def session_of(document: object) -> Session:
    """The session a document of ``pkit harness session`` gives. Raises
    :class:`keys.Untold` where it cannot be read."""
    entry = _versioned(document)
    replies: list[Reply] = []
    for where, item in keys.objects(entry, "replies", ""):
        replies.append(
            Reply(
                keys.text(item, "given", where),
                keys.text_or_null(item, "address", where),
                keys.text_or_null(item, "why", where),
            )
        )
    return Session(
        found=keys.flag(entry, "found", ""),
        why=keys.text_or_null(entry, "why", ""),
        messaging=keys.flag(entry, "messaging", ""),
        process=keys.text_or_null(entry, "process", ""),
        process_why=keys.text_or_null(entry, "process_why", ""),
        address=keys.text_or_null(entry, "address", ""),
        address_why=keys.text_or_null(entry, "address_why", ""),
        replies=tuple(replies),
    )


# ---- whether a recorded process runs -------------------------------------------------


@dataclass(frozen=True)
class Reading:
    """Whether a recorded process runs: RUNNING, ENDED or CANNOT_TELL, and why."""

    state: str
    why: str

    @property
    def runs(self) -> bool:
        return self.state == RUNNING

    @property
    def ended(self) -> bool:
        return self.state == ENDED


def read(names: Sequence[str], *, run: Runner | None = None) -> list[Reading]:
    """Whether each process ``names`` names runs, as the backbone reads it from here, one
    reading for each, in their order."""
    if not names:
        return []
    document, why = _ask(list(READ_ARGV), {"names": list(names)}, run)
    if document is None:
        return [Reading(CANNOT_TELL, why or "the backbone gave no reading") for _ in names]
    try:
        return readings_of(document, len(names))
    except keys.Untold as exc:
        why = f"the document of `pkit recorded-process read` could not be read: {exc}"
        return [Reading(CANNOT_TELL, why) for _ in names]


def readings_of(document: object, count: int) -> list[Reading]:
    """The readings a document of ``pkit recorded-process read`` gives for ``count``
    names. A state it does not know reads as CANNOT_TELL. Raises
    :class:`keys.Untold` where it cannot be read."""
    answers = keys.objects(_versioned(document), "answers", "")
    if len(answers) != count:
        raise keys.Untold(f"{len(answers)} answers for {count} names")
    readings: list[Reading] = []
    for where, entry in answers:
        state = keys.text(entry, "state", where)
        why = keys.text(entry, "why", where)
        if state not in STATES:
            why = f"the backbone answered {state!r}, a state this does not know"
            state = CANNOT_TELL
        readings.append(Reading(state, why))
    return readings


def compare(left: str, right: str, *, run: Runner | None = None) -> str:
    """ONE, TWO or CANNOT_TELL: whether two names name one process, as the backbone
    compares them."""
    document, _ = _ask(list(COMPARE_ARGV), {"pairs": [[left, right]]}, run)
    if document is None:
        return CANNOT_TELL
    try:
        return answer_of(document)
    except keys.Untold:
        return CANNOT_TELL


def answer_of(document: object) -> str:
    """The answer a document of ``pkit recorded-process compare`` gives for one pair:
    ONE, TWO, or CANNOT_TELL for an answer it does not know. Raises
    :class:`keys.Untold` where it cannot be read."""
    pairs = keys.objects(_versioned(document), "pairs", "")
    if len(pairs) != 1:
        raise keys.Untold(f"{len(pairs)} pairs for one asked")
    where, pair = pairs[0]
    answer = keys.text(pair, "answer", where)
    return answer if answer in ANSWERS else CANNOT_TELL


# ---- the calls -----------------------------------------------------------------------


def _versioned(document: object) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise keys.Untold("the document is no object")
    entry = cast(dict[str, Any], document)
    version = keys.value(entry, "schema_version", "")
    if version != VERSION:
        raise keys.Untold(f"`schema_version` is {version!r}, not {VERSION}")
    return entry


def _ask(
    argv: list[str], request: dict[str, Any] | None, run: Runner | None
) -> tuple[object | None, str | None]:
    """Run a backbone command and read its one document, or None with why."""
    shown = " ".join(argv[1:3])
    try:
        proc = (run or backbone.run)(
            argv,
            input=json.dumps(request) if request is not None else None,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except FileNotFoundError:
        return None, "`pkit` is not on PATH"
    except subprocess.TimeoutExpired:
        return None, f"`pkit {shown}` did not answer within {TIMEOUT} seconds"
    except OSError as exc:
        return None, f"`pkit {shown}` failed: {exc}"
    if proc.returncode != 0:
        said = (proc.stderr or proc.stdout or "").strip().splitlines()
        tail = said[-1] if said else f"it exited {proc.returncode}"
        return None, f"the backbone's `pkit {shown}` gave no document ({tail}); it may predate it"
    try:
        return json.loads(proc.stdout or ""), None
    except ValueError as exc:
        return None, f"the document of `pkit {shown}` is no JSON: {exc}"
