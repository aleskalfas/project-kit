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
        - ACT-planner
        - REQ-062
---

# UC-090 — See which agent works on which issue, without visiting each agent

**Goal:** See which agent works on which issue, without visiting each agent.

**Other actors:** None.

**Preconditions:** **From UC-082, or UC-092:** Each agent's clone has its number (DEC-035 point 1).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).

**Trigger:** The planner wants the whole picture, such as after a restart, or before planning more work for the [topology](../../../glossary.md#term-topology--topology)'s agents.

**Main path:**

1. In any [instance](../../../glossary.md#term-instance--instance), the planner lists the open issues, each signed with its [owner](../../../glossary.md#term-owner--owner): this instance, another instance, or none (DEC-035 point 7).

> [!WARNING]
> **Not built yet:** no command lists issues signed by their owner. DEC-035 point 7 decides the signed listing, and #521 tracks it.

2. For each owned [Task](../../../glossary.md#term-task--task), the planner reads its state in the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle), In Progress or Review, which the Task itself carries (DEC-006).

**Variants:**

- **1a.** The planner lists from a clone that has set no number. The listing signs nothing, since only an [instance](../../../glossary.md#term-instance--instance) signs its listings (DEC-035 point 1). The planner lists from an instance instead.

**Postconditions:** The planner knows which [instance](../../../glossary.md#term-instance--instance) works on each open [issue](../../../glossary.md#term-issue--issue), and how far each owned [Task](../../../glossary.md#term-task--task) has come, without visiting any agent.

**Minimal guarantees:**

- The [owner](../../../glossary.md#term-owner--owner) shown is read from the [issue](../../../glossary.md#term-issue--issue) itself, so every [instance](../../../glossary.md#term-instance--instance) shows the same owner (DEC-043 point 4).

## Open for the design

What the planner needs here that no accepted record decides yet:

- **Each owner's seat in the listing, decided.** DEC-045 point 1 gives a clone a name of its own, and only DEC-045 point 2's per-user file would name the other [instances](../../../glossary.md#term-instance--instance). The maintainer decided on 26 October that a clone's identity is its [seat](../../../glossary.md#term-seat--seat)'s name, such as `api-worker`. So the listing can name each [owner](../../../glossary.md#term-owner--owner) by its seat, once a project-management record on [topologies](../../../glossary.md#term-topology--topology) holds it (#512).
- **Which clone holds which seat, decided.** Each seat's [state issue](../../../glossary.md#term-state-issue--state-issue) shows the clone that holds it, and logs each clone that took or released it (`UC-082`). So the planner sees the seats on GitHub, without visiting any agent. The maintainer decided it on 26 October, and no record holds it yet.
- **The fixers' proposals across clones.** Each clone keeps the proposals its own runs made, and `land-work` prints only that clone's count (DEC-056 point 6). So the planner sees them only by visiting each agent.
- **One view of all that waits on a person,** such as heads ready to merge and records waiting for acceptance. The maintainer decided on 17 October that one view lists all of that (#1682), and no record holds the decision yet.
- **Where each agent is heading,** beside what it owns. The pilot analysis proposed a command for it, under [EPIC](../../../glossary.md#term-epic--epic) #943, and no record decides it.
