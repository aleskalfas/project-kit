"""Tests for the shared per-PR required-reviewer resolver (_lib/required_reviewers.py).

This is the single resolution `done-work`'s gate-checker and `review-pr` both
call so the set the gate checks == the set `review-pr` invokes (DEC-032 D1/D4,
no divergence). The collector (`reviewers_for_issues`) is exercised separately
in test_pm_review_contributions_lib.py; here we cover the layer this module
adds — the baseline∪contributed union, the closing-issue classification fetch,
and the fail-closed distinction (DEC-032 D5) between:

  * baseline-only branches (PR closes nothing / no workstream axis / no match),
  * a not-ok contribution collection (ERROR_COLLECTION fail-closed),
  * an unresolvable closing-issue lookup (ERROR_CLOSING_ISSUES fail-closed),

The `gh`-backed closing-issue/label fetchers and the collector are injected,
so these are pure-logic unit tests with no live repo / GitHub.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import MappingProxyType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
LIB_PATH = SCRIPTS_DIR / "_lib" / "required_reviewers.py"
RC_PATH = SCRIPTS_DIR / "_lib" / "review_contributions.py"


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
def rr():
    return _load("pm_required_reviewers_under_test", LIB_PATH)


@pytest.fixture(scope="module")
def rc():
    return _load("pm_rc_for_required_reviewers", RC_PATH)


REPO = Path("/tmp/x")  # collect_contributions is injected; never read.


def _design_collection(rc, *, deployed=True):
    err = None if deployed else rc.ContributionError(
        rc.ERROR_UNDEPLOYED_AGENT, "ux-ui-design", "design-reviewer not deployed",
    )
    rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="design-reviewer",
        deployed=deployed,
        resolution_error=err,
    )
    return rc.ContributionCollection(
        rules=(rule,),
        errors=() if deployed else (err,),
        capabilities_walked=("project-management", "ux-ui-design"),
    )


def _resolve(rr, *, baseline, collection, closing, labels=None, refs_unresolvable=None):
    """Drive resolve_required_local_reviewers with injected fetchers.

    `closing` is the issue-number list the PR closes (or, if
    `refs_unresolvable` is set, that `_Unresolvable` is returned instead).
    `labels` maps issue number → label-name list; an issue absent from it
    whose number is in a `None`-marked set resolves labels to None.
    """
    labels = labels or {}

    def closing_fn(pr):
        if refs_unresolvable is not None:
            return rr._Unresolvable(refs_unresolvable)
        return list(closing)

    def labels_fn(issue_number):
        val = labels.get(issue_number, [])
        if val is None:
            return None
        return [{"name": n} for n in val]

    return rr.resolve_required_local_reviewers(
        99,
        baseline_local=baseline,
        repo_root=REPO,
        closing_issue_numbers=closing_fn,
        issue_labels=labels_fn,
        collect_contributions=lambda repo_root: collection,
    )


# ---- baseline-only (no contributions) ---------------------------------


def test_no_contributions_single_baseline(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=()),
        closing=[],
    )
    assert res.ok
    assert res.required_local == ("reviewer",)
    assert res.contributed_rules == ()
    assert res.contributed_by == {}


def test_no_closing_issue_baseline_only(rr, rc) -> None:
    """A design contribution present but PR closes nothing → baseline only."""
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[],
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_no_workstream_axis_baseline_only(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[42],
        labels={42: ["priority:High", "type:feature"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_non_matching_workstream_baseline_only(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[42],
        labels={42: ["workstream:backend"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


# ---- compose (baseline ∪ contributed) ---------------------------------


def test_design_pr_adds_contributed_reviewer(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[42],
        labels={42: ["workstream:design"]},
    )
    assert res.ok
    # Baseline-first order, contributed appended.
    assert res.required_local == ("reviewer", "design-reviewer")
    assert res.contributed_by == {"design-reviewer": "ux-ui-design"}
    assert [r.reviewer for r in res.contributed_rules] == ["design-reviewer"]


def test_multi_issue_union(rr, rc) -> None:
    design = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="design-reviewer",
    )
    backend = rc.ContributionRule(
        capability="backend-discipline",
        predicate=MappingProxyType({"workstream": ("backend",)}),
        reviewer="backend-reviewer",
    )
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=(design, backend)),
        closing=[42, 43],
        labels={42: ["workstream:design"], 43: ["workstream:backend"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer", "design-reviewer", "backend-reviewer")


def test_dedup_reviewer_named_by_both(rr, rc) -> None:
    """A contributed reviewer named the same as the baseline is required once."""
    rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="reviewer",  # same name as baseline.
    )
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=(rule,)),
        closing=[42],
        labels={42: ["workstream:design"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


# ---- fail-closed (DEC-032 D5) -----------------------------------------


def test_fail_closed_not_ok_collection(rr, rc) -> None:
    err = rc.ContributionError(rc.ERROR_MALFORMED, "ux-ui-design", "bad decl")
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=(), errors=(err,)),
        closing=[42],
        labels={42: ["workstream:design"]},
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_COLLECTION
    assert res.error.collection is not None
    assert res.required_local == ()


def test_fail_closed_undeployed_contributed_reviewer(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc, deployed=False),
        closing=[42],
        labels={42: ["workstream:design"]},
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_COLLECTION


def test_fail_closed_closing_refs_unresolvable(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[],
        refs_unresolvable="gh failed",
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_CLOSING_ISSUES
    assert "gh failed" in res.error.message


def test_fail_closed_issue_labels_none(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[42, 43],
        labels={42: ["workstream:design"], 43: None},  # 43's labels unreadable.
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_CLOSING_ISSUES
    assert "#43" in res.error.message


def test_fail_closed_multi_workstream_label(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[42],
        labels={42: ["workstream:design", "workstream:backend"]},
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_CLOSING_ISSUES
    assert "multiple workstream" in res.error.message


def test_collection_gated_before_closing_issues(rr, rc) -> None:
    """A not-ok collection refuses even if closing-issue resolution would also
    fail — collection is gated first, deterministically (ERROR_COLLECTION)."""
    err = rc.ContributionError(rc.ERROR_MALFORMED, "ux-ui-design", "bad decl")
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=(), errors=(err,)),
        closing=[],
        refs_unresolvable="gh failed",
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_COLLECTION
