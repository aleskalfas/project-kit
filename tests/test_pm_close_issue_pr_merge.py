"""close-issue --mode pr-merge --pr <M> (#1049, #1968).

An open leaf is closed as completed through merged PR M only where M relates
to it: its body closes the issue, or it was merged from the issue's branch
(#1968). The PR is verified merged through the gh seam, the relation found is
named, the checkbox close-gate runs, the reference is posted as a comment, and
the closure cascade runs. Without --pr the mode moves no open issue to Done: it
reconciles the labels of an issue already closed, and refuses an open one.
Every `gh` call is faked.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAP_ROOT / "scripts" / "close-issue.py"


@pytest.fixture(scope="module")
def ci():
    module_name = "pm_close_issue_pr_merge_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _issue(
    *,
    title="[Task] landed elsewhere",
    state="OPEN",
    body="EPIC: #10\n\n## What\nx\n",
    labels=("state:in-progress",),
) -> dict:
    return {
        "title": title,
        "body": body,
        "state": state,
        "labels": [{"name": n} for n in labels],
        "milestone": None,
    }


#: Merged from #991's branch; its body closes #991 and #42.
MERGED = {
    "number": 1042,
    "state": "MERGED",
    "mergedAt": "2026-09-27T10:00:00Z",
    "url": "u",
    "headRefName": "feat/991-the-other-task",
    "body": "Closes #991\nCloses #42\n\n## Summary\n\nx\n",
}
#: Merged from #42's own branch; its body closes no issue.
FROM_ITS_BRANCH = {**MERGED, "headRefName": "fix/42-landed-elsewhere", "body": "## Summary\n"}
#: Merged from #991's branch, its body closing #991 alone: nothing in it is #42's.
UNRELATED = {**MERGED, "body": "Closes #991\n\n## Summary\n\nx\n"}
OPEN_PR = {**MERGED, "state": "OPEN", "mergedAt": None}
THROUGH_1042 = ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"]


def _run(
    ci,
    monkeypatch,
    argv: list[str],
    *,
    issue: dict,
    pr: dict | None = MERGED,
    comments: list | None = None,
    parents: dict | None = None,
) -> SimpleNamespace:
    """Run main() with every gate passed; record each `gh` write."""
    monkeypatch.setattr(sys, "argv", ["close-issue", *argv])
    monkeypatch.setattr(ci, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ci.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ci.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ci, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(ci, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        ci, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(ci, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(ci.axis_labels, "load_substrate_map", lambda *_a, **_k: None)
    monkeypatch.setattr(ci, "fire_hooks", lambda *a, **k: None)
    # Recording the close with the engine (#1231) is test_pm_close_issue_journal's.
    journaled: list[tuple] = []
    monkeypatch.setattr(ci, "journal_move", lambda *a, **k: journaled.append(a))

    issues = {42: issue, **(parents or {})}
    monkeypatch.setattr(ci, "_gh_get_issue", lambda n, _config: issues.get(n))
    # The closure cascade's report reads the engine's fold over each parent's
    # children (#1937): every child closed, it says here.
    monkeypatch.setattr(ci, "_engine_cascade_fold", lambda _n: {"opened": True})
    # The closure cascade resolves the closed issue's parent from its record,
    # which carries its native parent: none here.
    monkeypatch.setattr(
        ci.containment,
        "read_issue_record",
        lambda _config, *, issue_number: ci.containment.IssueRecord(
            issue=issues[int(issue_number)], parent=None
        ),
    )
    pr_reads: list[int] = []

    def fake_get_pr(n, _config):
        pr_reads.append(n)
        return pr

    monkeypatch.setattr(ci, "_gh_get_pr", fake_get_pr)

    calls: list[list[str]] = []

    def fake_gh_run(cmd, config, **kwargs):
        calls.append(cmd)
        stdout = ""
        if cmd[:3] == ["gh", "issue", "view"] and "comments" in cmd:
            stdout = json.dumps({"comments": comments or []})
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(ci, "gh_run", fake_gh_run)
    rc = ci.main()
    return SimpleNamespace(rc=rc, calls=calls, pr_reads=pr_reads, journaled=journaled)


def _writes(rec) -> list[list[str]]:
    return [c for c in rec.calls if c[:3] != ["gh", "issue", "view"]]


def test_closes_an_open_leaf_as_completed_through_a_merged_pr(ci, monkeypatch, capsys) -> None:
    parent = {"title": "[EPIC] e", "state": "OPEN", "body": "- [ ] open box\n", "labels": []}
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(),
        parents={10: parent},
    )
    assert rec.rc == 0
    assert rec.pr_reads == [1042]
    writes = _writes(rec)
    comment = next(c for c in writes if c[:3] == ["gh", "issue", "comment"])
    body = comment[comment.index("--body") + 1]
    assert body.startswith("[pr-merge close] completed by merged PR #1042, whose body closes #42.")
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in writes
    label_edit = next(c for c in writes if c[:3] == ["gh", "issue", "edit"])
    assert label_edit[label_edit.index("--add-label") + 1] == "state:done"
    out = capsys.readouterr().out
    # The relation found is named before anything is written.
    assert "completed by: PR #1042 (merged), whose body closes #42" in out
    # The closure cascade ran over the parent the first line names.
    assert "[cascade] parents to check for eligibility: #10" in out


def _comment(rec) -> str:
    comment = next(c for c in _writes(rec) if c[:3] == ["gh", "issue", "comment"])
    return comment[comment.index("--body") + 1]


def test_closes_through_a_pr_merged_from_the_issue_s_branch(ci, monkeypatch, capsys) -> None:
    """A PR merged from the issue's own branch (DEC-013) relates to it although
    its body closes no issue (#1968)."""
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(),
        pr=FROM_ITS_BRANCH,
    )
    assert rec.rc == 0
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in _writes(rec)
    relation = "whose branch `fix/42-landed-elsewhere` is #42's"
    assert _comment(rec).startswith(f"[pr-merge close] completed by merged PR #1042, {relation}.")
    assert f"completed by: PR #1042 (merged), {relation}" in capsys.readouterr().out


