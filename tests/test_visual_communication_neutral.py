"""The neutral brand, the brand the capability ships to start from (visual-communication
DEC-004, Implications). `pkit visual add neutral` copies and lists it. It names the
foundations alone, so it draws the starter at its defaults (DEC-008, Implications), and it
holds no component, so each top draws its own layouts (DEC-009, Implications). It gives
every shared role a value in every combination of its axes, and every pair the foundations
and the starter declare reaches its level there. So do the shared text roles and each
family's text on every fill a component lays them on, beyond the pairs declared. The
starter's reference renders, drawn under it, pass the check, and each of their texts
reaches its contrast as drawn in every combination (DEC-004 point 8). Its fonts and their
licences are the files their upstream releases ship, unchanged, and each weight its
typography roles use is a family of its own, whose file has that weight (DEC-012 point 4,
"A weight's own file").

The reference renders are the pieces under `tests/fixtures/visual-communication/starter/`,
pinned here with the neutral brand in place of the test brand. Run in this process
(`tests/in_process.py`); it starts no `pkit`."""

from __future__ import annotations

import hashlib
import itertools
import math
import shutil
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from fontTools.ttLib import TTFont

from tests import test_visual_communication_starter as starter
from tests.in_process import load, run_main
from tests.visual_communication_project import (
    CAPABILITY,
    FIXTURES,
    FOUNDATIONS,
    TEST_NOTATION,
    bound,
    copy_library,
    hold_shipped,
    importable,
    locked_at,
    project,
    taken,
    write_list,
    yaml_text,
)

add, checks, keys, pl, reading, tokens = load(
    "visual-communication", "add.py", "checks", "keys", "pipeline", "reading", "tokens"
)

NEUTRAL = CAPABILITY / "libraries" / "neutral"
STARTER = CAPABILITY / "libraries" / "starter"
PIECES = FIXTURES / "starter" / "pieces"
UNRELEASED = {"1.0.0": {"released": False}}

#: The hash of each file of `fonts/`, as it lies in the release that ships it: tag
#: `2.020R-ro/1.075R-it` of adobe-fonts/source-sans, and `2.038R-ro/1.058R-it/1.018R-VAR` of
#: adobe-fonts/source-code-pro, whose licence that tag names `LICENSE.md`.
UNCHANGED = {
    "LICENSE-Source-Code-Pro.txt": (
        "1036668c56392d012c81aa1c84cd8aacea3e767c52190f789d14857b3d0a5765"
    ),
    "LICENSE-Source-Sans-Pro.txt": (
        "653aaf9819e33cf1e2b3523c5d4d6c3dae925d770cb4563030f96655321ca2e9"
    ),
    "SourceCodePro-Regular.ttf": (
        "f144137f557805c7327fc4b14d1d730f6e1822e0124170251ff1bcd723a693f1"
    ),
    "SourceSansPro-Regular.otf": (
        "6b096b47206d8f78a2c49af2f2ae46b35d93b0e3cf105a9febef59144aa2eae2"
    ),
    "SourceSansPro-Semibold.otf": (
        "ee3ba5c88400b22b880d85202ce82143dc5e19861bf7880b7f4c32d4263e96d5"
    ),
}
#: The licence that covers each font file.
LICENCE_OF = {
    "SourceCodePro-Regular.ttf": "LICENSE-Source-Code-Pro.txt",
    "SourceSansPro-Regular.otf": "LICENSE-Source-Sans-Pro.txt",
    "SourceSansPro-Semibold.otf": "LICENSE-Source-Sans-Pro.txt",
}


def read(path: Path) -> Any:
    return reading.read_yaml(path)


def files_of(folder: Path) -> dict[str, bytes]:
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


@pytest.fixture(scope="module")
def brand() -> Any:
    """The neutral brand, resolved with the foundations and the starter."""
    scope = tokens.read_scope({"foundations": FOUNDATIONS, "starter": STARTER})
    return tokens.read_brand(NEUTRAL, scope)


# --- the copy, and what it names --------------------------------------------------------------


def test_add_copies_it_whole_and_lists_it_shipped(tmp_path: Path) -> None:
    """What the capability ships by default, as the tree holds it: the newest released
    version, with its record's entry, or the version being built where none is released."""
    ships = taken("neutral")
    root = project(tmp_path)
    added = run_main(add, "neutral", cwd=root)
    assert added.returncode == 0, added.stderr
    copy = root / "visual" / "libraries" / "neutral" / ships.version
    assert files_of(copy) == files_of(ships.folder)
    listed = read(root / "visual" / "libraries" / "libraries.yaml")
    versions = {ships.version: ships.entry}
    assert listed == bound(
        "libraries", libraries={"neutral": {"source": {"kind": "shipped"}, "versions": versions}}
    )


