"""`pkit visual status` (DEC-002 point 1, DEC-003 point 8): the location, and whether it is
recorded, then each piece with its state and its lock. Run in this process
(`tests/in_process.py`); it starts no `pkit`."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.in_process import load, run_main
from tests.visual_communication_project import CONFIG, project, write, write_list, write_piece

(status,) = load("visual-communication", "status.py")

BINDING = "pkit_schema: visual-communication:config\nschema_version: 1\n"


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(status, *args, cwd=root)


def test_with_no_visual_work_it_says_so_and_how_a_location_is_taken(tmp_path: Path) -> None:
    root = project(tmp_path)
    shown = run(root)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.startswith("location: none — ")
    assert "the first command that writes takes `visual`" in shown.stdout


def test_the_default_holding_work_is_shown_unrecorded_with_its_pieces(tmp_path: Path) -> None:
    root = project(tmp_path)
    write_list(root, {})
    write_piece(root, "flow", lock={"test-brand": "1.0.0", "foundations": "1.0.0"})
    write_piece(root, "chart", pinned=True, lock={"foundations": "1.0.0"})
    write_piece(root, "new")
    shown = run(root)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines() == [
        f"location: visual (the default, not recorded yet; the first command that writes "
        f"there records it in {CONFIG})",
        "pieces:",
        "  chart: draft, pinned; lock foundations 1.0.0",
        "  flow: draft; lock foundations 1.0.0, test-brand 1.0.0",
        "  new: draft; no lock yet (its first render writes one)",
    ]


def test_each_state_is_shown_and_a_pin_is_read_of_a_draft_alone(tmp_path: Path) -> None:
    root = project(tmp_path)
    write_list(root, {})
    lock = {"foundations": "1.0.0"}
    write_piece(root, "draft", lock=lock)
    write_piece(root, "final", lock=lock, state="final", pinned=True)
    write_piece(root, "published", lock=lock, state="published", pinned=True)
    shown = run(root)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[2:] == [
        "  draft: draft; lock foundations 1.0.0",
        "  final: final; lock foundations 1.0.0",
        "  published: published; lock foundations 1.0.0",
    ]


def test_a_piece_no_render_writes_a_lock_for_says_what_its_state_needs(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    write_list(root, {})
    write_piece(root, "draft")
    write_piece(root, "final", state="final")
    write_piece(root, "published", state="published")
    shown = run(root)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[2:] == [
        "  draft: draft; no lock yet (its first render writes one)",
        "  final: final; no lock (write back the lock of the version handed out, which is no "
        "move of it)",
        "  published: published; no lock (set it back to a draft for its first render)",
    ]


def test_the_recorded_location_is_shown_with_where_it_is_recorded(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / CONFIG, f"{BINDING}location: docs/art\n")
    (root / "docs" / "art").mkdir(parents=True)
    shown = run(root / "docs")
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines() == [
        f"location: docs/art (recorded in {CONFIG})",
        "pieces: none",
    ]


def test_a_piece_whose_piece_yaml_cannot_be_used_says_why(tmp_path: Path) -> None:
    root = project(tmp_path)
    write_list(root, {})
    write(root / "visual" / "pieces" / "bare" / "scenes" / "main.yaml", "")
    write(root / "visual" / "pieces" / "broken" / "piece.yaml", "state: [\n")
    write(root / "visual" / "pieces" / "other" / "piece.yaml", "pkit_schema: x:y\n")
    lines = run(root).stdout.splitlines()
    assert lines[2] == "  bare: no piece.yaml"
    assert lines[3].startswith("  broken: piece.yaml cannot be read: ")
    assert lines[4] == (
        "  other: piece.yaml names the schema `x:y`, not `visual-communication:piece`"
    )


def test_in_a_repository_the_pieces_are_listed_as_git_sees_them(tmp_path: Path) -> None:
    root = project(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    write(root / ".gitignore", "visual/pieces/scratch/\n")
    write_list(root, {})
    write_piece(root, "flow")
    write_piece(root, "scratch")
    assert run(root).stdout.splitlines()[1:] == [
        "pieces:",
        "  flow: draft; no lock yet (its first render writes one)",
    ]


def test_a_recorded_location_that_is_missing_fails_naming_the_configuration(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    write(root / CONFIG, f"{BINDING}location: gone\n")
    shown = run(root)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr.startswith(f"error: {CONFIG} records the location `gone`, which does not")


def test_it_takes_no_arguments(tmp_path: Path) -> None:
    assert run(project(tmp_path), "--json").returncode == 2
