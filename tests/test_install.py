"""Tests for `pkit init` (the Python port of the bash dispatcher's `cmd_init`).

The tests use pytest's `tmp_path` fixture to install into a fresh
directory each time, then assert the expected tree shape per the
bash dispatcher's behaviour. Adapter primitives (`merge-settings.sh`,
`deploy-skills.sh`) are stubbed via the `stub_adapter_primitives`
fixture (declared with `usefixtures`) for tests that care about pure
file layout — they're invoked separately and need a real
`.claude/settings.json` baseline to be meaningful.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest

from project_kit import install


@pytest.fixture
def tmp_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create an empty git repo at `tmp_path` so `find_target_root` resolves it."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def stub_adapter_primitives(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the adapter shell scripts during install tests.

    `_run_adapter_primitive` is the seam where the bash primitives are
    invoked. Tests assert tree shape; primitives are out of scope.
    """

    def _noop(_script: Path, _ctx: install.InstallContext) -> None:
        return None

    monkeypatch.setattr(install, "_run_adapter_primitive", _noop)


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_writes_expected_top_level_layout(tmp_target: Path) -> None:
    install.install_kit(tmp_target)

    pkit_dir = tmp_target / ".pkit"
    assert pkit_dir.is_dir()

    for area in install.PROPAGATED_AREAS:
        assert (pkit_dir / area).is_dir(), f"area '{area}' not installed"

    # Schemas area is part of PROPAGATED_AREAS — its `_defs/refs.schema.json`
    # carries shared $defs (source block, reference_token) that every
    # capability-shipped schema cross-references. Without this area
    # propagating, every installed capability with schemas would fail
    # validation in the adopter.
    assert (pkit_dir / "schemas" / "_defs" / "refs.schema.json").is_file()


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_copies_decisions_core(tmp_target: Path) -> None:
    install.install_kit(tmp_target)
    cor_files = list((tmp_target / ".pkit" / "decisions" / "core").glob("COR-*.md"))
    assert cor_files, "no COR-*.md records were copied into decisions/core/"


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_stubs_empty_project_directories(tmp_target: Path) -> None:
    install.install_kit(tmp_target)
    project_dir = tmp_target / ".pkit" / "decisions" / "project"
    assert project_dir.is_dir()
    assert (project_dir / ".gitkeep").is_file()


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_stubs_scratchpad_state_folders(tmp_target: Path) -> None:
    """Per COR-012, scratchpad state folders are adopter-owned. Init must
    create them empty (with .gitkeep) so the layout is there; the source
    kit's own scratchpad content must not propagate."""
    install.install_kit(tmp_target)
    scratchpad = tmp_target / ".pkit" / "scratchpad"
    for state_dir in ("active", "done", "dropped"):
        assert (scratchpad / state_dir).is_dir(), f"state folder '{state_dir}' not stubbed"
        assert (scratchpad / state_dir / ".gitkeep").is_file(), (
            f"state folder '{state_dir}' missing .gitkeep"
        )


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_does_not_propagate_scratchpad_notes(tmp_target: Path) -> None:
    """Source kit may have its own scratchpad notes (project-kit self-
    hosts). Those are adopter-owned content from sync's perspective and
    must not appear in a fresh adopter install."""
    install.install_kit(tmp_target)
    done_dir = tmp_target / ".pkit" / "scratchpad" / "done"
    notes = [p for p in done_dir.iterdir() if p.name != ".gitkeep"]
    assert not notes, f"unexpected scratchpad notes propagated: {[p.name for p in notes]}"


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_copies_scratchpad_readme(tmp_target: Path) -> None:
    """The area README is kit-owned per COR-012 and propagates on init."""
    install.install_kit(tmp_target)
    readme = tmp_target / ".pkit" / "scratchpad" / "README.md"
    assert readme.is_file(), "scratchpad README not propagated"


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_creates_agents_area_with_readme_and_subdirs(tmp_target: Path) -> None:
    """Per COR-013, the agents area is universal-variant. Init creates the
    README (core-shipped) + core/ (core-shipped) + project/ (stubbed)."""
    install.install_kit(tmp_target)
    agents = tmp_target / ".pkit" / "agents"
    assert (agents / "README.md").is_file(), "agents README not propagated"
    assert (agents / "core").is_dir(), "agents/core/ not created"
    assert (agents / "project").is_dir(), "agents/project/ not stubbed"
    assert (agents / "project" / ".gitkeep").is_file(), "agents/project/.gitkeep not stubbed"


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_copies_pkit_dispatcher_executable(tmp_target: Path) -> None:
    install.install_kit(tmp_target)
    pkit_bin = tmp_target / ".pkit" / "cli" / "pkit"
    assert pkit_bin.is_file()
    # Owner-execute bit set.
    assert pkit_bin.stat().st_mode & 0o100


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_seeds_adapter_project_settings(tmp_target: Path) -> None:
    install.install_kit(tmp_target)
    settings = (
        tmp_target / ".pkit" / "adapters" / "claude-code" / "settings" / "project" / "settings.json"
    )
    assert settings.is_file()
    content = settings.read_text(encoding="utf-8")
    assert '"permissions"' in content
    assert '"allow": []' in content


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_refuses_when_pkit_dir_already_exists(tmp_target: Path) -> None:
    (tmp_target / ".pkit").mkdir()
    with pytest.raises(click.ClickException, match=r"\.pkit/ already exists"):
        install.install_kit(tmp_target)


