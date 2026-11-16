"""The documents the process engine's commands and the wiring graph print hold their
contracts (ADR-097 point 7).

Each command runs once on a capability of the test's own, whose one process has a state
held for a person, a move a person takes, and an invariant; its predicates run in the
test's own process (`tests.in_process.start_in_process`). What that run does not reach is
built by the functions the command prints through: the status of an engine whose
answers are given, a cascade's fold, a health report and a graph holding every kind of
edge. `tests/test_backbone_documents.py` gathers the contracts here into its ratchet.
"""

from __future__ import annotations

import json
import stat
import textwrap
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from project_kit import connections as cx
from project_kit import process as engine_mod
from project_kit import process_graph as pg
from project_kit import process_health as ph
from project_kit.process import ProcessEngine, load_definition
from tests.backbone_documents import JSON_OPTION, document_of, invoke
from tests.document_contracts import Contract, Form, check
from tests.in_process import start_in_process

ADDRESS = "fixture:demo"

_DEFINITION = """\
process:
  id: demo
  version: 1
  subject:
    cardinality: singleton
    domain_ref: fixture
    blocked:
      blocked_on: awaiting-human
      assignee: the-reviewer
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
      trigger: approve
      authorisation: user
      gate:
        kind: authorisation-artifact
        predicate:
          run: gate-review
      why: Approve once a reviewer has signed off.
      hint: pkit process move fixture:demo --to shut
      prompt: Approve it, or send it back?
  invariants:
    - id: holds
      check:
        run: check-holds
      why: It holds.
"""

_PACKAGE = """\
schema_version: 2
component:
  kind: capability
  name: fixture
  version: 0.1.0
description: A capability whose process the documents' tests read.
commands:
  detect-open:
    script: scripts/detect_open.py
    help: detect open
  detect-shut:
    script: scripts/detect_shut.py
    help: detect shut
  gate-review:
    script: scripts/gate_review.py
    help: a reviewer's verdict
  check-holds:
    script: scripts/check_holds.py
    help: the invariant
"""

#: What each predicate answers.
_ANSWERS = {
    "detect_open": {"result": True, "reason": "it is open"},
    "detect_shut": {"result": False, "reason": "it is not shut"},
    "gate_review": {"exists": False, "result": False, "reason": "no verdict yet"},
    "check_holds": {"result": True, "reason": "it holds"},
}


