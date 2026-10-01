"""Tests for the shared gh-backed PR-data fetchers (_lib/closing_issue_fetchers.py).

`done-work`'s gate and `review-pr`'s invoke loop share these fetchers so the
set the gate checks == the set `review-pr` invokes (DEC-032 D1/D5). The resolver
branches on the exact `_Unresolvable` sentinel they return to decide
fail-closed vs. baseline-only, so the fail-closed contract is load-bearing:

  * `pr_closing_issue_numbers` — a present-but-null `closingIssuesReferences`
    is UNKNOWN ground truth (fail closed), not "closes nothing" (G2).
  * `pr_changed_files` — sourced from every page of GitHub's pull-request
    files API (the complete path set: not the page-capped `gh pr view --json
    files`, G1, nor `gh pr diff`, which GitHub refuses past 300 files, #1188);
    a gh failure or an empty result is UNKNOWN ground truth (fail closed, G2),
    and a listing that reaches GitHub's 3000-file ceiling is refused as too
    many files.

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


# ---- pr_changed_files (paginated files API, G1/G2, #1188) ---------------


def _files_api_stdout(*pages) -> str:
    """What `gh api --paginate … --jq` prints for these pages of file entries.

    Each page is a list of `(filename, previous_filename)` pairs; gh applies
    the jq filter to every page and prints one JSON array per file, so the
    pages arrive as one continuous run of lines.
    """
    return "".join(
        json.dumps([filename, previous]) + "\n"
        for page in pages
        for filename, previous in page
    )


def _pages(paths, size=100):
    """Split `paths` into pages of unrenamed file entries, `size` per page."""
    entries = [(path, None) for path in paths]
    return [entries[i:i + size] for i in range(0, len(entries), size)]


def test_changed_files_reads_every_page_of_the_files_api(cf) -> None:
    """The paginated files API is read, at the largest page size — not the
    page-capped `gh pr view --json files` (G1), nor `gh pr diff`, which
    GitHub refuses past 300 files (#1188)."""
    seen = {}

    def gh_run(argv, config, **kwargs):
        seen["argv"] = argv
        return _proc(stdout=_files_api_stdout([("src/app.py", None)]))

    cf.pr_changed_files(7, CONFIG, gh_run=gh_run)
    assert seen["argv"] == [
        "gh", "api", "--paginate",
        "repos/{owner}/{repo}/pulls/7/files?per_page=100",
        "--jq", ".[] | [.filename, .previous_filename]",
    ]


def test_changed_files_returns_all_paths(cf) -> None:
    stdout = _files_api_stdout(
        [("src/app.py", None), ("README.md", None), ("docs/conf.py", None)]
    )
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: _proc(stdout=stdout))
    assert out == ["src/app.py", "README.md", "docs/conf.py"]


def test_changed_files_past_300_files_reads_every_page(cf) -> None:
    """A 350-file PR — past `gh pr diff`'s 300-file refusal — comes back
    whole across four pages, the code file on the last page included (#1188)."""
    paths = [f"docs/page_{i}.md" for i in range(349)] + ["src/late.py"]
    pages = _pages(paths)
    assert len(pages) == 4
    proc = _proc(stdout=_files_api_stdout(*pages))
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert out == paths


def test_changed_files_rename_contributes_both_paths(cf) -> None:
    """A rename lists its new path and its old one: moving a file out of code
    removes code, as deleting it would."""
    stdout = _files_api_stdout([("docs/notes.md", "src/notes.py")])
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: _proc(stdout=stdout))
    assert out == ["docs/notes.md", "src/notes.py"]


def test_changed_files_empty_fails_closed(cf) -> None:
    """No files back → UNKNOWN ground truth, fail closed (G2)."""
    proc = _proc(stdout="\n  \n")
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert _is_unresolvable(cf, out)
    assert not isinstance(out, cf._TooManyChangedFiles)


def test_changed_files_gh_failure_fails_closed(cf) -> None:
    proc = _proc(returncode=1, stderr="HTTP 502: Bad Gateway")
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert _is_unresolvable(cf, out)
    assert not isinstance(out, cf._TooManyChangedFiles)
    assert "HTTP 502" in out.reason


def test_changed_files_line_that_is_not_an_entry_fails_closed(cf) -> None:
    """Output that is not one file entry per line is not read as a file list."""
    stdout = _files_api_stdout([("src/app.py", None)]) + "src/raw-path.py\n"
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: _proc(stdout=stdout))
    assert _is_unresolvable(cf, out)


def test_changed_files_at_the_listing_ceiling_is_too_many(cf) -> None:
    """GitHub lists at most 3000 files; a listing that reaches it may be cut
    short, so it is refused — as too many files, not as a gh failure."""
    paths = [f"src/mod_{i}.py" for i in range(3000)]
    proc = _proc(stdout=_files_api_stdout(*_pages(paths)))
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert isinstance(out, cf._TooManyChangedFiles)
    assert _is_unresolvable(cf, out)
    assert "3000" in out.reason


def test_changed_files_below_the_listing_ceiling_is_complete(cf) -> None:
    """One file short of the ceiling, and counted in files, not paths: the
    renames add paths but no files toward it."""
    entries = [(f"src/mod_{i}.py", f"src/old_{i}.py") for i in range(2999)]
    proc = _proc(stdout=_files_api_stdout(entries))
    out = cf.pr_changed_files(7, CONFIG, gh_run=lambda *a, **k: proc)
    assert isinstance(out, list)
    assert len(out) == 2 * 2999
