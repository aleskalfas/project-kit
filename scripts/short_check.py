"""Whether this run of the required `checks` job may be the short check (ADR-067).

`.github/workflows/checks.yml` runs this decider before the check aggregator. It
answers `full` or `short`, and the job runs `scripts/check.sh` or
`scripts/check.sh --short` by that answer. The short check is the aggregator
without its test suite. A run takes it only on a pull request, and only where:

- **a passing full run is the basis.** GitHub's own record of this workflow's
  runs is read through the Actions API, with the token the workflow holds. The
  runs kept are those of this workflow file, for `pull_request` events, on a
  branch of this repository, that GitHub lists for this pull request's number
  and that started before this run. Newest first, a short run is passed over,
  and the first full run decides: it must have finished with success, and its
  head is the basis. A run is told by its `checks` job's steps, as GitHub
  records them: `FULL_STEP` ran, or it was skipped and `SHORT_STEP` ran.
- **only answers changed since.** `pkit friction since <basis> --head <head>
  --base origin/<base> --json` says every change from the basis to the pull
  request's head lies inside `revalidated` blocks and `revisited` lists, a merge
  of the base counting only for what differs from git's merge of it. That
  command is the one home of the question (ADR-057 point 2), so this script
  reads no answer itself. GitHub lists a run for every pull request of its
  branch, so the basis is this pull request's only because `friction since`
  finds it on the head's own line of commits.

Everything else is a full run, and so is every doubt: another event, a pull
request from another repository, a re-run, a branch another pull request has
had as its head, a pull request whose base was changed, no full run among the
runs read, a full run that failed, was cancelled or has not finished, a run that
cannot be told, an answer from GitHub or from `pkit` that cannot be read. No
label, title, description, commit message or file of the pull request names the
basis: the branch's name only narrows the listing.

- **A re-run** runs in full. Its own first attempt is left out of the runs read,
  so a full run that failed could otherwise pass on its re-run with no suite.
- **Another pull request on the branch, or another base.** GitHub lists a run for
  every open pull request of its branch. A run made for another pull request, or
  against another base, ran that base's workflow, which may run no suite. So the
  branch must have been the head of this pull request alone, and its base never
  changed, by the pull request's events.

**Whose copy decides.** On a pull request the workflow runs the base's copy of
this script, in an environment built from the base's tree, so the `pkit` it asks
is the base's too. Both read this checkout's history. A pull request that
changes the decider, or the code behind `friction since`, is decided by the
code that passed `main`'s full run. On any other event the workflow runs this
tree's copy, which only says why the run is full. The workflow also lets no
other event run the short check, whatever this script says.

The answer goes to `$GITHUB_OUTPUT` as `mode=full` or `mode=short`, written
last, so a step that fails before it leaves no `short`. The reason goes to the
log and to the job's summary. The step's failure fails nothing: the workflow
lets it fail, and a run with no answer is full.

In the workflow, with `GH_TOKEN` set and the pull request's checkout as the
working directory:

    uv run --project <the base's tree> --frozen python <the base's tree>/scripts/short_check.py

It exits 0 whatever it decides.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

FULL = "full"
SHORT = "short"

#: The workflow whose runs are read, the job that is the required status, and the
#: names of its two steps that run the aggregator. The workflow's own steps carry
#: these names, and a test holds the two together.
WORKFLOW_FILE = "checks.yml"
WORKFLOW_PATH = f".github/workflows/{WORKFLOW_FILE}"
JOB = "checks"
FULL_STEP = "Run the check aggregator"
SHORT_STEP = "Run the short check"

#: How many runs a page of the listing holds, and how many pages are read. A basis
#: not found among them is no basis.
PAGE_SIZE = 100
PAGES = 3

#: The version of `pkit friction since --json` this script reads; a document of
#: another is no answer.
SINCE_SCHEMA_VERSION = 1
SINCE_TIMEOUT = 900
API_TIMEOUT = 60

#: How many changes outside the answers the reason names.
SHOWN = 5

_SHA = re.compile(r"[0-9a-f]{40}")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

#: The tokens the deciding step holds, kept from every command it starts but `gh`.
_TOKENS = ("GH_TOKEN", "GITHUB_TOKEN")

Api = Callable[[str], Any]
Since = Callable[[str, str, str], Any]


class Full(Exception):
    """The run is full, and why."""


@dataclass(frozen=True)
class PullRequest:
    number: int
    head: str
    branch: str
    base: str


@dataclass(frozen=True)
class Run:
    """A run of the workflow: its id, its number, its head and where it is shown."""

    id: int
    number: int
    head: str
    url: str

    def named(self) -> str:
        return f"run #{self.number} on {self.head[:7]}"


@dataclass(frozen=True)
class Decision:
    mode: str
    why: str
    basis: Run | None = None


# --- the pull request ---------------------------------------------------------------


def pull_request(event_name: str, event: Mapping[str, Any], repository: str) -> PullRequest:
    """The pull request this run checks, from the event GitHub wrote. Raises Full for
    any other event, or a pull request whose head is not a branch of this repository."""
    if event_name != "pull_request":
        raise Full(f"this is a `{event_name}` run, and the short check is for pull requests only")
    pr = _mapping(event.get("pull_request"))
    head = _mapping(pr.get("head"))
    base = _mapping(pr.get("base"))
    number, sha, branch = pr.get("number"), head.get("sha"), head.get("ref")
    base_ref = base.get("ref")
    if _mapping(head.get("repo")).get("full_name") != repository:
        raise Full("the pull request's head is not a branch of this repository")
    if not (
        isinstance(number, int)
        and number > 0
        and isinstance(sha, str)
        and _SHA.fullmatch(sha)
        and isinstance(branch, str)
        and branch
        and isinstance(base_ref, str)
        and base_ref
        and not base_ref.startswith("-")
    ):
        raise Full("the event does not say which pull request, head and base this run checks")
    return PullRequest(number, sha, branch, base_ref)


def first_attempt(env: Mapping[str, str]) -> None:
    """Return where this is the run's first attempt. A re-run runs in full: its own
    first attempt is left out of the runs read, so a full run that failed could
    otherwise pass on its re-run with no suite, on the tree it failed on."""
    attempt = env.get("GITHUB_RUN_ATTEMPT")
    if attempt != "1":
        raise Full(f"this is attempt {attempt or 'unknown'} of the run, and a re-run runs in full")


def one_pull_request(api: Api, repository: str, pr: PullRequest) -> None:
    """Return where no other pull request, open or closed, has had this branch as its
    head. GitHub lists a branch's runs for each of its open pull requests, so one made
    for another pull request, against another base, could pass as this one's."""
    owner = repository.split("/", 1)[0]
    head = quote(f"{owner}:{pr.branch}", safe="")
    listed = api(f"repos/{repository}/pulls?head={head}&state=all&per_page={PAGE_SIZE}")
    if not isinstance(listed, list) or len(cast("list[Any]", listed)) >= PAGE_SIZE:
        raise Full("the pull requests of this branch cannot be listed whole")
    numbers = {_mapping(p).get("number") for p in cast("list[Any]", listed)}
    if numbers != {pr.number}:
        others = sorted(n for n in numbers if isinstance(n, int) and n != pr.number)
        named = ", ".join(f"#{n}" for n in others) or "none of them this one"
        raise Full(f"another pull request has had this branch as its head ({named})")


