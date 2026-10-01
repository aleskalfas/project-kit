"""Edit a YAML mapping document in its text: only the keys a change touches.

Loading a YAML file, changing a value and dumping the result lays the whole
file out again — its lists re-indented, its quoting and spacing normalised —
so a one-key change shows as a rewrite of the file. `splice` makes the change
in the text instead. Given a document's text and the mapping it should hold,
it finds the keys whose values differ and edits those alone:

- a key whose value stays on one line keeps its line: only the value's
  characters are replaced, so the spacing, the quoting style and a comment
  after the value stay as written;
- a key whose value is or becomes a block collection has its lines replaced,
  from the key through the line its value ends on, by the value laid out at
  the key's column in the document's own mapping and list layout (`_Layout`);
- a key the document does not hold yet is added after the last key of the
  mapping that gets it, in that mapping's layout — or inside its braces, in a
  mapping written in flow style — and brings the mappings it needs with it.

Every other byte is the document's own: lists, comments, blank lines,
indentation and key order elsewhere stay as they were, and so do the line
breaks — the edit is made with `\\n` and written back in the one line break the
text uses (`line_breaks`). The result is read back before it is returned: it
must load as exactly the intended mapping, or `SpliceRefused` is raised and
nothing is to be written. That is the end of every change the edit of the
touched keys cannot express — one that removes a key, a text that mixes line
breaks, a key shared through a YAML alias.

ruamel declares its node and dumper API with types pyright cannot resolve, so
this module reads it in one place each, through `Any`: the composed tree into
typed `_Node`s, the dumper behind `_Render`.
"""

from __future__ import annotations

import io
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import MappingNode, Node, SequenceNode
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, SingleQuotedScalarString

from project_kit.line_breaks import line_break, universal_newlines, written_with

#: Wider than any line a configuration holds: no value is folded onto a second line.
_NO_WRAP = 1 << 16

#: The key a value is rendered under when only its own text is wanted.
_KEY = "k"

#: The scalar styles that write a value over lines of its own.
_BLOCK_SCALARS = ("|", ">")


class SpliceRefused(Exception):
    """The change cannot be made by editing only the keys it touches; nothing is to be written."""


def splice(written: str, after: Mapping[str, Any]) -> str:
    """`written` — the text of a YAML mapping document — edited to hold `after`.

    Only the keys whose values differ are edited, as the module says; the
    result reads back as `after`, or `SpliceRefused` is raised. A text that
    holds no mapping yet (blank, or comments only) gets the keys after what it
    holds.
    """
    newline = line_break(written)
    if newline is None:
        raise SpliceRefused(
            "it mixes line endings (`\\n` on some lines, `\\r\\n` or a lone `\\r` on others), "
            "and no one line ending would keep its other lines as they are; write it with one "
            "first"
        )
    text = universal_newlines(written)
    root = _compose(text)
    wanted = plain(after)
    render = _Render(_Layout.of(root))
    changes = _changes(_load(text), wanted, ())
    edited = _apply(text, [_edit(text, root, path, value, render) for path, value in changes])
    try:
        reread = _load(edited)
    except SpliceRefused:
        reread = None
    if reread != wanted:
        raise SpliceRefused(
            "editing the keys it sets would change more than those keys (is one of them "
            "shared through a YAML alias or merge key?)"
        )
    return written_with(edited, newline)


def plain(value: Any) -> Any:
    """`value` with its mappings as dicts keyed by text and its sequences as lists —
    the data a reader of the document sees, as JSON Schema sees it too."""
    if isinstance(value, Mapping):
        mapping = cast(Mapping[Any, Any], value)
        return {str(k): plain(v) for k, v in mapping.items()}
    if isinstance(value, list):
        return [plain(item) for item in cast(list[Any], value)]
    return value


# --- what changes --------------------------------------------------------------


