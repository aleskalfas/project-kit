"""Measure how merged pull requests flowed: merges of the base, reviews, answers, CI (#2633).

    uv run python scripts/pr_flow.py --since 2026-11-01 --search "visual-communication in:title"

The window is every pull request of this repository merged on or after `--since`.
`--search` narrows it by more terms of GitHub's issue search, and `--limit` keeps the
pull requests merged last. For each pull request it reports:

- **Each merge of the base into its branch, and whether it conflicted.** A merge of the
  base is a merge commit of the branch, not on the base when the pull request landed,
  whose second parent the base held by then. It is made again with
  `git merge-tree --write-tree`, and is clean, or conflicting in the files it names.
- **The review rounds.** A round is a distinct head that received a verdict, read from
  the `pkit-verdict sha=` marker of the reviewer comments. A verdict naming no head is
  counted, and is in no round. The comments are read by project-management's verdict
  parser (`_lib/agent_verdicts.py`), the one reading of the verdict grammar and its
  finding tags (DEC-028). A blocking finding is a finding tagged `[block]`, counted by
  its reviewer and by the rule it cites. That is the first rule-set rule (`RS-…`) its
  lead paragraph names, or else the first record. A rule's namespace is dropped, since
  its set's code names it; a record's is kept as written.
- **The answers it added, by artefact.** Each entry of each answer file under
  `.pkit/project/friction/answers/` that the change adds is one answer on the artefact
  it names, read by the backbone's answer reader.
- **Each failed CI run and its failing step.** A run is a workflow run on the branch,
  for a `pull_request` event, before the merge. Each attempt counts, so a failure that a
  re-run passed is still one. For each failed job it names the failed steps, and the
  aggregator lines its log names as failed (`-- <line>: FAILED`). It marks a run whose
  log holds the doc check's timeout (`'fill-doc-check' did not answer within`, #2410).

It only reads. GitHub is read through `gh api`, each call a GET. The commits are read
with git in a bare repository of the script's own, `.agent-workspace/pr-flow/git`. That
repository borrows this clone's objects, and fetches the pull requests' heads and their
bases into itself. So nothing is written outside the agent workspace, neither this
clone's refs nor the objects `merge-tree` writes.

The report is Markdown on standard output, the totals first and then each pull request.
Exit 0 with the report; 2, saying why, when GitHub or git cannot be read.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import statistics
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any
from urllib.parse import quote

from project_kit.answer_files import FOLDER as ANSWERS_FOLDER
from project_kit.answer_files import is_answer_file, read_answer_file

_ROOT = Path(__file__).resolve().parents[1]
_VERDICT_PARSER = _ROOT / ".pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py"

#: The bare repository the commits are read in, under the checkout's root.
CACHE = Path(".agent-workspace") / "pr-flow" / "git"

#: The conclusions of a run, a job or a step that failed.
FAILED = frozenset({"failure", "timed_out", "startup_failure"})

#: The doc check's timeout (#2410), as a job's log states it.
DOC_CHECK_TIMEOUT = re.compile(r"'fill-doc-check' did not answer within \d+ s")

# A line of the check aggregator that failed, as `scripts/check.sh` prints it.
_FAILED_LINE = re.compile(r"-- (?P<line>.+): FAILED\s*$")

# A rule of a rule set, its namespace optional; and a record, its namespace optional.
_RULE = re.compile(r"(?<![\w-])(?:[a-z][a-z0-9-]*:)?(?P<rule>RS-[A-Z]+-\d+)")
_RECORD = re.compile(r"(?<![\w-])(?:[a-z][a-z0-9-]*:)?(?:COR|PRJ|ADR|DEC)-\d+")

# The first line of a list item, which ends a finding's lead paragraph.
_ITEM = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])\s")

_PAGE = 100
_SHORT = 7

#: How many pull requests are read at once.
READERS = 8


class Unreadable(Exception):
    """GitHub or git could not be read."""


def _load_verdict_parser() -> ModuleType:
    """project-management's verdict parser, loaded from its file under a name of its own,
    so that no other `_lib` on the import path is taken for it."""
    name = "pr_flow_agent_verdicts"
    loaded = sys.modules.get(name)
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location(name, _VERDICT_PARSER)
    if spec is None or spec.loader is None:
        raise ImportError(f"the verdict parser cannot be loaded from {_VERDICT_PARSER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verdict_parser = _load_verdict_parser()


# ---- what is measured --------------------------------------------------------------


@dataclass(frozen=True)
class BaseMerge:
    """A merge of the base into the branch, made again."""

    commit: str
    #: The files the merge conflicted in; none for a clean merge.
    conflicts: tuple[str, ...] = ()
    #: Why the merge could not be made again, where it could not.
    problem: str | None = None

    @property
    def conflicted(self) -> bool:
        return bool(self.conflicts)


@dataclass(frozen=True)
class Block:
    """A blocking finding: its reviewer and the rule it cites, if it cites one."""

    reviewer: str
    rule: str | None


@dataclass(frozen=True)
class Round:
    """A head that received verdicts: how many, and the blocking findings among them."""

    head: str
    verdicts: int
    blocks: int


@dataclass(frozen=True)
class Review:
    """A pull request's verdicts: its rounds, every verdict, the verdicts that name no
    head, and every blocking finding."""

    rounds: tuple[Round, ...]
    verdicts: int
    unheaded: int
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class FailedJob:
    """A failed job of a run: its failed steps, the aggregator lines its log names as
    failed, and whether the log holds the doc check's timeout."""

    name: str
    steps: tuple[str, ...]
    lines: tuple[str, ...] = ()
    timeout: bool = False
    #: Whether the job's log could be read.
    logged: bool = True


