"""`pkit visual export <piece>` (visual-communication DEC-006 point 7): numbered exports in
the clone's local folder, never overwriting another; their record, `exports.yaml`; no stale
or missing produced picture, unless the person names a stale one; a piece of several
pages, one file for each page under one number; a piece exported as PDF, one file for each
language and combination holding its pages in order; a piece exported as HTML, one page file
for each language and set of combinations that share one (DEC-023 point 1); a piece exported
as switching files, one for each page, language and set of combinations that share one, each
held to the one-key file of each combination it holds (DEC-018 points 1 to 4); what a write
that fails leaves; and a published piece's current copy, in its folder or at a place, with
the gate on its lock (DEC-017 points 5, 7 and 8)."""

from __future__ import annotations

import dataclasses
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_pdf import read as read_pdf
from tests.test_visual_communication_pipeline import (
    LOCK,
    PHONE,
    PHONE_GROUND,
    PIECE,
    PIECE_FOLDER,
    TESTS,
    add_device,
    drawing_project,
    every_file,
    exported_up_to,
    hex_of,
    list_drawing_libraries,
    on_devices,
    page_values,
    stamped,
    two_steps,
    write_content,
    write_picture,
)
from tests.test_visual_communication_render import newer_tests
from tests.visual_communication_project import (
    CONFIG,
    SCHEMAS,
    bound,
    importable,
    write,
    write_piece,
    yaml_text,
)
from tests.visual_communication_writes import FULL, failing

(
    script,
    render_script,
    exports,
    svg,
    pdf,
    html,
    html_declaration,
    seam,
    framing,
    files,
    reading,
    fingerprint,
    pl,
    checks,
    text,
) = load(
    "visual-communication",
    "export.py",
    "render.py",
    "exports",
    "plugins.svg",
    "plugins.pdf",
    "plugins.html",
    "plugins.html_declaration",
    "plugins.seam",
    "framing",
    "files",
    "reading",
    "fingerprint",
    "pipeline",
    "checks",
    "text",
)

FOLDER = ".pkit/capabilities/visual-communication/project/local/exports/flow"
RECORD = f"{PIECE_FOLDER}/exports.yaml"
COPY = f"{PIECE_FOLDER}/current-copy"
PREVIEWS = ".pkit/capabilities/visual-communication/project/local/previews/flow"
TEXT = "{http://www.w3.org/2000/svg}text"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderers stand in for the import a run makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg, pdf, html)
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
        {"svg": "1.1.0"},
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


def test_a_piece_on_a_size_axis_exports_a_file_for_each_key_from_its_size_s_scene(
    tmp_path: Path,
) -> None:
    dark = "colour-scheme.dark"
    modes = {"colour-scheme": ["light", "dark"], "device": ["desktop", "phone"]}
    root = on_devices(tmp_path, modes=modes, exports=["svg", "pdf"])
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    keys = ["default", dark, PHONE, f"{dark}+{PHONE}"]
    assert exported(root) == sorted(
        f"flow.v1.en.{key}.{form}" for key in keys for form in ("svg", "pdf")
    )
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert sorted(version["files"]) == exported(root)
    drawn = {key: (root / FOLDER / f"flow.v1.en.{key}.svg").read_text("utf-8") for key in keys}
    for key, text in drawn.items():
        assert f'data-key="{key}"' in text
        assert ('width="480"' in text) == key.endswith(PHONE)


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
    project.scenes(facts=project.piece.stand_ins)
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
        "error: the piece `flow` is final (its state says so), and a final piece takes no export: "
        "run `pkit visual take-up flow <name>` to take it up again as a new draft\n"
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
            "`svg`, `svg-modes`, `pdf` or `html` there",
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


# --- the facts an export fills -----------------------------------------------------------------

#: A component of the piece's own that shows a version's number and its date, each in the
#: width the component is given.
FACTS = """\
pkit_schema: visual-communication:component
schema_version: 1

status: experimental
about: A version's number and its date.

parts:
  number:
    text: {fact: version, style: type.body, fill: text-primary}
    width: "=:width"
  date:
    text: {fact: date, style: type.body, fill: text-primary}
    y: "=number.bottom"
    width: "=:width"

preferred:
  height: "=@space.4 * 2"
"""

#: A component that shows a version's number in a width the stand-in fits, and a number of
#: ten digits does not.
NUMBER = """\
pkit_schema: visual-communication:component
schema_version: 1

status: experimental
about: A version's number, in a width for a number of a few digits.

parts:
  number:
    text: {fact: version, style: type.body, fill: text-primary}
    width: "=@space.3 * 3"

preferred:
  height: "=@space.4 * 2"
"""

#: A component that asks for the width its number takes, and one that places it in a width
#: the stand-in fits, so a number of ten digits leaves it less than it asks for.
BOXED = """\
pkit_schema: visual-communication:component
schema_version: 1

status: experimental
about: A version's number, as wide as it takes.

parts:
  number:
    text: {fact: version, style: type.body, fill: text-primary}

preferred:
  width: "=number.width"
  height: "=@space.4"
"""
HOLDER = """\
pkit_schema: visual-communication:component
schema_version: 1

status: experimental
about: A version's number, boxed in a width for a number of a few digits.

parts:
  box:
    use: piece/boxed
    width: "=@space.3 * 3"

preferred:
  height: "=@space.4 * 2"
"""

#: A component that shows each fact of its export in a width none of them fits.
NARROW = """\
pkit_schema: visual-communication:component
schema_version: 1

status: experimental
about: Each fact of the export, too narrow for any.

parts:
  language:
    text: {fact: language, style: type.body, fill: text-primary}
    width: "=@space.1"
  state:
    text: {fact: state, style: type.body, fill: text-primary}
    y: "=language.bottom"
    width: "=@space.1"
  number:
    text: {fact: version, style: type.body, fill: text-primary}
    y: "=state.bottom"
    width: "=@space.1"
  date:
    text: {fact: date, style: type.body, fill: text-primary}
    y: "=number.bottom"
    width: "=@space.1"

preferred:
  height: "=@space.4 * 2"
"""

#: Where the piece's own components lie.
OWN = f"{PIECE_FOLDER}/components"

#: The number a piece takes once `exported_up_to` names 1 000 000 000, too wide for `NUMBER`.
LONG = "v1000000001"

#: How an export says the way past a number or a date that overflows.
WAY_PAST = (
    "Give each room in its component, or name its fact with `--use-overflowing <fact>` to "
    "export its text as it is"
)


def showing(tmp_path: Path, component: str, *more: str, **fields: Any) -> Path:
    """The drawing project without its picture, its body the piece's own component
    `component`, each of `more` beside it, read from this module's text of that name."""
    root = drawing_project(tmp_path, picture=False, **fields)
    for name in (component, *more):
        write(root / OWN / f"{name}.yaml", globals()[name.upper()])
    write_content(root, body={"use": f"piece/{component}"})
    return root


def texts(path: Path) -> list[str]:
    """Each text an exported SVG file shows, in order, but the figure's head, which follows
    the body."""
    drawn = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    return ["".join(text.itertext()) for text in drawn.iter(TEXT)][:-1]


