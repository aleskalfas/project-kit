"""The containment graph, held where a parent is written or read (#1313).

`_lib/containment_graph` answers whether an issue's type may sit under its
parent's ([project-management:DEC-005-linking-and-containment]): every issue is
typed one way (`issue_type`, the substrate map a required argument), a parent is
read through the containment seam, and the verdicts are told apart into allowed,
refused, outside the graph (a type that cannot be told), unread and no issue. An
existing issue's parent is the one the seam resolves for it. These pin the
typing, the reading and the verdicts against the shipped schema, and that a
writer and the validator judge every (map, child, parent) alike; the verbs'
refusals are pinned in their own tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import axis_labels, containment  # noqa: E402
from _lib import containment_graph as graph  # noqa: E402

ISSUE_TYPES = YAML(typ="safe").load(
    (CAPABILITY / "schemas" / "issue-types.yaml").read_text(encoding="utf-8")
)
CLASSIFICATION = YAML(typ="safe").load(
    (CAPABILITY / "schemas" / "classification.yaml").read_text(encoding="utf-8")
)
TYPES: dict[str, dict] = ISSUE_TYPES["types"]

# A map whose `type` is carried by the adopter's own title prefixes, and one
# whose `type` is not title-carried at all (a label binding).
STORY_MAP = axis_labels.SubstrateMap(
    axes={"type": {"title-prefix": {"remap": {"feature": "[Story]", "task": "[Task]"}}}}
)
LABEL_MAP = axis_labels.SubstrateMap(axes={"type": {"label": {"remap": {"bug": "kind/bug"}}}})


def _prefix(structural_type: str) -> str:
    entry = TYPES[structural_type]
    prefix = entry["title_prefix"]
    return prefix.upper() if entry.get("title_case") == "upper" else prefix


def _record(
    title: str,
    *,
    body: str = "",
    labels: tuple[str, ...] = (),
    native: containment.NativeParent | None = None,
) -> containment.IssueRecord:
    issue = {
        "title": title,
        "body": body,
        "labels": [{"name": name} for name in labels],
        "state": "OPEN",
        "milestone": None,
    }
    return containment.IssueRecord(issue=issue, parent=native)


def _records(monkeypatch, table: dict) -> list[int]:
    """Answer the seam's record read from ``table`` (number → record or
    ``UnreadIssue``); return the numbers read."""
    asked: list[int] = []

    def fake(config, *, issue_number):
        asked.append(int(issue_number))
        return table[int(issue_number)]

    monkeypatch.setattr(containment, "read_issue_record", fake)
    return asked


# --- one typing, the map required ------------------------------------------------


@pytest.mark.parametrize(
    ("title", "labels", "substrate_map", "expected"),
    [
        ("[Task] a task", (), None, "task"),
        ("[Bug] Login crashes", (), None, "task"),  # a kind-driven Task prefix
        ("Login crashes", ("type:bug",), None, "task"),  # no prefix: the kind label
        ("Login crashes", ("type:feature",), None, None),  # a kind no type follows from
        ("[Story] a story", (), STORY_MAP, "feature"),
        ("[Task] a task", (), STORY_MAP, "task"),
        ("[Feature] the kit's prefix", (), STORY_MAP, None),  # not the map's vocabulary
        ("Login crashes", ("type:bug",), STORY_MAP, None),  # labels not consulted
        ("[Bug] Login crashes", (), LABEL_MAP, None),  # type not title-carried
        ("[Task] a task", ("type:bug",), LABEL_MAP, None),
    ],
)
def test_an_issue_is_typed_in_the_vocabulary_its_tracker_carries(
    title, labels, substrate_map, expected
) -> None:
    assert (
        graph.issue_type(
            title,
            ISSUE_TYPES,
            classification=CLASSIFICATION,
            substrate_map=substrate_map,
            labels=[{"name": name} for name in labels],
        )
        == expected
    )


def test_label_names_or_label_objects_type_alike() -> None:
    kwargs = {"classification": CLASSIFICATION, "substrate_map": None}
    assert graph.issue_type("x", ISSUE_TYPES, labels=["type:bug"], **kwargs) == "task"
    assert graph.issue_type("x", ISSUE_TYPES, labels=[{"name": "type:bug"}], **kwargs) == "task"


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("issue_type", ("[Task] x", ISSUE_TYPES)),
        ("typed_parent", (9, "[Task] x", ISSUE_TYPES)),
        ("read_parent", (9, {}, ISSUE_TYPES)),
    ],
)
def test_a_call_that_does_not_pass_the_map_fails_loudly(name, args) -> None:
    """Without `substrate_map=` a caller would type a mapped tracker with the kit's
    prefixes; it is a TypeError instead, never a silent greenfield read. (Called by
    name: a type checker refuses the call this test makes on purpose.)"""
    function = getattr(graph, name)
    with pytest.raises(TypeError, match="substrate_map"):
        function(*args, classification=CLASSIFICATION)


# --- reading a parent through the seam ---------------------------------------------


def test_read_parent_reads_the_record_once_and_types_it(monkeypatch) -> None:
    asked = _records(monkeypatch, {12: _record("[Umbrella] a bucket")})
    read = graph.read_parent(12, {}, ISSUE_TYPES, classification=CLASSIFICATION, substrate_map=None)

    assert read == graph.ParentRead(12, "umbrella")
    assert asked == [12]


def test_read_parent_types_an_untitled_kind_labelled_parent_in_greenfield_only(
    monkeypatch,
) -> None:
    _records(monkeypatch, {12: _record("Login crashes", labels=("type:bug",))})
    kwargs = {"classification": CLASSIFICATION}

    greenfield = graph.read_parent(12, {}, ISSUE_TYPES, substrate_map=None, **kwargs)
    mapped = graph.read_parent(12, {}, ISSUE_TYPES, substrate_map=STORY_MAP, **kwargs)

    assert greenfield.structural_type == "task"
    assert mapped.structural_type is None


def test_read_parent_that_fails_is_unread_with_why(monkeypatch) -> None:
    said = containment.Said("HTTP 502: Bad Gateway", containment.SPEAKER_GH)
    _records(monkeypatch, {12: containment.UnreadIssue("gh exited 4", said)})
    read = graph.read_parent(12, {}, ISSUE_TYPES, classification=CLASSIFICATION, substrate_map=None)
    assert read == graph.ParentRead(12, unread='gh exited 4. gh said: "HTTP 502: Bad Gateway"')


@pytest.mark.parametrize(
    "why",
    [
        "#12 is a pull request",
        "the record gh returned is #30's, not #12's (an issue transferred elsewhere, "
        "whose read was redirected)",
    ],
    ids=["pull-request", "redirected"],
)
def test_read_parent_of_a_number_naming_no_issue_says_so(monkeypatch, why) -> None:
    _records(monkeypatch, {12: containment.UnreadIssue(why, not_an_issue=True)})
    read = graph.read_parent(12, {}, ISSUE_TYPES, classification=CLASSIFICATION, substrate_map=None)
    assert read == graph.ParentRead(12, unread=why, not_an_issue=True)


def test_typed_parent_types_a_title_in_hand_without_a_read(monkeypatch) -> None:
    asked = _records(monkeypatch, {})
    read = graph.typed_parent(
        3, f"[{_prefix('epic')}] x", ISSUE_TYPES, classification=None, substrate_map=None
    )
    assert read == graph.ParentRead(3, "epic")
    assert asked == [], "a title in hand costs no read"


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
        "#9's type cannot be told, so whether a feature may sit under it was not checked "
        "(an issue whose type cannot be told is outside the containment graph)"
    )


def test_an_untyped_child_is_not_refused_and_says_nothing_was_checked() -> None:
    check = graph.check_parent(ISSUE_TYPES, None, graph.ParentRead(9, "task"))
    assert check.verdict is graph.Verdict.UNTYPED and not check.refuses
    assert check.message == (
        "this issue's type cannot be told, so whether it may sit under #9 was not checked "
        "(an issue whose type cannot be told is outside the containment graph)"
    )


def test_an_unread_parent_refuses_and_says_it_could_not_be_checked() -> None:
    check = graph.check_parent(ISSUE_TYPES, "umbrella", graph.ParentRead(9, unread="why"))
    assert check.verdict is graph.Verdict.UNREAD and check.refuses
    assert check.message == (
        "#9 could not be read (why), so whether an umbrella may sit under it cannot be checked"
    )


def test_a_number_naming_no_issue_refuses_and_says_what_it_names() -> None:
    read = graph.ParentRead(9, unread="#9 is a pull request", not_an_issue=True)
    check = graph.check_parent(ISSUE_TYPES, "task", read)
    assert check.verdict is graph.Verdict.NOT_AN_ISSUE and check.refuses
    assert check.message == (
        "#9 is not an issue in this repository — #9 is a pull request — so a task cannot "
        "sit under it"
    )


# --- the parent a first line asserts --------------------------------------------------


@pytest.mark.parametrize(
    ("child", "body", "asserted"),
    [
        ("task", "Feature: #9\n", 9),
        ("feature", "Feature: #9\n", 9),  # a form a Feature may not have: still asserted
        ("feature", "Feature: #9 — auth\n", 9),
        ("feature", "Epic: #9\n", None),  # not a type's own word, exactly
        ("epic", "Supersedes: #120\n", None),
        ("task", "Related: #45\n", None),
        ("task", "Milestone: [#5](../milestone/5)\n", None),
        ("task", "## What\n", None),
        (None, "Task: #9\n", 9),
    ],
)
def test_a_first_line_asserts_a_parent_only_under_a_types_own_label(child, body, asserted) -> None:
    assert graph.asserted_parent(body, child, ISSUE_TYPES) == asserted


# --- the severity of an existing violation (the maintainer's to confirm) ---------------


def test_an_existing_violation_is_hard_at_filing_and_a_warning_at_a_transition() -> None:
    assert graph.existing_violation_severity("create") == graph.SEVERITY_HARD_REJECT
    assert graph.existing_violation_severity("transition") == graph.SEVERITY_WARNING


# --- an existing issue's parent: the one the seam resolves -------------------------------


class _Reads:
    """A `read` that answers from a table and records every number asked."""

    def __init__(self, answers: dict[int, graph.ParentRead]) -> None:
        self.answers = answers
        self.asked: list[int] = []

    def __call__(self, number: int) -> graph.ParentRead:
        self.asked.append(number)
        return self.answers[number]


def _resolution(
    body: str,
    native: containment.NativeParent | None = None,
    *,
    child: str | None = "task",
    unread: bool = False,
) -> containment.ParentResolution:
    record = (
        containment.UnreadIssue("gh exited 1")
        if unread
        else containment.IssueRecord(issue={"body": body}, parent=native)
    )
    return containment.resolve_parent(
        {},
        issue_number=42,
        structural_type=child,
        issue_types=ISSUE_TYPES,
        record=record,
        body=body,
    )


def _findings(resolution, reads, *, child: str | None = "task", phase: str = "create"):
    return graph.parent_findings(resolution, child, ISSUE_TYPES, phase=phase, read=reads)


def test_a_native_parent_of_a_forbidden_type_is_found_with_no_first_line() -> None:
    reads = _Reads({7: graph.ParentRead(7, "task")})
    findings = _findings(_resolution("## What\n", containment.NativeParent(7)), reads)

    assert reads.asked == [7]
    assert len(findings) == 1
    severity, label, detail = findings[0]
    assert (severity, label) == ("hard-reject", "body.parent-ref.containment")
    assert detail.startswith(
        "#42's native parent is #7, and a task may not sit under #7, which is a task"
    )


def test_a_stale_first_line_under_an_allowed_native_parent_is_no_containment_finding() -> None:
    """The two records disagree; the native parent is judged alone — the stale
    line is the seam's to settle, not a containment violation."""
    reads = _Reads({7: graph.ParentRead(7, "feature"), 8: graph.ParentRead(8, "task")})
    findings = _findings(_resolution("Feature: #8\n", containment.NativeParent(7)), reads)

    assert reads.asked == [7]
    assert findings == []


