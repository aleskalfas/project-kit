"""Which substrate carries a classification axis — the single composition.

The rule ([project-management:DEC-051-axis-carriage-activation]): **ask the map;
where it is silent, ask the flag.** One composition, consulted by every writer,
reader, prerequisite check and mutator, so no two consumers can form different
beliefs about where an axis lives.

That drift is not hypothetical — it is the reported failure this module exists to
end (#708). An adopter's config set ``has_projects_v2_board: true`` while their
map bound ``priority`` to the repo's own labels. The filing verb honoured the
flag and wrote no label; nothing wrote the board field; the reviewer resolved
through the map and found nothing. Neither side was wrong on its own; there was
simply no single answer to ask.

Ordering
--------
The map is asked first. This is not a new ordering — it is the one ADR-026's
read-path contract already pins (the adopter-binding question resolves first, and
the board-versus-label distinction applies only underneath, in the kit-managed
case). Two guards in the tree today resolve board-versus-label *first* and reach
the seam only in their no-board branch, so under a configured board ``priority``
and ``workstream`` never reach the seam at all. This module restores the pinned
ordering rather than introducing one.

Purity, and why it is load-bearing
----------------------------------
This module performs **no I/O**. It takes ``config`` as an injected dict and never
loads it, and it answers only *where* an axis lives — never *what value* the
substrate currently holds. Reading a board field's value belongs to the board read
seam (``_lib/board_fields``), which is posture-neutral, and the decision to raise
on an unreadable board belongs to the gate that composes the two.

Keeping them apart is a correctness requirement, not tidiness:

* Rewiring the flag reads across the verb family is only safe if asking "where
  does this live?" cannot fail. A board outage must not become a filing outage on
  code paths that never touch the board.
* The rule that an unreadable board raises an error is **scoped to projects that
  actually expect a board value**. That scoping is only implementable if you can
  ask "does this project expect a board value for this axis?" *without performing
  a board read* — otherwise the condition depends on the very operation it gates.
* ADR-026's amendment pins a one-way layering: this module calls the seam, and
  the seam never calls this module.

What this module does NOT decide
--------------------------------
Board **membership** (every issue belongs on the configured board, per DEC-019)
and board **identity** (which board, and its node id) are jobs of the flag that
have nothing to do with carriage. They must not be routed through here: doing so
would silently drop the membership requirement for any board adopter who wrote a
single label binding. Those reads belong to ``_lib/board_fields``.
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
    "kit-label",       # greenfield: the kit's own `<axis>:<value>` label
    "adopter-label",   # a `label` binding: the adopter's own label string
    "title",           # a `title-prefix` binding: carried in the issue title
    "derived",         # a `derive` binding: computed by the detector engine
    "board",           # a field on the configured Projects-v2 board
    "degrade",         # nothing carries it; rules needing it soften
]

# The axes the board can claim when the map is silent. `type` is absent
# deliberately and permanently: it is always a label, board or no board,
# because PR-title alignment reads the type label and a board field is
# invisible from a PR.
BOARD_CLAIMABLE_AXES: tuple[str, ...] = ("priority", "workstream", "state")


def _flag_set(config: dict[str, Any] | None) -> bool:
    """Whether the adopter's config declares a Projects-v2 board.

    Deliberately only the flag, not ``projects_v2_board_id``. A board declared
    without an id is a misconfiguration the prerequisite check reports; treating
    it here as "no board" would silently hand the axis back to kit labels the
    adopter may not have, which is the harm the degrade rule exists to prevent.
    """
    return bool(config and config.get("has_projects_v2_board"))


def carriage(
    axis: str,
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> Carriage:
    """Where ``axis``'s value lives. Pure; no I/O; the single answer.

    Ask the map first. Where the map binds the axis, that binding is the answer
    and ``has_projects_v2_board`` is not consulted for it — an explicit statement
    of intent beats a project-wide switch that cannot see it.

    Where the map is silent — no map at all, or a map that omits this axis —
    nothing changes from today: the flag governs. That conservatism is
    deliberate. Making a present map authoritative for the axes it omits would
    silently degrade priority on upgrade for every board adopter with a partial
    map, which is the same failure class as the report this rule answers. The
    prerequisite check nudges those adopters toward declaring ``board: true``
    instead; the semantics stay put.

    The one asymmetry worth knowing: an axis absent from a *present* map with no
    board configured degrades rather than falling back to the kit's own labels
    (ADR-026's absent-≡-unsupported rule). A board field is not a label, so that
    rule never reached a board-carried axis — which is why the flag still answers
    for the board case and not for the kit-label case.
    """
    if substrate_map is not None:
        binding = substrate_map.axes.get(axis)
        if isinstance(binding, dict):
            # A binding exists: the adopter has spoken about this axis.
            if axis_labels.axis_is_board_carried(axis, substrate_map):
                return "board"
            if axis_labels.axis_is_label_bound(axis, substrate_map):
                return "adopter-label"
            if axis_labels.axis_is_title_carried(axis, substrate_map):
                return "title"
            if "derive" in binding:
                return "derived"
            if binding.get("unsupported") is True:
                # `unsupported` names NO substrate, so it cannot govern carriage
                # — it says the tracker has no encoding for this axis, which is a
                # statement about labels. The schema defines it as *equivalent to
                # omitting the axis*, so it falls through to the flag exactly as
                # an omitted axis does. Under a configured board that means the
                # board carries it, and an adopter holding the old
                # `unsupported: true` board workaround keeps their board write
                # rather than losing it on upgrade.
                #
                # This is the same reasoning point 3 applies to an omitted axis:
                # the degrade rule guards whether the KIT'S OWN LABELS may be
                # demanded, and a board field is not a label, so it never reached
                # the board question. With no board, the fall-through below
                # degrades — which is what `unsupported` has always meant.
                pass
            else:
                # A binding mapping matching no known arm is malformed; fail
                # closed rather than hand the axis to a label the adopter may not
                # have.
                return "degrade"

    # The map is silent about this axis. The flag governs, exactly as today.
    if axis in BOARD_CLAIMABLE_AXES and _flag_set(config):
        return "board"
    if substrate_map is not None:
        # Absent from a PRESENT map, with no board to carry it: degrade rather
        # than demand a kit label the adopter may be unable to create.
        return "degrade"
    return "kit-label"


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
    label? True only in greenfield with no board claiming the axis. Every other
    carriage — the adopter's own label, a title prefix, a derived state, a board
    field, or nothing at all — means the kit's label is not the thing to look
    for, which is the read path's expression of "never demand a label the adopter
    cannot create".
    """
    return carriage(axis, config, substrate_map) == "kit-label"
