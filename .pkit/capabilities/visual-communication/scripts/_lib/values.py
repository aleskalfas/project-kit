"""The document of a brand's resolved values, version 1 (DEC-005 points 7 and 8).

    {"document": "visual-communication/values", "version": 1,
     "lock": {<library>: <version>}, "keys": [<key>, ...],
     "tokens": {<token path>: {"type": <DTCG type>, "values": {<key>: <value>}}}}

It holds each token of a brand with a value, resolved over its chain, in each combination
asked for, named by token path and key; keys in key order, tokens in path order. Under a
lock these are the roles the brand exports, and every other role of the libraries locked
with it, at the brand's value or at its default (DEC-008 point 5). Each
value is in its DTCG form, canonical: a colour without `hex` and with `alpha`, a font
family a list. The engine computes it and never commits it; a producer and a code writer
read it. Its version is apart from the format number of the files a project keeps: it
rises only when a reader must read it differently.

Knows nothing of the working folder, pieces, the list or the configuration.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from _lib import keys
from _lib.reading import canonical_json

DOCUMENT = "visual-communication/values"
VERSION = 1


class BrandLike(Protocol):
    """What the document needs of a brand (`tokens.Brand`)."""

    @property
    def axes(self) -> Mapping[str, keys.AxisLike]: ...

    @property
    def valued(self) -> tuple[str, ...]: ...

    def resolve(self, token_path: str, combination: Mapping[str, str]) -> Any: ...

    def type_of(self, token_path: str) -> str: ...


def document(
    brand: BrandLike,
    combinations: Iterable[Mapping[str, str]],
    lock: Mapping[str, str],
    tokens: Iterable[str] | None = None,
) -> dict[str, Any]:
    """The values document of `brand` in each of `combinations`, under `lock`: every token
    with a value under it (`valued`), or those of `tokens` alone, such as the inputs a
    producer declares. Raises tokens.UnknownRole for a token that has no value under the
    brand, and keys.BadKey for a combination its axes do not hold."""
    by_key = {keys.key_of(combination, brand.axes): combination for combination in combinations}
    ordered = sorted(by_key, key=keys.key_order)
    paths = sorted(set(tokens)) if tokens is not None else sorted(brand.valued)
    return {
        "document": DOCUMENT,
        "version": VERSION,
        "lock": {name: lock[name] for name in sorted(lock)},
        "keys": ordered,
        "tokens": {
            path: {
                "type": brand.type_of(path),
                "values": {key: brand.resolve(path, by_key[key]) for key in ordered},
            }
            for path in paths
        },
    }


def variants(doc: Mapping[str, Any]) -> dict[str, list[str]]:
    """The combinations of a values document grouped by identical values: each group under
    its variant key (`keys.variant_key`), its keys in key order. A program that reads the
    document makes one output for each group (DEC-006 point 3)."""
    groups: dict[str, list[str]] = {}
    for key in doc["keys"]:
        values = {path: token["values"][key] for path, token in doc["tokens"].items()}
        groups.setdefault(canonical_json(values), []).append(key)
    return {keys.variant_key(group): sorted(group, key=keys.key_order) for group in groups.values()}
