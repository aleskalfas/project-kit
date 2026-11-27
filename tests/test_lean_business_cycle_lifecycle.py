"""The cycle's predicates (lean-business DEC-003 points 1 and 4): the classifier that places a
cycle on a day, and the gates on its seven moves, each asked in this process, on a fixed day,
of a copy of the fixture idea with one thing changed. The fixture's cycle has a window of
ninety days from 2026-11-01, whose last day a suspension from 2026-12-20, resumed on
2027-01-03, moves from 2027-01-29 to 2027-02-12, and a review recorded on 2027-02-15.

Each script reads today where it starts and hands it to `classify` or `judge`, so each test
asks those with a day of its own, as the script would on that day. A move the dates or a
suspension make is the script's, and its gate opens only once the data places the cycle at
its target. The person's moves, resuming and deciding, hold on both sides of the command's
write. A predicate gives no answer (`Unreadable`) where the files cannot tell; the engine
reads no answer as indeterminate."""

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
    detect,
    start,
    end,
    suspend_running,
    suspend_in_review,
    shift_window,
    resume,
    decide,
) = load(
    "lean-business",
    "positions",
    "cycle_lifecycle_detect.py",
    "cycle_lifecycle_gate_planned_running_start.py",
    "cycle_lifecycle_gate_running_in_review_end.py",
    "cycle_lifecycle_gate_running_suspended_suspend.py",
    "cycle_lifecycle_gate_in_review_suspended_suspend.py",
    "cycle_lifecycle_gate_in_review_running_shift_window.py",
    "cycle_lifecycle_gate_suspended_running_resume.py",
    "cycle_lifecycle_gate_in_review_decided_decide.py",
)

FIXTURE = Path(__file__).resolve().parent / "fixtures/lean-business/.repo"

IDEA = "lean-business/meal-plan"
GOAL = f"{IDEA}/goal.yaml"
CYCLE = f"{IDEA}/cycles/first.yaml"
LANDING = f"{IDEA}/experiments/landing-page.yaml"
SUBJECT = "meal-plan--first"

ONE_DAY = timedelta(days=1)
#: The window's first day.
FIRST_DAY = date(2026, 11, 1)
#: The window's last day, as the fixture's suspension moves it.
LAST_DAY = date(2027, 2, 12)
#: The window's last day with no suspension.
LAST_DAY_UNMOVED = date(2027, 1, 29)
#: The day the fixture's review records the decision.
REVIEWED = date(2027, 2, 15)
#: A day the fixture's suspension covers, and one well past the window, where an ongoing
#: suspension is asked about.
SUSPENDED_ON = date(2027, 1, 10)
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


#: The review taken away, so the cycle's suspensions and dates place it.
NO_REVIEW = drop("review")
#: The fixture's suspension made ongoing: it records no resumption.
ONGOING = drop("suspensions", 0, "resumed")


def suspension(first_day: date, recorded: date, resumed: date, resumption_recorded: date) -> Any:
    """A suspension that resumed, as the command records it."""
    return {
        "reason": "Away",
        "first-day": first_day,
        "by": "A. Founder",
        "when": recorded,
        "resumed": {"day": resumed, "by": "A. Founder", "when": resumption_recorded},
    }


def undecided(tmp_path: Path, *changes: Change) -> Path:
    """The fixture with no review, and each of `changes` made to its cycle."""
    root = project(tmp_path)
    edit(root, CYCLE, NO_REVIEW, *changes)
    return root


# --- the predicates, as the scripts ask them ----------------------------------------------------


def position(root: Path, on: date, subject: str = SUBJECT) -> Any:
    """Where the cycle stands on `on`, as `cycle_lifecycle_detect.py` answers."""
    return detect.classify(root, subject, on)


START: Gate = start.judge
END: Gate = end.judge
SUSPEND_RUNNING: Gate = suspend_running.judge
SUSPEND_IN_REVIEW: Gate = suspend_in_review.judge
SHIFT_WINDOW: Gate = shift_window.judge
RESUME: Gate = resume.judge
DECIDE: Gate = decide.judge


def ask(gate: Gate, root: Path, on: date, subject: str = SUBJECT) -> Any:
    return gate(root, subject, on)


def refusal(gate: Gate, root: Path, on: date, subject: str = SUBJECT) -> str:
    """Why `gate` refuses the move on `on`, which it must."""
    answer = ask(gate, root, on, subject)
    assert answer.result is False
    return answer.reason


