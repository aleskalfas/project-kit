---
id: JRN-002
title: Release with unfinished work under a stabilisation
status: active
actor: ACT-operator
steps:
  - UC-010
  - UC-004
  - UC-005
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/milestone.py
      artefact:
        - UC-010
        - UC-004
        - UC-005
---

# JRN-002 — Release with unfinished work under a stabilisation

**Starts:** A release is near while several clones have work in flight, some of it more than the release needs. The operator wants the release out without the unfinished rest.

**Steps:**

1. UC-010 — the operator stabilises the release Milestone.
2. UC-004 — the operator follows the release scope across every clone as it closes.
3. UC-005 — the operator defers what the release will not wait for, and the release goes out.

**Seams to watch:** where the path passes from one use case to the next — what must carry over, and how it could break.

- **UC-010 → UC-004:** the overview reads the stabilisation from the Milestone's description, where the one writer put it. A second writer, or another line format, would leave clones unaware of it.
- **UC-004 → UC-005:** the release scope the overview shows, the scope the guards hold and the scope the release gate checks must be one computation. A deferral only the gate honoured would leave the deferred parent's remaining Tasks free to land on the default branch during the freeze.

**Done when:** The release is out, carrying the finished release scope and the landed part of each deferred parent, and the stabilisation is lifted.
