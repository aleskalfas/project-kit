"""Integration tests for `.pkit/adapters/claude-code/deploy-agents.sh`.

The script and its Python helper are exercised against synthesised
kit layouts in tmp directories. No mocking — uv installs the script's
declared dependencies (ruamel.yaml) on first invocation via PEP 723
inline metadata, exactly as it does for adopters.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


SOURCE_REPO = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = SOURCE_REPO / ".pkit" / "adapters" / "claude-code" / "deploy-agents.sh"
RESOLVE_SCRIPT = SOURCE_REPO / ".pkit" / "adapters" / "claude-code" / "_resolve_agent.py"
OWNERSHIP_MODULE = SOURCE_REPO / ".pkit" / "lifecycle" / "ownership.py"

# The one write-carrying overlay category shipped today (ADR-051). Read from the
# real module rather than restated, so a rename can't leave these tests
# exercising a category nothing guards.
WRITE_CARRYING_CATEGORY = "process-authoring-targets"


@pytest.fixture
def mock_kit(tmp_path: Path) -> Path:
    """Stage a minimal kit layout under tmp_path with the adapter scripts copied in.

    Includes the propagated `.pkit/lifecycle/ownership.py` the resolver imports
    for its write-authority check (ADR-051) — a synced adopter tree always has
    it, so staging it is what makes this fixture a faithful stand-in.

    Returns the project root (the directory containing `.pkit/`).
    """
    adapter_dir = tmp_path / ".pkit" / "adapters" / "claude-code"
    adapter_dir.mkdir(parents=True)
    shutil.copy2(DEPLOY_SCRIPT, adapter_dir / "deploy-agents.sh")
    shutil.copy2(RESOLVE_SCRIPT, adapter_dir / "_resolve_agent.py")
    (adapter_dir / "deploy-agents.sh").chmod(0o755)
    (adapter_dir / "_resolve_agent.py").chmod(0o755)

    lifecycle_dir = tmp_path / ".pkit" / "lifecycle"
    lifecycle_dir.mkdir(parents=True)
    shutil.copy2(OWNERSHIP_MODULE, lifecycle_dir / "ownership.py")

    (tmp_path / ".pkit" / "agents" / "core").mkdir(parents=True)
    (tmp_path / ".pkit" / "agents" / "project").mkdir(parents=True)

    return tmp_path


def _write_agent(root: Path, namespace: str, name: str, content: str) -> None:
    agent_dir = root / ".pkit" / "agents" / namespace / name
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / f"{name}.md").write_text(content, encoding="utf-8")


def _run_deploy(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(root / ".pkit" / "adapters" / "claude-code" / "deploy-agents.sh")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_deploy_no_agents_succeeds(mock_kit: Path) -> None:
    """With zero kit agents, deploy reports 'Done.' and exits 0."""
    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "Done." in result.stdout
    # `.claude/agents/` is created (empty) by the script.
    assert (mock_kit / ".claude" / "agents").is_dir()


def test_deploy_agent_without_placeholders(mock_kit: Path) -> None:
    """An agent with no overlay placeholders deploys cleanly without an overlay."""
    _write_agent(
        mock_kit,
        "core",
        "simple-agent",
        "---\nname: simple-agent\ndescription: Test.\n---\n\n# Simple\n",
    )

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    deployed = mock_kit / ".claude" / "agents" / "simple-agent.md"
    assert deployed.is_file()
    content = deployed.read_text()
    assert "name: simple-agent" in content
    assert "# Simple" in content


def test_deploy_resolves_overlay_default_categories(mock_kit: Path) -> None:
    """Placeholders resolve against the overlay's top-level (default) categories."""
    _write_agent(
        mock_kit,
        "core",
        "test-agent",
        "---\nname: test-agent\ndescription: Test.\nowns:\n  - <code-paths>\n---\n\n# Test\n",
    )
    (mock_kit / ".pkit" / "agents" / "project" / "overlay.yaml").write_text(
        "code-paths:\n  - src/foo/\n  - lib/foo/\n", encoding="utf-8"
    )

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    content = (mock_kit / ".claude" / "agents" / "test-agent.md").read_text()
    assert "- src/foo/" in content
    assert "- lib/foo/" in content
    assert "<code-paths>" not in content


