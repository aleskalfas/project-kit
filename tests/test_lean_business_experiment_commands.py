"""lean-business's experiment path (lean-business DEC-002 points 7 to 11; DEC-003 points 3 to
5 and 7): a variant's assumptions and their ranks, a cycle's plan, and an experiment from its
draft through its declaration, its stopping rule and its result to its decision.

Each runs in this process on a copy of the fixture idea, on a day the test names, against
an engine that asks the same predicates as the engine itself (`tests/lean_business_world.py`).
The fixture's `direct` variant is shortlisted and `two-sided` shelved; its cycle, `first`,
was reviewed on 2027-02-15, so the next is planned after it; and its two experiments, both
on `direct`'s assumptions, are decided."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests import lean_business_world as lb

#: A day after the fixture's cycle was decided, when the next may be planned.
DAY = date(2027, 3, 1)

#: A day the fixture's cycle was undecided.
BEFORE_ITS_REVIEW = date(2026, 11, 20)

IDEA = "meal-plan"
DIRECT = "meal-plan--direct"
ASSUMPTIONS = f"{lb.IDEA}/variants/direct/assumptions.yaml"
#: The direct variant's assumptions in the fixture, the riskiest first: that planning the
#: week takes long, which the fixture's interviews tested and the drafts here test, and that
#: a household pays monthly, which its landing page, declared, tests.
PLANNING_TAKES_LONG = "meal-plan--direct--planning-takes-long"
TESTED = "meal-plan--direct--pays-monthly"

SECOND = "meal-plan--second"
SECOND_FILE = f"{lb.IDEA}/cycles/second.yaml"
PLAN = (
    "--variant",
    "direct",
    "--start",
    "2027-03-10",
    "--days",
    "60",
    "--objective",
    "Show that households keep paying for a planned week",
    "--key-result",
    "direct:revenue:30",
    "--constraint-step",
    "revenue",
    "--constraint-evidence",
    "Few of those who came back paid",
)

DRAFT = "meal-plan--weekly-calls"
DRAFT_FILE = f"{lb.IDEA}/experiments/weekly-calls.yaml"
GENERATIVE = (
    "--learn",
    "Whether a weekly call keeps households planning",
    "--stopping-rule",
    "Twelve calls, or three in a row that bring nothing new",
    "--fit",
    "8/calls that tell the same story",
)

LANDING_PAGE = "meal-plan--landing-page"

#: What a command says of a number that is not finite, such as `nan` or `1e400`.
NOT_FINITE = "is no finite number, and a file holds only finite numbers"


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> lb.World:
    return lb.world(tmp_path, monkeypatch, DAY)


def listed(world: lb.World) -> list[dict[str, Any]]:
    return world.read(ASSUMPTIONS)["assumptions"]


def ranks(world: lb.World) -> dict[str, int]:
    return {a["id"]: a["rank"] for a in listed(world)}


def planned(world: lb.World) -> None:
    """The second cycle planned, its window from 2027-03-10."""
    run = world.run("plan_cycle", SECOND, *PLAN, "--person-decided")
    assert run.code == 0, run.err


def drafted(world: lb.World, *, start: str = "2027-03-12", end: str = "2027-03-25") -> None:
    """A generative draft in the second cycle, on the untested assumption, its time box from
    `start` through `end`, with the person's estimate."""
    planned(world)
    run = world.run(
        "new_experiment",
        DRAFT,
        "--kind",
        "generative",
        "--assumption",
        "direct--planning-takes-long",
        "--cycle",
        "second",
    )
    assert run.code == 0, run.err
    run = world.run("draft_experiment", DRAFT, *GENERATIVE, "--start", start, "--end", end)
    assert run.code == 0, run.err
    run = world.run("record_estimate", DRAFT, "6", "--person-decided")
    assert run.code == 0, run.err


def declared(world: lb.World) -> None:
    drafted(world)
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 0, run.err


def on(world: lb.World, day: date) -> None:
    world.engine.on = day


def due_with_a_result(world: lb.World) -> None:
    """The draft declared, its stopping rule reached on 2027-03-15, and its result recorded
    on 2027-03-16, the day it then stands on, waiting for its decision."""
    declared(world)
    on(world, date(2027, 3, 15))
    assert world.run("reach_stopping_rule", DRAFT, "--person-decided").code == 0
    on(world, date(2027, 3, 16))
    argv = ("--measured", "9", "--evidence", "Notes", "--learned", "Some", "--person-decided")
    assert world.run("record_result", DRAFT, *argv).code == 0


#: The variants a split of `direct` makes, each shortlisted (`two_shortlisted`).
WEEKLY, DAILY = "meal-plan--weekly", "meal-plan--daily"


def two_shortlisted(world: lb.World) -> None:
    """Two shortlisted variants: `direct` taken back to the desk and split in two, each copy
    judged and shortlisted afresh, with the assumptions of `direct` copied to each."""
    steps = [
        ("judge", DIRECT, "viability", "no"),
        ("split", DIRECT, "--into", "weekly", "--into", "daily"),
    ]
    for variant in (WEEKLY, DAILY):
        steps += [("judge", variant, step, "yes") for step in ("desirability", "viability")]
        steps += [("judge", variant, "feasibility", "yes"), ("shortlist", variant)]
    for argv in steps:
        run = world.run(*argv, "--person-decided")
        assert run.code == 0, (argv, run.err)


def planned_over(world: lb.World, *variants: str) -> None:
    """The second cycle planned to explore `variants`, each with a key result."""
    plan = [*PLAN[2:8]]
    for variant in variants:
        own = variant.removeprefix(f"{IDEA}--")
        plan += ["--variant", own, "--key-result", f"{own}:revenue:30"]
    run = world.run("plan_cycle", SECOND, *plan, *PLAN[10:], "--person-decided")
    assert run.code == 0, run.err


def suspended(world: lb.World) -> None:
    """The second cycle running from 2027-03-10, suspended from 2027-03-14 on."""

    def change(data: Any) -> None:
        data["suspensions"] = [
            {
                "reason": "A move of house",
                "first-day": date(2027, 3, 14),
                "by": lb.PERSON,
                "when": date(2027, 3, 14),
            }
        ]

    world.edit(SECOND_FILE, change)
    on(world, date(2027, 3, 15))


# --- add-assumption ---------------------------------------------------------------------------


def test_add_assumption_from_an_entry_ranks_it_last_and_prints_its_id(world: lb.World) -> None:
    run = world.run(
        "add_assumption",
        DIRECT,
        "Households plan on Sunday evenings",
        "--kind",
        "desirability",
        "--entry",
        "planning-takes-long",
    )
    assert run.code == 0, run.err
    added = "meal-plan--direct--households-plan-on-sunday-evenings"
    assert f"Added `{added}`" in run.out
    assert "ranked 3" in run.out
    assert run.asked == []
    assert listed(world)[-1] == {
        "id": added,
        "statement": "Households plan on Sunday evenings",
        "source": {"entry": "meal-plan--direct--planning-takes-long"},
        "kind": "desirability",
        "rank": 3,
    }


def test_add_assumption_from_an_input_with_a_typed_id(world: lb.World) -> None:
    run = world.run(
        "add_assumption",
        DIRECT,
        "A household stays a year",
        "--kind",
        "viability",
        "--input",
        "lifetime",
        "--id",
        "stays-a-year",
    )
    assert run.code == 0, run.err
    assert listed(world)[-1]["id"] == "meal-plan--direct--stays-a-year"
    assert listed(world)[-1]["source"] == {"input": "lifetime"}