def refused(root: Path, *args: str) -> str:
    """What a refused run says on standard error, having written nothing: no export, no
    record and no location."""
    before = every_file(root)
    shown = run(root, PIECE, *args)
    assert shown.returncode == 1, shown.stdout
    assert shown.stdout == ""
    assert every_file(root) == before
    return shown.stderr


def test_every_file_of_a_version_shows_the_one_number_and_date_its_record_keeps(
    tmp_path: Path,
) -> None:
    root = showing(tmp_path, "facts", languages=["en", "cs"])
    write_content(root, "cs", body={"use": "piece/facts"})
    exported_up_to(root, 41)
    done = run(root, PIECE)
    assert done.returncode == 0, done.stderr
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert version["version"] == 42
    date = version["recorded"]["time"][: len("YYYY-MM-DD")]
    assert sorted(version["files"]) == [
        "flow.v42.cs.colour-scheme.dark.svg",
        "flow.v42.cs.default.svg",
        "flow.v42.en.colour-scheme.dark.svg",
        "flow.v42.en.default.svg",
    ]
    for name in version["files"]:
        assert texts(root / FOLDER / name) == ["v42", date]
    assert "let-through" not in version["recorded"]


@pytest.mark.parametrize(("shows", "fact"), [("number", "version"), ("date", "date")])
def test_a_piece_that_shows_a_number_or_a_date_exports_it_no_longer_refused(
    tmp_path: Path, shows: str, fact: str
) -> None:
    root = stamped(tmp_path, shows)
    done = run(root, PIECE)
    assert done.returncode == 0, done.stderr
    [version] = reading.read_yaml(root / RECORD)["versions"]
    shown = "v1" if fact == "version" else version["recorded"]["time"][: len("YYYY-MM-DD")]
    assert texts(root / FOLDER / "flow.v1.en.default.svg") == [shown]


def test_a_new_number_makes_nothing_stale(tmp_path: Path) -> None:
    """The fingerprint reads none of the facts an export fills (DEC-016 point 5)."""
    root = stamped(tmp_path, "number", state="published")
    assert run(root, PIECE).returncode == 0
    exported_up_to(root, 41)
    owed = [f.code for f, _ in checks.check(root, only=PIECE).judged if "copy" in f.code]
    assert owed == []
    assert run(root, PIECE).returncode == 0
    first, second = record_of(root)["versions"]
    assert (first["version"], second["version"]) == (1, 42)
    assert first["fingerprint"] == second["fingerprint"]
    assert texts(root / COPY / "flow.en.default.svg") == ["v42"]
    assert [f.code for f, level in checks.check(root, only=PIECE).judged if level == "fails"] == []


def test_a_number_that_overflows_stops_the_export_before_any_write(tmp_path: Path) -> None:
    """The stand-in fits, so the check finds nothing, and the export stops on the real text
    alone (DEC-016 point 6)."""
    root = showing(tmp_path, "number")
    exported_up_to(root, 1_000_000_000)
    assert "text-overflow" not in {f.code for f, _ in checks.check(root, only=PIECE).judged}
    said = refused(root)
    assert said == (
        f"error: a number or a date the export fills does not fit: `version` as `{LONG}` at "
        f"`figure/body/number` in `piece/number`, which overflows its width. {WAY_PAST}\n"
    )


def test_a_component_around_a_number_that_gets_less_than_it_asks_for_stops_the_export(
    tmp_path: Path,
) -> None:
    root = showing(tmp_path, "holder", "boxed")
    exported_up_to(root, 1_000_000_000)
    said = refused(root)
    assert said == (
        f"error: a number or a date the export fills does not fit: `version` as `{LONG}` at "
        f"`figure/body/box` in `piece/boxed`, which gets less than it asks for. {WAY_PAST}\n"
    )


@pytest.mark.parametrize(
    ("use", "state"),
    [
        pytest.param("piece/stamp", "draft", id="own"),
        pytest.param("tests/stamp", "draft", id="corrected-by-the-project"),
        pytest.param("tests/stamp", "published", id="released"),
    ],
)
def test_a_number_that_overflows_with_its_stand_in_too_stops_in_any_library(
    tmp_path: Path, use: str, state: str
) -> None:
    root = drawing_project(tmp_path, picture=False, state=state)
    write(root / OWN / "stamp.yaml", (TESTS / "components" / "stamp.yaml").read_text("utf-8"))
    write_content(root, body={"use": use, "shows": "narrow"})
    said = refused(root)
    assert said.startswith(
        "error: a number or a date the export fills does not fit: `version` as `v1` at "
        f"`figure/body/narrow` in `{use}`, which overflows its width. "
    )


def test_a_fact_named_lets_its_text_through_and_the_record_keeps_it(tmp_path: Path) -> None:
    root = showing(tmp_path, "number")
    exported_up_to(root, 1_000_000_000)
    done = run(root, PIECE, "--use-overflowing", "version")
    assert done.returncode == 0, done.stderr
    assert (
        f"let through: `version` as `{LONG}` at `figure/body/number` in `piece/number`, which "
        f"overflows its width"
    ) in done.stdout.splitlines()
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert version["recorded"]["let-through"] == [
        {
            "fact": "version",
            "text": LONG,
            "element": "figure/body/number",
            "component": "piece/number",
        }
    ]
    assert texts(root / FOLDER / f"flow.{LONG}.en.default.svg") == [LONG]


def test_a_text_let_through_in_a_library_names_the_version_of_its_component(
    tmp_path: Path,
) -> None:
    root = stamped(tmp_path, "narrow")
    assert run(root, PIECE, "--use-overflowing", "version").returncode == 0
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert version["recorded"]["let-through"] == [
        {
            "fact": "version",
            "text": "v1",
            "element": "figure/body/narrow",
            "component": "tests/stamp",
            "version": "1.0.0",
        }
    ]


def test_a_fact_nobody_named_still_stops(tmp_path: Path) -> None:
    root = showing(tmp_path, "narrow")
    said = refused(root, "--use-overflowing", "version")
    assert said.startswith("error: a number or a date the export fills does not fit: `date` as `")
    assert "`version`" not in said
    assert said.endswith(f"in `piece/narrow`, which overflows its width. {WAY_PAST}\n")


def test_the_language_and_the_state_stop_nothing_here(tmp_path: Path) -> None:
    """The check measures them as they stand, so the export leaves them to it, and naming
    either is refused (DEC-016 point 6)."""
    root = showing(tmp_path, "narrow")
    done = run(root, PIECE, "--use-overflowing", "version", "--use-overflowing", "date")
    assert done.returncode == 0, done.stderr
    let = [line for line in done.stdout.splitlines() if line.startswith("let through: ")]
    assert [line.split("`")[1] for line in let] == ["date", "version"]
    found = {f.code: f.where for f, _ in checks.check(root, only=PIECE).judged}
    assert found["text-overflow"]
    for word in ("language", "state"):
        said = run(root, PIECE, "--use-overflowing", word)
        assert said.returncode == 1
        assert said.stderr == (
            f"error: `--use-overflowing {word}` names no fact an export fills, which are "
            "`version` and `date`: the check measures the language and the state as they stand\n"
        )


