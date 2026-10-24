"""Conformance fixtures for the permission decision core (.pkit/permissions/decide.py).

Loads the REAL baseline privilege catalog (.pkit/schemas/privilege-catalog.yaml)
and runs the truth table the design (COR-028 Q1-Q4) and ADR-002's same-code
invariant require. The hook and the `pkit permissions` CLI both import this
module, so these fixtures are the shared proof they decide identically.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

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
        {
            "subject": "operator",
            "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit"), _tok("repo-read")],
            "effect": "allow",
        },
        {
            "subject": "agent:project-manager",
            "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit")],
            "effect": "allow",
        },
        {
            "subject": "agent:critic",
            "privilege": [_tok("repo-read"), _tok("web-fetch")],
            "effect": "allow",
        },
        {
            "subject": "agent:devops",
            "privilege": _tok("docker"),
            "scope": ["services/**", "deploy/**"],
            "effect": "allow",
        },
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
    d, _ = decide_mod.decide(
        MODEL, catalog, _bash("export GH_HOST=x && gh pr list", "agent:project-manager")
    )
    assert d == "allow"


def test_devops_docker_inside_scope_allow(decide_mod, catalog):
    d, _ = decide_mod.decide(
        MODEL, catalog, _bash("docker run img", "agent:devops", cwd="services/api")
    )
    assert d == "allow"


def test_devops_docker_outside_scope_deny(decide_mod, catalog):
    d, why = decide_mod.decide(
        MODEL, catalog, _bash("docker run img", "agent:devops", cwd="secret/vault")
    )
    assert d == "deny"  # deny-outside-scope
    assert "scope" in why.lower() or "only in" in why.lower()


def test_sudo_denied_for_everyone(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("sudo rm x", "agent:project-manager"))
    assert d == "deny"


def test_rm_rf_denied(decide_mod, catalog):
    d, _ = decide_mod.decide(MODEL, catalog, _bash("rm -rf /tmp/x", "operator"))
    assert d == "deny"


def test_force_push_denied_deny_wins(decide_mod, catalog):
    # pm has vcs allow; git push --force also matches vcs-history-rewrite (baseline deny) -> deny
    # wins.
    d, _ = decide_mod.decide(
        MODEL, catalog, _bash("git push --force origin main", "agent:project-manager")
    )
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
        {
            "subject": "agent:researcher",
            "privilege": _tok("web-fetch"),
            "scope": ["docs.python.org"],
            "effect": "allow",
        },
        # domain-scoped web-fetch: glob — any subdomain of example.com
        {
            "subject": "agent:analyst",
            "privilege": _tok("web-fetch"),
            "scope": ["*.example.com"],
            "effect": "allow",
        },
    ],
}


def test_domain_scope_matching_host_allowed(decide_mod, catalog):
    """A WebFetch request whose host exactly matches the scope glob is allowed."""
    d, _ = decide_mod.decide(
        _DOMAIN_MODEL,
        catalog,
        _tool("WebFetch", "agent:researcher", url="https://docs.python.org/3/library/fnmatch.html"),
    )
    assert d == "allow"


def test_domain_scope_non_matching_host_denied(decide_mod, catalog):
    """A WebFetch request whose host does NOT match the scope glob is denied."""
    d, why = decide_mod.decide(
        _DOMAIN_MODEL,
        catalog,
        _tool("WebFetch", "agent:researcher", url="https://evil.example.com/steal"),
    )
    assert d == "deny"
    assert "domain-scope" in why.lower() or "does not match" in why.lower()


def test_domain_scope_wildcard_glob_matching_host_allowed(decide_mod, catalog):
    """A host matched by a wildcard glob (*.example.com) is allowed."""
    d, _ = decide_mod.decide(
        _DOMAIN_MODEL,
        catalog,
        _tool("WebFetch", "agent:analyst", url="https://api.example.com/data"),
    )
    assert d == "allow"


def test_domain_scope_wildcard_glob_non_matching_host_denied(decide_mod, catalog):
    """A host that doesn't match the wildcard glob is denied."""
    d, why = decide_mod.decide(
        _DOMAIN_MODEL,
        catalog,
        _tool("WebFetch", "agent:analyst", url="https://api.notexample.com/data"),
    )
    assert d == "deny"
    assert "domain-scope" in why.lower() or "does not match" in why.lower()


def test_domain_scope_missing_url_denied(decide_mod, catalog):
    """A domain-scoped grant with no URL in the request is denied (can't check host)."""
    d, why = decide_mod.decide(
        _DOMAIN_MODEL,
        catalog,
        _tool("WebFetch", "agent:researcher"),  # no url kwarg
    )
    assert d == "deny"
    assert "hostname" in why.lower() or "url" in why.lower()


def test_domain_scope_deny_glob_rejected(decide_mod, catalog):
    """A negation/deny scope glob (starting with '!') is explicitly rejected, not silently
    applied."""
    deny_glob_model = {
        "posture": "lenient",
        "grants": [
            {
                "subject": "agent:researcher",
                "privilege": _tok("web-fetch"),
                "scope": ["!*.ru"],
                "effect": "allow",
            },
        ],
    }
    d, why = decide_mod.decide(
        deny_glob_model,
        catalog,
        _tool("WebFetch", "agent:researcher", url="https://docs.python.org/"),
    )
    assert d == "deny"
    # The rejection message must name the unsupported negation, not silently ignore it.
    assert "unsupported" in why.lower() or "negation" in why.lower() or "deny" in why.lower()


def test_directory_scope_unchanged_inside(decide_mod, catalog):
    """Directory-scope behaviour is unchanged: a request inside the scope is allowed."""
    d, _ = decide_mod.decide(
        MODEL, catalog, _bash("docker run img", "agent:devops", cwd="services/api")
    )
    assert d == "allow"


def test_directory_scope_unchanged_outside(decide_mod, catalog):
    """Directory-scope behaviour is unchanged: a request outside the scope is denied."""
    d, why = decide_mod.decide(
        MODEL, catalog, _bash("docker run img", "agent:devops", cwd="secret/vault")
    )
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
            {
                "subject": "agent:researcher",
                "privilege": _tok("web-fetch"),
                "scope": ["docs.python.org"],
                "effect": "allow",
            },
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
            {
                "subject": "agent:researcher",
                "privilege": _tok("web-fetch"),
                "scope": ["docs.python.org"],
                "effect": "allow",
            },
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
    payload = {
        "tool_name": "WebFetch",
        "tool_input": {"url": "https://x"},
        "cwd": "/r",
        "agent_type": "critic",
    }
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
            '    privilege: "[privilege-catalog:web-fetch]"\n'
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


@pytest.mark.parametrize(
    "cmd",
    [
        "rm -rf x",
        "rm -fr x",
        "rm -r x",
        "rm -R x",
        "rm -fR x",
        "rm -Rf x",
        "rm -rfv x",
        "rm --recursive x",
        "rm --recursive=true x",
        "rm -i -R x",
        "export Y=1 && rm -R x",
    ],
)
def test_recursive_rm_denied_any_form(decide_mod, catalog, cmd):
    assert "destructive-fs" in decide_mod.recognized_privileges(catalog, _bash(cmd, "operator"))
    d, _ = decide_mod.decide(MODEL, catalog, _bash(cmd, "operator"))
    assert d == "deny", cmd


@pytest.mark.parametrize(
    "cmd",
    [
        "rm x",
        "rm -f x",
        "rm -i x",
        "rm --force x",
        "rm ./-r-named-file",
        "rm-foo -r x",  # a DIFFERENT binary whose name starts with rm — not our rm
    ],
)
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
        profile=(
            "schema_version: 1\ndescription: t\nposture: lenient\n"
            'grants:\n  - subject: all\n    privilege: "[privilege-catalog:vcs]"\n'
            "    effect: allow\n"
        ),
        config=(
            "schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: team\n"
        ),
        grants=(
            "schema_version: 1\ngrants:\n  - subject: agent:critic\n"
            '    privilege: "[privilege-catalog:repo-read]"\n    effect: allow\n'
        ),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    assert model["active_profile"] == "team"
    ids = [next(iter(decide_mod._privilege_ids(g["privilege"]))) for g in model["grants"]]
    # guardrails (sorted) → profile → adopter, in that order
    assert ids == [
        "destructive-fs",
        "privilege-escalation",
        "vcs-history-rewrite",
        "vcs",
        "repo-read",
    ]
    # the profile's `all` vcs grant decides live
    d, _ = decide_mod.decide(model, catalog, _bash("git status", "operator"))
    assert d == "allow"


def test_profile_grants_annotated_with_profile_key(decide_mod, tmp_path):
    # ADR-046: profile-layer grants carry `_profile: <name>` (mirroring the
    # `_capability` annotation) as `apply`'s routing key. Never stripped —
    # decide() reads only subject/privilege/effect/scope and ignores it.
    _profile_tree(
        tmp_path,
        profile=(
            "schema_version: 1\ndescription: t\nposture: lenient\n"
            'grants:\n  - subject: all\n    privilege: "[privilege-catalog:vcs]"\n'
            "    effect: allow\n"
        ),
        config=(
            "schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: team\n"
        ),
    )
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    profile_grants = [g for g in model["grants"] if g.get("_profile")]
    assert len(profile_grants) == 1
    assert profile_grants[0]["_profile"] == "team"
    # decide() is unaffected by the annotation.
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


