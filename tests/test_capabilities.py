"""Tests for capability install / uninstall / list (per COR-017)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import capabilities as caps
from project_kit import install as install_mod
from project_kit.cli import main
from project_kit.manifest import BackboneManifest, write_backbone_manifest


# --- fixtures --------------------------------------------------------


def _stage_capability_in_source(
    source_kit: Path,
    name: str,
    *,
    version: str = "0.1.0",
    description: str = "Test capability.",
    requires_backbone: str = ">=0.1.0,<99.0.0",
    with_skills: tuple[str, ...] = (),
    with_agents: tuple[str, ...] = (),
    with_decisions: tuple[str, ...] = (),
    with_project_files: dict[str, str] | None = None,
) -> Path:
    """Materialise a capability at <source_kit>/capabilities/<name>/.

    `with_project_files` maps a path relative to the capability's
    adopter-owned `project/` subtree to its seed content.
    """
    cap_dir = source_kit / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"""schema_version: 1
component:
  kind: capability
  name: {name}
  version: {version}
description: {description}
requires_backbone: "{requires_backbone}"
""",
        encoding="utf-8",
    )
    (cap_dir / "README.md").write_text(f"# {name}\n\nTest capability.\n", encoding="utf-8")

    if with_skills:
        skills_dir = cap_dir / "skills"
        skills_dir.mkdir(exist_ok=True)
        for skill in with_skills:
            (skills_dir / f"{skill}.md").write_text(
                f"---\nname: {skill}\ndescription: t\n---\n# {skill}\n",
                encoding="utf-8",
            )

    if with_agents:
        agents_dir = cap_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        for agent in with_agents:
            (agents_dir / f"{agent}.md").write_text(
                f"---\nname: {agent}\ndescription: t\n---\n# {agent}\n",
                encoding="utf-8",
            )

    if with_decisions:
        decisions_dir = cap_dir / "decisions"
        decisions_dir.mkdir(exist_ok=True)
        for n, slug in enumerate(with_decisions, 1):
            num = str(n).zfill(3)
            (decisions_dir / f"DEC-{num}-{slug}.md").write_text(
                f"---\nid: DEC-{num}\ntitle: {slug}\nstatus: accepted\ndate: 2026-05-18\nauthor: t\n---\n# {slug}\n",
                encoding="utf-8",
            )

    if with_project_files:
        for rel, content in with_project_files.items():
            path = cap_dir / "project" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    return cap_dir


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal adopter project with `.pkit/` initialised."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")

    def _noop(_script: Path, _ctx: install_mod.InstallContext) -> None:
        return None

    monkeypatch.setattr(install_mod, "_run_adapter_primitive", _noop)
    install_mod.install_kit(tmp_path)
    return tmp_path


@pytest.fixture
def kit_source(tmp_path: Path) -> Path:
    """A scratch directory that masquerades as the kit source for capability lookups."""
    source = tmp_path / ".kit-source"
    source.mkdir()
    return source


# --- find_capability_in_source --------------------------------------


def test_find_capability_returns_source_when_exists(kit_source: Path) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    result = caps.find_capability_in_source(kit_source, "evidence")
    assert result is not None
    assert result.name == "evidence"
    assert result.package.version == "0.1.0"
    assert result.path == kit_source / "capabilities" / "evidence"


def test_find_capability_returns_none_when_absent(kit_source: Path) -> None:
    assert caps.find_capability_in_source(kit_source, "nope") is None


def test_find_capability_returns_none_on_invalid_name(kit_source: Path) -> None:
    """Capability names must be kebab-case; reject invalid ones up front."""
    _stage_capability_in_source(kit_source, "good")
    assert caps.find_capability_in_source(kit_source, "BadCase") is None
    assert caps.find_capability_in_source(kit_source, "with_underscore") is None


def test_find_capability_returns_none_when_package_yaml_is_not_capability_kind(
    kit_source: Path,
) -> None:
    cap_dir = kit_source / "capabilities" / "wrong-kind"
    cap_dir.mkdir(parents=True)
    (cap_dir / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: bundle\n  name: wrong-kind\n  version: 0.1.0\n",
        encoding="utf-8",
    )
    assert caps.find_capability_in_source(kit_source, "wrong-kind") is None


# --- list_capabilities ----------------------------------------------


def test_list_capabilities_empty_when_no_caps_in_source(
    kit_target: Path, kit_source: Path
) -> None:
    available, installed = caps.list_capabilities(kit_target, kit_source)
    assert available == []
    assert installed == []


def test_list_capabilities_shows_available_in_source(
    kit_target: Path, kit_source: Path
) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    _stage_capability_in_source(kit_source, "audit-log")
    available, installed = caps.list_capabilities(kit_target, kit_source)
    assert available == ["audit-log", "evidence"]
    assert installed == []


# --- is_installed / install / uninstall -----------------------------


def test_install_capability_copies_subtree_and_registers(
    kit_target: Path, kit_source: Path
) -> None:
    _stage_capability_in_source(
        kit_source,
        "evidence",
        with_skills=("add-evidence", "validate-evidence"),
        with_decisions=("citation-discipline",),
    )
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None

    installed_path = caps.install_capability(kit_target, source)

    expected = kit_target / ".pkit" / "capabilities" / "evidence"
    assert installed_path == expected
    assert expected.is_dir()
    assert (expected / "package.yaml").is_file()
    assert (expected / "skills" / "add-evidence.md").is_file()
    assert (expected / "skills" / "validate-evidence.md").is_file()
    assert (expected / "decisions" / "DEC-001-citation-discipline.md").is_file()
    assert (expected / "manifest.yaml").is_file()
    assert caps.is_installed(kit_target, "evidence")


def test_install_refuses_when_already_installed(
    kit_target: Path, kit_source: Path
) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)
    with pytest.raises(click.ClickException, match="already installed"):
        caps.install_capability(kit_target, source)


def test_install_dry_run_writes_nothing(kit_target: Path, kit_source: Path) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    path = caps.install_capability(kit_target, source, dry_run=True)
    # Path is returned but not written.
    assert not path.exists()
    assert not caps.is_installed(kit_target, "evidence")


def test_install_omits_skipped_artifacts(kit_target: Path, kit_source: Path) -> None:
    _stage_capability_in_source(
        kit_source,
        "evidence",
        with_skills=("add-evidence", "validate-evidence"),
    )
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(
        kit_target, source, skipped_artifacts=(("skill", "add-evidence"),)
    )
    expected = kit_target / ".pkit" / "capabilities" / "evidence"
    # The skipped skill is NOT in the installed tree.
    assert not (expected / "skills" / "add-evidence.md").exists()
    # The other skill IS.
    assert (expected / "skills" / "validate-evidence.md").is_file()


# --- refresh preserves the adopter-owned project/ subtree (COR-001) ----


def test_refresh_preserves_adopter_project_files(
    kit_target: Path, kit_source: Path
) -> None:
    """A `refresh_capability` (the sync path) must not clobber adopter-owned
    `project/` files with the shipped seed — the no-shared-files invariant."""
    _stage_capability_in_source(
        kit_source,
        "project-management",
        with_project_files={
            "config.yaml": "schema_version: 1\ndefault_branch: main\n",
            "workstreams.yaml": "schema_version: 1\nworkstreams: []\n",
        },
    )
    source = caps.find_capability_in_source(kit_source, "project-management")
    assert source is not None
    caps.install_capability(kit_target, source)

    installed = kit_target / ".pkit" / "capabilities" / "project-management"
    config = installed / "project" / "config.yaml"
    # Adopter customises the seeded config.
    config.write_text(
        "schema_version: 1\ndefault_branch: develop\ngh:\n  host: ghe.example.com\n",
        encoding="utf-8",
    )

    # Refresh from source (the seed still carries default_branch: main).
    caps.refresh_capability(kit_target, source)

    # The adopter's customisation survives — not overwritten by the seed.
    assert "default_branch: develop" in config.read_text(encoding="utf-8")
    assert "ghe.example.com" in config.read_text(encoding="utf-8")


def test_refresh_seeds_absent_project_file_and_refreshes_core(
    kit_target: Path, kit_source: Path
) -> None:
    """Refresh seeds a *new* project/ file the adopter lacks, and still
    refreshes core-owned files (new appears, removed disappears)."""
    _stage_capability_in_source(
        kit_source,
        "project-management",
        with_skills=("old-skill",),
        with_project_files={"config.yaml": "schema_version: 1\n"},
    )
    source = caps.find_capability_in_source(kit_source, "project-management")
    assert source is not None
    caps.install_capability(kit_target, source)

    installed = kit_target / ".pkit" / "capabilities" / "project-management"
    assert (installed / "skills" / "old-skill.md").is_file()

    # New source version: adds a project/ seed, swaps the skill. The helper
    # appends to the same source dir, so drop the old skill to model a
    # version that no longer ships it.
    (kit_source / "capabilities" / "project-management" / "skills" / "old-skill.md").unlink()
    _stage_capability_in_source(
        kit_source,
        "project-management",
        with_skills=("new-skill",),
        with_project_files={
            "config.yaml": "schema_version: 1\n",
            "workstreams.yaml": "schema_version: 1\nworkstreams: []\n",
        },
    )
    source = caps.find_capability_in_source(kit_source, "project-management")
    assert source is not None
    caps.refresh_capability(kit_target, source)

    # New project/ seed appears (was absent in the adopter).
    assert (installed / "project" / "workstreams.yaml").is_file()
    # Core-owned refresh: new skill appears, removed skill disappears.
    assert (installed / "skills" / "new-skill.md").is_file()
    assert not (installed / "skills" / "old-skill.md").exists()


def test_uninstall_capability_removes_and_deregisters(
    kit_target: Path, kit_source: Path
) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)
    assert caps.is_installed(kit_target, "evidence")

    caps.uninstall_capability(kit_target, "evidence")

    assert not (kit_target / ".pkit" / "capabilities" / "evidence").exists()
    assert not caps.is_installed(kit_target, "evidence")


def test_uninstall_refuses_when_not_installed(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="not installed"):
        caps.uninstall_capability(kit_target, "nope")


# --- collision detection --------------------------------------------


def test_detect_collisions_finds_skill_collision(
    kit_target: Path, kit_source: Path
) -> None:
    # Install a skill in the adopter's project-side area.
    project_skills = kit_target / ".pkit" / "skills" / "project"
    project_skills.mkdir(parents=True, exist_ok=True)
    (project_skills / "add-evidence.md").write_text(
        "---\nname: add-evidence\n---\n# Mine\n", encoding="utf-8"
    )
    _stage_capability_in_source(
        kit_source, "evidence", with_skills=("add-evidence", "no-collision")
    )
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None

    findings = caps.detect_collisions(kit_target, source)
    collision_names = [f.artifact_name for f in findings]
    assert "add-evidence" in collision_names
    assert "no-collision" not in collision_names


def test_detect_collisions_finds_agent_collision(
    kit_target: Path, kit_source: Path
) -> None:
    project_agents = kit_target / ".pkit" / "agents" / "project"
    project_agents.mkdir(parents=True, exist_ok=True)
    (project_agents / "coordinator.md").write_text(
        "---\nname: coordinator\n---\n# Mine\n", encoding="utf-8"
    )
    _stage_capability_in_source(kit_source, "pm", with_agents=("coordinator",))
    source = caps.find_capability_in_source(kit_source, "pm")
    assert source is not None

    findings = caps.detect_collisions(kit_target, source)
    assert len(findings) == 1
    assert findings[0].artifact_kind == "agent"
    assert findings[0].artifact_name == "coordinator"


def test_detect_no_collisions_when_clean(kit_target: Path, kit_source: Path) -> None:
    _stage_capability_in_source(
        kit_source, "evidence", with_skills=("unique-skill",)
    )
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    findings = caps.detect_collisions(kit_target, source)
    assert findings == []


# --- reference detection --------------------------------------------


def test_find_references_picks_up_citations(
    kit_target: Path, kit_source: Path
) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)
    # Adopter authored prose that cites the capability.
    (kit_target / "docs.md").write_text(
        "Per [evidence:DEC-001-citation-discipline], every claim is cited.\n",
        encoding="utf-8",
    )

    refs = caps.find_references(kit_target, "evidence")
    assert len(refs) == 1
    assert refs[0][0] == kit_target / "docs.md"
    assert "evidence:DEC-001" in refs[0][1]


def test_find_references_picks_up_path_refs(kit_target: Path, kit_source: Path) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)
    (kit_target / "run.sh").write_text(
        "#!/usr/bin/env bash\npython .pkit/capabilities/evidence/scripts/validate.py\n",
        encoding="utf-8",
    )

    refs = caps.find_references(kit_target, "evidence")
    paths = [str(p[0]) for p in refs]
    assert any("run.sh" in p for p in paths)


def test_find_references_skips_capability_own_files(
    kit_target: Path, kit_source: Path
) -> None:
    """The capability's own files shouldn't count as references to itself."""
    _stage_capability_in_source(
        kit_source, "evidence", with_decisions=("self-citing",)
    )
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)
    # Add a citation inside the capability's own file — should be ignored.
    cap_decision = (
        kit_target / ".pkit" / "capabilities" / "evidence" / "decisions"
        / "DEC-001-self-citing.md"
    )
    body = cap_decision.read_text() + "\nSee [evidence:DEC-001-self-citing].\n"
    cap_decision.write_text(body, encoding="utf-8")

    refs = caps.find_references(kit_target, "evidence")
    # No external refs; the capability's own file is excluded.
    assert refs == []


def test_find_references_sees_another_capability_project_config(
    kit_target: Path,
) -> None:
    """A capability's adopter-authored `project/` config is adopter content:
    if it cites another capability, uninstalling that capability must surface
    the reference. The scan must NOT skip capability-level `project/` files."""
    config = (
        kit_target / ".pkit" / "capabilities" / "alpha" / "project" / "config.yaml"
    )
    config.parent.mkdir(parents=True)
    config.write_text("note: depends on [evidence:DEC-001].\n", encoding="utf-8")

    refs = caps.find_references(kit_target, "evidence")

    assert any(path == config for path, _ in refs), (
        "uninstall ref-scan skipped an adopter-authored capability project/ "
        "config — the reference to 'evidence' was missed."
    )


def test_find_references_empty_when_no_refs(kit_target: Path, kit_source: Path) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)
    refs = caps.find_references(kit_target, "evidence")
    assert refs == []


# --- CLI wiring ------------------------------------------------------


def test_cli_list_capabilities_empty(kit_target: Path, kit_source: Path, monkeypatch) -> None:
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "list"])
    assert result.exit_code == 0
    assert "none ship in this kit version" in result.output


def test_cli_list_capabilities_shows_available(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    _stage_capability_in_source(kit_source, "audit")
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "list"])
    assert result.exit_code == 0
    assert "evidence" in result.output
    assert "audit" in result.output


def test_cli_install_capability_no_collisions(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    _stage_capability_in_source(
        kit_source, "evidence", with_skills=("add-evidence",)
    )
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "install", "evidence"])
    assert result.exit_code == 0, result.output
    assert "Installed capability 'evidence'" in result.output
    assert caps.is_installed(kit_target, "evidence")


def test_cli_install_capability_not_in_source_errors(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "install", "nonexistent"])
    assert result.exit_code != 0
    assert "no capability named 'nonexistent'" in result.output


def test_cli_uninstall_refuses_with_references(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    runner.invoke(main, ["capabilities", "install", "evidence"])
    (kit_target / "docs.md").write_text(
        "See [evidence:DEC-001-x].\n", encoding="utf-8"
    )

    result = runner.invoke(main, ["capabilities", "uninstall", "evidence"])
    assert result.exit_code != 0
    assert "Refusing" in result.output
    # Capability still installed.
    assert caps.is_installed(kit_target, "evidence")


def test_cli_uninstall_force_overrides(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    runner.invoke(main, ["capabilities", "install", "evidence"])
    (kit_target / "docs.md").write_text(
        "See [evidence:DEC-001-x].\n", encoding="utf-8"
    )

    result = runner.invoke(
        main, ["capabilities", "uninstall", "evidence", "--force"]
    )
    assert result.exit_code == 0, result.output
    assert "Removed capability 'evidence'" in result.output
    assert not caps.is_installed(kit_target, "evidence")


def test_cli_uninstall_clean_proceeds(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    _stage_capability_in_source(kit_source, "evidence")
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    runner.invoke(main, ["capabilities", "install", "evidence"])

    result = runner.invoke(main, ["capabilities", "uninstall", "evidence"])
    assert result.exit_code == 0, result.output
    assert "Removed capability 'evidence'" in result.output


def test_cli_uninstall_not_installed_errors(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "uninstall", "nothing"])
    assert result.exit_code != 0
    assert "not installed" in result.output


# --- pkit capabilities upgrade (per COR-017) ---------------------------


def test_detect_upgrade_collisions_excludes_self_collisions(
    kit_target: Path, kit_source: Path
) -> None:
    """The upgrade-only variant filters out collisions against the upgrading capability's own tree."""
    _stage_capability_in_source(kit_source, "evidence", with_skills=("add-evidence",))
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)

    # Standard detect_collisions sees the installed copy as a collision against itself.
    standard = caps.detect_collisions(kit_target, source)
    assert any(c.artifact_name == "add-evidence" for c in standard)

    # The upgrade variant filters those out.
    upgrade = caps.detect_upgrade_collisions(kit_target, source)
    assert not any(c.artifact_name == "add-evidence" for c in upgrade)


