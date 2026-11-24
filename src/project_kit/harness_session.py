"""The harness session whose shell runs a command, as the project's adapter
declares it (ADR-100 point 9, ADR-103 point 5).

An adapter declares, in `session.yaml` in its folder, how a command finds the
session whose shell runs it and that session's process, the messaging address
the harness gives the session, how a message's reply address is brought into
that address's form, how the harness names an address after the session's
process, and the platforms where a null signal was measured to tell a running
process id from a free one. The backbone reads it as data, running none of the
adapter's code, so a command of a capability learns the session from here and
names no harness.

- :func:`declaration` finds the one declaration among the adapters the backbone
  manifest registers.
- :func:`read` reads the session: its process, named by the backbone
  (`recorded_processes`), only once a process with the declared id runs in this
  command's process space and a null signal finds it there, and its messaging
  address only where it names that process as the declaration says (ADR-103
  point 5).
- :func:`reply` brings a message's reply address into the address's form.
- :func:`reader` gives `recorded_processes` the command that asks: its process
  space, whether the declaration names its platform for a reading by the id
  alone, and its session's process for that reading's guard (ADR-103 point 4).

A command that finds a session runs on the agent's call, whatever these checks
find (ADR-103 point 5, "The agent's call stands"). The declaration lies in the
checkout, which a sandboxed command can write: a guard, not a boundary
(ADR-100 point 9).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import recorded_processes as rp

#: The declaration's file in an adapter's folder, and the version it is read in.
DECLARATION = "session.yaml"
VERSION = 1

#: The keys a declaration holds, and those of its two parts.
_KEYS = frozenset({"schema_version", "process", "messaging", "id_alone_platforms"})
_PROCESS_KEYS = frozenset({"variable"})
_MESSAGING_KEYS = frozenset({"variable", "reply_prefix", "names_process"})
_VARIABLE = re.compile(r"[A-Z_][A-Z0-9_]*")
_PLATFORM = re.compile(r"[a-z][a-z0-9]*")
_PID = re.compile(r"[1-9][0-9]{0,9}")

_yaml: Any = YAML(typ="safe")


class DeclarationError(ValueError):
    """A declaration that cannot be read, or is not of the form this module reads."""


@dataclass(frozen=True)
class Declaration:
    """One adapter's declaration of a session.

    ``process_variable`` is the environment variable that holds the session's
    process id in a command its shell runs. ``address_variable`` holds its
    messaging address, ``reply_prefix`` is what a message's reply address carries
    before that address, and ``names_process`` a pattern that matches the whole
    address and names the session's process id in its group ``pid``. Each is None
    where the harness gives no messaging. ``id_alone_platforms`` are the platforms,
    as Python names them, where a process may be read by its id alone."""

    adapter: str
    process_variable: str
    address_variable: str | None = None
    reply_prefix: str | None = None
    names_process: re.Pattern[str] | None = None
    id_alone_platforms: tuple[str, ...] = ()


def path(root: Path, adapter: str) -> Path:
    """Where ``adapter`` keeps its declaration of a session."""
    return root / ".pkit" / "adapters" / adapter / DECLARATION


def parse(adapter: str, document: object) -> Declaration:
    """The declaration ``document`` holds for ``adapter``. Raises
    :class:`DeclarationError` on a version, a key or a value it does not read."""
    if not isinstance(document, Mapping):
        raise DeclarationError("it is no mapping")
    fields = cast(Mapping[str, object], document)
    if fields.get("schema_version") != VERSION:
        raise DeclarationError(
            f"`schema_version` is {fields.get('schema_version')!r}, and pkit reads {VERSION}"
        )
    _known(fields, _KEYS, "the declaration")
    process = _mapping(fields.get("process"), "`process`")
    _known(process, _PROCESS_KEYS, "`process`")
    process_variable = _variable(process.get("variable"), "`process.variable`")
    if process_variable is None:
        raise DeclarationError("`process.variable` is needed")
    messaging_given = fields.get("messaging")
    address_variable = reply_prefix = None
    names_process: re.Pattern[str] | None = None
    if messaging_given is not None:
        messaging = _mapping(messaging_given, "`messaging`")
        _known(messaging, _MESSAGING_KEYS, "`messaging`")
        address_variable = _variable(messaging.get("variable"), "`messaging.variable`")
        prefix = messaging.get("reply_prefix", "")
        if not isinstance(prefix, str):
            raise DeclarationError("`messaging.reply_prefix` is no string")
        reply_prefix = prefix
        pattern = messaging.get("names_process")
        if not isinstance(pattern, str):
            raise DeclarationError("`messaging.names_process` is needed, as a string")
        try:
            names_process = re.compile(pattern)
        except re.error as exc:
            raise DeclarationError(f"`messaging.names_process` is no pattern: {exc}") from exc
        if "pid" not in names_process.groupindex:
            raise DeclarationError("`messaging.names_process` names no group `pid`")
        if address_variable is None:
            raise DeclarationError("`messaging.variable` is needed")
    platforms = fields.get("id_alone_platforms", [])
    if not isinstance(platforms, list):
        raise DeclarationError("`id_alone_platforms` is no list")
    listed = cast(list[object], platforms)
    for platform in listed:
        if not isinstance(platform, str) or not _PLATFORM.fullmatch(platform):
            raise DeclarationError(f"`id_alone_platforms` holds {platform!r}, no platform's name")
    return Declaration(
        adapter,
        process_variable,
        address_variable,
        reply_prefix,
        names_process,
        tuple(cast(list[str], listed)),
    )


def _known(fields: Mapping[str, object], keys: frozenset[str], where: str) -> None:
    unknown = sorted(set(fields) - keys)
    if unknown:
        raise DeclarationError(f"{where} holds keys pkit does not read: {', '.join(unknown)}")


def _mapping(value: object, where: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DeclarationError(f"{where} is no mapping")
    return cast(Mapping[str, object], value)


def _variable(value: object, where: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _VARIABLE.fullmatch(value):
        raise DeclarationError(f"{where} is no environment variable's name")
    return value


@dataclass(frozen=True)
class Found:
    """The one declaration of a session among the registered adapters, or None with
    why."""

    declaration: Declaration | None
    why: str | None = None


def declaration(root: Path) -> Found:
    """The declaration of a session of the one registered adapter that ships one.
    None where no registered adapter declares one, where more than one does, since
    no record says which harness the project names, or where it cannot be read."""
    from project_kit import harness_support

    found: list[tuple[str, Path]] = []
    for adapter in harness_support.registered_adapters(root):
        if not harness_support.is_adapter(root, adapter):
            continue
        where = path(root, adapter)
        if where.is_file():
            found.append((adapter, where))
    if not found:
        return Found(None, "no registered adapter declares how a command finds its session")
    if len(found) > 1:
        names = ", ".join(adapter for adapter, _ in found)
        return Found(
            None,
            f"more than one registered adapter declares a session ({names}), and no record "
            "says which harness the project names",
        )
    adapter, where = found[0]
    try:
        return Found(parse(adapter, _yaml.load(where.read_text(encoding="utf-8"))))
    except (OSError, YAMLError, DeclarationError) as exc:
        return Found(None, f"{where.relative_to(root).as_posix()} cannot be read: {exc}")


# ---- the session ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Session:
    """The session whose shell runs a command, as its adapter declares it.

    ``found`` says whether a session runs this command, and ``why`` why not.
    ``messaging`` says whether the adapter declares messaging between sessions.
    ``process`` is the name the backbone gives its process, and ``address`` its
    messaging address, each None with why."""

    adapter: str | None
    found: bool
    why: str | None = None
    messaging: bool = False
    pid: int | None = None
    process: str | None = None
    process_why: str | None = None
    address: str | None = None
    address_why: str | None = None
    replies: tuple[Reply, ...] = field(default=())

    def document(self) -> dict[str, Any]:
        return {
            "schema_version": VERSION,
            "adapter": self.adapter,
            "found": self.found,
            "why": self.why,
            "messaging": self.messaging,
            "process": self.process,
            "process_why": self.process_why,
            "address": self.address,
            "address_why": self.address_why,
            "replies": [r.document() for r in self.replies],
        }


@dataclass(frozen=True)
class Reply:
    """A message's reply address as given, in the form of a session's messaging
    address, or None with why."""

    given: str
    address: str | None
    why: str | None = None

    def document(self) -> dict[str, Any]:
        return {"given": self.given, "address": self.address, "why": self.why}


def reply(found: Found, given: str) -> Reply:
    """``given``, a message's reply address, in the form of a session's messaging
    address, as the declaration says it is brought into it."""
    declared = found.declaration
    if declared is None:
        return Reply(given, None, found.why)
    if declared.reply_prefix is None:
        return Reply(given, None, f"the adapter {declared.adapter} declares no messaging")
    if not given.startswith(declared.reply_prefix):
        return Reply(given, None, "it does not carry the form the adapter declares")
    address = given[len(declared.reply_prefix) :]
    if declared.names_process is None or not declared.names_process.fullmatch(address):
        return Reply(given, None, "it names no session's process as the adapter declares")
    return Reply(given, address)


def session_pid(found: Found, env: Mapping[str, str]) -> int | None:
    """The process id the declaration's variable names in ``env``, or None."""
    declared = found.declaration
    if declared is None:
        return None
    value = env.get(declared.process_variable, "").strip()
    return int(value) if _PID.fullmatch(value) and int(value) <= rp.MAX_PID else None


