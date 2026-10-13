"""The prose lint (#1415): the mechanical parts of the writing rules, in the text a change adds.

Each mechanical part of a writing rule is an entry in `scripts/prose-lint.yaml`,
of one of four types: `count`, `forbid`, `substitute` and `link-resolves`. The
entries are data, and a new mechanical rule is an entry, not code.

What the lint checks:

- **Where:** in each artefact the change altered, by the accepted rules that
  bind on it at the head. It reads them, and the base, from the document
  `pkit rule-sets altered --json` prints (`rule_set_reading.altered_document`).
  It keeps no list of paths of its own.
- **Which entries:** an entry applies where its rule binds and the rule's set
  declares the part under `checks`, naming the check `prose-lint` (COR-051
  point 2).
- **Which text:** a finding is the change's when its unit holds text the change
  adds or moves. The unit is a sentence or a paragraph for `count`, and the
  match itself for the other types. A break the change only sits beside is not
  the change's.

How it reads text follows RS-WRITE-005's *How* (`tech-docs/rule-sets/writing.md`):

- A word is a token between spaces that holds a letter or a digit, once bold
  marks and backticks are removed.
- A sentence ends at a full stop, a question mark or an exclamation mark before
  a space or a line end. Each block ends one too: a paragraph, a list item, a
  table cell and a front-matter value.
- Headings, bold labels, code blocks and the quoted example of an item labelled
  "Breaks the rule" are not read, and nor is an HTML comment. For a count, a
  bare URL and an HTML entity are tokens like any other, and a link's target
  is part of its link's last token. No pattern searches them.

`lint_text` reads a given text whole, as a test of stamped template text calls
it. From the repository root:

    uv run python scripts/prose_lint.py               # against the check's base
    uv run python scripts/prose_lint.py --base main   # against the merge-base with main

Exit 0 when nothing is found, 1 on a finding, and 2 when the lint cannot run.
"""

from __future__ import annotations

import argparse
import re
import sys
import traceback
from bisect import bisect_right
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from html.entities import html5
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

import click
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from project_kit import rule_set_reading, validators
from project_kit.document_parts import split_front_matter
from project_kit.friction_git import CommitTree
from project_kit.line_breaks import universal_newlines
from project_kit.working_tree import WorkingTree

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "scripts" / "prose-lint.yaml"

#: The name a rule set's `checks` gives this lint (COR-051 point 2).
CHECK = "prose-lint"

#: The version of `pkit rule-sets altered --json` the lint reads.
ALTERED_SCHEMA_VERSION = 1

#: The methodology's container, whose answers are never read as prose (RS-WRITE-013).
CONTAINER = "pkit"

#: The label that marks a quoted example of a broken rule (WRITE, "How a rule reads").
BROKEN_EXAMPLE = "Breaks the rule"

TYPES = ("count", "forbid", "substitute", "link-resolves")
EXCEPTIONS = ("code", "quotes", "cells")


class LintError(Exception):
    """The lint cannot run: an entry is malformed, or a text cannot be read."""


