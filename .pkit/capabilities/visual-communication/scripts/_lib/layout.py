"""Components as data, and the values of one scene computed in reference order
(visual-communication DEC-001 points 4 and 6, DEC-005 points 1 to 3).

**A component** is a mapping. Beside its binding (`pkit_schema`, `schema_version`) it holds:

- `status` and `about`;
- `fields`: the JSON Schema of the content it takes. The engine reads its `properties`. A
  field whose `type` is `array`, or a list of types holding it, is a list field;
- `options`: each a list of words, the first the default; or `{item: <list field>}`,
  which names an item of that list by its id; or `{item: <list field>, point: true}`,
  which names an item and one of its exposed points, `{item: <id>, point: <name>}`. Such
  an option needs exactly one part that repeats over its list;
- `states`: each `{colour: <family>}`, or `{}` to keep the family;
- `colour`: the component's default colour family;
- `values`: named formulas, read by their name alone;
- `preferred`: `width` and `height`, the size it asks for;
- `parts`: drawn in order (below);
- `exposes`: the parts a component that places it may read. An exposed image part
  exposes its picture's points too, as parts of zero size of the component itself;
- `layouts`, on a top component: one layout in format 1, `{<layout>: {slots: {<field>:
  {pages: true}?}}}`. What a slot of pages places is a page. A top component with no slot
  of pages is a page alone, and part of the page that holds it (DEC-005 point 5).

**A part** is one of:

- a primitive, `box`, `ellipse`, `text`, `line` or `image`, whose own mapping holds its
  properties under SVG's names: `fill`, `stroke`, `stroke-width`, `rx`, `text-anchor`;
  a text's `content` (a field) and `style` (a typography role); an image's `produced` (a
  field naming a produced output);
- `use: <library>/<component>`, a component the part places, with `fields` (its field ->
  a field of this component) and `options` (its option -> a word, or a switch);
- `slot: <field>`, the component the content places in that field;
- `repeat: <list field>`, each item drawn by `draw` (a use) or the item's own `use`,
  arranged by `row` or `column` with `gap`, `align-items` (`stretch start center end`),
  `justify-content` (`start center end space-between`) and `sizes` (`own`, each item
  its preferred size along the line, or `equal`, the line shared equally). `colour` gives
  the items' default family.

A part may carry `when`: a field the content fills, or `{<option>: [<word>, ...]}`. A
missing part has zero size at its place. Its place is `x` and `y` (zero if absent), its
size `width` and `height`, each a formula; a line has `x1 y1 x2 y2`. A text's height is
its measured text's, and its width, where none is given, its widest paragraph's. An
image's height, where none is given, keeps its picture's proportions. Any property
value may be a switch, `{by: <option>, <word>: <value>, ...}`, naming every word. A
colour is a role's token path, or `:colour.<member>`: the role the foundations map that
member of the instance's colour family to (DEC-004 point 10). The instance's family is
the one a notation maps the content's `concept: <notation>/<concept>` to, else the
`colour` of the `repeat` part that draws it, else its component's, else its container's;
a state may change it. Content's `override: {<part>: <role>}` points a part's paint at
another role. `:index` and `:count` are an item's place among the items its list draws,
from 1, and how many it draws.

**Computed value by value.** Every value is a cell computed on first use, in the order
the references give, as a spreadsheet computes its cells: a loop is refused naming every
element in it. A value has one owner: a part's formula, its measured text, or its
parent's layout. Each problem is a finding; a value that cannot be computed is zero.

**Where a finding lies** is the file a person edits to mend it. A finding in a component,
or in what a component's part gave the component it places, names that component as
`component`, and its library's version as `library`, empty for the piece's own. The
finding on a component whose file cannot be read names it so too, and what names that
component takes none. A finding in what the content gave names neither. A top that names
no component lies in the piece, which names it: the finding says so as `piece`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar

from _lib import formula as fm
from _lib import names
from _lib.env import Env, PictureInfo, UnknownConcept, UnreadableComponent
from _lib.findings import FAILS, Finding
from _lib.keys import key_order
from _lib.text import Broken, Faces, Style, break_lines

PRIMITIVES = ("box", "ellipse", "text", "line", "image")
PLACING = ("use", "slot", "repeat")
KINDS = PRIMITIVES + PLACING

#: The keys each kind of part takes beside its kind and `when`.
PART_KEYS: Mapping[str, tuple[str, ...]] = {
    "box": ("x", "y", "width", "height"),
    "ellipse": ("x", "y", "width", "height"),
    "text": ("x", "y", "width"),
    "line": ("x1", "y1", "x2", "y2"),
    "image": ("x", "y", "width", "height"),
    "use": ("x", "y", "width", "height", "fields", "options"),
    "slot": ("x", "y", "width", "height"),
    "repeat": ("x", "y", "width", "height", "draw", "colour", "row", "column"),
}

#: The keys of a part that hold a formula: a place, a size or a line's end.
GEOMETRY = ("x", "y", "width", "height", "x1", "y1", "x2", "y2")

#: The keys each kind of part needs beside its kind.
REQUIRED: Mapping[str, tuple[str, ...]] = {
    "box": ("width", "height"),
    "ellipse": ("width", "height"),
    "line": ("x1", "y1", "x2", "y2"),
    "image": ("width",),
    "repeat": ("draw",),
}

#: Each primitive's properties, in its own mapping, under SVG's names.
PROPERTIES: Mapping[str, tuple[str, ...]] = {
    "box": ("fill", "stroke", "stroke-width", "rx"),
    "ellipse": ("fill", "stroke", "stroke-width"),
    "text": ("content", "style", "fill", "text-anchor"),
    "line": ("stroke", "stroke-width"),
    "image": ("produced",),
}
REQUIRED_PROPERTIES: Mapping[str, tuple[str, ...]] = {
    "text": ("content", "style"),
    "line": ("stroke",),
    "image": ("produced",),
}

#: The paint content's `override` points at another role, by kind of part.
OVERRIDDEN = {"box": "fill", "ellipse": "fill", "text": "fill", "line": "stroke"}

PAINTS = ("fill", "stroke")
LENGTHS = ("stroke-width", "rx")
OPERATORS = ("row", "column")

#: The words a property takes, the first its default.
WORDS: Mapping[str, tuple[str, ...]] = {
    "text-anchor": ("start", "middle", "end"),
    "align-items": ("stretch", "start", "center", "end"),
    "justify-content": ("start", "center", "end", "space-between"),
    "sizes": ("own", "equal"),
}
OPERATOR_WORDS = ("align-items", "justify-content", "sizes")

COMPONENT_KEYS = (
    "pkit_schema", "schema_version", "status", "about", "fields", "options", "states",
    "colour", "values", "preferred", "parts", "exposes", "layouts",
)  # fmt: skip

#: The key of a switch, which no option takes as a word.
SWITCH = "by"

#: The engine's mark for a member of the instance's colour family.
FAMILY = ":colour."

#: The start of the source of a value the content gave.
CONTENT = "content:"

#: A size this much less than the size asked for is not short of it: half the scene's
#: rounding step.
TOLERANCE = 0.005

_ONLY_ROLE = re.compile(r"^=@([a-z0-9.-]+)$")

T = TypeVar("T")


class Fault(Exception):
    """A value that cannot be computed, with the finding that says why, or none where
    that was reported already."""

    def __init__(self, finding: Finding | None = None) -> None:
        super().__init__(finding.message if finding else "reported already")
        self.finding = finding


class _Missing(Exception):
    """A path that reaches no exposed part, point or item; the formula reading it turns
    it into a finding."""


_FAILED = object()


def _is_use(value: Any) -> bool:
    if not isinstance(value, str) or value.count("/") != 1:
        return False
    library, component = value.split("/")
    return names.is_name(library) and names.is_name(component)


def _is_field(value: Any, fields: Mapping[str, Any] | set[str]) -> bool:
    return isinstance(value, str) and value in fields


def _is_list(schema: Any) -> bool:
    """Whether a field's schema makes it a list field: its `type` is `array`, or a list of
    types that holds `array`, such as `[array, null]`."""
    kind = schema.get("type") if isinstance(schema, Mapping) else None
    return kind == "array" or (isinstance(kind, list) and "array" in kind)


# --- components ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Option:
    """An option a component declares: words, or an item (and its point) of a list."""

    name: str
    words: tuple[str, ...] = ()
    items: str | None = None
    point: bool = False


@dataclass(frozen=True)
class Part:
    name: str
    kind: str
    spec: Mapping[str, Any]

    @property
    def props(self) -> Mapping[str, Any]:
        value = self.spec.get(self.kind) if self.kind in PRIMITIVES else None
        return value if isinstance(value, Mapping) else {}

    @property
    def operator(self) -> str:
        return next((name for name in OPERATORS if name in self.spec), OPERATORS[0])

    @property
    def settings(self) -> Mapping[str, Any]:
        value = self.spec.get(self.operator)
        return value if isinstance(value, Mapping) else {}

    @property
    def main(self) -> str:
        """The size along the line a list's items lie on."""
        return "width" if self.operator == "row" else "height"


