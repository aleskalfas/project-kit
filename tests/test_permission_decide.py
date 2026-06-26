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


def _tool(tool, subject, cwd="/r", url=None):
    r = {"type": "tool", "tool": tool, "cwd": cwd, "subject": subject}
    if url is not None:
        r["url"] = url
    return r


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
    # Unscoped web-fetch grant: no scope constraint → any host allowed.
    d, _ = decide_mod.decide(MODEL, catalog, _tool("WebFetch", "agent:critic"))
    assert d == "allow"


# ---- domain-scope matching (issue #23) -------------------------------------
# A grant with scope_type=domain and a scope list acts as a positive
# allow-list on the URL hostname.  Directory-scope behaviour is unchanged.

# Minimal model for domain-scope tests: web-fetch scoped to docs.python.org.
_DOMAIN_MODEL = {
    "posture": "strict",
    "grants": [
        # guardrail denies
        {"subject": "all", "privilege": _tok("privilege-escalation"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("destructive-fs"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("vcs-history-rewrite"), "effect": "deny"},
        # domain-scoped web-fetch: allow-list on a single exact host
        {"subject": "agent:researcher",
         "privilege": _tok("web-fetch"),
         "scope": ["docs.python.org"],
         "effect": "allow"},
        # domain-scoped web-fetch: glob — any subdomain of example.com
        {"subject": "agent:analyst",
         "privilege": _tok("web-fetch"),
         "scope": ["*.example.com"],
         "effect": "allow"},
    ],
}


def test_domain_scope_matching_host_allowed(decide_mod, catalog):
    """A WebFetch request whose host exactly matches the scope glob is allowed."""
    d, _ = decide_mod.decide(
        _DOMAIN_MODEL, catalog,
        _tool("WebFetch", "agent:researcher", url="https://docs.python.org/3/library/fnmatch.html"),
    )
    assert d == "allow"


def test_domain_scope_non_matching_host_denied(decide_mod, catalog):
    """A WebFetch request whose host does NOT match the scope glob is denied."""
    d, why = decide_mod.decide(
        _DOMAIN_MODEL, catalog,
        _tool("WebFetch", "agent:researcher", url="https://evil.example.com/steal"),
    )
    assert d == "deny"
    assert "domain-scope" in why.lower() or "does not match" in why.lower()


def test_domain_scope_wildcard_glob_matching_host_allowed(decide_mod, catalog):
    """A host matched by a wildcard glob (*.example.com) is allowed."""
    d, _ = decide_mod.decide(
        _DOMAIN_MODEL, catalog,
        _tool("WebFetch", "agent:analyst", url="https://api.example.com/data"),
    )
    assert d == "allow"


def test_domain_scope_wildcard_glob_non_matching_host_denied(decide_mod, catalog):
    """A host that doesn't match the wildcard glob is denied."""
    d, why = decide_mod.decide(
        _DOMAIN_MODEL, catalog,
        _tool("WebFetch", "agent:analyst", url="https://api.notexample.com/data"),
    )
    assert d == "deny"
    assert "domain-scope" in why.lower() or "does not match" in why.lower()


def test_domain_scope_missing_url_denied(decide_mod, catalog):
    """A domain-scoped grant with no URL in the request is denied (can't check host)."""
    d, why = decide_mod.decide(
        _DOMAIN_MODEL, catalog,
        _tool("WebFetch", "agent:researcher"),  # no url kwarg
    )
    assert d == "deny"
    assert "hostname" in why.lower() or "url" in why.lower()


def test_domain_scope_deny_glob_rejected(decide_mod, catalog):
    """A negation/deny scope glob (starting with '!') is explicitly rejected, not silently applied."""
    deny_glob_model = {
        "posture": "lenient",
        "grants": [
            {"subject": "agent:researcher",
             "privilege": _tok("web-fetch"),
             "scope": ["!*.ru"],
             "effect": "allow"},
        ],
    }
    d, why = decide_mod.decide(
        deny_glob_model, catalog,
        _tool("WebFetch", "agent:researcher", url="https://docs.python.org/"),
    )
    assert d == "deny"
    # The rejection message must name the unsupported negation, not silently ignore it.
    assert "unsupported" in why.lower() or "negation" in why.lower() or "deny" in why.lower()


def test_directory_scope_unchanged_inside(decide_mod, catalog):
    """Directory-scope behaviour is unchanged: a request inside the scope is allowed."""
    d, _ = decide_mod.decide(MODEL, catalog, _bash("docker run img", "agent:devops", cwd="services/api"))
    assert d == "allow"


def test_directory_scope_unchanged_outside(decide_mod, catalog):
    """Directory-scope behaviour is unchanged: a request outside the scope is denied."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("docker run img", "agent:devops", cwd="secret/vault"))
    assert d == "deny"
    assert "scope" in why.lower() or "only in" in why.lower() or "does not match" in why.lower()


def test_hook_decide_domain_scoped_webfetch_allowed(decide_mod, catalog):
    """hook_decide threads the URL through for domain-scope checks: matching host is allowed."""
    model = {
        "posture": "strict",
        "grants": [
            {"subject": "all", "privilege": _tok("privilege-escalation"), "effect": "deny"},
            {"subject": "all", "privilege": _tok("destructive-fs"), "effect": "deny"},
            {"subject": "all", "privilege": _tok("vcs-history-rewrite"), "effect": "deny"},
            {"subject": "agent:researcher",
             "privilege": _tok("web-fetch"),
             "scope": ["docs.python.org"],
             "effect": "allow"},
        ],
    }
    payload = {
        "tool_name": "WebFetch",
        "tool_input": {"url": "https://docs.python.org/3/"},
        "cwd": "/r",
        "agent_type": "researcher",
    }
    d, _ = decide_mod.hook_decide(model, catalog, payload)
    assert d == "allow"


def test_hook_decide_domain_scoped_webfetch_non_matching_denied(decide_mod, catalog):
    """hook_decide threads the URL through: non-matching host is denied."""
    model = {
        "posture": "strict",
        "grants": [
            {"subject": "all", "privilege": _tok("privilege-escalation"), "effect": "deny"},
            {"subject": "all", "privilege": _tok("destructive-fs"), "effect": "deny"},
            {"subject": "all", "privilege": _tok("vcs-history-rewrite"), "effect": "deny"},
            {"subject": "agent:researcher",
             "privilege": _tok("web-fetch"),
             "scope": ["docs.python.org"],
             "effect": "allow"},
        ],
    }
    payload = {
        "tool_name": "WebFetch",
        "tool_input": {"url": "https://evil.example.com/exfil"},
        "cwd": "/r",
        "agent_type": "researcher",
    }
    d, why = decide_mod.hook_decide(model, catalog, payload)
    assert d == "deny"
    assert "domain-scope" in why.lower() or "does not match" in why.lower()


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


# ---- active_profile per-machine source (ADR-032 / #304) --------------------
#
# `active_profile` is a decision-model input read by the live hook through
# `load_model` → `active_profile`. ADR-032 moves it to a per-machine sidecar
# with a permanent `config.yaml` fallback; these assert the resolution and the
# enforcement-unchanged guarantee (the hook still layers the profile's grants).

def _profile_sidecar_tree(root: Path, *, profile_name: str,
                          sidecar: str | None, config: str):
    (root / ".pkit" / "schemas").mkdir(parents=True)
    (root / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text(
        CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    pdir = root / ".pkit" / "permissions" / "project" / "profiles"
    pdir.mkdir(parents=True)
    (pdir / f"{profile_name}.yaml").write_text(
        "schema_version: 1\ndescription: t\nposture: lenient\n"
        "grants:\n  - subject: all\n    privilege: \"[privilege-catalog:vcs]\"\n"
        "    effect: allow\n",
        encoding="utf-8",
    )
    proj = root / ".pkit" / "permissions" / "project"
    (proj / "config.yaml").write_text(config, encoding="utf-8")
    if sidecar is not None:
        (proj / "active-profile.yaml").write_text(sidecar, encoding="utf-8")


def test_active_profile_resolves_from_sidecar(decide_mod, tmp_path):
    # The sidecar is the source of truth; config.yaml carries no active_profile.
    _profile_sidecar_tree(
        tmp_path, profile_name="team",
        sidecar="schema_version: 1\nactive_profile: team\n",
        config="schema_version: 1\nownership_mode: additive\nposture: lenient\n",
    )
    cfg = decide_mod.load_yaml(
        str(tmp_path / ".pkit" / "permissions" / "project" / "config.yaml"))
    assert decide_mod.active_profile(str(tmp_path), cfg) == "team"


def test_active_profile_falls_back_to_config(decide_mod, tmp_path):
    # An adopter mid-migration: no sidecar yet, active_profile still in config.
    _profile_sidecar_tree(
        tmp_path, profile_name="team", sidecar=None,
        config=("schema_version: 1\nownership_mode: additive\nposture: lenient\n"
                "active_profile: team\n"),
    )
    cfg = decide_mod.load_yaml(
        str(tmp_path / ".pkit" / "permissions" / "project" / "config.yaml"))
    assert decide_mod.active_profile(str(tmp_path), cfg) == "team"


def test_active_profile_sidecar_wins_over_config(decide_mod, tmp_path):
    # Sidecar takes precedence over a stale config value (post-relocation safety).
    _profile_sidecar_tree(
        tmp_path, profile_name="team",
        sidecar="schema_version: 1\nactive_profile: team\n",
        config=("schema_version: 1\nownership_mode: additive\nposture: lenient\n"
                "active_profile: stale\n"),
    )
    cfg = decide_mod.load_yaml(
        str(tmp_path / ".pkit" / "permissions" / "project" / "config.yaml"))
    assert decide_mod.active_profile(str(tmp_path), cfg) == "team"


@pytest.mark.parametrize("corrupt_sidecar", ["42\n", "- a\n- b\n", "just a string\n"],
                         ids=["bare-scalar", "top-level-list", "bare-string"])
@pytest.mark.parametrize("block_ruamel", [False, True], ids=["ruamel", "stdlib"])
def test_corrupt_sidecar_falls_back_to_config_on_both_parse_paths(
    decide_mod, tmp_path, monkeypatch, corrupt_sidecar, block_ruamel,
):
    # A hand-corrupted active-profile.yaml that parses to a non-dict (bare scalar,
    # top-level list, bare string) must NOT make active_profile()'s `.get()` raise.
    # load_yaml coerces a non-dict document to {} on BOTH parse paths (ruamel via
    # the CLI, stdlib via the sandboxed hook), so resolution degrades to the
    # config.yaml fallback identically — the same-code invariant (ADR-002/ADR-003).
    _profile_sidecar_tree(
        tmp_path, profile_name="team", sidecar=corrupt_sidecar,
        config=("schema_version: 1\nownership_mode: additive\nposture: lenient\n"
                "active_profile: team\n"),
    )
    if block_ruamel:
        import builtins
        real_import = builtins.__import__

        def _block(name, *args, **kwargs):
            if "ruamel" in name:
                raise ImportError(f"simulated missing ruamel: {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block)

    cfg = decide_mod.load_yaml(
        str(tmp_path / ".pkit" / "permissions" / "project" / "config.yaml"))
    # No raise, and the corrupt sidecar yields no name → config.yaml fallback.
    assert decide_mod.active_profile(str(tmp_path), cfg) == "team"


def test_load_model_layers_profile_from_sidecar(decide_mod, tmp_path):
    # Enforcement unchanged: with active_profile in the sidecar, load_model still
    # layers the profile's grants and the model decides the same.
    _profile_sidecar_tree(
        tmp_path, profile_name="team",
        sidecar="schema_version: 1\nactive_profile: team\n",
        config="schema_version: 1\nownership_mode: additive\nposture: lenient\n",
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    assert model["active_profile"] == "team"
    d, _ = decide_mod.decide(model, catalog, _bash("git status", "operator"))
    assert d == "allow"  # the profile's `all` vcs grant is live


def test_load_model_layers_profile_from_config_fallback(decide_mod, tmp_path):
    # No-regression mid-migration: active_profile only in config.yaml — load_model
    # STILL layers the profile (a frozen old loader would have, too; the point is
    # the new loader keeps doing so via the fallback).
    _profile_sidecar_tree(
        tmp_path, profile_name="team", sidecar=None,
        config=("schema_version: 1\nownership_mode: additive\nposture: lenient\n"
                "active_profile: team\n"),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    assert model["active_profile"] == "team"
    d, _ = decide_mod.decide(model, catalog, _bash("git status", "operator"))
    assert d == "allow"


# ---- stdlib YAML-subset fallback (ADR-014 pt.1 / ADR-002/003 same-code) -----
#
# Critical invariant: the stdlib fallback in load_yaml() MUST parse the real
# shipped files identically to ruamel.yaml safe-load, or the hook and CLI can
# disagree on the model — a security bug.  These tests assert structural
# equality between ruamel and stdlib parse results on the actual shipped files.

REPO_ROOT_LOCAL = Path(__file__).resolve().parent.parent
_SHIPPED_FILES = [
    REPO_ROOT_LOCAL / ".pkit" / "schemas" / "privilege-catalog.yaml",
    REPO_ROOT_LOCAL / ".pkit" / "schemas" / "confinement-toolkit.yaml",
    REPO_ROOT_LOCAL / ".pkit" / "permissions" / "profiles" / "autonomous.yaml",
    REPO_ROOT_LOCAL / ".pkit" / "permissions" / "profiles" / "non-destructive.yaml",
    REPO_ROOT_LOCAL / ".pkit" / "permissions" / "profiles" / "read-only.yaml",
    # Adopter-authored grants.yaml: block-seq-of-mappings at col 0 — the shape
    # that was broken in issue #55.  Added here so shipped-file parity covers it.
    REPO_ROOT_LOCAL / ".pkit" / "permissions" / "project" / "grants.yaml",
    # Capability-contributed fragment (ADR-016): must also be parse-identical
    # through the stdlib fallback so the hook can read it in macOS Seatbelt.
    REPO_ROOT_LOCAL / ".pkit" / "capabilities" / "project-management" / "permissions" / "grants.yaml",
]

# Representative synthetic files that exercise edge cases the shipped files use.
_SYNTHETIC_YAML_CASES = [
    # grants.yaml-like: block mapping + block sequence + double-quoted tokens
    (
        "grants-like",
        (
            "schema_version: 1\n"
            "grants:\n"
            '  - subject: operator\n'
            '    privilege: "[privilege-catalog:vcs]"\n'
            "    effect: allow\n"
            '  - subject: all\n'
            '    privilege:\n'
            '      - "[privilege-catalog:privilege-escalation]"\n'
            '      - "[privilege-catalog:destructive-fs]"\n'
            "    effect: deny\n"
        ),
    ),
    # config.yaml-like: simple block mapping with booleans and null
    (
        "config-like",
        (
            "schema_version: 1\n"
            "ownership_mode: additive\n"
            "posture: lenient\n"
            "active_profile: ~\n"
        ),
    ),
    # profile-like: block mapping + block sequence + single-quoted values
    (
        "profile-like",
        (
            "schema_version: 1\n"
            "description: A test profile.\n"
            "posture: strict\n"
            "grants:\n"
            "  - subject: all\n"
            "    privilege:\n"
            '      - "[privilege-catalog:vcs]"\n'
            "    effect: allow\n"
        ),
    ),
    # Flow sequence (used in privilege-catalog flag_any)
    (
        "flow-sequence",
        'flag_any: ["--force", "-f", "--force-with-lease"]\n',
    ),
    # Single-quoted string with regex chars (used in privilege-catalog pattern)
    (
        "single-quoted-regex",
        "pattern: '^rm(?=\\\\s).*'\n",
    ),
    # Booleans and integers
    (
        "booleans-and-ints",
        "enabled: true\ncount: 3\nguardrail: false\n",
    ),
    # Nested block mapping + block scalar (>-)
    (
        "block-scalar",
        (
            "toolkits:\n"
            "  gh:\n"
            "    description: GitHub CLI.\n"
            "    allowances:\n"
            "      - kind: exclude-command\n"
            "        effect: widening\n"
            "        value: gh\n"
            "        note: >-\n"
            "          runs gh OUTSIDE the box. Needed because gh TLS\n"
            "          fails under Seatbelt.\n"
        ),
    ),
    # Adopter grants.yaml shape: block-seq-of-mappings at col 0 — the "- " at
    # the SAME indent as the parent key.  This is the shape that was broken
    # (issue #55): _stdlib_load_yaml returned grants: None because the c2 > col
    # guard rejected same-indent sequences.  Covered here so the regression
    # can't silently reappear.
    (
        "grants-col0-block-seq",
        (
            "schema_version: 1\n"
            "grants:\n"
            "- subject: agent:project-manager\n"
            "  privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "  effect: deny\n"
        ),
    ),
    # Adopter grants.yaml with multiple col-0 entries (multi-entry variant).
    (
        "grants-col0-multi-entry",
        (
            "schema_version: 1\n"
            "grants:\n"
            "- subject: agent:project-manager\n"
            "  privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "  effect: deny\n"
            "- subject: all\n"
            "  privilege: '[privilege-catalog:vcs]'\n"
            "  effect: allow\n"
        ),
    ),
    # Adopter config.yaml shape: simple flat mapping (no sequence) — ensures
    # the same-indent-seq fix doesn't misfire on sibling mapping keys.
    (
        "config-adopter",
        (
            "schema_version: 1\n"
            "ownership_mode: additive\n"
            "posture: lenient\n"
            "active_profile: team\n"
        ),
    ),
]


def _ruamel_load(text: str) -> Any:
    """Parse with ruamel.yaml safe-load (the reference parser)."""
    try:
        from ruamel.yaml import YAML
        import io
        yaml = YAML(typ="safe")
        return yaml.load(io.StringIO(text)) or {}
    except ImportError:
        pytest.skip("ruamel.yaml not available — can't assert parse equality")


@pytest.mark.parametrize("shipped_path", _SHIPPED_FILES, ids=lambda p: p.name)
def test_stdlib_fallback_parses_identically_to_ruamel_on_shipped_files(decide_mod, shipped_path):
    """The stdlib fallback MUST parse every shipped file identically to ruamel.
    A mis-parse means the hook mis-decides — a security bug (ADR-014 / ADR-002)."""
    text = shipped_path.read_text(encoding="utf-8")
    ruamel_result = _ruamel_load(text)
    stdlib_result = decide_mod._stdlib_load_yaml(text)
    assert stdlib_result == ruamel_result, (
        f"stdlib fallback parse differs from ruamel for {shipped_path.name}:\n"
        f"  stdlib:  {stdlib_result!r}\n"
        f"  ruamel:  {ruamel_result!r}"
    )


@pytest.mark.parametrize("name,text", _SYNTHETIC_YAML_CASES, ids=lambda x: x if isinstance(x, str) else "text")
def test_stdlib_fallback_parses_synthetic_cases_identically_to_ruamel(decide_mod, name, text):
    """Synthetic edge-case files: fallback == ruamel on all YAML features the
    shipped files use (flow-seq, block-scalar, single/double-quoted, booleans)."""
    ruamel_result = _ruamel_load(text)
    stdlib_result = decide_mod._stdlib_load_yaml(text)
    assert stdlib_result == ruamel_result, (
        f"stdlib fallback parse differs from ruamel for case {name!r}:\n"
        f"  stdlib:  {stdlib_result!r}\n"
        f"  ruamel:  {ruamel_result!r}"
    )


def test_stdlib_fallback_used_when_ruamel_absent(decide_mod, tmp_path, monkeypatch):
    """When ruamel.yaml is not importable, load_yaml falls back to the stdlib
    parser and the result is structurally identical — same-code invariant holds."""
    import builtins
    real_import = builtins.__import__

    def _block_ruamel(name, *args, **kwargs):
        if "ruamel" in name:
            raise ImportError(f"simulated missing ruamel: {name}")
        return real_import(name, *args, **kwargs)

    # Write a representative grants file to a tmp tree.
    path = tmp_path / "grants.yaml"
    path.write_text(
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: operator\n"
        '    privilege: "[privilege-catalog:vcs]"\n'
        "    effect: allow\n",
        encoding="utf-8",
    )
    expected = decide_mod.load_yaml(str(path))  # parse with ruamel (reference)

    monkeypatch.setattr(builtins, "__import__", _block_ruamel)
    stdlib_result = decide_mod.load_yaml(str(path))  # must fall back to stdlib
    assert stdlib_result == expected


def test_stdlib_fallback_load_model_decides_correctly_without_ruamel(decide_mod, tmp_path, monkeypatch):
    """With ruamel blocked, load_model still builds a correct model and decide()
    still gives the right verdicts — the same-code invariant holds end-to-end."""
    import builtins
    real_import = builtins.__import__

    def _block_ruamel(name, *args, **kwargs):
        if "ruamel" in name:
            raise ImportError(f"simulated missing ruamel: {name}")
        return real_import(name, *args, **kwargs)

    # Build a complete tree so load_model has real files.
    _write_tree(
        tmp_path,
        grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: operator\n"
            '    privilege: "[privilege-catalog:vcs]"\n'
            "    effect: allow\n"
        ),
        config="schema_version: 1\nownership_mode: additive\nposture: lenient\n",
    )
    catalog_with_ruamel = decide_mod.load_catalog(str(tmp_path))
    model_with_ruamel = decide_mod.load_model(str(tmp_path), catalog_with_ruamel)

    monkeypatch.setattr(builtins, "__import__", _block_ruamel)
    catalog_stdlib = decide_mod.load_catalog(str(tmp_path))
    model_stdlib = decide_mod.load_model(str(tmp_path), catalog_stdlib)

    assert model_stdlib == model_with_ruamel
    # Decisions must be identical.
    for request in [
        _bash("git status", "operator"),
        _bash("sudo rm x", "operator"),
        _tool("WebFetch", "operator"),
    ]:
        d_ref, _ = decide_mod.decide(model_with_ruamel, catalog_with_ruamel, request)
        d_std, _ = decide_mod.decide(model_stdlib, catalog_stdlib, request)
        assert d_ref == d_std, f"decide differs on {request}: ruamel={d_ref} stdlib={d_std}"


# ---- issue-tracker-write deny (issue #53) -----------------------------------
#
# issue-tracker-write recognizes gh issue edit / gh issue comment / gh pr edit.
# It does NOT recognize gh issue view / gh pr view / gh api / git / pkit.
#
# The critical correctness property: deny-precedence.
# A project-manager `gh issue edit` matches BOTH:
#   - issue-tracker  (cmd: gh — the broad privilege, granted allow)
#   - issue-tracker-write  (pattern: the mutation privilege, denied)
# decide() iterates ALL effective grants, returns deny immediately on any
# deny-overlap hit — so the explicit deny wins over the broad allow regardless
# of ordering.  No change to decide.py was required: the existing loop already
# provides order-independent deny-wins semantics.

_PM_WITH_DENY_MODEL = {
    "posture": "lenient",
    "grants": [
        # guardrail denies (always present)
        {"subject": "all", "privilege": _tok("privilege-escalation"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("destructive-fs"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("vcs-history-rewrite"), "effect": "deny"},
        # project-manager's production-representative grants
        {"subject": "agent:project-manager",
         "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit")], "effect": "allow"},
        # the surgical deny that forces mutation through the validating scripts
        {"subject": "agent:project-manager",
         "privilege": _tok("issue-tracker-write"), "effect": "deny"},
    ],
}


@pytest.mark.parametrize("cmd", [
    "gh issue edit 53 --body 'new body'",
    "gh issue edit 53 --title 'new title'",
    "gh issue comment 53 --body 'a comment'",
    "gh pr edit 27 --title 'update'",
    "gh pr edit 27 --body 'new body'",
    # broadened mutation set (issue #118): create/close/reopen + pr create/merge/close/reopen
    "gh issue create --title 'x' --body 'y'",
    "gh issue close 53",
    "gh issue close 53 --reason completed",
    "gh issue reopen 53",
    "gh pr create --title 'x' --body 'y'",
    "gh pr merge 27 --squash",
    "gh pr close 27",
    "gh pr reopen 27",
    # env-prefix form — the segments() stripper must handle this
    "export GH_HOST=github.com && gh issue edit 53",
    "export GH_HOST=github.com && gh issue close 53",
])
def test_pm_issue_tracker_write_denied(decide_mod, catalog, cmd):
    """gh issue edit / gh issue comment / gh pr edit are blocked for project-manager.

    Deny-precedence proof: these commands also match issue-tracker (broad gh,
    granted allow), but the explicit deny on issue-tracker-write wins — decide()
    returns 'deny' even though an allow grant exists for the same request.
    """
    hits = decide_mod.recognized_privileges(catalog, _bash(cmd, "agent:project-manager"))
    assert "issue-tracker-write" in hits, f"issue-tracker-write should recognize {cmd!r}"
    d, why = decide_mod.decide(_PM_WITH_DENY_MODEL, catalog, _bash(cmd, "agent:project-manager"))
    assert d == "deny", f"expected deny for project-manager on {cmd!r}, got {d!r}: {why}"
    assert "issue-tracker-write" in why


@pytest.mark.parametrize("cmd", [
    "gh issue view 53",
    "gh issue list",
    "gh issue list --state open",
    "gh issue status",
    "gh pr view 27",
    "gh pr list",
    "gh pr checks 27",
    "gh pr diff 27",
    "gh api repos/owner/repo/issues",
    "gh api graphql -f query='...'",
    "gh api -X PATCH repos/o/r/issues/5 -f state=closed",
])
def test_pm_gh_reads_and_api_not_recognized_by_write_privilege(decide_mod, catalog, cmd):
    """gh reads and gh api are NOT recognized by issue-tracker-write.

    These commands only match issue-tracker (the broad gh privilege).  With a
    project-manager model that allows issue-tracker but denies issue-tracker-write,
    the deny has no overlap with the hits — so it does not fire.
    """
    hits = decide_mod.recognized_privileges(catalog, _bash(cmd, "agent:project-manager"))
    assert "issue-tracker-write" not in hits, (
        f"issue-tracker-write must NOT recognize {cmd!r} (only mutations), got hits={hits}"
    )


@pytest.mark.parametrize("cmd,expected", [
    # gh reads → allow (issue-tracker allow, no issue-tracker-write overlap → no deny)
    ("gh issue view 53", "allow"),
    ("gh issue list", "allow"),
    ("gh pr view 27", "allow"),
    ("gh api repos/owner/repo/issues", "allow"),
    # git → allow (vcs privilege, not affected by issue-tracker-write deny)
    ("git status", "allow"),
    ("git log --oneline", "allow"),
    ("git push origin main", "allow"),
    # pkit → allow (kit privilege)
    ("pkit status", "allow"),
    ("pkit permissions overview", "allow"),
])
def test_pm_unaffected_commands_allowed(decide_mod, catalog, cmd, expected):
    """Commands that do not match issue-tracker-write are unaffected by the deny.

    Proves: the surgical deny does not block reads, gh api, git, or pkit — only
    the three raw mutations (gh issue edit, gh issue comment, gh pr edit).
    """
    d, why = decide_mod.decide(_PM_WITH_DENY_MODEL, catalog, _bash(cmd, "agent:project-manager"))
    assert d == expected, (
        f"expected {expected!r} for {cmd!r}, got {d!r}: {why}"
    )


def test_deny_precedence_allow_before_deny_in_grant_list(decide_mod, catalog):
    """Deny-precedence is order-independent: even when the allow grant appears
    BEFORE the deny grant in the list, the deny still wins.

    This test exercises the most-restrictive-wins property directly: decide()
    continues iterating after matched_allow=True and short-circuits on the deny.
    """
    allow_first_model = {
        "posture": "lenient",
        "grants": [
            # allow issue-tracker first (broad gh)
            {"subject": "agent:project-manager",
             "privilege": _tok("issue-tracker"), "effect": "allow"},
            # deny issue-tracker-write second
            {"subject": "agent:project-manager",
             "privilege": _tok("issue-tracker-write"), "effect": "deny"},
        ],
    }
    d, why = decide_mod.decide(
        allow_first_model, catalog,
        _bash("gh issue edit 53", "agent:project-manager"),
    )
    assert d == "deny", f"deny must win even when allow precedes deny in grant list; got {d!r}: {why}"


def test_deny_precedence_deny_before_allow_in_grant_list(decide_mod, catalog):
    """Deny-precedence also holds when the deny grant appears BEFORE the allow grant."""
    deny_first_model = {
        "posture": "lenient",
        "grants": [
            # deny issue-tracker-write first
            {"subject": "agent:project-manager",
             "privilege": _tok("issue-tracker-write"), "effect": "deny"},
            # allow issue-tracker second (broad gh)
            {"subject": "agent:project-manager",
             "privilege": _tok("issue-tracker"), "effect": "allow"},
        ],
    }
    d, why = decide_mod.decide(
        deny_first_model, catalog,
        _bash("gh issue edit 53", "agent:project-manager"),
    )
    assert d == "deny", f"deny must win when deny precedes allow in grant list; got {d!r}: {why}"


def test_capability_scripts_internal_gh_not_blocked(decide_mod, catalog):
    """The capability scripts run inside the pkit subprocess, BELOW the PreToolUse hook.

    The hook fires on Claude Code agent tool calls; pkit's internal subprocess
    is not a Claude Code tool call and is therefore not subject to the hook.
    This test documents the invariant: a `pkit ...` call by project-manager is
    allowed (kit privilege), and any gh invocation inside that subprocess is
    out-of-scope for the hook — no code change is needed or correct here.
    """
    d, _ = decide_mod.decide(
        _PM_WITH_DENY_MODEL, catalog,
        _bash("pkit pm transition-state 53 in-progress", "agent:project-manager"),
    )
    assert d == "allow", "pkit invocations must remain allowed for project-manager"


# ---- issue-tracker-read-raw deny (issue #319) -------------------------------
#
# issue-tracker-read-raw recognizes the three raw read VIEWS the clean show-*
# verbs replace: gh issue view / gh pr view / gh pr diff.  It does NOT recognize
# gh pr checks, gh run, gh api, gh issue list, gh pr list, or any mutation.
#
# Same deny-precedence property as issue-tracker-write: a project-manager
# `gh issue view` matches BOTH issue-tracker (broad gh, allowed) and
# issue-tracker-read-raw (the read-redirect privilege, denied); decide()'s
# order-independent deny-wins makes the deny win, routing the agent to
# `pkit project-management show-issue` / `show-pr`.  No decide.py change needed.

_PM_WITH_READ_REDIRECT_MODEL = {
    "posture": "lenient",
    "grants": [
        # guardrail denies (always present)
        {"subject": "all", "privilege": _tok("privilege-escalation"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("destructive-fs"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("vcs-history-rewrite"), "effect": "deny"},
        # project-manager's production-representative grants
        {"subject": "agent:project-manager",
         "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit")], "effect": "allow"},
        # both capability denies the project-management fragment ships
        {"subject": "agent:project-manager",
         "privilege": _tok("issue-tracker-write"), "effect": "deny"},
        {"subject": "agent:project-manager",
         "privilege": _tok("issue-tracker-read-raw"), "effect": "deny"},
    ],
}


@pytest.mark.parametrize("cmd", [
    "gh issue view 1",
    "gh issue view 53 --json title,body",
    "gh pr view 1",
    "gh pr view 27 --json state",
    "gh pr diff 1",
    "gh pr diff 27 --color never",
    # env-prefix form — the segments() stripper must handle this
    "export GH_PAGER= && gh pr diff 27",
])
def test_pm_raw_read_views_denied(decide_mod, catalog, cmd):
    """gh issue view / gh pr view / gh pr diff are blocked for project-manager.

    Deny-precedence proof: these also match issue-tracker (broad gh allow), but
    the explicit deny on issue-tracker-read-raw wins — decide() returns 'deny',
    redirecting the agent to the clean show-issue / show-pr verbs.
    """
    hits = decide_mod.recognized_privileges(catalog, _bash(cmd, "agent:project-manager"))
    assert "issue-tracker-read-raw" in hits, f"issue-tracker-read-raw should recognize {cmd!r}"
    d, why = decide_mod.decide(
        _PM_WITH_READ_REDIRECT_MODEL, catalog, _bash(cmd, "agent:project-manager")
    )
    assert d == "deny", f"expected deny for project-manager on {cmd!r}, got {d!r}: {why}"
    assert "issue-tracker-read-raw" in why


@pytest.mark.parametrize("cmd", [
    # adjacent reads that MUST stay open — the alternation must not over-match
    "gh pr checks 27",
    "gh run list",
    "gh run view 12345",
    "gh api repos/owner/repo/issues",
    "gh api -X PATCH repos/o/r/issues/5 -f state=closed",
    "gh issue list",
    "gh issue list --state open",
    "gh issue status",
    "gh pr list",
    # mutations — covered by issue-tracker-write, NOT this privilege
    "gh issue edit 53 --body x",
    "gh issue comment 53 --body x",
    "gh pr edit 27 --title y",
    "gh issue create --title x",
    "gh pr merge 27 --squash",
    # near-miss prefixes that must not trip the `view`/`diff` alternation
    "gh issue viewer",
    "gh pr difftool",
])
def test_pm_adjacent_reads_not_recognized_by_read_redirect(decide_mod, catalog, cmd):
    """gh pr checks / gh run / gh api / list / mutations are NOT recognized by
    issue-tracker-read-raw — only the three replaced read views are.

    Proves the recognizer is scoped to view/diff and does not catch checks, run,
    api, list, or mutations.
    """
    hits = decide_mod.recognized_privileges(catalog, _bash(cmd, "agent:project-manager"))
    assert "issue-tracker-read-raw" not in hits, (
        f"issue-tracker-read-raw must NOT recognize {cmd!r} (only view/diff), got hits={hits}"
    )


@pytest.mark.parametrize("cmd,expected", [
    # adjacent reads → allow (issue-tracker allow, no read-raw overlap → no deny)
    ("gh pr checks 27", "allow"),
    ("gh run list", "allow"),
    ("gh issue list", "allow"),
    ("gh api repos/owner/repo/issues", "allow"),
    # git / pkit → allow (unaffected by the read-redirect deny)
    ("git status", "allow"),
    ("pkit status", "allow"),
])
def test_pm_read_redirect_leaves_adjacent_commands_allowed(decide_mod, catalog, cmd, expected):
    """The read-redirect deny does not block adjacent reads, gh api, git, or pkit —
    only the three raw read views (gh issue view / gh pr view / gh pr diff)."""
    d, why = decide_mod.decide(
        _PM_WITH_READ_REDIRECT_MODEL, catalog, _bash(cmd, "agent:project-manager")
    )
    assert d == expected, f"expected {expected!r} for {cmd!r}, got {d!r}: {why}"


@pytest.mark.parametrize("cmd", ["gh issue view 1", "gh pr view 1", "gh pr diff 1"])
def test_read_redirect_does_not_affect_other_subjects(decide_mod, catalog, cmd):
    """The three reads stay available to other subjects — the deny is per-agent.

    An operator with a broad issue-tracker allow and no read-raw deny still gets
    ALLOWED for the raw views; the redirect is scoped to agent:project-manager.
    """
    operator_model = {
        "posture": "lenient",
        "grants": [
            {"subject": "operator", "privilege": _tok("issue-tracker"), "effect": "allow"},
            # the capability deny is per-agent, so it does NOT apply to operator
            {"subject": "agent:project-manager",
             "privilege": _tok("issue-tracker-read-raw"), "effect": "deny"},
        ],
    }
    d, why = decide_mod.decide(operator_model, catalog, _bash(cmd, "operator"))
    assert d == "allow", f"raw views must stay allowed for operator on {cmd!r}, got {d!r}: {why}"


# ---- end-to-end guard: stdlib path enforces deny grants (issue #55) ---------
#
# The critical regression guard for the block-sequence-of-mappings parser fix.
# The zero-dep hook runs under macOS Seatbelt (ADR-014) where uv/ruamel is
# absent, so _stdlib_load_yaml is THE parse path for grants.yaml at decision
# time.  Before the fix, _stdlib_load_yaml returned grants: None for the
# col-0 block-seq shape, silently dropping every adopter grant and causing the
# hook to fail open even when a deny grant was present (issue #55 live failure).
#
# This test proves that with ruamel completely absent, hook_decide reads the
# deny grant from a grants.yaml file (col-0 block-seq shape) and actually
# returns "deny" for a project-manager gh issue edit — enforcement holds
# through the stdlib fallback path.

def test_stdlib_path_enforce_deny_grant_end_to_end(decide_mod, tmp_path, monkeypatch):
    """End-to-end: with ruamel absent, a deny grant in grants.yaml (col-0 block-seq
    shape) causes hook_decide to deny a project-manager gh issue edit.

    This is the end-to-end enforcement guard for issue #55.  The grants.yaml uses
    the exact shape that _stdlib_load_yaml previously mis-parsed to grants: None,
    which made the zero-dep hook fail open and rendered the deny ineffective.
    Passing here proves enforcement works *through the stdlib fallback*, not just
    that parse succeeds in isolation.
    """
    import builtins
    real_import = builtins.__import__

    def _block_ruamel(name, *args, **kwargs):
        if "ruamel" in name:
            raise ImportError(f"simulated missing ruamel: {name}")
        return real_import(name, *args, **kwargs)

    # Build a tree with:
    #   - The real privilege catalog (needed for recognizer matching).
    #   - A grants.yaml using the col-0 block-seq shape that was broken:
    #       grants:
    #       - subject: agent:project-manager
    #         privilege: '[privilege-catalog:issue-tracker-write]'
    #         effect: deny
    #   - No config (defaults: lenient posture).
    _write_tree(
        tmp_path,
        grants=(
            "schema_version: 1\n"
            "grants:\n"
            "- subject: agent:project-manager\n"
            "  privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "  effect: deny\n"
        ),
    )

    # Load catalog and model WITH ruamel (reference parse; verifies tree is valid).
    catalog_ref = decide_mod.load_catalog(str(tmp_path))
    model_ref = decide_mod.load_model(str(tmp_path), catalog_ref)
    # Sanity: the deny grant IS in the model under ruamel.
    deny_grants = [
        g for g in model_ref["grants"]
        if g.get("effect") == "deny" and g.get("subject") == "agent:project-manager"
    ]
    assert deny_grants, "reference model (ruamel) must contain the deny grant"

    # Now block ruamel — every load_yaml call falls back to _stdlib_load_yaml.
    monkeypatch.setattr(builtins, "__import__", _block_ruamel)

    catalog_stdlib = decide_mod.load_catalog(str(tmp_path))
    model_stdlib = decide_mod.load_model(str(tmp_path), catalog_stdlib)

    # The stdlib model must contain the deny grant (was None before the fix).
    deny_grants_stdlib = [
        g for g in model_stdlib["grants"]
        if g.get("effect") == "deny" and g.get("subject") == "agent:project-manager"
    ]
    assert deny_grants_stdlib, (
        "stdlib model is missing the deny grant — grants.yaml block-seq mis-parsed "
        "(issue #55 regression: _stdlib_load_yaml returned grants: None)"
    )

    # The real enforcement check: hook_decide must return deny for
    # project-manager gh issue edit (the command that failed live in #53).
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "gh issue edit 53 --body 'new body'"},
        "cwd": "/r",
        "agent_type": "project-manager",
    }
    d, why = decide_mod.hook_decide(model_stdlib, catalog_stdlib, payload)
    assert d == "deny", (
        f"stdlib path must enforce the deny grant for project-manager gh issue edit; "
        f"got {d!r}: {why} — enforcement failed open (issue #55)"
    )
    assert "issue-tracker-write" in why, (
        f"denial reason must name the privilege; got: {why!r}"
    )


# ---- default-agent subject resolution (issue #57) ----------------------------
#
# When the main Claude Code session has no agent_type in the payload (the hook
# only sets it for spawned Task-subagents), the hook must resolve the subject
# from the configured default agent in .claude/settings.json rather than
# unconditionally falling back to "operator".
#
# Without this fix: per-agent grants (e.g. the #53 issue-tracker-write deny on
# agent:project-manager) are inert for the main session because it resolves to
# "operator", not "agent:project-manager".

def _write_settings(root: Path, agent: str) -> None:
    """Write a minimal .claude/settings.json with the given agent value."""
    import json as _json
    claude_dir = root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text(
        _json.dumps({"agent": agent}), encoding="utf-8"
    )


def test_read_default_agent_returns_agent_from_settings(decide_mod, tmp_path):
    """_read_default_agent reads the 'agent' key from .claude/settings.json."""
    _write_settings(tmp_path, "project-manager")
    assert decide_mod._read_default_agent(str(tmp_path)) == "project-manager"


def test_read_default_agent_returns_none_when_file_missing(decide_mod, tmp_path):
    """_read_default_agent returns None when .claude/settings.json does not exist."""
    result = decide_mod._read_default_agent(str(tmp_path))
    assert result is None


def test_read_default_agent_returns_none_when_key_absent(decide_mod, tmp_path):
    """_read_default_agent returns None when settings.json has no 'agent' key."""
    import json as _json
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        _json.dumps({"permissions": {}}), encoding="utf-8"
    )
    assert decide_mod._read_default_agent(str(tmp_path)) is None


def test_read_default_agent_returns_none_on_malformed_json(decide_mod, tmp_path):
    """_read_default_agent returns None (never throws) when settings.json is malformed."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{ not valid json }", encoding="utf-8")
    assert decide_mod._read_default_agent(str(tmp_path)) is None


def test_hook_decide_agent_type_present_unchanged(decide_mod, catalog):
    """agent_type present in payload → subject agent:<type> (existing behaviour unchanged)."""
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "cwd": "/r",
        "agent_type": "project-manager",
    }
    d, why = decide_mod.hook_decide(MODEL, catalog, payload, project_root=None)
    assert d == "allow"
    assert "agent:project-manager" in why