def test_a_fact_named_that_does_not_overflow_is_used_as_it_is_and_said(tmp_path: Path) -> None:
    root = showing(tmp_path, "number")
    done = run(root, PIECE, "--use-overflowing", "date")
    assert done.returncode == 0, done.stderr
    assert "not overflowing, so used as it is: date" in done.stdout.splitlines()
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert "let-through" not in version["recorded"]


def test_an_overflow_measured_by_an_estimate_stops_nothing_and_the_run_says_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check only asks attention for it, so the export stops nothing on it (DEC-005
    point 14, DEC-016 point 6)."""
    of_role = text.Style.of_role.__func__

    def estimated(cls: Any, *given: Any) -> Any:
        return dataclasses.replace(of_role(cls, *given), measured="table")

    monkeypatch.setattr(text.Style, "of_role", classmethod(estimated))
    root = showing(tmp_path, "number")
    exported_up_to(root, 1_000_000_000)
    done = run(root, PIECE)
    assert done.returncode == 0, done.stderr
    assert (
        "stops nothing, measured otherwise than from a font file, from a table or by an "
        f"estimate: `version` as `{LONG}` at `figure/body/number` in `piece/number`, which "
        "overflows its width"
    ) in done.stdout.splitlines()
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert "let-through" not in version["recorded"]


def test_every_run_through_the_plan_measures_each_overflow_once(tmp_path: Path) -> None:
    root = stamped(tmp_path, "narrow", languages=["en", "cs"])
    write_content(root, "cs", body={"use": "tests/stamp", "shows": "narrow"})
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    with pytest.raises(pl.Refused) as refused:
        exports.plan(project)
    assert str(refused.value).count("`version` as `v1` at `figure/body/narrow`") == 1
    planned = exports.plan(project, use_overflowing=["version"])
    assert [overflow.element for overflow in planned.let_through] == ["figure/body/narrow"]


def test_a_run_that_proposes_a_move_says_its_own_way_past_an_overflow(tmp_path: Path) -> None:
    root = stamped(tmp_path, "narrow")
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    with pytest.raises(pl.Refused) as caught:
        exports.plan(project, way_past_overflow=lambda facts: f"Name {sorted(facts)}")
    assert str(caught.value).endswith(", which overflows its width. Name ['version']")


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
    assert version["recorded"]["renderers"] == {"pdf": "1.2.0"}


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
    assert version["recorded"]["renderers"] == {"pdf": "1.2.0", "svg": "1.1.0"}


def test_the_same_scene_gives_the_same_pdf_under_each_number(tmp_path: Path) -> None:
    root = deck(tmp_path, THREE, exports=["pdf"])
    assert run(root, PIECE).returncode == 0
    assert run(root, PIECE).returncode == 0
    for name in PDF_FILES:
        again = name.replace(".v1.", ".v2.")
        assert (root / FOLDER / name).read_bytes() == (root / FOLDER / again).read_bytes()
    first, second = reading.read_yaml(root / RECORD)["versions"]
    assert list(first["files"].values()) == list(second["files"].values())


def drawn_pictures(path: Path) -> list[tuple[bytes, bytes | None]]:
    """What each picture an exported PDF draws holds, page by page, in the order drawn: its
    image's data, and its soft mask's, where it has one."""
    file = read_pdf(path.read_bytes())
    drawn = []
    for page in file.pages():
        images = file.images(page)
        for name in re.findall(r"/(I\d+) Do", file.content(page)):
            mask = re.search(r"/SMask (\d+) 0 R", file.value(images[name]))
            drawn.append((file.stream(images[name]), file.stream(int(mask[1])) if mask else None))
    return drawn


def test_a_pdf_draws_the_produced_picture_from_the_variant_that_serves_each_combination(
    tmp_path: Path,
) -> None:
    """Each variant a PNG of 100 by 100 pixels of one colour, the dark one translucent: its
    colours and its alpha apart, the alpha a soft mask, beside the text drawn as before."""
    root = ready(tmp_path, exports=["pdf"])
    colours = {"default": (200, 30, 30, 255), "colour-scheme.dark": (30, 60, 200, 128)}
    write_picture(root, framing, by_variant=colours)

    shown = run(root, PIECE)

    assert shown.returncode == 0, shown.stderr
    for key, (red, green, blue, alpha) in colours.items():
        path = root / FOLDER / f"flow.v1.en.{key}.pdf"
        pixels = 100 * 100
        assert drawn_pictures(path) == [
            (bytes([red, green, blue]) * pixels, bytes([alpha]) * pixels)
        ]
        lines = heads(path)
        assert lines and any("Plan the work." in text for text in lines[0])


#: Names of exported PDF files: one for each language and combination, of no page.
PDF_NAMES = ["flow.v1.en.default.pdf", "flow.v12.cs.colour-scheme.dark+contrast.high.pdf"]


def test_the_record_takes_a_pdfs_name_beside_every_name_format_1_accepted() -> None:
    names = FORMAT_1_NAMES + PAGED_NAMES + PDF_NAMES
    assert files.shape_problems(record_naming(names), "exports") == []


@pytest.mark.parametrize("name", ["flow.v1.en.default.1.pdf", "flow.v1.en.default.2.pdf"])
def test_a_pdf_names_no_page(name: str) -> None:
    assert files.shape_problems(record_naming([name]), "exports") != []


# --- a piece exported as HTML (DEC-020 point 4, DEC-023 points 1 and 3) -------------------------

#: The page files a run of the deck of three slides makes as HTML, version 1: one for each
#: language, which holds both colour schemes under its first key.
HTML_FILES = [f"flow.v1.{language}.default.html" for language in THREE]

DARK = "colour-scheme.dark"


def page_file(path: Path) -> tuple[str, str, list[str], list[str]]:
    """What an exported page file names: its language, its key, the trace id of each page it
    holds, in order, and the signals each rule of its root lies under, the plain rule's
    empty."""
    drawn = path.read_text(encoding="utf-8")
    head = re.search(r"<html ([^>]*)>", drawn)
    assert head is not None
    named = dict(re.findall(r'([a-z-]+)="([^"]*)"', head.group(1)))
    pages = re.findall(r'<div data-page="([^"]+)"', drawn)
    rules = [media for media, _ in page_values(path.read_bytes())]
    return named["lang"], named["data-key"], pages, rules


def test_a_deck_exported_as_html_makes_one_page_file_for_each_language_its_modes_in_it(
    tmp_path: Path,
) -> None:
    root = deck(tmp_path, THREE, exports=["html"])
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert [line for line in shown.stdout.splitlines() if line.startswith("export: ")] == [
        *(f"export: {FOLDER}/{name}" for name in HTML_FILES),
        f"export: version 1 recorded in {RECORD}",
    ]
    assert exported(root) == sorted(HTML_FILES)
    for name in HTML_FILES:
        language = name.split(".")[2]
        pages = [f"deck/slides[{slide}]" for slide in THREE[language]]
        assert page_file(root / FOLDER / name) == (
            language,
            "default",
            pages,
            ["", "(prefers-color-scheme:dark)"],
        )
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert version["files"] == {
        name: reading.sha256((root / FOLDER / name).read_bytes()) for name in HTML_FILES
    }
    assert version["recorded"]["renderers"] == {"html": html.VERSION}


def test_html_and_pdf_are_exported_under_one_number(tmp_path: Path) -> None:
    root = deck(tmp_path, THREE, exports=["pdf", "html"])
    assert run(root, PIECE).returncode == 0
    assert exported(root) == sorted([*PDF_FILES, *HTML_FILES])
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert sorted(version["files"]) == exported(root)
    assert version["recorded"]["renderers"] == {"html": html.VERSION, "pdf": "1.2.0"}


@pytest.mark.parametrize(
    ("modes", "key"),
    [(["light", "dark"], "default"), (["dark"], DARK)],
    ids=["light-and-dark", "dark-alone"],
)
def test_a_page_file_takes_the_first_key_it_serves(
    tmp_path: Path, modes: list[str], key: str
) -> None:
    root = drawing_project(
        tmp_path, picture=False, modes={"colour-scheme": modes}, exports=["html"]
    )
    assert run(root, PIECE).returncode == 0
    assert exported(root) == [f"flow.v1.en.{key}.html"]
    assert page_file(root / FOLDER / f"flow.v1.en.{key}.html")[1] == key
    assert files.shape_problems(reading.read_yaml(root / RECORD), "exports") == []


def test_each_key_over_a_size_axis_takes_a_page_file_of_its_own_at_its_sizes_values(
    tmp_path: Path,
) -> None:
    root = drawing_project(
        tmp_path,
        picture=False,
        modes={"colour-scheme": ["light", "dark"], "device": ["desktop", "phone"]},
        exports=["html"],
    )
    add_device(root, PHONE_GROUND)
    assert run(root, PIECE).returncode == 0
    names = ["flow.v1.en.default.html", f"flow.v1.en.{PHONE}.html"]
    assert exported(root) == names
    desktop, phone = (root / FOLDER / name for name in names)
    assert [page_file(path)[1:] for path in (desktop, phone)] == [
        ("default", ["figure"], ["", "(prefers-color-scheme:dark)"]),
        (PHONE, ["figure"], ["", "(prefers-color-scheme:dark)"]),
    ]
    widths = [
        re.findall(r"width:min\(100%,([0-9.]+)px\)", path.read_text(encoding="utf-8"))
        for path in (desktop, phone)
    ]
    assert widths == [["960"], ["480"]]
    black = "#000000"
    assert [held["--background"] for _, held in page_values(phone.read_bytes())] == [black] * 2
    assert black not in {held["--background"] for _, held in page_values(desktop.read_bytes())}
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert sorted(version["files"]) == names


def test_a_piece_on_no_size_axis_takes_one_page_file_for_each_language_whatever_its_modes(
    tmp_path: Path,
) -> None:
    root = drawing_project(
        tmp_path,
        picture=False,
        languages=["en", "cs"],
        modes={"colour-scheme": ["light", "dark"], "contrast": ["standard", "high"]},
        exports=["html"],
    )
    write_content(root, "cs", body=two_steps("Naplánovat."))
    assert run(root, PIECE).returncode == 0
    assert exported(root) == ["flow.v1.cs.default.html", "flow.v1.en.default.html"]
    for language in ("en", "cs"):
        assert page_file(root / FOLDER / f"flow.v1.{language}.default.html") == (
            language,
            "default",
            ["figure"],
            [
                "",
                "(prefers-color-scheme:dark)",
                "(prefers-contrast:more)",
                "(prefers-color-scheme:dark) and (prefers-contrast:more)",
            ],
        )


def test_a_mode_no_signal_names_takes_a_page_file_of_its_own_under_the_first_key_it_serves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every mode the foundations ship has a pair, so a pair left out stands for one."""
    monkeypatch.setitem(
        html_declaration.HOLDS_MODES["html"]["colour-scheme"], "pairs", {"light": "light"}
    )
    root = drawing_project(
        tmp_path,
        picture=False,
        modes={"colour-scheme": ["light", "dark"], "contrast": ["standard", "high"]},
        exports=["html"],
    )
    assert run(root, PIECE).returncode == 0
    names = ["flow.v1.en.default.html", f"flow.v1.en.{DARK}.html"]
    assert exported(root) == sorted(names)
    light, dark = (root / FOLDER / name for name in names)
    assert [page_file(path)[1:] for path in (light, dark)] == [
        ("default", ["figure"], ["", "(prefers-contrast:more)"]),
        (DARK, ["figure"], ["", "(prefers-contrast:more)"]),
    ]
    assert "prefers-color-scheme" not in dark.read_text(encoding="utf-8")
    document = pl.Project(
        pl.read_piece(root, "visual", PIECE), LOCK, pl.Held(root, "visual")
    ).values()
    [(_, plain), _] = page_values(dark.read_bytes())
    assert plain["--background"] == hex_of(pl.colours_at(document, DARK)["background"])
    assert files.shape_problems(reading.read_yaml(root / RECORD), "exports") == []


