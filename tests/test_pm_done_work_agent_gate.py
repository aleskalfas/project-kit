"""Tests for `done-work`'s agent-mode gate-checker (DEC-028 + DEC-032).

These cover the conditional-reviewer resolution + AND-composition wired into
`done-work` per project-management:DEC-032 (#145):

  * **compose** — baseline + a contributed reviewer both required; the gate
    passes only when BOTH have a fresh APPROVED (D3 AND-across-set).
  * **backward-equivalence** — with no contributions and the single baseline
    reviewer the gate is the same as DEC-028's (the property #145 must hold).
  * **multi-issue union** — a PR closing a `design` issue and a `backend`
    issue requires both contributed reviewers (D1 union).
  * **baseline-only fallbacks** — no closing issue, or a closing entity with
    no `workstream` axis, resolves to baseline only (D1 resolution domain).
  * **FAIL-CLOSED** — an undeployed contributed reviewer / a not-ok
    collection refuses the gate (D5), never proceeds on the baseline.

The gate-checker's contribution collection (`collect_contributions`) and the
gh layer (`gh_run` for `gh pr view`, `gh_get_issue` for closing-issue labels)
are stubbed so the tests exercise the resolution + composition logic without
a real repo tree or GitHub.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
SCRIPT = SCRIPTS_DIR / "done-work.py"
LIB_PATH = SCRIPTS_DIR / "_lib" / "review_contributions.py"


@pytest.fixture(scope="module")
def dw():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_done_work_agent_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_done_work_agent_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def rc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_rc_for_agent_gate", LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_rc_for_agent_gate"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


# A capability_root whose .parent.parent.parent is some throwaway repo_root.
# collect_contributions is stubbed, so the actual path is never read.
CAP_ROOT = Path("/tmp/x/.pkit/capabilities/project-management")

# A commit timestamp every verdict comment post-dates (freshness anchor).
_COMMIT_TS = "2026-06-01T00:00:00Z"
_FRESH_TS = "2026-06-02T00:00:00Z"
# A second fresh timestamp strictly after _FRESH_TS (for latest-by-timestamp).
_LATER_TS = "2026-06-03T00:00:00Z"


def _config(local=("reviewer",), remote=()):
    return {
        "review": {
            "agents": {
                "local_registered": [{"name": n} for n in local],
                "remote_registered": [{"github_login": g} for g in remote],
            }
        }
    }


# Real reviewer-path verdicts carry the `<!-- pkit-verdict -->` marker the gate
# now requires (#593); `marked=False` simulates an unstamped verdict-grammar
# comment, which must NOT satisfy the gate.
_VERDICT_MARKER = "<!-- pkit-verdict -->"


def _local_verdict_comment(name, verdict, author="reviewer", ts=_FRESH_TS, marked=True):
    tail = f"\n\n{_VERDICT_MARKER}" if marked else ""
    return {
        "author": {"login": author},
        "body": f"Reviewer agent (local, {name}): {verdict}\n\nbody.{tail}",
        "createdAt": ts,
    }


def _remote_verdict_comment(verdict, author="review-bot", ts=_FRESH_TS, marked=True):
    tail = f"\n\n{_VERDICT_MARKER}" if marked else ""
    return {
        "author": {"login": author},
        "body": f"Reviewer agent: {verdict}\n\nbody.{tail}",
        "createdAt": ts,
    }


def _wire(
    dw,
    monkeypatch,
    *,
    collection,
    comments,
    closing_issue_labels=None,
    pr_author="author",
    closing_refs_returncode=0,
    closing_refs_stdout=None,
    issue_fetch_none=(),
    commits=None,
    changed_files=("README.md",),
):
    """Stub collect_contributions + the gh layer for one gate check.

    `collection` is the ContributionCollection collect_contributions returns.
    `comments` is the PR's verdict comments. `closing_issue_labels` maps an
    issue number → its label-name list (drives closing-issue resolution).

    Failure-injection knobs (for the fail-closed paths):
      * `closing_refs_returncode` / `closing_refs_stdout` — force the
        `gh pr view --json closingIssuesReferences` call to fail / return
        malformed JSON.
      * `issue_fetch_none` — a set of issue numbers whose `gh_get_issue`
        returns None (label fetch failed).
      * `commits` — override the commits payload (e.g. `[]` to remove the
        freshness anchor).

    `changed_files` is the PR's diff (the paginated files API, one file per
    page entry), read only when a floor-carrying contribution is installed.
    """
    closing_issue_labels = closing_issue_labels or {}
    commits = [{"committedDate": _COMMIT_TS}] if commits is None else commits

    monkeypatch.setattr(dw, "collect_contributions", lambda repo_root: collection)

    def fake_gh_run(args, config, **kwargs):
        joined = " ".join(args)
        if "closingIssuesReferences" in joined:
            if closing_refs_returncode != 0:
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=closing_refs_returncode,
                    stdout="",
                    stderr="gh: closingIssuesReferences failed",
                )
            if closing_refs_stdout is not None:
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout=closing_refs_stdout,
                    stderr="",
                )
            refs = [{"number": n} for n in closing_issue_labels]
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"closingIssuesReferences": refs}),
                stderr="",
            )
        if args[:2] == ["gh", "api"] and "/files" in joined:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=_files_api_pages(list(changed_files)), stderr="",
            )
        # gh pr view --json author,comments,commits
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                {
                    "author": {"login": pr_author},
                    "comments": comments,
                    "commits": commits,
                }
            ),
            stderr="",
        )

    def fake_gh_get_issue(issue_number, config, *, fields):
        if issue_number in issue_fetch_none:
            return None
        labels = closing_issue_labels.get(issue_number, [])
        return {"labels": [{"name": n} for n in labels]}

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    monkeypatch.setattr(dw, "gh_get_issue", fake_gh_get_issue)


def _design_collection(rc, *, deployed=True):
    """A collection with ux-ui-design contributing design-reviewer for design."""
    from types import MappingProxyType

    err = (
        None
        if deployed
        else rc.ContributionError(
            rc.ERROR_UNDEPLOYED_AGENT,
            "ux-ui-design",
            "design-reviewer is not deployed",
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


# ---- backward-equivalence (no contributions = DEC-028 behaviour) ------


def test_backward_equiv_single_baseline_local_approved(dw, rc, monkeypatch) -> None:
    """No contributions + single baseline local reviewer APPROVED → pass."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True
    assert "reviewer" in result.passed_via


