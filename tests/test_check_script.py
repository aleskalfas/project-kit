"""`scripts/check.sh`'s type, numbering, prose-lint and test steps.

The type step (PRJ-010):

- runs `scripts/pyright_ratchet.py` after the lint and the format check and
  before the tests;
- fails the run when the ratchet fails, and the checks after it still run.

The numbering check of decision records (#1417) runs `pkit decisions
check-diff` as a line of its own among the diff-scoped checks, right after the
migration check; a failure fails the run.

The prose lint (#1415) runs `scripts/prose_lint.py` among the diff-scoped
checks, after the friction change check; a finding fails the run.

The deployed agents' check (#1559) runs `scripts/check_deployed_agents.py`
right after `pkit validate`, before the diff-scoped checks; a finding fails the
run. The pages' console fences (#1807, #2098) run the doc-examples capability's
run, `.pkit/capabilities/doc-examples/scripts/run-examples.py`, right after it;
a failure fails the run. The pages' contents lists (#2053) are checked
by `scripts/page_contents.py` right after the console fences; a stale list fails
the run.

The test step (#1182):

- the suite runs in parallel workers, `-n auto` or the count
  `PKIT_TEST_WORKERS` names, and then the tests marked `serial` in one
  process; a serial pass with nothing marked passes, a failing one fails the
  step;
- the parallel pass prints its 30 slowest tests, whatever the count of
  workers (#2309);
- at most two full suites run at once on a machine: a third waits, says so and
  names the two it waits for, and takes a slot once one frees — when a run
  ends, killed included;
- when the slots cannot be opened, the step says so and runs the suite anyway.

The short check (#1798, ADR-067): `--short` runs every line the full run runs, in
the same order, but the suite, and in its place only the tests marked `answers`;
nothing marked passes, a failing one fails the run. Any other argument is
refused before a check runs.

The parts of a full run (#2308, ADR-078 point 1): `--rest` runs every line the whole
run runs, in the same order, but the parallel pass, with the tests marked `serial`
in the test step's place; `--shard i/N` runs only the parallel pass, cut to its
share, after taking a slot. Together they run what the whole run runs. A slice
whose share holds no test, pytest's exit 5, fails; any other failure does too.
Where `$PKIT_TEST_REPORTS` names a folder, each pass reports into a folder of its
own, and a slice reports its cut even where it names none.

`check.sh` runs here for real, against a stub `uv` first on PATH, so no test
runs the suite or pyright: the stub records every command it is handed; its
`pytest` records its arguments and, on the parallel pass, holds until the test
lets it go; its `python` is this interpreter, so a slot is taken with a real
lock, except for the ratchet, the prose lint, the deployed agents' check, the
console fences and the contents lists, which exit as the test says; the
numbering check exits as the test says too; every other command passes.
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
#: The doc-examples capability's run, started by its path (doc-examples DEC-001 point 9).
RUN_EXAMPLES = ".pkit/capabilities/doc-examples/scripts/run-examples.py"

# The stand-in for `uv run [--flag ...] <command> [arg ...]`: it logs each
# command; `python` is this interpreter, but for the ratchet, which exits with
# $STUB_TYPES_STATUS, the prose lint, which exits with $STUB_PROSE_STATUS, the
# deployed agents' check, which exits with $STUB_AGENTS_STATUS, the console
# fences, which exit with $STUB_CONSOLE_STATUS, and the contents lists, which exit
# with $STUB_CONTENTS_STATUS;
# `pkit decisions check-diff` exits with $STUB_NUMBERING_STATUS; `pytest` logs its
# arguments and, on the parallel pass, holds until the release file exists and
# then exits with $STUB_PARALLEL_STATUS; anything else passes.
STUB_UV = """#!/bin/sh
shift
while [ "${{1#-}}" != "$1" ]; do shift; done
echo "$*" >> "$STUB_STEPS"
case "$1" in
  python)
    shift
    case "$1" in
      scripts/pyright_ratchet.py) exit "${{STUB_TYPES_STATUS:-0}}" ;;
      scripts/prose_lint.py) exit "${{STUB_PROSE_STATUS:-0}}" ;;
      scripts/check_deployed_agents.py) exit "${{STUB_AGENTS_STATUS:-0}}" ;;
      .pkit/capabilities/doc-examples/scripts/run-examples.py) exit "${{STUB_CONSOLE_STATUS:-0}}" ;;
      scripts/page_contents.py) exit "${{STUB_CONTENTS_STATUS:-0}}" ;;
    esac
    exec "{python}" "$@" ;;
  pkit)
    case "$2 $3" in
      "decisions check-diff") exit "${{STUB_NUMBERING_STATUS:-0}}" ;;
    esac
    exit 0 ;;
  pytest)
    shift
    echo "$*" >> "$STUB_LOG"
    case "$*" in
      *"not serial"*)
        while [ ! -e "$STUB_RELEASE" ]; do sleep 0.1; done
        exit "${{STUB_PARALLEL_STATUS:-0}}" ;;
      *"-m answers"*) exit "${{STUB_ANSWERS_STATUS:-0}}" ;;
    esac
    exit "${{STUB_SERIAL_STATUS:-0}}" ;;
  *) exit 0 ;;
