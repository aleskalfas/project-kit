#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — draft-experiment: write what a draft of an experiment will
declare, a flag for each field (lean-business DEC-002 point 9).

Content, so it asks nothing and records no who or when; refused once the experiment is
declared, since a declaration is frozen and a correction comes as a new experiment. A flag
sets its field, `--effect` adds one effect each time, and `--clear <field>` takes a field
out. A generative experiment says what it sets out to learn, its stopping rule and its fit,
`--fit <count>/<what it counts>`. An evaluative one says its action, its metric, its
expected outcome, a `--direction` with a `--threshold` or a 90% `--range <low> <high>`,
where that number comes from, the effects known in advance and its control, earlier
`cohorts` or a `split` with the share `--exposed`.

Refused, since the declaring gate refuses each on any day: a time box of more than fourteen
days, or one that ends before it starts; a range whose low is above its high. Refused too: a
field of the other kind, which the experiment's kind forbids; an expected outcome without
its direction and one of a threshold and a range; a split without the share exposed, or a
share without a split. A draft in a suspended cycle is warned of, since nothing is declared
or recorded on it until the cycle resumes.

Usage:
  pkit lean draft-experiment <experiment> [--kind generative|evaluative]
      [--assumption <assumption>] [--cycle <cycle>]
      [--learn <text>] [--stopping-rule <text>] [--fit <count>/<of>]
      [--action <text>] [--metric <step>] [--direction at-least|at-most]
      [--threshold <number> | --range <low> <high>] [--source estimate|traction-target]
      [--effect <text>]... [--control cohorts|split] [--exposed <share>]
      [--start <day>] [--end <day>] [--clear <field>]...

Exit codes:
  0  written
  1  refused: nothing was written
  2  usage
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from ruamel.yaml.comments import CommentedMap, CommentedSeq

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, editing, experiments, gates, positions, writes
from _lib.acting import Context
from _lib.experiments import ORDER
from _lib.reading import day
from _lib.writes import Refused

#: The field each flag sets, by its dest.
SETS = {
    "assumption": "assumption",
    "cycle": "cycle",
    "learn": "learn",
    "stopping_rule": "stopping-rule",
    "fit": "fit",
    "action": "action",
    "metric": "metric",
    "direction": "expected",
    "threshold": "expected",
    "range": "expected",
    "source": "source",
    "effects": "effects",
    "control": "control",
    "exposed": "control",
    "start": "start",
    "end": "end",
}

#: The fields `--clear` takes out.
CLEARABLE = tuple(dict.fromkeys(SETS.values()))

