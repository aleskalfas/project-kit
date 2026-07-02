"""Kind ↔ structural-type consistency, the single reader of the DEC-011 table.

The methodology restricts which *structural* types each classification *kind*
may be carried by: a Feature / Umbrella / EPIC always carries kind ``feature``
(they deliver capability work by definition), so a non-``feature`` kind belongs
only on a Task. Filing (or leaving) a non-``feature`` kind on an
epic/feature/umbrella is a **hard-reject** — it manufactures the kind/structural
mismatch that breaks the closing PR's Conventional-Commits ``<type>`` derivation
(open-pr / validate-pr read the closing issue's ``type:*`` label). This is
[project-management:DEC-011-title-formats], grounded in ``classification.yaml``'s
``axes.type.structural_restriction``: refused outright at create-issue, and by
validate-issue as a hard-reject at its create phase but a warning at transition
phase (the mismatch is a create-time concern, not a lifecycle-move one).

This module is the single place that table is read for the consistency check:
``create-issue`` (refuse the mismatch at filing), ``validate-issue`` (flag a
mismatch — hard-reject at create phase, warning at transition phase), and
``set-field`` (refuse a ``--kind`` that would introduce the mismatch) all call
the predicates here rather than re-deriving the lookup. Per COR-007, the third
writer to want the gate extracts it rather than duplicating the table a third
time.

It is likewise the single reader of the *value → conv-type* bridge
(:func:`conv_type_for_kind` over ``pr_type_mapping``) and of the *title-prefix →
value* reverse read (:func:`kind_from_title` over ``title_prefix_by_value``):
``open-pr`` derives the PR title's Conventional-Commits ``<type>`` and
``start-work`` / ``review-work`` derive the branch prefix (DEC-013) through these
readers rather than each carrying a private ``type:*`` → prefix dict. Feeding the
kit *value* (resolved via ``axis_labels.read`` on the label arm, or
:func:`kind_from_title` on the title-prefix arm) into one lookup is what makes the
conv-type resolve identically greenfield and brownfield (the ADR-026 read-path
seam applied to the branch-prefix derivation).

The module is dependency-free at import time (no YAML load) so any PEP 723 script
can import it regardless of its declared dependencies — callers load
``classification.yaml`` themselves and pass the parsed dict in. It is content-free
about the *values* (kinds, structural types) — that vocabulary lives in
``classification.yaml`` / ``issue-types.yaml`` and is read from the passed dict.

Degrade posture (thin / board-less classification): when the table is empty or
absent, there is no restriction to ground, so :func:`kind_allowed_for_structural_type`
returns ``True`` (permit — the gate refuses nothing it cannot ground in the
schema) and :func:`kind_drives_title` returns ``False`` (fall back to the
structural title prefix). This mirrors the permissive degrade the three writers
carried before the extraction.
"""

from __future__ import annotations

from typing import Any


# The default kind every structural type carries implicitly. A structural type
# reachable ONLY by this kind is NOT kind-driven at the title level (it uses its
# structural prefix); a type reachable by some OTHER kind is kind-driven.
DEFAULT_KIND = "feature"


def allowed_structural_types_per_kind(classification: dict) -> dict:
    """The ``axes.type.structural_restriction.allowed_structural_types_per_kind`` map.

    The single source of truth (``classification.yaml``) for which structural
    types each kind may be carried by — the map DEC-011 names as the
    kind/structural restriction. Empty / absent / malformed ⇒ ``{}`` (no
    restriction declared).
    """
    axes = classification.get("axes") if isinstance(classification, dict) else None
    type_axis = axes.get("type") if isinstance(axes, dict) else None
    restriction = (
        type_axis.get("structural_restriction") if isinstance(type_axis, dict) else None
    )
    allowed = (
        restriction.get("allowed_structural_types_per_kind")
        if isinstance(restriction, dict)
        else None
    )
    return allowed if isinstance(allowed, dict) else {}


def kind_allowed_for_structural_type(
    kind: str, structural_type: str, classification: dict
) -> bool:
    """Whether ``kind`` may be carried by ``structural_type`` per the restriction.

    Reads :func:`allowed_structural_types_per_kind` (single source of truth).

    * Table empty / absent ⇒ ``True`` (permissive degrade — a thin or board-less
      classification declares no restriction, so the gate refuses nothing it
      cannot ground in the schema).
    * ``kind`` absent from the table ⇒ ``True`` (no declared restriction for that
      kind; permit).
    * Otherwise ⇒ ``structural_type`` is in the kind's allowed list.
    """
    allowed = allowed_structural_types_per_kind(classification)
    if not allowed:
        return True
    types = allowed.get(kind)
    if not isinstance(types, list):
        return True
    return structural_type in types