# --- entries ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    """One mechanical part of a rule, as `scripts/prose-lint.yaml` writes it.

    - `rule`: the rule's id, bare or as cited.
    - `type`: `count`, `forbid`, `substitute` or `link-resolves`.
    - `fields`: the type's own fields.
    - `exceptions`: the parts of the prose it does not read.
    """

    rule: str
    type: str
    fields: Mapping[str, Any] = field(default_factory=dict[str, Any])
    exceptions: frozenset[str] = frozenset()


_RULE_ID = re.compile(r"^(?:[a-z][a-z0-9-]*:)?RS-[A-Z][A-Z0-9]*-\d{3,}$")
_FIELDS: Mapping[str, frozenset[str]] = {
    "count": frozenset({"count", "in", "max"}),
    "forbid": frozenset({"pattern", "name"}),
    "substitute": frozenset({"replace"}),
    "link-resolves": frozenset(),
}


def entry(data: Mapping[str, Any]) -> Entry:
    """One entry from its data, every field checked. Raises `LintError` when it is malformed."""
    rule, kind = data.get("rule"), data.get("type")
    where = f"entry {rule or '(no rule)'}"
    if not isinstance(rule, str) or not _RULE_ID.match(rule):
        raise LintError(f"{where}: `rule` is not a rule id, such as RS-WRITE-005")
    if kind not in TYPES:
        raise LintError(f"{where}: `type` is not one of {', '.join(TYPES)}")
    own = {k: v for k, v in data.items() if k not in ("rule", "type", "except")}
    unknown = sorted(str(k) for k in set(own) - _FIELDS[kind])
    if unknown:
        raise LintError(f"{where}: a {kind} entry takes no {', '.join(unknown)}")
    exceptions = data.get("except", [])
    if not isinstance(exceptions, list) or not all(e in EXCEPTIONS for e in exceptions):
        raise LintError(f"{where}: `except` lists only {', '.join(EXCEPTIONS)}")
    _check_fields(where, kind, own)
    return Entry(rule, kind, own, frozenset(exceptions))


def _check_fields(where: str, kind: str, own: Mapping[str, Any]) -> None:
    if kind == "count":
        if own.get("count") not in ("words", "sentences") or own.get("in") not in (
            "sentence",
            "paragraph",
        ):
            raise LintError(f"{where}: `count` is words or sentences, `in` sentence or paragraph")
        if own["count"] == "sentences" and own["in"] == "sentence":
            raise LintError(f"{where}: a sentence holds one sentence")
        limit = own.get("max")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise LintError(f"{where}: `max` is a whole number")
    elif kind == "forbid":
        pattern = own.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise LintError(f"{where}: `pattern` is a regular expression")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise LintError(f"{where}: `pattern` does not compile: {exc}") from exc
        if "name" in own and not isinstance(own["name"], str):
            raise LintError(f"{where}: `name` is text")
    elif kind == "substitute":
        pairs = own.get("replace")
        if (
            not isinstance(pairs, Mapping)
            or not pairs
            or not all(
                isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
                for k, v in pairs.items()
            )
        ):
            raise LintError(f"{where}: `replace` maps each word to the word that replaces it")


def load_entries(path: Path = ENTRIES) -> list[Entry]:
    """The entries of the data file. Raises `LintError` when it is malformed."""
    try:
        data = YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError) as exc:
        raise LintError(f"{path.name}: cannot read it: {exc}") from exc
    if not isinstance(data, Mapping) or not isinstance(data.get("entries"), list):
        raise LintError(f"{path.name}: holds no `entries` list")
    found: list[Entry] = []
    for item in data["entries"]:
        if not isinstance(item, Mapping):
            raise LintError(f"{path.name}: an entry is not a mapping")
        found.append(entry(item))
    return found


# --- reading text, as RS-WRITE-005's How reads it -------------------------------------------


@dataclass(frozen=True)
class Block:
    """One block of prose: a paragraph, a list item, a table cell or a front-matter value.

    `text` is the block once its list marker, its bold label, its bold marks,
    its backticks and its HTML comments are removed. Each of its characters
    carries its offset in the source, and whether it lies in a code span, in
    quotation marks or in markup: a link's target, a bare URL or an HTML
    entity. A link definition is a block of its own, which only a link's check
    reads.
    """

    text: str
    offsets: tuple[int, ...]
    code: tuple[bool, ...]
    quoted: tuple[bool, ...]
    markup: tuple[bool, ...]
    cell: bool = False
    definition: bool = False

    def view(self, exceptions: frozenset[str], *, hide_markup: bool = False) -> str:
        """The text with the parts an entry does not read blanked out, and with
        `hide_markup` the markup too.

        A count reads markup as the How reads any token. A pattern does not, so a
        URL or an entity holds no semicolon.
        """
        hide_code, hide_quotes = "code" in exceptions, "quotes" in exceptions
        return "".join(
            " "
            if (hide_markup and self.markup[i])
            or (hide_code and self.code[i])
            or (hide_quotes and self.quoted[i])
            else char
            for i, char in enumerate(self.text)
        )


@dataclass(frozen=True)
class Unit:
    """A run of a block's text: `start` and `end` index the block's text."""

    start: int
    end: int
    words: int


_LIST_MARKER = r"(?:[-*+]|\d{1,9}[.)])"
_FENCE_OPEN = re.compile(rf"^\s*(?:{_LIST_MARKER}\s+)?(`{{3,}}|~{{3,}})")
_FENCE_CLOSE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
_HEADING = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
_SETEXT_UNDERLINE = re.compile(r"^\s{0,3}(=+|-{2,})\s*$")
_ITEM = re.compile(rf"^(\s*){_LIST_MARKER}(\s+|$)")
_THEMATIC_BREAK = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_QUOTE_PREFIX = re.compile(r"^\s{0,3}(>\s?)+")
_TABLE_ROW = re.compile(r"^\s*\|")
# A link definition: a label that is no footnote's, its target, and an optional quoted title.
_LINK_DEFINITION = re.compile(
    r"^\s{0,3}\[(?!\^)[^\]]+\]:\s*(\S+)(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*$"
)
_HTML_LINE = re.compile(r"^\s*<[^>]*>\s*$")
_DELIMITER_CELL = re.compile(r"^\s*:?-+:?\s*$")
_NO_PROSE = (_HEADING, _THEMATIC_BREAK, _HTML_LINE)
_ENDS = ".?!"


def markdown_blocks(text: str) -> list[Block]:
    """The blocks of prose of a Markdown text, in order.

    - **No prose:** fenced code, headings (a setext heading's text included),
      thematic breaks, HTML comments and lines that are one HTML tag. A fence
      closes on a bare fence of its own character, at least as long as it, in
      the same block quote or outside any. The end of a block quote closes a
      fence opened in it.
    - **Blocks:** a blank line ends a block, and so does the start of a block
      quote. A list marker starts one. Each table cell is a block of its own,
      and so is each link definition.
    - **Block quotes:** a line is read without its `>` marks, and the text of a
      block quote is quoted. An unquoted line that goes on from a quoted one
      stays in its block.
    """
    blocks: list[Block] = []
    current: list[tuple[int, int]] = []
    paragraph = False  # the current block opened as a paragraph, not as a list item
    quoted = False

    def flush() -> None:
        if current:
            blocks.append(block_of(text, current, quoted=quoted))
            current.clear()

    fence: str | None = None
    fence_quoted = False  # the fence opened inside a block quote, which closes it too
    in_comment = False
    offset = 0
    for line in text.split("\n"):
        start, end = offset, offset + len(line)
        offset = end + 1
        if in_comment:
            in_comment = "-->" not in line
            continue
        quote = _QUOTE_PREFIX.match(line)
        column = quote.end() if quote is not None else 0
        rest = line[column:]
        if fence is not None and fence_quoted and quote is None:
            fence = None  # the block quote ended, and its fence with it: read this line
        if fence is not None:
            close = _FENCE_CLOSE.match(rest if fence_quoted else line)
            if close is not None and close.group(1).startswith(fence):
                fence = None
            continue
        opened = _FENCE_OPEN.match(rest)
        if opened is not None:
            flush()
            fence, fence_quoted = opened.group(1), quote is not None
            continue
        if rest.lstrip().startswith("<!--"):
            flush()
            in_comment = "-->" not in line
            continue
        if current and quote is not None and not quoted:
            flush()  # a block quote interrupts a paragraph or a list item
        if current and paragraph and quoted == (quote is not None):
            if _SETEXT_UNDERLINE.match(rest):
                current.clear()  # the paragraph was a setext heading's text
                continue
        if not rest.strip() or any(p.match(rest) for p in _NO_PROSE):
            flush()
        elif _TABLE_ROW.match(rest):
            flush()
            for cell in _table_cells(text, start + column, end):
                blocks.append(block_of(text, [cell], quoted=quote is not None, cell=True))
        elif _LINK_DEFINITION.match(rest):
            flush()
            blocks.append(block_of(text, [(start + column, end)], definition=True))
        elif (item := _ITEM.match(rest)) is not None:
            flush()
            current.append((start + column + item.end(), end))
            paragraph, quoted = False, quote is not None
        else:
            if not current:
                paragraph, quoted = True, quote is not None
            current.append((start + column + len(rest) - len(rest.lstrip()), end))
    flush()
    return blocks


def _table_cells(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Each cell of a table row as `(start, end)` in `text`, split at each `|` outside code."""
    row = text[start:end]
    bars: list[int] = []
    code_run = 0
    i = 0
    while i < len(row):
        if row[i] == "`":
            run = len(row) - len(row[i:].lstrip("`"))
            code_run = run if code_run == 0 else (0 if code_run == run else code_run)
            i += run
            continue
        if row[i] == "\\":
            i += 2
            continue
        if row[i] == "|" and code_run == 0:
            bars.append(i)
        i += 1
    cells: list[tuple[int, int]] = []
    for left, right in zip([-1, *bars], [*bars, len(row)], strict=True):
        cell = row[left + 1 : right]
        if not cell.strip() or _DELIMITER_CELL.match(cell):
            continue
        lead = len(cell) - len(cell.lstrip())
        trail = len(cell) - len(cell.rstrip())
        cells.append((start + left + 1 + lead, start + right - trail))
    return cells


# A link's target with its optional title, from the `(` after the text to the `)`.
_LINK_TARGET = re.compile(r"\]\([^)\s]+(?:\s+\"[^\"]*\")?\)")
# A bare URL, ending before trailing punctuation as an autolink does, so a sentence's own
# full stop or semicolon after it is prose.
_BARE_URL = re.compile(r"<?[A-Za-z][A-Za-z0-9+.-]*://[^\s<>)\]]*[^\s<>)\].,;:!?'\"*_~]>?")
# An HTML entity: a number, or a name HTML defines (`html.entities.html5`).
_ENTITY_NAMES = "|".join(
    sorted((name[:-1] for name in html5 if name.endswith(";")), key=len, reverse=True)
)
_ENTITY = re.compile(rf"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|(?:{_ENTITY_NAMES}));")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def block_of(
    text: str,
    ranges: Sequence[tuple[int, int]],
    *,
    quoted: bool = False,
    cell: bool = False,
    definition: bool = False,
) -> Block:
    """The block whose lines are `ranges` of `text`, read inline as the How reads it.

    - Backticks are removed, and the characters between a pair of equal runs
      are a code span.
    - An HTML comment is removed. A link's target, a bare URL and an HTML
      entity outside code are markup, and so is the whole of a link definition.
    - A bold label opening the block is removed: bold text that ends in a
      colon, inside its marks or right after them.
    - Under a label that opens "Breaks the rule", the quoted example is removed:
      from the first quotation mark after the label to the last.
    - Bold marks outside code and markup are removed.
    - Text between paired quotation marks outside code and markup is quoted:
      straight marks paired in turn, and curly marks open and close. With
      `quoted`, a block quote's, the whole block is.
    """
    chars: list[str] = []
    offsets: list[int] = []
    for index, (start, end) in enumerate(ranges):
        if index:
            chars.append("\n")
            offsets.append(ranges[index - 1][1])
        chars.extend(text[start:end])
        offsets.extend(range(start, end))
    raw = "".join(chars)
    size = len(raw)
    removed = [False] * size
    code = [False] * size
    _mark_code(raw, removed, code)
    markup = [definition] * size
    _mark(_HTML_COMMENT, raw, removed, code)
    for pattern in (_LINK_TARGET, _BARE_URL, _ENTITY):
        _mark(pattern, raw, markup, code)
    label_end = _mark_label(raw, removed, code)
    _mark_bold(raw, removed, code, markup)
    marks = [True] * size if quoted else _quoted(raw, code, markup)
    kept = [i for i in range(label_end, size) if not removed[i]]
    return Block(
        text="".join(raw[i] for i in kept),
        offsets=tuple(offsets[i] for i in kept),
        code=tuple(code[i] for i in kept),
        quoted=tuple(marks[i] for i in kept),
        markup=tuple(markup[i] for i in kept),
        cell=cell,
        definition=definition,
    )


def _mark(pattern: re.Pattern[str], raw: str, flags: list[bool], code: list[bool]) -> None:
    """Flag each match of `pattern` that opens outside code and outside what is flagged."""
    for match in pattern.finditer(raw):
        if not code[match.start()] and not flags[match.start()]:
            flags[match.start() : match.end()] = [True] * (match.end() - match.start())


def _run_length(raw: str, at: int, char: str) -> int:
    return len(raw) - at - len(raw[at:].lstrip(char))


def _mark_code(raw: str, removed: list[bool], code: list[bool]) -> None:
    i = 0
    while i < len(raw):
        if raw[i] != "`":
            i += 1
            continue
        run = _run_length(raw, i, "`")
        close = i + run
        while close < len(raw):
            if raw[close] == "`":
                found = _run_length(raw, close, "`")
                if found == run:
                    break
                close += found
            else:
                close += 1
        for j in range(i, i + run):
            removed[j] = True
        if close >= len(raw):  # no closing run: the backticks are removed, nothing is code
            i += run
            continue
        for j in range(i, close + run):
            code[j] = True
        for j in range(close, close + run):
            removed[j] = True
        i = close + run


def _mark_label(raw: str, removed: list[bool], code: list[bool]) -> int:
    """Mark a bold label opening the block, and a broken rule's quoted example under it.

    Returns the index the block's prose starts at, past the label.
    """
    lead = len(raw) - len(raw.lstrip())
    if not raw.startswith("**", lead) or code[lead]:
        return 0
    close = raw.find("**", lead + 2)
    if close <= lead + 2:
        return 0
    inner = raw[lead + 2 : close]
    if inner.rstrip().endswith(":"):
        end = close + 2
    elif raw.startswith(":", close + 2):
        end = close + 3
    else:
        return 0
    if inner.strip().startswith(BROKEN_EXAMPLE):
        marks = [i for i in range(end, len(raw)) if raw[i] in '"“”' and not code[i]]
        if len(marks) >= 2:
            for j in range(marks[0], marks[-1] + 1):
                removed[j] = True
    return end


def _mark_bold(raw: str, removed: list[bool], code: list[bool], markup: list[bool]) -> None:
    i = 0
    while i < len(raw) - 1:
        if not code[i] and not markup[i] and raw[i : i + 2] in ("**", "__"):
            removed[i] = removed[i + 1] = True
            i += 2
        else:
            i += 1


def _quoted(raw: str, code: list[bool], markup: list[bool]) -> list[bool]:
    quoted = [False] * len(raw)
    straight: int | None = None
    curly: int | None = None
    for i, char in enumerate(raw):
        if code[i] or markup[i]:
            continue
        if char == '"':
            if straight is None:
                straight = i
            else:
                quoted[straight : i + 1] = [True] * (i + 1 - straight)
                straight = None
        elif char == "“":
            curly = i
        elif char == "”" and curly is not None:
            quoted[curly : i + 1] = [True] * (i + 1 - curly)
            curly = None
    return quoted


def is_word(token: str) -> bool:
    """A token holds a letter or a digit (RS-WRITE-005's How)."""
    return any(char.isalnum() for char in token)


def word_count(text: str) -> int:
    return sum(1 for token in text.split() if is_word(token))


def sentences(block: Block, view: str) -> list[Unit]:
    """The sentences of a block, each with its words; a run holding no word is none.

    A sentence ends at `.`, `?` or `!` before a space or the block's end, never
    inside a code span. The block's end ends the last.
    """
    found: list[Unit] = []
    start = 0
    for i, char in enumerate(view):
        if char in _ENDS and not block.code[i] and (i + 1 == len(view) or view[i + 1].isspace()):
            found.append(Unit(start, i + 1, word_count(view[start : i + 1])))
            start = i + 1
    found.append(Unit(start, len(view), word_count(view[start:])))
    return [unit for unit in found if unit.words]


# --- the sources of an artefact --------------------------------------------------------------


@dataclass(frozen=True)
class Source:
    """Text read from one file, and the file line each part of it is on.

    - `text`: Markdown, read in blocks; or, with `marks`, the front-matter
      values, one a line, each a block of its own.
    - `first_line`: for Markdown, the file line the text opens on.
    - `marks`: for front-matter values, `(offset, line)` pairs in order: the
      text from each offset on lies on that file line.
    """

    text: str
    first_line: int = 1
    marks: tuple[tuple[int, int], ...] | None = None

    def line(self, offset: int) -> int:
        if self.marks is None:
            return self.first_line + self.text.count("\n", 0, offset)
        index = bisect_right([at for at, _line in self.marks], offset) - 1
        return self.marks[max(index, 0)][1]

    def blocks(self) -> list[Block]:
        if self.marks is None:
            return markdown_blocks(self.text)
        found: list[Block] = []
        offset = 0
        for line in self.text.split("\n"):
            found.append(block_of(self.text, [(offset, offset + len(line))]))
            offset += len(line) + 1
        return found


def front_matter_values(front_matter: str, key: str | None = None, first_line: int = 2) -> Source:
    """The text values of a front matter, or of its entry `key`, outside the container.

    The methodology's container (`pkit`) holds answers a person decided or a
    reviewer checked, which RS-WRITE-013 keeps from rewriting for style. Keys,
    and values that are not text, are not read. A rule-set file's entries sit
    under its `rules`. `first_line` is the file line the front matter opens on.
    """
    try:
        node = YAML(typ="safe", pure=True).compose(front_matter)
    except YAMLError as exc:
        raise LintError(f"the front matter does not parse: {exc}") from exc
    if key is not None:
        node = _entry_node(node, key)
    values: list[list[tuple[str, int]]] = []
    _walk_values(node, first_line, values)
    text: list[str] = []
    marks: list[tuple[int, int]] = []
    offset = 0
    for pieces in values:
        if text:
            offset += 1  # the line break between two values
        for index, (piece, line) in enumerate(pieces):
            if index:
                text.append(" ")
                offset += 1
            marks.append((offset, line))
            text.append(piece)
            offset += len(piece)
        text.append("\n")
    return Source("".join(text).removesuffix("\n"), marks=tuple(marks))


def _value_of(node: Node | None, key: str) -> Node | None:
    if isinstance(node, MappingNode):
        for name, value in node.value:
            if isinstance(name, ScalarNode) and name.value == key:
                return value
    return None


def _entry_node(node: Node | None, key: str) -> Node | None:
    if _value_of(node, "rule-set") is not None:
        return _value_of(_value_of(node, "rules"), key)
    return _value_of(node, key)


def _walk_values(node: Node | None, first_line: int, found: list[list[tuple[str, int]]]) -> None:
    """Each text value, as its pieces and the file line each piece is on.

    A literal block (`|`) keeps a piece for each of its lines. Any other value
    is one piece, on the line its text opens on: the line after the marker for
    a folded block (`>`).
    """
    if isinstance(node, MappingNode):
        for name, value in node.value:
            if not (isinstance(name, ScalarNode) and name.value == CONTAINER):
                _walk_values(value, first_line, found)
    elif isinstance(node, SequenceNode):
        for item in node.value:
            _walk_values(item, first_line, found)
    elif isinstance(node, ScalarNode) and node.tag.endswith(":str") and str(node.value).strip():
        value = str(node.value)
        line = first_line + node.start_mark.line
        if node.style == "|":
            lines = value.rstrip("\n").split("\n")
            found.append([(piece, line + 1 + index) for index, piece in enumerate(lines)])
        else:
            found.append([(" ".join(value.split("\n")).strip(), line + (node.style == ">"))])


@dataclass(frozen=True)
class Sources:
    """An artefact's text: its front-matter values and its Markdown."""

    values: Source
    body: Source


EMPTY = Source("", marks=())


def document_sources(text: str) -> Sources:
    """A document's front-matter values and its body."""
    text = universal_newlines(text)
    front_matter, body = split_front_matter(text)
    first = text.count("\n") - body.count("\n") + 1
    values = EMPTY if front_matter is None else front_matter_values(front_matter)
    return Sources(values, Source(body, first_line=first))


def entry_sources(text: str, key: str, span: Mapping[str, int] | None) -> Sources:
    """A collection entry's values, read from its file's front matter, and its section."""
    text = universal_newlines(text)
    front_matter, _body = split_front_matter(text)
    values = EMPTY if front_matter is None else front_matter_values(front_matter, key)
    if span is None:
        return Sources(values, Source(""))
    lines = text.split("\n")[span["first_line"] - 1 : span["last_line"]]
    return Sources(values, Source("\n".join(lines), first_line=span["first_line"]))


# --- the text a change adds -----------------------------------------------------------------


_TOKEN = re.compile(r"\S+")


def added_mask(base: str | None, head: str) -> bytearray:
    """For each character of `head`, 1 when it is in a token the change adds or moves.

    Lines are compared first, then the tokens of each run of lines that
    differs, so a paragraph written on one line is compared word by word. A
    token in a run of lines the base does not hold is added. A token moved
    within the text is added where the diff inserts it. Without a base,
    everything is added.
    """
    if base is None:
        return everything(head)
    mask = bytearray(len(head))
    base_lines, head_lines = base.split("\n"), head.split("\n")
    starts = [0]
    for line in head_lines:
        starts.append(starts[-1] + len(line) + 1)
    lines = SequenceMatcher(None, base_lines, head_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in lines.get_opcodes():
        if tag == "equal" or j1 == j2:
            continue
        offset = starts[j1]
        head_chunk = "\n".join(head_lines[j1:j2])
        head_tokens = list(_TOKEN.finditer(head_chunk))
        base_tokens = [m.group() for m in _TOKEN.finditer("\n".join(base_lines[i1:i2]))]
        words = SequenceMatcher(None, base_tokens, [m.group() for m in head_tokens], autojunk=False)
        for word_tag, _a1, _a2, b1, b2 in words.get_opcodes():
            if word_tag in ("insert", "replace"):
                for match in head_tokens[b1:b2]:
                    mask[offset + match.start() : offset + match.end()] = b"\x01" * len(
                        match.group()
                    )
    return mask


def everything(text: str) -> bytearray:
    return bytearray(b"\x01" * len(text))


# --- findings -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One break the lint found: where, which rule, and what."""

    path: str
    line: int
    rule: str
    message: str
    location: str = ""

    def render(self) -> str:
        """`<path>:<line>  <rule>: <message>`, the rule followed by `in <id>` for an entry."""
        entry_id = self.location.removeprefix(f"{self.path}#")
        within = f" in {entry_id}" if entry_id not in ("", self.location) else ""
        return f"{self.path}:{self.line}  {self.rule}{within}: {self.message}"


Exists = Callable[[str], bool]


def _excerpt(text: str, words: int = 8) -> str:
    """The opening words of a unit, quoted, to find it by."""
    tokens = text.split()
    shown = " ".join(tokens[:words])
    return f'"{shown}{" …" if len(tokens) > words else ""}"'


def _context(text: str, start: int, end: int) -> str:
    """A match with up to four words on either side of it, quoted, to find it by."""
    before = re.search(r"(?:\S+\s+){0,4}\S*$", text[:start])
    after = re.match(r"\S*(?:\s+\S+){0,4}", text[end:])
    shown = (before.group() if before else "") + text[start:end] + (after.group() if after else "")
    return f'"{" ".join(shown.split())}"'


def check_source(
    entries: Sequence[Entry],
    source: Source,
    mask: bytearray,
    path: str,
    exists: Exists,
    location: str = "",
) -> list[Finding]:
    """The findings of `entries` on one source, kept where their unit holds added text.

    `mask` marks the added text (`added_mask`). A finding names the line its
    unit's first word is on.
    """
    found: list[Finding] = []
    for block in source.blocks():
        for item in entries:
            if block.cell and "cells" in item.exceptions:
                continue
            for start, end, message in _breaks(item, block, path, exists):
                if not any(mask[offset] for offset in block.offsets[start:end]):
                    continue
                first = next((i for i in range(start, end) if not block.text[i].isspace()), start)
                line = source.line(block.offsets[first])
                found.append(Finding(path, line, item.rule, message, location or path))
    return found


def _breaks(item: Entry, block: Block, path: str, exists: Exists) -> Iterable[tuple[int, int, str]]:
    """Each break of one entry in one block: `(start, end, message)`, indexing the block.

    A link definition is read by a link's check alone.
    """
    if item.type == "link-resolves":
        yield from _links(item, block, path, exists)
        return
    if block.definition:
        return
    view = block.view(item.exceptions, hide_markup=item.type != "count")
    if item.type == "count":
        yield from _count(item, block, view)
    elif item.type == "forbid":
        name = item.fields.get("name")
        for match in re.finditer(item.fields["pattern"], view):
            if match.end() > match.start():
                what = name or f'"{match.group()}"'
                context = _context(block.text, match.start(), match.end())
                yield match.start(), match.end(), f"{what}: {context}"
    else:
        for word, replacement in item.fields["replace"].items():
            pattern = r"(?<![\w-])" + r"\s+".join(map(re.escape, word.split())) + r"(?![\w-])"
            for match in re.finditer(pattern, view, re.IGNORECASE):
                yield match.start(), match.end(), f'"{match.group()}": write "{replacement}"'


def _links(item: Entry, block: Block, path: str, exists: Exists) -> Iterable[tuple[int, int, str]]:
    """Each link of a block whose target does not resolve; a link in code is none."""
    linkable = block.view(item.exceptions | {"code"})
    for match in (_LINK_DEFINITION if block.definition else _LINK).finditer(linkable):
        target = match.group(1)
        if not _resolves(target, path, exists):
            yield match.start(), match.end(), f'the link target "{target}" does not exist'


def _count(item: Entry, block: Block, view: str) -> Iterable[tuple[int, int, str]]:
    limit: int = item.fields["max"]
    counted = sentences(block, view)
    if item.fields["in"] == "sentence":
        for unit in counted:
            if unit.words > limit:
                excerpt = _excerpt(block.text[unit.start : unit.end])
                yield (
                    unit.start,
                    unit.end,
                    f"a sentence of {unit.words} words, over {limit}: {excerpt}",
                )
        return
    if item.fields["count"] == "words":
        total, what = sum(unit.words for unit in counted), "words"
    else:
        total, what = len(counted), "sentences"
    if total > limit:
        yield 0, len(view), f"a paragraph of {total} {what}, over {limit}: {_excerpt(block.text)}"


# A Markdown link or image, `[text](target)` with an optional title (refs.LINK_RE's shape).
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _resolves(target: str, path: str, exists: Exists) -> bool:
    """Whether a link's target exists: a URL, a fragment and a placeholder are not checked.

    A relative target is read from the linking file's folder, and one opening
    with `/` from the repository's root. The root itself resolves, and a target
    above it does not.
    """
    if _SCHEME.match(target) or target.startswith("//") or any(c in target for c in "<>{}"):
        return True
    target = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return True
    base = PurePosixPath("/") if target.startswith("/") else PurePosixPath("/", path).parent
    parts: list[str] = []
    for part in (base / target.lstrip("/")).parts[1:]:
        if part == "..":
            if not parts:
                return False
            parts.pop()
        elif part != ".":
            parts.append(part)
    return not parts or exists("/".join(parts))


def file_exists(root: Path = ROOT) -> Exists:
    """Whether a repository-relative path is a file or folder on disk under `root`."""
    return lambda rel: (root / rel).exists()


def tree_exists(files: Iterable[str]) -> Exists:
    """Whether a repository-relative path is a file a tree holds, or a folder holding one."""
    held = set(files)
    folders = {str(parent) for rel in held for parent in PurePosixPath(rel).parents}
    return lambda rel: rel.rstrip("/") in held or rel.rstrip("/") in folders


# --- the two ways in ------------------------------------------------------------------------


def lint_text(
    text: str,
    entries: Sequence[Entry] | None = None,
    *,
    path: str = "<text>",
    exists: Exists | None = None,
) -> list[Finding]:
    """Every finding in a given text, read whole: its front-matter values and its body.

    The text is read as a document. Every entry applies, `scripts/prose-lint.yaml`'s
    when `entries` is not given. A link resolves from `path` through `exists`, by
    default against the files on disk in this repository.
    """
    chosen = load_entries() if entries is None else list(entries)
    resolves = exists or file_exists()
    sources = document_sources(text)
    found: list[Finding] = []
    for source in (sources.values, sources.body):
        found += check_source(chosen, source, everything(source.text), path, resolves)
    return sorted(found, key=lambda f: f.line)


@dataclass(frozen=True)
class ChangeLint:
    """What the lint found in a change: the base and head it compared, and the findings."""

    base: Mapping[str, Any]
    head: Mapping[str, Any]
    checked: tuple[str, ...]
    findings: tuple[Finding, ...]


def applied_entries(rules: Iterable[Mapping[str, Any]], entries: Sequence[Entry]) -> list[Entry]:
    """The entries whose rule binds, by the `rules` of an artefact in the altered
    document, and declares a part this lint checks."""
    declared: set[str] = set()
    for rule in rules:
        if any(part.get("check") == CHECK for part in rule.get("checks", [])):
            declared.update((rule["rule"], rule["id"]))
    return [item for item in entries if item.rule in declared]


def _read(tree: CommitTree | WorkingTree, path: str) -> str | None:
    data = tree.read_bytes([path]).get(path)
    try:
        return None if data is None else data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LintError(f"{path}: not UTF-8 text: {exc}") from exc


def _read_sources(text: str, side: Mapping[str, Any]) -> Sources:
    try:
        return _sources(text, side)
    except LintError as exc:
        raise LintError(f"{side['location']}: {exc}") from exc


def _sources(text: str, side: Mapping[str, Any]) -> Sources:
    if side["kind"] == "entry":
        return entry_sources(text, side["id"], side["span"])
    return document_sources(text)


def lint_change(
    root: Path = ROOT, base: str | None = None, entries: Sequence[Entry] | None = None
) -> ChangeLint:
    """The findings in the text a change adds or moves, in each artefact the change altered.

    The base is the merge-base of `base`, else `$PKIT_CHECK_BASE`, else the
    default branch, with the working tree, as `pkit rule-sets altered` takes it.
    Raises `LintError` when an artefact cannot be read, and the change check's
    error when the base cannot be compared.
    """
    chosen = load_entries() if entries is None else list(entries)
    document = validators.as_one_run(lambda: rule_set_reading.altered_document(root, base))
    if document["schema_version"] != ALTERED_SCHEMA_VERSION:
        raise LintError(
            f"`pkit rule-sets altered` gives version {document['schema_version']}, "
            f"and the lint reads {ALTERED_SCHEMA_VERSION}"
        )
    head_tree = WorkingTree(root)
    base_tree: CommitTree | None = None
    exists: Exists | None = None
    checked: list[str] = []
    found: list[Finding] = []
    for altered in document["artefacts"]:
        head = altered["head"]
        if head is None:
            continue
        applied = applied_entries(head["rules"], chosen)
        if not applied:
            continue
        head_text = _read(head_tree, head["path"])
        if head_text is None:
            continue
        before = altered["base"]
        base_sources: Sources | None = None
        if before is not None:
            base_tree = base_tree or CommitTree(root, document["base"]["commit"])
            base_text = _read(base_tree, before["path"])
            base_sources = None if base_text is None else _read_sources(base_text, before)
        head_sources = _read_sources(head_text, head)
        exists = exists or tree_exists(head_tree.files())
        checked.append(head["location"])
        for kind in ("values", "body"):
            source: Source = getattr(head_sources, kind)
            old = None if base_sources is None else getattr(base_sources, kind).text
            mask = added_mask(old, source.text)
            found += check_source(applied, source, mask, head["path"], exists, head["location"])
    return ChangeLint(
        base=document["base"],
        head=document["head"],
        checked=tuple(checked),
        findings=tuple(sorted(found, key=lambda f: (f.path, f.line, f.rule))),
    )


def render(lint: ChangeLint) -> str:
    """The lint's report: what it compared, each finding, and a count."""
    base, head = lint.base, lint.head
    state = "the working tree" if head["working_tree"] else f"commit {head['commit'][:12]}"
    lines = [f"Prose lint — base {base['ref']} at {base['commit'][:12]}, head {state}"]
    if base.get("outdated"):
        lines.append(
            "  the base moved on after this branch left it; merge or rebase onto it "
            "for results that hold"
        )
    lines.extend(f"  {finding.render()}" for finding in lint.findings)
    lines.append(
        f"{len(lint.findings)} finding(s) in the text the change adds or moves, "
        f"{len(lint.checked)} artefact(s) checked."
    )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prose_lint.py",
        description="The mechanical parts of the writing rules, in the text a change adds.",
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        help="compare against the merge-base of REF and the working tree "
        "(default: $PKIT_CHECK_BASE, else the default branch)",
    )
    args = parser.parse_args(argv)
    try:
        lint = lint_change(ROOT, args.base)
        report = render(lint)
    except (LintError, click.ClickException) as exc:
        message = exc.format_message() if isinstance(exc, click.ClickException) else str(exc)
        print(f"prose lint: {message}", file=sys.stderr)
        return 2
    except Exception:  # a defect of the lint: exit 2, never 1, which means a finding
        traceback.print_exc()
        print("prose lint: failed with the error above", file=sys.stderr)
        return 2
    print(report, end="")
    return 1 if lint.findings else 0


if __name__ == "__main__":
    sys.exit(main())
