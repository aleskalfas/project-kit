"""`pkit visual mark-final <piece> <version>` (visual-communication DEC-017 points 1, 2 and 8):
a piece marked final, with its files in their folder; a draft and a published piece; the lock
put back; a piece changed after the version; each refusal; a lock that no longer holds; a piece
set final by hand; a version made before the reading of DEC-016 point 1; a record that cannot
be read; and a failed write put back. Run in this process, the renderers standing in for the
import an export makes when it draws."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    LOCK,
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    every_file,
)
from tests.test_visual_communication_render import newer_tests
from tests.visual_communication_project import importable, write, yaml_text
from tests.visual_communication_writes import FULL, failing

(
    script,
    export_script,
    render_script,
    check_script,
    produce_script,
    svg,
    pdf,
    copies,
    fingerprint,
    pl,
    reading,
    files,
) = load(
    "visual-communication",
    "mark-final.py",
    "export.py",
    "render.py",
    "check.py",
    "produce.py",
    "plugins.svg",
    "plugins.pdf",
    "copies",
    "fingerprint",
    "pipeline",
    "reading",
    "files",
)

LOCAL = ".pkit/capabilities/visual-communication/project/local/exports/flow"
RECORD = f"{PIECE_FOLDER}/exports.yaml"
PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
CONTENT = f"{PIECE_FOLDER}/content.en.yaml"
FINDINGS = f"{PIECE_FOLDER}/findings.yaml"
HANDED_OUT = f"{PIECE_FOLDER}/handed-out"
COPY = f"{PIECE_FOLDER}/current-copy"
V1 = ["flow.v1.en.colour-scheme.dark.svg", "flow.v1.en.default.svg"]
OLD = "foundations 1.0.0, test-brand 1.0.0, tests 1.0.0"
PUT_BACK = f"lock of version 1 put back: {OLD}"
CONFLICT = "pkit_schema: visual-communication:exports\n<<<<<<< HEAD\nversions: []\n"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderers stand in for the import an export makes when it draws."""
    importable(monkeypatch, svg, pdf)
    yield


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def export(root: Path) -> None:
    done = run_main(export_script, PIECE, cwd=root)
    assert done.returncode == 0, done.stderr


def exported(tmp_path: Path, **fields: Any) -> Path:
    """The skeleton piece, showing no produced picture, with its first version made, under
    libraries listed released."""
    root = drawing_project(tmp_path, picture=False, released=True, **fields)
    export(root)
    return root


def marked(root: Path, version: str = "1") -> list[str]:
    done = run(root, PIECE, version)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


def edit(root: Path, file: str, old: str, new: str) -> None:
    """Replace `old` in `file`, which must hold it."""
    path = root / file
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def record_of(root: Path) -> dict[str, Any]:
    return reading.read_yaml(root / RECORD)


def piece_of(root: Path) -> dict[str, Any]:
    return reading.read_yaml(root / PIECE_FILE)


def held_in(root: Path, folder: str) -> list[str]:
    return sorted(path.name for path in (root / folder).iterdir())


def refused_with_nothing_written(root: Path, *args: str) -> str:
    """What the run says on standard error, having written nothing."""
    before = every_file(root)
    shown = run(root, *args)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert every_file(root) == before
    return shown.stderr


# --- a piece marked final -----------------------------------------------------------------------


def test_a_draft_is_marked_final_with_its_files_in_their_folder(tmp_path: Path) -> None:
    root = exported(tmp_path)
    hashes = record_of(root)["versions"][0]["files"]
    assert marked(root) == [
        f"handed out: {HANDED_OUT}/{V1[1]}",
        f"handed out: {HANDED_OUT}/{V1[0]}",
        PUT_BACK,
        f"final: `flow`, version 1 named as handed out in {RECORD}: commit the piece's folder, "
        f"which holds its files",
    ]
    assert piece_of(root)["state"] == "final"
    assert piece_of(root)["lock"] == LOCK
    record = record_of(root)
    assert record["handed-out"] == 1
    assert files.shape_problems(record, "exports") == []
    assert held_in(root, HANDED_OUT) == V1
    assert held_in(root, LOCAL) == []
    assert {name: reading.sha256((root / HANDED_OUT / name).read_bytes()) for name in V1} == hashes


