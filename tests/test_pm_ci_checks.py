"""Tests for the shared CI-status gate (`_lib/ci_checks.py`, #498).

The gate reduces a PR's `statusCheckRollup` to a pass/refuse verdict, mirroring
`src/project_kit/release.py`'s #475 release-merge logic in the pm layer. Pure —
no I/O, no network: the reading of the checks a base branch requires (#1965)
runs on a fake `gh`.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "ci_checks.py"
)


@pytest.fixture(scope="module")
def ci():
    spec = importlib.util.spec_from_file_location("pm_ci_checks_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_ci_checks_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --- summarize_checks (mirror of release.summarize_checks) ------------


def test_summarize_all_green(ci) -> None:
    rollup = [
        {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"},
        {"name": "skipped-job", "status": "COMPLETED", "conclusion": "SKIPPED"},
        {"name": "neutral-job", "status": "COMPLETED", "conclusion": "NEUTRAL"},
        {"context": "legacy-status", "state": "SUCCESS"},
    ]
    passing, failing = ci.summarize_checks(rollup)
    assert passing is True
    assert failing == ()


def test_summarize_flags_failure_and_pending(ci) -> None:
    rollup = [
        {"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"},
        {"name": "build", "status": "IN_PROGRESS", "conclusion": ""},
        {"context": "legacy", "state": "PENDING"},
        {"name": "ok", "status": "COMPLETED", "conclusion": "SUCCESS"},
    ]
    passing, failing = ci.summarize_checks(rollup)
    assert passing is False
    assert failing == ("tests (FAILURE)", "build (IN_PROGRESS)", "legacy (PENDING)")


def test_summarize_empty_rollup_passes(ci) -> None:
    assert ci.summarize_checks([]) == (True, ())
    assert ci.summarize_checks(None) == (True, ())


# --- stale-run dedupe (#504): latest run per check wins --------------
# Mirrors tests/test_release_merge.py's dedupe cases — same shared fixture
# shape, kept in lockstep with the core reducer.


def test_summarize_latest_success_beats_stale_failure(ci) -> None:
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "startedAt": "2026-06-01T16:30:00Z",
            "completedAt": "2026-06-01T16:34:00Z",
        },
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "startedAt": "2026-06-01T16:35:00Z",
            "completedAt": "2026-06-01T16:39:00Z",
        },
    ]
    assert ci.summarize_checks(rollup) == (True, ())


def test_summarize_latest_failure_beats_stale_success(ci) -> None:
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "completedAt": "2026-06-01T16:30:00Z",
        },
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:39:00Z",
        },
    ]
    assert ci.summarize_checks(rollup) == (False, ("checks (FAILURE)",))


def test_summarize_single_genuine_failure_still_blocks(ci) -> None:
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:39:00Z",
        },
    ]
    assert ci.summarize_checks(rollup) == (False, ("checks (FAILURE)",))


def test_summarize_latest_pending_blocks(ci) -> None:
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "completedAt": "2026-06-01T16:30:00Z",
        },
        {
            "name": "checks",
            "status": "IN_PROGRESS",
            "conclusion": "",
            "startedAt": "2026-06-01T16:40:00Z",
        },
    ]
    assert ci.summarize_checks(rollup) == (False, ("checks (IN_PROGRESS)",))


def test_summarize_distinct_checks_dedupe_independently(ci) -> None:
    rollup = [
        {
            "name": "lint",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:30:00Z",
        },
        {
            "name": "lint",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "completedAt": "2026-06-01T16:39:00Z",
        },
        {
            "name": "tests",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "completedAt": "2026-06-01T16:31:00Z",
        },
        {
            "name": "tests",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:40:00Z",
        },
    ]
    assert ci.summarize_checks(rollup) == (False, ("tests (FAILURE)",))


def test_summarize_statuscontext_dedupes_on_createdat(ci) -> None:
    rollup = [
        {"context": "legacy", "state": "FAILURE", "createdAt": "2026-06-01T16:30:00Z"},
        {"context": "legacy", "state": "SUCCESS", "createdAt": "2026-06-01T16:39:00Z"},
    ]
    assert ci.summarize_checks(rollup) == (True, ())


def test_summarize_untimed_ties_prefer_last_listed(ci) -> None:
    rollup = [
        {"name": "checks", "status": "COMPLETED", "conclusion": "FAILURE"},
        {"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS"},
    ]
    assert ci.summarize_checks(rollup) == (True, ())


# --- evaluate_ci_gate --------------------------------------------------


def test_gate_passes_on_green(ci) -> None:
    result = ci.evaluate_ci_gate(
        [{"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS"}]
    )
    assert result.passing is True
    assert result.failing_checks == ()


def test_gate_refuses_on_failing_check(ci) -> None:
    result = ci.evaluate_ci_gate(
        [{"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}]
    )
    assert result.passing is False
    assert result.failing_checks == ("tests (FAILURE)",)


def test_gate_refuses_on_pending_check(ci) -> None:
    result = ci.evaluate_ci_gate([{"name": "build", "status": "IN_PROGRESS", "conclusion": ""}])
    assert result.passing is False
    assert result.failing_checks == ("build (IN_PROGRESS)",)


def test_gate_passes_on_empty(ci) -> None:
    assert ci.evaluate_ci_gate(None).passing is True
    assert ci.evaluate_ci_gate([]).passing is True


# --- the four states a waiting reader tells apart (#1203) --------------
# The merge gate passes a head with no check reported; `land-work`, which waits for
# the checks, must not read that as green. The gate's verdict says which.


@pytest.mark.parametrize("rollup", [None, []])
def test_no_check_reported_is_no_run_not_passed(ci, rollup) -> None:
    result = ci.evaluate_ci_gate(rollup)
    assert result.passing is True  # the merge gate's reading is unchanged
    assert result.no_checks is True
    assert result.state == ci.NO_RUN


def test_green_checks_are_passed(ci) -> None:
    result = ci.evaluate_ci_gate(
        [
            {"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "docs", "status": "COMPLETED", "conclusion": "SKIPPED"},
        ]
    )
    assert result.no_checks is False
    assert result.state == ci.PASSED
    assert result.failed == ()
    assert result.running == ()


def test_running_checks_are_running(ci) -> None:
    result = ci.evaluate_ci_gate(
        [
            {"name": "checks", "status": "IN_PROGRESS", "conclusion": ""},
            {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"context": "legacy", "state": "PENDING"},
            {"name": "queued", "status": "QUEUED"},
            {"name": "completed-no-conclusion", "status": "COMPLETED", "conclusion": ""},
        ]
    )
    assert result.state == ci.RUNNING
    assert result.running == (
        "checks (IN_PROGRESS)",
        "legacy (PENDING)",
        "queued (QUEUED)",
        "completed-no-conclusion (PENDING)",
    )
    assert result.failed == ()


def test_a_failed_check_is_failed_with_where_to_read_it(ci) -> None:
    result = ci.evaluate_ci_gate(
        [
            {
                "name": "tests",
                "status": "COMPLETED",
                "conclusion": "FAILURE",
                "detailsUrl": "https://ci/runs/1/job/2",
            },
            {"name": "build", "status": "IN_PROGRESS"},
            {"context": "external", "state": "ERROR", "targetUrl": "https://ext/9"},
            {"name": "cancelled", "status": "COMPLETED", "conclusion": "CANCELLED"},
        ]
    )
    # A failure decides even while another check still runs.
    assert result.state == ci.FAILED
    assert result.failed == (
        ci.FailedCheck("tests", "FAILURE", "https://ci/runs/1/job/2"),
        ci.FailedCheck("external", "ERROR", "https://ext/9"),
        ci.FailedCheck("cancelled", "CANCELLED", ""),
    )
    assert result.running == ("build (IN_PROGRESS)",)
    # The merge gate still lists every check that did not pass, in order.
    assert result.failing_checks == (
        "tests (FAILURE)",
        "build (IN_PROGRESS)",
        "external (ERROR)",
        "cancelled (CANCELLED)",
    )


def test_an_unknown_outcome_waits_rather_than_fails(ci) -> None:
    result = ci.evaluate_ci_gate([{"name": "new", "status": "SOMETHING_NEW"}])
    assert result.state == ci.RUNNING
    assert result.running == ("new (SOMETHING_NEW)",)


def test_the_states_read_the_latest_run_per_check(ci) -> None:
    """A check that failed and was re-run is judged on its re-run."""
    rollup = [
        {
            "name": "checks",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
            "completedAt": "2026-06-01T16:34:00Z",
        },
        {"name": "checks", "status": "IN_PROGRESS", "startedAt": "2026-06-01T16:35:00Z"},
    ]
    result = ci.evaluate_ci_gate(rollup)
    assert result.state == ci.RUNNING
    assert result.failed == ()


# --- the checks the base branch requires (#1965) ----------------------
# GitHub answers an empty rollup for a head no check reported on: in a project
# that runs none, and for a head just pushed, before its checks started. The
# merge gate passes it only where the base branch requires no check.


def test_an_empty_rollup_passes_where_the_base_requires_no_check(ci) -> None:
    result = ci.evaluate_ci_gate([], required=ci.RequiredChecks("main"))
    assert result.passing is True
    assert result.no_checks is True
    assert result.state == ci.NO_RUN
    assert result.cause == ""


def test_an_empty_rollup_is_pending_where_the_base_requires_checks(ci) -> None:
    result = ci.evaluate_ci_gate([], required=ci.RequiredChecks("main", ("checks", "docs")))
    assert result.passing is False
    assert result.failing_checks == ("checks (EXPECTED)", "docs (EXPECTED)")
    assert result.running == ("checks (EXPECTED)", "docs (EXPECTED)")
    assert result.failed == ()
    assert result.state == ci.NO_RUN
    assert result.cause == (
        "no check has been reported on the PR's head, and main requires checks: "
        "they have not started yet, or will not start"
    )


def test_an_empty_rollup_is_pending_where_the_required_checks_cannot_be_read(ci) -> None:
    required = ci.RequiredChecks("main", problem="HTTP 403: Forbidden")
    result = ci.evaluate_ci_gate([], required=required)
    assert result.passing is False
    # The label carries the cause, so a bypass audit that names it keeps it.
    assert result.failing_checks == ("none reported (required checks unread: HTTP 403: Forbidden)",)
    assert result.failed == ()
    assert result.state == ci.NO_RUN
    assert result.cause == (
        "no check has been reported on the PR's head, and the checks main requires "
        "could not be read (HTTP 403: Forbidden), so the gate cannot tell that it "
        "requires none"
    )


def test_a_rollup_with_checks_is_judged_on_them_alone(ci) -> None:
    """The base's requirement decides only an empty rollup."""
    green = [{"name": "checks", "status": "COMPLETED", "conclusion": "SUCCESS"}]
    required = ci.RequiredChecks("main", ("checks", "docs"))
    result = ci.evaluate_ci_gate(green, required=required)
    assert (result.passing, result.cause) == (True, "")


