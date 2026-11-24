"""Whether a recorded process runs, read in one place (ADR-103).

Some parts of the methodology note a process they did not start, and ask later
whether it still runs: a seat's loop asks it of the session recorded for a seat
([project-management:DEC-084-seat-session-address] points 2 and 3), and the
register of a clone's runs of a run's processes (ADR-100 point 6). Each asks the
backbone here, and reads no process for itself (ADR-103 point 1):

- :func:`name` names a process by its id: its process space, its id and the start
  time the operating system fixed when it made the process, each part this
  command can read (point 2). Only this module writes a name. Every other part
  stores and passes it whole.
- :func:`read` answers, for each name, *running*, *ended* or *cannot tell*, the
  reading that told, and why (points 1, 3 and 4).
- :func:`compare` answers whether two names name one process (point 3, "One
  process, two names").

**A name** is one line of text, tagged with its form: ``p1:<machine>:<boot>:
<namespace>:<id>:<start>``. The machine, the boot and the namespace are digests
derived for the repository, the same in every clone of it, with no key, so a name
can go on the tracker and a reader in another clone on the same machine derives
the same value (point 2, "Where other clones read it"). The namespace reads
``-`` on a platform with no process namespaces. A part this command could not
read is left empty, and a name with any part of its space empty reads as *cannot
tell* everywhere. The start time is the operating system's own: on macOS the
seconds and microseconds of the process table's ``p_starttime``, on Linux the
clock ticks after the boot of field 22 of ``/proc/<id>/stat``. Neither follows a
locale, a time zone or the clock.

**Ended** is answered only where this command runs in the recorded space and
could see the process, or where the recorded space belongs to an earlier boot of
this machine and the platform's source of the machine's identity names one
machine (point 3). That source is the platform's UUID on macOS, read as naming
one machine only where macOS reports that it does not run virtual, since a
virtual machine's identity can be copied with it. On Linux the machine's id is
copied with a disk image, so the earlier-boot rule never applies there. No failed
read, and no form this module does not know, reads as *ended*.

**By the id alone** (point 4): where the start time cannot be compared, a null
signal stands in only on a platform the adapter's declaration names, and only
once the same signal finds the process of the session this command runs in.

The operating system is reached through a :class:`System`, so a test gives its
own. Failure-posture neutral: each answer says what it found, and each part that
asks says what *cannot tell* means for it (point 6).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import os
import re
import struct
import subprocess
import sys
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

#: The form of the names this module writes, the tag each name starts with.
FORM = "p1"
#: Every form this module reads (point 2, "Tagged with its form").
FORMS = frozenset({FORM})

#: What a reading says of a recorded process.
RUNNING = "running"
ENDED = "ended"
CANNOT_TELL = "cannot-tell"

#: The reading that told.
BY_START_TIME = "start-time"
BY_ID_ALONE = "id-alone"
BY_EARLIER_BOOT = "earlier-boot"

#: What a comparison of two names says.
ONE = "one"
TWO = "two"

#: What a null signal, sent only to test whether a process with an id exists,
#: found: a process under the id (delivered, or refused for want of permission,
#: which only a process that holds the id refuses), no process, or a failure.
FOUND = "found"
NONE = "none"
FAILED = "failed"

#: The namespace part of a space on a platform with no process namespaces.
NO_NAMESPACES = "-"

#: The highest process id a name may hold. A null signal to 0 or below would
#: reach a group of processes, never one, so no such id is ever read.
MAX_PID = 2**31 - 1

_DIGEST = re.compile(r"[0-9a-f]{16}")
_START = re.compile(r"[0-9]{1,20}(?:\.[0-9]{1,9})?")
_PID = re.compile(r"[1-9][0-9]{0,9}")


# ---- the operating system ------------------------------------------------------------------


@dataclass(frozen=True)
class RawSpace:
    """The process space a command runs in, as the operating system gives it: each
    part's value, None where it could not be read. ``namespaces`` says whether the
    platform has process namespaces, and ``unique_machine`` whether its source of
    the machine's identity names one machine. ``why`` says why a part did not read."""

    machine: str | None
    boot: str | None
    namespace: str | None
    namespaces: bool
    unique_machine: bool
    why: str | None = None


