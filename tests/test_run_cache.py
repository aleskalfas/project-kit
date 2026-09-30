"""The run cache (#1144): what one run of `pkit validate` computed, shared with
the `pkit` commands the run starts.

- a run opens a fresh directory, names it in the environment, and removes it at
  the end; a run inside a run keeps the one already named;
- a value written is read back whole, in any process the run starts; outside a
  run nothing is kept; an entry that cannot be read, or a value JSON cannot
  hold, is a miss, never an error.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from project_kit import run_cache


@pytest.fixture(autouse=True)
def no_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(run_cache.CACHE_ENV, raising=False)


def test_a_run_names_a_fresh_directory_for_its_length_then_removes_it() -> None:
    with run_cache.opened():
        directory = Path(os.environ[run_cache.CACHE_ENV])
        assert directory.is_dir()
        with run_cache.opened():  # a run inside the run keeps the one named
            assert os.environ[run_cache.CACHE_ENV] == str(directory)
        assert directory.is_dir()
    assert run_cache.CACHE_ENV not in os.environ
    assert not directory.exists()


def test_a_value_written_in_a_run_is_read_back_whole_in_any_process_it_starts() -> None:
    with run_cache.opened():
        run_cache.write("point a", {"value": ["x", 1], "why": ""})
        assert run_cache.read("point a") == {"value": ["x", 1], "why": ""}
        assert run_cache.read("point b") is None
        reads = "from project_kit import run_cache; print(run_cache.read('point a'))"
        child = subprocess.run(
            [sys.executable, "-c", reads], capture_output=True, text=True, check=True
        )
        assert child.stdout.strip() == "{'value': ['x', 1], 'why': ''}"


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
