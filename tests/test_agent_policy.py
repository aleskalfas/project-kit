"""Per-agent model and effort (#1047): the vocabulary, the precedence, the
`pkit validate` finding and the `pkit agents` report.

The deploy carry-over is exercised against the real adapter in
`tests/test_deploy_agents.py`; the backbone-to-adapter parity guards live in
`tests/test_agents_overlay.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import agent_policy as ap
from project_kit import agents_overlay as ao
from project_kit import refs
from project_kit.cli import main
from project_kit.validators import Severity

# --- the vocabulary -----------------------------------------------------------


@pytest.mark.parametrize("value", [
    "inherit", "sonnet", "opus", "haiku", "opus[1m]",
    "claude-opus-4-1", "claude-fable-5", "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
])
def test_model_accepts_inherit_aliases_and_full_names(value):
    assert ap.value_problem(ap.MODEL, value) is None


@pytest.mark.parametrize("value", ["sonet", "gpt-5", "claude", "", "Sonnet", 3, True, ["opus"]])
def test_model_refuses_anything_else(value):
    problem = ap.value_problem(ap.MODEL, value)
    assert problem is not None
    assert "inherit" in problem and "sonnet" in problem  # names what to write instead


@pytest.mark.parametrize("value", ["inherit", "low", "medium", "high", "xhigh", "max"])
def test_effort_accepts_inherit_and_the_harness_levels(value):
    assert ap.value_problem(ap.EFFORT, value) is None


@pytest.mark.parametrize("value", ["extreme", "High", "", 2, None])
def test_effort_refuses_anything_else(value):
    problem = ap.value_problem(ap.EFFORT, value)
    assert problem is not None
    assert "xhigh" in problem


def test_effort_levels_are_review_prs_levels():
    """The front-matter effort and `review-pr --effort` share one vocabulary."""
    review_pr = (
        Path(__file__).resolve().parents[1]
        / ".pkit" / "capabilities" / "project-management" / "scripts" / "review-pr.py"
    ).read_text(encoding="utf-8")
    m = re.search(r'(?m)^EFFORT_LEVELS\s*=\s*\(([^)]*)\)', review_pr)
    assert m, "could not find EFFORT_LEVELS in review-pr.py"
    assert tuple(re.findall(r'"([^"]+)"', m.group(1))) == ap.EFFORT_LEVELS


# --- the precedence -----------------------------------------------------------


def test_absent_is_inherit():
    setting = ap.effective_setting(ap.MODEL)
    assert (setting.value, setting.source, setting.problem) == ("inherit", ap.SOURCE_DEFAULT, None)


def test_front_matter_value_applies():
    setting = ap.effective_setting(ap.MODEL, declared="sonnet")
    assert (setting.value, setting.source) == ("sonnet", ap.SOURCE_FRONT_MATTER)


def test_overlay_override_wins_over_front_matter():
    setting = ap.effective_setting(ap.EFFORT, declared="low", override="high")
    assert (setting.value, setting.source) == ("high", ap.SOURCE_OVERLAY)


def test_override_to_inherit_resets_a_shipped_value():
    setting = ap.effective_setting(ap.MODEL, declared="opus", override="inherit")
    assert (setting.value, setting.source) == ("inherit", ap.SOURCE_OVERLAY)


def test_bare_override_counts_as_absent():
    setting = ap.effective_setting(ap.MODEL, declared="haiku", override=None)
    assert (setting.value, setting.source) == ("haiku", ap.SOURCE_FRONT_MATTER)


def test_refused_value_falls_back_to_inherit_and_says_why():
    setting = ap.effective_setting(ap.MODEL, declared="sonnet", override="sonet")
    assert setting.value == "inherit"
    assert setting.source == ap.SOURCE_OVERLAY
    assert setting.written == "sonet"
    assert setting.problem is not None


# --- fixtures -----------------------------------------------------------------


@pytest.fixture
def kit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "proj"
    for area in ("agents", "skills"):
        for ns in ("core", "project"):
            (root / ".pkit" / area / ns).mkdir(parents=True)
    # Root-walk install marker (#656).
    (root / ".pkit" / "manifest.yaml").write_text("backbone_version: 0.0.0\n", encoding="utf-8")
    monkeypatch.chdir(root)
    return root


def _agent(root: Path, name: str, extra_front_matter: str = "", *, kind: str = "agents") -> Path:
    path = root / ".pkit" / kind / "core" / f"{name}.md"
    path.write_text(
        f"---\nname: {name}\ndescription: t\n{extra_front_matter}---\n\n# {name}\n",
        encoding="utf-8",
    )
    return path


def _overlay(root: Path, text: str) -> None:
    (root / ao.OVERLAY_PATH).write_text(text, encoding="utf-8")


def _policy_findings(root: Path) -> list[refs.Issue]:
    return [i for i in refs.validate_corpus(root) if i.kind == refs.AGENT_POLICY]


# --- the overlay's per-agent block ------------------------------------------


def test_policy_keys_are_not_overlay_categories(kit):
    _overlay(kit, "overrides:\n  critic:\n    model: haiku\n    code-paths:\n      - src/\n")
    values = ao.load_overlay_values(kit)
    assert values.overrides["critic"] == {"code-paths": ["src/"]}
    assert values.policy["critic"] == {"model": "haiku"}
    assert values.resolve("critic", "model") is None


# --- pkit validate ------------------------------------------------------------


def test_valid_and_absent_settings_raise_no_finding(kit):
    _agent(kit, "plain")
    _agent(kit, "tuned", "model: sonnet\neffort: high\n")
    _overlay(kit, "overrides:\n  plain:\n    model: inherit\n    effort: low\n")
    assert _policy_findings(kit) == []


def test_invalid_front_matter_value_is_an_error(kit):
    _agent(kit, "typo", "effort: extreme\n")
    findings = _policy_findings(kit)
    assert len(findings) == 1
    assert findings[0].location == ".pkit/agents/core/typo.md"
    assert "effort 'extreme'" in findings[0].diagnosis
    errors = [f for f in refs.outcome(kit).findings if f.severity is Severity.ERROR]
    assert any("extreme" in f.message for f in errors)


def test_invalid_overlay_override_is_an_error_at_the_overlay(kit):
    _agent(kit, "critic")
    _overlay(kit, "overrides:\n  critic:\n    model: sonet\n")
    findings = _policy_findings(kit)
    assert len(findings) == 1
    assert findings[0].location == str(ao.OVERLAY_PATH)
    assert "`overrides.critic.model`" in findings[0].diagnosis


def test_a_skills_model_is_not_this_checks_business(kit):
    _agent(kit, "some-skill", "model: whatever\n", kind="skills")
    assert _policy_findings(kit) == []


# --- pkit agents --------------------------------------------------------------


def _agents_output(root: Path) -> str:
    result = CliRunner().invoke(main, ["--color", "never", "agents"])
    assert result.exit_code == 0, result.output
    return result.output


def _row(output: str, name: str) -> str:
    return next(line for line in output.splitlines() if line.strip().startswith(name + " "))


def test_agents_reports_inherit_when_nothing_is_set(kit):
    _agent(kit, "plain")
    row = _row(_agents_output(kit), "plain")
    assert "model inherit" in row and "effort inherit" in row


def test_agents_reports_the_front_matter_and_the_override(kit):
    _agent(kit, "tuned", "model: sonnet\neffort: low\n")
    _overlay(kit, "overrides:\n  tuned:\n    effort: high\n")
    row = _row(_agents_output(kit), "tuned")
    assert "model sonnet" in row
    assert "effort high (overlay)" in row


def test_agents_reports_a_refused_value(kit):
    _agent(kit, "typo", "model: sonet\n")
    row = _row(_agents_output(kit), "typo")
    assert "model inherit (front matter value 'sonet' refused)" in row
