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
    TEST_PARTS,
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


def test_the_foundations_declare_the_shared_roles_axes_and_pairs(foundations: Any) -> None:
    assert foundations.roles["text-primary"] == tokens.Role("text-primary", "color")
    assert foundations.roles["space.3"].type == "dimension"
    assert foundations.roles["type.body"].type == "typography"
    assert set(foundations.axes) == {"colour-scheme", "contrast"}
    assert foundations.axes["contrast"] == tokens.Axis(
        "contrast", "value", ("standard", "high"), "standard"
    )
    assert foundations.pairs[0] == tokens.Pair("text-primary", "background", "text")
    assert foundations.pairs[0].minimum == 4.5
    assert {"space", "type", "font", "text-primary", "family"} <= set(foundations.top_groups)


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
    assert brand.families() == (
        "Source Code Pro",
        "Source Sans Pro",
        "Source Sans Pro Semibold",
    )
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
    # The neutral family paints its text with the primary text, so its pair falls with it.
    assert sorted(finding.where for finding in found) == ["family.neutral.text", "text-primary"]
    for finding in found:
        assert finding.level == findings.FAILS
        assert "`colour-scheme.dark`" in finding.message


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
    lock = libraries.move_lock(held, pl.needed(piece)).lock
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


# --- colour families (DEC-004 points 8 and 10) --------------------------------------------------

#: The colour families the foundations declare, and the members of each.
FAMILIES = ("neutral", "blue", "green", "orange", "purple", "red")
MEMBERS = ("fill", "line", "text")


def test_the_foundations_declare_each_colour_family_with_a_shared_role_for_each_member(
    foundations: Any,
) -> None:
    assert tuple(foundations.families) == FAMILIES
    for family in FAMILIES:
        members = foundations.families[family]
        assert members == {member: f"family.{family}.{member}" for member in MEMBERS}
        for role in members.values():
            # Roles of the foundations' first version, so none carries a default.
            assert foundations.roles[role] == tokens.Role(role, "color")


def test_each_familys_text_must_contrast_with_its_fill(foundations: Any) -> None:
    for family in FAMILIES:
        pair = tokens.Pair(f"family.{family}.text", f"family.{family}.fill", "text")
        assert pair in foundations.pairs


def test_the_test_brand_gives_each_familys_roles_a_value_in_every_combination(brand: Any) -> None:
    assert brand.findings == ()
    for family in FAMILIES:
        for combination in brand.combinations():
            text = brand.resolve(f"family.{family}.text", combination)
            fill = brand.resolve(f"family.{family}.fill", combination)
            assert brand.resolve(f"family.{family}.line", combination)["alpha"] == 1
            assert tokens.contrast_ratio(text, fill) >= 4.5, (family, combination)


def test_a_familys_text_below_its_contrast_fails_in_the_combinations_it_lies_in(
    tmp_path: Path, foundations: Any
) -> None:
    folder = brand_copy(tmp_path)
    edit_json(folder / DARK, setting("scheme|blue|text|$value", "{palette.blue.900}"))
    found = tokens.read_brand(folder, foundations).findings
    assert codes(found) == {"pair-contrast"}
    (finding,) = found  # at high contrast, the family's text is the scheme's strongest
    assert finding.where == "family.blue.text"
    assert "`family.blue.text` on `family.blue.fill`" in finding.message
    assert "the combination `colour-scheme.dark`" in finding.message


# --- a library's own roles (DEC-008) -----------------------------------------------------------

#: The libraries the test library's roles are read with: the foundations, and itself.
PARTS = {"foundations": FOUNDATIONS, "test-parts": TEST_PARTS}

BLACK = {"colorSpace": "srgb", "components": [0.0, 0.0, 0.0], "alpha": 1}
WHITE = {"colorSpace": "srgb", "components": [1.0, 1.0, 1.0], "alpha": 1}


@pytest.fixture(scope="module")
def parts() -> Any:
    return tokens.read_scope(PARTS)


