"""The agent workspace grant (#1043) in the permission decision core.

The `workspace` privilege is a path-scoped allow: recognized only for a FILE
TOOL whose target lies inside `.agent-workspace/` of a checkout of the project.
Every shipped profile grants it to every agent. A shell command is never the
workspace's — a redirect, a here-document or an `rm` into the folder is judged
exactly as `main` judges any shell write (ADR-025 unchanged), which the
security review's proofs of concept pin below. These fixtures drive the hook's
entry point (`hook_decide`) with the REAL catalog, against a real repository so
target paths resolve the way they do live.
"""
from __future__ import annotations

import copy
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


def _autonomous(dm, catalog, *, posture: str = "lenient") -> dict:
    """Guardrails + the shipped `autonomous` profile's grants — the widest
    shipped model, so a shell command it leaves ungranted is ungranted by all."""
    profile = dm.load_yaml(str(PERMISSIONS / "profiles" / "autonomous.yaml"))
    return {"posture": posture, "grants": [*dm.guardrail_denies(catalog), *profile["grants"]]}


def _tool(tool: str, path: Path | str, cwd: Path, **fields: str) -> dict:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return {"tool_name": tool, "tool_input": {key: str(path), **fields}, "cwd": str(cwd)}


def _write(path: Path | str, cwd: Path) -> dict:
    return _tool("Write", path, cwd, content="x")


def _edit(path: Path | str, cwd: Path) -> dict:
    return _tool("Edit", path, cwd, old_string="a", new_string="b")


def _bash(command: str, cwd: Path) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


def _decide(dm, model: dict, catalog: dict, payload: dict, root: Path | None) -> str:
    verdict, _ = dm.hook_decide(model, catalog, payload, project_root=str(root) if root else None)
    return verdict


# --- the grant decision: a file tool under the folder vs outside it ------------------


