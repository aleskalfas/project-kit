"""Tests for `land-work` (#1203) — one verb lands a pull request.

The real `land-work`, `review-pr` and `done-work` scripts run against an in-memory
GitHub (`_FakeGitHub`): every `gh` call the pm scripts make, and every one the
backbone's pull-request mechanic makes (routed in-process by
`tests.pull_request_backbone`), is answered from one PR's state, which a test
scripts — the checks on each head read by read, a head that moves at a given
call. The local checkout is a real git clone with a real origin, so the head
step compares real commits and the freshness rule reads real diffs. Only the
reviewer agent (the harness's `claude`), the verbs done-work runs after a
merge (`move-issue`, `close-issue`) and the branch clean-up are stubbed.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests import pull_request_backbone

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT = CAPABILITY / "scripts" / "land-work.py"

ISSUE = 42
PR = 496
BRANCH = "feat/42-land-it"
PANEL = ("reviewer", "code-reviewer")

_GREEN = [
    {
        "__typename": "CheckRun",
        "name": "checks",
        "status": "COMPLETED",
        "conclusion": "SUCCESS",
        "startedAt": "2026-10-01T10:00:00Z",
        "completedAt": "2026-10-01T10:08:00Z",
        "detailsUrl": "https://github.com/o/r/actions/runs/77/job/1",
    }
]
_RUNNING = [{"__typename": "CheckRun", "name": "checks", "status": "IN_PROGRESS"}]
_RED = [
    {
        "__typename": "CheckRun",
        "name": "checks",
        "status": "COMPLETED",
        "conclusion": "FAILURE",
        "detailsUrl": "https://github.com/o/r/actions/runs/78/job/2",
    }
]

_PR_BODY = (
    f"Closes #{ISSUE}\n\n"
    "## Summary\n\nLand it.\n\n"
    "## Test plan\n\n- [x] The tests pass.\n\n"
    "## Doc impact\n\nThe README.\n"
)

_BLOCKING = (
    "The change is unsafe.\n\n"
    "- [block] `land.py:10` merges a head nobody reviewed.\n"
    "  It must pin the head.\n"
    "- [advisory] A name could be clearer.\n"
    "* **[block]** The exit code hides a refusal.\n"
)


@pytest.fixture(scope="module")
def land() -> Iterator[ModuleType]:
    lib_dir = str(SCRIPT.parent)
    sys.path.insert(0, lib_dir)
    spec = importlib.util.spec_from_file_location("pm_land_work_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_land_work_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(lib_dir)


# ---- the in-memory GitHub ----------------------------------------------------


def _done(args: list[str], stdout: str = "", returncode: int = 0, stderr: str = "") -> Any:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


@dataclass
class _FakeGitHub:
    """One PR, its issue and its checks, as GitHub would answer for them."""

    mq: ModuleType
    head: str
    base: str
    #: The checks on each head, one list per reading; the last one stays.
    checks: dict[str, list[list[dict[str, Any]]]] = field(default_factory=dict)
    labels: list[str] = field(default_factory=lambda: ["state:review"])
    draft: bool = False
    state: str = "OPEN"
    mergeable: str = "MERGEABLE"
    merge_commit: str = ""
    #: The base branch merges through a queue.
    queue: bool = False
    queued: bool = False
    #: Every reading fails once a merge has been asked for.
    unreadable_after_merge: bool = False
    comments: list[dict[str, Any]] = field(default_factory=list)
    calls: list[list[str]] = field(default_factory=list)
    merges: list[list[str]] = field(default_factory=list)
    #: (when, what): `what` runs once, before the first call `when` matches.
    hooks: list[tuple[Callable[[list[str]], bool], Callable[[], None]]] = field(
        default_factory=list
    )
    #: The first call each of these matches gets no answer: gh exits 1.
    fails: list[Callable[[list[str]], bool]] = field(default_factory=list)
    _reads: dict[str, int] = field(default_factory=dict)

    # -- what the pm scripts ask (`_lib.gh.gh_run`) --

    def gh(self, args: list[str], config: dict[str, Any], **_: Any) -> Any:
        argv = list(args[1:]) if args[:1] == ["gh"] else list(args)
        self.calls.append(argv)
        for hook in list(self.hooks):
            when, what = hook
            if when(argv):
                self.hooks.remove(hook)
                what()
        for fail in list(self.fails):
            if fail(argv):
                self.fails.remove(fail)
                return _done(argv, returncode=1, stderr="HTTP 502: Bad Gateway")
        if argv[:2] == ["pr", "list"]:
            wanted = _option(argv, "--state")
            matches = _option(argv, "--head") == BRANCH and (
                (wanted == "open" and self.state == "OPEN")
                or (wanted == "merged" and self.state == "MERGED")
            )
            return _done(argv, json.dumps([self._view()] if matches else []))
        if argv[:2] == ["pr", "view"]:
            fields = (_option(argv, "--json") or "").split(",")
            view = self._view()
            if "statusCheckRollup" in fields:
                view["statusCheckRollup"] = self._rollup()
            return _done(argv, json.dumps({f: view.get(f) for f in fields}))
        if argv[:2] == ["pr", "comment"]:
            self.comments.append(
                {
                    "author": {"login": "octocat"},
                    "body": _option(argv, "--body"),
                    "createdAt": f"2026-10-01T11:{len(self.comments):02d}:00Z",
                    "url": f"https://github.com/o/r/pull/{PR}#c{len(self.comments)}",
                    "viewerDidAuthor": True,
                    "lastEditedAt": None,
                }
            )
            return _done(argv)
        if argv[:2] == ["pr", "review"]:
            return _done(argv)
        if argv[:2] == ["issue", "view"]:
            issue = {
                "number": ISSUE,
                "title": "[Task] Land it",
                "labels": [{"name": name} for name in self.labels],
                "body": "## Acceptance criteria\n\n- [x] landed\n",
                "state": "CLOSED" if self.state == "MERGED" else "OPEN",
                "closedAt": None,
                "milestone": None,
            }
            return _done(argv, json.dumps(issue))
        if argv[:2] == ["api", "user"]:
            return _done(argv, "octocat\n")
        if argv[:2] == ["api", "graphql"] and any(
            "closedByPullRequestsReferences" in a for a in argv
        ):
            merged = [dict(self._view(), state="MERGED")] if self.state == "MERGED" else []
            issue = {
                "closedByPullRequestsReferences": {"nodes": merged},
                "timelineItems": {"nodes": []},
            }
            return _done(argv, json.dumps({"data": {"repository": {"issue": issue}}}))
        return _done(argv, returncode=1, stderr=f"the fake GitHub does not know {argv}")

    def _view(self) -> dict[str, Any]:
        merged = self.state == "MERGED"
        return {
            "number": PR,
            "title": "feat(pm): land it",
            "isDraft": self.draft,
            "headRefName": BRANCH,
            "headRefOid": self.head,
            "baseRefName": "main",
            "baseRefOid": self.base,
            "state": self.state,
            "mergeable": self.mergeable,
            "isCrossRepository": False,
            "mergedAt": "2026-10-01T12:00:00Z" if merged else None,
            "author": {"login": "author"},
            "body": _PR_BODY,
            "comments": self.comments,
            "commits": [{"oid": self.head, "committedDate": "2026-10-01T09:00:00Z"}],
            "closingIssuesReferences": [{"number": ISSUE}],
            "reviews": [],
            "mergeCommit": {"oid": self.merge_commit} if merged else None,
        }

    def _rollup(self) -> list[dict[str, Any]]:
        readings = self.checks.get(self.head, [[]])
        seen = self._reads.get(self.head, 0)
        self._reads[self.head] = seen + 1
        return readings[min(seen, len(readings) - 1)]

    # -- what the backbone's pull-request mechanic asks --

    def reading(self, pr_number: int, config: dict[str, Any]) -> Any:
        if self.unreadable_after_merge and self.merges:
            raise self.mq.Unreadable("HTTP 502")
        return pull_request_backbone.reading(
            self.mq,
            has_queue=self.queue,
            merge_method="SQUASH" if self.queue else "",
            pr_state=self.state,
            head_oid=self.head,
            in_queue=self.queued,
            position=1 if self.queued else None,
            entry_state="AWAITING_CHECKS" if self.queued else "",
        )

    def backbone_gh(self, argv: Any) -> Any:
        argv = list(argv)[1:]
        if argv[:2] == ["pr", "merge"]:
            self.merges.append(argv)
            if _option(argv, "--match-head-commit") != self.head:
                return _done(argv, returncode=1, stderr="Head branch was modified")
            if "--auto" in argv:
                self.queued = True
            elif not self.unreadable_after_merge:
                self.state = "MERGED"
                self.merge_commit = "c" * 40
            return _done(argv)
        if argv[:2] == ["api", "repos/{owner}/{repo}"]:
            return _done(
                argv,
                json.dumps(
                    {
                        "squash_merge_commit_title": "PR_TITLE",
                        "squash_merge_commit_message": "PR_BODY",
                    }
                ),
            )
        return _done(argv, returncode=1, stderr=f"the fake backbone gh does not know {argv}")

    # -- what a test asks --

    def before(self, when: Callable[[list[str]], bool], what: Callable[[], None]) -> None:
        self.hooks.append((when, what))

    def verdicts(self) -> list[str]:
        return [c["body"].splitlines()[0] for c in self.comments]


def _option(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv else None


def _pr_list(argv: list[str]) -> bool:
    return argv[:2] == ["pr", "list"] and _option(argv, "--state") == "open"


def _nth(predicate: Callable[[list[str]], bool], n: int) -> Callable[[list[str]], bool]:
    """Matches the `n`th call (1-based) `predicate` matches."""
    seen = [0]

    def when(argv: list[str]) -> bool:
        if predicate(argv):
            seen[0] += 1
        return seen[0] == n and predicate(argv)

    return when


# ---- the clone, the project and the run ------------------------------------


def _git(cwd: Path, *argv: str) -> str:
    proc = subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


@dataclass
class _Run:
    """One test's world: the clone, GitHub, and what the stubbed verbs did."""

    land: ModuleType
    work: Path
    github: _FakeGitHub
    #: Each reviewer invocation: (reviewer, the head it was shown).
    invoked: list[tuple[str, str]] = field(default_factory=list)
    #: What each reviewer answers: (verdict, body), or None for a failed run.
    answers: dict[str, tuple[str, str] | None] = field(default_factory=dict)
    after_merge: list[str] = field(default_factory=list)
    sleeps: list[float] = field(default_factory=list)

    def commit(self, name: str, *, push: bool) -> str:
        (self.work / name).write_text(name, encoding="utf-8")
        _git(self.work, "add", name)
        _git(self.work, "commit", "-q", "-m", f"add {name}")
        if push:
            _git(self.work, "push", "-q", "origin", BRANCH)
        return _git(self.work, "rev-parse", "HEAD")

    def push_new_head(self, name: str) -> str:
        """A push to the PR's branch: the PR's head moves to it."""
        self.github.head = self.commit(name, push=True)
        return self.github.head

    def run(self, *argv: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
        rc = self.land.main([str(ISSUE), *argv])
        captured = capsys.readouterr()
        return rc, captured.out, captured.err


def _stage_project(work: Path, *, mode: str) -> Path:
    capability = work / ".pkit" / "capabilities" / "project-management"
    project = capability / "project"
    project.mkdir(parents=True)
    shutil.copytree(CAPABILITY / "schemas", capability / "schemas")
    shutil.copytree(CAPABILITY / "templates", capability / "templates")
    reviewers = "".join(f"      - name: {name}\n" for name in PANEL)
    (project / "config.yaml").write_text(
        "schema_version: 1\n"
        "default_branch: main\n"
        "workstreams: []\n"
        "review:\n"
        f"  mode: {mode}\n"
        "  agents:\n"
        "    local_registered:\n" + reviewers,
        encoding="utf-8",
    )
    (project / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )
    agents = work / ".claude" / "agents"
    agents.mkdir(parents=True)
    for name in PANEL:
        (agents / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    return capability


@dataclass(frozen=True)
class _Clone:
    """An origin and a clone of it on the PR's branch, one commit past main,
    pushed: built once per module, copied for each test."""

    root: Path
    base: str
    head: str


@pytest.fixture(scope="module")
def clone(tmp_path_factory: pytest.TempPathFactory) -> _Clone:
    root = tmp_path_factory.mktemp("land-work-clone")
    _git(root, "init", "-q", "--bare", "-b", "main", "origin.git")
    work = root / "work"
    work.mkdir()
    _git(work, "init", "-q", "-b", "main")
    _git(work, "config", "user.email", "octocat@example.com")
    _git(work, "config", "user.name", "Octo Cat")
    # Relative, so a copy of `root` pushes to its own copy of the origin.
    _git(work, "remote", "add", "origin", "../origin.git")
    (work / ".gitignore").write_text(".pkit/\n.claude/\n", encoding="utf-8")
    _git(work, "add", ".gitignore")
    _git(work, "commit", "-q", "-m", "start")
    _git(work, "push", "-q", "-u", "origin", "main")
    base = _git(work, "rev-parse", "HEAD")
    _git(work, "switch", "-q", "-c", BRANCH)
    (work / "change.txt").write_text("change", encoding="utf-8")
    _git(work, "add", "change.txt")
    _git(work, "commit", "-q", "-m", "add change.txt")
    _git(work, "push", "-q", "origin", BRANCH)
    return _Clone(root, base, _git(work, "rev-parse", "HEAD"))


@pytest.fixture
def world(land, clone, tmp_path, monkeypatch) -> Callable[..., _Run]:
    def build(*, mode: str = "agent", checks: list[list[dict[str, Any]]] | None = None) -> _Run:
        shutil.copytree(clone.root, tmp_path / "clone", symlinks=True)
        work = tmp_path / "clone" / "work"
        _stage_project(work, mode=mode)
        monkeypatch.chdir(work)
        monkeypatch.setenv("PM_INVOKER_LOGIN", "octocat")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        github = _FakeGitHub(mq=land.merge_queue, head=clone.head, base=clone.base)
        run = _Run(land=land, work=work, github=github)
        github.checks[github.head] = checks if checks is not None else [_GREEN]

        gh_module = sys.modules["_lib.gh"]
        for module in (gh_module, land, land.done_work, land.review_pr):
            monkeypatch.setattr(module, "gh_run", github.gh)
        now = [0.0]

        def sleep(seconds: float) -> None:
            run.sleeps.append(seconds)
            now[0] += seconds

        monkeypatch.setattr(land, "_sleep", sleep)
        monkeypatch.setattr(land, "_monotonic", lambda: now[0])
        pull_request_backbone.in_process(
            monkeypatch,
            land.merge_queue,
            gh=github.backbone_gh,
            read=github.reading,
            sleep=sleep,
            clock=lambda: now[0],
        )

        def invoke(name, pr_number, config, timeout=None, effort=None, **kwargs):
            run.invoked.append((name, kwargs.get("sha", "")))
            answer = run.answers.get(name, ("APPROVED", "Looks right."))
            return answer if answer is not None else (None, "")

        monkeypatch.setattr(land.review_pr, "_invoke_agent", invoke)

        def verb(name: str) -> Callable[..., int]:
            def stub(issue_number: int, *args: Any, **kwargs: Any) -> int:
                run.after_merge.append(f"{name} #{issue_number}")
                return 0

            return stub

        monkeypatch.setattr(land.done_work, "_invoke_move_issue", verb("move-issue"))
        monkeypatch.setattr(land.done_work, "_invoke_close_issue", verb("close-issue"))
        monkeypatch.setattr(land.done_work.pr_merge, "delete_remote_branch", lambda *a, **k: None)
        monkeypatch.setattr(land.done_work.pr_merge, "cleanup_local", lambda *a, **k: None)
        return run

    return build


def _steps(out: str) -> list[str]:
    """The lines land-work prints for its steps."""
    return [line for line in out.splitlines() if line.split(":")[0] in _STEP_NAMES]


_STEP_NAMES = {"head", "ci", "review", "merge"}


def _short(oid: str) -> str:
    return oid[:7]


# ---- the happy path -----------------------------------------------------------


def test_green_checks_two_reviewers_and_a_merge_one_line_each(world, capsys) -> None:
    run = world()
    head = run.github.head
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert _steps(out) == [
        f"head: {_short(head)} (PR #{PR}, {BRANCH})",
        f"ci: passed on {_short(head)} (8m, run https://github.com/o/r/actions/runs/77)",
        "review: 0 kept fresh, 2 re-run — all approved",
        f"merge: merged as {'c' * 7}",
    ]
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"
    # Every reviewer was shown the pinned head, and the merge was pinned to it.
    assert run.invoked == [(name, head) for name in PANEL]
    subject = ["--subject", "feat(pm): land it"]
    assert run.github.merges == [
        ["pr", "merge", str(PR), "--squash", *subject, "--match-head-commit", head]
    ]
    assert run.after_merge == [f"move-issue #{ISSUE}", f"close-issue #{ISSUE}"]
    assert run.sleeps == []


# ---- the head -----------------------------------------------------------------


def test_an_unpushed_local_head_is_refused_with_the_push(world, capsys) -> None:
    run = world()
    run.commit("not-pushed.txt", push=False)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        f"head: refused — local {BRANCH} has 1 commit PR #{PR}'s head "
        f"{_short(run.github.head)} lacks. Push first: `git push origin {BRANCH}`"
    )
    # Nothing past the head was read, reviewed or merged.
    assert not any(c[:2] == ["pr", "view"] for c in run.github.calls)
    assert run.invoked == []
    assert run.github.merges == []


def test_a_local_branch_diverged_from_the_pr_is_refused(world, capsys) -> None:
    run = world()
    pushed = run.github.head
    _git(run.work, "reset", "-q", "--hard", "HEAD~1")
    run.commit("elsewhere.txt", push=False)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        f"head: refused — local {BRANCH} and PR #{PR}'s head {_short(pushed)} have "
        "diverged (1 commit only here, 1 commit only on the PR). Nothing was done"
    )


