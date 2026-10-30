"""The suite's slices, as a full run in CI cuts them (ADR-078 points 5 and 6).

A slice, `scripts/check.sh --shard i/N`, runs the i-th of N shares of the suite's
parallel pass. `tests/conftest.py` hands pytest the options below, and this
module does the rest.

- **The cut.** The tests left once the `serial` mark's filter has run, in the
  order pytest collects them, are cut into N runs of consecutive tests. A test
  weighs its time in the table of test times, `tests/test_times.json`. A test
  the table lacks weighs the median of the table's times for the tests
  collected, and an entry no test bears is ignored. Each test lies in the share
  where the middle of its weight falls, so a share misses its Nth of the total
  by at most one test's time.
- **The same cut in every slice.** The cut reads only the tests collected and
  the table, both fixed by the run's commit, and holds no randomness. So the
  slices of one run agree, and a contributor can run a slice again.
- **What a slice reports.** A digest of the cut's inputs: the ids of the tests
  collected, in the order the cut follows, with the table and N. Beside it, the
  number of tests collected, the number the share held, how many entries the
  table holds, and how many tests collected it lacks.

The options:

- `--shard i/N` runs the i-th share. Where the share is empty, pytest exits 5,
  and the aggregator fails the slice.
- `--test-report DIR` writes what the run did into DIR. The process that runs
  the session writes `ran.json`, each test's time and the tests that failed. With
  `--shard`, each process that collects writes `cut.json`, the cut's report.
- `--shard-table PATH` reads another table than the committed one.

**The table** is written by a command, from the times each slice of a full run in
CI keeps as an artifact of the run (`.github/workflows/checks.yml`). By default
it reads the newest full run on `main` that passed and kept them:

    uv run python -m tests.slices table [--run ID]

The command asks `gh` for the run and its artifacts. Whoever refreshes the table
reviews it like any change (the tests README, "Running the suite").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest

#: The committed table of test times.
TABLE = Path(__file__).resolve().with_name("test_times.json")

#: What the digest covers is versioned, so a change to it changes every digest.
DIGEST_FORMAT = "pkit-test-slices 1"

#: The files a run writes under `--test-report`.
CUT_REPORT = "cut.json"
RAN_REPORT = "ran.json"

#: The workflow whose runs keep the times, and the names of the artifacts they keep.
WORKFLOW_FILE = "checks.yml"
ARTIFACT = re.compile(r"test-times-(\d+)-of-(\d+)")

#: How many of `main`'s runs the command looks through for one that kept the times.
RUNS_READ = 30

_SHARD = re.compile(r"([1-9][0-9]*)/([1-9][0-9]*)")


@dataclass(frozen=True)
class Shard:
    """The i-th of N shares, counted from 1."""

    index: int
    count: int

    @classmethod
    def parse(cls, text: str) -> Shard:
        matched = _SHARD.fullmatch(text)
        if matched is None or int(matched[1]) > int(matched[2]):
            raise ValueError(f"a shard is i/N, with 1 <= i <= N, not {text!r}")
        return cls(int(matched[1]), int(matched[2]))

    def __str__(self) -> str:
        return f"{self.index}/{self.count}"


# --- the table ----------------------------------------------------------------------


def read_table(path: Path) -> dict[str, int]:
    """Each test's time in the table at `path`, in milliseconds, by its id."""
    document = json.loads(path.read_text(encoding="utf-8"))
    tests = cast("Mapping[str, Mapping[str, float]]", document["tests"])
    return {
        _test_id(module, name): round(seconds * 1000)
        for module, names in tests.items()
        for name, seconds in names.items()
    }


def _test_id(module: str, name: str) -> str:
    return f"{module}::{name}" if name else module


def table_document(times: Mapping[str, float], source: Mapping[str, str]) -> dict[str, Any]:
    """The table for `times`, each test's seconds by its id, grouped by module and in
    order. `source` names the run the times come from."""
    tests: dict[str, dict[str, float]] = {}
    for test in sorted(times):
        module, _, name = test.partition("::")
        tests.setdefault(module, {})[name] = round(times[test], 2)
    return {
        "about": (
            "The time each test of the suite's parallel pass took in a full run in CI, "
            "which the slices are cut by (ADR-078 point 5). Written by "
            "`uv run python -m tests.slices table`, never by hand."
        ),
        **source,
        "tests": tests,
    }


# --- the cut ------------------------------------------------------------------------


def weights(ids: Sequence[str], table: Mapping[str, int]) -> list[int]:
    """Each test's weight in milliseconds: its time in the table, or the median of the
    times the table holds for the tests collected where the table lacks it. An entry
    no test bears weighs in nothing. Every test weighs at least one millisecond."""
    listed = [table[test] for test in ids if test in table]
    median = statistics.median_low(listed) if listed else 1
    return [max(1, table.get(test, median)) for test in ids]


