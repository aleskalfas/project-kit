"""Tests for set-field's pure planning logic (no network) + its exit contract.

Covers label resolution + idempotent diff for priority/workstream, the
parent-ref body rewrite (replace / prepend / no-op, and below a DEC-013
integration marker that stays the first line — #765; a malformed marker is
refused before anything is written — #1241), value-vocabulary reads,
the BOARD single-select write (#724 — name → id resolution, and the five
refusals that each name what the board actually offers), and the honesty posture
inherited from #709: a requested axis that was not written is `[refused]` with a
non-zero exit, never `[ok]`, while the label-substrate path and the partial
(mixed-axes) case stay legible. And `--parent`'s native half (#1040): the native
sub-issue link moves with the first line, or the call refuses before writing.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "set-field.py"
)
SCRIPTS = SCRIPT_PATH.parent


@pytest.fixture(scope="module")
def sf():
    sys.path.insert(0, str(SCRIPTS))
    module_name = "pm_set_field_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def axis_labels():
    # The read/write seam set-field resolves every axis through (ADR-026) — used
    # here only to build a parsed substrate-map fixture.
    sys.path.insert(0, str(SCRIPTS))
    from _lib import axis_labels as mod

    return mod


@pytest.fixture(scope="module")
def cr():
    # The shared kind ↔ structural predicate now lives in _lib (extracted from
    # set-field per COR-007 / issue #410); the pure permit/refuse + kind-drives
    # tests assert it directly at its new home.
    sys.path.insert(0, str(SCRIPTS))
    from _lib import classification_rules

    return classification_rules


@pytest.fixture
def issue_types() -> dict:
    return {
        "types": {
            "epic": {"title_prefix": "EPIC", "title_case": "upper"},
            "feature": {
                "title_prefix": "Feature",
                "title_case": "title",
                "parent_ref_form": "EPIC: #<N>",
            },
            "task": {
                "title_prefix": "Task",
                "title_case": "title",
                "parent_ref_form": "Feature: #<N>",
            },
        },
    }


@pytest.fixture
def classification() -> dict:
    return {
        "axes": {
            "priority": {"values": ["High", "Medium", "Low"]},
            "type": {
                "values": [
                    "feature",
                    "bug",
                    "docs",
                    "test",
                    "refactor",
                    "maintenance",
                ],
                "title_prefix_by_value": {
                    "feature": "Task",
                    "bug": "Bug",
                    "docs": "Docs",
                    "test": "Test",
                    "refactor": "Refactor",
                    "maintenance": "Chore",
                },
                "structural_restriction": {
                    "allowed_structural_types_per_kind": {
                        "feature": ["task", "feature", "umbrella", "epic"],
                        "bug": ["task"],
                        "docs": ["task"],
                        "test": ["task"],
                        "refactor": ["task"],
                        "maintenance": ["task"],
                    },
                },
            },
        },
    }


# --- value vocabulary reads -------------------------------------------------


def test_axis_values_reads_priority_list(sf, classification) -> None:
    assert sf._axis_values(classification, "priority") == {"High", "Medium", "Low"}


def test_axis_values_empty_for_unknown_axis(sf, classification) -> None:
    assert sf._axis_values(classification, "nope") == set()


def test_adopter_workstreams_list_form(sf) -> None:
    assert sf._adopter_workstreams({"workstreams": ["cli", "docs"]}) == {"cli", "docs"}


def test_adopter_workstreams_mapping_form(sf) -> None:
    assert sf._adopter_workstreams({"workstreams": {"cli": {}, "docs": {}}}) == {"cli", "docs"}


# --- label planning (greenfield: substrate_map None) -----------------------


def test_plan_labels_sets_new_priority(sf) -> None:
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=["type:feature"],
        substrate_map=None,
    )
    assert add == ["priority:High"]
    assert remove == []
    assert any(r.changed for r in results)


def test_plan_labels_replaces_stale_priority(sf) -> None:
    _results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=["priority:Low", "type:feature"],
        substrate_map=None,
    )
    assert add == ["priority:High"]
    assert remove == ["priority:Low"]


def test_plan_labels_idempotent_noop(sf) -> None:
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=["priority:High"],
        substrate_map=None,
    )
    assert add == [] and remove == []
    assert any("no-op" in r.message for r in results)


def test_plan_labels_batch_priority_and_workstream(sf) -> None:
    _results, add, _remove = sf._plan_labels(
        priority="Medium",
        workstream="cli",
        current_labels=[],
        substrate_map=None,
    )
    assert set(add) == {"priority:Medium", "workstream:cli"}


# --- axis routing: which substrate owns the axis (#724, #712) ----------------
#
# Routing asks `_lib/axis_carriage` and nothing else
# ([project-management:DEC-051-axis-carriage-activation]): where the map binds the
# axis, the binding decides and the board flag is not consulted for it; where the
# map is silent, the flag governs as before. The previous predicate — the flag
# crossed with `axis_is_label_bound` — resolved board-versus-label FIRST, so under
# a configured board a label-bound axis never reached the seam at all.

_BOARD = {"has_projects_v2_board": True, "projects_v2_board_id": 7}
_NO_BOARD = {"has_projects_v2_board": False}


def test_route_axes_no_board_sends_everything_to_labels(sf) -> None:
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream="cli",
        config=_NO_BOARD,
        substrate_map=None,
    )
    assert label_axes == {"priority": "High", "workstream": "cli"}
    assert board_axes == {}
    assert results == []


def test_route_axes_board_claims_priority_and_workstream(sf) -> None:
    """The map is silent, so the flag still governs — today's behaviour, kept."""
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream="cli",
        config=_BOARD,
        substrate_map=None,
    )
    assert board_axes == {"priority": "High", "workstream": "cli"}
    assert label_axes == {}
    assert results == []


def test_route_axes_label_binding_wins_over_the_board_flag(sf, axis_labels) -> None:
    """The #708 config — board flag on, map binds `priority` to the adopter's own
    labels — is no longer a refusal: the binding governs the axis it names, so the
    value routes to the LABEL plan and the board is not consulted for it."""
    sm = axis_labels.SubstrateMap(axes={"priority": {"label": {"remap": {"High": "P0"}}}})
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream=None,
        config=_BOARD,
        substrate_map=sm,
        board_id=7,
    )
    assert label_axes == {"priority": "High"}
    assert board_axes == {}
    assert results == []


def test_route_axes_mixed_map_splits_the_two_axes(sf, axis_labels) -> None:
    """Per-axis, not per-project: a bound axis follows its binding while a sibling
    the map does not bind still falls through to the flag. `unsupported` names no
    substrate, so it does NOT govern — it falls through exactly as an omitted axis
    does (DEC-051 decision point 1)."""
    sm = axis_labels.SubstrateMap(
        axes={
            "priority": {"label": {"remap": {"High": "P0"}}},
            "workstream": {"unsupported": True},
        }
    )
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream="cli",
        config=_BOARD,
        substrate_map=sm,
    )
    assert label_axes == {"priority": "High"}
    assert board_axes == {"workstream": "cli"}
    assert results == []


def test_route_axes_degraded_axis_is_a_note_not_a_refusal(sf, axis_labels) -> None:
    """No board to fall through to: an `unsupported` axis has nowhere to go by the
    adopter's OWN declaration, which stays a note (`ok=True`) — degradation working
    as designed, not a write the verb declined."""
    sm = axis_labels.SubstrateMap(axes={"priority": {"unsupported": True}})
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream=None,
        config=_NO_BOARD,
        substrate_map=sm,
    )
    assert label_axes == {} and board_axes == {}
    note = next(r for r in results if r.field == "priority")
    assert note.ok is True and note.changed is False
    assert "unsupported under your substrate-map" in note.message


def test_route_axes_title_carried_axis_is_refused_never_labelled(sf, axis_labels) -> None:
    """A title-prefix binding is SERVED but is not a substrate set-field writes for
    priority — and routing it to the label planner would apply the PREFIX string as
    a `gh --label` the tracker does not have. Refused, non-zero, never written."""
    sm = axis_labels.SubstrateMap(axes={"priority": {"title-prefix": {"remap": {"High": "[P0]"}}}})
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream=None,
        config=_NO_BOARD,
        substrate_map=sm,
    )
    assert label_axes == {} and board_axes == {}
    refusal = next(r for r in results if r.field == "priority")
    assert refusal.ok is False and refusal.changed is False
    assert "NOT SET" in refusal.message
    assert "in the issue TITLE" in refusal.message


def test_board_field_name_is_title_cased_axis(sf) -> None:
    assert sf._board_field_name("priority") == "Priority"
    assert sf._board_field_name("workstream") == "Workstream"


# --- board single-select planning (#724) -------------------------------------
#
# `_plan_board_fields` is pure: it plans against the `BoardState` snapshot one read
# round-trip produced, so every diagnosis is reachable without a network and is
# identical under `--dry-run`.


def _board_state(sf, **overrides):
    """A resolved BoardState: board #7 with a Priority single-select and a card."""
    defaults = dict(
        project_id="PVT_board7",
        item_id="PVTI_card42",
        fields=(
            {"id": "PVTF_title", "name": "Title", "type": "ProjectV2Field"},
            {
                "id": "PVTSSF_priority",
                "name": "Priority",
                "type": "ProjectV2SingleSelectField",
                "options": [
                    {"id": "opt_high", "name": "High"},
                    {"id": "opt_low", "name": "Low"},
                ],
            },
        ),
        board_ref="Projects-v2 board #7",
        membership_remediation="gh project item-add 7 --owner an-org --url URL",
    )
    defaults.update(overrides)
    return sf.BoardState(**defaults)


