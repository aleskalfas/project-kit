"""The experiment's predicates (lean-business DEC-003 points 1, 3 and 7): the classifier that
places an experiment on a day, and the gates on its eight moves, each asked in this process,
on a fixed day, of a copy of the fixture idea with a few things changed.

The fixture's generative experiment, the first interviews, has a time box from 2026-11-03
through 2026-11-16, declared on 2026-11-02 and decided on 2026-11-17. Its evaluative one, the
landing page, runs from 2026-12-12 through 2026-12-25, so its cycle's suspension from
2026-12-20, resumed on 2027-01-03, leaves its dates as they were; its result is recorded on
2027-01-04 and its decision on 2027-01-05. Most tests take the cycle without its review, so
that it is open, and an experiment without its result and decision, so that the dates and
the cycle's suspensions place it.

Each script reads today where it starts and hands it to `classify` or `judge`, so each test
asks those with a day of its own, as the script would on that day. A move the dates or a
suspension recorded late make is the script's, and its gate opens only once the data places
the experiment at its target. The person's moves, declaring and deciding, hold on both sides
of the command's write. A predicate gives no answer (`Unreadable`) where the files cannot
tell; the engine reads no answer as indeterminate."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.in_process import load

(
    positions,
    fingerprint,
    detect,
    declare_declared,
    declare_running,
    start,
    come_due,
    shift_running_declared,
    shift_due_declared,
    shift_due_running,
    decide,
) = load(
    "lean-business",
    "positions",
    "fingerprint",
    "experiment_lifecycle_detect.py",
    "experiment_lifecycle_gate_drafted_declared_declare.py",
    "experiment_lifecycle_gate_drafted_running_declare.py",
    "experiment_lifecycle_gate_declared_running_start.py",
    "experiment_lifecycle_gate_running_due_come_due.py",
    "experiment_lifecycle_gate_running_declared_shift_time_box.py",
    "experiment_lifecycle_gate_due_declared_shift_time_box.py",
    "experiment_lifecycle_gate_due_running_shift_time_box.py",
    "experiment_lifecycle_gate_due_decided_decide.py",
)

FIXTURE = Path(__file__).resolve().parent / "fixtures/lean-business/.repo"

IDEA = "lean-business/meal-plan"
GOAL = f"{IDEA}/goal.yaml"
CYCLE = f"{IDEA}/cycles/first.yaml"
DIRECT = f"{IDEA}/variants/direct/canvas.yaml"
ASSUMPTIONS = f"{IDEA}/variants/direct/assumptions.yaml"
INTERVIEWS = f"{IDEA}/experiments/first-interviews.yaml"
LANDING = f"{IDEA}/experiments/landing-page.yaml"
SUBJECT = "meal-plan--first-interviews"
LANDING_PAGE = "meal-plan--landing-page"

ONE_DAY = timedelta(days=1)
#: The day the first interviews were declared, the day before their time box.
DECLARED_ON = date(2026, 11, 2)
#: The first and last days of the first interviews' time box, and a day within it.
FIRST_DAY = date(2026, 11, 3)
LAST_DAY = date(2026, 11, 16)
WITHIN = date(2026, 11, 10)
#: The day the fixture records the first interviews' result and decision.
DECIDED_ON = date(2026, 11, 17)
#: The landing page's time box, which the cycle's suspension leaves on its dates.
LANDING_FIRST = date(2026, 12, 12)
LANDING_LAST = date(2026, 12, 25)
#: A day the cycle's suspension, from 2026-12-20, covers.
SUSPENDED_ON = date(2026, 12, 22)
#: The days the fixture records the landing page's result and decision, once the cycle resumed.
LANDING_RESULT = date(2027, 1, 4)
LANDING_DECIDED = date(2027, 1, 5)
LONG_AFTER = date(2027, 6, 1)

Change = Callable[[Any], None]
Gate = Callable[[Path, str, date], Any]


# --- the fixture, and changing it ---------------------------------------------------------------


def project(tmp_path: Path) -> Path:
    """A copy of the fixture where the capability is installed, so a predicate run from it
    takes it as the project's root."""
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    (root / ".pkit/capabilities/lean-business").mkdir(parents=True)
    return root


def _yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


def edit(root: Path, rel: str, *changes: Change) -> None:
    """Make each of `changes` to the file `rel`, in order, and write it back."""
    path = root / rel
    data = _yaml().load(path.read_text(encoding="utf-8"))
    for change in changes:
        change(data)
    with path.open("w", encoding="utf-8") as out:
        _yaml().dump(data, out)


def put(*path_and_value: Any) -> Change:
    """A change that sets the last of `path_and_value` at the path the others give."""
    *path, value = path_and_value

    def change(data: Any) -> None:
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return change


def drop(*path: Any) -> Change:
    """A change that removes what lies at `path`."""

    def change(data: Any) -> None:
        node = data
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]

    return change


def refrozen(*changes: Change) -> Change:
    """Each of `changes` made to an experiment, and its declaration's fingerprint taken anew,
    as the command takes it where it records the declaration."""

    def change(data: Any) -> None:
        for each in changes:
            each(data)
        data["declared"]["fingerprint"] = fingerprint.of_declaration(data).as_data()

    return change


#: The experiment before the person decides it: no result, and no decision.
UNDECIDED = (drop("result"), drop("decision"))
#: The experiment before the person declares it: a draft.
DRAFT = (drop("declared"), *UNDECIDED)
#: The cycle's review taken away, so the cycle is open on the experiments' days.
NO_REVIEW = drop("review")
#: The cycle's suspension made ongoing: it records no resumption.
ONGOING = drop("suspensions", 0, "resumed")
#: The first interviews' time box moved to start on a day the cycle's suspension covers, so
#: that the suspension moves it on to 2027-01-03 through 2027-01-16.
LATE_BOX = (put("start", date(2026, 12, 22)), put("end", date(2027, 1, 4)))
MOVED_FIRST = date(2027, 1, 3)
MOVED_LAST = date(2027, 1, 16)


def scene(
    tmp_path: Path, *changes: Change, rel: str = INTERVIEWS, cycle: tuple[Change, ...] = ()
) -> Path:
    """The fixture with its cycle's review taken away and each of `cycle` made to the cycle,
    and each of `changes` made to the experiment at `rel`."""
    root = project(tmp_path)
    edit(root, CYCLE, NO_REVIEW, *cycle)
    if changes:
        edit(root, rel, *changes)
    return root


def suspension(first_day: date, recorded: date, resumed: date | None = None) -> Any:
    """A suspension as the command records it: ongoing, or, where `resumed` is given, an
    absence already over, its resumption recorded on the day it was."""
    entry: dict[str, Any] = {
        "reason": "Away",
        "first-day": first_day,
        "by": "A. Founder",
        "when": recorded,
    }
    if resumed is not None:
        entry["resumed"] = {"day": resumed, "by": "A. Founder", "when": recorded}
    return entry


def stopped(on: date) -> Change:
    """The person's record that the stopping rule was reached on `on`."""
    return put("stopped", {"by": "A. Founder", "when": on})


# --- the predicates, as the scripts ask them ----------------------------------------------------


