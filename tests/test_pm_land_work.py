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
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Any

import pytest

from tests import pm_issue_branch_support as issue_branch_support
from tests import pull_request_backbone
from tests.adopter_repo import MakeAdopterRepo, sign_nothing
from tests.anchor_kind_capabilities import RESOLVER, RESOLVING, register_kinds
from tests.friction_documents import CONFIG, SOURCE, document, friction_config

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


def _check(name: str, outcome: str) -> dict[str, Any]:
    """A check under `name`: an outcome in capitals of a run that ended, else a status."""
    if outcome in ("IN_PROGRESS", "QUEUED"):
        return {"__typename": "CheckRun", "name": name, "status": outcome}
    return {"__typename": "CheckRun", "name": name, "status": "COMPLETED", "conclusion": outcome}


#: The check a project names to start the review, and the suite's two parts.
_FIRST = ("the remainder",)
_SLICE_1, _SLICE_2 = "slice 1 of 2", "slice 2 of 2"


def _parts(first: str, slice_1: str, slice_2: str = "QUEUED") -> list[dict[str, Any]]:
    return [
        _check(_FIRST[0], first),
        _check(_SLICE_1, slice_1),
        _check(_SLICE_2, slice_2),
    ]


#: Every part running; the first passed with the suite running; every part passed.
_ALL_RUNNING = _parts("IN_PROGRESS", "IN_PROGRESS")
_SUITE_RUNNING = _parts("SUCCESS", "IN_PROGRESS")
_ALL_PASSED = _parts("SUCCESS", "SUCCESS", "SUCCESS")
#: What the line for the checks that start the review names of the rest.
_THE_REST = f"{_SLICE_1} (IN_PROGRESS), {_SLICE_2} (QUEUED)"

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
    #: GitHub's `mergeStateStatus`; BEHIND refuses a merge, as a host that merges
    #: only a branch up to date with its base does.
    merge_state: str = "CLEAN"
    #: How many readings of `mergeStateStatus` answer UNKNOWN, as GitHub answers
    #: before it has worked the state out; the state is `merge_state` all the same.
    unsettled: int = 0
    #: The PR comes from a fork.
    cross_repository: bool = False
    merge_commit: str = ""
    #: The base branch merges through a queue.
    queue: bool = False
    queued: bool = False
    #: How many readings of the queue fail, the first ones; and how many were asked.
    queue_unreadable: int = 0
    queue_reads: int = 0
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
    #: The checks the base branch requires, by name, which its rulesets state
    #: (#1965); none by default.
    required: list[str] = field(default_factory=list)
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
            if "mergeStateStatus" in fields and self.unsettled:
                self.unsettled -= 1
                view["mergeStateStatus"] = "UNKNOWN"
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
        if argv == ["api", f"repos/{{owner}}/{{repo}}/branches/{self.base_branch}"]:
            # A ruleset protects the branch; its classic protection is off.
            off = {"enabled": False, "required_status_checks": {"enforcement_level": "off"}}
            return _done(argv, json.dumps({"protected": bool(self.required), "protection": off}))
        if argv == [
            "api",
            "--paginate",
            f"repos/{{owner}}/{{repo}}/rules/branches/{self.base_branch}",
        ]:
            checks = [{"context": name} for name in self.required]
            rule = {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": checks},
            }
            return _done(argv, json.dumps([rule] if checks else []))
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
            "mergeStateStatus": self.merge_state,
            "isCrossRepository": self.cross_repository,
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
        self.queue_reads += 1
        if self.unreadable_after_merge and self.merges:
            raise self.mq.Unreadable("HTTP 502")
        if self.queue_reads <= self.queue_unreadable:
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
            if self.merge_state == "BEHIND":
                return _done(argv, returncode=1, stderr="Head branch is out of date")
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
    #: How many times the head's checks had been read as each reviewer started.
    reads_at_review: list[int] = field(default_factory=list)
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
    #: The check's `answered_apart_at_tip`: each revalidation on the base's tip the
    #: change's answer did not read.
    apart: list[dict[str, Any]] = field(default_factory=list)
    outdated: bool = False
    tip: str = ""
    unreadable: list[str] = field(default_factory=list)
    unread: str | None = None
    #: Each (head, base) the list was derived for.
    derived: list[tuple[str, str | None]] = field(default_factory=list)
    #: The answers at a given head, where they are not `written`; None for a head
    #: whose answers cannot be read.
    written_at: dict[str, list[dict[str, Any]] | None] = field(default_factory=dict)
    merge_base: str = ""
    #: The backbone's answer on whether the authorisation for an earlier head covers
    #: the PR's head (`friction_answers.covers`): covered, or why it cannot answer —
    #: and each (since, head, base) it was asked about.
    cover: bool = False
    cover_problem: str | None = None
    asked_cover: list[tuple[str, str, str]] = field(default_factory=list)
    #: The accepted decision records the change alters at the head
    #: (`accepted_records.derive`), or why they could not be read, and each (head,
    #: base) they were derived for.
    altered: list[Any] = field(default_factory=list)
    altered_problem: str | None = None
    altered_for: list[tuple[str, str]] = field(default_factory=list)
    #: The list at a given head, where it is not `altered`; None for one that cannot
    #: be read there.
    altered_at: dict[str, list[Any] | None] = field(default_factory=dict)
    #: The change check on the merge of the head with the base's tip
    #: (`friction_answers.merged`): the findings it fails on, the files a merge
    #: conflicts in, or why it could not be read — and each (head, base, the head's own
    #: check) it was asked about. The merge is the head itself unless the base moved on.
    merge_refused: list[dict[str, Any]] = field(default_factory=list)
    #: Findings the check reports at the merge in warning mode, failing nothing.
    merge_reported: list[dict[str, Any]] = field(default_factory=list)
    merge_conflicts: tuple[str, ...] = ()
    merge_problem: str | None = None
    merged_for: list[tuple[str, str, Any]] = field(default_factory=list)
    #: The real `friction_answers.merged`, for a test that runs the change check.
    real_merged: Callable[..., Any] | None = None
    #: The real `friction_answers.derive` and `checked`, for such a test too.
    real_derive: Callable[..., Any] | None = None
    real_checked: Callable[..., Any] | None = None
    #: Whether each reviewer's brief told it to start nothing of the head (DEC-067 point 5).
    confined: list[bool] = field(default_factory=list)

    def merged(
        self, head: str, base: str, *, checked: Any = None, from_checkout: bool = True
    ) -> Any:
        """`friction_answers.merged`, answered from this world."""
        self.merged_for.append((head, base, checked))
        fa = self.land.friction_answers
        tip = self.tip or self.merge_base
        if self.merge_problem is not None:
            return fa.Merged(head, problem=self.merge_problem)
        if self.merge_conflicts:
            return fa.Merged(head, tip=tip, conflicts=self.merge_conflicts)
        findings = self.merge_refused or self.merge_reported
        document = {"failed": bool(self.merge_refused), "findings": findings}
        merge = "d" * 40 if self.outdated else head
        return fa.Merged(head, tip=tip, merge=merge, document=document)

    def accepted(self, head: str, base: str) -> Any:
        """`accepted_records.derive`, answered from this world."""
        self.altered_for.append((head, base))
        records = self.land.accepted_records
        if self.altered_problem is not None:
            return records.Derivation(problem=self.altered_problem)
        found = self.altered_at.get(head, self.altered)
        if found is None:
            return records.Derivation(problem=f"`pkit decisions check-diff`: no {head[:7]}")
        return records.Derivation(tuple(found))

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

    def derive(
        self, head: str, base: str | None, *, source: Any = None, from_checkout: bool = True
    ) -> Any:
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
            "answered_apart_at_tip": self.apart,
            "unreadable": self.unreadable,
        }
        return fa.Derivation(
            head, document=document, answers=tuple(self.written), settings=tuple(self.settings)
        )

    def checked(
        self, head: str, base: str, *, source: Any = None, from_checkout: bool = True
    ) -> Any:
        """`friction_answers.checked`, answered from this world's change check: the
        answers at `head`, the ones the run is told of unless `written_at` says
        otherwise."""
        fa = self.land.friction_answers
        written = self.written_at.get(head, self.written)
        if written is None:
            return fa.Derivation(head, problem="no document at that head")
        return fa.Derivation(head, document={"answers": written}, answers=tuple(written))

    def earlier_list(self, reason: str = "Rewritten with the redesign.") -> str:
        """A list of the answers as an earlier run wrote it into the description, for
        the current head, one answer's `reason` in it (DEC-055 point 1)."""
        fa = self.land.friction_answers
        return "\n".join(
            [
                fa.HEADING,
                "",
                f"{fa.MARKER_START} head={self.github.head} base={self.merge_base} -->",
                "These documents rely on something this change modifies, and each answer says "
                "whether the document is still true.",
                "",
                "1. `docs/cli.md` relies on `src/cli/**`. **Out of date, fixed later**: "
                f'"``{reason}``"',
                fa.MARKER_END,
            ]
        )

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

    def authorised(self, *argv: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
        """A run on the person's authorisation for the PR's head as it stands when
        the run is started: `--yes --expect-head <head>`, since an authorisation
        is for a named head (DEC-055 point 3, #1760)."""
        return self.run("--yes", "--expect-head", self.github.head, *argv, capsys=capsys)


def _stage_project(
    work: Path,
    *,
    mode: str,
    remote: tuple[str, ...] = (),
    local: tuple[str, ...] = PANEL,
    start_after: tuple[str, ...] = (),
) -> Path:
    capability = work / ".pkit" / "capabilities" / "project-management"
    project = capability / "project"
    project.mkdir(parents=True)
    shutil.copytree(CAPABILITY / "schemas", capability / "schemas")
    shutil.copytree(CAPABILITY / "templates", capability / "templates")
    reviewers = "".join(f"      - name: {name}\n" for name in local)
    remotes = "".join(f"      - github_login: {login}\n" for login in remote)
    first = "".join(f"      - {name}\n" for name in start_after)
    (project / "config.yaml").write_text(
        "schema_version: 1\n"
        "default_branch: main\n"
        "workstreams: []\n"
        "review:\n"
        f"  mode: {mode}\n"
        "  agents:\n"
        + (f"    remote_registered:\n{remotes}" if remote else "")
        + (f"    local_registered:\n{reviewers}" if local else "")
        + (f"    start_after_checks:\n{first}" if start_after else ""),
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
        local: tuple[str, ...] = PANEL,
        start_after: tuple[str, ...] = (),
    ) -> _Run:
        shutil.copytree(clone.root, tmp_path / "clone", symlinks=True)
        work = tmp_path / "clone" / "work"
        _stage_project(work, mode=mode, remote=remote, local=local, start_after=start_after)
        monkeypatch.chdir(work)
        monkeypatch.setenv("PM_INVOKER_LOGIN", "octocat")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        github = _FakeGitHub(mq=land.merge_queue, head=clone.head, base=clone.base)
        run = _Run(land=land, work=work, github=github, merge_base=clone.base)
        github.checks[github.head] = checks if checks is not None else [_GREEN]
        run.real_merged = land.friction_answers.merged
        run.real_derive = land.friction_answers.derive
        run.real_checked = land.friction_answers.checked
        monkeypatch.setattr(land.friction_answers, "merged", run.merged)
        monkeypatch.setattr(land.friction_answers, "derive", run.derive)
        monkeypatch.setattr(land.friction_answers, "checked", run.checked)
        monkeypatch.setattr(land.friction_answers, "covers", run.covers)
        monkeypatch.setattr(land.accepted_records, "derive", run.accepted)
        # The backbone's reading, stood in for: the default branch `main` (COR-054).
        settled = land.friction_answers.default_branch
        monkeypatch.setattr(settled, "_read", {})

        def ask(explicit: str | None, _run: Any) -> Any:
            branch = settled.Branch("main", False, "origin/main", clone.base, None)
            return settled.Reading(branch, settled.Base("origin/main", clone.base, None, None))

        monkeypatch.setattr(settled, "_ask", ask)

        gh_module = sys.modules["_lib.gh"]
        for module in (
            gh_module,
            land,
            land.done_work,
            land.review_pr,
            land.issue_branch,
            land.head_programs,
        ):
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
            run.confined.append(kwargs.get("confined", False))
            run.reads_at_review.append(github._reads.get(github.head, 0))
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
    rc, out, err = run.authorised(capsys=capsys)
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


# ---- the authorisation names its head (#1760) ---------------------------------
# An authorisation to merge is for a named head (DEC-055 point 3). A `--yes` that
# names none would merge whatever head the run finds, one the person may not have
# been shown, so it is refused before anything is read, waited for or reviewed.


@pytest.mark.parametrize("extra", [(), ("--dry-run",), ("--no-wait",)])
def test_yes_without_a_named_head_is_refused_before_anything_runs(
    world, capsys, extra: tuple[str, ...]
) -> None:
    run = world()
    with pytest.raises(SystemExit) as stopped:
        run.land.main([str(ISSUE), "--yes", *extra])
    assert stopped.value.code == run.land.EXIT_UNREADABLE == 2
    err = capsys.readouterr().err
    assert err.splitlines()[-1].endswith(
        "error: --yes needs --expect-head <sha>: an authorisation to merge is for a named "
        f"head. Nothing was done. Run `land-work {ISSUE}` without --yes: its ready: line "
        "names the head and the command that merges it"
    )
    # No command that merges is offered with a head in it.
    assert run.github.head[:7] not in err
    assert run.github.calls == []
    assert run.invoked == []
    assert run.github.merges == []


def test_yes_with_a_named_head_merges_that_head(world, capsys) -> None:
    run = world()
    head = run.github.head
    rc, out, err = run.run("--yes", "--expect-head", head[:7], capsys=capsys)
    assert rc == 0, out + err
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"
    assert [m[-1] for m in run.github.merges] == [head]


def test_a_named_head_without_yes_stops_ready(world, capsys) -> None:
    """`--expect-head` alone authorises nothing: off a terminal the run stops on
    its `ready:` line, as without the flag."""
    run = world()
    head = run.github.head
    rc, out, _err = run.run("--expect-head", head, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-1].startswith(f"ready: {_short(head)} — CI passed")
    assert run.github.merges == []


# ---- the head -----------------------------------------------------------------


def test_an_unpushed_local_head_is_refused_with_the_push(world, capsys) -> None:
    run = world()
    run.commit("not-pushed.txt", push=False)
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert _steps(out)[0] == (
        f"head: {_short(run.github.head)} (PR #{PR}, {BRANCH}); local {BRANCH} is "
        f"1 commit behind it; this checkout is on main, not {BRANCH}"
    )


def _pushed_by_a_fork(run: _Run, name: str) -> str:
    """A new head of the PR from a fork, which this clone lacks: committed in another
    clone and kept on the base's remote only as the ref it keeps for the PR."""
    fork = run.work.parent / "fork"
    _git(run.work.parent, "clone", "-q", "--branch", BRANCH, "origin.git", str(fork))
    _git(fork, "config", "user.email", "octocat@example.com")
    _git(fork, "config", "user.name", "Octo Cat")
    sign_nothing(fork)
    (fork / name).write_text(name, encoding="utf-8")
    _git(fork, "add", name)
    _git(fork, "commit", "-q", "-m", f"add {name}")
    _git(fork, "push", "-q", "origin", f"HEAD:refs/pull/{PR}/head")
    return _git(fork, "rev-parse", "HEAD")


def test_a_fork_s_head_this_clone_lacks_is_fetched_by_the_ref_its_base_keeps(
    world, capsys, monkeypatch
) -> None:
    """Beside a local branch at another commit, a fork's head this clone lacks is
    fetched by the ref the base repository keeps for the PR, on the base's remote, and
    the local branch is compared with it."""
    run = world()
    monkeypatch.setattr(run.land.pr_head, "base_remote", lambda _base: "origin")
    run.github.cross_repository = True
    run.github.head = _pushed_by_a_fork(run, "from-the-fork.txt")
    run.github.checks[run.github.head] = [_GREEN]
    assert not run.land.pr_head.has_commit(run.github.head)
    _rc, out, err = run.authorised(capsys=capsys)
    assert _steps(out)[0] == (
        f"head: {_short(run.github.head)} (PR #{PR}, {BRANCH}); local {BRANCH} is "
        "1 commit behind it"
    ), out + err


@pytest.mark.parametrize(
    ("cross_repository", "fetch"),
    [(False, f"origin {BRANCH}"), (True, f"upstream refs/pull/{PR}/head")],
    ids=["same-repository", "fork"],
)
def test_a_head_no_fetch_brings_names_the_fetch_to_make(
    world, capsys, monkeypatch, cross_repository: bool, fetch: str
) -> None:
    """The fetch named is the one the run made: of the branch, on the remote it is
    pushed to, or for a fork's PR of the ref the base repository keeps, on the base's
    remote."""
    run = world()
    tip = run.github.head
    monkeypatch.setattr(run.land.pr_head, "base_remote", lambda _base: "upstream")
    run.github.cross_repository = cross_repository
    run.github.head = "d" * 40
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    assert out.splitlines()[-1] == (
        f"head: cannot tell whether local {BRANCH} (at {_short(tip)}) holds commits "
        f"PR #{PR}'s head ddddddd lacks: this clone does not have that head. Fetch it "
        f"(`git fetch {fetch}`) and run `land-work {ISSUE}` again"
    )


def test_a_draft_pr_is_refused(world, capsys) -> None:
    run = world()
    run.github.draft = True
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE == 1
    assert out.splitlines()[-1] == (
        f"head: refused — PR #{PR} is a draft; mark it ready with `review-work {ISSUE}`"
    )


# ---- the checks ---------------------------------------------------------------


def test_no_run_yet_is_waited_for_then_green_goes_on(world, capsys) -> None:
    run = world(checks=[[], [], _RUNNING, _GREEN])
    rc, out, err = run.authorised(capsys=capsys)
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
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert f"  ci: no check has been reported for {_short(new)} yet" in out
    assert run.sleeps == [20.0]
    assert _steps(out)[1].startswith(f"ci: passed on {_short(new)}")
    assert sorted(run.invoked) == sorted((name, new) for name in PANEL)


def test_a_failed_check_stops_before_the_review(world, capsys) -> None:
    run = world(checks=[_RED])
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised("--wait-minutes", "1", capsys=capsys)
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
    assert last.endswith(
        f"review it with `review-pr {ISSUE}` and merge it, on the person's authorisation, "
        f"with `done-work {ISSUE} --yes`: `done-work` does not wait for a check nobody "
        "reported, and passes a head with none wherever the base requires no check"
    )
    assert run.invoked == []


def test_no_wait_reads_the_checks_once(world, capsys) -> None:
    run = world(checks=[_RUNNING])
    rc, out, _err = run.authorised("--no-wait", capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == 3
    assert out.splitlines()[-1] == (
        f"ci: stopped — PR #{PR}'s head moved from {_short(pinned)} to ddddddd while its "
        f"checks were awaited. Nothing was reviewed or merged; `land-work {ISSUE}` checks "
        "and reviews the new head"
    )


# ---- the review beside the checks -----------------------------------------------


def _checks_again(run: _Run, readings: list[list[dict[str, Any]]]) -> None:
    """The head's checks read as `readings` from here on, as after a run of them again."""
    run.github.checks[run.github.head] = readings
    run.github._reads.pop(run.github.head, None)


def _ci_lines(out: str) -> list[str]:
    return [line for line in _steps(out) if line.startswith("ci:")]


def test_the_reviewers_start_once_the_named_checks_passed(world, capsys) -> None:
    """The reviewers run beside the rest, and the run stops ready only once every check
    has passed (DEC-063 point 8). The authorised run then merges on the same verdicts."""
    run = world(checks=[_ALL_RUNNING, _SUITE_RUNNING, _ALL_PASSED], start_after=_FIRST)
    head = _short(run.github.head)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY == 8
    assert _steps(out) == [
        f"head: {head} (PR #{PR}, {BRANCH})",
        f"ci: the remainder passed on {head} — the review starts beside the rest: {_THE_REST}",
        "review: 0 kept fresh, 2 re-run — all approved",
        f"ci: passed on {head}",
        f"{_STEP}: none",
    ]
    assert out.splitlines()[-1].startswith(f"ready: {head} — CI passed")
    # Each reviewer started on the second reading, with the suite still running.
    assert run.reads_at_review == [2, 2]
    assert run.github.merges == []

    run.invoked.clear()
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert run.invoked == []
    assert len(run.github.merges) == 1


def test_the_rest_are_waited_for_after_the_review(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _SUITE_RUNNING, _ALL_PASSED], start_after=_FIRST)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert run.reads_at_review == [1, 1]
    assert run.sleeps == [20.0]
    assert f"  ci: running on {_short(run.github.head)}: {_THE_REST}" in out.splitlines()


def test_every_check_passed_at_the_first_reading_needs_no_second_wait(world, capsys) -> None:
    run = world(checks=[_ALL_PASSED], start_after=_FIRST)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert _ci_lines(out) == [f"ci: passed on {_short(run.github.head)}"]


@pytest.mark.parametrize(
    ("start_after", "first"),
    [
        pytest.param((), "SUCCESS", id="a project that names none"),
        pytest.param(_FIRST, "SKIPPED", id="a check that was skipped"),
        pytest.param((*_FIRST, _SLICE_2), "SUCCESS", id="one of two still running"),
    ],
)
def test_otherwise_the_review_waits_for_every_check(
    world, capsys, start_after: tuple[str, ...], first: str
) -> None:
    run = world(checks=[_parts(first, "IN_PROGRESS"), _ALL_PASSED], start_after=start_after)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert run.reads_at_review == [2, 2]
    assert _ci_lines(out) == [f"ci: passed on {_short(run.github.head)}"]


_ONLY_DECIDED = [_check("decide the form", "SUCCESS")]


def test_a_named_check_that_has_not_started_is_read_again(world, capsys) -> None:
    """Every check reported can pass before the named one has started: that is no
    pass of it, and a part that then fails starts no reviewer."""
    run = world(checks=[_ONLY_DECIDED, _SUITE_RUNNING, _ALL_PASSED], start_after=_FIRST)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert run.reads_at_review == [2, 2]
    assert f"  ci: the remainder not reported for {_short(run.github.head)} yet" in out.splitlines()


def test_a_named_check_that_fails_once_it_has_started_starts_no_reviewer(world, capsys) -> None:
    run = world(checks=[_ONLY_DECIDED, _parts("FAILURE", "IN_PROGRESS")], start_after=_FIRST)
    rc, _out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert run.invoked == []


def test_a_name_no_check_bears_is_warned_of_and_lands_after_every_check(world, capsys) -> None:
    run = world(checks=[_ALL_PASSED], start_after=("lint",))
    head = _short(run.github.head)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert run.sleeps == [20.0]
    assert run.reads_at_review == [2, 2]
    assert (
        f"  warn: no check on {head} is named lint, which review.agents.start_after_checks "
        "names, so the review waited for every check reported"
    ) in out.splitlines()
    assert _ci_lines(out) == [f"ci: passed on {head}", f"ci: passed on {head}"]


def test_a_check_that_starts_after_the_review_began_is_still_waited_for(world, capsys) -> None:
    """A name read as unreported twice may be a workflow that starts late: the run reads
    the checks again after the review, and a failure there stops it before the merge."""
    run = world(
        checks=[_ONLY_DECIDED, _ONLY_DECIDED, _parts("FAILURE", "SUCCESS", "SUCCESS")],
        start_after=_FIRST,
    )
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        f"ci: failed on {_short(run.github.head)} — {_FIRST[0]} (FAILURE). Merge not started"
    )
    assert run.github.merges == []