@pytest.mark.parametrize("tool", ["Read", "Write", "Edit", "MultiEdit", "NotebookEdit"])
def test_a_file_tool_under_the_workspace_is_allowed(dm, catalog, root, tool) -> None:
    payload = _tool(tool, root / WS / "notes.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, root) == "allow"


@pytest.mark.parametrize("make", [_write, _edit], ids=["write", "edit"])
@pytest.mark.parametrize("posture,expected", [("lenient", "abstain"), ("strict", "deny")])
def test_a_file_tool_outside_the_workspace_is_not_granted(
    dm, catalog, root, make, posture, expected
) -> None:
    payload = make(root / "src" / "module.py", root)
    model = _model(dm, catalog, posture=posture)
    assert _decide(dm, model, catalog, payload, root) == expected


def test_the_workspace_folder_itself_is_not_inside_it(dm, catalog, root) -> None:
    assert _decide(dm, _model(dm, catalog), catalog, _write(root / WS, root), root) == "abstain"


def test_a_relative_file_path_resolves_against_the_request_cwd(dm, catalog, root) -> None:
    model = _model(dm, catalog)
    assert _decide(dm, model, catalog, _write(f"{WS}/a.md", root), root) == "allow"
    # From `src/`, the same relative path names `src/.agent-workspace/` — not the workspace.
    assert _decide(dm, model, catalog, _write(f"{WS}/a.md", root / "src"), root) == "abstain"


def test_a_deny_of_the_workspace_wins_under_the_folder(dm, catalog, root) -> None:
    deny = {"subject": "agent:critic", "privilege": _tok("workspace"), "effect": "deny"}
    model = _model(dm, catalog, extra=(deny,))
    payload = {**_write(root / WS / "x.md", root), "agent_type": "critic"}
    assert _decide(dm, model, catalog, payload, root) == "deny"


def test_without_a_project_root_nothing_is_path_scoped(dm, catalog, root) -> None:
    payload = _write(root / WS / "x.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, None) == "abstain"


def test_a_symlink_out_of_the_workspace_is_outside_it(dm, catalog, root, tmp_path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / WS / "link").symlink_to(elsewhere, target_is_directory=True)
    payload = _write(root / WS / "link" / "x.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, root) == "abstain"


# --- a shell command is never the workspace's -------------------------------------------
#
# Every command below writes or deletes only inside the workspace — or claims to.
# None is granted by it: each is decided as main decides any shell command, so
# under the widest shipped profile a lenient posture defers to the operator and a
# strict one denies — except where a leading `cd` leaves a redirect behind it,
# which ADR-025 abstains on in either posture. The first five are the security
# review's proofs of concept (arbitrary execution through an emitter's
# arguments); the `cd …/nope; …` pair is the code review's (a `;` runs the
# remainder in the ORIGINAL directory when the `cd` fails, so "relative to the
# `cd` directory" was never certain — `rm -f *` would empty the project root).

_SHELL_WRITES = [  # (command, lenient verdict, strict verdict)
    # the security review's proofs of concept
    (f"echo =(touch PWNED) > {WS}/x", "abstain", "deny"),  # zsh process substitution
    (f"cd src && echo =(touch PWNED) > ../{WS}/x", "abstain", "abstain"),  # behind a leading cd
    (rf"echo ${{(e)C:=\$\(touch PWNED\)}} > {WS}/x", "abstain", "deny"),  # zsh (e) flag
    (rf"echo ${{C:=\$\(touch PWNED\)}}${{C@P}} > {WS}/x", "abstain", "deny"),  # bash 5 prompt expansion
    (f"echo *(e:'touch PWNED':) > {WS}/x", "abstain", "deny"),  # zsh glob qualifier
    # the code review's: the `cd` fails, the remainder runs in the project root
    (f"cd {WS}/nope; rm -f *", "abstain", "deny"),
    (f"cd {WS}/nope; echo x > f", "abstain", "abstain"),
    # the plain shapes the reverted recognizer read as the workspace's
    (f"echo hello > {WS}/note.txt", "abstain", "deny"),
    (f"printf '%s\\n' one two >> {WS}/note.txt", "abstain", "deny"),
    (f"cat > {WS}/pr-body.md <<'EOF'\n## Summary\nDone.\nEOF", "abstain", "deny"),
    (f"rm {WS}/a.md {WS}/b.md", "abstain", "deny"),
    (f"rm -f {WS}/*.md", "abstain", "deny"),
]


@pytest.mark.parametrize("command,lenient,strict", _SHELL_WRITES)
def test_a_shell_write_into_the_workspace_is_not_granted_by_it(
    dm, catalog, root, command, lenient, strict
) -> None:
    for posture, expected in (("lenient", lenient), ("strict", strict)):
        model = _autonomous(dm, catalog, posture=posture)
        assert _decide(dm, model, catalog, _bash(command, root), root) == expected, posture


def test_a_redirect_behind_a_leading_cd_still_fails_closed(dm, catalog, root) -> None:
    # ADR-025 unchanged: after a stripped `cd`, a redirect or a quote abstains
    # even when the command in front of it is granted and the target is the
    # workspace.
    model = _autonomous(dm, catalog)
    for command in (
        f"cd {root} && git diff > {WS}/change.patch",
        f"cd {root} && cat > {WS}/body.md <<'EOF'\nIt's done.\nEOF",
    ):
        verdict, reason = dm.hook_decide(model, catalog, _bash(command, root), project_root=str(root))
        assert verdict == "abstain"
        assert "untrusted construct" in reason


def test_the_recursive_deletion_guardrail_still_denies_in_the_workspace(dm, catalog, root) -> None:
    assert _decide(dm, _autonomous(dm, catalog), catalog, _bash(f"rm -r {WS}/old", root), root) == "deny"


@pytest.fixture(scope="module")
def main_dm(tmp_path_factory):
    """`main`'s decision core, loaded from git — the baseline the shell
    judgment must still equal. Skips where no base ref is available."""
    for ref in ("origin/main", "main"):
        shown = subprocess.run(
            ["git", "show", f"{ref}:.pkit/permissions/decide.py"],
            cwd=REPO, capture_output=True, text=True, check=False,
        )
        if shown.returncode == 0:
            path = tmp_path_factory.mktemp("main-decide") / "decide.py"
            path.write_text(shown.stdout, encoding="utf-8")
            return _load("perm_decide_main_baseline", path)
    pytest.skip("base ref (origin/main|main) not available")


@pytest.mark.parametrize("command", [
    *(command for command, _, _ in _SHELL_WRITES),
    f"cd {WS} && echo x > y",
    f"cd {WS}/nope; rm -f ../../*",
    "cd src && gh pr list",
    "cd src && gh pr list > out.txt",
    "git status",
    "rm -rf build/",
    "python3 build.py > out.txt",
])
@pytest.mark.parametrize("posture", ["lenient", "strict"])
def test_the_shell_judgment_is_mains(dm, main_dm, catalog, root, command, posture) -> None:
    model = _autonomous(dm, catalog, posture=posture)
    payload = _bash(command, root)
    assert dm.hook_decide(model, catalog, payload, project_root=str(root)) == main_dm.hook_decide(
        model, catalog, payload, project_root=str(root)
    )


# --- a worktree has its own workspace ----------------------------------------------


def test_a_linked_worktree_workspace_is_the_projects(dm, catalog, root, tmp_path) -> None:
    repo = GitRepo(root)
    repo.commit("initial", {"README.md": "hi\n"})
    worktree = tmp_path / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(worktree))
    (worktree / WS).mkdir()

    model = _model(dm, catalog)
    assert _decide(dm, model, catalog, _write(worktree / WS / "x.md", worktree), root) == "allow"
    assert _decide(dm, model, catalog, _write(f"{WS}/y.md", worktree), root) == "allow"


def test_another_repositorys_workspace_is_not_the_projects(dm, catalog, root, tmp_path) -> None:
    other = GitRepo.init(tmp_path / "other").root
    (other / WS).mkdir()
    payload = _write(other / WS / "x.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, root) == "abstain"


def test_from_a_linked_worktree_the_main_checkouts_workspace_counts(
    dm, catalog, root, tmp_path
) -> None:
    repo = GitRepo(root)
    repo.commit("initial", {"README.md": "hi\n"})
    worktree = tmp_path / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(worktree))

    payload = _write(root / WS / "x.md", root)
    assert _decide(dm, _model(dm, catalog), catalog, payload, worktree) == "allow"


def test_a_planted_git_pointer_does_not_make_a_worktree(dm, catalog, root, tmp_path) -> None:
    # A `.git` file naming the project's git directory — directly, or copied
    # from a registered worktree — does not register the directory holding it:
    # git's own entry for the worktree must point back at it.
    repo = GitRepo(root)
    repo.commit("initial", {"README.md": "hi\n"})
    worktree = tmp_path / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(worktree))
    model = _model(dm, catalog)
    pointers = {
        "direct": f"gitdir: {root / '.git'}\n",
        "copied": (worktree / ".git").read_text(encoding="utf-8"),
    }
    for name, pointer in pointers.items():
        planted = tmp_path / name
        (planted / WS).mkdir(parents=True)
        (planted / ".git").write_text(pointer, encoding="utf-8")
        payload = _write(planted / WS / "x.md", planted)
        assert _decide(dm, model, catalog, payload, root) == "abstain", name



# --- a repository nested inside the workspace is not the workspace -----------------------
#
# Its tracked files are another checkout's; the folder's allow must not make them
# writable without a prompt, whether the nested checkout is another repository
# cloned into the folder or a worktree of this one added there.

_NOT_GRANTED = [("lenient", "abstain"), ("strict", "deny")]


@pytest.mark.parametrize("posture,expected", _NOT_GRANTED)
def test_a_clone_nested_inside_the_workspace_is_not_the_workspace(
    dm, catalog, root, posture, expected
) -> None:
    clone = GitRepo.init(root / WS / "clone")
    clone.commit("initial", {"src/a.py": "x = 1\n"})
    model = _model(dm, catalog, posture=posture)

    for make in (_write, _edit):
        for target in (clone.root / "src" / "a.py", clone.root / "notes.md"):
            assert _decide(dm, model, catalog, make(target, root), root) == expected, target


@pytest.mark.parametrize("posture,expected", _NOT_GRANTED)
def test_a_worktree_nested_inside_the_workspace_is_not_the_workspace(
    dm, catalog, root, posture, expected
) -> None:
    repo = GitRepo(root)
    repo.commit("initial", {"README.md": "hi\n", "src/a.py": "x = 1\n"})
    nested = root / WS / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(nested))
    model = _model(dm, catalog, posture=posture)

    for make in (_write, _edit):
        for cwd in (root, nested):
            payload = make(nested / "src" / "a.py", cwd)
            assert _decide(dm, model, catalog, payload, root) == expected, cwd
    # The nested worktree's own workspace is still its workspace.
    (nested / WS).mkdir()
    assert _decide(dm, model, catalog, _write(nested / WS / "x.md", nested), root) == "allow"