def test_add_assumption_creates_the_list_a_variant_lacks(world: lb.World) -> None:
    run = world.run(
        "add_assumption",
        "meal-plan--two-sided",
        "Cooks sell their plans",
        "--kind",
        "viability",
        "--input",
        "price",
    )
    assert run.code == 0, run.err
    made = world.read(f"{lb.IDEA}/variants/two-sided/assumptions.yaml")
    assert made["pkit_schema"] == "lean-business:assumptions"
    assert [a["rank"] for a in made["assumptions"]] == [1]


@pytest.mark.parametrize(
    ("argv", "refused"),
    [
        (
            ("--entry", "no-such-entry"),
            "--entry `no-such-entry` names no entry of the canvas of `meal-plan--direct`",
        ),
        (("--entry", "planning-takes-long", "--side", "cooks"), "--side is given with --input"),
        (("--input", "price", "--side", "cooks"), "names no side `cooks`"),
        (("--input", "price", "--id", "pays-monthly"), "the id `meal-plan--direct--pays-monthly`"),
    ],
)
def test_add_assumption_refuses_what_can_only_be_a_slip(
    world: lb.World, argv: tuple[str, ...], refused: str
) -> None:
    kept = lb.snapshot(world.root)
    run = world.run("add_assumption", DIRECT, "Something", "--kind", "viability", *argv)
    assert run.code == 1
    assert refused in run.err
    assert lb.snapshot(world.root) == kept


# --- edit-assumption and remove-assumption ----------------------------------------------------


def test_edit_assumption_changes_its_words_and_warns_where_a_declared_experiment_tests_it(
    world: lb.World,
) -> None:
    run = world.run("edit_assumption", TESTED, "--statement", "A household pays ten a month")
    assert run.code == 0, run.err
    assert listed(world)[1]["statement"] == "A household pays ten a month"
    assert listed(world)[1]["id"] == TESTED
    assert f"warning: `{LANDING_PAGE}`, declared, tests `{TESTED}`" in run.out


def test_edit_assumption_replaces_its_source(world: lb.World) -> None:
    run = world.run("edit_assumption", TESTED, "--kind", "feasibility", "--input", "conversion")
    assert run.code == 0, run.err
    assert listed(world)[1]["source"] == {"input": "conversion"}
    assert listed(world)[1]["kind"] == "feasibility"
    assert "warning" in run.out


def test_edit_assumption_refuses_a_side_on_one_from_an_entry(world: lb.World) -> None:
    run = world.run("edit_assumption", PLANNING_TAKES_LONG, "--side", "cooks")
    assert run.code == 1
    assert "comes from no input, so it names no side" in run.err


def test_edit_assumption_refuses_where_nothing_is_given(world: lb.World) -> None:
    run = world.run("edit_assumption", TESTED)
    assert run.code == 1
    assert "give what the assumption changes" in run.err


def test_remove_assumption_refuses_while_an_experiment_tests_it(world: lb.World) -> None:
    kept = lb.snapshot(world.root)
    run = world.run("remove_assumption", TESTED)
    assert run.code == 1
    assert f"`{LANDING_PAGE}`, declared tests `{TESTED}`" in run.err
    assert lb.snapshot(world.root) == kept


def test_remove_assumption_takes_out_an_untested_one_and_keeps_the_ranks(world: lb.World) -> None:
    world.run(
        "add_assumption",
        DIRECT,
        "Households cook alone",
        "--kind",
        "desirability",
        "--input",
        "price",
    )
    run = world.run("remove_assumption", "meal-plan--direct--households-cook-alone")
    assert run.code == 0, run.err
    assert ranks(world) == {PLANNING_TAKES_LONG: 1, TESTED: 2}


# --- rank -------------------------------------------------------------------------------------


