"""A variant's assumptions, as the experiment path's commands read and change them
(lean-business DEC-002 points 7 and 8; DEC-003 point 8; DEC-001 point 3).

- **The list** (`open_list`): the variant's one list, read round trip from the write; a
  list the variant lacks is created where an assumption is added to it.
- **An assumption** (`Assumptions.find`): found by its id, given whole or by its own part,
  which the variant qualifies (`assumption_id`, `own_or_whole`).
- **Where it comes from** (`source`): an entry the canvas holds, or an input of the
  estimate with its side where the model names several. An entry that the canvas does not
  hold is refused when the source is written, since it can only be a typo; the link may
  dangle later, once the method removes the entry (DEC-002 point 7).
- **Its rank** (`next_rank`): an assumption added goes one past the highest rank, a
  placement that judges nothing; the person ranks them by risk (DEC-002 point 8).
- **Each key in its place** (`ORDER`, `SOURCE_ORDER`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from _lib import canvases, editing, ids, layout
from _lib.fingerprint import STEPS
from _lib.writes import Files, Refused

#: An assumption's keys, in the order the schema's reference instance writes them.
ORDER = ("id", "statement", "source", "kind", "rank")

#: A source's keys, in order.
SOURCE_ORDER = ("entry", "input", "side")

#: The estimate's inputs an assumption may come from (DEC-002 point 8).
INPUTS = ("price", "lifetime", "conversion", "referral-share")

#: The desk step whose risk an assumption carries.
KINDS = STEPS


@dataclass
class Assumptions:
    """A variant's list of assumptions in a write: its path, its file round trip, and the
    variant's id."""

    rel: str
    doc: editing.Doc
    variant: str

    def items(self) -> CommentedSeq:
        """The assumptions, an empty list put in its place where the file holds none."""
        held = self.doc.data.get("assumptions")
        if not isinstance(held, CommentedSeq):
            held = editing.seq()
            self.doc.data["assumptions"] = held
        return held

    def find(self, assumption: str) -> tuple[int, CommentedMap]:
        """The assumption whose id is `assumption`, with its place in the list. Raises
        Refused where the list holds none such."""
        for index, item in enumerate(self.items()):
            if isinstance(item, CommentedMap) and item.get("id") == assumption:
                return index, item
        raise Refused(f"the assumptions of `{self.variant}` hold no `{assumption}`")

    def ids(self) -> list[str]:
        return [
            str(item["id"])
            for item in self.items()
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        ]

    def next_rank(self) -> int:
        """One past the highest rank the list holds."""
        ranks = [
            item["rank"]
            for item in self.items()
            if isinstance(item, Mapping)
            and isinstance(item.get("rank"), int)
            and not isinstance(item.get("rank"), bool)
        ]
        return max(ranks, default=0) + 1


def assumption_id(given: str) -> str:
    """`given`, refused where it is no assumption's id, `<idea>--<variant>--<assumption>`."""
    if not ids.is_variant_qualified(given):
        raise Refused(
            f"`{given}` is no assumption's id: an assumption is named "
            f"`<idea>--<variant>--<assumption>`, as `pkit lean add-assumption` printed it"
        )
    return given


def own_or_whole(variant: str, given: str) -> str:
    """The id of an assumption of `variant`: `given` whole, or its own part, which the
    variant qualifies. Raises Refused where it is neither."""
    if ids.is_variant_qualified(given):
        return given
    if ids.is_segment(given):
        return ids.qualify(variant, given)
    raise Refused(
        f"`{given}` names no assumption: give its id, `<idea>--<variant>--<assumption>`, or its "
        f"own part"
    )


def open_list(files: Files, variant: str, *, create: bool = False) -> Assumptions:
    """The assumptions of the variant `variant`, as the write `files` leaves them so far:
    a new list where `create` and the variant has none. Raises Refused where the variant
    has no canvas, or no list and `create` is not set."""
    variant = canvases.variant_id(variant)
    if not files.exists(files.path("canvas", variant)):
        raise Refused(
            f"there is no variant `{variant}`; `pkit lean new-variant {variant} --archetype "
            f"<archetype>` creates it"
        )
    rel = files.path("assumptions", variant)
    doc = files.read(rel)
    if doc is None:
        if not create:
            raise Refused(
                f"`{variant}` has no assumptions yet: `pkit lean add-assumption {variant} "
                f"<statement> --kind <step> --entry <entry>` adds one"
            )
        doc = editing.new(layout.SCHEMA["assumptions"], {"assumptions": editing.seq()})
    return Assumptions(rel, doc, variant)


def source(
    canvas: canvases.Canvas, *, entry: str | None, input_name: str | None, side: str | None
) -> CommentedMap:
    """Where an assumption of `canvas`'s variant comes from: the entry `entry`, given by its
    id or its own part, which the canvas holds; or the estimate's input `input_name`, for
    `side` where given. Raises Refused for an entry the canvas does not hold, a side it does
    not name, or a side given with an entry."""
    if entry is not None:
        if side is not None:
            raise Refused("--side is given with --input alone: an entry names its side itself")
        named = canvases.entry_ref(canvas.id, entry)
        try:
            canvases.find_entry(canvas, named)
        except Refused as exc:
            raise Refused(
                f"--entry `{entry}` names no entry of the canvas of `{canvas.id}`: `pkit lean "
                f"canvas {canvas.id} --ids` shows each"
            ) from exc
        return editing.mapping([("entry", named)])
    assert input_name is not None
    canvases.check_side(canvas, side)
    return editing.mapping([("input", input_name), ("side", side)])