def test_it_names_the_foundations_alone_opens_no_role_and_holds_no_component() -> None:
    library = read(NEUTRAL / "library.yaml")
    assert library["builds-on"] == [{"name": "foundations", "major": 1}]
    assert library["open"] == []
    assert not (NEUTRAL / "components").exists()


# --- its values -------------------------------------------------------------------------------


def test_it_gives_every_shared_role_but_its_logo_a_value_in_every_combination(
    brand: Any,
) -> None:
    """It gives `picture.logo` no value, which no brand owes, so it does not export it, and
    its version states so (DEC-025 points 4 and 9)."""
    shared = {
        role: declared
        for role, declared in read(FOUNDATIONS / "roles.yaml")["roles"].items()
        if declared["type"] != tokens.PICTURE
    }
    assert brand.findings == ()
    assert len(brand.combinations()) == math.prod(len(a.modes) for a in brand.axes.values())
    assert set(shared) <= set(brand.roles)
    assert "picture.logo" not in brand.roles
    assert [(f.code, f.where) for f in brand.facts] == [("picture-role-unvalued", "picture.logo")]
    for role, combination in itertools.product(shared, brand.combinations()):
        assert brand.resolve(role, combination) is not None, (role, combination)


def test_it_draws_the_starter_at_its_defaults(brand: Any) -> None:
    own = read(STARTER / "roles.yaml")["roles"]
    assert not brand.names("starter")
    assert set(own).isdisjoint(brand.roles)
    for role, declared in own.items():
        default = str(declared["default"]).strip("{}")
        for combination in brand.combinations():
            assert brand.resolve(role, combination) == brand.resolve(default, combination), role


def test_a_strong_type_is_the_bodys_size_and_line_height_in_a_heavier_weight(brand: Any) -> None:
    """So a strong run keeps the line it lies in (`files.md`, *The foundations*)."""
    body, strong = brand.resolve("type.body", {}), brand.resolve("type.strong", {})
    assert strong["fontSize"] == body["fontSize"]
    assert strong["lineHeight"] == body["lineHeight"]
    assert strong["fontWeight"] > body["fontWeight"]


# --- its contrast -----------------------------------------------------------------------------


def contrast(brand: Any, ink: str, ground: str, combination: Mapping[str, str]) -> float:
    return tokens.contrast_ratio(
        brand.resolve(ink, combination), brand.resolve(ground, combination)
    )


def grounds(brand: Any) -> list[str]:
    """Each fill a component lays what it draws on: the background, the surface, and the
    fill of each colour family."""
    return ["background", "surface", *(family["fill"] for family in brand.scope.families.values())]


def test_each_pair_declared_reaches_its_level_in_every_combination(brand: Any) -> None:
    """Every pair of the foundations and of the starter, whose own roles lie at their
    defaults under the brand."""
    assert brand.scope.pairs
    below = [
        (pair.text, pair.under, combination, round(ratio, 2))
        for pair in brand.scope.pairs
        for combination in brand.combinations()
        if (ratio := contrast(brand, pair.text, pair.under, combination)) < pair.minimum
    ]
    assert below == []


def test_high_contrast_lowers_no_pair_declared(brand: Any) -> None:
    for pair, scheme in itertools.product(brand.scope.pairs, ("light", "dark")):
        standard = {"colour-scheme": scheme, "contrast": "standard"}
        high = {"colour-scheme": scheme, "contrast": "high"}
        assert contrast(brand, pair.text, pair.under, high) >= contrast(
            brand, pair.text, pair.under, standard
        ), (pair.text, pair.under, scheme)


@pytest.mark.parametrize("ink", ["text-primary", "text-secondary", "accent"])
def test_a_shared_text_role_reaches_the_level_of_text_on_every_ground(brand: Any, ink: str) -> None:
    """No pair declares these, yet a concept gives a code block any family's fill, under
    its prompts and comments in the secondary text and its commands in the accent. The
    reference renders do not draw each of those fills."""
    below = [
        (ground, combination, round(ratio, 2))
        for ground in grounds(brand)
        for combination in brand.combinations()
        if (ratio := contrast(brand, ink, ground, combination)) < tokens.LEVELS["text"]
    ]
    assert below == []