@pytest.mark.parametrize(
    ("rollup", "failed"),
    [
        pytest.param(_parts("FAILURE", "IN_PROGRESS"), _FIRST[0], id="the named check"),
        pytest.param(_parts("IN_PROGRESS", "FAILURE"), _SLICE_1, id="a slice, before it passed"),
        pytest.param(_parts("SUCCESS", "FAILURE"), _SLICE_1, id="a slice, once it passed"),
    ],
)
def test_a_check_that_has_failed_starts_no_reviewer(
    world, capsys, rollup: list[dict[str, Any]], failed: str
) -> None:
    run = world(checks=[rollup], start_after=_FIRST)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        f"ci: failed on {_short(run.github.head)} — {failed} (FAILURE). "
        "Review and merge not started"
    )
    assert run.invoked == []
    assert run.github.comments == []
    assert run.github.merges == []


def test_a_suite_that_fails_beside_the_review_stops_before_the_merge(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _parts("SUCCESS", "FAILURE")], start_after=_FIRST)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        f"ci: failed on {_short(run.github.head)} — {_SLICE_1} (FAILURE). Merge not started"
    )
    assert len(run.github.comments) == 2
    assert run.github.merges == []


def test_a_check_run_again_on_the_same_head_keeps_every_verdict(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _parts("SUCCESS", "FAILURE")], start_after=_FIRST)
    head = run.github.head
    assert run.run(capsys=capsys)[0] == 1
    run.invoked.clear()
    _checks_again(run, [_SUITE_RUNNING, _ALL_PASSED])
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert run.invoked == []
    assert "review: 2 kept fresh, 0 re-run — all approved" in _steps(out)
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_push_that_fixes_the_failure_runs_the_stale_verdicts_again(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _parts("SUCCESS", "FAILURE")], start_after=_FIRST)
    assert run.run(capsys=capsys)[0] == 1
    run.invoked.clear()
    new = run.push_new_head("fix.txt")
    run.github.checks[new] = [_SUITE_RUNNING, _ALL_PASSED]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert sorted(run.invoked) == sorted((name, new) for name in PANEL)
    assert "review: 0 kept fresh, 2 re-run — all approved" in _steps(out)


def test_the_wait_for_the_rest_runs_as_long_again(world, capsys) -> None:
    run = world(checks=[_ALL_RUNNING, _SUITE_RUNNING], start_after=_FIRST)
    rc, out, _err = run.run("--wait-minutes", "1", capsys=capsys)
    assert rc == run.land.EXIT_CI_PENDING == 5
    assert run.reads_at_review == [2, 2]
    assert sum(run.sleeps) == 20 + 60
    assert out.splitlines()[-1].startswith(f"ci: still running on {_short(run.github.head)} after")


def test_a_dry_run_says_the_review_would_start_and_runs_none(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING], start_after=_FIRST)
    head = _short(run.github.head)
    rc, out, err = run.run("--dry-run", capsys=capsys)
    assert rc == 0, out + err
    assert _steps(out)[1:3] == [
        f"ci: (dry-run) the remainder passed on {head} — would start the review, then wait "
        f"up to 30m for the rest: {_THE_REST}",
        "review: (dry-run) would keep 0 fresh and run " + ", ".join(PANEL),
    ]
    assert out.splitlines()[-1] == (
        f"merge: (dry-run) would hand PR #{PR} at {head} to done-work once the checks pass "
        "and the review approves"
    )
    assert run.invoked == []
    assert run.github.comments == []


def test_a_run_with_no_wait_only_reads(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING], start_after=_FIRST)
    rc, out, _err = run.run("--no-wait", capsys=capsys)
    assert rc == 5
    assert run.invoked == []
    assert out.splitlines()[-1].startswith(
        f"ci: still running on {_short(run.github.head)} (--no-wait)"
    )


def test_a_run_authorised_up_front_runs_no_reviewer_before_every_check(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _ALL_PASSED], start_after=_FIRST)
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert run.reads_at_review == [2, 2]
    assert _ci_lines(out) == [f"ci: passed on {_short(run.github.head)}"]


def test_a_suite_that_fails_under_an_authorised_run_left_it_no_verdict_to_merge_on(
    world, capsys
) -> None:
    """Had the reviewers started beside the suite, this run's `[person]` verdict would
    stand unshown, and its identical re-run would find it at its start and merge on it
    (DEC-055 point 3). So it posts none, and the re-run holds at `ready:`."""
    run = world(checks=[_SUITE_RUNNING, _parts("SUCCESS", "FAILURE")], start_after=_FIRST)
    head = run.github.head
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    assert run.run("--yes", "--expect-head", head, capsys=capsys)[0] == 1
    assert run.github.comments == []

    _checks_again(run, [_ALL_PASSED])
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_READY == 8
    assert "came after this run's --yes was given" in out.splitlines()[-1]
    assert run.github.merges == []


def test_a_finding_posted_beside_the_rest_is_shown_before_the_ready_line(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _ALL_PASSED], start_after=_FIRST)
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    lines = out.splitlines()
    assert lines.index(_person_lines("code-reviewer")[0]) < len(lines) - 1
    assert f"{_FINDINGS}: 1, above" in lines
    assert run.github.merges == []


@pytest.mark.parametrize(
    ("rest", "code"),
    [
        pytest.param(_parts("SUCCESS", "FAILURE"), 1, id="a failed check"),
        pytest.param(_SUITE_RUNNING, 5, id="a wait that ran out"),
    ],
)
def test_a_stop_on_the_rest_shows_the_finding_the_run_posted(
    world, capsys, rest: list[dict[str, Any]], code: int
) -> None:
    """A later `--yes` would find this verdict at its start and merge on it, so the run
    that posted it shows it before it waits for the rest (DEC-055 point 3)."""
    run = world(checks=[_SUITE_RUNNING, rest], start_after=_FIRST)
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    rc, out, _err = run.run("--wait-minutes", "1", capsys=capsys)
    assert rc == code
    lines = out.splitlines()
    at = lines.index(_person_lines("code-reviewer")[0])
    assert lines[at : at + 3] == [*_person_lines("code-reviewer"), f"{_FINDINGS}: 1, above"]
    assert run.github.merges == []


def test_a_finding_posted_during_the_wait_for_the_rest_is_shown_too(world, capsys) -> None:
    """The findings shown before the wait are not the last word: what the run prints
    before it stops ready is each latest verdict as it stands then (DEC-055 point 3)."""
    run = world(checks=[_SUITE_RUNNING, _ALL_PASSED], start_after=_FIRST)
    head = run.github.head
    run.github.before(
        _nth(lambda a: a[:2] == ["pr", "view"] and "statusCheckRollup" in a[-1], 2),
        lambda: run.github.comments.append(_verdict(run, "reviewer", _PERSON, sha=head)),
    )
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    lines = out.splitlines()
    assert _person_lines("reviewer")[0] in lines
    assert "1 finding to judge above" in lines[-1]


def test_a_finding_posted_before_a_stop_on_the_rest_is_shown_by_the_next_run(world, capsys) -> None:
    """The same command run again after a stop on the rest shows the finding once more,
    and stops at `ready:` for the person."""
    run = world(checks=[_SUITE_RUNNING, _parts("SUCCESS", "FAILURE")], start_after=_FIRST)
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    assert run.run(capsys=capsys)[0] == 1

    run.invoked.clear()
    _checks_again(run, [_ALL_PASSED])
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 8
    assert run.invoked == []
    assert _person_lines("code-reviewer")[0] in out.splitlines()
    assert run.github.merges == []


def test_a_head_that_moves_beside_the_review_stops_before_the_merge(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _SUITE_RUNNING], start_after=_FIRST)
    pinned = run.github.head
    run.github.before(
        _nth(lambda a: a[:2] == ["pr", "view"] and "statusCheckRollup" in a[-1], 2),
        lambda: setattr(run.github, "head", "d" * 40),
    )
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 3
    assert out.splitlines()[-1] == (
        f"ci: stopped — PR #{PR}'s head moved from {_short(pinned)} to ddddddd while its "
        f"checks were awaited. Nothing was merged; `land-work {ISSUE}` checks and reviews "
        "the new head"
    )
    assert run.github.merges == []


