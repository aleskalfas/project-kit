"""A capability's own configuration: one key recorded in it as text (COR-049 point 5).

A capability keeps its settings in its own subtree (COR-048 point 2). The
configuration this module writes is `.pkit/capabilities/<capability>/project/config.yaml`,
bound to the capability's `config` schema — the pair `schemas/config.yaml` and
`schemas/config.schema.json` (COR-018), named as `pkit_schema: <capability>:config`
(COR-023). A command of the capability that chooses a value — a location, say —
records it there when it first uses it, and reads it from then on (COR-049
point 5). `plan` and `write` are the writer `pkit config record` runs; a
capability records such a key through that command rather than keep a writer of
its own:

- **Added once, never moved.** A key the file holds with the same value writes
  nothing; one it holds with another value, an empty one included, is refused:
  an explicit value always wins (COR-049 point 3), and only a person moves it.
  The binding keys are the writer's own, never recorded.
- **As text, every other byte kept.** The key's line goes in through the
  backbone's text edit of a YAML mapping (`yaml_splice`), which `pkit config set`
  writes through too: after the last key of the mapping that gets it, in that
  mapping's layout, with the mappings it needs. The comments, the order, the
  blank lines, the indentation and the file's one line break stay as written. A
  byte-order mark is taken off before the edit and put back after it, so the
  edit never reads it as text of the file's first line.
- **Read back, and checked.** The result must read back as the file plus that
  key, and must bring no error of the schema the file did not have; otherwise
  nothing is written. A file that names another schema, or a `schema_version`
  other than its schema's, is refused, since the schema cannot judge it.
- **An absent file is created bound to the schema**: the editor directive, then
  `pkit_schema` and `schema_version`, then the key. A file that holds no mapping
  yet gains the binding before the key. A schema that declares no version is
  refused there, since the binding would name none.

The value is text, written so that every YAML reader, 1.1 or 1.2, reads it back
as the same text (`_scalar`); a key's segments are words every reader reads as
that word. `plan` computes the result and writes nothing, so a dry run, or a
capability that must learn before its first write that it cannot record the
key, asks the same question the write answers. Consent is the command's to ask.
"""

from __future__ import annotations

import contextlib
import copy
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

import click
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from project_kit import data_validate, yaml_splice
from project_kit.docs_roots import BACKBONE
from project_kit.friction_discovery import installed_capability_names

#: Where installed capabilities live, relative to the repository root.
CAPABILITIES_RELPATH = PurePosixPath(".pkit") / "capabilities"

#: The schema of a capability's own configuration, among its schemas (COR-018).
CONFIG_SCHEMA = "config"

#: The editor directive stamped at the top of a configuration the writer
#: creates (COR-023), pointing at the schema relative to the file.
EDITOR_DIRECTIVE = f"# yaml-language-server: $schema=../schemas/{CONFIG_SCHEMA}.schema.json"

#: The binding keys a configuration names its schema with (COR-023): the
#: writer's own, never recorded.
SCHEMA_FIELD = data_validate.PKIT_SCHEMA_FIELD
VERSION_FIELD = "schema_version"
BINDING_FIELDS = (SCHEMA_FIELD, VERSION_FIELD)

#: The byte-order mark a file may open with, kept as it was.
BOM = "﻿"

#: A value written plain: it starts with a letter and holds nothing YAML gives a meaning.
_PLAIN = re.compile(r"[A-Za-z][A-Za-z0-9._/-]*")

#: A key's segment: a word that starts with a letter, every reader's key.
_SEGMENT = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")

#: The words a YAML reader takes for another value than text where they stand alone:
#: a yes-or-no in YAML 1.1 (`y`, `n`, `yes`, `no`, `on`, `off`) or in 1.2 too
#: (`true`, `false`), and nothing (`null`). A value is written quoted, in any case; a
#: key's segment is refused.
_YAML_WORDS = frozenset({"y", "n", "yes", "no", "on", "off", "true", "false", "null"})

Outcome = Literal["recorded", "recorded-already"]


class RecordRefused(click.ClickException):
    """The key cannot be recorded; nothing is written. The message says why and what to do."""


