"""create-seats (DEC-059 point 3): each new seat's state issue, created and numbered.

The command runs on the change that adds seats. For each seat that names no
state issue and is not retired, it creates the seat's state issue through the
state-issue seam and writes its number into `project/topology.yaml` in the
working tree. These tests pin the creation, its idempotence (a second run, an
issue an earlier run created, a creation left half done), its refusals, and
the guard ADR-071 point 1 sets on the seam's callers. GitHub is the in-memory
fake of the state-issue tests, and the backbone's reading and git are fakes.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
TESTS = Path(__file__).resolve().parent
for entry in (SCRIPTS, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from _lib import audit_log, default_branch, provenance  # noqa: E402
from _lib import state_issues as si  # noqa: E402
from _lib import topology as tp  # noqa: E402

from pm_state_issue_fakes import FakeRepo  # noqa: E402

VERSIONS = provenance.Versions(tree="1.2.3", capability="0.9.0", cli="1.2.3")
TIP = "c0ffee"
MEMBERS_REL = ".pkit/capabilities/project-management/project/members.yaml"

TOPOLOGY = """\
schema_version: 1
# The seats of this project's agents.
seats:
  - name: planner   # plans, builds nothing
    role: planner
    organizer: true
    state_issue: 7
  - name: worker-1
    role: worker
  - name: old
    role: worker
    retired: true
  - name: tester
    role: worker
    scope:
      types: [test]
"""


def _script():
    spec = importlib.util.spec_from_file_location(
        "pm_create_seats_under_test", SCRIPTS / "create-seats.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CS = _script()


@pytest.fixture(autouse=True)
def fresh_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(default_branch, "_read", {})
    monkeypatch.setattr(default_branch, "_warned", set())


def _capability(tmp_path: Path, text: str = TOPOLOGY) -> Path:
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    (root / "project").mkdir(parents=True)
    tp.path(root).write_text(text, encoding="utf-8")
    return root


def _backbone(tip: str | None = TIP, problem: str | None = None) -> Any:
    def run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        document = {
            "schema_version": 1,
            "default_branch": {
                "name": "main",
                "source": "default",
                "ref": "origin/main",
                "commit": tip,
                "problem": problem,
            },
            "base": {"ref": "origin/main", "tip": tip, "fork": tip, "problem": problem},
        }
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")

    return run


def _git(members: list[str] | None = None) -> Any:
    """A git whose default branch holds ``members``, or no members file."""
    text = None
    if members is not None:
        text = json.dumps({"schema_version": 1, "members": [{"github_login": m} for m in members]})

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[0] == "ls-tree":
            held = f"{MEMBERS_REL}\0" if text is not None and args[-1] == MEMBERS_REL else ""
            return subprocess.CompletedProcess(args, 0, held, "")
        assert args[:2] == ["cat-file", "blob"] and text is not None
        return subprocess.CompletedProcess(args, 0, text, "")

    return run


def _create(root: Path, repo: FakeRepo, **kw: Any) -> int:
    kw.setdefault("yes", True)
    kw.setdefault("run", _backbone())
    kw.setdefault("git", _git(["me"]))
    return CS.create_seats(root, gh=repo, versions=VERSIONS, **kw)


def _numbers(root: Path) -> dict[str, int | None]:
    topology = tp.read_working_tree(root)
    assert topology is not None
    return {seat.name: seat.state_issue for seat in topology.seats}


def _state_issue(repo: FakeRepo, number: int, key: str, *, comment: bool = True) -> None:
    repo.add(number, si.description("seat", key, si.Fold(None), VERSIONS), title=f"Seat {key}")
    if comment:
        repo.post(number, si.marker_comment("seat", key, VERSIONS))


# ---- creation ----------------------------------------------------------------------


def test_it_creates_each_new_seat_s_state_issue_and_writes_its_number(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    assert _create(root, repo) == 0
    numbers = _numbers(root)
    assert numbers == {"planner": 7, "worker-1": 101, "old": None, "tester": 102}
    for number, key in ((101, "worker-1"), (102, "tester")):
        issue = repo.issues[number]
        assert issue.title == f"Seat {key}"
        marker = si.read_marker(issue.body)
        assert marker is not None and marker.names("seat", key)
        assert (
            si.read(
                number, "seat", key, si.StateRun(repo, si.Writers.closed(["me"]), VERSIONS)
            ).outcome
            == si.READ
        )
    text = tp.path(root).read_text("utf-8")
    assert "# The seats of this project's agents." in text and "# plans, builds nothing" in text
    assert tp.parse(tp.load(text)).problems == ()


def test_a_second_run_creates_nothing_and_leaves_the_file_as_it_is(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    _create(root, repo)
    before = tp.path(root).read_text("utf-8")
    calls = len(repo.calls)
    assert _create(root, repo) == 0
    assert tp.path(root).read_text("utf-8") == before and len(repo.calls) == calls


def test_a_state_issue_an_earlier_run_created_is_found_not_created_again(
    tmp_path: Path,
) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    _state_issue(repo, 40, "worker-1")
    assert _create(root, repo) == 0
    assert _numbers(root)["worker-1"] == 40
    created = [argv for argv in repo.writes() if argv[2] == "create"]
    assert len(created) == 1  # the tester's alone


def test_a_creation_left_half_done_is_finished(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    _state_issue(repo, 40, "worker-1", comment=False)
    assert _create(root, repo) == 0
    assert _numbers(root)["worker-1"] == 40
    marker = si.read_marker(repo.bodies(40)[0])
    assert marker is not None and marker.names("seat", "worker-1")
    assert any(provenance.FILING_MARKER in body for body in repo.bodies(40))


def test_a_closed_or_foreign_state_issue_is_not_taken_for_the_seat(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    _state_issue(repo, 40, "worker-1")
    repo.issues[40].state = "CLOSED"
    _state_issue(repo, 41, "worker-2")
    assert _create(root, repo) == 0
    assert _numbers(root)["worker-1"] not in (40, 41)


def test_the_members_come_from_the_default_branch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A marker comment from an author the default branch names no member of does
    not make an issue the seat's state issue (ADR-071 point 3), so no number is
    written for one that no clone would read as such."""
    root = _capability(tmp_path)
    repo = FakeRepo()  # every comment it posts is by `me`
    assert _create(root, repo, git=_git(["bob"])) == 3
    assert _numbers(root)["worker-1"] is None
    assert "does not read as the seat's state issue" in capsys.readouterr().err


