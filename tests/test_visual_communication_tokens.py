"""Brands and the foundations' declarations (DEC-004): the shipped foundations, the test
brand resolved in every combination, and what a brand or a declarations file is refused
for, each refusal built in the test's own folder from a copy of a valid one."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import FOUNDATIONS, TEST_BRAND, write

tokens, keys, env, findings = load("visual-communication", "tokens", "keys", "env", "findings")

ROLES = FOUNDATIONS / "roles.yaml"


@pytest.fixture(scope="module")
def foundations() -> Any:
    return tokens.read_declarations(ROLES)


@pytest.fixture(scope="module")
def brand(foundations: Any) -> Any:
    return tokens.read_brand(TEST_BRAND, foundations)


def brand_copy(tmp_path: Path) -> Path:
    """A copy of the test brand's version folder, to change."""
    target = tmp_path / "test-brand" / "1.0.0"
    shutil.copytree(TEST_BRAND, target)
    return target


def edit_json(path: Path, change: Callable[[dict[str, Any]], None]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def at(data: dict[str, Any], dotted: str) -> tuple[dict[str, Any], str]:
    """The mapping that holds the last segment of `dotted`, a path through `data`'s keys
    where `|` separates them (a key may hold a `.`), and that segment."""
    *parents, last = dotted.split("|")
    for key in parents:
        data = data[key]
    return data, last


def setting(dotted: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def change(data: dict[str, Any]) -> None:
        holder, key = at(data, dotted)
        holder[key] = value

    return change


def dropping(dotted: str) -> Callable[[dict[str, Any]], None]:
    def change(data: dict[str, Any]) -> None:
        holder, key = at(data, dotted)
        del holder[key]

    return change


def codes(found: Any) -> set[str]:
    return {finding.code for finding in found}


# --- the foundations ----------------------------------------------------------------------------


def test_the_foundations_declare_the_shared_roles_axes_and_pair(foundations: Any) -> None:
    assert foundations.roles["text-primary"] == tokens.Role("text-primary", "color")
    assert foundations.roles["space.3"].type == "dimension"
    assert foundations.roles["type.body"].type == "typography"
    assert set(foundations.axes) == {"colour-scheme", "contrast"}
    assert foundations.axes["contrast"] == tokens.Axis(
        "contrast", "value", ("standard", "high"), "standard"
    )
    assert foundations.pairs == (tokens.Pair("text-primary", "background", "text"),)
    assert foundations.pairs[0].minimum == 4.5
    assert foundations.families == {}
    assert {"space", "type", "font", "text-primary"} <= set(foundations.top_groups)


ROLES_TEXT = """\
pkit_schema: visual-communication:roles
schema_version: 1
roles:
  ink: {type: color}
  paper: {type: color}
  gap: {type: dimension}
axes:
  colour-scheme: {kind: value, modes: [light, dark], default: light}
families: {}
pairs:
  - {text: ink, under: paper, level: text}
"""


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("pkit_schema: visual-communication:roles", "pkit_schema: x:y", "roles-unreadable"),
        ("ink: {type: color}", "ink: {type: shadow}", "role-type"),
        ("ink: {type: color}", "Ink: {type: color}", "role-name"),
        ("ink: {type: color}", "component.ink: {type: color}", "role-name"),
        ("gap: {type: dimension}", "ink.gap: {type: color}", "role-name"),
        ("gap: {type: dimension}", "gap: {type: dimension, default: ink}", "role-default"),
        ("gap: {type: dimension}", "gap: {type: dimension, default: '{ink}'}", "role-default"),
        ("default: light}", "default: dim}", "axis-shape"),
        ("modes: [light, dark]", "modes: [light]", "axis-shape"),
        ("kind: value", "kind: hue", "axis-shape"),
        ("families: {}", "families: {warm: {first: gap}}", "family-shape"),
        ("level: text", "level: huge", "pair-shape"),
        ("text: ink,", "text: gap,", "pair-shape"),
    ],
)
def test_declarations_the_capability_cannot_read_are_refused(
    tmp_path: Path, old: str, new: str, code: str
) -> None:
    assert old in ROLES_TEXT
    path = write(tmp_path / "roles.yaml", ROLES_TEXT.replace(old, new))
    with pytest.raises(tokens.TokenError) as raised:
        tokens.read_declarations(path, library="foundations@1.0.0", shown="roles.yaml")
    assert code in codes(raised.value.findings)
    assert all(f.library == "foundations@1.0.0" for f in raised.value.findings)


