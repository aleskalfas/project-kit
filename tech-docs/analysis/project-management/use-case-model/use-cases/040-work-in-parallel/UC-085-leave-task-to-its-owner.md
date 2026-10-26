---
id: UC-085
title: Never work on a Task another agent already works on
status: active
actor: ACT-worker-agent
other-actors:
  - core:ACT-developer
requirements:
  - REQ-061
  - REQ-040
  - REQ-041
after:
  - [UC-083, UC-060]
shortfalls:
  - at: 2
    issue: "#520"
    record: project-management:DEC-035#6
  - at: 2
    issue: "#2141"
    record: project-management:DEC-059#6
  - at: 3
    issue: "#520"
    record: project-management:DEC-035#6
  - at: "1a"
    issue: "#520"
    record: project-management:DEC-035#6
  - at: "2a"
    issue: "#519"
    record: project-management:DEC-035#6
  - at: "3a"
    issue: "#520"
    record: project-management:DEC-035#6
  - at: "3b"
    issue: "#521"
    record: project-management:DEC-035#4
  - at: "3c"
    issue: "#2136"
    record: project-management:DEC-059#9
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/handoff-issue.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
      record:
        - project-management:DEC-035#3
        - project-management:DEC-035#4
        - project-management:DEC-035#6
        - project-management:DEC-035#8
        - project-management:DEC-043#3
        - project-management:DEC-059#6
        - project-management:DEC-059#9
        - project-management:DEC-014
        - project-management:DEC-026
        - project-management:DEC-012
        - COR-017
        - COR-021
      artefact:
        - ACT-worker-agent
        - REQ-061
        - REQ-040
        - REQ-041
---

# UC-085 — Never work on a Task another agent already works on

**Goal:** Never work on a Task that another agent already works on.

