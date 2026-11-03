"""The records the capability's commands keep, each read and written one way: the findings
record, the record of a piece's exports, a produced output's record, the record beside
written code, a piece's lock and the list of libraries (DEC-002 points 3 and 5).

- **Reading** (`read`): a record's value, bound to its kind at format 1. Whatever stops
  it is one error, `RecordError`, whose message is the reading's.
- **A record written whole** (`text`): a comment, then the record as block YAML, indented
  as the capability's reference instances are, no line folded and no value written as an
  alias. A time a record keeps is written quoted (`quoted_time`), so a reader of any YAML
  version reads it as text.
- **One key written into a file** (`with_mapping`): the file's text with a top-level key
  written as a block mapping, in the key's place or at the end, every other byte kept:
  its comments, its order, its line endings and a byte-order mark. The text must read
  back as it was with that key, or it is refused.
- **One entry added to a mapping of a file** (`with_entry`): the file's text with a new
  entry last in the mapping that a path of keys leads to, such as a library in the list,
  written in the style of that mapping, every other byte kept. The text must read back as
  it was with that entry, or it is refused.
"""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString

from _lib.files import FileError, read_bound
from _lib.reading import ReadError, load_yaml

#: The byte-order mark a file may open with, which a rewrite keeps.
BOM = "\ufeff"


class RecordError(Exception):
    """A record that cannot be read as its kind, or a text that cannot take a key; the
    message says why."""


def read(path: Path, kind: str) -> dict[str, Any]:
    """The value of the record of `kind` at `path`. Raises RecordError where it cannot be
    read, or is not bound to `kind` at format 1."""
    try:
        return read_bound(path, kind)
    except (ReadError, FileError) as exc:
        raise RecordError(str(exc)) from exc


def text(record: Mapping[str, Any], comment: Sequence[str], *, apart: bool = True) -> str:
    """A record written whole: a `# ` line for each line of `comment`, `#` alone for an
    empty one, then `record` as block YAML, set apart from the comment by a blank line
    unless `apart` is false."""
    lines = "".join(f"# {line}\n" if line else "#\n" for line in comment)
    gap = "\n" if apart else ""
    return f"{lines}{gap}{_dumped(record)}"


def _dumped(data: Mapping[str, Any], *, flow: bool = False) -> str:
    """`data` as the commands write YAML: block mappings indented by two, or one line of
    flow where `flow` is true; no line folded and no value written as an alias."""
    writer = YAML()
    writer.indent(mapping=2, sequence=4, offset=2)
    writer.width = 4096
    writer.default_flow_style = flow
    writer.representer.ignore_aliases = lambda *_: True
    stream = io.StringIO()
    writer.dump(dict(data), stream)
    return stream.getvalue()


def quoted_time(entry: Mapping[str, Any]) -> dict[str, Any]:
    """`entry` as a record writes it: the time under its `recorded` quoted, as every command
    writes a time."""
    recorded = dict(entry.get("recorded") or {})
    if isinstance(recorded.get("time"), str):
        recorded["time"] = SingleQuotedScalarString(recorded["time"])
    return {**entry, "recorded": recorded}


def with_mapping(original: str, key: str, mapping: Mapping[str, str], *, each: str) -> str:
    """`original`, the text of a YAML file, with its top-level `key` replaced by `mapping`,
    or added at its end: a block mapping, one entry a line in the order `mapping` gives, or
    `{}` when it is empty. Every other byte is kept: its comments, its order, its line
    endings and a byte-order mark. Raises RecordError where `original` cannot be read, or
    would not read back as it was with `mapping` under `key`; `each` names what one line
    holds, in the refusal."""
    bom, lines, newline = _lines(original)
    body = original[len(bom) :]
    block = [f"{key}:{' {}' if not mapping else ''}{newline}"]
    block += [f"  {name}: {value}{newline}" for name, value in mapping.items()]
    start = next((i for i, line in enumerate(lines) if _opens(line, key)), None)
    if start is None:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += newline
        updated = lines + block
    else:
        end = start
        for index in range(start + 1, len(lines)):
            line = lines[index]
            if not line.strip():
                continue
            if line[0] not in " \t":
                break
            end = index
        updated = lines[:start] + block + lines[end + 1 :]
    written = bom + "".join(updated)
    try:
        before, after = load_yaml(body), load_yaml(written[len(bom) :])
    except ReadError as exc:
        raise RecordError(str(exc)) from exc
    if not isinstance(before, Mapping) or after != {**before, key: dict(mapping)}:
        raise RecordError(f"write its top-level `{key}:` as a block mapping, one {each} a line")
    return written