def test_detect_upgrade_collisions_surfaces_genuinely_new_collisions(
    kit_target: Path, kit_source: Path
) -> None:
    """A skill added in the upgraded source that collides with core/project content is flagged."""
    # Install v0.1 with one skill.
    _stage_capability_in_source(kit_source, "evidence", with_skills=("add-evidence",))
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)

    # Adopter writes a project-side skill of name "new-skill".
    project_skill = kit_target / ".pkit" / "skills" / "project" / "new-skill.md"
    project_skill.parent.mkdir(parents=True, exist_ok=True)
    project_skill.write_text("---\nname: new-skill\n---\n# New\n", encoding="utf-8")

    # The upgraded source adds "new-skill".
    (kit_source / "capabilities" / "evidence" / "skills" / "new-skill.md").write_text(
        "---\nname: new-skill\n---\n# From evidence\n", encoding="utf-8"
    )

    source_v2 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v2 is not None
    upgrade = caps.detect_upgrade_collisions(kit_target, source_v2)
    assert any(c.artifact_name == "new-skill" for c in upgrade)


def test_read_prior_skipped_artifacts_returns_empty_when_no_manifest(kit_target: Path) -> None:
    assert caps.read_prior_skipped_artifacts(kit_target, "nope") == ()


def test_cli_upgrade_capability_refreshes_in_place(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    """A v0.2.0 source replaces the v0.1.0 installed content; manifest tracks the new version."""
    _stage_capability_in_source(
        kit_source, "evidence", version="0.1.0", with_skills=("add-evidence",)
    )
    source_v1 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v1 is not None
    caps.install_capability(kit_target, source_v1)

    # Bump source to v0.2.0 with the same skill but new body.
    (kit_source / "capabilities" / "evidence" / "package.yaml").write_text(
        """schema_version: 1
component:
  kind: capability
  name: evidence
  version: 0.2.0
description: Test capability.
requires_backbone: ">=0.1.0,<99.0.0"
""",
        encoding="utf-8",
    )
    (kit_source / "capabilities" / "evidence" / "skills" / "add-evidence.md").write_text(
        "---\nname: add-evidence\ndescription: t\n---\n# v0.2 body\n",
        encoding="utf-8",
    )

    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "upgrade", "evidence"])
    assert result.exit_code == 0, result.output
    assert "v0.2.0" in result.output

    installed_skill = (
        kit_target / ".pkit" / "capabilities" / "evidence" / "skills" / "add-evidence.md"
    )
    assert "v0.2 body" in installed_skill.read_text(encoding="utf-8")


