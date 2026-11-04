"""YAML text as ruamel's pure-Python safe loader reads it, the plain block form read
without it.

The loader, `YAML(typ="safe", pure=True)`, is the exact reading: each caller's
fallback builds it so, never leaving `pure` unset, since an install that holds
ruamel's compiled binding would then read the text by libyaml, as YAML 1.1.

ruamel's loader is pure Python, about a megabyte a second, and the
whole-repository friction check reads YAML on every run: every version of
every answer file in history, the front matter of every artefact file's
versions, and the settings of the commits it reads under. That reading was
most of the check's time, and it grows with every answer a change writes
(project-kit#2410).

`load` gives exactly what the loader gives. A text in the plain block form —
the form the answer writer writes, and most front matter is in — is read here,
line by line:

- block mappings, each key plain and on its own line, and block sequences, an
  entry's mapping started on the line of its dash included;
- a value on one line: a plain scalar, a quoted scalar — double-quoted only
  where its escapes are ones JSON reads alike — or a flow collection of those;
- blank lines, and comments, on lines of their own or after a value.

Each plain scalar's type is the loader's own resolver's, and a value of a type
other than text is built by the loader's own constructor, so
`2026-10-30T04:15:20Z` is the same instant and `12` the same integer. Any other
text, and any line this reading is not sure of — a block scalar, a scalar over
lines, an alias, a tag, a key written twice or of a type other than text, a
character the loader reads as a break or refuses — is read by the loader,
whole: a text it refuses raises its own error, and one this reading is unsure
of reads as the loader reads it. Tests hold both readings equal on texts made
to sit at the edges of the form, and on the answer files of the project's own
tree.

This reading takes a few parts of the loader as it is imported: the reader's
set of characters it refuses, the resolver and the constructor. Where the
installed ruamel.yaml lacks one, or calls it another way, this reading is off,
and `load` gives every text to the loader.
"""

from __future__ import annotations

import functools
import json
import re
from collections.abc import Callable
from typing import Any, cast

from ruamel.yaml import YAML

_STR = "tag:yaml.org,2002:str"
#: The implicit types a plain scalar may resolve to that this reading builds; any
#: other — the merge key `<<`, the value key `=` — leaves the text to the loader.
_BUILT = frozenset(
    {
        "tag:yaml.org,2002:null",
        "tag:yaml.org,2002:bool",
        "tag:yaml.org,2002:int",
        "tag:yaml.org,2002:float",
        "tag:yaml.org,2002:timestamp",
    }
)


def _parts() -> tuple[Any, Any, Any, str] | None:
    """The parts of the loader this reading takes: the class of a scalar's node, the
    resolver, the constructor, and the pattern of the characters the reader refuses.
    `None` where the installed ruamel.yaml lacks one, or calls it another way. Each call
    this reading makes of them is made here once, so a part renamed or changed turns the
    reading off, and no command fails for it."""
    try:
        from ruamel.yaml.nodes import ScalarNode
        from ruamel.yaml.reader import Reader

        # ruamel.yaml is untyped; its parts are read through `Any`.
        loader: Any = YAML(typ="safe", pure=True)
        resolver: Any = loader.resolver
        constructor: Any = loader.constructor
        refused = str(cast(Any, Reader).NON_PRINTABLE.pattern)
        re.compile(refused)
        if str(resolver.resolve(ScalarNode, "x", (True, False))) != _STR:
            return None
        twelve = ScalarNode(resolver.resolve(ScalarNode, "12", (True, False)), "12")
        if constructor.construct_non_recursive_object(twelve) != 12:
            return None
    except Exception:  # any part missing or changed: the loader reads every text
        return None
    return ScalarNode, resolver, constructor, refused


_PARTS = _parts()
#: Whether this reading is on: the installed ruamel.yaml has every part it takes.
ON = _PARTS is not None
# ruamel.yaml is untyped; its parts are read through `Any`, and not at all while off.
_scalar_node: Any
_resolver: Any
_constructor: Any
_scalar_node, _resolver, _constructor, _refused = _PARTS or (None, None, None, r"(?!)")

#: Characters the loader refuses, or reads as a line break or a byte-order mark,
#: and tabs and carriage returns, which a line here never holds.
_UNSURE_CHARACTERS = re.compile(_refused + r"|[\t\r\x85\u2028\u2029\ufeff]")

