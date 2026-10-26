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
  - at: "2a"
    issue: "#520"
    record: project-management:DEC-035#6
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

**Preconditions:** **From UC-084:** The worker's [instance](../../../glossary.md#term-instance--instance) owns a [Task](../../../glossary.md#term-task--task) In Progress, on the Task's own branch (DEC-026).

**Assumptions:**

- The harness hosts a new session in the same clone, which still holds what its last session committed (COR-013).

**Trigger:** The operator starts a new session in the worker's clone after its last session died, such as at a usage limit or a crash.

**Main path:**

1. The new session reads the clone's number: `pkit pm set-instance --show`. The number outlived the session that died (DEC-035 point 1).
2. The worker lists the issues its [instance](../../../glossary.md#term-instance--instance) owns, with the signed listing narrowed to its own (DEC-035 point 7).

> [!WARNING]
> **Not built yet:** no command lists issues signed by their [owner](../../../glossary.md#term-owner--owner). DEC-035 point 7 decides the signed listing and its narrowing, and #521 tracks it.

3. For each [Task](../../../glossary.md#term-task--task) In Progress, the worker finds the Task's branch, whose name carries the Task's number, and checks it out (DEC-013).
4. The worker reads the branch's commits, and the Task's [pull request](../../../../core/glossary.md#term-pull-request--pull-request) where one is open, to see what was done.
5. The worker goes on from there, and builds the rest of the Task, as `UC-084` describes from its step 7.

**Variants:**

- **1a.** The clone has set no number, such as a fresh clone. Nothing marks which Tasks were its own, and the worker finds them only among the issues assigned to its account (DEC-035 point 1).
- **2a.** The clone holds a [Task](../../../glossary.md#term-task--task)'s branch, but another [instance](../../../glossary.md#term-instance--instance) owns the Task now. That instance took the Task over while the session was dead (DEC-035 point 4). The worker's ordinary commands on the Task refuse, and name that instance (DEC-035 point 6). The worker leaves the Task to its [owner](../../../glossary.md#term-owner--owner), as `UC-085` describes.

> [!WARNING]
> **Not built yet:** no ordinary command reads the owner, so the worker's commands on the Task go on. DEC-035 point 6 decides the refusal, and #520 tracks it.

- **4a.** Work the dead session never committed is lost. The worker builds that part again.

**Postconditions:** The worker goes on with each [Task](../../../glossary.md#term-task--task) its [instance](../../../glossary.md#term-instance--instance) owns, on that Task's branch, from what the branch holds.

**Minimal guarantees:**

- The clone's number outlives every session in it (DEC-035 point 1).
- The [owner](../../../glossary.md#term-owner--owner) of each [issue](../../../glossary.md#term-issue--issue) is read from the issue itself, so no session's memory is needed to find it (DEC-043 point 4).

## Open for the design

What the worker needs here that no accepted record decides yet:

- **The seat after a session died, decided.** In the first and most tolerant mode, a [seat](../../../glossary.md#term-seat--seat) stays taken until its clone releases it, or until a release by force. So a new session in the same clone finds its seat still held, and goes on as that seat's agent, as `UC-092` describes. The maintainer decided it on 26 October, and a project-management record on [topologies](../../../glossary.md#term-topology--topology) is to hold it (#512).
- **The Tasks after a session died, decided.** The work renews a [Task](../../../glossary.md#term-task--task)'s ownership, and a generous limit ends an ownership the work no longer renews (`UC-085`). So a session that comes back late may find that another [instance](../../../glossary.md#term-instance--instance) owns the Task. It checks that before it writes, and parks its work where the Task is no longer its own. The maintainer decided it on 26 October, and no record holds it yet.
- **Where the work was heading,** beyond what the branch shows. No record decides how a session leaves its next step on the [issue](../../../glossary.md#term-issue--issue). The pilot analysis's intent notes proposed one, under [EPIC](../../../glossary.md#term-epic--epic) #943.
- **A session in a linked worktree** of the clone. Today it reads no number of its clone. #1140 proposes that it reads its clone's number, which refines DEC-035 point 1 and waits for the maintainer's sign-off.
