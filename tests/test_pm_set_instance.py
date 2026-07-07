"""Clone-local instance identity — set-instance / _lib.instance_identity (DEC-035).

Pins the opt-in per-clone id: write/read/clear round-trips, the fail-closed
tolerance (a missing / corrupt runtime file reads as an unset clone, never an
error, so the activation gate degrades to the no-op default), and the positive-int
constraint.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "_lib"
MODULE = LIB / "instance_identity.py"


@pytest.fixture(scope="module")
def ident():
    if str(LIB) not in sys.path:
        sys.path.insert(0, str(LIB))
    spec = importlib.util.spec_from_file_location("pm_instance_identity_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_instance_identity_under_test"] = module
    spec.loader.exec_module(module)
    return module


def test_absent_reads_as_unset(ident, tmp_path: Path) -> None:
    """A clone that never set an id reads None — the no-op activation default."""
    assert ident.read_instance_id(tmp_path) is None


def test_write_then_read_round_trip(ident, tmp_path: Path) -> None:
    path = ident.write_instance_id(tmp_path, 2)
    assert path == ident.identity_path(tmp_path)
    assert path.is_file()
    assert ident.read_instance_id(tmp_path) == 2


def test_overwrite_replaces(ident, tmp_path: Path) -> None:
    ident.write_instance_id(tmp_path, 2)
    ident.write_instance_id(tmp_path, 5)
    assert ident.read_instance_id(tmp_path) == 5


def test_clear_removes_and_is_idempotent(ident, tmp_path: Path) -> None:
    ident.write_instance_id(tmp_path, 3)
    assert ident.clear_instance_id(tmp_path) is True
    assert ident.read_instance_id(tmp_path) is None
    assert ident.clear_instance_id(tmp_path) is False  # already unset — no error


def test_non_positive_id_refused(ident, tmp_path: Path) -> None:
    for bad in (0, -1):
        with pytest.raises(ValueError):
            ident.write_instance_id(tmp_path, bad)


def test_bool_is_not_a_valid_id(ident, tmp_path: Path) -> None:
    """`True` is an int subclass — guard against it being taken as instance 1."""
    with pytest.raises(ValueError):
        ident.write_instance_id(tmp_path, True)  # type: ignore[arg-type]


def test_corrupt_file_reads_as_unset(ident, tmp_path: Path) -> None:
    """A malformed runtime file fails closed to the no-op default, never crashes."""
    path = ident.identity_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")
    assert ident.read_instance_id(tmp_path) is None

    path.write_text('{"instance": "two"}', encoding="utf-8")  # wrong type
    assert ident.read_instance_id(tmp_path) is None
