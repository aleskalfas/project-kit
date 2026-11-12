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
ADR-085 point 2, and `gives_nothing_more` whether one tool access gives no
tool another does not (ADR-087 point 4). A function keeps its name and its
answer: one whose answer changes takes a new name, so an older caller never
reads a newer answer as its own (ADR-086 point 5).

**What an adapter declares.** Which tools a harness has, the forms its names
take, which withheld entries it can enforce, and its own keys. This module
knows none of them: each adapter that deploys agents declares them as data, in
`tool-access.json` in its folder (ADR-086 point 4). `read_declaration` reads
one, and `harness_refusal` makes the adapter's refusals against it, so the
adapter's deploy and runner, which give it their own adapter's declaration, and
the reference validator, which gives it each one, refuse alike (point 6).

Propagated neutral code at the root of the agents area: sync copies it into
every project, and it imports nothing of the `pkit` command or an adapter.
Standard library only, and readable by Python 3.9, since the agent runner
loads it under the system's Python with nothing installed. A caller loads it
from its file, without adding the area to Python's import path and without
writing bytecode into the tree.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Collection
from pathlib import Path
from typing import Any, NamedTuple

#: The key of each form of tool access (COR-013 point 7): the tools granted,
#: and the tools withheld.
GRANT = "tools"
WITHHOLD = "withheld"
KEYS = (GRANT, WITHHOLD)

#: What each form says of the tools it names.
_VERB = {GRANT: "granted", WITHHOLD: "withheld"}

#: An adapter's declaration of tool access: a data file of this name in the
#: adapter's folder, whose presence is the declaration (ADR-086 point 4).
DECLARATION = "tool-access.json"

#: The version of a declaration's shape this reader reads. A change of shape
#: takes a new version, and ships its migration (ADR-086 point 4).
DECLARATION_VERSION = 1

#: The keys of a declaration. `$schema` points an editor at its schema,
#: `.pkit/schemas/tool-access.schema.json`; every other key is required.
_DECLARATION_KEYS = (
    "$schema",
    "schema_version",
    "harness",
    "keys",
    "name_forms",
    "known_tools",
    "withheld_admits",
)

#: The keys of a shape a declaration gives, each required.
_SHAPE_KEYS = ("pattern", "argument", "description")

#: The front matter and the body of a definition.
_FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*$", re.DOTALL | re.MULTILINE)

#: A top-level key of a front matter.
_KEY = r"[A-Za-z_][A-Za-z0-9_-]*"

#: A top-level key of the front matter, and what follows its colon.
_KEY_LINE = re.compile(rf"({_KEY}):(?:[ \t]+(.*))?")

#: A tool's name in no harness's form in particular: the reader's grammar of a
#: name, which bounds every form a declaration gives.
_NAME = r"[A-Za-z][A-Za-z0-9_-]*"

#: An entry: one of the harness's tools, by a name in the reader's grammar, and
#: at most one argument in parentheses after it.
_ENTRY = re.compile(rf"({_NAME})(?:\((.*)\))?", re.DOTALL)

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


class BadDeclaration(ValueError):
    """An adapter's declaration of tool access the reader cannot read; the message says why."""


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


class Shape(NamedTuple):
    """A shape an entry may take, as a declaration gives it: a tool's name its
    pattern matches whole, whether an argument may narrow the tool, and the
    shape in words, for a refusal to name."""

    pattern: re.Pattern[str]
    argument: bool
    description: str

    def names(self, tool: str) -> bool:
        """Whether *tool* is a name of this shape."""
        return self.pattern.fullmatch(tool) is not None

    def takes(self, entry: Entry) -> bool:
        """Whether *entry* takes this shape: its tool's name, and its argument
        only where the shape admits one."""
        return self.names(entry.tool) and (entry.argument is None or self.argument)


class Declaration(NamedTuple):
    """An adapter's declaration of tool access (ADR-086 point 4).

    `harness` names the harness in a refusal's words, and `keys` gives the
    harness's key for each form, `GRANT` and `WITHHOLD`. `name_forms` are the
    forms a tool's name may take, `known_tools` the harness's built-in tools by
    name, and `withheld_admits` the shapes of the withheld entries the harness
    was measured to withhold, which may be none.
    """

    harness: str
    keys: dict[str, str]
    name_forms: tuple[Shape, ...]
    known_tools: frozenset[str]
    withheld_admits: tuple[Shape, ...]


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


