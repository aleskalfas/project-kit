"""Tests for the `pkit agents` diagnostic + reconcile (per COR-013).

Includes a guard that the backbone reference-detection key-set stays in sync
with the claude-code adapter's `_resolve_agent.py` — the (B) factoring's
anti-drift net.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import agents_overlay as ao
from project_kit.cli import main

REPO = Path(__file__).resolve().parent.parent


# --- anti-drift guard: backbone keys must match the adapter resolver ---------

def test_resolvable_keys_match_adapter_resolver():
    """The (B) backbone scan only stays correct if its resolvable-key set equals
    what `_resolve_agent.py` actually substitutes. Pin it."""
    resolver = (REPO / ".pkit" / "adapters" / "claude-code" / "_resolve_agent.py").read_text()
    # The adapter resolves these top-level list keys ...
    m_top = re.search(r'for key in \(([^)]*)\):', resolver)
    assert m_top, "could not find the top-level resolvable-key tuple in _resolve_agent.py"
    top_keys = tuple(re.findall(r'"([a-z]+)"', m_top.group(1)))
    # ... and these reads.* sub-keys.
    m_reads = re.search(r'for k in \(([^)]*)\):', resolver)
    assert m_reads, "could not find the reads.* resolvable-key tuple in _resolve_agent.py"
    reads_keys = tuple(re.findall(r'"([a-z]+)"', m_reads.group(1)))

    assert top_keys == ao.RESOLVABLE_LIST_KEYS
    assert reads_keys == ao.RESOLVABLE_READS_KEYS


# --- fixtures ----------------------------------------------------------------

def _agent(dir_: Path, name: str, *, owns=None, reads_paths=None, body="body") -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    fm = ["---"]
    if owns:
        fm.append("owns:")
        fm += [f"  - {x}" for x in owns]
    if reads_paths:
        fm += ["reads:", "  paths:"]
        fm += [f"    - {x}" for x in reads_paths]
    fm.append("---")
    (dir_ / f"{name}.md").write_text("\n".join(fm) + f"\n{body}\n", encoding="utf-8")
    return dir_ / f"{name}.md"


def _project(tmp_path: Path, *, overlay: str | None = None) -> Path:
    proj = tmp_path / "proj"
    (proj / ".pkit" / "agents" / "core").mkdir(parents=True)
    (proj / ".pkit" / "agents" / "project").mkdir(parents=True)
    if overlay is not None:
        (proj / ".pkit" / "agents" / "project" / "overlay.yaml").write_text(overlay, encoding="utf-8")
    return proj


# --- discovery + reference-detection -----------------------------------------

def test_referenced_categories_only_from_resolvable_keys(tmp_path):
    proj = _project(tmp_path, overlay="")
    src = _agent(proj / ".pkit" / "agents" / "core", "a",
                 owns=["<architecture-docs>"], reads_paths=["<workflow-docs>", "README.md"],
                 body="prose mentions <not-a-real-ref> which must be ignored")
    cats = ao.agent_referenced_categories(src)
    assert cats == {"architecture-docs", "workflow-docs"}  # body token NOT counted


def test_project_namespace_wins_over_core(tmp_path):
    proj = _project(tmp_path, overlay="")
    _agent(proj / ".pkit" / "agents" / "core", "dup", owns=["<core-cat>"])
    _agent(proj / ".pkit" / "agents" / "project", "dup", owns=["<proj-cat>"])
    found = ao.discover_kit_agents(proj)
    assert found["dup"][0] == "project"


# --- status ------------------------------------------------------------------

def test_missing_category_marks_agent_skipped(tmp_path):
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "needs-arch", owns=["<architecture-docs>"])
    statuses = {s.name: s for s in ao.agent_overlay_statuses(proj)}
    st = statuses["needs-arch"]
    assert not st.deployable
    assert st.missing == ("architecture-docs",)
    assert ao.missing_categories(proj) == ["architecture-docs"]


def test_per_agent_override_satisfies_reference(tmp_path):
    overlay = (
        "workflow-docs:\n  - README.md\n"
        "overrides:\n  special:\n    architecture-docs:\n      - docs/ARCH.md\n"
    )
    proj = _project(tmp_path, overlay=overlay)
    _agent(proj / ".pkit" / "agents" / "core", "special", owns=["<architecture-docs>"])
    st = {s.name: s for s in ao.agent_overlay_statuses(proj)}["special"]
    assert st.deployable  # override defines it, even though defaults don't


# --- reconcile ---------------------------------------------------------------

def test_reconcile_dry_run_does_not_write(tmp_path):
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>", "<adr-records>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"
    before = overlay.read_text()
    added, report = ao.reconcile_overlay(proj, write=False)
    assert set(added) == {"architecture-docs", "adr-records"}
    assert overlay.read_text() == before  # untouched
    assert "dry-run" in report


def test_reconcile_write_appends_commented_stubs_idempotently(tmp_path):
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    added, _ = ao.reconcile_overlay(proj, write=True)
    assert added == ["architecture-docs"]
    text = overlay.read_text()
    assert "# architecture-docs:" in text  # commented, not active
    # The category stays undefined → agent still skipped (commented = visible, not resolved).
    assert ao.missing_categories(proj) == ["architecture-docs"]

    # Idempotent: a second run adds nothing (the commented stub is detected).
    # Crucially, it must surface "uncomment + set real paths" guidance — never
    # a bare "nothing to add" that strands the adopter (regression for issue #40).
    added2, report2 = ao.reconcile_overlay(proj, write=True)
    assert added2 == []
    assert overlay.read_text() == text  # file unchanged
    assert "uncomment" in report2
    assert "pkit sync" in report2
    assert "overlay is complete" not in report2


# --- reconcile: three-state regression (issue #40) ---------------------------

def test_reconcile_missing_state_adds_stub(tmp_path):
    """State 1 (missing): category absent from overlay → stub is added."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    added, report = ao.reconcile_overlay(proj, write=True)

    assert "architecture-docs" in added
    assert "# architecture-docs:" in overlay.read_text()
    # Still missing from sync/deploy's perspective (commented ≠ defined).
    assert ao.missing_categories(proj) == ["architecture-docs"]


