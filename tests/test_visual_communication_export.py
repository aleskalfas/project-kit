"""`pkit visual export <piece>` (visual-communication DEC-006 point 7): numbered exports in
the clone's local folder, never overwriting another; their record, `exports.yaml`; no stale
or missing produced picture, unless the person names a stale one; a piece of several
pages, one file for each page under one number; a piece exported as PDF, one file for each
language and combination holding its pages in order; what a write that fails leaves; and a
published piece's current copy, with the gate on its lock (DEC-017 points 5, 7 and 8)."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_pdf import read as read_pdf
from tests.test_visual_communication_pipeline import (
    LOCK,
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    list_drawing_libraries,
    stamped,
    write_content,
    write_picture,
)
from tests.test_visual_communication_render import newer_tests
from tests.visual_communication_project import CONFIG, SCHEMAS, bound, importable, write, yaml_text
from tests.visual_communication_writes import FULL, failing

script, render_script, exports, svg, pdf, seam, framing, files, reading, fingerprint, pl, checks = (
    load(
        "visual-communication",
        "export.py",
        "render.py",
        "exports",
        "plugins.svg",
        "plugins.pdf",
        "plugins.seam",
        "framing",
        "files",
        "reading",
        "fingerprint",
        "pipeline",
        "checks",
    )
)

FOLDER = ".pkit/capabilities/visual-communication/project/local/exports/flow"
RECORD = f"{PIECE_FOLDER}/exports.yaml"
COPY = f"{PIECE_FOLDER}/current-copy"
TEXT = "{http://www.w3.org/2000/svg}text"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderers stand in for the import a run makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg, pdf)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def ready(tmp_path: Path, **fields: Any) -> Path:
    """The skeleton piece with its picture, ready to export."""
    root = drawing_project(tmp_path, **fields)
    write_picture(root, framing)
    return root


def exported(root: Path) -> list[str]:
    return sorted(path.name for path in (root / FOLDER).iterdir())


def test_each_run_takes_the_next_number_and_records_it(tmp_path: Path) -> None:
    root = ready(tmp_path)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines() == [
        f"recorded the location `visual` (the default, at the repository's top) in {CONFIG}; "
        f"to move the work, move the folder and change the `location:` line there",
        f"export: {FOLDER}/flow.v1.en.default.svg",
        f"export: {FOLDER}/flow.v1.en.colour-scheme.dark.svg",
        f"export: version 1 recorded in {RECORD}",
    ]
    assert run(root, PIECE).returncode == 0
    assert exported(root) == [
        "flow.v1.en.colour-scheme.dark.svg",
        "flow.v1.en.default.svg",
        "flow.v2.en.colour-scheme.dark.svg",
        "flow.v2.en.default.svg",
    ]
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    first, second = record["versions"]
    assert (first["version"], second["version"]) == (1, 2)
    assert first["fingerprint"] == second["fingerprint"]
    assert second["files"] == {
        name: reading.sha256((root / FOLDER / name).read_bytes())
        for name in ("flow.v2.en.default.svg", "flow.v2.en.colour-scheme.dark.svg")
    }
    recorded = second["recorded"]
    assert (recorded["state"], recorded["renderers"], recorded["used-stale"]) == (
        "draft",
        {"svg": "1.0.1"},
        [],
    )
    assert "time: '" in (root / RECORD).read_text(encoding="utf-8")


def test_each_version_keeps_the_state_it_was_made_in(tmp_path: Path) -> None:
    root = ready(tmp_path)
    assert run(root, PIECE).returncode == 0
    list_drawing_libraries(root, released=True)
    path = root / PIECE_FOLDER / "piece.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("state: draft", "state: published"),
        encoding="utf-8",
    )
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    assert [version["recorded"]["state"] for version in record["versions"]] == [
        "draft",
        "published",
    ]


def test_the_record_names_each_produced_output_used_by_its_records_fingerprint(
    tmp_path: Path,
) -> None:
    root = ready(tmp_path)
    produced = reading.read_yaml(root / PIECE_FOLDER / "produced" / "square" / "record.yaml")
    assert run(root, PIECE).returncode == 0
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert version["recorded"]["used"] == {"square": produced["fingerprint"]["value"]}


def test_a_piece_that_shows_no_produced_output_records_none_used(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert run(root, PIECE).returncode == 0
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert (version["recorded"]["used"], version["recorded"]["used-stale"]) == ({}, [])


def test_an_export_draws_what_the_preview_draws(tmp_path: Path) -> None:
    root = ready(tmp_path)
    assert run(root, PIECE).returncode == 0
    light = (root / FOLDER / "flow.v1.en.default.svg").read_text(encoding="utf-8")
    assert light.startswith("<svg ") and 'data-key="default"' in light
    assert "data:image/png;base64," in light


def test_an_exports_inputs_name_its_whole_lock(tmp_path: Path) -> None:
    """Marking a version final reads the lock back from these inputs (DEC-017 point 1). Each
    library the lock names gives its files, since an export refuses a lock that does not
    hold, so no pair is left out."""
    root = ready(tmp_path)
    assert run(root, PIECE).returncode == 0
    kept = reading.read_yaml(root / RECORD)["versions"][0]["fingerprint"]
    assert fingerprint.lock_of(kept) == LOCK


@pytest.mark.parametrize("library", sorted(LOCK))
def test_an_export_refuses_a_lock_it_could_not_name_whole(tmp_path: Path, library: str) -> None:
    root = ready(tmp_path)
    shutil.rmtree(root / "visual" / "libraries" / library / "1.0.0")
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert f"{library}@1.0.0, which the project does not hold" in shown.stderr
    assert not (root / RECORD).exists()


def test_it_uses_the_lock_as_written_and_never_moves_it(tmp_path: Path) -> None:
    root = ready(tmp_path)
    before = (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8")
    assert run(root, PIECE).returncode == 0
    assert (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8") == before
    assert reading.read_yaml(root / PIECE_FOLDER / "piece.yaml")["lock"] == LOCK


# --- stale and missing pictures -----------------------------------------------------------------


def make_stale(root: Path) -> None:
    """Give the picture another size than its record was made at."""
    path = root / PIECE_FOLDER / "piece.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("width: 100", "width: 120"), encoding="utf-8"
    )


def test_a_stale_picture_stops_the_export_naming_what_changed(tmp_path: Path) -> None:
    root = ready(tmp_path)
    make_stale(root)
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr.startswith("error: a produced picture is stale: `square` (")
    assert "`piece.yaml` at `produced.square` changed; the pixel size of the variant" in (
        shown.stderr
    )
    assert shown.stderr.rstrip().endswith(
        "Run `pkit visual produce flow <output>` for each, or name it with `--use-stale "
        "<output>` to export it as it is"
    )
    assert not (root / FOLDER).exists()
    assert not (root / RECORD).exists()


def test_a_stale_picture_named_is_used_and_recorded(tmp_path: Path) -> None:
    root = ready(tmp_path)
    make_stale(root)
    shown = run(root, PIECE, "--use-stale", "square")
    assert shown.returncode == 0, shown.stderr
    assert "used while stale: square" in shown.stdout.splitlines()
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert version["recorded"]["used-stale"] == ["square"]


def test_naming_an_output_the_piece_does_not_declare_is_refused(tmp_path: Path) -> None:
    root = ready(tmp_path)
    make_stale(root)
    shown = run(root, PIECE, "--use-stale", "sqaure")
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: `--use-stale sqaure` names no produced output of `flow`, which declares `square`\n"
    )
    assert not (root / CONFIG).exists()
    assert not (root / FOLDER).exists()
    assert not (root / RECORD).exists()


def test_naming_an_output_that_is_not_stale_uses_it_as_it_is_and_says_so(tmp_path: Path) -> None:
    root = ready(tmp_path)
    shown = run(root, PIECE, "--use-stale", "square")
    assert shown.returncode == 0, shown.stderr
    assert "not stale, so used as it is: square" in shown.stdout.splitlines()
    assert "used while stale: square" not in shown.stdout.splitlines()
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert version["recorded"]["used-stale"] == []


def test_a_combination_the_record_does_not_map_makes_the_picture_stale(tmp_path: Path) -> None:
    root = ready(tmp_path)
    path = root / PIECE_FOLDER / "piece.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "colour-scheme:\n", "contrast:\n    - high\n  colour-scheme:\n"
        ),
        encoding="utf-8",
    )
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    project.scenes()
    stale = exports.stale_outputs(project)
    assert "the combination `contrast.high` has no variant" in stale["square"]


def test_a_missing_picture_stops_the_export_whatever_is_named(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    shown = run(root, PIECE, "--use-stale", "square")
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: a produced picture the piece shows is missing: `square`: "
        f"{PIECE_FOLDER}/produced/square/record.yaml does not exist: the picture was never "
        "produced — run `pkit visual produce flow square`\n"
    )


# --- refusals -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({}, id="whose-lock-holds"),
        pytest.param(
            {"lock": {"foundations": "1.0.0", "test-brand": "2.0.0", "tests": "1.0.0"}},
            id="whose-lock-does-not-hold",
        ),
    ],
)
def test_a_final_piece_takes_no_export_and_nothing_is_written(
    tmp_path: Path, fields: dict[str, Any]
) -> None:
    root = drawing_project(tmp_path, state="final", picture=False, **fields)
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr == (
        "error: the piece `flow` is final (its state says so), and a final piece takes no export\n"
    )
    assert not (root / FOLDER).exists()
    assert not (root / RECORD).exists()
    assert not (root / CONFIG).exists()


def test_a_published_piece_on_a_version_not_yet_released_is_refused_and_writes_nothing(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, state="published", released=False, picture=False)
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert "the published piece `flow` locks tests@1.0.0, which is not yet released" in shown.stderr
    assert "release it: `pkit visual release tests`" in shown.stderr
    assert not (root / FOLDER).exists()
    assert not (root / RECORD).exists()


@pytest.mark.parametrize("pinned", [False, True], ids=["draft", "pinned"])
def test_a_drafts_export_takes_a_version_not_yet_released(tmp_path: Path, pinned: bool) -> None:
    root = drawing_project(tmp_path, pinned=pinned, picture=False)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr


def test_a_published_pieces_lock_refused_is_told_of_its_state_and_of_no_pin(
    tmp_path: Path,
) -> None:
    root = drawing_project(
        tmp_path, state="published", pinned=True, lock={**LOCK, "tests": "1.2.0"}, picture=False
    )
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the lock of visual/pieces/flow/piece.yaml cannot be exported: the lock names "
        "tests@1.2.0, which the project does not hold — the piece is published, so no render "
        "moves its lock: set it back to a draft and run `pkit visual render flow`\n"
    )
    assert not (root / FOLDER).exists()


@pytest.mark.parametrize(
    ("fields", "said"),
    [
        pytest.param(
            {"lock": None},
            "error: the lock of visual/pieces/flow/piece.yaml cannot be exported: the piece has "
            "no lock yet",
            id="no-lock",
        ),
        pytest.param(
            {"exports": []},
            "error: visual/pieces/flow/piece.yaml declares no format under `exports`: name "
            "`svg` or `pdf` there",
            id="no-format",
        ),
    ],
)
def test_a_refusal_exits_1_and_writes_nothing(
    tmp_path: Path, fields: dict[str, Any], said: str
) -> None:
    root = drawing_project(tmp_path, **fields)
    if fields.get("lock", LOCK) is not None:
        write_picture(root, framing)
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr.startswith(said)
    assert not (root / CONFIG).exists()
    assert not (root / FOLDER).exists()
    assert not (root / RECORD).exists()


@pytest.mark.parametrize(
    ("shows", "fact", "part"),
    [("number", "version", "number"), ("date", "date", "date")],
)
def test_a_piece_that_shows_a_number_or_a_date_is_refused_naming_the_element(
    tmp_path: Path, shows: str, fact: str, part: str
) -> None:
    root = stamped(tmp_path, shows)
    before = (root / PIECE_FOLDER / "piece.yaml").read_bytes()
    done = run(root, PIECE)
    assert done.returncode == 1
    assert (
        f"`flow` shows a fact no export fills yet, so a file would hold a stand-in: "
        f"`{fact}` at `figure/body/{part}`"
    ) in done.stderr
    assert not (root / FOLDER).exists()
    assert not (root / RECORD).exists()
    assert (root / PIECE_FOLDER / "piece.yaml").read_bytes() == before


def test_every_run_through_the_plan_stops_on_a_number_or_a_date(tmp_path: Path) -> None:
    root = stamped(tmp_path, "date", languages=["en", "cs"])
    write_content(root, "cs", body={"use": "tests/stamp", "shows": "date"})
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    with pytest.raises(pl.Refused) as refused:
        exports.plan(project)
    assert str(refused.value).count("`date` at `figure/body/date`") == 1


def test_a_piece_that_shows_only_its_language_and_state_exports_their_real_text(
    tmp_path: Path,
) -> None:
    root = stamped(tmp_path, "files", state="published")
    done = run(root, PIECE)
    assert done.returncode == 0, done.stderr
    drawn = (root / FOLDER / "flow.v1.en.default.svg").read_text(encoding="utf-8")
    shown = ["".join(text.itertext()) for text in ElementTree.fromstring(drawn).iter(TEXT)]
    assert shown[:2] == ["en", "published"]


def test_a_file_the_record_does_not_name_is_never_overwritten_and_refuses_nothing(
    tmp_path: Path,
) -> None:
    root = ready(tmp_path)
    left = root / FOLDER / "flow.v1.en.default.svg"
    left.parent.mkdir(parents=True)
    left.write_text("kept\n", encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert left.read_text(encoding="utf-8") == "kept\n"
    assert exported(root) == [
        "flow.v1.en.default.svg",
        "flow.v2.en.colour-scheme.dark.svg",
        "flow.v2.en.default.svg",
    ]
    assert [entry["version"] for entry in reading.read_yaml(root / RECORD)["versions"]] == [2]


def test_a_file_of_a_number_under_another_name_moves_the_run_past_that_number(
    tmp_path: Path,
) -> None:
    root = ready(tmp_path)
    folder = root / FOLDER
    folder.mkdir(parents=True)
    left = folder / "flow.v1.en.default.1.svg"
    left.write_text("kept\n", encoding="utf-8")
    (folder / "notes.txt").write_text("mine\n", encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert left.read_text(encoding="utf-8") == "kept\n"
    assert exported(root) == [
        "flow.v1.en.default.1.svg",
        "flow.v2.en.colour-scheme.dark.svg",
        "flow.v2.en.default.svg",
        "notes.txt",
    ]
    assert [entry["version"] for entry in reading.read_yaml(root / RECORD)["versions"]] == [2]


def test_a_record_that_cannot_be_read_stops_the_next_export_as_a_final_pieces(
    tmp_path: Path,
) -> None:
    root = ready(tmp_path)
    (root / RECORD).write_text("pkit_schema: visual-communication:exports\n[", encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert "is final (its record of exports cannot be read: " in shown.stderr
    assert str(root) not in shown.stderr


def test_the_export_fingerprint_changes_with_what_the_scenes_were_computed_from(
    tmp_path: Path,
) -> None:
    root = ready(tmp_path)
    assert run(root, PIECE).returncode == 0
    path = root / PIECE_FOLDER / "content.en.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Build it.", "Build it well."),
        encoding="utf-8",
    )
    assert run(root, PIECE).returncode == 0
    first, second = reading.read_yaml(root / RECORD)["versions"]
    assert first["fingerprint"] != second["fingerprint"]


# --- a piece of several pages -------------------------------------------------------------------

#: The top of a piece of several pages: its slot of pages places each slide as a page of its
#: own, drawn by the card (the layout tests' deck, as a file).
DECK = bound(
    "component",
    status="experimental",
    about="A deck whose slides are each a page, drawn by the card.",
    fields={
        "type": "object",
        "required": ["slides"],
        "properties": {
            "slides": {
                "type": "array",
                "description": "The slides in order.",
                "items": {"type": "object"},
            }
        },
    },
    layouts={"slide": {"slots": {"slides": {"pages": True}}}},
    parts={"slides": {"repeat": "slides", "draw": "tests/card", "width": "=:width", "column": {}}},
    preferred={"width": "=@size.figure", "height": "=@space.4"},
)

#: The head of each slide of the deck, in order, in each of its languages.
SLIDES = {
    "en": {"one": "Plan the work.", "two": "Build it."},
    "cs": {"one": "Naplánovat práci.", "two": "Postavit ji."},
}

#: The files a run of the deck makes as version 1, each with the page it holds: two pages,
#: in two languages and two colour schemes.
DECK_FILES = {
    f"flow.v1.{language}.{key}.{number}.svg": (language, key, f"deck/slides[{slide}]")
    for language in SLIDES
    for key in ("default", "colour-scheme.dark")
    for number, slide in ((1, "one"), (2, "two"))
}


def deck(tmp_path: Path, slides: Mapping[str, Mapping[str, str]] = SLIDES, **fields: Any) -> Path:
    """The piece `flow` as a deck of a page for each slide, two by default, ready to
    export: its top the local component `piece/deck`, in English and Czech, in both colour
    schemes; `fields` are the piece's own, such as its `exports`."""
    root = drawing_project(
        tmp_path, picture=False, top="piece/deck", languages=list(slides), **fields
    )
    write(root / PIECE_FOLDER / "components" / "deck.yaml", yaml_text(DECK))
    for language, heads in slides.items():
        items = [{"id": slide, "head": head} for slide, head in heads.items()]
        text = yaml_text(bound("content", slides=items))
        write(root / PIECE_FOLDER / f"content.{language}.yaml", text)
    return root


