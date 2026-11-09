"""The document of a brand's resolved values, version 2 (DEC-005 points 7 and 8, DEC-025
point 4).

    {"document": "visual-communication/values", "version": 2,
     "lock": {<library>: <version>}, "keys": [<key>, ...],
     "tokens": {<token path>: {"type": <type>, "values": {<key>: <value>}}}}

It holds each token of a brand with a value, resolved over its chain, in each combination
asked for, named by token path and key; keys in key order, tokens in path order. Under a
lock these are the roles the brand exports, and every other role of the libraries locked
with it, at the brand's value or at its default (DEC-008 point 5). Each
value is in its DTCG form, canonical: a colour without `hex` and with `alpha`, a font
family a list. The engine computes it and never commits it; a producer and a code writer
read it. Its version is apart from the format number of the files a project keeps: it
rises only when a reader must read it differently.

**Version 2** holds, beside them, each picture role the brand gives a file (DEC-025 point
4), of the type `picture`. Its value in a combination is the file's bare name and the
brand whose version holds it, `{"file": <name>, "library": <brand>}`, that version being
the one `lock` names; or `null` where the brand gives the role no file there, which no
brand owes. Version 1 is version 2 without its picture roles (`as_version`): every other
token reads the same in both.

Knows nothing of the working folder, pieces, the list or the configuration.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from _lib import keys
from _lib.reading import canonical_json

DOCUMENT = "visual-communication/values"
VERSION = 2

#: Each version of the document a reader may still read: the first holds no picture role.
VERSIONS = (1, 2)

#: The type of a picture role, which version 2 holds and version 1 does not.
PICTURE = "picture"


class GivenLike(Protocol):
    """What the document needs of the file a brand gives a picture role (`tokens.GivenPicture`)."""

    @property
    def name(self) -> str: ...

    @property
    def brand(self) -> str: ...


class BrandLike(Protocol):
    """What the document needs of a brand (`tokens.Brand`)."""

    @property
    def axes(self) -> Mapping[str, keys.AxisLike]: ...

    @property
    def valued(self) -> tuple[str, ...]: ...

    @property
    def pictured(self) -> tuple[str, ...]: ...

    def resolve(self, token_path: str, combination: Mapping[str, str]) -> Any: ...

    def given(self, token_path: str, combination: Mapping[str, str]) -> GivenLike | None: ...

    def type_of(self, token_path: str) -> str: ...


def document(
    brand: BrandLike,
    combinations: Iterable[Mapping[str, str]],
    lock: Mapping[str, str],
    tokens: Iterable[str] | None = None,
) -> dict[str, Any]:
    """The values document of `brand` in each of `combinations`, under `lock`: every token
    with a value under it (`valued`), and each picture role it gives a file in one of them
    (`pictured`); or those of `tokens` alone, such as the inputs a producer declares.
    Raises tokens.UnknownRole for a token that has no value under the brand, and
    keys.BadKey for a combination its axes do not hold."""
    by_key = {keys.key_of(combination, brand.axes): combination for combination in combinations}
    ordered = sorted(by_key, key=keys.key_order)
    pictured = {
        path
        for path in brand.pictured
        if any(brand.given(path, by_key[key]) is not None for key in ordered)
    }
    paths = sorted(set(tokens)) if tokens is not None else sorted({*brand.valued, *pictured})
    return {
        "document": DOCUMENT,
        "version": VERSION,
        "lock": {name: lock[name] for name in sorted(lock)},
        "keys": ordered,
        "tokens": {
            path: {
                "type": brand.type_of(path),
                "values": {
                    key: _picture(brand.given(path, by_key[key]))
                    if path in pictured
                    else brand.resolve(path, by_key[key])
                    for key in ordered
                },
            }
            for path in paths
        },
    }


def _picture(given: GivenLike | None) -> dict[str, str] | None:
    """A picture role's value in one combination: the file's bare name and the brand whose
    version holds it; None where the brand gives the role no file there."""
    return None if given is None else {"file": given.name, "library": given.brand}


def as_version(doc: Mapping[str, Any], version: int) -> dict[str, Any]:
    """The document `doc`, of version 2, as `version` holds it: version 1 leaves out each
    picture role, and every other token reads the same. Raises ValueError for a version
    no reader reads."""
    if version not in VERSIONS:
        raise ValueError(f"the document {DOCUMENT} has no version {version}")
    tokens = {
        path: token
        for path, token in doc["tokens"].items()
        if version > 1 or token["type"] != PICTURE
    }
    return {**doc, "version": version, "tokens": tokens}


def variants(doc: Mapping[str, Any]) -> dict[str, list[str]]:
    """The combinations of a values document grouped by identical values: each group under
    its variant key (`keys.variant_key`), its keys in key order. A program that reads the
    document makes one output for each group (DEC-006 point 3)."""
    groups: dict[str, list[str]] = {}
    for key in doc["keys"]:
        values = {path: token["values"][key] for path, token in doc["tokens"].items()}
        groups.setdefault(canonical_json(values), []).append(key)
    return {keys.variant_key(group): sorted(group, key=keys.key_order) for group in groups.values()}
