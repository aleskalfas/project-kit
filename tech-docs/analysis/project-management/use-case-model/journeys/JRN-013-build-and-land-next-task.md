---
id: JRN-013
title: Build my next Task, and land it while other agents land theirs
status: active
actor: ACT-worker-agent
steps:
  - UC-084
  - UC-089
relies-on:
  - UC-092
  - UC-083
  - UC-060
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/review-work.py
        - .pkit/capabilities/project-management/scripts/land-work.py
      record:
        - project-management:DEC-026
        - project-management:DEC-055#3
        - project-management:DEC-055#6
        - project-management:DEC-059#7
      artefact:
        - ACT-worker-agent
        - UC-084
        - UC-089
        - UC-092
        - UC-083
        - UC-060
---

# JRN-013 — Build my next Task, and land it while other agents land theirs

**Goal:** Take my next ready Task, build it, and land it on the default branch while other agents land theirs.

**Steps:**

1. [UC-084](../use-cases/040-work-in-parallel/UC-084-take-next-task.md) — Take my next ready Task, and build it up to its merge
   - **Needs from [UC-092](../use-cases/040-work-in-parallel/UC-092-take-seat.md) (outside this journey):** the worker's clone holds a worker agent's [seat](../../glossary.md#term-seat--seat), and the worker acts as that seat's agent. The seat's [scope](../../glossary.md#term-scope--scope) narrows the Tasks the worker takes ([project-management DEC-059 point 7](../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool)).
   - **Needs from [UC-083](../use-cases/040-work-in-parallel/UC-083-plan-across-scopes.md) (outside this journey):** Tasks the planning agent filed, each with its [workstream](../../glossary.md#term-workstream--workstream). A [Task](../../glossary.md#term-task--task) whose `## Dependencies` section names an [issue](../../glossary.md#term-issue--issue) still open is not ready. The worker takes such a Task only once that issue closes (UC-084 step 2).
   - **Needs from [UC-060](../use-cases/020-file-and-move/UC-060-file-task.md) (outside this journey):** Tasks a developer filed, each with its workstream. Tasks either use case filed are enough.
2. [UC-089](../use-cases/040-work-in-parallel/UC-089-land-alongside-others.md) — Land my Task while other agents land theirs
   - **Needs from step 1 (UC-084):** the Task in Review, and its [pull request](../../../core/glossary.md#term-pull-request--pull-request) open, which `pkit pm review-work` opened on the Task's branch ([project-management DEC-026](../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)). Step 1 ends by landing the Task, as UC-089 describes. Other agents' pull requests may merge first, and move the [default branch](../../../core/glossary.md#term-default-branch--default-branch) past the worker's [base](../../../core/glossary.md#term-base--base). The worker then merges the default branch into the Task's branch before the merge (UC-089 step 4).

**Variants:**

- **1a.** The listing holds no ready [Task](../../glossary.md#term-task--task). The worker starts nothing, and the path ends ([UC-084](../use-cases/040-work-in-parallel/UC-084-take-next-task.md) variant 1a).
- **2a.** The Task is a piece of work that the Task of another [scope](../../glossary.md#term-scope--scope) depends on. The worker hands the next piece on as [UC-087](../use-cases/040-work-in-parallel/UC-087-hand-over-to-next-scope.md) describes, landing this Task through step 2, and the next piece's Task can start.
- **2b.** The merge of the [default branch](../../../core/glossary.md#term-default-branch--default-branch) into the Task's branch conflicts. The worker resolves the conflict, and the new [head](../../../core/glossary.md#term-head--head) needs a new [authorisation](../../glossary.md#term-authorisation--authorisation), so the path rejoins at step 2 ([UC-089](../use-cases/040-work-in-parallel/UC-089-land-alongside-others.md) variant 4a).

**Postconditions:** The [Task](../../glossary.md#term-task--task)'s [pull request](../../../core/glossary.md#term-pull-request--pull-request) merged at the [head](../../../core/glossary.md#term-head--head) the [merge gate](../../glossary.md#term-merge-gate--merge-gate) judged, after the other agents' changes, and the Task is in Done.

**Minimal guarantees:**

- Nothing merges at a [head](../../../core/glossary.md#term-head--head) the merge authoriser has not authorised, but for one exception. That is a head that only merges the [base](../../../core/glossary.md#term-base--base) without a conflict ([project-management DEC-055 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).
- A merge after which the [change check](../../../core/glossary.md#term-change-check--change-check) fails on a document merges nothing, and names each such document ([project-management DEC-055 point 6](../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#6-the-merge-as-it-would-land)).