def reader(root: Path, found: Found, env: Mapping[str, str], system: rp.System) -> rp.Reader:
    """The command that asks, for `recorded_processes`: its process space, derived
    for the repository; whether the declaration names its platform for a reading
    by the id alone; and its session's process, which that reading signals first."""
    space = rp.space_of(system.space(), rp.repository(root))
    declared = found.declaration
    id_alone = declared is not None and system.platform in declared.id_alone_platforms
    return rp.Reader(space, system.platform, id_alone, session_pid(found, env))


def read(
    root: Path,
    env: Mapping[str, str],
    system: rp.System,
    *,
    replies: tuple[str, ...] = (),
) -> Session:
    """The session whose shell runs this command, as the adapter declares it, and each
    of ``replies`` in its address's form."""
    found = declaration(root)
    given = tuple(reply(found, r) for r in replies)
    declared = found.declaration
    if declared is None:
        return Session(None, False, found.why, replies=given)
    messaging = declared.address_variable is not None
    pid = session_pid(found, env)
    if pid is None:
        return Session(
            declared.adapter,
            False,
            f"`{declared.process_variable}` names no process: no session of the adapter "
            f"{declared.adapter} runs this command",
            messaging,
            replies=given,
        )
    asking = reader(root, found, env, system)
    confirmed = system.signal(pid) == rp.FOUND
    process: str | None = None
    if not confirmed:
        process_why = f"a null signal finds no process {pid} in this command's process space"
    else:
        named = rp.name(pid, asking, system)
        process, process_why = named.name, named.why
    address, address_why = _address(declared, env, pid, confirmed)
    return Session(
        declared.adapter,
        True,
        None,
        messaging,
        pid,
        process,
        process_why,
        address,
        address_why,
        given,
    )


def _address(
    declared: Declaration, env: Mapping[str, str], pid: int, confirmed: bool
) -> tuple[str | None, str | None]:
    """The session's messaging address where it names the session's process ``pid``
    as the declaration says, and a null signal found that process, else None with
    why (ADR-103 point 5)."""
    if declared.address_variable is None or declared.names_process is None:
        return None, f"the adapter {declared.adapter} declares no messaging"
    value = env.get(declared.address_variable, "").strip()
    if not value:
        return None, f"`{declared.address_variable}` names no messaging address"
    match = declared.names_process.fullmatch(value)
    if match is None or match.group("pid") != str(pid):
        return None, "the messaging address does not name the session's process"
    if not confirmed:
        return None, "the session's process is not found in this command's process space"
    return value, None