@dataclass(frozen=True)
class Entry:
    """One read of a process's entry in the operating system's table. ``found`` is
    None where the read failed, with ``why``; ``start`` the start time where it was
    read; ``exited`` whether the process has exited and waits only to be collected."""

    found: bool | None
    start: str | None = None
    exited: bool = False
    why: str | None = None


class System(Protocol):
    """What this module asks of the operating system."""

    @property
    def platform(self) -> str: ...

    def space(self) -> RawSpace: ...

    def entry(self, pid: int) -> Entry: ...

    def signal(self, pid: int) -> str: ...


def null_signal(pid: int) -> str:
    """FOUND, NONE or FAILED: what a signal of nothing says of ``pid`` from here."""
    if not 1 <= pid <= MAX_PID:
        return FAILED
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return NONE
    except PermissionError:
        return FOUND
    except OSError:
        return FAILED
    return FOUND


#: macOS's `sysctl` names for one process's entry in the kernel's process table
#: (`kern.proc.pid.<id>`), and where its `struct kinfo_proc` holds the start time
#: the kernel fixed when it made the process (`p_starttime`, a `struct timeval`),
#: the process's state (`p_stat`) and its id (`p_pid`), on a 64-bit machine. The
#: id is read back, so an entry of another layout is never misread.
_CTL_KERN, _KERN_PROC, _KERN_PROC_PID = 1, 14, 1
_KINFO_STAT_OFFSET = 36
_KINFO_PID_OFFSET = 40
#: A process that has exited and waits only to be collected (`SZOMB`).
_MACOS_ZOMBIE = 5
#: How long `gethostuuid` may wait, in seconds: one of zero would wait for good.
_HOSTUUID_WAIT = 2


def _errno_text() -> str:
    return os.strerror(ctypes.get_errno())


