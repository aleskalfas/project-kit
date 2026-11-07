"""The JSON code writer: the values document itself as one file, spelling form 1
(visual-communication DEC-004 point 4, DEC-005 points 7 to 9).

It reads the values document, version 1 (`_lib.values`), and writes it unchanged: it adds
nothing, leaves nothing out and spells no name of its own. A token path stays as the brand
exports it, and each set of values is named by the key of its combination. Its declaration,
`json_declaration.py`, says what it takes: every value type and every kind of axis.

**Form 1 is public.** Code outside the capability reads the file, so
`schemas/values.schema.json` holds its shape. A later version of the document is a new form
beside this one, and the writer keeps writing this one (DEC-005 point 8).

**The text, form 1.** The file's content is the document's fields in the order `values`
gives them, each library and each token in the order of its name, and a token's values in
the order of `keys`, so the order of the mappings handed in changes nothing. An object
opens one line for each of its keys, two spaces deeper, down to a token's values. Each
value then keeps to its one line, in the canonical text (`reading.canonical_json`), as does
the list of keys. So a change of one value is a change of one line, which is what a person
reads in the difference `pkit visual add` prints and in a commit of the file. The text ends
in one line feed. It holds no comment, since JSON has none, and the record beside the file
says what wrote it. The order and the text are fixed, so one document gives one file on
every machine.

Standard library and `_lib` only.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from _lib.plugins.json_declaration import DECLARATION
from _lib.reading import ReadError, canonical_bytes, canonical_json
from _lib.values import DOCUMENT
from _lib.values import VERSION as DOCUMENT_VERSION

NAME = DECLARATION["name"]
VERSION = DECLARATION["version"]
FORMS = tuple(DECLARATION["forms"])

#: What each level of an object is set in by.
INDENT = "  "

#: How deep a token's values lie. An object above this depth opens a line for each key.
VALUE_DEPTH = 4


class JsonError(ValueError):
    """A values document, or a request, this writer has no form for."""


def write(
    document: Mapping[str, Any],
    axes: Mapping[str, Mapping[str, Any]],
    *,
    form: int = 1,
    prefix: str | None = None,
) -> str:
    """The file of `document`, the values document version 1, in spelling `form`. `axes` is
    what the command hands every code writer; this one reads none of it, since the document
    names each combination by its key. Raises JsonError, for a `prefix` too: the command
    refuses a declaration that names one, and no name here takes one."""
    if form not in FORMS:
        forms = ", ".join(str(found) for found in FORMS)
        raise JsonError(f"the json writer {VERSION} writes form {forms}, not form {form}")
    if document.get("document") != DOCUMENT or document.get("version") != DOCUMENT_VERSION:
        raise JsonError(f"the json writer reads the document {DOCUMENT} version {DOCUMENT_VERSION}")
    if prefix is not None:
        raise JsonError(
            "the json writer takes no prefix: a token path stays as the brand exports it"
        )
    try:
        canonical_bytes(document)
    except ReadError as exc:
        raise JsonError(f"the document holds what a JSON file cannot: {exc}") from exc
    return _spelled(_ordered(document), 0) + "\n"


def _ordered(document: Mapping[str, Any]) -> dict[str, Any]:
    """The document in the order of its text, whatever the order of the mappings handed in."""
    keys = document["keys"]
    return {
        "document": document["document"],
        "version": document["version"],
        "lock": {name: document["lock"][name] for name in sorted(document["lock"])},
        "keys": keys,
        "tokens": {
            path: {
                "type": document["tokens"][path]["type"],
                "values": {key: document["tokens"][path]["values"][key] for key in keys},
            }
            for path in sorted(document["tokens"])
        },
    }


def _spelled(value: Any, depth: int) -> str:
    """`value`, which lies `depth` objects deep."""
    if not isinstance(value, Mapping) or not value or depth == VALUE_DEPTH:
        return canonical_json(value)
    lines = [
        f"{INDENT * (depth + 1)}{canonical_json(key)}: {_spelled(item, depth + 1)}"
        for key, item in value.items()
    ]
    return "{\n" + ",\n".join(lines) + "\n" + INDENT * depth + "}"
