---
change: '#1826'
trigger: planned
reviewed-against:
  - title: "#1826's body"
    url: https://github.com/aleskalfas/project-kit/issues/1826
    version: '2026-10-20T01:06:24Z'
  - title: the design note on analysis concepts and order
    version: 81340bca60f7391b4e791673eafe70964a01238a
date: '2026-10-20'
by: 'builder agent for #1826'
confirmed-by: Aleš Kalfas
outcomes:
  ACT-developer: analysis-stale
  UC-002: gap-found
  UC-003: gap-found
  UC-004: gap-found
  UC-005: gap-found
  UC-006: gap-found
  UC-007: gap-found
  UC-008: gap-found
  UC-009: gap-found
  UC-010: gap-found
  UC-011: gap-found
  UC-012: gap-found
  UC-013: gap-found
---

# 2026-10-20 — The core's analysis in its five areas, each use case naming its producers

## Outcomes

- **ACT-developer — analysis-stale.** Its need to build a change under the project's conventions is met by software-engineering alone, so it moved to the head of that analysis's glossary, and the two records behind it went with it (DEC-001 point 2).
- **UC-002 — gap-found.** Its precondition, artefacts in a declared place that carry anchors, is variant 2a's, since the check handles its absence. What it does need, a project that runs the system, has no producer in force.
- **UC-003 — gap-found.** Its precondition, that the project declares changesets, has no producer in force.
- **UC-004 — gap-found.** Its Preconditions read None., while it needs a project that runs the system, which no use case in force produces.
- **UC-005 — gap-found.** Its Preconditions read None., while it needs a project that runs the system, which no use case in force produces. A declared place is variant 1a's, since the use case handles its absence.
- **UC-006 — gap-found.** Its precondition, a project that runs the system, has no producer in force. The project's continuous integration is the environment's, so it moved to the assumption of ADR-019 point 2.
- **UC-007 — gap-found.** Its Preconditions read None., while it needs debt that a landed change left, which no use case in force produces. The whole-repository check's job is the environment's, an assumption (ADR-055 point 5).
- **UC-008 — gap-found.** Its precondition named the changesets that UC-003 declares, whose absence variant 2a handles. It starts from the version the last release wrote, which it now names.
- **UC-009 — gap-found.** Two of its preconditions, the repository's changesets and their landing on the default branch, have no producer in force. Its package metadata comes from its own last release, and first from packaging the component, which is not written.
- **UC-010 — gap-found.** Its Preconditions read None., while it needs the methodology's source repository, which no use case in force produces.
- **UC-011 — gap-found.** Its Preconditions read None., while it needs the author's component, which no use case in force produces.
- **UC-012 — gap-found.** Its Preconditions read None., while it needs the system's tool on the adopter's machine, which no use case in force produces. An installed project is variant 1e's.
- **UC-013 — gap-found.** Its Preconditions read None., while it relies on the reports UC-012 files.

## Gaps

- **UC-002, UC-003, UC-004, UC-005, UC-006, UC-009, UC-010:** Develop the methodology in its source repository, in which the source repository runs the system as written, is not written. **Resolution:** #1719 writes it in 010-develop, and each of these preconditions then names it.
- **UC-002, UC-004, UC-005, UC-006:** Install the system into my project with one command, the other way a project comes to run the system, is not written. **Resolution:** #1717 writes it in 050-adopt.
- **UC-007, UC-009:** Land my change on the default branch is not written in the core's analysis, through pkit pull-request land or a direct commit. #1685 writes the path through project-management's land-work, which belongs to that capability's analysis. **Resolution:** no task carries the core's yet, so EPIC #1643 holds it until one is filed.
- **UC-009, UC-011:** Package a recurring discipline as a capability, and Adapt the system to another harness, are not written. **Resolution:** #1719 writes both in 010-develop.
- **UC-012:** Put the system's tool on my machine at a release is a need no actor states, and no use case writes it. **Resolution:** EPIC #1643 holds it until a task is filed.
- **UC-008:** its Preconditions did not say that it starts from the version the last release wrote. **Resolution:** it now opens From UC-008, or Environment, in this change.
- **UC-013:** its Preconditions read None. while it relies on the reports UC-012 files. **Resolution:** it now opens From UC-012, in this change.
