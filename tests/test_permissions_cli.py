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
    assert "docker: runs UNCONFINED" in out
    assert "`pkit permissions sandbox exclude docker`" in out   # backtick-wrapped, own line
    assert "────" not in out          # no drawn rules (convention)
    assert "── NEXT" not in out        # no divider header either
    assert "excludedCommands" not in _sb(proj)


def test_setup_autonomy_down_reports_accommodation_residual(tmp_path, monkeypatch):
    proj = _with_adapter(_setup(tmp_path))
    (proj / "uv.lock").write_text("")
    _run(proj, monkeypatch, "setup", "autonomy")
    _run(proj, monkeypatch, "sandbox", "exclude", "docker")     # a manual widening
    out = _run(proj, monkeypatch, "setup", "autonomy", "down")
    assert "narrowing accommodations remain" in out and "uv" in out
    assert "WIDENING exclusions remain" in out and "docker" in out


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
    assert "gh: runs UNCONFINED" in out and "sandbox exclude gh" in out
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
    assert "gh: runs UNCONFINED" in out and "sandbox exclude gh" in out


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
