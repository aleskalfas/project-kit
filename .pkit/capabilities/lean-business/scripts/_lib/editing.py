"""An idea's file as a command changes it: YAML read and written round trip (lean-business
DEC-002 point 2).

A command reads a file into a `Doc`, changes its `data` in place, and takes its `text`, the
file as it would stand. A key it adds goes where the schema writes it (`place`), and one it
removes leaves the rest as they were, so a file a person laid out stays laid out. A file a
command creates (`new`) names its schema first, then its format, then its body, its lists
indented as the schemas' reference instances indent theirs.

**What a file read keeps** (`load`): its comments, each above the key or the item it was
written above where a key is added (`place`) or an item moved (`move`); its key order and
its quoting; what comes before its body, up to and through a line `---` that starts it; its
line endings, a line feed or a carriage return before each; and its indentation, a nested
mapping's step and a list's, as its first nested mapping and its first list indent them. A
file indented one way in one place and another way in another is written the first way
throughout.

What the files mean is read from that text by the reader the check uses
(`reading.load_yaml`), never from the round-trip value (`plain`): a day is its text there,
and a key given twice is refused. So a command judges the file as the check will.

- **A day** is written as the calendar day it is, a `date`, which comes out plain,
  `2026-11-20`, each time it appears: one day a command writes in two places is never
  written as an alias of the other.
- **An answer**, `yes` or `no`, is written quoted (`quoted`), so no reader of an older
  YAML takes it for a truth value.
- **A number** is written whole where it is whole (`number`), `8` rather than `8.0`, and
  one that is not finite, such as `nan` or `inf`, is refused.
"""

from __future__ import annotations

import io
import itertools
import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import CommentMark, YAMLError
from ruamel.yaml.representer import RoundTripRepresenter
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from ruamel.yaml.tokens import CommentToken
from ruamel.yaml.util import load_yaml_guess_indent

from _lib.reading import ReadError, load_yaml

#: The indentation a file a command creates takes: a mapping's keys by two, a list's items
#: by four with their dash at two, as the schemas' reference instances write them.
NEW_INDENT = (2, 4, 2)

#: The format every file of the capability is written in, its `schema_version`.
FORMAT = 1


class Refused(Exception):
    """A command refuses: nothing it asked for was written, or what it wrote was undone.
    Every write goes through `writes`, which the commands import it from; it lies here, below
    `writes`, as a file's change is refused here too (`number`)."""


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
    """A file's YAML, as a command changes it: its `data`, a mapping changed in place; the
    indentation it was written with; what came before its body, `head`; and its line
    ending. `text` keeps each."""

    def __init__(
        self,
        data: CommentedMap,
        indent: tuple[int, int, int] = NEW_INDENT,
        *,
        head: str = "",
        newline: str = "\n",
    ) -> None:
        self.data = data
        self.indent = indent
        self.head = head
        self.newline = newline

    def text(self) -> str:
        """The file as it would stand."""
        out = io.StringIO()
        _yaml(self.indent).dump(self.data, out)
        return (self.head + out.getvalue()).replace("\n", self.newline)

    def plain(self) -> Any:
        """What the file means, read from its text as the check reads it."""
        return load_yaml(self.text())


def load(text: str, source: str = "") -> Doc:
    """The file whose text is `text`, round trip, with what it keeps (the module's
    docstring). Raises ReadError where it does not parse, or is not a mapping. `source`
    names it in a refusal."""
    where = f"{source}: " if source else ""
    load_yaml(text, source)
    newline = "\r\n" if "\r\n" in text else "\n"
    # Read with each line ended by a line feed alone: the round trip writes a comment with
    # the ending it read, and every other line with a line feed.
    lines = text.replace("\r\n", "\n")
    try:
        _, sequence, offset = load_yaml_guess_indent(lines)
    except (YAMLError, ValueError) as exc:
        raise ReadError(f"{where}does not parse as YAML: {exc}") from exc
    if offset is None:
        sequence, offset = 2, 0
    indent = (_mapping_step(lines), max(sequence or 2, offset + 2), offset)
    try:
        data = _yaml(indent).load(lines)
    except (YAMLError, ValueError) as exc:
        raise ReadError(f"{where}does not parse as YAML: {exc}") from exc
    if not isinstance(data, CommentedMap):
        raise ReadError(f"{where}is not a mapping")
    return Doc(data, indent, head=_head(lines), newline=newline)


def _head(lines: str) -> str:
    """What comes before the body of the file whose text is `lines`, which the round trip
    drops: up to and through the line `---` that starts it, where only comments, blank lines
    and directives come before that; else nothing."""
    held = lines.splitlines(keepends=True)
    for index, line in enumerate(held):
        bare = line.rstrip()
        if bare == "---":
            return "".join(held[: index + 1])
        if bare.strip() and not bare.lstrip().startswith(("#", "%")):
            return ""
    return ""


def _mapping_step(lines: str) -> int:
    """How far the file whose text is `lines` indents a mapping nested in a mapping: from
    the first key that opens one to the key under it; two where none nests."""
    held = [line for line in lines.splitlines() if line.strip() and not _comment(line)]
    for line, under in itertools.pairwise(held):
        key = line.rstrip()
        if not key.endswith(":") or key.lstrip().startswith("-"):
            continue
        step = _spaces(under) - _spaces(line)
        if step > 0 and not under.lstrip().startswith("-"):
            return step
    return 2


