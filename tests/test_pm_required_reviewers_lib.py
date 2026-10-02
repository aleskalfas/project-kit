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

and the adopter's per-contribution opt-out (#148): an opted-out contribution
leaves the set while the rest of the capability's contribution stays, and an
opt-out naming no installed contribution fails closed (ERROR_OPT_OUT) — and
the adopter's not-code list (#1178): a changed path it matches satisfies no
floor, and a malformed list fails closed (ERROR_NOT_CODE).

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
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
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

# The opt-out reader the consumers call (`read_opt_outs(config)`), used by
# `_resolve` to turn a configured list into the resolver's `opt_outs`.
_OO = _load(
    "pm_review_opt_outs_for_required_reviewers",
    SCRIPTS_DIR / "_lib" / "review_opt_outs.py",
)


def _design_collection(rc, *, deployed=True):
    err = (
        None
        if deployed
        else rc.ContributionError(
            rc.ERROR_UNDEPLOYED_AGENT,
            "ux-ui-design",
            "design-reviewer not deployed",
        )
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


# `_resolve`'s marker for "the config does not set `review.floors.not_code`".
_UNSET = object()


def _resolve(
    rr,
    *,
    baseline,
    collection,
    closing,
    labels=None,
    refs_unresolvable=None,
    changed=None,
    files_unresolvable=None,
    opt_outs=None,
    not_code=_UNSET,
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

    `opt_outs` is the configured `review.agents.contributed_opt_out` list
    (raw, as it appears in `project/config.yaml`); `None` is no opt-outs.

    `not_code` is the configured `review.floors.not_code` value (raw); left
    unset, the config carries no `floors` block, as most adopters' do.
    """
    labels = labels or {}
    changed = changed or []
    config = {"review": {"agents": {"contributed_opt_out": opt_outs}}}
    if not_code is not _UNSET:
        config["review"]["floors"] = {"not_code": not_code}

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
        opt_outs=_OO.read_opt_outs(config),
        not_code=rr.read_not_code(config),
        collect_contributions=lambda repo_root: collection,
    )


# ---- baseline-only (no contributions) ---------------------------------


def test_no_contributions_single_baseline(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[],
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_no_workstream_axis_baseline_only(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[42],
        labels={42: ["priority:High", "type:feature"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_non_matching_workstream_baseline_only(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[42],
        labels={42: ["workstream:backend"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


# ---- compose (baseline ∪ contributed) ---------------------------------


def test_design_pr_adds_contributed_reviewer(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
        collection=_design_collection(rc, deployed=False),
        closing=[42],
        labels={42: ["workstream:design"]},
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_COLLECTION


def test_fail_closed_closing_refs_unresolvable(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[],
        refs_unresolvable="gh failed",
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_CLOSING_ISSUES
    assert "gh failed" in res.error.message


def test_fail_closed_issue_labels_none(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_design_collection(rc),
        closing=[42, 43],
        labels={42: ["workstream:design"], 43: None},  # 43's labels unreadable.
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_CLOSING_ISSUES
    assert "#43" in res.error.message


def test_fail_closed_multi_workstream_label(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
        collection=_type_collection(rc, values=("feature",)),
        closing=[42],
        labels={42: ["type:feature", "priority:High"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer")
    assert res.contributed_by == {"code-reviewer": "software-engineering"}


def test_type_axis_non_matching_baseline_only(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_type_collection(rc, values=("bug",)),
        closing=[42],
        labels={42: ["type:feature"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_type_axis_no_type_label_baseline_only(rr, rc) -> None:
    """An entity carrying no `type` axis matches nothing → baseline only."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_type_collection(rc, values=("feature",)),
        closing=[42],
        labels={42: ["workstream:backend"]},
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_multi_type_label_fails_closed(rr, rc) -> None:
    """`type` is mutually_exclusive; two values on one issue fail closed."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
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
        predicate=MappingProxyType({"type": ("feature",), "workstream": ("design",)}),
        reviewer="specialist",
    )
    matched = _resolve(
        rr,
        baseline=["reviewer"],
        collection=rc.ContributionCollection(rules=(rule,)),
        closing=[42],
        labels={42: ["type:feature", "workstream:design"]},
    )
    assert matched.required_local == ("reviewer", "specialist")
    # Missing one axis → the AND-composed predicate no longer holds.
    only_type = _resolve(
        rr,
        baseline=["reviewer"],
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
            rr,
            baseline=["reviewer"],
            collection=_wildcard_type_collection(rc),
            closing=[42],
            labels={42: [f"type:{value}"]},
        )
        assert res.ok
        assert res.required_local == ("reviewer", "code-reviewer"), value


def test_wildcard_requires_axis_present(rr, rc) -> None:
    """A wildcard is axis-present: an entity with no `type` axis matches nothing."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
        collection=_floor_collection(rc),
        closing=[],
        changed=["scripts/run.sh"],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer")


def test_floor_silent_on_docs_only_diff(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
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
        rr,
        baseline=["reviewer"],
        collection=_design_collection(rc),  # classification-only rule.
        closing=[42],
        labels={42: ["workstream:design"]},
        files_unresolvable="gh boom (must not be reached)",
    )
    assert res.ok
    assert res.required_local == ("reviewer", "design-reviewer")


def test_floor_fails_closed_when_diff_unresolvable(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_floor_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        files_unresolvable="gh files failed",
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_CHANGED_FILES
    assert "gh files failed" in res.error.message


def test_floor_fails_closed_as_too_many_when_listing_is_cut_short(rr, rc) -> None:
    """A PR past GitHub's file-listing ceiling fails closed under its own kind,
    so a consumer can say "split the PR" rather than "retry" (#1188)."""
    res = rr.resolve_required_local_reviewers(
        99,
        baseline_local=["reviewer"],
        repo_root=REPO,
        closing_issue_numbers=lambda pr: [42],
        issue_labels=lambda n: [{"name": "type:feature"}],
        changed_files=lambda pr: rr._TooManyChangedFiles("PR #99 changes 3000+"),
        collect_contributions=lambda repo_root: _floor_collection(rc),
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_TOO_MANY_CHANGED_FILES
    assert "3000+" in res.error.message


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
        rr,
        baseline=["reviewer"],
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


# ---- per-contribution opt-out (#148) ----------------------------------
#
# The adopter withdraws one `(capability, reviewer)` contribution in
# `review.agents.contributed_opt_out`. The resolver drops it before matching,
# so it is neither invoked by review-pr nor required by done-work, while the
# rest of the capability's contribution still applies.

_SE = "software-engineering"
_DOCS_OPT_OUT = {
    "capability": _SE,
    "reviewer": "docs-reviewer",
    "reason": "Docs are reviewed by the tech-writing team.",
}


def _se_collection(rc, *, docs_deployed=True):
    """The software-engineering panel as it ships: code, security and docs
    reviewers on the `touches-code` floor, docs also on `type: *`."""

    def rule(reviewer, *, floor=None, match=None, deployed=True):
        error = (
            None
            if deployed
            else rc.ContributionError(
                rc.ERROR_UNDEPLOYED_AGENT,
                _SE,
                f"`{reviewer}` is not deployed",
            )
        )
        return rc.ContributionRule(
            capability=_SE,
            predicate=MappingProxyType(match or {}),
            reviewer=reviewer,
            floor=floor,
            deployed=deployed,
            resolution_error=error,
        )

    rules = (
        rule("code-reviewer", floor=rc.FLOOR_TOUCHES_CODE),
        rule("security-reviewer", floor=rc.FLOOR_TOUCHES_CODE),
        rule("docs-reviewer", floor=rc.FLOOR_TOUCHES_CODE, deployed=docs_deployed),
        rule("docs-reviewer", match={"type": rc.MATCH_ANY}, deployed=docs_deployed),
    )
    return rc.ContributionCollection(
        rules=rules,
        errors=tuple(r.resolution_error for r in rules if r.resolution_error),
        capabilities_walked=("project-management", _SE),
    )


def test_without_opt_out_the_panel_requires_docs_reviewer(rr, rc) -> None:
    """The control: the shipped panel on a code PR requires all three."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
    )
    assert res.ok
    # Classification-matched first (docs via `type: *`), then the floor rules.
    assert res.required_local == (
        "reviewer",
        "docs-reviewer",
        "code-reviewer",
        "security-reviewer",
    )
    assert res.opted_out == ()


def test_opted_out_reviewer_is_not_required(rr, rc) -> None:
    """docs-reviewer opted out: neither its floor rule nor its `type: *` rule
    applies, and the rest of the contribution still does."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
        opt_outs=[_DOCS_OPT_OUT],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer", "security-reviewer")
    assert "docs-reviewer" not in res.contributed_by
    assert [(o.capability, o.reviewer, o.reason) for o in res.opted_out] == [
        (_SE, "docs-reviewer", "Docs are reviewed by the tech-writing team."),
    ]


def test_opt_out_on_a_docs_only_classified_pr_leaves_baseline(rr, rc) -> None:
    """The match rule was the only one that fired; withdrawn, baseline remains."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:docs"]},
        changed=["README.md"],
        opt_outs=[_DOCS_OPT_OUT],
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_opt_out_never_withdraws_the_baseline(rr, rc) -> None:
    """A reviewer the adopter registers in `local_registered` stays required
    even when the same name's contribution is opted out."""
    res = _resolve(
        rr,
        baseline=["reviewer", "docs-reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:docs"]},
        changed=["README.md"],
        opt_outs=[_DOCS_OPT_OUT],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "docs-reviewer")


def test_opt_out_keeps_another_capabilitys_contribution_of_the_reviewer(rr, rc) -> None:
    """The same reviewer contributed by a second capability is still required
    — and attributed to that capability, not the opted-out one."""
    collection = _se_collection(rc)
    other = rc.ContributionRule(
        capability="tech-writing",
        predicate=MappingProxyType({"type": ("docs",)}),
        reviewer="docs-reviewer",
    )
    collection = rc.ContributionCollection(
        rules=(*collection.rules, other),
        capabilities_walked=(*collection.capabilities_walked, "tech-writing"),
    )
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=collection,
        closing=[42],
        labels={42: ["type:docs"]},
        changed=["README.md"],
        opt_outs=[_DOCS_OPT_OUT],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "docs-reviewer")
    assert res.contributed_by == {"docs-reviewer": "tech-writing"}


def test_opted_out_undeployed_reviewer_does_not_fail_closed(rr, rc) -> None:
    """An undeployed contributed agent fails the gate closed (DEC-032 D5) —
    unless its contribution is opted out, since it is then never required."""
    control = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc, docs_deployed=False),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
    )
    assert not control.ok and control.error.kind == rr.ERROR_COLLECTION

    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc, docs_deployed=False),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
        opt_outs=[_DOCS_OPT_OUT],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "code-reviewer", "security-reviewer")