def test_plan_board_fields_resolves_field_and_option_by_name(sf) -> None:
    """The substance of #724: names in, ids out — no hand-configured ids."""
    results, writes = sf._plan_board_fields(
        board_axes={"priority": "High"},
        state=_board_state(sf),
        issue_number=42,
    )
    assert len(writes) == 1
    write = writes[0]
    assert write.field_id == "PVTSSF_priority"
    assert write.option_id == "opt_high"
    assert write.item_id == "PVTI_card42"
    assert write.project_id == "PVT_board7"
    assert results[0].ok is True and results[0].changed is True
    assert "set board field `Priority` = 'High'" in results[0].message


def test_plan_board_fields_matches_field_and_option_case_insensitively(sf) -> None:
    state = _board_state(
        sf,
        fields=(
            {
                "id": "PVTSSF_priority",
                "name": "PRIORITY",
                "type": "ProjectV2SingleSelectField",
                "options": [{"id": "opt_high", "name": "high"}],
            },
        ),
    )
    _, writes = sf._plan_board_fields(board_axes={"priority": "High"}, state=state, issue_number=42)
    assert writes[0].option_id == "opt_high"


def test_plan_board_fields_missing_card_refuses_with_the_add_command(sf) -> None:
    """Board membership is a post-creation step, so the card may be absent. The
    decided behaviour is REFUSE with the exact remediation — adding the card is a
    membership decision this verb does not make silently — never a no-op."""
    results, writes = sf._plan_board_fields(
        board_axes={"priority": "High"},
        state=_board_state(sf, item_id=None),
        issue_number=42,
    )
    assert writes == []
    refusal = results[0]
    assert refusal.ok is False and refusal.changed is False
    assert "NO CARD" in refusal.message
    assert "gh project item-add 7 --owner an-org --url URL" in refusal.message
    assert "NOT SET" in refusal.message


def test_plan_board_fields_missing_field_names_what_the_board_offers(sf) -> None:
    """The diagnosis an adopter could not get before: not just "no Priority field"
    but the field list the board actually carries."""
    state = _board_state(
        sf,
        fields=(
            {"id": "PVTF_title", "name": "Title", "type": "ProjectV2Field"},
            {"id": "PVTSSF_status", "name": "Status", "type": "ProjectV2SingleSelectField"},
        ),
    )
    results, writes = sf._plan_board_fields(
        board_axes={"priority": "High"}, state=state, issue_number=42
    )
    assert writes == []
    message = results[0].message
    assert results[0].ok is False
    assert "NO FIELD named `Priority`" in message
    assert "Title, Status" in message


def test_plan_board_fields_missing_option_names_the_options_offered(sf) -> None:
    state = _board_state(sf)
    results, writes = sf._plan_board_fields(
        board_axes={"priority": "Medium"}, state=state, issue_number=42
    )
    assert writes == []
    message = results[0].message
    assert results[0].ok is False
    assert "NO OPTION named 'Medium'" in message
    assert "High, Low" in message


def test_plan_board_fields_refuses_a_non_single_select_field(sf) -> None:
    """Text / number / date / iteration are out of scope (#724) — refuse by type
    rather than mangle the value into a text field."""
    state = _board_state(
        sf,
        fields=({"id": "PVTF_priority", "name": "Priority", "type": "ProjectV2Field"},),
    )
    results, writes = sf._plan_board_fields(
        board_axes={"priority": "High"}, state=state, issue_number=42
    )
    assert writes == []
    assert results[0].ok is False
    assert "UNSUPPORTED FIELD TYPE" in results[0].message
    assert "ProjectV2Field" in results[0].message


def test_plan_board_fields_read_failure_surfaces_gh_stderr_verbatim(sf) -> None:
    """Scope / permission failures are the likeliest board failure and the remedy is
    in gh's own words — so they are passed through, not paraphrased."""
    stderr = (
        "your token has not been granted the required scopes to execute this "
        "query. missing: 'read:project'"
    )
    results, writes = sf._plan_board_fields(
        board_axes={"priority": "High"},
        state=_board_state(sf, error=stderr, item_id=None, fields=()),
        issue_number=42,
    )
    assert writes == []
    assert results[0].ok is False
    assert stderr in results[0].message


def test_plan_board_fields_plans_both_axes_independently(sf) -> None:
    """One axis resolvable, its sibling not: each gets its own verdict."""
    state = _board_state(sf)
    results, writes = sf._plan_board_fields(
        board_axes={"priority": "High", "workstream": "cli"},
        state=state,
        issue_number=42,
    )
    assert [w.axis for w in writes] == ["priority"]
    assert [(r.field, r.ok) for r in results] == [("priority", True), ("workstream", False)]


def test_label_substrate_path_is_untouched_by_the_board_path(sf) -> None:
    """Regression guard: the label planner is unchanged — `ok=True` and the labels
    planned exactly as before."""
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream="cli",
        current_labels=["priority:Low"],
        substrate_map=None,
    )
    assert set(add) == {"priority:High", "workstream:cli"}
    assert remove == ["priority:Low"]
    assert all(r.ok for r in results)


def test_plan_labels_value_with_no_remap_entry_is_a_refusal(sf, axis_labels) -> None:
    """DEC-051 decision point 5: routing has already established that a LABEL
    carries this axis, so the only remaining degrade is the value-unresolvable
    fourth arm — the adopter's `remap` has no entry for this value. It landed
    nowhere, so it must not report success (it used to return `ok=True`)."""
    sm = axis_labels.SubstrateMap(axes={"priority": {"label": {"remap": {"Low": "P2"}}}})
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=[],
        substrate_map=sm,
    )
    assert add == [] and remove == []
    refused = next(r for r in results if r.field == "priority")
    assert refused.ok is False and refused.changed is False
    assert "NOT SET" in refused.message


def test_plan_labels_strips_the_adopters_own_stale_label(sf, axis_labels) -> None:
    """A `label`-bound axis's substrate is the adopter's OWN label name, which
    carries no `priority:` prefix — a prefix-only stale search would add `P0` and
    leave `P2` behind, two values on a single-valued axis."""
    sm = axis_labels.SubstrateMap(
        axes={"priority": {"label": {"remap": {"High": "P0", "Low": "P2"}}}}
    )
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=["P2", "type:bug"],
        substrate_map=sm,
    )
    assert add == ["P0"]
    assert remove == ["P2"]
    assert all(r.ok for r in results)


def test_field_list_dedupes_and_preserves_order(sf) -> None:
    fr = sf.FieldResult
    listed = sf._field_list(
        [
            fr(field="kind", ok=True, changed=True, message=""),
            fr(field="title", ok=True, changed=True, message=""),
            fr(field="kind", ok=True, changed=False, message=""),
        ]
    )
    assert listed == "kind, title"


# --- kind planning (label swap + title-prefix realignment) ------------------


def test_axis_values_reads_type_list(sf, classification) -> None:
    assert sf._axis_values(classification, "type") == {
        "feature",
        "bug",
        "docs",
        "test",
        "refactor",
        "maintenance",
    }


def test_plan_kind_swaps_label_and_realigns_prefix(sf, issue_types, classification) -> None:
    results, add, remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Chore] fix the broken verb",
        current_labels=["type:maintenance", "priority:Medium"],
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    assert add == ["type:bug"]
    assert remove == ["type:maintenance"]
    assert new_title == "[Bug] fix the broken verb"
    assert any(r.field == "kind" and r.changed for r in results)
    assert any(r.field == "title" and r.changed for r in results)


def test_plan_kind_prefix_already_correct_is_noop(sf, issue_types, classification) -> None:
    # Label changes but the title prefix already matches the target kind.
    results, add, remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Bug] already titled right",
        current_labels=["type:maintenance"],
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    assert add == ["type:bug"]
    assert remove == ["type:maintenance"]
    assert new_title is None
    assert not any(r.field == "title" for r in results)


def test_plan_kind_idempotent_when_label_and_prefix_match(sf, issue_types, classification) -> None:
    results, add, remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Bug] nothing to do",
        current_labels=["type:bug"],
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    assert add == [] and remove == []
    assert new_title is None
    assert any("no-op" in r.message for r in results)


def test_kind_mismatch_on_epic_feature_umbrella_is_refused(cr, classification) -> None:
    # The up-front gate (DEC-011 / structural_restriction) refuses a non-feature
    # kind on epic/feature/umbrella — it would manufacture the kind/structural
    # mismatch that breaks PR-conv-type derivation. The gate is the SAME table
    # `kind_drives_title` reads; assert the shared predicate that drives it.
    assert cr.kind_allowed_for_structural_type("bug", "epic", classification) is False
    assert cr.kind_allowed_for_structural_type("bug", "feature", classification) is False
    assert cr.kind_allowed_for_structural_type("docs", "umbrella", classification) is False


def test_kind_feature_on_epic_feature_umbrella_is_permitted(cr, classification) -> None:
    # `feature` IS the kind epic/feature/umbrella carry by definition, so the gate
    # permits it (it lands downstream as a no-op: label already type:feature, no
    # prefix change). Permitted-not-refused is the consistent choice with the
    # up-front check keyed on `allowed_structural_types_per_kind`.
    assert cr.kind_allowed_for_structural_type("feature", "epic", classification) is True
    assert cr.kind_allowed_for_structural_type("feature", "feature", classification) is True
    assert cr.kind_allowed_for_structural_type("feature", "umbrella", classification) is True
    # And on a task, every kind is permitted.
    assert cr.kind_allowed_for_structural_type("bug", "task", classification) is True