def test_reconcile_commented_stub_state_reports_guidance_no_duplicate(tmp_path):
    """State 2 (commented-stub): stub exists but unfilled → guidance shown, no
    duplicate stub written, file unchanged."""
    # Overlay already contains a commented stub for architecture-docs.
    overlay_text = (
        "workflow-docs:\n  - README.md\n"
        "# architecture-docs:\n"
        "#   - <path/relative/to/project/root>\n"
    )
    proj = _project(tmp_path, overlay=overlay_text)
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"
    before = overlay.read_text()

    added, report = ao.reconcile_overlay(proj, write=True)

    # No new stubs appended.
    assert added == []
    assert overlay.read_text() == before
    # Actionable guidance must be present — never a bare "nothing to add".
    assert "uncomment" in report
    assert "pkit sync" in report
    assert "overlay is complete" not in report
    # The category name must be called out.
    assert "architecture-docs" in report


def test_reconcile_defined_state_reports_complete(tmp_path):
    """State 3 (defined): uncommented entry with paths → overlay is complete."""
    overlay_text = (
        "workflow-docs:\n  - README.md\n"
        "architecture-docs:\n  - docs/ARCH.md\n"
    )
    proj = _project(tmp_path, overlay=overlay_text)
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])

    added, report = ao.reconcile_overlay(proj, write=True)

    assert added == []
    assert "overlay is complete" in report
    # Agent should now be deployable (not missing).
    assert ao.missing_categories(proj) == []


# --- CLI ---------------------------------------------------------------------

def test_cli_agents_lists_status(tmp_path, monkeypatch):
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "needs-arch", owns=["<architecture-docs>"])
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(main, ["agents"])
    assert result.exit_code == 0, result.output
    assert "needs-arch" in result.output
    assert "SKIPPED" in result.output
    assert "architecture-docs" in result.output