def test_a_first_line_parent_is_judged_where_the_record_could_not_be_read() -> None:
    reads = _Reads({7: graph.ParentRead(7, "task")})
    findings = _findings(_resolution("Feature: #7\n", unread=True), reads)

    assert [f[:2] for f in findings] == [("hard-reject", "body.parent-ref.containment")]
    assert findings[0][2].startswith(
        "the first line names #7 as the parent (#42's record could not be read, so its "
        "native parent is not known), and a task may not sit under #7"
    )


def test_a_first_line_alone_is_judged_where_no_native_parent_was_read() -> None:
    reads = _Reads({7: graph.ParentRead(7, "task")})
    findings = _findings(_resolution("Feature: #7\n"), reads)
    assert findings[0][2].startswith("the first line names #7 as the parent, and a task")


def test_a_native_parent_in_another_repository_is_reported_not_checked() -> None:
    reads = _Reads({})
    native = containment.NativeParent(7, "other/repo")
    findings = _findings(_resolution("## What\n", native), reads)

    assert reads.asked == []
    assert findings == [
        (
            "warning",
            "body.parent-ref.containment-unchecked",
            "#42's native parent is other/repo#7, in another repository, so whether a task "
            "may sit under it was not checked.",
        )
    ]


@pytest.mark.parametrize(
    "body",
    [
        "",
        "## What\nx\n",
        "Milestone: [#5](../milestone/5)\n",
        "Milestone: #5\n",
        "Feature: #42\n",  # names the issue itself
        "Related: #7\n",  # names #7 for the close gate, asserts no parent
        "Supersedes: #7\n",
    ],
    ids=[
        "empty",
        "no-parent",
        "milestone",
        "old-milestone",
        "names-itself",
        "related",
        "supersedes",
    ],
)
def test_a_first_line_asserting_no_parent_issue_is_not_read(body: str) -> None:
    reads = _Reads({})
    assert _findings(_resolution(body), reads) == []
    assert reads.asked == []