def test_a_role_may_default_to_an_older_role_of_its_type(tmp_path: Path) -> None:
    text = ROLES_TEXT.replace("gap: {type: dimension}", "rule: {type: color, default: '{ink}'}")
    declarations = tokens.read_declarations(write(tmp_path / "roles.yaml", text))
    assert declarations.roles["rule"] == tokens.Role("rule", "color", "ink")


# --- the test brand -----------------------------------------------------------------------------


def test_the_test_brand_reads_with_no_findings(brand: Any) -> None:
    assert (brand.name, brand.version) == ("test-brand", "1.0.0")
    assert brand.findings == ()
    assert brand.open == ("accent", "space")
    assert set(brand.axes) == {"colour-scheme", "contrast"}


def test_the_test_brand_gives_every_role_a_value_of_its_type_in_every_combination(
    brand: Any, foundations: Any
) -> None:
    combinations = brand.combinations()
    assert [keys.key_of(c, brand.axes) for c in combinations] == [
        "default",
        "colour-scheme.dark",
        "contrast.high",
        "colour-scheme.dark+contrast.high",
    ]
    for combination in combinations:
        for path, role in foundations.roles.items():
            value = brand.resolve(path, combination)
            assert brand.type_of(path) == role.type
            assert value is not None, (path, combination)


def test_text_primary_on_background_reaches_the_text_level_in_every_combination(
    brand: Any,
) -> None:
    light = brand.resolve("text-primary", {})
    assert tokens.contrast_ratio(light, brand.resolve("background", {})) >= 4.5
    for combination in brand.combinations():
        text = brand.resolve("text-primary", combination)
        under = brand.resolve("background", combination)
        assert tokens.contrast_ratio(text, under) >= 4.5, combination


def test_values_are_given_in_their_canonical_form(brand: Any) -> None:
    assert brand.resolve("background", {}) == {
        "colorSpace": "srgb",
        "components": [1.0, 1.0, 1.0],
        "alpha": 1,
    }
    assert brand.resolve("space.3", {"contrast": "high"}) == {"value": 16, "unit": "px"}
    assert brand.resolve("font.body", {}) == ["Source Sans Pro"]
    assert brand.resolve("type.heading", {}) == {
        "fontFamily": ["Source Sans Pro Semibold"],
        "fontSize": {"value": 24, "unit": "px"},
        "fontWeight": 600,
        "letterSpacing": {"value": 0, "unit": "px"},
        "lineHeight": 1.2,
    }


def test_a_value_axis_changes_colours_alone(brand: Any) -> None:
    dark = {"colour-scheme": "dark"}
    assert brand.resolve("background", dark) != brand.resolve("background", {})
    assert brand.resolve("type.body", dark) == brand.resolve("type.body", {})


def test_a_role_the_brand_does_not_export_or_a_mode_the_axes_lack_is_refused(brand: Any) -> None:
    with pytest.raises(tokens.UnknownRole):
        brand.resolve("scheme.paper", {})
    with pytest.raises(tokens.UnknownRole):
        brand.type_of("palette.white")
    with pytest.raises(keys.BadKey):
        brand.resolve("background", {"colour-scheme": "sepia"})


def test_the_brand_names_the_font_files_it_holds(brand: Any) -> None:
    assert brand.families() == ("Source Sans Pro", "Source Sans Pro Semibold")
    assert brand.font_file("Source Sans Pro") == TEST_BRAND / "fonts" / "SourceSansPro-Regular.otf"
    with pytest.raises(env.MissingFont, match="`Comic Sans`"):
        brand.font_file("Comic Sans")


# --- a brand the capability cannot resolve ------------------------------------------------------

BASE = "tokens/base.tokens.json"
DARK = "tokens/dark.tokens.json"
RESOLVER = "test-brand.resolver.json"
PX = {"value": 5, "unit": "px"}


