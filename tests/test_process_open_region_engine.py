"""Engine tests for the COR-040 / ADR-036 open-region slot.

The slot's whole engine novelty is a POSITION FILTER on the existing invariant
report (`evaluate_invariants`): an invariant carrying `applies_to: <state>` is
evaluated/surfaced ONLY when the subject's resolved position equals that state.
Everything else (the exit gate, move-legality, blocked overlay) is composed from
unchanged parts — the exit is an ordinary `deterministic` gate.

The fixture is a two-state process: `build` (an open region) with a scoped
invariant + an unscoped process-wide invariant, and `ready` (terminal), reached
through an ordinary `deterministic` exit gate. Marker files drive detection and
the checks so the test can put the subject IN the region, OUT of the region, and
into an INDETERMINATE position, and watch which invariants surface. Covers:

- unscoped invariant unchanged (evaluated in AND out of the region),
- scoped invariant evaluated + surfaced when the subject is in its region,
- scoped invariant NOT surfaced when the subject is in another region,
- scoped invariant NOT-APPLICABLE under an indeterminate position,
- the status / validate rendering (narrative + --json) filters to the region,
- a violated region-scoped invariant renders alongside the shut exit gate as the
  reason the subject cannot leave,
- read-only: no journal written.
"""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import pytest

from project_kit.process import (
    ProcessEngine,
    load_definition,
    render_status_json,
    render_status_narrative,
    render_validate_json,
    render_validate_narrative,
)

# `build` is the open region: it carries a region-scoped invariant
# (`region-readiness`, applies_to: build) plus an unscoped process-wide
# invariant (`evidence-backed`). Its single exit is an ordinary deterministic
# gate whose predicate mirrors the region's readiness — so a shut exit and a
# violated region invariant have the same underlying cause (ADR-036 §2/§5).
_PROCESS_DEFINITION = """\
process:
  id: demo
  version: 1
  subject:
    cardinality: singleton
    domain_ref: fixture
  states:
    - id: build
      meaning: Build (open region).
      open_region: true
      detection:
        mode: inferred
        predicate:
          run: detect-build
    - id: ready
      meaning: Ready.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-ready
  transitions:
    - from: build
      to: ready
      trigger: leave
      authorisation: agent-autonomous
      gate:
        kind: deterministic
        predicate:
          run: exit-ready
  invariants:
    - id: evidence-backed
      check:
        run: check-evidence
      why: Every factual claim must resolve to an evidence record.
    - id: region-readiness
      check:
        run: check-readiness
      applies_to: build
      why: Each track's readiness must be recorded before leaving the build region.
"""


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """A repo with the shape contract staged + a fixture capability whose
    process declares an open region.

    Detection reads a `_state` marker (`build` / `ready` / anything else = no
    match). `check-readiness` and `exit-ready` both hold iff a `_ready` marker
    exists (the region's readiness is the exit condition). `check-evidence` holds
    iff `_evidence_ok` exists. `detect-build` becomes INDETERMINATE (non-zero
    exit) when a `_break_detect` marker exists — the lever for the indeterminate
    position case.
    """
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
description: Fixture capability for open-region tests.
commands:
  detect-build:
    script: scripts/detect_build.py
    help: detect build
  detect-ready:
    script: scripts/detect_ready.py
    help: detect ready
  check-evidence:
    script: scripts/check_evidence.py
    help: evidence invariant (process-wide)
  check-readiness:
    script: scripts/check_readiness.py
    help: region-scoped readiness invariant
  exit-ready:
    script: scripts/exit_ready.py
    help: the exit gate predicate
