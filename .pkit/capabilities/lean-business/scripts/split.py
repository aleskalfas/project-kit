#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — split: split a variant into variants that each tell one story
of the business (lean-business DEC-003 points 2 and 5; DEC-002 points 4, 5 and 7).

The split is the person's, so it takes their word and records who split the variant and
when, with the variants it went into. It moves the variant from sketched or a verdict's
state into split, which is final. A shortlisted variant is not split.

Each variant it names is created as a copy of this one, to be worked on from there:

- **Its canvas:** the archetype, the authors, the sides, every box's entries, the inputs
  and the traction target, and `comes-from` naming the variant split. Each entry's id, and
  each link to another entry, keeps its own part under the new variant's id. Neither the
  verdicts nor the outcome are copied, since they judged the variant split: the new one is
  judged at the desk afresh.
- **Its assumptions:** each, with its rank, its id and the entry it comes from re-qualified
  the same way.

The copies are new files in the capability's own layout, so the comments of the files they
copy, which speak of the variant split, are not carried over. An error the variant split
holds already, in what a copy takes, the copy would repeat, so the split is refused, naming
the file to fix first.

Each name is the new variant's own part, or its whole id within the same idea. A name is
refused where its variant or its assumptions exist, or where something still names its id
or an id the copy would give, since an id named is never given again.

Usage:
  pkit lean split <variant> --into <variant>... [--person-decided]

Exit codes:
  0  written
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

from _lib import acting, canvases, editing, engine, gates, ids, layout, naming, positions, writes
from _lib.acting import Context
from _lib.writes import Refused

#: The trigger of the desk stage's moves into split.
TRIGGER = "split"

#: What a copy takes of the canvas split: its model and its content, never its verdicts or
#: its outcome, which judged the variant split.
COPIED = ("archetype", "authors", "sides", "boxes", "viability", "traction")

#: An entry's fields that hold an entry's id, its own and the problem it answers; and the
#: one that holds a list of them, a problem's existing alternatives.
ENTRY_ID_FIELDS = ("id", "problem")
ENTRY_IDS_FIELD = "alternatives"


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean split",
        description="Split a variant into variants that each tell one story of the business, "
        "each a copy of it to work on.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument(
        "--into",
        action="append",
        required=True,
        metavar="VARIANT",
        help="A variant it is split into, by its own part or its id; repeat it for each.",
    )
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    variant = canvases.variant_id(str(args.variant))
    idea = ids.idea_of(variant)
    into = [_named(idea, str(given)) for given in args.into]
    twice = sorted({v for v in into if into.count(v) > 1})
    if twice:
        raise Refused(f"{', '.join(f'`{v}`' for v in twice)} is named twice")
    if variant in into:
        raise Refused(
            f"a variant is not split into itself, `{variant}`: it goes on only in the variants "
            f"it is split into"
        )
    before = acting.position(ctx, engine.DESK, variant)
    if before.state in (positions.SHELVED, positions.SPLIT):
        raise Refused(f"`{variant}` is {before.state}, which is final")
    if before.state == positions.SHORTLISTED:
        raise Refused(
            f"`{variant}` is shortlisted, and a variant is split only before it is: from "
            f"sketched or a verdict's state"
        )

    sources: list[str] = []
    copies_written: list[str] = []

    def build() -> tuple[writes.Files, str]:
        files = writes.Files(ctx.root, writes.for_writing(ctx.root))
        canvas = canvases.open_variant(files, variant)
        sources.extend((canvas.rel, files.path("assumptions", variant)))
        source = canvas.plain()
        listed = _assumptions_of(files, variant)
        taken = naming.in_use(files, idea)
        copies: list[tuple[int, Mapping[str, Any]]] = []
        for index, new in enumerate(into):
            canvas_rel = files.path("canvas", new)
            assumptions_rel = files.path("assumptions", new)
            copies_written.extend((canvas_rel, assumptions_rel))
            for rel in (canvas_rel, assumptions_rel):
                if files.exists(rel):
                    raise Refused(f"the variant `{new}` cannot be created: `{rel}` exists already")
            naming.given(idea, typed=ids.own(new), text="", fallback="variant", taken=taken)
            copied = _canvas_copy(source, variant, new)
            copied_assumptions = [_assumption_copy(a, variant, new) for a in listed]
            named = sorted(_ids_given(copied, copied_assumptions) & taken)
            if named:
                raise Refused(
                    f"the copy into `{new}` would give {', '.join(f'`{i}`' for i in named)}, "
                    f"which a reference still names, and an id named is never given again"
                )
            doc = editing.new(layout.SCHEMA["canvas"], _round_trip(copied))
            files.put(canvas_rel, doc)
            files.put(
                assumptions_rel,
                editing.new(
                    layout.SCHEMA["assumptions"],
                    {"assumptions": _round_trip(copied_assumptions)},
                ),
            )
            plain = doc.plain()
            copies.append((index, plain if isinstance(plain, Mapping) else {}))
        refusals = gates.split(variant, copies)
        if refusals:
            raise Refused("; ".join(refusal.message for refusal in refusals))
        outcome = editing.mapping(
            [
                ("kind", "split"),
                ("into", editing.seq(ids.ref(ids.CANVAS, new) for new in into)),
                ("by", ctx.who),
                ("when", ctx.on),
            ]
        )
        editing.place(canvas.data, "outcome", outcome, canvases.ORDER)
        files.put(canvas.rel, canvas.doc)
        return files, (
            f"Split `{variant}` into {_words(into)}: each is a copy of its canvas and its "
            f"assumptions, with no verdict, to judge at the desk afresh."
        )

    def repeated(held: writes.Held) -> str | None:
        """Where each error the split would add lies in a copy, and the variant split holds
        one already: each copy repeats it, so it is fixed in the variant first."""
        if not all(_file(f.location) in copies_written for f in held.added):
            return None
        holding = sorted({_file(f.location) for f in held.standing} & set(sources))
        if not holding:
            return None
        return (
            f"as each copy repeats what {_words(holding)} holds already: fix it in "
            f"{_words(holding)} first, then split"
        )

    acting.person_move(
        ctx,
        engine.DESK,
        variant,
        TRIGGER,
        before,
        build,
        decided=args.person_decided,
        added=repeated,
    )


