"""Engine tests for the COR-034 blocked / human-pause overlay.

Two fixtures, one per blocked reason, deliberately wiring the move's exit gate
and (for awaiting-condition) the `resume_when` predicate to DIFFERENT facts so
the two clearing paths can be shown to diverge — the meta-finding behind the
critic's R1 blocker. The old fixtures wired gate and resume_when to the SAME
fact, hiding the bug where an awaiting-human block consulted a side-predicate.

`pause-demo` (awaiting-human): its `parked` state has one outgoing move — a
`user` `approve` move gated by an authorisation artifact, carrying a prompt.
There is NO `resume_when`: the block is live while parked with that move not
yet taken, and resumes only when the move is TAKEN (position advances off
`parked`). A side-fact (a review file) does NOT clear it.

`condition-demo` (awaiting-condition): its `waiting` state has one outgoing
`script` move whose gate and the subject's `resume_when` read DIFFERENT facts.
The block clears via `resume_when` turning true, with no human in the loop.

A third fixture (`both-demo`) covers the COR-034 R2 rule: a state with BOTH a
`user` move and an `agent-autonomous` move. Awaiting-human is live only while
the human is the SOLE way forward — so an available (gate-open) autonomous move
suppresses it, while a gate-closed one (no real escape) does not.

Covers: per-reason live detection, the gate-closed→intervene→take path, the
awaiting-human side-fact NON-clear (the dead bug), the both-moves
autonomous-escape rule (R2), awaiting-condition divergence (both directions),
journaling blocked-enter at PARK time (G2), live-over-journal authority, prompt
surfacing, and the behaviour-preserving block-less case.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from project_kit.process import (
    ProcessEngine,
    load_definition,
    render_status_json,
    render_status_narrative,
)

# awaiting-human: `parked` has one outgoing move — a `user` approve gated by an
# authorisation artifact, carrying a prompt. NO `resume_when` (forbidden for
# awaiting-human): the wait is live while parked with the approve move not yet
# taken, and clears only when the move is taken (position leaves `parked`).
_DEFINITION = """\
process:
  id: pause-demo
  version: 1
  subject:
    cardinality: singleton
    domain_ref: fixture
    blocked:
      blocked_on: awaiting-human
      assignee: the-reviewer
  states:
    - id: open
      meaning: Work in progress.
      detection:
        mode: inferred
        predicate:
          run: detect-open
    - id: parked
      meaning: Parked awaiting a human reviewer.
      detection:
        mode: inferred
        predicate:
          run: detect-parked
    - id: done
      meaning: Complete.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-done
  transitions:
    - from: open
      to: parked
      trigger: park
      authorisation: agent-autonomous
    - from: parked
      to: done
      trigger: approve
      authorisation: user
      gate:
        kind: authorisation-artifact
        predicate:
          run: gate-review
      why: Approve once a reviewer has signed off.
      prompt: Approve this work, or send it back?
"""


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_defs(pkit: Path) -> None:
    defs_dst = pkit / "schemas" / "_defs"
    defs_dst.mkdir(parents=True, exist_ok=True)
    source_defs = (
        Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
    )
    defs_dst.joinpath("process.schema.json").write_text(
        source_defs.read_text(encoding="utf-8"), encoding="utf-8"
    )


@pytest.fixture
def paused_repo(tmp_path: Path) -> Path:
    """A repo with a fixture capability declaring an awaiting-human wait.

    Position marker: `_state` (open|parked|done). Review artifact: `_review`
    JSON `{by: <login>}`; when present, the approve gate reports it. There is
    NO resume_when — the wait resumes only when the approve move is taken
    (`_state` advances off `parked`).
    """
    repo = tmp_path
    pkit = repo / ".pkit"
    _install_defs(pkit)

    cap = pkit / "capabilities" / "fixture"
    scripts = cap / "scripts"
    cap.mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        """schema_version: 2
component:
  kind: capability
  name: fixture
  version: 0.1.0
