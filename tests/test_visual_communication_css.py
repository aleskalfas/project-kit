"""The CSS code writer, spelling form 1 (visual-communication DEC-004 point 4, DEC-005 points 7
to 9): its names, its values, its rules, and the reference output pinned to its version.

The rules are checked as a browser reads them: a small cascade below works out what each
custom property holds on an element that sets the axes' attributes, at the page's root or
in an area inside another, and compares it with the values document."""

from __future__ import annotations

import ast
import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import CAPABILITY, FOUNDATIONS, TEST_BRAND, TEST_PARTS

css, css_declaration, seam, values, tokens, keys = load(
    "visual-communication",
    "plugins.css",
    "plugins.css_declaration",
    "plugins.seam",
    "values",
    "tokens",
    "keys",
)

LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0"}

#: The style sheet the writer writes for the test brand, by the writer's version. A change
#: of output is a new version of the writer (DEC-005 point 9): add its reference here.
REFERENCE = {
    "1.0.0": """\
/* A brand's values as CSS custom properties, spelling form 1 of the css code writer,
   from foundations 1.0.0, test-brand 1.0.0.
   `pkit visual write-code` writes this file: write it again, never edit it. */

:root {
  --accent: #0969da;
  --background: #ffffff;
  --family--blue--fill: #ddf4ff;
  --family--blue--line: #0969da;
  --family--blue--text: #033d8b;
  --family--green--fill: #dafbe1;
  --family--green--line: #1a7f37;
  --family--green--text: #044f1e;
  --family--neutral--fill: #f6f8fa;
  --family--neutral--line: #d0d7de;
  --family--neutral--text: #1f2328;
  --family--orange--fill: #fff1e5;
  --family--orange--line: #bc4c00;
  --family--orange--text: #762c00;
  --family--purple--fill: #fbefff;
  --family--purple--line: #8250df;
  --family--purple--text: #512a97;
  --family--red--fill: #ffebe9;
  --family--red--line: #cf222e;
  --family--red--text: #82071e;
  --font--body: "Source Sans Pro";
  --font--heading: "Source Sans Pro Semibold";
  --line: #d0d7de;
  --size--figure: 960px;
  --size--slide: 1280px;
  --space--1: 4px;
  --space--2: 8px;
  --space--3: 16px;
  --space--4: 32px;
  --stroke--thick: 2px;
  --stroke--thin: 1px;
  --surface: #f6f8fa;
  --text-primary: #1f2328;
  --text-secondary: #57606a;
}

[data-colour-scheme="light"] {
  --accent: #0969da;
  --background: #ffffff;
  --family--blue--fill: #ddf4ff;
  --family--blue--line: #0969da;
  --family--blue--text: #033d8b;
  --family--green--fill: #dafbe1;
  --family--green--line: #1a7f37;
  --family--green--text: #044f1e;
  --family--neutral--fill: #f6f8fa;
  --family--neutral--line: #d0d7de;
  --family--neutral--text: #1f2328;
  --family--orange--fill: #fff1e5;
  --family--orange--line: #bc4c00;
  --family--orange--text: #762c00;
  --family--purple--fill: #fbefff;
  --family--purple--line: #8250df;
  --family--purple--text: #512a97;
  --family--red--fill: #ffebe9;
  --family--red--line: #cf222e;
  --family--red--text: #82071e;
  --line: #d0d7de;
  --surface: #f6f8fa;
  --text-primary: #1f2328;
  --text-secondary: #57606a;
}

[data-colour-scheme="dark"] {
  --accent: #4493f8;
  --background: #0d1117;
  --family--blue--fill: #0c2d6b;
  --family--blue--line: #4493f8;
  --family--blue--text: #a5d6ff;
  --family--green--fill: #033a16;
  --family--green--line: #2ea043;
  --family--green--text: #7ee787;
  --family--neutral--fill: #161b22;
  --family--neutral--line: #30363d;
  --family--neutral--text: #e6edf3;
  --family--orange--fill: #5a1e02;
  --family--orange--line: #db6d28;
  --family--orange--text: #ffc680;
  --family--purple--fill: #3c1e70;
  --family--purple--line: #a371f7;
  --family--purple--text: #e2c5ff;
  --family--red--fill: #67060c;
  --family--red--line: #f85149;
  --family--red--text: #ffc1ba;
  --line: #30363d;
  --surface: #161b22;
  --text-primary: #e6edf3;
  --text-secondary: #8d96a0;
}

[data-contrast="high"] {
  --background: #ffffff;
  --family--blue--text: #000000;
  --family--green--text: #000000;
  --family--neutral--line: #000000;
  --family--neutral--text: #000000;
  --family--orange--text: #000000;
  --family--purple--text: #000000;
  --family--red--text: #000000;
  --line: #000000;
  --text-primary: #000000;
  --text-secondary: #1f2328;
}

[data-colour-scheme="dark"][data-contrast="high"] {
  --background: #000000;
  --family--blue--text: #ffffff;
  --family--green--text: #ffffff;
  --family--neutral--line: #ffffff;
  --family--neutral--text: #ffffff;
  --family--orange--text: #ffffff;
  --family--purple--text: #ffffff;
  --family--red--text: #ffffff;
  --line: #ffffff;
  --text-primary: #ffffff;
  --text-secondary: #e6edf3;
}
""",
}


