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


def test_load_definition_scan_finds_id_in_offnamed_file(fixture_repo: Path) -> None:
    # No file named `<id>.yaml`: the scan-fallback finds the lone file whose
    # process.id matches.
    schemas = fixture_repo / ".pkit" / "capabilities" / "fixture" / "schemas"
    (schemas / "off-named.yaml").write_text(
        "process:\n  id: scanned\n  version: 1\n", encoding="utf-8"
    )
    definition = load_definition(fixture_repo, "fixture:scanned")
    assert definition.process_id == "scanned"


def test_load_definition_scan_raises_on_duplicate_id(fixture_repo: Path) -> None:
    # Two files claiming one process.id is a definition bug, not something to
    # resolve silently by sort order -> raise rather than return the first.
    schemas = fixture_repo / ".pkit" / "capabilities" / "fixture" / "schemas"
    (schemas / "dup-a.yaml").write_text(
        "process:\n  id: clashing\n  version: 1\n", encoding="utf-8"
    )
    (schemas / "dup-b.yaml").write_text(
        "process:\n  id: clashing\n  version: 1\n", encoding="utf-8"
    )
    with pytest.raises(ProcessError) as exc:
        load_definition(fixture_repo, "fixture:clashing")
    msg = str(exc.value)
    assert "dup-a.yaml" in msg and "dup-b.yaml" in msg


# --- CLI wiring -----------------------------------------------------------


# --- keyed cardinality (COR-032) ------------------------------------------


# A keyed process: position is per-subject. Each detect-* predicate reports
# result=true when a per-subject marker file `_state.<subject>` matches it, so
# two subjects resolve independently.
_KEYED_DEFINITION = """\
process:
  id: keyed-demo
  version: 1
  subject:
    cardinality: keyed
    key: unit-id
  states:
    - id: open
      meaning: Unit is open.
      detection:
        mode: inferred
        predicate:
          run: kdetect-open
    - id: shut
      meaning: Unit is shut.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: kdetect-shut
  transitions:
    - from: open
      to: shut
      trigger: shut
      authorisation: agent-autonomous
"""


@pytest.fixture
def keyed_repo(tmp_path: Path) -> Path:
    """A repo with a keyed fixture capability.

    Each detect predicate reads its subject id (first argv) and a per-subject
    marker file `_state.<subject>`, so two subjects resolve to different states.
    """
    repo = tmp_path
    pkit = repo / ".pkit"

    defs_dst = pkit / "schemas" / "_defs"
    defs_dst.mkdir(parents=True, exist_ok=True)
    source_defs = (
        Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
    )
    shutil.copy(source_defs, defs_dst / "process.schema.json")

    cap = pkit / "capabilities" / "kfixture"
    scripts = cap / "scripts"
    cap.mkdir(parents=True, exist_ok=True)

    (cap / "package.yaml").write_text(
        """schema_version: 2
component:
  kind: capability
  name: kfixture
  version: 0.1.0
description: Keyed fixture capability for process-engine tests.
commands:
  kdetect-open:
    script: scripts/kdetect_open.py
    help: detect open
  kdetect-shut:
    script: scripts/kdetect_shut.py
    help: detect shut
""",
        encoding="utf-8",
    )

    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    (cap / "schemas" / "keyed-demo.yaml").write_text(_KEYED_DEFINITION, encoding="utf-8")

    # Per-subject detect: argv[1] is the subject id; the marker is _state.<subject>.
    def _detect(state_name: str) -> str:
        return (
            "import json, sys, pathlib\n"
            "subject = sys.argv[1]\n"
            "marker = pathlib.Path(f'_state.{subject}')\n"
            "cur = marker.read_text().strip() if marker.exists() else ''\n"
            f"hit = cur == {state_name!r}\n"
            "print(json.dumps({'result': hit, 'subject': subject, "
            "'reason': f'{subject} marker is {cur!r}'}))\n"
            "sys.exit(0)\n"
        )

    _write_script(scripts / "kdetect_open.py", _detect("open"))
    _write_script(scripts / "kdetect_shut.py", _detect("shut"))

    return repo


def _keyed_set_state(repo: Path, subject: str, state: str) -> None:
    (repo / f"_state.{subject}").write_text(state, encoding="utf-8")


def test_keyed_resolves_each_subject_independently(keyed_repo: Path) -> None:
    _keyed_set_state(keyed_repo, "42", "open")
    _keyed_set_state(keyed_repo, "99", "shut")
    definition = load_definition(keyed_repo, "kfixture:keyed-demo")

    pos_42 = ProcessEngine.for_subject(definition, keyed_repo, "42").resolve_position()
    pos_99 = ProcessEngine.for_subject(definition, keyed_repo, "99").resolve_position()
    assert pos_42.state_id == "open"
    assert pos_99.state_id == "shut"


