"""Tests for project-management's create-issue script's pure logic.

Covers title composition, parent-ref line formatting, template body
substitution, frontmatter stripping, adopter-workstream extraction.
The gh subprocess invocations are not tested at unit level — they're
thin wrappers; their behaviour is the same shape as evidence's
validate.py call path.
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
