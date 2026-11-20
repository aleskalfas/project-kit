"""Every write of lean-business's commands, alike (lean-business DEC-001 point 3; DEC-002
points 1, 2, 7 and 14; DEC-003 points 1 and 5): the ids a command gives, its files written
round trip, each write held to the check and the data validation before anything is
written, the location's record, the consent forms, and the five ways a command meets the
process engine:

- a move with one target, `judge`'s yes on the next step;
- a move with two targets, a cycle's resuming, which lands in running or in review;
- an act with no move, `judge`'s no on the next step;
- an act followed by the script's move, a cycle's suspension;
- a move whose gate the write satisfies, a cycle's decision.

Each runs in this process, on a day the test names, against an engine that asks the same
predicates as the engine itself (`tests/lean_business_world.py`). The last test runs one
command against the engine itself."""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from tests import lean_business_world as lb
from tests.adopter_repo import MakeAdopterRepo
from tests.in_process import route_pkit, run_main

acting, editing, naming, writes = lb.acting, lb.LIB["editing"], lb.LIB["naming"], lb.LIB["writes"]

DAY = date(2026, 11, 20)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> lb.World:
    return lb.world(tmp_path, monkeypatch, DAY)


def sketched(world: lb.World) -> None:
    """The fixture's `direct` variant taken back to sketched: no verdict, no outcome."""

    def change(data: Any) -> None:
        del data["verdicts"]
        del data["outcome"]

    world.edit(lb.DIRECT, change)


# --- ids --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Planning the week's meals takes too long", "planning-the-weeks-meals-takes"),
        ("Café crème, à emporter", "cafe-creme-a-emporter"),
        ("3 meals a day", "n3-meals-a-day"),
        ("  Lists — on paper!  ", "lists-on-paper"),
        ("日本語", "problem"),
    ],
)
def test_an_id_from_text_keeps_its_first_words_in_kebab_case(text: str, expected: str) -> None:
    assert naming.from_text(text, "problem") == expected


def test_an_id_from_text_is_numbered_where_it_is_taken_and_a_typed_one_is_refused() -> None:
    taken = {"idea--v--paper-lists", "idea--v--paper-lists-2"}
    given = naming.given("idea--v", typed=None, text="Paper lists", fallback="x", taken=taken)
    assert given == "idea--v--paper-lists-3"
    with pytest.raises(writes.Refused, match="is taken"):
        naming.given("idea--v", typed="paper-lists", text="", fallback="x", taken=taken)
    with pytest.raises(writes.Refused, match="is no id"):
        naming.given("idea--v", typed="Paper Lists", text="", fallback="x", taken=taken)


def test_an_id_a_reference_still_names_is_never_given_again(world: lb.World) -> None:
    # The assumption keeps naming the problem it tested, removed from the canvas.
    entry = "meal-plan--direct--planning-takes-long"
    run = world.run("remove_entry", entry)
    assert run.code == 0, run.err
    typed = ("--id", "planning-takes-long")
    run = world.run("add_entry", "meal-plan--direct", "problem", "Planning takes long", *typed)
    assert run.code == 1
    assert f"the id `{entry}` is taken" in run.err
    run = world.run("add_entry", "meal-plan--direct", "problem", "Planning takes long")
    assert run.code == 0, run.err
    assert f"Added `{entry}-2` to problem." in run.out


def test_an_id_never_changes_with_its_text(world: lb.World) -> None:
    entry = "meal-plan--direct--paper-lists"
    run = world.run("edit_entry", entry, "--text", "Spreadsheets kept by hand")
    assert run.code == 0, run.err
    held = world.read(lb.DIRECT)["boxes"]["existing-alternatives"]
    assert held == [{"id": entry, "text": "Spreadsheets kept by hand"}]