def _profile_sidecar_tree(root: Path, *, profile_name: str, sidecar: str | None, config: str):
    (root / ".pkit" / "schemas").mkdir(parents=True)
    (root / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text(
        CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    pdir = root / ".pkit" / "permissions" / "project" / "profiles"
    pdir.mkdir(parents=True)
    (pdir / f"{profile_name}.yaml").write_text(
        "schema_version: 1\ndescription: t\nposture: lenient\n"
        'grants:\n  - subject: all\n    privilege: "[privilege-catalog:vcs]"\n'
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
        tmp_path,
        profile_name="team",
        sidecar="schema_version: 1\nactive_profile: team\n",
        config="schema_version: 1\nownership_mode: additive\nposture: lenient\n",
    )
    cfg = decide_mod.load_yaml(str(tmp_path / ".pkit" / "permissions" / "project" / "config.yaml"))
    assert decide_mod.active_profile(str(tmp_path), cfg) == "team"


def test_active_profile_falls_back_to_config(decide_mod, tmp_path):
    # An adopter mid-migration: no sidecar yet, active_profile still in config.
    _profile_sidecar_tree(
        tmp_path,
        profile_name="team",
        sidecar=None,
        config=(
            "schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: team\n"
        ),
    )
    cfg = decide_mod.load_yaml(str(tmp_path / ".pkit" / "permissions" / "project" / "config.yaml"))
    assert decide_mod.active_profile(str(tmp_path), cfg) == "team"


def test_active_profile_sidecar_wins_over_config(decide_mod, tmp_path):
    # Sidecar takes precedence over a stale config value (post-relocation safety).
    _profile_sidecar_tree(
        tmp_path,
        profile_name="team",
        sidecar="schema_version: 1\nactive_profile: team\n",
        config=(
            "schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: stale\n"
        ),
    )
    cfg = decide_mod.load_yaml(str(tmp_path / ".pkit" / "permissions" / "project" / "config.yaml"))
    assert decide_mod.active_profile(str(tmp_path), cfg) == "team"


@pytest.mark.parametrize(
    "corrupt_sidecar",
    ["42\n", "- a\n- b\n", "just a string\n"],
    ids=["bare-scalar", "top-level-list", "bare-string"],
)
@pytest.mark.parametrize("block_ruamel", [False, True], ids=["ruamel", "stdlib"])
def test_corrupt_sidecar_falls_back_to_config_on_both_parse_paths(
    decide_mod,
    tmp_path,
    monkeypatch,
    corrupt_sidecar,
    block_ruamel,
):
    # A hand-corrupted active-profile.yaml that parses to a non-dict (bare scalar,
    # top-level list, bare string) must NOT make active_profile()'s `.get()` raise.
    # load_yaml coerces a non-dict document to {} on BOTH parse paths (ruamel via
    # the CLI, stdlib via the sandboxed hook), so resolution degrades to the
    # config.yaml fallback identically — the same-code invariant (ADR-002/ADR-003).
    _profile_sidecar_tree(
        tmp_path,
        profile_name="team",
        sidecar=corrupt_sidecar,
        config=(
            "schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: team\n"
        ),
    )
    if block_ruamel:
        import builtins

        real_import = builtins.__import__

        def _block(name, *args, **kwargs):
            if "ruamel" in name:
                raise ImportError(f"simulated missing ruamel: {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block)

    cfg = decide_mod.load_yaml(str(tmp_path / ".pkit" / "permissions" / "project" / "config.yaml"))
    # No raise, and the corrupt sidecar yields no name → config.yaml fallback.
    assert decide_mod.active_profile(str(tmp_path), cfg) == "team"


def test_load_model_layers_profile_from_sidecar(decide_mod, tmp_path):
    # Enforcement unchanged: with active_profile in the sidecar, load_model still
    # layers the profile's grants and the model decides the same.
    _profile_sidecar_tree(
        tmp_path,
        profile_name="team",
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
        tmp_path,
        profile_name="team",
        sidecar=None,
        config=(
            "schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: team\n"
        ),
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
    REPO_ROOT_LOCAL
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "permissions"
    / "grants.yaml",
]

# Representative synthetic files that exercise edge cases the shipped files use.
_SYNTHETIC_YAML_CASES = [
    # grants.yaml-like: block mapping + block sequence + double-quoted tokens
    (
        "grants-like",
        (
            "schema_version: 1\n"
            "grants:\n"
            "  - subject: operator\n"
            '    privilege: "[privilege-catalog:vcs]"\n'
            "    effect: allow\n"
            "  - subject: all\n"
            "    privilege:\n"
            '      - "[privilege-catalog:privilege-escalation]"\n'
            '      - "[privilege-catalog:destructive-fs]"\n'
            "    effect: deny\n"
        ),
    ),
    # config.yaml-like: simple block mapping with booleans and null
    (
        "config-like",
        ("schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: ~\n"),
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
        ("schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: team\n"),
    ),
]


def _ruamel_load(text: str) -> Any:
    """Parse with ruamel.yaml safe-load (the reference parser)."""
    try:
        import io

        from ruamel.yaml import YAML

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


@pytest.mark.parametrize(
    "name,text", _SYNTHETIC_YAML_CASES, ids=lambda x: x if isinstance(x, str) else "text"
)
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


def test_stdlib_fallback_load_model_decides_correctly_without_ruamel(
    decide_mod, tmp_path, monkeypatch
):
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
        {
            "subject": "agent:project-manager",
            "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit")],
            "effect": "allow",
        },
        # the surgical deny that forces mutation through the validating scripts
        {
            "subject": "agent:project-manager",
            "privilege": _tok("issue-tracker-write"),
            "effect": "deny",
        },
    ],
}


@pytest.mark.parametrize(
    "cmd",
    [
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
    ],
)
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


@pytest.mark.parametrize(
    "cmd",
    [
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
    ],
)
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


@pytest.mark.parametrize(
    "cmd,expected",
    [
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
    ],
)
def test_pm_unaffected_commands_allowed(decide_mod, catalog, cmd, expected):
    """Commands that do not match issue-tracker-write are unaffected by the deny.

    Proves: the surgical deny does not block reads, gh api, git, or pkit — only
    the three raw mutations (gh issue edit, gh issue comment, gh pr edit).
    """
    d, why = decide_mod.decide(_PM_WITH_DENY_MODEL, catalog, _bash(cmd, "agent:project-manager"))
    assert d == expected, f"expected {expected!r} for {cmd!r}, got {d!r}: {why}"


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
            {
                "subject": "agent:project-manager",
                "privilege": _tok("issue-tracker"),
                "effect": "allow",
            },
            # deny issue-tracker-write second
            {
                "subject": "agent:project-manager",
                "privilege": _tok("issue-tracker-write"),
                "effect": "deny",
            },
        ],
    }
    d, why = decide_mod.decide(
        allow_first_model,
        catalog,
        _bash("gh issue edit 53", "agent:project-manager"),
    )
    assert d == "deny", (
        f"deny must win even when allow precedes deny in grant list; got {d!r}: {why}"
    )


def test_deny_precedence_deny_before_allow_in_grant_list(decide_mod, catalog):
    """Deny-precedence also holds when the deny grant appears BEFORE the allow grant."""
    deny_first_model = {
        "posture": "lenient",
        "grants": [
            # deny issue-tracker-write first
            {
                "subject": "agent:project-manager",
                "privilege": _tok("issue-tracker-write"),
                "effect": "deny",
            },
            # allow issue-tracker second (broad gh)
            {
                "subject": "agent:project-manager",
                "privilege": _tok("issue-tracker"),
                "effect": "allow",
            },
        ],
    }
    d, why = decide_mod.decide(
        deny_first_model,
        catalog,
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
        _PM_WITH_DENY_MODEL,
        catalog,
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
        {
            "subject": "agent:project-manager",
            "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit")],
            "effect": "allow",
        },
        # both capability denies the project-management fragment ships
        {
            "subject": "agent:project-manager",
            "privilege": _tok("issue-tracker-write"),
            "effect": "deny",
        },
        {
            "subject": "agent:project-manager",
            "privilege": _tok("issue-tracker-read-raw"),
            "effect": "deny",
        },
    ],
}


@pytest.mark.parametrize(
    "cmd",
    [
        "gh issue view 1",
        "gh issue view 53 --json title,body",
        "gh pr view 1",
        "gh pr view 27 --json state",
        "gh pr diff 1",
        "gh pr diff 27 --color never",
        # env-prefix form — the segments() stripper must handle this
        "export GH_PAGER= && gh pr diff 27",
    ],
)
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


@pytest.mark.parametrize(
    "cmd",
    [
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
    ],
)
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


