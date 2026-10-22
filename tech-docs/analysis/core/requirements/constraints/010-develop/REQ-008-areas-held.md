---
id: REQ-008
title: "Until #1600 is done, no change adds or removes an area or an adapter a release ships"
status: active
statement: No change adds or removes an area or an adapter that a release ships, or takes `ownership.py` from the `lifecycle` area.
measure: "A release ships the twelve areas and the one adapter, `claude-code`, that #1572 left, and the `lifecycle` area still holds `ownership.py`."
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

# REQ-008 · Constraint · Until #1600 is done, no change adds or removes an area or an adapter a release ships

**Verified by:** A test compares the areas and the adapters a release ships with the lists #1572 left, and fails on any difference. It also fails when the `lifecycle` area no longer holds `ownership.py`. Its message names #1600.

**Imposed by:** ADR-065 point 13. A project may hold an area or an adapter of its own. A later release may ship one of the same name, and its propagation would write over the project's.

Among published releases one such clash can happen, in the `lifecycle` area. A test of that area's content stops propagation before it writes, but cannot tell every case apart. A transition's propagation still writes over a project's own `lifecycle` area that holds a file named `ownership.py`. So ADR-065 point 13 keeps a release from adding another clash until #1600 builds the full check.

The constraint ends when #1600 is done.