def test_backward_equiv_single_baseline_no_verdict_refuses(dw, rc, monkeypatch) -> None:
    """No contributions + baseline reviewer with no fresh verdict → refuse."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[],
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "reviewer" in result.refusal_message


def test_backward_equiv_changes_requested_refuses(dw, rc, monkeypatch) -> None:
    """A fresh CHANGES_REQUESTED from the baseline reviewer → refuse."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[_local_verdict_comment("reviewer", "CHANGES_REQUESTED")],
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False


def test_backward_equiv_stale_verdict_ignored(dw, rc, monkeypatch) -> None:
    """An APPROVED verdict that predates the latest commit is stale → refuse."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED", ts="2026-05-01T00:00:00Z"),
        ],
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False


def test_backward_equiv_remote_baseline_approved(dw, rc, monkeypatch) -> None:
    """A remote-only baseline reviewer with a fresh APPROVED → pass."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[_remote_verdict_comment("APPROVED", author="review-bot")],
        pr_author="author",
    )
    result = dw._check_agent_gate(
        99, {}, _config(local=(), remote=("review-bot",)), "resolved", CAP_ROOT
    )
    assert result.passed is True
    assert "review-bot" in result.passed_via


def test_backward_equiv_dual_path_reviewer_satisfied_via_remote(dw, rc, monkeypatch) -> None:
    """A baseline reviewer registered on BOTH paths (a bot login + a local
    agent of the same name) is satisfied by either path's fresh APPROVED —
    DEC-028's per-reviewer OR-across-paths, required once."""
    config = {
        "review": {
            "agents": {
                "local_registered": [{"name": "reviewer"}],
                "remote_registered": [{"github_login": "reviewer"}],
            }
        }
    }
    # Only the remote path posted APPROVED; local path silent.
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[_remote_verdict_comment("APPROVED", author="reviewer")],
        pr_author="author",
    )
    result = dw._check_agent_gate(99, {}, config, "resolved", CAP_ROOT)
    assert result.passed is True


# ---- compose (baseline + contributed both required) -------------------


def test_compose_both_approved_passes(dw, rc, monkeypatch) -> None:
    """design PR: baseline reviewer + design-reviewer both APPROVED → pass."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "APPROVED"),
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True
    assert "design-reviewer" in result.passed_via
    assert "reviewer" in result.passed_via


def test_compose_only_baseline_approved_refuses(dw, rc, monkeypatch) -> None:
    """design PR: baseline APPROVED but design-reviewer missing → refuse."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    # The refusal must name the contributed reviewer + its provenance.
    assert "design-reviewer" in result.refusal_message
    assert "ux-ui-design" in result.refusal_message


