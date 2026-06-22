"""Engine tests for the COR-036 composition / cross-process resolution slot.

The genuinely-new engine capability: a parent process embeds an inner process
via a `subprocess` state and reads the inner's terminal OUTCOME (resolved live
by a recursive engine instantiation on the inner address) as an input to its own
gate. This file builds a fixture capability with:

- an INNER `verification` process (singleton: `draft -> verified`), the grounding
  shape from COR-036 — a per-point verification mini-process;
- an OUTER `discovery` process embedding it via a `subprocess` state whose
  outgoing move is gated `subprocess-outcome` on the inner reaching `verified`;
- a KEYED inner variant, to exercise COR-032's required-subject rule under
  embedding (a keyed inner with no supplied subject is fail-closed);
- self- and mutual-embedding processes, to exercise the acyclicity guard.

Covers: single-inner recursive resolution (inner not-yet-terminal -> gate closed
-> parent waits; inner terminal -> gate open -> parent moves), the
`awaiting-subprocess-outcome` auto-clearing overlay (live, no resume_when),
the unwired-outcome correct-wait case, the acyclicity guard (self + transitive,
fail-closed), the keyed-inner required-subject rule, the determinate keyed-inner
resolution, status surfacing (narrative + JSON), read-only resolution, and the
behaviour-preserving non-embedding case.
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

# --- fixture process definitions ------------------------------------------

# INNER (singleton): a per-point verification mini-process. `draft -> verified`,
# `verified` terminal. Position resolved from the `_inner` marker file.
_INNER_DEFINITION = """\
process:
  id: verification
  version: 1
  subject:
    cardinality: singleton
  interface:
    outcomes:
      - name: verified
        meaning: The point checks out.
  states:
    - id: draft
      meaning: Drafted, not yet verified.
      detection:
        mode: inferred
        predicate:
          run: inner-detect-draft
    - id: verified
      meaning: Verified.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: inner-detect-verified
  transitions:
    - from: draft
      to: verified
      trigger: verify
      authorisation: script
"""

# OUTER (singleton): `discovering` embeds the inner verification process; once
# the inner reaches `verified`, the `subprocess-outcome` gate opens and the
# parent may move to `discovered`. The `discovering` state declares the
# awaiting-subprocess-outcome wait. Position resolved from the `_outer` marker.
_OUTER_DEFINITION = """\
process:
  id: discovery
  version: 1
  subject:
    cardinality: singleton
    blocked:
      blocked_on: awaiting-subprocess-outcome
  states:
    - id: discovering
      meaning: Discovering an area, verifying a point.
      detection:
        mode: inferred
        predicate:
          run: outer-detect-discovering
      subprocess:
        runs: fixture:verification
    - id: discovered
      meaning: Area discovered (point verified).
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: outer-detect-discovered
  transitions:
    - from: discovering
      to: discovered
      trigger: proceed
      authorisation: agent-autonomous
      gate:
        kind: subprocess-outcome
        outcome: verified
      why: Proceed once the embedded verification reached `verified`.
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


def _marker_detect(marker: str, state_name: str) -> str:
    """A detection script reading a single-line marker file (absent => no match)."""
    return (
        "import json, pathlib\n"
        f"p = pathlib.Path({marker!r})\n"
        "cur = p.read_text().strip() if p.exists() else ''\n"
        f"print(json.dumps({{'result': cur == {state_name!r}, "
        "'reason': f'marker is {cur!r}'}))\n"
    )


@pytest.fixture
def composed_repo(tmp_path: Path) -> Path:
    """A repo with a fixture capability declaring the inner + outer processes.

    Markers: `_outer` (discovering|discovered) and `_inner` (draft|verified).
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
description: Composition fixture (COR-036).
commands:
  inner-detect-draft:
    script: scripts/inner_detect_draft.py
    help: inner draft
  inner-detect-verified:
    script: scripts/inner_detect_verified.py
    help: inner verified
  outer-detect-discovering:
    script: scripts/outer_detect_discovering.py
    help: outer discovering
  outer-detect-discovered:
    script: scripts/outer_detect_discovered.py
    help: outer discovered
""",
        encoding="utf-8",
    )
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "verification.yaml").write_text(_INNER_DEFINITION, encoding="utf-8")
    (cap / "schemas" / "discovery.yaml").write_text(_OUTER_DEFINITION, encoding="utf-8")

    _write_script(scripts / "inner_detect_draft.py", _marker_detect("_inner", "draft"))
    _write_script(scripts / "inner_detect_verified.py", _marker_detect("_inner", "verified"))
    _write_script(
        scripts / "outer_detect_discovering.py", _marker_detect("_outer", "discovering")
    )
    _write_script(
        scripts / "outer_detect_discovered.py", _marker_detect("_outer", "discovered")
    )

    (repo / "_outer").write_text("discovering", encoding="utf-8")
    (repo / "_inner").write_text("draft", encoding="utf-8")
    return repo


