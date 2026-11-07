"""`pkit visual upgrade <piece>` (visual-communication DEC-019 points 1 to 4, 6 and 7): each state
refused; a lock moved and landed, with the check and the next export; a lock written by hand;
nothing to move; a dry run; an edit, stopping and named; a stale picture, stopping and named; no
copy standing, some standing, and a file at a new place; each name in `add`'s form; a finding
that fails; and a failed write put back. Run in this process, the SVG renderer standing in for
the import a run makes when it draws."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    LOCK,
    PIECE,
    PIECE_FOLDER,
    changed_tests,
    drawing_project,
    every_file,
    exported_up_to,
    filled,
    list_drawing_libraries,
    write_picture,
)
from tests.visual_communication_project import (
    CONFIG,
    TEST_BRAND,
    copy_library,
    importable,
    write,
    yaml_text,
)
from tests.visual_communication_writes import FULL, failing

(
    script,
    export_script,
    check_script,
    render_script,
    mark_final_script,
    svg,
    seam,
    framing,
    before_after,
    fingerprint,
    reading,
    files,
    pl,
) = load(
    "visual-communication",
    "upgrade.py",
    "export.py",
    "check.py",
    "render.py",
    "mark-final.py",
    "plugins.svg",
    "plugins.seam",
    "framing",
    "before_after",
    "fingerprint",
    "reading",
    "files",
    "pipeline",
)

RECORD = f"{PIECE_FOLDER}/exports.yaml"
PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
CONTENT = f"{PIECE_FOLDER}/content.en.yaml"
FINDINGS = f"{PIECE_FOLDER}/findings.yaml"
COPY = f"{PIECE_FOLDER}/current-copy"
PLACE = "docs/images"
LOCAL = ".pkit/capabilities/visual-communication/project/local"
DRAWN = f"{LOCAL}/before-after/{PIECE}"
FILES = [f"{PIECE}.en.colour-scheme.dark.svg", f"{PIECE}.en.default.svg"]
OLD = "foundations 1.0.0, test-brand 1.0.0, tests 1.0.0"
NEW = "foundations 1.0.0, test-brand 1.0.0, tests 1.1.0"
MOVED = {**LOCK, "tests": "1.1.0"}
WROTE = "the lock of version 1, which wrote the current copy"
LEFT = (
    "proposal: left in the working tree, with nothing committed. Land it as a change, or discard it"
)
NOTHING_STOOD = "no file of the current copy stood, so the change shows only an after"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a run makes when it draws, and the test producer
    is registered, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def lines(root: Path, *args: str) -> list[str]:
    """What a run that succeeds prints, a line each."""
    done = run(root, PIECE, *args)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


def export(root: Path, *args: str) -> None:
    done = run_main(export_script, PIECE, *args, cwd=root)
    assert done.returncode == 0, done.stderr


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return run_main(check_script, PIECE, cwd=root)


def released(root: Path) -> None:
    """Each version the library folder holds, listed released."""
    list_drawing_libraries(root, released=True)


def newer(root: Path, version: str = "1.1.0") -> None:
    """The `tests` library at `version` too, which draws a step's head otherwise, listed
    released."""
    changed_tests(root / "visual/libraries/tests" / version, version)
    released(root)


def exported(tmp_path: Path, **fields: Any) -> Path:
    """The skeleton piece, published and exported once, under a lock of released versions."""
    root = drawing_project(tmp_path, state="published", picture=False, **fields)
    export(root)
    return root


def published(tmp_path: Path, **fields: Any) -> Path:
    """`exported`, with the `tests` library at 1.1.0 too."""
    root = exported(tmp_path, **fields)
    newer(root)
    return root


def edit(root: Path, file: str, old: str, new: str) -> None:
    """Replace `old` in `file`, which must hold it."""
    path = root / file
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def record_of(root: Path) -> dict[str, Any]:
    return reading.read_yaml(root / RECORD)


def lock_of(root: Path) -> dict[str, str]:
    return dict(reading.read_yaml(root / PIECE_FILE)["lock"])


def version_lock(root: Path, number: int) -> dict[str, str]:
    """The lock the version `number` of the piece was made under."""
    kept = next(each for each in record_of(root)["versions"] if each["version"] == number)
    return fingerprint.lock_of(kept["fingerprint"])


def refused(root: Path, *args: str) -> str:
    """What a refused run says on standard error, having changed no file."""
    before = every_file(root)
    shown = run(root, PIECE, *args)
    assert shown.returncode == 1, shown.stdout
    assert shown.stdout == ""
    assert every_file(root) == before
    return shown.stderr


# --- each state refused -------------------------------------------------------------------------


def test_a_draft_refuses_and_names_its_render(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    said = refused(root)
    assert "is a draft" in said and f"run `pkit visual render {PIECE}`" in said


def test_a_pinned_draft_refuses_and_names_a_hand_on_its_lock(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, pinned=True)
    said = refused(root)
    assert f"A hand moves a pinned draft's lock: change it in {PIECE_FILE}" in said


def test_a_final_piece_refuses_and_says_nothing_moves_its_lock(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, state="final")
    assert "nothing moves a final piece's lock" in refused(root)


def test_a_record_that_cannot_be_read_takes_the_piece_as_final(tmp_path: Path) -> None:
    root = published(tmp_path)
    write(root / RECORD, "pkit_schema: visual-communication:exports\n<<<<<<< HEAD\nversions: []\n")
    assert "nothing moves a final piece's lock" in refused(root)


def test_a_piece_with_a_version_handed_out_is_final_to_the_run(tmp_path: Path) -> None:
    root = published(tmp_path)
    done = run_main(mark_final_script, PIECE, "1", cwd=root)
    assert done.returncode == 0, done.stderr
    assert "nothing moves a final piece's lock" in refused(root)


def test_a_state_refuses_before_a_fault_in_the_content_is_read(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write(root / CONTENT, "not: [a content file\n")
    assert "is a draft" in refused(root)


def test_a_published_piece_with_no_lock_refuses(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, state="published", lock=None)
    said = refused(root)
    assert "has no lock to move" in said and "set it back to a draft" in said


def test_a_piece_the_location_does_not_hold_refuses(tmp_path: Path) -> None:
    root = published(tmp_path)
    shown = run(root, "other")
    assert shown.returncode == 1 and "holds no piece `other`" in shown.stderr


# --- a lock moved and landed --------------------------------------------------------------------


def test_a_run_moves_the_lock_and_carries_what_the_check_and_the_gate_read(tmp_path: Path) -> None:
    root = published(tmp_path)
    before = every_file(root)
    said = lines(root)
    assert said[:2] == [f"before: {WROTE}: {OLD}", f"after: what a run would propose: {NEW}"]
    assert f"lock: {NEW}" in said
    assert f"export: version 2 recorded in {RECORD}" in said
    assert said[-1] == LEFT
    assert lock_of(root) == MOVED
    record = record_of(root)
    assert record["current-copy"]["version"] == 2
    assert version_lock(root, 2) == MOVED
    hashes = record["versions"][-1]["files"]
    for name in FILES:
        data = (root / COPY / name).read_bytes()
        assert data != before[f"{COPY}/{name}"]
        numbered = name.replace(f"{PIECE}.", f"{PIECE}.v2.", 1)
        assert (root / LOCAL / "exports" / PIECE / numbered).read_bytes() == data
        assert hashes[numbered] == reading.sha256(data)


def git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def test_in_a_repository_the_diff_is_the_proposal_and_nothing_is_committed(tmp_path: Path) -> None:
    root = published(tmp_path)
    (root / ".gitignore").write_text(f"{LOCAL}/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-qm", "the piece")
    head = git(root, "rev-parse", "HEAD")
    lines(root)
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "branch", "--list").count("\n") == 1
    shown = git(root, "status", "--porcelain").splitlines()
    assert sorted(line[3:] for line in shown) == sorted(
        [PIECE_FILE, RECORD, FINDINGS, *(f"{COPY}/{name}" for name in FILES)]
    )
    assert check(root).returncode == 0
    export(root)


def test_every_other_byte_of_the_pieces_file_stays(tmp_path: Path) -> None:
    root = published(tmp_path)
    path = root / PIECE_FILE
    path.write_text("# Kept.\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    was = path.read_text(encoding="utf-8")
    lines(root)
    assert path.read_text(encoding="utf-8") == was.replace("tests: 1.0.0", "tests: 1.1.0")


def test_after_the_run_the_check_raises_nothing_for_the_move(tmp_path: Path) -> None:
    root = published(tmp_path)
    lines(root)
    shown = check(root)
    assert shown.returncode == 0, shown.stdout
    assert "current-copy" not in shown.stdout
    assert "read from their findings record" in shown.stdout


def test_after_the_run_the_next_export_passes_the_gate(tmp_path: Path) -> None:
    root = published(tmp_path)
    lines(root)
    export(root)
    assert record_of(root)["current-copy"]["version"] == 3
    assert version_lock(root, 3) == MOVED


def test_the_run_leaves_the_findings_record_of_a_render_under_the_moved_lock(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    assert f"findings: kept in {FINDINGS}" in lines(root)
    data = reading.read_yaml(root / FINDINGS)
    assert data["pkit_schema"] == "visual-communication:findings"
    inputs = data["key"]["inputs"]
    assert {entry["version"] for entry in inputs if entry.get("library") == "tests"} == {"1.1.0"}


def test_its_export_its_findings_and_its_drawing_take_the_stand_ins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Its export takes the stand-ins, as `pkit visual export` does, and refuses a piece that
    shows a version's number or its date, so its drawing takes them too (DEC-016 point 5)."""
    root = published(tmp_path)
    exported_up_to(root, 41)
    taken = filled(monkeypatch, pl)
    lines(root)
    stand_ins = pl.read_piece_file(root, "visual", PIECE).stand_ins
    assert len(taken) == 3
    assert all(facts == stand_ins for facts in taken)


