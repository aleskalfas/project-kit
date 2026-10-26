"""The topology of seats (DEC-059 points 1 to 3): its file, its readings and its check.

`_lib/topology` reads `project/topology.yaml`, from the default branch for the
commands that act as a seat and from the working tree for the change. These
tests pin the parse and each problem it reports, the check's further problems,
each against a failing and a passing case, the reading at the default branch's
commit, and `check-topology`'s report. The backbone's reading of the default
branch and every git call are fakes; no test reaches a remote or GitHub.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
TESTS = Path(__file__).resolve().parent
for entry in (SCRIPTS, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from _lib import audit_log, default_branch, provenance, state_issues  # noqa: E402
from _lib import topology as tp  # noqa: E402

from pm_state_issue_fakes import FakeRepo  # noqa: E402

REL = ".pkit/capabilities/project-management/project/topology.yaml"
MEMBERS_REL = ".pkit/capabilities/project-management/project/members.yaml"
TIP = "c0ffee"

PLANNER = {"name": "planner", "role": "planner", "organizer": True, "state_issue": 11}
WORKER = {"name": "worker-1", "role": "worker", "state_issue": 12}
TESTER = {"name": "tester", "role": "worker", "scope": {"types": ["test"]}, "state_issue": 13}


def _doc(*seats: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"schema_version": 1, "seats": [dict(s) for s in seats], **extra}


def _dump(data: object) -> str:
    return json.dumps(data)  # JSON is YAML, and keeps the tests free of a dumper


def _codes(problems: list[tp.Problem] | tuple[tp.Problem, ...]) -> list[str]:
    return [p.code for p in problems]


# ---- the parse -------------------------------------------------------------------


def test_a_sound_topology_parses_with_no_problem() -> None:
    topology = tp.parse(_doc(PLANNER, WORKER, TESTER, settings={"release_mode": "tolerant"}))
    assert topology.problems == ()
    assert [s.name for s in topology.seats] == ["planner", "worker-1", "tester"]
    assert [s.number for s in topology.seats] == [1, 2, 3]
    planner = topology.seat("planner")
    assert planner is not None and planner.organizer and planner.agent == tp.DEFAULT_AGENT
    assert topology.organizer == planner
    tester = topology.seat("tester")
    assert tester is not None and tester.scope == tp.Scope((), ("test",))
    assert topology.release_mode == tp.TOLERANT


def test_a_retired_seat_keeps_its_place_and_number() -> None:
    retired = {"name": "old", "role": "worker", "retired": True, "state_issue": 9}
    topology = tp.parse(_doc(PLANNER, retired, WORKER))
    assert topology.problems == ()
    assert [s.number for s in topology.seats] == [1, 2, 3]
    assert [s.name for s in topology.active] == ["planner", "worker-1"]


def test_a_retired_seat_needs_no_state_issue() -> None:
    assert tp.parse(_doc(PLANNER, {"name": "old", "role": "lead", "retired": True})).problems == ()


def test_a_seat_name_used_twice_is_a_problem() -> None:
    twin = {**WORKER, "state_issue": 14}
    problems = tp.parse(_doc(PLANNER, WORKER, twin)).problems
    assert _codes(problems) == [tp.DUPLICATE_SEAT]
    assert "seats 2 and 3 share the name 'worker-1'" in problems[0].message


def test_more_than_one_organizer_seat_is_a_problem() -> None:
    second = {**WORKER, "organizer": True}
    problems = tp.parse(_doc(PLANNER, second)).problems
    assert _codes(problems) == [tp.ORGANIZERS]
    assert "planner, worker-1" in problems[0].message


def test_a_retired_organizer_seat_does_not_count_as_a_second() -> None:
    retired = {"name": "old", "role": "planner", "organizer": True, "retired": True}
    assert tp.parse(_doc(PLANNER, retired)).problems == ()


def test_a_seat_with_no_state_issue_named_is_a_problem() -> None:
    problems = tp.parse(_doc(PLANNER, {"name": "worker-1", "role": "worker"})).problems
    assert _codes(problems) == [tp.NO_STATE_ISSUE]
    assert "pkit pm create-seats" in problems[0].message


def test_two_seats_naming_one_state_issue_is_a_problem() -> None:
    problems = tp.parse(_doc(PLANNER, {**WORKER, "state_issue": 11})).problems
    assert _codes(problems) == [tp.SHARED_STATE_ISSUE]


@pytest.mark.parametrize(
    ("seat", "said"),
    [
        ({"name": "Planner", "role": "planner", "state_issue": 1}, "has the name 'Planner'"),
        ({"name": "p-", "role": "planner", "state_issue": 1}, "has the name 'p-'"),
        ({"name": "p", "role": "boss", "state_issue": 1}, "has the role 'boss'"),
        ({"name": "p", "role": "lead", "state_issue": 0}, "names the state issue 0"),
        ({"name": "p", "role": "lead", "state_issue": True}, "names the state issue True"),
        ({"name": "p", "role": "lead", "state_issue": 1, "organizer": "yes"}, "`organizer: 'yes'`"),
        ({"name": "p", "role": "lead", "state_issue": 1, "agent": "Agent X"}, "agent 'Agent X'"),
        (
            {"name": "p", "role": "lead", "state_issue": 1, "scope": {}},
            "a scope that names nothing",
        ),
        (
            {"name": "p", "role": "lead", "state_issue": 1, "scope": {"layers": ["x"]}},
            "a scope has not: layers",
        ),
        ({"name": "p", "role": "lead", "state_issue": 1, "holder": "me"}, "keys a seat has not"),
        ("planner", "seat 1 is not a mapping"),
    ],
)
def test_a_shape_the_schema_refuses_is_a_problem(seat: object, said: str) -> None:
    problems = tp.parse({"schema_version": 1, "seats": [seat]}).problems
    assert tp.SHAPE in _codes(problems)
    assert any(said in p.message for p in problems), problems


@pytest.mark.parametrize(
    ("data", "said"),
    [
        (None, "holds nothing"),
        (["planner"], "holds list"),
        ({"schema_version": 2, "seats": []}, "`schema_version` is 2"),
        ({"schema_version": 1, "seats": {}}, "`seats` is not a list"),
        ({"schema_version": 1, "seats": [], "holders": {}}, "keys no topology has"),
        ({"schema_version": 1, "seats": [], "settings": {"release_mode": "strict"}}, "'strict'"),
    ],
)
def test_a_file_the_schema_refuses_is_a_problem(data: object, said: str) -> None:
    problems = tp.parse(data).problems
    assert any(p.code == tp.SHAPE and said in p.message for p in problems), problems


def _schema_errors(data: Any) -> list[str]:
    schema = json.loads((CAPABILITY / "schemas" / "topology.schema.json").read_text("utf-8"))
    return [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(data)]


def test_the_schema_and_the_parse_agree_on_a_sound_file_and_on_bad_shapes() -> None:
    sound = _doc(PLANNER, WORKER, TESTER, settings={"release_mode": "tolerant"})
    assert _schema_errors(sound) == [] and tp.parse(sound).problems == ()
    for bad in (
        _doc({**WORKER, "name": "Worker"}),
        _doc({**WORKER, "role": "boss"}),
        _doc({**WORKER, "state_issue": 0}),
        _doc({**WORKER, "holder": "me"}),
        _doc(WORKER, settings={"release_mode": "strict"}),
        {"schema_version": 2, "seats": []},
    ):
        assert _schema_errors(bad), bad
        assert tp.SHAPE in _codes(tp.parse(bad).problems), bad


def test_the_shipped_carrier_validates_and_parses() -> None:
    data = YAML(typ="safe").load((CAPABILITY / "schemas" / "topology.yaml").read_text("utf-8"))
    assert _schema_errors(data) == []
    assert data["pkit_schema"] == tp.BINDING
    assert tp.parse(data).problems == ()


# ---- the check -------------------------------------------------------------------


def _check(topology: tp.Topology | None, base: tp.Topology | None = None, **kw: Any):
    kw.setdefault("workstreams_declared", ["cli", "docs-site"])
    kw.setdefault("types", ["feature", "bug", "docs", "test"])
    kw.setdefault("substrate", "comment")
    return tp.check(topology, base=base, **kw)


def test_a_scope_naming_an_unknown_workstream_is_a_problem() -> None:
    known = tp.parse(_doc({**WORKER, "scope": {"workstreams": ["cli"]}}))
    assert _check(known) == []
    unknown = tp.parse(_doc({**WORKER, "scope": {"workstreams": ["gui"]}}))
    problems = _check(unknown)
    assert _codes(problems) == [tp.UNKNOWN_WORKSTREAM] and "'gui'" in problems[0].message


def test_a_scope_naming_an_unknown_type_is_a_problem() -> None:
    assert _check(tp.parse(_doc(TESTER))) == []
    unknown = tp.parse(_doc({**TESTER, "scope": {"types": ["design"]}}))
    problems = _check(unknown)
    assert _codes(problems) == [tp.UNKNOWN_TYPE] and "'design'" in problems[0].message


def test_a_topology_under_the_label_substrate_is_a_problem() -> None:
    topology = tp.parse(_doc(PLANNER))
    assert _check(topology, substrate="comment") == []
    problems = _check(topology, substrate="label")
    assert _codes(problems) == [tp.LABEL_SUBSTRATE]
    assert _check(None, substrate="label") == []  # no topology, nothing to refuse


def test_a_seat_of_the_base_deleted_is_a_problem() -> None:
    base = tp.parse(_doc(PLANNER, WORKER), ref="origin/main", commit=TIP)
    problems = _check(tp.parse(_doc(PLANNER)), base)
    assert _codes(problems) == [tp.SEAT_DELETED]
    assert "seat 2 (worker-1) of origin/main at c0ffee is gone" in problems[0].message


def test_a_seat_of_the_base_retired_in_place_is_no_problem() -> None:
    base = tp.parse(_doc(PLANNER, WORKER))
    retired = tp.parse(_doc(PLANNER, {**WORKER, "retired": True}, TESTER))
    assert _check(retired, base) == []


def test_a_seat_of_the_base_moved_is_a_problem() -> None:
    base = tp.parse(_doc(PLANNER, WORKER))
    inserted = tp.parse(_doc(PLANNER, TESTER, WORKER))
    problems = _check(inserted, base)
    assert _codes(problems) == [tp.SEAT_MOVED]
    assert "moved from place 2" in problems[0].message and "to place 3" in problems[0].message


def test_a_renamed_seat_is_a_deleted_one() -> None:
    base = tp.parse(_doc(PLANNER, WORKER))
    renamed = tp.parse(_doc(PLANNER, {**WORKER, "name": "builder"}))
    assert _codes(_check(renamed, base)) == [tp.SEAT_DELETED]


def test_a_change_that_removes_the_file_deletes_every_seat() -> None:
    base = tp.parse(_doc(PLANNER, WORKER))
    assert _codes(_check(None, base)) == [tp.SEAT_DELETED, tp.SEAT_DELETED]


# ---- the readings ----------------------------------------------------------------


def _capability(tmp_path: Path) -> Path:
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    (root / "project").mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "schemas" / "classification.yaml").write_text(
        (CAPABILITY / "schemas" / "classification.yaml").read_text("utf-8"), encoding="utf-8"
    )
    (root / "project" / "workstreams.yaml").write_text(
        "schema_version: 1\nworkstreams:\n  cli: {}\n", encoding="utf-8"
    )
    return root


def _write(capability_root: Path, data: object) -> None:
    tp.path(capability_root).write_text(_dump(data), encoding="utf-8")


class _Backbone:
    """A runner standing in for `pkit repository base --json`, which keeps its calls."""

    def __init__(
        self,
        tip: str | None = TIP,
        *,
        problem: str | None = None,
        unborn: bool = False,
        answers: bool = True,
    ) -> None:
        self.tip, self.problem, self.unborn, self.answers = tip, problem, unborn, answers
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        if not self.answers:
            return subprocess.CompletedProcess(argv, 1, "", "Error: no")
        named = next((a.split("=", 1)[1] for a in argv if a.startswith("--base=")), None)
        document = {
            "schema_version": 1,
            "default_branch": {
                "name": "main",
                "source": "default",
                "ref": "origin/main" if self.tip else None,
                "commit": self.tip,
                "problem": self.problem,
                "unborn": self.unborn,
            },
            "base": {
                "ref": named or "origin/main",
                "tip": self.tip,
                "fork": self.tip,
                "problem": self.problem,
            },
        }
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")


_backbone = _Backbone


def _git(files: dict[tuple[str, str], str], *, failing: bool = False) -> Any:
    """A git that holds ``files``, each by its commit and its path from the root."""

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        if failing:
            return subprocess.CompletedProcess(args, 128, "", "fatal: bad object c0ffee")
        if args[0] == "ls-tree":
            commit, rel = args[-3], args[-1]
            held = f"{rel}\0" if (commit, rel) in files else ""
            return subprocess.CompletedProcess(args, 0, held, "")
        if args[:2] == ["cat-file", "blob"]:
            commit, _, rel = args[2].partition(":")
            return subprocess.CompletedProcess(args, 0, files[(commit, rel)], "")
        raise AssertionError(f"unexpected git call: {args}")

    return run


@pytest.fixture(autouse=True)
def fresh_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(default_branch, "_read", {})
    monkeypatch.setattr(default_branch, "_warned", set())


def test_read_takes_the_default_branch_s_topology_never_the_working_tree(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    _write(root, _doc(WORKER))  # the branch's own file is never read
    git = _git({(TIP, REL): _dump(_doc(PLANNER, WORKER))})
    topology = tp.read(root, run=_backbone(), git=git)
    assert topology is not None
    assert [s.name for s in topology.seats] == ["planner", "worker-1"]
    assert (topology.ref, topology.commit) == ("origin/main", TIP)
    assert topology.where() == f"origin/main at {TIP}"


def test_read_is_none_where_the_default_branch_declares_no_topology(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    _write(root, _doc(PLANNER))
    assert tp.read(root, run=_backbone(), git=_git({})) is None


def test_read_is_none_where_the_default_branch_has_no_commit_yet(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    run = _backbone(None, problem="the default branch has no commit yet", unborn=True)
    assert tp.read(root, run=run, git=_git({}, failing=True)) is None


@pytest.mark.parametrize(
    "run",
    [_backbone(None, problem="origin/main is not fetched"), _backbone(answers=False)],
    ids=["no-commit", "no-answer"],
)
def test_read_refuses_an_unresolvable_default_branch(tmp_path: Path, run: Any) -> None:
    with pytest.raises(tp.Unresolved):
        tp.read(_capability(tmp_path), run=run, git=_git({}))


def test_read_refuses_where_git_cannot_read_the_commit(tmp_path: Path) -> None:
    with pytest.raises(tp.Unresolved, match="bad object"):
        tp.read(_capability(tmp_path), run=_backbone(), git=_git({}, failing=True))


def test_read_carries_what_the_file_says_wrong_of_itself(tmp_path: Path) -> None:
    git = _git({(TIP, REL): "seats: [unclosed"})
    topology = tp.read(_capability(tmp_path), run=_backbone(), git=git)
    assert topology is not None and _codes(topology.problems) == [tp.SHAPE]


def test_writers_are_the_members_the_default_branch_holds(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    (root / "project" / "members.yaml").write_text(  # the branch's own, never read
        _dump({"schema_version": 1, "members": [{"github_login": "mallory"}]}), encoding="utf-8"
    )
    at = tp.Settled("origin/main", TIP)
    members = {"schema_version": 1, "members": [{"github_login": "ann"}, {"github_login": "bo"}]}
    closed = tp.writers_at(root, at, git=_git({(TIP, MEMBERS_REL): _dump(members)}))
    assert closed == state_issues.Writers.closed(["ann", "bo"])
    assert tp.writers_at(root, at, git=_git({})) == state_issues.Writers.open()
    empty = {"schema_version": 1, "members": []}
    assert tp.writers_at(root, at, git=_git({(TIP, MEMBERS_REL): _dump(empty)})).gate_open


# ---- check_change and check-topology ------------------------------------------------


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "pm_check_topology_under_test", SCRIPTS / "check-topology.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_check_says_which_commit_it_read_and_passes_a_sound_change(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _capability(tmp_path)
    _write(root, _doc(PLANNER, WORKER, TESTER))
    git = _git({(TIP, REL): _dump(_doc(PLANNER, WORKER))})
    report = tp.check_change(root, run=_backbone(), git=git)
    assert report.problems == () and report.base == tp.Settled("origin/main", TIP)
    assert _load_script().say(report) == 0
    out = capsys.readouterr().out
    assert f"base: origin/main at {TIP}" in out and "3 seat(s)" in out


def test_the_check_fails_a_change_that_deletes_a_seat(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _capability(tmp_path)
    _write(root, _doc(PLANNER))
    git = _git({(TIP, REL): _dump(_doc(PLANNER, WORKER))})
    report = tp.check_change(root, run=_backbone(), git=git)
    assert _codes(report.problems) == [tp.SEAT_DELETED]
    assert _load_script().say(report) == 1
    assert "error  seat 2 (worker-1)" in capsys.readouterr().out


def test_the_check_compares_with_the_base_named_for_the_run(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    _write(root, _doc(PLANNER))
    run = _backbone()
    report = tp.check_change(root, "release-1", run=run, git=_git({}))
    assert report.base == tp.Settled("release-1", TIP)
    assert any("--base=release-1" in argv for argv in run.calls)


def test_the_check_reads_the_project_s_workstreams_types_and_substrate(tmp_path: Path) -> None:
    root = _capability(tmp_path)
    scoped = {**WORKER, "scope": {"workstreams": ["gui"], "types": ["design"]}}
    _write(root, _doc(PLANNER, scoped))
    (root / "project" / "instance-ownership.yaml").write_text(
        "schema_version: 1\nsubstrate: label\n", encoding="utf-8"
    )
    report = tp.check_change(root, run=_backbone(), git=_git({}))
    assert sorted(_codes(report.problems)) == sorted(
        [tp.UNKNOWN_WORKSTREAM, tp.UNKNOWN_TYPE, tp.LABEL_SUBSTRATE]
    )


def test_the_check_refuses_an_unresolvable_base_where_a_topology_is_declared(
    tmp_path: Path,
) -> None:
    root = _capability(tmp_path)
    _write(root, _doc(PLANNER))
    run = _backbone(None, problem="origin/main is not fetched")
    report = tp.check_change(root, run=run, git=_git({}))
    assert _codes(report.problems) == [tp.UNRESOLVED] and report.base is None
    assert "origin/main is not fetched" in report.problems[0].message


def test_the_check_of_a_tree_with_no_topology_notes_an_unresolvable_base(
    tmp_path: Path,
) -> None:
    report = tp.check_change(_capability(tmp_path), run=_backbone(answers=False), git=_git({}))
    assert report.problems == () and report.topology is None
    assert report.notes and "could not be read" in report.notes[0]


def test_the_check_of_a_tree_with_no_topology_and_none_on_the_base_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tp.check_change(_capability(tmp_path), run=_backbone(), git=_git({}))
    assert report.problems == () and report.notes == ()
    assert _load_script().say(report) == 0
    assert "no topology at project/topology.yaml" in capsys.readouterr().out


# ---- one run's snapshot (ADR-071 points 1 and 8) ------------------------------------

VERSIONS = provenance.Versions(tree="1.2.3", capability="0.9.0", cli="1.2.3")


def _state_issue(repo: FakeRepo, number: int, name: str, holder: tuple[str, str] | None) -> None:
    repo.add(number, state_issues.description("seat", name, state_issues.Fold(None), VERSIONS))
    repo.post(number, state_issues.marker_comment("seat", name, VERSIONS))
    if holder is not None:
        claim = audit_log.event(state_issues.CLAIM, key=name, clone=holder[1], place="h:/c")
        repo.post(number, audit_log.build(claim, versions=VERSIONS), author=holder[0])


def _snapshot(tmp_path: Path, repo: FakeRepo, *seats: dict[str, Any], **kw: Any):
    members = {"schema_version": 1, "members": [{"github_login": "me"}]}
    files = {(TIP, REL): _dump(_doc(*seats)), (TIP, MEMBERS_REL): _dump(members)}
    kw.setdefault("account", "me")
    kw.setdefault("key", "k1")
    return tp.snapshot(
        _capability(tmp_path), gh=repo, run=_backbone(), git=_git(files), versions=VERSIONS, **kw
    )


def test_the_snapshot_takes_the_default_branchs_topology_members_and_this_clone(
    tmp_path: Path,
) -> None:
    snap = _snapshot(tmp_path, FakeRepo(), PLANNER, WORKER)
    assert snap is not None
    assert [s.name for s in snap.topology.seats] == ["planner", "worker-1"]
    assert snap.topology.where() == f"origin/main at {TIP}"
    assert snap.run.writers == state_issues.Writers.closed(["me"])
    assert (snap.clone.account, snap.clone.key) == ("me", "k1")
    assert snap.clone.place.endswith(str(tmp_path))


def test_there_is_no_snapshot_where_the_default_branch_declares_no_topology(
    tmp_path: Path,
) -> None:
    root = _capability(tmp_path)
    repo = FakeRepo()
    assert tp.snapshot(root, gh=repo, account="me", key="k1", run=_backbone(), git=_git({})) is None
    default_branch._read.clear()  # a new run, which asks the backbone again
    with pytest.raises(tp.Unresolved, match="did not say which branch is settled"):
        tp.snapshot(root, gh=repo, account="me", key=None, run=_backbone(answers=False))
    assert repo.calls == []


def test_a_seats_holder_is_read_from_its_state_issue_once_a_run(tmp_path: Path) -> None:
    repo = FakeRepo()
    _state_issue(repo, 11, "planner", ("me", "k1"))
    _state_issue(repo, 12, "worker-1", None)
    snap = _snapshot(tmp_path, repo, PLANNER, WORKER)
    assert snap is not None
    planner = snap.state("planner")
    assert planner is not None and planner.state == tp.HELD and planner.held_by(snap.clone)
    assert planner.said() == "held by @me, clone k1, at h:/c"
    assert snap.state("planner") is planner
    worker = snap.state("worker-1")
    assert worker is not None and worker.state == tp.FREE and not worker.held_by(snap.clone)
    assert snap.state("worker-9") is None
    views = [argv[3] for argv in repo.calls if argv[1:3] == ["issue", "view"]]
    assert views == ["11", "12"]


def test_a_seat_with_no_state_issue_or_an_unreadable_one_is_unread(tmp_path: Path) -> None:
    """No reader takes such a seat for free (ADR-041 point 5)."""
    repo = FakeRepo()
    _state_issue(repo, 12, "worker-1", None)
    repo.failing.add("view")
    lead = {"name": "lead-1", "role": "lead"}
    snap = _snapshot(tmp_path, repo, WORKER, lead)
    assert snap is not None
    states = snap.states()
    assert [s.state for s in states] == [tp.UNREAD, tp.UNREAD]
    assert "could not be read" in str(states[0].cause)
    assert states[1].cause == "the topology names no state issue for it"
    assert states[0].said().startswith("unread (")


def test_the_place_names_the_machine_and_a_folder_under_home_from_the_tilde(
    tmp_path: Path,
) -> None:
    """DEC-058 point 5, with no user's name in a claim a public repository shows."""
    root = _capability(tmp_path)
    machine, _, folder = tp.place(root, home=tmp_path.parent).partition(":")
    assert machine and folder == f"~/{tmp_path.name}"
    assert tp.place(root, home=tmp_path / "elsewhere").endswith(":" + tmp_path.resolve().as_posix())


