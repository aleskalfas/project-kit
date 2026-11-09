"""An agent's tool access, read from the text of its definition (COR-013 point 7, ADR-086).

An agent's front matter names the tools it is granted (`tools`), the tools it
is withheld (`withheld`), or neither, and never both. This module is the one
reader of that access: the adapters' deploy and runner, the `pkit` command's
validator and any other part that needs a definition's tools call it, and none
reads them itself.

**What it reads.** The two keys, from the front matter's text itself, so no
caller's parser decides what they hold. A front matter holding a top-level
line it cannot read as a key, or a key written twice, is refused. A value is
read as a list, on one line or one entry to a line, or as one string whose
entries are separated by commas outside parentheses. A key with no value holds
no entries, and a value written any other way is refused.

**What it answers.** `tool_access` gives the definition's form and its
entries, each with any argument it carries, or raises `Refused` naming why
the definition is refused. `holds` and `lacks` answer the two readings of
ADR-085 point 2. A function keeps its name and its answer: one whose answer
changes takes a new name, so an older caller never reads a newer answer as
its own (ADR-086 point 5).

**What it leaves to an adapter.** Which tools a harness has, the form its
names take, which withheld entries it can enforce, and its own keys. This
module knows none of them (ADR-086 point 4).

Propagated neutral code at the root of the agents area: sync copies it into
every project, and it imports nothing of the `pkit` command or an adapter.
Standard library only, and readable by Python 3.9, since the agent runner
loads it under the system's Python with nothing installed. A caller loads it
from its file, without adding the area to Python's import path and without
writing bytecode into the tree.
"""

from __future__ import annotations

import re
from typing import NamedTuple

#: The key of each form of tool access (COR-013 point 7): the tools granted,
#: and the tools withheld.
GRANT = "tools"
WITHHOLD = "withheld"
KEYS = (GRANT, WITHHOLD)

#: The front matter and the body of a definition.
_FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*$", re.DOTALL | re.MULTILINE)

#: A top-level key of the front matter, and what follows its colon.
_KEY_LINE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]+(.*))?")

#: An entry: one of the harness's tools, by a name in no harness's form in
#: particular, and at most one argument in parentheses after it.
_ENTRY = re.compile(r"([A-Za-z][A-Za-z0-9_-]*)(?:\((.*)\))?", re.DOTALL)

#: The first characters of a value or an entry the reader does not take as a
#: plain one: YAML's indicators of a mapping, an anchor, an alias, a tag, a
#: block scalar, a directive or a reserved character.
_NOT_PLAIN = tuple("{}&*!|>%@`?")

#: The ways YAML writes a null value: none is a value of tool access.
_NULLS = frozenset({"~", "null", "Null", "NULL"})

#: A control character, which no entry holds.
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class Refused(ValueError):
    """The definition is refused for its tool access; the message says why."""


# The answers are named tuples, not dataclasses: a caller loads this module from
# its file without registering it among Python's modules, and under Python 3.9 a
# dataclass then cannot read its own annotations.


class Entry(NamedTuple):
    """One entry of a tool access: a tool's name, and the argument that narrows it."""

    tool: str
    argument: str | None = None

    def __str__(self) -> str:
        """The entry as a definition writes it, its argument in parentheses."""
        return self.tool if self.argument is None else f"{self.tool}({self.argument})"


class Access(NamedTuple):
    """A definition's tool access.

    `form` is `GRANT` or `WITHHOLD`, or None where the definition names neither,
    and `entries` are the tools it names in the order written.
    """

    form: str | None
    entries: tuple[Entry, ...] = ()

    def names(self, tool: str) -> bool:
        """Whether an entry names *tool*, whatever its argument."""
        return any(entry.tool == tool for entry in self.entries)


