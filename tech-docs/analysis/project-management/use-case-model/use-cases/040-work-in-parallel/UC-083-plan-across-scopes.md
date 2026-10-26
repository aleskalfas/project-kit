---
id: UC-083
title: Plan an intent into Tasks that one agent can each finish
status: active
actor: ACT-planning-agent
other-actors:
  - ACT-planner
  - ACT-worker-agent
  - ACT-lead-agent
requirements:
  - REQ-040
  - REQ-041
after:
  - [UC-082]
  - [UC-092]
  - [UC-064]
shortfalls:
  - at: 2
    issue: "#2143"
    record: project-management:DEC-059#1
  - at: 3
    issue: "#2143"
    record: project-management:DEC-059#7
  - at: 10
    issue: "#2136"
    record: project-management:DEC-059#7
  - at: "1a"
    issue: "#519"
    record: project-management:DEC-035#3
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/skills/pm/batch-plan.md
        - .pkit/capabilities/project-management/scripts/create-issue.py
      record:
        - project-management:DEC-029
        - project-management:DEC-054#5
        - project-management:DEC-005
        - project-management:DEC-012
        - project-management:DEC-018
        - project-management:DEC-035#3
        - project-management:DEC-045#4
        - project-management:DEC-059#1
        - project-management:DEC-059#2
        - project-management:DEC-059#4
        - project-management:DEC-059#6
        - project-management:DEC-059#7
        - COR-013
        - COR-017
      artefact:
        - ACT-planning-agent
        - ACT-planner
        - ACT-worker-agent
        - ACT-lead-agent
        - REQ-040
        - REQ-041
---

# UC-083 — Plan an intent into Tasks that one agent can each finish

**Goal:** Plan my planner's intent into Tasks that one agent can each finish, ordered where one Task needs another Task's work.

**Other actors:**