def position(root: Path, on: date, subject: str = SUBJECT) -> Any:
    """Where the experiment stands on `on`, as `experiment_lifecycle_detect.py` answers."""
    return detect.classify(root, subject, on)


DECLARE_DECLARED: Gate = declare_declared.judge
DECLARE_RUNNING: Gate = declare_running.judge
START: Gate = start.judge
COME_DUE: Gate = come_due.judge
SHIFT_RUNNING_DECLARED: Gate = shift_running_declared.judge
SHIFT_DUE_DECLARED: Gate = shift_due_declared.judge
SHIFT_DUE_RUNNING: Gate = shift_due_running.judge
DECIDE: Gate = decide.judge


def ask(gate: Gate, root: Path, on: date, subject: str = SUBJECT) -> Any:
    return gate(root, subject, on)


def refusal(gate: Gate, root: Path, on: date, subject: str = SUBJECT) -> str:
    """Why `gate` refuses the move on `on`, which it must."""
    answer = ask(gate, root, on, subject)
    assert answer.result is False
    return answer.reason


def untold(gate: Gate, root: Path, on: date, subject: str = SUBJECT) -> str:
    """Why `gate` gives no answer on `on`, which it must."""
    with pytest.raises(positions.Unreadable) as raised:
        ask(gate, root, on, subject)
    return str(raised.value)


#: How a time box falls where its cycle's suspensions moved it.
MOVED = ", as its cycle's suspensions move it"


def declared_reason(on: date, first: date = FIRST_DAY, moved: str = "") -> str:
    """Why a declared experiment whose time box starts on `first` stands declared on `on`."""
    return (
        f"its declaration is recorded, and its time box starts on {first}{moved}, after today, {on}"
    )


def running_reason(
    on: date, first: date = FIRST_DAY, last: date = LAST_DAY, moved: str = ""
) -> str:
    """Why an experiment whose time box runs from `first` through `last` stands running on
    `on`."""
    return f"its time box runs from {first} through {last}{moved}, and holds today, {on}"


def due_reason(on: date, last: date = LAST_DAY, moved: str = "") -> str:
    """Why an experiment whose time box ended on `last` stands due on `on`."""
    return f"its time box ended on {last}{moved}, before today, {on}, and no decision is recorded"


DECIDED_REASON = (
    "the person decided its next action on 2026-11-17, to double down, which outranks its dates"
)
DRAFTED_REASON = "a file exists, and its declaration is not recorded"
NO_START = (
    "its declaration is recorded, and an ongoing suspension of its cycle reached its time box "
    "before it started, so it has no start until the cycle resumes"
)
STRAY_STOP = (
    "; the stopping rule it records ends nothing, since an evaluative experiment runs its whole "
    "time box"
)
CYCLE_SUSPENDED = (
    "a suspension from 2026-12-20 is ongoing, with no day of resuming, which outranks the "
    "cycle's dates: none of its days count toward the window"
)


# --- the classifier -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "on"),
    [
        ((), DECLARED_ON),
        ((), WITHIN),
        ((), DECIDED_ON),
        ((drop("declared"),), DECIDED_ON),
    ],
    ids=["before-its-time-box", "within-it", "after-it", "without-its-declaration"],
)
def test_a_decision_places_the_experiment_whatever_else_it_holds(
    tmp_path: Path, changes: tuple[Change, ...], on: date
) -> None:
    root = project(tmp_path)
    if changes:
        edit(root, INTERVIEWS, *changes)
    assert position(root, on) == positions.Position(positions.DECIDED, DECIDED_REASON)


@pytest.mark.parametrize(
    ("changes", "on"),
    [
        ((), DECLARED_ON),
        ((), LONG_AFTER),
        ((stopped(WITHIN),), WITHIN),
    ],
    ids=["before-its-time-box", "long-after-it", "with-a-stopping-rule-reached"],
)
def test_without_its_declaration_it_stands_drafted_whatever_its_dates_say(
    tmp_path: Path, changes: tuple[Change, ...], on: date
) -> None:
    root = scene(tmp_path, *DRAFT, *changes)
    assert position(root, on) == positions.Position(positions.DRAFTED, DRAFTED_REASON)


@pytest.mark.parametrize(
    ("on", "state", "reason"),
    [
        (DECLARED_ON, "declared", declared_reason(DECLARED_ON)),
        (FIRST_DAY, "running", running_reason(FIRST_DAY)),
        (LAST_DAY, "running", running_reason(LAST_DAY)),
        (DECIDED_ON, "due", due_reason(DECIDED_ON)),
    ],
    ids=["the-day-before-its-time-box", "its-first-day", "its-last-day", "the-day-after"],
)
def test_without_a_decision_its_time_box_places_it(
    tmp_path: Path, on: date, state: str, reason: str
) -> None:
    """The cycle's suspension, from 2026-12-20, began after this time box ended, so it moves
    nothing, and the reason says nothing of it."""
    root = scene(tmp_path, *UNDECIDED)
    assert position(root, on) == positions.Position(state, reason)


@pytest.mark.parametrize(
    ("on", "state", "reason"),
    [
        (
            MOVED_FIRST - ONE_DAY,
            "declared",
            declared_reason(MOVED_FIRST - ONE_DAY, MOVED_FIRST, MOVED),
        ),
        (MOVED_FIRST, "running", running_reason(MOVED_FIRST, MOVED_FIRST, MOVED_LAST, MOVED)),
        (MOVED_LAST, "running", running_reason(MOVED_LAST, MOVED_FIRST, MOVED_LAST, MOVED)),
        (MOVED_LAST + ONE_DAY, "due", due_reason(MOVED_LAST + ONE_DAY, MOVED_LAST, MOVED)),
    ],
    ids=[
        "the-day-before-it-as-moved",
        "its-first-day-as-moved",
        "its-last-day-as-moved",
        "the-day-after",
    ],
)
def test_a_suspension_that_covered_its_start_moves_its_time_box_later(
    tmp_path: Path, on: date, state: str, reason: str
) -> None:
    """Declared from 2026-12-22, a day the suspension from 2026-12-20 covers, the time box
    starts on 2027-01-03, the day the cycle resumed, and keeps its fourteen days."""
    root = scene(tmp_path, *UNDECIDED, *LATE_BOX)
    assert position(root, on) == positions.Position(state, reason)


def test_an_ongoing_suspension_that_reached_its_start_leaves_it_declared(tmp_path: Path) -> None:
    root = scene(tmp_path, *UNDECIDED, *LATE_BOX, cycle=(ONGOING,))
    assert position(root, LONG_AFTER) == positions.Position(positions.DECLARED, NO_START)


@pytest.mark.parametrize(
    ("on", "state", "reason"),
    [
        (SUSPENDED_ON, "running", running_reason(SUSPENDED_ON, LANDING_FIRST, LANDING_LAST)),
        (LANDING_LAST + ONE_DAY, "due", due_reason(LANDING_LAST + ONE_DAY, LANDING_LAST)),
    ],
    ids=["while-its-cycle-is-suspended", "once-its-end-passed"],
)
def test_a_time_box_already_started_keeps_its_dates_while_its_cycle_is_suspended(
    tmp_path: Path, on: date, state: str, reason: str
) -> None:
    root = scene(tmp_path, *UNDECIDED, rel=LANDING, cycle=(ONGOING,))
    assert position(root, on, LANDING_PAGE) == positions.Position(state, reason)


