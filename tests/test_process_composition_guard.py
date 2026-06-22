"""COR-036 acyclicity guard + keyed-inner determinate-subject tests.

The acyclicity guard tracks the active resolution stack (each engine's own
address plus every inner above it) and refuses an address already on the stack,
FAILING CLOSED (surfaced, like an unrecognised gate kind). Because resolution is
single-level — resolving an inner reads its DETECTED position and never recurses
through the inner's own subprocess-outcome gates — the stack never deepens past
the one inner being loaded. So the guard in practice fires only on the DIRECT
self-embed (A runs A, where the inner address equals the engine's own seeded
address). A transitive cycle (A runs B runs A) is NOT reachable as a recursion
today and is bounded-safe incidentally, not guard-caught; the tests below pin
that honest behaviour (a wait, no spurious gate pass) rather than a guard firing.
The guard is the correct seam to extend if nesting-through-gates is ever added.
This is distinct from COR-034's deferred `deadlock` (a peer-subject cycle).

The keyed-inner tests exercise COR-032's required-subject rule under embedding:
a keyed inner must be given its one determinate subject id, supplied by the
parent's `subprocess.subject`; absent it, the resolution is fail-closed. The
engine NEVER enumerates a keyed inner's subjects (that breadth is cascade).
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from project_kit.process import ProcessEngine, load_definition

# Self-embedding: `loop` runs the SAME process (alpha:alpha). A runs A.
_SELF_DEFINITION = """\
process:
  id: alpha
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: loop
      meaning: Embeds itself (a cycle).
      detection:
        mode: inferred
        predicate:
          run: detect-loop
      subprocess:
        runs: fixture:alpha
    - id: done
      meaning: Done.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-done
  transitions:
    - from: loop
      to: done
      trigger: proceed
      authorisation: agent-autonomous
      gate:
        kind: subprocess-outcome
        outcome: done
"""

# Mutual embedding: beta runs gamma, gamma runs beta (A runs B runs A).
_BETA_DEFINITION = """\
process:
  id: beta
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: in-beta
      meaning: Beta embeds gamma.
      detection:
        mode: inferred
        predicate:
          run: detect-in
      subprocess:
        runs: fixture:gamma
    - id: beta-done
      meaning: Done.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-done
  transitions:
    - from: in-beta
      to: beta-done
      trigger: proceed
      authorisation: agent-autonomous
      gate:
        kind: subprocess-outcome
        outcome: gamma-done
"""

_GAMMA_DEFINITION = """\
process:
  id: gamma
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: in-gamma
      meaning: Gamma embeds beta (closing the cycle).
      detection:
        mode: inferred
        predicate:
          run: detect-in
      subprocess:
        runs: fixture:beta
    - id: gamma-done
      meaning: Done.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-done
  transitions:
    - from: in-gamma
      to: gamma-done
      trigger: proceed
      authorisation: agent-autonomous
      gate:
        kind: subprocess-outcome
        outcome: beta-done
"""

# A KEYED inner process: requires a subject id (COR-032). Singleton parent
# embeds it; one variant supplies the inner subject, one omits it.
_KEYED_INNER_DEFINITION = """\
process:
  id: point
  version: 1
  subject:
    cardinality: keyed
    key: point-id
  states:
    - id: pending
      meaning: Pending.
      detection:
        mode: inferred
        predicate:
          run: keyed-detect-pending
    - id: confirmed
      meaning: Confirmed.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: keyed-detect-confirmed
  transitions:
    - from: pending
      to: confirmed
      trigger: confirm
      authorisation: script
"""

_PARENT_WITH_SUBJECT = """\
process:
  id: with-subject
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: waiting
      meaning: Waiting on a determinate keyed inner.
      detection:
        mode: inferred
        predicate:
          run: parent-detect-waiting
      subprocess:
        runs: fixture:point
        subject: p1
    - id: ready
      meaning: Ready.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: parent-detect-ready
  transitions:
    - from: waiting
      to: ready
      trigger: proceed
      authorisation: agent-autonomous
      gate:
        kind: subprocess-outcome
        outcome: confirmed
