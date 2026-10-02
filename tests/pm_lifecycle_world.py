"""Issues moved through the real project-management scripts and the real process
engine, against an in-memory GitHub.

The scripts run in this process. `subprocess.run` is routed so that `gh` reaches
an in-memory tracker, `pkit process` reaches the engine's own CLI, and a script
that runs `move-issue` or `close-issue` runs its `main` here. The engine runs the shipped
issue-lifecycle definition in a scratch repository, and its predicates answer
from the tracker through the capability's own predicate code. A test compares
the tracker's view of an issue's state with the engine's and reads the engine's
journal.

A test module loads the scripts once (`load_script`), builds the scratch
repository per test (`make_engine_repo`) and wires a `World` over both
(`wire`).

A predicate answers in this process, but as its script would: where the
capability's predicate code could not reach an answer, the script exits 2 and
the engine reads no answer, so the harness hands the engine the same failure,
with what the code said on standard error.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
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
from project_kit.command_runner import diagnostic_tail
from project_kit.process import PredicateFailure, PredicateRunner, ProcessEngine, load_definition
from tests.process_journal_support import enable_journal_logging

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAPABILITY_ROOT / "scripts"
ADDRESS = "project-management:issue-lifecycle"

INVOKER = SimpleNamespace(github_login="octocat", email="octocat@example.com")
#: Who merges a pull request: another authority than the invoker, so the engine's
#: cross-authority gate on Review → Done passes.
MERGER = "a-reviewer"
REASON = "the maintainer asked for it in session"
MILESTONE = {"number": 7, "title": "Sprint 1"}
AUDIT_MARKER = "<!-- pkit-audit -->"
REPOSITORY_URL = "https://api.github.com/repos/acme/repo"

AUTHORED_BODY = (
    "## What\n\nA task filed to be promoted.\n\n"
    "## Acceptance criteria\n\n- [x] it is promoted\n\n"
    "## Doc impact\n\nNo doc impact.\n"
)

sys.path.insert(0, str(SCRIPTS_DIR))
from _lib import bootstrap_gate, session_guard  # noqa: E402
from _lib import lifecycle_inference as inference  # noqa: E402
from _lib import lifecycle_predicates as predicates  # noqa: E402


def load_script(script: str, module_name: str) -> ModuleType:
    """Load a capability script as a module named `module_name`."""
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _done(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def _option(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv else None


def _options(argv: list[str], flag: str) -> list[str]:
    return [argv[i + 1] for i, arg in enumerate(argv[:-1]) if arg == flag]


class Tracker:
    """GitHub as the scripts' `gh` calls see it: one repository's issues, their
    comments and their label timeline, all posted as the invoker, its one open
    milestone, and its merged pull requests.

    An issue is read through `gh issue view` and through its REST record
    (`gh api repos/{owner}/{repo}/issues/<n>`), which also carries its native
    parent: `native_parents` maps an issue to the issue it is natively a
    sub-issue of, in this repository or — given as `owner/repo#<n>` — in
    another. A closed issue's `state_reason` is GitHub's close reason enum
    (`COMPLETED`, `NOT_PLANNED`), set as GitHub sets it: completed for a merged
    pull request's `Closes #N`, and as `gh issue close --reason` says. Each
    close stamps the issue's `closedAt` with a time no other close has; a reopen
    clears it. `fail_next` holds `gh issue edit` flags whose next edit fails,
    once, before it changes anything; `views_fail` holds issues whose `gh issue
    view` fails, as a predicate's read of an unreachable issue does;
    `comments_fail` holds issues whose `gh issue comment` fails, posting
    nothing; `comment_reads_fail` holds issues whose comments cannot be read,
    while every other field of theirs can."""

    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self.comments: dict[int, list[dict[str, Any]]] = {}
        self.timeline: dict[int, list[dict[str, Any]]] = {}
        self.milestones: list[dict[str, Any]] = [MILESTONE]
        self.merged_prs: dict[int, dict[str, Any]] = {}
        self.native_parents: dict[int, int | str] = {}
        self.calls: list[list[str]] = []
        self.fail_next: set[str] = set()
        self.views_fail: set[int] = set()
        self.comments_fail: set[int] = set()
        self.comment_reads_fail: set[int] = set()
        self.closes = 0

    def merge(self, pr: int, closes: list[int], merged_by: str = MERGER) -> None:
        """Merge pull request `pr`, whose body closes `closes`, as `merged_by`,
        and close each of those issues the way GitHub does: closed, labels
        untouched."""
        body = "".join(f"Closes #{n}\n" for n in closes)
        self.merged_prs[pr] = {
            "number": pr,
            "state": "MERGED",
            "mergedAt": "2026-10-01T00:00:00Z",
            "mergedBy": {"login": merged_by},
            "body": body,
            "url": f"https://github.com/acme/repo/pull/{pr}",
        }
        for number in closes:
            self.close(number, "COMPLETED")

    def close(self, number: int, reason: str | None) -> None:
        """Close the issue with close reason `reason` (None: none reported)."""
        self.closes += 1
        self.issues[number]["state"] = "CLOSED"
        self.issues[number]["state_reason"] = reason
        self.issues[number]["closed_at"] = f"2026-10-01T12:00:{self.closes:02d}Z"

    def reopen(self, number: int) -> None:
        """Reopen the issue the way GitHub does when someone reopens it: open,
        with no close reason or time, labels untouched."""
        self.issues[number]["state"] = "OPEN"
        self.issues[number]["state_reason"] = None
        self.issues[number]["closed_at"] = None

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
        if argv[1] == "issue" and argv[2] in ("view", "edit", "comment", "close", "reopen"):
            number = int(argv[3])
            if argv[2] == "view":
                return self._view(argv, number, str(_option(argv, "--json")))
            if argv[2] == "edit":
                return self._edit(argv, number)
            if argv[2] == "close":
                reason = _option(argv, "--reason") or "completed"
                self.close(number, reason.upper().replace(" ", "_"))
                return _done(argv)
            if argv[2] == "reopen":
                self.reopen(number)
                return _done(argv)
            if number in self.comments_fail:
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            body = _option(argv, "--body")
            self.comments[number].append(
                {"body": body, "viewerDidAuthor": True, "includesCreatedEdit": False}
            )
            return _done(argv)
        if argv[1:3] == ["pr", "view"]:
            pr = self.merged_prs.get(int(argv[3]))
            if pr is None:
                return _done(argv, 1, stderr="no pull requests found")
            fields = str(_option(argv, "--json")).split(",")
            return _done(argv, stdout=json.dumps({f: pr[f] for f in fields}))
        if argv[1:3] == ["pr", "list"] and _option(argv, "--state") == "merged":
            fields = str(_option(argv, "--json")).split(",")
            prs = [{f: pr[f] for f in fields} for pr in self.merged_prs.values()]
            return _done(argv, stdout=json.dumps(prs))
        if argv[1] == "api" and argv[-1].endswith("/timeline"):
            number = int(argv[-1].split("/")[-2])
            return _done(argv, stdout=json.dumps(self.timeline[number]))
        if argv[1] == "api" and argv[-1].endswith("/milestones?state=open"):
            return _done(argv, stdout=json.dumps(self.milestones))
        record = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)", argv[-1])
        if argv[1] == "api" and record:
            return self._record(argv, int(record.group(1)))
        raise AssertionError(f"unexpected gh call: {argv}")

    def _record(self, argv: list[str], number: int) -> subprocess.CompletedProcess[str]:
        """The issue's REST record, as `gh api` prints it."""
        issue = self.issues.get(number)
        if issue is None:
            return _done(argv, 1, stderr="gh: Not Found (HTTP 404)")
        record = {
            "id": 1000 + number,
            "number": number,
            "title": issue["title"],
            "body": issue["body"],
            "state": issue["state"].lower(),
            "labels": [{"name": name} for name in issue["labels"]],
            "milestone": issue["milestone"],
            "repository_url": REPOSITORY_URL,
        }
        parent = self.native_parents.get(number)
        if isinstance(parent, str):
            repository, parent_number = parent.split("#")
            record["parent_issue_url"] = (
                f"https://api.github.com/repos/{repository}/issues/{parent_number}"
            )
        elif parent is not None:
            record["parent_issue_url"] = f"{REPOSITORY_URL}/issues/{parent}"
        return _done(argv, stdout=json.dumps(record))

    def reads(self, number: int) -> int:
        """How many times the issue was read, through either read."""
        return sum(
            1
            for argv in self.calls
            if argv[1:4] == ["issue", "view", str(number)]
            or (argv[1] == "api" and argv[-1] == f"repos/{{owner}}/{{repo}}/issues/{number}")
        )

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
        if number in self.views_fail:
            return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
        if number in self.comment_reads_fail and "comments" in fields.split(","):
            return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
        issue = self.issues[number]
        record = {
            "title": issue["title"],
            "body": issue["body"],
            "state": issue["state"],
            "stateReason": issue.get("state_reason") or "",
            "closedAt": issue.get("closed_at"),
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


class World:
    """The tracker, the engine and the scripts, wired as `subprocess.run` sees
    them: `gh` reaches the tracker, `pkit process` the engine's own CLI, and a
    script's move-issue — or close-issue, when the world has it (`cl`) — runs
    in this process. `engine_calls` lists every `pkit process` call made."""

    def __init__(self, tracker: Tracker, engine_repo: Path, ci, pi, mi, hist, cl=None) -> None:
        self.tracker = tracker
        self.engine_repo = engine_repo
        self.ci, self.pi, self.mi, self.hist, self.cl = ci, pi, mi, hist, cl
        self.engine_calls: list[list[str]] = []

    def run(self, argv, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = [str(arg) for arg in argv]
        if argv[0] == "gh":
            return self.tracker.gh(argv)
        if argv[:2] == ["pkit", "process"]:
            self.engine_calls.append(argv)
            result = CliRunner().invoke(pkit_main, argv[1:])
            if result.exception is not None and not isinstance(result.exception, SystemExit):
                raise result.exception
            return _done(argv, result.exit_code, result.stdout, result.stderr)
        if argv[0] == sys.executable and argv[1].endswith("move-issue.py"):
            return _done(argv, _with_argv(["move-issue.py", *argv[2:]], self.mi.main))
        if argv[0] == sys.executable and argv[1].endswith("close-issue.py") and self.cl:
            return _done(argv, _with_argv(["close-issue.py", *argv[2:]], self.cl.main))
        raise AssertionError(f"unexpected subprocess: {argv}")

    # --- the scripts ----------------------------------------------------------

    def file_issue(
        self,
        body: str = AUTHORED_BODY,
        *,
        title: str = "[Task] A freshly filed task",
        labels: tuple[str, ...] = ("type:task",),
    ) -> int:
        """File an issue the way create-issue does, through its own tracker call.
        By default a Task: a kind label, no state label, no milestone."""
        url = self.ci._gh_create_issue(
            title=title,
            body=body,
            labels=list(labels),
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

    def move(self, number: int, target: str, *options: str) -> int:
        """Run move-issue on the issue with `options` (`--dry-run`, …)."""
        return _with_argv(
            [
                "move-issue.py",
                str(number),
                "--to",
                target,
                *options,
                "--capability-root",
                str(CAPABILITY_ROOT),
                "--yes",
            ],
            self.mi.main,
        )

    def close(self, number: int, *options: str) -> int:
        """Run close-issue on the issue with `options` (`--mode`, `--reason`, …)."""
        assert self.cl is not None, "this world was built without close-issue"
        return _with_argv(
            [
                "close-issue.py",
                str(number),
                *options,
                "--capability-root",
                str(CAPABILITY_ROOT),
                "--yes",
            ],
            self.cl.main,
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

    # --- the two views --------------------------------------------------------

    def _engine(self, number: int) -> ProcessEngine:
        definition = load_definition(self.engine_repo, ADDRESS)
        return ProcessEngine.for_subject(definition, self.engine_repo, str(number))

    def views(self, number: int) -> tuple[str, str | None]:
        """(the tracker's state, the engine's position) for the issue."""
        return self.tracker.state_of(number), self._engine(number).resolve_position().state_id

    def journal(self, number: int) -> list[dict[str, Any]]:
        """The engine journal's move entries for the issue, oldest first."""
        return [entry for entry in self._engine(number).read_journal() if "to" in entry]

    def moves(self, number: int) -> list[tuple[str | None, str, str]]:
        """The engine journal's moves: (from, to, trigger)."""
        return [
            (entry.get("from"), entry["to"], entry["trigger"]) for entry in self.journal(number)
        ]

    def journal_files(self) -> list[Path]:
        return sorted((self.engine_repo / ".pkit").rglob("*.journal.jsonl"))

    # --- what the tracker holds -----------------------------------------------

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


def _predicate_answer(run_name: str, number: int) -> dict[str, Any] | None:
    """What the capability's predicate code answers for `run_name`, or None
    when no script of the capability runs it."""
    if run_name == "detect-state":
        return predicates.classify_state(number)
    if run_name.startswith("detect-"):
        return predicates.detect_state(number, run_name.removeprefix("detect-"))
    if run_name == "gate-checkboxes-ticked":
        return predicates.gate_checkboxes_ticked(number)
    if run_name == "gate-pr-merged":
        return predicates.gate_pr_merged(number)
    return None


def answer_from_tracker(
    runner: PredicateRunner, run_name: str, with_args: Any
) -> dict[str, Any] | PredicateFailure:
    """The engine's predicate run, answered in this process by the capability's
    own predicate code (which reads the tracker through `gh`), under its
    script's exit-code contract: an answer the predicate could not reach is no
    answer — the script exits 2, with what the predicate said on standard
    error — never the payload it carries."""
    said = io.StringIO()
    with contextlib.redirect_stderr(said):
        answer = _predicate_answer(run_name, int(runner.subject))
    if answer is None:
        return PredicateFailure("could not start: no script of the capability runs it")
    if answer.get(predicates.INDETERMINATE_KEY):
        return PredicateFailure("exited 2", diagnostic_tail(said.getvalue()))
    return answer


def make_engine_repo(tmp_path: Path) -> Path:
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


def wire(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """Route this process's subprocesses, the engine and the scripts' identity
    through `world`."""
    monkeypatch.setattr(subprocess, "run", world.run)
    monkeypatch.setattr(process_mod, "resolve_repo_root", lambda: world.engine_repo)
    monkeypatch.setattr(PredicateRunner, "_invoke", answer_from_tracker)
    monkeypatch.setattr(predicates, "_capability_root", lambda: CAPABILITY_ROOT)
    # Who runs the scripts and where they run are other tests' subjects.
    monkeypatch.setattr(session_guard, "enforce", lambda **kw: True)
    monkeypatch.setattr(bootstrap_gate, "enforce", lambda *a, **kw: True)
    scripts = [world.pi, world.mi, *([world.cl] if world.cl else [])]
    for script in scripts:
        monkeypatch.setattr(script, "resolve_invoker_identity", lambda config=None: INVOKER)
    for script in scripts[1:]:
        monkeypatch.setattr(script, "fire_hooks", lambda *a, **kw: None)
