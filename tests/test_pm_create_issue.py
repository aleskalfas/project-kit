"""Tests for project-management's create-issue script's pure logic.

Covers title composition, parent-ref line formatting, template body
substitution, frontmatter stripping, adopter-workstream extraction.
The gh subprocess invocations are not tested at unit level — they're
thin wrappers; their behaviour is the same shape as evidence's
validate.py call path.
"""

from __future__ import annotations

import importlib.util
import json
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
    / "create-issue.py"
)


@pytest.fixture(scope="module")
def ci():
    """Load create-issue.py as a module via importlib."""
    module_name = "pm_create_issue_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cr(ci):
    # The kind ↔ structural / kind-drives-title predicates now live in _lib
    # (extracted per COR-007 / issue #410). Loading create-issue puts SCRIPTS on
    # sys.path, so _lib is importable here.
    from _lib import classification_rules

    return classification_rules


# --- classification-faithful title prefix (#356, defect 2) -----------------
# The real schemas drive these — a task's prefix follows the kind label; the
# non-task structural types ignore kind and use their structural prefix.

_CLASSIFICATION = {
    "axes": {
        "type": {
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


def test_title_prefix_task_bug_kind_yields_bug(ci) -> None:
    """A `--kind bug` Task is prefixed `[Bug]`, not `[Task]` (the core of #356)."""
    type_entry = {"title_prefix": "Task", "title_case": "title"}
    assert (
        ci._title_prefix_for(type_entry, _CLASSIFICATION, "task", "bug") == "Bug"
    )


def test_title_prefix_task_feature_kind_yields_task(ci) -> None:
    type_entry = {"title_prefix": "Task", "title_case": "title"}
    assert (
        ci._title_prefix_for(type_entry, _CLASSIFICATION, "task", "feature") == "Task"
    )


def test_title_prefix_task_each_kind_maps_to_its_prefix(ci) -> None:
    type_entry = {"title_prefix": "Task", "title_case": "title"}
    expected = {
        "docs": "Docs",
        "test": "Test",
        "refactor": "Refactor",
        "maintenance": "Chore",
    }
    for kind, prefix in expected.items():
        assert (
            ci._title_prefix_for(type_entry, _CLASSIFICATION, "task", kind) == prefix
        )


def test_title_prefix_epic_ignores_kind_uses_structural_upper(ci) -> None:
    """EPIC is not kind-driven: kind defaults to feature, prefix stays `EPIC`
    (uppercased), NOT `Task` (what title_prefix_by_value['feature'] would give)."""
    type_entry = {"title_prefix": "EPIC", "title_case": "upper"}
    assert (
        ci._title_prefix_for(type_entry, _CLASSIFICATION, "epic", "feature") == "EPIC"
    )


def test_title_prefix_feature_and_umbrella_ignore_kind(ci) -> None:
    feature_entry = {"title_prefix": "Feature", "title_case": "title"}
    umbrella_entry = {"title_prefix": "Umbrella", "title_case": "title"}
    assert (
        ci._title_prefix_for(feature_entry, _CLASSIFICATION, "feature", "feature")
        == "Feature"
    )
    assert (
        ci._title_prefix_for(umbrella_entry, _CLASSIFICATION, "umbrella", "feature")
        == "Umbrella"
    )


def test_title_prefix_degrades_to_structural_on_empty_classification(ci) -> None:
    """Absent classification ⇒ structural prefix (no crash, no kind-driving)."""
    type_entry = {"title_prefix": "Task", "title_case": "title"}
    assert ci._title_prefix_for(type_entry, {}, "task", "bug") == "Task"


def test_kind_drives_title_true_only_for_task(cr) -> None:
    assert cr.kind_drives_title("task", _CLASSIFICATION) is True
    assert cr.kind_drives_title("epic", _CLASSIFICATION) is False
    assert cr.kind_drives_title("feature", _CLASSIFICATION) is False
    assert cr.kind_drives_title("umbrella", _CLASSIFICATION) is False


# --- parent-type detection + label (#356, defect 1) ------------------------


def _ISSUE_TYPES() -> dict:
    return {
        "types": {
            "epic": {"title_prefix": "EPIC", "title_case": "upper"},
            "feature": {"title_prefix": "Feature", "title_case": "title"},
            "umbrella": {"title_prefix": "Umbrella", "title_case": "title"},
            "task": {"title_prefix": "Task", "title_case": "title"},
        }
    }


def test_infer_structural_type_from_title_prefix(ci) -> None:
    types = _ISSUE_TYPES()
    assert ci._infer_structural_type("[EPIC] Big thesis", types) == "epic"
    assert ci._infer_structural_type("[Feature] A capability", types) == "feature"
    assert ci._infer_structural_type("[Umbrella] A bucket", types) == "umbrella"
    assert ci._infer_structural_type("[Bug] something", types) is None  # not a prefix
    assert ci._infer_structural_type("no prefix at all", types) is None


def test_parent_ref_label_matches_parent_type(ci) -> None:
    types = _ISSUE_TYPES()
    assert ci._parent_ref_label(types, "epic") == "EPIC"
    assert ci._parent_ref_label(types, "feature") == "Feature"
    assert ci._parent_ref_label(types, "umbrella") == "Umbrella"
    assert ci._parent_ref_label(types, "nonsense") is None


def test_parent_ref_line_uses_detected_parent_label(ci) -> None:
    """A Task under an EPIC emits `EPIC: #N`, not the first parent_ref_form label."""
    type_entry = {
        "parent_ref_form": "Feature: #<N> or Umbrella: #<N> or EPIC: #<N>",
    }
    assert (
        ci._parent_ref_line(type_entry, 128, parent_label="EPIC") == "EPIC: #128"
    )


def test_parent_ref_line_label_none_falls_back_to_first_option(ci) -> None:
    """Undetectable parent type degrades to the first parent_ref_form label."""
    type_entry = {
        "parent_ref_form": "Feature: #<N> or Umbrella: #<N> or EPIC: #<N>",
    }
    assert ci._parent_ref_line(type_entry, 128, parent_label=None) == "Feature: #128"


def test_detect_parent_structural_type_reads_title_and_infers(ci, monkeypatch) -> None:
    class _Proc:
        returncode = 0
        stdout = '{"title": "[EPIC] A grand thesis"}'
        stderr = ""

    monkeypatch.setattr(ci.subprocess, "run", lambda *a, **k: _Proc())
    assert (
        ci._detect_parent_structural_type(128, {}, _ISSUE_TYPES()) == "epic"
    )


def test_detect_parent_structural_type_none_on_gh_failure(ci, monkeypatch) -> None:
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(ci.subprocess, "run", lambda *a, **k: _Proc())
    assert ci._detect_parent_structural_type(128, {}, _ISSUE_TYPES()) is None


def test_detect_parent_structural_type_none_on_non_json(ci, monkeypatch) -> None:
    class _Proc:
        returncode = 0
        stdout = "not json"
        stderr = ""

    monkeypatch.setattr(ci.subprocess, "run", lambda *a, **k: _Proc())
    assert ci._detect_parent_structural_type(128, {}, _ISSUE_TYPES()) is None


# --- body-file first-line acceptance (#356, criterion 5) -------------------


def test_parent_ref_form_matchers_accept_each_allowed_option(ci) -> None:
    form = (
        "Feature: #<N> or Umbrella: #<N> or EPIC: #<N>"
        " or Milestone: [#<N>](../milestone/<N>)"
    )
    matchers = ci._parent_ref_form_matchers(form)

    def accepted(line: str) -> bool:
        return any(m.match(line) for m in matchers)

    # Every allowed form for the type is accepted as-is.
    assert accepted("Feature: #1")
    assert accepted("Umbrella: #2")
    assert accepted("EPIC: #128")
    assert accepted("Milestone: [#6](../milestone/6)")
    # Shapes the validator rejects are not accepted.
    assert not accepted("EPIC: 128")  # missing the `#`
    assert not accepted("Milestone: [#6](../milestone/9)")  # mismatched back-ref
    assert not accepted("just prose")


# --- parent-ref line --------------------------------------------------


def test_parent_ref_line_single_parent_type(ci) -> None:
    type_entry = {
        "parent_ref_form": "Feature: #<N>",
    }
    assert ci._parent_ref_line(type_entry, 42) == "Feature: #42"


def test_parent_ref_line_alternative_parents_picks_first(ci) -> None:
    type_entry = {
        "parent_ref_form": "EPIC: #<N> or Umbrella: #<N>",
    }
    assert ci._parent_ref_line(type_entry, 7) == "EPIC: #7"


def test_parent_ref_line_three_alternatives_picks_first(ci) -> None:
    type_entry = {
        "parent_ref_form": "Feature: #<N> or Umbrella: #<N> or EPIC: #<N>",
    }
    assert ci._parent_ref_line(type_entry, 99) == "Feature: #99"


def test_parent_ref_line_empty_when_no_parent_given(ci) -> None:
    type_entry = {"parent_ref_form": "Feature: #<N>"}
    assert ci._parent_ref_line(type_entry, None) == ""


def test_parent_ref_line_milestone_emits_link_form(ci) -> None:
    """When milestone_num is given and milestone is a valid parent, emit the link form."""
    type_entry = {
        "parent_issue_types": ["feature", "umbrella", "epic", "milestone"],
        "parent_ref_form": (
            "Feature: #<N> or Umbrella: #<N> or EPIC: #<N>"
            " or Milestone: [#<N>](../milestone/<N>)"
        ),
    }
    result = ci._parent_ref_line(type_entry, parent_num=None, milestone_num=6)
    assert result == "Milestone: [#6](../milestone/6)"


def test_parent_ref_line_milestone_ignored_when_not_a_valid_parent(ci) -> None:
    """When milestone is not in parent_issue_types, milestone_num has no effect."""
    type_entry = {
        "parent_issue_types": ["epic"],
        "parent_ref_form": "EPIC: #<N>",
    }
    # Both parent_num and milestone_num given — parent_num wins because
    # milestone is not a valid parent for this type.
    result = ci._parent_ref_line(type_entry, parent_num=3, milestone_num=6)
    assert result == "EPIC: #3"


def test_parent_ref_line_milestone_preferred_over_parent_when_both_given(ci) -> None:
    """milestone_num takes priority when milestone is a valid parent."""
    type_entry = {
        "parent_issue_types": ["epic", "milestone"],
        "parent_ref_form": "EPIC: #<N> or Milestone: [#<N>](../milestone/<N>)",
    }
    result = ci._parent_ref_line(type_entry, parent_num=3, milestone_num=6)
    assert result == "Milestone: [#6](../milestone/6)"


def test_compose_body_substitutes_milestone_link_form(ci, tmp_path: Path) -> None:
    """compose_body replaces the `Milestone: #` placeholder with the link form."""
    template = tmp_path / "EPIC.md"
    template.write_text(
        "---\nname: EPIC\n---\n"
        "Milestone: #\n\n"
        "## Outcome\nfoo\n",
        encoding="utf-8",
    )
    body = ci._compose_body(template, parent_ref="Milestone: [#6](../milestone/6)")
    assert "Milestone: [#6](../milestone/6)" in body
    assert "Milestone: #\n" not in body


# --- frontmatter stripping -------------------------------------------


def test_strip_frontmatter_removes_leading_yaml_block(ci) -> None:
    raw = (
        "---\n"
        "name: Task\n"
        "about: foo\n"
        "labels: ['type:feature']\n"
        "---\n"
        "body content here\n"
    )
    stripped = ci._strip_issue_template_frontmatter(raw)
    assert stripped.strip() == "body content here"


def test_strip_frontmatter_returns_input_when_no_frontmatter(ci) -> None:
    raw = "no frontmatter, just body."
    assert ci._strip_issue_template_frontmatter(raw) == raw


def test_strip_frontmatter_returns_input_when_unclosed(ci) -> None:
    raw = "---\nname: Task\nno-closing-marker\nstill content"
    assert ci._strip_issue_template_frontmatter(raw) == raw


# --- compose body -----------------------------------------------------


def test_compose_body_substitutes_parent_ref(ci, tmp_path: Path) -> None:
    template = tmp_path / "Task.md"
    template.write_text(
        "---\nname: Task\nlabels: ['type:feature']\n---\n"
        "Feature: #\n\n"
        "## What\nfoo\n",
        encoding="utf-8",
    )
    body = ci._compose_body(template, parent_ref="Feature: #42")
    assert "Feature: #42" in body
    assert "Feature: #\n" not in body  # the empty placeholder line gone


def test_compose_body_returns_minimal_body_when_template_missing(ci, tmp_path: Path) -> None:
    template = tmp_path / "Missing.md"
    body = ci._compose_body(template, parent_ref="EPIC: #5")
    assert "EPIC: #5" in body


def test_compose_body_no_parent_ref_leaves_template_placeholder(
    ci, tmp_path: Path
) -> None:
    template = tmp_path / "Task.md"
    template.write_text(
        "---\nname: Task\n---\n"
        "Feature: #\n\n"
        "## What\nfoo\n",
        encoding="utf-8",
    )
    body = ci._compose_body(template, parent_ref="")
    # Placeholder line stays as-is; author fills in.
    assert "Feature: #" in body


# --- adopter workstreams ---------------------------------------------


def test_adopter_workstreams_bare_list(ci) -> None:
    config = {"workstreams": ["cli", "schemas", "agents"]}
    assert ci._adopter_workstreams(config) == {"cli", "schemas", "agents"}


def test_adopter_workstreams_mapping_form(ci) -> None:
    """DEC-018's v0.5.0 mapping form is also recognised (forward-compatible)."""
    config = {
        "workstreams": {
            "cli": {"name": "cli", "status": "active"},
            "schemas": {"name": "schemas", "status": "active"},
        },
    }
    assert ci._adopter_workstreams(config) == {"cli", "schemas"}


def test_adopter_workstreams_empty_when_absent(ci) -> None:
    assert ci._adopter_workstreams({}) == set()


def test_adopter_workstreams_skips_non_string_entries(ci) -> None:
    config = {"workstreams": ["cli", 42, None, "schemas"]}
    assert ci._adopter_workstreams(config) == {"cli", "schemas"}


# --- titles pattern lookup -------------------------------------------


def test_title_pattern_for_returns_per_type_regex(ci) -> None:
    titles = {
        "formats": {
            "issue-task": {"pattern": r"^\[Task\] .+$"},
            "issue-feature": {"pattern": r"^\[Feature\] .+$"},
        },
    }
    assert ci._title_pattern_for(titles, "task") == r"^\[Task\] .+$"
    assert ci._title_pattern_for(titles, "feature") == r"^\[Feature\] .+$"


def test_title_pattern_for_returns_none_for_unknown_type(ci) -> None:
    titles = {"formats": {"issue-task": {"pattern": "x"}}}
    assert ci._title_pattern_for(titles, "umbrella") is None


def test_title_pattern_for_returns_none_on_empty_schema(ci) -> None:
    assert ci._title_pattern_for({}, "task") is None


# --- parent-requiredness gate under hierarchy mode (DEC-036 D4, #272) -----


def test_parent_requiredness_gated_under_greenfield(ci) -> None:
    """Greenfield / `hierarchy: gated`: a required parent-ref hard-rejects (gates).
    Byte-unchanged from today's behaviour."""
    type_entry = {"parent_ref_required_severity": "[validation-severity:hard-reject]"}
    assert ci._parent_requiredness_is_gated(type_entry, "gated") is True


def test_parent_requiredness_gated_default_when_knob_absent(ci) -> None:
    """A type with no `parent_ref_required_severity` defaults to hard-reject — the
    greenfield gate holds even before the knob is authored."""
    assert ci._parent_requiredness_is_gated({}, "gated") is True


def test_parent_requiredness_advisory_under_advisory_hierarchy(ci) -> None:
    """`hierarchy: advisory`: the parent-requiredness rule degrades to a warning —
    NOT gated. create-issue files parentless and advises. This is the relaxation
    flat brownfield trackers need (a parent the repo can't express)."""
    type_entry = {"parent_ref_required_severity": "[validation-severity:hard-reject]"}
    assert ci._parent_requiredness_is_gated(type_entry, "advisory") is False


def test_parent_requiredness_advisory_softens_even_without_explicit_knob(ci) -> None:
    """Advisory softens regardless of the authored knob — the mode is what
    degrades requiredness; the knob just confirms a rule exists to degrade."""
    assert ci._parent_requiredness_is_gated({}, "advisory") is False


def test_advisory_softens_requiredness_gate_real_guard(ci) -> None:
    """REAL guard over shipped code (requiredness side): the final assertion
    exercises the production `ci._parent_requiredness_is_gated`, confirming
    advisory does NOT gate. Unlike the containment `_illustration` tests in
    test_pm_substrate_map_schema.py (which model a non-existent production
    function locally), the requiredness gate IS a real function, so this guards
    its behaviour directly.

    The `buggy_is_gated` below is a LOCAL model of the inverse bug — advisory
    wrongly KEEPING the gate — shown only to make the failure mode the real
    assertion catches explicit. It is not production code.
    """
    def buggy_is_gated(type_entry, hierarchy):  # noqa: ARG001
        # BUG: ignores the hierarchy mode, always gates.
        return True

    # Under advisory the buggy model still gates...
    assert buggy_is_gated({}, "advisory") is True
    # ...which a not-gated assertion would reject:
    with pytest.raises(AssertionError):
        assert buggy_is_gated({}, "advisory") is False
    # The REAL production function correctly does NOT gate under advisory.
    assert ci._parent_requiredness_is_gated({}, "advisory") is False


# --- gh issue create milestone form (#223 regression) -----------------


def test_gh_create_issue_passes_milestone_by_name_not_number(
    ci, monkeypatch
) -> None:
    """`gh issue create --milestone` matches by name only (#223).

    Regression: the resolver normalises --milestone to the milestone
    NUMBER for parent-ref URL composition, but the gh create call must
    receive the milestone TITLE. Passing the number fails with
    "could not add to milestone '<N>': '<N>' not found".
    """
    captured: dict = {}

    class _Proc:
        returncode = 0
        stdout = "https://example.test/owner/repo/issues/1\n"
        stderr = ""

    def fake_run(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    url = ci._gh_create_issue(
        title="[Task] x",
        body="Milestone: [#7](../milestone/7)\n\n## What\n\ny\n",
        labels=["type:bug"],
        assignee="someone",
        milestone_title="Milestone 2: CLI + discipline polish round 1",
        config={},
    )

    assert url == "https://example.test/owner/repo/issues/1"
    cmd = captured["cmd"]
    assert "--milestone" in cmd
    ms_value = cmd[cmd.index("--milestone") + 1]
    # The NAME, not the number — this is the whole point of #223.
    assert ms_value == "Milestone 2: CLI + discipline polish round 1"
    assert ms_value != "7"


def test_gh_create_issue_omits_milestone_flag_when_none(ci, monkeypatch) -> None:
    """No --milestone flag when no milestone title is given."""
    captured: dict = {}

    class _Proc:
        returncode = 0
        stdout = "https://example.test/owner/repo/issues/2\n"
        stderr = ""

    def fake_run(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    ci._gh_create_issue(
        title="[Task] x",
        body="Feature: #1\n\n## What\n\ny\n",
        labels=["type:feature"],
        assignee="someone",
        milestone_title=None,
        config={},
    )

    assert "--milestone" not in captured["cmd"]


# --- board-item / project-node resolution for the set-board-field hook ----
# (DEC-037 §3 — the non-label per-create field default. The hook needs the
#  new item's node id + the project node id, captured/resolved here at create.)


def test_owner_from_issue_url_extracts_the_owner(ci) -> None:
    assert ci._owner_from_issue_url("https://github.com/acme/repo/issues/9") == "acme"


def test_owner_from_issue_url_none_on_malformed(ci) -> None:
    assert ci._owner_from_issue_url("not-a-url") is None


def test_add_to_board_returns_created_item_id(ci, monkeypatch) -> None:
    """`_gh_add_to_board` reads the created item's node id off
    `gh project item-add --format json` so the `set-board-field` hook can
    target THIS new item. Without this, the field default never seeds."""
    captured: dict = {}

    class _Proc:
        returncode = 0
        stdout = '{"id": "PVTI_newitem", "title": "x"}'
        stderr = ""

    def fake_run(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    item_id = ci._gh_add_to_board(
        7, "https://github.com/acme/repo/issues/9", config={}
    )
    assert item_id == "PVTI_newitem"
    # The membership write asks for json so the item id is recoverable.
    assert "--format" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--format") + 1] == "json"


def test_add_to_board_none_on_gh_failure(ci, monkeypatch) -> None:
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(ci.subprocess, "run", lambda *a, **k: _Proc())
    assert (
        ci._gh_add_to_board(7, "https://github.com/acme/repo/issues/9", config={})
        is None
    )


def test_add_to_board_none_on_unparseable_json(ci, monkeypatch) -> None:
    class _Proc:
        returncode = 0
        stdout = "not json"
        stderr = ""

    monkeypatch.setattr(ci.subprocess, "run", lambda *a, **k: _Proc())
    assert (
        ci._gh_add_to_board(7, "https://github.com/acme/repo/issues/9", config={})
        is None
    )


def test_resolve_project_node_id_reads_id_off_project_view(ci, monkeypatch) -> None:
    """Board NUMBER → project node id via `gh project view --format json`
    (`.id`) — the same read back-fill / pre-check use."""
    captured: dict = {}

    class _Proc:
        returncode = 0
        stdout = '{"id": "PVT_project", "number": 7}'
        stderr = ""

    def fake_run(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    node_id = ci._resolve_project_node_id(7, "acme", config={})
    assert node_id == "PVT_project"
    assert captured["cmd"][:3] == ["gh", "project", "view"]
    assert "--owner" in captured["cmd"]


def test_resolve_project_node_id_none_when_board_unresolvable(ci, monkeypatch) -> None:
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "no such project"

    monkeypatch.setattr(ci.subprocess, "run", lambda *a, **k: _Proc())
    assert ci._resolve_project_node_id(7, "acme", config={}) is None


# --- cache-first node-id resolution (#310) ---------------------------------
# The board→node-id mapping is invariant, so it's cached in config as
# `projects_v2_node_id` at adoption. create-issue consults the cache first and
# only live-resolves (a `gh project view` read) on a cache miss.


def test_resolve_project_node_id_uses_cached_config_without_gh_view(ci, monkeypatch) -> None:
    """Cache HIT (#310): a `projects_v2_node_id` in config is returned directly and
    NO `gh project view` (subprocess) call is issued — the per-create read is skipped."""
    def boom(*a, **k):  # pragma: no cover — must not be reached on a cache hit
        raise AssertionError("no gh call may run when projects_v2_node_id is cached")

    monkeypatch.setattr(ci.subprocess, "run", boom)
    node_id = ci._resolve_project_node_id(
        7, "acme", config={"projects_v2_node_id": "PVT_cached"}
    )
    assert node_id == "PVT_cached"


def test_resolve_project_node_id_live_resolves_on_cache_miss(ci, monkeypatch) -> None:
    """Cache MISS (field absent): fall back to the live `gh project view` read,
    preserving the pre-#310 behaviour exactly."""
    captured: dict = {}

    class _Proc:
        returncode = 0
        stdout = '{"id": "PVT_live", "number": 7}'
        stderr = ""

    def fake_run(cmd, *a, **k):
        captured["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(ci.subprocess, "run", fake_run)
    node_id = ci._resolve_project_node_id(7, "acme", config={})
    assert node_id == "PVT_live"
    assert captured["cmd"][:3] == ["gh", "project", "view"]


def test_resolve_project_node_id_empty_cache_falls_back_to_live(ci, monkeypatch) -> None:
    """An empty-string cache value is treated as absent → live-resolve (not a
    spurious empty node id)."""
    ran = {"n": 0}

    class _Proc:
        returncode = 0
        stdout = '{"id": "PVT_live"}'
        stderr = ""

    def fake_run(cmd, *a, **k):
        ran["n"] += 1
        return _Proc()

    monkeypatch.setattr(ci.subprocess, "run", fake_run)
    assert (
        ci._resolve_project_node_id(7, "acme", config={"projects_v2_node_id": ""})
        == "PVT_live"
    )
    assert ran["n"] == 1


def test_main_board_path_uses_cached_node_id_no_project_view(
    ci, tmp_path, monkeypatch
) -> None:
    """BOARD path end-to-end with `projects_v2_node_id` cached in config: main()
    reaches the hook with the CACHED project_node_id and issues NO `gh project
    view` call — the per-create read #310 eliminates on the common path."""
    root = _stage_capability_tree(tmp_path, has_board=True)
    # Cache the node id in the staged adopter config.
    config_path = root / "project" / "config.yaml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "projects_v2_node_id: PVT_cached\n",
        encoding="utf-8",
    )

    project_view_calls = {"n": 0}

    def fake_run(cmd, *args, **kwargs):
        class _Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        proc = _Proc()
        if "issue" in cmd and "create" in cmd:
            proc.stdout = "https://github.com/acme/repo/issues/42\n"
        elif "project" in cmd and "item-add" in cmd:
            proc.stdout = '{"id": "PVTI_newitem", "title": "x"}'
        elif "project" in cmd and "view" in cmd:
            project_view_calls["n"] += 1
            proc.stdout = '{"id": "PVT_live", "number": 7}'
        elif "repo" in cmd and "view" in cmd:
            proc.stdout = "acme/repo"
        return proc

    monkeypatch.setattr(ci.subprocess, "run", fake_run)
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(
        ci.sys,
        "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )

    hooks_module = _hooks_module(ci)

    captured_context: dict = {}
    real_fire_hooks = ci.fire_hooks

    def capturing_fire_hooks(event, context, config, **kwargs):
        captured_context.update(context)
        return real_fire_hooks(event, context, config, **kwargs)

    monkeypatch.setattr(ci, "fire_hooks", capturing_fire_hooks)

    class _WriteResult:
        ok = True
        detail = "set field"
        error = None

    monkeypatch.setattr(
        hooks_module.substrate_writes,
        "write_field_value",
        lambda config, **kwargs: _WriteResult(),
    )

    rc = ci.main()
    assert rc == 0
    # The cache hit means NO `gh project view` was ever issued...
    assert project_view_calls["n"] == 0
    # ...and the context carries the CACHED id, not a live-resolved one.
    assert captured_context["project_node_id"] == "PVT_cached"


# --- main() integration: the create-context ASSEMBLY (#295) ----------------
# The unit tests above prove the helpers return the right ids and that the hook
# seeds GIVEN a hand-built context. These drive the REAL main() to pin the wiring
# the fix actually repairs: that after a successful create + board-add, main()
# ASSEMBLES a context whose `issue.board_item_id` + top-level `project_node_id`
# are populated — the exact `{number,title}`-only context that bug #295 fixed —
# and that the REAL `set-board-field` hook reads those keys and reaches the seam.
#
# The hook runs for real here (a staged hooks.yaml + the real fire_hooks the
# script imports), so the asserted keys are the ones `_lib/hooks.py` actually
# reads. A future refactor that renames `board_item_id` / `project_node_id` in
# EITHER file drifts the cross-file contract and fails this test (critic Gap 4 +
# Gap 5).


def _stage_capability_tree(tmp_path: Path, *, has_board: bool) -> Path:
    """Stage a minimal but REAL pm capability tree main() can run against.

    Carries just enough for the create + (optional) board path: the schemas
    main() reads, a Task template, an adopter config (board on/off), an empty
    members file (open mode — any identity passes), and a hooks.yaml declaring
    the `set-board-field` hook so the REAL fire_hooks exercises the assembled
    context end-to-end.
    """
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    (root / "schemas").mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    (root / "project").mkdir(parents=True)

    (root / "schemas" / "issue-types.yaml").write_text(
        "types:\n"
        "  task:\n"
        "    title_prefix: Task\n"
        "    title_case: title\n"
        "    parent_issue_types: [feature, umbrella, epic, milestone]\n"
        "    parent_ref_form: 'Feature: #<N>'\n"
        "    parent_ref_optional: false\n"
        "    parent_ref_required_severity: '[validation-severity:hard-reject]'\n",
        encoding="utf-8",
    )
    (root / "schemas" / "titles.yaml").write_text(
        "formats:\n"
        "  issue-task:\n"
        "    pattern: '^\\[(Task|Bug|Docs|Test|Refactor|Chore)\\] .+$'\n",
        encoding="utf-8",
    )
    (root / "schemas" / "body-format.yaml").write_text("sections: {}\n", encoding="utf-8")

    (root / "templates" / "Task.md").write_text(
        "---\nname: Task\n---\nFeature: #\n\n## What\nfoo\n", encoding="utf-8"
    )

    config_lines = ["workstreams: [spyre]\n"]
    if has_board:
        config_lines.append("has_projects_v2_board: true\n")
        config_lines.append("projects_v2_board_id: 7\n")
    (root / "project" / "config.yaml").write_text("".join(config_lines), encoding="utf-8")

    # Empty members → open mode (membership passes for any resolved identity).
    (root / "project" / "members.yaml").write_text("members: []\n", encoding="utf-8")

    # The set-board-field hook: this is what reads the assembled context keys.
    (root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: set-board-field\n"
        "      field_id: PVTF_workstream\n"
        "      single_select_option_id: OPT_spyre\n",
        encoding="utf-8",
    )
    return root


def _gh_command_dispatcher(create_url: str):
    """Build a fake subprocess.run that answers the gh calls main() makes.

    Routes on the gh subcommand: `issue create` → the created URL; `project
    item-add` → the new item node id; `project view` → the project node id;
    `repo view` → owner/name. Any other gh call returns a benign empty success.
    """

    def fake_run(cmd, *args, **kwargs):
        class _Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        proc = _Proc()
        joined = " ".join(str(c) for c in cmd)
        if "issue" in cmd and "create" in cmd:
            proc.stdout = create_url + "\n"
        elif "project" in cmd and "item-add" in cmd:
            proc.stdout = '{"id": "PVTI_newitem", "title": "x"}'
        elif "project" in cmd and "view" in cmd:
            proc.stdout = '{"id": "PVT_project", "number": 7}'
        elif "repo" in cmd and "view" in cmd:
            proc.stdout = "acme/repo"
        elif "api" in cmd and "user" in joined:
            proc.stdout = "filer-login"
        return proc

    return fake_run


def test_main_board_path_assembles_context_hook_reads_and_seeds(
    ci, tmp_path, monkeypatch
) -> None:
    """BOARD path: after create + board-add, main() fires the hook with a
    context carrying `issue.board_item_id` and top-level `project_node_id`
    (the keys `_lib/hooks.py` reads), and the REAL set-board-field hook reaches
    the seam targeting the NEW item — the wiring #295 repairs."""
    root = _stage_capability_tree(tmp_path, has_board=True)

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/42"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(
        ci.sys,
        "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )

    # The seam the hook reaches lives on the hooks module create-issue imported.
    # Resolve it BEFORE wrapping ci.fire_hooks (the wrapper's __module__ is this
    # test, not the hooks module).
    hooks_module = _hooks_module(ci)

    # Capture the REAL context main() hands fire_hooks, without stubbing the
    # hook out — the wrapped real fire_hooks still runs the staged set-board-field
    # hook, so the seam capture below proves the keys were read, not just present.
    captured_context: dict = {}
    real_fire_hooks = ci.fire_hooks

    def capturing_fire_hooks(event, context, config, **kwargs):
        captured_context.update(context)
        return real_fire_hooks(event, context, config, **kwargs)

    monkeypatch.setattr(ci, "fire_hooks", capturing_fire_hooks)

    # Patch write_field_value on that hooks module to capture the field write
    # the hook drives.
    seam_call: dict = {}

    class _WriteResult:
        ok = True
        detail = "set field"
        error = None

    def fake_write(config, **kwargs):
        seam_call.update(kwargs)
        return _WriteResult()

    monkeypatch.setattr(hooks_module.substrate_writes, "write_field_value", fake_write)

    rc = ci.main()
    assert rc == 0

    # Gap 4: main() ASSEMBLED the populated context (not the {number,title}-only
    # shape #295 fixed).
    assert captured_context["issue"]["board_item_id"] == "PVTI_newitem"
    assert captured_context["project_node_id"] == "PVT_project"

    # Gap 5: the REAL hook read those keys and reached the seam for the NEW item.
    assert seam_call["item_id"] == "PVTI_newitem"
    assert seam_call["project_id"] == "PVT_project"
    assert seam_call["field_id"] == "PVTF_workstream"
    assert seam_call["single_select_option_id"] == "OPT_spyre"


def test_main_label_fallback_path_omits_board_keys_hook_skips(
    ci, tmp_path, monkeypatch
) -> None:
    """LABEL-FALLBACK path (no board configured): main() assembles a context
    with NEITHER `issue.board_item_id` NOR a populated `project_node_id`, so the
    REAL set-board-field hook skips and no field write is attempted."""
    root = _stage_capability_tree(tmp_path, has_board=False)

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/43"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(
        ci.sys,
        "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )

    hooks_module = _hooks_module(ci)

    captured_context: dict = {}
    real_fire_hooks = ci.fire_hooks

    def capturing_fire_hooks(event, context, config, **kwargs):
        captured_context.update(context)
        return real_fire_hooks(event, context, config, **kwargs)

    monkeypatch.setattr(ci, "fire_hooks", capturing_fire_hooks)

    def boom(*a, **k):  # pragma: no cover — must not be reached
        raise AssertionError("no field write may run on the label-fallback path")

    monkeypatch.setattr(hooks_module.substrate_writes, "write_field_value", boom)

    rc = ci.main()
    assert rc == 0

    # Neither board key is populated → the hook (had it run) reads nothing to
    # target, and skips. The seam `boom` above asserts no write was attempted.
    assert "board_item_id" not in captured_context["issue"]
    assert captured_context["project_node_id"] is None


def _hooks_module(ci):
    """The hooks module object create-issue.py imported its `fire_hooks` from.

    create-issue does `from _lib.hooks import fire_hooks`, so the function's
    `__module__` names the loaded hooks module; reach it through sys.modules to
    patch the `substrate_writes` seam the hook actually calls.
    """
    return sys.modules[ci.fire_hooks.__module__]


# --- native sub-issue link on --parent (DEC-005, #344) ---------------------
# create-issue sets GitHub's native sub-issue link IN ADDITION to the textual
# first-line parent-ref. These drive the real main() with the containment seam
# stubbed (offline) to prove: the native link is invoked on --parent; the
# textual ref is still written; and a native no-op (unsupported instance) never
# fails the create.


def test_main_parent_invokes_native_sub_issue_link_and_writes_textual_ref(
    ci, tmp_path, monkeypatch
) -> None:
    """On --parent, main() calls the containment seam to set the native link AND
    the created issue body still carries the textual first-line parent-ref
    (DEC-005: native is added, textual is unchanged)."""
    root = _stage_capability_tree(tmp_path, has_board=False)

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/55"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")

    # Capture the body passed to the create call (the textual ref must be there).
    created_body: dict = {}
    real_create = ci._gh_create_issue

    def capturing_create(**kwargs):
        created_body["body"] = kwargs["body"]
        return real_create(**kwargs)

    monkeypatch.setattr(ci, "_gh_create_issue", capturing_create)

    # Stub the containment seam: capture the call, report LINKED (no network).
    link_calls: list[dict] = []

    def fake_link(config, *, parent_number, child_number):
        link_calls.append({"parent": parent_number, "child": child_number})
        return _FakeLink("linked", ok=True)

    monkeypatch.setattr(ci, "link_sub_issue", fake_link)
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )

    rc = ci.main()
    assert rc == 0
    # The native link was invoked for the new child (#55) under parent #1.
    assert link_calls == [{"parent": 1, "child": 55}]
    # The textual first-line parent-ref is still written into the body.
    assert "Feature: #1" in created_body["body"]


def test_main_no_parent_does_not_invoke_native_link(ci, tmp_path, monkeypatch) -> None:
    """Without --parent (milestone parent), the native sub-issue link is NOT
    invoked — a milestone is not a sub-issue relationship."""
    root = _stage_capability_tree(tmp_path, has_board=False)
    # Make milestone an acceptable parent so the no-parent task is allowed.
    (root / "schemas" / "issue-types.yaml").write_text(
        "types:\n"
        "  task:\n"
        "    title_prefix: Task\n"
        "    title_case: title\n"
        "    parent_issue_types: [feature, milestone]\n"
        "    parent_ref_form: 'Feature: #<N>'\n"
        "    parent_ref_optional: true\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/56"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")

    def boom(*a, **k):  # pragma: no cover — must not be reached
        raise AssertionError("native link must not fire without an issue parent")

    monkeypatch.setattr(ci, "link_sub_issue", boom)
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )
    assert ci.main() == 0


def test_main_parent_native_link_unsupported_does_not_fail_create(
    ci, tmp_path, monkeypatch
) -> None:
    """A native no-op (unsupported instance) never fails the create — main()
    still returns 0 and the issue is created with its textual ref."""
    root = _stage_capability_tree(tmp_path, has_board=False)

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/57"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")

    monkeypatch.setattr(
        ci, "link_sub_issue",
        lambda *a, **k: _FakeLink(
            "native sub-issues unsupported on this instance; textual ref recorded",
            ok=False,
        ),
    )
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )
    assert ci.main() == 0


class _FakeLink:
    """Minimal stand-in for containment.LinkResult — carries `ok` + `detail`."""

    def __init__(self, detail: str, *, ok: bool) -> None:
        self.detail = detail
        self.ok = ok


# --- #356 end-to-end: classification-faithful create via main() ------------
# These drive the REAL main() against the REAL shipped schemas (issue-types,
# titles, classification) to prove the two acceptance criteria that the unit
# tests above only prove piecewise: a Task under an EPIC opens `EPIC: #N`, and
# `--kind bug` produces a `[Bug]` title.


def _stage_real_schema_tree(tmp_path: Path) -> Path:
    """Stage a capability tree using the REAL shipped schemas + a Task template.

    Symlinks the actual issue-types / titles / classification schemas so the test
    exercises the real vocabulary (EPIC/Feature/Umbrella/Task, the kind→prefix
    map) rather than a hand-rolled fixture that could drift from what ships.
    """
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    (root / "schemas").mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    (root / "project").mkdir(parents=True)

    real_schemas = (
        REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "schemas"
    )
    for name in ("issue-types.yaml", "titles.yaml", "classification.yaml"):
        (root / "schemas" / name).write_text(
            (real_schemas / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (root / "schemas" / "body-format.yaml").write_text(
        "sections: {}\n", encoding="utf-8"
    )

    (root / "templates" / "Task.md").write_text(
        "---\nname: Task\n---\nFeature: #\n\n## What\nfoo\n", encoding="utf-8"
    )
    (root / "project" / "config.yaml").write_text(
        "workstreams: [spyre]\n", encoding="utf-8"
    )
    (root / "project" / "members.yaml").write_text("members: []\n", encoding="utf-8")
    return root


def _dispatcher_with_parent_title(create_url: str, parent_title: str):
    """fake subprocess.run answering `issue view` with a chosen parent title."""

    def fake_run(cmd, *args, **kwargs):
        class _Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        proc = _Proc()
        joined = " ".join(str(c) for c in cmd)
        if "issue" in cmd and "create" in cmd:
            proc.stdout = create_url + "\n"
        elif "issue" in cmd and "view" in cmd:
            proc.stdout = json.dumps({"title": parent_title})
        elif "repo" in cmd and "view" in cmd:
            proc.stdout = "acme/repo"
        elif "api" in cmd and "user" in joined:
            proc.stdout = "filer-login"
        return proc

    return fake_run


def test_main_task_under_epic_emits_epic_parent_ref(ci, tmp_path, monkeypatch) -> None:
    """Acceptance 2: filing a Task under EPIC #128 opens the body `EPIC: #128`."""
    root = _stage_real_schema_tree(tmp_path)
    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _dispatcher_with_parent_title(
            "https://github.com/acme/repo/issues/355", "[EPIC] A grand thesis here"
        ),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(ci, "link_sub_issue", lambda *a, **k: _FakeLink("ok", ok=True))

    created: dict = {}
    real_create = ci._gh_create_issue

    def capturing_create(**kwargs):
        created.update(kwargs)
        return real_create(**kwargs)

    monkeypatch.setattr(ci, "_gh_create_issue", capturing_create)
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "fix the faithful create bug here",
            "--kind", "bug",
            "--parent", "128",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )
    assert ci.main() == 0
    first_line = created["body"].lstrip().split("\n", 1)[0]
    assert first_line == "EPIC: #128"
    assert "Feature: #128" not in created["body"]
    # Acceptance 3: --kind bug ⇒ [Bug] title prefix.
    assert created["title"].startswith("[Bug] ")


def test_main_body_file_accepts_any_allowed_parent_ref_form(
    ci, tmp_path, monkeypatch
) -> None:
    """Acceptance 5: a --body-file whose first line is any allowed parent-ref form
    for the type is accepted as-is (here `EPIC: #128` for a Task)."""
    root = _stage_real_schema_tree(tmp_path)
    body_file = tmp_path / "body.md"
    body_file.write_text(
        "EPIC: #128\n\n## What\n\nthe work\n\n## Acceptance criteria\n\n- [ ] done\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _dispatcher_with_parent_title(
            "https://github.com/acme/repo/issues/360", "[EPIC] A grand thesis here"
        ),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(ci, "link_sub_issue", lambda *a, **k: _FakeLink("ok", ok=True))

    created: dict = {}
    real_create = ci._gh_create_issue

    def capturing_create(**kwargs):
        created.update(kwargs)
        return real_create(**kwargs)

    monkeypatch.setattr(ci, "_gh_create_issue", capturing_create)
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "file with a prepared body here",
            "--kind", "bug",
            "--parent", "128",
            "--workstream", "spyre",
            "--body-file", str(body_file),
            "--capability-root", str(root),
            "--yes",
        ],
    )
    assert ci.main() == 0
    # Body used verbatim — the supplied EPIC parent-ref is preserved.
    assert created["body"].lstrip().split("\n", 1)[0] == "EPIC: #128"


# --- the containment substrate selector on --parent (DEC-039 D2 / ADR-035, #357)
# A `containment:` selector in the adopter's substrate-map gates the native link.
# `textual` ⇒ skip the native link entirely (the textual child-side ref already
# written is the record); `native` / absent-map ⇒ fire it as #344 does. These
# drive the real main() with the containment seam stubbed (offline) and a staged
# substrate-map to prove each branch of the single decision point.


def _write_substrate_map(root: Path, containment: str | None) -> None:
    """Stage a minimal substrate-map.yaml under the capability tree.

    `containment` None omits the key entirely (so the loader's default — native —
    applies); a string writes `containment: <value>`. A minimal but schema-valid
    map (schema_version + an empty axes map) so the loader parses a present map.
    """
    body = "schema_version: 1\naxes: {}\n"
    if containment is not None:
        body += f"containment: {containment}\n"
    (root / "project" / "substrate-map.yaml").write_text(body, encoding="utf-8")


def test_main_parent_textual_containment_skips_native_link_keeps_textual_ref(
    ci, tmp_path, monkeypatch
) -> None:
    """`containment: textual` ⇒ the native sub-issue link is NOT attempted, but
    the textual first-line parent-ref is STILL written (the universal spine,
    DEC-039 D3). The textual ref is the containment record in this mode."""
    root = _stage_capability_tree(tmp_path, has_board=False)
    _write_substrate_map(root, "textual")

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/58"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")

    created_body: dict = {}
    real_create = ci._gh_create_issue

    def capturing_create(**kwargs):
        created_body["body"] = kwargs["body"]
        return real_create(**kwargs)

    monkeypatch.setattr(ci, "_gh_create_issue", capturing_create)

    def boom(*a, **k):  # pragma: no cover — must not be reached
        raise AssertionError("native link must not fire under containment: textual")

    monkeypatch.setattr(ci, "link_sub_issue", boom)
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )

    rc = ci.main()
    assert rc == 0
    # The textual parent-ref is still the record — written regardless of mode.
    assert "Feature: #1" in created_body["body"]


def test_main_parent_native_containment_invokes_native_link(
    ci, tmp_path, monkeypatch
) -> None:
    """An explicit `containment: native` ⇒ the native sub-issue link fires exactly
    as #344 (greenfield-equivalent)."""
    root = _stage_capability_tree(tmp_path, has_board=False)
    _write_substrate_map(root, "native")

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/59"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")

    link_calls: list[dict] = []

    def fake_link(config, *, parent_number, child_number):
        link_calls.append({"parent": parent_number, "child": child_number})
        return _FakeLink("linked", ok=True)

    monkeypatch.setattr(ci, "link_sub_issue", fake_link)
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )

    rc = ci.main()
    assert rc == 0
    assert link_calls == [{"parent": 1, "child": 59}]


