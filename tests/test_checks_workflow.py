"""`.github/workflows/checks.yml`: the required check, its parts and its verdict.

The merge queue (#1011): the status `main` requires is the `checks` job. Where
`main` merges through a queue, the queue waits for that status on the merge it is
about to make, so the workflow must run on the queue's `merge_group` event as well
as on pull requests and pushes. The changeset guard, which needs the pull request's
labels, stays on pull requests. The whole-repository friction report gates nothing
and is a workflow of its own (`test_friction_tracking_issue.py`).

The short check (#1798, ADR-067): a step decides, before any part, whether the run
is full or short, and cannot fail the run. On a pull request the base's decider
decides, checked out beside the tree and run against it; a base with none leaves
the run full, and answers `full`; on any other event this tree's decider only says
why the run is full. Its shell runs here for real, against a stub `uv`. Only a
pull request runs the short form, by the workflow's own gate.

The parts (#2308, ADR-078):

- **the deciding job** decides, pins the base and names the form, and nothing else.
  It alone may read runs and pull requests, and of the steps that run the project's
  code only its deciding step holds the token. The base it pins, and the form it
  names, run here for real on each event;
- **the remainder's job** runs `--rest` or `--short` by the form, and the changeset
  guard on a pull request; **the slices** run only in the full form. Each part
  reads the pinned base and the pull request's head, times itself, names its
  failures and says that it passed, last (`scripts/ci_parts.py run`, run here
  against a stub aggregator);
- **`checks`** runs last, whatever became of the parts, and its two steps hold the
  two forms under the names the decider reads (`scripts/short_check.py`). Its
  verdict (`scripts/ci_parts.py verdict`) runs here for each outcome of each part,
  each missing output and each output that attests another step, on each event;
- **only a new head cancels**, and a run on `main` or in the merge queue takes a
  group of its own; each job but `checks` stops after 30 minutes, `checks` after 5.

`test_short_check.py` holds the decision.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML
from scripts import ci_parts, short_check

from tests import slices
from tests.adopter_repo import sign_nothing

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "checks.yml"

#: The jobs of the workflow, the slices among them, and the parts `checks` judges.
SLICES = 2
SLICE_JOBS = [f"slice-{i}" for i in range(1, SLICES + 1)]
JOBS = ["decide", "rest", *SLICE_JOBS, "checks"]
EVENTS = ["pull_request", "merge_group", "push"]

PINNED_BASE = "${{ needs.decide.outputs.base }}"
PR_HEAD = "${{ github.event.pull_request.head.sha }}"
FULL_FORM = "github.event_name != 'pull_request' || needs.decide.outputs.form != 'short'"
SHORT_FORM = "github.event_name == 'pull_request' && needs.decide.outputs.form == 'short'"


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    # YAML 1.2, so the `on:` key stays the string "on".
    return YAML(typ="safe").load(WORKFLOW.read_text(encoding="utf-8"))


def _job(workflow: dict[str, Any], name: str) -> dict[str, Any]:
    return workflow["jobs"][name]


def _step(job: dict[str, Any], name_prefix: str) -> dict[str, Any]:
    return next(s for s in job["steps"] if str(s.get("name", "")).startswith(name_prefix))


def _by_id(job: dict[str, Any], step_id: str) -> dict[str, Any]:
    return next(s for s in job["steps"] if s.get("id") == step_id)


def _all_steps(workflow: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(name, step) for name, job in workflow["jobs"].items() for step in job["steps"]]


def _shell(script: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """A step's shell, as GitHub runs one that names no shell."""
    return subprocess.run(
        ["bash", "-e", "-c", script], cwd=cwd, env=env, capture_output=True, text=True, check=False
    )


# --- the triggers and the jobs ----------------------------------------------------------


def test_checks_run_on_the_merge_the_queue_is_about_to_make(workflow) -> None:
    triggers = workflow["on"]
    assert triggers["merge_group"] == {"types": ["checks_requested"]}
    assert triggers["pull_request"]["branches"] == ["main"]
    assert triggers["push"]["branches"] == ["main"]


def test_the_jobs_are_the_deciding_job_the_parts_and_checks(workflow) -> None:
    assert list(workflow["jobs"]) == JOBS
    for name in JOBS[1:-1]:
        assert _job(workflow, name)["needs"] == "decide", name
    assert _job(workflow, "checks")["needs"] == JOBS[:-1]


def test_the_required_job_runs_whatever_became_of_the_others(workflow) -> None:
    """GitHub counts a required check whose job was skipped as passing, so `checks` runs
    after a part failed, was skipped or cancelled, and on every event."""
    assert _job(workflow, "checks")["if"] == "always()"