def gives_nothing_more(earlier: Access, current: Access) -> bool:
    """Whether *earlier* gives no tool that *current* does not give.

    The question a deploy asks before it keeps a copy written from an earlier text
    of the agent's definition, while the current text is refused for a cause other
    than its tool access (COR-013 point 8, ADR-087 point 4). Each entry is read
    whole with its argument: one without an argument covers its tool whole, and one
    with an argument covers only itself. So a current entry with an argument never
    covers an earlier one without it. Where a withheld list meets a grant, a granted
    entry and a withheld one of the same tool are read as overlapping, whatever
    their arguments.
    """
    if current.form is None:
        return True
    if current.form == GRANT:
        return earlier.form == GRANT and all(
            _covered(entry, current.entries) for entry in earlier.entries
        )
    if earlier.form is None:
        return not current.entries
    if earlier.form == WITHHOLD:
        return all(_covered(entry, earlier.entries) for entry in current.entries)
    withheld = {entry.tool for entry in current.entries}
    return not any(entry.tool in withheld for entry in earlier.entries)


def _covered(entry: Entry, entries: tuple[Entry, ...]) -> bool:
    """Whether *entries* name *entry* whole, or its tool with no argument."""
    return any(
        other == entry or (other.tool == entry.tool and other.argument is None) for other in entries
    )


# --- an adapter's declaration (ADR-086 point 4) ----------------------------------------


def declaration_path(adapter_folder: str | os.PathLike[str]) -> Path:
    """Where the adapter whose folder is *adapter_folder* keeps its declaration."""
    return Path(adapter_folder) / DECLARATION


def read_declaration(adapter_folder: str | os.PathLike[str]) -> Declaration | None:
    """The declaration of tool access of the adapter whose folder is
    *adapter_folder*, or None where it declares none.

    Raises `BadDeclaration`, naming why, where the declaration cannot be read:
    a file that is not JSON or writes a key twice, a schema version or a key
    the reader does not know, a key missing, or a value not of its shape.
    """
    path = declaration_path(adapter_folder)
    if not os.path.lexists(path):
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BadDeclaration(f"it cannot be read ({exc})") from None
    try:
        document = json.loads(text, object_pairs_hook=_unique_keys)
    except json.JSONDecodeError as exc:
        raise BadDeclaration(f"it is not JSON ({exc})") from None
    return _declaration(document)


def harness_refusal(
    access: Access, fields: Collection[str], declaration: Declaration
) -> str | None:
    """Why the declaration's harness cannot enforce or translate *access*, or
    None where it can (ADR-086 point 4).

    *access* is `tool_access`'s answer for a definition, and *fields* the
    top-level keys of its front matter. Refused are the harness's own key held
    beside the form that translates to it; a withheld name the declaration does
    not know as one of the harness's built-in tools; a tool's name in no form
    the declaration gives, or narrowed by an argument where its form takes none;
    and a withheld entry the declaration does not admit.
    """
    if access.form is None:
        return None
    own = declaration.keys[access.form]
    if own != access.form and own in fields:
        return (
            f"it holds {declaration.harness}'s own key `{own}` beside `{access.form}`: "
            f"name the tools it is {_VERB[access.form]} in `{access.form}` alone"
        )
    for entry in access.entries:
        problem = _harness_problem(entry, access.form, declaration)
        if problem is not None:
            return f"`{access.form}` names `{entry}`, {problem}"
    return None


def _harness_problem(entry: Entry, form: str, declaration: Declaration) -> str | None:
    """Why the declaration's harness cannot enforce or translate *entry* of *form*."""
    harness = declaration.harness
    withheld = form == WITHHOLD
    if withheld and entry.tool not in declaration.known_tools:
        return (
            f"which this adapter does not know as one of {harness}'s built-in tools, and a "
            "withheld name it does not know would withhold nothing: check its spelling, or "
            f"grant the tools instead (the adapter's {DECLARATION} lists the names it knows)"
        )
    forms = [shape for shape in declaration.name_forms if shape.names(entry.tool)]
    if not forms:
        taken = _said(declaration.name_forms) or "its adapter declares no form a name takes"
        return f"a name in a form {harness} does not take: {taken}"
    if entry.argument is not None and not any(shape.argument for shape in forms):
        return f"and {harness} takes no argument after {forms[0].description}"
    admits = declaration.withheld_admits
    if not withheld or any(shape.takes(entry) for shape in admits):
        return None
    if not admits:
        return (
            f"and {harness} was not measured to withhold any tool, so its adapter admits no "
            "withheld entry: grant the tools instead"
        )
    whole = entry.argument is not None and any(shape.takes(Entry(entry.tool)) for shape in admits)
    fix = f"withhold `{entry.tool}` whole, or grant" if whole else "grant"
    return f"and {harness} was measured to withhold only {_said(admits)}: {fix} the tools instead"