def test_hook_decide_no_agent_type_no_root_falls_back_to_operator(decide_mod, catalog):
    """agent_type absent, no project_root → subject 'operator' (unchanged fallback)."""
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "cwd": "/r",
    }
    d, why = decide_mod.hook_decide(MODEL, catalog, payload)
    assert d == "allow"
    assert "operator" in why


def test_hook_decide_no_agent_type_no_default_agent_falls_back_to_operator(decide_mod, catalog, tmp_path):
    """agent_type absent + settings.json has no 'agent' key → subject 'operator'."""
    # No .claude/settings.json in tmp_path.
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "cwd": "/r",
    }
    d, why = decide_mod.hook_decide(MODEL, catalog, payload, project_root=str(tmp_path))
    assert d == "allow"
    assert "operator" in why


def test_hook_decide_no_agent_type_resolves_from_settings(decide_mod, catalog, tmp_path):
    """agent_type absent + settings.json agent: project-manager → subject agent:project-manager.

    This is the core of the issue #57 fix: a main-session payload (no agent_type)
    is resolved to the configured default agent, so per-agent grants apply.
    """
    _write_settings(tmp_path, "project-manager")
    # git status: allowed for agent:project-manager via the MODEL vcs grant.
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "cwd": "/r",
    }
    d, why = decide_mod.hook_decide(MODEL, catalog, payload, project_root=str(tmp_path))
    assert d == "allow"
    assert "agent:project-manager" in why


