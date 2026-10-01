"""`scripts/check.sh`'s test step (#1182).

- the suite runs in parallel workers, `-n auto` or the count
  `PKIT_TEST_WORKERS` names, and then the tests marked `serial` in one
  process; a serial pass with nothing marked passes, a failing one fails the
  step;
- at most two full suites run at once on a machine: a third waits, says so and
  names the two it waits for, and takes a slot once one frees — when a run
  ends, killed included;
- when the slots cannot be opened, the step says so and runs the suite anyway.

`check.sh` runs here for real, against a stub `uv` first on PATH, so no test
runs the suite: the stub's `pytest` records its arguments and, on the parallel
pass, holds until the test lets it go; its `python` is this interpreter, so a
slot is taken with a real lock; every other command it is handed passes.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CHECK = REPO / "scripts" / "check.sh"

# The stand-in for `uv run [--flag ...] <command> [arg ...]`: `python` is this
# interpreter; `pytest` logs its arguments and, on the parallel pass, holds
# until the release file exists; anything else passes.
STUB_UV = """#!/bin/sh
shift
while [ "${{1#-}}" != "$1" ]; do shift; done
case "$1" in
  python) shift; exec "{python}" "$@" ;;
  pytest)
    shift
    echo "$*" >> "$STUB_LOG"
    case "$*" in
      *"not serial"*)
        while [ ! -e "$STUB_RELEASE" ]; do sleep 0.1; done
        exit 0 ;;
    esac
    exit "${{STUB_SERIAL_STATUS:-0}}" ;;
  *) exit 0 ;;
esac
"""

WAIT_SECONDS = 20


class Checkout:
    """A git checkout carrying `scripts/check.sh`, and the stub `uv` it runs."""

    def __init__(self, root: Path) -> None:
        self.root = root / "checkout"
        (self.root / "scripts").mkdir(parents=True)
        shutil.copy2(CHECK, self.root / "scripts" / "check.sh")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        stub_bin = root / "bin"
        stub_bin.mkdir()
        uv = stub_bin / "uv"
        uv.write_text(STUB_UV.format(python=sys.executable), encoding="utf-8")
        uv.chmod(0o755)
        self.log = root / "pytest.log"
        self.release = root / "release"
        self.cache = root / "cache"
        self.env = {
            **{k: v for k, v in os.environ.items() if k != "PKIT_TEST_WORKERS"},
            "PATH": f"{stub_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "XDG_CACHE_HOME": str(self.cache),
            "STUB_LOG": str(self.log),
            "STUB_RELEASE": str(self.release),
        }
        self.outputs = root / "outputs"
        self.outputs.mkdir()
        self.runs: list[subprocess.Popen[bytes]] = []

    def check(self, **env: str) -> subprocess.CompletedProcess[str]:
        """Run `check.sh` to the end; the parallel pass is let go at once."""
        self.release.touch()
        return subprocess.run(
            ["bash", "scripts/check.sh"],
            cwd=self.root,
            env={**self.env, **env},
            capture_output=True,
            text=True,
            timeout=WAIT_SECONDS,
        )

    def start(self) -> tuple[subprocess.Popen[bytes], Path]:
        """Start `check.sh` in a process group of its own; its output goes to a file."""
        output = self.outputs / f"run-{len(self.runs) + 1}.txt"
        with output.open("wb") as sink:
            run = subprocess.Popen(
                ["bash", "scripts/check.sh"],
                cwd=self.root,
                env=self.env,
                stdout=sink,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        self.runs.append(run)
        return run, output

    def parallel_passes(self) -> int:
        """How many parallel passes have started."""
        if not self.log.exists():
            return 0
        return sum("not serial" in line for line in self.log.read_text().splitlines())


def _until(condition: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail(f"timed out waiting for {what}")
        time.sleep(0.05)


@pytest.fixture
def checkout(tmp_path: Path) -> Iterator[Checkout]:
    made = Checkout(tmp_path)
    yield made
    made.release.touch()
    for run in made.runs:
        if run.poll() is None:
            os.killpg(run.pid, signal.SIGKILL)
            run.wait()


@pytest.mark.parametrize(("workers", "expected"), [(None, "-n auto"), ("3", "-n 3"), ("0", "-n 0")])
def test_the_suite_runs_in_parallel_workers_then_the_serial_tests_in_one_process(
    checkout: Checkout, workers: str | None, expected: str
) -> None:
    env = {} if workers is None else {"PKIT_TEST_WORKERS": workers}
    done = checkout.check(**env)

    assert done.returncode == 0, done.stdout + done.stderr
    assert checkout.log.read_text().splitlines() == [
        f"-q {expected} -m not serial",
        "-q -m serial",
    ]
    assert "-- tests: ok" in done.stdout


@pytest.mark.parametrize(
    ("status", "verdict"),
    [("5", "-- tests: ok"), ("1", "-- tests: FAILED")],
    ids=["nothing-marked-serial", "a-serial-test-fails"],
)
def test_the_serial_pass_passes_with_nothing_marked_and_fails_the_step_on_a_failure(
    checkout: Checkout, status: str, verdict: str
) -> None:
    done = checkout.check(STUB_SERIAL_STATUS=status)

    assert verdict in done.stdout
    assert (done.returncode == 0) == (status == "5")


def test_a_third_full_suite_waits_for_a_slot_names_the_two_it_waits_for_and_then_runs(
    checkout: Checkout,
) -> None:
    first, _ = checkout.start()
    second, _ = checkout.start()
    _until(lambda: checkout.parallel_passes() == 2, "two suites to start")

    third, said = checkout.start()
    _until(lambda: "waiting for a test slot" in said.read_text(), "the third to wait")
    waiting = said.read_text()
    assert f"pid {first.pid} in " in waiting
    assert f"pid {second.pid} in " in waiting
    assert str(checkout.cache / "pkit") in waiting
    assert checkout.parallel_passes() == 2

    checkout.release.touch()
    for run in (first, second, third):
        assert run.wait(timeout=WAIT_SECONDS) == 0
    assert "took test slot" in said.read_text()
    assert checkout.parallel_passes() == 3


def test_a_run_that_is_killed_frees_its_slot(checkout: Checkout) -> None:
    first, _ = checkout.start()
    second, _ = checkout.start()
    _until(lambda: checkout.parallel_passes() == 2, "two suites to start")
    third, said = checkout.start()
    _until(lambda: "waiting for a test slot" in said.read_text(), "the third to wait")

    os.killpg(first.pid, signal.SIGKILL)
    first.wait()

    _until(lambda: checkout.parallel_passes() == 3, "the third to take the freed slot")
    checkout.release.touch()
    assert second.wait(timeout=WAIT_SECONDS) == 0
    assert third.wait(timeout=WAIT_SECONDS) == 0


def test_the_suite_runs_without_the_limit_when_the_slots_cannot_be_opened(
    checkout: Checkout,
) -> None:
    checkout.cache.write_text("a file where the cache directory would be\n")

    done = checkout.check()

    assert done.returncode == 0, done.stdout + done.stderr
    assert "cannot open the test slots" in done.stdout
    assert checkout.parallel_passes() == 1
