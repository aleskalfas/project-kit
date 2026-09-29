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
      record:
        - project-management:DEC-013
        - project-management:DEC-016
        - ADR-019
      artefact:
        - ACT-clone-session
---

# UC-008 — Land integration-branch work during a stabilisation

**Goal:** Work on an integration branch goes on during a stabilisation, and reaches the default branch only as release scope.

**Starts when:** A release Milestone is stabilising while a clone session works on a Task under an integration marker (`Integration: integration/<slug>`).

**Main path:**

1. The session starts a Task under the marked issue. The start is allowed when the arc has already landed work on its integration branch: landing is read on the branch the work lands on, so continuing an arc is no new front.
2. The session opens the Task's pull request against the integration branch, as the marker dictates (project-management DEC-013).
3. The pull request lands on the integration branch. The stabilisation does not apply: the default branch is untouched.
4. When every marked descendant is closed, the session opens the final pull request, from the integration branch to the default branch.
5. The owning issue is release scope, so the promotion lands like any other in-scope work.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** The arc has landed nothing yet, on its integration branch or on the default branch. Starting it is a new front, refused unless bypassed with a reason.
- **5a.** The owning issue is outside release scope. The promotion is refused and waits until the stabilisation lifts; work on the integration branch goes on meanwhile.

**Done when:** The arc's Tasks kept landing on the integration branch throughout, and the arc reached the default branch only as release scope or after the stabilisation lifted.

**Design:** Situation S8 of the coordination design walk. Built today: integration branches, their marker and the pull-request target it dictates (DEC-013, `git-conventions.yaml`, `open-pr`). Intended, not built yet — EPIC #943: the stabilisation guards, which leave pull requests into an integration branch alone.