def test_hook_decide_no_agent_type_deny_applies_via_default_agent(decide_mod, catalog, tmp_path):
    """agent_type absent + settings.json agent: project-manager + deny grant → deny.

    The per-agent deny on issue-tracker-write for agent:project-manager now applies
    to the main session when no agent_type is present in the payload — the fix that
    makes #53's enforcement work end-to-end for the primary execution context.
    """
    _write_settings(tmp_path, "project-manager")
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "gh issue edit 53 --body 'new body'"},
        "cwd": "/r",
        # No agent_type — simulates a main-session call.
    }
    d, why = decide_mod.hook_decide(_PM_WITH_DENY_MODEL, catalog, payload, project_root=str(tmp_path))
    assert d == "deny", (
        f"deny grant on agent:project-manager must apply to main-session payload "
        f"(no agent_type) when settings.json sets agent: project-manager; got {d!r}: {why}"
    )
    assert "issue-tracker-write" in why


# ---- end-to-end stdlib-path deny for main session (issue #57) ---------------
#
# The live hook runs bare python3 (no ruamel, no uv — ADR-014 / macOS Seatbelt).
# This test proves that with ruamel completely absent:
#   - a main-session payload (no agent_type) with settings.json agent: project-manager
#   - the deny grant in grants.yaml (col-0 block-seq shape)
# resolves the subject to agent:project-manager and returns deny for gh issue edit.
# This is the end-to-end enforcement guard for issue #57.

