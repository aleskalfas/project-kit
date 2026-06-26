"""Inertness tests for COR-038 `depends_on` -- the engine NEVER reads it.

COR-038's load-bearing invariant: `depends_on` is INERT. The engine's runtime
operations (`status` / `can-move` / `move` / `validate`-of-position) must never
read it -- its only readers are the schema (shape-validation) and a future,
out-of-engine render. A malformed-or-absent `depends_on` cannot affect whether a
subject may move.

This pins that by running the SAME process twice -- once plain, once with a
`depends_on` block on the current state (and even a deliberately self-referential
upstream the engine would choke on if it ever tried to RESOLVE the address) --
and asserting identical position, identical legal-move prechecks, and identical
move outcomes. The block makes no observable difference.

Built on its own tiny fixture capability (mirroring test_process_engine.py) so
the engine has real reality to resolve against.
"""

from __future__ import annotations

import shutil
import stat
from pathlib import Path

import pytest

from project_kit.process import ProcessEngine, load_definition

# Two states resolved by detection predicates; one gated transition. The ONLY
# difference between the two fixtures is whether the current state carries a
# `depends_on` block -- everything the engine reads is identical.
_PLAIN_DEFINITION = """\
process:
  id: demo
  version: 1
  subject:
    cardinality: singleton
    domain_ref: fixture
  states:
    - id: draft
      meaning: Work has started but is not ready.
      detection:
        mode: inferred
        predicate:
          run: detect-draft
    - id: done
      meaning: Complete.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-done
  transitions:
    - from: draft
      to: done
      trigger: submit
      authorisation: agent-autonomous
      gate:
        kind: deterministic
        predicate:
          run: gate-checks-pass
      why: Submit once checks pass.
"""

# Same process, with an inert depends_on block on the CURRENT (draft) state.
# The `upstream` deliberately points back at this very process: if the engine
# ever tried to RESOLVE the address (it must not), the acyclicity guard or a
# load would surface -- the engine ignoring the block entirely is the invariant.
_DEPENDS_ON_BLOCK = """\
      depends_on:
        - upstream: fixture:demo
          relation: gates-on-readiness
          mode: pull
          why: A gate predicate elsewhere enforces upstream readiness; named here for visibility.
        - upstream: other-cap:some-process
          relation: triggered-by
          mode: push
          why: A connector kicks this off; engine-invisible, recorded for the render.
"""


def _annotated_definition() -> str:
    # Insert the depends_on block into the draft state, after its detection.
    anchor = "          run: detect-draft\n"
    return _PLAIN_DEFINITION.replace(anchor, anchor + _DEPENDS_ON_BLOCK, 1)


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _make_repo(tmp_path: Path, definition: str) -> Path:
    repo = tmp_path
    pkit = repo / ".pkit"

    defs_dst = pkit / "schemas" / "_defs"
    defs_dst.mkdir(parents=True, exist_ok=True)
    source_defs = (
        Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
    )
    shutil.copy(source_defs, defs_dst / "process.schema.json")

    cap = pkit / "capabilities" / "fixture"
    scripts = cap / "scripts"
    cap.mkdir(parents=True, exist_ok=True)

    (cap / "package.yaml").write_text(
        """schema_version: 2
component:
  kind: capability
  name: fixture
  version: 0.1.0
description: Fixture capability for depends_on inertness tests.
commands:
  detect-draft:
    script: scripts/detect_draft.py
    help: detect draft
  detect-done:
    script: scripts/detect_done.py
    help: detect done
  gate-checks-pass:
    script: scripts/gate_checks.py
    help: deterministic gate
""",
        encoding="utf-8",
    )

    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "demo.yaml").write_text(definition, encoding="utf-8")

    marker = repo / "_state"
    marker.write_text("draft", encoding="utf-8")

    def _detect(state_name: str) -> str:
        return (
            "import json, sys, pathlib\n"
            "cur = pathlib.Path('_state').read_text().strip()\n"
            f"hit = cur == {state_name!r}\n"
            "print(json.dumps({'result': hit, 'reason': f'marker is {cur!r}'}))\n"
            "sys.exit(0)\n"
        )

    _write_script(scripts / "detect_draft.py", _detect("draft"))
    _write_script(scripts / "detect_done.py", _detect("done"))
    _write_script(
        scripts / "gate_checks.py",
        "import json, sys, pathlib\n"
        "ok = pathlib.Path('_checks_ok').exists()\n"
        "print(json.dumps({'result': ok, 'reason': 'checks ' + ('pass' if ok else 'fail')}))\n"
        "sys.exit(0)\n",
    )

    return repo