class Darwin:
    """macOS: the platform's UUID, the boot's session UUID, and the kernel's process
    table through `sysctl`, which a command inside the harness's sandbox reads too.
    macOS has no process namespaces."""

    platform = "darwin"

    def __init__(self) -> None:
        self._libc: Any = None

    def _c(self) -> Any:
        if self._libc is None:
            self._libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.dylib", use_errno=True)
        return self._libc

    def _sysctl_named(self, name: str) -> tuple[bytes | None, str | None]:
        libc = self._c()
        size = ctypes.c_size_t(0)
        if libc.sysctlbyname(name.encode("ascii"), None, ctypes.byref(size), None, 0) != 0:
            return None, _errno_text()
        buffer = ctypes.create_string_buffer(max(size.value, 1))
        if libc.sysctlbyname(name.encode("ascii"), buffer, ctypes.byref(size), None, 0) != 0:
            return None, _errno_text()
        return buffer.raw[: size.value], None

    def _machine(self) -> tuple[str | None, str | None]:
        buffer = ctypes.create_string_buffer(16)
        wait = (ctypes.c_long * 2)(_HOSTUUID_WAIT, 0)
        if self._c().gethostuuid(buffer, wait) != 0:
            return None, f"the platform's UUID: {_errno_text()}"
        return str(uuid.UUID(bytes=buffer.raw)), None

    def _boot(self) -> tuple[str | None, str | None]:
        raw, why = self._sysctl_named("kern.bootsessionuuid")
        if raw is None:
            return None, f"kern.bootsessionuuid: {why}"
        text = raw.rstrip(b"\0").decode("ascii", errors="replace").strip()
        return (text, None) if text else (None, "kern.bootsessionuuid reads as empty")

    def _not_virtual(self) -> bool:
        raw, _ = self._sysctl_named("kern.hv_vmm_present")
        return raw is not None and len(raw) >= 4 and struct.unpack_from("=i", raw, 0)[0] == 0

    def space(self) -> RawSpace:
        try:
            machine, machine_why = self._machine()
            boot, boot_why = self._boot()
            unique = machine is not None and self._not_virtual()
        except (OSError, AttributeError) as exc:
            return RawSpace(None, None, None, False, False, f"libc: {type(exc).__name__}")
        return RawSpace(
            machine, boot, None, False, unique, "; ".join(w for w in (machine_why, boot_why) if w)
        )

    def entry(self, pid: int) -> Entry:
        if not 1 <= pid <= MAX_PID:
            return Entry(None, why=f"{pid} is no process id")
        try:
            libc = self._c()
            mib = (ctypes.c_int * 4)(_CTL_KERN, _KERN_PROC, _KERN_PROC_PID, pid)
            size = ctypes.c_size_t(0)
            if libc.sysctl(mib, 4, None, ctypes.byref(size), None, 0) != 0:
                return Entry(None, why=f"sysctl: {_errno_text()}")
            buffer = ctypes.create_string_buffer(max(size.value, 1))
            if libc.sysctl(mib, 4, buffer, ctypes.byref(size), None, 0) != 0:
                return Entry(None, why=f"sysctl: {_errno_text()}")
        except (OSError, AttributeError) as exc:
            return Entry(None, why=f"sysctl could not be called ({type(exc).__name__})")
        raw = buffer.raw[: size.value]
        if not raw:
            return Entry(False)
        short = len(raw) < _KINFO_PID_OFFSET + 4
        if short or struct.unpack_from("=i", raw, _KINFO_PID_OFFSET)[0] != pid:
            return Entry(None, why="the process table's entry has a layout pkit does not know")
        seconds, micros = struct.unpack_from("=qi", raw, 0)
        return Entry(True, f"{seconds}.{micros:06d}", raw[_KINFO_STAT_OFFSET] == _MACOS_ZOMBIE)

    def signal(self, pid: int) -> str:
        return null_signal(pid)


