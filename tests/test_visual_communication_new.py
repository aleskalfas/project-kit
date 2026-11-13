"""`pkit visual new <piece>` (visual-communication DEC-002 points 3 and 5, DEC-029 point 4): a
new piece's first files, stamped from what a person chooses. A deck, a figure and a site
stamped by it hold their schemas, and their first render writes the lock and passes the check;
its `piece.yaml` is the text `piece.md` shows; each refusal writes nothing, nor does a write
that fails. Run in this process, the SVG renderer standing in for the import a render makes."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import every_file
from tests.visual_communication_project import (
    CONFIG,
    add_library,
    importable,
    project,
    taken,
    write,
)
from tests.visual_communication_writes import FULL, failing

script, add, render, check, svg, seam, files, reading = load(
    "visual-communication",
    "new.py",
    "add.py",
    "render.py",
    "check.py",
    "plugins.svg",
    "plugins.seam",
    "files",
    "reading",
)

PIECE = "first-talk"
FOLDER = f"visual/pieces/{PIECE}"
#: The choices every piece of these tests makes, but for its top and its exports.
CHOSEN = ("--brand", "neutral", "--language", "en", "--audience", "Tests.", "--shown", "Nowhere.")


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    importable(monkeypatch, svg)
    yield
    seam.unregister("svg")


def _with_libraries(tmp_path: Path, *, being_built: bool = False) -> Path:
    """A project whose location holds the foundations and the neutral brand, the versions
    being built where `being_built` is true."""
    root = project(tmp_path)
    for library in ("foundations", "neutral"):
        added = run_main(add, library, *(["--being-built"] if being_built else []), cwd=root)
        assert added.returncode == 0, added.stderr
    return root


def _new(root: Path, *args: str) -> Any:
    return run_main(script, *args, cwd=root)


# --- what it writes ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("top", "exports", "being_built", "fields"),
    [
        ("deck", "pdf", False, {"slides"}),
        ("figure", "svg", False, {"body", "caption"}),
        ("site", "html", True, {"pages", "header", "footer"}),
    ],
)
def test_a_stamped_piece_holds_its_schemas_and_its_first_render_writes_the_lock_and_passes(
    tmp_path: Path, top: str, exports: str, being_built: bool, fields: set[str]
) -> None:
    root = _with_libraries(tmp_path, being_built=being_built)
    stamped = _new(root, PIECE, "--top", f"foundations/{top}", "--export", exports, *CHOSEN)
    assert stamped.returncode == 0, stamped.stderr
    assert f"`pkit visual render {PIECE}`" in stamped.stdout
    folder = root / FOLDER
    assert sorted(path.name for path in folder.iterdir()) == [
        "brief.yaml",
        "content.en.yaml",
        "piece.yaml",
    ]
    for name, kind in (("piece", "piece"), ("content.en", "content"), ("brief", "brief")):
        data = reading.read_yaml(folder / f"{name}.yaml")
        assert files.shape_problems(data, kind) == [], name
    content = files.without_binding(reading.read_yaml(folder / "content.en.yaml"))
    assert set(content) == fields
    assert files.without_binding(reading.read_yaml(folder / "brief.yaml")) == {}
    assert "lock" not in reading.read_yaml(folder / "piece.yaml")
    rendered = run_main(render, PIECE, cwd=root)
    assert rendered.returncode == 0, rendered.stderr
    assert "\nfails:" not in f"\n{rendered.stdout}", rendered.stdout
    assert {"foundations", "neutral"} == set(reading.read_yaml(folder / "piece.yaml")["lock"])
    for args in ((PIECE,), ()):
        checked = run_main(check, *args, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
        assert checked.returncode == 0, checked.stdout


def test_a_deck_s_content_holds_one_cover_each_of_its_slots_empty(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    assert _new(root, PIECE, "--top", "foundations/deck", *CHOSEN).returncode == 0
    assert (root / FOLDER / "content.en.yaml").read_text(encoding="utf-8") == (
        "pkit_schema: visual-communication:content\n"
        "schema_version: 1\n"
        "slides:\n"
        "  - id: cover\n"
        "    layout: cover\n"
        "    title: ''\n"
        "    subtitle: ''\n"
        "    author: ''\n"
        "    link: ''\n"
    )


#: A top of the project's own library, a field and a slot of which declare a list of types.
BOARD = """\
pkit_schema: visual-communication:component
schema_version: 1

status: experimental
about: A board of pages, whose note and whose aside may be left null.

fields:
  type: object
  properties:
    pages:
      type: array
      items: {type: object}
      x-pkit-pages: true
    title:
      type: string
    note:
      type: [string, "null"]

layouts:
  plain:
    slots:
      heading: {type: string}
      aside: {type: [string, "null"]}
    parts:
      background:
        box: {fill: surface}
        width: "=:width"
        height: "=:height"
