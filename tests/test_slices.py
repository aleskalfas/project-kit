"""The suite's slices (`tests/slices.py`, ADR-078 points 5 and 6).

- **The cut** puts each test collected in exactly one share. The shares are runs of
  consecutive tests in the collected order, and each misses its Nth of the total
  weight by at most one test's weight. It is deterministic, and reads only the
  tests and the table: a test the table lacks weighs the median, and an entry no
  test bears changes nothing.
- **The digest** covers the ids in their order, the table and N, and names no
  share, so every slice of a run reports the same one.
- **Under pytest,** the cut runs after the `serial` mark's filter, in one process
  and in xdist's workers alike. The slices together run every test the filter
  left, once. A share with no test makes pytest exit 5. Each slice reports its cut
  and what it ran.
- **The table** is written from the times the slices of a run in CI kept, by a
  command that reads the run through `gh`. Here `gh` is a fake.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from tests import slices

REPO = Path(__file__).resolve().parents[1]

IDS = [f"tests/test_{m}.py::test_{n}" for m in "abc" for n in range(5)]


def _table(**times: int) -> dict[str, int]:
    return dict(times)


# --- the cut ------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["1/1", "1/2", "2/2", "3/7"])
def test_a_shard_is_i_of_n(text: str) -> None:
    assert str(slices.Shard.parse(text)) == text


@pytest.mark.parametrize("text", ["0/2", "3/2", "1/0", "1", "a/b", "1/2/3", " 1/2", "-1/2"])
def test_anything_else_is_no_shard(text: str) -> None:
    with pytest.raises(ValueError, match="i/N"):
        slices.Shard.parse(text)


@pytest.mark.parametrize("count", [1, 2, 3, 4, 15, 16])
def test_each_test_lies_in_exactly_one_share_and_the_shares_follow_the_order(
    count: int,
) -> None:
    table = {test: 100 * (i % 4 + 1) for i, test in enumerate(IDS)}

    shares = slices.cut(IDS, table, count)

    assert len(shares) == count
    assert [test for share in shares for test in share] == IDS
    assigned = slices.assign(IDS, table, count)
    assert assigned == sorted(assigned)


def test_the_cut_is_the_same_every_time() -> None:
    table = {test: 7 * i + 3 for i, test in enumerate(IDS)}

    assert {str(slices.cut(IDS, table, 3)) for _ in range(5)} == {str(slices.cut(IDS, table, 3))}


def test_each_share_misses_its_part_of_the_total_by_at_most_one_test() -> None:
    weights = [5, 900, 30, 30, 2000, 1, 1, 400, 250, 250, 60, 700, 10, 10, 1200]
    table = dict(zip(IDS, weights, strict=True))
    total = sum(weights)

    for count in (2, 3, 4):
        for share in slices.cut(IDS, table, count):
            weight = sum(table[test] for test in share)
            assert abs(weight - total / count) <= max(weights)


def test_two_shares_split_where_the_weights_balance_not_the_counts() -> None:
    """Ten light tests, then five heavy ones: the cut falls among the heavy ones."""
    table = {test: (10 if i < 10 else 1000) for i, test in enumerate(IDS)}

    first, second = slices.cut(IDS, table, 2)

    assert len(first) == 12
    assert len(second) == 3


def test_a_test_the_table_lacks_weighs_the_median_of_those_it_holds() -> None:
    table = {IDS[0]: 100, IDS[1]: 300, IDS[2]: 500}

    assert slices.weights(IDS[:4], table) == [100, 300, 500, 300]


def test_an_entry_no_test_bears_changes_nothing() -> None:
    table = {test: 10 * (i + 1) for i, test in enumerate(IDS[:8])}
    stale = {**table, "tests/test_gone.py::test_x": 99_000, "tests/test_gone.py::test_y": 1}

    assert slices.cut(IDS, stale, 3) == slices.cut(IDS, table, 3)


def test_an_empty_table_weighs_every_test_the_same() -> None:
    first, second = slices.cut(IDS, {}, 2)

    # The eighth of fifteen lies on the half, and goes to the second share.
    assert (len(first), len(second)) == (7, 8)


def test_a_test_that_took_no_time_still_weighs() -> None:
    assert slices.weights(IDS[:2], {IDS[0]: 0, IDS[1]: 0}) == [1, 1]


# --- the digest ---------------------------------------------------------------------


def test_the_digest_covers_the_order_the_table_and_the_count() -> None:
    table = {IDS[0]: 10}
    digest = slices.digest(IDS, table, 2)

    assert digest.startswith("sha256:")
    assert slices.digest(list(IDS), dict(table), 2) == digest
    assert slices.digest(list(reversed(IDS)), table, 2) != digest
    assert slices.digest(IDS[:-1], table, 2) != digest
    assert slices.digest(IDS, {IDS[0]: 11}, 2) != digest
    assert slices.digest(IDS, table, 3) != digest


def test_the_table_is_read_as_milliseconds_by_test_id(tmp_path: Path) -> None:
    path = tmp_path / "times.json"
    document = slices.table_document(
        {"tests/test_a.py::test_x": 1.234, "tests/test_a.py::T::test_y[1]": 0.004},
        {"run": "https://example.invalid/runs/1"},
    )
    path.write_text(json.dumps(document), encoding="utf-8")

    assert document["tests"] == {"tests/test_a.py": {"T::test_y[1]": 0.0, "test_x": 1.23}}
    assert document["run"] == "https://example.invalid/runs/1"
    assert slices.read_table(path) == {
        "tests/test_a.py::test_x": 1230,
        "tests/test_a.py::T::test_y[1]": 0,
    }


def test_the_committed_table_reads() -> None:
    table = slices.read_table(slices.TABLE)

    assert all(isinstance(ms, int) and ms >= 0 for ms in table.values())


# --- under pytest -------------------------------------------------------------------

#: A suite of its own: twelve tests in two modules, two of them marked `serial`, and a
#: conftest that hooks the slices as this suite's conftest does.
CONFTEST = """
from tests import slices

