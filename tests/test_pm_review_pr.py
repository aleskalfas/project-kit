"""Tests for `review-pr` (DEC-028 local-agent invocation + DEC-032 resolved set)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import MappingProxyType

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
SCRIPT = SCRIPTS_DIR / "review-pr.py"
RC_PATH = SCRIPTS_DIR / "_lib" / "review_contributions.py"


@pytest.fixture(scope="module")
def rpr():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_review_pr_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_review_pr_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


@pytest.fixture(scope="module")
def rc():
    lib_dir = SCRIPT.parent
    inserted = str(lib_dir) not in sys.path
    if inserted:
        sys.path.insert(0, str(lib_dir))
    try:
        spec = importlib.util.spec_from_file_location("pm_rc_for_review_pr", RC_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["pm_rc_for_review_pr"] = module
        spec.loader.exec_module(module)
        yield module
    finally:
        if inserted and str(lib_dir) in sys.path:
            sys.path.remove(str(lib_dir))


# ---- _get_local_registered ----------------------------------------


def test_local_registered_returns_list(rpr) -> None:
    config = {"review": {"agents": {"local_registered": [
        {"name": "critic"},
        {"name": "security-review"},
    ]}}}
    result = rpr._get_local_registered(config)
    assert len(result) == 2
    assert result[0]["name"] == "critic"


def test_local_registered_empty_when_absent(rpr) -> None:
    assert rpr._get_local_registered({}) == []
    assert rpr._get_local_registered({"review": {}}) == []
    assert rpr._get_local_registered({"review": {"agents": {}}}) == []


def test_local_registered_filters_entries_without_name(rpr) -> None:
    config = {"review": {"agents": {"local_registered": [
        {"name": "critic"},
        {"other_field": "x"},  # no name
        {"name": ""},  # empty name
        {"name": "code-review"},
    ]}}}
    result = rpr._get_local_registered(config)
    assert [e["name"] for e in result] == ["critic", "code-review"]


def test_local_registered_handles_non_dict_review(rpr) -> None:
    assert rpr._get_local_registered({"review": "lol"}) == []


# ---- _format_verdict_comment ------------------------------------


def test_format_verdict_approved(rpr) -> None:
    out = rpr._format_verdict_comment("critic", "APPROVED", "")
    assert out == "Reviewer agent (local, critic): APPROVED"


def test_format_verdict_with_body(rpr) -> None:
    out = rpr._format_verdict_comment(
        "critic", "CHANGES_REQUESTED", "Three findings:\n1. fix X\n2. fix Y",
    )
    assert out.startswith("Reviewer agent (local, critic): CHANGES_REQUESTED\n\n")
    assert "Three findings" in out


def test_format_verdict_strips_blank_body(rpr) -> None:
    """Whitespace-only body is omitted."""
    out = rpr._format_verdict_comment("critic", "APPROVED", "  \n  \n")
    assert out == "Reviewer agent (local, critic): APPROVED"


# ---- _invoke_agent verdict scan (DEC-028 grammar, anywhere in output) ----
#
# The parser must find the FIRST line matching the DEC-028 local-path verdict
# grammar anywhere in the agent's output — not require it on line 1. LLM
# reviewers non-deterministically emit preamble, so a line-1-only parse failed
# intermittently and posted no verdict, stalling the merge (issue #355).


def _stub_claude(rpr, monkeypatch, stdout, *, returncode=0, stderr=""):
    """Make `_invoke_agent` see `claude` on PATH and return `stdout`."""
    import subprocess

    monkeypatch.setattr(rpr.shutil, "which", lambda _bin: "/usr/bin/claude")

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=returncode, stdout=stdout, stderr=stderr,
        )

    monkeypatch.setattr(rpr.subprocess, "run", fake_run)


def test_invoke_verdict_on_first_line(rpr, monkeypatch) -> None:
    """Regression: a verdict on line 1 still parses (the happy path)."""
    out = "Reviewer agent (local, reviewer): APPROVED\n\nLooks good."
    _stub_claude(rpr, monkeypatch, out)
    verdict, body = rpr._invoke_agent("reviewer", 99, {})
    assert verdict == "APPROVED"
    assert body == "\nLooks good."


def test_invoke_verdict_after_preamble(rpr, monkeypatch) -> None:
    """The fix: a verdict preceded by LLM preamble is still found."""
    out = (
        "Let me review this PR.\n"
        "Here is my assessment of the diff:\n"
        "\n"
        "Reviewer agent (local, reviewer): CHANGES_REQUESTED\n"
        "\n"
        "Finding: fix the off-by-one in foo()."
    )
    _stub_claude(rpr, monkeypatch, out)
    verdict, body = rpr._invoke_agent("reviewer", 99, {})
    assert verdict == "CHANGES_REQUESTED"
    assert body == "\nFinding: fix the off-by-one in foo()."


def test_invoke_verdict_line_tolerates_surrounding_whitespace(rpr, monkeypatch) -> None:
    out = "   Reviewer agent (local, reviewer): APPROVED   \n"
    _stub_claude(rpr, monkeypatch, out)
    verdict, _body = rpr._invoke_agent("reviewer", 99, {})
    assert verdict == "APPROVED"


def test_invoke_first_match_wins(rpr, monkeypatch) -> None:
    """Multi-match precedence: the FIRST matching line is the verdict."""
    out = (
        "Reviewer agent (local, reviewer): APPROVED\n"
        "On reflection:\n"
        "Reviewer agent (local, reviewer): CHANGES_REQUESTED\n"
    )
    _stub_claude(rpr, monkeypatch, out)
    verdict, _body = rpr._invoke_agent("reviewer", 99, {})
    assert verdict == "APPROVED"


def test_invoke_no_match_fails_closed_and_surfaces_full_output(
    rpr, monkeypatch, capsys,
) -> None:
    """No grammar match anywhere → no verdict (caller posts nothing), and the
    FULL agent output is surfaced to the operator for debugging."""
    out = "I reviewed the PR but forgot to emit the verdict line.\nSorry!"
    _stub_claude(rpr, monkeypatch, out)
    verdict, body = rpr._invoke_agent("reviewer", 99, {})
    assert verdict is None
    assert body == ""
    err = capsys.readouterr().err
    assert "no DEC-028 verdict line found" in err
    # Full output present, not a truncated first line.
    assert "forgot to emit the verdict line" in err
    assert "Sorry!" in err


def test_invoke_verdict_pinned_to_invoked_agent_name(rpr, monkeypatch) -> None:
    """A verdict line naming a DIFFERENT agent does not satisfy the parse —
    review-pr only accepts a verdict from the agent it invoked."""
    out = "Reviewer agent (local, other-agent): APPROVED\n"
    _stub_claude(rpr, monkeypatch, out)
    verdict, _body = rpr._invoke_agent("reviewer", 99, {})
    assert verdict is None


def test_invoke_nonzero_exit_returns_no_verdict(rpr, monkeypatch) -> None:
    _stub_claude(rpr, monkeypatch, "", returncode=1, stderr="boom")
    verdict, _body = rpr._invoke_agent("reviewer", 99, {})
    assert verdict is None


# ---- _post_comment ----------------------------------------------


def test_post_comment_returns_false_on_none_pr(rpr) -> None:
    assert rpr._post_comment(None, "body", {}) is False


def test_post_comment_propagates_gh_failure(rpr, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="not authorised",
        )
    monkeypatch.setattr(rpr, "gh_run", fake_gh_run)
    assert rpr._post_comment(99, "body", {}) is False
    assert "not authorised" in capsys.readouterr().err


def test_post_comment_success(rpr, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(rpr, "gh_run", fake_gh_run)
    assert rpr._post_comment(99, "body", {}) is True


# ---- _resolution_error_message (fail-closed surfacing) --------------


def test_resolution_error_collection_names_capability(rpr, rc) -> None:
    err = rc.ContributionError(
        rc.ERROR_UNDEPLOYED_AGENT, "ux-ui-design",
        "design-reviewer is not deployed",
    )
    collection = rc.ContributionCollection(rules=(), errors=(err,))
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_COLLECTION,
            message="collection failed",
            collection=collection,
        )
    )
    msg = rpr._resolution_error_message(resolution)
    assert "fail-closed" in msg
    assert "ux-ui-design" in msg
    assert "not deployed" in msg


def test_resolution_error_closing_issues(rpr, rc) -> None:
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_CLOSING_ISSUES,
            message="gh pr view closingIssuesReferences failed: boom",
        )
    )
    msg = rpr._resolution_error_message(resolution)
    assert "fail-closed" in msg
    assert "boom" in msg


# ---- end-to-end invocation flow (DEC-032 D4) ------------------------
#
# These drive `main()` with the membership / branch / PR / invocation seams
# stubbed, and capture which reviewer names get invoked. The point: the set
# `review-pr` invokes is the RESOLVED required-local set (baseline ∪
# contributed), not just the static baseline.


def _wire_main(
    rpr, monkeypatch, tmp_path, *, resolution, invoked,
):
    """Stub main()'s seams; record invoked names into `invoked`.

    `resolution` is the Resolution `_resolve_required_local` returns (so we
    exercise main's loop without the gh round-trips). Each `_invoke_agent`
    call appends the name to `invoked` and returns an APPROVED verdict; the
    deployed-agent file existence check is satisfied by creating the files.
    """
    from types import SimpleNamespace

    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_root.mkdir(parents=True)
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    # Deploy a file for every name in the resolved set.
    if resolution.ok:
        for name in resolution.required_local:
            (agents_dir / f"{name}.md").write_text("agent", encoding="utf-8")

    monkeypatch.setattr(rpr, "resolve_capability_root", lambda arg: cap_root)
    monkeypatch.setattr(rpr, "load_adopter_config", lambda root: {
        "review": {"agents": {"local_registered": [{"name": "reviewer"}]}}
    })
    monkeypatch.setattr(rpr, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(rpr, "resolve_invoker_identity", lambda config: "dev")
    monkeypatch.setattr(
        rpr, "check_membership",
        lambda members, invoker: SimpleNamespace(allowed=True, refusal_message=""),
    )
    monkeypatch.setattr(rpr, "_find_issue_branch", lambda n: f"feat/{n}-x")
    monkeypatch.setattr(
        rpr, "_find_pr_for_branch", lambda branch, config: {"number": 99}
    )
    monkeypatch.setattr(
        rpr, "_resolve_required_local",
        lambda pr_number, config, repo_root, baseline: resolution,
    )

    def fake_invoke(name, pr_number, config):
        invoked.append(name)
        return "APPROVED", "body"

    monkeypatch.setattr(rpr, "_invoke_agent", fake_invoke)
    monkeypatch.setattr(rpr, "_post_comment", lambda pr, body, config: True)
    monkeypatch.setattr(sys, "argv", ["review-pr", "147"])


def test_no_contribution_single_reviewer_unchanged(rpr, monkeypatch, tmp_path) -> None:
    """No contributions → review-pr invokes the one baseline agent, as today."""
    resolution = rpr.Resolution(required_local=("reviewer",))
    invoked: list[str] = []
    _wire_main(rpr, monkeypatch, tmp_path, resolution=resolution, invoked=invoked)
    rc_code = rpr.main()
    assert rc_code == 0
    assert invoked == ["reviewer"]


def test_multi_reviewer_invokes_baseline_plus_contributed(rpr, monkeypatch, tmp_path) -> None:
    """A design PR → review-pr invokes BOTH the baseline reviewer and the
    contributed design-reviewer (DEC-032 D4)."""
    resolution = rpr.Resolution(
        required_local=("reviewer", "design-reviewer"),
        contributed_by={"design-reviewer": "ux-ui-design"},
    )
    invoked: list[str] = []
    _wire_main(rpr, monkeypatch, tmp_path, resolution=resolution, invoked=invoked)
    rc_code = rpr.main()
    assert rc_code == 0
    assert invoked == ["reviewer", "design-reviewer"]


def test_fail_closed_resolution_aborts_without_invoking(rpr, monkeypatch, tmp_path) -> None:
    """A not-ok resolution on the closing-issue branch (a transient gh failure
    resolving what the PR closes) aborts with exit 2 and invokes NOTHING — a
    required reviewer is never silently skipped (fail-closed, DEC-032 D5)."""
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_CLOSING_ISSUES, message="boom",
        )
    )
    invoked: list[str] = []
    _wire_main(rpr, monkeypatch, tmp_path, resolution=resolution, invoked=invoked)
    rc_code = rpr.main()
    assert rc_code == 2
    assert invoked == []


def test_undeployed_contributed_agent_aborts(rpr, rc, monkeypatch, tmp_path) -> None:
    """An installed contribution naming an UNDEPLOYED contributed reviewer
    (a not-ok collection, ERROR_COLLECTION) aborts review-pr with exit 2 and
    invokes NOTHING through `main()` — the same fail-closed posture done-work's
    gate has for this case (DEC-032 D5). G3: exercising the collection-error
    abort end-to-end, not just `_resolution_error_message` in isolation."""
    err = rc.ContributionError(
        rc.ERROR_UNDEPLOYED_AGENT, "ux-ui-design",
        "design-reviewer is not deployed",
    )
    collection = rc.ContributionCollection(rules=(), errors=(err,))
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_COLLECTION,
            message="reviewer contribution collection failed",
            collection=collection,
        )
    )
    invoked: list[str] = []
    _wire_main(rpr, monkeypatch, tmp_path, resolution=resolution, invoked=invoked)
    rc_code = rpr.main()
    assert rc_code == 2
    assert invoked == []
