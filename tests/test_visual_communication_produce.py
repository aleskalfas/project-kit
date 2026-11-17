"""`pkit visual produce <piece> <output>` (visual-communication DEC-006 points 1 to 5): the
command around the framing (`test_visual_communication_framing.py`), run in this process
with the producer kept for the tests registered, and once as a process of its own, where
no test registers it, so the command refuses it as unknown (DEC-005 point 12); and what a
write that fails leaves."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.visual_communication_producer import OUTPUT, PIECE, producing_project
from tests.visual_communication_project import CAPABILITY, CONFIG, RECORDED_DEFAULT
from tests.visual_communication_writes import FULL, failing

script, seam = load("visual-communication", "produce.py", "plugins.seam")

SCRIPT = CAPABILITY / "scripts" / "produce.py"
PRODUCED = f"visual/pieces/{PIECE}/produced/{OUTPUT}"
HANDOVER = f".pkit/capabilities/visual-communication/project/local/handover/{PIECE}"


@pytest.fixture(autouse=True)
def square() -> Iterator[None]:
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def test_it_writes_the_picture_says_what_each_variant_serves_and_records_the_location(
    tmp_path: Path,
) -> None:
    root = producing_project(tmp_path)
    shown = run(root, PIECE, OUTPUT)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines() == [
        RECORDED_DEFAULT,
        "produced `marker` of `flow` with square 1.0.0: 2 variants for 4 combinations",
        "  default.png serves default, contrast.high",
        "  colour-scheme.dark.png serves colour-scheme.dark, colour-scheme.dark+contrast.high",
        f"wrote {PRODUCED}/record.yaml",
    ]
    assert (root / CONFIG).read_text(encoding="utf-8").endswith("location: visual\n")
    assert (root / PRODUCED / "default.png").is_file()


def test_a_second_run_records_nothing_and_names_a_variant_it_removed(tmp_path: Path) -> None:
    root = producing_project(tmp_path, modes={"colour-scheme": ["dark"]})
    assert run(root, PIECE, OUTPUT).returncode == 0
    piece = root / "visual" / "pieces" / PIECE / "piece.yaml"
    piece.write_text(
        piece.read_text(encoding="utf-8").replace("- dark", "- light"), encoding="utf-8"
    )
    shown = run(root, PIECE, OUTPUT)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines() == [
        "produced `marker` of `flow` with square 1.0.0: 1 variant for 1 combination",
        "  default.png serves default",
        "  removed colour-scheme.dark.png, which no variant names now",
        f"wrote {PRODUCED}/record.yaml",
    ]


def test_it_prints_each_loss_the_piece_does_not_accept(tmp_path: Path) -> None:
    edged = {
        OUTPUT: {
            "producer": producer.NAME,
            "inputs": {"fill": "accent", "edge": "line"},
            "pixels": {"width": 64, "height": 64},
        }
    }
    root = producing_project(tmp_path, produced=edged)
    shown = run(root, PIECE, OUTPUT)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[-1] == (
        "loss: the square producer leaves out `line`: a square of one colour draws no edge"
    )
    accepting = [{"plugin": "square", "what": "line", "reason": "The marker needs no edge."}]
    root = producing_project(tmp_path / "accepting", produced=edged, accept_losses=accepting)
    shown = run(root, PIECE, OUTPUT)
    assert shown.returncode == 0, shown.stderr
    assert not any(line.startswith("loss:") for line in shown.stdout.splitlines())


def test_a_refusal_exits_1_and_writes_nothing(tmp_path: Path) -> None:
    root = producing_project(tmp_path, lock=None)
    shown = run(root, PIECE, OUTPUT)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr == (
        "error: the piece `flow` has no lock yet: run `pkit visual render flow` first, which "
        "writes it, then produce\n"
    )
    assert not (root / CONFIG).exists()
    assert not (root / PRODUCED).exists()


def set_state(root: Path, state: str) -> None:
    piece = root / "visual" / "pieces" / PIECE / "piece.yaml"
    piece.write_text(
        piece.read_text(encoding="utf-8").replace("state: draft", f"state: {state}"),
        encoding="utf-8",
    )


def test_a_published_piece_with_no_lock_is_told_to_go_back_to_a_draft(tmp_path: Path) -> None:
    root = producing_project(tmp_path, lock=None)
    set_state(root, "published")
    shown = run(root, PIECE, OUTPUT)
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the piece `flow` is published and has no lock: set it back to a draft for its "
        "first render, then produce\n"
    )
    assert not (root / PRODUCED).exists()


def test_a_final_piece_takes_no_run_and_nothing_is_written(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    set_state(root, "final")
    shown = run(root, PIECE, OUTPUT)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr == (
        "error: the piece `flow` is final (its state says so), and a final piece takes no "
        "producer's run: making its pictures again would change it\n"
    )
    assert not (root / PRODUCED).exists()
    assert not (root / HANDOVER).exists()
    assert not (root / CONFIG).exists()


def test_a_location_refused_is_named(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    shown = run(root, PIECE, OUTPUT, "--location", ".pkit/art")
    assert shown.returncode == 1
    assert "lies under `.pkit/`" in shown.stderr


# --- what a failed run leaves -------------------------------------------------------------------


def produced(root: Path) -> dict[str, bytes]:
    """Every file of the output's folder, with its bytes."""
    folder = root / PRODUCED
    return {path.name: path.read_bytes() for path in sorted(folder.iterdir())}


@pytest.mark.parametrize("file", ["record.yaml", "default.png"])
def test_a_write_that_fails_leaves_the_variants_and_their_record_as_they_were(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file: str
) -> None:
    root = producing_project(tmp_path, modes={"colour-scheme": ["dark"]})
    assert run(root, PIECE, OUTPUT).returncode == 0
    piece = root / "visual" / "pieces" / PIECE / "piece.yaml"
    text = piece.read_text(encoding="utf-8").replace("- dark", "- light")
    piece.write_text(text.replace("64", "32"), encoding="utf-8")
    before = produced(root)
    with monkeypatch.context() as patch:
        failing(patch, write={file})
        shown = run(root, PIECE, OUTPUT)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr == f"error: {PRODUCED}/{file} could not be written: {FULL}\n"
    assert produced(root) == before
    assert run(root, PIECE, OUTPUT).returncode == 0
    assert sorted(produced(root)) == ["default.png", "record.yaml"]


def test_a_failed_first_run_records_no_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = producing_project(tmp_path)
    with monkeypatch.context() as patch:
        failing(patch, write={"record.yaml"})
        assert run(root, PIECE, OUTPUT).returncode == 1
    assert not (root / CONFIG).exists()
    assert not (root / "visual" / "pieces" / PIECE / "produced").exists()


@pytest.mark.process(
    "produce's end-to-end test: the command as a process of its own, where no test has "
    "registered a producer, refusing the one the piece names, with its exit code"
)
def test_an_unknown_producer_is_refused_by_the_command_run_as_a_process(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    shown = subprocess.run(
        [sys.executable, str(SCRIPT), PIECE, OUTPUT],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert shown.returncode == 1, shown.stdout
    assert shown.stderr.startswith("error: there is no producer `square` (the producers: ")
    assert not (root / CONFIG).exists()
    assert not (root / PRODUCED).exists()