#: A key this reading takes: plain, opening with a word character, with no space or
#: hash in it, and a colon only before a character that continues the key.
_KEY = r"[A-Za-z0-9_](?:[A-Za-z0-9_./-]|:(?=[A-Za-z0-9_./:-]))*"
#: A line that is a key: the key, then what is written on its line after it, if anything.
_KEY_LINE = re.compile(rf"(?P<key>{_KEY}):(?: +(?P<value>.*))?")
#: The characters a plain scalar may not open with, in block or flow context.
_INDICATORS = frozenset("-?:,[]{}#&*!|>'\"%@`")
#: An escape in a double-quoted scalar that JSON and YAML read alike: none that
#: names half of a surrogate pair, which JSON joins and YAML does not.
_ESCAPE = re.compile(r'\\(?:["\\/bfnrt]|u(?![dD][89a-fA-F])[0-9a-fA-F]{4})')
_ANY_ESCAPE = re.compile(r"\\.?")
#: A plain scalar inside a flow collection, as this reading takes one: no flow
#: indicator or quote in it, a hash only after a character that is no space, and a
#: colon only before a character that continues the scalar.
_FLOW_PLAIN = re.compile(
    r"[^ ,\[\]{}#'\":]"
    r"(?:[^ ,\[\]{}#'\":]|[ ]+(?=[^ #,\[\]{}])|(?<=[^ ])#|:(?=[^ ,\[\]{}]))*"
    r"[ ]*"
)
#: A key of a flow mapping, and the space after its colon.
_FLOW_KEY = re.compile(rf"(?P<key>{_KEY}): +")
#: A double-quoted scalar on one line, to its closing quote.
_DOUBLE_QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')
#: A single-quoted scalar on one line, to its closing quote.
_SINGLE_QUOTED = re.compile(r"'(?:[^']|'')*'")
#: What may follow a value on its line: a comment.
_COMMENT = re.compile(r" +#.*")
#: The longest simple key YAML reads.
_LONGEST_KEY = 1024


class _Unsure(Exception):
    """The text is not in the form this reading is sure of: the loader reads it."""


def load(text: str, fallback: Callable[[], Any]) -> Any:
    """The YAML `text` as ruamel's safe loader reads it: read here when it is in the
    plain block form, else by `fallback`, the caller's own call of the loader on it,
    whose errors are the caller's to catch. A text this reading fails on in any way is
    the loader's too, so every error raised is the loader's own. Every text is the
    loader's while this reading is off (`ON`)."""
    if not ON:
        return fallback()
    try:
        return _read(text)
    except Exception:  # `_Unsure`, or a value the loader is to refuse
        return fallback()


def _read(text: str) -> Any:
    """The text read here; raises `_Unsure` where it is not in the plain block form."""
    if _UNSURE_CHARACTERS.search(text):
        raise _Unsure
    lines: list[tuple[int, str]] = []
    for raw in text.split("\n"):
        line = raw.rstrip(" ")
        content = line.lstrip(" ")
        if not content or content.startswith("#"):
            continue
        if line.startswith(("---", "...", "%")):
            raise _Unsure
        lines.append((len(line) - len(content), content))
    if not lines:
        raise _Unsure
    reader = _Lines(lines)
    value = reader.node(lines[0][0], lines[0][1])
    if reader.at < len(lines):
        raise _Unsure
    return value


class _Lines:
    """The non-blank, non-comment lines of a text, read from `at` on."""

    def __init__(self, lines: list[tuple[int, str]]) -> None:
        self.lines = lines
        self.at = 0

    def indent(self) -> int:
        """The indent of the next line; -1 past the last."""
        return self.lines[self.at][0] if self.at < len(self.lines) else -1

    def node(self, column: int, content: str) -> Any:
        """The block node whose first line, the current one, holds `content` at
        `column`."""
        if content == "-" or content.startswith("- "):
            return self.sequence(column)
        if _KEY_LINE.fullmatch(content):
            return self.mapping(column, content)
        raise _Unsure  # a scalar alone on its line: over lines, or a document of one

    def sequence(self, column: int) -> list[Any]:
        """A block sequence whose entries' dashes stand at `column`."""
        items: list[Any] = []
        while self.at < len(self.lines):
            indent, content = self.lines[self.at]
            if indent < column:
                break
            if indent > column or not content.startswith("- "):
                if indent == column and not content.startswith("-"):
                    break
                raise _Unsure
            rest = content[2:]
            stripped = rest.lstrip(" ")
            inner = column + 2 + (len(rest) - len(stripped))
            if _KEY_LINE.fullmatch(stripped):
                items.append(self.mapping(inner, stripped))
            else:
                self.at += 1
                items.append(_value(stripped))
            if self.indent() > column:
                raise _Unsure
        return items

    def mapping(self, column: int, first: str) -> dict[Any, Any]:
        """A block mapping whose keys stand at `column`, the first of them on the
        current line, which holds `first` from `column` on."""
        found: dict[Any, Any] = {}
        content = first
        while True:
            matched = _KEY_LINE.fullmatch(content)
            if matched is None:
                raise _Unsure
            key = _key(matched.group("key"))
            if key in found:
                raise _Unsure  # the loader's to refuse
            value_text = matched.group("value")
            self.at += 1
            if value_text is not None and not value_text.startswith("#"):
                found[key] = _value(value_text)
                if self.indent() > column:
                    raise _Unsure  # a scalar over lines, or a value the line does not end
            else:
                found[key] = self.child(column)
            if self.indent() != column:
                if self.indent() > column:
                    raise _Unsure
                return found
            content = self.lines[self.at][1]
            if content == "-" or content.startswith("- "):
                raise _Unsure  # an entry where a key is due

    def child(self, column: int) -> Any:
        """The value of a key at `column` written on the lines after it: a node
        indented further, a sequence whose dashes stand at the key's column, or
        nothing."""
        indent = self.indent()
        if indent > column:
            content = self.lines[self.at][1]
            return self.node(indent, content)
        if indent == column:
            content = self.lines[self.at][1]
            if content.startswith("- "):
                return self.sequence(column)
            if content == "-":
                raise _Unsure
        return None


