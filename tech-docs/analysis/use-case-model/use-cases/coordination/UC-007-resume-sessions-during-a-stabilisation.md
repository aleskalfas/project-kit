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
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/done-work.py
        - .pkit/capabilities/project-management/scripts/merge-pr.py
      record:
        - project-management:DEC-016
        - project-management:DEC-014
        - project-management:DEC-035
        - ADR-019
      artefact:
        - ACT-clone-session
    revalidated:
      at: 2026-10-01T15:15:15Z
      outcome: unchanged
      unchanged-because: "_lib/milestone.py gains the rollforward reads (the date trigger, the Rollforward target: line, the next-numbered Milestone) and a native-field key on each child; how a session reads its position and the stabilisation from the Milestone is untouched"
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

- **2a.** A session tries to start a new front outside release scope. The start is refused; the operator may bypass it with a reason, stamped on the issue (project-management DEC-014).
- **2b.** A session starts release-scope work that has nothing in flight and nothing landed yet — an untouched Feature under the release Milestone, or a Task filed directly under it. The start is allowed: it is a new front, but inside release scope (gap K1).
- **4a.** A clone runs older tooling that knows nothing of stabilisation, or someone merges by hand. A required CI status runs the same check and holds the pull request (ADR-019) — including one whose checks passed before the stabilisation began (gap K2).
- **4b.** The operator decides the out-of-scope work must land anyway. The landing is bypassed with an audited reason.

**Done when:** Every clone is working again, and while the stabilisation was on the default branch received only release scope.

**Design:** Situation S7 of the coordination design walk; it builds on UC-001's position. Built today: the clone-local instance id (DEC-035) and reading Milestones (`_lib/milestone.py`, DEC-016). Intended, not built yet — EPIC #943 (F2): the `Stabilizing:` line and its one writer, the guards on `start-work`, `done-work` and `merge-pr` — whose scripts are anchored here — and the shared check a required CI status runs. F2 adds `stabilize-milestone`'s and the check's paths as anchors and revalidates this use case.

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **K1, at step 2 and 2a.** The start guard as walked refused every new front, including release-scope work — an untouched Feature under the release Milestone, and every Task filed directly under it through the shortcut hierarchy (project-management DEC-004) — while step 2 offers exactly those as free to pick. Proposed fix (pending authorisation; carried by F2 T2.2 of EPIC #943): refuse a start only when it is a new front and outside release scope (2a, 2b).
- **K2, at 4a.** A required status is computed per head commit. Stabilising a Milestone, or deferring a parent, is a tracker event that pushes no commit, so a pull request that went green before it stays green, and a raw merge crosses the freeze. Proposed fix (pending authorisation; carried by F2 T2.3 and T2.5 of EPIC #943; the design must choose): re-run open pull requests' status on Milestone edits and deferral events, evaluate at merge time (a merge queue, #1011), or declare the residual gap as ADR-019 point 3 requires.
