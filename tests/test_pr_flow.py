"""`scripts/pr_flow.py` measures how merged pull requests flowed (#2633).

The parsing is tested on recorded fixtures (`tests/fixtures/pr-flow/`): the reviewer
comments of #2597 and #2522, trimmed to the lines the parsing reads; the workflow runs
of #2615's branch, the attempt of one that failed, its jobs and two of their logs; and
two answer files of the repository. The merges of the base are tested in a repository
built here, with a clean merge, a conflicting one, and a merge of another branch.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from scripts import pr_flow

from tests.adopter_repo import GitRepo

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pr-flow"
ANSWERS = "tests/fixtures/pr-flow/answers"
PAGES = "20261103T141550Z-8bd2f51f.yaml"
TERMS = "20261103T032927Z-451d90fd.yaml"
FOLDER = ".pkit/project/friction/answers"
REPO = "acme/repo"
BRANCH = "feat/2605-the-capability-keeps-each-released"
MARKER = "<!-- pkit-verdict sha={sha} base={sha} -->"


def _json(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _comment(body: str, at: str = "2026-11-03T10:00:00Z") -> dict[str, Any]:
    return {"body": body, "created_at": at, "html_url": "", "user": {"login": "someone"}}


# ---- the review ----------------------------------------------------------------------


def test_a_round_is_each_head_that_received_a_verdict() -> None:
    review = pr_flow.review_of(_json("comments-2597.json"))
    assert [(r.head[:7], r.verdicts, r.blocks) for r in review.rounds] == [
        ("cdd97f8", 10, 2),
        ("66c5a61", 3, 0),
    ]
    # The filing comment is no verdict; two runs of the reviewers on one head are one round.
    assert review.verdicts == 13
    assert review.unheaded == 0


def test_a_blocking_finding_is_counted_by_its_reviewer_and_the_rule_it_cites() -> None:
    review = pr_flow.review_of(_json("comments-2597.json"))
    # `living-docs:RS-LDOC-002` is counted as its rule, the namespace dropped.
    assert review.blocks == (
        pr_flow.Block("docs-reviewer", "DEC-055"),
        pr_flow.Block("rule-set-reviewer", "RS-LDOC-002"),
    )


def test_a_tag_in_bold_blocks_and_a_finding_may_cite_no_rule() -> None:
    review = pr_flow.review_of(_json("comments-2522.json"))
    assert [(r.head[:7], r.verdicts, r.blocks) for r in review.rounds] == [
        ("6b736bd", 3, 2),
        ("a1928bd", 2, 0),
        ("28960d3", 3, 0),
    ]
    assert review.blocks == (
        pr_flow.Block("docs-reviewer", None),
        pr_flow.Block("docs-reviewer", None),
    )


def test_only_a_verdict_with_the_marker_counts_and_one_naming_no_head_is_in_no_round() -> None:
    head = "a" * 40
    review = pr_flow.review_of(
        [
            _comment("Reviewer agent (local, code-reviewer): CHANGES_REQUESTED\n\n- [block] x\n"),
            _comment(
                "Reviewer agent (local, code-reviewer): CHANGES_REQUESTED\n\n- [block] y\n\n"
                "<!-- pkit-verdict -->\n"
            ),
            _comment("Reviewer agent (local, pm-reviewer): APPROVED\n\n" + MARKER.format(sha=head)),
        ]
    )
    assert review.verdicts == 2
    assert review.unheaded == 1
    assert review.rounds == (pr_flow.Round(head, 1, 0),)
    assert review.blocks == (pr_flow.Block("code-reviewer", None),)


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("[block] **A fact away from its home** (`living-docs:RS-LDOC-002`).", "RS-LDOC-002"),
        ("[block] The rule is COR-062 point 7, and RS-LDOC-001 too.", "RS-LDOC-001"),
        ("[block] Breaks project-management:DEC-055 point 3.", "project-management:DEC-055"),
        ("[block] A crash.\n- **Where:** DEC-011 says a loop is refused.", None),
        ("[block] A crash.\n\nDEC-011 says a loop is refused.", None),
        ("[block] A wrapped lead\nthat names ADR-067 on its second line.", "ADR-067"),
        ("[block] No rule at all.", None),
    ],
)
def test_the_rule_cited_is_read_from_the_lead_paragraph(text: str, rule: str | None) -> None:
    assert pr_flow.rule_cited(text) == rule


# ---- the answers ---------------------------------------------------------------------


def test_answers_are_counted_by_artefact_from_the_answer_files() -> None:
    files = {
        f"{FOLDER}/{name}": (FIXTURES / "answers" / name).read_bytes() for name in (PAGES, TERMS)
    }
    files[f"{FOLDER}/20261103T000000Z-00000000.yaml"] = b"answers: [unclosed\n"
    answers = pr_flow.answers_of(files)
    assert answers.by_artefact == {
        ".pkit/capabilities/visual-communication/files.md": 1,
        ".pkit/capabilities/visual-communication/checks.md": 1,
        ".pkit/capabilities/visual-communication/components.md": 1,
        ".pkit/capabilities/visual-communication/README.md": 1,
        "tech-docs/analysis/project-management/glossary.md#TERM-fixer": 1,
        "tech-docs/analysis/project-management/domain-model/040-reviews-and-the-merge.md": 1,
    }
    assert answers.total == 6
    assert answers.files == 3
    assert answers.unreadable == (f"{FOLDER}/20261103T000000Z-00000000.yaml",)


# ---- CI ------------------------------------------------------------------------------


def test_a_failed_job_names_its_failed_steps() -> None:
    jobs = {job["name"]: job for job in _json("jobs-41665141214-1.json")["jobs"]}
    assert pr_flow.failed_steps(jobs["the remainder"]) == ("Run the remainder of the aggregator",)
    assert pr_flow.failed_steps(jobs["checks"]) == ("Run the check aggregator",)
    assert pr_flow.failed_steps(jobs["slice 1 of 2"]) == ()


def test_a_log_names_its_failed_lines_and_the_doc_checks_timeout() -> None:
    lines, timeout = pr_flow.read_log((FIXTURES / "log-the-remainder.txt").read_text())
    assert lines == ("validate", "doc check")
    assert timeout
    assert pr_flow.read_log((FIXTURES / "log-checks.txt").read_text()) == ((), False)


# ---- the merges ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("returncode", "output", "merge"),
    [
        (0, "tree\n", pr_flow.BaseMerge("c")),
        (1, "tree\na.md\nb.md\n", pr_flow.BaseMerge("c", ("a.md", "b.md"))),
        (1, "tree\n", pr_flow.BaseMerge("c", ("(not named)",))),
        (128, "", pr_flow.BaseMerge("c", problem="`git merge-tree` exited 128")),
    ],
)
def test_what_merge_tree_says_classes_a_merge(
    returncode: int, output: str, merge: pr_flow.BaseMerge
) -> None:
    assert pr_flow.merge_made_again("c", returncode, output) == merge


@pytest.fixture
def landed(tmp_path: Path) -> dict[str, Any]:
    """`origin`, with pull request 7 landed on `main` as a squash: its branch merged
    another branch, then `main` twice, once clean and once in conflict. A clone of
    `origin` is the checkout."""
    origin = GitRepo.init(tmp_path / "origin")
    origin.commit("start", {"a.md": "one\n", "b.md": "x\n"})
    origin.checkout("side", create=True)
    origin.commit("side", {"c.md": "side\n"})
    origin.checkout("main")
    origin.checkout("feature", create=True)
    pages = (FIXTURES / "answers" / PAGES).read_text()
    origin.commit("feature", {"a.md": "feature\n", f"{FOLDER}/{PAGES}": pages})
    other = origin.merge("side")
    origin.checkout("main")
    terms = (FIXTURES / "answers" / TERMS).read_text()
    origin.commit("main moves on", {"b.md": "y\n", f"{FOLDER}/{TERMS}": terms})
    origin.checkout("feature")
    clean = origin.merge("main")
    origin.checkout("main")
    origin.commit("main edits a.md", {"a.md": "main\n"})
    origin.checkout("feature")
    assert origin.git("merge", "-q", "main", check=False).returncode == 1
    conflicting = origin.commit("merge main", {"a.md": "both\n"})
    origin.checkout("main")
    squash = origin.squash_merge("feature")
    origin.git("update-ref", "refs/pull/7/head", conflicting)
    checkout = tmp_path / "checkout"
    origin.git("clone", "-q", str(origin.root), str(checkout))
    return {
        "origin": origin,
        "checkout": GitRepo(checkout),
        "other": other,
        "clean": clean,
        "conflicting": conflicting,
        "squash": squash,
    }


def _state(repo: GitRepo) -> tuple[str, str]:
    """What a run could change in the checkout: its refs, and its objects."""
    refs = repo.git("for-each-ref").stdout
    objects = repo.git("count-objects", "-v").stdout
    return refs, objects


def test_merges_of_the_base_are_made_again_and_classed(landed: dict[str, Any]) -> None:
    checkout: GitRepo = landed["checkout"]
    before = _state(checkout)
    history = pr_flow.History(checkout.root)
    history.prepare()
    history.fetch(str(landed["origin"].root), [7], ["main"])
    merges = history.base_merges(7, landed["squash"])
    # The merge of `side` is no merge of the base, since `main` never held `side`.
    assert merges == (
        pr_flow.BaseMerge(landed["clean"]),
        pr_flow.BaseMerge(landed["conflicting"], ("a.md",)),
    )
    # The answer file `main` added is not the pull request's.
    added = history.added_answers(7, landed["squash"])
    assert list(added) == [f"{FOLDER}/{PAGES}"]
    assert added[f"{FOLDER}/{PAGES}"] == (FIXTURES / "answers" / PAGES).read_bytes()
    # The fetch and the merges wrote only in the workspace's own repository.
    assert _state(checkout) == before
    assert (checkout.root / pr_flow.CACHE / "refs" / "pull" / "7" / "head").is_file()


# ---- one pull request, end to end ------------------------------------------------------


class Recorded(pr_flow.GitHub):
    """GitHub as recorded: each path's answer, its paging left out."""

    def __init__(self, answers: dict[str, Any], logs: dict[str, str]) -> None:
        self.answers = answers
        self.logs = logs
        self.read: list[str] = []

    def get(self, path: str) -> Any:
        self.read.append(path)
        return self.answers[re.sub(r"[?&]per_page=100&page=1$", "", path)]

    def text(self, path: str) -> str | None:
        self.read.append(path)
        return self.logs.get(path)


