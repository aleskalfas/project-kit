"""The part of an artefact an anchor names: a document's section, or its lead
(COR-050 points 2, 5 and 7; ADR-057 point 2).

The one reading of an `artefact` anchor's value. Both friction checks, at each
state they compare, validation's friction member and the artefacts document
read an artefact anchor through it, so they agree on what it names:

- **The value** splits at its last `#` (`record_points.split_anchor`, the mark
  COR-051 point 3 gives a part). A value that names an artefact whole, `#`
  included, is read whole first, so a `#` in an artefact's own name never reads
  as a part.
- **A section** is named by its heading's slug, `docs/guide.md#installing`, and
  **the lead** by a bare `#`, `docs/guide.md#`. Both are found by the one
  reading of where a part of a document lies (`document_parts.Body`): the slug
  by `heading_slug`, the sections with it by `Body.sections_by_slug`, the lead
  by `Body.lead`. An empty slug names no section, so a bare `#` never meets a
  heading whose slug is empty.
- **What an anchor finds** (`anchored_part`, `PartState`): an artefact whole,
  one section or the lead, a slug two headings share (ambiguous), nothing
  (dead), or a part COR-050 point 2 refuses, with its reason and the anchor to
  use (`Refusal`):
  - a section or the lead of a collection file, whose entries are artefacts:
    the entry whose id follows the `#`, or whose section holds the heading
    with the slug;
  - a section or the lead of a collection entry, cited whole by its id. An
    extension point a rule offers, `RS-CMN-003#cause-location`, reads as one,
    and its reason says so;
  - a section or the lead of an artefact whose file a record anchor names,
    whose parts are its points (`record_points`): the point whose id follows
    the `#`, or whose heading has the slug, else the whole record.
- **What a part stands on** (`part_standing`, COR-050 point 5): its text — a
  section's heading and its text, or the lead's text — and the artefact's own
  fields, outside the container. It is read in the shape a point's is
  (`record_points.Standing`), so the checks compare and diff the two alike. A
  change elsewhere in the body changes nothing it stands on, and a section
  keeps its slug wherever it sits.
- **The lines a part spans** (`AnchoredPart.span`), counted from its file's
  first line, as an entry's are: exactly the text `part_standing` compares.
- **The artefact a part anchor counts as** (`whole_target`): for cycles and
  truth-chain order, an anchor on a section or the lead counts as one on the
  whole artefact (COR-050 points 5 and 11).

Which record anchor names a file is the friction checks' resolver's
(`friction_check.record_naming`), handed in, so this module calls nothing of
the checks.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import cast

from project_kit.document_parts import Body, Extent, SectionSpan, heading_slug
from project_kit.friction_discovery import Anchor, Artefact, ArtefactKind, Discovery, content
from project_kit.record_points import Standing, read_points, split_anchor

#: The part a bare `#` names: a document's lead (COR-050 point 2).
LEAD = ""


class PartState(Enum):
    """What an `artefact` anchor finds at one state (COR-050 points 2 and 7)."""

    WHOLE = "whole"  # the value names an artefact whole
    LIVE = "live"  # one section with the slug, or the lead
    AMBIGUOUS = "ambiguous"  # two headings or more share the slug: an error
    MISSING = "missing"  # no artefact by the name, or no heading with the slug: a dead anchor
    REFUSED = "refused"  # a part COR-050 point 2 refuses: an error


class Refusal(Enum):
    """What a refused part anchor names a section or the lead of (COR-050 point 2)."""

    COLLECTION_FILE = "a collection file"
    ENTRY = "a collection entry"
    RECORD = "a record"


@dataclass(frozen=True)
class AnchoredPart:
    """What the `artefact` anchor `value` finds at one state (`anchored_part`).

    - `state`: what it finds (`PartState`).
    - `target`: the artefact it names, whole or a part of it; `None` where the
      name resolves to no artefact, a collection file included.
    - `name` and `part`: the value split at its last `#`. `part` is a slug,
      `LEAD` for the lead, and `None` for a whole anchor or a value with no `#`.
    - `extent`: where the part lies in the target's body; for an ambiguous
      anchor, the first section with the slug.
    - `sharing`: how many headings have the slug.
    - `refusal` and `use`: for a refused anchor, what it names a part of and
      the anchor to use instead, where there is one.
    """

    value: str
    state: PartState
    target: Artefact | None = None
    name: str = ""
    part: str | None = None
    extent: Extent | None = None
    sharing: int = 0
    refusal: Refusal | None = None
    use: Anchor | None = None

    @property
    def resolves(self) -> bool:
        """Whether it names something an anchor may stand on: an artefact whole, one
        section or the lead (COR-050 point 7)."""
        return self.state in (PartState.WHOLE, PartState.LIVE)

    @property
    def names_part(self) -> bool:
        """Whether it is a part anchor: its value has a `#` and names no artefact whole."""
        return self.part is not None

    @cached_property
    def standing(self) -> Standing | None:
        """What the part stands on here (`part_standing`): `None` for a whole anchor, a
        dead or refused one. An ambiguous anchor reads its first section."""
        if self.state not in (PartState.LIVE, PartState.AMBIGUOUS) or self.part is None:
            return None
        return part_standing(self.target, self.part)

    @property
    def span(self) -> SectionSpan | None:
        """The lines of the target's file a live part spans, counted from 1 with its front
        matter, as an entry's span is (`document_parts.Body.span_of`); `None` for an
        empty lead, and for anything but a live part."""
        if self.state is not PartState.LIVE or self.target is None or self.extent is None:
            return None
        return Body.read(self.target.body).span_of(self.extent, self.target.body_line)

    @property
    def problem(self) -> str | None:
        """Why a part anchor is dead, ambiguous or refused, as both checks and validation
        say it (COR-050 points 2 and 7); `None` where it resolves, and for a whole anchor
        that names nothing, whose reason is the checks' own."""
        if self.part is None or self.resolves:
            return None
        if self.state is PartState.AMBIGUOUS:
            return f"is ambiguous: {self.sharing} headings of {self.name} have the slug {self.part}"
        if self.state is PartState.REFUSED:
            return f"is refused: {self._refused()}"
        if self.target is None:
            return "names no artefact in the declared places"
        return f"{self.name} has no heading whose slug is {self.part}"

    def _refused(self) -> str:
        use = "" if self.use is None else f" — use the {self.use.kind} anchor {self.use.value}"
        if self.refusal is Refusal.COLLECTION_FILE:
            fallback = "" if self.use is not None else " — anchor one of its entries by its id"
            return (
                f"{self.name} is a collection file, whose entries are artefacts, each named by "
                f"its id{use}{fallback}"
            )
        if self.refusal is Refusal.RECORD:
            return f"{self.name} is a record, whose parts are its points{use}"
        if self.part and _offers(self.target, self.part):
            return (
                f"#{self.part} names an extension point of the rule {self.name}, which is no "
                f"anchor value (COR-051 point 3){use}"
            )
        return f"{self.name} is a collection entry, cited whole by its id{use}"


