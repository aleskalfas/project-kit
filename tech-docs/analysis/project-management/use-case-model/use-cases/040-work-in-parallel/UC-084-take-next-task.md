---
id: UC-084
title: Take my next ready Task, and build it up to its merge
status: active
actor: ACT-worker-agent
other-actors:
  - core:ACT-operator
requirements:
  - REQ-061
  - REQ-040
  - REQ-041
after:
  - [UC-092]
  - [UC-083, UC-060]
shortfalls:
  - at: 1
    issue: "#521"
    record: project-management:DEC-035#7
  - at: 5
    issue: "#519"
    record: project-management:DEC-035#3
  - at: 5
    issue: "#519"
    record: project-management:DEC-059#9
  - at: 6
    issue: "#519"
    record: project-management:DEC-035#6
  - at: 9
    issue: "#2136"
    record: project-management:DEC-059#9
  - at: "2a"
    issue: "#521"
    record: project-management:DEC-035#4
  - at: "2b"
    issue: "#2136"
    record: project-management:DEC-059#9
  - at: "3a"
    issue: "#2136"
    record: project-management:DEC-045#5
  - at: "9a"
    issue: "#2136"
    record: project-management:DEC-059#9
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/next-task.py
        - .pkit/capabilities/project-management/scripts/_lib/task_pool.py
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/review-work.py
        - .pkit/capabilities/project-management/scripts/handoff-issue.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
      record:
        - project-management:DEC-026
        - project-management:DEC-029
        - project-management:DEC-005
        - project-management:DEC-012
        - project-management:DEC-035#3
        - project-management:DEC-035#4
        - project-management:DEC-035#6
        - project-management:DEC-035#7
        - project-management:DEC-035#8
        - project-management:DEC-045#5
        - project-management:DEC-059#2
        - project-management:DEC-059#4
        - project-management:DEC-059#7
        - project-management:DEC-059#8
        - project-management:DEC-059#9
        - COR-013
        - COR-017
        - COR-021
        - COR-039
        - ADR-034#1
      artefact:
        - ACT-worker-agent
        - REQ-061
        - REQ-040
        - REQ-041
---

# UC-084 — Take my next ready Task, and build it up to its merge

**Goal:** Take my next ready Task, one that no other agent works on, and build it up to its merge.

**Other actors:** **Operator** (`core:ACT-operator`): is asked before a command changes a repository other than the session's own, so no such write happens silently ([core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:**

- **From [UC-092](UC-092-take-seat.md):** The worker's clone holds a worker agent's [seat](../../../glossary.md#term-seat--seat), and the worker acts as that seat's agent (DEC-059 points [4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat) and [8](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#8-the-agent-a-seat-names-runs-the-seats-role-through-the-pm-skill)).
- **From [UC-083](UC-083-plan-across-scopes.md), or [UC-060](../020-file-and-move/UC-060-file-task.md):** Tasks are filed, each with its [workstream](../../../glossary.md#term-workstream--workstream) ([DEC-012](../../../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and the commands of `pkit pm` ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).
- The harness hosts the worker's session in the worker's own clone ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md)).

