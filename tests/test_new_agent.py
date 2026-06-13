"""Tests for `pkit new agent` (per COR-013 + COR-015)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import agents
from project_kit.cli import main


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal project tree with `.pkit/agents/{core,project}/`."""
    agents_dir = tmp_path / ".pkit" / "agents"
    for ns in ("core", "project"):
        (agents_dir / ns).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --- stamp_new_agent (deterministic layer) ---------------------------


def test_stamp_creates_flat_file_in_core_namespace(kit_target: Path) -> None:
    target = agents.stamp_new_agent(kit_target, name="reviewer", namespace="core")
    assert target == kit_target / ".pkit" / "agents" / "core" / "reviewer.md"
    assert target.is_file()


def test_stamp_creates_flat_file_in_project_namespace(kit_target: Path) -> None:
    target = agents.stamp_new_agent(kit_target, name="my-agent", namespace="project")
    assert target == kit_target / ".pkit" / "agents" / "project" / "my-agent.md"
    assert target.is_file()


def test_stamp_seeds_frontmatter_and_canonical_body_sections(kit_target: Path) -> None:
    target = agents.stamp_new_agent(kit_target, name="qa-engineer", namespace="project")
    body = target.read_text(encoding="utf-8")

    # Frontmatter shape per COR-013.
    assert "---\n" in body
    assert "name: qa-engineer\n" in body
    assert "description:" in body
    assert "tools:" in body
    assert "reads:" in body
    assert "  paths:" in body
    assert "  records:" in body
    assert "  patterns:" in body
    assert "owns:" in body
    assert "needs:" in body

    # H1 derived from name (kebab → Title Case).
    assert "# Qa Engineer\n" in body

    # Canonical body sections per the agents README.
    assert "## When to invoke this agent" in body
    assert "## Files you own" in body
    assert "## Key documents to read" in body
    assert "## How you work" in body


def test_stamp_rejects_invalid_name(kit_target: Path) -> None:
    bad_names = [
        "BadCase",
        "trailing-",
        "-leading",
        "double--hyphen",
        "with_underscore",
        "with space",
        "1numeric-start",
    ]
    for name in bad_names:
        with pytest.raises(click.ClickException, match="kebab-case"):
            agents.stamp_new_agent(kit_target, name=name, namespace="project")


def test_stamp_accepts_valid_kebab_names(kit_target: Path) -> None:
    ok = ["reviewer", "qa-engineer", "a1", "agent2", "ui-ux-designer"]
    for i, name in enumerate(ok):
        # Use unique namespaces to avoid collision across iterations.
        ns = "core" if i % 2 == 0 else "project"
        target = agents.stamp_new_agent(kit_target, name=name, namespace=ns)
        assert target.is_file()


def test_stamp_refuses_existing_flat_file_in_same_namespace(kit_target: Path) -> None:
    agents.stamp_new_agent(kit_target, name="dup", namespace="project")
    with pytest.raises(click.ClickException, match="already exists"):
        agents.stamp_new_agent(kit_target, name="dup", namespace="project")


def test_stamp_refuses_collision_across_namespaces(kit_target: Path) -> None:
    """Project > core resolution means duplicate names silently mask. Refuse instead."""
    agents.stamp_new_agent(kit_target, name="shared", namespace="core")
    with pytest.raises(click.ClickException, match="already exists"):
        agents.stamp_new_agent(kit_target, name="shared", namespace="project")


def test_stamp_refuses_folder_form_collision(kit_target: Path) -> None:
    """COR-015 allows folder form too; stamping a flat file with the same name is a collision."""
    folder_form = kit_target / ".pkit" / "agents" / "core" / "legacy" / "legacy.md"
    folder_form.parent.mkdir(parents=True)
    folder_form.write_text("---\nname: legacy\n---\n", encoding="utf-8")

    with pytest.raises(click.ClickException, match="already exists"):
        agents.stamp_new_agent(kit_target, name="legacy", namespace="project")


