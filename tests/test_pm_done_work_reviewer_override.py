"""Tests for `done-work`'s per-reviewer override (project-management:DEC-050).

`--bypass-reviewer <name> --bypass-reviewer-reason "<r>"` satisfies ONE named
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
  * **one honest answer per slot** — the three surfaces that report the gate's
    decision (`passed_via`, the refusal listing, the audit comment) all read the
    single `_Slot` record, so a redundant override reads as redundant on every
    one of them and never as `satisfied-by-override`.
  * **audit fidelity** — the audit's state at override time comes from a read
    carrying the gate's own membership + author-exclusion filters, so a PR
    author's self-approval cannot describe what the override waived.
  * **DEC-049 format** — the audit renders the canonical `audit_comment_template`
    with the uniform `<!-- pkit-audit -->` marker rather than a bespoke body.

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


#: The real capability root, for the tests that assert the audit body renders
#: the canonical DEC-049 template out of the shipped schema.
REAL_CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"


def _slot(dw, name, *, label=None, approved=False, overridden=False, verdict=None):
    """A `_Slot` for the unit-level audit-builder tests."""
    return dw._Slot(
        reviewer=name,
        label=label or f"local agent ({name})",
        approved=approved,
        overridden=overridden,
        verdict=verdict,
    )


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


def test_redundant_override_on_approved_reviewer_labelled_approved(dw, rc, monkeypatch) -> None:
    """A reviewer with a genuine fresh APPROVED that is ALSO named in
    --bypass-reviewer is reported as APPROVED (the override was redundant), NOT
    satisfied-by-override — the honest label (DEC-050 W3). The gate passes
    either way."""
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
        override_reviewers=("design-reviewer",),
    )
    assert result.passed is True
    # A genuine APPROVED is reported as such even though the reviewer was named
    # in --bypass-reviewer — the override was redundant, not the reason it passed.
    assert "design-reviewer" in result.passed_via
    assert "satisfied-by-override" not in result.passed_via


# ---- one honest answer per slot (the three reporting surfaces) --------
#
# The gate DECISION was sound; the three surfaces that REPORT it each
# re-derived "was this slot overridden?" and disagreed. These pin all three to
# the single `_Slot` record, and are written per-surface on purpose: a
# regression in any one of them is the bug that shipped.


def test_redundant_override_refusal_reports_approved_not_override(dw, rc, monkeypatch) -> None:
    """The REFUSAL listing must report a genuine fresh APPROVED as APPROVED even
    when that reviewer was also named in `--bypass-reviewer`.

    This path tested `name in override_set` BEFORE the real verdict, so a reviewer
    with a marker-stamped fresh APPROVED printed `satisfied-by-override` — telling
    the operator review had been waived when it had not, while the PASS path (same
    state, different code) printed `APPROVED`. The gate still refuses here because
    a DIFFERENT required reviewer is unsatisfied."""
    _wire(
        dw, monkeypatch,
        collection=_design_collection(rc),
        comments=[
            # design-reviewer genuinely approved AND is named in the override;
            # the baseline reviewer has no verdict, so the gate refuses.
            _local_verdict_comment("design-reviewer", "APPROVED"),
        ],
        closing_issue_labels={42: ["workstream:design"]},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("design-reviewer",),
    )
    assert result.passed is False
    assert "design-reviewer" in result.refusal_message
    assert "satisfied-by-override" not in result.refusal_message, (
        "a real APPROVED must never be reported as a waiver"
    )
    assert "APPROVED" in result.refusal_message


def test_redundant_override_audit_records_redundancy(dw, rc, monkeypatch) -> None:
    """The AUDIT COMMENT must not assert a waiver that did not happen.

    It unconditionally appended "This reviewer's slot is satisfied-by-override
    …; every other required reviewer still gated" — contradicting its own state
    line two lines above ("a fresh APPROVED (override redundant)") on a redundant
    override. The comment is permanent; the claim has to be true."""
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
        override_reviewers=("design-reviewer",),
    )
    assert result.passed is True
    assert len(result.override_audits) == 1
    audit = result.override_audits[0]
    assert audit.redundant is True
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    body = dw._reviewer_override_audit_body(audit, "belt and braces", invoker)
    assert "REDUNDANT" in body
    assert "satisfied-by-override" not in body
    assert "a fresh APPROVED (override redundant)" in body


def test_all_slots_override_audit_does_not_claim_others_gated(dw, rc, monkeypatch) -> None:
    """With EVERY slot overridden, no other reviewer gated — so the audit must
    not claim one did.

    The all-slots nudge goes to stderr and evaporates; this comment stays on the
    PR forever, and it used to assert "every other required reviewer still
    gated" unconditionally."""
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
    assert len(result.override_audits) == 2
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    for audit in result.override_audits:
        body = dw._reviewer_override_audit_body(audit, "panel is broken", invoker)
        assert "still gated" not in body
        assert "Every required reviewer's slot was overridden" in body
        # And it steers to the honest whole-gate tool, like the stderr nudge.
        assert "--bypass" in body


