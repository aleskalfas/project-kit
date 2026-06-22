"""Schema-shape tests for the COR-034 blocked / human-pause additions.

Validates a `process` definition fragment against the shape contract
(`_defs/process.schema.json#/$defs/process`), covering:

- the optional `blocked` wait on a subject (accepted),
- per-reason `resume_when` (COR-034): REQUIRED for awaiting-condition,
  FORBIDDEN for awaiting-human,
- a `prompt` on a `user`-authorisation transition (accepted),
- rejection of a malformed `blocked` (bad `blocked_on`, unknown sub-field),
- rejection of a `prompt` on a non-`user` move (it is the human-pause case),
- the additive guarantee: a definition carrying NEITHER validates unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
)


def _process_validator() -> Draft202012Validator:
    """A validator for the `process` $def, with sibling $defs carried so the
    cross-references (`subject`, `transition`, `blocked`, `predicate`) resolve."""
    full = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = full["$defs"]
    schema = dict(defs["process"])
    schema["$defs"] = defs
    return Draft202012Validator(schema)


def _errors(definition: dict[str, Any]) -> list[str]:
    return [e.message for e in _process_validator().iter_errors(definition)]


def _base_definition() -> dict[str, Any]:
    """A minimal valid singleton process, no blocked / prompt."""
    return {
        "id": "demo",
        "version": 1,
        "subject": {"cardinality": "singleton"},
        "states": [
            {
                "id": "parked",
                "meaning": "Waiting.",
                "detection": {"mode": "inferred", "predicate": {"run": "detect-parked"}},
            }
        ],
        "transitions": [
            {
                "from": "parked",
                "to": "done",
                "trigger": "go",
                "authorisation": "user",
            }
        ],
    }


def test_blockless_promptless_definition_validates() -> None:
    # The additive guarantee: an existing definition (neither field) is valid.
    assert _errors(_base_definition()) == []


def test_blocked_awaiting_human_without_resume_validates() -> None:
    # awaiting-human carries NO resume_when (COR-034): its resume is the person
    # taking the move, never a side-predicate.
    definition = _base_definition()
    definition["subject"]["blocked"] = {
        "blocked_on": "awaiting-human",
        "assignee": "reviewer",
    }
    assert _errors(definition) == []


def test_blocked_awaiting_human_with_resume_rejected() -> None:
    # A resume_when on awaiting-human is FORBIDDEN — the side-predicate could
    # disagree with the (gate-closed) move and falsely report "not waiting".
    definition = _base_definition()
    definition["subject"]["blocked"] = {
        "blocked_on": "awaiting-human",
        "resume_when": {"run": "resume-when-reviewed"},
    }
    assert _errors(definition), "awaiting-human with a resume_when must be rejected"


def test_blocked_awaiting_condition_without_assignee_validates() -> None:
    definition = _base_definition()
    definition["subject"]["blocked"] = {
        "blocked_on": "awaiting-condition",
        "resume_when": {"run": "resume-when-window-open"},
    }
    assert _errors(definition) == []


def test_blocked_awaiting_condition_without_resume_rejected() -> None:
    # awaiting-condition REQUIRES a resume_when — the external fact the engine
    # re-checks live to auto-clear.
    definition = _base_definition()
    definition["subject"]["blocked"] = {"blocked_on": "awaiting-condition"}
    assert _errors(definition), "awaiting-condition without resume_when must be rejected"


def test_prompt_on_user_move_validates() -> None:
    definition = _base_definition()
    definition["transitions"][0]["prompt"] = "Which areas to keep?"
    assert _errors(definition) == []


def test_blocked_on_outside_enum_rejected() -> None:
    definition = _base_definition()
    definition["subject"]["blocked"] = {
        # A cross-subject reason that COR-034 explicitly defers.
        "blocked_on": "awaiting-subprocess-outcome",
        "resume_when": {"run": "resume"},
    }
    assert _errors(definition), "an unshipped blocked_on reason must be rejected"


def test_blocked_unknown_subfield_rejected() -> None:
    definition = _base_definition()
    definition["subject"]["blocked"] = {
        "blocked_on": "awaiting-condition",
        "resume_when": {"run": "resume"},
        "selection": ["a", "b"],  # the deferred option-set is not shipped
    }
    assert _errors(definition), "an unshipped blocked sub-field must be rejected"


def test_prompt_on_non_user_move_rejected() -> None:
    # A prompt is the question posed to a PERSON, so it is meaningful only on a
    # user-authorisation move (COR-034); an agent/script move carrying one is a
    # definition error.
    definition = _base_definition()
    definition["transitions"][0]["authorisation"] = "agent-autonomous"
    definition["transitions"][0]["prompt"] = "Should not be here."
    assert _errors(definition), "a prompt on a non-user move must be rejected"