def test_each_familys_text_reaches_the_level_of_marks_on_every_ground(brand: Any) -> None:
    """A connector's line takes its family's text, and may lie on the background or on
    another family's fill, which no pair declares."""
    below = [
        (family["text"], ground, combination, round(ratio, 2))
        for family in brand.scope.families.values()
        for ground in grounds(brand)
        for combination in brand.combinations()
        if (ratio := contrast(brand, family["text"], ground, combination)) < tokens.LEVELS["marks"]
    ]
    assert below == []


# --- the starter's reference renders ----------------------------------------------------------


def pinned_with_neutral(folder: Path) -> None:
    """The reference piece in `folder`, its brand and its lock moved to the neutral brand."""
    path = folder / "piece.yaml"
    piece = read(path)
    lock = dict(piece["lock"])
    lock["neutral"] = lock.pop("test-brand")
    path.write_text(yaml_text({**piece, "brand": "neutral", "lock": lock}), encoding="utf-8")


@pytest.fixture(scope="module")
def location(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A location that holds the foundations, the starter and the neutral brand being built
    as the capability ships them, the released version of their number where it is
    released, the test notation, and the starter's reference pieces, each locked at the
    versions being built."""
    return reference_location(project(tmp_path_factory.mktemp("neutral")))


def reference_location(root: Path) -> Path:
    """The location of `location`, laid out in the project at `root`."""
    copy_library(root, TEST_NOTATION, "test-notation", "1.0.0")
    write_list(root, {"test-notation": {"source": {"kind": "project"}, "versions": UNRELEASED}})
    built = {
        name: hold_shipped(root, name).version for name in ("foundations", "starter", "neutral")
    }
    shutil.copytree(PIECES, root / "visual" / "pieces")
    for folder in (root / "visual" / "pieces").iterdir():
        pinned_with_neutral(folder)
        locked_at(folder, built)
    return root


@pytest.fixture(scope="module")
def drawn(location: Path) -> dict[str, Any]:
    """Each reference piece as the engine draws it, by the piece's name."""
    projects = {}
    for folder in sorted(PIECES.iterdir()):
        piece = pl.read_piece(location, "visual", folder.name)
        projects[folder.name] = pl.Project(piece, piece.lock, pl.Held(location, "visual"))
    return projects


def colours_of(piece: Any) -> dict[str, Mapping[str, Any]]:
    """Each colour role of a piece as the engine draws it, with its value in each key."""
    return {
        path: token["values"]
        for path, token in piece.values()["tokens"].items()
        if token["type"] == "color"
    }


def scenes_of(piece: Any) -> Iterator[tuple[list[str], Mapping[str, Any]]]:
    """The scene of a piece in each of its languages and at each of its sizes, with the keys
    it is drawn in: each combination of the piece's modes at that size."""
    for _, result in piece.scenes(facts=piece.piece.stand_ins):
        assert result.findings == []
        size = result.scene.size_key
        yield [key for key in piece.keys if piece.size_key(key) == size], result.scene.to_dict()


def texts(element: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Each text within `element` that lays out lines."""
    if element.get("type") == "text" and element.get("lines"):
        yield element
    for child in element.get("children", []):
        yield from texts(child)


def test_every_reference_render_passes_the_check_under_it(location: Path) -> None:
    """The brand's version states, once, that it gives `picture.logo` no value, and no
    piece states it (DEC-025 point 9). Beside it, the pieces ask for attention where their
    concepts' signs are not drawn, as under the test brand."""
    report = checks.check(location)
    found = [
        (level, finding.code, finding.file, finding.where)
        for finding, level in report.judged
        if finding.code != "component-experimental" and finding.code not in starter.SIGN_LABELS
    ]
    built = taken("neutral", being_built=True).version
    assert found == [
        ("fact", "picture-role-unvalued", f"visual/libraries/neutral/{built}/", "picture.logo")
    ]
    assert starter.on_signs(report.judged) == starter.UNSIGNED
    assert not report.failed()


def test_each_reference_render_draws_on_the_foundations_being_built_as_on_their_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The neutral brand being built gives the sizes of the axis `device`, which the
    foundations being built add to their release 1.0.0, and a piece that names none is
    drawn at the default, `desktop` (DEC-021 points 2 and 9). So each reference piece draws
    under it on them as under the brand's release 1.0.0 on theirs, byte for byte: each
    preview, but for the foundations' version they name, and its values, but for the role
    `size.site` they add, which the brand gives as wide as its slide on a desktop,
    `size.line`, which no piece that names no size reads, and those of a run's sign and
    ground, at its smallest space. A web part's piece names the
    sizes, which the foundations' release does not declare."""
    importable(monkeypatch, starter.svg)
    root = reference_location(project(tmp_path))
    hold_shipped(root, "foundations", being_built=False)
    released_brand = hold_shipped(root, "neutral", being_built=False).version
    assert released_brand != taken("neutral", being_built=True).version
    on_each = starter.on_each_foundations(root, brand={"neutral": released_brand})
    released, built = on_each.values()
    assert sorted(built) == sorted(starter.UNSIZED)
    for name, (values, files) in built.items():
        assert files, name
        assert (starter.as_released(values, given=["size.line"]), files) == released[name], name


def test_each_text_of_the_reference_renders_reaches_its_contrast_in_every_combination(
    brand: Any, drawn: Mapping[str, Any]
) -> None:
    """A piece that names no size is drawn at the brand's default size alone, in every
    combination of its other axes (DEC-021 point 2). A web part's piece is drawn at every
    size, so a field in error and a button that cannot be pressed reach theirs in each."""
    measured = 0
    sizes = pl.size_axes(brand.axes)
    every = [keys.key_of(each, brand.axes) for each in brand.combinations()]
    unsized = [
        keys.key_of(each, brand.axes)
        for each in brand.combinations()
        if all(each[axis] == sizes[axis].default for axis in sizes)
    ]
    assert sizes and len(unsized) < len(every)
    for name, piece in drawn.items():
        expected = every if starter.names_a_size(PIECES / name) else unsized
        assert sorted(piece.keys) == sorted(expected), name
        colours = colours_of(piece)
        for served, scene in scenes_of(piece):
            assert checks.drawn_contrast(scene, colours, served) == [], name
            measured += sum(1 for _ in texts(scene))
    assert measured > 0


def test_the_measure_of_a_text_reads_each_combination(drawn: Mapping[str, Any]) -> None:
    """A text below its contrast in one combination alone is found there, so the test above
    reads what the brand gives in each."""
    card = drawn["card"]
    colours = colours_of(card)
    last = sorted(card.keys)[-1]
    weak = {**colours["text-secondary"], last: colours["surface"][last]}
    [(_, scene), *_] = scenes_of(card)
    found = checks.drawn_contrast(scene, {**colours, "text-secondary": weak}, card.keys)
    assert found
    assert all(finding.code == "contrast-drawn" for finding in found)
    assert all(f"`{last}`" in finding.message for finding in found)


# --- its fonts --------------------------------------------------------------------------------


def named_families(brand: Any) -> set[str]:
    """Each family a font or typography role names, in any combination."""
    families: set[str] = set()
    for role, combination in itertools.product(brand.valued, brand.combinations()):
        value = brand.resolve(role, combination)
        if brand.type_of(role) == "fontFamily":
            families.update(value)
        elif brand.type_of(role) == "typography":
            families.update(value["fontFamily"])
    return families


def weight_of(path: Path) -> int:
    """The weight a font file declares of itself, in its `OS/2` table."""
    font = TTFont(str(path), lazy=True)
    try:
        table: Any = font["OS/2"]
        return int(table.usWeightClass)
    finally:
        font.close()


def test_its_fonts_and_their_licences_are_committed_unchanged() -> None:
    found = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (NEUTRAL / "fonts").iterdir()
    }
    assert found == UNCHANGED


def test_each_font_file_lies_beside_its_licence() -> None:
    for font, licence in LICENCE_OF.items():
        assert (NEUTRAL / "fonts" / font).is_file()
        text = (NEUTRAL / "fonts" / licence).read_text(encoding="utf-8")
        assert "SIL Open Font License, Version 1.1" in text


def test_each_family_it_names_has_its_file(brand: Any) -> None:
    families = named_families(brand)
    files = {brand.font_file(family).name for family in families}
    assert files == set(LICENCE_OF)
    assert families == set(brand.families())


def test_each_typography_roles_weight_is_the_weight_of_its_familys_file(brand: Any) -> None:
    """A family's one file measures and draws it whatever its weight, so a weight its file
    does not have would be drawn in another (DEC-012 point 4, "A weight's own file", and
    DEC-004 point 9). Each weight is so a family of its own."""
    measured = 0
    for role, combination in itertools.product(brand.valued, brand.combinations()):
        if brand.type_of(role) != "typography":
            continue
        value = brand.resolve(role, combination)
        for family in value["fontFamily"]:
            assert weight_of(brand.font_file(family)) == value["fontWeight"], (role, family)
            measured += 1
    assert measured > 0
