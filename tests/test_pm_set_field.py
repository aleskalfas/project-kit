"""Tests for set-field's pure planning logic (no network) + its exit contract.

Covers label resolution + idempotent diff for priority/workstream, the
parent-ref body rewrite (replace / prepend / no-op), value-vocabulary reads,
the BOARD single-select write (#724 — name → id resolution, and the five
refusals that each name what the board actually offers), and the honesty posture
inherited from #709: a requested axis that was not written is `[refused]` with a
non-zero exit, never `[ok]`, while the label-substrate path and the partial
(mixed-axes) case stay legible.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "set-field.py"
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
    assert sf._adopter_workstreams(
        {"workstreams": {"cli": {}, "docs": {}}}
    ) == {"cli", "docs"}


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
    results, add, remove = sf._plan_labels(
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
    results, add, remove = sf._plan_labels(
        priority="Medium",
        workstream="cli",
        current_labels=[],
        substrate_map=None,
    )
    assert set(add) == {"priority:Medium", "workstream:cli"}


# --- axis routing: which substrate owns the axis (#724) ----------------------
#
# The routing predicate is deliberately the SAME pair pre-check's cross-substrate
# conflict check keys on (`has_projects_v2_board` × `axis_is_label_bound`), so the
# writer and the gate cannot disagree about where an axis lives.


def test_route_axes_no_board_sends_everything_to_labels(sf) -> None:
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream="cli",
        has_board=False,
        substrate_map=None,
    )
    assert label_axes == {"priority": "High", "workstream": "cli"}
    assert board_axes == {}
    assert results == []


def test_route_axes_board_claims_priority_and_workstream(sf) -> None:
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream="cli",
        has_board=True,
        substrate_map=None,
    )
    assert board_axes == {"priority": "High", "workstream": "cli"}
    assert label_axes == {}
    assert results == []


def test_route_axes_label_bound_axis_under_a_board_is_the_two_claimant_refusal(
    sf, axis_labels
) -> None:
    """The #708 root cause: config says board, the map binds the axis to a label.
    set-field refuses rather than picking a winner (that is #712's call) — and says
    the value went nowhere, keeping #709's posture."""
    sm = axis_labels.SubstrateMap(axes={"priority": {"label": {"High": "P0"}}})
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream=None,
        has_board=True,
        substrate_map=sm,
        board_id=7,
    )
    assert label_axes == {} and board_axes == {}
    refusal = next(r for r in results if r.field == "priority")
    assert refusal.ok is False and refusal.changed is False
    assert "TWO SUBSTRATES" in refusal.message
    assert "NOT SET" in refusal.message
    assert "#7" in refusal.message
    assert "pre-check" in refusal.message


def test_route_axes_mixed_map_splits_the_two_axes(sf, axis_labels) -> None:
    """Only the label-bound axis is diverted; a board-claimed sibling still routes
    to the board."""
    sm = axis_labels.SubstrateMap(
        axes={"priority": {"label": {"High": "P0"}}, "workstream": {"unsupported": True}}
    )
    label_axes, board_axes, results = sf._route_axes(
        priority="High",
        workstream="cli",
        has_board=True,
        substrate_map=sm,
    )
    assert board_axes == {"workstream": "cli"}
    assert label_axes == {}
    assert [r.field for r in results] == ["priority"]


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
    _, writes = sf._plan_board_fields(
        board_axes={"priority": "High"}, state=state, issue_number=42
    )
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


def test_unsupported_axis_under_map_is_still_a_note_not_a_refusal(sf, axis_labels) -> None:
    """Scope guard: an axis the adopter explicitly declared `unsupported` has
    nowhere to write BY DECLARATION — that stays a note (`ok=True`), unchanged by
    #709, which is about the board/label DISAGREEMENT."""
    sm = axis_labels.SubstrateMap(axes={"priority": {"unsupported": True}})
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=[],
        substrate_map=sm,
    )
    assert add == [] and remove == []
    assert next(r for r in results if r.field == "priority").ok is True


def test_field_list_dedupes_and_preserves_order(sf) -> None:
    fr = sf.FieldResult
    listed = sf._field_list([
        fr(field="kind", ok=True, changed=True, message=""),
        fr(field="title", ok=True, changed=True, message=""),
        fr(field="kind", ok=True, changed=False, message=""),
    ])
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


def test_plan_kind_swaps_label_and_realigns_prefix(
    sf, issue_types, classification
) -> None:
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