def test_every_other_byte_of_the_pieces_file_and_the_record_stays(tmp_path: Path) -> None:
    root = exported(tmp_path)
    path = root / PIECE_FILE
    path.write_bytes(b"# Kept.\r\n" + path.read_bytes().replace(b"\n", b"\r\n"))
    edit(root, PIECE_FILE, "state: draft", "state: draft  # for now")
    before, record = path.read_bytes(), (root / RECORD).read_bytes()
    marked(root)
    assert path.read_bytes() == before.replace(b"state: draft", b"state: final")
    assert (root / RECORD).read_bytes() == record + b"handed-out: 1\n"


def test_the_other_versions_stay_on_the_machine_that_made_them(tmp_path: Path) -> None:
    root = exported(tmp_path)
    export(root)
    marked(root, "2")
    assert held_in(root, LOCAL) == V1
    assert held_in(root, HANDED_OUT) == [name.replace("v1", "v2") for name in V1]


def test_no_fingerprint_reads_what_the_mark_writes_and_the_check_passes(tmp_path: Path) -> None:
    root = exported(tmp_path)
    kept = record_of(root)["versions"][0]["fingerprint"]
    marked(root)
    assert record_of(root)["versions"][0]["fingerprint"] == kept
    held = pl.Held(root, "visual")
    piece = pl.read_piece_file(root, "visual", PIECE)
    sources = pl.findings_key_sources(root, held, piece, piece.lock, [])
    assert fingerprint.verify(kept, "export", **sources) == []
    done = run_main(check_script, PIECE, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
    assert done.returncode == 0, done.stdout


def test_it_records_the_location_where_none_is(tmp_path: Path) -> None:
    root = exported(tmp_path)
    (root / ".pkit/capabilities/visual-communication/project/config.yaml").unlink()
    assert marked(root)[0].startswith("recorded the location `visual`")


# --- the lock put back --------------------------------------------------------------------------


def test_the_lock_of_the_version_comes_back_whatever_lock_the_draft_holds(tmp_path: Path) -> None:
    root = exported(tmp_path)
    newer_tests(root, released=True)
    assert run_main(render_script, PIECE, cwd=root).returncode == 0
    assert piece_of(root)["lock"]["tests"] == "1.1.0"
    said = marked(root)
    assert PUT_BACK in said
    assert piece_of(root)["lock"] == LOCK
    assert not [line for line in said if line.startswith("changed since")]


def test_a_published_pieces_lock_comes_back_too_and_its_copy_stays(tmp_path: Path) -> None:
    root = exported(tmp_path, state="published")
    newer_tests(root, released=True)
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 1.1.0")
    copy = every_file(root / COPY)
    said = marked(root)
    assert PUT_BACK in said
    assert piece_of(root)["state"] == "final"
    assert piece_of(root)["lock"] == LOCK
    assert every_file(root / COPY) == copy
    assert not [line for line in said if line.startswith("current copy")]


def test_a_published_piece_says_where_the_version_named_did_not_write_its_copy(
    tmp_path: Path,
) -> None:
    root = exported(tmp_path, state="published")
    export(root)
    copy = every_file(root / COPY)
    assert (
        "current copy: version 2 wrote it, not version 1. It stays, a page goes on showing it, "
        "and no export mends it"
    ) in marked(root)
    assert every_file(root / COPY) == copy
    assert record_of(root)["current-copy"]["version"] == 2


# --- what else changed --------------------------------------------------------------------------


def test_a_piece_changed_after_the_version_is_named_and_stops_nothing(tmp_path: Path) -> None:
    root = exported(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    write(root / "visual/libraries/tests/1.0.0/notes.txt", "A note.\n")
    edit(root, PIECE_FILE, "exports:\n  - svg", "exports:\n  - svg\n  - pdf")
    said = marked(root)
    assert [line for line in said if line.startswith("changed since")] == [
        "changed since version 1: `content.en.yaml` changed",
        "changed since version 1: `piece.yaml` at `exports` changed",
        "changed since version 1: `piece.yaml` changed",
        "changed since version 1: `notes.txt` of tests@1.0.0 is read now",
    ]
    assert piece_of(root)["state"] == "final"


def test_a_field_the_export_leaves_out_changes_nothing(tmp_path: Path) -> None:
    root = exported(tmp_path)
    edit(root, PIECE_FILE, "state: draft", "state: published\npinned: true")
    assert not [line for line in marked(root) if line.startswith(("changed", "read whole"))]


def made_before_the_reading(root: Path) -> None:
    """Rewrite the record's first version as an export before DEC-016's reading left it: its
    input of the piece's own file read the whole file, as it lies now."""
    record = record_of(root)
    kept = record["versions"][0]["fingerprint"]
    for entry in kept["inputs"]:
        if entry.get("file") == "piece.yaml" and "without" in entry:
            del entry["without"]
            entry["sha256"] = reading.sha256(fingerprint.reading(root / PIECE_FILE))
    kept["value"] = reading.sha256(reading.canonical_bytes(kept["inputs"]))
    write(root / RECORD, yaml_text(record))


WHOLE = (
    "read whole: version 1 read `piece.yaml` whole, made before an export left fields out of "
    "it, so a pin or a change of state reads as a change"
)


def test_a_version_made_before_the_reading_says_the_file_was_read_whole(tmp_path: Path) -> None:
    root = exported(tmp_path)
    made_before_the_reading(root)
    said = marked(root)
    assert WHOLE in said
    assert PUT_BACK in said
    assert not [line for line in said if line.startswith("changed since")]


def test_the_runs_own_state_counts_for_nothing_and_a_pin_reads_as_a_change_there(
    tmp_path: Path,
) -> None:
    root = exported(tmp_path)
    made_before_the_reading(root)
    edit(root, PIECE_FILE, "state: draft", "state: draft\npinned: true")
    said = marked(root)
    assert "changed since version 1: `piece.yaml` changed" in said
    assert WHOLE in said
    assert piece_of(root)["state"] == "final"


# --- what refuses -------------------------------------------------------------------------------


def test_a_file_missing_or_changed_refuses_naming_each(tmp_path: Path) -> None:
    root = exported(tmp_path)
    (root / LOCAL / V1[0]).unlink()
    write(root / LOCAL / V1[1], "<svg/>")
    said = refused_with_nothing_written(root, PIECE, "1")
    assert f"{LOCAL}/{V1[0]} is missing" in said
    assert f"{LOCAL}/{V1[1]} differs from the hash the record keeps" in said


@pytest.mark.parametrize(
    ("fault", "said"),
    [
        pytest.param(
            lambda kept: kept.pop("fingerprint"), "no fingerprint is kept", id="fingerprint-missing"
        ),
        pytest.param(
            lambda kept: kept["fingerprint"].update(value="0" * 64),
            "does not match its own inputs",
            id="fingerprint-edited",
        ),
    ],
)
def test_a_fingerprint_that_gives_no_lock_refuses_naming_the_record(
    tmp_path: Path, fault: Any, said: str
) -> None:
    root = exported(tmp_path)
    record = record_of(root)
    fault(record["versions"][0])
    write(root / RECORD, yaml_text(record))
    shown = refused_with_nothing_written(root, PIECE, "1")
    assert f"{RECORD} gives no lock of version 1" in shown
    assert said in shown


def test_a_second_version_refuses_on_a_piece_that_has_one_handed_out(tmp_path: Path) -> None:
    root = exported(tmp_path)
    export(root)
    marked(root)
    said = refused_with_nothing_written(root, PIECE, "2")
    assert f"{RECORD} names version 1 as handed out, and a piece holds one" in said


def test_the_same_version_again_refuses_too(tmp_path: Path) -> None:
    root = exported(tmp_path)
    marked(root)
    assert "names version 1 as handed out" in refused_with_nothing_written(root, PIECE, "1")


def test_a_version_the_record_does_not_hold_refuses_naming_those_it_does(tmp_path: Path) -> None:
    root = exported(tmp_path)
    said = refused_with_nothing_written(root, PIECE, "7")
    assert said == f"error: {RECORD} records no version 7: it holds 1\n"


def test_a_version_that_is_no_number_is_a_usage_error(tmp_path: Path) -> None:
    root = exported(tmp_path)
    before = every_file(root)
    assert run(root, PIECE, "first").returncode == 2
    assert every_file(root) == before


def test_a_piece_with_no_record_refuses(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    said = refused_with_nothing_written(root, PIECE, "1")
    assert said == f"error: {RECORD} records no version 1: it holds none\n"


def test_a_record_that_cannot_be_read_refuses(tmp_path: Path) -> None:
    root = exported(tmp_path)
    write(root / RECORD, CONFLICT)
    assert "mend it, then name the version" in refused_with_nothing_written(root, PIECE, "1")


def test_something_where_the_files_go_refuses(tmp_path: Path) -> None:
    root = exported(tmp_path)
    write(root / HANDED_OUT / "note.txt", "A person's file.\n")
    said = refused_with_nothing_written(root, PIECE, "1")
    assert f"{HANDED_OUT} lies in the piece's folder" in said


def test_a_file_reached_through_a_link_refuses(tmp_path: Path) -> None:
    root = exported(tmp_path)
    path = root / RECORD
    path.rename(root / "exports.yaml")
    path.symlink_to(root / "exports.yaml")
    assert "is reached through the link" in refused_with_nothing_written(root, PIECE, "1")


def test_a_state_its_text_cannot_take_refuses(tmp_path: Path) -> None:
    root = exported(tmp_path)
    path = root / PIECE_FILE
    data = reading.read_yaml(path)
    write(path, "{" + ", ".join(f"{key}: {value!r}" for key, value in data.items()) + "}\n")
    assert "cannot take" in refused_with_nothing_written(root, PIECE, "1")


# --- a lock that no longer holds ----------------------------------------------------------------


def test_a_version_gone_refuses_nothing_and_the_run_says_so(tmp_path: Path) -> None:
    root = exported(tmp_path)
    newer_tests(root, released=True)
    shutil.rmtree(root / "visual/libraries/tests/1.0.0")
    said = marked(root)
    assert any(
        line.startswith(
            f"fails: {PIECE_FILE}#lock: the lock names tests@1.0.0, which the project does not hold"
        )
        for line in said
    )
    assert piece_of(root)["lock"] == LOCK
    assert piece_of(root)["state"] == "final"


def test_a_version_changed_since_its_release_refuses_nothing_and_the_run_says_so(
    tmp_path: Path,
) -> None:
    root = exported(tmp_path)
    write(root / "visual/libraries/tests/1.0.0/notes.txt", "A note.\n")
    assert any(
        line.startswith("fails: visual/libraries/tests/1.0.0: tests@1.0.0 no longer matches")
        for line in marked(root)
    )


def test_a_version_not_released_refuses_nothing_and_the_run_says_so(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    export(root)
    assert any(
        "the final piece `flow` locks tests@1.0.0, which is not yet released" in line
        for line in marked(root)
    )


# --- a piece set final by hand ------------------------------------------------------------------


def test_a_piece_set_final_by_hand_takes_the_command(tmp_path: Path) -> None:
    root = exported(tmp_path)
    edit(root, PIECE_FILE, "state: draft", "state: final")
    before = (root / PIECE_FILE).read_bytes()
    assert PUT_BACK in marked(root)
    assert (root / PIECE_FILE).read_bytes() == before
    assert record_of(root)["handed-out"] == 1
    assert held_in(root, HANDED_OUT) == V1


# --- final to every command ---------------------------------------------------------------------


def test_the_field_makes_a_piece_final_whatever_its_state_says(tmp_path: Path) -> None:
    root = exported(tmp_path)
    marked(root)
    edit(root, PIECE_FILE, "state: final", "state: draft")
    newer_tests(root, released=True)
    before = (root / PIECE_FILE).read_bytes()
    said = "the piece `flow` is final (its record of exports hands out version 1)"
    assert said in run_main(export_script, PIECE, cwd=root).stderr
    assert said in run_main(produce_script, PIECE, "square", cwd=root).stderr
    drawn = run_main(render_script, PIECE, cwd=root)
    assert drawn.returncode == 0, drawn.stderr
    assert (root / PIECE_FILE).read_bytes() == before
    assert not (root / FINDINGS).exists()


def test_a_record_that_cannot_be_read_takes_the_piece_as_final(tmp_path: Path) -> None:
    root = exported(tmp_path)
    write(root / RECORD, CONFLICT)
    newer_tests(root, released=True)
    before = (root / PIECE_FILE).read_bytes()
    said = "the piece `flow` is final (its record of exports cannot be read: "
    assert said in run_main(export_script, PIECE, cwd=root).stderr
    assert said in run_main(produce_script, PIECE, "square", cwd=root).stderr
    drawn = run_main(render_script, PIECE, cwd=root)
    assert drawn.returncode == 0, drawn.stderr
    assert said.removeprefix("the piece `flow` is final ") in drawn.stdout
    assert (root / PIECE_FILE).read_bytes() == before
    assert not (root / FINDINGS).exists()
    assert copies.locks(root, "visual", "tests")[0].follows


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(CONFLICT, id="conflict"),
        pytest.param("versions: []\n", id="unbound"),
        pytest.param(
            "pkit_schema: visual-communication:exports\nschema_version: 1\nversions: []\n"
            "handed-out: first\n",
            id="no-number",
        ),
    ],
)
def test_a_record_it_cannot_read_gives_why_and_no_version(tmp_path: Path, record: str) -> None:
    root = exported(tmp_path)
    write(root / RECORD, record)
    assert copies.why_final({"state": "draft"}, root / PIECE_FOLDER).startswith(
        "its record of exports cannot be read: "
    )
    assert str(root) not in copies.why_final({"state": "draft"}, root / PIECE_FOLDER)
    with pytest.raises(copies.records.RecordError):
        copies.handed_out(root / PIECE_FOLDER)


def test_a_piece_with_no_record_and_a_record_naming_none_are_not_final(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert not copies.final({"state": "draft"}, root / PIECE_FOLDER)
    export(root)
    assert not copies.final({"state": "published"}, root / PIECE_FOLDER)
    assert copies.handed_out(root / PIECE_FOLDER) is None


def test_a_piece_reads_its_record_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = exported(tmp_path)
    reads = []
    handed_out = copies.handed_out
    monkeypatch.setattr(copies, "handed_out", lambda f: reads.append(f) or handed_out(f))
    piece = pl.read_piece_file(root, "visual", PIECE)
    assert not piece.final
    assert not piece.lock_stays
    assert len(reads) == 1


# --- a write that fails -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fails",
    [
        pytest.param({"write": ["exports.yaml"]}, id="the-record"),
        pytest.param({"write": ["piece.yaml"]}, id="the-pieces-file"),
        pytest.param({"write": ["handed-out"]}, id="the-folder"),
    ],
)
def test_a_write_that_fails_puts_every_file_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fails: dict[str, list[str]]
) -> None:
    root = exported(tmp_path)
    before = every_file(root)
    failing(monkeypatch, **fails)
    shown = run(root, PIECE, "1")
    assert shown.returncode == 1
    assert shown.stderr.startswith("error: ")
    assert FULL in shown.stderr
    assert every_file(root) == before
    assert not (root / HANDED_OUT).exists()


def test_a_write_that_fails_names_each_file_it_could_not_put_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file of that name cannot be removed from either folder here, so the copy in the
    piece's folder stays too, and the run names that folder."""
    root = exported(tmp_path)
    piece, record = (root / PIECE_FILE).read_bytes(), (root / RECORD).read_bytes()
    failing(monkeypatch, remove=[V1[1]])
    shown = run(root, PIECE, "1")
    assert shown.returncode == 1
    assert f"{LOCAL}/{V1[1]} could not be removed" in shown.stderr
    assert f"could not be put back as they were before the run: {HANDED_OUT}" in shown.stderr
    assert (root / PIECE_FILE).read_bytes() == piece
    assert (root / RECORD).read_bytes() == record
