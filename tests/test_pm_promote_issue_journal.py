"""Promoting a freshly filed issue records one move, Todo → Backlog (#1183).

`move-issue` writes the state label first and asks the process engine to record
the move second, in the order the process README's seam-ordering contract sets.
By then live detection reads the label just written. The engine took the live
position for the move's origin, so `promote-issue` had it asked for backlog →
backlog; it refused, and every successful promotion printed "the process engine
refused this move". `move-issue` now names the origin it read before the label
write (`pkit process move --from`).

Promoting with `--milestone` made no move at all (#1210). promote-issue attached
the milestone first, and the workflow reads a milestone as Backlog, so its
move-issue found nothing to move: no state label, no audit comment, nothing
journaled. It now moves first and attaches the milestone second, and a re-run
after a failure between the two completes the promotion without a second audit
comment.

These tests run the sequence through the real scripts and the real engine. The
issue is filed with create-issue's own tracker call, then promoted by
promote-issue, whose move-issue runs in this process. GitHub is an in-memory
tracker. The engine runs the shipped issue-lifecycle definition in a scratch
repository, and its predicates answer from that tracker through the capability's
own predicate code. After each step the tracker's view of the issue's state and
the engine's are compared.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import process as process_mod
from project_kit.cli import main as pkit_main
from project_kit.process import PredicateRunner, ProcessEngine, load_definition
from tests.process_journal_support import enable_journal_logging, set_journal_logging

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAPABILITY_ROOT / "scripts"
ADDRESS = "project-management:issue-lifecycle"

ENGINE_WARNING = "the process engine refused this move"
INVOKER = SimpleNamespace(github_login="octocat", email="octocat@example.com")
REASON = "the maintainer asked for it in session"
MILESTONE = {"number": 7, "title": "Sprint 1"}
AUDIT_MARKER = "<!-- pkit-audit -->"

AUTHORED_BODY = (
    "## What\n\nA task filed to be promoted.\n\n"
    "## Acceptance criteria\n\n- [x] it is promoted\n\n"
    "## Doc impact\n\nNo doc impact.\n"
)
UNTICKED_BODY = AUTHORED_BODY.replace("- [x]", "- [ ]")

sys.path.insert(0, str(SCRIPTS_DIR))
from _lib import bootstrap_gate, session_guard  # noqa: E402
from _lib import lifecycle_inference as inference  # noqa: E402
from _lib import lifecycle_predicates as predicates  # noqa: E402


def _load(script: str, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return _load("create-issue.py", "pm_create_issue_journal_sequence")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return _load("promote-issue.py", "pm_promote_issue_journal_sequence")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return _load("move-issue.py", "pm_move_issue_journal_sequence")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return _load("history.py", "pm_history_journal_sequence")


def _done(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def _option(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv else None


def _options(argv: list[str], flag: str) -> list[str]:
    return [argv[i + 1] for i, arg in enumerate(argv[:-1]) if arg == flag]


class _Tracker:
    """GitHub as this sequence's `gh` calls see it: one repository's issues,
    their comments and their label timeline, all posted as the invoker, and its
    one open milestone.

    `fail_next` holds `gh issue edit` flags whose next edit fails, once, before
    it changes anything."""

    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self.comments: dict[int, list[dict[str, Any]]] = {}
        self.timeline: dict[int, list[dict[str, Any]]] = {}
        self.milestones: list[dict[str, Any]] = [MILESTONE]
        self.calls: list[list[str]] = []
        self.fail_next: set[str] = set()

    def state_of(self, number: int) -> str:
        """The issue's state as the tracker carries it, read with move-issue's
        precedence (closed, then the state label, then a milestone)."""
        issue = self.issues[number]
        return inference.infer_current_state(
            state=issue["state"].lower(), milestone=issue["milestone"], labels=issue["labels"]
        )

    def gh(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        if argv[1:3] == ["issue", "create"]:
            return self._create(argv)
        if argv[1] == "issue" and argv[2] in ("view", "edit", "comment"):
            number = int(argv[3])
            if argv[2] == "view":
                return self._view(argv, number, str(_option(argv, "--json")))
            if argv[2] == "edit":
                return self._edit(argv, number)
            body = _option(argv, "--body")
            self.comments[number].append(
                {"body": body, "viewerDidAuthor": True, "includesCreatedEdit": False}
            )
            return _done(argv)
        if argv[1] == "api" and argv[-1].endswith("/timeline"):
            number = int(argv[-1].split("/")[-2])
            return _done(argv, stdout=json.dumps(self.timeline[number]))
        if argv[1] == "api" and argv[-1].endswith("/milestones?state=open"):
            return _done(argv, stdout=json.dumps(self.milestones))
        raise AssertionError(f"unexpected gh call: {argv}")

    def _create(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        number = len(self.issues) + 1
        milestone = _option(argv, "--milestone")
        self.issues[number] = {
            "title": _option(argv, "--title"),
            "body": _option(argv, "--body"),
            "state": "OPEN",
            "labels": _options(argv, "--label"),
            "assignees": _options(argv, "--assignee"),
            "milestone": {"title": milestone} if milestone else None,
        }
        self.comments[number] = []
        self.timeline[number] = []
        return _done(argv, stdout=f"https://github.com/acme/repo/issues/{number}\n")

    def _view(self, argv: list[str], number: int, fields: str):
        issue = self.issues[number]
        record = {
            "title": issue["title"],
            "body": issue["body"],
            "state": issue["state"],
            "milestone": issue["milestone"],
            "labels": [{"name": name} for name in issue["labels"]],
            "assignees": [{"login": login} for login in issue["assignees"]],
            "url": f"https://github.com/acme/repo/issues/{number}",
            "comments": self.comments[number],
        }
        return _done(argv, stdout=json.dumps({f: record[f] for f in fields.split(",")}))

    def _edit(self, argv: list[str], number: int) -> subprocess.CompletedProcess[str]:
        failing = self.fail_next.intersection(argv)
        if failing:
            self.fail_next -= failing
            return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
        title = _option(argv, "--milestone")
        if title is not None:
            self.issues[number]["milestone"] = next(
                m for m in self.milestones if m["title"] == title
            )
        labels = self.issues[number]["labels"]
        for event, flag in (("unlabeled", "--remove-label"), ("labeled", "--add-label")):
            for name in _options(argv, flag):
                if event == "labeled":
                    labels.append(name)
                else:
                    labels.remove(name)
                self.timeline[number].append(
                    {
                        "event": event,
                        "label": {"name": name},
                        "actor": {"login": INVOKER.github_login},
                        "created_at": "2026-10-01T00:00:00Z",
                    }
                )
        return _done(argv)


def _with_argv(argv: list[str], main) -> int:
    saved = sys.argv
    sys.argv = argv
    try:
        return main()
    finally:
        sys.argv = saved


class _World:
    """The tracker, the engine and the scripts, wired as `subprocess.run` sees
    them: `gh` reaches the tracker, `pkit process` the engine's own CLI, and
    promote-issue's move-issue runs in this process."""

    def __init__(self, tracker: _Tracker, engine_repo: Path, ci, pi, mi, hist) -> None:
        self.tracker = tracker
        self.engine_repo = engine_repo
        self.ci, self.pi, self.mi, self.hist = ci, pi, mi, hist

    def run(self, argv, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = [str(arg) for arg in argv]
        if argv[0] == "gh":
            return self.tracker.gh(argv)
        if argv[:2] == ["pkit", "process"]:
            result = CliRunner().invoke(pkit_main, argv[1:])
            if result.exception is not None and not isinstance(result.exception, SystemExit):
                raise result.exception
            return _done(argv, result.exit_code, result.stdout, result.stderr)
        if argv[0] == sys.executable and argv[1].endswith("move-issue.py"):
            return _done(argv, _with_argv(["move-issue.py", *argv[2:]], self.mi.main))
        raise AssertionError(f"unexpected subprocess: {argv}")

    # --- the sequence ------------------------------------------------------

    def file_issue(self, body: str = AUTHORED_BODY) -> int:
        """File a Task the way create-issue does, through its own tracker call: a
        kind label, no state label, no milestone."""
        url = self.ci._gh_create_issue(
            title="[Task] A freshly filed task",
            body=body,
            labels=["type:task"],
            assignee=INVOKER.github_login,
            milestone_title=None,
            config={},
        )
        assert url is not None
        return int(url.rsplit("/", 1)[1])

    def promote(self, number: int, milestone: str | None = None) -> int:
        scheduling = ["--milestone", milestone] if milestone is not None else []
        return _with_argv(
            [
                "promote-issue.py",
                str(number),
                *scheduling,
                "--reason",
                REASON,
                "--capability-root",
                str(CAPABILITY_ROOT),
                "--yes",
            ],
            self.pi.main,
        )

    def move(self, number: int, target: str) -> int:
        return _with_argv(
            [
                "move-issue.py",
                str(number),
                "--to",
                target,
                "--capability-root",
                str(CAPABILITY_ROOT),
                "--yes",
            ],
            self.mi.main,
        )

    def history(self, number: int) -> int:
        return _with_argv(
            [
                "history.py",
                str(number),
                "--check-drift",
                "--capability-root",
                str(CAPABILITY_ROOT),
            ],
            self.hist.main,
        )

    # --- the two views ------------------------------------------------------

    def _engine(self, number: int) -> ProcessEngine:
        definition = load_definition(self.engine_repo, ADDRESS)
        return ProcessEngine.for_subject(definition, self.engine_repo, str(number))

    def views(self, number: int) -> tuple[str, str | None]:
        """(the tracker's state, the engine's position) for the issue."""
        return self.tracker.state_of(number), self._engine(number).resolve_position().state_id

    def moves(self, number: int) -> list[tuple[str | None, str, str]]:
        """The engine journal's moves: (from, to, trigger)."""
        return [
            (entry.get("from"), entry["to"], entry["trigger"])
            for entry in self._engine(number).read_journal()
            if "to" in entry
        ]

    def journal_files(self) -> list[Path]:
        return sorted((self.engine_repo / ".pkit").rglob("*.journal.jsonl"))

    # --- what the tracker holds --------------------------------------------

    def labels(self, number: int) -> list[str]:
        return self.tracker.issues[number]["labels"]

    def milestone(self, number: int) -> str | None:
        milestone = self.tracker.issues[number]["milestone"]
        return milestone["title"] if milestone else None

    def audit_comments(self, number: int) -> list[str]:
        """The audit comments on the issue that carry the promotion's reason."""
        return [
            comment["body"]
            for comment in self.tracker.comments[number]
            if AUDIT_MARKER in comment["body"] and REASON in comment["body"]
        ]

    def milestone_calls(self) -> list[list[str]]:
        """The `gh` calls that read the open milestones or write one."""
        return [
            argv
            for argv in self.tracker.calls
            if "--milestone" in argv or argv[-1].endswith("/milestones?state=open")
        ]


def _answer_from_tracker(
    runner: PredicateRunner, run_name: str, with_args: Any
) -> dict[str, Any] | None:
    """The engine's predicate run, answered in this process by the capability's
    own predicate code (which reads the tracker through `gh`)."""
    number = int(runner.subject)
    if run_name.startswith("detect-"):
        return predicates.detect_state(number, run_name.removeprefix("detect-"))
    if run_name == "gate-checkboxes-ticked":
        return predicates.gate_checkboxes_ticked(number)
    return None  # not reached from todo or backlog; unrunnable reads as indeterminate


@pytest.fixture
def engine_repo(tmp_path: Path) -> Path:
    """A scratch repository holding the shipped issue-lifecycle definition, the
    package that registers its predicates and the shape contract, with journal
    logging on."""
    repo = tmp_path / "engine"
    capability = repo / ".pkit" / "capabilities" / "project-management"
    (capability / "schemas").mkdir(parents=True)
    shutil.copy(CAPABILITY_ROOT / "schemas" / "workflow.yaml", capability / "schemas")
    shutil.copy(CAPABILITY_ROOT / "package.yaml", capability)
    defs = repo / ".pkit" / "schemas" / "_defs"
    defs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / ".pkit" / "schemas" / "_defs" / "process.schema.json", defs)
    enable_journal_logging(repo)
    return repo


