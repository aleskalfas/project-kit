"""A reviewer's clone: where a reviewer works in a seat's clone (ADR-102 points 2 and 3).

- the clone is made from the code host: it shares no object with the seat's
  repository and borrows none, holds no hook, has one remote that cannot push, and
  is checked out at the default branch's head with no branch;
- it fetches the change's base and the code host's reference for the change's
  head, and a head that does not resolve to the one the caller names refuses it;
- two reviewers get two clones, and each is removed on every exit;
- a killed review's clone is removed only once its recorded process ends;
- a run folder that cannot be made refuses with the cause the review names a way
  out for;
- the run reaches the clone's runner from the clone's root, with the seat's clone
  as the checkout of its local settings and of its rules, and a folder for its
  rules outside the clone;
- the command's form: its options, and what it excludes.

The "code host" is a bare repository on disk, which keeps a pull request's head
under `refs/pull/<N>/head` as GitHub does. No real harness runs: the project
registers a stub adapter whose runner records the request it got.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import agent_confinement, agent_runs, review_clones
from project_kit import recorded_processes as rp
from project_kit.agent_runs import Request, run_agent
from project_kit.cli import main
from project_kit.review_clones import ReviewerClone
from tests.adopter_repo import MakeAdopterRepo
from tests.fake_processes import FakeSystem
from tests.test_agent_runs import _drop_claude_code_runner, _register

AGENT = "critic"
PULL = 12
REMOTE = "origin"

# The repository a process space is derived for, as the seat's `origin` remote reads.
REPOSITORY = "github.com/owner/repo"

# A runner that records the request it got, where it ran from and what it is, and
# what its folders held, then answers a finished run.
_STUB_RUNNER = """
import json, os, sys
from pathlib import Path
request = json.loads(sys.stdin.read())
folder = Path(request["folder"])
rules = Path(request["seat_permissions"]["settings_folder"])
Path(os.environ["STUB_RECORD"]).write_text(json.dumps({
    "request": request,
    "cwd": os.getcwd(),
    "script": os.path.abspath(__file__),
    "workspace": (folder / ".agent-workspace").is_dir(),
    "rules_mode": oct(rules.stat().st_mode & 0o777),
}))
print(json.dumps({"schema_version": 1, "ending": "finished", "exit_code": 0, "output": "ok\\n"}))
"""


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


@dataclass(frozen=True)
class _Seat:
    root: Path
    host: Path
    state: Path
    record: Path
    default: str
    commit: str
    head: str
    base_head: str

    @property
    def run_root(self) -> Path:
        return self.state.resolve() / "pkit" / "agent-runs"

    def run_folders(self) -> list[str]:
        if not self.run_root.is_dir():
            return []
        return sorted(entry.name for entry in self.run_root.iterdir())

    def wanted(self, **overrides: Any) -> ReviewerClone:
        fields: dict[str, Any] = {
            "commit": self.commit,
            "remote": REMOTE,
            "url": str(self.host),
            "default_branch": self.default,
            "branches": ("release",),
            "head_ref": f"refs/pull/{PULL}/head",
            "head": self.head,
            **overrides,
        }
        return ReviewerClone(**fields)

    def seen(self) -> dict[str, Any]:
        recorded: dict[str, Any] = json.loads(self.record.read_text(encoding="utf-8"))
        return recorded


@pytest.fixture
def seat(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> _Seat:
    """A seat's committed project whose one runner is the stub's, a code host it
    pushed its default branch, a base branch and a pull request's head to, and a
    state folder outside both."""
    root = make_adopter_repo(root=tmp_path / "seat").root
    _drop_claude_code_runner(root)
    _register(root, "adapter", "stub-harness", _STUB_RUNNER)
    (root / "README.md").write_text("A project.\n", encoding="utf-8")
    commit = _commit(root, "the project")
    default = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    _git(root, "remote", "add", "origin", f"https://{REPOSITORY}")
    _git(root, "switch", "-q", "-c", "release")
    (root / "RELEASE.md").write_text("A release.\n", encoding="utf-8")
    base_head = _commit(root, "a release")
    _git(root, "switch", "-q", "-c", "feature", default)
    (root / "CHANGE.md").write_text("A change.\n", encoding="utf-8")
    head = _commit(root, "the change")
    _git(root, "switch", "-q", default)
    host = tmp_path / "host.git"
    _git(tmp_path, "init", "-q", "--bare", str(host))
    _git(host, "config", "uploadpack.allowFilter", "true")
    _git(
        root,
        "push",
        "-q",
        "--no-verify",
        str(host),
        f"{default}:refs/heads/{default}",
        "release:refs/heads/release",
        f"feature:refs/pull/{PULL}/head",
    )
    record = tmp_path / "record.json"
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("STUB_RECORD", str(record))
    # The test's state folder lies in the system's temp folder, where a real run root
    # never does: the list of shared temp folders is emptied for it.
    monkeypatch.setattr(agent_confinement, "temp_folders", list)
    return _Seat(root, host, tmp_path / "state", record, default, commit, head, base_head)


def _objects(git_folder: Path) -> set[tuple[int, int]]:
    """The device and inode of each file under `git_folder`'s objects."""
    found: set[tuple[int, int]] = set()
    for folder, _dirs, files in os.walk(git_folder / "objects"):
        for name in files:
            held = os.stat(Path(folder) / name)
            found.add((held.st_dev, held.st_ino))
    return found