@pytest.mark.parametrize("on", [DECLARED_ON, WITHIN], ids=["before-its-time-box", "within-it"])
def test_a_stopping_rule_reached_makes_a_generative_experiment_due_whatever_its_dates_say(
    tmp_path: Path, on: date
) -> None:
    root = scene(tmp_path, *UNDECIDED, stopped(WITHIN))
    assert position(root, on) == positions.Position(
        positions.DUE,
        "the person recorded its stopping rule reached on 2026-11-10, which makes a generative "
        "experiment due whatever its dates say, and no decision is recorded",
    )


@pytest.mark.parametrize(
    ("on", "state", "reason"),
    [
        (
            date(2026, 12, 15),
            "running",
            running_reason(date(2026, 12, 15), LANDING_FIRST, LANDING_LAST),
        ),
        (LANDING_LAST + ONE_DAY, "due", due_reason(LANDING_LAST + ONE_DAY, LANDING_LAST)),
    ],
    ids=["within-its-time-box", "after-it"],
)
def test_an_evaluative_experiment_runs_its_whole_time_box_whatever_its_stopping_rule_says(
    tmp_path: Path, on: date, state: str, reason: str
) -> None:
    root = scene(tmp_path, *UNDECIDED, stopped(date(2026, 12, 15)), rel=LANDING)
    assert position(root, on, LANDING_PAGE) == positions.Position(state, f"{reason}{STRAY_STOP}")


@pytest.mark.parametrize(
    ("change", "why"),
    [
        (drop("cycle"), ", as declared, since it names no cycle whose suspensions could move it"),
        (
            put("cycle", "[cycle:meal-plan--second]"),
            ", as declared, since no file of the cycle it names lies in its place, so no "
            "suspension moves it",
        ),
    ],
    ids=["it-names-no-cycle", "its-cycle-has-no-file"],
)
def test_where_no_cycle_s_suspensions_can_move_it_its_time_box_falls_as_declared(
    tmp_path: Path, change: Change, why: str
) -> None:
    """Declared from 2026-12-22, the time box would move were the cycle's suspensions read."""
    root = scene(tmp_path, *UNDECIDED, *LATE_BOX, change)
    on = date(2026, 12, 22)
    assert position(root, on) == positions.Position(
        positions.RUNNING, running_reason(on, on, date(2027, 1, 4), why)
    )


def test_an_experiment_without_its_file_stands_nowhere_and_no_move_is_open(tmp_path: Path) -> None:
    root = project(tmp_path)
    third = "meal-plan--third"
    absent = f"no experiment's file lies at `{IDEA}/experiments/third.yaml`"
    assert position(root, DECIDED_ON, third) == positions.Position(
        None,
        f"`{third}` stands in none of the experiment's states, which start with its file: {absent}",
    )
    for gate in (DECLARE_DECLARED, START, DECIDE):
        assert refusal(gate, root, DECIDED_ON, third) == (
            f"no move of the experiment is open to `{third}`, which stands in none of its states "
            f"without its file: {absent}"
        )


def unread(rel: str) -> Callable[[Path], None]:
    """What makes the file `rel` no YAML, for the project a test is given later."""

    def change(root: Path) -> None:
        (root / rel).write_text("id: [unclosed\n", encoding="utf-8")

    return change


def editing(rel: str, *changes: Change) -> Callable[[Path], None]:
    """What `edit` does to the file `rel`, for the project a test is given later."""
    return lambda root: edit(root, rel, *changes)


def undecided_and(change: Callable[[Path], None]) -> Callable[[Path], None]:
    """`change`, made where the first interviews are undecided: a decision outranks the rest,
    so the classifier reads their cycle only then."""

    def both(root: Path) -> None:
        edit(root, INTERVIEWS, *UNDECIDED)
        change(root)

    return both


def test_a_decided_experiment_stands_decided_whatever_its_cycle_s_file_holds(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    unread(CYCLE)(root)
    assert position(root, DECIDED_ON) == positions.Position(positions.DECIDED, DECIDED_REASON)


@pytest.mark.parametrize(
    ("change", "why"),
    [
        (
            unread(INTERVIEWS),
            f"the experiment's file at `{INTERVIEWS}` cannot be read: it does not parse as YAML",
        ),
        (
            editing(INTERVIEWS, put("decision", "next", "abandon")),
            "records a decision whose next action is none of correct-course, double-down and stop",
        ),
        (
            editing(INTERVIEWS, put("decision", "double-down")),
            "records a decision whose next action is none of correct-course, double-down and stop",
        ),
        (
            editing(INTERVIEWS, *UNDECIDED, put("declared", "yes")),
            "records its declaration as something other than one",
        ),
        (
            editing(INTERVIEWS, *UNDECIDED, put("kind", "exploratory"), stopped(WITHIN)),
            "records its stopping rule reached, and its kind is neither generative nor evaluative",
        ),
        (
            editing(INTERVIEWS, *UNDECIDED, put("stopped", "yes")),
            "records its stopping rule reached as something other than one",
        ),
        (
            editing(INTERVIEWS, *UNDECIDED, put("start", "soon")),
            "declares no time box that reads as one, its first day and its last",
        ),
        (
            editing(INTERVIEWS, *UNDECIDED, put("cycle", "first")),
            "its `cycle` is no reference to a cycle, `[cycle:<idea>--<cycle>]`, so whose "
            "suspensions move its time box cannot be told",
        ),
        (
            editing(INTERVIEWS, *UNDECIDED, put("cycle", "[cycle:salad--first]")),
            "it names `salad--first`, a cycle of another idea, which an idea never names, so "
            "whose suspensions move its time box cannot be told",
        ),
        (
            undecided_and(unread(CYCLE)),
            f"the cycle's file at `{CYCLE}` cannot be read: it does not parse as YAML",
        ),
        (
            undecided_and(editing(CYCLE, put("suspensions", 0, "resumed", "day", "soon"))),
            f"the suspension at place 1 of `{CYCLE}` has no day of resuming that reads as a day",
        ),
        (
            undecided_and(editing(CYCLE, put("suspensions", "soon"))),
            f"the cycle's file at `{CYCLE}` keeps its suspensions as something other than a list",
        ),
    ],
    ids=[
        "a-file-no-yaml",
        "a-next-action-of-none",
        "a-decision-no-mapping",
        "a-declaration-no-mapping",
        "a-stopping-rule-on-a-kind-of-neither",
        "a-stopping-rule-no-mapping",
        "a-time-box-no-day",
        "a-cycle-no-reference",
        "a-cycle-of-another-idea",
        "a-cycle-file-no-yaml",
        "a-resumption-no-day",
        "suspensions-no-list",
    ],
)
def test_where_the_files_cannot_tell_where_it_stands_there_is_no_answer(
    tmp_path: Path, change: Callable[[Path], None], why: str
) -> None:
    root = project(tmp_path)
    change(root)
    with pytest.raises(positions.Unreadable) as raised:
        position(root, DECIDED_ON)
    assert why in str(raised.value)


def test_a_subject_that_is_no_experiment_s_id_has_no_answer(tmp_path: Path) -> None:
    root = project(tmp_path)
    no_id = "`Meal_Plan` is no experiment's id"
    with pytest.raises(positions.Unreadable, match=no_id):
        position(root, DECIDED_ON, "Meal_Plan")
    with pytest.raises(positions.Unreadable, match=no_id):
        ask(START, root, DECIDED_ON, "Meal_Plan")


# --- the moves the dates make -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "first", "last", "moved"),
    [((), FIRST_DAY, LAST_DAY, ""), (LATE_BOX, MOVED_FIRST, MOVED_LAST, MOVED)],
    ids=["as-declared", "as-its-cycle-s-suspension-moved-it"],
)
def test_the_start_opens_on_the_time_box_s_first_day(
    tmp_path: Path, changes: tuple[Change, ...], first: date, last: date, moved: str
) -> None:
    root = scene(tmp_path, *UNDECIDED, *changes)
    before = first - ONE_DAY
    assert refusal(START, root, before) == (
        f"the experiment stands declared, not running: {declared_reason(before, first, moved)}"
    )
    assert ask(START, root, first) == positions.Answer(
        True,
        f"the experiment's time box has started: {running_reason(first, first, last, moved)}",
    )


