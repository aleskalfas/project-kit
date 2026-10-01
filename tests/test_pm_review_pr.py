"""Tests for `review-pr` (DEC-028 local-agent invocation + DEC-032 resolved set)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
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


def _mark_bootstrapped(cap_root: Path) -> None:
    """Make a staged tree look like the bootstrapped project it stands in for.

    Every pm verb except the five setup/diagnosis ones refuses a project with no
    bootstrap stamp or no adopter config (the #747 prerequisite gate); a staged
    tree standing in for a live project is a bootstrapped one. The config is
    seeded only when absent, so a test that stages its own keeps it, and the
    stamp is left unbound (`repo:` null) so no git remote is needed in a tmp tree.
    """
    project = cap_root / "project"
    project.mkdir(parents=True, exist_ok=True)
    config = project / "config.yaml"
    if not config.is_file():
        config.write_text(
            "schema_version: 1\ndefault_branch: main\nworkstreams: []\n",
            encoding="utf-8",
        )
    (project / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )


def test_local_registered_returns_list(rpr) -> None:
    config = {
        "review": {
            "agents": {
                "local_registered": [
                    {"name": "critic"},
                    {"name": "security-review"},
                ]
            }
        }
    }
    result = rpr._get_local_registered(config)
    assert len(result) == 2
    assert result[0]["name"] == "critic"


def test_local_registered_empty_when_absent(rpr) -> None:
    assert rpr._get_local_registered({}) == []
    assert rpr._get_local_registered({"review": {}}) == []
    assert rpr._get_local_registered({"review": {"agents": {}}}) == []


def test_local_registered_filters_entries_without_name(rpr) -> None:
    config = {
        "review": {
            "agents": {
                "local_registered": [
                    {"name": "critic"},
                    {"other_field": "x"},  # no name
                    {"name": ""},  # empty name
                    {"name": "code-review"},
                ]
            }
        }
    }
    result = rpr._get_local_registered(config)
    assert [e["name"] for e in result] == ["critic", "code-review"]


def test_local_registered_handles_non_dict_review(rpr) -> None:
    assert rpr._get_local_registered({"review": "lol"}) == []


# ---- _format_verdict_comment ------------------------------------


def test_format_verdict_approved(rpr) -> None:
    out = rpr._format_verdict_comment("critic", "APPROVED", "")
    # First line is the gate grammar; the verdict marker (#593) is appended.
    assert out.split("\n", 1)[0] == "Reviewer agent (local, critic): APPROVED"
    assert "<!-- pkit-verdict -->" in out


def test_format_verdict_with_body(rpr) -> None:
    out = rpr._format_verdict_comment(
        "critic",
        "CHANGES_REQUESTED",
        "Three findings:\n1. fix X\n2. fix Y",
    )
    assert out.startswith("Reviewer agent (local, critic): CHANGES_REQUESTED\n\n")
    assert "Three findings" in out
    assert "<!-- pkit-verdict -->" in out


def test_format_verdict_strips_blank_body(rpr) -> None:
    """Whitespace-only body is omitted; the verdict marker is still appended."""
    out = rpr._format_verdict_comment("critic", "APPROVED", "  \n  \n")
    assert out.split("\n", 1)[0] == "Reviewer agent (local, critic): APPROVED"
    assert "<!-- pkit-verdict -->" in out


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
            args=args,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
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
    rpr,
    monkeypatch,
    capsys,
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


# ---- per-agent reviewer timeout (issue #766) --------------------
#
# Precedence: --timeout flag > PKIT_REVIEW_AGENT_TIMEOUT env var > default 1200.
# The default is a generous ceiling (reviewer runs are slow and variable,
# observed 300s to >600s); it was raised 300s → 600s → 1200s as the ceiling
# kept getting hit. A single uniform value applies to every reviewer.


def test_timeout_default_is_1200(rpr) -> None:
    assert rpr.DEFAULT_AGENT_TIMEOUT == 1200
    assert rpr._resolve_agent_timeout(None, {}) == 1200


def test_timeout_env_overrides_default(rpr) -> None:
    env = {rpr.AGENT_TIMEOUT_ENV: "900"}
    assert rpr._resolve_agent_timeout(None, env) == 900


def test_timeout_flag_overrides_env(rpr) -> None:
    env = {rpr.AGENT_TIMEOUT_ENV: "900"}
    assert rpr._resolve_agent_timeout("450", env) == 450


def test_timeout_empty_env_falls_back_to_default(rpr) -> None:
    # An unset-but-present (empty string) env var is treated as absent.
    assert rpr._resolve_agent_timeout(None, {rpr.AGENT_TIMEOUT_ENV: ""}) == 1200


@pytest.mark.parametrize("bad", ["abc", "12.5", ""])
def test_timeout_invalid_flag_non_integer_errors(rpr, bad) -> None:
    with pytest.raises(ValueError) as exc:
        rpr._resolve_agent_timeout(bad, {})
    assert "--timeout" in str(exc.value)


@pytest.mark.parametrize("bad", ["0", "-1", "-600"])
def test_timeout_non_positive_flag_errors(rpr, bad) -> None:
    with pytest.raises(ValueError) as exc:
        rpr._resolve_agent_timeout(bad, {})
    assert "positive" in str(exc.value)


def test_timeout_invalid_env_errors_and_names_env(rpr) -> None:
    with pytest.raises(ValueError) as exc:
        rpr._resolve_agent_timeout(None, {rpr.AGENT_TIMEOUT_ENV: "nope"})
    assert rpr.AGENT_TIMEOUT_ENV in str(exc.value)


def test_invoke_agent_passes_timeout_to_subprocess(rpr, monkeypatch) -> None:
    """The resolved timeout reaches `subprocess.run`'s `timeout=` kwarg."""
    import subprocess

    captured: dict = {}
    monkeypatch.setattr(rpr.shutil, "which", lambda _bin: "/usr/bin/claude")

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="Reviewer agent (local, reviewer): APPROVED\n",
            stderr="",
        )

    monkeypatch.setattr(rpr.subprocess, "run", fake_run)
    rpr._invoke_agent("reviewer", 99, {}, 720)
    assert captured["timeout"] == 720


