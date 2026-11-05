---
id: REQ-011
title: A suggestion of what to install never uses the network
status: active
statement: A suggestion of a capability to install reads only local capability catalogues and package metadata already fetched, never the network.
measure: With every network connection made to fail, the system gives the same suggestions, and installs nothing, so the manifest holds what it held before.
applies-to: "Every suggestion the system gives of a capability to install. Each is for a data point nothing fills, a role nobody provides, or a capability a process depends on that is not installed. The status report gives them today."
obligation: v1:sha256:4f96065de8a363cd71d0e3a16f8ba15632ba8bfa26b74bf6e9a372888387a581
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/capability_plans.py
        - tests/test_capability_plans.py
      record:
        - COR-053#8
      artefact:
        - ACT-adopter
---

# REQ-011 · Constraint · A suggestion of what to install never uses the network

**Verified by:** A test runs `pkit status` with every network connection made to fail. It finds the suggestion of a [capability](../../../glossary.md#term-capability--capability) the local capability catalogue holds for a [data point](../../../glossary.md#term-data-point--data-point) nothing fills, and finds the [manifest](../../../glossary.md#term-manifest--manifest) unchanged.

**Imposed by:** [COR-053 point 8](../../../../../../.pkit/decisions/core/COR-053-connection-points.md#8-discovery-a-plan-predicts-the-wiring-exactly) lets `pkit status` suggest an available [capability](../../../glossary.md#term-capability--capability) where a [data point](../../../glossary.md#term-data-point--data-point) is unfilled. The suggestion reads "only local catalogues and manifests already fetched, never the network", and it is never an action.

The record imposes the limit on a suggestion for a data point. This requirement holds the suggestion for a [role](../../../glossary.md#term-role--role) nobody provides, or a capability a process depends on that is not installed, to the same limit.