# --- round trip -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [lb.FIXTURE / lb.DIRECT, lb.FIXTURE / lb.CYCLE, lb.CAPABILITY / "schemas/canvas.yaml"],
    ids=["dash-at-the-key", "a-cycle", "dash-indented"],
)
def test_a_file_written_unchanged_keeps_every_byte(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert editing.load(text).text() == text


def test_a_key_added_lands_where_the_schema_writes_it_and_comments_stay(world: lb.World) -> None:
    run = world.run("set_traction", "meal-plan--direct", "--multiplier", "8")
    assert run.code == 0, run.err
    text = (world.root / lb.DIRECT).read_text(encoding="utf-8")
    assert text.startswith("# A direct model, judged yes on every step and shortlisted.\n")
    assert "traction:\n  multiplier: 8\n  first-stage:" in text


# --- held before anything is written ----------------------------------------------------------


def test_a_write_that_adds_an_error_is_refused_and_writes_nothing(world: lb.World) -> None:
    before = lb.snapshot(world.root)
    run = world.run("add_side", "meal-plan--direct", "cooks")
    assert run.code == 1
    assert "the write would add 1 error" in run.err
    assert "[sides]" in run.err and "a direct model names no sides" in run.err
    assert lb.snapshot(world.root) == before


def test_an_error_of_the_schema_is_named_as_the_data_validation_names_it(world: lb.World) -> None:
    files = writes.Files(world.root, writes.for_writing(world.root))
    doc = files.read(lb.DIRECT)
    assert doc is not None
    doc.data["archetype"] = "franchise"
    files.put(lb.DIRECT, doc)
    before = lb.snapshot(world.root)
    ctx = lb.context(world.root, DAY, world.engine)
    with pytest.raises(writes.Refused) as refused:
        acting.content(ctx, files, "written")
    assert f"{lb.DIRECT}#/archetype  [data]" in str(refused.value)
    assert lb.snapshot(world.root) == before


def test_an_error_already_in_the_files_is_named_and_refuses_nothing(world: lb.World) -> None:
    world.edit(lb.GOAL, lambda data: data.pop("currency"))
    run = world.run("add_entry", "meal-plan--direct", "cost-structure", "Delivery partners")
    assert run.code == 0, run.err
    assert "Already in the files, and left as they were: 1 error" in run.out
    assert f"{lb.GOAL}  [data]" in run.out


def test_a_warning_the_write_adds_is_named(world: lb.World) -> None:
    run = world.run("add_entry", "meal-plan--direct", "problem", "Recipes repeat")
    assert run.code == 0, run.err
    assert "[link]" in run.out
    assert "the problem names no existing alternative it is framed against" in run.out


# --- the location -----------------------------------------------------------------------------


def test_the_first_write_records_the_location_and_says_where_to_change_it(world: lb.World) -> None:
    assert not (world.root / lb.CONFIG).exists()
    run = world.run("add_entry", "meal-plan--direct", "cost-structure", "Delivery partners")
    assert run.code == 0, run.err
    assert world.read(lb.CONFIG)["location"] == "lean-business"
    assert f"Recorded where the ideas live, `lean-business/`, in `{lb.CONFIG}`" in run.out
    again = world.run("add_entry", "meal-plan--direct", "cost-structure", "Packaging")
    assert "Recorded where" not in again.out


def test_a_default_folder_holding_files_of_another_kind_records_nothing(world: lb.World) -> None:
    (world.root / "lean-business/notes.md").write_text("# Notes\n", encoding="utf-8")
    before = lb.snapshot(world.root)
    run = world.run("add_entry", "meal-plan--direct", "cost-structure", "Delivery partners")
    assert run.code == 1
    assert "`lean-business/notes.md`, a file of another kind" in run.err
    assert "pkit lean set-location <path>" in run.err
    assert lb.snapshot(world.root) == before


def test_set_location_records_a_folder_and_the_next_write_goes_there(world: lb.World) -> None:
    shutil.rmtree(world.root / "lean-business")
    run = world.run("set_location", "ideas")
    assert run.code == 0, run.err
    assert world.read(lb.CONFIG) == {
        "pkit_schema": "lean-business:config",
        "schema_version": 1,
        "location": "ideas",
    }
    run = world.run("new_variant", "board-game--platform", "--archetype", "marketplace")
    assert run.code == 0, run.err
    assert (world.root / "ideas/board-game/variants/platform/canvas.yaml").is_file()
    assert (world.root / "ideas/board-game/variants/platform/assumptions.yaml").is_file()


def test_set_location_refuses_while_the_location_in_use_holds_an_idea(world: lb.World) -> None:
    run = world.run("set_location", "ideas")
    assert run.code == 1
    assert "holds `meal-plan`: move the folder to `ideas/` first" in run.err
    assert not (world.root / lb.CONFIG).exists()


@pytest.mark.parametrize("recorded", [False, True], ids=["none-recorded", "the-old-one-recorded"])
def test_set_location_after_the_folder_is_moved_refuses_nothing_on_an_error_already_there(
    world: lb.World, recorded: bool
) -> None:
    # An error the check finds and the schema does not: a direct model naming a side.
    world.edit(lb.DIRECT, lambda data: data.insert(4, "sides", ["cooks"]))
    if recorded:
        first = world.run("add_entry", "meal-plan--direct", "cost-structure", "Packaging")
        assert first.code == 0, first.err
        assert world.read(lb.CONFIG)["location"] == "lean-business"
    # As set-location's refusal asks: the folder moved first, then the location recorded.
    shutil.move(world.root / "lean-business", world.root / "ideas")
    run = world.run("set_location", "ideas")
    assert run.code == 0, run.err
    assert world.read(lb.CONFIG)["location"] == "ideas"
    assert "Already in the files, and left as they were: 1 error" in run.out
    assert "ideas/meal-plan/variants/direct/canvas.yaml#/sides  [sides]" in run.out


def test_set_location_refuses_a_folder_the_rules_refuse(world: lb.World) -> None:
    run = world.run("set_location", ".pkit/ideas")
    assert run.code == 1
    assert "lies under `.pkit/`" in run.err


# --- the consent forms ------------------------------------------------------------------------


def test_off_a_terminal_an_act_without_the_persons_word_does_nothing_and_asks(
    world: lb.World,
) -> None:
    sketched(world)
    before = lb.snapshot(world.root)
    run = world.run("judge", "meal-plan--direct", "desirability", "no")
    assert run.code == acting.ASKED
    assert (
        run.out
        == "Record a no on desirability for `meal-plan--direct`? It stays sketched until a yes.\n"
    )
    assert "--person-decided" in run.err
    assert lb.snapshot(world.root) == before


def test_at_a_terminal_an_act_is_taken_on_a_yes_and_not_on_a_no(world: lb.World) -> None:
    sketched(world)
    before = lb.snapshot(world.root)
    refused = world.run(
        "judge", "meal-plan--direct", "desirability", "no", terminal=True, answers=[False]
    )
    assert refused.code == 1
    assert refused.asked == [
        "Record a no on desirability for `meal-plan--direct`? It stays sketched until a yes."
    ]
    assert lb.snapshot(world.root) == before
    taken = world.run(
        "judge", "meal-plan--direct", "desirability", "no", terminal=True, answers=[True]
    )
    assert taken.code == 0, taken.err
    assert world.read(lb.DIRECT)["verdicts"]["desirability"]["answer"] == "no"


def test_an_act_records_who_by_gits_user_name_and_refuses_without_one(world: lb.World) -> None:
    sketched(world)
    run = world.run(
        "judge", "meal-plan--direct", "desirability", "no", "--person-decided", who=None
    )
    assert run.code == 1
    assert "git names nobody" in run.err
    run = world.run(
        "judge", "meal-plan--direct", "desirability", "no", "--person-decided", who="B. Partner"
    )
    assert run.code == 0, run.err
    verdict = world.read(lb.DIRECT)["verdicts"]["desirability"]
    assert (verdict["by"], verdict["when"]) == ("B. Partner", DAY)


def test_content_takes_no_question_and_records_no_one(world: lb.World) -> None:
    run = world.run(
        "add_entry", "meal-plan--direct", "cost-structure", "Delivery partners", who=None
    )
    assert (run.code, run.asked) == (0, [])
    assert world.read(lb.DIRECT)["boxes"]["cost-structure"][-1] == {
        "id": "meal-plan--direct--delivery-partners",
        "text": "Delivery partners",
    }


# --- the five ways a command meets the engine -------------------------------------------------


def test_a_move_with_one_target(world: lb.World) -> None:
    sketched(world)
    run = world.run("judge", "meal-plan--direct", "desirability", "yes", "--person-decided")
    assert run.code == 0, run.err
    assert world.engine.moves == [
        ("desk-stage", "meal-plan--direct", "sketched", "desirable", lb.PERSON)
    ]
    kinds = [kind for kind, _, _ in world.engine.asked]
    assert kinds == ["status", "can-move", "status", "move"]
    assert "`meal-plan--direct` moved from sketched to desirable." in run.out


def test_a_move_asks_the_definitions_prompt(world: lb.World) -> None:
    sketched(world)
    run = world.run("judge", "meal-plan--direct", "desirability", "yes")
    assert run.code == acting.ASKED
    assert run.out.startswith("Is the variant desirable:")


def test_a_move_whose_gate_is_closed_is_refused_before_the_write(world: lb.World) -> None:
    sketched(world)
    world.edit(lb.DIRECT, lambda data: data["boxes"].pop("early-adopters"))
    before = lb.snapshot(world.root)
    run = world.run("judge", "meal-plan--direct", "desirability", "yes", "--person-decided")
    assert run.code == 1
    assert "the process engine refuses `pass-desirability`" in run.err
    assert "`early-adopters`" in run.err
    assert lb.snapshot(world.root) == before
    assert world.engine.moves == []


def _cycle(world: lb.World, change: Any) -> None:
    """The fixture's cycle, its review taken away and `change` made to it, with no
    experiment beside it."""
    for experiment in (world.root / lb.IDEA / "experiments").iterdir():
        experiment.unlink()

    def edited(data: Any) -> None:
        del data["review"]
        change(data)

    world.edit(lb.CYCLE, edited)


def _suspended_on_day_50(data: Any) -> None:
    data["suspensions"][0] = editing.mapping(
        [
            ("reason", "A family matter"),
            ("first-day", date(2026, 12, 20)),
            ("by", lb.PERSON),
            ("when", date(2027, 2, 28)),
        ]
    )


def _resumed(world: lb.World, day: date) -> tuple[Any, str]:
    files = writes.Files(world.root, writes.for_writing(world.root))
    doc = files.read(lb.CYCLE)
    assert doc is not None
    doc.data["suspensions"][0]["resumed"] = editing.mapping(
        [("day", day), ("by", lb.PERSON), ("when", world.engine.on)]
    )
    files.put(lb.CYCLE, doc)
    return files, f"Resumed on {day}."


@pytest.mark.parametrize(
    ("resumed", "lands"),
    [(date(2027, 1, 19), "running"), (date(2027, 1, 9), "in-review")],
    ids=["on-day-80-into-running", "on-day-70-into-review"],
)
def test_a_move_with_two_targets_goes_where_the_engine_places_it_after_the_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, resumed: date, lands: str
) -> None:
    # Decision 23's example: a window of days 1 to 90, suspended on day 50 and recorded on
    # day 120. Both of resuming's gates open before the write, and the day resumed decides.
    world = lb.world(tmp_path, monkeypatch, date(2027, 2, 28))
    _cycle(world, _suspended_on_day_50)
    ctx = lb.context(world.root, world.engine.on, world.engine)
    before = acting.position(ctx, "cycle-lifecycle", "meal-plan--first")
    assert before.state == "suspended"
    assert sorted(m.to for m in before.by("resume") if m.allowed) == ["in-review", "running"]
    moved = acting.person_move(
        ctx,
        "cycle-lifecycle",
        "meal-plan--first",
        "resume",
        before,
        lambda: _resumed(world, resumed),
        decided=True,
    )
    assert moved == lands
    assert world.engine.moves == [
        ("cycle-lifecycle", "meal-plan--first", "suspended", lands, lb.PERSON)
    ]
    can_moves = [what for kind, _, what in world.engine.asked if kind == "can-move"]
    assert sorted(can_moves) == ["meal-plan--first to in-review", "meal-plan--first to running"]


