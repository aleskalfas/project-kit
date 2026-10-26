---
id: UC-082
title: Set up the topology my project runs, so that every agent reads the same one
status: active
actor: ACT-director
other-actors:
  - ACT-planning-agent
  - ACT-worker-agent
  - ACT-lead-agent
  - core:ACT-operator
requirements:
  - REQ-040
  - REQ-041
after:
  - [UC-064]
shortfalls:
  - at: 3
    issue: "#512"
    record: project-management:DEC-045#1
  - at: 4
    issue: "#512"
    record: project-management:DEC-045#6
  - at: 5
    issue: "#512"
    record: project-management:DEC-045#4
  - at: "4a"
    issue: "#512"
    record: project-management:DEC-045#6
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/set-instance.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
      record:
        - project-management:DEC-035#1
        - project-management:DEC-035#2
        - project-management:DEC-045#1
        - project-management:DEC-045#2
        - project-management:DEC-045#3
        - project-management:DEC-045#4
        - project-management:DEC-045#5
        - project-management:DEC-045#6
        - project-management:DEC-018
        - COR-017
        - COR-021
      artefact:
        - ACT-director
        - ACT-planning-agent
        - ACT-worker-agent
        - ACT-lead-agent
        - REQ-040
        - REQ-041
---

# UC-082 — Set up the topology my project runs, so that every agent reads the same one

**Goal:** Set up the topology my project runs, so that every agent of that topology reads the same one.

**Other actors:**

- **Planning agent** (`ACT-planning-agent`), **Worker agent** (`ACT-worker-agent`) and **Lead agent** (`ACT-lead-agent`): each works in a clone of its own. The clone's number tells its work apart from the others' (DEC-035 points 1 and 2).
- **Operator** (`core:ACT-operator`): sets the number of each clone on the machine where the clone lies, since the number never leaves its clone (DEC-035 point 1).

**Preconditions:** **From UC-064:** The [project](../../../../core/glossary.md#term-project--project) declares the [workstreams](../../../glossary.md#term-workstream--workstream) its work falls into (DEC-018).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).
- Each agent of the [topology](../../../glossary.md#term-topology--topology) works in a clone of the project's repository of its own, on one machine or on a platform's sandboxes (DEC-035).

**Trigger:** The director decides to run several agents on the [project](../../../../core/glossary.md#term-project--project) at once, or to alter which agents run.

**Main path:**

1. The director chooses the agents the [project](../../../../core/glossary.md#term-project--project) runs. For each agent, they choose a name and a [scope](../../../glossary.md#term-scope--scope). They also choose whether the agent plans, builds or does both.
2. In each agent's clone, the director or the operator sets the clone's number: `pkit pm set-instance <N>`. The system writes the number to a file of the clone that is never committed (DEC-035 point 1).
3. The system writes the agent's name beside the number, such as `api` (DEC-045 point 1).

> [!WARNING]
> **Not built yet:** `set-instance` takes a number alone. DEC-045 point 1 decides that an [instance](../../../glossary.md#term-instance--instance) carries a name too, and #512 tracks it.

4. The system walks the director through each [workstream](../../../glossary.md#term-workstream--workstream), asking which agents' scopes name it. Each scope names workstreams and changes none of them (DEC-045 points 3 and 6).

> [!WARNING]
> **Not built yet:** nothing walks the director through the workstreams, and no scope is written anywhere. DEC-045 point 6 decides the guided assignment, and #512 tracks it.

5. The system warns of a workstream that two scopes name, or that no scope names, and refuses neither (DEC-045 point 4).

> [!WARNING]
> **Not built yet:** nothing reads the scopes, so nothing warns. DEC-045 point 4 decides the warning, and #512 tracks it.

**Variants:**

- **2a.** A clone sets no number. It marks no [issue](../../../glossary.md#term-issue--issue) and is guarded by nothing, as before [instances](../../../glossary.md#term-instance--instance) existed (DEC-035 point 1).
- **2b.** The director asks a clone for its number: `pkit pm set-instance --show` prints it, or `unset` (`set-instance.py`).
- **4a.** The director runs the assignment again after the [workstreams](../../../glossary.md#term-workstream--workstream) changed. The system names each workstream that no [scope](../../../glossary.md#term-scope--scope) names, and each scope naming a removed workstream. It walks the director through them (DEC-045 point 6).

> [!WARNING]
> **Not built yet:** nothing walks the director through the workstreams. DEC-045 point 6 decides that the assignment runs again and reconciles the changes, and #512 tracks it.

**Postconditions:** Each agent's clone carries its number and its name, and each agent's [scope](../../../glossary.md#term-scope--scope) names the [workstreams](../../../glossary.md#term-workstream--workstream) it takes work from.

**Minimal guarantees:**

- A clone that sets no number works as before [instances](../../../glossary.md#term-instance--instance) existed (DEC-035 point 1).
- A [topology](../../../glossary.md#term-topology--topology) never changes a [workstream](../../../glossary.md#term-workstream--workstream) (DEC-045 point 3).

## Open for the design

What the director needs here that no accepted record decides yet:

- **Where the topology is kept.** DEC-045 point 2 keeps it in one person's file, on one machine and never committed. The maintainer decided on 25 October that it is shared through the [project](../../../../core/glossary.md#term-project--project)'s committed configuration instead (#512). The record changes with the [topology](../../../glossary.md#term-topology--topology)'s design.
- **The guided assignment, once the topology is shared.** DEC-045 points 5 and 6 read and write the per-user file of point 2. So the topology's design may alter steps 4 and 5 and variant 4a, and where the scopes are written.
- **How the topology records what each agent does:** plans, builds or both. This analysis reads the agents' <!-- pkit:not-the-term -->roles that #512 names as planning, building or both, after the actors #2096 lists.
- **Who may change a shared topology, and when an agent sees a change.** A committed topology reaches a clone only once that clone takes the [default branch](../../../../core/glossary.md#term-default-branch--default-branch). DEC-045 calls a shared topology a larger concern, with questions of authority of its own.
- **More than four agents under one account.** DEC-035 point 2 gives each person a pool of four numbers, and `set-instance` takes any positive number. No record says what a topology of five agents under one account does.
- **How an agent learns its place.** No record decides how an agent that starts in a clone learns its name and its [scope](../../../glossary.md#term-scope--scope). Nor does one decide how the agent learns whether it plans, builds or does both.
- **A scope by stage of the work,** such as design, development or testing. No record decides how a scope names a stage, since [workstreams](../../../glossary.md#term-workstream--workstream) are long-lived areas and no stage (DEC-018).

## Sources

The goal rests on a decision of the maintainer's, recorded on #512 on 25 October. The maintainer decided that "the agent work [topology](../../../glossary.md#term-topology--topology)" is "shared through the [project](../../../../core/glossary.md#term-project--project)'s committed pkit configuration, not kept per user on one machine". The topology there is "which agents a project runs, their <!-- pkit:not-the-term -->roles and the domains each works in".