@dataclass(frozen=True)
class Recording:
    """What recording `key: value` in a capability's configuration makes of it.

    `before` is the file's bytes as they are, None where it is absent; `after` the
    bytes the write makes, None where the file records that value already."""

    capability: str
    key: str
    value: str
    path: Path
    relpath: str
    before: bytes | None
    after: bytes | None

    @property
    def outcome(self) -> Outcome:
        return "recorded-already" if self.after is None else "recorded"

    def line(self) -> str:
        """`<capability> <key> = <value>  (<file>)`: what a notice names."""
        return f"{self.capability} {self.key} = {self.value}  ({self.relpath})"


def config_relpath(capability: str) -> PurePosixPath:
    """A capability's own configuration, relative to the repository root."""
    return CAPABILITIES_RELPATH / capability / "project" / "config.yaml"


def plan(target_root: Path, capability: str, key: str, value: str) -> Recording:
    """What recording `key` (dotted) as `value` makes of `capability`'s configuration,
    written nowhere. Raises RecordRefused where it cannot be recorded."""
    _refuse_unless_installed(target_root, capability)
    relpath = config_relpath(capability).as_posix()
    path = target_root / relpath
    segments = _segments(key)
    if not value:
        raise RecordRefused("a recording records a value: VALUE is empty")
    binding = _binding(target_root, capability, path)
    _refuse_links(target_root, path, relpath)
    before = _read(path, relpath)
    existing = _decode(before, relpath) if before is not None else None
    bom = BOM if existing is not None and existing.startswith(BOM) else ""
    text = existing[len(bom) :] if existing is not None else f"{EDITOR_DIRECTIVE}\n"
    was = _load(text, relpath)
    _refuse_another_binding(was, binding, relpath)
    recording = Recording(capability, ".".join(segments), value, path, relpath, before, None)
    held = _held(was, segments, relpath)
    if held is not _ABSENT:
        if held == value:
            return recording
        shown = "an empty value" if held is None else f"`{held}`"
        raise RecordRefused(
            f"{relpath} records {shown} at `{recording.key}` already; a recording never moves "
            f"it. To change it, change that line by hand"
        )
    wanted = _wanted(was, segments, _scalar(value), binding)
    try:
        written = yaml_splice.splice(text, wanted)
    except yaml_splice.SpliceRefused as exc:
        raise RecordRefused(
            f"{relpath} would not read back as it is plus `{recording.key}`: {exc}. Nothing was "
            f"written; add `{recording.key}: {value}` there by hand"
        ) from exc
    _refuse_new_errors(target_root, binding, was if before is not None else None, wanted, relpath)
    return replace(recording, after=(bom + written).encode("utf-8"))


def write(recording: Recording) -> None:
    """Write what `recording` makes, atomically and byte for byte; nothing where the
    file records the value already."""
    if recording.after is None:
        return
    path = recording.path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    except OSError as exc:
        raise RecordRefused(f"{recording.relpath} could not be written: {exc}") from exc
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(recording.after)
        os.replace(temporary, path)
    except OSError as exc:
        raise RecordRefused(f"{recording.relpath} could not be written: {exc}") from exc
    finally:
        with contextlib.suppress(OSError):
            Path(temporary).unlink(missing_ok=True)


# --- what the writer finds ---------------------------------------------------------


def _refuse_unless_installed(target_root: Path, capability: str) -> None:
    if capability == BACKBONE:
        raise RecordRefused(
            "the backbone's own configuration, .pkit/project/config.yaml, is set with "
            "`pkit config set <key> <value>`"
        )
    if capability not in installed_capability_names(target_root):
        if (target_root / ".pkit" / "adapters" / capability).is_dir():
            raise RecordRefused(
                f"{capability!r} is an adapter; an adapter keeps no configuration of its own"
            )
        raise RecordRefused(f"no capability named {capability!r} is installed")


