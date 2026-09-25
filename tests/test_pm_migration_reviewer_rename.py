"""The 0.55.0 migration renames the default local reviewer `reviewer` →
`pm-reviewer` (#770), keyed on provenance so an adopter's OWN agent named
`reviewer` is never touched.

The config string `- name: reviewer` is byte-identical whether it registers the
kit-shipped default or an adopter-authored agent that happens to share the name.
Keying the rewrite on that string would corrupt a custom registration. The
migration instead keys on the DEPLOYED agent's provenance — deploy-agents.sh
stamps its copies with a `managed-by: project-kit` marker in the header; an
adopter file has none there — and an adopter `reviewer` source in the project
agent namespace owns the name outright. These tests pin the disconfirming cases:
a marker-carrying default is rewritten; a marker-less (or marker-below-header)
custom agent is left entirely alone; already-migrated and no-review-block states
are clean no-ops. They also pin every `local_registered` shape (rewritten, or
reported for a manual edit, never silently skipped) and that each message the
migration prints matches what it did (#912).

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

# The config-shape variants the capability's own docs demonstrate (DEC-028 /
# the pm README register the default with a trailing inline comment) plus the
# quoting / flow forms valid YAML permits. The `$`-anchored first-cut regex
# missed every one of these, leaving a real registration pointing at the
# deleted agent.
CONFIG_INLINE_COMMENT = (
    "schema_version: 1\n"
    "review:\n"
    "  mode: agent\n"
    "  agents:\n"
    "    local_registered:\n"
    "      - name: reviewer                 # matches `.claude/agents/reviewer.md` (default)\n"
)
CONFIG_QUOTED = CONFIG_DEFAULT.replace("- name: reviewer", '- name: "reviewer"')
# An adopter's own agent that documents the deploy marker in its body. Only the
# header (first 5 lines) is the adapter's provenance window; line 20 is not.
ADOPTER_QUOTING_MARKER = (
    "---\nname: reviewer\ndescription: my own reviewer\n---\n"
    + "".join(f"line {i}\n" for i in range(5, 20))
    + f"Kit-deployed agents carry `{MARKER}`; this one does not.\n"
)
assert ADOPTER_QUOTING_MARKER.splitlines()[19].startswith("Kit-deployed")

CONFIG_FLOW = (
    "schema_version: 1\n"
    "review:\n"
    "  mode: agent\n"
    "  agents:\n"
    "    local_registered: [{name: reviewer}]\n"
)


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
    # deployed: "kit-copy" | "adopter-copy" | "adopter-quotes-marker" | "kit-symlink" | None
    deployed: str | None = None,
    new_deployed: bool = False,  # also lay down .claude/agents/pm-reviewer.md
    new_deployed_marker: bool = True,  # ...carrying the kit marker in its header
    # project_agent: "flat" | "folder" | None — adopter source in .pkit/agents/project/
    project_agent: str | None = None,
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
    elif deployed == "adopter-quotes-marker":
        deployed_reviewer.write_text(ADOPTER_QUOTING_MARKER, encoding="utf-8")
    elif deployed == "kit-symlink":
        deployed_reviewer.symlink_to(cap / "agents" / "reviewer.md")

    if new_deployed:
        marker_line = f"{MARKER}\n" if new_deployed_marker else ""
        (claude_agents / "pm-reviewer.md").write_text(
            f"---\n{marker_line}name: pm-reviewer\n---\nbody\n", encoding="utf-8"
        )

    project_agents = root / ".pkit" / "agents" / "project"
    if project_agent == "flat":
        project_agents.mkdir(parents=True)
        (project_agents / "reviewer.md").write_text(
            "---\nname: reviewer\n---\nmine\n", encoding="utf-8"
        )
    elif project_agent == "folder":
        (project_agents / "reviewer").mkdir(parents=True)
        (project_agents / "reviewer" / "reviewer.md").write_text(
            "---\nname: reviewer\n---\nmine\n", encoding="utf-8"
        )
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
    reviewer.md AND laid down pm-reviewer.md. That pm-reviewer.md presence is the
    positive kit signal that lets the absent-reviewer.md case rewrite the config."""
    cap = _install(tmp_path, deployed=None, new_deployed=True)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["pm-reviewer"]


