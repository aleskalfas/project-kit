"""`.github/workflows/checks.yml` under the merge queue (#1011).

The status `main` requires is the `checks` job. Where `main` merges through a
queue, the queue waits for that status on the merge it is about to make, so the
workflow must run on the queue's `merge_group` event as well as on pull
requests and pushes, and the diff-scoped checks inside it must read the base
that merge is built on. The changeset guard, which needs the pull request's
labels, stays on pull requests. The whole-repository friction report gates
nothing and is a workflow of its own (`test_friction_tracking_issue.py`).

The short check (#1798, ADR-067): a step decides, before the aggregator, whether
the run is full or short, and cannot fail the job. On a pull request the base's
decider decides, checked out beside the tree and run against it; a base with
none leaves the run full, and answers `full`; on any other event this tree's
decider only says why the run is full. Its shell runs here for real, against a
stub `uv`. The two forms exclude each other, the run is full unless the step
named the short check, and only a pull request runs the short one, by the
workflow's own gate. Where the deciding step gave no answer, as when it failed
before the decider started, the full run's step says in the job's summary that
the run is full; its shell runs here too, against a stub aggregator.
Their steps' names are the marks `scripts/short_check.py` reads on earlier runs.
The job may only read. The checkout keeps the token out of the clone, and of the
steps that run the project's code, only the deciding step holds it.
`test_short_check.py` holds the decision.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML
from scripts import short_check

from tests.adopter_repo import sign_nothing

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


# --- the short check (#1798, ADR-067) -------------------------------------------------


def _steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return workflow["jobs"]["checks"]["steps"]


def _decider(workflow: dict[str, Any]) -> dict[str, Any]:
    return next(step for step in _steps(workflow) if step.get("id") == "form")


def test_the_deciding_step_comes_before_both_forms_and_fails_nothing(workflow) -> None:
    """The deciding step runs after the sync, on every event, and cannot fail the job."""
    steps = _steps(workflow)
    names = [str(step.get("name", "")) for step in steps]
    decide = _decider(workflow)
    assert decide["continue-on-error"] is True
    assert "if" not in decide
    position = steps.index(decide)
    assert names.index("Sync (provisions the query commands)") < position
    assert position < names.index(short_check.FULL_STEP)
    assert position < names.index(short_check.SHORT_STEP)


def test_the_two_forms_exclude_each_other_and_only_a_pull_request_runs_the_short_one(
    workflow,
) -> None:
    """The event gate is the workflow's, outside the decider: a decider that said
    `short` on a push to `main` or a queued merge would still leave the run full."""
    full = _step(workflow["jobs"]["checks"], short_check.FULL_STEP)
    short = _step(workflow["jobs"]["checks"], short_check.SHORT_STEP)
    # The names are the mark the deciding step reads on earlier runs.
    assert full["name"] == short_check.FULL_STEP
    assert short["name"] == short_check.SHORT_STEP
    assert full["if"] == (
        "github.event_name != 'pull_request' || steps.form.outputs.mode != 'short'"
    )
    assert short["if"] == (
        "github.event_name == 'pull_request' && steps.form.outputs.mode == 'short'"
    )
    assert full["run"].splitlines()[-1] == "./scripts/check.sh"
    assert short["run"] == "./scripts/check.sh --short"
    form = {"PKIT_FORM_MODE", "PKIT_FORM_OUTCOME"}
    assert {k: v for k, v in full["env"].items() if k not in form} == short["env"]


# The deciding step's shell, run for real against a stub `uv` that logs what it ran
# and where, over a clone whose `origin/main` holds a decider or not.
STUB_UV = '#!/bin/sh\necho "$PWD|$*" >> "$STUB_LOG"\n'


class Decider:
    """A clone of an `origin` whose `main` holds the decider or not, and the step's
    environment."""

    def __init__(self, root: Path, *, base_has_decider: bool) -> None:
        origin = root / "origin"
        (origin / "scripts").mkdir(parents=True)
        if base_has_decider:
            (origin / "scripts" / "short_check.py").write_text("# the base's\n")
        else:
            (origin / "scripts" / "check.sh").write_text("# no decider yet\n")
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(["git", "init", "-q", "-b", "main", str(origin)], check=True)
        sign_nothing(origin)
        subprocess.run([*git, "-C", str(origin), "add", "-A"], check=True)
        subprocess.run([*git, "-C", str(origin), "commit", "-q", "-m", "base"], check=True)
        self.checkout = root / "checkout"
        subprocess.run(["git", "clone", "-q", str(origin), str(self.checkout)], check=True)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        (bin_dir / "uv").write_text(STUB_UV)
        (bin_dir / "uv").chmod(0o755)
        self.log = root / "uv.log"
        self.summary = root / "summary"
        self.summary.touch()
        self.output = root / "output"
        self.output.touch()
        self.temp = root / "runner-temp"
        self.temp.mkdir()
        self.env = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(root),
            "STUB_LOG": str(self.log),
            "RUNNER_TEMP": str(self.temp),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "GITHUB_OUTPUT": str(self.output),
            "PKIT_DECIDER_BASE": "main",
        }

    def run(self, script: str, event: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-e", "-c", script],
            cwd=self.checkout,
            env={**self.env, "GITHUB_EVENT_NAME": event},
            capture_output=True,
            text=True,
            check=False,
        )

    def ran(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []


def test_on_a_pull_request_the_base_s_decider_decides_against_this_tree(
    workflow, tmp_path: Path
) -> None:
    decider = Decider(tmp_path, base_has_decider=True)

    done = decider.run(_decider(workflow)["run"], "pull_request")

    assert done.returncode == 0, done.stderr
    copy = decider.temp / "decider"
    assert (copy / "scripts" / "short_check.py").read_text() == "# the base's\n"
    assert decider.ran() == [
        f"{decider.checkout}|run --project {copy} --frozen python {copy}/scripts/short_check.py"
    ]


def test_a_base_with_no_decider_leaves_the_run_full_and_says_so(workflow, tmp_path: Path) -> None:
    decider = Decider(tmp_path, base_has_decider=False)

    done = decider.run(_decider(workflow)["run"], "pull_request")

    assert done.returncode == 0, done.stderr
    assert decider.ran() == []
    assert "the full run" in decider.summary.read_text()
    assert "no decider" in decider.summary.read_text()
    # An answer, so the full run's step adds no second section to the summary.
    assert decider.output.read_text() == "mode=full\n"


@pytest.mark.parametrize("event", ["push", "merge_group"])
def test_on_any_other_event_this_tree_s_decider_only_says_why_the_run_is_full(
    workflow, tmp_path: Path, event: str
) -> None:
    decider = Decider(tmp_path, base_has_decider=True)

    done = decider.run(_decider(workflow)["run"], event)

    assert done.returncode == 0, done.stderr
    assert decider.ran() == [f"{decider.checkout}|run python scripts/short_check.py"]
    assert not (decider.temp / "decider").exists()


def test_a_base_that_cannot_be_checked_out_fails_the_step_and_decides_nothing(
    workflow, tmp_path: Path
) -> None:
    decider = Decider(tmp_path, base_has_decider=True)
    decider.env["PKIT_DECIDER_BASE"] = "no-such-branch"

    done = decider.run(_decider(workflow)["run"], "pull_request")

    assert done.returncode != 0
    assert decider.ran() == []


# The full run's step's shell, run for real over a stub aggregator that logs that it
# ran and exits with the status it is given.
STUB_CHECK = '#!/bin/sh\necho ran >> "$STUB_LOG"\nexit "${STUB_STATUS:-0}"\n'


def _full_run(
    workflow: dict[str, Any], root: Path, mode: str, outcome: str, status: str = "0"
) -> tuple[subprocess.CompletedProcess[str], str, list[str]]:
    """Run the full run's step's shell as GitHub would, with the deciding step's answer
    `mode` and its outcome; return the result, the job's summary and what ran."""
    (root / "scripts").mkdir()
    (root / "scripts" / "check.sh").write_text(STUB_CHECK)
    (root / "scripts" / "check.sh").chmod(0o755)
    summary, log = root / "summary", root / "check.log"
    summary.touch()
    done = subprocess.run(
        [
            "bash",
            "-e",
            "-o",
            "pipefail",
            "-c",
            _step(workflow["jobs"]["checks"], short_check.FULL_STEP)["run"],
        ],
        cwd=root,
        env={
            "PATH": os.environ["PATH"],
            "GITHUB_STEP_SUMMARY": str(summary),
            "STUB_LOG": str(log),
            "STUB_STATUS": status,
            "PKIT_FORM_MODE": mode,
            "PKIT_FORM_OUTCOME": outcome,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    ran = log.read_text().splitlines() if log.exists() else []
    return done, summary.read_text(), ran


def test_the_full_run_says_which_form_ran_where_the_deciding_step_gave_no_answer(
    workflow, tmp_path: Path
) -> None:
    """The deciding step failed before the decider started, as where the base cannot be
    checked out or `uv` cannot build its environment: nothing else says which form ran."""
    full = _step(workflow["jobs"]["checks"], short_check.FULL_STEP)
    assert full["env"]["PKIT_FORM_MODE"] == "${{ steps.form.outputs.mode }}"
    assert full["env"]["PKIT_FORM_OUTCOME"] == "${{ steps.form.outcome }}"

    done, summary, ran = _full_run(workflow, tmp_path, mode="", outcome="failure")

    assert done.returncode == 0, done.stderr
    assert ran == ["ran"]
    assert summary.startswith("### `checks`: the full run\n")
    assert "gave no answer (it ended in `failure`)" in summary
    assert "ADR-067" in summary


def test_the_full_run_adds_nothing_to_the_summary_where_the_deciding_step_answered(
    workflow, tmp_path: Path
) -> None:
    done, summary, ran = _full_run(workflow, tmp_path, mode="full", outcome="success")

    assert done.returncode == 0, done.stderr
    assert ran == ["ran"]
    assert summary == ""


def test_the_full_run_fails_as_its_aggregator_does_after_the_fallback_line(
    workflow, tmp_path: Path
) -> None:
    done, summary, ran = _full_run(workflow, tmp_path, mode="", outcome="failure", status="1")

    assert done.returncode == 1
    assert ran == ["ran"]
    assert "the full run" in summary


def test_the_runs_read_are_this_workflow_s_and_its_required_job_s(workflow) -> None:
    assert WORKFLOW.name == short_check.WORKFLOW_FILE
    assert f".github/workflows/{WORKFLOW.name}" == short_check.WORKFLOW_PATH
    assert list(workflow["jobs"]) == [short_check.JOB]
    assert "name" not in workflow["jobs"]["checks"]


def test_the_job_only_reads_and_of_the_project_s_code_only_the_decider_holds_the_token(
    workflow,
) -> None:
    """The checkout keeps the token out of the clone's configuration, so no later step
    reads it there, and only the deciding step is handed it."""
    job = workflow["jobs"]["checks"]
    assert job["permissions"] == {"contents": "read", "actions": "read", "pull-requests": "read"}
    checkout = _step(job, "Checkout")
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"]["persist-credentials"] is False
    holders = [
        step.get("id") or step.get("name")
        for step in job["steps"]
        if any("github.token" in str(value) for value in (step.get("env") or {}).values())
    ]
    assert holders == ["form"]
    assert "env" not in workflow
    assert "env" not in job


def test_the_steps_of_the_two_forms_put_no_expression_in_a_shell_line(workflow) -> None:
    """A value in a `run:` line would be run as shell: the deciding step reads the
    base's name from its environment, and the decider the event GitHub wrote."""
    job = workflow["jobs"]["checks"]
    steps = [
        _decider(workflow),
        _step(job, short_check.FULL_STEP),
        _step(job, short_check.SHORT_STEP),
    ]
    for step in steps:
        assert "${{" not in str(step["run"]), step.get("name")
    assert _decider(workflow)["env"]["PKIT_DECIDER_BASE"] == (
        "${{ github.event.pull_request.base.ref }}"
    )