def test_compose_only_contributed_approved_refuses(dw, rc, monkeypatch) -> None:
    """design PR: design-reviewer APPROVED but baseline missing → refuse."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("design-reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "reviewer" in result.refusal_message


# ---- multi-issue union (D1) -------------------------------------------


def test_multi_issue_union_requires_both(dw, rc, monkeypatch) -> None:
    """A PR closing a design issue + a backend issue requires both reviewers."""
    from types import MappingProxyType

    design_rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="design-reviewer",
    )
    backend_rule = rc.ContributionRule(
        capability="backend-discipline",
        predicate=MappingProxyType({"workstream": ("backend",)}),
        reviewer="backend-reviewer",
    )
    collection = rc.ContributionCollection(rules=(design_rule, backend_rule))

    # Only the design-reviewer has approved → still refused (backend missing).
    _wire(
        dw,
        monkeypatch,
        collection=collection,
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "APPROVED"),
        ],
        closing_issue_labels={
            42: ["workstream:design"],
            43: ["workstream:backend"],
        },
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "backend-reviewer" in result.refusal_message

    # Now all three approve → pass.
    _wire(
        dw,
        monkeypatch,
        collection=collection,
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "APPROVED"),
            _local_verdict_comment("backend-reviewer", "APPROVED"),
        ],
        closing_issue_labels={
            42: ["workstream:design"],
            43: ["workstream:backend"],
        },
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True


# ---- baseline-only fallbacks (D1 resolution domain) -------------------


def test_no_closing_issue_baseline_only(dw, rc, monkeypatch) -> None:
    """A PR closing no issue resolves to baseline only — contributed rule
    present in the collection but never required."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={},  # PR closes nothing.
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True
    assert "design-reviewer" not in result.passed_via


def test_closing_entity_no_workstream_axis_baseline_only(dw, rc, monkeypatch) -> None:
    """A closing issue with no workstream label matches nothing → baseline only."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["priority:High", "type:feature"]},  # no workstream.
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True
    assert "design-reviewer" not in result.passed_via


def test_non_matching_workstream_baseline_only(dw, rc, monkeypatch) -> None:
    """A design-reviewer rule does not fire for a backend-workstream PR."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:backend"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True
    assert "design-reviewer" not in result.passed_via


# ---- FAIL-CLOSED (D5) -------------------------------------------------