def test_deploy_per_agent_override_replaces_default(mock_kit: Path) -> None:
    """`overrides.<agent>.<category>` fully replaces the default category."""
    _write_agent(
        mock_kit,
        "core",
        "qa-engineer",
        "---\nname: qa-engineer\ndescription: Test.\nowns:\n  - <code-paths>\n---\n\n# QA\n",
    )
    (mock_kit / ".pkit" / "agents" / "project" / "overlay.yaml").write_text(
        "code-paths:\n  - src/\noverrides:\n  qa-engineer:\n    code-paths:\n      - tests/\n",
        encoding="utf-8",
    )

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    content = (mock_kit / ".claude" / "agents" / "qa-engineer.md").read_text()
    assert "- tests/" in content
    assert "- src/" not in content  # the override replaces the default


def test_deploy_project_wins_over_core_collision(mock_kit: Path) -> None:
    """When the same agent name exists in core and project, project wins."""
    _write_agent(
        mock_kit,
        "core",
        "shared",
        "---\nname: shared\ndescription: From core.\n---\n\n# Core version\n",
    )
    _write_agent(
        mock_kit,
        "project",
        "shared",
        "---\nname: shared\ndescription: From project.\n---\n\n# Project version\n",
    )

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    content = (mock_kit / ".claude" / "agents" / "shared.md").read_text()
    assert "From project" in content
    assert "# Project version" in content


def test_deploy_unresolved_category_degrades_not_aborts(mock_kit: Path) -> None:
    """An overlay category an agent references but the overlay doesn't define is
    an adopter-config gap, NOT a fatal error (#287). The agent is skipped loudly
    with remediation, the rest deploy, and the run exits 0 — so one stale overlay
    can't abort an unrelated `pkit upgrade`/`sync`."""
    _write_agent(
        mock_kit,
        "core",
        "broken",
        "---\nname: broken\nowns:\n  - <undefined-category>\n---\n\n# Broken\n",
    )
    # A second, resolvable agent must still deploy despite the broken one.
    _write_agent(
        mock_kit,
        "core",
        "fine",
        "---\nname: fine\ndescription: Test.\n---\n\n# Fine\n",
    )

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr            # degrade, not abort
    assert "skipped" in result.stdout and "broken" in result.stdout
    assert "<undefined-category>" in result.stdout          # the missing category named
    assert "overlay.yaml" in result.stdout                  # remediation pointer
    assert "pkit agents adopt" in result.stdout             # lead command: adopt
    assert "pkit agents reconcile --write" in result.stdout  # custom-layout fallback named
    assert "1 agent(s) skipped" in result.stdout            # end-of-run summary
    assert (mock_kit / ".claude" / "agents" / "fine.md").is_file()      # rest deployed
    assert not (mock_kit / ".claude" / "agents" / "broken.md").exists()  # the gap one skipped


# --- write-carrying categories (ADR-051) -------------------------------------
#
# `process-authoring-targets` grants the core `process-author` agent write
# authority over paths only the adopter can enumerate. Three properties are
# exercised here: the explicit-`[]` form deploys the agent inert, a bare/absent
# key skips it with remediation that does NOT promise `adopt`, and an entry
# resolving into sync-managed content is refused outright.

def _write_carrying_agent(root: Path, name: str = "process-author") -> None:
    _write_agent(
        root,
        "core",
        name,
        f"---\nname: {name}\ndescription: Test.\n"
        f"owns:\n  - <{WRITE_CARRYING_CATEGORY}>\n---\n\n# Teeth\n",
    )


def _overlay(root: Path, body: str) -> None:
    (root / ".pkit" / "agents" / "project" / "overlay.yaml").write_text(body, encoding="utf-8")


