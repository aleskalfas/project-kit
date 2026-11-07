"""`pkit visual take-up <piece> <name>` (visual-communication DEC-003 point 8, DEC-017 points 1,
3, 5 and 8): a final piece copied as a new draft with its lock pinned, which draws as the piece it
copies and moves no lock; sources changed since the version, so the copy holds later words; the
final piece's past left out, its place for a current copy included; a piece set final by hand,
and each other refusal; the messages on a final piece that name the command; and a failed write.
Run in this process, the renderers standing in for the import an export makes when it draws."""

from __future__ import annotations

import os
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
    drawing_project,
    every_file,
    write_picture,
)
from tests.test_visual_communication_render import newer_tests
from tests.visual_communication_project import importable, write, yaml_text
from tests.visual_communication_writes import FULL, failing

(
    script,
    export_script,
    mark_script,
    render_script,
    check_script,
    svg,
    pdf,
    seam,
    framing,
    checks,
    reading,
    files,
) = load(
    "visual-communication",
    "take-up.py",
    "export.py",
    "mark-final.py",
    "render.py",
    "check.py",
    "plugins.svg",
    "plugins.pdf",
    "plugins.seam",
    "framing",
    "checks",
    "reading",
    "files",
)

NEW = "talk"
NEW_FOLDER = f"visual/pieces/{NEW}"
NEW_FILE = f"{NEW_FOLDER}/piece.yaml"
PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
CONTENT = f"{PIECE_FOLDER}/content.en.yaml"
RECORD = f"{PIECE_FOLDER}/exports.yaml"
CONFIG = ".pkit/capabilities/visual-communication/project/config.yaml"
TAKE_UP = "`pkit visual take-up flow <name>`"
PINNED = "lock of version 1 pinned: foundations 1.0.0, test-brand 1.0.0, tests 1.0.0"
TAKEN_UP = (
    f"taken up: `{NEW}`, a draft copied from `flow` with the lock of version 1 pinned, in "
    f"{NEW_FOLDER}: commit its folder. `flow` stays as it was"
)


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderers stand in for the import a run makes when it draws, and the test producer
    is registered, for the length of the test."""
    importable(monkeypatch, svg, pdf)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def final(tmp_path: Path, *, picture: bool = False, **fields: Any) -> Path:
    """The skeleton piece, its first version exported and marked final, under libraries listed
    released; with `picture`, it shows its produced picture too."""
    root = drawing_project(tmp_path, picture=picture, released=True, **fields)
    if picture:
        write_picture(root, framing)
    for command, args in ((export_script, [PIECE]), (mark_script, [PIECE, "1"])):
        done = run_main(command, *args, cwd=root)
        assert done.returncode == 0, done.stderr
    return root


def taken_up(root: Path, *args: str) -> list[str]:
    done = run(root, PIECE, NEW, *args)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


def piece_of(root: Path, file: str = NEW_FILE) -> dict[str, Any]:
    return reading.read_yaml(root / file)


def edit(root: Path, file: str, old: str, new: str) -> None:
    """Replace `old` in `file`, which must hold it."""
    path = root / file
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def refused_with_nothing_written(root: Path, *args: str) -> str:
    """What the run says on standard error, having written nothing."""
    before = every_file(root)
    shown = run(root, *args)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert every_file(root) == before
    return shown.stderr


def checked(root: Path, piece: str) -> subprocess.CompletedProcess[str]:
    return run_main(check_script, piece, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})


# --- a final piece taken up again ---------------------------------------------------------------


def test_a_final_piece_is_copied_as_a_draft_with_its_lock_pinned(tmp_path: Path) -> None:
    root = final(tmp_path)
    before = every_file(root / PIECE_FOLDER)
    assert taken_up(root) == [PINNED, TAKEN_UP]
    data = piece_of(root)
    assert (data["state"], data["pinned"], data["lock"]) == ("draft", True, LOCK)
    assert files.shape_problems(data, "piece") == []
    assert sorted(every_file(root / NEW_FOLDER)) == ["content.en.yaml", "piece.yaml"]
    copied = root / NEW_FOLDER / "content.en.yaml"
    assert copied.read_bytes() == (root / CONTENT).read_bytes()
    assert every_file(root / PIECE_FOLDER) == before


def test_the_copy_draws_as_the_final_piece_and_its_render_moves_no_lock(tmp_path: Path) -> None:
    root = final(tmp_path, picture=True)
    taken_up(root)
    newer_tests(root, released=True)
    before = (root / NEW_FILE).read_bytes()
    drawn = run_main(render_script, NEW, cwd=root)
    assert drawn.returncode == 0, drawn.stderr
    assert (root / NEW_FILE).read_bytes() == before
    assert (root / NEW_FOLDER / "findings.yaml").is_file()
    done = checked(root, NEW)
    assert done.returncode == 0, done.stdout
    assert "stale" not in done.stdout
    assert checked(root, PIECE).returncode == 0


def test_every_other_byte_of_the_pieces_file_stays_and_its_copy_place_goes(
    tmp_path: Path,
) -> None:
    root = final(tmp_path)
    path = root / PIECE_FILE
    text = path.read_bytes().replace(b"state: final", b"state: final  # handed out\npinned: false")
    original = b"# For the board.\r\ncopy-place: docs/figures\r\n" + text.replace(b"\n", b"\r\n")
    path.write_bytes(original)
    taken_up(root)
    assert (root / NEW_FILE).read_bytes() == (
        original.replace(b"copy-place: docs/figures\r\n", b"")
        .replace(b"state: final", b"state: draft")
        .replace(b"pinned: false", b"pinned: true")
    )
    assert path.read_bytes() == original


def test_a_pin_the_piece_lacks_is_added_at_the_end_of_its_file(tmp_path: Path) -> None:
    root = final(tmp_path)
    original = (root / PIECE_FILE).read_bytes()
    taken_up(root)
    assert (root / NEW_FILE).read_bytes() == (
        original.replace(b"state: final", b"state: draft") + b"pinned: true\n"
    )


def test_the_lock_is_the_one_the_version_handed_out_was_made_under(tmp_path: Path) -> None:
    root = final(tmp_path)
    newer_tests(root, released=True)
    edit(root, PIECE_FILE, "tests: 1.0.0", "tests: 1.1.0")
    assert PINNED in taken_up(root)
    assert piece_of(root)["lock"] == LOCK


def test_the_final_pieces_past_is_left_out(tmp_path: Path) -> None:
    """A published piece marked final keeps its current copy; a render left a findings record
    before it was final."""
    root = final(tmp_path, state="published")
    assert (root / PIECE_FOLDER / "current-copy").is_dir()
    write(root / PIECE_FOLDER / "findings.yaml", "# left from before\n")
    write(root / PIECE_FOLDER / "notes" / "why.txt", "A person's note.\n")
    taken_up(root)
    assert sorted(every_file(root / NEW_FOLDER)) == [
        "content.en.yaml",
        "notes/why.txt",
        "piece.yaml",
    ]
    done = checked(root, NEW)
    assert "current-copy-standing" not in done.stdout


def test_a_copy_of_sources_changed_since_the_version_holds_the_later_words(
    tmp_path: Path,
) -> None:
    root = final(tmp_path)
    edit(root, CONTENT, "Plan the work.", "Plan it.")
    said = taken_up(root)
    assert said == [PINNED, "changed since version 1: `content.en.yaml` changed", TAKEN_UP]
    assert "Plan it." in (root / NEW_FOLDER / "content.en.yaml").read_text(encoding="utf-8")


def test_it_records_the_location_where_none_is(tmp_path: Path) -> None:
    root = final(tmp_path)
    (root / CONFIG).unlink()
    assert taken_up(root)[0].startswith("recorded the location `visual`")


# --- what refuses -------------------------------------------------------------------------------


def test_a_piece_set_final_by_hand_is_refused_naming_the_mark(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    said = refused_with_nothing_written(root, PIECE, NEW)
    assert said == (
        f"error: the piece `flow` is final, and {RECORD} names no version handed out: run "
        f"`pkit visual mark-final flow <version>` first, which names it\n"
    )


def test_a_piece_with_no_version_handed_out_is_refused(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    assert refused_with_nothing_written(root, PIECE, NEW) == (
        "error: the piece `flow` has no version handed out, and only a final piece is taken up "
        "again\n"
    )


@pytest.mark.parametrize(
    ("name", "said"),
    [
        pytest.param(PIECE, "visual/pieces/flow lies in the location already", id="the-piece"),
        pytest.param("notes", "visual/pieces/notes lies in the location already", id="a-folder"),
        pytest.param("Talk", "`Talk` is not a piece's name", id="no-name"),
        pytest.param("no", "`no` is not a piece's name", id="a-yaml-word"),
    ],
)
def test_a_name_taken_or_not_a_pieces_name_is_refused(tmp_path: Path, name: str, said: str) -> None:
    root = final(tmp_path)
    write(root / "visual/pieces/notes/note.txt", "A person's file.\n")
    assert said in refused_with_nothing_written(root, PIECE, name)


def test_a_record_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    root = final(tmp_path)
    write(root / RECORD, "pkit_schema: visual-communication:exports\n<<<<<<< HEAD\n")
    assert "mend it, then take the piece up" in refused_with_nothing_written(root, PIECE, NEW)


def test_a_version_whose_fingerprint_gives_no_lock_is_refused(tmp_path: Path) -> None:
    root = final(tmp_path)
    record = reading.read_yaml(root / RECORD)
    record["versions"][0]["fingerprint"]["value"] = "0" * 64
    write(root / RECORD, yaml_text(record))
    said = refused_with_nothing_written(root, PIECE, NEW)
    assert f"{RECORD} gives no lock of version 1, handed out" in said
    assert "does not match its own inputs" in said


def test_a_file_the_copy_takes_through_a_link_is_refused(tmp_path: Path) -> None:
    root = final(tmp_path)
    path = root / CONTENT
    path.rename(root / "content.en.yaml")
    path.symlink_to(root / "content.en.yaml")
    said = refused_with_nothing_written(root, PIECE, NEW)
    assert f"the copy would reach a file through the link {CONTENT}" in said


def test_a_piece_reached_through_a_link_is_refused(tmp_path: Path) -> None:
    root = final(tmp_path)
    pieces = root / "visual/pieces"
    pieces.rename(root / "pieces")
    pieces.symlink_to(root / "pieces")
    said = refused_with_nothing_written(root, PIECE, NEW)
    assert "is reached through the link visual/pieces" in said


def test_a_link_in_the_final_pieces_past_refuses_nothing(tmp_path: Path) -> None:
    root = final(tmp_path)
    os.symlink(root / CONTENT, root / PIECE_FOLDER / "handed-out" / "content.en.yaml")
    taken_up(root)
    assert not (root / NEW_FOLDER / "handed-out").exists()


# --- the messages on a final piece name the command ---------------------------------------------


def test_an_export_and_a_second_mark_of_a_final_piece_name_the_command(tmp_path: Path) -> None:
    root = final(tmp_path)
    exported = run_main(export_script, PIECE, cwd=root)
    assert exported.returncode == 1
    assert f"run {TAKE_UP} to take it up again as a new draft" in exported.stderr
    marked = run_main(mark_script, PIECE, "1", cwd=root)
    assert marked.returncode == 1
    assert f"run {TAKE_UP}, which takes it up again as a new draft" in marked.stderr
    assert TAKE_UP in checks.no_move(PIECE)


# --- a failed write -----------------------------------------------------------------------------


def test_a_write_that_fails_leaves_no_part_of_the_new_piece(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = final(tmp_path)
    before = every_file(root)
    failing(monkeypatch, write=[NEW])
    shown = run(root, PIECE, NEW)
    assert shown.returncode == 1
    assert shown.stderr.startswith(f"error: {NEW_FOLDER} could not be written: ")
    assert FULL in shown.stderr
    assert every_file(root) == before
    assert sorted(path.name for path in (root / "visual/pieces").iterdir()) == [PIECE]