def test_coming_due_opens_the_day_after_the_time_box_s_last(tmp_path: Path) -> None:
    root = scene(tmp_path, *UNDECIDED)
    assert refusal(COME_DUE, root, LAST_DAY) == (
        f"the experiment stands running, not due: {running_reason(LAST_DAY)}"
    )
    assert ask(COME_DUE, root, DECIDED_ON) == positions.Answer(
        True, f"the experiment's time box has ended: {due_reason(DECIDED_ON)}"
    )


def test_a_stopping_rule_reached_brings_a_generative_experiment_due_once_recorded(
    tmp_path: Path,
) -> None:
    """Before the person records the stopping rule reached, the experiment runs, so the gate
    is closed; after, it opens on the record, which keeps its rules."""
    root = scene(tmp_path, *UNDECIDED)
    assert refusal(COME_DUE, root, WITHIN) == (
        f"the experiment stands running, not due: {running_reason(WITHIN)}"
    )
    edit(root, INTERVIEWS, stopped(WITHIN))
    assert ask(COME_DUE, root, WITHIN) == positions.Answer(
        True,
        "the person recorded its stopping rule reached, within its time box, 2026-11-03 through "
        "2026-11-16, which ends a generative experiment early: the person recorded its stopping "
        "rule reached on 2026-11-10, which makes a generative experiment due whatever its dates "
        "say, and no decision is recorded",
    )


#: The first interviews' time box moved to 2026-12-14 through 2026-12-27, which had started by
#: the suspension's first day, 2026-12-20, so the suspension leaves it on its dates.
STARTED_BEFORE_THE_SUSPENSION = (put("start", date(2026, 12, 14)), put("end", date(2026, 12, 27)))


@pytest.mark.parametrize(
    ("changes", "cycle", "on", "why"),
    [
        (
            (stopped(DECLARED_ON),),
            (),
            DECLARED_ON,
            "its stopping rule was reached on 2026-11-02, before its time box started, as its "
            "cycle's suspensions work it out: 2026-11-03 through 2026-11-16",
        ),
        (
            (put("stopped", {"by": "A. Founder"}),),
            (),
            WITHIN,
            "its stopping rule records no day it was reached, so its rules cannot be asked of it",
        ),
        (
            (*STARTED_BEFORE_THE_SUSPENSION, stopped(SUSPENDED_ON)),
            (ONGOING,),
            SUSPENDED_ON,
            "its stopping rule was recorded on 2026-12-22, a day the suspension of its cycle from "
            "2026-12-20, ongoing covers: nothing is recorded on a suspended cycle's experiments "
            "until the person resumes it",
        ),
    ],
    ids=["before-its-time-box", "on-no-day", "while-its-cycle-is-suspended"],
)
def test_a_stopping_rule_its_rules_refuse_brings_nothing_due(
    tmp_path: Path, changes: tuple[Change, ...], cycle: tuple[Change, ...], on: date, why: str
) -> None:
    """The detection places the experiment due on the record alone; the gate holds the record
    to its rules."""
    root = scene(tmp_path, *UNDECIDED, *changes, cycle=cycle)
    assert position(root, on).state == positions.DUE
    assert refusal(COME_DUE, root, on) == why


@pytest.mark.parametrize(
    ("gate", "target"),
    [
        (START, "running"),
        (COME_DUE, "due"),
        (SHIFT_RUNNING_DECLARED, "declared"),
        (SHIFT_DUE_DECLARED, "declared"),
        (SHIFT_DUE_RUNNING, "running"),
    ],
    ids=["start", "come-due", "shift-running-declared", "shift-due-declared", "shift-due-running"],
)
def test_no_date_and_no_suspension_moves_a_decided_experiment(
    tmp_path: Path, gate: Gate, target: str
) -> None:
    root = scene(tmp_path)
    assert refusal(gate, root, LONG_AFTER) == (
        f"the experiment stands decided, not {target}: {DECIDED_REASON}"
    )


# --- shifting the time box ----------------------------------------------------------------------

#: The day a suspension is recorded late, after the first interviews' time box ended.
RECORDED_LATE = date(2026, 11, 20)
#: An absence from 2026-11-03 until 2026-11-10, recorded once it was over: it covered the
#: first interviews' first day, so their time box starts on 2026-11-10 and ends 2026-11-23.
LATE_ABSENCE = suspension(FIRST_DAY, RECORDED_LATE, WITHIN)
SHIFTED_LAST = date(2026, 11, 23)


def test_an_absence_already_over_recorded_late_makes_a_due_experiment_run_again(
    tmp_path: Path,
) -> None:
    root = scene(tmp_path, *UNDECIDED, cycle=(drop("suspensions"),))
    before = due_reason(RECORDED_LATE)
    assert position(root, RECORDED_LATE) == positions.Position(positions.DUE, before)
    assert refusal(SHIFT_DUE_RUNNING, root, RECORDED_LATE) == (
        f"the experiment stands due, not running: {before}"
    )
    edit(root, CYCLE, put("suspensions", [LATE_ABSENCE]))
    after = running_reason(RECORDED_LATE, WITHIN, SHIFTED_LAST, MOVED)
    assert position(root, RECORDED_LATE) == positions.Position(positions.RUNNING, after)
    assert ask(SHIFT_DUE_RUNNING, root, RECORDED_LATE) == positions.Answer(
        True,
        "the suspension of its cycle recorded last, from 2026-11-03 until 2026-11-10, moved its "
        "time box from 2026-11-03 through 2026-11-16 to 2026-11-10 through 2026-11-23, and keeps "
        f"its rules: {after}",
    )
    for gate in (SHIFT_RUNNING_DECLARED, SHIFT_DUE_DECLARED):
        assert refusal(gate, root, RECORDED_LATE) == (
            f"the experiment stands running, not declared: {after}"
        )