""",
        encoding="utf-8",
    )

    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "demo.yaml").write_text(_PROCESS_DEFINITION, encoding="utf-8")

    (repo / "_state").write_text("build", encoding="utf-8")

    # detect-build: matches iff `_state` == build, but goes INDETERMINATE (exit
    # non-zero) when `_break_detect` exists — the lever for the indeterminate
    # position test.
    _write_script(
        scripts / "detect_build.py",
        "import json, sys, pathlib\n"
        "if pathlib.Path('_break_detect').exists():\n"
        "    sys.stderr.write('boom'); sys.exit(3)\n"
        "cur = pathlib.Path('_state').read_text().strip()\n"
        "print(json.dumps({'result': cur == 'build', 'reason': f'marker is {cur!r}'}))\n"
        "sys.exit(0)\n",
    )
    _write_script(
        scripts / "detect_ready.py",
        "import json, sys, pathlib\n"
        "cur = pathlib.Path('_state').read_text().strip()\n"
        "print(json.dumps({'result': cur == 'ready', 'reason': f'marker is {cur!r}'}))\n"
        "sys.exit(0)\n",
    )

    _write_script(
        scripts / "check_evidence.py",
        "import json, sys, pathlib\n"
        "ok = pathlib.Path('_evidence_ok').exists()\n"
        "print(json.dumps({'result': ok, 'reason': "
        "'all claims cited' if ok else 'uncited claim found'}))\n"
        "sys.exit(0)\n",
    )
    # The region's readiness — shared by the scoped invariant AND the exit gate.
    _write_script(
        scripts / "check_readiness.py",
        "import json, sys, pathlib\n"
        "ok = pathlib.Path('_ready').exists()\n"
        "print(json.dumps({'result': ok, 'reason': "
        "'readiness recorded' if ok else 'readiness not yet recorded'}))\n"
        "sys.exit(0)\n",
    )
    _write_script(
        scripts / "exit_ready.py",
        "import json, sys, pathlib\n"
        "ok = pathlib.Path('_ready').exists()\n"
        "print(json.dumps({'result': ok, 'reason': "
        "'region conditions met' if ok else 'region conditions not yet met'}))\n"
        "sys.exit(0)\n",
    )

    return repo


def _engine(repo: Path) -> ProcessEngine:
    return ProcessEngine(load_definition(repo, "fixture:demo"), repo)


def _set_marker(repo: Path, name: str, present: bool) -> None:
    marker = repo / name
    if present:
        marker.write_text("", encoding="utf-8")
    elif marker.exists():
        marker.unlink()


def _outcomes(repo: Path) -> dict[str, object]:
    return {inv.invariant_id: inv for inv in _engine(repo).evaluate_invariants()}


# --- the filter: unscoped stays process-wide ------------------------------


def test_unscoped_invariant_evaluated_in_region(fixture_repo: Path) -> None:
    # In `build`, the unscoped process-wide invariant is evaluated (unchanged).
    _set_marker(fixture_repo, "_evidence_ok", present=False)
    outcomes = _outcomes(fixture_repo)
    assert "evidence-backed" in outcomes
    assert outcomes["evidence-backed"].holds is False  # type: ignore[attr-defined]


def test_unscoped_invariant_evaluated_out_of_region(fixture_repo: Path) -> None:
    # Out of `build` (in `ready`), the unscoped invariant is STILL evaluated —
    # process-wide behaviour is byte-unchanged from COR-035.
    (fixture_repo / "_state").write_text("ready", encoding="utf-8")
    _set_marker(fixture_repo, "_evidence_ok", present=False)
    outcomes = _outcomes(fixture_repo)
    assert "evidence-backed" in outcomes
    assert outcomes["evidence-backed"].holds is False  # type: ignore[attr-defined]


# --- the filter: scoped follows the resolved position ---------------------


def test_scoped_invariant_evaluated_in_region(fixture_repo: Path) -> None:
    # In `build`, the region-scoped invariant IS evaluated and surfaced.
    _set_marker(fixture_repo, "_ready", present=False)
    outcomes = _outcomes(fixture_repo)
    assert "region-readiness" in outcomes
    assert outcomes["region-readiness"].holds is False  # type: ignore[attr-defined]

    _set_marker(fixture_repo, "_ready", present=True)
    outcomes = _outcomes(fixture_repo)
    assert outcomes["region-readiness"].holds is True  # type: ignore[attr-defined]


def test_scoped_invariant_not_surfaced_out_of_region(fixture_repo: Path) -> None:
    # In `ready` (another region), the scoped invariant is NOT evaluated and NOT
    # returned — even though its readiness marker is absent (would be violated in
    # `build`). No spurious out-of-region violation.
    (fixture_repo / "_state").write_text("ready", encoding="utf-8")
    _set_marker(fixture_repo, "_ready", present=False)
    outcomes = _outcomes(fixture_repo)
    assert "region-readiness" not in outcomes
    # The unscoped one is still there (sanity).
    assert "evidence-backed" in outcomes


def test_scoped_invariant_not_applicable_under_indeterminate_position(fixture_repo: Path) -> None:
    # Break detection so the position is indeterminate. The scoped invariant is
    # NOT-APPLICABLE (not evaluated, not surfaced) — the engine cannot confirm
    # the region. The unscoped one continues to evaluate (COR-035 unchanged).
    _set_marker(fixture_repo, "_break_detect", present=True)
    _set_marker(fixture_repo, "_ready", present=False)
    _set_marker(fixture_repo, "_evidence_ok", present=False)

    engine = _engine(fixture_repo)
    assert engine.resolve_position().indeterminate is True
    outcomes = {inv.invariant_id: inv for inv in engine.evaluate_invariants()}
    assert "region-readiness" not in outcomes
    assert "evidence-backed" in outcomes
    assert outcomes["evidence-backed"].holds is False


# --- status / validate rendering filters to the region --------------------


def test_status_narrative_shows_region_violation_and_shut_exit(fixture_repo: Path) -> None:
    # In `build` with readiness unrecorded: the region-scoped invariant shows as
    # a violation AND the exit gate is shut (✗) with its reason — read together,
    # status is self-explaining about why the subject cannot leave (ADR-036 §5).
    _set_marker(fixture_repo, "_ready", present=False)
    _set_marker(fixture_repo, "_evidence_ok", present=True)
    text = render_status_narrative(_engine(fixture_repo), actor="agent")
    assert "Invariant violations:" in text
    assert "region-readiness" in text
    # The exit move renders shut.
    assert "✗ ready" in text
    assert "region conditions not yet met" in text


def test_status_narrative_hides_scoped_violation_out_of_region(fixture_repo: Path) -> None:
    # In `ready`, the scoped invariant's violation must NOT appear on status
    # (it is not applicable to this region).
    (fixture_repo / "_state").write_text("ready", encoding="utf-8")
    _set_marker(fixture_repo, "_ready", present=False)
    _set_marker(fixture_repo, "_evidence_ok", present=True)
    text = render_status_narrative(_engine(fixture_repo), actor="agent")
    assert "region-readiness" not in text


def test_status_json_carries_filtered_set(fixture_repo: Path) -> None:
    _set_marker(fixture_repo, "_ready", present=False)
    _set_marker(fixture_repo, "_evidence_ok", present=True)
    # In region: both the (holding) unscoped and the (violated) scoped appear.
    payload = json.loads(render_status_json(_engine(fixture_repo), actor="agent"))
    by_id = {inv["id"]: inv for inv in payload["invariants"]}
    assert set(by_id) == {"evidence-backed", "region-readiness"}
    assert by_id["region-readiness"]["holds"] is False
    # The shut exit gate is an ordinary closed-gate legal_moves entry.
    exit_move = next(m for m in payload["legal_moves"] if m["to"] == "ready")
    assert exit_move["allowed"] is False
    assert exit_move["indeterminate"] is False  # a determinate "not yet"

    # Out of region: the scoped invariant drops out of the JSON set entirely.
    (fixture_repo / "_state").write_text("ready", encoding="utf-8")
    payload = json.loads(render_status_json(_engine(fixture_repo), actor="agent"))
    by_id = {inv["id"]: inv for inv in payload["invariants"]}
    assert "region-readiness" not in by_id
    assert "evidence-backed" in by_id


def test_validate_filters_to_region(fixture_repo: Path) -> None:
    _set_marker(fixture_repo, "_ready", present=False)
    _set_marker(fixture_repo, "_evidence_ok", present=True)
    # In `build`: validate reports the scoped invariant (violated).
    payload = json.loads(render_validate_json(_engine(fixture_repo)))
    by_id = {inv["id"]: inv for inv in payload["invariants"]}
    assert "region-readiness" in by_id
    assert payload["ok"] is False  # the scoped violation fails the audit
    narrative = render_validate_narrative(_engine(fixture_repo))
    assert "region-readiness" in narrative

    # In `ready`: validate no longer reports the scoped invariant, and with the
    # unscoped one holding, the audit passes.
    (fixture_repo / "_state").write_text("ready", encoding="utf-8")
    payload = json.loads(render_validate_json(_engine(fixture_repo)))
    by_id = {inv["id"]: inv for inv in payload["invariants"]}
    assert "region-readiness" not in by_id
    assert payload["ok"] is True


def test_exit_opens_when_region_conditions_met(fixture_repo: Path) -> None:
    # Record readiness: the scoped invariant holds AND the exit gate opens — the
    # subject may leave. Confirms the exit is an ordinary gate, not blocked by
    # the invariant (which merely reports the same condition).
    _set_marker(fixture_repo, "_ready", present=True)
    _set_marker(fixture_repo, "_evidence_ok", present=True)
    allowed, reason, _position = _engine(fixture_repo).can_move("ready", actor="agent")
    assert allowed is True, reason


# --- read-only ------------------------------------------------------------


def test_open_region_status_writes_no_journal(fixture_repo: Path) -> None:
    _set_marker(fixture_repo, "_ready", present=False)
    engine = _engine(fixture_repo)
    render_status_narrative(engine, actor="agent")
    render_status_json(engine, actor="agent")
    render_validate_json(engine)
    engine.evaluate_invariants()
    assert not engine.journal_path().is_file()
