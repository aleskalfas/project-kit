"""The JSON code writer: the values document itself as one file, in each of its forms
(visual-communication DEC-004 point 4, DEC-005 points 7 to 9, DEC-025 point 4).

It reads the values document, version 2 (`_lib.values`), and writes it as the version of
the document its form is: it adds nothing, leaves out only what that version does not hold,
and spells no name of its own. A token path stays as the brand exports it, and each set of
values is named by the key of its combination. Its declaration, `json_declaration.py`, says
what each form takes: every kind of axis, and every value type the form's version holds.

**Each form is a version of the document.** Form 1 is version 1, which holds no picture
role, so the command reports each as a loss before the writer runs and hands it none. Form 2
is version 2, which holds a picture role's file. Each is public: code outside the capability
reads the file, so `schemas/values.schema.json` holds form 1's shape, and
`schemas/values-2.schema.json` form 2's. The writer keeps writing every form it shipped
(DEC-005 point 8), and a brand that gives no picture role gets the same file of form 1 as
before version 2 came.

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
from _lib.values import DOCUMENT, PICTURE, as_version
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
    """The file of `document`, the values document version 2, in spelling `form`: the
    version of the document the form is. `axes` is what the command hands every code
    writer; this one reads none of it, since the document names each combination by its
    key. Raises JsonError, for a `prefix` too: the command refuses a declaration that names
    one, and no name here takes one. So it does for a picture role handed to form 1, whose
    version holds none: the command reports it as a loss and hands it none."""
    if form not in FORMS:
        forms = ", ".join(str(found) for found in FORMS)
        raise JsonError(f"the json writer {VERSION} writes form {forms}, not form {form}")
    if document.get("document") != DOCUMENT or document.get("version") != DOCUMENT_VERSION:
        raise JsonError(f"the json writer reads the document {DOCUMENT} version {DOCUMENT_VERSION}")
    if prefix is not None:
        raise JsonError(
            "the json writer takes no prefix: a token path stays as the brand exports it"
        )
    held = as_version(document, form)
    if len(held["tokens"]) != len(document["tokens"]):
        pictured = sorted(set(document["tokens"]) - set(held["tokens"]))
        raise JsonError(
            f"form {form} of the json writer has no form for a {PICTURE} value, so it writes "
            f"no {', '.join(f'`{path}`' for path in pictured)}"
        )
    try:
        canonical_bytes(held)
    except ReadError as exc:
        raise JsonError(f"the document holds what a JSON file cannot: {exc}") from exc
    return _spelled(_ordered(held), 0) + "\n"


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
