---
id: UC-088
title: Delegate a Task of my scope to a helper agent
status: active
actor: ACT-lead-agent
other-actors:
  - core:ACT-ai-agent
requirements:
  - REQ-061
  - REQ-062
after:
  - [UC-092]
  - [UC-083, UC-060]
shortfalls:
  - at: 1
    issue: "#519"
    record: project-management:DEC-035#3
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
      record:
        - project-management:DEC-029
        - project-management:DEC-035#3
        - project-management:DEC-026
        - project-management:DEC-012
        - project-management:DEC-059#4
        - project-management:DEC-059#6
        - project-management:DEC-059#7
        - COR-013
        - COR-017
      artefact:
        - ACT-lead-agent
        - REQ-061
        - REQ-062
---

# UC-088 — Delegate a Task of my scope to a helper agent

**Goal:** Delegate a Task of my scope to a helper agent, which acts as my instance while the helper agent builds the Task.

**Other actors:** **AI agent** (`core:ACT-ai-agent`): the helper agent the lead starts, which the [topology](../../../glossary.md#term-topology--topology) does not name. The helper agent builds the [Task](../../../glossary.md#term-task--task) and returns the whole result to the lead ([DEC-029](../../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).

**Preconditions:**

- **From [UC-092](UC-092-take-seat.md):** The lead's clone holds a lead agent's [seat](../../../glossary.md#term-seat--seat), whose [scope](../../../glossary.md#term-scope--scope) names what the lead takes work from (DEC-059 points [4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat) and [7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool)).
- **From [UC-083](UC-083-plan-across-scopes.md), or [UC-060](../020-file-and-move/UC-060-file-task.md):** The [Task](../../../glossary.md#term-task--task) is filed in the lead's scope ([DEC-012](../../../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the adapter deploys the helper agents the lead starts ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md) and [COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
- The harness lets a session start agents, down to a limit on how deep agents nest ([DEC-029](../../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).

**Trigger:** The lead decides to have a helper agent build a [Task](../../../glossary.md#term-task--task) of the lead's [scope](../../../glossary.md#term-scope--scope).

**Main path:**

1. The lead starts the [Task](../../../glossary.md#term-task--task): `pkit pm start-work <N>`, as `UC-084` steps 4 to 6 describe. The lead's [instance](../../../glossary.md#term-instance--instance) becomes the Task's [owner](../../../glossary.md#term-owner--owner) ([DEC-035 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#3-a-clone-claims-at-creation-for-the-whole-tree)).

> [!WARNING]
> **Not built yet:** `start-work` writes no owner. DEC-035 point 3 decides that an instance that starts an [issue](../../../glossary.md#term-issue--issue) with no owner becomes the issue's owner, and #519 tracks it.

2. The lead starts a helper agent for the Task through the harness, and passes the helper agent no name. The helper agent's whole result then comes back ([DEC-029](../../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)). The helper agent acts as the lead's instance while the helper agent builds the Task ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).
3. The helper agent builds the Task on the Task's branch, then commits and pushes the work.
4. The helper agent ends, and returns its result to the lead.
5. The lead reviews the result, and lands the Task, as `UC-089` describes.

**Variants:**

- **3a.** The lead's session dies while the helper agent works, and the helper agent's session ends with the lead's session. A new session of the lead takes up the [Task](../../../glossary.md#term-task--task), as `UC-086` describes, and finds on the Task's branch what the helper agent pushed.

**Postconditions:** The [Task](../../../glossary.md#term-task--task)'s work is on the Task's branch, and the lead's [instance](../../../glossary.md#term-instance--instance) still owns the Task.

**Minimal guarantees:**

- The lead's [instance](../../../glossary.md#term-instance--instance) stays the [Task](../../../glossary.md#term-task--task)'s [owner](../../../glossary.md#term-owner--owner), whichever session builds the Task ([DEC-035 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#3-a-clone-claims-at-creation-for-the-whole-tree)).
- The helper agent's result reaches the lead whole, since the lead passes the helper agent no name ([DEC-029](../../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).

## Open for the design

What the lead needs here that no accepted record decides yet:

- **The lead's identity in a linked worktree** of the clone, where the helper agent runs a command of project-management. The helper agent acts as the lead's [instance](../../../glossary.md#term-instance--instance), and [project-management DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology) leaves undecided how a linked worktree reads that identity. Today a linked worktree reads no number of its clone, and #1140 proposes that a linked worktree reads its clone's number.
- **Several delegations at once.** `start-work` checks each [Task](../../../glossary.md#term-task--task)'s branch out in the lead's own clone, so the lead delegates one Task at a time. A second delegation at once needs a linked worktree, which reads no number today (#1140).
- **Which helper agents a lead may start.** A scratchpad note on which agent may start which other agent, `2026-07-02-agent-dispatch-privilege-model`, has produced no record yet.
