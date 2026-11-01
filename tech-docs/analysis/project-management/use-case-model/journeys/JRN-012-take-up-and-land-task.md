---
id: JRN-012
title: Take up my Task, and land its change
status: active
actor: core:ACT-developer
steps:
  - UC-061
  - UC-062
relies-on:
  - UC-060
  - UC-063
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/review-work.py
        - .pkit/capabilities/project-management/scripts/land-work.py
      record:
        - project-management:DEC-006
        - project-management:DEC-013
        - project-management:DEC-026
        - project-management:DEC-028
        - project-management:DEC-050
      artefact:
        - UC-061
        - UC-062
        - UC-060
        - UC-063
---

# JRN-012 — Take up my Task, and land its change

**Goal:** Take up a Task that is filed, and land its change, so the Task ends in Done.

**Steps:**

1. [UC-061](../use-cases/020-file-and-move/UC-061-move-issue.md) — Move my issue through its lifecycle, each move checked
   - **Needs from [UC-060](../use-cases/020-file-and-move/UC-060-file-task.md) (outside this journey):** the [Task](../../glossary.md#term-task--task), filed under its parent with a value on each [classification axis](../../glossary.md#term-classification-axis--classification-axis), where the developer filed it. A body that still holds a placeholder of its template is refused at the first move, until it is written (UC-061 variant 3b).
   - **Needs from [UC-063](../use-cases/010-plan/UC-063-plan-intent.md) (outside this journey):** the Task, where the planner's approved plan filed it. A Task either use case filed is enough.
2. [UC-062](../use-cases/030-review-and-land/UC-062-review-and-land.md) — Have the reviewers my change requires review my pull request, and land it
   - **Needs from step 1 (UC-061):** the Task in Review, and its [pull request](../../../core/glossary.md#term-pull-request--pull-request) open, which `pkit pm review-work` opened from the Task's branch ([project-management DEC-026](../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)). The merge moves to Done only each [issue](../../glossary.md#term-issue--issue) the pull request closes, as UC-062 step 14 describes. So the pull request names the Task with a closing keyword, such as `Closes #N` ([project-management DEC-013](../../../../../.pkit/capabilities/project-management/decisions/DEC-013-branch-and-pr-conventions.md)).

**Variants:**

- **1a.** The developer decides that the [Task](../../glossary.md#term-task--task) will not be done, and closes it while it is in Todo or Backlog. The Task is in Done, and the path ends ([UC-061](../use-cases/020-file-and-move/UC-061-move-issue.md) variant 1d).
- **1b.** The Task's work ends with no [pull request](../../../core/glossary.md#term-pull-request--pull-request), such as an audit. The developer closes it as completed, naming where the result lives, and the path ends (UC-061 variant 1h).
- **2a.** A [required reviewer](../../glossary.md#term-required-reviewer--required-reviewer)'s [verdict](../../glossary.md#term-verdict--verdict) requests changes. The developer changes the work, and the path rejoins at step 2 ([UC-062](../use-cases/030-review-and-land/UC-062-review-and-land.md) variant 7a).

**Postconditions:** The [Task](../../glossary.md#term-task--task)'s [change](../../../core/glossary.md#term-change--change) is merged at the [head](../../../core/glossary.md#term-head--head) the [merge gate](../../glossary.md#term-merge-gate--merge-gate) judged, with a standing approval from each [required reviewer](../../glossary.md#term-required-reviewer--required-reviewer), and the Task is in Done.

**Minimal guarantees:**

- A move the [issue lifecycle](../../glossary.md#term-issue-lifecycle--issue-lifecycle) does not declare is never made, so a [Task](../../glossary.md#term-task--task) stopped on the way stays in a state of its lifecycle ([project-management DEC-006](../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)).
- Nothing merges without a standing approval from each [required reviewer](../../glossary.md#term-required-reviewer--required-reviewer), save a [bypass](../../glossary.md#term-bypass--bypass) whose reason is posted before the merge ([project-management DEC-028](../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md) and [DEC-050](../../../../../.pkit/capabilities/project-management/decisions/DEC-050-per-reviewer-override.md)).