def test_a_non_conforming_line_under_a_types_label_is_held_too() -> None:
    """`Feature: #7 — auth` asserts #7 under a type's own label, so it is held."""
    reads = _Reads({7: graph.ParentRead(7, "feature")})
    findings = _findings(
        _resolution("Feature: #7 — auth\n", child="feature"), reads, child="feature"
    )
    assert [f[1] for f in findings] == ["body.parent-ref.containment"]


def test_an_epic_whose_first_line_names_an_issue_is_reported() -> None:
    """An EPIC sits under a milestone; a first line asserting an issue puts it under one."""
    reads = _Reads({7: graph.ParentRead(7, "feature")})
    findings = _findings(_resolution("Feature: #7\n", child="epic"), reads, child="epic")
    assert [f[:2] for f in findings] == [("hard-reject", "body.parent-ref.containment")]


def test_an_existing_violation_is_a_warning_at_a_transition() -> None:
    reads = _Reads({7: graph.ParentRead(7, "task")})
    findings = _findings(_resolution("Feature: #7\n"), reads, phase="transition")
    assert [f[:2] for f in findings] == [("warning", "body.parent-ref.containment")]


@pytest.mark.parametrize(
    ("read", "said"),
    [
        (graph.ParentRead(7, unread="gh exited 1"), "#7 could not be read (gh exited 1)"),
        (
            graph.ParentRead(7, unread="#7 is a pull request", not_an_issue=True),
            "#7 is not an issue in this repository — #7 is a pull request —",
        ),
    ],
    ids=["unread", "not-an-issue"],
)
def test_a_parent_that_cannot_be_typed_is_reported_unchecked_not_violated(read, said) -> None:
    findings = _findings(_resolution("Umbrella: #7\n"), _Reads({7: read}))
    assert [f[:2] for f in findings] == [("warning", "body.parent-ref.containment-unchecked")]
    assert findings[0][2].startswith(f"the first line names #7 as the parent, but {said}")