def test_cli_upgrade_capability_refuses_on_new_collisions_without_interactive(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    """When the upgraded source adds a colliding skill, refuse and suggest --interactive."""
    _stage_capability_in_source(
        kit_source, "evidence", version="0.1.0", with_skills=("add-evidence",)
    )
    source_v1 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v1 is not None
    caps.install_capability(kit_target, source_v1)

    # Adopter has a project skill "new-skill".
    project_skill = kit_target / ".pkit" / "skills" / "project" / "new-skill.md"
    project_skill.parent.mkdir(parents=True, exist_ok=True)
    project_skill.write_text(
        "---\nname: new-skill\n---\n# Adopter's skill\n", encoding="utf-8"
    )

    # Upgraded source adds "new-skill".
    (kit_source / "capabilities" / "evidence" / "skills" / "new-skill.md").write_text(
        "---\nname: new-skill\n---\n# From evidence v0.2\n", encoding="utf-8"
    )

    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "upgrade", "evidence"])
    assert result.exit_code != 0
    assert "collision" in result.output.lower()
    assert "--interactive" in result.output


def test_cli_upgrade_capability_interactive_with_skip(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    """--interactive prompts per collision; choosing skip records the skip-state."""
    _stage_capability_in_source(
        kit_source, "evidence", version="0.1.0", with_skills=("add-evidence",)
    )
    source_v1 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v1 is not None
    caps.install_capability(kit_target, source_v1)

    project_skill = kit_target / ".pkit" / "skills" / "project" / "conflict.md"
    project_skill.parent.mkdir(parents=True, exist_ok=True)
    project_skill.write_text(
        "---\nname: conflict\n---\n# Adopter's\n", encoding="utf-8"
    )
    (kit_source / "capabilities" / "evidence" / "skills" / "conflict.md").write_text(
        "---\nname: conflict\n---\n# From evidence\n", encoding="utf-8"
    )

    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    # Type "skip" for the one collision.
    result = runner.invoke(
        main, ["capabilities", "upgrade", "evidence", "--interactive"], input="skip\n"
    )
    assert result.exit_code == 0, result.output
    assert "Refreshed capability 'evidence'" in result.output
    # The colliding file was skipped — capability's tree does not contain it.
    skipped_path = (
        kit_target / ".pkit" / "capabilities" / "evidence" / "skills" / "conflict.md"
    )
    assert not skipped_path.exists()
    # Adopter's project skill is untouched.
    assert project_skill.read_text(encoding="utf-8") == "---\nname: conflict\n---\n# Adopter's\n"


def test_cli_upgrade_capability_not_installed_errors(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "upgrade", "ghost"])
    assert result.exit_code != 0
    assert "not installed" in result.output