@pytest.mark.parametrize(
    "cmd,expected",
    [
        # adjacent reads → allow (issue-tracker allow, no read-raw overlap → no deny)
        ("gh pr checks 27", "allow"),
        ("gh run list", "allow"),
        ("gh issue list", "allow"),
        ("gh api repos/owner/repo/issues", "allow"),
        # git / pkit → allow (unaffected by the read-redirect deny)
        ("git status", "allow"),
        ("pkit status", "allow"),
    ],
)
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
            {
                "subject": "agent:project-manager",
                "privilege": _tok("issue-tracker-read-raw"),
                "effect": "deny",
            },
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
        g
        for g in model_ref["grants"]
        if g.get("effect") == "deny" and g.get("subject") == "agent:project-manager"
    ]
    assert deny_grants, "reference model (ruamel) must contain the deny grant"

    # Now block ruamel — every load_yaml call falls back to _stdlib_load_yaml.
    monkeypatch.setattr(builtins, "__import__", _block_ruamel)

    catalog_stdlib = decide_mod.load_catalog(str(tmp_path))
    model_stdlib = decide_mod.load_model(str(tmp_path), catalog_stdlib)

    # The stdlib model must contain the deny grant (was None before the fix).
    deny_grants_stdlib = [
        g
        for g in model_stdlib["grants"]
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
    assert "issue-tracker-write" in why, f"denial reason must name the privilege; got: {why!r}"


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
    (claude_dir / "settings.json").write_text(_json.dumps({"agent": agent}), encoding="utf-8")


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


def test_hook_decide_no_agent_type_no_default_agent_falls_back_to_operator(
    decide_mod, catalog, tmp_path
):
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
    d, why = decide_mod.hook_decide(
        _PM_WITH_DENY_MODEL, catalog, payload, project_root=str(tmp_path)
    )
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
    assert "issue-tracker-write" in why, f"denial reason must name the privilege; got: {why!r}"


# ---- capability-fragment layer (ADR-016) ------------------------------------
#
# load_model gains a new layer:
#   guardrail_denies + capability_fragment_grants + active_profile_grants + adopter_grants
#
# Discovery walks the manifest components list; an orphan capability directory
# with no manifest entry contributes nothing (install-state-as-gate).
# Capability grants are annotated with _capability for the reporting layer;
# decide() ignores the extra key (it reads only subject/privilege/effect/scope).

CAP_FRAG_PATH = (
    REPO_ROOT_LOCAL
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "permissions"
    / "grants.yaml"
)


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
    cap_grants = [g for g in model["grants"] if g.get("_capability") == "project-management"]
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
        manifest=("schema_version: 1\nbackbone_version: 1.0.0\ncomponents: []\n"),
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
        g
        for g in model["grants"]
        if g.get("subject") == "all"
        and g.get("effect") == "allow"
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
        f"capability deny must override autonomous profile allow via deny-wins; got {d!r}: {why}"
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
        g
        for g in model["grants"]
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
        model,
        catalog,
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
            "schema_version: 1\nownership_mode: additive\nposture: lenient\nactive_profile: team\n"
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

    cap_idx = next(i for i, g in enumerate(grants) if g.get("_capability") == "project-management")
    profile_idx = next(
        i
        for i, g in enumerate(grants)
        if g.get("subject") == "all" and g.get("effect") == "allow" and not g.get("_capability")
    )
    adopter_idx = next(i for i, g in enumerate(grants) if g.get("subject") == "agent:critic")
    assert cap_idx < profile_idx, "capability fragment must come before profile grants in the model"
    assert profile_idx < adopter_idx, "profile grants must come before adopter grants in the model"


def test_stdlib_fallback_parses_capability_fragment_identically_to_ruamel(decide_mod):
    """The stdlib fallback must parse the shipped capability fragment identically to ruamel.

    Same-code invariant (ADR-002): if the hook runs in a macOS Seatbelt context
    without ruamel, it must parse the capability fragment file through
    _stdlib_load_yaml and get byte-identical results.
    """
    try:
        import io

        from ruamel.yaml import YAML

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
    assert not any("forbidden-floor" in str(g.get("privilege")) for g in denies), (
        "a rejected fragment guardrail must never synthesize a global deny"
    )


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
    assert decide_mod._privilege_ids("[privilege-catalog:trip-planning:ad-hoc-scraping]") == {
        "trip-planning:ad-hoc-scraping"
    }
    # The deny binds: researcher running `curl …` is DENIED.
    decision, reason = decide_mod.decide(
        model,
        catalog,
        {
            "type": "bash",
            "command": "curl https://example.com",
            "cwd": "/r",
            "subject": "agent:researcher",
        },
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
    _write_catalog_fragment_tree(tmp_path, fragment=fragment, project_grants=project_grants)
    catalog = decide_mod.load_catalog(str(tmp_path))
    model = decide_mod.load_model(str(tmp_path), catalog)
    # researcher is denied git (the overlapping fragment deny binds).
    d_res, _ = decide_mod.decide(
        model,
        catalog,
        {"type": "bash", "command": "git status", "cwd": "/r", "subject": "agent:researcher"},
    )
    assert d_res == "deny", "the capability's deny fences ITS named subject on the overlap"
    # builder is unaffected — it has a vcs allow and no scm-scrape deny.
    d_build, _ = decide_mod.decide(
        model,
        catalog,
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
    assert decide_mod._strip_leading_cd("cd a b && gh pr list") is None  # two args
    assert decide_mod._strip_leading_cd("cd /x | gh pr list") is None  # not && / ;
    assert decide_mod._strip_leading_cd("cd /x") is None  # no remainder
    assert decide_mod._strip_leading_cd("gh pr list") is None  # no leading cd


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
    d, why = decide_mod.decide(MODEL, catalog, _bash('cd "/x; rm -rf ~" && gh pr list', "operator"))
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
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /a && cd /b && gh pr list", "operator"))
    assert d == "allow", why


# ---- pipe-in-remainder: each segment must be covered (#1908) ---------------
#
# `|` is NOT in `_UNTRUSTED`: the splitter splits on it, so each side of a pipe
# is a segment of its own, and an allow needs a grant on every segment
# (ADR-025 point 2). A pipe whose every segment is granted allows, with or
# without a leading `cd`. A pipe into a command no grant covers, such as
# `| jq` or `| sh`, abstains. The cd-strip leaves the pipe untouched, so the
# cd-prefixed form decides exactly as the bare form does.


def test_cd_prefix_then_granted_pipe_allows(decide_mod, catalog):
    """`cd /x && git diff | git apply --check` ALLOWS: both sides of the pipe
    are `git`, which the operator's `vcs` grant covers, so the leading-cd strip
    reveals a compound whose every segment is granted."""
    d, why = decide_mod.decide(
        MODEL, catalog, _bash("cd /x && git diff | git apply --check", "operator")
    )
    assert d == "allow", why


def test_cd_prefix_then_pipe_to_ungranted_filter_abstains(decide_mod, catalog):
    """`cd /x && gh pr list | jq .` ABSTAINS: `gh` is granted, but no grant
    covers the `jq` segment, and a grant on one segment no longer carries
    another (#1908)."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && gh pr list | jq .", "operator"))
    assert d == "abstain", why
    assert "'jq'" in why


def test_cd_prefix_then_pipe_to_destructive_denies(decide_mod, catalog):
    """`cd /x && gh pr list | rm -rf ~` DENIES — deny-wins survives a pipe through
    the cd-strip recursion: the `rm -rf` segment hits the destructive-fs guardrail
    after the leading cd is stripped."""
    d, why = decide_mod.decide(MODEL, catalog, _bash("cd /x && gh pr list | rm -rf ~", "operator"))
    assert d == "deny", why
    assert "destructive-fs" in why


def test_cd_prefix_then_pipe_to_shell_matches_bare_form(decide_mod, catalog):
    """`cd /x && gh pr list | sh` resolves to EXACTLY the bare `gh pr list | sh`
    verdict, and both abstain: the cd-strip is verdict-preserving over a
    pipe-to-shell, and no grant covers the `sh` segment (#1908)."""
    cd_decision, cd_why = decide_mod.decide(
        MODEL, catalog, _bash("cd /x && gh pr list | sh", "operator")
    )
    bare_decision, _ = decide_mod.decide(MODEL, catalog, _bash("gh pr list | sh", "operator"))
    assert cd_decision == bare_decision == "abstain", (
        f"cd-prefixed pipe-to-shell must match the bare form's abstain; "
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


# ---- a compound allows only when a grant covers every segment (#1908) -------
#
# ADR-025 point 2, inherited from ADR-004 decision point 4: an unrecognized
# command in any segment makes the core abstain, never auto-allow. A grant on
# one segment of a compound used to carry the whole command, so where `gh` is
# granted, `gh pr list | sh` and `gh pr list ; python3 x.py` were allowed. Now
# each segment the splitter yields needs an allow of its own. A segment that
# matches no privilege, or matches only privileges the subject is not granted,
# leaves the compound unallowed: lenient abstains (the harness asks), strict
# denies. Deny-wins is unchanged: a deny on any segment still binds.
#
# MODEL grants `operator` vcs (git) + issue-tracker (gh) + kit (pkit) +
# repo-read. `docker` is recognized but granted only to `agent:devops`.

_UNCOVERED_COMPOUNDS = [
    # a segment no privilege recognizes
    "gh pr list | sh",
    "gh pr list ; python3 x.py",
    "gh pr list && frobnicate",
    "git status || curl -s example.com",
    "frobnicate | gh pr list",
    # a segment whose privilege is recognized but not granted to the operator
    "gh pr list && docker ps",
    "docker ps | git status",
]


@pytest.mark.parametrize("command", _UNCOVERED_COMPOUNDS)
def test_compound_with_an_uncovered_segment_abstains(decide_mod, catalog, command):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
    assert d == "abstain", f"{command!r} must not be allowed by a grant on another segment: {why}"


@pytest.mark.parametrize("command", _UNCOVERED_COMPOUNDS)
def test_compound_with_an_uncovered_segment_denies_under_strict(decide_mod, catalog, command):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture="strict")
    assert d == "deny", f"{command!r} must deny under a strict posture: {why}"


def test_the_reason_names_only_the_uncovered_segments_program(decide_mod, catalog):
    # The program, never its arguments: the diagnostic log records the reason
    # beside a redacted command, so an argument here would undo the redaction.
    for posture in ("lenient", "strict"):
        _, why = decide_mod.decide(
            MODEL, catalog, _bash("gh pr list ; python3 x.py --token s3cret", "operator"), posture
        )
        assert "'python3'" in why, why
        assert "x.py" not in why and "s3cret" not in why, why
        assert "'gh'" not in why, why


@pytest.mark.parametrize(
    "command,hidden",
    [
        # no space around the separator: the log's redaction splits on spaces
        # alone, so it keeps none of this, and the reason must not either
        ("gh pr list;/Users/alice/secret-proj/bin/tool --x", "secret-proj"),
        ("gh pr list ; my-key=s3cret curl x", "s3cret"),
    ],
)
def test_the_reason_shows_no_path_or_assignment(decide_mod, catalog, command, hidden):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d in ("abstain", "deny"), why
        assert hidden not in why and "'<other>'" in why, why


@pytest.mark.parametrize(
    "command",
    [
        "git status && gh pr list",
        "gh pr list ; git status",
        "git diff | git apply --check",
        "git fetch && git status || pkit status",
        "export GH_HOST=x && gh pr list | git hash-object --stdin",
    ],
)
def test_compound_whose_every_segment_is_granted_allows(decide_mod, catalog, command):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
    assert d == "allow", f"{command!r}: every segment is granted, so it stays allowed: {why}"


def test_leading_cd_then_a_granted_compound_allows(decide_mod, catalog):
    d, why = decide_mod.decide(
        MODEL, catalog, _bash("cd /x && git status && gh pr list", "operator")
    )
    assert d == "allow", why


@pytest.mark.parametrize(
    "command", ["cd /x && gh pr list ; python3 x.py", "cd /x; gh pr list | sh"]
)
def test_leading_cd_then_an_uncovered_segment_abstains(decide_mod, catalog, command):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
    assert d == "abstain", why
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture="strict")
    assert d == "deny", why


def test_a_scoped_grant_covers_only_its_own_segment(decide_mod, catalog):
    # devops may run docker inside services/, and nothing grants it gh.
    d, why = decide_mod.decide(
        MODEL, catalog, _bash("docker ps && gh pr list", "agent:devops", cwd="services/api")
    )
    assert d == "abstain", why


@pytest.mark.parametrize(
    "command,privilege",
    [
        ("frobnicate && sudo whoami", "privilege-escalation"),
        ("gh pr list | rm -rf ~", "destructive-fs"),
        ("python3 x.py ; git push --force", "vcs-history-rewrite"),
    ],
)
def test_a_deny_on_any_segment_still_wins(decide_mod, catalog, command, privilege):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture=posture)
        assert d == "deny", why
        assert privilege in why


def test_a_single_command_is_decided_as_before(decide_mod, catalog):
    # One segment: its own grant decides it, exactly as before #1908.
    assert decide_mod.decide(MODEL, catalog, _bash("gh pr list", "operator"))[0] == "allow"
    assert decide_mod.decide(MODEL, catalog, _bash("frobnicate", "operator"))[0] == "abstain"
    assert decide_mod.decide(MODEL, catalog, _bash("docker ps", "operator"))[0] == "abstain"


def test_uncovered_compound_hook_and_decide_parity(decide_mod, catalog):
    """The coverage check lives in the shared core, so hook_decide and decide
    agree on a compound with an uncovered segment (ADR-002 / ADR-003)."""
    cmd = "gh pr list | sh"
    d_decide, _ = decide_mod.decide(MODEL, catalog, _bash(cmd, "operator"))
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "/r"}
    d_hook, _ = decide_mod.hook_decide(MODEL, catalog, payload)  # no agent_type → operator
    assert d_decide == d_hook == "abstain"


# ---- a construct the splitter cannot trust, anywhere in the command (#1917) --
#
# ADR-025 point 2, inherited from ADR-004 decision point 4: a command
# substitution, a backtick or a `<` / `>` redirection is a construct the dumb
# splitter cannot be trusted on, so a grant never allows a command holding one,
# with or without a leading `cd`. A lenient posture abstains, a strict one
# denies, and a deny on any segment still wins. A newline and a background `&`
# separate segments as `;` does, and an assignment whose value holds such a
# construct stays a segment of its own. Each command below was allowed before:
# MODEL grants the operator `gh` and `git`, as the `autonomous` profile does.

_UNTRUSTED_COMMANDS = [
    "gh pr list $(python3 x.py)",
    "gh pr list `python3 x.py`",
    "gh pr list > ~/.bashrc",
    "gh pr list < /etc/passwd",
    "gh pr list\npython3 x.py",
    "gh pr list & python3 x.py",
    "gh pr list && X=$(python3 x.py)",
    "gh pr list && X=$(./x.sh)",
    "gh pr list =(python3 x.py)",  # zsh process substitution
]


@pytest.mark.parametrize("command", _UNTRUSTED_COMMANDS)
def test_an_untrusted_construct_anywhere_abstains(decide_mod, catalog, command):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
    assert d == "abstain", f"{command!r} must not be allowed by the grant: {why}"


@pytest.mark.parametrize("command", _UNTRUSTED_COMMANDS)
def test_an_untrusted_construct_anywhere_denies_under_strict(decide_mod, catalog, command):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture="strict")
    assert d == "deny", f"{command!r} must deny under a strict posture: {why}"