"""

_PARENT_NO_SUBJECT = _PARENT_WITH_SUBJECT.replace("id: with-subject", "id: no-subject").replace(
    "        subject: p1\n", ""
)


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
def guard_repo(tmp_path: Path) -> Path:
    """A repo whose fixture capability declares the self- and mutually-embedding
    processes plus a keyed inner and two parents (with/without supplied subject)."""
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
description: Acyclicity-guard + keyed-inner fixture (COR-036).
commands:
  detect-loop:
    script: scripts/detect_loop.py
    help: loop
  detect-in:
    script: scripts/detect_in.py
    help: in
  detect-done:
    script: scripts/detect_done.py
    help: done
  keyed-detect-pending:
    script: scripts/keyed_detect_pending.py
    help: keyed pending
  keyed-detect-confirmed:
    script: scripts/keyed_detect_confirmed.py
    help: keyed confirmed
  parent-detect-waiting:
    script: scripts/parent_detect_waiting.py
    help: parent waiting
  parent-detect-ready:
    script: scripts/parent_detect_ready.py
    help: parent ready
""",
        encoding="utf-8",
    )
    schemas = cap / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    (schemas / "alpha.yaml").write_text(_SELF_DEFINITION, encoding="utf-8")
    (schemas / "beta.yaml").write_text(_BETA_DEFINITION, encoding="utf-8")
    (schemas / "gamma.yaml").write_text(_GAMMA_DEFINITION, encoding="utf-8")
    (schemas / "point.yaml").write_text(_KEYED_INNER_DEFINITION, encoding="utf-8")
    (schemas / "with-subject.yaml").write_text(_PARENT_WITH_SUBJECT, encoding="utf-8")
    (schemas / "no-subject.yaml").write_text(_PARENT_NO_SUBJECT, encoding="utf-8")

    # Detection scripts. The cyclic processes always resolve to their embedding
    # state and their terminal states never match. For the transitive case this
    # means: resolving beta's inner (gamma) reads gamma's DETECTED position, which
    # is `in-gamma` (non-terminal) -- resolution is single-level and does not
    # descend into gamma's own subprocess gate back to beta, so the stack never
    # deepens and the guard does not fire. beta simply sees a determinate-but-not-
    # terminal gamma -> a wait. For the direct self-embed (alpha runs alpha), the
    # inner address equals alpha's own seeded stack entry, so the guard DOES fire.
    def _const(result: bool, reason: str) -> str:
        return f"import json\nprint(json.dumps({{'result': {result}, 'reason': {reason!r}}}))\n"

    _write_script(scripts / "detect_loop.py", _const(True, "loop"))
    _write_script(scripts / "detect_in.py", _const(True, "in"))
    _write_script(scripts / "detect_done.py", _const(False, "not done"))
    _write_script(scripts / "parent_detect_waiting.py", _const(True, "waiting"))
    _write_script(scripts / "parent_detect_ready.py", _const(False, "not ready"))

    # Keyed inner: position from a per-subject marker file `_point_<subject>`.
    def _keyed(state_name: str) -> str:
        return (
            "import json, sys, pathlib\n"
            "subject = sys.argv[1] if len(sys.argv) > 1 else '_'\n"
            "p = pathlib.Path(f'_point_{subject}')\n"
            "cur = p.read_text().strip() if p.exists() else ''\n"
            f"print(json.dumps({{'result': cur == {state_name!r}, 'reason': cur}}))\n"
        )

    _write_script(scripts / "keyed_detect_pending.py", _keyed("pending"))
    _write_script(scripts / "keyed_detect_confirmed.py", _keyed("confirmed"))
    return repo


# --- the acyclicity guard -------------------------------------------------