#: Names of exported page files: one for each language and set of combinations, of no page.
HTML_NAMES = [
    "flow.v1.en.default.html",
    "flow.v12.cs.colour-scheme.dark.html",
    f"flow.v1.en.{PHONE}.html",
]


def test_the_record_takes_a_page_files_name_beside_every_name_format_1_accepted() -> None:
    names = FORMAT_1_NAMES + PAGED_NAMES + PDF_NAMES + HTML_NAMES
    assert files.shape_problems(record_naming(names), "exports") == []


@pytest.mark.parametrize("name", ["flow.v1.en.default.1.html", "flow.v1.en.default.htm"])
def test_a_page_file_names_no_page(name: str) -> None:
    assert files.shape_problems(record_naming([name]), "exports") != []


def no_page_in_czech(tmp_path: Path, form: str) -> Path:
    return deck(tmp_path, {**SLIDES, "cs": {}}, exports=[form])


def a_stale_picture(tmp_path: Path, form: str) -> Path:
    root = ready(tmp_path, exports=[form])
    make_stale(root)
    return root


def a_number_that_does_not_fit(tmp_path: Path, form: str) -> Path:
    root = showing(tmp_path, "number", exports=[form])
    exported_up_to(root, 1_000_000_000)
    return root


def an_unreadable_record(tmp_path: Path, form: str) -> Path:
    root = ready(tmp_path, exports=[form])
    write(root / RECORD, "pkit_schema: visual-communication:exports\n[")
    return root


def a_link_for_the_exports_folder(tmp_path: Path, form: str) -> Path:
    root = ready(tmp_path, exports=[form])
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / FOLDER).parent.mkdir(parents=True)
    (root / FOLDER).symlink_to(elsewhere, target_is_directory=True)
    return root


#: A piece of each kind an export refuses, in a format the test names.
REFUSED: dict[str, Callable[[Path, str], Path]] = {
    "final": lambda tmp_path, form: drawing_project(
        tmp_path, state="final", picture=False, exports=[form]
    ),
    "no-lock": lambda tmp_path, form: drawing_project(tmp_path, lock=None, exports=[form]),
    "a-lock-that-does-not-hold": lambda tmp_path, form: drawing_project(
        tmp_path, lock={**LOCK, "test-brand": "2.0.0"}, picture=False, exports=[form]
    ),
    "a-picture-missing": lambda tmp_path, form: drawing_project(tmp_path, exports=[form]),
    "a-stale-picture": a_stale_picture,
    "no-page-in-a-language": no_page_in_czech,
    "a-number-that-does-not-fit": a_number_that_does_not_fit,
    "an-unreadable-record": an_unreadable_record,
    "a-link-for-the-exports-folder": a_link_for_the_exports_folder,
}