def test_invoke_agent_defaults_timeout_to_1200(rpr, monkeypatch) -> None:
    """Omitting the timeout arg uses the raised default, not the old 300/600."""
    import subprocess

    captured: dict = {}
    monkeypatch.setattr(rpr.shutil, "which", lambda _bin: "/usr/bin/claude")

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="Reviewer agent (local, reviewer): APPROVED\n",
            stderr="",
        )

    monkeypatch.setattr(rpr.subprocess, "run", fake_run)
    rpr._invoke_agent("reviewer", 99, {})
    assert captured["timeout"] == 1200


# ---- _post_comment ----------------------------------------------


def test_post_comment_returns_false_on_none_pr(rpr) -> None:
    assert rpr._post_comment(None, "body", {}) is False


def test_post_comment_propagates_gh_failure(rpr, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess

        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="not authorised",
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
        rc.ERROR_UNDEPLOYED_AGENT,
        "ux-ui-design",
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


def test_resolution_error_opt_out_names_the_entry(rpr) -> None:
    """An invalid contribution opt-out (#148) names the offending entry and
    points at the config key — not the transient-gh remediation."""
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_OPT_OUT,
            message="the reviewer-contribution opt-out list is invalid",
            details=(
                "review.agents.contributed_opt_out[0]: capability "
                "`ux-ui-design` is not an installed capability contributing "
                "reviewer requirements",
            ),
        )
    )
    msg = rpr._resolution_error_message(resolution)
    assert "fail-closed" in msg
    assert "contributed_opt_out[0]" in msg
    assert "`ux-ui-design`" in msg
    assert "review.agents.contributed_opt_out" in msg.split("Remediation:")[1]
    assert "transient" not in msg


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


def test_resolution_error_changed_files_asks_for_a_retry(rpr) -> None:
    """A failed changed-files read is a gh failure: retry — and the remedy no
    longer points at closing-issue links, which have nothing to do with it."""
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_CHANGED_FILES,
            message="gh api pulls/99/files failed: HTTP 502",
        )
    )
    msg = rpr._resolution_error_message(resolution)
    assert "HTTP 502" in msg
    remediation = msg.split("Remediation:")[1]
    assert "retry" in remediation
    assert "changed files" in remediation
    assert "closing-issue" not in remediation


def test_resolution_error_too_many_changed_files_names_the_cause(rpr) -> None:
    """A PR past GitHub's file listing is refused naming that cause and a
    split-or-bypass remedy — not "transient gh failure" (#1188)."""
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_TOO_MANY_CHANGED_FILES,
            message=(
                "PR #99 changes at least 3000 files, the most GitHub lists for "
                "a pull request — its complete changed-file set cannot be read"
            ),
        )
    )
    msg = rpr._resolution_error_message(resolution)
    assert "fail-closed" in msg
    assert "at least 3000 files" in msg
    remediation = msg.split("Remediation:")[1]
    assert "not transient" in remediation
    assert "Split the PR" in remediation
    assert "done-work --bypass" in remediation
    assert "transient gh failure" not in msg


# ---- the reviewer brief (#1188) ---------------------------------------


def test_review_brief_names_the_local_diff_for_a_refused_diff(rpr) -> None:
    """GitHub refuses `gh pr diff` past 300 files, so the brief tells the
    reviewer where else to read the diff: this checkout, from the merge base."""
    brief = rpr._review_brief(
        "reviewer",
        99,
        base="main",
        head="fix/1188-large-prs",
    )
    assert "Review the diff of PR #99" in brief
    assert "`gh pr diff 99`" in brief
    assert "300" in brief
    assert "`git diff origin/main...fix/1188-large-prs`" in brief
    assert "Reviewer agent (local, reviewer): APPROVED" in brief


def test_review_brief_leaves_an_unknown_base_as_a_placeholder(rpr) -> None:
    brief = rpr._review_brief("reviewer", 99, base=None, head="HEAD")
    assert "`git diff origin/<base>...HEAD`" in brief


def test_invoke_agent_sends_the_brief(rpr, monkeypatch) -> None:
    """The brief is what reaches the reviewer session as its prompt."""
    import subprocess

    captured: dict = {}
    monkeypatch.setattr(rpr.shutil, "which", lambda _bin: "/usr/bin/claude")

    def fake_run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="Reviewer agent (local, reviewer): APPROVED\n",
            stderr="",
        )

    monkeypatch.setattr(rpr.subprocess, "run", fake_run)
    rpr._invoke_agent("reviewer", 99, {}, 720, base="main", head="feat/147-x")
    prompt = captured["args"][captured["args"].index("-p") + 1]
    assert prompt == rpr._review_brief(
        "reviewer",
        99,
        base="main",
        head="feat/147-x",
    )


