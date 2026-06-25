"""adopt-existing — the brownfield onboarding ceremony (DEC-037 §1).

`adopt-existing.py` inventories a live tracker through `gh` READS only, infers +
DRAFTS a candidate `substrate-map.yaml`, and prints an audit report showing the
EVIDENCE for each inferred binding. The load-bearing invariant is that it
**mutates nothing** — it never writes the live map, never edits a
label/field/issue, never installs anything.

These tests pin the contract this ceremony owns:

  * inventory parsing — from sample `gh` JSON outputs (labels + usage, title
    prefixes, open/closed counts, blocked-label convention, milestones, board
    fields);
  * inference correctness — a known corpus shape → the expected draft bindings,
    each carrying the audit EVIDENCE it was inferred from (DEC-037 §1);
  * schema validity — the drafted map validates against substrate-map.schema.json
    (and an invalid draft is reported, not silently emitted);
  * the MUTATE-NOTHING invariant — end-to-end, only READ `gh` calls are ever
    issued (no `create`/`edit`/`item-edit`/`item-add`/label mutation/graphql
    mutation), mirroring back-fill's no-write test but for the whole ceremony;
  * the live-map write guard — `--out` pointed at the live substrate-map path is
    refused.

The `gh` reads are stubbed at `gh_run` (and at the `_lib.gh` source module for
the end-to-end mutate-nothing proof, so a write through any binding is caught).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAP_ROOT / "scripts"
LIB_DIR = SCRIPTS_DIR / "_lib"
SCRIPT = SCRIPTS_DIR / "adopt-existing.py"
SUBSTRATE_MAP_SCHEMA = CAP_ROOT / "schemas" / "substrate-map.schema.json"


@pytest.fixture(scope="module")
def ae():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_adopt_existing_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_adopt_existing_under_test"] = module
    spec.loader.exec_module(module)
    yield module


@pytest.fixture(scope="module")
def schema_validator() -> Draft202012Validator:
    schema = json.loads(SUBSTRATE_MAP_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


# ----- sample gh outputs (the AUJ-shaped corpus + a richer one) ----------

# AUJ shape: native P0/P1/P2 priority labels, [Task]/[Epic] title prefixes, a
# `Blocked` label, no workstream labels, no board.
AUJ_LABELS = ["P0", "P1", "P2", "Blocked", "bug", "documentation"]
AUJ_ISSUES = [
    {"number": 1, "title": "[Task] do the thing", "state": "OPEN",
     "labels": [{"name": "P0"}], "milestone": {"title": "Sprint 1"}},
    {"number": 2, "title": "[Epic] big initiative", "state": "OPEN",
     "labels": [{"name": "P1"}, {"name": "Blocked"}], "milestone": None},
    {"number": 3, "title": "[Task] another", "state": "CLOSED",
     "labels": [{"name": "P2"}], "milestone": {"title": "Sprint 1"}},
    {"number": 4, "title": "no prefix here", "state": "CLOSED",
     "labels": [], "milestone": None},
]


def _config() -> dict:
    return {"gh": {"default_owner": "ai-platform-incubation"}}


def _serve_auj_reads(args, config=None, **_kw):
    """A fake gh_run serving the AUJ-shaped reads; mutating calls raise loudly."""
    if args[:3] == ["gh", "label", "list"]:
        return subprocess.CompletedProcess(
            args, 0, json.dumps([{"name": n} for n in AUJ_LABELS]), "")
    if args[:3] == ["gh", "issue", "list"]:
        return subprocess.CompletedProcess(args, 0, json.dumps(AUJ_ISSUES), "")
    if args[:3] == ["gh", "repo", "view"]:
        return subprocess.CompletedProcess(
            args, 0, json.dumps({"nameWithOwner": "ai-platform-incubation/spyre"}), "")
    # No board configured in _config(), so field-list should never be reached.
    return subprocess.CompletedProcess(args, 0, "{}", "")


# ===== inventory parsing =================================================


def test_inventory_parses_labels_with_per_issue_usage(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    assert inv.read_ok
    usage = {o.name: o.issue_usage for o in inv.labels}
    # P0 on #1, P1 on #2, P2 on #3, Blocked on #2.
    assert usage["P0"] == 1
    assert usage["P1"] == 1
    assert usage["Blocked"] == 1
    assert usage["bug"] == 0  # present on the repo, on no sampled issue


def test_inventory_parses_title_prefixes_with_frequency(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    counts = {o.prefix: o.count for o in inv.title_prefixes}
    assert counts == {"Task": 2, "Epic": 1}  # the no-prefix issue contributes none


def test_inventory_counts_open_closed_and_blocked_label(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    assert inv.open_count == 2
    assert inv.closed_count == 2
    assert inv.has_blocked_label is True


def test_inventory_collects_milestones_in_use(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    assert inv.milestones_in_use == ["Sprint 1"]


def test_inventory_truncation_flagged_when_sample_fills_limit(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=4)  # exactly the 4 AUJ issues
    assert inv.sample_truncated is True
    inv2 = ae.take_inventory(_config(), sample_limit=200)
    assert inv2.sample_truncated is False


def test_inventory_read_ok_false_when_both_reads_fail(ae, monkeypatch) -> None:
    def fail(args, config=None, **kw):
        return subprocess.CompletedProcess(args, 1, "", "boom")
    monkeypatch.setattr(ae, "gh_run", fail)
    inv = ae.take_inventory(_config(), sample_limit=200)
    assert inv.read_ok is False


def test_inventory_board_fields_read_when_board_configured(ae, monkeypatch) -> None:
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([{"name": "P0"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps(AUJ_ISSUES), "")
        if args[:3] == ["gh", "project", "field-list"]:
            return subprocess.CompletedProcess(
                args, 0,
                json.dumps({"fields": [
                    {"name": "Workstream", "options": [{"name": "Spyre"}]},
                    {"name": "Status"},
                ]}), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    config = {"has_projects_v2_board": True, "projects_v2_board_id": 7,
              "gh": {"default_owner": "ai-platform-incubation"}}
    inv = ae.take_inventory(config, sample_limit=200)
    assert inv.has_board is True
    names = [f["name"] for f in inv.board_fields]
    assert "Workstream" in names


# ===== inference correctness (known corpus shape → expected bindings) =====


def test_priority_inferred_as_label_remap_with_evidence(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    pri = next(i for i in draft.inferences if i.axis == "priority")
    assert pri.binding == {"label": {"remap": {"High": "P0", "Medium": "P1", "Low": "P2"}},
                           "default": "P1"}
    # the EVIDENCE cites the observed labels + usage (DEC-037 §1).
    assert "P0" in pri.evidence and "P1" in pri.evidence and "P2" in pri.evidence
    # G1: tier ORDERING is assumed, not detected — even a full P0/P1/P2 sweep is
    # ordering-unverified, so confidence is NEVER `high` (capped at `low`), and the
    # evidence flags the direction as assumed so the human can catch an inversion.
    assert pri.confidence == "low"
    assert "ORDERING ASSUMED" in pri.evidence
    assert "all three tiers observed" in pri.evidence  # coverage still reported


def test_type_inferred_as_title_prefix_with_evidence(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    typ = next(i for i in draft.inferences if i.axis == "type")
    assert typ.binding == {"title-prefix": {"remap": {"task": "[Task]", "epic": "[Epic]"}}}
    assert "[Task]" in typ.evidence and "[Epic]" in typ.evidence


def test_state_inferred_as_derive_blocked_arm_live_when_label_observed(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    state = next(i for i in draft.inferences if i.axis == "state")
    assert state.binding["derive"]["from"] == "open-closed"
    assert set(state.binding["derive"]["states"]) == {"open", "blocked", "done"}
    assert "WAS observed" in state.evidence  # the Blocked label was observed → arm is live


def test_state_derive_warns_when_no_blocked_label(ae, monkeypatch) -> None:
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(
                args, 0, json.dumps([{"name": "P0"}]), "")  # no Blocked label
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps(AUJ_ISSUES), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    state = next(i for i in draft.inferences if i.axis == "state")
    # The state binding is still drafted, but the evidence warns the blocked arm
    # will never fire (and the inventory did not observe a Blocked label).
    assert inv.has_blocked_label is False
    assert "never fire" in state.evidence
    assert state.confidence == "low"


def test_workstream_unsupported_when_no_workstream_labels(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    ws = next(i for i in draft.inferences if i.axis == "workstream")
    assert ws.binding is None  # omitted ≡ unsupported
    assert "UNSUPPORTED" in ws.evidence


def test_workstream_inferred_as_label_remap_when_workstream_labels_present(ae, monkeypatch) -> None:
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                json.dumps([{"name": "workstream:spyre"}, {"name": "workstream:core"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    ws = next(i for i in draft.inferences if i.axis == "workstream")
    assert ws.binding == {"label": {"remap": {"spyre": "workstream:spyre",
                                              "core": "workstream:core"}}}


def test_priority_unsupported_when_no_priority_labels(ae, monkeypatch) -> None:
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([{"name": "bug"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    pri = next(i for i in draft.inferences if i.axis == "priority")
    assert pri.binding is None
    assert pri.confidence == "none"


def test_partial_priority_tiers_flagged_low_confidence(ae, monkeypatch) -> None:
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(
                args, 0, json.dumps([{"name": "P0"}, {"name": "P1"}]), "")  # no P2
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    pri = next(i for i in draft.inferences if i.axis == "priority")
    assert pri.binding["label"]["remap"] == {"High": "P0", "Medium": "P1"}
    assert pri.confidence == "low"
    assert "PARTIAL" in pri.evidence


def test_priority_ordering_flagged_as_assumed_not_high_confidence(ae, monkeypatch) -> None:
    """G1 — an inverted-priority corpus (P0=lowest urgency by the adopter's
    convention) is INDISTINGUISHABLE from the labels alone. The remap is drawn in
    the conventional P0=High direction, but the audit must (a) flag the ordering as
    ASSUMED (so the human can catch the inversion) and (b) NOT stamp `high`
    confidence — ordering is unverifiable from labels alone (mirrors `_infer_
    hierarchy`'s honest hedge for the same epistemic situation)."""
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            # A full P0/P1/P2 sweep — usage counts say nothing about urgency order.
            return subprocess.CompletedProcess(
                args, 0, json.dumps([{"name": "P0"}, {"name": "P1"}, {"name": "P2"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    pri = next(i for i in draft.inferences if i.axis == "priority")
    # The remap is still drawn (conventional direction) — but never at `high`.
    assert pri.binding["label"]["remap"] == {"High": "P0", "Medium": "P1", "Low": "P2"}
    assert pri.confidence != "high"
    assert pri.confidence == "low"
    # The evidence must explicitly say the ordering is assumed and ask the human to
    # confirm the direction — the hook the inverted-convention adopter needs.
    assert "ORDERING ASSUMED" in pri.evidence
    assert "NOT DETECTED" in pri.evidence
    assert "inverted" in pri.evidence.lower()
    assert "confirm the direction" in pri.evidence.lower()


def test_priority_unsupported_echoes_unrecognised_priorityish_labels(ae, monkeypatch) -> None:
    """G2 — a repo using `priority/high` / `severity:1` (shapes the matcher doesn't
    recognise) drafts UNSUPPORTED, but the evidence must ECHO the observed-but-
    unmatched priority-ish labels so the human can tell "no priority axis" from
    "the matcher didn't know my shape."""
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                json.dumps([{"name": "priority/high"}, {"name": "severity:1"},
                            {"name": "bug"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    pri = next(i for i in draft.inferences if i.axis == "priority")
    assert pri.binding is None  # unrecognised shapes don't match → unsupported
    assert "priority/high" in pri.evidence
    assert "severity:1" in pri.evidence
    assert "bug" not in pri.evidence  # not priority-ish → not echoed


def test_workstream_unsupported_echoes_unrecognised_grouping_labels(ae, monkeypatch) -> None:
    """G3 — a repo grouping by `area:`/`team:`/`component:` (not the kit
    `workstream:` prefix) drafts workstream UNSUPPORTED, but the evidence must ECHO
    those grouping-ish labels so the human sees them surfaced."""
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                json.dumps([{"name": "area:billing"}, {"name": "team:platform"},
                            {"name": "bug"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    ws = next(i for i in draft.inferences if i.axis == "workstream")
    assert ws.binding is None
    assert "area:billing" in ws.evidence
    assert "team:platform" in ws.evidence
    assert "bug" not in ws.evidence


def test_type_low_coverage_prefix_is_low_confidence(ae, monkeypatch) -> None:
    """G7 — a coincidental bracket prefix carried by a tiny fraction of issues
    (e.g. one `[Feature]` changelog marker among many plain titles) must read `low`
    confidence with an evidence note that it may be coincidental, NOT a `high`-
    confidence type taxonomy. Mirrors priority's coverage-driven confidence."""
    issues = [{"number": 1, "title": "[Feature] changelog note", "state": "OPEN",
               "labels": [], "milestone": None}]
    # 19 plain-title issues → only 1/20 carries a mapped prefix (5% < 10%).
    issues += [{"number": n, "title": f"plain title {n}", "state": "OPEN",
                "labels": [], "milestone": None} for n in range(2, 21)]

    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([{"name": "bug"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps(issues), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    typ = next(i for i in draft.inferences if i.axis == "type")
    assert typ.binding == {"title-prefix": {"remap": {"feature": "[Feature]"}}}
    assert typ.confidence == "low"
    assert "LOW COVERAGE" in typ.evidence
    assert "coincidental" in typ.evidence.lower()


def test_type_high_coverage_prefix_stays_high_confidence(ae, monkeypatch) -> None:
    """G7 sibling — when most sampled issues carry a mapped prefix, type stays
    `high` (the coverage modulation doesn't downgrade a genuine taxonomy)."""
    issues = [{"number": n, "title": "[Task] real work", "state": "OPEN",
               "labels": [], "milestone": None} for n in range(1, 11)]

    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([{"name": "bug"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps(issues), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    typ = next(i for i in draft.inferences if i.axis == "type")
    assert typ.confidence == "high"
    assert "10/10" in typ.evidence


def test_label_read_truncation_flagged_when_label_count_fills_limit(ae, monkeypatch) -> None:
    """G6 — `_read_labels` requests `LABELS_LIMIT` labels; when the read fills that
    cap the inventory flags `labels_truncated` (the same `== limit` honesty the
    issue sample uses), so a partial label read isn't reported as the whole set."""
    full = [{"name": f"label-{i}"} for i in range(ae.LABELS_LIMIT)]

    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps(full), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    assert inv.labels_truncated is True
    # A sub-cap read is NOT flagged truncated.
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv2 = ae.take_inventory(_config(), sample_limit=200)
    assert inv2.labels_truncated is False


def test_evaluated_rejected_axes_emit_explicit_unsupported(ae, monkeypatch, schema_validator) -> None:
    """G5 — an axis evaluated-and-rejected lands as an explicit `unsupported: true`
    in the drafted map (not omitted), so the committed artifact self-documents
    "considered and rejected" vs "never looked". Still schema-valid."""
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([{"name": "bug"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                json.dumps([{"number": 1, "title": "plain title", "state": "OPEN",
                             "labels": [], "milestone": None}]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft_map = ae.infer_draft(inv).substrate_map()
    # priority/type/workstream evaluated-and-rejected → explicit unsupported.
    assert draft_map["axes"]["priority"] == {"unsupported": True}
    assert draft_map["axes"]["type"] == {"unsupported": True}
    assert draft_map["axes"]["workstream"] == {"unsupported": True}
    # state always binds (open/closed is universal).
    assert "derive" in draft_map["axes"]["state"]
    # Still schema-valid (the `unsupported: true` oneOf branch).
    assert [e.message for e in schema_validator.iter_errors(draft_map)] == []


def test_hierarchy_drafted_advisory_with_explicit_evidence(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft = ae.infer_draft(inv)
    assert draft.hierarchy == "advisory"
    assert "cannot positively detect" in draft.hierarchy_evidence


# ===== schema validity of the drafted map ================================


def test_drafted_map_validates_against_schema(ae, monkeypatch, schema_validator) -> None:
    """The AUJ-shaped draft validates clean against substrate-map.schema.json."""
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft_map = ae.infer_draft(inv).substrate_map()
    errors = [e.message for e in schema_validator.iter_errors(draft_map)]
    assert errors == [], f"drafted map failed schema validation: {errors}"


def test_self_check_reports_valid_for_the_auj_draft(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft_map = ae.infer_draft(inv).substrate_map()
    check = ae.validate_draft(draft_map, CAP_ROOT)
    assert check.ran is True
    assert check.valid is True
    assert check.errors == []


def test_self_check_surfaces_an_invalid_draft(ae) -> None:
    """If a draft would fail validation, the self-check reports it (not silent)."""
    bad = {"schema_version": 1, "axes": {"priority": {"label": {}}}}  # remap required
    check = ae.validate_draft(bad, CAP_ROOT)
    assert check.ran is True
    assert check.valid is False
    assert check.errors


def test_all_unsupported_draft_is_valid_and_marks_axes_unsupported(ae, monkeypatch, schema_validator) -> None:
    """An all-unsupported brownfield outcome (nothing fit) is a VALID draft. Per G5
    the rejected axes are written EXPLICITLY as `unsupported: true` (self-
    documenting) rather than omitted; state always derives. Schema-valid either
    way (DEC-036 absent ≡ unsupported, made explicit)."""
    def serve(args, config=None, **kw):
        if args[:3] == ["gh", "label", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([{"name": "bug"}]), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                json.dumps([{"number": 1, "title": "plain title", "state": "OPEN",
                             "labels": [], "milestone": None}]), "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(ae, "gh_run", serve)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft_map = ae.infer_draft(inv).substrate_map()
    # All four axes present: priority/type/workstream explicit-unsupported, state derives.
    assert set(draft_map["axes"]) == {"priority", "type", "workstream", "state"}
    assert draft_map["axes"]["priority"] == {"unsupported": True}
    assert [e.message for e in schema_validator.iter_errors(draft_map)] == []


# ===== draft emission =====================================================


def test_render_draft_yaml_marks_it_a_draft_and_round_trips(ae, monkeypatch) -> None:
    monkeypatch.setattr(ae, "gh_run", _serve_auj_reads)
    inv = ae.take_inventory(_config(), sample_limit=200)
    draft_map = ae.infer_draft(inv).substrate_map()
    text = ae.render_draft_yaml(draft_map)
    assert "DRAFT" in text
    assert "wrote NOTHING" in text
    # The YAML body round-trips back to the same document (ignoring the comment).
    loaded = YAML(typ="safe").load(text)
    assert loaded["axes"]["priority"]["label"]["remap"]["High"] == "P0"


# ===== the live-map write guard ==========================================


def test_out_refuses_the_live_substrate_map_path(ae, tmp_path, monkeypatch, capsys) -> None:
    """`--out` pointed at the live substrate-map path is refused (exit 2) — the
    ceremony NEVER writes the live map (DEC-037 §1)."""
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True)
    (cap / "schemas").mkdir(parents=True)
    live = cap / "project" / "substrate-map.yaml"
    monkeypatch.setattr(ae, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        sys, "argv",
        ["adopt-existing.py", "--capability-root", str(cap), "--out", str(live)],
    )
    rc = ae.main()
    assert rc == 2
    assert "LIVE substrate-map" in capsys.readouterr().err
    assert not live.exists()  # nothing written


def test_main_refuses_exit_2_when_inventory_unreadable(ae, tmp_path, monkeypatch, capsys) -> None:
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap.mkdir(parents=True)
    monkeypatch.setattr(ae, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        ae, "gh_run",
        lambda args, config=None, **kw: subprocess.CompletedProcess(args, 1, "", "boom"),
    )
    monkeypatch.setattr(sys, "argv", ["adopt-existing.py", "--capability-root", str(cap)])
    rc = ae.main()
    assert rc == 2
    assert "nothing to infer" in capsys.readouterr().err


# ===== the MUTATE-NOTHING invariant (the load-bearing proof) =============


def _is_mutating_call(call: list[str]) -> bool:
    """Recognise a MUTATING gh call (mirrors back-fill's no-write detector).

    Covers the `gh` subcommand mutations (item-edit/item-add/issue edit/create/
    comment/label create/edit/delete) AND a graphql MUTATION (a read `query(...)`
    is fine; any mutation keyword makes it a write).

    Widened (C2) to also flag the OTHER substrates DEC-037 §3 names — milestone
    writes (a `gh ... --milestone` write, a `gh api .../milestones -X POST`) and
    `gh issue develop`/`transfer`/`pin` — so a future regression introducing one of
    those (not just the originally-covered label/field/graphql writes) is caught."""
    joined = " ".join(call)
    subcommand_mutations = [
        "item-edit", "item-add",
        "issue edit", "issue create", "issue comment", "issue close",
        "issue develop", "issue transfer", "issue pin", "issue unpin",
        "label create", "label edit", "label delete",
        "project create", "project field-create",
    ]
    if any(m in joined for m in subcommand_mutations):
        return True
    # A `--milestone` write (assign/clear a milestone on an issue or via api edit).
    if "--milestone" in call:
        return True
    if call[:2] == ["gh", "api"]:
        body = joined.lower()
        # A milestones-collection write: POST/PATCH/DELETE/PUT against .../milestones.
        if "milestones" in body and any(
            f"-x {verb}" in body for verb in ("post", "patch", "delete", "put")
        ):
            return True
    if call[:3] == ["gh", "api", "graphql"]:
        body = joined.lower()
        mutation_markers = ("mutation", "updateprojectv2", "additem", "createissue")
        return any(marker in body for marker in mutation_markers)
    return False


def test_no_mutating_gh_call_is_ever_issued(ae, tmp_path, monkeypatch, capsys) -> None:
    """The hard boundary (DEC-037 §1): running the WHOLE ceremony end-to-end issues
    only READ gh calls — never a mutating one. Caught at the `_lib.gh` source module
    both adopt-existing and any write path would import from, so a write through any
    binding would be captured (mirroring back-fill's seam-level catch)."""
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True)
    # Use the REAL schema so the self-check runs end-to-end (a read of a file).
    (cap / "schemas").mkdir(parents=True)
    (cap / "schemas" / "substrate-map.schema.json").write_text(
        SUBSTRATE_MAP_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")

    issued: list[list[str]] = []

    def fake_gh_run(args, config=None, **kwargs):
        issued.append(list(args))
        served = _serve_auj_reads(args)
        return served

    # Patch at the SOURCE module (`_lib.gh`) so ANY reachable gh call is captured,
    # plus the script's own binding.
    sys.path.insert(0, str(LIB_DIR))
    import gh as gh_source  # the `_lib.gh` module, imported as top-level `gh`
    monkeypatch.setattr(gh_source, "gh_run", fake_gh_run)
    monkeypatch.setattr(ae, "gh_run", fake_gh_run)

    monkeypatch.setattr(ae, "load_adopter_config", lambda _r: _config())
    out = tmp_path / "draft-substrate-map.yaml"
    monkeypatch.setattr(
        sys, "argv",
        ["adopt-existing.py", "--capability-root", str(cap), "--out", str(out)],
    )

    rc = ae.main()
    assert rc == 0

    offenders = [c for c in issued if _is_mutating_call(c)]
    assert not offenders, f"the ceremony issued mutating gh call(s): {offenders}"
    # At least the two inventory reads were issued (proves the ceremony actually ran).
    assert any(c[:3] == ["gh", "label", "list"] for c in issued)
    assert any(c[:3] == ["gh", "issue", "list"] for c in issued)
    # The draft was written to the REVIEW file, never the live map.
    assert out.exists()
    assert not (cap / "project" / "substrate-map.yaml").exists()


def test_no_write_detector_catches_a_graphql_mutation() -> None:
    """Mutation-proof for the no-write detector: a `gh api graphql` READ passes; an
    `updateProjectV2ItemFieldValue` MUTATION is flagged (the detector is not a
    blanket graphql exemption)."""
    read_call = ["gh", "api", "graphql", "-f",
                 "query=query($p: ID!) { node(id: $p) { id } }"]
    mutation_call = ["gh", "api", "graphql", "-f",
                     "query=mutation { updateProjectV2ItemFieldValue(input: {}) "
                     "{ clientMutationId } }"]
    assert _is_mutating_call(read_call) is False
    assert _is_mutating_call(mutation_call) is True


def test_no_write_detector_catches_milestone_and_issue_lifecycle_writes() -> None:
    """C2 — the widened detector flags the OTHER DEC-037 §3 substrates: a
    `--milestone` write, a `gh api .../milestones -X POST`, and
    `gh issue develop`/`transfer`/`pin`. Reads against those substrates still pass,
    so the widening doesn't make a benign read look like a write."""
    # Milestone writes (assign on edit, create via api) — flagged.
    assert _is_mutating_call(
        ["gh", "issue", "edit", "5", "--milestone", "Sprint 1"]) is True
    assert _is_mutating_call(
        ["gh", "api", "repos/o/r/milestones", "-X", "POST", "-f", "title=Sprint 1"]) is True
    # Issue-lifecycle mutations DEC-037 §3 names — flagged.
    assert _is_mutating_call(["gh", "issue", "develop", "5"]) is True
    assert _is_mutating_call(["gh", "issue", "transfer", "5", "o/other"]) is True
    assert _is_mutating_call(["gh", "issue", "pin", "5"]) is True
    # Reads against the same substrates still pass (a milestones LIST is a read).
    assert _is_mutating_call(["gh", "api", "repos/o/r/milestones"]) is False
    assert _is_mutating_call(
        ["gh", "issue", "list", "--json", "number,milestone"]) is False


def test_script_shells_out_only_through_gh_run_no_direct_subprocess_run() -> None:
    """C1 — make the mutate-nothing invariant STRUCTURAL, not just test-enforced.

    The end-to-end no-mutation test patches `gh_run`, so it proves "no mutating call
    THROUGH gh_run" — a future DIRECT `subprocess.run(` would BYPASS that stub and
    go uncaught (the same limitation back-fill's sibling guard closes). Since
    mutate-nothing is THE invariant of this tool, this guard asserts structurally
    that the script constructs no `subprocess.run(` literal — every shell-out is
    routed through the auditable `gh_run` seam (mirroring the ADR-031 guard
    philosophy: enforce the seam structurally, don't rely on it being remembered)."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "subprocess.run(" not in source, (
        "adopt-existing.py contains a direct `subprocess.run(` — every gh shell-out "
        "must go through `gh_run` so the mutate-nothing invariant (DEC-037 §1) is "
        "auditable at one seam, not scattered across direct subprocess calls."
    )
    # It must not even import subprocess (no path to a direct call).
    assert "import subprocess" not in source, (
        "adopt-existing.py imports `subprocess` directly — it should shell out only "
        "via `gh_run`."
    )
