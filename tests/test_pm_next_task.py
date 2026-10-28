"""Tests for `next-task`: a worker takes its next task from one shared pool
(DEC-059 point 7).

`main()` runs against the shipped schemas with its gates stubbed. The listing of
open issues and every ownership read reach one in-memory GitHub
(`tests/pm_ownership_support.FakeGitHub`), never GitHub itself. `start-work` is
recorded, or, for the race between two clones, run in process on the same
in-memory GitHub, its own seams stubbed as `tests/test_pm_start_work.py` stubs
them. The other clone's claim lands at a chosen read, as the claim tests stand
for a claim made in the same instant.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from tests.pm_ownership_support import (
    FakeGitHub,
    clone_with,
    seat_issue,
    seat_snapshot,
    snapshot_with,
    topology_with,
)
from tests.pm_state_issue_fakes import FakeRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
CAP_ROOT = SCRIPTS.parent


def _load(name: str, script: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def nt():
    sys.path.insert(0, str(SCRIPTS))
    yield _load("pm_next_task_under_test", "next-task.py")
    sys.path.remove(str(SCRIPTS))


@pytest.fixture(scope="module")
def sw(nt):
    return _load("pm_start_work_for_next_task", "start-work.py")


# ---- the in-memory GitHub, listed -----------------------------------------------


class Pool:
    """Open issues on one in-memory GitHub: `add` files a Task in Backlog, and
    `list` answers `gh issue list` from what the GitHub holds now."""

    def __init__(self) -> None:
        self.github = FakeGitHub()
        self.titles: dict[int, str] = {}
        self.milestones: dict[int, int] = {}
        self.listed: list[list[str]] = []
        self.returncode = 0

    def add(
        self,
        number: int,
        *,
        priority: str = "Medium",
        state: str = "backlog",
        kind: str = "feature",
        assignees: tuple[str, ...] = (),
        body: str = "Feature: #1\n\n## What\n\nx\n",
        title: str = "[Task] do the thing",
        milestone: int | None = None,
    ) -> None:
        labels = (f"state:{state}", f"priority:{priority}", f"type:{kind}", "workstream:cli")
        self.github.add(number, assignees=assignees, labels=labels, body=body)
        self.titles[number] = title
        if milestone is not None:
            self.milestones[number] = milestone

    def list(self, argv: list[str], _config: dict, **_kw: Any) -> subprocess.CompletedProcess[str]:
        self.listed.append(list(argv))
        assert argv[1:3] == ["issue", "list"], argv
        rows = [self.issue(n) for n in sorted(self.github.issues)]
        return subprocess.CompletedProcess(argv, self.returncode, json.dumps(rows), "")

    def issue(self, number: int) -> dict[str, Any]:
        """Issue `number` as `gh` returns it to a listing or to `gh issue view`."""
        held = self.github.issues[number]
        milestone = self.milestones.get(number)
        return {
            "number": number,
            "id": f"I_{number}",
            "title": self.titles[number],
            "labels": [{"name": n} for n in held.labels],
            "assignees": [{"login": a} for a in held.assignees],
            "milestone": None if milestone is None else {"number": milestone, "title": "M"},
            "state": "OPEN",
            "body": held.body,
        }

    def claims(self, number: int) -> list[str]:
        """The ownership events on the issue, as `event instance`."""
        out = []
        for comment in self.github.issues[number].comments:
            body = comment["body"]
            if "event=" in body:
                out.append(
                    f"{body.split('event=')[1].split()[0]} {body.split('instance=')[1].split()[0]}"
                )
        return out


def _stamp(nt, instance: int, event: str = "claim") -> str:
    return nt.instance_claims.ownership.format_event_comment(event=event, instance=instance)


@pytest.fixture
def run(nt, monkeypatch: pytest.MonkeyPatch):
    """Returns `run(pool, instance=None, extra=(), start=None, seated=None,
    yes=True) -> (rc, starts)`. `instance` is this clone's instance id (none by
    default). `start` stands in for `start-work`; by default it records each
    start and answers 0. `seated` is the run's snapshot of the topology and the
    seat this clone took, where it took one. `yes` passes `--yes`. `starts` holds
    `(number, dry_run)` for each start."""

    def go(
        pool: Pool,
        instance: int | None = None,
        extra: tuple[str, ...] = (),
        start: Any = None,
        seated: tuple[Any, str] | None = None,
        yes: bool = True,
        config: dict | None = None,
        axes: dict | None = None,
    ) -> tuple[int, list[tuple[int, bool]]]:
        starts: list[tuple[int, bool]] = []

        def recorded(number: int, *, dry_run: bool, **_kw: Any) -> int:
            starts.append((number, dry_run))
            return 0 if start is None else start(number, dry_run=dry_run)

        clone_with(nt.instance_claims, monkeypatch, instance)
        if seated is not None:
            snapshot, hint = seated
            snapshot_with(nt.instance_claims, monkeypatch, snapshot, hint=hint)
        monkeypatch.setattr(nt.instance_claims, "_gh", lambda args, _c: pool.github(args))
        monkeypatch.setattr(nt, "_gh", pool.list)
        monkeypatch.setattr(sys, "argv", ["next-task", *(("--yes",) if yes else ()), *extra])
        monkeypatch.setattr(nt, "resolve_capability_root", lambda _e: CAP_ROOT)
        monkeypatch.setattr(nt.bootstrap_gate, "enforce", lambda *a, **k: True)
        monkeypatch.setattr(nt.session_guard, "enforce", lambda **k: True)
        monkeypatch.setattr(nt, "load_adopter_config", lambda _r: dict(config or {}))
        monkeypatch.setattr(nt, "_read_members", lambda *a: [])
        monkeypatch.setattr(
            nt, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
        )
        monkeypatch.setattr(nt, "check_membership", lambda *a: SimpleNamespace(allowed=True))
        substrate_map = None if axes is None else nt.axis_labels.SubstrateMap(axes=axes)
        monkeypatch.setattr(nt.axis_labels, "load_substrate_map", lambda _r: substrate_map)
        monkeypatch.setattr(nt, "_start_work", recorded)
        return nt.main(), starts

    return go


# ---- picking the next ready Task ---------------------------------------------------


def test_it_starts_the_highest_in_priority(run, capsys) -> None:
    pool = Pool()
    pool.add(10, priority="Low")
    pool.add(11, priority="High")
    pool.add(12, priority="Medium")
    rc, starts = run(pool)
    assert rc == 0
    assert starts == [(11, False)]
    out = capsys.readouterr().out
    assert "next-task: 3 Tasks are ready for this clone, with no scope" in out
    assert "next-task: #11 [Task] do the thing (priority High, in Backlog)" in out
    assert "[ok] next-task: started #11" in out


def test_with_no_instance_id_it_reads_no_owner(run) -> None:
    """Outside instance ownership no owner exists to read (DEC-035 point 1)."""
    pool = Pool()
    pool.add(10)
    run(pool)
    assert pool.github.calls == []
    (listed,) = pool.listed
    assert listed[3:] == ["--state", "open", "--limit", "1000", "--json", listed[-1]]


def test_a_task_waiting_on_an_open_issue_is_skipped(run) -> None:
    pool = Pool()
    pool.add(10, priority="High", body="Feature: #1\n\n## Dependencies\n\n- #30, then this\n")
    pool.add(11, priority="Low")
    pool.add(30, title="[Feature] the foundation")
    rc, starts = run(pool)
    assert rc == 0
    assert starts == [(11, False)]


def test_a_task_another_instance_holds_is_skipped(run, nt, capsys) -> None:
    pool = Pool()
    pool.add(10, priority="High", assignees=("me",))
    pool.add(11, priority="Low")
    pool.github.post(10, _stamp(nt, 3))
    rc, starts = run(pool, instance=2)
    assert rc == 0
    assert starts == [(11, False)]
    assert "  skipped #10: held by instance 3" in capsys.readouterr().out
    assert pool.github.writes() == []


def test_this_clones_own_tasks_come_before_the_pool(run, nt, capsys) -> None:
    """A lead owns what it files (DEC-059 point 7), and the clash guard refuses
    that Task to every other clone. It is this clone's own work, outside the
    pool, so it comes first, and its own Tasks rank by priority among themselves."""
    pool = Pool()
    pool.add(10, priority="Low", assignees=("me",))
    pool.add(11, priority="High")
    pool.add(12, priority="Medium", assignees=("me",))
    pool.github.post(10, _stamp(nt, 2))
    pool.github.post(12, _stamp(nt, 2))
    rc, starts = run(pool, instance=2)
    assert (rc, starts) == (0, [(12, False)])
    out = capsys.readouterr().out
    assert "with no scope, its own first, then the highest in priority." in out
    assert "next-task: #12 [Task] do the thing (priority Medium, in Backlog, this clone's own)" in (
        out
    )


def test_this_clones_own_task_waiting_on_an_open_issue_is_skipped(run, nt) -> None:
    pool = Pool()
    pool.add(10, assignees=("me",), body="Feature: #1\n\n## Dependencies\n\n- #30\n")
    pool.add(11, priority="Low")
    pool.add(30, title="[Feature] the foundation")
    pool.github.post(10, _stamp(nt, 2))
    rc, starts = run(pool, instance=2)
    assert (rc, starts) == (0, [(11, False)])


def test_a_task_another_instance_of_this_account_owns_is_still_skipped(run, nt, capsys) -> None:
    pool = Pool()
    pool.add(10, priority="Low", assignees=("me",))
    pool.add(11, priority="Low")
    pool.github.post(10, _stamp(nt, 3))
    rc, starts = run(pool, instance=2)
    assert (rc, starts) == (0, [(11, False)])
    assert "  skipped #10: held by instance 3" in capsys.readouterr().out
    assert pool.github.writes() == []


def test_a_task_assigned_to_another_account_is_skipped(run) -> None:
    pool = Pool()
    pool.add(10, priority="High", assignees=("alice",))
    pool.add(11, priority="Low")
    rc, starts = run(pool)
    assert (rc, starts) == (0, [(11, False)])


def test_with_nothing_ready_it_starts_nothing(run, nt, capsys) -> None:
    pool = Pool()
    pool.add(10, state="todo")
    pool.add(11, state="in-progress")
    rc, starts = run(pool)
    assert rc == nt.EXIT_NONE_READY == 5
    assert starts == []
    assert "[ok] next-task: no Task is ready for this clone, so nothing was started." in (
        capsys.readouterr().out
    )


def test_a_dry_run_hands_start_work_its_dry_run(run) -> None:
    pool = Pool()
    pool.add(10)
    rc, starts = run(pool, extra=("--dry-run",))
    assert (rc, starts) == (0, [(10, True)])


@pytest.mark.parametrize("reply", ["", "n", "no"])
def test_a_person_who_declines_the_prompt_starts_nothing(run, monkeypatch, capsys, reply) -> None:
    """Without `--yes`, at a terminal, the command asks before it starts a Task. A
    person who declines starts nothing, and the run ends with 0 and `aborted.`, as
    the README's exit table says (#2143)."""
    pool = Pool()
    pool.add(10)
    asked: list[str] = []
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or reply)
    rc, starts = run(pool, yes=False)
    assert (rc, starts) == (0, [])
    assert asked == ["Start #10? [y/N] "]
    assert "aborted." in capsys.readouterr().err