@pytest.fixture(scope="module")
def brand() -> Any:
    return tokens.read_brand(TEST_BRAND, tokens.read_declarations(FOUNDATIONS / "roles.yaml"))


def axes_of(brand: Any) -> dict[str, dict[str, Any]]:
    return {
        axis.name: {"kind": axis.kind, "modes": list(axis.modes), "default": axis.default}
        for axis in brand.axes.values()
    }


def written_document(brand: Any) -> dict[str, Any]:
    """The test brand's values document, with the tokens the writer has a form for."""
    doc = values.document(brand, brand.combinations(), LOCK)
    doc["tokens"] = {p: t for p, t in doc["tokens"].items() if t["type"] in css.KINDS}
    return doc


# --- the cascade, as a browser reads the rules --------------------------------------------------

_BLOCK = re.compile(r"^(?P<selector>[^\n]+) \{\n(?P<body>(?:  [^\n]+\n)*)\}$", re.M)
_ATTRIBUTE = re.compile(r'\[data-(?P<axis>[a-z0-9-]+)="(?P<mode>[a-z0-9-]+)"\]')
_DECLARATION = re.compile(r"^  (?P<name>--[A-Za-z0-9-]+): (?P<value>.+);$")


@dataclass(frozen=True)
class Rule:
    modes: tuple[tuple[str, str], ...] | None  # None for `:root`
    declarations: dict[str, str]


def parsed(sheet: str) -> list[Rule]:
    rules = []
    for match in _BLOCK.finditer(sheet):
        selector = match["selector"]
        if selector == ":root":
            modes = None
        else:
            modes = tuple((m["axis"], m["mode"]) for m in _ATTRIBUTE.finditer(selector))
            assert "".join(f'[data-{a}="{m}"]' for a, m in modes) == selector, selector
        lines = match["body"].splitlines()
        found = {}
        for line in lines:
            declared = _DECLARATION.match(line)
            assert declared is not None, line
            found[declared["name"]] = declared["value"]
        assert len(found) == len(lines), f"a name is declared twice in {selector}"
        rules.append(Rule(modes, found))
    return rules


def computed(
    rules: list[Rule], attributes: Mapping[str, str], inherited: Mapping[str, str] | None
) -> dict[str, str]:
    """What each custom property holds on an element with `attributes`: the root when
    `inherited` is None, else an element inside one whose values are `inherited`. The rule
    of the highest specificity wins, the later of two; what no rule sets is inherited."""
    best: dict[str, tuple[tuple[int, int], str]] = {}
    for order, rule in enumerate(rules):
        if rule.modes is None:
            if inherited is not None:
                continue
            specificity = 1
        else:
            if not all(attributes.get(axis) == mode for axis, mode in rule.modes):
                continue
            specificity = len(rule.modes)
        for name, value in rule.declarations.items():
            if name not in best or (specificity, order) >= best[name][0]:
                best[name] = ((specificity, order), value)
    return {**(inherited or {}), **{name: value for name, (_, value) in best.items()}}