_EXPECTED = ("direction", "threshold", "range")
_CONTROL = ("kind", "exposed")


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean draft-experiment",
        description="Write what a draft of an experiment will declare, a flag for each field.",
    )
    made.add_argument("experiment", help="The experiment's id, `<idea>--<experiment>`.")
    made.add_argument("--kind", choices=positions.KINDS)
    made.add_argument(
        "--assumption",
        help="The assumption it tests, by its id, the part after the idea, or its own part.",
    )
    made.add_argument("--cycle", help="The cycle it runs in, by its id or its own part.")
    generative = made.add_argument_group("a generative experiment")
    generative.add_argument("--learn", help="What it sets out to learn.")
    generative.add_argument(
        "--stopping-rule",
        help="What ends it before its time box does, such as a number of interviews.",
    )
    generative.add_argument(
        "--fit",
        metavar="COUNT/OF",
        help="What counts as fit: the number its result is held against, `/`, and what that "
        "number counts, such as `8/interviews that tell one story`.",
    )
    evaluative = made.add_argument_group("an evaluative experiment")
    evaluative.add_argument("--action", help="The one action it takes.")
    evaluative.add_argument(
        "--metric",
        choices=canvases.FACTORY_STEPS,
        help="The step of the customer factory it measures.",
    )
    evaluative.add_argument(
        "--direction",
        choices=("at-least", "at-most"),
        help="The direction of the expected outcome that counts as success.",
    )
    expected = evaluative.add_mutually_exclusive_group()
    expected.add_argument("--threshold", type=float, help="The expected outcome, as a threshold.")
    expected.add_argument(
        "--range",
        type=float,
        nargs=2,
        metavar=("LOW", "HIGH"),
        help="The expected outcome, as a 90%% range.",
    )
    evaluative.add_argument(
        "--source",
        choices=("estimate", "traction-target"),
        help="Where the expected number comes from.",
    )
    evaluative.add_argument(
        "--effect",
        action="append",
        dest="effects",
        help="An effect known in advance that may move the result, such as a season; repeat it "
        "for each.",
    )
    evaluative.add_argument(
        "--control",
        choices=("cohorts", "split"),
        help="What the result is compared with: earlier cohorts, or a split.",
    )
    evaluative.add_argument(
        "--exposed",
        type=float,
        help="With a split: the share of people exposed, above 0 and below 1.",
    )
    made.add_argument("--start", help="The first day of its time box, YYYY-MM-DD.")
    made.add_argument("--end", help="The last day of its time box, YYYY-MM-DD, fourteen at most.")
    made.add_argument(
        "--clear",
        action="append",
        choices=CLEARABLE,
        metavar="FIELD",
        help=f"Take a field out: one of {', '.join(CLEARABLE)}; repeat it for each.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    setting = {field for dest, field in SETS.items() if getattr(args, dest) is not None}
    clearing = set(args.clear or [])
    if not setting and not clearing and args.kind is None:
        raise Refused("give what the draft changes: --kind, a field's flag or --clear <field>")
    both = sorted(setting & clearing)
    if both:
        raise Refused(f"{_named(both)} is both set and cleared: give one or the other")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    experiment = experiments.open_experiment(files, str(args.experiment))
    experiments.unfrozen(experiment, "its draft no longer changes")
    data = experiment.data
    kind = str(args.kind if args.kind is not None else data.get("kind"))
    _of_its_kind(experiment, kind, setting, clearing, changed=args.kind is not None)
    if args.kind is not None:
        editing.place(data, "kind", args.kind, ORDER)
    for field in clearing:
        data.pop(field, None)
    _set(files, experiment, args)
    _time_box(experiment)
    files.put(experiment.rel, experiment.doc)
    acting.content(ctx, files, f"Changed the draft `{experiment.id}`.")
    warning = experiments.suspended_warning(ctx, experiment.plain())
    if warning is not None:
        ctx.say(warning)


def _of_its_kind(
    experiment: experiments.Experiment,
    kind: str,
    setting: set[str],
    clearing: set[str],
    *,
    changed: bool,
) -> None:
    """Refuse a field of the other kind: one a flag sets, or, where the kind changes, one the
    draft holds and the command does not clear."""
    other = next((k for k in positions.KINDS if k != kind), None)
    if kind not in positions.KINDS or other is None:
        return
    forbidden = experiments.DECLARES[other]
    given = [field for field in forbidden if field in setting]
    if given:
        raise Refused(
            f"{_named(given)} {'is' if len(given) == 1 else 'are'} held by {other} experiments "
            f"alone, and `{experiment.id}` is {kind}"
        )
    if not changed:
        return
    held = [field for field in forbidden if field in experiment.data and field not in clearing]
    if held:
        clears = " ".join(f"--clear {field}" for field in held)
        raise Refused(
            f"`{experiment.id}` holds {_named(held)}, which a {kind} experiment holds none of: "
            f"clear {'it' if len(held) == 1 else 'them'} with the change of kind, `{clears}`"
        )


def _set(files: writes.Files, experiment: experiments.Experiment, args: argparse.Namespace) -> None:
    """Set each field a flag gives."""
    data, idea = experiment.data, experiment.idea
    if args.assumption is not None:
        reference = experiments.assumption_ref(files, idea, str(args.assumption))
        experiments.assumption_held(files, reference)
        editing.place(data, "assumption", reference, ORDER)
    if args.cycle is not None:
        reference = experiments.cycle_ref(files, idea, str(args.cycle))
        experiments.cycle_held(files, reference)
        editing.place(data, "cycle", reference, ORDER)
    for dest, field in (
        ("learn", "learn"),
        ("stopping_rule", "stopping-rule"),
        ("action", "action"),
    ):
        value = getattr(args, dest)
        if value is not None:
            editing.place(data, field, _words(value, f"--{field}"), ORDER)
    if args.fit is not None:
        editing.place(data, "fit", _fit(str(args.fit)), ORDER)
    if args.metric is not None:
        editing.place(data, "metric", args.metric, ORDER)
    if args.direction is not None or args.threshold is not None or args.range is not None:
        _expected(data, args)
    if args.source is not None:
        editing.place(data, "source", args.source, ORDER)
    if args.effects is not None:
        held = data.get("effects")
        effects = held if isinstance(held, CommentedSeq) else editing.seq()
        for given in args.effects:
            effect = _words(given, "--effect")
            if effect not in effects:
                effects.append(effect)
        editing.place(data, "effects", effects, ORDER)
    if args.control is not None or args.exposed is not None:
        _control(data, args)
    for key in ("start", "end"):
        given = getattr(args, key)
        if given is not None:
            editing.place(data, key, experiments.a_day(str(given), f"--{key}"), ORDER)


def _words(text: str, flag: str) -> str:
    said = str(text).strip()
    if not said:
        raise Refused(f"{flag} has words")
    return said


def _fit(given: str) -> CommentedMap:
    """The fit `given` writes, `<count>/<what it counts>`."""
    count, slash, of = given.partition("/")
    if not slash or not of.strip():
        raise Refused(
            f"--fit `{given}` is not `<count>/<what it counts>`, such as `8/interviews that "
            f"tell one story`"
        )
    try:
        number = int(count.strip())
    except ValueError as exc:
        raise Refused(
            f"--fit `{given}` counts `{count.strip()}`, which is no whole number"
        ) from exc
    if number < 1:
        raise Refused(f"--fit `{given}` counts {number}: what counts as fit is one at least")
    return editing.mapping([("count", number), ("of", of.strip())])


def _expected(data: CommentedMap, args: argparse.Namespace) -> None:
    """Set the parts of the expected outcome the flags give: a threshold replaces a range,
    and a range a threshold. Refused where it is left without its direction or without one
    of the two, or with a range whose low is above its high."""
    held = data.get("expected")
    expected = held if isinstance(held, CommentedMap) else editing.mapping()
    if args.direction is not None:
        editing.place(expected, "direction", args.direction, _EXPECTED)
    if args.threshold is not None:
        expected.pop("range", None)
        editing.place(expected, "threshold", editing.number(args.threshold), _EXPECTED)
    if args.range is not None:
        low, high = args.range
        if low > high:
            raise Refused(
                f"--range runs from {editing.number(low)} to {editing.number(high)}, its low "
                f"above its high"
            )
        expected.pop("threshold", None)
        span = editing.mapping([("low", editing.number(low)), ("high", editing.number(high))])
        editing.place(expected, "range", span, _EXPECTED)
    if "direction" not in expected or ("threshold" not in expected and "range" not in expected):
        raise Refused(
            "an expected outcome is a --direction with a --threshold or a --range: give the "
            "part it lacks"
        )
    editing.place(data, "expected", expected, ORDER)


def _control(data: CommentedMap, args: argparse.Namespace) -> None:
    """Set the control the flags give: cohorts take no share exposed, and a split takes
    one, above 0 and below 1."""
    held = data.get("control")
    control = held if isinstance(held, CommentedMap) else editing.mapping()
    if args.control is not None:
        editing.place(control, "kind", args.control, _CONTROL)
        if args.control == "cohorts":
            if args.exposed is not None:
                raise Refused("--exposed is given with a split alone: cohorts expose everyone")
            control.pop("exposed", None)
    if args.exposed is not None:
        if control.get("kind") != "split":
            raise Refused(
                "--exposed is given with a split alone: `--control split --exposed <share>`"
            )
        if not 0 < args.exposed < 1:
            raise Refused(f"--exposed is a share above 0 and below 1, and {args.exposed} is not")
        editing.place(control, "exposed", editing.number(args.exposed), _CONTROL)
    if control.get("kind") == "split" and "exposed" not in control:
        raise Refused("a split names the share of people exposed: `--exposed <share>`")
    editing.place(data, "control", control, ORDER)


def _time_box(experiment: experiments.Experiment) -> None:
    """Refuse a time box the declaring gate refuses on any day: one that ends before it
    starts, or holds more than fourteen days."""
    plain = experiment.plain()
    start, end = day(plain.get("start")), day(plain.get("end"))
    if start is None or end is None:
        return
    held = (end - start).days + 1
    if held < 1:
        raise Refused(f"its time box would end on {end}, before it starts, on {start}")
    if held > gates.TIME_BOX_DAYS:
        raise Refused(
            f"its time box would hold {held} days, {start} through {end}, more than "
            f"{gates.TIME_BOX_DAYS}"
        )


def _named(fields: list[str]) -> str:
    return ", ".join(f"`{field}`" for field in fields)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
