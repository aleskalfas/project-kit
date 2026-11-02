"""Brands and the foundations' declarations (DEC-004): the shipped foundations, the test
brand resolved in every combination, the test edition resolved over the test brand, its
base (point 6), and what a brand or a declarations file is refused for, each refusal built
in the test's own folder from a copy of a valid one."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    FOUNDATIONS,
    TEST_BRAND,
    TEST_EDITION,
    bound,
    copy_library,
    project,
    write,
    write_piece,
    yaml_text,
)

tokens, keys, env, findings, libraries, pl = load(
    "visual-communication", "tokens", "keys", "env", "findings", "libraries", "pipeline"
)

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
    assert all(f.library == "test-brand@1.0.0" for f in raised.value.findings)


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
    assert {f.who for f in found} == {"the owner of the brand test-brand"}


# --- a brand built on another (DEC-004 point 6) -------------------------------------------------

EDITION = "tokens/edition.tokens.json"
DARK_MODE = {"colour-scheme": "dark"}

#: The edition's accent in the dark colour scheme, `palette.orange.300`.
ORANGE = {"colorSpace": "srgb", "components": [1.0, 0.651, 0.3412], "alpha": 1}


@pytest.fixture(scope="module")
def edition(foundations: Any) -> Any:
    return tokens.read_brand(TEST_EDITION, foundations, locked={"test-brand": TEST_BRAND})


def chain_copy(tmp_path: Path) -> tuple[Path, Path]:
    """Copies of the test brand and of the edition built on it, to change."""
    folder = tmp_path / "test-edition" / "1.0.0"
    shutil.copytree(TEST_EDITION, folder)
    return brand_copy(tmp_path), folder


def replace_in(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def built_on_edition(tmp_path: Path, edition: Path) -> Path:
    """A third link: a copy of the edition, named `test-third`, whose base is the edition."""
    folder = tmp_path / "test-third" / "1.0.0"
    shutil.copytree(edition, folder)
    library = folder / "library.yaml"
    replace_in(library, "name: test-edition", "name: test-third")
    replace_in(
        library,
        "{name: test-brand, major: 1, base: true}",
        "{name: test-edition, major: 1, base: true}",
    )
    return folder


def test_a_brand_built_on_another_reads_over_its_base(edition: Any) -> None:
    assert edition.label == "test-edition@1.0.0"
    assert edition.base is not None
    assert edition.base.label == "test-brand@1.0.0"
    assert edition.findings == ()
    assert edition.open == ("accent",)
    assert edition.opened == {"accent"}
    assert edition.base.opened == {"accent", "space.1", "space.2", "space.3", "space.4"}
    assert edition.axes == edition.base.axes
    assert edition.roles == edition.base.roles


def test_an_open_roles_value_wins_where_the_brand_gives_it_and_the_bases_holds_elsewhere(
    edition: Any, brand: Any
) -> None:
    assert edition.resolve("accent", DARK_MODE) == ORANGE
    assert brand.resolve("accent", DARK_MODE) != ORANGE
    assert edition.resolve("accent", {}) == brand.resolve("accent", {})
    for combination in edition.combinations():
        assert edition.resolve("space.4", combination) == {"value": 40, "unit": "px"}
        assert brand.resolve("space.4", combination) == {"value": 32, "unit": "px"}
        for role in ("background", "text-primary", "line", "space.1", "type.body", "font.body"):
            assert edition.resolve(role, combination) == brand.resolve(role, combination)
    assert edition.font_file("Source Sans Pro") == brand.font_file("Source Sans Pro")


def test_an_alias_of_a_role_follows_its_merged_value(
    tmp_path: Path, foundations: Any, edition: Any
) -> None:
    for combination in edition.combinations():
        if combination["contrast"] == "high":
            text = edition.resolve("text-primary", combination)
            assert edition.resolve("accent", combination) == text
    base, folder = chain_copy(tmp_path)
    edit_json(base / BASE, setting("line|$value", "{accent}"))
    read = tokens.read_brand(folder, foundations, locked={"test-brand": base})
    assert read.findings == ()
    assert read.resolve("line", DARK_MODE) == ORANGE
    assert read.base is not None
    assert read.resolve("line", {}) == read.base.resolve("accent", {})


def test_a_brands_private_token_never_changes_its_bases(tmp_path: Path, foundations: Any) -> None:
    base, folder = chain_copy(tmp_path)
    black = {"colorSpace": "srgb", "components": [0, 0, 0]}
    edit_json(folder / EDITION, setting("palette|white", {"$value": black}))
    read = tokens.read_brand(folder, foundations, locked={"test-brand": base})
    assert read.findings == ()
    assert read.resolve("background", {})["components"] == [1.0, 1.0, 1.0]


def test_a_value_for_a_role_its_base_does_not_open_fails_and_the_bases_holds(
    tmp_path: Path, foundations: Any
) -> None:
    base, folder = chain_copy(tmp_path)
    green = {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0, 0.5, 0]}}
    edit_json(folder / EDITION, setting("surface", green))
    read = tokens.read_brand(folder, foundations, locked={"test-brand": base}, root=tmp_path)
    (finding,) = read.findings
    assert (finding.code, finding.level) == ("role-not-open", findings.FAILS)
    assert finding.library == "test-edition@1.0.0"
    assert (finding.file, finding.where) == (
        "test-edition/1.0.0/tokens/edition.tokens.json",
        "surface",
    )
    assert read.base is not None
    assert read.resolve("surface", {}) == read.base.resolve("surface", {})


def test_an_alias_to_a_token_its_base_keeps_private_fails(tmp_path: Path, foundations: Any) -> None:
    base, folder = chain_copy(tmp_path)
    edit_json(folder / DARK, setting("accent|$value", "{palette.blue.400}"))
    with pytest.raises(tokens.TokenError) as raised:
        tokens.read_brand(folder, foundations, locked={"test-brand": base}, root=tmp_path)
    (finding,) = raised.value.findings
    assert finding.code == "alias-private"
    assert finding.library == "test-edition@1.0.0"
    assert finding.file == "test-edition/1.0.0/tokens/dark.tokens.json"
    assert "which test-brand@1.0.0 keeps private" in finding.message


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (
            setting(
                "modifiers|density", {"contexts": {"loose": [], "tight": []}, "default": "loose"}
            ),
            "adds an axis",
        ),
        (setting("modifiers|colour-scheme|contexts|sepia", []), "adds the mode `sepia`"),
        (setting("modifiers|contrast|default", "high"), "changes the default to `high`"),
    ],
)
def test_a_brand_built_on_another_adds_no_axis_or_mode_and_changes_no_default(
    tmp_path: Path, foundations: Any, change: Callable[[dict[str, Any]], None], said: str
) -> None:
    base, folder = chain_copy(tmp_path)
    edit_json(folder / "test-edition.resolver.json", change)
    with pytest.raises(tokens.TokenError) as raised:
        tokens.read_brand(folder, foundations, locked={"test-brand": base})
    found = [f for f in raised.value.findings if f.code == "base-axis"]
    assert len(found) == 1
    assert said in found[0].message
    assert "test-brand@1.0.0" in found[0].message
    assert found[0].library == "test-edition@1.0.0"


def test_in_a_chain_each_link_opens_at_most_what_the_last_opens(
    tmp_path: Path, foundations: Any
) -> None:
    base, edition = chain_copy(tmp_path)
    third = built_on_edition(tmp_path, edition)
    edit_json(third / EDITION, setting("space|4|$value", {"value": 48, "unit": "px"}))
    locked = {"test-brand": base, "test-edition": edition}
    read = tokens.read_brand(third, foundations, locked=locked)
    assert read.base is not None and read.base.base is not None
    assert read.base.base.label == "test-brand@1.0.0"
    (finding,) = read.findings
    assert (finding.code, finding.where, finding.library) == (
        "role-not-open",
        "space.4",
        "test-third@1.0.0",
    )
    assert read.resolve("space.4", {}) == {"value": 40, "unit": "px"}
    assert read.resolve("accent", DARK_MODE) == ORANGE
    assert read.opened == {"accent"}
    replace_in(edition / "library.yaml", "open: [accent]", "open: [accent, text-primary]")
    widened = tokens.read_brand(edition, foundations, locked=locked)
    (finding,) = widened.findings
    assert (finding.code, finding.where) == ("open-wider", "open")
    assert "`text-primary`" in finding.message
    assert widened.opened == {"accent"}


@pytest.mark.parametrize(
    ("old", "new", "locked", "code"),
    [
        ("major: 1, base: true", "major: 1, base: true", {}, "base-lock"),
        ("major: 1, base: true", "major: 2, base: true", None, "base-lock"),
        (
            "{name: foundations, major: 1}",
            "{name: foundations, major: 1, base: true}",
            None,
            "base-shape",
        ),
        (
            "{name: test-brand, major: 1, base: true}",
            "{name: foundations, major: 1, base: true}",
            None,
            "base-kind",
        ),
        (
            "{name: test-brand, major: 1, base: true}",
            "{name: test-edition, major: 1, base: true}",
            None,
            "base-loop",
        ),
    ],
)
def test_a_base_the_brand_cannot_build_on_is_refused(
    tmp_path: Path,
    foundations: Any,
    old: str,
    new: str,
    locked: dict[str, Path] | None,
    code: str,
) -> None:
    base, folder = chain_copy(tmp_path)
    replace_in(folder / "library.yaml", old, new)
    given = {"test-brand": base, "foundations": FOUNDATIONS} if locked is None else locked
    with pytest.raises(tokens.TokenError) as raised:
        tokens.read_brand(folder, foundations, locked=given)
    assert code in codes(raised.value.findings)
    if code == "base-lock":
        assert {f.library for f in raised.value.findings} == {""}


def test_a_brands_findings_hold_its_bases_each_once_naming_the_base(
    tmp_path: Path, foundations: Any
) -> None:
    base, folder = chain_copy(tmp_path)
    paper = {"colorSpace": "srgb", "components": [1, 1, 1], "alpha": 0.5}
    edit_json(base / BASE, setting("scheme|paper|$value", paper))
    read = tokens.read_brand(folder, foundations, locked={"test-brand": base})
    assert codes(read.findings) == {"pair-translucent"}
    assert {f.library for f in read.findings} == {"test-brand@1.0.0"}
    assert len(read.findings) == len(tokens.read_brand(base, foundations).findings)


def test_a_piece_in_a_brand_built_on_another_reads_its_base_at_the_version_it_locks(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TEST_EDITION, "test-edition", "1.0.0")
    write_piece(root, "card", brand="test-edition", modes={"colour-scheme": ["light", "dark"]})
    write(root / "visual/pieces/card/content.en.yaml", yaml_text(bound("content", caption="x")))
    held = libraries.Held(root, "visual", (0, 1, 0))
    piece = pl.read_piece(root, "visual", "card")
    lock = libraries.move_lock(held, pl.needed(piece))
    assert lock == {"foundations": "1.0.0", "test-brand": "1.0.0", "test-edition": "1.0.0"}
    document = pl.Project(piece, lock, held).values()
    assert document["tokens"]["accent"]["values"]["colour-scheme.dark"] == ORANGE
    assert document["tokens"]["space.4"]["values"]["default"] == {"value": 40, "unit": "px"}


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
