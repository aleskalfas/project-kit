"""Shared fixtures: the prototype's root on the import path, and its two pieces."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.model import Piece  # noqa: E402

PIECES = ["friday-slice", "sockets-figure"]


@pytest.fixture(scope="session")
def root():
    return ROOT


@pytest.fixture(scope="session", params=PIECES)
def piece(request):
    return Piece(ROOT / "pieces" / request.param)


@pytest.fixture(scope="session")
def friday():
    return Piece(ROOT / "pieces" / "friday-slice")


def pytest_terminal_summary(terminalreporter):
    """Print the pass test's line counts after every run."""
    module = sys.modules.get("test_pass")
    for row in getattr(module, "RESULTS", []):
        terminalreporter.write_line(row)
