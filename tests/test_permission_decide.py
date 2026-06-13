"""Conformance fixtures for the permission decision core (.pkit/permissions/decide.py).

Loads the REAL baseline privilege catalog (.pkit/schemas/privilege-catalog.yaml)
and runs the truth table the design (COR-028 Q1-Q4) and ADR-002's same-code
invariant require. The hook and the `pkit permissions` CLI both import this
module, so these fixtures are the shared proof they decide identically.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DECIDE_PATH = REPO_ROOT / ".pkit" / "permissions" / "decide.py"
CATALOG_PATH = REPO_ROOT / ".pkit" / "schemas" / "privilege-catalog.yaml"


@pytest.fixture(scope="module")
def decide_mod():
    spec = importlib.util.spec_from_file_location("perm_decide_under_test", DECIDE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def catalog(decide_mod):
    return decide_mod.load_yaml(str(CATALOG_PATH))


def _tok(pid: str) -> str:
    return f"[privilege-catalog:{pid}]"


MODEL = {
    "posture": "lenient",
    "grants": [
        {"subject": "all", "privilege": _tok("privilege-escalation"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("destructive-fs"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("vcs-history-rewrite"), "effect": "deny"},
        {"subject": "operator",
         "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit"), _tok("repo-read")],
         "effect": "allow"},
        {"subject": "agent:project-manager",
         "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit")], "effect": "allow"},
        {"subject": "agent:critic",
         "privilege": [_tok("repo-read"), _tok("web-fetch")], "effect": "allow"},
        {"subject": "agent:devops", "privilege": _tok("docker"),
         "scope": ["services/**", "deploy/**"], "effect": "allow"},
    ],
}


def _bash(cmd, subject, cwd="/r"):
    return {"type": "bash", "command": cmd, "cwd": cwd, "subject": subject}


def _tool(tool, subject, cwd="/r"):
    return {"type": "tool", "tool": tool, "cwd": cwd, "subject": subject}


def test_segments_strips_env_prefix_and_matches_gh(decide_mod, catalog):
    assert decide_mod.segments("export GH_HOST=x && gh pr list") == [["gh", "pr", "list"]]
    assert decide_mod.recognized_privileges(
        catalog, _bash("export GH_HOST=x && gh pr list", "agent:project-manager")
    ) == {"issue-tracker"}


def test_pm_allowed_gh_after_env_prefix(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("export GH_HOST=x && gh pr list", "agent:project-manager"))
    assert d == "allow"


def test_devops_docker_inside_scope_allow(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("docker run img", "agent:devops", cwd="services/api"))
    assert d == "allow"


def test_devops_docker_outside_scope_deny(decide_mod, catalog):
    d, why = decide_mod.decide(MODEL, catalog, _bash("docker run img", "agent:devops", cwd="secret/vault"))
    assert d == "deny"  # deny-outside-scope
    assert "scope" in why.lower() or "only in" in why.lower()


def test_sudo_denied_for_everyone(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("sudo rm x", "agent:project-manager"))
    assert d == "deny"


def test_rm_rf_denied(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("rm -rf /tmp/x", "operator"))
    assert d == "deny"


def test_force_push_denied_deny_wins(decide_mod, catalog):
    # pm has vcs allow; git push --force also matches vcs-history-rewrite (baseline deny) -> deny wins.
    d, _ = decide_mod.decide(MODEL, catalog, _bash("git push --force origin main", "agent:project-manager"))
    assert d == "deny"


def test_plain_git_push_allowed_for_pm(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("git push origin main", "agent:project-manager"))
    assert d == "allow"


def test_critic_webfetch_allow(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _tool("WebFetch", "agent:critic"))
    assert d == "allow"


def test_critic_gh_abstain_lenient(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("gh pr list", "agent:critic"))
    assert d == "abstain"


def test_critic_gh_deny_strict(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("gh pr list", "agent:critic"), posture="strict")
    assert d == "deny"


def test_operator_git_allow(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("git status", "operator"))
    assert d == "allow"


def test_hook_decide_fail_open_on_malformed(decide_mod, catalog):
    d, why = decide_mod.hook_decide(MODEL, catalog, {"garbage": True})
    assert d == "abstain" and "fail-open" in why


def test_hook_decide_main_thread_is_operator(decide_mod, catalog):
    # No agent_type in payload -> operator subject.
    payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": "/r"}
    d, why = decide_mod.hook_decide(MODEL, catalog, payload)
    assert d == "allow" and "operator" in why


def test_hook_decide_subagent_uses_agent_subject(decide_mod, catalog):
    payload = {"tool_name": "WebFetch", "tool_input": {"url": "https://x"},
               "cwd": "/r", "agent_type": "critic"}
    d, _ = decide_mod.hook_decide(MODEL, catalog, payload)
    assert d == "allow"


# ---- load_model: the single loader (same-code invariant) -------------------

def test_guardrail_denies_derived_from_catalog(decide_mod, catalog):
    denies = decide_mod.guardrail_denies(catalog)
    pids = {decide_mod._privilege_ids(g["privilege"]).pop() for g in denies}
    assert pids == {"privilege-escalation", "destructive-fs", "vcs-history-rewrite"}
    assert all(g["subject"] == "all" and g["effect"] == "deny" for g in denies)


def _write_tree(root: Path, *, grants: str | None = None, config: str | None = None) -> None:
    (root / ".pkit" / "schemas").mkdir(parents=True)
    (root / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text(
        CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    if grants is not None or config is not None:
        (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
        if grants is not None:
            (root / ".pkit" / "permissions" / "project" / "grants.yaml").write_text(grants)
        if config is not None:
            (root / ".pkit" / "permissions" / "project" / "config.yaml").write_text(config)


def test_load_model_unions_guardrails_with_project_grants(decide_mod, tmp_path):
    _write_tree(
        tmp_path,
        grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:critic\n"
            "    privilege: \"[privilege-catalog:web-fetch]\"\n"
            "    effect: allow\n"
        ),
        config="schema_version: 1\nownership_mode: additive\nposture: strict\n",
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    assert model["posture"] == "strict"
    subjects = {g["subject"] for g in model["grants"]}
    assert "all" in subjects and "agent:critic" in subjects
    # The unioned model drives a real decision: critic gets web-fetch; everyone
    # is denied the guardrails.
    d, _ = decide_mod.decide(model, catalog, _tool("WebFetch", "agent:critic"))
    assert d == "allow"
    d, _ = decide_mod.decide(model, catalog, _bash("sudo rm x", "agent:critic"))
    assert d == "deny"


def test_load_model_defaults_when_no_project_state(decide_mod, tmp_path):
    _write_tree(tmp_path)
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    assert model["posture"] == "lenient" and model["ownership_mode"] == "additive"
    assert len(model["grants"]) == 3  # guardrails only


# ---- destructive-fs guardrail: recursive rm in any flag form (widened) -----

@pytest.mark.parametrize("cmd", [
    "rm -rf x", "rm -fr x", "rm -r x", "rm -R x", "rm -fR x", "rm -Rf x",
    "rm -rfv x", "rm --recursive x", "rm --recursive=true x", "rm -i -R x",
    "export Y=1 && rm -R x",
])
def test_recursive_rm_denied_any_form(decide_mod, catalog, cmd):
    assert "destructive-fs" in decide_mod.recognized_privileges(catalog, _bash(cmd, "operator"))
    d, _ = decide_mod.decide(MODEL, catalog, _bash(cmd, "operator"))
    assert d == "deny", cmd


@pytest.mark.parametrize("cmd", [
    "rm x", "rm -f x", "rm -i x", "rm --force x", "rm ./-r-named-file",
    "rm-foo -r x",  # a DIFFERENT binary whose name starts with rm — not our rm
])
def test_non_recursive_rm_not_a_guardrail(decide_mod, catalog, cmd):
    # bare / force-single-file / interactive rm is NOT destructive-fs — it must
    # not be over-blocked (that is fs-cleanup territory, not the guardrail).
    assert "destructive-fs" not in decide_mod.recognized_privileges(catalog, _bash(cmd, "operator"))


# ---- active-profile grant layering (ADR-005 / #255) ------------------------

def _profile_tree(root: Path, *, profile: str, config: str, grants: str | None = None):
    (root / ".pkit" / "schemas").mkdir(parents=True)
    (root / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text(
        CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    pdir = root / ".pkit" / "permissions" / "project" / "profiles"
    pdir.mkdir(parents=True)
    (pdir / "team.yaml").write_text(profile, encoding="utf-8")
    proj = root / ".pkit" / "permissions" / "project"
    (proj / "config.yaml").write_text(config, encoding="utf-8")
    if grants is not None:
        (proj / "grants.yaml").write_text(grants, encoding="utf-8")


def test_load_model_layers_active_profile_between_guardrails_and_adopter(decide_mod, tmp_path):
    _profile_tree(
        tmp_path,
        profile=("schema_version: 1\ndescription: t\nposture: lenient\n"
                 "grants:\n  - subject: all\n    privilege: \"[privilege-catalog:vcs]\"\n"
                 "    effect: allow\n"),
        config=("schema_version: 1\nownership_mode: additive\nposture: lenient\n"
                "active_profile: team\n"),
        grants=("schema_version: 1\ngrants:\n  - subject: agent:critic\n"
                "    privilege: \"[privilege-catalog:repo-read]\"\n    effect: allow\n"),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    assert model["active_profile"] == "team"
    ids = [next(iter(decide_mod._privilege_ids(g["privilege"]))) for g in model["grants"]]
    # guardrails (sorted) → profile → adopter, in that order
    assert ids == ["destructive-fs", "privilege-escalation", "vcs-history-rewrite",
                   "vcs", "repo-read"]
    # the profile's `all` vcs grant decides live
    d, _ = decide_mod.decide(model, catalog, _bash("git status", "operator"))
    assert d == "allow"


def test_load_model_no_active_profile_no_layer(decide_mod, tmp_path):
    _write_tree(tmp_path)  # catalog only, no config/profile
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    assert model["active_profile"] is None
    assert len(model["grants"]) == 3  # guardrails only
