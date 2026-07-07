"""Tests for the shared CI-status gate (`_lib/ci_checks.py`, #498).

The gate reduces a PR's `statusCheckRollup` to a pass/refuse verdict, mirroring
`src/project_kit/release.py`'s #475 release-merge logic in the pm layer. Pure —
no I/O, no network.
"""

from __future__ import annotations

import importlib.util
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
    result = ci.evaluate_ci_gate(
        [{"name": "build", "status": "IN_PROGRESS", "conclusion": ""}]
    )
    assert result.passing is False
    assert result.failing_checks == ("build (IN_PROGRESS)",)


def test_gate_passes_on_empty(ci) -> None:
    assert ci.evaluate_ci_gate(None).passing is True
    assert ci.evaluate_ci_gate([]).passing is True