def test_a_person_who_agrees_to_the_prompt_starts_the_task(run, monkeypatch) -> None:
    pool = Pool()
    pool.add(10)
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    rc, starts = run(pool, yes=False)
    assert (rc, starts) == (0, [(10, False)])


def test_a_failure_that_is_not_a_lost_claim_stops_the_run(run, capsys) -> None:
    pool = Pool()
    pool.add(10, priority="High")
    pool.add(11, priority="Low")
    rc, starts = run(pool, instance=2, start=lambda _n, dry_run: 3)
    assert rc == 3
    assert starts == [(10, False)]
    assert "[failed] next-task: start-work #10 failed (exit 3), and no other instance holds it" in (
        capsys.readouterr().err
    )


def test_a_listing_that_reaches_its_limit_refuses(run, capsys) -> None:
    pool = Pool()
    pool.add(10)
    pool.add(11)
    rc, starts = run(pool, extra=("--limit", "2"))
    assert (rc, starts) == (2, [])
    assert "the listing reached its limit of 2 open issues" in capsys.readouterr().err


def test_a_listing_that_fails_is_a_gh_failure(run, capsys) -> None:
    pool = Pool()
    pool.returncode = 1
    rc, starts = run(pool)
    assert (rc, starts) == (3, [])
    assert "error: the open issues could not be read" in capsys.readouterr().err