def test_kind_allowed_permissive_on_empty_classification(cr) -> None:
    # No restriction table to ground a refusal ⇒ permit (the up-front gate refuses
    # nothing it can't ground in the schema).
    assert cr.kind_allowed_for_structural_type("bug", "epic", {}) is True


def test_plan_kind_feature_on_feature_issue_is_full_noop(sf, issue_types, classification) -> None:
    # The one --kind path that reaches _plan_kind for a feature-structural issue:
    # kind `feature` on an already-`type:feature` [Feature] issue. Label already
    # correct, structural prefix already correct — nothing mutates.
    results, add, remove, new_title = sf._plan_kind(
        kind="feature",
        title="[Feature] a feature surface",
        current_labels=["type:feature"],
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    assert add == [] and remove == []
    assert new_title is None
    assert any("no-op" in r.message for r in results)


def test_retitle_prefix_swaps_leading_bracket(sf) -> None:
    assert sf._retitle_prefix("[Chore] do a thing", "Bug") == "[Bug] do a thing"


def test_retitle_prefix_none_without_prefix(sf) -> None:
    assert sf._retitle_prefix("no prefix here", "Bug") is None


def test_kind_drives_title_true_for_task(cr, classification) -> None:
    assert cr.kind_drives_title("task", classification) is True


def test_kind_drives_title_false_for_feature(cr, classification) -> None:
    assert cr.kind_drives_title("feature", classification) is False


def test_kind_drives_title_false_on_empty_classification(cr) -> None:
    assert cr.kind_drives_title("task", {}) is False


def test_unknown_kind_not_in_declared_values(sf, classification) -> None:
    # The up-front validation gate reads the declared type vocabulary; an unknown
    # kind is absent from it, so the gate (in main) refuses before any mutation.
    valid = sf._axis_values(classification, "type")
    assert "nonsense" not in valid
    assert "bug" in valid


def test_kind_composes_with_priority_workstream_batch(sf, issue_types, classification) -> None:
    # The aggregate add/remove main builds: kind swap + priority + workstream in
    # one batch, all label writes against a single edit call.
    current = ["type:maintenance", "priority:Low"]
    _k_results, k_add, k_remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Chore] mislabelled defect",
        current_labels=current,
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    _a_results, a_add, a_remove = sf._plan_labels(
        priority="High",
        workstream="cli",
        current_labels=current,
        substrate_map=None,
    )
    add = k_add + a_add
    remove = k_remove + a_remove
    assert set(add) == {"type:bug", "priority:High", "workstream:cli"}
    assert set(remove) == {"type:maintenance", "priority:Low"}
    assert new_title == "[Bug] mislabelled defect"


# --- parent-ref planning ----------------------------------------------------


def test_plan_parent_replaces_existing_ref(sf) -> None:
    body = "Feature: #1\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body.startswith("Feature: #9\n")
    assert result.changed is True


def test_plan_parent_idempotent_noop(sf) -> None:
    body = "Feature: #9\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == body
    assert result.changed is False
    assert "no-op" in result.message


def test_plan_parent_prepends_when_absent(sf) -> None:
    body = "## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body.startswith("Feature: #9\n\n## What")
    assert result.changed is True


def test_plan_parent_preserves_milestone_link_form_recognised(sf) -> None:
    body = "Milestone: [#6](../milestone/6)\n\n## What\nx\n"
    new_body, _result = sf._plan_parent(body, "EPIC: #3")
    # The existing first line is a recognised parent-ref, so it is REPLACED
    # (not prepended-before).
    assert new_body.startswith("EPIC: #3\n")
    assert "Milestone:" not in new_body.splitlines()[0]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Feature: #1\n\n## What\nx\n", "Feature: #9\n\n## What\nx\n"),
        ("\n\nFeature: #1\n\n## What\nx\n", "\n\nFeature: #9\n\n## What\nx\n"),
        ("## What\nx\n", "Feature: #9\n\n## What\nx\n"),
        ("\n \n\n## What\nx\n", "Feature: #9\n\n## What\nx\n"),
        ("", "Feature: #9\n"),
    ],
    ids=[
        "replace",
        "replace-after-leading-blanks",
        "prepend",
        "prepend-over-leading-blanks",
        "empty-body",
    ],
)
def test_plan_parent_unmarked_body_exact_rewrite(sf, body, expected) -> None:
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == expected
    assert result.changed is True


# --- parent-ref planning under a DEC-013 integration marker (#765) ----------
#
# A marked body opens with `Integration: integration/<slug>`, directly above the
# parent-ref with no blank line between (DEC-013). `--parent` rewrites the
# parent-ref below the marker; it must never push the marker off the first line,
# where every reader looks for it — a buried marker also loses the issue its
# integration branch.

_MARKER = "Integration: integration/foo"


def test_plan_parent_under_marker_replaces_the_ref_below_it(sf) -> None:
    body = f"{_MARKER}\nFeature: #1\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == f"{_MARKER}\nFeature: #9\n\n## What\nx\n"
    assert result.changed is True
    assert "was 'Feature: #1'" in result.message


def test_plan_parent_under_marker_idempotent_noop(sf) -> None:
    body = f"{_MARKER}\nFeature: #9\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == body
    assert result.changed is False
    assert "no-op" in result.message


def test_plan_parent_under_marker_crlf_reset_is_a_noop(sf) -> None:
    body = f"{_MARKER}\r\nFeature: #9\r\n\r\n## What\r\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == body
    assert result.changed is False


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (f"{_MARKER}\n\n## What\nx\n", f"{_MARKER}\nFeature: #9\n\n## What\nx\n"),
        (f"{_MARKER}\n## What\nx\n", f"{_MARKER}\nFeature: #9\n\n## What\nx\n"),
        (f"{_MARKER}\n", f"{_MARKER}\nFeature: #9\n"),
    ],
    ids=["blank-then-content", "content-directly-below", "marker-only"],
)
def test_plan_parent_under_marker_without_a_ref_inserts_directly_below(sf, body, expected) -> None:
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == expected
    assert result.changed is True
    assert "inserted below the integration marker" in result.message


@pytest.mark.parametrize(
    "body",
    [
        f"{_MARKER}\nFeature: #1\n\n## What\n",
        f"{_MARKER}\n\n## What\n",
        f"\n\n{_MARKER}\nFeature: #1\n\n## What\n",
        f"{_MARKER}\r\nFeature: #1\r\n\r\n## What\r\n",
        f"{_MARKER}\r\n\r\n## What\r\n",
    ],
    ids=["ref", "no-ref", "leading-blanks", "crlf-ref", "crlf-no-ref"],
)
def test_plan_parent_under_marker_reads_back_marker_first(sf, body) -> None:
    """Whatever the layout, the written body opens with the marker and the new
    parent-ref directly below it, and the readers find both."""
    new_body, _result = sf._plan_parent(body, "Feature: #9")
    lines = [ln.strip() for ln in new_body.splitlines()]
    first = next(i for i, ln in enumerate(lines) if ln)
    assert lines[first : first + 2] == [_MARKER, "Feature: #9"]
    assert sf.body_parent_ref.named_issue(new_body) == 9
    assert sf.infer.integration_slug(new_body) == "foo"


# --- structural type + parent-ref form -------------------------------------


def test_infer_structural_type_task(sf, issue_types) -> None:
    assert sf.infer_structural_type("[Task] x", issue_types) == "task"


def test_infer_structural_type_bug_via_classification(sf, issue_types, classification) -> None:
    assert sf.infer_structural_type("[Bug] x", issue_types, classification=classification) == "task"


def test_parent_ref_line_uses_type_form(sf, issue_types) -> None:
    task = issue_types["types"]["task"]
    assert sf._parent_ref_line(task, 42) == "Feature: #42"


def test_parent_ref_line_empty_without_form(sf) -> None:
    assert sf._parent_ref_line({}, 42) == ""


def test_is_parent_ref_recognises_forms(sf) -> None:
    assert sf._is_parent_ref("Feature: #1")
    assert sf._is_parent_ref("Milestone: [#6](../milestone/6)")
    assert sf._is_parent_ref("Milestone: #6")
    assert sf._is_parent_ref("Epic:#5")
    assert sf._is_parent_ref("Feature: #1   ")
    assert not sf._is_parent_ref("## What")
    assert not sf._is_parent_ref("just prose")
    # A line naming an issue and saying more is not a parent-ref and nothing else.
    assert not sf._is_parent_ref("Feature: #12 — auth")
    assert not sf._is_parent_ref("Note: #45 was closed in favour of this one")


# --- `--parent` never deletes what an author wrote (#1281) -----------------
#
# Only a first line that is a parent-ref and nothing else is replaced. A first
# line naming an issue and saying more is kept, and the new parent-ref is
# written above it: every reader reads only the first line, so it reads the new
# one, and nothing the author wrote is lost. The plan line says which was done.

_TAILED_LINES = [
    "Feature: #12 — auth",
    "Fixes: #12 by moving the reader into the seam, so the cascade reads one parent",
    "Note: #45 was closed in favour of this one; its discussion still applies here.",
]


