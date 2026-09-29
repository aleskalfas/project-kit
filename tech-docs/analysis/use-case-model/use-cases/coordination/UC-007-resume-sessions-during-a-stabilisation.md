---
id: UC-007
title: Resume sessions killed during a stabilisation
status: active
actor: ACT-clone-session
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/milestone.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
      record:
        - project-management:DEC-016
        - project-management:DEC-014
        - project-management:DEC-035
        - ADR-019
      artefact:
        - ACT-clone-session
---

# UC-007 — Resume sessions killed during a stabilisation

**Goal:** Sessions restarted while a Milestone is stabilising resume their work and respect the stabilisation, though none of them remembers it.

**Starts when:** Every session is killed while a release Milestone is stabilising, and the operator restarts them.

**Main path:**

1. Each new session reads its clone's position (UC-001). The position shows that a stabilisation is on — the Milestone, since when, by whom and why — read from the Milestone's description.
2. The session's work in flight continues; what is free to pick holds only release scope.
3. A session that finishes in-scope work lands it on the default branch as usual.
4. A session that finishes out-of-scope work keeps it on its branch, or in an open pull request: landing it on the default branch is refused while the stabilisation is on.
5. When the stabilisation lifts, the held work lands.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **2a.** A session tries to start a new front. The start is refused; the operator may bypass it with a reason, stamped on the issue (project-management DEC-014).
- **4a.** A clone runs older tooling that knows nothing of stabilisation, or someone merges by hand. A required CI status runs the same check and holds the pull request (ADR-019).
- **4b.** The operator decides the out-of-scope work must land anyway. The landing is bypassed with an audited reason.

**Done when:** Every clone is working again, and while the stabilisation was on the default branch received only release scope.

**Design:** Situation S7 of the coordination design walk. Built today: the clone-local instance id (DEC-035) and reading Milestones (`_lib/milestone.py`, DEC-016). Intended, not built yet — EPIC #943: the `Stabilizing:` line and its one writer, the guards on `start-work`, `done-work` and `merge-pr`, and the shared check a required CI status runs.
