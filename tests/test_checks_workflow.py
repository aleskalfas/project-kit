"""`.github/workflows/checks.yml` under the merge queue (#1011).

The status `main` requires is the `checks` job. Where `main` merges through a
queue, the queue waits for that status on the merge it is about to make, so the
workflow must run on the queue's `merge_group` event as well as on pull
requests and pushes, and the diff-scoped checks inside it must read the base
that merge is built on. The changeset guard, which needs the pull request's
labels, stays on pull requests. The whole-repository friction report gates
nothing and is a workflow of its own (`test_friction_tracking_issue.py`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "checks.yml"


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    # YAML 1.2, so the `on:` key stays the string "on".
    return YAML(typ="safe").load(WORKFLOW.read_text(encoding="utf-8"))


def _step(job: dict[str, Any], name_prefix: str) -> dict[str, Any]:
    return next(s for s in job["steps"] if str(s.get("name", "")).startswith(name_prefix))


def test_checks_run_on_the_merge_the_queue_is_about_to_make(workflow) -> None:
    triggers = workflow["on"]
    assert triggers["merge_group"] == {"types": ["checks_requested"]}
    assert triggers["pull_request"]["branches"] == ["main"]
    assert triggers["push"]["branches"] == ["main"]


def test_the_required_job_runs_on_every_trigger(workflow) -> None:
    """`checks` has no event condition, so the queue gets the status it waits for."""
    assert "if" not in workflow["jobs"]["checks"]


def test_the_aggregator_compares_with_the_base_the_queued_merge_is_built_on(workflow) -> None:
    base = _step(workflow["jobs"]["checks"], "Run the check aggregator")["env"]["PKIT_CHECK_BASE"]
    # A merge group's own base first; else the pull request's base; else main.
    assert base.index("github.event.merge_group.base_sha") < base.index(
        "github.event.pull_request.base.ref"
    )
    assert "format('origin/{0}'" in base
    assert "'main'" in base


def test_the_changeset_guard_keeps_to_pull_requests(workflow) -> None:
    guard = _step(workflow["jobs"]["checks"], "Changeset guard")
    assert guard["if"] == "github.event_name == 'pull_request'"


def test_the_required_workflow_holds_no_friction_report(workflow) -> None:
    """The report gates nothing, and keeps an issue `checks` has no permission for."""
    assert list(workflow["jobs"]) == ["checks"]
    assert "permissions" not in workflow