def drawn_as(path: Path) -> tuple[str, str, str]:
    """The language, the combination's key and the page an exported SVG file names."""
    svg = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    return svg.get("data-language", ""), svg.get("data-key", ""), svg.get("data-page", "")


def test_a_piece_of_several_pages_exports_each_page_under_one_number(tmp_path: Path) -> None:
    root = deck(tmp_path)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert exported(root) == sorted(DECK_FILES)
    assert [line for line in shown.stdout.splitlines() if line.startswith("export: ")] == [
        *(f"export: {FOLDER}/{name}" for name in DECK_FILES),
        f"export: version 1 recorded in {RECORD}",
    ]


def test_each_file_holds_its_page_the_pages_in_order(tmp_path: Path) -> None:
    root = deck(tmp_path)
    assert run(root, PIECE).returncode == 0
    assert {name: drawn_as(root / FOLDER / name) for name in DECK_FILES} == DECK_FILES


def test_the_record_names_the_file_of_each_page_with_its_hash(tmp_path: Path) -> None:
    root = deck(tmp_path)
    assert run(root, PIECE).returncode == 0
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert version["version"] == 1
    assert version["files"] == {
        name: reading.sha256((root / FOLDER / name).read_bytes()) for name in DECK_FILES
    }


def test_a_piece_with_no_page_in_one_language_is_refused_and_writes_nothing(
    tmp_path: Path,
) -> None:
    root = deck(tmp_path, {**SLIDES, "cs": {}})
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: `flow` has no page in `cs`, so the export would hold no file in that language\n"
    )
    assert not (root / CONFIG).exists()
    assert not (root / FOLDER).exists()
    assert not (root / RECORD).exists()


