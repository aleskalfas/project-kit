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
    writer = YAML()
    writer.indent(mapping=2, sequence=4, offset=2)
    writer.width = 4096
    writer.representer.ignore_aliases = lambda *_: True
    stream = io.StringIO()
    writer.dump(dict(record), stream)
    lines = "".join(f"# {line}\n" if line else "#\n" for line in comment)
    gap = "\n" if apart else ""
    return f"{lines}{gap}{stream.getvalue()}"


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
    bom = BOM if original.startswith(BOM) else ""
    body = original[len(bom) :]
    lines = body.splitlines(keepends=True)
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
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


def _opens(line: str, key: str) -> bool:
    """Whether `line` opens the top-level `key`."""
    head = line.split("#", 1)[0].rstrip()
    return head == f"{key}:" or head.startswith((f"{key}: ", f"{key}:\t"))
