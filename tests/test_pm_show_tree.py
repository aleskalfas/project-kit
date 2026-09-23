"""Tests for project-management's show-tree script's pure logic.

Covers parent-ref extraction, parent linkage, issue parsing, PR
parsing, orphan detection.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "show-tree.py"
)


@pytest.fixture(scope="module")
def st():
    module_name = "pm_show_tree_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _link_parents_textual_only(st, issues, monkeypatch) -> None:
    """Run `_link_parents` with the native `…/sub_issues` read stubbed to
    unsupported → textual-only resolution through the containment seam.

    show-tree no longer parses body parent-refs directly; it routes child
    building through `_lib.containment.resolve_children` (ADR-026). These linkage
    tests assert the TEXTUAL projection, so the native side is stubbed off; the
    native-wins / mixed-mode behaviour is proven in the read-seam test.
    """
    # Patch the function the resolver ACTUALLY calls. Stubbing the legacy
    # two-valued wrapper intercepted nothing, so these tests issued real
    # `gh api …/sub_issues` requests against whatever repo the git remote
    # resolves to — passing only because show-tree ignores the completeness
    # verdict and a failed native read degrades to a textual render.
    monkeypatch.setattr(
        st.containment,
        "read_native_children",
        lambda _config, *, parent_number: st.containment.NativeRead(
            numbers=set(), outcome=st.containment.NativeReadOutcome.UNSUPPORTED
        ),
    )
    st._link_parents(issues, {}, corpus_complete=True)


@pytest.fixture
def issue_types() -> dict:
    return {
        "types": {
            "epic": {"title_prefix": "EPIC", "title_case": "upper"},
            "feature": {"title_prefix": "Feature", "title_case": "title"},
            "umbrella": {"title_prefix": "Umbrella", "title_case": "title"},
            "task": {"title_prefix": "Task", "title_case": "title"},
        },
    }


# --- candidate-parent pre-scan ref recognition -----------------------
# show-tree's direct body-ref parser is gone; the seam owns authoritative
# resolution. `_first_parent_ref` survives only to BOUND which parents get a
# native read (it never decides the rendered child set) — same recognition.


def test_first_parent_ref_simple(st) -> None:
    body = "Feature: #42\n\n## What\nfoo"
    assert st._first_parent_ref(body) == 42


def test_first_parent_ref_epic_form(st) -> None:
    body = "EPIC: #99\n\nbody"
    assert st._first_parent_ref(body) == 99


def test_first_parent_ref_returns_none_when_no_ref(st) -> None:
    body = "## What\nplain body."
    assert st._first_parent_ref(body) is None


def test_first_parent_ref_empty_body(st) -> None:
    assert st._first_parent_ref("") is None


def test_first_parent_ref_skips_leading_whitespace(st) -> None:
    body = "\n\n   EPIC: #5\nbody"
    assert st._first_parent_ref(body) == 5


# --- structural type inference ---------------------------------------


def test_infer_recognises_each_prefix(st, issue_types) -> None:
    assert st.infer_structural_type("[EPIC] x", issue_types) == "epic"
    assert st.infer_structural_type("[Feature] y", issue_types) == "feature"
    assert st.infer_structural_type("[Umbrella] z", issue_types) == "umbrella"
    assert st.infer_structural_type("[Task] w", issue_types) == "task"


def test_infer_none_for_unknown_prefix(st, issue_types) -> None:
    assert st.infer_structural_type("plain", issue_types) is None


# --- issue parsing ---------------------------------------------------


def test_parse_issues_extracts_basic_fields(st, issue_types) -> None:
    raw = [
        {
            "number": 42,
            "title": "[Task] do thing",
            "body": "Feature: #1\n\n## What\nfoo",
            "state": "OPEN",
            "labels": [{"name": "type:feature"}, {"name": "priority:Medium"}],
            "milestone": {"title": "M1"},
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    assert 42 in issues
    issue = issues[42]
    assert issue.title == "[Task] do thing"
    assert issue.state == "open"
    assert issue.structural_type == "task"
    assert "type:feature" in issue.labels
    assert issue.milestone == "M1"


def test_parse_issues_handles_missing_milestone(st, issue_types) -> None:
    raw = [{"number": 1, "title": "[Task] x", "body": "", "state": "OPEN", "labels": []}]
    issues = st._parse_issues(raw, issue_types)
    assert issues[1].milestone is None


def test_parse_issues_skips_malformed(st, issue_types) -> None:
    raw = ["string", 42, {"title": "no number"}, {"number": 1, "title": "ok", "state": "OPEN"}]
    issues = st._parse_issues(raw, issue_types)
    assert 1 in issues
    assert len(issues) == 1


# --- PR parsing ------------------------------------------------------


def test_parse_prs_extracts_closes(st) -> None:
    raw = [{"number": 99, "title": "feat: x", "state": "OPEN", "body": "Closes #42"}]
    prs = st._parse_prs(raw)
    assert prs[99].closes == [42]


def test_parse_prs_extracts_multiple_closes(st) -> None:
    raw = [
        {
            "number": 99,
            "title": "feat: x",
            "state": "OPEN",
            "body": "Closes #1, fixes #2\nResolves #3",
        }
    ]
    prs = st._parse_prs(raw)
    assert prs[99].closes == [1, 2, 3]


def test_parse_prs_empty_closes_when_no_keyword(st) -> None:
    raw = [{"number": 99, "title": "x", "state": "OPEN", "body": "no keyword"}]
    prs = st._parse_prs(raw)
    assert prs[99].closes == []


# --- parent linking --------------------------------------------------


def test_link_parents_sets_relationships(st, issue_types, monkeypatch) -> None:
    raw = [
        {
            "number": 1,
            "title": "[EPIC] thing",
            "body": "Milestone: #M1",
            "state": "OPEN",
            "labels": [],
        },
        {
            "number": 2,
            "title": "[Feature] sub-feature",
            "body": "EPIC: #1\n",
            "state": "OPEN",
            "labels": [],
        },
        {
            "number": 3,
            "title": "[Task] do thing",
            "body": "Feature: #2\n",
            "state": "OPEN",
            "labels": [],
        },
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    assert issues[3].parent_number == 2
    assert issues[2].parent_number == 1
    # EPIC ref to Milestone: parent is M1 (not a real issue number); we
    # try to parse but EPIC's parent_ref says "Milestone: #M1" which
    # won't match the digits regex, so parent stays None.
    assert issues[1].parent_number is None
    assert 3 in issues[2].children
    assert 2 in issues[1].children


def test_link_parents_handles_missing_parent_target(st, issue_types, monkeypatch) -> None:
    """Parent ref that doesn't resolve in the loaded set stays unlinked."""
    raw = [
        {
            "number": 5,
            "title": "[Task] x",
            "body": "Feature: #999\n",
            "state": "OPEN",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    assert issues[5].parent_number is None


# --- orphan detection ------------------------------------------------


def test_orphan_task_with_no_parent_ref(st, issue_types, monkeypatch) -> None:
    raw = [
        {
            "number": 1,
            "title": "[Task] orphan",
            "body": "## What\nno parent ref",
            "state": "OPEN",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    orphans = st._detect_orphans(issues, {})
    assert 1 in orphans["open_issues_with_no_parent_ref"]


def test_epic_with_no_parent_is_not_orphan(st, issue_types, monkeypatch) -> None:
    """EPICs legitimately have no parent (parent_ref_optional)."""
    raw = [
        {
            "number": 1,
            "title": "[EPIC] thing",
            "body": "## Outcome\nfoo",
            "state": "OPEN",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    orphans = st._detect_orphans(issues, {})
    assert 1 not in orphans["open_issues_with_no_parent_ref"]


def test_orphan_pr_without_matching_closing_issue(st, issue_types) -> None:
    issues = st._parse_issues([], issue_types)
    prs = st._parse_prs(
        [{"number": 99, "title": "x", "state": "OPEN", "body": "Closes #42"}]
    )
    orphans = st._detect_orphans(issues, prs)
    assert 99 in orphans["prs_without_closing_issue_in_repo"]


def test_pr_with_matching_closing_issue_not_orphan(st, issue_types) -> None:
    raw_issues = [
        {
            "number": 42,
            "title": "[Task] x",
            "body": "Feature: #1\n",
            "state": "OPEN",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw_issues, issue_types)
    prs = st._parse_prs(
        [{"number": 99, "title": "y", "state": "OPEN", "body": "Closes #42"}]
    )
    orphans = st._detect_orphans(issues, prs)
    assert 99 not in orphans["prs_without_closing_issue_in_repo"]


def test_closed_issues_not_counted_as_orphans(st, issue_types, monkeypatch) -> None:
    raw = [
        {
            "number": 1,
            "title": "[Task] x",
            "body": "## What\nno parent ref",
            "state": "CLOSED",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    orphans = st._detect_orphans(issues, {})
    assert 1 not in orphans["open_issues_with_no_parent_ref"]


# --- a bounded render says it is bounded (#863) -------------------------------


def _run_show_tree(st, monkeypatch, capsys, *, total: int, limit: int, fmt: str = "text"):
    """Render a tracker of `total` issues through a `--limit` of `limit`.

    The `gh` stub honours `--limit` the way the real command does; without that
    the corpus would never be short and the label could never fire.
    """
    def fake_gh(args, config, **kwargs):
        if "pr" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if "issue" in args and "list" in args:
            n = int(args[args.index("--limit") + 1])
            rows = [
                {"number": i, "title": f"t{i}", "body": "## What", "state": "OPEN",
                 "labels": [], "milestone": None}
                for i in range(1, total + 1)
            ]
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps(rows[:n]), stderr=""
            )
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(st, "gh_run", fake_gh)
    monkeypatch.setattr(st.containment, "_gh_call", fake_gh)
    monkeypatch.setattr(sys, "argv", ["show-tree", "--format", fmt, "--limit", str(limit)])
    st.main()
    return capsys.readouterr()


def test_a_truncated_render_says_so(st, monkeypatch, capsys) -> None:
    """A tree built from a bounded corpus cannot tell "no other children" from
    "I stopped looking" — and this is the command people use to check whether a
    container is ready to close, so it must not present a short tree as whole."""
    captured = _run_show_tree(st, monkeypatch, capsys, total=40, limit=10)
    # stdout as well as stderr: a redirected render must keep the caveat, which
    # is the case the label exists for. The README and ADR both promise both.
    assert "[partial]" in captured.out
    assert "[partial]" in captured.err
    assert "higher --limit" in captured.out


def test_a_complete_render_carries_no_notice(st, monkeypatch, capsys) -> None:
    """The label has to mean something: absent when the corpus was exhausted."""
    captured = _run_show_tree(st, monkeypatch, capsys, total=4, limit=10)
    assert "[partial]" not in captured.err


def test_json_carries_the_same_caveat(st, monkeypatch, capsys) -> None:
    """A machine consumer gets the verdict too, not just the human reader."""
    captured = _run_show_tree(st, monkeypatch, capsys, total=40, limit=10, fmt="json")
    assert json.loads(captured.out)["complete"] is False


def test_refresh_children_views_refuses_on_a_bounded_corpus(st, monkeypatch, capsys) -> None:
    """The refresh WRITES, so a bounded corpus must stop it — not merely label it.

    The refresh has two triggers and only `create-issue`'s was gated at first;
    this one ran before the completeness check and would full-overwrite each
    parent's children comment from a truncated view. Worse than the read-side
    defect, because each comment is replaced wholesale and the damage outlives
    the command.
    """
    wrote: list = []

    def fake_gh(args, config, **kwargs):
        if "pr" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if "issue" in args and "list" in args:
            n = int(args[args.index("--limit") + 1])
            rows = [
                {"number": i, "title": f"t{i}", "body": "## What", "state": "OPEN",
                 "labels": [], "milestone": None}
                for i in range(1, 41)
            ]
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(rows[:n]), stderr="")
        wrote.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(st, "gh_run", fake_gh)
    monkeypatch.setattr(st.containment, "_gh_call", fake_gh)
    monkeypatch.setattr(st.session_guard, "enforce", lambda **_kw: True)
    monkeypatch.setattr(
        sys, "argv",
        ["show-tree", "--format", "text", "--limit", "10", "--refresh-children-views"],
    )
    rc = st.main()
    captured = capsys.readouterr()

    assert rc == 1, "a refused write must not exit success"
    assert "[refused]" in captured.err
    assert not any("comment" in " ".join(map(str, c)) for c in wrote), "nothing may be written"


def test_an_unreadable_native_panel_labels_the_render(st, monkeypatch, capsys) -> None:
    """A complete corpus is not sufficient: the seam must vouch per parent too.

    The corpus here is whole — no limit is struck — but the native sub-issues
    read fails in a way that cannot be attributed to an absent endpoint, so a
    parent may have children nobody saw. Driving the label off `corpus.complete`
    alone rendered that as a complete tree, which is the same "no other children"
    vs "I could not see them" confusion the label exists to prevent.
    """
    def fake_gh(args, config, **kwargs):
        joined = " ".join(args)
        if "pr" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if "issue" in args and "list" in args:
            # #2 names #1 as its parent, so #1 is a candidate parent and the
            # seam is actually asked about it. Without that nothing resolves and
            # the test would pass for want of a question rather than a verdict.
            rows = [
                {"number": 1, "title": "t1", "body": "## What", "state": "OPEN",
                 "labels": [], "milestone": None},
                {"number": 2, "title": "t2", "body": "EPIC: #1\n\n## What",
                 "state": "OPEN", "labels": [], "milestone": None},
            ]
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(rows), stderr="")
        if "sub_issues" in joined:
            # Reachable endpoint, unreadable answer -> the seam cannot vouch.
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="error connecting")
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(st, "gh_run", fake_gh)
    monkeypatch.setattr(st.containment, "_gh_call", fake_gh)
    monkeypatch.setattr(sys, "argv", ["show-tree", "--format", "json", "--limit", "500"])
    st.main()
    assert json.loads(capsys.readouterr().out)["complete"] is False


def test_a_truncated_view_reports_truncation_not_its_consequence(st) -> None:
    """When both causes hold, name the root one.

    A bounded corpus is handed to the seam as an unvouched one, so every parent
    then reports incomplete *as a consequence*. Reporting that instead told the
    operator "the corpus was read in full" while it plainly had been cut at the
    limit, and pointed them away from the remedy that would actually work.
    """
    both = st._partial_note(limit=5, truncated=True, incomplete_parents=[1, 2, 3])
    assert "first 5 issues" in both
    assert "read in full" not in both

    only_unvouched = st._partial_note(limit=500, truncated=False, incomplete_parents=[7])
    assert "#7" in only_unvouched
    assert "higher --limit will not help" in only_unvouched

    # Unreachable by construction, but a fallback that invents a cause is the one
    # thing this function exists to prevent.
    neither = st._partial_note(limit=500, truncated=False, incomplete_parents=[])
    assert "not established" in neither
    assert "--limit" not in neither


def test_refresh_refuses_a_filtered_corpus(st, monkeypatch, capsys) -> None:
    """A filter is not a truncation, and the completeness verdict cannot see it.

    `--state open` yields a corpus that is *complete for what it asked* while
    every closed child is absent from it. Writing a parent's children comment
    from that view drops them silently — the same defect as a bounded corpus,
    arriving with `complete=True`, so the truncation guard does not catch it.
    Measured on this repo when found: 148 of 530 issues visible.
    """
    wrote: list = []

    def fake_gh(args, config, **kwargs):
        if "pr" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if "issue" in args and "list" in args:
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps([
                {"number": 1, "title": "t1", "body": "## What", "state": "OPEN",
                 "labels": [], "milestone": None},
            ]), stderr="")
        wrote.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(st, "gh_run", fake_gh)
    monkeypatch.setattr(st.containment, "_gh_call", fake_gh)
    monkeypatch.setattr(st.session_guard, "enforce", lambda **_kw: True)
    # The DEFAULT state, which is what makes this matter: the plain invocation
    # was the one writing a filtered view.
    monkeypatch.setattr(sys, "argv", ["show-tree", "--refresh-children-views"])
    rc = st.main()
    captured = capsys.readouterr()

    assert rc == 1
    assert "--state all" in captured.err, "the refusal must name the remedy that works"
    assert not any("comment" in " ".join(map(str, c)) for c in wrote)
