"""A cycle, as the commands that plan it, change its plan, suspend it, resume it and review
it write it (lean-business DEC-002 points 11 to 13; DEC-003 points 4 and 5).

- **The cycle** (`open_cycle`): its file read round trip from the write, refused where the
  id is no cycle's or the file does not exist.
- **The plan's flags** (`plan_flags`), one for each part of the plan, a repeated part
  repeating its flag: the variants it explores, its window's first day and its days, its
  objective and key results, `--key-result <variant>:<step>:<target>`, and its constraint.
  Planning gives each; a change gives the parts it changes, each replacing the part whole,
  and leaves the others as they are.
- **The plan laid** (`lay_plan`). A variant the plan names is shortlisted, as the process
  engine places it, since a cycle explores only what the desk let through (DEC-002 point
  11). The rest of the plan's rules are the check's, which every write is held to: a goal
  set first, one undecided cycle at a time, windows that do not overlap, a key result for
  each variant explored and none for another, and each experiment's variant explored.
- **Who planned it, and its fingerprint** (`stamp`): who first planned it and the day, who
  changed it last and the day, and the plan's fingerprint over all of it, taken again with
  each change while the cycle is planned (DEC-002 points 11 and 13).
- **A suspension's rules** (`suspension_breaks`): each rule the suspension a command records,
  or resumes, breaks, through the predicate the check shares (`suspensions.of_cycle`), under
  the acts the cycle's suspensions bear on as the files stand (`acts.bearing_on`), so the
  command refuses the suspension it records where the check would find the break at it
  (DEC-002 point 12).
- **What a suspension moves** (`moved`): where the window, and the time box of each of the
  cycle's experiments not yet decided, fall before a change of its suspensions and after
  it, each worked out by the one predicate the check and the status share (`timeline`);
  and each experiment that had started by a suspension's first day, which keeps its dates.
- **A suspension in words** (`away`), as the review and the status show it: its days, its
  reason and the day it was recorded, so one recorded late stands apart.
- **Each key in its place** (`ORDER`, `SUSPENSION_ORDER`).
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from ruamel.yaml.comments import CommentedMap

from _lib import (
    acting,
    acts,
    canvases,
    editing,
    experiments,
    fingerprint,
    gates,
    ids,
    model,
    positions,
    timeline,
)
from _lib import engine as engines
from _lib import suspensions as rules
from _lib.experiments import a_day
from _lib.reading import day
from _lib.timeline import Span, span_text
from _lib.writes import Files, Refused

#: A cycle's keys, in the order the schema's reference instance writes them.
ORDER = (
    "pkit_schema",
    "schema_version",
    "id",
    "variants",
    "window",
    "objective",
    "constraint",
    "planned",
    "suspensions",
    "review",
)

#: A suspension's keys, in the order the schema writes them.
SUSPENSION_ORDER = ("reason", "first-day", "by", "when", "resumed")

#: The days a window holds where the plan gives none (DEC-002 point 11).
DAYS = 90

#: The most days a window holds: ten years, far beyond any cycle the method sizes, and well
#: short of the calendar's last day, where the days worked out from a window run out.
MOST_DAYS = 3650

#: The flags of the plan's parts, by their dest.
PLAN_FLAGS = (
    "variants",
    "start",
    "days",
    "objective",
    "key_results",
    "constraint_step",
    "constraint_evidence",
)


@dataclass
class Cycle:
    """A cycle in a write: its path, its file round trip, and its id."""

    rel: str
    doc: editing.Doc
    id: str

    @property
    def data(self) -> CommentedMap:
        return self.doc.data

    @property
    def idea(self) -> str:
        return ids.idea_of(self.id)

    def plain(self) -> Mapping[str, Any]:
        """What the cycle means as the write leaves it so far, read as the check reads it."""
        read = self.doc.plain()
        return read if isinstance(read, Mapping) else {}


def cycle_id(given: str) -> str:
    """`given`, refused where it is no cycle's id, `<idea>--<cycle>`."""
    if not ids.is_idea_qualified(given):
        raise Refused(
            f"`{given}` is no cycle's id: a cycle is named `<idea>--<cycle>`, such as "
            f"`meal-plan--first`"
        )
    return given