def test_every_step_of_checks_runs_on_a_cancelled_run(workflow) -> None:
    """A step with no condition is skipped once the run is cancelled, so the checkout and
    the setting-up run on `always()` too, or the verdict would find no script to run and
    write no summary."""
    for step in _job(workflow, "checks")["steps"]:
        assert str(step.get("if", "")).startswith("always()"), step.get("name")


def test_the_runs_read_are_this_workflow_s_and_one_job_is_named_checks(workflow) -> None:
    """The decider reads the job named `checks`: no other job takes the name."""
    assert WORKFLOW.name == short_check.WORKFLOW_FILE
    assert f".github/workflows/{WORKFLOW.name}" == short_check.WORKFLOW_PATH
    assert "name" not in _job(workflow, short_check.JOB)
    names = [job.get("name", key) for key, job in workflow["jobs"].items()]
    assert names.count(short_check.JOB) == 1


def test_the_required_workflow_holds_no_friction_report(workflow) -> None:
    """The report gates nothing, and keeps an issue `checks` has no permission for."""
    assert "permissions" not in workflow
    assert "env" not in workflow


def test_each_job_but_checks_stops_after_30_minutes_and_checks_after_5(workflow) -> None:
    for name in JOBS[:-1]:
        assert _job(workflow, name)["timeout-minutes"] == 30, name
    assert _job(workflow, "checks")["timeout-minutes"] == 5


def test_only_a_new_head_cancels_and_main_and_the_queue_get_groups_of_their_own(workflow) -> None:
    """The runs on a pull request share a group; only a `synchronize` run's first attempt
    cancels what runs in it. A run on `main` or in the merge queue is keyed on its own
    run's id, so nothing cancels it or drops it while it waits (ADR-078 point 9)."""
    concurrency = workflow["concurrency"]
    assert concurrency["group"] == (
        "${{ github.event_name == 'pull_request' && "
        "format('checks-pr-{0}', github.event.pull_request.number) || "
        "format('checks-run-{0}', github.run_id) }}"
    )
    assert concurrency["cancel-in-progress"] == (
        "${{ github.event_name == 'pull_request' && github.event.action == 'synchronize' "
        "&& github.run_attempt == '1' }}"
    )
    for job in workflow["jobs"].values():
        assert "concurrency" not in job


# --- the token and what the parts read ----------------------------------------------------


def test_only_the_deciding_job_reads_runs_and_pull_requests(workflow) -> None:
    assert _job(workflow, "decide")["permissions"] == {
        "contents": "read",
        "actions": "read",
        "pull-requests": "read",
    }
    for name in JOBS[1:]:
        assert _job(workflow, name)["permissions"] == {"contents": "read"}, name


def test_every_checkout_keeps_the_token_out_and_only_the_decider_holds_it(workflow) -> None:
    """The checkouts keep the token out of the clone's configuration, so no later step
    reads it there, and of the steps that run the project's code only the deciding
    step is handed it."""
    checkouts = [
        step
        for _, step in _all_steps(workflow)
        if step.get("uses", "").startswith("actions/checkout@")
    ]
    assert len(checkouts) == len(JOBS)
    for step in checkouts:
        assert step["uses"] == "actions/checkout@v4"
        assert step["with"]["persist-credentials"] is False
    holders = [
        (job, step.get("id") or step.get("name"))
        for job, step in _all_steps(workflow)
        if "github.token" in json.dumps(step)
    ]
    assert holders == [("decide", "form")]
    for job in workflow["jobs"].values():
        assert "env" not in job


def test_no_step_puts_an_expression_in_a_shell_line(workflow) -> None:
    """A value in a `run:` line would be run as shell: each step reads what GitHub
    names from its environment."""
    for job, step in _all_steps(workflow):
        if "run" in step:
            assert "${{" not in step["run"], (job, step.get("name"))


def test_every_part_reads_the_pinned_base_and_the_pull_request_s_own_head(workflow) -> None:
    """One base for every part, the one the deciding job pinned, and the change's own
    head beside it, as the change checks read them (ADR-068 point 6)."""
    parts = [
        _by_id(_job(workflow, "rest"), "rest"),
        _by_id(_job(workflow, "rest"), "short"),
        *(_by_id(_job(workflow, name), "part") for name in SLICE_JOBS),
    ]
    for step in parts:
        assert step["env"] == {"PKIT_CHECK_BASE": PINNED_BASE, "PKIT_CHECK_HEAD": PR_HEAD}
    guard = _by_id(_job(workflow, "rest"), "guard")
    assert guard["env"]["PKIT_CHECK_BASE"] == PINNED_BASE
    assert _job(workflow, "decide")["outputs"]["base"] == "${{ steps.base.outputs.sha }}"