def anchored_part(
    discovery: Discovery, value: str, record_of: Callable[[str], str | None]
) -> AnchoredPart:
    """What the `artefact` anchor `value` finds in the artefacts `discovery` holds
    (COR-050 points 2 and 7).

    The value names an artefact whole where one has it as its name, `#` included.
    Otherwise it splits at its last `#`, and the name before it is looked up as a
    whole anchor's is (`Discovery.find`). `record_of` says which record anchor
    names a file, if one does (`friction_check.record_naming`).
    """
    whole = discovery.find(value)
    if whole is not None:
        return AnchoredPart(value, PartState.WHOLE, whole, value)
    name, part = split_anchor(value)
    if part is None:
        return AnchoredPart(value, PartState.MISSING, name=value)
    target = discovery.find(name)
    if target is None:
        entries = [
            a for a in discovery.artefacts if a.path == name and a.kind is ArtefactKind.ENTRY
        ]
        if not entries:
            return AnchoredPart(value, PartState.MISSING, None, name, part)
        entry = _entry_for(entries, part)
        use = None if entry is None else Anchor("artefact", entry.id)
        return AnchoredPart(
            value, PartState.REFUSED, None, name, part, refusal=Refusal.COLLECTION_FILE, use=use
        )
    if target.kind is ArtefactKind.ENTRY:
        use = Anchor("artefact", name)
        return AnchoredPart(
            value, PartState.REFUSED, target, name, part, refusal=Refusal.ENTRY, use=use
        )
    record = record_of(target.path)
    if record is not None:
        use = Anchor("record", _point_to_use(record, target, part))
        return AnchoredPart(
            value, PartState.REFUSED, target, name, part, refusal=Refusal.RECORD, use=use
        )
    body = Body.read(target.body)
    if part == LEAD:
        return AnchoredPart(value, PartState.LIVE, target, name, part, body.lead())
    found = body.sections_by_slug(part)
    if not found:
        return AnchoredPart(value, PartState.MISSING, target, name, part)
    state = PartState.LIVE if len(found) == 1 else PartState.AMBIGUOUS
    return AnchoredPart(value, state, target, name, part, found[0], sharing=len(found))