def test_an_act_with_no_move(world: lb.World) -> None:
    sketched(world)
    run = world.run("judge", "meal-plan--direct", "desirability", "no", "--person-decided")
    assert run.code == 0, run.err
    assert world.engine.moves == []
    assert [kind for kind, _, _ in world.engine.asked] == ["status"]
    verdict = world.read(lb.DIRECT)["verdicts"]["desirability"]
    assert (verdict["answer"], verdict["by"], verdict["when"]) == ("no", lb.PERSON, DAY)


def _suspension(world: lb.World) -> Any:
    files = writes.Files(world.root, writes.for_writing(world.root))
    doc = files.read(lb.CYCLE)
    assert doc is not None
    doc.data["suspensions"] = editing.seq(
        [
            editing.mapping(
                [
                    ("reason", "A family matter"),
                    ("first-day", date(2026, 12, 20)),
                    ("by", lb.PERSON),
                    ("when", world.engine.on),
                ]
            )
        ]
    )
    files.put(lb.CYCLE, doc)
    return files


def test_an_act_followed_by_the_scripts_move_asks_no_can_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = lb.world(tmp_path, monkeypatch, date(2026, 12, 21))
    _cycle(world, lambda data: data.pop("suspensions"))
    ctx = lb.context(world.root, world.engine.on, world.engine)
    before = acting.position(ctx, "cycle-lifecycle", "meal-plan--first")
    assert before.state == "running"
    moved = acting.act_then_moved(
        ctx,
        "cycle-lifecycle",
        "meal-plan--first",
        before,
        _suspension(world),
        "Suspended.",
        question="Suspend the cycle?",
        decided=True,
    )
    assert moved == "suspended"
    assert world.engine.moves == [
        ("cycle-lifecycle", "meal-plan--first", "running", "suspended", lb.PERSON)
    ]
    assert "can-move" not in [kind for kind, _, _ in world.engine.asked]


