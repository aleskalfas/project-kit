---
id: UC-008
title: Land integration-branch work during a stabilisation
status: active
actor: ACT-clone-session
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/schemas/git-conventions.yaml
        - .pkit/capabilities/project-management/scripts/open-pr.py
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/done-work.py
        - .pkit/capabilities/project-management/scripts/merge-pr.py
      record:
        - project-management:DEC-013
        - project-management:DEC-016
        - ADR-019
      artefact:
        - ACT-clone-session
    revalidated:
      at: 2026-10-01T01:25:11Z
      outcome: unchanged
      unchanged-because: "on this branch the anchored code changed only in layout: ruff format and the lint fixes; behaviour and the documented commands are unchanged"
---

# UC-008 — Land integration-branch work during a stabilisation

**Goal:** Work on an integration branch goes on during a stabilisation, and reaches the default branch only as release scope.

**Starts when:** A release Milestone is stabilising while a clone session works on a Task under an integration marker (`Integration: integration/<slug>`).

**Main path:**

1. The session starts a Task under the marked issue, and the start is allowed: continuing an arc that has already landed work on its integration branch opens no new front (gap I).
2. The session opens the Task's pull request against the integration branch, as the marker dictates (project-management DEC-013).
3. The pull request lands on the integration branch. The stabilisation does not apply: the default branch is untouched.
4. When every marked descendant is closed, the session opens the final pull request, from the integration branch to the default branch.
5. The owning issue is release scope, so the promotion lands like any other in-scope work.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** The arc has landed nothing yet, on its integration branch or on the default branch. Whether the stabilisation refuses starting it, as a new front, is open (gap I).
- **5a.** The owning issue is outside release scope. The promotion is refused and waits until the stabilisation lifts; work on the integration branch goes on meanwhile.

**Done when:** The arc's Tasks kept landing on the integration branch throughout, and the arc reached the default branch only as release scope or after the stabilisation lifted.

**Design:** Situation S8 of the coordination design walk. Built today: integration branches, their marker and the pull-request target it dictates (DEC-013, `git-conventions.yaml`, `open-pr`). Intended, not built yet — EPIC #943 (F2): the stabilisation guards, which leave pull requests into an integration branch alone, in the lifecycle scripts anchored here. F2 adds the shared check's path as an anchor and revalidates this use case.

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **I, at step 1 and 1a.** Pull requests into an integration branch were exempt from the landing guard, but the start guard's new-front test read "landed" on the default branch only, so continuing an arc whose earlier Tasks had landed on its integration branch was refused. Proposed fix (pending authorisation; carried by F2 T2.2 of EPIC #943): "landed" is read on the branch the work lands on — the integration branch, for work under an integration marker — so starting an arc that has landed nothing is still a new front (1a refused). Alternative: leave integration-marked work out of the start guard altogether (1a allowed). Its only way to the default branch, the promotion, is guarded already (5a), and refusing its start sits ill with this use case's goal, that integration work goes on during a stabilisation.