@pytest.mark.parametrize(
    ("file", "change", "code"),
    [
        (BASE, setting("text-primary|$value", "{scheme.nothing}"), "alias-dangling"),
        (BASE, setting("scheme|paper|$value", "{background}"), "alias-loop"),
        (BASE, setting("text-primary|$value", "{space.1}"), "alias-type"),
        (BASE, dropping("surface"), "role-missing"),
        (BASE, setting("surface", {"$type": "dimension", "$value": PX}), "role-type"),
        (BASE, setting("space|1|$value", {"value": 1, "unit": "rem"}), "token-value"),
        (BASE, setting("space|5", {"$value": PX}), "token-shared-group"),
        (BASE, setting("scheme|Paper", {"$value": "{palette.white}"}), "token-name"),
        (BASE, setting("scheme|$type", "shadow"), "token-type"),
        (BASE, setting("scheme|paper|$foo", 1), "tokens-shape"),
        (
            BASE,
            setting("background|$extensions", {"pkit.visual-communication": {}}),
            "tokens-shape",
        ),
        (BASE, dropping("type|body|$value|lineHeight"), "token-value"),
        (
            DARK,
            setting("space", {"$type": "dimension", "1": {"$value": PX}}),
            "value-axis-changes-size",
        ),
        (RESOLVER, setting("version", "2024"), "resolver-shape"),
        (RESOLVER, setting("$schema", "x"), "resolver-shape"),
        (RESOLVER, setting("resolutionOrder", [{"$ref": "#/sets/palette"}]), "resolver-shape"),
        (RESOLVER, setting("modifiers|density", {"contexts": {}, "default": "x"}), "brand-axis"),
        (RESOLVER, setting("modifiers|colour-scheme|default", "dark"), "brand-axis"),
        (RESOLVER, dropping("modifiers|contrast|contexts|high"), "brand-axis"),
        (RESOLVER, setting("sets|base|sources", [{"$ref": "../base.json"}]), "brand-file"),
        (RESOLVER, setting("sets|base|sources", [{"$ref": "tokens/none.json"}]), "brand-file"),
    ],
)
def test_a_brand_that_cannot_be_resolved_is_refused_naming_why(
    tmp_path: Path, foundations: Any, file: str, change: Callable[[dict[str, Any]], None], code: str
) -> None:
    folder = brand_copy(tmp_path)
    edit_json(folder / file, change)
    with pytest.raises(tokens.TokenError) as raised:
        tokens.read_brand(folder, foundations, root=tmp_path)
    assert code in codes(raised.value.findings), raised.value.findings
    assert all(f.library == "test-brand@1.0.0" for f in raised.value.findings)
    assert all(f.file.startswith("test-brand/1.0.0/") for f in raised.value.findings)


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("kind: brand", "kind: components", "brand-kind"),
        ('dtcg: "2025.10"', 'dtcg: "2024.1"', "brand-dtcg"),
        ("resolver: test-brand.resolver.json", "resolver: missing.json", "brand-file"),
        ("pkit_schema: visual-communication:library", "pkit_schema: x:y", "brand-unreadable"),
    ],
)
def test_a_brand_whose_library_file_is_wrong_is_refused(
    tmp_path: Path, foundations: Any, old: str, new: str, code: str
) -> None:
    folder = brand_copy(tmp_path)
    library = folder / "library.yaml"
    text = library.read_text(encoding="utf-8")
    assert old in text
    library.write_text(text.replace(old, new), encoding="utf-8")
    with pytest.raises(tokens.TokenError) as raised:
        tokens.read_brand(folder, foundations)
    assert code in codes(raised.value.findings)


# --- a brand usable with findings ---------------------------------------------------------------


def test_an_open_role_the_brand_does_not_export_is_a_finding(
    tmp_path: Path, foundations: Any
) -> None:
    folder = brand_copy(tmp_path)
    library = folder / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace("[accent, space]", "[accent, spac]"),
        encoding="utf-8",
    )
    found = tokens.read_brand(folder, foundations).findings
    assert codes(found) == {"open-unknown"}