def base_unchanged(api: Api, repository: str, pr: PullRequest) -> None:
    """Return where the pull request's base was never changed, by its events. A run
    made against another base ran that base's workflow, which may run no suite."""
    for page in range(1, PAGES + 1):
        items = api(
            f"repos/{repository}/issues/{pr.number}/events?per_page={PAGE_SIZE}&page={page}"
        )
        if not isinstance(items, list):
            raise Full("the pull request's events cannot be read")
        events = [_mapping(item).get("event") for item in cast("list[Any]", items)]
        if "base_ref_changed" in events:
            raise Full(
                "the pull request's base was changed, so an earlier run may have run "
                "another base's workflow"
            )
        if len(events) < PAGE_SIZE:
            return
    raise Full("the pull request has more events than the decider reads")


# --- the basis ----------------------------------------------------------------------


def earlier_runs(
    api: Api, repository: str, pr: PullRequest, before: int
) -> list[Mapping[str, Any]]:
    """This workflow's runs on the pull request that started before run number
    `before`, newest first. Raises Full when no listing can be read."""
    runs: list[Mapping[str, Any]] = []
    branch = quote(pr.branch, safe="")
    for page in range(1, PAGES + 1):
        listed = _mapping(
            api(
                f"repos/{repository}/actions/workflows/{WORKFLOW_FILE}/runs"
                f"?event=pull_request&branch={branch}&per_page={PAGE_SIZE}&page={page}"
            )
        )
        page_runs = listed.get("workflow_runs")
        if not isinstance(page_runs, list):
            raise Full("GitHub's listing of this workflow's runs holds no list of runs")
        for item in cast("list[Any]", page_runs):
            run = _mapping(item)
            if _ours(run, repository, pr) and _number(run) < before:
                runs.append(run)
        if len(cast("list[Any]", page_runs)) < PAGE_SIZE:
            break
    return sorted(runs, key=_number, reverse=True)