def test_sole_reviewer_override_audit_says_whole_gate_waived(dw, rc, monkeypatch) -> None:
    """A single-reviewer set with that reviewer overridden waived the whole gate
    — say so, rather than claiming other reviewers gated."""
    _wire(
        dw, monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[_local_verdict_comment("reviewer", "CHANGES_REQUESTED")],
        closing_issue_labels={42: []},
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("reviewer",),
    )
    assert result.passed is True
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    body = dw._reviewer_override_audit_body(
        result.override_audits[0], "false block", invoker,
    )
    assert "ONLY required reviewer" in body
    assert "still gated" not in body


def test_partial_override_audit_names_the_reviewers_that_gated(dw, rc, monkeypatch) -> None:
    """The genuine case: one slot overridden, another genuinely APPROVED. The
    audit names who still gated, instead of asserting it abstractly."""
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
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    body = dw._reviewer_override_audit_body(
        result.override_audits[0], "false block", invoker,
    )
    assert "satisfied-by-override" in body
    assert "still gated it on a genuine APPROVED" in body
    assert "local agent (reviewer)" in body


# ---- audit fidelity: the gate's own filters, not a permissive read ----


def test_audit_ignores_the_pr_authors_self_approval(dw, rc, monkeypatch) -> None:
    """The audit's state at override time must be read with the gate's OWN
    membership + author-exclusion filters.

    The audit build called the permissive `latest_verdicts_per_reviewer` with an
    allow-all remote predicate, so the PR author's self-approval — which the gate
    correctly refuses to count (DEC-028 step 3) — drove the record: it said
    "a fresh APPROVED (override redundant)" when the override was the ONLY thing
    that let the merge through. ADR-042 names calling the permissive primitive
    from a gate path as the anti-pattern."""
    _wire(
        dw, monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[
            # The PR author self-approves on the remote path.
            _remote_verdict_comment("self-approver", "APPROVED"),
        ],
        closing_issue_labels={42: []},
        pr_author="self-approver",
    )
    result = dw._check_agent_gate(
        99, {}, _config(local=(), remote=("self-approver",)), "resolved", CAP_ROOT,
        override_reviewers=("self-approver",),
    )
    # The override is what let it through — the self-approval never counted.
    assert result.passed is True
    assert "satisfied-by-override" in result.passed_via
    audit = result.override_audits[0]
    assert audit.redundant is False
    assert "override redundant" not in audit.state, (
        "the author's own self-approval must not describe the overridden state"
    )
    assert "none" in audit.state


# ---- one audit per waiver, however many times the flag names it -------


def test_duplicate_bypass_reviewer_flag_audits_once(dw, rc, monkeypatch) -> None:
    """`--bypass-reviewer X --bypass-reviewer X` posts ONE audit.

    The audit build iterated the raw flag tuple, so a repeated name yielded two
    records — and under GitHub's read-after-write window the second fetch missed
    the first comment and posted again. Slots are one per required reviewer, so
    the de-duplication the gate always had now covers the audit path too."""
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
        override_reviewers=("design-reviewer", "design-reviewer"),
    )
    assert result.passed is True
    assert [a.reviewer for a in result.override_audits] == ["design-reviewer"]
    # The all-slots nudge must not fire either — one of two slots is overridden.
    assert result.warnings == []


# ---- the all-slots nudge survives a later refusal --------------------