def test_a_pr_that_merged_beside_the_review_is_completed(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _SUITE_RUNNING], start_after=_FIRST)

    def merged() -> None:
        run.github.state = "MERGED"
        run.github.merge_commit = "c" * 40

    run.github.before(
        _nth(lambda a: a[:2] == ["pr", "view"] and "statusCheckRollup" in a[-1], 2), merged
    )
    rc, out, err = run.run(capsys=capsys)
    assert f"ci: PR #{PR} has merged meanwhile" in _steps(out), out + err
    assert run.github.merges == []
    assert rc in (run.land.EXIT_MERGED, run.land.EXIT_READY)


def test_changes_requested_beside_the_suite_names_the_check_that_failed(world, capsys) -> None:
    """Both reach one fix round, and a stop is one line the fix round is handed."""
    run = world(checks=[_SUITE_RUNNING, _parts("SUCCESS", "FAILURE")], start_after=_FIRST)
    run.answers["code-reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        "review: changes requested by code-reviewer — the blocking findings are above, and a "
        f"check failed on {_short(run.github.head)}: {_SLICE_1} (FAILURE); merge not started"
    )


@pytest.mark.parametrize(
    "rollup",
    [pytest.param(_SUITE_RUNNING, id="running"), pytest.param(_ALL_PASSED, id="passed")],
)
def test_changes_requested_beside_the_suite_adds_nothing_where_no_check_failed(
    world, capsys, rollup: list[dict[str, Any]]
) -> None:
    run = world(checks=[_SUITE_RUNNING, rollup], start_after=_FIRST)
    run.answers["code-reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        "review: changes requested by code-reviewer — the blocking findings are above; "
        "merge not started"
    )


def test_a_stop_on_changes_requested_stands_where_the_checks_cannot_be_read(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _SUITE_RUNNING], start_after=_FIRST)
    run.answers["code-reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    run.github.fails.append(
        _nth(lambda a: a[:2] == ["pr", "view"] and "statusCheckRollup" in a[-1], 2)
    )
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1] == (
        "review: changes requested by code-reviewer — the blocking findings are above; "
        "merge not started"
    )


def test_the_merge_gate_still_reads_every_check(world, capsys) -> None:
    """A check that fails after the run read every check as passed is `done-work`'s to
    refuse, whatever started the reviewers."""
    run = world(
        checks=[_SUITE_RUNNING, _ALL_PASSED, _parts("SUCCESS", "SUCCESS", "FAILURE")],
        start_after=_FIRST,
    )
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-1].startswith("merge: refused")
    assert run.github.merges == []


def test_a_queue_is_read_once_though_the_checks_are_waited_for_twice(world, capsys) -> None:
    run = world(checks=[_SUITE_RUNNING, _ALL_PASSED], start_after=_FIRST)
    run.github.merge_state = "BEHIND"
    run.github.queue = True
    after_the_second_wait: list[int] = []
    run.github.before(
        lambda a: a[:2] == ["pr", "view"] and a[-1].endswith(",author"),
        lambda: after_the_second_wait.append(run.github.queue_reads),
    )
    run.run(capsys=capsys)
    assert after_the_second_wait == [1]


@pytest.mark.parametrize(
    "value", ["the remainder", ["the remainder", 7], {"the remainder": True}, None]
)
def test_a_value_that_is_no_list_of_names_names_no_check(land, value: object) -> None:
    config = {"review": {"agents": {"start_after_checks": value}}}
    args = land._parser().parse_args([str(ISSUE)])
    assert land._checks_that_start_review(args, config) == ()


# ---- the review ---------------------------------------------------------------


def test_changes_requested_stops_before_the_merge_with_its_findings(world, capsys) -> None:
    run = world()
    run.answers["code-reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    rc, out, _err = run.authorised(capsys=capsys)
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
    assert run.authorised(capsys=capsys)[0] == 1
    run.invoked.clear()
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == 3
    assert run.invoked == []
    assert out.splitlines()[-1] == (
        f"review: stopped — PR #{PR}'s head is {_short(run.github.head)}, not "
        f"{_short(pinned)}, the head this run pinned. Nothing was merged; "
        f"`land-work {ISSUE}` checks and reviews the new head"
    )


def test_a_head_that_moves_between_the_review_and_the_merge_merges_nothing(world, capsys) -> None:
    """done-work's lookup — the third — finds the PR moved after the review:
    done-work refuses the pinned head it no longer has."""
    run = world()
    pinned = run.github.head
    run.github.before(_nth(_pr_list, 3), lambda: run.push_new_head("later.txt"))
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == 3
    assert run.github.merges == []
    assert out.splitlines()[-1] == (
        f"merge: stopped — error: PR #{PR}'s head is {_short(run.github.head)}, not "
        f"{_short(pinned)}, the head this run was asked to land: its checks and review "
        "were for that head. Nothing was posted or merged, and #42 stays where it is."
    )


def test_human_review_mode_runs_no_reviewer_and_done_work_gates(world, capsys) -> None:
    run = world(mode="human")
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == 1
    assert run.invoked == []
    steps = _steps(out)
    assert steps[2] == (
        "review: human review mode (project default) — no reviewer agent to run; the "
        "approval is done-work's gate"
    )
    assert steps[4] == f"merge: refused — [refused] approval gate not satisfied for PR #{PR}."


# ---- no local reviewer of the project's own (#1934) ---------------------------


def _contribute(run: _Run, monkeypatch: pytest.MonkeyPatch, reviewer: str) -> None:
    """An installed capability contributes `reviewer` to a PR that closes an
    issue in the `design` workstream (DEC-032 point D2), and the agent is
    deployed. review-pr and done-work collect it alike."""
    rc = sys.modules["_lib.review_contributions"]
    rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer=reviewer,
    )
    collection = rc.ContributionCollection(rules=(rule,))
    for module in (run.land.review_pr, run.land.done_work):
        monkeypatch.setattr(module, "collect_contributions", lambda _root: collection)
    (run.work / ".claude" / "agents" / f"{reviewer}.md").write_text(
        f"# {reviewer}\n", encoding="utf-8"
    )
    run.github.labels.append("workstream:design")


def test_a_contributed_reviewer_reviews_where_the_project_registers_none_of_its_own(
    world, capsys, monkeypatch
) -> None:
    """Only a remote reviewer is registered, and a capability contributes one the
    PR requires: the review step runs it, and the PR lands on its approval and
    the remote one (DEC-032 point D4). It used to skip the review."""
    run = world(remote=("review-bot",), local=())
    _contribute(run, monkeypatch, "design-reviewer")
    head = run.github.head
    run.github.comments.append(_remote_verdict(run, "review-bot", "Fine.", sha=head))
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert run.invoked == [("design-reviewer", head)]
    assert "review: 0 kept fresh, 1 re-run — all approved" in _steps(out)
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_pr_that_requires_no_local_reviewer_leaves_the_approval_to_the_gate(
    world, capsys
) -> None:
    """Only a remote reviewer is registered, and no capability contributes one:
    the review step runs nothing, says so, and the gate reads the remote verdict."""
    run = world(remote=("review-bot",), local=())
    head = run.github.head
    run.github.comments.append(_remote_verdict(run, "review-bot", "Fine.", sha=head))
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert run.invoked == []
    assert "review: no local reviewer is required — the approval is done-work's gate" in _steps(out)
    assert [merge[-1] for merge in run.github.merges] == [head]


# ---- the merge ----------------------------------------------------------------


def test_a_queued_pr_passes_done_works_4_through(world, capsys) -> None:
    run = world()
    run.github.queue = True
    rc, out, _err = run.authorised("--no-wait", capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    assert run.authorised("--no-wait", capsys=capsys)[0] == 5
    rc, out, err = run.authorised("--no-wait", capsys=capsys)
    assert rc == 5  # the second reading: still no run
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert run.sleeps == []


def test_a_rerun_waits_for_nothing_and_re_runs_no_fresh_verdict(world, capsys) -> None:
    """A reviewer could not run: the re-run keeps the verdict the other posted,
    runs only the missing one, and waits for no check already green."""
    run = world()
    run.answers["code-reviewer"] = None
    assert run.authorised(capsys=capsys)[0] == 6
    assert sorted(run.invoked) == sorted((name, run.github.head) for name in PANEL)
    run.invoked.clear()
    del run.answers["code-reviewer"]
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert run.invoked == [("code-reviewer", run.github.head)]
    assert "review: 1 kept fresh, 1 re-run — all approved" in _steps(out)
    assert run.sleeps == []


def test_a_rerun_after_changes_requested_reviews_the_fix(world, capsys) -> None:
    run = world()
    run.answers["code-reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    assert run.authorised(capsys=capsys)[0] == 1
    fixed = run.push_new_head("fix.txt")
    run.github.checks[fixed] = [_GREEN]
    run.answers["code-reviewer"] = ("APPROVED", "Fixed.")
    run.invoked.clear()
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    # A change since makes both verdicts stale: both review the fix.
    assert sorted(run.invoked) == sorted((name, fixed) for name in PANEL)
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"


def test_a_rerun_after_the_head_moved_lands_the_new_head(world, capsys) -> None:
    run = world()
    run.github.before(_nth(_pr_list, 2), lambda: run.push_new_head("late.txt"))
    assert run.authorised(capsys=capsys)[0] == 3
    run.github.checks[run.github.head] = [_GREEN]
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert sorted(run.invoked) == sorted((name, run.github.head) for name in PANEL)


def test_a_rerun_after_the_queue_merged_completes_the_issue(world, capsys) -> None:
    run = world()
    run.github.queue = True
    assert run.authorised("--no-wait", capsys=capsys)[0] == 4
    run.github.state = "MERGED"
    run.github.queued = False
    rc, out, err = run.authorised(capsys=capsys)
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
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert _steps(out)[0] == f"head: {_short(run.github.head)} (PR #{PR}, {BRANCH})"
    assert out.splitlines()[-1] == f"merge: merged as {'c' * 7}"
    # Read once for the run: review-pr and done-work are handed land-work's reading.
    assert _open_pr_readings(run) == 1


def test_several_branches_none_open_completes_a_merged_pr_from_the_issue(world, capsys) -> None:
    run = world()
    _git(run.work, "branch", _STALE, "main")
    run.github.state = "MERGED"
    rc, out, err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    assert run.authorised("--no-wait", capsys=capsys)[0] == 0
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    assert run.authorised(capsys=capsys)[0] == 2
    assert run.github.merges == []
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    head = run.github.head
    assert sorted(run.invoked) == sorted((name, head) for name in PANEL)
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_done_works_own_lookup_without_an_answer_merges_nothing(world, capsys) -> None:
    """land-work, then review-pr, found the PR; done-work's lookup — the third
    — gets no answer, and done-work stops rather than look for a merged PR."""
    run = world()
    run.github.fails.append(_nth(_pr_list, 3))
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_RETRY == 7
    assert out.splitlines()[-1] == (
        f"merge: not completed — error: PR #{PR} for '{BRANCH}' is open, and this run was "
        "asked only to complete a PR that has merged. Nothing was changed. Run "
        f"`land-work {ISSUE}` again to check, review and land it"
    )
    assert run.github.merges == []
    assert run.after_merge == []
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err


# ---- how done-work's run ended, not its exit code -----------------------------


def test_a_merge_whose_commit_cannot_be_read_is_still_merged(world, capsys) -> None:
    """done-work's run says merged only once GitHub reports it merged; the
    merge commit is only what the line names."""
    run = world()
    run.github.fails.append(lambda a: a[:2] == ["pr", "view"] and a[-1] == "mergeCommit")
    rc, out, err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_RETRY == 7
    assert out.splitlines()[-1] == (
        f"merge: merged as {'c' * 7}, but a step after the merge failed: [warn] PR merged "
        f"but move-issue exited 1. The merge is durable; re-run `move-issue {ISSUE} --to done` "
        f"to complete the lifecycle transition. — run `land-work {ISSUE}` again to complete "
        f"#{ISSUE}"
    )
    monkeypatch.setattr(run.land.done_work, "_invoke_move_issue", lambda *a, **k: 0)
    rc, out, err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised("--no-wait", capsys=capsys)
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
    rc, out, _err = run.authorised("--no-wait", capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert sorted(run.invoked) == sorted((name, pinned) for name in PANEL)
    assert len(run.github.comments) == len(PANEL)
    assert all(f"sha={pinned}" in comment["body"] for comment in run.github.comments)
    assert run.github.merges == []
    assert out.splitlines()[-1] == (
        f"review: stopped — PR #{PR}'s head is {_short(run.github.head)}, not "
        f"{_short(pinned)}, the head this run pinned. Nothing was merged; "
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert run.github.state == "OPEN"
    assert [merge[-1] for merge in run.github.merges] == [pinned]
    assert out.splitlines()[-1] == (
        f"merge: stopped — PR #{PR}'s head moved from {_short(pinned)} to "
        f"{_short(run.github.head)} before the merge. Nothing was merged; "
        f"`land-work {ISSUE}` checks and reviews the new head"
    )


def test_a_head_pushed_as_the_gate_reads_its_checks_is_not_passed_unchecked(world, capsys) -> None:
    """No check has reported on the new head yet. Where the base requires
    checks, `done-work`'s gate takes that for pending, so no merge is asked
    for (#1965)."""
    run = world()
    run.github.required = ["checks"]

    def rollup_read(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1] == "statusCheckRollup"

    run.github.before(rollup_read, lambda: run.push_new_head("racing.txt"))
    rc, _out, err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert (run.github.state, run.github.merges) == ("OPEN", [])
    assert "failing/pending: checks (EXPECTED)" in err


def test_a_head_the_host_reads_as_behind_stops_at_the_checks_with_the_merge_to_make(
    world, capsys
) -> None:
    """A host that merges only a branch up to date with its base reads the branch as
    behind it: the run stops at the checks, before the review and the ready stop,
    with the merge of the base to make (DEC-064 point 1)."""
    run = world()
    run.github.merge_state = "BEHIND"
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert run.invoked == [] and run.github.merges == []
    assert out.splitlines()[-1] == (
        f"ci: stopped — the host merges only a branch up to date with main, and reads "
        f"PR #{PR} as behind it. Merge main into {BRANCH} (`git merge origin/main`), push, "
        f"and run `land-work {ISSUE}` again"
    )


def test_a_base_that_merges_through_a_queue_is_not_stopped_at_the_checks(world, capsys) -> None:
    """A queue builds the merge with the base itself, so a branch the host reads as
    behind goes on to its review."""
    run = world()
    run.github.merge_state = "BEHIND"
    run.github.queue = True
    run.authorised(capsys=capsys)
    assert run.invoked != []


def test_a_queue_that_cannot_be_read_at_the_checks_is_said_and_the_run_goes_on(
    world, capsys
) -> None:
    """Whether the base merges through a queue cannot be read: one line says so, the
    run goes on to its review, and the merge step names the merge when the host
    refuses it (DEC-064 point 2)."""
    run = world()
    run.github.merge_state = "BEHIND"
    run.github.queue_unreadable = 1
    rc, out, _err = run.authorised(capsys=capsys)
    assert (
        f"  ci: PR #{PR} reads as behind main, and whether main merges through a queue could "
        "not be read, so the run goes on: the merge step names the merge of main if the host "
        "refuses the merge for it"
    ) in out.splitlines()
    assert run.invoked != []
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1].startswith(
        "merge: stopped — the host merges only a branch up to date with main"
    )


def test_the_queue_is_read_once_while_the_checks_are_awaited(world, capsys) -> None:
    """A PR read as behind a base that merges through a queue goes on, and the queue
    is read once a run, not on every poll of the checks."""
    run = world(checks=[_RUNNING, _RUNNING, _GREEN])
    run.github.merge_state = "BEHIND"
    run.github.queue = True
    at_review: list[int] = []

    def review_reads_the_head(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1] == "headRefOid,baseRefOid"

    run.github.before(review_reads_the_head, lambda: at_review.append(run.github.queue_reads))
    run.authorised(capsys=capsys)
    assert run.github._reads[run.github.head] >= 3
    assert at_review == [1]


def test_a_reading_not_settled_goes_on_and_the_merge_step_names_the_merge(world, capsys) -> None:
    """GitHub answers UNKNOWN before it has worked the state out: the run goes on past
    the checks, and where the host then refuses the merge of a head behind its base,
    the merge step names the merge (DEC-064 point 2)."""
    run = world()
    run.github.merge_state = "BEHIND"
    run.github.unsettled = 1
    rc, out, _err = run.authorised(capsys=capsys)
    assert run.invoked != []
    assert len(run.github.merges) == 1
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"merge: stopped — the host merges only a branch up to date with main, and reads "
        f"PR #{PR} as behind it. Merge main into {BRANCH} (`git merge origin/main`), push, "
        f"and run `land-work {ISSUE}` again"
    )


def test_a_merge_refused_on_a_head_behind_a_queued_base_names_no_merge(world, capsys) -> None:
    """A queue builds the merge with the base itself, so a refused request on a head
    read as behind names no merge at the merge step either, as at the checks."""
    run = world()
    run.github.queue = True

    def behind() -> None:
        run.github.merge_state = "BEHIND"

    def review_reads_the_head(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1] == "headRefOid,baseRefOid"

    run.github.before(review_reads_the_head, behind)
    rc, out, _err = run.authorised(capsys=capsys)
    assert run.github.state == "OPEN"
    assert rc == run.land.EXIT_RETRY
    assert out.splitlines()[-1].startswith("merge: not merged — ")
    assert "git merge" not in out.splitlines()[-1]


def test_a_fork_s_behind_stop_names_the_merge_from_the_base_s_remote(
    world, capsys, monkeypatch
) -> None:
    """A PR from a fork: its branch's remote is the fork's, so the merge of the base
    to make is named from the base's remote."""
    run = world()
    _git(run.work, "remote", "add", "fork", "../origin.git")
    _git(run.work, "config", f"branch.{BRANCH}.pushRemote", "fork")
    monkeypatch.setattr(run.land.pr_head, "base_remote", lambda _base: "upstream")
    run.github.merge_state = "BEHIND"
    run.github.cross_repository = True
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"ci: stopped — the host merges only a branch up to date with main, and reads "
        f"PR #{PR} as behind it. Merge main into {BRANCH} (`git merge upstream/main`), push, "
        f"and run `land-work {ISSUE}` again"
    )
    # From the base's own repository, the branch's remote is the base's too.
    run.github.cross_repository = False
    _rc, out, _err = run.authorised(capsys=capsys)
    assert "(`git merge fork/main`)" in out.splitlines()[-1]


def test_a_merge_the_host_refuses_on_a_head_behind_its_base_names_the_merge(world, capsys) -> None:
    """The base moved on after the checks: the host refuses the merge, and a run again
    would fail the same way. The run stops at exit 1 with the merge of the base to
    make (DEC-064 point 1), not exit 7."""
    run = world()

    def behind() -> None:
        run.github.merge_state = "BEHIND"

    def review_reads_the_head(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1] == "headRefOid,baseRefOid"

    run.github.before(review_reads_the_head, behind)
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert run.github.state == "OPEN"
    assert len(run.github.merges) == 1
    assert out.splitlines()[-1] == (
        f"merge: stopped — the host merges only a branch up to date with main, and reads "
        f"PR #{PR} as behind it. Merge main into {BRANCH} (`git merge origin/main`), push, "
        f"and run `land-work {ISSUE}` again"
    )


def test_a_head_review_pr_cannot_read_stops_unreadable_not_moved(world, capsys) -> None:
    run = world()
    head = run.github.head
    run.github.fails.append(lambda a: a[:2] == ["pr", "view"] and a[-1] == "headRefOid,baseRefOid")
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised("--no-wait", capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    assert out.splitlines()[-1] == (
        f"ci: PR #{PR}'s checks could not be read: HTTP 502: Bad Gateway. Run "
        f"`land-work {ISSUE}` again"
    )
    assert run.invoked == []


def test_checks_done_work_cannot_read_stop_the_merge_unreadable(world, capsys) -> None:
    """The checks passed on land-work's reading; done-work's own reading of them
    gets no answer, and its gate refuses rather than read none as green (#1946)."""
    run = world()
    run.github.fails.append(lambda a: a[:2] == ["pr", "view"] and a[-1] == "statusCheckRollup")
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE == 2
    assert out.splitlines()[-1] == (
        f"merge: stopped — [refused] CI-status gate for PR #{PR}: its checks could not be "
        "read (HTTP 502: Bad Gateway). Nothing was changed."
    )
    assert run.github.merges == []
    assert run.after_merge == []


def test_checks_unreadable_once_are_read_again_while_waiting(world, capsys) -> None:
    run = world()
    run.github.fails.append(lambda a: a[:2] == ["pr", "view"] and "statusCheckRollup" in a[-1])
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert "  ci: the checks could not be read: HTTP 502: Bad Gateway" in out
    assert run.sleeps == [20.0]


# ---- the review's findings ----------------------------------------------------


def test_a_block_is_reported_even_when_another_reviewer_could_not_run(world, capsys) -> None:
    run = world()
    run.answers["reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    run.answers["code-reviewer"] = None
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, err = run.authorised(capsys=capsys)
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
    """A head whose changes since the authorised one lie outside the answers
    is a head nobody authorised: the run stops, naming the changes (DEC-055 point 3)."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("after.txt")
    rc, out, _err = run.run("--yes", "--expect-head", authorised[:12], capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    assert out.splitlines()[-1] == (
        f"head: stopped — PR #{PR}'s head is {_short(head)}, not "
        f"{authorised[:7]}, the head the merge was authorised for: an authorisation covers a "
        "later head only where every change since lies inside answer files the change "
        "adds, a clean merge of main counting as none, and these changes do "
        f"not: after.txt ({head[:7]}: added). "
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
        f"{_short(authorised)} lies inside answer files the change adds, a "
        "clean merge of main counting as none"
    )


def test_an_authorisation_covers_a_later_head_of_re_resolved_answers(world, capsys) -> None:
    """Every change since the authorised head lies inside the answers: the run
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
    run.written = [INSTALL, {**DEFERRED, "asked": False}]
    run.cover = True
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 document left "
        "out of date and 1 answer this change was not asked for above, for information; the "
        f"authorisation for {_short(authorised)} "
        f"covers {_short(head)} only where nothing there needs a person, and it holds 1 answer "
        f"this change was not asked for; {_merge_line(run)}"
    )
    assert run.github.merges == []


def _covered_head(run: _Run) -> tuple[str, str]:
    """The PR's head authorised, and a later one it covers, its checks green."""
    authorised = run.github.head
    head = run.push_new_head("answers.txt")
    run.github.checks[head] = [_GREEN]
    run.cover = True
    return authorised, head


def test_a_covered_head_leaving_out_of_date_what_the_head_authorised_did_not_stops_ready(
    world, capsys
) -> None:
    """A deferral first written at a later head: the person was told what the head
    authorised leaves, and a line printed just before the merge is no telling on an
    authorisation given up front (DEC-065 point 4)."""
    run = world()
    authorised, head = _covered_head(run)
    run.written = [INSTALL, DEFERRED]
    run.written_at = {authorised: [INSTALL]}
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 document left "
        f"out of date above, for information; the authorisation for {_short(authorised)} "
        f"covers {_short(head)} only where nothing there needs a person, and it holds "
        f"something left out of date that {_short(authorised)} did not leave; "
        f"{_merge_line(run)}"
    )
    assert run.github.merges == []


def test_a_covered_head_that_rewords_a_deferral_stops_ready(world, capsys) -> None:
    """The words name the follow-up, so other words are a follow-up nobody was told."""
    run = world()
    authorised, _head = _covered_head(run)
    run.written = [DEFERRED]
    run.written_at = {authorised: [{**DEFERRED, "reason": "Rewritten later."}]}
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert "something left out of date that" in out.splitlines()[-1]


def test_a_covered_head_leaving_the_same_out_of_date_merges(world, capsys) -> None:
    run = world()
    authorised, _head = _covered_head(run)
    run.written = [INSTALL, DEFERRED]
    rc, out, err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_MERGED, out + err


def test_a_covered_head_that_fixed_what_was_left_out_of_date_merges(world, capsys) -> None:
    """Fewer lines tell the person nothing new, and leaving nothing runs no check."""
    run = world()
    authorised, _head = _covered_head(run)
    run.written = [INSTALL]
    run.written_at = {authorised: None}
    rc, out, err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_MERGED, out + err


def test_a_covered_head_whose_earlier_answers_cannot_be_read_stops_ready(world, capsys) -> None:
    run = world()
    authorised, _head = _covered_head(run)
    run.written = [DEFERRED]
    run.written_at = {authorised: None}
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert (
        f"it holds something left out of date, with the answers at {_short(authorised)} unread"
    ) in out.splitlines()[-1]
    assert run.github.merges == []


def test_expect_head_takes_a_commit_id_only(land) -> None:
    with pytest.raises(SystemExit):
        land._parser().parse_args([str(ISSUE), "--expect-head", "not-a-sha"])


# ---- the answers the change wrote (DEC-055, DEC-065) -------------------------------


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
)