def tool_access(text: str) -> Access:
    """The tool access of the definition whose whole text is *text*.

    Raises `Refused`, naming why, where the definition holds both keys, where
    its front matter holds a line the reader cannot read as a key or a key
    written twice, or where a key's value or an entry is written in a way the
    reader does not read.
    """
    match = _FRONT_MATTER.match(text)
    if match is None:
        raise Refused("the definition has no front matter")
    fields = _fields(match.group(1))
    held = [key for key in KEYS if key in fields]
    if len(held) > 1:
        raise Refused(
            f"it names both `{GRANT}` and `{WITHHOLD}`, which would say the same thing "
            "twice and could disagree: keep one (COR-013 point 7)"
        )
    if not held:
        return Access(None)
    key = held[0]
    return Access(key, tuple(_entry(item, key) for item in _items(fields[key], key)))


def holds(access: Access, tool: str) -> bool:
    """Whether a check that the agent holds *tool* holds (ADR-085 point 2).

    It holds where the agent's grant names the tool, or where the agent names
    no grant and does not withhold the tool.
    """
    if access.form == GRANT:
        return access.names(tool)
    return not (access.form == WITHHOLD and access.names(tool))


def lacks(access: Access, tool: str) -> bool:
    """Whether a check that the agent lacks *tool* holds (ADR-085 point 2).

    It holds only where the agent's grant leaves the tool out: a withheld list
    gives every tool it does not name, so it never shows that an agent lacks one.
    """
    return access.form == GRANT and not access.names(tool)


# --- the front matter ------------------------------------------------------------------


def _fields(front_matter: str) -> dict[str, list[str]]:
    """Each top-level key of *front_matter*, with the text after its colon and
    the lines below it."""
    fields: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in front_matter.split("\n"):
        if not line.strip() or line[0] in " \t" or line == "-" or line.startswith("- "):
            if current is not None:
                current.append(line)
            elif line.strip():
                raise Refused(f"its front matter opens with {line!r}, which is not a key")
            continue
        if line.startswith("#"):
            continue
        match = _KEY_LINE.fullmatch(line.rstrip())
        if match is None:
            raise Refused(f"its front matter holds {line!r}, which the reader cannot read as a key")
        key = match.group(1)
        if key in fields:
            raise Refused(f"its front matter writes `{key}` twice")
        current = fields[key] = [match.group(2) or ""]
    return fields


def _content(lines: list[str]) -> list[str]:
    """The lines below a key that hold more than a comment, stripped."""
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def _items(lines: list[str], key: str) -> list[str]:
    """The entries of a key's value, as written, quoted ones unquoted."""
    head, below = lines[0].strip(), _content(lines[1:])
    if not head or head.startswith("#"):
        items: list[str] = []
        for line in below:
            if not (line == "-" or line.startswith("- ")):
                raise Refused(f"`{key}` holds {line!r} in a list, which is not an entry")
            item = _item(line[1:].strip(), key)
            if item is None:
                raise Refused(f"`{key}` holds an empty entry")
            items.append(item)
        return items
    if head.startswith("]") or head.startswith(_NOT_PLAIN):
        raise Refused(f"`{key}` is written as {head!r}, neither a list nor one string")
    if below:
        raise Refused(f"`{key}` goes on over more than one line, which the reader does not read")
    if head.startswith("["):
        return _flow_list(head, key)
    text, tail = _quoted(head, key) if head[0] in "\"'" else (head, "")
    if tail and not tail.startswith("#"):
        raise Refused(f"`{key}` goes on after its closing quote")
    if head[0] not in "\"'":
        text = _without_comment(text)
        if text in _NULLS:
            raise Refused(f"`{key}` is written as null: leave the key with no value, or write `[]`")
    return [part.strip() for part in _split(text, key) if part.strip()]


def _flow_list(head: str, key: str) -> list[str]:
    """The entries of a list written on one line, `[a, b(c, d)]`."""
    parts = _split(head[1:], key, closing="]")
    tail = parts.pop()
    if tail.strip() and not tail.strip().startswith("#"):
        raise Refused(f"`{key}` goes on after its list closes")
    if parts and not parts[-1].strip():
        parts.pop()  # A trailing comma, as YAML admits one.
    items: list[str] = []
    for part in parts:
        item = _item(part.strip(), key)
        if item is None:
            raise Refused(f"`{key}` holds an empty entry")
        items.append(item)
    return items