@functools.lru_cache(maxsize=1 << 12)
def _key(text: str) -> str:
    """A plain key, which this reading takes only where the loader reads it as text."""
    if len(text) >= _LONGEST_KEY:
        raise _Unsure
    if str(_resolver.resolve(_scalar_node, text, (True, False))) != _STR:
        raise _Unsure
    return text


def _value(text: str) -> Any:
    """The value written as `text` after a key or a dash, to the end of its line: a
    scalar or a flow collection, and a comment after it, if any."""
    if text[0] in "\"'[{":
        value, end = _flow_node(text, 0)
        if end < len(text) and not _COMMENT.fullmatch(text, end):
            raise _Unsure
        return value
    cut = text.find(" #")
    if cut >= 0:
        text = text[:cut].rstrip(" ")
    if ": " in text or text.endswith(":"):
        raise _Unsure
    return _plain(text)


def _flow_node(text: str, at: int) -> tuple[Any, int]:
    """The node of a flow collection, or the quoted scalar, opening at `at`, and
    where it ends."""
    if at >= len(text):
        raise _Unsure  # a collection the line does not close
    first = text[at]
    if first == "[":
        return _flow_sequence(text, at + 1)
    if first == "{":
        return _flow_mapping(text, at + 1)
    if first == '"':
        end = _DOUBLE_QUOTED.match(text, at)
        if end is None:
            raise _Unsure
        return _double_quoted(end.group()), end.end()
    if first == "'":
        end = _SINGLE_QUOTED.match(text, at)
        if end is None:
            raise _Unsure
        return end.group()[1:-1].replace("''", "'"), end.end()
    found = _FLOW_PLAIN.match(text, at)
    if found is None:
        raise _Unsure
    return _plain(found.group().rstrip(" ")), found.end()


def _flow_sequence(text: str, at: int) -> tuple[list[Any], int]:
    """The flow sequence whose entries start after its `[` at `at`, and where it ends."""
    items: list[Any] = []
    at = _skip(text, at)
    if text.startswith("]", at):
        return items, at + 1
    while True:
        item, at = _flow_node(text, at)
        items.append(item)
        at = _skip(text, at)
        if text.startswith("]", at):
            return items, at + 1
        if not text.startswith(",", at):
            raise _Unsure  # a single-pair mapping, or what the sequence does not hold
        at = _skip(text, at + 1)
        if at >= len(text) or text[at] in ",]":
            raise _Unsure  # an empty entry, or a trailing comma


def _flow_mapping(text: str, at: int) -> tuple[dict[Any, Any], int]:
    """The flow mapping whose entries start after its `{` at `at`, and where it ends."""
    found: dict[Any, Any] = {}
    at = _skip(text, at)
    if text.startswith("}", at):
        return found, at + 1
    while True:
        key = _FLOW_KEY.match(text, at)
        if key is None:
            raise _Unsure
        name = _key(key.group("key"))
        if name in found:
            raise _Unsure
        found[name], at = _flow_node(text, key.end())
        at = _skip(text, at)
        if text.startswith("}", at):
            return found, at + 1
        if not text.startswith(",", at):
            raise _Unsure
        at = _skip(text, at + 1)
        if at >= len(text) or text[at] in ",}":
            raise _Unsure


def _skip(text: str, at: int) -> int:
    while at < len(text) and text[at] == " ":
        at += 1
    return at


@functools.lru_cache(maxsize=1 << 14)
def _plain(text: str) -> Any:
    """A plain scalar, of the type the loader's resolver gives it; the value is never a
    collection, so one reading serves every text that writes it."""
    if not text or text[0] in _INDICATORS:
        raise _Unsure
    tag = _resolver.resolve(_scalar_node, text, (True, False))
    name = str(tag)
    if name == _STR:
        return text
    if name not in _BUILT:
        raise _Unsure
    return _constructor.construct_non_recursive_object(_scalar_node(tag, text))


def _double_quoted(text: str) -> str:
    """A double-quoted scalar on one line, `text` with its quotes, read as JSON reads
    it where its escapes are ones the two read alike."""
    inner = text[1:-1]
    if any(not _ESCAPE.fullmatch(escape.group()) for escape in _ANY_ESCAPE.finditer(inner)):
        raise _Unsure
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise _Unsure from exc
    if not isinstance(value, str):
        raise _Unsure
    return value
