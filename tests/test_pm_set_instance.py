"""Clone-local instance identity — set-instance / _lib.instance_identity (DEC-035).

Pins the opt-in per-clone id: write/read/clear round-trips, the fail-closed
tolerance (a missing / corrupt runtime file reads as an unset clone, never an
error, so the activation gate degrades to the no-op default), and the positive-int
constraint. In a project with a topology (DEC-059 point 6), the runtime file
keeps the seat the clone took as a hint, and set-instance refuses a typed number.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

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
        ident.write_instance_id(tmp_path, True)


def test_corrupt_file_reads_as_unset(ident, tmp_path: Path) -> None:
    """A malformed runtime file fails closed to the no-op default, never crashes."""
    path = ident.identity_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")
    assert ident.read_instance_id(tmp_path) is None

    path.write_text('{"instance": "two"}', encoding="utf-8")  # wrong type
    assert ident.read_instance_id(tmp_path) is None


# ---- the clone's key (DEC-058 point 5) ------------------------------------------


def test_a_clone_has_no_key_until_it_is_asked_for_one(ident, tmp_path: Path) -> None:
    assert ident.read_clone_key(tmp_path) is None
    assert not ident.identity_path(tmp_path).exists()


def test_the_key_is_generated_once_and_kept(ident, tmp_path: Path) -> None:
    key = ident.ensure_clone_key(tmp_path)
    assert key and len(key) == 32
    assert ident.ensure_clone_key(tmp_path) == key
    assert ident.read_clone_key(tmp_path) == key
    # A key alone sets no instance id: the activation gate stays off.
    assert ident.read_instance_id(tmp_path) is None


def test_two_clones_get_keys_of_their_own(ident, tmp_path: Path) -> None:
    assert ident.ensure_clone_key(tmp_path / "a") != ident.ensure_clone_key(tmp_path / "b")


def test_setting_and_clearing_the_id_keeps_the_key(ident, tmp_path: Path) -> None:
    key = ident.ensure_clone_key(tmp_path)
    ident.write_instance_id(tmp_path, 4)
    assert ident.read_clone_key(tmp_path) == key and ident.read_instance_id(tmp_path) == 4
    assert ident.clear_instance_id(tmp_path) is True
    assert ident.read_instance_id(tmp_path) is None
    assert ident.read_clone_key(tmp_path) == key
    assert ident.clear_instance_id(tmp_path) is False  # the key alone is no id


def test_a_corrupt_file_holds_no_key(ident, tmp_path: Path) -> None:
    path = ident.identity_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")
    assert ident.read_clone_key(tmp_path) is None


# ---- the seat's hint (DEC-059 point 6) ------------------------------------------


def test_the_seat_a_clone_took_is_kept_beside_its_key_and_number(ident, tmp_path: Path) -> None:
    assert ident.read_seat_hint(tmp_path) is None
    key = ident.ensure_clone_key(tmp_path)
    ident.write_instance_id(tmp_path, 4)
    ident.write_seat_hint(tmp_path, "worker-1")
    assert ident.read_seat_hint(tmp_path) == "worker-1"
    assert ident.clear_seat_hint(tmp_path) is True
    assert ident.read_seat_hint(tmp_path) is None
    assert ident.read_clone_key(tmp_path) == key and ident.read_instance_id(tmp_path) == 4
    assert ident.clear_seat_hint(tmp_path) is False


def test_clearing_the_number_keeps_the_seat(ident, tmp_path: Path) -> None:
    ident.write_instance_id(tmp_path, 4)
    ident.write_seat_hint(tmp_path, "worker-1")
    assert ident.clear_instance_id(tmp_path) is True
    assert ident.read_seat_hint(tmp_path) == "worker-1"
    assert ident.clear_seat_hint(tmp_path) is True
    assert not ident.identity_path(tmp_path).exists()


def test_a_seat_is_named_or_not_kept(ident, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ident.write_seat_hint(tmp_path, "")


# ---- set-instance in a project with a topology (DEC-059 point 6) -----------------

SCRIPTS = LIB.parent
TOPOLOGY_REL = ".pkit/capabilities/project-management/project/topology.yaml"


@pytest.fixture(scope="module")
def script():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "pm_set_instance_under_test", SCRIPTS / "set-instance.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_set_instance_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def fresh_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from _lib import default_branch

    monkeypatch.setattr(default_branch, "_read", {})
    monkeypatch.setattr(default_branch, "_warned", set())


def _backbone(tip: str | None = "c0ffee") -> Any:
    def run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        document = {
            "schema_version": 1,
            "default_branch": {"name": "main", "ref": "origin/main", "commit": tip},
            "base": {"ref": "origin/main", "tip": tip, "fork": tip},
        }
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")

    return run


def _git(topology: bool) -> Any:
    text = json.dumps({"schema_version": 1, "seats": [{"name": "w", "role": "worker"}]})

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[0] == "ls-tree":
            held = f"{TOPOLOGY_REL}\0" if topology else ""
            return subprocess.CompletedProcess(args, 0, held, "")
        return subprocess.CompletedProcess(args, 0, text, "")

    return run


def _root(tmp_path: Path) -> Path:
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    root.mkdir(parents=True)
    return root


def test_a_typed_number_is_refused_where_the_default_branch_holds_a_topology(
    script, tmp_path: Path
) -> None:
    refusal = script.typed_number_refusal(_root(tmp_path), run=_backbone(), git=_git(True))
    assert refusal is not None
    assert "origin/main at c0ffee holds a topology" in refusal
    assert "`pkit pm take-seat`" in refusal


def test_a_typed_number_stands_where_the_default_branch_holds_none(script, tmp_path: Path) -> None:
    assert script.typed_number_refusal(_root(tmp_path), run=_backbone(), git=_git(False)) is None


def test_no_number_is_typed_on_a_guess(script, tmp_path: Path) -> None:
    """COR-054 point 4: where the default branch cannot be resolved."""
    refusal = script.typed_number_refusal(_root(tmp_path), run=_backbone(None), git=_git(True))
    assert refusal is not None and "could not be read from the default branch" in refusal
