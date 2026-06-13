"""Tests for `pkit status` (the Python port of the bash dispatcher's `cmd_status`)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import install
from project_kit.cli import status


@pytest.fixture
def empty_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with no `.pkit/` — status should report not-installed."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    return tmp_path


@pytest.fixture
def installed_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with the kit installed — status should report installed."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")

    def _noop(_script: Path, _ctx: install.InstallContext) -> None:
        return None

    monkeypatch.setattr(install, "_run_adapter_primitive", _noop)
    install.install_kit(tmp_path)
    return tmp_path


def test_status_outside_a_project_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Status from a directory with no .git/ and no .pkit/ should error."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "/nonexistent")  # force find_target_root to None
    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code != 0
    assert isinstance(result.exception, click.ClickException) or "not inside a project tree" in (
        result.output
        + (
            result.exception.format_message()
            if isinstance(result.exception, click.ClickException)
            else ""
        )
    )


def test_status_reports_not_installed_when_pkit_dir_missing(empty_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    assert "project-kit is NOT installed in this project." in result.output
    assert "Project root:" in result.output
    assert str(empty_target) in result.output


def test_status_reports_installed_after_install_kit(installed_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    out = result.output

    assert "Kit installed at:" in out
    assert "Adapter: claude-code" in out
    assert "Capabilities" in out
    assert "Decisions" in out
    assert "Skills" in out

    # Counts should be non-zero for the installed state (decisions and skills
    # both ship core/ content).
    assert "core" in out
    assert "records" in out


def test_status_uses_pkit_source_bin_env_var(installed_target: Path) -> None:
    """The bash shim passes `PKIT_SOURCE_BIN`; status should echo that path."""
    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    assert "Source pkit:" in result.output
    assert "/fake/pkit" in result.output


def test_status_detects_kit_skill_in_per_name_dir_symlink_form(installed_target: Path) -> None:
    """Per COR-015, kit skills deploy as `.claude/skills/<name>/SKILL.md` symlinks.

    The status walker must recognise this shape as kit-managed, not as
    user content. Pre-fix behaviour misread the real directory and listed
    every kit skill under "user-managed".
    """
    name = "decision-author"
    deploy_dir = installed_target / ".claude" / "skills" / name
    deploy_dir.mkdir(parents=True, exist_ok=True)
    inner = deploy_dir / "SKILL.md"
    if not inner.exists():
        inner.symlink_to(f"../../../.pkit/skills/core/{name}.md")

    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    out = result.output
    assert "kit-managed" in out
    assert f"{name} ->" in out
    # The name must NOT appear under "user-managed".
    kit_block, _, rest = out.partition("user-managed")
    assert name in kit_block


def test_status_reports_agents_inventory(installed_target: Path) -> None:
    """After install with the agents area present, status reports core/project counts."""
    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    assert "Agents" in result.output


def test_status_detects_kit_managed_agent_copy(installed_target: Path) -> None:
    """Kit-managed agents are detected via the deploy-time marker on the resolved copy."""
    name = "methodology-reviewer"
    deployed = installed_target / ".claude" / "agents" / f"{name}.md"
    deployed.parent.mkdir(parents=True, exist_ok=True)
    deployed.write_text(
        f"---\n# managed-by: project-kit (deploy-agents.sh) — do not edit\n"
        f"name: {name}\n---\nresolved body\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    out = result.output
    assert "agents deployed" in out
    # The name must appear under kit-managed, not user-managed.
    kit_block, _, _ = out.partition("user-managed")
    assert name in kit_block


def test_status_classifies_unmarked_name_collision_as_user_managed(
    installed_target: Path,
) -> None:
    """An adopter-authored file with a kit name but no marker is user content.

    Regression: prior status logic classified by name alone, so a
    restored adopter `product-manager.md` showed as kit-managed even
    though deploy-agents had correctly preserved it as user content.
    """
    name = "methodology-reviewer"  # a real kit-shipped agent name
    deployed = installed_target / ".claude" / "agents" / f"{name}.md"
    deployed.parent.mkdir(parents=True, exist_ok=True)
    # No marker — adopter authored this themselves.
    deployed.write_text(
        f"---\nname: {name}\ndescription: my own version\n---\n# Mine\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    out = result.output
    # Should NOT appear in the kit-managed block.
    kit_block, _, user_block = out.partition("user-managed")
    assert name not in kit_block
    assert name in user_block


def test_status_classifies_unknown_agent_as_user_managed(installed_target: Path) -> None:
    """Agents at `.claude/agents/` whose name doesn't match a source kit agent are user content."""
    deployed = installed_target / ".claude" / "agents" / "my-custom-agent.md"
    deployed.parent.mkdir(parents=True, exist_ok=True)
    deployed.write_text("---\nname: my-custom-agent\n---\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    assert "my-custom-agent" in result.output
    # Must show up in the user-managed section, not kit-managed.
    _, _, user_block = result.output.partition("user-managed")
    assert "my-custom-agent" in user_block


def test_status_counts_flat_form_skills_in_source(installed_target: Path) -> None:
    """Source skill count must include flat `<name>.md` files (post-COR-015)."""
    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    out = result.output

    # Find the Skills inventory block.
    skills_idx = out.find("\n  Skills\n")
    assert skills_idx != -1, "Skills section missing from status output"
    skills_block = out[skills_idx : skills_idx + 200]
    # Expect a non-zero core count given the install bundles core skills.
    import re

    match = re.search(r"core\s+(\d+)", skills_block)
    assert match is not None, f"could not parse core skill count from: {skills_block!r}"
    assert int(match.group(1)) >= 1, "expected at least one core skill in inventory"


def test_status_reports_backbone_version_up_to_date(installed_target: Path) -> None:
    """Fresh install stamps the manifest with the current source version → up to date."""
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert "Backbone version:" in result.output
    assert "up to date" in result.output


def test_status_reports_backbone_version_when_behind(installed_target: Path) -> None:
    """A manifest behind the source shows the source version + the upgrade hint."""
    import re
    manifest = installed_target / ".pkit" / "manifest.yaml"
    manifest.write_text(
        re.sub(r"backbone_version:.*", "backbone_version: 0.1.0", manifest.read_text()),
        encoding="utf-8",
    )
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert "Backbone version:      0.1.0" in result.output
    assert "pkit upgrade --dry-run" in result.output