# --- what the clone holds ----------------------------------------------------------


def test_the_clone_shares_no_object_holds_no_hook_and_cannot_push(seat: _Seat) -> None:
    with review_clones.reviewer_clone(seat.root, seat.wanted()) as made:
        clone = made.clone
        git_folder = clone / ".git"
        assert made.folder.parent == seat.run_root
        assert not os.path.lexists(git_folder / "objects" / "info" / "alternates")
        assert not _objects(git_folder) & _objects(seat.root / ".git")
        assert not (git_folder / "hooks").exists()
        assert _git(clone, "config", "core.hooksPath") == os.devnull
        assert _git(clone, "remote").splitlines() == [REMOTE]
        assert _git(clone, "remote", "get-url", REMOTE) == str(seat.host)
        pushed = subprocess.run(
            ["git", "push", "-q", REMOTE, "HEAD:refs/heads/pushed"],
            cwd=clone,
            capture_output=True,
            text=True,
            check=False,
        )
        assert pushed.returncode != 0
        assert "pushed" not in _git(seat.host, "for-each-ref", "--format=%(refname)")
        # At the default branch's head, with no branch; the base and the head fetched.
        assert (git_folder / "HEAD").read_text(encoding="utf-8").strip() == seat.commit
        assert _git(clone, "rev-parse", f"{REMOTE}/{seat.default}") == seat.commit
        assert _git(clone, "rev-parse", f"{REMOTE}/release") == seat.base_head
        assert _git(clone, "rev-parse", f"refs/remotes/{REMOTE}/pull/{PULL}/head") == seat.head
        assert _git(clone, "symbolic-ref", f"refs/remotes/{REMOTE}/HEAD") == (
            f"refs/remotes/{REMOTE}/{seat.default}"
        )
        assert _git(clone, "show", f"{seat.head}:CHANGE.md") == "A change."
        assert not _git(clone, "tag")
        # Its workspace, and the folder for the run's rules beside it.
        assert made.workspace == clone / ".agent-workspace"
        assert made.workspace.is_dir()
        assert made.rules.parent == made.folder
        assert made.rules.stat().st_mode & 0o777 == 0o700
    assert seat.run_folders() == []


def test_a_head_that_does_not_resolve_to_the_one_named_refuses_the_clone(seat: _Seat) -> None:
    with (
        pytest.raises(agent_confinement.Refused, match="resolves to") as refused,
        review_clones.reviewer_clone(seat.root, seat.wanted(head=seat.base_head)),
    ):
        pass
    assert seat.head in refused.value.reason
    assert refused.value.cause is None
    assert seat.run_folders() == []


def test_a_head_the_code_host_does_not_keep_refuses_the_clone(seat: _Seat) -> None:
    with (
        pytest.raises(agent_confinement.Refused, match="cannot fetch"),
        review_clones.reviewer_clone(seat.root, seat.wanted(head_ref="refs/pull/99/head")),
    ):
        pass
    assert seat.run_folders() == []


def test_a_commit_the_clone_does_not_hold_refuses_it(seat: _Seat) -> None:
    with (
        pytest.raises(agent_confinement.Refused, match="does not hold"),
        review_clones.reviewer_clone(seat.root, seat.wanted(commit="0" * 40)),
    ):
        pass


def test_a_commit_that_holds_the_workspace_refuses_the_clone(seat: _Seat) -> None:
    (seat.root / ".agent-workspace").mkdir(exist_ok=True)
    (seat.root / ".agent-workspace" / "planted.md").write_text("x", encoding="utf-8")
    _git(seat.root, "add", "-f", ".agent-workspace/planted.md")
    commit = _commit(seat.root, "plant a workspace")
    _git(seat.root, "push", "-q", "--no-verify", str(seat.host), f"{seat.default}")
    with (
        pytest.raises(agent_confinement.Refused, match=r"holds something at `\.agent-workspace`"),
        review_clones.reviewer_clone(seat.root, seat.wanted(commit=commit)),
    ):
        pass