@pytest.mark.parametrize("kind", sorted(REFUSED))
def test_what_refuses_an_svg_or_a_pdf_export_refuses_an_html_or_a_switching_one_before_any_write(
    tmp_path: Path, kind: str
) -> None:
    """Each refusal names the same, but a file's format where it names a file."""
    said = {}
    for form in ("svg", "pdf", "html", "svg-modes"):
        root = REFUSED[kind](tmp_path / form, form)
        said[form] = re.sub(r"\.(svg|pdf|html)\b", ".<format>", refused(root))
    assert said["html"] == said["svg"] == said["pdf"] == said["svg-modes"]
    assert said["html"].startswith("error: ")


# --- a piece exported as switching files (DEC-018 points 1 to 4) --------------------------------

#: The format of switching files, and the files a run of the deck makes in it as version 1:
#: one for each page and language, which holds both colour schemes under its first key.
MODES = "svg-modes"
SWITCHING_FILES = [
    f"flow.v1.{language}.default.{number}.svg" for language in SLIDES for number in (1, 2)
]


def rules_of(path: Path) -> list[str]:
    """The signals each rule of an exported switching file lies under, in order."""
    return re.findall(r"@media ([^{]+)\{", path.read_text(encoding="utf-8"))


def test_a_deck_exported_as_switching_files_makes_one_for_each_page_and_language(
    tmp_path: Path,
) -> None:
    root = deck(tmp_path, exports=[MODES])
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[1:] == [
        *(f"export: {FOLDER}/{name}" for name in SWITCHING_FILES),
        f"export: version 1 recorded in {RECORD}",
    ]
    assert exported(root) == sorted(SWITCHING_FILES)
    for name in SWITCHING_FILES:
        assert rules_of(root / FOLDER / name) == ["(prefers-color-scheme:dark)"]
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert version["files"] == {
        name: reading.sha256((root / FOLDER / name).read_bytes()) for name in SWITCHING_FILES
    }
    assert version["recorded"]["renderers"] == {"svg": svg.VERSION}
    assert "differing" not in version["recorded"]


@pytest.mark.parametrize(
    ("modes", "key"),
    [(["light", "dark"], "default"), (["dark"], DARK)],
    ids=["light-and-dark", "dark-alone"],
)
def test_a_switching_file_takes_the_first_key_it_serves(
    tmp_path: Path, modes: list[str], key: str
) -> None:
    root = drawing_project(tmp_path, picture=False, modes={"colour-scheme": modes}, exports=[MODES])
    assert run(root, PIECE).returncode == 0
    assert exported(root) == [f"flow.v1.en.{key}.svg"]
    assert rules_of(root / FOLDER / f"flow.v1.en.{key}.svg") == (
        ["(prefers-color-scheme:dark)"] if len(modes) > 1 else []
    )


def test_a_mode_the_combinations_hold_alike_parts_nothing(tmp_path: Path) -> None:
    root = drawing_project(
        tmp_path,
        picture=False,
        modes={"colour-scheme": ["light", "dark"], "contrast": ["standard"]},
        exports=[MODES],
    )
    assert run(root, PIECE).returncode == 0
    assert exported(root) == ["flow.v1.en.default.svg"]


def test_each_key_over_a_size_axis_takes_a_switching_file_of_its_own(tmp_path: Path) -> None:
    root = drawing_project(
        tmp_path,
        picture=False,
        modes={"colour-scheme": ["light", "dark"], "device": ["desktop", "phone"]},
        exports=[MODES],
    )
    add_device(root, PHONE_GROUND)
    assert run(root, PIECE).returncode == 0
    names = ["flow.v1.en.default.svg", f"flow.v1.en.{PHONE}.svg"]
    assert exported(root) == names
    for name in names:
        assert rules_of(root / FOLDER / name) == ["(prefers-color-scheme:dark)"]


def test_a_produced_picture_shows_the_variant_that_serves_each_combination(
    tmp_path: Path,
) -> None:
    root = ready(tmp_path, exports=[MODES])
    colours = {"default": (200, 30, 30, 255), "colour-scheme.dark": (30, 60, 200, 128)}
    write_picture(root, framing, by_variant=colours)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    drawn = (root / FOLDER / "flow.v1.en.default.svg").read_text(encoding="utf-8")
    assert re.findall(r'data-shown-in="([^"]*)"', drawn) == ["default", DARK]
    assert '[data-shown-in~="colour-scheme.dark"]{display:inline}' in drawn


def test_a_piece_that_names_both_svg_formats_is_refused_and_writes_nothing(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False, exports=["svg", MODES])
    assert refused(root) == (
        f"error: {PIECE_FOLDER}/piece.yaml names both `svg` and `svg-modes` under `exports`, "
        f"which write files of one name: name one of them\n"
    )


def test_a_piece_whose_combinations_differ_in_a_mode_of_no_pair_is_refused(
    tmp_path: Path,
) -> None:
    root = drawing_project(
        tmp_path,
        picture=False,
        modes={"colour-scheme": ["light", "dark"], "contrast": ["standard", "high"]},
        exports=[MODES],
    )
    assert refused(root) == (
        f"error: {PIECE_FOLDER}/piece.yaml: its combinations differ in a mode no switching file "
        f"of its format can hold: `svg-modes` reads no pair of `contrast`'s mode `standard`; "
        f"`svg-modes` reads no pair of `contrast`'s mode `high`. Draw that mode in a piece of "
        f"its own, or export the piece as `svg`\n"
    )


def slipping(monkeypatch: pytest.MonkeyPatch) -> None:
    """A slip in the switching file's rules, from now to the end of the test: the rule of a
    combination repaints nothing, so the plain drawing shows there."""
    monkeypatch.setattr(svg.Switching, "_key_rules", lambda self, key: "")


def differing_elements(said: str) -> list[str]:
    """The elements a refusal names as differing, in order."""
    return re.findall(r"`([^`]+)` of `flow\.v1\.en\.default\.svg` in `colour-scheme\.dark`", said)


def test_a_switching_file_that_differs_from_the_one_key_file_stops_the_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = drawing_project(tmp_path, picture=False, exports=[MODES])
    slipping(monkeypatch)
    said = refused(root)
    assert said.startswith(
        "error: a switching file paints a combination otherwise than the SVG renderer's file "
        "of that combination: `"
    )
    assert said.endswith(
        "Name each such element with `--use-differing <element>` to export its file as it is, "
        "and report it to whoever maintains the capability\n"
    )
    assert differing_elements(said)
    assert "and the one-key file's" in said


def test_each_element_named_is_let_through_and_the_record_keeps_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = drawing_project(tmp_path, picture=False, exports=[MODES])
    slipping(monkeypatch)
    elements = differing_elements(refused(root))
    named = [part for element in elements for part in ("--use-differing", element)]
    assert differing_elements(refused(root, *named[2:])) == elements[:1]
    done = run(root, PIECE, *named)
    assert done.returncode == 0, done.stderr
    let_through = [line for line in done.stdout.splitlines() if line.startswith("let through: ")]
    assert differing_elements("\n".join(let_through)) == elements
    record = reading.read_yaml(root / RECORD)
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert version["recorded"]["differing"] == [
        {"file": "flow.v1.en.default.svg", "key": DARK, "element": element} for element in elements
    ]