def test_keyed_journal_is_per_subject(keyed_repo: Path) -> None:
    _keyed_set_state(keyed_repo, "42", "open")
    definition = load_definition(keyed_repo, "kfixture:keyed-demo")
    engine = ProcessEngine.for_subject(definition, keyed_repo, "42")
    result = engine.move("shut", actor="agent")
    assert result.ok is True
    assert engine.journal_path().name == "42.journal.jsonl"
    assert engine.journal_path().is_file()
    # A different subject has its own (here, absent) journal.
    other = ProcessEngine.for_subject(definition, keyed_repo, "99")
    assert other.journal_path().name == "99.journal.jsonl"
    assert not other.journal_path().is_file()
    entry = json.loads(engine.journal_path().read_text().splitlines()[0])
    assert entry["subject"] == "42"


def test_keyed_requires_subject(keyed_repo: Path) -> None:
    definition = load_definition(keyed_repo, "kfixture:keyed-demo")
    with pytest.raises(ProcessError) as exc:
        ProcessEngine.for_subject(definition, keyed_repo, None)
    assert "keyed" in str(exc.value)
    assert "--subject" in str(exc.value)
    # Empty string is treated as missing too.
    with pytest.raises(ProcessError):
        ProcessEngine.for_subject(definition, keyed_repo, "")


def test_singleton_ignores_subject_and_uses_fixed_key(fixture_repo: Path) -> None:
    definition = load_definition(fixture_repo, "fixture:demo")
    # A supplied subject on a singleton process is ignored; the fixed key wins.
    engine = ProcessEngine.for_subject(definition, fixture_repo, "ignored")
    assert engine.subject == SINGLETON_SUBJECT
    # And no --subject at all also works (the singleton default).
    engine2 = ProcessEngine.for_subject(definition, fixture_repo, None)
    assert engine2.subject == SINGLETON_SUBJECT


def test_keyed_cli_requires_subject(keyed_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subprocess.run(["git", "init", "-q"], cwd=keyed_repo, check=True)
    monkeypatch.chdir(keyed_repo)
    runner = CliRunner()
    # No --subject on a keyed process -> a clear error, non-zero exit.
    missing = runner.invoke(main, ["process", "status", "kfixture:keyed-demo", "--json"])
    assert missing.exit_code != 0
    assert "keyed" in missing.output

    # With --subject it resolves that subject's position.
    _keyed_set_state(keyed_repo, "7", "open")
    ok = runner.invoke(
        main, ["process", "status", "kfixture:keyed-demo", "--subject", "7", "--json"]
    )
    assert ok.exit_code == 0, ok.output
    payload = json.loads(ok.output)
    assert payload["subject"] == "7"
    assert payload["position"]["state"] == "open"


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


def test_cli_move_cross_authority_bites_on_real_actor(
    fixture_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The cross-authority gate (ready -> done) compares the authorisation
    # artifact's producer login against the `--actor` login. Threading the REAL
    # invoker login (not an authorisation token) is what makes it bite: a
    # self-approval (produced_by == actor) refuses; a different authority passes.
    subprocess.run(["git", "init", "-q"], cwd=fixture_repo, check=True)
    monkeypatch.chdir(fixture_repo)
    runner = CliRunner()
    _set_state(fixture_repo, "ready")
    # The review verdict was produced by login "alice".
    (fixture_repo / "_review").write_text(json.dumps({"by": "alice"}), encoding="utf-8")

    # Same login drives the move -> self-approval -> refused.
    same = runner.invoke(
        main, ["process", "move", "fixture:demo", "--to", "done", "--actor", "alice"]
    )
    assert same.exit_code == 1, same.output
    assert "refused" in same.output

    # A different login drives the move -> cross-authority satisfied -> moves.
    other = runner.invoke(
        main, ["process", "move", "fixture:demo", "--to", "done", "--actor", "bob"]
    )
    assert other.exit_code == 0, other.output
    assert "moved to 'done'" in other.output


def test_resolve_actor_identity_uses_gh_login(monkeypatch: pytest.MonkeyPatch) -> None:
    # The `--actor` default must resolve a real gh login (not a token), so the
    # cross-authority comparison is against the right namespace.
    from project_kit import cli as cli_mod

    def _fake_run(argv, **kwargs):
        assert argv == ["gh", "api", "user", "-q", ".login"]
        return subprocess.CompletedProcess(argv, 0, stdout="octocat\n", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert cli_mod._resolve_actor_identity() == "octocat"


def test_resolve_actor_identity_falls_back_when_gh_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from project_kit import cli as cli_mod

    def _no_gh(argv, **kwargs):
        raise FileNotFoundError("gh not installed")

    monkeypatch.setattr(subprocess, "run", _no_gh)
    assert cli_mod._resolve_actor_identity() == "operator"