#: Where Linux keeps what a name holds. A process's `stat` holds, after its
#: command's name in parentheses, its state (field 3) and its start time in clock
#: ticks after the boot (field 22), which the kernel fixes when it makes it.
_LINUX_MACHINE = (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id"))
_LINUX_STATE_FIELD, _LINUX_START_FIELD = 3, 22
_LINUX_EXITED = frozenset({"Z", "X", "x"})


class Linux:
    """Linux: the machine's id, the boot's id, the reader's process namespace, and
    each process's `stat` under `/proc`. The machine's id is copied with a disk
    image, so it is never read as naming one machine."""

    platform = "linux"

    def __init__(self, proc: Path = Path("/proc")) -> None:
        self._proc = proc

    def space(self) -> RawSpace:
        whys: list[str] = []
        machine = None
        for path in _LINUX_MACHINE:
            machine = _text(path)
            if machine is not None:
                break
        if machine is None:
            whys.append("the machine's id reads nowhere")
        boot = _text(self._proc / "sys/kernel/random/boot_id")
        if boot is None:
            whys.append("the boot's id does not read")
        try:
            namespace: str | None = os.readlink(self._proc / "self/ns/pid")
        except OSError as exc:
            namespace = None
            whys.append(f"the process namespace: {exc.strerror or type(exc).__name__}")
        return RawSpace(machine, boot, namespace, True, False, "; ".join(whys) or None)

    def entry(self, pid: int) -> Entry:
        if not 1 <= pid <= MAX_PID:
            return Entry(None, why=f"{pid} is no process id")
        try:
            text = (self._proc / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return Entry(False)
        except OSError as exc:
            return Entry(None, why=f"its stat: {exc.strerror or type(exc).__name__}")
        fields = text.rpartition(")")[2].split()
        state, start = _LINUX_STATE_FIELD - 3, _LINUX_START_FIELD - 3
        if len(fields) <= start or not fields[start].isdigit():
            return Entry(None, why="its stat has a layout pkit does not know")
        return Entry(True, fields[start], fields[state] in _LINUX_EXITED)

    def signal(self, pid: int) -> str:
        return null_signal(pid)


class Unknown:
    """A platform this module reads no process space on, so every answer is
    *cannot tell*."""

    def __init__(self, platform: str) -> None:
        self.platform = platform

    def space(self) -> RawSpace:
        why = f"pkit reads no process space on {self.platform}"
        return RawSpace(None, None, None, False, False, why)

    def entry(self, pid: int) -> Entry:
        return Entry(None, why=f"pkit reads no process table on {self.platform}")

    def signal(self, pid: int) -> str:
        return null_signal(pid)


def _text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def this_system() -> System:
    """The operating system this command runs on."""
    if sys.platform == "darwin":
        return Darwin()
    if sys.platform.startswith("linux"):
        return Linux()
    return Unknown(sys.platform)


# ---- the process space, derived for the repository -----------------------------------------


@dataclass(frozen=True)
class Space:
    """A process space in a name's form: each part a digest derived for the
    repository, the namespace ``-`` where the platform has none, and each part None
    where it could not be read."""

    machine: str | None
    boot: str | None
    namespace: str | None
    unique_machine: bool = False
    why: str | None = None

    @property
    def whole(self) -> bool:
        return self.machine is not None and self.boot is not None and self.namespace is not None


def repository(root: Path) -> str | None:
    """The repository's identity a space is derived for: its `origin` remote, in the
    one form every clone of it reads (ADR-103 point 2). None where it has none."""
    from project_kit.session_guard import normalize_origin_url

    try:
        answer = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = answer.stdout.strip() if answer.returncode == 0 else ""
    return normalize_origin_url(text) if text else None


def digest(repository_id: str, part: str, value: str) -> str:
    """One part of a space, derived for the repository with no key: the same in
    every clone of it, and telling nothing that stays the same across another's
    repositories."""
    text = f"pkit-process-space/1\0{repository_id}\0{part}\0{value}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def space_of(raw: RawSpace, repository_id: str | None) -> Space:
    """``raw`` in a name's form, derived for ``repository_id``. With no repository,
    no part is derived, so the space is not whole."""
    if repository_id is None:
        why = "the repository has no `origin` remote to derive a process space for"
        return Space(None, None, None, False, why)

    def part(name: str, value: str | None) -> str | None:
        return digest(repository_id, name, value) if value is not None else None

    namespace = part("namespace", raw.namespace) if raw.namespaces else NO_NAMESPACES
    return Space(
        part("machine", raw.machine),
        part("boot", raw.boot),
        namespace,
        raw.unique_machine and raw.machine is not None,
        raw.why,
    )


# ---- names ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Name:
    """A process as a name holds it: its space, its id and, where it was read, its
    start time."""

    space: Space
    pid: int
    start: str | None

    def text(self) -> str:
        parts = (self.space.machine, self.space.boot, self.space.namespace)
        space = ":".join(p or "" for p in parts)
        return f"{FORM}:{space}:{self.pid}:{self.start or ''}"


def parse(text: object) -> Name | None:
    """The name ``text`` holds, or None where it is no name of a form this module
    reads. A part left empty reads as None."""
    if not isinstance(text, str):
        return None
    fields = text.split(":")
    if len(fields) != 6 or fields[0] not in FORMS:
        return None
    _, machine, boot, namespace, pid, start = fields
    if machine and not _DIGEST.fullmatch(machine):
        return None
    if boot and not _DIGEST.fullmatch(boot):
        return None
    if namespace and namespace != NO_NAMESPACES and not _DIGEST.fullmatch(namespace):
        return None
    if not _PID.fullmatch(pid) or int(pid) > MAX_PID:
        return None
    if start and not _START.fullmatch(start):
        return None
    return Name(Space(machine or None, boot or None, namespace or None), int(pid), start or None)


@dataclass(frozen=True)
class Reader:
    """The command that asks: the process space it runs in, the platform, whether
    the adapter's declaration names that platform for a reading by the id alone,
    and the process of the session it runs in, as the declaration names it."""

    space: Space
    platform: str
    id_alone: bool = False
    session_pid: int | None = None


@dataclass(frozen=True)
class Named:
    """A name :func:`name` wrote, or None with why it wrote none."""

    name: str | None
    why: str | None = None


def name(pid: int, reader: Reader, system: System) -> Named:
    """Name the process ``pid`` as this command reads it (ADR-103 point 2): its space,
    its id and its start time where the table gives one. No name where this command
    cannot read its own space whole, or no process holds the id."""
    if not 1 <= pid <= MAX_PID:
        return Named(None, f"{pid} is no process id")
    if not reader.space.whole:
        return Named(None, f"this command cannot read its own process space: {reader.space.why}")
    entry = system.entry(pid)
    if entry.found is False:
        return Named(None, f"no process holds the id {pid}")
    if entry.found and entry.exited:
        return Named(None, f"process {pid} has exited")
    start = entry.start if entry.found else None
    if not entry.found and system.signal(pid) != FOUND:
        return Named(None, f"process {pid} could not be read: {entry.why}")
    return Named(Name(reader.space, pid, start).text())


# ---- reading -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    """Whether the process a name names runs: RUNNING, ENDED or CANNOT_TELL; the
    reading that told, None for CANNOT_TELL; and why, for people."""

    name: object
    state: str
    by: str | None
    why: str

    def document(self) -> dict[str, Any]:
        return {"name": self.name, "state": self.state, "by": self.by, "why": self.why}


def read(names: Iterable[object], reader: Reader, system: System) -> list[Answer]:
    """Whether each process ``names`` names runs, as this command reads it (ADR-103
    points 1, 3 and 4), one answer for each, in their order."""
    return [_read_one(text, reader, system) for text in names]


def _read_one(text: object, reader: Reader, system: System) -> Answer:
    def cannot(why: str) -> Answer:
        return Answer(text, CANNOT_TELL, None, why)

    own = reader.space
    if not own.whole:
        return cannot(f"this command cannot read its own process space: {own.why}")
    recorded = parse(text)
    if recorded is None:
        return cannot("it is no process name of a form pkit reads")
    space = recorded.space
    if not space.whole:
        return cannot("the name holds no whole process space")
    pid = recorded.pid
    if (space.machine, space.boot, space.namespace) != (own.machine, own.boot, own.namespace):
        if space.machine == own.machine and space.boot != own.boot:
            if own.unique_machine:
                return Answer(text, ENDED, BY_EARLIER_BOOT, "it ran before this machine restarted")
            return cannot(
                "it ran in another boot of a machine whose identity this platform may "
                "share with another machine"
            )
        return cannot("it was recorded in another process space")
    entry = system.entry(pid)
    if entry.found is False:
        return Answer(text, ENDED, BY_START_TIME, f"no process holds the id {pid}")
    if entry.found and entry.start is not None and recorded.start is not None:
        if entry.start != recorded.start:
            why = f"the process under the id {pid} started at another time"
            return Answer(text, ENDED, BY_START_TIME, why)
        if entry.exited:
            return Answer(text, ENDED, BY_START_TIME, f"process {pid} has exited")
        return Answer(text, RUNNING, BY_START_TIME, f"process {pid} started when it was named")
    if entry.found and entry.exited:
        return Answer(text, ENDED, BY_START_TIME, f"the process under the id {pid} has exited")
    unread = (
        "the name holds no start time"
        if recorded.start is None
        else f"the start time of process {pid} cannot be read here ({entry.why})"
    )
    return _by_id_alone(text, pid, unread, reader, system)


def _by_id_alone(text: object, pid: int, unread: str, reader: Reader, system: System) -> Answer:
    """ADR-103 point 4: by the id alone, only on a declared platform, and only once
    the same signal finds this command's own session's process."""
    if not reader.id_alone:
        return Answer(
            text,
            CANNOT_TELL,
            None,
            f"{unread}, and the adapter's declaration names no reading by the id alone on "
            f"{reader.platform}",
        )
    if reader.session_pid is None:
        return Answer(
            text, CANNOT_TELL, None, f"{unread}, and this command runs in no session to guard by"
        )
    if system.signal(reader.session_pid) != FOUND:
        return Answer(
            text,
            CANNOT_TELL,
            None,
            f"{unread}, and a null signal does not find this command's own session's process",
        )
    found = system.signal(pid)
    if found == FOUND:
        return Answer(text, RUNNING, BY_ID_ALONE, f"a process holds the id {pid}")
    if found == NONE:
        return Answer(text, ENDED, BY_ID_ALONE, f"no process holds the id {pid}")
    return Answer(text, CANNOT_TELL, None, f"{unread}, and a null signal to {pid} failed")


# ---- comparing -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Comparison:
    """ONE, TWO or CANNOT_TELL for two names, and why."""

    names: tuple[object, object]
    answer: str
    why: str

    def document(self) -> dict[str, Any]:
        return {"names": list(self.names), "answer": self.answer, "why": self.why}


def compare(left: object, right: object) -> Comparison:
    """Whether two names name one process: their spaces and ids are the same and,
    where both hold a start time, their start times are (ADR-103 point 3)."""
    pair = (left, right)
    a, b = parse(left), parse(right)
    if a is None or b is None:
        return Comparison(pair, CANNOT_TELL, "a name is of no form pkit reads")
    if not a.space.whole or not b.space.whole:
        return Comparison(pair, CANNOT_TELL, "a name holds no whole process space")
    same_space = (a.space.machine, a.space.boot, a.space.namespace) == (
        b.space.machine,
        b.space.boot,
        b.space.namespace,
    )
    if not same_space:
        return Comparison(pair, TWO, "they were named in two process spaces")
    if a.pid != b.pid:
        return Comparison(pair, TWO, "they hold two process ids")
    if a.start is not None and b.start is not None and a.start != b.start:
        return Comparison(pair, TWO, "they hold one id and two start times")
    return Comparison(pair, ONE, "they name one process")


# ---- the documents -------------------------------------------------------------------------

#: The version of the documents `pkit recorded-process` prints.
DOCUMENT_VERSION = 1


class FormError(ValueError):
    """A request that is not of the form a command reads."""


def _list(request: object, key: str) -> list[object]:
    if not isinstance(request, dict):
        raise FormError("the request is no JSON object")
    value = cast(dict[str, object], request).get(key, [])
    if not isinstance(value, list):
        raise FormError(f"`{key}` is no list")
    return cast(list[object], value)


def _names(values: list[object]) -> list[object]:
    if not all(isinstance(value, str) for value in values):
        raise FormError("each name is a string")
    return values


def read_document(request: object, reader: Reader, system: System) -> dict[str, Any]:
    """`pkit recorded-process read`'s document for ``request``: ``{"names": [...]}``."""
    names = _names(_list(request, "names"))
    answers = read(names, reader, system)
    return {"schema_version": DOCUMENT_VERSION, "answers": [a.document() for a in answers]}


def compare_document(request: object) -> dict[str, Any]:
    """`pkit recorded-process compare`'s document for ``request``:
    ``{"pairs": [[<name>, <name>], ...]}``."""
    pairs: list[Comparison] = []
    for pair in _list(request, "pairs"):
        if not isinstance(pair, list) or len(cast(list[object], pair)) != 2:
            raise FormError("each pair is a list of two names")
        left, right = _names(cast(list[object], pair))
        pairs.append(compare(left, right))
    return {"schema_version": DOCUMENT_VERSION, "pairs": [c.document() for c in pairs]}