def mismatch_severity_token(classification: dict) -> str | None:
    """The ``structural_restriction.mismatch_severity`` token, or ``None``.

    The ``[validation-severity:<id>]`` token the schema tags a kind/structural
    mismatch with (``hard-reject`` in the shipped classification). A caller that
    reports a finding parses this through its own severity-token reader so the
    finding carries the schema's authored severity rather than a hardcoded one.
    ``None`` when the restriction (or the field) is absent — the caller decides
    the fallback.
    """
    axes = classification.get("axes") if isinstance(classification, dict) else None
    type_axis = axes.get("type") if isinstance(axes, dict) else None
    restriction = (
        type_axis.get("structural_restriction") if isinstance(type_axis, dict) else None
    )
    token = (
        restriction.get("mismatch_severity") if isinstance(restriction, dict) else None
    )
    return token if isinstance(token, str) and token else None


def title_prefix_by_value(classification: dict) -> dict:
    """The ``axes.type.title_prefix_by_value`` map from ``classification.yaml``.

    The map create-issue's / set-field's title composition reads to couple a
    kind to its ``[Prefix]``. Lives here beside the restriction table because
    :func:`kind_drives_title` reads both together. Empty / absent ⇒ ``{}``.
    """
    axes = classification.get("axes") if isinstance(classification, dict) else None
    type_axis = axes.get("type") if isinstance(axes, dict) else None
    mapping = (
        type_axis.get("title_prefix_by_value") if isinstance(type_axis, dict) else None
    )
    return mapping if isinstance(mapping, dict) else {}


def kind_from_title(title: str, classification: dict) -> str | None:
    """The kit type *value* a ``[Prefix]`` title carries, or ``None``.

    The reverse of :func:`title_prefix_by_value`: given an issue title like
    ``"[Bug] hostname mismatch"`` and the classification's
    ``title_prefix_by_value`` map (``{bug: Bug, ...}``), recover the kit's own
    kind value (``bug``). This is the read side of the ``type`` axis's
    ``title-prefix`` substrate — the arm ``axis_labels.read("type", labels)``
    cannot serve, because a brownfield adopter carries the kind in the bracket
    prefix and no ``type:*`` label exists to read. Mirrors how
    ``move-issue._structural_type_from_title`` reads the prefix (``title``
    ``startswith(f"[{prefix}] ")``), so the two title reads agree by construction.

    Empty / absent map ⇒ ``None`` (no title-prefix vocabulary to match). A title
    with no recognised bracket prefix ⇒ ``None`` (the caller decides the
    fallback). First match wins over the map's iteration order; the shipped map
    is one-to-one so ordering is immaterial.
    """
    prefix_by_value = title_prefix_by_value(classification)
    for value, prefix in prefix_by_value.items():
        if isinstance(prefix, str) and prefix and title.startswith(f"[{prefix}] "):
            return str(value)
    return None


def conv_type_for_kind(kind: str, classification: dict) -> str | None:
    """The closing PR's Conventional-Commits ``<type>`` for kit kind ``kind``.

    The single reader of ``classification.yaml``'s top-level ``pr_type_mapping``
    (``[{issue_label_value: bug, pr_conv_type: fix}, ...]``) — the table that
    bridges an issue's kit type value to the branch/PR conv-type. ``open-pr``
    (PR-title derivation), ``start-work`` and ``review-work`` (branch-prefix
    derivation, DEC-013) all read the SAME table here rather than each carrying a
    private ``type:*`` → prefix dict (COR-007 single source; the private dicts in
    the two work-wrappers were the ADR-026 read-bypass this consolidates).

    ``kind`` is the kit's own value (``bug`` / ``feature`` / ...), NOT a raw
    ``type:*`` label — callers resolve the value first, through
    ``axis_labels.read("type", labels)`` (label arm) or :func:`kind_from_title`
    (title-prefix arm), so greenfield and brownfield feed the same lookup. Empty /
    absent mapping, or a ``kind`` with no entry ⇒ ``None`` (the caller decides
    whether that is an error or a default).
    """
    axes_source = classification if isinstance(classification, dict) else {}
    mapping = axes_source.get("pr_type_mapping") or []
    if not isinstance(mapping, list):
        return None
    for entry in mapping:
        if not isinstance(entry, dict):
            continue
        if entry.get("issue_label_value") == kind:
            conv_type = entry.get("pr_conv_type")
            return str(conv_type) if isinstance(conv_type, str) and conv_type else None
    return None


def kind_drives_title(structural_type: str, classification: dict) -> bool:
    """Whether the ``type`` (kind) axis drives the title prefix for ``structural_type``.

    Reads the restriction table rather than hardcoding ``task``: a structural
    type is kind-driven iff it is reachable by a kind OTHER than the default
    ``feature`` (today only ``task`` is, per ``allowed_structural_types_per_kind``).
    Those types take their prefix from ``title_prefix_by_value[<kind>]``; the rest
    carry kind ``feature`` and use their structural prefix. Empty / absent
    classification ⇒ ``False`` (degrade to the structural prefix).
    """
    prefix_by_value = title_prefix_by_value(classification)
    allowed = allowed_structural_types_per_kind(classification)
    if not allowed:
        return False
    for kind, types in allowed.items():
        if kind == DEFAULT_KIND or kind not in prefix_by_value:
            continue
        if isinstance(types, list) and structural_type in types:
            return True
    return False
