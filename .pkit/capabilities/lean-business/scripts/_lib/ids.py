"""Ids and the references between an idea's files (lean-business DEC-002 point 7).

- **An id** is lower-case words joined by hyphens, starting with a letter: a *segment*. An
  idea's id is one segment, its folder's name.
- **A qualified id** joins its parts with full stops. A variant's, an experiment's and a
  cycle's id is qualified by its idea, `<idea>.<own>`; an entry's and an assumption's by
  its variant, `<idea>.<variant>.<own>`. So each is unique across the location, and safe in
  a path.
- **A reference** names a subject of another file in the typed form `[<namespace>:<id>]`
  (COR-019), the namespace being the stem of the schema that holds the subject: `canvas`
  for a variant, `assumptions`, `experiment` and `cycle`.

The patterns here are the ones `schemas/shapes.schema.json` writes, and a test holds the
two equal.
"""

from __future__ import annotations

import re
from typing import NamedTuple

#: One part of an id.
SEGMENT = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"

#: A variant's, an experiment's or a cycle's id: `<idea>.<own>`.
IDEA_QUALIFIED = rf"{SEGMENT}\.{SEGMENT}"

#: A canvas entry's or an assumption's id: `<idea>.<variant>.<own>`.
VARIANT_QUALIFIED = rf"{SEGMENT}\.{SEGMENT}\.{SEGMENT}"

#: The namespaces a reference names, each the stem of the schema that holds its subject.
CANVAS = "canvas"
ASSUMPTIONS = "assumptions"
EXPERIMENT = "experiment"
CYCLE = "cycle"

#: The id each namespace's subjects carry.
ID_PATTERN = {
    CANVAS: IDEA_QUALIFIED,
    ASSUMPTIONS: VARIANT_QUALIFIED,
    EXPERIMENT: IDEA_QUALIFIED,
    CYCLE: IDEA_QUALIFIED,
}

#: The full pattern of a reference into each namespace.
REF_PATTERN = {namespace: rf"\[{namespace}:{qid}\]" for namespace, qid in ID_PATTERN.items()}

_SEGMENT = re.compile(rf"^{SEGMENT}$")
_IDEA_QUALIFIED = re.compile(rf"^{IDEA_QUALIFIED}$")
_VARIANT_QUALIFIED = re.compile(rf"^{VARIANT_QUALIFIED}$")
_REFS = {namespace: re.compile(rf"^{pattern}$") for namespace, pattern in REF_PATTERN.items()}


class Ref(NamedTuple):
    """A reference read: the namespace it names and the id it names there."""

    namespace: str
    id: str


def is_segment(value: object) -> bool:
    return isinstance(value, str) and _SEGMENT.match(value) is not None


def is_idea_qualified(value: object) -> bool:
    return isinstance(value, str) and _IDEA_QUALIFIED.match(value) is not None


def is_variant_qualified(value: object) -> bool:
    return isinstance(value, str) and _VARIANT_QUALIFIED.match(value) is not None


def ref(namespace: str, qualified: str) -> str:
    """The reference to the subject `qualified` of `namespace`, as a file writes it."""
    return f"[{namespace}:{qualified}]"


def parse_ref(value: object, namespace: str) -> Ref | None:
    """The reference `value` writes into `namespace`, or None where it is no such
    reference."""
    pattern = _REFS.get(namespace)
    if not isinstance(value, str) or pattern is None or pattern.match(value) is None:
        return None
    return Ref(namespace, value[len(namespace) + 2 : -1])


def idea_of(qualified: str) -> str:
    """The idea a qualified id belongs to: its first part."""
    return qualified.split(".", 1)[0]


def qualifier(qualified: str) -> str:
    """What a qualified id is qualified by: every part but its last."""
    return qualified.rsplit(".", 1)[0]


def own(qualified: str) -> str:
    """A qualified id's own part: its last."""
    return qualified.rsplit(".", 1)[-1]