# Note: the bash dispatcher's `_refuse_if_target_is_source` guard is
# defensive — `.pkit/` always exists in the source repo, so the
# already-initialised guard fires first. The Python port preserves both
# guards in the same order for parity. The target-is-source case is not
# directly testable without manually circumventing the first guard.


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_kit_dry_run_writes_nothing(tmp_target: Path) -> None:
    install.install_kit(tmp_target, dry_run=True)
    # In dry-run, .pkit/ should not have been created.
    assert not (tmp_target / ".pkit").exists()


def test_find_target_root_resolves_git_repo(tmp_target: Path) -> None:
    nested = tmp_target / "deep" / "nested" / "dir"
    nested.mkdir(parents=True)
    resolved = install.find_target_root(nested)
    assert resolved is not None
    assert resolved.resolve() == tmp_target.resolve()


def test_find_target_root_returns_none_outside_a_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory with no .git/ and no .pkit/ on the way up should resolve None."""
    monkeypatch.chdir(tmp_path)
    # Force-shadow git so subprocess returns non-zero (mimics a directory
    # with no enclosing repo).
    monkeypatch.setenv("PATH", "/nonexistent")
    assert install.find_target_root(tmp_path) is None


def test_find_target_root_walk_recognises_worktree_git_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stage 2 walk: `.git` may be a file (worktree marker), not a directory.

    Mimics a worktree where git isn't on PATH (forcing Stage 2). The walk
    must recognise `.git` as a tree boundary regardless of whether it's a
    directory or a file.
    """
    worktree_root = tmp_path / "worktree"
    nested = worktree_root / "deep"
    nested.mkdir(parents=True)
    # Worktree marker: a regular file, not a directory.
    (worktree_root / ".git").write_text("gitdir: /elsewhere/.git/worktrees/foo\n", encoding="utf-8")

    # Force Stage 1 to fail by shadowing git.
    monkeypatch.setenv("PATH", "/nonexistent")
    resolved = install.find_target_root(nested)
    assert resolved is not None
    assert resolved.resolve() == worktree_root.resolve()


# ---- flat-content area propagation (#285) ------------------------------------

@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_propagates_flat_permissions_and_schemas(tmp_target: Path) -> None:
    """Non-COR-011 areas (permissions/, schemas/) keep kit-owned content as
    flat top-level files + dirs. `_install_area` must propagate them, or the
    whole permission subsystem is dead in adopters (#285: 'decision core not
    found'). Regression guard against the enumerated-subset copy that dropped
    them."""
    install.install_kit(tmp_target)
    perms = tmp_target / ".pkit" / "permissions"
    # The decision core + projector + shipped profiles must land.
    assert (perms / "decide.py").is_file()
    assert (perms / "projection.py").is_file()
    assert (perms / "profiles").is_dir()
    assert any((perms / "profiles").glob("*.yaml"))
    # The schema area's flat top-level schema files must land too.
    schemas = tmp_target / ".pkit" / "schemas"
    assert (schemas / "privilege-catalog.yaml").is_file()
    assert (schemas / "permission-profile.schema.json").is_file()
    assert (schemas / "_defs").is_dir()  # COR-011 subdir still copied


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_decision_core_loads_after_propagation(tmp_target: Path) -> None:
    """End-to-end: the propagated decision core is importable + builds a model
    in the adopter tree — i.e. `permissions explain/probe/setup` would work."""
    install.install_kit(tmp_target)
    from project_kit import permissions as perm

    catalog = perm._load_catalog(tmp_target)            # reads .pkit/schemas/privilege-catalog.yaml
    assert "privileges" in catalog and catalog["privileges"]
    model = perm._load_model(tmp_target)                # imports .pkit/permissions/decide.py
    assert "grants" in model                            # guardrail denies synthesized


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_does_not_propagate_scratchpad_state_contents(tmp_target: Path) -> None:
    """The flat-content pass must NOT sweep in adopter-owned scratchpad state
    (active/done/dropped) — project-kit's own notes must never land in adopters."""
    install.install_kit(tmp_target)
    done = tmp_target / ".pkit" / "scratchpad" / "done"
    # Stubbed empty (only .gitkeep), never populated with the source's own notes.
    notes = [p for p in done.glob("*.md")] if done.is_dir() else []
    assert notes == []


# ── rules area propagation (issue #96) ────────────────────────────────────


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_propagates_rules_area(tmp_target: Path) -> None:
    """The rules area is in PROPAGATED_AREAS and core.md lands on init."""
    assert "rules" in install.PROPAGATED_AREAS
    install.install_kit(tmp_target)
    rules = tmp_target / ".pkit" / "rules"
    assert rules.is_dir(), ".pkit/rules/ not created on install"
    assert (rules / "core.md").is_file(), ".pkit/rules/core.md not propagated"
    assert (rules / "README.md").is_file(), ".pkit/rules/README.md not propagated"


@pytest.mark.usefixtures("stub_adapter_primitives")
def test_install_does_not_propagate_rules_project_md(tmp_target: Path) -> None:
    """project.md is adopter-owned; init must never copy it into a fresh adopter tree."""
    install.install_kit(tmp_target)
    project_md = tmp_target / ".pkit" / "rules" / "project.md"
    # project.md is in the source kit (project-kit self-hosts) but must not
    # land in adopters — it's authored by each adopter for their own rules.
    assert not project_md.exists(), (
        ".pkit/rules/project.md was copied into the adopter tree; "
        "it is adopter-owned and must not propagate"
    )