@pytest.mark.parametrize("line", _TAILED_LINES)
def test_plan_parent_keeps_a_first_line_that_names_an_issue_and_says_more(sf, line) -> None:
    body = f"{line}\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == f"Feature: #9\n\n{line}\n\n## What\nx\n"
    assert sf.body_parent_ref.named_issue(new_body) == 9
    assert result.changed is True
    named = sf.body_parent_ref.named_issue(f"{line}\n")
    assert result.message == (
        f"parent: set 'Feature: #9' (prepended, above {line!r}, which names #{named} and says "
        "more, so it is kept)"
    )


@pytest.mark.parametrize("line", ["Feature: #12", "Epic:#5", "Feature: #12  ", "Milestone: #3"])
def test_plan_parent_replaces_a_first_line_that_is_only_a_parent_ref(sf, line) -> None:
    body = f"{line}\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == "Feature: #9\n\n## What\nx\n"
    assert result.message == f"parent: set 'Feature: #9' (was {line.strip()!r})"


@pytest.mark.parametrize("line", _TAILED_LINES)
def test_plan_parent_under_marker_keeps_a_tailed_line_below_the_new_ref(sf, line) -> None:
    for between in ("", "\n"):
        body = f"{_MARKER}\n{between}{line}\n\n## What\nx\n"
        new_body, result = sf._plan_parent(body, "Feature: #9")
        assert new_body == f"{_MARKER}\nFeature: #9\n\n{line}\n\n## What\nx\n", between
        assert sf.infer.integration_slug(new_body) == "foo"
        assert sf.body_parent_ref.named_issue(new_body) == 9
        assert "(inserted below the integration marker, above " in result.message
        assert "so it is kept)" in result.message


def test_plan_parent_under_marker_replaces_a_bare_ref_directly_below_it(sf) -> None:
    body = f"{_MARKER}\nEpic:#5\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == f"{_MARKER}\nFeature: #9\n\n## What\nx\n"
    assert result.message == "parent: set 'Feature: #9' (was 'Epic:#5')"


@pytest.mark.parametrize("marker", ["", f"{_MARKER}\r\n"])
def test_plan_parent_on_a_crlf_body_keeps_a_tailed_line_and_replaces_a_bare_one(sf, marker) -> None:
    tailed = f"{marker}Feature: #12 — auth\r\n\r\n## What\r\nx\r\n"
    new_body, result = sf._plan_parent(tailed, "Feature: #9")
    lines = [ln for ln in new_body.splitlines() if ln.strip()]
    expected_first = [_MARKER] if marker else []
    assert lines[: len(expected_first) + 2] == [
        *expected_first,
        "Feature: #9",
        "Feature: #12 — auth",
    ]
    assert sf.body_parent_ref.named_issue(new_body) == 9
    assert "so it is kept)" in result.message

    bare = f"{marker}Feature: #12\r\n\r\n## What\r\nx\r\n"
    new_body, result = sf._plan_parent(bare, "Feature: #9")
    lines = [ln for ln in new_body.splitlines() if ln.strip()]
    assert lines[: len(expected_first) + 2] == [*expected_first, "Feature: #9", "## What"]
    assert result.message == "parent: set 'Feature: #9' (was 'Feature: #12')"


# --- the board READ orchestration (#724) -------------------------------------
#
# `_read_board_state` is the one place the three board reads happen. The seam
# functions (`_lib/board_fields`) are stubbed; the orchestration — order, the
# membership-remediation composition, and error capture — runs for real.


def _stub_board_reads(
    sf,
    monkeypatch,
    *,
    project=None,
    fields_read=None,
    item=None,
) -> None:
    bf = sf.board_fields
    monkeypatch.setattr(
        bf,
        "read_project_node_id",
        lambda config, owner=None, gh_call=None: (
            project or bf.ProjectLookup(ok=True, node_id="PVT_board7")
        ),
    )
    monkeypatch.setattr(
        bf,
        "read_fields",
        lambda config, owner=None, gh_call=None: (
            fields_read or bf.BoardFieldsRead(ok=True, fields=({"id": "F", "name": "Priority"},))
        ),
    )
    monkeypatch.setattr(
        bf,
        "resolve_item_id",
        lambda config, issue_node_id, project_node_id, gh_call=None: (
            item or bf.ItemLookup(ok=True, item_id="PVTI_card42")
        ),
    )


_BOARD_CONFIG = {
    "has_projects_v2_board": True,
    "projects_v2_board_id": 7,
    "gh": {"default_owner": "an-org"},
}
_BOARD_ISSUE = {"id": "I_issue42", "url": "https://github.com/an-org/r/issues/42"}


def test_read_board_state_gathers_the_three_ids(sf, monkeypatch) -> None:
    _stub_board_reads(sf, monkeypatch)
    state = sf._read_board_state(_BOARD_CONFIG, issue=_BOARD_ISSUE, issue_number=42)
    assert state.error is None
    assert state.project_id == "PVT_board7"
    assert state.item_id == "PVTI_card42"
    assert state.fields == ({"id": "F", "name": "Priority"},)
    assert state.board_ref == "Projects-v2 board #7"


def test_read_board_state_composes_the_exact_item_add_remediation(sf, monkeypatch) -> None:
    """The missing-card refusal is only actionable if the command is runnable as
    printed — board number, owner and issue URL all resolved."""
    _stub_board_reads(sf, monkeypatch)
    state = sf._read_board_state(_BOARD_CONFIG, issue=_BOARD_ISSUE, issue_number=42)
    assert state.membership_remediation == (
        "gh project item-add 7 --owner an-org --url https://github.com/an-org/r/issues/42"
    )


def test_read_board_state_surfaces_a_read_failure_verbatim(sf, monkeypatch) -> None:
    stderr = "missing required scopes: 'read:project'"
    _stub_board_reads(
        sf,
        monkeypatch,
        fields_read=sf.board_fields.BoardFieldsRead(ok=False, error=stderr),
    )
    state = sf._read_board_state(_BOARD_CONFIG, issue=_BOARD_ISSUE, issue_number=42)
    assert state.error == stderr


def test_read_board_state_without_an_issue_node_id_is_an_error_not_a_guess(sf, monkeypatch) -> None:
    _stub_board_reads(sf, monkeypatch)
    state = sf._read_board_state(_BOARD_CONFIG, issue={"url": "u"}, issue_number=42)
    assert state.error is not None
    assert "no node id" in state.error


# --- main()'s exit contract (#709 posture, #724 board write) -----------------
#
# The planning tests above pin `ok=False` / the resolved write; these pin what the
# CALLER sees — the exit code and the summary line — because that is where the
# original bug lived: a refusal that exited 0 and summarised as "all fields already
# set". No network: the gh seams (`gh_get_issue`, the label/title writers, the
# board read + the board write) and the foreign-repo guard are stubbed; everything
# else (config load, membership, schema reads, routing, planning, summary) runs for
# real.


def _mark_bootstrapped(cap_root: Path) -> None:
    """Make a staged tree look like the bootstrapped project it stands in for.

    Every pm verb except the five setup/diagnosis ones refuses a project with no
    bootstrap stamp or no adopter config (the #747 prerequisite gate); a staged
    tree standing in for a live project is a bootstrapped one. The config is
    seeded only when absent, so a test that stages its own keeps it, and the
    stamp is left unbound (`repo:` null) so no git remote is needed in a tmp tree.
    """
    project = cap_root / "project"
    project.mkdir(parents=True, exist_ok=True)
    config = project / "config.yaml"
    if not config.is_file():
        config.write_text(
            "schema_version: 1\ndefault_branch: main\nworkstreams: []\n",
            encoding="utf-8",
        )
    (project / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )


def _stage_capability_root(tmp_path: Path, *, has_board: bool) -> Path:
    """Stage a minimal but REAL pm capability tree set-field's main() can run on."""
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    (root / "schemas").mkdir(parents=True)
    (root / "project").mkdir(parents=True)

    (root / "schemas" / "issue-types.yaml").write_text(
        "types:\n"
        "  feature:\n"
        "    title_prefix: Feature\n"
        "    title_case: title\n"
        "    can_contain: [task]\n"
        "    parent_issue_types: []\n"
        "    parent_ref_form: 'Milestone: [#<N>](../milestone/<N>)'\n"
        "  task:\n"
        "    title_prefix: Task\n"
        "    title_case: title\n"
        "    can_contain: []\n"
        "    parent_issue_types: [feature]\n"
        "    parent_ref_form: 'Feature: #<N>'\n",
        encoding="utf-8",
    )
    (root / "schemas" / "classification.yaml").write_text(
        "axes:\n"
        "  priority:\n"
        "    values: [High, Medium, Low]\n"
        "  type:\n"
        "    values: [feature, bug]\n"
        "    title_prefix_by_value:\n"
        "      feature: Task\n"
        "      bug: Bug\n"
        "    structural_restriction:\n"
        "      allowed_structural_types_per_kind:\n"
        "        feature: [task, feature, umbrella, epic]\n"
        "        bug: [task]\n",
        encoding="utf-8",
    )

    config_lines = ["schema_version: 1\ndefault_branch: main\nworkstreams: [cli]\n"]
    if has_board:
        config_lines.append("has_projects_v2_board: true\nprojects_v2_board_id: 7\n")
    (root / "project" / "config.yaml").write_text("".join(config_lines), encoding="utf-8")
    # Empty members ⇒ open mode (membership passes for any resolved identity).
    (root / "project" / "members.yaml").write_text("members: []\n", encoding="utf-8")
    _mark_bootstrapped(root)
    return root


