"""A brand's own axes through the engine (visual-communication DEC-004 points 2, 3 and 5,
DEC-023 point 1): a piece names the modes of an axis of its brand's own as it names a shared
one, and a mode its brand lacks fails, after a brand switch too; a size axis of its own
draws a scene for each of its modes; the HTML page gives a value axis of its own, which no
reader's signal names, a file of its own; the CSS and JSON code writers write it as they
write a shared one; and adding an axis with a default changes no key that existed.

Each project is the drawing project of the pipeline's tests, the figure `flow` in the test
brand on the foundations' release 1.0.0, its copy of the test brand given an axis of its
own (`giving_own_axis`)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tests import test_visual_communication_pipeline as drawing
from tests.in_process import load
from tests.test_visual_communication_pipeline import (
    drawing_project,
    list_drawing_libraries,
    project_of,
)
from tests.visual_communication_project import (
    RELEASED_FOUNDATIONS,
    TEST_BRAND,
    WINTER_ACCENT,
    giving_own_axis,
    importable,
    write_piece,
)

pl, tokens, keys, values, exports, css, json_writer, html = load(
    "visual-communication",
    "pipeline",
    "tokens",
    "keys",
    "values",
    "exports",
    "plugins.css",
    "plugins.json",
    "plugins.html",
)

PIECE = "flow"
LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0"}

#: The modes the drawing project's piece names, the shared colour scheme's two.
SCHEMES = {"colour-scheme": ["light", "dark"]}

#: The modes of each kind of axis `giving_own_axis` gives by default.
OWN = {"value": ("season", ["summer", "winter"]), "size": ("density", ["roomy", "compact"])}


def brand_folder(root: Path, name: str = "test-brand") -> Path:
    return root / "visual" / "libraries" / name / "1.0.0"


def own_project(tmp_path: Path, kind: str, modes: Mapping[str, list[str]]) -> Any:
    """The drawing project, its test brand given an axis of its own of `kind`, its piece
    drawn in `modes`."""
    root = drawing_project(tmp_path, picture=False, modes=dict(modes))
    giving_own_axis(brand_folder(root), *own_axis(kind))
    return project_of(root)


def own_axis(kind: str) -> tuple[str, str]:
    return OWN[kind][0], kind


def released() -> Any:
    return tokens.read_declarations(RELEASED_FOUNDATIONS / "roles.yaml")


def axes_of(brand: Any) -> dict[str, dict[str, Any]]:
    """The axes as the command hands them to a code writer (`code.plan`)."""
    return {
        axis.name: {"kind": axis.kind, "modes": list(axis.modes), "default": axis.default}
        for axis in sorted(brand.axes.values(), key=lambda axis: axis.name)
    }


def css_sheet(brand: Any) -> str:
    """The CSS writer's sheet of `brand`'s value axes, each size axis at its default, as the
    command hands it."""
    spelled = {n: a for n, a in axes_of(brand).items() if a["kind"] == "value"}
    combinations = keys.combinations({n: a["modes"] for n, a in spelled.items()}, brand.axes)
    document = values.document(brand, combinations, LOCK)
    document["tokens"] = {p: t for p, t in document["tokens"].items() if t["type"] in css.KINDS}
    return css.write(document, spelled)


def json_file(brand: Any) -> dict[str, Any]:
    document = values.document(brand, brand.combinations(), LOCK)
    return json.loads(json_writer.write(document, axes_of(brand), form=2))


# --- a piece names an axis of its brand's own ---------------------------------------------------


@pytest.mark.parametrize("kind", ["value", "size"])
def test_a_piece_names_the_modes_of_an_axis_of_its_brands_own(tmp_path: Path, kind: str) -> None:
    name, _ = own_axis(kind)
    modes = OWN[kind][1]
    project = own_project(tmp_path, kind, {name: modes})
    assert project.keys == ["default", f"{name}.{modes[1]}"]
    document = project.values()
    assert document["keys"] == project.keys


def test_a_size_axis_of_its_own_draws_a_scene_for_each_of_its_modes(tmp_path: Path) -> None:
    project = own_project(tmp_path, "size", {"density": ["roomy", "compact"], **SCHEMES})
    assert project.size_keys == ["default", "density.compact"]
    results = project.scenes(facts=project.piece.stand_ins)
    assert [result.scene.size_key for _, result in results] == ["default", "density.compact"]


def test_a_value_axis_of_its_own_takes_a_scene_for_all_its_modes(tmp_path: Path) -> None:
    project = own_project(tmp_path, "value", {"season": ["summer", "winter"]})
    assert project.size_keys == ["default"]


def test_a_mode_its_brand_lacks_fails(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, modes={"season": ["autumn"]})
    giving_own_axis(brand_folder(root))
    with pytest.raises(drawing.pl.Refused, match="`autumn` is not a mode of `season`"):
        project_of(root)


def test_an_axis_of_its_own_fails_after_a_switch_to_a_brand_that_lacks_it(tmp_path: Path) -> None:
    """The piece names `season` of the test brand's own, and its brand is switched to `plain`,
    a copy of the test brand with no axis of its own."""
    root = drawing_project(tmp_path, picture=False, modes={"season": ["summer", "winter"]})
    giving_own_axis(brand_folder(root))
    project_of(root)

    plain = brand_folder(root, "plain")
    shutil.copytree(TEST_BRAND, plain)
    library = plain / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace("name: test-brand", "name: plain"),
        encoding="utf-8",
    )
    list_drawing_libraries(root, plain="project")
    write_piece(
        root,
        PIECE,
        brand="plain",
        modes={"season": ["summer", "winter"]},
        exports=["svg"],
        lock={"foundations": "1.0.0", "plain": "1.0.0", "tests": "1.0.0"},
    )
    with pytest.raises(drawing.pl.Refused, match="`season` is not an axis"):
        project_of(root)


# --- the HTML page and the code writers ---------------------------------------------------------


def test_the_html_page_gives_a_value_axis_of_its_own_a_file_of_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No reader's signal names `season`, so its winter takes a file of its own, where the
    dark colour scheme shares the light one's (DEC-023 point 1)."""
    importable(monkeypatch, html)
    project = own_project(tmp_path, "value", {"season": ["summer", "winter"], **SCHEMES})
    results = project.scenes(facts=project.piece.stand_ins)
    held = [group for _, group, _ in pl.drawn(project, results, "html")]
    assert held == [
        ("default", "colour-scheme.dark"),
        ("season.winter", "colour-scheme.dark+season.winter"),
    ]


