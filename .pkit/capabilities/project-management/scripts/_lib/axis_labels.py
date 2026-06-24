"""The sole constructor of methodology axis-labels, and the substrate-map read seam (ADR-026).

A *methodology axis* is one of the conceptual dimensions the capability tracks
on an issue — ``type``, ``priority``, ``workstream``, ``state`` (lifecycle). In
the kit's own (greenfield) substrate each axis is encoded as a label of the
form ``<axis>:<value>`` (e.g. ``priority:High``, ``state:in-progress``). Those
labels used to be string-formatted inline at ~26 write-path sites scattered
across the mutating scripts; Task A pulled every such construction (and the
matching read) behind this one seam.

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

What Task B grows (this module's resolution layer)
--------------------------------------------------
Task B adds the ``substrate-map.yaml`` read path ADR-026 pins. The seam now
answers a **ternary per axis**, never a binary:

  * **No ``substrate-map.yaml`` at all** ⇒ every axis resolves to the kit's own
    ``<axis>:<value>`` label, **byte-unchanged**. The legacy functions
    (:func:`label`, :func:`prefix`, :func:`read`, :func:`read_all`,
    :func:`is_axis_label`) are the no-map (greenfield) arm and keep their exact
    Task-A behaviour — the ~38 call sites Task A routed are untouched.
  * **A map present, axis bound** ⇒ resolve through the declared binding (a
    ``label`` value→value remap, a ``title-prefix`` remap, or a ``derive``
    predicate). :func:`resolve_write` returns the adopter's OWN substrate value.
  * **A map present, axis ``unsupported`` OR absent-from-a-present-map** ⇒
    the seam returns :data:`DEGRADE`; it emits **no write-label**. Absence is
    treated as ``unsupported``, NOT greenfield — the load-bearing rule.
  * **value-unresolvable within a *bound* axis** (a methodology value with no
    entry in the binding's remap — e.g. ``feature`` when only ``[Task]`` /
    ``[Epic]`` prefixes exist) ⇒ :func:`resolve_write` returns :data:`DEGRADE`
    for *that value only*. This is distinct from axis-``unsupported``: the axis
    is :data:`SERVED`, only the one value is missing, so it must degrade only
    the rules depending on that value — never the axis as a whole (which would
    silently soften the type-keyed Feature-in-Feature containment invariant
    DEC-036 D4 holds hard).

**Fail-closed (ADR-026 part (ii)).** :func:`resolve_write` NEVER returns the
kit's own ``<axis>:<value>`` label as a write target in a present-map world. It
returns the adopter's substrate value on the determinate paths and
:data:`DEGRADE` on the indeterminate ones. The kit's own label is reachable as a
*write target* only via the no-map identity arm (greenfield), where it is the
adopter's own substrate.

Scope held to Task B
--------------------
This grows the seam's *resolution API* and makes ``pre-check`` (the first
consumer) degrade. It does **not** rewire the ~26 inline-write sites
(``create-issue`` / ``bootstrap`` / ``move-issue`` / …) to call
:func:`resolve_write` — that write-side refactor (what makes sole-constructor
*structural* rather than merely *available*) is the sibling Wave-2 write-side
guard work, out of Task B's scope. Those sites stay on :func:`label`, which is
correct in greenfield (the only mode they are exercised in today). When a future
author routes them through :func:`resolve_write`, the fail-closed posture below
already does the right thing. The ``derive`` predicate ENGINE (the DEC-033
detector swap, reduced state set, no-op position collapse) is likewise sibling
work; this module reads the ``derive`` *binding shape* and surfaces it, but does
not evaluate predicates.

The module is deliberately content-free about *which* values are valid on an
axis — that vocabulary lives in ``classification.yaml`` / ``issue-types.yaml`` /
``workflow.yaml`` and is read by the callers. This seam owns the ``<axis>:<value>``
encoding and the adopter-substrate remap; nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError
except ImportError:  # pragma: no cover
    YAML = None  # type: ignore[assignment, misc]
    YAMLError = Exception  # type: ignore[assignment, misc]


# The four methodology axes the kit encodes as `<axis>:<value>` labels in its
# own (greenfield) substrate. This tuple is the allow-list the sole-constructor
# guard keys on; it is the one place the axis names live.
AXES: tuple[str, ...] = ("type", "priority", "workstream", "state")

# Where the optional adopter substrate-map lives, relative to the capability
# root. Absent ⇒ greenfield (the seam is inert).
SUBSTRATE_MAP_RELATIVE_PATH = "project/substrate-map.yaml"

CAPABILITY_NAME = "project-management"


# ----- the degrade sentinel + disposition vocabulary ---------------------


class _Degrade:
    """The fail-closed sentinel :func:`resolve_write` returns instead of a
    write-label when an axis (or a value within a bound axis) cannot be resolved
    to a substrate the adopter owns.

    A distinct singleton (not ``None``) so a caller cannot mistake "degrade" for
    "no label present" or accidentally write it: it is not a string, so any site
    that tries to use it as a label name fails loudly rather than emitting the
    sentinel's repr onto the tracker. ADR-026 part (ii): the seam emits no
    write-label on the indeterminate paths.
    """

    _instance: "_Degrade | None" = None

    def __new__(cls) -> "_Degrade":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "<axis_labels.DEGRADE>"

    def __bool__(self) -> bool:
        # Falsy so `if resolve_write(...)` reads naturally as "did it resolve?".
        return False


DEGRADE: _Degrade = _Degrade()

# An axis's capability disposition — the seam's binary read of the ADR-026
# ternary, the signal a degrading consumer (pre-check's capability matrix)
# reports.
#   served      — the axis resolves through a binding (or greenfield identity);
#                 its rules run at their authored severity.
#   unsupported — the axis is explicitly `unsupported` or absent from a present
#                 map (absent ≡ unsupported, the load-bearing rule); the rules
#                 depending on it degrade.
# This is the only distinction the seam can make without the consumer's schema.
# Whether a degraded (`unsupported`) axis softens its rules to advisory (a
# `*_severity` knob exists to flip) or disables the feature outright is the
# consumer's call — it knows which of its rules carry a knob. The seam reports
# only `served` vs `unsupported` — see `axis_disposition`.
Disposition = Literal["served", "unsupported"]


# ----- the substrate map (parsed view) -----------------------------------


@dataclass(frozen=True)
class SubstrateMap:
    """A parsed ``substrate-map.yaml`` — the per-axis bindings.

    ``axes`` maps an axis name to its raw binding mapping (one of ``label`` /
    ``title-prefix`` / ``derive`` / ``unsupported``, plus an optional
    ``default``). An axis NOT in this mapping is absent-from-a-present-map and
    resolves identically to ``unsupported`` (ADR-026 the load-bearing rule).

    A ``SubstrateMap`` instance existing at all means *a map is present* — the
    no-map (greenfield) case is represented by ``None``, never by an empty
    ``SubstrateMap``. That keeps "the file exists but lists no axes" (every axis
    degrades) distinct from "no file" (every axis is greenfield).
    """

    axes: dict[str, dict[str, Any]]


def load_substrate_map(capability_root: Path | None = None) -> SubstrateMap | None:
    """Load the adopter's ``substrate-map.yaml``, or ``None`` when absent.

    ``None`` is the greenfield signal (no map ⇒ identity); a returned
    :class:`SubstrateMap` means a map is present and the ternary is in effect.
    ``capability_root`` defaults to walking up from CWD for
    ``.pkit/capabilities/project-management/`` (mirrors the discovery the other
    ``_lib`` modules use); pass it explicitly when the caller already knows it
    (pre-check does).

    A file that is present but unparseable or not a mapping is treated as
    **present-but-empty** (a :class:`SubstrateMap` with no axes ⇒ every axis
    degrades), never as greenfield — fail closed: a malformed map must not
    silently re-enter greenfield writes. The loader does NOT itself raise or
    report the parse error — its sole job is to refuse the greenfield
    fall-through. Diagnosability is the consumer's: pre-check re-reads the file
    and reports a distinct "present but unparseable/invalid — degrading all
    axes" line (see ``pre-check._check_substrate_map_parse``) so a typo'd map is
    not mistaken for a deliberate all-``unsupported`` config. Without that
    consumer-side report a malformed map would degrade silently — which is why
    a consumer that loads a map should also surface its parse health.
    """
    if capability_root is None:
        capability_root = _resolve_capability_root()
    if capability_root is None:
        return None
    path = capability_root / SUBSTRATE_MAP_RELATIVE_PATH
    if not path.is_file():
        return None
    if YAML is None:  # pragma: no cover
        return SubstrateMap(axes={})
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        # Present-but-unparseable ⇒ degrade-all, not greenfield (fail closed).
        return SubstrateMap(axes={})
    if not isinstance(data, dict):
        return SubstrateMap(axes={})
    raw_axes = data.get("axes")
    axes: dict[str, dict[str, Any]] = {}
    if isinstance(raw_axes, dict):
        for axis, binding in raw_axes.items():
            if isinstance(axis, str) and isinstance(binding, dict):
                axes[axis] = binding
    return SubstrateMap(axes=axes)


# ----- the ternary resolution API (ADR-026) ------------------------------


def axis_disposition(
    axis: str, substrate_map: SubstrateMap | None
) -> Disposition:
    """Whether ``axis`` is SERVED or degrades, per the ADR-026 ternary.

    * No map (``substrate_map is None``) ⇒ ``"served"`` (greenfield identity).
    * Map present, axis bound (``label`` / ``title-prefix`` / ``derive``) ⇒
      ``"served"``.
    * Map present, axis ``unsupported`` OR absent from the map ⇒
      ``"unsupported"`` (absent ≡ unsupported, the load-bearing rule).

    Note this is *axis-level* disposition. A SERVED axis can still have
    individual values that are value-unresolvable within its binding (the fourth
    arm) — that is :func:`resolve_write` returning :data:`DEGRADE` for the value,
    NOT this function returning ``"unsupported"``. Collapsing the two would
    soften every rule keyed on the axis (ADR-026 §2's fourth arm).

    The consumer maps ``"unsupported"`` onto its own advisory-vs-disabled call
    (it knows which of its rules have a ``*_severity`` knob); the seam reports
    only the served/degraded binary it can know without the consumer's schema.
    """
    if substrate_map is None:
        return "served"
    binding = substrate_map.axes.get(axis)
    if binding is None:
        # Absent from a present map ⇒ unsupported (NOT greenfield).
        return "unsupported"
    if binding.get("unsupported") is True:
        return "unsupported"
    if any(key in binding for key in ("label", "title-prefix", "derive")):
        return "served"
    # A binding mapping with none of the four arms is malformed; fail closed.
    return "unsupported"


def workstream_mutator_refusal(
    capability_root: Path | None = None,
) -> str | None:
    """The constraint-1 gate for the workstream-label MUTATORS (RF-2, #265).

    The five mutators (``add`` / ``remove`` / ``merge`` / ``rename`` /
    ``split-workstream``) create / delete / rename kit ``workstream:*`` labels via
    ``gh label``. Under a PRESENT substrate-map whose ``workstream`` axis is
    ``unsupported`` (or absent — absent ≡ unsupported, the load-bearing rule),
    creating a kit ``workstream:*`` label would violate "never write an unmanaged
    label" (DEC-036, EPIC #217 constraint 1).

    Returns an advisory string the caller prints before refusing (exit 1) when
    the gate trips, or ``None`` when the mutator may proceed:

    * **Greenfield** (no map) ⇒ ``None`` — the kit's ``workstream:*`` labels ARE
      the adopter's substrate; mutators run unchanged.
    * **Map present, ``workstream`` SERVED** (bound to ``label`` / ``title-prefix``
      / ``derive``) ⇒ ``None`` here — but note this minimal gate does NOT yet do
      the richer present-map mutator behaviour (validate-against-the-bound-set /
      retag); that is the ``adopt-existing`` Feature #264. This function only
      blocks the constraint-1 violation (the ``unsupported`` arm).
    * **Map present, ``workstream`` ``unsupported`` / absent** ⇒ a refusal string.

    This is deliberately the MINIMAL safe gate, not the full present-map mutator
    feature: it prevents an unmanaged label ever being created, and defers the
    richer behaviour to #264.
    """
    substrate_map = load_substrate_map(capability_root)
    if axis_disposition("workstream", substrate_map) == "unsupported":
        return (
            "workstream is unsupported under your substrate-map; this label "
            "mutator is disabled — manage your workstream substrate directly. "
            "(Richer present-map workstream management — validate-against-the-"
            "bound-set, retag — is tracked as the adopt-existing Feature #264.)"
        )
    return None


def resolve_write(
    axis: str, value: str, substrate_map: SubstrateMap | None
) -> str | _Degrade:
    """Resolve the substrate value to WRITE for ``(axis, value)``, or :data:`DEGRADE`.

    The fail-closed write-path resolver (ADR-026 part (ii)). It returns:

    * **No map** ⇒ the kit's own ``<axis>:<value>`` label — greenfield identity.
      This is the ONLY arm that returns the kit's own label; in greenfield the
      kit's label *is* the adopter's substrate, so this is not a fall-through.
    * **Map present, axis bound to ``label``** ⇒ the adopter's remapped label
      string (e.g. ``P0``), NOT ``priority:P0``. :data:`DEGRADE` if ``value`` has
      no entry in the remap (value-unresolvable — the fourth arm).
    * **Map present, axis bound to ``title-prefix``** ⇒ the adopter's prefix
      string (e.g. ``[Task]``). :data:`DEGRADE` if ``value`` has no entry.
    * **Map present, axis bound to ``derive``** ⇒ :data:`DEGRADE`. A derived
      (predicate) axis has no write-label — state is written by closing/opening
      the issue, not by labelling it; the detector engine (sibling work) owns
      that. The seam refuses to invent one.
    * **Map present, axis ``unsupported`` / absent / malformed** ⇒
      :data:`DEGRADE`.

    Crucially, in a present-map world there is NO arm that returns the kit's own
    ``<axis>:<value>`` as a write target — the unsafe direction is unreachable.
    Callers test the result with ``if result is DEGRADE`` (or its falsiness) and
    take the degrade path; they never write :data:`DEGRADE` (it is not a string).
    """
    if substrate_map is None:
        # Greenfield identity — the kit's own label IS the adopter's substrate.
        return label(axis, value)

    binding = substrate_map.axes.get(axis)
    if binding is None:
        return DEGRADE  # absent ≡ unsupported
    if binding.get("unsupported") is True:
        return DEGRADE

    label_binding = binding.get("label")
    if isinstance(label_binding, dict):
        remap = label_binding.get("remap")
        if isinstance(remap, dict):
            mapped = remap.get(value)
            if isinstance(mapped, str) and mapped:
                return mapped
        return DEGRADE  # value-unresolvable within a bound axis (fourth arm)

    prefix_binding = binding.get("title-prefix")
    if isinstance(prefix_binding, dict):
        remap = prefix_binding.get("remap")
        if isinstance(remap, dict):
            mapped = remap.get(value)
            if isinstance(mapped, str) and mapped:
                return mapped
        return DEGRADE  # value-unresolvable within a bound axis (fourth arm)

    if "derive" in binding:
        # A derived axis has no write-label; the detector engine owns state
        # transitions. Refuse to invent one (fail closed).
        return DEGRADE

    # Malformed binding (none of the four arms matched) ⇒ fail closed.
    return DEGRADE


def axis_default(
    axis: str, substrate_map: SubstrateMap | None
) -> str | None:
    """The optional ``default:`` substrate value declared for ``axis``, or ``None``.

    A write-side hint the adopter declares to seed an axis when the caller
    supplies no value (e.g. ``P1`` for a priority axis). The READ seam never
    invents it — it is surfaced for the writer to apply. ``None`` in greenfield
    (no map) and whenever the axis declares no ``default``.
    """
    if substrate_map is None:
        return None
    binding = substrate_map.axes.get(axis)
    if not isinstance(binding, dict):
        return None
    default = binding.get("default")
    return default if isinstance(default, str) and default else None


# ----- greenfield identity arm (Task A — byte-unchanged) ------------------
# These are the no-map arm of the ternary above. Every one of the ~38 call
# sites Task A routed calls these; their greenfield behaviour is frozen by
# `test_pm_axis_label_seam_parity`. Do NOT thread the map through them — the
# present-map consumers call `resolve_write` / `axis_disposition` instead.


def label(axis: str, value: str) -> str:
    """The kit's own ``<axis>:<value>`` label — the greenfield (no-map) encoding.

    This is the **sole constructor** of an axis-label on a write path (ADR-026
    part (i)): mutating scripts obtain a label to write *only* by calling here,
    never by string-formatting ``<axis>:<value>`` themselves. The grep/AST guard
    enforces that no mutating script reintroduces an inline literal.

    In a present-map world a write target is resolved through
    :func:`resolve_write` (which fails closed to :data:`DEGRADE` on an
    unsupported/absent/value-unresolvable axis), NOT through this function. This
    function is the no-map identity arm: greenfield output is byte-identical to
    the inline ``f"{axis}:{value}"`` it replaced.

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
        The kit's own label name for this (axis, value).
    """
    return f"{axis}:{value}"


def prefix(axis: str) -> str:
    """The ``<axis>:`` prefix used to recognise this axis's labels (greenfield).

    Centralises the prefix string so reads (`startswith` / `removeprefix`) and
    the membership-keying in ``required_reviewers`` go through one definition
    rather than open-coding ``"workstream:"`` etc. Equivalent to
    ``label(axis, "")`` but named for the read side.

    In a present-map world an axis bound to a ``title-prefix`` or ``derive``
    substrate is not recognised by a ``<axis>:`` label prefix at all; such reads
    resolve through the binding. This function is the no-map arm.
    """
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


# ----- capability-root discovery (shared shape) --------------------------


def _resolve_capability_root() -> Path | None:
    """Walk up from CWD looking for .pkit/capabilities/project-management/.

    Mirrors the discovery in ``_lib.hooks`` and ``pre-check`` so the seam can
    locate the optional ``substrate-map.yaml`` without every caller threading a
    root through. Callers that already know the root pass it to
    :func:`load_substrate_map` directly.
    """
    cur = Path.cwd()
    while cur != cur.parent:
        candidate = cur / ".pkit" / "capabilities" / CAPABILITY_NAME
        if candidate.is_dir():
            return candidate
        cur = cur.parent
    return None
