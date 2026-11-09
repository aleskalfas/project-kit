"""The CSS code writer: a brand's resolved values as CSS custom properties, spelling form 1
(visual-communication DEC-004 point 4, DEC-005 points 7 to 9, DEC-021 point 8).

It reads the values document, version 2 (`_lib.values`), and the brand's value axes, and
writes one style sheet. Its declaration, `css_declaration.py`, says what it takes. It spells
no size axis: the command hands it a brand's values at the default of each, and reports
each token a size changes as a loss. Nothing in the sheet answers a window's width.

**Names, form 1.** One custom property for each exported token path: `--`, then, with a
`prefix`, the prefix and `--`, then the path's segments joined by `--`. A segment's own
words keep their single hyphens, and no name holds `--`, so no two paths spell the same:
`space.1` is `--space--1`, `text-primary` is `--text-primary`, and with the prefix
`brand`, `--brand--space--1`.

**Values, form 1.** A colour is `#rrggbb` from its components rounded to 8 bits (half
up), or `#rrggbbaa` when its alpha is not 1. A dimension is its number and `px`. A font
family is a list of quoted names. A font weight and a number are the number. Numbers are
written as the canonical text writes them (`1.4`, `16`). The writer has no form for a
typography value, nor for a picture role's file (DEC-025 point 4); its declaration says
so, and the command reports each as a loss.

**Rules, form 1, in this order.** Each mode is switched by an attribute,
`data-<axis>="<mode>"`, which the selectors expect on one element: the page's root by
default. An area that changes modes sets every axis's attribute on its own element; the
root may leave out an axis at its default.

1. `:root`, with every token at the combination of every default.
2. For each value axis in the order of its name, and each of its modes in the order the
   foundations declare them, the default included, `[data-<axis>="<mode>"]`:
   - at a mode that is not the default, every token the axis changes in some combination,
     at that mode and every other axis at its default;
   - at the default, every token whose first axis that changes it, in the order of the
     axes' names, is this one, at the combination of every default. So an area may set a
     default mode inside another, and no rule of a default mode overrides a rule of
     another axis's mode that comes before it.
3. For each combination of two or more modes that are not their axis's default, in key
   order, the conjunction of their selectors, with only the tokens whose value there
   differs from what the rules before it give. A conjunction of more selectors is more
   specific, so it wins over the rules of fewer.

Values are compared as they are spelled: two that spell the same are the same. A rule
left with no token is not written, and a rule declares its tokens once each, in the order
of their paths. A comment opens the sheet, naming the form and the lock. The order is
fixed, so one document gives one style sheet on every machine.

Standard library and `_lib` only.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from _lib import keys
from _lib.plugins.css_declaration import DECLARATION
from _lib.reading import canonical_json
from _lib.values import DOCUMENT
from _lib.values import VERSION as DOCUMENT_VERSION

NAME = DECLARATION["name"]
VERSION = DECLARATION["version"]
FORMS = tuple(DECLARATION["forms"])
KINDS = tuple(DECLARATION["kinds"])

#: What joins a prefix and the segments of a path in a name.
JOIN = "--"


class CssError(ValueError):
    """A values document, or axes, this writer has no form for."""


@dataclass(frozen=True)
class _Axis:
    """An axis as keys read it (`keys.AxisLike`)."""

    modes: tuple[str, ...]
    default: str


@dataclass(frozen=True)
class _Rule:
    """One rule: the modes its selector names, and the declarations it holds by token path,
    each already spelled."""

    modes: tuple[tuple[str, str], ...]
    declarations: dict[str, str]

    @property
    def specificity(self) -> int:
        return max(len(self.modes), 1)

    def matches(self, combination: Mapping[str, str]) -> bool:
        return all(combination[axis] == mode for axis, mode in self.modes)


# --- the whole ----------------------------------------------------------------------------------


def write(
    document: Mapping[str, Any],
    axes: Mapping[str, Mapping[str, Any]],
    *,
    form: int = 1,
    prefix: str | None = None,
) -> str:
    """The style sheet of `document`, the values document version 2, in spelling `form`.
    `axes` maps each axis of the brand to `{kind, modes, default}`, its modes in declared
    order; the document's keys must be every combination of them. Raises CssError."""
    if form not in FORMS:
        raise CssError(f"the css writer {VERSION} writes form {_listed(FORMS)}, not form {form}")
    if document.get("document") != DOCUMENT or document.get("version") != DOCUMENT_VERSION:
        raise CssError(f"the css writer reads the document {DOCUMENT} version {DOCUMENT_VERSION}")
    read = _axes(axes)
    spelled = _spelled(document, read)
    rules = _rules(spelled, read)
    return _text(document, rules, prefix)