def test_cli_agents_skip_report_leads_with_adopt_and_names_reconcile(tmp_path, monkeypatch):
    """The pkit agents skip report leads with `pkit agents adopt` and names
    `pkit agents reconcile --write` as the custom-layout fallback alongside the
    overlay-file path (regression for issue #31; updated for issue #49)."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "needs-arch", owns=["<architecture-docs>"])
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(main, ["agents"])
    assert result.exit_code == 0, result.output
    assert "pkit agents adopt" in result.output
    assert "pkit agents reconcile --write" in result.output
    assert "overlay.yaml" in result.output


def test_cli_agents_never_load_bearing(tmp_path, monkeypatch):
    from project_kit import cli_render
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "needs-arch", owns=["<architecture-docs>"])
    monkeypatch.chdir(proj)
    always = CliRunner().invoke(main, ["--color", "always", "agents"]).output
    never = CliRunner().invoke(main, ["--color", "never", "agents"]).output
    assert "\033[" in always
    assert cli_render.strip_ansi(always) == never


# --- reconcile: detect-then-fill (issue #45) ---------------------------------

def test_reconcile_auto_fills_when_conventional_dir_exists(tmp_path):
    """State 4 (detect-then-fill): missing category + conventional default dir
    exists → written uncommented; agent becomes deployable after write."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    # Create the conventional default directory.
    (proj / "docs" / "architecture").mkdir(parents=True)

    added, report = ao.reconcile_overlay(proj, write=True)

    assert "architecture-docs" in added
    text = overlay.read_text()
    # Written uncommented — no leading `#` on the category key line.
    assert "architecture-docs:" in text
    assert "# architecture-docs:" not in text
    # Verify the conventional path was written.
    assert "docs/architecture" in text
    # Category is now defined → agent is deployable.
    assert ao.missing_categories(proj) == []