@pytest.mark.parametrize(
    ("gate", "on", "origin", "before"),
    [
        (SHIFT_RUNNING_DECLARED, date(2026, 11, 5), "running", running_reason(date(2026, 11, 5))),
        (SHIFT_DUE_DECLARED, RECORDED_LATE, "due", due_reason(RECORDED_LATE)),
    ],
    ids=["from-running", "from-due"],
)
def test_an_ongoing_suspension_recorded_late_takes_the_experiment_back_to_declared(
    tmp_path: Path, gate: Gate, on: date, origin: str, before: str
) -> None:
    """A suspension from 2026-11-03, the first interviews' first day, recorded on `on` and
    not resumed, leaves their time box no start. The landing page is a draft here, since the
    ongoing suspension would cover the days its acts were recorded on."""
    root = scene(tmp_path, *UNDECIDED, cycle=(drop("suspensions"),))
    edit(root, LANDING, *DRAFT)
    assert refusal(gate, root, on) == f"the experiment stands {origin}, not declared: {before}"
    edit(root, CYCLE, put("suspensions", [suspension(FIRST_DAY, on)]))
    assert position(root, on) == positions.Position(positions.DECLARED, NO_START)
    assert ask(gate, root, on) == positions.Answer(
        True,
        "the suspension of its cycle recorded last, from 2026-11-03, ongoing, moved its time box "
        f"from 2026-11-03 through 2026-11-16 to not started yet, and keeps its rules: {NO_START}",
    )


def test_a_suspension_that_began_after_the_time_box_started_brings_no_move_back(
    tmp_path: Path,
) -> None:
    root = scene(tmp_path, *UNDECIDED, rel=LANDING, cycle=(ONGOING,))
    running = running_reason(SUSPENDED_ON, LANDING_FIRST, LANDING_LAST)
    assert refusal(SHIFT_DUE_RUNNING, root, SUSPENDED_ON, LANDING_PAGE) == (
        "the suspension of its cycle recorded last, from 2026-12-20, ongoing, leaves its time box "
        "where it fell, 2026-12-12 through 2026-12-25: only a suspension recorded late, covering "
        f"the start of its time box, moves an experiment back: {running}"
    )


ONLY_A_LATE_SUSPENSION = (
    "only a suspension recorded late, covering the start of its time box, moves an experiment back"
)


@pytest.mark.parametrize(
    ("changes", "cycle", "why"),
    [
        (
            (),
            (drop("suspensions"),),
            "no suspension of its cycle, `meal-plan--first`, is recorded: "
            f"{ONLY_A_LATE_SUSPENSION}: {running_reason(WITHIN)}",
        ),
        (
            (drop("cycle"),),
            (),
            f"no suspension moves its time box, since it names no cycle: {ONLY_A_LATE_SUSPENSION}",
        ),
        (
            (put("cycle", "[cycle:meal-plan--second]"),),
            (),
            "no suspension moves its time box, since no cycle's file lies at "
            f"`{IDEA}/cycles/second.yaml`: {ONLY_A_LATE_SUSPENSION}",
        ),
    ],
    ids=["none-is-recorded", "it-names-no-cycle", "its-cycle-has-no-file"],
)
def test_only_a_suspension_of_its_cycle_shifts_the_time_box(
    tmp_path: Path, changes: tuple[Change, ...], cycle: tuple[Change, ...], why: str
) -> None:
    root = scene(tmp_path, *UNDECIDED, *changes, cycle=cycle)
    assert position(root, WITHIN).state == positions.RUNNING
    assert refusal(SHIFT_DUE_RUNNING, root, WITHIN) == why


def test_a_late_suspension_that_breaks_its_rules_moves_nothing_back(tmp_path: Path) -> None:
    """An absence from 2026-11-02, the day the experiment was declared, until 2026-11-10."""
    root = scene(
        tmp_path,
        *UNDECIDED,
        cycle=(put("suspensions", [suspension(DECLARED_ON, RECORDED_LATE, WITHIN)]),),
    )
    assert position(root, RECORDED_LATE).state == positions.RUNNING
    assert refusal(SHIFT_DUE_RUNNING, root, RECORDED_LATE) == (
        "the suspension at place 1 breaks its rules: it covers 2026-11-02, which holds the "
        "declaration of `meal-plan--first-interviews`"
    )


def test_where_what_a_suspension_s_rules_weigh_cannot_be_read_there_is_no_answer(
    tmp_path: Path,
) -> None:
    root = scene(tmp_path, *UNDECIDED, cycle=(put("suspensions", [LATE_ABSENCE]),))
    unread(LANDING)(root)
    assert untold(SHIFT_DUE_RUNNING, root, RECORDED_LATE) == (
        f"`{LANDING}` cannot be read, and a suspension's rules weigh them: so whether the move "
        f"may happen cannot be told"
    )


# --- declaring ----------------------------------------------------------------------------------


def may_declare(into: str, cycle_stands: str) -> str:
    """Why the first interviews, drafted, may be declared `into`, their cycle standing
    `cycle_stands`."""
    return (
        f"the experiment may be declared, {into}: it records every field its kind, generative, "
        f"needs, at least one estimate, and a time box of 14 days, 2026-11-03 through 2026-11-16; "
        f"it tests an assumption of `meal-plan--direct`, whose shortlisting stands and is not "
        f"stale; and its cycle, `meal-plan--first`, stands {cycle_stands}, and explores the "
        f"variant"
    )


INTO_DECLARED = "into declared"
INTO_RUNNING = "its time box starting today"


@pytest.mark.parametrize(
    ("on", "cycle_stands"),
    [(date(2026, 10, 31), "planned"), (DECLARED_ON, "running")],
    ids=["its-cycle-planned", "its-cycle-running"],
)
def test_a_draft_whose_time_box_starts_later_is_declared_into_declared(
    tmp_path: Path, on: date, cycle_stands: str
) -> None:
    root = scene(tmp_path, *DRAFT)
    assert ask(DECLARE_DECLARED, root, on) == positions.Answer(
        True, may_declare(INTO_DECLARED, cycle_stands)
    )
    assert refusal(DECLARE_RUNNING, root, on) == (
        f"its time box starts on 2026-11-03, after today, {on}, so declaring it moves it into "
        f"declared, not straight into running"
    )


def test_a_draft_whose_time_box_starts_today_is_declared_straight_into_running(
    tmp_path: Path,
) -> None:
    root = scene(tmp_path, *DRAFT)
    assert ask(DECLARE_RUNNING, root, FIRST_DAY) == positions.Answer(
        True, may_declare(INTO_RUNNING, "running")
    )
    assert refusal(DECLARE_DECLARED, root, FIRST_DAY) == (
        "its time box starts today, 2026-11-03, so declaring it moves it straight into running, "
        "not into declared"
    )


@pytest.mark.parametrize("gate", [DECLARE_DECLARED, DECLARE_RUNNING], ids=["declared", "running"])
def test_a_draft_whose_time_box_started_before_today_is_declared_into_neither(
    tmp_path: Path, gate: Gate
) -> None:
    root = scene(tmp_path, *DRAFT)
    on = FIRST_DAY + ONE_DAY
    assert refusal(gate, root, on) == (
        f"its time box starts on 2026-11-03, before the day it was declared, {on}"
    )