- **Planner** (`ACT-planner`): approves the whole plan before any [issue](../../../glossary.md#term-issue--issue) of the plan is filed ([DEC-029](../../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).
- **Worker agent** (`ACT-worker-agent`) and **Lead agent** (`ACT-lead-agent`): take the Tasks from the ready Tasks that every [seat](../../../glossary.md#term-seat--seat) shares. Each [Task](../../../glossary.md#term-task--task) names the Tasks that the Task waits on, so these agents never start a Task too early (`batch-plan.md`).

**Preconditions:**

- **From [UC-082](UC-082-set-up-topology.md):** The [topology](../../../glossary.md#term-topology--topology) on the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) declares the [seats](../../../glossary.md#term-seat--seat), and the [scope](../../../glossary.md#term-scope--scope) of each seat that has a scope (DEC-059 points [1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch) and [2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#2-a-seat-has-a-name-a-role-an-agent-and-an-optional-scope)).
- **From [UC-092](UC-092-take-seat.md):** The planning agent's clone holds the planning agent's seat ([DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat)).
- **From [UC-064](../010-plan/UC-064-define-milestones-and-workstreams.md):** The [project](../../../../core/glossary.md#term-project--project) declares the [workstreams](../../../glossary.md#term-workstream--workstream) its work falls into ([DEC-018](../../../../../../.pkit/capabilities/project-management/decisions/DEC-018-workstream-taxonomy-and-lifecycle.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the adapter deploys the `project-manager` agent and the `pm` [skill](../../../../core/glossary.md#term-skill--skill) ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md) and [COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).

**Trigger:** The planner gives the planning agent an intent to plan for the [topology](../../../glossary.md#term-topology--topology)'s agents.

**Main path:**

1. The planner gives the planning agent an intent, with the intent's reference material, as `UC-063` step 1 describes.
2. The agent reads the intent, the intent's references and the [project](../../../../core/glossary.md#term-project--project)'s use cases, as `UC-063` steps 2 and 3 describe ([DEC-054 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#5-the-planning-step)). The agent reads too the [topology](../../../glossary.md#term-topology--topology) from the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), with each [seat](../../../glossary.md#term-seat--seat) and the seat's [scope](../../../glossary.md#term-scope--scope) ([DEC-059 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch)).

> [!WARNING]
> **Not built yet:** `batch-plan.md` reads no topology. DEC-059 point 1 decides that every clone reads the topology from the default branch, and #2143 tracks it.

3. The agent slices the intent into an [EPIC](../../../glossary.md#term-epic--epic), Features and Tasks. The agent slices vertically, so that one agent can finish a [Task](../../../glossary.md#term-task--task) or a [Feature](../../../glossary.md#term-feature--feature) across the software's layers ([DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool)). The agent gives each Task the [workstream](../../../glossary.md#term-workstream--workstream) and the kind of the work the Task does ([DEC-012](../../../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)). A Task falls in each scope whose parts the Task matches.

> [!WARNING]
> **Not built yet:** `batch-plan.md` says nothing of how a plan is sliced across the software's layers. DEC-059 point 7 decides vertical slices, and #2143 tracks it.

10. The system warns of each Task of the plan that no seat may take, and refuses nothing (DEC-059 point 7 and [DEC-045 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#4-the-partition-is-soft--full-coverage-is-the-default-sharing-and-gaps-are-allowed-but-discouraged)).

> [!WARNING]
> **Not built yet:** nothing reads the seats' scopes, so nothing warns. DEC-059 point 7 decides the warning, and #2136 tracks it.

4. Where two Tasks edit the same files, the later Task's `## Dependencies` section names the earlier Task. The later Task is built once the earlier Task has merged ([DEC-005](../../../../../../.pkit/capabilities/project-management/decisions/DEC-005-linking-and-containment.md) and `batch-plan.md`).
5. Where a Task needs what a Task of another scope builds, the first Task's `## Dependencies` section names that other Task too (DEC-005 and `batch-plan.md`).
6. The agent has the plan reviewed, and shows the plan to the planner, as `UC-063` steps 5 and 6 describe ([DEC-029](../../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).
7. The planner approves the plan (DEC-029).
8. The agent files the issues, as `UC-063` steps 8 and 9 describe. The agent files the issues with no [owner](../../../glossary.md#term-owner--owner), so the issues join the ready Tasks that every seat shares (DEC-059 point 7). The agent of each seat takes the seat's Tasks from there, as `UC-084` describes.
9. The agent reports each [issue](../../../glossary.md#term-issue--issue) the agent filed, with the issue's number, link and workstream.

**Variants:**

- **1a.** A lead agent plans the work of the lead agent's own [scope](../../../glossary.md#term-scope--scope), in place of a planning agent. The lead agent's [instance](../../../glossary.md#term-instance--instance) owns each [issue](../../../glossary.md#term-issue--issue) the lead agent files, the parents and the Tasks alike. The lead agent builds that work itself ([DEC-035 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#3-a-clone-claims-at-creation-for-the-whole-tree) and [DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool)).

> [!WARNING]
> **Not built yet:** `create-issue` writes no [owner](../../../glossary.md#term-owner--owner). DEC-035 point 3 decides that the instance that files an issue owns the issue, and #519 tracks it.

- **7a.** The planner asks for changes, or cancels the plan, as `UC-063` variants 7a and 7c describe.
- **8a.** The planning agent's clone holds no [seat](../../../glossary.md#term-seat--seat). The clone marks no issue, and the agent files as step 8 does, with no owner ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

**Postconditions:** Each [Task](../../../glossary.md#term-task--task) of the approved plan is filed with no [owner](../../../glossary.md#term-owner--owner), with the [workstream](../../../glossary.md#term-workstream--workstream) and the kind of the Task's work. The `## Dependencies` section of each Task names each Task that the Task waits on.

**Minimal guarantees:**

- No [issue](../../../glossary.md#term-issue--issue) is filed before the planner approves the whole plan ([DEC-029](../../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).
- The `## Dependencies` section of a [Task](../../../glossary.md#term-task--task) that edits the same files as an earlier Task names the earlier Task (`batch-plan.md`).

## Open for the design

What the planning agent needs here that no accepted record decides yet:

- **How one scope gives another scope what the other scope needs,** such as an interface two scopes share. A contract between scopes is proposed only, in an unmerged note (draft PR #566). Typed `Blocked by:` lines, and the Tasks ready to start that those lines give, are [project-management DEC-025](../../../../../../.pkit/capabilities/project-management/decisions/DEC-025-parallelization-primitive.md)'s, which is proposed.
- **Work that passes through stages,** such as design, development and testing, where each stage needs the work of the stage before. No record decides how such work is planned.
