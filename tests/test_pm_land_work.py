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

from tests import pm_issue_branch_support as issue_branch_support
from tests import pull_request_backbone
from tests.adopter_repo import sign_nothing

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
    #: The PR's description, and each one written to it.
    body: str = _PR_BODY
    bodies: list[str] = field(default_factory=list)
    #: The branch the PR merges into.
    base_branch: str = "main"
    #: The PR's author as GitHub returns it; None for one it returns as null.
    author: dict[str, Any] | None = field(default_factory=lambda: {"login": "author"})
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
        if argv[:2] == ["pr", "edit"]:
            self.body = Path(_option(argv, "--body-file") or "").read_text(encoding="utf-8")
            self.bodies.append(self.body)
            return _done(argv)
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
        if issue_branch_support.is_open_prs_reading(argv):
            # The open PRs of several local branches matching the issue (#1608).
            open_on = {BRANCH: [PR]} if self.state == "OPEN" else {}
            return _done(argv, issue_branch_support.answer(argv, open_on))
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
            "baseRefName": self.base_branch,
            "baseRefOid": self.base,
            "state": self.state,
            "mergeable": self.mergeable,
            "isCrossRepository": False,
            "mergedAt": "2026-10-01T12:00:00Z" if merged else None,
            "author": self.author,
            "body": self.body,
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
    #: Each reviewer invocation: (reviewer, the head it was shown), in no order:
    #: the reviewers run at once (#1594).
    invoked: list[tuple[str, str]] = field(default_factory=list)
    #: What each reviewer answers: (verdict, body), or None for a failed run.
    answers: dict[str, tuple[str, str] | None] = field(default_factory=dict)
    after_merge: list[str] = field(default_factory=list)
    sleeps: list[float] = field(default_factory=list)
    #: The change check at the head: the answers the change wrote (entries of
    #: its `answers`), the friction settings it alters, whether the base moved
    #: on and to which commit, the head's unreadable files — or why it could
    #: not be read.
    written: list[dict[str, Any]] = field(default_factory=list)
    settings: list[Any] = field(default_factory=list)
    outdated: bool = False
    tip: str = ""
    unreadable: list[str] = field(default_factory=list)
    unread: str | None = None
    #: Each (head, base) the list was derived for.
    derived: list[tuple[str, str | None]] = field(default_factory=list)
    merge_base: str = ""
    #: The backbone's answer on whether the authorisation for an earlier head covers
    #: the PR's head (`friction_answers.covers`): covered, or why it cannot answer —
    #: and each (since, head, base) it was asked about.
    cover: bool = False
    cover_problem: str | None = None
    asked_cover: list[tuple[str, str, str]] = field(default_factory=list)

    def covers(self, since: str, head: str, base: str) -> Any:
        """`friction_answers.covers`, answered from this world."""
        self.asked_cover.append((since, head, base))
        fa = self.land.friction_answers
        if self.cover_problem is not None:
            return fa.Coverage(problem=self.cover_problem)
        full = _git(self.work, "rev-parse", since)
        if self.cover:
            return fa.Coverage(full, head, True, inside=1)
        return fa.Coverage(full, head, False, outside=(f"after.txt ({head[:7]}: added)",))

    def derive(self, head: str, base: str | None) -> Any:
        """`friction_answers.derive`, answered from this world's change check."""
        self.derived.append((head, base))
        fa = self.land.friction_answers
        if self.unread is not None:
            return fa.Derivation(head, problem=self.unread)
        document = {
            "schema_version": 1,
            "base": {
                "commit": self.merge_base,
                "tip": self.tip or self.merge_base,
                "outdated": self.outdated,
            },
            "findings": [],
            "answers": self.written,
            "unreadable": self.unreadable,
        }
        return fa.Derivation(
            head, document=document, answers=tuple(self.written), settings=tuple(self.settings)
        )

    def section(self) -> str:
        """The list the description carries for the current head."""
        derived = self.derive(self.github.head, None)
        self.derived.pop()
        section = self.land.friction_answers.render(
            derived.document, self.github.head, derived.settings
        )
        assert section is not None
        return section

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


def _stage_project(work: Path, *, mode: str, remote: tuple[str, ...] = ()) -> Path:
    capability = work / ".pkit" / "capabilities" / "project-management"
    project = capability / "project"
    project.mkdir(parents=True)
    shutil.copytree(CAPABILITY / "schemas", capability / "schemas")
    shutil.copytree(CAPABILITY / "templates", capability / "templates")
    reviewers = "".join(f"      - name: {name}\n" for name in PANEL)
    remotes = "".join(f"      - github_login: {login}\n" for login in remote)
    (project / "config.yaml").write_text(
        "schema_version: 1\n"
        "default_branch: main\n"
        "workstreams: []\n"
        "review:\n"
        f"  mode: {mode}\n"
        "  agents:\n"
        + (f"    remote_registered:\n{remotes}" if remote else "")
        + "    local_registered:\n"
        + reviewers,
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
    sign_nothing(work)  # each test's copy keeps it, so no commit in a copy is signed either
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
    def build(
        *,
        mode: str = "agent",
        checks: list[list[dict[str, Any]]] | None = None,
        remote: tuple[str, ...] = (),
    ) -> _Run:
        shutil.copytree(clone.root, tmp_path / "clone", symlinks=True)
        work = tmp_path / "clone" / "work"
        _stage_project(work, mode=mode, remote=remote)
        monkeypatch.chdir(work)
        monkeypatch.setenv("PM_INVOKER_LOGIN", "octocat")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        github = _FakeGitHub(mq=land.merge_queue, head=clone.head, base=clone.base)
        run = _Run(land=land, work=work, github=github, merge_base=clone.base)
        github.checks[github.head] = checks if checks is not None else [_GREEN]
        monkeypatch.setattr(land.friction_answers, "derive", run.derive)
        monkeypatch.setattr(land.friction_answers, "covers", run.covers)
        # The backbone's reading, stood in for: the default branch `main` (COR-054).
        settled = land.friction_answers.default_branch
        monkeypatch.setattr(settled, "_read", {})

        def ask(explicit: str | None, _run: Any) -> Any:
            branch = settled.Branch("main", False, "origin/main", clone.base, None)
            return settled.Reading(branch, settled.Base("origin/main", clone.base, None, None))

        monkeypatch.setattr(settled, "_ask", ask)

        gh_module = sys.modules["_lib.gh"]
        for module in (gh_module, land, land.done_work, land.review_pr, land.issue_branch):
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
        monkeypatch.setattr(land.done_work.pr_merge, "delete_branch", lambda *a, **k: None)
        monkeypatch.setattr(land.done_work.pr_merge, "cleanup_local", lambda *a, **k: None)
        return run

    return build


def _steps(out: str) -> list[str]:
    """The lines land-work prints for its steps."""
    return [line for line in out.splitlines() if line.split(":")[0] in _STEP_NAMES]


#: How the line of the step that lists the answers begins (land-work's `STEP`).
_STEP = "documents this change affects"
#: How the line of the step that prints the `[person]` findings begins (`FINDINGS`).
_FINDINGS = "findings to judge"
_STEP_NAMES = {"head", "ci", "review", _STEP, _FINDINGS, "merge"}
#: The description's section of the answers, and the heading an earlier run wrote it under.
_HEADING = "## Documentation this change affects"
_FORMER_HEADING = "## Friction answers"


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
        f"{_STEP}: none",
        f"merge: merged as {'c' * 7}",
    ]
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"
    # The list was derived at the pinned head against the PR's base, named, and a
    # change that wrote no answers leaves the description as it was.
    assert run.derived == [(head, "main")]
    assert run.github.bodies == []
    # Every reviewer was shown the pinned head, and the merge was pinned to it.
    assert sorted(run.invoked) == sorted((name, head) for name in PANEL)
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
    assert sorted(run.invoked) == sorted((name, new) for name in PANEL)


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
    assert steps[4] == f"merge: refused — [refused] approval gate not satisfied for PR #{PR}."


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
    assert sorted(run.invoked) == sorted((name, run.github.head) for name in PANEL)
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
    assert sorted(run.invoked) == sorted((name, fixed) for name in PANEL)
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"


