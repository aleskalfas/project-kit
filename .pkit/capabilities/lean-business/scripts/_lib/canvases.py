"""A variant's canvas, as the desk commands change it (lean-business DEC-002 points 4 to 7;
DEC-001 point 3).

- **The variant** (`open_variant`): its canvas read round trip from the write, refused where
  the id is no variant's or the canvas does not exist.
- **An entry** (`find_entry`): found by its id, which names its variant.
- **The links** an entry carries (`LINKS`), each on the boxes that take it, and the fields
  an entry's edit may clear (`CLEARABLE`). A link to another entry names it by its id,
  given whole or by its own part, which the variant qualifies (`entry_ref`).
- **Each key in its place** (`ORDER`, `ENTRY_ORDER`): a key a command adds lands where the
  schema's reference instance writes it (`editing.place`).
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from _lib import editing, ids, layout, listing
from _lib import location as locations
from _lib.fingerprint import BOXES, Fingerprint, FingerprintError
from _lib.writes import Files, Refused

#: A canvas's keys, in the order the schema's reference instance writes them.
ORDER = (
    "pkit_schema",
    "schema_version",
    "id",
    "archetype",
    "authors",
    "comes-from",
    "sides",
    "boxes",
    "viability",
    "traction",
    "verdicts",
    "outcome",
)

#: An entry's keys, in order.
ENTRY_ORDER = (
    "id",
    "text",
    "side",
    "sub-headline",
    "problem",
    "alternatives",
    "triggers",
    "kind",
    "step",
)

#: The archetypes a variant takes (DEC-001 point 7).
ARCHETYPES = ("direct", "multisided", "marketplace")

#: The steps of the customer factory a key metric measures, and a traction target names.
FACTORY_STEPS = ("acquisition", "activation", "retention", "revenue", "referral")

#: The kinds of a channel.
CHANNEL_KINDS = ("early", "scalable")

#: Each link an entry carries, by its field, with the boxes that take it.
LINKS: Mapping[str, tuple[str, ...]] = {
    "alternatives": ("problem",),
    "problem": ("unique-value-proposition", "solution"),
    "sub-headline": ("unique-value-proposition",),
    "triggers": ("early-adopters",),
    "kind": ("channels",),
    "step": ("key-metrics",),
}

#: The fields of an entry an edit may clear: its side and each link.
CLEARABLE = ("side", *LINKS)


@dataclass
class Canvas:
    """A variant's canvas in a write: its path, its file round trip, and its variant's id."""

    rel: str
    doc: editing.Doc
    id: str

    @property
    def data(self) -> CommentedMap:
        return self.doc.data

    @property
    def idea(self) -> str:
        return ids.idea_of(self.id)

    def boxes(self) -> CommentedMap:
        """The canvas's boxes, an empty mapping put in its place where it holds none."""
        held = self.data.get("boxes")
        if not isinstance(held, CommentedMap):
            held = CommentedMap()
            editing.place(self.data, "boxes", held, ORDER)
        return held

    def box(self, name: str) -> CommentedSeq:
        """The box `name`'s entries, an empty list put in its place where it holds none."""
        boxes = self.boxes()
        held = boxes.get(name)
        if not isinstance(held, CommentedSeq):
            held = CommentedSeq()
            editing.place(boxes, name, held, BOXES)
        return held

    def sides(self) -> list[str]:
        held = self.data.get("sides")
        return [side for side in held if isinstance(side, str)] if isinstance(held, list) else []

    def plain(self) -> Mapping[str, Any]:
        """What the canvas means as the write leaves it so far, read as the check reads it."""
        read = self.doc.plain()
        return read if isinstance(read, Mapping) else {}


def variant_id(given: str) -> str:
    """`given`, refused where it is no variant's id, `<idea>--<variant>`."""
    if not ids.is_idea_qualified(given):
        raise Refused(
            f"`{given}` is no variant's id: a variant is named `<idea>--<variant>`, such as "
            f"`meal-plan--direct`"
        )
    return given


