---
id: UC-010
title: Stabilise a Milestone for a release
status: active
actor: ACT-operator
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/milestone.py
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/done-work.py
        - .pkit/capabilities/project-management/scripts/merge-pr.py
      record:
        - project-management:DEC-016
        - project-management:DEC-014
        - project-management:DEC-044
        - ADR-019
      artefact:
        - ACT-operator
---

# UC-010 — Stabilise a Milestone for a release

**Goal:** The operator freezes a release Milestone: work in flight continues, nothing new starts, and the default branch receives only release scope.

**Starts when:** A release is near, and the operator wants the clones to finish the release scope rather than start more.

**Main path:**

1. The operator stabilises the Milestone (`stabilize-milestone <N> --reason "<why>"`). A `Stabilizing:` line — time, operator, instance and reason — goes into the Milestone's description, written by the one writer that edits it, which re-reads the description before writing.
2. From then on, every clone's position shows the stabilisation (UC-001, UC-004).
3. Release scope is computed once, for every reader: the Milestone's children, and the open parents of work landed on the default branch since the last release, each with its subtree, less what the operator deferred.
4. Starting a new front is refused, and so is landing out-of-scope work on the default branch; either can be bypassed with a reason stamped on the issue (project-management DEC-014).
5. A required CI status runs the same check on every pull request into the default branch (ADR-019).

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** Two writes to the Milestone's description race. The later one wins; the lost one shows in every position, and running it again is enough.
- **4a.** A hotfix is needed. The operator files it as a Bug on the stabilising Milestone, which puts it in release scope.
- **5a.** The operator lifts the stabilisation (`stabilize-milestone <N> --lift`), or closes the Milestone after the release (UC-005). The line is removed and the guards stand down.

**Done when:** Every clone knows the Milestone is stabilising, and the default branch accepts only release scope until the stabilisation lifts.

**Design:** The first half of situation S5 of the coordination design walk; the release itself is UC-005. Built today: Milestones and their categories (`_lib/milestone.py`, DEC-016), the bypassable-with-audit severity (DEC-014) and the audit stamp (DEC-044). Intended, not built yet — EPIC #943: `stabilize-milestone` and the description's one writer, the release-scope computation shared by the guards and the release gate, the guards on `start-work`, `done-work` and `merge-pr`, and the required CI status.
