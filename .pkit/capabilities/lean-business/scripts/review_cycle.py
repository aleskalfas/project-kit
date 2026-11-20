#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — review-cycle: record a cycle's review, what each key result
reached, the variant that did best, and the person's decision for it, persevere, pivot or
pause (lean-business DEC-002 point 11; DEC-003 points 4 and 5).

Deciding is the person's move, on `decide`, out of review, so it takes their word and
records who decided and the day. The review gives a number reached for each key result, in
the objective's order, and names the winning variant: the one the cycle explored, where it
explored one, else the one the person names. Its reasons are the person's words, and a pivot
names at least one decided experiment as its evidence.

Before it asks, the command says the progress report the decision rests on: each key
result against its target, met or missed; each suspension, its days, its reason and the day
it was recorded, so one recorded late stands apart; and each experiment of the cycle still
undecided, which the decision does not wait for. Persevering where the winning variant
missed the objective is the person's call, and draws a warning, since the method perseveres
where the objective was met.

The review is held to the gate the check shares (`gates.deciding_cycle`), and the process
engine is asked whether the move may be taken, before anything is written. After the write,
the cycle moves to decided, and the write is undone where the engine refuses it.

Refused: a cycle suspended, which is resumed first; one planned or running, whose window
has not ended; one decided already; a count of numbers reached that differs from the key
results; a winner the cycle did not explore, or none named where it explored several; a
persevere or a pivot for a variant shelved or split; and a pivot with no decided experiment
as its evidence.

Usage:
  pkit lean review-cycle <cycle> --reached <number>... [--winning <variant>]
                         --decision persevere|pivot|pause --reasons <text>
                         [--evidence <experiment>]... [--person-decided]

Exit codes:
  0  decided
  1  refused, or answered no: nothing was written
  2  usage
  3  nobody could be asked: the question is printed, and nothing was written
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import (
    acting,
    cycles,
    editing,
    engine,
    experiments,
    gates,
    ids,
    naming,
    positions,
    readings,
    timeline,
    writes,
)
from _lib.acting import Context
from _lib.cycles import Cycle
from _lib.timeline import span_text
from _lib.writes import Refused

TRIGGER = "decide"


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean review-cycle",
        description="Record a cycle's review, and your decision for the variant that did best.",
    )
    made.add_argument("cycle", help="The cycle, by its id, `<idea>--<cycle>`, or its own part.")
    made.add_argument(
        "--reached",
        action="append",
        required=True,
        metavar="NUMBER",
        help="What a key result reached; repeat it for each, in the plan's order.",
    )
    made.add_argument(
        "--winning",
        help="The variant that did best, by its id or its own part; the one the cycle "
        "explored where it explored one.",
    )
    made.add_argument(
        "--decision",
        required=True,
        choices=positions.DECISIONS,
        help="What you decide for the winning variant.",
    )
    made.add_argument("--reasons", required=True, help="Why, in your words.")
    made.add_argument(
        "--evidence",
        action="append",
        metavar="EXPERIMENT",
        help="A decided experiment the decision rests on, by its id or its own part; repeat "
        "it for each. A pivot names one at least.",
    )
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    reasons = str(args.reasons).strip()
    if not reasons:
        raise Refused("a review says why: give --reasons the person's words")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    cycle = cycles.open_cycle(files, naming.named(files, naming.CYCLE, str(args.cycle)))
    subject, idea = cycle.id, cycle.idea
    before = acting.position(ctx, engine.CYCLE, subject)
    plan = cycle.plain()
    _in_review(subject, before.state, plan)
    reached = _reached(args.reached, plan)
    winner = _winner(idea, args.winning, gates.explored(plan))
    evidence = [_experiment(files, idea, given) for given in args.evidence or []]
    decision = str(args.decision)
    review = editing.mapping(
        [
            ("reached", editing.seq(reached)),
            ("winning", ids.ref(ids.CANVAS, winner)),
            ("decision", decision),
            ("reasons", reasons),
            (
                "evidence",
                editing.seq(ids.ref(ids.EXPERIMENT, named) for named, _ in evidence)
                if evidence
                else None,
            ),
            ("by", ctx.who),
            ("when", ctx.on),
        ]
    )
    editing.place(cycle.data, "review", review, cycles.ORDER)
    reviewed = cycle.plain()
    canvas = files.read(files.path("canvas", winner))
    read = canvas.plain() if canvas is not None else None
    refusals = gates.deciding_cycle(
        reviewed,
        ctx.on,
        winning=read if isinstance(read, Mapping) else None,
        evidence=[plain for _, plain in evidence],
    )
    if refusals:
        raise Refused("; ".join(dict.fromkeys(refusal.message for refusal in refusals)))

    def build() -> tuple[writes.Files, str]:
        # Said once the engine opened the move, before the question: the report it rests on.
        for line in _report(files, cycle, reviewed, winner, decision):
            ctx.say(line)
        files.put(cycle.rel, cycle.doc)
        return files, f"Reviewed `{subject}`: {decision} for `{winner}`, because {reasons}"

    acting.person_move(
        ctx, engine.CYCLE, subject, TRIGGER, before, build, decided=args.person_decided
    )