def open_variant(files: Files, given: str) -> Canvas:
    """The canvas of the variant `given`, as the write `files` leaves it so far. Raises
    Refused where the id is no variant's, or where its canvas does not exist."""
    variant = variant_id(given)
    rel = files.path("canvas", variant)
    doc = files.read(rel)
    if doc is None:
        raise Refused(
            f"there is no variant `{variant}`: `{rel}` does not exist; `pkit lean new-variant "
            f"{variant} --archetype <archetype>` creates it"
        )
    return Canvas(rel, doc, variant)


def reading_location(root: Path) -> str:
    """The location a command that only reads reads. Raises Refused where none can be."""
    try:
        found = locations.for_reading(root)
    except locations.LocationRefused as exc:
        raise Refused(str(exc)) from exc
    if found is None:
        raise Refused(
            f"nothing records where the ideas live, and the default, `{locations.DEFAULT}`, "
            f"is no folder: record one, `pkit lean set-location <path>`"
        )
    return found.path


def read_variant(root: Path, given: str) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    """The canvas of the variant `given`, and its idea's goal or None, as the files stand,
    for a command that only reads. Raises Refused where the canvas cannot be read."""
    variant = variant_id(given)
    idea, own = ids.idea_of(variant), ids.own(variant)
    location = reading_location(root)
    try:
        held = layout.read(root, location, idea).ideas.get(idea)
    except (listing.ListingFailed, layout.IdRefused) as exc:
        raise Refused(f"the idea's files cannot be read: {exc}") from exc
    found = held.variants.get(own) if held is not None else None
    canvas = found.canvas if found is not None else None
    if canvas is None or canvas.data is None:
        why = canvas.problem if canvas is not None and canvas.problem else "it does not exist"
        raise Refused(f"the canvas of `{variant}` cannot be read: {why}")
    goal = held.goal.data if held is not None and held.goal is not None else None
    return canvas.data, goal


def goal_of(files: Files, idea: str) -> Mapping[str, Any] | None:
    """The idea's goal as the write `files` leaves it so far, or None where it has none.
    Raises Refused where its file cannot be read."""
    doc = files.read(files.path("goal", idea))
    read = doc.plain() if doc is not None else None
    return read if isinstance(read, Mapping) else None


def fingerprint_data(taken: Callable[[], Fingerprint]) -> CommentedMap:
    """The fingerprint `taken` gives, as a file writes it. Raises Refused where what it
    covers has no text the fingerprint can take."""
    try:
        found = taken()
    except FingerprintError as exc:
        raise Refused(f"what the judgement covers cannot be fingerprinted: {exc}") from exc
    return editing.mapping(found.as_data().items())


def entry_variant(entry: str) -> str:
    """The variant whose canvas holds the entry `entry`, from its id. Raises Refused where
    the id is no entry's."""
    if not ids.is_variant_qualified(entry):
        raise Refused(
            f"`{entry}` is no entry's id: an entry is named `<idea>--<variant>--<entry>`, as "
            f"`pkit lean canvas <variant> --ids` shows each"
        )
    return ids.qualifier(entry)


def find_entry(canvas: Canvas, entry: str) -> tuple[str, CommentedSeq, int]:
    """The box that holds the entry `entry`, its entries and the entry's place among them.
    Raises Refused where the canvas holds no such entry."""
    boxes = canvas.data.get("boxes")
    if isinstance(boxes, Mapping):
        for name, held in boxes.items():
            if not isinstance(held, CommentedSeq):
                continue
            for index, item in enumerate(held):
                if isinstance(item, Mapping) and item.get("id") == entry:
                    return str(name), held, index
    raise Refused(f"the canvas of `{canvas.id}` holds no entry `{entry}`")