@pytest.mark.parametrize(
    "command",
    ["gh pr list $(python3 x.py)", "gh pr list > ~/.bashrc", "cd /x && gh pr list > out.txt"],
)
def test_the_reason_names_the_untrusted_construct_not_the_command(decide_mod, catalog, command):
    for posture in ("lenient", "strict"):
        _, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert "untrusted construct" in why, why
        assert "python3" not in why and "bashrc" not in why and "out.txt" not in why, why


def test_a_newline_and_a_background_amp_separate_segments(decide_mod):
    assert decide_mod.segments("gh pr list\npython3 x.py") == [
        ["gh", "pr", "list"],
        ["python3", "x.py"],
    ]
    assert decide_mod.segments("gh pr list & python3 x.py") == [
        ["gh", "pr", "list"],
        ["python3", "x.py"],
    ]
    assert decide_mod.segments("gh pr list&python3 x.py") == [
        ["gh", "pr", "list"],
        ["python3", "x.py"],
    ]
    # `&&` stays one separator, and a trailing `&` leaves no empty segment.
    assert decide_mod.segments("git status && gh pr list &") == [
        ["git", "status"],
        ["gh", "pr", "list"],
    ]


def test_an_assignment_holding_a_substitution_stays_a_segment(decide_mod):
    assert decide_mod.segments("gh pr list && X=$(./x.sh)") == [
        ["gh", "pr", "list"],
        ["X=$(./x.sh)"],
    ]
    assert decide_mod.segments("export X=`./x.sh` && gh pr list") == [
        ["export", "X=`./x.sh`"],
        ["gh", "pr", "list"],
    ]
    # A plain assignment is still stripped, as before, and so is one in front
    # of a command, so the command's own privileges are recognised.
    assert decide_mod.segments("export GH_HOST=x && gh pr list") == [["gh", "pr", "list"]]
    assert decide_mod.segments("X=$(true) gh pr list") == [["gh", "pr", "list"]]


@pytest.mark.parametrize(
    "command",
    [
        "gh pr list",
        "git status\ngh pr list",
        "git fetch & git status",
        "cd /x && gh pr list",
        "cd /x; git status\ngh pr list",
    ],
)
def test_a_granted_command_without_an_untrusted_construct_still_allows(
    decide_mod, catalog, command
):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "allow", f"{command!r}: {why}"


@pytest.mark.parametrize(
    "command,privilege",
    [
        ("gh pr list > x ; rm -rf ~", "destructive-fs"),
        ("cd /x && rm -rf ~ > log", "destructive-fs"),
        ("gh pr list $(id)\nsudo whoami", "privilege-escalation"),
        # behind an assignment holding a quote or a substitution
        ("FOO='' git push --force", "vcs-history-rewrite"),
        ('FOO="x" sudo id', "privilege-escalation"),
        ("X=$(true) rm -rf ~", "destructive-fs"),
    ],
)
def test_a_deny_still_wins_over_an_untrusted_construct(decide_mod, catalog, command, privilege):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "deny", why
        assert privilege in why


def test_a_leading_cd_then_an_untrusted_construct_denies_under_strict(decide_mod, catalog):
    d, why = decide_mod.decide(
        MODEL, catalog, _bash("cd /x && gh pr list > out.txt", "operator"), posture="strict"
    )
    assert d == "deny", why


def test_untrusted_construct_hook_and_decide_parity(decide_mod, catalog):
    """The check lives in the shared core, so hook_decide and decide agree on a
    command holding an untrusted construct (ADR-002 / ADR-003)."""
    cmd = "gh pr list > ~/.bashrc"
    d_decide, _ = decide_mod.decide(MODEL, catalog, _bash(cmd, "operator"))
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "/r"}
    d_hook, _ = decide_mod.hook_decide(MODEL, catalog, payload)  # no agent_type → operator
    assert d_decide == d_hook == "abstain"


# ---- the core reads a command's words as the shell does (#1942) -------------
#
# ADR-025 point 2: before it matches a grant or a deny, the core removes quotes
# and backslashes from each word as the shell removes them, so a quoted or
# escaped word is matched as the word the shell runs. A deny on it binds, and a
# quoted argument with no other untrusted construct is allowed where a grant
# covers its segment. A command whose words the core cannot read as the shell
# does is never allowed by a grant: a quote that does not close, whitespace the
# shell does not split on, a comment, a brace expansion, an expansion opened by
# `$`, an assignment to a variable that changes which program runs, or a
# leading assignment written with a quote or a backslash. A lenient posture
# abstains, a strict one denies, and a deny still wins.


@pytest.mark.parametrize(
    "command",
    [
        'git push origin main "--force"',
        "git push origin main '--force'",
        "git push origin main \\--force",
        'git push origin main --for"ce"',
        '"git" push -f origin main',
        'git "push" origin main -f',
        "cd /x && git push origin main '--force'",
    ],
)
def test_a_quoted_or_escaped_force_push_is_denied(decide_mod, catalog, command):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "deny", f"{command!r}: {why}"
        assert "vcs-history-rewrite" in why, why


@pytest.mark.parametrize(
    "command,privilege",
    [
        ("rm '-rf' build", "destructive-fs"),
        ("r\\m -r build", "destructive-fs"),
        ('"sudo" whoami', "privilege-escalation"),
    ],
)
def test_a_quoted_or_escaped_guardrail_is_denied(decide_mod, catalog, command, privilege):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "deny", f"{command!r}: {why}"
        assert privilege in why, why