def test_a_rerun_after_the_head_moved_lands_the_new_head(world, capsys) -> None:
    run = world()
    run.github.before(_nth(_pr_list, 2), lambda: run.push_new_head("late.txt"))
    assert run.run("--yes", capsys=capsys)[0] == 3
    run.github.checks[run.github.head] = [_GREEN]
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert sorted(run.invoked) == sorted((name, run.github.head) for name in PANEL)


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


# ---- the issue's branch among several (#1608) --------------------------------

#: A branch an earlier attempt left behind. It sorts before the PR's branch, so
#: the first match in git's order was the stale one.
_STALE = f"feat/{ISSUE}-a-stopped-attempt"


def _open_pr_readings(run: _Run) -> int:
    """How many times the open PRs of several branches were read."""
    return sum(1 for call in run.github.calls if issue_branch_support.is_open_prs_reading(call))


def test_a_stale_branch_does_not_take_the_place_of_the_pr_s(world, capsys) -> None:
    run = world()
    _git(run.work, "branch", _STALE, "main")
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert _steps(out)[0] == f"head: {_short(run.github.head)} (PR #{PR}, {BRANCH})"
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"
    # Read once for the run: review-pr and done-work are handed land-work's reading.
    assert _open_pr_readings(run) == 1


def test_several_branches_none_open_completes_a_merged_pr_from_the_issue(world, capsys) -> None:
    run = world()
    _git(run.work, "branch", _STALE, "main")
    run.github.state = "MERGED"
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert _steps(out) == [
        f"head: no open PR on any of {_STALE}, {BRANCH} — done-work completes a PR that "
        "has merged already",
        f"merge: #{ISSUE} completed through its merged PR",
    ]
    assert run.after_merge == [f"move-issue #{ISSUE}", f"close-issue #{ISSUE}"]
    assert _open_pr_readings(run) == 1


def test_several_branches_gh_unanswered_stops_before_anything(world, capsys) -> None:
    run = world()
    _git(run.work, "branch", _STALE, "main")
    run.github.fails.append(issue_branch_support.is_open_prs_reading)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 2
    assert f"  2 local branches match `*/{ISSUE}-*` ({_STALE}, {BRANCH})" in out
    assert "could not be read: HTTP 502: Bad Gateway" in out
    assert out.splitlines()[-1] == (
        f"head: stopped — which local branch is #{ISSUE}'s cannot be told (above). Nothing was done"
    )
    assert run.invoked == []
    assert run.github.merges == []


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
        f"{_STEP}: none",
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
    assert sorted(run.invoked) == sorted((name, head) for name in PANEL)
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


def test_an_unconfirmed_merge_seen_neither_merged_nor_queued_stays_unconfirmed(
    world, capsys, monkeypatch
) -> None:
    """Whether the merge was made is not known, and one reading of neither does
    not settle it — the request may still show (#1256): it stays unconfirmed,
    exit 4, naming the reading that tells, never "not merged"."""
    run = world()
    run.github.unreadable_after_merge = True
    _then(run, monkeypatch, lambda: setattr(run.github, "unreadable_after_merge", False))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == 4
    assert out.splitlines()[-1] == (
        f"merge: unconfirmed — PR #{PR} reads neither merged nor queued (not in the queue), "
        f"which does not tell whether the request was made; read it with `pkit pull-request "
        f"read {PR}`, and run `land-work {ISSUE}` again: it merges the PR if it has not merged"
    )
    assert run.after_merge == []