def test_an_element_named_that_does_not_differ_is_said_and_stops_nothing(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False, exports=[MODES])
    done = run(root, PIECE, "--use-differing", "figure")
    assert done.returncode == 0, done.stderr
    assert "not differing, so used as it is: figure" in done.stdout.splitlines()
    [version] = reading.read_yaml(root / RECORD)["versions"]
    assert "differing" not in version["recorded"]


def test_a_published_switching_files_copy_holds_its_versions_bytes(tmp_path: Path) -> None:
    root = published(tmp_path, exports=[MODES])
    assert run(root, PIECE).returncode == 0
    assert copied(root) == ["flow.en.default.svg"]
    copy = (root / COPY / "flow.en.default.svg").read_bytes()
    assert copy == (root / FOLDER / "flow.v1.en.default.svg").read_bytes()
    [version] = record_of(root)["versions"]
    assert record_of(root)["current-copy"]["files"] == {
        "current-copy/flow.en.default.svg": version["files"]["flow.v1.en.default.svg"]
    }


def test_the_previews_stay_one_key_files_whatever_the_format(tmp_path: Path) -> None:
    drawn = {}
    for form in ("svg", MODES):
        root = drawing_project(tmp_path / form, picture=False, exports=[form])
        assert run_main(render_script, PIECE, cwd=root).returncode == 0
        drawn[form] = every_file(root / PREVIEWS)
    assert sorted(drawn[MODES]) == ["flow.en.colour-scheme.dark.svg", "flow.en.default.svg"]
    assert drawn[MODES] == drawn["svg"]


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


# --- a current copy at a place ------------------------------------------------------------------

PLACE = "docs/images"

#: The files of the skeleton piece's current copy at the place, by the path the record holds.
PLACED = [f"{PLACE}/{name}" for name in reversed(COPIES)]

#: What the export says of a file of the last copy it did not write again.
LEFT = "the run did not write it again, and only a person removes it"


def at_place(tmp_path: Path, place: str = PLACE, **fields: Any) -> Path:
    """The published skeleton piece, naming `place` for its current copy."""
    return published(tmp_path, **{"copy-place": place}, **fields)


def placed_once(tmp_path: Path) -> Path:
    """A published piece exported once, its copy at the place."""
    root = at_place(tmp_path)
    assert run(root, PIECE).returncode == 0
    return root


def reworded(root: Path) -> None:
    """Change what the piece draws, so the next version's files differ."""
    path = root / PIECE_FOLDER / "content.en.yaml"
    text = path.read_text(encoding="utf-8")
    assert "Build it." in text
    path.write_text(text.replace("Build it.", "Build it well."), encoding="utf-8")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def assert_nothing_written(root: Path, shown: Any, said: str) -> None:
    """The first export was refused for `said`, and left no trace."""
    assert shown.returncode == 1
    assert said in shown.stderr, shown.stderr
    assert not (root / RECORD).exists()
    assert not (root / FOLDER).exists()
    assert not (root / CONFIG).exists()
    assert not (root / COPY).exists()


def assert_later_run_refused(root: Path, shown: Any, record: bytes, said: str) -> None:
    """A later export was refused for `said`: no new version, the record as it stood."""
    assert shown.returncode == 1
    assert said in shown.stderr, shown.stderr
    assert (root / RECORD).read_bytes() == record
    assert not any(".v2." in name for name in exported(root))


def test_a_piece_that_names_a_place_takes_its_copy_there_in_place_of_its_folder(
    tmp_path: Path,
) -> None:
    root = at_place(tmp_path)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[3:5] == [f"current copy: {path}" for path in PLACED]
    assert "left behind" not in shown.stdout
    assert copied(root, PLACE) == COPIES
    assert not (root / COPY).exists()
    for name in exported(root):
        copy = root / PLACE / name.replace("flow.v1.", "flow.")
        assert copy.read_bytes() == (root / FOLDER / name).read_bytes()


def test_the_record_holds_each_path_at_a_place_from_the_repositorys_root(tmp_path: Path) -> None:
    record = record_of(placed_once(tmp_path))
    assert files.shape_problems(record, "exports") == []
    [version] = record["versions"]
    assert record["current-copy"] == {
        "piece": PIECE,
        "version": 1,
        "files": {
            f"{PLACE}/{name.replace('flow.v1.', 'flow.')}": digest
            for name, digest in version["files"].items()
        },
    }