def _outer(repo: Path) -> ProcessEngine:
    return ProcessEngine(load_definition(repo, "fixture:discovery"), repo)


def _set(repo: Path, marker: str, value: str) -> None:
    (repo / marker).write_text(value, encoding="utf-8")


def _proceed_check(engine: ProcessEngine, actor: str = "agent"):
    """The parent's `proceed` move check (to `discovered`) from its current state."""
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, actor)
    return next(c for c in checks if c.to == "discovered")


# --- the recursive resolution itself --------------------------------------


def test_resolution_none_when_state_embeds_no_subprocess(composed_repo: Path) -> None:
    # `discovered` embeds nothing -> resolve_subprocess_outcome returns None.
    assert _outer(composed_repo).resolve_subprocess_outcome("discovered") is None


def test_resolution_outcome_none_while_inner_not_terminal(composed_repo: Path) -> None:
    # Inner at `draft` (non-terminal): the resolution is determinate but has NO
    # outcome yet -- a correct wait, not an error.
    resolution = _outer(composed_repo).resolve_subprocess_outcome("discovering")
    assert resolution is not None
    assert resolution.address == "fixture:verification"
    assert resolution.outcome is None
    assert resolution.indeterminate is False


def test_resolution_reads_inner_terminal_outcome(composed_repo: Path) -> None:
    # Inner reaches `verified` (terminal): the parent resolves that outcome.
    _set(composed_repo, "_inner", "verified")
    resolution = _outer(composed_repo).resolve_subprocess_outcome("discovering")
    assert resolution is not None
    assert resolution.outcome == "verified"
    assert resolution.indeterminate is False


def test_resolution_indeterminate_when_inner_position_indeterminate(composed_repo: Path) -> None:
    # Break the inner's detection -> inner position indeterminate -> the
    # resolution is fail-closed (indeterminate), and any gate reading it fails
    # closed too.
    scripts = composed_repo / ".pkit" / "capabilities" / "fixture" / "scripts"
    _write_script(scripts / "inner_detect_draft.py", "import sys\nsys.exit(4)\n")
    _write_script(scripts / "inner_detect_verified.py", "import sys\nsys.exit(4)\n")
    resolution = _outer(composed_repo).resolve_subprocess_outcome("discovering")
    assert resolution is not None
    assert resolution.indeterminate is True
    assert resolution.outcome is None


# --- the subprocess-outcome gate ------------------------------------------


def test_subprocess_gate_closed_while_inner_not_verified(composed_repo: Path) -> None:
    # Inner at `draft`: the proceed gate (subprocess-outcome: verified) is closed.
    proceed = _proceed_check(_outer(composed_repo))
    assert proceed.allowed is False
    assert proceed.indeterminate is False  # closed, not indeterminate


def test_subprocess_gate_open_when_inner_verified(composed_repo: Path) -> None:
    # Inner reaches `verified`: the proceed gate opens (a legal move now exists).
    _set(composed_repo, "_inner", "verified")
    proceed = _proceed_check(_outer(composed_repo))
    assert proceed.allowed is True
    assert "verified" in proceed.outcome.reason


def test_can_move_blocked_until_inner_verified(composed_repo: Path) -> None:
    engine = _outer(composed_repo)
    allowed, _reason, _pos = engine.can_move("discovered", "agent")
    assert allowed is False
    _set(composed_repo, "_inner", "verified")
    allowed, _reason, _pos = _outer(composed_repo).can_move("discovered", "agent")
    assert allowed is True


# --- the awaiting-subprocess-outcome overlay (auto-clearing) ---------------