def test_main_parent_absent_containment_key_defaults_to_native_link(
    ci, tmp_path, monkeypatch
) -> None:
    """A present map with NO `containment:` key keeps the native default — the
    native link fires (absent ⇒ native, the safe direction toward the ideal)."""
    root = _stage_capability_tree(tmp_path, has_board=False)
    _write_substrate_map(root, None)  # present map, containment key omitted

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/60"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")

    link_calls: list[dict] = []

    def fake_link(config, *, parent_number, child_number):
        link_calls.append({"parent": parent_number, "child": child_number})
        return _FakeLink("linked", ok=True)

    monkeypatch.setattr(ci, "link_sub_issue", fake_link)
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
        ],
    )

    rc = ci.main()
    assert rc == 0
    assert link_calls == [{"parent": 1, "child": 60}]


# --- workstream-requiredness gate honours the substrate-map degrade (#443) --
# The label-fallback (no board) gate must not demand a `--workstream` when the
# substrate-map declares the `workstream` axis `unsupported` — the downstream
# `_build_labels`/`resolve_write` path already DEGRADEs and drops the label, so a
# brownfield adopter with no workstream substrate can file without a throwaway
# value. The gate keys on the SAME `axis_disposition` signal that degradation
# uses, so gate and resolution cannot disagree. Greenfield and a SERVED
# workstream axis are unchanged (still required); the board path already skips.


