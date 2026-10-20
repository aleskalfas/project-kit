"""Whether a run of the required `checks` job may be the short check (#1798, ADR-067).

`scripts/short_check.py` answers `full` or `short`. These tests hold its decision:

- **the short check** where the most recent full run on the pull request passed, a
  short run between them passed over, and `pkit friction since` says only answers
  changed since that run's head;
- **a full run** on every other path, and on every doubt: another event, a pull
  request from another repository, a re-run, a branch another pull request has had
  as its head, a base that was changed, no full run, a most recent full run that
  failed or was cancelled though an older one passed, a run that has not finished
  or ran neither step, a run listed for no pull request or another, more runs than
  are read, a checkout that is not the merge of the head, a change outside the
  answers, a rewritten branch, an answer from GitHub or from `pkit` that cannot be
  read or does not hold together, and the script's own fault;
- **what it reads**: only runs of this workflow, on this repository's branch,
  started before this run; the branch's name only as a query value; `pkit friction
  since` in the tree the script lies in, with no token in its environment;
- **what it writes**: `mode=` once, last, and the reason in the job's summary, with
  what the author named in code spans;
- **the tests the short check runs**: the two the record names keep the `answers`
  mark.

GitHub is a fake that answers the listing of runs, each run's jobs, the branch's pull
requests and the pull request's events. One test runs the real `pkit friction since`
over a real history.
"""

from __future__ import annotations

import ast
import json
import os
import stat
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from scripts import short_check as sc

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T2, friction_config, guide

REPOSITORY = "owner/project"
NUMBER = 7
HEAD = "a" * 40
BASIS = "b" * 40
OLDER = "c" * 40
THIS_RUN = 100
PAGE = "docs/guide.md"


# --- GitHub, faked ------------------------------------------------------------------


def _run(
    number: int,
    head: str = BASIS,
    *,
    status: str = "completed",
    conclusion: str | None = "success",
    pr: int = NUMBER,
    repository: str = REPOSITORY,
    event: str = "pull_request",
    path: str = sc.WORKFLOW_PATH,
) -> dict[str, Any]:
    return {
        "id": number * 1000,
        "run_number": number,
        "head_sha": head,
        "status": status,
        "conclusion": conclusion,
        "event": event,
        "path": path,
        "html_url": f"https://github.com/{REPOSITORY}/actions/runs/{number * 1000}",
        "head_repository": {"full_name": repository},
        "pull_requests": [{"number": pr}],
    }


def _job(
    head: str = BASIS,
    *,
    full: str | None = "success",
    short: str | None = "skipped",
    conclusion: str = "success",
    status: str = "completed",
    name: str = sc.JOB,
) -> dict[str, Any]:
    steps = [{"name": "Set up job", "conclusion": "success"}]
    if full is not None:
        steps.append({"name": sc.FULL_STEP, "conclusion": full})
    if short is not None:
        steps.append({"name": sc.SHORT_STEP, "conclusion": short})
    return {
        "name": name,
        "head_sha": head,
        "status": status,
        "conclusion": conclusion,
        "steps": steps,
    }


FULL_PASSED = _job()
FULL_FAILED = _job(full="failure", conclusion="failure")
SHORT_PASSED = _job(full="skipped", short="success")
SHORT_FAILED = _job(full="skipped", short="failure", conclusion="failure")