def test_every_part_sets_up_as_the_whole_run_did(workflow) -> None:
    for name in JOBS[1:-1]:
        steps = [str(step.get("name", step.get("uses"))) for step in _job(workflow, name)["steps"]]
        assert steps[:5] == [
            steps[0],
            "Set up Python",
            "Install uv",
            "Install project (clean resolve)",
            "Sync (provisions the query commands)",
        ], name
        assert _job(workflow, name)["steps"][0]["with"]["fetch-depth"] == 0


def test_the_deciding_job_sets_up_no_project_and_runs_no_check(workflow) -> None:
    runs = [step["run"] for step in _job(workflow, "decide")["steps"] if "run" in step]
    assert not any("uv sync" in run or "pkit sync" in run or "check.sh" in run for run in runs)
    assert not any("ci_parts.py" in run for run in runs)


# --- the deciding job ---------------------------------------------------------------------


def _decider(workflow: dict[str, Any]) -> dict[str, Any]:
    return _by_id(_job(workflow, "decide"), "form")


def test_the_deciding_job_pins_decides_then_names_and_the_decision_fails_nothing(
    workflow,
) -> None:
    ids = [step.get("id") for step in _job(workflow, "decide")["steps"]]
    assert ids.index("base") < ids.index("form") < ids.index("named") == len(ids) - 1
    decide = _decider(workflow)
    assert decide["continue-on-error"] is True
    assert "if" not in decide
    assert decide["env"]["PKIT_DECIDER_BASE"] == "${{ github.event.pull_request.base.ref }}"
    assert _job(workflow, "decide")["outputs"] == {
        "form": "${{ steps.named.outputs.form }}",
        "mode": "${{ steps.form.outputs.mode }}",
        "outcome": "${{ steps.form.outcome }}",
        "base": "${{ steps.base.outputs.sha }}",
    }


@pytest.mark.parametrize(
    ("event", "mode", "form"),
    [
        ("pull_request", "short", "short"),
        ("pull_request", "full", "full"),
        ("pull_request", "", "full"),
        ("merge_group", "short", "full"),
        ("push", "short", "full"),
        ("push", "", "full"),
    ],
)
def test_only_a_pull_request_s_decider_names_the_short_form(
    workflow, tmp_path: Path, event: str, mode: str, form: str
) -> None:
    named = _by_id(_job(workflow, "decide"), "named")
    assert named["env"] == {"PKIT_FORM_MODE": "${{ steps.form.outputs.mode }}"}
    output = tmp_path / "output"
    env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output)}

    done = _shell(
        named["run"], tmp_path, {**env, "GITHUB_EVENT_NAME": event, "PKIT_FORM_MODE": mode}
    )

    assert done.returncode == 0, done.stderr
    assert output.read_text() == f"form={form}\n"


