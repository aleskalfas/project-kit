---
id: UC-063
title: Plan an intent into an EPIC and its work, filed once I approve the plan
status: active
actor: ACT-planner
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements:
  - REQ-040
  - REQ-041
  - REQ-042
after:
  - [UC-064]
shortfalls:
  - at: 8
    issue: "#1761"
    record: project-management:DEC-014
  - at: 9
    issue: "#1761"
    record: project-management:DEC-029
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/agents/project-manager/project-manager.md
        - .pkit/capabilities/project-management/agents/project-manager/storyboard.md
        - .pkit/capabilities/project-management/skills/pm/batch-plan.md
        - .pkit/capabilities/project-management/scripts/decline-use-case-task.py
        - .pkit/capabilities/project-management/scripts/_lib/use_case_task.py
        - .pkit/capabilities/project-management/scripts/_lib/use_case_citations.py
        - .pkit/capabilities/project-management/scripts/edit-issue.py
        - .pkit/capabilities/project-management/schemas/use-cases.schema.json
      record:
        - project-management:DEC-014
        - project-management:DEC-004
        - project-management:DEC-005
        - project-management:DEC-006
        - project-management:DEC-008
        - project-management:DEC-012
        - project-management:DEC-029
        - project-management:DEC-054#1
        - project-management:DEC-054#3
        - project-management:DEC-054#4
        - project-management:DEC-054#5
        - COR-013
        - COR-017
        - COR-024
        - COR-052
        - COR-053
        - COR-039
        - ADR-034#1
      artefact:
        - ACT-planner
        - REQ-040
        - REQ-041
        - REQ-042
---

# UC-063 — Plan an intent into an EPIC and its work, filed once I approve the plan

**Goal:** Plan an intent against my project's use cases into an EPIC and its work, which are filed once I approve the plan.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `project-manager` agent, which drafts the [batch plan](../../glossary.md#term-batch-plan--batch-plan), has it reviewed and files it. It files nothing before the planner approves the plan ([DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).
- **Operator** (`core:ACT-operator`): is asked before a filing changes a repository other than the session's own, so no such write happens silently ([core:REQ-012](../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-064](UC-064-define-milestones-and-workstreams.md):** The [project](../../../core/glossary.md#term-project--project) declares the [workstreams](../../glossary.md#term-workstream--workstream) its work falls into ([DEC-012](../../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has project-management installed, and the adapter deploys the `project-manager` agent and the `pm` [skill](../../../core/glossary.md#term-skill--skill) ([COR-013](../../../../../.pkit/decisions/core/COR-013-agent-architecture.md) and [COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- Where a [component](../../../core/glossary.md#term-component--component) fills the use-case [data point](../../../core/glossary.md#term-data-point--data-point), the backbone resolves it, with the [use-case entries](../../glossary.md#term-use-case-entry--use-case-entry) settled on the [default branch](../../../core/glossary.md#term-default-branch--default-branch) ([COR-052](../../../../../.pkit/decisions/core/COR-052-slots.md) and [COR-053](../../../../../.pkit/decisions/core/COR-053-connection-points.md)). Which component fills it, and how, is that component's.
- The harness lets the agent hand the plan to the critic and the architect for review ([COR-024](../../../../../.pkit/decisions/core/COR-024-critic-and-architect-agents.md)).

**Trigger:** The planner gives the agent an intent, with the reference material that frames it.

**Main path:**

