"""Each document a lean-business command prints for a program holds its contract (ADR-097
point 7; lean-business DEC-002 point 15).

Each test runs the command in the test's own process, in the world the command tests run
in (`tests/lean_business_world.py`), and holds what it prints to the contract pinned here
with `tests/document_contracts.py`. A key that goes, or comes back, fails until the same
change updates the pin, beside the changeset that declares the break.
`tests/test_capability_documents.py` holds the ratchet over every capability's commands.

A subject's `state` is a state of the capability's process definitions, whose values
those definitions own, so this contract pins its type and lists no values.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from tests import lean_business_world as lb
from tests.document_contracts import Contract, Form, check

#: A subject's place in the status: its id, its state, and why the engine could not tell.
_STANDING = {"id": "str", "state": "str|null", "why": "str|null"}

LEAN_STATUS = Contract(
    name="pkit lean status --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "location": "str",
                "ideas": "list",
                "ideas[]": "object",
                "ideas[].id": "str",
                "ideas[].goal": "object|null",
                "ideas[].goal.revenue": "int|float|null",
                "ideas[].goal.per": "str|null",
                "ideas[].goal.currency": "str|null",
                "ideas[].goal.years": "int|float|null",
                "ideas[].waiting": "list",
                "ideas[].waiting[]": "object",
                "ideas[].waiting[].subject": "str",
                "ideas[].waiting[].what": "str",
                "ideas[].waiting[].command": "str",
                **{
                    f"ideas[].{held}{key}": kind
                    for held in ("variants", "cycles", "experiments")
                    for key, kind in {"": "list", "[]": "object"}.items()
                },
                **{
                    f"ideas[].{held}[].{key}": kind
                    for held in ("variants", "cycles", "experiments")
                    for key, kind in _STANDING.items()
                },
            }
        )
    },
)

CONTRACTS: Mapping[str, tuple[Contract, ...]] = {"lean-business status": (LEAN_STATUS,)}


def _printed(world: lb.World, *args: str) -> dict[str, Any]:
    run = world.run("status", "--json", *args)
    assert run.code == 0, run.err
    document = json.loads(run.out)
    assert isinstance(document, dict), run.out
    return document


def test_the_status_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = lb.world(tmp_path, monkeypatch, date(2026, 11, 20))
    # An idea with no goal and a variant to judge, beside one whose canvas cannot be read,
    # so the engine cannot tell where it stands.
    assert world.run("new_variant", "board-game--platform", "--archetype", "marketplace").code == 0
    unreadable = world.root / "lean-business/garden/variants/plots/canvas.yaml"
    unreadable.parent.mkdir(parents=True)
    unreadable.write_text("id: [unclosed\n", encoding="utf-8")
    every = _printed(world)
    assert any(
        variant["state"] is None for idea in every["ideas"] for variant in idea["variants"]
    ), every
    check(LEAN_STATUS, {"answer": [every, _printed(world, "meal-plan")]})