def test_cli_upgrade_capability_orphan_in_source_errors(
    kit_target: Path, kit_source: Path, monkeypatch
) -> None:
    """If the capability is installed but no longer in source, error clearly."""
    _stage_capability_in_source(kit_source, "evidence")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)

    # Wipe the capability from source.
    import shutil

    shutil.rmtree(kit_source / "capabilities" / "evidence")

    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit_source)
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "upgrade", "evidence"])
    assert result.exit_code != 0
    assert "no longer ships from source" in result.output


# --- migrations during refresh (per COR-010 + COR-017) ---------------


def test_refresh_capability_runs_migrations_in_version_order(
    kit_target: Path, kit_source: Path
) -> None:
    """Migrations under <source>/migrations/<X.Y.0>/ run in semver order when bumping versions."""
    # Stage v0.1.0 and install.
    _stage_capability_in_source(kit_source, "evidence", version="0.1.0")
    source_v1 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v1 is not None
    caps.install_capability(kit_target, source_v1)

    # Source bumps to v0.3.0, ships migrations for 0.2.0 and 0.3.0.
    cap_dir = kit_source / "capabilities" / "evidence"
    (cap_dir / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: evidence\n  version: 0.3.0\n"
        'requires_backbone: ">=0.1.0,<99.0.0"\n',
        encoding="utf-8",
    )
    # Migrations write a trace file under target_root so we can verify
    # they ran AND ran in order.
    trace_file = kit_target / "migration-trace.txt"
    (cap_dir / "migrations" / "0.2.0").mkdir(parents=True)
    (cap_dir / "migrations" / "0.2.0" / "001-first.sh").write_text(
        f'#!/usr/bin/env bash\necho "0.2.0/001" >> "{trace_file}"\n',
        encoding="utf-8",
    )
    (cap_dir / "migrations" / "0.2.0" / "001-first.sh").chmod(0o755)
    (cap_dir / "migrations" / "0.3.0").mkdir(parents=True)
    (cap_dir / "migrations" / "0.3.0" / "001-second.sh").write_text(
        f'#!/usr/bin/env bash\necho "0.3.0/001" >> "{trace_file}"\n',
        encoding="utf-8",
    )
    (cap_dir / "migrations" / "0.3.0" / "001-second.sh").chmod(0o755)

    source_v3 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v3 is not None
    caps.refresh_capability(kit_target, source_v3)

    assert trace_file.is_file()
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert lines == ["0.2.0/001", "0.3.0/001"]