def test_stdlib_path_default_agent_deny_end_to_end(decide_mod, tmp_path, monkeypatch):
    """End-to-end: stdlib-only path (no ruamel), no agent_type payload, settings.json
    agent: project-manager, deny grant → hook_decide returns deny for gh issue edit.

    This is the enforcement guard for issue #57: the same test as #55's
    test_stdlib_path_enforce_deny_grant_end_to_end but via the DEFAULT-AGENT
    resolution path (no agent_type in payload) rather than the explicit agent_type
    path — proving that the main session finally enforces per-agent denies.
    """
    import builtins
    real_import = builtins.__import__

    def _block_ruamel(name, *args, **kwargs):
        if "ruamel" in name:
            raise ImportError(f"simulated missing ruamel: {name}")
        return real_import(name, *args, **kwargs)

    # Build a tree with the real catalog + deny grant (col-0 block-seq shape).
    _write_tree(
        tmp_path,
        grants=(
            "schema_version: 1\n"
            "grants:\n"
            "- subject: agent:project-manager\n"
            "  privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "  effect: deny\n"
        ),
    )
    # Write settings.json so _read_default_agent returns "project-manager".
    _write_settings(tmp_path, "project-manager")

    # Block ruamel — every load_yaml call falls back to _stdlib_load_yaml.
    monkeypatch.setattr(builtins, "__import__", _block_ruamel)

    catalog_stdlib = decide_mod.load_catalog(str(tmp_path))
    model_stdlib = decide_mod.load_model(str(tmp_path), catalog_stdlib)

    # Main-session payload: NO agent_type — the gap that issue #57 describes.
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "gh issue edit 53 --body 'new body'"},
        "cwd": "/r",
        # Deliberately no agent_type to simulate the main session.
    }
    d, why = decide_mod.hook_decide(
        model_stdlib, catalog_stdlib, payload, project_root=str(tmp_path)
    )
    assert d == "deny", (
        f"stdlib path must resolve default agent from settings.json and enforce the "
        f"deny grant for main-session gh issue edit; got {d!r}: {why} — "
        f"issue #57 fix not working through stdlib fallback"
    )
    assert "issue-tracker-write" in why, (
        f"denial reason must name the privilege; got: {why!r}"
    )