def open_cycle(files: Files, given: str) -> Cycle:
    """The cycle `given`, as the write `files` leaves it so far. Raises Refused where the id
    is no cycle's, or where its file does not exist."""
    cycle = cycle_id(given)
    rel = files.path("cycle", cycle)
    doc = files.read(rel)
    if doc is None:
        raise Refused(
            f"there is no cycle `{cycle}`: `{rel}` does not exist; `pkit lean plan-cycle "
            f"{cycle} ...` plans it"
        )
    return Cycle(rel, doc, cycle)


# --- the plan's flags -------------------------------------------------------------------------


def plan_flags(parser: argparse.ArgumentParser, *, first: bool) -> None:
    """Add a flag for each part of the plan, each required where `first`, as planning needs
    the whole plan."""
    parser.add_argument(
        "--variant",
        action="append",
        dest="variants",
        required=first,
        metavar="VARIANT",
        help="A shortlisted variant the cycle explores, by its id or its own part; repeat it "
        "for each.",
    )
    parser.add_argument("--start", required=first, help="The window's first day, YYYY-MM-DD.")
    parser.add_argument(
        "--days",
        type=int,
        help=f"The days the window holds, sized to the time you can give it, {MOST_DAYS} at "
        f"most; {DAYS} where none is given.",
    )
    parser.add_argument("--objective", required=first, help="What the cycle sets out to reach.")
    parser.add_argument(
        "--key-result",
        action="append",
        dest="key_results",
        required=first,
        metavar="VARIANT:STEP:TARGET",
        help="A key result: the variant it is taken from, the step of the customer factory "
        "and the number to reach there; repeat it for each, one at least for each variant.",
    )
    parser.add_argument(
        "--constraint-step",
        required=first,
        choices=canvases.FACTORY_STEPS,
        help="The one step of the customer factory the cycle works on.",
    )
    parser.add_argument(
        "--constraint-evidence",
        required=first,
        help="The evidence that the step is the weakest.",
    )


def given(args: argparse.Namespace) -> bool:
    """Whether the flags give any part of the plan."""
    return any(getattr(args, dest) is not None for dest in PLAN_FLAGS)


# --- the plan laid ----------------------------------------------------------------------------


def lay_plan(
    ctx: acting.Context, files: Files, cycle: Cycle, args: argparse.Namespace, *, first: bool
) -> None:
    """Lay each part of the plan the flags give into `cycle`, each replacing the part whole,
    and leave each part no flag gives as it is, even where the file lacks it. The window
    holds `DAYS` days where the flags give none at the plan's `first` laying, its planning,
    and only then. Raises Refused for a part that does not read, or a variant that is not
    shortlisted."""
    data, idea = cycle.data, cycle.idea
    if args.variants is not None:
        named = [variant_of(idea, given) for given in args.variants]
        twice = sorted({v for v in named if named.count(v) > 1})
        if twice:
            raise Refused(f"{', '.join(f'`{v}`' for v in twice)} is given twice")
        for variant in named:
            shortlisted(ctx, files, variant)
        variants = editing.seq(ids.ref(ids.CANVAS, v) for v in named)
        editing.place(data, "variants", variants, ORDER)
    days = args.days if args.days is not None else (DAYS if first else None)
    if args.start is not None or days is not None:
        window = _part(data, "window")
        if args.start is not None:
            editing.place(window, "start", a_day(args.start, "--start"), _WINDOW)
        if days is not None:
            if days < 1:
                raise Refused("--days is one at least: a window holds a day or more")
            if days > MOST_DAYS:
                raise Refused(f"--days is {MOST_DAYS} at most: a window holds ten years at most")
            editing.place(window, "days", days, _WINDOW)
    if args.objective is not None or args.key_results is not None:
        objective = _part(data, "objective")
        if args.objective is not None:
            statement = _words(args.objective, "--objective")
            editing.place(objective, "statement", statement, _OBJECTIVE)
        if args.key_results is not None:
            results = editing.seq(key_result(idea, given) for given in args.key_results)
            editing.place(objective, "key-results", results, _OBJECTIVE)
    if args.constraint_step is not None or args.constraint_evidence is not None:
        constraint = _part(data, "constraint")
        if args.constraint_step is not None:
            editing.place(constraint, "step", args.constraint_step, _CONSTRAINT)
        if args.constraint_evidence is not None:
            evidence = _words(args.constraint_evidence, "--constraint-evidence")
            editing.place(constraint, "evidence", evidence, _CONSTRAINT)


_WINDOW = ("start", "days")
_OBJECTIVE = ("statement", "key-results")
_CONSTRAINT = ("step", "evidence")


