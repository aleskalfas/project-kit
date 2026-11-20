"""An idea's file as a command changes it: YAML read and written round trip, its comments,
its key order, its quoting and its indentation kept (lean-business DEC-002 point 2).

A command reads a file into a `Doc`, changes its `data` in place, and takes its `text`, the
file as it would stand. A key it adds goes at the end of its mapping, and one it removes
leaves the rest as they were, so a file a person laid out stays laid out. A file a command
creates (`new`) names its schema first, then its format, then its body, its lists indented
as the schemas' reference instances indent theirs.

What the files mean is read from that text by the reader the check uses
(`reading.load_yaml`), never from the round-trip value (`plain`): a day is its text there,
and a key given twice is refused. So a command judges the file as the check will.

- **A day** is written as the calendar day it is, a `date`, which comes out plain,
  `2026-11-20`, each time it appears: one day a command writes in two places is never
  written as an alias of the other.
- **An answer**, `yes` or `no`, is written quoted (`quoted`), so no reader of an older
  YAML takes it for a truth value.
"""

from __future__ import annotations

import io
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.representer import RoundTripRepresenter
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from ruamel.yaml.util import load_yaml_guess_indent

from _lib.reading import ReadError, load_yaml

#: The indentation a file a command creates takes: a mapping's keys by two, a list's items
#: by four with their dash at two, as the schemas' reference instances write them.
NEW_INDENT = (2, 4, 2)

#: The format every file of the capability is written in, its `schema_version`.
FORMAT = 1


class _Representer(RoundTripRepresenter):
    """The round-trip representer, which writes a day as itself wherever it appears, never
    as an anchor and its alias."""

    def ignore_aliases(self, data: Any) -> bool:
        return isinstance(data, date) or super().ignore_aliases(data)


def _yaml(indent: tuple[int, int, int]) -> YAML:
    mapping, sequence, offset = indent
    yaml = YAML()
    yaml.Representer = _Representer
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=mapping, sequence=sequence, offset=offset)
    return yaml


class Doc:
    """A file's YAML, as a command changes it: its `data`, a mapping changed in place, and
    the indentation it was written with, which `text` keeps."""

    def __init__(self, data: CommentedMap, indent: tuple[int, int, int] = NEW_INDENT) -> None:
        self.data = data
        self.indent = indent

    def text(self) -> str:
        """The file as it would stand."""
        out = io.StringIO()
        _yaml(self.indent).dump(self.data, out)
        return out.getvalue()

    def plain(self) -> Any:
        """What the file means, read from its text as the check reads it."""
        return load_yaml(self.text())


def load(text: str, source: str = "") -> Doc:
    """The file whose text is `text`, round trip. Raises ReadError where it does not parse,
    or is not a mapping. `source` names it in a refusal."""
    where = f"{source}: " if source else ""
    load_yaml(text, source)
    try:
        _, sequence, offset = load_yaml_guess_indent(text)
    except (YAMLError, ValueError) as exc:
        raise ReadError(f"{where}does not parse as YAML: {exc}") from exc
    indent = (2, max(sequence or 2, 2) if offset else 2, offset or 0)
    try:
        data = _yaml(indent).load(text)
    except (YAMLError, ValueError) as exc:
        raise ReadError(f"{where}does not parse as YAML: {exc}") from exc
    if not isinstance(data, CommentedMap):
        raise ReadError(f"{where}is not a mapping")
    return Doc(data, indent)


def new(schema: str, body: Mapping[str, Any]) -> Doc:
    """A file a command creates, bound to `schema`, such as `lean-business:canvas`, holding
    `body` after its binding."""
    data = CommentedMap()
    data["pkit_schema"] = schema
    data["schema_version"] = FORMAT
    for key, value in body.items():
        data[key] = value
    return Doc(data)


def mapping(pairs: Iterable[tuple[str, Any]] = ()) -> CommentedMap:
    """A mapping a command writes, its keys in the order given, each value that is None
    left out."""
    made = CommentedMap()
    for key, value in pairs:
        if value is not None:
            made[key] = value
    return made


def place(into: CommentedMap, key: str, value: Any, order: Sequence[str]) -> None:
    """Set `key` of the mapping `into` to `value`: where it is, in its place; where it is
    not, after the last key that comes before it in `order`, so a key a command adds lands
    where the schema's reference instance writes it. A key `order` does not name goes last."""
    if key in into:
        into[key] = value
        return
    if key not in order:
        into[key] = value
        return
    before = set(order[: order.index(key)])
    position = 0
    for index, held in enumerate(into):
        if held in before:
            position = index + 1
    into.insert(position, key, value)


def seq(items: Iterable[Any] = ()) -> CommentedSeq:
    """A list a command writes."""
    made = CommentedSeq()
    made.extend(items)
    return made


def quoted(text: str) -> DoubleQuotedScalarString:
    """`text` written quoted, as an answer is."""
    return DoubleQuotedScalarString(text)
