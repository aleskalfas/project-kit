"""Which local branch is an issue's: the one reading the verbs share (#1608).

`_lib/issue_branch` lists the clone's local branches that match
`<type>/<N>-<slug>` (DEC-013). One match is the issue's branch. Of several, the
one with the issue's open pull request is, read in one `gh` call. With none
open, more than one open, or no answer from `gh`, no branch is chosen and the
refusal names each. These tests hold the reading itself, that every verb which
finds an issue's branch by name reads it there, and how each verb meets a
reading that chose none. `done-work` and `land-work` are held in their own
modules, beside the merged-PR completion they keep.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from tests import pm_issue_branch_support as support
from tests.adopter_repo import sign_nothing

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAP_ROOT / "scripts"

#: Every verb that finds an issue's branch by name.
VERBS = (
    "start-work",
    "create-draft",
    "review-work",
    "back-to-draft",
    "review-pr",
    "done-work",
    "land-work",
)

PR_BRANCH = "fix/42-do-the-thing"
#: Left behind by an earlier attempt. It sorts first, as the stale one did on #1367.
STALE = "fix/42-a-stopped-attempt"


@pytest.fixture(scope="module")
def lib() -> ModuleType:
    sys.path.insert(0, str(SCRIPTS))
    from _lib import issue_branch

    return issue_branch


def _local(lib: ModuleType, monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    monkeypatch.setattr(lib, "_local_branches", lambda: names)


def _gh(
    lib: ModuleType, monkeypatch: pytest.MonkeyPatch, open_on: dict[str, list[int]] | None
) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(lib, "gh_run", support.fake_gh(open_on, calls))
    return calls


# ---- the reading ---------------------------------------------------------------


def test_no_matching_branch_is_no_branch_and_asks_nothing(lib, monkeypatch) -> None:
    _local(lib, monkeypatch, "main", "feat/7-other-issue")
    calls = _gh(lib, monkeypatch, open_on={})
    reading = lib.read(42, {})
    assert (reading.branch, reading.refusal, reading.matching) == (None, "", ())
    assert calls == []


def test_one_matching_branch_is_the_issue_s_and_asks_nothing(lib, monkeypatch) -> None:
    _local(lib, monkeypatch, "main", PR_BRANCH, "fix/420-another-issue")
    calls = _gh(lib, monkeypatch, open_on={})
    reading = lib.read(42, {})
    assert reading.branch == PR_BRANCH
    assert reading.refusal == ""
    assert calls == []


def test_of_two_matching_the_one_with_the_open_pr_wins(lib, monkeypatch) -> None:
    _local(lib, monkeypatch, STALE, PR_BRANCH)
    calls = _gh(lib, monkeypatch, open_on={PR_BRANCH: [1604]})
    reading = lib.read(42, {})
    assert reading.branch == PR_BRANCH
    assert reading.refusal == ""
    assert not reading.none_open
    # One call for both, each branch passed as a variable, not written into the query.
    assert len(calls) == 1
    assert support.asked(calls[0]) == {"b0": STALE, "b1": PR_BRANCH}
    query = next(a for a in calls[0] if a.startswith("query="))
    assert STALE not in query
    assert PR_BRANCH not in query


def test_of_two_matching_with_none_open_none_is_chosen_and_each_is_named(lib, monkeypatch) -> None:
    _local(lib, monkeypatch, STALE, PR_BRANCH)
    _gh(lib, monkeypatch, open_on={})
    reading = lib.read(42, {})
    assert reading.branch is None
    assert reading.none_open
    assert reading.refusal.splitlines() == [
        "2 local branches match `*/42-*`, and none has an open pull request, so which is "
        "#42's branch cannot be told:",
        f"  - {STALE}: no open pull request",
        f"  - {PR_BRANCH}: no open pull request",
        "Delete or rename the branches that are not #42's, then run it again.",
    ]


def test_of_two_matching_with_both_open_none_is_chosen_and_each_pr_is_named(
    lib, monkeypatch
) -> None:
    _local(lib, monkeypatch, STALE, PR_BRANCH)
    _gh(lib, monkeypatch, open_on={STALE: [1603], PR_BRANCH: [1604]})
    reading = lib.read(42, {})
    assert reading.branch is None
    assert not reading.none_open
    assert reading.refusal.splitlines() == [
        "2 local branches match `*/42-*`, and more than one has an open pull request, so "
        "which is #42's branch cannot be told:",
        f"  - {STALE}: open pull request #1603",
        f"  - {PR_BRANCH}: open pull request #1604",
        "Close the pull requests that are not #42's, then run it again.",
    ]


@pytest.mark.parametrize(
    ("stdout", "returncode", "why"),
    [
        ("", 1, "HTTP 502: Bad Gateway"),
        ("not json", 0, "gh's answer is not JSON"),
        ('{"data": {"repository": null}}', 0, "gh's answer names no repository"),
        ('{"data": {"repository": {"b0": {"nodes": []}}}}', 0, f"says nothing of {PR_BRANCH}"),
    ],
    ids=["gh-failed", "not-json", "no-repository", "a-branch-missing"],
)
def test_an_unanswered_reading_is_never_none_open(
    lib, monkeypatch, stdout: str, returncode: int, why: str
) -> None:
    _local(lib, monkeypatch, STALE, PR_BRANCH)

    def gh_run(argv: list[str], config: Any, **_kw: Any) -> Any:
        return subprocess.CompletedProcess(argv, returncode, stdout, "HTTP 502: Bad Gateway")

    monkeypatch.setattr(lib, "gh_run", gh_run)
    reading = lib.read(42, {})
    assert reading.branch is None
    assert not reading.none_open
    assert why in reading.unread
    assert reading.refusal == (
        f"2 local branches match `*/42-*` ({STALE}, {PR_BRANCH}), and whether any of them "
        f"has an open pull request could not be read: {reading.unread}. Which is #42's "
        "branch cannot be told. Run it again once gh answers."
    )


def test_a_branch_naming_the_issue_in_another_shape_is_never_its_branch(lib, monkeypatch) -> None:
    _local(lib, monkeypatch, "fix/42", "fix/42-Upper", "Fix/42-x", "fix/42-ok", "fix/420-x")
    reading = lib.read(42, {})
    assert reading.matching == ("fix/42-ok",)
    assert reading.misshapen == ("fix/42", "fix/42-Upper")
    assert reading.branch == "fix/42-ok"


def _git(cwd: Path, *argv: str) -> str:
    proc = subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def test_the_local_branches_are_read_from_the_clone_in_git_s_order(
    lib, tmp_path, monkeypatch
) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    sign_nothing(tmp_path)
    _git(
        tmp_path,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "root",
    )
    for name in (PR_BRANCH, STALE, "feat/7-other"):
        _git(tmp_path, "branch", name)
    monkeypatch.chdir(tmp_path)
    assert lib._local_branches() == ("feat/7-other", STALE, PR_BRANCH, "main")
    _gh(lib, monkeypatch, open_on={PR_BRANCH: [1604]})
    assert lib.read(42, {}).branch == PR_BRANCH


# ---- every verb reads it there -------------------------------------------------


def _listings(path: Path) -> list[int]:
    """The lines of `path` that list local branches (`git branch --list`)."""
    lines: list[int] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.List | ast.Tuple):
            items = list(node.elts)
        elif isinstance(node, ast.Call):
            items = list(node.args)
        else:
            continue
        words = {i.value for i in items if isinstance(i, ast.Constant)}
        if {"branch", "--list"} <= words:
            lines.append(node.lineno)
    return lines


def test_only_the_shared_reading_lists_local_branches() -> None:
    """No verb keeps a reading of its own (#1608): a copy is how the first match
    in git's order came back in seven places."""
    found = {
        str(path.relative_to(SCRIPTS)): _listings(path)
        for path in sorted([*SCRIPTS.glob("*.py"), *SCRIPTS.glob("_lib/*.py")])
    }
    assert {name: lines for name, lines in found.items() if lines}.keys() == {
        "_lib/issue_branch.py"
    }


@pytest.mark.parametrize("verb", VERBS)
def test_every_verb_that_finds_an_issue_s_branch_reads_it_there(verb: str) -> None:
    source = (SCRIPTS / f"{verb}.py").read_text(encoding="utf-8")
    assert "issue_branch.read(" in source
    for gone in ("_find_issue_branch", "_existing_branch_for_issue"):
        assert gone not in source


# ---- how each verb meets a reading that chose none -----------------------------


def _load(verb: str) -> ModuleType:
    name = f"pm_issue_branch_{verb.replace('-', '_')}_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{verb}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def verbs(lib) -> dict[str, ModuleType]:
    return {
        v: _load(v)
        for v in ("start-work", "create-draft", "review-work", "back-to-draft", "review-pr")
    }


_ISSUE = {
    "number": 42,
    "title": "[Task] do the thing",
    "labels": [{"name": "type:bug"}, {"name": "state:backlog"}],
    "assignees": [],
    "state": "OPEN",
    "body": "Feature: #1\n\n## What\nx",
    "milestone": None,
}


def _pass_gates(monkeypatch: pytest.MonkeyPatch, mod: ModuleType, verb: str) -> list[list[str]]:
    """Pass every gate ahead of the reading; any `gh` call but the reading fails
    the test. Returns the reading's calls."""
    # review-pr asks no confirmation, so it takes no `--yes`.
    monkeypatch.setattr(sys, "argv", [verb, "42", *([] if verb == "review-pr" else ["--yes"])])
    monkeypatch.setattr(mod, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(mod.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(mod.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(mod, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(mod, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        mod, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(
        mod, "check_membership", lambda *a: SimpleNamespace(allowed=True, refusal_message="")
    )
    if hasattr(mod, "_gh_get_issue"):
        monkeypatch.setattr(mod, "_gh_get_issue", lambda _n, _config: _ISSUE)
    if hasattr(mod, "_derive_branch_prefix"):
        monkeypatch.setattr(mod, "_derive_branch_prefix", lambda *a: "fix")
    if hasattr(mod, "_get_local_registered"):
        monkeypatch.setattr(mod, "_get_local_registered", lambda _config: [{"name": "r"}])
    if hasattr(mod, "axis_labels"):
        monkeypatch.setattr(mod.axis_labels, "load_substrate_map", lambda _r: None)

    def no_gh(argv: list[str], config: Any, **_kw: Any) -> Any:
        raise AssertionError(f"a verb whose branch cannot be told called gh: {argv}")

    monkeypatch.setattr(mod, "gh_run", no_gh)
    _local(mod.issue_branch, monkeypatch, STALE, PR_BRANCH)
    return _gh(mod.issue_branch, monkeypatch, open_on={})


@pytest.mark.parametrize(
    "verb", ["start-work", "create-draft", "review-work", "back-to-draft", "review-pr"]
)
def test_a_verb_refuses_naming_each_branch_when_none_has_an_open_pr(
    verbs, monkeypatch, capsys, verb: str
) -> None:
    mod = verbs[verb]
    readings = _pass_gates(monkeypatch, mod, verb)
    for name in ("_create_branch", "_set_assignee"):
        if hasattr(mod, name):
            monkeypatch.setattr(mod, name, lambda *a, **k: pytest.fail(f"{verb} acted"))
    rc = mod.main()
    err = capsys.readouterr().err
    assert rc == 2
    assert len(readings) == 1
    assert (
        "error: 2 local branches match `*/42-*`, and none has an open pull request, so which "
        "is #42's branch cannot be told:"
    ) in err
    assert f"  - {STALE}: no open pull request" in err
    assert f"  - {PR_BRANCH}: no open pull request" in err


def test_review_work_takes_the_branch_with_the_issue_s_open_pr(verbs, monkeypatch, capsys) -> None:
    """#1367: an empty branch left by a stopped builder sorted first, and
    review-work validated it instead of the branch PR #1604 was on."""
    mod = verbs["review-work"]
    _pass_gates(monkeypatch, mod, "review-work")
    in_progress = {**_ISSUE, "labels": [{"name": "type:bug"}, {"name": "state:in-progress"}]}
    monkeypatch.setattr(mod, "_gh_get_issue", lambda _n, _config: in_progress)
    monkeypatch.setattr(sys, "argv", ["review-work", "42", "--base", "main", "--dry-run"])
    readings = _gh(mod.issue_branch, monkeypatch, open_on={PR_BRANCH: [1604]})
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert f"  branch: {PR_BRANCH}\n" in out
    assert len(readings) == 1


def test_start_work_uses_the_branch_with_the_open_pr_rather_than_cut_another(
    verbs, monkeypatch, capsys
) -> None:
    mod = verbs["start-work"]
    _pass_gates(monkeypatch, mod, "start-work")
    monkeypatch.setattr(sys, "argv", ["start-work", "42", "--dry-run"])
    _gh(mod.issue_branch, monkeypatch, open_on={PR_BRANCH: [1604]})
    assert mod.main() == 0
    assert f"  branch:    {PR_BRANCH}\n" in capsys.readouterr().out


def test_start_work_refuses_a_misshapen_branch_only_when_none_matches(
    verbs, monkeypatch, capsys
) -> None:
    mod = verbs["start-work"]
    _pass_gates(monkeypatch, mod, "start-work")
    monkeypatch.setattr(sys, "argv", ["start-work", "42", "--dry-run"])
    _local(mod.issue_branch, monkeypatch, "fix/42")
    assert mod.main() == 2
    assert "error: branch 'fix/42' exists for #42 but doesn't match" in capsys.readouterr().err
    _local(mod.issue_branch, monkeypatch, "fix/42", PR_BRANCH)
    assert mod.main() == 0
    assert f"  branch:    {PR_BRANCH}\n" in capsys.readouterr().out
