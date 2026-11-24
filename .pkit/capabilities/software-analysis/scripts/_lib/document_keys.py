"""A document a backbone command prints, read by its keys (ADR-097 point 3).

A reading finds what it needs by a key, and never takes what it does not know for what it
knows. A key it needs and does not find, a null its contract does not explain, a value of
another type than the contract's, and a value of a set it does not know are each a
document it cannot tell anything from, never a default such as false, zero or empty. So
each function here returns the value at a key as its contract types it, or raises
`Untold`, naming the key. A reading turns that into its own refusal, which says what it
could not read.

`where` names the object a key is read from, as the document holds it, `files[3]`, and
`""` for the document itself.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


class Untold(Exception):
    """The document cannot be read at a key: the key is missing, null where its contract
    does not explain a null, of another type, or a value of a set the reading does not
    know."""


def at(where: str, key: str) -> str:
    """The name of `key` of the object at `where`."""
    return f"{where}.{key}" if where else key


def value(entry: Mapping[str, Any], key: str, where: str) -> Any:
    """The value at `key`, of any type, null included."""
    if key not in entry:
        raise Untold(f"`{at(where, key)}` is missing")
    return entry[key]


def text(entry: Mapping[str, Any], key: str, where: str) -> str:
    """The string at `key`."""
    found = value(entry, key, where)
    if not isinstance(found, str):
        raise Untold(f"`{at(where, key)}` is {_kind(found)}, not a string")
    return found


def text_or_null(entry: Mapping[str, Any], key: str, where: str) -> str | None:
    """The string at `key`, or `None` where the contract prints it null."""
    found = value(entry, key, where)
    return None if found is None else text(entry, key, where)


def flag(entry: Mapping[str, Any], key: str, where: str) -> bool:
    """The boolean at `key`."""
    found = value(entry, key, where)
    if not isinstance(found, bool):
        raise Untold(f"`{at(where, key)}` is {_kind(found)}, not true or false")
    return found


def flag_or_null(entry: Mapping[str, Any], key: str, where: str) -> bool | None:
    """The boolean at `key`, or `None` where the contract prints it null."""
    found = value(entry, key, where)
    return None if found is None else flag(entry, key, where)


def number(entry: Mapping[str, Any], key: str, where: str) -> int:
    """The integer at `key`."""
    found = value(entry, key, where)
    if isinstance(found, bool) or not isinstance(found, int):
        raise Untold(f"`{at(where, key)}` is {_kind(found)}, not a whole number")
    return found


def number_or_null(entry: Mapping[str, Any], key: str, where: str) -> int | None:
    """The integer at `key`, or `None` where the contract prints it null."""
    found = value(entry, key, where)
    return None if found is None else number(entry, key, where)


def mapping(entry: Mapping[str, Any], key: str, where: str) -> Mapping[str, Any]:
    """The object at `key`."""
    found = value(entry, key, where)
    if not isinstance(found, Mapping):
        raise Untold(f"`{at(where, key)}` is {_kind(found)}, not an object")
    return found


def mapping_or_null(entry: Mapping[str, Any], key: str, where: str) -> Mapping[str, Any] | None:
    """The object at `key`, or `None` where the contract prints it null."""
    found = value(entry, key, where)
    return None if found is None else mapping(entry, key, where)


def listed(entry: Mapping[str, Any], key: str, where: str) -> list[Any]:
    """The list at `key`."""
    found = value(entry, key, where)
    if not isinstance(found, list):
        raise Untold(f"`{at(where, key)}` is {_kind(found)}, not a list")
    return found


def objects(entry: Mapping[str, Any], key: str, where: str) -> list[tuple[str, Mapping[str, Any]]]:
    """Each object of the list at `key`, with where it lies, `places[3]`."""
    found: list[tuple[str, Mapping[str, Any]]] = []
    for index, item in enumerate(listed(entry, key, where)):
        name = f"{at(where, key)}[{index}]"
        if not isinstance(item, Mapping):
            raise Untold(f"`{name}` is {_kind(item)}, not an object")
        found.append((name, item))
    return found


def texts(entry: Mapping[str, Any], key: str, where: str) -> tuple[str, ...]:
    """Each string of the list at `key`."""
    return tuple(_each(entry, key, where, str, "a string"))


def numbers(entry: Mapping[str, Any], key: str, where: str) -> tuple[int, ...]:
    """Each integer of the list at `key`."""
    return tuple(_each(entry, key, where, int, "a whole number"))


def one_of(entry: Mapping[str, Any], key: str, where: str, values: Iterable[str]) -> str:
    """The string at `key`, one of `values`: any other is a value of its set the reading
    does not know."""
    found = text(entry, key, where)
    known = frozenset(values)
    if found not in known:
        raise Untold(
            f"`{at(where, key)}` is {found!r}, a value this reading does not know "
            f"(it knows {', '.join(repr(v) for v in sorted(known))})"
        )
    return found


def _each(entry: Mapping[str, Any], key: str, where: str, kind: type, said: str) -> list[Any]:
    items = listed(entry, key, where)
    for index, item in enumerate(items):
        if not isinstance(item, kind) or (kind is int and isinstance(item, bool)):
            raise Untold(f"`{at(where, key)}[{index}]` is {_kind(item)}, not {said}")
    return items


def _kind(found: Any) -> str:
    """What `found` is, in a few words."""
    if found is None:
        return "null"
    if isinstance(found, bool):
        return "true or false"
    if isinstance(found, (int, float)):
        return "a number"
    if isinstance(found, str):
        return "a string"
    if isinstance(found, list):
        return "a list"
    if isinstance(found, Mapping):
        return "an object"
    return type(found).__name__
