"""The containment graph, held where a parent is written or read (#1313).

`_lib/containment_graph` answers whether an issue's type may sit under its
parent's ([project-management:DEC-005-linking-and-containment]): from one read
of the parent's title, told apart into allowed, refused, untyped (outside the
graph) and unread (nothing to check). These pin the reading and the verdicts
against the shipped schema; the verbs' refusals are pinned in their own tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import containment_graph as graph  # noqa: E402

ISSUE_TYPES = YAML(typ="safe").load(
    (CAPABILITY / "schemas" / "issue-types.yaml").read_text(encoding="utf-8")
)
CLASSIFICATION = YAML(typ="safe").load(
    (CAPABILITY / "schemas" / "classification.yaml").read_text(encoding="utf-8")
)
TYPES: dict[str, dict] = ISSUE_TYPES["types"]


def _prefix(structural_type: str) -> str:
    entry = TYPES[structural_type]
    prefix = entry["title_prefix"]
    return prefix.upper() if entry.get("title_case") == "upper" else prefix


def _answering(monkeypatch, proc=None, *, raises: BaseException | None = None) -> list:
    """Make the module's one gh call answer `proc` (or raise); return the argv seen."""
    seen: list = []

    def fake(args, config, **kwargs):
        seen.append((list(args), kwargs))
        if raises is not None:
            raise raises
        return proc

    monkeypatch.setattr(graph, "gh_run", fake)
    return seen


def _ok(title: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], 0, stdout=json.dumps({"title": title}), stderr="")


# --- reading a parent's type -------------------------------------------------


def test_read_parent_reads_the_title_once_bounded_and_types_it(monkeypatch) -> None:
    seen = _answering(monkeypatch, _ok("[Umbrella] a bucket"))
    read = graph.read_parent(12, {}, ISSUE_TYPES)

    assert read == graph.ParentRead(12, "umbrella")
    assert [args for args, _ in seen] == [["gh", "issue", "view", "12", "--json", "title"]]
    assert seen[0][1]["timeout"] == graph.READ_TIMEOUT_SECONDS


def test_read_parent_reads_a_kind_prefixed_task_as_a_task(monkeypatch) -> None:
    _answering(monkeypatch, _ok("[Bug] a defect"))
    assert graph.read_parent(
        12, {}, ISSUE_TYPES, classification=CLASSIFICATION
    ).structural_type == ("task")


def test_read_parent_of_an_untyped_issue_is_read_with_no_type(monkeypatch) -> None:
    _answering(monkeypatch, _ok("no prefix at all"))
    assert graph.read_parent(12, {}, ISSUE_TYPES) == graph.ParentRead(12)


@pytest.mark.parametrize(
    ("proc", "raises", "why"),
    [
        (
            subprocess.CompletedProcess([], 1, "", "gh: Not Found\nmore"),
            None,
            "gh exited 1: gh: Not Found",
        ),
        (subprocess.CompletedProcess([], 0, "not json", ""), None, "gh's answer was not JSON"),
        (subprocess.CompletedProcess([], 0, "[]", ""), None, "gh's answer carried no title"),
        (None, subprocess.TimeoutExpired(["gh"], 30), "gh did not answer within 30s"),
        (None, FileNotFoundError("gh"), "`gh` is not on PATH"),
    ],
    ids=["non-zero", "non-json", "no-title", "timeout", "no-gh"],
)
def test_read_parent_that_fails_is_unread_with_why(monkeypatch, proc, raises, why) -> None:
    _answering(monkeypatch, proc, raises=raises)
    assert graph.read_parent(12, {}, ISSUE_TYPES) == graph.ParentRead(12, unread=why)


# --- the verdicts --------------------------------------------------------------

_ISSUE_CHILDREN = sorted(c for c in TYPES if graph.takes_an_issue_parent(ISSUE_TYPES, c))
_PAIRS = [(c, p) for c in _ISSUE_CHILDREN for p in sorted(TYPES)]


def test_an_epic_takes_no_issue_parent_and_every_other_type_does() -> None:
    assert not graph.takes_an_issue_parent(ISSUE_TYPES, "epic")
    assert sorted(set(TYPES) - {"epic"}) == _ISSUE_CHILDREN


@pytest.mark.parametrize(("child", "parent"), _PAIRS)
def test_a_parent_is_allowed_exactly_where_the_schema_lists_its_type(child, parent) -> None:
    check = graph.check_parent(ISSUE_TYPES, child, graph.ParentRead(9, parent))
    allowed = parent in TYPES[child]["parent_issue_types"]

    assert check.verdict is (graph.Verdict.ALLOWED if allowed else graph.Verdict.REFUSED)
    assert check.refuses is not allowed
    if not allowed:
        assert check.message is not None
        assert " may not sit under #9, which is " in check.message
        assert f"`{TYPES[child]['parent_ref_form']}`" in check.message