def test_find_pr_for_branch_reads_the_base_branch(rpr, monkeypatch) -> None:
    """The PR lookup reads the base branch the brief names."""
    import subprocess

    seen: dict = {}

    def fake_gh_run(args, config, **kwargs):
        seen["args"] = args
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stderr="",
            stdout=_json.dumps(
                [
                    {
                        "number": 99,
                        "isDraft": False,
                        "headRefName": "feat/147-x",
                        "baseRefName": "main",
                    }
                ]
            ),
        )

    monkeypatch.setattr(rpr, "gh_run", fake_gh_run)
    pr = rpr._find_pr_for_branch("feat/147-x", {})
    assert pr["baseRefName"] == "main"
    assert "baseRefName" in seen["args"][seen["args"].index("--json") + 1]


# ---- end-to-end invocation flow (DEC-032 D4) ------------------------
#
# These drive `main()` with the membership / branch / PR / invocation seams
# stubbed, and capture which reviewer names get invoked. The point: the set
# `review-pr` invokes is the RESOLVED required-local set (baseline ∪
# contributed), not just the static baseline.


_REVIEWED = "a" * 40
_MOVED_TO = "b" * 40
_BASE = "c" * 40


def _wire_main(
    rpr,
    monkeypatch,
    tmp_path,
    *,
    resolution,
    invoked,
    briefed=None,
    fresh=None,
    stale=None,
    unreadable=False,
    argv=(),
    heads=None,
    posted=None,
    native=None,
):
    """Stub main()'s seams; record invoked names into `invoked`.

    `resolution` is the Resolution `_resolve_required_local` returns (so we
    exercise main's loop without the gh round-trips). Each `_invoke_agent`
    call appends the name to `invoked` and returns an APPROVED verdict; the
    deployed-agent file existence check is satisfied by creating the files.
    `briefed`, when given, collects the `(base, head)` each call was passed.

    `fresh` is what the verdict read reports fresh (#1178) — reviewer name →
    token; default none fresh — and `stale` what it reports stale — reviewer
    name → (token, reason) (#1179); `unreadable` makes the read fail instead.
    Each read is recorded in the returned list. `argv` is extra CLI arguments.

    `heads` is the PR head each `_read_tips` call returns, in order, beside
    the base `_BASE` (#1179); default the same head every time. `posted`, when given, collects
    each posted comment body. `native`, when given, enables the native review
    and collects the verdict of each one delivered.
    """
    from types import SimpleNamespace

    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_root.mkdir(parents=True)
    _mark_bootstrapped(cap_root)
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    # Deploy a file for every name in the resolved set.
    if resolution.ok:
        for name in resolution.required_local:
            (agents_dir / f"{name}.md").write_text("agent", encoding="utf-8")

    monkeypatch.setattr(rpr, "resolve_capability_root", lambda arg: cap_root)
    monkeypatch.setattr(
        rpr,
        "load_adopter_config",
        lambda root: {"review": {"agents": {"local_registered": [{"name": "reviewer"}]}}},
    )
    monkeypatch.setattr(rpr, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(rpr, "resolve_invoker_identity", lambda config: "dev")
    monkeypatch.setattr(
        rpr,
        "check_membership",
        lambda members, invoker: SimpleNamespace(allowed=True, refusal_message=""),
    )
    monkeypatch.setattr(rpr, "_find_issue_branch", lambda n: f"feat/{n}-x")
    monkeypatch.setattr(
        rpr,
        "_find_pr_for_branch",
        lambda branch, config: {"number": 99, "baseRefName": "main"},
    )
    monkeypatch.setattr(
        rpr,
        "_resolve_required_local",
        lambda pr_number, config, repo_root, baseline: resolution,
    )

    def fake_invoke(
        name,
        pr_number,
        config,
        timeout=None,
        effort=None,
        *,
        base=None,
        head="HEAD",
        sha="",
    ):
        invoked.append(name)
        if briefed is not None:
            briefed.append((base, head))
        return "APPROVED", "body"

    monkeypatch.setattr(rpr, "_invoke_agent", fake_invoke)

    def fake_post(pr, body, config):
        if posted is not None:
            posted.append(body)
        return True

    monkeypatch.setattr(rpr, "_post_comment", fake_post)
    head_reads = iter(heads) if heads is not None else None
    monkeypatch.setattr(
        rpr,
        "_read_tips",
        lambda pr, config: (next(head_reads) if head_reads else _REVIEWED, _BASE),
    )

    reads: list[tuple[int, list[str]]] = []

    def fake_read_states(pr_number, resolution, config):
        reads.append((pr_number, list(resolution.required_local)))
        if unreadable:
            return None
        return rpr._VerdictStates(fresh=dict(fresh or {}), stale=dict(stale or {}))

    monkeypatch.setattr(rpr, "_read_verdict_states", fake_read_states)
    if native is None:
        # `--no-native` keeps the native-review delivery (a live `gh` call) out.
        argv = ("--no-native", *argv)
    else:
        monkeypatch.setattr(
            rpr,
            "_deliver_native_review",
            lambda pr, verdict, comment, config: native.append(verdict),
        )
    monkeypatch.setattr(sys, "argv", ["review-pr", "147", *argv])
    return reads


def test_no_contribution_single_reviewer_unchanged(rpr, monkeypatch, tmp_path) -> None:
    """No contributions → review-pr invokes the one baseline agent, as today."""
    resolution = rpr.Resolution(required_local=("reviewer",))
    invoked: list[str] = []
    _wire_main(rpr, monkeypatch, tmp_path, resolution=resolution, invoked=invoked)
    rc_code = rpr.main()
    assert rc_code == 0
    assert invoked == ["reviewer"]


def test_each_reviewer_is_briefed_with_the_prs_base_and_branch(
    rpr,
    monkeypatch,
    tmp_path,
) -> None:
    """main hands every reviewer the PR's base and its branch, so the brief's
    local-diff fallback names the real range (#1188)."""
    resolution = rpr.Resolution(
        required_local=("reviewer", "code-reviewer"),
        contributed_by={"code-reviewer": "software-engineering"},
    )
    invoked: list[str] = []
    briefed: list[tuple] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=resolution,
        invoked=invoked,
        briefed=briefed,
    )
    assert rpr.main() == 0
    assert briefed == [("main", "feat/147-x"), ("main", "feat/147-x")]


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


