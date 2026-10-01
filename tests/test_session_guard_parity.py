"""The capability's comparison and the backbone's, held to one table of cases (#1254).

The cross-repository guard's comparison — the session's anchor against the
repository a change targets — has its home in the backbone
(`project_kit.session_guard.evaluate`, ADR-061 point 6). project-management's
guard keeps a copy (`_lib/session_guard.evaluate`) until it reads the
backbone's by command (#1220), and both run on one change: the capability's
before its verb runs, the backbone's before the request. When they disagree
the backbone refuses, so a copy that drifts stops landings rather than letting
one through — and this table keeps them from drifting: each case runs both
comparisons on real git repositories and expects one answer from them.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from project_kit import session_guard

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_GUARD = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "_lib"
) / "session_guard.py"


@pytest.fixture(scope="module")
def capability() -> ModuleType:
    """The capability's guard, loaded by path: its scripts are not a package."""
    name = "pm_session_guard_parity"
    spec = importlib.util.spec_from_file_location(name, CAPABILITY_GUARD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _repository(path: Path, origin: str | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    if origin is not None:
        _git(path, "remote", "add", "origin", origin)
    return path


def _plain(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _worktree(repository: Path, path: Path) -> Path:
    _git(
        repository,
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "--allow-empty",
        "-q",
        "-m",
        "init",
    )
    _git(repository, "worktree", "add", "-q", str(path))
    return path


#: Builds a case's directories under a temporary one: (the target, the anchor).
Build = Callable[[Path], "tuple[Path, Path | None]"]


@dataclass(frozen=True)
class Case:
    id: str
    build: Build
    verdict: str
    undetermined_kind: str | None = None
    #: git cannot be run while the comparisons ask it.
    git_fault: bool = False


def _same_by_common_directory(tmp: Path) -> tuple[Path, Path | None]:
    anchor = _repository(tmp / "a")
    return _plain(anchor / "nested" / "dir"), anchor


def _same_by_origin(anchor_origin: str, target_origin: str) -> Build:
    def build(tmp: Path) -> tuple[Path, Path | None]:
        return _repository(tmp / "b", target_origin), _repository(tmp / "a", anchor_origin)

    return build


def _different(tmp: Path) -> tuple[Path, Path | None]:
    anchor = _repository(tmp / "a", "https://github.com/octo/project.git")
    return _repository(tmp / "b", "https://github.com/octo/other.git"), anchor


def _different_without_origins(tmp: Path) -> tuple[Path, Path | None]:
    return _repository(tmp / "b"), _repository(tmp / "a")


def _worktree_of_the_sessions(tmp: Path) -> tuple[Path, Path | None]:
    anchor = _repository(tmp / "a")
    return _worktree(anchor, tmp / "worktree"), anchor


def _no_anchor(tmp: Path) -> tuple[Path, Path | None]:
    return _repository(tmp / "b"), None


def _anchor_not_a_repository(tmp: Path) -> tuple[Path, Path | None]:
    return _repository(tmp / "b"), _plain(tmp / "a")


def _target_not_a_repository(tmp: Path) -> tuple[Path, Path | None]:
    return _plain(tmp / "b"), _repository(tmp / "a")


def _two_repositories(tmp: Path) -> tuple[Path, Path | None]:
    return _repository(tmp / "b"), _repository(tmp / "a")


CASES = (
    Case("same-repository-by-common-directory", _same_by_common_directory, session_guard.SAME_REPO),
    Case(
        "same-by-origin-ssh-and-https",
        _same_by_origin("git@github.com:octo/project.git", "https://github.com/octo/project"),
        session_guard.SAME_REPO,
    ),
    Case(
        "same-by-origin-ssh-url-with-a-port",
        _same_by_origin("ssh://git@github.com:22/octo/project.git", "git@github.com:octo/project"),
        session_guard.SAME_REPO,
    ),
    Case(
        "same-by-origin-git-suffix-and-slash",
        _same_by_origin("https://github.com/octo/project.git", "https://github.com/octo/project/"),
        session_guard.SAME_REPO,
    ),
    Case(
        "same-by-origin-in-another-case",
        _same_by_origin("https://GitHub.com/Octo/Project", "https://github.com/octo/project.git"),
        session_guard.SAME_REPO,
    ),
    Case("a-different-repository", _different, session_guard.DIVERGED),
    Case("two-repositories-without-origins", _different_without_origins, session_guard.DIVERGED),
    Case(
        "a-worktree-of-the-sessions-repository",
        _worktree_of_the_sessions,
        session_guard.SAME_REPO,
    ),
    Case("no-anchor", _no_anchor, session_guard.UNDETERMINED, session_guard.NONCOVERAGE),
    Case(
        "an-anchor-that-is-not-a-repository",
        _anchor_not_a_repository,
        session_guard.UNDETERMINED,
        session_guard.NONCOVERAGE,
    ),
    Case(
        "a-target-that-is-not-a-repository",
        _target_not_a_repository,
        session_guard.UNDETERMINED,
        session_guard.NONCOVERAGE,
    ),
    Case(
        "a-git-fault",
        _two_repositories,
        session_guard.UNDETERMINED,
        session_guard.FAULT,
        git_fault=True,
    ),
)


def _without_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """git hangs on every question from here on, as far as the comparisons see."""
    run = subprocess.run

    def hanging(argv: Any, *args: Any, **kwargs: Any) -> Any:
        if list(argv)[:1] == ["git"]:
            raise subprocess.TimeoutExpired(argv, 5)
        return run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", hanging)


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_the_two_comparisons_answer_alike(
    case: Case, capability: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, anchor = case.build(tmp_path)
    if case.git_fault:
        _without_git(monkeypatch)
    backbone = session_guard.evaluate(target, anchor)
    # The capability reads the anchor from the environment when handed none,
    # and the suite runs outside any session (conftest), so None is no anchor.
    copy = capability.evaluate(
        target_cwd=str(target), anchor_dir=str(anchor) if anchor is not None else None
    )
    assert (backbone.verdict, backbone.undetermined_kind) == (
        case.verdict,
        case.undetermined_kind,
    )
    assert (copy.verdict, copy.undetermined_kind) == (case.verdict, case.undetermined_kind)
    assert (backbone.anchor, backbone.target) == (copy.anchor_repo, copy.target_repo)


@pytest.mark.parametrize(
    "remote",
    [
        "git@github.com:Octo/Project.git",
        "ssh://git@github.com/octo/project.git",
        "ssh://git@ghe.example:2222/octo/project",
        "https://github.com/octo/project/",
        "http://user@github.com/octo/project.git",
        "/srv/git/Project.git/",
        "file:///srv/git/project.git",
        "git://host",
        "not a url",
        "",
    ],
)
def test_the_two_normalisers_answer_alike(capability: ModuleType, remote: str) -> None:
    assert session_guard.normalize_origin_url(remote) == capability.normalize_origin_url(remote)