@pytest.mark.parametrize("posture,expected", _NOT_GRANTED)
def test_a_file_hard_linked_into_the_workspace_is_not_the_workspace(
    dm, catalog, root, posture, expected
) -> None:
    # A hard link planted in the folder is the same file as its other name: a
    # write through it changes the file outside the folder too.
    source = root / "src" / "module.py"
    source.write_text("x = 1\n", encoding="utf-8")
    os.link(source, root / WS / "module.py")
    (root / WS / "own.md").write_text("mine\n", encoding="utf-8")
    model = _model(dm, catalog, posture=posture)

    assert _decide(dm, model, catalog, _edit(root / WS / "module.py", root), root) == expected
    assert _decide(dm, model, catalog, _edit(root / WS / "own.md", root), root) == "allow"


# --- the folder is the checkout's own ------------------------------------------------


def test_a_symlinked_workspace_folder_is_never_the_workspace(dm, catalog, tmp_path) -> None:
    # A hostile checkout could commit `.agent-workspace` as a symlink to the
    # home directory; the grant must not follow it there.
    root = GitRepo.init(tmp_path / "proj").root
    home = tmp_path / "home"
    home.mkdir()
    (root / WS).symlink_to(home, target_is_directory=True)
    model = _model(dm, catalog)

    assert _decide(dm, model, catalog, _write(root / WS / ".bashrc", root), root) == "abstain"
    assert _decide(dm, model, catalog, _write(home / ".bashrc", root), root) == "abstain"