def own_roles(
    tmp_path: Path,
    roles: dict[str, Any],
    pairs: list[dict[str, str]] | None = None,
    builds_on: tuple[str, ...] = ("foundations",),
    **more: Any,
) -> Any:
    """The own roles of a library `test-parts` written from `roles` and `pairs`, read in a
    scope with the foundations."""
    path = write(
        tmp_path / "roles.yaml",
        yaml_text(bound("roles", roles=roles, pairs=pairs or [], **more)),
    )
    declared = tokens.read_own_roles(
        path, name="test-parts", library="test-parts@1.0.0", builds_on=builds_on
    )
    return tokens.Scope(tokens.read_declarations(ROLES), [declared])


def naming_brand(tmp_path: Path, given: dict[str, Any] | None = None, file: str = BASE) -> Path:
    """A copy of the test brand that names `test-parts` 1 among the libraries it builds on,
    `given` added to its token file `file`; by default, the test library's role without a
    default, its warning, takes the brand's ink."""
    folder = brand_copy(tmp_path)
    replace_in(
        folder / "library.yaml",
        "  - {name: foundations, major: 1}\n",
        "  - {name: foundations, major: 1}\n  - {name: test-parts, major: 1}\n",
    )
    if given is None:
        given = {"test-parts": {"$type": "color", "warning": {"$value": "{scheme.ink}"}}}
    edit_json(folder / file, lambda data: data.update(given))
    return folder


def test_a_librarys_own_roles_lie_under_its_name_and_their_type_reads_with_no_brand(
    parts: Any,
) -> None:
    assert parts.owner["test-parts.ink"] == "test-parts"
    assert parts.owner["text-primary"] == ""
    assert parts.type_of("test-parts.gap") == "dimension"
    assert parts.type_of("background") == "color"
    with pytest.raises(tokens.UnknownRole):
        parts.type_of("test-parts.nothing")
    assert parts.default_of("test-parts.note") == "test-parts.ink"
    assert parts.default_of("test-parts.ink") == "text-primary"
    assert parts.default_of("test-parts.warning") is None
    (fact,) = parts.findings
    assert (fact.code, fact.level, fact.where) == (
        "role-brand-only",
        findings.FACT,
        "roles.test-parts.warning",
    )
    assert fact.library == "test-parts@1.0.0"
    assert tokens.Pair("test-parts.ink", "test-parts.paper", "text") in parts.pairs


def test_a_brand_that_does_not_name_the_library_draws_it_at_its_defaults(parts: Any) -> None:
    brand = tokens.read_brand(TEST_BRAND, parts)
    assert brand.named == frozenset()
    assert brand.findings == ()
    for combination in brand.combinations():
        assert brand.resolve("test-parts.note", combination) == brand.resolve(
            "text-primary", combination
        )
        assert brand.resolve("test-parts.paper", combination) == brand.resolve(
            "background", combination
        )
        assert brand.resolve("test-parts.gap", combination) == brand.resolve("space.2", combination)
    with pytest.raises(tokens.RoleWithoutValue):
        brand.resolve("test-parts.warning", {})
    assert not any(path.startswith("test-parts.") for path in brand.roles)
    assert {"test-parts.ink", "test-parts.note", "test-parts.gap"} <= set(brand.valued)
    assert "test-parts.warning" not in brand.valued
    assert brand.type_of("test-parts.warning") == "color"


def test_a_brand_that_names_the_library_gives_its_roles_values_and_its_defaults_follow(
    tmp_path: Path, parts: Any
) -> None:
    given = {
        "test-parts": {
            "$type": "color",
            "ink": {"$value": "{scheme.strong-ink}"},
            "warning": {"$value": "{scheme.ink}"},
        }
    }
    brand = tokens.read_brand(naming_brand(tmp_path, given), parts)
    assert brand.named == {"test-parts"}
    assert brand.findings == ()
    assert brand.resolve("test-parts.ink", {}) == BLACK
    assert brand.resolve("test-parts.note", {}) == BLACK
    assert brand.resolve("test-parts.note", DARK_MODE) == WHITE
    assert brand.resolve("test-parts.paper", {}) == brand.resolve("background", {})
    assert {"test-parts.ink", "test-parts.warning"} <= set(brand.roles)
    assert "test-parts.paper" not in brand.roles
    assert "test-parts.paper" in brand.valued