def _in_review(subject: str, state: str | None, plan: Mapping[str, Any]) -> None:
    """Refuse a cycle that is not in review: suspended, planned, running or decided."""
    if state == positions.IN_REVIEW:
        return
    if state == positions.SUSPENDED:
        raise Refused(
            f"`{subject}` is suspended: it is resumed first, `pkit lean resume {subject}`, "
            f"and reviewed once its window has ended"
        )
    if state in (positions.PLANNED, positions.RUNNING):
        window = timeline.cycle_window(plan)
        falls = f": its window falls {span_text(window)}" if window is not None else ""
        raise Refused(
            f"`{subject}` is {positions.CYCLE_STATE_WORDS[state]}, and a cycle is reviewed "
            f"once its window has ended{falls}"
        )
    if state == positions.DECIDED:
        raise Refused(f"`{subject}` is decided already, and a decided cycle takes no act")
    raise Refused(
        f"`{subject}` stands in none of its states, and only a cycle in review is decided"
    )


def _reached(given: Sequence[str], plan: Mapping[str, Any]) -> list[int | float]:
    """The numbers `--reached` gives, one for each key result. Raises Refused for one that
    is no number, or a count that differs from the key results."""
    numbers: list[int | float] = []
    for each in given:
        try:
            numbers.append(editing.number(float(each)))
        except ValueError as exc:
            raise Refused(f"--reached is a number, and `{each}` is none") from exc
    results = _key_results(plan)
    if len(numbers) != len(results):
        raise Refused(
            f"--reached gives {len(numbers)} {'number' if len(numbers) == 1 else 'numbers'}, "
            f"and the objective has {len(results)} key "
            f"{'result' if len(results) == 1 else 'results'}: give it once for each, in the "
            f"plan's order"
        )
    return numbers


def _winner(idea: str, given: str | None, explored: Sequence[str]) -> str:
    """The winning variant: the one `--winning` names, or the one the cycle explored where
    it names none. Raises Refused where it names none and the cycle explored several."""
    if given is not None:
        return cycles.variant_of(idea, given)
    if len(explored) == 1:
        return explored[0]
    raise Refused(
        f"the cycle explored {', '.join(f'`{v}`' for v in explored)}: name the one that did "
        f"best with --winning"
    )


def _experiment(files: writes.Files, idea: str, given: str) -> tuple[str, Mapping[str, Any]]:
    """The experiment of `idea` that `given` names, its id whole or its own part, and what
    its file holds. Raises Refused where it names none of the idea's."""
    whole = given if ids.is_idea_qualified(given) else None
    if whole is None and ids.is_segment(given):
        whole = ids.qualify(idea, given)
    if whole is None or ids.idea_of(whole) != idea:
        raise Refused(
            f"--evidence `{given}` names no experiment of `{idea}`: give its id, "
            f"`<idea>--<experiment>`, or its own part"
        )
    found = experiments.open_experiment(files, whole).plain()
    return whole, found


def _report(
    files: writes.Files,
    cycle: Cycle,
    reviewed: Mapping[str, Any],
    winner: str,
    decision: str,
) -> list[str]:
    """The progress report the decision rests on, in words: each key result against its
    target, each suspension, and each experiment of the cycle still undecided."""
    lines = [f"The progress report of `{cycle.id}`:"]
    review = reviewed.get("review")
    reached = review.get("reached") if isinstance(review, Mapping) else None
    for index, result in enumerate(_key_results(reviewed)):
        if not isinstance(result, Mapping):
            continue
        value = reached[index] if isinstance(reached, list) and index < len(reached) else None
        target = result.get("target")
        met = _met(value, target)
        variant = ids.parse_ref(result.get("variant"), ids.CANVAS)
        lines.append(
            f"  `{variant.id if variant is not None else result.get('variant')}`, "
            f"{result.get('metric')}: reached {value} of {target}, "
            f"{'met' if met else 'missed' if met is False else 'not told'}"
        )
    for entry in cycles.suspensions_of(reviewed):
        lines.append(f"  Suspended {cycles.away(entry)}")
    held = experiments.read_idea(files, cycle.idea)
    for experiment in held.experiments_of(cycle.id) if held is not None else []:
        data = experiment.data
        if isinstance(data.get("decision"), Mapping):
            continue
        outcome = readings.experiment_outcome(data)
        result = (
            f"its result is {positions.OUTCOME_WORDS[outcome]}"
            if outcome is not None
            else "it has no result"
        )
        lines.append(
            f"  `{data.get('id', ids.qualify(cycle.idea, experiment.own))}` is not decided, "
            f"and {result}: the decision does not wait for it"
        )
    if decision == "persevere" and readings.met_objective(reviewed, winner) is False:
        lines.append(
            f"`{winner}` missed the objective, so persevering draws a warning: the method "
            f"perseveres where the objective was met, and a near miss with a clear cause "
            f"stays your call."
        )
    return lines


def _key_results(plan: Mapping[str, Any]) -> list[Any]:
    """The objective's key results as the plan lists them, in its order, as the gate counts
    them."""
    objective = plan.get("objective")
    listed = objective.get("key-results") if isinstance(objective, Mapping) else None
    return list(listed) if isinstance(listed, list) else []


def _met(value: object, target: object) -> bool | None:
    """Whether `value` reached `target`, or None where either is no number."""
    if isinstance(value, bool) or isinstance(target, bool):
        return None
    if isinstance(value, (int, float)) and isinstance(target, (int, float)):
        return value >= target
    return None


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