def test_rank_puts_the_named_first_and_the_rest_after_them_as_they_were(world: lb.World) -> None:
    world.run(
        "add_assumption",
        DIRECT,
        "Households cook alone",
        "--kind",
        "desirability",
        "--input",
        "price",
    )
    added = "meal-plan--direct--households-cook-alone"
    run = world.run("rank", DIRECT, "households-cook-alone", terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [
        f"Rank the assumptions of `{DIRECT}` by risk, the riskiest first: 1. `{added}`, 2. "
        f"`{PLANNING_TAKES_LONG}`, 3. `{TESTED}`? The riskiest is tested first."
    ]
    assert ranks(world) == {added: 1, PLANNING_TAKES_LONG: 2, TESTED: 3}
    assert [a["id"] for a in listed(world)] == [PLANNING_TAKES_LONG, TESTED, added]


def test_rank_asks_nothing_where_they_are_ranked_so_already(world: lb.World) -> None:
    run = world.run("rank", DIRECT, PLANNING_TAKES_LONG)
    assert run.code == 0, run.err
    assert "ranked so already" in run.out
    assert run.asked == []


def test_rank_off_a_terminal_prints_the_question_and_writes_nothing(world: lb.World) -> None:
    kept = lb.snapshot(world.root)
    run = world.run("rank", DIRECT, "pays-monthly")
    assert run.code == 3
    assert "Rank the assumptions of" in run.out + run.err
    assert lb.snapshot(world.root) == kept


@pytest.mark.parametrize(
    ("named", "refused"),
    [
        (("pays-monthly", "pays-monthly"), "is named twice"),
        (("no-such",), "hold no `meal-plan--direct--no-such`"),
    ],
)
def test_rank_refuses_an_assumption_named_twice_or_not_held(
    world: lb.World, named: tuple[str, ...], refused: str
) -> None:
    run = world.run("rank", DIRECT, *named, "--person-decided")
    assert run.code == 1
    assert refused in run.err


# --- plan-cycle and change-plan ---------------------------------------------------------------


def test_plan_cycle_records_the_plan_with_who_when_and_its_fingerprint(world: lb.World) -> None:
    run = world.run("plan_cycle", SECOND, *PLAN, terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [
        f"Plan the cycle `{SECOND}`: 60 days from 2027-03-10, exploring `{DIRECT}`, toward "
        f'"Show that households keep paying for a planned week"? Its plan may change until '
        f"its window starts, and is frozen from then."
    ]
    cycle = world.read(SECOND_FILE)
    fingerprint = cycle["planned"].pop("fingerprint")
    assert fingerprint["form"] == 1
    assert cycle == {
        "pkit_schema": "lean-business:cycle",
        "schema_version": 1,
        "id": SECOND,
        "variants": [f"[canvas:{DIRECT}]"],
        "window": {"start": date(2027, 3, 10), "days": 60},
        "objective": {
            "statement": "Show that households keep paying for a planned week",
            "key-results": [{"variant": f"[canvas:{DIRECT}]", "metric": "revenue", "target": 30}],
        },
        "constraint": {"step": "revenue", "evidence": "Few of those who came back paid"},
        "planned": {"first": {"by": lb.PERSON, "when": DAY}, "by": lb.PERSON, "when": DAY},
    }
    assert "&" not in (world.root / SECOND_FILE).read_text(encoding="utf-8")


def test_plan_cycle_gives_a_window_of_ninety_days_where_none_is_given(world: lb.World) -> None:
    plan = [*PLAN]
    del plan[4:6]
    run = world.run("plan_cycle", SECOND, *plan, "--person-decided")
    assert run.code == 0, run.err
    assert world.read(SECOND_FILE)["window"]["days"] == 90


@pytest.mark.parametrize(
    ("flags", "refused"),
    [
        (("--days", "0"), "--days is one at least"),
        (("--days", "3000000"), "--days is 3650 at most"),
        (("--key-result", "direct:revenue:nan"), f"`nan` {NOT_FINITE}"),
        (("--key-result", "direct:revenue:1e400"), f"`inf` {NOT_FINITE}"),
    ],
)
def test_plan_cycle_refuses_a_window_out_of_bounds_and_a_target_that_is_not_finite(
    world: lb.World, flags: tuple[str, ...], refused: str
) -> None:
    kept = lb.snapshot(world.root)
    run = world.run("plan_cycle", SECOND, *PLAN, *flags, "--person-decided")
    assert run.code == 1
    assert refused in run.err
    assert lb.snapshot(world.root) == kept


def test_plan_cycle_refuses_while_the_last_cycle_is_undecided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = lb.world(tmp_path, monkeypatch, BEFORE_ITS_REVIEW)
    world.edit(lb.CYCLE, lambda data: data.pop("review"))
    run = world.run("plan_cycle", SECOND, *PLAN, "--person-decided")
    assert run.code == 1
    assert "the next cycle is planned once the last is decided" in run.err
    assert not (world.root / SECOND_FILE).exists()


def test_plan_cycle_refuses_a_variant_not_shortlisted(world: lb.World) -> None:
    plan = [*PLAN, "--variant", "two-sided", "--key-result", "two-sided:revenue:10"]
    run = world.run("plan_cycle", SECOND, *plan, "--person-decided")
    assert run.code == 1
    assert "`meal-plan--two-sided` stands shelved, not shortlisted" in run.err


def test_plan_cycle_refuses_a_key_result_of_a_variant_it_does_not_explore(world: lb.World) -> None:
    plan = [*PLAN, "--key-result", "two-sided:revenue:10"]
    run = world.run("plan_cycle", SECOND, *plan, "--person-decided")
    assert run.code == 1
    assert "[cycle-variants]" in run.err
    assert (
        "the key result names `meal-plan--two-sided`, which the cycle does not explore" in run.err
    )
    assert not (world.root / SECOND_FILE).exists()


def test_plan_cycle_refuses_an_idea_with_no_goal(world: lb.World) -> None:
    (world.root / lb.GOAL).unlink()
    kept = lb.snapshot(world.root)
    run = world.run("plan_cycle", SECOND, *PLAN, "--person-decided")
    assert run.code == 1
    assert "it was planned in an idea with no goal" in run.err
    assert lb.snapshot(world.root) == kept


def test_plan_cycle_refuses_a_window_that_overlaps_another_cycles(world: lb.World) -> None:
    # The fixture's cycle, decided, its window drawn out by hand to run into the next one's.
    world.edit(lb.CYCLE, lambda data: data["window"].update(days=150))
    kept = lb.snapshot(world.root)
    run = world.run("plan_cycle", SECOND, *PLAN, "--person-decided")
    assert run.code == 1
    assert "[one-cycle]" in run.err
    assert "overlaps the window of `meal-plan--first`" in run.err
    assert lb.snapshot(world.root) == kept


def test_plan_cycle_refuses_a_variant_with_no_key_result(world: lb.World) -> None:
    two_shortlisted(world)
    kept = lb.snapshot(world.root)
    plan = [*PLAN[2:8], "--variant", "weekly", "--variant", "daily"]
    plan += ["--key-result", "weekly:revenue:30", *PLAN[10:]]
    run = world.run("plan_cycle", SECOND, *plan, "--person-decided")
    assert run.code == 1
    assert f"the cycle explores `{DAILY}`, and no key result names it" in run.err
    assert lb.snapshot(world.root) == kept


def test_plan_cycle_refuses_a_cycle_that_exists(world: lb.World) -> None:
    run = world.run("plan_cycle", "meal-plan--first", *PLAN, "--person-decided")
    assert run.code == 1
    assert "exists already" in run.err


def test_plan_cycle_warns_of_a_window_started_by_today(world: lb.World) -> None:
    plan = [*PLAN]
    plan[3] = DAY.isoformat()
    run = world.run("plan_cycle", SECOND, *plan, "--person-decided")
    assert run.code == 0, run.err
    assert "warning: its window started on 2027-03-01" in run.out


#: What the planning gate says of a window that, as planned, ended before the day the cycle
#: is first planned, the fixture's day.
ENDED = (
    "it was planned on 2027-03-01, and its window, as planned, ended on 2027-02-28, before "
    "that day: a window may start before the day its cycle is planned, but one that ended by "
    "then leaves the cycle no day to run"
)


def test_plan_cycle_refuses_a_window_that_ended_before_today(world: lb.World) -> None:
    plan = [*PLAN]
    plan[3], plan[5] = "2027-02-20", "9"
    kept = lb.snapshot(world.root)
    run = world.run("plan_cycle", SECOND, *plan, "--person-decided")
    assert run.code == 1
    assert ENDED in run.err
    assert lb.snapshot(world.root) == kept


def test_plan_cycle_takes_a_window_that_ends_today(world: lb.World) -> None:
    plan = [*PLAN]
    plan[3], plan[5] = "2027-02-20", "10"
    run = world.run("plan_cycle", SECOND, *plan, "--person-decided")
    assert run.code == 0, run.err
    assert "warning: its window started on 2027-02-20, by today, 2027-03-01" in run.out


def test_change_plan_replaces_what_it_gives_and_keeps_who_first_planned_it(
    world: lb.World,
) -> None:
    planned(world)
    first = world.read(SECOND_FILE)["planned"]
    on(world, DAY + timedelta(days=2))
    run = world.run(
        "change_plan",
        SECOND,
        "--days",
        "45",
        "--objective",
        "Keep them paying",
        who="B. Partner",
        terminal=True,
        answers=[True],
    )
    assert run.code == 0, run.err
    assert run.asked[0].startswith(f"Change the plan of `{SECOND}`, from 60 days from 2027-03-10")
    changed = world.read(SECOND_FILE)
    assert changed["window"] == {"start": date(2027, 3, 10), "days": 45}
    assert changed["objective"]["statement"] == "Keep them paying"
    assert changed["planned"]["first"] == {"by": lb.PERSON, "when": DAY}
    assert changed["planned"]["by"] == "B. Partner"
    assert changed["planned"]["when"] == DAY + timedelta(days=2)
    assert changed["planned"]["fingerprint"] != first["fingerprint"]


def test_change_plan_refuses_a_cycle_that_is_not_planned(world: lb.World) -> None:
    run = world.run("change_plan", "meal-plan--first", "--days", "30", "--person-decided")
    assert run.code == 1
    assert "stands decided, not planned" in run.err


def test_change_plan_refuses_a_start_moved_to_a_day_its_plan_is_frozen(world: lb.World) -> None:
    planned(world)
    on(world, DAY + timedelta(days=2))
    run = world.run("change_plan", SECOND, "--start", "2027-03-02", "--person-decided")
    assert run.code == 1
    assert "a plan changes only before its window's first day" in run.err


def test_change_plan_on_the_day_of_the_first_planning_may_move_the_start_to_that_day(
    world: lb.World,
) -> None:
    planned(world)
    argv = ("--start", DAY.isoformat(), "--person-decided")
    run = world.run("change_plan", SECOND, *argv, who="B. Partner")
    assert run.code == 0, run.err
    changed = world.read(SECOND_FILE)
    assert changed["window"] == {"start": DAY, "days": 60}
    assert changed["planned"]["first"] == {"by": lb.PERSON, "when": DAY}
    assert (changed["planned"]["by"], changed["planned"]["when"]) == ("B. Partner", DAY)
    assert (
        f"warning: its window started on {DAY}, by today, {DAY}, so its plan is frozen from now"
        in run.out
    )


def test_change_plan_on_the_day_of_the_first_planning_refuses_a_window_ended_before_it(
    world: lb.World,
) -> None:
    planned(world)
    kept = lb.snapshot(world.root)
    argv = ("--start", "2027-02-20", "--days", "9", "--person-decided")
    run = world.run("change_plan", SECOND, *argv)
    assert run.code == 1
    assert "[plan-refused]" in run.err
    assert ENDED in run.err
    assert lb.snapshot(world.root) == kept


def test_change_plan_leaves_a_part_it_is_not_given_as_it_is_where_the_file_lacks_it(
    world: lb.World,
) -> None:
    planned(world)
    world.edit(SECOND_FILE, lambda data: data.pop("constraint"))
    run = world.run("change_plan", SECOND, "--objective", "Keep them paying", "--person-decided")
    assert run.code == 0, run.err
    changed = world.read(SECOND_FILE)
    assert "constraint" not in changed
    assert changed["objective"]["statement"] == "Keep them paying"


@pytest.mark.parametrize(("first", "laid"), [(True, {"days": 90}), (False, {})])
def test_a_window_takes_ninety_days_where_none_is_given_at_its_planning_alone(
    world: lb.World, first: bool, laid: dict[str, int]
) -> None:
    cycles, writes = lb.LIB["cycles"], lb.LIB["writes"]
    doc = lb.LIB["editing"].load(f"id: {SECOND}\nwindow:\n  start: 2027-03-10\n")
    args = lb.SCRIPT["change_plan"].parser().parse_args([SECOND, "--start", "2027-03-11"])
    files = writes.Files(world.root, writes.for_writing(world.root))
    ctx = lb.context(world.root, DAY, world.engine)
    cycles.lay_plan(ctx, files, cycles.Cycle(SECOND_FILE, doc, SECOND), args, first=first)
    assert doc.plain() == {"id": SECOND, "window": {"start": "2027-03-11", **laid}}


def test_change_plan_refuses_to_drop_a_variant_an_experiment_of_the_cycle_tests(
    world: lb.World,
) -> None:
    two_shortlisted(world)
    planned_over(world, WEEKLY, DAILY)
    tested = ("--assumption", "weekly--planning-takes-long", "--cycle", "second")
    run = world.run("new_experiment", DRAFT, "--kind", "generative", *tested)
    assert run.code == 0, run.err
    kept = lb.snapshot(world.root)
    argv = ("--variant", "daily", "--key-result", "daily:revenue:30", "--person-decided")
    run = world.run("change_plan", SECOND, *argv)
    assert run.code == 1
    assert "[cycle-variants]" in run.err
    assert lb.snapshot(world.root) == kept


def test_change_plan_is_held_to_the_check(world: lb.World) -> None:
    drafted(world)
    kept = lb.snapshot(world.root)
    run = world.run(
        "change_plan", SECOND, "--key-result", "two-sided:revenue:10", "--person-decided"
    )
    assert run.code == 1
    assert "the write would add 2 errors" in run.err
    assert "the cycle explores `meal-plan--direct`, and no key result names it" in run.err
    assert lb.snapshot(world.root) == kept


def test_change_plan_refuses_where_nothing_is_given(world: lb.World) -> None:
    run = world.run("change_plan", SECOND)
    assert run.code == 1
    assert "give what the plan changes" in run.err


# --- new-experiment, draft-experiment and remove-experiment -----------------------------------


def test_new_experiment_starts_a_draft_whose_authors_default_to_the_person(
    world: lb.World,
) -> None:
    run = world.run("new_experiment", DRAFT, "--kind", "evaluative")
    assert run.code == 0, run.err
    assert world.read(DRAFT_FILE) == {
        "pkit_schema": "lean-business:experiment",
        "schema_version": 1,
        "id": DRAFT,
        "kind": "evaluative",
        "authors": [lb.PERSON],
    }


@pytest.mark.parametrize(
    ("argv", "refused"),
    [
        (
            ("--assumption", "direct--no-such"),
            "there is no assumption `meal-plan--direct--no-such`",
        ),
        (("--cycle", "no-such"), "there is no cycle `meal-plan--no-such`"),
        (("--assumption", "other-idea--direct--x"), "an assumption of another idea"),
    ],
)
def test_new_experiment_refuses_what_names_nothing(
    world: lb.World, argv: tuple[str, ...], refused: str
) -> None:
    run = world.run("new_experiment", DRAFT, "--kind", "generative", *argv)
    assert run.code == 1
    assert refused in run.err


def test_new_experiment_in_a_suspended_cycle_writes_the_draft_and_warns(
    world: lb.World,
) -> None:
    planned(world)
    suspended(world)
    run = world.run("new_experiment", DRAFT, "--kind", "generative", "--cycle", "second")
    assert run.code == 0, run.err
    assert world.read(DRAFT_FILE)["cycle"] == f"[cycle:{SECOND}]"
    assert f"its cycle, `{SECOND}`, is suspended" in run.out
    assert f"`pkit lean resume {SECOND}`" in run.out


def test_new_experiment_refuses_an_experiment_that_exists(world: lb.World) -> None:
    run = world.run("new_experiment", LANDING_PAGE, "--kind", "evaluative")
    assert run.code == 1
    assert "exists already" in run.err


def test_draft_experiment_writes_an_evaluative_draft_in_its_keys_order(world: lb.World) -> None:
    planned(world)
    world.run("new_experiment", DRAFT, "--kind", "evaluative", "--cycle", "second")
    run = world.run(
        "draft_experiment",
        DRAFT,
        "--end",
        "2027-03-20",
        "--control",
        "split",
        "--exposed",
        "0.5",
        "--effect",
        "Easter",
        "--effect",
        "Easter",
        "--source",
        "estimate",
        "--direction",
        "at-least",
        "--threshold",
        "0.04",
        "--metric",
        "revenue",
        "--action",
        "A price of ten a month",
        "--assumption",
        TESTED,
        "--start",
        "2027-03-10",
    )
    assert run.code == 0, run.err
    text = (world.root / DRAFT_FILE).read_text(encoding="utf-8")
    keys = [line.split(":")[0] for line in text.splitlines() if line and line[0].isalpha()]
    assert keys == [
        "pkit_schema",
        "schema_version",
        "id",
        "assumption",
        "cycle",
        "kind",
        "action",
        "metric",
        "expected",
        "source",
        "effects",
        "control",
        "start",
        "end",
        "authors",
    ]
    draft = world.read(DRAFT_FILE)
    assert draft["expected"] == {"direction": "at-least", "threshold": 0.04}
    assert draft["effects"] == ["Easter"]
    assert draft["control"] == {"kind": "split", "exposed": 0.5}
    run = world.run("draft_experiment", DRAFT, "--range", "0.02", "0.06", "--control", "cohorts")
    assert run.code == 0, run.err
    draft = world.read(DRAFT_FILE)
    assert draft["expected"] == {"direction": "at-least", "range": {"low": 0.02, "high": 0.06}}
    assert draft["control"] == {"kind": "cohorts"}


def test_draft_experiment_clears_a_field(world: lb.World) -> None:
    drafted(world)
    run = world.run("draft_experiment", DRAFT, "--clear", "fit", "--clear", "learn")
    assert run.code == 0, run.err
    draft = world.read(DRAFT_FILE)
    assert "fit" not in draft
    assert "learn" not in draft


@pytest.mark.parametrize(
    ("argv", "refused"),
    [
        (("--start", "2027-03-12", "--end", "2027-03-26"), "would hold 15 days"),
        (("--start", "2027-03-12", "--end", "2027-03-11"), "before it starts"),
        (("--action", "A page"), "`action` is held by evaluative experiments alone"),
        (("--kind", "evaluative"), "clear them with the change of kind"),
        (("--learn", "x", "--clear", "learn"), "is both set and cleared"),
        (("--fit", "eight/calls"), "which is no whole number"),
        (("--fit", "8"), "is not `<count>/<what it counts>`"),
        ((), "give what the draft changes"),
    ],
)
def test_draft_experiment_refuses_what_its_declaration_could_never_hold(
    world: lb.World, argv: tuple[str, ...], refused: str
) -> None:
    drafted(world)
    kept = lb.snapshot(world.root)
    run = world.run("draft_experiment", DRAFT, *argv)
    assert run.code == 1
    assert refused in run.err
    assert lb.snapshot(world.root) == kept


@pytest.mark.parametrize(
    ("argv", "refused"),
    [
        (("--range", "0.08", "0.03", "--direction", "at-least"), "its low above its high"),
        (("--direction", "at-least"), "a --direction with a --threshold or a --range"),
        (("--control", "split"), "a split names the share of people exposed"),
        (("--exposed", "0.5"), "--exposed is given with a split alone"),
        (("--control", "split", "--exposed", "1"), "a share above 0 and below 1"),
    ],
)
def test_draft_experiment_refuses_an_expectation_or_a_control_that_does_not_read(
    world: lb.World, argv: tuple[str, ...], refused: str
) -> None:
    world.run("new_experiment", DRAFT, "--kind", "evaluative")
    run = world.run("draft_experiment", DRAFT, *argv)
    assert run.code == 1
    assert refused in run.err


@pytest.mark.parametrize(
    "argv",
    [
        ("--direction", "at-least", "--threshold", "nan"),
        ("--direction", "at-least", "--threshold", "inf"),
        ("--direction", "at-most", "--range", "1", "1e400"),
    ],
)
def test_draft_experiment_refuses_an_expected_number_that_is_not_finite(
    world: lb.World, argv: tuple[str, ...]
) -> None:
    world.run("new_experiment", DRAFT, "--kind", "evaluative")
    kept = lb.snapshot(world.root)
    run = world.run("draft_experiment", DRAFT, *argv)
    assert run.code == 1
    assert NOT_FINITE in run.err
    assert lb.snapshot(world.root) == kept


def test_draft_and_remove_experiment_refuse_once_declared(world: lb.World) -> None:
    kept = lb.snapshot(world.root)
    run = world.run("draft_experiment", LANDING_PAGE, "--action", "Another page")
    assert run.code == 1
    assert "was declared on 2026-12-10, and a declaration is frozen" in run.err
    run = world.run("remove_experiment", LANDING_PAGE)
    assert run.code == 1
    assert "a declaration is frozen, so it stays" in run.err
    assert lb.snapshot(world.root) == kept


def test_remove_experiment_removes_a_draft(world: lb.World) -> None:
    drafted(world)
    run = world.run("remove_experiment", DRAFT)
    assert run.code == 0, run.err
    assert not (world.root / DRAFT_FILE).exists()


def test_a_draft_in_a_suspended_cycle_is_warned_of(world: lb.World) -> None:
    drafted(world)
    suspended(world)
    run = world.run("draft_experiment", DRAFT, "--learn", "Whether a call a week is enough")
    assert run.code == 0, run.err
    assert f"its cycle, `{SECOND}`, is suspended" in run.out
    assert f"`pkit lean resume {SECOND}`" in run.out


# --- record-estimate --------------------------------------------------------------------------


def test_record_estimate_replaces_the_same_persons_earlier_one(world: lb.World) -> None:
    drafted(world)
    run = world.run("record_estimate", DRAFT, "4", who="B. Partner", terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [
        f"Record 4 as your own estimate for `{DRAFT}`, made alone, before seeing anyone else's?"
    ]
    run = world.run("record_estimate", DRAFT, "7.5", "--person-decided")
    assert run.code == 0, run.err
    assert "It replaces your earlier one." in run.out
    assert world.read(DRAFT_FILE)["estimates"] == [
        {"by": lb.PERSON, "value": 7.5},
        {"by": "B. Partner", "value": 4},
    ]


@pytest.mark.parametrize("value", ["nan", "inf", "1e400"])
def test_record_estimate_refuses_a_guess_that_is_not_finite(world: lb.World, value: str) -> None:
    drafted(world)
    kept = lb.snapshot(world.root)
    run = world.run("record_estimate", DRAFT, value, "--person-decided")
    assert run.code == 1
    assert NOT_FINITE in run.err
    assert lb.snapshot(world.root) == kept


def test_record_estimate_refuses_once_declared(world: lb.World) -> None:
    run = world.run("record_estimate", LANDING_PAGE, "0.04", "--person-decided")
    assert run.code == 1
    assert "a declaration is frozen" in run.err


def test_record_estimate_refuses_while_the_cycle_is_suspended(world: lb.World) -> None:
    drafted(world)
    suspended(world)
    run = world.run("record_estimate", DRAFT, "5", "--person-decided")
    assert run.code == 1
    assert f"its cycle, `{SECOND}`, is suspended" in run.err
    assert f"`pkit lean resume {SECOND}`" in run.err


# --- declare ----------------------------------------------------------------------------------


def test_declare_freezes_the_draft_and_moves_it_into_declared(world: lb.World) -> None:
    drafted(world)
    run = world.run("declare", DRAFT, terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [
        "Declare the experiment? Once declared it cannot change, and a correction is a new "
        "experiment."
    ]
    assert f"`{DRAFT}` moved from drafted to declared." in run.out
    record = world.read(DRAFT_FILE)["declared"]
    assert record["by"] == lb.PERSON
    assert record["when"] == DAY
    assert record["rested-on"]["when"] == date(2026, 10, 8)
    assert record["fingerprint"]["form"] == 1
    assert world.engine.moves[-1] == (
        "experiment-lifecycle",
        DRAFT,
        "drafted",
        "declared",
        lb.PERSON,
    )


def test_declare_names_the_variant_by_its_files_place(world: lb.World) -> None:
    # The id the canvas's file holds may differ from its place after a hand edit; the
    # declaration names the variant whose canvas it read, as the canvas's heading does.
    drafted(world)
    world.edit(lb.DIRECT, lambda data: data.update({"id": "meal-plan--other"}))
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 0, run.err
    assert (
        f"Declared `{DRAFT}`, resting on the shortlisting of `meal-plan--direct` recorded on "
        "2026-10-08"
    ) in run.out


def test_declare_moves_a_time_box_starting_today_straight_into_running(world: lb.World) -> None:
    drafted(world)
    on(world, date(2027, 3, 12))
    run = world.run("declare", DRAFT, terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [
        "Declare the experiment, its time box starting today? Once declared it cannot change, "
        "and a correction is a new experiment."
    ]
    assert f"`{DRAFT}` moved from drafted to running." in run.out


def test_declare_refuses_a_draft_its_gate_refuses(world: lb.World) -> None:
    drafted(world)
    world.edit(DRAFT_FILE, lambda data: data.pop("estimates"))
    kept = lb.snapshot(world.root)
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 1
    assert "it was declared without an estimate" in run.err
    assert lb.snapshot(world.root) == kept
    assert world.engine.moves == []


def test_declare_refuses_a_time_box_that_started_before_today(world: lb.World) -> None:
    drafted(world)
    on(world, date(2027, 3, 13))
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 1
    assert "its time box starts on 2027-03-12, before the day it was declared" in run.err


def test_declare_refuses_a_stale_shortlisting(world: lb.World) -> None:
    drafted(world)
    world.edit(lb.DIRECT, lambda data: data["boxes"]["problem"][0].update(text="Planning is dull"))
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 1
    assert "the shortlisting of `meal-plan--direct` is stale" in run.err


def test_declare_warns_where_a_riskier_assumption_is_untested(world: lb.World) -> None:
    planned(world)
    world.run("new_experiment", DRAFT, "--kind", "generative", "--cycle", "second")
    world.run(
        "draft_experiment",
        DRAFT,
        *GENERATIVE,
        "--assumption",
        TESTED,
        "--start",
        "2027-03-12",
        "--end",
        "2027-03-25",
    )
    world.run("record_estimate", DRAFT, "6", "--person-decided")
    world.run(
        "add_assumption",
        DIRECT,
        "Households cook alone",
        "--kind",
        "desirability",
        "--input",
        "price",
    )
    world.run("rank", DIRECT, "households-cook-alone", "--person-decided")
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 0, run.err
    assert (
        "warning: `meal-plan--direct--households-cook-alone`, ranked riskier than "
        f"`{TESTED}`, is untested"
    ) in run.out


def test_declare_refuses_while_the_cycle_is_suspended(world: lb.World) -> None:
    drafted(world)
    suspended(world)
    kept = lb.snapshot(world.root)
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 1
    assert f"`pkit lean resume {SECOND}`, so its declaration waits" in run.err
    assert lb.snapshot(world.root) == kept


@pytest.mark.parametrize(
    ("cycle", "day", "stands"),
    [("second", date(2027, 5, 10), "in-review"), ("first", DAY, "decided")],
    ids=["in-review", "decided"],
)
def test_declare_refuses_a_draft_whose_cycle_is_not_open(
    world: lb.World, cycle: str, day: date, stands: str
) -> None:
    planned(world)
    run = world.run("new_experiment", DRAFT, "--kind", "generative", "--cycle", cycle)
    assert run.code == 0, run.err
    on(world, day)
    kept = lb.snapshot(world.root)
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 1
    assert (
        f"its cycle, `{IDEA}--{cycle}`, stands {stands}: an experiment is declared only in an "
        "open cycle, planned or running"
    ) in run.err
    assert lb.snapshot(world.root) == kept


def test_declare_refuses_a_draft_on_a_variant_its_cycle_does_not_explore(
    world: lb.World,
) -> None:
    # The draft tests an assumption of `weekly`, and is edited by hand to test the same
    # assumption of `daily`, shortlisted, which the cycle does not explore.
    two_shortlisted(world)
    planned_over(world, WEEKLY)
    tested = ("--assumption", "weekly--planning-takes-long", "--cycle", "second")
    assert world.run("new_experiment", DRAFT, "--kind", "generative", *tested).code == 0
    times = ("--start", "2027-03-12", "--end", "2027-03-25")
    assert world.run("draft_experiment", DRAFT, *GENERATIVE, *times).code == 0
    assert world.run("record_estimate", DRAFT, "6", "--person-decided").code == 0

    def elsewhere(data: Any) -> None:
        data["assumption"] = f"[assumptions:{DAILY}--planning-takes-long]"

    world.edit(DRAFT_FILE, elsewhere)
    kept = lb.snapshot(world.root)
    run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 1
    assert (
        f"it tests an assumption of `{DAILY}`, which its cycle, `{SECOND}`, does not explore"
        in run.err
    )
    assert lb.snapshot(world.root) == kept


def test_declare_refuses_one_declared_already(world: lb.World) -> None:
    run = world.run("declare", LANDING_PAGE, "--person-decided")
    assert run.code == 1
    assert "it is not declared again" in run.err


# --- reach-stopping-rule ----------------------------------------------------------------------


def test_reach_stopping_rule_records_it_and_leaves_the_move_to_due_to_the_script(
    world: lb.World,
) -> None:
    declared(world)
    on(world, date(2027, 3, 15))
    run = world.run("reach_stopping_rule", DRAFT, terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked[0].startswith(f'Record the stopping rule of `{DRAFT}`, "Twelve calls')
    assert world.read(DRAFT_FILE)["stopped"] == {"by": lb.PERSON, "when": date(2027, 3, 15)}
    assert world.engine.moves == [("experiment-lifecycle", DRAFT, "drafted", "declared", lb.PERSON)]
    assert world.engine.status("experiment-lifecycle", DRAFT).state == "due"


def test_reach_stopping_rule_refuses_before_the_time_box_starts(world: lb.World) -> None:
    declared(world)
    run = world.run("reach_stopping_rule", DRAFT, "--person-decided")
    assert run.code == 1
    assert "before its time box started" in run.err


def test_reach_stopping_rule_refuses_after_the_time_box_ended(world: lb.World) -> None:
    declared(world)
    on(world, date(2027, 3, 26))
    run = world.run("reach_stopping_rule", DRAFT, "--person-decided")
    assert run.code == 1
    assert "after its time box ended on 2027-03-25" in run.err
    assert "stopped" not in world.read(DRAFT_FILE)


def test_reach_stopping_rule_refuses_one_recorded_already(world: lb.World) -> None:
    declared(world)
    on(world, date(2027, 3, 15))
    assert world.run("reach_stopping_rule", DRAFT, "--person-decided").code == 0
    on(world, date(2027, 3, 16))
    kept = lb.snapshot(world.root)
    run = world.run("reach_stopping_rule", DRAFT, "--person-decided")
    assert run.code == 1
    assert f"`{DRAFT}` records its stopping rule reached already, on 2027-03-15" in run.err
    assert lb.snapshot(world.root) == kept


def test_reach_stopping_rule_refuses_a_draft(world: lb.World) -> None:
    drafted(world)
    on(world, date(2027, 3, 15))
    run = world.run("reach_stopping_rule", DRAFT, "--person-decided")
    assert run.code == 1
    assert f"`{DRAFT}` is a draft: a stopping rule is reached once it is declared" in run.err


def test_reach_stopping_rule_refuses_an_evaluative_experiment(world: lb.World) -> None:
    run = world.run("reach_stopping_rule", LANDING_PAGE, "--person-decided")
    assert run.code == 1
    assert "only a generative experiment has a stopping rule" in run.err


def test_reach_stopping_rule_refuses_while_the_cycle_is_suspended(world: lb.World) -> None:
    declared(world)
    suspended(world)
    run = world.run("reach_stopping_rule", DRAFT, "--person-decided")
    assert run.code == 1
    assert f"`pkit lean resume {SECOND}`" in run.err


# --- record-result and decide -----------------------------------------------------------------


def test_the_path_from_a_result_to_a_decision(world: lb.World) -> None:
    declared(world)
    on(world, date(2027, 3, 15))
    run = world.run("decide", DRAFT, "double-down", "--person-decided")
    assert run.code == 1
    assert "stands running, not due" in run.err
    assert world.run("reach_stopping_rule", DRAFT, "--person-decided").code == 0
    run = world.run("decide", DRAFT, "double-down", "--person-decided")
    assert run.code == 1
    assert f"`pkit lean record-result {DRAFT}" in run.err
    run = world.run(
        "record_result",
        DRAFT,
        "--measured",
        "9",
        "--evidence",
        "The call notes",
        "--learned",
        "A weekly call keeps them planning",
        terminal=True,
        answers=[True],
    )
    assert run.code == 0, run.err
    assert run.asked == [f"Record the result of `{DRAFT}`: 9 measured, which works out to a pass?"]
    on(world, date(2027, 3, 16))
    run = world.run("decide", DRAFT, "double-down", terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [
        "Decide the experiment on what it found, with the next action given? Once decided, "
        "neither its result nor its next action can change."
    ]
    assert f"`{DRAFT}` moved from due to decided." in run.out
    assert world.read(DRAFT_FILE)["decision"] == {
        "next": "double-down",
        "by": lb.PERSON,
        "when": date(2027, 3, 16),
    }


def refused_by_the_engine(world: lb.World, monkeypatch: pytest.MonkeyPatch) -> None:
    """An engine whose `can-move` refuses every move."""

    def refused(process: str, subject: str, to: str, actor: str) -> Any:
        return lb.engine.Verdict(False, "its gate refuses it")

    monkeypatch.setattr(world.engine, "can_move", refused)


def test_decide_and_declare_say_nothing_before_the_engine_refuses_the_move(
    world: lb.World, monkeypatch: pytest.MonkeyPatch
) -> None:
    drafted(world)
    added(world)
    assert world.run("rank", DIRECT, "households-cook-alone", "--person-decided").code == 0
    with monkeypatch.context() as stubbed:
        refused_by_the_engine(world, stubbed)
        run = world.run("declare", DRAFT, "--person-decided")
    assert run.code == 1
    assert "the process engine refuses `declare`" in run.err
    assert run.out == ""
    assert world.run("remove_assumption", ADDED).code == 0
    assert world.run("declare", DRAFT, "--person-decided").code == 0
    on(world, date(2027, 3, 15))
    assert world.run("reach_stopping_rule", DRAFT, "--person-decided").code == 0
    argv = ("--measured", "9", "--evidence", "Notes", "--learned", "Some", "--person-decided")
    assert world.run("record_result", DRAFT, *argv).code == 0
    refused_by_the_engine(world, monkeypatch)
    run = world.run("decide", DRAFT, "double-down", "--person-decided")
    assert run.code == 1
    assert "the process engine refuses `decide`" in run.err
    assert run.out == ""


def test_record_result_replaces_an_earlier_one_and_says_what_it_works_out_to(
    world: lb.World,
) -> None:
    declared(world)
    on(world, date(2027, 3, 26))
    argv = ("--evidence", "The call notes", "--learned", "Too few calls", "--person-decided")
    assert world.run("record_result", DRAFT, *argv).code == 0
    run = world.run("record_result", DRAFT, "--measured", "3", *argv)
    assert run.code == 0, run.err
    assert "works out to neither pass nor fail. It replaces the result recorded before." in run.out
    assert world.read(DRAFT_FILE)["result"]["measured"] == 3


def test_record_result_refuses_a_spoiled_measurement_no_suspension_ran_through(
    world: lb.World,
) -> None:
    declared(world)
    on(world, date(2027, 3, 26))
    run = world.run(
        "record_result",
        DRAFT,
        "--spoiled",
        "--evidence",
        "The call notes",
        "--learned",
        "Nothing",
        "--person-decided",
    )
    assert run.code == 1
    assert "a measurement is spoiled only by a suspension its time box ran through" in run.err


def test_record_result_asks_of_a_spoiled_measurement_where_nothing_was_measured(
    world: lb.World,
) -> None:
    declared(world)
    suspended(world)
    on(world, date(2027, 3, 16))
    run = world.run("resume", SECOND, "--person-decided")
    assert run.code == 0, run.err
    on(world, date(2027, 3, 28))
    argv = ("--evidence", "The call notes", "--learned", "Nothing to read")
    run = world.run("record_result", DRAFT, "--spoiled", *argv, terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [
        f"Record the result of `{DRAFT}`: nothing measured, spoiled, which works out to "
        "neither pass nor fail?"
    ]
    assert world.read(DRAFT_FILE)["result"]["spoiled"] is True


def test_record_result_refuses_a_measurement_that_is_not_finite(world: lb.World) -> None:
    declared(world)
    on(world, date(2027, 3, 26))
    kept = lb.snapshot(world.root)
    argv = ("--evidence", "The call notes", "--learned", "Nothing", "--person-decided")
    run = world.run("record_result", DRAFT, "--measured", "nan", *argv)
    assert run.code == 1
    assert f"`nan` {NOT_FINITE}" in run.err
    assert lb.snapshot(world.root) == kept


def test_record_result_and_decide_refuse_a_draft_or_a_decided_one(world: lb.World) -> None:
    drafted(world)
    argv = ("--evidence", "Notes", "--learned", "Something", "--person-decided")
    run = world.run("record_result", DRAFT, *argv)
    assert run.code == 1
    assert "is a draft" in run.err
    run = world.run("record_result", LANDING_PAGE, *argv)
    assert run.code == 1
    assert "is decided" in run.err
    run = world.run("decide", LANDING_PAGE, "stop", "--person-decided")
    assert run.code == 1
    assert "is decided already" in run.err


def test_decide_refuses_while_the_cycle_is_suspended(world: lb.World) -> None:
    due_with_a_result(world)
    on(world, date(2027, 3, 17))
    argv = ("--reason", "Ill", "--since", "2027-03-17", "--person-decided")
    assert world.run("suspend", SECOND, *argv).code == 0
    kept = lb.snapshot(world.root)
    run = world.run("decide", DRAFT, "double-down", "--person-decided")
    assert run.code == 1
    assert f"`pkit lean resume {SECOND}`, so its decision waits" in run.err
    assert lb.snapshot(world.root) == kept


def test_decide_refuses_where_its_result_was_recorded_after_today(world: lb.World) -> None:
    # The result, recorded on 2027-03-16, is later than the day the decision would be.
    due_with_a_result(world)
    on(world, date(2027, 3, 15))
    kept = lb.snapshot(world.root)
    run = world.run("decide", DRAFT, "double-down", "--person-decided")
    assert run.code == 1
    assert "its result was recorded on 2027-03-16, after its decision, on 2027-03-15" in run.err
    assert lb.snapshot(world.root) == kept


def test_record_result_refuses_while_the_cycle_is_suspended(world: lb.World) -> None:
    declared(world)
    suspended(world)
    run = world.run(
        "record_result", DRAFT, "--evidence", "Notes", "--learned", "Some", "--person-decided"
    )
    assert run.code == 1
    assert f"`pkit lean resume {SECOND}`" in run.err


# --- asked off a terminal, and answered no ----------------------------------------------------


def running(world: lb.World) -> None:
    """The draft declared, on a day its time box runs."""
    declared(world)
    on(world, date(2027, 3, 15))


def ended(world: lb.World) -> None:
    """The draft declared, on the day after its time box ended."""
    declared(world)
    on(world, date(2027, 3, 26))


#: Each act and move of the experiment path that asks the person, with the world it is asked
#: in and what it is given.
ASKING: dict[str, tuple[Callable[[lb.World], None], tuple[str, ...]]] = {
    "plan_cycle": (lambda _: None, (SECOND, *PLAN)),
    "change_plan": (planned, (SECOND, "--objective", "Keep them")),
    "record_estimate": (drafted, (DRAFT, "7")),
    "declare": (drafted, (DRAFT,)),
    "reach_stopping_rule": (running, (DRAFT,)),
    "record_result": (ended, (DRAFT, "--evidence", "Notes", "--learned", "Some")),
    "decide": (due_with_a_result, (DRAFT, "double-down")),
}


@pytest.mark.parametrize("command", list(ASKING))
def test_each_asking_command_writes_nothing_off_a_terminal_or_on_a_no(
    world: lb.World, command: str
) -> None:
    prepared, argv = ASKING[command]
    prepared(world)
    kept = lb.snapshot(world.root)
    run = world.run(command, *argv)
    assert run.code == 3, run.err
    assert "?" in run.out + run.err
    assert lb.snapshot(world.root) == kept
    run = world.run(command, *argv, terminal=True, answers=[False])
    assert run.code == 1, run.err
    assert len(run.asked) == 1
    assert lb.snapshot(world.root) == kept


# --- naming an assumption or a cycle ----------------------------------------------------------

#: An untested assumption the tests add, and each name of it: its id, the part after the
#: idea, and its own part.
ADDED = "meal-plan--direct--households-cook-alone"
NAMES_OF_ADDED = (ADDED, "direct--households-cook-alone", "households-cook-alone")

#: A second draft, for the command that drafts what a draft names.
OTHER_DRAFT = "meal-plan--daily-calls"
OTHER_DRAFT_FILE = f"{lb.IDEA}/experiments/daily-calls.yaml"


def added(world: lb.World) -> None:
    run = world.run(
        "add_assumption",
        DIRECT,
        "Households cook alone",
        "--kind",
        "desirability",
        "--input",
        "price",
    )
    assert run.code == 0, run.err


def both_drafts_name(world: lb.World, flag: str, name: str) -> list[Any]:
    """What each draft names under `flag`: one drafted with `name` from the start, and one
    given it afterwards."""
    run = world.run("new_experiment", DRAFT, "--kind", "generative", flag, name)
    assert run.code == 0, run.err
    run = world.run("new_experiment", OTHER_DRAFT, "--kind", "generative")
    assert run.code == 0, run.err
    run = world.run("draft_experiment", OTHER_DRAFT, flag, name)
    assert run.code == 0, run.err
    key = flag.removeprefix("--")
    return [world.read(rel)[key] for rel in (DRAFT_FILE, OTHER_DRAFT_FILE)]


@pytest.mark.parametrize("name", NAMES_OF_ADDED)
def test_each_command_that_names_an_assumption_takes_each_name_of_it(
    world: lb.World, name: str
) -> None:
    added(world)
    run = world.run("edit_assumption", name, "--statement", "Households cook on their own")
    assert run.code == 0, run.err
    assert listed(world)[-1]["statement"] == "Households cook on their own"
    run = world.run("rank", DIRECT, name, "--person-decided")
    assert run.code == 0, run.err
    assert ranks(world) == {ADDED: 1, PLANNING_TAKES_LONG: 2, TESTED: 3}
    assert both_drafts_name(world, "--assumption", name) == [f"[assumptions:{ADDED}]"] * 2
    for draft in (DRAFT, OTHER_DRAFT):
        assert world.run("remove_experiment", draft).code == 0
    run = world.run("remove_assumption", name)
    assert run.code == 0, run.err
    assert ADDED not in ranks(world)


@pytest.mark.parametrize("name", [SECOND, "second"])
def test_each_command_that_names_a_cycle_takes_each_name_of_it(world: lb.World, name: str) -> None:
    planned(world)
    run = world.run("change_plan", name, "--days", "45", "--person-decided")
    assert run.code == 0, run.err
    assert world.read(SECOND_FILE)["window"]["days"] == 45
    assert both_drafts_name(world, "--cycle", name) == [f"[cycle:{SECOND}]"] * 2


@pytest.mark.parametrize(
    ("argv", "refused"),
    [
        (
            ("edit_assumption", "Households", "--statement", "Words"),
            "`Households` names no assumption: give its id, `<idea>--<variant>--<assumption>`",
        ),
        (
            ("edit_assumption", "no-such", "--statement", "Words"),
            "`no-such` names no assumption in the location",
        ),
        (
            ("remove_assumption", "two-sided--pays-monthly"),
            "`two-sided--pays-monthly` names no assumption in the location",
        ),
        (
            ("new_experiment", DRAFT, "--kind", "generative", "--assumption", "no-such"),
            "`no-such` names no assumption of `meal-plan`",
        ),
        (("change_plan", "no-such", "--days", "45"), "`no-such` names no cycle in the location"),
        (("change_plan", "a--b--c", "--days", "45"), "`a--b--c` names no cycle"),
    ],
)
def test_a_name_that_reads_as_no_assumption_or_cycle_is_refused(
    world: lb.World, argv: tuple[str, ...], refused: str
) -> None:
    kept = lb.snapshot(world.root)
    run = world.run(*argv)
    assert run.code == 1
    assert refused in run.err
    assert lb.snapshot(world.root) == kept


def test_a_part_that_more_than_one_id_ends_with_is_refused_naming_each(world: lb.World) -> None:
    run = world.run(
        "add_assumption",
        "meal-plan--two-sided",
        "Cooks pay monthly",
        "--kind",
        "viability",
        "--input",
        "price",
        "--id",
        "pays-monthly",
    )
    assert run.code == 0, run.err
    shutil.copytree(world.root / lb.IDEA / "cycles", world.root / "lean-business/other/cycles")
    kept = lb.snapshot(world.root)
    two = "`meal-plan--direct--pays-monthly`, `meal-plan--two-sided--pays-monthly`"
    run = world.run("new_experiment", DRAFT, "--kind", "generative", "--assumption", "pays-monthly")
    assert run.code == 1
    assert f"`pays-monthly` names 2 assumptions of `meal-plan`, {two}" in run.err
    run = world.run("edit_assumption", "pays-monthly", "--statement", "Words")
    assert run.code == 1
    assert f"`pays-monthly` names 2 assumptions in the location, {two}" in run.err
    run = world.run("change_plan", "first", "--days", "45", "--person-decided")
    assert run.code == 1
    assert "`first` names 2 cycles in the location, `meal-plan--first`, `other--first`" in run.err
    assert lb.snapshot(world.root) == kept
    run = world.run("edit_assumption", "direct--pays-monthly", "--statement", "Words")
    assert run.code == 0, run.err