def _review(world: lb.World, winning: str) -> tuple[Any, str]:
    files = writes.Files(world.root, writes.for_writing(world.root))
    doc = files.read(lb.CYCLE)
    assert doc is not None
    doc.data["review"] = editing.mapping(
        [
            ("reached", editing.seq([52])),
            ("winning", f"[canvas:{winning}]"),
            ("decision", "persevere"),
            ("reasons", "Retention passed its target"),
            ("by", lb.PERSON),
            ("when", world.engine.on),
        ]
    )
    files.put(lb.CYCLE, doc)
    return files, "Reviewed."


def _in_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[lb.World, Any, Any]:
    world = lb.world(tmp_path, monkeypatch, date(2027, 2, 15))
    _cycle(world, lambda data: None)
    ctx = lb.context(world.root, world.engine.on, world.engine)
    before = acting.position(ctx, "cycle-lifecycle", "meal-plan--first")
    assert before.state == "in-review"
    return world, ctx, before


def test_a_move_whose_gate_the_write_satisfies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, ctx, before = _in_review(tmp_path, monkeypatch)
    moved = acting.person_move(
        ctx,
        "cycle-lifecycle",
        "meal-plan--first",
        "decide",
        before,
        lambda: _review(world, "meal-plan--direct"),
        decided=True,
    )
    assert moved == "decided"
    assert world.engine.moves == [
        ("cycle-lifecycle", "meal-plan--first", "in-review", "decided", lb.PERSON)
    ]