def _changes(
    before: Mapping[str, Any], after: Mapping[str, Any], at: tuple[str, ...]
) -> Iterator[tuple[tuple[str, ...], Any]]:
    """The key path and new value of each key `after` sets differently from `before`,
    in `after`'s order: a mapping in both is compared key by key; any other value
    that differs is set whole. A key `after` drops is refused — a write sets keys."""
    for key in before:
        if key not in after:
            raise SpliceRefused(f"the change removes `{'.'.join((*at, key))}`; a write sets keys")
    for key, value in after.items():
        if key in before and before[key] == value:
            continue
        old = before.get(key)
        if key in before and isinstance(old, Mapping) and isinstance(value, Mapping):
            yield from _changes(
                cast(Mapping[str, Any], old), cast(Mapping[str, Any], value), (*at, key)
            )
        else:
            yield (*at, key), value


# --- the text --------------------------------------------------------------------


@dataclass(frozen=True)
class _Node:
    """A composed YAML node, read once out of ruamel's untyped tree.

    `start` and `end` index the text. A block collection's `end` is the next
    token — past trailing comments and blank lines — so `content_end` is where
    its own text ends; it is `None` for an empty value, which has no text.
    """

    kind: Literal["mapping", "sequence", "scalar"]
    start: int
    end: int
    column: int
    content_end: int | None
    flow: bool = False  # a collection written in flow style (`{…}`, `[…]`)
    style: str | None = None  # a scalar's style: None (plain), '"', "'", '|' or '>'
    text: str = ""  # a scalar's text
    pairs: tuple[tuple[_Node, _Node], ...] = ()
    items: tuple[_Node, ...] = ()


def _compose(text: str) -> _Node | None:
    """The document's root mapping, or `None` when it holds nothing."""
    try:
        node: Node | None = cast(Any, YAML()).compose(io.StringIO(text))
    except YAMLError as exc:
        raise SpliceRefused(f"it does not parse as YAML ({str(exc).splitlines()[0]})") from exc
    if node is None:
        return None
    root = _read(node)
    if root.kind != "mapping":
        raise SpliceRefused("it is not a mapping of keys to values")
    return root


def _read(node: Node) -> _Node:
    raw = cast(Any, node)
    start: int = raw.start_mark.index
    end: int = raw.end_mark.index
    column: int = raw.start_mark.column
    if isinstance(node, MappingNode):
        pairs = tuple((_read(key), _read(value)) for key, value in raw.value)
        flow = bool(raw.flow_style)
        content = end if flow or not pairs else _pair_end(*pairs[-1])
        return _Node("mapping", start, end, column, content, flow=flow, pairs=pairs)
    if isinstance(node, SequenceNode):
        items = tuple(_read(item) for item in raw.value)
        flow = bool(raw.flow_style)
        content = end if flow or not items else _content_end(items[-1])
        return _Node("sequence", start, end, column, content, flow=flow, items=items)
    text: str = raw.value
    style: str | None = raw.style
    content = None if text == "" and style is None else end
    return _Node("scalar", start, end, column, content, style=style, text=text)


def _load(text: str) -> dict[str, Any]:
    """The document's mapping as plain data; `{}` when it holds nothing."""
    try:
        data = cast(Any, YAML()).load(text)
    except YAMLError as exc:
        raise SpliceRefused(f"it does not parse as YAML ({str(exc).splitlines()[0]})") from exc
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise SpliceRefused("it is not a mapping of keys to values")
    return cast(dict[str, Any], plain(data))


def _pair(mapping: _Node, key: str) -> tuple[_Node, _Node] | None:
    for pair in mapping.pairs:
        if pair[0].kind == "scalar" and pair[0].text == key:
            return pair
    return None


def _pair_end(key: _Node, value: _Node) -> int:
    """Where a key's value ends in the text: its last character, not the next token."""
    return key.end if value.content_end is None else value.content_end


def _content_end(node: _Node) -> int:
    """Where a list item's text ends; an empty item's is where it starts."""
    return node.start if node.content_end is None else node.content_end


def _pairs_in(node: _Node | None) -> Iterator[tuple[_Node, _Node]]:
    """Every key and value of every mapping under `node`, in document order."""
    if node is None:
        return
    for key, value in node.pairs:
        yield key, value
        yield from _pairs_in(value)
    for item in node.items:
        yield from _pairs_in(item)