def test_a_brands_value_wins_where_its_sources_cover_and_the_default_holds_elsewhere(
    tmp_path: Path, parts: Any
) -> None:
    folder = naming_brand(tmp_path)
    given = {"test-parts": {"$type": "color", "ink": {"$value": "{palette.white}"}}}
    edit_json(folder / DARK, lambda data: data.update(given))
    brand = tokens.read_brand(folder, parts)
    assert brand.findings == ()
    assert brand.resolve("test-parts.ink", DARK_MODE) == WHITE
    assert brand.resolve("test-parts.ink", {}) == brand.resolve("text-primary", {})
    assert "test-parts.ink" in brand.roles


def test_a_role_whose_chain_of_defaults_reaches_no_value_has_none(tmp_path: Path) -> None:
    roles = {
        "test-parts.warning": {"type": "color"},
        "test-parts.alert": {"type": "color", "default": "{test-parts.warning}"},
    }
    scope = own_roles(tmp_path, roles)
    brand = tokens.read_brand(TEST_BRAND, scope)
    assert brand.findings == ()
    with pytest.raises(tokens.RoleWithoutValue):
        brand.resolve("test-parts.alert", {})
    named = tokens.read_brand(naming_brand(tmp_path), scope)
    assert named.findings == ()
    assert named.resolve("test-parts.alert", {}) == named.resolve("text-primary", {})


def test_a_brand_that_names_the_library_gives_each_role_without_a_default_a_value(
    tmp_path: Path, parts: Any
) -> None:
    (finding,) = tokens.read_brand(naming_brand(tmp_path, {}), parts).findings
    assert (finding.code, finding.level, finding.where) == (
        "library-role-missing",
        findings.FAILS,
        "test-parts.warning",
    )
    assert finding.library == "test-brand@1.0.0"
    assert "no value in any combination" in finding.message
    folder = naming_brand(tmp_path / "dark", {})
    given = {"test-parts": {"$type": "color", "warning": {"$value": "{scheme.ink}"}}}
    edit_json(folder / DARK, lambda data: data.update(given))
    (finding,) = tokens.read_brand(folder, parts).findings
    assert "in the combinations `default`, `contrast.high`" in finding.message


def test_a_token_under_a_named_librarys_name_that_fits_none_of_its_roles_is_a_finding(
    tmp_path: Path, parts: Any
) -> None:
    given = {
        "test-parts": {
            "warning": {"$type": "color", "$value": "{scheme.ink}"},
            "extra": {"$type": "color", "$value": "{scheme.ink}"},
            "gap": {"$type": "color", "$value": "{scheme.ink}"},
        }
    }
    brand = tokens.read_brand(naming_brand(tmp_path, given), parts)
    found = {finding.where: finding for finding in brand.findings}
    assert set(found) == {"test-parts.extra", "test-parts.gap"}
    assert {finding.code for finding in found.values()} == {"library-token"}
    assert "is none of its roles" in found["test-parts.extra"].message
    assert "of type `color`, but the role" in found["test-parts.gap"].message
    assert brand.resolve("test-parts.gap", {}) == brand.resolve("space.2", {})


def test_a_token_under_a_library_the_brand_does_not_name_stays_private_and_asks_attention(
    tmp_path: Path, parts: Any
) -> None:
    folder = brand_copy(tmp_path)
    given = {"test-parts": {"$type": "color", "ink": {"$value": "{scheme.strong-ink}"}}}
    edit_json(folder / BASE, lambda data: data.update(given))
    brand = tokens.read_brand(folder, parts)
    (finding,) = brand.findings
    assert (finding.code, finding.level) == ("library-token-private", findings.ATTENTION)
    assert finding.who == "the owner of the brand test-brand"
    assert brand.resolve("test-parts.ink", {}) == brand.resolve("text-primary", {})
    assert tokens.read_brand(folder, tokens.read_declarations(ROLES)).findings == ()


def test_an_alias_to_a_role_of_a_library_the_brand_does_not_name_fails(
    tmp_path: Path, parts: Any
) -> None:
    folder = brand_copy(tmp_path)
    edit_json(folder / BASE, setting("accent|$value", "{test-parts.ink}"))
    with pytest.raises(tokens.TokenError) as raised:
        tokens.read_brand(folder, parts)
    (finding,) = raised.value.findings
    assert finding.code == "alias-dangling"
    assert "which test-brand@1.0.0 does not name among the libraries" in finding.message