def test_opted_out_contribution_is_listed_with_its_reason(
    rpr,
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    """#148: review-pr names each opt-out in force, with its reason, next to
    the reviewers it invokes — and does not invoke the opted-out reviewer."""
    (opt_out,) = rpr.read_opt_outs(
        {
            "review": {
                "agents": {
                    "contributed_opt_out": [
                        {
                            "capability": "software-engineering",
                            "reviewer": "docs-reviewer",
                            "reason": "Docs are reviewed by the tech-writing team.",
                        }
                    ]
                }
            }
        }
    ).entries
    resolution = rpr.Resolution(
        required_local=("reviewer", "code-reviewer"),
        contributed_by={"code-reviewer": "software-engineering"},
        opted_out=(opt_out,),
    )
    invoked: list[str] = []
    _wire_main(rpr, monkeypatch, tmp_path, resolution=resolution, invoked=invoked)
    assert rpr.main() == 0
    assert invoked == ["reviewer", "code-reviewer"]
    out = capsys.readouterr().out
    assert (
        "  opted out: docs-reviewer (capability `software-engineering`) — "
        "Docs are reviewed by the tech-writing team."
    ) in out


def test_fail_closed_resolution_aborts_without_invoking(rpr, monkeypatch, tmp_path) -> None:
    """A not-ok resolution on the closing-issue branch (a transient gh failure
    resolving what the PR closes) aborts with exit 2 and invokes NOTHING — a
    required reviewer is never silently skipped (fail-closed, DEC-032 D5)."""
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_CLOSING_ISSUES,
            message="boom",
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
        rc.ERROR_UNDEPLOYED_AGENT,
        "ux-ui-design",
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


# ---- the head a reviewer reviewed (#1179) -----------------------------
#
# review-pr reads the PR's head before invoking a reviewer, names it in the
# brief, checks it is unchanged before posting, and stamps it in the verdict
# marker. A head that moved is reported; the verdict still names the head the
# reviewer saw, and the freshness rule judges what changed since.


def test_review_brief_names_the_head_under_review(rpr) -> None:
    brief = rpr._review_brief(
        "reviewer",
        99,
        base="main",
        head="feat/1179-x",
        sha=_REVIEWED,
    )
    assert f"You are reviewing its head commit {_REVIEWED}" in brief
    assert f"`git diff origin/main...{_REVIEWED}`" in brief


def test_each_verdict_names_the_head_its_reviewer_saw(
    rpr,
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    posted: list[str] = []
    native: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=("reviewer",)),
        invoked=[],
        posted=posted,
        native=native,
    )
    assert rpr.main() == 0
    (comment,) = posted
    assert comment.endswith(f"<!-- pkit-verdict sha={_REVIEWED} base={_BASE} -->\n")
    assert native == ["APPROVED"]
    assert "moved" not in capsys.readouterr().out


def test_a_head_that_moves_during_the_review_is_reported(
    rpr,
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    """A push during the review: the verdict is posted against the head the
    reviewer saw (so the freshness rule holds it stale once the push is a
    change it checks), and no native review lands on the head it never saw."""
    posted: list[str] = []
    native: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=("reviewer",)),
        invoked=[],
        posted=posted,
        native=native,
        heads=[_REVIEWED, _MOVED_TO],
    )
    assert rpr.main() == 0
    (comment,) = posted
    assert f"sha={_REVIEWED}" in comment
    assert native == []
    out = capsys.readouterr().out
    assert "[reviewer] the PR's head moved from aaaaaaa to bbbbbbb" in out
    assert "the verdict is recorded against aaaaaaa" in out
    assert "[native] skipped" in out


def test_an_unreadable_head_posts_a_verdict_naming_none(
    rpr,
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    """Without the head, the verdict names none and falls back to the latest
    commit's time — today's rule — rather than not being posted."""
    posted: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=("reviewer",)),
        invoked=[],
        posted=posted,
        heads=["", ""],
    )
    assert rpr.main() == 0
    (comment,) = posted
    assert comment.endswith("<!-- pkit-verdict -->\n")
    assert "names no reviewed head" in capsys.readouterr().out


def test_report_head_check_when_the_head_cannot_be_read_again(rpr, capsys) -> None:
    assert rpr._report_head_check("reviewer", _REVIEWED, "") is False
    assert "could not be read again" in capsys.readouterr().out
    assert rpr._report_head_check("reviewer", _REVIEWED, _REVIEWED) is True