def _part(data: CommentedMap, key: str) -> CommentedMap:
    """The plan's part `key`, an empty mapping put in its place where the file holds none."""
    held = data.get(key)
    if not isinstance(held, CommentedMap):
        held = editing.mapping()
        editing.place(data, key, held, ORDER)
    return held


def _words(text: str, flag: str) -> str:
    said = text.strip()
    if not said:
        raise Refused(f"{flag} has words")
    return said


def variant_of(idea: str, given: str) -> str:
    """The id of the variant of `idea` that `given` names: its id whole, or its own part.
    Raises Refused where it is neither, or names a variant of another idea."""
    whole = given if ids.is_idea_qualified(given) else None
    if whole is None and ids.is_segment(given):
        whole = ids.qualify(idea, given)
    if whole is None:
        raise Refused(
            f"`{given}` names no variant: give its id, `<idea>--<variant>`, or its own part"
        )
    if ids.idea_of(whole) != idea:
        raise Refused(f"`{given}` is a variant of another idea, which `{idea}` never names")
    return whole


def key_result(idea: str, given: str) -> CommentedMap:
    """The key result `given` writes, `<variant>:<step>:<target>`. Raises Refused where it
    does not read so."""
    parts = given.split(":")
    if len(parts) != 3:
        raise Refused(
            f"the key result `{given}` is not `<variant>:<step>:<target>`, such as "
            f"`direct:retention:40`"
        )
    variant, step, target = parts
    if step not in canvases.FACTORY_STEPS:
        raise Refused(
            f"the key result `{given}` names `{step}`, no step of the customer factory: one "
            f"of {', '.join(canvases.FACTORY_STEPS)}"
        )
    try:
        reached = float(target)
    except ValueError as exc:
        raise Refused(f"the key result `{given}` names `{target}`, which is no number") from exc
    return editing.mapping(
        [
            ("variant", ids.ref(ids.CANVAS, variant_of(idea, variant))),
            ("metric", step),
            ("target", editing.number(reached)),
        ]
    )


def shortlisted(ctx: acting.Context, files: Files, variant: str) -> None:
    """Refuse a variant that is not shortlisted, as the process engine places it: a cycle
    explores only a variant the desk let through (DEC-002 point 11)."""
    if not files.exists(files.path("canvas", variant)):
        raise Refused(f"there is no variant `{variant}`")
    state = acting.position(ctx, engines.DESK, variant).state
    if state != positions.SHORTLISTED:
        raise Refused(
            f"`{variant}` stands {state}, not shortlisted: a cycle explores only a "
            f"shortlisted variant, `pkit lean shortlist {variant}`"
        )


# --- who planned it, and its fingerprint ------------------------------------------------------


def stamp(ctx: acting.Context, cycle: Cycle) -> None:
    """Record who planned the cycle and the day: who first planned it and when, kept where
    it was planned before, and who changed it last and when; then the plan's fingerprint,
    taken over the plan and that record (DEC-002 point 11)."""
    held = cycle.data.get("planned")
    first = held.get("first") if isinstance(held, Mapping) else None
    if not isinstance(first, CommentedMap):
        first = editing.mapping([("by", ctx.who), ("when", ctx.on)])
    planned = editing.mapping([("first", first), ("by", ctx.who), ("when", ctx.on)])
    editing.place(cycle.data, "planned", planned, ORDER)
    plain = cycle.plain()
    planned["fingerprint"] = canvases.fingerprint_data(lambda: fingerprint.of_plan(plain))


def words(plan: Mapping[str, Any]) -> str:
    """The plan, in words: its window, the variants it explores and its objective."""
    window = plan.get("window")
    start = window.get("start") if isinstance(window, Mapping) else None
    days = window.get("days") if isinstance(window, Mapping) else None
    explored = gates.explored(plan)
    objective = plan.get("objective")
    statement = objective.get("statement") if isinstance(objective, Mapping) else None
    return (
        f"{days} days from {start}, exploring {', '.join(f'`{v}`' for v in explored)}, toward "
        f'"{statement}"'
    )


def started(plan: Mapping[str, Any], on: date) -> str | None:
    """The warning a plan gives where its window has started by `on`, or None: its plan is
    frozen from its first day."""
    window = timeline.cycle_window(plan)
    if window is None or window.start is None or window.start > on:
        return None
    return (
        f"warning: its window started on {window.start}, by today, {on}, so its plan is frozen "
        f"from now"
    )