def test_segments_removes_quotes_and_backslashes_as_the_shell_does(decide_mod):
    assert decide_mod.segments('git commit -m "fix: x"') == [["git", "commit", "-m", "fix: x"]]
    assert decide_mod.segments("git commit -m 'it''s'") == [["git", "commit", "-m", "its"]]
    assert decide_mod.segments("gh pr list --search a\\ b") == [
        ["gh", "pr", "list", "--search", "a b"]
    ]
    assert decide_mod.segments('git log --grep "a \\"b\\" \\x"') == [
        ["git", "log", "--grep", 'a "b" \\x']
    ]
    assert decide_mod.segments('git commit -m ""') == [["git", "commit", "-m", ""]]
    # An assignment is one only where its name is written unquoted, as the
    # shell reads it: `"GH_HOST=x"` is the name of the program it runs.
    assert decide_mod.segments('GH_HOST="a b" gh pr list') == [["gh", "pr", "list"]]
    assert decide_mod.segments('"GH_HOST=x" gh pr list') == [["GH_HOST=x", "gh", "pr", "list"]]


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "fix: x"',
        "git commit -m 'fix: x'",
        'gh pr list --search "is:open label:bug"',
        "gh pr list --search is:open\\ label:bug",
        '"gh" pr list',
        "cd /x && git commit -m 'fix: x' && git push origin main",
        "git commit -m '#12 fix'",  # a quoted `#` opens no comment
        # one word, `a --force`, which the shell passes on as it is: no flag
        "git push origin a\\ --force",
    ],
)
def test_a_quoted_argument_with_no_other_construct_is_allowed(decide_mod, catalog, command):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "allow", f"{command!r}: {why}"


_QUOTED_UNTRUSTED = [
    'git commit -m "$(cat msg.txt)"',
    "git commit -m '$(cat msg.txt)'",
    'git commit -m "a `id` b"',
    'git commit -m "a > b"',
    "git commit -m 'a < b'",
]

# Words the core cannot read as the shell does.
_UNREADABLE = [
    'gh pr list "x',  # a quote that does not close
    "gh pr list \\",  # a backslash with nothing after it
    'git log --format="%h;%s"',  # the splitter cuts the quoted `;`
    "gh\u00a0pr list",  # a no-break space: the shell runs a program named `gh pr`
    "gh pr list\u2003x",
    "gh pr list\rx",
    "gh pr list\vx",
    "gh pr list # x",  # a comment: the shell drops it
    "gh pr list --label {a,b}",  # a brace expansion: the shell makes two words
    "gh pr list --label x{1..3}",
    "git push origin {main,--force}",
    # behind a leading `cd`: the shell runs the word after a newline as a
    # command, and reads `cd<no-break space>x` as one word
    "cd\n{rm,-rf,~};git status",
    "cd {a,b} && git status",
    "cd #x && git status",
    "cd\u00a0sub/x;git status",
    "git push origin {a{b},--force}",  # nested: the outer brace still expands
    "'gh pr' list",  # one program word, which a `pattern` would read as two
]

# An expansion opened by `$`: a value the core never sees, and some forms
# evaluate it as code.
_EXPANSIONS = [
    "gh pr list ${X@P}",  # bash prompt expansion runs the value's substitutions
    "gh pr list $[X]",  # arithmetic, which evaluates the value
    "gh pr list ${X:$Y}",  # an arithmetic offset
    "gh pr list $X",
    "gh pr list $~X",  # zsh globs the value, whose qualifiers run code
    "git push origin main $'\\x2d\\x2dforce'",  # a quote the core cannot remove
]

# A leading assignment to a variable that changes which program runs.
_PROGRAM_PATH_ASSIGNMENTS = [
    "PATH=/tmp/x gh pr list",
    "PATH=/tmp/x:$PATH gh pr list",
    "export PATH=/tmp/x && gh pr list",
    "PATH=/tmp/x; gh pr list",
    "path=/tmp/x gh pr list",  # zsh's array tied to PATH
    "GIT_EXEC_PATH=/tmp/x git status",
    "LD_PRELOAD=/tmp/x.so git status",
    "DYLD_INSERT_LIBRARIES=/tmp/x.dylib gh pr list",
    "PYTHONPATH=/tmp/x pkit status",
    "BASH_ENV=/tmp/x.sh pkit status",
    "PATH+=:/tmp/x gh pr list",
    "JAVA_TOOL_OPTIONS=-javaagent:/tmp/x.jar pkit status",
    "GH_HOST=x \t PATH=/tmp/x gh pr list",
    "cd /x && PATH=/tmp/x gh pr list",
    # `export` takes every word as a name or an assignment, and runs no program
    "export git PATH=/tmp/x; git status",
    "export gh LD_PRELOAD=/tmp/x.so && gh pr list",
    "export pkit PYTHONPATH=/tmp/x; pkit status",
    # an `export` word the shell expands first: with a file named `PATH=bin`
    # in the directory, each of these sets `PATH`
    "export PAT?=bin; gh pr list",
    "export [P]ATH=bin && gh pr list",
    "export * && git status",
    "export LD_PRELOA?=x.so; git status",
    "cd sub && export PAT?=bin && gh pr list",
    # an assignment written with a quote or a backslash: its value may name a
    # command the grant never sees
    'GH_HOST="github.example.com" gh pr list',
    "GIT_SSH_COMMAND=sh\\ x.sh git fetch",
    "export GIT_SSH_COMMAND='sh x.sh' && git fetch",
]


@pytest.mark.parametrize(
    "command", _QUOTED_UNTRUSTED + _UNREADABLE + _EXPANSIONS + _PROGRAM_PATH_ASSIGNMENTS
)
def test_a_command_whose_words_the_core_cannot_read_is_not_allowed(decide_mod, catalog, command):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
    assert d == "abstain", f"{command!r} must not be allowed by the grant: {why}"
    assert "untrusted construct" in why, why
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture="strict")
    assert d == "deny", f"{command!r} must deny under a strict posture: {why}"


@pytest.mark.parametrize(
    "command,kind",
    [
        ('gh pr list "x', "unclosed quote"),
        ("gh\u00a0pr list", "whitespace"),
        ("gh pr list # x", "comment"),
        ("gh pr list {a,b}", "brace expansion"),
        ("gh pr list ${X@P}", "expansion"),
        ("PATH=/tmp/x gh pr list", "PATH"),
        ("GH_HOST='x' gh pr list", "assignment written with a quote"),
        ("gh pr list > secret-out.txt", "redirection"),
    ],
)
def test_the_reason_names_the_kind_of_construct_not_the_command(decide_mod, catalog, command, kind):
    for posture in ("lenient", "strict"):
        _, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert "untrusted construct" in why and kind in why, why
        assert "/tmp/x" not in why and "secret-out" not in why, why


@pytest.mark.parametrize(
    "command",
    [
        "GH_HOST=x gh pr list",
        "export GH_HOST=x && gh pr list",
        "GIT_PAGER=cat git log",
        "GH_HOST+=x gh pr list",
    ],
)
def test_an_assignment_that_leaves_the_program_alone_is_still_stripped(
    decide_mod, catalog, command
):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
    assert d == "allow", f"{command!r}: {why}"


@pytest.mark.parametrize(
    "command", ["cd\n./x.sh;git status", "cd\n./x.sh && git status", "declare PATH=/x; git status"]
)
def test_a_cd_before_a_newline_is_not_stripped(decide_mod, catalog, command):
    # The word after the newline is a command of its own, which no grant covers.
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
    assert d == "abstain", f"{command!r}: {why}"
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture="strict")
    assert d == "deny", f"{command!r}: {why}"


def test_the_brace_check_is_linear(decide_mod):
    # A word of many `{` and `,` with no `}` must not stall the hook.
    import time

    word = "{," * 20000
    started = time.perf_counter()
    assert decide_mod._brace_expansion(word) is False
    assert decide_mod._doubts(f"gh pr list {word}") == []
    assert time.perf_counter() - started < 1.0


def test_an_export_segment_runs_no_program(decide_mod):
    # `export` takes each word after it as a name or an assignment, so no
    # grant on a program covers the segment, and nothing of it is matched.
    assert decide_mod.segments("export git PATH=/tmp/x; git status") == [["git", "status"]]
    assert decide_mod.segments("export GH_HOST=x && gh pr list") == [["gh", "pr", "list"]]


def test_a_quoted_assignment_name_is_the_program_the_shell_runs(decide_mod, catalog):
    d, why = decide_mod.decide(MODEL, catalog, _bash('"GH_HOST=x" gh pr list', "operator"))
    assert d == "abstain", why


@pytest.mark.parametrize(
    "command,privilege",
    [
        ("PATH=/tmp/x sudo whoami", "privilege-escalation"),
        ("PATH+=:/tmp/x sudo whoami", "privilege-escalation"),
        ("PATH=/tmp/x git push --force", "vcs-history-rewrite"),
        ("git push {a,b} --force", "vcs-history-rewrite"),
        ("git push $X --force", "vcs-history-rewrite"),
        ('git push origin main "--force" # x', "vcs-history-rewrite"),
        ("gh pr list # x ; rm -rf ~", "destructive-fs"),
    ],
)
def test_a_deny_still_wins_over_a_word_the_core_cannot_read(
    decide_mod, catalog, command, privilege
):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "deny", f"{command!r}: {why}"
        assert privilege in why, why


def test_reading_words_hook_and_decide_parity(decide_mod, catalog):
    """The reading lives in the shared core, so hook_decide and decide agree
    on a quoted command (ADR-002 / ADR-003)."""
    for cmd, expected in (
        ('git push origin main "--force"', "deny"),
        ('git commit -m "fix: x"', "allow"),
        ("PATH=/tmp/x gh pr list", "abstain"),
    ):
        d_decide, _ = decide_mod.decide(MODEL, catalog, _bash(cmd, "operator"))
        payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "/r"}
        d_hook, _ = decide_mod.hook_decide(MODEL, catalog, payload)  # no agent_type → operator
        assert d_decide == d_hook == expected, cmd


# ---- a deny holds against the forms of the command it names (#1960) ---------
#
# ADR-025 point 5: a deny binds on the command in the forms programs read, not
# only the form its recognizer spells. A short flag inside a bundle, a long
# flag cut to a prefix, with its value after `=` or behind one dash, a program
# named by its path or in another case, and a subcommand behind the options
# before it are denied, as are `--mirror` and a refspec opening with `+`, which
# the catalog names. ADR-025 point 2: where a pathname pattern,
# or an assignment that changes the program's configuration, may make the
# command one a deny names, the core cannot tell: a lenient posture abstains, a
# strict one denies, and no grant allows it. A command no deny can name in any
# form is decided as before.


