"""Tests for `_lib/pr_head.py`: where a pull request's head is fetched from, and the
one fetch of a commit this clone lacks (project-management, #2663)."""

from __future__ import annotations

import importlib
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent / ".pkit" / "capabilities" / "project-management"
) / "scripts"

HEAD_OID = "c" * 40


@pytest.fixture(scope="module")
def ph() -> Iterator[ModuleType]:
    """The module, imported as the pm scripts import it."""
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        yield importlib.import_module("_lib.pr_head")
    finally:
        if inserted:
            sys.path.remove(str(SCRIPTS_DIR))


class Call:
    """One `git` call: its arguments after `git`, and the environment it was given."""

    def __init__(self, argv: tuple[str, ...], env: dict[str, str] | None) -> None:
        self.argv = argv
        self.env = env


def clone_git(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    *,
    holds: bool,
    fetch_brings: bool,
    said: str = "fatal: couldn't find ref\n",
) -> list[Call]:
    """`git` as a clone answers it, recorded, in place of `module`'s own: whether it
    holds `HEAD_OID`, and whether a fetch brings it, or exits 128 saying `said`."""
    held = {HEAD_OID} if holds else set()
    calls: list[Call] = []

    def git(*argv: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(Call(argv, env))
        if argv[0] == "cat-file":
            return subprocess.CompletedProcess(argv, 0 if HEAD_OID in held else 1, "", "")
        if argv[0] == "fetch":
            if not fetch_brings:
                return subprocess.CompletedProcess(argv, 128, "", said)
            held.add(HEAD_OID)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(module, "_git", git)
    return calls


def _fetches(calls: list[Call]) -> list[Call]:
    return [call for call in calls if call.argv[0] == "fetch"]


def _base_resolved(ph: ModuleType, monkeypatch, ref: str, resolved: str | None) -> None:
    """The backbone resolves every base named to `ref`, `resolved` as it says."""
    base = ph.default_branch.Base(ref, "e" * 40, None, None, resolved)
    monkeypatch.setattr(ph.default_branch, "check_base", lambda _named=None: base)


@pytest.mark.parametrize(
    ("cross_repository", "remote", "ref"),
    [(False, "fork", "refs/heads/feat/7-x"), (True, "upstream", "refs/pull/7/head")],
    ids=["same-repository", "fork"],
)
def test_a_head_this_clone_lacks_is_fetched_from_its_source(
    ph: ModuleType, monkeypatch, cross_repository: bool, remote: str, ref: str
) -> None:
    """A PR from the base's own repository is fetched from its branch, on the remote
    the branch is pushed to. One from a fork is fetched by the ref the base repository
    keeps for it, on the base's remote as the base is fetched, never the branch's."""
    calls = clone_git(monkeypatch, ph, holds=False, fetch_brings=True)
    _base_resolved(ph, monkeypatch, "upstream/main", "remote")
    source = ph.pull_request_source(
        "feat/7-x", 7, cross_repository=cross_repository, base="main", remote="fork"
    )
    assert source == ph.Source(remote, ref)
    assert ph.fetch_head(HEAD_OID, source) is None
    assert [call.argv for call in _fetches(calls)] == [
        ("fetch", "--quiet", "--no-tags", remote, ref)
    ]


def test_a_commit_given_no_source_is_fetched_by_its_object_name_from_origin(
    ph: ModuleType, monkeypatch
) -> None:
    calls = clone_git(monkeypatch, ph, holds=False, fetch_brings=True)
    assert ph.fetch(HEAD_OID) == ph.Fetched(HEAD_OID, True, "origin", HEAD_OID, 0, ())
    assert [call.argv for call in _fetches(calls)] == [
        ("fetch", "--quiet", "--no-tags", "origin", HEAD_OID)
    ]


@pytest.mark.parametrize(
    "source", [None, ("upstream", "refs/pull/7/head")], ids=["by-object-name", "by-ref"]
)
def test_a_fetch_never_prompts_for_credentials(
    ph: ModuleType, monkeypatch, source: tuple[str, str] | None
) -> None:
    """A pm script runs unattended, whichever way it fetches."""
    calls = clone_git(monkeypatch, ph, holds=False, fetch_brings=True)
    ph.fetch(HEAD_OID, None if source is None else ph.Source(*source))
    (fetched,) = _fetches(calls)
    assert fetched.env is not None and fetched.env["GIT_TERMINAL_PROMPT"] == "0"


def test_a_head_this_clone_holds_is_not_fetched(ph: ModuleType, monkeypatch) -> None:
    calls = clone_git(monkeypatch, ph, holds=True, fetch_brings=True)
    assert ph.fetch_head(HEAD_OID, ph.Source("origin", "refs/heads/feat/7-x")) is None
    assert ph.fetch(HEAD_OID) == ph.Fetched(HEAD_OID, held=True)
    assert _fetches(calls) == []


@pytest.mark.parametrize(
    ("said", "why"),
    [
        (
            "warning: one\n\nfatal: couldn't find ref\n",
            "fetching refs/heads/feat/7-x from origin failed: fatal: couldn't find ref",
        ),
        ("", "fetching refs/heads/feat/7-x from origin did not bring it"),
    ],
    ids=["git-said-why", "git-said-nothing"],
)
def test_a_head_no_fetch_brings_says_why(ph: ModuleType, monkeypatch, said: str, why: str) -> None:
    """What git said, a line each with blank ones left out, and the head's line on its
    last."""
    clone_git(monkeypatch, ph, holds=False, fetch_brings=False, said=said)
    source = ph.Source("origin", "refs/heads/feat/7-x")
    found = ph.fetch(HEAD_OID, source)
    assert (found.held, found.returncode) == (False, 128)
    assert found.said == tuple(line for line in said.splitlines() if line)
    assert ph.fetch_head(HEAD_OID, source) == f"the head ccccccc is not in this clone, and {why}"


@pytest.mark.parametrize("resolved", ["local", None], ids=["local-branch", "revision"])
def test_a_base_that_names_no_remote_s_branch_is_fetched_from_origin(
    ph: ModuleType, monkeypatch, resolved: str | None
) -> None:
    _base_resolved(ph, monkeypatch, "main", resolved)
    assert ph.base_remote("main") == "origin"


def test_a_base_the_backbone_cannot_resolve_is_fetched_from_origin(
    ph: ModuleType, monkeypatch
) -> None:
    def unanswered(_named: Any = None) -> Any:
        raise ph.default_branch.Unanswered("no answer")

    monkeypatch.setattr(ph.default_branch, "check_base", unanswered)
    assert ph.base_remote("main") == "origin"


def test_a_remote_s_branch_names_its_remote_and_branch(ph: ModuleType) -> None:
    def base(ref: str, resolved: str | None) -> Any:
        return ph.default_branch.Base(ref, "e" * 40, None, None, resolved)

    assert ph.remote_branch(base("upstream/release/2", "remote")) == ("upstream", "release/2")
    assert ph.remote_branch(base("main", "local")) is None
    assert ph.remote_branch(base("upstream", "remote")) is None
