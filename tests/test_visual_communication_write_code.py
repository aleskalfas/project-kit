"""`pkit visual write-code <name>` (visual-communication DEC-005 point 7, DEC-006 points 4 and
5): what it prints, what it writes, and how it refuses. Run in this process
(`tests/in_process.py`), but for one end-to-end test of the command as a process."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.in_process import load, run_main
from tests.visual_communication_project import (
    CAPABILITY,
    CONFIG,
    FOUNDATIONS,
    TEST_BRAND,
    bound,
    copy_library,
    importable,
    project,
    write,
    yaml_text,
)
from tests.visual_communication_writes import FULL, failing

script, css = load("visual-communication", "write-code.py", "plugins.css")

SCRIPT = CAPABILITY / "scripts" / "write-code.py"
DECLARATION = "visual/code/brand-css.yaml"
LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0"}


@pytest.fixture(autouse=True)
def _writer_importable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The writer stands in for the import the command makes when it runs it, for the
    length of the test."""
    importable(monkeypatch, css)


def declare(root: Path, **fields: object) -> None:
    data = {"writer": "css", "form": 1, "brand": "test-brand", "lock": dict(LOCK)}
    data.update({"out": "web/brand.css", **fields})
    write(root / DECLARATION, yaml_text(bound("code", **data)))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    found = project(tmp_path)
    copy_library(found, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(found, TEST_BRAND, "test-brand", "1.0.0")
    declare(found)
    return found


def run(root: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=cwd or root)


def test_it_writes_the_code_and_its_record_and_prints_the_losses(root: Path) -> None:
    shown = run(root, "brand-css")
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines() == [
        "wrote web/brand.css and its record web/brand.css.record.yaml",
        "loss: css left out `type.body`: form 1 of the css writer has no form for a "
        "typography value",
        "loss: css left out `type.heading`: form 1 of the css writer has no form for a "
        "typography value",
        f"accept a loss under `accept-losses` in {DECLARATION} to stop it being reported",
    ]
    assert (root / "web/brand.css").is_file()
    assert (root / "web/brand.css.record.yaml").is_file()


def test_run_again_it_writes_nothing_and_says_so(root: Path) -> None:
    run(root, "brand-css")
    shown = run(root / "web", "brand-css", cwd=root / "web")
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines()[0] == (
        "web/brand.css is up to date: its record verifies, so nothing was written"
    )


def test_accepted_losses_are_not_printed(root: Path) -> None:
    accepted = [
        {"plugin": "css", "what": path, "reason": "Pages set their own type."}
        for path in ("type.body", "type.heading")
    ]
    declare(root, **{"accept-losses": accepted})
    shown = run(root, "brand-css")
    assert shown.stdout.splitlines() == [
        "wrote web/brand.css and its record web/brand.css.record.yaml"
    ]


def test_it_never_records_a_location(root: Path) -> None:
    run(root, "brand-css")
    assert not (root / CONFIG).exists()


@pytest.mark.parametrize(
    ("name", "why"),
    [
        ("missing", "there is no declaration visual/code/missing.yaml"),
        ("Brand", "is not the name of a declaration"),
    ],
)
def test_it_refuses_a_name_that_names_no_declaration(root: Path, name: str, why: str) -> None:
    shown = run(root, name)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert why in shown.stderr


def test_it_refuses_where_there_is_no_visual_work(tmp_path: Path) -> None:
    shown = run(project(tmp_path), "brand-css")
    assert shown.returncode == 1
    assert "there is no visual work here" in shown.stderr


def test_it_refuses_a_lock_that_does_not_hold_and_writes_nothing(root: Path) -> None:
    declare(root, lock={"test-brand": "1.0.0"})
    shown = run(root, "brand-css")
    assert shown.returncode == 1
    assert "the lock names no version of `foundations`" in shown.stderr
    assert not (root / "web").exists()


def test_a_write_that_fails_is_an_error_naming_the_file_and_leaves_nothing(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as patch:
        failing(patch, write={"brand.css.record.yaml"})
        shown = run(root, "brand-css")
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr == f"error: web/brand.css.record.yaml could not be written: {FULL}\n"
    assert not (root / "web").exists()


def test_a_name_is_required(root: Path) -> None:
    shown = run(root)
    assert shown.returncode == 2
    assert "name" in shown.stderr


@pytest.mark.process(
    "the command's end-to-end test: the script as a process of its own, importing its writer "
    "when it runs, from the project root it finds above its working directory"
)
def test_the_command_writes_the_code_as_a_process_of_its_own(root: Path) -> None:
    (root / "web").mkdir()
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "brand-css"],
        cwd=root / "web",
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("wrote web/brand.css and its record web/brand.css.record.yaml\n")
    assert (root / "web/brand.css").read_text(encoding="utf-8").count(" {\n") == 5
