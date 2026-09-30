"""edit-issue --milestone / --clear-milestone (#1049).

Moving an issue between milestones through the validated path: the target
resolves as `create-issue --milestone` resolves it (an OPEN milestone, by
number or title), the native field is written through the substrate-write
seam, a first line naming the old milestone follows the move, and a move that
would shift the issue in the lifecycle is refused. Every `gh` call is faked.
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
SCRIPT_PATH = CAP_ROOT / "scripts" / "edit-issue.py"

TASK_BODY = (
    "Milestone: [#5](../milestone/5)\n\n"
    "## What\nwork\n\n## Acceptance criteria\n- [ ] done\n\n## Doc impact\n- [ ] none\n"
)


@pytest.fixture(scope="module")
def ei():
    module_name = "pm_edit_issue_milestone_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _milestones(ei, *open_ones: tuple[int, str]):
    """A `resolve_milestone` fake over these OPEN milestones (number or title)."""
    table = [ei.Milestone(number=n, title=t) for n, t in open_ones]

    def resolve(arg, _config):
        for ms in table:
            if arg == str(ms.number) or arg == ms.title:
                return ms
        return None

    return resolve


def _issue(
    *,
    body: str = TASK_BODY,
    milestone=(5, "Milestone 5"),
    labels=("state:backlog",),
    title: str = "[Task] move me",
    state: str = "OPEN",
) -> dict:
    return {
        "title": title,
        "body": body,
        "state": state,
        "labels": [{"name": n} for n in labels],
        "milestone": {"number": milestone[0], "title": milestone[1]} if milestone else None,
    }


def _run(
    ei,
    monkeypatch,
    argv: list[str],
    issue: dict,
    *,
    open_milestones=((5, "Milestone 5"), (6, "Milestone 6")),
    comments: list | None = None,
) -> SimpleNamespace:
    """Run main() with every gate passed and every write captured.

    A milestone flag without `--reason` gets one, since the change requires it
    (#1016); tests of the reason rule itself build their argv by hand.
    """
    if ("--milestone" in argv or "--clear-milestone" in argv) and "--reason" not in argv:
        argv = [*argv, "--reason", "rescheduled"]
    monkeypatch.setattr(sys, "argv", ["edit-issue", *argv])
    monkeypatch.setattr(ei, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ei.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ei.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ei, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(ei, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        ei, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(ei, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(ei.axis_labels, "load_substrate_map", lambda *_a, **_k: None)
    monkeypatch.setattr(ei, "_gh_get_issue", lambda _n, _config: issue)
    monkeypatch.setattr(ei, "resolve_milestone", _milestones(ei, *open_milestones))

    record = SimpleNamespace(milestone_writes=[], clears=[], edits=[], comments=[], order=[])

    def fake_gh_run(cmd, config, **kwargs):
        # The audit comment's fetch-then-post (`post_audit_once`).
        stdout = ""
        if cmd[:3] == ["gh", "issue", "view"]:
            stdout = json.dumps({"comments": comments or []})
        elif cmd[:3] == ["gh", "issue", "comment"]:
            record.comments.append(cmd[cmd.index("--body") + 1])
            record.order.append("comment")
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(ei, "gh_run", fake_gh_run)

    def fake_write(config, *, issue_number, title):
        record.milestone_writes.append((issue_number, title))
        record.order.append("milestone")
        return SimpleNamespace(ok=True, detail="")

    def fake_clear(config, *, issue_number):
        record.clears.append(issue_number)
        return SimpleNamespace(ok=True, detail="")

    def fake_apply(issue_number, *, title, body, current_title, config):
        record.edits.append({"title": title, "body": body})
        return True

    monkeypatch.setattr(ei, "write_milestone", fake_write)
    monkeypatch.setattr(ei, "clear_milestone", fake_clear)
    monkeypatch.setattr(ei, "_gh_apply_edit", fake_apply)
    record.rc = ei.main()
    return record


# --- moving between milestones ----------------------------------------


def test_moves_the_milestone_and_the_first_line_follows(ei, monkeypatch) -> None:
    rec = _run(ei, monkeypatch, ["42", "--milestone", "6", "--yes"], _issue())
    assert rec.rc == 0
    assert rec.milestone_writes == [(42, "Milestone 6")]
    assert len(rec.edits) == 1
    assert rec.edits[0]["body"].startswith("Milestone: [#6](../milestone/6)\n\n## What")


def test_resolves_the_milestone_by_title(ei, monkeypatch) -> None:
    rec = _run(ei, monkeypatch, ["42", "--milestone", "Milestone 6", "--yes"], _issue())
    assert rec.rc == 0
    assert rec.milestone_writes == [(42, "Milestone 6")]


def test_an_issue_parent_first_line_is_left_alone(ei, monkeypatch) -> None:
    """The milestone is scheduling, not the parent, when the first line names
    an EPIC — only the native field moves; the body is not rewritten."""
    body = TASK_BODY.replace("Milestone: [#5](../milestone/5)", "EPIC: #10")
    rec = _run(ei, monkeypatch, ["42", "--milestone", "6", "--yes"], _issue(body=body))
    assert rec.rc == 0
    assert rec.milestone_writes == [(42, "Milestone 6")]
    assert rec.edits == []


def test_an_unknown_or_closed_milestone_is_a_usage_error(ei, monkeypatch, capsys) -> None:
    rec = _run(ei, monkeypatch, ["42", "--milestone", "99", "--yes"], _issue())
    assert rec.rc == 2
    assert rec.milestone_writes == [] and rec.edits == []
    assert "did not match any OPEN milestone" in capsys.readouterr().err


def test_the_same_milestone_is_a_noop(ei, monkeypatch, capsys) -> None:
    rec = _run(ei, monkeypatch, ["42", "--milestone", "5", "--yes"], _issue())
    assert rec.rc == 0
    assert rec.milestone_writes == [] and rec.edits == []
    assert "[noop]" in capsys.readouterr().out


def test_dry_run_writes_nothing(ei, monkeypatch) -> None:
    rec = _run(ei, monkeypatch, ["42", "--milestone", "6", "--dry-run"], _issue())
    assert rec.rc == 0
    assert rec.milestone_writes == [] and rec.edits == []


def test_combines_with_a_title_edit(ei, monkeypatch) -> None:
    rec = _run(
        ei, monkeypatch, ["42", "--milestone", "6", "--title", "[Task] renamed", "--yes"], _issue()
    )
    assert rec.rc == 0
    assert rec.milestone_writes == [(42, "Milestone 6")]
    assert rec.edits[0]["title"] == "[Task] renamed"


# --- the lifecycle guard ------------------------------------------------


def test_scheduling_a_label_less_todo_issue_is_refused(ei, monkeypatch, capsys) -> None:
    """With no state label, a milestone IS the Backlog signal: attaching one
    would move the issue Todo → Backlog without promote-issue's audit."""
    body = TASK_BODY.replace("Milestone: [#5](../milestone/5)", "EPIC: #10")
    rec = _run(
        ei,
        monkeypatch,
        ["42", "--milestone", "6", "--yes"],
        _issue(body=body, milestone=None, labels=()),
    )
    assert rec.rc == 1
    assert rec.milestone_writes == [] and rec.edits == []
    assert "promote-issue 42" in capsys.readouterr().err


def test_a_state_label_keeps_the_position_so_attach_is_allowed(ei, monkeypatch) -> None:
    body = TASK_BODY.replace("Milestone: [#5](../milestone/5)", "EPIC: #10")
    rec = _run(
        ei,
        monkeypatch,
        ["42", "--milestone", "6", "--yes"],
        _issue(body=body, milestone=None, labels=("state:in-progress",)),
    )
    assert rec.rc == 0
    assert rec.milestone_writes == [(42, "Milestone 6")]


def test_unscheduling_a_label_less_backlog_issue_is_refused(ei, monkeypatch, capsys) -> None:
    body = TASK_BODY.replace("Milestone: [#5](../milestone/5)", "EPIC: #10")
    rec = _run(ei, monkeypatch, ["42", "--clear-milestone", "--yes"], _issue(body=body, labels=()))
    assert rec.rc == 1
    assert rec.clears == []
    assert "no backlog → todo transition" in capsys.readouterr().err


# --- clearing ------------------------------------------------------------


def test_clear_detaches_when_the_first_line_names_an_issue_parent(ei, monkeypatch) -> None:
    body = TASK_BODY.replace("Milestone: [#5](../milestone/5)", "EPIC: #10")
    rec = _run(ei, monkeypatch, ["42", "--clear-milestone", "--yes"], _issue(body=body))
    assert rec.rc == 0
    assert rec.clears == [42]
    assert rec.edits == []


def test_clear_refuses_to_orphan_a_required_milestone_parent(ei, monkeypatch, capsys) -> None:
    rec = _run(ei, monkeypatch, ["42", "--clear-milestone", "--yes"], _issue())
    assert rec.rc == 1
    assert rec.clears == [] and rec.edits == []
    assert "set-field 42 --parent" in capsys.readouterr().err


def test_clear_drops_an_optional_milestone_line_on_an_epic(ei, monkeypatch) -> None:
    body = "Milestone: [#5](../milestone/5)\n\n## Thesis\nwhy\n"
    rec = _run(
        ei,
        monkeypatch,
        ["42", "--clear-milestone", "--yes"],
        _issue(body=body, title="[EPIC] Big thing"),
    )
    assert rec.rc == 0
    assert rec.clears == [42]
    assert rec.edits[0]["body"].startswith("## Thesis\nwhy\n")


def test_nothing_to_edit_names_the_milestone_flags(ei, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["edit-issue", "42"])
    assert ei.main() == 2
    assert "--milestone" in capsys.readouterr().err


def test_milestone_flags_are_mutually_exclusive(ei, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["edit-issue", "42", "--milestone", "6", "--clear-milestone"])
    with pytest.raises(SystemExit) as exc:
        ei.main()
    assert exc.value.code == 2


# --- the audit comment and the type check (#1016) -------------------------


def test_a_milestone_change_requires_a_reason(ei, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["edit-issue", "42", "--milestone", "6", "--reason", "  "])
    assert ei.main() == 2
    assert "--reason" in capsys.readouterr().err


def test_a_reason_without_a_milestone_flag_is_refused(ei, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["edit-issue", "42", "--title", "[Task] x", "--reason", "why"])
    assert ei.main() == 2


def test_the_change_posts_an_audit_comment_before_writing(ei, monkeypatch) -> None:
    rec = _run(
        ei,
        monkeypatch,
        ["42", "--milestone", "6", "--reason", "belongs to the second increment", "--yes"],
        _issue(),
    )
    assert rec.rc == 0
    assert rec.order == ["comment", "milestone"]
    (comment,) = rec.comments
    assert comment.startswith("<!-- pkit-hook: edit-issue-milestone -->")
    assert "Milestone: #5 Milestone 5 → #6 Milestone 6" in comment
    assert "reason: belongs to the second increment" in comment
    assert "<!-- pkit-audit-key: edit-issue-milestone:" in comment


def test_a_retry_does_not_post_the_audit_comment_twice(ei, monkeypatch) -> None:
    edit = ei.MilestoneEdit(
        current=ei.Milestone(number=5, title="Milestone 5"),
        target=ei.Milestone(number=6, title="Milestone 6"),
    )
    key = ei._milestone_audit_key(edit, "rescheduled")
    today = ei.dt.date.today().isoformat()
    posted = {
        "body": ei._milestone_audit_body(edit, "rescheduled", today, key),
        "viewerDidAuthor": True,
        "includesCreatedEdit": False,
    }
    rec = _run(ei, monkeypatch, ["42", "--milestone", "6", "--yes"], _issue(), comments=[posted])
    assert rec.rc == 0
    assert rec.comments == []
    assert rec.milestone_writes == [(42, "Milestone 6")]


def test_clearing_posts_the_audit_comment_too(ei, monkeypatch) -> None:
    body = TASK_BODY.replace("Milestone: [#5](../milestone/5)", "EPIC: #10")
    rec = _run(ei, monkeypatch, ["42", "--clear-milestone", "--yes"], _issue(body=body))
    assert rec.rc == 0
    assert "Milestone: #5 Milestone 5 → (none)" in rec.comments[0]


def test_a_noop_posts_no_audit_comment(ei, monkeypatch) -> None:
    rec = _run(ei, monkeypatch, ["42", "--milestone", "5", "--yes"], _issue())
    assert rec.rc == 0
    assert rec.comments == []


def test_an_epic_may_be_attached(ei, monkeypatch) -> None:
    """#1016's case: attaching EPIC #885 to Milestone 5. An EPIC's parent-ref
    form offers the milestone line, so its type may carry one."""
    body = "## Outcome\nwhy\n\n## Success criteria\n- [ ] it works\n"
    rec = _run(
        ei,
        monkeypatch,
        ["885", "--milestone", "6", "--yes"],
        _issue(body=body, title="[EPIC] Big thing", milestone=None, labels=("state:in-progress",)),
    )
    assert rec.rc == 0
    assert rec.milestone_writes == [(885, "Milestone 6")]


def test_an_unrecognised_type_may_not_carry_a_milestone(ei, monkeypatch, capsys) -> None:
    rec = _run(
        ei,
        monkeypatch,
        ["42", "--milestone", "6", "--yes"],
        _issue(title="Untyped title", labels=("state:backlog",)),
    )
    assert rec.rc == 1
    assert rec.milestone_writes == [] and rec.comments == []
    assert "does not let sit under a milestone" in capsys.readouterr().err


def test_type_may_carry_milestone_reads_the_schema(ei) -> None:
    types = {
        "types": {
            "epic": {
                "parent_issue_types": [],
                "parent_ref_form": "Milestone: [#<N>](../milestone/<N>)",
            },
            "feature": {
                "parent_issue_types": ["epic", "milestone"],
                "parent_ref_form": "EPIC: #<N>",
            },
            "leaf": {"parent_issue_types": ["feature"], "parent_ref_form": "Feature: #<N>"},
        }
    }
    assert ei._type_may_carry_milestone("epic", types)
    assert ei._type_may_carry_milestone("feature", types)
    assert not ei._type_may_carry_milestone("leaf", types)
    assert not ei._type_may_carry_milestone(None, types)
