"""Every listing of a folder in one order, sorted or reversed, for the guard on the
suite's collection (`tests/test_collection_order.py`, #2668).

A folder lists its files in an order its machine's file system sets, and two of CI's
runners list them in different orders. A test parametrized over a listing it does not
sort then collects in another order on each, and the slices of one run cut the suite
apart (ADR-078 point 5).

Loaded as a plugin, `pytest -p tests.listing_order`, with `$PKIT_LISTING_ORDER` set to
`sorted` or `reversed`, this module puts every listing in that order before any test
module is imported. It reorders `os.listdir` and `os.scandir`, and so `os.walk`,
`glob`, `Path.iterdir`, `Path.glob` and `Path.rglob`, which list through them. A
listing another program makes, such as `find` in a subprocess, it does not reach.
Without the variable, importing it changes nothing.
"""

from __future__ import annotations

import glob
import os
from collections.abc import Callable, Iterator
from typing import Any

#: The variable that names the order, and the orders it may name.
ENV = "PKIT_LISTING_ORDER"
ORDERS = ("sorted", "reversed")

_listdir = os.listdir
_scandir = os.scandir


class _Listing:
    """What `os.scandir` returns, its entries in the order given: an iterator that is
    also a context manager."""

    def __init__(self, entries: list[os.DirEntry[Any]]) -> None:
        self._entries: Iterator[os.DirEntry[Any]] = iter(entries)

    def __iter__(self) -> _Listing:
        return self

    def __next__(self) -> os.DirEntry[Any]:
        return next(self._entries)

    def __enter__(self) -> _Listing:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._entries = iter(())


def install(order: str, assign: Callable[[object, str, object], None] = setattr) -> None:
    """Make every listing come back in `order`, one of `ORDERS`, by name. `assign` sets
    each replaced function: `setattr`, or a test's `monkeypatch.setattr`."""
    if order not in ORDERS:
        raise ValueError(f"${ENV} is one of {', '.join(ORDERS)}, not {order!r}")
    backwards = order == "reversed"

    def listdir(path: Any = ".") -> list[Any]:
        return sorted(_listdir(path), reverse=backwards)

    def scandir(path: Any = ".") -> _Listing:
        with _scandir(path) as listed:
            entries = list(listed)
        return _Listing(sorted(entries, key=lambda entry: entry.name, reverse=backwards))

    assign(os, "listdir", listdir)
    assign(os, "scandir", scandir)
    # `Path.glob` and `Path.rglob` list through a globber that keeps its own reference
    # to `os.scandir`, taken when `glob` was imported (Python 3.13 on).
    globber = getattr(glob, "_StringGlobber", None)
    if globber is not None:
        assign(globber, "scandir", staticmethod(scandir))


if ENV in os.environ:
    install(os.environ[ENV])
