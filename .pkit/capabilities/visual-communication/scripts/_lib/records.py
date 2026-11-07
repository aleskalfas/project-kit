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
  entry last in the mapping that a path of keys leads to, such as a library in the list, or
  last in the file, written in the style of that mapping, every other byte kept. The text
  must read back as it was with that entry, or it is refused.
- **One entry's value replaced** (`with_value`): the file's text with the value of an
  entry that a path of keys leads to written again in its place, such as a version of the
  list or the release a library's file names, in the style it was written in, every other
  byte kept. The text must read back as it was with that value, or it is refused.
- **One entry of a file's top taken out** (`without_entry`): the file's text without the
  lines of a top-level key, such as the place a piece names for its current copy, every
  other byte kept. The text must read back as it was without that key, or it is refused.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString

from _lib.files import FileError, read_bound
from _lib.reading import ReadError, load_yaml

#: The byte-order mark a file may open with, which a rewrite keeps.
BOM = "\ufeff"

#: The width past which a line of flow would be folded: past any line a record writes.
_FLOW_WIDTH = 1 << 24


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
    # One line of flow holds a whole value, such as a released version's hash, however long.
    writer.width = _FLOW_WIDTH if flow else 4096
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
    the mapping the keys of `path` lead to from its top; an empty `path` names the file's
    top, so the entry ends the file. Where the mapping's entries lie on the lines below its
    key, the entry is written there as block YAML, at their indent; where the mapping is
    written in flow on its key's line, such as `{}`, it is written in flow before the
    closing brace. Every other byte is kept: its comments, its order, its line endings and a
    byte-order mark. Raises RecordError where `original` cannot be read, the mapping holds
    `name` already, or the text would not read back as it was with the entry added; `each`
    names what one entry of the mapping holds, in the refusal. A key on the way that the
    text writes in quotes is found by no line, and the refusal names it, to be written
    without them."""
    bom, lines, newline = _lines(original)
    before = _loaded(original[len(bom) :])
    shown = f"`{'.'.join(path)}`" if path else "the file"
    refusal = f"write {shown} as a block mapping, one {each} an entry"
    held = _at(before, path)
    if not isinstance(held, Mapping):
        raise RecordError(f"{shown} is not a mapping: {refusal}")
    if name in held:
        raise RecordError(f"{shown} holds `{name}` already")
    entered = _entered(lines, path, name, value, newline)
    if entered is None:
        quoted = _quoted(lines, path)
        if quoted:
            keys = ", ".join(f"`{key}`" for key in quoted)
            raise RecordError(
                f"write the key{'s' if len(quoted) > 1 else ''} {keys} without quotes"
            )
        raise RecordError(refusal)
    written = bom + "".join(entered)
    try:
        after = load_yaml(written[len(bom) :])
    except ReadError:
        after = None
    if after != _added(before, path, name, value):
        raise RecordError(refusal)
    return written


def with_value(original: str, path: Sequence[str], name: str, value: Any, *, each: str) -> str:
    """`original`, the text of a YAML file, with the value of the entry `name` of the
    mapping the keys of `path` lead to replaced by `value`, in its place; an empty `path`
    names the file's top, as for the release a library's file names. Where the entry
    opens a line of its own, it is written again there, at its indent: in flow on that line
    where its value was written on it, else as block YAML on the lines below. Where the
    mapping is written in flow on one line, such as `versions: {1.0.0: {released: false}}`,
    the value is written again in flow in its place on that line. Every other byte is kept:
    its comments, its order, its line endings and a byte-order mark. Raises RecordError
    where `original` cannot be read, the mapping does not hold `name`, or the text would not
    read back as it was with the value replaced; `each` names what one entry of the mapping
    holds, in the refusal."""
    bom, lines, newline = _lines(original)
    before = _loaded(original[len(bom) :])
    dotted = ".".join(path)
    held = _at(before, path)
    if not isinstance(held, Mapping) or name not in held:
        raise RecordError(f"{f'`{dotted}`' if path else 'the file'} holds no `{name}`")
    wanted = _with_value(before, [*path, name], value)
    for candidate in _replacements(lines, path, name, value, newline):
        written = bom + "".join(candidate)
        try:
            after = load_yaml(written[len(bom) :])
        except ReadError:
            continue
        if after == wanted:
            return written
    quoted = _quoted(lines, [*path, name])
    if quoted:
        keys = ", ".join(f"`{key}`" for key in quoted)
        raise RecordError(f"write the key{'s' if len(quoted) > 1 else ''} {keys} without quotes")
    if not path:
        raise RecordError(f"write `{name}:` at the top of the file, on a line of its own")
    raise RecordError(f"write `{dotted}` as a block mapping, one {each} an entry")


def without_entry(original: str, name: str) -> str:
    """`original`, the text of a YAML file, with the entry `name` of its top taken out: the
    line that opens it, and each line its value takes below, with the comments among them.
    Every other byte is kept: its comments, its order, its line endings and a byte-order
    mark. Raises RecordError where `original` cannot be read, its top does not hold `name`,
    or the text would not read back as it was without it. A key the text writes in quotes is
    found by no line, and the refusal names it, to be written without them."""
    bom, lines, _ = _lines(original)
    before = _loaded(original[len(bom) :])
    if not isinstance(before, Mapping) or name not in before:
        raise RecordError(f"the file holds no `{name}`")
    refusal = f"write `{name}:` at the top of the file, on a line of its own"
    found = _key_lines(lines, [name])
    if found is None:
        if _quoted(lines, [name]):
            raise RecordError(f"write the key `{name}` without quotes")
        raise RecordError(refusal)
    start = found[0]
    written = bom + "".join([*lines[:start], *lines[_block_end(lines, start, 0) + 1 :]])
    try:
        # A text that holds no entry left reads as nothing.
        after = load_yaml(written[len(bom) :]) or {}
    except ReadError:
        after = None
    if after != {key: value for key, value in before.items() if key != name}:
        raise RecordError(refusal)
    return written


def _with_value(data: Mapping[str, Any], keys: Sequence[str], value: Any) -> dict[str, Any]:
    """`data` with the value the keys of `keys` lead to replaced by `value`."""
    head, *rest = keys
    return {**data, head: _with_value(data[head], rest, value) if rest else value}


def _replacements(
    lines: list[str], path: Sequence[str], name: str, value: Any, newline: str
) -> Iterator[list[str]]:
    """Each way of writing `lines` with the value of the entry `name` of the mapping the
    keys of `path` lead to replaced by `value`: where the entry opens a line of its own,
    that line and what it holds written again; else, on the line that writes in flow the
    mapping or one that holds it, each place where `name` opens an entry, its value written
    again there. A way that does not read back as wanted is passed over."""
    found = _key_lines(lines, [*path, name])
    if found is not None:
        start = found[-1]
        indent = _indent(lines[start])
        end = _block_end(lines, start, indent)
        line = lines[start]
        head = line.split("#", 1)[0].rstrip()
        rest = line[len(head) :]
        if head[indent + len(name) + 1 :].strip():
            entry = _dumped({name: value}, flow=True).strip()[1:-1]
            yield [*lines[:start], " " * indent + entry + rest, *lines[end + 1 :]]
            return
        block = [" " * indent + text + newline for text in _dumped({name: value}).splitlines()]
        block[0] = block[0][: -len(newline)] + rest
        if not lines[end].endswith(("\n", "\r")):
            block[-1] = block[-1][: -len(newline)]
        yield [*lines[:start], *block, *lines[end + 1 :]]
        return
    shown = None
    for depth in range(len(path), 0, -1):
        shown = _key_lines(lines, path[:depth])
        if shown is not None:
            break
    if shown is None:
        return
    index = shown[-1]
    line = lines[index]
    # Dumped as an entry's value, so a plain value is written as one line of flow too.
    text = _dumped({"value": value}, flow=True).strip()[len("{value: ") : -1]
    for match in re.finditer(rf"(?<=[{{,\s]){re.escape(name)}\s*:", line):
        span = _flow_span(line, match.end())
        if span is not None:
            start, end = span
            yield [*lines[:index], line[:start] + text + line[end:], *lines[index + 1 :]]


def _flow_span(line: str, start: int) -> tuple[int, int] | None:
    """Where the value of flow that starts at `start` of `line`, past its spaces, lies: a
    mapping or a sequence to its closing bracket, or a plain value to the comma or bracket
    that ends it. None where the line holds no value there."""
    begin = start
    while begin < len(line) and line[begin] == " ":
        begin += 1
    depth, quote = 0, ""
    for at in range(begin, len(line)):
        char = line[at]
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char in "{[":
            depth += 1
        elif char in "}]":
            if depth == 0:
                return _plain(line, begin, at)
            depth -= 1
            if depth == 0:
                return begin, at + 1
        elif depth == 0 and (char == "," or (char == "#" and line[at - 1] == " ")):
            return _plain(line, begin, at)
    return None


def _plain(line: str, begin: int, end: int) -> tuple[int, int] | None:
    """A plain value of flow from `begin` up to `end`, its trailing spaces left out; None
    where it is empty."""
    while end > begin and line[end - 1] == " ":
        end -= 1
    return (begin, end) if end > begin else None


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
    None where the lines do not show where its entries lie. An empty `path` names the file's
    top, whose entries end with the file."""
    if not path:
        block = [text + newline for text in _dumped({name: value}).splitlines()]
        if lines and not lines[-1].endswith(("\n", "\r")):
            return [*lines[:-1], lines[-1] + newline, *block]
        return [*lines, *block]
    found = _key_lines(lines, path)
    if found is None:
        return None
    start = found[-1]
    indent = _indent(lines[start])
    end = _block_end(lines, start, indent)
    inner = _entries_indent(lines, start, end)
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