def test_plan_kind_prefix_already_correct_is_noop(
    sf, issue_types, classification
) -> None:
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


def test_plan_kind_idempotent_when_label_and_prefix_match(
    sf, issue_types, classification
) -> None:
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


def test_plan_kind_feature_on_feature_issue_is_full_noop(
    sf, issue_types, classification
) -> None:
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


def test_kind_composes_with_priority_workstream_batch(
    sf, issue_types, classification
) -> None:
    # The aggregate add/remove main builds: kind swap + priority + workstream in
    # one batch, all label writes against a single edit call.
    current = ["type:maintenance", "priority:Low"]
    k_results, k_add, k_remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Chore] mislabelled defect",
        current_labels=current,
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    a_results, a_add, a_remove = sf._plan_labels(
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
    new_body, result = sf._plan_parent(body, "EPIC: #3")
    # The existing first line is a recognised parent-ref, so it is REPLACED
    # (not prepended-before).
    assert new_body.startswith("EPIC: #3\n")
    assert "Milestone:" not in new_body.splitlines()[0]


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
    assert not sf._is_parent_ref("## What")
    assert not sf._is_parent_ref("just prose")


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
        lambda config, owner=None, gh_call=None: project
        or bf.ProjectLookup(ok=True, node_id="PVT_board7"),
    )
    monkeypatch.setattr(
        bf,
        "read_fields",
        lambda config, owner=None, gh_call=None: fields_read
        or bf.BoardFieldsRead(ok=True, fields=({"id": "F", "name": "Priority"},)),
    )
    monkeypatch.setattr(
        bf,
        "resolve_item_id",
        lambda config, issue_node_id, project_node_id, gh_call=None: item
        or bf.ItemLookup(ok=True, item_id="PVTI_card42"),
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
        "gh project item-add 7 --owner an-org "
        "--url https://github.com/an-org/r/issues/42"
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


def test_read_board_state_without_an_issue_node_id_is_an_error_not_a_guess(
    sf, monkeypatch
) -> None:
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
        "  task:\n"
        "    title_prefix: Task\n"
        "    title_case: title\n"
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
) -> dict:
    """Drive `sf.main()` with the gh seams stubbed; return rc + captured writes.

    `board_state` stubs the board READ (its own tests cover the orchestration), so
    a main() test states the board situation as data. Board writes are captured
    rather than issued; `board_write_ok=False` makes the write fail at the point of
    writing (the exit-3 path).
    """
    captured: dict = {"labels": [], "titles": [], "bodies": [], "board": []}

    monkeypatch.setattr(sf, "gh_get_issue", lambda *a, **k: issue)
    if board_state is not None:
        monkeypatch.setattr(
            sf, "_read_board_state", lambda config, **k: board_state
        )

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


def test_main_board_axis_writes_the_board_single_select(
    sf, tmp_path, monkeypatch, capsys
) -> None:
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


def test_write_board_field_routes_through_the_substrate_write_seam(
    sf, monkeypatch
) -> None:
    """ADR-031: the field-value write is obtained from `substrate_writes`, never
    string-built here — the same primitive the `set-board-field` hook uses."""
    seen: dict = {}

    def fake_write_field_value(config, **kwargs):
        seen.update(kwargs)
        return sf.substrate_writes.SubstrateWriteResult(
            ok=True, executed=True, detail="set"
        )

    monkeypatch.setattr(
        sf.substrate_writes, "write_field_value", fake_write_field_value
    )
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


def test_write_board_field_failure_prints_gh_stderr_verbatim(
    sf, monkeypatch, capsys
) -> None:
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


def test_main_label_substrate_axis_still_succeeds(
    sf, tmp_path, monkeypatch, capsys
) -> None:
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
    captured = _run_main(
        sf, monkeypatch, root=root, argv=["42", "--priority", "High"], issue=issue
    )
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


def test_main_two_claimant_conflict_refuses_and_writes_nothing(
    sf, tmp_path, monkeypatch, capsys
) -> None:
    """The #708 config: board flag on, substrate-map binds `priority` to a label.
    set-field refuses the axis (it will not pick a winner), writes nothing, and
    points at pre-check."""
    root = _stage_capability_root(tmp_path, has_board=True)
    (root / "project" / "substrate-map.yaml").write_text(
        "schema_version: 1\naxes:\n  priority:\n    label:\n      High: P0\n",
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
    assert "TWO SUBSTRATES" in out
    assert "pre-check" in out
