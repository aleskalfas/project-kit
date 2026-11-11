"""The capability's project configuration, written as text with every other byte kept
(DEC-002 point 2; COR-049 point 5).

A command records a key, such as the location, the first time it needs it. The line goes
in as text at the end of the file, so its comments, its order, its line endings and a
byte-order mark all stay. The file must read back as it was plus that key, or nothing is
written. An absent file is created, bound to the configuration's schema. The command
writes the text as a step of its change (`files.Change`), so a write of the run that
fails takes the key back out.

Copied in substance from living-docs' `_lib/stamp.py` (`_config_text`, `_inserted`,
`_crlf`): a capability cannot import the backbone's splice, nor another capability's code.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from _lib.files import FORMAT, FileError, refuse_links, schema_of
from _lib.names import YAML_WORDS
from _lib.reading import ReadError, load_yaml
from _lib.root import CONFIG

#: A value that may be written plain: it starts with a letter, so no YAML reads it as a
#: number, and holds nothing YAML gives a meaning.
_PLAIN = re.compile(r"[A-Za-z][A-Za-z0-9._/-]*")


class ConfigRefused(Exception):
    """The configuration cannot take the key as text, or cannot be read."""


def with_key(existing: str | None, key: str, value: str) -> str:
    """The configuration's text with the top-level `key: value` added at its end, every
    other byte kept, its line endings and a byte-order mark included; a new file, bound to
    the configuration's schema, when `existing` is None. Unchanged when the file records
    that value already. Raises ConfigRefused when it records another value, holds the key
    with no value, or would not read back as it was plus the key."""
    line = f"{key}: {scalar(value)}\n"
    binding = f"pkit_schema: {schema_of('config')}\nschema_version: {FORMAT}\n"
    if existing is None:
        return f"{binding}\n{line}"
    bom = "﻿" if existing.startswith("﻿") else ""
    written = existing[len(bom) :]
    crlf = _crlf(written)
    text = written.replace("\r\n", "\n") if crlf else written
    was = _load(text)
    if key in was:
        if was[key] is None:
            raise ConfigRefused(
                f"{CONFIG} records an empty `{key}:`: write its value there, such as "
                f"`{key}: {scalar(value)}`, or remove the line"
            )
        if was[key] == value:
            return existing
        raise ConfigRefused(
            f"{CONFIG} records `{key}: {was[key]}` already; a command never moves it — change "
            f"that line by hand to move it"
        )
    lead = "" if not text or text.endswith("\n") else "\n"
    added = line if was else f"{binding}{line}"
    updated = f"{text}{lead}{added}"
    wanted = dict(was) if was else {"pkit_schema": schema_of("config"), "schema_version": FORMAT}
    wanted[key] = value
    try:
        reads = _load(updated)
    except ConfigRefused:
        reads = None
    if reads != wanted:
        raise ConfigRefused(
            f"{CONFIG} would not read back as it is plus `{key}` — its top is not written as "
            f"the command can extend it, a block mapping: add `{key}: {scalar(value)}` at its "
            f"top level by hand, then run the command again"
        )
    return bom + (updated.replace("\n", "\r\n") if crlf else updated)


def recording(root: Path, key: str, value: str) -> str | None:
    """The text of the capability's configuration under `root` once it records `key:
    value`, every other byte kept, or None where it records that value already. Writes
    nothing. Raises ConfigRefused where the configuration cannot be read, is reached through
    a link, or cannot take the key as text."""
    target = root / CONFIG
    try:
        refuse_links(root, target)
        existing = target.read_bytes().decode("utf-8") if target.exists() else None
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigRefused(f"{CONFIG} cannot be read: {exc}") from exc
    except FileError as exc:
        raise ConfigRefused(str(exc)) from exc
    text = with_key(existing, key, value)
    return None if text == existing else text


def scalar(value: str) -> str:
    """`value` as YAML: plain where YAML reads it back as the same text and it is no word
    another version of YAML reads as another value, so another tool reads it as the same
    text too; else quoted."""
    if _PLAIN.fullmatch(value) and value.lower() not in YAML_WORDS:
        try:
            if load_yaml(f"k: {value}\n") == {"k": value}:
                return value
        except ReadError:
            pass
    return json.dumps(value, ensure_ascii=False)


def _load(text: str) -> Mapping[str, Any]:
    try:
        data = load_yaml(text, CONFIG)
    except ReadError as exc:
        raise ConfigRefused(f"{exc}; fix it first") from exc
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ConfigRefused(f"{CONFIG} is not a mapping; fix it first")
    return data


def _crlf(text: str) -> bool:
    """Whether every line of `text` ends CRLF: the file is then edited as LF and written
    back CRLF. Lines that end a lone CR, or several endings, are refused."""
    if "\r" not in text:
        return False
    if text.count("\r\n") == text.count("\n") == text.count("\r"):
        return True
    how = (
        "its lines end a lone CR"
        if "\n" not in text
        else "it has mixed line endings, some lines CRLF, others LF or a lone CR"
    )
    raise ConfigRefused(
        f"{CONFIG}: {how}. The command writes its line with the file's own ending, LF or "
        f"CRLF — give the file one of them, then run the command again"
    )
