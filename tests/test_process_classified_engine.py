"""Tests for `classified` detection (COR-033 point 5, ADR-062).

A fixture capability whose predicates are one generic script each: it counts
its runs in a file, then prints the answer the test wrote for it — or, when the
test says so, writes a refusal on stderr and exits non-zero. So every reading
ADR-062 point 3 names is driven from a file, and the number of runs is a fact
the test reads back. Covers:

- the one run: a classifier runs once per `status`, per `can-move`, per `move`
  and per CLI invocation, however many states name it; and once per resolution
  of a cascade member (a fresh memo each time, ADR-062 point 11),
- each reading of a classifier's answer: its own state, another of its states,
  `null` with a reason that is not blank (a determinate "no position", the
  reason shown in the narrative and as `position.placed_nowhere` in `--json`),
  every unreadable answer — a blank reason and a falsy `state` among them —
  (indeterminate, the answer quoted — bounded, made safe), a `result` beside
  `state` (not read, nor fallen back on beside an unreadable one), no answer at
  all — a non-zero exit, a timeout, two documents, trailing text, an array —
  (one cause, shown once per classifier in the narrative views and in a
  refusal, once per state in `--json`),
- from an indeterminate position a gated `from: "*"` move is listed refused and
  its gate is not run,
- nothing survives an invocation,
- one mode per definition: a definition that mixes modes — a typo'd mode, a
  detection with no mode — runs no detection and says why, and `pkit
  validate`'s process member reports it; a state with no detection is no
  mode; so too `classified` detections that name one command under different
  `with` mappings, which run as two classifiers,
- the reading lives in position resolution alone: a `state` in a gate's, an
  invariant's, a `resume_when`'s and a `membership`'s answer is not read,
- several classifiers (ADR-062 point 6) and a classifier naming another's state,
- a classifier's command in an `inferred` definition reads false (point 4),
- a detection mode this engine does not implement.
"""

from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.cli_render import strip_ansi
from project_kit.process import (
    ProcessEngine,
    definitions_outcome,
    load_definition,
    render_status_json,
    render_status_narrative,
)

# --- fixture scaffolding --------------------------------------------------

# Every predicate the fixtures register. Each is the same generic script,
# reading and counting under its own name.
_COMMANDS = (
    "classify",
    "classify-other",
    "detect-done",
    "gate-open",
    "gate-state-only",
    "check-state-only",
    "resume-state-only",
)

_TRANSITIONS = """\
  transitions:
    - from: draft
      to: ready
      trigger: submit
      authorisation: agent-autonomous
      gate:
        kind: deterministic
        predicate:
          run: gate-open
    - from: ready
      to: done
      trigger: approve
      authorisation: agent-autonomous
"""

# (state id, mode — None for a detection that declares none, command — None
# for a state with no detection, `with` mapping or None)
State = tuple[str, str | None, str | None, dict[str, Any] | None]

_ONE_CLASSIFIER: list[State] = [
    ("draft", "classified", "classify", None),
    ("ready", "classified", "classify", None),
    ("done", "classified", "classify", None),
]


def _answering(name: str) -> str:
    """A predicate that counts its run, then answers what `_answer-<name>`
    holds — or, when `_exit-<name>` exists, writes `_stderr-<name>` on stderr
    and exits with that code; when `_sleep-<name>` exists it first sleeps past
    any bound a test sets."""
    return (
        "import pathlib, sys\n"
        f"name = {name!r}\n"
        "with open(f'_runs-{name}', 'a') as fh:\n"
        "    fh.write('run\\n')\n"
        "if pathlib.Path(f'_sleep-{name}').exists():\n"
        "    import time\n"
        "    time.sleep(60)\n"
        "code = pathlib.Path(f'_exit-{name}')\n"
        "if code.exists():\n"
        "    said = pathlib.Path(f'_stderr-{name}')\n"
        "    sys.stderr.write(said.read_text() if said.exists() else '')\n"
        "    sys.exit(int(code.read_text()))\n"
        "sys.stdout.write(pathlib.Path(f'_answer-{name}').read_text())\n"
    )


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _definition(states: list[State], transitions: str = _TRANSITIONS, extra: str = "") -> str:
    lines = [
        "process:",
        "  id: demo",
        "  version: 1",
        "  subject:",
        "    cardinality: singleton",
    ]
    if extra:
        lines.append(extra.rstrip("\n"))
    lines.append("  states:")
    for state_id, mode, command, with_args in states:
        lines += [f"    - id: {state_id}", f"      meaning: The {state_id} state."]
        if state_id == "done":
            lines.append("      terminal: true")
        if command is None:
            continue
        lines.append("      detection:")
        if mode is not None:
            lines.append(f"        mode: {mode}")
        lines += ["        predicate:", f"          run: {command}"]
        if with_args is not None:
            lines.append(f"          with: {json.dumps(with_args)}")
    return "\n".join(lines) + "\n" + transitions