def _answers_world(world: Callable[..., _Run], *, listed: bool = False) -> _Run:
    """A change that wrote two answers; `listed`: the description carries the list
    of them an earlier run wrote (DEC-055 point 1)."""
    run = world()
    run.written = [INSTALL, DEFERRED]
    if listed:
        run.github.body = f"{_PR_BODY}\n{run.earlier_list()}\n"
    return run


#: What the person who authorises the merge is told of `_answers_world`'s answers,
#: as information: the one document left out of date, with the deferral's words.
TOLD = [
    '  Left out of date: docs/cli.md, for changes to src/cli/**: "Rewritten with the redesign."'
]
#: What the step's line adds where the description carried an earlier run's list.
_REMOVED = " — removed the list of answers an earlier run left from the pull request's description"


def _ready_line(
    run: _Run, told: str = ", 1 document left out of date above, for information"
) -> str:
    head = run.github.head
    return (
        f"ready: {_short(head)} — CI passed, all required verdicts approved{told}; merge with: "
        f"pkit pm land-work {ISSUE} --yes --expect-head {head}"
    )


def test_what_the_person_is_told_is_printed_above_ready_and_no_list_is_written(
    world, capsys
) -> None:
    """The answers are read from the change check at the pinned head; the person is
    told what is left out of date, directly above the `ready:` line, which is last.
    An answer that holds is not told, and the description is left as it was
    (DEC-065 points 1 and 4)."""
    run = _answers_world(world)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert f"{_STEP}: 2" in lines
    assert lines[-2:] == [*TOLD, _ready_line(run)]
    assert INSTALL["reason"] not in out
    assert run.github.bodies == [] and run.github.merges == []


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
#: A target the change revisited by changing it: the reviewer's to check, never told.
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
    16, #1703); a target the change revisited by changing it is not told."""
    run = _answers_world(world)
    run.written = [INSTALL, DEFERRED, REVISIT_UPDATED, REVISIT_DEFERRED]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert "tests/test_latency.py" not in out
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


def test_each_answer_a_person_decided_is_told_above_ready(world, capsys) -> None:
    """An answer the change check did not ask for, and a reason for having no anchors,
    were a person's to decide, or their delegate's (COR-064): each is told with its
    words, and the `ready:` line counts them (DEC-065 point 4)."""
    run = world()
    run.written = [
        INSTALL,
        {**DEFERRED, "asked": False},
        _answer("docs/new.md", "A rule of the method.", answer="unanchored", asked=False),
    ]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-4:] == [
        *TOLD,
        "  Not asked for by this change: docs/cli.md, for changes to src/cli/**, out of date, "
        'fixed later: "Rewritten with the redesign."',
        '  Not asked for by this change: docs/new.md, not tied to anything: "A rule of the '
        'method."',
        _ready_line(
            run,
            ", 1 document left out of date and 2 answers this change was not asked for above, "
            "for information",
        ),
    ]


def test_the_ready_line_counts_what_it_tells(land) -> None:
    end = land._AnswersEnd
    assert end(targets=1).phrase() == ", 1 target of a link left out of date above, for information"
    assert end(updated=1, left=2, targets=3).phrase() == (
        ", what changed in 1 updated document, 2 documents left out of date and 3 targets of a "
        "link left out of date above, for information"
    )
    assert end(left=1).phrase() == ", 1 document left out of date above, for information"
    assert (
        end(unasked=1).phrase() == ", 1 answer this change was not asked for above, for information"
    )
    assert end().phrase() == ""


def test_a_pr_into_another_branch_is_derived_against_that_branch(world, capsys) -> None:
    """The PR's base is always named to the change check, which resolves it as it
    resolves every branch named a base — never `$PKIT_CHECK_BASE`."""
    run = world()
    run.github.base_branch = "integration/7-x"
    run.run(capsys=capsys)
    assert run.derived == [(run.github.head, "integration/7-x")]


def test_a_list_an_earlier_run_left_is_removed_and_said(world, capsys) -> None:
    """Pull requests opened before DEC-065 carry a list: land-work removes it, the
    rest of the description as it was and the footer last, and says so. The
    identical run finds nothing to remove."""
    run = _answers_world(world, listed=True)
    # As the host may hand it back: other line endings, trailing spaces.
    run.github.body = run.github.body.replace("\n", "  \r\n")
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert f"{_STEP}: 2{_REMOVED}" in out.splitlines()
    (written,) = run.github.bodies
    assert _HEADING not in written and "pkit-friction-answers" not in written
    assert "Rewritten with the redesign." not in written
    assert written.replace("  \n", "\n").startswith(_PR_BODY.rstrip("\n"))
    assert written.rstrip("\n").endswith("<!-- pkit-provenance:end -->")
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert f"{_STEP}: 2" in out.splitlines() and len(run.github.bodies) == 1


def test_a_list_an_earlier_run_wrote_under_the_former_heading_is_removed(world, capsys) -> None:
    run = _answers_world(world)
    earlier = run.earlier_list().replace(_HEADING, _FORMER_HEADING, 1)
    run.github.body = f"{_PR_BODY}\n{earlier}\n"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert f"{_STEP}: 2{_REMOVED}" in out.splitlines()
    (written,) = run.github.bodies
    assert _FORMER_HEADING not in written and _HEADING not in written