def expected(doc: Mapping[str, Any], key: str, prefix: str | None = None) -> dict[str, str]:
    return {
        css.name_of(path, prefix): css.value_of(token["type"], token["values"][key])
        for path, token in doc["tokens"].items()
    }


def assert_switches(sheet: str, doc: Mapping[str, Any], axes: Mapping[str, Any]) -> None:
    """Every combination is what the rules give: at the page's root, with every axis's
    attribute or with only those not at their default, and in an area that sets every
    axis's attribute inside a root at any other combination."""
    rules = parsed(sheet)
    read = {name: _Axis(tuple(a["modes"]), a["default"]) for name, a in axes.items()}
    every = keys.combinations({n: a.modes for n, a in read.items()}, read)
    for combination in every:
        key = keys.key_of(combination, read)
        wanted = expected(doc, key)
        assert computed(rules, combination, None) == wanted, f"the root at {key}"
        only = {a: m for a, m in combination.items() if m != read[a].default}
        assert computed(rules, only, None) == wanted, f"the root naming {key}'s modes alone"
        for outer in every:
            around = computed(rules, outer, None)
            inside = computed(rules, combination, around)
            assert inside == wanted, f"an area at {key} in a root at {keys.key_of(outer, read)}"


@dataclass(frozen=True)
class _Axis:
    modes: tuple[str, ...]
    default: str


# --- names --------------------------------------------------------------------------------------


def test_a_name_joins_the_segments_and_a_prefix_with_two_hyphens() -> None:
    assert css.name_of("space.1") == "--space--1"
    assert css.name_of("text-primary") == "--text-primary"
    assert css.name_of("space.1", "brand") == "--brand--space--1"
    assert css.name_of("component.tests.card.fill", "my-brand") == (
        "--my-brand--component--tests--card--fill"
    )


def test_no_two_token_paths_spell_one_name() -> None:
    paths = ["a.b-c", "a-b.c", "a.b.c", "a-b-c", "ab.c", "a.bc", "space.1", "space-1"]
    assert len({css.name_of(path) for path in paths}) == len(paths)
    assert len({css.name_of(path, "x") for path in paths}) == len(paths)


# --- values -------------------------------------------------------------------------------------


def colour(r: float, g: float, b: float, alpha: float = 1) -> dict[str, Any]:
    return {"colorSpace": "srgb", "components": [r, g, b], "alpha": alpha}


@pytest.mark.parametrize(
    ("type_", "value", "spelled"),
    [
        ("color", colour(1.0, 1.0, 1.0), "#ffffff"),
        ("color", colour(0, 0.5, 0.9647), "#0080f6"),
        ("color", colour(0.0018, 0.002, 1), "#0001ff"),
        ("color", colour(0, 0, 0, 0.5), "#00000080"),
        ("color", colour(0, 0, 0, 0), "#00000000"),
        ("dimension", {"value": 16, "unit": "px"}, "16px"),
        ("dimension", {"value": 1.5, "unit": "px"}, "1.5px"),
        ("dimension", {"value": -0.25, "unit": "px"}, "-0.25px"),
        ("dimension", {"value": 16.0, "unit": "px"}, "16px"),
        ("fontFamily", ["Source Sans Pro"], '"Source Sans Pro"'),
        ("fontFamily", ["A", "B C"], '"A", "B C"'),
        (
            "fontFamily",
            ['Say "hi"', "back\\slash", "tab\there"],
            r'"Say \"hi\"", "back\\slash", "tab\9 here"',
        ),
        ("fontWeight", 400, "400"),
        ("number", 1.4, "1.4"),
        ("number", 0, "0"),
    ],
)
def test_each_kind_of_value_has_one_spelling(type_: str, value: Any, spelled: str) -> None:
    assert css.value_of(type_, value) == spelled