def _line_start(text: str, index: int) -> int:
    return text.rfind("\n", 0, index) + 1


def _through_line(text: str, start: int, end: int) -> int:
    """The end of the line holding the character before `end`, trailing blank lines left out."""
    newline = text.find("\n", max(end - 1, start))
    stop = len(text) if newline == -1 else newline + 1
    while stop > start:
        line_start = text.rfind("\n", start, stop - 1) + 1
        if line_start <= start or text[line_start:stop].strip():
            break
        stop = line_start
    return stop


# --- the edit ----------------------------------------------------------------------


@dataclass(frozen=True)
class _Edit:
    """Replace the characters `[start, end)` with `text`; an insertion when the two are equal."""

    start: int
    end: int
    text: str


def _edit(
    text: str, root: _Node | None, path: tuple[str, ...], value: Any, render: _Render
) -> _Edit:
    """The edit that sets the key at `path` to `value`; every mapping before its
    last step is one the document holds, since only the leaf of a change is new."""
    *parents, key = path
    if root is None:  # nothing to add to yet: the key goes after what the text holds
        return _insertion(text, len(text), render.block(render.key(key), value, 0))
    holder = root
    for step in parents:
        pair = _pair(holder, step)
        if pair is None or pair[1].kind != "mapping":
            raise SpliceRefused(
                f"`{'.'.join(path)}` is not written out in the text (is it reached through a "
                f"YAML alias or merge key?)"
            )
        holder = pair[1]
    existing = _pair(holder, key)
    if existing is None:
        return _add(text, holder, key, value, render)
    return _replace(text, holder, existing, value, render)


def _replace(
    text: str, holder: _Node, existing: tuple[_Node, _Node], value: Any, render: _Render
) -> _Edit:
    """A key's new value: in place of the old one's characters where it fits
    there, else in place of the key's lines with the key kept as written."""
    key, old = existing
    if holder.flow or old.flow:
        return _Edit(old.start, old.end, render.flow_value(value))
    if old.kind == "scalar" and old.content_end is not None and old.style not in _BLOCK_SCALARS:
        inline = render.inline(value, old.style)
        if inline is not None:
            return _Edit(old.start, old.end, inline)
    start = _line_start(text, key.start)
    if text[start : key.start].strip():
        raise SpliceRefused(f"`{key.text}` does not start its line")
    end = _through_line(text, start, _pair_end(key, old))
    lines = render.within(key, old).block(text[key.start : key.end], value, key.column)
    return _Edit(start, end, lines)


def _add(text: str, holder: _Node, key: str, value: Any, render: _Render) -> _Edit:
    """A key the mapping does not hold, after its last key and in its layout."""
    if holder.flow or not holder.pairs:
        written = render.flow_pair(key, value)
        if not holder.pairs:
            return _Edit(holder.start + 1, holder.start + 1, written)  # just inside `{`
        at = _pair_end(*holder.pairs[-1])
        return _Edit(at, at, f", {written}")
    last_key, last_value = holder.pairs[-1]
    at = _through_line(text, _line_start(text, last_key.start), _pair_end(last_key, last_value))
    column = holder.pairs[0][0].column
    return _insertion(text, at, render.block(render.key(key), value, column))


def _insertion(text: str, at: int, lines: str) -> _Edit:
    """`lines` inserted at `at`, after the line break a text's last line may lack."""
    lead = "\n" if at and text[at - 1] != "\n" else ""
    return _Edit(at, at, lead + lines)


def _apply(text: str, edits: Sequence[_Edit]) -> str:
    """`text` with every edit made, from the last to the first. Insertions at
    one place keep their order, ahead of a key's lines replaced from there.
    Edits of the same characters — a key written once and reached twice,
    through an alias — must agree."""
    unique = list(dict.fromkeys(edits))
    ordered = sorted(enumerate(unique), key=lambda e: (e[1].start, e[1].end, e[0]), reverse=True)
    bound = len(text)
    for _, edit in ordered:
        if edit.end > bound:
            raise SpliceRefused("two of the keys it sets are written in the same place")
        text = text[: edit.start] + edit.text + text[edit.end :]
        bound = edit.start
    return text


