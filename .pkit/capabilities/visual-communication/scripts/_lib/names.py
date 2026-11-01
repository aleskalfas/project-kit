"""The shapes of names, ids, token paths and language tags, and the reserved words
(DEC-002 point 4, DEC-004 points 4 and 7).

- **One name shape for every name** a person gives: a library, a component, a field, an
  option and its words, a state, a concept, a layout, a slot, an exposed part or point, an
  axis, a mode, a role's segment, a piece, a produced output, a declaration. Lower-case
  words of letters and digits joined by single hyphens, starting with a letter. So a name
  holds no `.`, `/` or `#`, and YAML never reads one as a number or a yes-or-no.
- **A token path's segments** take the same words, and may start with a digit, as in
  `space.3`. The segments are joined by `.`.
- **An id** starts with a letter and holds letters, digits, `-` and `_`. It is never one of
  the words YAML 1.1 reads as a yes-or-no, in any case.
- **A language** is a lower-case tag: two or three letters, then subtags of two to eight
  letters or digits.

Standard library only.
"""

from __future__ import annotations

import re

NAME = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
SEGMENT = r"^[a-z0-9]+(-[a-z0-9]+)*$"
ID = r"^[A-Za-z][A-Za-z0-9_-]*$"
LANGUAGE = r"^[a-z]{2,3}(-[a-z0-9]{2,8})*$"

#: The words YAML 1.1 reads as a yes-or-no, which no id may be, in any case.
YAML11_BOOLEANS = ("y", "n", "yes", "no", "true", "false", "on", "off")

#: The keys every mapping that places a component reserves (DEC-002 point 4), the
#: methodology's container among them.
RESERVED_PLACING_KEYS = ("id", "use", "concept", "state", "override", "pkit")

#: The methodology's container key (COR-053 point 10), which the capability never reads.
CONTAINER = "pkit"

#: The fields that bind a file of the capability's format, which its top reserves too.
BINDING_KEYS = ("pkit_schema", "schema_version")

#: What `use` names for a component of the piece itself.
PIECE = "piece"

#: The group of component tokens (DEC-004 point 7).
COMPONENT = "component"

#: Names no library takes: the piece's own word for `use`, and the component tokens' group.
#: The top groups of the shared roles are reserved too, read from the foundations.
RESERVED_LIBRARY_NAMES = (PIECE, COMPONENT)

_NAME = re.compile(NAME)
_SEGMENT = re.compile(SEGMENT)
_ID = re.compile(ID)
_LANGUAGE = re.compile(LANGUAGE)


def is_name(s: object) -> bool:
    """Whether `s` takes the one name shape."""
    return isinstance(s, str) and _NAME.match(s) is not None


def is_segment(s: object) -> bool:
    """Whether `s` takes the shape of one segment of a token path."""
    return isinstance(s, str) and _SEGMENT.match(s) is not None


def is_token_path(s: object) -> bool:
    """Whether `s` is a token path: segments joined by `.`."""
    return isinstance(s, str) and all(is_segment(part) for part in s.split("."))


def is_id(s: object) -> bool:
    """Whether `s` takes the id shape and is no word YAML 1.1 reads as a yes-or-no."""
    return isinstance(s, str) and _ID.match(s) is not None and s.lower() not in YAML11_BOOLEANS


def is_language(s: object) -> bool:
    """Whether `s` is a language tag of the shape the capability takes."""
    return isinstance(s, str) and _LANGUAGE.match(s) is not None


def split_use(use: str) -> tuple[str, str]:
    """A `use`'s library and component: `<library>/<component>`, or `piece/<component>`
    for a component of the piece. Raises ValueError for another shape."""
    library, slash, component = use.partition("/")
    if not slash or not is_name(library) or not is_name(component):
        raise ValueError(
            f"`use: {use}` is not `<library>/<component>`, each a name of lower-case words"
        )
    return library, component


def library_name_problem(name: str, shared_top_groups: tuple[str, ...] = ()) -> str | None:
    """Why `name` cannot name a library, or None: it takes the name shape, and is neither a
    reserved word nor the name of a top group of the shared roles (DEC-004 point 7)."""
    if not is_name(name):
        return f"`{name}` is not a name of lower-case words of letters and digits joined by hyphens"
    if name in RESERVED_LIBRARY_NAMES:
        return f"`{name}` is reserved: no library takes it"
    if name in shared_top_groups:
        return f"`{name}` is a top group of the shared roles, so no library takes it"
    return None
