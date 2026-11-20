"""lean-business's desk commands (lean-business DEC-001 points 3, 6 and 10; DEC-002 points 1
to 7, 13 and 15; DEC-003 points 2 and 5): the goal, a variant's canvas and its content, its
verdicts and its shortlisting, and what reads them, the grid, the estimate and the status.

Each runs in this process on a copy of the fixture idea, on a day the test names, against
an engine that asks the same predicates as the engine itself (`tests/lean_business_world.py`).
The fixture's `direct` variant has a yes on all three steps, none stale, and is
shortlisted; `two-sided` is shelved; the cycle was reviewed after its window."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from tests import lean_business_world as lb

DAY = date(2026, 11, 20)

#: A day after the cycle's window, as its suspension moved it, ended.
AFTER_THE_CYCLE = date(2027, 3, 1)

ASSUMPTIONS = f"{lb.IDEA}/variants/direct/assumptions.yaml"


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> lb.World:
    return lb.world(tmp_path, monkeypatch, DAY)


def later(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> lb.World:
    return lb.world(tmp_path, monkeypatch, AFTER_THE_CYCLE)


def entries(world: lb.World, box: str, rel: str = lb.DIRECT) -> list[Any]:
    return world.read(rel)["boxes"][box]


def no_outcome(world: lb.World) -> None:
    world.edit(lb.DIRECT, lambda data: data.pop("outcome"))


def desirable(world: lb.World) -> None:
    """The fixture's `direct` variant with its yes on desirability alone."""

    def change(data: Any) -> None:
        del data["outcome"]
        del data["verdicts"]["viability"]
        del data["verdicts"]["feasibility"]

    world.edit(lb.DIRECT, change)


# --- set-goal ---------------------------------------------------------------------------------


