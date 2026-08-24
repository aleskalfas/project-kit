"""Tests for `done-work`'s honest approval-gate summary
(software-engineering:DEC-002 companion (c), realising DEC-050's distinct
`satisfied-by-override` state).

The summary must enumerate each required reviewer's disposition, per-perspective,
so a green gate can never imply every perspective reviewed the code (#715):

  * **APPROVED** — a genuine fresh approval;
  * **overridden** — satisfied-by-override, shown DISTINCTLY from APPROVED (never
    folded into an approved count), with the operator + reason;
  * **not reviewed** — a required reviewer overridden with NO verdict posted — a
    required-but-missing perspective, named explicitly.

The dispositions are computed by the passing agent-mode gate (`_check_agent_gate`,
exercised as in test_pm_done_work_agent_gate.py) and rendered by the pure
`_render_gate_summary`; the two are tested together so the classification and its
rendering cannot drift. The summary is a read/display projection (ADR-042) — it
never alters the gate outcome.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
SCRIPT = SCRIPTS_DIR / "done-work.py"
LIB_PATH = SCRIPTS_DIR / "_lib" / "review_contributions.py"


@pytest.fixture(scope="module")
def dw():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "pm_done_work_summary_under_test", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_done_work_summary_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def rc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_rc_for_summary", LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_rc_for_summary"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


CAP_ROOT = Path("/tmp/x/.pkit/capabilities/project-management")

_COMMIT_TS = "2026-06-01T00:00:00Z"
_FRESH_TS = "2026-06-02T00:00:00Z"
_VERDICT_MARKER = "<!-- pkit-verdict -->"


def _config(local=("reviewer",), remote=()):
    return {
        "review": {
            "agents": {
                "local_registered": [{"name": n} for n in local],
                "remote_registered": [{"github_login": g} for g in remote],
            }
        }
    }


def _local_verdict_comment(name, verdict, author="reviewer", ts=_FRESH_TS):
    return {
        "author": {"login": author},
        "body": f"Reviewer agent (local, {name}): {verdict}\n\nbody.\n\n{_VERDICT_MARKER}",
        "createdAt": ts,
        "url": f"https://example.test/c/{name}",
    }


def _wire(dw, monkeypatch, *, collection, comments, closing_issue_labels=None,
          pr_author="author", commits=None):
    closing_issue_labels = closing_issue_labels or {}
    commits = [{"committedDate": _COMMIT_TS}] if commits is None else commits

    monkeypatch.setattr(dw, "collect_contributions", lambda repo_root: collection)

    def fake_gh_run(args, config, **kwargs):
        joined = " ".join(args)
        if "closingIssuesReferences" in joined:
            refs = [{"number": n} for n in closing_issue_labels]
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"closingIssuesReferences": refs}), stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({
                "author": {"login": pr_author},
                "comments": comments,
                "commits": commits,
            }),
            stderr="",
        )

    def fake_gh_get_issue(issue_number, config, *, fields):
        labels = closing_issue_labels.get(issue_number, [])
        return {"labels": [{"name": n} for n in labels]}

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    monkeypatch.setattr(dw, "gh_get_issue", fake_gh_get_issue)


def _collection(rc, *reviewers):
    """A contribution collection requiring each named reviewer on
    `workstream:design` (so a design-labelled PR resolves them all)."""
    from types import MappingProxyType

    rules = tuple(
        rc.ContributionRule(
            capability="ux-ui-design",
            predicate=MappingProxyType({"workstream": ("design",)}),
            reviewer=name,
            deployed=True,
        )
        for name in reviewers
    )
    return rc.ContributionCollection(
        rules=rules,
        capabilities_walked=("project-management", "ux-ui-design"),
    )


def _invoker(dw):
    return dw.Identity(github_login="alice", email="alice@example.test")


def _summary(dw, result, reason=""):
    return "\n".join(dw._render_gate_summary(result, _invoker(dw), reason))


def _reviewer_line(text, name):
    """The single per-reviewer summary line mentioning *name* (the labels embed
    provenance, so match on the name substring rather than an exact label)."""
    hits = [ln for ln in text.splitlines() if name in ln and ln.strip().startswith("-")]
    assert len(hits) == 1, f"expected one line for {name!r}, got {hits}"
    return hits[0]


# ---- all approved ----------------------------------------------------


def test_all_approved_summary_names_every_perspective(dw, rc, monkeypatch) -> None:
    """Every required reviewer genuinely APPROVED → each is enumerated as
    APPROVED and the honesty line confirms all reviewed."""
    _wire(
        dw, monkeypatch,
        collection=_collection(rc, "design-reviewer"),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "APPROVED"),
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is True

    dispositions = result.reviewer_dispositions
    assert {d.disposition for d in dispositions} == {dw.DISPOSITION_APPROVED}

    text = _summary(dw, result)
    assert _reviewer_line(text, "(reviewer)").endswith(": APPROVED")
    assert _reviewer_line(text, "design-reviewer").endswith(": APPROVED")
    assert "all 2 required perspective(s) reviewed and approved." in text
    # A clean all-approved summary carries no override language.
    assert "overridden" not in text
    assert "NOT REVIEWED" not in text


# ---- one overridden --------------------------------------------------


def test_one_overridden_shown_distinct_with_operator_and_reason(dw, rc, monkeypatch) -> None:
    """A reviewer with a fresh block that is overridden is shown DISTINCTLY from
    APPROVED, naming the operator + reason and the state at override time."""
    _wire(
        dw, monkeypatch,
        collection=_collection(rc, "design-reviewer"),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "CHANGES_REQUESTED"),
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("design-reviewer",),
    )
    assert result.passed is True

    by_disp = {d.disposition for d in result.reviewer_dispositions}
    assert by_disp == {dw.DISPOSITION_APPROVED, dw.DISPOSITION_OVERRIDDEN}

    text = _summary(dw, result, reason="flaky false block")
    # The genuinely-approved baseline is still APPROVED.
    assert _reviewer_line(text, "(reviewer)").endswith(": APPROVED")
    # The overridden reviewer is NOT counted as approved — a distinct line with
    # operator + reason + the waived state.
    design_line = _reviewer_line(text, "design-reviewer")
    assert "overridden by alice" in design_line
    assert 'reason: "flaky false block"' in design_line
    assert "fresh CHANGES_REQUESTED" in design_line
    # Honesty line names the overridden perspective as one that did not review.
    assert "1 of 2 required perspective(s) did NOT genuinely review" in text
    assert "design-reviewer" in text.split("honesty:")[1]


# ---- not reviewed / missing required perspective ---------------------


def test_not_reviewed_required_perspective_named(dw, rc, monkeypatch) -> None:
    """A required reviewer overridden with NO verdict posted is a required-but-
    missing perspective: shown as NOT REVIEWED and named in the honesty line —
    a green summary must not imply it reviewed."""
    _wire(
        dw, monkeypatch,
        collection=_collection(rc, "design-reviewer"),
        comments=[
            # baseline approved; design-reviewer never posted a verdict.
            _local_verdict_comment("reviewer", "APPROVED"),
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("design-reviewer",),
    )
    assert result.passed is True

    not_reviewed = [
        d for d in result.reviewer_dispositions
        if d.disposition == dw.DISPOSITION_NOT_REVIEWED
    ]
    assert len(not_reviewed) == 1
    assert "design-reviewer" in not_reviewed[0].label

    text = _summary(dw, result, reason="agent undeployed this run")
    design_line = _reviewer_line(text, "design-reviewer")
    assert "NOT REVIEWED — overridden by alice" in design_line
    assert "no verdict posted" in design_line
    assert "did NOT genuinely review" in text
    assert "design-reviewer" in text.split("honesty:")[1]


# ---- mixed -----------------------------------------------------------


def test_mixed_dispositions_all_enumerated(dw, rc, monkeypatch) -> None:
    """A panel with one genuine APPROVED, one overridden block, and one
    overridden-not-reviewed reviewer enumerates all three disposition kinds and
    names the two that did not genuinely review."""
    _wire(
        dw, monkeypatch,
        collection=_collection(rc, "design-reviewer", "security-reviewer"),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "CHANGES_REQUESTED"),
            # security-reviewer never posted a verdict.
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("design-reviewer", "security-reviewer"),
    )
    assert result.passed is True

    by_label = {d.label: d.disposition for d in result.reviewer_dispositions}
    assert by_label["local agent (reviewer)"] == dw.DISPOSITION_APPROVED
    design = next(k for k in by_label if "design-reviewer" in k)
    security = next(k for k in by_label if "security-reviewer" in k)
    assert by_label[design] == dw.DISPOSITION_OVERRIDDEN
    assert by_label[security] == dw.DISPOSITION_NOT_REVIEWED

    text = _summary(dw, result, reason="mixed batch")
    assert _reviewer_line(text, "(reviewer)").endswith(": APPROVED")
    assert "overridden by alice" in _reviewer_line(text, "design-reviewer")
    assert "NOT REVIEWED — overridden by alice" in _reviewer_line(text, "security-reviewer")
    honesty = text.split("honesty:")[1]
    assert "2 of 3 required perspective(s) did NOT genuinely review" in text
    assert "design-reviewer" in honesty
    assert "security-reviewer" in honesty


# ---- read/display only: bypass + human paths carry no per-reviewer block ----


def test_bypass_gate_summary_is_gate_line_only(dw) -> None:
    """A whole-gate --bypass carries no dispositions (the entire gate was
    discarded), so the summary is just the honest `gate:` line — no per-reviewer
    enumeration to fabricate."""
    result = dw._GateResult(passed=True, passed_via="--bypass: PM authorised")
    lines = dw._render_gate_summary(result, _invoker(dw), "")
    assert lines == ["  gate:    --bypass: PM authorised"]