def _comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def _spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


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
    where the schema's reference instance writes it. A key `order` does not name goes last.
    The comment lines written after the key before it, which lead the key after, stay there,
    as do those after the value it replaces (`_take_after`)."""
    if key in into:
        after = _take_after(into, key)
        into[key] = value
        _put_after(into, key, after)
        return
    position = len(into)
    if key in order:
        before = set(order[: order.index(key)])
        position = 0
        for index, held in enumerate(into):
            if held in before:
                position = index + 1
    after = _take_after(into, list(into)[position - 1]) if position > 0 else ""
    into.insert(position, key, value)
    _put_after(into, key, after)


def move(holder: CommentedMap, key: str, index: int, to: int) -> None:
    """Move the item at `index` of the list `holder[key]` to `to`, each comment line written
    above an item kept above it, and those after the last item kept after the last."""
    items = holder[key]
    count = len(items)
    leading = [_take_first(holder, key), *(_take_after(items, i) for i in range(count - 1))]
    after = _take_after(items, count - 1)
    own = items.ca.items.pop(index, None)
    item = items[index]
    del items[index]
    items.insert(to, item)
    if own is not None:
        items.ca.items[to] = own
    leading.insert(to, leading.pop(index))
    _put_first(holder, key, leading[0])
    for position in range(1, count):
        _put_after(items, position - 1, leading[position])
    _put_after(items, count - 1, after)


# --- the comments around an item ------------------------------------------------------------
#
# The round trip keeps a comment line where it read it: after the item before it, in the
# deepest last place of that item's value, with the comment on that item's own line. So a
# comment written above an item goes with the item before it, which a key inserted or an
# item moved would carry off. These take such lines out, and put them back where they lead.


def _tail(holder: CommentedMap | CommentedSeq, key: Any) -> tuple[dict[Any, Any], Any, int]:
    """Where the comment lines after the item `key` of `holder` are kept: the place of the
    comment on its line, in the deepest last item of its value."""
    value = holder[key]
    if isinstance(value, CommentedMap) and value:
        return _tail(value, list(value)[-1])
    if isinstance(value, CommentedSeq) and value:
        return _tail(value, len(value) - 1)
    return holder.ca.items, key, 2 if isinstance(holder, CommentedMap) else 0


def _take_after(holder: CommentedMap | CommentedSeq, key: Any) -> str:
    """The comment lines written after the item `key` of `holder`, before the next, taken
    out; the comment on the item's own line stays."""
    kept, at, place_of = _tail(holder, key)
    slots = kept.get(at)
    return _take_below(slots, place_of) if slots is not None else ""


def _take_below(slots: list[Any], place_of: int) -> str:
    """The lines after the first of the comment at `slots[place_of]`, taken out: the round
    trip keeps the comment on an item's line, or a key's, with the lines below it."""
    token = slots[place_of]
    if token is None:
        return ""
    line, _, rest = token.value.partition("\n")
    if line.strip():
        token.value = line + "\n"
    else:
        slots[place_of] = None
    return rest


def _put_after(holder: CommentedMap | CommentedSeq, key: Any, lines: str) -> None:
    """Write the comment lines `lines` after the item `key` of `holder`."""
    if not lines:
        return
    kept, at, place_of = _tail(holder, key)
    slots = kept.setdefault(at, [None, None, None, None])
    token = slots[place_of]
    if token is None:
        slots[place_of] = CommentToken("\n" + lines, CommentMark(0), None)
    else:
        token.value = token.value + lines


def _take_first(holder: CommentedMap, key: str) -> str:
    """The comment lines written above the first item of the list `holder[key]`, taken out:
    the round trip keeps them with the key that holds the list, and with the list too, below
    the comment on the key's line where the key has one."""
    slots = holder.ca.items.get(key)
    if slots is None:
        return ""
    lines = _take_below(slots, 2)
    tokens = slots[3]
    if not tokens:
        return lines
    lines += "".join(" " * token.column + token.value for token in tokens)
    slots[3] = None
    own = holder[key].ca
    if own.comment is not None and own.comment[1] is tokens:
        own.comment = None
    return lines


def _put_first(holder: CommentedMap, key: str, lines: str) -> None:
    """Write the comment lines `lines` above the first item of the list `holder[key]`."""
    if not lines:
        return
    first = lines.split("\n", 1)[0]
    column = _spaces(first) if first.strip() else 0
    token = CommentToken(lines[column:], CommentMark(column), None)
    holder.ca.items.setdefault(key, [None, None, None, None])[3] = [token]


def seq(items: Iterable[Any] = ()) -> CommentedSeq:
    """A list a command writes."""
    made = CommentedSeq()
    made.extend(items)
    return made


def quoted(text: str) -> DoubleQuotedScalarString:
    """`text` written quoted, as an answer is."""
    return DoubleQuotedScalarString(text)


def number(value: float) -> int | float:
    """`value` as a file writes it: whole where it is whole. Raises Refused for a value that
    is not finite, such as `nan`, `inf` or `1e400`, which no file holds as a number."""
    if not math.isfinite(value):
        raise Refused(f"`{value}` is no finite number, and a file holds only finite numbers")
    return int(value) if value == int(value) else value
