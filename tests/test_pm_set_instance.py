"""Clone-local instance identity — set-instance / _lib.instance_identity (DEC-035).

Pins the opt-in per-clone id: write/read/clear round-trips, the fail-closed
tolerance (a missing / corrupt runtime file reads as an unset clone, never an
error, so the activation gate degrades to the no-op default), and the positive-int
constraint. A clone includes its linked worktrees (DEC-035 point 1): a worktree
with no id file of its own reads the main working tree's through git's common
directory, a worktree that sets its own id keeps it, and a worktree of a bare
repository reads its own file alone.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests.adopter_repo import GitRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB = SCRIPTS / "_lib"
MODULE = LIB / "instance_identity.py"
CAPABILITY = Path(".pkit") / "capabilities" / "project-management"


@pytest.fixture(scope="module")
def ident():
    # The module reads git's common directory through `_lib.session_guard`.
    for path in (LIB, SCRIPTS):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
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


# --- a clone and its linked worktrees (DEC-035 point 1) ------------------------


def _clone(root: Path) -> GitRepo:
    """A repository with the capability's folder committed, so each worktree has it."""
    repo = GitRepo.init(root)
    repo.commit("init", {(CAPABILITY / "README.md").as_posix(): "pm\n"})
    return repo


def _worktree(repository: Path, dest: Path) -> Path:
    """Add a linked worktree of the repository at `repository` (its git directory
    when bare) at `dest`, on a branch of its own."""
    GitRepo(repository).git("worktree", "add", "-q", "-b", dest.name, str(dest))
    return dest


def test_a_worktree_without_its_own_id_reads_the_clones(ident, tmp_path: Path) -> None:
    """The issue's case: a subagent's worktree acts as the clone it belongs to."""
    clone = _clone(tmp_path / "clone")
    ident.write_instance_id(clone.root / CAPABILITY, 2)
    worktree = _worktree(clone.root, tmp_path / "wt")

    assert ident.read_instance_id(worktree / CAPABILITY) == 2
    assert ident.identity_source(worktree / CAPABILITY) == ident.identity_path(
        clone.root.resolve() / CAPABILITY
    )


def test_a_worktree_of_a_clone_with_no_id_is_unset(ident, tmp_path: Path) -> None:
    clone = _clone(tmp_path / "clone")
    worktree = _worktree(clone.root, tmp_path / "wt")
    assert ident.read_instance_id(worktree / CAPABILITY) is None
    assert ident.identity_source(worktree / CAPABILITY) is None


def test_a_worktree_with_its_own_id_keeps_it(ident, tmp_path: Path) -> None:
    clone = _clone(tmp_path / "clone")
    ident.write_instance_id(clone.root / CAPABILITY, 2)
    worktree = _worktree(clone.root, tmp_path / "wt")
    ident.write_instance_id(worktree / CAPABILITY, 3)

    assert ident.read_instance_id(worktree / CAPABILITY) == 3
    assert ident.identity_source(worktree / CAPABILITY) == ident.identity_path(
        worktree / CAPABILITY
    )
    assert ident.read_instance_id(clone.root / CAPABILITY) == 2


def test_a_worktrees_own_file_decides_even_when_it_is_corrupt(ident, tmp_path: Path) -> None:
    """A worktree's own file fails closed to unset; it does not fall back to the clone's."""
    clone = _clone(tmp_path / "clone")
    ident.write_instance_id(clone.root / CAPABILITY, 2)
    worktree = _worktree(clone.root, tmp_path / "wt")
    own = ident.identity_path(worktree / CAPABILITY)
    own.parent.mkdir(parents=True)
    own.write_text("{ not json", encoding="utf-8")

    assert ident.read_instance_id(worktree / CAPABILITY) is None


def test_the_main_working_tree_reads_its_own_file_alone(ident, tmp_path: Path) -> None:
    """A worktree's id never flows back to the clone."""
    clone = _clone(tmp_path / "clone")
    worktree = _worktree(clone.root, tmp_path / "wt")
    ident.write_instance_id(worktree / CAPABILITY, 3)

    assert ident.read_instance_id(clone.root / CAPABILITY) is None


def test_setting_an_id_in_a_worktree_writes_its_own_file(ident, tmp_path: Path) -> None:
    """`set-instance` writes locally, so a worktree can take a number of its own."""
    clone = _clone(tmp_path / "clone")
    ident.write_instance_id(clone.root / CAPABILITY, 2)
    worktree = _worktree(clone.root, tmp_path / "wt")

    written = ident.write_instance_id(worktree / CAPABILITY, 3)

    assert written == ident.identity_path(worktree / CAPABILITY)
    clones = json.loads(ident.identity_path(clone.root / CAPABILITY).read_text(encoding="utf-8"))
    assert clones == {"instance": 2}