def _segments(key: str) -> tuple[str, ...]:
    """The key's segments: words every YAML reader reads as that word, none the binding's."""
    segments = tuple(key.split("."))
    if not key or any(not segment for segment in segments):
        raise RecordRefused(f"key {key!r} is not a dotted path of non-empty segments")
    for segment in segments:
        if not _SEGMENT.fullmatch(segment) or segment.lower() in _YAML_WORDS:
            raise RecordRefused(
                f"key {key!r}: the segment {segment!r} is no word every YAML reader reads as "
                f"that word — one starts with a letter, holds letters, digits, `-` and `_`, "
                f"and is none of {', '.join(sorted(_YAML_WORDS))}. Write that key by hand"
            )
    if segments[0] in BINDING_FIELDS:
        raise RecordRefused(
            f"`{segments[0]}` binds the configuration to its schema (COR-023): the writer "
            f"writes it with a file it creates, and no recording does"
        )
    return segments


def _binding(target_root: Path, capability: str, path: Path) -> data_validate.ResolvedBinding:
    """The capability's configuration schema (COR-018, COR-023)."""
    found = data_validate.bind(path, target_root, capability, CONFIG_SCHEMA)
    if isinstance(found, data_validate.BindingError):
        raise RecordRefused(
            f"{capability} ships no configuration schema (`schemas/{CONFIG_SCHEMA}.yaml` and "
            f"`schemas/{CONFIG_SCHEMA}.schema.json`), so it keeps no configuration of its own "
            f"to record a key in"
        )
    return found


def _refuse_links(target_root: Path, path: Path, relpath: str) -> None:
    """A file reached through a link is refused: a whole-file write would replace the link."""
    for step in (path, *path.parents):
        if step == target_root:
            return
        if step.is_symlink():
            raise RecordRefused(
                f"{relpath} is reached through the link {step.relative_to(target_root).as_posix()}"
                f", which a whole-file write would replace: add the key where the file lies, "
                f"by hand"
            )


def _read(path: Path, relpath: str) -> bytes | None:
    """The file's bytes, or None where it is absent."""
    if not path.exists():
        return None
    try:
        return path.read_bytes()
    except OSError as exc:
        raise RecordRefused(f"{relpath} cannot be read: {exc}") from exc


def _decode(data: bytes, relpath: str) -> str:
    """The file's text as written: its line breaks unread, a byte-order mark kept."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RecordRefused(f"{relpath} cannot be read as UTF-8: {exc}") from exc


def _load(text: str, relpath: str) -> dict[str, Any]:
    """The file's mapping as plain data; empty where it holds nothing yet."""
    try:
        data = cast(Any, YAML()).load(text)
    except YAMLError as exc:
        raise RecordRefused(
            f"{relpath} does not parse as YAML ({str(exc).splitlines()[0]}); fix it first"
        ) from exc
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise RecordRefused(f"{relpath} is not a mapping of keys to values; fix it first")
    return cast(dict[str, Any], yaml_splice.plain(data))


def _refuse_another_binding(
    was: Mapping[str, Any], binding: data_validate.ResolvedBinding, relpath: str
) -> None:
    """Refuse a file its schema cannot judge: one that names another schema, or another
    version of it — a file a migration has not carried over yet (COR-023)."""
    named = f"{binding.capability}:{binding.schema_name}"
    declared = was.get(SCHEMA_FIELD)
    if declared is not None and declared != named:
        raise RecordRefused(
            f"{relpath} names the schema `{declared}`, not `{named}`, so it is no "
            f"configuration of {binding.capability} the writer can check; fix that line first"
        )
    version = was.get(VERSION_FIELD)
    current = data_validate.schema_version_of(binding)
    if version is not None and current is not None and version != current:
        raise RecordRefused(
            f"{relpath} declares `{VERSION_FIELD}: {version}`, and {named} is at {current}: "
            f"the file is in a format its migration has not carried over yet (COR-023). Run "
            f"`pkit upgrade` or the capability's migration, then record again"
        )


#: A key the file does not hold.
_ABSENT: Any = object()


