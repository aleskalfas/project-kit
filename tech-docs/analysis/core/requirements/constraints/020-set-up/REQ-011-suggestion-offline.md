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
---

# REQ-011 · Constraint · A suggestion of what to install never uses the network

**Verified by:** A test runs the status report with every network connection made to fail. It finds the suggestion of a capability the local catalogue holds for a data point nothing fills, and finds the manifest unchanged.

**Imposed by:** COR-053 point 8 lets the status report suggest an available capability where a data point is unfilled. The suggestion reads "only local catalogues and manifests already fetched, never the network", and it is never an action. So the adopter learns what could fill a data point from what is on the machine, and nothing is installed for them.