def test_two_reviewers_get_two_clones(seat: _Seat) -> None:
    with (
        review_clones.reviewer_clone(seat.root, seat.wanted()) as first,
        review_clones.reviewer_clone(seat.root, seat.wanted()) as second,
    ):
        assert first.folder != second.folder
        assert first.clone.is_dir() and second.clone.is_dir()
        assert len(seat.run_folders()) == 2
    assert seat.run_folders() == []


# --- the sweep --------------------------------------------------------------------


def _left(root: Path, folder: str, name: str) -> Path:
    """A run's folder a killed review left in `root`, naming the process `name`."""
    left = root / folder
    (left / "clone").mkdir(parents=True)
    (left / agent_confinement.PROCESS_FILE).write_text(f"{name}\n", encoding="utf-8")
    return left


def test_a_killed_reviews_clone_is_removed_only_once_its_process_ends(
    seat: _Seat, monkeypatch: pytest.MonkeyPatch
) -> None:
    system = FakeSystem(
        entries={
            os.getpid(): rp.Entry(True, "500.0"),
            42: rp.Entry(True, "100.0"),
            43: rp.Entry(True, "100.0"),
        }
    )
    monkeypatch.setattr(rp, "this_system", lambda: system)
    asking = agent_confinement.reader(seat.root, system)

    def named(pid: int) -> str:
        found = rp.name(pid, asking, system)
        assert found.name is not None, found.why
        return found.name

    seat.run_root.mkdir(parents=True, mode=0o700)
    _left(seat.run_root, "run-ended", named(43))
    _left(seat.run_root, "run-live", named(42))
    del system.entries[43]

    with review_clones.reviewer_clone(seat.root, seat.wanted()) as made:
        recorded = (made.folder / agent_confinement.PROCESS_FILE).read_text(encoding="utf-8")
        assert rp.compare(recorded.strip(), named(os.getpid())).answer == rp.ONE
        assert sorted(set(seat.run_folders()) - {made.folder.name}) == ["run-live"]
    assert seat.run_folders() == ["run-live"]


# --- a folder that cannot be made -------------------------------------------------


def test_a_run_root_that_cannot_be_written_refuses_with_its_cause(seat: _Seat) -> None:
    seat.run_root.mkdir(parents=True, mode=0o700)
    seat.run_root.chmod(0o500)
    try:
        run = run_agent(seat.root, Request(AGENT, "Review it.", None, 30, review=seat.wanted()))
    finally:
        seat.run_root.chmod(0o700)
    assert run.ending == agent_runs.REFUSED
    assert run.refusal_cause == agent_confinement.RUN_FOLDER
    assert run.as_json()["refusal_cause"] == "run-folder"


def test_a_state_folder_that_cannot_be_written_refuses_with_its_cause(seat: _Seat) -> None:
    seat.state.mkdir(mode=0o500)
    try:
        run = run_agent(seat.root, Request(AGENT, "Review it.", None, 30, review=seat.wanted()))
    finally:
        seat.state.chmod(0o700)
    assert (run.ending, run.refusal_cause) == (agent_runs.REFUSED, agent_confinement.RUN_FOLDER)


def test_a_clone_that_cannot_be_made_names_no_cause(seat: _Seat) -> None:
    run = run_agent(
        seat.root,
        Request(AGENT, "Review it.", None, 30, review=seat.wanted(head=seat.base_head)),
    )
    assert (run.ending, run.refusal_cause) == (agent_runs.REFUSED, None)
    assert "resolves to" in run.reason


# --- the run ----------------------------------------------------------------------


def test_the_run_reaches_the_clones_runner_with_the_seats_clone(seat: _Seat) -> None:
    run = run_agent(seat.root, Request(AGENT, "Review it.", None, 30, review=seat.wanted()))

    assert (run.ending, run.exit_code, run.output) == (agent_runs.FINISHED, 0, "ok\n")
    assert not run.confined
    seen = seat.seen()
    request = seen["request"]
    clone = Path(request["folder"])
    assert clone.parent.parent == seat.run_root
    assert clone.name == agent_confinement.CLONE
    assert Path(seen["cwd"]).resolve() == clone.resolve()
    assert Path(seen["script"]).is_relative_to(clone)
    assert request["local_settings_from"] == str(seat.root.resolve())
    assert request["seat_permissions"] == {
        "seat_clone": str(seat.root.resolve()),
        "settings_folder": str(clone.parent / review_clones.RULES),
    }
    assert "confined" not in request
    assert seen["workspace"] is True
    assert seen["rules_mode"] == oct(0o700)
    assert seat.run_folders() == []