def _gh(answers):
    """A `gh` runner answering each call from *answers*, keyed by the endpoint,
    and recording what it was asked."""
    asked = []

    def run(args, config, **kwargs):
        asked.append((args, config, kwargs))
        answer = answers[args[-1]]
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, tuple):
            return subprocess.CompletedProcess(args, answer[0], "", answer[1])
        return subprocess.CompletedProcess(args, 0, answer, "")

    return run, asked


_BRANCH = "repos/{owner}/{repo}/branches/main"
_RULES = "repos/{owner}/{repo}/rules/branches/main"
_UNPROTECTED = json.dumps(
    {
        "protected": False,
        "protection": {
            "enabled": False,
            "required_status_checks": {"enforcement_level": "off", "contexts": [], "checks": []},
        },
    }
)


def _rule(*contexts):
    return {
        "type": "required_status_checks",
        "parameters": {"required_status_checks": [{"context": c} for c in contexts]},
    }


def test_a_branch_nothing_protects_requires_no_check(ci) -> None:
    run, asked = _gh({_BRANCH: _UNPROTECTED, _RULES: "[]"})
    assert ci.read_required_checks("main", {"gh": {}}, run) == ci.RequiredChecks("main")
    assert [args for args, _, _ in asked] == [
        ["gh", "api", _BRANCH],
        ["gh", "api", "--paginate", _RULES],
    ]
    assert all(config == {"gh": {}} and kw == {"check": False} for _, config, kw in asked)


