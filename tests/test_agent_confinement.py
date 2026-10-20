"""A confined agent run: its clone, its check and its files (ADR-066 points 6 to 8; #1744).

- the request reaches the runner the clone registers, from the clone's root, in
  the confined form: no folder, the `confined` block with the run's folders, the
  run's rules and its exclusions, and the brief's markers replaced;
- the clone shares no object with the person's repository, and fetches a commit
  only a remote-tracking reference holds;
- the check finds a changed tracked file, a new ignored file, a moved and a new
  reference, and passes a clean run;
- the copy refuses a link, a file with two links, a name read as `.git`, a set
  past its bound and anything that is not a regular file, and skips the temp
  folder; what it refuses is a breach;
- the marker refuses both forms before anything is read;
- the run folder is removed on every exit, and a stale one first;
- the exclusion is passed only where ADR-027's test holds;
- the run root is refused when it is a link, writable by others, or inside a
  working tree;
- the run's `pkit` starts from the clone's root with git pointed at the clone;
- the command's confined form: its options, its document and what it prints.

No real harness runs: the project registers a stub adapter whose runner records
the request it got and answers as the test tells it. The run's rules come from a
stand-in for `project_kit.run_rules`, and provisioning is stubbed.
"""

from __future__ import annotations

import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import types
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import agent_confinement, agent_runs, permissions, provisioning
from project_kit.agent_confinement import names_git
from project_kit.agent_runs import Request, run_agent
from project_kit.cli import main
from tests.adopter_repo import MakeAdopterRepo
from tests.test_agent_runs import _drop_claude_code_runner, _register

# The shared temp folders as the module finds them; the `project` fixture empties them.
_TEMP_FOLDERS = agent_confinement.temp_folders

AGENT = "living-docs"
RULES_OF = "project-management:fix-drift"
EXCLUDED = ("pkit", "analysis", "propose")

# A runner that records the request it got, where it ran from and what it is,
# runs the test's `STUB_DO` with the request in hand, and answers a finished run,
# laid over with the test's `STUB_ANSWER`.
_STUB_RUNNER = """
import json, os, sys
from pathlib import Path
request = json.loads(sys.stdin.read())
Path(os.environ["STUB_RECORD"]).write_text(json.dumps({
    "request": request,
    "cwd": os.getcwd(),
    "script": os.path.abspath(__file__),
    "bytecode": os.environ.get("PYTHONDONTWRITEBYTECODE"),
}))
clone = Path(request["confined"]["working_copy"])
workspace = Path(request["confined"]["workspace"])
exec(os.environ.get("STUB_DO", ""))
answer = {"schema_version": 1, "ending": "finished", "exit_code": 0, "output": "done\\n"}
answer.update(json.loads(os.environ.get("STUB_ANSWER", "{}")))
print(json.dumps(answer))
"""


@dataclass(frozen=True)
class _Projection:
    """A stand-in for `run_rules.RunProjection`."""

    allow: tuple[dict[str, Any], ...]
    deny: tuple[dict[str, Any], ...]
    excluded_candidates: tuple[tuple[str, ...], ...]
    forms: tuple[str, ...] = ()


@dataclass
class _RunRules:
    """A stand-in for `project_kit.run_rules`: records each call, and answers with
    `answer`, or with the projection it builds for the clone."""

    answer: str | None = None
    calls: list[tuple[Path, str, str, Path, Path]] = field(default_factory=list)

    def project_run(
        self, root: Path, rules_of: str, agent: str, *, working_copy: Path, workspace: Path
    ) -> _Projection | str:
        self.calls.append((root, rules_of, agent, working_copy, workspace))
        if self.answer is not None:
            return self.answer
        return _Projection(
            allow=(
                {"tool": "Read", "folder": str(working_copy)},
                {"command": ["git", "-C", str(working_copy), "log"]},
            ),
            deny=({"tool": "Edit"}, {"command": ["gh"]}),
            excluded_candidates=(EXCLUDED,),
        )


@dataclass(frozen=True)
class _Project:
    root: Path
    commit: str
    state: Path
    files_to: Path
    record: Path
    rules: _RunRules

    @property
    def run_root(self) -> Path:
        return self.state.resolve() / "pkit" / "agent-runs"

    def seen(self) -> dict[str, Any]:
        """What the stub runner recorded of its run."""
        recorded: dict[str, Any] = json.loads(self.record.read_text(encoding="utf-8"))
        return recorded

    def run_folders(self) -> list[str]:
        if not self.run_root.is_dir():
            return []
        return sorted(entry.name for entry in self.run_root.iterdir())


