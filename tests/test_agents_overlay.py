"""Tests for the `pkit agents` diagnostic + reconcile (per COR-013).

Includes a guard that the backbone reference-detection key-set stays in sync
with the claude-code adapter's `_resolve_agent.py` — the (B) factoring's
anti-drift net.
"""
from __future__ import annotations

import re
from pathlib import Path

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

    # Idempotent: a second run adds nothing (the commented key is detected).
    added2, _ = ao.reconcile_overlay(proj, write=True)
    assert added2 == []
    assert overlay.read_text() == text


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


def test_cli_agents_never_load_bearing(tmp_path, monkeypatch):
    from project_kit import cli_render
    proj = _project(tmp_path, overlay="workflow-docs:\n  - README.md\n")
    _agent(proj / ".pkit" / "agents" / "core", "needs-arch", owns=["<architecture-docs>"])
    monkeypatch.chdir(proj)
    always = CliRunner().invoke(main, ["--color", "always", "agents"]).output
    never = CliRunner().invoke(main, ["--color", "never", "agents"]).output
    assert "\033[" in always
    assert cli_render.strip_ansi(always) == never
