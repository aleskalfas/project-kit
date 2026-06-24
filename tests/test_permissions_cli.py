"""Tests for the read-only `pkit permissions` CLI (explain / diff / catalog)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit.cli import main

REPO = Path(__file__).resolve().parent.parent


def _setup(tmp_path: Path, *, grants: str | None = None, config: str | None = None,
           settings: str | None = None) -> Path:
    """Build a tmp project tree with the real privilege catalog + optional
    model / live settings, and return its root."""
    proj = tmp_path / "proj"
    (proj / ".pkit" / "schemas").mkdir(parents=True)
    for f in ("privilege-catalog.yaml", "privilege-catalog.schema.json",
              "confinement-toolkit.yaml"):
        shutil.copy(REPO / ".pkit" / "schemas" / f, proj / ".pkit" / "schemas" / f)
    # The decision core is propagated into every adopter tree; the CLI imports
    # it to build the model through the same loader the hook uses (ADR-002).
    (proj / ".pkit" / "permissions").mkdir(parents=True, exist_ok=True)
    for mod in ("decide.py", "projection.py"):
        shutil.copy(REPO / ".pkit" / "permissions" / mod,
                    proj / ".pkit" / "permissions" / mod)
    # Shipped permission profiles (ADR-005) so `profile list/show/activate` resolve them.
    shutil.copytree(REPO / ".pkit" / "permissions" / "profiles",
                    proj / ".pkit" / "permissions" / "profiles")
    if grants is not None or config is not None:
        (proj / ".pkit" / "permissions" / "project").mkdir(parents=True)
        if grants is not None:
            (proj / ".pkit" / "permissions" / "project" / "grants.yaml").write_text(grants)
        if config is not None:
            (proj / ".pkit" / "permissions" / "project" / "config.yaml").write_text(config)
    if settings is not None:
        (proj / ".claude").mkdir(parents=True)
        (proj / ".claude" / "settings.json").write_text(settings)
    return proj


def _run(proj: Path, monkeypatch, *args) -> str:
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(main, ["permissions", *args])
    assert result.exit_code == 0, result.output
    return result.output


def test_catalog_lists_baseline_privileges(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "catalog")
    assert "vcs" in out and "docker" in out and "scope: directory" in out


def test_explain_baseline_guardrail_denies_present(tmp_path, monkeypatch):
    # With no authored grants the model is not empty: the catalog-derived
    # guardrail denies are always present (the model half of the double-lock).
    out = _run(_setup(tmp_path), monkeypatch, "explain")
    assert "all" in out
    for pid in ("privilege-escalation", "destructive-fs", "vcs-history-rewrite"):
        assert pid in out
    assert "deny" in out


def test_explain_no_grants_for_unknown_agent(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "explain", "nobody")
    assert "no grants declared" in out
    assert "inherits the `all` guardrails" in out


def test_explain_is_self_explanatory(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "explain")
    # title + banner + legend glosses + subject key + guardrail marker + commands
    assert "who may (allow) or may not (deny)" in out
    assert "posture: lenient" in out and "defer to Claude Code" in out
    assert "Legend" in out and "subjects" in out and "agent:<name>" in out
    assert "can't be granted around" in out
    assert "Commands" in out and "pkit permissions grant" in out


def test_explain_renders_a_grant(tmp_path, monkeypatch):
    grants = (
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: agent:critic\n"
        "    privilege: \"[privilege-catalog:repo-read]\"\n"
        "    effect: allow\n"
    )
    out = _run(_setup(tmp_path, grants=grants), monkeypatch, "explain")
    assert "agent:critic" in out and "repo-read" in out and "allow" in out


def test_diff_flags_unjustified_and_extra(tmp_path, monkeypatch):
    # Live settings allow `gh` (recognized -> issue-tracker, but no grant) and
    # `foobar` (no catalog privilege recognizes it). Model is empty.
    settings = '{"permissions": {"allow": ["Bash(gh:*)", "Bash(foobar:*)"], "deny": []}}'
    out = _run(_setup(tmp_path, settings=settings), monkeypatch, "diff")
    assert "unjustified" in out and "issue-tracker" in out
    assert "extra" in out and "foobar" in out


def test_diff_clean_when_grant_justifies_live_rule(tmp_path, monkeypatch):
    grants = (
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: operator\n"
        "    privilege: \"[privilege-catalog:issue-tracker]\"\n"
        "    effect: allow\n"
    )
    settings = '{"permissions": {"allow": ["Bash(gh:*)"], "deny": []}}'
    out = _run(_setup(tmp_path, grants=grants, settings=settings), monkeypatch, "diff")
    assert "every live allow rule is justified" in out


# --- grant / revoke / mode --------------------------------------------------


def _run_fail(proj: Path, monkeypatch, *args) -> str:
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(main, ["permissions", *args])
    assert result.exit_code != 0, result.output
    return result.output


def test_grant_then_explain_roundtrip(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "grant", "agent:critic", "repo-read")
    out = _run(proj, monkeypatch, "explain")
    assert "agent:critic" in out and "repo-read" in out and "allow" in out
    g = (proj / ".pkit" / "permissions" / "project" / "grants.yaml").read_text()
    assert "[privilege-catalog:repo-read]" in g


def test_grant_deny_then_revoke(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "grant", "agent:devops", "docker", "--deny")
    out = _run(proj, monkeypatch, "explain", "devops")
    assert "deny" in out and "docker" in out
    _run(proj, monkeypatch, "revoke", "agent:devops", "docker")
    out = _run(proj, monkeypatch, "explain", "devops")
    assert "no grants declared" in out


def test_grant_unknown_privilege_refused(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "grant", "operator", "nonexistent")
    assert "not in the catalog" in out


def test_grant_scope_refused_for_unscoped_privilege(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "grant", "operator", "vcs", "--scope", "src/**")
    assert "scope_type" in out


def test_grant_scope_ok_for_docker(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "grant", "agent:devops", "docker", "--scope", "services/**")
    out = _run(proj, monkeypatch, "explain", "devops")
    assert "docker" in out and "services/**" in out


def test_grant_invalid_subject_refused(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "grant", "Bad Subject", "vcs")
    assert "invalid subject" in out


def test_grant_idempotent_update(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "grant", "operator", "vcs")
    _run(proj, monkeypatch, "grant", "operator", "vcs")
    g = (proj / ".pkit" / "permissions" / "project" / "grants.yaml").read_text()
    assert g.count("privilege-catalog:vcs") == 1


def test_mode_show_and_set(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    assert "additive" in _run(proj, monkeypatch, "mode")
    assert "managed" in _run(proj, monkeypatch, "mode", "managed")
    assert "managed" in _run(proj, monkeypatch, "mode")


# ---- enable / disable live enforcement -------------------------------------

import json  # noqa: E402

HOOK_COMMAND = "${CLAUDE_PROJECT_DIR}/.pkit/adapters/claude-code/permission-hook.py"


def _with_adapter(proj: Path) -> Path:
    """Add the claude-code adapter substrate enable/disable need: a manifest
    entry + the canonical core settings (the native deny source)."""
    (proj / ".pkit").mkdir(parents=True, exist_ok=True)
    (proj / ".pkit" / "manifest.yaml").write_text(
        "components:\n  - kind: adapter\n    name: claude-code\n"
    )
    core = proj / ".pkit" / "adapters" / "claude-code" / "settings" / "core"
    core.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        REPO / ".pkit" / "adapters" / "claude-code" / "settings" / "core" / "settings.json",
        core / "settings.json",
    )
    # The enforcement declaration drives the gap report (apply / diff).
    shutil.copy(
        REPO / ".pkit" / "adapters" / "claude-code" / "permission-enforcement.yaml",
        proj / ".pkit" / "adapters" / "claude-code" / "permission-enforcement.yaml",
    )
    return proj


_ALL_VCS = (
    "schema_version: 1\n"
    "grants:\n"
    "  - subject: all\n"
    "    privilege: \"[privilege-catalog:vcs]\"\n"
    "    effect: allow\n"
)


def _settings(proj: Path) -> dict:
    return json.loads((proj / ".claude" / "settings.json").read_text())


def test_enable_registers_hook_and_native_denies(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "enable")
    assert "enabled" in out
    data = _settings(proj)
    entries = data["hooks"]["PreToolUse"]
    assert any(
        h.get("command") == HOOK_COMMAND
        for e in entries for h in e.get("hooks", [])
    )
    # The fail-closed half of the double-lock is present.
    assert "Bash(sudo:*)" in data["permissions"]["deny"]


def test_enable_idempotent(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "enable")
    _run(proj, monkeypatch, "enable")
    entries = _settings(proj)["hooks"]["PreToolUse"]
    cmds = [h.get("command") for e in entries for h in e.get("hooks", [])]
    assert cmds.count(HOOK_COMMAND) == 1


def test_disable_strips_only_pkit_hook(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    # Pre-existing adopter hook that must survive disable.
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / ".claude" / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}
        ]}
    }))
    _run(proj, monkeypatch, "enable")
    out = _run(proj, monkeypatch, "disable")
    assert "disabled" in out
    data = _settings(proj)
    cmds = [h.get("command") for e in data["hooks"]["PreToolUse"] for h in e.get("hooks", [])]
    assert "echo mine" in cmds and HOOK_COMMAND not in cmds


def test_disable_idempotent_and_removes_empty_hooks(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "enable")
    _run(proj, monkeypatch, "disable")
    # No orphaned hook structure when ours was the only entry.
    assert "hooks" not in _settings(proj)
    assert "already disabled" in _run(proj, monkeypatch, "disable")


def test_enable_refused_without_adapter(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "enable")
    assert "claude-code adapter is not installed" in out


# --- overview ---------------------------------------------------------------

def test_overview_groups_guardrails_and_enablers(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "overview")
    assert "GUARDRAILS" in out and "ENABLERS" in out
    # guardrails (deny floor) vs enablers (grant to enable) land in their sections
    g_section = out.split("ENABLERS")[0]
    e_section = out.split("ENABLERS")[1]
    assert "destructive-fs" in g_section and "double-locked" in g_section
    assert "issue-tracker" in e_section and "vcs" in e_section
    # provenance is surfaced + explained in the legend
    assert "backbone" in out and "capability:<name>" in out


def test_overview_shows_granted_to(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "grant", "operator", "vcs")
    out = _run(proj, monkeypatch, "overview")
    # the vcs enabler line now names its grantee
    vcs_line = next(ln for ln in out.splitlines() if ln.strip().startswith("vcs "))
    assert "granted to: operator" in vcs_line


def test_overview_shows_enforcement_status_legend_and_commands(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    # No settings file → enforcement OFF.
    out = _run(proj, monkeypatch, "overview")
    assert "Live enforcement: OFF" in out
    # Register the hook in the same tree → ON.
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "*", "hooks": [{"type": "command", "command": HOOK_COMMAND}]}
    ]}}))
    out = _run(proj, monkeypatch, "overview")
    assert "Live enforcement: ON" in out
    # The explanatory scaffolding the user asked for.
    assert "Legend" in out and "double-locked" in out
    assert "Commands" in out and "pkit permissions enable" in out


# ---- apply (additive realization, #250) ------------------------------------

def test_apply_realizes_allow_and_guardrail_denies(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path, grants=_ALL_VCS))
    out = _run(proj, monkeypatch, "apply")
    assert "applied (additive)" in out
    data = _settings(proj)
    assert "Bash(git:*)" in data["permissions"]["allow"]          # projected allow
    assert "Bash(sudo:*)" in data["permissions"]["deny"]          # ensured guardrail deny


def test_apply_is_idempotent(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path, grants=_ALL_VCS))
    _run(proj, monkeypatch, "apply")
    before = _settings(proj)
    out = _run(proj, monkeypatch, "apply")
    assert "already realized" in out
    assert _settings(proj) == before  # fixed point — no duplicates, no change


def test_apply_is_additive_preserves_existing(tmp_path, monkeypatch):
    settings = json.dumps({"permissions": {"allow": ["Bash(myown:*)"], "deny": []}})
    proj = _with_adapter(_setup(tmp_path, grants=_ALL_VCS, settings=settings))
    _run(proj, monkeypatch, "apply")
    allow = _settings(proj)["permissions"]["allow"]
    assert "Bash(myown:*)" in allow and "Bash(git:*)" in allow  # added, removed nothing


def test_apply_reports_out_of_harness_gap(tmp_path, monkeypatch):
    # A per-agent bash grant projects to runtime, not settings → shows in the gap.
    grants = (
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: agent:pm\n"
        "    privilege: \"[privilege-catalog:vcs]\"\n"
        "    effect: allow\n"
    )
    proj = _with_adapter(_setup(tmp_path, grants=grants))
    out = _run(proj, monkeypatch, "apply")
    assert "out-of-harness gap" in out
    assert "enforced at runtime" in out                 # pm's vcs (per-agent bash)
    assert "not natively enforceable" in out            # network-egress (enforcement: none)


def test_apply_refused_without_adapter(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path, grants=_ALL_VCS), monkeypatch, "apply")
    assert "claude-code adapter is not installed" in out


def test_apply_refused_in_managed_mode(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(
        tmp_path, grants=_ALL_VCS,
        config="schema_version: 1\nownership_mode: managed\nposture: lenient\n",
    ))
    out = _run_fail(proj, monkeypatch, "apply")
    assert "managed" in out and "#252" in out


# ---- profiles (#255 / ADR-005) ---------------------------------------------

def test_profile_list_shows_shipped_tiers(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "profile", "list")
    assert "read-only" in out and "non-destructive" in out and "autonomous" in out
    # description column rendered per profile
    assert "Read the repo only" in out
    # house-style banner + Legend + Commands footer (not an ad-hoc trailer)
    assert "Active profile: none" in out
    assert "Legend" in out and "Commands" in out and "profile show" in out
    # all-shipped default: the SOURCE column is suppressed (no per-row noise)
    assert "shipped" not in out


def test_profile_list_shows_source_only_when_project_profile_exists(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    d = proj / ".pkit" / "permissions" / "project" / "profiles"
    d.mkdir(parents=True)
    (d / "house.yaml").write_text(
        "schema_version: 1\ndescription: house tier\nposture: strict\ngrants: []\n"
    )
    out = _run(proj, monkeypatch, "profile", "list")
    # now that a project profile exists, SOURCE becomes informative and appears
    assert "house" in out and "shipped" in out and "project" in out


def test_profile_show(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "profile", "show", "non-destructive")
    assert "non-destructive" in out and "vcs" in out and "issue-tracker" in out
    # grants are enriched with their catalog meaning, not just bare ids
    assert "Git version control." in out
    # house format: GRANTS section + Commands footer; uniform all/allow in header
    assert "GRANTS" in out and "Commands" in out
    assert "every agent and the operator" in out


def test_profile_show_unknown_refused(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "profile", "show", "nope")
    assert "no profile named" in out


def test_profile_activate_sets_active_and_layers_grants(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    out = _run(proj, monkeypatch, "profile", "activate", "non-destructive", "--no-apply")
    assert "active" in out
    cfg = (proj / ".pkit" / "permissions" / "project" / "config.yaml").read_text()
    assert "active_profile: non-destructive" in cfg
    # the profile's grants are now live in the model (explain shows them, layered)
    out = _run(proj, monkeypatch, "explain")
    assert "vcs" in out and "issue-tracker" in out


def test_profile_activate_marks_active_in_list(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "profile", "activate", "read-only", "--no-apply")
    out = _run(proj, monkeypatch, "profile", "list")
    assert "read-only" in out and "active" in out


def test_profile_activate_does_not_clobber_manual_grants(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "grant", "agent:devops", "docker")          # manual grant
    _run(proj, monkeypatch, "profile", "activate", "non-destructive", "--no-apply")
    g = (proj / ".pkit" / "permissions" / "project" / "grants.yaml").read_text()
    assert "[privilege-catalog:docker]" in g                            # still there
    out = _run(proj, monkeypatch, "explain", "devops")
    assert "docker" in out                                              # manual grant survives


def test_profile_activate_unknown_refused(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "profile", "activate", "nope")
    assert "no profile named" in out


# ---- sandbox confinement (ADR-004 / ADR-005, #274) ---------------------------

CRED_PATHS = ["~/.ssh", "~/.aws", "~/.config/gh", "~/.netrc"]


def test_sandbox_enable_writes_fail_closed_block(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "sandbox enabled" in out
    assert "not hot-reloaded" in out                       # restart note
    sb = _settings(proj)["sandbox"]
    assert sb["enabled"] is True
    assert sb["autoAllowBashIfSandboxed"] is True
    assert sb["failIfUnavailable"] is True                 # the ADR-004 invariant
    assert "allowUnsandboxedCommands" not in sb            # reconciled: harness default
    for p in CRED_PATHS:
        assert p in sb["filesystem"]["denyRead"]           # credential floor


def test_sandbox_enable_idempotent(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "sandbox", "enable")
    before = _settings(proj)
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "already" in out
    assert _settings(proj) == before                       # fixed point, no duplicates


def test_sandbox_enable_additive_preserves_operator_keys(tmp_path, monkeypatch):
    settings = json.dumps({"sandbox": {
        "excludedCommands": ["docker *"],
        "filesystem": {"denyRead": ["~/secrets"]},
    }})
    proj = _with_adapter(_setup(tmp_path, settings=settings))
    _run(proj, monkeypatch, "sandbox", "enable")
    sb = _settings(proj)["sandbox"]
    assert sb["excludedCommands"] == ["docker *"]          # operator key survives
    assert "~/secrets" in sb["filesystem"]["denyRead"]     # operator entry survives
    assert "~/.ssh" in sb["filesystem"]["denyRead"]        # floor unioned in


def test_sandbox_enable_strict_locks_fail_over(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "enable", "--strict")
    assert "strict" in out
    assert _settings(proj)["sandbox"]["allowUnsandboxedCommands"] is False


def test_sandbox_dangerous_flag_is_loud_and_not_persisted_as_default(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "enable", "--dangerously-allow-unconfined")
    assert "DANGEROUS" in out and "UNCONFINED" in out
    assert _settings(proj)["sandbox"]["failIfUnavailable"] is False
    # Re-running WITHOUT the flag restores the fail-closed floor.
    _run(proj, monkeypatch, "sandbox", "enable")
    assert _settings(proj)["sandbox"]["failIfUnavailable"] is True


def test_sandbox_disable_flips_enabled_only(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "sandbox", "enable", "--strict")
    out = _run(proj, monkeypatch, "sandbox", "disable")
    assert "disabled" in out and "not hot-reloaded" in out
    sb = _settings(proj)["sandbox"]
    assert sb["enabled"] is False
    assert sb["allowUnsandboxedCommands"] is False         # operator keys left in place
    assert "~/.ssh" in sb["filesystem"]["denyRead"]
    assert "already disabled" in _run(proj, monkeypatch, "sandbox", "disable")


def test_sandbox_status_off_and_on(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox")               # no subcommand = status
    assert "OFF" in out and "sandbox enable" in out
    _run(proj, monkeypatch, "sandbox", "enable")
    out = _run(proj, monkeypatch, "sandbox")
    assert "ON" in out and "prompt-free" in out
    assert "closed" in out                                 # fail mode line
    assert "complete" in out                               # credential floor line


def test_sandbox_status_warns_on_fail_open(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "sandbox", "enable", "--dangerously-allow-unconfined")
    out = _run(proj, monkeypatch, "sandbox")
    assert "OPEN" in out and "UNCONFINED" in out


def test_sandbox_enable_refused_without_adapter(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "sandbox", "enable")
    assert "claude-code adapter is not installed" in out


# ---- auto-accommodation of narrowing toolkits on sandbox enable (#22) --------

def test_sandbox_enable_auto_accommodates_uv_when_detected(tmp_path, monkeypatch):
    """When uv.lock is present, `sandbox enable` auto-applies the uv-cache
    narrowing allowance via the provenance writer (ADR-008 single-writer rule)."""
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")              # signals uv toolkit
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "auto-accommodated" in out and "uv" in out
    assert "~/.cache/uv" in _sb(proj)["filesystem"]["allowWrite"]
    # recorded in permission-config (committable narrowing list)
    cfg = (proj / ".pkit" / "permissions" / "project" / "config.yaml").read_text()
    assert "[confinement-toolkit:uv]" in cfg
    # widening never written
    assert "excludedCommands" not in _sb(proj)


def test_sandbox_enable_auto_accommodate_uv_idempotent(tmp_path, monkeypatch):
    """Re-running `sandbox enable` when uv is already accommodated is a no-op:
    no duplicate entries in allowWrite, settings file is a fixed point."""
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    _run(proj, monkeypatch, "sandbox", "enable")
    before = _settings(proj)
    _run(proj, monkeypatch, "sandbox", "enable")
    assert _settings(proj) == before
    assert _sb(proj)["filesystem"]["allowWrite"].count("~/.cache/uv") == 1


def test_sandbox_enable_does_not_accommodate_when_uv_absent(tmp_path, monkeypatch):
    """When no uv.lock or pyproject.toml is present, no uv allowance is written."""
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "auto-accommodated" not in out
    fs = _sb(proj).get("filesystem", {})
    assert "~/.cache/uv" not in fs.get("allowWrite", [])
    cfgp = proj / ".pkit" / "permissions" / "project" / "config.yaml"
    if cfgp.is_file():
        assert "confinement-toolkit:uv" not in cfgp.read_text()


def test_sandbox_enable_auto_accommodate_provenance_tagged_narrowing(tmp_path, monkeypatch):
    """The auto-applied uv allowance is recorded in sandbox-provenance.yaml as
    authored by the 'uv' toolkit (the provenance writer — ADR-008 rule 2)."""
    import json as _json
    from ruamel.yaml import YAML as _YAML
    proj = _with_adapter(_setup(tmp_path))
    (proj / "pyproject.toml").write_text("[build-system]\n")  # pyproject.toml also detects uv
    _run(proj, monkeypatch, "sandbox", "enable")
    prov_path = proj / ".pkit" / "permissions" / "project" / "sandbox-provenance.yaml"
    assert prov_path.is_file(), "provenance file not written"
    yaml = _YAML(typ="safe")
    with prov_path.open() as fh:
        doc = yaml.load(fh)
    entries = doc.get("entries", [])
    uv_entries = [e for e in entries if e.get("toolkit") == "uv"]
    assert uv_entries, "no uv-tagged provenance entries found"
    # Each uv entry corresponds to a narrowing allowance
    for e in uv_entries:
        assert e.get("kind") == "allow-write"
        assert e.get("value") == "~/.cache/uv"


def test_overview_banner_gains_sandbox_line(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "overview")
    assert "sandbox OFF" in out
    _run(proj, monkeypatch, "sandbox", "enable")
    out = _run(proj, monkeypatch, "overview")
    assert "sandbox ON" in out and "fail-closed" in out


# ---- probe (#276) ------------------------------------------------------------

def test_probe_empty_model_guardrails_hold_and_exit_zero(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "probe")
    assert "DECISION LAYER" in out
    # Guardrails REJECTED even with no grants at all.
    assert out.count("REJECTED") >= 3
    # Ungranted enablers + unrecognized commands fall through to posture.
    assert "NOT COVERED" in out and "lenient" in out
    assert "BROKEN" not in out
    assert "all behave as the model declares" in out
    # Honest framing: decision layer + coverage scope named.
    assert "decision layer proves the verdict" in out
    assert "baseline catalog only" in out


def test_probe_reflects_grants(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path, grants=_ALL_VCS), monkeypatch, "probe")
    assert "version control — `git status`" in out
    # The vcs probe is ALLOWED and matches; force-push stays REJECTED (deny-wins
    # across the union: vcs allow + vcs-history-rewrite guardrail).
    assert "ALLOWED — allow grant for operator on ['vcs']" in out
    assert "REJECTED — deny grant for operator on ['vcs-history-rewrite']" in out
    assert "BROKEN" not in out


def test_probe_strict_posture_uncovered_is_denied(tmp_path, monkeypatch):
    proj = _setup(tmp_path, config="schema_version: 1\nposture: strict\n")
    out = _run(proj, monkeypatch, "probe")
    assert "posture: strict" in out
    # The unrecognized probe is REJECTED under strict — and that MATCHES.
    assert "an unrecognized command" in out
    tail = out.split("an unrecognized command")[1]
    assert "REJECTED" in tail.splitlines()[1] and "✓ works" in tail
    assert "BROKEN" not in out


def test_probe_scope_deny_outside_cwd(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "grant", "all", "docker", "--scope", str(proj / "**"))
    out = _run(proj, monkeypatch, "probe")
    # In-project docker ALLOWED; out-of-scope (cwd /) docker REJECTED — both match.
    assert "docker in the project" in out
    assert "docker outside a scoped grant's boundary" in out
    outside = out.split("docker outside a scoped grant's boundary")[1]
    assert "REJECTED" in outside.splitlines()[1] and "✓ works" in outside
    # A real boundary was exercised — the unscoped-grant gloss must NOT appear.
    assert "no directory boundary exists" not in out
    assert "BROKEN" not in out


def test_probe_unscoped_grant_allowed_carries_honesty_gloss(tmp_path, monkeypatch):
    # An UNscoped docker grant: cwd / is legitimately ALLOWED, but the probe
    # must say no boundary was tested rather than reading like a scope check.
    proj = _setup(tmp_path)
    _run(proj, monkeypatch, "grant", "all", "docker")
    out = _run(proj, monkeypatch, "probe")
    outside = out.split("docker outside a scoped grant's boundary")[1]
    assert "ALLOWED" in outside.splitlines()[1] and "✓ works" in outside
    assert "the active grant is unscoped — no directory boundary exists" in outside
    assert "BROKEN" not in out


def test_probe_catches_dropped_guardrail_via_golden_expectation(tmp_path, monkeypatch):
    # Tamper the propagated decision core: guardrail_denies returns nothing.
    # The live verdict AND the computed oracle then agree on abstain — only the
    # static golden expectation (guardrail: always deny) catches the regression.
    proj = _setup(tmp_path)
    core = proj / ".pkit" / "permissions" / "decide.py"
    core.write_text(core.read_text().replace(
        "for pid in sorted(catalog.get(\"privileges\", {})):",
        "for pid in []:",
    ))
    out = _run_fail(proj, monkeypatch, "probe")
    assert "BROKEN" in out and "golden expectation" in out


def test_probe_catches_recognizer_drift(tmp_path, monkeypatch):
    # Tamper the catalog: sudo is no longer recognized as privilege-escalation.
    proj = _setup(tmp_path)
    cat = proj / ".pkit" / "schemas" / "privilege-catalog.yaml"
    cat.write_text(cat.read_text().replace("- cmd: sudo", "- cmd: sudoXX"))
    out = _run_fail(proj, monkeypatch, "probe")
    assert "recognizer drift" in out
    assert "privilege-escalation" in out


def test_probe_double_lock_missing_deny_breaks_only_when_hook_on(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    # Hook OFF, no denies in live settings → informational, exit 0.
    out = _run(proj, monkeypatch, "probe")
    assert "⚠ missing" in out and "hook enforcement: OFF" in out
    # Hook ON (enable also writes the denies) → all present, exit 0.
    _run(proj, monkeypatch, "enable")
    out = _run(proj, monkeypatch, "probe")
    assert "present verbatim" in out and "hook enforcement: ON" in out
    # Now delete one deny while the hook is ON → BROKEN, exit 1.
    data = _settings(proj)
    data["permissions"]["deny"] = [d for d in data["permissions"]["deny"] if d != "Bash(sudo:*)"]
    (proj / ".claude" / "settings.json").write_text(json.dumps(data))
    out = _run_fail(proj, monkeypatch, "probe")
    assert "✗ BROKEN" in out and "Bash(sudo:*)" in out


def test_probe_live_confinement_honest_verdicts(tmp_path, monkeypatch):
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    readable = tmp_path / "fake-cred"
    readable.write_text("not-a-secret")
    monkeypatch.setattr(perm, "SANDBOX_CREDENTIAL_DENY_READ",
                        [str(readable), str(tmp_path / "absent-cred")])
    # Sandbox OFF in settings → ALLOWED is "not configured", never a pass.
    out = _run(proj, monkeypatch, "probe", "--live")
    assert "CONFINEMENT FLOOR" in out
    assert "confinement not configured" in out
    assert "absent on this machine" in out
    # Sandbox ON in settings but this process is outside the box → UNPROVEN.
    _run(proj, monkeypatch, "sandbox", "enable")
    out = _run(proj, monkeypatch, "probe", "--live")
    assert "UNPROVEN" in out and "outside the box" in out
    assert "no bytes read" in out


def test_probe_subject_agent(tmp_path, monkeypatch):
    grants = (
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: agent:critic\n"
        "    privilege: \"[privilege-catalog:repo-read]\"\n"
        "    effect: allow\n"
    )
    proj = _setup(tmp_path, grants=grants)
    out = _run(proj, monkeypatch, "probe", "--subject", "agent:critic")
    assert "subject: agent:critic" in out
    assert "ALLOWED — allow grant for agent:critic on ['repo-read']" in out
    assert "BROKEN" not in out
    # The same probe as operator: repo-read not granted → NOT COVERED, still ✓.
    out = _run(proj, monkeypatch, "probe")
    assert "ALLOWED — allow grant" not in out.split("repository read")[1].splitlines()[1]


def test_probe_invalid_subject_refused(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "probe", "--subject", "Bogus!")
    assert "invalid subject" in out


# ---- setup goals (ADR-007, #279) ----------------------------------------------

def test_setup_lists_goals_when_bare(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "setup")
    assert "autonomy" in out and "resumable" in out
    assert "setup <goal> down" in out


def test_setup_autonomy_first_run_stands_up_and_stops_at_restart(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "setup", "autonomy")
    # All three switches stood up via the primitives.
    assert "[1/4] intent" in out and "done — profile 'autonomous' activated" in out
    assert "[2/4] enforcement" in out and "hook registered" in out
    assert "[3/4] confinement" in out and "fail-closed" in out
    # Honest boundary (rule 4): blocked at the restart, with the instruction.
    assert "blocked: sandbox.enabled is not hot-reloaded" in out
    assert "restart the session" in out
    assert "goal reached" not in out  # never declared on configuration alone
    data = _settings(proj)
    assert data["sandbox"]["enabled"] is True and data["sandbox"]["failIfUnavailable"] is True
    assert any("permission-hook" in h.get("command", "")
               for e in data["hooks"]["PreToolUse"] for h in e.get("hooks", []))


def test_setup_autonomy_resumes_and_reports_pending_outside_box(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "setup", "autonomy")          # first run: stands up
    out = _run(proj, monkeypatch, "setup", "autonomy")    # re-run: skips + verifies
    assert "already — profile 'autonomous' active" in out
    assert "already — PreToolUse hook registered" in out
    assert "already — OS sandbox enabled" in out
    # Verification ran; decision layer proven; floor honestly pending (we are
    # not inside the box in tests) — goal NOT declared reached.
    assert "decision layer proven" in out
    assert "One step left: restart the session" in out
    assert "goal reached" not in out


def test_setup_autonomy_declares_goal_only_when_floor_proven(tmp_path, monkeypatch):
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "setup", "autonomy")
    # Simulate running inside the box: the credential floor is OS-rejected.
    monkeypatch.setattr(perm, "_reach_attempt", lambda _p: "rejected")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "credential floor REJECTED by the OS" in out
    assert "Result: goal reached — autonomous agents: configured, confined, and proven." in out


def test_setup_autonomy_broken_decision_layer_fails(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "setup", "autonomy")
    # Tamper the catalog so a probe breaks (recognizer drift).
    cat = proj / ".pkit" / "schemas" / "privilege-catalog.yaml"
    cat.write_text(cat.read_text().replace("- cmd: sudo", "- cmd: sudoXX"))
    out = _run_fail(proj, monkeypatch, "setup", "autonomy")
    assert "✗ BROKEN" in out and "pkit permissions probe" in out


def test_setup_autonomy_custom_profile(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "setup", "autonomy", "--profile", "non-destructive")
    assert "profile 'non-destructive' activated" in out


def test_setup_autonomy_down_reports_residuals_loudly(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "setup", "autonomy")
    out = _run(proj, monkeypatch, "setup", "autonomy", "down")
    assert "PreToolUse hook stripped" in out
    assert "sandbox disabled" in out
    # Rule 7: the residual is named, never a bare success.
    assert "STILL ACTIVE in the model" in out and "UNENFORCED" in out
    assert "profile activate read-only" in out
    data = _settings(proj)
    assert data["sandbox"]["enabled"] is False
    assert "~/.ssh" in data["sandbox"]["filesystem"]["denyRead"]   # operator keys left
    # Idempotent re-run.
    out = _run(proj, monkeypatch, "setup", "autonomy", "down")
    assert "hook already off" in out and "sandbox already off" in out


def test_setup_autonomy_refused_without_adapter(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "setup", "autonomy")
    assert "claude-code adapter is not installed" in out


def test_setup_autonomy_no_dangerous_flag(tmp_path, monkeypatch):
    # ADR-007 rule 6: the orchestrator must not accept the escape hatch.
    proj = _with_adapter(_setup(tmp_path))
    out = _run_fail(proj, monkeypatch, "setup", "autonomy", "--dangerously-allow-unconfined")
    assert "no such option" in out.lower() or "No such option" in out


# ---- confinement allowances (ADR-008, #281) ----------------------------------

def _sb(proj: Path) -> dict:
    p = proj / ".claude" / "settings.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text()).get("sandbox", {})


def test_toolkit_list_marks_effect(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "sandbox", "toolkit", "list")
    assert "uv" in out and "narrowing" in out
    assert "docker" in out and "widening" in out
    assert "Legend" in out


def test_toolkit_show_marks_each_allowance(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    out = _run(proj, monkeypatch, "sandbox", "toolkit", "show", "gh")
    assert "exclude-command" in out and "widening" in out
    assert "WIDENING allowances" in out and "sandbox exclude" in out
    out = _run(proj, monkeypatch, "sandbox", "toolkit", "show", "uv")
    assert "allow-write" in out and "narrowing" in out and "~/.cache/uv" in out


def test_toolkit_show_unknown_refused(tmp_path, monkeypatch):
    out = _run_fail(_setup(tmp_path), monkeypatch, "sandbox", "toolkit", "show", "nope")
    assert "no confinement toolkit named" in out


def test_accommodate_applies_narrowing_only(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "uv")
    assert "narrowing applied" in out
    assert "~/.cache/uv" in _sb(proj)["filesystem"]["allowWrite"]
    # recorded in config (committable, narrowing-only)
    cfg = (proj / ".pkit" / "permissions" / "project" / "config.yaml").read_text()
    assert "[confinement-toolkit:uv]" in cfg
    # nothing widening was written
    assert "excludedCommands" not in _sb(proj)


def test_accommodate_idempotent(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "sandbox", "accommodate", "uv")
    before = _settings(proj)
    _run(proj, monkeypatch, "sandbox", "accommodate", "uv")
    assert _sb(proj)["filesystem"]["allowWrite"].count("~/.cache/uv") == 1
    assert _settings(proj) == before


def test_accommodate_widening_only_tool_nudges_to_exclude(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "docker")
    assert "all WIDENING" in out and "sandbox exclude docker" in out
    assert "excludedCommands" not in _sb(proj)   # never applied here


def test_accommodate_detect(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")              # signals uv
    (proj / "Dockerfile").write_text("FROM x")     # signals docker (widening)
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "--detect")
    assert "uv" in out
    assert "~/.cache/uv" in _sb(proj)["filesystem"]["allowWrite"]
    # docker is widening → detected but NOT auto-excluded
    assert "excludedCommands" not in _sb(proj)


def test_accommodate_remove_only_pkit_entries(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    # operator hand-added the SAME path independently.
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / ".claude" / "settings.json").write_text(json.dumps({
        "sandbox": {"enabled": True, "filesystem": {"allowWrite": ["~/.cache/uv", "~/mine"]}}
    }))
    _run(proj, monkeypatch, "sandbox", "accommodate", "uv")     # pkit also "adds" it (dedup)
    _run(proj, monkeypatch, "sandbox", "accommodate", "uv", "--remove")
    aw = _sb(proj)["filesystem"]["allowWrite"]
    # provenance had uv→~/.cache/uv; removal drops it, but operator's ~/mine stays.
    # The operator's ~/.cache/uv intent collides — documented: pkit removes its tagged entry.
    assert "~/mine" in aw


def test_exclude_is_loud_and_not_committed(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "exclude", "docker")
    assert "WIDENING" in out and "UNCONFINED" in out
    assert "NOT recorded in any committed file" in out
    assert "docker" in _sb(proj)["excludedCommands"]
    # never written to permission-config
    cfgp = proj / ".pkit" / "permissions" / "project" / "config.yaml"
    if cfgp.is_file():
        assert "docker" not in cfgp.read_text()


def test_exclude_remove(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "sandbox", "exclude", "docker")
    out = _run(proj, monkeypatch, "sandbox", "exclude", "docker", "--remove")
    assert "runs inside the box again" in out
    assert "docker" not in _sb(proj).get("excludedCommands", [])


def test_exclude_needs_command_or_flag(tmp_path, monkeypatch):
    out = _run_fail(_with_adapter(_setup(tmp_path)), monkeypatch, "sandbox", "exclude")
    assert "give a COMMAND" in out.lower() or "give a command" in out.lower()


def test_setup_autonomy_applies_accommodations_and_nudges_widening(tmp_path, monkeypatch):
    from project_kit import permissions as perm
    # This test exercises the NUDGE-ONLY (optional widening) path; neutralise the
    # required-exclusion auto-apply (its own tests below) so the run is
    # deterministic regardless of the host platform / installed uv version.
    monkeypatch.setattr(perm, "_uv_required_exclusion", lambda _r: False)
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    (proj / "Dockerfile").write_text("FROM x")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    # narrowing auto-applied for the detected uv
    assert "accommodations:" in out and "uv" in out
    assert "~/.cache/uv" in _sb(proj)["filesystem"]["allowWrite"]
    # docker (widening) surfaced in the Next block as a backtick-wrapped command
    # on its own line; Title-case header + whitespace zoning, NO horizontal rules
    # (per the CLI output convention). Never applied.
    assert "Next — run these yourself" in out
    # docker is an OPTIONAL widening (not the macOS-mandatory uv/pkit) → "optional" copy
    assert "`docker` — optional" in out and "run unconfined" in out
    assert "`pkit permissions sandbox exclude docker`" in out   # backtick-wrapped, own line
    assert "────" not in out          # no drawn rules (convention)
    assert "── NEXT" not in out        # no divider header either
    assert "excludedCommands" not in _sb(proj)


def test_setup_autonomy_down_reports_accommodation_residual(tmp_path, monkeypatch):
    from project_kit import permissions as perm
    # Deterministic across hosts: neutralise the required-exclusion auto-apply so
    # the residual under test is the narrowing accommodation + the operator's
    # manual docker widening (the required exclusion has its own teardown test).
    monkeypatch.setattr(perm, "_uv_required_exclusion", lambda _r: False)
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    _run(proj, monkeypatch, "setup", "autonomy")
    _run(proj, monkeypatch, "sandbox", "exclude", "docker")     # a manual widening
    out = _run(proj, monkeypatch, "setup", "autonomy", "down")
    assert "narrowing accommodations remain" in out and "uv" in out
    assert "WIDENING exclusions remain" in out and "docker" in out


# ---- required-exclusion auto-apply + self-heal (ADR-027, #256) ---------------
#   Auto-apply the macOS uv exclusion ONLY when necessity is verified (version
#   floor) and a uv repo marker is present; never on Linux, new-uv, or bare PATH.
#   Distinct `_required` provenance, correct status attribution, self-heal, and
#   teardown reversal. Tests mock `_read_uv_version` (the robust subprocess read)
#   and `sys.platform` so they are deterministic on any host.

from packaging.version import Version as _V  # noqa: E402


def _force_uv(monkeypatch, *, platform="darwin", version="0.9.8"):
    """Make the auto-apply predicate deterministic: pin the platform and the
    installed uv version. version=None simulates uv unreadable / absent."""
    from project_kit import permissions as perm
    monkeypatch.setattr("sys.platform", platform)
    monkeypatch.setattr(perm, "_read_uv_version",
                        lambda: (_V(version) if version else None))


def test_required_exclusion_auto_applies_on_macos_old_uv_with_marker(tmp_path, monkeypatch):
    _force_uv(monkeypatch, platform="darwin", version="0.9.8")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")                 # real project use
    out = _run(proj, monkeypatch, "setup", "autonomy")
    # Loud, dedicated block (NOT folded into the quiet "accommodations:" line).
    assert "Required exclusion (platform-mandatory" in out
    assert "REQUIRED exclusion auto-applied: `uv`" in out
    assert "OUTSIDE the OS box — UNCONFINED" in out
    # Applied via the real primitive → lands in live settings excludedCommands.
    assert "uv" in _sb(proj)["excludedCommands"]
    # Distinct provenance tag — `_required`, NOT `_manual`.
    prov_path = proj / ".pkit" / "permissions" / "project" / "sandbox-provenance.yaml"
    from ruamel.yaml import YAML as _YAML
    doc = _YAML(typ="safe").load(prov_path.open())
    req = [e for e in doc["entries"]
           if e.get("kind") == "exclude-command" and e.get("value") == "uv"]
    assert req and req[0]["toolkit"] == "_required"
    assert all(e.get("toolkit") != "_manual" for e in req)
    # Not surfaced as a nudge too (would be double-reported).
    assert "`uv` — REQUIRED on macOS" not in out


@pytest.mark.parametrize("version", ["0.9.8", "0.9.9", "1.5.0"])
def test_required_exclusion_auto_applies_on_every_version_while_no_fix(
        tmp_path, monkeypatch, version):
    # With no known-fixed release (the default), the Seatbelt panic is present in
    # EVERY uv release — so auto-apply must fire on any readable version, NOT just
    # at/below the first known-bad. The 0.9.9 case is the regression guard: the
    # old `installed <= known-bad-floor` ceiling wrongly nudged it instead of
    # auto-applying (0.9.9 <= 0.9.8 is False).
    from project_kit import permissions as perm
    assert perm._UV_KNOWN_FIXED_RELEASE is None      # default: no fix known
    _force_uv(monkeypatch, platform="darwin", version=version)
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "REQUIRED exclusion auto-applied: `uv`" in out
    assert "uv" in _sb(proj)["excludedCommands"]
    assert "`uv` — REQUIRED on macOS" not in out      # not also nudged


def test_required_exclusion_auto_applies_below_fixed_release(tmp_path, monkeypatch):
    # A known-fixed release is set, but the installed uv is still below it → the
    # panic still occurs → auto-apply.
    from project_kit import permissions as perm
    monkeypatch.setattr(perm, "_UV_KNOWN_FIXED_RELEASE", "0.10.0")
    _force_uv(monkeypatch, platform="darwin", version="0.9.9")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "REQUIRED exclusion auto-applied: `uv`" in out
    assert "uv" in _sb(proj)["excludedCommands"]


@pytest.mark.parametrize("version", ["0.10.0", "0.10.1"])
def test_required_exclusion_not_applied_at_or_above_fixed_release(
        tmp_path, monkeypatch, version):
    # At OR above the known-fixed release the box can host the command → no
    # auto-apply (the boundary is exclusive: < fixed required, >= fixed not).
    from project_kit import permissions as perm
    monkeypatch.setattr(perm, "_UV_KNOWN_FIXED_RELEASE", "0.10.0")
    _force_uv(monkeypatch, platform="darwin", version=version)
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "REQUIRED exclusion auto-applied" not in out
    assert "excludedCommands" not in _sb(proj)


def test_required_exclusion_not_applied_on_linux(tmp_path, monkeypatch):
    _force_uv(monkeypatch, platform="linux", version="0.9.8")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "REQUIRED exclusion auto-applied" not in out
    assert "excludedCommands" not in _sb(proj)


def test_required_exclusion_not_applied_on_fixed_uv(tmp_path, monkeypatch):
    # A uv at/above a known-fixed release: the box can host the command again.
    from project_kit import permissions as perm
    monkeypatch.setattr(perm, "_UV_KNOWN_FIXED_RELEASE", "0.10.0")
    _force_uv(monkeypatch, platform="darwin", version="0.10.0")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "REQUIRED exclusion auto-applied" not in out
    assert "excludedCommands" not in _sb(proj)


def test_required_exclusion_not_applied_without_repo_marker(tmp_path, monkeypatch):
    # macOS + old uv on PATH but NO uv.lock / pyproject.toml → not real project use.
    _force_uv(monkeypatch, platform="darwin", version="0.9.8")
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "REQUIRED exclusion auto-applied" not in out
    assert "excludedCommands" not in _sb(proj)


def test_required_exclusion_not_applied_when_uv_unreadable(tmp_path, monkeypatch):
    # Necessity cannot be VERIFIED (uv version unreadable) → do not auto-apply.
    _force_uv(monkeypatch, platform="darwin", version=None)
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "REQUIRED exclusion auto-applied" not in out
    assert "excludedCommands" not in _sb(proj)


def test_required_exclusion_status_attribution(tmp_path, monkeypatch):
    _force_uv(monkeypatch, platform="darwin", version="0.9.8")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    _run(proj, monkeypatch, "setup", "autonomy")
    # An operator-set manual exclusion alongside the auto-applied required one.
    _run(proj, monkeypatch, "sandbox", "exclude", "gh")
    out = _run(proj, monkeypatch, "sandbox")    # no subcommand = status
    # uv attributed as auto-applied (required), gh as operator-set — not vice versa.
    assert "uv — auto-applied (required" in out
    assert "gh — operator-set" in out


def test_required_exclusion_self_heals_when_uv_fixed(tmp_path, monkeypatch):
    # First run on old uv applies the required exclusion.
    _force_uv(monkeypatch, platform="darwin", version="0.9.8")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    # A separate operator manual carve-out that self-heal must NEVER touch.
    _run(proj, monkeypatch, "sandbox", "exclude", "gh")
    _run(proj, monkeypatch, "setup", "autonomy")
    assert "uv" in _sb(proj)["excludedCommands"]
    # uv upgraded past a fixed release → re-run self-heals the required entry.
    from project_kit import permissions as perm
    monkeypatch.setattr(perm, "_UV_KNOWN_FIXED_RELEASE", "0.10.0")
    _force_uv(monkeypatch, platform="darwin", version="0.10.0")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "self-healed: `uv`" in out
    assert "uv" not in _sb(proj).get("excludedCommands", [])
    # The operator's manual gh exclusion is untouched.
    assert "gh" in _sb(proj)["excludedCommands"]
    prov_path = proj / ".pkit" / "permissions" / "project" / "sandbox-provenance.yaml"
    from ruamel.yaml import YAML as _YAML
    doc = _YAML(typ="safe").load(prov_path.open())
    tags = {(e.get("value"), e.get("toolkit")) for e in doc["entries"]
            if e.get("kind") == "exclude-command"}
    assert ("gh", "_manual") in tags
    assert ("uv", "_required") not in tags


def test_required_exclusion_teardown_reverses_it_not_manual(tmp_path, monkeypatch):
    _force_uv(monkeypatch, platform="darwin", version="0.9.8")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    _run(proj, monkeypatch, "sandbox", "exclude", "gh")    # operator manual widening
    _run(proj, monkeypatch, "setup", "autonomy")
    out = _run(proj, monkeypatch, "setup", "autonomy", "down")
    # Teardown reverses the auto-applied required exclusion and reports it.
    assert "auto-applied `uv` exclusion removed" in out
    assert "uv" not in _sb(proj).get("excludedCommands", [])
    # The operator's manual gh exclusion stays (reported as residual widening).
    assert "gh" in _sb(proj)["excludedCommands"]
    assert "WIDENING exclusions remain" in out and "gh" in out


def test_required_exclusion_idempotent_no_double_apply(tmp_path, monkeypatch):
    _force_uv(monkeypatch, platform="darwin", version="0.9.8")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    _run(proj, monkeypatch, "setup", "autonomy")
    out = _run(proj, monkeypatch, "setup", "autonomy")    # re-run
    # Already excluded → no second apply line, single excludedCommands entry.
    assert _sb(proj)["excludedCommands"].count("uv") == 1
    assert "REQUIRED exclusion auto-applied" not in out


def test_optional_widening_stays_nudge_only_under_auto_apply(tmp_path, monkeypatch):
    # Even with the required-exclusion auto-apply live, optional widenings
    # (docker) are NEVER auto-applied — they stay nudge-only.
    _force_uv(monkeypatch, platform="darwin", version="0.9.8")
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    (proj / "Dockerfile").write_text("FROM x")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "uv" in _sb(proj)["excludedCommands"]          # required: applied
    assert "docker" not in _sb(proj)["excludedCommands"]  # optional: NOT applied
    assert "`docker` — optional" in out                   # docker still nudged
    assert "`pkit permissions sandbox exclude docker`" in out


def test_setup_autonomy_seeds_profile_recommendations(tmp_path, monkeypatch):
    # A project profile recommending uv is seeded into config on first setup run.
    proj = _with_adapter(_setup(tmp_path))
    pdir = proj / ".pkit" / "permissions" / "project" / "profiles"
    pdir.mkdir(parents=True)
    (pdir / "autonomous.yaml").write_text(
        "schema_version: 1\n"
        "description: test autonomous\n"
        "posture: lenient\n"
        "recommended_accommodations: [\"[confinement-toolkit:uv]\"]\n"
        "grants: []\n"
    )
    _run(proj, monkeypatch, "setup", "autonomy")
    assert "~/.cache/uv" in _sb(proj)["filesystem"]["allowWrite"]
    cfg = (proj / ".pkit" / "permissions" / "project" / "config.yaml").read_text()
    assert "[confinement-toolkit:uv]" in cfg


# ---- host-environment detection: accommodate --socket + setup (ADR-010, #291) -

import socket as _socketmod  # noqa: E402


@pytest.fixture(autouse=True)
def _hermetic_host_env(monkeypatch):
    """Host-env detection (ADR-010) reads $SSH_AUTH_SOCK and git config; isolate
    both so every test is deterministic regardless of the runner's environment.
    Tests opt in by setting SSH_AUTH_SOCK / running `git init` + local config."""
    import os as _os
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)
    # Neutralize the developer's global/system gitconfig so `git config --get`
    # sees only what a test configures locally (else this machine's real
    # gpg.format=ssh leaks into "no signing" assertions).
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", _os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", _os.devnull)


def _listening_socket() -> tuple[Path, "_socketmod.socket"]:
    """A live AF_UNIX listening socket at a SHORT path; caller closes the server.

    Bound under a short temp dir, not pytest's `tmp_path`: an AF_UNIX socket
    path has a hard OS length limit (~104 bytes on macOS, ~108 on Linux), and
    pytest's deeply-nested `tmp_path` can exceed it — `OSError: AF_UNIX path too
    long` (the path *bytes* passed to bind() are what's measured, so a short
    base avoids it regardless of how deep the test's tmp dir is).
    """
    import tempfile

    d = Path(tempfile.mkdtemp(prefix="pkit-sock-", dir="/tmp"))
    p = d / "agent.sock"
    srv = _socketmod.socket(_socketmod.AF_UNIX, _socketmod.SOCK_STREAM)
    srv.bind(str(p))
    srv.listen(1)
    return p, srv


def test_accommodate_socket_writes_per_machine_not_committed(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    sock = str(tmp_path / "my.sock")
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "--socket", sock, "--name", "mything")
    assert "socket accommodated (mything)" in out and "NOT committed" in out
    assert sock in _sb(proj)["network"]["allowUnixSockets"]
    # Never written to committed config.
    cfgp = proj / ".pkit" / "permissions" / "project" / "config.yaml"
    if cfgp.is_file():
        assert "mything" not in cfgp.read_text() and sock not in cfgp.read_text()


def test_accommodate_socket_recompute_replace_no_accretion(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    s1, s2 = str(tmp_path / "a.sock"), str(tmp_path / "b.sock")
    _run(proj, monkeypatch, "sandbox", "accommodate", "--socket", s1, "--name", "ssh-agent")
    _run(proj, monkeypatch, "sandbox", "accommodate", "--socket", s2, "--name", "ssh-agent")
    socks = _sb(proj)["network"]["allowUnixSockets"]
    assert s2 in socks and s1 not in socks   # replaced, not accreted


def test_accommodate_socket_remove(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    sock = str(tmp_path / "x.sock")
    _run(proj, monkeypatch, "sandbox", "accommodate", "--socket", sock, "--name", "x")
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "--name", "x", "--remove")
    assert "removed socket allowance 'x'" in out
    assert sock not in _sb(proj).get("network", {}).get("allowUnixSockets", [])


def test_accommodate_socket_under_floor_warns_but_applies(tmp_path, monkeypatch):
    # --socket is an explicit operator gesture: in-floor warns but proceeds.
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "--socket", "~/.ssh/agent.sock", "--name", "x")
    assert "under the credential denyRead floor" in out


def test_setup_autonomy_auto_resolves_live_ssh_auth_sock(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    sock_path, srv = _listening_socket()
    try:
        monkeypatch.setenv("SSH_AUTH_SOCK", str(sock_path))
        out = _run(proj, monkeypatch, "setup", "autonomy")
    finally:
        srv.close()
    assert "ssh-agent socket" in out and "accommodations:" in out
    assert str(sock_path) in _sb(proj)["network"]["allowUnixSockets"]


def test_setup_autonomy_dead_ssh_sock_nudges_not_applies(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    monkeypatch.setenv("SSH_AUTH_SOCK", str(tmp_path / "nonexistent.sock"))
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "isn't answering" in out
    assert "allowUnixSockets" not in _sb(proj).get("network", {})


def test_setup_autonomy_in_floor_ssh_sock_nudges_not_applies(tmp_path, monkeypatch):
    # A socket under the credential floor is never silently auto-applied (rule 7).
    proj = _with_adapter(_setup(tmp_path))
    monkeypatch.setenv("SSH_AUTH_SOCK", str(Path("~/.ssh/agent.sock").expanduser()))
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "under the credential floor" in out and "accommodate --socket" in out
    assert "allowUnixSockets" not in _sb(proj).get("network", {})


def test_setup_autonomy_no_ssh_sock_is_quiet(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))   # autouse fixture deleted SSH_AUTH_SOCK
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "ssh-agent socket" not in out


def test_ssh_agent_toolkit_dropped(tmp_path, monkeypatch):
    out = _run(_setup(tmp_path), monkeypatch, "sandbox", "toolkit", "list")
    assert "ssh-agent" not in out


# ---- setup autonomy NEXT block: gh + commit-signing detection (#293) ---------

def _git_init_signing(proj: Path, program: str) -> None:
    import subprocess as _sp
    _sp.run(["git", "init", "-q"], cwd=proj, check=True)
    _sp.run(["git", "config", "gpg.format", "ssh"], cwd=proj, check=True)
    _sp.run(["git", "config", "gpg.ssh.program", program], cwd=proj, check=True)


def test_setup_next_block_offers_signing_for_1password(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _git_init_signing(proj, "/Applications/1Password.app/Contents/MacOS/op-ssh-sign")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "Next — run these yourself" in out
    assert "1Password" in out and "narrowing — box stays confined" in out
    assert "accommodate --socket ~/.1password/agent.sock --name signing" in out
    # nudge only — no socket auto-applied for signing
    assert "~/.1password/agent.sock" not in _sb(proj).get("network", {}).get("allowUnixSockets", [])


def test_setup_signing_nudge_suppressed_once_accommodated(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    _git_init_signing(proj, "op-ssh-sign")
    # Accommodate the 1Password socket → the signing nudge must disappear.
    sock = str(Path("~/.1password/agent.sock").expanduser())
    _run(proj, monkeypatch, "sandbox", "accommodate", "--socket", sock, "--name", "signing")
    # accommodate stored the *expanded* path; the detector compares expanded paths.
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "commit-signing" not in out


def test_setup_no_signing_config_no_signing_nudge(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))  # no git signing configured
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "commit-signing" not in out


def test_gh_detected_via_repo_marker(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    (proj / ".github").mkdir()
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "`gh` — optional" in out and "sandbox exclude gh" in out
    assert "gh" not in _sb(proj).get("excludedCommands", [])   # nudge only


def test_gh_detected_via_path(tmp_path, monkeypatch):
    # No repo marker; gh "on PATH" via a stub bin dir prepended to PATH.
    proj = _with_adapter(_setup(tmp_path))
    bindir = tmp_path / "bin"
    bindir.mkdir()
    stub = bindir / "gh"
    stub.write_text("#!/bin/sh\n")
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}:{__import__('os').environ['PATH']}")
    out = _run(proj, monkeypatch, "setup", "autonomy")
    assert "`gh` — optional" in out and "sandbox exclude gh" in out


# ---- setup-autonomy NEXT block: wrapping + required-vs-optional copy (#247) ---
#   (a) a long widening desc hang-indents continuation lines under the 4-space
#       label (6 spaces), never flush to column 0.
#   (b) the macOS-mandatory uv/pkit exclusion renders REQUIRED copy; an optional
#       one (gh) renders "optional" copy. Distinction computed at runtime.
#   (c) the `sandbox exclude` command line is present and unbroken (own line, not
#       mid-token wrapped).

def _next_steps(widening, *, platform, width, host=None):
    """Render _setup_next_steps with a forced platform + wrap width, no signing
    (a nonexistent root → no git → empty signing). Returns the line list."""
    import unittest.mock as _mock

    from project_kit import cli_render
    from project_kit import permissions as perm

    saved = cli_render._wrap_width
    cli_render.set_wrap_width(width)
    try:
        with _mock.patch("sys.platform", platform):
            return perm._setup_next_steps(Path("/nonexistent-xyz"), widening, host or [])
    finally:
        cli_render.set_wrap_width(saved)


def test_next_step_long_desc_hangs_at_six_spaces_not_column_zero():
    # Narrow width forces the optional copy to wrap; continuations must hang at
    # indent(4) + hang(2) = 6 spaces, never at column 0 (the bug being fixed).
    out = _next_steps([("gh", "gh")], platform="linux", width=50)
    # the label anchors line 1 at the 4-space margin
    label_lines = [ln for ln in out if ln.startswith("    `gh` — optional:")]
    assert label_lines, "expected the label at the 4-space margin"
    # body continuations hang at exactly 6 spaces (not 8 = the command line)
    conts = [ln for ln in out
             if ln.startswith("      ") and not ln.startswith("        ")]
    assert conts, "expected a hung continuation line at 6 spaces"
    for ln in conts:
        assert not ln.startswith("       ")        # exactly 6, not 7+
        assert ln[6] != " "                         # content begins at col 6
    # nothing in the block wrapped flush to column 0
    block = out[2:]  # skip the leading blank + heading
    assert not any(ln and not ln.startswith(" ") for ln in block)


def test_next_step_macos_uv_required_copy():
    out = _next_steps([("uv", "uv")], platform="darwin", width=0)
    text = "\n".join(out)
    assert "`uv` — REQUIRED on macOS" in text
    assert "fixed Seatbelt panic" in text and "ADR-014" in text
    assert "Still gated by the permission hook." in text
    # the exclude command is present, on its own line, unbroken
    assert "        `pkit permissions sandbox exclude uv`" in out


def test_next_step_pkit_also_required_on_macos():
    # The mandatory match keys on uv OR pkit, by tool name or cmd value.
    out = _next_steps([("pkit", "pkit")], platform="darwin", width=0)
    assert "`pkit` — REQUIRED on macOS" in "\n".join(out)


def test_next_step_gh_optional_copy_on_macos():
    # gh is NOT uv/pkit → optional even on macOS.
    out = _next_steps([("gh", "gh")], platform="darwin", width=0)
    text = "\n".join(out)
    assert "`gh` — optional" in text and "REQUIRED" not in text
    assert "        `pkit permissions sandbox exclude gh`" in out


def test_next_step_uv_optional_off_macos():
    # Off macOS, even uv is optional (the Seatbelt panic is macOS-specific).
    out = _next_steps([("uv", "uv")], platform="linux", width=0)
    text = "\n".join(out)
    assert "`uv` — optional" in text and "REQUIRED" not in text


def test_next_step_exclude_command_line_unbroken_under_narrow_width():
    # Even at a punishing width the command token overflows (copy-pasteable),
    # never breaks mid-token.
    out = _next_steps([("gh", "gh")], platform="linux", width=20)
    assert "        `pkit permissions sandbox exclude gh`" in out


# ---- run-once SSH stability tip (#299) ---------------------------------------

def test_stability_tip_shown_for_volatile_socket_with_1password(tmp_path, monkeypatch):
    from project_kit import permissions as perm
    home = tmp_path / "home"
    (home / ".1password").mkdir(parents=True)
    (home / ".1password" / "agent.sock").touch()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/var/run/com.apple.launchd.ABC123/Listeners")
    tip = "\n".join(perm._setup_stability_tip(tmp_path))
    assert "Optional — make SSH survive reboots" in tip
    assert "export SSH_AUTH_SOCK=~/.1password/agent.sock" in tip
    assert "~/.zshrc" in tip                 # shell-aware
    assert "────" not in tip and "── " not in tip   # no rules (convention)


def test_stability_tip_absent_when_socket_already_stable(tmp_path, monkeypatch):
    from project_kit import permissions as perm
    home = tmp_path / "home"
    (home / ".1password").mkdir(parents=True)
    (home / ".1password" / "agent.sock").touch()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SSH_AUTH_SOCK", str(tmp_path / "stable.sock"))  # non-volatile path
    assert perm._setup_stability_tip(tmp_path) == []   # self-vanishing


def test_stability_tip_absent_without_stable_agent(tmp_path, monkeypatch):
    from project_kit import permissions as perm
    home = tmp_path / "home"
    home.mkdir()                              # no ~/.1password/agent.sock
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SSH_AUTH_SOCK", "/var/run/com.apple.launchd.XYZ/Listeners")
    assert perm._setup_stability_tip(tmp_path) == []   # nothing to recommend


def test_stability_tip_absent_when_no_ssh_auth_sock(tmp_path, monkeypatch):
    from project_kit import permissions as perm
    assert perm._setup_stability_tip(tmp_path) == []   # autouse fixture cleared it


# --- styling layer (ADR-011): the procedural step-logs are styled but the
# styling is never load-bearing (Bucket A: sandbox status / probe / toolkit
# list / setup-list — the always-hand-built surfaces). -----------------------

@pytest.mark.parametrize("args", [
    ["sandbox"],            # no subcommand → status
    ["probe"],
    ["sandbox", "toolkit", "list"],
    ["setup"],              # no goal → setup-list
    ["explain"],
    ["catalog"],
    ["overview"],
    ["diff"],
])
def test_procedural_step_logs_styling_is_never_load_bearing(tmp_path, monkeypatch, args):
    """Each procedural step-log emits SGR under --color always, yet strips back
    byte-for-byte to its --color never form (ADR-011 §3): structure reads with
    zero styling."""
    from project_kit import cli_render

    proj = _setup(tmp_path)
    monkeypatch.chdir(proj)
    always = CliRunner().invoke(main, ["--color", "always", "permissions", *args]).output
    never = CliRunner().invoke(main, ["--color", "never", "permissions", *args]).output

    assert "\033[" in always, f"{args} should emit SGR under --color always"
    assert cli_render.strip_ansi(always) == never


# ---- ADR-002 amendment: enforcement-runtime self-check + ADR-014 zero-dep ---
# Tests for:
#   (a) `enable` and `sandbox enable` run the self-check and are loud on a dead
#       hook runtime.
#   (b) `sandbox enable` sets failIfUnavailable: true (already existing test
#       test_sandbox_enable_writes_fail_closed_block covers this; these add the
#       diagnostic self-check angle).
#   (c) `overview` surfaces enforcement-runtime fault and confinement write probe.
#   (d) `sandbox status` surfaces actual-confinement write probe.
#   (e) Confinement write probe: reports "denied" when OS blocks, "allowed" when
#       not confining.


def _with_adapter_and_hook(proj: Path) -> Path:
    """Like _with_adapter but also copies the hook script so _hook_runtime_check
    can find it and run it (needed for tests that want a HEALTHY runtime)."""
    _with_adapter(proj)
    hook_dst = proj / ".pkit" / "adapters" / "claude-code" / "permission-hook.py"
    hook_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        REPO / ".pkit" / "adapters" / "claude-code" / "permission-hook.py",
        hook_dst,
    )
    # Also copy decide.py so the hook can import it in the probe.
    (proj / ".pkit" / "permissions").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        REPO / ".pkit" / "permissions" / "decide.py",
        proj / ".pkit" / "permissions" / "decide.py",
    )
    return proj


def test_enable_warns_loudly_when_hook_runtime_dead(tmp_path, monkeypatch):
    """When the hook script is missing (dead runtime), `enable` warns loudly
    rather than silently proceeding (ADR-002 amendment)."""
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    # Patch _hook_runtime_check to simulate a dead runtime.
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (False, "python3 not found"))
    out = _run(proj, monkeypatch, "enable")
    assert "live enforcement enabled" in out  # still registers (structural change)
    assert "WARNING" in out
    assert "CANNOT START" in out
    assert "fail-open" in out
    assert "python3 not found" in out


def test_enable_no_warning_when_hook_runtime_healthy(tmp_path, monkeypatch):
    """When the hook runtime is healthy, `enable` outputs no WARNING (clean path)."""
    from project_kit import permissions as perm
    proj = _with_adapter_and_hook(_setup(tmp_path))
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (True, "hook started"))
    out = _run(proj, monkeypatch, "enable")
    assert "live enforcement enabled" in out
    assert "WARNING" not in out
    assert "CANNOT START" not in out


def test_sandbox_enable_warns_loudly_when_hook_runtime_dead(tmp_path, monkeypatch):
    """When the hook runtime is dead, `sandbox enable` warns loudly (ADR-002 amendment)."""
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (False, "decide.py missing"))
    # Also stub out the confinement probe so it doesn't add noise.
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "error")
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "sandbox enabled" in out
    assert "WARNING" in out
    assert "CANNOT START" in out
    assert "decide.py missing" in out


def test_sandbox_enable_sets_failIfUnavailable_true(tmp_path, monkeypatch):
    """sandbox enable always sets failIfUnavailable: true (ADR-004 / ADR-014 §6).
    Regression test: fail-closed invariant must hold post #21 changes."""
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (True, "ok"))
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "denied")
    _run(proj, monkeypatch, "sandbox", "enable")
    assert _settings(proj)["sandbox"]["failIfUnavailable"] is True


def test_sandbox_enable_confinement_probe_denied_is_quiet(tmp_path, monkeypatch):
    """When the confinement probe is DENIED (box is confining), sandbox enable
    reports it cleanly — no warning."""
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (True, "ok"))
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "denied")
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "confinement verified" in out
    assert "NOT actually confining" not in out


def test_sandbox_enable_confinement_probe_allowed_warns_loudly(tmp_path, monkeypatch):
    """When the confinement probe is ALLOWED (box not confining), sandbox enable
    warns loudly about 'configured but NOT actually confining' (ADR-014 §6)."""
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (True, "ok"))
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "allowed")
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "WARNING" in out
    assert "NOT actually confining" in out
    assert "out-of-workspace" in out


def test_overview_surfaces_enforcement_runtime_fault(tmp_path, monkeypatch):
    """When enforcement is ON but the hook can't start, `overview` surfaces it
    as a loud, diagnosed fault (ADR-002 amendment)."""
    from project_kit import permissions as perm
    proj = _setup(tmp_path)
    # Register the hook in settings to make enforcement appear ON.
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "*", "hooks": [{"type": "command", "command": HOOK_COMMAND}]}
    ]}}))
    # Simulate a dead runtime.
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (False, "python3 not found"))
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "error")
    out = _run(proj, monkeypatch, "overview")
    assert "ENFORCEMENT-RUNTIME FAULT" in out
    assert "CANNOT START" in out
    assert "python3 not found" in out
    # Must name the healthy-runtime remediation.
    assert "pkit permissions enable" in out or "Re-run" in out


def test_overview_no_fault_when_runtime_healthy(tmp_path, monkeypatch):
    """When enforcement is ON and the hook runtime is healthy, `overview` reports
    clean ON status with no fault (ADR-002 amendment)."""
    from project_kit import permissions as perm
    proj = _with_adapter_and_hook(_setup(tmp_path))
    # Register the hook in settings.
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "*", "hooks": [{"type": "command", "command": HOOK_COMMAND}]}
    ]}}))
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (True, "ok"))
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "error")
    out = _run(proj, monkeypatch, "overview")
    assert "Live enforcement: ON" in out
    assert "ENFORCEMENT-RUNTIME FAULT" not in out
    assert "CANNOT START" not in out


def test_overview_sandbox_on_surfaces_confinement_probe(tmp_path, monkeypatch):
    """When sandbox is ON, `overview` runs the confinement write probe and reports
    its outcome — either verified or NOT-CONFINING (ADR-002 amendment / ADR-014 §6)."""
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (False, "no hook"))
    # First: probe denied → confinement verified.
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "denied")
    _run(proj, monkeypatch, "sandbox", "enable")
    out = _run(proj, monkeypatch, "overview")
    # Reset probe to denied to check the verified branch.
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "denied")
    out = _run(proj, monkeypatch, "overview")
    assert "confinement verified" in out or "write outside workspace DENIED" in out

    # Second: probe allowed → NOT confining warning.
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "allowed")
    out = _run(proj, monkeypatch, "overview")
    assert "NOT actually confining" in out or "WARNING" in out


def test_sandbox_status_surfaces_confinement_write_probe(tmp_path, monkeypatch):
    """sandbox status reports actual-confinement write probe: VERIFIED or NOT CONFINING
    (ADR-002 amendment / ADR-014 §6)."""
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    monkeypatch.setattr(perm, "_hook_runtime_check", lambda _r: (True, "ok"))

    # Enable sandbox first so status shows ON.
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "denied")
    _run(proj, monkeypatch, "sandbox", "enable")

    # Status with probe denied → VERIFIED.
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "denied")
    out = _run(proj, monkeypatch, "sandbox")
    assert "VERIFIED" in out or "DENIED" in out

    # Status with probe allowed → NOT CONFINING warning.
    monkeypatch.setattr(perm, "_confinement_write_probe", lambda: "allowed")
    out = _run(proj, monkeypatch, "sandbox")
    assert "NOT CONFINING" in out or "NOT actually confining" in out or "ALLOWED" in out


def test_confinement_write_probe_allowed_when_not_sandboxed():
    """The confinement write probe returns 'allowed' when not in a sandbox
    (plain terminal). This is the expected state in tests."""
    from project_kit import permissions as perm
    result = perm._confinement_write_probe()
    # From a plain test process, the write outside workspace MUST succeed.
    # If somehow it doesn't (very rare), 'error' is also acceptable.
    assert result in ("allowed", "error"), (
        f"Expected 'allowed' (not sandboxed) or 'error', got {result!r}"
    )


def test_confinement_write_probe_denied_simulation(tmp_path, monkeypatch):
    """Simulate the 'denied' case by making the /tmp write raise PermissionError."""
    from project_kit import permissions as perm
    import pathlib

    original_write_text = pathlib.Path.write_text

    def _raise_perm(self, *args, **kwargs):
        name = str(self)
        if "pkit-confinement-probe-" in name:
            raise PermissionError("simulated sandbox denial")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", _raise_perm)
    result = perm._confinement_write_probe()
    assert result == "denied"


# ---- allow-host network egress (ADR-015, issue #24) --------------------------
#
# Acceptance criteria:
#   (a) allow-host kind added to schema (additive; no schema_version bump).
#   (b) Named/bounded hosts auto-apply on capability install via single writer.
#   (c) Every applied allow-host MANDATORILY surfaced in sandbox status +
#       permissions overview with source + verbatim "session-wide egress to X;
#       not a security boundary" gloss.
#   (d) network: any / * treated as widening — never auto-applied.
#   (e) Adopter-set values preserved; idempotent.
#   (f) Regression: status surfaces declared egress; override preserved.


def _toolkit_yaml(name: str, host: str, effect: str = "narrowing") -> str:
    """Build a minimal confinement-toolkit YAML with one allow-host allowance."""
    return (
        "schema_version: 1\n"
        "toolkits:\n"
        f"  {name}:\n"
        f"    description: Test toolkit for {name}\n"
        f"    detect:\n"
        f"      - \"{name}.lock\"\n"
        f"    allowances:\n"
        f"      - kind: allow-host\n"
        f"        effect: {effect}\n"
        f"        value: \"{host}\"\n"
        f"        note: test note for {host}\n"
    )


def _project_toolkit(proj: Path, yaml_text: str) -> None:
    """Write a project-level confinement-toolkit override."""
    d = proj / ".pkit" / "permissions" / "project"
    d.mkdir(parents=True, exist_ok=True)
    (d / "confinement-toolkit.yaml").write_text(yaml_text)


def test_allow_host_schema_accepts_named_host(tmp_path, monkeypatch):
    """allow-host kind is accepted by schema validation — additive, no schema_version bump."""
    # The shipped confinement-toolkit.yaml now includes github-api with allow-host.
    out = _run(_setup(tmp_path), monkeypatch, "sandbox", "toolkit", "list")
    assert "github-api" in out
    assert "narrowing-but-reported" in out   # effect mark for allow-host narrowing


def test_allow_host_auto_applied_on_accommodate(tmp_path, monkeypatch):
    """Named bounded host auto-applies through accommodate — single provenance writer."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "my-api")
    assert "narrowing applied" in out
    sb = _sb(proj)
    assert "api.example.com" in sb["network"]["allowedHosts"]


def test_allow_host_auto_applied_provenance_tagged(tmp_path, monkeypatch):
    """allow-host entries are provenance-tagged to the toolkit (ADR-008 rule 2)."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    _run(proj, monkeypatch, "sandbox", "accommodate", "my-api")
    prov_path = proj / ".pkit" / "permissions" / "project" / "sandbox-provenance.yaml"
    from ruamel.yaml import YAML as _YAML
    _yaml = _YAML(typ="safe")
    with prov_path.open() as fh:
        doc = _yaml.load(fh)
    entries = doc.get("entries", [])
    host_entries = [e for e in entries if e.get("kind") == "allow-host"]
    assert len(host_entries) == 1
    assert host_entries[0]["value"] == "api.example.com"
    assert host_entries[0]["toolkit"] == "my-api"


def test_allow_host_idempotent(tmp_path, monkeypatch):
    """Re-applying the same allow-host toolkit is a no-op (set-union write)."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    _run(proj, monkeypatch, "sandbox", "accommodate", "my-api")
    before = _settings(proj)
    _run(proj, monkeypatch, "sandbox", "accommodate", "my-api")
    after = _settings(proj)
    assert after == before
    assert after["sandbox"]["network"]["allowedHosts"].count("api.example.com") == 1


def test_allow_host_operator_value_preserved(tmp_path, monkeypatch):
    """Operator-set allowedHosts entries survive pkit operations (no silent deletion)."""
    import json as _json
    proj = _with_adapter(_setup(tmp_path, settings=_json.dumps({
        "sandbox": {"network": {"allowedHosts": ["my.operator.host"]}}
    })))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    _run(proj, monkeypatch, "sandbox", "accommodate", "my-api")
    hosts = _sb(proj)["network"]["allowedHosts"]
    assert "my.operator.host" in hosts        # operator entry preserved
    assert "api.example.com" in hosts         # pkit entry added


def test_allow_host_mandatory_reporting_in_sandbox_status(tmp_path, monkeypatch):
    """Applied allow-host is mandatorily surfaced in sandbox status with verbatim gloss."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    _run(proj, monkeypatch, "sandbox", "enable")
    _run(proj, monkeypatch, "sandbox", "accommodate", "my-api")
    out = _run(proj, monkeypatch, "sandbox")
    assert "session-wide egress to api.example.com; not a security boundary" in out
    assert "my-api" in out          # source toolkit named


def test_allow_host_mandatory_reporting_in_permissions_overview(tmp_path, monkeypatch):
    """Applied allow-host is mandatorily surfaced in permissions overview."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    _run(proj, monkeypatch, "sandbox", "accommodate", "my-api")
    out = _run(proj, monkeypatch, "overview")
    assert "session-wide egress to api.example.com; not a security boundary" in out
    assert "my-api" in out


def test_allow_host_gloss_in_toolkit_show(tmp_path, monkeypatch):
    """toolkit show surfaces the egress honesty gloss for allow-host allowances."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    out = _run(proj, monkeypatch, "sandbox", "toolkit", "show", "my-api")
    assert "allow-host" in out and "narrowing" in out
    assert "session-wide egress to api.example.com; not a security boundary" in out
    assert "narrowing-but-reported" in out or "NARROWING-BUT-REPORTED" in out


def test_allow_host_not_reported_when_not_applied(tmp_path, monkeypatch):
    """Egress section is absent from status / overview when no allow-host is applied."""
    proj = _with_adapter(_setup(tmp_path))
    _run(proj, monkeypatch, "sandbox", "enable")
    out = _run(proj, monkeypatch, "sandbox")
    assert "session-wide egress" not in out
    out = _run(proj, monkeypatch, "overview")
    assert "session-wide egress" not in out


def test_allow_host_any_is_widening_not_auto_applied(tmp_path, monkeypatch):
    """allow-host with value `*` is widening — never auto-applied via accommodate."""
    proj = _with_adapter(_setup(tmp_path))
    # A toolkit with effect: widening (as required for any/* per ADR-015 fork 6).
    # The accommodate command refuses to apply widening allowances.
    _project_toolkit(proj, _toolkit_yaml("open-egress", "*", effect="widening"))
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "open-egress")
    assert "WIDENING" in out and "sandbox exclude" in out
    # allowedHosts must NOT contain `*`
    assert "*" not in _sb(proj).get("network", {}).get("allowedHosts", [])


def test_allow_host_any_guard_in_apply_allowances(tmp_path, monkeypatch):
    """_apply_allowances refuses to write allow-host `*` even if called directly."""
    from project_kit import permissions as perm
    proj = _with_adapter(_setup(tmp_path))
    import pytest as _pytest
    with _pytest.raises(perm.PermissionsError, match="unambiguously widening"):
        perm._apply_allowances(
            proj,
            [{"kind": "allow-host", "value": "*", "effect": "narrowing"}],
            "bad-toolkit",
        )
    # `any` keyword also blocked
    with _pytest.raises(perm.PermissionsError, match="unambiguously widening"):
        perm._apply_allowances(
            proj,
            [{"kind": "allow-host", "value": "any", "effect": "narrowing"}],
            "bad-toolkit",
        )
    # No allowedHosts entry written
    assert "allowedHosts" not in _sb(proj).get("network", {})


def test_allow_host_auto_accommodate_on_sandbox_enable(tmp_path, monkeypatch):
    """Named allow-host toolkits are auto-applied on sandbox enable when detected."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    (proj / "my-api.lock").write_text("")   # signal detect glob
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "auto-accommodated" in out and "my-api" in out
    assert "api.example.com" in _sb(proj)["network"]["allowedHosts"]
    # Mandatory egress gloss must appear in sandbox enable output too.
    assert "session-wide egress to api.example.com; not a security boundary" in out


def test_allow_host_not_auto_accommodated_when_any(tmp_path, monkeypatch):
    """A toolkit with widening allow-host `*` is never auto-accommodated on sandbox enable."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("open-egress", "*", effect="widening"))
    (proj / "open-egress.lock").write_text("")   # signal detect glob
    out = _run(proj, monkeypatch, "sandbox", "enable")
    assert "open-egress" not in out or "auto-accommodated" not in out
    assert "*" not in _sb(proj).get("network", {}).get("allowedHosts", [])


def test_allow_host_remove_cleans_provenance(tmp_path, monkeypatch):
    """Removing a toolkit with allow-host removes its host from allowedHosts (pkit-authored only)."""
    proj = _with_adapter(_setup(tmp_path))
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    _run(proj, monkeypatch, "sandbox", "accommodate", "my-api")
    assert "api.example.com" in _sb(proj)["network"]["allowedHosts"]
    _run(proj, monkeypatch, "sandbox", "accommodate", "my-api", "--remove")
    assert "api.example.com" not in _sb(proj).get("network", {}).get("allowedHosts", [])


def test_allow_host_toolkit_list_shows_narrowing_but_reported(tmp_path, monkeypatch):
    """Toolkit list marks allow-host narrowing toolkits as narrowing-but-reported."""
    proj = _setup(tmp_path)
    _project_toolkit(proj, _toolkit_yaml("my-api", "api.example.com"))
    out = _run(proj, monkeypatch, "sandbox", "toolkit", "list")
    assert "my-api" in out
    assert "narrowing-but-reported" in out


def test_allow_host_shipped_github_api_toolkit_present(tmp_path, monkeypatch):
    """The shipped github-api toolkit with allow-host is present in the toolkit list."""
    proj = _setup(tmp_path)
    out = _run(proj, monkeypatch, "sandbox", "toolkit", "list")
    assert "github-api" in out
    out = _run(proj, monkeypatch, "sandbox", "toolkit", "show", "github-api")
    assert "api.github.com" in out
    assert "allow-host" in out and "narrowing" in out


# ---- anthropic-api confinement toolkit (issue #79) -------------------------
#
# Faithful sibling of github-api: allow-host → api.anthropic.com, narrowing-
# but-reported, explicit-accommodate only (no detect glob).


def test_allow_host_shipped_anthropic_api_toolkit_present(tmp_path, monkeypatch):
    """The shipped anthropic-api toolkit is present in the toolkit list as narrowing-but-reported."""
    proj = _setup(tmp_path)
    out = _run(proj, monkeypatch, "sandbox", "toolkit", "list")
    assert "anthropic-api" in out
    assert "narrowing-but-reported" in out


def test_allow_host_shipped_anthropic_api_toolkit_show(tmp_path, monkeypatch):
    """toolkit show renders the allowance + egress honesty gloss for anthropic-api."""
    proj = _setup(tmp_path)
    out = _run(proj, monkeypatch, "sandbox", "toolkit", "show", "anthropic-api")
    assert "api.anthropic.com" in out
    assert "allow-host" in out and "narrowing" in out
    assert "session-wide egress to api.anthropic.com; not a security boundary" in out
    assert "narrowing-but-reported" in out or "NARROWING-BUT-REPORTED" in out


def test_allow_host_anthropic_api_accommodate_applies_host(tmp_path, monkeypatch):
    """accommodate anthropic-api writes api.anthropic.com to allowedHosts (single provenance writer)."""
    proj = _with_adapter(_setup(tmp_path))
    out = _run(proj, monkeypatch, "sandbox", "accommodate", "anthropic-api")
    assert "narrowing applied" in out
    sb = _sb(proj)
    assert "api.anthropic.com" in sb["network"]["allowedHosts"]


def test_allow_host_anthropic_api_not_auto_detected(tmp_path, monkeypatch):
    """anthropic-api has no detect glob — sandbox enable does NOT auto-accommodate it."""
    proj = _with_adapter(_setup(tmp_path))
    # Ensure no detect-glob file triggers it inadvertently.
    out = _run(proj, monkeypatch, "sandbox", "enable")
    sb = _sb(proj)
    assert "api.anthropic.com" not in sb.get("network", {}).get("allowedHosts", [])
    # anthropic-api must not appear in the auto-accommodated notice.
    assert "anthropic-api" not in out or "auto-accommodated" not in out


# ---- capability-contributed grant attribution (ADR-016) ---------------------
#
# pkit permissions overview / explain MUST surface which capability contributed
# a deny, so the operator can always see why an agent is denied a privilege.
# ADR-016 narrowing-but-reported: auto-applied like narrowing, but visible.

def _setup_with_capability(
    tmp_path: Path,
    *,
    cap_name: str = "project-management",
    cap_grants: str,
    manifest_yaml: str,
    config: str | None = None,
) -> Path:
    """Extend _setup with a manifest + capability fragment."""
    proj = _setup(tmp_path, config=config)
    # Write manifest.
    (proj / ".pkit" / "manifest.yaml").write_text(manifest_yaml)
    # Write capability fragment.
    cap_perm_dir = proj / ".pkit" / "capabilities" / cap_name / "permissions"
    cap_perm_dir.mkdir(parents=True)
    (cap_perm_dir / "grants.yaml").write_text(cap_grants)
    return proj


_PM_MANIFEST = (
    "schema_version: 1\n"
    "backbone_version: 1.0.0\n"
    "components:\n"
    "  - kind: capability\n"
    "    name: project-management\n"
    "    manifest: .pkit/capabilities/project-management/manifest.yaml\n"
)
_PM_CAP_GRANTS = (
    "schema_version: 1\n"
    "grants:\n"
    "  - subject: agent:project-manager\n"
    "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
    "    effect: deny\n"
)


def test_explain_shows_capability_attribution(tmp_path, monkeypatch):
    """pkit permissions explain shows 'contributed by capability: <name>' for capability denies."""
    proj = _setup_with_capability(
        tmp_path,
        cap_grants=_PM_CAP_GRANTS,
        manifest_yaml=_PM_MANIFEST,
    )
    out = _run(proj, monkeypatch, "explain")
    assert "contributed by capability: project-management" in out, (
        f"explain must attribute the capability deny; got:\n{out}"
    )
    assert "issue-tracker-write" in out


def test_explain_agent_filter_shows_capability_attribution(tmp_path, monkeypatch):
    """pkit permissions explain <agent> shows capability attribution for that agent's denies."""
    proj = _setup_with_capability(
        tmp_path,
        cap_grants=_PM_CAP_GRANTS,
        manifest_yaml=_PM_MANIFEST,
    )
    out = _run(proj, monkeypatch, "explain", "project-manager")
    assert "contributed by capability: project-management" in out, (
        f"explain <agent> must attribute the capability deny; got:\n{out}"
    )


def test_overview_shows_capability_contributed_deny_section(tmp_path, monkeypatch):
    """pkit permissions overview shows the CAPABILITY-CONTRIBUTED DENIES section."""
    proj = _setup_with_capability(
        tmp_path,
        cap_grants=_PM_CAP_GRANTS,
        manifest_yaml=_PM_MANIFEST,
    )
    out = _run(proj, monkeypatch, "overview")
    assert "CAPABILITY-CONTRIBUTED DENIES" in out, (
        f"overview must show the capability-contributed denies section; got:\n{out}"
    )
    assert "agent:project-manager" in out
    assert "DENY issue-tracker-write" in out
    assert "contributed by capability: project-management" in out


def test_overview_enabler_row_shows_capability_denied_subjects(tmp_path, monkeypatch):
    """overview's ENABLERS section annotates the deny with the source capability."""
    proj = _setup_with_capability(
        tmp_path,
        cap_grants=_PM_CAP_GRANTS,
        manifest_yaml=_PM_MANIFEST,
    )
    out = _run(proj, monkeypatch, "overview")
    # The issue-tracker-write row in ENABLERS should show the denied subject + capability.
    assert "agent:project-manager (capability: project-management)" in out, (
        f"overview ENABLERS row must name the denied subject with capability source; got:\n{out}"
    )


# ---- diagnose (PRJ-006) CLI wiring ------------------------------------------

def test_diagnose_on_status_off_round_trip(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    assert "OFF" in _run(proj, monkeypatch, "diagnose")  # no subcommand = status
    assert "armed" in _run(proj, monkeypatch, "diagnose", "on")
    assert "ARMED" in _run(proj, monkeypatch, "diagnose", "status")
    assert "disarmed" in _run(proj, monkeypatch, "diagnose", "off")
    assert "OFF" in _run(proj, monkeypatch, "diagnose", "status")


def test_diagnose_report_empty(tmp_path, monkeypatch):
    proj = _setup(tmp_path)
    assert "nothing captured" in _run(proj, monkeypatch, "diagnose", "report")