@pytest.fixture
def world(engine_repo: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> _World:
    world = _World(_Tracker(), engine_repo, ci, pi, mi, hist)
    monkeypatch.setattr(subprocess, "run", world.run)
    monkeypatch.setattr(process_mod, "resolve_repo_root", lambda: engine_repo)
    monkeypatch.setattr(PredicateRunner, "_invoke", _answer_from_tracker)
    monkeypatch.setattr(predicates, "_capability_root", lambda: CAPABILITY_ROOT)
    # Who runs the scripts and where they run are other tests' subjects.
    monkeypatch.setattr(session_guard, "enforce", lambda **kw: True)
    monkeypatch.setattr(bootstrap_gate, "enforce", lambda *a, **kw: True)
    for script in (pi, mi):
        monkeypatch.setattr(script, "resolve_invoker_identity", lambda config=None: INVOKER)
    monkeypatch.setattr(mi, "fire_hooks", lambda *a, **kw: None)
    return world


# --- the sequence ---------------------------------------------------------


def test_promoting_a_filed_issue_journals_one_todo_to_backlog_move(
    world: _World, capsys: pytest.CaptureFixture[str]
) -> None:
    number = world.file_issue()
    assert world.views(number) == ("todo", "todo")
    assert world.moves(number) == []

    assert world.promote(number) == 0
    promoted = capsys.readouterr()
    assert ENGINE_WARNING not in promoted.err
    assert f"[ok] promoted #{number} Todo → Backlog" in promoted.out
    assert world.views(number) == ("backlog", "backlog")
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]

    # `pkit pm history` shows the one move, and the timeline holds no state
    # change the journal lacks.
    assert world.history(number) == 0
    history = capsys.readouterr().out
    assert history.count("todo → backlog (promote-issue)") == 1
    assert "no ungoverned state changes detected" in history


