"""Which substrate carries a classification axis — the single composition.

The rule ([project-management:DEC-062-axes-chosen-in-the-map] point 1): **ask the
map.** An axis lives where the adopter's substrate map binds it, and nowhere
else: on the board only where the map binds it there with `board: true`, on the
kit's own labels with no map or where the map binds it there with
`kit-label: true`. `has_projects_v2_board` says only that a board exists, and
carries no axis. One composition, consulted by every writer, reader,
prerequisite check and mutator, so no two consumers can form different beliefs
about where an axis lives ([project-management:DEC-051-axis-carriage-activation]
point 4).

That drift is not hypothetical — it is the reported failure this module exists to
end (#708). An adopter's config set ``has_projects_v2_board: true`` while their
map bound ``priority`` to the repo's own labels. The filing verb honoured the
flag and wrote no label; nothing wrote the board field; the reviewer resolved
through the map and found nothing. Neither side was wrong on its own; there was
simply no single answer to ask.

Where the map is silent
-----------------------
An axis the map does not bind reads as DEC-036 point 2 says, board or no board
(DEC-062 point 2). With no map at all, it reads the kit's own labels. In a
present map, an axis that is absent or marked `unsupported` degrades. So a
map's presence carries nothing beyond its bindings (DEC-062 point 4): a
`kit-label` axis behaves in any map as it does with no map.

Purity, and why it is load-bearing
----------------------------------
This module performs **no I/O**. It answers only *where* an axis lives — never
*what value* the substrate currently holds. Reading a board field's value
belongs to the board read seam (``_lib/board_fields``), which is
posture-neutral, and the decision to raise on an unreadable board belongs to the
consumer that composes the two ([pkit:ADR-053]).

Keeping them apart is a correctness requirement, not tidiness:

* Every verb asks "where does this live?", and only a few ever need a board
  value. A board outage must not become a filing outage on code paths that
  never touch the board, so the question cannot fail.
* The rule that an unreadable board raises an error is **scoped to projects that
  actually expect a board value**. That scoping is only implementable if you can
  ask "does this project expect a board value for this axis?" *without performing
  a board read* — otherwise the condition depends on the very operation it gates.
* The layering runs one way: this module calls the seam, and the seam never
  calls this module.

What this module does NOT decide
--------------------------------
Board **membership** (every issue belongs on the configured board, per DEC-019)
and board **identity** (which board, and its node id) are the flag's jobs, and
have nothing to do with carriage (DEC-062 point 1). They must not be routed
through here: doing so would silently drop the membership requirement for any
board adopter whose map binds no axis to the board. Those reads belong to
``_lib/board_fields``.
"""

from __future__ import annotations

from typing import Any, Literal

from _lib import axis_labels

# The resolved carriage of an axis. A closed set on purpose: a boolean
# "is it on the board?" would re-create the ordering inversion this module
# exists to remove — a consumer with a False arm still has to ask the seam to
# be correct, and a guard that only forbids reading the flag cannot see it.
# `False` would also be ambiguous between "the kit's own label" and "nothing".
Carriage = Literal[
    "kit-label",  # the kit's own `<axis>:<value>` label: no map, or `kit-label: true`
    "adopter-label",  # a `label` binding: the adopter's own label string
    "title",  # a `title-prefix` binding: carried in the issue title
    "derived",  # a `derive` binding: computed by the detector engine
    "board",  # a `board` binding: a field on the configured Projects-v2 board
    "degrade",  # nothing carries it; rules needing it soften
]


