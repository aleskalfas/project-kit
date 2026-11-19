"""The canonical form, and the fingerprints taken over it (lean-business DEC-002 point 13).

A *fingerprint* is a digest of the data a judgement judged or a declaration fixed, kept
with it: `{form: <the canonical form's version>, sha256: <hex>}`. It shows, from the working
tree alone, that a declaration was edited after it was declared, or that a verdict's canvas
or goal has changed since.

**Form 1** has two parts, what each kind covers and how the covered data becomes text.

- **What each covers**, read from the files as values, never bytes:
  - a verdict on `desirability`: the canvas's customer segments, early adopters, existing
    alternatives, problems and unique value propositions (DEC-003 point 2);
  - a verdict on `viability`: the revenue streams, the estimate's inputs and the goal;
  - a verdict on `feasibility`: the traction target and the goal;
  - a shortlisting: every box, the estimate's inputs, the traction target and the goal;
  - a declaration: every field of the experiment but its binding (`pkit_schema`,
    `schema_version`) and what is recorded after it is declared (`declared`, `stopped`,
    `result`, `decision`);
  - a cycle's plan: its window as declared, its variants, its objective and its
    constraint, never its suspensions.

  The goal counts by its content alone, its `revenue` and `years`, never who set it or
  when. So the covered data is what the person modelled, never the verdicts, outcomes
  and fingerprints kept beside it, nor a file's binding. The covered data names what it
  covers (`of`), so one kind's fingerprint never stands for another's.
- **Its text**: JSON with no space between tokens, each mapping's keys in the order of
  their characters' code points, every character of a string as itself but those JSON
  must escape, a number that is whole as an integer and any other in its shortest form
  that reads back the same. A key whose value is null, an empty list or an empty mapping
  counts as no key, as an absent box counts as an empty one. A number that is not finite
  has no text. The fingerprint's `sha256` is the SHA-256 of that text as UTF-8.

So a change of layout, key order, quoting or comments makes nothing stale. A change to
the form, or to the schemas that moves a covered field, is a new form: a release takes the
fingerprints again through the capability's migration, which first checks each under the
form it was taken with (`compare`). Every form the capability shipped stays here.

Its limit: a fingerprint lies in the file it guards, so an edit that takes it again by
hand passes. Version control shows such an edit; the check cannot.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

#: The canonical form this version takes fingerprints with.
FORM = 1

#: Every form this version can check a fingerprint under.
FORMS = (1,)

#: The desk steps, in the order the method judges them (DEC-003 point 2).
STEPS = ("desirability", "viability", "feasibility")

#: The canvas's boxes, as its schema names them.
BOXES = (
    "customer-segments",
    "early-adopters",
    "problem",
    "existing-alternatives",
    "unique-value-proposition",
    "high-level-concept",
    "solution",
    "channels",
    "revenue-streams",
    "cost-structure",
    "key-metrics",
    "unfair-advantage",
)

#: The boxes each step reviews (DEC-003 point 2). Viability and feasibility judge the goal
#: too, and viability the estimate's inputs, feasibility the traction target.
STEP_BOXES: Mapping[str, tuple[str, ...]] = {
    "desirability": (
        "customer-segments",
        "early-adopters",
        "existing-alternatives",
        "problem",
        "unique-value-proposition",
    ),
    "viability": ("revenue-streams",),
    "feasibility": (),
}

#: An experiment's fields that bind it to its schema, which no fingerprint covers.
BINDING = ("pkit_schema", "schema_version")

#: What is recorded on an experiment once it is declared, which its declaration does not
#: cover.
RECORDED_AFTER = ("declared", "stopped", "result", "decision")

#: A cycle's plan (DEC-002 point 11).
PLAN = ("window", "variants", "objective", "constraint")

#: What a goal counts by.
GOAL_CONTENT = ("revenue", "years")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class FingerprintError(Exception):
    """Data the form has no text for, or a form this version does not know."""


@dataclass(frozen=True)
class Fingerprint:
    """A fingerprint: the form it was taken with and its digest."""

    form: int
    sha256: str

    def as_data(self) -> dict[str, Any]:
        """The fingerprint as a file writes it."""
        return {"form": self.form, "sha256": self.sha256}


# --- the text ---------------------------------------------------------------------------------


def canonical_text(value: Any) -> str:
    """The canonical text of `value` (form 1). Raises FingerprintError for a value it has
    no text for."""
    return json.dumps(
        _normal(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _normal(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            normal = _normal(item)
            if not _empty(normal):
                out[str(key)] = normal
        return out
    if isinstance(value, (list, tuple)):
        return [_normal(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise FingerprintError(f"the number {value!r} is not finite, so it has no text")
        return int(value) if value.is_integer() else value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise FingerprintError(f"a value of the kind {type(value).__name__} has no text")


def _empty(value: Any) -> bool:
    return value is None or value == [] or value == {}


def take(covered: Any, form: int = FORM) -> Fingerprint:
    """The fingerprint of `covered` under `form`. Raises FingerprintError."""
    if form not in FORMS:
        raise FingerprintError(f"no canonical form {form!r} is known to this version")
    text = canonical_text(covered)
    return Fingerprint(form, hashlib.sha256(text.encode("utf-8")).hexdigest())


# --- what each kind covers --------------------------------------------------------------------


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def goal_content(goal: object) -> dict[str, Any] | None:
    """What a goal counts by in a fingerprint: its revenue and its years, or None where the
    idea has no goal."""
    if not isinstance(goal, Mapping):
        return None
    return {key: goal.get(key) for key in GOAL_CONTENT}


def _boxes(canvas: object, names: tuple[str, ...]) -> dict[str, Any]:
    boxes = _mapping(_mapping(canvas).get("boxes"))
    return {name: boxes.get(name) for name in names}


def verdict_covers(step: str, canvas: object, goal: object, form: int = FORM) -> dict[str, Any]:
    """What a verdict on `step` covers under `form`. Raises FingerprintError for a step the
    method does not judge."""
    _known(form)
    if step not in STEPS:
        raise FingerprintError(f"`{step}` is no desk step")
    covered: dict[str, Any] = {"of": f"verdict:{step}", "boxes": _boxes(canvas, STEP_BOXES[step])}
    if step == "viability":
        covered["viability"] = _mapping(canvas).get("viability")
    if step == "feasibility":
        covered["traction"] = _mapping(canvas).get("traction")
    if step != "desirability":
        covered["goal"] = goal_content(goal)
    return covered


def shortlisting_covers(canvas: object, goal: object, form: int = FORM) -> dict[str, Any]:
    """What a shortlisting covers under `form`."""
    _known(form)
    return {
        "of": "shortlisting",
        "boxes": _boxes(canvas, BOXES),
        "viability": _mapping(canvas).get("viability"),
        "traction": _mapping(canvas).get("traction"),
        "goal": goal_content(goal),
    }


def declaration_covers(experiment: object, form: int = FORM) -> dict[str, Any]:
    """What an experiment's declaration covers under `form`: its declared fields."""
    _known(form)
    skipped = (*BINDING, *RECORDED_AFTER)
    fields = {key: value for key, value in _mapping(experiment).items() if key not in skipped}
    return {"of": "declaration", "fields": fields}