def running_reason(on: date, last: date = LAST_DAY, moved: bool = True) -> str:
    """Why a cycle whose window runs through `last` stands running on `on`."""
    worked = ", as its suspensions work it out" if moved else ""
    return (
        f"its window runs from {FIRST_DAY} through {last}{worked}, and holds today, {on}, "
        f"with no suspension ongoing"
    )


def in_review_reason(on: date, last: date = LAST_DAY, moved: bool = True) -> str:
    """Why a cycle whose window ended on `last` stands in review on `on`."""
    worked = ", as its suspensions work it out" if moved else ""
    return f"its window ended on {last}{worked}, before today, {on}, and no decision is recorded"


DECIDED_REASON = (
    "the person decided to persevere for `meal-plan--direct` on 2027-02-15, which outranks its "
    "suspensions and its dates"
)
SUSPENDED_REASON = (
    "a suspension from 2026-12-20 is ongoing, with no day of resuming, which outranks the "
    "cycle's dates: none of its days count toward the window"
)


# --- the classifier -----------------------------------------------------------------------------


@pytest.mark.parametrize("on", [FIRST_DAY - ONE_DAY, REVIEWED], ids=["before-its-window", "then"])
def test_a_decision_places_the_cycle_whatever_its_dates_say(tmp_path: Path, on: date) -> None:
    root = project(tmp_path)
    assert position(root, on) == positions.Position(positions.DECIDED, DECIDED_REASON)


@pytest.mark.parametrize(
    ("on", "state", "reason"),
    [
        (
            FIRST_DAY - ONE_DAY,
            "planned",
            "its plan is recorded, and its window starts on 2026-11-01, as its suspensions work "
            "it out, after today, 2026-10-31",
        ),
        (FIRST_DAY, "running", running_reason(FIRST_DAY)),
        (date(2027, 1, 2), "running", running_reason(date(2027, 1, 2))),
        (LAST_DAY, "running", running_reason(LAST_DAY)),
        (LAST_DAY + ONE_DAY, "in-review", in_review_reason(LAST_DAY + ONE_DAY)),
    ],
    ids=[
        "the-day-before-its-window",
        "its-first-day",
        "a-day-its-resumed-suspension-covered",
        "its-last-day-as-moved",
        "the-day-after",
    ],
)
def test_without_a_decision_its_window_as_worked_out_places_it(
    tmp_path: Path, on: date, state: str, reason: str
) -> None:
    root = undecided(tmp_path)
    assert position(root, on) == positions.Position(state, reason)


@pytest.mark.parametrize("on", [SUSPENDED_ON, LONG_AFTER], ids=["within-its-window", "long-after"])
def test_an_ongoing_suspension_places_it_suspended_whatever_its_dates_say(
    tmp_path: Path, on: date
) -> None:
    root = undecided(tmp_path, ONGOING)
    assert position(root, on) == positions.Position(positions.SUSPENDED, SUSPENDED_REASON)


def test_a_cycle_without_its_file_stands_nowhere_and_no_move_is_open(tmp_path: Path) -> None:
    root = project(tmp_path)
    second = "meal-plan--second"
    absent = f"no cycle's file lies at `{IDEA}/cycles/second.yaml`"
    assert position(root, REVIEWED, second) == positions.Position(
        None,
        f"`{second}` stands in none of the cycle's states, which start with its plan: {absent}",
    )
    assert refusal(START, root, REVIEWED, second) == (
        f"no move of the cycle is open to `{second}`, which stands in none of its states without "
        f"its file: {absent}"
    )


def unread_cycle(root: Path) -> None:
    (root / CYCLE).write_text("id: [unclosed\n", encoding="utf-8")


def editing(*changes: Change) -> Callable[[Path], None]:
    """What `edit` does to the cycle, for the project a test is given later."""
    return lambda root: edit(root, CYCLE, *changes)


