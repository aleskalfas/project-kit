"""Kind ↔ structural-type consistency, the single reader of the DEC-011 table.

The methodology restricts which *structural* types each classification *kind*
may be carried by: a Feature / Umbrella / EPIC always carries kind ``feature``
(they deliver capability work by definition), so a non-``feature`` kind belongs
only on a Task. Filing (or leaving) a non-``feature`` kind on an
epic/feature/umbrella is a **hard-reject** — it manufactures the kind/structural
mismatch that breaks the closing PR's Conventional-Commits ``<type>`` derivation
(open-pr / validate-pr read the closing issue's ``type:*`` label). This is
[project-management:DEC-011-title-formats] ("Filing a Feature with ``type:bug``
is a hard-reject — refused at create-issue and at validate-issue") grounded in
``classification.yaml``'s ``axes.type.structural_restriction``.

This module is the single place that table is read for the consistency check:
``create-issue`` (refuse the mismatch at filing), ``validate-issue`` (flag an
existing mismatched issue), and ``set-field`` (refuse a ``--kind`` that would
introduce the mismatch) all call the predicates here rather than re-deriving the
lookup. Per COR-007, the third writer to want the gate extracts it rather than
duplicating the table a third time.

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
