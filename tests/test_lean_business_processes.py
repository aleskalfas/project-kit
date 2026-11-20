"""The lean-business capability's process definitions (lean-business DEC-003 point 1). This
repository does not install the capability, so no `pkit validate` of it reads them: each is
held here to what validation would hold it to. It conforms to the shape contract, loads as
the engine loads it, with detections the engine can read, and names only predicates the
capability registers, each with a script that exists."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import process
from project_kit.command_runner import registered_commands
from project_kit.process_authoring import lint_process_block

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit/capabilities/lean-business"


def _process_block(path: Path) -> dict[str, Any] | None:
    raw = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    block = raw.get("process") if isinstance(raw, dict) else None
    return block if isinstance(block, dict) else None


#: Each process definition the capability declares, by its id: a schema file whose top-level
#: block is `process:`, as the engine's discovery finds one.
DEFINITIONS = {
    block["id"]: block
    for block in (_process_block(path) for path in sorted((CAPABILITY / "schemas").glob("*.yaml")))
    if block is not None
}


def _predicates(node: object) -> list[str]:
    """The command each predicate of a definition names, in the order the definition names
    them: every mapping with a `run`, which the shape contract gives a predicate alone."""
    if isinstance(node, dict):
        run = node.get("run")
        named = [run] if isinstance(run, str) else []
        return named + [found for value in node.values() for found in _predicates(value)]
    if isinstance(node, list):
        return [found for value in node for found in _predicates(value)]
    return []


def test_the_capability_declares_a_process_for_each_kind_of_subject() -> None:
    assert sorted(DEFINITIONS) == ["cycle-lifecycle", "desk-stage", "experiment-lifecycle"]


@pytest.mark.parametrize("name", sorted(DEFINITIONS))
def test_it_conforms_to_the_shape_contract(name: str) -> None:
    assert lint_process_block(REPO, DEFINITIONS[name]) == []


@pytest.mark.parametrize("name", sorted(DEFINITIONS))
def test_it_loads_as_the_engine_loads_it_with_detections_it_can_read(name: str) -> None:
    definition = process.load_definition(REPO, f"lean-business:{name}")
    assert process.detection_faults(definition) == []


@pytest.mark.parametrize("name", sorted(DEFINITIONS))
def test_each_predicate_it_names_is_registered_with_a_script_that_exists(name: str) -> None:
    registered = {
        command.name: command.script for command in registered_commands(CAPABILITY).values()
    }
    named = _predicates(DEFINITIONS[name])
    assert named
    assert [run for run in named if run not in registered] == []
    assert [run for run in named if not registered[run].is_file()] == []