description: Blocked-overlay fixture capability.
commands:
  detect-open:
    script: scripts/detect_open.py
    help: detect open
  detect-parked:
    script: scripts/detect_parked.py
    help: detect parked
  detect-done:
    script: scripts/detect_done.py
    help: detect done
  gate-review:
    script: scripts/gate_review.py
    help: review gate
""",
        encoding="utf-8",
    )
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "pause-demo.yaml").write_text(_DEFINITION, encoding="utf-8")

    (repo / "_state").write_text("open", encoding="utf-8")

    def _detect(state_name: str) -> str:
        return (
            "import json, sys, pathlib\n"
            "cur = pathlib.Path('_state').read_text().strip()\n"
            f"print(json.dumps({{'result': cur == {state_name!r}, "
            "'reason': f'marker is {cur!r}'}))\n"
        )

    _write_script(scripts / "detect_open.py", _detect("open"))
    _write_script(scripts / "detect_parked.py", _detect("parked"))
    _write_script(scripts / "detect_done.py", _detect("done"))

    # Authorisation-artifact gate: {exists, produced_by} from `_review`.
    _write_script(
        scripts / "gate_review.py",
        "import json, sys, pathlib\n"
        "p = pathlib.Path('_review')\n"
        "if p.exists():\n"
        "    print(json.dumps({'exists': True, 'produced_by': json.loads(p.read_text())['by'],\n"
        "                      'reason': 'verdict present'}))\n"
        "else:\n"
        "    print(json.dumps({'exists': False, 'reason': 'no verdict'}))\n",
    )
    return repo


def _set_state(repo: Path, state: str) -> None:
    (repo / "_state").write_text(state, encoding="utf-8")


def _engine(repo: Path) -> ProcessEngine:
    return ProcessEngine(load_definition(repo, "fixture:pause-demo"), repo)


def _live_blocked(repo: Path, actor: str = "agent"):
    engine = _engine(repo)
    position = engine.resolve_position()
    checks = engine.precheck_transitions(position.state_id, actor)
    return engine.evaluate_blocked(position, checks, actor)


# --- awaiting-human: live detection + resume-is-the-move ------------------


def test_not_blocked_when_open_has_no_pending_human_move(paused_repo: Path) -> None:
    # `open`'s only outgoing move is the agent-autonomous `park` — no `user`
    # move ahead, so the subject is not awaiting a person.
    _set_state(paused_repo, "open")
    assert _live_blocked(paused_repo) is None


def test_blocked_when_parked_awaiting_human_move(paused_repo: Path) -> None:
    # In `parked` the only move is the `user` approve, not yet taken -> the
    # subject is awaiting a person, regardless of the gate.
    _set_state(paused_repo, "parked")
    blocked = _live_blocked(paused_repo)
    assert blocked is not None
    assert blocked.blocked_on == "awaiting-human"
    assert blocked.at == "parked"
    assert blocked.assignee == "the-reviewer"


def test_terminal_position_is_not_blocked(paused_repo: Path) -> None:
    # `done` is terminal: no move out, but that is *done*, not stuck.
    _set_state(paused_repo, "done")
    assert _live_blocked(paused_repo) is None


# --- THE DEAD BUG: a side-fact must NOT clear an awaiting-human block ------


def test_side_fact_does_not_clear_awaiting_human_while_move_untaken(paused_repo: Path) -> None:
    # The exact bug COR-034's R1 kills: a review file exists (the approve gate
    # is now OPEN — the move is ready to take), but the human has NOT taken it.
    # The subject is STILL blocked: awaiting-human consults no side-predicate;
    # only taking the move resumes it.
    _set_state(paused_repo, "parked")
    (paused_repo / "_review").write_text(json.dumps({"by": "bob"}), encoding="utf-8")

    blocked = _live_blocked(paused_repo)
    assert blocked is not None, "a side-fact must NOT clear an awaiting-human block"
    assert blocked.blocked_on == "awaiting-human"
    # The approve move is now gate-open (ready) but still pending.
    engine = _engine(paused_repo)
    pos = engine.resolve_position()
    approve = next(c for c in engine.precheck_transitions(pos.state_id, "agent") if c.to == "done")
    assert approve.allowed, "gate should be open (review present) yet the wait persists"


def test_awaiting_human_clears_only_when_move_is_taken(paused_repo: Path) -> None:
    # Take the move: with the review present the gate passes; the move lands the
    # subject at `done`. Position advancing off `parked` removes the pending
    # `user` move -> the wait clears.
    _set_state(paused_repo, "parked")
    (paused_repo / "_review").write_text(json.dumps({"by": "bob"}), encoding="utf-8")

    # Journal the enter first (park-time), then take the move.
    enter = _engine(paused_repo).reconcile_blocked(actor="agent", assume_state="parked")
    assert enter is not None and enter["event"] == "blocked-enter"

    result = _engine(paused_repo).move("done", actor="user")
    assert result.ok is True
    # The move's reconcile (against target `done`, terminal) clears the wait.
    resume = [
        e for e in _engine(paused_repo).read_journal() if e.get("event") == "blocked-resume"
    ]
    assert resume, "taking the move must journal blocked-resume"
    assert resume[-1]["blocked_on"] == "awaiting-human"

    # And once at `done` the live overlay is None.
    _set_state(paused_repo, "done")
    assert _live_blocked(paused_repo) is None


# --- awaiting-human: gate-closed -> intervene -> take ---------------------


def test_gate_closed_then_intervene_then_take(paused_repo: Path) -> None:
    # Gate-closed: no review yet, so the approve gate refuses. The subject is
    # STILL awaiting-human (a person must intervene in reality, then take it).
    _set_state(paused_repo, "parked")
    blocked = _live_blocked(paused_repo)
    assert blocked is not None and blocked.blocked_on == "awaiting-human"
    engine = _engine(paused_repo)
    pos = engine.resolve_position()
    approve = next(c for c in engine.precheck_transitions(pos.state_id, "agent") if c.to == "done")
    assert not approve.allowed, "gate is closed (no review) — the move is not yet takeable"

    # Reality amended (the human files the review) so the gate opens — but the
    # move is not yet taken, so the subject is STILL blocked.
    (paused_repo / "_review").write_text(json.dumps({"by": "bob"}), encoding="utf-8")
    assert _live_blocked(paused_repo) is not None, "gate opening does not by itself resume"

    # The human takes the move -> position advances off `parked` -> clears.
    assert _engine(paused_repo).move("done", actor="user").ok is True
    _set_state(paused_repo, "done")
    assert _live_blocked(paused_repo) is None


# --- journaling: blocked-enter at PARK time (G2) --------------------------


def test_move_into_parked_journals_blocked_enter_at_park_time(paused_repo: Path) -> None:
    # G2: the move into `parked` reconciles against its TARGET state, so the
    # blocked-enter is journaled AT PARK TIME — even though reality (the `_state`
    # marker the wrapper would update) still reads `open` at the instant of the
    # move. This makes `since` meaningful for the stuck-work view immediately,
    # not lazily once the human finally acts.
    _set_state(paused_repo, "open")
    result = _engine(paused_repo).move("parked", actor="agent")
    assert result.ok is True

    # Reality is still `open` (the wrapper has not applied the side-effect), yet
    # the enter was journaled at park time against the target.
    assert (paused_repo / "_state").read_text().strip() == "open"
    journal = _engine(paused_repo).read_journal()
    enters = [e for e in journal if e.get("event") == "blocked-enter"]
    assert enters, "park-time blocked-enter must be journaled by the move itself"
    enter = enters[-1]
    assert enter["blocked_on"] == "awaiting-human"
    assert enter["at"] == "parked"
    assert enter["assignee"] == "the-reviewer"


def test_park_time_enter_is_idempotent(paused_repo: Path) -> None:
    # A second reconcile while still parked-and-blocked is a no-op.
    _set_state(paused_repo, "open")
    assert _engine(paused_repo).move("parked", actor="agent").ok is True
    _set_state(paused_repo, "parked")
    assert _engine(paused_repo).reconcile_blocked(actor="agent") is None


def test_since_read_from_open_enter_entry(paused_repo: Path) -> None:
    _set_state(paused_repo, "open")
    assert _engine(paused_repo).move("parked", actor="agent").ok is True
    _set_state(paused_repo, "parked")
    journal = _engine(paused_repo).read_journal()
    enter = next(e for e in journal if e.get("event") == "blocked-enter")
    blocked = _live_blocked(paused_repo)
    assert blocked is not None
    assert blocked.since == enter["ts"]


# --- prompt surfacing on both renderings ----------------------------------


def test_prompt_surfaces_on_json_status(paused_repo: Path) -> None:
    _set_state(paused_repo, "parked")
    payload = json.loads(render_status_json(_engine(paused_repo), actor="agent"))
    assert payload["blocked"]["blocked_on"] == "awaiting-human"
    assert payload["blocked"]["prompt"] == "Approve this work, or send it back?"
    approve = next(m for m in payload["legal_moves"] if m["to"] == "done")
    assert approve["prompt"] == "Approve this work, or send it back?"


def test_prompt_surfaces_on_narrative_status(paused_repo: Path) -> None:
    _set_state(paused_repo, "parked")
    text = render_status_narrative(_engine(paused_repo), actor="agent")
    assert "Blocked: awaiting-human" in text
    assert "Approve this work, or send it back?" in text


def test_json_blocked_is_null_when_not_blocked(paused_repo: Path) -> None:
    _set_state(paused_repo, "open")
    payload = json.loads(render_status_json(_engine(paused_repo), actor="agent"))
    assert payload["blocked"] is None


def test_status_render_is_read_only(paused_repo: Path) -> None:
    # Rendering status (which evaluates the blocked overlay) must NOT journal.
    _set_state(paused_repo, "parked")
    render_status_json(_engine(paused_repo), actor="agent")
    render_status_narrative(_engine(paused_repo), actor="agent")
    assert not _engine(paused_repo).read_journal(), "status must not write the journal"


# --- awaiting-condition: divergence (gate vs resume_when) -----------------

# DIVERGENCE: the `verify` move's exit gate reads `_gate`, while the subject's
# `resume_when` reads `_window`. The two facts are independent, so the clearing
# paths can disagree. awaiting-condition clears via `resume_when` (`_window`),
# never via the gate.
_CONDITION_DEFINITION = """\
process:
  id: condition-demo
  version: 1
  subject:
    cardinality: singleton
    blocked:
      blocked_on: awaiting-condition
      resume_when:
        run: window-open
  states:
    - id: waiting
      meaning: Awaiting an external window.
      detection:
        mode: inferred
        predicate:
          run: detect-waiting
    - id: verified
      meaning: Window opened, verified.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-verified
  transitions:
    - from: waiting
      to: verified
      trigger: verify
      authorisation: script
      gate:
        kind: deterministic
        predicate:
          run: gate-open