def _write_script(path: Path, answer: Mapping[str, Any]) -> None:
    """A predicate script whose `main` prints `answer`, as a process and in this process
    alike."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"import json\nprint(json.dumps({dict(answer)!r}))\nreturn 0\n"
    code = "import sys\n\n\ndef main():\n" + textwrap.indent(body, "    ")
    code += "\n\nif __name__ == '__main__':\n    sys.exit(main())\n"
    path.write_text("#!/usr/bin/env python3\n" + code, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project holding the capability, the process's shape contract staged, its
    predicates started in this process, run from its root."""
    pkit = tmp_path / ".pkit"
    (pkit / "schemas" / "_defs").mkdir(parents=True)
    (pkit / "manifest.yaml").write_text("backbone_version: 0.0.0\n", encoding="utf-8")
    source = Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs"
    (pkit / "schemas" / "_defs" / "process.schema.json").write_text(
        (source / "process.schema.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    capability = pkit / "capabilities" / "fixture"
    (capability / "schemas").mkdir(parents=True)
    (capability / "package.yaml").write_text(_PACKAGE, encoding="utf-8")
    (capability / "schemas" / "demo.yaml").write_text(_DEFINITION, encoding="utf-8")
    for name, answer in _ANSWERS.items():
        _write_script(capability / "scripts" / f"{name}.py", answer)
    start_in_process(monkeypatch)
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --- `pkit process status --json`, `validate --json` and `cascade --json` ------------------

_OUTCOME_KEYS = {
    "runs": "str",
    "outcome": "str|null",
    "indeterminate": "bool",
    "reason": "str",
    "stderr_tail": "str|null",
}

#: A cascade's fold, as the engine's status and its `cascade` operation give it.
CASCADE = Form(
    keys={
        **_OUTCOME_KEYS,
        "op": "str",
        "threshold": "int|null",
        "reached": "int",
        "total": "int",
        "opened": "bool",
    }
)

#: An invariant's verdict, as the status and `validate` give it.
INVARIANT = Form(
    keys={
        "id": "str",
        "holds": "bool",
        "indeterminate": "bool",
        "why": "str",
        "reason": "str",
        "stderr_tail": "str|null",
    }
)

_DEFINITION_KEYS = {"process": "str", "subject": "str", "version": "int"}

PROCESS_STATUS = Contract(
    name="pkit process status --json",
    forms={
        "answer": Form(
            keys={
                **_DEFINITION_KEYS,
                "position": "object",
                "position.state": "str|null",
                "position.indeterminate": "bool",
                "position.meaning": "str|null",
                "position.terminal": "bool|null",
                "position.unevaluated": "list",
                "position.unevaluated[]": "object",
                "position.unevaluated[].state": "str",
                "position.unevaluated[].reason": "str",
                "position.unevaluated[].stderr_tail": "str|null",
                "position.placed_nowhere": "list",
                "position.placed_nowhere[]": "object",
                "position.placed_nowhere[].predicate": "str",
                "position.placed_nowhere[].reason": "str",
                "position.subprocess": "object|null",
                **{f"position.subprocess.{key}": kind for key, kind in _OUTCOME_KEYS.items()},
                "position.cascade": "object|null",
                "blocked": "object|null",
                "blocked.blocked_on": "str",
                "blocked.at": "str|null",
                "blocked.resume_reason": "str",
                "blocked.since": "str|null",
                "blocked.assignee": "str|null",
                "blocked.prompt": "str|null",
                "blocked.stderr_tail": "str|null",
                "invariants": "list",
                "invariants[]": "object",
                "journal_logging": "object",
                "journal_logging.enabled": "bool",
                "journal_logging.committed": "bool",
                "journal": "list",
                "journal[]": "object",
                "legal_moves": "list",
                "legal_moves[]": "object",
                "legal_moves[].to": "str",
                "legal_moves[].trigger": "str",
                "legal_moves[].allowed": "bool",
                "legal_moves[].indeterminate": "bool",
                "legal_moves[].reason": "str",
                "legal_moves[].stderr_tail": "str|null",
                "legal_moves[].why": "str|null",
                "legal_moves[].hint": "str|null",
                "legal_moves[].prompt": "str|null",
            }
        )
    },
    shapes={"cascade": CASCADE, "invariant": INVARIANT},
    refs={"position.cascade": "cascade", "invariants[]": "invariant"},
    sets={
        "blocked.blocked_on": frozenset(
            {
                "awaiting-human",
                "awaiting-condition",
                "awaiting-subprocess-outcome",
                "awaiting-cascade-outcome",
            }
        ),
        "cascade:op": frozenset({"all", "count"}),
    },
    # Each entry is a line of the process's journal as its file holds it, whose format
    # is decided apart (ADR-097 point 1).
    payloads=frozenset({"journal[]"}),
)

PROCESS_VALIDATE = Contract(
    name="pkit process validate --json",
    forms={
        "answer": Form(
            keys={**_DEFINITION_KEYS, "ok": "bool", "invariants": "list", "invariants[]": "object"}
        )
    },
    shapes={"invariant": INVARIANT},
    refs={"invariants[]": "invariant"},
)

PROCESS_CASCADE = Contract(
    name="pkit process cascade --json",
    forms={"answer": Form(keys={"cascade": "object|null"})},
    shapes={"cascade": CASCADE},
    refs={"cascade": "cascade"},
    sets={"cascade:op": frozenset({"all", "count"})},
)


def _folds() -> list[engine_mod.CascadeResolution]:
    """A fold of each operation: one opened, one held, one that could not be read."""
    return [
        engine_mod.CascadeResolution(
            "fixture:member", "all", "verified", None, 2, 2, True, False, "every member"
        ),
        engine_mod.CascadeResolution(
            "fixture:member", "count", "verified", 3, 1, 4, False, False, "one of four"
        ),
        engine_mod.CascadeResolution(
            "fixture:member", "all", None, None, 0, 0, False, True, "unread", "store locked"
        ),
    ]


def _answered(monkeypatch: pytest.MonkeyPatch, fold: engine_mod.CascadeResolution) -> None:
    """The engine answering with a position no state's detection places, each kind of
    state it could not read, a subprocess it waits on, `fold`, a held state with all its
    parts, a violated invariant, and a journal kept with one entry."""
    position = engine_mod.Position(
        None,
        True,
        {
            "open": engine_mod.PredicateOutcome(
                False, "could not run", indeterminate=True, stderr_tail="boom"
            )
        },
        placed_nowhere=(("detect-open", "no state fits"),),
    )
    inner = engine_mod.SubprocessResolution("fixture:inner", "done", False, "it ended", "")
    held = engine_mod.BlockedState(
        "awaiting-condition", "open", "waits on a condition", "2026-10-01", "a-person", "Go?", "x"
    )
    invariant = engine_mod.InvariantOutcome("holds", False, "It holds.", "failed", True, "broke")
    entry = {"at": "2026-10-01T10:00:00Z", "to": "shut", "anything": ["its", "own"]}
    monkeypatch.setattr(ProcessEngine, "resolve_position", lambda self: position)
    monkeypatch.setattr(ProcessEngine, "resolve_subprocess_outcome", lambda self, state: inner)
    monkeypatch.setattr(ProcessEngine, "resolve_cascade_outcome", lambda self: fold)
    monkeypatch.setattr(ProcessEngine, "_has_cascade_gated_move", lambda self, state: True)
    monkeypatch.setattr(ProcessEngine, "evaluate_blocked", lambda self, *args: held)
    monkeypatch.setattr(ProcessEngine, "evaluate_invariants", lambda self: [invariant])
    monkeypatch.setattr(ProcessEngine, "read_journal", lambda self: [entry])


def _held_states(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """The status of a held state for each reason the engine holds one."""
    documents = []
    for reason in sorted(PROCESS_STATUS.sets["blocked.blocked_on"]):
        held = engine_mod.BlockedState(reason, "open", "why it waits")
        monkeypatch.setattr(ProcessEngine, "evaluate_blocked", lambda self, *args, h=held: h)
        documents.append(json.loads(engine_mod.render_status_json(_engine(), actor="agent")))
    return documents


def _engine() -> ProcessEngine:
    return ProcessEngine(load_definition(Path.cwd(), ADDRESS), Path.cwd())


def test_the_process_engine_documents_hold_their_contracts(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status = document_of(invoke("process", "status", ADDRESS, JSON_OPTION))
    validated = document_of(invoke("process", "validate", ADDRESS, JSON_OPTION))
    no_cascade = document_of(invoke("process", "cascade", ADDRESS, JSON_OPTION))
    built: list[dict[str, Any]] = []
    folded: list[dict[str, Any]] = []
    for fold in _folds():
        _answered(monkeypatch, fold)
        built.append(json.loads(engine_mod.render_status_json(_engine(), actor="agent")))
        folded.append(document_of(invoke("process", "cascade", ADDRESS, JSON_OPTION)))
    violated = json.loads(engine_mod.render_validate_json(_engine()))
    check(PROCESS_STATUS, {"answer": [status, *built, *_held_states(monkeypatch)]})
    check(PROCESS_VALIDATE, {"answer": [validated, violated]})
    check(PROCESS_CASCADE, {"answer": [no_cascade, *folded]})


# --- `pkit process health --json` ------------------------------------------------------------

_SUBJECT_FINDING = {"subject": "str|null", "reason": "str", "stderr_tail": "str|null"}
_CONTRACT_KEYS = {
    "contracts": "list",
    "contracts[]": "object",
    "contracts[].upstream": "str",
    "contracts[].downstream": "str",
    "contracts[].trigger": "str|null",
    "contracts[].state": "str|null",
    "contracts[].indeterminate": "list",
    "contracts[].indeterminate[]": "object",
    **{f"contracts[].indeterminate[].{key}": kind for key, kind in _SUBJECT_FINDING.items()},
    "contracts[].counts": "object",
    "contracts[].counts.indeterminate": "int",
    "skipped": "list",
    "skipped[]": "object",
    "skipped[].address": "str",
    "skipped[].reason": "str",
    "unresolved_scope": "object|null",
    "unresolved_scope.address": "str",
    "unresolved_scope.reason": "str",
    "view": "str",
    "totals": "object",
    "totals.indeterminate": "int",
}

PROCESS_HEALTH = Contract(
    name="pkit process health --json",
    forms={
        "full": Form(
            keys={
                **_CONTRACT_KEYS,
                "contracts[].misses": "list",
                "contracts[].misses[]": "object",
                "contracts[].misses[].subject": "str|null",
                "contracts[].misses[].reason": "str",
                "contracts[].counts.at_trigger": "int",
                "contracts[].counts.satisfied": "int",
                "contracts[].counts.missed": "int",
                "totals.missed": "int",
            }
        ),
        "interpretation only": Form(keys=_CONTRACT_KEYS),
    },
    sets={"view": frozenset({"full", "interpretation-only"})},
)


def _health() -> ph.HealthReport:
    """A report with a contract that missed one subject, could not read another and
    names no trigger, a definition skipped, and a scope that named nothing."""
    contract = ph.HandoffContract(
        "fixture:demo", "fixture:upstream", "open", {"trigger": "done"}, "fixture", Path(".")
    )
    untriggered = ph.HandoffContract(
        "fixture:demo", "fixture:other", None, None, "fixture", Path(".")
    )
    findings = (
        ph.Finding("7", ph.KIND_MISSED, "not picked up"),
        ph.Finding("8", ph.KIND_INDETERMINATE, "could not tell", "boom"),
        ph.Finding(None, ph.KIND_INDETERMINATE, "the contract is malformed"),
    )
    return ph.HealthReport(
        (ph.ContractReport(contract, findings, 3, 1), ph.ContractReport(untriggered, (), 0, 0)),
        (ph.SkippedDefinition("fixture:broken", "unreadable"),),
        ph.UnresolvedScope("fixture:nowhere", "no such process"),
    )


def _interpretation(report: ph.HealthReport) -> ph.InterpretationReport:
    return ph.InterpretationReport(
        tuple(ph.ContractInterpretation(c.contract, c.indeterminate) for c in report.contracts),
        report.skipped,
        report.unresolved_scope,
    )


def test_the_health_documents_hold_their_contract(project: Path) -> None:
    full = document_of(invoke("process", "health", JSON_OPTION))
    interpreted = document_of(invoke("process", "health", "--interpretation-only", JSON_OPTION))
    report = _health()
    check(
        PROCESS_HEALTH,
        {
            "full": [full, json.loads(ph.render_json(report))],
            "interpretation only": [
                interpreted,
                json.loads(ph.render_interpretation_json(_interpretation(report))),
            ],
        },
        enumerations={"view": (ph.VIEW_FULL, ph.VIEW_INTERPRETATION_ONLY)},
    )


# --- `pkit process graph --json` and `pkit connections graph --json` -----------------------

_GRAPH_KEYS = {
    "nodes": "list",
    "nodes[]": "str",
    "edges": "list",
    "edges[]": "object",
    "edges[].from": "str",
    "edges[].from_state": "str|null",
    "edges[].to": "str",
    "edges[].relation": "str",
    "edges[].mode": "str",
    "edges[].source": "str",
    "edges[].why": "str|null",
    "skipped": "list",
    "skipped[]": "object",
    "skipped[].address": "str",
    "skipped[].reason": "str",
}

_DEFINER_MODES = ("active", "not selected", "conflict")
_PROCESS_RELATIONS = frozenset(
    {
        "composed-subprocess",
        "aggregates",
        "informational",
        "gates-on-readiness",
        "triggered-by",
        "constrained-with",
        "offers",
    }
)
_WIRING_RELATIONS = frozenset({"accepts", "contributes", "fills", "emits", "subscribes"})
_PROCESS_MODES = frozenset({"pull", "push", *_DEFINER_MODES})
_BINDINGS = frozenset(
    {
        "bound",
        "inert (version)",
        "inert (provider)",
        "no active provider",
        "no such point",
        "not installed",
    }
)


def _graph_contract(command: str, relations: frozenset[str], modes: frozenset[str]) -> Contract:
    return Contract(
        name=f"pkit {command} --json",
        forms={"answer": Form(keys=_GRAPH_KEYS)},
        sets={
            "edges[].relation": relations,
            "edges[].mode": modes,
            "edges[].source": frozenset({"derived", "annotated", "resolved"}),
        },
    )


PROCESS_GRAPH = _graph_contract("process graph", _PROCESS_RELATIONS, _PROCESS_MODES)
CONNECTIONS_GRAPH = _graph_contract(
    "connections graph", _PROCESS_RELATIONS | _WIRING_RELATIONS, _PROCESS_MODES | _BINDINGS
)


def _edges(relations: frozenset[str], modes: frozenset[str]) -> list[pg.Edge]:
    """An edge of each relation and of each mode, each from its source."""
    sources = {pg.RELATION_COMPOSED: pg.SOURCE_DERIVED, pg.RELATION_AGGREGATES: pg.SOURCE_DERIVED}
    sources |= {relation: pg.SOURCE_ANNOTATED for relation in pg.ANNOTATED_RELATIONS}
    ordered_modes = sorted(modes)
    return [
        pg.Edge(
            "fixture:demo",
            f"fixture:{index}",
            relation,
            ordered_modes[index % len(ordered_modes)],
            sources.get(relation, pg.SOURCE_RESOLVED),
            from_state="open" if index % 2 else None,
            why="a reason" if index % 2 else None,
        )
        for index, relation in enumerate(sorted(relations) + ["informational"] * len(modes))
    ]


def _graph(relations: frozenset[str], modes: frozenset[str]) -> dict[str, Any]:
    graph = pg.Graph(
        ("fixture:demo",),
        tuple(_edges(relations, modes)),
        (pg.Skipped("fixture:broken", "unreadable"),),
    )
    return json.loads(pg.render_json(graph))


def test_the_graph_documents_hold_their_contracts(project: Path) -> None:
    check(
        PROCESS_GRAPH,
        {
            "answer": [
                document_of(invoke("process", "graph", JSON_OPTION)),
                _graph(_PROCESS_RELATIONS, _PROCESS_MODES),
            ]
        },
        enumerations={
            "edges[].relation": (*pg.DERIVED_RELATIONS, *pg.ANNOTATED_RELATIONS, pg.RELATION_OFFERS)
        },
    )
    check(
        CONNECTIONS_GRAPH,
        {
            "answer": [
                document_of(invoke("connections", "graph", JSON_OPTION)),
                _graph(_PROCESS_RELATIONS | _WIRING_RELATIONS, _PROCESS_MODES | _BINDINGS),
            ]
        },
        enumerations={"edges[].mode": (status.value for status in cx.BindingStatus)},
    )


#: The contracts of each process command, and of the wiring graph, by the command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "process status": (PROCESS_STATUS,),
    "process validate": (PROCESS_VALIDATE,),
    "process cascade": (PROCESS_CASCADE,),
    "process health": (PROCESS_HEALTH,),
    "process graph": (PROCESS_GRAPH,),
    "connections graph": (CONNECTIONS_GRAPH,),
}
