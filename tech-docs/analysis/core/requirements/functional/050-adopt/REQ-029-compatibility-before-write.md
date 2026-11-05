---
id: REQ-029
title: A version transition resolves compatibility across components before it writes anything
status: active
statement: A version transition resolves compatibility across components before it writes anything.
measure: Where a component's range excludes the target backbone, or a dependency gate refuses, the version transition refuses and names each conflict. Every file of the project then holds what it held before, the manifests included.
applies-to: "Every version transition: of the backbone, by `pkit upgrade` and by `pkit pin` to a newer release, and of one capability, by `pkit capabilities upgrade`."
obligation: v1:sha256:736287a6616cbb1571133a9ce2b0f7c0dd6f5cf23a81d57b6ef5ade80d4f84ac
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/upgrade.py
        - src/project_kit/capabilities.py
        - tests/test_upgrade.py
        - tests/test_capabilities.py
      record:
        - COR-010
        - ADR-065#4
        - ADR-065#6
      artefact:
        - ACT-adopter
---

# REQ-029 · Functional · A version transition resolves compatibility across components before it writes anything

**Verified by:** Tests of `pkit upgrade` find that it refuses a [component](../../../glossary.md#term-component--component) whose new [range](../../../glossary.md#term-range--range) excludes the target, reading the range as the resolver does. Tests of its [dependency gates](../../../glossary.md#term-dependency-gate--dependency-gate) find that they refuse a moving [capability](../../../glossary.md#term-capability--capability) whose dependency is missing or out of range. Every file then holds what it held before. Tests of `pkit capabilities upgrade` find that it refuses a [version](../../../glossary.md#term-version--version) whose range excludes the recorded [backbone](../../../glossary.md#term-backbone--backbone), or whose dependencies do not hold.

**Rationale:** The adopter upgrades like a dependency, so a conflict must show before the [project](../../../glossary.md#term-project--project) changes, as a package manager's resolver runs before it installs. [COR-010](../../../../../../.pkit/decisions/core/COR-010-resource-lifecycle.md) resolves compatibility across all installed [components](../../../glossary.md#term-component--component) before any [migration](../../../glossary.md#term-migration--migration), or refuses with the conflict surfaced. [ADR-065 point 4](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#4-a-transition-runs-in-cor-010s-order-with-seed-paths-after-the-migrations) puts that resolution in a [version transition](../../../glossary.md#term-version-transition--version-transition)'s first step, where each check may refuse and none writes.
