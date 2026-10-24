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
    assert spec is not None and spec.loader is not None
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
    model = {
        "grants": [
            {"subject": "all", "privilege": _tok("destructive-fs"), "effect": "deny"},
            {"subject": "all", "privilege": _tok("vcs-history-rewrite"), "effect": "deny"},
        ]
    }
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
    model = {
        "grants": [{"subject": "agent:critic", "privilege": _tok("web-fetch"), "effect": "allow"}]
    }
    out = projection.project(model, catalog)
    assert out["settings"]["allow"] == []
    assert any(r["privilege"] == "web-fetch" for r in out["runtime"])


def test_scoped_grant_is_unprojectable(projection, catalog):
    model = {
        "grants": [
            {
                "subject": "all",
                "privilege": _tok("docker"),
                "effect": "allow",
                "scope": ["services/**"],
            }
        ]
    }
    out = projection.project(model, catalog)
    assert out["settings"]["allow"] == []
    assert len(out["unprojectable"]) == 1 and out["unprojectable"][0]["privilege"] == "docker"


def test_full_model_projection_routes_each_grant(projection, catalog):
    model = {
        "grants": [
            {"subject": "all", "privilege": _tok("privilege-escalation"), "effect": "deny"},
            {
                "subject": "operator",
                "privilege": [_tok("vcs"), _tok("issue-tracker"), _tok("kit"), _tok("repo-read")],
                "effect": "allow",
            },
            {"subject": "agent:pm", "privilege": _tok("vcs"), "effect": "allow"},
            {
                "subject": "agent:devops",
                "privilege": _tok("docker"),
                "scope": ["services/**"],
                "effect": "allow",
            },
        ]
    }
    out = projection.project(model, catalog)
    # Only `all` bash projects to settings; operator bash → runtime. So operator's
    # repo-read (tool) is the only thing reaching settings here.
    assert set(out["settings"]["allow"]) == {"Read", "Grep", "Glob"}
    # operator's vcs/issue-tracker/kit (bash) + agent:pm's vcs (bash) → runtime.
    assert {r["privilege"] for r in out["runtime"]} == {"vcs", "issue-tracker", "kit"}
    assert {u["privilege"] for u in out["unprojectable"]} == {"docker"}  # scoped


# ---- the read-only filters and the Python runner (#2000) ---------------------
#
# A `cmd`-only recognizer renders as a native prefix, so a profile's grant of
# the read-only filters realizes one `Bash(<program>:*)` per program. The
# `sort` and `uniq` recognizers are regexes that leave out the forms writing a
# file, and no native prefix can say that, so none is written for them: a
# `Bash(sort:*)` would allow `sort -o`. The runner renders as `Bash(uv:*)`.

_FILTER_PROGRAMS = {
    "cat",
    "head",
    "tail",
    "wc",
    "cut",
    "tr",
    "grep",
    "egrep",
    "fgrep",
    "jq",
    "ls",
    "cmp",
    "basename",
    "dirname",
    "realpath",
    "pwd",
    "echo",
    "true",
    "false",
}


def test_the_read_filter_projects_a_prefix_per_program_and_none_for_sort_or_uniq(
    projection, catalog
):
    model = {"grants": [{"subject": "all", "privilege": _tok("read-filter"), "effect": "allow"}]}
    out = projection.project(model, catalog)
    assert set(out["settings"]["allow"]) == {f"Bash({p}:*)" for p in _FILTER_PROGRAMS}
    assert [u["privilege"] for u in out["unprojectable"]] == ["read-filter", "read-filter"]


def test_the_python_runner_projects_the_uv_prefix(projection, catalog):
    model = {"grants": [{"subject": "all", "privilege": _tok("python-runner"), "effect": "allow"}]}
    assert projection.project(model, catalog)["settings"]["allow"] == ["Bash(uv:*)"]


def test_project_kits_own_grants_project_nothing_its_settings_lack(projection, catalog):
    # project-kit grants the runner in its own grants.yaml. Its committed
    # settings already allow `uv` alone, so `apply` adds nothing to them.
    import json

    grants = _load(DECIDE_PATH, "decide_for_self_host").load_yaml(
        str(REPO / ".pkit" / "permissions" / "project" / "grants.yaml")
    )
    settings = json.loads((REPO / ".claude" / "settings.json").read_text())
    out = projection.project({"grants": grants["grants"]}, catalog)
    assert out["settings"]["allow"] == ["Bash(uv:*)"]
    assert set(out["settings"]["allow"]) <= set(settings["permissions"]["allow"])
