"""Structural-type inference from an issue title — the one implementation.

An issue's *structural type* (`epic` / `feature` / `umbrella` / `task`) is
carried by its title prefix. Reading it back is needed almost everywhere: to
pick a body template, to choose the parent-ref form, to check the containment
graph, to render a tree. Before this module it was implemented **nine times
across seven divergent bodies**, so the same title resolved differently
depending on which command you asked — `[Docs] …` resolved to `task` under
`move-issue` and to nothing under `show-issue`.

This module is the parity pass `move-issue`'s own docstring called for and
nobody performed. Per COR-007, the recurrence (nine copies) is the trigger to
extract rather than repeat; per ADR-031's sole-constructor discipline applied
to a read, callers ask this module rather than re-deriving the vocabulary.

Three vocabularies, consulted in a fixed precedence
---------------------------------------------------

1. **Adopter prefixes**, when a brownfield `substrate_map` binds the `type`
   axis to `title-prefix`. This SHORT-CIRCUITS: under a map the kit's own
   vocabulary is not the yardstick, so a non-match resolves to `None` rather
   than falling through (#553). A map binding `type` any other way
   (`label` / `derive` / `unsupported` / absent) means the type is not
   title-carried at all — also `None`.
2. **Kit structural prefixes** from `issue-types.yaml` `types[*].title_prefix`
   — `[EPIC]` / `[Feature]` / `[Umbrella]` / `[Task]`.
3. **Kind-driven prefixes** from `classification.yaml`
   `axes.type.title_prefix_by_value` — `[Bug]` / `[Docs]` / `[Test]` /
   `[Refactor]` / `[Chore]`. These only ever resolve to `task`, per
   classification.yaml's `structural_restriction`.
4. **The `type:*` kind label**, as a fallback when no prefix matched — for a
   title whose prefix was edited away. Only ever recovers `task`; a container
   carries no distinguishing kind label and stays unrecoverable, which the
   caller surfaces as malformed.

Callers opt in by what they pass. Passing only `issue_types` reproduces the
prefix-only behaviour exactly, so wiring a previously-prefix-only caller
through this module is behaviour-preserving until it chooses to pass more.
"""

from __future__ import annotations

from typing import Any

from _lib import axis_labels
from _lib.classification_rules import allowed_structural_types_per_kind


def structural_type_from_kind_label(
    labels: list[str],
    classification: dict,
) -> str | None:
    """Recover the structural type from the issue's `type:*` kind label.

    A `type:*` label carries only *kind* and exists only on Tasks: per
    classification.yaml's `structural_restriction`, every non-feature kind maps
    to the single structural type `task`, while feature-kind containers carry no
    distinguishing label. The kind -> structural table is READ from
    `allowed_structural_types_per_kind` rather than hardcoded, so a kind recovers
    a type only when its allowed-set is unambiguous. Ambiguous or unknown -> None.
    """
    kind = axis_labels.read("type", labels)
    if kind is None:
        return None
    allowed = allowed_structural_types_per_kind(classification)
    candidates = allowed.get(kind) if isinstance(allowed, dict) else None
    if isinstance(candidates, list) and len(candidates) == 1:
        only = candidates[0]
        return str(only) if isinstance(only, str) else None
    return None


def infer_structural_type(
    title: str,
    issue_types: dict,
    *,
    classification: dict | None = None,
    labels: list[str] | None = None,
    substrate_map: Any | None = None,
) -> str | None:
    """Infer an issue's structural type from its title. See the module docstring.

    Every parameter beyond `title` and `issue_types` is optional and additive:
    omit `classification` and kind-driven prefixes are not consulted; omit
    `labels` and the label fallback is not attempted. `substrate_map` is
    exclusive — when present it decides the answer alone.
    """
    # 1. Brownfield: the adopter's vocabulary replaces the kit's, or the type
    #    is not title-carried at all. Either way the kit prefixes do not apply.
    if substrate_map is not None:
        if axis_labels.axis_title_prefix_remap("type", substrate_map) is None:
            return None
        return axis_labels.resolve_title_prefix_read("type", title, substrate_map)

    # 2. Kit structural prefixes.
    types = issue_types.get("types") or {}
    for type_name, entry in types.items():
        if not isinstance(entry, dict):
            continue
        prefix = entry.get("title_prefix", "")
        case = entry.get("title_case", "title")
        rendered = str(prefix)
        if case == "upper":
            rendered = rendered.upper()
        if title.startswith(f"[{rendered}] "):
            return str(type_name)

    # 3. Kind-driven prefixes — task-only by construction.
    if classification:
        prefix_by_value = (
            classification.get("axes", {})
            .get("type", {})
            .get("title_prefix_by_value", {})
        )
        for _kind_value, kind_prefix in prefix_by_value.items():
            if isinstance(kind_prefix, str) and title.startswith(f"[{kind_prefix}] "):
                return "task"

    # 4. Fallback: recover from the `type:*` kind label when the prefix is gone.
    if labels and classification:
        return structural_type_from_kind_label(labels, classification)

    return None