@pytest.mark.parametrize(
    ("changes", "why"),
    [
        (
            (drop("estimates"),),
            "it was declared without an estimate, made alone before the declaration",
        ),
        ((drop("learn"),), "it was declared without `learn`, which a generative declaration needs"),
        (
            (drop("assumption"),),
            "it was declared without `assumption`, which a generative declaration needs",
        ),
        ((drop("cycle"),), "it was declared without `cycle`, which a generative declaration needs"),
        (
            (drop("kind"),),
            "a declaration needs its kind, generative or evaluative, which says what else it needs",
        ),
        ((put("end", DECIDED_ON),), "its time box holds 15 days, more than 14"),
        (
            (put("start", "soon"),),
            "its `start` does not read as a day, `YYYY-MM-DD`, and a time box is given by its "
            "first day and its last",
        ),
    ],
    ids=[
        "no-estimate",
        "no-field-its-kind-needs",
        "no-assumption",
        "no-cycle",
        "no-kind",
        "a-time-box-too-long",
        "a-start-no-day",
    ],
)
def test_a_draft_that_lacks_what_a_declaration_needs_is_not_declared(
    tmp_path: Path, changes: tuple[Change, ...], why: str
) -> None:
    root = scene(tmp_path, *DRAFT, *changes)
    assert refusal(DECLARE_DECLARED, root, DECLARED_ON) == why


SHELVED_BECAUSE = "Too few households cook every evening"


@pytest.mark.parametrize(
    ("rel", "changes", "why"),
    [
        (
            DIRECT,
            (drop("outcome"),),
            "it tests an assumption of `meal-plan--direct`, which stands feasible, not "
            "shortlisted: an experiment is declared only on a shortlisted variant (the person's "
            "yes stands on desirability, viability and feasibility, and the variant has no "
            "outcome yet)",
        ),
        (
            DIRECT,
            (put("outcome", "kind", "shelved"), put("outcome", "reason", SHELVED_BECAUSE)),
            "it tests an assumption of `meal-plan--direct`, which stands shelved, not "
            "shortlisted: an experiment is declared only on a shortlisted variant (the person "
            f"shelved the variant on 2026-10-08: {SHELVED_BECAUSE})",
        ),
        (
            DIRECT,
            (put("boxes", "problem", 0, "text", "Planning the week takes an evening"),),
            "the shortlisting of `meal-plan--direct` is stale: the canvas or the goal changed "
            "since, so the variant is judged and shortlisted again first",
        ),
        (
            GOAL,
            (put("revenue", "amount", 2000000),),
            "the shortlisting of `meal-plan--direct` is stale: the canvas or the goal changed "
            "since, so the variant is judged and shortlisted again first",
        ),
        (
            INTERVIEWS,
            (put("assumption", "[assumptions:meal-plan--direct--no-such]"),),
            "it tests `meal-plan--direct--no-such`, which no list of the variant's assumptions "
            "holds",
        ),
        (
            INTERVIEWS,
            (put("assumption", "planning-takes-long"),),
            "its `assumption` is no reference to an assumption, "
            "`[assumptions:<idea>--<variant>--<assumption>]`",
        ),
        (
            INTERVIEWS,
            (put("assumption", "[assumptions:salad--direct--cheap]"),),
            "it tests `salad--direct--cheap`, an assumption of another idea, which an idea never "
            "names; it tests an assumption of `salad--direct`, which its cycle, "
            "`meal-plan--first`, does not explore",
        ),
        (
            INTERVIEWS,
            (put("assumption", "[assumptions:meal-plan--solo--cheap]"),),
            "it tests `meal-plan--solo--cheap`, which no list of the variant's assumptions holds; "
            "it tests an assumption of `meal-plan--solo`, which stands nowhere, not shortlisted: "
            "an experiment is declared only on a shortlisted variant (`meal-plan--solo` stands in "
            "none of the desk stage's states, which start with a canvas: no canvas lies at "
            f"`{IDEA}/variants/solo/canvas.yaml`); it tests an assumption of `meal-plan--solo`, "
            "which its cycle, `meal-plan--first`, does not explore",
        ),
    ],
    ids=[
        "a-variant-not-shortlisted",
        "a-variant-shelved",
        "a-shortlisting-stale-by-its-canvas",
        "a-shortlisting-stale-by-the-goal",
        "an-assumption-no-list-holds",
        "an-assumption-no-reference",
        "an-assumption-of-another-idea",
        "an-assumption-of-a-variant-with-no-canvas",
    ],
)
def test_a_declaration_needs_an_assumption_of_a_variant_whose_shortlisting_stands(
    tmp_path: Path, rel: str, changes: tuple[Change, ...], why: str
) -> None:
    root = scene(tmp_path, *DRAFT)
    edit(root, rel, *changes)
    assert refusal(DECLARE_DECLARED, root, DECLARED_ON) == why


#: A time box that starts the day after the cycle's window ended, as its suspension moved it.
AFTER_THE_WINDOW = (put("start", date(2027, 2, 14)), put("end", date(2027, 2, 27)))


@pytest.mark.parametrize(
    ("changes", "cycle", "on", "why"),
    [
        (
            (),
            (ONGOING,),
            DECLARED_ON,
            "its cycle, `meal-plan--first`, stands suspended: an experiment is declared only in "
            f"an open cycle, planned or running ({CYCLE_SUSPENDED})",
        ),
        (
            AFTER_THE_WINDOW,
            (),
            date(2027, 2, 13),
            "its cycle, `meal-plan--first`, stands in review: an experiment is declared only in "
            "an open cycle, planned or running (its window ended on 2027-02-12, as its "
            "suspensions work it out, before today, 2027-02-13, and no decision is recorded)",
        ),
        (
            (),
            (put("variants", ["[canvas:meal-plan--two-sided]"]),),
            DECLARED_ON,
            "it tests an assumption of `meal-plan--direct`, which its cycle, `meal-plan--first`, "
            "does not explore",
        ),
        (
            (put("cycle", "[cycle:meal-plan--second]"),),
            (),
            DECLARED_ON,
            "it names the cycle `meal-plan--second`, and no cycle's file lies at "
            f"`{IDEA}/cycles/second.yaml`: an experiment is declared only in an open cycle",
        ),
        (
            (put("cycle", "first"),),
            (),
            DECLARED_ON,
            "its `cycle` is no reference to a cycle, `[cycle:<idea>--<cycle>]`: an experiment is "
            "declared only in an open cycle",
        ),
        (
            (put("cycle", "[cycle:salad--first]"),),
            (),
            DECLARED_ON,
            "it names `salad--first`, a cycle of another idea, which an idea never names: an "
            "experiment is declared only in an open cycle",
        ),
    ],
    ids=[
        "suspended",
        "in-review",
        "not-exploring-its-variant",
        "no-file",
        "no-reference",
        "of-another-idea",
    ],
)
def test_a_declaration_needs_an_open_cycle_that_explores_its_variant(
    tmp_path: Path, changes: tuple[Change, ...], cycle: tuple[Change, ...], on: date, why: str
) -> None:
    root = scene(tmp_path, *DRAFT, *changes, cycle=cycle)
    assert refusal(DECLARE_DECLARED, root, on) == why