def test_opt_out_naming_an_unknown_capability_is_a_validation_error(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
        opt_outs=[{**_DOCS_OPT_OUT, "capability": "ux-ui-design"}],
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_OPT_OUT
    assert res.required_local == ()
    (detail,) = res.error.details
    assert "contributed_opt_out[0]" in detail
    assert "`ux-ui-design`" in detail


def test_opt_out_naming_an_unknown_reviewer_is_a_validation_error(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
        opt_outs=[{**_DOCS_OPT_OUT, "reviewer": "design-reviewer"}],
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_OPT_OUT
    (detail,) = res.error.details
    assert "no reviewer `design-reviewer`" in detail


def test_malformed_opt_out_is_a_validation_error(rr, rc) -> None:
    """A missing reason voids the list: nothing is withdrawn, the resolver
    refuses rather than guess."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
        opt_outs=[{"capability": _SE, "reviewer": "docs-reviewer"}],
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_OPT_OUT
    assert any(".reason" in d for d in res.error.details)


def test_broken_declaration_is_reported_before_the_opt_out(rr, rc) -> None:
    """A malformed declaration leaves its capability contributing nothing, which
    would make an opt-out naming it look unknown — the collection error is the
    root cause, so it is the one reported."""
    err = rc.ContributionError(rc.ERROR_MALFORMED, _SE, "bad decl")
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=rc.ContributionCollection(
            rules=(),
            errors=(err,),
            capabilities_walked=(_SE,),
        ),
        closing=[42],
        labels={42: ["type:feature"]},
        opt_outs=[_DOCS_OPT_OUT],
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_COLLECTION


# ---- the adopter's not-code list (#1178) -------------------------------
#
# `review.floors.not_code` names paths that never count as code; a changed
# path it matches satisfies no floor. Shipped default, when the key is absent:
# `.changes/**` — the changeset every surface-changing PR carries, a YAML file
# the suffix test would otherwise read as code.

_CHANGESET = ".changes/unreleased/project-management-none-20261001-wording.yaml"
_PANEL = ("reviewer", "docs-reviewer", "code-reviewer", "security-reviewer")


@pytest.mark.parametrize("issue_type", ["type:docs", "type:feature"])
def test_changeset_is_the_only_non_markdown_change_no_panel(
    rr,
    rc,
    issue_type,
) -> None:
    """A wording PR carrying its changeset: baseline + the classification-matched
    docs-reviewer only — the floor reviewers stay out, whatever the type."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: [issue_type]},
        changed=["README.md", "docs/guide.md", _CHANGESET],
    )
    assert res.ok
    assert res.required_local == ("reviewer", "docs-reviewer")


def test_changeset_only_unclassified_pr_is_baseline_only(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[],
        changed=[_CHANGESET],
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


@pytest.mark.parametrize(
    "code_path",
    [
        ".pkit/capabilities/project-management/scripts/_lib/required_reviewers.py",
        ".pkit/capabilities/project-management/schemas/review-contributions.yaml",
        ".pkit/capabilities/project-management/schemas/config.schema.json",
    ],
)
def test_changeset_with_code_still_requires_the_panel(rr, rc, code_path) -> None:
    """The exclusion is the changeset's alone: a `.py` or a schema alongside it
    still touches code, so the panel is required."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:docs"]},
        changed=["README.md", _CHANGESET, code_path],
    )
    assert res.ok
    assert res.required_local == _PANEL


def test_a_null_not_code_is_the_default(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[],
        changed=[_CHANGESET],
        not_code=None,
    )
    assert res.ok
    assert res.required_local == ("reviewer",)


def test_an_empty_not_code_excludes_nothing(rr, rc) -> None:
    """`not_code: []` is the adopter's choice that changesets count as code."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:docs"]},
        changed=["README.md", _CHANGESET],
        not_code=[],
    )
    assert res.ok
    assert res.required_local == _PANEL


def test_a_configured_not_code_replaces_the_default(rr, rc) -> None:
    """The adopter's list is the whole list: `.changes/` counts again unless it
    is listed, and what is listed is left out."""
    generated = "docs/examples/sample-config.yaml"
    replaced = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[],
        changed=[generated, _CHANGESET],
        not_code=["docs/examples/**"],
    )
    assert replaced.ok
    assert "code-reviewer" in replaced.required_local  # the changeset counts.

    extended = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[],
        changed=[generated, _CHANGESET],
        not_code=[".changes/**", "docs/examples/**"],
    )
    assert extended.ok
    assert extended.required_local == ("reviewer",)


