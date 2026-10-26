---
id: UC-089
title: Land my Task while other agents land theirs
status: active
actor: ACT-worker-agent
other-actors:
  - core:ACT-merge-authoriser
  - core:ACT-ci-pipeline
requirements:
  - REQ-040
  - REQ-041
  - REQ-042
after:
  - [UC-084]
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/land-work.py
        - .pkit/capabilities/project-management/scripts/fix-drift.py
        - .pkit/capabilities/project-management/skills/pm/batch-plan.md
      record:
        - project-management:DEC-013
        - project-management:DEC-026
        - project-management:DEC-028
        - project-management:DEC-055#3
        - project-management:DEC-056#3
        - project-management:DEC-056#4
        - project-management:DEC-056#6
        - ADR-061
        - COR-017
        - COR-021
      artefact:
        - ACT-worker-agent
        - REQ-040
        - REQ-041
        - REQ-042
---

# UC-089 — Land my Task while other agents land theirs

**Goal:** Land my finished Task on the default branch while other agents land theirs, each merge judged at its own head.

**Other actors:**

- **Merge authoriser** (`core:ACT-merge-authoriser`): authorises the merge of one [head](../../../../core/glossary.md#term-head--head) at a time, and no [verdict](../../../glossary.md#term-verdict--verdict) stands in for that [authorisation](../../../glossary.md#term-authorisation--authorisation) ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).
- **CI pipeline** (`core:ACT-ci-pipeline`): runs the checks at each new head of the worker's [pull request](../../../../core/glossary.md#term-pull-request--pull-request).

**Preconditions:** **From [UC-084](UC-084-take-next-task.md):** The [Task](../../../glossary.md#term-task--task) is in Review, and the Task's [pull request](../../../../core/glossary.md#term-pull-request--pull-request) is open ([DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and the commands of `pkit pm` ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).
- The backbone merges a [pull request](../../../../core/glossary.md#term-pull-request--pull-request) pinned to a [head](../../../../core/glossary.md#term-head--head), through a merge queue where the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) has one ([ADR-061](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md)).

**Trigger:** The worker's [pull request](../../../../core/glossary.md#term-pull-request--pull-request) is ready, while other agents' pull requests wait to merge into the same [default branch](../../../../core/glossary.md#term-default-branch--default-branch).

**Main path:**

1. The worker runs `pkit pm land-work <N>`. The system checks, reviews and stops ready at the [head](../../../../core/glossary.md#term-head--head) the system judged, as `UC-062` steps 2 to 10 describe.
2. The merge authoriser authorises the merge of that head, as `UC-062` step 11 describes ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).
3. Another agent's [pull request](../../../../core/glossary.md#term-pull-request--pull-request) merges first, so the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) moves past the worker's [base](../../../../core/glossary.md#term-base--base).
4. The worker merges the default branch into the [Task](../../../glossary.md#term-task--task)'s branch, with no conflict, and pushes the new head.
5. The worker runs `pkit pm land-work <N> --yes --expect-head <sha>`, naming the head the merge authoriser authorised. The [authorisation](../../../glossary.md#term-authorisation--authorisation) covers the new head, since a clean merge of the base counts as no edit (DEC-055 point 3).
6. Each [reviewer](../../../../core/glossary.md#term-reviewer--reviewer) whose [verdict](../../../glossary.md#term-verdict--verdict) no longer stands on the new base reviews again ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)). The system then merges at the head the [merge gate](../../../glossary.md#term-merge-gate--merge-gate) judged, as `UC-062` steps 6 to 14 describe.
7. After the merge, the worker runs `pkit pm fix-drift` ([DEC-056 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-056-drift-fixers.md#3-a-command-starts-the-granted-fixers)). The fixers the [project](../../../../core/glossary.md#term-project--project) granted propose answers for what the merge left out of date.

**Variants:**

- **3a.** No other [pull request](../../../../core/glossary.md#term-pull-request--pull-request) merged since the worker's [base](../../../../core/glossary.md#term-base--base). The system merges at the authorised [head](../../../../core/glossary.md#term-head--head), as `UC-062` steps 12 to 14 describe, and the path goes on at step 7.
- **4a.** The merge of the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) conflicts. The worker resolves the conflict on the [Task](../../../glossary.md#term-task--task)'s branch. The new head holds an edit the merge authoriser has not seen, so the new head needs a new [authorisation](../../../glossary.md#term-authorisation--authorisation) ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)). The path rejoins at step 1.
- **5a.** The default branch merges through a merge queue. The backbone queues the pull request pinned to the pull request's head. The queue merges the agents' pull requests one at a time ([DEC-013](../../../../../../.pkit/capabilities/project-management/decisions/DEC-013-branch-and-pr-conventions.md) and [ADR-061](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md)).
- **7a.** Another run of `fix-drift` in the same clone holds the clone's lock. The command refuses, and the worker runs `fix-drift` again later ([DEC-056 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-056-drift-fixers.md#4-the-run-is-bounded)).

**Postconditions:** The worker's [pull request](../../../../core/glossary.md#term-pull-request--pull-request) merged at the [head](../../../../core/glossary.md#term-head--head) the gate judged, after the other agents' changes, and the pull request's [Task](../../../glossary.md#term-task--task) is in Done.

**Minimal guarantees:**

- Nothing merges at a [head](../../../../core/glossary.md#term-head--head) nobody authorised ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)). The one exception is a later head whose every edit lies in [answer](../../../../core/glossary.md#term-answer--answer) files or a clean merge of the [base](../../../../core/glossary.md#term-base--base).
- A [verdict](../../../glossary.md#term-verdict--verdict) given on an older base no longer stands at the merge ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).
- No two runs of the fixers start at once in one clone, since the clone's lock holds back a second run (`fix-drift.py`).

## Open for the design

What the worker needs here that no accepted record decides yet:

- **One batch of ready heads** across the agents, which the merge authoriser authorises in one sitting. The maintainer decided on 17 October that decisions reach the person in one batch (#1675), and no record holds that decision yet.
- **The fixers across clones.** Each clone keeps its own queue and its own lock ([DEC-056 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-056-drift-fixers.md#6-the-proposals-wait-for-a-decision)). So agents that land in separate clones may each start fixers on the same out-of-date artefact, and no record decides which agent runs the fixers.
- **The review rounds that parallel landings cost.** Each landing sends every other open [pull request](../../../../core/glossary.md#term-pull-request--pull-request) on the same files through another review round (`batch-plan.md`). No record decides how a [topology](../../../glossary.md#term-topology--topology) keeps that cost down.