def _split(text: str, key: str, closing: str | None = None) -> list[str]:
    """*text* split at each comma outside parentheses and quotes.

    With *closing*, the text ends at that character outside them, and what
    follows it is the last part. Raises where a list nests another, or where a
    parenthesis or a quote is left open.
    """
    parts: list[str] = []
    start, depth, quote, index = 0, 0, "", 0
    while index < len(text):
        char = text[index]
        if quote:
            doubled = char == quote == "'" and text[index + 1 : index + 2] == "'"
            if doubled or (char == "\\" and quote == '"'):
                index += 1  # A quote written twice, or an escaped character.
            elif char == quote:
                quote = ""
        elif char in "\"'" and not text[start:index].strip():
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise Refused(f"`{key}` closes a parenthesis it never opened")
        elif depth == 0 and char in "[{":
            raise Refused(f"`{key}` nests a collection, which is not an entry")
        elif depth == 0 and char == ",":
            parts.append(text[start:index])
            start = index + 1
        elif depth == 0 and closing is not None and char == closing:
            parts.append(text[start:index])
            parts.append(text[index + 1 :])
            return parts
        index += 1
    if quote:
        raise Refused(f"`{key}` has no closing quote")
    if depth:
        raise Refused(f"`{key}` leaves a parenthesis open")
    if closing is not None:
        raise Refused(f"`{key}` is not a closed list: a list is written on one line")
    parts.append(text[start:])
    return parts


def _item(text: str, key: str) -> str | None:
    """One entry as written in a list, unquoted, its comment left out; None when empty."""
    if not text or text.startswith("#"):
        return None
    if text[0] in "\"'":
        value, tail = _quoted(text, key)
        if tail and not tail.startswith("#"):
            raise Refused(f"`{key}` goes on after an entry's closing quote")
        return value
    if text.startswith(_NOT_PLAIN) or text[0] in "[]":
        raise Refused(f"`{key}` holds {text!r}, which is not an entry")
    return _without_comment(text)


def _quoted(text: str, key: str) -> tuple[str, str]:
    """A quoted value at the start of *text*, unquoted, and what follows it.

    A single-quoted value writes its quote twice; a double-quoted one escapes
    only a backslash or its quote.
    """
    quote, index = text[0], 1
    value: list[str] = []
    while index < len(text):
        char = text[index]
        if quote == "'" and char == "'":
            if text[index + 1 : index + 2] == "'":
                value.append("'")
                index += 2
                continue
            return "".join(value), text[index + 1 :].strip()
        if quote == '"' and char == "\\":
            escaped = text[index + 1 : index + 2]
            if escaped not in ('"', "\\"):
                raise Refused(
                    f"`{key}` holds the escape \\{escaped}, which the reader does not read"
                )
            value.append(escaped)
            index += 2
            continue
        if quote == '"' and char == '"':
            return "".join(value), text[index + 1 :].strip()
        value.append(char)
        index += 1
    raise Refused(f"`{key}` has no closing quote")


def _without_comment(text: str) -> str:
    """*text* without a comment that follows it, as YAML reads a plain value."""
    return re.split(r"[ \t]#", text, maxsplit=1)[0].rstrip()


def _entry(text: str, key: str) -> Entry:
    """One entry read as a tool's name and its argument."""
    match = _ENTRY.fullmatch(text)
    if match is None or _CONTROL.search(text):
        raise Refused(
            f"`{key}` names {text!r}, which is not a tool's name with at most one argument in "
            "parentheses after it"
        )
    name, argument = match.group(1), match.group(2)
    if argument is not None and not argument.strip():
        raise Refused(f"`{key}` names {text!r}, whose parentheses hold no argument")
    return Entry(name, argument)