def carriage(
    axis: str,
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> Carriage:
    """Where ``axis``'s value lives. Pure; no I/O; the single answer.

    The map alone answers (DEC-062 point 1). With no map, or where the map binds
    the axis with `kit-label: true`, the kit's own labels carry it. Where the
    map binds it to a substrate, that binding is the answer. Where a present map
    omits it, marks it `unsupported`, or binds it in no shape the seam knows, it
    degrades — the kit's own labels are not demanded of an adopter who may be
    unable to create them (DEC-036 point 2).

    ``config`` is accepted beside the map, as every caller holds both, and read
    for nothing: the board flag carries no axis. A `board: true` binding under a
    config that declares no board answers `board` all the same; the prerequisite
    check refuses that pair, and a consumer that reads the board fails on it.
    """
    del config  # the flag carries no axis (DEC-062 point 1)
    if substrate_map is None or axis_labels.axis_expects_kit_labels(axis, substrate_map):
        return "kit-label"
    binding = substrate_map.axes.get(axis)
    if not isinstance(binding, dict):
        # Absent from a present map: degrade rather than demand a kit label the
        # adopter may be unable to create.
        return "degrade"
    if axis_labels.axis_is_board_carried(axis, substrate_map):
        return "board"
    if axis_labels.axis_is_label_bound(axis, substrate_map):
        return "adopter-label"
    if axis_labels.axis_is_title_carried(axis, substrate_map):
        return "title"
    if "derive" in binding:
        return "derived"
    # `unsupported` names no substrate, and a binding matching no known arm is
    # malformed: both degrade, so an axis is never handed to a label the
    # adopter may not have.
    return "degrade"


def is_board_carried(
    axis: str,
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> bool:
    """Whether ``axis`` resolves to the board — the scoping predicate.

    This is the question "does this project expect a value from the board for
    this axis?", answerable without touching the network. It is what scopes the
    raise-on-unreadable-board rule: a project with no board, or an axis that does
    not live on one, never performs a board read and so can never fail one.

    Prefer :func:`carriage` where the consumer has more than two arms; this is
    the narrow predicate for gates that only need the board/not-board split.
    """
    return carriage(axis, config, substrate_map) == "board"


def expects_kit_labels(
    axis: str,
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> bool:
    """Whether the kit's own ``<axis>:*`` labels are this axis's substrate.

    The presence-gate question: may this gate demand a ``priority:High``-shaped
    label? True with no map, and where the map binds the axis with
    `kit-label: true`. Every other carriage — the adopter's own label, a title
    prefix, a derived state, a board field, or nothing at all — means the kit's
    label is not the thing to look for, which is the read path's expression of
    "never demand a label the adopter cannot create".
    """
    return carriage(axis, config, substrate_map) == "kit-label"


# How each carriage reads in a sentence, for a message that has to tell an
# adopter WHY the kit's own labels were not touched. One table, because every
# consumer composing such a message would otherwise write its own phrasing and
# they would drift (COR-007). `{axis}` is substituted by :func:`describe`.
_CARRIAGE_PHRASE: dict[Carriage, str] = {
    "kit-label": "by the kit's own `{axis}:*` labels",
    "adopter-label": ("by your OWN labels (a `label:` binding in project/substrate-map.yaml)"),
    "title": ("in the issue TITLE (a `title-prefix:` binding in project/substrate-map.yaml)"),
    "derived": ("by a detection predicate (a `derive:` binding in project/substrate-map.yaml)"),
    "board": ("on your Projects-v2 board (a `board: true` binding in project/substrate-map.yaml)"),
    "degrade": "by nothing — the axis is unsupported under your substrate-map",
}


def describe(
    axis: str,
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> str:
    """Where ``axis`` lives, as a phrase to drop into a message ("on your board…").

    Naming the substrate is what turns "no label was created" from a silent
    difference into something an adopter can act on, and the phrase has to agree
    with the carriage that produced it — so it is derived from the same call
    rather than re-guessed at each site.
    """
    return _CARRIAGE_PHRASE[carriage(axis, config, substrate_map)].format(axis=axis)


def kit_label_mutation_note(
    axis: str,
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> str | None:
    """``None`` when the kit's own ``<axis>:*`` labels may be MUTATED, else why not.

    The gate for a mutator that creates / renames / deletes a kit ``<axis>:<value>``
    label (the five workstream mutators). It is :func:`expects_kit_labels` plus the
    sentence explaining the answer, kept in one place because five mutators ask the
    same question and five hand-written phrasings would drift (COR-007).

    Why a *note* rather than a refusal: the naive substitution of a carriage read
    for a kit-label check turns kit-label mutation **on** for an adopter whose
    map binds the axis to their own labels. That does not merely write an
    unmanaged ``workstream:<slug>`` label — ``remove`` / ``merge`` / ``split``
    would issue ``gh label delete`` and ``rename`` a ``gh label edit`` against a
    name the kit does not own. The mutators' other half — editing the adopter's
    declared workstream vocabulary in ``workstreams.yaml`` — stays meaningful on
    every carriage, and a board adopter runs them with the label half skipped, so
    a hard refusal here would regress a working path. The label half is
    suppressed and *said out loud* instead.

    Distinct from :func:`axis_labels.workstream_mutator_refusal`, which stays the
    hard refusal for the one arm where the mutator has nothing left to do: an
    ``unsupported`` / absent axis under a present map names no substrate at all,
    so neither the label half nor the vocabulary half means anything. The two run
    together — the refusal first, this note second.
    """
    if expects_kit_labels(axis, config, substrate_map):
        return None
    return (
        f"{axis} is carried {describe(axis, config, substrate_map)}, so the kit's "
        f"`{axis}:*` labels are not this project's {axis} substrate: no kit label "
        f"is created, renamed or deleted here. The declared {axis} vocabulary is "
        f"still updated. (Managing an adopter-owned {axis} substrate from these "
        f"mutators is the adopt-existing Feature #264.)"
    )