def _run_main(
    sf,
    monkeypatch,
    *,
    root: Path,
    argv: list[str],
    issue: dict,
    board_state=None,
    board_write_ok: bool = True,
    others: Mapping[int, dict | None] | None = None,
) -> dict:
    """Drive `sf.main()` with the gh seams stubbed; return rc + captured writes.

    `board_state` stubs the board READ (its own tests cover the orchestration), so
    a main() test states the board situation as data. Board writes are captured
    rather than issued; `board_write_ok=False` makes the write fail at the point of
    writing (the exit-3 path). `issue` answers every issue read but those
    `others` answers by number — a `--parent`'s record read, made through the
    containment seam (`containment.read_issue_record`); an `others` answer of
    None is a read that fails, and one carrying `not_an_issue` names a pull
    request.
    """
    captured: dict = {"labels": [], "titles": [], "bodies": [], "board": []}

    monkeypatch.setattr(sf, "gh_get_issue", lambda n, *a, **k: (others or {}).get(n, issue))

    def fake_record_read(config, *, issue_number):
        answer = (others or {}).get(int(issue_number), issue)
        if answer is None:
            said = sf.containment.Said("HTTP 502: Bad Gateway", sf.containment.SPEAKER_GH)
            return sf.containment.UnreadIssue("gh exited 1", said)
        if answer.get("not_an_issue"):
            return sf.containment.UnreadIssue(
                f"#{issue_number} is a pull request", not_an_issue=True
            )
        record = {"title": answer.get("title", ""), "labels": answer.get("labels", [])}
        return sf.containment.IssueRecord(issue=record, parent=None)

    monkeypatch.setattr(sf.containment, "read_issue_record", fake_record_read)
    if board_state is not None:
        monkeypatch.setattr(sf, "_read_board_state", lambda config, **k: board_state)

    def fake_board_write(write, config):
        captured["board"].append(write)
        return board_write_ok

    monkeypatch.setattr(sf, "_write_board_field", fake_board_write)
    monkeypatch.setattr(sf.session_guard, "enforce", lambda **k: True)
    monkeypatch.setenv("PM_INVOKER_LOGIN", "an-invoker")

    def fake_edit_labels(issue_number, add, remove, config):
        captured["labels"].append((add, remove))
        return True

    monkeypatch.setattr(sf, "_gh_edit_labels", fake_edit_labels)
    monkeypatch.setattr(
        sf,
        "_gh_write_title",
        lambda n, title, config: captured["titles"].append(title) is None,
    )
    monkeypatch.setattr(
        sf,
        "_gh_write_body",
        lambda n, body, config: captured["bodies"].append(body) is None,
    )
    monkeypatch.setattr(
        sf.sys,
        "argv",
        ["set-field.py", *argv, "--capability-root", str(root), "--yes"],
    )
    captured["rc"] = sf.main()
    return captured


_TASK_ISSUE = {
    "title": "[Task] do a thing",
    "body": "## What\nx\n",
    "labels": [],
    "id": "I_issue42",
    "url": "https://github.com/an-org/r/issues/42",
}


def test_main_board_axis_writes_the_board_single_select(sf, tmp_path, monkeypatch, capsys) -> None:
    """#724's headline: `set-field 42 --priority High` under a board WRITES the
    board field — ids resolved from names — and exits 0."""
    root = _stage_capability_root(tmp_path, has_board=True)
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--priority", "High"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf),
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert captured["labels"] == []  # the axis is NOT a label under a board
    assert [(w.field_id, w.option_id, w.item_id) for w in captured["board"]] == [
        ("PVTSSF_priority", "opt_high", "PVTI_card42")
    ]
    assert "[ok] priority: set board field `Priority` = 'High'" in out
    assert "updated" in out
    assert "[refused]" not in out


