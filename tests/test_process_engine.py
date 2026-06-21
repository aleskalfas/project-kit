"""Tests for the process-substrate engine (COR-031, homed in the binary per ADR-020).

Builds a small fixture capability with a process definition + predicate
commands (tiny executable scripts that emit structured JSON) so the engine has
real reality to resolve against. Covers:

- position resolution (the state whose detection predicate matches),
- a passing and a failing deterministic gate,
- an authorisation-artifact gate with cross-authority (produced_by == actor
  refuses; != actor allows),
- fail-closed on a broken predicate (non-zero exit / bad JSON),
- journal append + entry shape (validated against the shape contract),
- the status JSON shape.
"""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.process import (
    SINGLETON_SUBJECT,
    ProcessEngine,
    ProcessError,
    load_definition,
    render_status_json,
)

# --- fixture scaffolding --------------------------------------------------


# The fixture process has three states resolved by detection predicates and
# four transitions exercising both gate kinds plus a broken predicate.
_PROCESS_DEFINITION = """\
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
    - id: ready
      meaning: Ready for review.
      detection:
        mode: inferred
        predicate:
          run: detect-ready
    - id: done
      meaning: Complete.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-done
  transitions:
    - from: draft
      to: ready
      trigger: submit
      authorisation: agent-autonomous
      gate:
        kind: deterministic
        predicate:
          run: gate-checks-pass
      why: Submit work for review once checks pass.
      hint: pkit process move demo:fixture --to ready
    - from: ready
      to: done
      trigger: approve
      authorisation: user
      gate:
        kind: authorisation-artifact
        predicate:
          run: gate-review-verdict
      why: Approve once a different authority has reviewed.
    - from: draft
      to: done
      trigger: force
      authorisation: script
      gate:
        kind: deterministic
        predicate:
          run: gate-broken
      why: A move whose gate predicate is broken (fail-closed).
"""


def _write_script(path: Path, body: str) -> None:
    """Write an executable python3 script and mark it runnable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """A repo with the shape contract staged + a fixture capability bound to it.

    Detection state is controlled by a `_state` marker file the test rewrites;
    each detect-* predicate reports result=true when the marker matches it.
    """
    repo = tmp_path
    pkit = repo / ".pkit"

    # Stage the real shape contract so journal-entry validation resolves it.
    defs_dst = pkit / "schemas" / "_defs"
    defs_dst.mkdir(parents=True, exist_ok=True)
    source_defs = (
        Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
    )
    shutil.copy(source_defs, defs_dst / "process.schema.json")

    cap = pkit / "capabilities" / "fixture"
    scripts = cap / "scripts"
    cap.mkdir(parents=True, exist_ok=True)

    # package.yaml registers every predicate command (the engine rejects an
    # unregistered name).
    (cap / "package.yaml").write_text(
        """schema_version: 2
component:
  kind: capability
  name: fixture
  version: 0.1.0
description: Fixture capability for process-engine tests.
commands:
  detect-draft:
    script: scripts/detect_draft.py
    help: detect draft
  detect-ready:
    script: scripts/detect_ready.py
    help: detect ready
  detect-done:
    script: scripts/detect_done.py
    help: detect done
  gate-checks-pass:
    script: scripts/gate_checks.py
    help: deterministic gate
  gate-review-verdict:
    script: scripts/gate_review.py
    help: authorisation-artifact gate
  gate-broken:
    script: scripts/gate_broken.py
    help: broken gate