@pytest.mark.parametrize(
    ("page", "name"),
    [(None, "flow.v3.en.colour-scheme.dark.svg"), (2, "flow.v3.en.colour-scheme.dark.2.svg")],
    ids=["one-page", "several-pages"],
)
def test_a_file_name_adds_the_page_number_only_where_one_is_given(
    page: int | None, name: str
) -> None:
    assert exports.file_name("flow", 3, "en", "colour-scheme.dark", "svg", page) == name


#: Names of exported files as format 1 named them before a piece of several pages exported,
#: and still names the files of a piece of one page.
FORMAT_1_NAMES = [
    "flow.v1.en.default.svg",
    "flow.v12.en.colour-scheme.dark.svg",
    "flow.v1.cs.colour-scheme.dark+contrast.high.svg",
    "release-notes.v2.pt-br.default.svg",
]
#: Names of the files of a piece of several pages, each with its page's number.
PAGED_NAMES = ["flow.v1.en.default.1.svg", "flow.v1.en.colour-scheme.dark.12.svg"]


def record_naming(names: list[str]) -> dict[str, Any]:
    """The reference record of exports, its one version naming `names`."""
    record = reading.read_yaml(SCHEMAS / "exports.yaml")
    [version] = record["versions"]
    version["files"] = {name: "0" * 64 for name in names}
    return record