def entry_ref(variant: str, given: str) -> str:
    """The id of an entry a link names: `given` whole, or its own part, which the variant
    `variant` qualifies. Raises Refused where it is neither."""
    if ids.is_variant_qualified(given):
        return given
    if ids.is_segment(given):
        return ids.qualify(variant, given)
    raise Refused(
        f"`{given}` names no entry: give the entry's id, `<idea>--<variant>--<entry>`, or its "
        f"own part"
    )


def check_link(box: str, link: str, flag: str) -> None:
    """Refuse the link `link`, given by the flag `flag`, on an entry of a box that takes
    none such."""
    if box not in LINKS[link]:
        takes = " or ".join(f"`{b}`" for b in LINKS[link])
        raise Refused(f"{flag} is given on an entry of {takes} alone, and this is in `{box}`")


def check_side(canvas: Canvas, side: str | None) -> None:
    """Refuse a side the canvas does not name."""
    if side is None:
        return
    if side not in canvas.sides():
        named = ", ".join(f"`{s}`" for s in canvas.sides()) or "none"
        raise Refused(
            f"the canvas of `{canvas.id}` names no side `{side}` (it names {named}): "
            f"`pkit lean add-side {canvas.id} {side}` adds it"
        )


def set_entry_field(entry: CommentedMap, key: str, value: Any) -> None:
    """Set an entry's field in its place."""
    editing.place(entry, key, value, ENTRY_ORDER)


# --- an entry's links, as flags ---------------------------------------------------------------

#: Each link flag, by the field it sets.
FLAGS = {
    "alternatives": "--alternative",
    "problem": "--problem",
    "sub-headline": "--sub-headline",
    "triggers": "--trigger",
    "kind": "--kind",
    "step": "--step",
}


def link_flags(parser: argparse.ArgumentParser) -> None:
    """Add the flags that give an entry's links, each on the boxes that take it."""
    parser.add_argument(
        "--alternative",
        action="append",
        dest="alternatives",
        metavar="ENTRY",
        help="On a problem: an existing alternative it is framed against; repeat it for each.",
    )
    parser.add_argument(
        "--problem",
        metavar="ENTRY",
        help="On a value proposition or a solution: the problem it answers.",
    )
    parser.add_argument("--sub-headline", help="On a value proposition: its sub-headline.")
    parser.add_argument(
        "--trigger",
        action="append",
        dest="triggers",
        metavar="TEXT",
        help="On an early adopter: an event that made such customers switch; repeat it for each.",
    )
    parser.add_argument("--kind", choices=CHANNEL_KINDS, help="On a channel: early or scalable.")
    parser.add_argument(
        "--step",
        choices=FACTORY_STEPS,
        help="On a key metric: the step of the customer factory it measures.",
    )


def given_links(args: argparse.Namespace) -> dict[str, Any]:
    """The links the flags give, by their field, each left out that is not given."""
    found = {
        "alternatives": args.alternatives,
        "problem": args.problem,
        "sub-headline": args.sub_headline,
        "triggers": args.triggers,
        "kind": args.kind,
        "step": args.step,
    }
    return {field: value for field, value in found.items() if value is not None}


def add_links(canvas: Canvas, box: str, entry: CommentedMap, links: Mapping[str, Any]) -> None:
    """Lay the links `links` on the entry `entry` of `box`: a list's items added to what it
    holds, every other field set. Raises Refused for a link the box takes none of."""
    for field, value in links.items():
        check_link(box, field, FLAGS[field])
        if field == "alternatives":
            _extend(entry, field, [entry_ref(canvas.id, str(v)) for v in value])
        elif field == "triggers":
            _extend(entry, field, [str(v) for v in value])
        elif field == "problem":
            set_entry_field(entry, field, entry_ref(canvas.id, str(value)))
        else:
            set_entry_field(entry, field, value)


def _extend(entry: CommentedMap, field: str, values: list[str]) -> None:
    held = entry.get(field)
    if not isinstance(held, list):
        held = editing.seq()
        set_entry_field(entry, field, held)
    for value in values:
        if value not in held:
            held.append(value)
