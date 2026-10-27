"""take-seat, release-seat and seats (DEC-059 points 3 to 6): a clone takes a
seat, releases it, and lists who sits where.

A clone takes a seat by its name or the first free one of a role, only where
the seat names the session's agent definition, through a claim on the seat's
state issue. It holds at most one seat, takes up the one it holds, and releases
a retired one first. A seat is released by its clone, or by force from the
organizer seat's clone or on a person's authorisation, with its reason logged.
The listing shows each seat, its role and its holder, and names the state
issues no seat names. It names too each Task in Review a released seat left,
with the pull request from its branch (#2196). These tests pin each, against a
failing and a passing case. GitHub is the in-memory fake of the state-issue
tests, and the backbone's reading of the default branch and git are fakes.
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

from _lib import audit_log, default_branch, instance_identity, provenance  # noqa: E402
from _lib import instance_ownership as ownership  # noqa: E402
from _lib import state_issues as si  # noqa: E402
from _lib import topology as tp  # noqa: E402

from pm_state_issue_fakes import FakeRepo  # noqa: E402

VERSIONS = provenance.Versions(tree="1.2.3", capability="0.9.0", cli="1.2.3")
TIP = "c0ffee"
TOPOLOGY_REL = ".pkit/capabilities/project-management/project/topology.yaml"
MEMBERS_REL = ".pkit/capabilities/project-management/project/members.yaml"

SEATS = [
    {"name": "planner", "role": "planner", "organizer": True, "state_issue": 11},
    {"name": "worker-1", "role": "worker", "state_issue": 12},
    {"name": "worker-2", "role": "worker", "state_issue": 13},
    {
        "name": "tester",
        "role": "worker",
        "agent": "test-writer",
        "scope": {"types": ["test"]},
        "state_issue": 14,
    },
    {"name": "old", "role": "worker", "retired": True, "state_issue": 15},
]


def _script(file: str) -> Any:
    name = "pm_" + file.removesuffix(".py").replace("-", "_") + "_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TAKE = _script("take-seat.py")
RELEASE = _script("release-seat.py")
LIST = _script("seats.py")


@pytest.fixture(autouse=True)
def fresh_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(default_branch, "_read", {})
    monkeypatch.setattr(default_branch, "_warned", set())


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / ".pkit" / "capabilities" / "project-management"
    (path / "project").mkdir(parents=True)
    return path


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


def _git(seats: list[dict] | None = SEATS, members: tuple[str, ...] = ("me", "you")) -> Any:
    """A git whose default branch holds a topology of ``seats`` (None: no
    topology), and ``members``."""
    files = {MEMBERS_REL: json.dumps({"members": [{"github_login": m} for m in members]})}
    if seats is not None:
        files[TOPOLOGY_REL] = json.dumps({"schema_version": 1, "seats": seats})

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[0] == "ls-tree":
            rel = args[-1]
            return subprocess.CompletedProcess(args, 0, f"{rel}\0" if rel in files else "", "")
        assert args[:2] == ["cat-file", "blob"]
        return subprocess.CompletedProcess(args, 0, files[args[2].partition(":")[2]], "")

    return run


def _repo(**held: tuple[str, str]) -> FakeRepo:
    """The state issues of every seat, each held by the clone ``held`` gives
    for its name (an account and a key), with dashes as underscores."""
    repo = FakeRepo()
    for seat in SEATS:
        number, name = seat["state_issue"], seat["name"]
        repo.add(
            number, si.description("seat", name, si.Fold(None), VERSIONS), title=f"Seat {name}"
        )
        repo.post(number, si.marker_comment("seat", name, VERSIONS))
        holder = held.get(name.replace("-", "_"))
        if holder is not None:
            _claim(repo, number, name, holder)
    return repo


def _claim(repo: FakeRepo, number: int, name: str, holder: tuple[str, str]) -> None:
    claim = audit_log.event(si.CLAIM, key=name, clone=holder[1], place="host:/clone")
    repo.post(number, audit_log.build(claim, versions=VERSIONS), author=holder[0])


def _holder(repo: FakeRepo, number: int, name: str) -> si.Holder | None:
    found = si.read(
        number, "seat", name, si.StateRun(repo, si.Writers.closed(["me", "you"]), VERSIONS)
    )
    assert found.fold is not None
    return found.fold.holder


def _key(root: Path) -> str:
    return instance_identity.ensure_clone_key(root)


def _take(root: Path, repo: FakeRepo, name: str | None = None, **kw: Any) -> int:
    kw.setdefault("role", None)
    kw.setdefault("agent", "project-manager")
    kw.setdefault("login", "me")
    kw.setdefault("run", _backbone())
    kw.setdefault("git", _git())
    return TAKE.take_seat(root, name=name, gh=repo, versions=VERSIONS, **kw)


# ---- take-seat ---------------------------------------------------------------------


def test_it_takes_the_first_free_seat_of_a_role_and_says_who_the_clone_is_now(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo()
    assert _take(root, repo, role="worker") == 0
    key = instance_identity.read_clone_key(root)
    assert key is not None
    assert _holder(repo, 12, "worker-1") == si.Holder("me", key, tp.place(root))
    assert instance_identity.read_seat_hint(root) == "worker-1"
    out = capsys.readouterr().out
    assert f"take-seat: the topology of origin/main at {TIP}" in out
    assert "It is now instance 2, named worker-1 (DEC-059 point 6)." in out
    assert "agent definition: project-manager" in out


def test_it_takes_the_first_free_seat_in_the_topologys_order(root: Path) -> None:
    repo = _repo(planner=("you", "k7"))
    assert _take(root, repo) == 0
    assert instance_identity.read_seat_hint(root) == "worker-1"


def test_it_takes_the_seat_named(root: Path) -> None:
    repo = _repo()
    assert _take(root, repo, "worker-2") == 0
    assert _holder(repo, 13, "worker-2") is not None
    assert _holder(repo, 12, "worker-1") is None


def test_a_seat_of_another_agent_definition_is_not_taken(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """DEC-059 point 4: only a seat whose definition the session follows."""
    repo = _repo()
    assert _take(root, repo, "tester") == 1
    assert repo.writes() == []
    assert "names the agent definition test-writer, and this session follows" in (
        capsys.readouterr().err
    )
    assert _take(root, repo, "tester", agent="test-writer") == 0


def test_no_free_seat_of_the_sessions_definition_takes_none(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(worker_1=("you", "k7"), worker_2=("you", "k8"))
    assert _take(root, repo, role="worker") == 1
    assert repo.writes() == [] and instance_identity.read_seat_hint(root) is None
    assert "no free seat of the role worker names the agent definition" in capsys.readouterr().err


def test_a_seat_another_clone_holds_is_not_taken(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(worker_1=("you", "k7"))
    assert _take(root, repo, "worker-1") == 1
    assert repo.writes() == []
    assert "the seat worker-1 is held by @you, clone k7" in capsys.readouterr().err


def test_a_new_session_takes_up_the_seat_its_clone_holds(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """DEC-059 point 4: the key outlives every session, whatever the runtime
    file says of the seat."""
    repo = _repo(worker_2=("me", _key(root)))
    assert _take(root, repo, role="worker") == 0
    assert repo.writes() == []
    assert instance_identity.read_seat_hint(root) == "worker-2"
    assert "this clone takes up the seat worker-2" in capsys.readouterr().out


def test_a_clone_holds_at_most_one_seat(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(worker_2=("me", _key(root)))
    assert _take(root, repo, "worker-1") == 1
    assert repo.writes() == []
    assert "holds the seat worker-2, and a clone holds at most one seat" in (
        capsys.readouterr().err
    )


def test_a_retired_seat_its_clone_holds_is_released_first(root: Path) -> None:
    """DEC-059 point 5."""
    repo = _repo(old=("me", _key(root)))
    assert _take(root, repo, role="worker") == 0
    assert _holder(repo, 15, "old") is None
    assert instance_identity.read_seat_hint(root) == "worker-1"


def test_a_seat_another_clone_claimed_in_the_same_instant_is_lost(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """DEC-058 point 6: the first claim holds, and the loser writes nothing more."""
    repo = _repo()

    def rival(number: int) -> None:
        if number == 12 and repo.before_post is not None:
            repo.before_post = None
            _claim(repo, 12, "worker-1", ("you", "k7"))

    repo.before_post = rival
    assert _take(root, repo, role="worker") == 1
    assert _holder(repo, 12, "worker-1") == si.Holder("you", "k7", "host:/clone")
    assert instance_identity.read_seat_hint(root) is None
    assert "took the seat worker-1 first, so this clone holds no seat" in capsys.readouterr().err


def test_no_seat_is_taken_where_the_default_branch_cannot_be_resolved(root: Path) -> None:
    """DEC-059 point 1."""
    repo = _repo()
    assert _take(root, repo, run=_backbone(None, "origin/main is not fetched")) == 1
    assert repo.calls == []


def test_no_seat_is_taken_where_the_default_branch_declares_no_topology(root: Path) -> None:
    repo = _repo()
    assert _take(root, repo, git=_git(None)) == 1
    assert repo.calls == []


def test_a_seat_whose_state_issue_is_not_named_or_cannot_be_read_is_not_taken(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """DEC-059 point 3."""
    seats = [*SEATS, {"name": "lead-1", "role": "lead"}]
    repo = _repo()
    assert _take(root, repo, "lead-1", git=_git(seats)) == 1
    assert "the topology names no state issue for it" in capsys.readouterr().err
    repo.failing.add("view")
    assert _take(root, repo, "worker-1") == 1
    assert repo.writes() == []


def test_a_dry_run_claims_nothing(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo()
    assert _take(root, repo, role="worker", dry_run=True) == 0
    assert repo.writes() == [] and instance_identity.read_clone_key(root) is None
    assert "seat 2 (worker-1, a worker): free, on #12" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("explicit", "environ", "agent"),
    [
        ("project-manager", {"PKIT_AGENT": "test-writer"}, "project-manager"),
        (None, {"PKIT_AGENT": "test-writer"}, "test-writer"),
        (None, {}, None),
        ("Not A Name", {}, None),
    ],
)
def test_the_session_says_which_agent_definition_it_follows(explicit, environ, agent) -> None:
    """Harness-agnostic: --agent, else the session's PKIT_AGENT, and no guess."""
    found, problem = TAKE.session_agent(explicit, environ)
    assert found == agent
    assert (problem is None) is (agent is not None)


