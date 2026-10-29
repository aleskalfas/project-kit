"""The rule sets the backbone ships, which every adopter receives (COR-068; ADR-075 point 1).

Every adopter holds `.pkit/rule-sets/`, where the backbone keeps its method rule
sets, the loaded set `OPS` among them. The folder is a place declared to hold
rule sets, so the friction walk walks it, and each of its rules is an artefact
carrying the `pkit` container. A fresh adopter's friction pass is therefore awake,
and it holds rule sets and artefacts before a test writes any.

A test about something else, written while a fresh adopter held none, leaves the
shipped sets out of what it compares:

- `own` keeps the items of a sequence that are not the shipped sets': paths,
  locations, or objects with a `path` or `location`;
- `own_keys` does the same for a mapping keyed by path or location;
- `without_shipped_rule_sets` takes the folder out of an adopter, for a test whose
  subject needs an adopter that holds no artefact or rule set, such as a dormant
  pass or a count line.

A test of what the shipped sets change, such as a fresh install's counts, reads
them with `shipped_rules`, so it follows the set as it grows.

The dormant-pass tests that take the folder out cover a state no installed project
reaches since ADR-075, since every install carries it.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, TypeVar

from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs

#: The backbone's rule-set folder, as discovery names it.
SHIPPED_RULE_SETS = fd.BACKBONE_RULE_SETS_DIR.as_posix()

T = TypeVar("T")
V = TypeVar("V")


def is_shipped(path: str) -> bool:
    """Whether a repository-relative path, or an artefact's location, lies in the
    backbone's rule-set folder, or is that folder."""
    return path == SHIPPED_RULE_SETS or path.startswith(f"{SHIPPED_RULE_SETS}/")


#: The fields an item names its path by, the first it has.
_PATH_FIELDS = ("path", "pattern", "location")


def _path_of(item: Any) -> str:
    if isinstance(item, str):
        return item
    for name in _PATH_FIELDS:
        value = item.get(name) if isinstance(item, Mapping) else getattr(item, name, None)
        if isinstance(value, str):
            return value
    raise TypeError(f"{item!r} names no path: give `own` a key")


def own(items: Iterable[T], key: Callable[[T], str] | None = None) -> list[T]:
    """`items` in their order, the shipped sets' left out. An item is a path or a
    location, an object or a mapping with a `path`, `pattern` or `location`, or `key`
    gives one."""
    path_of: Callable[[T], str] = key if key is not None else _path_of
    return [item for item in items if not is_shipped(path_of(item))]


def own_keys(mapping: Mapping[str, V]) -> dict[str, V]:
    """`mapping`, keyed by path or location, the shipped sets' keys left out."""
    return {key: value for key, value in mapping.items() if not is_shipped(key)}


def without_shipped_rule_sets(adopter: Any) -> None:
    """Take the backbone's rule-set folder out of an adopter: an `AdopterRepo`, or its
    root. A module-level function, so a template may be prepared with it."""
    root = adopter if isinstance(adopter, Path) else adopter.root
    shutil.rmtree(root / SHIPPED_RULE_SETS)


def shipped_rules(root: Path) -> tuple[str, ...]:
    """The ids of the rules the backbone's rule sets hold in the adopter at `root`, in
    the order discovery reads them."""
    return tuple(r.id for r in rs.discover_rule_sets(root).rules if is_shipped(r.path))