@pytest.mark.parametrize(
    "raw,detail",
    [
        (".changes/**", "`review.floors.not_code` must be a list, got str"),
        ([".changes/**", 7], "`review.floors.not_code[1]` must be a non-empty path"),
        (["  "], "`review.floors.not_code[0]` must be a non-empty path"),
    ],
)
def test_malformed_not_code_fails_closed(rr, rc, raw, detail) -> None:
    """A malformed list applies nothing and the resolver refuses, naming it."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[],
        changed=[_CHANGESET],
        not_code=raw,
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_NOT_CODE
    assert res.required_local == ()
    assert any(d.startswith(detail) for d in res.error.details)


def test_satisfied_floors_reads_only_what_the_list_leaves(rr) -> None:
    """A path the list matches satisfies no floor, code suffix or not; a path it
    does not match is read by the suffix test exactly as before."""
    generated = rr.NotCode(patterns=("generated/**",))
    assert rr.satisfied_floors(["generated/client.py"], generated) == set()
    assert rr.satisfied_floors(
        ["generated/client.py", "src/app.py"],
        generated,
    ) == {rr.FLOOR_TOUCHES_CODE}
    assert rr.satisfied_floors([_CHANGESET]) == set()  # the shipped default.
    assert rr.satisfied_floors(
        [_CHANGESET],
        rr.NotCode(patterns=()),
    ) == {rr.FLOOR_TOUCHES_CODE}


# ---- which reviewers only a floor requires (#1179) ----------------------
#
# The freshness rule keeps a floor-scoped reviewer's approval standing until
# the author's changes reach one of its floors; any other reviewer is required
# for the whole change. A reviewer is floor-scoped only when every rule it has
# is a floor and nothing else. The resolution names the floor-scoped ones.

_CODE_AND_SECURITY_ON_THEIR_FLOOR = {
    "code-reviewer": frozenset({"touches-code"}),
    "security-reviewer": frozenset({"touches-code"}),
}


def test_floor_only_reviewers_on_a_classified_code_pr(rr, rc) -> None:
    """docs-reviewer is matched by the `type: *` classification rule, so it is
    required for the whole change; code and security only by their floor."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[42],
        labels={42: ["type:feature"]},
        changed=["src/app.py"],
    )
    assert res.floors_by_reviewer == _CODE_AND_SECURITY_ON_THEIR_FLOOR


