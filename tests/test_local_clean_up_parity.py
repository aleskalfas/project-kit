"""The release step's local clean-up and project-management's, held to one table of cases (#2189).

After a merge, `pkit release merge` cleans up the clone it runs in
(`release._git_cleanup_local`), and so do project-management's merge verbs
(`_lib/pr_merge.cleanup_local`). The backbone imports no capability's code,
and the capability's scripts run without the backbone's package, so each
keeps its own copy of the clean-up. This table keeps the copies in step: each
case runs both on one clone, as `git` answers for it, and expects the same git
commands from them, in the same order.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from project_kit import release

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

#: The branch that merged, the default branch, and the heads the clone knows.
BRANCH = "fix/42-slug"
DEFAULT = "main"
MERGED = "sha-merged"
TIP = "sha-tip"

#: The git commands that change the clone, as a case names them.
_MOVES = {"checkout": "checkout", "pull": "pull", "branch": "delete"}


@pytest.fixture(scope="module")
def capability() -> Iterator[ModuleType]:
    """project-management's `_lib.pr_merge`, loaded by path: its scripts are not a package."""
    sys.path.insert(0, str(SCRIPTS))
    name = "pm_pr_merge_for_local_clean_up_parity"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "_lib" / "pr_merge.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS))


@dataclass(frozen=True)
class Case:
    """A clone, how the branch on GitHub ended, and the commands that change
    the clone, in order (`moves`): `checkout`, `pull`, `delete`."""

    id: str
    moves: str
    #: The branch the clone is on; None, a detached HEAD.
    current: str | None = BRANCH
    #: `git status --porcelain`'s lines: empty, a clean working tree.
    changes: str = ""
    #: git cannot read the working tree, in these words.
    status_fault: str = ""
    #: The clone has a local copy of the branch that merged, at `TIP`.
    has_branch: bool = True
    checkout_fault: str = ""
    pull_fault: str = ""
    delete_fault: str = ""
    #: The commits on the local copy the merge does not hold; "", git cannot tell.
    unmerged: str = "0"
    merged_head: str = MERGED
    remote: str = "deleted"
    cross_repository: bool = False


CASES = (
    Case("on-the-branch-that-merged", "checkout pull delete"),
    Case("on-the-default-branch", "pull", current=DEFAULT),
    Case("on-the-default-branch-without-the-branch", "pull", current=DEFAULT, has_branch=False),
    Case("on-another-branch", "", current="feat/7-next"),
    Case("on-another-branch-with-changes", "", current="feat/7-next", changes=" M a.py\n"),
    Case("on-a-detached-head", "", current=None),
    Case("changes-on-the-branch-that-merged", "", changes=" M a.py\n"),
    Case("untracked-files-on-the-branch-that-merged", "", changes="?? notes.txt\n"),
    Case("changes-on-the-default-branch", "", current=DEFAULT, changes="A  b.py\n"),
    Case("a-working-tree-git-cannot-read", "", status_fault="fatal: index file corrupt"),
    Case("the-checkout-fails", "checkout", checkout_fault="fatal: 'main' is already used"),
    Case("the-pull-fails", "checkout pull delete", pull_fault="fatal: Not possible"),
    Case("the-fast-forward-fails", "pull", current=DEFAULT, pull_fault="fatal: Not possible"),
    Case("the-delete-fails", "checkout pull delete", delete_fault="error: cannot delete"),
    Case("the-remote-branch-was-kept", "checkout pull", remote="kept"),
    Case("work-since-the-merge", "checkout pull", unmerged="2"),
    Case("a-clone-that-cannot-tell", "checkout pull", unmerged=""),
    Case("no-merged-head-known", "checkout pull", merged_head=""),
    Case("a-fork", "checkout pull", cross_repository=True, remote="refused"),
)


def _done(argv: list[str], code: int = 0, out: str = "", err: str = "") -> Any:
    return subprocess.CompletedProcess(argv, code, stdout=out, stderr=err)


def _git(case: Case, seen: list[list[str]]) -> Callable[..., Any]:
    """`subprocess.run` as git answers it for `case`'s clone, each command recorded in `seen`."""

    def run(argv: Sequence[str], *args: Any, **kwargs: Any) -> Any:
        git = list(argv)
        seen.append(git)
        assert git[:1] == ["git"], git
        command = git[1]
        if command == "symbolic-ref":
            return _done(git, 0 if case.current else 1, f"{case.current or ''}\n")
        if command == "status":
            code = 128 if case.status_fault else 0
            return _done(git, code, case.changes, case.status_fault)
        if command == "rev-parse":
            return _done(git, 0, f"{TIP}\n") if case.has_branch else _done(git, 1)
        if command == "rev-list":
            return _done(git, 0 if case.unmerged else 128, f"{case.unmerged}\n")
        faults = {
            "checkout": case.checkout_fault,
            "pull": case.pull_fault,
            "branch": case.delete_fault,
        }
        fault = faults[command]
        return _done(git, 1 if fault else 0, err=fault)

    return run


def _release(case: Case, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    seen: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _git(case, seen))
    release._git_cleanup_local(
        BRANCH,
        DEFAULT,
        Path("/repo"),
        cross_repository=case.cross_repository,
        merged_head=case.merged_head,
        remote=case.remote,
    )
    return seen


def _project_management(
    case: Case, capability: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> list[list[str]]:
    seen: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _git(case, seen))
    monkeypatch.setattr(capability.default_branch, "name", lambda config, **kwargs: DEFAULT)
    capability.cleanup_local(
        BRANCH,
        {},
        cross_repository=case.cross_repository,
        merged_head=case.merged_head,
        remote=case.remote,
    )
    return seen


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_the_two_clean_ups_run_the_same_git_commands(
    case: Case, capability: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    ours = _release(case, monkeypatch)
    theirs = _project_management(case, capability, monkeypatch)
    assert ours == theirs
    moves = [_MOVES[argv[1]] for argv in ours if argv[1] in _MOVES]
    assert " ".join(moves) == case.moves


def test_the_rows_are_told_apart() -> None:
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids))
