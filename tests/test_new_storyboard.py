"""Tests for `pkit new storyboard` (per COR-016)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import storyboards
from project_kit.cli import main


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal project tree with `.pkit/agents/{core,project}/`."""
    agents_dir = tmp_path / ".pkit" / "agents"
    for ns in ("core", "project"):
        (agents_dir / ns).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _make_flat_agent(root: Path, namespace: str, name: str) -> Path:
    target = root / ".pkit" / "agents" / namespace / f"{name}.md"
    target.write_text(
        f"---\nname: {name}\ndescription: t\n---\n\n# {name}\n", encoding="utf-8"
    )
    return target


def _make_folder_agent(root: Path, namespace: str, name: str) -> Path:
    folder = root / ".pkit" / "agents" / namespace / name
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{name}.md"
    target.write_text(
        f"---\nname: {name}\ndescription: t\n---\n\n# {name}\n", encoding="utf-8"
    )
    return target


# --- stamp_new_storyboard (deterministic layer) ---------------------


def test_stamp_for_flat_agent_converts_to_folder_and_writes_sibling(
    kit_target: Path,
) -> None:
    """A flat agent gets migrated to folder form when a storyboard sibling is stamped."""
    flat = _make_flat_agent(kit_target, "project", "my-agent")
    assert flat.is_file()

    target = storyboards.stamp_new_storyboard(kit_target, "agent", "my-agent")

    folder_agent = kit_target / ".pkit" / "agents" / "project" / "my-agent" / "my-agent.md"
    storyboard_file = kit_target / ".pkit" / "agents" / "project" / "my-agent" / "storyboard.md"

    assert folder_agent.is_file(), "agent didn't migrate to folder form"
    assert not flat.exists(), "flat agent file wasn't removed after migration"
    assert target == storyboard_file
    assert storyboard_file.is_file()


def test_stamp_for_folder_agent_writes_sibling_directly(kit_target: Path) -> None:
    """An agent already in folder form just gets a sibling storyboard added."""
    agent = _make_folder_agent(kit_target, "core", "reviewer")
    folder = agent.parent

    target = storyboards.stamp_new_storyboard(kit_target, "agent", "reviewer")

    assert target == folder / "storyboard.md"
    assert target.is_file()
    assert agent.is_file(), "agent file should still exist after sibling stamp"


def test_stamp_scenario_flag_produces_named_storyboard(kit_target: Path) -> None:
    _make_folder_agent(kit_target, "project", "coordinator")
    target = storyboards.stamp_new_storyboard(
        kit_target, "agent", "coordinator", scenario="security-pr-review"
    )
    expected = (
        kit_target / ".pkit" / "agents" / "project" / "coordinator"
        / "security-pr-review.storyboard.md"
    )
    assert target == expected
    assert expected.is_file()


def test_stamp_seeds_three_layer_template(kit_target: Path) -> None:
    _make_folder_agent(kit_target, "project", "agent-a")
    target = storyboards.stamp_new_storyboard(kit_target, "agent", "agent-a")
    body = target.read_text(encoding="utf-8")

    assert "## Framing" in body
    assert "## Tone" in body
    assert "## Scenario 1" in body
    assert "**Trigger.**" in body
    assert "**Preconditions.**" in body
    assert "### Walkthrough" in body
    assert "### Behind the scenes" in body


def test_stamp_seeds_consumers_frontmatter(kit_target: Path) -> None:
    """The stamped storyboard's frontmatter declares the agent as a consumer."""
    _make_folder_agent(kit_target, "project", "specific-agent")
    target = storyboards.stamp_new_storyboard(kit_target, "agent", "specific-agent")
    body = target.read_text(encoding="utf-8")
    assert "consumers:" in body
    assert "kind: agent" in body
    assert "name: specific-agent" in body
    assert "namespace: project" in body


def test_stamp_seeds_kind_and_name_in_template_comment(kit_target: Path) -> None:
    """The template body still surfaces the consumer info in a comment for readers."""
    _make_folder_agent(kit_target, "project", "specific-agent")
    target = storyboards.stamp_new_storyboard(kit_target, "agent", "specific-agent")
    body = target.read_text(encoding="utf-8")
    assert "agent: project/specific-agent" in body


