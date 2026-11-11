"""A project adds a kind of piece the capability does not ship, a poster, and its own brand
draws it, with no file of the capability changed (visual-communication UC-104's main path):
the poster, a top that declares its physical size (DEC-034 point 3); the brand's drawing of
its layout, which the brand may hold since it names the poster's library (DEC-034 points 1
and 6, DEC-009 point 3); and what render, check and export make of a piece of it, each where
DEC-002 point 1 places it.

The project's own work is the committed fixture `tests/fixtures/visual-communication/poster/`,
laid out as it lies in the location: the component library `test-print`, which holds the
poster, a page alone printed at A1; the test brand's drawing of the poster's one layout; and
`conference`, a poster under the test brand. A location holds it beside the foundations
being built and the test brand that gives sizes, the project's own brand, whose
`library.yaml` the project makes name `test-print`. The commands run in this process.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load, run_main
from tests.test_visual_communication_pdf import read as read_pdf
from tests.visual_communication_project import (
    CONFIG,
    FIXTURES,
    copy_library,
    hold_shipped,
    importable,
    locked_at,
    project,
    taken,
    write,
    write_list,
    yaml_text,
)

render, check, export, pl, checks, findings, reading, svg, pdf = load(
    "visual-communication",
    "render.py",
    "check.py",
    "export.py",
    "pipeline",
    "checks",
    "findings",
    "reading",
    "plugins.svg",
    "plugins.pdf",
)

#: The files the project adds to its location to make a poster, each at its place there.
POSTER = FIXTURES / "poster"
#: The test brand that gives sizes, built on the foundations being built: the project's own
#: brand, as the project holds it before it adds the poster.
SIZED_BRAND = FIXTURES / "libraries" / "test-brand" / "1.1.0"
BRAND = "visual/libraries/test-brand/1.1.0"
PIECE = "conference"
PIECE_FOLDER = f"visual/pieces/{PIECE}"
#: Where the capability keeps what a render and an export make, local to the clone.
LOCAL = ".pkit/capabilities/visual-communication/project/local"
PREVIEWS = f"{LOCAL}/previews/{PIECE}"
EXPORTS = f"{LOCAL}/exports/{PIECE}"
PREVIEW = f"{PIECE}.en.default.svg"
EXPORT = f"{PIECE}.v1.en.default.pdf"

#: The poster's trim size, A1 upright, in millimetres, as its top declares it.
A1 = {"width": 594, "height": 841}
#: The width the poster asks for, the test brand's `size.figure`, and the height A1 gives it.
WIDTH = 960
HEIGHT = round(WIDTH * 841 / 594, 2)
#: A1 in PDF points, 72 to the inch: the page an export draws the poster on.
A1_POINTS = "0 0 1683.78 2383.94"

#: What the piece's content gives the poster's two fields.
TITLE = "Drawing with data"
DETAILS = "Hall B, on 14 May at ten in the morning."


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderers stand in for the import a run makes when it draws, for the length of
    the test."""
    importable(monkeypatch, svg, pdf)
    yield


def poster_project(tmp_path: Path) -> Path:
    """A project whose location holds the foundations being built, the test brand, and the
    files the project adds to make a poster. The brand names the poster's library among
    those it builds on, by its major, so its drawing of the poster draws (DEC-009 point 3).
    The piece is locked at the versions the location holds."""
    root = project(tmp_path)
    copy_library(root, SIZED_BRAND, "test-brand", "1.1.0")
    shutil.copytree(POSTER, root / "visual", dirs_exist_ok=True)
    library = root / BRAND / "library.yaml"
    brand = dict(reading.read_yaml(library))
    brand["builds-on"] = [*brand["builds-on"], {"name": "test-print", "major": 1}]
    write(library, yaml_text(brand))
    unreleased = {"released": False}
    write_list(
        root,
        {
            "test-brand": {"source": {"kind": "project"}, "versions": {"1.1.0": unreleased}},
            "test-print": {"source": {"kind": "project"}, "versions": {"1.0.0": unreleased}},
        },
    )
    built = hold_shipped(root, "foundations").version
    locked_at(root / PIECE_FOLDER, {"foundations": built})
    return root


def scene_of(root: Path) -> Any:
    """The poster's one scene, in its one language at its one key, as the check draws it."""
    piece = pl.read_piece(root, "visual", PIECE)
    drawn = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    [(language, result)] = drawn.scenes(facts=piece.stand_ins)
    assert language == "en"
    return result


def files_under(folder: Path) -> list[Path]:
    return sorted(path for path in folder.rglob("*") if path.is_file())