def test_a_font_file_the_brand_does_not_hold_is_a_finding_and_missing_when_drawn(
    tmp_path: Path, foundations: Any
) -> None:
    folder = brand_copy(tmp_path)
    (folder / "fonts" / "SourceSansPro-Semibold.otf").unlink()
    read = tokens.read_brand(folder, foundations)
    assert codes(read.findings) == {"font-missing"}
    assert read.font_file("Source Sans Pro").is_file()
    with pytest.raises(env.MissingFont, match="does not hold"):
        read.font_file("Source Sans Pro Semibold")


def test_a_family_with_no_file_declared_is_a_finding(tmp_path: Path, foundations: Any) -> None:
    folder = brand_copy(tmp_path)
    edit_json(folder / BASE, dropping("font|heading|$extensions"))
    read = tokens.read_brand(folder, foundations)
    assert codes(read.findings) == {"font-missing"}
    with pytest.raises(env.MissingFont, match="has no file"):
        read.font_file("Source Sans Pro Semibold")


def test_a_font_named_by_its_hash_is_found_in_the_locations_fonts(
    tmp_path: Path, foundations: Any
) -> None:
    folder = brand_copy(tmp_path)
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    regular = folder / "fonts" / "SourceSansPro-Regular.otf"
    held = fonts / "any-name.otf"
    shutil.copyfile(regular, held)
    digest = f"sha256:{hashlib.sha256(regular.read_bytes()).hexdigest()}"
    files = "font|body|$extensions|pkit.visual-communication|files"
    edit_json(folder / BASE, setting(files, {"Source Sans Pro": {"hash": digest}}))
    read = tokens.read_brand(folder, foundations, fonts=fonts)
    assert read.findings == ()
    assert read.font_file("Source Sans Pro") == held
    unheld = tokens.read_brand(folder, foundations)
    assert codes(unheld.findings) == {"font-missing"}


def test_a_font_extension_of_another_shape_is_a_finding(tmp_path: Path, foundations: Any) -> None:
    folder = brand_copy(tmp_path)
    measure = "font|body|$extensions|pkit.visual-communication|measure"
    edit_json(folder / BASE, setting(measure, "shaped"))
    assert "font-shape" in codes(tokens.read_brand(folder, foundations).findings)


def test_a_pair_below_its_contrast_fails_in_the_combination_it_lies_in(
    tmp_path: Path, foundations: Any
) -> None:
    folder = brand_copy(tmp_path)
    edit_json(folder / DARK, setting("scheme|ink|$value", "{palette.night.800}"))
    found = tokens.read_brand(folder, foundations).findings
    assert codes(found) == {"pair-contrast"}
    (finding,) = found
    assert finding.level == findings.FAILS
    assert "`colour-scheme.dark`" in finding.message
    assert finding.where == "text-primary"


def test_a_translucent_ground_asks_for_attention(tmp_path: Path, foundations: Any) -> None:
    folder = brand_copy(tmp_path)
    paper = {"colorSpace": "srgb", "components": [1, 1, 1], "alpha": 0.5}
    edit_json(folder / BASE, setting("scheme|paper|$value", paper))
    found = tokens.read_brand(folder, foundations).findings
    assert codes(found) == {"pair-translucent"}
    assert {f.level for f in found} == {findings.ATTENTION}


# --- contrast -----------------------------------------------------------------------------------


def colour(*components: float, alpha: float = 1) -> dict[str, Any]:
    return {"colorSpace": "srgb", "components": list(components), "alpha": alpha}


def test_contrast_is_wcag_contrast() -> None:
    assert tokens.contrast_ratio(colour(0, 0, 0), colour(1, 1, 1)) == pytest.approx(21)
    assert tokens.contrast_ratio(colour(1, 1, 1), colour(0, 0, 0)) == pytest.approx(21)
    assert tokens.contrast_ratio(colour(1, 1, 1), colour(1, 1, 1)) == pytest.approx(1)
    grey = 0.4663  # #777777, 4.48 on white
    assert tokens.contrast_ratio(colour(grey, grey, grey), colour(1, 1, 1)) == pytest.approx(
        4.48, abs=0.01
    )


def test_a_translucent_text_is_laid_over_its_ground_first() -> None:
    half = tokens.contrast_ratio(colour(0, 0, 0, alpha=0.5), colour(1, 1, 1))
    assert half == pytest.approx(tokens.contrast_ratio(colour(0.5, 0.5, 0.5), colour(1, 1, 1)))