def test_stamp_refuses_existing_storyboard(kit_target: Path) -> None:
    _make_folder_agent(kit_target, "project", "agent-a")
    storyboards.stamp_new_storyboard(kit_target, "agent", "agent-a")
    with pytest.raises(click.ClickException, match="already exists"):
        storyboards.stamp_new_storyboard(kit_target, "agent", "agent-a")


def test_stamp_refuses_unknown_agent(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="no agent named"):
        storyboards.stamp_new_storyboard(kit_target, "agent", "nope")


def test_stamp_refuses_invalid_name(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="kebab-case"):
        storyboards.stamp_new_storyboard(kit_target, "agent", "BadName")


def test_stamp_refuses_invalid_scenario_slug(kit_target: Path) -> None:
    _make_folder_agent(kit_target, "project", "agent-a")
    with pytest.raises(click.ClickException, match="kebab-case"):
        storyboards.stamp_new_storyboard(
            kit_target, "agent", "agent-a", scenario="Bad_Scenario"
        )


def test_stamp_refuses_when_agents_area_missing(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    with pytest.raises(click.ClickException, match="does not exist"):
        storyboards.stamp_new_storyboard(tmp_path, "agent", "foo")


def test_stamp_dry_run_writes_nothing(kit_target: Path) -> None:
    _make_folder_agent(kit_target, "project", "agent-a")
    target = storyboards.stamp_new_storyboard(
        kit_target, "agent", "agent-a", dry_run=True
    )
    assert not target.exists(), "dry-run wrote the storyboard"


def test_stamp_dry_run_does_not_migrate_flat_agent(kit_target: Path) -> None:
    """Dry-run on a flat agent reports intent without performing the migration."""
    flat = _make_flat_agent(kit_target, "project", "still-flat")
    storyboards.stamp_new_storyboard(
        kit_target, "agent", "still-flat", dry_run=True
    )
    assert flat.is_file(), "dry-run migrated the agent to folder form"


def test_stamp_project_wins_over_core_collision(kit_target: Path) -> None:
    """When an agent name exists in both namespaces, project wins (mirrors deploy)."""
    _make_folder_agent(kit_target, "core", "shared")
    _make_folder_agent(kit_target, "project", "shared")

    target = storyboards.stamp_new_storyboard(kit_target, "agent", "shared")
    assert ".pkit/agents/project/shared/" in str(target)


def test_stamp_rejects_unknown_artifact_kind() -> None:
    """The handler-dispatch raises for kinds not yet supported."""
    # The CLI Choice already prevents this; the module-level check is the second line of defense.
    with pytest.raises(click.ClickException, match="unknown artifact-kind"):
        storyboards.stamp_new_storyboard(Path("/tmp"), "cli", "anything")  # type: ignore[arg-type]


# --- CLI wiring -----------------------------------------------------


def test_cli_stamps_storyboard(kit_target: Path) -> None:
    _make_folder_agent(kit_target, "project", "my-agent")
    runner = CliRunner()
    result = runner.invoke(main, ["new", "storyboard", "agent", "my-agent"])
    assert result.exit_code == 0, result.output
    assert "Stamped:" in result.output
    assert "storyboard.md" in result.output


def test_cli_scenario_flag(kit_target: Path) -> None:
    _make_folder_agent(kit_target, "core", "reviewer")
    runner = CliRunner()
    result = runner.invoke(
        main, ["new", "storyboard", "agent", "reviewer", "--scenario", "sec-pr"]
    )
    assert result.exit_code == 0, result.output
    assert "sec-pr.storyboard.md" in result.output


def test_cli_dry_run_reports_intent(kit_target: Path) -> None:
    _make_folder_agent(kit_target, "project", "agent-a")
    runner = CliRunner()
    result = runner.invoke(
        main, ["new", "storyboard", "agent", "agent-a", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "Would stamp:" in result.output


def test_cli_rejects_unknown_artifact_kind(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["new", "storyboard", "bogus", "foo"])
    assert result.exit_code != 0
    # Click's Choice error.
    assert "Invalid value" in result.output or "is not one of" in result.output.lower()


def test_cli_refuses_outside_pkit_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["new", "storyboard", "agent", "anything"])
    assert result.exit_code != 0
