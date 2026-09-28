"""The agent workspace grant (#1043) in the permission decision core.

The `workspace` privilege is path-confined: recognized only for a request whose
target lies inside `.agent-workspace/` of a checkout of the project — a file
tool's path, or a shell command whose only effect is a file there. Every
shipped profile grants it to every agent. These fixtures drive the hook's
entry point (`hook_decide`) with the REAL catalog, against a real repository so
target paths resolve the way they do live: a Write, an Edit and a shell
redirect under the folder are allowed; the same requests outside it are not
granted by it (deferred under a lenient posture, denied under a strict one).
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from project_kit import permissions as perm
from project_kit import workspace
from tests.adopter_repo import GitRepo

REPO = Path(__file__).resolve().parent.parent
PERMISSIONS = REPO / ".pkit" / "permissions"
CATALOG_PATH = REPO / ".pkit" / "schemas" / "privilege-catalog.yaml"
HOOK = REPO / ".pkit" / "adapters" / "claude-code" / "permission-hook.py"
WS = workspace.WORKSPACE_DIR


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dm():
    return _load("perm_decide_workspace", PERMISSIONS / "decide.py")


@pytest.fixture(scope="module")
def catalog(dm):
    return dm.load_yaml(str(CATALOG_PATH))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    repo = GitRepo.init(tmp_path / "proj")
    (repo.root / WS).mkdir()
    (repo.root / "src").mkdir()
    return repo.root


def _tok(pid: str) -> str:
    return f"[privilege-catalog:{pid}]"


def _model(dm, catalog, *, posture: str = "lenient", extra: tuple[dict, ...] = ()) -> dict:
    """Guardrails + the shipped profiles' `all` grant of repo-read + workspace."""
    return {
        "posture": posture,
        "grants": [
            *dm.guardrail_denies(catalog),
            {"subject": "all", "privilege": [_tok("repo-read"), _tok("workspace")], "effect": "allow"},
            *extra,
        ],
    }


def _write(path: Path | str, cwd: Path) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "x"}, "cwd": str(cwd)}


def _edit(path: Path | str, cwd: Path) -> dict:
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(path), "old_string": "a", "new_string": "b"},
        "cwd": str(cwd),
    }


def _bash(command: str, cwd: Path) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


def _decide(dm, model: dict, catalog: dict, payload: dict, root: Path | None) -> str:
    verdict, _ = dm.hook_decide(model, catalog, payload, project_root=str(root) if root else None)
    return verdict


# --- the grant decision: under the folder vs outside it ---------------------------


