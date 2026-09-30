"""The run cache (#1144): what one run of `pkit validate` computed, shared with
the `pkit` commands the run starts.

- a run opens a fresh directory, names it in the environment, and removes it at
  the end; a run inside a run keeps the one already named; a run that cannot
  make one goes without, and every reader computes for itself;
- a value written is read back whole, in the run's process and in any process
  the run starts through the command runner; a process outside the run — a
  plain child, a shell a run's variables were left in — neither reads nor
  writes it, and a run opened there makes a fresh one; outside a run nothing is
  kept; an entry that cannot be read, or a value JSON cannot hold, is a miss,
  never an error.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from project_kit import command_runner, run_cache
from project_kit.command_runner import Ending, run_command

# A command that prints what the run holds for `point a`, as JSON.
_READS_THE_CACHE = (
    "import json\n"
    "from project_kit import run_cache\n"
    "print(json.dumps({'value': run_cache.read('point a')}))\n"
)


def _reader(path: Path) -> Path:
    """A command reading the run cache, under this interpreter, so it imports the
    module under test."""
    path.write_text(f"#!{sys.executable}\n{_READS_THE_CACHE}", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_a_run_names_a_fresh_directory_for_its_length_then_removes_it() -> None:
    with run_cache.opened():
        directory = Path(os.environ[run_cache.CACHE_ENV])
        assert directory.is_dir()
        with run_cache.opened():  # a run inside the run keeps the one named
            assert os.environ[run_cache.CACHE_ENV] == str(directory)
        assert directory.is_dir()
    assert run_cache.CACHE_ENV not in os.environ
    assert not directory.exists()


def test_a_value_written_in_a_run_is_read_back_whole_by_the_processes_it_starts(
    tmp_path: Path,
) -> None:
    reader = _reader(tmp_path / "reader.py")
    with run_cache.opened():
        run_cache.write("point a", {"value": ["x", 1], "why": ""})
        assert run_cache.read("point a") == {"value": ["x", 1], "why": ""}
        assert run_cache.read("point b") is None
        # A command the run starts through the runner runs inside it, and reads it.
        run = run_command(reader, [], cwd=tmp_path)
        assert run.ending is Ending.ANSWERED, run.stderr
        assert run.document == {"value": {"value": ["x", 1], "why": ""}}
        # A process started any other way is not the run's, whatever it inherits.
        plain = subprocess.run([str(reader)], capture_output=True, text=True, check=True)
        assert plain.stdout.strip() == '{"value": null}'


def test_outside_a_run_nothing_is_kept() -> None:
    run_cache.write("point a", {"value": 1})
    assert run_cache.read("point a") is None


def test_what_cannot_be_kept_or_read_is_a_miss() -> None:
    with run_cache.opened():
        run_cache.write("point a", {"value": object()})  # JSON cannot hold it
        assert run_cache.read("point a") is None
        run_cache.write("point b", {"value": 1})
        [entry] = Path(os.environ[run_cache.CACHE_ENV]).glob("*.json")
        entry.write_text("{half", encoding="utf-8")
        assert run_cache.read("point b") is None


def test_a_directory_a_shell_kept_from_another_run_is_neither_read_nor_joined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A run's directory, and its deadline, left in a shell after the run: its
    # strays directory is gone, so nothing here runs inside that run.
    stale = tmp_path / "stale"
    with run_cache.opened():
        run_cache.write("point a", {"value": "stale"})
        [entry] = Path(os.environ[run_cache.CACHE_ENV]).glob("*.json")
        stale.mkdir()
        (stale / entry.name).write_text(entry.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv(run_cache.CACHE_ENV, str(stale))
    monkeypatch.setenv(command_runner.DEADLINE_ENV, "4102444800.000")
    monkeypatch.setenv(command_runner.STRAYS_ENV, str(tmp_path / "strays-removed"))
    assert run_cache.read("point a") is None
    run_cache.write("point b", {"value": 1})
    assert sorted(p.name for p in stale.iterdir()) == [entry.name]  # nothing written there
    with run_cache.opened():  # a run opened in that shell makes a fresh one
        fresh = os.environ[run_cache.CACHE_ENV]
        assert fresh != str(stale)
        assert run_cache.read("point a") is None
    assert os.environ[run_cache.CACHE_ENV] == str(stale)  # the shell's, as it was
    assert not Path(fresh).exists()


def test_a_run_that_cannot_make_its_directory_goes_without_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refused(*args: object, **kwargs: object) -> str:
        raise PermissionError("no temporary directory")

    monkeypatch.setattr(tempfile, "mkdtemp", refused)
    monkeypatch.setenv(run_cache.CACHE_ENV, str(tmp_path / "left-over"))
    with run_cache.opened():
        # No cache, and none passed on: a left-over name is not handed to the
        # commands the run starts.
        assert run_cache.CACHE_ENV not in os.environ
        run_cache.write("point a", {"value": 1})
        assert run_cache.read("point a") is None
    assert os.environ[run_cache.CACHE_ENV] == str(tmp_path / "left-over")
