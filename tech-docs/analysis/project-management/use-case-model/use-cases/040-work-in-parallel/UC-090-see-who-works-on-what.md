---
id: UC-090
title: See which agent works on which issue, without visiting each agent
status: active
actor: ACT-planner
other-actors: []
requirements:
  - REQ-062
after:
  - [UC-082, UC-092]
shortfalls:
  - at: 1
    issue: "#521"
    record: project-management:DEC-035#7
  - at: 1
    issue: "#521"
    record: project-management:DEC-059#6
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
        - .pkit/capabilities/project-management/scripts/seats.py
      record:
        - project-management:DEC-006
        - project-management:DEC-035#1
        - project-management:DEC-035#7
        - project-management:DEC-043#4
        - project-management:DEC-056#6
        - project-management:DEC-058#4
        - project-management:DEC-059#3
        - project-management:DEC-059#4
        - project-management:DEC-059#6
        - COR-017
        - COR-021
      artefact:
        - ACT-planner
        - REQ-062
---

# UC-090 — See which agent works on which issue, without visiting each agent

**Goal:** See which agent works on which issue, without visiting each agent.

**Other actors:** None.

**Preconditions:** **From [UC-082](UC-082-set-up-topology.md), or [UC-092](UC-092-take-seat.md):** Each agent's clone holds a [seat](../../../glossary.md#term-seat--seat) of the [topology](../../../glossary.md#term-topology--topology) ([DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and the commands of `pkit pm` ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).

**Trigger:** The planner wants the whole picture, such as after a restart, or before planning more work for the [topology](../../../glossary.md#term-topology--topology)'s agents.

**Main path:**

1. In any [instance](../../../glossary.md#term-instance--instance), the planner lists the open issues, each [issue](../../../glossary.md#term-issue--issue) signed with the issue's [owner](../../../glossary.md#term-owner--owner): this instance, another instance, or none ([DEC-035 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#7-listings-show-every-issue-signed-by-owner)). Each owner is named by the name of the owner's [seat](../../../glossary.md#term-seat--seat), such as `api-worker` ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

> [!WARNING]
> **Not built yet:** no command lists issues signed by their owner. DEC-035 point 7 decides the signed listing, and #521 tracks it.

> [!WARNING]
> **Not built yet:** no owner carries a seat's name. DEC-059 point 6 decides that an instance is named by its seat, and #521 tracks it.

2. For each owned [Task](../../../glossary.md#term-task--task), the planner reads the Task's state in the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle), In Progress or Review. The Task itself carries that state ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)).
3. The planner lists the seats of the [topology](../../../glossary.md#term-topology--topology): `pkit pm seats`. The listing shows each seat and the clone that holds the seat. The listing also shows whether the seat's agent plans, builds or does both ([DEC-059 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#3-each-seat-has-a-state-issue-which-the-topology-names)). Each holder is read from the seat's [state issue](../../../glossary.md#term-state-issue--state-issue) ([DEC-058 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#4-the-comments-are-the-record-and-the-description-shows-the-current-state)).

**Variants:**

- **1a.** The planner lists from a clone that holds no [seat](../../../glossary.md#term-seat--seat). The listing signs nothing, since only an [instance](../../../glossary.md#term-instance--instance) signs its listings ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology) and [DEC-035 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#1-activation-is-per-clone-and-opt-in)). The planner lists from an instance instead.
- **3a.** A [change](../../../../core/glossary.md#term-change--change) that added seats was closed unmerged. The listing of the seats names each [state issue](../../../glossary.md#term-state-issue--state-issue) that no seat names, for a person to close ([DEC-059 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#3-each-seat-has-a-state-issue-which-the-topology-names)).

**Postconditions:** The planner knows which [instance](../../../glossary.md#term-instance--instance) works on each open [issue](../../../glossary.md#term-issue--issue), and how far each owned [Task](../../../glossary.md#term-task--task) has come, without visiting any agent. The planner knows too which clone holds each [seat](../../../glossary.md#term-seat--seat).

**Minimal guarantees:**

- The [owner](../../../glossary.md#term-owner--owner) shown is read from the [issue](../../../glossary.md#term-issue--issue) itself, so every [instance](../../../glossary.md#term-instance--instance) shows the same owner ([DEC-043 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-043-ownership-substrate-selection.md#4-the-current-owner-is-mirrored-into-the-issue-description-as-a-derived-regenerable-view)).
- The clone that holds a [seat](../../../glossary.md#term-seat--seat) is read from the seat's [state issue](../../../glossary.md#term-state-issue--state-issue), so every instance shows the same holder ([DEC-058 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#4-the-comments-are-the-record-and-the-description-shows-the-current-state)).

## Open for the design

What the planner needs here that no accepted record decides yet:

- **The fixers' proposals across clones.** Each clone keeps the proposals its own runs made, and `land-work` prints only that clone's count ([project-management DEC-056 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-056-drift-fixers.md#6-the-proposals-wait-for-a-decision)). So the planner sees the proposals only by visiting each agent.
- **One view of all that waits on a person,** such as heads ready to merge and records waiting for acceptance. The maintainer decided on 17 October that one view lists all of that (#1682), and no record holds the decision yet.
- **Where each agent is heading,** beside what the agent owns. The pilot analysis proposed a command that shows where each agent is heading, under [EPIC](../../../glossary.md#term-epic--epic) #943, and no record decides on that command.