@pytest.mark.parametrize(
    ("type_", "value"),
    [
        ("typography", {"fontFamily": ["A"], "fontSize": {"value": 16, "unit": "px"}}),
        ("shadow", {}),
        ("dimension", {"value": 1, "unit": "rem"}),
        ("color", {"colorSpace": "display-p3", "components": [1, 1, 1], "alpha": 1}),
        ("color", {"colorSpace": "srgb", "components": [1, 1], "alpha": 1}),
        ("fontFamily", "Source Sans Pro"),
        ("number", True),
        ("number", "1"),
    ],
)
def test_a_value_it_has_no_form_for_is_refused(type_: str, value: Any) -> None:
    with pytest.raises(css.CssError):
        css.value_of(type_, value)


def test_the_kinds_it_declares_are_the_kinds_it_spells() -> None:
    samples = {
        "color": colour(0, 0, 0),
        "dimension": {"value": 1, "unit": "px"},
        "fontFamily": ["A"],
        "fontWeight": 700,
        "number": 2,
        "typography": {},
    }
    spelled = set()
    for type_, sample in samples.items():
        try:
            css.value_of(type_, sample)
        except css.CssError:
            continue
        spelled.add(type_)
    assert spelled == set(css_declaration.DECLARATION["kinds"])
    assert set(samples) == set(tokens.TYPES)


# --- the style sheet ----------------------------------------------------------------------------


def test_the_test_brand_gives_the_reference_style_sheet_of_the_writers_version(
    brand: Any,
) -> None:
    assert css.VERSION in REFERENCE, f"no reference output for the css writer {css.VERSION}"
    sheet = css.write(written_document(brand), axes_of(brand))
    assert sheet == REFERENCE[css.VERSION]


def test_the_rules_give_every_combination_at_the_root_and_in_any_area(brand: Any) -> None:
    doc = written_document(brand)
    assert_switches(css.write(doc, axes_of(brand)), doc, axes_of(brand))


def test_a_prefix_changes_the_names_alone(brand: Any) -> None:
    doc = written_document(brand)
    plain = css.write(doc, axes_of(brand))
    prefixed = css.write(doc, axes_of(brand), prefix="brand")
    assert prefixed == plain.replace("  --", "  --brand--")
    names = re.findall(r"^  (--[^:]+):", prefixed, re.M)
    assert names and all(name.startswith("--brand--") for name in names)


def three_axes() -> tuple[dict[str, Any], dict[str, Any]]:
    """A values document over three axes, one whose default is not its first mode, with
    tokens that each axis, each pair, all three or none change, and one that changes in
    one combination alone."""
    axes = {
        "mood": {"kind": "value", "modes": ["calm", "loud"], "default": "calm"},
        "density": {"kind": "value", "modes": ["tight", "normal", "airy"], "default": "normal"},
        "theme": {"kind": "value", "modes": ["night", "day"], "default": "day"},
    }
    read = {name: _Axis(tuple(a["modes"]), a["default"]) for name, a in axes.items()}
    every = keys.combinations({n: a.modes for n, a in read.items()}, read)
    names = sorted(axes)
    subsets = [s for size in range(len(names) + 1) for s in itertools.combinations(names, size)]
    tokens_: dict[str, Any] = {}
    for subset in subsets:
        path = "by." + ("-".join(subset) or "none")
        tokens_[path] = {
            "type": "number",
            "values": {
                keys.key_of(c, read): sum(
                    (1 + read[a].modes.index(c[a])) * 10**i for i, a in enumerate(subset)
                )
                for c in every
            },
        }
    tokens_["only.loud-airy-night"] = {
        "type": "number",
        "values": {
            keys.key_of(c, read): int(c == {"mood": "loud", "density": "airy", "theme": "night"})
            for c in every
        },
    }
    doc = {
        "document": "visual-communication/values",
        "version": 2,
        "lock": {"lab": "1.0.0"},
        "keys": [keys.key_of(c, read) for c in every],
        "tokens": dict(sorted(tokens_.items())),
    }
    return doc, axes


