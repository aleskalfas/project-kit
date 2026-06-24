"""The sole constructor of methodology axis-labels (ADR-026 part (i)).

A *methodology axis* is one of the conceptual dimensions the capability tracks
on an issue — ``type``, ``priority``, ``workstream``, ``state`` (lifecycle). In
the kit's own (greenfield) substrate each axis is encoded as a label of the
form ``<axis>:<value>`` (e.g. ``priority:High``, ``state:in-progress``). Today
those labels are string-formatted inline at ~26 write-path sites scattered
across the mutating scripts; this module pulls every such construction (and the
matching read) behind one seam.

Why a seam, per [ADR-026](../../../../docs/architecture/decisions/ADR-026-substrate-map-read-path-contract.md):
the load-bearing brownfield-adoption invariant (DEC-036, EPIC #217 constraint 1)
is *never write an unmanaged label*. That invariant only bites if the seam is
the **sole constructor** of any axis-label on a write path — a writer that
string-formats ``<axis>:<value>`` itself is unconstrained by anything the seam
guarantees. So this module is the single auditable point through which a
write-label comes into being, enforced structurally by the grep/AST guard
(`test_pm_axis_label_seam_guard.py`, ADR-026's part-(b) sole-constructor test).
It is the constructor analogue of ADR-024's ``render_status_json`` *never
calling* ``wrap()``.

**Scope of THIS module right now.** There is no ``substrate-map.yaml`` and no
resolution arms yet — that is the trunk Wave-2 Feature's work (Task B, DEC-036).
Today every axis resolves to the kit's own vocabulary directly: ``label(axis,
value)`` returns ``f"{axis}:{value}"`` and ``read(axis, labels)`` parses the
value back off the first ``<axis>:`` label. Greenfield output is therefore
**byte-identical** to the inline construction it replaces — the refactor is
purely behaviour-preserving. The API is pinned so Task B can grow the
map-reading internals (the ternary: bound / unsupported / absent-treated-as-
unsupported, plus the value-unresolvable fourth arm) *without changing any call
site* — the call sites already ask the seam; only the seam's internals gain the
map lookup. See the ``# TODO(Task B)`` markers below for the exact extension
points.

The module is deliberately content-free about *which* axes exist and *which*
values are valid — that vocabulary lives in ``classification.yaml`` /
``issue-types.yaml`` / ``workflow.yaml`` and is read by the callers, exactly as
``lifecycle_inference`` stays agnostic to the process definition. This seam only
owns the ``<axis>:<value>`` *encoding*.
"""

from __future__ import annotations

# The four methodology axes the kit encodes as `<axis>:<value>` labels in its
# own (greenfield) substrate. This tuple is the allow-list the sole-constructor
# guard keys on; it is the one place the axis names live.
AXES: tuple[str, ...] = ("type", "priority", "workstream", "state")


def label(axis: str, value: str) -> str:
    """The label encoding axis ``axis`` at value ``value`` *in this repo*.

    Greenfield (no ``substrate-map.yaml`` — always, in this Task): the kit's own
    ``<axis>:<value>`` encoding, byte-identical to the inline ``f"{axis}:{value}"``
    this replaces.

    This is the **sole constructor** of an axis-label on a write path (ADR-026
    part (i)): mutating scripts obtain a label to write *only* by calling here,
    never by string-formatting ``<axis>:<value>`` themselves. The grep/AST guard
    enforces that no mutating script reintroduces an inline literal.

    Parameters
    ----------
    axis:
        A methodology axis name (see :data:`AXES`).
    value:
        The kit's own value on that axis (e.g. ``High`` for priority, ``feature``
        for type, ``in-progress`` for state, a workstream slug for workstream).

    Returns
    -------
    str
        The label name to read or write for this (axis, value) in this repo.
    """
    # TODO(Task B / DEC-036): when a `substrate-map.yaml` is present and binds
    # this axis, resolve `value` through the declared binding (a `label`
    # value->value remap, a `title-prefix`, or a `derive` predicate) instead of
    # returning the kit's own label; when the axis is `unsupported` / absent /
    # value-unresolvable, return a degrade signal rather than a write-label
    # (ADR-026 part (ii) — fail closed to a read, never open to a write). The
    # greenfield identity below is the no-map arm of that ternary and stays
    # byte-unchanged.
    return f"{axis}:{value}"


def prefix(axis: str) -> str:
    """The ``<axis>:`` prefix used to recognise this axis's labels.

    Centralises the prefix string so reads (`startswith` / `removeprefix`) and
    the membership-keying in ``required_reviewers`` go through one definition
    rather than open-coding ``"workstream:"`` etc. Equivalent to
    ``label(axis, "")`` but named for the read side.
    """
    # TODO(Task B / DEC-036): in a present-map world an axis bound to a
    # `title-prefix` or `derive` substrate is not recognised by a `<axis>:`
    # label prefix at all; the read side resolves through the same binding the
    # constructor does. The greenfield prefix below is the no-map arm.
    return f"{axis}:"


def read(axis: str, labels: list[str]) -> str | None:
    """The value of axis ``axis`` carried by ``labels``, or ``None`` if absent.

    The parse counterpart to :func:`label`: given an issue's label names, return
    the kit's own value on ``axis`` read off the first ``<axis>:`` label, exactly
    as the inline ``startswith(...) / removeprefix(...)`` reads it replaces. The
    "first match wins" ordering mirrors ``lifecycle_inference.infer_current_state``
    and ``promote-issue``'s state read, which is the established pm contract.

    Returns ``None`` when no label on ``axis`` is present (the caller decides
    whether that is an error, a default, or a no-op — the seam does not).
    """
    pfx = prefix(axis)
    for name in labels:
        if name.startswith(pfx):
            return name.removeprefix(pfx)
    return None


def read_all(axis: str, labels: list[str]) -> list[str]:
    """Every value of axis ``axis`` carried by ``labels`` (order preserved).

    The multi-valued read counterpart for callers that collect *all* labels on
    an axis (e.g. ``validate-issue`` reporting duplicate ``type:*`` labels, or a
    filter dropping every classification label). Mirrors the inline
    ``[lbl for lbl in labels if lbl.startswith("<axis>:")]`` comprehensions,
    returning the parsed *values* (prefix stripped). Use :func:`is_axis_label`
    when the caller wants the full label names rather than the values.
    """
    pfx = prefix(axis)
    return [name.removeprefix(pfx) for name in labels if name.startswith(pfx)]


def is_axis_label(name: str, axis: str) -> bool:
    """True when label ``name`` encodes axis ``axis`` (greenfield prefix match)."""
    return name.startswith(prefix(axis))