def test_refresh_capability_skips_already_applied_migrations(
    kit_target: Path, kit_source: Path
) -> None:
    """Migrations for minor versions ≤ installed version are not re-run."""
    # Stage v0.2.0 and install (so 0.2.0 is the recorded installed version).
    _stage_capability_in_source(kit_source, "evidence", version="0.2.0")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)

    cap_dir = kit_source / "capabilities" / "evidence"
    trace_file = kit_target / "migration-trace.txt"
    # Add a 0.2.0 migration AFTER install — should NOT run on next refresh
    # since 0.2.0 is already the installed version.
    (cap_dir / "migrations" / "0.2.0").mkdir(parents=True)
    (cap_dir / "migrations" / "0.2.0" / "001-already-applied.sh").write_text(
        f'#!/usr/bin/env bash\necho "0.2.0/001" >> "{trace_file}"\n',
        encoding="utf-8",
    )
    (cap_dir / "migrations" / "0.2.0" / "001-already-applied.sh").chmod(0o755)
    # Bump source to 0.3.0 with a fresh migration — only this should run.
    (cap_dir / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: evidence\n  version: 0.3.0\n"
        'requires_backbone: ">=0.1.0,<99.0.0"\n',
        encoding="utf-8",
    )
    (cap_dir / "migrations" / "0.3.0").mkdir(parents=True)
    (cap_dir / "migrations" / "0.3.0" / "001-new.sh").write_text(
        f'#!/usr/bin/env bash\necho "0.3.0/001" >> "{trace_file}"\n',
        encoding="utf-8",
    )
    (cap_dir / "migrations" / "0.3.0" / "001-new.sh").chmod(0o755)

    source_v3 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v3 is not None
    caps.refresh_capability(kit_target, source_v3)

    assert trace_file.is_file()
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert lines == ["0.3.0/001"], "only the post-installed-version migration should run"