def test_the_refusal_names_both_types_the_forms_and_the_way_out() -> None:
    check = graph.check_parent(ISSUE_TYPES, "task", graph.ParentRead(9, "task"))
    assert check.message == (
        "a task may not sit under #9, which is a task: a task's parent is one of "
        f"`{TYPES['task']['parent_ref_form']}` — the containment graph in issue-types.yaml "
        "(DEC-005). Choose a parent of one of those types, or change the issue's type"
    )


def test_an_untyped_parent_is_not_refused_and_says_nothing_was_checked() -> None:
    check = graph.check_parent(ISSUE_TYPES, "feature", graph.ParentRead(9))
    assert check.verdict is graph.Verdict.UNTYPED and not check.refuses
    assert check.message == (
        "#9's type cannot be told from its title, so whether a feature may sit under it was "
        "not checked (an untyped issue is outside the containment graph)"
    )


def test_an_unread_parent_refuses_and_says_it_could_not_be_checked() -> None:
    check = graph.check_parent(ISSUE_TYPES, "umbrella", graph.ParentRead(9, unread="why"))
    assert check.verdict is graph.Verdict.UNREAD and check.refuses
    assert check.message == (
        "#9 could not be read (why), so whether an umbrella may sit under it cannot be checked"
    )


# --- an existing issue's first line ----------------------------------------------


class _Reads:
    """A `read` that answers from a table and records every number asked."""

    def __init__(self, answers: dict[int, graph.ParentRead]) -> None:
        self.answers = answers
        self.asked: list[int] = []

    def __call__(self, number: int) -> graph.ParentRead:
        self.asked.append(number)
        return self.answers[number]


@pytest.mark.parametrize(
    "body",
    ["", "## What\nx\n", "Milestone: [#5](../milestone/5)\n", "Milestone: #5\n", "Feature: #42\n"],
    ids=["empty", "no-parent", "milestone", "old-milestone", "names-itself"],
)
def test_a_first_line_naming_no_parent_issue_is_not_read(body: str) -> None:
    reads = _Reads({})
    assert graph.first_line_findings(body, "task", ISSUE_TYPES, issue_number=42, read=reads) == []
    assert reads.asked == []


def test_a_first_line_under_a_parent_the_type_may_not_sit_under_is_a_hard_reject() -> None:
    reads = _Reads({7: graph.ParentRead(7, "task")})
    findings = graph.first_line_findings(
        "Feature: #7\n\n## What\n", "task", ISSUE_TYPES, issue_number=42, read=reads
    )

    assert reads.asked == [7]
    assert len(findings) == 1
    severity, label, detail = findings[0]
    assert (severity, label) == ("hard-reject", "body.parent-ref.containment")
    assert detail.startswith(
        "the first line names #7 as the parent, and a task may not sit under #7, which is a task"
    )


def test_a_non_conforming_first_line_names_its_parent_and_is_held_too() -> None:
    """`Feature: #7 — auth` names #7 for every reader, so it is held to the graph."""
    reads = _Reads({7: graph.ParentRead(7, "feature")})
    findings = graph.first_line_findings(
        "Feature: #7 — auth\n", "feature", ISSUE_TYPES, issue_number=42, read=reads
    )
    assert [f[1] for f in findings] == ["body.parent-ref.containment"]


def test_an_epic_whose_first_line_names_an_issue_is_reported() -> None:
    """An EPIC sits under a milestone; a first line naming an issue puts it under one."""
    reads = _Reads({7: graph.ParentRead(7, "feature")})
    findings = graph.first_line_findings(
        "Feature: #7\n", "epic", ISSUE_TYPES, issue_number=42, read=reads
    )
    assert [f[:2] for f in findings] == [("hard-reject", "body.parent-ref.containment")]


def test_a_first_line_parent_that_cannot_be_read_is_reported_unchecked_not_violated() -> None:
    reads = _Reads({7: graph.ParentRead(7, unread="gh exited 1")})
    findings = graph.first_line_findings(
        "Umbrella: #7\n", "task", ISSUE_TYPES, issue_number=42, read=reads
    )
    assert findings == [
        (
            "warning",
            "body.parent-ref.containment-unchecked",
            "the first line names #7 as the parent, but #7 could not be read (gh exited 1), "
            "so whether a task may sit under it cannot be checked.",
        )
    ]


@pytest.mark.parametrize("parent", [None, "umbrella"], ids=["untyped", "allowed"])
def test_an_allowed_or_untyped_first_line_parent_reports_nothing(parent) -> None:
    reads = _Reads({7: graph.ParentRead(7, parent)})
    assert (
        graph.first_line_findings(
            "Umbrella: #7\n", "task", ISSUE_TYPES, issue_number=42, read=reads
        )
        == []
    )


def test_typed_parent_types_a_title_in_hand(monkeypatch) -> None:
    seen = _answering(monkeypatch, None)
    assert graph.typed_parent(3, f"[{_prefix('epic')}] x", ISSUE_TYPES) == graph.ParentRead(
        3, "epic"
    )
    assert seen == [], "a title in hand costs no read"
