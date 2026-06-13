"""Conformance fixtures for the realized-state projection (.pkit/permissions/projection.py).

Golden pins of `project(model, catalog)` against the REAL baseline catalog. Per
the #249 critic pass: this task establishes the single `project()` and pins its
output; the same-code *proof* (apply emits exactly project()'s output) is an
acceptance criterion of the apply task (#250/#252), which doesn't exist yet — so
there is no tautological two-producer fixture here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PROJ_PATH = REPO / ".pkit" / "permissions" / "projection.py"
DECIDE_PATH = REPO / ".pkit" / "permissions" / "decide.py"
CATALOG = REPO / ".pkit" / "schemas" / "privilege-catalog.yaml"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def projection():
    return _load(PROJ_PATH, "proj_under_test")


@pytest.fixture(scope="module")
def catalog():
    return _load(DECIDE_PATH, "decide_for_proj").load_yaml(str(CATALOG))


def _tok(pid):
    return f"[privilege-catalog:{pid}]"


def test_cmd_only_allow_for_all_projects_to_settings(projection, catalog):
    model = {"grants": [{"subject": "all", "privilege": _tok("vcs"), "effect": "allow"}]}
    out = projection.project(model, catalog)
    assert out["settings"]["allow"] == ["Bash(git:*)"]
    assert out["settings"]["deny"] == []  # denies are never projected (canonical)


def test_denies_are_not_projected(projection, catalog):
    # The guardrail denies (flag_any/subcommand recognizers) must NOT be rendered
    # — re-deriving them as positional prefixes would weaken the fail-closed half.
    model = {"grants": [
        {"subject": "all", "privilege": _tok("destructive-fs"), "effect": "deny"},
        {"subject": "all", "privilege": _tok("vcs-history-rewrite"), "effect": "deny"},
    ]}
    out = projection.project(model, catalog)
    assert out["settings"] == {"allow": [], "deny": []}


def test_tool_privilege_for_all_projects_to_settings(projection, catalog):
    model = {"grants": [{"subject": "operator", "privilege": _tok("repo-read"), "effect": "allow"}]}
    out = projection.project(model, catalog)
    assert set(out["settings"]["allow"]) == {"Read", "Grep", "Glob"}


def test_per_agent_bash_routes_to_runtime(projection, catalog):
    model = {"grants": [{"subject": "agent:pm", "privilege": _tok("vcs"), "effect": "allow"}]}
    out = projection.project(model, catalog)
    assert out["settings"]["allow"] == []
    assert len(out["runtime"]) == 1 and out["runtime"][0]["privilege"] == "vcs"


def test_per_agent_tool_routes_to_runtime(projection, catalog):
    model = {"grants": [{"subject": "agent:critic", "privilege": _tok("web-fetch"), "effect": "allow"}]}
    out = projection.project(model, catalog)
    assert out["settings"]["allow"] == []
    assert any(r["privilege"] == "web-fetch" for r in out["runtime"])


def test_scoped_grant_is_unprojectable(projection, catalog):
    model = {"grants": [{
        "subject": "all", "privilege": _tok("docker"), "effect": "allow",
        "scope": ["services/**"],
    }]}
    out = projection.project(model, catalog)
    assert out["settings"]["allow"] == []
    assert len(out["unprojectable"]) == 1 and out["unprojectable"][0]["privilege"] == "docker"


def test_full_model_projection_routes_each_grant(projection, catalog):
    model = {"grants": [
        {"subject": "all", "privilege": _tok("privilege-escalation"), "effect": "deny"},
        {"subject": "operator",
         "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit"), _tok("repo-read")],
         "effect": "allow"},
        {"subject": "agent:pm", "privilege": _tok("vcs"), "effect": "allow"},
        {"subject": "agent:devops", "privilege": _tok("docker"),
         "scope": ["services/**"], "effect": "allow"},
    ]}
    out = projection.project(model, catalog)
    # Only `all` bash projects to settings; operator bash → runtime. So operator's
    # repo-read (tool) is the only thing reaching settings here.
    assert set(out["settings"]["allow"]) == {"Read", "Grep", "Glob"}
    # operator's vcs/issue-tracker/kit (bash) + agent:pm's vcs (bash) → runtime.
    assert {r["privilege"] for r in out["runtime"]} == {"vcs", "issue-tracker", "kit"}
    assert {u["privilege"] for u in out["unprojectable"]} == {"docker"}  # scoped