# --- a suspension -----------------------------------------------------------------------------


def suspension_breaks(files: Files, cycle: Cycle, index: int) -> list[str]:
    """Each rule the suspension at place `index` of `cycle`'s list, as the write leaves it
    so far, breaks, in words: through the predicate the check shares
    (`suspensions.of_cycle`), under the acts the cycle's suspensions bear on as the files
    stand (`acts.bearing_on`). Where two suspensions together break a rule, the break is the
    one recorded last, which a command appends, so a break found at another place is not
    this command's to refuse."""
    held = experiments.read_idea(files, cycle.idea)
    own = ids.own(cycle.id)
    on_file = next((c for c in held.cycles if c.own == own), None) if held is not None else None
    bearing = acts.bearing_on(held, on_file) if held is not None and on_file is not None else []
    found = rules.of_cycle(cycle.plain(), bearing)
    return list(dict.fromkeys(each.message for each in found if each.index == index))


def moved(
    files: Files, cycle: Cycle, was: Mapping[str, Any], *, since: date | None = None
) -> list[str]:
    """What a change to `cycle`'s suspensions moves, in words (DEC-002 point 12): where its
    window falls with the suspensions `was`, the cycle before the change, holds, and where it
    falls as the write leaves it; the same of each time box that moves, of its experiments
    declared and not decided; and, where `since` is the first day of a suspension it
    records, each such experiment whose time box had started by then and not ended, which
    keeps its dates."""
    written = cycle.plain()
    lines: list[str] = []
    before, after = timeline.cycle_window(was), timeline.cycle_window(written)
    if before is not None and after is not None and before != after:
        lines.append(f"Its window: {span_text(before)} before this, {span_text(after)} after it.")
    held = experiments.read_idea(files, cycle.idea)
    for experiment in held.experiments_of(cycle.id) if held is not None else []:
        data = experiment.data
        if not model.declared(data) or isinstance(data.get("decision"), Mapping):
            continue
        box_before = timeline.experiment_time_box(data, was)
        box_after = timeline.experiment_time_box(data, written)
        if box_before is None or box_after is None:
            continue
        named = data.get("id", ids.qualify(cycle.idea, experiment.own))
        if box_before != box_after:
            lines.append(
                f"`{named}`'s time box: {span_text(box_before)} before this, "
                f"{span_text(box_after)} after it."
            )
        elif since is not None and _running_on(box_after, since):
            lines.append(
                f"`{named}` had started by {since}, so it keeps its time box, "
                f"{span_text(box_after)}: the world went on answering it, and its result "
                f"waits for you once it is due."
            )
    return lines


def _running_on(box: Span, when: date) -> bool:
    return box.start is not None and box.start < when and (box.end is None or when <= box.end)


def away(entry: Mapping[str, Any]) -> str:
    """A suspension of a cycle's list, in words, as the review and the status show it: its
    days, its reason, and the day it was recorded, with how long after its first day, so one
    recorded late stands apart from one recorded as it began (DEC-002 point 12). Each value
    that does not read is said not to, rather than printed as the file holds it."""
    first, recorded = day(entry.get("first-day")), day(entry.get("when"))
    resumption = entry.get("resumed")
    resumed = day(resumption.get("day")) if isinstance(resumption, Mapping) else None
    if first is not None and resumed is not None:
        span = f"from {first} until {resumed}, {_days((resumed - first).days)}"
    elif isinstance(resumption, Mapping):
        span = f"from {_day_said(first)} until {_day_said(resumed)}"
    else:
        span = f"from {_day_said(first)}, ongoing"
    noted = f"recorded on {_day_said(recorded)}"
    if first is not None and recorded is not None and recorded > first:
        noted += f", {_days((recorded - first).days)} after its first day"
    reason = entry.get("reason")
    said = reason if isinstance(reason, str) else "a reason that cannot be read"
    return f"{span}: {said}; {noted}"


def _day_said(when: date | None) -> str:
    return str(when) if when is not None else "a day that cannot be read"


def suspensions_of(cycle: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    """The suspensions a cycle's file lists that read as suspensions, in its order."""
    listed = cycle.get("suspensions")
    return [s for s in listed if isinstance(s, Mapping)] if isinstance(listed, list) else []


def _days(count: int) -> str:
    return "1 day" if count == 1 else f"{count} days"