def test_a_librarys_pair_is_judged_where_the_brands_values_reach_it(
    tmp_path: Path, parts: Any
) -> None:
    given = {
        "test-parts": {
            "$type": "color",
            "ink": {"$value": "{scheme.rule}"},
            "warning": {"$value": "{scheme.ink}"},
        }
    }
    found = tokens.read_brand(naming_brand(tmp_path, given), parts).findings
    assert codes(found) == {"pair-contrast"}
    assert {finding.where for finding in found} == {"test-parts.ink"}
    assert all("`test-parts.ink` on `test-parts.paper`" in f.message for f in found)


def test_a_pair_with_a_role_without_a_default_is_judged_only_where_it_has_a_value(
    tmp_path: Path, parts: Any
) -> None:
    assert tokens.read_brand(TEST_BRAND, parts).findings == ()
    given = {"test-parts": {"$type": "color", "warning": {"$value": "{scheme.paper}"}}}
    found = tokens.read_brand(naming_brand(tmp_path, given), parts).findings
    assert codes(found) == {"pair-contrast"}
    assert {finding.where for finding in found} == {"test-parts.warning"}


def library_chain(tmp_path: Path, *, base_names: bool, edition_names: bool) -> tuple[Path, Path]:
    """The test brand as a base that opens the test library's ink, and the edition over it
    that gives the ink a value; each names `test-parts` as asked."""
    base, edition = chain_copy(tmp_path)
    if base_names:
        given = {
            "test-parts": {
                "$type": "color",
                "ink": {"$value": "{scheme.strong-ink}"},
                "warning": {"$value": "{scheme.ink}"},
            }
        }
        naming = naming_brand(tmp_path / "named", given)
        shutil.rmtree(base)
        shutil.copytree(naming, base)
    replace_in(
        base / "library.yaml", "open: [accent, space]", "open: [accent, space, test-parts.ink]"
    )
    replace_in(edition / "library.yaml", "open: [accent]", "open: [accent, test-parts.ink]")
    if edition_names:
        replace_in(
            edition / "library.yaml",
            "  - {name: foundations, major: 1}\n",
            "  - {name: foundations, major: 1}\n  - {name: test-parts, major: 1}\n",
        )
    given = {"test-parts": {"$type": "color", "ink": {"$value": "{text-secondary}"}}}
    edit_json(edition / EDITION, lambda data: data.update(given))
    return base, edition


def test_a_brand_built_on_a_base_gives_a_library_role_a_value_where_both_name_it(
    tmp_path: Path, parts: Any
) -> None:
    base, edition = library_chain(tmp_path, base_names=True, edition_names=True)
    read = tokens.read_brand(edition, parts, locked={"test-brand": base})
    assert read.findings == ()
    assert read.base is not None
    assert read.base.opened >= {"test-parts.ink"}
    assert read.opened == {"accent", "test-parts.ink"}
    secondary = read.resolve("text-secondary", {})
    assert read.resolve("test-parts.ink", {}) == secondary
    assert read.resolve("test-parts.note", {}) == secondary
    assert read.base.resolve("test-parts.ink", {}) == BLACK
    assert "test-parts.ink" in read.roles


def test_a_brand_that_does_not_name_the_library_keeps_its_bases_values_for_it(
    tmp_path: Path, parts: Any
) -> None:
    base, edition = library_chain(tmp_path, base_names=True, edition_names=False)
    read = tokens.read_brand(edition, parts, locked={"test-brand": base})
    assert read.resolve("test-parts.ink", {}) == BLACK
    assert "test-parts.ink" in read.roles
    found = {finding.code: finding for finding in read.findings}
    assert set(found) == {"library-token-private", "open-unknown"}
    assert "roles of `test-parts`, which the brand does not name" in found["open-unknown"].message


