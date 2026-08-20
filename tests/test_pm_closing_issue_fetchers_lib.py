"""Tests for the shared gh-backed PR-data fetchers (_lib/closing_issue_fetchers.py).

`done-work`'s gate and `review-pr`'s invoke loop share these fetchers so the
set the gate checks == the set `review-pr` invokes (DEC-032 D1/D5). The resolver
branches on the exact `_Unresolvable` sentinel they return to decide
fail-closed vs. baseline-only, so the fail-closed contract is load-bearing:

  * `pr_closing_issue_numbers` — a present-but-null `closingIssuesReferences`
    is UNKNOWN ground truth (fail closed), not "closes nothing" (G2).
  * `pr_changed_files` — sourced from `gh pr diff --name-only` (the complete
    path set, not the page-capped `gh pr view --json files`, G1); a gh failure
    or an empty result is UNKNOWN ground truth (fail closed, G2).

`gh_run` / `gh_get_issue` are injected, so these are pure-logic unit tests with
no live repo / GitHub.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
FETCHERS_PATH = SCRIPTS_DIR / "_lib" / "closing_issue_fetchers.py"


def _load(module_name: str, path: Path):
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and str(SCRIPTS_DIR) in sys.path:
            sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def cf():
    return _load("pm_closing_issue_fetchers_under_test", FETCHERS_PATH)


CONFIG = {"repo": "owner/name"}


def _proc(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _is_unresolvable(cf, value) -> bool:
    return isinstance(value, cf._Unresolvable)


# ---- pr_closing_issue_numbers -----------------------------------------


def test_closing_numbers_empty_array_is_no_closing(cf) -> None:
    """A present, empty array is the legitimate "closes nothing" branch."""
    proc = _proc(stdout=json.dumps({"closingIssuesReferences": []}))
    out = cf.pr_closing_issue_numbers(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert out == []


def test_closing_numbers_returns_numbers(cf) -> None:
    proc = _proc(
        stdout=json.dumps(
            {"closingIssuesReferences": [{"number": 42}, {"number": 43}]}
        )
    )
    out = cf.pr_closing_issue_numbers(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert out == [42, 43]


def test_closing_numbers_null_field_fails_closed(cf) -> None:
    """`{"closingIssuesReferences": null}` is UNKNOWN, not empty (G2)."""
    proc = _proc(stdout=json.dumps({"closingIssuesReferences": None}))
    out = cf.pr_closing_issue_numbers(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert _is_unresolvable(cf, out)


def test_closing_numbers_gh_failure_fails_closed(cf) -> None:
    proc = _proc(returncode=1, stderr="boom")
    out = cf.pr_closing_issue_numbers(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert _is_unresolvable(cf, out)


def test_closing_numbers_malformed_json_fails_closed(cf) -> None:
    proc = _proc(stdout="not json")
    out = cf.pr_closing_issue_numbers(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert _is_unresolvable(cf, out)


def test_closing_numbers_missing_field_fails_closed(cf) -> None:
    proc = _proc(stdout=json.dumps({"something": "else"}))
    out = cf.pr_closing_issue_numbers(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert _is_unresolvable(cf, out)


# ---- pr_changed_files (gh pr diff --name-only, G1/G2) ------------------


def test_changed_files_uses_gh_pr_diff_name_only(cf) -> None:
    """The complete-source command is issued, not the page-capped view (G1)."""
    seen = {}

    def gh_run(argv, config, **kwargs):
        seen["argv"] = argv
        return _proc(stdout="src/app.py\n")

    cf.pr_changed_files(7, CONFIG, gh_run=gh_run)
    assert seen["argv"] == ["gh", "pr", "diff", "7", "--name-only"]


def test_changed_files_returns_all_paths(cf) -> None:
    proc = _proc(stdout="src/app.py\nREADME.md\ndocs/conf.py\n")
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert out == ["src/app.py", "README.md", "docs/conf.py"]


def test_changed_files_large_diff_not_capped(cf) -> None:
    """A >100-file diff returns every path — no page cap (G1)."""
    paths = [f"src/mod_{i}.py" for i in range(250)]
    proc = _proc(stdout="\n".join(paths) + "\n")
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert out == paths
    assert len(out) == 250


def test_changed_files_empty_fails_closed(cf) -> None:
    """No paths back → UNKNOWN ground truth, fail closed (G2)."""
    proc = _proc(stdout="\n  \n")
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert _is_unresolvable(cf, out)


def test_changed_files_gh_failure_fails_closed(cf) -> None:
    proc = _proc(returncode=1, stderr="boom")
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert _is_unresolvable(cf, out)