def test_done_work_raising_still_ends_with_a_step_line(world, capsys, monkeypatch) -> None:
    run = world()

    def boom(argv: list[str], **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(run.land.done_work, "run", boom)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_RETRY
    # One reading after done-work raised says what it found, never "not merged":
    # a request done-work sent may still show, and the re-run reads it first.
    assert out.splitlines()[-1] == (
        f"merge: not seen merged — done-work failed (RuntimeError: boom), and one reading since "
        f"finds PR #{PR} open. Run `land-work {ISSUE}` again: it reads the PR first, and "
        "completes it if it has merged"
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


def test_a_head_that_moves_during_the_reviews_posts_their_verdicts_and_stops(world, capsys) -> None:
    """The reviewers ran at once on the pinned head (#1594), and the PR moved
    while they ran: each verdict is the pinned head's and is posted, and
    nothing merges."""
    run = world()
    pinned = run.github.head

    def tips(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1] == "headRefOid,baseRefOid"

    run.github.before(_nth(tips, 2), lambda: run.push_new_head("during.txt"))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert sorted(run.invoked) == sorted((name, pinned) for name in PANEL)
    assert len(run.github.comments) == len(PANEL)
    assert all(f"sha={pinned}" in comment["body"] for comment in run.github.comments)
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
        f"review: stopped — PR #{PR}'s head could not be read before the reviews, so "
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
    assert sorted(run.invoked) == sorted((name, head) for name in PANEL)
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
    """A head whose changes since the authorised one lie outside `revalidated` blocks
    is a head nobody authorised: the run stops, naming the changes (DEC-055 point 3)."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("after.txt")
    rc, out, _err = run.run("--yes", "--expect-head", authorised[:12], capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert out.splitlines()[-1] == (
        f"head: stopped — PR #{PR}'s head is {_short(head)}, not "
        f"{authorised[:7]}, the head the merge was authorised for: an authorisation covers a "
        "later head only where every change since lies inside `revalidated` blocks, a clean "
        f"merge of main counting as none, and these changes do not: after.txt ({head[:7]}: "
        "added). "
        f"Nothing was done; `land-work {ISSUE}` checks and reviews the new one"
    )
    assert run.asked_cover == [(authorised[:12], head, "main")]
    assert not any(call[:2] == ["pr", "view"] for call in run.github.calls)
    assert run.github.merges == []
    assert run.invoked == []


def test_an_authorisation_whose_cover_cannot_be_told_stops_before_anything(world, capsys) -> None:
    """The backbone cannot answer: never read as covered."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("after.txt")
    run.cover_problem = "`pkit friction since …`: it exited 1: Error: this clone is shallow"
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert out.splitlines()[-1] == (
        f"head: stopped — PR #{PR}'s head is {_short(head)}, not {authorised[:7]}, the head "
        "the merge was authorised for, and whether that authorisation covers it could not be "
        f"told: {run.cover_problem}. Nothing was done; `land-work {ISSUE}` checks and reviews "
        "the new one"
    )
    assert run.github.merges == [] and run.invoked == []


def test_an_answer_for_another_pair_of_heads_is_no_answer(world, capsys, monkeypatch) -> None:
    """The backbone's answer is taken only for the two heads it was asked about."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("answers.txt")
    fa = run.land.friction_answers
    monkeypatch.setattr(
        fa, "covers", lambda since, h, base: fa.Coverage(authorised, "f" * 40, True)
    )
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert (
        f"whether that authorisation covers it could not be told: the backbone answered for "
        f"{authorised[:7]} to fffffff, not {authorised[:7]} to {_short(head)}"
    ) in out.splitlines()[-1]
    assert run.github.merges == []


def test_a_later_head_whose_base_cannot_be_read_stops_before_anything(world, capsys) -> None:
    run = world()
    authorised = run.github.head
    run.push_new_head("answers.txt")
    run.github.base_branch = ""
    run.cover = True
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert "its base branch could not be read" in out.splitlines()[-1]
    assert run.asked_cover == [] and run.github.merges == []


#: How the head step and the merge step say an earlier head's authorisation covers it.
def _covered(authorised: str) -> str:
    return (
        f"the authorisation for {_short(authorised)} covers it, since every change after "
        f"{_short(authorised)} lies inside `revalidated` blocks, a clean merge of main "
        "counting as none"
    )


def test_an_authorisation_covers_a_later_head_of_re_resolved_answers(world, capsys) -> None:
    """Every change since the authorised head lies inside `revalidated` blocks: the run
    goes on at the later head — its checks, its review — and merges it, saying which
    head it merged and why the authorisation covered it (DEC-055 point 3)."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("answers.txt")
    run.github.checks[head] = [_GREEN]
    run.cover = True
    rc, out, err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == 0, out + err
    steps = _steps(out)
    assert steps[0] == f"head: {_short(head)} (PR #{PR}, {BRANCH}); {_covered(authorised)}"
    assert steps[-1] == f"merge: merged as {'c' * 7}, at {_short(head)} — {_covered(authorised)}"
    assert [merge[-1] for merge in run.github.merges] == [head]
    # The reviewers judged the later head, not the one authorised.
    assert sorted(run.invoked) == sorted((name, head) for name in PANEL)
    assert run.derived == [(head, "main")]


def test_a_covered_head_whose_checks_fail_merges_nothing(world, capsys) -> None:
    """The run at the later head passes as any run must: a failed check stops it."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("answers.txt")
    run.github.checks[head] = [_RED]
    run.cover = True
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1].startswith(f"ci: failed on {_short(head)}")
    assert run.github.merges == []


def test_a_covered_head_with_a_finding_to_judge_stops_ready(world, capsys) -> None:
    """A `[person]` finding at the later head needs the person, who was not shown it:
    the run stops ready on that head, though its verdict stood when the run started."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("answers.txt")
    run.github.checks[head] = [_GREEN]
    run.github.comments.append(_verdict(run, "code-reviewer", _PERSON, sha=head))
    run.github.comments.append(_verdict(run, "reviewer", "Looks right.", sha=head))
    run.cover = True
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 finding to judge "
        f"above; the authorisation for {_short(authorised)} covers {_short(head)} only where "
        f"nothing there needs a person, and it holds 1 finding to judge; {_merge_line(run)}"
    )
    assert run.github.merges == []
    # The person's authorisation for the later head, given on the finding, merges it.
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_covered_head_with_an_answer_not_asked_for_stops_ready(world, capsys) -> None:
    """An answer the change check did not ask for needed the person's acceptance: the
    earlier head's authorisation does not cover a later head holding one."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("answers.txt")
    run.github.checks[head] = [_GREEN]
    run.written = [INSTALL, DEFERRED]
    run.cover = True
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 document left "
        f"out of date above, for information; the authorisation for {_short(authorised)} "
        f"covers {_short(head)} only where nothing there needs a person, and it holds 1 answer "
        f"this change was not asked for; {_merge_line(run)}"
    )
    assert run.github.merges == []


def test_expect_head_takes_a_commit_id_only(land) -> None:
    with pytest.raises(SystemExit):
        land._parser().parse_args([str(ISSUE), "--expect-head", "not-a-sha"])


# ---- the answers the change wrote (DEC-055) ---------------------------------------


def _answer(location: str, reason: str | None, **fields: Any) -> dict[str, Any]:
    """One entry of the change check's `answers`."""
    return {
        "artefact": location.split("/")[-1].removesuffix(".md"),
        "location": location,
        "answer": "unchanged",
        "anchor": None,
        "reason": reason,
        "kept": [],
        "asked": True,
        "status": "stands",
        "new": False,
        **fields,
    }


INSTALL = _answer(
    "docs/install.md",
    "The flag rename leaves the install steps as written.",
    changed=[{"kind": "path", "value": "src/cli/flags.py"}],
)
DEFERRED = _answer(
    "docs/cli.md",
    "Rewritten with the redesign.",
    answer="deferred",
    anchor={"kind": "path", "value": "src/cli/**"},
    asked=False,
)
#: The list as land-work prints it: the question once, then each answer — the document,
#: the anchors the change modified that it relies on, and whether it still holds (#1468).
LISTED = [
    "  These documents rely on something this change modifies, and each answer says whether "
    "the document is still true.",
    "  1. docs/install.md relies on src/cli/flags.py, which this change modifies. Still "
    'accurate: "The flag rename leaves the install steps as written."',
    "  2. docs/cli.md relies on src/cli/**. Out of date, fixed later (not asked for by this "
    'change): "Rewritten with the redesign."',
]
#: Where the step's line says the list is.
_IN_THE_DESCRIPTION = "listed above and in the pull request's description"


def _answers_world(world: Callable[..., _Run], *, listed: bool = False) -> _Run:
    """A change that wrote two answers; `listed`: the description carries their list."""
    run = world()
    run.written = [INSTALL, DEFERRED]
    if listed:
        run.github.body = f"{_PR_BODY}\n{run.section()}\n"
    return run


#: What the `ready:` line tells, above it, of `_answers_world`'s answers, as
#: information: the one document left out of date, with the deferral's words.
TOLD = [
    '  Left out of date: docs/cli.md, for changes to src/cli/**: "Rewritten with the redesign."'
]


def _ready_line(
    run: _Run, told: str = ", 1 document left out of date above, for information"
) -> str:
    head = run.github.head
    return (
        f"ready: {_short(head)} — CI passed, all required verdicts approved{told}; merge with: "
        f"pkit pm land-work {ISSUE} --yes --expect-head {head}"
    )


def test_the_answers_are_printed_above_ready_and_written_into_the_description(
    world, capsys
) -> None:
    run = _answers_world(world)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    at = lines.index(LISTED[0])
    assert lines[at : at + 4] == [
        *LISTED,
        f"{_STEP}: 2, {_IN_THE_DESCRIPTION} (written now)",
    ]
    # done-work's gates, run dry, print their detail; what the person is told, as
    # information, sits directly above the `ready:` line, which is last.
    assert lines[-2:] == [*TOLD, _ready_line(run)]
    # Written once, last before the provenance footer the write stamps.
    (written,) = run.github.bodies
    assert written.startswith(_PR_BODY)
    assert f"\n{run.section()}\n\n<!-- pkit-provenance:start -->" in written
    assert run.github.merges == []


#: A revisit entry (COR-050 point 16) that leaves a target of a link out of date.
REVISIT_DEFERRED = _answer(
    "reqs/latency.md",
    "The cache decision is revisited in #9999.",
    answer="revisited",
    outcome="deferred",
    target={"kind": "path", "value": "docs/cache.md"},
    links=["verified-by"],
    fields=["threshold"],
)
#: A target the change revisited by changing it: listed, never told.
REVISIT_UPDATED = _answer(
    "reqs/latency.md",
    None,
    answer="revisited",
    outcome="updated",
    target={"kind": "path", "value": "tests/test_latency.py"},
    links=["verified-by"],
    fields=["threshold"],
)


def test_a_target_a_revisit_entry_leaves_out_of_date_is_told_above_ready(world, capsys) -> None:
    """The person who authorises the merge is told which targets of a link are left
    out of date, until which follow-up, beside the documents (COR-050 points 3 and
    16, #1703); a target the change revisited by changing it is listed, not told."""
    run = _answers_world(world)
    run.written = [INSTALL, DEFERRED, REVISIT_UPDATED, REVISIT_DEFERRED]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert (
        "  3. reqs/latency.md names tests/test_latency.py through verified-by, and this change "
        "modifies its threshold. Updated in this change"
    ) in lines
    assert lines[-3:] == [
        *TOLD,
        "  Left out of date: docs/cache.md, which reqs/latency.md names through verified-by: "
        '"The cache decision is revisited in #9999."',
        _ready_line(
            run,
            ", 1 document left out of date and 1 target of a link left out of date above, for "
            "information",
        ),
    ]


def test_the_ready_line_counts_the_targets_left_out_of_date(land) -> None:
    end = land._AnswersEnd
    assert end(targets=1).phrase() == ", 1 target of a link left out of date above, for information"
    assert end(updated=1, left=2, targets=3).phrase() == (
        ", what changed in 1 updated document, 2 documents left out of date and 3 targets of a "
        "link left out of date above, for information"
    )
    assert end(left=1).phrase() == ", 1 document left out of date above, for information"
    assert end().phrase() == ""


def test_a_pr_into_another_branch_is_derived_against_that_branch(world, capsys) -> None:
    """The PR's base is always named to the change check, which resolves it as it
    resolves every branch named a base — never `$PKIT_CHECK_BASE`."""
    run = world()
    run.github.base_branch = "integration/7-x"
    run.run(capsys=capsys)
    assert run.derived == [(run.github.head, "integration/7-x")]


def test_a_list_already_in_the_description_is_read_as_current(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    # As the host may hand it back: other line endings, trailing spaces.
    run.github.body = run.github.body.replace("\n", "  \r\n")
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert f"{_STEP}: 2, {_IN_THE_DESCRIPTION}" in out.splitlines()
    assert run.github.bodies == []


def test_a_list_of_another_head_is_written_again(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    run.written = [INSTALL]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert "(written now)" in out
    (written,) = run.github.bodies
    assert written.count(_HEADING) == 1 and "docs/cli.md" not in written


def test_a_dry_run_writes_nothing(world, capsys) -> None:
    run = _answers_world(world)
    rc, out, err = run.run("--dry-run", capsys=capsys)
    assert rc == 0, out + err
    assert (f"{_STEP}: (dry-run) 2, {_IN_THE_DESCRIPTION} (would write)") in out.splitlines()
    assert run.github.bodies == [] and run.github.merges == []


def test_no_answers_removes_the_list_an_earlier_head_left(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    run.written = []
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert (
        f"{_STEP}: none — removed the list an earlier head left from the pull request's description"
    ) in out.splitlines()
    (written,) = run.github.bodies
    assert _HEADING not in written and written.startswith(_PR_BODY)
    assert [merge[-1] for merge in run.github.merges] == [run.github.head]


def test_a_dry_run_with_no_answers_leaves_an_earlier_list(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    run.written = []
    rc, out, err = run.run("--dry-run", capsys=capsys)
    assert rc == 0, out + err
    assert "would remove the list an earlier head left" in out
    assert run.github.bodies == []


@pytest.mark.parametrize(
    "unread",
    [
        "`pkit friction check --json --head x`: it exited 1: Error: no such base",
        "the base origin/main could not be fetched: Could not resolve host",
    ],
)
def test_a_list_that_cannot_be_derived_stops_unreadable(world, capsys, unread) -> None:
    run = _answers_world(world)
    run.unread = unread
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE == 2
    assert out.splitlines()[-1] == (
        f"{_STEP}: the change check's list at {_short(run.github.head)} could not be read — "
        f"{unread}. Nothing was merged; run `land-work {ISSUE}` again"
    )
    assert run.github.bodies == [] and run.github.merges == []


def test_a_reason_that_reads_as_a_closing_reference_is_refused_and_never_written(
    world, capsys
) -> None:
    run = _answers_world(world)
    run.written = [INSTALL, _answer("docs/api.md", "Holds once this fixes #77.")]
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE == 1
    assert out.splitlines()[-1] == (
        f"{_STEP}: refused — the words on docs/api.md read as a closing reference (fixes #77): "
        "in the description and the squash commit they would close an issue at merge. Reword "
        f"them there, push, and run `land-work {ISSUE}` again. Nothing was written"
    )
    assert run.github.bodies == [] and run.github.merges == []


def test_a_revisit_entry_s_target_that_reads_as_a_closing_reference_is_refused(
    world, capsys
) -> None:
    """A revisit entry's target, links and trigger fields are words of the list too
    (#1703): one that reads as a closing reference is refused, never written."""
    run = _answers_world(world)
    target = {"kind": "path", "value": "docs/fixes #77.md"}
    run.written = [INSTALL, {**REVISIT_DEFERRED, "target": target}]
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"{_STEP}: refused — the words on reqs/latency.md read as a closing reference (fixes "
        "#77): in the description and the squash commit they would close an issue at merge. "
        f"Reword them there, push, and run `land-work {ISSUE}` again. Nothing was written"
    )
    assert run.github.bodies == [] and run.github.merges == []


def test_a_reason_quoting_the_provenance_marker_is_refused_and_never_written(world, capsys) -> None:
    """A delimiter in a reason could open or close an HTML comment around the
    section's markers: the list is refused, as a closing reference is."""
    run = _answers_world(world)
    run.written = [INSTALL, _answer("docs/api.md", "The footer: <!-- pkit-provenance:start -->")]
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"{_STEP}: refused — the words on docs/api.md hold an HTML comment's delimiter (<!--): "
        "in the description it could hide the list or the markers that delimit it. Reword "
        f"them there, push, and run `land-work {ISSUE}` again. Nothing was written"
    )
    assert run.github.bodies == [] and run.github.merges == []


def test_a_list_the_description_cannot_hold_is_refused(world, capsys) -> None:
    run = _answers_world(world)
    run.written = [_answer("docs/api.md", "x" * 70000)]
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    last = out.splitlines()[-1]
    assert "past the 65536 the host keeps. Shorten the description's own text, split" in last
    assert "The only way past it is `done-work`, which lands the PR without the list" in last
    assert run.github.bodies == [] and run.github.merges == []


def test_a_write_that_fails_merges_nothing_and_is_a_retry(world, capsys) -> None:
    """The host may keep a write it answered with an error: the run merges nothing,
    since the description may not carry the list for the head it would merge, and
    running again writes it and goes on."""
    run = _answers_world(world)

    def kept_then_502(argv: list[str]) -> bool:
        if argv[:2] != ["pr", "edit"]:
            return False
        run.github.body = Path(_option(argv, "--body-file") or "").read_text(encoding="utf-8")
        return True

    run.github.fails.append(kept_then_502)
    head = run.github.head
    rc, out, _err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == run.land.EXIT_RETRY == 7
    assert out.splitlines()[-1] == (
        f"{_STEP}: 2, listed above, but the list could not be written to PR #{PR}'s description "
        "(HTTP 502: Bad Gateway), and the host may have kept it all the same. Nothing was "
        f"merged; run `land-work {ISSUE}` again"
    )
    assert run.github.merges == []
    # The host kept it: the identical run finds it there and merges.
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert run.github.merges[-1][-1] == head


@pytest.mark.parametrize("listed", [False, True])
def test_a_dry_run_that_fails_is_a_retry_whether_or_not_the_run_wrote_the_list(
    world, capsys, monkeypatch, listed
) -> None:
    """A change with answers stops on a failure as any other does: what the run
    wrote is information, and holds no next step."""
    run = _answers_world(world, listed=listed)

    def failing(argv: list[str], **kwargs: Any) -> Any:
        raise RuntimeError("gh timed out")

    monkeypatch.setattr(run.land.done_work, "run", failing)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_RETRY
    assert ("(written now)" in out) is not listed
    assert out.splitlines()[-1].startswith("merge: not merged — done-work failed")


# -- the authorisation, where the change wrote answers (DEC-055 point 3) --


@pytest.mark.parametrize("listed", [False, True])
def test_yes_merges_a_change_with_answers_as_any_other(world, capsys, listed) -> None:
    """A change with answers merges under the same authorisation as any other: a
    `--yes` run — naming the head or not — writes the list where it must, prints
    it, and merges in the same run."""
    run = _answers_world(world, listed=listed)
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    lines = out.splitlines()
    assert lines.index(LISTED[0]) < lines.index(f"merge: merged as {'c' * 7}")
    assert len(run.github.bodies) == (0 if listed else 1)
    assert run.github.merges[-1][-1] == run.github.head
    assert run.after_merge == [f"move-issue #{ISSUE}", f"close-issue #{ISSUE}"]


def test_yes_naming_the_head_that_writes_the_list_merges_in_the_same_run(world, capsys) -> None:
    """The run that has to write the list no longer stops for a second run: the
    description carries the list for the head it merges, written before the merge."""
    run = _answers_world(world)
    head = run.github.head
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert f"{_STEP}: 2, {_IN_THE_DESCRIPTION} (written now)" in out.splitlines()
    (written,) = run.github.bodies
    assert f"\n{run.section()}\n" in written
    assert [merge[-1] for merge in run.github.merges] == [head]
    assert run.after_merge == [f"move-issue #{ISSUE}", f"close-issue #{ISSUE}"]


def test_yes_naming_the_head_whose_list_is_current_merges(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    rc, out, err = run.run("--yes", "--expect-head", run.github.head[:12], capsys=capsys)
    assert rc == 0, out + err
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"
    assert run.github.bodies == []
    lines = out.splitlines()
    assert lines.index(LISTED[0]) < lines.index(f"merge: merged as {'c' * 7}")


def test_at_a_terminal_without_yes_the_prompt_follows_the_answers(
    world, capsys, monkeypatch
) -> None:
    run = _answers_world(world)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    before: list[str] = []

    def answer(prompt: str = "") -> str:
        before.append(capsys.readouterr().out)
        return "y"

    monkeypatch.setattr("builtins.input", answer)
    rc, out, err = run.run(capsys=capsys)
    assert rc == 0, out + err
    (printed,) = before
    assert LISTED[0] in printed.splitlines()
    assert "(written now)" in printed
    assert run.github.merges[-1][-1] == run.github.head


def _main_moves_on(run: _Run, path: str) -> str:
    """A commit on the base after the PR's head left it, changing `path`."""
    _git(run.work, "switch", "-q", "main")
    (run.work / path).parent.mkdir(parents=True, exist_ok=True)
    (run.work / path).write_text("main's words\n", encoding="utf-8")
    _git(run.work, "add", path)
    _git(run.work, "commit", "-q", "-m", f"main changes {path}")
    _git(run.work, "push", "-q", "origin", "main")
    tip = _git(run.work, "rev-parse", "HEAD")
    _git(run.work, "switch", "-q", BRANCH)
    run.outdated, run.tip = True, tip
    return tip


def test_a_base_that_changed_a_listed_file_is_refused(world, capsys) -> None:
    """The base's commits since the head left it changed a file an answer is on:
    the merge could land words the list does not show."""
    run = _answers_world(world, listed=True)
    _main_moves_on(run, "docs/install.md")
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"{_STEP}: refused — main moved on after PR #{PR}'s head left it, and its commits since "
        "changed 1 file (docs/install.md) the list's words are on, so its merge can land words "
        f"the list at {_short(run.github.head)} does not show. Merge main into {BRANCH} (`git "
        f"merge origin/main`), push, and run `land-work {ISSUE}` again"
    )
    assert run.github.merges == []


def test_a_base_that_moved_on_elsewhere_stops_nothing(world, capsys) -> None:
    """An outdated base whose commits changed no file the list's words are on
    lands as an up-to-date one does: the list shows every word that merges."""
    run = _answers_world(world, listed=True)
    _main_moves_on(run, "src/elsewhere.py")
    rc, out, err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == 0, out + err
    assert run.github.merges[-1][-1] == run.github.head


def test_a_base_whose_changes_cannot_be_read_is_refused(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    run.outdated, run.tip = True, "f" * 40  # a tip this clone does not have
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert (
        "which of the list's files and settings its commits since changed could not be read"
        in out.splitlines()[-1]
    )
    # With no answers, an outdated base is no reason to stop.
    run.written = []
    run.github.body = _PR_BODY
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err


def test_a_file_the_change_did_not_touch_that_cannot_be_read_is_no_reason_to_stop(
    world, capsys
) -> None:
    """A file the change did not touch holds no word of it."""
    run = world()
    run.unreadable = [".gitignore"]  # unreadable, and untouched by the change
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err


def test_a_file_the_change_touches_that_cannot_be_read_is_refused(world, capsys) -> None:
    """Words on a file whose front matter does not parse cannot be listed."""
    run = world()
    run.unreadable = ["change.txt", ".gitignore"]  # the change added change.txt
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"{_STEP}: refused — front matter the change check cannot read, in 1 file "
        "(change.txt) this change touches, so its words cannot be listed. Fix it (`pkit "
        f"validate` names the problem), push, and run `land-work {ISSUE}` again"
    )
    assert run.github.merges == []


def test_the_terminal_list_shows_what_a_terminal_would_act_on_escaped(world, capsys) -> None:
    run = world()
    run.written = [_answer("docs/a.md", "fine\x1b[2Kgone ‮esrever")]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert '  1. docs/a.md — still accurate: "fine\\x1b[2Kgone \\u202eesrever"' in out.splitlines()
    assert "\x1b" not in out and "‮" not in out
    assert "``fine\\x1b[2Kgone \\u202eesrever``" in run.github.body


def test_done_work_closes_no_issue_the_list_names(world, capsys) -> None:
    """done-work reads the closing references outside the list: a description whose
    list says "fixes #77" closes #42 alone, through done-work's real path."""
    run = world()
    assert run.run(capsys=capsys)[0] == run.land.EXIT_READY  # reviewed, not merged
    run.written = [_answer("docs/a.md", "Holds once this fixes #77.")]
    run.github.body = f"{_PR_BODY}\n{run.section()}\n"
    end = run.land.done_work.run([str(ISSUE), "--yes"], pinned_head=run.github.head)
    assert end.kind == run.land.done_work.MERGED
    assert run.after_merge == [f"move-issue #{ISSUE}", f"close-issue #{ISSUE}"]
    assert not any(call[:3] == ["issue", "view", "77"] for call in run.github.calls)


# -- a section no command wrote, and the friction settings (DEC-055 points 1 and 3) --


def _hand_written(heading: str) -> str:
    """A list an agent typed under `heading`, with no markers."""
    return f"{heading}\n\n```\n1. docs/install.md — unchanged: as I recall it\n```\n"


@pytest.mark.parametrize("heading", [_HEADING, _FORMER_HEADING])
def test_a_section_no_command_wrote_is_removed_and_said(world, capsys, heading) -> None:
    """A section an agent typed under the heading — or the one an earlier run wrote
    — with no markers is never the list: land-work removes it as it writes the
    check's own, and says so."""
    run = _answers_world(world)
    run.github.body = f"{_PR_BODY}\n{_hand_written(heading)}"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert (
        f"{_STEP}: 2, {_IN_THE_DESCRIPTION} (written now); removed a list written by hand"
    ) in out.splitlines()
    (written,) = run.github.bodies
    assert "as I recall it" not in written and written.count(_HEADING) == 1
    assert _FORMER_HEADING not in written


@pytest.mark.parametrize("heading", [_HEADING, _FORMER_HEADING])
def test_a_section_no_command_wrote_is_removed_where_the_change_wrote_none(
    world, capsys, heading
) -> None:
    run = world()
    run.github.body = f"{_PR_BODY}\n{_hand_written(heading)}"
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert (
        f"{_STEP}: none — removed a list written by hand from the pull request's description"
    ) in out.splitlines()
    (written,) = run.github.bodies
    assert heading not in written and written.startswith(_PR_BODY)


def test_a_list_an_earlier_run_wrote_under_the_former_heading_is_written_again(
    world, capsys
) -> None:
    """The markers identify the list: one an earlier run wrote under the former
    heading, in the former words, is replaced whole — one section, under the
    heading, in the section's words — and is not read as current."""
    run = _answers_world(world)
    section = run.section()
    assert section.startswith(f"{_HEADING}\n")
    earlier = section.replace(_HEADING, _FORMER_HEADING, 1).replace("Still accurate", "unchanged")
    run.github.body = f"{_PR_BODY}\n{earlier}\n"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert f"{_STEP}: 2, {_IN_THE_DESCRIPTION} (written now)" in out.splitlines()
    (written,) = run.github.bodies
    assert written.count(_HEADING) == 1 and _FORMER_HEADING not in written
    assert f"\n{section}\n\n<!-- pkit-provenance:start -->" in written


def test_an_earlier_list_that_cannot_be_removed_is_a_retry(world, capsys) -> None:
    """With no answers and no setting, nothing is held: a removal that failed is
    run again like any other step."""
    run = _answers_world(world, listed=True)
    run.written = []
    run.github.fails.append(lambda argv: argv[:2] == ["pr", "edit"])
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_RETRY
    assert out.splitlines()[-1] == (
        f"{_STEP}: none, and the list an earlier head left could not be removed from PR "
        f"#{PR}'s description: HTTP 502: Bad Gateway. Nothing was merged; run "
        f"`land-work {ISSUE}` again"
    )
    assert run.github.merges == []


def test_a_change_that_sets_friction_dormant_is_shown_like_an_answer(world, capsys) -> None:
    """A change that empties the friction places leaves the check dormant at its
    head, listing no answer: the settings it altered are shown instead, and told
    above the `ready:` line, as information."""
    run = world()
    answers = run.land.friction_answers
    run.settings = [answers.Setting(answers.PLACES, ("docs",), ())]
    head = run.github.head
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert f"  {answers.PLACES}: docs → none" in lines
    assert (
        f"{_STEP}: none, but a change to which documents are checked, {_IN_THE_DESCRIPTION} "
        "(written now)"
    ) in lines
    assert lines[-2:] == [
        f"  {answers.PLACES}: docs → none",
        f"ready: {_short(head)} — CI passed, all required verdicts approved, a change to "
        "which documents are checked above, for information; merge with: pkit pm land-work "
        f"{ISSUE} --yes --expect-head {head}",
    ]
    (written,) = run.github.bodies
    assert f"- {answers.PLACES}: `docs` → none" in written
    assert run.github.merges == []
    # The authorisation merges it as it merges any other change.
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert run.github.merges[-1][-1] == head and len(run.github.bodies) == 1


# -- the author's sentences, and what the person is told (DEC-055 points 1 and 3) --

#: The description of a change that updated two documents and says what changed
#: in one of them.
_SAID = (
    f"{_PR_BODY}\n## What changed in each updated document\n\n"
    "- `docs/install.md`: The install steps name the renamed flag.\n"
)
UPDATED_INSTALL = _answer(
    "docs/install.md",
    None,
    answer="updated",
    changed=[{"kind": "path", "value": "src/cli/flags.py"}],
)
UPDATED_GUIDE = _answer("docs/guide.md", None, answer="updated")


def test_the_list_gives_each_updated_document_its_author_s_sentence(world, capsys) -> None:
    """Each sentence is read from the description's own section and given beside its
    document — in the printed list, in the list written, and in what the `ready:`
    line tells — and a document with none is said to have none."""
    run = world()
    run.written = [UPDATED_INSTALL, UPDATED_GUIDE, DEFERRED]
    run.github.body = _SAID
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    said = (
        "   (what changed, in the words of the pull request's author: \"The install steps "
        'name the renamed flag.")'
    )
    assert f"  {said}" in lines
    assert "     (what changed: the pull request's author has not said)" in lines
    head = run.github.head
    assert lines[-4:] == [
        '  What changed in docs/install.md: "The install steps name the renamed flag."',
        "  What changed in docs/guide.md: the pull request's author has not said",
        *TOLD,
        f"ready: {_short(head)} — CI passed, all required verdicts approved, what changed in 2 "
        "updated documents and 1 document left out of date above, for information; merge "
        f"with: pkit pm land-work {ISSUE} --yes --expect-head {head}",
    ]
    (written,) = run.github.bodies
    assert written.startswith(_SAID)  # the author's own section stays where it was
    assert (
        "   - (what changed, in the words of the pull request's author: \"``The install steps "
        'name the renamed flag.``")'
    ) in written
    # The list with the sentence is current: the identical run writes nothing again.
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY and len(run.github.bodies) == 1
    assert f"{_STEP}: 3, {_IN_THE_DESCRIPTION}" in out.splitlines()


@pytest.mark.parametrize(
    ("item", "unread"),
    [
        ("- **docs/guide.md:** The guide names the new flag.", True),
        ("- docs/guide.md: The guide names the new flag.", True),
        ("- `docs/guide.md`: The guide names the new flag.", False),
    ],
    ids=["bold path", "no code span", "read form"],
)
def test_an_item_it_cannot_read_draws_a_warning_naming_its_line_and_the_form(
    world, capsys, item, unread
) -> None:
    """As on PR #1519: a sentence in bold reads as none, and the person is told the
    author has not said. The warning above the list names its line in the
    description and the form a sentence takes; the read form draws none."""
    run = world()
    run.written = [UPDATED_INSTALL, UPDATED_GUIDE, DEFERRED]
    run.github.body = f"{_SAID}{item}\n"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    warned = [line for line in lines if "is not read as a sentence" in line]
    told = "  What changed in docs/guide.md: the pull request's author has not said"
    if not unread:
        assert warned == [] and told not in lines
        return
    assert run.github.body.split("\n")[17] == item  # line 18 of the description
    assert warned == [
        "  warn: line 18 of the description, under `## What changed in each updated document`, "
        f'is not read as a sentence: "{item}" — write it as "- `path`: sentence", starting in '
        "the line's first column, the document in a code span as the list names it"
    ]
    assert lines.index(warned[0]) < lines.index("  " + run.land.friction_answers.QUESTION)
    assert told in lines


@pytest.mark.parametrize("current", [True, False], ids=["list kept", "list rewritten"])
def test_the_line_named_is_the_line_in_the_description_the_run_leaves(
    world, capsys, current
) -> None:
    """With the list above the sentences, a run that keeps the description names the
    line where it is, and a run that writes the list again — last — names the line
    the item moves up to."""
    run = world()
    run.written = [UPDATED_INSTALL, UPDATED_GUIDE, DEFERRED]
    item = "- **docs/guide.md:** The guide names the new flag."
    run.github.body = f"{_SAID}{item}\n"
    assert run.run(capsys=capsys)[0] == run.land.EXIT_READY
    region = run.land.friction_answers.find(run.github.bodies[-1])
    said = _SAID.removeprefix(_PR_BODY)
    if not current:  # the author's sentence changed since the list was written
        said = said.replace("name the renamed flag", "keep the old flag")
    before = f"{_PR_BODY}\n{_HEADING}\n\n{region}\n{said}{item}\n"
    run.github.body = before
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert ("(written now)" in out) is not current
    left = (before if current else run.github.bodies[-1]).split("\n").index(item) + 1
    assert (left == before.split("\n").index(item) + 1) is current
    (warned,) = [line for line in out.splitlines() if "is not read as a sentence" in line]
    assert warned.startswith(f"  warn: line {left} of the description, ")


def test_a_sentence_edited_in_the_description_is_written_again(world, capsys) -> None:
    run = world()
    run.written = [UPDATED_INSTALL]
    run.github.body = _SAID
    assert run.run(capsys=capsys)[0] == run.land.EXIT_READY
    # The author edits the sentence in their own section on the host, by hand: the list
    # written before still gives the old one.
    author, listed = run.github.body.split(_HEADING, 1)
    author = author.replace("name the renamed flag", "keep the old flag")
    run.github.body = f"{author}{_HEADING}{listed}"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert "(written now)" in out
    assert "keep the old flag.``" in run.github.bodies[-1]
    assert "name the renamed flag.``" not in run.github.bodies[-1]


@pytest.mark.parametrize(
    ("sentence", "why"),
    [
        (
            "It fixes #77 too.",
            "reads as a closing reference (fixes #77): in the list it would close an issue at "
            "merge",
        ),
        (
            "Quotes <!-- a comment.",
            "holds an HTML comment's delimiter (<!--): in the list it could hide the list or the "
            "markers that delimit it",
        ),
    ],
)
def test_a_sentence_the_list_must_not_hold_is_refused_and_never_written(
    world, capsys, sentence, why
) -> None:
    run = world()
    run.written = [UPDATED_INSTALL]
    run.github.body = _SAID.replace("The install steps name the renamed flag.", sentence)
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"{_STEP}: refused — the sentence on what changed in docs/install.md, under `## What "
        f"changed in each updated document` in PR #{PR}'s description, {why}. Reword it there "
        f"(`edit-pr {PR}`), and run `land-work {ISSUE}` again. Nothing was written"
    )
    assert run.github.bodies == [] and run.github.merges == []


def test_a_base_that_changed_the_listed_settings_is_refused(world, capsys, monkeypatch) -> None:
    """The settings the list shows are words of it too: a base whose commits since
    changed them can land settings the list does not show."""
    run = world()
    answers = run.land.friction_answers
    run.settings = [answers.Setting(answers.PLACES, ("docs",), ())]
    run.github.body = f"{_PR_BODY}\n{run.section()}\n"
    _main_moves_on(run, "src/elsewhere.py")
    moved: list[tuple[str, str]] = []

    def settings_change(merge_base: str, head: str) -> Any:
        moved.append((merge_base, head))
        return (answers.Setting(answers.PLACES, ("docs",), ("docs", "guides")),)

    monkeypatch.setattr(answers, "settings_change", settings_change)
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert "its commits since changed the friction settings the list shows" in out.splitlines()[-1]
    assert moved == [(run.merge_base, run.tip)] and run.github.merges == []
    # A base that left the settings as they were stops nothing.
    monkeypatch.setattr(answers, "settings_change", lambda merge_base, head: ())
    rc, out, err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == 0, out + err


# ---- the findings to judge (DEC-028's finding tags, DEC-055 point 3) ---------------

_PERSON = (
    "Approved, with one point for you.\n"
    "\n"
    "- [person] RS-GUIDE-003, `docs/install.md` line 12 — whether the new paragraph says "
    "only what the page's reader needs.\n"
    "  - the paragraph on worktrees\n"
    "- [advisory] A name could be clearer.\n"
)


def _person_lines(name: str, stale: str = "") -> list[str]:
    """How land-work prints `_PERSON`'s `[person]` finding: whole, under its reviewer."""
    under = " " * len(f"  [{name}] ")
    return [
        f"  [{name}] {stale}[person] RS-GUIDE-003, `docs/install.md` line 12 — whether the new "
        "paragraph says only what the page's reader needs.",
        f"{under}- the paragraph on worktrees",
    ]


def _comment(run: _Run, body: str) -> dict[str, Any]:
    """A comment as the fake GitHub posts one, next in time."""
    n = len(run.github.comments)
    return {
        "author": {"login": "octocat"},
        "body": body,
        "createdAt": f"2026-10-01T11:{n:02d}:00Z",
        "url": f"https://github.com/o/r/pull/{PR}#c{n}",
        "viewerDidAuthor": True,
        "lastEditedAt": None,
    }


def _verdict(run: _Run, name: str, body: str, *, sha: str) -> dict[str, Any]:
    """A local reviewer's approval of `sha`, as review-pr posts it."""
    posted = run.land.review_pr._format_verdict_comment(
        name, "APPROVED", body, sha=sha, base=run.github.base
    )
    return _comment(run, posted)


def _remote_verdict(run: _Run, login: str, body: str, *, sha: str) -> dict[str, Any]:
    """A remote reviewer's approval of `sha`, posted under its own login."""
    posted = run.land.review_pr.stamp_verdict(
        f"Reviewer agent: APPROVED\n\n{body}", sha, run.github.base
    )
    return {**_comment(run, posted), "author": {"login": login}, "viewerDidAuthor": False}


def _findings_read(run: _Run) -> Callable[[list[str]], bool]:
    fields = ",".join(run.land._FINDINGS_VIEW)
    return lambda argv: argv[:2] == ["pr", "view"] and argv[-1] == fields


def _merge_line(run: _Run) -> str:
    return f"merge with: pkit pm land-work {ISSUE} --yes --expect-head {run.github.head}"


def test_a_person_finding_this_run_posted_stops_it_ready_and_the_rerun_merges(
    world, capsys
) -> None:
    """The `--yes` came before the verdict: the finding is printed whole, and the
    run stops ready. Its identical re-run found the verdict when it started,
    standing for the head, and merges."""
    run = world()
    head = run.github.head
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_READY == 8
    lines = out.splitlines()
    at = lines.index(_person_lines("code-reviewer")[0])
    assert lines[at : at + 3] == [*_person_lines("code-reviewer"), f"{_FINDINGS}: 1, above"]
    assert lines[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 finding to judge "
        "above (code-reviewer's verdict came after this run's --yes was given, so the --yes does "
        f"not cover its finding); {_merge_line(run)}"
    )
    assert run.github.merges == []

    run.invoked.clear()
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert run.invoked == []
    lines = out.splitlines()
    merged = lines.index(f"merge: merged as {'c' * 7}")
    assert lines.index(_person_lines("code-reviewer")[0]) < merged
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_person_finding_found_at_the_start_for_the_head_merges(world, capsys) -> None:
    """The person is shown the finding at the `ready:` stop and authorises that
    head: the run that merges found the verdict when it started."""
    run = world()
    head = run.github.head
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert _person_lines("code-reviewer")[0] in lines
    assert lines[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 finding to judge "
        f"above; {_merge_line(run)}"
    )
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert f"{_FINDINGS}: 1, above" in out.splitlines()
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_person_finding_posted_while_the_run_ran_stops_it_ready(world, capsys) -> None:
    run = world()
    head = run.github.head
    assert run.run(capsys=capsys)[0] == run.land.EXIT_READY
    late = _verdict(run, "reviewer", _PERSON, sha=head)
    run.github.before(_findings_read(run), lambda: run.github.comments.append(late))
    rc, out, _err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert _person_lines("reviewer")[0] in lines
    assert lines[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 finding to judge "
        "above (reviewer's verdict came after this run's --yes was given, so the --yes does not "
        f"cover its finding); {_merge_line(run)}"
    )
    assert run.github.merges == []
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_person_finding_for_another_head_holds_every_run_until_a_review(world, capsys) -> None:
    """Human review mode re-runs no reviewer: a verdict reviewed at an earlier
    head is printed marked stale, and every `--yes` run stops ready, naming the
    review it waits for, until the reviewer posts a verdict for the head."""
    run = world(mode="human")
    old = run.github.head
    run.github.comments.append(_verdict(run, "code-reviewer", _PERSON, sha=old))
    new = run.push_new_head("fix.txt")
    run.github.checks[new] = [_GREEN]
    run.github.comments.append(_comment(run, "Approved — looks right."))
    stale = f"(stale: reviewed {_short(old)}; changed since: fix.txt) "
    ready = (
        f"ready: {_short(new)} — CI passed, the PR is approved, 1 finding to judge above "
        f"(code-reviewer's verdict does not stand for {_short(new)}, so no --yes covers its "
        f"finding until code-reviewer posts one that does; `review-pr {ISSUE}` runs a local "
        f"reviewer again); {_merge_line(run)}"
    )
    for _ in range(2):
        rc, out, _err = run.run("--yes", "--expect-head", new, capsys=capsys)
        assert rc == run.land.EXIT_READY
        lines = out.splitlines()
        at = lines.index(_person_lines("code-reviewer", stale)[0])
        assert lines[at : at + 3] == [
            *_person_lines("code-reviewer", stale),
            f"{_FINDINGS}: 1, above (1 marked stale)",
        ]
        assert lines[-1] == ready
        assert run.github.merges == []

    run.github.comments.append(_verdict(run, "code-reviewer", _PERSON, sha=new))
    rc, out, err = run.run("--yes", "--expect-head", new, capsys=capsys)
    assert rc == 0, out + err
    assert _person_lines("code-reviewer")[0] in out.splitlines()
    assert [merge[-1] for merge in run.github.merges] == [new]


def test_verdicts_that_could_not_be_read_at_the_start_hold_the_run(world, capsys) -> None:
    """What the run found at its start is what it read then: a read that failed
    found nothing, so the finding is new to it — the hold fails toward a stop."""
    run = world()
    head = run.github.head
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    assert run.run(capsys=capsys)[0] == run.land.EXIT_READY
    run.github.fails.append(lambda argv: argv[:2] == ["pr", "view"] and argv[-1] == "comments")
    rc, out, _err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 finding to judge "
        "above (the verdicts could not be read when this run started, so its --yes does not "
        f"cover its finding); {_merge_line(run)}"
    )
    assert run.github.merges == []


def test_verdicts_that_cannot_be_read_for_the_findings_stop_the_run(world, capsys) -> None:
    run = world()
    run.github.fails.append(_findings_read(run))
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    assert out.splitlines()[-1] == (
        f"{_FINDINGS}: PR #{PR}'s verdicts could not be read: HTTP 502: Bad Gateway. Nothing "
        f"was merged; run `land-work {ISSUE}` again"
    )
    assert run.github.merges == []


def test_findings_that_cannot_be_read_stop_before_the_list_is_written(world, capsys) -> None:
    """The findings are read before the answers' list is written: a run that
    wrote the list must end ready, never on a stop whose next step is the same
    `--yes` again (DEC-055 point 3)."""
    run = _answers_world(world)
    run.github.fails.append(_findings_read(run))
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    assert out.splitlines()[-1].startswith(f"{_FINDINGS}: PR #{PR}'s verdicts could not be read")
    assert run.github.bodies == []
    assert run.github.merges == []


@pytest.mark.parametrize(
    "author",
    [None, {"login": ""}, {"is_bot": True, "login": "app/"}],
    ids=["null-author", "empty-login", "gh-null-author"],
)
def test_a_remote_person_finding_on_a_pr_whose_author_cannot_be_read_stops_the_run(
    world, capsys, author
) -> None:
    """With no author read, no remote verdict counts, so a remote reviewer's
    `[person]` finding would go unshown, though its verdict may not be the
    author's own: the run stops before the answers' list is written, with
    nothing merged (#1485)."""
    run = world(remote=("review-bot",))
    run.github.comments.append(_remote_verdict(run, "review-bot", _PERSON, sha=run.github.head))
    run.github.author = author
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    assert out.splitlines()[-1] == (
        f"{_FINDINGS}: whose verdicts count could not be resolved (PR #{PR}'s author could "
        "not be read), so the findings a reviewer left for a person to judge cannot be shown. "
        f"Nothing was merged; run `land-work {ISSUE}` again"
    )
    assert _person_lines("review-bot")[0] not in out.splitlines()
    assert run.github.bodies == []
    assert run.github.merges == []


@pytest.mark.parametrize(
    "author",
    [None, {"login": ""}, {"is_bot": True, "login": "app/"}],
    ids=["null-author", "empty-login", "gh-null-author"],
)
def test_a_local_person_finding_on_a_pr_whose_author_cannot_be_read_holds_as_before(
    world, capsys, author
) -> None:
    """A local verdict is read with no author exclusion (DEC-028 step 3), so an
    unread author changes nothing for it: its finding is shown and holds the
    `--yes` it came after, and the identical re-run merges (#1485)."""
    run = world()
    head = run.github.head
    run.github.author = author
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    rc, out, _err = run.run("--yes", capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    at = lines.index(_person_lines("code-reviewer")[0])
    assert lines[at : at + 3] == [*_person_lines("code-reviewer"), f"{_FINDINGS}: 1, above"]
    assert lines[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 finding to judge "
        "above (code-reviewer's verdict came after this run's --yes was given, so the --yes does "
        f"not cover its finding); {_merge_line(run)}"
    )
    assert run.github.merges == []

    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_person_finding_from_an_unrequired_remote_login_holds_nothing_when_the_author_is_unread(
    world, capsys
) -> None:
    """Only a required remote reviewer's verdict is one an unread author could
    hide: a remote verdict from a login the gate does not require stops
    nothing and holds nothing, as with the author read (#1485)."""
    run = world()
    run.github.author = None
    run.github.comments.append(_remote_verdict(run, "stranger", _PERSON, sha=run.github.head))
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert "[stranger]" not in out
    assert not any(step.startswith(f"{_FINDINGS}:") for step in _steps(out))


def test_a_person_finding_from_a_reviewer_the_gate_does_not_require_holds_nothing(
    world, capsys
) -> None:
    run = world()
    run.github.comments.append(_verdict(run, "stranger", _PERSON, sha=run.github.head))
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    assert "[stranger]" not in out
    assert not any(step.startswith(f"{_FINDINGS}:") for step in _steps(out))


def test_a_person_finding_in_an_unmarked_verdict_holds_nothing(world, capsys) -> None:
    """Only a marked verdict is one the gate reads: a verdict-shaped comment with
    no marker — typed by hand, say — neither shows its finding nor holds."""
    run = world()
    head = run.github.head
    assert run.run(capsys=capsys)[0] == run.land.EXIT_READY
    # The latest comment of its shape, but with no marker.
    run.github.comments.append(
        _comment(run, f"Reviewer agent (local, code-reviewer): APPROVED\n\n{_PERSON}")
    )
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert _person_lines("code-reviewer")[0] not in out.splitlines()
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_findings_with_no_person_tag_land_as_today(world, capsys) -> None:
    """An untagged finding counts as `[advisory]`, and a tag in a fenced block
    is no tag: no step prints, and nothing holds the `--yes`."""
    run = world()
    head = run.github.head
    run.answers["code-reviewer"] = (
        "APPROVED",
        "Fine.\n\n- An untagged note.\n- [advisory] A name could be clearer.\n\n"
        "```\n- [person] quoted in a fence\n```\n",
    )
    rc, out, err = run.run("--yes", capsys=capsys)
    assert rc == 0, out + err
    lines = out.splitlines()
    assert "  [code-reviewer] An untagged note." in lines
    assert "  [code-reviewer] [advisory] A name could be clearer." in lines
    assert _steps(out) == [
        f"head: {_short(head)} (PR #{PR}, {BRANCH})",
        f"ci: passed on {_short(head)} (8m, run https://github.com/o/r/actions/runs/77)",
        "review: 0 kept fresh, 2 re-run — all approved; 2 advisories above (every verdict in "
        f"full: `show-pr {PR} --field review`)",
        f"{_STEP}: none",
        f"merge: merged as {'c' * 7}",
    ]


def test_at_a_terminal_the_prompt_follows_the_findings(world, capsys, monkeypatch) -> None:
    run = world()
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    before: list[str] = []

    def answer(prompt: str = "") -> str:
        before.append(capsys.readouterr().out)
        return "y"

    monkeypatch.setattr("builtins.input", answer)
    rc, out, err = run.run(capsys=capsys)
    assert rc == 0, out + err
    (printed,) = before
    shown = printed.splitlines()
    at = shown.index(_person_lines("code-reviewer")[0])
    assert shown[at : at + 3] == [*_person_lines("code-reviewer"), f"{_FINDINGS}: 1, above"]