def plan_covers(cycle: object, form: int = FORM) -> dict[str, Any]:
    """What a cycle's plan covers under `form`."""
    _known(form)
    data = _mapping(cycle)
    return {"of": "plan", **{key: data.get(key) for key in PLAN}}


def _known(form: int) -> None:
    if form not in FORMS:
        raise FingerprintError(f"no canonical form {form!r} is known to this version")


def of_verdict(step: str, canvas: object, goal: object, form: int = FORM) -> Fingerprint:
    """The fingerprint a verdict on `step` takes."""
    return take(verdict_covers(step, canvas, goal, form), form)


def of_shortlisting(canvas: object, goal: object, form: int = FORM) -> Fingerprint:
    """The fingerprint a shortlisting takes."""
    return take(shortlisting_covers(canvas, goal, form), form)


def of_declaration(experiment: object, form: int = FORM) -> Fingerprint:
    """The fingerprint an experiment's declaration takes."""
    return take(declaration_covers(experiment, form), form)


def of_plan(cycle: object, form: int = FORM) -> Fingerprint:
    """The fingerprint a cycle's plan takes."""
    return take(plan_covers(cycle, form), form)


# --- checking a fingerprint kept ----------------------------------------------------------------

#: What `compare` finds.
MATCHES = "matches"
DIFFERS = "differs"
UNKNOWN_FORM = "unknown-form"
UNREADABLE = "unreadable"


def read(stored: object) -> Fingerprint | None:
    """The fingerprint a file keeps, or None where it keeps none that reads as one."""
    if not isinstance(stored, Mapping):
        return None
    form, digest = stored.get("form"), stored.get("sha256")
    if isinstance(form, bool) or not isinstance(form, int) or form < 1:
        return None
    if not isinstance(digest, str) or _SHA256.match(digest) is None:
        return None
    return Fingerprint(form, digest)


def compare(stored: object, taken: Callable[[int], Fingerprint]) -> str:
    """Whether the fingerprint a file keeps, `stored`, still matches the data it covers,
    taken again under the form it names by `taken(form)`: `MATCHES`, `DIFFERS`,
    `UNKNOWN_FORM` where this version knows no such form, or `UNREADABLE` where `stored`
    is no fingerprint. Raises FingerprintError where the covered data has no text."""
    kept = read(stored)
    if kept is None:
        return UNREADABLE
    if kept.form not in FORMS:
        return UNKNOWN_FORM
    return MATCHES if taken(kept.form) == kept else DIFFERS