def test_a_clone_with_no_key_holds_no_seat(tmp_path: Path) -> None:
    repo = FakeRepo()
    _state_issue(repo, 11, "planner", ("me", "k1"))
    snap = _snapshot(tmp_path, repo, PLANNER, key=None)
    assert snap is not None
    state = snap.state("planner")
    assert state is not None and state.state == tp.HELD and not state.held_by(snap.clone)


def test_what_a_write_found_replaces_what_the_run_read(tmp_path: Path) -> None:
    repo = FakeRepo()
    _state_issue(repo, 12, "worker-1", None)
    snap = _snapshot(tmp_path, repo, WORKER)
    assert snap is not None
    seat = snap.topology.seat("worker-1")
    assert seat is not None
    claimed = state_issues.claim(12, "seat", "worker-1", snap.clone, snap.run)
    state = snap.learn(seat, claimed.read)
    assert state.held_by(snap.clone) and snap.state("worker-1") is state
    assert snap.learn(seat, None).state == tp.UNREAD


# ---- the commit a run names (DEC-059 point 1) -----------------------------------------


def test_a_run_names_the_commit_it_read_once() -> None:
    """A clone says which commit of the default branch it read, and a second
    reading of the same commit in the run says it no more."""
    env: dict[str, str] = {}
    tree = tp.parse(_doc(PLANNER), ref="origin/main", commit=TIP)
    assert tp.name_once(tree, env) == f"origin/main at {TIP}"
    assert env == {tp.NAMED_ENV: TIP}
    assert tp.name_once(tree, env) is None


def test_a_reading_of_another_commit_names_that_commit() -> None:
    """The default branch moved between two readings of one run: the second
    names the commit it read."""
    env = {tp.NAMED_ENV: TIP}
    moved = tp.parse(_doc(PLANNER), ref="origin/main", commit="beef")
    assert tp.name_once(moved, env) == "origin/main at beef"
    assert tp.name_once(moved, env) is None


def test_a_topology_read_at_no_commit_names_nothing() -> None:
    env: dict[str, str] = {}
    assert tp.name_once(tp.Topology(), env) is None
    assert env == {}


def test_the_commit_named_reaches_each_command_the_run_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The commit is kept in this process's environment, so a command that this
    one runs, such as the `move-issue` that `start-work` runs, inherits it."""
    monkeypatch.setenv(tp.NAMED_ENV, "")
    tree = tp.parse(_doc(PLANNER), ref="origin/main", commit=TIP)
    assert tp.name_once(tree) == f"origin/main at {TIP}"
    child = subprocess.run(
        [sys.executable, "-c", f"import os; print(os.environ[{tp.NAMED_ENV!r}])"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert child.stdout.strip() == TIP
