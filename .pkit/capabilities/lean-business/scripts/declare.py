#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — declare: declare an experiment, freezing what it declared
(lean-business DEC-002 point 9; DEC-003 points 3, 5 and 7).

The person's move, on `declare`: it records who declared it and the day, the variant's
shortlisting it rests on, by its fingerprint and its day, and the declaration's own
fingerprint, over every declared field and that record. From then on nothing it declared
changes, and a correction comes as a new experiment. Its time box starting after today
takes it into declared, and starting today straight into running; where it stands after
the write is the process engine's.

Refused, through the predicates the check shares (`gates.declaring`,
`gates.stale_shortlisting`, `gates.unexplored`): a draft that lacks a field its kind needs,
or an estimate; a time box of more than fourteen days, or one that starts before today; a
variant that is not shortlisted, or whose shortlisting is stale; a cycle that does not
explore the variant, or whose window has ended. Refused too: a cycle that is not open,
planned or running, as the process engine places it, and one that is suspended, naming
`resume`. Warned of before it asks: a riskier assumption of the variant, ranked above the
one tested, that no declared experiment has tested.

Usage:
  pkit lean declare <experiment> [--person-decided]

Exit codes:
  0  declared
  1  refused, or answered no: nothing was written
  2  usage
  3  nobody could be asked: the question is printed, and nothing was written
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import (
    acting,
    canvases,
    editing,
    engine,
    experiments,
    fingerprint,
    gates,
    ids,
    positions,
    readings,
    writes,
)
from _lib.acting import Context
from _lib.experiments import ORDER
from _lib.writes import Refused

TRIGGER = "declare"


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean declare",
        description="Declare an experiment, freezing what it declared.",
    )
    made.add_argument("experiment", help="The experiment's id, `<idea>--<experiment>`.")
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    experiment = experiments.open_experiment(files, str(args.experiment))
    subject = experiment.id
    experiments.unfrozen(experiment, "it is not declared again")
    before = acting.position(ctx, engine.EXPERIMENT, subject)
    plain = experiment.plain()
    experiments.refuse_if_suspended(ctx, plain, "its declaration")
    _open(ctx, plain)
    canvas = _canvas(files, plain)
    refusals = _refusals(files, experiment, plain, canvas, ctx.on)
    if refusals:
        raise Refused("; ".join(refusals))
    riskier = _riskier(files, experiment.idea, plain)
    if riskier is not None:
        ctx.say(riskier)

    def build() -> tuple[writes.Files, str]:
        rests_on = fingerprint.shortlisting(canvas) if canvas is not None else None
        if canvas is None or rests_on is None:
            raise Refused(
                "the variant whose assumption it tests keeps no shortlisting that reads whole"
            )
        declared = editing.mapping(
            [
                ("by", ctx.who),
                ("when", ctx.on),
                (
                    "rested-on",
                    editing.mapping(
                        [
                            (
                                "fingerprint",
                                editing.mapping(rests_on.fingerprint.as_data().items()),
                            ),
                            ("when", rests_on.when),
                        ]
                    ),
                ),
            ]
        )
        editing.place(experiment.data, "declared", declared, ORDER)
        recorded = experiment.plain()
        declared["fingerprint"] = canvases.fingerprint_data(
            lambda: fingerprint.of_declaration(recorded)
        )
        files.put(experiment.rel, experiment.doc)
        return files, (
            f"Declared `{subject}`, resting on the shortlisting of `{canvas.get('id')}` "
            f"recorded on {rests_on.when}: its time box runs {plain.get('start')} through "
            f"{plain.get('end')}."
        )

    acting.person_move(
        ctx, engine.EXPERIMENT, subject, TRIGGER, before, build, decided=args.person_decided
    )


def _open(ctx: Context, plain: Mapping[str, Any]) -> None:
    """Refuse a cycle that is not open, planned or running, as the engine places it."""
    cycle = experiments.cycle_named(plain)
    if cycle is None:
        return
    state = acting.position(ctx, engine.CYCLE, cycle).state
    if state not in positions.OPEN:
        raise Refused(
            f"its cycle, `{cycle}`, stands {state}: an experiment is declared only in an open "
            f"cycle, planned or running"
        )


def _canvas(files: writes.Files, plain: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """The canvas of the variant whose assumption the experiment tests, or None where it
    names none, or the variant has no canvas."""
    named = ids.parse_ref(plain.get("assumption"), ids.ASSUMPTIONS)
    if named is None:
        return None
    doc = files.read(files.path("canvas", ids.qualifier(named.id)))
    read = doc.plain() if doc is not None else None
    return read if isinstance(read, Mapping) else None


def _refusals(
    files: writes.Files,
    experiment: experiments.Experiment,
    plain: Mapping[str, Any],
    canvas: Mapping[str, Any] | None,
    on: date,
) -> list[str]:
    """Why the declaring gates refuse the draft today, in words."""
    cycle = experiments.cycle_plain(files, plain)
    found = gates.declaring(
        plain,
        on,
        cycle=cycle,
        canvas=canvas,
        rests_on=fingerprint.shortlisting(canvas) if canvas is not None else None,
    )
    if canvas is not None:
        found += gates.stale_shortlisting(canvas, canvases.goal_of(files, experiment.idea))
    if cycle is not None:
        found += gates.unexplored(plain, cycle)
    return list(dict.fromkeys(refusal.message for refusal in found))


def _riskier(files: writes.Files, idea: str, plain: Mapping[str, Any]) -> str | None:
    """The warning a declaration gives where an assumption of the variant ranked above the
    one it tests is untested, or None."""
    named = ids.parse_ref(plain.get("assumption"), ids.ASSUMPTIONS)
    if named is None:
        return None
    doc = files.read(files.path("assumptions", ids.qualifier(named.id)))
    listed = doc.plain().get("assumptions") if doc is not None else None
    ranked = {
        str(a["id"]): a["rank"]
        for a in (listed if isinstance(listed, list) else [])
        if isinstance(a, Mapping) and isinstance(a.get("id"), str) and _rank(a.get("rank"))
    }
    rank = ranked.get(named.id)
    if rank is None:
        return None
    held = experiments.read_idea(files, idea)
    tested = [e.data for e in held.experiments] if held is not None else []
    untested = [
        assumption
        for assumption, its in sorted(ranked.items(), key=lambda pair: pair[1])
        if its < rank and readings.assumption_outcome(assumption, tested) == readings.UNTESTED
    ]
    if not untested:
        return None
    return (
        f"warning: {', '.join(f'`{a}`' for a in untested)}, ranked riskier than `{named.id}`, "
        f"{'is' if len(untested) == 1 else 'are'} untested: the riskiest assumption is tested "
        f"first"
    )


def _rank(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
