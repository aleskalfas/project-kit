"""`pkit workspace remove`: removal from the agent workspace (ADR-060 point 10; #2360).

The command reads its paths as the shell expanded them, tests every one, and
removes nothing unless every path lies inside the checkout's own
`.agent-workspace/`. Its tests of what lies inside are the permission hook's
recogniser's, from the running pkit's decision core, and a table of paths here
holds the two to one answer. These run the command through Click on real git
repositories, and drive the module's plan and removal apart where a test must
change the disk between the two, as a swap for a link would.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from click.testing import CliRunner, Result

from project_kit import cli, session_guard, workspace, workspace_remove
from project_kit.install import find_source_kit
from tests import sessions
from tests.adopter_repo import GitRepo

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / ".pkit" / "schemas" / "privilege-catalog.yaml"
HOOKS_CORE = REPO / ".pkit" / "permissions" / "decide.py"
WS = workspace.WORKSPACE_DIR


def _run(*args: str) -> Result:
    return CliRunner().invoke(cli.main, ["workspace", "remove", *args])


def _file(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _register(root: Path, *capabilities: str) -> None:
    """A backbone manifest at `root` that registers each of `capabilities`."""
    lines = ["schema_version: 1", "backbone_version: 1.0.0", "components:"]
    for name in capabilities:
        lines += [
            "  - kind: capability",
            f"    name: {name}",
            f"    manifest: .pkit/capabilities/{name}/manifest.yaml",
        ]
    _file(root / ".pkit" / "manifest.yaml", "\n".join(lines) + "\n")


@pytest.fixture
def repo(tmp_path: Path) -> GitRepo:
    repo = GitRepo.init(tmp_path / "proj")
    repo.commit("initial", {"README.md": "hi\n", "src/a.py": "x = 1\n"})
    (repo.root / WS).mkdir()
    return repo


@pytest.fixture
def root(repo: GitRepo, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The project root, where the command runs."""
    monkeypatch.chdir(repo.root)
    return repo.root


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    """A folder outside every checkout, with a file in it."""
    folder = tmp_path / "outside"
    _file(folder / "keep.txt", "keep\n")
    return folder


# --- what it removes -----------------------------------------------------------------


def test_a_file_and_a_folder_with_everything_in_it_are_removed(root: Path) -> None:
    _file(root / WS / "pr-body.md")
    _file(root / WS / "run" / "deep" / "out.log")
    result = _run(f"{WS}/pr-body.md", f"{WS}/run")
    assert result.exit_code == 0, result.output
    assert not (root / WS / "pr-body.md").exists()
    assert not (root / WS / "run").exists()
    assert (root / WS).is_dir()
    assert "removed  .agent-workspace/pr-body.md" in result.stdout


