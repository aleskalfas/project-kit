---
id: UC-087
title: Hand the next piece of the work to the scope that does that piece
status: active
actor: ACT-worker-agent
other-actors:
  - ACT-planning-agent
requirements:
  - REQ-040
  - REQ-041
after:
  - [UC-084]
  - [UC-083]
shortfalls:
  - at: "1a"
    issue: "#521"
    record: project-management:DEC-035#4
  - at: "4a"
    issue: "#519"
    record: project-management:DEC-035#3
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/handoff-issue.py
        - .pkit/capabilities/project-management/scripts/next-task.py
      record:
        - project-management:DEC-005
        - project-management:DEC-012
        - project-management:DEC-026
        - project-management:DEC-035#3
        - project-management:DEC-035#4
        - project-management:DEC-059#7
        - project-management:DEC-061#5
        - COR-017
        - COR-021
        - COR-042
      artefact:
        - ACT-worker-agent
        - ACT-planning-agent
        - REQ-040
        - REQ-041
---

# UC-087 — Hand the next piece of the work to the scope that does that piece

**Goal:** Hand the next piece of the work to the scope that does that piece, with what that piece needs from my piece.

**Other actors:** **Planning agent** (`ACT-planning-agent`): filed the next piece's [Task](../../../glossary.md#term-task--task) in that Task's own [scope](../../../glossary.md#term-scope--scope). The `## Dependencies` section of the next piece's Task names this piece's Task (`batch-plan.md`).

**Preconditions:**

- **From [UC-084](UC-084-take-next-task.md):** The worker's [instance](../../../glossary.md#term-instance--instance) owns this piece's [Task](../../../glossary.md#term-task--task), which is In Progress ([DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).
- **From [UC-083](UC-083-plan-across-scopes.md):** The next piece's Task is filed in that Task's own [scope](../../../glossary.md#term-scope--scope). That Task's `## Dependencies` section names this piece's Task ([DEC-005](../../../../../../.pkit/capabilities/project-management/decisions/DEC-005-linking-and-containment.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and the commands of `pkit pm` ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).

**Trigger:** The worker finishes the worker's piece of the work, such as an interface that another [scope](../../../glossary.md#term-scope--scope) builds on.

**Main path:**

1. The worker finishes this piece's [Task](../../../glossary.md#term-task--task). What the next piece needs from this piece's Task, such as an interface, lies in the work that Task lands.
2. The worker lands this piece's Task, as `UC-089` describes, and that Task closes ([DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).
3. The next piece's Task now names no open [issue](../../../glossary.md#term-issue--issue) in that Task's `## Dependencies` section ([DEC-005](../../../../../../.pkit/capabilities/project-management/decisions/DEC-005-linking-and-containment.md)).
4. The agent of the next piece's [scope](../../../glossary.md#term-scope--scope) takes that Task, as `UC-084` describes.

**Variants:**

- **1a.** The worker hands this piece's [Task](../../../glossary.md#term-task--task) to another [instance](../../../glossary.md#term-instance--instance) unfinished, such as when the [topology](../../../glossary.md#term-topology--topology) moves the Task's [workstream](../../../glossary.md#term-workstream--workstream) to another [scope](../../../glossary.md#term-scope--scope): `pkit pm handoff-issue <N> --to-instance <M> --reason "<R>"`. That instance becomes the [owner](../../../glossary.md#term-owner--owner), and the Task's state does not [change](../../../../core/glossary.md#term-change--change) ([DEC-035 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#4-ownership-releases-on-terminal-transitions-and-transfers-on-reclaim) and [DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).

> [!WARNING]
> **Not built yet:** `handoff-issue` hands an [issue](../../../glossary.md#term-issue--issue) from one person to another only. DEC-035 point 4 decides the hand-over between instances, and #521 tracks it.

- **4a.** The next piece's agent finds a defect in this piece. That agent files a Task in this piece's scope, as `UC-060` describes, and that agent's instance owns the Task ([DEC-035 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#3-a-clone-claims-at-creation-for-the-whole-tree)). This scope's agent takes the Task over, as `UC-084` variant 2a describes.

> [!WARNING]
> **Not built yet:** `create-issue` writes no owner. DEC-035 point 3 decides that the instance that files an issue owns the issue, and #519 tracks it.

- **4b.** The next piece is a Task of the kind `test`, and a testing [seat](../../../glossary.md#term-seat--seat)'s scope names that kind of work. That seat's agent may take the Task with `pkit pm next-task`, and so may the agent of every seat that builds with no scope. The command hands the Task to no seat whose scope leaves the Task out ([DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) and [DEC-012](../../../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)). Where the topology declares [pools](../../../glossary.md#term-pool--pool), only the seats that serve the pool of the Task's [Milestone](../../../glossary.md#term-milestone--milestone) may take the Task ([DEC-061 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-061-pools-of-workers.md#5-a-seat-that-builds-chooses-its-work-only-from-its-pools)).

**Postconditions:** What the next piece needs from this piece has landed on the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), and the next piece's [Task](../../../glossary.md#term-task--task) can start.

**Minimal guarantees:**

- A hand-over to another [owner](../../../glossary.md#term-owner--owner) never moves the [Task](../../../glossary.md#term-task--task) in the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) ([DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).

## Open for the design

What the worker needs here that no accepted record decides yet:

- **A checked hand-over between stages,** so that the next piece starts only from what this piece declared done. The core's [processes](../../../../core/glossary.md#term-process--process) can declare a hand-over that a check reports on. [COR-042](../../../../../../.pkit/decisions/core/COR-042-process-health.md) calls such a hand-over a hand-off contract. None is declared between stages of the work.
- **A scope by a discipline that no kind of work carries,** such as design, for the [seat](../../../glossary.md#term-seat--seat) that does that discipline's work. A [scope](../../../glossary.md#term-scope--scope) names testing by the kind of work `test` (variant 4b). [project-management DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) leaves a discipline with no kind to a record that decides how a [Task](../../../glossary.md#term-task--task) carries the discipline.
- **Typed dependencies.** While `## Dependencies` is prose, `pkit pm next-task` reads each `#N` the section names, and so finds the next piece's Task ready once this piece's Task closes. Typed `Blocked by:` lines are named in [project-management DEC-025](../../../../../../.pkit/capabilities/project-management/decisions/DEC-025-parallelization-primitive.md), and wait for lived evidence before they are built.