def _register_capability(root: Path, name: str, *, origin: str | None) -> None:
    """Register *name* in the backbone manifest, optionally with an origin."""
    lines = [
        "schema_version: 1",
        "backbone_version: 1.0.0",
        "components:",
        "  - kind: capability",
        f"    name: {name}",
        f"    manifest: .pkit/capabilities/{name}/manifest.yaml",
    ]
    if origin is not None:
        lines.append(f"    origin: {origin}")
    (root / ".pkit" / "manifest.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_deploy_write_carrying_explicit_empty_list_deploys_inert(mock_kit: Path) -> None:
    """The shipped form: `cat: []` resolves to an empty `owns:` and the agent deploys."""
    _write_carrying_agent(mock_kit)
    _overlay(mock_kit, f"{WRITE_CARRYING_CATEGORY}: []\n")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    assert "skipped" not in result.stdout
    deployed = mock_kit / ".claude" / "agents" / "process-author.md"
    assert deployed.is_file()
    content = deployed.read_text()
    assert "owns: []" in content                          # inert: owns nothing
    assert f"<{WRITE_CARRYING_CATEGORY}>" not in content  # placeholder resolved


def test_deploy_write_carrying_bare_key_skips_with_honest_remediation(mock_kit: Path) -> None:
    """A bare key (`cat:` with no value) does not resolve → the agent is skipped.

    The remediation must not advertise `pkit agents adopt`: there is no
    conventional default for paths core cannot enumerate, so adopt would refuse.
    """
    _write_carrying_agent(mock_kit)
    _overlay(mock_kit, f"{WRITE_CARRYING_CATEGORY}:\n")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "skipped" in result.stdout and "process-author" in result.stdout
    assert f"<{WRITE_CARRYING_CATEGORY}>" in result.stdout      # the category named
    assert "cannot serve" in result.stdout                     # adopt ruled out …
    assert "pkit agents reconcile --write" in result.stdout     # … the real path named
    assert "Deploy it:  pkit agents adopt" not in result.stdout  # generic advice suppressed
    assert not (mock_kit / ".claude" / "agents" / "process-author.md").exists()


def test_deploy_write_carrying_absent_key_skips(mock_kit: Path) -> None:
    """An absent key skips exactly as a bare one does — no overlay file at all."""
    _write_carrying_agent(mock_kit)

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "skipped" in result.stdout and "process-author" in result.stdout
    assert not (mock_kit / ".claude" / "agents" / "process-author.md").exists()


def test_deploy_write_carrying_rejects_sync_managed_path(mock_kit: Path) -> None:
    """A core area is sync-managed, so the category may not name it (ADR-051)."""
    _write_carrying_agent(mock_kit)
    _overlay(mock_kit, f"{WRITE_CARRYING_CATEGORY}:\n  - .pkit/agents/core/\n")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr          # degrade, not abort
    assert "skipped" in result.stdout
    assert "sync-managed" in result.stdout                # the reason
    assert ".pkit/agents/core/" in result.stdout          # the offending path, named
    assert "overlay.yaml" in result.stdout                # where to fix it
    assert not (mock_kit / ".claude" / "agents" / "process-author.md").exists()


def test_deploy_write_carrying_rejects_kit_shipped_capability_subtree(mock_kit: Path) -> None:
    """A registered kit-shipped capability's own subtree is sync-managed."""
    _write_carrying_agent(mock_kit)
    _register_capability(mock_kit, "shipped-cap", origin="kit-shipped")
    _overlay(
        mock_kit,
        f"{WRITE_CARRYING_CATEGORY}:\n  - .pkit/capabilities/shipped-cap/schemas/flow.yaml\n",
    )

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "skipped" in result.stdout and "sync-managed" in result.stdout
    assert ".pkit/capabilities/shipped-cap/schemas/flow.yaml" in result.stdout


def test_deploy_write_carrying_accepts_project_tree_in_kit_shipped_capability(
    mock_kit: Path,
) -> None:
    """`project/` inside a kit-shipped capability is adopter-owned by tier (ADR-051)."""
    _write_carrying_agent(mock_kit)
    _register_capability(mock_kit, "shipped-cap", origin="kit-shipped")
    target = ".pkit/capabilities/shipped-cap/project/process/predicates/"
    _overlay(mock_kit, f"{WRITE_CARRYING_CATEGORY}:\n  - {target}\n")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    assert "skipped" not in result.stdout
    content = (mock_kit / ".claude" / "agents" / "process-author.md").read_text()
    assert target in content


def test_deploy_write_carrying_accepts_unregistered_capability_subtree(mock_kit: Path) -> None:
    """The bootstrap window: a subtree authored but not yet registered is admissible."""
    _write_carrying_agent(mock_kit)
    _register_capability(mock_kit, "some-other-cap", origin="kit-shipped")
    target = ".pkit/capabilities/fresh-cap/schemas/renovation.yaml"
    _overlay(mock_kit, f"{WRITE_CARRYING_CATEGORY}:\n  - {target}\n")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    assert "skipped" not in result.stdout
    assert target in (mock_kit / ".claude" / "agents" / "process-author.md").read_text()


def test_deploy_write_carrying_accepts_incubated_capability_subtree(mock_kit: Path) -> None:
    """An incubated capability is adopter-owned (COR-031 D1) — admissible."""
    _write_carrying_agent(mock_kit)
    _register_capability(mock_kit, "mine", origin="incubated-in-repo")
    target = ".pkit/capabilities/mine/schemas/renovation.yaml"
    _overlay(mock_kit, f"{WRITE_CARRYING_CATEGORY}:\n  - {target}\n")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    assert target in (mock_kit / ".claude" / "agents" / "process-author.md").read_text()


def test_deploy_read_carrying_category_may_name_sync_managed_paths(mock_kit: Path) -> None:
    """The constraint guards *write* authority only.

    `architecture-docs` legitimately points at kit-shipped records (project-kit's
    own overlay does exactly that), so a non-write-carrying category must not be
    checked — otherwise shipping the constraint would break existing installs.
    """
    _write_agent(
        mock_kit,
        "core",
        "architect",
        "---\nname: architect\ndescription: Test.\nowns:\n  - <architecture-docs>\n---\n\n# Arch\n",
    )
    _overlay(mock_kit, "architecture-docs:\n  - .pkit/decisions/core/\n")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    assert ".pkit/decisions/core/" in (mock_kit / ".claude" / "agents" / "architect.md").read_text()


def test_deploy_missing_ownership_module_fails_loudly(mock_kit: Path) -> None:
    """Without the shared predicate the check cannot run — skip loudly, never silently.

    Deploying an agent whose write grant was never validated is the outcome
    ADR-051 exists to prevent, so an absent `.pkit/lifecycle/ownership.py` skips
    every placeholder-bearing agent with a `pkit sync` pointer.
    """
    (mock_kit / ".pkit" / "lifecycle" / "ownership.py").unlink()
    _write_carrying_agent(mock_kit)
    _overlay(mock_kit, f"{WRITE_CARRYING_CATEGORY}: []\n")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr      # still degrades, not aborts
    assert "skipped" in result.stdout
    assert "ownership.py" in result.stdout
    assert "pkit sync" in result.stdout
    assert not (mock_kit / ".claude" / "agents" / "process-author.md").exists()


def test_deploy_idempotent_reports_exists(mock_kit: Path) -> None:
    """Re-running deploy on already-deployed content reports 'exists', not 'updated'."""
    _write_agent(
        mock_kit,
        "core",
        "stable",
        "---\nname: stable\ndescription: Test.\n---\n\n# Stable\n",
    )
    first = _run_deploy(mock_kit)
    assert first.returncode == 0
    assert "created" in first.stdout

    second = _run_deploy(mock_kit)
    assert second.returncode == 0
    assert "exists" in second.stdout
    assert "created" not in second.stdout
    assert "updated" not in second.stdout


def test_deploy_emits_kit_marker_in_resolved_file(mock_kit: Path) -> None:
    """Every kit-deployed agent file carries the `managed-by` marker in frontmatter."""
    _write_agent(
        mock_kit,
        "core",
        "marked",
        "---\nname: marked\ndescription: Test.\n---\n\n# Marked\n",
    )
    _run_deploy(mock_kit)
    deployed = (mock_kit / ".claude" / "agents" / "marked.md").read_text()
    # Marker is on line 2 (line 1 is `---`).
    assert "managed-by: project-kit" in deployed
    second_line = deployed.splitlines()[1]
    assert "managed-by: project-kit" in second_line


def test_deploy_skips_existing_user_content_without_marker(mock_kit: Path) -> None:
    """An adopter-authored agent at the same name is NOT overwritten — `skipped` status, kit's version is dropped.

    Regression for the silent-overwrite bug discovered in
    example-brownfield: kit's `product-manager.md` deployed over the
    adopter's pre-existing `product-manager.md`, destroying their work.
    Kit-deployed files now carry a marker; deploy refuses to overwrite
    a file that lacks the marker.
    """
    _write_agent(
        mock_kit,
        "core",
        "product-manager",
        "---\nname: product-manager\ndescription: Kit version.\n---\n\n# Kit version\n",
    )
    user_content = (
        "---\nname: product-manager\ndescription: My CA-specific PM.\n---\n\n# Adopter version\n"
    )
    user_file = mock_kit / ".claude" / "agents" / "product-manager.md"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text(user_content, encoding="utf-8")

    result = _run_deploy(mock_kit)
    assert result.returncode == 0
    assert "skipped" in result.stdout
    assert "no kit marker" in result.stdout
    # File is untouched.
    assert user_file.read_text() == user_content


def test_deploy_updates_its_own_marked_files(mock_kit: Path) -> None:
    """A previously-deployed (marked) file gets refreshed on the next deploy when source changes."""
    _write_agent(
        mock_kit,
        "core",
        "stable",
        "---\nname: stable\ndescription: First.\n---\n\n# First\n",
    )
    _run_deploy(mock_kit)

    # Update the source so the resolved content changes.
    (mock_kit / ".pkit" / "agents" / "core" / "stable" / "stable.md").write_text(
        "---\nname: stable\ndescription: Second.\n---\n\n# Second\n",
        encoding="utf-8",
    )

    result = _run_deploy(mock_kit)
    assert result.returncode == 0
    assert "updated" in result.stdout
    assert "skipped" not in result.stdout
    content = (mock_kit / ".claude" / "agents" / "stable.md").read_text()
    assert "Second" in content


def test_deploy_picks_up_agents_from_installed_capabilities(mock_kit: Path) -> None:
    """An agent shipped by an installed capability gets deployed alongside core agents (per COR-017)."""
    # No core agent — just an agent inside an installed capability.
    cap_agents_dir = mock_kit / ".pkit" / "capabilities" / "evidence" / "agents"
    cap_agents_dir.mkdir(parents=True)
    (cap_agents_dir / "evidence-reviewer.md").write_text(
        "---\nname: evidence-reviewer\ndescription: From the evidence capability.\n---\n\n# Reviewer\n",
        encoding="utf-8",
    )

    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    deployed = mock_kit / ".claude" / "agents" / "evidence-reviewer.md"
    assert deployed.is_file()
    assert "evidence-reviewer" in deployed.read_text()


# --- stale-removal pass ------------------------------------------------------

# The frontmatter marker deploy-agents.sh stamps into its own deployed copies.
# Kept in sync with deploy-agents.sh's MARKER (a drift would fail these tests
# loudly, which is the intent).
_MARKER = "# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync"


def _predeploy(root: Path, name: str, *, marked: bool) -> Path:
    """Place a file directly in .claude/agents/ as if a prior deploy left it."""
    dest_dir = root / ".claude" / "agents"
    dest_dir.mkdir(parents=True, exist_ok=True)
    fm = ["---"]
    if marked:
        fm.append(_MARKER)
    fm += [f"name: {name}", "---", "body"]
    dest = dest_dir / f"{name}.md"
    dest.write_text("\n".join(fm) + "\n", encoding="utf-8")
    return dest


def test_stale_marked_agent_is_pruned(mock_kit: Path) -> None:
    """A deployed agent carrying the marker whose source no longer ships is removed."""
    orphan = _predeploy(mock_kit, "orphan", marked=True)
    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert not orphan.exists()
    assert "removed" in result.stdout and "orphan.md" in result.stdout


def test_unmarked_agent_is_preserved(mock_kit: Path) -> None:
    """An adopter-authored agent (no marker) is never pruned, even if unshipped."""
    mine = _predeploy(mock_kit, "myown", marked=False)
    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert mine.exists()  # untouched — not ours to remove


def test_shipped_agent_survives_prune(mock_kit: Path) -> None:
    """A still-shipped agent deploys and is not swept by the prune pass."""
    _write_agent(
        mock_kit, "core", "keeper",
        "---\nname: keeper\ndescription: t\n---\n# keeper\n",
    )
    _predeploy(mock_kit, "orphan", marked=True)  # also stale, to mix
    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert (mock_kit / ".claude" / "agents" / "keeper.md").exists()
    assert not (mock_kit / ".claude" / "agents" / "orphan.md").exists()