def test_set_goal_sets_a_first_goal_from_every_flag_and_creates_the_idea(
    world: lb.World,
) -> None:
    flags = ("--revenue", "20000", "--per", "month", "--currency", "CZK", "--years", "2")
    run = world.run("set_goal", "board-game", *flags[:4])
    assert run.code == 1
    assert "its first needs --currency, --years" in run.err
    run = world.run("set_goal", "board-game", *flags, terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [
        "Set the idea's goal to 20000 CZK a month, within 2 years? Viability and feasibility "
        "are judged against it."
    ]
    assert lb.read(world.root, "lean-business/board-game/goal.yaml") == {
        "pkit_schema": "lean-business:goal",
        "schema_version": 1,
        "revenue": {"amount": 20000, "per": "month"},
        "currency": "CZK",
        "years": 2,
        "by": lb.PERSON,
        "when": DAY,
    }


def test_set_goal_refuses_while_a_cycle_is_planned_running_or_suspended(world: lb.World) -> None:
    run = world.run("set_goal", "meal-plan", "--years", "4", "--person-decided")
    assert run.code == 1
    assert "while the cycle `meal-plan--first` was planned, running or suspended" in run.err


def test_set_goal_changes_what_it_is_given_and_stales_the_judgements_on_the_goal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = later(tmp_path, monkeypatch)
    run = world.run("set_goal", "meal-plan", "--years", "4", "--person-decided")
    assert run.code == 0, run.err
    goal = world.read(lb.GOAL)
    assert (goal["years"], goal["currency"], goal["when"]) == (4, "EUR", AFTER_THE_CYCLE)
    assert "the verdict on viability of `meal-plan--direct` is stale after this change" in run.out
    assert "the verdict on feasibility of `meal-plan--direct` is stale after this change" in run.out
    assert "the verdict on desirability" not in run.out
    assert "warning: the shortlisting of `meal-plan--direct` is stale after this change" in run.out


def test_set_goal_keeps_the_currency_while_a_declared_experiment_is_undecided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = later(tmp_path, monkeypatch)
    world.edit(f"{lb.IDEA}/experiments/landing-page.yaml", lambda data: data.pop("decision"))
    run = world.run("set_goal", "meal-plan", "--currency", "USD", "--person-decided")
    assert run.code == 1
    assert "while `meal-plan--landing-page`, declared in the first, is undecided" in run.err


# --- new-variant, add-side --------------------------------------------------------------------


def test_new_variant_creates_its_canvas_and_an_empty_list_of_assumptions(world: lb.World) -> None:
    run = world.run("new_variant", "meal-plan--boxes", "--archetype", "direct")
    assert run.code == 0, run.err
    assert run.asked == []
    assert world.read(f"{lb.IDEA}/variants/boxes/canvas.yaml") == {
        "pkit_schema": "lean-business:canvas",
        "schema_version": 1,
        "id": "meal-plan--boxes",
        "archetype": "direct",
        "authors": [lb.PERSON],
    }
    assert world.read(f"{lb.IDEA}/variants/boxes/assumptions.yaml") == {
        "pkit_schema": "lean-business:assumptions",
        "schema_version": 1,
        "assumptions": [],
    }


def test_new_variant_refuses_a_variant_that_exists(world: lb.World) -> None:
    run = world.run("new_variant", "meal-plan--direct", "--archetype", "direct")
    assert run.code == 1
    assert "the variant `meal-plan--direct` exists already" in run.err


def test_new_variant_takes_up_a_shelved_story_and_no_other(world: lb.World) -> None:
    run = world.run(
        "new_variant",
        "meal-plan--grocers",
        "--archetype",
        "marketplace",
        "--author",
        "B. Partner",
        "--comes-from",
        "two-sided",
    )
    assert run.code == 0, run.err
    canvas = world.read(f"{lb.IDEA}/variants/grocers/canvas.yaml")
    assert (canvas["authors"], canvas["comes-from"]) == (
        ["B. Partner"],
        "[canvas:meal-plan--two-sided]",
    )
    run = world.run(
        "new_variant", "meal-plan--again", "--archetype", "direct", "--comes-from", "direct"
    )
    assert run.code == 1
    assert "[comes-from]" in run.err and "neither split nor shelved" in run.err


def test_add_side_names_a_side_once(world: lb.World) -> None:
    run = world.run("add_side", "meal-plan--two-sided", "couriers")
    assert run.code == 0, run.err
    assert world.read(lb.TWO_SIDED)["sides"] == ["cooks", "shops", "couriers"]
    run = world.run("add_side", "meal-plan--two-sided", "couriers")
    assert run.code == 1
    assert "names the side `couriers` already" in run.err


# --- add-entry, edit-entry, remove-entry ------------------------------------------------------


def test_add_entry_gives_an_id_from_its_text_and_qualifies_its_links(world: lb.World) -> None:
    run = world.run(
        "add_entry",
        "meal-plan--direct",
        "solution",
        "A shopping list sorted by aisle",
        "--problem",
        "food-wasted",
    )
    assert run.code == 0, run.err
    assert "Added `meal-plan--direct--a-shopping-list-sorted-by` to solution." in run.out
    assert entries(world, "solution")[-1] == {
        "id": "meal-plan--direct--a-shopping-list-sorted-by",
        "text": "A shopping list sorted by aisle",
        "problem": "meal-plan--direct--food-wasted",
    }


@pytest.mark.parametrize(
    ("box", "flags", "refused"),
    [
        ("problem", ("--problem", "food-wasted"), "--problem is given on an entry of"),
        ("solution", ("--kind", "early"), "--kind is given on an entry of `channels` alone"),
        ("problem", ("--side", "cooks"), "names no side `cooks`"),
    ],
)
def test_add_entry_refuses_a_link_its_box_does_not_take(
    world: lb.World, box: str, flags: tuple[str, ...], refused: str
) -> None:
    run = world.run("add_entry", "meal-plan--direct", box, "Something", *flags)
    assert run.code == 1
    assert refused in run.err


def test_add_entry_adds_an_entry_for_its_side(world: lb.World) -> None:
    run = world.run(
        "add_entry",
        "meal-plan--two-sided",
        "early-adopters",
        "Grocers who lost a shop nearby",
        "--side",
        "shops",
        "--trigger",
        "A rival opens across the road",
    )
    assert run.code == 0, run.err
    assert entries(world, "early-adopters", lb.TWO_SIDED) == [
        {
            "id": "meal-plan--two-sided--grocers-who-lost-a-shop",
            "text": "Grocers who lost a shop nearby",
            "side": "shops",
            "triggers": ["A rival opens across the road"],
        }
    ]


def test_edit_entry_changes_clears_and_drops_its_links(world: lb.World) -> None:
    problem = "meal-plan--direct--food-wasted"
    run = world.run("edit_entry", problem, "--drop-alternative", "paper-lists")
    assert run.code == 0, run.err
    assert "alternatives" not in entries(world, "problem")[1]
    run = world.run("edit_entry", problem, "--alternative", "meal-plan--direct--paper-lists")
    assert run.code == 0, run.err
    assert entries(world, "problem")[1]["alternatives"] == ["meal-plan--direct--paper-lists"]
    run = world.run("edit_entry", problem, "--clear", "alternatives")
    assert run.code == 0, run.err
    assert entries(world, "problem")[1] == {
        "id": problem,
        "text": "Food bought for the week goes to waste",
    }
    run = world.run("edit_entry", problem, "--clear", "step")
    assert run.code == 1
    assert "--clear step is given on an entry of `key-metrics` alone" in run.err
    run = world.run("edit_entry", problem)
    assert run.code == 1
    assert "give what the entry changes" in run.err


def test_edit_entry_of_judged_content_names_each_judgement_it_stales(world: lb.World) -> None:
    run = world.run("edit_entry", "meal-plan--direct--households", "--text", "Households of two")
    assert run.code == 0, run.err
    assert "warning: the verdict on desirability of `meal-plan--direct` is stale" in run.out
    assert "pkit lean judge meal-plan--direct desirability" in run.out
    assert "warning: the shortlisting of `meal-plan--direct` is stale" in run.out
    assert "the verdict on viability" not in run.out


def test_a_stale_shortlisting_an_undecided_cycle_explores_is_said_louder(world: lb.World) -> None:
    world.edit(lb.CYCLE, lambda data: data.pop("review"))
    run = world.run("edit_entry", "meal-plan--direct--households", "--text", "Households of two")
    assert run.code == 0, run.err
    assert (
        "WARNING: the shortlisting of `meal-plan--direct` is stale after this change, and "
        "`meal-plan--first`, not yet reviewed, explores it" in run.out
    )


def test_remove_entry_warns_of_what_still_names_it_and_removes_it(world: lb.World) -> None:
    entry = "meal-plan--direct--planning-takes-long"
    run = world.run("remove_entry", entry)
    assert run.code == 0, run.err
    assert entry not in [e["id"] for e in entries(world, "problem")]
    assert (
        "warning: the entry `meal-plan--direct--plan-in-a-minute`, the entry "
        "`meal-plan--direct--weekly-plan`, the assumption `meal-plan--direct--planning-takes-long` "
        f"still name `{entry}`, and are kept as they are" in run.out
    )
    run = world.run("remove_entry", entry)
    assert run.code == 1
    assert f"holds no entry `{entry}`" in run.err


# --- set-inputs, set-traction -----------------------------------------------------------------


def test_set_inputs_merges_into_the_set_for_its_side(world: lb.World) -> None:
    run = world.run(
        "set_inputs", "meal-plan--direct", "--referral-share", "0.2", "--clear", "conversion"
    )
    assert run.code == 0, run.err
    assert world.read(lb.DIRECT)["viability"] == [
        {
            "price": {"amount": 8, "per": "month"},
            "lifetime": {"length": 2, "unit": "year"},
            "referral-share": 0.2,
        }
    ]
    run = world.run(
        "set_inputs", "meal-plan--two-sided", "--side", "shops", "--price", "150", "month"
    )
    assert run.code == 0, run.err
    assert world.read(lb.TWO_SIDED)["viability"][1]["price"] == {"amount": 150, "per": "month"}


@pytest.mark.parametrize(
    ("flags", "refused"),
    [
        (("--conversion", "0"), "a share above 0 and at most 1"),
        (("--referral-share", "1"), "at least 0 and below 1"),
        (("--price", "8", "week"), "counts in a month or a year"),
        (("--lifetime", "0", "year"), "longer than nothing"),
        ((), "give an input to set"),
    ],
)
def test_set_inputs_refuses_an_input_out_of_its_range(
    world: lb.World, flags: tuple[str, ...], refused: str
) -> None:
    run = world.run("set_inputs", "meal-plan--direct", *flags)
    assert run.code == 1
    assert refused in run.err


def test_set_traction_sets_and_clears_the_traction_target(world: lb.World) -> None:
    flags = ("--first-stage-metric", "activation", "--first-stage-target", "100")
    run = world.run("set_traction", "meal-plan--direct", *flags)
    assert run.code == 0, run.err
    assert world.read(lb.DIRECT)["traction"] == {
        "multiplier": 10,
        "first-stage": {"metric": "activation", "target": 100},
    }
    assert "the verdict on feasibility of `meal-plan--direct` is stale" in run.out
    run = world.run("set_traction", "meal-plan--direct", "--first-stage-metric", "activation")
    assert run.code == 1
    assert "given together" in run.err
    run = world.run("set_traction", "meal-plan--direct", "--clear")
    assert run.code == 0, run.err
    assert "traction" not in world.read(lb.DIRECT)


# --- judge ------------------------------------------------------------------------------------


def test_judge_a_yes_on_a_passed_step_judges_it_again_and_moves_nothing(
    world: lb.World,
) -> None:
    world.run("edit_entry", "meal-plan--direct--households", "--text", "Households of two")
    run = world.run("judge", "meal-plan--direct", "desirability", "yes", "--note", "Still so")
    assert run.code == lb.acting.ASKED
    assert run.out.startswith("Judge desirability of `meal-plan--direct` yes again")
    run = world.run("judge", "meal-plan--direct", "desirability", "yes", "--person-decided")
    assert run.code == 0, run.err
    assert world.engine.moves == []
    canvas, goal = world.read(lb.DIRECT), world.read(lb.GOAL)
    assert lb.LIB["fingerprint"].check_verdict("desirability", canvas, goal).fresh


def test_judge_a_no_on_a_passed_step_takes_the_variant_back_and_clears_after_it(
    world: lb.World,
) -> None:
    run = world.run("judge", "meal-plan--direct", "viability", "no", "--person-decided")
    assert run.code == 0, run.err
    assert world.engine.moves == [
        ("desk-stage", "meal-plan--direct", "shortlisted", "desirable", lb.PERSON)
    ]
    canvas = world.read(lb.DIRECT)
    assert sorted(canvas["verdicts"]) == ["desirability", "viability"]
    assert canvas["verdicts"]["viability"]["answer"] == "no"
    assert "outcome" not in canvas


@pytest.mark.parametrize(
    ("variant", "step", "refused"),
    [
        ("meal-plan--two-sided", "desirability", "is shelved, which is final"),
        ("meal-plan--boxes", "desirability", "there is no variant"),
    ],
)
def test_judge_refuses_a_final_variant_and_one_with_no_canvas(
    world: lb.World, variant: str, step: str, refused: str
) -> None:
    run = world.run("judge", variant, step, "no", "--person-decided")
    assert run.code == 1
    assert refused in run.err or "stands in none" in run.err


def test_judge_refuses_a_step_after_the_next(world: lb.World) -> None:
    desirable(world)
    run = world.run("judge", "meal-plan--direct", "feasibility", "yes", "--person-decided")
    assert run.code == 1
    assert "viability is judged next" in run.err


def test_judge_refuses_a_verdict_against_the_goal_while_the_idea_has_none(
    world: lb.World,
) -> None:
    (world.root / lb.GOAL).unlink()
    desirable(world)
    run = world.run("judge", "meal-plan--direct", "viability", "no", "--person-decided")
    assert run.code == 1
    assert "the idea has none" in run.err


# --- shortlist --------------------------------------------------------------------------------


# A shortlisting given again on the day an experiment was declared on the old one would
# leave that declaration resting on a shortlisting that never stood then, which the check
# refuses; so these shortlist after the cycle.


def test_shortlist_moves_a_feasible_variant_into_shortlisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = later(tmp_path, monkeypatch)
    no_outcome(world)
    run = world.run("shortlist", "meal-plan--direct", terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == ["Shortlist the variant, to test it in a cycle?"]
    assert world.engine.moves == [
        ("desk-stage", "meal-plan--direct", "feasible", "shortlisted", lb.PERSON)
    ]
    outcome = world.read(lb.DIRECT)["outcome"]
    assert (outcome["kind"], outcome["by"], outcome["when"]) == (
        "shortlisted",
        lb.PERSON,
        AFTER_THE_CYCLE,
    )


def test_shortlist_again_takes_the_shortlisting_anew(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = later(tmp_path, monkeypatch)
    run = world.run("shortlist", "meal-plan--direct", "--person-decided")
    assert run.code == 0, run.err
    assert world.engine.moves == [
        ("desk-stage", "meal-plan--direct", "shortlisted", "shortlisted", lb.PERSON)
    ]
    assert world.read(lb.DIRECT)["outcome"]["when"] == AFTER_THE_CYCLE


def test_shortlist_refuses_where_a_declaration_rests_on_the_shortlisting_it_replaces(
    world: lb.World,
) -> None:
    run = world.run("shortlist", "meal-plan--direct", "--person-decided")
    assert run.code == 1
    assert "[declaration-refused]" in run.err


def test_shortlist_refuses_on_a_stale_verdict(world: lb.World) -> None:
    world.run("edit_entry", "meal-plan--direct--households", "--text", "Households of two")
    run = world.run("shortlist", "meal-plan--direct", "--person-decided")
    assert run.code == 1
    assert "stale" in run.err


def test_shortlist_refuses_a_variant_that_is_not_feasible(world: lb.World) -> None:
    run = world.run("shortlist", "meal-plan--two-sided", "--person-decided")
    assert run.code == 1
    assert "no move on `shortlist` leaves there" in run.err


# --- canvas, estimate, status -----------------------------------------------------------------


def test_canvas_draws_the_grid_with_its_credit_line(world: lb.World) -> None:
    run = world.run("canvas", "meal-plan--direct")
    assert run.code == 0, run.err
    lines = run.out.splitlines()
    assert lines[0] == "`meal-plan--direct`, a direct model"
    assert [cell.strip() for cell in lines[2].split("|")[1:6]] == [
        "PROBLEM",
        "SOLUTION",
        "UNIQUE VALUE",
        "UNFAIR ADVANTAGE",
        "CUSTOMER",
    ]
    lower = next(index for index, line in enumerate(lines) if "EXISTING" in line)
    assert [cell.strip() for cell in lines[lower].split("|")[1:6]] == [
        "EXISTING",
        "KEY METRICS",
        "HIGH-LEVEL",
        "CHANNELS",
        "EARLY ADOPTERS",
    ]
    assert "| COST STRUCTURE" in run.out and "| REVENUE STREAMS" in run.out
    assert {len(line) for line in lines[1:] if line.startswith(("|", "+"))} == {96}
    assert "[paper-lists]" not in run.out
    assert lines[-3].startswith("Arranged as the Lean Canvas, Ash Maurya's adaptation")
    assert "Creative Commons Attribution-ShareAlike 3.0" in run.out


def test_canvas_shows_each_entrys_own_id_where_asked(world: lb.World) -> None:
    run = world.run("canvas", "meal-plan--direct", "--ids")
    assert run.code == 0, run.err
    assert run.out.splitlines()[1].startswith("Each entry's id is `meal-plan--direct--`")
    assert "|   [paper-lists]" in run.out


def _inputs(world: lb.World, change: Any) -> None:
    """Make `change` to the `direct` variant's one set of inputs."""
    world.edit(lb.DIRECT, lambda data: change(data["viability"][0]))


def test_estimate_works_the_numbers_out_from_the_goal_and_the_inputs(world: lb.World) -> None:
    _inputs(world, lambda inputs: inputs.insert(3, "referral-share", 0.25))
    run = world.run("estimate", "meal-plan--direct")
    assert run.code == 0, run.err
    assert run.out.splitlines()[1:] == [
        "The goal: 1,000,000 EUR a year, within 3 years; traction grows 10 times a year.",
        "",
        "The model:",
        "  a year's revenue from one customer: 96 EUR",
        "  active customers needed: 10,417",
        "  customers lost each year, and as many won to replace them: 5,209",
        "  of those, won by referral: 1,303; through the channels: 3,907",
        "  leads needed each year: 78,128",
        "  active customers on the way: year 1: 105, year 2: 1,042, year 3: 10,417",
    ]


_ON_THE_WAY = "  active customers on the way: year 1: 105, year 2: 1,042, year 3: 10,417"


@pytest.mark.parametrize(
    ("removed", "shown"),
    [
        (
            (),
            [
                "  a year's revenue from one customer: 96 EUR",
                "  active customers needed: 10,417",
                "  customers lost each year, and as many won to replace them: 5,209",
                _ON_THE_WAY,
                "  not worked out, for want of: referral-share",
            ],
        ),
        (
            ("lifetime", "conversion"),
            [
                "  a year's revenue from one customer: 96 EUR",
                "  active customers needed: 10,417",
                _ON_THE_WAY,
                "  not worked out, for want of: lifetime, conversion, referral-share",
            ],
        ),
        (("price",), ["  nothing is worked out, for want of: price, referral-share"]),
    ],
    ids=["the-referral-share", "the-lifetime-and-the-conversion", "the-price"],
)
def test_estimate_names_each_input_missing_and_works_out_what_rests_on_none(
    world: lb.World, removed: tuple[str, ...], shown: list[str]
) -> None:
    # The fixture's inputs give no referral share.
    _inputs(world, lambda inputs: [inputs.pop(name) for name in removed])
    run = world.run("estimate", "meal-plan--direct")
    assert run.code == 0, run.err
    assert run.out.split("The model:\n")[1].splitlines() == shown


def test_estimate_counts_only_the_sides_that_pay(world: lb.World) -> None:
    run = world.run("estimate", "meal-plan--two-sided")
    assert run.code == 0, run.err
    assert "The side `cooks`:\n  pays nothing, so it counts at nothing toward the goal" in run.out
    shops = run.out.split("The side `shops`:\n")[1].splitlines()
    assert shops[:2] == [
        "  a year's revenue from one customer: 2,400 EUR",
        "  active customers needed: 417",
    ]


def test_estimate_refuses_without_a_goal(world: lb.World) -> None:
    (world.root / lb.GOAL).unlink()
    run = world.run("estimate", "meal-plan--direct")
    assert run.code == 1
    assert "the idea has none" in run.err


def test_status_gives_a_line_for_each_idea_and_an_idea_in_full(world: lb.World) -> None:
    world.run("new_variant", "board-game--platform", "--archetype", "marketplace")
    run = world.run("status")
    assert run.code == 0, run.err
    assert run.out.splitlines() == [
        "board-game: no goal, 1 variant (1 sketched); 2 waiting",
        "meal-plan: a goal, 2 variants (1 shortlisted, 1 shelved)",
    ]
    run = world.run("status", "board-game")
    assert "    board-game--platform: sketched" in run.out
    assert "      pkit lean judge board-game--platform desirability yes|no" in run.out


def test_status_json_is_its_documented_structured_form(world: lb.World) -> None:
    run = world.run("status", "meal-plan", "--json")
    assert run.code == 0, run.err
    document = json.loads(run.out)
    assert document["schema_version"] == 1
    assert set(document) == {"schema_version", "location", "ideas"}
    (idea,) = document["ideas"]
    assert set(idea) == {"id", "goal", "variants", "cycles", "experiments", "waiting"}
    assert idea["goal"] == {"revenue": 1000000, "per": "year", "currency": "EUR", "years": 3}
    assert idea["variants"] == [
        {"id": "meal-plan--direct", "state": "shortlisted", "why": None},
        {"id": "meal-plan--two-sided", "state": "shelved", "why": None},
    ]
    assert idea["cycles"] == [{"id": "meal-plan--first", "state": "decided", "why": None}]
    assert idea["waiting"] == []
