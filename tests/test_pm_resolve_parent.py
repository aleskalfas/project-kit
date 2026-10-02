"""An issue's parent, resolved by the containment seam (#1281).

`containment.resolve_parent` is the upward counterpart of `resolve_children`:
from one read of the issue's record — or a record the caller already holds — it
returns the parent the issue has, with how its native link and its first line
stand: agreed, native only, first line only, disagreeing, none, or unread. The
first line is classified by `body_parent_ref.read_first_line`, which names the
same issue `body_parent_ref.named_issue` does for the textual side of a child
set, conforming or not.

These pin the resolver's matrix, its wording of each fact and remedy, what a
writer may act on, and its cost; the consumers' behaviour on each row is pinned
in `test_pm_parent_resolution_parity.py`.
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

from _lib import body_parent_ref, containment  # noqa: E402

ISSUE_TYPES = YAML(typ="safe").load(
    (CAPABILITY / "schemas" / "issue-types.yaml").read_text(encoding="utf-8")
)
Kind = containment.ParentKind
Form = body_parent_ref.LineForm


def _record(body: str, native: containment.NativeParent | None) -> containment.IssueRecord:
    return containment.IssueRecord(issue={"body": body}, parent=native)


def _resolve(
    body: str,
    native: int | str | None,
    structural_type: str | None = "task",
) -> containment.ParentResolution:
    if isinstance(native, str):
        repository, number = native.split("#")
        parent = containment.NativeParent(int(number), repository)
    else:
        parent = containment.NativeParent(native) if native is not None else None
    return containment.resolve_parent(
        {},
        issue_number=12,
        structural_type=structural_type,
        issue_types=ISSUE_TYPES,
        record=_record(body, parent),
    )


# --- the matrix ------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "native", "kind", "form", "parent", "walks"),
    [
        ("Feature: #5\n", 5, Kind.AGREED, Form.CONFORMING, 5, True),
        ("Epic: #5\n", 5, Kind.AGREED, Form.NON_CONFORMING, 5, True),
        ("Feature: #5\n", None, Kind.TEXTUAL_ONLY, Form.CONFORMING, 5, True),
        ("Feature: #5 — auth\n", None, Kind.TEXTUAL_ONLY, Form.NON_CONFORMING, 5, False),
        ("## What\n", 7, Kind.NATIVE_ONLY, Form.NONE, 7, False),
        ("Milestone: [#3](../milestone/3)\n", 7, Kind.NATIVE_ONLY, Form.MILESTONE, 7, False),
        ("Feature: #5\n", 7, Kind.DISAGREE, Form.CONFORMING, 7, False),
        ("Feature: #5\n", "other/repo#5", Kind.DISAGREE, Form.CONFORMING, 5, False),
        ("## What\n", None, Kind.NONE, Form.NONE, None, False),
        ("Milestone: #3\n", None, Kind.NONE, Form.MILESTONE, None, False),
        ("Integration: integration/big\nFeature: #5\n", 5, Kind.AGREED, Form.CONFORMING, 5, True),
    ],
)
def test_each_record_pair_resolves_to_one_kind_and_one_parent(
    body: str, native, kind, form, parent: int | None, walks: bool
) -> None:
    resolution = _resolve(body, native)
    assert resolution.kind is kind
    assert resolution.line.form is form
    assert (resolution.parent.number if resolution.parent else None) == parent
    assert resolution.walks is walks


def test_the_native_parent_is_the_parent_wherever_one_was_read() -> None:
    resolution = _resolve("Feature: #5\n", 7)
    assert resolution.parent == containment.NativeParent(7)
    assert resolution.named == 5
    # Both are parents the issue is a child of: the reading consumers count both.
    assert resolution.local_parents == (7, 5)


def test_a_native_parent_in_another_repository_is_no_local_parent() -> None:
    resolution = _resolve("Feature: #5\n", "other/repo#7")
    assert resolution.parent == containment.NativeParent(7, "other/repo")
    assert resolution.local_parents == (5,)


def test_an_unreadable_record_reads_the_line_from_the_callers_body() -> None:
    resolution = containment.resolve_parent(
        {},
        issue_number=12,
        structural_type="task",
        issue_types=ISSUE_TYPES,
        record=containment.UnreadIssue("gh exited 1"),
        body="Feature: #5\n",
    )
    assert resolution.kind is Kind.UNREAD
    assert resolution.native is None
    assert resolution.parent == containment.NativeParent(5)
    assert resolution.walks is False
    assert resolution.fact == (
        "#12's record could not be read to hold its native parent to #5, the parent its "
        "first line names (gh exited 1)"
    )


# --- the seam's words ------------------------------------------------------


def test_a_disagreement_is_worded_once_with_its_remedy() -> None:
    resolution = _resolve("Feature: #5\n", 7)
    assert resolution.fact == "#12's first line names #5, its native parent is #7"
    assert resolution.remedy() == (
        "→ the native parent wins (DEC-005): `set-field 12 --parent 7` rewrites #12's first "
        "line to name it."
    )


def test_a_native_parent_with_no_line_is_worded_as_such() -> None:
    resolution = _resolve("## What\n", 7)
    assert resolution.fact == "#12's first line names no parent issue, its native parent is #7"


def test_a_native_parent_abroad_cannot_be_named_on_a_first_line() -> None:
    resolution = _resolve("Feature: #5\n", "other/repo#7")
    assert resolution.remedy(abroad="the forward cascade does not walk into") == (
        "→ other/repo#7 is in another repository, which no first-line form can name and the "
        "forward cascade does not walk into; if #5 is its parent, `set-field 12 --parent 5` "
        "moves the native link under it."
    )
    assert resolution.remedy() == (
        "→ other/repo#7 is in another repository, which no first-line form can name; if #5 "
        "is its parent, `set-field 12 --parent 5` moves the native link under it."
    )


@pytest.mark.parametrize(("body", "native"), [("Feature: #5\n", 5), ("Feature: #5\n", None)])
def test_records_that_agree_have_nothing_to_settle(body: str, native: int | None) -> None:
    resolution = _resolve(body, native)
    assert resolution.fact is None
    assert resolution.remedy() is None
    assert resolution.form_note is None


def test_a_line_in_a_form_the_type_does_not_allow_is_noted_whatever_the_native_says() -> None:
    forms = ISSUE_TYPES["types"]["feature"]["parent_ref_form"]
    resolution = _resolve("Epic: #5\n", 5, structural_type="feature")
    assert resolution.form_note == (
@pytest.mark.parametrize(
    ("body", "native"),
    [("Milestone: [#3](../milestone/3)\n", 7), ("Feature: #5\n", 7), ("## What\n", 7)],
)
def test_an_epic_is_told_its_container_is_a_milestone_not_a_rewrite_that_names_nothing(
    body: str, native: int
) -> None:
    """An EPIC's first line names a milestone, never an issue: `set-field --parent`
    on it writes `Milestone: #<N>`, so the usual remedy — rewrite the first line
    to name the native parent — would name nothing. The seam says what applies
    instead (#1281)."""
    resolution = _resolve(body, native, structural_type="epic")
    assert resolution.line.issue_form is False
    assert resolution.remedy() == (
        "→ #12's container is a milestone: no first-line form its type may have names an "
        "issue, so no rewrite of its first line names #7."
    )
    assert "set-field" not in (resolution.remedy() or "")


def test_an_epic_under_a_native_parent_abroad_says_where_it_is() -> None:
    resolution = _resolve("Milestone: [#3](../milestone/3)\n", "other/repo#7", "epic")
    assert resolution.remedy(abroad="the forward cascade does not walk into") == (
        "→ #12's container is a milestone: no first-line form its type may have names an "
        "issue, so no rewrite of its first line names other/repo#7; other/repo#7 is in "
        "another repository, which the forward cascade does not walk into."
    )


def test_an_issue_of_unknown_type_keeps_the_rewrite_remedy() -> None:
    resolution = _resolve("## What\n", 7, structural_type=None)
    assert resolution.line.issue_form is True
    assert resolution.remedy() is not None
    assert "`set-field 12 --parent 7`" in (resolution.remedy() or "")


        f"#12's first line `Epic: #5` is not a parent-ref a feature may have: {forms}"
    )