def _write_workstream_unsupported_map(root: Path) -> None:
    """Stage a present substrate-map declaring the `workstream` axis unsupported.

    Minimal but schema-shaped: schema_version + an `axes` map binding only
    `workstream: {unsupported: true}`. Absence would degrade identically
    (absent ≡ unsupported), but declaring it explicitly makes the intent the
    test asserts on unambiguous.
    """
    (root / "project" / "substrate-map.yaml").write_text(
        "schema_version: 1\naxes:\n  workstream:\n    unsupported: true\n",
        encoding="utf-8",
    )


def test_main_label_fallback_workstream_unsupported_files_without_workstream(
    ci, tmp_path, monkeypatch
) -> None:
    """#443: label-fallback + `workstream: unsupported` + no `--workstream` ⇒
    create SUCCEEDS (rc 0), and no workstream label is written (the axis
    DEGRADEs downstream, exactly as `_build_labels` already does)."""
    root = _stage_capability_tree(tmp_path, has_board=False)
    _write_workstream_unsupported_map(root)

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/61"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(ci, "link_sub_issue", lambda *a, **k: _FakeLink("ok", ok=True))

    created: dict = {}
    real_create = ci._gh_create_issue

    def capturing_create(**kwargs):
        created.update(kwargs)
        return real_create(**kwargs)

    monkeypatch.setattr(ci, "_gh_create_issue", capturing_create)
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            # NOTE: no --workstream — the whole point of #443.
            "--capability-root", str(root),
            "--yes",
        ],
    )

    rc = ci.main()
    assert rc == 0
    # The workstream axis DEGRADEd: no `workstream:*` label was written.
    assert not any(lbl.startswith("workstream:") for lbl in created["labels"])