def _git(root: Path, *args: str) -> str:
    """Run git in a test's own repository, never signing."""
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--no-verify", "-m", message)
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> _Project:
    """A committed project whose one runner is the stub's, a state folder outside it,
    a folder for the run's files, and the run's rules, provisioning and ADR-027's test
    stood in for."""
    root = make_adopter_repo(root=tmp_path / "project").root
    _drop_claude_code_runner(root)
    _register(root, "adapter", "stub-harness", _STUB_RUNNER)
    (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (root / "README.md").write_text("A project.\n", encoding="utf-8")
    commit = _commit(root, "the project")
    files_to = tmp_path / "files"
    files_to.mkdir()
    record = tmp_path / "record.json"
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("STUB_RECORD", str(record))
    monkeypatch.delenv("STUB_DO", raising=False)
    monkeypatch.delenv("STUB_ANSWER", raising=False)
    monkeypatch.setattr(provisioning, "ensure", lambda _root, **_: [])
    monkeypatch.setattr(permissions, "_uv_required_exclusion", lambda _root: False)
    # The test's state folder lies in the system's temp folder, where a real run root
    # never does: the list of shared temp folders is emptied for it.
    monkeypatch.setattr(agent_confinement, "temp_folders", list)
    rules = _RunRules()
    module = types.ModuleType("project_kit.run_rules")
    monkeypatch.setattr(module, "project_run", rules.project_run, raising=False)
    monkeypatch.setitem(sys.modules, "project_kit.run_rules", module)
    return _Project(root, commit, tmp_path / "state", files_to, record, rules)


def _confined(project: _Project, brief: str = "Fix the drift.", **overrides: Any) -> Request:
    fields: dict[str, Any] = {
        "agent": AGENT,
        "brief": brief,
        "folder": None,
        "limit_seconds": 60,
        "commit": project.commit,
        "rules_of": RULES_OF,
        "files_to": project.files_to,
        **overrides,
    }
    return Request(**fields)


# --- the request the runner gets --------------------------------------------------


def test_a_confined_run_reaches_the_clones_runner_in_the_confined_form(
    project: _Project,
) -> None:
    run = run_agent(project.root, _confined(project))

    assert (run.ending, run.exit_code, run.runner) == (agent_runs.FINISHED, 0, "stub-harness")
    seen = project.seen()
    request = seen["request"]
    confined = request["confined"]
    clone = Path(confined["working_copy"])
    workspace = clone / ".agent-workspace"
    assert set(request) == {
        "schema_version",
        "agent",
        "brief",
        "limit_seconds",
        "effort",
        "confined",
    }
    assert (request["schema_version"], request["agent"]) == (1, AGENT)
    assert clone.parent.parent == project.run_root
    assert confined == {
        "working_copy": str(clone),
        "workspace": str(workspace),
        "temp": str(workspace / ".tmp"),
        "pkit_folder": str(clone.parent / "bin"),
        "project_root": str(project.root.resolve()),
        "rules": {
            "allow": [
                {"tool": "Read", "folder": str(clone)},
                {"command": ["git", "-C", str(clone), "log"]},
            ],
            "deny": [{"tool": "Edit"}, {"command": ["gh"]}],
        },
        "excluded": [],
    }
    # The clone's own runner, from the clone's root, writing no bytecode there.
    assert Path(seen["script"]).is_relative_to(clone)
    assert Path(seen["cwd"]).resolve() == clone.resolve()
    assert seen["bytecode"] == "1"
    # The run's rules were read in the clone, for this command and agent.
    assert project.rules.calls == [(clone, RULES_OF, AGENT, clone, workspace)]
    assert run.as_json() | {"output": None} == {
        "schema_version": 1,
        "agent": AGENT,
        "runner": "stub-harness",
        "ending": "finished",
        "exit_code": 0,
        "output": None,
        "diagnostics": "",
        "reason": "",
        "refused_calls": [],
        "confined": True,
        "commit": project.commit,
        "check": {"verdict": "clean", "changes": []},
        "files": str(project.files_to),
        "excluded": [],
    }


def test_the_briefs_markers_are_replaced_every_time_they_occur(project: _Project) -> None:
    brief = (
        "Read {{pkit:working-copy}}, and only {{pkit:working-copy}}. Write {{pkit:workspace}}. "
        "Temp: {{pkit:temp}}. Commit {{pkit:commit}}. Quoted: { {pkit:commit}}. "
        "Unknown: {{pkit:other}}."
    )
    run_agent(project.root, _confined(project, brief))
    seen = project.seen()["request"]
    clone = seen["confined"]["working_copy"]
    assert seen["brief"] == (
        f"Read {clone}, and only {clone}. Write {clone}/.agent-workspace. "
        f"Temp: {clone}/.agent-workspace/.tmp. Commit {project.commit}. "
        "Quoted: { {pkit:commit}}. Unknown: {{pkit:other}}."
    )


def test_the_calls_the_harness_refused_reach_the_document(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = [{"tool": "Bash", "input": "gh pr list"}]
    monkeypatch.setenv("STUB_ANSWER", json.dumps({"refused_calls": calls, "start_report": {}}))
    run = run_agent(project.root, _confined(project))
    assert run.as_json()["refused_calls"] == calls


def test_a_provisioning_failure_is_a_warning_not_a_refusal(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        provisioning,
        "ensure",
        lambda _root, **_: [
            ("unchanged", "query command 'a' (cap) — already provisioned"),
            ("warning", "query command 'b' (cap) not provisioned: no network"),
        ],
    )
    run = run_agent(project.root, _confined(project))
    assert run.ending == agent_runs.FINISHED
    assert run.diagnostics == "provisioning: query command 'b' (cap) not provisioned: no network"


# --- the exclusion ----------------------------------------------------------------


@pytest.mark.parametrize("required", [True, False])
def test_the_exclusion_is_passed_only_where_adr_027s_test_holds(
    project: _Project, monkeypatch: pytest.MonkeyPatch, required: bool
) -> None:
    tested: list[Path] = []

    def uv_required(root: Path) -> bool:
        tested.append(root)
        return required

    monkeypatch.setattr(permissions, "_uv_required_exclusion", uv_required)
    run = run_agent(project.root, _confined(project))
    expected = [list(EXCLUDED)] if required else []
    confined = project.seen()["request"]["confined"]
    assert confined["excluded"] == expected
    assert run.as_json()["excluded"] == expected
    assert tested == [Path(confined["working_copy"])]  # judged in the clone


# --- the clone --------------------------------------------------------------------


def _object_files(repository: Path) -> list[Path]:
    return [path for path in (repository / ".git" / "objects").rglob("*") if path.is_file()]


def test_the_clone_shares_no_object_with_the_repository(project: _Project, tmp_path: Path) -> None:
    clone = tmp_path / "elsewhere" / "clone"
    clone.parent.mkdir()
    agent_confinement.make_clone(project.root, project.commit, clone)

    source = {(held.st_dev, held.st_ino) for held in map(os.stat, _object_files(project.root))}
    cloned = [os.stat(path) for path in _object_files(clone)]
    assert cloned
    assert all(held.st_nlink == 1 for held in cloned)
    assert not source & {(held.st_dev, held.st_ino) for held in cloned}
    assert not (clone / ".git" / "objects" / "info" / "alternates").exists()
    assert not (clone / ".git" / "hooks").exists()
    assert (clone / ".git" / "HEAD").read_text(encoding="utf-8").strip() == project.commit
    assert (clone / "README.md").read_text(encoding="utf-8") == "A project.\n"


def test_a_commit_only_a_remote_tracking_reference_holds_is_fetched(
    project: _Project, tmp_path: Path
) -> None:
    """The default branch resolves to its remote-tracking reference first (COR-054
    point 2), which a clone does not copy."""
    ahead = _git(
        project.root,
        "commit-tree",
        f"{project.commit}^{{tree}}",
        "-p",
        project.commit,
        "-m",
        "ahead",
    )
    _git(project.root, "update-ref", "refs/remotes/origin/main", ahead)
    clone = tmp_path / "elsewhere" / "clone"
    clone.parent.mkdir()
    agent_confinement.make_clone(project.root, ahead, clone)
    assert (clone / ".git" / "HEAD").read_text(encoding="utf-8").strip() == ahead


def test_a_commit_the_repository_does_not_hold_is_a_problem(project: _Project) -> None:
    request = _confined(project, commit="f" * 40)
    assert request.problem(project.root) == f"the repository holds no commit {'f' * 40}"
    assert request.problem() is None  # with no repository named, only the form is checked


@pytest.mark.parametrize(
    ("overrides", "says"),
    [
        ({"commit": "abc123"}, "not a full commit id"),
        ({"commit": "A" * 40}, "not a full commit id"),
        ({"rules_of": "project-management"}, "name no command"),
        ({"rules_of": "../x:y"}, "name no command"),
        ({"rules_of": "pm:fix drift"}, "name no command"),
        ({"files_to": Path("relative")}, "is not a directory"),
        ({"files_to": None}, "all three"),
        ({"commit": None}, "all three"),
    ],
)
def test_a_confined_request_with_a_problem_is_refused_before_any_clone(
    project: _Project, overrides: dict[str, Any], says: str
) -> None:
    run = run_agent(project.root, _confined(project, **overrides))
    assert run.ending == agent_runs.REFUSED
    assert says in run.reason
    assert run.as_json()["check"] == {"verdict": "not-run", "changes": []}
    assert project.run_folders() == []


def test_a_commit_that_holds_the_workspace_is_refused(project: _Project) -> None:
    (project.root / ".agent-workspace").mkdir(exist_ok=True)
    (project.root / ".agent-workspace" / "planted.md").write_text("x", encoding="utf-8")
    _git(project.root, "add", "-f", ".agent-workspace/planted.md")
    commit = _commit(project.root, "plant a workspace")
    run = run_agent(project.root, _confined(project, commit=commit))
    assert run.ending == agent_runs.REFUSED
    assert "the commit holds something at `.agent-workspace`" in run.reason
    assert run.check == agent_confinement.CHECK_NOT_RUN
    assert project.run_folders() == []


# --- the check --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("do", "line"),
    [
        (
            "Path(clone, 'README.md').write_text('changed')",
            "changed: README.md",
        ),
        (
            "Path(clone, 'debug.log').write_text('ignored')",
            "appeared: debug.log",
        ),
        (
            "Path(clone, '.git', 'HEAD').write_text('0' * 40 + '\\n')",
            "reference moved: .git/HEAD",
        ),
        (
            "Path(clone, '.git', 'refs', 'heads', 'planted').write_text(str(clone))",
            "reference appeared: .git/refs/heads/planted",
        ),
        (
            "os.remove(Path(clone, '.gitignore'))",
            "removed: .gitignore",
        ),
        (
            "with open(Path(clone, '.git', 'config'), 'a') as c:\n"
            "    c.write('[core]\\n\\tfsmonitor = x\\n')\n",
            "changed: .git/config",
        ),
        (
            "Path(clone, '.git', 'hooks').mkdir()\n"
            "Path(clone, '.git', 'hooks', 'post-checkout').write_text('#!/bin/sh\\n')\n",
            ("appeared: .git/hooks", "appeared: .git/hooks/post-checkout"),
        ),
        (
            "Path(clone, '.git', 'info').mkdir()\n"
            "Path(clone, '.git', 'info', 'attributes').write_text('* filter=x\\n')\n",
            ("appeared: .git/info", "appeared: .git/info/attributes"),
        ),
    ],
    ids=[
        "tracked-file-changed",
        "ignored-file-appeared",
        "reference-moved",
        "reference-appeared",
        "file-removed",
        "git-config-changed",
        "hook-planted",
        "info-planted",
    ],
)
def test_the_check_finds_what_the_run_changed_outside_the_workspace(
    project: _Project, monkeypatch: pytest.MonkeyPatch, do: str, line: str | tuple[str, ...]
) -> None:
    monkeypatch.setenv("STUB_DO", do)
    run = run_agent(project.root, _confined(project))
    assert run.ending == agent_runs.FINISHED, run.reason
    lines = (line,) if isinstance(line, str) else line
    assert run.check == agent_confinement.Check("breach", lines)


def test_the_check_leaves_out_the_index_and_the_objects(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A git call that only reads may refresh the index, and the objects are named
    by their content: neither is read by the check."""
    monkeypatch.setenv(
        "STUB_DO",
        "Path(clone, '.git', 'index').write_bytes(b'refreshed')\n"
        "Path(clone, '.git', 'objects', 'stray').write_text('x')\n",
    )
    run = run_agent(project.root, _confined(project))
    assert run.check == agent_confinement.Check("clean")


def test_what_the_run_writes_in_its_workspace_is_its_files(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "STUB_DO",
        "(workspace / 'docs').mkdir()\n"
        "(workspace / 'docs' / 'answer.json').write_text('{}')\n"
        "(workspace / '.tmp' / 'scratch').write_text('x')\n",
    )
    run = run_agent(project.root, _confined(project))
    assert run.check == agent_confinement.Check("clean")
    assert sorted(
        str(path.relative_to(project.files_to)) for path in project.files_to.rglob("*")
    ) == ["docs", "docs/answer.json"]


def test_what_the_copy_refuses_is_a_breach(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "STUB_DO",
        "(workspace / 'kept.md').write_text('kept')\n"
        "os.symlink('/etc/hosts', workspace / 'hosts')\n",
    )
    run = run_agent(project.root, _confined(project))
    assert run.check == agent_confinement.Check("breach", ("refused: hosts: a symbolic link",))
    assert (project.files_to / "kept.md").read_text(encoding="utf-8") == "kept"
    assert not (project.files_to / "hosts").exists()


def test_a_runner_that_ends_without_an_answer_still_has_its_clone_checked(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "STUB_DO",
        "Path(clone, 'debug.log').write_text('x')\nsys.exit(4)\n",
    )
    run = run_agent(project.root, _confined(project))
    assert run.ending == agent_runs.NO_ANSWER
    assert run.check == agent_confinement.Check("breach", ("appeared: debug.log",))


def test_the_check_reads_an_unreadable_folder_as_a_breach(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    (clone / ".git" / "refs").mkdir(parents=True)
    (clone / ".git" / "HEAD").write_text("x\n", encoding="utf-8")
    (clone / "sealed").mkdir()
    before = agent_confinement.record(clone)
    (clone / "sealed").chmod(0)
    try:
        check = agent_confinement.check(clone, before)
    finally:
        (clone / "sealed").chmod(0o700)
    assert check.verdict == "breach"
    assert any(line.startswith("unreadable: sealed:") for line in check.changes)


def test_a_name_that_is_not_one_line_is_shown_on_one(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    (clone / ".git" / "refs").mkdir(parents=True)
    before = agent_confinement.record(clone)
    (clone / "two\nlines").write_text("x", encoding="utf-8")
    check = agent_confinement.check(clone, before)
    assert check.changes == ("appeared: 'two\\nlines'",)


# --- the copy ---------------------------------------------------------------------


def _copied(files_to: Path) -> list[str]:
    return sorted(str(path.relative_to(files_to)) for path in files_to.rglob("*"))


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    folder = tmp_path / "workspace"
    (folder / ".tmp").mkdir(parents=True)
    (folder / ".tmp" / "scratch").write_text("never copied", encoding="utf-8")
    (folder / "answer.json").write_text("{}", encoding="utf-8")
    return folder


def test_the_copy_takes_regular_files_and_skips_the_temp_folder(
    workspace: Path, tmp_path: Path
) -> None:
    (workspace / "docs").mkdir()
    (workspace / "docs" / "diff.patch").write_text("--- a\n", encoding="utf-8")
    (workspace / "docs" / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (workspace / "docs" / "run.sh").chmod(0o755)
    files_to = tmp_path / "files"
    files_to.mkdir()
    assert agent_confinement.copy_files(workspace, files_to) == []
    assert _copied(files_to) == ["answer.json", "docs", "docs/diff.patch", "docs/run.sh"]
    assert not os.access(files_to / "docs" / "run.sh", os.X_OK)  # data, never a program


@pytest.mark.parametrize(
    ("plant", "line"),
    [
        (lambda w: os.symlink(w / "answer.json", w / "link"), "refused: link: a symbolic link"),
        (
            lambda w: os.link(w / "answer.json", w / "twin"),
            "refused: answer.json: a file with more than one link",
        ),
        (
            lambda w: (w / ".GIT").mkdir() or (w / ".GIT" / "config").write_text("x"),
            "refused: .GIT: a name a file system may read as .git",
        ),
        (lambda w: os.mkfifo(w / "pipe"), "refused: pipe: not a regular file"),
    ],
    ids=["link", "hard-link", "dot-git-folder", "fifo"],
)
def test_the_copy_refuses_what_is_not_a_plain_file_of_the_run(
    workspace: Path, tmp_path: Path, plant: Callable[[Path], object], line: str
) -> None:
    plant(workspace)
    files_to = tmp_path / "files"
    files_to.mkdir()
    refused = agent_confinement.copy_files(workspace, files_to)
    assert line in refused
    assert not any(name.startswith((".GIT", "link", "pipe")) for name in _copied(files_to))


def test_the_copy_refuses_a_set_past_its_bound(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_confinement, "COPY_LIMIT_BYTES", 10)
    (workspace / "answer.json").write_text("123456", encoding="utf-8")
    (workspace / "more.json").write_text("123456", encoding="utf-8")
    files_to = tmp_path / "files"
    files_to.mkdir()
    refused = agent_confinement.copy_files(workspace, files_to)
    assert refused == ["refused: more.json: past the bound of 10 bytes on the run's files"]
    assert _copied(files_to) == ["answer.json"]


def test_the_copy_never_writes_over_what_the_folder_holds(workspace: Path, tmp_path: Path) -> None:
    files_to = tmp_path / "files"
    files_to.mkdir()
    (files_to / "answer.json").write_text("the caller's", encoding="utf-8")
    refused = agent_confinement.copy_files(workspace, files_to)
    assert [line.split(": ")[1] for line in refused] == ["answer.json"]
    assert (files_to / "answer.json").read_text(encoding="utf-8") == "the caller's"


def test_a_link_swapped_in_after_the_entry_was_judged_is_not_followed(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A process the run left behind swaps a link in for a folder, and for a file,
    after the copy judged each entry: the copy opens each from its folder, following
    no link, so it reads neither target."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("the person's", encoding="utf-8")
    (workspace / "docs").symlink_to(outside)
    (workspace / "leak.txt").symlink_to(outside / "secret.txt")
    judged = agent_confinement._lstat_at

    def before_the_swap(folder: int, name: str) -> os.stat_result:
        """Each link as the entry it replaced: a folder, a file."""
        if name == "docs":
            return os.stat(outside)
        if name == "leak.txt":
            return os.stat(outside / "secret.txt")
        return judged(folder, name)

    monkeypatch.setattr(agent_confinement, "_lstat_at", before_the_swap)
    files_to = tmp_path / "files"
    files_to.mkdir()
    refused = agent_confinement.copy_files(workspace, files_to)
    # Opened without following, a link reads as a link, or, opened as a folder on
    # some systems, as no folder: never as its target.
    docs, leak = refused
    assert docs in (
        "refused: docs: a symbolic link",
        "refused: docs: no longer a folder when it was opened",
    )
    assert leak == "refused: leak.txt: a symbolic link"
    assert _copied(files_to) == ["answer.json"]


def test_the_copy_refuses_the_entries_past_its_bound(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_confinement, "COPY_LIMIT_ENTRIES", 3)
    for name in ("b", "c", "d", "e"):
        (workspace / name).write_text(name, encoding="utf-8")
    files_to = tmp_path / "files"
    files_to.mkdir()
    refused = agent_confinement.copy_files(workspace, files_to)
    assert refused == [
        "refused: d: it and every entry after it: past the bound of 3 entries on the run's files"
    ]
    assert _copied(files_to) == ["answer.json", "b", "c"]


def test_the_copy_refuses_folders_past_its_depth(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_confinement, "COPY_LIMIT_DEPTH", 2)
    (workspace / "a" / "b" / "c").mkdir(parents=True)
    (workspace / "a" / "b" / "ok.txt").write_text("ok", encoding="utf-8")
    (workspace / "a" / "b" / "c" / "deep.txt").write_text("deep", encoding="utf-8")
    files_to = tmp_path / "files"
    files_to.mkdir()
    refused = agent_confinement.copy_files(workspace, files_to)
    assert refused == ["refused: a/b/c: past the bound of 2 folders deep"]
    assert _copied(files_to) == ["a", "a/b", "a/b/ok.txt", "answer.json"]


def test_the_removal_never_changes_a_links_target(tmp_path: Path) -> None:
    """A run folder the run sealed is opened up and removed, and a link in it, or in
    place of it, never has its target's mode changed."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("the person's", encoding="utf-8")
    folder = tmp_path / "run"
    (folder / "sealed").mkdir(parents=True)
    (folder / "sealed" / "x").write_text("x", encoding="utf-8")
    (folder / "locked").mkdir()
    (folder / "locked" / "y").write_text("y", encoding="utf-8")
    (folder / "elsewhere").symlink_to(outside)
    linked = tmp_path / "linked-run"
    linked.symlink_to(outside)
    (folder / "sealed").chmod(0o500)
    (folder / "locked").chmod(0)
    outside.chmod(0o500)
    try:
        agent_confinement.remove_tree(folder)
        agent_confinement._make_folders_writable(linked)
        assert not folder.exists()
        assert stat.S_IMODE(outside.stat().st_mode) == 0o500
        assert (outside / "keep").read_text(encoding="utf-8") == "the person's"
    finally:
        outside.chmod(0o700)


@pytest.mark.parametrize(
    ("name", "is_git"),
    [
        (".git", True),
        (".GIT", True),
        (".Git", True),
        (".git.", True),
        (".git ", True),
        (".git. .", True),
        (".git:stream", True),
        ("git~1", True),
        ("GIT~1", True),
        (".g‌it", True),
        ("﻿.git", True),
        (".git⁪", True),
        (".github", False),
        (".gitignore", False),
        ("git", False),
        ("git~2", False),
        ("my.git", False),
    ],
)
def test_a_name_a_file_system_may_read_as_dot_git(name: str, is_git: bool) -> None:
    assert names_git(name) is is_git


# --- the marker -------------------------------------------------------------------


def test_the_marker_refuses_a_confined_run_before_anything_is_made(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(agent_runs.MARKER_ENV, "")
    run = run_agent(project.root, _confined(project))
    assert (run.ending, run.reason) == (agent_runs.REFUSED, agent_runs.INSIDE_A_RUN)
    assert run.as_json()["check"] == {"verdict": "not-run", "changes": []}
    assert not project.state.exists()
    assert not project.record.exists()


class _UnreadStdin(io.BytesIO):
    """A standard input that fails the test if the command reads it."""

    def read(self, size: int | None = -1) -> bytes:
        if size == 0:  # click probes a stream with an empty read
            return b""
        raise AssertionError("the command read its standard input")


def test_the_command_refuses_a_confined_run_inside_a_run(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(agent_runs.MARKER_ENV, "1")
    result = CliRunner().invoke(main, [*_confined_args(project), "--json"], input=_UnreadStdin())
    assert result.exit_code == 1, result.output
    document = json.loads(result.stdout)
    assert (document["ending"], document["confined"], document["commit"]) == (
        "refused",
        True,
        project.commit,
    )
    assert document["check"] == {"verdict": "not-run", "changes": []}
    assert not project.state.exists()


# --- the run folder ---------------------------------------------------------------


def _interrupted(*_args: object, **_kwargs: object) -> None:
    raise KeyboardInterrupt


@pytest.mark.parametrize(
    "ending",
    ["clean", "breach", "no-answer", "rules-refuse", "interrupted"],
)
def test_the_run_folder_is_removed_on_every_exit(
    project: _Project, monkeypatch: pytest.MonkeyPatch, ending: str
) -> None:
    if ending == "breach":
        monkeypatch.setenv("STUB_DO", "Path(clone, 'x.log').write_text('x')")
    elif ending == "no-answer":
        monkeypatch.setenv("STUB_DO", "sys.exit(3)")
    elif ending == "rules-refuse":
        project.rules.answer = "the grant names no such fixer"
    if ending == "interrupted":
        monkeypatch.setattr(agent_runs.command_runner, "run_command", _interrupted)
        with pytest.raises(KeyboardInterrupt):
            run_agent(project.root, _confined(project))
    else:
        run = run_agent(project.root, _confined(project))
        if ending == "rules-refuse":
            assert (run.ending, run.reason) == (agent_runs.REFUSED, "the grant names no such fixer")
            assert run.check == agent_confinement.CHECK_NOT_RUN
    assert project.run_root.is_dir()
    assert project.run_folders() == []


def test_a_stale_run_folder_is_removed_first(project: _Project) -> None:
    gone = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getpid())"],
        capture_output=True,
        text=True,
        check=True,
    )
    dead = int(gone.stdout)
    project.run_root.mkdir(parents=True, mode=0o700)
    stale = project.run_root / f"run-{dead}-killed"
    (stale / "clone" / "sealed").mkdir(parents=True)
    (stale / "pid").write_text(f"{dead}\n", encoding="utf-8")
    (stale / "clone").chmod(0o500)  # its run took away the write that removing needs
    unwritten = project.run_root / f"run-{dead}-unwritten"  # killed before its pid file
    unwritten.mkdir()
    live = project.run_root / f"run-{os.getppid()}-live"
    live.mkdir()
    (live / "pid").write_text(f"{os.getppid()}\n", encoding="utf-8")
    foreign = project.run_root / "notes"
    foreign.mkdir()

    run_agent(project.root, _confined(project))

    assert project.run_folders() == ["notes", f"run-{os.getppid()}-live"]


# --- the run root -----------------------------------------------------------------


def test_the_run_root_is_made_for_this_user_alone(project: _Project) -> None:
    root = agent_confinement.run_root(project.root)
    assert root == project.run_root
    assert stat.S_IMODE(root.stat().st_mode) == 0o700


def test_the_shared_temp_folders_are_the_systems_and_tmpdirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path / "harness-temp"))
    folders = _TEMP_FOLDERS()
    named = [tempfile.gettempdir(), str(tmp_path / "harness-temp"), "/tmp", "/private/tmp"]
    assert {Path(folder).resolve() for folder in named} <= set(folders)
    assert {Path("/var/folders").resolve(), Path("/private/var/folders").resolve()} <= set(folders)