@pytest.mark.parametrize(
    "command",
    [
        # a short flag inside a bundle
        "git push -uf origin main",
        "git push -fu origin main",
        "git push -vf origin main",
        # a long flag cut to a prefix, or carrying its value after `=`
        "git push --forc origin main",
        "git push --fo origin main",
        "git push --force-w origin main",
        "git push --force-with-lease=main origin main",
        "git push --force-w=main:abc origin main",
        "git push --forc=x origin main",
        # a refspec opening with `+` forces the update of its ref
        "git push origin +main",
        "git push origin '+main'",
        "git push origin +HEAD:refs/heads/main",
        "git push origin '+refs/heads/*:refs/heads/*'",
        "git push origin +ma*",
        # the subcommand behind the options before it
        "git -C . push --force origin main",
        "git -c core.x=y push -f origin main",
        "git --git-dir .git push -f origin main",
        "git -C ~/repo push origin +main",
        # the program named by its path, by zsh's `=`, or in other case, which
        # a case-insensitive file system runs as `git`
        "/usr/bin/git push --force origin main",
        "./git push -f origin main",
        "=git push -f origin main",
        "Git push -f origin main",
        # a long flag behind one dash, and `--mirror`, which forces every ref
        "git push -force origin main",
        "git push --mirror origin",
        "git push --mirr origin",
        # behind a leading `cd`, and behind a configuration assignment
        "cd /x && git push -uf origin main",
        "HOME=/tmp/x git push --forc origin main",
    ],
)
def test_a_force_push_in_any_form_is_denied(decide_mod, catalog, command):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "deny", f"{command!r}: {why}"
        assert "vcs-history-rewrite" in why, why


@pytest.mark.parametrize(
    "command,privilege",
    [
        ("/usr/bin/sudo whoami", "privilege-escalation"),
        ("=sudo whoami", "privilege-escalation"),
        ("SUDO whoami", "privilege-escalation"),
        ("/bin/rm -rf build", "destructive-fs"),
        ("RM -rf build", "destructive-fs"),
        ("rm --recur build", "destructive-fs"),
        ("rm --r build", "destructive-fs"),
        ("rm --recursive build", "destructive-fs"),
    ],
)
def test_a_guardrail_in_any_form_is_denied(decide_mod, catalog, command, privilege):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "deny", f"{command!r}: {why}"
        assert privilege in why, why


def test_the_recognizer_names_a_forced_refspec_and_a_cut_recursive_flag(decide_mod, catalog):
    # The forms a recognizer spells itself are recognized as written too.
    for command, privilege in (
        ("git push origin +main", "vcs-history-rewrite"),
        ("rm --recur build", "destructive-fs"),
    ):
        hits = decide_mod.recognized_privileges(catalog, _bash(command, "operator"))
        assert privilege in hits, (command, hits)
    hits = decide_mod.recognized_privileges(catalog, _bash("git push origin main", "operator"))
    assert "vcs-history-rewrite" not in hits


# A form the core cannot see: what a pathname pattern expands to, or what a
# configuration an assignment points the program at holds.
_UNSEEN_FORMS = [
    # a pathname pattern that may expand to a flag or a forced refspec
    "git push origin --forc[e]",
    "git push origin -[f] main",
    "git push origin -?",
    "git push origin *",
    "git push origin [+]main",
    "git push origin ^main",  # zsh's EXTENDED_GLOB negation
    "git push origin --forc#e",  # zsh's EXTENDED_GLOB repetition
    "git push origin x#+main",  # `x#` may match nothing, leaving `+main`
    "git push x#-f origin main",
    # a pathname pattern where the program or its subcommand stands
    "gi? push --force origin main",
    "[g]it push -f origin main",
    "git pu?h --force origin main",
    # an assignment that changes the program's configuration, which may set a
    # forced refspec or an alias
    "HOME=/tmp/x git push origin main",
    "GIT_CONFIG_GLOBAL=/tmp/x git push origin main",
    "XDG_CONFIG_HOME=/tmp/x git push origin main",
    "GIT_DIR=/tmp/x/.git git push origin main",
    "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.p GIT_CONFIG_VALUE_0=push git p origin main",
    "HOME=/tmp/x git p origin main",
    "HOME=/tmp/x git status",  # a configuration may hold an alias of any name
    "export HOME=/tmp/x && git push origin main",
    "HOME=/tmp/x; git push origin main",
    "builtin export HOME=/tmp/x; git push origin main",
    "cd /x && HOME=/tmp/x git push origin main",
]


@pytest.mark.parametrize("command", _UNSEEN_FORMS)
def test_a_form_the_core_cannot_see_is_not_allowed(decide_mod, catalog, command):
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
    assert d == "abstain", f"{command!r} must not be allowed by the grant: {why}"
    assert "vcs-history-rewrite" in why, why
    d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture="strict")
    assert d == "deny", f"{command!r} must deny under a strict posture: {why}"


@pytest.mark.parametrize(
    "command,privilege",
    [
        ("rm -[r]f build", "destructive-fs"),
        ("rm * build", "destructive-fs"),
        ("r? -rf build", "destructive-fs"),
        ("sud? whoami", "privilege-escalation"),
    ],
)
def test_a_guardrail_form_the_core_cannot_see_keeps_a_grant_from_allowing(
    decide_mod, catalog, command, privilege
):
    # Where a grant covers the program, the deny's doubt is what keeps it from
    # allowing: grant every `r…` and `s…` program, and the command still
    # abstains, naming the guardrail.
    model = {
        "posture": "lenient",
        "grants": [
            *MODEL["grants"],
            {"subject": "operator", "privilege": _tok("anything"), "effect": "allow"},
        ],
    }
    wide = {
        "privileges": {
            **catalog["privileges"],
            "anything": {
                "description": "any program",
                "recognize": {"bash": [{"pattern": "^"}]},
            },
        }
    }
    d, why = decide_mod.decide(model, wide, _bash(command, "operator"))
    assert d == "abstain", f"{command!r}: {why}"
    assert privilege in why, why


@pytest.mark.parametrize(
    "command,kind",
    [
        ("git push origin --forc[e]", "pathname pattern"),
        ("HOME=/tmp/x git push origin main", "configuration"),
    ],
)
def test_the_reason_names_the_kind_of_form_not_the_command(decide_mod, catalog, command, kind):
    for posture in ("lenient", "strict"):
        _, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert kind in why, why
        assert "/tmp/x" not in why and "forc[e]" not in why, why


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push -u origin feat/x",
        "git push --set-upstream origin feat/x",
        "git push --follow-tags origin main",
        "git push --no-force origin main",
        "git push origin 'refs/heads/*:refs/heads/*'",
        "git push origin HEAD:refs/heads/feat-*",
        "git -C ~/repo push origin main",
        "git -C sub status",
        "git -c core.pager=cat log",
        "git add *.py",
        "git add src/*.py",
        "git log -- '*.md'",
        "git show HEAD^",
        "git rebase -i HEAD~3",
        "GIT_PAGER=cat git log",
        "HOME=/tmp/x gh pr list",  # no deny names `gh` for the operator
        # an assignment in front of a command is that command's alone, and one
        # a later segment exports reaches no segment before it
        "HOME=/tmp/x gh pr list && git status",
        "git push origin main && export HOME=/tmp/x",
        "gh api 'repos/o/r/issues?state=open'",
        "gh pr view 1 --json files --jq '.files[].path'",
        # a quoted or escaped glob character the shell passes on as it is
        "git push origin '[+]main'",
        "git push origin \\*",
        "git push origin '--forc*'",
    ],
)
def test_a_command_no_deny_names_in_any_form_is_allowed(decide_mod, catalog, command):
    for posture in ("lenient", "strict"):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
        assert d == "allow", f"{command!r}: {why}"


def test_builtin_export_stays_a_program_no_grant_covers(decide_mod, catalog):
    # A segment led by `builtin export` is no grant's, so no grant allows the
    # command, as on main. The denies read its assignments as `export`'s, so
    # one that changes the configuration names the deny it may get past.
    assert decide_mod.segments("builtin export GH_HOST=x && gh pr list") == [
        ["builtin", "export", "GH_HOST=x"],
        ["gh", "pr", "list"],
    ]
    for command in (
        "builtin export GH_HOST=x && gh pr list",
        "builtin export PATH=/tmp/x; gh pr list",
        "command export GH_HOST=x && gh pr list",
    ):
        for posture, verdict in (("lenient", "abstain"), ("strict", "deny")):
            d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
            assert d == verdict, (command, posture, why)
    for command in (
        "builtin export HOME=/tmp/x; git push origin main",
        "builtin builtin export GIT_CONFIG_GLOBAL=/tmp/x; git push origin main",
    ):
        d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"))
        assert d == "abstain" and "vcs-history-rewrite" in why, (command, why)


def test_a_word_prefix_a_pathname_pattern_may_expand_to_is_not_allowed(decide_mod, catalog):
    # Where the text before a pattern's first glob character opens a prefix the
    # recognizer names, the word may open with it.
    wide = {
        "privileges": {
            **catalog["privileges"],
            "main-push": {
                "description": "pushing to main",
                "recognize": {
                    "bash": [
                        {
                            "cmd": "git",
                            "subcommand": ["push"],
                            "word_prefix_any": ["refs/heads/main"],
                        }
                    ]
                },
            },
        }
    }
    model = {
        "posture": "lenient",
        "grants": [
            *MODEL["grants"],
            {"subject": "operator", "privilege": _tok("main-push"), "effect": "deny"},
        ],
    }
    for command, verdict in (
        ("git push origin refs/heads/main", "deny"),
        ("git push origin refs/heads/main*", "deny"),
        ("git push origin refs/heads/ma?n", "abstain"),
        ("git push origin refs/heads/mai*", "abstain"),
        ("git push origin r*", "abstain"),
        ("git push origin refs/tags/v*", "allow"),
        ("git push origin v*", "allow"),
        # zsh's EXTENDED_GLOB `#` makes the character before it optional
        ("git push origin x#refs/heads/main", "abstain"),
    ):
        d, why = decide_mod.decide(model, wide, _bash(command, "operator"))
        assert d == verdict, (command, why)