def part_standing(artefact: Artefact | None, part: str) -> Standing | None:
    """What an anchor on `part` of `artefact` stands on (COR-050 point 5): the part's
    text, a section's heading and its text or the lead's text, and the artefact's own
    fields, outside the container, each as YAML reads it, written out as JSON with its
    keys sorted.

    `None` where it stands on nothing: no artefact, an entry, whose parts are
    refused, or no section with the slug. A slug two headings share reads the
    first. Where the part sits in its document is not compared, so a move that
    keeps its text changes nothing.
    """
    if artefact is None or artefact.kind is not ArtefactKind.DOCUMENT:
        return None
    body = Body.read(artefact.body)
    if part == LEAD:
        extent = body.lead()
    else:
        found = body.sections_by_slug(part)
        if not found:
            return None
        extent = found[0]
    _body, own = content(artefact)
    fields = tuple(
        (str(key), json.dumps(value, sort_keys=True, default=str, ensure_ascii=False))
        for key, value in sorted(own.items(), key=lambda item: str(item[0]))
    )
    return Standing(fields, body.text_of(extent), "")


def whole_target(discovery: Discovery, value: str) -> Artefact | None:
    """The artefact an `artefact` anchor counts as for cycles and truth-chain order
    (COR-050 points 5 and 11): the one it names whole, else the one whose section or
    lead it names, its part ignored; `None` where it names none."""
    whole = discovery.find(value)
    if whole is not None:
        return whole
    name, part = split_anchor(value)
    return None if part is None else discovery.find(name)


def _offers(target: Artefact | None, part: str) -> bool:
    """Whether `target` is a rule that offers the extension point `part`, by its name in
    the rule's `offers` (COR-051 point 3)."""
    if target is None or target.rule_set is None:
        return False
    offers: object = target.carrier.get("offers")
    return isinstance(offers, list) and part in cast("list[object]", offers)


def _entry_for(entries: Sequence[Artefact], part: str) -> Artefact | None:
    """The entry a part of a collection file meant: the one whose id follows the `#`,
    else the first whose section holds a heading with the slug; `None` for the lead."""
    if part == LEAD:
        return None
    by_id = next((entry for entry in entries if entry.id == part), None)
    if by_id is not None:
        return by_id
    return next((e for e in entries if Body.read(e.body).sections_by_slug(part)), None)


def _point_to_use(record: str, target: Artefact, part: str) -> str:
    """The record anchor a part of the record `record` meant (COR-050 point 2): the live
    point whose id follows the `#`, else the one whose heading has the slug, both read by
    the one reading of a record's points; else the whole record.

    Only the point headings are asked of the record, so its body is read, without its
    front matter. A retired id is no point the record holds, so it names the whole
    record."""
    if part == LEAD:
        return record
    points = read_points(target.body).points
    for point in points:
        if point.id == part:
            return f"{record}#{point.id}"
    for point in points:
        heading = point.extent.heading
        if heading is not None and heading_slug(heading.title) == part:
            return f"{record}#{point.id}"
    return record
