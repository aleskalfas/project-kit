"""Tests for `pkit status` (the Python port of the bash dispatcher's `cmd_status`)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import data_points as dp
from project_kit.cli import main, status
from project_kit.status import _data_point_lines, _skill_owner
from tests.adopter_repo import MakeAdopterRepo
from tests.shipped_rule_sets import shipped_rules


@pytest.fixture
def empty_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with no `.pkit/` — status should report not-installed."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    return tmp_path


@pytest.fixture
def installed_target(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with the kit installed — status should report installed."""
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    return make_adopter_repo().root


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


OWN = "the project's own, which pkit does not deploy:"
ITEM = " " * 25  # the indent of an entry listed under a status line's label
MARKER = "# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync"


def _deploy_skill(root: Path, name: str, source: str) -> None:
    """`.claude/skills/<name>/SKILL.md` linked to `source`, as deploy-skills.sh links it."""
    folder = root / ".claude" / "skills" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").symlink_to(f"../../../{source}")


def _deploy_agent(root: Path, name: str, *, marked: bool = True) -> None:
    """`.claude/agents/<name>.md`, carrying deploy-agents.sh's marker when `marked`."""
    path = root / ".claude" / "agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = f"{MARKER}\n" if marked else ""
    path.write_text(f"---\n{marker}name: {name}\n---\nbody\n", encoding="utf-8")


def _deployed(output: str) -> list[str]:
    """The adapter section's lines after `settings.json`."""
    return _section(output, "Adapter: claude-code").splitlines()[1:]


def test_status_detects_kit_skill_in_per_name_dir_symlink_form(installed_target: Path) -> None:
    """Per COR-015, kit skills deploy as `.claude/skills/<name>/SKILL.md` symlinks.

    The status walker must recognise this shape as deployed from core, not as
    the project's own. Pre-fix behaviour misread the real directory and listed
    every kit skill as the project's.
    """
    name = "decision-author"
    _deploy_skill(installed_target, name, f".pkit/skills/core/{name}.md")

    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    out = result.output
    assert "1 deployed from core:" in out
    assert f"{name} ->" in out
    kit_block, _, _rest = out.partition(OWN)
    assert name in kit_block


def test_status_names_the_deploy_commands_when_nothing_is_deployed(installed_target: Path) -> None:
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert _deployed(result.output) == [
        f"    {'skills':<18} 0 deployed (run 'pkit deploy-skills')",
        f"    {'agents':<18} 0 deployed (run 'pkit deploy-agents')",
    ]