def test_fail_closed_undeployed_contributed_reviewer(dw, rc, monkeypatch) -> None:
    """An installed contribution naming an undeployed agent → refuse, even
    with the baseline reviewer APPROVED. The gate never proceeds on baseline."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc, deployed=False),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "unsatisfiable" in result.refusal_message
    assert "ux-ui-design" in result.refusal_message


def test_fail_closed_not_ok_collection(dw, rc, monkeypatch) -> None:
    """A collection with a blocking (malformed-declaration) error → refuse."""
    err = rc.ContributionError(
        rc.ERROR_MALFORMED,
        "ux-ui-design",
        "contributions[0].reviewer must be a non-empty string",
    )
    collection = rc.ContributionCollection(rules=(), errors=(err,))
    _wire(
        dw,
        monkeypatch,
        collection=collection,
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "must be a non-empty string" in result.refusal_message


# ---- dedup (a reviewer named by both baseline + contribution) ---------


def test_dedup_reviewer_required_once(dw, rc, monkeypatch) -> None:
    """A reviewer named by both baseline and a contribution is required once
    — its single APPROVED satisfies the gate."""
    from types import MappingProxyType

    rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="reviewer",  # same name as the baseline.
    )
    collection = rc.ContributionCollection(rules=(rule,))
    _wire(
        dw,
        monkeypatch,
        collection=collection,
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True
    # Only one "reviewer ... APPROVED" segment (deduped).
    assert result.passed_via.count("APPROVED") == 1


# ---- FAIL-CLOSED: closing-issue resolution failure (#145 finding 1/2) ----


def test_fail_closed_closing_refs_gh_failure_refuses(dw, rc, monkeypatch) -> None:
    """`gh pr view closingIssuesReferences` exits non-zero on a design PR with
    only the baseline approved → REFUSE (not baseline-only).

    A transient gh failure resolving what the PR closes must not silently drop
    a genuinely-required contributed reviewer (DEC-032 D5). The contributed
    set is UNKNOWN, not empty — the gate fails closed.
    """
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_refs_returncode=1,
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "classification is unknown" in result.refusal_message
    assert "retry `done-work`" in result.refusal_message


def test_fail_closed_closing_refs_malformed_json_refuses(dw, rc, monkeypatch) -> None:
    """Malformed JSON from the closingIssuesReferences call → REFUSE."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_refs_stdout="{not valid json",
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "classification is unknown" in result.refusal_message


def test_fail_closed_issue_label_fetch_none_refuses(dw, rc, monkeypatch) -> None:
    """One of two closing issues' label fetch (`gh_get_issue`) returns None →
    REFUSE, even with the baseline approved.

    The unreadable issue's classification is UNKNOWN; a contributed reviewer
    it might require cannot be dropped (DEC-032 D5).
    """
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"], 43: ["workstream:backend"]},
        issue_fetch_none={43},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "classification is unknown" in result.refusal_message
    assert "#43" in result.refusal_message


def test_pr_closes_nothing_still_baseline_only(dw, rc, monkeypatch) -> None:
    """The legitimate fail-open branch is preserved: an empty
    closingIssuesReferences array (PR closes nothing) → baseline only, NOT a
    refusal. Distinguishes 'closes nothing' from 'could not determine'."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={},  # array present + empty.
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True
    assert "design-reviewer" not in result.passed_via


# ---- FAIL-CLOSED: freshness anchor unestablishable (#145 finding 3) ------


def test_fail_closed_no_commit_timestamp_refuses(dw, rc, monkeypatch) -> None:
    """No commits returned → no freshness anchor → REFUSE.

    Previously the freshness guard was skipped when latest_commit_ts was
    empty, accepting every (possibly-stale) verdict. An unestablishable
    freshness anchor must fail closed (DEC-032 D5)."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        commits=[],
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "freshness anchor is unknown" in result.refusal_message


def test_fail_closed_commit_missing_timestamp_fields_refuses(dw, rc, monkeypatch) -> None:
    """A commit with neither committedDate nor authoredDate → REFUSE."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        commits=[{"oid": "abc123"}],
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "freshness anchor is unknown" in result.refusal_message


# ---- latest-per-agent BY TIMESTAMP, not list order (#145 finding 4) ------


def test_latest_by_timestamp_changes_requested_after_approved_blocks(dw, rc, monkeypatch) -> None:
    """APPROVED then a LATER-timestamp CHANGES_REQUESTED → the later verdict
    wins (REFUSE), regardless of array order — array places APPROVED last."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[
            # CHANGES_REQUESTED is later by timestamp but earlier in the array.
            _local_verdict_comment("reviewer", "CHANGES_REQUESTED", ts=_LATER_TS),
            _local_verdict_comment("reviewer", "APPROVED", ts=_FRESH_TS),
        ],
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False


def test_latest_by_timestamp_approved_after_changes_requested_passes(dw, rc, monkeypatch) -> None:
    """CHANGES_REQUESTED then a LATER-timestamp APPROVED → the later APPROVED
    wins (PASS), even though CHANGES_REQUESTED is last in the array."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[
            # APPROVED is later by timestamp but earlier in the array.
            _local_verdict_comment("reviewer", "APPROVED", ts=_LATER_TS),
            _local_verdict_comment("reviewer", "CHANGES_REQUESTED", ts=_FRESH_TS),
        ],
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True


def test_latest_by_timestamp_remote_path(dw, rc, monkeypatch) -> None:
    """Same latest-by-timestamp selection on the remote path: a later
    CHANGES_REQUESTED after an APPROVED blocks regardless of array order."""
    _wire(
        dw,
        monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[
            _remote_verdict_comment("CHANGES_REQUESTED", author="review-bot", ts=_LATER_TS),
            _remote_verdict_comment("APPROVED", author="review-bot", ts=_FRESH_TS),
        ],
        pr_author="author",
    )
    result = dw._check_agent_gate(
        99, {}, _config(local=(), remote=("review-bot",)), "resolved", CAP_ROOT
    )
    assert result.passed is False


# ---- multi-workstream label on one issue (#145 finding 5) ----------------


def test_multi_workstream_label_refuses(dw, rc, monkeypatch) -> None:
    """An issue carrying two distinct workstream labels violates DEC-012's
    mutually-exclusive workstream axis. The gate refuses rather than guess
    which workstream's contributed reviewer to honour (fail-closed)."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design", "workstream:backend"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "multiple workstream" in result.refusal_message


