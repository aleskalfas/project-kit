"""The desk stage's predicates (lean-business DEC-003 points 1 and 2): the classifier that
places a variant, and the gates on its moves into desirable, viable, feasible, shortlisted and
shelved, each asked in this process of a copy of the fixture idea with one thing changed. The
fixture's `direct` variant has a yes on all three steps, none stale, and is shortlisted.

Each gate's script hands the variant its subject names to `positions.desk_gate`, with its
judgement: `passing` on its step, `shortlisting`, or `shelving`. So each test asks that pair,
as the script does. A gate refuses with what the files show, and gives no answer
(`Unreadable`) where they cannot tell; the engine reads no answer as indeterminate."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.in_process import load

(positions, gates) = load("lean-business", "positions", "gates")

FIXTURE = Path(__file__).resolve().parent / "fixtures/lean-business/.repo"

IDEA = "lean-business/meal-plan"
GOAL = f"{IDEA}/goal.yaml"
DIRECT = f"{IDEA}/variants/direct/canvas.yaml"
CONFIG = ".pkit/capabilities/lean-business/project/config.yaml"
SUBJECT = "meal-plan--direct"

Change = Callable[[Any], None]
Gate = Callable[[Path, str], Any]


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


#: The variant's outcome taken away, so its verdicts alone place it.
NO_OUTCOME = drop("outcome")


def answered(step: str, answer: str) -> Change:
    return put("verdicts", step, "answer", answer)


def unread_goal(root: Path) -> None:
    (root / GOAL).write_text("revenue: [\n", encoding="utf-8")


def unread_canvas(root: Path) -> None:
    (root / DIRECT).write_text("id: [\n", encoding="utf-8")


def refuse_location(root: Path) -> None:
    """Record a location outside the repository, which the rules refuse."""
    (root / CONFIG).parent.mkdir(parents=True)
    (root / CONFIG).write_text("location: ../out\n", encoding="utf-8")


def editing(rel: str, *changes: Change) -> Callable[[Path], None]:
    """What `edit` does to `rel`, for the project a test is given later."""
    return lambda root: edit(root, rel, *changes)


# --- the predicates, as the scripts ask them ----------------------------------------------------


def stage(root: Path) -> Any:
    """Where the variant stands, as `desk_stage_detect.py` answers."""
    return positions.desk_stage_of(root, SUBJECT)


def _passing(step: str) -> Gate:
    return positions.desk_gate(lambda variant: positions.passing(variant, step))


PASS_DESIRABILITY = _passing("desirability")
PASS_VIABILITY = _passing("viability")
PASS_FEASIBILITY = _passing("feasibility")
#: The gate on `shortlist`, from feasible and from shortlisted itself.
SHORTLIST = positions.desk_gate(positions.shortlisting)
#: The gate on `shelve`, from each state it leaves.
SHELVE = positions.desk_gate(positions.shelving)


def ask(gate: Gate, root: Path) -> Any:
    return gate(root, SUBJECT)


def passes(gate: Gate, root: Path) -> bool:
    answer = ask(gate, root)
    assert answer.reason
    return answer.result


def refusal(gate: Gate, root: Path) -> str:
    """Why `gate` refuses the move, which it must."""
    answer = ask(gate, root)
    assert answer.result is False
    return answer.reason


# --- the classifier -----------------------------------------------------------------------------


def test_an_outcome_places_the_variant_whatever_its_verdicts_say(tmp_path: Path) -> None:
    root = project(tmp_path)
    position = stage(root)
    assert position.state == positions.SHORTLISTED
    assert position.reason == (
        "the person shortlisted the variant on 2026-10-08, which outranks its verdicts"
    )
    edit(root, DIRECT, answered("viability", "no"))
    assert stage(root).state == positions.SHORTLISTED


def test_a_shelved_variant_stands_shelved_with_its_reason(tmp_path: Path) -> None:
    root = project(tmp_path)
    shelved = {"kind": "shelved", "reason": "Too few parents plan", "by": "A", "when": "2026-10-09"}
    edit(root, DIRECT, put("outcome", shelved))
    assert stage(root) == positions.Position(
        positions.SHELVED, "the person shelved the variant on 2026-10-09: Too few parents plan"
    )


def test_a_split_variant_stands_split_naming_the_variants_it_went_into(tmp_path: Path) -> None:
    root = project(tmp_path)
    split = {
        "kind": "split",
        "into": ["[canvas:meal-plan--a]", "[canvas:meal-plan--b]"],
        "by": "A",
        "when": "2026-10-09",
    }
    edit(root, DIRECT, put("outcome", split))
    assert stage(root) == positions.Position(
        positions.SPLIT,
        "the person split the variant on 2026-10-09 into `meal-plan--a` and `meal-plan--b`",
    )


@pytest.mark.parametrize(
    ("changes", "state", "reason"),
    [
        (
            (),
            "feasible",
            "the person's yes stands on desirability, viability and feasibility, and the "
            "variant has no outcome yet",
        ),
        (
            (answered("feasibility", "no"),),
            "viable",
            "the person's yes stands on desirability and viability, and feasibility has a no",
        ),
        (
            (drop("verdicts", "viability"), drop("verdicts", "feasibility")),
            "desirable",
            "the person's yes stands on desirability, and viability has no verdict",
        ),
        (
            (
                answered("desirability", "no"),
                drop("verdicts", "viability"),
                drop("verdicts", "feasibility"),
            ),
            "sketched",
            "a canvas exists, and desirability has a no",
        ),
        (
            (drop("verdicts"),),
            "sketched",
            "a canvas exists, and desirability has no verdict",
        ),
    ],
    ids=["all-three", "a-no-on-feasibility", "only-desirability", "a-no-on-desirability", "none"],
)
def test_without_an_outcome_the_run_of_yes_from_the_first_step_places_it(
    tmp_path: Path, changes: tuple[Change, ...], state: str, reason: str
) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME, *changes)
    assert stage(root) == positions.Position(state, reason)


def test_the_run_stops_at_the_first_step_without_a_yes(tmp_path: Path) -> None:
    """A yes past a gap, and an answer that does not read past a no, count for nothing:
    the run never reaches them."""
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME, drop("verdicts", "viability"))
    assert stage(root).state == positions.DESIRABLE
    edit(root, DIRECT, put("verdicts", "viability", {"answer": "no"}))
    edit(root, DIRECT, answered("feasibility", "maybe"))
    assert stage(root) == positions.Position(
        positions.DESIRABLE, "the person's yes stands on desirability, and viability has a no"
    )


def test_a_stale_verdict_holds_the_position(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME, put("boxes", "customer-segments", 0, "text", "Everyone"))
    assert stage(root).state == positions.FEASIBLE


@pytest.mark.parametrize(
    ("change", "why"),
    [
        (
            editing(DIRECT, put("outcome", "kind", "parked")),
            "records an outcome that is none of shortlisted, shelved and split",
        ),
        (
            editing(DIRECT, put("outcome", "shortlisted")),
            "records an outcome that is none of shortlisted, shelved and split",
        ),
        (
            editing(DIRECT, NO_OUTCOME, answered("desirability", "maybe")),
            f"the verdict on desirability at `{DIRECT}` holds no answer",
        ),
        (
            editing(DIRECT, NO_OUTCOME, put("verdicts", ["yes"])),
            "keeps its verdicts as something other than one verdict for each step",
        ),
        (unread_canvas, "cannot be read: it does not parse as YAML"),
        (
            editing(DIRECT, put("pkit_schema", "lean-business:goal")),
            "names `lean-business:goal`, not `lean-business:canvas`",
        ),
        (refuse_location, "the location of the ideas cannot be read"),
    ],
    ids=[
        "an-unknown-outcome",
        "an-outcome-no-mapping",
        "an-answer-neither-yes-nor-no",
        "verdicts-no-mapping",
        "a-canvas-no-yaml",
        "a-canvas-of-another-schema",
        "a-location-refused",
    ],
)
def test_where_the_files_cannot_tell_where_it_stands_there_is_no_answer(
    tmp_path: Path, change: Callable[[Path], object], why: str
) -> None:
    root = project(tmp_path)
    change(root)
    with pytest.raises(positions.Unreadable) as raised:
        stage(root)
    assert why in str(raised.value)


def test_a_canvas_git_ignores_is_none_and_no_move_is_open(tmp_path: Path) -> None:
    root = project(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".gitignore").write_text(f"{DIRECT}\n", encoding="utf-8")
    position = stage(root)
    assert position.state is None
    assert "something lies there, but it is a link, or a file git ignores" in position.reason
    assert "no move of the desk stage is open to `meal-plan--direct`" in refusal(
        PASS_DESIRABILITY, root
    )


def test_a_canvas_ending_in_yml_is_none_and_named_astray(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / DIRECT).rename(root / DIRECT.replace(".yaml", ".yml"))
    position = stage(root)
    assert position.state is None
    assert f"`{DIRECT.replace('.yaml', '.yml')}` lies astray in its folder" in position.reason


def test_with_no_location_no_variant_stands_anywhere(tmp_path: Path) -> None:
    root = project(tmp_path)
    shutil.rmtree(root / "lean-business")
    (root / "lean-business").write_text("x", encoding="utf-8")
    position = stage(root)
    assert position.state is None
    assert "no idea lies anywhere" in position.reason
    assert "no idea lies anywhere" in refusal(PASS_DESIRABILITY, root)


# --- the gates on a yes -------------------------------------------------------------------------


def test_each_gate_lets_its_move_through_where_nothing_refuses_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME)
    assert ask(PASS_DESIRABILITY, root) == positions.Answer(
        True, "a yes on desirability may stand: each box desirability judges holds an entry"
    )
    assert ask(PASS_VIABILITY, root) == positions.Answer(
        True,
        "a yes on viability may stand: the variant has a yes on desirability, not stale; the "
        "idea's goal is set; the revenue streams hold an entry, and the estimate's inputs are "
        "given",
    )
    assert ask(PASS_FEASIBILITY, root) == positions.Answer(
        True,
        "a yes on feasibility may stand: the variant has a yes on desirability and viability, "
        "neither stale; the idea's goal is set; the first stage's target is given",
    )
    assert ask(SHORTLIST, root) == positions.Answer(
        True,
        "the variant may be shortlisted: it has a yes on desirability, viability and "
        "feasibility, none stale",
    )


def test_a_yes_needs_a_yes_on_each_step_before_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME, drop("verdicts", "viability"), drop("verdicts", "feasibility"))
    assert passes(PASS_VIABILITY, root)
    assert refusal(PASS_FEASIBILITY, root) == "a yes on feasibility needs a yes on viability first"
    edit(root, DIRECT, answered("desirability", "no"))
    assert passes(PASS_DESIRABILITY, root)
    assert refusal(PASS_VIABILITY, root) == "a yes on viability needs a yes on desirability first"
    edit(root, DIRECT, answered("desirability", "maybe"))
    assert refusal(PASS_VIABILITY, root) == "a yes on viability needs a yes on desirability first"


def test_a_yes_after_a_no_on_its_own_step_may_stand(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME, answered("feasibility", "no"))
    assert passes(PASS_FEASIBILITY, root)


def test_a_yes_needs_what_its_step_judges(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME, drop("boxes", "problem"))
    assert refusal(PASS_DESIRABILITY, root) == (
        "a yes on desirability needs `problem`, and the canvas the yes judged holds no entry there"
    )
    root = project(tmp_path / "target")
    edit(root, DIRECT, NO_OUTCOME, drop("traction", "first-stage", "target"))
    assert refusal(PASS_FEASIBILITY, root) == (
        "a yes on feasibility needs the first stage's target, `traction`, and the canvas the "
        "yes judged holds no entry there"
    )


def test_a_yes_judged_against_the_goal_needs_the_goal(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / GOAL).unlink()
    assert passes(PASS_DESIRABILITY, root)
    assert refusal(PASS_VIABILITY, root) == (
        "a verdict on viability judges the variant against the idea's goal, and the idea has "
        "none: the goal is set before any variant's viability is judged"
    )
    feasibility = refusal(PASS_FEASIBILITY, root)
    assert "a verdict on feasibility judges the variant against the idea's goal" in feasibility
    assert "the verdict on viability is stale" in feasibility
    again = refusal(SHORTLIST, root)
    assert "the verdict on viability is stale" in again
    assert "the verdict on feasibility is stale" in again


def test_nothing_new_rests_on_a_stale_verdict(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME, put("boxes", "customer-segments", 0, "text", "Everyone"))
    stale = (
        "the verdict on desirability is stale, and nothing new rests on a stale verdict: the "
        "model or the boxes it judged changed since it was given"
    )
    assert refusal(PASS_VIABILITY, root) == stale
    assert refusal(PASS_FEASIBILITY, root) == stale
    assert refusal(SHORTLIST, root) == stale


def test_a_changed_goal_makes_stale_only_the_verdicts_judged_against_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, GOAL, put("years", 4))
    assert passes(PASS_VIABILITY, root)
    assert "the verdict on viability is stale" in refusal(PASS_FEASIBILITY, root)
    again = refusal(SHORTLIST, root)
    assert "the verdict on viability is stale" in again
    assert "the verdict on feasibility is stale" in again


# --- the gate on a shortlisting -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "none_on"),
    [
        ((answered("feasibility", "no"),), "feasibility"),
        (
            (drop("verdicts", "viability"), drop("verdicts", "feasibility")),
            "viability, feasibility",
        ),
    ],
    ids=["a-no-on-feasibility", "only-desirability"],
)
def test_a_shortlisting_needs_a_yes_on_all_three_steps(
    tmp_path: Path, changes: tuple[Change, ...], none_on: str
) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, NO_OUTCOME, *changes)
    assert refusal(SHORTLIST, root) == (
        f"a shortlisting needs a yes on all three steps, and the variant has none on {none_on}"
    )


def test_a_shortlisting_gone_stale_alone_may_be_taken_again(tmp_path: Path) -> None:
    """A change the verdicts did not judge, such as to the channels, leaves them fresh, and
    the shortlisting the person takes again records its fingerprint anew."""
    root = project(tmp_path)
    edit(root, DIRECT, put("boxes", "channels", 0, "text", "Schools"))
    assert stage(root).state == positions.SHORTLISTED
    assert passes(SHORTLIST, root)


def test_the_shortlisting_gate_reads_only_the_verdicts_it_rests_on(tmp_path: Path) -> None:
    """The shortlisting is the move itself, so an outcome the files cannot read, which leaves
    the variant's position untold, is not the gate's to judge."""
    root = project(tmp_path)
    edit(root, DIRECT, put("outcome", "kind", "parked"))
    assert passes(SHORTLIST, root)


# --- what a gate cannot tell --------------------------------------------------------------------


def test_a_goal_that_does_not_read_leaves_untold_each_move_judged_against_it(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    unread_goal(root)
    assert stage(root).state == positions.SHORTLISTED
    assert passes(PASS_DESIRABILITY, root)
    for gate in (PASS_VIABILITY, PASS_FEASIBILITY, SHORTLIST):
        with pytest.raises(positions.Unreadable) as raised:
            ask(gate, root)
        assert f"the idea's goal at `{GOAL}` cannot be read" in str(raised.value)


def test_a_refusal_the_files_show_stands_beside_what_cannot_be_told(tmp_path: Path) -> None:
    root = project(tmp_path)
    unread_goal(root)
    edit(root, DIRECT, drop("boxes", "revenue-streams"))
    assert refusal(PASS_VIABILITY, root) == (
        "a yes on viability needs `revenue-streams`, and the canvas the yes judged holds no "
        "entry there"
    )
    root = project(tmp_path / "stale")
    unread_goal(root)
    edit(root, DIRECT, put("boxes", "customer-segments", 0, "text", "Everyone"))
    for gate in (PASS_FEASIBILITY, SHORTLIST):
        assert refusal(gate, root).startswith("the verdict on desirability is stale")


def test_a_fingerprint_that_cannot_be_compared_leaves_the_move_untold(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("verdicts", "desirability", "fingerprint", "form", 9))
    assert passes(PASS_DESIRABILITY, root)
    for gate in (PASS_VIABILITY, SHORTLIST):
        with pytest.raises(positions.Unreadable) as raised:
            ask(gate, root)
        assert "of the canonical form 9, which this version" in str(raised.value)
    root = project(tmp_path / "none")
    edit(root, DIRECT, drop("verdicts", "viability", "fingerprint"))
    for gate in (PASS_FEASIBILITY, SHORTLIST):
        with pytest.raises(positions.Unreadable) as raised:
            ask(gate, root)
        assert "the verdict on viability keeps no fingerprint that reads as one" in str(
            raised.value
        )
    edit(root, DIRECT, drop("traction", "first-stage", "target"))
    assert "needs the first stage's target" in refusal(PASS_FEASIBILITY, root)


def test_a_canvas_that_does_not_read_leaves_every_move_untold(tmp_path: Path) -> None:
    root = project(tmp_path)
    unread_canvas(root)
    for gate in (PASS_DESIRABILITY, SHELVE):
        with pytest.raises(positions.Unreadable):
            ask(gate, root)


# --- the gate on a shelving ---------------------------------------------------------------------


def test_a_variant_without_an_outcome_or_shortlisted_may_be_shelved(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert passes(SHELVE, root)
    edit(root, DIRECT, NO_OUTCOME)
    assert ask(SHELVE, root) == positions.Answer(
        True, "the variant may be shelved: it has no outcome yet, and a shelving records its reason"
    )


def test_a_shelving_records_its_reason(tmp_path: Path) -> None:
    root = project(tmp_path)
    shelved = {"kind": "shelved", "reason": "Too few parents plan", "by": "A", "when": "2026-10-09"}
    edit(root, DIRECT, put("outcome", shelved))
    assert passes(SHELVE, root)
    edit(root, DIRECT, put("outcome", "reason", "  "))
    assert refusal(SHELVE, root) == (
        "the canvas records the variant shelved without a reason: a shelving says why"
    )
    assert stage(root) == positions.Position(
        positions.SHELVED, "the person shelved the variant on 2026-10-09"
    )


def test_a_split_variant_is_never_shelved(tmp_path: Path) -> None:
    root = project(tmp_path)
    split = {"kind": "split", "into": ["[canvas:meal-plan--a]"], "by": "A", "when": "2026-10-09"}
    edit(root, DIRECT, put("outcome", split))
    assert (
        refusal(SHELVE, root) == "the variant is split, which is final: no split variant is shelved"
    )


def test_an_outcome_the_files_cannot_read_leaves_the_shelving_untold(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("outcome", "kind", "parked"))
    with pytest.raises(positions.Unreadable):
        ask(SHELVE, root)


# --- the split's predicate, which the check shares ----------------------------------------------


def test_a_split_names_other_variants_each_of_which_comes_from_it() -> None:
    comes = "[canvas:meal-plan--direct]"
    going_on = {"id": "meal-plan--a", "comes-from": comes}
    assert gates.split(SUBJECT, [(0, going_on)]) == []
    (other,) = gates.split(SUBJECT, [(0, {"id": "meal-plan--b"}), (1, going_on)])
    assert other.pointer == "/outcome/into/0"
    assert "`meal-plan--b`, which does not name `meal-plan--direct` as the variant" in other.message
    (itself,) = gates.split(SUBJECT, [(2, {"id": SUBJECT, "comes-from": comes})])
    assert itself.pointer == "/outcome/into/2"
    assert "the variant is split into itself, `meal-plan--direct`" in itself.message


# --- answering the engine -----------------------------------------------------------------------


def test_the_engine_reads_one_json_object_or_no_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = project(tmp_path)
    monkeypatch.chdir(root)
    argv = [SUBJECT, "--json"]
    assert positions.answer_detection(argv, "detect", "", positions.desk_stage_of) == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "shortlisted",
        "reason": "the person shortlisted the variant on 2026-10-08, which outranks its verdicts",
    }
    assert positions.answer_gate(argv, "shelve", "", SHELVE) == 0
    answer = json.loads(capsys.readouterr().out)
    assert answer["result"] is True
    unread_canvas(root)
    assert positions.answer_gate(argv, "shelve", "", SHELVE) == positions.NO_ANSWER
    said = capsys.readouterr()
    assert said.out == ""
    assert said.err.startswith(f"shelve: the canvas at `{DIRECT}` cannot be read")
    no_variant = ["meal-plan", "--json"]
    assert (
        positions.answer_detection(no_variant, "detect", "", positions.desk_stage_of)
        == positions.NO_ANSWER
    )
    assert "`meal-plan` is no variant's id" in capsys.readouterr().err
