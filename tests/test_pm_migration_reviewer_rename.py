"""The 0.55.0 migration renames the default local reviewer `reviewer` →
`pm-reviewer` (#770), keyed on provenance so an adopter's OWN agent named
`reviewer` is never touched.

The config string `- name: reviewer` is byte-identical whether it registers the
kit-shipped default or an adopter-authored agent that happens to share the name.
Keying the rewrite on that string would corrupt a custom registration. The
migration instead keys on the DEPLOYED agent's provenance — deploy-agents.sh
stamps its copies with a `managed-by: project-kit` marker; an adopter file has
none. These tests pin the disconfirming cases: a marker-carrying default is
rewritten; a marker-less custom agent is left entirely alone; already-migrated
and no-review-block states are clean no-ops.

They also pin the end state the rename exists to reach: the shipped canonical
agent is `pm-reviewer.md` naming `pm-reviewer`, the project registers
`pm-reviewer`, and the deployed-agent resolver finds `pm-reviewer` (and not
`reviewer`) — so `review-pr` / the gate resolve the renamed agent.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
MIGRATION = CAPABILITY / "migrations" / "0.55.0" / "001-pm-reviewer-agent-rename.sh"
AGENTS_MODULE = CAPABILITY / "scripts" / "_lib" / "agents.py"

MARKER = "# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync"

CONFIG_DEFAULT = (
    "schema_version: 1\n"
    "review:\n"
    "  mode: agent\n"
    "  agents:\n"
    "    local_registered:\n"
    "      - name: reviewer\n"
)
CONFIG_MIGRATED = CONFIG_DEFAULT.replace("- name: reviewer", "- name: pm-reviewer")
CONFIG_NO_REVIEW = "schema_version: 1\ndefault_branch: main\n"


@pytest.fixture(scope="module")
def agents_mod():
    """Load the deployed-agent resolver the gate/review-pr use."""
    sys.path.insert(0, str(CAPABILITY / "scripts"))
    spec = importlib.util.spec_from_file_location("pm_agents_for_migration_test", AGENTS_MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(CAPABILITY / "scripts"))


def _install(
    root: Path,
    *,
    config: str | None = CONFIG_DEFAULT,
    deployed: str | None = None,  # "kit-copy" | "adopter-copy" | "kit-symlink" | None
) -> Path:
    """Lay down an installed-adopter shape for the migration to act on."""
    cap = root / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True)
    (cap / "agents").mkdir(parents=True)
    claude_agents = root / ".claude" / "agents"
    claude_agents.mkdir(parents=True)

    if config is not None:
        (cap / "project" / "config.yaml").write_text(config, encoding="utf-8")

    deployed_reviewer = claude_agents / "reviewer.md"
    if deployed == "kit-copy":
        deployed_reviewer.write_text(
            f"---\n{MARKER}\nname: reviewer\n---\nbody\n", encoding="utf-8"
        )
    elif deployed == "adopter-copy":
        deployed_reviewer.write_text("---\nname: reviewer\n---\nmy own agent\n", encoding="utf-8")
    elif deployed == "kit-symlink":
        deployed_reviewer.symlink_to(cap / "agents" / "reviewer.md")
    return cap


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        capture_output=True,
        text=True,
        check=False,
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def _registered_names(cap: Path) -> list[str]:
    doc = YAML(typ="safe").load((cap / "project" / "config.yaml").read_text(encoding="utf-8"))
    return [e["name"] for e in doc["review"]["agents"]["local_registered"]]


# --- The rename itself: shipped default is rewritten -------------------------


def test_default_kit_copy_is_rewritten_and_stale_copy_removed(tmp_path) -> None:
    """Pre-sync ordering: a marker-carrying deployed reviewer.md is the kit
    default, so its config entry is rewritten and the stale copy removed."""
    cap = _install(tmp_path, deployed="kit-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["pm-reviewer"]
    assert not (tmp_path / ".claude" / "agents" / "reviewer.md").exists()


def test_post_sync_default_with_deployed_already_removed_is_rewritten(tmp_path) -> None:
    """Sync-has-run ordering: deploy-agents.sh already stale-removed the old
    copy, so only the config entry remains to rewrite."""
    cap = _install(tmp_path, deployed=None)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["pm-reviewer"]


def test_kit_symlink_default_is_rewritten_and_removed(tmp_path) -> None:
    """Older installs may carry a symlink into pm's canonical tree rather than a
    marker copy; it is still the kit default."""
    cap = _install(tmp_path, deployed="kit-symlink")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["pm-reviewer"]
    assert not (tmp_path / ".claude" / "agents" / "reviewer.md").exists()


# --- The disconfirming case: adopter's OWN `reviewer` is untouched -----------


def test_adopter_custom_reviewer_is_not_rewritten(tmp_path) -> None:
    """A marker-less deployed reviewer.md is adopter content — the config entry
    points at THEIR agent, not the kit default, so nothing is rewritten and the
    file is preserved."""
    cap = _install(tmp_path, deployed="adopter-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["reviewer"]
    assert (tmp_path / ".claude" / "agents" / "reviewer.md").exists()


# --- Clean no-ops ------------------------------------------------------------


def test_already_migrated_is_a_no_op(tmp_path) -> None:
    cap = _install(tmp_path, config=CONFIG_MIGRATED, deployed=None)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["pm-reviewer"]


def test_no_review_block_is_a_no_op(tmp_path) -> None:
    cap = _install(tmp_path, config=CONFIG_NO_REVIEW, deployed=None)
    before = (cap / "project" / "config.yaml").read_text(encoding="utf-8")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert (cap / "project" / "config.yaml").read_text(encoding="utf-8") == before


def test_re_running_is_idempotent(tmp_path) -> None:
    cap = _install(tmp_path, deployed="kit-copy")
    _run(tmp_path)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["pm-reviewer"]


def test_absent_capability_is_a_clean_skip(tmp_path) -> None:
    proc = _run(tmp_path)
    assert proc.returncode == 0
    assert "not installed" in proc.stdout


# --- The rename resolves: agent file + config + resolver all agree -----------


def test_shipped_agent_is_pm_reviewer(agents_mod) -> None:
    """The canonical kit agent is now pm-reviewer.md naming pm-reviewer, and the
    old reviewer.md no longer ships."""
    agents_dir = CAPABILITY / "agents"
    assert (agents_dir / "pm-reviewer.md").is_file()
    assert not (agents_dir / "reviewer.md").exists()
    head = (agents_dir / "pm-reviewer.md").read_text(encoding="utf-8")
    assert "name: pm-reviewer" in head


def test_project_registers_pm_reviewer(agents_mod) -> None:
    """project-kit dogfoods the rename — its own config registers pm-reviewer."""
    doc = YAML(typ="safe").load(
        (CAPABILITY / "project" / "config.yaml").read_text(encoding="utf-8")
    )
    assert _registered_names(CAPABILITY) == ["pm-reviewer"]
    assert doc["review"]["agents"]["local_registered"][0]["name"] == "pm-reviewer"


def test_resolver_finds_pm_reviewer_after_deploy(agents_mod, tmp_path) -> None:
    """The deployed-agent resolver (used by pre-check / the gate / review-pr)
    resolves pm-reviewer and not reviewer once the migrated state is deployed."""
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "pm-reviewer.md").write_text("x", encoding="utf-8")
    assert agents_mod.agent_is_deployed(tmp_path, "pm-reviewer")
    assert not agents_mod.agent_is_deployed(tmp_path, "reviewer")
