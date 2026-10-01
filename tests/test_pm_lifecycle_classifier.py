"""The issue lifecycle's classifier, `detect-state` (DEC-033 D2).

The shipped lifecycle names one classifier for its five states under
`mode: classified` (COR-033 point 5), so the engine reads an issue once per
reading of its position. Pinned here:

- parity: across the full truth table — kit labels, an adopter's label remap, a
  derive binding, an unsupported binding, closed issues, milestones, a stray
  state label — the classifier answers the inferred state when the lifecycle
  declares it and `null` (the value in the reason) when it does not, and every
  per-state detector agrees with it: `detect_state(n, S).result` is
  `classify_state(n).state == S`;
- one read: the classifier calls `_fetch_issue` exactly once;
- the shipped definition: five states, one mode, one classifier, `version` 5;
- a failed read: the script exits non-zero with `gh`'s own words on stderr, and
  through the real engine every state is indeterminate with that cause, shown
  once in the narrative;
- a value the lifecycle does not declare — a derive binding's `open`, a stray
  state label — through the real script and the real engine: a determinate
  "no position" with the classifier's reason shown, in the narrative and as
  `position.placed_nowhere`;
- one fetch through the real engine: a `status` reads the issue's state once.

The engine-driven tests run the shipped scripts the way the engine runs every
predicate, against a fake `gh` on PATH that logs its arguments, each script
given the test's own interpreter rather than its `uv run --script` shebang.
"""

from __future__ import annotations

import itertools
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
CAP_SRC = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
CAP_SCRIPTS = CAP_SRC / "scripts"
if str(CAP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CAP_SCRIPTS))

from _lib import axis_labels  # noqa: E402
from _lib import lifecycle_inference as infer  # noqa: E402
from _lib import lifecycle_predicates as predicates  # noqa: E402

from project_kit.cli_render import strip_ansi  # noqa: E402
from project_kit.process import (  # noqa: E402
    ProcessEngine,
    load_definition,
    render_status_json,
    render_status_narrative,
)

LIFECYCLE = ["todo", "backlog", "in-progress", "review", "done"]
ADDRESS = "project-management:issue-lifecycle"

# The substrate-map shapes the position read distinguishes (ADR-026 point 5).
DERIVE_MAP = axis_labels.SubstrateMap(
    axes={
        "state": {
            "derive": {
                "from": "open-closed",
                "states": {
                    "open": "issue is open and not labelled Blocked",
                    "blocked": "issue is open and labelled Blocked",
                    "done": "issue is closed",
                },
            }
        },
    }
)
LABEL_STATE_MAP = axis_labels.SubstrateMap(
    axes={
        "state": {
            "label": {
                "remap": {
                    "todo": "Status:Todo",
                    "backlog": "Status:Backlog",
                    "in-progress": "Status:Doing",
                    "review": "Status:Review",
                    "done": "Status:Done",
                }
            }
        },
    }
)
UNSUPPORTED_STATE_MAP = axis_labels.SubstrateMap(axes={"state": {"unsupported": True}})


# --- parity across the truth table ------------------------------------------


def _truth_table():
    gh_states = ["open", "closed"]
    milestones: list[dict[str, Any] | None] = [None, {}, {"title": "M1"}]
    label_sets = [
        [],
        ["type:feature"],
        *([f"state:{s}"] for s in LIFECYCLE),
        ["state:in-progress", "type:feature"],
        ["priority:High", "state:review"],
        ["state:parked"],  # a stray state label: not a lifecycle state
        ["Status:Doing"],  # an adopter's remapped label
        ["Status:Review", "state:todo"],
        ["Blocked"],
        ["Blocked", "state:backlog"],
    ]
    maps = [None, LABEL_STATE_MAP, DERIVE_MAP, UNSUPPORTED_STATE_MAP]
    return itertools.product(gh_states, milestones, label_sets, maps)


def _stub_read(
    monkeypatch: pytest.MonkeyPatch, issue: dict[str, Any], substrate_map: Any
) -> list[str]:
    """Stub the predicates' capability lookup, config, map and issue read; the
    returned list records each `_fetch_issue` call's fields."""
    fetched: list[str] = []

    def fetch(_number: int, _config: dict[str, Any], fields: str) -> dict[str, Any]:
        fetched.append(fields)
        return issue

    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_fetch_issue", fetch)
    monkeypatch.setattr(predicates.axis_labels, "load_substrate_map", lambda _root: substrate_map)
    return fetched


def test_the_classifier_agrees_with_the_inference_and_every_detector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answered: set[str | None] = set()
    for gh_state, milestone, labels, substrate_map in _truth_table():
        issue = {
            "state": gh_state.upper(),
            "milestone": milestone,
            "labels": [{"name": name} for name in labels],
        }
        fetched = _stub_read(monkeypatch, issue, substrate_map)
        inferred = infer.infer_current_state(
            state=gh_state, milestone=milestone or {}, labels=labels, substrate_map=substrate_map
        )
        case = f"{gh_state} milestone={milestone} labels={labels} map={substrate_map}"

        answer = predicates.classify_state(1)
        assert fetched == ["state,milestone,labels"], case  # one read
        expected = inferred if inferred in LIFECYCLE else None
        assert answer["state"] == expected, case
        assert answer["detail"] == {"inferred_state": inferred}, case
        assert repr(inferred) in answer["reason"], case
        answered.add(answer["state"])

        for state in LIFECYCLE:
            assert predicates.detect_state(1, state)["result"] is (answer["state"] == state), (
                f"{case}: detect-{state} disagrees with the classifier"
            )

    # The table reaches every lifecycle state and the null answer.
    assert answered == {*LIFECYCLE, None}