def test_a_dry_run_removes_nothing(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    rc, out, err = run.run("--dry-run", capsys=capsys)
    assert rc == 0, out + err
    assert (
        f"{_STEP}: 2 — would remove the list of answers an earlier run left from the pull "
        "request's description"
    ) in out.splitlines()
    assert run.github.bodies == [] and run.github.merges == []


def test_no_answers_removes_the_list_an_earlier_run_left(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    run.written = []
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert f"{_STEP}: none{_REMOVED}" in out.splitlines()
    (written,) = run.github.bodies
    assert _HEADING not in written and written.startswith(_PR_BODY)
    assert [merge[-1] for merge in run.github.merges] == [run.github.head]


@pytest.mark.parametrize(
    "unread",
    [
        "`pkit friction check --json --head x`: it exited 1: Error: no such base",
        "the base origin/main could not be fetched: Could not resolve host",
    ],
)
def test_answers_that_cannot_be_read_stop_unreadable(world, capsys, unread) -> None:
    run = _answers_world(world, listed=True)
    run.unread = unread
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE == 2
    assert out.splitlines()[-1] == (
        f"{_STEP}: the change check's answers at {_short(run.github.head)} could not be read — "
        f"{unread}. Nothing was merged; run `land-work {ISSUE}` again"
    )
    assert run.github.bodies == [] and run.github.merges == []


@pytest.mark.parametrize(
    "reason",
    ["Holds once this fixes #77.", "The footer: <!-- pkit-provenance:start -->", "x" * 70000],
    ids=["closing reference", "comment delimiter", "past the host's limit"],
)
def test_no_word_of_an_answer_stops_the_merge(world, capsys, reason) -> None:
    """With no list in the description, an answer's words close no issue, hide no
    marker and fill no description: none is refused (DEC-065 point 5)."""
    run = _answers_world(world)
    run.written = [INSTALL, _answer("docs/api.md", reason)]
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert run.github.bodies == []
    assert [merge[-1] for merge in run.github.merges] == [run.github.head]


def test_a_removal_that_fails_merges_nothing_and_is_a_retry(world, capsys) -> None:
    """The host may keep a write it answered with an error: the run merges nothing,
    and running again finds no list there and merges."""
    run = _answers_world(world, listed=True)

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
        f"{_STEP}: the list of answers an earlier run left could not be removed from PR "
        f"#{PR}'s description: HTTP 502: Bad Gateway. Nothing was merged; run "
        f"`land-work {ISSUE}` again"
    )
    assert run.github.merges == []
    # The host kept it: the identical run finds no list there and merges.
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert f"{_STEP}: 2" in out.splitlines()
    assert run.github.merges[-1][-1] == head


@pytest.mark.parametrize("listed", [False, True])
def test_a_dry_run_that_fails_is_a_retry_whether_or_not_the_run_removed_a_list(
    world, capsys, monkeypatch, listed
) -> None:
    """A change with answers stops on a failure as any other does: what the run
    removed holds no next step."""
    run = _answers_world(world, listed=listed)

    def failing(argv: list[str], **kwargs: Any) -> Any:
        raise RuntimeError("gh timed out")

    monkeypatch.setattr(run.land.done_work, "run", failing)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_RETRY
    assert (_REMOVED in out) is listed
    assert out.splitlines()[-1].startswith("merge: not merged — done-work failed")


# -- the authorisation, where the change wrote answers (DEC-055 point 3) --


@pytest.mark.parametrize("listed", [False, True])
def test_yes_merges_a_change_with_answers_as_any_other(world, capsys, listed) -> None:
    """A change with answers merges under the same authorisation as any other: a
    `--yes` run prints what the person is told, before done-work merges, and merges
    in the same run."""
    run = _answers_world(world, listed=listed)
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    lines = out.splitlines()
    assert lines.index(TOLD[0]) < lines.index(f"merge: merged as {'c' * 7}")
    assert len(run.github.bodies) == (1 if listed else 0)
    assert run.github.merges[-1][-1] == run.github.head
    assert run.after_merge == [f"move-issue #{ISSUE}", f"close-issue #{ISSUE}"]


def test_yes_naming_the_head_by_a_prefix_merges(world, capsys) -> None:
    run = _answers_world(world)
    rc, out, err = run.run("--yes", "--expect-head", run.github.head[:12], capsys=capsys)
    assert rc == 0, out + err
    lines = out.splitlines()
    assert lines[-1] == f"merge: merged as {'c' * 7}"
    assert lines.index(TOLD[0]) < lines.index(f"merge: merged as {'c' * 7}")
    assert run.github.bodies == []


def test_at_a_terminal_without_yes_the_prompt_follows_the_answers(
    world, capsys, monkeypatch
) -> None:
    run = _answers_world(world)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    before: list[str] = []
    asked: list[str] = []

    def answer(prompt: str = "") -> str:
        before.append(capsys.readouterr().out)
        asked.append(prompt)
        return "y"

    monkeypatch.setattr("builtins.input", answer)
    rc, out, err = run.run(capsys=capsys)
    assert rc == 0, out + err
    (printed,) = before
    assert TOLD[0] in printed.splitlines()
    assert f"{_STEP}: 2" in printed.splitlines()
    # The yes is for a named head: the question names the head the run pinned,
    # and that head is the one that merges (#1760).
    assert asked == [f"Squash-merge PR #{PR} at {_short(run.github.head)} + close? [y/N] "]
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


def test_a_base_that_changed_a_file_an_answer_is_on_is_refused(world, capsys) -> None:
    """The base's commits since the head left it changed a file an answer is on: the
    merge could land answers other than those the reviewer checked and the person
    was told (DEC-065 point 5)."""
    run = _answers_world(world)
    _main_moves_on(run, "docs/install.md")
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"{_STEP}: refused — main moved on after PR #{PR}'s head left it, and its commits since "
        "changed 1 file (docs/install.md) the answers' words are on, so its merge can land "
        f"answers other than those at {_short(run.github.head)}. Merge main into {BRANCH} (`git "
        f"merge origin/main`), push, and run `land-work {ISSUE}` again"
    )
    assert run.github.merges == []


def test_a_base_that_moved_on_elsewhere_stops_nothing(world, capsys) -> None:
    """An outdated base whose commits changed no file the answers' words are on
    lands as an up-to-date one does."""
    run = _answers_world(world)
    _main_moves_on(run, "src/elsewhere.py")
    rc, out, err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == 0, out + err
    assert run.github.merges[-1][-1] == run.github.head


def test_a_base_whose_changes_cannot_be_read_is_refused(world, capsys) -> None:
    run = _answers_world(world)
    run.outdated, run.tip = True, "f" * 40  # a tip this clone does not have
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert (
        "which of the answers' files and settings its commits since changed could not be read"
        in out.splitlines()[-1]
    )
    # With no answers, an outdated base is no reason to stop.
    run.written = []
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err


#: An answer file the change adds, as the change check names it (COR-062 point 1). This
#: world's repository ignores `.pkit/`, and land-work reads the path as the check gives
#: it, wherever it lies.
_ANSWER_FILE = "friction/answers/20261022T090000Z-1a2b3c4d.yaml"


def _answered_in_a_file(world: Callable[..., _Run]) -> _Run:
    """`_answers_world`, the change's answer on docs/install.md written in an answer
    file, as the change check names it (`file`)."""
    run = world()
    run.written = [{**INSTALL, "file": _ANSWER_FILE}, {**DEFERRED, "file": "docs/cli.md"}]
    return run


def test_a_base_that_changed_the_answer_file_an_answer_is_in_is_refused(world, capsys) -> None:
    """The answers' words sit in the file the change check names for each answer: a
    base that changed that answer file since the head left it could land answers
    other than those the reviewer checked (DEC-065 point 5)."""
    run = _answered_in_a_file(world)
    _main_moves_on(run, _ANSWER_FILE)
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert f"changed 1 file ({_ANSWER_FILE}) the answers' words are on" in out.splitlines()[-1]
    assert run.github.merges == []


def test_a_base_that_changed_only_the_document_an_answer_file_answers_stops_nothing(
    world, capsys
) -> None:
    """An answer in an answer file leaves its words out of the document it answers on:
    a base that changed only that document lands no other answer."""
    run = _answered_in_a_file(world)
    _main_moves_on(run, "docs/install.md")
    rc, out, err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == 0, out + err
    assert run.github.merges[-1][-1] == run.github.head


#: A revalidation on the base's tip that the change's answer on docs/install.md did not
#: read, as the change check reports it (`answered_apart_at_tip`).
_APART = {
    "artefact": "install",
    "location": "docs/install.md",
    "revalidations": [
        {
            "file": ".pkit/project/friction/answers/20261023T090000Z-5e6f7a8b.yaml",
            "at": "2026-10-23T09:00:00Z",
            "outcome": "unchanged",
            "unchanged_because": "The new flag leaves the steps as written.",
        }
    ],
}
_APART_LINE = (
    "  Answered apart once merged: docs/install.md — the base's revalidation in "
    ".pkit/project/friction/answers/20261023T090000Z-5e6f7a8b.yaml of 2026-10-23T09:00:00Z, "
    "which this change's answer did not read. Still accurate: \"The new flag leaves the "
    'steps as written."'
)


def test_a_revalidation_the_merge_would_leave_answered_apart_is_told_and_stops_nothing(
    world, capsys
) -> None:
    """Before it stops ready, the run prints each revalidation on the base's tip that the
    change's answer did not read, beside what the person is told, and the `ready:` line
    counts it, as information (DEC-055 point 3)."""
    run = _answers_world(world)
    run.apart = [_APART]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-3:] == [
        *TOLD,
        _APART_LINE,
        _ready_line(
            run,
            ", 1 document left out of date and 1 revalidation answered apart once merged above, "
            "for information",
        ),
    ]
    assert run.github.bodies == []


def test_a_revalidation_answered_apart_never_holds_an_authorised_merge(world, capsys) -> None:
    run = _answers_world(world)
    run.apart = [_APART]
    rc, out, err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == 0, out + err
    assert _APART_LINE in out.splitlines()
    assert run.github.merges[-1][-1] == run.github.head


def test_a_file_the_change_did_not_touch_that_cannot_be_read_is_no_reason_to_stop(
    world, capsys
) -> None:
    """A file the change did not touch holds no answer of it."""
    run = world()
    run.unreadable = [".gitignore"]  # unreadable, and untouched by the change
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err


def test_a_file_the_change_touches_that_cannot_be_read_is_refused(world, capsys) -> None:
    """Answers on a file whose front matter does not parse cannot be read."""
    run = world()
    run.unreadable = ["change.txt", ".gitignore"]  # the change added change.txt
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert out.splitlines()[-1] == (
        f"{_STEP}: refused — front matter the change check cannot read, in 1 file "
        "(change.txt) this change touches, so the answers on it cannot be read. Fix it (`pkit "
        f"validate` names the problem), push, and run `land-work {ISSUE}` again"
    )
    assert run.github.merges == []


def test_what_is_told_shows_what_a_terminal_would_act_on_escaped(world, capsys) -> None:
    run = world()
    run.written = [
        _answer(
            "docs/a.md",
            "fine\x1b[2Kgone ‮esrever",
            answer="deferred",
            anchor={"kind": "path", "value": "src/**"},
        )
    ]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert (
        '  Left out of date: docs/a.md, for changes to src/**: "fine\\x1b[2Kgone \\u202eesrever"'
    ) in out.splitlines()
    assert "\x1b" not in out and "‮" not in out


def test_done_work_closes_no_issue_an_earlier_list_names(world, capsys) -> None:
    """done-work reads the closing references outside a list an earlier run wrote: a
    description whose list says "fixes #77" closes #42 alone, through done-work's
    real path."""
    run = world()
    assert run.run(capsys=capsys)[0] == run.land.EXIT_READY  # reviewed, not merged
    run.github.body = f"{_PR_BODY}\n{run.earlier_list('Holds once this fixes #77.')}\n"
    end = run.land.done_work.run([str(ISSUE), "--yes"], pinned_head=run.github.head)
    assert end.kind == run.land.done_work.MERGED
    assert run.after_merge == [f"move-issue #{ISSUE}", f"close-issue #{ISSUE}"]
    assert not any(call[:3] == ["issue", "view", "77"] for call in run.github.calls)


# -- a section no command wrote, and the friction settings (DEC-065 points 1 and 4) --


def _hand_written(heading: str) -> str:
    """A section someone typed under `heading`, with no markers."""
    return f"{heading}\n\n```\n1. docs/install.md — unchanged: as I recall it\n```\n"


@pytest.mark.parametrize("heading", [_HEADING, _FORMER_HEADING])
def test_a_section_no_command_wrote_is_left_as_it_is(world, capsys, heading) -> None:
    """No list remains for it to be mistaken for: only a region a command wrote is
    removed, and the description is not written (DEC-065 point 1)."""
    run = _answers_world(world)
    run.github.body = f"{_PR_BODY}\n{_hand_written(heading)}"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert f"{_STEP}: 2" in out.splitlines()
    assert run.github.bodies == []


def test_an_earlier_list_goes_and_a_section_typed_below_it_stays(world, capsys) -> None:
    run = _answers_world(world, listed=True)
    run.github.body += f"\n{_hand_written(_FORMER_HEADING)}"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert f"{_STEP}: 2{_REMOVED}" in out.splitlines()
    (written,) = run.github.bodies
    assert _HEADING not in written and "as I recall it" in written


def test_a_start_marker_with_no_end_warns_and_leaves_the_description(world, capsys) -> None:
    """An end lost, or a marker quoted: what follows may be the author's, so the run
    warns and writes nothing (DEC-065 point 1)."""
    run = _answers_world(world)
    marker = run.land.friction_answers.MARKER_START
    run.github.body = f"{_PR_BODY}\n```\n{marker} head=x base=y -->\n```\n\nCloses #{ISSUE}\n"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert f"  warn: {run.land.friction_answers.ORPHAN_WARNING}" in out.splitlines()
    assert run.github.bodies == []


def test_an_earlier_list_that_cannot_be_removed_is_a_retry(world, capsys) -> None:
    """With no answers and no setting, nothing is held: a removal that failed is
    run again like any other step."""
    run = _answers_world(world, listed=True)
    run.written = []
    run.github.fails.append(lambda argv: argv[:2] == ["pr", "edit"])
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_RETRY
    assert out.splitlines()[-1] == (
        f"{_STEP}: the list of answers an earlier run left could not be removed from PR "
        f"#{PR}'s description: HTTP 502: Bad Gateway. Nothing was merged; run "
        f"`land-work {ISSUE}` again"
    )
    assert run.github.merges == []


def test_a_change_that_sets_friction_dormant_is_told_like_an_answer(world, capsys) -> None:
    """A change that empties the friction places leaves the check dormant at its
    head, giving no answer: the person is told the settings it altered instead,
    above the `ready:` line, as information."""
    run = world()
    answers = run.land.friction_answers
    run.settings = [answers.Setting(answers.PLACES, ("docs",), ())]
    head = run.github.head
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert f"{_STEP}: none, but a change to which documents are checked" in lines
    assert lines[-2:] == [
        f"  {answers.PLACES}: docs → none",
        f"ready: {_short(head)} — CI passed, all required verdicts approved, a change to "
        "which documents are checked above, for information; merge with: pkit pm land-work "
        f"{ISSUE} --yes --expect-head {head}",
    ]
    assert run.github.bodies == [] and run.github.merges == []
    # The authorisation merges it as it merges any other change.
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert run.github.merges[-1][-1] == head and run.github.bodies == []


# -- the author's sentences, and what the person is told (DEC-065 points 1 and 4) --

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