def test_the_rules_hold_over_three_axes_with_tokens_changed_by_any_of_them() -> None:
    doc, axes = three_axes()
    sheet = css.write(doc, axes)
    assert_switches(sheet, doc, axes)
    selectors = [rule.modes for rule in parsed(sheet)]
    assert selectors[0] is None
    singles = [modes for modes in selectors[1:] if modes is not None and len(modes) == 1]
    assert [axis for ((axis, _),) in singles] == sorted(axis for ((axis, _),) in singles)


def test_a_rule_left_with_no_token_is_not_written(brand: Any) -> None:
    sheet = css.write(written_document(brand), axes_of(brand))
    assert '[data-contrast="standard"]' not in sheet
    assert sheet.count(" {\n") == 5


def test_one_document_gives_one_style_sheet(brand: Any) -> None:
    doc = written_document(brand)
    shuffled = {**doc, "tokens": dict(reversed(list(doc["tokens"].items())))}
    assert css.write(shuffled, axes_of(brand)) == css.write(doc, axes_of(brand))


# --- what it refuses ----------------------------------------------------------------------------


def test_it_refuses_a_size_axis_another_form_or_document_and_missing_combinations(
    brand: Any,
) -> None:
    """A size axis never reaches the writer: the command hands it a brand's values at the
    default of each size (DEC-021 point 8), so one handed to it is refused."""
    doc, axes = written_document(brand), axes_of(brand)
    with pytest.raises(css.CssError, match=r"size axis; .* at the default of every other axis"):
        css.write(doc, {**axes, "contrast": {**axes["contrast"], "kind": "size"}})
    with pytest.raises(css.CssError, match="form 2"):
        css.write(doc, axes, form=2)
    with pytest.raises(css.CssError, match="document"):
        css.write({**doc, "version": 1}, axes)
    with pytest.raises(css.CssError, match="every combination"):
        css.write({**doc, "keys": doc["keys"][:-1]}, axes)
    with pytest.raises(css.CssError, match="typography"):
        css.write(values.document(brand, brand.combinations(), LOCK), axes)


# --- its declaration ----------------------------------------------------------------------------


def test_its_declaration_is_plain_data_the_seam_ships_as_a_code_writer() -> None:
    source = (CAPABILITY / "scripts/_lib/plugins/css_declaration.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    found = seam.declaration("css", seam.CODE_WRITER)
    assert found is css_declaration.DECLARATION
    assert found["module"] == "css"
    assert found["forms"] == [1]
    assert found["programs"] == [] and found["services"] == []
    assert "css" in seam.names(seam.CODE_WRITER)
    assert found["version"] == css.VERSION


# --- a library's own roles (DEC-008 point 5) ---------------------------------------------------


def test_the_roles_of_a_library_locked_with_the_brand_are_written_at_their_defaults() -> None:
    scope = tokens.read_scope({"foundations": FOUNDATIONS, "test-parts": TEST_PARTS})
    brand = tokens.read_brand(TEST_BRAND, scope)
    doc = values.document(brand, brand.combinations(), {**LOCK, "test-parts": "1.0.0"})
    assert doc["version"] == 2
    doc["tokens"] = {p: t for p, t in doc["tokens"].items() if t["type"] in css.KINDS}
    sheet = css.write(doc, axes_of(brand))
    root = parsed(sheet)[0].declarations
    assert root["--test-parts--note"] == root["--text-primary"]
    assert root["--test-parts--gap"] == "8px"
    assert "--test-parts--warning" not in sheet
    assert_switches(sheet, doc, axes_of(brand))
    plain = css.write(written_document(brand), axes_of(brand))
    assert plain != sheet
    assert css.VERSION == "1.0.0"