def _recorded() -> Recorded:
    runs = f"repos/{REPO}/actions/runs"
    return Recorded(
        {
            f"repos/{REPO}/issues/7/comments": _json("comments-2597.json"),
            f"{runs}?branch={quote(BRANCH, safe='')}&event=pull_request": _json("runs-2615.json"),
            f"{runs}/41665141214/attempts/1": _json("attempt-41665141214-1.json"),
            f"{runs}/41665141214/attempts/1/jobs": _json("jobs-41665141214-1.json"),
        },
        {
            f"repos/{REPO}/actions/jobs/126018656531/logs": (
                FIXTURES / "log-the-remainder.txt"
            ).read_text(),
            f"repos/{REPO}/actions/jobs/126029205311/logs": (
                FIXTURES / "log-checks.txt"
            ).read_text(),
        },
    )


def _pull(squash: str) -> dict[str, Any]:
    return {
        "number": 7,
        "title": "feat(scripts): a pull request",
        "created_at": "2026-11-03T14:22:29Z",
        "merged_at": "2026-11-03T16:50:58Z",
        "merge_commit_sha": squash,
        "head": {"ref": BRANCH},
        "base": {"ref": "main"},
    }


def test_a_pull_request_is_read_end_to_end(landed: dict[str, Any]) -> None:
    history = pr_flow.History(landed["checkout"].root)
    history.prepare()
    history.fetch(str(landed["origin"].root), [7], ["main"])
    github = _recorded()
    flow = pr_flow.flow_of(github, history, REPO, _pull(landed["squash"]))
    assert flow.problem is None
    assert flow.merges is not None and [m.conflicted for m in flow.merges] == [False, True]
    assert len(flow.review.rounds) == 2
    assert flow.answers is not None and flow.answers.total == 4
    # A run whose re-run passed failed in its first attempt, and that attempt counts.
    assert flow.failed_runs == (
        pr_flow.FailedRun(
            run=41665141214,
            attempt=1,
            workflow="checks",
            jobs=(
                pr_flow.FailedJob(
                    "the remainder",
                    ("Run the remainder of the aggregator",),
                    ("validate", "doc check"),
                    timeout=True,
                ),
                pr_flow.FailedJob("checks", ("Run the check aggregator",)),
            ),
        ),
    )
    report = pr_flow.render([flow], since=date(2026, 11, 1), search=None, read_at=datetime.now(UTC))
    assert f"`{landed['conflicting'][:7]}` conflicting in `a.md`" in report
    assert "| Blocking findings | 2 | 2.0 / 2 | 1 |" in report
    assert "| RS-LDOC-002 | 1 |" in report
    assert "the doc check's timeout (#2410)" in report


def test_every_read_of_github_is_a_get() -> None:
    assert pr_flow.GitHub().command("repos/acme/repo/pulls/7") == [
        "gh",
        "api",
        "--method",
        "GET",
        "repos/acme/repo/pulls/7",
    ]