def test_every_name_format_1_accepted_still_holds_beside_names_with_a_page_number() -> None:
    assert files.shape_problems(record_naming(FORMAT_1_NAMES + PAGED_NAMES), "exports") == []


@pytest.mark.parametrize(
    "name",
    ["flow.v1.en.default.0.svg", "flow.v1.en.default.01.svg", "flow.v1.en.default.1.2.svg"],
)
def test_a_page_number_counts_from_1_and_comes_once(name: str) -> None:
    assert files.shape_problems(record_naming([name]), "exports") != []


# --- a piece exported as PDF --------------------------------------------------------------------

#: The heads of a deck of three slides, in two languages.
THREE = {
    "en": {"one": "Plan the work.", "two": "Build it.", "three": "Ship it."},
    "cs": {"one": "Naplánovat práci.", "two": "Postavit ji.", "three": "Vydat ji."},
}

#: The files a run of the deck of three slides makes as PDF, version 1: one for each
#: language and combination, each holding every page.
PDF_FILES = [
    f"flow.v1.{language}.{key}.pdf"
    for language in THREE
    for key in ("default", "colour-scheme.dark")
]


def heads(path: Path) -> list[list[str]]:
    """The text each page of an exported PDF shows, page by page."""
    file = read_pdf(path.read_bytes())
    return [file.lines(page) for page in file.pages()]