def test_all_slots_nudge_survives_a_gh_failure(dw, rc, monkeypatch) -> None:
    """A transient `gh` failure must not swallow the all-slots steer.

    The nudge was computed before the verdict fetch and attached to only 2 of the
    5 returns, so three refusal paths dropped it."""
    _wire(
        dw, monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[],
        closing_issue_labels={42: []},
    )
    real_gh_run = dw.gh_run

    def failing_gh_run(args, config, **kwargs):
        joined = " ".join(args)
        if "author,comments,commits" in joined:
            return subprocess.CompletedProcess(
                args=args, returncode=1, stdout="", stderr="boom",
            )
        return real_gh_run(args, config, **kwargs)

    monkeypatch.setattr(dw, "gh_run", failing_gh_run)
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("reviewer",),
    )
    assert result.passed is False
    assert "gh pr view failed" in result.refusal_message
    assert any("covers EVERY required reviewer" in w for w in result.warnings)


def test_all_slots_nudge_survives_an_unresolvable_freshness_anchor(dw, rc, monkeypatch) -> None:
    """Same for the freshness-anchor refusal (no commits ⇒ no anchor)."""
    _wire(
        dw, monkeypatch,
        collection=rc.ContributionCollection(rules=()),
        comments=[],
        closing_issue_labels={42: []},
        commits=[],
    )
    result = dw._check_agent_gate(
        99, {}, _config(), "resolved", CAP_ROOT,
        override_reviewers=("reviewer",),
    )
    assert result.passed is False
    assert "freshness anchor is unknown" in result.refusal_message
    assert any("covers EVERY required reviewer" in w for w in result.warnings)


# ---- DEC-049: the ONE canonical audit format -------------------------


def test_audit_body_renders_the_canonical_dec049_template(dw) -> None:
    """The audit's headline is the canonical DEC-049 line, from the schema.

    The writer emitted a bespoke `<!-- pkit-hook: … -->` marker and a hand-rolled
    `Per-reviewer override by …` line, where DEC-049 fixes ONE format sourced from
    `validation-severity.yaml`'s `audit_comment_template` behind a uniform
    `<!-- pkit-audit -->` marker. The per-reviewer detail is additive prose BELOW
    that line — the template has no fields for it."""
    from _lib import audit as audit_lib

    audit = dw._OverrideAudit(
        reviewer="design-reviewer", capability="ux-ui-design",
        state="a fresh CHANGES_REQUESTED (an active block)",
        block_comment_url="https://example.test/block", head="sha1",
    )
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    body = dw._reviewer_override_audit_body(
        audit, "flaky false block", invoker, REAL_CAP_ROOT,
    )
    lines = body.split("\n")
    # The canonical marker, first, from the schema template.
    assert lines[0] == audit_lib.AUDIT_MARKER
    assert lines[1] == "Bypassed by alice <alice@example.test>: flaky false block"
    # Rendered from the shipped schema, not a hardcoded string.
    assert audit_lib.load_audit_template(REAL_CAP_ROOT).startswith(
        audit_lib.AUDIT_MARKER
    )
    # The per-reviewer detail DEC-050 requires is still all there.
    assert "design-reviewer" in body
    assert "ux-ui-design" in body
    assert "a fresh CHANGES_REQUESTED" in body
    assert "https://example.test/block" in body


def test_audit_body_is_one_comment_per_marker(dw) -> None:
    """Exactly one `<!-- pkit-audit -->` per audit comment (DEC-049)."""
    from _lib import audit as audit_lib

    audit = dw._OverrideAudit(
        reviewer="design-reviewer", capability=None,
        state="none (no verdict the gate counts)", block_comment_url=None,
        head="sha1",
    )
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    body = dw._reviewer_override_audit_body(audit, "r", invoker, REAL_CAP_ROOT)
    assert body.count(audit_lib.AUDIT_MARKER) == 1


# ---- one fetch for N audits (cost) -----------------------------------


def test_threaded_comment_list_costs_no_extra_fetch(dw, monkeypatch) -> None:
    """Threading an already-fetched comment list in means N audits cost ONE
    fetch, not one `gh pr view` each."""
    fetches: list = []
    posts: list = []

    def fake_gh_run(args, config, **kwargs):
        if "comment" in args and "--body" in args:
            posts.append(args)
        else:
            fetches.append(args)
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout=json.dumps({"comments": []}), stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    comments = dw._fetch_subject_comments("pr", 7, {})
    assert len(fetches) == 1
    for name in ("a-reviewer", "b-reviewer", "c-reviewer"):
        audit = dw._OverrideAudit(
            reviewer=name, capability=None, state="none (no verdict the gate counts)",
            block_comment_url=None, head="sha1",
        )
        assert dw._post_reviewer_override_audit(
            7, audit, "r", invoker, {}, comments=comments,
        ) is True
    assert len(posts) == 3
    assert len(fetches) == 1, "three audits, one comment fetch"


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
    # The first line is the DEC-049 audit marker (an HTML comment), not a verdict.
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