@pytest.mark.parametrize(
    ("change", "why"),
    [
        (unread_cycle, f"the cycle's file at `{CYCLE}` cannot be read: it does not parse as YAML"),
        (
            editing(put("review", "decision", "stop")),
            "records a review whose decision is none of persevere, pivot and pause",
        ),
        (
            editing(NO_REVIEW, put("window", "days", 0)),
            "declares no window that reads as one, a first day and the days it holds, at least one",
        ),
        (
            editing(NO_REVIEW, put("suspensions", 0, "resumed", "day", "soon")),
            f"the suspension at place 1 of `{CYCLE}` has no day of resuming that reads as a day",
        ),
    ],
    ids=["a-file-no-yaml", "a-decision-of-none", "a-window-of-no-days", "a-resumption-no-day"],
)
def test_where_the_files_cannot_tell_where_it_stands_there_is_no_answer(
    tmp_path: Path, change: Callable[[Path], object], why: str
) -> None:
    root = project(tmp_path)
    change(root)
    with pytest.raises(positions.Unreadable) as raised:
        position(root, REVIEWED)
    assert why in str(raised.value)


def test_a_subject_that_is_no_cycle_s_id_has_no_answer(tmp_path: Path) -> None:
    root = project(tmp_path)
    no_id = "`Meal_Plan` is no cycle's id"
    with pytest.raises(positions.Unreadable, match=no_id):
        position(root, REVIEWED, "Meal_Plan")
    with pytest.raises(positions.Unreadable, match=no_id):
        ask(START, root, REVIEWED, "Meal_Plan")


# --- the moves the dates make -------------------------------------------------------------------


def test_the_start_opens_on_the_window_s_first_day(tmp_path: Path) -> None:
    root = undecided(tmp_path)
    assert refusal(START, root, FIRST_DAY - ONE_DAY).startswith(
        "the cycle stands planned, not running: its plan is recorded"
    )
    assert ask(START, root, FIRST_DAY) == positions.Answer(
        True, f"the cycle's window has started: {running_reason(FIRST_DAY)}"
    )


def test_the_end_opens_the_day_after_the_window_s_last(tmp_path: Path) -> None:
    root = undecided(tmp_path)
    assert refusal(END, root, LAST_DAY) == (
        f"the cycle stands running, not in review: {running_reason(LAST_DAY)}"
    )
    after = LAST_DAY + ONE_DAY
    assert ask(END, root, after) == positions.Answer(
        True, f"the cycle's window has ended: {in_review_reason(after)}"
    )


def test_no_date_moves_a_suspended_cycle(tmp_path: Path) -> None:
    root = undecided(tmp_path, ONGOING)
    assert refusal(END, root, LONG_AFTER) == (
        f"the cycle stands suspended, not in review: {SUSPENDED_REASON}"
    )
    assert refusal(START, root, LONG_AFTER) == (
        f"the cycle stands suspended, not running: {SUSPENDED_REASON}"
    )


@pytest.mark.parametrize(
    ("gate", "target"),
    [
        (START, "running"),
        (END, "in review"),
        (SUSPEND_RUNNING, "suspended"),
        (SUSPEND_IN_REVIEW, "suspended"),
        (SHIFT_WINDOW, "running"),
        (RESUME, "running"),
    ],
    ids=["start", "end", "suspend-running", "suspend-in-review", "shift-window", "resume"],
)
def test_no_move_but_its_decision_is_open_to_a_decided_cycle(
    tmp_path: Path, gate: Gate, target: str
) -> None:
    root = project(tmp_path)
    assert refusal(gate, root, REVIEWED) == (
        f"the cycle stands decided, not {target}: {DECIDED_REASON}"
    )


# --- suspending ---------------------------------------------------------------------------------


def test_a_suspension_moves_the_cycle_only_once_the_person_recorded_it(tmp_path: Path) -> None:
    """Before the command writes, the gate is closed, so a cycle in review still waits on
    the person; after, the ongoing suspension it recorded lets the move through."""
    root = undecided(tmp_path)
    assert refusal(SUSPEND_RUNNING, root, LAST_DAY) == (
        f"the cycle stands running, not suspended: {running_reason(LAST_DAY)}"
    )
    after = LAST_DAY + ONE_DAY
    assert refusal(SUSPEND_IN_REVIEW, root, after) == (
        f"the cycle stands in review, not suspended: {in_review_reason(after)}"
    )
    root = undecided(tmp_path / "recorded", ONGOING)
    edit(root, LANDING, drop("result"), drop("decision"))
    kept = positions.Answer(
        True, f"the person recorded a suspension that keeps its rules: {SUSPENDED_REASON}"
    )
    assert ask(SUSPEND_RUNNING, root, SUSPENDED_ON) == kept
    assert ask(SUSPEND_IN_REVIEW, root, SUSPENDED_ON) == kept


