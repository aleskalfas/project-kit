---
id: UC-090
title: See which agent works on which issue, without visiting each agent
status: active
actor: ACT-director
other-actors: []
requirements:
  - REQ-062
after:
  - [UC-082]
shortfalls:
  - at: 1
    issue: "#521"
    record: project-management:DEC-035#7
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
      record:
        - project-management:DEC-006
        - project-management:DEC-035#1
        - project-management:DEC-035#7
        - project-management:DEC-045#1
        - project-management:DEC-045#2
        - project-management:DEC-043#4
        - project-management:DEC-056#6
        - COR-017
        - COR-021
      artefact:
        - ACT-director
        - REQ-062
---

# UC-090 — See which agent works on which issue, without visiting each agent

**Goal:** See which agent works on which issue, without visiting each agent.

**Other actors:** None.

**Preconditions:** **From UC-082:** Each agent's clone has its number (DEC-035 point 1).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).

**Trigger:** The director wants the whole picture, such as after a restart, or before changing the [topology](../../../glossary.md#term-topology--topology).

**Main path:**

1. In any [instance](../../../glossary.md#term-instance--instance), the director lists the open issues, each signed with its [owner](../../../glossary.md#term-owner--owner): this instance, another instance, or none (DEC-035 point 7).

> [!WARNING]
> **Not built yet:** no command lists issues signed by their owner. DEC-035 point 7 decides the signed listing, and #521 tracks it.

2. For each owned [Task](../../../glossary.md#term-task--task), the director reads its state in the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle), In Progress or Review, which the Task itself carries (DEC-006).

**Variants:**

- **1a.** The director lists from a clone that has set no number. The listing signs nothing, since only an [instance](../../../glossary.md#term-instance--instance) signs its listings (DEC-035 point 1). The director lists from an instance instead.

**Postconditions:** The director knows which [instance](../../../glossary.md#term-instance--instance) works on each open [issue](../../../glossary.md#term-issue--issue), and how far each owned [Task](../../../glossary.md#term-task--task) has come, without visiting any agent.

**Minimal guarantees:**

- The [owner](../../../glossary.md#term-owner--owner) shown is read from the [issue](../../../glossary.md#term-issue--issue) itself, so every [instance](../../../glossary.md#term-instance--instance) shows the same owner (DEC-043 point 4).

## Open for the design

What the director needs here that no accepted record decides yet:

- **Each instance's name in the listing,** such as `api`. DEC-045 point 1 gives a clone a name of its own, and only DEC-045 point 2's per-user file would name the other [instances](../../../glossary.md#term-instance--instance).
- **The fixers' proposals across clones.** Each clone keeps the proposals its own runs made, and `land-work` prints only that clone's count (DEC-056 point 6). So the director sees them only by visiting each agent.
- **One view of all that waits on the director,** such as heads ready to merge and records waiting for acceptance. The maintainer decided on 17 October that one view lists all of that (#1682), and no record holds the decision yet.
- **Where each agent is heading,** beside what it owns. The pilot analysis proposed a command for it, under [EPIC](../../../glossary.md#term-epic--epic) #943, and no record decides it.