class Component:
    """A component as data, read once per scene and checked as it is read: its names, its
    switches, and every formula's references and dimensions. `issues` lists what is
    wrong, as `(code, key path, message)`."""

    def __init__(self, use: str, data: Mapping[str, Any], ctx: Context) -> None:
        self.use = use
        self.issues: list[tuple[str, str, str]] = []
        self.options: dict[str, Option] = {}
        self.states: dict[str, str | None] = {}
        self.parts: dict[str, Part] = {}
        self.formulas: dict[str, fm.Formula | None] = {}
        self.repeats_over: dict[str, str] = {}
        self.pages: frozenset[str] = frozenset()
        self.top = "layouts" in data
        self._ctx = ctx
        self._value_dims: dict[str, int | None] = {}
        self._roles_reported: set[str] = set()
        fields = data.get("fields")
        properties = fields.get("properties") if isinstance(fields, Mapping) else None
        self.fields: Mapping[str, Any] = properties if isinstance(properties, Mapping) else {}
        self.lists = {name for name, schema in self.fields.items() if _is_list(schema)}
        self.colour: str | None = data.get("colour")
        self.values = self._mapping(data, "values")
        self.preferred = self._mapping(data, "preferred")
        exposes = data.get("exposes") or []
        self.exposes: tuple[str, ...] = tuple(exposes) if isinstance(exposes, list) else ()
        self._read(data)

    def _issue(self, code: str, where: str, message: str) -> None:
        self.issues.append((code, where, f"{self.use}: {message}"))

    def _shape(self, where: str, message: str) -> None:
        self._issue("component-shape", where, message)

    def _mapping(self, data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
        value = data.get(key)
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            self._shape(key, f"`{key}` is not a mapping")
            return {}
        return value

    def _read(self, data: Mapping[str, Any]) -> None:
        for key in data:
            if key not in COMPONENT_KEYS:
                self._shape(str(key), f"takes no key `{key}`")
        self._read_options(self._mapping(data, "options"))
        for state, decl in self._mapping(data, "states").items():
            self.states[state] = decl.get("colour") if isinstance(decl, Mapping) else None
        for name, spec in self._mapping(data, "parts").items():
            self._read_kind(name, spec)
        for name, value in self.values.items():
            if name in self.parts:
                self._shape(f"values.{name}", f"names `{name}` both a value and a part")
            self._number(f"values.{name}", value, None)
        for size, value in self.preferred.items():
            if size in ("width", "height"):
                self._number(f"preferred.{size}", value, fm.LENGTH)
            else:
                self._shape(f"preferred.{size}", f"asks for no size `{size}`")
        for part in self.parts.values():
            self._read_part(part)
        for name in self.exposes:
            if name not in self.parts:
                self._shape("exposes", f"exposes `{name}`, which is no part of it")
        for option in self.options.values():
            if option.items is not None and not self.repeats_over.get(option.items):
                self._shape(
                    f"options.{option.name}",
                    f"the option `{option.name}` names an item of `{option.items}`, "
                    "over which not exactly one part repeats",
                )
        if self.top:
            self._read_layouts(data.get("layouts"))

    def _read_options(self, options: Mapping[str, Any]) -> None:
        for name, decl in options.items():
            where = f"options.{name}"
            if name in self.fields or name in names.RESERVED_PLACING_KEYS:
                self._shape(where, f"`{name}` is an option and a field or a reserved key")
            if isinstance(decl, list) and decl and all(names.is_name(word) for word in decl):
                if SWITCH in decl or len(set(decl)) != len(decl):
                    self._shape(where, f"the option `{name}` repeats a word or takes `{SWITCH}`")
                self.options[name] = Option(name, words=tuple(decl))
            elif isinstance(decl, Mapping) and "item" in decl and set(decl) <= {"item", "point"}:
                if not _is_field(decl["item"], self.lists):
                    self._shape(where, f"the option `{name}` names no list field `{decl['item']}`")
                if decl.get("point", True) is not True:
                    self._shape(where, f"the option `{name}` takes `point: true` or no point")
                self.options[name] = Option(name, items=decl["item"], point="point" in decl)
            else:
                self._shape(where, f"the option `{name}` is neither words nor an item of a list")

    def _read_kind(self, name: str, spec: Any) -> None:
        where = f"parts.{name}"
        if not names.is_name(name):
            self._shape(where, f"`{name}` is not a name")
            return
        kinds = [kind for kind in KINDS if isinstance(spec, Mapping) and kind in spec]
        if len(kinds) != 1:
            self._shape(where, f"the part `{name}` is not exactly one of {', '.join(KINDS)}")
            return
        self.parts[name] = Part(name, kinds[0], spec)
        # Every list's repeat is known before any formula is read, so a formula may read an
        # item option whose list a later part repeats over.
        listed = spec.get("repeat")
        if kinds[0] == "repeat" and _is_field(listed, self.lists):
            # Where two parts repeat over a list, no option names its items.
            self.repeats_over[listed] = "" if listed in self.repeats_over else name

    def _read_part(self, part: Part) -> None:
        where = f"parts.{part.name}"
        kind, spec = part.kind, part.spec
        for key in spec:
            if key == "height" and kind == "text":
                self._issue(
                    "two-owners",
                    f"{where}.height",
                    f"the height of the text `{part.name}` has two owners: the part gives "
                    "it, and its measured text sets it",
                )
            elif key not in (kind, "when", *PART_KEYS[kind]):
                self._shape(f"{where}.{key}", f"the {kind} `{part.name}` takes no `{key}`")
        for key in REQUIRED.get(kind, ()):
            if key not in spec:
                self._shape(where, f"the {kind} `{part.name}` needs `{key}`")
        if "when" in spec:
            self._read_when(f"{where}.when", spec["when"])
        for key in GEOMETRY:
            if key in spec and key in PART_KEYS[kind]:
                self._number(f"{where}.{key}", spec[key], fm.LENGTH)
        if kind in PRIMITIVES:
            self._read_properties(part)
        elif kind == "use":
            self._read_use(part)
        elif kind == "slot" and not _is_field(spec["slot"], self.fields):
            self._shape(f"{where}.slot", f"the slot `{part.name}` names no field `{spec['slot']}`")
        elif kind == "repeat":
            self._read_repeat(part)

    def _read_properties(self, part: Part) -> None:
        where = f"parts.{part.name}.{part.kind}"
        raw = part.spec[part.kind]
        if raw is not None and not isinstance(raw, Mapping):
            self._shape(where, f"the {part.kind} `{part.name}` holds no mapping of properties")
            return
        for key in REQUIRED_PROPERTIES.get(part.kind, ()):
            if key not in part.props:
                self._shape(where, f"the {part.kind} `{part.name}` needs `{key}`")
        for key, value in part.props.items():
            at = f"{where}.{key}"
            if key not in PROPERTIES[part.kind]:
                self._shape(at, f"the {part.kind} `{part.name}` takes no property `{key}`")
            elif key in PAINTS:
                self._switched(at, value, self._paint, nothing=True)
            elif key in LENGTHS:
                self._number(at, value, fm.LENGTH)
            elif key in WORDS:
                self._switched(at, value, self._words(WORDS[key]))
            elif key == "style":
                self._switched(at, value, self._role)
            elif not _is_field(value, self.fields):  # content, produced
                self._shape(at, f"`{key}` names no field `{value}`")

    def _read_use(self, part: Part) -> None:
        where = f"parts.{part.name}"
        if not _is_use(part.spec["use"]):
            self._shape(f"{where}.use", f"`{part.spec['use']}` is not `<library>/<component>`")
        bound = part.spec.get("fields") or {}
        if not isinstance(bound, Mapping):
            self._shape(f"{where}.fields", "`fields` is not a mapping")
        else:
            for theirs, ours in bound.items():
                if not _is_field(ours, self.fields):
                    self._shape(f"{where}.fields.{theirs}", f"passes no field `{ours}` of its own")
        chosen = part.spec.get("options") or {}
        if not isinstance(chosen, Mapping):
            self._shape(f"{where}.options", "`options` is not a mapping")
        else:
            for theirs, word in chosen.items():
                self._switched(f"{where}.options.{theirs}", word, self._words(None))

    def _read_repeat(self, part: Part) -> None:
        where = f"parts.{part.name}"
        listed = part.spec["repeat"]
        if not _is_field(listed, self.lists):
            self._shape(f"{where}.repeat", f"repeats over `{listed}`, which is no list field")
        if "draw" in part.spec and not _is_use(part.spec["draw"]):
            self._shape(f"{where}.draw", f"`{part.spec['draw']}` is not `<library>/<component>`")
        operators = [name for name in OPERATORS if name in part.spec]
        if len(operators) != 1:
            self._shape(where, f"the list `{part.name}` takes one of `row` and `column`")
            return
        settings = part.spec[operators[0]] or {}
        if not isinstance(settings, Mapping):
            self._shape(f"{where}.{operators[0]}", "the operator holds no mapping")
            return
        for key, value in settings.items():
            at = f"{where}.{operators[0]}.{key}"
            if key == "gap":
                self._number(at, value, fm.LENGTH)
            elif key in OPERATOR_WORDS:
                self._switched(at, value, self._words(WORDS[key]))
            else:
                self._shape(at, f"`{operators[0]}` takes no `{key}`")

    def _read_when(self, where: str, when: Any) -> None:
        if isinstance(when, str):
            if when not in self.fields:
                self._shape(where, f"`when` names no field `{when}`")
            return
        if isinstance(when, Mapping) and len(when) == 1:
            ((name, words),) = when.items()
            option = self.options.get(name)
            listed = words if isinstance(words, list) else [words]
            if option is None or not option.words:
                self._shape(where, f"`when` names no option of words `{name}`")
            elif not all(word in option.words for word in listed):
                self._shape(where, f"`when` names a word the option `{name}` lacks")
            return
        self._shape(where, "`when` takes a field, or `{<option>: [<word>, ...]}`")

    def _read_layouts(self, layouts: Any) -> None:
        if not isinstance(layouts, Mapping) or len(layouts) != 1:
            self._shape("layouts", "a top component declares one layout in format 1")
            return
        pages = set()
        for layout, decl in layouts.items():
            slots = decl.get("slots") if isinstance(decl, Mapping) else None
            if not isinstance(slots, Mapping):
                self._shape(f"layouts.{layout}", f"the layout `{layout}` declares no slots")
                continue
            for slot, slot_decl in slots.items():
                if slot not in self.fields:
                    self._shape(f"layouts.{layout}.slots.{slot}", f"the slot `{slot}` is no field")
                if isinstance(slot_decl, Mapping) and slot_decl.get("pages") is True:
                    pages.add(slot)
        self.pages = frozenset(pages)

    # -- values, which may switch on an option

    def _switched(
        self, where: str, value: Any, check: Callable[[str, Any], None], *, nothing: bool = False
    ) -> None:
        """Checks a value, or each branch of its switch; `nothing` lets a branch be null."""
        if not (isinstance(value, Mapping) and SWITCH in value):
            check(where, value)
            return
        option = self.options.get(value[SWITCH])
        if option is None or not option.words:
            self._shape(where, f"switches on `{value[SWITCH]}`, which is no option of words")
            return
        branches = {key for key in value if key != SWITCH}
        if branches != set(option.words):
            self._shape(
                where,
                f"the switch on `{option.name}` names {', '.join(sorted(branches))}, not each "
                f"word of it: {', '.join(option.words)}",
            )
        for word in option.words:
            if word in value and not (nothing and value[word] is None):
                self._switched(f"{where}.{word}", value[word], check, nothing=nothing)

    def _number(self, where: str, value: Any, expected: int | None) -> None:
        self._switched(where, value, lambda at, text: self._formula(at, text, expected))

    def _paint(self, where: str, value: Any) -> None:
        if isinstance(value, str) and value.startswith(FAMILY):
            if names.is_segment(value[len(FAMILY) :]):
                return
        if not names.is_token_path(value):
            self._shape(where, f"`{value}` is not a role's token path, nor `{FAMILY}<member>`")

    def _role(self, where: str, value: Any) -> None:
        if not names.is_token_path(value):
            self._shape(where, f"`{value}` is not a role's token path")

    def _words(self, words: tuple[str, ...] | None) -> Callable[[str, Any], None]:
        def check(where: str, value: Any) -> None:
            if not names.is_name(value) or (words is not None and value not in words):
                self._shape(
                    where, f"`{value}` is not {'one of ' + ', '.join(words) if words else 'a word'}"
                )

        return check

    # -- formulas

    def _formula(self, where: str, text: Any, expected: int | None) -> None:
        """Reads a formula at its key path and checks it; `formulas` holds it, or `None`."""
        self.formulas[where] = None
        if not fm.is_formula(text):
            self._issue(
                "formula-unreadable", where, f"`{text}` is not a formula, which starts with `=`"
            )
            return
        try:
            formula = fm.parse(text)
        except fm.FormulaError as error:
            self._issue("formula-unreadable", where, str(error))
            return
        for ref in formula.references():
            problem = self._unreachable(ref)
            if problem:
                self._issue("formula-reach", where, f"the formula `{text}` {problem}")
                return
        try:
            result = fm.dimension(formula, self._dimension)
        except fm.FormulaError as error:
            self._issue("formula-dimension", where, str(error))
            return
        if expected is not None and result is not None and result != expected:
            self._issue(
                "formula-dimension",
                where,
                f"the formula `{text}` gives {fm.dimension_name(result)} where "
                f"{fm.dimension_name(expected)} belongs",
            )
            return
        self.formulas[where] = formula

    def _unreachable(self, ref: fm.Reference) -> str | None:
        """Why a formula of this component may not read `ref`, as far as reading the
        component alone tells; the rest is found when the scene is computed."""
        if isinstance(ref, fm.Value):
            return None if ref.name in self.values else f"names no value `{ref.name}`"
        if not isinstance(ref, fm.Path):
            return None
        if ref.option is not None:
            option = self.options.get(ref.option)
            if option is None or option.items is None:
                return f"reads `{{{ref.option}}}`, which is no option naming an item"
            if not self.repeats_over.get(option.items):
                return (
                    f"reads `{{{ref.option}}}`, an item of `{option.items}`, over which not "
                    "exactly one part repeats"
                )
            return (
                f"reads below the point `{{{ref.option}}}` gives"
                if option.point and ref.steps
                else None
            )
        first = ref.steps[0]
        part = self.parts.get(first.name)
        if part is None:
            return f"reads `{ref}`: there is no part `{first.name}`"
        if first.item is not None and part.kind != "repeat":
            return f"reads `{ref}`: `{first.name}` is no list"
        if part.kind == "repeat" and first.item is None and len(ref.steps) > 1:
            return (
                f"reads `{ref}` with no item of `{first.name}`: name `:first`, `:last` or `[<id>]`"
            )
        if part.kind in ("box", "ellipse", "text", "line") and len(ref.steps) > 1:
            return f"reads `{ref}`: the {part.kind} `{first.name}` exposes nothing"
        if part.kind == "image" and len(ref.steps) > 2:
            return f"reads `{ref}`: a point has no parts"
        return None

    def _dimension(self, ref: fm.Reference) -> int | None:
        if isinstance(ref, fm.Engine):
            return fm.LENGTH if ref.name in ("width", "height") else fm.NUMBER
        if isinstance(ref, fm.Path):
            return fm.LENGTH
        if isinstance(ref, fm.Value):
            return self._value_dimension(ref.name)
        dimension, problem = self._ctx.role_dimension(ref.path)
        if problem and ref.path not in self._roles_reported:
            self._roles_reported.add(ref.path)
            code = (
                "unknown-role"
                if dimension is None and "no value" in problem
                else "formula-dimension"
            )
            self._issue(code, f"@{ref.path}", f"a formula reading `@{ref.path}` {problem}")
        return dimension

    def _value_dimension(self, name: str) -> int | None:
        if name in self._value_dims:
            return self._value_dims[name]
        self._value_dims[name] = None  # a loop of values is reported when one is computed
        found: set[int | None] = set()

        def collect(value: Any) -> None:
            if isinstance(value, Mapping) and SWITCH in value:
                for key, branch in value.items():
                    if key != SWITCH:
                        collect(branch)
                return
            try:
                found.add(fm.dimension(fm.parse(value), self._dimension))
            except (fm.FormulaError, TypeError, AttributeError):
                found.add(None)

        collect(self.values.get(name))
        if len(found) > 1 and None not in found:
            self._issue(
                "formula-dimension",
                f"values.{name}",
                f"the value `{name}` switches between dimensions",
            )
        self._value_dims[name] = found.pop() if len(found) == 1 else None
        return self._value_dims[name]


# --- one scene's context ------------------------------------------------------------------


class Context:
    """What computing one scene shares: the environment, its language, the faces, the
    components read, the findings, and the cells being computed."""

    def __init__(self, env: Env, language: str) -> None:
        self.env = env
        self.language = language
        self.faces = Faces(env.font_file)
        self.findings: list[Finding] = []
        self.stack: list[tuple[Instance, tuple[str, ...]]] = []
        self.active: set[tuple[int, tuple[str, ...]]] = set()
        self._seen: set[tuple[str, str, str]] = set()
        self._components: dict[str, Component | None] = {}
        self._unreadable: set[str] = set()
        self._roles: dict[str, Any] = {}
        self._families: dict[str, Mapping[str, str] | None] = {}
        self._concepts: dict[str, str | UnknownConcept | None] = {}

    def finding(self, code: str, message: str, *, where: str, use: str = "") -> Finding:
        """A finding that fails, at `where`: in the file of the component `use`, which it
        names with its library's version; with none, in the content."""
        if not use:
            return Finding(code, FAILS, message, where=where)
        library = self.library(use)
        return Finding(code, FAILS, message, where=where, library=library, extra={"component": use})

    def report(self, code: str, message: str, *, where: str, use: str = "") -> None:
        """Records a finding that fails, once: in the component `use`, or in the content."""
        self.add(self.finding(code, message, where=where, use=use))

    def add(self, finding: Finding) -> None:
        key = (finding.code, finding.where, finding.message)
        if key not in self._seen:
            self._seen.add(key)
            self.findings.append(finding)

    def attempt(self, compute: Callable[[], T], default: T) -> T:
        """A value, or `default` where it cannot be computed, its finding recorded."""
        try:
            return compute()
        except Fault as fault:
            if fault.finding is not None:
                self.add(fault.finding)
            return default

    def library(self, use: str) -> str:
        """`<library>@<version>` of the library a component lies in; empty for the piece's
        own, which lies in the piece. A finding in a component names it beside this, as
        `component`, so the check finds the component's file in either."""
        library = use.split("/")[0]
        if library == names.PIECE:
            return ""
        try:
            return f"{library}@{self.env.library_version(library)}"
        except KeyError:
            return library

    def component(self, use: str) -> Component | None:
        """A component, read and checked once, its issues recorded; `None` where there is none,
        or where its file cannot be read, which is a finding in that file (`unreadable`)."""
        if use not in self._components:
            try:
                data = self.env.component(use)
            except UnreadableComponent as unreadable:
                self._unreadable.add(use)
                self.report("component-unreadable", str(unreadable), where="", use=use)
                data = None
            except KeyError:
                data = None
            component = Component(use, data, self) if isinstance(data, Mapping) else None
            self._components[use] = component
            for code, where, message in component.issues if component else ():
                self.report(code, message, where=where, use=use)
        return self._components[use]

    def unreadable(self, use: Any) -> bool:
        """Whether `use` names a component whose file is present and cannot be read. What
        names it is not at fault, so it takes no finding."""
        return use in self._unreadable

    def role(self, path: str) -> Any:
        """A role's resolved value; raises `KeyError` where the brand gives it none."""
        if path not in self._roles:
            try:
                self._roles[path] = self.env.role(path)
            except KeyError:
                self._roles[path] = KeyError
        if self._roles[path] is KeyError:
            raise KeyError(path)
        return self._roles[path]

    def family(self, name: str) -> Mapping[str, str] | None:
        """The members of a colour family the foundations declare, each mapped to a colour
        role (DEC-004 point 10); `None` where they declare no such family."""
        if name not in self._families:
            try:
                self._families[name] = self.env.family(name)
            except KeyError:
                self._families[name] = None
        return self._families[name]

    def concept(self, name: str) -> str | None:
        """The colour family a concept maps to, `<notation>/<concept>` (DEC-004 point 10);
        `None` where its notation, or the concept in it, cannot be read, which is a finding
        in the notation. Raises `UnknownConcept` where the piece's notations do not hold
        it."""
        if name not in self._concepts:
            try:
                self._concepts[name] = self.env.concept(name)
            except UnknownConcept as unknown:
                self._concepts[name] = unknown
        found = self._concepts[name]
        if isinstance(found, UnknownConcept):
            raise UnknownConcept(found.concept, found.why)
        return found

    def role_dimension(self, path: str) -> tuple[int | None, str | None]:
        """A role's dimension in a formula, or why it has none."""
        try:
            value = self.role(path)
        except KeyError:
            return None, "names a role the brand gives no value"
        if isinstance(value, Mapping) and "value" in value and "unit" in value:
            if value["unit"] != "px":
                return None, f"reads a length in {value['unit']}; format 1 measures in px"
            return fm.LENGTH, None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return fm.NUMBER, None
        return None, "reads a role that is not a length or a number"

    def role_number(self, path: str) -> float:
        dimension, problem = self.role_dimension(path)
        if problem:
            raise Fault()  # recorded when the formula's component was read
        value = self.role(path)
        return float(value["value"] if dimension == fm.LENGTH else value)


# --- instances ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Arrangement:
    """A list's items along one axis: each item's offset and size, and the size they ask
    for together."""

    offsets: tuple[float, ...]
    sizes: tuple[float, ...]
    asked: float


@dataclass
class Node:
    """A part as one instance draws it."""

    part: Part
    present: bool = True
    child: Instance | None = None
    items: list[Instance] = field(default_factory=list)
    text: str = ""
    style: Style | None = None
    picture: PictureInfo | None = None
    output: str = ""


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _filled(value: Any) -> bool:
    return value not in (None, "", [], {})


def first_variant(picture: PictureInfo) -> str:
    """The variant whose pixels and points a scene reads: the first key in key order, the
    default first. Every variant one scene holds shares them (DEC-005 point 5)."""
    return min(picture.variants, key=key_order)


class Instance:
    """A component placed once: its fields and options, its colour family, its parts as
    built from the content, and its values, each computed on first use."""

    def __init__(
        self,
        ctx: Context,
        component: Component,
        given: Mapping[str, Any],
        *,
        trace: str,
        content_path: str | None,
        paths: Mapping[str, str] | None = None,
        sources: Mapping[str, str] | None = None,
        parent: Instance | None = None,
        part: str = "",
        is_item: bool = False,
        place_colour: tuple[str, str] | None = None,
        chain: tuple[str, ...] = (),
        through_pages: bool = False,
        by_content: bool = True,
    ) -> None:
        self.ctx = ctx
        self.component = component
        self.given = given
        self.trace = trace
        # The key path of the mapping in the content file that holds what it was given; None
        # where no mapping does, as where a `use` part placed it: `paths` then holds the key
        # path of each field the part passes on.
        self.content_path = content_path
        self._paths = dict(paths or {})
        self.parent = parent
        self.part_name = part
        self.is_item = is_item  # an item its parent's list draws
        self.position = 0  # its place among the items its list draws, from 0
        self.chain = chain or (component.use,)
        self.cells: dict[tuple[str, ...], Any] = {}
        self.nodes: dict[str, Node] = {}
        self.options: dict[str, Any] = {}
        self.option_sources: dict[str, str] = {}
        self.overrides: dict[str, tuple[str, str]] = {}
        self.library = ctx.library(component.use)
        # The instance whose part placed it with what it was given, where no content did.
        self._placer = None if by_content else parent
        self._sources = dict(sources or {})
        # What a slot of pages places is a page. A top component with no slot of pages is
        # a page alone, and part of the page that holds it (DEC-005 point 5).
        inside = any(above.is_page for above in self._ancestors())
        self.is_page = through_pages or (component.top and not component.pages and not inside)
        if self.is_page and inside:
            self._note("page-in-page", f"{trace}: {component.use} is a page inside a page")
        self._read_options()
        self.family, self.family_source = self._colour(place_colour)
        self._read_overrides()
        for name, each in component.parts.items():
            self.nodes[name] = self._build(each)

    # -- findings

    def _note(self, code: str, message: str, where: str = "", given: str = "") -> None:
        """Records a finding on what this instance was given, at the trace of the element
        it concerns: `where`, else the instance's own. It lies where `given`, the key of
        what it concerns, came from: in the content, where the content placed this
        instance, or gave that value for a part to pass on; else in the component whose
        part placed it, and gave the value or left it out."""
        passed_on = self._sources.get(given, "").startswith(CONTENT)
        placer = None if passed_on else self._placer
        use = placer.component.use if placer is not None else ""
        self.ctx.report(code, message, where=where or self.trace, use=use)

    def _fail(self, code: str, message: str, where: str = "") -> Fault:
        """A fault, with its finding, in this instance's component."""
        where = where or self.trace
        return Fault(self.ctx.finding(code, message, where=where, use=self.component.use))

    # -- what it was given

    def _ancestors(self) -> list[Instance]:
        found, above = [], self.parent
        while above is not None:
            found.append(above)
            above = above.parent
        return found

    def field_path(self, name: str) -> str | None:
        """The key path of the field `name` in the content file, by the keys the file
        writes: below the mapping that holds what this instance was given, or, where a
        `use` part placed it, the path of the field the part passes on under that name.
        None where no key of the content file gives the field."""
        if self.content_path is not None:
            return _join(self.content_path, name)
        return self._paths.get(name)

    def source_of_field(self, name: str) -> str:
        """Where the field or option `name` comes from: the source the part that placed
        this instance gave it, else the field's key path in the content file. A field no key
        of the content file gives, such as one a `use` part does not pass on, is the
        component whose part placed the instance's to give, and it gives none."""
        if name in self._sources:
            return self._sources[name]
        path = self.field_path(name)
        if path is not None:
            return f"{CONTENT}{path}"
        placer = self.parent if self.parent is not None else self
        return f"default:{placer.component.use}"

    def _read_options(self) -> None:
        use = self.component.use
        for name, option in self.component.options.items():
            raw = self.given.get(name)
            if not option.words:
                self.options[name] = self._item_option(name, option, raw)
                self.option_sources[name] = self.source_of_field(name)
            elif raw in option.words:
                self.options[name], self.option_sources[name] = raw, self.source_of_field(name)
            else:
                if raw is not None:
                    words = ", ".join(option.words)
                    self._note(
                        "option-word",
                        f"{self.trace}: `{name}` of {use} takes {words}, not `{raw}`",
                        given=name,
                    )
                self.options[name], self.option_sources[name] = option.words[0], f"default:{use}"

    def _item_option(self, name: str, option: Option, raw: Any) -> Mapping[str, str] | None:
        use = self.component.use
        if raw is None:
            self._note(
                "option-missing", f"{self.trace}: {use} needs the option `{name}`", given=name
            )
            return None
        if not isinstance(raw, Mapping) or set(raw) != (
            {"item", "point"} if option.point else {"item"}
        ):
            shape = "{item: <id>, point: <name>}" if option.point else "{item: <id>}"
            self._note(
                "option-word",
                f"{self.trace}: the option `{name}` of {use} takes {shape}",
                given=name,
            )
            return None
        listed = self.given.get(option.items or "")
        ids = (
            [each.get("id") for each in listed if isinstance(each, Mapping)]
            if isinstance(listed, list)
            else []
        )
        if raw["item"] not in ids:
            self._note(
                "unknown-item",
                f"{self.trace}: `{name}` names `{raw['item']}`, no item of `{option.items}`",
                given=name,
            )
            return None
        return raw

    def _colour(self, place: tuple[str, str] | None) -> tuple[str | None, str]:
        """The instance's colour family (DEC-001 point 6): its concept's, else its place's
        default in a list, else its component's, else its container's; then its state's."""
        concept = self._concept()
        if concept is not None:
            family, source = concept, self.source_of_field("concept")
        elif place is not None:
            family, source = place
        elif self.component.colour:
            family, source = self.component.colour, f"default:{self.component.use}"
        elif self.parent is not None:
            family, source = self.parent.family, self.parent.family_source
        else:
            family, source = None, ""
        state = self.given.get("state")
        if state is not None:
            if state not in self.component.states:
                self._note(
                    "unknown-state",
                    f"{self.trace}: {self.component.use} declares no state `{state}`",
                    given="state",
                )
            elif self.component.states[state]:
                family, source = self.component.states[state], self.source_of_field("state")
        return family, source

    def _concept(self) -> str | None:
        """The colour family of the concept the instance names, `<notation>/<concept>`
        (DEC-004 point 10); None where it names none, or none gives it a family. A concept
        of another shape, or one the piece's notations do not hold, is reported; one its
        notation cannot read is a finding in that notation alone."""
        raw = self.given.get("concept")
        if raw is None:
            return None
        # A concept is read with its notation's name, as a use is with its library's.
        if not _is_use(raw):
            self._note(
                "unknown-concept",
                f"{self.trace}: `concept` takes `<notation>/<concept>`, not `{raw}`",
                given="concept",
            )
            return None
        try:
            return self.ctx.concept(raw)
        except UnknownConcept as unknown:
            self._note("unknown-concept", f"{self.trace}: {unknown}", given="concept")
            return None

    def _read_overrides(self) -> None:
        raw = self.given.get("override")
        if raw is None:
            return
        if not isinstance(raw, Mapping):
            self._note(
                "override", f"{self.trace}: `override` takes {{<part>: <role>}}", given="override"
            )
            return
        for name, role in raw.items():
            part = self.component.parts.get(name)
            if part is None or part.kind not in OVERRIDDEN:
                self._note(
                    "override",
                    f"{self.trace}: `override` names `{name}`, no painted part of it",
                    given="override",
                )
            elif not names.is_token_path(role):
                self._note(
                    "override",
                    f"{self.trace}: `override` points `{name}` at `{role}`, not a role",
                    given="override",
                )
            else:
                self.overrides[name] = (role, f"{self.source_of_field('override')}.{name}")

    def pick(self, where: str, value: Any) -> tuple[str, Any, str | None]:
        """A value through its switches: the key path of the branch taken, the value, and
        the option that chose it."""
        chosen = None
        while isinstance(value, Mapping) and SWITCH in value:
            chosen = value[SWITCH]
            word = self.options.get(chosen)
            where, value = f"{where}.{word}", value.get(word)
        return where, value, chosen

    def _when(self, part: Part) -> bool:
        when = part.spec.get("when")
        if when is None:
            return True
        if isinstance(when, str):
            return _filled(self.given.get(when))
        if isinstance(when, Mapping) and len(when) == 1:
            ((name, words),) = when.items()
            return self.options.get(name) in (words if isinstance(words, list) else [words])
        return False

    # -- its parts, built from the content

    def _build(self, part: Part) -> Node:
        node = Node(part, present=self._when(part))
        if node.present:
            trace = f"{self.trace}/{part.name}"
            build = {
                "text": self._build_text,
                "image": self._build_image,
                "use": self._build_use,
                "slot": self._build_slot,
                "repeat": self._build_items,
            }.get(part.kind)
            if build is not None:
                build(node, trace)
        return node

    def _build_text(self, node: Node, trace: str) -> None:
        props = node.part.props
        content = props.get("content", "")
        value = self.given.get(content)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(value)
        if value is not None and not isinstance(value, str):
            self._note(
                "content-shape",
                f"{trace}: the field `{content}` holds no text",
                where=trace,
                given=content,
            )
            value = None
        node.text = value or ""
        _, role, _ = self.pick(f"parts.{node.part.name}.text.style", props.get("style"))
        if not isinstance(role, str):
            node.present = False  # recorded when the component was read
            return
        try:
            node.style = Style.of_role(role, self.ctx.role(role), self.ctx.faces)
        except KeyError:
            self._lose(
                node, "unknown-role", f"{trace}: the brand gives the role @{role} no value", trace
            )
        except ValueError as error:
            self._lose(node, "role-type", f"{trace}: {error}", trace)

    def _lose(self, node: Node, code: str, message: str, where: str) -> None:
        """Records why the component cannot draw the part at `where`, which then has zero
        size."""
        self.ctx.report(code, message, where=where, use=self.component.use)
        node.present = False

    def _build_image(self, node: Node, trace: str) -> None:
        produced = node.part.props.get("produced", "")
        output = self.given.get(produced)
        if not isinstance(output, str):
            node.present = False
            return
        try:
            picture = self.ctx.env.picture(output)
        except KeyError:
            picture = None
        if picture is None or not picture.variants:
            self._note(
                "missing-picture",
                f"{trace}: the piece has no produced output `{output}`",
                where=trace,
                given=produced,
            )
            node.present = False
            return
        first = first_variant(picture)
        for key, variant in picture.variants.items():
            moved = any(places.get(key) != places.get(first) for places in picture.points.values())
            if moved or variant.get("pixels") != picture.variants[first].get("pixels"):
                self._note(
                    "picture-variants",
                    f"{trace}: the variants of `{output}` differ in pixels or points, and one "
                    "scene holds them all",
                    where=trace,
                    given=produced,
                )
                break
        node.picture, node.output = picture, output

    def _component(self, node: Node, use: Any, trace: str, *, by_content: bool) -> Component | None:
        """The component `use` names, to draw a part or an item; `None` where there is none,
        with a finding in what named it: the content where `by_content`, else this
        instance's component. A component whose file cannot be read is a finding in that
        file alone (`Context.component`)."""
        component = self.ctx.component(use) if isinstance(use, str) else None
        if component is None:
            if not self.ctx.unreadable(use):
                named_in = "" if by_content else self.component.use
                self.ctx.report(
                    "unknown-component", f"{trace}: no component `{use}`", where=trace, use=named_in
                )
            node.present = False
        return component

    def _build_use(self, node: Node, trace: str) -> None:
        spec = node.part.spec
        use = spec["use"]
        if use in self.chain:
            loop = " → ".join([*self.chain, use])
            self.ctx.report(
                "places-itself",
                f"{trace}: {use} places itself: {loop}",
                where=trace,
                use=self.component.use,
            )
            node.present = False
            return
        component = self._component(node, use, trace, by_content=False)
        if component is None:
            return
        given: dict[str, Any] = {}
        sources: dict[str, str] = {}
        # Each field it passes on keeps the key path the content file writes for it.
        paths: dict[str, str] = {}
        for theirs, ours in (spec.get("fields") or {}).items():
            path = self.field_path(ours)
            if path is not None:
                paths[theirs] = path
            if ours in self.given:
                given[theirs], sources[theirs] = self.given[ours], self.source_of_field(ours)
        for theirs, raw in (spec.get("options") or {}).items():
            _, word, chosen = self.pick(f"parts.{node.part.name}.options.{theirs}", raw)
            given[theirs] = word
            sources[theirs] = f"option:{chosen}" if chosen else f"default:{self.component.use}"
        node.child = Instance(
            self.ctx, component, given, trace=trace, content_path=None, paths=paths,
            sources=sources, parent=self, part=node.part.name, chain=(*self.chain, use),
            by_content=False,
        )  # fmt: skip

    def _build_slot(self, node: Node, trace: str) -> None:
        name = node.part.spec["slot"]
        placed = self.given.get(name)
        if not _filled(placed):
            node.present = False
            return
        if not isinstance(placed, Mapping) or "use" not in placed:
            self._note(
                "content-shape",
                f"{trace}: the slot `{name}` takes a component, `{{use: ...}}`",
                where=trace,
                given=name,
            )
            node.present = False
            return
        component = self._component(node, placed["use"], trace, by_content=True)
        if component is not None:
            node.child = Instance(
                self.ctx, component, placed, trace=trace, content_path=self.field_path(name),
                parent=self, part=node.part.name, through_pages=name in self.component.pages,
            )  # fmt: skip

    def _build_items(self, node: Node, trace: str) -> None:
        """Each item of the list the part repeats over, drawn in the content's order. An item
        that is no mapping, repeats an id, or names no component is left out: it takes no
        place among the items drawn, so `:index` and `:count` never count it. Its trace
        keeps its place in the content's list, and so does its key path, which names the
        list as the content file writes it."""
        spec = node.part.spec
        name = spec["repeat"]
        listed = self.given.get(name)
        listed = listed if isinstance(listed, list) else []
        place = (spec["colour"], f"default:{self.component.use}") if spec.get("colour") else None
        path = self.field_path(name)
        seen: set[str] = set()
        for index, item in enumerate(listed, start=1):
            key = item.get("id") if isinstance(item, Mapping) else None
            step = f"[{key}]" if key is not None else f"#{index}"
            at = f"{trace}{step}"
            if not isinstance(item, Mapping) or key in seen:
                self._note(
                    "content-shape",
                    f"{at}: an item of `{name}` is no mapping, or repeats its id",
                    where=at,
                    given=name,
                )
                continue
            if key is not None:
                seen.add(key)
            use = item.get("use", spec.get("draw"))
            component = self._component(node, use, at, by_content="use" in item)
            if component is None:
                node.present = True  # the list stays; the item is left out
                continue
            instance = Instance(
                self.ctx, component, item, trace=at,
                content_path=None if path is None else f"{path}{step}", parent=self,
                part=node.part.name, is_item=True, place_colour=place,
                through_pages=name in self.component.pages,
            )  # fmt: skip
            instance.position = len(node.items)
            node.items.append(instance)

    def texts(self) -> list[tuple[str, Node]]:
        """Every text this instance and those below it draw, with its trace id."""
        found = []
        for name, node in self.nodes.items():
            if not node.present:
                continue
            if node.part.kind == "text":
                found.append((f"{self.trace}/{name}", node))
            for child in ([node.child] if node.child else []) + node.items:
                found.extend(child.texts())
        return found

    # -- cells

    def label(self, cell: tuple[str, ...]) -> str:
        """A cell, named for a message."""
        kind = cell[0]
        if kind == "size":
            return f"{self.trace} :{cell[1]}"
        if kind in ("preferred", "value"):
            return f"{self.trace} {kind} {cell[1]}"
        if kind == "part":
            return f"{self.trace}/{cell[1]}.{cell[2]}"
        return f"{self.trace}/{cell[1]} {kind}"

    def get(self, *cell: str) -> Any:
        """A cell's value, computed on first use. Raises `Fault`."""
        if cell in self.cells:
            if self.cells[cell] is _FAILED:
                raise Fault()
            return self.cells[cell]
        key = (id(self), cell)
        if key in self.ctx.active:
            start = next(i for i, (at, c) in enumerate(self.ctx.stack) if at is self and c == cell)
            loop = [at.label(c) for at, c in self.ctx.stack[start:]] + [self.label(cell)]
            raise self._fail("loop", f"a loop of references: {' → '.join(loop)}")
        self.ctx.stack.append((self, cell))
        self.ctx.active.add(key)
        try:
            value = self._compute(cell)
        except Fault:
            self.cells[cell] = _FAILED
            raise
        finally:
            self.ctx.stack.pop()
            self.ctx.active.discard(key)
        self.cells[cell] = value
        return value

    def _compute(self, cell: tuple[str, ...]) -> Any:
        kind, name = cell[0], cell[1]
        if kind == "size":
            return self._size(name)
        if kind == "preferred":
            if name not in self.component.preferred:
                use = self.component.use
                raise self._fail(
                    "no-size", f"{self.trace}: {use} asks for no {name}, and is given none"
                )
            return self.number(f"preferred.{name}", self.component.preferred[name])
        if kind == "value":
            return self.number(f"values.{name}", self.component.values[name])
        if kind == "part":
            return self._geometry(name, cell[2])
        if kind == "lines":
            return self._lines(name)
        if kind == "points":
            return self._mapped_points(name)
        return self._arrange(name, kind)

    def number(self, where: str, raw: Any) -> float:
        """The value of the component's formula at a key path. Raises `Fault`."""
        where, _, _ = self.pick(where, raw)
        formula = self.component.formulas.get(where)
        if formula is None:
            raise Fault()  # recorded when the component was read
        try:
            return fm.evaluate(formula, self._read)
        except fm.DivisionByZero as error:
            message = f"{self.trace}: {where} of {self.component.use}: {error}"
            raise self._fail("division-by-zero", message) from error

    def source(self, where: str, raw: Any) -> str:
        """Where a formula's value comes from: the option that chose it, the one role it
        reads, or the component's own default."""
        _, value, chosen = self.pick(where, raw)
        if chosen:
            return f"option:{chosen}"
        only = _ONLY_ROLE.match(value) if isinstance(value, str) else None
        return f"role:{only.group(1)}" if only else f"default:{self.component.use}"

    def _read(self, ref: fm.Reference) -> float:
        if isinstance(ref, fm.Engine):
            if ref.name in ("width", "height"):
                return self.get("size", ref.name)
            if not self.is_item or self.parent is None:
                message = f"{self.trace}: {self.component.use} reads :{ref.name} but is no item"
                raise self._fail("formula-reach", message)
            drawn = self.parent.nodes[self.part_name].items
            return float(self.position + 1 if ref.name == "index" else len(drawn))
        if isinstance(ref, fm.Role):
            return self.ctx.role_number(ref.path)
        if isinstance(ref, fm.Value):
            return self.get("value", ref.name)
        try:
            return self.measure(ref)
        except _Missing as missing:
            message = f"{self.trace}: {self.component.use} reads `{ref}`: {missing}"
            raise self._fail("missing-exposed", message) from missing

    # -- sizes and places

    def _size(self, size: str) -> float:
        """The size this instance gets: from its parent's part or list, or, at the top,
        the size it asks for."""
        if self.parent is None:
            return self.get("preferred", size)
        if self.is_item:
            part = self.parent.nodes[self.part_name].part
            axis = "main" if size == part.main else "cross"
            return self.parent.get(axis, self.part_name).sizes[self.position]
        return self.parent.get("part", self.part_name, size)

    def _geometry(self, name: str, key: str) -> float:
        node = self.nodes[name]
        part, spec = node.part, node.part.spec
        where = f"parts.{name}.{key}"
        if part.kind == "line":
            if key in ("x1", "y1", "x2", "y2"):
                return self.number(where, spec[key])
            ends = ("x1", "x2") if key in ("x", "width") else ("y1", "y2")
            first, second = (self.get("part", name, end) for end in ends)
            return min(first, second) if key in ("x", "y") else abs(second - first)
        if key in ("x", "y"):
            return self.number(where, spec[key]) if key in spec else 0.0
        if not node.present:
            return 0.0
        if part.kind == "text" and not (key == "width" and "width" in spec):
            lines = self.get("lines", name)
            assert node.style is not None
            return lines.natural if key == "width" else len(lines.lines) * node.style.line_height
        if key in spec:
            return self.number(where, spec[key])
        if part.kind == "image" and key == "height" and node.picture is not None:
            pixels = node.picture.variants[first_variant(node.picture)]["pixels"]
            return self.get("part", name, "width") * pixels["height"] / pixels["width"]
        if node.child is not None:
            return node.child.get("preferred", key)
        if part.kind == "repeat":
            return self.get("main" if key == part.main else "cross", name).asked
        raise Fault()  # a size the part needs, recorded when the component was read

    def _lines(self, name: str) -> Broken:
        node = self.nodes[name]
        assert node.style is not None
        width = self.get("part", name, "width") if "width" in node.part.spec else None
        return break_lines(node.text, width, node.style, self.ctx.language)

    def word(self, where: str, raw: Any, default: str) -> str:
        _, value, _ = self.pick(where, raw)
        return value if isinstance(value, str) else default

    def setting(self, name: str, key: str) -> str:
        """A list's operator setting, or its default."""
        part = self.nodes[name].part
        where = f"parts.{name}.{part.operator}.{key}"
        return self.word(where, part.settings.get(key), WORDS[key][0])

    def _arrange(self, name: str, axis: str) -> Arrangement:
        """A list's items laid out along its line (`main`) or across it (`cross`)."""
        node = self.nodes[name]
        part, items = node.part, node.items
        count = len(items)
        cross = "height" if part.main == "width" else "width"
        size = part.main if axis == "main" else cross
        given = self.get("part", name, size) if size in part.spec else None
        if axis == "cross":
            align = self.setting(name, "align-items")
            stretched = align == "stretch" and given is not None
            asked = None if stretched else [item.get("preferred", size) for item in items]
            line = given if given is not None else max(asked or [0.0])
            sizes = [line] * count if align == "stretch" else list(asked or [])
            shift = {"center": 0.5, "end": 1.0}.get(align, 0.0)
            offsets = tuple((line - each) * shift for each in sizes)
            return Arrangement(offsets, tuple(sizes), max(asked) if asked else line)
        raw = part.settings.get("gap")
        gap = self.number(f"parts.{name}.{part.operator}.gap", raw) if raw is not None else 0.0
        gaps = gap * max(count - 1, 0)
        if self.setting(name, "sizes") == "own":
            sizes = [item.get("preferred", size) for item in items]
        elif given is None:
            message = f"{self.trace}/{name}: the list shares its {size} equally, and is given none"
            raise self._fail("no-size", message, where=f"{self.trace}/{name}")
        else:
            sizes = [(given - gaps) / count] * count if count else []
        asked = sum(sizes) + gaps
        free = given - asked if given is not None else 0.0
        justify = self.setting(name, "justify-content")
        if justify == "space-between" and count > 1 and free > 0:
            gap, free = gap + free / (count - 1), 0.0
        at = {"center": free / 2, "end": free}.get(justify, 0.0)
        offsets = []
        for each in sizes:
            offsets.append(at)
            at += each + gap
        return Arrangement(tuple(offsets), tuple(sizes), asked)

    def item_frame(self, name: str, position: int) -> tuple[float, float, float, float]:
        """An item's frame within its list's part: x, y, width, height."""
        main, cross = self.get("main", name), self.get("cross", name)
        along = (main.offsets[position], main.sizes[position])
        across = (cross.offsets[position], cross.sizes[position])
        (x, width), (y, height) = (
            (along, across) if self.nodes[name].part.main == "width" else (across, along)
        )
        return x, y, width, height

    # -- reading the frames below

    def measure(self, path: fm.Path) -> float:
        """A path's measure in this instance's frame. Raises `_Missing` and `Fault`."""
        steps = list(path.steps)
        if path.option:
            steps = self._option_steps(path.option) + steps
        axis = "x" if path.measure in ("x", "width", "right", "center") else "y"
        if path.measure in ("width", "height"):
            return self._extent(steps, axis)
        place = self._position(steps, axis)
        if path.measure in ("x", "y"):
            return place
        share = 1.0 if path.measure in ("right", "bottom") else 0.5
        return place + share * self._extent(steps, axis)

    def _option_steps(self, name: str) -> list[fm.Step]:
        chosen = self.options.get(name)
        if chosen is None:
            raise Fault()  # recorded when the content was read
        option = self.component.options[name]
        steps = [fm.Step(self.component.repeats_over[option.items or ""], chosen["item"], True)]
        return [*steps, fm.Step(chosen["point"])] if option.point else steps

    def _item(self, node: Node, step: fm.Step) -> int:
        items = node.items
        if items and not step.by_id and step.item in ("first", "last"):
            return 0 if step.item == "first" else len(items) - 1
        for position, item in enumerate(items):
            if step.by_id and item.given.get("id") == step.item:
                return position
        raise _Missing(f"the list `{step.name}` draws no item {step}")

    def _position(self, steps: list[fm.Step], axis: str) -> float:
        first, rest = steps[0], steps[1:]
        node = self.nodes[first.name]
        base = self.get("part", first.name, axis)
        if node.part.kind == "repeat" and first.item is not None:
            position = self._item(node, first)
            x, y, _, _ = self.item_frame(first.name, position)
            inner = node.items[position]._exposed_position(rest, axis) if rest else 0.0
            return base + (x if axis == "x" else y) + inner
        if not rest or not node.present:
            return base
        if node.child is not None:
            return base + node.child._exposed_position(rest, axis)
        return base + self._point(first.name, rest[0].name)[0 if axis == "x" else 1]

    def _extent(self, steps: list[fm.Step], axis: str) -> float:
        first, rest = steps[0], steps[1:]
        node = self.nodes[first.name]
        size = "width" if axis == "x" else "height"
        if node.part.kind == "repeat" and first.item is not None:
            item = node.items[self._item(node, first)]
            return item._exposed_extent(rest, axis) if rest else item.get("size", size)
        if not rest:
            return self.get("part", first.name, size)
        if not node.present:
            return 0.0
        if node.child is not None:
            return node.child._exposed_extent(rest, axis)
        self._point(first.name, rest[0].name)
        return 0.0

    def _exposer(self, steps: list[fm.Step]) -> tuple[str, str | None]:
        """What an exposed name reaches: a part, or an exposed image part and its point."""
        step = steps[0]
        if step.name in self.component.exposes:
            return step.name, None
        for name in self.component.exposes:
            node = self.nodes.get(name)
            picture = node.picture if node and node.part.kind == "image" else None
            if picture and step.name in picture.points and step.item is None and len(steps) == 1:
                return name, step.name
        raise _Missing(f"{self.component.use} exposes no part or point `{step}`")

    def _exposed_position(self, steps: list[fm.Step], axis: str) -> float:
        name, point = self._exposer(steps)
        if point is None:
            return self._position(steps, axis)
        return self.get("part", name, axis) + self._point(name, point)[0 if axis == "x" else 1]

    def _exposed_extent(self, steps: list[fm.Step], axis: str) -> float:
        _, point = self._exposer(steps)
        return self._extent(steps, axis) if point is None else 0.0

    def _point(self, name: str, point: str) -> tuple[float, float]:
        points = self.get("points", name)
        if point not in points:
            raise _Missing(f"the picture of `{name}` exposes no point `{point}`")
        return points[point]

    def _mapped_points(self, name: str) -> dict[str, tuple[float, float]]:
        """The picture's exposed points mapped into its part's frame: the picture drawn
        whole, centred, as large as the frame allows."""
        picture = self.nodes[name].picture
        if picture is None:
            return {}
        first = first_variant(picture)
        pixels = picture.variants[first]["pixels"]
        width, height = self.get("part", name, "width"), self.get("part", name, "height")
        scale = min(width / pixels["width"], height / pixels["height"])
        left = (width - pixels["width"] * scale) / 2
        top = (height - pixels["height"] * scale) / 2
        return {
            point: (left + places[first]["x"] * scale, top + places[first]["y"] * scale)
            for point, places in sorted(picture.points.items())
            if first in places
        }

    # -- what is drawn

    def paint(self, name: str, prop: str) -> tuple[str | None, str]:
        """A part's paint, as a role, and where it comes from. `:colour.<member>` paints
        with the role the foundations map that member of the instance's colour family to
        (DEC-004 point 10); an instance with no family, a family the foundations do not
        declare, or one that lacks the member paints nothing. Raises `Fault`."""
        part = self.nodes[name].part
        if name in self.overrides and OVERRIDDEN.get(part.kind) == prop:
            return self.overrides[name]
        _, value, chosen = self.pick(f"parts.{name}.{part.kind}.{prop}", part.props.get(prop))
        if not isinstance(value, str):
            return None, ""
        source = f"option:{chosen}" if chosen else f"default:{self.component.use}"
        if not value.startswith(FAMILY):
            return value, source
        where = f"{self.trace}/{name}"
        if self.family is None:
            message = f"{where}: paints `{value}`, and has no colour family"
            raise self._fail("no-colour", message, where)
        members = self.ctx.family(self.family)
        if members is None:
            message = (
                f"{where}: paints `{value}` of the colour family `{self.family}`, which the "
                "foundations do not declare"
            )
            raise self._fail("no-colour", message, where)
        member = value[len(FAMILY) :]
        if member not in members:
            message = (
                f"{where}: paints `{value}`, and the colour family `{self.family}` has no "
                f"member `{member}`"
            )
            raise self._fail("no-colour", message, where)
        return members[member], self.family_source or source

    def shortfalls(self) -> list[tuple[str, float, float]]:
        """Each size this instance gets that is less than it asks for: size, gets, asks.
        Raises `Fault`."""
        if self.parent is None:
            return []
        short = []
        for size in ("width", "height"):
            if size in self.component.preferred:
                gets, asks = self.get("size", size), self.get("preferred", size)
                if asks - gets > TOLERANCE:
                    short.append((size, gets, asks))
        return short


def place_top(ctx: Context, top: str, content: Mapping[str, Any]) -> Instance | None:
    """The piece's top component placed with its content, every part below it built;
    `None`, with a finding, where the top names no component, or one whose file cannot be
    read (`Context.component`). The piece itself names its top, so the finding on a top
    that names no component lies there, at `top`, and says so as `piece`."""
    trace = top.split("/")[-1]
    component = ctx.component(top)
    if component is None:
        if not ctx.unreadable(top):
            message = f"the piece's top names no component `{top}`"
            ctx.add(
                Finding("unknown-component", FAILS, message, where="top", extra={"piece": True})
            )
        return None
    if not component.top:
        ctx.report("not-top", f"the piece's top `{top}` declares no layouts", where=trace, use=top)
    return Instance(ctx, component, content, trace=trace, content_path="")