""",
        encoding="utf-8",
    )

    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "demo.yaml").write_text(_PROCESS_DEFINITION, encoding="utf-8")

    # State marker the detect-* scripts read. Default: draft.
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
    _write_script(scripts / "detect_ready.py", _detect("ready"))
    _write_script(scripts / "detect_done.py", _detect("done"))

    # Deterministic gate: passes iff a `_checks_ok` marker exists.
    _write_script(
        scripts / "gate_checks.py",
        "import json, sys, pathlib\n"
        "ok = pathlib.Path('_checks_ok').exists()\n"
        "print(json.dumps({'result': ok, 'reason': 'checks ' + ('pass' if ok else 'fail')}))\n"
        "sys.exit(0)\n",
    )

    # Authorisation-artifact gate: reports {exists, produced_by} from a
    # `_review` JSON marker if present; the engine computes cross-authority.
    _write_script(
        scripts / "gate_review.py",
        "import json, sys, pathlib\n"
        "p = pathlib.Path('_review')\n"
        "if p.exists():\n"
        "    data = json.loads(p.read_text())\n"
        "    print(json.dumps({'exists': True, 'produced_by': data['by'],\n"
        "                      'result': True, 'reason': 'verdict present'}))\n"
        "else:\n"
        "    print(json.dumps({'exists': False, 'reason': 'no verdict'}))\n"
        "sys.exit(0)\n",
    )

    # Broken gate: exits non-zero -> indeterminate (fail-closed).
    _write_script(
        scripts / "gate_broken.py",
        "import sys\nsys.stderr.write('boom')\nsys.exit(3)\n",
    )

    return repo


def _set_state(repo: Path, state: str) -> None:
    (repo / "_state").write_text(state, encoding="utf-8")


def _engine(repo: Path) -> ProcessEngine:
    definition = load_definition(repo, "fixture:demo")
    return ProcessEngine(definition, repo)


# --- position resolution --------------------------------------------------


def test_position_resolves_to_matching_state(fixture_repo: Path) -> None:
    engine = _engine(fixture_repo)
    pos = engine.resolve_position()
    assert pos.state_id == "draft"
    assert pos.indeterminate is False

    _set_state(fixture_repo, "ready")
    pos = _engine(fixture_repo).resolve_position()
    assert pos.state_id == "ready"


def test_position_no_match_is_no_position_not_indeterminate(fixture_repo: Path) -> None:
    _set_state(fixture_repo, "nowhere")
    pos = _engine(fixture_repo).resolve_position()
    assert pos.state_id is None
    assert pos.indeterminate is False


# --- deterministic gate ---------------------------------------------------


def test_deterministic_gate_failing_refuses(fixture_repo: Path) -> None:
    # In draft, checks marker absent -> submit gate fails.
    allowed, reason, _pos = _engine(fixture_repo).can_move("ready", actor="agent")
    assert allowed is False
    assert "checks fail" in reason


def test_deterministic_gate_passing_allows_and_moves(fixture_repo: Path) -> None:
    (fixture_repo / "_checks_ok").write_text("", encoding="utf-8")
    engine = _engine(fixture_repo)
    allowed, _reason, _pos = engine.can_move("ready", actor="agent")
    assert allowed is True

    result = engine.move("ready", actor="agent")
    assert result.ok is True
    assert result.journal_entry is not None
    assert result.journal_entry["from"] == "draft"
    assert result.journal_entry["to"] == "ready"
    assert result.journal_entry["gate_result"] == "pass"


# --- authorisation-artifact gate (cross-authority) ------------------------


def test_authorisation_artifact_same_actor_refuses(fixture_repo: Path) -> None:
    _set_state(fixture_repo, "ready")
    # Verdict produced by the same actor being gated -> not cross-authority.
    (fixture_repo / "_review").write_text(json.dumps({"by": "alice"}), encoding="utf-8")
    allowed, reason, _pos = _engine(fixture_repo).can_move("done", actor="alice")
    assert allowed is False
    assert "produced by the actor being gated" in reason


def test_authorisation_artifact_different_actor_allows(fixture_repo: Path) -> None:
    _set_state(fixture_repo, "ready")
    (fixture_repo / "_review").write_text(json.dumps({"by": "bob"}), encoding="utf-8")
    allowed, reason, _pos = _engine(fixture_repo).can_move("done", actor="alice")
    assert allowed is True
    assert "cross-authority" in reason


def test_authorisation_artifact_supplied_result_is_ignored(fixture_repo: Path) -> None:
    # The review predicate emits result=True even for the same actor; the engine
    # must ignore it and compute cross-authority itself.
    _set_state(fixture_repo, "ready")
    (fixture_repo / "_review").write_text(json.dumps({"by": "alice"}), encoding="utf-8")
    allowed, _reason, _pos = _engine(fixture_repo).can_move("done", actor="alice")
    assert allowed is False


# --- fail-closed ----------------------------------------------------------


def test_broken_gate_predicate_fails_closed(fixture_repo: Path) -> None:
    # The `force` transition (draft -> done) has a gate that exits non-zero.
    allowed, reason, _pos = _engine(fixture_repo).can_move("done", actor="script")
    assert allowed is False
    assert "couldn't evaluate" in reason


def test_unregistered_predicate_raises_clear_error(fixture_repo: Path) -> None:
    # Point a detection predicate at a command the package.yaml does not register.
    bad = _PROCESS_DEFINITION.replace("run: detect-draft", "run: not-registered")
    (fixture_repo / ".pkit" / "capabilities" / "fixture" / "schemas" / "demo.yaml").write_text(
        bad, encoding="utf-8"
    )
    with pytest.raises(ProcessError) as exc:
        _engine(fixture_repo).resolve_position()
    assert "not registered" in str(exc.value)


# --- move refusal does not write the journal ------------------------------


def test_refused_move_writes_no_journal(fixture_repo: Path) -> None:
    engine = _engine(fixture_repo)
    result = engine.move("ready", actor="agent")  # gate fails (no _checks_ok)
    assert result.ok is False
    assert not engine.journal_path().is_file()


def test_journal_appends_and_validates_shape(fixture_repo: Path) -> None:
    (fixture_repo / "_checks_ok").write_text("", encoding="utf-8")
    engine = _engine(fixture_repo)
    engine.move("ready", actor="agent")

    path = engine.journal_path()
    assert path.is_file()
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    entry = json.loads(lines[0])
    # Required fields per _defs/process.schema.json#/$defs/journal_entry.
    for key in ("ts", "subject", "to", "trigger", "actor"):
        assert key in entry
    assert entry["subject"] == SINGLETON_SUBJECT


# --- status JSON shape ----------------------------------------------------


def test_status_json_shape(fixture_repo: Path) -> None:
    payload = json.loads(render_status_json(_engine(fixture_repo), actor="agent"))
    assert payload["process"] == "fixture:demo"
    assert payload["subject"] == SINGLETON_SUBJECT
    assert payload["position"]["state"] == "draft"
    assert payload["position"]["indeterminate"] is False
    assert isinstance(payload["journal"], list)
    moves = {m["to"]: m for m in payload["legal_moves"]}
    # From draft: submit->ready (gate fails) and force->done (broken, fail-closed).
    assert moves["ready"]["allowed"] is False
    assert moves["done"]["indeterminate"] is True


def test_status_json_after_move_reflects_journal(fixture_repo: Path) -> None:
    (fixture_repo / "_checks_ok").write_text("", encoding="utf-8")
    engine = _engine(fixture_repo)
    engine.move("ready", actor="agent")
    _set_state(fixture_repo, "ready")
    payload = json.loads(render_status_json(_engine(fixture_repo), actor="agent"))
    assert payload["position"]["state"] == "ready"
    assert len(payload["journal"]) == 1
    assert payload["journal"][0]["to"] == "ready"


# --- address parsing ------------------------------------------------------


def test_load_definition_rejects_bad_address(fixture_repo: Path) -> None:
    with pytest.raises(ProcessError):
        load_definition(fixture_repo, "no-colon-here")
    with pytest.raises(ProcessError):
        load_definition(fixture_repo, "fixture:missing")


# --- CLI wiring -----------------------------------------------------------


def test_cli_status_json_and_move(fixture_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The CLI resolves the repo root via git; init one so find_target_root works.
    subprocess.run(["git", "init", "-q"], cwd=fixture_repo, check=True)
    monkeypatch.chdir(fixture_repo)
    runner = CliRunner()

    result = runner.invoke(main, ["process", "status", "fixture:demo", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["position"]["state"] == "draft"

    # Illegal move (gate fails) refuses with exit 1.
    refused = runner.invoke(main, ["process", "move", "fixture:demo", "--to", "ready"])
    assert refused.exit_code == 1
    assert "refused" in refused.output

    # Make the gate pass, then the move succeeds.
    (fixture_repo / "_checks_ok").write_text("", encoding="utf-8")
    moved = runner.invoke(
        main, ["process", "move", "fixture:demo", "--to", "ready", "--actor", "agent"]
    )
    assert moved.exit_code == 0, moved.output
    assert "moved to 'ready'" in moved.output