# ---- refusals ----------------------------------------------------------------------


def test_a_dry_run_creates_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    assert _create(root, repo, dry_run=True) == 0
    assert repo.calls == [] and _numbers(root)["worker-1"] is None
    out = capsys.readouterr().out
    assert "seat 2 (worker-1, worker)" in out and "seat 3" not in out
    assert f"the 1 member(s) origin/main at {TIP} names" in out


def test_off_a_terminal_without_yes_it_refuses(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    assert _create(root, repo, yes=False) == 1
    assert repo.calls == []


def test_it_refuses_a_file_with_other_problems(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _capability(tmp_path, TOPOLOGY + "  - name: tester\n    role: lead\n")
    repo = FakeRepo()
    assert _create(root, repo) == 1
    assert repo.calls == []
    assert "share the name 'tester'" in capsys.readouterr().err


def test_it_refuses_where_the_default_branch_cannot_be_resolved(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    assert _create(root, repo, run=_backbone(None, "origin/main is not fetched")) == 1
    assert repo.calls == [] and _numbers(root)["worker-1"] is None


def test_with_no_topology_or_no_new_seat_there_is_nothing_to_do(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    tp.path(root).unlink()
    assert _create(root, FakeRepo()) == 0
    tp.path(root).write_text(
        "schema_version: 1\nseats:\n  - name: planner\n    role: planner\n    state_issue: 7\n",
        encoding="utf-8",
    )
    repo = FakeRepo()
    assert _create(root, repo) == 0 and repo.calls == []


def test_a_listing_that_fails_creates_nothing(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    repo.failing.add("list")
    assert _create(root, repo) == 3
    assert repo.writes() == [] and _numbers(root)["worker-1"] is None
    assert _create(root, repo) == 0  # the next run goes on
    assert _numbers(root)["tester"] == 102


def test_a_creation_that_fails_stops_and_keeps_the_numbers_already_written(
    tmp_path: Path,
) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    _state_issue(repo, 40, "worker-1")  # found, so its number is written first
    repo.failing.add("create")
    assert _create(root, repo) == 3
    assert _numbers(root) == {"planner": 7, "worker-1": 40, "old": None, "tester": None}


# ---- the guard (ADR-071 point 1) ------------------------------------------------------


def test_construction_every_write_it_runs_comes_from_the_seam(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    _state_issue(repo, 40, "worker-1", comment=False)
    _create(root, repo)
    writes = repo.writes()
    assert writes
    for argv in writes:
        verb = argv[2]
        if verb == "create":
            assert argv[:3] == ["gh", "issue", "create"] and "--body-file" in argv
            assert not {"--label", "--assignee", "--milestone", "--project"} & set(argv)
        else:
            assert verb == "comment" and argv == si.comment_args(int(argv[3]), argv[5])
            body = argv[5]
            assert si.read_marker(body) is not None or provenance.FILING_MARKER in body
            assert audit_log.parse(body) is None
    listed = [argv for argv in repo.calls if argv[1:3] == ["issue", "list"]]
    assert len(listed) == 1 and "--search" not in listed[0]