def test_clearing_a_worktrees_own_id_leaves_the_clones(ident, tmp_path: Path) -> None:
    clone = _clone(tmp_path / "clone")
    ident.write_instance_id(clone.root / CAPABILITY, 2)
    worktree = _worktree(clone.root, tmp_path / "wt")
    ident.write_instance_id(worktree / CAPABILITY, 3)

    assert ident.clear_instance_id(worktree / CAPABILITY) is True
    assert ident.read_instance_id(worktree / CAPABILITY) == 2
    assert ident.clear_instance_id(worktree / CAPABILITY) is False
    assert ident.read_instance_id(clone.root / CAPABILITY) == 2


@pytest.mark.parametrize("git_directory", [".git", "project.git"])
def test_a_worktree_of_a_bare_repository_reads_its_own_file_alone(
    ident, tmp_path: Path, git_directory: str
) -> None:
    """A bare repository has no main working tree: a file where one would sit is not read."""
    source = _clone(tmp_path / "source")
    holder = tmp_path / "project"
    bare = holder / git_directory
    GitRepo(tmp_path).git("clone", "-q", "--bare", str(source.root), str(bare))
    worktree = _worktree(bare, holder / "wt")
    ident.write_instance_id(holder / CAPABILITY, 2)

    assert ident.read_instance_id(worktree / CAPABILITY) is None
    ident.write_instance_id(worktree / CAPABILITY, 4)
    assert ident.read_instance_id(worktree / CAPABILITY) == 4


def test_a_worktree_where_git_cannot_run_reads_as_unset(
    ident, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail closed: no git means no clone to read from, never a crash."""
    clone = _clone(tmp_path / "clone")
    ident.write_instance_id(clone.root / CAPABILITY, 2)
    worktree = _worktree(clone.root, tmp_path / "wt")
    monkeypatch.setenv("PATH", str(tmp_path / "no-git-here"))

    assert ident.read_instance_id(worktree / CAPABILITY) is None


# --- set-instance --show / --clear in a worktree -------------------------------


@pytest.fixture
def set_instance(ident, monkeypatch: pytest.MonkeyPatch):
    """The `set-instance` script, its prerequisite and foreign-repo gates passed."""
    spec = importlib.util.spec_from_file_location(
        "pm_set_instance_under_test", SCRIPTS / "set-instance.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.bootstrap_gate, "enforce", lambda *_a, **_k: True)
    monkeypatch.setattr(module.session_guard, "enforce", lambda *_a, **_k: True)
    return module


def _run(module, monkeypatch: pytest.MonkeyPatch, capability_root: Path, *args: str) -> int:
    argv = ["set-instance", *args, "--capability-root", str(capability_root)]
    monkeypatch.setattr(sys, "argv", argv)
    return module.main()


def test_show_names_the_main_working_tree_for_the_clones_id(
    set_instance, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    clone = _clone(tmp_path / "clone")
    set_instance.write_instance_id(clone.root / CAPABILITY, 2)
    worktree = _worktree(clone.root, tmp_path / "wt")

    assert _run(set_instance, monkeypatch, worktree / CAPABILITY, "--show") == 0
    out = capsys.readouterr().out
    assert out.startswith("instance: 2 ")
    assert "main working tree" in out

    set_instance.write_instance_id(worktree / CAPABILITY, 3)
    assert _run(set_instance, monkeypatch, worktree / CAPABILITY, "--show") == 0
    assert capsys.readouterr().out == "instance: 3\n"


def test_clear_in_a_worktree_says_it_reads_the_clones_id(
    set_instance, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    clone = _clone(tmp_path / "clone")
    set_instance.write_instance_id(clone.root / CAPABILITY, 2)
    worktree = _worktree(clone.root, tmp_path / "wt")
    set_instance.write_instance_id(worktree / CAPABILITY, 3)

    assert _run(set_instance, monkeypatch, worktree / CAPABILITY, "--clear") == 0
    assert "instance 2" in capsys.readouterr().out

    assert _run(set_instance, monkeypatch, worktree / CAPABILITY, "--clear") == 0
    out = capsys.readouterr().out
    assert "no instance id of its own" in out
    assert "instance 2" in out
    assert set_instance.read_instance_id(clone.root / CAPABILITY) == 2