def test_stamp_refuses_when_namespace_dir_missing(tmp_path: Path) -> None:
    """If `.pkit/agents/<namespace>/` doesn't exist, the stamp refuses with a clear message."""
    (tmp_path / ".pkit").mkdir()  # no agents/ subdir
    with pytest.raises(click.ClickException, match="does not exist"):
        agents.stamp_new_agent(tmp_path, name="foo", namespace="core")


def test_stamp_dry_run_writes_nothing(kit_target: Path) -> None:
    target = agents.stamp_new_agent(
        kit_target, name="ghost", namespace="project", dry_run=True
    )
    assert not target.exists(), "dry-run wrote a file"


# --- CLI wiring ------------------------------------------------------


def test_cli_new_agent_stamps_file(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["new", "agent", "project", "my-agent"])
    assert result.exit_code == 0, result.output
    assert "Stamped:" in result.output
    assert ".pkit/agents/project/my-agent.md" in result.output
    target = kit_target / ".pkit" / "agents" / "project" / "my-agent.md"
    assert target.is_file()


def test_cli_new_agent_dry_run_reports_intent(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["new", "agent", "core", "preview-agent", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Would stamp:" in result.output
    target = kit_target / ".pkit" / "agents" / "core" / "preview-agent.md"
    assert not target.exists()


def test_cli_new_agent_rejects_unknown_namespace(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["new", "agent", "bogus", "foo"])
    assert result.exit_code != 0
    # Click's Choice error.
    assert "Invalid value" in result.output or "is not one of" in result.output.lower()


def test_cli_new_agent_refuses_outside_pkit_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If invoked outside a tree with `.pkit/`, fail with a clear message."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["new", "agent", "project", "foo"])
    assert result.exit_code != 0
    output_lower = (
        result.output + (str(result.exception) if result.exception else "")
    ).lower()
    assert ".pkit/" in output_lower or "not in a project tree" in output_lower


# --- --with-storyboard ----------------------------------------------


def test_stamp_with_storyboard_creates_folder_form(kit_target: Path) -> None:
    """with_storyboard=True stamps folder layout with sibling storyboard.md."""
    target = agents.stamp_new_agent(
        kit_target, name="coordinator", namespace="project", with_storyboard=True
    )
    expected_agent = (
        kit_target / ".pkit" / "agents" / "project" / "coordinator" / "coordinator.md"
    )
    expected_storyboard = expected_agent.parent / "storyboard.md"

    assert target == expected_agent
    assert expected_agent.is_file()
    assert expected_storyboard.is_file()
    assert not (kit_target / ".pkit" / "agents" / "project" / "coordinator.md").exists()


def test_stamp_with_storyboard_seeds_storyboard_template(kit_target: Path) -> None:
    agents.stamp_new_agent(
        kit_target, name="reviewer", namespace="core", with_storyboard=True
    )
    storyboard = (
        kit_target / ".pkit" / "agents" / "core" / "reviewer" / "storyboard.md"
    )
    body = storyboard.read_text(encoding="utf-8")
    assert "## Framing" in body
    assert "## Tone" in body
    assert "## Scenario 1" in body


def test_stamp_with_storyboard_dry_run_writes_nothing(kit_target: Path) -> None:
    agents.stamp_new_agent(
        kit_target,
        name="ghost",
        namespace="project",
        with_storyboard=True,
        dry_run=True,
    )
    folder = kit_target / ".pkit" / "agents" / "project" / "ghost"
    assert not folder.exists()


def test_cli_new_agent_with_storyboard_flag(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main, ["new", "agent", "project", "my-coord", "--with-storyboard"]
    )
    assert result.exit_code == 0, result.output
    assert "my-coord.md" in result.output
    assert "storyboard.md" in result.output
    folder = kit_target / ".pkit" / "agents" / "project" / "my-coord"
    assert (folder / "my-coord.md").is_file()
    assert (folder / "storyboard.md").is_file()