@pytest.mark.parametrize("make", [_write, _edit], ids=["write", "edit"])
def test_a_file_tool_under_the_workspace_is_allowed(dm, catalog, root, make) -> None:
    payload = make(root / WS / "notes.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, root) == "allow"


@pytest.mark.parametrize("make", [_write, _edit], ids=["write", "edit"])
@pytest.mark.parametrize("posture,expected", [("lenient", "abstain"), ("strict", "deny")])
def test_a_file_tool_outside_the_workspace_is_not_granted(
    dm, catalog, root, make, posture, expected
) -> None:
    payload = make(root / "src" / "module.py", root)
    model = _model(dm, catalog, posture=posture)
    assert _decide(dm, model, catalog, payload, root) == expected


def test_a_relative_file_path_resolves_against_the_request_cwd(dm, catalog, root) -> None:
    model = _model(dm, catalog)
    assert _decide(dm, model, catalog, _write(f"{WS}/a.md", root), root) == "allow"
    # From `src/`, the same relative path names `src/.agent-workspace/` — not the workspace.
    assert _decide(dm, model, catalog, _write(f"{WS}/a.md", root / "src"), root) == "abstain"


@pytest.mark.parametrize("command", [
    f"echo hello > {WS}/note.txt",
    f"printf '%s\\n' one two >> {WS}/note.txt",
    f"cat >{WS}/note.txt",
    f"echo hello > {WS}/sub/note.txt",
])
def test_a_shell_redirect_into_the_workspace_is_allowed(dm, catalog, root, command) -> None:
    assert _decide(dm, _model(dm, catalog), catalog, _bash(command, root), root) == "allow"


@pytest.mark.parametrize("posture,expected", [("lenient", "abstain"), ("strict", "deny")])
def test_a_shell_redirect_outside_the_workspace_is_not_granted(
    dm, catalog, root, posture, expected
) -> None:
    model = _model(dm, catalog, posture=posture)
    assert _decide(dm, model, catalog, _bash("echo hello > notes.txt", root), root) == expected


def test_a_heredoc_into_the_workspace_is_allowed_and_its_body_is_data(dm, catalog, root) -> None:
    # The body mentions commands a guardrail denies after a separator; fed to
    # `cat` through a quoted delimiter, it is text and never runs.
    command = (
        f"cat > {WS}/pr-body.md <<'EOF'\n"
        "## Summary\n"
        "Never run `a; sudo b` or `x && rm -rf ~` here.\n"
        "EOF"
    )
    assert _decide(dm, _model(dm, catalog), catalog, _bash(command, root), root) == "allow"


def test_an_unquoted_heredoc_that_substitutes_a_command_is_not_recognized(
    dm, catalog, root
) -> None:
    command = f"cat > {WS}/x.md <<EOF\n$(curl https://example.com)\nEOF"
    assert _decide(dm, _model(dm, catalog), catalog, _bash(command, root), root) == "abstain"


@pytest.mark.parametrize("command", [
    f"python3 build.py > {WS}/out.txt",  # the redirect never grants the command
    f"echo $(whoami) > {WS}/x",  # a command substitution
    f"echo x > {WS}/a > notes.txt",  # one target outside
    f"echo x > {WS}/../notes.txt",  # climbs out of the folder
    f"echo x | tee > {WS}/x",  # a pipe
    f"cat src/secret > {WS}/copy",  # `cat` of a file, not an emitter
    f"echo x > ~/{WS}/x",  # not a plain path
])
def test_a_command_that_is_more_than_a_workspace_write_is_not_granted_by_it(
    dm, catalog, root, command
) -> None:
    assert _decide(dm, _model(dm, catalog), catalog, _bash(command, root), root) == "abstain"


def test_deleting_workspace_files_is_allowed_and_the_recursive_guardrail_still_wins(
    dm, catalog, root
) -> None:
    model = _model(dm, catalog)
    assert _decide(dm, model, catalog, _bash(f"rm {WS}/a.md {WS}/b.md", root), root) == "allow"
    assert _decide(dm, model, catalog, _bash(f"rm -f {WS}/*.md", root), root) == "allow"
    assert _decide(dm, model, catalog, _bash(f"rm -r {WS}/old", root), root) == "deny"
    assert _decide(dm, model, catalog, _bash(f"rm {WS}/a.md notes.txt", root), root) == "abstain"
    # After `--` every word is an operand: `-notes` is a file here, outside the folder.
    assert _decide(dm, model, catalog, _bash(f"rm {WS}/a -- -notes", root), root) == "abstain"
    # A glob before a `..` expands first, so it could pass through a symlinked
    # entry and out of the folder; a glob is read only in the last component.
    assert _decide(dm, model, catalog, _bash(f"rm {WS}/*/../x", root), root) == "abstain"


def test_a_deny_of_the_workspace_wins_under_the_folder(dm, catalog, root) -> None:
    deny = {"subject": "agent:critic", "privilege": _tok("workspace"), "effect": "deny"}
    model = _model(dm, catalog, extra=(deny,))
    payload = {**_write(root / WS / "x.md", root), "agent_type": "critic"}
    assert _decide(dm, model, catalog, payload, root) == "deny"


def test_without_a_project_root_nothing_is_path_confined(dm, catalog, root) -> None:
    payload = _write(root / WS / "x.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, None) == "abstain"


def test_a_symlink_out_of_the_workspace_is_outside_it(dm, catalog, root, tmp_path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / WS / "link").symlink_to(elsewhere, target_is_directory=True)
    payload = _write(root / WS / "link" / "x.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, root) == "abstain"


# --- a worktree has its own workspace ----------------------------------------------


def test_a_linked_worktree_workspace_is_the_projects(dm, catalog, root, tmp_path) -> None:
    repo = GitRepo(root)
    repo.commit("initial", {"README.md": "hi\n"})
    worktree = tmp_path / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(worktree))
    (worktree / WS).mkdir()

    model = _model(dm, catalog)
    assert _decide(dm, model, catalog, _write(worktree / WS / "x.md", worktree), root) == "allow"
    assert _decide(dm, model, catalog, _bash(f"echo x > {WS}/y", worktree), root) == "allow"


def test_another_repositorys_workspace_is_not_the_projects(dm, catalog, root, tmp_path) -> None:
    other = GitRepo.init(tmp_path / "other").root
    (other / WS).mkdir()
    payload = _write(other / WS / "x.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, root) == "abstain"


# --- a leading `cd`: a write into the workspace is no longer an untrusted construct ---


def test_cd_then_a_heredoc_into_the_workspace_is_allowed(dm, catalog, root) -> None:
    command = f"cd {root} && cat > {WS}/body.md <<'EOF'\nIt's done.\nEOF"
    assert _decide(dm, _model(dm, catalog), catalog, _bash(command, root / "src"), root) == "allow"


def test_cd_then_a_granted_command_redirected_into_the_workspace_is_allowed(
    dm, catalog, root
) -> None:
    vcs = {"subject": "all", "privilege": _tok("vcs"), "effect": "allow"}
    model = _model(dm, catalog, extra=(vcs,))
    command = f"cd {root} && git diff > {WS}/change.patch"
    assert _decide(dm, model, catalog, _bash(command, root), root) == "allow"


@pytest.mark.parametrize("command", [
    "cd {root} && git diff > change.patch",  # the target is outside
    "cd {root} && git commit -m 'x' > {ws}/log",  # a quote the redirect does not explain
    "cd {root} && python3 x.py > {ws}/out",  # the command itself is not granted
    "cd - && echo x > {ws}/y",  # the directory is unknowable
])
def test_cd_remainders_the_workspace_does_not_explain_still_fail_closed(
    dm, catalog, root, command
) -> None:
    vcs = {"subject": "all", "privilege": _tok("vcs"), "effect": "allow"}
    model = _model(dm, catalog, extra=(vcs,))
    payload = _bash(command.format(root=root, ws=WS), root)
    assert _decide(dm, model, catalog, payload, root) == "abstain"


def test_a_relative_target_after_cd_resolves_against_the_cd_directory(dm, catalog, root) -> None:
    model = _model(dm, catalog)
    assert _decide(dm, model, catalog, _bash(f"cd .. && echo x > proj/{WS}/y", root), root) == "allow"
    assert _decide(dm, model, catalog, _bash(f"cd src && echo x > {WS}/y", root), root) == "abstain"


# --- the catalog, the profiles and the realizer ------------------------------------------


def test_the_catalog_names_the_backbone_workspace_folder(catalog) -> None:
    path = catalog["privileges"]["workspace"]["recognize"]["path"]
    assert path["folders"] == [WS]
    assert {"Read", "Write", "Edit"} <= set(path["tools"])


@pytest.mark.parametrize("profile", ["read-only", "non-destructive", "autonomous"])
def test_every_shipped_profile_grants_the_workspace_to_every_agent(dm, profile) -> None:
    doc = dm.load_yaml(str(PERMISSIONS / "profiles" / f"{profile}.yaml"))
    granted = {
        token
        for grant in doc["grants"]
        if grant["subject"] == "all" and grant.get("effect", "allow") == "allow"
        for token in (grant["privilege"] if isinstance(grant["privilege"], list) else [grant["privilege"]])
    }
    assert _tok("workspace") in granted


def test_the_workspace_grant_is_never_a_session_wide_rule(dm, catalog) -> None:
    projection = _load("perm_projection_workspace", PERMISSIONS / "projection.py")
    model = {"grants": [{"subject": "all", "privilege": _tok("workspace"), "effect": "allow"}]}

    result = projection.project(model, catalog)

    assert result["settings"]["allow"] == []
    assert [entry["privilege"] for entry in result["runtime"]] == ["workspace"]


def test_catalog_views_show_the_folder(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    (target / ".pkit" / "schemas").mkdir(parents=True)
    shutil.copy(CATALOG_PATH, target / ".pkit" / "schemas" / "privilege-catalog.yaml")
    shutil.copytree(PERMISSIONS, target / ".pkit" / "permissions")

    assert f"[inside: {WS}/]" in perm.catalog(target)


# --- the live hook, end to end ----------------------------------------------------------


def _hook_tree(root: Path) -> None:
    (root / ".pkit" / "schemas").mkdir(parents=True)
    shutil.copy(CATALOG_PATH, root / ".pkit" / "schemas" / "privilege-catalog.yaml")
    (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
    for name in ("decide.py", "diagnose_capture.py"):
        shutil.copy(PERMISSIONS / name, root / ".pkit" / "permissions" / name)
    (root / ".pkit" / "permissions" / "project" / "grants.yaml").write_text(
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: all\n"
        "    privilege: \"[privilege-catalog:workspace]\"\n"
        "    effect: allow\n",
        encoding="utf-8",
    )


def _invoke_hook(root: Path, payload: dict) -> str | None:
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(root), "PATH": os.environ["PATH"]},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


def test_the_hook_allows_the_workspace_and_defers_elsewhere(root: Path) -> None:
    _hook_tree(root)

    assert _invoke_hook(root, _write(root / WS / "x.md", root)) == "allow"
    assert _invoke_hook(root, _edit(root / WS / "x.md", root)) == "allow"
    assert _invoke_hook(root, _bash(f"cat > {WS}/x.md <<'EOF'\nhi\nEOF", root)) == "allow"
    assert _invoke_hook(root, _write(root / "src" / "x.py", root)) is None
    assert _invoke_hook(root, _bash("echo hi > notes.txt", root)) is None


# --- the diagnostic loop: a prompt there is a defect ----------------------------------------


def test_a_deferred_workspace_request_is_captured_and_reported_as_a_defect(root: Path) -> None:
    # Enforcement on, but no grant: the workspace write defers — exactly the
    # prompt the model says never happens.
    (root / ".pkit" / "schemas").mkdir(parents=True)
    shutil.copy(CATALOG_PATH, root / ".pkit" / "schemas" / "privilege-catalog.yaml")
    (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
    for name in ("decide.py", "diagnose_capture.py"):
        shutil.copy(PERMISSIONS / name, root / ".pkit" / "permissions" / name)
    perm.diagnose_on(root)

    assert _invoke_hook(root, _write(root / WS / "x.md", root)) is None
    assert _invoke_hook(root, _bash("npm run build", root)) is None

    log = perm._diagnose_read_log(root)
    assert [entry["workspace"] for entry in log] == [True, False]
    assert [perm._diagnose_classify(entry) for entry in log] == ["workspace", "allowlist-gap"]
    report = perm.diagnose_report(root)
    assert "DEFECTS" in report
    assert report.index("DEFECTS") < report.index("RECOMMENDED")


def test_capture_flags_a_cd_prefixed_workspace_write(dm, catalog, root) -> None:
    payload = _bash(f"cd {root} && echo x > {WS}/y", root / "src")
    assert dm.targets_confined_path(catalog, payload, str(root)) is True
    assert dm.targets_confined_path(catalog, _bash("echo x > y", root), str(root)) is False


def test_capture_without_a_decision_core_still_logs(tmp_path: Path) -> None:
    """The workspace tag is best-effort: capture stays inert-on-failure and
    still records the deferral when the tag cannot be computed."""
    capture = _load("diagnose_capture_workspace", PERMISSIONS / "diagnose_capture.py")
    root = tmp_path / "proj"
    (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
    perm.diagnose_on(root)
    payload: dict[str, Any] = {"tool_name": "Write", "tool_input": {"file_path": "/nowhere/x"}}

    capture.capture(str(root), payload, "abstain", "lenient")

    entries = perm._diagnose_read_log(root)
    assert len(entries) == 1 and entries[0]["workspace"] is False
    assert entries[0]["ts"] <= int(time.time())