@pytest.mark.parametrize(
    ("labels", "substrate_map", "inferred"),
    [
        ([], DERIVE_MAP, "open"),
        (["Blocked"], DERIVE_MAP, "blocked"),
        (["state:parked"], None, "parked"),
    ],
)
def test_a_value_the_lifecycle_does_not_declare_is_a_reasoned_null(
    monkeypatch: pytest.MonkeyPatch, labels: list[str], substrate_map: Any, inferred: str
) -> None:
    issue = {"state": "OPEN", "milestone": None, "labels": [{"name": n} for n in labels]}
    _stub_read(monkeypatch, issue, substrate_map)
    assert predicates.classify_state(7) == {
        "state": None,
        "reason": f"#7 inferred state is {inferred!r}, which is not a state of the issue lifecycle",
        "detail": {"inferred_state": inferred},
    }


def test_a_failed_read_is_indeterminate_and_says_why(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates.axis_labels, "load_substrate_map", lambda _root: None)
    monkeypatch.setattr(
        predicates,
        "gh_run",
        lambda argv, _config, **_kw: subprocess.CompletedProcess(
            argv, 1, "", "HTTP 404: Could not resolve to an Issue with the number of 9.\n"
        ),
    )
    answer = predicates.classify_state(9)
    assert answer.get(predicates.INDETERMINATE_KEY) is True
    assert "state" not in answer  # never read as an answer, even if passed on
    said = capsys.readouterr().err
    assert "could not read issue #9: `gh issue view` exited 1" in said
    assert "HTTP 404: Could not resolve to an Issue with the number of 9." in said


# --- the shipped definition ---------------------------------------------------


def test_the_shipped_lifecycle_detects_with_one_classifier() -> None:
    workflow = YAML(typ="safe").load((CAP_SRC / "schemas" / "workflow.yaml").read_text())
    process = workflow["process"]
    detections = [state["detection"] for state in process["states"]]
    assert [state["id"] for state in process["states"]] == [
        "done",
        "review",
        "in-progress",
        "backlog",
        "todo",
    ]
    assert detections == [{"mode": "classified", "predicate": {"run": "detect-state"}}] * 5
    assert process["version"] == 5
    assert workflow["schema_version"] == 4

    package = YAML(typ="safe").load((CAP_SRC / "package.yaml").read_text())
    for command in ("detect-state", *(f"detect-{state}" for state in LIFECYCLE)):
        assert package["commands"][command]["script"] == f"scripts/{command}.py"


# --- the real scripts through the real engine --------------------------------

_VALID_CONFIG = "schema_version: 1\ndefault_branch: main\nworkstreams: []\n"

# A fake `gh`: logs its arguments, one call per line, then answers `gh issue
# view` from `_issue.json` (or fails as `_gh-fails` says) and `gh pr list` with
# no merged pull requests.
_FAKE_GH = """\
import json, pathlib, sys
root = pathlib.Path({root!r})
with open(root / "_gh-calls", "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
failing = root / "_gh-fails"
if failing.exists():
    sys.stderr.write(failing.read_text())
    sys.exit(1)
if sys.argv[1:3] == ["issue", "view"]:
    issue = json.loads((root / "_issue.json").read_text())
    fields = sys.argv[sys.argv.index("--json") + 1].split(",")
    print(json.dumps({{f: issue[f] for f in fields}}))
elif sys.argv[1:3] == ["pr", "list"]:
    print("[]")
else:
    sys.stderr.write("unexpected gh call\\n")
    sys.exit(1)
"""