def contents(folder: Path) -> dict[str, bytes]:
    """Each file under `folder`, by its path there, and its bytes."""
    return {path.relative_to(folder).as_posix(): path.read_bytes() for path in files_under(folder)}


# --- the scene ----------------------------------------------------------------------------------


def test_the_brands_drawing_draws_the_poster_at_the_height_its_physical_size_sets(
    tmp_path: Path,
) -> None:
    """The brand's drawing asks for its width, and the engine sets the height from it in
    A1's proportion (DEC-034 points 2 and 3). The instance keeps its id, and what each field
    shows the field's name (point 5)."""
    result = scene_of(poster_project(tmp_path))
    assert [finding.code for finding in result.findings] == []
    element = result.scene.find("poster")
    assert element is not None
    group = element.properties
    assert (group["component"], group["version"]) == ("test-brand/poster", "1.1.0")
    assert (group["width"], group["height"]) == (WIDTH, HEIGHT)
    assert element.sources["height"] == "engine"
    assert result.scene.find("poster/band") is not None
    for field, text in (("title", TITLE), ("details", DETAILS)):
        shown = result.scene.find(f"poster/{field}")
        assert shown is not None and shown.properties["text"] == text
    root = result.scene.to_dict()
    assert (root["pages"], root["physical-size"]) == (["poster"], A1)


# --- render, check and export -------------------------------------------------------------------


def test_the_poster_renders_drawn_by_the_brands_drawing(tmp_path: Path) -> None:
    root = poster_project(tmp_path)
    shown = run_main(render, PIECE, cwd=root)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[1:] == [
        f"previews: 1 file(s) in {PREVIEWS}/",
        f"findings: 0 kept in {PIECE_FOLDER}/findings.yaml",
    ]
    assert list(contents(root / PREVIEWS)) == [PREVIEW]
    drawn = (root / PREVIEWS / PREVIEW).read_text(encoding="utf-8")
    assert re.match(rf'<svg [^>]*width="{WIDTH}" height="{HEIGHT}"', drawn)
    assert 'data-id="poster/band"' in drawn
    assert f">{TITLE}</tspan>" in drawn


def test_the_poster_passes_the_check_with_no_failing_finding(tmp_path: Path) -> None:
    """The check judges the brand's version, which holds the drawing, the poster's library
    and the piece, its scene read from the record the render keeps."""
    root = poster_project(tmp_path)
    assert run_main(render, PIECE, cwd=root).returncode == 0
    shown = run_main(check, cwd=root)
    assert shown.returncode == 0, shown.stdout
    assert shown.stdout.splitlines()[0] == (
        "1 piece(s) in `visual`: the scenes of 1 read from their findings record, of 0 "
        "computed now, of 0 not checked."
    )
    failing = [
        (finding.code, finding.file, finding.where)
        for finding, level in checks.check(root).judged
        if level == findings.FAILS
    ]
    assert failing == []


def test_the_poster_exports_a_pdf_whose_page_is_its_physical_size(tmp_path: Path) -> None:
    """594 by 841 mm is 1683.78 by 2383.94 pt (DEC-034 point 3). The brand's drawing sets
    the title under its band and the details at the foot."""
    root = poster_project(tmp_path)
    shown = run_main(export, PIECE, cwd=root)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[1:] == [
        f"export: {EXPORTS}/{EXPORT}",
        f"export: version 1 recorded in {PIECE_FOLDER}/exports.yaml",
    ]
    file = read_pdf((root / EXPORTS / EXPORT).read_bytes())
    [page] = file.pages()
    assert re.findall(r"/MediaBox \[([^\]]*)\]", file.value(page)) == [A1_POINTS]
    assert file.lines(page) == [TITLE, DETAILS]


# --- where the files lie ------------------------------------------------------------------------


def test_what_the_project_adds_and_makes_lies_in_its_own_folders(tmp_path: Path) -> None:
    """After render, check and export, every file of the project lies in its location, or
    in the capability's folder of the project's own, where the capability records the
    location and keeps what a render and an export make (DEC-002 point 1). The foundations
    the location holds are the capability's own, byte for byte."""
    root = poster_project(tmp_path)
    assert run_main(render, PIECE, cwd=root).returncode == 0
    assert run_main(check, cwd=root).returncode == 0
    assert run_main(export, PIECE, cwd=root).returncode == 0
    location = root / "visual"
    own = root / CONFIG.removesuffix("/config.yaml")
    assert [
        path.relative_to(root).as_posix()
        for path in files_under(root)
        if not path.is_relative_to(location) and not path.is_relative_to(own)
    ] == []
    shipped = taken("foundations", being_built=True)
    held = location / "libraries" / "foundations" / shipped.version
    assert contents(held) == contents(shipped.folder)
