---
id: REQ-029
title: A version transition resolves compatibility across components before it writes anything
status: active
statement: A version transition resolves compatibility across components before it writes anything.
measure: Where a component's range excludes the target backbone, or a dependency gate refuses, the transition refuses and names each conflict. Every file of the project then holds what it held before, the manifests included.
applies-to: "Every version transition: of the backbone, by `pkit upgrade` and by `pkit pin` to a newer release, and of one capability, by `pkit capabilities upgrade`."
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_upgrade.py
        - tests/test_capabilities.py
      record:
        - COR-010
        - ADR-065#4
        - ADR-065#6
      artefact:
        - ACT-adopter
    revalidated:
      at: 2026-10-25T14:34:33Z
      outcome: unchanged
      unchanged-because: tests/test_upgrade.py gains only a test that upgrade's lookup of the latest release skips the tag latest. No test of compatibility resolved before a write changed, so the requirement holds.
---

# REQ-029 · Functional · A version transition resolves compatibility across components before it writes anything

**Verified by:** Tests of `pkit upgrade` find that it refuses a [component](../../../glossary.md#term-component--component) whose new [range](../../../glossary.md#term-range--range) excludes the target, reading the range as the resolver does. Tests of its dependency gates find that they refuse a moving [capability](../../../glossary.md#term-capability--capability) whose dependency is missing or out of range. Every file then holds what it held before. Tests of `pkit capabilities upgrade` find that it refuses a [version](../../../glossary.md#term-version--version) whose range excludes the recorded [backbone](../../../glossary.md#term-backbone--backbone), or whose dependencies do not hold.

**Rationale:** The adopter upgrades like a dependency, so a conflict must show before the [project](../../../glossary.md#term-project--project) changes, as a package manager's resolver runs before it installs. COR-010 resolves compatibility across all installed [components](../../../glossary.md#term-component--component) before any [migration](../../../glossary.md#term-migration--migration), or refuses with the conflict surfaced. ADR-065 [point](../../../glossary.md#term-point--point) 4 puts that resolution in a transition's first step, where each check may refuse and none writes.