def test_a_pr_related_both_ways_names_both(ci, monkeypatch, capsys) -> None:
    pr = {**FROM_ITS_BRANCH, "body": "Fixes #42\n"}
    rec = _run(ci, monkeypatch, THROUGH_1042, issue=_issue(), pr=pr)
    assert rec.rc == 0
    assert (
        "completed by: PR #1042 (merged), whose body closes #42 and whose branch "
        "`fix/42-landed-elsewhere` is #42's"
    ) in capsys.readouterr().out


@pytest.mark.parametrize(
    "pr",
    [
        UNRELATED,
        {**UNRELATED, "headRefName": "fix/42"},
        {**UNRELATED, "headRefName": "fix/420-another-task"},
        {**UNRELATED, "headRefName": "fix/4-2"},
        {**UNRELATED, "body": "Closes #420\n\nThe work of #42 landed here too.\n"},
        {**UNRELATED, "body": None, "headRefName": None},
    ],
    ids=[
        "closes-another",
        "branch-with-no-slug",
        "branch-of-420",
        "branch-splitting-the-number",
        "names-42-without-closing-it",
        "nothing-read",
    ],
)
def test_refuses_a_merged_pr_that_does_not_relate_to_the_issue(
    ci, monkeypatch, capsys, pr: dict
) -> None:
    """A merged PR that neither closes the issue nor was merged from its branch
    records nothing of having completed it: nothing is written (#1968)."""
    rec = _run(ci, monkeypatch, THROUGH_1042, issue=_issue(), pr=pr)
    assert rec.rc == 1
    assert _writes(rec) == []
    assert rec.journaled == []
    err = capsys.readouterr().err
    assert "[refused] PR #1042 has merged, but nothing in it relates it to #42" in err
    assert "`edit-pr 1042 --closes 42`" in err
    assert 'close-issue 42 --reason "<R>"' in err


def test_a_dry_run_refuses_an_unrelated_pr_too(ci, monkeypatch, capsys) -> None:
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--dry-run"],
        issue=_issue(),
        pr=UNRELATED,
    )
    assert rec.rc == 1
    assert _writes(rec) == []
    assert "[refused] PR #1042 has merged" in capsys.readouterr().err


@pytest.mark.parametrize("line", ["Epic: #10", "EPIC: #10 — the auth work", "Related: #10"])
def test_a_first_line_not_in_an_allowed_form_has_its_parent_checked_with_a_warning(
    ci, monkeypatch, capsys, line: str
) -> None:
    """A line the Task's type does not accept still names its parent — the close
    gate counts the Task under it — so the closure cascade checks that parent,
    and says the line is not an allowed form (#1281)."""
    parent = {"title": "[EPIC] e", "state": "OPEN", "body": "## What\n", "labels": []}
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(body=f"{line}\n\n## What\nx\n"),
        parents={10: parent},
    )
    assert rec.rc == 0
    out, err = capsys.readouterr()
    assert "[cascade] parents to check for eligibility: #10\n" in out
    assert "  · parent #10 open; no open child left and checkboxes complete" in out
    assert (
        f"[warn] #42's first line `{line}` is not a parent-ref a task may have: Feature: #<N> "
        "or Umbrella: #<N> or EPIC: #<N> or Milestone: [#<N>](../milestone/<N>); #10 is "
        "checked as its parent all the same.\n"
    ) in err