"""


@pytest.fixture
def condition_repo(tmp_path: Path) -> Path:
    repo = tmp_path
    pkit = repo / ".pkit"
    _install_defs(pkit)
    cap = pkit / "capabilities" / "fixture"
    scripts = cap / "scripts"
    cap.mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        """schema_version: 2
component:
  kind: capability
  name: fixture
  version: 0.1.0
description: awaiting-condition fixture.
commands:
  detect-waiting:
    script: scripts/detect_waiting.py
    help: detect waiting
  detect-verified:
    script: scripts/detect_verified.py
    help: detect verified
  window-open:
    script: scripts/window_open.py
    help: resume_when predicate (reads _window)
  gate-open:
    script: scripts/gate_open.py
    help: exit gate predicate (reads _gate)
""",
        encoding="utf-8",
    )
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "condition-demo.yaml").write_text(_CONDITION_DEFINITION, encoding="utf-8")
    (repo / "_state").write_text("waiting", encoding="utf-8")

    def _detect(state_name: str) -> str:
        return (
            "import json, pathlib\n"
            "cur = pathlib.Path('_state').read_text().strip()\n"
            f"print(json.dumps({{'result': cur == {state_name!r}, 'reason': cur}}))\n"
        )

    _write_script(scripts / "detect_waiting.py", _detect("waiting"))
    _write_script(scripts / "detect_verified.py", _detect("verified"))
    # resume_when reads `_window`; the exit gate reads a DIFFERENT fact `_gate`.
    _write_script(
        scripts / "window_open.py",
        "import json, pathlib\n"
        "ok = pathlib.Path('_window').exists()\n"
        "print(json.dumps({'result': ok, 'reason': 'open' if ok else 'window not yet open'}))\n",
    )
    _write_script(
        scripts / "gate_open.py",
        "import json, pathlib\n"
        "ok = pathlib.Path('_gate').exists()\n"
        "print(json.dumps({'result': ok, 'reason': 'gate open' if ok else 'gate closed'}))\n",
    )
    return repo


def _condition_live(repo: Path):
    engine = ProcessEngine(load_definition(repo, "fixture:condition-demo"), repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "script")
    return engine.evaluate_blocked(pos, checks, "script")


def test_awaiting_condition_clears_via_resume_when_not_gate(condition_repo: Path) -> None:
    # Both facts absent: no legal move (gate closed) + resume_when false -> blocked.
    blocked = _condition_live(condition_repo)
    assert blocked is not None
    assert blocked.blocked_on == "awaiting-condition"
    assert blocked.prompt is None  # no human, no question

    # DIVERGENCE: resume_when (`_window`) true, but the gate (`_gate`) is still
    # closed. awaiting-condition clears via resume_when regardless of the gate.
    (condition_repo / "_window").write_text("", encoding="utf-8")
    assert _condition_live(condition_repo) is None, "resume_when true must clear it"


def test_awaiting_condition_no_legal_move_exit_when_gate_open(condition_repo: Path) -> None:
    # The CONVERSE divergence, tested honestly: open the exit gate (`_gate`)
    # while `resume_when` (`_window`) is still false. A legal move now exists,
    # so `has_no_legal_move` is False and the awaiting-condition block lifts via
    # its "no legal move" exit — even though `resume_when` never held. (The
    # `script` move is now autonomously takeable; the subject is no longer
    # parked-with-no-move.)
    assert not (condition_repo / "_window").exists(), "resume_when fact must be false"
    (condition_repo / "_gate").write_text("", encoding="utf-8")  # exit gate open
    assert (
        _condition_live(condition_repo) is None
    ), "gate open => legal move exists => not blocked, regardless of resume_when"


def test_awaiting_condition_stays_blocked_while_gate_closed_and_window_shut(
    condition_repo: Path,
) -> None:
    # Both facts false: gate closed (no legal move) AND resume_when false. The
    # subject stays blocked until one of them flips. Asserts resume_when, not a
    # stale flag, is the live decider: set then clear the window and confirm the
    # block returns.
    (condition_repo / "_window").write_text("", encoding="utf-8")  # resume cond true
    assert _condition_live(condition_repo) is None, "window open -> clears"
    (condition_repo / "_window").unlink()  # resume cond false again
    assert _condition_live(condition_repo) is not None, "no window, gate closed -> still blocked"


def test_awaiting_condition_indeterminate_resume_fails_closed(condition_repo: Path) -> None:
    # Make resume_when indeterminate (the command errors): fail-closed -> stays
    # blocked rather than silently resuming.
    scripts = condition_repo / ".pkit" / "capabilities" / "fixture" / "scripts"
    _write_script(scripts / "window_open.py", "import sys\nsys.exit(3)\n")
    blocked = _condition_live(condition_repo)
    assert blocked is not None, "indeterminate resume_when must fail closed (stay blocked)"


# --- R2: a state with BOTH a user move and an autonomous move --------------

# COR-034 awaiting-human rule: the block is live only while the subject's SOLE
# forward progress is an untaken `user` move — i.e. NO autonomous move the
# engine could take instead is currently allowed. `both` has BOTH an outgoing
# `user` `approve` move and an `agent-autonomous` `auto-advance` move gated on
# `_auto`. `solo` has ONLY the `user` move. The autonomous move's gate is
# toggled by the `_auto` marker file to show the gate-open vs gate-closed split.
_BOTH_MOVES_DEFINITION = """\
process:
  id: both-demo
  version: 1
  subject:
    cardinality: singleton
    blocked:
      blocked_on: awaiting-human
      assignee: the-reviewer
  states:
    - id: both
      meaning: Both a human move and an autonomous move are outgoing.
      detection:
        mode: inferred
        predicate:
          run: detect-both
    - id: solo
      meaning: Only the human move is outgoing.
      detection:
        mode: inferred
        predicate:
          run: detect-solo
    - id: done
      meaning: Complete.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-done
  transitions:
    - from: both
      to: done
      trigger: approve
      authorisation: user
      prompt: Approve, or wait for auto-advance?
    - from: both
      to: done
      trigger: auto-advance
      authorisation: agent-autonomous
      gate:
        kind: deterministic
        predicate:
          run: gate-auto
    - from: solo
      to: done
      trigger: approve
      authorisation: user