@pytest.mark.parametrize("parent", [None, "umbrella"], ids=["untyped", "allowed"])
def test_an_allowed_or_untyped_parent_reports_nothing(parent) -> None:
    reads = _Reads({7: graph.ParentRead(7, parent)})
    assert _findings(_resolution("Umbrella: #7\n"), reads) == []


def test_an_issue_whose_type_cannot_be_told_reads_no_parent_and_reports_nothing() -> None:
    reads = _Reads({})
    resolution = _resolution("## What\n", containment.NativeParent(7), child=None)
    assert _findings(resolution, reads, child=None) == []
    assert reads.asked == []


# --- a writer and the validator judge every (map, child, parent) alike ---------------------
# The writer's path: the child typed by `issue_type`, the parent read and typed
# through the seam, held by `check_parent`. The validator's: the same child, its
# parent resolved by the seam and judged by `parent_findings`. Each row is a
# (map, child title, parent title and labels) and the verdict both must give.

_REFUSED, _ALLOWED, _OUTSIDE = "refused", "allowed", "outside the graph"

_PARITY = [
    (None, "[Task] the child", ("[Task] the parent", ()), _REFUSED),
    (None, "[Task] the child", ("[Feature] the parent", ()), _ALLOWED),
    (None, "[Task] the child", ("[Bug] Login crashes", ()), _REFUSED),
    (None, "[Task] the child", ("Login crashes", ("type:bug",)), _REFUSED),
    (None, "[Feature] the child", ("[Feature] the parent", ()), _REFUSED),
    (None, "[Feature] the child", ("[Umbrella] the parent", ()), _ALLOWED),
    (None, "[Task] the child", ("no type at all", ()), _OUTSIDE),
    (LABEL_MAP, "[Task] the child", ("[Bug] Login crashes", ()), _OUTSIDE),
    (LABEL_MAP, "[Feature] the child", ("[Feature] the parent", ()), _OUTSIDE),
    (LABEL_MAP, "[Task] the child", ("Login crashes", ("type:bug",)), _OUTSIDE),
    (STORY_MAP, "[Story] the child", ("[Story] the parent", ()), _REFUSED),
    (STORY_MAP, "[Task] the child", ("[Story] the parent", ()), _ALLOWED),
    (STORY_MAP, "[Task] the child", ("[Task] the parent", ()), _REFUSED),
    (STORY_MAP, "[Feature] the child", ("[Story] the parent", ()), _OUTSIDE),
    (STORY_MAP, "[Story] the child", ("[EPIC] the parent", ()), _OUTSIDE),
    (STORY_MAP, "[Task] the child", ("Login crashes", ("type:bug",)), _OUTSIDE),
]


