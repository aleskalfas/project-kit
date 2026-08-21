"""Tests for `done-work`'s per-reviewer override (project-management:DEC-050).

`--bypass-reviewer <name> --bypass-reason "<r>"` satisfies ONE named required
reviewer's slot as a first-class `satisfied-by-override` state — distinct from a
fresh APPROVED — while every other required reviewer still gates. These cover:

  * **one slot** — override satisfies exactly one reviewer; the others still
    gate (a genuine APPROVED still required on them).
  * **hard error** — a `--bypass-reviewer` name not in the freshly-resolved
    required set refuses, naming the resolved set.
  * **all-slots nudge** — overriding every slot warns (steers to `--bypass`)
    but still proceeds.
  * **verdict-distinctness** — the audit comment is NOT counted by the gate's
    verdict reader (`gate_verdicts`).
  * **idempotency** — the per-reviewer(+reason) stamp makes a re-run a no-op,
    while a different reviewer / reason posts anew.
  * **ephemeral** — the override does not persist: a later run WITHOUT the flag
    re-resolves and refuses.

The gate-checker (`_check_agent_gate`) is exercised directly (mirroring
test_pm_done_work_agent_gate.py's style); the audit-comment shape + idempotency
+ verdict-distinctness are exercised via the pure helpers so no live gh is
needed.
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
VERDICTS_PATH = SCRIPTS_DIR / "_lib" / "agent_verdicts.py"


@pytest.fixture(scope="module")
def dw():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "pm_done_work_override_under_test", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_done_work_override_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def rc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_rc_for_override", LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_rc_for_override"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def av():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_av_for_override", VERDICTS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_av_for_override"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


CAP_ROOT = Path("/tmp/x/.pkit/capabilities/project-management")

_COMMIT_TS = "2026-06-01T00:00:00Z"
_FRESH_TS = "2026-06-02T00:00:00Z"
_STALE_TS = "2026-05-01T00:00:00Z"
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


def _local_verdict_comment(name, verdict, author="reviewer", ts=_FRESH_TS,
                           marked=True, url=None):
    tail = f"\n\n{_VERDICT_MARKER}" if marked else ""
    return {
        "author": {"login": author},
        "body": f"Reviewer agent (local, {name}): {verdict}\n\nbody.{tail}",
        "createdAt": ts,
        "url": url or f"https://example.test/c/{name}",
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


def _design_collection(rc):
    from types import MappingProxyType

    rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="design-reviewer",
        deployed=True,
    )
    return rc.ContributionCollection(
        rules=(rule,),
        capabilities_walked=("project-management", "ux-ui-design"),
    )


# ---- override satisfies exactly one slot -----------------------------


def test_override_satisfies_one_slot_others_gate(dw, rc, monkeypatch) -> None:
    """design PR: baseline APPROVED, design-reviewer BLOCKED but overridden →
    pass. The override satisfies exactly the named slot."""
    _wire(
        dw, monkeypatch,
        collection=_design_collection(rc),
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
    assert "satisfied-by-override" in result.passed_via
    assert "design-reviewer" in result.passed_via
    # The non-overridden baseline reviewer is shown as a real APPROVED.
    assert "reviewer" in result.passed_via


def test_override_one_slot_other_still_required(dw, rc, monkeypatch) -> None:
    """Overriding design-reviewer does NOT satisfy the baseline reviewer — a
    genuine APPROVED on the others is still required (AND-across-set holds)."""
    _wire(
        dw, monkeypatch,
        collection=_design_collection(rc),
        comments=[
            # baseline has NO fresh verdict; design-reviewer blocked.
            _local_verdict_comment("design-reviewer", "CHANGES_REQUESTED"),
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("design-reviewer",),
    )
    assert result.passed is False
    # The refusal still names the un-overridden baseline reviewer as missing,
    # and shows the overridden one as satisfied-by-override.
    assert "reviewer" in result.refusal_message
    assert "satisfied-by-override" in result.refusal_message


def test_override_with_genuine_approval_on_others_passes(dw, rc, monkeypatch) -> None:
    """A genuine APPROVED on the baseline + an override on design-reviewer →
    pass (the required-others-approve property)."""
    _wire(
        dw, monkeypatch,
        collection=_design_collection(rc),
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("design-reviewer",),
    )
    assert result.passed is True


# ---- unknown name → hard error ---------------------------------------


def test_unknown_override_name_hard_errors(dw, rc, monkeypatch) -> None:
    """A --bypass-reviewer name not in the resolved set refuses, naming the
    resolved set (DEC-050 Decision 5)."""
    _wire(
        dw, monkeypatch,
        collection=_design_collection(rc),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "APPROVED"),
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("typo-reviewer",),
    )
    assert result.passed is False
    assert "not in the freshly-resolved required set" in result.refusal_message
    assert "typo-reviewer" in result.refusal_message
    # Names the resolved set so the operator can correct the typo.
    assert "design-reviewer" in result.refusal_message
    assert "reviewer" in result.refusal_message


# ---- all-slots nudge → warn but proceed ------------------------------


def test_all_slots_override_warns_but_proceeds(dw, rc, monkeypatch) -> None:
    """Overriding EVERY required slot warns (steers to --bypass) but still
    passes (DEC-050 Decision 6 — a warning, not a refusal)."""
    _wire(
        dw, monkeypatch,
        collection=_design_collection(rc),
        comments=[
            _local_verdict_comment("reviewer", "CHANGES_REQUESTED"),
            _local_verdict_comment("design-reviewer", "CHANGES_REQUESTED"),
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("reviewer", "design-reviewer"),
    )
    assert result.passed is True
    assert any("covers EVERY required reviewer" in w for w in result.warnings)
    assert any("--bypass" in w for w in result.warnings)


def test_partial_override_no_all_slots_warning(dw, rc, monkeypatch) -> None:
    """Overriding a strict subset does NOT trigger the all-slots nudge."""
    _wire(
        dw, monkeypatch,
        collection=_design_collection(rc),
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
    assert result.warnings == []


# ---- unresolvable set → override cannot help -------------------------


def test_override_on_unresolvable_set_points_at_bypass(dw, rc, monkeypatch) -> None:
    """When the required set is unresolvable (undeployed contributed agent), a
    --bypass-reviewer cannot help — the refusal steers to whole-gate --bypass
    (DEC-050 Decision 5)."""
    from types import MappingProxyType

    err = rc.ContributionError(
        rc.ERROR_UNDEPLOYED_AGENT, "ux-ui-design",
        "design-reviewer is not deployed",
    )
    rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="design-reviewer",
        deployed=False,
        resolution_error=err,
    )
    collection = rc.ContributionCollection(rules=(rule,), errors=(err,))
    _wire(
        dw, monkeypatch,
        collection=collection,
        comments=[_local_verdict_comment("reviewer", "APPROVED")],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("design-reviewer",),
    )
    assert result.passed is False
    assert "--bypass-reviewer cannot help" in result.refusal_message
    assert "RESOLVED required set" in result.refusal_message


# ---- audit comment is NOT a verdict (verdict-distinctness) ------------


def test_override_audit_not_matched_by_gate_verdict_reader(dw, av) -> None:
    """The per-reviewer-override audit comment must NOT be counted by the gate's
    verdict reader — no verdict grammar, no verdict marker (DEC-050 Decision 4).
    """
    audit = dw._OverrideAudit(
        reviewer="design-reviewer",
        capability="ux-ui-design",
        state="a fresh CHANGES_REQUESTED (an active block)",
        block_comment_url="https://example.test/c/design-reviewer",
    )
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    body = dw._reviewer_override_audit_body(audit, "flaky false block", invoker)

    # No verdict marker.
    assert av.VERDICT_MARKER not in body
    # The first line is the idempotency stamp (an HTML comment), not a verdict.
    first_line = body.split("\n", 1)[0].strip()
    token, _path, _name = av.parse_verdict_line(first_line)
    assert token is None
    # The strict gate reader counts zero verdicts from this comment.
    comment = {
        "author": {"login": "alice"},
        "body": body,
        "createdAt": _FRESH_TS,
        "url": "https://example.test/audit",
    }
    verdicts = av.gate_verdicts(
        [comment],
        min_timestamp=_COMMIT_TS,
        local_reviewer_ok=lambda _n: True,
        remote_reviewer_ok=lambda _l: True,
    )
    assert verdicts == []


def test_override_audit_records_state_and_operator(dw) -> None:
    """The audit body records the operator (name + email), reason, overridden
    reviewer + provenance, state at override time, and block-comment link."""
    audit = dw._OverrideAudit(
        reviewer="design-reviewer",
        capability="ux-ui-design",
        state="a fresh CHANGES_REQUESTED (an active block)",
        block_comment_url="https://example.test/c/design-reviewer",
    )
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    body = dw._reviewer_override_audit_body(audit, "flaky false block", invoker)
    assert "alice" in body
    assert "alice@example.test" in body
    assert "flaky false block" in body
    assert "design-reviewer" in body
    assert "ux-ui-design" in body
    assert "a fresh CHANGES_REQUESTED" in body
    assert "https://example.test/c/design-reviewer" in body


# ---- state at override time (the three states) -----------------------


def test_state_none_when_no_verdict(dw) -> None:
    state, url = dw._describe_override_state(None, _COMMIT_TS)
    assert "none" in state
    assert url is None


def test_state_fresh_changes_requested(dw, av) -> None:
    v = av.Verdict(
        reviewer="design-reviewer", token=av.CHANGES_REQUESTED,
        path=av.PATH_LOCAL, body="", timestamp=_FRESH_TS, url="u1",
    )
    state, url = dw._describe_override_state(v, _COMMIT_TS)
    assert "fresh CHANGES_REQUESTED" in state
    assert url == "u1"


def test_state_stale_approved(dw, av) -> None:
    v = av.Verdict(
        reviewer="design-reviewer", token=av.APPROVED,
        path=av.PATH_LOCAL, body="", timestamp=_STALE_TS, url="u2",
    )
    state, url = dw._describe_override_state(v, _COMMIT_TS)
    assert "stale APPROVED" in state
    # A stale APPROVED is not a block, so no block-comment link.
    assert url is None


# ---- per-reviewer(+reason) idempotency stamp -------------------------


def test_stamp_differs_by_reviewer(dw) -> None:
    a = dw._reviewer_override_stamp("design-reviewer", "reason")
    b = dw._reviewer_override_stamp("backend-reviewer", "reason")
    assert a != b


def test_stamp_differs_by_reason(dw) -> None:
    a = dw._reviewer_override_stamp("design-reviewer", "reason one")
    b = dw._reviewer_override_stamp("design-reviewer", "reason two")
    assert a != b


def test_stamp_stable_for_same_reviewer_and_reason(dw) -> None:
    a = dw._reviewer_override_stamp("design-reviewer", "  reason  ")
    b = dw._reviewer_override_stamp("design-reviewer", "reason")
    # The reason is stripped before hashing, so surrounding whitespace is a
    # no-op — a re-run with cosmetically-different reason text still no-ops.
    assert a == b


def test_audit_idempotent_skip_when_stamp_present(dw, monkeypatch) -> None:
    """Re-running the identical override is a no-op: the stamp is already on the
    PR, so no new comment is posted."""
    audit = dw._OverrideAudit(
        reviewer="design-reviewer", capability=None,
        state="none (no verdict posted)", block_comment_url=None,
    )
    stamp = dw._reviewer_override_stamp("design-reviewer", "same reason")
    posted: list = []

    def fake_gh_run(args, config, **kwargs):
        if "comment" in args and "--body" in args:
            posted.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        # gh pr view --json comments → the stamp is already present.
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"comments": [{"body": f"{stamp}\n\nold audit"}]}),
            stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    ok = dw._post_reviewer_override_audit(7, audit, "same reason", invoker, {})
    assert ok is True
    assert posted == []  # no new comment.


def test_audit_posts_when_reason_differs(dw, monkeypatch) -> None:
    """A DIFFERENT reason carries a distinct stamp → a fresh audit posts even
    though a prior override audit for the same reviewer exists."""
    audit = dw._OverrideAudit(
        reviewer="design-reviewer", capability=None,
        state="none (no verdict posted)", block_comment_url=None,
    )
    old_stamp = dw._reviewer_override_stamp("design-reviewer", "old reason")
    posted: list = []

    def fake_gh_run(args, config, **kwargs):
        if "comment" in args and "--body" in args:
            posted.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"comments": [{"body": f"{old_stamp}\n\nold audit"}]}),
            stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    ok = dw._post_reviewer_override_audit(7, audit, "new reason", invoker, {})
    assert ok is True
    assert len(posted) == 1  # a fresh audit posted.


# ---- ephemeral: no persistence across a re-run without the flag ------


def test_override_ephemeral_not_persisted(dw, rc, monkeypatch) -> None:
    """The override does not persist: a later run WITHOUT --bypass-reviewer
    re-resolves and refuses on the still-blocked reviewer. The prior audit
    comment does NOT satisfy the gate (it is verdict-distinct)."""
    audit = dw._OverrideAudit(
        reviewer="design-reviewer",
        capability="ux-ui-design",
        state="a fresh CHANGES_REQUESTED (an active block)",
        block_comment_url="https://example.test/c/design-reviewer",
    )
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    prior_audit_body = dw._reviewer_override_audit_body(audit, "reason", invoker)
    prior_audit_comment = {
        "author": {"login": "alice"},
        "body": prior_audit_body,
        "createdAt": _FRESH_TS,
        "url": "https://example.test/audit",
    }
    _wire(
        dw, monkeypatch,
        collection=_design_collection(rc),
        comments=[
            _local_verdict_comment("reviewer", "APPROVED"),
            _local_verdict_comment("design-reviewer", "CHANGES_REQUESTED"),
            prior_audit_comment,  # last run's audit is still on the PR.
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    # Re-run WITHOUT the override flag.
    result = dw._check_agent_gate(99, {}, _config(), "resolved", CAP_ROOT)
    assert result.passed is False
    # The prior audit did not stand in for a fresh APPROVED.
    assert "design-reviewer" in result.refusal_message