"""


def test_a_field_or_slot_of_a_list_of_types_is_left_out(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    folder = add_library(root, "ours", "1.0.0", builds_on={"foundations": 1})
    board = write(folder / "components" / "board.yaml", BOARD)
    assert files.shape_problems(reading.read_yaml(board), "component") == []
    stamped = _new(root, PIECE, "--top", "ours/board", *CHOSEN)
    assert stamped.returncode == 0, stamped.stderr
    assert (root / FOLDER / "content.en.yaml").read_text(encoding="utf-8") == (
        "pkit_schema: visual-communication:content\n"
        "schema_version: 1\n"
        "pages:\n"
        "  - id: plain\n"
        "    layout: plain\n"
        "    heading: ''\n"
        "title: ''\n"
    )


def test_its_piece_yaml_is_the_text_piece_md_shows_with_each_choice(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    stamped = _new(
        root,
        PIECE,
        "--top",
        "foundations/deck",
        "--brand",
        "neutral",
        "--language",
        "en",
        "--language",
        "no",
        "--audience",
        "New members of the team, who have not seen the project yet.",
        "--shown",
        "On a screen, at the team's weekly meeting.",
        "--explains",
        "--export",
        "pdf",
        "--mode",
        "colour-scheme=light,dark",
    )
    assert stamped.returncode == 0, stamped.stderr
    folder = root / FOLDER
    assert (folder / "piece.yaml").read_text(encoding="utf-8") == (
        "pkit_schema: visual-communication:piece\n"
        "schema_version: 1\n"
        "top: foundations/deck\n"
        "brand: neutral\n"
        'languages: [en, "no"]\n'
        'audience: "New members of the team, who have not seen the project yet."\n'
        'shown: "On a screen, at the team\'s weekly meeting."\n'
        "explains: true\n"
        "exports: [pdf]\n"
        "state: draft\n"
        "modes:\n"
        "  colour-scheme: [light, dark]\n"
    )
    assert (folder / "content.no.yaml").read_bytes() == (folder / "content.en.yaml").read_bytes()


def test_it_records_the_location_it_takes(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    (root / CONFIG).unlink()
    stamped = _new(root, PIECE, "--top", "foundations/figure", *CHOSEN)
    assert stamped.returncode == 0, stamped.stderr
    assert "recorded the location `visual`" in stamped.stdout
    assert "location: visual" in (root / CONFIG).read_text(encoding="utf-8")


# --- what it refuses ---------------------------------------------------------------------------


def _refused(root: Path, *args: str) -> str:
    """What the command says where it refuses `args`, having written nothing."""
    before = every_file(root)
    refused = _new(root, *args)
    assert refused.returncode == 1, refused.stdout
    assert every_file(root) == before
    return refused.stderr


def test_it_refuses_a_name_taken_and_writes_over_nothing(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    write(root / FOLDER / "notes.txt", "mine\n")
    said = _refused(root, PIECE, "--top", "foundations/deck", *CHOSEN)
    assert f"{FOLDER} lies in the location already, so the name `{PIECE}` is taken" in said


@pytest.mark.parametrize("name", ["First-Talk", "first_talk", "yes", "1st"])
def test_it_refuses_a_name_not_of_a_piece_s_shape(tmp_path: Path, name: str) -> None:
    root = _with_libraries(tmp_path)
    said = _refused(root, name, "--top", "foundations/deck", *CHOSEN)
    assert f"`{name}` is not a piece's name" in said
    assert not (root / "visual/pieces").exists()


def test_it_refuses_a_brand_the_location_lacks_naming_add(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert run_main(add, "foundations", cwd=root).returncode == 0
    said = _refused(root, PIECE, "--top", "foundations/deck", *CHOSEN)
    assert "the location holds no version of `neutral`" in said
    assert "`pkit visual add neutral`" in said


def test_it_refuses_a_top_whose_library_the_location_lacks_naming_add(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    said = _refused(root, PIECE, "--top", "starter/list", *CHOSEN)
    assert "`pkit visual add starter`" in said


def test_it_refuses_a_library_of_the_project_s_own_it_lacks(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    said = _refused(root, PIECE, "--top", "foundations/deck", "--notation", "ours", *CHOSEN)
    said_of = "the location holds no version of `ours`: put a version of it in visual/libraries/"
    assert said_of in said


def test_it_refuses_a_top_its_library_lacks(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    said = _refused(root, PIECE, "--top", "foundations/poster", *CHOSEN)
    added = taken("foundations").version
    assert f"foundations@{added} holds no component `poster`" in said


def test_it_refuses_a_choice_the_piece_s_schema_refuses(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    said = _refused(
        root, PIECE, "--top", "foundations/deck", *CHOSEN, "--language", "EN", "--export", "gif"
    )
    assert "piece.yaml would not hold its schema: /exports/0: " in said
    assert "/languages/1: " in said


def test_with_no_location_it_refuses_and_records_none(tmp_path: Path) -> None:
    root = project(tmp_path)
    said = _refused(root, PIECE, "--top", "foundations/deck", *CHOSEN)
    assert "`pkit visual add foundations`" in said
    assert not (root / CONFIG).exists()


def test_a_mode_without_its_axis_is_a_usage_error(tmp_path: Path) -> None:
    root = _with_libraries(tmp_path)
    before = every_file(root)
    stopped = _new(root, PIECE, "--top", "foundations/deck", *CHOSEN, "--mode", "dark")
    assert stopped.returncode == 2
    assert "--mode `dark`: give it as <axis>=<mode>" in stopped.stderr
    assert every_file(root) == before


def test_a_write_that_fails_leaves_no_part_of_the_piece(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _with_libraries(tmp_path)
    before = every_file(root)
    failing(monkeypatch, write=[PIECE])
    shown = _new(root, PIECE, "--top", "foundations/deck", *CHOSEN)
    assert shown.returncode == 1
    assert shown.stderr.startswith(f"error: {FOLDER} could not be written: ")
    assert FULL in shown.stderr
    assert every_file(root) == before
    assert not (root / FOLDER).exists()