def _map_id(substrate_map) -> str:
    if substrate_map is None:
        return "greenfield"
    return "story-prefix" if substrate_map is STORY_MAP else "type-by-label"


@pytest.mark.parametrize(
    ("substrate_map", "child_title", "parent", "verdict"),
    _PARITY,
    ids=[f"{_map_id(m)}:{c}<-{p[0]}" for m, c, p, _ in _PARITY],
)
def test_a_writer_and_the_validator_give_the_same_verdict(
    monkeypatch, substrate_map, child_title, parent, verdict
) -> None:
    parent_title, parent_labels = parent
    _records(monkeypatch, {9: _record(parent_title, labels=parent_labels)})
    kwargs = {"classification": CLASSIFICATION, "substrate_map": substrate_map}
    child_type = graph.issue_type(child_title, ISSUE_TYPES, **kwargs)

    def read(number: int) -> graph.ParentRead:
        return graph.read_parent(number, {}, ISSUE_TYPES, **kwargs)

    check = graph.check_parent(ISSUE_TYPES, child_type, read(9))
    writer = {
        graph.Verdict.REFUSED: _REFUSED,
        graph.Verdict.ALLOWED: _ALLOWED,
        graph.Verdict.UNTYPED: _OUTSIDE,
    }[check.verdict]

    resolution = _resolution("Feature: #9\n", containment.NativeParent(9), child=child_type)
    findings = graph.parent_findings(resolution, child_type, ISSUE_TYPES, phase="create", read=read)
    validator = _REFUSED if [f for f in findings if f[1] == graph.LABEL_VIOLATION] else None

    assert writer == verdict
    assert validator == (_REFUSED if verdict == _REFUSED else None)
    assert [f for f in findings if f[1] != graph.LABEL_VIOLATION] == [], "nothing else said"
