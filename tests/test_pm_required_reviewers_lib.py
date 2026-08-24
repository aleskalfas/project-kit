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


def _resolve(
    rr, *, baseline, collection, closing, labels=None, refs_unresolvable=None,
    changed=None, files_unresolvable=None,
):
    """Drive resolve_required_local_reviewers with injected fetchers.

    `closing` is the issue-number list the PR closes (or, if
    `refs_unresolvable` is set, that `_Unresolvable` is returned instead).
    `labels` maps issue number → label-name list; an issue absent from it
    whose number is in a `None`-marked set resolves labels to None.

    `changed` is the PR's changed-file path list the diff-property floor sees
    (default empty → touches nothing); `files_unresolvable`, when set, makes
    the changed-files fetcher return that `_Unresolvable` instead. The resolver
    only calls the changed-files fetcher when the collection carries a floor
    rule, so floor-free scenarios never exercise it.
    """
    labels = labels or {}
    changed = changed or []

    def closing_fn(pr):
        if refs_unresolvable is not None:
            return rr._Unresolvable(refs_unresolvable)
        return list(closing)

    def labels_fn(issue_number):
        val = labels.get(issue_number, [])
        if val is None:
            return None
        return [{"name": n} for n in val]

    def changed_fn(pr):
        if files_unresolvable is not None:
            return rr._Unresolvable(files_unresolvable)
        return list(changed)

    return rr.resolve_required_local_reviewers(
        99,
        baseline_local=baseline,
        repo_root=REPO,
        closing_issue_numbers=closing_fn,
        issue_labels=labels_fn,
        changed_files=changed_fn,
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


# ---- type-axis resolution (DEC-032 amendment) -------------------------


def _type_collection(rc, *, values=("feature",), reviewer="code-reviewer"):
    rule = rc.ContributionRule(
        capability="software-engineering",
        predicate=MappingProxyType({"type": tuple(values)}),
        reviewer=reviewer,
    )
    return rc.ContributionCollection(rules=(rule,))


def test_type_axis_match_adds_reviewer(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_type_collection(rc, values=("feature",)),
        closing=[42],
        labels={42: ["type:feature", "priority:High"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer")
    assert res.contributed_by == {"code-reviewer": "software-engineering"}


def test_type_axis_non_matching_baseline_only(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_type_collection(rc, values=("bug",)),
        closing=[42],
        labels={42: ["type:feature"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_type_axis_no_type_label_baseline_only(rr, rc) -> None:
    """An entity carrying no `type` axis matches nothing → baseline only."""
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_type_collection(rc, values=("feature",)),
        closing=[42],
        labels={42: ["workstream:backend"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_multi_type_label_fails_closed(rr, rc) -> None:
    """`type` is mutually_exclusive; two values on one issue fail closed."""
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_type_collection(rc, values=("feature",)),
        closing=[42],
        labels={42: ["type:feature", "type:bug"]},
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_CLOSING_ISSUES
    assert "multiple type" in res.error.message


def test_type_and_workstream_both_read(rr, rc) -> None:
    """Both axes are read into the classification a rule can AND-compose on."""
    rule = rc.ContributionRule(
        capability="cap",
        predicate=MappingProxyType(
            {"type": ("feature",), "workstream": ("design",)}
        ),
        reviewer="specialist",
    )
    matched = _resolve(
        rr, baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=(rule,)),
        closing=[42],
        labels={42: ["type:feature", "workstream:design"]},
    )
    assert matched.required_local == ("reviewer", "specialist")
    # Missing one axis → the AND-composed predicate no longer holds.
    only_type = _resolve(
        rr, baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=(rule,)),
        closing=[42],
        labels={42: ["type:feature"]},
    )
    assert only_type.required_local == ("reviewer",)


# ---- wildcard / axis-present predicate (DEC-032 amendment) -------------


def _wildcard_type_collection(rc, *, reviewer="code-reviewer"):
    rule = rc.ContributionRule(
        capability="software-engineering",
        predicate={"type": rc.MATCH_ANY},
        reviewer=reviewer,
    )
    return rc.ContributionCollection(rules=(rule,))


def test_wildcard_matches_every_type_value(rr, rc) -> None:
    for value in ("feature", "bug", "docs", "refactor"):
        res = _resolve(
            rr, baseline=["reviewer"],
            collection=_wildcard_type_collection(rc),
            closing=[42],
            labels={42: [f"type:{value}"]},
        )
        assert res.ok
        assert res.required_local == ("reviewer", "code-reviewer"), value


def test_wildcard_requires_axis_present(rr, rc) -> None:
    """A wildcard is axis-present: an entity with no `type` axis matches nothing."""
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_wildcard_type_collection(rc),
        closing=[42],
        labels={42: ["workstream:design"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


# ---- diff-property floor (DEC-032 amendment) --------------------------


def _floor_collection(rc, *, reviewer="code-reviewer"):
    rule = rc.ContributionRule(
        capability="software-engineering",
        predicate={},  # floor-only rule — no classification predicate.
        reviewer=reviewer,
        floor=rc.FLOOR_TOUCHES_CODE,
    )
    return rc.ContributionCollection(rules=(rule,))


def test_floor_fires_on_code_diff_for_docs_issue(rr, rc) -> None:
    """A code-touching diff pulls in the floor reviewer even for `type:docs`."""
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_floor_collection(rc),
        closing=[42],
        labels={42: ["type:docs"]},
        changed=["src/app.py", "README.md"],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer")


def test_floor_fires_on_code_file_under_docs_dir(rr, rc) -> None:
    """A code file checked into a docs tree still fires the floor (R1).

    Before the code-suffix-dominant fix, `docs/conf.py` read as documentation,
    so a PR touching only code under `docs/` escaped the code-review floor.
    """
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_floor_collection(rc),
        closing=[42],
        labels={42: ["type:docs"]},
        changed=["docs/conf.py", "docs/index.md"],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer")


def test_floor_fires_on_code_diff_for_unclassified_pr(rr, rc) -> None:
    """No closing issue at all: the floor still fires on a code diff."""
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_floor_collection(rc),
        closing=[],
        changed=["scripts/run.sh"],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer")


def test_floor_silent_on_docs_only_diff(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_floor_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["README.md", "docs/guide.rst", "docs/img/diagram.png"],
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_floor_only_collection_does_not_fetch_diff_when_no_floor(rr, rc) -> None:
    """A floor-free collection never calls the changed-files fetcher.

    `files_unresolvable` would fail closed IF the fetcher were called; the
    resolver must not call it when no rule carries a floor.
    """
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_design_collection(rc),  # classification-only rule.
        closing=[42],
        labels={42: ["workstream:design"]},
        files_unresolvable="gh boom (must not be reached)",
    )
    assert res.ok
    assert res.required_local == ("reviewer", "design-reviewer")


def test_floor_fails_closed_when_diff_unresolvable(rr, rc) -> None:
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=_floor_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        files_unresolvable="gh files failed",
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_CHANGED_FILES
    assert "gh files failed" in res.error.message


def test_floor_and_classification_dedup_same_reviewer(rr, rc) -> None:
    """A reviewer required by both a classification rule and a floor is once."""
    class_rule = rc.ContributionRule(
        capability="software-engineering",
        predicate=MappingProxyType({"type": ("feature",)}),
        reviewer="code-reviewer",
    )
    floor_rule = rc.ContributionRule(
        capability="software-engineering",
        predicate={},
        reviewer="code-reviewer",
        floor=rc.FLOOR_TOUCHES_CODE,
    )
    res = _resolve(
        rr, baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=(class_rule, floor_rule)),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer")


# ---- diff_touches_code predicate (the design point) -------------------


@pytest.mark.parametrize(
    "path,is_code",
    [
        ("src/app.py", True),
        ("config/settings.yaml", True),
        ("data.json", True),
        ("scripts/run.sh", True),
        ("bin/tool", True),  # extensionless executable — fail-closed default.
        ("README.md", False),
        ("docs/guide.rst", False),
        ("CHANGELOG.mdx", False),
        ("docs/img/diagram.png", False),  # non-code file UNDER a docs/ dir.
        ("app/docs.py", True),  # a file merely NAMED docs is code.
        # --- code-suffix dominates the docs/ location (R1 gate-escapes) ---
        ("docs/conf.py", True),
        ("docs/generate.py", True),
        ("docs/deploy.sh", True),
        ("src/docs/handler.py", True),
        ("docs/config.yaml", True),  # config under docs/ is still code.
        # --- .txt is code-adjacent, not documentation (G3) ---
        ("requirements.txt", True),
        ("CMakeLists.txt", True),
        ("notes.txt", True),  # any .txt is code (fail-closed default).
        # --- docs/ segment matched case-insensitively (G4) ---
        ("Docs/img/diagram.png", False),
        ("Docs/conf.py", True),  # code suffix still wins under Docs/.
        # --- unknown suffix is code (fail-closed default) ---
        ("mystery.xyz", True),
        # --- extensionless / unknown-suffix file UNDER docs/ is code, not
        #     documentation: the docs/ location alone must not demote it, or a
        #     script checked in extensionless slips past the floor (G3). ---
        ("docs/tools/helper", True),
        ("docs/scripts/run", True),
        ("docs/data.bin", True),  # unknown suffix under docs/ is still code.
    ],
)
def test_diff_touches_code_per_file(rr, path, is_code) -> None:
    assert rr.diff_touches_code([path]) is is_code


def test_diff_touches_code_empty_is_false(rr) -> None:
    assert rr.diff_touches_code([]) is False


def test_diff_touches_code_mixed_is_true(rr) -> None:
    assert rr.diff_touches_code(["README.md", "src/app.py"]) is True
