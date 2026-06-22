"""Tests for the COR-035 invariants slot + the `validate` engine operation.

Builds a fixture capability whose process declares two invariants — each backed
by a marker-file predicate the test toggles — so the engine has real reality to
check against. Covers:

- `validate` reports holds + violations (with the declaration's `why`),
- a fail-closed indeterminate `check` (broken predicate) is reported as NOT
  holding, distinctly,
- a violation is surfaced on the status view (narrative + `--json`),
- read-only: `validate` and `status` write no journal entries,
- behaviour-preserving: a process with no invariants reports an empty set and
  `validate` says all hold,
- the CLI `validate` subcommand (narrative + `--json`, non-zero exit on a
  violation).
"""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.process import (
    ProcessEngine,
    load_definition,
    render_status_json,
    render_status_narrative,
    render_validate_json,
    render_validate_narrative,
)

# --- fixture scaffolding --------------------------------------------------


# A singleton process with two invariants: one backed by a marker the test
# toggles (the "honest" check), one backed by a broken predicate (always
# indeterminate -> fail-closed). One trivial state + a transition so the
# definition is structurally complete; invariants are position-independent.
_PROCESS_DEFINITION = """\
process:
  id: demo
  version: 1
  subject:
    cardinality: singleton
    domain_ref: fixture
  states:
    - id: open
      meaning: Open.
      detection:
        mode: inferred
        predicate:
          run: detect-open
    - id: shut
      meaning: Shut.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: detect-shut
  transitions:
    - from: open
      to: shut
      trigger: close
      authorisation: agent-autonomous
  invariants:
    - id: evidence-backed
      check:
        run: check-evidence
      why: Every factual claim must resolve to an evidence record.
    - id: derive-dont-store
      check:
        run: check-broken
      why: Computed views are never persisted alongside the atoms they derive from.
"""


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """A repo with the shape contract staged + a fixture capability whose
    process declares invariants.

    `check-evidence` holds iff a `_evidence_ok` marker exists; `check-broken`
    always exits non-zero (indeterminate -> fail-closed).
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
description: Fixture capability for invariants tests.
commands:
  detect-open:
    script: scripts/detect_open.py
    help: detect open
  detect-shut:
    script: scripts/detect_shut.py
    help: detect shut
  check-evidence:
    script: scripts/check_evidence.py
    help: evidence invariant
  check-broken:
    script: scripts/check_broken.py
    help: broken invariant (fail-closed)
""",
        encoding="utf-8",
    )

    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "demo.yaml").write_text(_PROCESS_DEFINITION, encoding="utf-8")

    marker = repo / "_state"
    marker.write_text("open", encoding="utf-8")

    def _detect(state_name: str) -> str:
        return (
            "import json, sys, pathlib\n"
            "cur = pathlib.Path('_state').read_text().strip()\n"
            f"hit = cur == {state_name!r}\n"
            "print(json.dumps({'result': hit, 'reason': f'marker is {cur!r}'}))\n"
            "sys.exit(0)\n"
        )

    _write_script(scripts / "detect_open.py", _detect("open"))
    _write_script(scripts / "detect_shut.py", _detect("shut"))

    # Evidence invariant: holds iff a `_evidence_ok` marker exists.
    _write_script(
        scripts / "check_evidence.py",
        "import json, sys, pathlib\n"
        "ok = pathlib.Path('_evidence_ok').exists()\n"
        "print(json.dumps({'result': ok, 'reason': "
        "'all claims cited' if ok else 'uncited claim found'}))\n"
        "sys.exit(0)\n",
    )

    # Broken invariant: exits non-zero -> indeterminate (fail-closed).
    _write_script(
        scripts / "check_broken.py",
        "import sys\nsys.stderr.write('boom')\nsys.exit(3)\n",
    )

    return repo


def _engine(repo: Path) -> ProcessEngine:
    definition = load_definition(repo, "fixture:demo")
    return ProcessEngine(definition, repo)


def _set_evidence(repo: Path, ok: bool) -> None:
    marker = repo / "_evidence_ok"
    if ok:
        marker.write_text("", encoding="utf-8")
    elif marker.exists():
        marker.unlink()


# --- validate -------------------------------------------------------------


def test_validate_reports_violation_with_why(fixture_repo: Path) -> None:
    _set_evidence(fixture_repo, ok=False)
    outcomes = {inv.invariant_id: inv for inv in _engine(fixture_repo).evaluate_invariants()}

    assert set(outcomes) == {"evidence-backed", "derive-dont-store"}
    evidence = outcomes["evidence-backed"]
    assert evidence.holds is False
    assert evidence.indeterminate is False
    assert evidence.why == "Every factual claim must resolve to an evidence record."
    assert "uncited" in evidence.reason


def test_validate_reports_holding(fixture_repo: Path) -> None:
    _set_evidence(fixture_repo, ok=True)
    outcomes = {inv.invariant_id: inv for inv in _engine(fixture_repo).evaluate_invariants()}
    assert outcomes["evidence-backed"].holds is True


def test_indeterminate_check_is_fail_closed(fixture_repo: Path) -> None:
    # The broken predicate cannot be evaluated -> reported as NOT holding,
    # flagged indeterminate (a check that cannot be confirmed is a violation).
    outcomes = {inv.invariant_id: inv for inv in _engine(fixture_repo).evaluate_invariants()}
    broken = outcomes["derive-dont-store"]
    assert broken.holds is False
    assert broken.indeterminate is True


