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
    # env-prefix form — the segments() stripper must handle this
    "export GH_HOST=github.com && gh issue edit 53",
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
    "gh pr view 27",
    "gh pr list",
    "gh api repos/owner/repo/issues",
    "gh api graphql -f query='...'",
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