def test_a_run_root_in_a_shared_temp_folder_is_refused_before_anything_is_made(
    project: _Project, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_confinement, "temp_folders", _TEMP_FOLDERS)
    # Only the test's folder is shared, whichever temp folder the machine has.
    monkeypatch.setattr(agent_confinement, "SHARED_TEMP_FOLDERS", (str(tmp_path),))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "system-temp"))
    monkeypatch.delenv("TMPDIR", raising=False)
    run = run_agent(project.root, _confined(project))
    assert run.ending == agent_runs.REFUSED
    assert f"lies inside the temp folder {tmp_path.resolve()}" in run.reason
    assert "ADR-066 point 7" in run.reason
    assert not project.state.exists()
    assert not project.record.exists()


def test_a_relative_state_folder_is_not_used(
    project: _Project, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", "relative/state")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = agent_confinement.run_root(project.root)
    assert root == (tmp_path / "home").resolve() / ".local" / "state" / "pkit" / "agent-runs"


def _linked(project: _Project, tmp_path: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir(mode=0o700)
    (project.state / "pkit").mkdir(parents=True)
    (project.state / "pkit" / "agent-runs").symlink_to(target)


def _open_to_the_group(
    project: _Project, _tmp_path: Path, _monkeypatch: pytest.MonkeyPatch
) -> None:
    (project.state / "pkit" / "agent-runs").mkdir(parents=True)
    (project.state / "pkit" / "agent-runs").chmod(0o770)


def _inside_the_working_tree(
    project: _Project, _tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(project.root / "state"))


@pytest.mark.parametrize(
    ("make", "says"),
    [
        (_linked, "is a symbolic link"),
        (_open_to_the_group, "can be written by its group or by others"),
        (_inside_the_working_tree, "lies inside the working tree"),
    ],
    ids=["link", "group-writable", "inside-a-working-tree"],
)
def test_a_run_root_others_could_reach_is_refused(
    project: _Project,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make: Callable[[_Project, Path, pytest.MonkeyPatch], None],
    says: str,
) -> None:
    make(project, tmp_path, monkeypatch)
    run = run_agent(project.root, _confined(project))
    assert run.ending == agent_runs.REFUSED
    assert says in run.reason
    assert not project.record.exists()


# --- the run's `pkit` -------------------------------------------------------------


# An interpreter that prints where it ran, its arguments and its environment.
_RECORDING_PYTHON = """#!/bin/sh
exec {python} -c '
import json, os, sys
print(json.dumps({{"cwd": os.getcwd(), "argv": sys.argv[1:], "env": dict(os.environ)}}))
' "$@"
"""


def test_the_runs_pkit_starts_from_the_clone_with_git_pointed_at_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "run"
    clone = folder / "clone"
    (clone / ".git").mkdir(parents=True)
    workspace = clone / ".agent-workspace"
    workspace.mkdir()
    python = tmp_path / "python"
    python.write_text(_RECORDING_PYTHON.format(python=sys.executable), encoding="utf-8")
    python.chmod(0o755)
    monkeypatch.setattr(agent_confinement.sys, "executable", str(python))
    bin_folder = agent_confinement.write_pkit(folder, clone)
    assert bin_folder == folder / "bin"

    done = subprocess.run(
        [str(bin_folder / "pkit"), "friction", "explain"],
        cwd=workspace,
        env={**os.environ, "GIT_INDEX_FILE": str(workspace / "index"), "GIT_DIR": "/elsewhere"},
        capture_output=True,
        text=True,
        check=True,
    )
    seen = json.loads(done.stdout)
    assert Path(seen["cwd"]).resolve() == clone.resolve()
    assert seen["argv"] == ["-P", "-m", "project_kit", "friction", "explain"]
    env = seen["env"]
    assert (env["GIT_DIR"], env["GIT_WORK_TREE"]) == (str(clone / ".git"), str(clone))
    assert (env["UV_NO_CONFIG"], env["PYTHONDONTWRITEBYTECODE"]) == ("1", "1")
    assert "GIT_INDEX_FILE" not in env


def test_the_runs_pkit_runs_this_backbone(tmp_path: Path) -> None:
    folder = tmp_path / "run"
    clone = folder / "clone"
    (clone / ".git").mkdir(parents=True)
    bin_folder = agent_confinement.write_pkit(folder, clone)
    done = subprocess.run(
        [str(bin_folder / "pkit"), "--version"], capture_output=True, text=True, check=True
    )
    from project_kit import __version__

    assert done.stdout.split()[-1] == __version__


# --- the command ------------------------------------------------------------------


def _confined_args(project: _Project) -> list[str]:
    return [
        "agents",
        "run",
        AGENT,
        "--limit",
        "60",
        "--commit",
        project.commit,
        "--rules-of",
        RULES_OF,
        "--files-to",
        str(project.files_to),
    ]


def test_the_command_runs_the_confined_form(project: _Project) -> None:
    result = CliRunner().invoke(main, [*_confined_args(project), "--json"], input="Fix it.")
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert (document["confined"], document["commit"], document["files"]) == (
        True,
        project.commit,
        str(project.files_to.resolve()),
    )
    assert document["check"] == {"verdict": "clean", "changes": []}
    assert project.seen()["request"]["brief"] == "Fix it."


def test_without_json_the_command_prints_the_check_and_the_exclusions(
    project: _Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(permissions, "_uv_required_exclusion", lambda _root: True)
    monkeypatch.setenv("STUB_DO", "Path(clone, 'x.log').write_text('x')")
    result = CliRunner().invoke(main, _confined_args(project), input="Fix it.")
    assert result.exit_code == 0, result.output
    assert result.stdout == "done\n"
    assert result.stderr.splitlines() == [
        f"agent {AGENT}: finished, exit 0",
        "check: breach",
        "  appeared: x.log",
        "excluded from the sandbox: pkit analysis propose",
    ]


@pytest.mark.parametrize(
    "change",
    [
        lambda args: [*args, "--folder", args[-1]],
        lambda args: args[: args.index("--files-to")],
        lambda args: [arg if arg != RULES_OF else "pm" for arg in args],
        lambda args: [
            *args[: args.index("--commit") + 1],
            "f" * 40,
            *args[args.index("--commit") + 2 :],
        ],
    ],
    ids=["with-folder", "without-files-to", "rules-of-no-command", "commit-not-held"],
)
def test_a_confined_usage_error_exits_2(
    project: _Project, change: Callable[[list[str]], list[str]]
) -> None:
    result = CliRunner().invoke(main, change(_confined_args(project)), input="Fix it.")
    assert result.exit_code == 2, result.output
    assert project.run_folders() == []


def test_neither_form_is_a_usage_error(project: _Project) -> None:
    result = CliRunner().invoke(main, ["agents", "run", AGENT, "--limit", "5"], input="Go.")
    assert result.exit_code == 2
    assert "all three together" in result.output