def test_the_css_writer_switches_a_value_axis_of_its_own_by_its_attribute(tmp_path: Path) -> None:
    folder = giving_own_axis(shutil.copytree(TEST_BRAND, tmp_path / "test-brand" / "1.0.0"))
    brand = tokens.read_brand(folder, released())
    sheet = css_sheet(brand)
    assert '[data-season="winter"] {\n  --accent: #336699;\n' in sheet


def test_the_json_writer_names_each_combination_of_an_axis_of_its_own_by_its_key(
    tmp_path: Path,
) -> None:
    folder = giving_own_axis(shutil.copytree(TEST_BRAND, tmp_path / "test-brand" / "1.0.0"))
    brand = tokens.read_brand(folder, released())
    written = json_file(brand)
    assert "season.winter" in written["keys"]
    assert written["tokens"]["accent"]["values"]["season.winter"] == WINTER_ACCENT


# --- a key stays the same when a brand adds an axis with a default (DEC-004 point 3) ------------


@pytest.mark.parametrize("kind", ["value", "size"])
def test_an_axis_of_its_own_with_a_default_changes_no_key_that_existed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """The test brand, before and after it adds an axis of its own: its combinations, the
    names its CSS and JSON code writers write, a piece's export file names and each picture
    variant's key are each as they were, the new axis at its default."""
    name, _ = own_axis(kind)
    before = tokens.read_brand(TEST_BRAND, released())
    folder = giving_own_axis(
        shutil.copytree(TEST_BRAND, tmp_path / "test-brand" / "1.0.0"), name, kind
    )
    after = tokens.read_brand(folder, released())

    old = [keys.key_of(c, before.axes) for c in before.combinations()]
    new = [keys.key_of(c, after.axes) for c in after.combinations()]
    assert set(old) <= set(new)
    at_default = [c for c in after.combinations() if c[name] == after.axes[name].default]
    assert [keys.key_of(c, after.axes) for c in at_default] == old

    if kind == "size":
        assert css_sheet(after) == css_sheet(before)
    else:
        sheet_before, sheet_after = css_sheet(before), css_sheet(after)
        assert set(_names(sheet_before)) == set(_names(sheet_after))
        assert set(_selectors(sheet_before)) <= set(_selectors(sheet_after))
    written_before, written_after = json_file(before), json_file(after)
    assert set(written_before["keys"]) <= set(written_after["keys"])
    assert set(written_before["tokens"]) == set(written_after["tokens"])
    for path, token in written_before["tokens"].items():
        for key, value in token["values"].items():
            assert written_after["tokens"][path]["values"][key] == value

    variants_before = values.variants(
        values.document(before, before.combinations(), LOCK, tokens=["accent", "space.3"])
    )
    variants_after = values.variants(
        values.document(after, after.combinations(), LOCK, tokens=["accent", "space.3"])
    )
    for key, served in variants_before.items():
        assert key in variants_after
        assert set(served) <= set(variants_after[key])

    root = drawing_project(tmp_path / "piece", picture=False, modes=SCHEMES)
    names_before = [exports.file_name(PIECE, 1, "en", key, "svg") for key in project_of(root).keys]
    giving_own_axis(brand_folder(root), name, kind)
    names_after = [exports.file_name(PIECE, 1, "en", key, "svg") for key in project_of(root).keys]
    assert names_after == names_before


def _names(sheet: str) -> list[str]:
    """Each custom property the sheet declares."""
    return [line.split(":")[0].strip() for line in sheet.splitlines() if line.startswith("  --")]


def _selectors(sheet: str) -> list[str]:
    """Each rule's selector."""
    return [line[: -len(" {")] for line in sheet.splitlines() if line.endswith(" {")]