def test_with_journal_logging_off_promoting_prints_no_engine_warning(
    world: _World, capsys: pytest.CaptureFixture[str]
) -> None:
    set_journal_logging(world.engine_repo, enabled=False)
    number = world.file_issue()
    assert world.views(number) == ("todo", "todo")

    assert world.promote(number) == 0
    promoted = capsys.readouterr()
    assert ENGINE_WARNING not in promoted.err
    assert f"[ok] promoted #{number} Todo → Backlog" in promoted.out
    assert world.views(number) == ("backlog", "backlog")
    assert world.journal_files() == []


def test_the_next_move_journals_its_own_transition_not_a_self_loop(
    world: _World, capsys: pytest.CaptureFixture[str]
) -> None:
    # In Progress declares a move to itself (create-draft). Taking the live
    # position for the origin journaled Backlog → In Progress as that self-loop,
    # silently, where Todo → Backlog was refused out loud.
    number = world.file_issue()
    assert world.promote(number) == 0

    assert world.move(number, "in-progress") == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.views(number) == ("in-progress", "in-progress")
    assert world.moves(number) == [
        ("todo", "backlog", "promote-issue"),
        ("backlog", "in-progress", "start-work"),
    ]


def test_a_move_the_engine_refuses_still_warns(
    world: _World, capsys: pytest.CaptureFixture[str]
) -> None:
    # Backlog → Done is gated on every checkbox being ticked. move-issue writes
    # the label regardless, and the engine refuses to record the move.
    number = world.file_issue(body=UNTICKED_BODY)
    assert world.promote(number) == 0
    capsys.readouterr()

    assert world.move(number, "done") == 0
    moved = capsys.readouterr()
    assert world.views(number) == ("done", "done")
    assert (
        f"[warn] {ENGINE_WARNING}: refused: gate refused: 1 unticked checkbox(es) remain. "
        in moved.err
    )
    assert f"`pkit pm history {number} --check-drift` will show the gap" in moved.err
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]