def test_main_missing_card_refuses_nonzero_and_writes_nothing(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """The membership race: no card on the board ⇒ refusal with the `item-add`
    remediation, non-zero exit, and NO write of any kind. Never a silent no-op."""
    root = _stage_capability_root(tmp_path, has_board=True)
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--priority", "High"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf, item_id=None),
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 1
    assert captured["board"] == [] and captured["labels"] == []
    assert "[refused] priority:" in out
    assert "[ok] priority:" not in out
    assert "gh project item-add 7" in out
    assert "all fields already set" not in out
    assert "remain unset" in out


def test_main_missing_option_refuses_and_names_what_the_board_offers(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    root = _stage_capability_root(tmp_path, has_board=True)
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--priority", "Medium"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf),
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 1
    assert captured["board"] == []
    assert "NO OPTION named 'Medium'" in out
    assert "High, Low" in out


def test_main_dry_run_resolves_the_names_without_mutating(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """`--dry-run` reports the concrete write it WOULD make (names already resolved
    to ids — the resolution is a read) and issues nothing."""
    root = _stage_capability_root(tmp_path, has_board=True)
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--priority", "High", "--dry-run"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf),
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert captured["board"] == []  # nothing written
    assert "would set board field `Priority` = 'High'" in out
    assert "nothing written" in out


def test_main_dry_run_still_refuses_a_knowably_impossible_board_write(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """A missing field/option is knowable without writing, so `--dry-run` reports it
    as a refusal (non-zero) rather than a clean plan."""
    root = _stage_capability_root(tmp_path, has_board=True)
    state = _board_state(
        sf, fields=({"id": "F", "name": "Status", "type": "ProjectV2SingleSelectField"},)
    )
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--priority", "High", "--dry-run"],
        issue=_TASK_ISSUE,
        board_state=state,
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 1
    assert captured["board"] == []
    assert "[refused]" in out
    assert "NO FIELD named `Priority`" in out


def test_main_board_write_failure_exits_three(sf, tmp_path, monkeypatch, capsys) -> None:
    """A write that failed at the point of writing is exit 3 (the gh-write-failure
    code), not a refusal and certainly not a success."""
    root = _stage_capability_root(tmp_path, has_board=True)
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--priority", "High"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf),
        board_write_ok=False,
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 3
    assert len(captured["board"]) == 1  # attempted
    assert "updated" not in out
    # The plan line said `[ok] … set board field …`; the failure has to be said on
    # the same stream, not left to stderr alone.
    assert "[failed]" in out
    assert "was NOT written" in out


def test_write_board_field_routes_through_the_substrate_write_seam(sf, monkeypatch) -> None:
    """ADR-031: the field-value write is obtained from `substrate_writes`, never
    string-built here — the same primitive the `set-board-field` hook uses."""
    seen: dict = {}

    def fake_write_field_value(config, **kwargs):
        seen.update(kwargs)
        return sf.substrate_writes.SubstrateWriteResult(ok=True, executed=True, detail="set")

    monkeypatch.setattr(sf.substrate_writes, "write_field_value", fake_write_field_value)
    write = sf.BoardWrite(
        axis="priority",
        field_name="Priority",
        field_id="PVTSSF_priority",
        option_name="High",
        option_id="opt_high",
        item_id="PVTI_card42",
        project_id="PVT_board7",
    )
    assert sf._write_board_field(write, {}) is True
    assert seen == {
        "item_id": "PVTI_card42",
        "field_id": "PVTSSF_priority",
        "project_id": "PVT_board7",
        "single_select_option_id": "opt_high",
    }


def test_write_board_field_failure_prints_gh_stderr_verbatim(sf, monkeypatch, capsys) -> None:
    stderr = "HTTP 403: Resource not accessible by personal access token"
    monkeypatch.setattr(
        sf.substrate_writes,
        "write_field_value",
        lambda config, **k: sf.substrate_writes.SubstrateWriteResult(
            ok=False, executed=True, detail="failed", error=stderr
        ),
    )
    write = sf.BoardWrite(
        axis="priority",
        field_name="Priority",
        field_id="F",
        option_name="High",
        option_id="O",
        item_id="I",
        project_id="P",
    )
    assert sf._write_board_field(write, {}) is False
    assert stderr in capsys.readouterr().err


def test_main_label_substrate_axis_still_succeeds(sf, tmp_path, monkeypatch, capsys) -> None:
    """Regression guard: with no board, the normal path is untouched — the label
    is written and the exit is 0."""
    root = _stage_capability_root(tmp_path, has_board=False)
    captured = _run_main(
        sf, monkeypatch, root=root, argv=["42", "--priority", "High"], issue=_TASK_ISSUE
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert captured["labels"] == [(["priority:High"], [])]
    assert "[ok] priority: set 'priority:High'" in out
    assert "updated" in out
    assert "[refused]" not in out


def test_main_idempotent_noop_still_reports_all_fields_set(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """The genuine no-op keeps its success summary — the new refusal path must not
    swallow the idempotent case (DEC-038: re-running is a no-op success)."""
    root = _stage_capability_root(tmp_path, has_board=False)
    issue = {"title": "[Task] do a thing", "body": "x\n", "labels": ["priority:High"]}
    captured = _run_main(sf, monkeypatch, root=root, argv=["42", "--priority", "High"], issue=issue)
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert "no change (all fields already set)" in out


def test_main_mixed_axes_applies_label_refuses_unresolvable_board(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """PARTIAL: `--kind` is always label-substrate (classification.yaml) while
    `--priority` is board-backed here and its card is missing. The label half IS
    applied, the board half is refused, the exit is non-zero, and the summary names
    both — a partial application must never read as a clean success."""
    root = _stage_capability_root(tmp_path, has_board=True)
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--kind", "bug", "--priority", "High"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf, item_id=None),
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 1
    # The label-substrate axis was genuinely applied (label + title realignment).
    assert captured["labels"] == [(["type:bug"], [])]
    assert captured["titles"] == ["[Bug] do a thing"]
    assert captured["board"] == []
    # ...and the summary says what was done and what was not.
    assert "[partial]" in out
    assert "applied kind, title" in out
    assert "REFUSED priority" in out
    assert "all fields already set" not in out


def test_main_mixed_axes_both_substrates_applied_is_a_clean_success(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """The mixed case when nothing fails: the `type:*` label AND the board field are
    both written in the one call, and the exit is 0."""
    root = _stage_capability_root(tmp_path, has_board=True)
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--kind", "bug", "--priority", "High"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf),
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert captured["labels"] == [(["type:bug"], [])]
    assert [w.axis for w in captured["board"]] == ["priority"]
    assert "[partial]" not in out
    assert "updated" in out


def test_main_map_binding_wins_over_the_board_flag(sf, tmp_path, monkeypatch, capsys) -> None:
    """The #708 config end-to-end: board flag on, substrate-map binds `priority` to
    the adopter's own labels. The binding governs — the adopter's label is written,
    the board is not touched, and the call succeeds. Before DEC-051 this was a
    refusal that recorded the value nowhere."""
    root = _stage_capability_root(tmp_path, has_board=True)
    (root / "project" / "substrate-map.yaml").write_text(
        "schema_version: 1\naxes:\n  priority:\n    label:\n      remap:\n        High: P0\n",
        encoding="utf-8",
    )
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--priority", "High"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf),
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert captured["labels"] == [(["P0"], [])]
    assert captured["board"] == []
    assert "[refused]" not in out


def test_main_label_bound_value_with_no_remap_entry_never_exits_zero(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """The posture DEC-051 decision point 5 requires be preserved on the path the
    inversion now enters: a value with no remap entry lands nowhere, so it is a
    refusal with a non-zero exit — never `no change (all fields already set)`."""
    root = _stage_capability_root(tmp_path, has_board=True)
    (root / "project" / "substrate-map.yaml").write_text(
        "schema_version: 1\naxes:\n  priority:\n    label:\n      remap:\n        Low: P2\n",
        encoding="utf-8",
    )
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--priority", "High"],
        issue=_TASK_ISSUE,
        board_state=_board_state(sf),
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 1
    assert captured["board"] == [] and captured["labels"] == []
    assert "NOT SET" in out
    assert "no change (all fields already set)" not in out


# --- --parent moves the native link with the first line (#1040) -------------
#
# The native half of `--parent` goes through the containment seam, whose one gh
# entry point (`containment._gh_call`) is replaced by `_NativeTracker` — an
# in-memory model of GitHub's native sub-issues, including its one-parent rule.
# The body/label/title writers are stubbed by `_run_main` as for every main test.

_ONE_PARENT_BODY = json.dumps(
    {
        "message": "Validation Failed",
        "errors": [{"field": "sub_issue_id", "message": "Sub issue may only have one parent"}],
        "status": "422",
    }
)
_DB = 1000  # a fake issue's database id is its number plus this


class _NativeTracker:
    """GitHub's native sub-issues, as the containment seam sees them.

    ``native`` maps a parent to its sub-issue numbers. ``honour_replace=False``
    refuses a move the way an instance without ``replace_parent`` would;
    ``record_error`` fails the issue-record read; ``unsupported`` answers every
    sub-issues call the way an instance without the feature does;
    ``refuse_add`` refuses every add with that ``(stdout, stderr)``.
    """

    def __init__(
        self,
        native: dict[int, set[int]] | None = None,
        *,
        honour_replace: bool = True,
        record_error: bool = False,
        unsupported: bool = False,
        refuse_add: tuple[str, str] | None = None,
    ) -> None:
        self.native = {p: set(c) for p, c in (native or {}).items()}
        self.honour_replace = honour_replace
        self.record_error = record_error
        self.unsupported = unsupported
        self.refuse_add = refuse_add
        self.calls: list[list[str]] = []

    @property
    def posts(self) -> list[list[str]]:
        return [c for c in self.calls if "POST" in c]

    def parent_of(self, child: int) -> int | None:
        return next((p for p, children in self.native.items() if child in children), None)

    def __call__(self, args, config):
        args = [str(a) for a in args]
        self.calls.append(args)
        path = next(a for a in args if a.startswith("repos/"))
        m = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)/sub_issues", path)
        if m:
            parent = int(m.group(1))
            if self.unsupported:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="gh: HTTP 410: Gone")
            if "POST" in args:
                return self._add(args, parent)
            listed = [{"id": _DB + n, "number": n} for n in sorted(self.native.get(parent, ()))]
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(listed), stderr="")
        m = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)", path)
        if m:
            if self.record_error:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="gh: HTTP 502")
            number = int(m.group(1))
            parent = self.parent_of(number)
            url = f"https://api.github.com/repos/o/r/issues/{parent}" if parent else ""
            stdout = f"{_DB + number}\n{url}\nhttps://api.github.com/repos/o/r\n"
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")
        raise AssertionError(f"unexpected gh call: {args}")

    def _add(self, args: list[str], parent: int) -> subprocess.CompletedProcess:
        if self.refuse_add is not None:
            stdout, stderr = self.refuse_add
            return subprocess.CompletedProcess(args, 1, stdout=stdout, stderr=stderr)
        child = int(args[args.index("-F") + 1].split("=", 1)[1]) - _DB
        holder = self.parent_of(child)
        moving = "replace_parent=true" in args and self.honour_replace
        if holder is not None and holder != parent and not moving:
            return subprocess.CompletedProcess(
                args, 1, stdout=_ONE_PARENT_BODY, stderr="gh: Validation Failed (HTTP 422)"
            )
        if holder is not None:
            self.native[holder].discard(child)
        self.native.setdefault(parent, set()).add(child)
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")


def _task_issue(body: str) -> dict:
    return {**_TASK_ISSUE, "body": body}


# The parent `--parent 9` names in these tests: a Feature, which a Task may sit under.
_FEATURE_9 = {9: {"title": "[Feature] the parent"}}


def _run_parent(sf, monkeypatch, tmp_path, *, native: _NativeTracker, body: str, extra=()):
    root = _stage_capability_root(tmp_path, has_board=False)
    monkeypatch.setattr(sf.containment, "_gh_call", native)
    return _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--parent", "9", *extra],
        issue=_task_issue(body),
        others=_FEATURE_9,
    )


def test_main_parent_moves_the_native_link_with_the_first_line(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """#42 names #7 on its first line and is natively under #7. `--parent 9`
    rewrites the line AND moves the link: #7 loses the child, #9 gains it, in
    one write that asks GitHub to replace the parent."""
    native = _NativeTracker({7: {42}})
    captured = _run_parent(
        sf, monkeypatch, tmp_path, native=native, body="Feature: #7\n\n## What\nx\n"
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert native.native == {7: set(), 9: {42}}
    assert len(native.posts) == 1 and native.posts[0][-2:] == ["-F", "replace_parent=true"]
    assert captured["bodies"] and captured["bodies"][0].startswith("Feature: #9\n")
    assert "parent: native link moves from #7 to #9" in out
    assert "moved #42 from #7 to #9 as a native sub-issue" in out


def _stage_with_shipped_types(tmp_path: Path) -> Path:
    """A staged capability root carrying the shipped `issue-types.yaml`."""
    root = _stage_capability_root(tmp_path, has_board=False)
    shipped = SCRIPTS.parent / "schemas" / "issue-types.yaml"
    (root / "schemas" / "issue-types.yaml").write_text(
        shipped.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return root


def _shipped_types() -> dict:
    from ruamel.yaml import YAML

    shipped = SCRIPTS.parent / "schemas" / "issue-types.yaml"
    return YAML(typ="safe").load(shipped.read_text(encoding="utf-8"))


_SHIPPED = _shipped_types()["types"]


def _prefix(structural_type: str) -> str:
    entry = _SHIPPED[structural_type]
    prefix = entry["title_prefix"]
    return prefix.upper() if entry.get("title_case") == "upper" else prefix


# Every pairing of a child type that takes an issue parent (an EPIC's `--parent`
# names a milestone) with a parent type, read from the shipped schema: refused
# where the parent type is not among the child's `parent_issue_types`.
_PAIRINGS = [
    (child, parent)
    for child, entry in sorted(_SHIPPED.items())
    if any(p != "milestone" for p in entry["parent_issue_types"])
    for parent in sorted(_SHIPPED)
]
_IMPOSSIBLE = [(c, p) for c, p in _PAIRINGS if p not in _SHIPPED[c]["parent_issue_types"]]
_ALLOWED = [(c, p) for c, p in _PAIRINGS if p in _SHIPPED[c]["parent_issue_types"]]


def _run_typed_parent(
    sf,
    monkeypatch,
    tmp_path,
    child: str,
    parent_title,
    extra=(),
    *,
    parent: dict | None = None,
    map_text: str | None = None,
):
    """`set-field 42 --parent 9` on a `child` issue, #9 answering `parent_title`
    (None: #9 cannot be read) — or the whole `parent` answer — against the
    shipped schema, under `map_text` as the substrate map where one is given."""
    root = _stage_with_shipped_types(tmp_path)
    if map_text is not None:
        (root / "project" / "substrate-map.yaml").write_text(
            f"schema_version: 1\n{map_text}", encoding="utf-8"
        )
    native = _NativeTracker()
    monkeypatch.setattr(sf.containment, "_gh_call", native)
    answer = (
        parent
        if parent is not None
        else (None if parent_title is None else {"title": parent_title})
    )
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--parent", "9", *extra],
        issue={**_TASK_ISSUE, "title": f"[{_prefix(child)}] the child"},
        others={9: answer},
    )
    return captured, native


def test_the_schema_defines_impossible_and_allowed_pairings() -> None:
    assert ("task", "task") in _IMPOSSIBLE and ("feature", "feature") in _IMPOSSIBLE
    assert ("task", "feature") in _ALLOWED


@pytest.mark.parametrize(("child", "parent"), _IMPOSSIBLE)
@pytest.mark.parametrize("extra", [(), ("--dry-run",)], ids=["write", "dry-run"])
def test_main_parent_of_a_type_the_child_may_not_sit_under_is_refused(
    sf, tmp_path, monkeypatch, capsys, child: str, parent: str, extra
) -> None:
    """#1313: DEC-005 refuses a re-parent that breaks the containment graph. The
    whole call is refused before anything is written — no body, no native read or
    link, no label — `--dry-run` alike, naming both types and the child's forms."""
    captured, native = _run_typed_parent(
        sf, monkeypatch, tmp_path, child, f"[{_prefix(parent)}] the parent", extra
    )
    out, err = capsys.readouterr()

    assert captured["rc"] == 1
    assert captured["bodies"] == [] and captured["labels"] == []
    assert native.calls == [], "nothing native is read or written"
    a_child = f"{'an' if child[0] in 'aeiou' else 'a'} {child}"
    a_parent = f"{'an' if parent[0] in 'aeiou' else 'a'} {parent}"
    assert (
        f"[refused] cannot set --parent: {a_child} may not sit under #9, which is {a_parent}"
    ) in out
    assert f"`{_SHIPPED[child]['parent_ref_form']}`" in out
    assert "validation failed before any mutation; nothing written" in err


@pytest.mark.parametrize(("child", "parent"), _ALLOWED)
def test_main_parent_of_a_type_the_child_may_sit_under_is_named_by_its_own_label(
    sf, tmp_path, monkeypatch, capsys, child: str, parent: str
) -> None:
    """#1281: the first line carries the parent's own label — a Task set under an
    Umbrella reads `Umbrella: #9`, not the form's first option — and the native
    link follows, with nothing to warn of."""
    captured, native = _run_typed_parent(
        sf, monkeypatch, tmp_path, child, f"[{_prefix(parent)}] the parent"
    )

    assert captured["rc"] == 0
    assert captured["bodies"][0].startswith(f"{_prefix(parent)}: #9\n")
    assert native.posts, "the native link is made"
    assert "[warn]" not in capsys.readouterr().out


def test_main_parent_whose_type_cannot_be_told_is_named_in_the_first_form_with_a_warning(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """An untyped parent is outside the containment graph: accepted, named in the
    form's first option, with a warning that nothing was checked — so a legacy
    tree stays linkable."""
    captured, native = _run_typed_parent(sf, monkeypatch, tmp_path, "task", "no type prefix")

    assert captured["rc"] == 0
    assert captured["bodies"][0].startswith("Feature: #9\n")
    assert native.posts
    assert (
        "  [warn] parent: #9's type cannot be told, so whether a task may sit under it "
        "was not checked (an issue whose type cannot be told is outside the containment graph)"
    ) in capsys.readouterr().out


@pytest.mark.parametrize("extra", [(), ("--dry-run",)], ids=["write", "dry-run"])
def test_main_parent_that_cannot_be_read_is_refused(
    sf, tmp_path, monkeypatch, capsys, extra
) -> None:
    """A parent that cannot be read cannot be checked, so the call is refused
    before anything is written."""
    captured, native = _run_typed_parent(sf, monkeypatch, tmp_path, "task", None, extra)
    out = capsys.readouterr().out

    assert captured["rc"] == 1
    assert captured["bodies"] == [] and native.calls == []
    assert (
        '[refused] cannot set --parent: #9 could not be read (gh exited 1. gh said: "HTTP '
        '502: Bad Gateway"), so whether a task may sit under it cannot be checked'
    ) in out


def test_main_parent_naming_a_pull_request_is_refused(sf, tmp_path, monkeypatch, capsys) -> None:
    """A pull request is no parent: the whole call is refused, exit 1, nothing
    written, and the message says what the number names."""
    captured, native = _run_typed_parent(
        sf, monkeypatch, tmp_path, "task", None, parent={"not_an_issue": True}
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 1
    assert captured["bodies"] == [] and native.calls == []
    assert (
        "[refused] cannot set --parent: #9 is not an issue in this repository — #9 is a "
        "pull request — so a task cannot sit under it"
    ) in out


def test_main_parent_untitled_but_kind_labelled_is_a_task_in_greenfield(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    captured, _native = _run_typed_parent(
        sf,
        monkeypatch,
        tmp_path,
        "task",
        None,
        parent={"title": "Login crashes", "labels": [{"name": "type:bug"}]},
    )

    assert captured["rc"] == 1
    assert "a task may not sit under #9, which is a task" in capsys.readouterr().out


_STORY_MAP = (
    "axes:\n  type:\n    title-prefix:\n      remap: {feature: '[Story]', task: '[Task]'}\n"
)
_TYPE_BY_LABEL_MAP = "axes:\n  type:\n    label:\n      remap: {bug: 'kind/bug'}\n"


@pytest.mark.parametrize(
    ("parent_title", "verdict"),
    [("[Task] another task", "refused"), ("[Story] a story", "allowed")],
)
def test_main_parent_under_a_story_map_is_typed_by_the_maps_prefixes(
    sf, tmp_path, monkeypatch, capsys, parent_title, verdict
) -> None:
    """Under a map binding `type` to `[Story]` / `[Task]`, both types are told by
    the map's prefixes: a Task under a `[Task]` is refused, under a `[Story]` — a
    Feature — it is set and named `Feature: #9`."""
    captured, _native = _run_typed_parent(
        sf, monkeypatch, tmp_path, "task", parent_title, map_text=_STORY_MAP
    )
    out = capsys.readouterr().out

    if verdict == "refused":
        assert captured["rc"] == 1
        assert "a task may not sit under #9, which is a task" in out
    else:
        assert captured["rc"] == 0
        assert captured["bodies"][0].startswith("Feature: #9\n")
        assert "[warn]" not in out


@pytest.mark.parametrize(
    "parent",
    [
        {"title": "[Bug] Login crashes"},
        {"title": "Login crashes", "labels": [{"name": "type:bug"}]},
    ],
    ids=["kind-prefixed", "kind-labelled"],
)
def test_main_parent_under_a_map_not_carrying_type_in_titles_is_not_refused(
    sf, tmp_path, monkeypatch, capsys, parent
) -> None:
    """A map whose `type` is not title-carried tells no type — not the issue's,
    not the parent's: the kit's prefixes and labels are not read on a mapped
    tracker, so the pair is outside the graph, set with one warning."""
    captured, _native = _run_typed_parent(
        sf, monkeypatch, tmp_path, "task", None, parent=parent, map_text=_TYPE_BY_LABEL_MAP
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert out.count("[warn] parent:") == 1
    assert "this issue's type cannot be told, so whether it may sit under #9 was not checked" in out


def test_main_parent_refusal_refuses_the_whole_request(sf, tmp_path, monkeypatch) -> None:
    """Validation is up front for every field (DEC-038): a refused parent leaves a
    priority asked for in the same call unwritten too."""
    captured, _native = _run_typed_parent(
        sf, monkeypatch, tmp_path, "task", "[Bug] a kind-prefixed task", ("--priority", "High")
    )

    assert captured["rc"] == 1
    assert captured["labels"] == [] and captured["bodies"] == []


def test_main_parent_on_an_epic_names_a_milestone_and_says_so(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """An EPIC's container is a milestone: `--parent 9` writes `Milestone: #9`,
    which names milestone 9 and no issue, so the warning says the line names
    milestone 9, not issue #9 — and no issue #9 is read or linked."""
    root = _stage_with_shipped_types(tmp_path)
    native = _NativeTracker()
    monkeypatch.setattr(sf.containment, "_gh_call", native)

    class _Reads(dict):
        """Every issue number read, through `_run_main`'s `others`."""

        def __init__(self, answers: dict) -> None:
            super().__init__(answers)
            self.numbers: list[int] = []

        def get(self, key, default=None):
            self.numbers.append(key)
            return super().get(key, default)

    reads = _Reads({9: {"title": "[Umbrella] an issue numbered like the milestone"}})
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--parent", "9"],
        issue={**_TASK_ISSUE, "title": "[EPIC] a thesis"},
        others=reads,
    )

    assert captured["rc"] == 0
    assert 9 not in reads.numbers, "an EPIC's number is a milestone's: issue #9 is not read"
    assert captured["bodies"][0].startswith("Milestone: #9\n")
    out = capsys.readouterr().out
    assert (
        "  [warn] parent: this type's container is a milestone, never an issue "
        "(Milestone: [#<N>](../milestone/<N>)), so the first line `Milestone: #9` names "
        "milestone 9, not issue #9.\n"
    ) in out
    assert native.calls == [], "a milestone is not a sub-issue parent: nothing native is read"


def test_main_parent_on_a_marked_body_keeps_the_marker_first(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """#765: a marked descendant re-parented through the verb keeps its DEC-013
    marker as the first line, the new parent-ref directly below it."""
    native = _NativeTracker({7: {42}})
    body = "Integration: integration/foo\nFeature: #7\n\n## What\nx\n"
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body=body)

    assert captured["rc"] == 0
    assert native.native == {7: set(), 9: {42}}
    assert captured["bodies"][0].startswith(
        "Integration: integration/foo\nFeature: #9\n\n## What\nx\n"
    )


@pytest.mark.parametrize(
    "first_line",
    [
        "Integration: integration/Foo_Bar!!",
        "Integration:integration/foo",
        "Integration: #7",
    ],
    ids=["bad-slug", "no-space-after-key", "parent-ref-shaped"],
)
@pytest.mark.parametrize("extra", [(), ("--dry-run",)], ids=["write", "dry-run"])
def test_main_parent_on_a_malformed_marker_refuses_and_writes_nothing(
    sf, tmp_path, monkeypatch, capsys, first_line, extra
) -> None:
    """A first line that attempts the DEC-013 marker but is malformed is not
    skipped as one, so a parent-ref written above it would move it off the first
    line, past validate-issue's hard-reject. The verb refuses up front instead:
    it names the line and the required form, exits 1, and touches neither the
    body nor the native link — it does not even read the native parent."""
    native = _NativeTracker({7: {42}})
    body = f"{first_line}\nFeature: #7\n\n## What\nx\n"
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body=body, extra=extra)
    out, err = capsys.readouterr()

    assert captured["rc"] == 1
    assert native.calls == [] and captured["bodies"] == []
    assert native.native == {7: {42}}
    assert (
        f"[refused] cannot set --parent: the first body line {first_line!r} looks like a "
        "DEC-013 integration marker but does not match the required form "
        "`Integration: integration/<slug>`"
    ) in out
    assert "validation failed before any mutation; nothing written" in err


def test_main_parent_on_a_valid_marker_is_not_refused(sf, tmp_path, monkeypatch, capsys) -> None:
    """The refusal is for a malformed marker only: a body opening with a valid one,
    after leading blank lines, is re-parented below it as before."""
    native = _NativeTracker({7: {42}})
    body = "\n\nIntegration: integration/foo\nFeature: #7\n\n## What\nx\n"
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body=body)

    assert captured["rc"] == 0
    assert "[refused]" not in capsys.readouterr().out
    assert captured["bodies"][0].startswith(
        "\n\nIntegration: integration/foo\nFeature: #9\n\n## What\nx\n"
    )


def test_main_parent_prepended_over_leading_blank_lines_adds_no_extra_blank_line(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """An unmarked body with leading blank lines and no parent-ref gets the
    parent-ref as its first line and exactly one blank line before its content."""
    native = _NativeTracker()
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="\n\n\n## What\nx\n")

    assert captured["rc"] == 0
    assert captured["bodies"][0].startswith("Feature: #9\n\n## What\nx\n")


def test_main_parent_dry_run_plans_the_move_and_writes_nothing(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    native = _NativeTracker({7: {42}})
    captured = _run_parent(
        sf, monkeypatch, tmp_path, native=native, body="Feature: #7\n", extra=("--dry-run",)
    )
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert native.posts == [] and captured["bodies"] == []
    assert native.native == {7: {42}}
    assert "parent: native link moves from #7 to #9" in out


def test_main_parent_refused_move_writes_nothing_and_names_the_kept_parent(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """GitHub refuses the move: the call stops before the first line is
    rewritten, so the two records are left as they were, and it says where the
    issue stays."""
    native = _NativeTracker({7: {42}}, honour_replace=False)
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="Feature: #7\n")
    out = capsys.readouterr().out

    assert captured["rc"] == 3
    assert captured["bodies"] == [], "the first line must not move without the link"
    assert native.native == {7: {42}}
    assert "[failed] #42: parent NOT set — #42 could not be moved to #9" in out
    assert "it stays a native sub-issue of #7" in out
    assert 'GitHub said: "Validation Failed; Sub issue may only have one parent"' in out
    assert "containment: textual" not in out, "a conflict is not a refusal to work around"


def test_main_parent_unreadable_native_parent_refuses_before_any_write(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    native = _NativeTracker({7: {42}}, record_error=True)
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="Feature: #7\n")
    out = capsys.readouterr().out

    assert captured["rc"] == 1
    assert native.posts == [] and captured["bodies"] == []
    assert "native parent could not be read" in out


def test_main_parent_right_first_line_but_link_elsewhere_moves_only_the_link(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """The first line already names #9 but the native link sits under #7 — the
    disagreement #1040 is about. The call is not a no-op: it moves the link."""
    native = _NativeTracker({7: {42}})
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="Feature: #9\n")

    assert captured["rc"] == 0
    assert native.native == {7: set(), 9: {42}}
    assert captured["bodies"] == []


def test_main_parent_already_in_agreement_is_a_no_op(sf, tmp_path, monkeypatch, capsys) -> None:
    native = _NativeTracker({9: {42}})
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="Feature: #9\n")
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert native.posts == [] and captured["bodies"] == []
    assert "no change (all fields already set)" in out


def test_main_parent_without_a_native_parent_adds_the_link(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    native = _NativeTracker()
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="## What\nx\n")

    assert captured["rc"] == 0
    assert native.native == {9: {42}}
    assert "replace_parent=true" not in native.posts[0]
    assert captured["bodies"][0].startswith("Feature: #9\n")


def test_main_parent_on_an_instance_without_sub_issues_rewrites_the_first_line(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    native = _NativeTracker(unsupported=True)
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="## What\nx\n")
    out = capsys.readouterr().out

    assert captured["rc"] == 0
    assert captured["bodies"][0].startswith("Feature: #9\n")
    assert (
        "[warn] native sub-issues unsupported on this instance; the first line alone "
        "records the parent"
    ) in out


_WAY_OUT = (
    "  → If this GitHub does not offer sub-issues, set `containment: textual` in "
    "project/substrate-map.yaml and pm stops attempting the native link."
)


def test_main_parent_a_422_stops_before_any_write(sf, tmp_path, monkeypatch, capsys) -> None:
    """#808: a 422 used to read as "unsupported", so an issue with no native
    parent had its first line rewritten while the link silently failed. A 422
    is a failure: the call stops before the first line moves, GitHub's words
    are printed, and the refusal does not also claim a textual ref was recorded
    — nothing was written. The textual-mode way out follows."""
    refusal = json.dumps({"message": "Parent issue is locked", "status": "422"})
    native = _NativeTracker(refuse_add=(refusal, "gh: Parent issue is locked (HTTP 422)"))
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="## What\nx\n")
    out = capsys.readouterr().out

    assert captured["rc"] == 3
    assert captured["bodies"] == [], "the first line must not move without the link"
    assert (
        "[failed] #42: parent NOT set — GitHub refused to link #42 under #9 (HTTP 422) "
        'for a reason pm does not recognise. GitHub said: "Parent issue is locked". '
        "Nothing was written: the first line and the native link are as they were."
    ) in out
    assert "textual ref recorded" not in out
    assert "unsupported" not in out
    assert _WAY_OUT in out


def test_main_parent_a_move_refused_by_an_unrelated_422_is_no_conflict(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """#42 is natively under #7 and `--parent 9` moves it. GitHub refuses the
    move with a 422 unrelated to the one-parent rule: the parent #42 has is the
    move's precondition, not a finding, so the report is the failure GitHub
    stated — not a conflict telling the operator to remove a link first."""
    unrelated = "Validation failed, or the endpoint has been spammed."
    refusal = json.dumps({"message": unrelated, "status": "422"})
    native = _NativeTracker({7: {42}}, refuse_add=(refusal, "gh: Validation Failed (HTTP 422)"))
    captured = _run_parent(sf, monkeypatch, tmp_path, native=native, body="Feature: #7\n")
    out = capsys.readouterr().out

    assert captured["rc"] == 3
    assert captured["bodies"] == []
    assert native.native == {7: {42}}
    assert "[failed] #42: parent NOT set — GitHub refused to move #42 to #9 (HTTP 422)" in out
    assert f'GitHub said: "{unrelated}"' in out
    assert "must be removed first" not in out
    assert _WAY_OUT in out


def test_main_parent_in_textual_containment_writes_no_native_link(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    root = _stage_capability_root(tmp_path, has_board=False)
    (root / "project" / "substrate-map.yaml").write_text(
        "schema_version: 1\naxes: {}\ncontainment: textual\n", encoding="utf-8"
    )
    native = _NativeTracker({7: {42}})
    monkeypatch.setattr(sf.containment, "_gh_call", native)
    captured = _run_main(
        sf,
        monkeypatch,
        root=root,
        argv=["42", "--parent", "9"],
        issue=_task_issue("Feature: #7\n"),
        others=_FEATURE_9,
    )

    assert captured["rc"] == 0
    assert native.calls == [], "textual containment reads and writes no native link"
    assert captured["bodies"][0].startswith("Feature: #9\n")


def test_main_parent_naming_the_issue_itself_is_refused(sf, tmp_path, monkeypatch, capsys) -> None:
    root = _stage_capability_root(tmp_path, has_board=False)
    native = _NativeTracker()
    monkeypatch.setattr(sf.containment, "_gh_call", native)
    captured = _run_main(
        sf, monkeypatch, root=root, argv=["42", "--parent", "42"], issue=_task_issue("")
    )

    assert captured["rc"] == 1
    assert native.calls == [] and captured["bodies"] == []
    assert "cannot be its own parent" in capsys.readouterr().out