def test_a_body_naming_no_parent_is_said_to_name_none(ci, monkeypatch, capsys) -> None:
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(body="## What\nx\n"),
    )
    assert rec.rc == 0
    out, err = capsys.readouterr()
    assert (
        "[cascade] no parent issue: neither a native parent nor one named on the first line; "
        "parent check skipped."
    ) in out
    assert "first line names" not in err


def test_the_comment_is_posted_once_across_a_retry(ci, monkeypatch) -> None:
    """A run that posted the reference and then failed to close finds it on the
    re-run and does not post it again (the shared audit idempotence)."""
    _key, body = ci._pr_merge_close_comment(1042, "whose body closes #42")
    posted = [{"body": body, "viewerDidAuthor": True, "includesCreatedEdit": False}]
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(),
        comments=posted,
    )
    assert rec.rc == 0
    assert not any(c[:3] == ["gh", "issue", "comment"] for c in _writes(rec))
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in _writes(rec)


def test_refuses_a_pr_that_is_not_merged(ci, monkeypatch, capsys) -> None:
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(),
        pr=OPEN_PR,
    )
    assert rec.rc == 1
    assert _writes(rec) == []
    assert "not merged" in capsys.readouterr().err


def test_an_unreadable_pr_is_a_usage_error(ci, monkeypatch) -> None:
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(),
        pr=None,
    )
    assert rec.rc == 2
    assert _writes(rec) == []


def test_refuses_a_container(ci, monkeypatch, capsys) -> None:
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(title="[Feature] a container"),
    )
    assert rec.rc == 2
    assert rec.pr_reads == []
    assert "cascade-eligibility-close" in capsys.readouterr().err


def test_the_checkbox_gate_applies(ci, monkeypatch, capsys) -> None:
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(body="EPIC: #10\n\n- [ ] not yet\n"),
    )
    assert rec.rc == 1
    assert _writes(rec) == []
    assert "not yet" in capsys.readouterr().err


def test_dry_run_writes_nothing(ci, monkeypatch) -> None:
    rec = _run(
        ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--dry-run"], issue=_issue()
    )
    assert rec.rc == 0
    assert _writes(rec) == []


def test_pr_outside_pr_merge_mode_is_a_usage_error(ci, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["close-issue", "42", "--mode", "wont-do", "--pr", "1"])
    assert ci.main() == 2


def test_already_closed_issue_only_reconciles_labels(ci, monkeypatch, capsys) -> None:
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
        issue=_issue(state="CLOSED"),
    )
    assert rec.rc == 0
    writes = _writes(rec)
    assert not any(c[:3] in (["gh", "issue", "comment"], ["gh", "issue", "close"]) for c in writes)
    assert "[noop]" in capsys.readouterr().out


@pytest.mark.parametrize("extra", [["--yes"], ["--dry-run"], []], ids=["yes", "dry-run", "plain"])
def test_without_pr_an_open_issue_is_refused_and_nothing_written(
    ci, monkeypatch, capsys, extra: list[str]
) -> None:
    """No merged PR is named, so nothing says the issue's work landed: pr-merge
    mode moves no open issue to Done — no label, no journal entry (#1968)."""
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", *extra], issue=_issue())
    assert rec.rc == 1
    assert rec.pr_reads == []
    assert _writes(rec) == []
    assert rec.journaled == []
    err = capsys.readouterr().err
    assert "[refused] #42 is open, and pr-merge mode without --pr moves no open issue" in err
    assert "re-run with --pr <M>" in err


def test_without_pr_a_closed_issue_has_its_labels_reconciled(ci, monkeypatch, capsys) -> None:
    """GitHub closed the issue as a PR merged and left its label: the label is
    reconciled to done and the close journaled, with nothing closed again."""
    rec = _run(
        ci,
        monkeypatch,
        ["42", "--mode", "pr-merge", "--yes"],
        issue=_issue(state="CLOSED", labels=("state:review",)),
    )
    assert rec.rc == 0
    assert rec.pr_reads == []
    writes = _writes(rec)
    assert not any(c[:3] in (["gh", "issue", "comment"], ["gh", "issue", "close"]) for c in writes)
    label_edit = next(c for c in writes if c[:3] == ["gh", "issue", "edit"])
    assert label_edit[label_edit.index("--add-label") + 1] == "state:done"
    assert [entry[1:3] for entry in rec.journaled] == [("review", "done")]
    assert "[ok] noted pr-merge close for #42." in capsys.readouterr().out
