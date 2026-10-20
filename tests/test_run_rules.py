"""The rules of an agent run: read, filled in and projected (ADR-066 point 5).

project-management's `permissions/runs.yaml` declares the rules of the runs
`pkit pm fix-drift` starts. The backbone reads them at the pinned commit
(`run_rules`), and projects them through the shared decision core
(`.pkit/permissions/projection.py`, `project_run`) into the forms a runner
renders as native rules. These tests hold both to the records: one deny of
every call none of what proposing needs recognises, held as an allow list; a
floor of denies, each held natively or by that list; and a refusal wherever a
deny reaches what the run needs and no native rule can hold it.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import run_rules

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / ".pkit" / "capabilities" / "project-management" / "permissions" / "runs.yaml"
FIX_DRIFT = "project-management:fix-drift"
SCHEMA = REPO / ".pkit" / "schemas" / "permission-runs.schema.json"


def _projection() -> Any:
    path = REPO / ".pkit" / "permissions" / "projection.py"
    spec = importlib.util.spec_from_file_location("projection_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


project_run = _projection().project_run


def _token(pid: str) -> str:
    return f"[privilege-catalog:{pid}]"


def _rules(*pids: str) -> list[dict[str, Any]]:
    return [{"subject": "all", "privilege": _token(p), "effect": "deny"} for p in pids]


ALLOWED = {
    "cap:read": {
        "description": "read",
        "recognize": {"path": {"folders": ["/wc"], "tools": ["Read"]}},
    },
    "cap:git-read": {
        "description": "git reading",
        "recognize": {"bash": [{"cmd": "git", "args": ["-C", "/wc", "log"]}]},
    },
    "cap:pkit-read": {
        "description": "pkit reading",
        "recognize": {"bash": [{"cmd": "pkit", "args": ["friction", "check"]}]},
    },
}
EVERYTHING_ELSE = {
    "cap:else": {
        "description": "else",
        "recognize": {"except": [_token(p) for p in ALLOWED]},
    }
}


def _privileges(**more: Any) -> dict[str, Any]:
    return {**ALLOWED, **EVERYTHING_ELSE, **more}


# --- the file project-management ships ------------------------------------------------


def test_project_managements_rules_hold_their_shape() -> None:
    import jsonschema

    document = YAML(typ="safe").load(RUNS.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(document)
    template = YAML(typ="safe").load(
        (REPO / ".pkit" / "schemas" / "permission-runs.yaml").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(schema).validate(template)


def test_the_fix_drift_run_projects_with_no_refusal() -> None:
    projected = run_rules.view(REPO, FIX_DRIFT, "living-docs")
    assert not isinstance(projected, str), projected
    allow = projected.allow
    assert {"tool": "Read", "folder": "{{pkit:working-copy}}"} in allow
    assert {"tool": "Write", "folder": "{{pkit:workspace}}"} in allow
    assert {"command": ["git", "-C", "{{pkit:working-copy}}", "show"]} in allow
    assert {"command": ["git", "-C", "{{pkit:working-copy}}", "apply", "--check"]} in allow
    assert {"command": ["git", "diff", "--no-index"]} in allow
    assert {"command": ["pkit", "friction", "explain"]} in allow
    assert {"command": ["pkit", "analysis", "propose"]} in allow
    # Writes outside the workspace, and every command of this capability.
    assert not any(rule.get("tool") == "Write" and "folder" not in rule for rule in allow)
    assert not any(rule.get("command", [None, None])[:2] == ["pkit", "pm"] for rule in allow)
    deny = projected.deny
    for rule in (
        {"tool": "Edit"},
        {"tool": "NotebookEdit"},
        {"command": ["gh"]},
        {"command": ["uv"]},
        {"command": ["pkit", "pm"]},
        {"command": ["pkit", "project-management"]},
        {"command": ["sudo"]},
    ):
        assert rule in deny, rule
    held = {entry["privilege"]: entry["how"] for entry in projected.held}
    assert held["project-management:beyond-proposing"] == "allow list"
    assert held["project-management:version-control-beyond-reading"] == "allow list"
    assert held["project-management:methodology-writers"] == "allow list"
    assert "native deny" in held["issue-tracker"]


def test_project_managements_own_commands_are_never_allowed() -> None:
    projected = run_rules.view(REPO, FIX_DRIFT, "living-docs")
    assert not isinstance(projected, str)
    names = {tuple(rule["command"][:2]) for rule in projected.allow if "command" in rule}
    assert ("pkit", "pm") not in names
    assert ("pkit", "project-management") not in names


def test_filled_in_folders_leave_no_placeholder(tmp_path: Path) -> None:
    projected = run_rules.project_run(
        REPO,
        FIX_DRIFT,
        "living-docs",
        working_copy=tmp_path / "clone",
        workspace=tmp_path / "clone" / ".agent-workspace",
    )
    assert not isinstance(projected, str), projected
    text = json.dumps([*projected.allow, *projected.deny])
    assert "{working-copy}" not in text and "{workspace}" not in text
    assert {"tool": "Read", "folder": str(tmp_path / "clone")} in projected.allow
    assert ["git", "-C", str(tmp_path / "clone"), "log"] in [
        rule.get("command") for rule in projected.allow
    ]
    # The brief still names the folders by the markers the backbone fills in.
    assert "`git -C {{pkit:working-copy}} log …`" in projected.forms


def test_forms_name_each_folder_by_its_marker() -> None:
    projected = run_rules.view(REPO, FIX_DRIFT, "analysis-resolver")
    assert not isinstance(projected, str)
    assert "Read, Grep and Glob on files in `{{pkit:working-copy}}`" in projected.forms
    assert "`pkit analysis propose …`" in projected.forms


def test_queries_leave_out_the_capability_that_declares_the_rules() -> None:
    found = run_rules.queries(REPO, leaving_out="project-management")
    words = {q.words for q in found}
    assert ("analysis", "propose") in words
    assert ("software-analysis", "propose") in words
    assert not any(w[0] in ("pm", "project-management") for w in words)


def test_a_query_that_starts_uv_is_a_candidate_for_the_exclusion() -> None:
    projected = run_rules.view(REPO, FIX_DRIFT, "analysis-resolver")
    assert not isinstance(projected, str)
    assert ("pkit", "analysis", "propose") in projected.excluded_candidates


# --- reading -------------------------------------------------------------------------


def _project(tmp_path: Path, body: str | None) -> Path:
    root = tmp_path / "root"
    (root / ".pkit" / "schemas").mkdir(parents=True)
    shutil.copy(SCHEMA, root / ".pkit" / "schemas" / SCHEMA.name)
    if body is not None:
        folder = root / ".pkit" / "capabilities" / "demo" / "permissions"
        folder.mkdir(parents=True)
        (folder / "runs.yaml").write_text(body, encoding="utf-8")
    return root


def test_a_run_named_badly_is_no_run(tmp_path: Path) -> None:
    assert "names no run" in str(run_rules.read(tmp_path, "demo"))
    assert "names no run" in str(run_rules.read(tmp_path, "Demo:run"))


def test_a_capability_with_no_rules_declares_none(tmp_path: Path) -> None:
    root = _project(tmp_path, None)
    assert "declares no rules of agent runs" in str(run_rules.read(root, "demo:run"))


def test_rules_that_break_their_shape_refuse(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "schema_version: 1\nprivileges: {}\nruns:\n  run:\n    description: d\n    rules:\n"
        "      - {subject: agent:x, privilege: '[privilege-catalog:a]', effect: deny}\n",
    )
    said = str(run_rules.read(root, "demo:run"))
    assert "does not hold its shape" in said


def test_a_run_the_file_does_not_declare_refuses(tmp_path: Path) -> None:
    root = _project(tmp_path, "schema_version: 1\nprivileges: {}\nruns: {}\n")
    assert "declares no run of `other`" in str(run_rules.read(root, "demo:other"))


def test_the_schema_missing_refuses(tmp_path: Path) -> None:
    root = _project(tmp_path, "schema_version: 1\nprivileges: {}\nruns: {}\n")
    (root / ".pkit" / "schemas" / SCHEMA.name).unlink()
    assert "upgrade the backbone" in str(run_rules.read(root, "demo:run"))


# --- the projection ------------------------------------------------------------------


def test_the_complement_becomes_the_allow_list() -> None:
    out = project_run(_privileges(), _rules("cap:else"), [])
    assert out["refused"] is None
    assert {"tool": "Read", "folder": "/wc"} in out["allow"]
    assert {"command": ["git", "-C", "/wc", "log"]} in out["allow"]
    assert out["held"] == [{"privilege": "cap:else", "how": "allow list"}]


def test_no_complement_refuses() -> None:
    out = project_run(_privileges(), [], [])
    assert "no deny of every call" in out["refused"]


def test_two_complements_refuse() -> None:
    privileges = _privileges(**{"cap:else2": EVERYTHING_ELSE["cap:else"]})
    out = project_run(privileges, _rules("cap:else", "cap:else2"), [])
    assert "more than one" in out["refused"]


def test_an_allowed_privilege_no_native_rule_names_refuses() -> None:
    privileges = _privileges(
        **{
            "cap:read": {
                "description": "x",
                "recognize": {"bash": [{"cmd": "git", "subcommand": ["log"]}]},
            }
        }
    )
    out = project_run(privileges, _rules("cap:else"), [])
    assert "cannot name" in out["refused"]


def test_a_floor_deny_disjoint_from_the_allow_list_is_also_native() -> None:
    privileges = _privileges(
        **{"cap:gh": {"description": "gh", "recognize": {"bash": [{"cmd": "gh"}]}}}
    )
    out = project_run(privileges, _rules("cap:else", "cap:gh"), [])
    assert out["refused"] is None
    assert {"command": ["gh"]} in out["deny"]
    assert {"privilege": "cap:gh", "how": "allow list and native deny"} in out["held"]


def test_a_floor_deny_carved_out_of_what_is_allowed_is_held_by_the_list() -> None:
    privileges = _privileges(
        **{
            "cap:git-beyond": {
                "description": "git beyond reading",
                "recognize": {"bash": [{"cmd": "git"}], "except": [_token("cap:git-read")]},
            }
        }
    )
    out = project_run(privileges, _rules("cap:else", "cap:git-beyond"), [])
    assert out["refused"] is None
    assert {"command": ["git"]} not in out["deny"]
    assert {"privilege": "cap:git-beyond", "how": "allow list"} in out["held"]


def test_a_carved_deny_reaching_what_is_still_allowed_refuses() -> None:
    privileges = _privileges(
        **{
            "cap:git-beyond": {
                "description": "git beyond reading",
                "recognize": {"bash": [{"cmd": "pkit"}], "except": [_token("cap:git-read")]},
            }
        }
    )
    out = project_run(privileges, _rules("cap:else", "cap:git-beyond"), [])
    assert "reaches what the run needs" in out["refused"]


def test_a_model_deny_on_something_allowed_is_written_natively() -> None:
    model = [{"subject": "all", "privilege": _token("cap:pkit-read"), "effect": "deny"}]
    out = project_run(_privileges(), _rules("cap:else"), model)
    assert out["refused"] is None
    assert {"command": ["pkit", "friction", "check"]} in out["deny"]
    assert {"privilege": "cap:pkit-read", "how": "native deny"} in out["held"]


def test_a_model_deny_reaching_what_is_allowed_with_a_pattern_refuses() -> None:
    privileges = _privileges(
        **{"git-pattern": {"description": "p", "recognize": {"bash": [{"pattern": r"^git\s+log"}]}}}
    )
    model = [{"subject": "all", "privilege": _token("git-pattern"), "effect": "deny"}]
    out = project_run(privileges, _rules("cap:else"), model)
    assert "no native rule can hold it" in out["refused"]


def test_a_scoped_model_deny_reaching_what_is_allowed_refuses() -> None:
    model = [
        {
            "subject": "all",
            "privilege": _token("cap:pkit-read"),
            "effect": "deny",
            "scope": ["x/**"],
        }
    ]
    out = project_run(_privileges(), _rules("cap:else"), model)
    assert "no native rule can hold it" in out["refused"]


def test_guardrails_on_other_commands_are_held_by_the_list() -> None:
    privileges = _privileges(
        **{
            "destructive-fs": {
                "description": "rm -r",
                "recognize": {"bash": [{"pattern": r"^rm(?=\s).*(\s-[a-zA-Z]*[rR])"}]},
            },
            "vcs-history-rewrite": {
                "description": "force push",
                "recognize": {
                    "bash": [{"cmd": "git", "subcommand": ["push"], "flag_any": ["--force"]}]
                },
            },
        }
    )
    model = [
        {"subject": "all", "privilege": _token("destructive-fs"), "effect": "deny"},
        {"subject": "all", "privilege": _token("vcs-history-rewrite"), "effect": "deny"},
    ]
    out = project_run(privileges, _rules("cap:else"), model)
    assert out["refused"] is None
    held = {h["privilege"]: h["how"] for h in out["held"]}
    assert held["destructive-fs"] == "allow list"
    assert held["vcs-history-rewrite"] == "allow list"


def test_a_subcommand_deny_reaching_an_allowed_subcommand_refuses() -> None:
    privileges = _privileges(
        **{
            "cap:git-diff": {
                "description": "git diff",
                "recognize": {"bash": [{"cmd": "git", "args": ["diff", "--no-index"]}]},
            },
            "no-diff": {
                "description": "no diff",
                "recognize": {"bash": [{"cmd": "git", "subcommand": ["diff"]}]},
            },
        }
    )
    privileges["cap:else"] = {
        "description": "else",
        "recognize": {"except": [_token(p) for p in [*ALLOWED, "cap:git-diff"]]},
    }
    model = [{"subject": "all", "privilege": _token("no-diff"), "effect": "deny"}]
    out = project_run(privileges, _rules("cap:else"), model)
    assert "no native rule can hold it" in out["refused"]


def test_an_unknown_privilege_recognises_nothing() -> None:
    model = [{"subject": "all", "privilege": _token("nowhere"), "effect": "deny"}]
    out = project_run(_privileges(), _rules("cap:else"), model)
    assert out["refused"] is None


# --- shown, not hidden ----------------------------------------------------------------


def test_the_permission_views_list_each_runs_rules() -> None:
    from project_kit import permissions

    for view in (permissions.explain(REPO, None), permissions.overview(REPO)):
        assert "RULES OF AGENT RUNS" in view
        assert (
            "project-management:fix-drift  (contributed by capability: project-management)" in view
        )
        assert "all — DENY project-management:beyond-proposing" in view


def test_agents_rules_shows_a_run_and_refuses_an_unknown_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from click.testing import CliRunner

    from project_kit.cli import main

    monkeypatch.chdir(REPO)
    shown = CliRunner().invoke(main, ["agents", "rules", FIX_DRIFT, "--json"])
    assert shown.exit_code == 0, shown.output
    document = json.loads(shown.output)
    assert document["refused"] is None
    assert "`pkit friction explain …`" in document["forms"]
    assert {"command": ["gh"]} in document["deny"]
    refused = CliRunner().invoke(main, ["agents", "rules", "project-management:nothing", "--json"])
    assert refused.exit_code == 1
    assert "declares no run of `nothing`" in json.loads(refused.output)["refused"]
    human = CliRunner().invoke(main, ["agents", "rules", FIX_DRIFT])
    assert "Allowed, and nothing else:" in human.output
    assert "project-management:beyond-proposing: allow list" in human.output


@pytest.mark.parametrize("words", run_rules.READING_COMMANDS)
def test_a_reading_command_is_never_a_writer(words: tuple[str, ...]) -> None:
    # The writers the methodology ships, which no reading command's words start.
    writers = {
        ("friction", "revalidate"),
        ("friction", "defer"),
        ("friction", "revisit"),
        ("friction", "record-status"),
        ("friction", "resolve"),
        ("refs", "rename"),
        ("version",),
        ("sync",),
        ("upgrade",),
        ("init",),
    }
    for writer in writers:
        assert words[: len(writer)] != writer