def test_a_suspension_over_days_that_hold_work_breaks_its_rules(tmp_path: Path) -> None:
    """The landing page's result and decision, recorded on 2027-01-04 and 2027-01-05, fall
    on days the ongoing suspension covers."""
    root = undecided(tmp_path, ONGOING)
    assert refusal(SUSPEND_RUNNING, root, SUSPENDED_ON) == (
        "the suspension at place 1 breaks its rules: it covers 2027-01-04, which holds the "
        "result of `meal-plan--landing-page`; the suspension at place 1 breaks its rules: it "
        "covers 2027-01-05, which holds the decision of `meal-plan--landing-page`"
    )


# --- shifting the window ------------------------------------------------------------------------

#: The day an absence already over is recorded, after the unmoved window ended.
RECORDED_LATE = date(2027, 2, 1)
#: An absence from 2027-01-20 until 2027-01-30, recorded once it was over: its ten days move
#: the unmoved window's last day to 2027-02-08.
LATE_ABSENCE = suspension(date(2027, 1, 20), RECORDED_LATE, date(2027, 1, 30), RECORDED_LATE)
LAST_DAY_SHIFTED = date(2027, 2, 8)


def test_an_absence_already_over_recorded_late_takes_the_cycle_back_to_running(
    tmp_path: Path,
) -> None:
    root = undecided(tmp_path, drop("suspensions"))
    before = in_review_reason(RECORDED_LATE, LAST_DAY_UNMOVED, moved=False)
    assert position(root, RECORDED_LATE) == positions.Position(positions.IN_REVIEW, before)
    assert refusal(SHIFT_WINDOW, root, RECORDED_LATE) == (
        f"the cycle stands in review, not running: {before}"
    )
    edit(root, CYCLE, put("suspensions", [LATE_ABSENCE]))
    after = running_reason(RECORDED_LATE, LAST_DAY_SHIFTED)
    assert position(root, RECORDED_LATE) == positions.Position(positions.RUNNING, after)
    assert ask(SHIFT_WINDOW, root, RECORDED_LATE) == positions.Answer(
        True,
        f"the suspension recorded last, from 2027-01-20 until 2027-01-30, moved the window on, "
        f"and keeps its rules: {after}",
    )


def test_a_late_absence_that_an_act_recorded_since_contradicts_is_refused(
    tmp_path: Path,
) -> None:
    """The goal set at the review, on 2027-01-31, needed the window ended."""
    root = undecided(tmp_path, put("suspensions", [LATE_ABSENCE]))
    edit(root, GOAL, put("when", date(2027, 1, 31)))
    assert refusal(SHIFT_WINDOW, root, RECORDED_LATE) == (
        "the suspension at place 1 breaks its rules: counted with it, the goal set, recorded on "
        "2027-01-31, reads as one its gate refuses: the goal was set on 2027-01-31, while the "
        "cycle `meal-plan--first` was planned, running or suspended: it changes only while none "
        "of the idea's cycles is"
    )


def test_only_a_recorded_suspension_shifts_the_window(tmp_path: Path) -> None:
    root = undecided(tmp_path, drop("suspensions"))
    on = date(2027, 1, 5)
    assert refusal(SHIFT_WINDOW, root, on) == (
        "no suspension is recorded, and only an absence already over moves a cycle's window "
        f"on, back from its review: {running_reason(on, LAST_DAY_UNMOVED, moved=False)}"
    )


# --- resuming -----------------------------------------------------------------------------------


def test_a_suspended_cycle_may_resume(tmp_path: Path) -> None:
    root = undecided(tmp_path, ONGOING)
    assert ask(RESUME, root, SUSPENDED_ON) == positions.Answer(
        True,
        f"the cycle may resume: {SUSPENDED_REASON}; resuming records the day it resumed, which "
        f"its rules hold no earlier than the suspension's first day and no later than the day it "
        f"is recorded",
    )


@pytest.mark.parametrize(
    "on", [date(2027, 1, 3), date(2027, 1, 5)], ids=["the-day-it-resumed", "a-later-day"]
)
def test_a_resumption_its_rules_allow_lets_the_move_through(tmp_path: Path, on: date) -> None:
    root = undecided(tmp_path)
    assert ask(RESUME, root, on) == positions.Answer(
        True, f"the cycle resumed on 2027-01-03, a day its rules allow: {running_reason(on)}"
    )