# --- scheduling while promoting (#1210) -------------------------------------


def _assert_promoted(world: _World, number: int, milestone: str | None) -> None:
    """The issue is in Backlog on both views with `milestone` set (or none), one
    audit comment carries the reason, and the journal holds one todo → backlog
    move that `pm history --check-drift` finds no drift against."""
    assert world.views(number) == ("backlog", "backlog")
    assert "state:backlog" in world.labels(number)
    assert world.milestone(number) == milestone
    assert len(world.audit_comments(number)) == 1
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]
    assert world.history(number) == 0


def test_promoting_with_a_milestone_makes_the_whole_move_and_schedules(
    world: _World, capsys: pytest.CaptureFixture[str]
) -> None:
    # Attached first, the milestone read as Backlog: move-issue found nothing
    # to move, and the issue ended with the milestone and nothing else.
    number = world.file_issue()
    assert world.views(number) == ("todo", "todo")

    assert world.promote(number, milestone=MILESTONE["title"]) == 0
    promoted = capsys.readouterr()
    assert ENGINE_WARNING not in promoted.err
    assert f"[ok] promoted #{number} Todo → Backlog (milestone: Sprint 1)" in promoted.out
    _assert_promoted(world, number, milestone="Sprint 1")
    assert "no ungoverned state changes detected" in capsys.readouterr().out