def assign(ids: Sequence[str], table: Mapping[str, int], count: int) -> list[int]:
    """The share, from 0, of each test in `ids`, in order. Each test lies in the share
    where the middle of its weight falls, so the shares are runs of consecutive
    tests, and each misses its Nth of the total by at most one test's weight."""
    weighed = weights(ids, table)
    total = sum(weighed)
    shares: list[int] = []
    before = 0
    for weight in weighed:
        shares.append(min(count - 1, count * (2 * before + weight) // (2 * total)))
        before += weight
    return shares


def cut(ids: Sequence[str], table: Mapping[str, int], count: int) -> list[list[str]]:
    """The tests of each of the `count` shares, in order."""
    shares: list[list[str]] = [[] for _ in range(count)]
    for test, share in zip(ids, assign(ids, table, count), strict=True):
        shares[share].append(test)
    return shares


def digest(ids: Sequence[str], table: Mapping[str, int], count: int) -> str:
    """The digest of the cut's inputs: the ids in the order the cut follows, the table
    and the number of shares. It names no share, so every slice of a run reports it."""
    hashed = hashlib.sha256(f"{DIGEST_FORMAT}\n{count}\n".encode())
    hashed.update(json.dumps(table, sort_keys=True, separators=(",", ":")).encode())
    for test in ids:
        hashed.update(f"\n{test}".encode())
    return f"sha256:{hashed.hexdigest()}"


# --- the plugin ---------------------------------------------------------------------


def addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("slices", "the suite's slices (tests/slices.py, ADR-078)")
    group.addoption(
        "--shard",
        metavar="i/N",
        help="run only the i-th of N shares of the tests collected, cut by the table of times",
    )
    group.addoption(
        "--shard-table",
        metavar="PATH",
        default=str(TABLE),
        help="the table of test times the cut reads (default: tests/test_times.json)",
    )
    group.addoption(
        "--test-report",
        metavar="DIR",
        help="write each test's time and the tests that failed, and the cut, into DIR",
    )


def configure(config: pytest.Config) -> None:
    """Register the slices' hooks where an option asks for them."""
    shard = cast("str | None", config.getoption("shard"))
    report = cast("str | None", config.getoption("test_report"))
    if shard is None and report is None:
        return
    try:
        parsed = Shard.parse(shard) if shard is not None else None
    except ValueError as exc:
        raise pytest.UsageError(f"--shard: {exc}") from exc
    table = Path(cast("str", config.getoption("shard_table")))
    plugin = Slices(config, parsed, table, Path(report).resolve() if report else None)
    config.pluginmanager.register(plugin, "pkit-slices")


class Slices:
    """Cuts the collected tests where `--shard` asks, and reports what ran where
    `--test-report` asks."""

    def __init__(
        self, config: pytest.Config, shard: Shard | None, table: Path, report: Path | None
    ) -> None:
        self.config = config
        self.shard = shard
        self.table = table
        self.report = report
        #: An xdist worker collects and runs; the session's own process reports what ran.
        self.worker = hasattr(config, "workerinput")
        self.times: dict[str, float] = {}
        self.failed: list[str] = []

    # After every other plugin's, so the cut follows the mark's filter.
    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(
        self, config: pytest.Config, items: list[pytest.Item]
    ) -> None:
        if self.shard is None:
            return
        table = read_table(self.table)
        ids = [item.nodeid for item in items]
        shares = assign(ids, table, self.shard.count)
        mine = self.shard.index - 1
        kept = [item for item, share in zip(items, shares, strict=True) if share == mine]
        dropped = [item for item, share in zip(items, shares, strict=True) if share != mine]
        if dropped:
            config.hook.pytest_deselected(items=dropped)
        items[:] = kept
        if self.report is not None:
            _write(
                self.report / CUT_REPORT,
                {
                    "shard": str(self.shard),
                    "digest": digest(ids, table, self.shard.count),
                    "collected": len(ids),
                    "held": len(kept),
                    "listed": len(table),
                    "unlisted": sum(test not in table for test in ids),
                },
            )

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if self.report is None or self.worker:
            return
        self.times[report.nodeid] = self.times.get(report.nodeid, 0.0) + report.duration
        if report.failed and report.nodeid not in self.failed:
            self.failed.append(report.nodeid)

    def pytest_sessionfinish(self) -> None:
        if self.report is None or self.worker:
            return
        times = {test: round(seconds, 3) for test, seconds in self.times.items()}
        _write(self.report / RAN_REPORT, {"tests": times, "failed": self.failed})

    def pytest_terminal_summary(self, terminalreporter: Any) -> None:
        if self.shard is None or self.report is None:
            return
        try:
            said = json.loads((self.report / CUT_REPORT).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        terminalreporter.write_line(
            f"slice {said['shard']}: {said['held']} of the {said['collected']} tests "
            f"collected, digest {said['digest']}; the table lacks {said['unlisted']} of them"
        )


def _write(path: Path, document: Mapping[str, Any]) -> None:
    """Write `document` to `path` whole: each process that collects writes the same cut,
    so a reader sees one of them, never a part."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}")
    partial.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    os.replace(partial, path)


# --- the command that writes the table ----------------------------------------------


class Refused(Exception):
    """The table cannot be written from the run asked for, and why."""


Gh = Callable[[Sequence[str]], str]


def gh(args: Sequence[str]) -> str:
    """`gh <args>`, its standard output. Raises Refused when it fails."""
    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    except OSError as exc:
        raise Refused(f"gh could not be run: {exc}") from exc
    if done.returncode != 0:
        raise Refused(f"gh {' '.join(args[:2])} exited {done.returncode}: {done.stderr.strip()}")
    return done.stdout


def _api(run: Gh, path: str) -> Mapping[str, Any]:
    answer = json.loads(run(["api", "-H", "Accept: application/vnd.github+json", path]))
    if not isinstance(answer, Mapping):
        raise Refused(f"GitHub's answer to {path} is not an object")
    return cast("Mapping[str, Any]", answer)


def slices_kept(run: Gh, repository: str, run_id: int) -> int | None:
    """How many slices of the run kept their times, where every one of them did."""
    listed = _api(run, f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100")
    found: set[tuple[int, int]] = set()
    for artifact in cast("list[Mapping[str, Any]]", listed.get("artifacts") or []):
        matched = ARTIFACT.fullmatch(str(artifact.get("name")))
        if matched and not artifact.get("expired"):
            found.add((int(matched[1]), int(matched[2])))
    counts = {count for _, count in found}
    if len(counts) != 1:
        return None
    (count,) = counts
    return count if found == {(i, count) for i in range(1, count + 1)} else None


def newest_run(run: Gh, repository: str) -> int:
    """The newest run of the workflow on a push to `main` that passed and whose slices
    kept their times."""
    listed = _api(
        run,
        f"repos/{repository}/actions/workflows/{WORKFLOW_FILE}/runs"
        f"?branch=main&event=push&status=success&per_page={RUNS_READ}",
    )
    for found in cast("list[Mapping[str, Any]]", listed.get("workflow_runs") or []):
        if slices_kept(run, repository, int(found["id"])) is not None:
            return int(found["id"])
    raise Refused(
        f"none of the {RUNS_READ} newest runs on main that passed kept the times of its slices"
    )


def times_of(folders: Sequence[Path]) -> dict[str, float]:
    """Each test's time from the slices' reports, the i-th slice's in the i-th folder.
    Raises Refused where the slices do not make up one cut."""
    times: dict[str, float] = {}
    digests: set[str] = set()
    for index, folder in enumerate(folders, 1):
        cut_said = json.loads((folder / CUT_REPORT).read_text(encoding="utf-8"))
        ran = json.loads((folder / RAN_REPORT).read_text(encoding="utf-8"))
        if cut_said["shard"] != f"{index}/{len(folders)}":
            raise Refused(f"the report of slice {index}/{len(folders)} is {cut_said['shard']}'s")
        digests.add(cut_said["digest"])
        for test, seconds in cast("Mapping[str, float]", ran["tests"]).items():
            if test in times:
                raise Refused(f"{test} ran in two slices")
            times[test] = seconds
    if len(digests) != 1:
        raise Refused("the slices of the run did not cut the same tests")
    return times


def write_table(
    run: Gh, repository: str, run_id: int | None, out: Path | None = None
) -> tuple[str, int]:
    """Write the table, the committed one unless `out` names another, from the run
    `run_id`, or the newest that kept the times. Returns the run's address and how
    many tests the table holds."""
    out = TABLE if out is None else out
    run_id = newest_run(run, repository) if run_id is None else run_id
    meta = _api(run, f"repos/{repository}/actions/runs/{run_id}")
    if meta.get("path") != f".github/workflows/{WORKFLOW_FILE}":
        raise Refused(f"run {run_id} is not a run of {WORKFLOW_FILE}")
    count = slices_kept(run, repository, run_id)
    if count is None:
        raise Refused(f"run {run_id} did not keep the times of every slice")
    with tempfile.TemporaryDirectory() as scratch:
        folders: list[Path] = []
        for index in range(1, count + 1):
            name = f"test-times-{index}-of-{count}"
            folders.append(Path(scratch) / name)
            run(
                [
                    "run",
                    "download",
                    str(run_id),
                    "-R",
                    repository,
                    "-n",
                    name,
                    "-D",
                    str(folders[-1]),
                ]
            )
        times = times_of(folders)
    source = {
        "run": str(meta.get("html_url")),
        "event": str(meta.get("event")),
        "branch": str(meta.get("head_branch")),
        "commit": str(meta.get("head_sha")),
    }
    document = table_document(times, source)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return source["run"], len(times)


def main(argv: Sequence[str] | None = None, run: Gh = gh) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tests.slices", description="The suite's slices (ADR-078)."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    table = commands.add_parser(
        "table", help="write tests/test_times.json from the times a full run in CI kept"
    )
    table.add_argument(
        "--run",
        type=int,
        help="the run's id; by default the newest run on a push to main that passed and kept them",
    )
    table.add_argument("--repository", help="owner/name; by default the one gh sees here")
    args = parser.parse_args(argv)
    try:
        repository = (
            args.repository
            or run(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()
        )
        address, tests = write_table(run, repository, args.run)
    except (Refused, ValueError, KeyError, OSError) as exc:
        print(f"tests.slices table: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {TABLE}: {tests} tests, from {address}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
