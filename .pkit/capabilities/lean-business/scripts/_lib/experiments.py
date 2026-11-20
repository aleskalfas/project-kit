"""An experiment, as the experiment path's commands read and change it (lean-business DEC-002
points 9 and 10; DEC-003 points 3 and 5; DEC-001 point 3).

- **The experiment** (`open_experiment`): its file read round trip from the write, refused
  where the id is no experiment's or the file does not exist.
- **Frozen once declared** (`unfrozen`): a draft's fields, its estimates and its file
  change only before its declaration, since a declaration is frozen and a correction comes
  as a new experiment (DEC-002 point 9).
- **What it names** (`assumption_ref`, `cycle_ref`, `assumption_held`, `cycle_held`): the
  assumption it tests and the cycle it runs in, each read within the experiment's idea as
  every command reads a name (`naming.named`), and each refused where it is another idea's
  or nothing holds it.
- **Its cycle, suspended** (`refuse_if_suspended`, `suspended_warning`). Nothing is recorded
  on an experiment of a suspended cycle until the person resumes it (DEC-003 point 3): an
  act on it is refused, naming `resume`, and a draft's change is warned of. Where the cycle
  stands is the process engine's.
- **The idea as its files stand** (`read_idea`), its experiments among them, which an
  assumption's commands and a cycle's read too.
- **A day a flag gives** (`a_day`), as a time box's days and a window's first day are.
- **Each key in its place** (`ORDER`): a key a command adds lands where the schema's
  reference instance writes it (`editing.place`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from ruamel.yaml.comments import CommentedMap

from _lib import acting, editing, ids, layout, listing, naming, positions
from _lib import engine as engines
from _lib.engine import EngineFailed
from _lib.model import IdeaModel, Pools
from _lib.reading import day
from _lib.writes import Files, Refused

#: An experiment's keys, in the order the schema's reference instance writes them.
ORDER = (
    "pkit_schema",
    "schema_version",
    "id",
    "assumption",
    "cycle",
    "kind",
    "learn",
    "stopping-rule",
    "fit",
    "action",
    "metric",
    "expected",
    "source",
    "effects",
    "control",
    "start",
    "end",
    "authors",
    "estimates",
    "declared",
    "stopped",
    "result",
    "decision",
)

#: The fields each kind declares, which an experiment of the other kind holds none of
#: (DEC-002 point 9).
DECLARES = {
    "generative": ("learn", "stopping-rule", "fit"),
    "evaluative": ("action", "metric", "expected", "source", "effects", "control"),
}


@dataclass
class Experiment:
    """An experiment in a write: its path, its file round trip, and its id."""

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
        """What the experiment means as the write leaves it so far, read as the check reads
        it."""
        read = self.doc.plain()
        return read if isinstance(read, Mapping) else {}


def experiment_id(given: str) -> str:
    """`given`, refused where it is no experiment's id, `<idea>--<experiment>`."""
    if not ids.is_idea_qualified(given):
        raise Refused(
            f"`{given}` is no experiment's id: an experiment is named `<idea>--<experiment>`, "
            f"such as `meal-plan--landing-page`"
        )
    return given


def open_experiment(files: Files, given: str) -> Experiment:
    """The experiment `given`, as the write `files` leaves it so far. Raises Refused where
    the id is no experiment's, or where its file does not exist."""
    experiment = experiment_id(given)
    rel = files.path("experiment", experiment)
    doc = files.read(rel)
    if doc is None:
        raise Refused(
            f"there is no experiment `{experiment}`: `{rel}` does not exist; `pkit lean "
            f"new-experiment {experiment} --kind generative|evaluative` creates it"
        )
    return Experiment(rel, doc, experiment)


def unfrozen(experiment: Experiment, what: str) -> None:
    """Refuse `what` on an experiment already declared, whose declaration is frozen."""
    declared = experiment.plain().get("declared")
    if not isinstance(declared, Mapping):
        return
    raise Refused(
        f"`{experiment.id}` was declared on {declared.get('when')}, and a declaration is "
        f"frozen, so {what}: a correction comes as a new experiment, `pkit lean new-experiment`"
    )


# --- what an experiment names -----------------------------------------------------------------


def assumption_ref(files: Files, idea: str, given: str) -> str:
    """The reference to the assumption that `given` names within `idea` (`naming.named`).
    Raises Refused where the name reads as no assumption, or as one of another idea."""
    whole = naming.named(files, naming.ASSUMPTION, given, idea)
    if ids.idea_of(whole) != idea:
        raise Refused(f"`{given}` is an assumption of another idea, which `{idea}` never names")
    return ids.ref(ids.ASSUMPTIONS, whole)