def _executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A bootstrapped adopter project with the shipped capability, its scripts
    run by this interpreter, and a fake `gh` first on PATH."""
    root = tmp_path / "repo"
    root.mkdir()
    for args in (["init", "-q"], ["remote", "add", "origin", "git@github.com:acme/widget.git"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    cap = root / ".pkit" / "capabilities" / "project-management"
    shutil.copytree(CAP_SRC / "schemas", cap / "schemas")
    shutil.copytree(CAP_SCRIPTS, cap / "scripts")
    shutil.copy(CAP_SRC / "package.yaml", cap / "package.yaml")
    (cap / "project").mkdir()
    (cap / "project" / "config.yaml").write_text(_VALID_CONFIG, encoding="utf-8")
    (cap / "project" / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\nbootstrap:\n  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.53.0\n  by: bootstrap\n  repo: github.com/acme/widget\n",
        encoding="utf-8",
    )
    for script in (cap / "scripts").glob("*.py"):
        body = script.read_text(encoding="utf-8").split("\n", 1)[1]
        script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    defs = root / ".pkit" / "schemas" / "_defs"
    defs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / ".pkit" / "schemas" / "_defs" / "process.schema.json", defs)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _executable(bin_dir / "gh", f"#!{sys.executable}\n" + _FAKE_GH.format(root=str(root)))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    _issue(root, "OPEN", ["type:task", "state:in-progress"])
    return root


def _issue(root: Path, state: str, labels: list[str], body: str = "- [x] done\n") -> None:
    issue = {
        "state": state,
        "milestone": {"title": "M1"},
        "labels": [{"name": n} for n in labels],
        "body": body,
    }
    (root / "_issue.json").write_text(json.dumps(issue), encoding="utf-8")


# A derive binding (ADR-026 point 5): state read from open/closed, so an open
# issue is `open`, a value the lifecycle does not declare.
_DERIVE_MAP_YAML = """\
axes:
  state:
    derive:
      from: open-closed
      states:
        open: issue is open and not labelled Blocked
        blocked: issue is open and labelled Blocked
        done: issue is closed
"""


def _gh_calls(root: Path) -> list[str]:
    log = root / "_gh-calls"
    return log.read_text().splitlines() if log.exists() else []


def _engine(root: Path) -> ProcessEngine:
    return ProcessEngine.for_subject(load_definition(root, ADDRESS), root, "42")


def test_a_status_reads_the_issue_state_once(project: Path) -> None:
    payload = json.loads(render_status_json(_engine(project), "agent"))
    assert payload["position"]["state"] == "in-progress"
    assert payload["position"]["indeterminate"] is False
    # One read of where the issue stands, and one of its body for the close
    # gate out of in-progress — not five of the first.
    assert _gh_calls(project) == [
        "issue view 42 --json state,milestone,labels",
        "issue view 42 --json body",
    ]


def test_a_failed_read_leaves_every_state_indeterminate_with_its_cause(project: Path) -> None:
    (project / "_gh-fails").write_text(
        "HTTP 404: Could not resolve to an Issue with the number of 42.\n", encoding="utf-8"
    )
    script = project / ".pkit" / "capabilities" / "project-management" / "scripts"
    direct = subprocess.run(
        [str(script / "detect-state.py"), "42", "--json"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert direct.returncode != 0
    assert direct.stdout == ""
    assert "HTTP 404: Could not resolve to an Issue" in direct.stderr

    payload = json.loads(render_status_json(_engine(project), "agent"))
    unevaluated = payload["position"]["unevaluated"]
    assert [entry["state"] for entry in unevaluated] == [
        "done",
        "review",
        "in-progress",
        "backlog",
        "todo",
    ]
    for entry in unevaluated:
        assert (
            entry["reason"] == "couldn't evaluate detection predicate 'detect-state': it exited 2"
        )
        assert "could not read issue #42: `gh issue view` exited 1" in entry["stderr_tail"]
        assert "HTTP 404: Could not resolve to an Issue" in entry["stderr_tail"]

    narrative = strip_ansi(render_status_narrative(_engine(project), "agent"))
    assert (
        "couldn't evaluate 'done', 'review', 'in-progress', 'backlog', 'todo': couldn't "
        "evaluate detection predicate 'detect-state': it exited 2"
    ) in narrative
    assert narrative.count("HTTP 404") == 1

    allowed, reason, _position = _engine(project).can_move("review", "agent")
    assert allowed is False
    assert reason.count("HTTP 404") == 1


@pytest.mark.parametrize(
    ("derive", "labels", "inferred"),
    [
        pytest.param(True, ["type:task"], "open", id="derive-bound"),
        pytest.param(False, ["type:task", "state:foo"], "foo", id="stray-label"),
    ],
)
def test_a_value_the_lifecycle_does_not_declare_is_no_position_with_its_reason(
    project: Path, derive: bool, labels: list[str], inferred: str
) -> None:
    if derive:
        cap = project / ".pkit" / "capabilities" / "project-management"
        (cap / "project" / "substrate-map.yaml").write_text(_DERIVE_MAP_YAML, encoding="utf-8")
    _issue(project, "OPEN", labels)
    reason = f"#42 inferred state is {inferred!r}, which is not a state of the issue lifecycle"

    script = project / ".pkit" / "capabilities" / "project-management" / "scripts"
    direct = subprocess.run(
        [str(script / "detect-state.py"), "42", "--json"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert direct.returncode == 0, direct.stderr
    assert json.loads(direct.stdout) == {
        "state": None,
        "reason": reason,
        "detail": {"inferred_state": inferred},
    }

    position = json.loads(render_status_json(_engine(project), "agent"))["position"]
    assert (position["state"], position["indeterminate"]) == (None, False)
    assert position["unevaluated"] == []
    assert position["placed_nowhere"] == [{"predicate": "detect-state", "reason": reason}]

    narrative = strip_ansi(render_status_narrative(_engine(project), "agent"))
    assert "Where: no position" in narrative
    assert f"'detect-state' places the subject in none of its states: {reason}" in narrative