def test_a_task_whose_owner_cannot_be_read_is_skipped(run, capsys) -> None:
    pool = Pool()
    pool.add(10)
    pool.github.failing.add("view")
    rc, starts = run(pool, instance=2)
    assert (rc, starts) == (3, [])
    err = capsys.readouterr().err
    assert "#10 could not be read, so whose it is cannot be told. Skipped." in err


def test_start_work_is_run_with_the_run_s_own_confirmations(nt, monkeypatch) -> None:
    ran: list[list[str]] = []
    fake = SimpleNamespace(run=lambda cmd, check: ran.append(cmd) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(nt, "subprocess", fake)
    root = Path("/elsewhere")
    assert nt._start_work(7, dry_run=True, capability_root_arg=root, allow_foreign_repo=True) == 0
    (cmd,) = ran
    assert cmd[1].endswith("start-work.py")
    assert cmd[2:] == [
        "7",
        "--yes",
        "--dry-run",
        "--allow-foreign-repo",
        "--capability-root",
        "/elsewhere",
    ]


# ---- a project with a topology of seats (DEC-059 points 2, 7 and 9) ------------------


def _seat(nt, monkeypatch, *, role: str = "worker", scope: Any = None, holders: dict | None = None):
    """This clone holds `worker-2`, the second seat, with the key `k2`."""
    claims = nt.instance_claims
    ownership = claims.ownership
    held = {"worker-2": ownership.Holder(ownership.SEAT_HELD, "me", "k2")}
    seat = claims.Seat("worker-2", 2, role, scope)
    topology_with(claims, monkeypatch, claims.Topology(seat, holders or held), key="k2")


def _scope(**parts: tuple[str, ...]) -> Any:
    return importlib.import_module("_lib.topology").Scope(**parts)


def test_a_seat_takes_within_its_scope(run, nt, monkeypatch, capsys) -> None:
    pool = Pool()
    pool.add(10, priority="High", kind="feature")
    pool.add(11, priority="Low", kind="test")
    _seat(nt, monkeypatch, scope=_scope(types=("test",)))
    rc, starts = run(pool)
    assert (rc, starts) == (0, [(11, False)])
    assert (
        "1 Task is ready for seat worker-2, instance 2, within the scope of types test"
        in capsys.readouterr().out
    )


def test_a_task_whose_seat_was_released_is_taken_over(run, nt, monkeypatch, capsys) -> None:
    """DEC-059 points 7 and 9: a Task In Progress whose claim no longer counts."""
    ownership = nt.instance_claims.ownership
    pool = Pool()
    pool.add(10, state="in-progress", assignees=("me",))
    pool.github.post(
        10,
        ownership.format_event_comment(
            event="claim", instance=1, seat="worker-1", seat_number=1, clone="k1"
        ),
    )
    _seat(
        nt,
        monkeypatch,
        holders={
            "worker-1": ownership.Holder(ownership.SEAT_FREE),
            "worker-2": ownership.Holder(ownership.SEAT_HELD, "me", "k2"),
        },
    )
    rc, starts = run(pool)
    assert (rc, starts) == (0, [(10, False)])
    assert "(priority Medium, In Progress, its claim no longer counting)" in capsys.readouterr().out


def test_a_task_in_progress_whose_claim_counts_is_left_alone(run, nt, monkeypatch) -> None:
    ownership = nt.instance_claims.ownership
    pool = Pool()
    pool.add(10, state="in-progress", assignees=("me",))
    pool.github.post(
        10,
        ownership.format_event_comment(
            event="claim", instance=1, seat="worker-1", seat_number=1, clone="k1"
        ),
    )
    _seat(
        nt,
        monkeypatch,
        holders={
            "worker-1": ownership.Holder(ownership.SEAT_HELD, "me", "k1"),
            "worker-2": ownership.Holder(ownership.SEAT_HELD, "me", "k2"),
        },
    )
    rc, starts = run(pool)
    assert (rc, starts) == (nt.EXIT_NONE_READY, [])


def test_a_planners_seat_takes_nothing(run, nt, monkeypatch, capsys) -> None:
    pool = Pool()
    pool.add(10)
    _seat(nt, monkeypatch, role="planner")
    rc, starts = run(pool)
    assert (rc, starts) == (2, [])
    assert "[refused] next-task: this clone holds the planner's seat worker-2" in (
        capsys.readouterr().err
    )
    assert pool.listed == []


def test_a_clone_that_holds_no_seat_takes_nothing(run, nt, monkeypatch, capsys) -> None:
    pool = Pool()
    pool.add(10)
    topology_with(nt.instance_claims, monkeypatch, nt.instance_claims.Topology(None, {}))
    rc, starts = run(pool, instance=2)
    assert (rc, starts) == (2, [])
    assert "this clone holds no seat of the project's topology" in capsys.readouterr().err


def _scoped_topology(nt, holder: tuple[str, str] | None = ("me", "k2"), *, retired: bool = False):
    """The run's snapshot of a topology whose second seat, `tester`, takes only
    Tasks of the type `test`, and the in-memory GitHub of its state issues.
    `tester` is held by `holder`, and this clone took it."""
    claims = nt.instance_claims
    repo = FakeRepo()
    seat_issue(claims, repo, 11, "planner")
    seat_issue(claims, repo, 12, "tester", holder)
    seats = [
        {"name": "planner", "role": "planner", "organizer": True, "state_issue": 11},
        {
            "name": "tester",
            "role": "worker",
            "state_issue": 12,
            "retired": retired,
            "scope": {"types": ["test"]},
        },
    ]
    doc = {"schema_version": 1, "seats": seats}
    return (seat_snapshot(claims, doc, repo), "tester"), repo


def test_a_seat_takes_within_the_scope_its_topology_gives_it(run, nt, capsys) -> None:
    """DEC-059 point 7: the scope is the one the default branch's topology gives
    the seat this clone took, confirmed on the seat's state issue."""
    pool = Pool()
    pool.add(20, priority="High", kind="feature")
    pool.add(21, priority="Low", kind="test")
    seated, _repo = _scoped_topology(nt)
    rc, starts = run(pool, seated=seated)
    assert (rc, starts) == (0, [(21, False)])
    assert (
        "1 Task is ready for seat tester, instance 2, within the scope of types test"
        in capsys.readouterr().out
    )


def test_a_seat_that_cannot_be_confirmed_takes_nothing(run, nt, capsys) -> None:
    """DEC-059 point 6: a seat another clone holds now is refused before the
    listing is read."""
    pool = Pool()
    pool.add(21, kind="test")
    seated, _repo = _scoped_topology(nt, ("me", "k9"))
    rc, starts = run(pool, seated=seated)
    assert (rc, starts) == (2, [])
    err = capsys.readouterr().err
    assert "[refused] next-task: this clone no longer holds the seat tester" in err
    assert pool.listed == []


def test_a_dry_run_releases_no_retired_seat(run, nt) -> None:
    """A retired seat is released at its clone's next command, but not by a dry run."""
    pool = Pool()
    pool.add(21, kind="test")
    seated, repo = _scoped_topology(nt, retired=True)
    rc, starts = run(pool, extra=("--dry-run",), seated=seated)
    assert (rc, starts) == (2, [])
    assert repo.writes() == []


# ---- pools of workers (DEC-061 points 5, 8 and 9, ADR-072 points 2 and 6) -------------

OPEN_MILESTONES = [
    {"number": 3, "title": "Sprint 3: auth", "description": "Close trigger: either\nPool: alpha"},
    {"number": 4, "title": "Sprint 4: docs", "description": "Pool: bravo"},
    {"number": 5, "title": "Sprint 5: misc", "description": "Close trigger: either"},
    {"number": 6, "title": "Sprint 6: odd", "description": "Pool: charlie"},
]


def _pooled_topology(nt, *, seat_pools: Any = ("alpha",), extra: dict | None = None):
    """The run's snapshot of a topology that declares the pools alpha and bravo,
    whose second seat, `tester`, serves `seat_pools` (None: names none), and
    which this clone took."""
    claims = nt.instance_claims
    repo = FakeRepo()
    seat_issue(claims, repo, 11, "planner")
    seat_issue(claims, repo, 12, "tester", ("me", "k2"))
    tester: dict[str, Any] = {"name": "tester", "role": "worker", "state_issue": 12}
    if seat_pools is not None:
        tester["pools"] = list(seat_pools)
    seats = [{"name": "planner", "role": "planner", "organizer": True, "state_issue": 11}, tester]
    doc = {"schema_version": 1, "pools": ["alpha", "bravo"], "seats": seats, **(extra or {})}
    return seat_snapshot(claims, doc, repo), "tester"


def _milestones(nt, monkeypatch, rows: Any = OPEN_MILESTONES) -> list[int]:
    """The open milestones every read returns (None: the read fails); the
    returned list counts the reads."""
    reads: list[int] = []

    def listed(_config: Any, gh: Any = None) -> Any:
        reads.append(1)
        return rows

    monkeypatch.setattr(nt.pools.milestone, "list_open_milestones", listed)
    return reads


def test_a_seat_takes_only_from_the_open_milestones_of_its_pools(
    run, nt, monkeypatch, capsys
) -> None:
    pool = Pool()
    pool.add(20, priority="High", milestone=4)
    pool.add(21, priority="Low", milestone=3)
    pool.add(22, priority="High", milestone=5)
    pool.add(23, priority="High")
    reads = _milestones(nt, monkeypatch)
    rc, starts = run(pool, seated=_pooled_topology(nt))
    assert (rc, starts) == (0, [(21, False)])
    assert reads == [1]
    captured = capsys.readouterr()
    assert "1 Task is ready for seat tester, instance 2, from its pools (alpha)" in captured.out
    assert "milestone #6 names the pool 'charlie'" in captured.err


def test_milestones_that_cannot_be_read_take_nothing(run, nt, monkeypatch, capsys) -> None:
    """Never the whole Backlog: the run takes nothing and exits 3, never 5."""
    pool = Pool()
    pool.add(21, milestone=3)
    _milestones(nt, monkeypatch, None)
    rc, starts = run(pool, seated=_pooled_topology(nt))
    assert (rc, starts) == (3, [])
    assert "the open milestones could not be read" in capsys.readouterr().err
    assert pool.listed == []


def test_a_seat_that_names_no_pool_takes_nothing_and_says_why(run, nt, monkeypatch, capsys) -> None:
    pool = Pool()
    pool.add(21, milestone=3)
    _milestones(nt, monkeypatch)
    rc, starts = run(pool, seated=_pooled_topology(nt, seat_pools=None))
    assert (rc, starts) == (nt.EXIT_NONE_READY, [])
    assert "this seat names no pool" in capsys.readouterr().out


def test_a_pool_with_no_open_milestone_is_said(run, nt, monkeypatch, capsys) -> None:
    pool = Pool()
    pool.add(21, milestone=3)
    _milestones(nt, monkeypatch, OPEN_MILESTONES[:1])
    rc, starts = run(pool, seated=_pooled_topology(nt, seat_pools=("bravo",)))
    assert (rc, starts) == (nt.EXIT_NONE_READY, [])
    assert "pool bravo has no open milestone" in capsys.readouterr().out


def test_where_no_pool_is_declared_no_milestone_is_read(run, nt, monkeypatch) -> None:
    pool = Pool()
    pool.add(21, kind="test", milestone=4)
    reads = _milestones(nt, monkeypatch)
    seated, _repo = _scoped_topology(nt)
    rc, starts = run(pool, seated=seated)
    assert (rc, starts) == (0, [(21, False)])
    assert reads == []


def test_code_that_cannot_read_the_topology_in_full_takes_nothing(
    run, nt, monkeypatch, capsys
) -> None:
    pool = Pool()
    pool.add(21, milestone=3)
    reads = _milestones(nt, monkeypatch)
    rc, starts = run(pool, seated=_pooled_topology(nt, extra={"lanes": ["x"]}))
    assert (rc, starts) == (2, [])
    err = capsys.readouterr().err
    assert "[refused] next-task: this code cannot read the topology" in err
    assert "keys no topology has: lanes" in err
    assert pool.listed == [] and reads == []


# ---- two clones at once (DEC-035 point 6, DEC-059 point 7) ----------------------------


class StartWorkInProcess:
    """`start-work` run here, on the pool's in-memory GitHub, as this clone runs
    it: its gates pass, its branch and its move are recorded, and its assignee
    and its move are written to the GitHub, as GitHub holds them after."""

    def __init__(self, sw: ModuleType, monkeypatch: pytest.MonkeyPatch, pool: Pool) -> None:
        self.sw = sw
        self.pool = pool
        self.moved: list[int] = []
        self.branches: list[str] = []
        invoker = SimpleNamespace(github_login="me")
        monkeypatch.setattr(sw, "resolve_capability_root", lambda _e: CAP_ROOT)
        monkeypatch.setattr(sw.bootstrap_gate, "enforce", lambda *a, **k: True)
        monkeypatch.setattr(sw.session_guard, "enforce", lambda **k: True)
        monkeypatch.setattr(sw, "load_adopter_config", lambda _r: {"default_branch": "main"})
        monkeypatch.setattr(sw, "_read_members", lambda *a: [])
        monkeypatch.setattr(sw, "resolve_invoker_identity", lambda **k: invoker)
        monkeypatch.setattr(sw, "check_membership", lambda *a: SimpleNamespace(allowed=True))
        monkeypatch.setattr(sw, "_gh_get_issue", lambda n, _c: pool.issue(n))
        monkeypatch.setattr(sw.issue_branch, "_local_branches", lambda: ())
        monkeypatch.setattr(
            sw, "_create_branch", lambda name, _base: self.branches.append(name) or True
        )
        monkeypatch.setattr(sw, "_set_assignee", self._assign)
        monkeypatch.setattr(sw.composed_move, "invoke_move_issue", self._move)
        lib = sw.infer.default_branch
        monkeypatch.setattr(lib, "_read", {})
        monkeypatch.setattr(lib, "_warned", set[str]())

        def ask(explicit: str | None, _run: Any) -> Any:
            branch = lib.Branch("main", False, "origin/main", "c0ffee", None)
            return lib.Reading(
                branch, lib.Base(f"origin/{explicit or 'main'}", "c0ffee", "c0ffee", None)
            )

        monkeypatch.setattr(lib, "_ask", ask)
        self.monkeypatch = monkeypatch

    def _assign(self, number: int, login: str, _config: dict) -> bool:
        held = self.pool.github.issues[number]
        if login not in held.assignees:
            held.assignees.append(login)
        return True

    def _move(self, number: int, target: str, **_kw: Any) -> int:
        self.moved.append(number)
        labels = self.pool.github.issues[number].labels
        labels[:] = [n for n in labels if not n.startswith("state:")] + [f"state:{target}"]
        return 0

    def __call__(self, number: int, *, dry_run: bool) -> int:
        argv = ["start-work", str(number), "--yes", *(["--dry-run"] if dry_run else [])]
        self.monkeypatch.setattr(sys, "argv", argv)
        return self.sw.main()


def _rival(pool: Pool, nt, *, number: int, instance: int, at: int) -> None:
    """The other clone, instance `instance` of this account, claims `number`
    just before its `at`-th read: 0 is next-task's read of the owner, 1 the
    clash guard's, 2 the claim's own read and 3 the claim's re-read."""

    def on_view(issue: int, seen: int) -> None:
        if issue == number and seen == at:
            pool.github.post(issue, _stamp(nt, instance))

    pool.github.on_view = on_view


@pytest.mark.parametrize(
    ("at", "rival", "events"),
    [
        pytest.param(1, 3, ["claim 3"], id="claimed-before-the-guard-read"),
        pytest.param(2, 3, ["claim 3"], id="claimed-after-the-guard-and-first"),
        pytest.param(
            3, 1, ["claim 2", "claim 1", "abandon 2"], id="claimed-in-the-same-instant-by-a-lower"
        ),
    ],
)
def test_two_clones_at_once_never_both_start_one_task(
    run, nt, sw, monkeypatch, capsys, at: int, rival: int, events: list[str]
) -> None:
    """The other clone's claim on #10 holds, and this clone, instance 2, backs
    off and starts #11. This run moves #10 nowhere, and #10 is the rival's.
    Where the rival claimed first, this clone writes no claim on #10, whatever
    the rival's number."""
    pool = Pool()
    pool.add(10, priority="High")
    pool.add(11, priority="Low")
    _rival(pool, nt, number=10, instance=rival, at=at)
    start = StartWorkInProcess(sw, monkeypatch, pool)
    rc, starts = run(pool, instance=2, start=start)
    assert rc == 0
    assert [n for n, _ in starts] == [10, 11]
    assert start.moved == [11]
    assert pool.claims(10) == events
    resolution = nt.instance_claims.ownership.resolve_owner(
        comments=pool.github.issues[10].comments, labels=[], assignee_login="me"
    )
    assert resolution.owners == frozenset({rival})
    assert pool.claims(11) == ["claim 2"]
    out = capsys.readouterr().out
    assert "[note] next-task: another instance claimed #10 first, and the first claim holds" in out
    assert "[ok] next-task: started #11" in out


def test_this_clone_keeps_a_task_it_claimed_first(run, nt, sw, monkeypatch) -> None:
    """A higher instance claims in the same instant: this clone, instance 2,
    keeps #10 and starts it, and the other clone is the one that backs off."""
    pool = Pool()
    pool.add(10, priority="High")
    pool.add(11, priority="Low")
    _rival(pool, nt, number=10, instance=3, at=3)
    start = StartWorkInProcess(sw, monkeypatch, pool)
    rc, starts = run(pool, instance=2, start=start)
    assert rc == 0
    assert [n for n, _ in starts] == [10]
    assert start.moved == [10]
    resolution = nt.instance_claims.ownership.resolve_owner(
        comments=pool.github.issues[10].comments, labels=[], assignee_login="me"
    )
    assert resolution.winner == 2


# ---- the commit the run read (DEC-059 point 1) ----------------------------------------------

_READ = "this clone read the topology of origin/main at c0ffee."


def test_it_names_the_commit_it_read_and_the_start_work_it_runs_does_not_repeat_it(
    run, nt, sw, monkeypatch, capsys
) -> None:
    """A clone says which commit of the default branch it read, once in the run:
    `start-work` reads the topology again to confirm the seat, and says nothing more."""
    pool = Pool()
    pool.add(21, kind="test")
    seated, _repo = _scoped_topology(nt)
    start = StartWorkInProcess(sw, monkeypatch, pool)
    rc, starts = run(pool, seated=seated, start=start)
    assert (rc, starts) == (0, [(21, False)])
    assert start.moved == [21]
    assert capsys.readouterr().err.count(_READ) == 1


def test_a_project_with_no_topology_names_no_commit(run, capsys) -> None:
    pool = Pool()
    pool.add(10)
    rc, starts = run(pool, instance=2)
    assert (rc, starts) == (0, [(10, False)])
    assert "read the topology" not in capsys.readouterr().err


# ---- where the board carries the state (DEC-051 point 6, DEC-062 point 5) ------

BOARD = {"has_projects_v2_board": True, "projects_v2_board_id": 4}
STATE_ON_BOARD = {
    "type": {"kit-label": True},
    "priority": {"kit-label": True},
    "workstream": {"kit-label": True},
    "state": {"board": True},
}


def _board_snapshot(nt, monkeypatch, statuses: dict[int, str | None] | None) -> list[int]:
    """Stand in for the one read of every card's Status: `statuses` maps an issue
    to the Status its card holds, None for no Status; an issue it leaves out has
    no card. None stands for a board that cannot be read. Returns the reads made."""
    reads: list[int] = []

    def read(config, workflow, **_kw):
        reads.append(1)
        if statuses is None:
            return None, "missing required scopes [read:project]"
        options = {f"I_{number}": status for number, status in statuses.items()}
        return nt.board_status.Snapshot("board #4", workflow, options), ""

    monkeypatch.setattr(nt.board_status, "read_snapshot", read)
    return reads


def test_the_state_is_read_from_each_cards_status(run, nt, monkeypatch, capsys) -> None:
    """The labels say Backlog for both, and are not read: the card of #10 says In
    Progress, which no clone takes over outside a topology, and #11's says
    Backlog."""
    pool = Pool()
    pool.add(10, priority="High")
    pool.add(11, priority="Low")
    reads = _board_snapshot(nt, monkeypatch, {10: "In Progress", 11: "Backlog"})

    rc, starts = run(pool, config=BOARD, axes=STATE_ON_BOARD)

    assert (rc, starts) == (0, [(11, False)])
    assert reads == [1]
    assert "1 Task is ready for this clone" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("statuses", "says"),
    [
        ({11: "Backlog"}, "#10 has no card on board #4"),
        ({10: None, 11: "Backlog"}, "#10's card on board #4 has no Status"),
        ({10: "Done", 11: "Backlog"}, "#10's card on board #4 has the Status 'Done'"),
    ],
)
def test_a_task_its_status_does_not_place_is_skipped_with_a_warning(
    run, nt, monkeypatch, capsys, statuses, says
) -> None:
    pool = Pool()
    pool.add(10, priority="High")
    pool.add(11, priority="Low")
    _board_snapshot(nt, monkeypatch, statuses)

    rc, starts = run(pool, config=BOARD, axes=STATE_ON_BOARD)

    assert (rc, starts) == (0, [(11, False)])
    err = capsys.readouterr().err
    assert f"[warn] next-task: #10 skipped: {says}" in err


def test_a_board_that_cannot_be_read_takes_nothing(run, nt, monkeypatch, capsys) -> None:
    """As Milestones that cannot be read take nothing: exit 3, never 5."""
    pool = Pool()
    pool.add(10)
    _board_snapshot(nt, monkeypatch, None)

    rc, starts = run(pool, config=BOARD, axes=STATE_ON_BOARD)

    assert (rc, starts) == (3, [])
    err = capsys.readouterr().err
    assert "the board's Status could not be read" in err
    assert "missing required scopes [read:project]" in err


def test_where_the_map_carries_the_state_off_the_board_no_status_is_read(
    run, nt, monkeypatch
) -> None:
    pool = Pool()
    pool.add(10)
    reads = _board_snapshot(nt, monkeypatch, {})

    rc, starts = run(pool, config=BOARD)

    assert (rc, starts) == (0, [(10, False)])
    assert reads == []