def test_where_the_move_is_refused_after_the_write_everything_written_is_undone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, ctx, before = _in_review(tmp_path, monkeypatch)
    kept = lb.snapshot(world.root)
    world.engine.refuse_move = "its gate refuses what the write recorded"
    with pytest.raises(writes.Refused, match="so the write was undone"):
        acting.person_move(
            ctx,
            "cycle-lifecycle",
            "meal-plan--first",
            "decide",
            before,
            lambda: _review(world, "meal-plan--direct"),
            decided=True,
        )
    # The location's record, written by this first write, is undone with the rest.
    assert lb.snapshot(world.root) == kept
    assert not (world.root / lb.CONFIG).exists()
    assert not (world.root / lb.CONFIG).parent.exists()


class _PlacesElsewhere:
    """The in-process engine, except that after the write it places the subject in `state`,
    where the trigger asked does not lead, and that it would take any move asked of it."""

    def __init__(self, inner: lb.InProcessEngine, state: str) -> None:
        self.inner = inner
        self.state = state
        self.statuses = 0
        self.moved: list[tuple[str, str]] = []

    def status(self, process: str, subject: str) -> Any:
        self.statuses += 1
        if self.statuses == 1:
            return self.inner.status(process, subject)
        return lb.engine.Status(self.state)

    def can_move(self, process: str, subject: str, to: str, actor: str) -> Any:
        return self.inner.can_move(process, subject, to, actor)

    def move(self, process: str, subject: str, to: str, origin: str, actor: str) -> Any:
        self.moved.append((origin, to))
        return lb.engine.Verdict(True, "moved")