def test_the_required_checks_are_read_from_protection_and_rulesets(ci) -> None:
    branch = {
        "protected": True,
        "protection": {
            "enabled": True,
            "required_status_checks": {
                "enforcement_level": "non_admins",
                "contexts": ["checks", "lint"],
                "checks": [{"context": "lint", "app_id": 15368}],
            },
        },
    }
    rules = [{"type": "deletion"}, _rule("checks", "docs")]
    run, _ = _gh({_BRANCH: json.dumps(branch), _RULES: json.dumps(rules)})
    reading = ci.read_required_checks("main", {}, run)
    assert reading == ci.RequiredChecks("main", ("checks", "lint", "docs"))


def test_protection_that_enforces_no_check_requires_none(ci) -> None:
    branch = {
        "protected": True,
        "protection": {
            "enabled": True,
            "required_status_checks": {"enforcement_level": "off", "contexts": ["old"]},
        },
    }
    run, _ = _gh({_BRANCH: json.dumps(branch), _RULES: "[]"})
    assert ci.read_required_checks("main", {}, run) == ci.RequiredChecks("main")


def test_protection_not_enabled_that_states_no_requirement_requires_none(ci) -> None:
    run, _ = _gh(
        {_BRANCH: json.dumps({"protected": True, "protection": {"enabled": False}}), _RULES: "[]"}
    )
    assert ci.read_required_checks("main", {}, run) == ci.RequiredChecks("main")