def _ours(run: Mapping[str, Any], repository: str, pr: PullRequest) -> bool:
    pulls = run.get("pull_requests")
    return (
        run.get("event") == "pull_request"
        and run.get("path") == WORKFLOW_PATH
        and _mapping(run.get("head_repository")).get("full_name") == repository
        and isinstance(pulls, list)
        and any(_mapping(p).get("number") == pr.number for p in cast("list[Any]", pulls))
    )


def _number(run: Mapping[str, Any]) -> int:
    number = run.get("run_number")
    if not isinstance(number, int) or isinstance(number, bool):
        raise Full("a run in GitHub's listing has no run number")
    return number


def _run(run: Mapping[str, Any]) -> Run:
    rid, sha, url = run.get("id"), run.get("head_sha"), run.get("html_url")
    if not (isinstance(rid, int) and isinstance(sha, str) and _SHA.fullmatch(sha)):
        raise Full("a run in GitHub's listing has no id or head commit")
    return Run(rid, _number(run), sha, url if isinstance(url, str) else "")


#: What a run was, as its `checks` job's steps tell it.
PASSED, FAILED, PASSED_OVER = "full, passed", "full, did not pass", "short"


def form(api: Api, repository: str, listed: Mapping[str, Any]) -> tuple[Run, str]:
    """The run, and whether it was a full run that passed, a full run that did not,
    or a short run. Raises Full when it cannot be told."""
    run = _run(listed)
    if listed.get("status") != "completed":
        raise Full(
            f"{run.named()}, earlier than this one, has not finished, so the most recent "
            f"full run cannot be told"
        )
    jobs = _mapping(api(f"repos/{repository}/actions/runs/{run.id}/jobs?per_page=100")).get("jobs")
    named = [_mapping(job) for job in (cast("list[Any]", jobs) if isinstance(jobs, list) else [])]
    named = [job for job in named if job.get("name") == JOB]
    if len(named) != 1:
        raise Full(f"{run.named()} has no single `{JOB}` job, so it cannot be told")
    job = named[0]
    if job.get("head_sha") != run.head or job.get("status") != "completed":
        raise Full(f"{run.named()}'s `{JOB}` job is not that run's finished job")
    steps = job.get("steps")
    by_name = [
        _mapping(step) for step in (cast("list[Any]", steps) if isinstance(steps, list) else [])
    ]
    full = _ran(by_name, FULL_STEP)
    short = _ran(by_name, SHORT_STEP)
    if full is not None and short is None:
        passed = (
            listed.get("conclusion") == "success"
            and job.get("conclusion") == "success"
            and full == "success"
        )
        return run, PASSED if passed else FAILED
    if short is not None and full is None:
        return run, PASSED_OVER
    ran = "both" if full is not None else "neither"
    raise Full(f"{run.named()} ran {ran} of the full run and the short check, so it cannot be told")