def test_where_the_write_leaves_the_subject_where_its_trigger_does_not_lead_it_is_undone(
    world: lb.World,
) -> None:
    sketched(world)
    kept = lb.snapshot(world.root)
    elsewhere = _PlacesElsewhere(world.engine, "shelved")
    ctx = lb.context(world.root, DAY, elsewhere)
    judge = lb.SCRIPT["judge"]
    argv = ["meal-plan--direct", "desirability", "yes", "--person-decided"]
    assert acting.invoke(judge.parser(), judge.run, argv, ctx) == acting.REFUSED
    assert (
        "after the write `meal-plan--direct` stands in shelved, where `pass-desirability` "
        "does not lead from sketched, so the write was undone"
    ) in ctx.err.getvalue()
    assert ctx.out.getvalue() == ""
    assert elsewhere.moved == []
    # The verdict and the location's record, written by this first write, are undone.
    assert lb.snapshot(world.root) == kept
    assert not (world.root / lb.CONFIG).parent.exists()


def test_a_command_refuses_where_the_engine_cannot_tell_the_position(world: lb.World) -> None:
    (world.root / lb.DIRECT).write_text("id: [unclosed\n", encoding="utf-8")
    run = world.run("judge", "meal-plan--direct", "desirability", "no", "--person-decided")
    assert run.code == 1
    assert "the process engine cannot tell where `meal-plan--direct` stands" in run.err


# --- the engine itself ------------------------------------------------------------------------


@pytest.mark.process(
    "the commands' end-to-end test: `judge` asks the engine itself, `pkit process`, whose "
    "status, can-move and move each start the desk stage's predicates as processes of their own"
)
def test_judge_moves_the_variant_through_the_engine_itself(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo(capabilities=("lean-business",))
    for script in (repo.root / ".pkit/capabilities/lean-business/scripts").glob("*.py"):
        body = script.read_text(encoding="utf-8").split("\n", 1)[1]
        script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    shutil.copytree(lb.FIXTURE / "lean-business", repo.root / "lean-business")
    repo.git("config", "user.name", lb.PERSON)
    route_pkit(monkeypatch, lb.backbone)
    judged = run_main(
        lb.SCRIPT["judge"],
        "meal-plan--direct",
        "feasibility",
        "no",
        "--note",
        "The first stage's target is out of reach",
        "--person-decided",
        cwd=repo.root,
    )
    assert judged.returncode == 0, judged.stderr
    assert "`meal-plan--direct` moved from shortlisted to viable." in judged.stdout
    canvas = lb.read(repo.root, lb.DIRECT)
    assert "outcome" not in canvas
    assert canvas["verdicts"]["feasibility"]["answer"] == "no"
