"""Tests for `_lib.criterion_cli._parse_targets` — the positional grammar.

`check-criterion <issue> <index> [text] <index> [text] ...` parses an integer as
a new target's index and a following non-integer as that index's guard. These
tests pin the grammar offline (no network, no membership).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


@pytest.fixture(scope="module", autouse=True)
def _scripts_on_path():
    sys.path.insert(0, str(SCRIPTS))
    yield
    sys.path.remove(str(SCRIPTS))


@pytest.fixture(scope="module")
def cli(_scripts_on_path):
    from _lib import criterion_cli

    return criterion_cli


def test_single_index(cli) -> None:
    targets = cli._parse_targets(["1"])
    assert len(targets) == 1
    assert targets[0].index == 1
    assert targets[0].expected_text is None


def test_index_with_guard(cli) -> None:
    targets = cli._parse_targets(["1", "docs updated"])
    assert targets[0].index == 1
    assert targets[0].expected_text == "docs updated"


def test_batch_mixed_guards(cli) -> None:
    targets = cli._parse_targets(["1", "alpha", "3", "5"])
    assert [(t.index, t.expected_text) for t in targets] == [
        (1, "alpha"),
        (3, None),
        (5, None),
    ]


def test_consecutive_indices(cli) -> None:
    targets = cli._parse_targets(["1", "2", "3"])
    assert [t.index for t in targets] == [1, 2, 3]
    assert all(t.expected_text is None for t in targets)


def test_guard_without_index_is_error(cli) -> None:
    with pytest.raises(ValueError, match="no preceding index"):
        cli._parse_targets(["not-a-number"])


def test_non_positive_index_is_error(cli) -> None:
    with pytest.raises(ValueError, match="1-based"):
        cli._parse_targets(["0"])


def test_negative_index_is_error(cli) -> None:
    with pytest.raises(ValueError, match="1-based"):
        cli._parse_targets(["-1"])