1. The planner gives the `project-manager` agent an intent, such as "let a [project](../../../core/glossary.md#term-project--project) rename a [workstream](../../glossary.md#term-workstream--workstream)", with its reference material.
2. The agent reads the intent and each reference. Where the intent is unclear, it asks at most two questions, in one message (`batch-plan.md`).
3. The agent reads the [use-case entries](../../glossary.md#term-use-case-entry--use-case-entry) with `pkit connections resolve pkit::work-tracking:use-cases --json` ([DEC-054 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#3-the-states-the-rule-distinguishes)). It walks the active entries against the intent, reading each one's document where its path is given ([DEC-054 point 5](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#5-the-planning-step)).
4. The agent slices the intent into an [EPIC](../../glossary.md#term-epic--epic), Features, Umbrellas and Tasks. It gives each its parent, its value on each [classification axis](../../glossary.md#term-classification-axis--classification-axis), and the use-case entries it serves ([DEC-004](../../../../../.pkit/capabilities/project-management/decisions/DEC-004-six-level-hierarchy.md), [DEC-012](../../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md) and DEC-054 point 5).
5. Where the plan holds three issues or more, the agent has the critic review it. Where its work crosses three [components](../../../core/glossary.md#term-component--component) or more, or brings in a new abstraction, the architect reviews it too ([DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).
6. The agent shows the [batch plan](../../glossary.md#term-batch-plan--batch-plan): its rows, the order of the work, the [reviewers](../../../core/glossary.md#term-reviewer--reviewer)' [findings](../../../core/glossary.md#term-finding--finding) and the use-case entries each [issue](../../glossary.md#term-issue--issue) serves. It names the active entries the intent touches that no issue names, and the work that no entry describes (DEC-054 point 5).
7. The planner approves the plan (DEC-029).
8. The agent files the issues, parents before children, each with `pkit pm create-issue`. It then writes each body with `pkit pm edit-issue`, which checks the body (DEC-029).

> [!WARNING]
> **Not built yet:** filing an issue and writing its body are two calls. A body refused after its issue is filed leaves the template's body there. [DEC-014](../../../../../.pkit/capabilities/project-management/decisions/DEC-014-validation-severity-model.md) decides that no issue is left half filed, and #1761 tracks it.

9. The agent attaches each issue the plan schedules to its [Milestone](../../glossary.md#term-milestone--milestone) with `pkit pm promote-issue <n> --milestone <M>`, the planner's approval being its reason ([DEC-006](../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md) and DEC-029).

> [!WARNING]
> **Not built yet:** the `batch-plan` procedure attaches the Milestone with a raw `gh issue edit`. That leaves no [audit comment](../../glossary.md#term-audit-comment--audit-comment) and no journal entry, and checks no repository. DEC-029 decides that the agent files through the [capability](../../../core/glossary.md#term-capability--capability)'s own commands, and #1761 tracks it.

10. The agent reports each issue it filed, with its number and its link.

**Variants:**

- **3a.** Nothing fills the [data point](../../../core/glossary.md#term-data-point--data-point). The agent skips the step, and the plan names no [use-case entry](../../glossary.md#term-use-case-entry--use-case-entry) ([DEC-054 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#3-the-states-the-rule-distinguishes)).
- **3b.** The data point cannot be read, such as in a clone that never fetched the [default branch](../../../core/glossary.md#term-default-branch--default-branch). The agent says why, and plans without the step. It never takes that outcome for an empty set ([DEC-054 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#3-the-states-the-rule-distinguishes)).
- **3c.** Only part of the data point resolved. The agent walks what the data point holds, and names the filler that gave nothing. The gaps it finds are shown as possible ones ([DEC-054 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#3-the-states-the-rule-distinguishes)).
- **4a.** The data point holds no entry, and the plan builds work that touches what users do. The plan opens with a [Task](../../glossary.md#term-task--task) to describe what users do with the software, and only that work depends on it ([DEC-054 point 5](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#5-the-planning-step)).
- **4b.** The planner declined that Task earlier the same day, in this checkout. The agent leaves it out, and says when it was declined ([DEC-054 point 5](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#5-the-planning-step)).
- **7a.** The planner asks for changes. The agent drafts the plan again, and runs the [reviewers](../../../core/glossary.md#term-reviewer--reviewer) again where the revision is not trivial. The path rejoins at step 6.
- **7b.** The planner revises the Task of variant 4a away. Once the plan is approved, the agent keeps the decline with `pkit pm decline-use-case-task`, until the next day ([DEC-054 point 5](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#5-the-planning-step)). The path goes on at step 8.
- **7c.** The planner cancels the plan. The agent files nothing, and the use case ends ([DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).
- **8a.** A filing is refused. The agent stops, says which [issue](../../glossary.md#term-issue--issue) failed and why, and proposes a fix to the planner. What it filed before stays filed (`batch-plan.md`).
- **8b.** A body cites a use-case entry the data point does not hold. The system warns, and the agent mends the body and writes it again ([DEC-054 point 4](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#4-the-rule)).

**Postconditions:** Each [issue](../../glossary.md#term-issue--issue) of the approved plan is filed under its parent, with its value on each [classification axis](../../glossary.md#term-classification-axis--classification-axis) and the [use-case entries](../../glossary.md#term-use-case-entry--use-case-entry) it serves. The planner saw every issue of the plan before any was filed.

**Minimal guarantees:**

- No [issue](../../glossary.md#term-issue--issue) is filed before the planner approves the whole plan ([DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).
- A plan never cites an id the [data point](../../../core/glossary.md#term-data-point--data-point) does not hold, and never suggests one ([DEC-054 point 5](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#5-the-planning-step)).
- A data point that cannot be read is never taken for an empty set ([DEC-054 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#3-the-states-the-rule-distinguishes)).