"""


@pytest.fixture
def both_moves_repo(tmp_path: Path) -> Path:
    """A repo whose `both` state has a `user` move AND an `agent-autonomous`
    move gated on `_auto`; `solo` has only the `user` move. Position marker
    `_state` (both|solo|done)."""
    repo = tmp_path
    pkit = repo / ".pkit"
    _install_defs(pkit)
    cap = pkit / "capabilities" / "fixture"
    scripts = cap / "scripts"
    cap.mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        """schema_version: 2
component:
  kind: capability
  name: fixture
  version: 0.1.0
description: both-moves fixture (R2).
commands:
  detect-both:
    script: scripts/detect_both.py
    help: detect both
  detect-solo:
    script: scripts/detect_solo.py
    help: detect solo
  detect-done:
    script: scripts/detect_done.py
    help: detect done
  gate-auto:
    script: scripts/gate_auto.py
    help: autonomous-move gate (reads _auto)
""",
        encoding="utf-8",
    )
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "both-demo.yaml").write_text(_BOTH_MOVES_DEFINITION, encoding="utf-8")
    (repo / "_state").write_text("both", encoding="utf-8")

    def _detect(state_name: str) -> str:
        return (
            "import json, pathlib\n"
            "cur = pathlib.Path('_state').read_text().strip()\n"
            f"print(json.dumps({{'result': cur == {state_name!r}, 'reason': cur}}))\n"
        )

    _write_script(scripts / "detect_both.py", _detect("both"))
    _write_script(scripts / "detect_solo.py", _detect("solo"))
    _write_script(scripts / "detect_done.py", _detect("done"))
    # The autonomous move's gate: open iff `_auto` exists.
    _write_script(
        scripts / "gate_auto.py",
        "import json, pathlib\n"
        "ok = pathlib.Path('_auto').exists()\n"
        "print(json.dumps({'result': ok, 'reason': 'auto open' if ok else 'auto closed'}))\n",
    )
    return repo


def _both_live(repo: Path, actor: str = "agent"):
    engine = ProcessEngine(load_definition(repo, "fixture:both-demo"), repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, actor)
    return engine.evaluate_blocked(pos, checks, actor)


def test_both_moves_gate_open_autonomous_not_awaiting_human(both_moves_repo: Path) -> None:
    # Both moves gate-open: the `user` approve is present AND the autonomous
    # auto-advance is allowed (gate open). The engine can take the autonomous
    # move on its own, so the subject is NOT awaiting a person -> no overlay.
    _set_state(both_moves_repo, "both")
    (both_moves_repo / "_auto").write_text("", encoding="utf-8")  # autonomous gate open
    # Sanity: the autonomous move really is allowed.
    engine = ProcessEngine(load_definition(both_moves_repo, "fixture:both-demo"), both_moves_repo)
    pos = engine.resolve_position()
    auto = next(
        c
        for c in engine.precheck_transitions(pos.state_id, "agent")
        if c.trigger == "auto-advance"
    )
    assert auto.allowed, "autonomous move should be gate-open in this case"
    assert _both_live(both_moves_repo) is None, (
        "an available autonomous move means the engine can advance without a "
        "person -> NOT awaiting-human"
    )


def test_both_moves_autonomous_gate_closed_is_awaiting_human(both_moves_repo: Path) -> None:
    # Autonomous move gate-CLOSED (`_auto` absent) while the `user` move is
    # present. A gate-closed autonomous move is not an escape — the engine
    # cannot take it — so the human is the sole way forward: awaiting-human IS
    # live.
    _set_state(both_moves_repo, "both")
    assert not (both_moves_repo / "_auto").exists(), "autonomous gate must be closed"
    blocked = _both_live(both_moves_repo)
    assert blocked is not None, "gate-closed autonomous move is no escape -> awaiting-human"
    assert blocked.blocked_on == "awaiting-human"
    assert blocked.at == "both"
    assert blocked.prompt == "Approve, or wait for auto-advance?"


def test_solo_state_with_only_user_move_is_awaiting_human(both_moves_repo: Path) -> None:
    # `solo` has only the `user` move — the classic awaiting-human case, as
    # before: the human is the only way forward.
    _set_state(both_moves_repo, "solo")
    blocked = _both_live(both_moves_repo)
    assert blocked is not None
    assert blocked.blocked_on == "awaiting-human"
    assert blocked.at == "solo"


# --- behaviour-preserving: a block-less process never reports blocked ------

_PLAIN_DEFINITION = """\
process:
  id: plain-demo
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: idle
      meaning: Parked with no wait declared.
      detection:
        mode: inferred
        predicate:
          run: detect-idle
    - id: gone
      meaning: Done.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-gone
  transitions:
    - from: idle
      to: gone
      trigger: finish
      authorisation: user