def test_it_draws_no_preview_and_keeps_its_look_ahead_in_the_local_folder(tmp_path: Path) -> None:
    root = published(tmp_path)
    said = lines(root)
    assert not (root / LOCAL / "previews").exists()
    assert sorted(every_file(root / DRAWN)) == [
        *(f"after/{name}" for name in FILES),
        *(f"before/{name}" for name in FILES),
    ]
    assert f"drawn both ways in {DRAWN}/: 2 of 2 files differ" in said
    assert [line for line in said if line.startswith("differs: ")] == [
        f"differs: {name}" for name in FILES
    ]


def test_it_commits_nothing_and_touches_no_file_outside_the_proposal(tmp_path: Path) -> None:
    root = published(tmp_path)
    before = every_file(root)
    lines(root)
    after = every_file(root)
    changed = {path for path in {*before, *after} if before.get(path) != after.get(path)}
    outside = {path for path in changed if not path.startswith(f"{LOCAL}/")}
    assert outside == {PIECE_FILE, RECORD, FINDINGS, *(f"{COPY}/{name}" for name in FILES)}
    assert not (root / ".git").exists()


def test_it_states_each_newer_version_it_held_back_with_why(tmp_path: Path) -> None:
    root = published(tmp_path)
    newer(root, "2.0.0")
    said = lines(root)
    assert f"after: what a run would propose: {NEW}" in said
    assert any(line.startswith("held back: tests@2.0.0: ") for line in said)