def test_a_regex_names_its_program_before_a_space(decide_mod, catalog):
    # A regex opening with `^git push` names `git`, so a pathname pattern in a
    # command of another program leaves it alone.
    wide = {
        "privileges": {
            **catalog["privileges"],
            "push-unverified": {
                "description": "a push past the hooks",
                "recognize": {"bash": [{"pattern": "^git push.*--no-verify"}]},
            },
        }
    }
    model = {
        "posture": "lenient",
        "grants": [
            *MODEL["grants"],
            {"subject": "operator", "privilege": _tok("push-unverified"), "effect": "deny"},
        ],
    }
    d, why = decide_mod.decide(model, wide, _bash("gh pr list --label x*", "operator"))
    assert d == "allow", why
    d, why = decide_mod.decide(model, wide, _bash("git log -- x*", "operator"))
    assert d == "abstain" and "push-unverified" in why, why
    # The core reads the subcommand behind 64 options with values at most: past
    # them it cannot tell, and defers rather than allows.
    for count, verdict in ((63, "deny"), (64, "abstain"), (500, "abstain")):
        command = "git " + "-C . " * count + "push origin main --no-verify"
        d, why = decide_mod.decide(model, wide, _bash(command, "operator"))
        assert d == verdict, (count, why)


def test_a_pattern_deny_holds_against_a_program_named_by_its_path(decide_mod, catalog):
    for command in (
        "/opt/homebrew/bin/gh issue create --title x",
        "=gh pr merge 27",
        "gh --repo o/r issue create --title x",
    ):
        d, why = decide_mod.decide(
            _PM_WITH_DENY_MODEL, catalog, _bash(command, "agent:project-manager")
        )
        assert d == "deny" and "issue-tracker-write" in why, (command, why)


def test_a_pathname_pattern_in_a_pattern_denys_program_is_not_allowed(decide_mod, catalog):
    # A pattern spells the words it names, so a pathname pattern anywhere in a
    # segment of its program keeps the core from telling. A quoted one is
    # passed on as it is.
    pm = "agent:project-manager"
    for command in ("gh issue cre* --title x", "gh pr list --label -*"):
        d, why = decide_mod.decide(_PM_WITH_DENY_MODEL, catalog, _bash(command, pm))
        assert d == "abstain" and "issue-tracker-write" in why, (command, why)
    for command in ("gh api 'repos/o/r/issues?state=open'", "gh pr list --jq '.[].title'"):
        d, why = decide_mod.decide(_PM_WITH_DENY_MODEL, catalog, _bash(command, pm))
        assert d == "allow", (command, why)


def test_a_sure_deny_wins_over_a_form_the_core_cannot_see(decide_mod, catalog):
    for command in (
        "HOME=/tmp/x git push -uf origin main",
        "git push origin * --force",
        "gi? status && git push origin +main",
    ):
        for posture in ("lenient", "strict"):
            d, why = decide_mod.decide(MODEL, catalog, _bash(command, "operator"), posture)
            assert d == "deny" and "vcs-history-rewrite" in why, (command, why)


def test_flag_forms(decide_mod):
    flags = ["--force", "-f", "--force-with-lease"]
    for word in (
        "--force",
        "-f",
        "--forc",
        "--f",
        "--force-with-lease=x",
        "-uf",
        "-4f",
        "-force",
        "-force-with-lease=x",
    ):
        assert decide_mod._flag_form(word, flags), word
    for word in ("--", "-", "--no-force", "--forcex", "-u", "-F", "-o.f", "--=x", "f", "-="):
        assert not decide_mod._flag_form(word, flags), word


def test_forms_hook_and_decide_parity(decide_mod, catalog):
    """The forms are read in the shared core, so hook_decide and decide agree
    (ADR-002 / ADR-003)."""
    for cmd, expected in (
        ("git push -uf origin main", "deny"),
        ("git push origin +main", "deny"),
        ("git push origin --forc[e]", "abstain"),
        ("HOME=/tmp/x git push origin main", "abstain"),
        ("git push origin main", "allow"),
    ):
        d_decide, _ = decide_mod.decide(MODEL, catalog, _bash(cmd, "operator"))
        payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "/r"}
        d_hook, _ = decide_mod.hook_decide(MODEL, catalog, payload)  # no agent_type → operator
        assert d_decide == d_hook == expected, cmd


# ---- the guardrails a deferred command may hide (#1982) ---------------------
#
# Where the core abstains on a command that may hide a form of a guardrail, a
# harness may still allow it by rules of its own. `hidden_guardrails` names
# those guardrails among the subject's denies, each with what keeps the core
# from seeing the form, so an adapter can ask the person (ADR-025 point 2).
# It names no project's own deny, none where no guardrail may bind unseen, and
# it changes no verdict of `decide()`.

_AGENT_GUARDRAIL_MODEL = {
    "posture": "lenient",
    "grants": [
        {
            "subject": "agent:project-manager",
            "privilege": _tok("vcs-history-rewrite"),
            "effect": "deny",
        },
    ],
}


@pytest.mark.parametrize("command", _UNSEEN_FORMS)
def test_hidden_guardrails_names_a_guardrail_the_core_cannot_tell(decide_mod, catalog, command):
    request = _bash(command, "operator")
    hidden = decide_mod.hidden_guardrails(MODEL, catalog, request)
    # A pattern where the program stands, such as `gi?`, may name any program,
    # and with it every guardrail.
    assert "vcs-history-rewrite" in hidden, (command, hidden)
    assert decide_mod.decide(MODEL, catalog, request)[0] == "abstain"


@pytest.mark.parametrize(
    "command,privilege,kind",
    [
        ("git push origin --forc[e]", "vcs-history-rewrite", "a pathname pattern"),
        ("HOME=/tmp/x git push origin main", "vcs-history-rewrite", "configuration"),
        ("rm -[r]f build", "destructive-fs", "a pathname pattern"),
        ("rm " + "-v x " * 65 + "build", "destructive-fs", "options"),
    ],
)
def test_hidden_guardrails_says_what_keeps_the_core_from_seeing(
    decide_mod, catalog, command, privilege, kind
):
    hidden = decide_mod.hidden_guardrails(MODEL, catalog, _bash(command, "operator"))
    assert list(hidden) == [privilege], hidden
    assert any(kind in phrase for phrase in hidden[privilege]), hidden
    assert all("/tmp/x" not in phrase and "[" not in phrase for phrase in hidden[privilege])


@pytest.mark.parametrize(
    "command",
    [
        # deferred, but no guardrail may bind on it unseen
        "gh pr list | sh",
        "git log $X",
        "git push origin main 2>&1",
        "env git status",
        "HOME=/tmp/x gh pr list",
        "gh issue cre* --title x",
        # allowed or denied by decide(), so never asked about
        "git push origin main",
        "git status",
        "git push -uf origin main",
        "sudo whoami",
    ],
)
def test_hidden_guardrails_names_none_where_no_guardrail_may_bind_unseen(
    decide_mod, catalog, command
):
    assert decide_mod.hidden_guardrails(MODEL, catalog, _bash(command, "operator")) == {}


def test_hidden_guardrails_names_no_projects_own_deny(decide_mod, catalog):
    # The project manager's `gh` deny may bind on a glob in a `gh` command, and
    # keeps a grant from allowing it, but it is no guardrail, so it is not named.
    pm = "agent:project-manager"
    request = _bash("gh issue cre* --title x", pm)
    assert decide_mod.decide(_PM_WITH_DENY_MODEL, catalog, request)[0] == "abstain"
    assert decide_mod.hidden_guardrails(_PM_WITH_DENY_MODEL, catalog, request) == {}
    request = _bash("git push origin --forc[e]", pm)
    hidden = decide_mod.hidden_guardrails(_PM_WITH_DENY_MODEL, catalog, request)
    assert list(hidden) == ["vcs-history-rewrite"], hidden


def test_hidden_guardrails_reads_only_the_subjects_denies(decide_mod, catalog):
    # A model without the guardrails' denies hides nothing, and one that denies
    # a guardrail to one agent alone hides it from that agent only.
    request = _bash("git push origin --forc[e]", "operator")
    allow_only = {"posture": "lenient", "grants": [MODEL["grants"][3]]}
    assert decide_mod.hidden_guardrails(allow_only, catalog, request) == {}
    assert decide_mod.hidden_guardrails(_AGENT_GUARDRAIL_MODEL, catalog, request) == {}
    request = _bash("git push origin --forc[e]", "agent:project-manager")
    hidden = decide_mod.hidden_guardrails(_AGENT_GUARDRAIL_MODEL, catalog, request)
    assert list(hidden) == ["vcs-history-rewrite"], hidden


def test_hidden_guardrails_names_none_for_a_tool_request(decide_mod, catalog):
    assert decide_mod.hidden_guardrails(MODEL, catalog, _tool("Read", "operator")) == {}


