"""`pkit visual export <piece>` (visual-communication DEC-006 point 7): numbered exports in
the clone's local folder, never overwriting another; their record, `exports.yaml`; no stale
or missing produced picture, unless the person names a stale one; a piece of several
pages, one file for each page under one number; a piece exported as PDF, one file for each
language and combination holding its pages in order; and what a write that fails
leaves."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator, Mapping
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
    write_picture,
)
from tests.visual_communication_project import CONFIG, SCHEMAS, bound, importable, write, yaml_text
from tests.visual_communication_writes import FULL, failing

script, exports, svg, pdf, seam, framing, files, reading, fingerprint, pl = load(
    "visual-communication",
    "export.py",
    "exports",
    "plugins.svg",
    "plugins.pdf",
    "plugins.seam",
    "framing",
    "files",
    "reading",
    "fingerprint",
    "pipeline",
)

FOLDER = ".pkit/capabilities/visual-communication/project/local/exports/flow"
RECORD = f"{PIECE_FOLDER}/exports.yaml"


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


def test_a_record_that_cannot_be_read_stops_the_next_export(tmp_path: Path) -> None:
    root = ready(tmp_path)
    (root / RECORD).write_text("pkit_schema: visual-communication:exports\n[", encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert "mend it before the next export" in shown.stderr


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