def test_a_base_that_does_not_name_the_library_opens_none_of_its_roles(
    tmp_path: Path, parts: Any
) -> None:
    base, edition = library_chain(tmp_path, base_names=False, edition_names=True)
    read = tokens.read_brand(edition, parts, locked={"test-brand": base})
    assert read.base is not None
    assert "test-parts.ink" not in read.base.opened
    found = {(finding.code, finding.library) for finding in read.findings}
    assert ("open-unknown", "test-brand@1.0.0") in found
    assert ("role-not-open", "test-edition@1.0.0") in found
    assert ("library-role-missing", "test-edition@1.0.0") in found
    (not_open,) = [f for f in read.findings if f.code == "role-not-open"]
    assert "does not name `test-parts`, so it opens none of its roles" in not_open.message
    assert read.resolve("test-parts.ink", {}) == read.resolve("text-primary", {})


def without_value(brand: Any, path: str) -> Any:
    """What resolving the role at `path` under `brand` raises, which has no value there."""
    with pytest.raises(tokens.RoleWithoutValue) as raised:
        brand.resolve(path, {})
    return raised.value


def test_a_role_without_a_value_names_its_library_and_whether_a_brand_of_the_chain_names_it(
    tmp_path: Path, parts: Any
) -> None:
    alone = without_value(tokens.read_brand(TEST_BRAND, parts), "test-parts.warning")
    assert isinstance(alone, env.UnvaluedRole)
    assert (alone.role, alone.library, alone.named) == ("test-parts.warning", "test-parts", False)
    named = tokens.read_brand(naming_brand(tmp_path / "named", {}), parts)
    assert without_value(named, "test-parts.warning").named
    base, edition = library_chain(tmp_path / "chain", base_names=True, edition_names=False)
    edit_json(base / BASE, dropping("test-parts|warning"))
    read = tokens.read_brand(edition, parts, locked={"test-brand": base})
    assert ("library-role-missing", "test-brand@1.0.0") in {
        (finding.code, finding.library) for finding in read.findings
    }
    assert without_value(read, "test-parts.warning").named


@pytest.mark.parametrize(
    ("roles", "builds_on", "code", "said"),
    [
        (
            {"test-parts.a": {"type": "color", "default": "{component.card.fill}"}},
            ("foundations",),
            "role-default",
            "a component token",
        ),
        (
            {"test-parts.a": {"type": "dimension", "default": "{text-primary}"}},
            ("foundations",),
            "role-default",
            "of type `color`, not `dimension`",
        ),
        (
            {"test-parts.a": {"type": "color", "default": "{text-primary}"}},
            (),
            "role-default",
            "which `test-parts` does not build on",
        ),
        (
            {"test-parts.a": {"type": "color", "default": "text-primary"}},
            ("foundations",),
            "role-default",
            "is not an alias",
        ),
        (
            {"test-parts.a": {"type": "color", "default": "{test-parts.nothing}"}},
            ("foundations",),
            "default-dangling",
            "neither `test-parts` nor a library it builds on declares",
        ),
        (
            {
                "test-parts.a": {"type": "color", "default": "{test-parts.b}"},
                "test-parts.b": {"type": "color", "default": "{test-parts.a}"},
            },
            ("foundations",),
            "default-loop",
            "the defaults make a loop",
        ),
        (
            {"other.a": {"type": "color", "default": "{text-primary}"}},
            ("foundations",),
            "role-name",
            "lies outside `test-parts`",
        ),
        (
            {"component.a": {"type": "color"}},
            ("foundations",),
            "role-name",
            "the group of component tokens",
        ),
    ],
)
def test_a_default_that_does_not_hold_is_the_librarys_finding_and_gives_no_value(
    tmp_path: Path, roles: dict[str, Any], builds_on: tuple[str, ...], code: str, said: str
) -> None:
    scope = own_roles(tmp_path, roles, builds_on=builds_on)
    failing = [f for f in scope.findings_of("test-parts") if f.level == findings.FAILS]
    assert {finding.code for finding in failing} == {code}
    assert all(said in finding.message for finding in failing)
    assert all(finding.library == "test-parts@1.0.0" for finding in failing)
    for path in roles:
        assert scope.default_of(path) is None
    brand = tokens.read_brand(TEST_BRAND, scope)
    assert brand.findings == ()
    assert not any(path in brand.valued for path in roles)