# ---- capability-fragment layer (ADR-016) ------------------------------------
#
# load_model gains a new layer:
#   guardrail_denies + capability_fragment_grants + active_profile_grants + adopter_grants
#
# Discovery walks the manifest components list; an orphan capability directory
# with no manifest entry contributes nothing (install-state-as-gate).
# Capability grants are annotated with _capability for the reporting layer;
# decide() ignores the extra key (it reads only subject/privilege/effect/scope).

CAP_FRAG_PATH = REPO_ROOT_LOCAL / ".pkit" / "capabilities" / "project-management" / "permissions" / "grants.yaml"


def _write_cap_tree(
    root: Path,
    *,
    manifest: str | None = None,
    cap_name: str = "project-management",
    cap_grants: str | None = None,
    project_grants: str | None = None,
    profile_name: str | None = None,
    profile_yaml: str | None = None,
    config: str | None = None,
) -> None:
    """Build a minimal project tree with manifest + capability fragment support."""
    (root / ".pkit" / "schemas").mkdir(parents=True)
    (root / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text(
        CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    if manifest is not None:
        (root / ".pkit" / "manifest.yaml").write_text(manifest, encoding="utf-8")
    if cap_grants is not None:
        cap_perm_dir = root / ".pkit" / "capabilities" / cap_name / "permissions"
        cap_perm_dir.mkdir(parents=True)
        (cap_perm_dir / "grants.yaml").write_text(cap_grants, encoding="utf-8")
    (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
    if project_grants is not None:
        (root / ".pkit" / "permissions" / "project" / "grants.yaml").write_text(
            project_grants, encoding="utf-8"
        )
    if config is not None:
        (root / ".pkit" / "permissions" / "project" / "config.yaml").write_text(
            config, encoding="utf-8"
        )
    if profile_name is not None and profile_yaml is not None:
        pdir = root / ".pkit" / "permissions" / "profiles"
        pdir.mkdir(parents=True)
        (pdir / f"{profile_name}.yaml").write_text(profile_yaml, encoding="utf-8")


def test_capability_fragment_grants_loaded_when_manifest_registered(decide_mod, tmp_path):
    """load_model includes capability fragment grants for manifest-registered capabilities."""
    _write_cap_tree(
        tmp_path,
        manifest=(
            "schema_version: 1\n"
            "backbone_version: 1.0.0\n"
            "components:\n"
            "  - kind: capability\n"
            "    name: project-management\n"
            "    manifest: .pkit/capabilities/project-management/manifest.yaml\n"
        ),
        cap_grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:project-manager\n"
            "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "    effect: deny\n"
        ),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    cap_grants = [
        g for g in model["grants"]
        if g.get("_capability") == "project-management"
    ]
    assert cap_grants, "capability fragment grants must appear in the model"
    assert cap_grants[0]["effect"] == "deny"
    assert cap_grants[0]["subject"] == "agent:project-manager"


def test_orphan_capability_dir_contributes_nothing(decide_mod, tmp_path):
    """An orphan capability directory not registered in the manifest contributes nothing.

    This is the install-state-as-gate invariant (ADR-016 decision 2): only
    manifest-registered components contribute fragments; a leftover directory
    from a botched uninstall or rebase does not change the model.
    """
    # Write a capability fragment at the expected path, but NO manifest entry.
    _write_cap_tree(
        tmp_path,
        manifest=(
            "schema_version: 1\n"
            "backbone_version: 1.0.0\n"
            "components: []\n"
        ),
        cap_grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:project-manager\n"
            "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "    effect: deny\n"
        ),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    cap_grants = [g for g in model["grants"] if g.get("_capability")]
    assert not cap_grants, (
        "orphan capability directory must NOT contribute grants — "
        "only manifest-registered capabilities are install-gated"
    )


def test_capability_deny_survives_autonomous_profile_allow_deny_wins(decide_mod, tmp_path):
    """Pinned dependency test (ADR-016 / critic G-2).

    With the project-management capability installed and the 'autonomous' profile
    active (which grants issue-tracker to all), a raw 'gh issue edit' by
    agent:project-manager still resolves to DENY — proving:

    (a) The capability deny overrides the profile allow via deny-wins (order-independent).
    (b) issue-tracker-write is independently recognized for the mutation command.
    (c) The capability fragment layer sits before the profile layer, but deny-wins
        makes the result invariant to ordering — the deny always surfaces.
    """
    autonomous_profile = (
        "schema_version: 1\n"
        "description: test autonomous\n"
        "posture: lenient\n"
        "grants:\n"
        "  - subject: all\n"
        "    privilege:\n"
        "      - '[privilege-catalog:vcs]'\n"
        "      - '[privilege-catalog:issue-tracker]'\n"
        "      - '[privilege-catalog:kit]'\n"
        "      - '[privilege-catalog:repo-read]'\n"
        "    effect: allow\n"
    )
    _write_cap_tree(
        tmp_path,
        manifest=(
            "schema_version: 1\n"
            "backbone_version: 1.0.0\n"
            "components:\n"
            "  - kind: capability\n"
            "    name: project-management\n"
            "    manifest: .pkit/capabilities/project-management/manifest.yaml\n"
        ),
        cap_grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:project-manager\n"
            "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "    effect: deny\n"
        ),
        profile_name="autonomous",
        profile_yaml=autonomous_profile,
        config=(
            "schema_version: 1\n"
            "ownership_mode: additive\n"
            "posture: lenient\n"
            "active_profile: autonomous\n"
        ),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)

    # Prove (a): the profile grants issue-tracker to all.
    profile_grants = [
        g for g in model["grants"]
        if g.get("subject") == "all" and g.get("effect") == "allow"
        and "issue-tracker" in str(g.get("privilege", ""))
    ]
    assert profile_grants, "autonomous profile must grant issue-tracker to all"

    # Prove (b): issue-tracker-write is recognized for gh issue edit.
    request = _bash("gh issue edit 53 --body 'new'", "agent:project-manager")
    hits = decide_mod.recognized_privileges(catalog, request)
    assert "issue-tracker-write" in hits, (
        f"issue-tracker-write must recognize gh issue edit; got {hits}"
    )

    # Prove (c): deny-wins — the capability deny overrides the profile allow.
    d, why = decide_mod.decide(model, catalog, request)
    assert d == "deny", (
        f"capability deny must override autonomous profile allow via deny-wins; "
        f"got {d!r}: {why}"
    )
    assert "issue-tracker-write" in why


def test_capability_deny_under_autonomous_via_stdlib_path(decide_mod, tmp_path, monkeypatch):
    """Pinned deny-under-autonomous test through the stdlib fallback path.

    Same as test_capability_deny_survives_autonomous_profile_allow_deny_wins but
    with ruamel blocked — proves the enforcement holds through the zero-dep hook's
    actual runtime (ADR-002 / ADR-003 same-code invariant).
    """
    import builtins
    real_import = builtins.__import__

    def _block_ruamel(name, *args, **kwargs):
        if "ruamel" in name:
            raise ImportError(f"simulated missing ruamel: {name}")
        return real_import(name, *args, **kwargs)

    autonomous_profile = (
        "schema_version: 1\n"
        "description: test autonomous\n"
        "posture: lenient\n"
        "grants:\n"
        "  - subject: all\n"
        "    privilege:\n"
        "      - '[privilege-catalog:vcs]'\n"
        "      - '[privilege-catalog:issue-tracker]'\n"
        "      - '[privilege-catalog:kit]'\n"
        "      - '[privilege-catalog:repo-read]'\n"
        "    effect: allow\n"
    )
    _write_cap_tree(
        tmp_path,
        manifest=(
            "schema_version: 1\n"
            "backbone_version: 1.0.0\n"
            "components:\n"
            "  - kind: capability\n"
            "    name: project-management\n"
            "    manifest: .pkit/capabilities/project-management/manifest.yaml\n"
        ),
        cap_grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:project-manager\n"
            "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "    effect: deny\n"
        ),
        profile_name="autonomous",
        profile_yaml=autonomous_profile,
        config=(
            "schema_version: 1\n"
            "ownership_mode: additive\n"
            "posture: lenient\n"
            "active_profile: autonomous\n"
        ),
    )

    monkeypatch.setattr(builtins, "__import__", _block_ruamel)

    catalog_stdlib = decide_mod.load_catalog(str(tmp_path))
    model_stdlib = decide_mod.load_model(str(tmp_path), catalog_stdlib)

    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "gh issue edit 53 --body 'new body'"},
        "cwd": "/r",
        "agent_type": "project-manager",
    }
    d, why = decide_mod.hook_decide(model_stdlib, catalog_stdlib, payload)
    assert d == "deny", (
        f"stdlib path must enforce capability deny even with autonomous profile active; "
        f"got {d!r}: {why}"
    )
    assert "issue-tracker-write" in why