def pytest_addoption(parser):
    slices.addoption(parser)

def pytest_configure(config):
    config.addinivalue_line("markers", "serial: runs alone")
    slices.configure(config)
"""

MODULE = """
import pytest

{tests}
"""


class Suite:
    def __init__(self, root: Path, tests: Sequence[str] = ("a", "b")) -> None:
        self.root = root / "suite"
        self.root.mkdir()
        (self.root / "conftest.py").write_text(CONFTEST, encoding="utf-8")
        for module in tests:
            body = "\n".join(
                ("@pytest.mark.serial\n" if n == 0 else "") + f"def test_{n}():\n    pass\n"
                for n in range(6)
            )
            (self.root / f"test_{module}.py").write_text(MODULE.format(tests=body))
        self.table = root / "times.json"
        times = {f"test_{m}.py::test_{n}": float(n + 1) for m in tests for n in range(6)}
        self.table.write_text(json.dumps(slices.table_document(times, {})), encoding="utf-8")

    def run(self, *args: str, report: Path | None = None) -> subprocess.CompletedProcess[str]:
        # One token each: pytest reads its own options before a conftest adds these,
        # and would take a value apart from its option for a path to collect.
        options = [f"--shard-table={self.table}"]
        if report is not None:
            options.append(f"--test-report={report}")
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *options, *args],
            cwd=self.root,
            env={
                **{k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")},
                "PYTHONPATH": str(REPO),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("workers", [[], ["-n", "2"]], ids=["one-process", "xdist"])
def test_the_slices_together_run_every_test_the_filter_left_once(
    tmp_path: Path, workers: list[str]
) -> None:
    suite = Suite(tmp_path)
    cuts: list[Any] = []
    ran: list[str] = []

    for index in (1, 2):
        report = tmp_path / f"report-{index}"
        done = suite.run(*workers, "-m", "not serial", f"--shard={index}/2", report=report)

        assert done.returncode == 0, done.stdout + done.stderr
        cuts.append(_read(report / slices.CUT_REPORT))
        ran += list(_read(report / slices.RAN_REPORT)["tests"])
        assert f"slice {index}/2: " in done.stdout

    left = [f"test_{m}.py::test_{n}" for m in "ab" for n in range(1, 6)]
    assert sorted(ran) == sorted(left)
    assert len(set(ran)) == len(ran)
    assert {cut["digest"] for cut in cuts} == {cuts[0]["digest"]}
    assert [cut["collected"] for cut in cuts] == [10, 10]
    assert sum(cut["held"] for cut in cuts) == 10
    assert [cut["listed"] for cut in cuts] == [12, 12]
    assert [cut["unlisted"] for cut in cuts] == [0, 0]
    # Consecutive tests in the collected order: the first slice ends where the second
    # starts.
    first = [test for test in left if test in _read(tmp_path / "report-1" / "ran.json")["tests"]]
    assert first == left[: len(first)]


def test_the_cut_follows_the_filter(tmp_path: Path) -> None:
    """The serial tests are filtered out before the cut, so the shares add up to what
    runs, and their entries in the table weigh in nothing."""
    suite = Suite(tmp_path)
    report = tmp_path / "report"

    suite.run("-m", "not serial", "--shard=1/2", report=report)
    cut = _read(report / slices.CUT_REPORT)
    ids = [f"test_{m}.py::test_{n}" for m in "ab" for n in range(1, 6)]
    table = slices.read_table(suite.table)

    assert cut["digest"] == slices.digest(ids, table, 2)


def test_a_slice_whose_share_holds_no_test_exits_5(tmp_path: Path) -> None:
    suite = Suite(tmp_path)

    # One test, of two shares: the cut puts it in the second.
    done = suite.run("-m", "not serial", "-k", "test_a and test_3", "--shard=1/2")

    assert done.returncode == 5, done.stdout + done.stderr


def test_a_report_names_each_test_s_time_and_the_tests_that_failed(tmp_path: Path) -> None:
    suite = Suite(tmp_path)
    (suite.root / "test_c.py").write_text("def test_fails():\n    assert False\n")
    report = tmp_path / "report"

    done = suite.run("-n", "2", "-m", "not serial", report=report)

    assert done.returncode == 1
    ran = _read(report / slices.RAN_REPORT)
    assert ran["failed"] == ["test_c.py::test_fails"]
    assert len(ran["tests"]) == 11
    assert not (report / slices.CUT_REPORT).exists()


def test_a_shard_that_is_no_shard_is_a_usage_error(tmp_path: Path) -> None:
    done = Suite(tmp_path).run("--shard=3/2")

    assert done.returncode == 4
    assert "i/N" in done.stderr


# --- the command that writes the table ----------------------------------------------

REPOSITORY = "owner/project"
RUN = 77


class Gh:
    """Answers the runs on `main`, a run's artifacts and the run itself, and downloads
    an artifact from `kept`, the reports each artifact holds."""

    def __init__(self, kept: dict[int, dict[str, Any]], runs: Sequence[int] = (RUN,)) -> None:
        self.kept = kept
        self.runs = runs
        self.path = ".github/workflows/checks.yml"
        self.asked: list[list[str]] = []

    def __call__(self, args: Sequence[str]) -> str:
        self.asked.append(list(args))
        if args[0] == "run":
            run, name, folder = int(args[2]), args[args.index("-n") + 1], args[-1]
            reports = self.kept[run][name]
            Path(folder).mkdir(parents=True)
            for file, document in reports.items():
                (Path(folder) / file).write_text(json.dumps(document), encoding="utf-8")
            return ""
        path = args[-1]
        if "/workflows/" in path:
            return json.dumps({"workflow_runs": [{"id": run} for run in self.runs]})
        run = int(path.split("/runs/")[1].split("/")[0].split("?")[0])
        if path.split("?")[0].endswith("/artifacts"):
            names = [{"name": name, "expired": False} for name in self.kept.get(run, {})]
            return json.dumps({"artifacts": [*names, {"name": "something else"}]})
        return json.dumps(
            {
                "path": self.path,
                "html_url": f"https://github.com/{REPOSITORY}/actions/runs/{run}",
                "event": "push",
                "head_branch": "main",
                "head_sha": "f" * 40,
            }
        )


def _kept(*shares: dict[str, float], digest: str = "sha256:" + "a" * 64) -> dict[str, Any]:
    count = len(shares)
    return {
        f"test-times-{i}-of-{count}": {
            slices.CUT_REPORT: {"shard": f"{i}/{count}", "digest": digest},
            slices.RAN_REPORT: {"tests": times, "failed": []},
        }
        for i, times in enumerate(shares, 1)
    }


def test_the_table_is_written_from_every_slice_of_the_newest_run_that_kept_them(
    tmp_path: Path,
) -> None:
    gh = Gh(
        {
            80: _kept({"tests/test_a.py::test_x": 1.0}),  # one slice of two: not whole
            RUN: _kept({"tests/test_a.py::test_x": 2.5}, {"tests/test_b.py::test_y": 0.25}),
        },
        runs=(81, 80, RUN),
    )
    gh.kept[80]["test-times-1-of-2"] = gh.kept[80].pop("test-times-1-of-1")
    out = tmp_path / "times.json"

    address, tests = slices.write_table(gh, REPOSITORY, None, out)

    assert (address, tests) == (f"https://github.com/{REPOSITORY}/actions/runs/{RUN}", 2)
    document = _read(out)
    assert document["tests"] == {
        "tests/test_a.py": {"test_x": 2.5},
        "tests/test_b.py": {"test_y": 0.25},
    }
    assert (document["event"], document["branch"], document["commit"]) == ("push", "main", "f" * 40)
    assert "branch=main&event=push&status=success" in gh.asked[0][-1]


def test_a_run_of_another_workflow_writes_no_table(tmp_path: Path) -> None:
    gh = Gh({RUN: _kept({"tests/test_a.py::test_x": 1.0})})
    gh.path = ".github/workflows/other.yml"

    with pytest.raises(slices.Refused, match=r"not a run of checks\.yml"):
        slices.write_table(gh, REPOSITORY, RUN, tmp_path / "times.json")


@pytest.mark.parametrize(
    ("kept", "why"),
    [
        (
            _kept({"tests/test_a.py::test_x": 1.0}, {"tests/test_a.py::test_x": 2.0}),
            "ran in two slices",
        ),
        (
            {
                **_kept({"tests/test_a.py::test_x": 1.0}, {"tests/test_b.py::test_y": 2.0}),
                "test-times-2-of-2": _kept(
                    {"x": 1.0}, {"tests/test_b.py::test_y": 2.0}, digest="sha256:" + "b" * 64
                )["test-times-2-of-2"],
            },
            "did not cut the same tests",
        ),
    ],
    ids=["a-test-in-two-slices", "slices-that-disagree"],
)
def test_slices_that_make_no_one_cut_write_no_table(
    tmp_path: Path, kept: dict[str, Any], why: str
) -> None:
    out = tmp_path / "times.json"

    with pytest.raises(slices.Refused, match=why):
        slices.write_table(Gh({RUN: kept}), REPOSITORY, RUN, out)
    assert not out.exists()


def test_a_run_that_kept_no_slice_s_times_writes_no_table(tmp_path: Path) -> None:
    with pytest.raises(slices.Refused, match="did not keep the times of every slice"):
        slices.write_table(Gh({}), REPOSITORY, RUN, tmp_path / "times.json")


def test_the_command_says_what_it_wrote_or_why_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(slices, "TABLE", tmp_path / "times.json")
    gh = Gh({RUN: _kept({"tests/test_a.py::test_x": 1.0})})

    assert slices.main(["table", "--repository", REPOSITORY, "--run", str(RUN)], gh) == 0
    assert "1 tests" in capsys.readouterr().out
    assert slices.main(["table", "--repository", REPOSITORY, "--run", "5"], Gh({})) == 1
    assert "did not keep" in capsys.readouterr().err