# ---- worst-state-wins across paths (audit fidelity) ------------------


def _remote_verdict_comment(login, verdict, ts=_FRESH_TS, url=None):
    return {
        "author": {"login": login},
        "body": f"Reviewer agent: {verdict}\n\nbody.\n\n{_VERDICT_MARKER}",
        "createdAt": ts,
        "url": url or f"https://example.test/c/{login}",
    }


def _build_audits(dw, slots, comments, *, contributed_by=None, head="head0",
                  ok=lambda _n: True):
    """`_build_override_audits` with the gate-strength predicates every caller
    must inject (the membership + author-exclusion filters)."""
    return dw._build_override_audits(
        slots=slots,
        comments=comments,
        latest_commit_ts=_COMMIT_TS,
        head=head,
        contributed_by=contributed_by or {},
        remote_reviewer_ok=ok,
        local_reviewer_ok=ok,
    )


def test_build_override_audits_dual_path_prefers_most_blocking(dw) -> None:
    """A reviewer that posted on BOTH paths — a stale local APPROVED and a fresh
    remote CHANGES_REQUESTED — must be audited by the most-blocking state, so the
    audit faithfully records the active block and keeps its link, rather than the
    stale APPROVED that sorts first (DEC-050 G2). The local verdict is listed
    first to prove the choice is severity-based, not order-based."""
    audits = _build_audits(
        dw,
        [_slot(dw, "dual-reviewer", overridden=True)],
        [
            _local_verdict_comment("dual-reviewer", "APPROVED", ts=_STALE_TS),
            _remote_verdict_comment(
                "dual-reviewer", "CHANGES_REQUESTED", ts=_FRESH_TS,
                url="https://example.test/block",
            ),
        ],
    )
    assert len(audits) == 1
    assert "fresh CHANGES_REQUESTED" in audits[0].state
    assert audits[0].block_comment_url == "https://example.test/block"


def test_no_override_builds_no_audits_and_reparses_nothing(dw) -> None:
    """With no slot overridden the builder returns immediately — the ordinary
    merge pays no comment re-parse (it used to run a full one regardless)."""
    reparsed: list = []

    class _Tripwire(list):
        def __iter__(self):
            reparsed.append(True)
            return super().__iter__()

    audits = _build_audits(
        dw,
        [_slot(dw, "reviewer", approved=True)],
        _Tripwire([_local_verdict_comment("reviewer", "APPROVED")]),
    )
    assert audits == []
    assert reparsed == [], "no override supplied → the comments are never walked"


# ---- per-reviewer(+reason) idempotency stamp -------------------------


def test_stamp_differs_by_reviewer(dw) -> None:
    a = dw._reviewer_override_stamp("design-reviewer", "reason", "head1")
    b = dw._reviewer_override_stamp("backend-reviewer", "reason", "head1")
    assert a != b


def test_stamp_differs_by_reason(dw) -> None:
    a = dw._reviewer_override_stamp("design-reviewer", "reason one", "head1")
    b = dw._reviewer_override_stamp("design-reviewer", "reason two", "head1")
    assert a != b


def test_stamp_differs_by_head(dw) -> None:
    """New commits ⇒ a new stamp, so a re-run RE-AUDITS against the current
    state instead of reusing a record computed against a HEAD that no longer
    exists. The override is scoped to the current HEAD (DEC-050 Decision 3);
    keying only on name+reason let a run recording "none" be reused after the
    reviewer had posted a CHANGES_REQUESTED — an audit denying the block it
    waived, with no link to it."""
    a = dw._reviewer_override_stamp("design-reviewer", "reason", "sha-old")
    b = dw._reviewer_override_stamp("design-reviewer", "reason", "sha-new")
    assert a != b