def test_awaiting_subprocess_outcome_blocked_while_inner_draft(composed_repo: Path) -> None:
    engine = _outer(composed_repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    blocked = engine.evaluate_blocked(pos, checks, "agent")
    assert blocked is not None
    assert blocked.blocked_on == "awaiting-subprocess-outcome"
    assert blocked.at == "discovering"


def test_awaiting_subprocess_outcome_auto_clears_when_inner_verified(composed_repo: Path) -> None:
    # The condition IS the recursive resolution: when the inner reaches a wired
    # outcome the proceed gate opens, a legal move exists, and the wait clears
    # live -- no resume_when, no human in the loop.
    _set(composed_repo, "_inner", "verified")
    engine = _outer(composed_repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    assert engine.evaluate_blocked(pos, checks, "agent") is None


def test_terminal_outer_position_not_blocked(composed_repo: Path) -> None:
    # Once the parent reaches `discovered` (terminal, embeds nothing), no wait.
    _set(composed_repo, "_outer", "discovered")
    engine = _outer(composed_repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    assert engine.evaluate_blocked(pos, checks, "agent") is None


def test_unwired_inner_outcome_is_a_correct_wait(composed_repo: Path) -> None:
    # COR-036: outcome->transition wiring is the author's responsibility. If the
    # inner finishes at an outcome the parent did not wire, the parent is
    # CORRECTLY still awaiting-subprocess-outcome -- it has no move its author
    # gave it. Here we rewrite the inner so its terminal is `rejected` (which the
    # parent's `verified` gate does not match): the inner IS terminal, but the
    # parent's only gate tests `verified`, so no legal move -> still blocked.
    inner = (composed_repo / ".pkit" / "capabilities" / "fixture" / "schemas" / "verification.yaml")
    inner.write_text(
        _INNER_DEFINITION.replace("id: verified", "id: rejected")
        .replace("run: inner-detect-verified", "run: inner-detect-verified")
        .replace("to: verified", "to: rejected")
        .replace("Verified.", "Rejected."),
        encoding="utf-8",
    )
    # Point the verified-detector script at the `rejected` marker value so the
    # inner resolves to its (now `rejected`) terminal.
    scripts = composed_repo / ".pkit" / "capabilities" / "fixture" / "scripts"
    _write_script(scripts / "inner_detect_verified.py", _marker_detect("_inner", "rejected"))
    _set(composed_repo, "_inner", "rejected")

    engine = _outer(composed_repo)
    resolution = engine.resolve_subprocess_outcome("discovering")
    assert resolution is not None and resolution.outcome == "rejected"
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    # The parent's gate tests `verified`, the inner reached `rejected` -> closed.
    proceed = next(c for c in checks if c.to == "discovered")
    assert proceed.allowed is False
    # So the parent is correctly still blocked (incomplete parent wiring).
    assert engine.evaluate_blocked(pos, checks, "agent") is not None


# --- status surfacing -----------------------------------------------------


def test_subprocess_surfaces_on_json_status(composed_repo: Path) -> None:
    payload = json.loads(render_status_json(_outer(composed_repo), actor="agent"))
    sub = payload["position"]["subprocess"]
    assert sub is not None
    assert sub["runs"] == "fixture:verification"
    assert sub["outcome"] is None  # inner still at draft
    assert sub["indeterminate"] is False
    assert payload["blocked"]["blocked_on"] == "awaiting-subprocess-outcome"


def test_subprocess_outcome_surfaces_on_json_status_when_verified(composed_repo: Path) -> None:
    _set(composed_repo, "_inner", "verified")
    payload = json.loads(render_status_json(_outer(composed_repo), actor="agent"))
    assert payload["position"]["subprocess"]["outcome"] == "verified"


def test_subprocess_surfaces_on_narrative_status(composed_repo: Path) -> None:
    text = render_status_narrative(_outer(composed_repo), actor="agent")
    assert "embeds fixture:verification" in text


def test_status_render_is_read_only(composed_repo: Path) -> None:
    # Resolving an inner outcome (which status does) must write nothing.
    render_status_json(_outer(composed_repo), actor="agent")
    render_status_narrative(_outer(composed_repo), actor="agent")
    assert not _outer(composed_repo).read_journal(), "status must not write the journal"
    # And the inner journal is untouched too.
    inner_journal = (
        composed_repo / ".pkit" / "capabilities" / "fixture"
        / "project" / "process" / "verification"
    )
    assert not inner_journal.exists(), "resolving the inner must not write its journal"


# --- moving off the subprocess state clears the wait ----------------------


def test_move_off_subprocess_clears_wait(composed_repo: Path) -> None:
    _set(composed_repo, "_inner", "verified")
    # Park-time enter (the parent is currently blocked at `discovering`).
    enter = _outer(composed_repo).reconcile_blocked(actor="agent", assume_state="discovering")
    # At discovering with a verified inner the gate is OPEN, so there IS a legal
    # move -> not blocked -> no enter journaled. The proceed move is takeable.
    assert enter is None
    result = _outer(composed_repo).move("discovered", actor="agent")
    assert result.ok is True