def test_a_change_of_the_place_leaves_the_exports_fingerprint_as_it_was(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    edit(root, f"copy-place: {PLACE}", "copy-place: docs/figures")
    assert run(root, PIECE).returncode == 0
    first, second = record_of(root)["versions"]
    assert first["fingerprint"] == second["fingerprint"]


def test_a_piece_in_another_state_writes_nothing_at_its_place(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, **{"copy-place": "../outside"})
    assert run(root, PIECE).returncode == 0
    assert not (root.parent / "outside").exists()


@pytest.mark.parametrize(
    ("place", "said"),
    [
        pytest.param("../outside", "lies outside the repository", id="outside"),
        pytest.param("/outside/images", "is absolute", id="absolute"),
        pytest.param(".", "is the repository's top itself", id="the-top"),
        pytest.param(".pkit/images", "lies under `.pkit/`", id="the-methodologys-folder"),
        pytest.param("docs/.images", "lies under a hidden folder", id="hidden"),
        pytest.param("visual", "lies in the location `visual`", id="the-location"),
        pytest.param("visual/images", "lies in the location `visual`", id="in-the-location"),
        pytest.param("current-copy", "reads as the piece's own `current-copy/`", id="its-own-name"),
    ],
)
def test_a_place_the_rules_refuse_refuses_and_writes_nothing(
    tmp_path: Path, place: str, said: str
) -> None:
    root = at_place(tmp_path, place)
    assert_nothing_written(root, run(root, PIECE), f"`copy-place: {place}` {said}")
    assert not (root.parent / "outside").exists()


def test_a_place_version_control_does_not_keep_refuses_and_writes_nothing(tmp_path: Path) -> None:
    root = at_place(tmp_path)
    git(root, "init", "-q")
    write(root / ".gitignore", "docs/images/\n")
    assert_nothing_written(
        root,
        run(root, PIECE),
        f"is no place version control keeps: git ignores {', '.join(PLACED)}",
    )
    assert not (root / "docs").exists()


def test_a_file_version_control_would_not_keep_refuses_at_a_place_it_keeps(tmp_path: Path) -> None:
    root = at_place(tmp_path)
    git(root, "init", "-q")
    write(root / ".gitignore", "*.svg\n")
    assert_nothing_written(root, run(root, PIECE), "is no place version control keeps")


def test_a_place_version_control_keeps_takes_the_copy(tmp_path: Path) -> None:
    root = at_place(tmp_path)
    git(root, "init", "-q")
    write(root / ".gitignore", "docs/other/\n")
    assert run(root, PIECE).returncode == 0
    assert copied(root, PLACE) == COPIES


def test_a_place_in_a_submodule_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """Git keeps no such file in this repository, and says so by failing."""
    root = at_place(tmp_path)
    git(root, "init", "-q")
    inner = root / "docs"
    inner.mkdir()
    git(inner, "init", "-q")
    identity = ("-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false")
    git(inner, *identity, "commit", "-q", "--allow-empty", "-m", "held")
    git(root, "add", "docs")
    assert_nothing_written(root, run(root, PIECE), "is no place git can say it keeps")


def test_a_link_on_the_way_to_a_place_refuses_and_writes_nothing(tmp_path: Path) -> None:
    root = at_place(tmp_path)
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    (root / "docs").symlink_to(elsewhere)
    assert_nothing_written(root, run(root, PIECE), "is reached through the link docs")
    assert list(elsewhere.iterdir()) == []


def test_a_link_at_a_path_it_writes_refuses_and_writes_nothing(tmp_path: Path) -> None:
    root = at_place(tmp_path)
    held = write(root / "elsewhere.svg", "mine\n")
    (root / PLACE).mkdir(parents=True)
    (root / PLACED[0]).symlink_to(held)
    assert_nothing_written(root, run(root, PIECE), f"is reached through the link {PLACED[0]}")
    assert held.read_text(encoding="utf-8") == "mine\n"


@pytest.mark.parametrize("file", ["docs", PLACE], ids=["above-the-place", "the-place-itself"])
def test_a_file_where_a_place_goes_refuses_and_writes_nothing(tmp_path: Path, file: str) -> None:
    root = at_place(tmp_path)
    write(root / file, "mine\n")
    assert_nothing_written(root, run(root, PIECE), f"is no folder: {file} is a file")


def test_an_export_writes_over_the_files_of_its_own_copy(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    before = {path: (root / path).read_bytes() for path in PLACED}
    reworded(root)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "left behind" not in shown.stdout
    assert all((root / path).read_bytes() != held for path, held in before.items())
    current = record_of(root)["current-copy"]
    assert current["version"] == 2
    assert current["files"] == {path: reading.sha256((root / path).read_bytes()) for path in PLACED}


def test_a_file_with_another_hash_refuses_and_is_named_before_any_write(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    record = (root / RECORD).read_bytes()
    reworded(root)
    changed = root / PLACED[0]
    changed.write_text("changed\n", encoding="utf-8")
    other = (root / PLACED[1]).read_bytes()
    assert_later_run_refused(
        root,
        run(root, PIECE),
        record,
        f"the export would write over {PLACED[0]}, and writes over only a file of the piece's "
        f"current copy with the hash the record keeps: name another place under `copy-place`, "
        f"or remove a file you mean to replace",
    )
    assert changed.read_text(encoding="utf-8") == "changed\n"
    assert (root / PLACED[1]).read_bytes() == other


def test_each_file_that_stops_the_run_is_named(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    record = (root / RECORD).read_bytes()
    for path in PLACED:
        (root / path).write_text("changed\n", encoding="utf-8")
    said = f"the export would write over {', '.join(PLACED)}, and"
    assert_later_run_refused(root, run(root, PIECE), record, said)


def test_a_file_removed_is_written_again(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    (root / PLACED[0]).unlink()
    assert run(root, PIECE).returncode == 0
    assert copied(root, PLACE) == COPIES


def test_a_file_no_record_names_refuses_the_first_export(tmp_path: Path) -> None:
    root = at_place(tmp_path)
    write(root / PLACED[0], "mine\n")
    assert_nothing_written(root, run(root, PIECE), f"would write over {PLACED[0]}, and")
    assert (root / PLACED[0]).read_text(encoding="utf-8") == "mine\n"


def test_a_folder_at_a_path_it_writes_refuses_and_writes_nothing(tmp_path: Path) -> None:
    root = at_place(tmp_path)
    (root / PLACED[0]).mkdir(parents=True)
    assert_nothing_written(root, run(root, PIECE), f"would write over {PLACED[0]}, and")


def test_a_file_of_another_piece_refuses_though_its_hash_holds(tmp_path: Path) -> None:
    """The record names a piece the location holds, so its copy is that piece's."""
    root = placed_once(tmp_path)
    write_piece(root, "other")
    record = record_of(root)
    record["current-copy"]["piece"] = "other"
    (root / RECORD).write_text(yaml_text(record), encoding="utf-8")
    held = (root / RECORD).read_bytes()
    assert_later_run_refused(
        root, run(root, PIECE), held, f"would write over {PLACED[0]}, {PLACED[1]}, and"
    )


def test_a_copy_of_another_piece_is_not_named_as_left_behind(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    write_piece(root, "other")
    record = record_of(root)
    record["current-copy"]["piece"] = "other"
    (root / RECORD).write_text(yaml_text(record), encoding="utf-8")
    edit(root, f"copy-place: {PLACE}", "copy-place: docs/figures")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "left behind" not in shown.stdout


def test_a_place_changed_names_each_old_file_and_leaves_it(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    held = {path: (root / path).read_bytes() for path in PLACED}
    edit(root, f"copy-place: {PLACE}", "copy-place: docs/figures")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert [line for line in shown.stdout.splitlines() if line.startswith("left behind")] == [
        f"left behind: {path}: {LEFT}" for path in PLACED
    ]
    assert {path: (root / path).read_bytes() for path in PLACED} == held
    assert copied(root, "docs/figures") == COPIES
    assert list(record_of(root)["current-copy"]["files"]) == [
        path.replace(PLACE, "docs/figures") for path in PLACED
    ]


def test_an_old_file_named_once_is_named_no_more(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    edit(root, f"copy-place: {PLACE}", "copy-place: docs/figures")
    assert run(root, PIECE).returncode == 0
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "left behind" not in shown.stdout


def test_a_file_the_new_version_does_not_write_at_a_place_is_named_and_stays(
    tmp_path: Path,
) -> None:
    root = placed_once(tmp_path)
    edit(root, "    - dark\n", "")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    dark = f"{PLACE}/flow.en.colour-scheme.dark.svg"
    assert f"left behind: {dark}: {LEFT}" in shown.stdout.splitlines()
    assert (root / dark).is_file()
    assert list(record_of(root)["current-copy"]["files"]) == [f"{PLACE}/flow.en.default.svg"]


def test_a_file_a_person_removed_is_not_named(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    (root / PLACED[1]).unlink()
    edit(root, f"copy-place: {PLACE}", "copy-place: docs/figures")
    shown = run(root, PIECE)
    assert [line for line in shown.stdout.splitlines() if line.startswith("left behind")] == [
        f"left behind: {PLACED[0]}: {LEFT}"
    ]


def test_a_piece_that_comes_to_name_a_place_names_its_folders_files_and_leaves_them(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    edit(root, "state: published", f"state: published\ncopy-place: {PLACE}")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert [line for line in shown.stdout.splitlines() if line.startswith("left behind")] == [
        f"left behind: {COPY}/{name}: {LEFT}" for name in reversed(COPIES)
    ]
    assert copied(root) == COPIES
    assert copied(root, PLACE) == COPIES


def test_a_piece_that_stops_naming_a_place_writes_its_folder_and_names_the_old_files(
    tmp_path: Path,
) -> None:
    root = placed_once(tmp_path)
    edit(root, f"copy-place: {PLACE}\n", "")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert [line for line in shown.stdout.splitlines() if line.startswith("left behind")] == [
        f"left behind: {path}: {LEFT}" for path in PLACED
    ]
    assert copied(root) == COPIES
    assert copied(root, PLACE) == COPIES
    assert list(record_of(root)["current-copy"]["files"]) == [
        f"current-copy/{name}" for name in reversed(COPIES)
    ]


def test_a_file_that_goes_with_the_pieces_folder_is_not_named(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    edit(root, "    - dark\n", "")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "left behind" not in shown.stdout
    assert copied(root) == ["flow.en.default.svg"]


def test_a_renamed_piece_names_each_file_of_its_old_name_at_the_place(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    renamed = "visual/pieces/flow-renamed"
    os.rename(root / PIECE_FOLDER, root / renamed)
    shown = run(root, "flow-renamed")
    assert shown.returncode == 0, shown.stderr
    assert [line for line in shown.stdout.splitlines() if line.startswith("left behind")] == [
        f"left behind: {path}: {LEFT}" for path in PLACED
    ]
    assert copied(root, PLACE) == sorted(
        [*COPIES, "flow-renamed.en.default.svg", "flow-renamed.en.colour-scheme.dark.svg"]
    )
    current = record_of(root, renamed)["current-copy"]
    assert current["piece"] == "flow-renamed"
    assert list(current["files"]) == [
        f"{PLACE}/flow-renamed.en.default.svg",
        f"{PLACE}/flow-renamed.en.colour-scheme.dark.svg",
    ]


def test_a_renamed_piece_in_its_folder_names_nothing(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert run(root, PIECE).returncode == 0
    os.rename(root / PIECE_FOLDER, root / "visual/pieces/flow-renamed")
    shown = run(root, "flow-renamed")
    assert shown.returncode == 0, shown.stderr
    assert "left behind" not in shown.stdout


def test_a_run_that_proposes_a_move_shares_the_rules_of_a_place(tmp_path: Path) -> None:
    root = placed_once(tmp_path)
    (root / PLACED[0]).write_text("changed\n", encoding="utf-8")
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    with pytest.raises(pl.Refused, match="the export would write over"):
        exports.plan(project)


def test_a_failed_first_export_leaves_no_folder_at_the_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = at_place(tmp_path)
    with monkeypatch.context() as patch:
        failing(patch, write={"exports.yaml"})
        shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == f"error: {RECORD} could not be written: {FULL}\n"
    assert not (root / "docs").exists()
    assert not (root / RECORD).exists()


def test_a_failed_export_puts_each_file_at_the_place_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = placed_once(tmp_path)
    held = {path: (root / path).read_bytes() for path in PLACED}
    record = (root / RECORD).read_bytes()
    reworded(root)
    with monkeypatch.context() as patch:
        failing(patch, write={"exports.yaml"})
        shown = run(root, PIECE)
    assert shown.returncode == 1
    assert {path: (root / path).read_bytes() for path in PLACED} == held
    assert (root / RECORD).read_bytes() == record
    assert copied(root, PLACE) == COPIES


# --- a page file's current copy (DEC-006 point 7, DEC-017 points 7 and 8) -----------------------


@pytest.mark.parametrize("place", [None, PLACE], ids=["in-its-folder", "at-a-place"])
def test_a_published_pieces_copy_holds_its_page_file_and_its_next_export_reads_the_record(
    tmp_path: Path, place: str | None
) -> None:
    root = published(tmp_path, exports=["html"], **({} if place is None else {"copy-place": place}))
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    folder = COPY if place is None else place
    assert copied(root, folder) == ["flow.en.default.html"]
    assert (root / folder / "flow.en.default.html").read_bytes() == (
        root / FOLDER / "flow.v1.en.default.html"
    ).read_bytes()
    record = record_of(root)
    assert files.shape_problems(record, "exports") == []
    recorded = "current-copy" if place is None else place
    [version] = record["versions"]
    assert record["current-copy"] == {
        "piece": PIECE,
        "version": 1,
        "files": {f"{recorded}/flow.en.default.html": version["files"]["flow.v1.en.default.html"]},
    }
    reworded(root)
    again = run(root, PIECE)
    assert again.returncode == 0, again.stderr
    assert record_of(root)["current-copy"]["version"] == 2
    assert copied(root, folder) == ["flow.en.default.html"]


@pytest.mark.parametrize("place", [None, PLACE], ids=["in-its-folder", "at-a-place"])
def test_a_page_file_whose_first_key_changes_goes_or_is_left_behind_as_any_file_of_the_copy(
    tmp_path: Path, place: str | None
) -> None:
    """A piece of dark alone that gains light names its file by the default key."""
    root = published(
        tmp_path,
        exports=["html"],
        modes={"colour-scheme": ["dark"]},
        **({} if place is None else {"copy-place": place}),
    )
    assert run(root, PIECE).returncode == 0
    folder = COPY if place is None else place
    assert copied(root, folder) == [f"flow.en.{DARK}.html"]
    edit(root, "    - dark\n", "    - light\n    - dark\n")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    left = [line for line in shown.stdout.splitlines() if line.startswith("left behind: ")]
    if place is None:
        assert copied(root, folder) == ["flow.en.default.html"]
        assert left == []
    else:
        assert copied(root, folder) == [f"flow.en.{DARK}.html", "flow.en.default.html"]
        assert left == [f"left behind: {place}/flow.en.{DARK}.html: {LEFT}"]
    recorded = "current-copy" if place is None else place
    assert list(record_of(root)["current-copy"]["files"]) == [f"{recorded}/flow.en.default.html"]


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


def test_a_plan_added_to_a_change_waits_for_what_holds_the_change(tmp_path: Path) -> None:
    root = exported_once(tmp_path)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    change = files.Change(root)
    exports.add(exports.plan(project), change)
    assert record_of(root)["current-copy"]["version"] == 1
    change.commit()
    assert record_of(root)["current-copy"]["version"] == 2


def test_a_plan_fingerprints_what_a_run_writes_in_place_of_the_file(tmp_path: Path) -> None:
    root = exported_once(tmp_path)
    edit(root, "tests: 1.0.0", "tests: 1.1.0")
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    path = root / PIECE_FOLDER / "piece.yaml"
    moved = path.read_bytes()
    now = datetime(2026, 11, 7, tzinfo=UTC)
    from_the_file = exports.plan(project, now=now)
    path.write_bytes(moved.replace(b"tests: 1.1.0", b"tests: 1.0.0"))
    assert exports.plan(project, now=now, written={path: moved}).versions == (
        from_the_file.versions
    )


def test_a_run_that_proposes_a_move_says_its_own_way_past_a_stale_picture(tmp_path: Path) -> None:
    root = ready(tmp_path)
    make_stale(root)
    piece = pl.read_piece(root, "visual", PIECE)
    project = pl.Project(piece, piece.lock, pl.Held(root, "visual"))
    with pytest.raises(pl.Refused) as caught:
        exports.plan(project, way_past_stale=lambda stale: f"Name {sorted(stale)}")
    said = str(caught.value)
    assert said.startswith("a produced picture is stale: `square` (")
    assert said.endswith(". Name ['square']")
    assert "pkit visual produce" not in said


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