@dataclass(frozen=True)
class FailedRun:
    """A failed attempt of a workflow run."""

    run: int
    attempt: int
    workflow: str
    jobs: tuple[FailedJob, ...]

    @property
    def timeout(self) -> bool:
        return any(job.timeout for job in self.jobs)


@dataclass(frozen=True)
class Answers:
    """The answers a pull request added: how many on each artefact, the files that hold
    them, and the files that could not be read."""

    by_artefact: Counter[str]
    files: int
    unreadable: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        return sum(self.by_artefact.values())


@dataclass(frozen=True)
class Flow:
    """How one merged pull request flowed."""

    number: int
    title: str
    created: datetime
    merged: datetime
    #: Its merges of the base; None where its history could not be read.
    merges: tuple[BaseMerge, ...] | None
    review: Review
    answers: Answers | None
    failed_runs: tuple[FailedRun, ...]
    #: Why its history could not be read, where it could not.
    problem: str | None = None

    @property
    def hours_open(self) -> float:
        return (self.merged - self.created).total_seconds() / 3600


# ---- reading what GitHub and git give ------------------------------------------------


def parse_time(text: str) -> datetime:
    """A timestamp as GitHub writes it, `2026-11-03T16:50:58Z`."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def as_parsed(comment: Mapping[str, Any]) -> dict[str, Any]:
    """A comment of GitHub's REST API in the shape the verdict parser reads, that of
    `gh pr view --json comments`."""
    user = comment.get("user") or {}
    return {
        "body": comment.get("body") or "",
        "createdAt": comment.get("created_at") or "",
        "author": {"login": user.get("login") or ""},
        "url": comment.get("html_url") or "",
    }


def lead(text: str) -> str:
    """A finding's lead paragraph: its text up to a blank line or a sub-item."""
    kept: list[str] = []
    for index, line in enumerate(text.split("\n")):
        if not line.strip() or (index and _ITEM.match(line)):
            break
        kept.append(line)
    return "\n".join(kept)


def rule_cited(text: str) -> str | None:
    """The rule a finding cites: the first rule-set rule its lead paragraph names,
    without its namespace, or else the first record as written; None where it names
    neither."""
    head = lead(text)
    rule = _RULE.search(head)
    if rule is not None:
        return rule["rule"]
    record = _RECORD.search(head)
    return None if record is None else record[0]


