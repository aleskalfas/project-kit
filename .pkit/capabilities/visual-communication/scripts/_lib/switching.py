"""A switching file read in a mode, and held to the one-key file of that mode, with no browser
(visual-communication DEC-018 point 1).

A *switching file* holds several combinations of modes, and draws the one the reader's signal
names: its plain drawing is the first combination's, and a rule of the file repaints it where
a signal names another. An export holds it to the SVG renderer's file of each combination
it holds, element by element, so the file a page shows paints as the drawing a person looked
at. This module reads both files as a browser reads them, and shares nothing with what writes
them, so a slip in either shows as a difference.

- **Reading in a mode** (`painted`). Each `@media` rule of the file whose every condition the
  mode's signals hold, such as `(prefers-color-scheme:dark)`, applies; any other does not. A
  rule of a style wins over an element's attribute of the same property, and a later rule
  over an earlier one. Each selector of a rule is one attribute's: present, equal to a CSS
  string, or holding it as one of its words, so each weighs the same. Anything else in a
  rule refuses the read (`Unreadable`), since a browser could read it otherwise.
- **What is compared.** Each element drawn, in the file's order, outside `<defs>`: its name,
  its attributes, what it paints and its text. An element whose `display` is `none`, and all
  below it, is not drawn. What the file writes only so a rule can reach it is left out: the
  marks of a paint and of a picture, and `data-key` on the root, which names the first key.
- **What it paints** is its fill and its stroke as an element takes them, its own or its
  parent's: a colour and its opacity, or `none`, and a stroke's width. A paint of `none`
  paints no opacity or width, so neither counts. A marker is read where it lies, as its
  triangle paints, and one that paints nothing counts as none. So two files that paint alike
  compare equal, whatever ids their markers take.
- **The styles.** The text of each file's styles, every `@media` rule left out, is compared
  whole: the fonts each file embeds, and the rules it holds in every mode.

A difference names the element by the nearest trace id at or above it, `data-id`, or the
page's own, `data-page`, and says what differs.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree

#: The namespace of an SVG element, as ElementTree names it.
_SVG = "{http://www.w3.org/2000/svg}"

#: What marks a paint or a picture so a rule can reach it, and what names the first key: none
#: of it is drawn.
UNDRAWN = frozenset({"data-fill", "data-stroke", "data-shown-in"})

#: Each paint an element takes from its parent where it names none, with its value at the
#: root.
INHERITED = {
    "fill": "#000000",
    "fill-opacity": "1",
    "stroke": "none",
    "stroke-opacity": "1",
    "stroke-width": "1",
}

#: The attributes that place an arrowhead.
MARKERS = ("marker-start", "marker-end")

_CONDITIONS = re.compile(r"^\(([a-z-]+):([a-z0-9-]+)\)((?: and \([a-z-]+:[a-z0-9-]+\))*)$")
_CONDITION = re.compile(r"\(([a-z-]+):([a-z0-9-]+)\)")
_RULE = re.compile(r'\[([a-z-]+)(?:(~?=)("(?:[^"\\]|\\.)*"))?\]\{([^{}"\\]*)\}')
_DECLARATION = re.compile(r"^([a-z-]+):([^:;]+)$")
_URL = re.compile(r"^url\(#([^)]+)\)$")
_ESCAPE = re.compile(r"\\([0-9a-fA-F]{1,6}) ?|\\(.)")


class Unreadable(Exception):
    """A file this module cannot read as a browser would."""


@dataclass(frozen=True)
class Difference:
    """An element the two files draw otherwise: its trace id, and what differs."""

    element: str
    why: str


def differences(switching: str, one_key: str, signals: Mapping[str, str]) -> list[Difference]:
    """Each element the switching file `switching`, read under `signals`, draws otherwise than
    the one-key file `one_key`, once, in the file's order. `signals` holds the value of each
    reader's signal in the combination, such as `{"prefers-color-scheme": "dark"}`. A file
    that cannot be read is one difference, at its page."""
    try:
        held = painted(switching, signals)
    except (Unreadable, ElementTree.ParseError) as exc:
        return [Difference(_page_of(switching), f"the switching file cannot be read: {exc}")]
    try:
        expected = painted(one_key, {})
    except (Unreadable, ElementTree.ParseError) as exc:
        return [Difference(_page_of(one_key), f"the one-key file cannot be read: {exc}")]
    found: dict[str, str] = {}
    if held.style != expected.style:
        found.setdefault(held.page, "its fonts or its styles differ")
    for index in range(max(len(held.elements), len(expected.elements))):
        if index >= len(held.elements):
            found.setdefault(expected.elements[index].owner, "it is not drawn")
            continue
        if index >= len(expected.elements):
            found.setdefault(held.elements[index].owner, "the one-key file draws no such element")
            continue
        why = held.elements[index].differs(expected.elements[index])
        if why:
            found.setdefault(held.elements[index].owner, why)
    return [Difference(element, why) for element, why in found.items()]


@dataclass(frozen=True)
class Drawn:
    """One element as it is drawn: the trace id it lies under, its name, its attributes, what it
    paints, each arrowhead as it paints, and its text and what follows it."""

    owner: str
    name: str
    attributes: tuple[tuple[str, str], ...]
    paint: tuple[Any, ...]
    markers: tuple[Any, ...]
    text: str
    tail: str

    def differs(self, other: Drawn) -> str:
        """What differs between this element and `other`, in words; empty where nothing does."""
        if self.name != other.name:
            return f"it is a `{self.name}`, and the one-key file draws a `{other.name}`"
        for prop, mine, theirs in zip(("fill", "stroke"), self.paint, other.paint, strict=True):
            if mine != theirs:
                return f"its {prop} is {_said(mine)}, and the one-key file's {_said(theirs)}"
        if self.markers != other.markers:
            return "its arrowheads paint otherwise"
        if self.attributes != other.attributes:
            return "its attributes differ"
        if (self.text, self.tail) != (other.text, other.tail):
            return "its text differs"
        return ""


@dataclass(frozen=True)
class Reading:
    """A file as a browser draws it in one mode: its page's trace id, the text of its styles
    with every `@media` rule left out, and each element drawn, in order."""

    page: str
    style: str
    elements: tuple[Drawn, ...]


def painted(text: str, signals: Mapping[str, str]) -> Reading:
    """The file `text` as a browser draws it where the reader's signals hold `signals`. Raises
    Unreadable, or ElementTree.ParseError for a file that is no XML."""
    root = ElementTree.fromstring(text)
    page = root.get("data-page") or ""
    styles = [style.text or "" for style in root.iter(f"{_SVG}style")]
    kept, rules = [], []
    for style in styles:
        plain, media = _split(style)
        kept.append(plain)
        for conditions, body in media:
            if all(signals.get(name) == value for name, value in conditions):
                rules.extend(_rules(body))
    markers = {
        str(marker.get("id")): marker
        for marker in root.iter(f"{_SVG}marker")
        if marker.get("id") is not None
    }
    reader = _Reader(page, rules, markers)
    return Reading(page, "".join(kept), tuple(reader.drawn(root)))


class _Reader:
    """Reads each element of one file under the rules that apply in one mode."""

    def __init__(
        self,
        page: str,
        rules: list[tuple[str, str | None, str | None, dict[str, str]]],
        markers: Mapping[str, ElementTree.Element],
    ) -> None:
        self.page = page
        self.rules = rules
        self.markers = markers

    def specified(self, element: ElementTree.Element) -> dict[str, str]:
        """The element's attributes, each property a rule that matches it sets put in its
        place, later rules last."""
        held = dict(element.attrib)
        for attribute, operator, value, declared in self.rules:
            if _matches(element, attribute, operator, value):
                held.update(declared)
        return held

    def drawn(
        self,
        element: ElementTree.Element,
        owner: str = "",
        inherited: Mapping[str, str] = INHERITED,
    ) -> Iterator[Drawn]:
        """`element` and each element below it that is drawn, in order. `<defs>` holds nothing
        drawn where it lies."""
        name = element.tag.removeprefix(_SVG)
        if name == "defs":
            return
        held = self.specified(element)
        if held.pop("display", "inline") == "none":
            return
        owner = held.get("data-id") or owner or self.page
        paints = {prop: held.pop(prop, inherited[prop]) for prop in INHERITED}
        markers = tuple(self.marker(held.pop(at, "")) for at in MARKERS)
        if name == "svg":
            held.pop("data-key", None)
        attributes = tuple(
            sorted((key, value) for key, value in held.items() if key not in UNDRAWN)
        )
        yield Drawn(
            owner,
            name,
            attributes,
            _paint(paints),
            markers,
            element.text or "",
            element.tail or "",
        )
        for child in element:
            yield from self.drawn(child, owner, paints)

    def marker(self, place: str) -> tuple[Any, ...] | None:
        """The arrowhead an attribute places, as it paints: the marker's own attributes, and the
        shape and the paint of each path in it. None where it places none, or where its
        triangle paints nothing. Raises Unreadable for a marker the file does not hold."""
        if not place:
            return None
        found = _URL.match(place)
        if found is None or found.group(1) not in self.markers:
            raise Unreadable(f"an arrowhead `{place}` names no marker of the file")
        marker = self.markers[found.group(1)]
        own = tuple(sorted((key, value) for key, value in marker.attrib.items() if key != "id"))
        paths = []
        for path in marker:
            held = self.specified(path)
            paint = _paint({prop: held.get(prop, INHERITED[prop]) for prop in INHERITED})
            if paint[0] != ("none",):
                paths.append((held.get("d", ""), paint))
        return (own, tuple(paths)) if paths else None


def _paint(paints: Mapping[str, str]) -> tuple[Any, ...]:
    """A fill and a stroke as they paint: a colour, its opacity and a stroke's width, or
    `none`, which paints neither."""
    fill = (
        ("none",)
        if paints["fill"] == "none"
        else (paints["fill"].lower(), _number(paints["fill-opacity"]))
    )
    stroke = (
        ("none",)
        if paints["stroke"] == "none"
        else (
            paints["stroke"].lower(),
            _number(paints["stroke-opacity"]),
            _number(paints["stroke-width"]),
        )
    )
    return (fill, stroke)


def _said(paint: tuple[Any, ...]) -> str:
    """A fill or a stroke in words: `none`, or its colour, its opacity and a stroke's width."""
    if paint == ("none",):
        return "none"
    said = f"{paint[0]} at an opacity of {paint[1]:g}"
    return said if len(paint) == 2 else f"{said}, {paint[2]:g} px wide"