def _cap(repo: Path) -> Path:
    return repo / ".pkit" / "capabilities" / "fixture"


def _use(repo: Path, definition: str) -> None:
    (_cap(repo) / "schemas" / "demo.yaml").write_text(definition, encoding="utf-8")


def _answer(repo: Path, name: str, payload: Any) -> None:
    (repo / f"_answer-{name}").write_text(json.dumps(payload), encoding="utf-8")


def _answer_raw(repo: Path, name: str, text: str) -> None:
    """What the predicate prints on standard output, byte for byte."""
    (repo / f"_answer-{name}").write_text(text, encoding="utf-8")


def _refuse(repo: Path, name: str, code: int, said: str) -> None:
    (repo / f"_exit-{name}").write_text(str(code), encoding="utf-8")
    (repo / f"_stderr-{name}").write_text(said, encoding="utf-8")


def _runs(repo: Path, name: str) -> int:
    counter = repo / f"_runs-{name}"
    return len(counter.read_text().splitlines()) if counter.exists() else 0


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo with the shape contract staged and a fixture capability whose
    `demo` process detects every state with the one classifier `classify`,
    which answers `draft` until a test says otherwise."""
    pkit = tmp_path / ".pkit"
    defs = pkit / "schemas" / "_defs"
    defs.mkdir(parents=True, exist_ok=True)
    source_defs = (
        Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
    )
    (defs / "process.schema.json").write_text(source_defs.read_text(encoding="utf-8"))

    cap = _cap(tmp_path)
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    registered = "".join(
        f"  {name}:\n    script: scripts/{name}.py\n    help: {name}\n" for name in _COMMANDS
    )
    (cap / "package.yaml").write_text(
        "schema_version: 2\n"
        "component:\n  kind: capability\n  name: fixture\n  version: 0.1.0\n"
        "description: Fixture capability for classified detection.\n"
        f"commands:\n{registered}",
        encoding="utf-8",
    )
    for name in _COMMANDS:
        _write_script(cap / "scripts" / f"{name}.py", _answering(name))

    _use(tmp_path, _definition(_ONE_CLASSIFIER))
    _answer(tmp_path, "classify", {"state": "draft", "reason": "the work says draft"})
    _answer(tmp_path, "gate-open", {"result": True, "reason": "checks pass"})
    return tmp_path


def _engine(repo: Path) -> ProcessEngine:
    return ProcessEngine(load_definition(repo, "fixture:demo"), repo)


def _status(repo: Path) -> dict[str, Any]:
    return json.loads(render_status_json(_engine(repo), "agent"))


# --- one run per reading of the position (ADR-062 point 11) ---------------


def test_a_status_read_runs_the_classifier_once_for_every_state(repo: Path) -> None:
    payload = _status(repo)
    assert payload["position"]["state"] == "draft"
    assert _runs(repo, "classify") == 1

    narrative = render_status_narrative(_engine(repo), "agent")
    assert "Where: draft" in strip_ansi(narrative)
    assert _runs(repo, "classify") == 2  # one more invocation, one more run


def test_can_move_and_move_each_run_the_classifier_once(repo: Path) -> None:
    allowed, _reason, _position = _engine(repo).can_move("ready", "agent")
    assert allowed is True
    assert _runs(repo, "classify") == 1

    result = _engine(repo).move("ready", "agent")
    assert result.ok is True
    assert _runs(repo, "classify") == 2


def test_each_cli_invocation_runs_the_classifier_once(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    monkeypatch.chdir(repo)
    runner = CliRunner()

    status = runner.invoke(main, ["process", "status", "fixture:demo", "--json"])
    assert status.exit_code == 0, status.output
    assert json.loads(status.output)["position"]["state"] == "draft"
    assert _runs(repo, "classify") == 1

    can_move = runner.invoke(main, ["process", "can-move", "fixture:demo", "--to", "ready"])
    assert can_move.exit_code == 0, can_move.output
    assert _runs(repo, "classify") == 2


def test_nothing_survives_an_invocation(repo: Path) -> None:
    assert _engine(repo).resolve_position().state_id == "draft"
    _answer(repo, "classify", {"state": "ready", "reason": "the work was submitted"})
    assert _engine(repo).resolve_position().state_id == "ready"
    assert _runs(repo, "classify") == 2


# --- reading a classifier's answer (ADR-062 point 3) ----------------------


@pytest.mark.parametrize("state_id", ["draft", "ready", "done"])
def test_each_declared_answer_places_the_subject(repo: Path, state_id: str) -> None:
    _answer(repo, "classify", {"state": state_id, "reason": f"the work says {state_id}"})
    position = _engine(repo).resolve_position()
    assert position.state_id == state_id
    assert position.indeterminate is False
    assert position.detection_reasons[state_id].result is True
    others = [sid for sid in ("draft", "ready", "done") if sid != state_id]
    assert all(position.detection_reasons[sid].result is False for sid in others)
    assert not position.unevaluated


def test_null_with_a_reason_is_a_determinate_no_position_that_says_why(repo: Path) -> None:
    _answer(repo, "classify", {"state": None, "reason": "the work is 'parked', no state of mine"})
    position = _engine(repo).resolve_position()
    assert position.state_id is None
    assert position.indeterminate is False
    assert position.placed_nowhere == (("classify", "the work is 'parked', no state of mine"),)

    narrative = strip_ansi(render_status_narrative(_engine(repo), "agent"))
    assert "Where: no position" in narrative
    assert (
        "'classify' places the subject in none of its states: "
        "the work is 'parked', no state of mine"
    ) in narrative

    # --json carries the reason too, so a consumer can tell a reasoned "none"
    # from detections that are all false.
    payload = _status(repo)["position"]
    assert (payload["state"], payload["indeterminate"]) == (None, False)
    assert payload["placed_nowhere"] == [
        {"predicate": "classify", "reason": "the work is 'parked', no state of mine"}
    ]


def test_a_reason_padded_with_whitespace_is_a_reason(repo: Path) -> None:
    _answer(repo, "classify", {"state": None, "reason": "  parked  "})
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == (None, False)
    assert position.placed_nowhere == (("classify", "  parked  "),)


def test_placed_nowhere_is_empty_when_a_state_is_true(repo: Path) -> None:
    assert _status(repo)["position"]["placed_nowhere"] == []


def test_a_multi_line_null_reason_hangs_under_its_line(repo: Path) -> None:
    _answer(repo, "classify", {"state": None, "reason": "parked\nuntil the owner returns"})
    narrative = strip_ansi(render_status_narrative(_engine(repo), "agent")).splitlines()
    first = narrative.index("    'classify' places the subject in none of its states: parked")
    assert narrative[first + 1] == "      until the owner returns"


@pytest.mark.parametrize(
    ("answer", "why"),
    [
        ({"reason": "no state given"}, "no `state` key"),
        ({"state": None}, "`state` is null without a reason"),
        ({"state": None, "reason": None}, "`state` is null without a reason"),
        ({"state": None, "reason": 7}, "`state` is null without a reason"),
        ({"state": None, "reason": ["parked"]}, "`state` is null without a reason"),
        # A blank reason is no reason: it cannot tell a deliberate "none" from
        # an accident.
        ({"state": None, "reason": ""}, "`state` is null with a blank reason"),
        ({"state": None, "reason": " "}, "`state` is null with a blank reason"),
        ({"state": None, "reason": "\n"}, "`state` is null with a blank reason"),
        ({"state": None, "reason": " \t\r\n"}, "`state` is null with a blank reason"),
        ({"state": 3, "reason": "a number"}, "`state` is neither a string nor null"),
        ({"state": ["draft"], "reason": "a list"}, "`state` is neither a string nor null"),
        ({"state": True, "reason": "a bool"}, "`state` is neither a string nor null"),
        # Falsy values are not `null`: none says "none of these".
        ({"state": 0, "reason": "zero"}, "`state` is neither a string nor null"),
        ({"state": False, "reason": "false"}, "`state` is neither a string nor null"),
        ({"state": [], "reason": "an empty list"}, "`state` is neither a string nor null"),
        ({"state": {}, "reason": "an empty object"}, "`state` is neither a string nor null"),
        ({"state": "", "reason": "empty"}, "`state` is the empty string"),
        (
            {"state": "parked", "reason": "x"},
            "`state` names a state the definition does not declare",
        ),
        (
            {"state": "Draft", "reason": "case"},
            "`state` names a state the definition does not declare",
        ),
        (
            {"state": " draft", "reason": "space"},
            "`state` names a state the definition does not declare",
        ),
        (
            {"state": "draft\n", "reason": "newline"},
            "`state` names a state the definition does not declare",
        ),
    ],
)
def test_an_unreadable_answer_leaves_every_state_indeterminate(
    repo: Path, answer: dict[str, Any], why: str
) -> None:
    _answer(repo, "classify", answer)
    position = _engine(repo).resolve_position()
    assert position.state_id is None
    assert position.indeterminate is True
    assert list(position.unevaluated) == ["draft", "ready", "done"]
    quoted = json.dumps(answer, sort_keys=True, ensure_ascii=False)
    expected = (
        f"couldn't read the answer of detection predicate 'classify': {why}; it answered {quoted}"
    )
    assert {o.reason for o in position.unevaluated.values()} == {expected}


def test_an_unreadable_answer_is_quoted_bounded_and_made_safe(repo: Path) -> None:
    # A right-to-left override and an escape sequence could rewrite the
    # operator's terminal; a long answer could flood it.
    _answer(repo, "classify", {"state": "‮draft\u001b[2J" + "x" * 4000, "reason": "r"})
    reason = _engine(repo).resolve_position().unevaluated["draft"].reason
    assert "‮" not in reason
    assert "\u001b" not in reason
    assert "…" in reason  # cut to its tail
    assert len(reason.encode("utf-8")) < 1700


@pytest.mark.parametrize(
    "answer",
    [
        {"result": True, "reason": "x"},
        {"state": "parked", "result": True, "reason": "x"},
        {"state": None, "result": True},
        {"state": None, "result": True, "reason": " "},
    ],
)
def test_a_result_beside_an_unreadable_state_is_not_fallen_back_on(
    repo: Path, answer: dict[str, Any]
) -> None:
    # Read by `result`, each would place the subject in `draft`, the first
    # declared state.
    _answer(repo, "classify", answer)
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == (None, True)
    assert list(position.unevaluated) == ["draft", "ready", "done"]


def test_a_result_beside_state_is_not_read(repo: Path) -> None:
    # Read by `result`, this answer would place the subject in every state and
    # the first declared — `draft` — would win.
    _answer(repo, "classify", {"state": "ready", "result": True, "reason": "submitted"})
    assert _engine(repo).resolve_position().state_id == "ready"

    _answer(repo, "classify", {"state": None, "result": True, "reason": "parked"})
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == (None, False)


def test_a_classifier_that_gives_no_answer_shows_its_one_cause_once(repo: Path) -> None:
    _refuse(repo, "classify", 2, "[refused] classify: cannot read the work\n→ run `fixture fix`\n")
    cause = "couldn't evaluate detection predicate 'classify': it exited 2"
    said = "[refused] classify: cannot read the work\n→ run `fixture fix`"

    # --json: one entry per state, shape unchanged.
    payload = _status(repo)
    assert payload["position"]["indeterminate"] is True
    assert payload["position"]["unevaluated"] == [
        {"state": state_id, "reason": cause, "stderr_tail": said}
        for state_id in ("draft", "ready", "done")
    ]
    assert _runs(repo, "classify") == 1

    # Narrative: the cause and what the predicate said, once, with its states.
    narrative = strip_ansi(render_status_narrative(_engine(repo), "agent"))
    assert f"couldn't evaluate 'draft', 'ready', 'done': {cause}" in narrative
    assert narrative.count("it exited 2") == 1
    assert narrative.count("the predicate said:") == 1
    assert _runs(repo, "classify") == 2

    # A refusal: the same, once.
    result = _engine(repo).move("ready", "agent")
    assert result.ok is False
    assert result.reason.splitlines() == [
        "position is indeterminate — a detection predicate could not be evaluated; "
        "refusing to move (fail-closed)",
        f"    'draft', 'ready', 'done': {cause}",
        "      the predicate said:",
        "        [refused] classify: cannot read the work",
        "        → run `fixture fix`",
    ]
    assert _runs(repo, "classify") == 3


@pytest.mark.parametrize(
    ("output", "cause"),
    [
        (
            '{"state": "draft", "reason": "a"}{"state": "ready", "reason": "b"}',
            "it printed no JSON document on its standard output",
        ),
        (
            '{"state": "draft", "reason": "a"}\nand then some text\n',
            "it printed no JSON document on its standard output",
        ),
        ('[{"state": "draft", "reason": "a"}]', "it answered with JSON that is not an object"),
        ('"draft"', "it answered with JSON that is not an object"),
        ("", "it printed no JSON document on its standard output"),
    ],
)
def test_output_that_is_not_one_json_object_is_no_answer(
    repo: Path, output: str, cause: str
) -> None:
    _answer_raw(repo, "classify", output)
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == (None, True)
    assert list(position.unevaluated) == ["draft", "ready", "done"]
    assert {o.reason for o in position.unevaluated.values()} == {
        f"couldn't evaluate detection predicate 'classify': {cause}"
    }
    assert _runs(repo, "classify") == 1


def test_a_classifier_that_overruns_is_no_answer(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from project_kit import command_runner

    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    (repo / "_sleep-classify").write_text("", encoding="utf-8")
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == (None, True)
    assert {o.reason for o in position.unevaluated.values()} == {
        "couldn't evaluate detection predicate 'classify': "
        "it did not answer within 1 s and was stopped"
    }
    assert _runs(repo, "classify") == 1


_WILDCARD_TRANSITIONS = (
    _TRANSITIONS
    + """\
    - from: "*"
      to: done
      trigger: abandon
      authorisation: agent-autonomous
      gate:
        kind: deterministic
        predicate:
          run: gate-open