esac
"""

WAIT_SECONDS = 20

#: The parallel pass as a local run, which names no count of workers, hands it to `uv`.
PARALLEL_PASS = "pytest -q -n auto --durations=30 -m not serial"


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
        self.steps = root / "steps.log"
        self.release = root / "release"
        self.cache = root / "cache"
        self.env = {
            **{k: v for k, v in os.environ.items() if k != "PKIT_TEST_WORKERS"},
            "PATH": f"{stub_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "XDG_CACHE_HOME": str(self.cache),
            "STUB_LOG": str(self.log),
            "STUB_STEPS": str(self.steps),
            "STUB_RELEASE": str(self.release),
        }
        self.outputs = root / "outputs"
        self.outputs.mkdir()
        self.runs: list[subprocess.Popen[bytes]] = []

    def check(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        """Run `check.sh` to the end; the parallel pass is let go at once."""
        self.release.touch()
        return subprocess.run(
            ["bash", "scripts/check.sh", *args],
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


def test_the_type_check_runs_after_the_lint_and_format_and_before_the_tests(
    checkout: Checkout,
) -> None:
    done = checkout.check()

    assert done.returncode == 0, done.stdout + done.stderr
    assert "-- types: ok" in done.stdout
    steps = checkout.steps.read_text().splitlines()
    order = [
        "ruff check .",
        "ruff format --check .",
        "python scripts/pyright_ratchet.py",
        PARALLEL_PASS,
    ]
    positions = [steps.index(step) for step in order]
    assert positions == sorted(positions)


def test_a_failing_type_check_fails_the_run_and_the_checks_after_it_still_run(
    checkout: Checkout,
) -> None:
    done = checkout.check(STUB_TYPES_STATUS="1")

    assert done.returncode == 1
    assert "-- types: FAILED" in done.stdout
    assert "-- tests: ok" in done.stdout
    assert "-- changelog lint: ok" in done.stdout


def test_the_numbering_check_runs_after_the_migration_check_and_a_failure_fails_the_run(
    checkout: Checkout,
) -> None:
    done = checkout.check(STUB_NUMBERING_STATUS="1")

    assert done.returncode == 1
    assert "-- record numbering: FAILED" in done.stdout
    assert "-- friction check: ok" in done.stdout
    steps = checkout.steps.read_text().splitlines()
    numbering = steps.index("pkit decisions check-diff")
    assert numbering == steps.index("pkit migrations check-diff") + 1
    assert steps.index("pkit validate") < numbering


def test_the_prose_lint_runs_after_the_friction_check_and_a_finding_fails_the_run(
    checkout: Checkout,
) -> None:
    done = checkout.check(STUB_PROSE_STATUS="1")

    assert done.returncode == 1
    assert "-- prose lint: FAILED" in done.stdout
    steps = checkout.steps.read_text().splitlines()
    assert steps.index("python scripts/prose_lint.py") == steps.index("pkit friction check") + 1


def test_the_deployed_agents_check_runs_after_validate_and_a_finding_fails_the_run(
    checkout: Checkout,
) -> None:
    done = checkout.check(STUB_AGENTS_STATUS="1")

    assert done.returncode == 1
    assert "-- deployed agents: FAILED" in done.stdout
    assert "-- changelog lint: ok" in done.stdout
    steps = checkout.steps.read_text().splitlines()
    check = steps.index("python scripts/check_deployed_agents.py")
    assert check == steps.index("pkit validate") + 1
    assert check < steps.index("pkit migrations check-diff")


def test_the_console_fences_run_after_the_deployed_agents_and_a_failure_fails_the_run(
    checkout: Checkout,
) -> None:
    done = checkout.check(STUB_CONSOLE_STATUS="1")

    assert done.returncode == 1
    assert "-- console fences: FAILED" in done.stdout
    assert "-- changelog lint: ok" in done.stdout
    steps = checkout.steps.read_text().splitlines()
    fences = steps.index(f"python {RUN_EXAMPLES}")
    assert fences == steps.index("python scripts/check_deployed_agents.py") + 1
    assert fences < steps.index("pkit migrations check-diff")


def test_the_contents_lists_run_after_the_console_fences_and_a_stale_one_fails_the_run(
    checkout: Checkout,
) -> None:
    done = checkout.check(STUB_CONTENTS_STATUS="1")

    assert done.returncode == 1
    assert "-- contents lists: FAILED" in done.stdout
    assert "-- changelog lint: ok" in done.stdout
    steps = checkout.steps.read_text().splitlines()
    contents = steps.index("python scripts/page_contents.py")
    assert contents == steps.index(f"python {RUN_EXAMPLES}") + 1
    assert contents < steps.index("pkit migrations check-diff")


@pytest.mark.parametrize(
    ("workers", "expected"),
    [(None, "-n auto"), ("8", "-n 8"), ("3", "-n 3"), ("0", "-n 0")],
    ids=["local", "ci", "three", "one-process"],
)
def test_the_suite_runs_in_parallel_workers_printing_its_slowest_then_the_serial_tests(
    checkout: Checkout, workers: str | None, expected: str
) -> None:
    """The parallel pass prints its 30 slowest tests in every run, CI's eight workers and
    a local run's `-n auto` alike; the serial pass prints none (#2309)."""
    env = {} if workers is None else {"PKIT_TEST_WORKERS": workers}
    done = checkout.check(**env)

    assert done.returncode == 0, done.stdout + done.stderr
    assert checkout.log.read_text().splitlines() == [
        f"-q {expected} --durations=30 -m not serial",
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


# --- the short check (#1798, ADR-067) -------------------------------------------------


def test_the_short_check_runs_every_line_but_the_suite_and_the_tests_marked_answers(
    checkout: Checkout,
) -> None:
    full = checkout.check()
    full_steps = checkout.steps.read_text().splitlines()
    checkout.steps.unlink()
    checkout.log.unlink()

    done = checkout.check("--short")

    assert full.returncode == 0, full.stdout + full.stderr
    assert done.returncode == 0, done.stdout + done.stderr
    steps = checkout.steps.read_text().splitlines()
    suite = {PARALLEL_PASS, "pytest -q -m serial"}
    # The full run's test step also takes a slot, through `python -`.
    assert steps == [
        "pytest -q -m answers" if step == PARALLEL_PASS else step
        for step in full_steps
        if step != "pytest -q -m serial" and not step.startswith("python - ")
    ]
    assert not suite & set(steps)
    assert checkout.log.read_text().splitlines() == ["-q -m answers"]
    assert "the short check: the test suite was skipped" in done.stdout


@pytest.mark.parametrize(
    ("status", "ok"), [("5", True), ("1", False)], ids=["nothing-marked", "a-test-fails"]
)
def test_the_short_check_passes_with_nothing_marked_and_fails_on_a_failure(
    checkout: Checkout, status: str, ok: bool
) -> None:
    done = checkout.check("--short", STUB_ANSWERS_STATUS=status)

    assert (done.returncode == 0) == ok
    assert ("FAILED" in done.stdout) != ok


@pytest.mark.parametrize(
    "args",
    [
        ("--quick",),
        ("--short", "--short"),
        ("short",),
        ("--rest", "--short"),
        ("--shard",),
        ("--shard", "0/2"),
        ("--shard", "3/2"),
        ("--shard", "1/0"),
        ("--shard", "a/b"),
        ("--shard", "1/2", "--rest"),
        ("--shard=1/2",),
        ("--rest", "--shard", "1/2"),
    ],
)
def test_any_other_argument_is_refused_before_a_check_runs(
    checkout: Checkout, args: tuple[str, ...]
) -> None:
    done = checkout.check(*args)

    assert done.returncode == 2
    assert "usage: scripts/check.sh [--short | --rest | --shard i/N]" in done.stderr
    assert not checkout.steps.exists()


# --- the parts of a full run (#2308, ADR-078) ------------------------------------------

#: What taking a test slot hands `uv`: `python -` and the slot's arguments.
TAKES_A_SLOT = "python - "


def _ran(checkout: Checkout, *args: str, **env: str) -> list[str]:
    """What `check.sh` with `args` hands `uv`, once it ran to the end and passed."""
    if checkout.steps.exists():
        checkout.steps.unlink()
    done = checkout.check(*args, **env)
    assert done.returncode == 0, done.stdout + done.stderr
    return checkout.steps.read_text().splitlines()


def test_the_remainder_runs_every_line_but_the_parallel_pass(checkout: Checkout) -> None:
    whole = _ran(checkout)

    rest = _ran(checkout, "--rest")

    assert rest == [
        step for step in whole if step != PARALLEL_PASS and not step.startswith(TAKES_A_SLOT)
    ]
    assert "pytest -q -m serial" in rest


def test_a_slice_runs_its_share_of_the_parallel_pass_and_nothing_else(
    checkout: Checkout,
) -> None:
    ran = _ran(checkout, "--shard", "2/3")

    assert len(ran) == 2
    assert ran[0].startswith(TAKES_A_SLOT)
    assert ran[1].startswith(f"{PARALLEL_PASS} --shard=2/3 --test-report=")
    assert ran[1].endswith("/parallel")


@pytest.mark.parametrize("count", [1, 2, 3])
def test_the_parts_together_are_the_whole_run(checkout: Checkout, count: int) -> None:
    """The remainder and every slice run each line the whole run runs, the parallel pass
    once for each slice, with its share."""
    whole = _ran(checkout)
    rest = _ran(checkout, "--rest")
    shares = [_ran(checkout, "--shard", f"{i}/{count}") for i in range(1, count + 1)]

    parallel = [step for share in shares for step in share if step.startswith(PARALLEL_PASS)]
    assert [step.split(" --test-report=")[0] for step in parallel] == [
        f"{PARALLEL_PASS} --shard={i}/{count}" for i in range(1, count + 1)
    ]
    slots = [step for step in whole if step.startswith(TAKES_A_SLOT)]
    assert sorted({*rest, PARALLEL_PASS, *slots}) == sorted(set(whole))
    assert len(rest) + 2 == len(whole)


@pytest.mark.parametrize(
    ("status", "ok"),
    [("0", True), ("5", False), ("1", False)],
    ids=["passed", "an-empty-share", "a-test-fails"],
)
def test_a_slice_whose_share_holds_no_test_fails(checkout: Checkout, status: str, ok: bool) -> None:
    done = checkout.check("--shard", "1/2", STUB_PARALLEL_STATUS=status)

    assert (done.returncode == 0) == ok
    verdict = "ok" if ok else "FAILED"
    assert f"-- tests (slice 1/2 of the parallel pass): {verdict}" in done.stdout


def test_the_remainder_passes_with_no_test_marked_serial_and_fails_on_a_failure(
    checkout: Checkout,
) -> None:
    assert checkout.check("--rest", STUB_SERIAL_STATUS="5").returncode == 0
    failed = checkout.check("--rest", STUB_SERIAL_STATUS="1")
    assert failed.returncode == 1
    assert "-- tests (the remainder: only those marked serial): FAILED" in failed.stdout
    assert "-- changelog lint: ok" in failed.stdout


@pytest.mark.parametrize(
    ("args", "passes"),
    [
        ((), ["parallel", "serial"]),
        (("--rest",), ["serial"]),
        (("--short",), ["answers"]),
        (("--shard", "1/2"), ["parallel"]),
    ],
    ids=["whole", "rest", "short", "slice"],
)
def test_each_pass_reports_into_a_folder_of_its_own_where_reports_are_asked_for(
    checkout: Checkout, tmp_path: Path, args: tuple[str, ...], passes: list[str]
) -> None:
    reports = tmp_path / "reports"

    _ran(checkout, *args, PKIT_TEST_REPORTS=str(reports))

    asked = [line.split("--test-report=")[1] for line in checkout.log.read_text().splitlines()]
    assert asked == [str(reports / name) for name in passes]


def test_a_whole_run_asks_for_no_report_where_none_is_asked_for(checkout: Checkout) -> None:
    _ran(checkout)

    assert "--test-report" not in checkout.log.read_text()