# ---- release-seat ------------------------------------------------------------------


def _release(root: Path, repo: FakeRepo, name: str | None = None, **kw: Any) -> int:
    kw.setdefault("login", "me")
    kw.setdefault("run", _backbone())
    kw.setdefault("git", _git())
    return RELEASE.release_own(root, name=name, gh=repo, versions=VERSIONS, **kw)


def _force(root: Path, repo: FakeRepo, name: str, reason: str = "its sandbox is gone", **kw):
    kw.setdefault("login", "me")
    kw.setdefault("run", _backbone())
    kw.setdefault("git", _git())
    return RELEASE.release_by_force(
        root, name=name, reason=reason, gh=repo, versions=VERSIONS, **kw
    )


def test_a_clone_releases_the_seat_it_holds_and_forgets_it(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(worker_2=("me", _key(root)))
    instance_identity.write_seat_hint(root, "worker-2")
    assert _release(root, repo) == 0
    assert _holder(repo, 13, "worker-2") is None
    assert instance_identity.read_seat_hint(root) is None
    assert "stops counting, with no write to those issues" in capsys.readouterr().out


def test_a_clone_that_holds_no_seat_releases_nothing(root: Path) -> None:
    repo = _repo(worker_2=("you", "k7"))
    _key(root)
    assert _release(root, repo) == 0
    assert repo.writes() == []
    assert _holder(repo, 13, "worker-2") is not None


def test_a_seat_another_clone_holds_is_released_only_by_force(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(worker_2=("you", "k7"))
    _key(root)
    assert _release(root, repo, "worker-2") == 1
    assert repo.writes() == []
    assert '--force --reason "<why>"' in capsys.readouterr().err


def test_the_organizer_seats_clone_releases_a_seat_by_force_with_its_reason(root: Path) -> None:
    """DEC-059 point 5: the privilege the reviewed topology grants, with no
    person's authorisation, and the reason on the seat's state issue."""
    repo = _repo(planner=("me", _key(root)), worker_1=("you", "k7"))
    assert _force(root, repo, "worker-1") == 0
    assert _holder(repo, 12, "worker-1") is None
    forced = [audit_log.parse(body) for body in repo.bodies(12)]
    assert any(ev is not None and ev.get("reason") == "its sandbox is gone" for ev in forced)


def test_any_other_clone_releases_by_force_only_on_a_persons_authorisation(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Off a terminal with no --yes, it refuses, as a held move does (DEC-006)."""
    repo = _repo(worker_1=("you", "k7"))
    assert _force(root, repo, "worker-1") == 1
    assert repo.writes() == []
    assert "is the person's to authorise" in capsys.readouterr().err
    assert _force(root, repo, "worker-1", yes=True) == 0
    assert _holder(repo, 12, "worker-1") is None


def test_a_release_by_force_carries_its_reason(root: Path) -> None:
    repo = _repo(worker_1=("you", "k7"))
    assert _force(root, repo, "worker-1", reason="  ", yes=True) == 1
    assert repo.writes() == []


def test_a_free_seat_is_not_released_by_force(root: Path) -> None:
    repo = _repo()
    assert _force(root, repo, "worker-1", yes=True) == 0
    assert repo.writes() == []


# ---- seats ---------------------------------------------------------------------


def _list(root: Path, repo: FakeRepo, **kw: Any) -> int:
    kw.setdefault("login", "me")
    kw.setdefault("run", _backbone())
    kw.setdefault("git", _git())
    return LIST.list_seats(root, gh=repo, versions=VERSIONS, **kw)


def test_the_listing_shows_each_seat_its_role_and_its_holder(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(planner=("me", _key(root)), worker_1=("you", "k7"))
    assert _list(root, repo) == 0
    out = capsys.readouterr().out
    assert f"seats: the topology of origin/main at {TIP}, 5 seat(s), 1 retired" in out
    assert "  1. planner (planner, agent project-manager, organizer), #11: held by @me" in out
    assert out.splitlines()[1].endswith("← this clone")
    assert "  2. worker-1 (worker, agent project-manager), #12: held by @you, clone k7" in out
    assert "  3. worker-2 (worker, agent project-manager), #13: free" in out
    assert "  4. tester (worker, agent test-writer, scope: types test), #14: free" in out
    assert "  5. old (worker, agent project-manager, retired), #15: free" in out
    assert repo.writes() == []


def test_the_listing_shows_the_milestones_a_scope_names_each_beside_its_title() -> None:
    """A milestone whose title the run did not read is shown by its number alone."""
    scope = tp.Scope(("cli",), (), (8, 12))
    seat = tp.Seat("sprinter", 6, tp.WORKER, scope=scope, state_issue=16)
    state = tp.SeatState(seat, tp.FREE)
    assert LIST.seat_line(state, mine=False, titles={8: "Phase 2: ship\nit"}) == (
        "  6. sprinter (worker, agent project-manager, scope: workstreams cli with "
        'milestones 8 "Phase 2: ship\\nit" and 12), #16: free'
    )
    assert LIST.seat_line(state, mine=False) == (
        "  6. sprinter (worker, agent project-manager, scope: workstreams cli with "
        "milestones 8 and 12), #16: free"
    )


SPRINTER = {"name": "sprinter", "role": "worker", "scope": {"milestones": [8, 12]}}
MILESTONES_READ = "repos/{owner}/{repo}/milestones?state=all&per_page=100"


def _with_milestones(repo: FakeRepo, answer: list[dict] | None) -> Any:
    """``repo``, which also answers the read of the repository's milestones with
    ``answer``, or fails it where ``answer`` is None."""

    def gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["api", MILESTONES_READ]:
            repo.calls.append(list(argv))
            if answer is None:
                return subprocess.CompletedProcess(argv, 1, "", "HTTP 502: Bad Gateway")
            return subprocess.CompletedProcess(argv, 0, json.dumps(answer), "")
        return repo(argv)

    return gh


def _sprinter_repo() -> FakeRepo:
    """The state issues of every seat, and of `sprinter`, the sixth, free."""
    repo = _repo()
    repo.add(16, si.description("seat", "sprinter", si.Fold(None), VERSIONS), title="Seat sprinter")
    repo.post(16, si.marker_comment("seat", "sprinter", VERSIONS))
    return repo


def test_the_listing_reads_the_milestones_once_for_their_titles(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _sprinter_repo()
    milestones = [{"number": 8, "title": "Release 2.0"}, {"number": 3, "title": "Done"}]
    gh = _with_milestones(repo, milestones)
    git = _git([*SEATS, {**SPRINTER, "state_issue": 16}])
    assert (
        LIST.list_seats(root, login="me", gh=gh, run=_backbone(), git=git, versions=VERSIONS) == 0
    )
    out = capsys.readouterr().out
    assert 'scope: milestones 8 "Release 2.0" and 12), #16: free' in out
    assert [argv for argv in repo.calls if MILESTONES_READ in argv] == [
        ["gh", "api", MILESTONES_READ, "--paginate"]
    ]


def test_where_the_milestones_cannot_be_read_each_is_shown_by_its_number(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = _with_milestones(_sprinter_repo(), None)
    git = _git([*SEATS, {**SPRINTER, "state_issue": 16}])
    assert (
        LIST.list_seats(root, login="me", gh=gh, run=_backbone(), git=git, versions=VERSIONS) == 0
    )
    captured = capsys.readouterr()
    assert "scope: milestones 8 and 12), #16: free" in captured.out
    assert "the repository's milestones could not be read" in captured.err


def test_no_milestone_is_read_where_no_scope_names_one(root: Path) -> None:
    repo = _repo()
    gh = _with_milestones(repo, [])
    assert (
        LIST.list_seats(root, login="me", gh=gh, run=_backbone(), git=_git(), versions=VERSIONS)
        == 0
    )
    assert all(MILESTONES_READ not in argv for argv in repo.calls)


def test_the_listing_names_the_state_issues_no_seat_names(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """DEC-059 point 3: such as those a change closed unmerged left."""
    repo = _repo()
    repo.add(40, si.description("seat", "worker-9", si.Fold(None), VERSIONS), title="Seat worker-9")
    repo.add(41, si.description("seat", "worker-1", si.Fold(None), VERSIONS), title="Seat worker-1")
    repo.add(42, "## What\n\nwork\n", title="[Task] work")
    assert _list(root, repo) == 0
    out = capsys.readouterr().out
    assert "State issues no seat names, for a person to close (DEC-059 point 3):" in out
    assert "  #40  seat worker-9" in out and "  #41  seat worker-1" in out
    assert "#42" not in out and "  #12  seat" not in out


def test_text_from_outside_the_project_cannot_forge_a_line_of_the_listing(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Anyone who may open an issue may write a seat's marker, so a key that is
    no seat's name is shown quoted, and a holder's clone and place escaped."""
    repo = _repo(worker_1=("me", "k\n[ok] forged"))
    forged = "x\n[ok] forged line\x1b[2J"
    repo.add(40, si.description("seat", forged, si.Fold(None), VERSIONS), title="Seat")
    assert _list(root, repo) == 0
    out = capsys.readouterr().out
    assert "\n[ok] forged" not in out and "\x1b" not in out
    assert f"  #40  seat {forged!r}" in out
    assert "held by @me, clone k\\n[ok] forged, at host:/clone" in out


def test_the_listing_says_where_it_could_not_read(root: Path) -> None:
    repo = _repo()
    repo.failing.add("view")
    assert _list(root, repo) == 3
    assert _list(root, _repo(), git=_git(None)) == 0
    default_branch._read.clear()  # a new run, which asks the backbone again
    assert _list(root, _repo(), run=_backbone(None, "origin/main is not fetched")) == 1


def test_every_write_these_commands_run_comes_from_the_seam(root: Path) -> None:
    """ADR-071 point 1: each comment is a state-issue event the seam built, and
    no listing searches."""
    repo = _repo(old=("me", _key(root)), worker_2=("you", "k7"))
    _take(root, repo, role="worker")
    _force(root, repo, "worker-2", yes=True)
    _release(root, repo)
    _list(root, repo)
    writes = repo.writes()
    assert writes
    for argv in writes:
        assert argv[2] in ("comment", "edit"), argv
        if argv[2] == "comment":
            ev = audit_log.parse(argv[5])
            assert ev is not None and ev.type in si.EVENTS
    assert all("--search" not in argv for argv in repo.calls)


# ---- the Tasks in Review a released seat left (DEC-059 points 5 and 9) ---------------


def _task(
    repo: FakeRepo,
    number: int,
    title: str,
    *,
    state: str = "review",
    claims: tuple[tuple[str, str], ...] = (),
    account: str = "you",
) -> None:
    """A Task in ``state``, assigned to ``account``, with a claim of each seat
    and clone key ``claims`` names, as `start-work` posts one: the seat's
    number is its place in the topology."""
    repo.add(
        number, "## What\n\nwork\n", title=title, labels=(f"state:{state}",), assignees=(account,)
    )
    names = [s["name"] for s in SEATS]
    for seat, clone in claims:
        instance = names.index(seat) + 1
        body = ownership.format_event_comment(
            event="claim", instance=instance, seat=seat, seat_number=instance, clone=clone
        )
        repo.post(number, body, author=account)


def _release_event(repo: FakeRepo, number: int, name: str, holder: tuple[str, str]) -> None:
    """The holder's own release of the seat, as `release-seat` posts it."""
    release = audit_log.event(si.RELEASE, key=name, clone=holder[1], place="host:/clone")
    repo.post(number, audit_log.build(release, versions=VERSIONS), author=holder[0])


LEFT_HEADING = (
    "Tasks in Review that a released seat left, each for a person to land or to hand over to "
    "a worker (DEC-059 points 5 and 9):"
)


def test_the_listing_names_each_task_in_review_a_released_seat_left_with_its_pull_request(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The seat's release freed its clone's claims, so no worker's loop takes up
    its Tasks in Review: the listing names each, with the open pull request from
    its branch, for a person to land or hand over."""
    repo = _repo(worker_1=("you", "k7"), worker_2=("you", "k8"))
    _task(repo, 50, "Add the dispatcher", claims=(("worker-1", "k7"),))
    _task(repo, 53, "Write its tests", claims=(("worker-1", "k7"),))
    _task(repo, 51, "Still in its seat", claims=(("worker-2", "k8"),))
    _task(repo, 52, "Back in the pool", state="in-progress", claims=(("worker-1", "k7"),))
    _task(repo, 54, "Handed on", claims=(("worker-1", "k7"), ("worker-2", "k8")))
    _task(repo, 55, "Never claimed")
    repo.prs = {60: "feat/50-add-the-dispatcher", 61: "feat/51-still", 62: "feat/500-other"}
    assert _force(root, repo, "worker-1", yes=True) == 0
    capsys.readouterr()
    written = len(repo.writes())
    assert _list(root, repo) == 0
    out = capsys.readouterr().out
    left = out[out.index(LEFT_HEADING) :].splitlines()
    assert left == [
        LEFT_HEADING,
        "  seat worker-1, clone k7 of @you:",
        "    #50 Add the dispatcher: pull request #60",
        "    #53 Write its tests: no open pull request from its branch",
    ]
    assert len(repo.writes()) == written


def test_a_seat_its_own_clone_took_again_frees_none_of_the_claims_it_released(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A claim made before the clone's current take of the seat counts for
    nothing (#2182), so its Task in Review is still the person's to hand back."""
    repo = _repo(worker_1=("you", "k7"))
    _task(repo, 50, "Add the dispatcher", claims=(("worker-1", "k7"),))
    _release_event(repo, 12, "worker-1", ("you", "k7"))
    _claim(repo, 12, "worker-1", ("you", "k7"))
    repo.prs = {60: "feat/50-add-the-dispatcher"}
    assert _list(root, repo) == 0
    out = capsys.readouterr().out
    assert "  2. worker-1 (worker, agent project-manager), #12: held by @you, clone k7" in out
    assert f"{LEFT_HEADING}\n  seat worker-1, clone k7 of @you:\n" in out
    assert "    #50 Add the dispatcher: pull request #60" in out


def test_no_tasks_log_is_read_until_a_seat_is_released(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Before any release, no claim has stopped counting for one, so the
    listing reads no Task's log and lists no pull request."""
    repo = _repo(worker_1=("you", "k7"))
    _task(repo, 50, "Add the dispatcher", claims=(("worker-1", "k7"),))
    assert _list(root, repo) == 0
    assert LEFT_HEADING not in capsys.readouterr().out
    assert not any("/issues/50/" in " ".join(argv) for argv in repo.calls)
    assert not any(argv[1] == "pr" for argv in repo.calls)


def test_the_listing_says_which_task_or_pull_request_it_could_not_read(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(worker_1=("you", "k7"))
    _task(repo, 50, "Add the dispatcher", claims=(("worker-1", "k7"),))
    _task(repo, 51, "Write its tests", claims=(("worker-1", "k7"),))
    _release_event(repo, 12, "worker-1", ("you", "k7"))
    repo.failing.update({"page:51", "pr-list"})
    assert _list(root, repo) == 3
    captured = capsys.readouterr()
    assert "    #50 Add the dispatcher: its pull request could not be read" in captured.out
    assert "#51" not in captured.out
    assert "the log of #51, in Review, could not be read" in captured.err
    assert "the open pull requests could not be listed" in captured.err


def test_text_from_a_task_cannot_forge_a_line_of_the_listing(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A Task's title, and the key its claim names, are anyone's text."""
    repo = _repo(worker_1=("you", "k\n[ok] forged"))
    _task(repo, 50, "x\n[ok] forged line\x1b[2J", claims=(("worker-1", "k\n[ok] forged"),))
    _release_event(repo, 12, "worker-1", ("you", "k\n[ok] forged"))
    assert _list(root, repo) == 0
    out = capsys.readouterr().out
    assert "\n[ok] forged" not in out and "\x1b" not in out
    assert "  seat worker-1, clone k\\n[ok] forged of @you:" in out
    assert "    #50 x\\n[ok] forged line\\x1b[2J: no open pull request from its branch" in out