def test_self_embedding_fails_closed(guard_repo: Path) -> None:
    # alpha runs alpha: the inner address is already on the stack (the top-level
    # engine seeds its own address) -> cyclic embedding refused, fail-closed.
    engine = ProcessEngine(load_definition(guard_repo, "fixture:alpha"), guard_repo)
    resolution = engine.resolve_subprocess_outcome("loop")
    assert resolution is not None
    assert resolution.indeterminate is True
    assert "cyclic embedding refused" in resolution.reason


def test_self_embedding_gate_fails_closed(guard_repo: Path) -> None:
    # The subprocess-outcome gate reading the cyclic resolution fails closed
    # (indeterminate), exactly like an unrecognised gate kind -- never a silent
    # pass.
    engine = ProcessEngine(load_definition(guard_repo, "fixture:alpha"), guard_repo)
    pos = engine.resolve_position()
    proceed = next(c for c in engine.precheck_transitions(pos.state_id, "agent") if c.to == "done")
    assert proceed.allowed is False
    assert proceed.indeterminate is True


def test_transitive_cycle_yields_a_wait(guard_repo: Path) -> None:
    # beta runs gamma runs beta. Resolution is single-level: resolving beta's
    # inner (gamma) reads gamma's DETECTED position only -- it does NOT recurse
    # through gamma's own subprocess gate back into beta. So the stack never
    # deepens and the guard does NOT fire. gamma's detected position is `in-gamma`
    # (non-terminal), so beta sees a determinate-but-not-terminal inner -> a WAIT.
    engine = ProcessEngine(load_definition(guard_repo, "fixture:beta"), guard_repo)
    resolution = engine.resolve_subprocess_outcome("in-beta")
    assert resolution is not None
    # The honest behaviour: a wait, NOT a fail-closed and NOT a spurious match.
    assert resolution.indeterminate is False
    assert resolution.outcome is None


def test_transitive_cycle_gate_does_not_pass(guard_repo: Path) -> None:
    # The key safety property: a transitive cycle never lets a parent's gate
    # spuriously pass. beta's proceed gate (outcome: gamma-done) must not open.
    engine = ProcessEngine(load_definition(guard_repo, "fixture:beta"), guard_repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    proceed = next(c for c in checks if c.to == "beta-done")
    assert proceed.allowed is False


# --- keyed inner: COR-032 required-subject rule under embedding -----------


def test_keyed_inner_without_subject_fails_closed(guard_repo: Path) -> None:
    # The parent embeds a KEYED inner but supplies no `subject` -> COR-032's
    # required-subject rule -> fail-closed resolution.
    engine = ProcessEngine(load_definition(guard_repo, "fixture:no-subject"), guard_repo)
    resolution = engine.resolve_subprocess_outcome("waiting")
    assert resolution is not None
    assert resolution.indeterminate is True
    assert "subject" in resolution.reason.lower()


def test_keyed_inner_with_subject_resolves_determinate(guard_repo: Path) -> None:
    # The parent supplies `subject: p1`; the engine resolves THAT one inner
    # subject (never enumerating). With p1 confirmed, the outcome resolves.
    (guard_repo / "_point_p1").write_text("confirmed", encoding="utf-8")
    engine = ProcessEngine(load_definition(guard_repo, "fixture:with-subject"), guard_repo)
    resolution = engine.resolve_subprocess_outcome("waiting")
    assert resolution is not None
    assert resolution.indeterminate is False
    assert resolution.outcome == "confirmed"


def test_keyed_inner_resolves_only_the_named_subject(guard_repo: Path) -> None:
    # p1 pending, a DIFFERENT subject p2 confirmed: the engine resolves only the
    # named p1 (single-inner, no enumeration) -> p1 not yet confirmed -> no
    # outcome. The presence of a confirmed p2 is invisible to the resolution.
    (guard_repo / "_point_p1").write_text("pending", encoding="utf-8")
    (guard_repo / "_point_p2").write_text("confirmed", encoding="utf-8")
    engine = ProcessEngine(load_definition(guard_repo, "fixture:with-subject"), guard_repo)
    resolution = engine.resolve_subprocess_outcome("waiting")
    assert resolution is not None
    assert resolution.outcome is None
    assert resolution.indeterminate is False
