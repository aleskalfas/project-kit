"""Tests for the reviewer-contribution collector (_lib/review_contributions.py).

Per project-management:DEC-032, a capability contributes reviewer
requirements and pm collects them by walking the manifest-registered
capabilities. This covers:

  * The pure `parse_contributions` shape validator (well-formed,
    malformed, empty, unsupported axis, scalar-or-list match values).
  * `list_registered_capabilities` — manifest `components:` reading.
  * `collect_contributions` end-to-end against a temp repo tree:
      - no contributions present anywhere,
      - one registered capability with a rule (collected),
      - an UNregistered (orphan) capability directory present but ignored,
      - an installed contribution whose reviewer agent is undeployed
        (kept VISIBLE as an unsatisfiable requirement, gate fails closed),
      - a malformed/parse-error declaration surfaced as a structured error.
  * `reviewers_for` / `reviewers_for_issues` — the resolution seam the
    gate-checker (#145), pre-check (#146), and review-pr (#147) import:
    provenance-carrying matched rules, the D1 union across closing issues,
    and the fail-closed `ok` / `has_blocking_errors` predicate.
  * The shared `_lib.agents` deployed-agent helper.
  * Structured `ContributionError`s (kind-tagged, not string-matched).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
LIB_PATH = SCRIPTS_DIR / "_lib" / "review_contributions.py"


def _load_lib(module_name: str, path: Path):
    """Spec-load a _lib module with the scripts dir on sys.path.

    The scripts dir is inserted so the module's own `from _lib.agents
    import ...` resolves as it does at runtime, mirroring the smoke test.
    """
    scripts_dir_str = str(SCRIPTS_DIR)
    inserted = scripts_dir_str not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir_str)
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and scripts_dir_str in sys.path:
            sys.path.remove(scripts_dir_str)


@pytest.fixture(scope="module")
def rc():
    return _load_lib("pm_review_contributions_lib_under_test", LIB_PATH)


@pytest.fixture(scope="module")
def agents_lib():
    return _load_lib(
        "pm_agents_lib_under_test", SCRIPTS_DIR / "_lib" / "agents.py"
    )


# --- repo-tree builders ----------------------------------------------


def _write_manifest(repo_root: Path, capability_names: list[str]) -> None:
    """Write a backbone manifest registering the given capabilities."""
    lines = ["schema_version: 1", "backbone_version: 1.0.0", "components:"]
    # An adapter component to prove kind-filtering ignores non-capabilities.
    lines += [
        "  - kind: adapter",
        "    name: claude-code",
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml",
    ]
    for name in capability_names:
        lines += [
            "  - kind: capability",
            f"    name: {name}",
            f"    manifest: .pkit/capabilities/{name}/manifest.yaml",
        ]
    (repo_root / ".pkit").mkdir(parents=True, exist_ok=True)
    (repo_root / ".pkit" / "manifest.yaml").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _write_contribution(repo_root: Path, capability: str, body: str) -> None:
    cap_dir = repo_root / ".pkit" / "capabilities" / capability
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "review-contributions.yaml").write_text(body, encoding="utf-8")


def _deploy_agent(repo_root: Path, name: str) -> None:
    agents_dir = repo_root / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{name}.md").write_text("# agent\n", encoding="utf-8")


# --- shared _lib.agents helper ---------------------------------------


def test_agents_helper_deploy_path_and_presence(agents_lib, tmp_path) -> None:
    expected = tmp_path / ".claude" / "agents" / "design-reviewer.md"
    assert agents_lib.agent_deploy_path(tmp_path, "design-reviewer") == expected
    assert agents_lib.agent_is_deployed(tmp_path, "design-reviewer") is False
    _deploy_agent(tmp_path, "design-reviewer")
    assert agents_lib.agent_is_deployed(tmp_path, "design-reviewer") is True


def test_collector_uses_shared_agents_resolver(rc, agents_lib) -> None:
    # The collector's default agent check IS the shared _lib.agents one,
    # so a single deploy-path definition serves both (COR-007). (Asserted
    # by source provenance, not object identity: the test harness
    # spec-loads agents.py under a second module name, so the function
    # objects differ even though both come from the one _lib/agents.py.)
    assert (
        rc._default_agent_is_deployed.__module__.endswith("agents")
        and rc._default_agent_is_deployed.__name__ == "agent_is_deployed"
    )
    assert (
        Path(rc._default_agent_is_deployed.__code__.co_filename).resolve()
        == (SCRIPTS_DIR / "_lib" / "agents.py").resolve()
        == Path(agents_lib.agent_is_deployed.__code__.co_filename).resolve()
    )


# --- parse_contributions (pure shape validation) ---------------------


def test_parse_none_is_empty_no_error(rc) -> None:
    rules, errors = rc.parse_contributions(None, "ux-ui-design")
    assert rules == ()
    assert errors == ()


def test_parse_well_formed_rule(rc) -> None:
    data = {
        "schema_version": 1,
        "contributions": [
            {"match": {"workstream": "design"}, "reviewer": "design-reviewer"},
        ],
    }
    rules, errors = rc.parse_contributions(data, "ux-ui-design")
    assert errors == ()
    assert len(rules) == 1
    rule = rules[0]
    assert rule.capability == "ux-ui-design"
    assert rule.reviewer == "design-reviewer"
    assert dict(rule.predicate) == {"workstream": ("design",)}
    assert rule.deployed is True
    assert rule.resolution_error is None


def test_parse_multi_value_match(rc) -> None:
    # A list value (OR within the axis) — the case a scalar could not
    # express; committed at schema_version 1 (finding #4).
    data = {
        "contributions": [
            {"match": {"workstream": ["design", "ui"]}, "reviewer": "design-reviewer"},
        ]
    }
    rules, errors = rc.parse_contributions(data, "ux-ui-design")
    assert errors == ()
    assert len(rules) == 1
    assert dict(rules[0].predicate) == {"workstream": ("design", "ui")}


def test_parse_multi_value_match_dedups_values(rc) -> None:
    data = {
        "contributions": [
            {"match": {"workstream": ["design", "design"]}, "reviewer": "r"},
        ]
    }
    rules, errors = rc.parse_contributions(data, "cap")
    assert errors == ()
    assert dict(rules[0].predicate) == {"workstream": ("design",)}


def test_parse_empty_list_match_is_malformed(rc) -> None:
    data = {"contributions": [{"match": {"workstream": []}, "reviewer": "r"}]}
    rules, errors = rc.parse_contributions(data, "cap")
    assert rules == ()
    assert any("must be a non-empty list" in e.message for e in errors)


def test_parse_non_string_list_member_is_malformed(rc) -> None:
    data = {"contributions": [{"match": {"workstream": ["design", 7]}, "reviewer": "r"}]}
    rules, errors = rc.parse_contributions(data, "cap")
    assert rules == ()
    assert any("values must be non-empty strings" in e.message for e in errors)


def test_parse_missing_contributions_key(rc) -> None:
    rules, errors = rc.parse_contributions({"schema_version": 1}, "cap")
    assert rules == ()
    assert any("missing the `contributions:` key" in e.message for e in errors)


def test_parse_contributions_not_a_list(rc) -> None:
    rules, errors = rc.parse_contributions(
        {"contributions": {"match": {}}}, "cap"
    )
    assert rules == ()
    assert any("`contributions` must be a list" in e.message for e in errors)


def test_parse_errors_are_structured(rc) -> None:
    # Errors carry a kind a consumer can branch on, not just a string.
    rules, errors = rc.parse_contributions({"schema_version": 1}, "cap")
    assert rules == ()
    assert len(errors) == 1
    err = errors[0]
    assert err.kind == rc.ERROR_MALFORMED
    assert err.capability == "cap"
    assert "missing the `contributions:` key" in err.message


def test_parse_rule_missing_reviewer(rc) -> None:
    data = {"contributions": [{"match": {"workstream": "design"}}]}
    rules, errors = rc.parse_contributions(data, "cap")
    assert rules == ()
    assert any("reviewer must be a non-empty string" in e.message for e in errors)


def test_parse_rule_empty_match(rc) -> None:
    data = {"contributions": [{"match": {}, "reviewer": "r"}]}
    rules, errors = rc.parse_contributions(data, "cap")
    assert rules == ()
    assert any("match must be a non-empty mapping" in e.message for e in errors)


def test_parse_rule_unsupported_axis(rc) -> None:
    data = {
        "contributions": [
            {"match": {"priority": "High"}, "reviewer": "r"},
        ]
    }
    rules, errors = rc.parse_contributions(data, "cap")
    assert rules == ()
    assert any("unsupported axis" in e.message for e in errors)


def test_parse_mixed_good_and_bad_rules(rc) -> None:
    data = {
        "contributions": [
            {"match": {"workstream": "design"}, "reviewer": "design-reviewer"},
            {"match": {"workstream": "ui"}},  # missing reviewer
        ]
    }
    rules, errors = rc.parse_contributions(data, "cap")
    assert len(rules) == 1
    assert rules[0].reviewer == "design-reviewer"
    assert any("reviewer must be a non-empty string" in e.message for e in errors)


# --- list_registered_capabilities ------------------------------------


def test_list_registered_capabilities_filters_kind(rc) -> None:
    manifest = {
        "components": [
            {"kind": "adapter", "name": "claude-code"},
            {"kind": "capability", "name": "project-management"},
            {"kind": "capability", "name": "ux-ui-design"},
        ]
    }
    assert rc.list_registered_capabilities(manifest) == (
        "project-management",
        "ux-ui-design",
    )


def test_list_registered_capabilities_tolerates_garbage(rc) -> None:
    assert rc.list_registered_capabilities(None) == ()
    assert rc.list_registered_capabilities({}) == ()
    assert rc.list_registered_capabilities({"components": "nope"}) == ()


# --- collect_contributions (end-to-end against a temp tree) ----------


def test_collect_no_contributions_present(rc, tmp_path) -> None:
    _write_manifest(tmp_path, ["project-management"])
    result = rc.collect_contributions(tmp_path)
    assert result.rules == ()
    assert result.errors == ()
    assert result.ok is True
    assert result.has_blocking_errors is False
    assert result.capabilities_walked == ("project-management",)


def test_collect_one_registered_capability_with_rule(rc, tmp_path) -> None:
    _write_manifest(tmp_path, ["project-management", "ux-ui-design"])
    _write_contribution(
        tmp_path,
        "ux-ui-design",
        "schema_version: 1\n"
        "contributions:\n"
        "  - match:\n"
        "      workstream: design\n"
        "    reviewer: design-reviewer\n",
    )
    _deploy_agent(tmp_path, "design-reviewer")

    result = rc.collect_contributions(tmp_path)
    assert result.ok is True
    assert len(result.rules) == 1
    rule = result.rules[0]
    assert rule.capability == "ux-ui-design"
    assert rule.reviewer == "design-reviewer"
    assert dict(rule.predicate) == {"workstream": ("design",)}
    assert rule.deployed is True


def test_collect_multi_value_match_end_to_end(rc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_contribution(
        tmp_path,
        "ux-ui-design",
        "schema_version: 1\n"
        "contributions:\n"
        "  - match:\n"
        "      workstream:\n"
        "        - design\n"
        "        - ui\n"
        "    reviewer: design-reviewer\n",
    )
    _deploy_agent(tmp_path, "design-reviewer")

    result = rc.collect_contributions(tmp_path)
    assert result.ok is True
    assert dict(result.rules[0].predicate) == {"workstream": ("design", "ui")}
    # The rule fires for either listed value.
    assert result.reviewers_for({"workstream": "ui"})[0].reviewer == "design-reviewer"
    assert (
        result.reviewers_for({"workstream": "design"})[0].reviewer
        == "design-reviewer"
    )
    assert result.reviewers_for({"workstream": "backend"}) == ()


def test_collect_ignores_orphan_unregistered_capability(rc, tmp_path) -> None:
    # Only project-management is registered; ux-ui-design exists on disk
    # (with a contribution + deployed agent) but is NOT in the manifest.
    _write_manifest(tmp_path, ["project-management"])
    _write_contribution(
        tmp_path,
        "ux-ui-design",
        "schema_version: 1\n"
        "contributions:\n"
        "  - match:\n"
        "      workstream: design\n"
        "    reviewer: design-reviewer\n",
    )
    _deploy_agent(tmp_path, "design-reviewer")

    result = rc.collect_contributions(tmp_path)
    # The orphan directory must NOT contribute — no rules, no errors.
    assert result.rules == ()
    assert result.ok is True
    assert "ux-ui-design" not in result.capabilities_walked


def test_collect_undeployed_reviewer_stays_visible_and_fails_closed(
    rc, tmp_path
) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_contribution(
        tmp_path,
        "ux-ui-design",
        "schema_version: 1\n"
        "contributions:\n"
        "  - match:\n"
        "      workstream: design\n"
        "    reviewer: design-reviewer\n",
    )
    # NOTE: deliberately do NOT deploy the agent file.

    result = rc.collect_contributions(tmp_path)

    # Fail-closed seam: the requirement is NOT dropped. The rule is present
    # but marked unsatisfiable, and a structured error is surfaced.
    assert len(result.rules) == 1
    broken = result.rules[0]
    assert broken.reviewer == "design-reviewer"
    assert broken.deployed is False
    assert broken.resolution_error is not None
    assert broken.resolution_error.kind == rc.ERROR_UNDEPLOYED_AGENT

    assert result.ok is False
    assert result.has_blocking_errors is True
    assert any(e.kind == rc.ERROR_UNDEPLOYED_AGENT for e in result.errors)

    # The gate-checker resolving a matching PR sees the requirement — so it
    # can refuse on an unsatisfiable reviewer rather than silently dropping.
    matched = result.reviewers_for({"workstream": "design"})
    assert len(matched) == 1
    assert matched[0].deployed is False
    assert any(not r.deployed for r in matched)


def test_collect_missing_manifest_returns_empty(rc, tmp_path) -> None:
    # No .pkit/manifest.yaml at all.
    result = rc.collect_contributions(tmp_path)
    assert result.rules == ()
    assert result.ok is True
    assert result.capabilities_walked == ()


def test_collect_malformed_declaration_surfaced(rc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_contribution(
        tmp_path,
        "ux-ui-design",
        "schema_version: 1\ncontributions: not-a-list\n",
    )
    result = rc.collect_contributions(tmp_path)
    assert result.rules == ()
    assert result.has_blocking_errors is True
    err = next(e for e in result.errors if "`contributions` must be a list" in e.message)
    assert err.kind == rc.ERROR_MALFORMED
    assert err.capability == "ux-ui-design"


# --- reviewers_for / reviewers_for_issues (the consumer seam) --------


def test_reviewers_for_returns_rules_with_provenance(rc) -> None:
    collection = rc.ContributionCollection(
        rules=(
            rc.ContributionRule("ux-ui-design", {"workstream": ("design",)}, "design-reviewer"),
            rc.ContributionRule("backend-cap", {"workstream": ("backend",)}, "backend-reviewer"),
        )
    )
    matched = collection.reviewers_for({"workstream": "design"})
    assert len(matched) == 1
    # Provenance is preserved (the gate-checker's refusal message wants it).
    assert matched[0].reviewer == "design-reviewer"
    assert matched[0].capability == "ux-ui-design"


def test_reviewers_for_no_axis_matches_nothing(rc) -> None:
    collection = rc.ContributionCollection(
        rules=(
            rc.ContributionRule("a", {"workstream": ("design",)}, "design-reviewer"),
        )
    )
    # Closing entity carries no workstream axis → baseline only (DEC-032 D1).
    assert collection.reviewers_for({}) == ()
    assert collection.reviewers_for({"type": "feature"}) == ()


def test_reviewers_for_deduplicates_by_reviewer(rc) -> None:
    collection = rc.ContributionCollection(
        rules=(
            rc.ContributionRule("a", {"workstream": ("design",)}, "design-reviewer"),
            rc.ContributionRule("b", {"workstream": ("design",)}, "design-reviewer"),
        )
    )
    matched = collection.reviewers_for({"workstream": "design"})
    assert tuple(r.reviewer for r in matched) == ("design-reviewer",)


def test_reviewers_for_multi_value_predicate(rc) -> None:
    collection = rc.ContributionCollection(
        rules=(
            rc.ContributionRule("a", {"workstream": ("design", "ui")}, "design-reviewer"),
        )
    )
    assert collection.reviewers_for({"workstream": "ui"})[0].reviewer == "design-reviewer"
    assert collection.reviewers_for({"workstream": "design"})[0].reviewer == "design-reviewer"
    assert collection.reviewers_for({"workstream": "backend"}) == ()


def test_reviewers_for_issues_unions_across_closing_issues(rc) -> None:
    # DEC-032 D1: a PR closing a `design` issue and a `backend` issue
    # requires BOTH reviewers — the union, owned by the collector.
    collection = rc.ContributionCollection(
        rules=(
            rc.ContributionRule("a", {"workstream": ("design",)}, "design-reviewer"),
            rc.ContributionRule("b", {"workstream": ("backend",)}, "backend-reviewer"),
        )
    )
    matched = collection.reviewers_for_issues(
        [{"workstream": "design"}, {"workstream": "backend"}]
    )
    assert {r.reviewer for r in matched} == {"design-reviewer", "backend-reviewer"}


def test_reviewers_for_issues_dedups_across_issues(rc) -> None:
    # Two design issues on one PR require `design-reviewer` once.
    collection = rc.ContributionCollection(
        rules=(
            rc.ContributionRule("a", {"workstream": ("design",)}, "design-reviewer"),
        )
    )
    matched = collection.reviewers_for_issues(
        [{"workstream": "design"}, {"workstream": "design"}]
    )
    assert tuple(r.reviewer for r in matched) == ("design-reviewer",)


def test_reviewers_for_issues_empty_is_baseline_only(rc) -> None:
    # A PR closing no issues → no contributed reviewers (baseline only).
    collection = rc.ContributionCollection(
        rules=(
            rc.ContributionRule("a", {"workstream": ("design",)}, "design-reviewer"),
        )
    )
    assert collection.reviewers_for_issues([]) == ()


def test_reviewers_for_issues_preserves_unsatisfiable_rule(rc) -> None:
    # The union must keep a broken (undeployed) requirement visible so a
    # multi-issue PR also fails closed.
    err = rc.ContributionError(rc.ERROR_UNDEPLOYED_AGENT, "ux-ui-design", "missing")
    collection = rc.ContributionCollection(
        rules=(
            rc.ContributionRule(
                "ux-ui-design",
                {"workstream": ("design",)},
                "design-reviewer",
                deployed=False,
                resolution_error=err,
            ),
        )
    )
    matched = collection.reviewers_for_issues([{"workstream": "design"}])
    assert len(matched) == 1
    assert matched[0].deployed is False
