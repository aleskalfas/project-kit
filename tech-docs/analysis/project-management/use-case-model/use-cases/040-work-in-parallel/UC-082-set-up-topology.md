---
id: UC-082
title: Set up my project's topology in its committed configuration, so that every clone reads the same seats
status: active
actor: core:ACT-adopter
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
        - ACT-planning-agent
        - ACT-worker-agent
        - ACT-lead-agent
        - REQ-040
        - REQ-041
---

# UC-082 — Set up my project's topology in its committed configuration, so that every clone reads the same seats

**Goal:** Set up my project's topology in its committed configuration, so that every clone reads the same seats from the default branch.

**Other actors:**

- **Planning agent** (`ACT-planning-agent`), **Worker agent** (`ACT-worker-agent`) and **Lead agent** (`ACT-lead-agent`): each acts in a [seat](../../../glossary.md#term-seat--seat) that its own clone holds, as `UC-092` describes. The clone's number tells its work apart from the others' (DEC-035 points 1 and 2).
- **Operator** (`core:ACT-operator`): sets the number of each clone on the machine where the clone lies, since the number never leaves its clone (DEC-035 point 1).

**Preconditions:** **From UC-064:** The [project](../../../../core/glossary.md#term-project--project) declares the [workstreams](../../../glossary.md#term-workstream--workstream) its work falls into (DEC-018).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).
- Each agent of the [topology](../../../glossary.md#term-topology--topology) works in a clone of the project's repository of its own, on one machine or on a platform's sandboxes (DEC-035).

**Trigger:** The adopter decides to run several AI agents on the [project](../../../../core/glossary.md#term-project--project) at once, or to alter the [seats](../../../glossary.md#term-seat--seat) of its [topology](../../../glossary.md#term-topology--topology).

**Main path:**

1. The adopter chooses the [seats](../../../glossary.md#term-seat--seat) of the [topology](../../../glossary.md#term-topology--topology). For each seat, the adopter chooses a name and whether its agent plans, builds or does both, and may give the seat a [scope](../../../glossary.md#term-scope--scope).
2. In each agent's clone, the adopter or the operator sets the clone's number: `pkit pm set-instance <N>`. The system writes the number to a file of the clone that is never committed (DEC-035 point 1).
3. The system writes the clone's name beside the number, such as `api` (DEC-045 point 1).

> [!WARNING]
> **Not built yet:** `set-instance` takes a number alone. DEC-045 point 1 decides that an [instance](../../../glossary.md#term-instance--instance) carries a name too, and #512 tracks it.

4. The system walks the adopter through each [workstream](../../../glossary.md#term-workstream--workstream), asking which seats' scopes name it. Each scope names workstreams and changes none of them (DEC-045 points 3 and 6).

> [!WARNING]
> **Not built yet:** nothing walks the adopter through the workstreams, and no scope is written anywhere. DEC-045 point 6 decides the guided assignment, and #512 tracks it.

5. The system warns of a workstream that two scopes name, or that no scope names, and refuses neither (DEC-045 point 4).

> [!WARNING]
> **Not built yet:** nothing reads the scopes, so nothing warns. DEC-045 point 4 decides the warning, and #512 tracks it.

**Variants:**

- **2a.** A clone sets no number. It marks no [issue](../../../glossary.md#term-issue--issue) and is guarded by nothing, as before [instances](../../../glossary.md#term-instance--instance) existed (DEC-035 point 1).
- **2b.** The adopter asks a clone for its number: `pkit pm set-instance --show` prints it, or `unset` (`set-instance.py`).
- **4a.** The adopter runs the assignment again after the [workstreams](../../../glossary.md#term-workstream--workstream) changed. The system names each workstream that no [scope](../../../glossary.md#term-scope--scope) names, and each scope naming a removed workstream. It walks the adopter through them (DEC-045 point 6).

> [!WARNING]
> **Not built yet:** nothing walks the adopter through the workstreams. DEC-045 point 6 decides that the assignment runs again and reconciles the changes, and #512 tracks it.

**Postconditions:** Each clone carries its number and its name, and each [scope](../../../glossary.md#term-scope--scope) names the [workstreams](../../../glossary.md#term-workstream--workstream) its [seat](../../../glossary.md#term-seat--seat)'s agent takes work from.

**Minimal guarantees:**

- A clone that sets no number works as before [instances](../../../glossary.md#term-instance--instance) existed (DEC-035 point 1).
- A [topology](../../../glossary.md#term-topology--topology) never changes a [workstream](../../../glossary.md#term-workstream--workstream) (DEC-045 point 3).

## Open for the design

What the adopter needs here that no accepted record decides yet. The maintainer decided the design on 25 and 26 October, and a project-management record on [topologies](../../../glossary.md#term-topology--topology) is to hold it (#512).

- **Where the topology is kept, decided.** DEC-045 point 2 keeps it in one person's file, on one machine and never committed. The maintainer decided on 25 October that it is shared through the [project](../../../../core/glossary.md#term-project--project)'s committed configuration instead (#512). Every clone reads it from the [default branch](../../../../core/glossary.md#term-default-branch--default-branch).
- **What the adopter writes for each seat, decided.** On 26 October the maintainer decided that the adopter writes the topology as a set of [seats](../../../glossary.md#term-seat--seat), each with these:
  - its name
  - whether its agent plans, builds or does both, as the planning agent, a worker agent or a lead agent
  - the [agent definition](../../../../core/glossary.md#term-agent-definition--agent-definition) its agent follows, the project-manager agent's by default. An agent of another definition takes, holds and lands work by the procedure the `pm` [skill](../../../../core/glossary.md#term-skill--skill) provides
  - an optional [scope](../../../glossary.md#term-scope--scope), by discipline first, such as design or testing, and by [workstream](../../../glossary.md#term-workstream--workstream) later
  - whether it is the organizer seat, typically the planning agent's, whose clone may release other seats by force
- **A state issue for each seat, decided.** Each seat has a [state issue](../../../glossary.md#term-state-issue--state-issue) on GitHub, which comes with the topology. Its comments log each clone that takes or releases the seat, and its description shows which clone holds the seat now. That is the pattern of an [owner](../../../glossary.md#term-owner--owner)'s comment log (DEC-043 points 3 and 4). Which command creates the state issues, and when, is not decided.
- **What lives where, decided.** What a person reviews stays in the committed configuration, and what changes while agents work lives in state issues. The maintainer called the mechanism a "living state issue", for any shared data that changes at run time.
- **The guided assignment, once the topology is shared.** DEC-045 points 5 and 6 read and write the per-user file of point 2. So the topology's design may alter steps 4 and 5 and variant 4a, and where the scopes are written. The agent of a seat with no scope takes from all the project's ready Tasks, as `UC-084` describes.
- **Each clone's name and number, decided.** The maintainer decided that a clone's identity is its seat's name. The number DEC-035 uses for the tie-break and the `instance:N` label is derived from the topology, never typed. So the record to come alters steps 2 and 3.
- **More than four seats under one account.** DEC-035 point 2 gives each person a pool of four numbers, and `set-instance` takes any positive number. No record says what a topology of five seats under one account does.
- **Who may change a shared topology, and when an agent sees a change.** A committed topology reaches a clone only once that clone takes the default branch. DEC-045 calls a shared topology a larger concern, with questions of authority of its own.

## Sources

The goal rests on two decisions of the maintainer's, Aleš Kalfas. The first, on 25 October, is recorded on #512. He decided that "the agent work [topology](../../../glossary.md#term-topology--topology)" is "shared through the [project](../../../../core/glossary.md#term-project--project)'s committed pkit configuration, not kept per user on one machine". The topology there is "which agents a project runs, their <!-- pkit:not-the-term -->roles and the domains each works in".

The second came on 26 October, as he walked this use case with the project-manager agent. That decision made the topology a set of [seats](../../../glossary.md#term-seat--seat), each with a [state issue](../../../glossary.md#term-state-issue--state-issue) on GitHub.