def test_a_path_is_read_against_the_directory_it_runs_in(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _file(root / WS / "sub" / "x.md")
    monkeypatch.chdir(root / WS / "sub")
    result = _run("x.md")
    assert result.exit_code == 0, result.output
    assert not (root / WS / "sub" / "x.md").exists()


def test_an_absolute_path_inside_is_removed(root: Path) -> None:
    target = _file(root / WS / "x.md")
    assert _run(str(target)).exit_code == 0
    assert not target.exists()


@pytest.mark.parametrize("trailing", ["", "/"])
def test_a_symlink_given_is_removed_as_a_link(root: Path, outside: Path, trailing: str) -> None:
    (root / WS / "to-file").symlink_to(outside / "keep.txt")
    (root / WS / "to-folder").symlink_to(outside, target_is_directory=True)
    result = _run(f"{WS}/to-file{trailing}", f"{WS}/to-folder{trailing}")
    assert result.exit_code == 0, result.output
    assert not os.path.lexists(root / WS / "to-file")
    assert not os.path.lexists(root / WS / "to-folder")
    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep\n"


def test_a_link_inside_a_removed_folder_is_never_followed(root: Path, outside: Path) -> None:
    _file(root / WS / "drafts" / "a.md")
    (root / WS / "drafts" / "out").symlink_to(outside, target_is_directory=True)
    (root / WS / "drafts" / "keep").symlink_to(outside / "keep.txt")
    result = _run(f"{WS}/drafts")
    assert result.exit_code == 0, result.output
    assert not (root / WS / "drafts").exists()
    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep\n"


def test_a_hard_link_loses_only_the_name_given(root: Path, outside: Path) -> None:
    os.link(outside / "keep.txt", root / WS / "linked.txt")
    result = _run(f"{WS}/linked.txt")
    assert result.exit_code == 0, result.output
    assert not (root / WS / "linked.txt").exists()
    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep\n"
    assert (outside / "keep.txt").stat().st_nlink == 1


def test_a_missing_path_inside_refuses_nothing_and_the_call_runs_again(root: Path) -> None:
    _file(root / WS / "x.md")
    first = _run(f"{WS}/x.md", f"{WS}/never-there.md")
    assert first.exit_code == 0, first.output
    assert "missing" in first.stdout and "never-there.md" in first.stdout
    assert not (root / WS / "x.md").exists()
    again = _run(f"{WS}/x.md", f"{WS}/never-there.md")
    assert again.exit_code == 0, again.output


def test_a_path_under_a_file_names_nothing(root: Path) -> None:
    _file(root / WS / "notes.md")
    result = _run(f"{WS}/notes.md/inner")
    assert result.exit_code == 0, result.output
    assert "missing" in result.stdout
    assert (root / WS / "notes.md").exists()


def test_a_path_given_twice_or_under_another_is_gone_once(root: Path) -> None:
    _file(root / WS / "d" / "x.md")
    result = _run(f"{WS}/d", f"{WS}/d/x.md", f"./{WS}/d")
    assert result.exit_code == 0, result.output
    assert not (root / WS / "d").exists()


def test_in_a_linked_worktree_it_removes_from_that_worktrees_own_folder(
    repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = tmp_path / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(worktree))
    _file(worktree / WS / "x.md")
    kept = _file(repo.root / WS / "x.md")
    monkeypatch.setenv(session_guard.CLAUDE_CODE_ANCHOR, str(repo.root))
    monkeypatch.chdir(worktree)
    result = _run(f"{WS}/x.md")
    assert result.exit_code == 0, result.output
    assert not (worktree / WS / "x.md").exists()
    assert kept.exists()


def test_dry_run_tests_every_path_and_removes_nothing(root: Path) -> None:
    target = _file(root / WS / "x.md")
    result = _run("--dry-run", f"{WS}/x.md", f"{WS}/nope")
    assert result.exit_code == 0, result.output
    assert "would remove  .agent-workspace/x.md" in result.stdout
    assert "Dry run: nothing removed." in result.stdout
    assert target.exists()


# --- what it refuses -----------------------------------------------------------------
#
# Each refusal is made beside a path the command would remove, which must stay:
# one refused path refuses the whole call.


def _refused(root: Path, *paths: str) -> Result:
    kept = _file(root / WS / "kept.md")
    result = _run(f"{WS}/kept.md", *paths)
    assert result.exit_code == 1, result.output
    assert "Nothing was removed." in result.stderr
    assert kept.exists()
    return result


@pytest.mark.parametrize(
    "given,why",
    [
        ("src/a.py", "lies outside the agent workspace"),
        ("README.md", "lies outside the agent workspace"),
        (WS, "is the workspace folder itself"),
        (f"{WS}/", "is the workspace folder itself"),
        (f"{WS}/.", "names no entry"),
        (f"{WS}/sub/..", "names no entry"),
        (".", "names no entry"),
        ("..", "names no entry"),
        (f"{WS}/../src/a.py", "lies outside the agent workspace"),
        ("", "names no path"),
    ],
)
def test_a_path_outside_or_naming_no_entry_refuses_the_call(
    root: Path, given: str, why: str
) -> None:
    result = _refused(root, given)
    [line] = [line for line in result.stderr.splitlines() if line.startswith(f"refused  {given} —")]
    assert why in line
    assert (root / "src" / "a.py").exists() and (root / WS).is_dir()


def test_an_absolute_path_outside_is_refused(root: Path, outside: Path) -> None:
    result = _refused(root, str(outside / "keep.txt"), str(outside / "missing.txt"))
    assert result.stderr.count("lies outside the agent workspace") == 2
    assert (outside / "keep.txt").exists()


def test_each_refused_path_is_named_with_why(root: Path) -> None:
    result = _refused(root, "src/a.py", WS)
    assert "refused  src/a.py — lies outside" in result.stderr
    assert "refused  .agent-workspace — is the workspace folder itself" in result.stderr


@pytest.mark.parametrize(
    "given",
    [
        f"{WS}/project-management",
        f"{WS}/project-management/",
        f"{WS}/project-management/drift/index.json",
        f"{WS}/project-management/never-there",
        f"{WS}/PROJECT-MANAGEMENT/drift",
    ],
)
def test_a_capabilitys_lasting_state_is_refused(root: Path, given: str) -> None:
    _register(root, "project-management")
    queue = _file(root / WS / "project-management" / "drift" / "index.json")
    result = _refused(root, given)
    assert "the lasting state of the capability project-management" in result.stderr
    assert queue.exists()


def test_a_pattern_over_the_whole_folder_is_refused_where_lasting_state_stands(
    root: Path,
) -> None:
    _register(root, "living-docs")
    _file(root / WS / "living-docs" / "draft.md")
    scratch = _file(root / WS / "scratch.md")
    every = sorted(str(path.relative_to(root)) for path in (root / WS).iterdir())
    result = _refused(root, *every)
    assert "living-docs" in result.stderr
    assert scratch.exists()


def test_a_child_named_after_no_registered_capability_is_scratch(root: Path) -> None:
    _register(root, "project-management")
    _file(root / WS / "living-docs" / "draft.md")
    assert _run(f"{WS}/living-docs").exit_code == 0
    assert not (root / WS / "living-docs").exists()


def test_the_manifest_of_the_checkout_holding_the_path_is_read_too(
    repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run from a linked worktree whose own manifest registers nothing, the
    main checkout's manifest still marks its lasting state."""
    worktree = tmp_path / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(worktree))
    _register(repo.root, "project-management")
    queue = _file(repo.root / WS / "project-management" / "drift" / "index.json")
    monkeypatch.chdir(worktree)
    result = _run(str(queue))
    assert result.exit_code == 1, result.output
    assert "the lasting state of the capability project-management" in result.stderr
    assert queue.exists()


def test_a_manifest_that_cannot_be_read_refuses(root: Path) -> None:
    _file(root / ".pkit" / "manifest.yaml", "components: [unclosed\n")
    result = _refused(root, f"{WS}/scratch")
    assert "cannot be read" in result.stderr


def test_a_nested_repository_is_refused_whole_and_in_part(root: Path) -> None:
    clone = GitRepo.init(root / WS / "clone")
    clone.commit("initial", {"src/b.py": "y = 2\n"})
    _file(root / WS / "deep" / "inner" / "clone" / ".git" / "HEAD", "ref: refs/heads/main\n")
    result = _refused(root, f"{WS}/clone", f"{WS}/clone/src/b.py", f"{WS}/deep")
    assert result.stderr.count("the operator removes it by hand") == 3
    assert (root / WS / "clone" / "src" / "b.py").exists()
    assert (root / WS / "deep" / "inner" / "clone" / ".git" / "HEAD").exists()


def test_a_nested_git_file_is_refused(root: Path) -> None:
    _file(root / WS / "planted" / ".git", "gitdir: /nowhere\n")
    _file(root / WS / "planted" / "notes.md")
    result = _refused(root, f"{WS}/planted", f"{WS}/planted/notes.md")
    assert result.stderr.count("nested in the workspace") == 2


def test_a_worktree_git_registered_is_left_to_git_worktree_remove(
    repo: GitRepo, root: Path
) -> None:
    nested = root / WS / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(nested))
    result = _refused(root, f"{WS}/wt")
    assert f"`git worktree remove {nested.resolve()}`" in result.stderr
    assert (nested / "README.md").exists()