def _ran(steps: Iterable[Mapping[str, Any]], name: str) -> str | None:
    """The conclusion of the step `name` where it ran, else `None`. A name given to
    more than one step cannot be told."""
    found = [step for step in steps if step.get("name") == name]
    if len(found) > 1:
        raise Full(f"a run has more than one step named {name!r}")
    if not found:
        return None
    conclusion = found[0].get("conclusion")
    if conclusion == "skipped":
        return None
    return conclusion if isinstance(conclusion, str) else "unfinished"


def basis(api: Api, repository: str, pr: PullRequest, before: int) -> Run:
    """The head of the most recent full run on the pull request, which passed. Raises
    Full when there is none, or the most recent did not pass."""
    runs = earlier_runs(api, repository, pr, before)
    for listed in runs:
        run, kind = form(api, repository, listed)
        if kind == PASSED_OVER:
            continue
        if kind == FAILED:
            raise Full(
                f"the most recent full run on this pull request, {run.named()}, did not pass"
            )
        return run
    raise Full(f"no full run on this pull request was found among the {len(runs)} runs read")


# --- only answers since -------------------------------------------------------------


def answers_only(since: Since, found: Run, pr: PullRequest) -> None:
    """Return where every change from the basis to the head lies inside the answers,
    as `pkit friction since` answers it. Raises Full otherwise, or when its answer
    cannot be read."""
    document = _mapping(since(found.head, pr.head, f"origin/{pr.base}"))
    covered, reason, outside = (document.get(k) for k in ("all_inside", "reason", "outside"))
    if not (
        document.get("schema_version") == SINCE_SCHEMA_VERSION
        and document.get("report") == "since"
        and document.get("since") == found.head
        and document.get("head") == pr.head
        and isinstance(covered, bool)
        and (reason is None or isinstance(reason, str))
        and isinstance(outside, list)
    ):
        raise Full(
            f"`pkit friction since` gave no answer of version {SINCE_SCHEMA_VERSION} for "
            f"{found.head[:7]} to {pr.head[:7]}"
        )
    changes = [_mapping(o) for o in cast("list[Any]", outside)]
    if covered != (reason is None and not changes):
        raise Full("`pkit friction since` gave an answer that disagrees with the changes it names")
    if covered:
        return
    if reason is not None:
        raise Full(f"not only answers changed since {found.named()}: {_code(reason)}")
    shown = [
        f"{_code(str(c.get('path') or 'the merge'))} "
        f"({str(c.get('commit'))[:7]}: {_code(str(c.get('why')))})"
        for c in changes[:SHOWN]
    ]
    more = f", and {len(changes) - SHOWN} more" if len(changes) > SHOWN else ""
    raise Full(f"changes since {found.named()} lie outside the answers: {', '.join(shown)}{more}")


# --- the decision -------------------------------------------------------------------


def decide(env: Mapping[str, str], api: Api, since: Since) -> Decision:
    """Whether this run is the short check, and why."""
    try:
        repository = env["GITHUB_REPOSITORY"]
        before = int(env["GITHUB_RUN_NUMBER"])
        event_name = env["GITHUB_EVENT_NAME"]
        event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        pr = pull_request(event_name, _mapping(event), repository)
        first_attempt(env)
        one_pull_request(api, repository, pr)
        base_unchanged(api, repository, pr)
        found = basis(api, repository, pr, before)
        answers_only(since, found, pr)
    except Full as full:
        return Decision(FULL, str(full))
    return Decision(
        SHORT,
        f"the most recent full run on this pull request, {found.named()}, passed, and every "
        f"change since lies inside `revalidated` blocks and `revisited` lists, a merge of the "
        f"base counting only for what differs from git's merge of it",
        found,
    )