def test_read_tips(rpr, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake(argv, config, check=False):
        calls.append(list(argv))
        return _Proc(0, _json.dumps({"headRefOid": _REVIEWED, "baseRefOid": _BASE}))

    monkeypatch.setattr(rpr, "gh_run", fake)
    assert rpr._read_tips(99, {}) == (_REVIEWED, _BASE)
    assert calls == [["gh", "pr", "view", "99", "--json", "headRefOid,baseRefOid"]]
    for proc in (_Proc(1, "", "gh down"), _Proc(0, "not json"), _Proc(0, "[]")):
        monkeypatch.setattr(
            rpr,
            "gh_run",
            lambda argv, config, check=False, proc=proc: proc,
        )
        assert rpr._read_tips(99, {}) == ("", "")
    assert rpr._read_tips(None, {}) == ("", "")


# ---- fresh-verdict skip and --force (#1178) --------------------------
#
# A required reviewer whose latest verdict is still fresh is not re-run;
# `--force` re-runs it. What counts as fresh is done-work's own selection
# (`gate_verdicts` with the freshness rule, `_lib.verdict_freshness`).

_PANEL = ("reviewer", "code-reviewer")


def test_fresh_approved_reviewer_is_not_re_run(
    rpr,
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    invoked: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        fresh={"reviewer": "APPROVED"},
    )
    assert rpr.main() == 0
    assert invoked == ["code-reviewer"]
    out = capsys.readouterr().out
    assert "  [reviewer] fresh verdict APPROVED — not re-run" in out
    assert "--force re-runs a reviewer whose verdict is fresh." in out


def test_fresh_changes_requested_reviewer_is_not_re_run(
    rpr,
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    """A fresh CHANGES_REQUESTED is not re-run either: the same head would be
    reviewed again. A new commit makes it stale."""
    invoked: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        fresh={"code-reviewer": "CHANGES_REQUESTED"},
    )
    assert rpr.main() == 0
    assert invoked == ["reviewer"]
    out = capsys.readouterr().out
    assert "  [code-reviewer] fresh verdict CHANGES_REQUESTED — not re-run" in out


def test_a_stale_reviewer_is_re_run_with_the_reason(
    rpr,
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    """A re-run is never silent about why (#1179): the reviewer whose verdict
    went stale is named with the freshness rule's reason before it runs."""
    invoked: list[str] = []
    reason = (
        "reviewed aaaaaaa; the changes since cannot be read: the reviewed head, "
        "aaaaaaa, is not in this checkout and could not be fetched from origin: "
        "fatal: unable to access origin"
    )
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        fresh={"reviewer": "APPROVED"},
        stale={"code-reviewer": ("APPROVED", reason)},
    )
    assert rpr.main() == 0
    assert invoked == ["code-reviewer"]
    out = capsys.readouterr().out
    assert f"  [code-reviewer] stale verdict APPROVED ({reason}) — re-run" in out


def test_every_reviewer_fresh_invokes_nothing(rpr, monkeypatch, tmp_path) -> None:
    invoked: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        fresh={"reviewer": "APPROVED", "code-reviewer": "APPROVED"},
    )
    assert rpr.main() == 0
    assert invoked == []


def test_force_re_runs_a_fresh_reviewer(rpr, monkeypatch, tmp_path, capsys) -> None:
    invoked: list[str] = []
    reads = _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        fresh={"reviewer": "APPROVED"},
        argv=("--force",),
    )
    assert rpr.main() == 0
    assert invoked == ["reviewer", "code-reviewer"]
    assert reads == []  # --force does not consult the verdicts at all.
    assert "not re-run" not in capsys.readouterr().out


def test_unreadable_verdicts_run_every_reviewer(
    rpr,
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    invoked: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        unreadable=True,
    )
    assert rpr.main() == 0
    assert invoked == ["reviewer", "code-reviewer"]
    assert "fresh verdicts: could not be read" in capsys.readouterr().out


def test_dry_run_reports_the_skip(rpr, monkeypatch, tmp_path, capsys) -> None:
    invoked: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        fresh={"reviewer": "APPROVED"},
        argv=("--dry-run",),
    )
    assert rpr.main() == 0
    assert invoked == []
    out = capsys.readouterr().out
    assert "  [reviewer] fresh verdict APPROVED — not re-run" in out
    assert "  [code-reviewer] (dry-run) would invoke against PR #99" in out


# ---- `review()`, for a verb that composes the review (`land-work`, #1203) ---


def test_review_reports_what_became_of_each_reviewer(rpr, monkeypatch, tmp_path) -> None:
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=[],
        fresh={"reviewer": "CHANGES_REQUESTED"},
    )
    run = rpr.review()
    assert run.exit_code == 0
    assert run.pr_number == 99
    assert run.kept == {"reviewer": "CHANGES_REQUESTED"}
    (token, comment) = run.posted["code-reviewer"]
    assert token == "APPROVED"
    assert comment.startswith("Reviewer agent (local, code-reviewer): APPROVED\n\nbody")
    assert run.failed == {}
    assert run.moved_to is None


def test_review_names_a_reviewer_that_could_not_run(rpr, monkeypatch, tmp_path) -> None:
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=[],
    )
    monkeypatch.setattr(rpr, "_invoke_agent", lambda *a, **k: (None, ""))
    run = rpr.review()
    assert run.exit_code == 3
    assert run.failed == {
        "reviewer": "the invocation failed, so there is no verdict to post",
        "code-reviewer": "the invocation failed, so there is no verdict to post",
    }
    assert run.posted == {}


def test_review_lists_whom_a_dry_run_would_invoke(rpr, monkeypatch, tmp_path) -> None:
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=[],
        fresh={"reviewer": "APPROVED"},
        argv=("--dry-run",),
    )
    run = rpr.review()
    assert run.kept == {"reviewer": "APPROVED"}
    assert run.would_run == ["code-reviewer"]