def test_validate_json_shape(fixture_repo: Path) -> None:
    _set_evidence(fixture_repo, ok=True)
    payload = json.loads(render_validate_json(_engine(fixture_repo)))
    assert payload["process"] == "fixture:demo"
    # ok is False because the broken invariant is fail-closed.
    assert payload["ok"] is False
    by_id = {inv["id"]: inv for inv in payload["invariants"]}
    assert by_id["evidence-backed"]["holds"] is True
    assert by_id["derive-dont-store"]["holds"] is False
    assert by_id["derive-dont-store"]["indeterminate"] is True


def test_validate_narrative_lists_invariants(fixture_repo: Path) -> None:
    _set_evidence(fixture_repo, ok=False)
    text = render_validate_narrative(_engine(fixture_repo))
    assert "evidence-backed" in text
    assert "uncited claim found" in text
    assert "violated" in text


def test_validate_position_independent_when_no_position(fixture_repo: Path) -> None:
    # No state's detection matches -> no position. Invariants still evaluate
    # (they are process-wide, not position-dependent).
    (fixture_repo / "_state").write_text("nowhere", encoding="utf-8")
    _set_evidence(fixture_repo, ok=True)
    outcomes = {inv.invariant_id: inv for inv in _engine(fixture_repo).evaluate_invariants()}
    assert outcomes["evidence-backed"].holds is True


# --- status surfacing -----------------------------------------------------


def test_violation_surfaces_on_status_narrative(fixture_repo: Path) -> None:
    _set_evidence(fixture_repo, ok=False)
    text = render_status_narrative(_engine(fixture_repo), actor="agent")
    assert "Invariant violations:" in text
    assert "evidence-backed" in text


def test_violation_surfaces_on_status_json(fixture_repo: Path) -> None:
    _set_evidence(fixture_repo, ok=False)
    payload = json.loads(render_status_json(_engine(fixture_repo), actor="agent"))
    by_id = {inv["id"]: inv for inv in payload["invariants"]}
    assert by_id["evidence-backed"]["holds"] is False
    # The full set is carried on status JSON (not just violations).
    assert "derive-dont-store" in by_id


def test_holding_invariant_not_shown_in_status_narrative(fixture_repo: Path) -> None:
    # Status narrative shows only violations (terse). evidence-backed holds;
    # derive-dont-store is fail-closed (a violation) and IS shown.
    _set_evidence(fixture_repo, ok=True)
    text = render_status_narrative(_engine(fixture_repo), actor="agent")
    assert "Invariant violations:" in text
    assert "derive-dont-store" in text
    # The holding one is not surfaced as a violation.
    assert "evidence-backed" not in text


# --- read-only ------------------------------------------------------------


def test_validate_writes_no_journal(fixture_repo: Path) -> None:
    engine = _engine(fixture_repo)
    engine.evaluate_invariants()
    render_validate_json(engine)
    render_validate_narrative(engine)
    assert not engine.journal_path().is_file()


def test_status_with_invariants_writes_no_journal(fixture_repo: Path) -> None:
    _set_evidence(fixture_repo, ok=False)
    engine = _engine(fixture_repo)
    render_status_narrative(engine, actor="agent")
    render_status_json(engine, actor="agent")
    assert not engine.journal_path().is_file()


# --- behaviour-preserving (no invariants) ---------------------------------


_NO_INVARIANTS = """\
process:
  id: bare
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: open
      meaning: Open.
      detection:
        mode: inferred
        predicate:
          run: detect-open
  transitions: []
"""


def test_process_without_invariants_reports_empty(fixture_repo: Path) -> None:
    schemas = fixture_repo / ".pkit" / "capabilities" / "fixture" / "schemas"
    (schemas / "bare.yaml").write_text(_NO_INVARIANTS, encoding="utf-8")
    definition = load_definition(fixture_repo, "fixture:bare")
    engine = ProcessEngine(definition, fixture_repo)

    assert engine.evaluate_invariants() == []
    payload = json.loads(render_validate_json(engine))
    assert payload["ok"] is True
    assert payload["invariants"] == []
    # Status narrative shows no violations section when there are none.
    text = render_status_narrative(engine, actor="agent")
    assert "Invariant violations:" not in text


# --- CLI wiring -----------------------------------------------------------


def test_cli_validate_json_and_exit_code(fixture_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_evidence(fixture_repo, ok=False)
    monkeypatch.chdir(fixture_repo)
    runner = CliRunner()
    result = runner.invoke(main, ["process", "validate", "fixture:demo", "--json"])
    # A violation -> non-zero exit.
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert any(inv["id"] == "evidence-backed" and not inv["holds"] for inv in payload["invariants"])


def test_cli_validate_passes_when_all_hold(fixture_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Drop the broken invariant so every check can hold, then satisfy evidence.
    schemas = fixture_repo / ".pkit" / "capabilities" / "fixture" / "schemas"
    only_evidence = _PROCESS_DEFINITION.split("    - id: derive-dont-store")[0]
    (schemas / "demo.yaml").write_text(only_evidence, encoding="utf-8")
    _set_evidence(fixture_repo, ok=True)

    monkeypatch.chdir(fixture_repo)
    runner = CliRunner()
    result = runner.invoke(main, ["process", "validate", "fixture:demo"])
    assert result.exit_code == 0
    assert "all invariants hold" in result.output