"""
)


def test_a_gated_wildcard_move_from_an_indeterminate_position_runs_no_gate(repo: Path) -> None:
    _use(repo, _definition(_ONE_CLASSIFIER, _WILDCARD_TRANSITIONS))
    _refuse(repo, "classify", 2, "cannot read the work")

    payload = _status(repo)
    assert payload["position"]["indeterminate"] is True
    (abandon,) = [move for move in payload["legal_moves"] if move["trigger"] == "abandon"]
    assert (abandon["allowed"], abandon["indeterminate"]) == (False, True)
    assert abandon["reason"] == (
        "position is indeterminate — a detection predicate could not be evaluated; "
        "refusing to move (fail-closed)"
    )
    assert _runs(repo, "gate-open") == 0

    narrative = strip_ansi(render_status_narrative(_engine(repo), "agent"))
    assert "? done  [abandon]" in narrative
    assert "✓ done" not in narrative
    assert _runs(repo, "gate-open") == 0

    allowed, _reason, _position = _engine(repo).can_move("done", "agent")
    assert allowed is False
    assert _runs(repo, "gate-open") == 0


# --- one mode per definition (COR-033 point 5, ADR-062 points 7 and 9) ----

_MIXED: list[State] = [
    ("draft", "classified", "classify", None),
    ("ready", "classified", "classify", None),
    ("done", "inferred", "detect-done", None),
]


def test_a_definition_that_mixes_modes_runs_no_detection(repo: Path) -> None:
    _use(repo, _definition(_MIXED))
    # Read alone, `detect-done` would place the subject in `done`.
    _answer(repo, "detect-done", {"result": True, "reason": "closed"})

    position = _engine(repo).resolve_position()
    assert position.state_id is None
    assert position.indeterminate is True
    assert _runs(repo, "classify") == 0
    assert _runs(repo, "detect-done") == 0
    reasons = {o.reason for o in position.unevaluated.values()}
    assert list(position.unevaluated) == ["draft", "ready", "done"]
    assert reasons == {
        "the definition's states declare more than one detection mode — 'classified' by "
        "'draft', 'ready'; 'inferred' by 'done' — so no detection was run; every state of a "
        "definition declares the same mode"
    }

    narrative = strip_ansi(render_status_narrative(_engine(repo), "agent"))
    assert narrative.count("more than one detection mode") == 1
    assert "couldn't evaluate 'draft', 'ready', 'done': the definition's states" in narrative

    allowed, reason, _position = _engine(repo).can_move("ready", "agent")
    assert allowed is False
    assert reason.count("more than one detection mode") == 1


@pytest.mark.parametrize(
    ("states", "described"),
    [
        (
            [
                ("draft", "inferred", "classify", None),
                ("ready", "inferred", "classify", None),
                ("review", "inferred", "classify", None),
                ("held", "inferred", "classify", None),
                ("done", "clasified", "classify", None),
            ],
            "'inferred' by 'draft', 'ready', 'review', 'held'; 'clasified' by 'done'",
        ),
        (
            [
                ("draft", "classified", "classify", None),
                ("ready", "classified", "classify", None),
                ("done", None, "classify", None),
            ],
            "'classified' by 'draft', 'ready'; no mode by 'done'",
        ),
    ],
)
def test_a_typod_or_missing_mode_mixes_the_modes(
    repo: Path, states: list[State], described: str
) -> None:
    _use(repo, _definition(states))
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == (None, True)
    assert _runs(repo, "classify") == 0
    assert {o.reason for o in position.unevaluated.values()} == {
        f"the definition's states declare more than one detection mode — {described} — so no "
        "detection was run; every state of a definition declares the same mode"
    }
    (finding,) = definitions_outcome(repo).findings
    assert described in finding.message


def test_a_state_with_no_detection_declares_no_mode(repo: Path) -> None:
    _use(
        repo,
        _definition(
            [
                ("draft", "classified", "classify", None),
                ("ready", "classified", "classify", None),
                ("done", None, None, None),
            ]
        ),
    )
    assert definitions_outcome(repo).findings == ()
    _answer(repo, "classify", {"state": "ready", "reason": "submitted"})
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == ("ready", False)
    assert set(position.detection_reasons) == {"draft", "ready"}
    assert _runs(repo, "classify") == 1


def test_validation_reports_a_definition_that_mixes_modes(repo: Path) -> None:
    assert definitions_outcome(repo).findings == ()

    _use(repo, _definition(_MIXED))
    findings = definitions_outcome(repo).findings
    assert [(f.location, f.severity.value) for f in findings] == [
        (".pkit/capabilities/fixture/schemas/demo.yaml", "error")
    ]
    assert findings[0].message == (
        "process fixture:demo: its states declare more than one detection mode — "
        "'classified' by 'draft', 'ready'; 'inferred' by 'done'; every state of a definition "
        "declares the same mode"
    )


def test_validation_reports_one_command_under_different_with_mappings(repo: Path) -> None:
    _use(
        repo,
        _definition(
            [
                ("draft", "classified", "classify", {"variant": "early"}),
                ("ready", "classified", "classify", {"variant": "early"}),
                ("done", "classified", "classify", None),
            ]
        ),
    )
    findings = definitions_outcome(repo).findings
    assert len(findings) == 1
    assert findings[0].message == (
        "process fixture:demo: its `classified` detections name command 'classify' under 2 "
        "different `with` mappings ('draft', 'ready'; 'done'); they are separate classifiers "
        "that the runner gives the same input, so an answer one of them can read is "
        "unreadable for the other"
    )


def test_one_command_under_two_with_mappings_runs_as_two_classifiers(repo: Path) -> None:
    # Invalid (validation reports it, above); at run time each is a classifier
    # of its own, with only its own states, given the same input.
    _use(
        repo,
        _definition(
            [
                ("draft", "classified", "classify", {"variant": "early"}),
                ("ready", "classified", "classify", {"variant": "early"}),
                ("done", "classified", "classify", {"variant": "late"}),
            ]
        ),
    )
    position = _engine(repo).resolve_position()
    assert _runs(repo, "classify") == 2
    # `draft` is the early classifier's; for the late one it names another
    # classifier's state, so `done` is indeterminate — and `draft` still wins.
    assert (position.state_id, position.indeterminate) == ("draft", False)
    assert list(position.unevaluated) == ["done"]
    assert "`state` names a state another predicate detects" in (
        position.unevaluated["done"].reason
    )

    _answer(repo, "classify", {"state": "done", "reason": "finished"})
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == ("done", False)
    assert list(position.unevaluated) == ["draft", "ready"]


def test_a_mode_this_engine_does_not_implement_resolves_no_position(repo: Path) -> None:
    _use(
        repo, _definition([(sid, "stored", "classify", None) for sid in ("draft", "ready", "done")])
    )
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == (None, True)
    assert _runs(repo, "classify") == 0
    assert {o.reason for o in position.unevaluated.values()} == {
        "detection mode 'stored' is not implemented by this engine "
        "(it implements 'inferred', 'classified')"
    }
    assert _engine(repo).move("ready", "agent").ok is False


# --- the reading lives in position resolution alone (ADR-062 point 5) -----

_STATE_ONLY_TRANSITIONS = """\
  transitions:
    - from: draft
      to: ready
      trigger: submit
      authorisation: agent-autonomous
      gate:
        kind: deterministic
        predicate:
          run: gate-state-only
