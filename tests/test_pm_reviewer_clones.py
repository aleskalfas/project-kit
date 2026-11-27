"""Tests for `_lib/reviewer_clones.py`: where `review-pr`'s reviewers work (ADR-102).

- a seat's clone is one whose runtime folder names a seat; a linked worktree of
  one is not, and one git cannot tell about reads as one;
- the reviewer's clone is read from the code host in one call: its address, by
  how the checkout reaches the remote the default branch resolves through, the
  default branch's head, and the references to fetch;
- what cannot be read is a reason, never a clone;
- the brief says what the clone's working tree holds, and how the change is read.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

HEAD = "a" * 40
DEFAULT_HEAD = "b" * 40


@pytest.fixture(scope="module")
def rc() -> ModuleType:
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import reviewer_clones

    return reviewer_clones


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _seat(capability_root: Path, seat: str | None) -> None:
    identity = capability_root / "project" / "instance" / "clone.json"
    identity.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {"key": "k"}
    if seat is not None:
        data["seat"] = seat
    identity.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A repository with one commit."""
    root = tmp_path / "clone"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-q", "--no-verify", "-m", "first")
    return root


# --- a seat's clone ------------------------------------------------------------------


def test_a_clone_whose_runtime_folder_names_a_seat_is_a_seats_clone(
    rc: ModuleType, clone: Path
) -> None:
    capability_root = clone / ".pkit" / "capabilities" / "project-management"
    assert not rc.in_seat_clone(capability_root, clone)
    _seat(capability_root, None)
    assert not rc.in_seat_clone(capability_root, clone)
    _seat(capability_root, "worker-1")
    assert rc.in_seat_clone(capability_root, clone)


def test_a_linked_worktree_of_a_seats_clone_is_none(
    rc: ModuleType, clone: Path, tmp_path: Path
) -> None:
    linked = tmp_path / "linked"
    _git(clone, "worktree", "add", "-q", "--detach", str(linked))
    capability_root = linked / ".pkit" / "capabilities" / "project-management"
    _seat(capability_root, "worker-1")
    assert not rc.in_seat_clone(capability_root, linked)


def test_a_clone_git_cannot_tell_about_reads_as_a_seats_clone(
    rc: ModuleType, tmp_path: Path
) -> None:
    capability_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    _seat(capability_root, "worker-1")

    def failing(*argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 128, stdout="", stderr="not a repository")

    def missing(*_argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("git")

    assert rc.in_seat_clone(capability_root, tmp_path, git=failing)
    assert rc.in_seat_clone(capability_root, tmp_path, git=missing)


# --- the reviewer's clone ------------------------------------------------------------


def _host(
    rc: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    answer: object,
    *,
    code: int = 0,
    remote: str = "upstream",
) -> list[list[str]]:
    """The code host answering `answer`, through `gh`, and the default branch `main`
    resolving through `remote`. Returns each call made of `gh`."""
    calls: list[list[str]] = []

    def gh_run(argv: list[str], config: dict[str, Any], **_kwargs: Any) -> Any:
        calls.append(argv)
        stdout = answer if isinstance(answer, str) else json.dumps(answer)
        return subprocess.CompletedProcess(argv, code, stdout=stdout, stderr="refused")

    monkeypatch.setattr(rc, "gh_run", gh_run)
    monkeypatch.setattr(rc.default_branch, "name", lambda config: "main")
    monkeypatch.setattr(rc.pr_head, "base_remote", lambda base: remote)
    return calls


def _answer(oid: str = DEFAULT_HEAD) -> dict[str, Any]:
    return {
        "data": {
            "repository": {
                "url": "https://github.com/owner/repo",
                "sshUrl": "git@github.com:owner/repo.git",
                "ref": {"target": {"oid": oid}},
            }
        }
    }


def _reaching(url: str) -> Any:
    def git(*argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert argv == ("remote", "get-url", "upstream")
        return subprocess.CompletedProcess(argv, 0, stdout=f"{url}\n", stderr="")

    return git


@pytest.mark.parametrize(
    ("reached", "address"),
    [
        pytest.param("git@github.com:owner/repo.git", "git@github.com:owner/repo.git", id="ssh"),
        pytest.param("ssh://git@github.com/owner/repo", "git@github.com:owner/repo.git", id="url"),
        pytest.param("https://github.com/owner/repo.git", "https://github.com/owner/repo", id="h"),
    ],
)
def test_the_clone_is_read_from_the_code_host(
    rc: ModuleType, monkeypatch: pytest.MonkeyPatch, reached: str, address: str
) -> None:
    calls = _host(rc, monkeypatch, _answer())
    found = rc.read_clone(7, HEAD, "release", {}, git=_reaching(reached))
    assert found == rc.agent_runs.ReviewerClone(
        commit=DEFAULT_HEAD,
        remote="upstream",
        url=address,
        default_branch="main",
        branches=("release",),
        head_ref="refs/pull/7/head",
        head=HEAD,
    )
    (call,) = calls
    assert call[:3] == ["gh", "api", "graphql"]
    assert "ref=refs/heads/main" in call
    assert "owner={owner}" in call and "repo={repo}" in call


def test_a_change_against_the_default_branch_fetches_no_other(
    rc: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    _host(rc, monkeypatch, _answer())
    found = rc.read_clone(7, HEAD, "main", {}, git=_reaching("https://x"))
    assert found.branches == ()


@pytest.mark.parametrize(
    ("head", "answer", "code", "says"),
    [
        pytest.param("", _answer(), 0, "head could not be read", id="no-head"),
        pytest.param(HEAD, _answer(), 1, "refused", id="gh-fails"),
        pytest.param(HEAD, "{nope", 0, "not JSON", id="no-json"),
        pytest.param(HEAD, {"data": {}}, 0, "names no repository", id="no-repository"),
        pytest.param(HEAD, _answer("main"), 0, "no head of `main`", id="no-commit"),
        pytest.param(
            HEAD,
            {"data": {"repository": {"url": "", "sshUrl": "", "ref": None}}},
            0,
            "no address",
            id="no-address",
        ),
    ],
)
def test_what_cannot_be_read_is_a_reason(
    rc: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    head: str,
    answer: object,
    code: int,
    says: str,
) -> None:
    _host(rc, monkeypatch, answer, code=code)
    found = rc.read_clone(7, head, "main", {}, git=_reaching("https://x"))
    assert isinstance(found, str) and says in found


def test_a_default_branch_that_cannot_be_read_is_a_reason(
    rc: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unanswered(config: dict[str, Any]) -> str:
        raise rc.default_branch.Unanswered("the backbone did not answer")

    monkeypatch.setattr(rc.default_branch, "name", unanswered)
    found = rc.read_clone(7, HEAD, "main", {})
    assert found == "the default branch cannot be read: the backbone did not answer"


def test_the_brief_says_what_the_clones_tree_holds(rc: ModuleType) -> None:
    clone = rc.agent_runs.ReviewerClone(
        commit=DEFAULT_HEAD,
        remote="origin",
        url="https://x",
        default_branch="main",
        branches=(),
        head_ref="refs/pull/7/head",
        head=HEAD,
    )
    brief = rc.brief(clone, HEAD)
    assert f"Its working tree holds the default branch's head, {DEFAULT_HEAD}, not the change" in (
        brief
    )
    assert f"`git show {HEAD}:<path>`" in brief