# --- rendering ---------------------------------------------------------------------


@dataclass(frozen=True)
class _Layout:
    """How the document lays out a nested block, from the column of the key that
    holds it — ruamel's `indent(mapping=…, sequence=…, offset=…)`: a mapping's keys
    `mapping` columns in, a list's dashes `offset` in and its items `sequence` in.
    What the document shows no example of takes ruamel's default."""

    mapping: int = 2
    sequence: int = 2
    offset: int = 0

    @classmethod
    def of(cls, root: _Node | None) -> _Layout:
        """The document's layout, measured from the first block mapping and the
        first block list a key holds."""
        held = [(key, value) for key, value in _pairs_in(root) if not value.flow]
        mapping = next(((k, v) for k, v in held if v.kind == "mapping" and v.pairs), None)
        sequence = next(((k, v) for k, v in held if v.kind == "sequence" and v.items), None)
        layout = cls()
        for found in (mapping, sequence):
            if found is not None:
                layout = layout.measured(*found)
        return layout

    def measured(self, key: _Node, value: _Node) -> _Layout:
        """This layout, with what `value` — the block `key` holds — shows of it."""
        if value.flow:
            return self
        if value.kind == "mapping" and value.pairs:
            return replace(self, mapping=value.pairs[0][0].column - key.column)
        if value.kind == "sequence" and value.items:
            return replace(
                self,
                sequence=value.items[0].column - key.column,
                offset=value.column - key.column,
            )
        return self


class _Render:
    """Values as text in a layout: in block style at a key's column, on one
    line, or in flow style."""

    def __init__(self, layout: _Layout) -> None:
        self.layout = layout
        self._block = _dumper(layout, flow=False)
        self._flow = _dumper(layout, flow=True)

    def within(self, key: _Node, value: _Node) -> _Render:
        """A renderer in the layout `value` — the block `key` holds — shows,
        so a block replaced keeps its own; this one where it shows none."""
        layout = self.layout.measured(key, value)
        return self if layout == self.layout else _Render(layout)

    def key(self, key: str) -> str:
        """`key` as a block mapping writes it."""
        return _dump(self._block, {key: None}).rstrip("\n").removesuffix(":")

    def block(self, key: str, value: Any, column: int) -> str:
        """`key: value` in block style, its lines at `column`; `key` is the key as written."""
        lines = _dump(self._block, {_KEY: value}).splitlines()
        lines[0] = key + lines[0][len(_KEY) :]
        pad = " " * column
        return "".join(f"{pad}{line}\n" if line else "\n" for line in lines)

    def inline(self, value: Any, style: str | None) -> str | None:
        """`value` as a scalar on one line, quoted in `style` where it was quoted;
        `None` when it takes more than one line."""
        if isinstance(value, str) and style == '"':
            value = DoubleQuotedScalarString(value)
        elif isinstance(value, str) and style == "'":
            value = SingleQuotedScalarString(value)
        lines = _dump(self._block, {_KEY: value}).splitlines()
        prefix = f"{_KEY}: "
        if len(lines) != 1 or not lines[0].startswith(prefix):
            return None
        return lines[0][len(prefix) :]

    def flow_pair(self, key: str, value: Any) -> str:
        """`key: value` as it reads inside a flow mapping's braces."""
        return _dump(self._flow, {key: value}).strip()[1:-1]

    def flow_value(self, value: Any) -> str:
        """`value` as it reads inside a flow collection."""
        return self.flow_pair(_KEY, value).removeprefix(f"{_KEY}: ")


def _dumper(layout: _Layout, *, flow: bool) -> Any:
    yaml = cast(Any, YAML())
    yaml.indent(mapping=layout.mapping, sequence=layout.sequence, offset=layout.offset)
    yaml.width = _NO_WRAP
    yaml.default_flow_style = flow
    return yaml


def _dump(yaml: Any, data: Mapping[str, Any]) -> str:
    stream = io.StringIO()
    yaml.dump(dict(data), stream)
    return stream.getvalue()