def test_no_library_version_travels_in_it(tmp_path: Path) -> None:
    root = published(tmp_path)
    libraries = every_file(root / "visual/libraries")
    lines(root)
    assert every_file(root / "visual/libraries") == libraries


def test_the_location_is_recorded_as_any_writing_command_records_it(tmp_path: Path) -> None:
    root = published(tmp_path)
    (root / CONFIG).unlink()
    assert lines(root)[0].startswith("recorded the location `visual`")
    assert "location: visual" in (root / CONFIG).read_text(encoding="utf-8")


# --- a lock written by hand ---------------------------------------------------------------------


def test_it_serves_a_piece_the_gate_stopped_for_a_lock_written_by_hand(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 1.1.0")
    stopped = run_main(export_script, PIECE, cwd=root)
    assert stopped.returncode == 1 and f"pkit visual upgrade {PIECE}" in stopped.stderr
    said = lines(root)
    assert said[:2] == [f"before: {WROTE}: {OLD}", f"after: what a run would propose: {NEW}"]
    assert f"lock as it stands: {NEW}" in said
    assert version_lock(root, 2) == MOVED
    export(root)


def test_a_lock_written_by_hand_to_a_new_major_is_read_as_it_stands(tmp_path: Path) -> None:
    root = published(tmp_path)
    newer(root, "2.0.0")
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 2.0.0")
    lines(root)
    assert version_lock(root, 2) == {**LOCK, "tests": "2.0.0"}


# --- nothing to move ----------------------------------------------------------------------------


def test_nothing_to_move_says_so_and_writes_nothing(tmp_path: Path) -> None:
    root = exported(tmp_path)
    before = every_file(root)
    assert lines(root) == [
        f"nothing to move: `{PIECE}` holds {OLD}, and version 1, which wrote its current copy, "
        f"was made under that lock"
    ]
    assert every_file(root) == before


def test_a_second_run_finds_nothing_to_move(tmp_path: Path) -> None:
    root = published(tmp_path)
    lines(root)
    assert lines(root)[-1].startswith("nothing to move: ")


def test_nothing_to_move_still_states_what_it_held_back(tmp_path: Path) -> None:
    root = exported(tmp_path)
    newer(root, "2.0.0")
    said = lines(root)
    assert said[0].startswith("held back: tests@2.0.0: ")
    assert said[-1].startswith("nothing to move: ")


def test_naming_the_versions_the_lock_holds_is_nothing_to_move(tmp_path: Path) -> None:
    root = published(tmp_path)
    assert lines(root, "tests@1.0.0")[-1].startswith("nothing to move: ")


def test_a_lock_the_copy_was_not_made_under_is_a_move_though_the_lock_stays(tmp_path: Path) -> None:
    root = exported(tmp_path)
    newer(root)
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 1.1.0")
    assert f"export: version 2 recorded in {RECORD}" in lines(root)


def test_an_edit_does_not_stop_a_run_with_nothing_to_move(tmp_path: Path) -> None:
    root = exported(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    assert lines(root)[-1].startswith("nothing to move: ")


# --- a dry run ----------------------------------------------------------------------------------


def test_a_dry_run_says_what_it_would_write_and_changes_nothing(tmp_path: Path) -> None:
    root = published(tmp_path)
    before = every_file(root)
    said = lines(root, "--dry-run")
    assert every_file(root) == before
    assert said[:2] == [f"before: {WROTE}: {OLD}", f"after: what a run would propose: {NEW}"]
    assert [line for line in said if line.startswith("differs: ")] == [
        f"differs: {name}" for name in FILES
    ]
    assert "dry run: nothing is written, and a run would leave:" in said
    assert f"lock: {NEW}" in said
    assert f"current copy: {COPY}/{FILES[0]}" in said
    assert f"export: version 2 recorded in {RECORD}" in said
    assert f"findings: kept in {FINDINGS}" in said
    assert LEFT not in said


def test_a_dry_run_keeps_no_drawing_and_names_no_folder(tmp_path: Path) -> None:
    root = published(tmp_path)
    said = lines(root, "--dry-run")
    assert every_file(root / LOCAL / "before-after") == {}
    assert not any("drawn" in line for line in said)


def test_a_dry_run_records_no_location(tmp_path: Path) -> None:
    root = published(tmp_path)
    (root / CONFIG).unlink()
    lines(root, "--dry-run")
    assert not (root / CONFIG).exists()


def test_a_dry_run_stops_where_the_run_would(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    assert "changed since version 1" in refused(root, "--dry-run")


def test_a_dry_run_says_nothing_to_move_too(tmp_path: Path) -> None:
    assert lines(exported(tmp_path), "--dry-run")[-1].startswith("nothing to move: ")


def test_a_dry_run_then_a_run_take_one_number(tmp_path: Path) -> None:
    root = published(tmp_path)
    lines(root, "--dry-run")
    lines(root)
    assert record_of(root)["current-copy"]["version"] == 2


# --- an edit since the copy ---------------------------------------------------------------------


def test_an_edit_stops_the_run_and_names_each_input_and_the_line(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    write(root / PIECE_FOLDER / "components/extra.yaml", "pkit_schema: x\n")
    said = refused(root)
    assert "changed since version 1, which wrote its current copy" in said
    assert "`content.en.yaml` changed" in said and "`components/extra.yaml` is read now" in said
    line = f"{PIECE} --edited components/extra.yaml --edited content.en.yaml`"
    assert f"`pkit visual upgrade {line}" in said


def test_a_lock_moved_by_hand_and_a_new_version_gone_are_no_edit(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 1.1.0")
    assert "changed since" not in "\n".join(lines(root, "--dry-run"))


def test_a_library_version_gone_from_the_project_stops_nothing(tmp_path: Path) -> None:
    """The version the copy's lock named left the project: its files are left out."""
    root = published(tmp_path)
    for path in sorted((root / "visual/libraries/tests/1.0.0").rglob("*"), reverse=True):
        path.rmdir() if path.is_dir() else path.unlink()
    (root / "visual/libraries/tests/1.0.0").rmdir()
    released(root)
    said = lines(root)
    assert f"lock: {NEW}" in said and "no before: " in "\n".join(said)


def test_a_field_an_export_leaves_out_is_no_edit(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, PIECE_FILE, "state: published", "state: published\npinned: true")
    assert f"lock: {NEW}" in lines(root)


def test_an_edit_named_goes_on_and_lands_in_the_copy(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    assert "edit named: `content.en.yaml` changed" in lines(root, "--edited", "content.en.yaml")
    assert check(root).returncode == 0


def test_an_input_nobody_named_still_stops_and_the_line_names_them_all(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    write(root / PIECE_FOLDER / "components/extra.yaml", "pkit_schema: x\n")
    said = refused(root, "--edited", "content.en.yaml")
    assert "`components/extra.yaml` is read now" in said
    assert "`content.en.yaml` changed" not in said
    assert "--edited components/extra.yaml --edited content.en.yaml`" in said


def test_the_line_carries_what_else_was_named(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    said = refused(root, "tests@1.1.0")
    assert f"`pkit visual upgrade {PIECE} tests@1.1.0 --edited content.en.yaml`" in said


def test_an_input_named_that_did_not_change_is_said_and_stops_nothing(tmp_path: Path) -> None:
    root = published(tmp_path)
    said = lines(root, "--edited", "content.en.yaml")
    assert "named, and not changed since the copy: `content.en.yaml`" in said


def test_the_plain_way_on_is_an_export_under_the_lock_the_copy_holds(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    assert f"Run `pkit visual export {PIECE}`" in refused(root)
    export(root)
    assert f"lock: {NEW}" in lines(root)


def test_an_edit_stops_it_where_the_versions_files_no_longer_stand(tmp_path: Path) -> None:
    root = published(tmp_path)
    for name in FILES:
        (root / COPY / name).unlink()
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    assert "changed since version 1" in refused(root)


def test_where_nothing_wrote_a_copy_nothing_compares(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    newer(root)
    assert NOTHING_STOOD in lines(root)


def test_a_fingerprint_it_cannot_read_refuses_and_names_the_record(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, RECORD, "value: ", "value: 0")
    said = refused(root)
    assert f"{RECORD} gives no lock of version 1, which wrote the current copy" in said
    assert "as version control last held it" in said


# --- a stale picture ----------------------------------------------------------------------------


def pictured(tmp_path: Path) -> Path:
    """The piece with its picture, published and exported once, and the test brand at 1.1.0
    too, listed released, under which `accent` reads another value, so the picture goes
    stale there alone."""
    root = drawing_project(tmp_path, state="published")
    write_picture(root, framing)
    export(root)
    folder = copy_library(root, TEST_BRAND, "test-brand", "1.1.0")
    edit(root, f"{folder.relative_to(root)}/library.yaml", "version: 1.0.0", "version: 1.1.0")
    tokens = f"{folder.relative_to(root)}/tokens/base.tokens.json"
    edit(root, tokens, "{palette.blue.600}", "{palette.blue.800}")
    released(root)
    return root


def test_a_stale_picture_stops_the_run_names_what_changed_and_runs_no_program(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = pictured(tmp_path)
    monkeypatch.setattr(framing, "run", lambda *_: pytest.fail("no program runs"))
    said = refused(root)
    assert "a produced picture is stale: `square` (the value of `accent` in " in said
    assert "pkit visual produce" not in said
    assert f"`pkit visual upgrade {PIECE} --use-stale square`" in said


def test_a_stale_picture_named_is_used_as_it_is_and_the_lock_moves(tmp_path: Path) -> None:
    root = pictured(tmp_path)
    said = lines(root, "--use-stale", "square")
    assert "used while stale: square" in said
    assert record_of(root)["versions"][-1]["recorded"]["used-stale"] == ["square"]
    assert lock_of(root)["test-brand"] == "1.1.0"


def test_a_copy_made_over_a_stale_picture_asks_for_attention_and_fails_nothing(
    tmp_path: Path,
) -> None:
    root = pictured(tmp_path)
    lines(root, "--use-stale", "square")
    shown = check(root)
    assert shown.returncode == 0, shown.stdout
    assert "current-copy-over-stale" in shown.stdout


def test_a_picture_made_again_after_the_run_lands_through_the_next_export(tmp_path: Path) -> None:
    root = pictured(tmp_path)
    lines(root, "--use-stale", "square")
    write_picture(root, framing)
    export(root)
    assert "current-copy-over-stale" not in check(root).stdout


def test_a_picture_written_by_hand_under_the_new_lock_is_an_edit_to_name(tmp_path: Path) -> None:
    root = pictured(tmp_path)
    edit(root, PIECE_FILE, "test-brand: 1.0.0", "test-brand: 1.1.0")
    write_picture(root, framing)
    said = refused(root)
    assert "`produced/square/record.yaml` changed" in said
    assert "--edited produced/square/record.yaml" in said
    edited = lines(root, "--edited", "produced/square/record.yaml")
    assert "used while stale: square" not in edited


def test_an_output_the_piece_does_not_declare_refuses(tmp_path: Path) -> None:
    said = refused(published(tmp_path), "--use-stale", "square")
    assert "`--use-stale square` names no produced output" in said


def test_no_run_writes_the_lock_and_stops(tmp_path: Path) -> None:
    root = pictured(tmp_path)
    assert lock_of(root)["test-brand"] == "1.0.0"
    refused(root)
    assert lock_of(root)["test-brand"] == "1.0.0"


# --- a move with nothing to compare -------------------------------------------------------------


def test_with_no_copy_standing_it_writes_the_copy_whole_and_says_no_file_stood(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    for name in FILES:
        (root / COPY / name).unlink()
    said = lines(root)
    assert NOTHING_STOOD in said
    assert sorted(path.name for path in (root / COPY).iterdir()) == FILES
    assert record_of(root)["current-copy"]["version"] == 2
    export(root)


def test_a_folder_gone_with_its_copy_reads_as_no_copy_standing(tmp_path: Path) -> None:
    root = published(tmp_path)
    for name in FILES:
        (root / COPY / name).unlink()
    (root / COPY).rmdir()
    assert NOTHING_STOOD in lines(root)


def test_with_no_copy_of_its_own_it_goes_on(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="draft", picture=False)
    edit(root, PIECE_FILE, "state: draft", "state: published")
    released(root)
    said = lines(root)
    assert NOTHING_STOOD in said
    assert record_of(root)["current-copy"]["version"] == 1
    assert check(root).returncode == 0


def test_with_some_standing_each_missing_one_shows_its_after_alone(tmp_path: Path) -> None:
    root = published(tmp_path)
    (root / COPY / FILES[0]).unlink()
    said = lines(root)
    assert f"no file stood at {COPY}/{FILES[0]}, so the change shows only its after" in said
    assert NOTHING_STOOD not in said
    assert not any(f"no file stood at {COPY}/{FILES[1]}" in line for line in said)


def test_a_file_at_a_new_place_reads_as_new_and_what_stood_is_left_behind(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, PIECE_FILE, "state: published", f"state: published\ncopy-place: {PLACE}")
    said = lines(root)
    for name in FILES:
        assert f"no file stood at {PLACE}/{name}, so the change shows only its after" in said
        assert f"current copy: {PLACE}/{name}" in said
        assert (root / COPY / name).is_file()
        assert any(line.startswith(f"left behind: {COPY}/{name}: ") for line in said)
    assert NOTHING_STOOD not in said
    assert check(root).returncode == 0


def test_a_place_the_rules_refuse_stops_the_run(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, PIECE_FILE, "state: published", "state: published\ncopy-place: visual/images")
    assert "lies in the location" in refused(root)


# --- each name in `add`'s form ------------------------------------------------------------------


def test_a_name_moves_what_it_names_and_only_what_that_needs(tmp_path: Path) -> None:
    root = published(tmp_path)
    folder = copy_library(root, TEST_BRAND, "test-brand", "1.1.0")
    edit(root, f"{folder.relative_to(root)}/library.yaml", "version: 1.0.0", "version: 1.1.0")
    released(root)
    said = lines(root, "tests@1.1.0")
    assert f"after: the versions named: {NEW}" in said
    assert lock_of(root) == MOVED


def test_several_may_be_named(tmp_path: Path) -> None:
    root = published(tmp_path)
    folder = copy_library(root, TEST_BRAND, "test-brand", "1.1.0")
    edit(root, f"{folder.relative_to(root)}/library.yaml", "version: 1.0.0", "version: 1.1.0")
    released(root)
    lines(root, "tests@1.1.0", "test-brand@1.1.0")
    assert lock_of(root) == {**MOVED, "test-brand": "1.1.0"}


def test_a_name_may_lie_below_the_lock(tmp_path: Path) -> None:
    root = published(tmp_path)
    lines(root)
    lines(root, "tests@1.0.0")
    assert lock_of(root) == LOCK


def test_a_new_major_is_taken_by_a_name(tmp_path: Path) -> None:
    root = published(tmp_path)
    newer(root, "2.0.0")
    lines(root, "tests@2.0.0")
    assert lock_of(root) == {**LOCK, "tests": "2.0.0"}


def test_flags_may_come_before_a_name(tmp_path: Path) -> None:
    root = published(tmp_path)
    newer(root, "2.0.0")
    lines(root, "--dry-run", "tests@2.0.0")
    assert lock_of(root) == LOCK


def test_a_name_of_another_form_refuses(tmp_path: Path) -> None:
    assert "`tests` is no `<library>@<version>`" in refused(published(tmp_path), "tests")


def test_a_version_the_project_does_not_hold_refuses(tmp_path: Path) -> None:
    said = refused(published(tmp_path), "tests@9.0.0")
    assert "the project does not hold tests@9.0.0: bring it in" in said


def test_a_version_not_released_refuses(tmp_path: Path) -> None:
    root = published(tmp_path)
    path = root / "visual/libraries/libraries.yaml"
    data = reading.read_yaml(path)
    data["libraries"]["tests"]["versions"]["1.1.0"] = {"released": False}
    write(path, yaml_text(data))
    assert "tests@1.1.0 is not released" in refused(root, "tests@1.1.0")


def test_a_library_the_piece_does_not_use_refuses(tmp_path: Path) -> None:
    root = published(tmp_path)
    folder = root / "visual/libraries/other/1.0.0"
    copy_library(root, TEST_BRAND, "other", "1.0.0")
    edit(root, f"{folder.relative_to(root)}/library.yaml", "name: test-brand", "name: other")
    list_drawing_libraries(root, released=True, other="project")
    assert "the piece does not use `other`" in refused(root, "other@1.0.0")


# --- a finding that fails -----------------------------------------------------------------------


def renamed(root: Path) -> None:
    """The `tests` library at 2.0.0, whose card calls its head `title`, listed released."""
    changed_tests(root / "visual/libraries/tests/2.0.0", "2.0.0")
    card = "visual/libraries/tests/2.0.0/components/card.yaml"
    edit(root, card, "required: [head]", "required: [title]")
    edit(root, card, "    head:\n      type: string", "    title:\n      type: string")
    edit(root, card, "content: head", "content: title")
    released(root)


def test_it_names_each_finding_that_fails_under_the_new_lock_and_stops_on_none(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    renamed(root)
    said = lines(root, "tests@2.0.0")
    failing_lines = [line for line in said if line.startswith("fails: ")]
    assert failing_lines and all(f"{CONTENT}#" in line for line in failing_lines)
    assert lock_of(root)["tests"] == "2.0.0"
    assert said[-1] == LEFT
    assert check(root).returncode == 1


def test_a_finding_mended_in_the_same_change_lands_through_an_export(tmp_path: Path) -> None:
    root = published(tmp_path)
    renamed(root)
    lines(root, "tests@2.0.0")
    edit(root, CONTENT, "head: ", "title: ")
    export(root)
    assert version_lock(root, 3)["tests"] == "2.0.0"


# --- a failed write -----------------------------------------------------------------------------


@pytest.mark.parametrize("file", ["exports.yaml", "findings.yaml", "piece.yaml"])
def test_a_failed_write_leaves_each_file_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file: str
) -> None:
    root = published(tmp_path)
    before = every_file(root)
    failing(monkeypatch, write={file})
    shown = run(root, PIECE)
    assert shown.returncode == 1 and FULL in shown.stderr
    assert every_file(root) == before


def test_a_write_it_cannot_put_back_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = published(tmp_path)
    failing(
        monkeypatch,
        write={"exports.yaml"},
        remove={f"{PIECE}.v2.en.default.svg"},
    )
    shown = run(root, PIECE)
    assert shown.returncode == 1 and FULL in shown.stderr
    assert f"{PIECE}.v2.en.default.svg" in shown.stderr


def test_a_link_where_a_file_goes_refuses_before_any_write(tmp_path: Path) -> None:
    root = published(tmp_path)
    target = root / "elsewhere.yaml"
    target.write_text("{}\n", encoding="utf-8")
    (root / FINDINGS).unlink(missing_ok=True)
    (root / FINDINGS).symlink_to(target)
    assert "is reached through the link" in refused(root)


def test_a_drawing_that_cannot_be_kept_stops_nothing(tmp_path: Path) -> None:
    root = published(tmp_path)
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    (root / DRAWN).parent.mkdir(parents=True, exist_ok=True)
    (root / DRAWN).symlink_to(elsewhere)
    said = lines(root)
    assert any(line.startswith("no before-and-after kept: ") for line in said)
    assert lock_of(root) == MOVED


# --- what an export run shares with it ----------------------------------------------------------


def test_a_stop_of_an_export_stops_the_run(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, PIECE_FILE, "- svg", "[]")
    edit(root, PIECE_FILE, "exports:\n", "exports: ")
    assert "declares no format under `exports`" in refused(root, "--edited", "piece.yaml")


def test_the_gate_stays_at_the_export_a_person_runs(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 1.1.0")
    assert run_main(export_script, PIECE, cwd=root).returncode == 1
    assert run(root, PIECE).returncode == 0