class GitHub:
    """Answers the listing of runs, a page at a time, each run's jobs, the pull requests
    of the branch and the pull request's events, a page at a time. Logs each path."""

    def __init__(
        self,
        runs: list[dict[str, Any]],
        jobs: Mapping[int, dict[str, Any]],
        *,
        pulls: list[Any] | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.runs = runs
        self.jobs = jobs
        self.pulls: Any = [{"number": NUMBER}] if pulls is None else pulls
        self.events = ["labeled", "head_ref_force_pushed"] if events is None else events
        self.asked: list[str] = []

    def __call__(self, path: str) -> Any:
        self.asked.append(path)
        url = urlsplit(path)
        query = parse_qs(url.query)
        if url.path == f"repos/{REPOSITORY}/actions/workflows/{sc.WORKFLOW_FILE}/runs":
            size, page = int(query["per_page"][0]), int(query["page"][0])
            return {"workflow_runs": self.runs[(page - 1) * size : page * size]}
        if url.path == f"repos/{REPOSITORY}/pulls":
            return self.pulls
        if url.path == f"repos/{REPOSITORY}/issues/{NUMBER}/events":
            size, page = int(query["per_page"][0]), int(query["page"][0])
            return [{"event": e} for e in self.events[(page - 1) * size : page * size]]
        run_id = int(url.path.split("/")[-2])
        job = self.jobs[run_id // 1000]
        return {"jobs": [{**job, "head_sha": job["head_sha"]}]}


def _pairs(
    *pairs: tuple[dict[str, Any], dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    """Runs newest first, and each one's `checks` job by its number."""
    return [run for run, _ in pairs], {run["run_number"]: job for run, job in pairs}


def _github(*pairs: tuple[dict[str, Any], dict[str, Any]]) -> GitHub:
    """Runs newest first, each with its `checks` job, on a branch of this pull request
    alone, whose base never changed."""
    return GitHub(*_pairs(*pairs))


def _since_document(
    since: str = BASIS,
    head: str = HEAD,
    *,
    outside: list[dict[str, Any]] | None = None,
    reason: str | None = None,
    version: int = sc.SINCE_SCHEMA_VERSION,
) -> dict[str, Any]:
    outside = outside or []
    return {
        "schema_version": version,
        "report": "since",
        "since": since,
        "head": head,
        "base": {"ref": "origin/main", "tip": OLDER},
        "all_inside": reason is None and not outside,
        "reason": reason,
        "commits": [],
        "inside": [PAGE],
        "outside": outside,
    }


class Since:
    """`pkit friction since`, answering one document and logging what it was asked."""

    def __init__(self, document: Any = None, error: str | None = None) -> None:
        self.document = _since_document() if document is None else document
        self.error = error
        self.asked: list[tuple[str, str, str]] = []

    def __call__(self, since: str, head: str, base: str) -> Any:
        self.asked.append((since, head, base))
        if self.error is not None:
            raise sc.Full(self.error)
        return self.document


def _event(
    tmp_path: Path,
    *,
    head: str = HEAD,
    branch: str = "feat/1-topic",
    repository: str = REPOSITORY,
    base: str = "main",
) -> Path:
    event = {
        "pull_request": {
            "number": NUMBER,
            "title": "a title the contributor chose, naming run #1 as its basis",
            "head": {"sha": head, "ref": branch, "repo": {"full_name": repository}},
            "base": {"ref": base},
        }
    }
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event), encoding="utf-8")
    return path


def _env(tmp_path: Path, event_name: str = "pull_request", **event: Any) -> dict[str, str]:
    return {
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_RUN_NUMBER": str(THIS_RUN),
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_EVENT_NAME": event_name,
        "GITHUB_EVENT_PATH": str(_event(tmp_path, **event)),
    }


def _merge_of(head: str = HEAD) -> Callable[[], str]:
    """The checkout's second parent: by default, the pull request's head."""
    return lambda: head


def _decide(tmp_path: Path, github: Callable[[str], Any], since: Since, **env: Any) -> sc.Decision:
    return sc.decide(_env(tmp_path, **env), github, since, _merge_of())


# --- the short check ----------------------------------------------------------------


def test_the_short_check_where_the_most_recent_full_run_passed_and_only_answers_changed(
    tmp_path: Path,
) -> None:
    github = _github((_run(90), FULL_PASSED))
    since = Since()

    decision = _decide(tmp_path, github, since)

    assert decision.mode == sc.SHORT
    assert decision.basis is not None and decision.basis.head == BASIS
    assert since.asked == [(BASIS, HEAD, "origin/main")]
    assert "run #90 on bbbbbbb, passed" in decision.why


@pytest.mark.parametrize("short", [SHORT_PASSED, SHORT_FAILED], ids=["passed", "failed"])
def test_a_short_run_is_passed_over_for_the_full_run_before_it(
    tmp_path: Path, short: dict[str, Any]
) -> None:
    github = _github((_run(95, OLDER), {**short, "head_sha": OLDER}), (_run(90), FULL_PASSED))
    since = Since()

    decision = _decide(tmp_path, github, since)

    assert decision.mode == sc.SHORT
    assert since.asked == [(BASIS, HEAD, "origin/main")]


def test_the_runs_are_read_newest_first_by_their_number(tmp_path: Path) -> None:
    """The listing's order is not trusted: the run with the highest number decides."""
    github = _github((_run(80, OLDER), {**FULL_FAILED, "head_sha": OLDER}), (_run(90), FULL_PASSED))

    decision = _decide(tmp_path, github, Since())

    assert decision.mode == sc.SHORT
    assert decision.basis is not None and decision.basis.number == 90


# --- a full run ---------------------------------------------------------------------


def test_a_failed_full_run_is_never_hidden_by_an_older_one_that_passed(tmp_path: Path) -> None:
    """A clean merge of the base whose full run fails, then a push of answers only:
    keyed on the last head that passed, the short check would pass. The most recent
    full run decides, so the run is full."""
    github = _github(
        (_run(95, OLDER), {**FULL_FAILED, "head_sha": OLDER}),
        (_run(90), FULL_PASSED),
    )
    since = Since()

    decision = _decide(tmp_path, github, since)

    assert decision.mode == sc.FULL
    assert "run #95 on ccccccc, did not pass" in decision.why
    assert since.asked == []


@pytest.mark.parametrize(
    ("run", "job"),
    [
        (_run(95, conclusion="cancelled"), _job(full="cancelled", conclusion="cancelled")),
        (_run(95, conclusion="failure"), _job(full="success", conclusion="failure")),
        (_run(95, conclusion="success"), _job(full="failure", conclusion="success")),
    ],
    ids=["cancelled", "the-run-failed-after-the-aggregator", "the-step-failed"],
)
def test_a_full_run_that_did_not_wholly_pass_is_no_basis(
    tmp_path: Path, run: dict[str, Any], job: dict[str, Any]
) -> None:
    decision = _decide(tmp_path, _github((run, job), (_run(90), FULL_PASSED)), Since())

    assert decision.mode == sc.FULL
    assert "did not pass" in decision.why


@pytest.mark.parametrize("status", ["in_progress", "queued"])
def test_an_earlier_run_that_has_not_finished_makes_the_run_full(
    tmp_path: Path, status: str
) -> None:
    """It may be a full run that is about to fail."""
    github = _github(
        (_run(95, OLDER, status=status, conclusion=None), _job(OLDER)),
        (_run(90), FULL_PASSED),
    )

    decision = _decide(tmp_path, github, Since())

    assert decision.mode == sc.FULL
    assert "has not finished" in decision.why


@pytest.mark.parametrize(
    "job",
    [
        _job(full=None, short=None, conclusion="failure"),
        _job(full="skipped", short="skipped", conclusion="failure"),
        _job(full="success", short="success"),
        _job(name="something else"),
        _job(status="in_progress"),
        _job(head=OLDER),
    ],
    ids=["neither-step", "both-skipped", "both-ran", "no-checks-job", "job-unfinished", "job-head"],
)
def test_a_run_that_cannot_be_told_makes_the_run_full(tmp_path: Path, job: dict[str, Any]) -> None:
    decision = _decide(tmp_path, _github((_run(95), job), (_run(90), FULL_PASSED)), Since())

    assert decision.mode == sc.FULL


def test_no_full_run_on_the_pull_request_makes_the_run_full(tmp_path: Path) -> None:
    decision = _decide(tmp_path, _github((_run(95), SHORT_PASSED)), Since())

    assert decision.mode == sc.FULL
    assert "no full run on this pull request was found among its 1 earlier runs" in decision.why


@pytest.mark.parametrize(
    "run",
    [
        _run(90, repository="someone/fork"),
        _run(90, event="push"),
        _run(90, path=".github/workflows/other.yml"),
        _run(THIS_RUN),
        _run(THIS_RUN + 1),
    ],
    ids=["another-repository", "another-event", "another-workflow", "this", "later"],
)
def test_only_earlier_runs_of_this_workflow_on_this_pull_request_count(
    tmp_path: Path, run: dict[str, Any]
) -> None:
    decision = _decide(tmp_path, _github((run, FULL_PASSED)), Since())

    assert decision.mode == sc.FULL
    assert "no full run on this pull request" in decision.why


@pytest.mark.parametrize("pulls", [[{"number": 8}], [], None], ids=["another", "none", "missing"])
def test_a_run_on_the_branch_not_listed_for_this_pull_request_makes_the_run_full(
    tmp_path: Path, pulls: Any
) -> None:
    """Passed over, a failed full run GitHub listed for no pull request would let an
    older one that passed be the basis."""
    failed = {**_run(95), "pull_requests": pulls}
    github = _github((failed, FULL_FAILED), (_run(90), FULL_PASSED))

    decision = _decide(tmp_path, github, Since())

    assert decision.mode == sc.FULL
    assert "run #95 on the branch is not listed for this pull request" in decision.why


@pytest.mark.parametrize("parent", [OLDER, None], ids=["another-head", "no-merge"])
def test_a_checkout_that_is_not_the_merge_of_the_head_makes_the_run_full(
    tmp_path: Path, parent: str | None
) -> None:
    """The aggregator runs on the checkout: the head judged must be the head it merges."""
    github = _github((_run(90), FULL_PASSED))

    decision = sc.decide(_env(tmp_path), github, Since(), lambda: parent)

    assert decision.mode == sc.FULL
    assert "not a merge of the pull request's head" in decision.why


def test_a_change_outside_the_answers_makes_the_run_full_and_is_named(tmp_path: Path) -> None:
    outside = [{"path": "src/cli/main.py", "commit": HEAD, "why": "not an artefact's file"}]
    since = Since(_since_document(outside=outside))

    decision = _decide(tmp_path, _github((_run(90), FULL_PASSED)), since)

    assert decision.mode == sc.FULL
    assert "`src/cli/main.py` (aaaaaaa: `not an artefact's file`)" in decision.why


def test_a_rewritten_branch_makes_the_run_full(tmp_path: Path) -> None:
    reason = "aaaaaaa does not descend from bbbbbbb: the branch was rebased or force-pushed"
    since = Since(_since_document(reason=reason))

    decision = _decide(tmp_path, _github((_run(90), FULL_PASSED)), since)

    assert decision.mode == sc.FULL
    assert reason in decision.why


@pytest.mark.parametrize(
    "document",
    [
        _since_document(version=2),
        _since_document(since=OLDER),
        _since_document(head=OLDER),
        {**_since_document(), "all_inside": "yes"},
        {**_since_document(), "outside": [{"path": "x"}]},
        {**_since_document(reason="rebased"), "all_inside": True},
        ["not", "a", "document"],
    ],
    ids=[
        "version",
        "since",
        "head",
        "not-a-bool",
        "inside-but-names-a-change",
        "inside-but-a-reason",
        "list",
    ],
)
def test_an_answer_from_friction_since_that_does_not_hold_makes_the_run_full(
    tmp_path: Path, document: Any
) -> None:
    decision = _decide(tmp_path, _github((_run(90), FULL_PASSED)), Since(document))

    assert decision.mode == sc.FULL


def test_friction_since_that_cannot_answer_makes_the_run_full(tmp_path: Path) -> None:
    since = Since(
        error="`pkit friction since` could not answer: it exited 1: this clone is shallow"
    )

    decision = _decide(tmp_path, _github((_run(90), FULL_PASSED)), since)

    assert decision.mode == sc.FULL
    assert "shallow" in decision.why


@pytest.mark.parametrize("event_name", ["push", "merge_group", "pull_request_target"])
def test_only_a_pull_request_may_run_the_short_check(tmp_path: Path, event_name: str) -> None:
    github = _github((_run(90), FULL_PASSED))

    decision = _decide(tmp_path, github, Since(), event_name=event_name)

    assert decision.mode == sc.FULL
    assert github.asked == []


def test_a_pull_request_from_another_repository_runs_in_full(tmp_path: Path) -> None:
    github = _github((_run(90), FULL_PASSED))

    decision = _decide(tmp_path, github, Since(), repository="someone/fork")

    assert decision.mode == sc.FULL
    assert github.asked == []


@pytest.mark.parametrize(
    "event", [{"head": "not-a-commit"}, {"branch": ""}, {"base": "--upload-pack=x"}]
)
def test_an_event_that_does_not_say_what_is_checked_runs_in_full(
    tmp_path: Path, event: dict[str, str]
) -> None:
    decision = _decide(tmp_path, _github((_run(90), FULL_PASSED)), Since(), **event)

    assert decision.mode == sc.FULL


def test_a_listing_github_cannot_give_makes_the_run_full(tmp_path: Path) -> None:
    def refused(path: str) -> Any:
        raise sc.Full("GitHub's record of runs could not be read: `gh api` exited 1: HTTP 403")

    decision = _decide(tmp_path, refused, Since())

    assert decision.mode == sc.FULL
    assert "HTTP 403" in decision.why


def test_a_listing_with_no_runs_in_it_makes_the_run_full(tmp_path: Path) -> None:
    decision = _decide(tmp_path, lambda path: {"message": "Not Found"}, Since())

    assert decision.mode == sc.FULL


@pytest.mark.parametrize("attempt", ["2", "", None])
def test_a_re_run_runs_in_full(tmp_path: Path, attempt: str | None) -> None:
    """Its own first attempt is left out of the runs read: a full run that failed
    would otherwise pass on its re-run, with no suite, on the tree it failed on."""
    github = _github((_run(90), FULL_PASSED))
    env = _env(tmp_path)
    if attempt is None:
        del env["GITHUB_RUN_ATTEMPT"]
    else:
        env["GITHUB_RUN_ATTEMPT"] = attempt

    decision = sc.decide(env, github, Since(), _merge_of())

    assert decision.mode == sc.FULL
    assert "a re-run runs in full" in decision.why
    assert github.asked == []


@pytest.mark.parametrize(
    "pulls",
    [
        [{"number": NUMBER}, {"number": 3}],
        [{"number": 3}],
        [],
        {"message": "Not Found"},
        [{"number": NUMBER}] * sc.PAGE_SIZE,
    ],
    ids=["another-too", "only-another", "none", "not-a-list", "a-full-page"],
)
def test_a_branch_another_pull_request_has_had_as_its_head_runs_in_full(
    tmp_path: Path, pulls: Any
) -> None:
    """GitHub lists a branch's runs for each of its open pull requests: a run made for
    another, against another base, ran that base's workflow."""
    github = GitHub(*_pairs((_run(90), FULL_PASSED)), pulls=pulls)

    decision = _decide(tmp_path, github, Since())

    assert decision.mode == sc.FULL
    assert not any("/runs" in path for path in github.asked)


def test_a_pull_request_whose_base_was_changed_runs_in_full(tmp_path: Path) -> None:
    """A run made before the change ran the old base's workflow, which may run no suite."""
    github = GitHub(*_pairs((_run(90), FULL_PASSED)), events=["labeled", "base_ref_changed"])

    decision = _decide(tmp_path, github, Since())

    assert decision.mode == sc.FULL
    assert "base was changed" in decision.why


def test_the_events_are_read_a_page_at_a_time_up_to_their_bound(tmp_path: Path) -> None:
    late = ["labeled"] * sc.PAGE_SIZE + ["base_ref_changed"]
    assert _decide(
        tmp_path, GitHub(*_pairs((_run(90), FULL_PASSED)), events=late), Since()
    ).mode == (sc.FULL)
    endless = ["labeled"] * (sc.PAGE_SIZE * sc.PAGES)
    decision = _decide(tmp_path, GitHub(*_pairs((_run(90), FULL_PASSED)), events=endless), Since())
    assert decision.mode == sc.FULL
    assert "more events than the decider reads" in decision.why


# --- what it reads ------------------------------------------------------------------


def test_the_listing_is_read_a_page_at_a_time_up_to_its_bound(tmp_path: Path) -> None:
    shorts = [
        (_run(2000 - i, OLDER), {**SHORT_PASSED, "head_sha": OLDER}) for i in range(sc.PAGE_SIZE)
    ]
    github = _github(*shorts, (_run(10), FULL_PASSED))
    env = {**_env(tmp_path), "GITHUB_RUN_NUMBER": "2001"}

    decision = sc.decide(env, github, Since(), _merge_of())

    assert decision.mode == sc.SHORT
    listings = [path for path in github.asked if "/workflows/" in path]
    assert len(listings) == 2


def test_more_runs_than_the_pages_read_make_the_run_full(tmp_path: Path) -> None:
    """Runs past the bound are never read, so the decision would rest on the order GitHub
    lists them in: a full listing on the last page read is no basis, even with a full run
    that passed on it."""
    count = sc.PAGE_SIZE * sc.PAGES
    shorts = [
        (_run(2000 - i, OLDER), {**SHORT_PASSED, "head_sha": OLDER}) for i in range(count - 1)
    ]
    github = _github(*shorts, (_run(10), FULL_PASSED), (_run(5), FULL_PASSED))
    env = {**_env(tmp_path), "GITHUB_RUN_NUMBER": "2001"}

    decision = sc.decide(env, github, Since(), _merge_of())

    assert decision.mode == sc.FULL
    assert "more runs on the branch than the decider reads" in decision.why
    assert len([path for path in github.asked if "/workflows/" in path]) == sc.PAGES


def test_the_branch_name_is_only_a_query_value(tmp_path: Path) -> None:
    """A branch is the contributor's to name: it reaches the listing encoded, as one value."""
    github = _github((_run(90), FULL_PASSED))
    branch = "feat/x&branch=main#{owner}"

    _decide(tmp_path, github, Since(), branch=branch)

    pulls = next(path for path in github.asked if "/pulls?" in path)
    runs = next(path for path in github.asked if "/runs?" in path)
    assert parse_qs(urlsplit(pulls).query)["head"] == [f"owner:{branch}"]
    query = parse_qs(urlsplit(runs).query)
    assert query["branch"] == [branch]
    assert query["event"] == ["pull_request"]
    assert all("{owner}" not in path for path in github.asked)


def test_friction_since_runs_unrouted_with_no_token_in_the_decider_s_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It runs in the tree the script lies in, the base's on a pull request, never in
    the pull request's checkout, so the code `pkit` loads from its tree is the base's."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pkit = bin_dir / "pkit"
    pkit.write_text(
        '#!/bin/sh\nprintf \'{"args": "%s", "gh": "%s", "github": "%s", "route": "%s", '
        '"cwd": "%s"}\' "$*" "${GH_TOKEN:-}" "${GITHUB_TOKEN:-}" "${PKIT_NO_ROUTE:-}" "$PWD"\n',
        encoding="utf-8",
    )
    pkit.chmod(pkit.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    checkout = tmp_path / "the-pull-request-s-checkout"
    checkout.mkdir()
    monkeypatch.chdir(checkout)

    answered = sc.friction_since(BASIS, HEAD, "origin/main")

    assert Path(__file__).resolve().parents[1] == sc.ROOT
    assert answered == {
        "args": f"friction since {BASIS} --head {HEAD} --base origin/main --json",
        "gh": "",
        "github": "",
        "route": "1",
        "cwd": str(sc.ROOT),
    }


def test_the_commit_tested_is_read_as_the_checkout_s_second_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, make_adopter_repo: MakeAdopterRepo
) -> None:
    repo = make_adopter_repo()
    repo.write({"a.txt": "a\n"})
    repo.commit("start", files=None)
    assert sc.checkout_head() is None
    repo.checkout("topic", create=True)
    head = repo.commit("the head", {"b.txt": "b\n"})
    repo.checkout("main")
    repo.commit("the base moves", {"c.txt": "c\n"})
    repo.git("merge", "--no-ff", "-q", "-m", "merge", "topic")

    assert sc.checkout_head() == head


@pytest.mark.parametrize(
    ("script", "said"),
    [("echo 'HTTP 404: Not Found' >&2; exit 1", "HTTP 404"), ("echo 'not json'", "not JSON")],
    ids=["refused", "not-json"],
)
def test_gh_that_cannot_answer_is_a_full_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script: str, said: str
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    with pytest.raises(sc.Full, match=said):
        sc.gh_api("repos/owner/project/actions/runs/1/jobs")


# --- what it writes -----------------------------------------------------------------


def _outputs(tmp_path: Path) -> dict[str, str]:
    output, summary = tmp_path / "output", tmp_path / "summary"
    output.write_text("earlier=1\n", encoding="utf-8")
    summary.write_text("", encoding="utf-8")
    return {"GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)}


def test_main_writes_the_form_once_and_last_and_says_why(tmp_path: Path) -> None:
    files = _outputs(tmp_path)
    env = {**_env(tmp_path), **files}

    assert sc.main(env, _github((_run(90), FULL_PASSED)), Since(), _merge_of()) == 0

    assert Path(files["GITHUB_OUTPUT"]).read_text().splitlines() == ["earlier=1", "mode=short"]
    said = Path(files["GITHUB_STEP_SUMMARY"]).read_text()
    assert "The short check" in said
    assert "run #90 on bbbbbbb" in said
    assert "ADR-067" in said


def test_a_fault_of_its_own_is_a_full_run(tmp_path: Path) -> None:
    files = _outputs(tmp_path)
    env = {**_env(tmp_path), **files}

    def broken(path: str) -> Any:
        raise RuntimeError("a bug")

    assert sc.main(env, broken, Since(), _merge_of()) == 0

    assert Path(files["GITHUB_OUTPUT"]).read_text().splitlines()[-1] == "mode=full"
    assert (
        "could not be made (`RuntimeError: a bug`)"
        in Path(files["GITHUB_STEP_SUMMARY"]).read_text()
    )


def test_a_run_outside_a_workflow_is_full(tmp_path: Path) -> None:
    files = _outputs(tmp_path)

    sc.main(files, _github((_run(90), FULL_PASSED)), Since(), _merge_of())

    assert Path(files["GITHUB_OUTPUT"]).read_text().splitlines()[-1] == "mode=full"


def test_the_summary_escapes_control_characters(tmp_path: Path) -> None:
    said = sc.summary(sc.Decision(sc.FULL, "changes lie outside: src/x\x1b[8m.py"))

    assert "\x1b" not in said
    assert "src/x\\x1b[8m.py" in said


# --- end to end, over a real history ------------------------------------------------


@pytest.fixture
def history(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """A page on `main`, and a branch `topic` whose first commit changes the code."""
    repo = make_adopter_repo()
    repo.git("config", "core.autocrlf", "false")
    repo.write({CONFIG: friction_config(), **SOURCE, PAGE: guide()})
    repo.commit("start", files=None)
    repo.checkout("topic", create=True)
    return repo


def _decide_over(repo: AdopterRepo, tmp_path: Path, basis: str, head: str) -> sc.Decision:
    github = _github((_run(90, basis), {**FULL_PASSED, "head_sha": basis}))
    env = _env(tmp_path, head=head)
    return sc.decide(
        env,
        github,
        lambda s, h, b: sc.friction_since(s, h, "main", root=repo.root),
        _merge_of(head),
    )


def test_over_a_real_history_answers_are_short_and_code_is_full(
    history: AdopterRepo, tmp_path: Path
) -> None:
    basis = history.commit("the change", {"src/cli/main.py": "print('cli, renamed')\n"})
    answered = history.commit("answer again", {PAGE: guide(at=T2, because="renamed, still true")})

    assert _decide_over(history, tmp_path, basis, answered).mode == sc.SHORT

    coded = history.commit("a fix", {"src/core/engine.py": "ENGINE = 2\n"})
    decision = _decide_over(history, tmp_path, basis, coded)
    assert decision.mode == sc.FULL
    assert "src/core/engine.py" in decision.why


def test_over_a_real_history_a_rewritten_branch_is_full(
    history: AdopterRepo, tmp_path: Path
) -> None:
    basis = history.commit("the change", {"src/cli/main.py": "print('cli, renamed')\n"})
    history.checkout("main")
    history.checkout("rewritten", create=True)
    rewritten = history.commit("answer again", {PAGE: guide(at=T2, because="rewritten")})

    decision = _decide_over(history, tmp_path, basis, rewritten)

    assert decision.mode == sc.FULL
    assert "does not descend" in decision.why


# --- the tests the short check runs -------------------------------------------------


def _marked_answers(tree: ast.Module) -> set[str]:
    """The test functions of a module that carry `@pytest.mark.answers`."""
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and any(
            ast.unparse(d.func if isinstance(d, ast.Call) else d) == "pytest.mark.answers"
            for d in node.decorator_list
        )
    }


def test_the_tests_that_read_the_repository_s_answers_carry_the_mark() -> None:
    """The short check runs the tests marked `answers`, and passes where none is: a mark
    removed or renamed would empty it with no failure (ADR-067 point 8). So the full run
    holds the two tests the record names to the mark."""
    tests = Path(__file__).resolve().parent
    marked = {
        (path.name, name)
        for path in tests.glob("test_*.py")
        for name in _marked_answers(ast.parse(path.read_text(encoding="utf-8")))
    }

    assert {
        (
            "test_self_host_documentation.py",
            "test_every_declared_place_is_a_page_anchored_and_revalidated",
        ),
        (
            "test_software_analysis_rule_set.py",
            "test_the_judgement_rules_ship_proposed_declaring_no_check",
        ),
    } <= marked
