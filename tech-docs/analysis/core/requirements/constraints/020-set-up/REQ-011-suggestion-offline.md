---
id: REQ-011
title: A suggestion of what to install never uses the network
status: active
statement: A suggestion of a capability to install reads only local catalogues and manifests already fetched, never the network.
measure: With every network connection made to fail, the system gives the same suggestions, and installs nothing, so the manifest holds what it held before.
applies-to: "Every suggestion the system gives of a capability to install, for a data point nothing fills, a role nobody provides or an upstream not installed. The status report gives them today."
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_capability_plans.py
      record:
        - COR-053#8
      artefact:
        - ACT-adopter
    revalidated:
      at: 2026-10-24T10:39:15Z
      outcome: unchanged
      unchanged-because: ACT-adopter's need says "Upgrade the system" for "Upgrade it", and "a version the whole project pins" for "a version pinned for the whole project". The need is the same, so this artefact holds.
---

# REQ-011 · Constraint · A suggestion of what to install never uses the network

**Verified by:** A test runs the status [report](../../../glossary.md#term-report--report) with every network connection made to fail. It finds the suggestion of a [capability](../../../glossary.md#term-capability--capability) the local catalogue holds for a [data point](../../../glossary.md#term-data-point--data-point) nothing fills, and finds the [manifest](../../../glossary.md#term-manifest--manifest) unchanged.

**Imposed by:** COR-053 [point](../../../glossary.md#term-point--point) 8 lets the status [report](../../../glossary.md#term-report--report) suggest an available [capability](../../../glossary.md#term-capability--capability) where a [data point](../../../glossary.md#term-data-point--data-point) is unfilled. The suggestion reads "only local catalogues and manifests already fetched, never the network", and it is never an action.

The record imposes the limit on a suggestion for a data point. This requirement holds the suggestion for a [role](../../../glossary.md#term-role--role) nobody provides, or an upstream not installed, to the same limit.