class Merge:
    """A clone whose HEAD is a merge of a head onto a base, as GitHub checks one out."""

    def __init__(self, root: Path) -> None:
        self.root = root / "clone"
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(self.root)]
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        sign_nothing(self.root)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "root"], check=True)
        subprocess.run([*git, "checkout", "-q", "-b", "topic"], check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "head"], check=True)
        subprocess.run([*git, "checkout", "-q", "main"], check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "base"], check=True)
        self.base = self.rev("HEAD")
        subprocess.run([*git, "merge", "-q", "--no-ff", "-m", "merge", "topic"], check=True)
        self.merge = self.rev("HEAD")
        self.output = root / "output"

    def rev(self, ref: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", ref],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def pin(self, script: str, event: str, **env: str) -> subprocess.CompletedProcess[str]:
        return _shell(
            script,
            self.root,
            {
                "PATH": os.environ["PATH"],
                "HOME": str(self.root.parent),
                "GITHUB_OUTPUT": str(self.output),
                "GITHUB_EVENT_NAME": event,
                "PKIT_QUEUE_BASE": "",
                "PKIT_PUSHED": "",
                **env,
            },
        )


def test_the_base_is_pinned_to_one_commit_on_each_event(workflow, tmp_path: Path) -> None:
    """A pull request's base is the first parent of the merge checked out; the queue's,
    the commit its merge is built on; a push's, the pushed commit itself."""
    step = _by_id(_job(workflow, "decide"), "base")
    assert step["env"] == {
        "PKIT_QUEUE_BASE": "${{ github.event.merge_group.base_sha }}",
        "PKIT_PUSHED": "${{ github.sha }}",
    }
    clone = Merge(tmp_path)
    cases = [
        ("pull_request", {}, clone.base),
        ("merge_group", {"PKIT_QUEUE_BASE": clone.base[:12]}, clone.base),
        ("push", {"PKIT_PUSHED": clone.merge}, clone.merge),
    ]
    for event, env, pinned in cases:
        clone.output.write_text("")

        done = clone.pin(step["run"], event, **env)

        assert done.returncode == 0, (event, done.stderr)
        assert clone.output.read_text() == f"sha={pinned}\n", event


@pytest.mark.parametrize(
    ("event", "env"),
    [("merge_group", {}), ("merge_group", {"PKIT_QUEUE_BASE": "f" * 40}), ("push", {})],
    ids=["no-queue-base", "a-base-not-in-the-clone", "no-pushed-commit"],
)
def test_a_base_that_cannot_be_pinned_fails_the_deciding_job_and_names_none(
    workflow, tmp_path: Path, event: str, env: dict[str, str]
) -> None:
    clone = Merge(tmp_path)

    done = clone.pin(_by_id(_job(workflow, "decide"), "base")["run"], event, **env)

    assert done.returncode != 0
    assert not clone.output.exists() or "sha=" not in clone.output.read_text()


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
        return _shell(script, self.checkout, {**self.env, "GITHUB_EVENT_NAME": event})

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
    # An answer, so `checks` adds no line saying that no answer was given.
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


# --- the parts ----------------------------------------------------------------------------


def test_the_two_forms_exclude_each_other_and_only_a_pull_request_runs_the_short_one(
    workflow,
) -> None:
    """The event gate is the workflow's, outside the decider: a decider that said
    `short` on a push to `main` or a queued merge would still leave the run full."""
    rest = _job(workflow, "rest")
    assert _by_id(rest, "rest")["if"] == FULL_FORM
    assert _by_id(rest, "short")["if"] == SHORT_FORM
    for name in SLICE_JOBS:
        assert _job(workflow, name)["if"] == FULL_FORM
    checks = _job(workflow, "checks")
    assert _step(checks, short_check.FULL_STEP)["if"] == f"always() && ({FULL_FORM})"
    assert _step(checks, short_check.SHORT_STEP)["if"] == f"always() && {SHORT_FORM}"


def test_each_part_runs_its_part_of_the_aggregator(workflow) -> None:
    rest = _job(workflow, "rest")
    assert _by_id(rest, "rest")["run"] == "python scripts/ci_parts.py run --rest"
    assert _by_id(rest, "short")["run"] == "python scripts/ci_parts.py run --short"
    for index, name in enumerate(SLICE_JOBS, 1):
        step = _by_id(_job(workflow, name), "part")
        assert step["run"] == f"python scripts/ci_parts.py run --shard {index}/{SLICES}"


def test_the_slices_differ_only_in_which_slice_they_run(workflow) -> None:
    def generic(name: str, index: int) -> str:
        text = json.dumps(_job(workflow, name))
        return text.replace(f"{index}/{SLICES}", "i/N").replace(f"{index} of {SLICES}", "i of N")

    first = generic(SLICE_JOBS[0], 1)
    for index, name in enumerate(SLICE_JOBS, 1):
        assert generic(name, index).replace(f"-{index}-of-", "-1-of-") == first
        assert _job(workflow, name)["name"] == f"slice {index} of {SLICES}"


def test_each_slice_hands_on_its_report_and_keeps_its_times(workflow) -> None:
    for index, name in enumerate(SLICE_JOBS, 1):
        job = _job(workflow, name)
        assert job["outputs"] == {
            key: f"${{{{ steps.part.outputs.{key} }}}}"
            for key in ("passed", "digest", "collected", "share", "listed", "unlisted", "seconds")
        }
        keep = _step(job, "Keep the slice's test times")
        assert keep["uses"] == "actions/upload-artifact@v4"
        assert keep["if"] == "${{ !cancelled() }}"
        assert slices.ARTIFACT.fullmatch(keep["with"]["name"])
        assert keep["with"]["name"] == f"test-times-{index}-of-{SLICES}"
        assert keep["with"]["path"] == "${{ runner.temp }}/test-reports/parallel/"


def test_the_remainder_hands_on_one_attestation_and_the_guard_s(workflow) -> None:
    """Two attestations side by side would match neither form."""
    assert _job(workflow, "rest")["outputs"] == {
        "passed": "${{ steps.rest.outputs.passed }}${{ steps.short.outputs.passed }}",
        "seconds": "${{ steps.rest.outputs.seconds || steps.short.outputs.seconds }}",
        "guard": "${{ steps.guard.outputs.passed }}",
    }


def test_the_changeset_guard_keeps_to_pull_requests_runs_in_both_forms_and_says_it_passed(
    workflow,
) -> None:
    guard = _by_id(_job(workflow, "rest"), "guard")
    assert guard["name"].startswith("Changeset guard")
    assert guard["if"] == (
        "${{ !cancelled() && github.event_name == 'pull_request' "
        "&& steps.sync.outcome == 'success' }}"
    )
    lines = guard["run"].splitlines()
    assert lines == [
        'uv run pkit release check --base "$PKIT_CHECK_BASE"',
        f'echo "passed={ci_parts.GUARD}" >> "$GITHUB_OUTPUT"',
    ]


# --- checks -------------------------------------------------------------------------------


def test_checks_holds_the_two_forms_under_the_names_the_decider_reads(workflow) -> None:
    """The decider tells a run's form by these two steps of the `checks` job: keep both
    names, and no other job's steps take them (ADR-078 point 4)."""
    checks = _job(workflow, "checks")
    full = _step(checks, short_check.FULL_STEP)
    short = _step(checks, short_check.SHORT_STEP)
    assert full["name"] == short_check.FULL_STEP
    assert short["name"] == short_check.SHORT_STEP
    assert full["run"] == f"python scripts/ci_parts.py verdict full --slices {SLICES}"
    assert short["run"] == "python scripts/ci_parts.py verdict short"
    for step in (full, short):
        assert step["env"] == {"PKIT_NEEDS": "${{ toJSON(needs) }}"}
    others = [
        step.get("name")
        for job, step in _all_steps(workflow)
        if job != "checks" and step.get("name") in (short_check.FULL_STEP, short_check.SHORT_STEP)
    ]
    assert others == []


# The verdict over the jobs' outcomes and outputs, as `needs` hands them to `checks`.
DIGEST = "sha256:" + "d" * 64


def _slice(index: int, *, share: int = 50, digest: str = DIGEST) -> dict[str, Any]:
    return {
        "result": "success",
        "outputs": {
            "passed": f"check.sh --shard {index}/{SLICES} {digest}",
            "digest": digest,
            "collected": "100",
            "share": str(share),
            "listed": "100",
            "unlisted": "0",
            "seconds": "754",
        },
    }


def _needs(event: str, form: str = "full") -> dict[str, Any]:
    guard = {"guard": ci_parts.GUARD} if event == "pull_request" else {}
    rest = "check.sh --rest" if form == "full" else "check.sh --short"
    needs: dict[str, Any] = {
        "decide": {
            "result": "success",
            "outputs": {"form": form, "mode": form, "outcome": "success", "base": "b" * 40},
        },
        "rest": {"result": "success", "outputs": {"passed": rest, "seconds": "390", **guard}},
    }
    if form == "full":
        needs |= {name: _slice(i) for i, name in enumerate(SLICE_JOBS, 1)}
    else:
        needs |= {name: {"result": "skipped", "outputs": {}} for name in SLICE_JOBS}
    return needs


def _verdict(form: str, needs: dict[str, Any], event: str) -> ci_parts.Verdict:
    return ci_parts.verdict(form, SLICES, needs, event)


@pytest.mark.parametrize("event", EVENTS)
def test_a_full_run_whose_parts_all_said_they_passed_passes_and_shows_each_part_s_time(
    event: str,
) -> None:
    found = _verdict("full", _needs(event), event)

    assert found.passed, found.summary
    assert "### `checks`: the full run, passed" in found.summary
    assert "| slice 1 of 2 | `success` | 12 min 34 s | ran 50 |" in found.summary
    assert "| the remainder | `success` | 6 min 30 s | `check.sh --rest` |" in found.summary
    assert ("the changeset guard" in found.summary) == (event == "pull_request")
    assert "The slices agree" in found.summary


def test_a_short_check_on_a_pull_request_passes_without_the_slices() -> None:
    found = _verdict("short", _needs("pull_request", "short"), "pull_request")

    assert found.passed, found.summary
    assert "the short check, passed" in found.summary


@pytest.mark.parametrize("event", ["merge_group", "push"])
def test_only_a_pull_request_may_take_the_short_form(event: str) -> None:
    found = _verdict("short", _needs(event, "short"), event)

    assert not found.passed
    assert "only a pull request may take the short form" in found.summary


PARTS = ["decide", "rest", *SLICE_JOBS]


@pytest.mark.parametrize("event", EVENTS)
@pytest.mark.parametrize("part", PARTS)
@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", None])
def test_a_part_that_did_not_end_in_success_fails_the_full_run(
    event: str, part: str, result: str | None
) -> None:
    """A part that failed, was cancelled, was skipped, or never ran at all."""
    needs = _needs(event)
    if result is None:
        del needs[part]
    else:
        needs[part]["result"] = result

    assert not _verdict("full", needs, event).passed


@pytest.mark.parametrize("part", ["decide", "rest"])
@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", None])
def test_a_part_that_did_not_end_in_success_fails_the_short_check(
    part: str, result: str | None
) -> None:
    needs = _needs("pull_request", "short")
    if result is None:
        del needs[part]
    else:
        needs[part]["result"] = result

    assert not _verdict("short", needs, "pull_request").passed


@pytest.mark.parametrize("event", EVENTS)
@pytest.mark.parametrize(
    ("part", "output"),
    [
        ("decide", "form"),
        ("rest", "passed"),
        *((name, key) for name in SLICE_JOBS for key in ("passed", "digest", "collected", "share")),
    ],
)
def test_a_missing_output_fails_the_full_run(event: str, part: str, output: str) -> None:
    """A job ends in success with a step its condition skipped: only the step's own
    output says it ran and passed."""
    needs = _needs(event)
    del needs[part]["outputs"][output]

    assert not _verdict("full", needs, event).passed


@pytest.mark.parametrize(("form"), ["full", "short"])
def test_a_pull_request_whose_changeset_guard_said_nothing_fails(form: str) -> None:
    needs = _needs("pull_request", form)
    del needs["rest"]["outputs"]["guard"]

    found = _verdict(form, needs, "pull_request")

    assert not found.passed
    assert "the changeset guard did not say it passed" in found.summary


@pytest.mark.parametrize("event", ["merge_group", "push"])
def test_the_changeset_guard_is_a_pull_request_s_alone(event: str) -> None:
    needs = _needs(event)

    assert "guard" not in needs["rest"]["outputs"]
    assert _verdict("full", needs, event).passed


@pytest.mark.parametrize("event", EVENTS)
@pytest.mark.parametrize(
    ("part", "output", "said"),
    [
        ("rest", "passed", "check.sh --short"),
        ("rest", "passed", "check.sh --rest" + "check.sh --short"),
        ("rest", "passed", "passed"),
        ("slice-1", "passed", f"check.sh --shard 2/2 {DIGEST}"),
        ("slice-2", "passed", f"check.sh --shard 2/3 {DIGEST}"),
        ("slice-1", "passed", f"check.sh --shard 1/2 sha256:{'e' * 64}"),
        ("slice-1", "passed", "check.sh --shard 1/2"),
        ("slice-1", "passed", "check.sh --rest"),
    ],
    ids=[
        "the-remainder-ran-the-short-check",
        "both-forms-ran",
        "no-attestation",
        "another-slice",
        "another-count",
        "another-digest",
        "no-digest",
        "the-remainder-s",
    ],
)
def test_an_output_that_attests_another_step_fails_the_full_run(
    event: str, part: str, output: str, said: str
) -> None:
    needs = _needs(event)
    needs[part]["outputs"][output] = said

    assert not _verdict("full", needs, event).passed


@pytest.mark.parametrize(
    ("said", "named"),
    [("check.sh --rest", "short"), ("check.sh --short", "full"), ("check.sh --short", "")],
    ids=["the-remainder-ran-the-full-form", "the-decider-named-full", "the-decider-named-none"],
)
def test_a_short_check_that_attests_the_other_form_fails(said: str, named: str) -> None:
    needs = _needs("pull_request", "short")
    needs["rest"]["outputs"]["passed"] = said
    needs["decide"]["outputs"]["form"] = named

    assert not _verdict("short", needs, "pull_request").passed


@pytest.mark.parametrize(
    ("change", "why"),
    [
        ({"slice-2": {"digest": "sha256:" + "e" * 64}}, "one digest"),
        ({"slice-2": {"collected": "99"}}, "one number of tests collected"),
        ({"slice-2": {"share": "49"}}, "not the 100 collected"),
        ({"slice-1": {"share": "51"}}, "not the 100 collected"),
    ],
    ids=["digests", "collections", "a-share-short", "a-share-over"],
)
def test_slices_that_do_not_add_up_to_what_was_collected_fail(
    change: dict[str, dict[str, str]], why: str
) -> None:
    needs = _needs("push")
    for part, outputs in change.items():
        needs[part]["outputs"] |= outputs
        if "digest" in outputs:
            needs[part]["outputs"]["passed"] = (
                f"check.sh --shard {part[-1]}/{SLICES} {outputs['digest']}"
            )

    found = _verdict("full", needs, "push")

    assert not found.passed
    assert why in found.summary


def test_a_collection_a_tenth_below_the_table_warns_and_fails_nothing() -> None:
    needs = _needs("push")
    for name in SLICE_JOBS:
        needs[name]["outputs"] |= {"listed": "112", "unlisted": "12"}

    found = _verdict("full", needs, "push")

    assert found.passed, found.summary
    assert "a tenth fewer than the 112 the table names" in found.summary
    assert "the table lacks 12 of the 100 tests collected; a tenth or more" in found.summary


def test_a_deciding_job_that_named_no_form_fails_and_checks_says_the_run_is_full() -> None:
    """The deciding job failed before it named a form: no part started, and the full
    form's step runs and fails (ADR-078 point 4)."""
    needs = _needs("pull_request")
    needs["decide"] = {"result": "failure", "outputs": {}}
    for name in ["rest", *SLICE_JOBS]:
        needs[name] = {"result": "skipped", "outputs": {}}

    found = _verdict("full", needs, "pull_request")

    assert not found.passed
    assert "the deciding job named no form (it ended in `failure`)" in found.summary
    assert "gave no answer (it ended in `failure`), so the run is full" in found.summary


def test_a_decider_that_gave_no_answer_leaves_the_run_full_and_checks_says_so() -> None:
    needs = _needs("pull_request")
    needs["decide"]["outputs"] |= {"mode": "", "outcome": "failure"}

    found = _verdict("full", needs, "pull_request")

    assert found.passed, found.summary
    assert "gave no answer (it ended in `failure`), so the run is full (ADR-067)" in found.summary


def test_a_decider_that_answered_adds_no_such_line() -> None:
    assert "gave no answer" not in _verdict("full", _needs("push"), "push").summary


def test_what_a_part_said_is_set_in_code_spans() -> None:
    needs = _needs("push")
    needs["rest"]["outputs"]["passed"] = "<b>`hello`</b>"

    found = _verdict("full", needs, "push")

    assert "`<b>'hello'</b>`" in found.summary


@pytest.mark.parametrize("form", ["full", "short"])
def test_the_verdict_step_reads_needs_and_fails_as_its_verdict_does(
    tmp_path: Path, form: str
) -> None:
    summary = tmp_path / "summary"
    needs = _needs("pull_request", form)
    env = {
        "PKIT_NEEDS": json.dumps(needs),
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_STEP_SUMMARY": str(summary),
    }
    args = ["verdict", form, *(["--slices", str(SLICES)] if form == "full" else [])]

    assert ci_parts.main(args, env) == 0
    assert "passed" in summary.read_text()
    needs["rest"]["result"] = "failure"
    assert ci_parts.main(args, {**env, "PKIT_NEEDS": json.dumps(needs)}) == 1
    assert ci_parts.main(args, {**env, "PKIT_NEEDS": "not json"}) == 1


# --- a part, run against a stub aggregator ------------------------------------------------

# Prints a line for each check, `FAILED` for those $STUB_FAILED names, writes the
# reports $STUB_REPORTS holds, and exits with $STUB_STATUS.
STUB_CHECK = """#!/bin/sh
echo "args: $*"
for label in $STUB_FAILED; do echo "-- $label: FAILED"; done
echo "-- lint: ok"
if [ -n "$STUB_REPORTS" ]; then
  mkdir -p "$PKIT_TEST_REPORTS"
  cp -R "$STUB_REPORTS"/. "$PKIT_TEST_REPORTS"
fi
exit "${STUB_STATUS:-0}"
"""


class Part:
    """A runner's temporary folder, its output and summary files, and a stub aggregator."""

    def __init__(self, root: Path) -> None:
        self.check = root / "check.sh"
        self.check.write_text(STUB_CHECK)
        self.check.chmod(0o755)
        self.temp = root / "temp"
        self.temp.mkdir()
        self.output = root / "output"
        self.summary = root / "summary"
        self.reports = root / "reports"
        self.env = {
            "PATH": os.environ["PATH"],
            "RUNNER_TEMP": str(self.temp),
            "GITHUB_OUTPUT": str(self.output),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "STUB_REPORTS": "",
        }

    def report(self, name: str, ran: dict[str, Any], cut: dict[str, Any] | None = None) -> None:
        folder = self.reports / name
        folder.mkdir(parents=True)
        (folder / slices.RAN_REPORT).write_text(json.dumps(ran))
        if cut is not None:
            (folder / slices.CUT_REPORT).write_text(json.dumps(cut))
        self.env["STUB_REPORTS"] = str(self.reports)

    def run(self, *part: str, **env: str) -> int:
        return ci_parts.run_part(list(part), {**self.env, **env}, self.check)

    def outputs(self) -> list[tuple[str, str]]:
        lines = self.output.read_text().splitlines() if self.output.exists() else []
        return [(key, value) for key, _, value in (line.partition("=") for line in lines)]


CUT = {"shard": "1/2", "digest": DIGEST, "collected": 3, "held": 2, "listed": 3, "unlisted": 1}
RAN = {"tests": {"tests/test_a.py::test_x": 1.5, "tests/test_a.py::test_y": 0.25}, "failed": []}


def test_a_slice_that_passed_hands_on_its_report_and_says_it_passed_last(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    part = Part(tmp_path)
    part.report("parallel", RAN, CUT)

    assert part.run("--shard", "1/2") == 0

    outputs = part.outputs()
    assert outputs[-1] == ("passed", f"check.sh --shard 1/2 {DIGEST}")
    said = dict(outputs)
    assert {k: said[k] for k in ("digest", "collected", "share", "listed", "unlisted")} == {
        "digest": DIGEST,
        "collected": "3",
        "share": "2",
        "listed": "3",
        "unlisted": "1",
    }
    assert said["seconds"].isdigit()
    assert "args: --shard 1/2" in capfd.readouterr().out
    summary = part.summary.read_text()
    assert "slice 1 of 2 of the suite's parallel pass: passed" in summary
    assert "Its share held 2 of the 3 tests collected" in summary
    assert "Run it again" not in summary


def test_a_slice_that_failed_names_its_failures_says_how_to_run_it_again_and_not_that_it_passed(
    tmp_path: Path,
) -> None:
    part = Part(tmp_path)
    part.report("parallel", {**RAN, "failed": ["tests/test_a.py::test_y"]}, CUT)

    assert part.run("--shard", "1/2", STUB_STATUS="1", STUB_FAILED="tests") == 1

    keys = [key for key, _ in part.outputs()]
    assert "passed" not in keys
    assert {"seconds", "digest", "share"} <= set(keys)
    summary = part.summary.read_text()
    assert "slice 1 of 2 of the suite's parallel pass: did not pass" in summary
    assert "- `tests/test_a.py::test_y`" in summary
    assert "- `tests`" in summary
    assert "Run it again: `./scripts/check.sh --shard 1/2`." in summary


@pytest.mark.parametrize(
    ("ran", "cut"),
    [(RAN, None), ({"tests": {}, "failed": []}, CUT), (None, None)],
    ids=["no-cut", "no-test-ran", "no-report"],
)
def test_a_slice_that_passed_without_reporting_what_it_ran_did_not_pass(
    tmp_path: Path, ran: dict[str, Any] | None, cut: dict[str, Any] | None
) -> None:
    part = Part(tmp_path)
    if ran is not None:
        part.report("parallel", ran, cut)

    assert part.run("--shard", "1/2") == 1
    assert "passed" not in dict(part.outputs())


@pytest.mark.parametrize("which", ["--rest", "--short"])
def test_the_remainder_says_which_form_it_ran_last(tmp_path: Path, which: str) -> None:
    part = Part(tmp_path)

    assert part.run(which) == 0

    assert part.outputs()[-1] == ("passed", f"check.sh {which}")
    assert [key for key, _ in part.outputs()] == ["seconds", "passed"]


def test_the_remainder_names_each_failing_line_and_each_failing_test(tmp_path: Path) -> None:
    part = Part(tmp_path)
    part.report(
        "serial",
        {"tests": {"tests/test_s.py::test_alone": 3.0}, "failed": ["tests/test_s.py::test_alone"]},
    )

    assert part.run("--rest", STUB_STATUS="1", STUB_FAILED="validate prose") == 1

    assert "passed" not in dict(part.outputs())
    summary = part.summary.read_text()
    assert "- `validate`\n- `prose`" in summary
    assert "- `tests/test_s.py::test_alone`" in summary
    assert "Run it again: `./scripts/check.sh --rest`." in summary