def review_of(comments: Sequence[Mapping[str, Any]]) -> Review:
    """The review of a pull request, from its comments as GitHub's REST API lists them.

    Only a verdict carrying the verdict marker counts, as the merge gate counts it. The
    rounds are in the order of each head's first verdict."""
    found = verdict_parser.all_verdicts([as_parsed(c) for c in comments], require_marker=True)
    heads: dict[str, list[int]] = {}
    blocks: list[Block] = []
    unheaded = 0
    for verdict in found:
        tagged = verdict_parser.tagged(verdict.body, verdict_parser.TAG_BLOCK)
        blocks.extend(Block(verdict.reviewer, rule_cited(f.text)) for f in tagged)
        if not verdict.sha:
            unheaded += 1
            continue
        counts = heads.setdefault(verdict.sha, [0, 0])
        counts[0] += 1
        counts[1] += len(tagged)
    rounds = tuple(Round(head, n, b) for head, (n, b) in heads.items())
    return Review(rounds, len(found), unheaded, tuple(blocks))


def answers_of(files: Mapping[str, bytes | None]) -> Answers:
    """The answers in the answer files a pull request added, from each file's path and
    bytes (None where it cannot be read): one for each entry, on the artefact it names."""
    by_artefact: Counter[str] = Counter()
    unreadable: list[str] = []
    for path in sorted(files):
        read = read_answer_file(PurePosixPath(path).name, files[path])
        if read.problem is not None:
            unreadable.append(path)
        by_artefact.update(entry.location for entry in read.entries)
    return Answers(by_artefact, len(files), tuple(unreadable))


def failed_steps(job: Mapping[str, Any]) -> tuple[str, ...]:
    """The steps of a job, as the Actions API lists it, that failed."""
    steps = job.get("steps") or []
    return tuple(str(s.get("name")) for s in steps if s.get("conclusion") in FAILED)


def read_log(text: str) -> tuple[tuple[str, ...], bool]:
    """The aggregator lines a job's log names as failed, in order, and whether it holds
    the doc check's timeout."""
    lines: list[str] = []
    for raw in text.splitlines():
        match = _FAILED_LINE.search(raw)
        if match is not None and match["line"] not in lines:
            lines.append(match["line"])
    return tuple(lines), DOC_CHECK_TIMEOUT.search(text) is not None


def merge_made_again(commit: str, returncode: int, output: str) -> BaseMerge:
    """A merge from what `git merge-tree --write-tree --name-only --no-messages` said of
    it: exit 0 is clean; exit 1 conflicts in the files listed after the tree; any other
    exit could not make it."""
    if returncode == 0:
        return BaseMerge(commit)
    if returncode == 1:
        names = tuple(line for line in output.splitlines()[1:] if line)
        return BaseMerge(commit, names or ("(not named)",))
    return BaseMerge(commit, problem=f"`git merge-tree` exited {returncode}")


# ---- GitHub, read through `gh api` ---------------------------------------------------