def name_of(token_path: str, prefix: str | None = None) -> str:
    """The custom property a token path takes, form 1."""
    return JOIN + JOIN.join([*([prefix] if prefix else []), *token_path.split(".")])


def value_of(type_: str, value: Any) -> str:
    """A value of a DTCG type in its canonical form, spelled in CSS, form 1. Raises CssError
    for a type the writer has no form for, or a value not of its type."""
    try:
        if type_ == "color":
            return _colour(value)
        if type_ == "dimension":
            if value["unit"] != "px":
                raise CssError(f"a dimension in `{value['unit']}` has no form; form 1 takes px")
            return f"{_number(value['value'])}px"
        if type_ == "fontFamily":
            if not isinstance(value, list) or not all(isinstance(f, str) for f in value):
                raise TypeError("a font family is a list of names")
            return ", ".join(_quoted(family) for family in value)
        if type_ in ("fontWeight", "number"):
            return _number(value)
    except (KeyError, TypeError) as exc:
        raise CssError(f"`{value!r}` is not a {type_} value in canonical form") from exc
    raise CssError(f"the css writer has no form for a {type_} value")


# --- reading ------------------------------------------------------------------------------------


def _axes(axes: Mapping[str, Mapping[str, Any]]) -> dict[str, _Axis]:
    read = {}
    for name in sorted(axes):
        spec = axes[name]
        if spec.get("kind") not in DECLARATION["axis-kinds"]:
            raise CssError(
                f"the axis `{name}` is a {spec.get('kind')} axis; form 1 spells only "
                f"{_listed(DECLARATION['axis-kinds'])} axes, and is handed a brand's values "
                f"at the default of every other axis"
            )
        read[name] = _Axis(modes=tuple(spec["modes"]), default=spec["default"])
    return read


def _spelled(document: Mapping[str, Any], axes: Mapping[str, _Axis]) -> dict[str, dict[str, str]]:
    """Each token's value spelled in CSS, by token path then key. Raises CssError when the
    keys are not every combination of the axes."""
    every = {
        keys.key_of(combination, axes)
        for combination in keys.combinations({n: a.modes for n, a in axes.items()}, axes)
    }
    if set(document["keys"]) != every:
        raise CssError(
            "the document's keys are not every combination of the axes: written code switches "
            "between all of them"
        )
    spelled = {}
    for path, token in document["tokens"].items():
        spelled[path] = {key: value_of(token["type"], token["values"][key]) for key in every}
    return spelled


# --- the rules ----------------------------------------------------------------------------------


def _rules(spelled: Mapping[str, Mapping[str, str]], axes: Mapping[str, _Axis]) -> list[_Rule]:
    default = keys.DEFAULT_KEY
    changed = {name: _changed_by(spelled, axes, name) for name in axes}
    first = {path: next((name for name in axes if path in changed[name]), None) for path in spelled}
    rules = [_Rule((), {path: spelled[path][default] for path in sorted(spelled)})]
    for name, axis in axes.items():
        for mode in axis.modes:
            if mode == axis.default:
                held = [path for path in sorted(spelled) if first[path] == name]
                key = default
            else:
                held = sorted(changed[name])
                key = keys.key_of({name: mode}, axes)
            rules.append(_Rule(((name, mode),), {path: spelled[path][key] for path in held}))
    every = keys.combinations({n: a.modes for n, a in axes.items()}, axes)
    for combination in every:
        modes = tuple((n, combination[n]) for n in axes if combination[n] != axes[n].default)
        if len(modes) < 2:
            continue
        key = keys.key_of(combination, axes)
        given = _cascade(rules, combination)
        differs = {
            path: spelled[path][key]
            for path in sorted(spelled)
            if given.get(path) != spelled[path][key]
        }
        rules.append(_Rule(modes, differs))
    return [rule for rule in rules if rule.declarations]


