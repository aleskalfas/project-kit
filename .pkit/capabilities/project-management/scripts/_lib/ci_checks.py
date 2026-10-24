"""Shared CI-status gate for the pm merge paths (`merge-pr`, `done-work`).

Both merge scripts must refuse to land a PR whose GitHub checks are red or
still running (the #498 hole: a reviewer APPROVED verdict is not evidence CI
passed — PR #496 merged with a failing check). This module owns the fact-
reduction and the gate verdict so the two call sites share one definition
rather than each re-deriving it.

Two layers, mirroring `src/project_kit/release.py`'s #475 release-merge gate
(the pm scripts are a separate layer from core `src/project_kit`, so the
`summarize_checks` logic is **mirrored here**, not imported — there is no
shared seam to import across that boundary):

  * `summarize_checks(rollup)` — pure reduction of a `statusCheckRollup` to
    (all-passing, non-passing-check-labels). No I/O.
  * `evaluate_ci_gate(rollup, required=…)` — the gate verdict (`CiGateResult`):
    pass, or refuse naming the offending checks. The verdict also tells apart
    the four states a head's checks can be in (`CiGateResult.state`) — none
    reported yet, still running, failed, passed — for a reader that waits for
    them (`land-work`, #1203), which must not take a head with no check
    reported for green.

An empty rollup is what GitHub answers in a project that runs no checks, and
also for a head just pushed, before its checks started. The merge gate tells
the two apart by the checks the PR's base branch requires
(`read_required_checks`, #1965): it passes an empty rollup only where the base
requires none, and otherwise refuses it as a pending one, naming the cause.

The gh round-trips (`gh pr view --json statusCheckRollup`, and the two reads of
the base's requirements) go through the runner each script passes, so each
threads its own adopter config through the pm `gh` helper.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

# CheckRun conclusions / StatusContext states that count as "not blocking a
# merge". SKIPPED and NEUTRAL are non-failures; everything else that is not
# SUCCESS (a failure, or a still-running/pending check) blocks the merge.
# Mirrors release.py's `_CHECK_PASSING_OUTCOMES`.
_CHECK_PASSING_OUTCOMES = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"})

# The outcomes of a check that finished without passing. Every other outcome
# that does not pass — IN_PROGRESS, QUEUED, PENDING, WAITING, REQUESTED,
# EXPECTED, or one GitHub adds later — is a check still running, so a reader
# that waits for the checks waits on it rather than call it failed.
_CHECK_FAILED_OUTCOMES = frozenset(
    {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"}
)

# The states a head's checks are in (`CiGateResult.state`).
NO_RUN = "no-run"
RUNNING = "running"
FAILED = "failed"
PASSED = "passed"


@dataclass(frozen=True)
class FailedCheck:
    """A check that finished without passing, and where to read it."""

    name: str
    outcome: str
    #: A CheckRun's `detailsUrl`, a StatusContext's `targetUrl`; empty when
    #: GitHub gives none.
    url: str = ""


@dataclass(frozen=True)
class CiGateResult:
    """The CI gate's verdict on a PR's `statusCheckRollup`.

    `passing` and `failing_checks` are the merge gate's: every check passed,
    or the ones that did not, failed and still running alike. The other
    fields tell those apart for a reader that waits for the checks (`state`).
    """

    passing: bool
    failing_checks: tuple[str, ...] = field(default_factory=tuple)
    #: No check reported at all. It is what GitHub reports in a repository
    #: that runs no checks, and for a head just pushed, before any check has
    #: started. The merge gate passes it only where the base branch requires
    #: no check (#1965), and a reader that waits for the checks reads it as
    #: :data:`NO_RUN`, never as green.
    no_checks: bool = False
    #: The checks that finished without passing.
    failed: tuple[FailedCheck, ...] = field(default_factory=tuple)
    #: The checks still running, labelled as `failing_checks` labels them.
    running: tuple[str, ...] = field(default_factory=tuple)
    #: Why a rollup with no check does not pass; empty otherwise.
    cause: str = ""

    @property
    def state(self) -> str:
        """:data:`NO_RUN`; :data:`FAILED` when any check failed, others still
        running or not; :data:`RUNNING`; else :data:`PASSED`."""
        if self.no_checks:
            return NO_RUN
        if self.failed:
            return FAILED
        if self.running:
            return RUNNING
        return PASSED


@dataclass(frozen=True)
class RequiredChecks:
    """The checks a branch requires before a PR merges into it, as GitHub's
    protection and rulesets for it state them — or, in `problem`, why they
    could not be read, which is not an answer of none (#1965)."""

    branch: str
    names: tuple[str, ...] = ()
    problem: str = ""


def _check_identity(check: dict) -> str:
    """The identity a check re-runs under — `name` (CheckRun) / `context` (StatusContext)."""
    return check.get("name") or check.get("context") or "check"


def _check_timestamp(check: dict) -> str:
    """The instant a check's latest run reports, for ordering re-runs.

    A CheckRun carries `completedAt` (terminal) / `startedAt` (running); a
    StatusContext carries `createdAt`. ISO-8601 strings sort chronologically as
    plain strings, so the raw value is enough. Missing ⇒ empty string, which
    sorts first — so a timestamped run always wins over an untimed one, and ties
    (all untimed / equal) fall through to GitHub's roughly-chronological order.
    """
    return check.get("completedAt") or check.get("startedAt") or check.get("createdAt") or ""


def _check_url(check: dict) -> str:
    """Where a check's run can be read — `detailsUrl` (CheckRun) / `targetUrl`
    (StatusContext) — or "" when GitHub gives none."""
    return str(check.get("detailsUrl") or check.get("targetUrl") or "")


def _check_outcome(check: dict) -> str:
    """A check's outcome: a StatusContext's `state`; a CheckRun's `status`
    while it runs, its `conclusion` once completed (PENDING when it has none)."""
    state = str(check.get("state") or "").upper()
    status = str(check.get("status") or "").upper()
    conclusion = str(check.get("conclusion") or "").upper()
    if state:  # StatusContext
        return state
    if status and status != "COMPLETED":  # CheckRun still running/queued
        return status
    return conclusion or "PENDING"  # completed CheckRun


def dedupe_to_latest_run(rollup: list[dict]) -> list[dict]:
    """Collapse a `statusCheckRollup` to the latest run per check identity.

    GitHub retains *every* run of a check in the rollup — so a check that failed
    then re-ran green (a fix-and-repush, a label re-trigger) appears twice, and a
    naive reduction counts the stale FAILURE. This keeps only the latest run per
    identity (by timestamp; ties broken by last-listed, GitHub returning roughly
    chronological), matching how `gh pr checks` reports. Output preserves each
    identity's first-seen order so the reduced failing-check list stays stable.
    """
    latest: dict[str, dict] = {}
    for check in rollup:
        identity = _check_identity(check)
        current = latest.get(identity)
        # `>=` keeps the last-listed on a timestamp tie (chronological input).
        if current is None or _check_timestamp(check) >= _check_timestamp(current):
            latest[identity] = check
    return list(latest.values())


def summarize_checks(rollup: list[dict] | None) -> tuple[bool, tuple[str, ...]]:
    """Reduce a `statusCheckRollup` to (all-passing, non-passing-check-labels).

    Handles both node shapes GitHub returns: a CheckRun carries `status`
    (COMPLETED / IN_PROGRESS / QUEUED) + `conclusion` (SUCCESS / FAILURE / …);
    a StatusContext carries `state` (SUCCESS / FAILURE / PENDING / ERROR). A
    check passes only when its outcome is a non-failing terminal one; a
    still-running check blocks (a PR must be green before merging). An empty
    rollup (no checks configured) is treated as passing.

    The rollup is first deduped to the latest run per check identity
    (`dedupe_to_latest_run`) — GitHub keeps stale runs, so a check that failed
    then re-ran green would otherwise wrongly block the merge (#504).

    Mirrors `src/project_kit/release.py:summarize_checks` — kept in lockstep
    by intent, not by import (cross-layer boundary; see the module docstring).
    """
    failing: list[str] = []
    for check in dedupe_to_latest_run(rollup or []):
        outcome = _check_outcome(check)
        if outcome not in _CHECK_PASSING_OUTCOMES:
            failing.append(f"{_check_identity(check)} ({outcome})")
    return (not failing, tuple(failing))


def evaluate_ci_gate(
    rollup: list[dict] | None, required: RequiredChecks | None = None
) -> CiGateResult:
    """Decide whether a PR's CI status permits a merge — pure, no I/O.

    A green rollup passes; any failing or still-pending check refuses, naming
    the offending checks so the operator sees exactly what blocks. The caller
    decides how a `--bypass` overrides a refusal.

    A rollup with no check passes only where *required*, the checks the PR's
    base branch requires, are none (#1965). Where the base requires checks, it
    is refused as pending, each required check labelled `EXPECTED`, GitHub's
    word for a required check not yet reported. Where they could not be read,
    it is refused as pending too: the gate cannot tell that none is required.
    `cause` says which. A reader that only waits for the checks passes no
    *required*, and reads the rollup's state alone.

    The verdict also separates a rollup with no check at all, the checks that
    failed and those still running (`CiGateResult.state`), each read off the
    same latest run per check the gate judges.
    """
    if not rollup and required is not None and (required.names or required.problem):
        base = required.branch or "the base branch"
        if required.problem:
            # The label carries the cause, so a `--bypass-ci` audit that names
            # it records why no required check could be named.
            return CiGateResult(
                passing=False,
                failing_checks=(f"none reported (required checks unread: {required.problem})",),
                no_checks=True,
                cause=(
                    "no check has been reported on the PR's head, and the checks "
                    f"{base} requires could not be read ({required.problem}), "
                    "so the gate cannot tell that it requires none"
                ),
            )
        expected = tuple(f"{name} (EXPECTED)" for name in required.names)
        return CiGateResult(
            passing=False,
            failing_checks=expected,
            no_checks=True,
            running=expected,
            cause=(
                f"no check has been reported on the PR's head, and {base} "
                "requires checks: they have not started yet, or will not start"
            ),
        )
    passing, failing = summarize_checks(rollup)
    failed: list[FailedCheck] = []
    running: list[str] = []
    for check in dedupe_to_latest_run(rollup or []):
        outcome = _check_outcome(check)
        if outcome in _CHECK_PASSING_OUTCOMES:
            continue
        name = _check_identity(check)
        if outcome in _CHECK_FAILED_OUTCOMES:
            failed.append(FailedCheck(name, outcome, _check_url(check)))
        else:
            running.append(f"{name} ({outcome})")
    return CiGateResult(
        passing=passing,
        failing_checks=failing,
        no_checks=not rollup,
        failed=tuple(failed),
        running=tuple(running),
    )


#: Runs one `gh` command with the caller's adopter config: the pm `gh` helper.
GhRunner = Callable[..., subprocess.CompletedProcess]


def _named(entries: Any, key: str) -> list[str] | None:
    """The *key* of each entry of a list of required checks, or None when the
    list is not one."""
    if not isinstance(entries, list):
        return None
    if not all(isinstance(entry, dict) and isinstance(entry.get(key), str) for entry in entries):
        return None
    return [entry[key] for entry in entries]


def _protection_requires(answer: Any) -> list[str] | None:
    """The checks a branch's classic protection requires, from GitHub's answer
    for the branch; None when the answer does not say.

    An unprotected branch requires none, and so does protection that is not
    enabled and states no requirement, or whose `enforcement_level` is `off`.
    Any other level enforces the checks listed, by name (`contexts`) and by
    app (`checks`). Any other shape is no answer.
    """
    if not isinstance(answer, dict):
        return None
    protection = answer.get("protection")
    if protection is None:
        return [] if answer.get("protected") is False else None
    if not isinstance(protection, dict):
        return None
    status = protection.get("required_status_checks")
    if status is None:
        return [] if protection.get("enabled") is False else None
    if not isinstance(status, dict) or not isinstance(status.get("enforcement_level"), str):
        return None
    if status["enforcement_level"] == "off":
        return []
    contexts = status.get("contexts")
    checks = _named(status.get("checks", []), "context")
    if not isinstance(contexts, list) or not all(isinstance(c, str) for c in contexts):
        return None
    if checks is None:
        return None
    return [*contexts, *checks]


#: The ruleset rules that require checks to pass before a merge, each with the
#: list in its parameters that names them and the key that names each entry:
#: status checks by context, workflows by path, code scanning by tool.
_RULES_THAT_REQUIRE = {
    "required_status_checks": ("required_status_checks", "context"),
    "workflows": ("workflows", "path"),
    "code_scanning": ("code_scanning_tools", "tool"),
}


def _rules_require(rules: Any) -> list[str] | None:
    """The checks the rulesets that apply to a branch require, from GitHub's
    list of those rules; None when it is not a list of rules."""
    if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
        return None
    names: list[str] = []
    for rule in rules:
        requirement = _RULES_THAT_REQUIRE.get(rule.get("type"))
        if requirement is None:
            continue
        listed, key = requirement
        parameters = rule.get("parameters")
        named = _named(parameters.get(listed), key) if isinstance(parameters, dict) else None
        if named is None:
            return None
        names.extend(named)
    return names


def _pages(text: str) -> list[Any] | None:
    """The JSON value of each page `gh api --paginate` printed, one after
    another, or None when the output is not JSON values alone."""
    decoder = json.JSONDecoder()
    pages: list[Any] = []
    index, end = 0, len(text)
    while True:
        while index < end and text[index].isspace():
            index += 1
        if index >= end:
            return pages
        try:
            page, index = decoder.raw_decode(text, index)
        except ValueError:
            return None
        pages.append(page)


def _gh_api(args: list[str], config: dict, run: GhRunner) -> tuple[str, str]:
    """`gh api` with *args*: its output, and why there is none, else ""."""
    try:
        proc = run(args, config, check=False)
    except OSError as exc:
        return "", f"`gh` could not be run ({exc})"
    if proc.returncode != 0:
        return "", " ".join((proc.stderr or "").split()) or f"gh exited {proc.returncode}"
    return proc.stdout or "", ""


def read_required_checks(branch: str, config: dict, run: GhRunner) -> RequiredChecks:
    """Read the checks *branch* requires before a PR merges into it (#1965).

    Two sources state them: the branch's classic protection, in GitHub's
    answer for the branch, and the rulesets that apply to it, every page of
    them. *run* is the caller's pm `gh` helper, which threads its adopter
    config. The branch name is one segment of each endpoint, every character
    but a letter, a digit and `_.-~` escaped. A call that fails, or an answer
    that does not read as these, is no answer, never one of none: `problem`
    names it.
    """
    if not branch:
        return RequiredChecks(branch, problem="the PR's base branch is not known")
    segment = quote(branch, safe="")
    stdout, problem = _gh_api(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/branches/{segment}"], config, run
    )
    if problem:
        return RequiredChecks(branch, problem=problem)
    try:
        answer = json.loads(stdout)
    except ValueError:
        return RequiredChecks(branch, problem=f"GitHub's answer for {branch} is not JSON")
    protected = _protection_requires(answer)
    if protected is None:
        return RequiredChecks(branch, problem=f"GitHub's answer for {branch} carries no protection")
    stdout, problem = _gh_api(
        ["gh", "api", "--paginate", f"repos/{{owner}}/{{repo}}/rules/branches/{segment}"],
        config,
        run,
    )
    if problem:
        return RequiredChecks(branch, problem=problem)
    pages = _pages(stdout)
    if not pages:
        return RequiredChecks(branch, problem=f"GitHub's rules for {branch} are not JSON")
    ruled = (
        _rules_require([rule for page in pages for rule in page])
        if all(isinstance(page, list) for page in pages)
        else None
    )
    if ruled is None:
        return RequiredChecks(
            branch, problem=f"GitHub's rules for {branch} are not a list of rules"
        )
    return RequiredChecks(branch, tuple(dict.fromkeys([*protected, *ruled])))
