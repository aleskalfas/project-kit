"""Keys, combinations and variant keys (DEC-004 point 3).

A *combination* takes one mode on each axis. Its *key* names the modes that are not their
axis's default, axes in the order of their names, each segment `<axis>.<mode>`, joined by
`+`: `colour-scheme.dark+contrast.high`. The combination of every default is `default`,
which no other key spells, since every other key holds a `.`. So a key stays the same
when an axis with a default is added.

A *variant* of a picture serves one or more combinations, and takes the first of their
keys: the one with the fewest segments, then the first in string order. Keys are put in
that same order wherever a list of them is kept.

Standard library only. Knows nothing of the working folder, pieces or libraries.
"""

from __future__ import annotations

import itertools
from collections.abc import Collection, Iterable, Mapping
from typing import Protocol

DEFAULT_KEY = "default"


class AxisLike(Protocol):
    """What a key needs of an axis: its modes and its default (`tokens.Axis`)."""

    @property
    def modes(self) -> tuple[str, ...]: ...

    @property
    def default(self) -> str: ...


class BadKey(ValueError):
    """A combination or key that names an axis or a mode the axes do not hold."""


def key_of(modes: Mapping[str, str], axes: Mapping[str, AxisLike]) -> str:
    """The key of a combination: `modes` maps an axis to its mode, an axis left out taking
    its default. Raises BadKey for an axis or a mode the axes do not hold."""
    for axis, mode in modes.items():
        _check(axis, mode, axes)
    segments = [
        f"{axis}.{modes[axis]}"
        for axis in sorted(axes)
        if axis in modes and modes[axis] != axes[axis].default
    ]
    return "+".join(segments) if segments else DEFAULT_KEY


def parse_key(key: str, axes: Mapping[str, AxisLike]) -> dict[str, str]:
    """The combination a key names, every axis given its mode. Raises BadKey for a key
    that is not spelled as `key_of` spells it."""
    combination = {axis: spec.default for axis, spec in axes.items()}
    if key == DEFAULT_KEY:
        return combination
    seen: list[str] = []
    for segment in key.split("+"):
        axis, dot, mode = segment.partition(".")
        if not dot:
            raise BadKey(f"`{key}` is not a key: `{segment}` is not `<axis>.<mode>`")
        _check(axis, mode, axes)
        if mode == axes[axis].default:
            raise BadKey(f"`{key}` names the default mode of `{axis}`, which a key leaves out")
        if seen and axis <= seen[-1]:
            raise BadKey(f"`{key}` does not name its axes once each, in the order of their names")
        seen.append(axis)
        combination[axis] = mode
    return combination


def narrowed(key: str, axes: Collection[str]) -> str:
    """The key of the part of the combination `key` names on the axes `axes`: its segments
    of every other axis left out, such as a brand's own axis where only shared axes are
    read. Checks nothing of the segments it keeps."""
    kept = [segment for segment in key.split("+") if segment.partition(".")[0] in axes]
    return "+".join(kept) if key != DEFAULT_KEY and kept else DEFAULT_KEY


def combinations(
    named: Mapping[str, Iterable[str]], axes: Mapping[str, AxisLike]
) -> list[dict[str, str]]:
    """Every combination of the modes `named` gives each axis; an axis it names none of is
    taken at its default. In key order (`key_order`). Raises BadKey for an axis or a mode
    the axes do not hold, and for an axis named with no mode or one mode twice."""
    choices: list[tuple[str, tuple[str, ...]]] = []
    for axis in named:
        _check_axis(axis, axes)
    for axis in sorted(axes):
        modes = tuple(named.get(axis, (axes[axis].default,)))
        if not modes:
            raise BadKey(f"the axis `{axis}` is named with no mode")
        if len(set(modes)) != len(modes):
            raise BadKey(f"the axis `{axis}` names a mode twice")
        for mode in modes:
            _check(axis, mode, axes)
        choices.append((axis, modes))
    product = [
        dict(zip([axis for axis, _ in choices], picked, strict=True))
        for picked in itertools.product(*(modes for _, modes in choices))
    ]
    return sorted(product, key=lambda combination: key_order(key_of(combination, axes)))


def key_order(key: str) -> tuple[int, str]:
    """Where a key falls among keys: by its count of segments, then its spelling. The
    default key, with none, comes first."""
    return (0 if key == DEFAULT_KEY else key.count("+") + 1, key)


def variant_key(keys: Iterable[str]) -> str:
    """The key a variant takes from the keys of the combinations it serves: the first in
    key order. Raises ValueError for no keys."""
    return min(keys, key=key_order)


def _check_axis(axis: str, axes: Mapping[str, AxisLike]) -> None:
    if axis not in axes:
        known = ", ".join(sorted(axes)) or "none"
        raise BadKey(f"`{axis}` is not an axis (the axes: {known})")


def _check(axis: str, mode: str, axes: Mapping[str, AxisLike]) -> None:
    _check_axis(axis, axes)
    if mode not in axes[axis].modes:
        known = ", ".join(axes[axis].modes)
        raise BadKey(f"`{mode}` is not a mode of `{axis}` (its modes: {known})")