def test_a_symlinked_workspace_is_never_the_workspace(root: Path, outside: Path) -> None:
    (root / WS).rmdir()
    (root / WS).symlink_to(outside, target_is_directory=True)
    result = _run(f"{WS}/keep.txt", WS)
    assert result.exit_code == 1, result.output
    assert "a symlink, which is never the workspace" in result.stderr
    assert (outside / "keep.txt").exists() and (root / WS).is_symlink()


def test_a_folder_inside_linking_out_is_outside(root: Path, outside: Path) -> None:
    (root / WS / "out").symlink_to(outside, target_is_directory=True)
    _refused(root, f"{WS}/out/keep.txt")
    assert (outside / "keep.txt").exists()


def test_another_repositorys_workspace_is_refused(root: Path, tmp_path: Path) -> None:
    other = GitRepo.init(tmp_path / "other").root
    theirs = _file(other / WS / "x.md")
    _refused(root, str(theirs))
    assert theirs.exists()


def test_the_root_is_never_the_sessions_anchor(
    root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The anchor is the guard's comparand, never a root: a workspace at the
    anchor is outside for a command run in another checkout."""
    anchored = _file(tmp_path / "anchor" / WS / "x.md")
    monkeypatch.setenv(session_guard.CLAUDE_CODE_ANCHOR, str(tmp_path / "anchor"))
    _refused(root, str(anchored))
    assert anchored.exists()


# --- the cross-repository guard --------------------------------------------------------


@pytest.fixture
def foreign(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A session rooted in one repository, the command run in another."""
    _, target = sessions.rooted_elsewhere(tmp_path, monkeypatch)
    (target / WS).mkdir()
    monkeypatch.chdir(target)
    return target


def test_another_repository_than_the_sessions_is_refused_with_no_terminal(
    foreign: Path,
) -> None:
    target = _file(foreign / WS / "x.md")
    result = _run(f"{WS}/x.md")
    assert result.exit_code == 1
    assert "the cross-repository guard refused" in result.stderr
    assert "Nothing was removed" in result.stderr
    assert session_guard.CONFIRM_OPTION not in result.stderr
    assert target.exists()


@pytest.mark.parametrize("answer,removed", [("y\n", True), ("n\n", False)])
def test_at_a_terminal_the_guard_asks(
    foreign: Path, monkeypatch: pytest.MonkeyPatch, answer: str, removed: bool
) -> None:
    target = _file(foreign / WS / "x.md")
    monkeypatch.setattr(session_guard, "_is_a_terminal", lambda stream: True)
    monkeypatch.setattr(session_guard, "_answer", lambda: answer)
    result = _run(f"{WS}/x.md")
    assert "Make the change there anyway?" in result.stderr
    assert result.exit_code == (0 if removed else 1)
    assert target.exists() is not removed


@pytest.mark.parametrize("option", [session_guard.CONFIRM_OPTION, "--yes", "--force"])
def test_no_confirmation_or_widening_is_taken_with_the_call(foreign: Path, option: str) -> None:
    target = _file(foreign / WS / "x.md")
    result = _run(option, f"{WS}/x.md")
    assert result.exit_code == 2
    assert target.exists()


# --- exit codes and the platform -----------------------------------------------------


def test_no_path_is_a_usage_error(root: Path) -> None:
    assert _run().exit_code == 2


def test_a_file_named_like_an_option_stops_the_call(root: Path) -> None:
    kept = _file(root / WS / "kept.md")
    result = _run(f"{WS}/kept.md", "--recursive")
    assert result.exit_code == 2
    assert kept.exists()


def test_after_a_double_dash_an_option_like_name_is_a_path(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    odd = _file(root / WS / "--odd")
    monkeypatch.chdir(root / WS)
    result = _run("--", "--odd")
    assert result.exit_code == 0, result.output
    assert not odd.exists()


def test_a_platform_whose_rmtree_follows_links_is_refused(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _file(root / WS / "x.md")
    monkeypatch.setattr(shutil.rmtree, "avoids_symlink_attacks", False)
    result = _run(f"{WS}/x.md")
    assert result.exit_code == 1
    assert "does not resist symlink attacks" in result.stderr
    assert target.exists()


def test_outside_a_project_tree_nothing_is_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bare = tmp_path / "bare"
    target = _file(bare / WS / "x.md")
    monkeypatch.chdir(bare)
    monkeypatch.setattr(cli, "find_target_root", lambda start=None: None)
    result = _run(f"{WS}/x.md")
    assert result.exit_code == 1
    assert target.exists()


# --- a swap between the test and the removal ------------------------------------------


def _clearance(root: Path) -> session_guard.Clearance:
    passage = session_guard.clear(root, confirmed=False)
    assert isinstance(passage, session_guard.Clearance)
    return passage


def _swap_for_link(path: Path, to: Path) -> None:
    path.rename(path.with_name(path.name + ".moved"))
    path.symlink_to(to, target_is_directory=True)


def test_a_part_swapped_for_a_link_since_the_test_stops_that_path(
    root: Path, outside: Path
) -> None:
    _file(root / WS / "a" / "keep.txt")
    other = _file(root / WS / "other.md")
    plan = workspace_remove.plan([f"{WS}/a/keep.txt", f"{WS}/other.md"], cwd=root, root=root)
    assert not plan.refused
    _swap_for_link(root / WS / "a", outside)
    outcome = workspace_remove.remove(plan, _clearance(root))
    assert [held.given for held in outcome.stopped] == [f"{WS}/a/keep.txt"]
    assert "has turned into a link" in outcome.stopped[0].why
    assert outcome.removed == (f"{WS}/other.md",)
    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep\n"
    assert not other.exists()


def test_the_workspace_swapped_for_a_link_since_the_test_stops_every_path(
    root: Path, outside: Path
) -> None:
    _file(root / WS / "keep.txt")
    plan = workspace_remove.plan([f"{WS}/keep.txt"], cwd=root, root=root)
    assert not plan.refused
    _swap_for_link(root / WS, outside)
    outcome = workspace_remove.remove(plan, _clearance(root))
    assert [held.given for held in outcome.stopped] == [f"{WS}/keep.txt"]
    assert (outside / "keep.txt").exists()


def test_a_folder_swapped_for_a_link_since_the_test_loses_only_the_link(
    root: Path, outside: Path
) -> None:
    _file(root / WS / "drafts" / "a.md")
    plan = workspace_remove.plan([f"{WS}/drafts"], cwd=root, root=root)
    _swap_for_link(root / WS / "drafts", outside)
    outcome = workspace_remove.remove(plan, _clearance(root))
    assert outcome.removed == (f"{WS}/drafts",)
    assert not os.path.lexists(root / WS / "drafts")
    assert (outside / "keep.txt").exists()


def test_a_removal_needs_the_guards_clearance_for_its_root(root: Path, tmp_path: Path) -> None:
    _file(root / WS / "x.md")
    plan = workspace_remove.plan([f"{WS}/x.md"], cwd=root, root=root)
    with pytest.raises(TypeError):
        workspace_remove.remove(plan, None)  # pyright: ignore[reportArgumentType] a removal with no clearance is what the guard refuses
    with pytest.raises(ValueError):
        workspace_remove.remove(plan, _clearance(tmp_path))
    assert (root / WS / "x.md").exists()


# --- one table of paths, read by the command and by the recogniser -----------------------


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hooks_core() -> ModuleType:
    """The decision core the permission hook runs, loaded as the hook loads it."""
    return _load("decide_for_workspace_remove", HOOKS_CORE)


@pytest.fixture(scope="module")
def catalog(hooks_core: ModuleType) -> dict[str, Any]:
    return hooks_core.load_yaml(str(CATALOG))


def _recognised(
    core: ModuleType, catalog: dict[str, Any], target: str, cwd: Path, root: Path
) -> bool:
    request = {"type": "tool", "tool": "Write", "path": target, "root": str(root), "cwd": str(cwd)}
    return "workspace" in core.recognized_privileges(catalog, request)


@pytest.fixture
def scene(repo: GitRepo, tmp_path: Path, outside: Path) -> dict[str, tuple[Path, Path, bool]]:
    """Each case: (the path, the directory it is read from, whether it lies inside)."""
    root = repo.root
    _file(root / WS / "a.md")
    (root / WS / "sub").mkdir()
    (root / WS / "out").symlink_to(outside, target_is_directory=True)
    (root / WS / "in").symlink_to(root / WS / "sub", target_is_directory=True)
    GitRepo.init(root / WS / "clone").commit("initial", {"b.py": "y = 2\n"})
    _file(root / WS / "planted" / ".git", "gitdir: /nowhere\n")
    worktree = tmp_path / "wt"
    repo.git("worktree", "add", "-q", "-b", "topic", str(worktree))
    (worktree / WS).mkdir()
    other = GitRepo.init(tmp_path / "other").root
    (other / WS).mkdir()
    spoof = tmp_path / "spoof"
    (spoof / WS).mkdir(parents=True)
    _file(spoof / ".git", f"gitdir: {root / '.git'}\n")
    return {
        "a file in the folder": (root / WS / "a.md", root, True),
        "a new file in a new folder": (root / WS / "new" / "x.md", root, True),
        "a relative path": (Path(WS) / "a.md", root, True),
        "relative, from inside the folder": (Path("b.md"), root / WS / "sub", True),
        "the folder itself": (root / WS, root, False),
        "beside the folder": (root / "src" / "a.py", root, False),
        "out and back in": (root / WS / ".." / "README.md", root, False),
        "through a link out": (root / WS / "out" / "keep.txt", root, False),
        "through a link that stays in": (root / WS / "in" / "x.md", root, True),
        "in a nested clone": (root / WS / "clone" / "b.py", root, False),
        "beside a planted pointer": (root / WS / "planted" / "x.md", root, False),
        "a linked worktree's folder": (worktree / WS / "x.md", worktree, True),
        "another repository's folder": (other / WS / "x.md", root, False),
        "a folder a planted pointer claims": (spoof / WS / "x.md", spoof, False),
        "outside every checkout": (outside / "keep.txt", root, False),
    }


def test_the_command_and_the_recogniser_read_one_table_of_paths(
    repo: GitRepo,
    scene: dict[str, tuple[Path, Path, bool]],
    hooks_core: ModuleType,
    catalog: dict[str, Any],
) -> None:
    root = repo.root
    for case, (target, cwd, expected) in scene.items():
        recognised = _recognised(hooks_core, catalog, str(target), cwd, root)
        removable = workspace_remove.inside(str(target), str(cwd), str(root))
        assert (recognised, removable) == (expected, expected), case


def test_the_two_part_where_a_removal_changes_another_entry_than_a_write(
    repo: GitRepo, outside: Path, hooks_core: ModuleType, catalog: dict[str, Any]
) -> None:
    """A write follows a symlink and changes a hard-linked file at every name,
    so the recogniser leaves both out. A removal changes the entry given: the
    link, or the one name."""
    root = repo.root
    (root / WS / "link").symlink_to(outside / "keep.txt")
    os.link(outside / "keep.txt", root / WS / "hard.txt")
    for name in ("link", "hard.txt"):
        target = str(root / WS / name)
        assert not _recognised(hooks_core, catalog, target, root, root), name
        assert workspace_remove.inside(target, str(root), str(root)), name


def test_the_tests_are_the_running_pkits_own_never_the_roots(root: Path) -> None:
    expected = find_source_kit() / "permissions" / "decide.py"
    workspace_remove.decision_core.cache_clear()
    assert Path(str(workspace_remove.decision_core().__file__)) == expected
    workspace_remove.decision_core.cache_clear()
    _file(root / ".pkit" / "permissions" / "decide.py", "raise SystemExit('the root\\'s own')\n")
    target = _file(root / WS / "x.md")
    result = _run(f"{WS}/x.md")
    assert result.exit_code == 0, result.output
    assert not target.exists()