def test_a_rerun_after_the_milestone_write_fails_attaches_it_without_moving_again(
    world: _World, capsys: pytest.CaptureFixture[str]
) -> None:
    number = world.file_issue()
    world.tracker.fail_next = {"--milestone"}

    assert world.promote(number, milestone=MILESTONE["title"]) == 2
    assert (
        f"[warn] #{number} was moved to Backlog but milestone 'Sprint 1' was not attached."
        in capsys.readouterr().err
    )
    # The move is whole; only the milestone is missing.
    assert "state:backlog" in world.labels(number)
    assert world.milestone(number) is None
    assert len(world.audit_comments(number)) == 1
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]

    assert world.promote(number, milestone=MILESTONE["title"]) == 0
    assert f"[ok] #{number} already at state:backlog (milestone attached" in (
        capsys.readouterr().out
    )
    _assert_promoted(world, number, milestone="Sprint 1")


def test_a_rerun_after_the_label_write_fails_posts_the_audit_comment_once(
    world: _World, capsys: pytest.CaptureFixture[str]
) -> None:
    # move-issue posts the audit comment before the label write, so the reason
    # survives the failure; the re-run finds that comment by its key and moves.
    number = world.file_issue()
    world.tracker.fail_next = {"--add-label"}

    assert world.promote(number, milestone=MILESTONE["title"]) == 3
    assert (
        f"[warn] move-issue exited 3: #{number} was not moved and milestone 'Sprint 1' "
        "was not attached" in capsys.readouterr().err
    )
    assert world.views(number) == ("todo", "todo")
    assert world.milestone(number) is None
    assert len(world.audit_comments(number)) == 1
    assert world.moves(number) == []

    assert world.promote(number, milestone=MILESTONE["title"]) == 0
    assert "transition audit comment already present" in capsys.readouterr().out
    _assert_promoted(world, number, milestone="Sprint 1")


def test_promoting_without_a_milestone_leaves_the_milestone_alone(
    world: _World, capsys: pytest.CaptureFixture[str]
) -> None:
    number = world.file_issue()

    assert world.promote(number) == 0
    assert f"[ok] promoted #{number} Todo → Backlog (milestone unchanged)" in (
        capsys.readouterr().out
    )
    _assert_promoted(world, number, milestone=None)
    assert world.milestone_calls() == []