class GitHub:
    """GitHub, read through `gh api`, each call a GET."""

    def command(self, path: str) -> list[str]:
        """The `gh` command that reads `path`."""
        return ["gh", "api", "--method", "GET", path]

    def _run(self, path: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                self.command(path), capture_output=True, text=True, check=False, timeout=300
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Unreadable(f"`gh api {path}` could not be run ({exc})") from exc

    def get(self, path: str) -> Any:
        """The JSON GitHub answers for `path`."""
        proc = self._run(path)
        if proc.returncode != 0:
            said = proc.stderr.strip() or proc.stdout.strip()
            raise Unreadable(f"`gh api {path}` exited {proc.returncode}: {said}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise Unreadable(f"`gh api {path}` gave no JSON ({exc})") from exc

    def text(self, path: str) -> str | None:
        """The text GitHub answers for `path`, or None where it gives none, as for a log
        that has expired."""
        proc = self._run(path)
        return proc.stdout if proc.returncode == 0 else None

    def pages(self, path: str, key: str | None = None) -> list[Any]:
        """Every item of a listing, page by page; `key` names the list in an object."""
        items: list[Any] = []
        joiner = "&" if "?" in path else "?"
        page = 1
        while True:
            answer = self.get(f"{path}{joiner}per_page={_PAGE}&page={page}")
            listed = answer if key is None else answer.get(key)
            if not isinstance(listed, list):
                raise Unreadable(f"`gh api {path}` gave no list")
            items.extend(listed)
            if len(listed) < _PAGE:
                return items
            page += 1


# ---- git, in the workspace's own repository ------------------------------------------


def _git(where: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=where,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except OSError as exc:
        raise Unreadable(f"`git` cannot be run ({exc})") from exc


def _git_out(where: Path, *args: str) -> str:
    proc = _git(where, *args)
    if proc.returncode != 0:
        said = proc.stderr.strip() or proc.stdout.strip()
        raise Unreadable(f"`git {' '.join(args)}` failed: {said}")
    return proc.stdout


class History:
    """The pull requests' commits, read in a bare repository in the agent workspace that
    borrows the checkout's objects (`objects/info/alternates`)."""

    def __init__(self, checkout: Path) -> None:
        self.checkout = checkout
        self.repo = checkout / CACHE

    def prepare(self) -> None:
        """Make the repository, where it is missing, and point it at the checkout's objects."""
        if not (self.repo / "HEAD").is_file():
            self.repo.mkdir(parents=True, exist_ok=True)
            _git_out(self.repo, "init", "--quiet", "--bare")
        common = _git_out(
            self.checkout, "rev-parse", "--path-format=absolute", "--git-common-dir"
        ).strip()
        alternates = self.repo / "objects" / "info" / "alternates"
        wanted = f"{Path(common) / 'objects'}\n"
        if not alternates.is_file() or alternates.read_text() != wanted:
            alternates.parent.mkdir(parents=True, exist_ok=True)
            alternates.write_text(wanted)

    def fetch(self, url: str, numbers: Iterable[int], bases: Iterable[str]) -> None:
        """Fetch each pull request's head as `refs/pull/<n>/head`, and each base."""
        specs = [f"+refs/heads/{b}:refs/heads/{b}" for b in sorted(set(bases))]
        specs += [f"+refs/pull/{n}/head:refs/pull/{n}/head" for n in numbers]
        _git_out(self.repo, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", url, *specs)

    def base_merges(self, number: int, landed: str) -> tuple[BaseMerge, ...]:
        """The merges of the base into pull request `number`'s branch, oldest first, each
        made again. `landed` is the commit it landed as, whose first parent is the base
        it landed on."""
        before = f"{landed}^1"
        listed = _git_out(
            self.repo,
            "rev-list",
            "--min-parents=2",
            "--parents",
            "--reverse",
            "--topo-order",
            f"refs/pull/{number}/head",
            "--not",
            before,
        )
        merges: list[BaseMerge] = []
        for line in listed.splitlines():
            commit, first, second, *_ = line.split()
            if _git(self.repo, "merge-base", "--is-ancestor", second, before).returncode != 0:
                continue
            made = _git(
                self.repo,
                "merge-tree",
                "--write-tree",
                "--name-only",
                "--no-messages",
                first,
                second,
            )
            merges.append(merge_made_again(commit, made.returncode, made.stdout))
        return tuple(merges)

    def added_answers(self, number: int, landed: str) -> dict[str, bytes | None]:
        """Each answer file pull request `number` added, against the base it landed on,
        with its bytes at its head (None where they cannot be read)."""
        head = f"refs/pull/{number}/head"
        listed = _git_out(
            self.repo,
            "diff",
            "--name-only",
            "--diff-filter=A",
            "--no-renames",
            f"{landed}^1...{head}",
            "--",
            f"{ANSWERS_FOLDER}/",
        )
        files: dict[str, bytes | None] = {}
        for path in listed.splitlines():
            if not is_answer_file(path):
                continue
            try:
                shown = subprocess.run(
                    ["git", "cat-file", "blob", f"{head}:{path}"],
                    cwd=self.repo,
                    capture_output=True,
                    check=False,
                )
            except OSError as exc:
                raise Unreadable(f"`git` cannot be run ({exc})") from exc
            files[path] = shown.stdout if shown.returncode == 0 else None
        return files


# ---- one pull request ------------------------------------------------------------------


def failed_runs(github: GitHub, repo: str, pull: Mapping[str, Any]) -> tuple[FailedRun, ...]:
    """Each failed attempt of a workflow run on the pull request's branch, for a
    `pull_request` event, from its opening to its merge."""
    branch = quote(pull["head"]["ref"], safe="")
    runs = github.pages(
        f"repos/{repo}/actions/runs?branch={branch}&event=pull_request", "workflow_runs"
    )
    opened, merged = parse_time(pull["created_at"]), parse_time(pull["merged_at"])
    found: list[FailedRun] = []
    for run in sorted(runs, key=lambda r: (r["created_at"], r["id"])):
        if not opened <= parse_time(run["created_at"]) <= merged:
            continue
        last = int(run.get("run_attempt") or 1)
        for attempt in range(1, last + 1):
            if attempt == last:
                conclusion = run.get("conclusion")
            else:
                conclusion = github.get(
                    f"repos/{repo}/actions/runs/{run['id']}/attempts/{attempt}"
                )["conclusion"]
            if conclusion not in FAILED:
                continue
            jobs = github.pages(
                f"repos/{repo}/actions/runs/{run['id']}/attempts/{attempt}/jobs", "jobs"
            )
            found.append(
                FailedRun(
                    run=int(run["id"]),
                    attempt=attempt,
                    workflow=str(run.get("name") or run.get("path") or ""),
                    jobs=tuple(
                        _failed_job(github, repo, job)
                        for job in jobs
                        if job.get("conclusion") in FAILED
                    ),
                )
            )
    return tuple(found)


def _failed_job(github: GitHub, repo: str, job: Mapping[str, Any]) -> FailedJob:
    log = github.text(f"repos/{repo}/actions/jobs/{job['id']}/logs")
    if log is None:
        return FailedJob(str(job.get("name")), failed_steps(job), logged=False)
    lines, timeout = read_log(log)
    return FailedJob(str(job.get("name")), failed_steps(job), lines, timeout)


def flow_of(github: GitHub, history: History, repo: str, pull: Mapping[str, Any]) -> Flow:
    """How the merged pull request `pull` (the REST API's object) flowed."""
    number = int(pull["number"])
    landed = str(pull.get("merge_commit_sha") or "")
    merges: tuple[BaseMerge, ...] | None = None
    answers: Answers | None = None
    problem: str | None = None
    try:
        if not landed:
            raise Unreadable("GitHub names no commit it landed as")
        merges = history.base_merges(number, landed)
        answers = answers_of(history.added_answers(number, landed))
    except Unreadable as exc:
        problem = str(exc)
    comments = github.pages(f"repos/{repo}/issues/{number}/comments")
    return Flow(
        number=number,
        title=str(pull.get("title") or ""),
        created=parse_time(pull["created_at"]),
        merged=parse_time(pull["merged_at"]),
        merges=merges,
        review=review_of(comments),
        answers=answers,
        failed_runs=failed_runs(github, repo, pull),
        problem=problem,
    )


def window(
    github: GitHub, repo: str, since: date, search: str | None, limit: int | None
) -> list[dict[str, Any]]:
    """The pull requests of the window, oldest merge first, each as the REST API gives it."""
    terms = f"repo:{repo} is:pr is:merged merged:>={since.isoformat()}"
    if search:
        terms = f"{terms} {search}"
    items = github.pages(f"search/issues?q={quote(terms, safe='')}", "items")
    with ThreadPoolExecutor(READERS) as pool:
        read = list(
            pool.map(lambda item: github.get(f"repos/{repo}/pulls/{item['number']}"), items)
        )
    pulls = [p for p in read if p.get("merged_at")]
    pulls.sort(key=lambda p: (p["merged_at"], p["number"]))
    return pulls[-limit:] if limit else pulls


# ---- the report ----------------------------------------------------------------------

#: How many of the most answered artefacts the report lists.
TOP_ARTEFACTS = 20


def _short(commit: str) -> str:
    return f"`{commit[:_SHORT]}`"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> list[str]:
    lines = [f"| {' | '.join(headers)} |", f"|{'---|' * len(headers)}"]
    lines += [f"| {' | '.join(str(cell) for cell in row)} |" for row in rows]
    return lines


def _mean_median(values: Sequence[float]) -> str:
    if not values:
        return "—"
    return f"{statistics.fmean(values):.1f} / {statistics.median(values):g}"


def _ranked(counted: Counter[str]) -> list[tuple[str, int]]:
    return sorted(counted.items(), key=lambda item: (-item[1], item[0]))


def _section(title: str, headers: Sequence[str], counted: Counter[str]) -> list[str]:
    if not counted:
        return []
    return ["", f"## {title}", "", *_table(headers, _ranked(counted))]


def document_of(location: str) -> str:
    """The document an answer's artefact lies in: its location without an entry's id."""
    return location.split("#", 1)[0]


def _totals(flows: Sequence[Flow]) -> list[str]:
    known = [f for f in flows if f.merges is not None]
    answered = [f.answers for f in flows if f.answers is not None]
    rounds = [len(f.review.rounds) for f in flows]
    runs = [r for f in flows for r in f.failed_runs]

    def having(test: Callable[[Flow], bool], among: Sequence[Flow] = flows) -> int:
        return sum(1 for f in among if test(f))

    return _table(
        ("Measure", "Total", "Per pull request (mean / median)", "Pull requests with any"),
        [
            (
                "Merges of the base",
                sum(len(f.merges or ()) for f in known),
                _mean_median([len(f.merges or ()) for f in known]),
                having(lambda f: bool(f.merges), known),
            ),
            (
                "… conflicting",
                sum(m.conflicted for f in known for m in f.merges or ()),
                "",
                having(lambda f: any(m.conflicted for m in f.merges or ()), known),
            ),
            ("Review rounds", sum(rounds), _mean_median(rounds), sum(1 for n in rounds if n)),
            ("… pull requests with two or more", "", "", sum(1 for n in rounds if n >= 2)),
            (
                "Verdicts",
                sum(f.review.verdicts for f in flows),
                _mean_median([f.review.verdicts for f in flows]),
                having(lambda f: f.review.verdicts > 0),
            ),
            (
                "Blocking findings",
                sum(len(f.review.blocks) for f in flows),
                _mean_median([len(f.review.blocks) for f in flows]),
                having(lambda f: bool(f.review.blocks)),
            ),
            (
                "Answers added",
                sum(a.total for a in answered),
                _mean_median([a.total for a in answered]),
                sum(1 for a in answered if a.total),
            ),
            ("… in answer files", sum(a.files for a in answered), "", ""),
            (
                "Failed CI runs",
                len(runs),
                _mean_median([len(f.failed_runs) for f in flows]),
                having(lambda f: bool(f.failed_runs)),
            ),
            (
                "… with the doc check's timeout (#2410)",
                sum(r.timeout for r in runs),
                "",
                having(lambda f: any(r.timeout for r in f.failed_runs)),
            ),
            ("Hours open", "", _mean_median([round(f.hours_open, 1) for f in flows]), ""),
        ],
    )


def _answers(flows: Sequence[Flow]) -> list[str]:
    by_artefact: Counter[str] = Counter()
    by_document: Counter[str] = Counter()
    pulls_on: Counter[str] = Counter()
    pulls_in: Counter[str] = Counter()
    for flow in flows:
        if flow.answers is None:
            continue
        by_artefact.update(flow.answers.by_artefact)
        pulls_on.update(flow.answers.by_artefact.keys())
        pulls_in.update({document_of(a) for a in flow.answers.by_artefact})
        for location, count in flow.answers.by_artefact.items():
            by_document[document_of(location)] += count
    if not by_artefact:
        return []
    artefacts_in = Counter(document_of(a) for a in by_artefact)
    top = _ranked(by_artefact)[:TOP_ARTEFACTS]
    return [
        "",
        "## Answers by document",
        "",
        *_table(
            ("Document", "Answers", "Artefacts", "Pull requests"),
            ((f"`{d}`", n, artefacts_in[d], pulls_in[d]) for d, n in _ranked(by_document)),
        ),
        "",
        f"## Answers by artefact ({len(top)} most answered of {len(by_artefact)})",
        "",
        *_table(
            ("Artefact", "Answers", "Pull requests"),
            ((f"`{a}`", n, pulls_on[a]) for a, n in top),
        ),
    ]


def render(flows: Sequence[Flow], *, since: date, search: str | None, read_at: datetime) -> str:
    """The report on `flows`, in Markdown: the totals, what they break down into, and each
    pull request."""
    scope = f"merged since {since.isoformat()}"
    if search:
        scope += f", search `{search}`"
    out = [
        "# Pull request flow",
        "",
        f"{_plural(len(flows), 'pull request')} {scope}; read {read_at:%Y-%m-%d %H:%M} UTC.",
    ]
    if not flows:
        return "\n".join(out) + "\n"
    out += ["", "## Totals", "", *_totals(flows)]
    unheaded = sum(f.review.unheaded for f in flows)
    if unheaded:
        out += ["", f"{_plural(unheaded, 'verdict')} named no head, and are in no round."]
    unread = [f for f in flows if f.problem]
    if unread:
        out += ["", "Their history was not read, so no merge or answer is counted, for:", ""]
        out += [f"- #{f.number}: {f.problem}" for f in unread]
    conflicts = Counter(f"`{name}`" for f in flows for m in f.merges or () for name in m.conflicts)
    blocks = [b for f in flows for b in f.review.blocks]
    runs = [r for f in flows for r in f.failed_runs]
    out += _section("Conflicting files", ("File", "Merges"), conflicts)
    out += _section(
        "Blocking findings by reviewer",
        ("Reviewer", "Findings"),
        Counter(b.reviewer for b in blocks),
    )
    out += _section(
        "Blocking findings by rule",
        ("Rule", "Findings"),
        Counter(b.rule or "(none cited)" for b in blocks),
    )
    out += _section(
        "Failed CI runs by failing step",
        ("Job: step", "Runs"),
        Counter(step for r in runs for step in _steps(r)),
    )
    out += _section(
        "Failed CI runs by aggregator line",
        ("Line", "Runs"),
        Counter(line for r in runs for line in {line for j in r.jobs for line in j.lines}),
    )
    out += _answers(flows)
    out += ["", "## Each pull request"]
    for flow in flows:
        out += ["", *_one(flow)]
    return "\n".join(out) + "\n"


def _steps(run: FailedRun) -> set[str]:
    return {f"{j.name}: {s}" for j in run.jobs for s in (j.steps or ("(no step named)",))}


def _one(flow: Flow) -> list[str]:
    lines = [
        f"### #{flow.number} {flow.title}",
        "",
        f"Merged {flow.merged:%Y-%m-%d %H:%M}, open {flow.hours_open:.1f} hours.",
        "",
    ]
    if flow.merges is None:
        lines.append(f"- Merges of the base: not read ({flow.problem}).")
    else:
        merges = "; ".join(_merge(m) for m in flow.merges) or "none"
        lines.append(f"- Merges of the base: {merges}.")
    review = flow.review
    rounds = "; ".join(
        f"{_short(r.head)} {_plural(r.verdicts, 'verdict')}"
        + (f", {r.blocks} blocking" if r.blocks else "")
        for r in review.rounds
    )
    lines.append(f"- Review rounds: {len(review.rounds)}" + (f": {rounds}." if rounds else "."))
    if review.unheaded:
        lines.append(f"- Verdicts naming no head: {review.unheaded}.")
    if review.blocks:
        counted = Counter(f"{b.reviewer} {b.rule or '(none cited)'}" for b in review.blocks)
        each = ", ".join(k if n == 1 else f"{k} ×{n}" for k, n in _ranked(counted))
        lines.append(f"- Blocking findings: {each}.")
    lines.append(f"- Answers: {_answered(flow)}.")
    if flow.answers is not None and flow.answers.unreadable:
        unread = ", ".join(f"`{p}`" for p in flow.answers.unreadable)
        lines.append(f"- Answer files not read: {unread}.")
    if not flow.failed_runs:
        lines.append("- Failed CI runs: none.")
    else:
        lines.append("- Failed CI runs:")
        lines += [f"  - {_run(r)}" for r in flow.failed_runs]
    return lines


def _answered(flow: Flow) -> str:
    """A pull request's answers, by the document each artefact lies in, naming how many
    artefacts of a document they are on where they are on more than one."""
    answers = flow.answers
    if answers is None:
        return f"not read ({flow.problem})"
    if not answers.total:
        return "none"
    by_document: Counter[str] = Counter()
    artefacts: Counter[str] = Counter()
    for location, count in answers.by_artefact.items():
        by_document[document_of(location)] += count
        artefacts[document_of(location)] += 1
    each = ", ".join(
        f"`{d}` {n}" + (f" on {artefacts[d]} artefacts" if artefacts[d] > 1 else "")
        for d, n in _ranked(by_document)
    )
    return f"{answers.total} in {_plural(answers.files, 'file')}: {each}"


def _merge(merge: BaseMerge) -> str:
    if merge.problem:
        return f"{_short(merge.commit)} not made again ({merge.problem})"
    if merge.conflicted:
        names = ", ".join(f"`{n}`" for n in merge.conflicts)
        return f"{_short(merge.commit)} conflicting in {names}"
    return f"{_short(merge.commit)} clean"


def _run(run: FailedRun) -> str:
    parts: list[str] = []
    for job in run.jobs:
        said = f"{job.name}: {', '.join(job.steps) or '(no step named)'}"
        if job.lines:
            said += f" (failed lines: {', '.join(job.lines)})"
        if not job.logged:
            said += " (log not read)"
        parts.append(said)
    jobs = "; ".join(parts) or "no failed job"
    text = f"run {run.run}, attempt {run.attempt} ({run.workflow}): {jobs}"
    return text + (" — the doc check's timeout (#2410)" if run.timeout else "")


# ---- the command ---------------------------------------------------------------------


def run(since: date, search: str | None, limit: int | None) -> int:
    """Measure the window and print the report."""
    try:
        checkout = Path(_git_out(Path.cwd(), "rev-parse", "--show-toplevel").strip())
        github = GitHub()
        repo = str(github.get("repos/{owner}/{repo}")["full_name"])
        pulls = window(github, repo, since, search, limit)
        history = History(checkout)
        if pulls:
            url = _git_out(checkout, "remote", "get-url", "origin").strip()
            history.prepare()
            history.fetch(url, (int(p["number"]) for p in pulls), (p["base"]["ref"] for p in pulls))
        print(f"Reading {_plural(len(pulls), 'pull request')} of {repo}.", file=sys.stderr)
        with ThreadPoolExecutor(READERS) as pool:
            flows = list(pool.map(lambda pull: flow_of(github, history, repo, pull), pulls))
    except Unreadable as exc:
        print(f"error: {exc}. No report was made.", file=sys.stderr)
        return 2
    print(render(flows, since=since, search=search, read_at=datetime.now(UTC)), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report how the pull requests merged since a date flowed: merges of the base, "
            "review rounds and blocking findings, answers added, failed CI runs. It only reads."
        ),
    )
    parser.add_argument(
        "--since",
        required=True,
        type=date.fromisoformat,
        help="The first day of merges, YYYY-MM-DD.",
    )
    parser.add_argument(
        "--search",
        help='More terms of GitHub\'s issue search, such as "visual-communication in:title".',
    )
    parser.add_argument(
        "--limit", type=int, help="Keep only this many pull requests, those merged last."
    )
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    return run(args.since, args.search, args.limit)


if __name__ == "__main__":
    sys.exit(main())