def test_duplicate_same_workstream_label_is_single(dw, rc, monkeypatch) -> None:
    """The same workstream value repeated is not multi-workstream — it
    resolves normally (defensive: dedup before the multi-value guard)."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "APPROVED"),
        ],
        closing_issue_labels={42: ["workstream:design", "workstream:design"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True


# ---- per-contribution opt-out (#148) ------------------------------------

_DESIGN_OPT_OUT = {
    "capability": "ux-ui-design",
    "reviewer": "design-reviewer",
    "reason": "This project has no UI.",
}


def _config_opting_out(*opt_outs):
    config = _config()
    config["review"]["agents"]["contributed_opt_out"] = list(opt_outs)
    return config


def test_opted_out_reviewer_is_not_required(dw, rc, monkeypatch) -> None:
    """A design PR with design-reviewer opted out passes on the baseline
    approval alone — the contributed gate no longer applies."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99,
        {},
        _config_opting_out(_DESIGN_OPT_OUT),
        "resolved",
        CAP_ROOT,
    )
    assert result.passed is True, result.refusal_message
    assert "design-reviewer" not in result.passed_via


def test_opted_out_undeployed_reviewer_does_not_fail_closed(dw, rc, monkeypatch) -> None:
    """An undeployed contributed agent refuses the gate (D5) unless its
    contribution is opted out — then it is never required."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc, deployed=False),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99,
        {},
        _config_opting_out(_DESIGN_OPT_OUT),
        "resolved",
        CAP_ROOT,
    )
    assert result.passed is True, result.refusal_message


def test_opt_out_naming_no_contribution_refuses(dw, rc, monkeypatch) -> None:
    """An opt-out naming a reviewer no installed capability contributes is a
    validation error: the gate refuses, naming the entry and the key to fix."""
    _wire(
        dw,
        monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99,
        {},
        _config_opting_out({**_DESIGN_OPT_OUT, "reviewer": "ui-reviewer"}),
        "resolved",
        CAP_ROOT,
    )
    assert result.passed is False
    assert "opt-out list is invalid" in result.refusal_message
    assert "contributed_opt_out[0]" in result.refusal_message
    assert "no reviewer `ui-reviewer`" in result.refusal_message


# ---- diff floor on a PR past `gh pr diff`'s 300 files (#1188) -------------
#
# GitHub refuses `gh pr diff` for a PR changing more than 300 files, which made
# the changed-file read fail and the gate refuse such a PR as a "transient"
# failure. The gate now reads every page of the files API, so a 350-file PR
# resolves its floor reviewer like any other, and the refusal that remains for
# a PR past GitHub's 3000-file listing says so instead of asking for a retry.


def _floor_collection(rc):
    """software-engineering's code-reviewer, required whenever code changes."""
    rule = rc.ContributionRule(
        capability="software-engineering",
        predicate={},
        reviewer="code-reviewer",
        floor=rc.FLOOR_TOUCHES_CODE,
    )
    return rc.ContributionCollection(rules=(rule,))


def _files_api_pages(paths, size=100):
    """`gh api --paginate … --jq` output for `paths`, `size` files per page."""
    pages = [paths[i : i + size] for i in range(0, len(paths), size)]
    return "".join(json.dumps([path, None]) + "\n" for page in pages for path in page)


def _wire_files_api(dw, monkeypatch, *, stdout="", returncode=0, stderr=""):
    """Answer the PR files API on top of `_wire`'s gh fake; record each call."""
    inner = dw.gh_run
    calls: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        if args[:2] == ["gh", "api"] and "/files" in " ".join(args):
            calls.append(args)
            return subprocess.CompletedProcess(
                args=args,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
        return inner(args, config, **kwargs)

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    return calls


# 350 files over four pages: docs throughout, one code file on the last page,
# so only a read of every page sees that the PR touches code.
_LARGE_PR_PATHS = [f"docs/page_{i}.md" for i in range(349)] + ["src/late.py"]


def test_large_pr_resolves_floor_reviewer_and_passes(dw, rc, monkeypatch) -> None:
    """A 350-file PR resolves code-reviewer from the code file on page four,
    and passes once it approves."""
    _wire(
        dw,
        monkeypatch,
        collection=_floor_collection(rc),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("code-reviewer", "APPROVED"),
        ],
        closing_issue_labels={42: ["type:docs"]},
    )
    calls = _wire_files_api(
        dw,
        monkeypatch,
        stdout=_files_api_pages(_LARGE_PR_PATHS),
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert len(calls) == 1
    assert result.passed is True
    assert "code-reviewer" in result.passed_via


def test_large_pr_still_requires_the_floor_reviewer(dw, rc, monkeypatch) -> None:
    """The same PR with only the baseline approved refuses, naming the floor
    reviewer the last page brought in — the floor is computed, not skipped."""
    _wire(
        dw,
        monkeypatch,
        collection=_floor_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["type:docs"]},
    )
    _wire_files_api(dw, monkeypatch, stdout=_files_api_pages(_LARGE_PR_PATHS))
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "code-reviewer" in result.refusal_message