def test_a_local_branch_behind_the_pr_and_another_checkout_are_noted(world, capsys) -> None:
    """The PR moved on GitHub (a push from elsewhere) and this checkout is on
    main: land-work lands the PR's head and says so."""
    run = world()
    old = run.github.head
    run.push_new_head("from-elsewhere.txt")
    _git(run.work, "reset", "-q", "--hard", old)
    _git(run.work, "switch", "-q", "main")
    run.github.checks[run.github.head] = [_GREEN]
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert _steps(out)[0] == (
        f"head: {_short(run.github.head)} (PR #{PR}, {BRANCH}); local {BRANCH} is "
        f"1 commit behind it; this checkout is on main, not {BRANCH}"
    )


def test_a_draft_pr_is_refused(world, capsys) -> None:
    run = world()
    run.github.draft = True
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE == 1
    assert out.splitlines()[-1] == (
        f"head: refused — PR #{PR} is a draft; mark it ready with `review-work {ISSUE}`"
    )


# ---- the checks ---------------------------------------------------------------


def test_no_run_yet_is_waited_for_then_green_goes_on(world, capsys) -> None:
    run = world(checks=[[], [], _RUNNING, _GREEN])
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    head = _short(run.github.head)
    assert f"  ci: no check has been reported for {head} yet" in out
    assert f"  ci: running on {head}: checks (IN_PROGRESS)" in out
    assert run.sleeps == [20.0, 20.0, 20.0]
    assert _steps(out)[1].startswith(f"ci: passed on {head}")