def test_main_label_fallback_greenfield_still_requires_workstream(
    ci, tmp_path, monkeypatch
) -> None:
    """The unchanged path: label-fallback with NO substrate-map (greenfield) and
    no `--workstream` still hard-refuses (rc 2) — the kit's `workstream:*` label
    IS the adopter's substrate there, so a value is genuinely required."""
    root = _stage_capability_tree(tmp_path, has_board=False)
    # No substrate-map staged ⇒ greenfield ⇒ workstream axis is SERVED.

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/62"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(ci, "link_sub_issue", lambda *a, **k: _FakeLink("ok", ok=True))
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            # No --workstream, and greenfield ⇒ the gate must still fire.
            "--capability-root", str(root),
            "--yes",
        ],
    )

    assert ci.main() == 2


def test_main_label_fallback_workstream_served_map_still_requires_workstream(
    ci, tmp_path, monkeypatch
) -> None:
    """A present map that BINDS `workstream` (SERVED, not unsupported) keeps the
    requirement — a bound axis has a substrate to write to, so omitting the value
    is still a refusal (rc 2). This pins that the fix keys on `unsupported`, not
    merely on the presence of a map."""
    root = _stage_capability_tree(tmp_path, has_board=False)
    # A present map binding workstream to a label remap ⇒ SERVED.
    (root / "project" / "substrate-map.yaml").write_text(
        "schema_version: 1\n"
        "axes:\n"
        "  workstream:\n"
        "    label:\n"
        "      remap:\n"
        "        spyre: Spyre\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        ci.subprocess,
        "run",
        _gh_command_dispatcher("https://github.com/acme/repo/issues/63"),
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(ci, "link_sub_issue", lambda *a, **k: _FakeLink("ok", ok=True))
    monkeypatch.setattr(
        ci.sys, "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "do a thing",
            "--parent", "1",
            # No --workstream; the axis is SERVED ⇒ the gate must still fire.
            "--capability-root", str(root),
            "--yes",
        ],
    )

    assert ci.main() == 2