"""

_STATE_ONLY_EXTRA = """\
  invariants:
    - id: state-only
      check:
        run: check-state-only
      why: An answer carrying only a state.
"""

_STATE_ONLY_BLOCKED = """\
    blocked:
      blocked_on: awaiting-condition
      resume_when:
        run: resume-state-only
"""


def test_a_state_in_other_predicates_answers_is_not_read(repo: Path) -> None:
    definition = _definition(_ONE_CLASSIFIER, _STATE_ONLY_TRANSITIONS, _STATE_ONLY_EXTRA)
    definition = definition.replace(
        "    cardinality: singleton\n", "    cardinality: singleton\n" + _STATE_ONLY_BLOCKED
    )
    _use(repo, definition)
    for name in ("gate-state-only", "check-state-only", "resume-state-only"):
        _answer(repo, name, {"state": "ready", "reason": "only a state"})

    engine = _engine(repo)
    position = engine.resolve_position()
    assert position.state_id == "draft"

    # A gate: read by `result`, absent — a closed gate, not an indeterminate one.
    (submit,) = engine.precheck_transitions("draft", "agent")
    assert (submit.allowed, submit.indeterminate) == (False, False)
    # An invariant's check: does not hold, determinately.
    (invariant,) = engine.evaluate_invariants()
    assert (invariant.holds, invariant.indeterminate) == (False, False)
    # A resume_when: not yet holding, so the wait stays.
    blocked = engine.evaluate_blocked(position, [submit], "agent")
    assert blocked is not None
    assert blocked.resume_reason == "only a state"


# --- several classifiers (ADR-062 point 6) --------------------------------

_TWO_CLASSIFIERS: list[State] = [
    ("draft", "classified", "classify", None),
    ("ready", "classified", "classify", None),
    ("review", "classified", "classify-other", None),
    ("done", "classified", "classify-other", None),
]


def test_two_classifiers_placing_the_subject_resolve_to_the_earlier_state(repo: Path) -> None:
    _use(repo, _definition(_TWO_CLASSIFIERS))
    _answer(repo, "classify", {"state": "ready", "reason": "submitted"})
    _answer(repo, "classify-other", {"state": "review", "reason": "in review"})
    assert _engine(repo).resolve_position().state_id == "ready"

    _answer(repo, "classify", {"state": None, "reason": "not mine"})
    _answer(repo, "classify-other", {"state": "done", "reason": "closed"})
    assert _engine(repo).resolve_position().state_id == "done"


def test_a_failing_classifier_holds_the_position_only_when_no_state_is_true(repo: Path) -> None:
    _use(repo, _definition(_TWO_CLASSIFIERS))
    _refuse(repo, "classify", 2, "cannot read")
    _answer(repo, "classify-other", {"state": "review", "reason": "in review"})
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == ("review", False)
    assert set(position.unevaluated) == {"draft", "ready"}

    _answer(repo, "classify-other", {"state": None, "reason": "not mine"})
    position = _engine(repo).resolve_position()
    assert (position.state_id, position.indeterminate) == (None, True)


def test_a_classifier_naming_another_classifiers_state_is_unreadable(repo: Path) -> None:
    _use(repo, _definition(_TWO_CLASSIFIERS))
    _answer(repo, "classify", {"state": "review", "reason": "thinks it is in review"})
    _answer(repo, "classify-other", {"state": None, "reason": "not in review"})
    position = _engine(repo).resolve_position()
    # It does not make `review` true; its own states are indeterminate.
    assert (position.state_id, position.indeterminate) == (None, True)
    assert set(position.unevaluated) == {"draft", "ready"}
    assert "`state` names a state another predicate detects" in (
        position.unevaluated["draft"].reason
    )


# --- an `inferred` definition is read as before (ADR-062 point 4) ---------


def test_a_classifiers_command_in_an_inferred_definition_reads_false(repo: Path) -> None:
    _use(
        repo,
        _definition([(sid, "inferred", "classify", None) for sid in ("draft", "ready", "done")]),
    )
    _answer(repo, "classify", {"state": "draft", "reason": "the work says draft"})
    position = _engine(repo).resolve_position()
    # The limit point 4 names: a determinate "no position", read by `result`.
    assert (position.state_id, position.indeterminate) == (None, False)
    assert position.placed_nowhere == ()
    assert _runs(repo, "classify") == 1  # the memo is shared under `inferred` too
    assert _status(repo)["position"]["placed_nowhere"] == []


# --- a cascade member is resolved afresh each time (ADR-062 point 11) -----

_ITEM = """\
process:
  id: item
  version: 1
  subject:
    cardinality: keyed
    key: item-id
  states:
    - id: open
      meaning: Being worked.
      detection:
        mode: classified
        predicate:
          run: classify-item
    - id: closed
      meaning: Finished.
      terminal: true
      detection:
        mode: classified
        predicate:
          run: classify-item
  transitions: []