def test_removing_manual_grant_does_not_weaken_enforcement(decide_mod, tmp_path):
    """Removing the manual project grant does not weaken enforcement — the fragment now provides it.

    This is the end-to-end test proving that with the capability installed and
    the project grants.yaml empty (grants: []), the deny still comes from the
    capability fragment and hook_decide still returns deny for gh issue edit.
    """
    _write_cap_tree(
        tmp_path,
        manifest=(
            "schema_version: 1\n"
            "backbone_version: 1.0.0\n"
            "components:\n"
            "  - kind: capability\n"
            "    name: project-management\n"
            "    manifest: .pkit/capabilities/project-management/manifest.yaml\n"
        ),
        cap_grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:project-manager\n"
            "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "    effect: deny\n"
        ),
        # Empty project grants — the manual deny is gone.
        project_grants="schema_version: 1\ngrants: []\n",
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)

    # No manual deny in model (project grants empty).
    manual_denies = [
        g for g in model["grants"]
        if g.get("subject") == "agent:project-manager"
        and g.get("effect") == "deny"
        and not g.get("_capability")
    ]
    assert not manual_denies, "no manual deny should be present — only the capability fragment"

    # But enforcement still holds via the fragment.
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "gh issue edit 53 --body 'new body'"},
        "cwd": "/r",
        "agent_type": "project-manager",
    }
    d, why = decide_mod.hook_decide(model, catalog, payload)
    assert d == "deny", (
        f"capability fragment must provide the deny even with empty project grants; "
        f"got {d!r}: {why}"
    )
    assert "issue-tracker-write" in why


def test_capability_fragment_grants_annotated_with_capability_key(decide_mod, tmp_path):
    """Capability fragment grants carry the _capability annotation for the reporting layer.

    The _capability annotation is how pkit permissions overview / explain
    surfaces 'contributed by capability: <name>' (ADR-016 narrowing-but-reported).
    decide() ignores the extra key — it only reads subject/privilege/effect/scope.
    """
    _write_cap_tree(
        tmp_path,
        manifest=(
            "schema_version: 1\n"
            "backbone_version: 1.0.0\n"
            "components:\n"
            "  - kind: capability\n"
            "    name: project-management\n"
            "    manifest: .pkit/capabilities/project-management/manifest.yaml\n"
        ),
        cap_grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:project-manager\n"
            "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "    effect: deny\n"
        ),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)

    cap_grants = [g for g in model["grants"] if g.get("_capability")]
    assert cap_grants, "capability grants must carry the _capability annotation"
    assert cap_grants[0]["_capability"] == "project-management"

    # decide() must still work with the annotated grant (the extra key is ignored).
    d, why = decide_mod.decide(
        model, catalog,
        _bash("gh issue edit 53", "agent:project-manager"),
    )
    assert d == "deny", f"decide() must work with _capability-annotated grants; got {d!r}: {why}"


def test_capability_fragment_layered_before_profile_and_adopter(decide_mod, tmp_path):
    """Capability fragments sit before the profile and adopter grants in the model.

    ADR-016 decision 1: ordering is guardrails → capability fragments → profile →
    adopter. This test verifies the positional ordering in the grants list.
    """
    _write_cap_tree(
        tmp_path,
        manifest=(
            "schema_version: 1\n"
            "backbone_version: 1.0.0\n"
            "components:\n"
            "  - kind: capability\n"
            "    name: project-management\n"
            "    manifest: .pkit/capabilities/project-management/manifest.yaml\n"
        ),
        cap_grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:project-manager\n"
            "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
            "    effect: deny\n"
        ),
        profile_name="team",
        profile_yaml=(
            "schema_version: 1\n"
            "description: team\n"
            "posture: lenient\n"
            "grants:\n"
            "  - subject: all\n"
            "    privilege: '[privilege-catalog:vcs]'\n"
            "    effect: allow\n"
        ),
        config=(
            "schema_version: 1\n"
            "ownership_mode: additive\n"
            "posture: lenient\n"
            "active_profile: team\n"
        ),
        project_grants=(
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: agent:critic\n"
            "    privilege: '[privilege-catalog:repo-read]'\n"
            "    effect: allow\n"
        ),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    grants = model["grants"]

    cap_idx = next(
        i for i, g in enumerate(grants)
        if g.get("_capability") == "project-management"
    )
    profile_idx = next(
        i for i, g in enumerate(grants)
        if g.get("subject") == "all" and g.get("effect") == "allow"
        and not g.get("_capability")
    )
    adopter_idx = next(
        i for i, g in enumerate(grants)
        if g.get("subject") == "agent:critic"
    )
    assert cap_idx < profile_idx, (
        "capability fragment must come before profile grants in the model"
    )
    assert profile_idx < adopter_idx, (
        "profile grants must come before adopter grants in the model"
    )


def test_stdlib_fallback_parses_capability_fragment_identically_to_ruamel(decide_mod):
    """The stdlib fallback must parse the shipped capability fragment identically to ruamel.

    Same-code invariant (ADR-002): if the hook runs in a macOS Seatbelt context
    without ruamel, it must parse the capability fragment file through
    _stdlib_load_yaml and get byte-identical results.
    """
    try:
        from ruamel.yaml import YAML
        import io
        yaml = YAML(typ="safe")
    except ImportError:
        pytest.skip("ruamel.yaml not available")

    text = CAP_FRAG_PATH.read_text(encoding="utf-8")
    ruamel_result = yaml.load(io.StringIO(text)) or {}
    stdlib_result = decide_mod._stdlib_load_yaml(text)
    assert stdlib_result == ruamel_result, (
        f"stdlib fallback parse differs from ruamel for capability grants.yaml:\n"
        f"  stdlib: {stdlib_result!r}\n"
        f"  ruamel: {ruamel_result!r}"
    )


# ---- capability-CATALOG-fragment merge (ADR-021) ----------------------------
#
# load_catalog merges installed capabilities' privilege-catalog fragments into
# the backbone catalog under an additive-only, collision-rejecting,
# guardrail-forbidding rule. The merge lives in load_catalog (not load_model) so
# the hook and the CLI both decide on the identical merged catalog and
# guardrail_denies runs on the merged result. Discovery walks the manifest
# components list (orphan dirs contribute nothing). A capability id is rewritten
# to <cap>:<name> and the spec is stamped provenance: capability:<name>.

_MANIFEST_WITH_CAP = (
    "schema_version: 1\n"
    "backbone_version: 1.0.0\n"
    "components:\n"
    "  - kind: capability\n"
    "    name: trip-planning\n"
    "    manifest: .pkit/capabilities/trip-planning/manifest.yaml\n"
)