def test_stamp_stable_for_same_reviewer_reason_and_head(dw) -> None:
    a = dw._reviewer_override_stamp("design-reviewer", "  reason  ", "head1")
    b = dw._reviewer_override_stamp(" design-reviewer ", "reason", "head1")
    # Name and reason are stripped before hashing, so surrounding whitespace is
    # a no-op — a re-run with cosmetically-different text still no-ops.
    assert a == b


def test_stamp_survives_a_comment_closer_in_the_reviewer_name(dw) -> None:
    """A reviewer name containing `-->` must not break the marker.

    The name comes from adopter config, and the stamp is an HTML comment: an
    interpolated `-->` closed it early, so the marker never matched again and
    every re-run reposted. Hashing the name makes the marker well-formed by
    construction — and still distinguishes the two names."""
    evil = "design-reviewer --> <!-- injected"
    stamp = dw._reviewer_override_stamp(evil, "reason", "head1")
    assert stamp.startswith("<!--")
    assert stamp.endswith("-->")
    # Exactly one comment closer: the marker's own.
    assert stamp.count("-->") == 1
    assert stamp != dw._reviewer_override_stamp("design-reviewer", "reason", "head1")


def test_stamp_scan_matches_a_posted_evil_name_stamp(dw, monkeypatch) -> None:
    """End-to-end on the pathological name: the stamp the poster writes is the
    stamp its own idempotency scan finds, so the re-run is a no-op."""
    audit = dw._OverrideAudit(
        reviewer="design-reviewer --> <!-- injected", capability=None,
        state="none (no verdict the gate counts)", block_comment_url=None,
        head="head1",
    )
    posted: list = []

    def fake_gh_run(args, config, **kwargs):
        if "comment" in args and "--body" in args:
            posted.append(args[args.index("--body") + 1])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"comments": [{"body": b} for b in posted]}),
            stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    assert dw._post_reviewer_override_audit(7, audit, "r", invoker, {}) is True
    assert len(posted) == 1
    # The second run finds its own stamp in the first run's body.
    assert dw._post_reviewer_override_audit(7, audit, "r", invoker, {}) is True
    assert len(posted) == 1


def test_audit_idempotent_skip_when_stamp_present(dw, monkeypatch) -> None:
    """Re-running the identical override is a no-op: the stamp is already on the
    PR, so no new comment is posted."""
    audit = dw._OverrideAudit(
        reviewer="design-reviewer", capability=None,
        state="none (no verdict the gate counts)", block_comment_url=None,
        head="head1",
    )
    stamp = dw._reviewer_override_stamp("design-reviewer", "same reason", "head1")
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
        state="none (no verdict the gate counts)", block_comment_url=None,
        head="head1",
    )
    old_stamp = dw._reviewer_override_stamp("design-reviewer", "old reason", "head1")
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


def test_audit_reposts_after_new_commits(dw, monkeypatch) -> None:
    """A re-run of the SAME override after new commits posts a FRESH audit.

    The stamp is keyed to HEAD (DEC-050 Decision 3), so the earlier record — made
    against a HEAD that no longer exists, and carrying the state as of THEN — is
    not reused. Keyed on name+reason alone, a run recording "none" was reused
    after the reviewer posted a CHANGES_REQUESTED: the merge landed with an audit
    denying the block it waived, and no link to it."""
    old_audit = dw._OverrideAudit(
        reviewer="design-reviewer", capability=None,
        state="none (no verdict the gate counts)", block_comment_url=None,
        head="sha-old",
    )
    new_audit = dw._OverrideAudit(
        reviewer="design-reviewer", capability=None,
        state="a fresh CHANGES_REQUESTED (an active block)",
        block_comment_url="https://example.test/block", head="sha-new",
    )
    invoker = dw.Identity(github_login="alice", email="alice@example.test")
    prior_body = dw._reviewer_override_audit_body(old_audit, "same reason", invoker)
    posted: list = []

    def fake_gh_run(args, config, **kwargs):
        if "comment" in args and "--body" in args:
            posted.append(args[args.index("--body") + 1])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"comments": [{"body": prior_body}]}), stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    ok = dw._post_reviewer_override_audit(7, new_audit, "same reason", invoker, {})
    assert ok is True
    assert len(posted) == 1, "new HEAD ⇒ a fresh audit, not a stale-record reuse"
    # And the fresh audit carries the CURRENT state, with the block link.
    assert "a fresh CHANGES_REQUESTED" in posted[0]
    assert "https://example.test/block" in posted[0]


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