def test_a_green_run_on_an_older_head_does_not_count(world, capsys) -> None:
    """The previous head's checks passed; the new head has no run yet. Land
    waits for the new head's — it never borrows the old head's green."""
    run = world()
    old = run.github.head
    new = run.push_new_head("fix.txt")
    run.github.checks[new] = [[], _GREEN]
    assert run.github.checks[old] == [_GREEN]
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert f"  ci: no check has been reported for {_short(new)} yet" in out
    assert run.sleeps == [20.0]
    assert _steps(out)[1].startswith(f"ci: passed on {_short(new)}")
    assert run.invoked == [(name, new) for name in PANEL]


def test_a_failed_check_stops_before_the_review(world, capsys) -> None:
    run = world(checks=[_RED])
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        f"ci: failed on {_short(run.github.head)} — checks (FAILURE) "
        "https://github.com/o/r/actions/runs/78/job/2. Review and merge not started"
    )
    assert run.invoked == []
    assert run.github.comments == []
    assert run.github.merges == []


def test_the_wait_running_out_on_no_run_is_its_own_exit(world, capsys) -> None:
    run = world(checks=[[]])
    rc, out, _err = run.run("--yes", "--wait-minutes", "1", capsys=capsys)
    assert rc == run.land.EXIT_CI_PENDING == 5
    assert sum(run.sleeps) == 60
    last = out.splitlines()[-1]
    assert last.startswith(
        f"ci: no check has been reported for {_short(run.github.head)} after 1m: its run "
        "has not started, or none will — no workflow runs on pull requests here, the "
        "workflows skip the paths this PR changes, its head commit asks to skip CI "
        "([skip ci]), or a run from a fork awaits approval."
    )
    assert f"Run `land-work {ISSUE}` again to keep waiting" in last
    assert f"review it with `review-pr {ISSUE}` and merge it with `done-work {ISSUE}`" in last
    assert run.invoked == []