# --- Config-shape breadth: the shapes the `$`-anchored first cut missed ------


def test_inline_comment_shape_is_rewritten(tmp_path) -> None:
    """The exact shape the capability's docs demonstrate — a trailing inline
    comment after `name: reviewer` — must be rewritten, not left dangling."""
    cap = _install(tmp_path, config=CONFIG_INLINE_COMMENT, deployed="kit-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["pm-reviewer"]
    # The trailing comment survives; only the token is rewritten.
    assert "# matches" in (cap / "project" / "config.yaml").read_text(encoding="utf-8")


def test_quoted_value_shape_is_rewritten(tmp_path) -> None:
    """A quoted `name: "reviewer"` value is the default too."""
    cap = _install(tmp_path, config=CONFIG_QUOTED, deployed="kit-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["pm-reviewer"]


def test_flow_style_shape_is_rewritten(tmp_path) -> None:
    """Flow-style `local_registered: [{name: reviewer}]` is the default too."""
    cap = _install(tmp_path, config=CONFIG_FLOW, deployed="kit-copy")
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


def test_absent_reviewer_without_pm_reviewer_signal_is_not_rewritten(tmp_path) -> None:
    """No deployed reviewer.md AND no deployed pm-reviewer.md ⇒ no positive kit
    signal. The config `reviewer` could be an adopter's undeployed/custom agent,
    so it is NOT silently taken over (advisory disambiguator for the absent-file
    branch)."""
    cap = _install(tmp_path, deployed=None, new_deployed=False)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _registered_names(cap) == ["reviewer"]


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


# --- #912 defect 1: provenance uses the adapter's header window --------------


def _config_text(cap: Path) -> str:
    return (cap / "project" / "config.yaml").read_text(encoding="utf-8")


def test_adopter_file_quoting_marker_below_header_is_untouched(tmp_path) -> None:
    """deploy-agents.sh decides "ours" from the first 5 lines only. An adopter's
    reviewer.md quoting the marker on line 20 is adopter content: neither the
    file nor its config registration may be rewritten or removed."""
    cap = _install(tmp_path, deployed="adopter-quotes-marker")
    deployed = tmp_path / ".claude" / "agents" / "reviewer.md"
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert deployed.read_text(encoding="utf-8") == ADOPTER_QUOTING_MARKER
    assert _config_text(cap) == CONFIG_DEFAULT
    assert "no kit marker" in proc.stdout


def test_pm_reviewer_without_marker_is_no_kit_signal(tmp_path) -> None:
    """The post-sync signal is a KIT-deployed pm-reviewer.md: one without the
    header marker is not proof the kit deployed it."""
    cap = _install(tmp_path, deployed=None, new_deployed=True, new_deployed_marker=False)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _config_text(cap) == CONFIG_DEFAULT


# --- #912 defect 2: every local_registered shape, scoped to that list ---------

_HEAD = "schema_version: 1\nreview:\n  mode: agent\n  agents:\n"

# (config before, config expected after) — the expected text pins that only the
# token moves: quoting, comments, indentation and sibling entries survive.
REWRITABLE_SHAPES = {
    "dash-on-own-line": (
        _HEAD + "    local_registered:\n      -\n        name: reviewer\n",
        _HEAD + "    local_registered:\n      -\n        name: pm-reviewer\n",
    ),
    "name-not-first-key": (
        _HEAD + "    local_registered:\n      - path: x\n        name: reviewer\n",
        _HEAD + "    local_registered:\n      - path: x\n        name: pm-reviewer\n",
    ),
    "sequence-level-with-key": (
        _HEAD + "    local_registered:\n    - name: reviewer\n",
        _HEAD + "    local_registered:\n    - name: pm-reviewer\n",
    ),
    "flow-mapping-in-block-item": (
        _HEAD + "    local_registered:\n      - {name: reviewer}\n",
        _HEAD + "    local_registered:\n      - {name: pm-reviewer}\n",
    ),
    "multi-line-flow-sequence": (
        _HEAD + "    local_registered: [\n      {name: code-reviewer},\n"
        '      {"name": "reviewer"}\n    ]\n',
        _HEAD + "    local_registered: [\n      {name: code-reviewer},\n"
        '      {"name": "pm-reviewer"}\n    ]\n',
    ),
    "single-quoted-with-comment": (
        _HEAD + "    local_registered:\n      - name: 'reviewer'   # the default\n",
        _HEAD + "    local_registered:\n      - name: 'pm-reviewer'   # the default\n",
    ),
    "mixed-list": (
        _HEAD + "    local_registered:\n      - name: pm-reviewer\n      - name: reviewer\n"
        "      - name: code-reviewer\n",
        _HEAD + "    local_registered:\n      - name: pm-reviewer\n      - name: pm-reviewer\n"
        "      - name: code-reviewer\n",
    ),
    "crlf": (
        (_HEAD + "    local_registered:\n      - name: reviewer\n").replace("\n", "\r\n"),
        (_HEAD + "    local_registered:\n      - name: pm-reviewer\n").replace("\n", "\r\n"),
    ),
}


@pytest.mark.parametrize("shape", sorted(REWRITABLE_SHAPES))
def test_every_local_registered_shape_is_rewritten(tmp_path, shape) -> None:
    before, after = REWRITABLE_SHAPES[shape]
    cap = _install(tmp_path, config=before, deployed="kit-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert (cap / "project" / "config.yaml").read_bytes().decode("utf-8") == after
    assert "[warn]" not in proc.stdout
    # A re-run on the rewritten shape is a no-op.
    proc = _run(tmp_path)
    assert (cap / "project" / "config.yaml").read_bytes().decode("utf-8") == after
    assert "nothing to reconcile" in proc.stdout


def test_name_reviewer_outside_local_registered_is_never_touched(tmp_path) -> None:
    """Only review.agents.local_registered is in scope: a `name: reviewer`
    elsewhere, a commented-out entry, and a role named `reviewer` all survive."""
    config = (
        "schema_version: 1\n"
        "extras:\n"
        "  - name: reviewer\n"
        "review:\n"
        "  mode: agent\n"
        "  human:\n"
        "    reviewer_role: reviewer\n"
        "  agents:\n"
        "    local_registered:\n"
        "      # - name: reviewer\n"
        "      - name: reviewer\n"
        "  other:\n"
        "    - name: reviewer\n"
    )
    cap = _install(tmp_path, config=config, deployed="kit-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    expected = config.replace(
        "      - name: reviewer\n  other:", "      - name: pm-reviewer\n  other:"
    )
    assert _config_text(cap) == expected


MANUAL_SHAPES = {
    "value-on-next-line": _HEAD + "    local_registered:\n      - name:\n          reviewer\n",
    "anchored-value": _HEAD + "    local_registered:\n      - name: &default reviewer\n",
    "tagged-value": _HEAD + "    local_registered:\n      - name: !!str reviewer\n",
}


@pytest.mark.parametrize("shape", sorted(MANUAL_SHAPES))
def test_unrewritable_shape_is_reported_for_manual_edit(tmp_path, shape) -> None:
    """A shape too exotic to rewrite safely is never left silently unmigrated:
    the config is untouched and a warning names the file and line to edit."""
    config = MANUAL_SHAPES[shape]
    cap = _install(tmp_path, config=config, deployed="kit-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _config_text(cap) == config
    line = next(n for n, text in enumerate(config.splitlines(), 1) if "reviewer" in text)
    assert f"line(s) {line}:" in proc.stdout
    assert "Edit it by hand" in proc.stdout
    assert "[ok]" not in proc.stdout
    assert "[note]" not in proc.stdout


def test_flow_style_parent_is_reported_not_edited(tmp_path) -> None:
    """With local_registered inside a flow-style parent the list can't be
    scoped, so the file is only inspected and the operator told what to edit."""
    config = (
        "schema_version: 1\nreview: {mode: agent, agents: {local_registered: [{name: reviewer}]}}\n"
    )
    cap = _install(tmp_path, config=config, deployed="kit-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _config_text(cap) == config
    assert "cannot scope" in proc.stdout
    assert "line(s) 2" in proc.stdout
    assert "manual config edit" in proc.stdout


def test_unrewritable_shape_without_kit_signal_is_silent_skip(tmp_path) -> None:
    """No kit signal ⇒ the registration is the adopter's; no manual-edit
    warning is raised for it."""
    config = MANUAL_SHAPES["value-on-next-line"]
    cap = _install(tmp_path, config=config, deployed="adopter-copy")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _config_text(cap) == config
    assert "[warn]" not in proc.stdout


# --- #912 defect 3: messages reflect what happened ----------------------------


_NOTE = "[note] any OPEN PR"
_OK = "[ok] reviewer -> pm-reviewer rename reconciled"
_NOOP = "[skip] reviewer -> pm-reviewer rename: nothing to reconcile"


def test_messages_when_config_rewritten(tmp_path) -> None:
    _install(tmp_path, deployed=None, new_deployed=True)
    out = _run(tmp_path).stdout
    assert "[rewrite]" in out and _NOTE in out and _OK in out
    assert _NOOP not in out


def test_messages_when_only_stale_file_removed(tmp_path) -> None:
    """Config already migrated but a stale kit copy remains: removal is a real
    action (so `[ok]`), but no config was rewritten (so no stale-verdict note)."""
    _install(tmp_path, config=CONFIG_MIGRATED, deployed="kit-copy")
    out = _run(tmp_path).stdout
    assert "[remove]" in out and _OK in out
    assert _NOTE not in out and "[rewrite]" not in out


def test_messages_when_nothing_needed(tmp_path) -> None:
    _install(tmp_path, config=CONFIG_MIGRATED, deployed=None, new_deployed=True)
    out = _run(tmp_path).stdout
    assert _NOOP in out
    assert _OK not in out and _NOTE not in out


def test_messages_when_adopter_content_skipped(tmp_path) -> None:
    _install(tmp_path, deployed="adopter-copy")
    out = _run(tmp_path).stdout
    assert "left untouched" in out and _NOOP in out
    assert _OK not in out and _NOTE not in out


def test_messages_on_re_run_are_no_op(tmp_path) -> None:
    _install(tmp_path, deployed="kit-copy")
    first = _run(tmp_path).stdout
    second = _run(tmp_path).stdout
    assert _OK in first and _NOTE in first
    assert _NOOP in second and _OK not in second and _NOTE not in second


# --- #912 defect 4: an undeployed adopter-owned `reviewer` agent --------------


@pytest.mark.parametrize("form", ["flat", "folder"])
@pytest.mark.parametrize("deployed", [None, "kit-copy"])
def test_project_namespace_reviewer_keeps_its_registration(tmp_path, form, deployed) -> None:
    """An adopter's own `reviewer` agent source under .pkit/agents/project/
    owns the registration — undeployed (pm-reviewer.md present, reviewer.md
    absent) or deployed (project wins the name collision, so even a marker copy
    is the adopter's). Config and files are left alone (DEC-028's amendment)."""
    cap = _install(tmp_path, deployed=deployed, new_deployed=True, project_agent=form)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _config_text(cap) == CONFIG_DEFAULT
    assert (tmp_path / ".claude" / "agents" / "reviewer.md").exists() == (deployed is not None)
    assert "adopter-owned reviewer agent source" in proc.stdout
    assert _NOOP in proc.stdout