def _changed_by(
    spelled: Mapping[str, Mapping[str, str]], axes: Mapping[str, _Axis], name: str
) -> set[str]:
    """The tokens the axis `name` changes in some combination: a value that differs between
    two combinations that differ in that axis alone."""
    found = set()
    every = keys.combinations({n: a.modes for n, a in axes.items()}, axes)
    for combination in every:
        here = keys.key_of(combination, axes)
        for mode in axes[name].modes:
            there = keys.key_of({**combination, name: mode}, axes)
            found.update(path for path, by in spelled.items() if by[here] != by[there])
    return found


def _cascade(rules: list[_Rule], combination: Mapping[str, str]) -> dict[str, str]:
    """What the rules give an element that sets every axis's attribute to `combination`:
    for each token, the rule of the highest specificity that holds it, the later of two."""
    given: dict[str, tuple[int, str]] = {}
    for rule in rules:
        if not rule.matches(combination):
            continue
        for path, value in rule.declarations.items():
            if path not in given or rule.specificity >= given[path][0]:
                given[path] = (rule.specificity, value)
    return {path: value for path, (_, value) in given.items()}


# --- the text -----------------------------------------------------------------------------------


def _text(document: Mapping[str, Any], rules: list[_Rule], prefix: str | None) -> str:
    lock = ", ".join(f"{name} {version}" for name, version in document["lock"].items())
    blocks = [
        "/* A brand's values as CSS custom properties, spelling form 1 of the css code writer,\n"
        f"   from {lock}.\n"
        "   `pkit visual write-code` writes this file: write it again, never edit it. */"
    ]
    for rule in rules:
        lines = [f"{_selector(rule)} {{"]
        lines.extend(
            f"  {name_of(path, prefix)}: {value};" for path, value in rule.declarations.items()
        )
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def _selector(rule: _Rule) -> str:
    if not rule.modes:
        return ":root"
    return "".join(f'[data-{axis}="{mode}"]' for axis, mode in rule.modes)


def _colour(value: Mapping[str, Any]) -> str:
    if value["colorSpace"] != "srgb":
        raise CssError(f"a colour in `{value['colorSpace']}` has no form; form 1 takes srgb")
    if len(value["components"]) != 3:
        raise TypeError("a colour has three components")
    channels = [*value["components"], *([] if value["alpha"] == 1 else [value["alpha"]])]
    return "#" + "".join(f"{_byte(channel):02x}" for channel in channels)


def _byte(channel: float) -> int:
    """A channel from 0 to 1 as 8 bits, rounded half up."""
    return min(255, max(0, math.floor(channel * 255 + 0.5)))


def _number(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CssError(f"`{value!r}` is not a number")
    return canonical_json(value)


def _quoted(family: str) -> str:
    """A family name as a CSS string: `"` and `\\` escaped, and a control character as its
    code point."""
    # The canvas's `css_string` (`_lib/canvas.py`) writes a name the same way, and escapes
    # more for a style element. It is kept apart so that this writer's output and version
    # do not move: a change to how either writes a CSS string is weighed for the other too.
    out = []
    for char in family:
        if char in ('"', "\\"):
            out.append("\\" + char)
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append(f"\\{ord(char):x} ")
        else:
            out.append(char)
    return '"' + "".join(out) + '"'


def _listed(items: Any) -> str:
    return ", ".join(str(item) for item in items)