def test_an_untyped_issues_line_outside_the_label_form_is_noted() -> None:
    """`Epic:#5` names #5 for an issue whose type cannot be told, and is said."""
    resolution = _resolve("Epic:#5\n", None, structural_type=None)
    assert resolution.named == 5
    assert resolution.line.form is Form.NON_CONFORMING
    assert resolution.form_note == (
        "#12's first line `Epic:#5` is not in the parent-ref form `<Label>: #<N>`"
    )


# --- one reading of the issue a line names --------------------------------

_LINES = [
    "Feature: #5",
    "EPIC: #5",
    "Epic: #5",
    "EPIC:#5",
    "Feature: #5 — auth",
    "Related: #5",
    "Blocked by: #5",
    "Milestone: [#5](../milestone/5)",
    "Milestone: #5",
    "Milestone: [#5](../milestone/6)",
    "Feature: 5",
    "## What",
    "",
]


@pytest.mark.parametrize("structural_type", ["epic", "feature", "umbrella", "task", None])
@pytest.mark.parametrize("line", _LINES)
def test_the_typed_and_the_untyped_reading_name_the_same_issue(
    line: str, structural_type: str | None
) -> None:
    body = f"{line}\n\n## What\nx\n"
    read = body_parent_ref.read_first_line(body, structural_type, ISSUE_TYPES)
    assert read.issue == body_parent_ref.named_issue(body)
    if read.form is Form.CONFORMING:
        assert body_parent_ref.parent_issue(body, structural_type, ISSUE_TYPES) == read.issue


def test_a_milestone_number_is_never_read_as_an_issue() -> None:
    for line in ("Milestone: #3", "Milestone: [#3](../milestone/3)"):
        assert body_parent_ref.named_issue(f"{line}\n") is None
        assert not containment._body_names_parent(f"{line}\n", 3)


# --- cost: one read when the record is omitted, none when supplied --------


def _record_reads(monkeypatch: pytest.MonkeyPatch, payload: dict) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_gh(args, config):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(containment, "_gh_call", fake_gh)
    return calls


def test_an_omitted_record_is_read_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_reads(
        monkeypatch,
        {
            "number": 12,
            "body": "Feature: #5\n",
            "parent_issue_url": "https://api.github.com/repos/o/r/issues/7",
            "repository_url": "https://api.github.com/repos/o/r",
        },
    )
    resolution = containment.resolve_parent(
        {}, issue_number=12, structural_type="task", issue_types=ISSUE_TYPES
    )
    assert calls == [["gh", "api", "repos/{owner}/{repo}/issues/12"]]
    assert resolution.kind is Kind.DISAGREE


def test_a_supplied_record_costs_no_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_reads(monkeypatch, {})
    _resolve("Feature: #5\n", 5)
    assert calls == []