def gh_api(path: str) -> Any:
    """`gh api <path>`, read as JSON. Raises Full when it cannot be."""
    try:
        proc = subprocess.run(
            ["gh", "api", "-H", "Accept: application/vnd.github+json", path],
            capture_output=True,
            text=True,
            check=False,
            timeout=API_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Full(f"GitHub could not be read: {_code(str(exc))}") from exc
    if proc.returncode != 0:
        said = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise Full(
            f"GitHub could not be read: `gh api` exited {proc.returncode}"
            + (f": {_code(said[-1])}" if said else "")
        )
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        raise Full("GitHub could not be read: its answer is not JSON") from exc


def friction_since(since: str, head: str, base: str) -> Any:
    """`pkit friction since <since> --head <head> --base <base> --json`, read as JSON,
    with no token in its environment. Raises Full when it cannot answer."""
    env = {k: v for k, v in os.environ.items() if k not in _TOKENS}
    env["PKIT_NO_ROUTE"] = "1"
    command = ["pkit", "friction", "since", since, "--head", head, "--base", base, "--json"]
    try:
        proc = subprocess.run(
            command, env=env, capture_output=True, text=True, check=False, timeout=SINCE_TIMEOUT
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Full(f"`pkit friction since` could not be run: {_code(str(exc))}") from exc
    if proc.returncode != 0:
        said = (proc.stderr or "").strip().splitlines()
        raise Full(
            f"`pkit friction since` could not answer: it exited {proc.returncode}"
            + (f": {_code(said[-1])}" if said else "")
        )
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        raise Full("`pkit friction since` answered no JSON") from exc


# --- the report ---------------------------------------------------------------------


def summary(decision: Decision) -> str:
    """The job summary's section: which form ran, and why."""
    if decision.mode == SHORT:
        title = "The short check: the aggregator without its test suite"
    else:
        title = "The full run: the whole aggregator, the test suite included"
    lines = [f"### `{JOB}`: {title}", "", f"{_shown(decision.why)}."]
    if decision.basis is not None and decision.basis.url:
        lines += ["", f"The full run it rests on: {_shown(decision.basis.url)}"]
    lines += ["", "When the short check runs: ADR-067."]
    return "\n".join(lines) + "\n"


def _code(text: str) -> str:
    """Text the author or a tool chose, set in a code span, so the summary renders none
    of it as Markdown or HTML."""
    return "`" + text.replace("`", "'") + "`"


def _shown(text: str) -> str:
    """Text that may quote a name the author chose, its control characters escaped."""
    return _CONTROL.sub(lambda m: f"\\x{ord(m.group()):02x}", text)


def main(
    env: Mapping[str, str] | None = None, api: Api = gh_api, since: Since = friction_since
) -> int:
    env = os.environ if env is None else env
    try:
        decision = decide(env, api, since)
    except Exception as exc:  # any fault of its own is a doubt too, so the run is full
        fault = _code(f"{type(exc).__name__}: {exc}")
        decision = Decision(FULL, f"the decision could not be made ({fault})")
    report = summary(decision)
    print(report, end="")
    if env.get("GITHUB_STEP_SUMMARY"):
        with open(env["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(report)
    if env.get("GITHUB_OUTPUT"):
        with open(env["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write(f"mode={decision.mode}\n")
    return 0


def _mapping(value: object) -> Mapping[str, Any]:
    return cast("Mapping[str, Any]", value) if isinstance(value, Mapping) else {}


if __name__ == "__main__":
    sys.exit(main())