def test_no_experiment_is_declared_in_a_decided_cycle(tmp_path: Path) -> None:
    """The fixture's cycle records its review, which places it decided whatever its dates."""
    root = project(tmp_path)
    edit(root, INTERVIEWS, *DRAFT)
    assert refusal(DECLARE_DECLARED, root, DECLARED_ON) == (
        "its cycle, `meal-plan--first`, stands decided: an experiment is declared only in an open "
        "cycle, planned or running (the person decided to persevere for `meal-plan--direct` on "
        "2027-02-15, which outranks its suspensions and its dates)"
    )


def test_a_declaration_recorded_holds_where_the_detection_places_the_experiment(
    tmp_path: Path,
) -> None:
    """After the command writes, the gate on each move of `declare` opens only where the
    detection places the experiment at that move's target."""
    root = scene(tmp_path, *UNDECIDED)
    declared = declared_reason(DECLARED_ON)
    assert ask(DECLARE_DECLARED, root, DECLARED_ON) == positions.Answer(
        True,
        "the declaration recorded on 2026-11-02 passes its gate as the check asks it, resting on "
        "the shortlisting of `meal-plan--direct` recorded on 2026-10-08, which still stands, not "
        "stale, in the open cycle `meal-plan--first`, which explores it: "
        f"{declared}",
    )
    assert refusal(DECLARE_RUNNING, root, DECLARED_ON) == (
        f"the experiment stands declared, not running: {declared}"
    )
    root = scene(
        tmp_path / "on-its-first-day", *UNDECIDED, refrozen(put("declared", "when", FIRST_DAY))
    )
    running = running_reason(FIRST_DAY)
    assert ask(DECLARE_RUNNING, root, FIRST_DAY) == positions.Answer(
        True,
        "the declaration recorded on 2026-11-03 passes its gate as the check asks it, resting on "
        "the shortlisting of `meal-plan--direct` recorded on 2026-10-08, which still stands, not "
        "stale, in the open cycle `meal-plan--first`, which explores it: "
        f"{running}",
    )
    assert refusal(DECLARE_DECLARED, root, FIRST_DAY) == (
        f"the experiment stands running, not declared: {running}"
    )


@pytest.mark.parametrize(
    ("changes", "gate", "on", "why"),
    [
        (
            (put("learn", "Whether planning is a burden"),),
            DECLARE_DECLARED,
            DECLARED_ON,
            "a declared field, or the record of the declaration, changed since it was declared: "
            "a declaration is frozen, so a correction comes as a new experiment",
        ),
        (
            (put("declared", "fingerprint", "none"),),
            DECLARE_DECLARED,
            DECLARED_ON,
            "the declaration keeps no fingerprint that reads as one, which freezes what it "
            "declared",
        ),
        (
            (refrozen(drop("declared", "by")),),
            DECLARE_DECLARED,
            DECLARED_ON,
            "the declaration does not say who declared it",
        ),
        (
            (refrozen(drop("declared", "when")),),
            DECLARE_DECLARED,
            DECLARED_ON,
            "the declaration records no day it was declared, so its gate cannot be asked of it",
        ),
        (
            (refrozen(put("declared", "when", FIRST_DAY + ONE_DAY)),),
            DECLARE_RUNNING,
            FIRST_DAY + ONE_DAY,
            "its time box starts on 2026-11-03, before the day it was declared, 2026-11-04",
        ),
        (
            (refrozen(put("declared", "rested-on", "when", date(2026, 11, 5))),),
            DECLARE_DECLARED,
            DECLARED_ON,
            "it rests on a shortlisting of `meal-plan--direct` recorded on 2026-11-05, after the "
            "day it was declared, 2026-11-02",
        ),
    ],
    ids=[
        "a-declared-field-changed",
        "no-fingerprint",
        "no-one-declared-it",
        "on-no-day",
        "after-its-time-box-started",
        "on-a-later-shortlisting",
    ],
)
def test_a_declaration_recorded_that_its_gate_refuses_moves_nothing(
    tmp_path: Path, changes: tuple[Change, ...], gate: Gate, on: date, why: str
) -> None:
    root = scene(tmp_path, *UNDECIDED, *changes)
    assert refusal(gate, root, on) == why


@pytest.mark.parametrize(
    ("change", "why"),
    [
        (
            unread(GOAL),
            f"the idea's goal at `{GOAL}` cannot be read, and the shortlisting of "
            "`meal-plan--direct` covers it, so whether it is stale cannot be told",
        ),
        (
            unread(ASSUMPTIONS),
            f"the assumptions at `{ASSUMPTIONS}` cannot be read, so whether they hold the one it "
            "tests, `meal-plan--direct--planning-takes-long`, cannot be told",
        ),
        (
            editing(DIRECT, put("outcome", "fingerprint", "none")),
            "the shortlisting of `meal-plan--direct` keeps no fingerprint that reads as one, so "
            "whether it is stale cannot be told",
        ),
        (
            unread(DIRECT),
            f"the canvas at `{DIRECT}` cannot be read: it does not parse as YAML",
        ),
    ],
    ids=[
        "a-goal-no-yaml",
        "assumptions-no-yaml",
        "a-shortlisting-no-fingerprint",
        "a-canvas-no-yaml",
    ],
)
def test_where_the_files_cannot_tell_whether_a_draft_may_be_declared_there_is_no_answer(
    tmp_path: Path, change: Callable[[Path], None], why: str
) -> None:
    root = scene(tmp_path, *DRAFT)
    change(root)
    assert why in untold(DECLARE_DECLARED, root, DECLARED_ON)


def test_where_a_declaration_s_fingerprint_is_of_an_unknown_form_there_is_no_answer(
    tmp_path: Path,
) -> None:
    root = scene(tmp_path, *UNDECIDED, put("declared", "fingerprint", "form", 9))
    assert untold(DECLARE_DECLARED, root, DECLARED_ON) == (
        "the declaration keeps a fingerprint of the canonical form 9, which this version of the "
        "capability does not know: so whether the move may happen cannot be told"
    )


def test_a_refusal_the_files_show_stands_beside_what_cannot_be_told(tmp_path: Path) -> None:
    root = scene(tmp_path, *DRAFT, drop("estimates"))
    unread(GOAL)(root)
    assert refusal(DECLARE_DECLARED, root, DECLARED_ON) == (
        "it was declared without an estimate, made alone before the declaration"
    )


# --- deciding -----------------------------------------------------------------------------------


def test_a_decision_is_open_only_once_the_experiment_is_due(tmp_path: Path) -> None:
    root = scene(tmp_path, *UNDECIDED)
    assert ask(DECIDE, root, DECIDED_ON) == positions.Answer(
        True,
        f"the experiment may be decided: {due_reason(DECIDED_ON)}; its cycle, "
        f"`meal-plan--first`, is not suspended; deciding records its result, where none is "
        f"recorded yet, and its next action, with who decided and when",
    )
    assert refusal(DECIDE, root, LAST_DAY) == (
        f"the experiment stands running, not due: {running_reason(LAST_DAY)}; so no decision is "
        f"open"
    )
    root = scene(tmp_path / "drafted", *DRAFT)
    assert refusal(DECIDE, root, DECIDED_ON) == (
        f"the experiment stands drafted, not due: {DRAFTED_REASON}; so no decision is open"
    )


