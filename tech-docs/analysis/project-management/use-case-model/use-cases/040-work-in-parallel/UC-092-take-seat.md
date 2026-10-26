---
id: UC-092
title: Take a seat of my project's topology, and act as that seat's agent
status: active
actor: core:ACT-ai-agent
other-actors:
  - core:ACT-operator
  - core:ACT-adopter
requirements: []
after:
  - [UC-082]
shortfalls:
  - at: 2
    issue: "#512"
    record: project-management:DEC-045#1
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/set-instance.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
        - .pkit/capabilities/project-management/agents/project-manager/project-manager.md
      record:
        - project-management:DEC-035#1
        - project-management:DEC-045#1
        - project-management:DEC-029
        - project-management:DEC-008
        - COR-013
        - COR-017
        - COR-021
---

# UC-092 — Take a seat of my project's topology, and act as that seat's agent

**Goal:** Take a seat of my project's topology, and act as that seat's agent.

**Other actors:**

- **Operator** (`core:ACT-operator`): starts the agent's session in its harness, in a clone on the machine or the sandbox where the clone lies. A platform that runs agents in sandboxes may start it instead.
- **Adopter** (`core:ACT-adopter`): set up the [topology](../../../glossary.md#term-topology--topology), as `UC-082` describes, so the agent must act as the adopter set its [seat](../../../glossary.md#term-seat--seat) up.

**Preconditions:** **From UC-082:** The [topology](../../../glossary.md#term-topology--topology) is set up (DEC-045).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).
- The harness hosts the agent's session in a clone of the project's repository, with the [agent definition](../../../../core/glossary.md#term-agent-definition--agent-definition) the session is started with (COR-013).

**Trigger:** The operator, or a platform, starts an agent session in its harness, in a clone of the [project](../../../../core/glossary.md#term-project--project).

**Main path:**

1. The agent reads which [instance](../../../glossary.md#term-instance--instance) its clone is: `pkit pm set-instance --show` prints the clone's number (DEC-035 point 1).
2. The system prints the clone's name beside its number, such as `api` (DEC-045 point 1).

> [!WARNING]
> **Not built yet:** `set-instance` keeps a number alone, so `--show` prints no name. DEC-045 point 1 decides that an instance carries a name too, and #512 tracks it.

3. The agent follows the project-manager agent's definition. It reads from its request, or from the session's configuration, whether a planner or a developer directs it (DEC-008 and DEC-029).
4. The agent goes on as the planning agent (`UC-083`), a worker agent (`UC-084`) or a lead agent (`UC-088`).

**Variants:**

- **1a.** The clone has no number yet, and `--show` prints `unset`. The agent sets one: `pkit pm set-instance <N>`. The system writes it to a file of the clone that is never committed, and the path goes on at step 2 (DEC-035 point 1).
- **3a.** The request does not show who directs the agent. The agent asks, and goes on once it is told (`project-manager.md`).

**Postconditions:** The agent works as its clone's [instance](../../../glossary.md#term-instance--instance), on the direction its request gives.

**Minimal guarantees:**

- A clone that sets no number works as before [instances](../../../glossary.md#term-instance--instance) existed (DEC-035 point 1).
- The clone's number never leaves the clone, so no commit carries it (DEC-035 point 1).

## Open for the design

What the agent needs here that no accepted record decides yet. The maintainer decided the design on 26 October, walking `UC-082` with the project-manager agent. A project-management record on [topologies](../../../glossary.md#term-topology--topology) is to hold it, refining DEC-035 point 1 and DEC-045 points 1 and 2 (#512).

- **Which seat the clone takes, decided.** It takes the [seat](../../../glossary.md#term-seat--seat) it is given by name, such as `take-seat api-worker`. Otherwise it takes the first free seat, or the first free seat whose agent does the work asked for, such as `take-seat --role worker`.
- **How the clone takes it, decided.** Taking a seat works as taking a [Task](../../../glossary.md#term-task--task): the clone writes itself on the seat's [state issue](../../../glossary.md#term-state-issue--state-issue). Two clones may reach for one free seat at the same instant. Neither has a number yet to break the tie with, and how that tie is broken is not decided.
- **The clone's identity, decided.** It is its seat's name. The number DEC-035 uses for the tie-break and the `instance:N` label is derived from the topology, never typed. So the record to come alters steps 1 and 2 and variant 1a.
- **The agent the seat names, decided.** By default it is the project-manager agent, which reads from the seat whether it plans, builds or does both, and runs the procedure for that. A seat may name another agent, which takes, holds and lands work by the procedure the `pm` [skill](../../../../core/glossary.md#term-skill--skill) provides. So the record to come alters step 3.
- **How long the seat stays taken, decided.** In the first and most tolerant mode, the seat stays taken until its clone releases it. Otherwise only a release by force frees it, from the organizer seat's clone or by the adopter from any clone. The seat's state issue logs each release by force, and no seat is freed for its clone's silence in that mode. How sensitive a seat is to that silence is set in later modes.

## Sources

The goal rests on a decision of the maintainer's, Aleš Kalfas, on 26 October. Walking `UC-082` with the project-manager agent, he decided that a clone takes a [seat](../../../glossary.md#term-seat--seat) of the [topology](../../../glossary.md#term-topology--topology), and then acts as that seat's agent. He decided too that which clone holds each seat is kept on GitHub, on the seat's own [state issue](../../../glossary.md#term-state-issue--state-issue), and never committed.