def test_what_changed_in_each_updated_document_is_told_in_its_author_s_sentence(
    world, capsys
) -> None:
    """Each sentence is read from the description's own section, which stays as the
    author wrote it, and told above the `ready:` line; a document with none is said to
    have none."""
    run = world()
    run.written = [UPDATED_INSTALL, UPDATED_GUIDE, DEFERRED]
    run.github.body = _SAID
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    head = run.github.head
    assert out.splitlines()[-4:] == [
        '  What changed in docs/install.md: "The install steps name the renamed flag."',
        "  What changed in docs/guide.md: the pull request's author has not said",
        *TOLD,
        f"ready: {_short(head)} — CI passed, all required verdicts approved, what changed in 2 "
        "updated documents and 1 document left out of date above, for information; merge "
        f"with: pkit pm land-work {ISSUE} --yes --expect-head {head}",
    ]
    assert f"{_STEP}: 3" in out.splitlines()
    assert run.github.bodies == []


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
    author has not said. The warning names its line in the description and the form
    a sentence takes; the read form draws none."""
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
        "the line's first column, the document in a code span as the change check names it"
    ]
    assert lines.index(warned[0]) < lines.index(told)


def test_the_line_named_is_the_line_in_the_description_the_run_leaves(world, capsys) -> None:
    """With a list an earlier run wrote above the sentences, the run removes the list,
    and the warning names the line the item moves up to."""
    run = world()
    run.written = [UPDATED_INSTALL, UPDATED_GUIDE, DEFERRED]
    item = "- **docs/guide.md:** The guide names the new flag."
    said = _SAID.removeprefix(_PR_BODY)
    before = f"{_PR_BODY}\n{run.earlier_list()}\n{said}{item}\n"
    run.github.body = before
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    (written,) = run.github.bodies
    left = written.split("\n").index(item) + 1
    assert left < before.split("\n").index(item) + 1
    (warned,) = [line for line in out.splitlines() if "is not read as a sentence" in line]
    assert warned.startswith(f"  warn: line {left} of the description, ")


@pytest.mark.parametrize(
    "written", [[UPDATED_INSTALL, DEFERRED], []], ids=["answers", "no answers"]
)
def test_a_sentence_on_a_document_the_check_does_not_mark_updated_is_warned_of(
    world, capsys, written
) -> None:
    """No reviewer checks a sentence on a document the change check does not mark
    updated, a deferred one here, or any where the change wrote no answers: a warning
    names each, and the edit that removes it, before the run stops ready. Nothing is
    refused (DEC-065 point 3)."""
    run = world()
    run.written = written
    run.github.body = f"{_SAID}- `docs/cli.md`: The page drops the old flag.\n"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    head = _short(run.github.head)

    def warning(location: str) -> str:
        return (
            f"  warn: {location} has a sentence under `## What changed in each updated "
            f"document`, and the change check at {head} does not mark it updated, so no "
            f"reviewer checks the sentence — remove it from the description with `edit-pr {PR} "
            "--body-file <file>`"
        )

    unlisted = ["docs/cli.md"] if written else ["docs/install.md", "docs/cli.md"]
    assert [line for line in lines if "no reviewer checks the sentence" in line] == [
        warning(location) for location in unlisted
    ]
    assert lines.index(warning("docs/cli.md")) < len(lines) - 1
    assert lines[-1].startswith("ready: ")
    assert "held for the sentence" not in lines[-1]


def test_a_sentence_no_reviewer_checks_holds_a_run_authorised_up_front(world, capsys) -> None:
    """The person authorised before the warning was shown, so the run stops ready, as
    a `[person]` finding holds it, until the author removes the sentence (DEC-055
    point 3). Once it is removed, the same command merges."""
    run = world()
    run.written = [UPDATED_INSTALL, DEFERRED]
    run.github.body = f"{_SAID}- `docs/cli.md`: The page drops the old flag.\n"
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert run.github.state == "OPEN"
    assert (
        f"; held for the sentence on docs/cli.md, which no reviewer checks (above): "
        f"remove it with `edit-pr {PR} --body-file <file>`, then run the command below again; "
        f"merge with: pkit pm land-work {ISSUE} --yes --expect-head {run.github.head}"
    ) in out.splitlines()[-1]
    run.github.body = run.github.body.replace("- `docs/cli.md`: The page drops the old flag.\n", "")
    assert run.authorised(capsys=capsys)[0] == run.land.EXIT_MERGED


def test_a_missing_sentence_holds_a_run_authorised_up_front(world, capsys) -> None:
    """An edit after the verdict makes no verdict stale, and no move to review runs
    again, so the landing command is what stops it. Once the sentence is written, the
    same command merges (DEC-065 point 4)."""
    run = world()
    run.written = [UPDATED_INSTALL, UPDATED_GUIDE]
    run.github.body = _SAID
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert run.github.state == "OPEN"
    assert (
        f"; held for docs/guide.md, updated with no sentence on what changed (above): write it "
        f"with `edit-pr {PR} --body-file <file>`, then run the command below again; merge with: "
        f"pkit pm land-work {ISSUE} --yes --expect-head {run.github.head}"
    ) in out.splitlines()[-1]
    run.github.body += "- `docs/guide.md`: The guide names the new flag.\n"
    assert run.authorised(capsys=capsys)[0] == run.land.EXIT_MERGED


def test_a_missing_sentence_holds_no_run_a_person_is_asked_at(world, capsys) -> None:
    """Without `--yes` the run stops ready anyway, and tells the person the author has
    not said: nothing is held, since nothing was authorised before it was shown."""
    run = world()
    run.written = [UPDATED_GUIDE]
    run.github.body = _PR_BODY
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert "  What changed in docs/guide.md: the pull request's author has not said" in out
    assert "held for" not in out.splitlines()[-1]


@pytest.mark.parametrize(
    "sentence",
    ["It fixes #77 too.", "Fixed #77.", "Resolves owner/repo#77."],
    ids=["keyword", "past tense", "another repository"],
)
def test_a_sentence_that_reads_as_a_closing_reference_is_refused_and_nothing_written(
    world, capsys, sentence
) -> None:
    """It stays in the description and the squash commit, where the host would close
    an issue with it, past the checkbox gate: nothing overrides the refusal (DEC-065
    point 5)."""
    run = world()
    run.written = [UPDATED_INSTALL]
    run.github.body = _SAID.replace("The install steps name the renamed flag.", sentence)
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    last = out.splitlines()[-1]
    assert last.startswith(
        f"{_STEP}: refused — the sentence on what changed in docs/install.md, under `## What "
        "changed in each updated document`, reads as a closing reference ("
    )
    assert last.endswith(
        f"the host would close an issue with it at merge — reword it, with `edit-pr {PR} "
        f"--body-file <file>`, and run `land-work {ISSUE}` again. Nothing was written"
    )
    assert run.github.bodies == [] and run.github.merges == []


def test_a_base_that_changed_the_settings_the_change_alters_is_refused(
    world, capsys, monkeypatch
) -> None:
    """A base whose commits since changed the friction settings the change alters can
    land settings other than those the person was told (DEC-065 point 5)."""
    run = world()
    answers = run.land.friction_answers
    run.settings = [answers.Setting(answers.PLACES, ("docs",), ())]
    _main_moves_on(run, "src/elsewhere.py")
    moved: list[tuple[str, str]] = []

    def settings_change(merge_base: str, head: str) -> Any:
        moved.append((merge_base, head))
        return (answers.Setting(answers.PLACES, ("docs",), ("docs", "guides")),)

    monkeypatch.setattr(answers, "settings_change", settings_change)
    rc, out, _err = run.run("--yes", "--expect-head", run.github.head, capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    assert (
        "its commits since changed the friction settings the change alters" in out.splitlines()[-1]
    )
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, err = run.authorised(capsys=capsys)
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


def _shown_above_the_stop(out: str, shown: list[str], line: str) -> None:
    """`shown` and the step's `line` are printed just above the stop, the run's last line."""
    lines = out.splitlines()
    at = lines.index(shown[0])
    assert lines[at:-1] == [*shown, line]


@pytest.mark.parametrize("authorised", [False, True], ids=["ready-first", "authorised"])
@pytest.mark.parametrize(
    ("other", "code"),
    [
        pytest.param(("CHANGES_REQUESTED", _BLOCKING), 1, id="a reviewer's block"),
        pytest.param(None, 6, id="a reviewer that failed"),
    ],
)
def test_a_stop_inside_the_review_shows_the_finding_another_reviewer_posted(
    world, capsys, other: tuple[str, str] | None, code: int, authorised: bool
) -> None:
    """A later `--yes` would find this verdict at its start and merge on it, so the run
    that posted it shows it, whichever reviewer stopped the run (DEC-055 point 3)."""
    run = world()
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    run.answers["reviewer"] = other
    rc, out, _err = run.authorised(capsys=capsys) if authorised else run.run(capsys=capsys)
    assert rc == code
    _shown_above_the_stop(out, _person_lines("code-reviewer"), f"{_FINDINGS}: 1, above")
    assert out.splitlines()[-1].startswith("review: ")
    assert run.github.merges == []


def test_a_block_beside_the_checks_shows_the_finding_and_names_the_check_that_failed(
    world, capsys
) -> None:
    run = world(checks=[_SUITE_RUNNING, _parts("SUCCESS", "FAILURE")], start_after=_FIRST)
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    run.answers["reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    _shown_above_the_stop(out, _person_lines("code-reviewer"), f"{_FINDINGS}: 1, above")
    assert f"a check failed on {_short(run.github.head)}" in out.splitlines()[-1]


def test_a_block_that_carries_a_finding_to_judge_shows_it_too(world, capsys) -> None:
    run = world()
    run.answers["reviewer"] = ("CHANGES_REQUESTED", f"{_BLOCKING}\n{_PERSON}")
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    _shown_above_the_stop(out, _person_lines("reviewer"), f"{_FINDINGS}: 1, above")


def test_review_pr_raising_shows_the_finding_of_a_verdict_standing_for_the_head(
    world, capsys, monkeypatch
) -> None:
    run = world()
    run.github.comments.append(_verdict(run, "code-reviewer", _PERSON, sha=run.github.head))

    def boom(argv: list[str], **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(run.land.review_pr, "review", boom)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_REVIEW_INCOMPLETE
    _shown_above_the_stop(out, _person_lines("code-reviewer"), f"{_FINDINGS}: 1, above")


def test_a_stale_verdict_left_by_a_reviewer_that_failed_is_shown_marked_stale(
    world, capsys
) -> None:
    """Its reviewer's new run posted nothing, so its latest verdict is the old one, and
    the stop prints it as the findings' step would."""
    run = world()
    old = run.github.head
    run.github.comments.append(_verdict(run, "code-reviewer", _PERSON, sha=old))
    new = run.push_new_head("fix.txt")
    run.github.checks[new] = [_GREEN]
    run.answers["code-reviewer"] = None
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_REVIEW_INCOMPLETE
    stale = f"(stale: reviewed {_short(old)}; changed since: fix.txt) "
    _shown_above_the_stop(
        out, _person_lines("code-reviewer", stale), f"{_FINDINGS}: 1, above (1 marked stale)"
    )


def test_a_head_that_moved_during_the_review_shows_the_finding_the_run_posted(
    world, capsys
) -> None:
    """The stop stays the moved head's, and the verdict is judged for the head the PR
    has now."""
    run = world()
    pinned = run.github.head
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)

    def tips(argv: list[str]) -> bool:
        return argv[:2] == ["pr", "view"] and argv[-1] == "headRefOid,baseRefOid"

    run.github.before(_nth(tips, 2), lambda: run.push_new_head("during.txt"))
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_HEAD_MOVED
    stale = f"(stale: reviewed {_short(pinned)}; changed since: during.txt) "
    _shown_above_the_stop(
        out, _person_lines("code-reviewer", stale), f"{_FINDINGS}: 1, above (1 marked stale)"
    )
    assert out.splitlines()[-1].startswith(f"review: stopped — PR #{PR}'s head is ")