**Other actors:** **Developer** (`core:ACT-developer`): only a person sets the refusal aside, with a reason that an [audit comment](../../../glossary.md#term-audit-comment--audit-comment) records before the start ([DEC-014](../../../../../../.pkit/capabilities/project-management/decisions/DEC-014-validation-severity-model.md)).

**Preconditions:** **From [UC-083](UC-083-plan-across-scopes.md), or [UC-060](../020-file-and-move/UC-060-file-task.md):** The [Task](../../../glossary.md#term-task--task) is filed, with its [workstream](../../../glossary.md#term-workstream--workstream) ([DEC-012](../../../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and the commands of `pkit pm` ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).

**Trigger:** The worker starts a [Task](../../../glossary.md#term-task--task) that another [instance](../../../glossary.md#term-instance--instance) owns, or that another instance starts at the same instant.

**Main path:**

1. The worker starts a [Task](../../../glossary.md#term-task--task): `pkit pm start-work <N>`.
2. Before changing anything, the system reads the Task's [owner](../../../glossary.md#term-owner--owner) ([DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock)). With a [topology](../../../glossary.md#term-topology--topology), the system first confirms on the [seat](../../../glossary.md#term-seat--seat)'s [state issue](../../../glossary.md#term-state-issue--state-issue) that the worker's clone still holds the seat ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

> [!WARNING]
> **Not built yet:** `start-work` reads no owner. DEC-035 point 6 decides that an ordinary command reads the owner first, and #520 tracks it.

> [!WARNING]
> **Not built yet:** no command confirms a clone's seat. DEC-059 point 6 decides that every command acting as an [instance](../../../glossary.md#term-instance--instance) confirms the clone's seat before writing, and #2141 tracks it.

3. Another instance owns the Task. The system refuses the start, names that instance, and writes nothing (DEC-035 point 6).

> [!WARNING]
> **Not built yet:** `start-work` starts the Task again for a second instance under the same account. DEC-035 point 6 decides the refusal, and #520 tracks it.

4. The worker leaves the Task to the Task's owner, and takes another Task, as `UC-084` describes.

**Variants:**

- **1a.** The worker acts on the [Task](../../../glossary.md#term-task--task) with another ordinary command: `done-work`, `edit-issue` or `move-issue`. The system refuses as at step 3 ([DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock)).

> [!WARNING]
> **Not built yet:** none of these commands reads the [owner](../../../glossary.md#term-owner--owner). DEC-035 point 6 decides the refusal, and #520 tracks it.

- **2a.** No [instance](../../../glossary.md#term-instance--instance) owns the Task, and another instance starts the Task at the same instant. Each instance writes itself as the Task's owner, reads the Task again and finds two owners. The higher-numbered instance gives the Task up and says so, and the lower-numbered instance keeps the Task ([DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock)).

> [!WARNING]
> **Not built yet:** no command writes an owner or reads the Task back, so both instances go on. DEC-035 point 6 decides that the higher number gives the Task up, and #519 tracks it.

- **2b.** The Task is assigned to another person's account. `start-work` refuses, points to `handoff-issue`, and changes nothing (`start-work.py`).
- **3a.** The developer decides that the worker takes the Task all the same, and sets the refusal aside with a reason. The worker passes that reason with the worker's start, and an [audit comment](../../../glossary.md#term-audit-comment--audit-comment) records the reason before the start ([DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock) and [DEC-014](../../../../../../.pkit/capabilities/project-management/decisions/DEC-014-validation-severity-model.md)).

> [!WARNING]
> **Not built yet:** there is no refusal to set aside. DEC-035 point 6 decides that the refusal yields to a reason, and #520 tracks it.

- **3b.** The owner's agent no longer works on the Task, such as an agent whose [scope](../../../glossary.md#term-scope--scope) changed. The worker takes the Task over: `pkit pm handoff-issue <N> --to-instance self --reason "<R>"`. The worker's instance becomes the owner, and the assignee stays ([DEC-035 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#4-ownership-releases-on-terminal-transitions-and-transfers-on-reclaim)).

> [!WARNING]
> **Not built yet:** `handoff-issue` hands an [issue](../../../glossary.md#term-issue--issue) from one person to another only. DEC-035 point 4 decides the hand-over between instances, and #521 tracks it.

- **3c.** The owner's ownership no longer counts, since the ownership lapsed or the owner's [seat](../../../glossary.md#term-seat--seat) was released. The system does not refuse, and the worker takes the Task over, as `UC-084` variant 2b describes ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again) and [DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock)).

> [!WARNING]
> **Not built yet:** no ownership lapses or stops counting. DEC-059 point 9 decides that an ownership that no longer counts is no ownership, and #2136 tracks it.

**Postconditions:** The [Task](../../../glossary.md#term-task--task) has one [owner](../../../glossary.md#term-owner--owner). The worker works on no Task that the worker's [instance](../../../glossary.md#term-instance--instance) does not own, unless a person set the refusal aside.

**Minimal guarantees:**

- A start the system refuses writes nothing (`start-work.py`).
- Two [instances](../../../glossary.md#term-instance--instance) that take one [Task](../../../glossary.md#term-task--task) at the same instant end with one [owner](../../../glossary.md#term-owner--owner) ([DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock)).
- A refusal never moves the Task in the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle), since the owner is no input to a move ([DEC-035 point 8](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#8-the-instance-marker-is-a-pm-domain-side-effect-never-engine-state)).

## Open for the design

What the worker needs here that no accepted record decides yet:

- **Instances of two people** that take one [Task](../../../glossary.md#term-task--task) at the same instant. [project-management DEC-035](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md) leaves the tie-break between people for later. A [topology](../../../glossary.md#term-topology--topology) numbers its [seats](../../../glossary.md#term-seat--seat) across the whole [project](../../../../core/glossary.md#term-project--project) ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)), and no record says whether the lower number then wins between people.
- **Agents with GitHub accounts of their own.** Today every agent acts under its person's account, so only the [instances](../../../glossary.md#term-instance--instance) tell the agents apart. [DEC-059](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md) names accounts for agents for later, as [EPIC](../../../glossary.md#term-epic--epic) #1673 does, and no [issue](../../../glossary.md#term-issue--issue) tracks accounts for agents.