@pytest.fixture
def plain_repo(tmp_path: Path) -> Path:
    return _make_repo(tmp_path / "plain", _PLAIN_DEFINITION)


@pytest.fixture
def annotated_repo(tmp_path: Path) -> Path:
    return _make_repo(tmp_path / "annotated", _annotated_definition())


def _engine(repo: Path) -> ProcessEngine:
    return ProcessEngine(load_definition(repo, "fixture:demo"), repo)


# --- the inertness invariant ----------------------------------------------


def test_position_identical_with_and_without_depends_on(
    plain_repo: Path, annotated_repo: Path
) -> None:
    plain = _engine(plain_repo).resolve_position()
    annotated = _engine(annotated_repo).resolve_position()
    assert annotated.state_id == plain.state_id == "draft"
    assert annotated.indeterminate == plain.indeterminate is False


def test_can_move_identical_with_and_without_depends_on(
    plain_repo: Path, annotated_repo: Path
) -> None:
    # Gate closed (no _checks_ok marker): both refuse, identically.
    p_allowed, p_reason, _ = _engine(plain_repo).can_move("done", actor="agent")
    a_allowed, a_reason, _ = _engine(annotated_repo).can_move("done", actor="agent")
    assert a_allowed == p_allowed is False
    assert a_reason == p_reason

    # Gate open: both allow, identically. The depends_on block does not gate.
    (plain_repo / "_checks_ok").write_text("", encoding="utf-8")
    (annotated_repo / "_checks_ok").write_text("", encoding="utf-8")
    p_allowed, _, _ = _engine(plain_repo).can_move("done", actor="agent")
    a_allowed, _, _ = _engine(annotated_repo).can_move("done", actor="agent")
    assert a_allowed == p_allowed is True


def test_move_identical_with_and_without_depends_on(
    plain_repo: Path, annotated_repo: Path
) -> None:
    (plain_repo / "_checks_ok").write_text("", encoding="utf-8")
    (annotated_repo / "_checks_ok").write_text("", encoding="utf-8")

    plain = _engine(plain_repo).move("done", actor="agent")
    annotated = _engine(annotated_repo).move("done", actor="agent")

    assert annotated.ok == plain.ok is True
    # The journaled move records the SAME edge -- depends_on leaves no trace.
    assert annotated.journal_entry is not None and plain.journal_entry is not None
    assert annotated.journal_entry["from"] == plain.journal_entry["from"] == "draft"
    assert annotated.journal_entry["to"] == plain.journal_entry["to"] == "done"
    assert annotated.journal_entry["gate_result"] == plain.journal_entry["gate_result"] == "pass"
    # depends_on is NOT carried into the journal -- the entry is the plain edge.
    assert "depends_on" not in annotated.journal_entry


def test_legal_moves_identical_with_and_without_depends_on(
    plain_repo: Path, annotated_repo: Path
) -> None:
    (plain_repo / "_checks_ok").write_text("", encoding="utf-8")
    (annotated_repo / "_checks_ok").write_text("", encoding="utf-8")

    plain = _engine(plain_repo)
    annotated = _engine(annotated_repo)
    p_pos = plain.resolve_position()
    a_pos = annotated.resolve_position()

    p_moves = [(c.to, c.allowed) for c in plain.precheck_transitions(p_pos.state_id, "agent")]
    a_moves = [(c.to, c.allowed) for c in annotated.precheck_transitions(a_pos.state_id, "agent")]
    assert a_moves == p_moves
