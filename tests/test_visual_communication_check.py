"""`pkit visual check` (visual-communication DEC-002 points 6 and 7, DEC-005 point 13): the
validator of `pkit validate`, under the query contract — `--json` prints the findings
document and exits 0; without it, it exits 1 when a finding fails. Its findings are
`test_visual_communication_checks.py`'s; here, the command: the findings record read while
its key verifies, the validation's bound, the time it takes, and one run through `pkit
validate`'s runner as a process of its own."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests import visual_communication_producer as producer
from tests.adopter_repo import MakeAdopterRepo
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    lay_out_drawing,
    write_content,
    write_picture,
)
from tests.visual_communication_project import importable

check, render, svg, seam, framing = load(
    "visual-communication", "check.py", "render.py", "plugins.svg", "plugins.seam", "framing"
)

# The picture the piece declares and nobody made: the producer's check reports it once,
# at the record that is missing.
MISSING = f"{PIECE_FOLDER}/produced/square/record.yaml#produced.square"

# A word with no place to break, wider than the figure: its text overflows its box.
LONG_WORD = "Unbreakable" * 40

BRAND_FONT = "visual/libraries/test-brand/1.0.0/fonts/SourceSansPro-Regular.otf"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a render makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def run(root: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return run_main(check, *args, cwd=root, env={"PKIT_COMMAND_DEADLINE": None, **env})


def document(root: Path, *args: str, **env: str) -> dict[str, Any]:
    shown = run(root, "--json", *args, **env)
    assert shown.returncode == 0, shown.stderr
    return json.loads(shown.stdout)


def drawn(tmp_path: Path) -> Path:
    """The skeleton piece with its picture, rendered: its findings record committed."""
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    assert run_main(render, PIECE, cwd=root).returncode == 0
    return root


# --- the query contract -------------------------------------------------------------------------


def test_json_prints_the_document_and_exits_0_though_a_finding_fails(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    found = document(root)
    assert found["summary"] == [
        "1 piece(s) in `visual`: the scenes of 0 read from their findings record, of 1 "
        "computed now, of 0 not checked."
    ]
    errors = [f for f in found["findings"] if f["severity"] == "error"]
    [missing] = [f for f in errors if f["label"] == "produced-record-missing"]
    assert missing["location"] == MISSING
    assert "pkit visual produce flow square" in missing["message"]


def test_without_json_it_lists_the_findings_and_exits_1_when_one_fails(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    shown = run(root)
    assert shown.returncode == 1
    lines = shown.stdout.splitlines()
    assert lines[0].startswith("1 piece(s) in `visual`")
    assert f"  error   {MISSING}  [produced-record-missing]" in lines


def test_a_font_file_that_cannot_be_read_fails_as_a_missing_font_does(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    (root / BRAND_FONT).write_bytes(b"not a font")
    [found] = [f for f in document(root)["findings"] if f["label"] == "font-missing"]
    assert found["severity"] == "error"
    assert "cannot be read" in found["message"]


def test_a_piece_whose_findings_do_not_fail_exits_0(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stdout
    assert shown.stdout.splitlines()[0] == (
        "the piece `flow` in `visual`: the scenes of 0 read from their findings record, of 1 "
        "computed now, of 0 not checked."
    )
    assert "  info    " in shown.stdout


# --- the findings record ------------------------------------------------------------------------


def test_the_record_is_read_while_its_key_verifies_and_the_scenes_computed_after(
    tmp_path: Path,
) -> None:
    root = drawn(tmp_path)
    assert "the scenes of 1 read from their findings record" in document(root)["summary"][0]
    write_content(root, head="Plan the work again.")
    assert "of 1 computed now" in document(root)["summary"][0]


def test_a_record_that_no_longer_verifies_is_not_believed(tmp_path: Path) -> None:
    root = drawn(tmp_path)
    (root / PIECE_FOLDER / "produced" / "square" / "record.yaml").unlink()
    found = document(root)
    assert "of 1 computed now" in found["summary"][0]
    assert ("produced-record-missing", MISSING) in [
        (f["label"], f["location"]) for f in found["findings"]
    ]


def test_past_the_validations_bound_a_piece_without_a_record_fails_as_not_checked(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    found = document(root, PKIT_COMMAND_DEADLINE=str(time.time()))
    assert [(f["severity"], f["location"], f["label"]) for f in found["findings"]] == [
        ("error", f"{PIECE_FOLDER}/findings.yaml", "not-checked")
    ]
    # A record that verifies is read whatever the bound.
    assert run_main(render, PIECE, cwd=root).returncode == 0
    found = document(root, PKIT_COMMAND_DEADLINE=str(time.time()))
    assert "not-checked" not in [f["label"] for f in found["findings"]]


def test_a_final_piece_with_only_a_fact_at_its_lock_exits_0(tmp_path: Path) -> None:
    lock = {"foundations": "1.0.0", "tests": "1.0.0"}
    root = drawing_project(tmp_path, state="final", picture=False, lock=lock)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stdout
    lines = shown.stdout.splitlines()
    assert lines[0] == (
        "the piece `flow` in `visual`: the scenes of 0 read from their findings record, of 0 "
        "computed now, of 0 not checked, of 1 left out as final."
    )
    assert any("[lock-incomplete]" in line and line.startswith("  info") for line in lines)


def test_it_checks_the_skeleton_piece_within_a_few_seconds(tmp_path: Path) -> None:
    """The validation runs it on every `pkit validate`: computing the skeleton piece's
    scenes, and reading them from its record, each take well under its bound."""
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    for case, said in (("computed", "of 1 computed now"), ("read", "of 1 read from")):
        started = time.monotonic()
        found = document(root)
        took = time.monotonic() - started
        assert said in found["summary"][0]
        assert took < 3.0, f"{case}: {took:.2f} s"
        assert run_main(render, PIECE, cwd=root).returncode == 0


# --- through pkit validate ----------------------------------------------------------------------


@pytest.mark.process(
    "the validator's end-to-end test: `pkit validate` finds the `visual-communication:check` "
    "member, starts its script as a process of its own and reads its document and its exit"
)
def test_it_is_the_check_member_of_pkit_validate(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = make_adopter_repo(capabilities=("visual-communication",))
    script = repo.root / ".pkit/capabilities/visual-communication/scripts/check.py"
    body = script.read_text(encoding="utf-8").split("\n", 1)[1]
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    # No produced picture: the test producer is registered in this process alone, so the
    # check's own process would not know it (DEC-005 point 12).
    root = lay_out_drawing(repo.root, picture=False)
    only = ["--color", "never", "validate", "--only", "visual-communication:check"]
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 0, result.output
    assert "visual-communication:check" in result.output
    write_content(root, body={"use": "tests/steps", "steps": [{"id": "plan", "head": LONG_WORD}]})
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 1, result.output
    assert "text-overflow" in result.output