**Trigger:** The worker has no [Task](../../../glossary.md#term-task--task) in flight, and Tasks wait to be built.

**Main path:**

1. The worker lists the open Tasks in Backlog and In Progress, each [Task](../../../glossary.md#term-task--task) signed with the Task's [owner](../../../glossary.md#term-owner--owner) ([DEC-035 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#7-listings-show-every-issue-signed-by-owner)). The owner is the worker's own [instance](../../../glossary.md#term-instance--instance), another instance, or none.

> [!WARNING]
> **Not built yet:** no command lists issues signed by their owner. DEC-035 point 7 decides the signed listing, and #521 tracks it.

2. The worker asks for the next Task to build: `pkit pm next-task`. Of the Tasks in Backlog with no owner, the system keeps those whose `## Dependencies` section names no [issue](../../../glossary.md#term-issue--issue) still open. These Tasks are ready, as are the Tasks In Progress of variant 2b, and every [seat](../../../glossary.md#term-seat--seat) shares the ready Tasks ([DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) and [DEC-005](../../../../../../.pkit/capabilities/project-management/decisions/DEC-005-linking-and-containment.md)).
3. Where the worker's seat gives the worker a [scope](../../../glossary.md#term-scope--scope), the system keeps the Tasks that fall in the scope. A scope naming [Milestones](../../../glossary.md#term-milestone--milestone) by number keeps only their Tasks, and the system names each ready Task left out, with the reason ([DEC-059 point 2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#2-a-seat-has-a-name-a-role-an-agent-and-an-optional-scope)). The system chooses the highest in priority among the Tasks in Backlog that the worker's instance owns and whose dependencies name no open issue. Where there is none, the system chooses the highest in priority among the ready Tasks (DEC-059 point 7 and [DEC-012](../../../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).
4. The system starts the chosen Task through `pkit pm start-work <N>`. That command checks the move, cuts the Task's branch, assigns the worker's account and moves the Task to In Progress ([DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).
5. The system makes the worker's instance the Task's owner ([DEC-035 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#3-a-clone-claims-at-creation-for-the-whole-tree)). The ownership names the worker's seat, the seat's number and the clone's key ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)).

> [!WARNING]
> **Not built yet:** `start-work` writes no owner. DEC-035 point 3 decides that an instance that starts an issue with no owner becomes the issue's owner, and #519 tracks it.

> [!WARNING]
> **Not built yet:** no command writes an ownership that names a seat or a clone's key. DEC-059 point 9 decides what an ownership names, and #519 tracks it.

6. The system reads the Task again after writing, and finds the worker's instance the Task's only owner ([DEC-035 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#6-the-clash-guard-catches-and-resolves-it-does-not-lock)).

> [!WARNING]
> **Not built yet:** `start-work` reads nothing back. DEC-035 point 6 decides that the command that takes an issue reads the issue again to catch a clash, and #519 tracks it.

9. As the worker builds, the worker's work renews the ownership, each renewal by a separate ownership event. The worker renews the ownership before each push, and at least once within a part of the limit the [topology](../../../glossary.md#term-topology--topology) sets (DEC-059 point 9). Before each push, the worker also checks that the worker's clone still holds the seat, and that the ownership still counts.

> [!WARNING]
> **Not built yet:** nothing renews an ownership, or checks an ownership before a push. DEC-059 point 9 decides both, and #2136 tracks it.

7. The worker builds the Task on the Task's branch, and opens the Task's [pull request](../../../../core/glossary.md#term-pull-request--pull-request): `pkit pm review-work <N>`, as `UC-061` step 7 describes (DEC-026).
8. The worker lands the Task, as `UC-089` describes.

**Variants:**

- **1a.** The listing holds no ready [Task](../../../glossary.md#term-task--task). The worker starts nothing, and the use case ends.
- **2a.** A Task in Backlog is owned by the [instance](../../../glossary.md#term-instance--instance) that filed the Task, such as a lead agent's instance no longer working on the Task. The worker takes the Task over: `pkit pm handoff-issue <N> --to-instance self --reason "<R>"`. The worker's instance becomes the [owner](../../../glossary.md#term-owner--owner), and the path goes on at step 3 ([DEC-035 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#4-ownership-releases-on-terminal-transitions-and-transfers-on-reclaim)).

> [!WARNING]
> **Not built yet:** `handoff-issue` hands an [issue](../../../glossary.md#term-issue--issue) from one person to another only. DEC-035 point 4 decides that an instance takes over another instance's issue, and #521 tracks it.

- **2b.** A Task In Progress has an ownership that no longer counts, since the ownership lapsed or the ownership's [seat](../../../glossary.md#term-seat--seat) was released ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)). The Task is ready, and the worker takes the Task over and goes on from the Task's branch ([DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) and [DEC-035 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#4-ownership-releases-on-terminal-transitions-and-transfers-on-reclaim)).

> [!WARNING]
> **Not built yet:** no ownership lapses. DEC-059 point 9 decides when an ownership lapses, and #2136 tracks it.

- **3a.** The worker chooses a Task that only another seat may take. The system warns that the other seat is expected to take the Task, and goes on ([DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) and [DEC-045 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#5-ownership-derivation-feeds-the-pm-layer-guard-only-and-degrades-gracefully)).

> [!WARNING]
> **Not built yet:** nothing reads which seat alone may take a Task, so nothing warns. DEC-045 point 5 decides the warning, and #2136 tracks it.

- **4a.** The Task is assigned to another person's account. `start-work` refuses, points to `handoff-issue`, and changes nothing (`start-work.py`).
- **5a.** Another instance owns the Task already, or takes the Task at the same instant. The path goes on as `UC-085` describes.
- **9a.** The check before a push finds that the ownership lapsed, or passed to another clone. The worker parks the work on a separate branch, and writes nothing to the Task's branch or [pull request](../../../../core/glossary.md#term-pull-request--pull-request). The worker says on the Task where the parked work lies ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)).

> [!WARNING]
> **Not built yet:** no session parks its work. DEC-059 point 9 decides how a session parks the work, and #2136 tracks it.

**Postconditions:** The worker's [instance](../../../glossary.md#term-instance--instance) owns the [Task](../../../glossary.md#term-task--task), which is In Progress on the Task's own branch, and the Task's [pull request](../../../../core/glossary.md#term-pull-request--pull-request) is open.

**Minimal guarantees:**

- A start refused at its checks writes no branch and no assignee (`start-work.py`).
- The [owner](../../../glossary.md#term-owner--owner) is never an input to a move of the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) ([DEC-035 point 8](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#8-the-instance-marker-is-a-pm-domain-side-effect-never-engine-state)).
- A worker whose ownership no longer counts writes nothing to the [Task](../../../glossary.md#term-task--task)'s branch or [pull request](../../../../core/glossary.md#term-pull-request--pull-request) ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)).
- Renewal and lapse use the time GitHub records for each comment, so no clone's clock decides them (DEC-059 point 9).

## Open for the design

What the worker needs here that no accepted record decides yet:

- **Taking over a Task in Backlog.** [project-management DEC-035 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#4-ownership-releases-on-terminal-transitions-and-transfers-on-reclaim) adds the takeover to `handoff-issue`, which [project-management DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md) lets act only on an [issue](../../../glossary.md#term-issue--issue) In Progress or in Review. No record says which of the two holds for a [Task](../../../glossary.md#term-task--task) in Backlog.
- **Typed dependencies.** While `## Dependencies` is prose, `pkit pm next-task` reads each `#N` the section names. Typed `Blocked by:` lines are named in [project-management DEC-025](../../../../../../.pkit/capabilities/project-management/decisions/DEC-025-parallelization-primitive.md), and wait for lived evidence before they are built. [DEC-059](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md) names typed dependencies between Tasks for later.
- **Whether the worker asks the person anything,** or only stops when the worker's [pull request](../../../../core/glossary.md#term-pull-request--pull-request) is ready to merge. The maintainer decided on 17 October that agents bring the person's decisions in one batch (#1675), and no record holds that decision yet.