def test_review_with_a_pinned_head_reviews_only_that_head(
    rpr, monkeypatch, tmp_path, capsys
) -> None:
    """The PR moved after its checks were waited for: no reviewer is shown the
    new head, and nothing is posted."""
    invoked: list[str] = []
    posted: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        posted=posted,
        heads=[_MOVED_TO],
    )
    run = rpr.review(pinned_head=_REVIEWED)
    assert run.exit_code == 3
    assert run.moved_to == _MOVED_TO
    assert invoked == []
    assert posted == []
    assert (
        "  [reviewer] not run — the PR's head is bbbbbbb, not aaaaaaa, the head this "
        "review was asked to review."
    ) in capsys.readouterr().out


def test_review_with_a_pinned_head_stops_when_it_moves_during_a_review(
    rpr, monkeypatch, tmp_path
) -> None:
    """The verdict on the pinned head is posted — it is that head's — and no
    further reviewer runs on a PR that has moved on."""
    invoked: list[str] = []
    posted: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
        posted=posted,
        heads=[_REVIEWED, _MOVED_TO],
    )
    run = rpr.review(pinned_head=_REVIEWED)
    assert run.exit_code == 3
    assert run.moved_to == _MOVED_TO
    assert invoked == ["reviewer"]
    (comment,) = posted
    assert f"sha={_REVIEWED}" in comment


def test_review_with_a_pinned_head_that_holds_runs_every_reviewer(
    rpr, monkeypatch, tmp_path
) -> None:
    invoked: list[str] = []
    _wire_main(
        rpr,
        monkeypatch,
        tmp_path,
        resolution=rpr.Resolution(required_local=_PANEL),
        invoked=invoked,
    )
    run = rpr.review(pinned_head=_REVIEWED)
    assert run.exit_code == 0
    assert invoked == list(_PANEL)
    assert run.moved_to is None


_HEAD = [
    {"committedDate": "2026-06-01T00:00:00Z"},
    {"oid": "head", "committedDate": "2026-06-02T00:00:00Z"},
]


def _rule(rpr, commits=_HEAD):
    """The freshness rule for a PR whose verdicts name no head: they are
    judged by the latest commit's time."""
    return rpr.rule_for_pr(
        {"commits": commits},
        rpr.Resolution(),
        author_delta=lambda *a, **k: pytest.fail("no head is named"),
        base_kept=lambda *a, **k: pytest.fail("no base is named"),
    )


def _verdict_comment(name, token, ts, *, marked=True, remote=False):
    first = f"Reviewer agent: {token}" if remote else (f"Reviewer agent (local, {name}): {token}")
    body = f"{first}\n\nreasons"
    if marked:
        body += "\n\n<!-- pkit-verdict -->"
    return {"author": {"login": name}, "body": body, "createdAt": ts}


def test_local_verdict_states_count_only_what_the_gate_counts(rpr) -> None:
    comments = [
        # after the head, marked, required → fresh
        _verdict_comment("reviewer", "APPROVED", "2026-06-03T00:00:00Z"),
        # at the head → stale (strictly after is fresh)
        _verdict_comment("code-reviewer", "APPROVED", "2026-06-02T00:00:00Z"),
        # after the head but unmarked → not a gate verdict
        _verdict_comment("security-reviewer", "APPROVED", "2026-06-03T00:00:00Z", marked=False),
        # after the head but not required
        _verdict_comment("design-reviewer", "APPROVED", "2026-06-03T00:00:00Z"),
        # a remote verdict is not a local reviewer's
        _verdict_comment("docs-reviewer", "APPROVED", "2026-06-03T00:00:00Z", remote=True),
    ]
    required = ["reviewer", "code-reviewer", "security-reviewer", "docs-reviewer"]
    assert rpr._local_verdict_states(comments, _rule(rpr), required).fresh == {
        "reviewer": "APPROVED",
    }


def test_local_verdict_states_read_the_latest_verdict(rpr) -> None:
    comments = [
        _verdict_comment("reviewer", "APPROVED", "2026-06-03T00:00:00Z"),
        _verdict_comment("reviewer", "CHANGES_REQUESTED", "2026-06-04T00:00:00Z"),
    ]
    states = rpr._local_verdict_states(comments, _rule(rpr), ["reviewer"])
    assert states.fresh == {"reviewer": "CHANGES_REQUESTED"}
    # The fresh verdict's own body, for a caller to quote its findings.
    assert states.bodies == {"reviewer": comments[1]["body"]}


def test_local_verdict_states_without_a_head_timestamp_are_stale(rpr) -> None:
    # A verdict naming no head is fresh only after the latest commit; with
    # that commit's time unknown it is stale, so the reviewer runs again.
    comments = [_verdict_comment("reviewer", "APPROVED", "2026-06-03T00:00:00Z")]
    assert rpr._local_verdict_states(comments, _rule(rpr, []), ["reviewer"]).fresh == {}
    states = rpr._local_verdict_states(comments, _rule(rpr, [{"oid": "x"}]), ["reviewer"])
    assert states.fresh == {}
    # The re-run says why: the latest commit's time is unknown.
    assert states.stale == {
        "reviewer": (
            "APPROVED",
            "no reviewed head recorded; the latest commit's time is unknown",
        ),
    }