def test_rules_that_require_workflows_or_code_scanning_require_checks(ci) -> None:
    """A workflow a ruleset requires, and a code scanning tool, report as checks
    the merge waits for, so each counts as a check the base requires."""
    rules = [
        {
            "type": "workflows",
            "parameters": {"workflows": [{"path": ".github/workflows/ci.yml", "repository_id": 1}]},
        },
        {
            "type": "code_scanning",
            "parameters": {
                "code_scanning_tools": [{"tool": "CodeQL", "alerts_threshold": "errors"}]
            },
        },
    ]
    run, _ = _gh({_BRANCH: _UNPROTECTED, _RULES: json.dumps(rules)})
    reading = ci.read_required_checks("main", {}, run)
    assert reading == ci.RequiredChecks("main", (".github/workflows/ci.yml", "CodeQL"))


def test_every_page_of_the_rules_is_read(ci) -> None:
    pages = json.dumps([_rule("a")]) + json.dumps([_rule("b")])
    run, _ = _gh({_BRANCH: _UNPROTECTED, _RULES: pages})
    assert ci.read_required_checks("main", {}, run).names == ("a", "b")


def test_a_branch_name_is_one_segment_of_the_endpoint(ci) -> None:
    endpoint = "repos/{owner}/{repo}/branches/release%2F1.0%3F"
    rules = "repos/{owner}/{repo}/rules/branches/release%2F1.0%3F"
    run, asked = _gh({endpoint: _UNPROTECTED, rules: "[]"})
    assert ci.read_required_checks("release/1.0?", {}, run).problem == ""
    assert [args[-1] for args, _, _ in asked] == [endpoint, rules]


_NO_PROTECTION = "GitHub's answer for main carries no protection"
_NO_RULES = "GitHub's rules for main are not a list of rules"


@pytest.mark.parametrize(
    ("answers", "problem"),
    [
        ({_BRANCH: (1, "HTTP 403: Forbidden\n"), _RULES: "[]"}, "HTTP 403: Forbidden"),
        ({_BRANCH: _UNPROTECTED, _RULES: (1, "")}, "gh exited 1"),
        ({_BRANCH: FileNotFoundError("gh"), _RULES: "[]"}, "`gh` could not be run (gh)"),
        ({_BRANCH: "<html>", _RULES: "[]"}, "GitHub's answer for main is not JSON"),
        ({_BRANCH: _UNPROTECTED, _RULES: "[] <html>"}, "GitHub's rules for main are not JSON"),
        ({_BRANCH: _UNPROTECTED, _RULES: ""}, "GitHub's rules for main are not JSON"),
        ({_BRANCH: "[]", _RULES: "[]"}, _NO_PROTECTION),
        ({_BRANCH: json.dumps({"protected": True}), _RULES: "[]"}, _NO_PROTECTION),
        (
            {
                _BRANCH: json.dumps(
                    {"protected": True, "protection": {"required_status_checks": {"contexts": "x"}}}
                ),
                _RULES: "[]",
            },
            _NO_PROTECTION,
        ),
        # Enabled protection that states no requirement, a null one, and a
        # level that enforces with no list of checks are no answer either.
        (
            {
                _BRANCH: json.dumps({"protected": True, "protection": {"enabled": True}}),
                _RULES: "[]",
            },
            _NO_PROTECTION,
        ),
        (
            {
                _BRANCH: json.dumps(
                    {"protected": True, "protection": {"required_status_checks": None}}
                ),
                _RULES: "[]",
            },
            _NO_PROTECTION,
        ),
        (
            {
                _BRANCH: json.dumps(
                    {
                        "protected": True,
                        "protection": {
                            "enabled": True,
                            "required_status_checks": {"enforcement_level": "non_admins"},
                        },
                    }
                ),
                _RULES: "[]",
            },
            _NO_PROTECTION,
        ),
        ({_BRANCH: _UNPROTECTED, _RULES: "{}"}, _NO_RULES),
        (
            {_BRANCH: _UNPROTECTED, _RULES: json.dumps([{"type": "required_status_checks"}])},
            _NO_RULES,
        ),
        (
            {_BRANCH: _UNPROTECTED, _RULES: json.dumps([{"type": "workflows", "parameters": {}}])},
            _NO_RULES,
        ),
    ],
)
def test_required_checks_that_cannot_be_read_name_why(ci, answers, problem) -> None:
    """No answer is never an answer of none: the reading names why."""
    run, _ = _gh(answers)
    reading = ci.read_required_checks("main", {}, run)
    assert (reading.names, reading.problem) == ((), problem)


def test_a_base_branch_not_known_is_no_answer(ci) -> None:
    run, asked = _gh({})
    reading = ci.read_required_checks("", {}, run)
    assert reading.problem == "the PR's base branch is not known"
    assert asked == []