def test_a_reviewer_with_a_classification_rule_is_not_floor_scoped(rr, rc) -> None:
    """With no classification to match, only the floor requires docs-reviewer
    on this PR — but its `type: *` rule declares a remit wider than the floor
    (its job is the documentation), so a Markdown fix must still stale it."""
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[],
        changed=["src/app.py"],
    )
    assert "docs-reviewer" in res.required_local
    assert res.floors_by_reviewer == _CODE_AND_SECURITY_ON_THEIR_FLOOR


def test_a_rule_carrying_a_floor_and_a_match_is_a_wider_remit(rr, rc) -> None:
    """One rule with both a floor and a classification match is not a floor
    and nothing else, so its reviewer is not floor-scoped."""
    rule = rc.ContributionRule(
        capability=_SE,
        predicate=MappingProxyType({"type": ("feature",)}),
        reviewer="code-reviewer",
        floor=rc.FLOOR_TOUCHES_CODE,
    )
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=rc.ContributionCollection(
            rules=(rule,),
            capabilities_walked=("project-management", _SE),
        ),
        closing=[],
        changed=["src/app.py"],
    )
    assert res.required_local == ("reviewer", "code-reviewer")
    assert res.floors_by_reviewer == {}


def test_a_baseline_reviewer_on_a_floor_is_required_for_the_whole_change(
    rr,
    rc,
) -> None:
    res = _resolve(
        rr,
        baseline=["code-reviewer"],
        collection=_floor_collection(rc),
        closing=[],
        changed=["src/app.py"],
    )
    assert res.required_local == ("code-reviewer",)
    assert res.floors_by_reviewer == {}


def test_the_resolution_carries_the_not_code_list_it_applied(rr, rc) -> None:
    res = _resolve(
        rr,
        baseline=["reviewer"],
        collection=_se_collection(rc),
        closing=[],
        changed=["src/app.py"],
        not_code=["generated/**"],
    )
    assert res.not_code.patterns == ("generated/**",)
    assert (
        _resolve(
            rr,
            baseline=["reviewer"],
            collection=_se_collection(rc),
            closing=[],
            changed=["src/app.py"],
        ).not_code
        == rr.DEFAULT_NOT_CODE
    )


def test_read_not_code(rr) -> None:
    default = rr.DEFAULT_NOT_CODE_PATTERNS
    assert default == (".changes/**",)
    assert rr.read_not_code({}).patterns == default
    assert rr.read_not_code({"review": {}}).patterns == default
    assert rr.read_not_code({"review": {"floors": {}}}).patterns == default
    assert rr.read_not_code(
        {"review": {"floors": {"not_code": [" a/** ", "b/*.yaml"]}}}
    ).patterns == ("a/**", "b/*.yaml")