def test_refresh_capability_halts_on_migration_failure(
    kit_target: Path, kit_source: Path
) -> None:
    """A migration script that exits non-zero halts the refresh; files are NOT updated."""
    _stage_capability_in_source(kit_source, "evidence", version="0.1.0")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)

    cap_dir = kit_source / "capabilities" / "evidence"
    (cap_dir / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: evidence\n  version: 0.2.0\n"
        'requires_backbone: ">=0.1.0,<99.0.0"\n',
        encoding="utf-8",
    )
    (cap_dir / "migrations" / "0.2.0").mkdir(parents=True)
    (cap_dir / "migrations" / "0.2.0" / "001-fails.sh").write_text(
        '#!/usr/bin/env bash\necho "boom" >&2\nexit 1\n',
        encoding="utf-8",
    )
    (cap_dir / "migrations" / "0.2.0" / "001-fails.sh").chmod(0o755)

    source_v2 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v2 is not None

    with pytest.raises(click.ClickException, match="exited with status 1"):
        caps.refresh_capability(kit_target, source_v2)

    # Manifest still records the OLD version since the refresh halted before re-stamping.
    installed = caps._read_installed_capability_version(kit_target, "evidence")
    assert installed == "0.1.0"


def test_refresh_capability_with_no_migrations_is_clean(
    kit_target: Path, kit_source: Path
) -> None:
    """A version bump without any migrations succeeds; no migration output emitted."""
    _stage_capability_in_source(kit_source, "evidence", version="0.1.0")
    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None
    caps.install_capability(kit_target, source)

    (kit_source / "capabilities" / "evidence" / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: evidence\n  version: 0.2.0\n"
        'requires_backbone: ">=0.1.0,<99.0.0"\n',
        encoding="utf-8",
    )

    source_v2 = caps.find_capability_in_source(kit_source, "evidence")
    assert source_v2 is not None
    refreshed = caps.refresh_capability(kit_target, source_v2)
    assert refreshed.is_dir()
    installed = caps._read_installed_capability_version(kit_target, "evidence")
    assert installed == "0.2.0"


def test_pending_migration_scripts_walks_version_window(
    kit_target: Path, kit_source: Path
) -> None:
    """The version walker filters strictly (installed, source]."""
    _stage_capability_in_source(kit_source, "evidence", version="0.5.0")
    cap_dir = kit_source / "capabilities" / "evidence"

    for minor in ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0"):
        (cap_dir / "migrations" / minor).mkdir(parents=True)
        (cap_dir / "migrations" / minor / f"001-{minor}.sh").write_text(
            "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
        )

    source = caps.find_capability_in_source(kit_source, "evidence")
    assert source is not None

    # Installed at 0.2.0 → expect 0.3.0, 0.4.0, 0.5.0 (0.6.0 is past source).
    scripts = caps._pending_migration_scripts(source, "0.2.0")
    versions = [s.parent.name for s in scripts]
    assert versions == ["0.3.0", "0.4.0", "0.5.0"]

    # Installed unknown → run every shipped migration up to source.
    scripts_unknown = caps._pending_migration_scripts(source, None)
    versions_unknown = [s.parent.name for s in scripts_unknown]
    assert versions_unknown == ["0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0"]