def _number(text: str) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise Unreadable(f"`{text}` is no number") from exc


def _matches(
    element: ElementTree.Element, attribute: str, operator: str | None, value: str | None
) -> bool:
    """Whether the selector of one attribute matches the element."""
    held = element.get(attribute)
    if held is None:
        return False
    if operator is None:
        return True
    if operator == "=":
        return held == value
    return value in held.split()


def _split(style: str) -> tuple[str, list[tuple[list[tuple[str, str]], str]]]:
    """The text of a style with each `@media` rule left out, and each such rule: its
    conditions, and its body. Reads strings, so a brace or an `@media` in a name is text.
    Raises Unreadable for a rule whose block does not close, or whose conditions it cannot
    read."""
    kept: list[str] = []
    media: list[tuple[list[tuple[str, str]], str]] = []
    at = index = 0
    quote = ""
    escaped = False
    while index < len(style):
        char = style[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            quote = "" if char == quote else quote
        elif char in "\"'":
            quote = char
        elif style.startswith("@media ", index):
            kept.append(style[at:index])
            opening = style.find("{", index)
            if opening < 0:
                raise Unreadable("an `@media` rule opens no block")
            closing = _closing(style, opening)
            conditions = style[index + len("@media ") : opening]
            if _CONDITIONS.match(conditions) is None:
                raise Unreadable(f"an `@media` rule's conditions `{conditions}` cannot be read")
            media.append((_CONDITION.findall(conditions), style[opening + 1 : closing]))
            index = at = closing + 1
            continue
        index += 1
    kept.append(style[at:])
    return "".join(kept), media


def _closing(text: str, opening: int) -> int:
    """The index of the brace that closes the block opened at `opening`, strings read."""
    depth = 0
    quote = ""
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            quote = "" if char == quote else quote
        elif char in "\"'":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise Unreadable("an `@media` rule's block does not close")


def _rules(body: str) -> list[tuple[str, str | None, str | None, dict[str, str]]]:
    """The rules of an `@media` rule's body, in order: each selector's attribute, its operator
    and its value, and the properties it sets. Raises Unreadable for anything else."""
    found = []
    at = 0
    while at < len(body):
        rule = _RULE.match(body, at)
        if rule is None:
            raise Unreadable(f"a rule `{body[at : at + 60]}` cannot be read")
        attribute, operator, quoted, declarations = rule.groups()
        declared = {}
        for declaration in declarations.split(";"):
            held = _DECLARATION.match(declaration)
            if held is None:
                raise Unreadable(f"a declaration `{declaration}` cannot be read")
            declared[held.group(1)] = held.group(2)
        value = None if quoted is None else _unquoted(quoted)
        found.append((attribute, operator, value, declared))
        at = rule.end()
    return found


def _unquoted(quoted: str) -> str:
    """A CSS string's value: its quotes taken off, and each escape read."""

    def escape(found: re.Match[str]) -> str:
        code, char = found.groups()
        return chr(int(code, 16)) if code is not None else char

    return _ESCAPE.sub(escape, quoted[1:-1])


def _page_of(text: str) -> str:
    """The page a file names, read without parsing it, for a file that cannot be read."""
    found = re.search(r'data-page="([^"]*)"', text)
    return found.group(1) if found else ""