def test_a_loop_of_defaults_is_found_at_each_role_in_it(tmp_path: Path) -> None:
    roles = {
        "test-parts.a": {"type": "color", "default": "{test-parts.b}"},
        "test-parts.b": {"type": "color", "default": "{test-parts.c}"},
        "test-parts.c": {"type": "color", "default": "{test-parts.a}"},
        "test-parts.d": {"type": "color", "default": "{test-parts.a}"},
    }
    found = own_roles(tmp_path, roles).findings_of("test-parts")
    loops = [finding for finding in found if finding.code == "default-loop"]
    assert {finding.where for finding in loops} == {
        "roles.test-parts.a",
        "roles.test-parts.b",
        "roles.test-parts.c",
    }
    assert ("role-brand-only", "roles.test-parts.d") in {(f.code, f.where) for f in found}


def test_a_librarys_roles_file_declares_no_axes_or_families_and_is_read_still(
    tmp_path: Path,
) -> None:
    roles = {"test-parts.a": {"type": "color", "default": "{text-primary}"}}
    axes = {"density": {"kind": "size", "modes": ["tight", "loose"], "default": "tight"}}
    scope = own_roles(tmp_path, roles, axes=axes, families={"blue": {"fill": "test-parts.a"}})
    found = scope.findings_of("test-parts")
    assert {(f.code, f.where) for f in found} == {
        ("roles-declaration", "axes"),
        ("roles-declaration", "families"),
    }
    assert scope.default_of("test-parts.a") == "text-primary"
    assert "density" not in scope.axes


def test_a_librarys_roles_file_that_cannot_be_read_is_its_finding(tmp_path: Path) -> None:
    declared = tokens.read_own_roles(
        tmp_path / "roles.yaml", name="test-parts", library="test-parts@1.0.0"
    )
    assert [finding.code for finding in declared.findings] == ["roles-unreadable"]
    assert declared.roles == {}


@pytest.mark.parametrize(
    ("pairs", "code", "said"),
    [
        (
            [{"text": "text-primary", "under": "background", "level": "text"}],
            "pair-shape",
            "names none of the library's own roles",
        ),
        (
            [{"text": "test-parts.a", "under": "test-parts.gap", "level": "text"}],
            "pair-shape",
            "does not name two colour roles",
        ),
        (
            [{"text": "test-parts.a", "under": "other.paper", "level": "text"}],
            "pair-shape",
            "which is no colour role of `test-parts` or of a library it builds on",
        ),
        (
            [{"text": "test-parts.a", "under": "test-parts.b", "level": "text"}],
            "pair-defaults",
            "falls at its defaults on `text-secondary` on `surface`",
        ),
        (
            [{"text": "test-parts.c", "under": "test-parts.b", "level": "text"}],
            "pair-defaults",
            "falls at its defaults on `text-primary` on `surface`",
        ),
    ],
)
def test_a_librarys_pair_at_its_defaults_rests_on_a_declared_pair(
    tmp_path: Path, pairs: list[dict[str, str]], code: str, said: str
) -> None:
    roles = {
        "test-parts.a": {"type": "color", "default": "{text-secondary}"},
        "test-parts.b": {"type": "color", "default": "{surface}"},
        "test-parts.c": {"type": "color", "default": "{text-primary}"},
        "test-parts.gap": {"type": "dimension", "default": "{space.2}"},
    }
    found = own_roles(tmp_path, roles, pairs).findings_of("test-parts")
    (finding,) = [f for f in found if f.level == findings.FAILS]
    assert (finding.code, finding.where) == (code, "pairs.0")
    assert said in finding.message


def test_a_pair_resting_on_a_pair_of_its_library_at_a_level_as_strict_holds(
    tmp_path: Path,
) -> None:
    roles = {
        "test-parts.ink": {"type": "color", "default": "{text-primary}"},
        "test-parts.paper": {"type": "color", "default": "{background}"},
        "test-parts.note": {"type": "color", "default": "{test-parts.ink}"},
        "test-parts.card": {"type": "color", "default": "{test-parts.paper}"},
    }
    pairs = [
        {"text": "test-parts.ink", "under": "test-parts.paper", "level": "large-text"},
        {"text": "test-parts.note", "under": "test-parts.card", "level": "large-text"},
        {"text": "test-parts.note", "under": "test-parts.card", "level": "text"},
    ]
    found = own_roles(tmp_path, roles, pairs).findings_of("test-parts")
    assert [(f.code, f.where) for f in found] == [("pair-defaults", "pairs.2")]