def _file(location: str) -> str:
    """The file a finding's place names, without the place within it."""
    return location.split("#", 1)[0]


def _named(idea: str, given: str) -> str:
    """The id of the variant `given` names: its whole id, which lies in `idea`, or its own
    part, which `idea` qualifies. Raises Refused where it is neither."""
    if ids.is_idea_qualified(given):
        if ids.idea_of(given) != idea:
            raise Refused(f"`{given}` is a variant of another idea: a split stays in `{idea}`")
        return given
    if ids.is_segment(given):
        return ids.qualify(idea, given)
    raise Refused(
        f"`{given}` names no variant: give its own part, such as `solo`, or its id, "
        f"`{idea}--<variant>`"
    )


def _assumptions_of(files: writes.Files, variant: str) -> list[Any]:
    """The assumptions of `variant`, as the check reads them, or none where it has no list."""
    doc = files.read(files.path("assumptions", variant))
    listed = doc.plain().get("assumptions") if doc is not None else None
    return list(listed) if isinstance(listed, list) else []


def _requalified(value: object, old: str, new: str) -> object:
    """`value`, where it is an id qualified by the variant `old`, with its own part under
    `new`; else as it is."""
    if ids.is_variant_qualified(value) and ids.qualifier(str(value)) == old:
        return ids.qualify(new, ids.own(str(value)))
    return value


def _canvas_copy(canvas: Mapping[str, Any], old: str, new: str) -> dict[str, Any]:
    """The canvas of the variant `new`, copied from `old`'s, its keys in the schema's order."""
    copied: dict[str, Any] = {}
    for key in canvases.ORDER:
        if key == "id":
            copied[key] = new
        elif key == "comes-from":
            copied[key] = ids.ref(ids.CANVAS, old)
        elif key == "boxes" and isinstance(canvas.get(key), Mapping):
            copied[key] = {
                box: [_entry_copy(e, old, new) for e in held] if isinstance(held, list) else held
                for box, held in canvas[key].items()
            }
        elif key in COPIED and key in canvas:
            copied[key] = canvas[key]
    return copied


def _entry_copy(entry: object, old: str, new: str) -> object:
    if not isinstance(entry, Mapping):
        return entry
    copied = dict(entry)
    for field in ENTRY_ID_FIELDS:
        if field in copied:
            copied[field] = _requalified(copied[field], old, new)
    held = copied.get(ENTRY_IDS_FIELD)
    if isinstance(held, list):
        copied[ENTRY_IDS_FIELD] = [_requalified(value, old, new) for value in held]
    return copied


def _assumption_copy(assumption: object, old: str, new: str) -> object:
    if not isinstance(assumption, Mapping):
        return assumption
    copied = dict(assumption)
    if "id" in copied:
        copied["id"] = _requalified(copied["id"], old, new)
    source = copied.get("source")
    if isinstance(source, Mapping) and "entry" in source:
        copied["source"] = {**source, "entry": _requalified(source["entry"], old, new)}
    return copied


def _ids_given(canvas: Mapping[str, Any], assumptions: Sequence[object]) -> set[str]:
    """Every id the copy gives: each entry's and each assumption's."""
    found: set[str] = set()
    boxes = canvas.get("boxes")
    for held in boxes.values() if isinstance(boxes, Mapping) else []:
        for entry in held if isinstance(held, list) else []:
            if isinstance(entry, Mapping) and isinstance(entry.get("id"), str):
                found.add(entry["id"])
    for assumption in assumptions:
        if isinstance(assumption, Mapping) and isinstance(assumption.get("id"), str):
            found.add(assumption["id"])
    return found


def _round_trip(value: Any) -> Any:
    """`value`, read as the check reads it, as a file a command writes holds it."""
    if isinstance(value, Mapping):
        return editing.mapping((str(k), _round_trip(v)) for k, v in value.items())
    if isinstance(value, list):
        return editing.seq(_round_trip(v) for v in value)
    return value


def _words(named: list[str]) -> str:
    return positions.joined([f"`{n}`" for n in named])


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