@pytest.mark.parametrize(
    ("overrides", "said"),
    [
        pytest.param({"folder": Path("/")}, "names no folder", id="a-folder"),
        pytest.param({"local_settings_from": Path("/")}, "names no folder", id="local-settings"),
        pytest.param({"commit": "a" * 40}, "names no folder", id="a-commit"),
    ],
)
def test_a_run_in_a_reviewers_clone_names_no_other_forms_parts(
    seat: _Seat, overrides: dict[str, Any], said: str
) -> None:
    request = replace(Request(AGENT, "Review it.", None, 30, review=seat.wanted()), **overrides)
    run = run_agent(seat.root, request)
    assert run.ending == agent_runs.REFUSED
    assert said in run.reason
    assert seat.run_folders() == []


@pytest.mark.parametrize(
    ("overrides", "said"),
    [
        pytest.param({"commit": "HEAD"}, "commit 'HEAD'", id="a-commit-by-name"),
        pytest.param({"head": "a" * 39}, "head", id="a-short-head"),
        pytest.param({"remote": "-x"}, "remote", id="an-option-for-a-remote"),
        pytest.param({"remote": "a..b"}, "remote", id="a-remote-with-two-dots"),
        pytest.param({"url": "--upload-pack=x"}, "address", id="an-option-for-an-address"),
        pytest.param({"url": "a b"}, "address", id="an-address-with-a-space"),
        pytest.param({"url": ""}, "address", id="no-address"),
        pytest.param({"default_branch": "-x"}, "branch", id="an-option-for-a-branch"),
        pytest.param({"branches": ("a..b",)}, "branch", id="a-branch-with-two-dots"),
        pytest.param({"head_ref": "pull/12/head"}, "head reference", id="a-reference-no-refs"),
        pytest.param({"head_ref": "refs/-x"}, "head reference", id="an-option-in-a-ref"),
    ],
)
def test_a_reviewers_clone_named_wrongly_is_refused(
    seat: _Seat, overrides: dict[str, Any], said: str
) -> None:
    wanted = seat.wanted(**overrides)
    problem = wanted.problem()
    assert problem is not None and said in problem
    run = run_agent(seat.root, Request(AGENT, "Review it.", None, 30, review=wanted))
    assert (run.ending, run.reason) == (agent_runs.REFUSED, problem)


# --- the command ------------------------------------------------------------------


def _clone_options(seat: _Seat) -> list[str]:
    wanted = seat.wanted()
    return [
        "--clone-at",
        wanted.commit,
        "--clone-remote",
        wanted.remote,
        "--clone-url",
        wanted.url,
        "--clone-default",
        wanted.default_branch,
        "--clone-branch",
        "release",
        "--clone-head-ref",
        wanted.head_ref,
        "--clone-head",
        wanted.head,
    ]


def test_the_command_runs_a_reviewer_in_a_clone_of_its_own(
    seat: _Seat, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(seat.root)
    result = CliRunner().invoke(
        main,
        ["agents", "run", AGENT, *_clone_options(seat), "--limit", "30", "--json"],
        input="Review it.",
    )
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert (document["ending"], document["refusal_cause"]) == ("finished", None)
    assert seat.seen()["request"]["seat_permissions"]["seat_clone"] == str(seat.root.resolve())


@pytest.mark.parametrize(
    ("added", "dropped", "said"),
    [
        pytest.param(["--folder", "."], None, "exclude --folder", id="with-a-folder"),
        pytest.param(["--local-settings"], None, "exclude --folder", id="with-local-settings"),
        pytest.param(["--commit", "a" * 40], None, "exclude --folder", id="with-a-commit"),
        pytest.param([], "--clone-head", "together", id="without-the-head"),
        pytest.param([], "--clone-url", "together", id="without-the-address"),
    ],
)
def test_the_commands_clone_options_go_together_and_alone(
    seat: _Seat,
    monkeypatch: pytest.MonkeyPatch,
    added: list[str],
    dropped: str | None,
    said: str,
) -> None:
    monkeypatch.chdir(seat.root)
    options = _clone_options(seat)
    if dropped is not None:
        at = options.index(dropped)
        del options[at : at + 2]
    result = CliRunner().invoke(
        main, ["agents", "run", AGENT, *options, *added, "--limit", "30"], input="Review it."
    )
    assert result.exit_code == 2, result.output
    assert said in result.output
    assert not seat.record.exists()