def _write_catalog_fragment_tree(
    root: Path,
    *,
    manifest: str | None = _MANIFEST_WITH_CAP,
    cap_name: str = "trip-planning",
    fragment: str | None = None,
    project_grants: str | None = None,
) -> None:
    """Build a project tree with a backbone catalog + a capability catalog fragment."""
    (root / ".pkit" / "schemas").mkdir(parents=True)
    (root / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text(
        CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    if manifest is not None:
        (root / ".pkit" / "manifest.yaml").write_text(manifest, encoding="utf-8")
    if fragment is not None:
        frag_dir = root / ".pkit" / "capabilities" / cap_name / "permissions"
        frag_dir.mkdir(parents=True)
        (frag_dir / "privilege-catalog.yaml").write_text(fragment, encoding="utf-8")
    (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
    if project_grants is not None:
        (root / ".pkit" / "permissions" / "project" / "grants.yaml").write_text(
            project_grants, encoding="utf-8"
        )


_SCRAPER_FRAGMENT = (
    "schema_version: 1\n"
    "privileges:\n"
    "  ad-hoc-scraping:\n"
    "    description: Raw shell scrapers a researcher reflexively reaches for.\n"
    "    recognize:\n"
    "      bash:\n"
    "        - cmd: curl\n"
    "        - cmd: wget\n"
)


def test_fragment_privilege_merged_when_capability_installed(decide_mod, tmp_path):
    """An installed capability's fragment privilege is merged, scoped, and stamped."""
    _write_catalog_fragment_tree(tmp_path, fragment=_SCRAPER_FRAGMENT)
    catalog = decide_mod.load_catalog(str(tmp_path))
    privileges = catalog["privileges"]
    assert "trip-planning:ad-hoc-scraping" in privileges, (
        "fragment id must be merged under its capability-scoped key"
    )
    assert "ad-hoc-scraping" not in privileges, (
        "the bare (unscoped) id must NOT appear — only the scoped key"
    )
    assert privileges["trip-planning:ad-hoc-scraping"]["provenance"] == "capability:trip-planning"
    # Backbone privileges are untouched.
    assert "vcs" in privileges and "destructive-fs" in privileges


def test_orphan_catalog_fragment_dir_contributes_nothing(decide_mod, tmp_path):
    """A fragment present on disk but not manifest-registered contributes nothing."""
    _write_catalog_fragment_tree(
        tmp_path,
        manifest="schema_version: 1\nbackbone_version: 1.0.0\ncomponents: []\n",
        fragment=_SCRAPER_FRAGMENT,
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    assert "trip-planning:ad-hoc-scraping" not in catalog["privileges"], (
        "orphan (non-manifest-registered) fragment must NOT merge — install-gated"
    )


def test_fragment_colliding_with_backbone_id_rejected(decide_mod, tmp_path):
    """A fragment id that, once scoped, would still need a backbone slot is dropped;
    and a fragment cannot overwrite a backbone privilege via id collision.

    Scoping makes a raw backbone-name collision impossible, so we force the
    collision directly: name the capability so its scoped id equals a backbone
    id is not constructible — instead assert the scoped id never overwrites
    the backbone recognizer (the real safety property)."""
    # Fragment tries to redefine `vcs` (a backbone id). Scoped, it becomes
    # `trip-planning:vcs` — which does NOT collide — so the backbone `vcs` recognizer
    # must be intact and the scoped variant is a separate, inert id.
    fragment = (
        "schema_version: 1\n"
        "privileges:\n"
        "  vcs:\n"
        "    description: hijack attempt.\n"
        "    recognize:\n"
        "      bash:\n"
        "        - cmd: echo\n"
    )
    _write_catalog_fragment_tree(tmp_path, fragment=fragment)
    catalog = decide_mod.load_catalog(str(tmp_path))
    # Backbone `vcs` recognizer is untouched (still matches git, not echo).
    assert catalog["privileges"]["vcs"]["recognize"]["bash"] == [{"cmd": "git"}], (
        "a fragment must never overwrite a backbone privilege's recognizer"
    )


def test_fragment_id_collision_with_backbone_scoped_name_rejected(decide_mod, tmp_path):
    """When a scoped fragment id WOULD collide with an existing key, it is rejected
    (dropped, not overwriting) and the rejection is surfaced on the catalog."""
    # Pre-seed the backbone catalog with a key that equals the scoped form the
    # fragment will produce, to exercise the collision branch directly.
    (tmp_path / ".pkit" / "schemas").mkdir(parents=True)
    backbone = (
        "schema_version: 1\n"
        "privileges:\n"
        "  'trip-planning:ad-hoc-scraping':\n"
        "    description: pre-existing backbone entry.\n"
        "    recognize:\n"
        "      bash:\n"
        "        - cmd: ls\n"
    )
    (tmp_path / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text(
        backbone, encoding="utf-8"
    )
    (tmp_path / ".pkit" / "manifest.yaml").write_text(_MANIFEST_WITH_CAP, encoding="utf-8")
    frag_dir = tmp_path / ".pkit" / "capabilities" / "trip-planning" / "permissions"
    frag_dir.mkdir(parents=True)
    (frag_dir / "privilege-catalog.yaml").write_text(_SCRAPER_FRAGMENT, encoding="utf-8")

    catalog = decide_mod.load_catalog(str(tmp_path))
    # The pre-existing entry is intact (not overwritten by the fragment).
    assert catalog["privileges"]["trip-planning:ad-hoc-scraping"]["recognize"]["bash"] == [
        {"cmd": "ls"}
    ], "collision must drop the fragment entry, never overwrite the existing one"
    rejections = catalog.get("_fragment_rejections") or []
    assert any("collides" in r for r in rejections), (
        "a collision must be surfaced on the catalog (visibility — ADR-021 §6)"
    )


def test_fragment_guardrail_rejected(decide_mod, tmp_path):
    """A fragment privilege carrying guardrail: true is rejected (dropped), never
    merged — a capability may not install a deny that applies to every adopter."""
    fragment = (
        "schema_version: 1\n"
        "privileges:\n"
        "  forbidden-floor:\n"
        "    description: sneaky global deny.\n"
        "    guardrail: true\n"
        "    recognize:\n"
        "      bash:\n"
        "        - cmd: ssh\n"
    )
    _write_catalog_fragment_tree(tmp_path, fragment=fragment)
    catalog = decide_mod.load_catalog(str(tmp_path))
    assert "trip-planning:forbidden-floor" not in catalog["privileges"], (
        "a guardrail-bearing fragment privilege must NOT merge"
    )
    rejections = catalog.get("_fragment_rejections") or []
    assert any("guardrail" in r for r in rejections), (
        "a rejected guardrail must be surfaced (visibility — ADR-021 §6)"
    )
    # And it never becomes a global deny: guardrail_denies sees only backbone.
    denies = decide_mod.guardrail_denies(catalog)
    assert not any(
        "forbidden-floor" in str(g.get("privilege")) for g in denies
    ), "a rejected fragment guardrail must never synthesize a global deny"


def test_scoped_token_round_trips_deny_binds_not_fail_open(decide_mod, tmp_path):
    """The load-bearing fail-open guard: a deny grant referencing a scoped
    fragment privilege by its `[privilege-catalog:<cap>:<name>]` token must
    actually bind to the merged privilege (deny), not resolve to nothing.

    A mis-resolved scoped token would empty the grant's privilege match and the
    deny would silently not bind (fail-open). This proves exact round-trip."""
    project_grants = (
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: agent:researcher\n"
        "    privilege: '[privilege-catalog:trip-planning:ad-hoc-scraping]'\n"
        "    effect: deny\n"
    )
    _write_catalog_fragment_tree(
        tmp_path, fragment=_SCRAPER_FRAGMENT, project_grants=project_grants
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    # The token must normalise to the scoped catalog key exactly.
    assert decide_mod._privilege_ids(
        "[privilege-catalog:trip-planning:ad-hoc-scraping]"
    ) == {"trip-planning:ad-hoc-scraping"}
    # The deny binds: researcher running `curl …` is DENIED.
    decision, reason = decide_mod.decide(
        model, catalog,
        {"type": "bash", "command": "curl https://example.com",
         "cwd": "/r", "subject": "agent:researcher"},
    )
    assert decision == "deny", f"scoped deny must bind, got {decision} ({reason})"


def test_recognizer_overlap_deny_wins_per_subject(decide_mod, tmp_path):
    """A fragment recognizer may overlap a command another privilege also matches.
    Both ids hit; deny-wins composition applies per the subject's grants — the
    capability fences only the subjects its own deny grant names."""
    # Fragment recognizes `git` (overlapping the backbone vcs privilege).
    fragment = (
        "schema_version: 1\n"
        "privileges:\n"
        "  scm-scrape:\n"
        "    description: overlaps vcs on git.\n"
        "    recognize:\n"
        "      bash:\n"
        "        - cmd: git\n"
    )
    project_grants = (
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: agent:researcher\n"
        "    privilege: '[privilege-catalog:trip-planning:scm-scrape]'\n"
        "    effect: deny\n"
        "  - subject: agent:builder\n"
        "    privilege: '[privilege-catalog:vcs]'\n"
        "    effect: allow\n"
    )
    _write_catalog_fragment_tree(
        tmp_path, fragment=fragment, project_grants=project_grants
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    # researcher is denied git (the overlapping fragment deny binds).
    d_res, _ = decide_mod.decide(
        model, catalog,
        {"type": "bash", "command": "git status", "cwd": "/r", "subject": "agent:researcher"},
    )
    assert d_res == "deny", "the capability's deny fences ITS named subject on the overlap"
    # builder is unaffected — it has a vcs allow and no scm-scrape deny.
    d_build, _ = decide_mod.decide(
        model, catalog,
        {"type": "bash", "command": "git status", "cwd": "/r", "subject": "agent:builder"},
    )
    assert d_build == "allow", "a third party is NOT narrowed by a capability's deny"


def test_no_fragment_no_manifest_is_inert(decide_mod, tmp_path):
    """With no manifest at all, load_catalog returns the backbone catalog unchanged."""
    (tmp_path / ".pkit" / "schemas").mkdir(parents=True)
    (tmp_path / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text(
        CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    assert "vcs" in catalog["privileges"]
    assert "_fragment_rejections" not in catalog


def test_stdlib_fallback_parses_catalog_fragment_identically_to_ruamel(decide_mod, tmp_path):
    """Same-code invariant (ADR-002): the stdlib fallback must merge a catalog
    fragment identically to the ruamel path, so the macOS-Seatbelt hook decides
    the same as the CLI."""
    try:
        from ruamel.yaml import YAML  # noqa: F401
    except ImportError:
        pytest.skip("ruamel.yaml not available")
    stdlib_result = decide_mod._stdlib_load_yaml(_SCRAPER_FRAGMENT)
    import io
    from ruamel.yaml import YAML as _Y
    ruamel_result = _Y(typ="safe").load(io.StringIO(_SCRAPER_FRAGMENT)) or {}
    assert stdlib_result == ruamel_result


# ---- leading-cd strip (ADR-025 Phase 1 / issue #240) ------------------------
#
# A compound Bash command whose FIRST segment is a bare `cd <path>` followed by
# `&&` / `;` has the cd stripped, and the remainder is decided against the
# unchanged grant model. The strip is a prompt-reduction over already-granted
# intent (`cd src && gh pr list` auto-approves as `gh pr list` would), NEVER a
# new grant. It inherits ADR-004 dp-4 fail-closed-on-uncertainty wholesale: a
# remainder carrying a quote / `$()` / backtick / `<` / `>` redirection ABSTAINS
# (prompts), never auto-allows. Deny-wins is unchanged — a deny in the full
# command (a tricky quoted cd) or in the remainder (rm -rf) still binds.
#
# MODEL grants `operator` issue-tracker (gh) + vcs + kit + repo-read; baseline
# guardrail denies cover destructive-fs / privilege-escalation / vcs-history-rewrite.


def test_strip_leading_cd_returns_remainder_for_bare_cd(decide_mod):
    """A bare `cd <path> &&` / `cd <path> ;` prefix is stripped to the remainder."""
    assert decide_mod._strip_leading_cd("cd /x && gh pr list") == "gh pr list"
    assert decide_mod._strip_leading_cd("cd src; gh pr list") == "gh pr list"
    assert decide_mod._strip_leading_cd("cd ../rel && git status") == "git status"


def test_strip_leading_cd_does_not_strip_complex_cd(decide_mod):
    """A cd that is anything more than a bare single-path arg is NOT stripped
    (returns None → fall through). Quotes, substitution, backtick, redirection,
    flags, and multi-arg cd all defeat the strip — conservatism by abstention."""
    assert decide_mod._strip_leading_cd('cd "/x; rm -rf ~" && gh pr list') is None
    assert decide_mod._strip_leading_cd("cd $(pwd) && gh pr list") is None
    assert decide_mod._strip_leading_cd("cd `pwd` && gh pr list") is None
    assert decide_mod._strip_leading_cd("cd -P /x && gh pr list") is None  # flag
    assert decide_mod._strip_leading_cd("cd a b && gh pr list") is None    # two args
    assert decide_mod._strip_leading_cd("cd /x | gh pr list") is None      # not && / ;
    assert decide_mod._strip_leading_cd("cd /x") is None                   # no remainder
    assert decide_mod._strip_leading_cd("gh pr list") is None              # no leading cd


def test_cd_prefix_then_granted_gh_auto_approves(decide_mod, catalog):
    """`cd /x && gh pr list` (gh granted) auto-approves — the prompt the leading
    cd used to force is gone. This is the headline ADR-025 case."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && gh pr list", "operator"))
    assert d == "allow", why


def test_cd_prefix_does_not_weaken_destructive_deny(decide_mod, catalog):
    """`cd /x && rm -rf /` still DENIES — stripping cd never weakens a deny; the
    remainder rm -rf is itself recognized as destructive-fs and the guardrail binds."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && rm -rf /", "operator"))
    assert d == "deny", why
    assert "destructive-fs" in why


def test_cd_prefix_with_redirection_in_remainder_abstains(decide_mod, catalog):
    """`cd /x && echo z > ~/f` ABSTAINS — the `>` redirection in the remainder is
    a construct the dumb splitter can't be trusted on, so fail closed (never
    auto-allow), per ADR-004 dp-4."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && echo z > ~/f", "operator"))
    assert d == "abstain", why
    assert "untrusted" in why.lower() or "fail closed" in why.lower()


def test_tricky_quoted_cd_is_not_stripped_and_never_silently_allowed(decide_mod, catalog):
    """`cd "/x; rm -rf ~" && gh pr list` — the quoted cd is NOT a bare cd, so it is
    NOT stripped. It falls through to the full-command path, where the dumb
    splitter leaks the `rm -rf ~` into a segment and the destructive-fs guardrail
    denies. The one property that MUST hold: never a silent auto-allow."""
    d, why = decide_mod.decide(
        MODEL, catalog, _bash('cd "/x; rm -rf ~" && gh pr list', "operator")
    )
    assert d != "allow", f"a tricky quoted cd must never silently auto-allow; got {d!r}: {why}"


def test_cd_prefix_with_command_substitution_in_remainder_abstains(decide_mod, catalog):
    """`cd /x && gh $(rm -rf ~)` ABSTAINS — the `$()` substitution smuggles a
    second command the per-segment matcher cannot see, so fail closed. (This is a
    TIGHTENING: the pre-ADR-025 dumb path would have matched the bare `gh` and
    auto-allowed it.)"""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && gh $(rm -rf ~)", "operator"))
    assert d == "abstain", why
    assert "untrusted" in why.lower() or "fail closed" in why.lower()


def test_cd_prefix_with_backtick_in_remainder_abstains(decide_mod, catalog):
    """A backtick in the remainder of a cd-stripped compound also fails closed."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && gh `rm -rf ~`", "operator"))
    assert d == "abstain", why


def test_bare_cd_with_no_granted_remainder_abstains(decide_mod, catalog):
    """A bare `cd /x` with no separator/remainder is not a strip case; it falls
    through and abstains (cd matches no grant; lenient posture defers)."""
    d, _ = decide_mod.decide(MODEL, catalog, _bash("cd /x", "operator"))
    assert d == "abstain"


def test_cd_prefix_then_ungranted_remainder_abstains(decide_mod, catalog):
    """`cd /x && <ungranted>` abstains — the strip reveals the remainder, which
    matches no allow grant, so lenient posture defers (no new grant invented)."""
    d, _ = decide_mod.decide(MODEL, catalog, _bash("cd /x && unknowncmd --flag", "operator"))
    assert d == "abstain"


def test_cd_prefix_then_ungranted_remainder_denies_under_strict(decide_mod, catalog):
    """Under strict posture the ungranted remainder of a cd-stripped compound
    denies — the strip changes only WHICH command is decided, not the posture."""
    d, _ = decide_mod.decide(
        MODEL, catalog, _bash("cd /x && unknowncmd --flag", "operator"), posture="strict"
    )
    assert d == "deny"


def test_cd_prefix_composes_with_env_prefix_strip(decide_mod, catalog):
    """`cd /x && export Y=1 && gh pr list` allows — after the cd strip the
    remainder `export Y=1 && gh pr list` re-enters decide(), where the existing
    env-prefix strip in segments() handles the export. The two strips compose."""
    d, why = decide_mod.decide(
        MODEL, catalog, _bash("cd /x && export Y=1 && gh pr list", "operator")
    )
    assert d == "allow", why


def test_chained_cd_strips_to_final_granted_command(decide_mod, catalog):
    """Chained bare cds (`cd /a && cd /b && gh pr list`) strip recursively to the
    final granted command — each cd is only a cwd change, never a grant."""
    d, why = decide_mod.decide(
        MODEL, catalog, _bash("cd /a && cd /b && gh pr list", "operator")
    )
    assert d == "allow", why


# ---- pipe-in-remainder: inherited porosity, unchanged by the cd-strip -------
#
# `|` is NOT in `_UNTRUSTED` (it does not force an abstain). Pipe handling is
# inherited UNCHANGED from the bare-command path — `segments()` already splits
# on `|` and matches the granted first segment. These tests pin that behavior so
# a future `_UNTRUSTED` edit can't silently flip it (the rationale lives at the
# `_UNTRUSTED` definition in decide.py). The cd-strip neither creates nor worsens
# pipe porosity; the real boundary for `| sh` is the OS sandbox (ADR-004).


def test_cd_prefix_then_legitimate_pipe_allows(decide_mod, catalog):
    """`cd /x && gh pr list | jq .` ALLOWS — the legitimate-pipe win is preserved.
    `gh` is granted (issue-tracker); the `jq` segment matches no grant but a
    non-match is not a deny, so the granted first segment carries the allow. A
    quote-free `jq .` is used so the win, not the `_UNTRUSTED` abstain, is what's
    pinned. The cd-strip leaves the pipe untouched."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && gh pr list | jq .", "operator"))
    assert d == "allow", why


def test_cd_prefix_then_pipe_to_destructive_denies(decide_mod, catalog):
    """`cd /x && gh pr list | rm -rf ~` DENIES — deny-wins survives a pipe through
    the cd-strip recursion: the `rm -rf` segment hits the destructive-fs guardrail
    after the leading cd is stripped."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && gh pr list | rm -rf ~", "operator"))
    assert d == "deny", why
    assert "destructive-fs" in why


def test_cd_prefix_then_pipe_to_shell_matches_bare_form(decide_mod, catalog):
    """`cd /x && gh pr list | sh` resolves to EXACTLY the bare `gh pr list | sh`
    verdict — proving the cd-strip is verdict-preserving over a pipe-to-shell. The
    `| sh` porosity (whatever it is today) is INHERITED from the bare-command path,
    not a cd-strip artifact; `|` is deliberately absent from `_UNTRUSTED`. The real
    boundary for `| sh` is the OS sandbox (ADR-004)."""
    cd_decision, cd_why = decide_mod.decide(
        MODEL, catalog, _bash("cd /x && gh pr list | sh", "operator")
    )
    bare_decision, _ = decide_mod.decide(
        MODEL, catalog, _bash("gh pr list | sh", "operator")
    )
    assert cd_decision == bare_decision, (
        f"cd-prefixed pipe-to-shell must match the bare form's verdict; "
        f"got cd={cd_decision!r}, bare={bare_decision!r}: {cd_why}"
    )


def test_cd_strip_hook_and_decide_parity(decide_mod, catalog):
    """The cd-strip lives in the shared core, so hook_decide and decide agree on
    a cd-prefixed compound (ADR-002 / ADR-003 same-code invariant)."""
    cmd = "cd /x && gh pr list"
    d_decide, _ = decide_mod.decide(MODEL, catalog, _bash(cmd, "operator"))
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "/r"}
    d_hook, _ = decide_mod.hook_decide(MODEL, catalog, payload)  # no agent_type → operator
    assert d_decide == d_hook == "allow"