def test_hook_hidden_guardrails_resolves_the_subject_as_hook_decide_does(
    decide_mod, catalog, tmp_path
):
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git push origin --forc[e]"},
        "cwd": "/r",
        "agent_type": "project-manager",
    }
    hidden = decide_mod.hook_hidden_guardrails(_AGENT_GUARDRAIL_MODEL, catalog, payload)
    assert list(hidden) == ["vcs-history-rewrite"], hidden
    main = {k: v for k, v in payload.items() if k != "agent_type"}
    assert decide_mod.hook_hidden_guardrails(_AGENT_GUARDRAIL_MODEL, catalog, main) == {}
    # The main session runs as the configured default agent.
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text('{"agent": "project-manager"}')
    hidden = decide_mod.hook_hidden_guardrails(
        _AGENT_GUARDRAIL_MODEL, catalog, main, project_root=str(tmp_path)
    )
    assert list(hidden) == ["vcs-history-rewrite"], hidden
    hidden = decide_mod.hook_hidden_guardrails(
        _AGENT_GUARDRAIL_MODEL, catalog, main, project_root=str(tmp_path), as_subject="operator"
    )
    assert hidden == {}, hidden


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tool_name": "Bash"},
        {"tool_name": "Bash", "tool_input": "git push origin --forc[e]"},
        {"tool_name": "Edit", "tool_input": {"file_path": "/x"}},
    ],
)
def test_hook_hidden_guardrails_fails_open(decide_mod, catalog, payload):
    assert decide_mod.hook_hidden_guardrails(MODEL, catalog, payload) == {}


def test_hook_decide_still_decides_as_decide(decide_mod, catalog):
    # Resolving a payload's request moved into a helper both hook entry
    # points share, and hook_decide still returns decide()'s verdict.
    for cmd, expected in (
        ("git push origin --forc[e]", "abstain"),
        ("git push -uf origin main", "deny"),
        ("git status", "allow"),
    ):
        payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "/r"}
        assert decide_mod.hook_decide(MODEL, catalog, payload)[0] == expected, cmd
    verdict, why = decide_mod.hook_decide(MODEL, catalog, {"tool_name": "Bash"})
    assert verdict == "abstain" and "fail-open" in why


# ---- read-only filters and the Python runner in a compound (#2000) -----------
#
# Every shipped profile grants the read-only filters to every agent, and
# project-kit's own grants give every agent the Python runner, `uv`. ADR-025
# point 2 already allows a compound whose every segment a grant covers, so a
# pipe or chain of filters, `uv` and the programs a profile grants is allowed
# for the project manager and for a builder alike. A program that writes a file
# or runs another stays unrecognized, a deny still wins, and an untrusted
# construct still defers. The model is built from the shipped files, as
# `load_model` composes them: guardrails, the profile, the project-management
# fragment, then project-kit's own grants.

_PROFILES = REPO_ROOT / ".pkit" / "permissions" / "profiles"
_PROJECT_GRANTS = REPO_ROOT / ".pkit" / "permissions" / "project" / "grants.yaml"
_PM_FRAGMENT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "permissions" / "grants.yaml"
)
_BUILDERS = ("agent:project-manager", "agent:software-engineer")


def _shipped_model(decide_mod, catalog, profile: str) -> dict[str, Any]:
    shipped = decide_mod.load_yaml(str(_PROFILES / f"{profile}.yaml"))
    return {
        "posture": shipped["posture"],
        "grants": [
            *decide_mod.guardrail_denies(catalog),
            *shipped["grants"],
            *decide_mod.load_yaml(str(_PM_FRAGMENT))["grants"],
            *decide_mod.load_yaml(str(_PROJECT_GRANTS))["grants"],
        ],
    }


_FILTER_COMPOUNDS = [
    "grep x f | head",
    "cat f | grep x",
    "uv run pytest t.py -q | tail -3",
    "cd /Users/x/proj && uv run pkit validate | tail -1",
    "cat f | sort | uniq -c | head -5",
    "ls docs | wc -l",
    "git log --oneline | head -5",
    "gh pr list | jq .",
    "jq -r .name f | cut -d, -f1 | tr a-z A-Z",
    "echo done && pwd",
]


@pytest.mark.parametrize("profile", ["read-only", "non-destructive", "autonomous"])
@pytest.mark.parametrize("subject", _BUILDERS)
@pytest.mark.parametrize("command", _FILTER_COMPOUNDS[:4])
def test_a_filter_or_runner_compound_is_allowed_under_every_profile(
    decide_mod, catalog, profile, subject, command
):
    model = _shipped_model(decide_mod, catalog, profile)
    d, why = decide_mod.decide(model, catalog, _bash(command, subject))
    assert d == "allow", (profile, command, why)


@pytest.mark.parametrize("subject", _BUILDERS)
@pytest.mark.parametrize("command", _FILTER_COMPOUNDS)
def test_a_filter_compound_with_granted_programs_is_allowed(decide_mod, catalog, subject, command):
    model = _shipped_model(decide_mod, catalog, "autonomous")
    d, why = decide_mod.decide(model, catalog, _bash(command, subject))
    assert d == "allow", (command, why)


def test_the_runner_is_granted_by_the_project_not_by_a_profile(decide_mod, catalog):
    # ADR-005: no shipped profile grants scripting; project-kit's grants do.
    for profile in ("read-only", "non-destructive", "autonomous"):
        shipped = decide_mod.load_yaml(str(_PROFILES / f"{profile}.yaml"))
        tokens = {
            token
            for grant in shipped["grants"]
            for token in decide_mod._privilege_ids(grant["privilege"])
        }
        assert "read-filter" in tokens and "python-runner" not in tokens, profile
    profile_only = {
        "posture": "lenient",
        "grants": [
            *decide_mod.guardrail_denies(catalog),
            *decide_mod.load_yaml(str(_PROFILES / "autonomous.yaml"))["grants"],
        ],
    }
    d, why = decide_mod.decide(profile_only, catalog, _bash("uv run pytest | tail -3", "operator"))
    assert d == "abstain" and "'uv'" in why, why


@pytest.mark.parametrize(
    "command",
    [
        "sed -i s/a/b/ f",
        "awk -f prog.awk f",
        "find . -name x",
        "xargs rm",
        "tee out.txt",
        "rg x",
        "diff -l a b",
        "printf -v PATH /tmp/x",
        "sort -o out.txt f",
        "sort f -o out.txt",
        "sort -ro out.txt f",
        "sort -rnoout.txt f",
        "sort --output=out.txt f",
        "sort --output out.txt f",
        "sort --out=out.txt f",
        "sort --compress-program=sh f",
        "sort --compress-prog sh f",
        "sort -T /tmp/x f",
        "sort --temporary-directory=/tmp/x f",
        "uniq in.txt out.txt",
        "uniq -c in.txt out.txt",
        "uniq in.txt -c",
        "uniq - out.txt",
        "uniq -- in.txt out.txt",
        "uniq '' out.txt",
    ],
)
def test_a_program_that_writes_or_runs_another_is_no_filter(decide_mod, catalog, command):
    assert "read-filter" not in decide_mod.recognized_privileges(
        catalog, _bash(command, "operator")
    )
    lenient = _shipped_model(decide_mod, catalog, "autonomous")
    strict = _shipped_model(decide_mod, catalog, "read-only")
    for subject in _BUILDERS:
        piped = _bash(f"grep x f | {command}", subject)
        assert decide_mod.decide(lenient, catalog, piped)[0] == "abstain", command
        assert decide_mod.decide(strict, catalog, piped)[0] == "deny", command


@pytest.mark.parametrize(
    "command",
    [
        "sort f",
        "sort -u -t, -k2,2 f",
        "sort -rn --key=2 f",
        "uniq",
        "uniq -c in.txt",
        "uniq --skip-fields=1 -d in.txt",
    ],
)
def test_sort_and_uniq_are_filters_where_they_write_no_file(decide_mod, catalog, command):
    assert "read-filter" in decide_mod.recognized_privileges(catalog, _bash(command, "operator"))


@pytest.mark.parametrize(
    "command,privilege",
    [
        ("cat f | sudo tee /etc/x", "privilege-escalation"),
        ("grep x f && rm -rf ~", "destructive-fs"),
        ("uv run pytest -q | tail -3 ; git push --force", "vcs-history-rewrite"),
        ("cd /x && cat f ; git push origin +main", "vcs-history-rewrite"),
        ("gh pr view 1 | head", "issue-tracker-read-raw"),
    ],
)
def test_a_deny_still_wins_over_filters_and_the_runner(decide_mod, catalog, command, privilege):
    model = _shipped_model(decide_mod, catalog, "autonomous")
    d, why = decide_mod.decide(model, catalog, _bash(command, "agent:project-manager"))
    assert d == "deny" and privilege in why, why


@pytest.mark.parametrize(
    "command",
    [
        "grep x f > out.txt",
        "cat f | head >> out.txt",
        "uv run pytest t.py -q 2>&1 | tail -3",
        "cat < f | head",
        "cat <<EOF\nx\nEOF",
        "grep $X f | head",
        "cat f | head -n $(id -u)",
        "echo `id` | cat",
        "uv run pytest {a,b}.py | tail",
    ],
)
def test_an_untrusted_construct_still_defers(decide_mod, catalog, command):
    for profile, expected in (("autonomous", "abstain"), ("read-only", "deny")):
        model = _shipped_model(decide_mod, catalog, profile)
        for subject in _BUILDERS:
            d, why = decide_mod.decide(model, catalog, _bash(command, subject))
            assert d == expected, (profile, command, why)


def test_filter_and_runner_hook_and_decide_parity(decide_mod, catalog):
    """The new privileges are catalog data read by the shared core, so
    hook_decide and decide agree on each new case (ADR-002 / ADR-003)."""
    model = _shipped_model(decide_mod, catalog, "autonomous")
    for cmd, expected in (
        ("grep x f | head", "allow"),
        ("uv run pytest t.py -q | tail -3", "allow"),
        ("cd /x && uv run pkit validate | tail -1", "allow"),
        ("grep x f | sort -o out.txt", "abstain"),
        ("grep x f | uniq - out.txt", "abstain"),
        ("grep x f > out.txt", "abstain"),
        ("cat f && rm -rf ~", "deny"),
    ):
        for subject in _BUILDERS:
            d_decide, _ = decide_mod.decide(model, catalog, _bash(cmd, subject))
            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": cmd},
                "cwd": "/r",
                "agent_type": subject.split(":", 1)[1],
            }
            d_hook, _ = decide_mod.hook_decide(model, catalog, payload)
            assert d_decide == d_hook == expected, (cmd, subject)