def test_status_lists_a_capabilitys_skills_and_agents_under_the_capability(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A skill linked into a capability's `skills/`, and a marked agent copy a
    capability ships, are listed under that capability, never as the project's
    own (#2085). Only what the project added itself is the project's own."""
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    root = make_adopter_repo(capabilities=("project-management",)).root
    _deploy_skill(root, "decision-author", ".pkit/skills/core/decision-author.md")
    _deploy_skill(root, "pm", ".pkit/capabilities/project-management/skills/pm/pm.md")
    notes = root / ".claude" / "skills" / "my-notes"
    notes.mkdir(parents=True)
    (notes / "SKILL.md").write_text("---\nname: my-notes\n---\n", encoding="utf-8")
    _deploy_agent(root, "critic")
    _deploy_agent(root, "project-manager")
    _deploy_agent(root, "my-agent", marked=False)

    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    pad = " " * 18
    assert _deployed(result.output) == [
        f"    {'skills':<18} 1 deployed from core:",
        f"{ITEM}decision-author -> ../../../.pkit/skills/core/decision-author.md",
        f"    {pad} 1 deployed from capability project-management:",
        f"{ITEM}pm -> ../../../.pkit/capabilities/project-management/skills/pm/pm.md",
        f"    {pad} 1 {OWN}",
        f"{ITEM}my-notes",
        f"    {'agents':<18} 1 deployed from core:",
        f"{ITEM}critic",
        f"    {pad} 1 deployed from capability project-management:",
        f"{ITEM}project-manager",
        f"    {pad} 1 {OWN}",
        f"{ITEM}my-agent",
    ]


def test_status_lists_the_project_namespace_last_and_a_copy_nothing_ships_apart(
    installed_target: Path,
) -> None:
    """What deploys from the project namespace is listed after core's, and a
    marked copy whose source is gone is what the next deploy removes, not the
    project's own."""
    (installed_target / ".pkit" / "agents" / "project" / "my-reviewer.md").write_text(
        "---\nname: my-reviewer\n---\n", encoding="utf-8"
    )
    _deploy_skill(installed_target, "my-skill", ".pkit/skills/project/my-skill.md")
    _deploy_skill(installed_target, "schema", ".pkit/skills/core/schema/schema.md")
    _deploy_agent(installed_target, "my-reviewer")
    _deploy_agent(installed_target, "critic")
    _deploy_agent(installed_target, "retired-agent")

    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    pad = " " * 18
    assert _deployed(result.output) == [
        f"    {'skills':<18} 1 deployed from core:",
        f"{ITEM}schema -> ../../../.pkit/skills/core/schema/schema.md",
        f"    {pad} 1 deployed from the project namespace:",
        f"{ITEM}my-skill -> ../../../.pkit/skills/project/my-skill.md",
        f"    {'agents':<18} 1 deployed from core:",
        f"{ITEM}critic",
        f"    {pad} 1 deployed from the project namespace:",
        f"{ITEM}my-reviewer",
        f"    {pad} 1 no longer shipped, which the next `pkit sync` removes:",
        f"{ITEM}retired-agent",
    ]


@pytest.mark.parametrize(
    ("link", "owner"),
    [
        ("../../../.pkit/skills/core/decision-author.md", "core"),
        ("../../../.pkit/skills/project/mine/mine.md", "project"),
        # The form before COR-015: the deployed folder is itself the link.
        ("../../.pkit/skills/core/schema", "core"),
        ("../../../.pkit/capabilities/project-management/skills/pm/pm.md", "project-management"),
        ("/repo/.pkit/capabilities/living-docs/skills/docs-author.md", "living-docs"),
        ("../../../.pkit/capabilities/project-management/agents/pm.md", None),
        ("../../../.pkit/skills/other/x.md", None),
        ("../../../my-skills/notes.md", None),
    ],
)
def test_a_skill_belongs_to_where_its_link_leads(link: str, owner: str | None) -> None:
    assert _skill_owner(link) == owner


def test_status_reports_agents_inventory(installed_target: Path) -> None:
    """After install with the agents area present, status reports core/project counts."""
    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    assert "Agents" in result.output


def test_status_detects_kit_managed_agent_copy(installed_target: Path) -> None:
    """Kit-managed agents are detected via the deploy-time marker on the resolved copy."""
    name = "methodology-reviewer"
    _deploy_agent(installed_target, name)

    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    out = result.output
    assert f"{'agents':<18} 1 deployed from core:" in out
    kit_block, _, _ = out.partition(OWN)
    assert name in kit_block


def test_status_classifies_unmarked_name_collision_as_the_projects_own(
    installed_target: Path,
) -> None:
    """An adopter-authored file with a kit name but no marker is the project's own.

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
    kit_block, _, user_block = out.partition(OWN)
    assert name not in kit_block
    assert name in user_block


def test_status_classifies_unknown_agent_as_the_projects_own(installed_target: Path) -> None:
    """Agents at `.claude/agents/` whose name doesn't match a source kit agent are the project's."""
    _deploy_agent(installed_target, "my-custom-agent", marked=False)

    runner = CliRunner()
    result = runner.invoke(status, [])
    assert result.exit_code == 0
    assert "my-custom-agent" in result.output
    _, _, user_block = result.output.partition(OWN)
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


def test_status_shows_no_transition_line_when_complete_and_current(installed_target: Path) -> None:
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert "Transition:" not in result.output
    assert "A transition moves:" not in result.output


@pytest.mark.parametrize(
    ("completion", "shown"),
    [
        ("", "incomplete — no readable completion is recorded, so `pkit upgrade` runs"),
        # A completion that is no version reads as none, as upgrade reads it.
        ("completed_version: garbage\n", "incomplete — no readable completion is recorded"),
        ("completed_version: 0.1.0\n", "incomplete — completed_version is 0.1.0;"),
    ],
)
def test_status_shows_an_incomplete_transition_beside_the_backbone_line(
    installed_target: Path, completion: str, shown: str
) -> None:
    """A missing completion, or one behind the target, reads as incomplete, and the
    line names `pkit upgrade`, which finishes it (ADR-065 point 8). The backbone
    line then calls its version the target, not up to date."""
    import re

    manifest = installed_target / ".pkit" / "manifest.yaml"
    manifest.write_text(
        re.sub(r"(?m)^completed_version:.*\n", completion, manifest.read_text()),
        encoding="utf-8",
    )
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert f"Transition:            {shown}" in result.output
    assert "(the target of an incomplete transition)" in result.output
    assert "up to date" not in result.output


def test_status_says_a_record_newer_than_the_bundle_is_never_moved_down(
    installed_target: Path,
) -> None:
    import re

    record = installed_target / ".pkit" / "adapters" / "claude-code" / "project" / "manifest.yaml"
    record.write_text(
        re.sub(r"(?m)^  version: .*$", "  version: 99.0.0", record.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert "adapter claude-code: 99.0.0, newer than " in result.output
    assert "never moved down" in result.output
    # Nothing listed moves up, so status points at no command that would do nothing.
    assert "a transition never moves a record down)" in result.output
    assert "`pkit upgrade` moves each one up" not in result.output


def test_status_names_upgrade_for_an_empty_backbone_version(installed_target: Path) -> None:
    import re

    manifest = installed_target / ".pkit" / "manifest.yaml"
    manifest.write_text(
        re.sub(r"(?m)^backbone_version:.*$", "backbone_version:", manifest.read_text()),
        encoding="utf-8",
    )
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert "unknown (`backbone_version` is empty — `pkit upgrade` records its version)" in (
        result.output
    )


def test_status_lists_each_component_a_transition_would_move(installed_target: Path) -> None:
    """An adapter with no record, and a shipped capability recorded at another version
    than its bundle's, are each listed with both versions (ADR-065 point 8)."""
    (installed_target / ".pkit" / "adapters" / "claude-code" / "project" / "manifest.yaml").unlink()
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert "A transition moves:    adapter claude-code: no record -> " in result.output
    assert "`pkit upgrade` moves each one up)" in result.output


def test_status_shows_no_transition_line_in_the_methodology_source(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No transition runs in the methodology's source, so neither line applies there
    (ADR-065 point 3)."""
    from project_kit import install

    manifest = installed_target / ".pkit" / "manifest.yaml"
    manifest.write_text(
        "\n".join(
            line for line in manifest.read_text().splitlines() if "completed_version" not in line
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(install, "is_self_host", lambda *_args: True)
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert "Transition:" not in result.output


# --- rule sets (COR-051 point 7) ---------------------------------------------------

PROJECT_SETS = "docs/rule-sets"


def _rule_set(name: str, version: str, *pins: str) -> str:
    """A rule-set file with no rules, pinning `pins`."""
    inherits = f"inherits: [{', '.join(pins)}]\n" if pins else ""
    return f"---\nrule-set: {name}\nversion: {version}\n{inherits}rules: {{}}\n---\n"


def _section(output: str, heading: str) -> str:
    """The lines of one status section, from its heading to the next blank line."""
    return output.split(f"\n  {heading}\n", 1)[1].split("\n\n", 1)[0]


def test_status_reports_the_shipped_rule_sets_alone_on_a_fresh_install(
    installed_target: Path,
) -> None:
    """A fresh install holds the backbone's rule sets alone, which pin nothing (COR-068;
    ADR-073 point 1)."""
    rules = len(shipped_rules(installed_target))
    assert rules > 0
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    assert _section(result.output, "Rule sets").splitlines() == [
        f"    {'found':<18} 1 rule set(s), {rules} rule(s)",
        f"    {'pins':<18} none",
    ]


def test_status_shows_each_pin_behind_the_inherited_major_with_the_fix(
    installed_target: Path,
) -> None:
    sets = installed_target / PROJECT_SETS
    sets.mkdir(parents=True)
    (sets / "cmn.md").write_text(_rule_set("CMN", "2.1.0"), encoding="utf-8")
    (sets / "doc.md").write_text(_rule_set("DOC", "1.0.0", "CMN@1"), encoding="utf-8")
    (sets / "app.md").write_text(_rule_set("APP", "1.0.0", "CMN@2"), encoding="utf-8")

    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    fix = (
        f"review what changed in CMN, then update the pin to CMN@2 in `inherits` of "
        f"{PROJECT_SETS}/doc.md"
    )
    shipped = len(shipped_rules(installed_target))  # the backbone's set, beside the three
    assert _section(result.output, "Rule sets").splitlines() == [
        f"    {'found':<18} 4 rule set(s), {shipped} rule(s)",
        f"    {'pins':<18} 2 checked, 1 behind the inherited set's major:",
        "                         DOC pins CMN@1; CMN is at 2.1.0",
        f"                           fix: {fix}",
    ]

    # Beside the failure `pkit validate` already reports on the same pin, with the same fix.
    validated = CliRunner().invoke(main, ["validate", "--only", "versions"])
    assert validated.exit_code == 1, validated.output
    assert f"{PROJECT_SETS}/doc.md:/inherits/0" in validated.output
    assert fix in validated.output

    # The fix applied: every pin current, and nothing listed.
    (sets / "doc.md").write_text(_rule_set("DOC", "1.0.0", "CMN@2"), encoding="utf-8")
    repinned = CliRunner().invoke(status, [])
    assert _section(repinned.output, "Rule sets").splitlines()[1] == (
        f"    {'pins':<18} 2 checked, all current"
    )


# --- a data point's filler line (COR-052 point 7) ---------------------------------


def test_a_filler_that_reads_beyond_the_working_tree_names_what_and_at_which_commit() -> None:
    head, tip = "a" * 40, "b" * 40

    def filler(name: str, *reads: dp.FillerRead) -> dp.Filler:
        return dp.Filler(
            dp.FillerSource.CONTRIBUTION,
            name,
            "command 'export'",
            dp.FillerState.TAKEN,
            query_contract=True,
            reads=reads,
        )

    point = dp.ResolvedPoint(
        address="pkit::documentation:readers",
        provider="docs-a",
        policy="union",
        inert_policy="fail",
        participation=None,
        fillers=(
            filler(
                "evidence",
                dp.FillerRead("history", "HEAD", head, True),
                dp.FillerRead("settled", "origin/main", tip),
            ),
            filler("notes"),
        ),
        outcome=dp.Outcome.RESOLVED,
        value=[],
    )
    contract = "query contract declared: no network, trusted, not enforced"
    assert [line.strip() for line in _data_point_lines(point)[-2:]] == [
        f"filler   evidence (command 'export'; {contract}; reads history (HEAD {head[:12]}, "
        f"shallow clone) and the default branch (origin/main at {tip[:12]})): taken",
        f"filler   notes (command 'export'; {contract}): taken",
    ]
