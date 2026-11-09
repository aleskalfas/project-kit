"""The suite collects the same tests, in the same order, on every machine (#2668).

Each slice of a full run in CI collects the suite on a runner of its own, and cuts it
in the order it collected (ADR-078 point 5). A folder lists its files in an order its
machine's file system sets. So a test parametrized over a listing it does not sort
collects in another order on another runner, and the slices of one run report two
digests. Here the suite is collected twice, with every listing sorted and with every
listing reversed (`tests/listing_order.py`), and must collect the same ids in the
same order both times.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests import listing_order

REPO = Path(__file__).resolve().parents[1]

#: How long one collection of the whole suite may take, in seconds.
TIMEOUT = 600


def _collect(root: Path, order: str) -> subprocess.Popen[str]:
    """Start collecting the suite at `root`, with every listing in `order`."""
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "tests.listing_order",
        ],
        cwd=root,
        env={
            **{k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")},
            "PYTHONPATH": str(REPO),
            listing_order.ENV: order,
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def collected(root: Path) -> dict[str, list[str]]:
    """The ids of the tests collected at `root` under each order, in the order collected.
    The two collections run side by side."""
    runs = {order: _collect(root, order) for order in listing_order.ORDERS}
    try:
        outputs = {order: run.communicate(timeout=TIMEOUT)[0] for order, run in runs.items()}
    finally:
        for run in runs.values():
            run.kill()
    ids: dict[str, list[str]] = {}
    for order, output in outputs.items():
        assert runs[order].returncode == 0, f"collecting with every listing {order}:\n{output}"
        # The ids come first, one to a line, and a blank line ends them.
        listed = output.split("\n\n", 1)[0]
        ids[order] = [line for line in listed.splitlines() if "::" in line]
    return ids


def moved(ids: dict[str, list[str]]) -> list[str]:
    """The modules whose tests the two orders collect differently, or in another order."""
    by_module: dict[str, dict[str, list[str]]] = {}
    for order, tests in ids.items():
        for test in tests:
            by_module.setdefault(order, {}).setdefault(test.partition("::")[0], []).append(test)
    first, second = (by_module.get(order, {}) for order in listing_order.ORDERS)
    return sorted(m for m in first.keys() | second.keys() if first.get(m) != second.get(m))


def test_the_suite_collects_the_same_tests_in_the_same_order_however_a_folder_lists(
    request: pytest.FixtureRequest,
) -> None:
    ids = collected(REPO)
    modules = moved(ids)

    assert modules == [], (
        "where a folder lists its files in another order, these modules collect their tests "
        f"in another order, so sort the listing they are parametrized over: {', '.join(modules)}"
    )
    assert ids["sorted"] == ids["reversed"]
    assert request.node.nodeid in ids["sorted"]


# --- the guard's own reach ----------------------------------------------------------

#: A test module parametrized over the files of the folder `data` beside it, listed as
#: `{listed}` says.
OVER_A_LISTING = """
from pathlib import Path

import pytest

FILES = Path(__file__).with_name("data").iterdir()


@pytest.mark.parametrize("path", {listed}, ids=lambda path: path.name)
def test_each_file(path):
    pass
"""


def test_a_module_parametrized_over_a_listing_it_does_not_sort_is_named(tmp_path: Path) -> None:
    """The plugin reorders the listings before a test module is imported, so the guard
    names a module parametrized over an unsorted listing, and passes one that sorts it."""
    (tmp_path / "data").mkdir()
    for name in ("a.txt", "b.txt", "c.txt"):
        (tmp_path / "data" / name).write_text("", encoding="utf-8")
    for module, listed in (("unsorted", "list(FILES)"), ("sorted", "sorted(FILES)")):
        module_text = OVER_A_LISTING.format(listed=listed)
        (tmp_path / f"test_{module}.py").write_text(module_text, encoding="utf-8")

    ids = collected(tmp_path)

    assert moved(ids) == ["test_unsorted.py"]
    assert len(ids["sorted"]) == 6


@pytest.mark.parametrize("order", listing_order.ORDERS)
def test_every_way_of_listing_a_folder_comes_back_in_the_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, order: str
) -> None:
    names = ["b.py", "c.py", "a.py"]
    for name in names:
        (tmp_path / name).write_text("")
    expected = sorted(names, reverse=order == "reversed")

    listing_order.install(order, monkeypatch.setattr)

    def listings() -> Sequence[list[str]]:
        with os.scandir(tmp_path) as entries:
            scanned = [entry.name for entry in entries]
        return [
            os.listdir(tmp_path),
            scanned,
            next(os.walk(tmp_path))[2],
            [Path(p).name for p in glob.glob(str(tmp_path / "*.py"))],
            [p.name for p in tmp_path.iterdir()],
            [p.name for p in tmp_path.glob("*.py")],
            [p.name for p in tmp_path.rglob("*.py")],
        ]

    assert listings() == [expected] * 7


def test_an_order_that_is_none_of_the_two_is_refused() -> None:
    with pytest.raises(ValueError, match="sorted, reversed"):
        listing_order.install("shuffled", lambda *_: None)
