---
id: REQ-008
title: "Until #1600 is done, no change adds an area or an adapter a release ships, other than the `rule-sets` area, and none removes one"
status: active
statement: No change adds an area or an adapter that a release ships, other than the `rule-sets` area, and no change removes an area or an adapter, or takes `ownership.py` from the `lifecycle` area.
measure: "A release ships the twelve areas and the one adapter, `claude-code`, that #1572 left, and the `rule-sets` area. The `lifecycle` area still holds `ownership.py`."
applies-to: "Every change in the methodology's source repository, and so every release made from it. It holds until #1600, which builds the full check of a clash of area names, is done."
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_area_name_clash.py
      record:
        - ADR-065#13
      artefact:
        - ACT-adopter
---

# REQ-008 · Constraint · Until #1600 is done, no change adds an area or an adapter a release ships, other than the `rule-sets` area, and none removes one

**Verified by:** A test compares the [areas](../../../glossary.md#term-area--area) and the [adapters](../../../glossary.md#term-adapter--adapter) a [release](../../../glossary.md#term-release--release) ships with the lists #1572 left, with `rule-sets` among the areas. It fails on any difference. It also fails when the `lifecycle` area no longer holds `ownership.py`. Its message names #1600 and the exception.

**Imposed by:** [ADR-065 point 13](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#13-a-transition-and-sync-stop-on-a-clash-of-area-names-and-no-core-area-but-rule-sets-is-added-until-1600). A [project](../../../glossary.md#term-project--project) may hold an [area](../../../glossary.md#term-area--area) or an [adapter](../../../glossary.md#term-adapter--adapter) of its own. A later [release](../../../glossary.md#term-release--release) may ship one of the same name, and its [propagation](../../../glossary.md#term-propagation--propagation) would write over the project's.

Among published releases one such clash can happen, in the `lifecycle` area. A test of that area's content stops propagation before it writes, but cannot tell every case apart. A transition's propagation still writes over a project's own `lifecycle` area that holds a file named `ownership.py`. So ADR-065 point 13 keeps a release from adding another clash until #1600 builds the full check.

One area passes the hold: `rule-sets`, where the [backbone](../../../glossary.md#term-backbone--backbone) keeps its method [rule sets](../../../glossary.md#term-rule-set--rule-set). A project has no use for an area of that name, since every file in it is read as a rule set the backbone ships. The exception is no precedent (ADR-065 point 13).

The constraint ends when #1600 is done.