"""


@pytest.fixture
def plain_repo(tmp_path: Path) -> Path:
    repo = tmp_path
    pkit = repo / ".pkit"
    _install_defs(pkit)
    cap = pkit / "capabilities" / "fixture"
    scripts = cap / "scripts"
    cap.mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        """schema_version: 2
component:
  kind: capability
  name: fixture
  version: 0.1.0
description: block-less fixture.
commands:
  detect-idle:
    script: scripts/detect_idle.py
    help: detect idle
  detect-gone:
    script: scripts/detect_gone.py
    help: detect gone
""",
        encoding="utf-8",
    )
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "plain-demo.yaml").write_text(_PLAIN_DEFINITION, encoding="utf-8")
    (repo / "_state").write_text("idle", encoding="utf-8")

    def _detect(state_name: str) -> str:
        return (
            "import json, pathlib\n"
            "cur = pathlib.Path('_state').read_text().strip()\n"
            f"print(json.dumps({{'result': cur == {state_name!r}, 'reason': cur}}))\n"
        )

    _write_script(scripts / "detect_idle.py", _detect("idle"))
    _write_script(scripts / "detect_gone.py", _detect("gone"))
    return repo


def test_blockless_process_never_reports_blocked(plain_repo: Path) -> None:
    # No `blocked` declaration -> the overlay is always None, even at a
    # non-terminal position with a pending user move (no wait was declared).
    engine = ProcessEngine(load_definition(plain_repo, "fixture:plain-demo"), plain_repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    assert engine.evaluate_blocked(pos, checks, "agent") is None
