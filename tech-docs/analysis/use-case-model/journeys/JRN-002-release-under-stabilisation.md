---
id: JRN-002
title: Release with unfinished work under a stabilisation
status: active
actor: ACT-operator
steps:
  - UC-010
  - UC-005
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/milestone.py
      artefact:
        - UC-010
        - UC-005
    revalidated:
      at: 2026-10-01T01:25:13Z
      outcome: unchanged
      unchanged-because: "on this branch the anchored code changed only in layout: ruff format and the lint fixes; behaviour and the documented commands are unchanged"
---

# JRN-002 — Release with unfinished work under a stabilisation

**Starts:** A release is near while several clones have work in flight, some of it more than the release needs. The operator wants the release out without the unfinished rest.

**Steps:**

1. UC-010 — the operator stabilises the release Milestone, and the clones finish release scope under the freeze.
2. UC-005 — the operator reads the Milestone's readiness, defers what the release will not wait for, and the release goes out.

**Seams to watch:** where the path passes from one use case to the next — what must carry over, and how it could break.

- **UC-010 → UC-005:** the release scope the stabilisation guards hold (UC-010, step 3) must be the scope the readiness shows and the release gate checks (UC-005, steps 1 and 5). A deferral only the gate honoured would leave the deferred parent's remaining Tasks free to land on the default branch during the freeze (gap G); a pull request whose status went green before the stabilisation or a deferral could still cross it (gap K2); and the release pull request, which closes no issue, must not be held back by the freeze it ends (gap K3).

**Done when:** The release is out, carrying the finished release scope and the landed part of each deferred parent, and the stabilisation is lifted.