def test_local_verdict_states_keep_a_floor_reviewer_fresh_past_a_markdown_fix(
    rpr,
) -> None:
    """The skip applies the gate's rule (#1179): after a Markdown-only fix a
    floor-only reviewer's verdict stands and it is not re-run; the baseline
    reviewer's does not."""
    from _lib.author_delta import AuthorDelta

    def pinned(name):
        comment = _verdict_comment(name, "APPROVED", "2026-06-01T00:00:00Z")
        comment["body"] = rpr.stamp_verdict(comment["body"], _REVIEWED)
        return comment

    resolution = rpr.Resolution(
        required_local=("reviewer", "code-reviewer"),
        floors_by_reviewer={"code-reviewer": frozenset({"touches-code"})},
    )
    rule = rpr.rule_for_pr(
        {"headRefOid": _MOVED_TO, "commits": _HEAD},
        resolution,
        author_delta=lambda since, head, *, base_tip: AuthorDelta(
            paths=("README.md",),
        ),
        base_kept=lambda reviewed_base, base_tip: pytest.fail("no base is named"),
    )
    comments = [pinned("reviewer"), pinned("code-reviewer")]
    states = rpr._local_verdict_states(comments, rule, resolution.required_local)
    assert states.fresh == {"code-reviewer": "APPROVED"}
    assert states.stale == {
        "reviewer": ("APPROVED", "reviewed aaaaaaa; changed since: README.md"),
    }


def test_read_verdict_states_fetches_comments_head_and_base(rpr, monkeypatch) -> None:
    calls: list[list[str]] = []
    payload = {
        "comments": [
            _verdict_comment("reviewer", "APPROVED", "2026-06-03T00:00:00Z"),
        ],
        "commits": _HEAD,
    }

    def fake(argv, config, check=False):
        calls.append(list(argv))
        return _Proc(0, _json.dumps(payload))

    monkeypatch.setattr(rpr, "gh_run", fake)
    resolution = rpr.Resolution(required_local=("reviewer",))
    assert rpr._read_verdict_states(99, resolution, {}) == rpr._VerdictStates(
        fresh={"reviewer": "APPROVED"},
    )
    assert calls == [
        [
            "gh",
            "pr",
            "view",
            "99",
            "--json",
            "comments,commits,headRefOid,baseRefOid",
        ]
    ]


@pytest.mark.parametrize(
    "proc",
    [
        lambda: _Proc(1, "", "gh down"),
        lambda: _Proc(0, "not json"),
        lambda: _Proc(0, "[]"),
    ],
)
def test_read_verdict_states_unreadable_is_none(rpr, monkeypatch, proc) -> None:
    monkeypatch.setattr(rpr, "gh_run", lambda argv, config, check=False: proc())
    resolution = rpr.Resolution(required_local=("reviewer",))
    assert rpr._read_verdict_states(99, resolution, {}) is None


def test_resolution_error_not_code_names_the_key(rpr) -> None:
    resolution = rpr.Resolution(
        error=rpr.RequiredReviewersError(
            kind=rpr.ERROR_NOT_CODE,
            message="the not-code list is invalid",
            details=("`review.floors.not_code` must be a list, got str",),
        )
    )
    msg = rpr._resolution_error_message(resolution)
    assert "fail-closed" in msg
    assert "must be a list, got str" in msg
    assert "review.floors.not_code" in msg.split("Remediation:")[1]
    assert "transient" not in msg


# ---- native GitHub review delivery (DEC-028, amended) ----------------

import json as _json  # noqa: E402


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_gh(author: str = "alice", me: str = "bob"):
    """A gh_run stand-in that answers pr-view (author), api-user (login), and
    records the pr-review call. Returns (fake, calls)."""
    calls: list[list[str]] = []

    def fake(argv, config, check=False):
        calls.append(list(argv))
        if argv[:3] == ["gh", "pr", "view"]:
            return _Proc(0, _json.dumps({"author": {"login": author}}))
        if argv[:2] == ["gh", "api"]:  # gh api user --jq .login
            return _Proc(0, me + "\n")
        if argv[:3] == ["gh", "pr", "review"]:
            return _Proc(0, "")
        return _Proc(0, "")

    return fake, calls


def test_deliver_native_review_approve(rpr, monkeypatch) -> None:
    fake, calls = _fake_gh(author="alice", me="bob")
    monkeypatch.setattr(rpr, "gh_run", fake)
    rpr._deliver_native_review(42, "APPROVED", "the body", {})
    review = [c for c in calls if c[:3] == ["gh", "pr", "review"]]
    assert len(review) == 1 and "--approve" in review[0]
    assert "42" in review[0] and "the body" in review[0]


def test_deliver_native_review_request_changes(rpr, monkeypatch) -> None:
    fake, calls = _fake_gh(author="alice", me="bob")
    monkeypatch.setattr(rpr, "gh_run", fake)
    rpr._deliver_native_review(42, "CHANGES_REQUESTED", "b", {})
    review = [c for c in calls if c[:3] == ["gh", "pr", "review"]]
    assert len(review) == 1 and "--request-changes" in review[0]


def test_deliver_native_review_self_approval_skips(rpr, monkeypatch) -> None:
    # Reviewer identity == PR author → GitHub blocks self-approval → skip native.
    fake, calls = _fake_gh(author="alice", me="alice")
    monkeypatch.setattr(rpr, "gh_run", fake)
    rpr._deliver_native_review(42, "APPROVED", "b", {})
    assert not [c for c in calls if c[:3] == ["gh", "pr", "review"]]