def test_a_resumption_that_leaves_the_window_run_out_does_not_run_the_cycle(
    tmp_path: Path,
) -> None:
    """Suspended on 2027-01-25 and resumed on 2027-01-27, recorded only on 2027-03-01: the
    window, moved on by two days, ended on 2027-01-31, so the cycle reads in review, and the
    resumption's move into running is refused. The move into review that resuming takes then
    (DEC-003 point 4) has a gate of its own."""
    resumed = suspension(date(2027, 1, 25), date(2027, 1, 26), date(2027, 1, 27), date(2027, 3, 1))
    root = undecided(tmp_path, put("suspensions", [resumed]))
    on = date(2027, 3, 1)
    ended = in_review_reason(on, date(2027, 1, 31))
    assert position(root, on) == positions.Position(positions.IN_REVIEW, ended)
    assert refusal(RESUME, root, on).startswith(
        f"it resumed on 2027-01-27, and the cycle stands in review, not running: {ended}"
    )


def test_a_cycle_never_suspended_resumes_from_nothing(tmp_path: Path) -> None:
    root = undecided(tmp_path, drop("suspensions"))
    on = date(2027, 1, 5)
    assert refusal(RESUME, root, on) == (
        "the cycle was never suspended, so it resumes from nothing: "
        f"{running_reason(on, LAST_DAY_UNMOVED, moved=False)}"
    )


# --- deciding -----------------------------------------------------------------------------------


def test_a_decision_is_open_only_in_review(tmp_path: Path) -> None:
    root = undecided(tmp_path)
    after = LAST_DAY + ONE_DAY
    assert ask(DECIDE, root, after) == positions.Answer(
        True,
        f"the cycle may be decided: {in_review_reason(after)}; the review records what each key "
        f"result reached, the winning variant among those the cycle explored, and the person's "
        f"decision for it, with its reasons",
    )
    assert refusal(DECIDE, root, LAST_DAY) == (
        f"the cycle stands running, not in review: {running_reason(LAST_DAY)}; so no decision is "
        f"open"
    )
    root = undecided(tmp_path / "suspended", ONGOING)
    assert refusal(DECIDE, root, date(2027, 3, 1)) == (
        f"the cycle stands suspended, not in review: {SUSPENDED_REASON}; so no decision is open"
    )


def test_a_review_its_gate_lets_through_moves_the_cycle(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert ask(DECIDE, root, REVIEWED) == positions.Answer(
        True,
        "the review records the person's decision on 2027-02-15 to persevere for "
        "`meal-plan--direct`, with its reasons, and its gate lets it through: each key result's "
        "reach is recorded, the winning variant is one the cycle explored, and the window ended "
        "before the decision",
    )


@pytest.mark.parametrize(
    ("changes", "on", "why"),
    [
        (
            (put("review", "decision", "pivot"),),
            REVIEWED,
            "it pivots on no decided experiment: a pivot names at least one as its evidence",
        ),
        (
            (put("review", "when", LAST_DAY - 2 * ONE_DAY),),
            LAST_DAY - 2 * ONE_DAY,
            "it was decided on 2027-02-10, but its window ends on 2027-02-12, as its suspensions "
            "work it out",
        ),
        (
            (put("review", "decision", "stop"),),
            REVIEWED,
            "the review records no decision of persevere, pivot and pause",
        ),
    ],
    ids=["a-pivot-without-evidence", "before-the-window-ended", "a-decision-of-none"],
)
def test_a_review_its_gate_refuses_moves_nothing(
    tmp_path: Path, changes: tuple[Change, ...], on: date, why: str
) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, *changes)
    assert refusal(DECIDE, root, on) == why


# --- answering the engine -----------------------------------------------------------------------


def test_the_engine_reads_one_json_object_or_no_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each script answers the engine through `as_of`, on the day it read where it started."""
    root = undecided(tmp_path)
    monkeypatch.chdir(root)
    argv = [SUBJECT, "--json"]
    on = LAST_DAY + ONE_DAY
    classify = positions.as_of(detect.classify, on)
    assert positions.answer_detection(argv, "detect", "", classify) == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "in-review",
        "reason": in_review_reason(on),
    }
    assert positions.answer_gate(argv, "end", "", positions.as_of(END, on)) == 0
    assert json.loads(capsys.readouterr().out)["result"] is True
    unread_cycle(root)
    assert positions.answer_gate(argv, "end", "", positions.as_of(END, on)) == positions.NO_ANSWER
    said = capsys.readouterr()
    assert said.out == ""
    assert said.err.startswith(f"end: the cycle's file at `{CYCLE}` cannot be read")