def _key_lines(lines: list[str], path: Sequence[str], *, quoted: bool = False) -> list[int] | None:
    """The line that opens each key of `path`, from the top of `lines` down: each at the
    indent of the entries of the key before it, among the lines that key holds. None where
    the lines do not show the way. A key is found written plain, or in quotes too where
    `quoted` is true."""
    found: list[int] = []
    low, high, indent = 0, len(lines), 0
    for key in path:
        start = next(
            (
                index
                for index in range(low, high)
                if _indent(lines[index]) == indent
                and _opens(lines[index][indent:], key, quoted=quoted)
            ),
            None,
        )
        if start is None:
            return None
        found.append(start)
        if len(found) < len(path):
            end = _block_end(lines, start, indent)
            inner = _entries_indent(lines, start, end)
            if inner is None:
                return None
            low, high, indent = start + 1, end + 1, inner
    return found


def _quoted(lines: list[str], path: Sequence[str]) -> list[str]:
    """The keys of `path` that `lines` write in quotes on the way to the mapping it leads
    to; none where every key is written plain, or the way is not shown even in quotes."""
    found = _key_lines(lines, path, quoted=True)
    if found is None:
        return []
    return [
        key
        for key, index in zip(path, found, strict=True)
        if not _opens(lines[index][_indent(lines[index]) :], key)
    ]


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
    where they hold none, as when the key's value is written on the key's own line."""
    for line in lines[start + 1 : end + 1]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return _indent(line)
    return None


def _opens(line: str, key: str, *, quoted: bool = False) -> bool:
    """Whether `line`, from its indent on, opens `key`: written plain, or also in single or
    double quotes where `quoted` is true."""
    head = line.split("#", 1)[0].rstrip()
    forms = (key, f"'{key}'", f'"{key}"') if quoted else (key,)
    return any(head == f"{form}:" or head.startswith((f"{form}: ", f"{form}:\t")) for form in forms)