def test_a_deck_exported_as_pdf_makes_one_file_for_each_language_its_pages_in_order(
    tmp_path: Path,
) -> None:
    root = deck(tmp_path, THREE, exports=["pdf"])
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert [line for line in shown.stdout.splitlines() if line.startswith("export: ")] == [
        *(f"export: {FOLDER}/{name}" for name in PDF_FILES),
        f"export: version 1 recorded in {RECORD}",
    ]
    assert exported(root) == sorted(PDF_FILES)
    for name in PDF_FILES:
        language = name.split(".")[2]
        assert heads(root / FOLDER / name) == [[head] for head in THREE[language].values()]
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert version["files"] == {
        name: reading.sha256((root / FOLDER / name).read_bytes()) for name in PDF_FILES
    }
    assert version["recorded"]["renderers"] == {"pdf": "1.0.0"}


def test_a_pdf_draws_each_combination_in_its_own_colours(tmp_path: Path) -> None:
    root = deck(tmp_path, THREE, exports=["pdf"])
    assert run(root, PIECE).returncode == 0
    light, dark = (
        (root / FOLDER / f"flow.v1.en.{key}.pdf").read_bytes()
        for key in ("default", "colour-scheme.dark")
    )
    assert light != dark
    assert heads(root / FOLDER / "flow.v1.en.default.pdf") == heads(
        root / FOLDER / "flow.v1.en.colour-scheme.dark.pdf"
    )


def test_svg_and_pdf_are_exported_under_one_number(tmp_path: Path) -> None:
    root = deck(tmp_path, THREE, exports=["svg", "pdf"])
    assert run(root, PIECE).returncode == 0
    svgs = [
        f"flow.v1.{language}.{key}.{page}.svg"
        for language in THREE
        for key in ("default", "colour-scheme.dark")
        for page in (1, 2, 3)
    ]
    assert exported(root) == sorted([*svgs, *PDF_FILES])
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert version["recorded"]["renderers"] == {"pdf": "1.0.0", "svg": "1.0.1"}


def test_the_same_scene_gives_the_same_pdf_under_each_number(tmp_path: Path) -> None:
    root = deck(tmp_path, THREE, exports=["pdf"])
    assert run(root, PIECE).returncode == 0
    assert run(root, PIECE).returncode == 0
    for name in PDF_FILES:
        again = name.replace(".v1.", ".v2.")
        assert (root / FOLDER / name).read_bytes() == (root / FOLDER / again).read_bytes()
    first, second = reading.read_yaml(root / RECORD)["versions"]
    assert list(first["files"].values()) == list(second["files"].values())


def test_a_picture_the_pdf_renderer_refuses_leaves_the_rest_drawn(tmp_path: Path) -> None:
    root = ready(tmp_path, exports=["pdf"])
    assert run(root, PIECE).returncode == 0
    lines = heads(root / FOLDER / "flow.v1.en.default.pdf")
    assert lines and any("Plan the work." in text for text in lines[0])


#: Names of exported PDF files: one for each language and combination, of no page.
PDF_NAMES = ["flow.v1.en.default.pdf", "flow.v12.cs.colour-scheme.dark+contrast.high.pdf"]


def test_the_record_takes_a_pdfs_name_beside_every_name_format_1_accepted() -> None:
    names = FORMAT_1_NAMES + PAGED_NAMES + PDF_NAMES
    assert files.shape_problems(record_naming(names), "exports") == []


@pytest.mark.parametrize("name", ["flow.v1.en.default.1.pdf", "flow.v1.en.default.2.pdf"])
def test_a_pdf_names_no_page(name: str) -> None:
    assert files.shape_problems(record_naming([name]), "exports") != []


# --- what a failed export leaves ----------------------------------------------------------------


@pytest.mark.parametrize("file", ["flow.v2.en.colour-scheme.dark.svg", "exports.yaml"])
def test_a_write_that_fails_removes_the_files_of_the_run_and_keeps_the_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file: str
) -> None:
    root = ready(tmp_path)
    assert run(root, PIECE).returncode == 0
    record = (root / RECORD).read_bytes()
    with monkeypatch.context() as patch:
        failing(patch, write={file})
        shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stdout == ""
    folder = PIECE_FOLDER if file == "exports.yaml" else FOLDER
    assert shown.stderr == f"error: {folder}/{file} could not be written: {FULL}\n"
    assert exported(root) == ["flow.v1.en.colour-scheme.dark.svg", "flow.v1.en.default.svg"]
    assert (root / RECORD).read_bytes() == record


def test_a_failed_first_export_records_no_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = ready(tmp_path)
    with monkeypatch.context() as patch:
        failing(patch, write={"exports.yaml"})
        assert run(root, PIECE).returncode == 1
    assert not (root / CONFIG).exists()
    assert not (root / RECORD).exists()
    assert not (root / FOLDER).exists()


def test_a_file_a_failed_run_could_not_remove_is_named_and_refuses_no_later_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = ready(tmp_path)
    with monkeypatch.context() as patch:
        failing(patch, write={"exports.yaml"}, remove={"flow.v1.en.default.svg"})
        shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        f"error: {RECORD} could not be written: {FULL}; these could not be put back as they "
        f"were before the run: {FOLDER}/flow.v1.en.default.svg\n"
    )
    assert exported(root) == ["flow.v1.en.default.svg"]
    assert not (root / RECORD).exists()
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[-1] == f"export: version 2 recorded in {RECORD}"
    assert [entry["version"] for entry in reading.read_yaml(root / RECORD)["versions"]] == [2]