def cycle_ref(files: Files, idea: str, given: str) -> str:
    """The reference to the cycle that `given` names within `idea` (`naming.named`). Raises
    Refused where the name reads as no cycle, or as one of another idea."""
    whole = naming.named(files, naming.CYCLE, given, idea)
    if ids.idea_of(whole) != idea:
        raise Refused(f"`{given}` is a cycle of another idea, which `{idea}` never names")
    return ids.ref(ids.CYCLE, whole)


def assumption_held(files: Files, reference: str) -> None:
    """Refuse the reference to an assumption that its variant's list does not hold."""
    named = ids.parse_ref(reference, ids.ASSUMPTIONS)
    assert named is not None
    variant = ids.qualifier(named.id)
    doc = files.read(files.path("assumptions", variant))
    listed = doc.plain().get("assumptions") if doc is not None else None
    held = (
        [a.get("id") for a in listed if isinstance(a, Mapping)] if isinstance(listed, list) else []
    )
    if named.id not in held:
        raise Refused(
            f"there is no assumption `{named.id}`: `pkit lean add-assumption {variant} "
            f"<statement> --kind <step> --entry <entry>` adds one"
        )


def cycle_held(files: Files, reference: str) -> None:
    """Refuse the reference to a cycle of which no file lies in its place."""
    named = ids.parse_ref(reference, ids.CYCLE)
    assert named is not None
    if not files.exists(files.path("cycle", named.id)):
        raise Refused(
            f"there is no cycle `{named.id}`: `pkit lean plan-cycle {named.id} ...` plans it"
        )


def cycle_named(experiment: Mapping[str, Any]) -> str | None:
    """The id of the cycle the experiment names, or None where it names none."""
    found = ids.parse_ref(experiment.get("cycle"), ids.CYCLE)
    return found.id if found is not None else None


def cycle_plain(files: Files, experiment: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """The cycle the experiment names, as the write `files` leaves it so far and as the check
    reads it, or None where it names none, or no file of it lies in its place. A gate reads
    the suspensions it holds."""
    cycle = cycle_named(experiment)
    doc = files.read(files.path("cycle", cycle)) if cycle is not None else None
    read = doc.plain() if doc is not None else None
    return read if isinstance(read, Mapping) else None


# --- its cycle, suspended ---------------------------------------------------------------------


def refuse_if_suspended(ctx: acting.Context, experiment: Mapping[str, Any], what: str) -> None:
    """Refuse `what`, an act of the person's on the experiment, where its cycle is
    suspended, naming the move that resumes it (DEC-003 point 3). Raises Refused too where
    the engine cannot tell where the cycle stands."""
    cycle = cycle_named(experiment)
    if cycle is None:
        return
    if acting.position(ctx, engines.CYCLE, cycle).state == positions.SUSPENDED:
        raise Refused(
            f"its cycle, `{cycle}`, is suspended, and nothing is recorded on its experiments "
            f"until you resume it, `pkit lean resume {cycle}`, so {what} waits until then"
        )


def suspended_warning(ctx: acting.Context, experiment: Mapping[str, Any]) -> str | None:
    """The warning a draft's change gives where its cycle is suspended, or None: nothing is
    declared or recorded on it until the person resumes the cycle. Where the engine cannot
    tell, there is nothing to warn of, since a draft's content waits on no position."""
    cycle = cycle_named(experiment)
    if cycle is None:
        return None
    try:
        found = ctx.engine.status(engines.CYCLE, cycle)
    except EngineFailed:
        return None
    if found.state != positions.SUSPENDED:
        return None
    return (
        f"warning: its cycle, `{cycle}`, is suspended: nothing is declared or recorded on the "
        f"draft until you resume it, `pkit lean resume {cycle}`"
    )


# --- the idea ---------------------------------------------------------------------------------


def read_idea(files: Files, idea: str) -> IdeaModel | None:
    """The idea `idea` as its files stand, before the write `files`, or None where the
    location holds no file of it. Raises Refused where its files cannot be read."""
    try:
        contents = layout.read(files.root, files.location, idea)
    except (listing.ListingFailed, layout.IdRefused) as exc:
        raise Refused(f"the idea's files cannot be read: {exc}") from exc
    found = contents.ideas.get(idea)
    return IdeaModel(found, Pools.of(contents)) if found is not None else None


def a_day(given: str, flag: str) -> date:
    """The day `given` writes, `YYYY-MM-DD`. Raises Refused where it names none."""
    found = day(given)
    if found is None:
        raise Refused(f"{flag} is a day of the calendar, YYYY-MM-DD, and `{given}` names none")
    return found