def test_verdicts_that_cannot_be_read_at_a_stop_warn_and_the_stop_stands(world, capsys) -> None:
    run = world()
    run.answers["reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    run.github.fails.append(_findings_read(run))
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert out.splitlines()[-2:] == [
        f"  warn: {_FINDINGS}: PR #{PR}'s verdicts could not be read: HTTP 502: Bad Gateway. "
        f"Nothing was merged; run `land-work {ISSUE}` again",
        "review: changes requested by reviewer — the blocking findings are above; merge not "
        "started",
    ]


def test_a_stop_inside_the_review_with_no_finding_to_judge_prints_no_line_for_them(
    world, capsys
) -> None:
    run = world()
    run.answers["reviewer"] = ("CHANGES_REQUESTED", _BLOCKING)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == 1
    assert _FINDINGS not in out


def test_a_stop_on_the_accepted_records_shows_the_finding_read_before_it(world, capsys) -> None:
    run = world()
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    run.altered_problem = "`pkit decisions check-diff --json …`: it exited 2"
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    lines = out.splitlines()
    assert lines[-3:-1] == _person_lines("code-reviewer")
    assert lines[-1].startswith(f"{_FINDINGS}: the accepted records this change alters")


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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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
    rc, out, _err = run.authorised(capsys=capsys)
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

    rc, out, err = run.authorised(capsys=capsys)
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
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert "[stranger]" not in out
    assert not any(step.startswith(f"{_FINDINGS}:") for step in _steps(out))


def test_a_person_finding_from_a_reviewer_the_gate_does_not_require_holds_nothing(
    world, capsys
) -> None:
    run = world()
    run.github.comments.append(_verdict(run, "stranger", _PERSON, sha=run.github.head))
    rc, out, err = run.authorised(capsys=capsys)
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
    rc, out, err = run.authorised(capsys=capsys)
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


# ---- the accepted records a change alters (#2161) ------------------------------------

_ACCEPTED = ".pkit/decisions/project/PRJ-001-a.md"


def _altered(run: _Run) -> Any:
    """An accepted record the change alters: one point narrowed, one added."""
    records = run.land.accepted_records
    points = (records.Point("1", "altered", "Scope"), records.Point("4", "added", "Who"))
    return records.Altered(_ACCEPTED, "PRJ-001", points)


#: How land-work prints `_altered`, a finding a person judges.
_ALTERED_LINE = (
    f"  [accepted record] PRJ-001, `{_ACCEPTED}`: point 1 (Scope) altered and point 4 (Who) "
    "added. Judge whether each edit changes what the record decides."
)


def test_an_accepted_record_the_change_alters_is_shown_as_a_finding_to_judge(world, capsys) -> None:
    """The list is derived at the pinned head against the PR's base, printed among the
    findings to judge before the answers, and counted on the `ready:` line."""
    run = world()
    head = run.github.head
    run.altered = [_altered(run)]
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    at = lines.index(_ALTERED_LINE)
    assert lines[at + 1] == f"{_FINDINGS}: 1, above"
    assert at < lines.index(f"{_STEP}: none")
    assert lines[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 finding to judge "
        f"above; {_merge_line(run)}"
    )
    assert run.altered_for == [(head, "main")]
    assert run.github.merges == []


def test_a_change_that_alters_no_accepted_record_prints_no_finding(world, capsys) -> None:
    run = world()
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert not any(line.startswith(_FINDINGS) for line in out.splitlines())


def test_yes_for_the_head_merges_a_change_to_an_accepted_record(world, capsys) -> None:
    """The records stand for the head and were there when the run started: the
    authorisation for that head, given on the `ready:` stop that showed them, merges."""
    run = world()
    head = run.github.head
    run.altered = [_altered(run)]
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    lines = out.splitlines()
    assert lines.index(_ALTERED_LINE) < lines.index(f"merge: merged as {'c' * 7}")
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_covered_later_head_merges_on_the_records_the_earlier_head_showed(world, capsys) -> None:
    """The list at the later head is the one at the head authorised, which the person
    was shown: the authorisation covers it."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("answers.txt")
    run.github.checks[head] = [_GREEN]
    run.cover = True
    run.altered = [_altered(run)]
    rc, out, err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == 0, out + err
    assert _ALTERED_LINE in out.splitlines()
    assert [merge[-1] for merge in run.github.merges] == [head]
    assert run.altered_for == [(head, "main"), (authorised, "main")]


@pytest.mark.parametrize(
    ("at_authorised", "held"),
    [
        ([], "a change to accepted records other than the one at {earlier}"),
        (None, "accepted records this change alters that could not be read at {earlier}"),
    ],
)
def test_a_covered_later_head_with_another_list_of_accepted_records_stops_ready(
    world, capsys, at_authorised, held
) -> None:
    """A merge of the base moves where the head left it, so a record the base accepted
    meanwhile can join the list: a list nobody was shown at the head authorised, or one
    that cannot be read there, needs the person."""
    run = world()
    authorised = run.github.head
    head = run.push_new_head("answers.txt")
    run.github.checks[head] = [_GREEN]
    run.cover = True
    run.altered = [_altered(run)]
    run.altered_at[authorised] = at_authorised
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    reason = held.format(earlier=_short(authorised))
    assert out.splitlines()[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 1 finding to judge "
        f"above; the authorisation for {_short(authorised)} covers {_short(head)} only where "
        f"nothing there needs a person, and it holds {reason}; {_merge_line(run)}"
    )
    assert run.github.merges == []


def test_a_person_finding_and_an_accepted_record_are_counted_together_and_only_the_verdict_holds(
    world, capsys
) -> None:
    run = world()
    head = run.github.head
    run.answers["code-reviewer"] = ("APPROVED", _PERSON)
    run.altered = [_altered(run)]
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    at = lines.index(_person_lines("code-reviewer")[0])
    assert lines[at : at + 4] == [
        *_person_lines("code-reviewer"),
        _ALTERED_LINE,
        f"{_FINDINGS}: 2, above",
    ]
    assert lines[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, 2 findings to judge "
        "above (code-reviewer's verdict came after this run's --yes was given, so the --yes does "
        f"not cover its finding); {_merge_line(run)}"
    )


def test_accepted_records_that_cannot_be_read_stop_the_run_before_the_list_is_written(
    world, capsys
) -> None:
    run = world()
    run.written = [INSTALL]
    run.altered_problem = "`pkit decisions check-diff --json …`: it exited 2"
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE
    assert out.splitlines()[-1] == (
        f"{_FINDINGS}: the accepted records this change alters at {_short(run.github.head)} "
        "could not be read — `pkit decisions check-diff --json …`: it exited 2. Nothing was "
        f"merged; run `land-work {ISSUE}` again"
    )
    assert run.github.merges == [] and run.github.bodies == []


# ---- the fixers' proposals that wait (DEC-056 point 6, #1744) ----------------------------


def _queue(run: _Run) -> Path:
    """The queue's folder in the clone's main working tree, as git names it."""
    return run.work.resolve() / ".agent-workspace" / "project-management" / "drift"


def _waiting(run: _Run, *states: str) -> None:
    """A queue whose index holds one artefact in each of `states`."""
    queue = _queue(run)
    queue.mkdir(parents=True)
    artefacts = {
        f"docs/{n}.md": {"type": "living-docs:page", "fixer": "living-docs", "state": state}
        for n, state in enumerate(states)
    }
    index = {"schema_version": 1, "contract_version": 1, "artefacts": artefacts}
    (queue / "index.json").write_text(json.dumps(index), encoding="utf-8")


def _count(run: _Run, count: int) -> str:
    noun = "proposal waits" if count == 1 else "proposals wait"
    return f"fixers: {count} {noun} for you — pkit pm fix-drift gathered them in {_queue(run)}"


def test_the_count_of_proposals_that_wait_comes_just_before_the_ready_line(world, capsys) -> None:
    run = world()
    _waiting(run, "proposed", "held", "none", "failed", "set-aside")
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-2:] == [_count(run, 2), _ready_line(run, told="")]


def test_the_count_comes_before_the_last_line_of_a_merge(world, capsys) -> None:
    run = world()
    _waiting(run, "proposed")
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert out.splitlines()[-2:] == [_count(run, 1), f"merge: merged as {'c' * 7}"]


def test_the_count_comes_before_the_last_line_of_a_run_that_stops(world, capsys) -> None:
    stopped = world(checks=[_RED])
    _waiting(stopped, "held", "held", "proposed")
    rc, out, _err = stopped.run(capsys=capsys)
    assert rc == stopped.land.EXIT_NEEDS_CHANGE
    lines = out.splitlines()
    assert lines[-2] == _count(stopped, 3)
    assert lines[-1].startswith("ci: failed on")


@pytest.mark.parametrize("states", [(), ("none", "failed", "set-aside")])
def test_with_nothing_waiting_no_count_is_printed(world, capsys, states) -> None:
    run = world()
    if states:
        _waiting(run, *states)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert not any(line.startswith("fixers:") for line in out.splitlines())


def test_a_queue_that_cannot_be_read_warns_and_changes_nothing(world, capsys) -> None:
    run = world()
    _queue(run).mkdir(parents=True)
    (_queue(run) / "index.json").write_text('{"schema_version": 9}', encoding="utf-8")
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    warning, last = out.splitlines()[-2:]
    assert warning.startswith("warn: the fixers' queue cannot be read, so whether proposals wait")
    assert "schema_version 9" in warning
    assert last == f"merge: merged as {'c' * 7}"
    assert [merge[-1] for merge in run.github.merges] == [run.github.head]


# ---- a change to the fixers' grant list (DEC-056 point 2, #1744) -------------------------

_CONFIG = ".pkit/capabilities/project-management/project/config.yaml"
_GRANT = "fixers:\n  living-docs:\n    granted:\n      - living-docs:page\n"
_GRANT_AND_REFUSE = _GRANT + "    refused:\n      - living-docs:guide\n"
_GRANTED = "Fixer grant added: living-docs may start on its own on living-docs:page"
_REFUSED = "Fixer refusal added: living-docs is refused living-docs:guide"
_GRANTS = "a change to which fixers may start"


def _push_grants(run: _Run, block: str) -> str:
    """A push to the PR's branch whose project configuration carries `block`, the
    staged configuration kept above it. The clone ignores `.pkit/`, so the base
    holds no configuration: every grant and refusal is the change's."""
    config = run.work / _CONFIG
    text = config.read_text(encoding="utf-8").split("fixers:", 1)[0]
    config.write_text(text + block, encoding="utf-8")
    _git(run.work, "add", "-f", _CONFIG)
    _git(run.work, "commit", "-q", "-m", "grant a fixer")
    _git(run.work, "push", "-q", "origin", BRANCH)
    head = _git(run.work, "rev-parse", "HEAD")
    run.github.head = head
    run.github.checks[head] = [_GREEN]
    return head


def test_a_change_to_the_grant_list_is_listed_before_the_run_stops_ready(world, capsys) -> None:
    run = world()
    _push_grants(run, _GRANT_AND_REFUSE)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert f"{_STEP}: none, but {_GRANTS}" in lines
    # A line each, by agent and type: living-docs:guide before living-docs:page, told
    # just above the `ready:` line, which names it.
    told = f", {_GRANTS} above, for information"
    assert lines[-3:] == [f"  {_REFUSED}", f"  {_GRANTED}", _ready_line(run, told=told)]
    # Printed only: the description is left as it was.
    assert run.github.bodies == []


def test_a_change_to_the_grant_list_beside_answers_is_listed_with_them(world, capsys) -> None:
    run = _answers_world(world)
    _push_grants(run, _GRANT)
    rc, out, _err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY
    lines = out.splitlines()
    assert f"{_STEP}: 2, plus {_GRANTS}" in lines
    told = f", 1 document left out of date and {_GRANTS} above, for information"
    assert lines[-3:] == [*TOLD, f"  {_GRANTED}", _ready_line(run, told=told)]


def test_an_authorisation_for_the_head_merges_its_grant_list_change(world, capsys) -> None:
    """The run reads the change at the head it pinned when it started: the head the
    person was shown, so the authorisation covers it."""
    run = world()
    _push_grants(run, _GRANT)
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert f"  {_GRANTED}" in out.splitlines()
    assert [merge[-1] for merge in run.github.merges] == [run.github.head]


def test_a_grant_list_that_cannot_be_read_at_the_head_stops_and_merges_nothing(
    world, capsys
) -> None:
    run = world()
    head = _push_grants(run, "fixers: [living-docs]\n")
    rc, out, _err = run.authorised(capsys=capsys)
    assert rc == run.land.EXIT_NEEDS_CHANGE
    last = out.splitlines()[-1]
    assert last.startswith(
        f"{_STEP}: refused — the fixers' grant list at {_short(head)} cannot be read ("
    )
    assert last.endswith(f"push, and run `land-work {ISSUE}` again. Nothing was written")
    assert run.github.merges == []
    assert run.github.bodies == []


def test_a_covered_later_head_with_the_same_grant_list_change_merges(world, capsys) -> None:
    run = world()
    authorised = _push_grants(run, _GRANT)
    head = run.push_new_head("answers.txt")
    run.github.checks[head] = [_GREEN]
    run.cover = True
    rc, out, err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == 0, out + err
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_covered_later_head_with_another_grant_list_change_stops_ready(world, capsys) -> None:
    """The authorisation covers only the change the person was shown, the one at the
    head authorised: a later head that brings another stops at `ready:`, as an answer
    the change check did not ask for does."""
    run = world()
    authorised = _push_grants(run, _GRANT)
    head = _push_grants(run, _GRANT_AND_REFUSE)
    run.cover = True
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert out.splitlines()[-1] == (
        f"ready: {_short(head)} — CI passed, all required verdicts approved, {_GRANTS} above, "
        f"for information; the authorisation for {_short(authorised)} covers {_short(head)} "
        f"only where nothing there needs a person, and it holds {_GRANTS} other than the one "
        f"at {_short(authorised)}; {_merge_line(run)}"
    )
    assert run.github.merges == []
    # The person's authorisation for the later head, shown the change, merges it.
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == 0, out + err
    assert [merge[-1] for merge in run.github.merges] == [head]


def test_a_covered_later_head_that_left_its_base_elsewhere_holds_its_grant_list_change(
    world, capsys
) -> None:
    """The change at the head authorised is read from where the later head left its base,
    which the change check names, and pm computes no fork point of its own (COR-054 point
    5): where the head authorised left the base elsewhere, its change could not be read,
    and a person decides."""
    run = world()
    authorised = _push_grants(run, _GRANT)
    tip = _main_moves_on(run, "src/elsewhere.py")
    _git(run.work, "merge", "-q", "--no-edit", "main")
    _git(run.work, "push", "-q", "origin", BRANCH)
    head = run.github.head = _git(run.work, "rev-parse", "HEAD")
    run.github.checks[head] = [_GREEN]
    run.merge_base, run.outdated, run.cover = tip, False, True
    rc, out, _err = run.run("--yes", "--expect-head", authorised, capsys=capsys)
    assert rc == run.land.EXIT_READY
    assert (
        f"it holds a change to the fixers' grant list that could not be read at "
        f"{_short(authorised)};"
    ) in out.splitlines()[-1]
    assert run.github.merges == []


# ---- the merge as it would land (DEC-055 point 6, #2228) -------------------------
# Just before it stops ready, asks or merges, land-work runs the change check on the
# merge of the pinned head with the base as it stands, fetched, and refuses where the
# check fails there, naming each document.

#: How the line of the step that checks the merge begins (land-work's `MERGE_CHECK`).
_MERGE_CHECK = "merge check"

_FRICTION = {
    "location": "docs/core.md",
    "kind": "friction",
    "message": "path src/core/** changed in this diff; revalidate the artefact",
}
_DEAD = {"location": "docs/old.md", "kind": "dead-anchor", "message": "src/gone.py matches no file"}


def _merge_check_line(out: str) -> str:
    (line,) = [line for line in out.splitlines() if line.startswith(f"{_MERGE_CHECK}:")]
    return line


def test_a_merge_the_check_passes_on_goes_on_and_says_what_was_checked(world, capsys) -> None:
    run = world()
    head = run.github.head
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert _merge_check_line(out) == (
        f"{_MERGE_CHECK}: the change check passes on {_short(head)}, which holds main at "
        f"{_short(run.merge_base)}"
    )
    # Asked after the answers, for the pinned head against the PR's base, handed the
    # head's own check so a base the head holds is not checked twice.
    ((asked, base, checked),) = run.merged_for
    assert (asked, base, checked["base"]["commit"]) == (head, "main", run.merge_base)
    lines = out.splitlines()
    assert lines.index(_merge_check_line(out)) > lines.index(f"{_STEP}: none")


def test_a_merge_with_a_base_that_moved_on_is_named_as_merged(world, capsys) -> None:
    run = world()
    run.outdated, run.tip = True, "e" * 40
    rc, out, err = run.run(capsys=capsys)
    assert rc == 8, out + err
    assert _merge_check_line(out) == (
        f"{_MERGE_CHECK}: the change check passes on {_short(run.github.head)} merged with main "
        f"at {'e' * 7}"
    )


@pytest.mark.parametrize("authorised", [True, False], ids=["--yes", "ready"])
def test_a_merge_the_check_fails_on_is_refused_naming_each_document(
    world, capsys, authorised
) -> None:
    run = world()
    run.outdated, run.tip = True, "e" * 40
    run.merge_refused = [_FRICTION, _DEAD]
    if authorised:
        rc, out, err = run.authorised(capsys=capsys)
    else:
        rc, out, err = run.run(capsys=capsys)
    assert rc == 1, out + err
    lines = out.splitlines()
    assert f"  docs/core.md: friction — {_FRICTION['message']}" in lines
    assert f"  docs/old.md: dead-anchor — {_DEAD['message']}" in lines
    assert lines[-1] == (
        f"{_MERGE_CHECK}: refused — the change check fails on {_short(run.github.head)} merged "
        f"with main at {'e' * 7}, on 2 documents (docs/core.md, docs/old.md), above. Merge main "
        f"into {BRANCH} (`git merge origin/main`), settle each finding there, push, and run "
        f"`land-work {ISSUE}` again. Nothing was merged"
    )
    assert not any(line.startswith("ready:") for line in lines)
    assert (run.github.merges, run.after_merge) == ([], [])


def test_in_warning_mode_what_the_merge_check_finds_is_shown_and_stops_nothing(
    world, capsys
) -> None:
    run = world()
    run.outdated, run.tip = True, "e" * 40
    run.merge_reported = [_FRICTION]
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 0, out + err
    assert f"  docs/core.md: friction — {_FRICTION['message']}" in out.splitlines()
    assert _merge_check_line(out) == (
        f"{_MERGE_CHECK}: the change check passes on {_short(run.github.head)} merged with main "
        f"at {'e' * 7}, and reports 1 document above, which the project's friction mode fails "
        "nothing on: for information"
    )
    assert len(run.github.merges) == 1


def test_a_head_that_holds_the_base_and_fails_is_refused_without_a_merge_to_make(
    world, capsys
) -> None:
    run = world()
    run.merge_refused = [_FRICTION]
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 1, out + err
    assert out.splitlines()[-1] == (
        f"{_MERGE_CHECK}: refused — the change check fails on {_short(run.github.head)}, which "
        f"holds main at {_short(run.merge_base)}, on 1 document (docs/core.md), above. Settle "
        f"each finding in {BRANCH}, push, and run `land-work {ISSUE}` again. Nothing was merged"
    )
    assert run.github.merges == []


def test_a_merge_that_conflicts_with_the_base_as_fetched_is_refused(world, capsys) -> None:
    run = world()
    run.tip = "e" * 40
    run.merge_conflicts = ("src/cli/main.py",)
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 1, out + err
    assert out.splitlines()[-1] == (
        f"{_MERGE_CHECK}: refused — {_short(run.github.head)} conflicts with main as it stands, "
        f"at {'e' * 7}, in 1 file (src/cli/main.py). Merge main into {BRANCH} (`git merge "
        f"origin/main`), resolve the conflicts, push, and run `land-work {ISSUE}` again. "
        "Nothing was merged"
    )
    assert run.github.merges == []


def test_a_merge_check_that_cannot_be_read_merges_nothing(world, capsys) -> None:
    run = world()
    run.merge_problem = "the base origin/main could not be fetched: no network"
    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 2, out + err
    assert out.splitlines()[-1] == (
        f"{_MERGE_CHECK}: the change check on {_short(run.github.head)} merged with main could "
        "not be read — the base origin/main could not be fetched: no network. Nothing was "
        f"merged; run `land-work {ISSUE}` again"
    )
    assert run.github.merges == []


def test_a_dry_run_checks_the_merge_and_merges_nothing(world, capsys) -> None:
    run = world()
    assert run.run(capsys=capsys)[0] == 8  # reviewed: a dry run now has nothing to wait for
    run.merge_refused = [_FRICTION]
    rc, out, err = run.run("--dry-run", capsys=capsys)
    assert rc == 1, out + err
    assert out.splitlines()[-1].startswith(f"{_MERGE_CHECK}: refused — ")
    assert run.github.merges == []


def _commit_files(work: Path, message: str, files: dict[str, str]) -> str:
    for path, text in files.items():
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_text(text, encoding="utf-8")
    # The friction settings sit under `.pkit/`, which the clone ignores.
    _git(work, "add", "-f", *files)
    _git(work, "commit", "-q", "-m", message)
    return _git(work, "rev-parse", "HEAD")


def test_landing_the_second_of_two_changes_that_pass_alone_is_refused(
    world, capsys, monkeypatch, pkit_on_path
) -> None:
    """The race of #2228, through the real change check: another change adds a page
    anchored to the engine, and the PR changes the engine. Each passes alone, so the
    PR stops ready. Once the other lands on the origin, landing the PR is refused,
    naming the page, and nothing merges."""
    run = world()
    work = run.work
    monkeypatch.setattr(run.land.friction_answers, "merged", run.real_merged)
    _git(work, "switch", "-q", "main")
    config = {".pkit/project/config.yaml": friction_config(mode="enforcing"), **SOURCE}
    base = _commit_files(work, "friction", config)
    _git(work, "push", "-q", "origin", "main")
    _git(work, "switch", "-q", "-c", "anchor")
    _commit_files(
        work,
        "a page on the engine",
        {"docs/core.md": document("core", anchors={"path": ["src/core/**"]})},
    )
    _git(work, "switch", "-q", "-C", BRANCH, base)
    head = _commit_files(work, "change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    _git(work, "push", "-q", "-f", "origin", BRANCH)
    run.github.head = head
    run.github.checks[head] = [_GREEN]
    # The backbone's reading of the base: the origin's main, a remote's, so it is fetched.
    settled = run.land.friction_answers.default_branch
    monkeypatch.setattr(settled, "_read", {})

    def ask(explicit: str | None, _run: Any) -> Any:
        tip = _git(work, "rev-parse", "origin/main")
        branch = settled.Branch("main", False, "origin/main", tip, None)
        return settled.Reading(branch, settled.Base("origin/main", tip, None, None, "remote"))

    monkeypatch.setattr(settled, "_ask", ask)

    rc, out, err = run.run(capsys=capsys)
    assert rc == 8, out + err
    assert _merge_check_line(out).startswith(
        f"{_MERGE_CHECK}: the change check passes on {_short(head)}"
    )

    # The other change lands on the origin; this clone's origin/main is left behind,
    # so only the fetch the step makes shows it.
    _git(work, "switch", "-q", "main")
    _git(work, "merge", "--squash", "-q", "anchor")
    _git(work, "commit", "-q", "-m", "a page on the engine (#7)")
    landed = _git(work, "rev-parse", "HEAD")
    _git(work, "push", "-q", "origin", "main")
    _git(work, "update-ref", "refs/remotes/origin/main", base)
    _git(work, "switch", "-q", BRANCH)

    rc, out, err = run.authorised(capsys=capsys)
    assert rc == 1, out + err
    last = out.splitlines()[-1]
    assert last.startswith(
        f"{_MERGE_CHECK}: refused — the change check fails on {_short(head)} merged with main at "
        f"{_short(landed)}, on 1 document (docs/core.md), above."
    ), last
    assert any(line.startswith("  docs/core.md: friction — ") for line in out.splitlines())
    assert (run.github.merges, run.after_merge) == ([], [])


# ---- which heads may start programs (DEC-067) ---------------------------------


#: The line `land-work` says of a head from elsewhere, and how its stop goes on.
_STOPPED = "a person at a terminal can run `land-work 42` and name the head"
_NO_ANSWER = "through `done-work` or `merge-pr` runs no change check and tells no answer"


def _real_change_check(run: _Run, monkeypatch: pytest.MonkeyPatch) -> None:
    """The run reads the real change check at every step."""
    fa = run.land.friction_answers
    monkeypatch.setattr(fa, "merged", run.real_merged)
    monkeypatch.setattr(fa, "derive", run.real_derive)
    monkeypatch.setattr(fa, "checked", run.real_checked)


def _base_with_a_kind(
    run: _Run, make_adopter_repo: MakeAdopterRepo, tmp_path: Path, *, anchored: bool
) -> Path:
    """The clone's `main` holds the backbone, the friction settings and a registered
    kind, with a document anchored through it where `anchored` says. Pushed, and the
    resolver's path returned."""
    work = run.work
    installed = make_adopter_repo(root=tmp_path / "installed", chdir=False)
    shutil.copytree(
        installed.root / ".pkit",
        work / ".pkit",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    _git(work, "switch", "-q", "main")
    capability = register_kinds(work, "kinds", kinds={"source": "resolve"}, script_body=RESOLVING)
    files = {CONFIG: friction_config(mode="enforcing"), **SOURCE, "sources/alpha.md": "alpha\n"}
    if anchored:
        files["docs/sourced.md"] = document("sourced", anchors={"source": ["alpha"]})
    for path, text in files.items():
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_text(text, encoding="utf-8")
    _git(work, "add", "-f", ".pkit", *files)
    _git(work, "commit", "-q", "-m", "base")
    _git(work, "push", "-q", "origin", "main")
    return capability / RESOLVER


def _replace_the_resolver(run: _Run, resolver: Path, ran: Path) -> str:
    """The PR's head is a commit that replaces `resolver` with one that leaves `ran`
    behind, with checks green. The clone stays on `main`, so a tree of the person's."""
    work = run.work
    _git(work, "switch", "-q", "-C", BRANCH, "main")
    planted = resolver.read_text(encoding="utf-8") + f"open({str(ran)!r}, 'w').close()\n"
    head = _commit_files(work, "a resolver of its own", {str(resolver.relative_to(work)): planted})
    _git(work, "push", "-q", "-f", "origin", BRANCH)
    _git(work, "switch", "-q", "main")
    run.github.head = head
    run.github.checks[head] = [_GREEN]
    return head


def _track_the_origin(run: _Run, monkeypatch: pytest.MonkeyPatch) -> None:
    """The backbone's reading of the base: the origin's main, a remote's, so it is fetched
    and a commit landed there is what the merge is built with."""
    settled = run.land.friction_answers.default_branch
    monkeypatch.setattr(settled, "_read", {})

    def ask(explicit: str | None, _run: Any) -> Any:
        tip = _git(run.work, "rev-parse", "origin/main")
        branch = settled.Branch("main", False, "origin/main", tip, None)
        return settled.Reading(branch, settled.Base("origin/main", tip, None, None, "remote"))

    monkeypatch.setattr(settled, "_ask", ask)


@pytest.fixture
def replaced(
    world, make_adopter_repo, tmp_path_factory, monkeypatch, pkit_on_path
) -> Callable[..., tuple[_Run, str, Path]]:
    """A world whose PR head replaced the resolver its anchors need, read through a real
    backbone: the run, the head and the file the head's program leaves behind."""

    def build() -> tuple[_Run, str, Path]:
        run = world()
        _real_change_check(run, monkeypatch)
        scratch = tmp_path_factory.mktemp("outside-the-repository")
        resolver = _base_with_a_kind(run, make_adopter_repo, scratch, anchored=True)
        _track_the_origin(run, monkeypatch)
        ran = scratch / "the-head-s-resolver-ran"
        return run, _replace_the_resolver(run, resolver, ran), ran

    return build


@pytest.mark.process(
    "the landing route end to end: only a real change check refuses, and only a real "
    "resolver started from a checkout shows the mark this test reads means a start"
)
def test_a_fork_s_head_that_replaced_a_resolver_starts_nothing_and_merges_nothing(
    replaced, capsys
) -> None:
    """Off a terminal the run stops before any wait or review, with a code of its own,
    and its line says why, that a second run changes nothing, how a person goes on and
    what the other merge commands leave out (DEC-067 points 3 and 9)."""
    run, head, ran = replaced()
    run.github.cross_repository = True
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_PERSON == 9, out + err
    assert not ran.exists()
    assert (run.github.merges, run.invoked, run.github.comments) == ([], [], [])
    assert f"head: {_short(head)} is from elsewhere — it lies in another repository" in out
    last = out.splitlines()[-1]
    assert f"PR #{PR}'s head {_short(head)} is from elsewhere" in last
    assert "A second run changes nothing" in last
    assert _STOPPED in last and _NO_ANSWER in last
    assert "ci:" not in out


@pytest.mark.process("the landing route end to end, through a real change check")
def test_a_reading_that_does_not_place_the_head_is_never_a_pass(replaced, capsys) -> None:
    """A host that did not say where the head lies gives no checkout (DEC-067 point 1)."""
    run, _head, ran = replaced()
    run.github.cross_repository = None
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_PERSON, out + err
    assert not ran.exists()
    assert "the host did not say it lies in the base's repository" in out


@pytest.mark.process("the landing route end to end, through a real change check")
def test_a_head_on_the_base_s_repository_keeps_its_checkout_and_runs_as_before(
    replaced, capsys
) -> None:
    """A head that passes the test takes its checkout where an anchor needs one, and the
    run says nothing of the test: a writer's head lands as it did (DEC-067 point 8)."""
    run, head, ran = replaced()
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY, out + err
    assert ran.exists()
    assert "elsewhere" not in out + err
    assert run.confined == [False] * len(PANEL)
    assert out.splitlines()[0].startswith(f"head: {_short(head)} (PR #{PR}, {BRANCH})")


@pytest.mark.process("the landing route end to end, through a real change check")
def test_a_run_authorised_up_front_stops_even_at_a_terminal(replaced, capsys, monkeypatch) -> None:
    """No flag gives the word, and neither does a dry run (DEC-067 point 4)."""
    run, head, ran = replaced()
    run.github.cross_repository = True
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)

    def no_question(_prompt: str = "") -> str:
        raise AssertionError("nobody may be asked here")

    monkeypatch.setattr("builtins.input", no_question)
    rc, out, err = run.run("--yes", "--expect-head", head, capsys=capsys)
    assert rc == run.land.EXIT_PERSON, out + err
    rc, out, err = run.run("--dry-run", capsys=capsys)
    assert rc == run.land.EXIT_PERSON, out + err
    assert not ran.exists() and run.github.comments == []


@pytest.mark.process("the landing route end to end, through a real change check")
def test_a_named_head_starts_its_programs_for_that_run_alone(replaced, capsys, monkeypatch) -> None:
    """The short id typed at a terminal starts the head's programs for that run, after a
    comment names the commit, the command and who named it. The next run asks again,
    and a wrong word starts nothing (DEC-067 point 4)."""
    run, head, ran = replaced()
    run.github.cross_repository = True
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    prompts: list[str] = []
    replies = iter(["no", _short(head), "n", _short(head), "n"])

    def answer(prompt: str = "") -> str:
        prompts.append(prompt)
        if "Type" in prompt:
            assert ran.exists() is False, "a program started before the person was asked"
        return next(replies)

    monkeypatch.setattr("builtins.input", answer)

    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_PERSON, out + err
    assert not ran.exists() and run.github.comments == []
    assert head in out and f"gh pr diff {PR}" in out

    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY, out + err
    assert ran.exists()
    (word,) = [c["body"] for c in run.github.comments if f"named head {head}" in c["body"]]
    assert "octocat" in word and "`land-work`" in word
    # The reviewers the run starts are covered by the word.
    assert run.confined and not any(run.confined)

    ran.unlink()
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY, out + err
    assert len([p for p in prompts if "Type" in p]) == 3
    assert ran.exists()
    assert len([c for c in run.github.comments if f"named head {head}" in c["body"]]) == 2


@pytest.mark.process("the landing route end to end, through a real change check")
def test_a_word_with_no_comment_posted_starts_nothing(replaced, capsys, monkeypatch) -> None:
    run, head, ran = replaced()
    run.github.cross_repository = True
    run.github.fails.append(lambda argv: argv[:2] == ["pr", "comment"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": _short(head))
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_PERSON, out + err
    assert not ran.exists()
    assert "could not be posted" in out


@pytest.mark.process(
    "the merge check's route end to end: only a real change check, reading a real merge "
    "from git objects, shows the head's own check passing where its merge is refused"
)
def test_a_merge_needing_a_resolver_its_head_did_not_stops_the_same_way(
    world, make_adopter_repo, tmp_path_factory, monkeypatch, pkit_on_path, capsys
) -> None:
    """The base adds an anchor of the kind whose script the head replaced: the head's
    own check starts nothing and passes, and the merge is refused away from a checkout.
    It must not take one (DEC-067 point 3). Reviewers start under the brief."""
    run = world()
    _real_change_check(run, monkeypatch)
    scratch = tmp_path_factory.mktemp("outside-the-repository")
    resolver = _base_with_a_kind(run, make_adopter_repo, scratch, anchored=False)
    _track_the_origin(run, monkeypatch)
    ran = scratch / "the-head-s-resolver-ran"
    head = _replace_the_resolver(run, resolver, ran)
    work = run.work
    _commit_files(
        work,
        "a page anchored through the kind",
        {"docs/sourced.md": document("sourced", anchors={"source": ["alpha"]})},
    )
    _git(work, "push", "-q", "origin", "main")
    run.github.cross_repository = True

    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_PERSON, out + err
    assert not ran.exists()
    assert run.confined and all(run.confined)
    assert run.github.merges == []
    last = out.splitlines()[-1]
    assert last.startswith(f"merge check: stopped — PR #{PR}'s head {_short(head)}"), last
    assert _STOPPED in last


def test_two_open_prs_sharing_the_branch_s_name_stop_the_run(world, capsys, monkeypatch) -> None:
    """One may be a fork's, so the run names both and starts nothing (DEC-067 point 1)."""
    run = world()
    fork = {"number": 77, "headRefName": BRANCH, "isCrossRepository": True}
    real = run.land.done_work._lookup_prs

    def both(branch: str, state: str, fields: str, config: dict) -> Any:
        found = real(branch, state, fields, config)
        return replace(found, prs=(*found.prs, fork))

    monkeypatch.setattr(run.land.done_work, "_lookup_prs", both)
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE, out + err
    assert f"#{PR} and #77 share the branch name {BRANCH}" in out.splitlines()[-1]
    assert run.invoked == [] and run.github.merges == []


def test_a_head_holding_a_build_s_commits_is_from_elsewhere(world, capsys, monkeypatch) -> None:
    """A build's commits fail the test on the base's own repository (DEC-067 point 1), and
    where no anchor needs a resolver the run goes on, its reviewers told to start nothing."""
    run = world()
    monkeypatch.setattr(
        run.land.head_programs, "build_commits", lambda *a: frozenset({run.github.head})
    )
    monkeypatch.setattr(run.land.head_programs, "_held", lambda head, base, named, source: (head,))
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY, out + err
    assert f"it holds commits of a sandboxed build ({_short(run.github.head)})" in out
    assert run.confined == [True] * len(PANEL)


def test_build_records_that_cannot_be_read_fail_the_test(world, capsys, monkeypatch) -> None:
    run = world()
    monkeypatch.setattr(run.land.head_programs, "build_commits", lambda *a: "gh exited 1")
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY, out + err
    assert "#42's build records could not be read (gh exited 1)" in out
    assert run.confined == [True] * len(PANEL)


@pytest.mark.parametrize(
    ("standing", "expected"),
    [
        pytest.param({}, True, id="passed"),
        pytest.param({"elsewhere": "a fork's", "named": True}, False, id="named"),
        pytest.param({"elsewhere": "a fork's"}, False, id="from-elsewhere"),
    ],
)
def test_an_earlier_head_takes_a_checkout_only_where_the_head_passed(
    land, monkeypatch, standing, expected
) -> None:
    """The test's answer holds for an earlier head an authorisation names, and a person's
    word does not: it covers the commit named (DEC-067 points 1 and 4)."""
    asked: list[bool] = []

    def checked(head: str, base: str, *, source: Any = None, from_checkout: bool = True) -> Any:
        asked.append(from_checkout)
        return land.friction_answers.Derivation(head, problem="unread")

    monkeypatch.setattr(land.friction_answers, "checked", checked)
    monkeypatch.setattr(land.friction_answers, "left_out", lambda _document: ["left"])
    head = land._Head(
        ISSUE,
        PR,
        BRANCH,
        "a" * 40,
        base="main",
        remote="origin",
        base_branch="main",
        authorised="b" * 40,
        standing=land.head_programs.Standing("a" * 40, **standing),
    )
    assert "unread" in land._left_moved(head, {})
    assert asked == [expected]


def test_what_a_head_says_reaches_the_terminal_escaped(world, capsys) -> None:
    """A problem the change check states can hold a control character, which could move
    the cursor or erase the lines the person is reading (DEC-067 point 7)."""
    run = world()
    run.merge_problem = "docs/\x1b[2Ka.md\u202e is odd\r\nnext line"
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_UNREADABLE, out + err
    assert "\x1b" not in out + err and "\u202e" not in out + err
    assert "\\x1b[2Ka.md\\u202e is odd" in out


def test_a_grant_s_words_reach_the_terminal_escaped(world, capsys, monkeypatch) -> None:
    """What the head wrote into the fixers' grant list is printed with the rest."""
    run = world()
    fixers = run.land.fixers
    change = fixers.GrantChange("fix\x1b[1Aer", "page\x1b]0;x\x07", True, fixers.GRANTED)
    monkeypatch.setattr(fixers, "change_between", lambda *a: (change,))
    rc, out, err = run.run(capsys=capsys)
    assert rc == run.land.EXIT_READY, out + err
    assert "\x1b" not in out + err and "\x07" not in out + err
    assert "\\x1b[1A" in out