# --- a published piece's current copy -----------------------------------------------------------

#: The files of the skeleton piece's current copy.
COPIES = ["flow.en.colour-scheme.dark.svg", "flow.en.default.svg"]


def published(tmp_path: Path, **fields: Any) -> Path:
    """The skeleton piece, published, showing no produced picture, ready to export."""
    return drawing_project(tmp_path, state="published", picture=False, **fields)


def copied(root: Path, folder: str = COPY) -> list[str]:
    return sorted(path.name for path in (root / folder).iterdir())


def edit(root: Path, old: str, new: str) -> None:
    """Replace `old` in the piece's own file, which must hold it."""
    path = root / PIECE_FOLDER / "piece.yaml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def record_of(root: Path, folder: str = PIECE_FOLDER) -> dict[str, Any]:
    return reading.read_yaml(root / folder / "exports.yaml")


def test_a_published_pieces_export_writes_its_copy_and_the_record_says_who_wrote_it(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[1:] == [
        f"export: {FOLDER}/flow.v1.en.default.svg",
        f"export: {FOLDER}/flow.v1.en.colour-scheme.dark.svg",
        f"current copy: {COPY}/flow.en.default.svg",
        f"current copy: {COPY}/flow.en.colour-scheme.dark.svg",
        f"export: version 1 recorded in {RECORD}",
    ]
    assert copied(root) == COPIES
    record = record_of(root)
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert record["current-copy"] == {
        "piece": PIECE,
        "version": 1,
        "files": {
            f"current-copy/{name.replace('flow.v1.', 'flow.')}": digest
            for name, digest in version["files"].items()
        },
    }


def test_each_file_of_the_copy_holds_its_versions_bytes(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    for name in exported(root):
        copy = root / COPY / name.replace("flow.v1.", "flow.")
        assert copy.read_bytes() == (root / FOLDER / name).read_bytes()


def test_a_copy_takes_each_page_and_format_of_the_version(tmp_path: Path) -> None:
    root = deck(tmp_path, THREE, exports=["svg", "pdf"], state="published")
    assert run(root, PIECE).returncode == 0
    assert copied(root) == sorted(name.replace("flow.v1.", "flow.") for name in exported(root))
    assert "flow.en.default.2.svg" in copied(root)
    assert "flow.cs.colour-scheme.dark.pdf" in copied(root)


@pytest.mark.parametrize(("state", "code"), [("draft", 0), ("final", 1)])
def test_a_piece_in_any_other_state_writes_no_copy(tmp_path: Path, state: str, code: int) -> None:
    root = drawing_project(tmp_path, state=state, picture=False)
    assert run(root, PIECE).returncode == code
    assert not (root / COPY).exists()
    assert not (root / RECORD).exists() or "current-copy" not in record_of(root)


def test_a_render_writes_no_copy(tmp_path: Path) -> None:
    root = published(tmp_path)
    shown = run_main(render_script, PIECE, cwd=root)
    assert shown.returncode == 0, shown.stderr
    assert not (root / COPY).exists()
    assert not (root / RECORD).exists()


def test_a_later_export_replaces_the_copy_whole(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    left = root / COPY / "notes.txt"
    left.write_text("mine\n", encoding="utf-8")
    edit(root, "    - dark\n", "")
    assert run(root, PIECE).returncode == 0
    assert copied(root) == ["flow.en.default.svg"]
    current = record_of(root)["current-copy"]
    assert (current["version"], list(current["files"])) == (
        2,
        ["current-copy/flow.en.default.svg"],
    )
    assert exported(root) == [
        "flow.v1.en.colour-scheme.dark.svg",
        "flow.v1.en.default.svg",
        "flow.v2.en.default.svg",
    ]


def test_a_copy_and_its_record_stay_through_a_drafts_export(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    before = record_of(root)["current-copy"]
    held = {name: (root / COPY / name).read_bytes() for name in copied(root)}
    edit(root, "state: published", "state: draft")
    assert run(root, PIECE).returncode == 0
    record = record_of(root)
    assert files.shape_problems(record, "exports") == []
    assert record["current-copy"] == before
    assert [version["version"] for version in record["versions"]] == [1, 2]
    assert {name: (root / COPY / name).read_bytes() for name in copied(root)} == held


def test_no_fingerprint_reads_the_copy_and_the_findings_record_stays_valid(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert run_main(render_script, PIECE, cwd=root).returncode == 0
    assert run(root, PIECE).returncode == 0
    (root / COPY / "flow.en.default.svg").write_text("changed\n", encoding="utf-8")
    assert run(root, PIECE).returncode == 0
    first, second = record_of(root)["versions"]
    assert first["fingerprint"] == second["fingerprint"]
    piece = pl.read_piece(root, "visual", PIECE)
    assert checks.read_findings_record(root, pl.Held(root, "visual"), piece) is not None


# --- what stops a copy being written ------------------------------------------------------------


def test_a_file_where_the_copys_folder_goes_refuses_and_writes_nothing(tmp_path: Path) -> None:
    root = published(tmp_path)
    (root / COPY).write_text("mine\n", encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        f"error: {COPY} is a file, and the piece's current copy lies in a folder of that name: "
        f"move the file\n"
    )
    assert not (root / RECORD).exists()
    assert not (root / FOLDER).exists()
    assert not (root / CONFIG).exists()


def test_a_link_in_the_copys_place_refuses_and_writes_nothing(tmp_path: Path) -> None:
    root = published(tmp_path)
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    (root / COPY).symlink_to(elsewhere)
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert f"is reached through the link {COPY}" in shown.stderr
    assert list(elsewhere.iterdir()) == []
    assert not (root / RECORD).exists()


# --- the gate on a published piece's lock -------------------------------------------------------

#: What the export says of a lock that differs from that of the version that wrote its copy.
DIFFERS = (
    "error: the lock of visual/pieces/flow/piece.yaml differs from the lock of version 1, which "
    "wrote the piece's current copy: foundations@1.0.0, test-brand@1.0.0, tests@1.0.0. Run "
    "`pkit visual upgrade flow` to propose a move of the lock, or write that lock back, which "
    "is no move of it\n"
)


def exported_once(tmp_path: Path) -> Path:
    """A published piece exported once, and the `tests` library at 1.1.0 too."""
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    newer_tests(root, released=True)
    return root


def assert_refused_with_nothing_written(root: Path, shown: Any, said: str) -> None:
    assert shown.returncode == 1
    assert shown.stderr == said
    assert [version["version"] for version in record_of(root)["versions"]] == [1]
    assert not any(".v2." in name for name in exported(root))


def test_a_lock_written_by_hand_refuses_and_writing_it_back_lets_the_export_run(
    tmp_path: Path,
) -> None:
    root = exported_once(tmp_path)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    assert_refused_with_nothing_written(root, run(root, PIECE), DIFFERS)
    edit(root, "tests: 1.1.0", "tests: 1.0.0")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert record_of(root)["current-copy"]["version"] == 2


def test_a_state_changed_and_changed_back_brings_no_new_library_version(tmp_path: Path) -> None:
    root = exported_once(tmp_path)
    edit(root, "state: published", "state: draft")
    assert run_main(render_script, PIECE, cwd=root).returncode == 0
    assert reading.read_yaml(root / PIECE_FOLDER / "piece.yaml")["lock"]["tests"] == "1.1.0"
    assert run(root, PIECE).returncode == 0
    edit(root, "state: draft", "state: published")
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == DIFFERS
    assert record_of(root)["current-copy"]["version"] == 1


def test_the_gate_reads_the_record_so_removing_the_copy_changes_nothing(tmp_path: Path) -> None:
    root = exported_once(tmp_path)
    shutil.rmtree(root / COPY)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    assert_refused_with_nothing_written(root, run(root, PIECE), DIFFERS)
    assert not (root / COPY).exists()


def test_a_copy_removed_under_the_same_lock_is_written_again(tmp_path: Path) -> None:
    root = exported_once(tmp_path)
    shutil.rmtree(root / COPY)
    assert run(root, PIECE).returncode == 0
    assert copied(root) == COPIES


def test_the_gate_holds_a_published_piece_alone(tmp_path: Path) -> None:
    root = exported_once(tmp_path)
    edit(root, "state: published", "state: draft")
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr


def test_a_piece_with_no_copy_in_its_record_compares_nothing(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert run(root, PIECE).returncode == 0
    newer_tests(root, released=True)
    edit(root, "state: draft", "state: published")
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert record_of(root)["current-copy"]["version"] == 2


def test_a_folder_copied_by_hand_brings_no_copy_of_its_own_so_nothing_compares(
    tmp_path: Path,
) -> None:
    root = exported_once(tmp_path)
    hand = "visual/pieces/flow-two"
    shutil.copytree(root / PIECE_FOLDER, root / hand)
    path = root / hand / "piece.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("tests: 1.0.0", "tests: 1.1.0"), encoding="utf-8"
    )
    original = record_of(root)
    shown = run(root, "flow-two")
    assert shown.returncode == 0, shown.stderr
    assert copied(root, f"{hand}/current-copy") == [
        "flow-two.en.colour-scheme.dark.svg",
        "flow-two.en.default.svg",
    ]
    current = record_of(root, hand)["current-copy"]
    assert (current["piece"], current["version"]) == ("flow-two", 2)
    assert record_of(root) == original
    assert copied(root) == COPIES


def test_a_renamed_piece_keeps_its_copy_and_the_gate_still_holds_it(tmp_path: Path) -> None:
    root = exported_once(tmp_path)
    renamed = "visual/pieces/flow-renamed"
    os.rename(root / PIECE_FOLDER, root / renamed)
    written = record_of(root, renamed)["current-copy"]["files"]
    assert all((root / renamed / path).is_file() for path in written)
    path = root / renamed / "piece.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("tests: 1.0.0", "tests: 1.1.0"), encoding="utf-8")
    shown = run(root, "flow-renamed")
    assert shown.returncode == 1
    assert shown.stderr == DIFFERS.replace("pieces/flow/", "pieces/flow-renamed/").replace(
        "upgrade flow", "upgrade flow-renamed"
    )
    path.write_text(text, encoding="utf-8")
    shown = run(root, "flow-renamed")
    assert shown.returncode == 0, shown.stderr
    assert record_of(root, renamed)["current-copy"]["piece"] == "flow-renamed"
    assert copied(root, f"{renamed}/current-copy") == [
        "flow-renamed.en.colour-scheme.dark.svg",
        "flow-renamed.en.default.svg",
    ]


def sealed(fingerprint_kept: dict[str, Any], library: str, version: str) -> None:
    """Make the first library's input of a kept fingerprint name `library` at `version`,
    its value taken again, so its own inputs still match."""
    entry = next(item for item in fingerprint_kept["inputs"] if "library" in item)
    entry.update(library=library, version=version)
    fingerprint_kept["value"] = reading.sha256(
        fingerprint.canonical_bytes(fingerprint_kept["inputs"])
    )


def edited_value(record: dict[str, Any]) -> None:
    record["versions"][0]["fingerprint"]["value"] = "0" * 64


def no_fingerprint(record: dict[str, Any]) -> None:
    del record["versions"][0]["fingerprint"]


def no_such_version(record: dict[str, Any]) -> None:
    record["current-copy"]["version"] = 7


def a_library_outside_the_folder(record: dict[str, Any]) -> None:
    sealed(record["versions"][0]["fingerprint"], "../../outside", "1.0.0")


def a_version_outside_the_folder(record: dict[str, Any]) -> None:
    sealed(record["versions"][0]["fingerprint"], "tests", "../../outside")


def a_form_of_no_number(record: dict[str, Any]) -> None:
    record["versions"][0]["fingerprint"]["form"] = [1]


def a_number_past_json(record: dict[str, Any]) -> None:
    record["versions"][0]["fingerprint"]["inputs"][0]["size"] = 2**60


@pytest.mark.parametrize(
    ("spoil", "said"),
    [
        pytest.param(edited_value, "it was edited", id="edited"),
        pytest.param(a_form_of_no_number, "form [1]", id="a-list-form"),
        pytest.param(a_number_past_json, "inputs cannot be read", id="a-number-past-json"),
        pytest.param(no_fingerprint, "no fingerprint is kept", id="none-kept"),
        pytest.param(no_such_version, "no fingerprint is kept", id="no-such-version"),
        pytest.param(a_library_outside_the_folder, "../../outside", id="no-library"),
        pytest.param(a_version_outside_the_folder, "../../outside", id="no-version"),
    ],
)
def test_a_fingerprint_the_gate_cannot_read_refuses_and_names_the_record(
    tmp_path: Path, spoil: Callable[[dict[str, Any]], None], said: str
) -> None:
    root = exported_once(tmp_path)
    record = record_of(root)
    spoil(record)
    (root / RECORD).write_text(yaml_text(record), encoding="utf-8")
    number = record["current-copy"]["version"]
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr.startswith(
        f"error: {RECORD} gives no lock of version {number}, which wrote the piece's current copy: "
    )
    assert said in shown.stderr
    assert shown.stderr.endswith("Mend it before the next export\n")
    assert not any(".v2." in name for name in exported(root))


@pytest.mark.parametrize("state", ["draft", "published"])
@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(None, id="nothing"),
        pytest.param({"piece": "../outside", "version": 1, "files": {}}, id="a-path-for-a-piece"),
        pytest.param({"piece": PIECE, "version": 1}, id="no-files"),
        pytest.param({"piece": PIECE, "version": 1, "files": {}}, id="no-file"),
        pytest.param(
            {"piece": PIECE, "version": 1, "files": {"current-copy/flow.en.default.svg": "0" * 64}}
            | {"written": "2026"},
            id="another-field",
        ),
    ],
)
def test_a_current_copy_of_no_shape_refuses_in_every_state_and_names_the_record(
    tmp_path: Path, state: str, entry: Any
) -> None:
    root = exported_once(tmp_path)
    edit(root, "state: published", f"state: {state}")
    record = record_of(root)
    record["current-copy"] = entry
    (root / RECORD).write_text(yaml_text(record), encoding="utf-8")
    held = (root / RECORD).read_bytes()
    assert_refused_with_nothing_written(
        root,
        run(root, PIECE),
        f"error: {RECORD} keeps a `current-copy` that names no piece, version and files as its "
        f"schema asks: mend it before the next export\n",
    )
    assert (root / RECORD).read_bytes() == held


def test_the_gate_lies_outside_what_a_proposed_move_of_the_lock_shares(tmp_path: Path) -> None:
    root = exported_once(tmp_path)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    exports.write(exports.plan(project), files.Change(root))
    current = record_of(root)["current-copy"]
    assert current["version"] == 2
    assert run(root, PIECE).returncode == 0


# --- what a failed export of a published piece leaves -------------------------------------------


def test_a_first_copy_that_cannot_be_written_leaves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = published(tmp_path)
    with monkeypatch.context() as patch:
        failing(patch, write={"current-copy"})
        shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == f"error: {COPY} could not be written: {FULL}\n"
    assert not (root / COPY).exists()
    assert not (root / RECORD).exists()
    assert not (root / FOLDER).exists()
    assert not (root / CONFIG).exists()


def test_a_failed_export_puts_the_copy_back_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    record = (root / RECORD).read_bytes()
    held = {name: (root / COPY / name).read_bytes() for name in copied(root)}
    edit(root, "    - dark\n", "")
    with monkeypatch.context() as patch:
        failing(patch, write={"exports.yaml"})
        shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == f"error: {RECORD} could not be written: {FULL}\n"
    assert {name: (root / COPY / name).read_bytes() for name in copied(root)} == held
    assert (root / RECORD).read_bytes() == record
    assert not any(".v2." in name for name in exported(root))
    assert not list((root / PIECE_FOLDER).glob(".*"))


def test_a_failed_export_names_each_file_it_could_not_put_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    with monkeypatch.context() as patch:
        failing(patch, write={"exports.yaml"}, remove={"flow.v2.en.default.svg"})
        shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        f"error: {RECORD} could not be written: {FULL}; these could not be put back as they "
        f"were before the run: {FOLDER}/flow.v2.en.default.svg\n"
    )