def test_files_api_failure_refuses_as_transient(dw, rc, monkeypatch) -> None:
    """A failed files read refuses (fail closed) and asks for a retry."""
    _wire(
        dw,
        monkeypatch,
        collection=_floor_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["type:docs"]},
    )
    _wire_files_api(dw, monkeypatch, returncode=1, stderr="HTTP 502")
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "changed files cannot be read" in result.refusal_message
    assert "HTTP 502" in result.refusal_message
    assert "retry `done-work`" in result.refusal_message


def test_files_api_empty_refuses(dw, rc, monkeypatch) -> None:
    """An empty files read is unknown ground truth, not a docs-only PR."""
    _wire(
        dw,
        monkeypatch,
        collection=_floor_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["type:docs"]},
    )
    _wire_files_api(dw, monkeypatch, stdout="")
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "changed files cannot be read" in result.refusal_message


def test_pr_past_the_listing_ceiling_refuses_naming_the_cause(
    dw,
    rc,
    monkeypatch,
) -> None:
    """A PR reaching GitHub's 3000-file listing refuses with the cause and a
    split-the-PR remediation, not a "transient gh failure" retry."""
    _wire(
        dw,
        monkeypatch,
        collection=_floor_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["type:docs"]},
    )
    paths = [f"docs/page_{i}.md" for i in range(3000)]
    _wire_files_api(dw, monkeypatch, stdout=_files_api_pages(paths))
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    message = result.refusal_message
    assert "changed files cannot be read" in message
    assert "at least 3000 files" in message
    assert "Split the PR" in message
    assert "not transient" in message
    assert "Transient gh failure" not in message


# ---- the not-code list (#1178) ------------------------------------------
#
# The gate reads `review.floors.not_code` from the config exactly as review-pr
# does, so a changeset-only diff does not require a floor reviewer here either.

_CHANGESET = ".changes/unreleased/project-management-none-20261001-wording.yaml"


def test_changeset_only_diff_needs_no_floor_reviewer(dw, rc, monkeypatch) -> None:
    _wire(
        dw, monkeypatch,
        collection=_floor_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        changed_files=("README.md", _CHANGESET),
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True, result.refusal_message
    assert "code-reviewer" not in result.passed_via


def test_changeset_with_code_needs_the_floor_reviewer(dw, rc, monkeypatch) -> None:
    _wire(
        dw, monkeypatch,
        collection=_floor_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        changed_files=(_CHANGESET, "src/app.py"),
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    assert "code-reviewer" in result.refusal_message


def test_large_pr_with_only_a_changeset_beside_docs_needs_no_floor_reviewer(
    dw, rc, monkeypatch,
) -> None:
    """The list is applied to every page the files API returns: a 350-file PR
    of docs whose one non-doc file, on the last page, is its changeset draws
    no floor reviewer."""
    _wire(
        dw, monkeypatch,
        collection=_floor_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["type:docs"]},
    )
    paths = [*_LARGE_PR_PATHS[:-1], _CHANGESET]
    _wire_files_api(dw, monkeypatch, stdout=_files_api_pages(paths))
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True, result.refusal_message
    assert "code-reviewer" not in result.passed_via


def test_malformed_not_code_refuses(dw, rc, monkeypatch) -> None:
    _wire(
        dw, monkeypatch,
        collection=_floor_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        changed_files=(_CHANGESET,),
    )
    config = _config()
    config["review"]["floors"] = {"not_code": ".changes/**"}
    result = dw._check_agent_gate(99, {}, config, "resolved", CAP_ROOT)
    assert result.passed is False
    assert "not-code list is invalid" in result.refusal_message
    assert "`review.floors.not_code` must be a list" in result.refusal_message