def _held(data: Mapping[str, Any], segments: tuple[str, ...], relpath: str) -> Any:
    """The value the file holds at `segments`, `_ABSENT` where it holds none. Refused
    where a mapping on the way holds anything but a mapping."""
    node: Any = data
    for depth, segment in enumerate(segments[:-1]):
        node = cast(Mapping[str, Any], node).get(segment, _ABSENT)
        if node is _ABSENT:
            return _ABSENT
        if not isinstance(node, Mapping):
            at = ".".join(segments[: depth + 1])
            if node is None:
                raise RecordRefused(
                    f"{relpath} holds an empty value at `{at}`, not a mapping, so "
                    f"`{'.'.join(segments)}` cannot go under it. Give `{at}` the empty mapping "
                    f"`{{}}` and record again, or add the key under it by hand"
                )
            raise RecordRefused(
                f"{relpath} holds a value at `{at}`, not a mapping, so `{'.'.join(segments)}` "
                f"cannot go under it; fix that line first"
            )
    return cast(Mapping[str, Any], node).get(segments[-1], _ABSENT)


def _wanted(
    was: Mapping[str, Any],
    segments: tuple[str, ...],
    value: str,
    binding: data_validate.ResolvedBinding,
) -> dict[str, Any]:
    """The file's mapping plus the key; a mapping that holds nothing yet gains the
    binding first."""
    wanted: dict[str, Any] = (
        copy.deepcopy(dict(was))
        if was
        else {
            SCHEMA_FIELD: f"{binding.capability}:{binding.schema_name}",
            VERSION_FIELD: _schema_version(binding),
        }
    )
    node = wanted
    for segment in segments[:-1]:
        node = node.setdefault(segment, {})
    node[segments[-1]] = value
    return wanted


def _schema_version(binding: data_validate.ResolvedBinding) -> int:
    """The `schema_version` the binding of a file the writer stamps names: the version of
    the schema the file is written against (COR-023). Refused where the schema's YAML
    declares none, since the binding would then name no version."""
    version = data_validate.schema_version_of(binding)
    if version is None:
        raise RecordRefused(
            f"{binding.capability}'s `schemas/{binding.schema_name}.yaml` declares no "
            f"whole-number `{VERSION_FIELD}`, which a file bound to it names (COR-023), so "
            f"the writer cannot bind a file to it. Nothing was written; the schema is to "
            f"declare its version first"
        )
    return version


def _scalar(value: str) -> str:
    """`value` as the edit writes it: plain where every YAML reader, 1.1 or 1.2, reads it
    back as the same text, else double-quoted."""
    if _PLAIN.fullmatch(value) and value.lower() not in _YAML_WORDS:
        return value
    return DoubleQuotedScalarString(value)


# --- the schema's judgement ----------------------------------------------------------


def _refuse_new_errors(
    target_root: Path,
    binding: data_validate.ResolvedBinding,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any],
    relpath: str,
) -> None:
    """Refuse a result with an error of the schema the file did not have before. An
    error is told from another by its location and the schema keyword it breaks, never
    by its message, which names what the data holds: so an error the file already had
    stays the same error once the key is in, and is left for the file's owner to mend."""
    had: set[tuple[str, str | None]] = set()
    if before is not None:
        had = {_key(issue) for issue in _errors(target_root, binding, before)}
    new = [i for i in _errors(target_root, binding, after) if _key(i) not in had]
    if not new:
        return
    lines = [
        f"refusing to write {relpath}: the result would not validate against "
        f"{binding.capability}:{binding.schema_name}. Nothing was written."
    ]
    lines.extend(f"  {issue.location}: {issue.message}" for issue in new)
    raise RecordRefused("\n".join(lines))


def _errors(
    target_root: Path, binding: data_validate.ResolvedBinding, data: Mapping[str, Any]
) -> list[data_validate.DataValidationIssue]:
    issues = data_validate.validate_data(_text_values(data), binding, target_root)
    return [issue for issue in issues if issue.severity == "error"]


def _text_values(data: Any) -> Any:
    """`data` with every string a plain `str`, as a reader of the file sees it."""
    if isinstance(data, Mapping):
        return {str(k): _text_values(v) for k, v in cast(Mapping[Any, Any], data).items()}
    if isinstance(data, list):
        return [_text_values(item) for item in cast(list[Any], data)]
    if isinstance(data, str):
        return str(data)
    return data


def _key(issue: data_validate.DataValidationIssue) -> tuple[str, str | None]:
    return issue.location, issue.check
