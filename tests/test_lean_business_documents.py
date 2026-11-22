"""Each document a lean-business command prints for a program holds its contract (ADR-097
point 7; lean-business DEC-002 point 15).

Each test runs the command in the test's own process, in the world the command tests run
in (`tests/lean_business_world.py`), and holds what it prints to the contract pinned here
with `tests/document_contracts.py`. A key that goes, or comes back, fails until the same
change updates the pin, beside the changeset that declares the break.
`tests/test_capability_documents.py` holds the ratchet over every capability's commands.

Each set the capability's README lists is pinned with its values. Where the values come
from, the test reads them as the code gives them: a subject's `state` from the process
definition that declares it, a value a file holds from the schema that allows it, and a
reading from the code that works it out. So a value the code comes to give, or no longer
gives, fails until the pin follows it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests import lean_business_world as lb
from tests.document_contracts import Contract, Form, check

_SCHEMAS = lb.CAPABILITY / "schemas"

#: A subject's place in the status: its id, its state, and why the engine could not tell.
_STANDING = {"id": "str", "state": "str|null", "why": "str|null"}

#: What the briefing adds to a subject's place, for each kind of subject.
_VARIANT = {
    "stale": "list",
    "stale[]": "str",
    "assumptions": "list|null",
    "assumptions[]": "object",
    "assumptions[].id": "str|null",
    "assumptions[].rank": "int|null",
    "assumptions[].outcome": "str|null",
}
_CYCLE = {
    "window": "object|null",
    "window.start": "str|null",
    "window.end": "str|null",
    "window.days": "int|null",
    "window.counted": "int|null",
    "objective": "str|null",
    "key_results": "list|null",
    "key_results[]": "object",
    "key_results[].variant": "str|null",
    "key_results[].metric": "str|null",
    "key_results[].target": "int|float|null",
    "key_results[].reached": "int|float|null",
    "constraint": "object|null",
    "constraint.step": "str|null",
    "constraint.evidence": "str|null",
    "suspensions": "list|null",
    "suspensions[]": "object",
    "suspensions[].reason": "str|null",
    "suspensions[].first_day": "str|null",
    "suspensions[].resumed": "str|null",
    "suspensions[].recorded": "str|null",
    "review": "object|null",
    "review.decision": "str|null",
    "review.winning": "str|null",
    "review.when": "str|null",
}
_EXPERIMENT = {
    "kind": "str|null",
    "assumption": "str|null",
    "cycle": "str|null",
    "time_box": "object|null",
    "time_box.start": "str|null",
    "time_box.end": "str|null",
    "expected": "str|null",
    "outcome": "str|null",
}

#: The steps of the customer factory, which a key result counts and a constraint names.
_FACTORY_STEPS = frozenset({"acquisition", "activation", "retention", "revenue", "referral"})

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
                "ideas[].goal_why": "str|null",
                "ideas[].dropped": "bool|null",
                "ideas[].last_act": "object|null",
                "ideas[].last_act.day": "str",
                "ideas[].last_act.what": "list",
                "ideas[].last_act.what[]": "str",
                "ideas[].offer": "object|null",
                "ideas[].offer.cycle": "str",
                "ideas[].offer.last_work": "str|null",
                "ideas[].offer.first_day": "str",
                "ideas[].offer.window_end": "str|null",
                "ideas[].offer.window_end_if_back_today": "str|null",
                "ideas[].offer.command": "str",
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
                **{
                    f"ideas[].{held}[].{key}": kind
                    for held, keys in (
                        ("variants", _VARIANT),
                        ("cycles", _CYCLE),
                        ("experiments", _EXPERIMENT),
                    )
                    for key, kind in keys.items()
                },
            }
        )
    },
    sets={
        "ideas[].goal.per": frozenset({"month", "year"}),
        "ideas[].variants[].state": frozenset(
            {"sketched", "desirable", "viable", "feasible", "shortlisted", "shelved", "split"}
        ),
        "ideas[].variants[].stale[]": frozenset(
            {"desirability", "viability", "feasibility", "shortlisting"}
        ),
        "ideas[].variants[].assumptions[].outcome": frozenset(
            {"untested", "being-tested", "supported", "refuted", "inconclusive"}
        ),
        "ideas[].cycles[].state": frozenset(
            {"planned", "running", "suspended", "in-review", "decided"}
        ),
        "ideas[].cycles[].key_results[].metric": _FACTORY_STEPS,
        "ideas[].cycles[].constraint.step": _FACTORY_STEPS,
        "ideas[].cycles[].review.decision": frozenset({"persevere", "pivot", "pause"}),
        "ideas[].experiments[].state": frozenset(
            {"drafted", "declared", "running", "due", "decided"}
        ),
        "ideas[].experiments[].kind": frozenset({"generative", "evaluative"}),
        "ideas[].experiments[].outcome": frozenset({"pass", "fail", "neither"}),
    },
)

CONTRACTS: Mapping[str, tuple[Contract, ...]] = {"lean-business status": (LEAN_STATUS,)}


def _states(process: str) -> tuple[str, ...]:
    """The states the process definition `process` declares."""
    definition = YAML(typ="safe").load((_SCHEMAS / f"{process}.yaml").read_text())
    return tuple(state["id"] for state in definition["process"]["states"])


def _enum(schema: str, *path: str) -> tuple[str, ...]:
    """The values the schema `schema` allows at the place `path` leads to."""
    held: Any = json.loads((_SCHEMAS / f"{schema}.schema.json").read_text(encoding="utf-8"))
    for key in path:
        held = held[key]
    return tuple(held["enum"])


def _enumerations() -> dict[str, tuple[str, ...]]:
    """Every value the code can give each set the contract pins."""
    briefing = lb.LIB["briefing"]
    steps = _enum("shapes", "$defs", "factory-step")
    return {
        "ideas[].goal.per": lb.LIB["estimates"].PERIODS,
        "ideas[].variants[].state": _states("desk-stage"),
        "ideas[].variants[].stale[]": (*lb.LIB["fingerprint"].STEPS, briefing.SHORTLISTING),
        "ideas[].variants[].assumptions[].outcome": tuple(briefing.ASSUMPTION_WORDS),
        "ideas[].cycles[].state": _states("cycle-lifecycle"),
        "ideas[].cycles[].key_results[].metric": steps,
        "ideas[].cycles[].constraint.step": steps,
        "ideas[].cycles[].review.decision": _enum(
            "cycle", "properties", "review", "properties", "decision"
        ),
        "ideas[].experiments[].state": _states("experiment-lifecycle"),
        "ideas[].experiments[].kind": _enum("experiment", "properties", "kind"),
        "ideas[].experiments[].outcome": tuple(lb.positions.OUTCOME_WORDS),
    }


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
    # An idea with no goal and a variant to judge, beside one whose goal, canvas and cycle
    # cannot be read, so the engine cannot tell where either stands.
    assert world.run("new_variant", "board-game--platform", "--archetype", "marketplace").code == 0
    for rel in ("goal.yaml", "variants/plots/canvas.yaml", "cycles/spring.yaml"):
        unreadable = world.root / "lean-business/garden" / rel
        unreadable.parent.mkdir(parents=True)
        unreadable.write_text("id: [unclosed\n", encoding="utf-8")
    every = _printed(world)
    assert any(
        variant["state"] is None for idea in every["ideas"] for variant in idea["variants"]
    ), every
    assert any(cycle["key_results"] is None for idea in every["ideas"] for cycle in idea["cycles"])
    assert any(idea["goal_why"] is not None for idea in every["ideas"]), every
    reviewed = _printed(world, "meal-plan")
    # The idea's cycle running and quiet since it was planned, so the briefing offers to
    # record the silence, and a verdict of its variant gone stale.
    for experiment in (world.root / lb.IDEA / "experiments").iterdir():
        experiment.unlink()

    def quiet(data: Any) -> None:
        del data["review"]
        del data["suspensions"]

    def reworded(data: Any) -> None:
        data["boxes"]["problem"][0]["text"] = "Planning the week takes an evening"

    world.edit(lb.CYCLE, quiet)
    world.edit(lb.DIRECT, reworded)
    # Three weeks of its window gone with nothing recorded, the silence the offer waits for.
    world.engine.on = date(2026, 11, 21)
    running = _printed(world, "meal-plan")
    (idea,) = running["ideas"]
    assert idea["offer"] is not None and idea["variants"][0]["stale"], running
    check(LEAN_STATUS, {"answer": [every, reviewed, running]}, enumerations=_enumerations())