def with_entry(original: str, path: Sequence[str], name: str, value: Any, *, each: str) -> str:
    """`original`, the text of a YAML file, with `name: value` added as the last entry of
    the mapping the keys of `path` lead to from its top. Where the mapping's entries lie
    on the lines below its key, the entry is written there as block YAML, at their indent;
    where the mapping is written in flow on its key's line, such as `{}`, it is written in
    flow before the closing brace. Every other byte is kept: its comments, its order, its
    line endings and a byte-order mark. Raises RecordError where `original` cannot be
    read, the mapping holds `name` already, or the text would not read back as it was with
    the entry added; `each` names what one entry of the mapping holds, in the refusal."""
    bom, lines, newline = _lines(original)
    before = _loaded(original[len(bom) :])
    dotted = ".".join(path)
    refusal = f"write `{dotted}` as a block mapping, one {each} an entry"
    held = _at(before, path)
    if not isinstance(held, Mapping):
        raise RecordError(f"`{dotted}` is not a mapping: {refusal}")
    if name in held:
        raise RecordError(f"`{dotted}` holds `{name}` already")
    entered = _entered(lines, path, name, value, newline)
    if entered is None:
        raise RecordError(refusal)
    written = bom + "".join(entered)
    try:
        after = load_yaml(written[len(bom) :])
    except ReadError:
        after = None
    if after != _added(before, path, name, value):
        raise RecordError(refusal)
    return written


def _lines(original: str) -> tuple[str, list[str], str]:
    """The byte-order mark `original` opens with, or "", its lines with their endings,
    and the line ending its first line takes, `\\n` where it has none."""
    bom = BOM if original.startswith(BOM) else ""
    lines = original[len(bom) :].splitlines(keepends=True)
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    return bom, lines, newline


def _loaded(text: str) -> Any:
    """The value of the YAML document `text`. Raises RecordError where it cannot be read."""
    try:
        return load_yaml(text)
    except ReadError as exc:
        raise RecordError(str(exc)) from exc


def _at(data: Any, path: Sequence[str]) -> Any:
    """The value the keys of `path` lead to in `data`, or None."""
    for key in path:
        data = data.get(key) if isinstance(data, Mapping) else None
    return data


def _added(data: Mapping[str, Any], path: Sequence[str], name: str, value: Any) -> dict[str, Any]:
    """`data` with `name: value` added to the mapping the keys of `path` lead to."""
    if not path:
        return {**data, name: value}
    head, *rest = path
    return {**data, head: _added(data[head], rest, name, value)}


def _entered(
    lines: list[str], path: Sequence[str], name: str, value: Any, newline: str
) -> list[str] | None:
    """`lines` with `name: value` added last to the mapping the keys of `path` lead to, or
    None where the lines do not show where its entries lie."""
    low, high, indent = 0, len(lines), 0
    start = end = 0
    inner: int | None = None
    for depth, key in enumerate(path):
        start = next(
            (
                index
                for index in range(low, high)
                if _indent(lines[index]) == indent and _opens(lines[index][indent:], key)
            ),
            -1,
        )
        if start < 0:
            return None
        end = _block_end(lines, start, indent)
        inner = _entries_indent(lines, start, end)
        if depth < len(path) - 1:
            if inner is None:
                return None
            low, high, indent = start + 1, end + 1, inner
    line = lines[start]
    head = line.split("#", 1)[0].rstrip()
    flow = head[indent + len(path[-1]) + 1 :].strip()
    if flow:
        if not (flow.startswith("{") and flow.endswith("}")):
            return None
        close = len(head) - 1
        gap = ", " if flow[1:-1].strip() else ""
        entry = _dumped({name: value}, flow=True).strip()[1:-1]
        return [*lines[:start], line[:close] + gap + entry + line[close:], *lines[start + 1 :]]
    if inner is None:
        return None
    block = [" " * inner + text + newline for text in _dumped({name: value}).splitlines()]
    last = lines[end] if lines[end].endswith(("\n", "\r")) else lines[end] + newline
    return [*lines[:end], last, *block, *lines[end + 1 :]]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block_end(lines: list[str], start: int, indent: int) -> int:
    """The last line of what the key on line `start`, at `indent`, holds: every line after
    it that is indented further, up to the last of them, past blank lines and comments."""
    end = start
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if _indent(line) <= indent:
            break
        end = index
    return end


def _entries_indent(lines: list[str], start: int, end: int) -> int | None:
    """The indent of the first entry on the lines after `start`, up to `end`, or None
    where they hold none: the key's value is on its own line."""
    for line in lines[start + 1 : end + 1]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return _indent(line)
    return None


def _opens(line: str, key: str) -> bool:
    """Whether `line`, from its indent on, opens `key`."""
    head = line.split("#", 1)[0].rstrip()
    return head == f"{key}:" or head.startswith((f"{key}: ", f"{key}:\t"))