@pytest.mark.parametrize("folder,target", [
    ("/", "src/x.py"),
    ("/tmp", "/tmp/x"),
    ("~", "~/x"),
    ("..", "src/x.py"),
    ("../elsewhere", "../elsewhere/x"),
    ("sub/../..", "../x"),
    (".", "src/x.py"),
])
def test_a_folder_entry_that_is_absolute_or_climbs_out_is_never_recognized(
    dm, catalog, root, folder, target
) -> None:
    # A capability's catalog fragment (ADR-021) could otherwise declare the
    # whole filesystem, or the directory above the project, a workspace.
    widened = copy.deepcopy(catalog)
    widened["privileges"]["workspace"]["recognize"]["path"]["folders"] = [folder]
    payload = _write(os.path.normpath(root / target), root)
    assert _decide(dm, _model(dm, widened), widened, payload, root) == "abstain"


def test_a_nested_relative_folder_entry_is_recognized(dm, catalog, root) -> None:
    widened = copy.deepcopy(catalog)
    widened["privileges"]["workspace"]["recognize"]["path"]["folders"] = ["build/scratch"]
    payload = _write(root / "build" / "scratch" / "x", root)
    assert _decide(dm, _model(dm, widened), widened, payload, root) == "allow"


# --- the catalog, the profiles and the realizer ------------------------------------------


def test_the_catalog_names_the_backbone_workspace_folder(catalog) -> None:
    path = catalog["privileges"]["workspace"]["recognize"]["path"]
    assert path["folders"] == [WS]
    assert set(path["tools"]) == {"Read", "Write", "Edit", "MultiEdit", "NotebookEdit"}
    assert set(catalog["privileges"]["workspace"]["recognize"]) == {"path"}


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


def test_the_hook_allows_the_workspace_file_tools_and_defers_elsewhere(root: Path) -> None:
    _hook_tree(root)

    assert _invoke_hook(root, _write(root / WS / "x.md", root)) == "allow"
    assert _invoke_hook(root, _edit(root / WS / "x.md", root)) == "allow"
    assert _invoke_hook(root, _write(root / "src" / "x.py", root)) is None
    assert _invoke_hook(root, _bash(f"cat > {WS}/x.md <<'EOF'\nhi\nEOF", root)) is None
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


def test_capture_tags_file_tools_only(dm, catalog, root) -> None:
    # A shell write into the workspace is judged like any other, so a prompt
    # for one is not a workspace defect.
    assert dm.targets_path_scoped(catalog, _write(root / WS / "y", root), str(root)) is True
    assert dm.targets_path_scoped(catalog, _bash(f"echo x > {WS}/y", root), str(root)) is False
    assert dm.targets_path_scoped(catalog, _write(root / "y", root), str(root)) is False


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