def test_deliver_native_review_failure_degrades(rpr, monkeypatch, capsys) -> None:
    def fake(argv, config, check=False):
        if argv[:3] == ["gh", "pr", "view"]:
            return _Proc(0, _json.dumps({"author": {"login": "alice"}}))
        if argv[:2] == ["gh", "api"]:
            return _Proc(0, "bob\n")
        return _Proc(1, "", "permission denied")  # the review post fails

    monkeypatch.setattr(rpr, "gh_run", fake)
    rpr._deliver_native_review(42, "APPROVED", "b", {})  # must not raise
    assert "could not post native review" in capsys.readouterr().err


def test_gh_pr_author_and_current_login(rpr, monkeypatch) -> None:
    fake, _ = _fake_gh(author="alice", me="bob")
    monkeypatch.setattr(rpr, "gh_run", fake)
    assert rpr._gh_pr_author(42, {}) == "alice"
    assert rpr._gh_current_login({}) == "bob"


# ---- per-agent reviewer effort (issue #1046) ---------------------
#
# Precedence: --effort flag > PKIT_REVIEW_AGENT_EFFORT env var >
# review.agents.effort in the project config > None (nothing passed; the
# harness default applies). One uniform value for every reviewer.


def _config_with_effort(level: str | None) -> dict:
    agents: dict = {"local_registered": [{"name": "pm-reviewer"}]}
    if level is not None:
        agents["effort"] = level
    return {"review": {"mode": "agent", "agents": agents}}


def test_effort_unset_everywhere_is_none(rpr) -> None:
    assert rpr._resolve_agent_effort(None, {}, {}) == (None, None)
    assert rpr._resolve_agent_effort(None, {}, _config_with_effort(None)) == (None, None)


def test_effort_config_sets_the_level_and_names_its_source(rpr) -> None:
    resolved = rpr._resolve_agent_effort(None, {}, _config_with_effort("medium"))
    assert resolved == ("medium", "review.agents.effort")


def test_effort_env_overrides_config(rpr) -> None:
    env = {rpr.AGENT_EFFORT_ENV: "high"}
    resolved = rpr._resolve_agent_effort(None, env, _config_with_effort("medium"))
    assert resolved == ("high", f"${rpr.AGENT_EFFORT_ENV}")


def test_effort_flag_overrides_env_and_config(rpr) -> None:
    env = {rpr.AGENT_EFFORT_ENV: "high"}
    resolved = rpr._resolve_agent_effort("low", env, _config_with_effort("medium"))
    assert resolved == ("low", "--effort")


def test_effort_empty_values_are_treated_as_absent(rpr) -> None:
    env = {rpr.AGENT_EFFORT_ENV: ""}
    assert rpr._resolve_agent_effort("", env, _config_with_effort("")) == (None, None)
    assert rpr._resolve_agent_effort("", env, _config_with_effort("xhigh"))[0] == "xhigh"


@pytest.mark.parametrize("bad", [0, False, 3, ["medium"]])
def test_effort_non_string_config_values_all_error(rpr, bad) -> None:
    """A falsy non-string is as wrong as a truthy one; only absence and '' are absent."""
    with pytest.raises(ValueError) as exc:
        rpr._resolve_agent_effort(None, {}, _config_with_effort(bad))
    assert "review.agents.effort" in str(exc.value)


@pytest.mark.parametrize("bad", ["extreme", "MEDIUM", "2", " high"])
def test_effort_invalid_flag_errors_and_names_the_flag(rpr, bad) -> None:
    with pytest.raises(ValueError) as exc:
        rpr._resolve_agent_effort(bad, {}, {})
    assert "--effort" in str(exc.value)
    assert "low, medium, high, xhigh, max" in str(exc.value)


def test_effort_invalid_env_errors_and_names_env(rpr) -> None:
    with pytest.raises(ValueError) as exc:
        rpr._resolve_agent_effort(None, {rpr.AGENT_EFFORT_ENV: "nope"}, {})
    assert rpr.AGENT_EFFORT_ENV in str(exc.value)


def test_effort_invalid_config_errors_and_names_the_key(rpr) -> None:
    with pytest.raises(ValueError) as exc:
        rpr._resolve_agent_effort(None, {}, _config_with_effort("turbo"))
    assert "review.agents.effort" in str(exc.value)


def _capture_invocation(rpr, monkeypatch) -> dict:
    import subprocess

    captured: dict = {}
    monkeypatch.setattr(rpr.shutil, "which", lambda _bin: "/usr/bin/claude")

    def fake_run(args, **kwargs):
        captured["args"] = list(args)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="Reviewer agent (local, reviewer): APPROVED\n",
            stderr="",
        )

    monkeypatch.setattr(rpr.subprocess, "run", fake_run)
    return captured


def test_invoke_agent_passes_effort_to_the_harness(rpr, monkeypatch) -> None:
    captured = _capture_invocation(rpr, monkeypatch)
    rpr._invoke_agent("reviewer", 99, {}, 720, effort="medium")
    args = captured["args"]
    assert args[-2:] == ["--effort", "medium"]
    assert args[:2] == ["/usr/bin/claude", "-p"]
    assert args[-4:-2] == ["--agent", "reviewer"]


def test_invoke_agent_passes_no_effort_when_unset(rpr, monkeypatch) -> None:
    captured = _capture_invocation(rpr, monkeypatch)
    rpr._invoke_agent("reviewer", 99, {}, 720)
    assert "--effort" not in captured["args"]
    assert captured["args"][-2:] == ["--agent", "reviewer"]