"""

# The parent folds its items; it detects in `inferred` — each definition is
# read by its own mode (ADR-062 point 1).
_AREA = """\
process:
  id: area
  version: 1
  subject:
    cardinality: keyed
    key: area-id
  cascade:
    runs: fixture:item
    members:
      run: area-items
    membership:
      run: item-member
    reducer:
      op: all
      outcome: closed
  states:
    - id: collecting
      meaning: Items are being worked.
      detection:
        mode: inferred
        predicate:
          run: area-collecting
    - id: complete
      meaning: Every item finished.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: area-complete
  transitions:
    - from: collecting
      to: complete
      trigger: close
      authorisation: agent-autonomous
      gate:
        kind: cascade-outcome
"""

_CLASSIFY_ITEM = (
    "import pathlib, sys\n"
    "subject = sys.argv[1]\n"
    "with open(f'_runs-item-{subject}', 'a') as fh:\n"
    "    fh.write('run\\n')\n"
    "sys.stdout.write(pathlib.Path(f'_item-{subject}').read_text())\n"
)


@pytest.fixture
def cascade_repo(repo: Path) -> Path:
    cap = _cap(repo)
    extra = {
        "classify-item": _CLASSIFY_ITEM,
        "area-items": _answering("area-items"),
        "item-member": _answering("item-member"),
        "area-collecting": _answering("area-collecting"),
        "area-complete": _answering("area-complete"),
    }
    package = (cap / "package.yaml").read_text(encoding="utf-8")
    package += "".join(
        f"  {name}:\n    script: scripts/{name}.py\n    help: {name}\n" for name in extra
    )
    (cap / "package.yaml").write_text(package, encoding="utf-8")
    for name, body in extra.items():
        _write_script(cap / "scripts" / f"{name}.py", body)
    (cap / "schemas" / "item.yaml").write_text(_ITEM, encoding="utf-8")
    (cap / "schemas" / "area.yaml").write_text(_AREA, encoding="utf-8")

    _answer(repo, "area-items", {"members": ["m1", "m2"], "reason": "two items"})
    _answer(repo, "item-member", {"result": True, "reason": "an item of this area"})
    _answer(repo, "area-collecting", {"result": True, "reason": "collecting"})
    _answer(repo, "area-complete", {"result": False, "reason": "not complete"})
    for member in ("m1", "m2"):
        (repo / f"_item-{member}").write_text(
            json.dumps({"state": "closed", "reason": "finished"}), encoding="utf-8"
        )
    return repo


def _area(repo: Path) -> ProcessEngine:
    return ProcessEngine(load_definition(repo, "fixture:area"), repo, subject="a1")


def test_a_cascade_member_runs_its_classifier_once_per_resolution(cascade_repo: Path) -> None:
    engine = _area(cascade_repo)
    fold = engine.resolve_cascade_outcome()
    assert fold is not None
    assert (fold.opened, fold.total, fold.reached) == (True, 2, 2)
    assert (_runs(cascade_repo, "item-m1"), _runs(cascade_repo, "item-m2")) == (1, 1)

    # One invocation may resolve a member again: a fresh memo, one more run.
    engine.resolve_cascade_outcome()
    assert (_runs(cascade_repo, "item-m1"), _runs(cascade_repo, "item-m2")) == (2, 2)


def test_a_membership_answer_carrying_only_a_state_excludes_the_candidate(
    cascade_repo: Path,
) -> None:
    _answer(cascade_repo, "item-member", {"state": "closed", "reason": "only a state"})
    fold = _area(cascade_repo).resolve_cascade_outcome()
    assert fold is not None
    # Read by `result`, absent: a determinate non-member, never folded.
    assert (fold.total, fold.indeterminate, fold.opened) == (0, False, False)
    assert _runs(cascade_repo, "item-m1") == 0