def test_reconcile_auto_fill_dry_run_does_not_write(tmp_path):
    """Dry-run with conventional dir present: reports what would be written but
    does not touch the file."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"
    before = overlay.read_text()

    (proj / "docs" / "architecture").mkdir(parents=True)

    added, report = ao.reconcile_overlay(proj, write=False)

    assert "architecture-docs" in added
    assert overlay.read_text() == before  # untouched
    assert "dry-run" in report
    assert "architecture-docs" in report


def test_reconcile_stubs_when_conventional_dir_absent(tmp_path):
    """Missing category without a conventional dir → commented stub (unchanged
    from issue #40 behaviour)."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    # Do NOT create docs/architecture.
    added, report = ao.reconcile_overlay(proj, write=True)

    assert "architecture-docs" in added
    text = overlay.read_text()
    # Must be commented — dir was absent so we can't auto-fill.
    assert "# architecture-docs:" in text
    # Category still missing from deploy's perspective.
    assert ao.missing_categories(proj) == ["architecture-docs"]
    assert "uncomment" in report


def test_reconcile_does_not_overwrite_adopter_set_value(tmp_path):
    """An adopter-set (uncommented, non-conventional) value is never clobbered."""
    overlay_text = (
        "workflow-docs:\n  - README.md\n"
        "architecture-docs:\n  - docs/custom-arch/\n"
    )
    proj = _project(tmp_path, overlay=overlay_text)
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"
    before = overlay.read_text()

    # Create conventional dir — reconcile must NOT overwrite the adopter value.
    (proj / "docs" / "architecture").mkdir(parents=True)

    added, report = ao.reconcile_overlay(proj, write=True)

    assert added == []
    assert overlay.read_text() == before  # unchanged
    assert "overlay is complete" in report
    # Confirm the adopter's custom path survived.
    assert "docs/custom-arch/" in overlay.read_text()


def test_reconcile_mixed_auto_fill_and_stub(tmp_path):
    """Two missing categories: one with the conventional dir present (auto-fill),
    one without (stub).  Both returned in added; correct form for each."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    # Agent references both architecture-docs and adr-records.
    _agent(proj / ".pkit" / "agents" / "core", "a",
           owns=["<architecture-docs>", "<adr-records>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    # Only architecture-docs conventional dir exists; adr-records dir does not.
    (proj / "docs" / "architecture").mkdir(parents=True)

    added, report = ao.reconcile_overlay(proj, write=True)

    assert set(added) == {"architecture-docs", "adr-records"}
    text = overlay.read_text()
    # architecture-docs → uncommented (dir existed).
    assert "architecture-docs:" in text
    assert "# architecture-docs:" not in text
    # adr-records → commented stub (dir absent).
    assert "# adr-records:" in text
    # Only architecture-docs is now deployable; adr-records still missing.
    assert ao.missing_categories(proj) == ["adr-records"]


def test_reconcile_auto_fill_idempotent(tmp_path):
    """After auto-fill, a second reconcile call reports 'overlay is complete'
    and does not re-append the category."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    (proj / "docs" / "architecture").mkdir(parents=True)

    ao.reconcile_overlay(proj, write=True)
    text_after_first = overlay.read_text()

    added2, report2 = ao.reconcile_overlay(proj, write=True)
    assert added2 == []
    assert overlay.read_text() == text_after_first  # unchanged
    assert "overlay is complete" in report2


def test_reconcile_conventional_defaults_map_covers_architect_categories():
    """The CONVENTIONAL_CATEGORY_DEFAULTS map must declare defaults for every
    category referenced by the core architect agent, matching the paths
    documented in that agent's prose."""
    architect_src = (
        REPO / ".pkit" / "agents" / "core" / "architect.md"
    )
    cats = ao.agent_referenced_categories(architect_src)
    # Both architect categories have a registered conventional default.
    for cat in cats:
        assert cat in ao.CONVENTIONAL_CATEGORY_DEFAULTS, (
            f"architect category <{cat}> has no entry in CONVENTIONAL_CATEGORY_DEFAULTS"
        )


# --- adopt (issue #47) -------------------------------------------------------

def _deploy_ok(target_root: Path, agent_name: str) -> bool:  # noqa: ARG001
    """Stub deploy_fn that always succeeds (avoids invoking deploy-agents.sh in tests)."""
    return True


def test_adopt_fresh_creates_dirs_and_wires_overlay(tmp_path):
    """Fresh adopt: conventional dirs created + overlay wired uncommented + deployed."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a",
           owns=["<architecture-docs>", "<adr-records>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    result = ao.adopt_agent(proj, "a", deploy_fn=_deploy_ok)

    # Both categories should be wired.
    assert set(result.categories_wired) == {"architecture-docs", "adr-records"}
    # Both conventional dirs were absent; adr-records is processed first (alphabetical),
    # its mkdir(parents=True) also creates docs/architecture, so architecture-docs' dir
    # may not be separately tracked as created. What matters: both dirs exist.
    assert result.deployed is True
    assert result.categories_already_set == ()

    # Dirs and seed READMEs exist on disk.
    assert (proj / "docs" / "architecture").is_dir()
    assert (proj / "docs" / "architecture" / "decisions").is_dir()
    assert (proj / "docs" / "architecture" / "decisions" / "README.md").is_file()

    # Overlay updated with both categories uncommented.
    text = overlay.read_text()
    assert re.search(r"(?m)^architecture-docs:", text)
    assert "docs/architecture" in text
    assert re.search(r"(?m)^adr-records:", text)
    assert "docs/architecture/decisions" in text
    # Not commented.
    assert "# architecture-docs:" not in text
    assert "# adr-records:" not in text

    # Agent is now deployable.
    assert ao.missing_categories(proj) == []


def test_adopt_idempotent(tmp_path):
    """Re-running adopt on an already-adopted agent → no overlay changes, no error."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    ao.adopt_agent(proj, "a", deploy_fn=_deploy_ok)
    text_after_first = overlay.read_text()

    result2 = ao.adopt_agent(proj, "a", deploy_fn=_deploy_ok)
    assert result2.categories_wired == ()
    assert result2.dirs_created == ()
    assert result2.deployed is True
    assert overlay.read_text() == text_after_first  # overlay unchanged


def test_adopt_does_not_overwrite_adopter_set_value(tmp_path):
    """Adopter-set overlay value is never clobbered by adopt."""
    overlay_text = (
        "workflow-docs:\n  - README.md\n"
        "architecture-docs:\n  - docs/custom-arch/\n"
    )
    proj = _project(tmp_path, overlay=overlay_text)
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    overlay = proj / ".pkit" / "agents" / "project" / "overlay.yaml"

    result = ao.adopt_agent(proj, "a", deploy_fn=_deploy_ok)

    # Category was already defined — no change.
    assert result.categories_wired == ()
    assert result.dirs_created == ()
    assert "architecture-docs" in result.categories_already_set
    assert overlay.read_text() == overlay_text  # custom path survives


def test_adopt_unknown_agent_raises(tmp_path):
    """Requesting adopt for an unknown agent → clear ClickException."""
    import click
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    with pytest.raises(click.ClickException, match="unknown agent"):
        ao.adopt_agent(proj, "does-not-exist", deploy_fn=_deploy_ok)


def test_adopt_agent_no_categories_raises(tmp_path):
    """Agent that references no overlay categories → clear ClickException."""
    import click
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    # Agent with no placeholder owns/reads.
    _agent(proj / ".pkit" / "agents" / "core", "plain", body="nothing special")
    with pytest.raises(click.ClickException, match="references no overlay categories"):
        ao.adopt_agent(proj, "plain", deploy_fn=_deploy_ok)


def test_adopt_dir_exists_no_duplicate_creation(tmp_path):
    """If the conventional dir already exists, adopt wires the overlay without
    re-creating the dir or writing a second seed README."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    # Pre-create the dir.
    arch_dir = proj / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    (arch_dir / "existing.md").write_text("# pre-existing file", encoding="utf-8")

    result = ao.adopt_agent(proj, "a", deploy_fn=_deploy_ok)

    # Dir was already present — not listed as created.
    assert result.dirs_created == ()
    # Category still wired (overlay updated).
    assert "architecture-docs" in result.categories_wired
    # Pre-existing file untouched; no spurious README.md created.
    assert (arch_dir / "existing.md").read_text("utf-8") == "# pre-existing file"
    # deploy ran.
    assert result.deployed is True


def test_adopt_cli_fresh(tmp_path, monkeypatch):
    """CLI: `pkit agents adopt <agent>` outputs dirs-created + wired categories."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    monkeypatch.chdir(proj)

    # Patch adopt_agent to avoid real disk + deploy side-effects.
    import project_kit.cli as cli_mod
    import project_kit.agents_overlay as ao_mod

    called: list[str] = []

    def fake_adopt(target_root: Path, agent_name: str, **kwargs: object) -> ao_mod.AdoptResult:
        called.append(agent_name)
        return ao_mod.AdoptResult(
            agent=agent_name,
            dirs_created=("docs/architecture",),
            categories_wired=("architecture-docs",),
            categories_already_set=(),
            deployed=True,
        )

    monkeypatch.setattr(ao_mod, "adopt_agent", fake_adopt)

    result = CliRunner().invoke(main, ["agents", "adopt", "a"])
    assert result.exit_code == 0, result.output
    assert "docs/architecture" in result.output
    assert "architecture-docs" in result.output
    assert "deployed" in result.output
    assert called == ["a"]


def test_adopt_cli_unknown_agent(tmp_path, monkeypatch):
    """CLI: unknown agent → non-zero exit with error message."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(main, ["agents", "adopt", "no-such-agent"])
    assert result.exit_code != 0
    assert "unknown agent" in result.output


def test_adopt_guidance_in_reconcile_output(tmp_path):
    """reconcile's dir-absent stub output mentions `pkit agents adopt <agent>`."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    # Do NOT create docs/architecture — so reconcile stubs it.
    _added, report = ao.reconcile_overlay(proj, write=True)
    assert "pkit agents adopt" in report


def test_adopt_guidance_in_reconcile_commented_stub_output(tmp_path):
    """reconcile's commented-stub output also mentions `pkit agents adopt <agent>`."""
    overlay_text = (
        "workflow-docs:\n  - README.md\n"
        "# architecture-docs:\n"
        "#   - <path/relative/to/project/root>\n"
    )
    proj = _project(tmp_path, overlay=overlay_text)
    _agent(proj / ".pkit" / "agents" / "core", "a", owns=["<architecture-docs>"])
    _added, report = ao.reconcile_overlay(proj, write=True)
    assert "pkit agents adopt" in report


def test_adopt_guidance_in_render_status(tmp_path, monkeypatch):
    """render_status warn message mentions `pkit agents adopt`."""
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "needs-arch", owns=["<architecture-docs>"])
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(main, ["agents"])
    assert result.exit_code == 0, result.output
    assert "pkit agents adopt" in result.output
