"""Reading the capability's files: YAML 1.2, a calendar day as the text it is written as.

A file is read as its value, never its bytes, so its layout, its key order and its
comments mean nothing (lean-business DEC-002 point 13). A timestamp is read as the text it
is written as, so a day written `2026-11-19` and one quoted `"2026-11-19"` read alike, and
`day` turns either into a date. A key given twice is refused.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.constructor import SafeConstructor
from ruamel.yaml.error import YAMLError

#: A calendar day as the files write it (DEC-003 point 1).
_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class ReadError(Exception):
    """A file that cannot be read, or does not parse as YAML."""


class _Constructor(SafeConstructor):
    """The safe constructor, with a timestamp read as the text it is written as."""


_Constructor.add_constructor("tag:yaml.org,2002:timestamp", SafeConstructor.construct_yaml_str)


def _yaml() -> YAML:
    loader = YAML(typ="safe", pure=True)
    loader.Constructor = _Constructor
    return loader


def load_yaml(text: str, source: str = "") -> Any:
    """The value of the YAML document `text`. `source` names it in a refusal."""
    where = f"{source}: " if source else ""
    try:
        return _yaml().load(text)
    except (YAMLError, ValueError) as exc:
        problem = str(exc).strip().splitlines()
        raise ReadError(f"{where}does not parse as YAML: {problem[0] if problem else exc}") from exc


def read_yaml(path: Path) -> Any:
    """The value of the YAML file at `path`."""
    try:
        text = path.read_bytes().decode("utf-8")
    except OSError as exc:
        raise ReadError(f"{path}: cannot be read: {exc.strerror or exc}") from exc
    except UnicodeDecodeError as exc:
        raise ReadError(f"{path}: is not UTF-8: {exc}") from exc
    return load_yaml(text, str(path))


def written_as_day(value: object) -> bool:
    """Whether `value` is written in the shape of a day, `YYYY-MM-DD`, whether or not the
    calendar holds it."""
    return isinstance(value, str) and _DAY.fullmatch(value) is not None


def day(value: object) -> date | None:
    """The calendar day `value` writes as `YYYY-MM-DD`, or None for anything else, such
    as a day the calendar does not hold."""
    if not isinstance(value, str) or not written_as_day(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
