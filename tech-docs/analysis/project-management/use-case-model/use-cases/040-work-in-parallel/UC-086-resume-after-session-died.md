---
id: UC-086
title: Take up my instance's work after my session died
status: active
actor: ACT-worker-agent
other-actors:
  - core:ACT-operator
requirements:
  - REQ-062
after:
  - [UC-084]
shortfalls:
  - at: 2
    issue: "#521"
    record: project-management:DEC-035#7
  - at: "1a"
    issue: "#519"
    record: project-management:DEC-059#9
  - at: "2a"
    issue: "#520"
    record: project-management:DEC-035#6
  - at: "2b"
    issue: "#2136"
    record: project-management:DEC-059#9
  - at: "2c"
    issue: "#2136"
    record: project-management:DEC-059#9
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/set-instance.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
        - .pkit/capabilities/project-management/scripts/start-work.py
      record:
        - project-management:DEC-035#1
        - project-management:DEC-035#4
        - project-management:DEC-035#6
        - project-management:DEC-035#7
        - project-management:DEC-043#4
        - project-management:DEC-058#5
        - project-management:DEC-059#4
        - project-management:DEC-059#5
        - project-management:DEC-059#7
        - project-management:DEC-059#9
        - project-management:DEC-013
        - project-management:DEC-026
        - COR-013
      artefact:
        - ACT-worker-agent
        - REQ-062
---

# UC-086 — Take up my instance's work after my session died

**Goal:** Take up my instance's work in flight after my session died, without losing what that session had done.

**Other actors:** **Operator** (`core:ACT-operator`): starts the new session in the same clone, on the machine or the sandbox where the clone lies.

**Preconditions:** **From [UC-084](UC-084-take-next-task.md):** The worker's [instance](../../../glossary.md#term-instance--instance) owns a [Task](../../../glossary.md#term-task--task) In Progress, on the Task's own branch ([DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).

**Assumptions:**

- The harness hosts a new session in the same clone. The clone still holds what the clone's last session committed ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md)).

**Trigger:** The operator starts a new session in the worker's clone after the clone's last session died, such as at a usage limit or a crash.

**Main path:**

1. The new session takes up the clone's [seat](../../../glossary.md#term-seat--seat) with `pkit pm take-seat`, since the clone's key outlived the dead session ([DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat) and [DEC-058 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#5-a-claim-on-a-state-issue-takes-the-shape-of-a-claim-on-a-task)). In the first mode, a seat stays taken until the seat is released, so no other clone took the seat meanwhile ([DEC-059 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#5-in-the-first-mode-a-seat-stays-taken-until-it-is-released)).

2. The worker lists the issues the worker's [instance](../../../glossary.md#term-instance--instance) owns, with the signed listing narrowed to that instance's issues ([DEC-035 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#7-listings-show-every-issue-signed-by-owner)).

> [!WARNING]
> **Not built yet:** no command lists issues signed by their [owner](../../../glossary.md#term-owner--owner). DEC-035 point 7 decides the signed listing and its narrowing, and #521 tracks it.

3. For each [Task](../../../glossary.md#term-task--task) In Progress, the worker finds the Task's branch, whose name carries the Task's number, and checks the branch out ([DEC-013](../../../../../../.pkit/capabilities/project-management/decisions/DEC-013-branch-and-pr-conventions.md)).
4. The worker reads the branch's commits, and the Task's [pull request](../../../../core/glossary.md#term-pull-request--pull-request) where one is open, to see what was done.
5. The worker goes on from there, and builds the rest of the Task, as `UC-084` steps 9, 7 and 8 describe.

**Variants:**

- **1a.** The clone is new, such as a clone that replaced another clone lost with that other clone's sandbox. The new clone takes a [seat](../../../glossary.md#term-seat--seat) as `UC-092` describes. The new clone inherits none of the lost clone's ownerships, which name the lost clone's key ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)). The lost clone's Tasks return to the ready Tasks once the lost clone's seat is released ([DEC-059 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#5-in-the-first-mode-a-seat-stays-taken-until-it-is-released)).

> [!WARNING]
> **Not built yet:** no command writes an ownership that names a clone's key. The read of an [issue](../../../glossary.md#term-issue--issue)'s [owner](../../../glossary.md#term-owner--owner) never asks whether the ownership's clone still holds the ownership's seat. DEC-059 point 9 decides that a clone never inherits another clone's ownership, and #519 tracks it.

- **2a.** The clone holds a [Task](../../../glossary.md#term-task--task)'s branch, but another [instance](../../../glossary.md#term-instance--instance) owns the Task now. That instance took the Task over while the session was dead ([DEC-035 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#4-ownership-releases-when-the-work-ends-or-stops-and-transfers-on-reclaim)). The worker's ordinary commands on the Task refuse, and name that instance ([DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock)). The worker leaves the Task to the Task's owner, as `UC-085` describes.

> [!WARNING]
> **Not built yet:** no ordinary command reads the owner, so the worker's commands on the Task go on. DEC-035 point 6 decides the refusal, and #520 tracks it.

- **2b.** The worker's ownership of a Task lapsed while the session was dead, since nothing renewed the ownership, and another clone took the Task over. Before writing, the worker finds that the Task is another clone's, and parks the worker's work, as `UC-084` variant 9a describes ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)).

> [!WARNING]
> **Not built yet:** no ownership lapses, and no session parks its work. DEC-059 point 9 decides both, and #2136 tracks it.

- **2c.** The worker's ownership lapsed, and no other clone took the Task. The Task is ready. The worker takes the Task over again from the worker's seat, as `UC-084` variant 2b describes (DEC-059 points [7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) and [9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)).

> [!WARNING]
> **Not built yet:** no ownership lapses. DEC-059 point 9 decides when an ownership stops counting, and #2136 tracks it.

- **4a.** Work the dead session never committed is lost. The worker builds that part again.

**Postconditions:** The worker goes on with each [Task](../../../glossary.md#term-task--task) the worker's [instance](../../../glossary.md#term-instance--instance) owns, on that Task's branch, from what the branch holds.

**Minimal guarantees:**

- The clone's key outlives every session in the clone, so a new session takes up the same [seat](../../../glossary.md#term-seat--seat) ([DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat)).
- The [owner](../../../glossary.md#term-owner--owner) of each [issue](../../../glossary.md#term-issue--issue) is read from the issue itself, so no session's memory is needed to find the owner ([DEC-043 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-043-ownership-substrate-selection.md#4-the-current-owner-is-mirrored-into-the-issue-description-as-a-derived-regenerable-view)).

## Open for the design

What the worker needs here that no accepted record decides yet:

- **Where the work was heading,** beyond what the branch shows. No record decides how a session leaves its next step on the [issue](../../../glossary.md#term-issue--issue). The pilot analysis's intent notes proposed a way, under [EPIC](../../../glossary.md#term-epic--epic) #943.
- **A session in a linked worktree** of the clone. [project-management DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology) leaves undecided how a linked worktree reads its clone's identity. Today a linked worktree reads no number of its clone, and #1140 proposes that a linked worktree reads its clone's number.
