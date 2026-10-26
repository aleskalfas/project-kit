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
  - at: 6
    issue: "#519"
    record: project-management:DEC-035#6
  - at: "2a"
    issue: "#521"
    record: project-management:DEC-035#4
  - at: "3a"
    issue: "#512"
    record: project-management:DEC-045#5
pkit:
  friction:
    anchors:
      path:
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

**Other actors:** **Operator** (`core:ACT-operator`): is asked before a command changes a repository other than the session's own, so no such write happens silently (core:REQ-012).

**Preconditions:**

- **From UC-092:** The worker's clone has its number, and the worker acts as a worker agent (DEC-035 point 1 and DEC-029).
- **From UC-083, or UC-060:** Tasks are filed, each with its [workstream](../../../glossary.md#term-workstream--workstream) (DEC-012).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).
- The harness hosts the worker's session in the worker's own clone (COR-013).

**Trigger:** The worker has no [Task](../../../glossary.md#term-task--task) in flight, and Tasks wait in Backlog.

**Main path:**

1. The worker lists the open Tasks in Backlog, each signed with its [owner](../../../glossary.md#term-owner--owner) (DEC-035 point 7). The owner is the worker's own [instance](../../../glossary.md#term-instance--instance), another instance, or none.

> [!WARNING]
> **Not built yet:** no command lists issues signed by their owner. DEC-035 point 7 decides the signed listing, and #521 tracks it.

2. Of the Tasks with no owner, the worker keeps those whose `## Dependencies` section names no [issue](../../../glossary.md#term-issue--issue) still open (DEC-005).
3. The worker chooses one of them, the highest in priority (DEC-012).
4. The worker starts it: `pkit pm start-work <N>`. The system checks the move, cuts the [Task](../../../glossary.md#term-task--task)'s branch, assigns the worker's account and moves the Task to In Progress (DEC-026).
5. The system makes the worker's instance the Task's owner (DEC-035 point 3).

> [!WARNING]
> **Not built yet:** `start-work` writes no owner. DEC-035 point 3 decides that starting an issue with no owner makes the instance its owner, and #519 tracks it.

6. The system reads the Task again after writing, and finds the worker's instance its only owner (DEC-035 point 6).

> [!WARNING]
> **Not built yet:** `start-work` reads nothing back. DEC-035 point 6 decides that the command that takes an issue reads it again to catch a clash, and #519 tracks it.

7. The worker builds the Task on its branch, and opens its [pull request](../../../../core/glossary.md#term-pull-request--pull-request): `pkit pm review-work <N>`, as `UC-061` step 7 describes (DEC-026).
8. The worker lands the Task, as `UC-089` describes.

**Variants:**

- **1a.** The listing holds no [Task](../../../glossary.md#term-task--task) with no [owner](../../../glossary.md#term-owner--owner) and no open dependency. The worker starts nothing, and the use case ends.
- **2a.** A Task in Backlog is owned by the [instance](../../../glossary.md#term-instance--instance) that filed it, such as the planning agent's. The worker takes it over: `pkit pm handoff-issue <N> --to-instance self --reason "<R>"`. Its instance becomes the owner, and the path goes on at step 3 (DEC-035 point 4).

> [!WARNING]
> **Not built yet:** `handoff-issue` hands an [issue](../../../glossary.md#term-issue--issue) from one person to another only. DEC-035 point 4 decides that an instance takes over another's issue, and #521 tracks it.

- **3a.** The worker chooses a Task whose [workstream](../../../glossary.md#term-workstream--workstream) only another agent's [scope](../../../glossary.md#term-scope--scope) names. The system warns that the other agent's instance is the one expected to take it, and goes on (DEC-045 point 5).

> [!WARNING]
> **Not built yet:** nothing reads which instance a workstream is expected to go to, so nothing warns. DEC-045 point 5 decides the warning, and #512 tracks it.

- **4a.** The Task is assigned to another person's account. `start-work` refuses, points to `handoff-issue`, and changes nothing (`start-work.py`).
- **5a.** Another instance owns the Task already, or takes it at the same instant. The path goes on as `UC-085` describes.

**Postconditions:** The worker's [instance](../../../glossary.md#term-instance--instance) owns the [Task](../../../glossary.md#term-task--task), which is In Progress on its own branch, and its [pull request](../../../../core/glossary.md#term-pull-request--pull-request) is open.

**Minimal guarantees:**

- A start refused at its checks writes no branch and no assignee (`start-work.py`).
- The [owner](../../../glossary.md#term-owner--owner) is never an input to a move of the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) (DEC-035 point 8).

## Open for the design

What the worker needs here that no accepted record decides yet. The maintainer decided the first three on 26 October, and a project-management record on [topologies](../../../glossary.md#term-topology--topology) is to hold them (#512):

- **One shared pool, decided.** By default, workers take the next ready [Task](../../../glossary.md#term-task--task) from one shared pool, the highest in priority first. They skip Tasks that wait on other issues still open. The [owner](../../../glossary.md#term-owner--owner) keeps the agents apart, as `UC-085` describes.
- **Work sliced across layers, decided.** The planning agent slices the work vertically, so one agent can finish a Task or a [Feature](../../../glossary.md#term-feature--feature) end to end, across the software's layers. [Workstreams](../../../glossary.md#term-workstream--workstream) as software layers are not the partition, since agents split by layer must coordinate across layers.
- **A seat's scope as a filter, decided.** A [seat](../../../glossary.md#term-seat--seat)'s [scope](../../../glossary.md#term-scope--scope) stays optional, and narrows the pool where it is given. It names a discipline for a specialist's seat, such as design or testing, and later a workstream, for a seat that keeps to one area. DEC-045 point 3 gives a scope as workstreams alone, so no form for a discipline is decided.
- **Taking over a Task in Backlog.** DEC-035 point 4 adds the takeover to `handoff-issue`, which DEC-026 lets act only on an [issue](../../../glossary.md#term-issue--issue) In Progress or in Review. No record says which of the two holds for a Task in Backlog.
- **Which Tasks are ready to start.** While `## Dependencies` is prose, the worker reads each one. Typed `Blocked by:` lines, and a listing of the Tasks ready to start, are DEC-025's, which is proposed.
- **Whether the worker asks the person anything,** or only stops when its [pull request](../../../../core/glossary.md#term-pull-request--pull-request) is ready to merge. The maintainer decided on 17 October that agents bring the person's decisions in one batch (#1675), and no record holds it yet.