def _said(shapes: tuple[Shape, ...]) -> str:
    """*shapes* in words, one after another."""
    return ", or ".join(shape.description for shape in shapes)


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """A JSON object's keys and values, refused where one key is written twice."""
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise BadDeclaration(f"it writes the key {key!r} twice")
        document[key] = value
    return document


def _declaration(document: Any) -> Declaration:
    """The declaration *document* holds, read as JSON."""
    if not isinstance(document, dict):
        raise BadDeclaration("it is not a JSON object")
    version = document.get("schema_version")
    if isinstance(version, bool) or version != DECLARATION_VERSION:
        raise BadDeclaration(
            f"its schema version is {json.dumps(version)}, and this reader reads version "
            f"{DECLARATION_VERSION} only"
        )
    unknown = sorted(set(document) - set(_DECLARATION_KEYS))
    if unknown:
        raise BadDeclaration(f"it holds keys this reader does not know: {', '.join(unknown)}")
    missing = [key for key in _DECLARATION_KEYS[1:] if key not in document]
    if missing:
        raise BadDeclaration(f"it lacks {', '.join(missing)}")
    harness = document["harness"]
    if not isinstance(harness, str) or not harness.strip():
        raise BadDeclaration("its `harness` is not a harness's name")
    return Declaration(
        harness=harness,
        keys=_harness_keys(document["keys"]),
        name_forms=_shapes(document["name_forms"], "name_forms"),
        known_tools=_known_tools(document["known_tools"]),
        withheld_admits=_shapes(document["withheld_admits"], "withheld_admits"),
    )


def _harness_keys(value: Any) -> dict[str, str]:
    """The harness's key for each form, one key a front matter holds for each."""
    if not isinstance(value, dict):
        raise BadDeclaration("its `keys` is not an object")
    unknown = sorted(set(value) - set(KEYS))
    if unknown:
        raise BadDeclaration(
            f"its `keys` names forms the reader does not know: {', '.join(unknown)}"
        )
    missing = [form for form in KEYS if form not in value]
    if missing:
        raise BadDeclaration(f"its `keys` gives no key for {', '.join(missing)}")
    for form, key in value.items():
        if not isinstance(key, str) or re.fullmatch(_KEY, key) is None:
            raise BadDeclaration(
                f"its `keys` gives {json.dumps(key)} for `{form}`, which is not a key a front "
                "matter holds"
            )
    if len(set(value.values())) < len(KEYS):
        raise BadDeclaration("its `keys` gives one key for both forms")
    return dict(value)


def _known_tools(value: Any) -> frozenset[str]:
    """The harness's built-in tools, each by a name in the reader's grammar, once."""
    if not isinstance(value, list):
        raise BadDeclaration("its `known_tools` is not a list")
    names: set[str] = set()
    for name in value:
        if not isinstance(name, str) or re.fullmatch(_NAME, name) is None:
            raise BadDeclaration(
                f"its `known_tools` holds {json.dumps(name)}, which is not a tool's name the "
                "reader reads"
            )
        if name in names:
            raise BadDeclaration(f"its `known_tools` names {name} twice")
        names.add(name)
    return frozenset(names)


def _shapes(value: Any, key: str) -> tuple[Shape, ...]:
    """The shapes a list of the declaration gives."""
    if not isinstance(value, list):
        raise BadDeclaration(f"its `{key}` is not a list")
    return tuple(_shape(item, key) for item in value)


def _shape(item: Any, key: str) -> Shape:
    """One shape: a pattern in Python's dialect, which matches a whole name, whether
    an argument may follow the name, and the shape in words."""
    if not isinstance(item, dict):
        raise BadDeclaration(f"its `{key}` holds {json.dumps(item)}, which is not an object")
    unknown = sorted(set(item) - set(_SHAPE_KEYS))
    if unknown:
        raise BadDeclaration(
            f"its `{key}` holds a shape with keys the reader does not know: {', '.join(unknown)}"
        )
    missing = [field for field in _SHAPE_KEYS if field not in item]
    if missing:
        raise BadDeclaration(f"its `{key}` holds a shape that lacks {', '.join(missing)}")
    pattern, argument, description = item["pattern"], item["argument"], item["description"]
    if not isinstance(pattern, str):
        raise BadDeclaration(f"its `{key}` gives a pattern that is not a string")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise BadDeclaration(
            f"its `{key}` gives the pattern {json.dumps(pattern)}, which is not a regular "
            f"expression ({exc})"
        ) from None
    if not isinstance(argument, bool):
        raise BadDeclaration(f"its `{key}` gives an `argument` that is not true or false")
    if not isinstance(description, str) or not description.strip():
        raise BadDeclaration(f"its `{key}` gives a shape with no description")
    return Shape(compiled, argument, description)


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
