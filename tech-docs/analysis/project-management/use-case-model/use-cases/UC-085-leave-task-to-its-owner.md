---
id: UC-085
title: Never work on a Task another agent already works on
status: active
actor: ACT-worker-agent
other-actors:
  - ACT-director
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
        - project-management:DEC-014
        - project-management:DEC-026
        - project-management:DEC-012
        - COR-017
        - COR-021
      artefact:
        - ACT-worker-agent
        - ACT-director
        - REQ-061
        - REQ-040
        - REQ-041
---

# UC-085 — Never work on a Task another agent already works on

**Goal:** Never work on a Task that another agent already works on.

**Other actors:** **Director** (`ACT-director`): only a person sets the refusal aside, with a reason that an [audit comment](../../glossary.md#term-audit-comment--audit-comment) records before the start (DEC-014).

**Preconditions:** **From UC-083, or UC-060:** The [Task](../../glossary.md#term-task--task) is filed in the worker's [scope](../../glossary.md#term-scope--scope) (DEC-012).

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).

**Trigger:** The worker starts a [Task](../../glossary.md#term-task--task) that another [instance](../../glossary.md#term-instance--instance) owns, or that another instance starts at the same instant.

**Main path:**

1. The worker starts a [Task](../../glossary.md#term-task--task) of its [scope](../../glossary.md#term-scope--scope): `pkit pm start-work <N>`.
2. Before it changes anything, the system reads the Task's [owner](../../glossary.md#term-owner--owner) (DEC-035 point 6).

> [!WARNING]
> **Not built yet:** `start-work` reads no owner. DEC-035 point 6 decides that an ordinary command reads the owner first, and #520 tracks it.

3. Another [instance](../../glossary.md#term-instance--instance) owns the Task. The system refuses the start, names that instance, and writes nothing (DEC-035 point 6).

> [!WARNING]
> **Not built yet:** `start-work` starts the Task again for a second instance under the same account. DEC-035 point 6 decides the refusal, and #520 tracks it.

4. The worker leaves the Task to its owner, and takes another, as `UC-084` describes.

**Variants:**

- **1a.** The worker acts on the [Task](../../glossary.md#term-task--task) with another ordinary command: `done-work`, `edit-issue` or `move-issue`. The system refuses as at step 3 (DEC-035 point 6).

> [!WARNING]
> **Not built yet:** none of these commands reads the [owner](../../glossary.md#term-owner--owner). DEC-035 point 6 decides the refusal, and #520 tracks it.

- **2a.** No [instance](../../glossary.md#term-instance--instance) owns the Task, and another instance starts it at the same instant. Each writes its owner, reads the Task again and finds two owners. The higher-numbered instance gives the Task up and says so, and the lower one keeps it (DEC-035 point 6).

> [!WARNING]
> **Not built yet:** no command writes an owner or reads the Task back, so both instances go on. DEC-035 point 6 decides that the higher number gives the Task up, and #519 tracks it.

- **2b.** The Task is assigned to another person's account. `start-work` refuses, points to `handoff-issue`, and changes nothing (`start-work.py`).
- **3a.** The director decides that the worker takes the Task all the same. The worker sets the refusal aside with the director's reason, which an [audit comment](../../glossary.md#term-audit-comment--audit-comment) records before the start (DEC-035 point 6 and DEC-014).

> [!WARNING]
> **Not built yet:** there is no refusal to set aside. DEC-035 point 6 decides that the refusal yields to a reason, and #520 tracks it.

- **3b.** The owner's agent no longer works on the Task, such as one whose [scope](../../glossary.md#term-scope--scope) changed. The worker takes the Task over: `pkit pm handoff-issue <N> --to-instance self --reason "<R>"`. Its instance becomes the owner, and the assignee stays (DEC-035 point 4).

> [!WARNING]
> **Not built yet:** `handoff-issue` hands an [issue](../../glossary.md#term-issue--issue) from one person to another only. DEC-035 point 4 decides the hand-over between instances, and #521 tracks it.

**Postconditions:** The [Task](../../glossary.md#term-task--task) has one [owner](../../glossary.md#term-owner--owner), and the worker works on no Task that its [instance](../../glossary.md#term-instance--instance) does not own, unless a person set the refusal aside.

**Minimal guarantees:**

- A start the system refuses writes nothing (`start-work.py`).
- Two [instances](../../glossary.md#term-instance--instance) that take one [Task](../../glossary.md#term-task--task) at the same instant end with one [owner](../../glossary.md#term-owner--owner) (DEC-035 point 6).
- A refusal never moves the Task in the [issue lifecycle](../../glossary.md#term-issue-lifecycle--issue-lifecycle), since the owner is no input to a move (DEC-035 point 8).

## Open for the design

What the worker needs here that no accepted record decides yet:

- **Instances of two people** that take one [Task](../../glossary.md#term-task--task) at the same instant. DEC-035 leaves the tie-break between people for later.
- **Agents with GitHub accounts of their own.** Today every agent acts under its person's account, so only the [instances](../../glossary.md#term-instance--instance) tell the agents apart. Accounts for agents are named for later under [EPIC](../../glossary.md#term-epic--epic) #1673, and no [issue](../../glossary.md#term-issue--issue) tracks them.