def test_no_wait_reads_the_checks_once(world, capsys) -> None:
    run = world(checks=[_RUNNING])
    rc, out, _err = run.run("--yes", "--no-wait", capsys=capsys)
    assert rc == 5
    assert run.sleeps == []
    assert out.splitlines()[-1] == (
        f"ci: still running on {_short(run.github.head)} (--no-wait): checks "
        f"(IN_PROGRESS). Run `land-work {ISSUE}` again to keep waiting"
    )


def test_a_head_that_moves_while_the_checks_are_awaited_stops(world, capsys) -> None:
    run = world(checks=[_RUNNING])
    pinned = run.github.head
    run.github.before(
        _nth(lambda a: a[:2] == ["pr", "view"] and "statusCheckRollup" in a[-1], 2),
        lambda: setattr(run.github, "head", "d" * 40),
    )
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 3
    assert out.splitlines()[-1] == (
        f"ci: stopped — PR #{PR}'s head moved from {_short(pinned)} to ddddddd while its "
        f"checks were awaited. Nothing was reviewed or merged; `land-work {ISSUE}` checks "
        "and reviews the new head"
    )


# ---- the review ---------------------------------------------------------------


def test_changes_requested_stops_before_the_merge_with_its_findings(world, capsys) -> None:
    run = world()
    run.answers["code-reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 1
    lines = out.splitlines()
    assert "  [code-reviewer] [block] `land.py:10` merges a head nobody reviewed." in lines
    assert "  [code-reviewer] **[block]** The exit code hides a refusal." in lines
    assert not any("[advisory]" in line for line in lines)
    assert lines[-1] == (
        "review: changes requested by code-reviewer — the blocking findings are above; "
        "merge not started"
    )
    assert run.github.merges == []


def test_a_fresh_changes_requested_kept_from_a_run_before_also_stops(world, capsys) -> None:
    """A re-run does not re-run a fresh CHANGES_REQUESTED, and does not merge
    past it either: its findings are read from the verdict it kept."""
    run = world()
    run.answers["code-reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    assert run.run("--yes", capsys=capsys)[0] == 1
    run.invoked.clear()
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 1
    assert run.invoked == []
    assert "  [code-reviewer] [block] `land.py:10` merges a head nobody reviewed." in out
    assert out.splitlines()[-1].startswith("review: changes requested by code-reviewer")


def test_changes_requested_without_a_tagged_finding_prints_its_first_lines(world, capsys) -> None:
    run = world()
    run.answers["reviewer"] = (
        "CHANGES_REQUESTED",
        "Please rework it.\n\nThe parser is wrong.\nSo is the printer.\nAnd the rest.",
    )
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 1
    lines = out.splitlines()
    first = lines.index("  [reviewer] Please rework it.")
    assert lines[first : first + 4] == [
        "  [reviewer] Please rework it.",
        "  [reviewer] The parser is wrong.",
        "  [reviewer] So is the printer.",
        f"  [reviewer] (no finding tagged blocking — read it all with `show-pr {PR} "
        "--field review`)",
    ]


def test_a_reviewer_that_could_not_run_stops_and_is_not_approval(world, capsys) -> None:
    run = world()
    run.answers["code-reviewer"] = None
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_REVIEW_INCOMPLETE == 6
    assert out.splitlines()[-1] == (
        "review: stopped — a reviewer could not be run, so the review is not complete "
        "(code-reviewer: the invocation failed, so there is no verdict to post). "
        f"Run `land-work {ISSUE}` again once it can run"
    )
    assert run.github.merges == []


def test_a_head_that_moves_between_the_checks_and_the_review_stops(world, capsys) -> None:
    """review-pr's own lookup — the second open-PR lookup — finds the PR moved:
    no reviewer is shown a head whose checks were not waited for."""
    run = world()
    pinned = run.github.head
    run.github.before(_nth(_pr_list, 2), lambda: run.push_new_head("late.txt"))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 3
    assert run.invoked == []
    assert out.splitlines()[-1] == (
        f"review: stopped — PR #{PR}'s head is {_short(run.github.head)}, not "
        f"{_short(pinned)}, the head whose checks passed. Nothing was merged; "
        f"`land-work {ISSUE}` checks and reviews the new head"
    )


def test_a_head_that_moves_between_the_review_and_the_merge_merges_nothing(world, capsys) -> None:
    """done-work's lookup — the third — finds the PR moved after the review:
    done-work refuses the pinned head it no longer has."""
    run = world()
    pinned = run.github.head
    run.github.before(_nth(_pr_list, 3), lambda: run.push_new_head("later.txt"))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 3
    assert run.github.merges == []
    assert out.splitlines()[-1] == (
        f"merge: stopped — error: PR #{PR}'s head is {_short(run.github.head)}, not "
        f"{_short(pinned)}, the head this run was asked to land: its checks and review "
        "were for that head. Nothing was posted or merged, and #42 stays where it is."
    )


def test_human_review_mode_runs_no_reviewer_and_done_work_gates(world, capsys) -> None:
    run = world(mode="human")
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 1
    assert run.invoked == []
    steps = _steps(out)
    assert steps[2] == (
        "review: human review mode (project default) — no reviewer agent to run; the "
        "approval is done-work's gate"
    )
    assert steps[3] == f"merge: refused — [refused] approval gate not satisfied for PR #{PR}."


# ---- the merge ----------------------------------------------------------------


def test_a_queued_pr_passes_done_works_4_through(world, capsys) -> None:
    run = world()
    run.github.queue = True
    rc, out, _err = run.run("--yes", "--no-wait", capsys=capsys)
    assert rc == 4
    assert run.github.merges == [
        ["pr", "merge", str(PR), "--auto", "--match-head-commit", run.github.head]
    ]
    assert out.splitlines()[-1] == (
        f"merge: queued — PR #{PR} position 1 in the queue, awaiting checks; run "
        f"`land-work {ISSUE}` again once it merges"
    )
    assert run.after_merge == []


def test_an_unconfirmed_merge_passes_done_works_4_through(world, capsys) -> None:
    run = world()
    run.github.unreadable_after_merge = True
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 4
    assert "[unconfirmed]" in out
    assert out.splitlines()[-1] == (
        f"merge: unconfirmed — whether PR #{PR} merged is not known; run `land-work {ISSUE}` "
        "again once it merges"
    )
    assert run.after_merge == []


def test_a_declined_prompt_is_not_reported_merged(world, capsys, monkeypatch) -> None:
    """At a terminal done-work's prompt is the authorisation. done-work exits 0
    when it is declined; land-work decides on how done-work's run ended, so it
    reports the PR not merged, with the not-authorised exit."""
    run = world()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY == 8
    assert out.splitlines()[-1] == (
        f"merge: declined — PR #{PR} at {_short(run.github.head)} was not merged"
    )
    assert run.github.merges == []


# ---- a re-run resumes ---------------------------------------------------------


def test_a_rerun_after_the_wait_ran_out_goes_on(world, capsys) -> None:
    run = world(checks=[[], [], _GREEN])
    assert run.run("--yes", "--no-wait", capsys=capsys)[0] == 5
    rc, out, err = run.run("--yes", "--no-wait", capsys=capsys)
    assert rc == 5  # the second reading: still no run
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert run.sleeps == []


def test_a_rerun_waits_for_nothing_and_re_runs_no_fresh_verdict(world, capsys) -> None:
    """A reviewer could not run: the re-run keeps the verdict the other posted,
    runs only the missing one, and waits for no check already green."""
    run = world()
    run.answers["code-reviewer"] = None
    assert run.run("--yes", capsys=capsys)[0] == 6
    assert run.invoked == [(name, run.github.head) for name in PANEL]
    run.invoked.clear()
    del run.answers["code-reviewer"]
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert run.invoked == [("code-reviewer", run.github.head)]
    assert "review: 1 kept fresh, 1 re-run — all approved" in _steps(out)
    assert run.sleeps == []


def test_a_rerun_after_changes_requested_reviews_the_fix(world, capsys) -> None:
    run = world()
    run.answers["code-reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    assert run.run("--yes", capsys=capsys)[0] == 1
    fixed = run.push_new_head("fix.txt")
    run.github.checks[fixed] = [_GREEN]
    run.answers["code-reviewer"] = ("APPROVED", "Fixed.")
    run.invoked.clear()
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    # A change since makes both verdicts stale: both review the fix.
    assert run.invoked == [(name, fixed) for name in PANEL]
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"


def test_a_rerun_after_the_head_moved_lands_the_new_head(world, capsys) -> None:
    run = world()
    run.github.before(_nth(_pr_list, 2), lambda: run.push_new_head("late.txt"))
    assert run.run("--yes", capsys=capsys)[0] == 3
    run.github.checks[run.github.head] = [_GREEN]
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert run.invoked == [(name, run.github.head) for name in PANEL]


def test_a_rerun_after_the_queue_merged_completes_the_issue(world, capsys) -> None:
    run = world()
    run.github.queue = True
    assert run.run("--yes", "--no-wait", capsys=capsys)[0] == 4
    run.github.state = "MERGED"
    run.github.queued = False
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert _steps(out) == [
        f"head: no open PR for {BRANCH} — done-work completes a PR that has merged already",
        f"merge: #{ISSUE} completed through its merged PR",
    ]
    assert run.after_merge == [f"move-issue #{ISSUE}", f"close-issue #{ISSUE}"]


# ---- a dry run ----------------------------------------------------------------


def test_a_dry_run_says_what_each_step_would_do_and_does_none(world, capsys) -> None:
    run = world(checks=[_RUNNING])
    rc, out, err = run.run("--dry-run", capsys=capsys)
    assert rc == 0, out + err
    head = _short(run.github.head)
    assert _steps(out) == [
        f"head: {head} (PR #{PR}, {BRANCH})",
        f"ci: (dry-run) running on {head}: checks (IN_PROGRESS) — would wait up to 30m",
        "review: (dry-run) would keep 0 fresh and run reviewer, code-reviewer",
        f"merge: (dry-run) would hand PR #{PR} at {head} to done-work once the checks pass "
        "and the review approves",
    ]
    assert run.invoked == []
    assert run.github.comments == []
    assert run.github.merges == []
    assert run.sleeps == []


def test_a_dry_run_with_nothing_left_to_wait_for_shows_done_works_plan(world, capsys) -> None:
    run = world()
    assert run.run("--yes", "--no-wait", capsys=capsys)[0] == 0
    run.github.state = "OPEN"  # as if the merge had not happened: replay it dry
    run.github.merges.clear()
    rc, out, err = run.run("--dry-run", capsys=capsys)
    assert rc == 0, out + err
    assert "(dry-run: would post bypass audit (if any)" in out
    assert out.splitlines()[-1] == "merge: (dry-run) done-work's plan is above"
    assert run.github.merges == []


# ---- lookups that get no answer -----------------------------------------------
# "gh did not answer" is never "no open PR": a run that read it so handed over
# with no pinned head, and done-work, finding the PR on its own lookup, merged
# it on its own gates — with no CI wait and no review.


def test_an_open_pr_lookup_gh_does_not_answer_stops_with_nothing_done(world, capsys) -> None:
    run = world()
    run.github.fails.append(_nth(_pr_list, 1))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE == 2
    assert out.splitlines()[-1] == (
        f"head: whether {BRANCH} has an open PR could not be read: HTTP 502: Bad Gateway. "
        f"Nothing was done; run `land-work {ISSUE}` again once gh answers"
    )
    # done-work never ran: its own lookup would have found the PR.
    assert sum(1 for call in run.github.calls if _pr_list(call)) == 1
    assert run.github.merges == []
    assert run.invoked == []
    assert run.after_merge == []


def test_a_lookup_that_fails_then_answers_never_merges_unpinned(world, capsys) -> None:
    run = world()
    run.github.fails.append(_nth(_pr_list, 1))
    assert run.run("--yes", capsys=capsys)[0] == 2
    assert run.github.merges == []
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    head = run.github.head
    assert run.invoked == [(name, head) for name in PANEL]
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_done_works_own_lookup_without_an_answer_merges_nothing(world, capsys) -> None:
    """land-work, then review-pr, found the PR; done-work's lookup — the third
    — gets no answer, and done-work stops rather than look for a merged PR."""
    run = world()
    run.github.fails.append(_nth(_pr_list, 3))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 2
    assert out.splitlines()[-1] == (
        f"merge: stopped — error: whether '{BRANCH}' has an open PR could not be read: "
        "HTTP 502: Bad Gateway. Nothing was changed."
    )
    assert run.github.merges == []
    assert run.after_merge == []


def test_with_no_open_pr_done_work_only_completes_and_refuses_a_pr_that_opened(
    world, capsys
) -> None:
    """land-work's lookup answers "none open", so it hands over only to complete
    a merged PR; by done-work's lookup the PR is open — one nobody checked or
    reviewed — and nothing is merged. A re-run pins it and lands it."""
    run = world()
    run.github.state = "CLOSED"
    run.github.before(_nth(_pr_list, 2), lambda: setattr(run.github, "state", "OPEN"))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_RETRY == 7
    assert out.splitlines()[-1] == (
        f"merge: not completed — error: PR #{PR} for '{BRANCH}' is open, and this run was "
        "asked only to complete a PR that has merged. Nothing was changed. Run "
        f"`land-work {ISSUE}` again to check, review and land it"
    )
    assert run.github.merges == []
    assert run.after_merge == []
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err


# ---- how done-work's run ended, not its exit code -----------------------------


def test_a_merge_whose_commit_cannot_be_read_is_still_merged(world, capsys) -> None:
    """done-work's run says merged only once GitHub reports it merged; the
    merge commit is only what the line names."""
    run = world()
    run.github.fails.append(lambda a: a[:2] == ["pr", "view"] and a[-1] == "mergeCommit")
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert out.splitlines()[-1] == "merge: merged"


def test_completing_a_merged_pr_declined_is_not_reported_completed(
    world, capsys, monkeypatch
) -> None:
    run = world()
    run.github.state = "MERGED"
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert out.splitlines()[-1] == f"merge: declined — #{ISSUE}'s merged PR was not completed"
    assert run.after_merge == []


def test_a_step_after_the_merge_failing_is_merged_and_owed(world, capsys, monkeypatch) -> None:
    """The PR merged and the move to Done failed: not a refusal to hand back,
    a completion a re-run owes."""
    run = world()
    monkeypatch.setattr(run.land.done_work, "_invoke_move_issue", lambda *a, **k: 1)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_RETRY == 7
    assert out.splitlines()[-1] == (
        f"merge: merged as {'c' * 7}, but a step after the merge failed: [warn] PR merged "
        f"but move-issue exited 1. The merge is durable; re-run `move-issue {ISSUE} --to done` "
        f"to complete the lifecycle transition. — run `land-work {ISSUE}` again to complete "
        f"#{ISSUE}"
    )
    monkeypatch.setattr(run.land.done_work, "_invoke_move_issue", lambda *a, **k: 0)
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert out.splitlines()[-1] == f"merge: #{ISSUE} completed through its merged PR"


def _then(run: _Run, monkeypatch: pytest.MonkeyPatch, after: Callable[[], None]) -> None:
    """Run `after` once done-work's run has returned."""
    original = run.land.done_work.run

    def run_then(argv: list[str], **kwargs: Any) -> Any:
        end = original(argv, **kwargs)
        after()
        return end

    monkeypatch.setattr(run.land.done_work, "run", run_then)


def test_a_queued_pr_seen_merged_meanwhile_is_owed_its_completion(
    world, capsys, monkeypatch
) -> None:
    run = world()
    run.github.queue = True

    def merged() -> None:
        run.github.state, run.github.queued = "MERGED", False

    _then(run, monkeypatch, merged)
    rc, out, _err = run.run("--yes", "--no-wait", capsys=capsys)
    assert rc == run.land.EXIT_RETRY
    assert out.splitlines()[-1] == (
        f"merge: merged meanwhile — run `land-work {ISSUE}` again to complete #{ISSUE}"
    )


def test_a_queued_pr_seen_neither_merged_nor_queued_is_known_not_merged(
    world, capsys, monkeypatch
) -> None:
    """The reading succeeded and shows the PR neither merged nor queued: that
    is known — not merged — not "unconfirmed"."""
    run = world()
    run.github.queue = True
    _then(run, monkeypatch, lambda: setattr(run.github, "queued", False))
    rc, out, _err = run.run("--yes", "--no-wait", capsys=capsys)
    assert rc == run.land.EXIT_RETRY
    last = out.splitlines()[-1]
    assert last.startswith(
        f"merge: not merged — PR #{PR} is neither merged nor in the merge queue ("
    )
    assert last.endswith(f"); run `land-work {ISSUE}` again to merge it")


def test_done_work_raising_still_ends_with_a_step_line(world, capsys, monkeypatch) -> None:
    run = world()

    def boom(argv: list[str], **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(run.land.done_work, "run", boom)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_RETRY
    assert out.splitlines()[-1] == (
        f"merge: not merged — done-work failed (RuntimeError: boom). Run `land-work {ISSUE}` again"
    )


def test_review_pr_raising_still_ends_with_a_step_line(world, capsys, monkeypatch) -> None:
    run = world()

    def boom(argv: list[str], **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(run.land.review_pr, "review", boom)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_REVIEW_INCOMPLETE
    assert out.splitlines()[-1] == (
        "review: stopped — review-pr failed (RuntimeError: boom), so the review is not "
        f"complete. Run `land-work {ISSUE}` again once it can run"
    )
    assert run.github.merges == []


# ---- a head that moves --------------------------------------------------------


def test_a_head_that_moves_during_a_review_stops_after_that_review(world, capsys) -> None:
    """The first reviewer's verdict is the pinned head's and is posted; no
    further reviewer is shown a head that moved, and nothing merges."""
    run = world()
    pinned = run.github.head

    def tips(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1] == "headRefOid,baseRefOid"

    run.github.before(_nth(tips, 2), lambda: run.push_new_head("during.txt"))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert run.invoked == [(PANEL[0], pinned)]
    assert f"sha={pinned}" in run.github.comments[0]["body"]
    assert run.github.merges == []
    assert out.splitlines()[-1] == (
        f"review: stopped — PR #{PR}'s head is {_short(run.github.head)}, not "
        f"{_short(pinned)}, the head whose checks passed. Nothing was merged; "
        f"`land-work {ISSUE}` checks and reviews the new head"
    )


def test_verdicts_kept_fresh_at_another_head_are_not_the_pinned_heads(world, capsys) -> None:
    """Every verdict would be kept, so no reviewer reads the head; the verdicts
    were read at a head that moved after the checks, so none is kept."""
    run = world()
    assert run.run(capsys=capsys)[0] == run.land.EXIT_READY
    run.invoked.clear()

    def verdict_read(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1].startswith("comments,")

    run.github.before(verdict_read, lambda: run.push_new_head("late.txt"))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert run.invoked == []
    assert run.github.merges == []
    assert out.splitlines()[-1].startswith(
        f"review: stopped — PR #{PR}'s head is {_short(run.github.head)}, not "
    )


def test_a_head_that_moves_before_done_works_gate_reads_it_merges_nothing(world, capsys) -> None:
    """The gate read another head than the pinned one: its verdict — here a
    refusal, the verdicts being stale for that head — is not the pinned
    head's, so the run reports the move, not a refusal."""
    run = world()
    pinned = run.github.head

    def gate_read(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1].startswith("author,comments")

    run.github.before(gate_read, lambda: run.push_new_head("racing.txt"))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert run.github.merges == []
    assert out.splitlines()[-1] == (
        f"merge: stopped — error: PR #{PR}'s head is {_short(run.github.head)}, not "
        f"{_short(pinned)}, the head this run was asked to land: its checks and review "
        f"were for that head. Nothing was posted or merged, and #{ISSUE} stays where it is."
    )


def test_a_head_that_moves_between_the_gate_and_the_merge_request_merges_nothing(
    world, capsys
) -> None:
    """The merge request is pinned to the head: GitHub refuses it, and
    land-work reads the PR to say why — its head moved."""
    run = world()
    pinned = run.github.head

    def rollup_read(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1] == "statusCheckRollup"

    run.github.before(rollup_read, lambda: run.push_new_head("racing.txt"))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert run.github.state == "OPEN"
    assert [merge[-1] for merge in run.github.merges] == [pinned]
    assert out.splitlines()[-1] == (
        f"merge: stopped — PR #{PR}'s head moved from {_short(pinned)} to "
        f"{_short(run.github.head)} before the merge. Nothing was merged; "
        f"`land-work {ISSUE}` checks and reviews the new head"
    )


def test_a_head_review_pr_cannot_read_stops_unreadable_not_moved(world, capsys) -> None:
    run = world()
    head = run.github.head
    run.github.fails.append(lambda a: a[:2] == ["pr", "view"] and a[-1] == "headRefOid,baseRefOid")
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    assert run.invoked == []
    assert out.splitlines()[-1] == (
        f"review: stopped — PR #{PR}'s head could not be read before reviewer's review, so "
        f"whether it is {_short(head)}, the head this review was asked to review, cannot "
        "be told"
    )


# ---- what no run starts on, and checks that cannot be read --------------------


def test_a_pr_that_conflicts_with_its_base_stops_at_once(world, capsys) -> None:
    """GitHub runs no pull_request workflow on a PR that conflicts with its
    base: there is nothing to wait for."""
    run = world(checks=[[]])
    run.github.mergeable = "CONFLICTING"
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert run.sleeps == []
    assert out.splitlines()[-1] == (
        f"ci: stopped — PR #{PR} conflicts with main, and GitHub runs no pull_request "
        f"workflow on a PR that conflicts with its base. Merge main into {BRANCH} "
        f"(`git merge origin/main`), resolve the conflicts, push, and run "
        f"`land-work {ISSUE}` again"
    )


def test_checks_that_cannot_be_read_stop_unreadable(world, capsys) -> None:
    run = world()
    run.github.fails.append(lambda a: a[:2] == ["pr", "view"] and "statusCheckRollup" in a[-1])
    rc, out, _err = run.run("--yes", "--no-wait", capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    assert out.splitlines()[-1] == (
        f"ci: PR #{PR}'s checks could not be read: HTTP 502: Bad Gateway. Run "
        f"`land-work {ISSUE}` again"
    )
    assert run.invoked == []


def test_checks_unreadable_once_are_read_again_while_waiting(world, capsys) -> None:
    run = world()
    run.github.fails.append(lambda a: a[:2] == ["pr", "view"] and "statusCheckRollup" in a[-1])
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert "  ci: the checks could not be read: HTTP 502: Bad Gateway" in out
    assert run.sleeps == [20.0]


# ---- the review's findings ----------------------------------------------------


def test_a_block_is_reported_even_when_another_reviewer_could_not_run(world, capsys) -> None:
    run = world()
    run.answers["reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    run.answers["code-reviewer"] = None
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert "  [reviewer] [block] `land.py:10` merges a head nobody reviewed." in out
    assert out.splitlines()[-1] == (
        "review: changes requested by reviewer — the blocking findings are above; merge not started"
    )


def test_pm_reviewers_severities_are_blocking_findings(world, capsys) -> None:
    run = world()
    run.answers["reviewer"] = (
        "CHANGES_REQUESTED",
        "Findings:\n\n"
        "- **hard-reject**: the title is not a conventional commit.\n"
        "- `bypassable-with-audit` — the changeset has no audit comment.\n"
        "- warning: the body is long.\n",
    )
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert "  [reviewer] **hard-reject**: the title is not a conventional commit." in out
    assert "  [reviewer] `bypassable-with-audit` — the changeset has no audit comment." in out
    assert "the body is long" not in out


def test_the_advisories_of_approvals_are_printed_in_the_review_step(world, capsys) -> None:
    run = world()
    run.answers["code-reviewer"] = (
        "APPROVED",
        "Fine.\n\n- [advisory] A name could be clearer.\n"
        "- [advisory] (pre-existing: older code) A loop is slow.\n",
    )
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert "  [code-reviewer] [advisory] A name could be clearer." in out
    assert "  [code-reviewer] [advisory] (pre-existing: older code) A loop is slow." in out
    assert _steps(out)[2] == (
        "review: 0 kept fresh, 2 re-run — all approved; 2 advisories above (every "
        f"verdict in full: `show-pr {PR} --field review`)"
    )


# ---- the authorisation --------------------------------------------------------


def test_without_yes_it_stops_ready_and_merges_nothing(world, capsys) -> None:
    """Off a terminal, no `--yes` is no authorisation: the checks, the review and
    done-work's gates run, and the run stops naming the head and the command
    that merges it. That authorisation then merges with nothing re-reviewed."""
    run = world()
    head = run.github.head
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY == 8
    assert out.splitlines()[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved; merge with: "
        f"pkit pm land-work {ISSUE} --yes --expect-head {head}"
    )
    assert run.github.merges == []
    assert run.after_merge == []
    assert run.invoked == [(name, head) for name in PANEL]
    run.invoked.clear()
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert run.invoked == []
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_ready_runs_done_works_gates_and_reports_their_refusal(world, capsys) -> None:
    """Human review mode, no approval: `ready` is never said of a PR done-work
    would refuse."""
    run = world(mode="human")
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"merge: refused — [refused] approval gate not satisfied for PR #{PR}."
    )
    assert run.github.merges == []


def test_an_authorisation_for_another_head_stops_before_anything(world, capsys) -> None:
    run = world()
    authorised = run.github.head
    run.push_new_head("after.txt")
    rc, out, _err = run.run("--yes", "--expect-head", authorised[:12], capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert out.splitlines()[-1] == (
        f"head: stopped — PR #{PR}'s head is {_short(run.github.head)}, not "
        f"{authorised[:7]}, the head the merge was authorised for: an authorisation is "
        f"for one head. Nothing was done; `land-work {ISSUE}` checks and reviews the new one"
    )
    assert not any(call[:2] == ["pr", "view"] for call in run.github.calls)
    assert run.github.merges == []
    assert run.invoked == []


def test_expect_head_takes_a_commit_id_only(land) -> None:
    with pytest.raises(SystemExit):
        land._parser().parse_args([str(ISSUE), "--expect-head", "not-a-sha"])