@pytest.mark.parametrize(
    ("changes", "on"),
    [(UNDECIDED, LANDING_LAST + ONE_DAY), ((), LANDING_DECIDED)],
    ids=["before-the-command-writes", "after"],
)
def test_a_due_experiment_waits_for_its_suspended_cycle_to_resume(
    tmp_path: Path, changes: tuple[Change, ...], on: date
) -> None:
    root = scene(tmp_path, *changes, rel=LANDING, cycle=(ONGOING,))
    assert refusal(DECIDE, root, on, LANDING_PAGE) == (
        f"its cycle, `meal-plan--first`, is suspended: {CYCLE_SUSPENDED}; nothing is recorded on "
        f"its experiments until the person resumes it, by the cycle's move `resume`"
    )


@pytest.mark.parametrize(
    ("changes", "why"),
    [
        ((drop("cycle"),), "it names no cycle, and deciding needs its cycle, not suspended"),
        (
            (put("cycle", "[cycle:meal-plan--second]"),),
            "it names the cycle `meal-plan--second`, and no cycle's file lies at "
            f"`{IDEA}/cycles/second.yaml`: deciding needs its cycle, not suspended",
        ),
    ],
    ids=["it-names-no-cycle", "its-cycle-has-no-file"],
)
def test_a_decision_needs_the_cycle_it_names(
    tmp_path: Path, changes: tuple[Change, ...], why: str
) -> None:
    root = scene(tmp_path, *UNDECIDED, *changes)
    assert refusal(DECIDE, root, DECIDED_ON) == why


def decided(on: date, result_on: date, outcome: str, early: str = "") -> str:
    """Why a decision recorded on `on`, its result on `result_on`, passes its gate."""
    return (
        f"the person decided on {on} to double down, with its result recorded on {result_on}, "
        f"which works out to {outcome}, and its gate lets it through: the experiment was "
        f"declared, its time box ended before the decision{early}, and its cycle, "
        f"`meal-plan--first`, is not suspended"
    )


EARLY = ", or its stopping rule was reached within it"


@pytest.mark.parametrize(
    ("rel", "subject", "changes", "on", "why"),
    [
        (INTERVIEWS, SUBJECT, (), DECIDED_ON, decided(DECIDED_ON, DECIDED_ON, "a pass", EARLY)),
        (
            INTERVIEWS,
            SUBJECT,
            (stopped(WITHIN), put("result", "when", WITHIN), put("decision", "when", WITHIN)),
            WITHIN,
            decided(WITHIN, WITHIN, "a pass", EARLY),
        ),
        (
            LANDING,
            LANDING_PAGE,
            (),
            LANDING_DECIDED,
            decided(LANDING_DECIDED, LANDING_RESULT, "a pass"),
        ),
        (
            LANDING,
            LANDING_PAGE,
            (put("result", "spoiled", True),),
            LANDING_DECIDED,
            decided(LANDING_DECIDED, LANDING_RESULT, "neither pass nor fail"),
        ),
    ],
    ids=[
        "after-its-time-box",
        "on-its-stopping-rule-reached",
        "once-its-cycle-resumed",
        "spoiled-by-a-suspension-its-time-box-ran-through",
    ],
)
def test_a_decision_recorded_that_its_gate_lets_through_moves_the_experiment(
    tmp_path: Path, rel: str, subject: str, changes: tuple[Change, ...], on: date, why: str
) -> None:
    root = scene(tmp_path, *changes, rel=rel)
    assert ask(DECIDE, root, on, subject) == positions.Answer(True, why)


@pytest.mark.parametrize(
    ("changes", "on", "why"),
    [
        (
            (
                put("result", "when", LAST_DAY - ONE_DAY),
                put("decision", "when", LAST_DAY - ONE_DAY),
            ),
            LAST_DAY - ONE_DAY,
            "it was decided on 2026-11-15, but its time box ends on 2026-11-16, as its cycle's "
            "suspensions work it out, and no stopping rule was reached within it by then",
        ),
        (
            (put("result", "when", DECIDED_ON + ONE_DAY),),
            DECIDED_ON + ONE_DAY,
            "its result was recorded on 2026-11-18, after its decision, on 2026-11-17",
        ),
        (
            (drop("result"),),
            DECIDED_ON,
            "it is decided without its result: deciding needs the result and a next action",
        ),
        (
            (put("decision", "next", "abandon"),),
            DECIDED_ON,
            "the decision records no next action of correct-course, double-down and stop",
        ),
        ((drop("decision", "by"),), DECIDED_ON, "the decision does not say who decided"),
        (
            (drop("decision", "when"),),
            DECIDED_ON,
            "the decision records no day it was decided, so its gate cannot be asked of it",
        ),
        ((drop("result", "by"),), DECIDED_ON, "the result does not say who recorded it"),
        (
            (drop("result", "when"),),
            DECIDED_ON,
            "the result records no day it was recorded, so whether it came before the decision "
            "cannot be told",
        ),
        ((drop("declared"),), DECIDED_ON, "it is decided, but it was never declared"),
        (
            (put("result", "spoiled", True),),
            DECIDED_ON,
            "it is recorded as spoiled, but no suspension of its cycle ran through its time box, "
            "2026-11-03 through 2026-11-16: a measurement is spoiled only by a suspension its "
            "time box ran through",
        ),
    ],
    ids=[
        "before-its-time-box-ended",
        "its-result-after-it",
        "without-its-result",
        "a-next-action-of-none",
        "no-one-decided-it",
        "on-no-day",
        "no-one-recorded-its-result",
        "its-result-on-no-day",
        "never-declared",
        "spoiled-by-no-suspension",
    ],
)
def test_a_decision_recorded_that_its_gate_refuses_moves_nothing(
    tmp_path: Path, changes: tuple[Change, ...], on: date, why: str
) -> None:
    root = scene(tmp_path, *changes)
    assert refusal(DECIDE, root, on) == why


def test_a_decision_that_is_no_decision_has_no_answer(tmp_path: Path) -> None:
    root = scene(tmp_path, put("decision", "double-down"))
    assert untold(DECIDE, root, DECIDED_ON) == (
        f"the experiment's file at `{INTERVIEWS}` keeps its decision as something other than one, "
        f"so whether it may be decided cannot be told"
    )


# --- answering the engine -----------------------------------------------------------------------


def test_the_engine_reads_one_json_object_or_no_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each script answers the engine through `as_of`, on the day it read where it started."""
    root = scene(tmp_path, *UNDECIDED)
    monkeypatch.chdir(root)
    argv = [SUBJECT, "--json"]
    classify = positions.as_of(detect.classify, DECIDED_ON)
    assert positions.answer_detection(argv, "detect", "", classify) == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "due",
        "reason": due_reason(DECIDED_ON),
    }
    assert positions.answer_gate(argv, "come-due", "", positions.as_of(COME_DUE, DECIDED_ON)) == 0
    assert json.loads(capsys.readouterr().out)["result"] is True
    unread(INTERVIEWS)(root)
    gate = positions.as_of(COME_DUE, DECIDED_ON)
    assert positions.answer_gate(argv, "come-due", "", gate) == positions.NO_ANSWER
    said = capsys.readouterr()
    assert said.out == ""
    assert said.err.startswith(f"come-due: the experiment's file at `{INTERVIEWS}` cannot be read")
