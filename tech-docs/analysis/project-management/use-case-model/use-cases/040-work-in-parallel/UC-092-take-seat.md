---
id: UC-092
title: Take a seat of my project's topology for my clone, and act as that seat's agent
status: active
actor: core:ACT-ai-agent
other-actors:
  - core:ACT-operator
  - core:ACT-adopter
requirements: []
after:
  - [UC-082]
shortfalls:
  - at: 1
    issue: "#2141"
    record: project-management:DEC-059#4
  - at: 2
    issue: "#2140"
    record: project-management:DEC-059#1
  - at: 3
    issue: "#2143"
    record: project-management:DEC-059#8
  - at: 5
    issue: "#2138"
    record: project-management:DEC-058#5
  - at: 6
    issue: "#2141"
    record: project-management:DEC-059#6
  - at: "1a"
    issue: "#2141"
    record: project-management:DEC-059#6
  - at: "1b"
    issue: "#2141"
    record: project-management:DEC-059#4
  - at: "2a"
    issue: "#2140"
    record: project-management:DEC-059#3
  - at: "2b"
    issue: "#2140"
    record: project-management:DEC-059#1
  - at: "3b"
    issue: "#2136"
    record: project-management:DEC-059#8
  - at: "4a"
    issue: "#2141"
    record: project-management:DEC-059#5
  - at: "4b"
    issue: "#2141"
    record: project-management:DEC-059#5
  - at: "4c"
    issue: "#2141"
    record: project-management:DEC-059#5
  - at: "5a"
    issue: "#2138"
    record: project-management:DEC-058#6
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
        - project-management:DEC-058#5
        - project-management:DEC-058#6
        - project-management:DEC-059#1
        - project-management:DEC-059#3
        - project-management:DEC-059#4
        - project-management:DEC-059#5
        - project-management:DEC-059#6
        - project-management:DEC-059#8
        - project-management:DEC-029
        - project-management:DEC-008
        - COR-013
        - COR-017
        - COR-021
---

# UC-092 — Take a seat of my project's topology for my clone, and act as that seat's agent

**Goal:** Take a seat of my project's topology for my clone, and act as that seat's agent.

**Other actors:**

- **Operator** (`core:ACT-operator`): starts the agent's session in the agent's harness, in a clone on the machine or the sandbox where the clone lies. A platform that runs agents in sandboxes may start it instead.
- **Adopter** (`core:ACT-adopter`): set up the [topology](../../../glossary.md#term-topology--topology), as `UC-082` describes, so the agent must act as the adopter set its [seat](../../../glossary.md#term-seat--seat) up. The adopter may also release a seat by force, from any clone ([DEC-059 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#5-in-the-first-mode-a-seat-stays-taken-until-it-is-released)).

**Preconditions:** **From [UC-082](UC-082-set-up-topology.md):** The [topology](../../../glossary.md#term-topology--topology) is on the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), and names the [state issue](../../../glossary.md#term-state-issue--state-issue) of each [seat](../../../glossary.md#term-seat--seat) (DEC-059 points [1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch) and [3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#3-each-seat-has-a-state-issue-which-the-topology-names)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).
- The harness hosts the agent's session in a clone of the project's repository, with the [agent definition](../../../../core/glossary.md#term-agent-definition--agent-definition) the session is started with ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md)).

**Trigger:** The operator, or a platform, starts an agent session in the agent's harness, in a clone of the [project](../../../../core/glossary.md#term-project--project).

**Main path:**

1. The agent asks the system to take a [seat](../../../glossary.md#term-seat--seat) for its clone. It names the seat where whoever started the session named one ([DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat)). Otherwise it asks for the first free seat, or the first free seat for a worker agent, the planning agent or a lead agent.

> [!WARNING]
> **Not built yet:** no command takes a seat. DEC-059 point 4 decides how a clone takes one, and #2141 tracks it.

2. The system reads the [topology](../../../glossary.md#term-topology--topology) from the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), and prints the commit it read. It takes only a free seat whose [agent definition](../../../../core/glossary.md#term-agent-definition--agent-definition) is the one the session follows (DEC-059 points [1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch) and 4).

> [!WARNING]
> **Not built yet:** nothing reads a topology. DEC-059 point 1 decides that every clone reads it from the default branch, and #2140 tracks it.

5. The system takes the seat with a comment on the seat's [state issue](../../../glossary.md#term-state-issue--state-issue). The clone generated its key when it first took a seat, and keeps the key in a file that is never committed ([DEC-035 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#1-activation-is-per-clone-and-opt-in)). The comment names these ([DEC-058 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#5-a-claim-on-a-state-issue-takes-the-shape-of-a-claim-on-a-task)):
   - the account
   - the clone's key
   - where the clone lies, such as its machine and folder

> [!WARNING]
> **Not built yet:** no command writes to a state issue, and no clone has a key. DEC-058 point 5 decides how a clone takes what a state issue holds, and #2138 tracks it.

6. The system reads the state issue again, and finds that the clone holds the seat. The first taking of a free seat holds ([DEC-058 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#6-the-first-claim-on-a-free-state-holds)). The clone is now an [instance](../../../glossary.md#term-instance--instance) named by its seat, with the seat's number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology) and [DEC-045 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#1-instances-gain-a-human-readable-name)). The system prints these:
   - the seat's name
   - the seat's number
   - the agent definition the seat names

> [!WARNING]
> **Not built yet:** a clone's identity is a number typed into it, with no name. DEC-059 point 6 decides that a clone takes its identity from its seat, and #2141 tracks it.

3. The agent follows the agent definition the seat names, the project-manager agent's by default. It reads whether the seat's agent plans, builds or does both, and runs that procedure of the `pm` [skill](../../../../core/glossary.md#term-skill--skill). The seat sets the agent's direction in place of the agent's request ([DEC-059 point 8](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#8-the-agent-a-seat-names-runs-the-seats-role-through-the-pm-skill), [DEC-029](../../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md) and [DEC-008](../../../../../../.pkit/capabilities/project-management/decisions/DEC-008-pm-and-implementer-roles.md)).

> [!WARNING]
> **Not built yet:** the project-manager agent reads its direction from its request alone, and the `pm` skill holds no procedure for a worker agent. DEC-059 point 8 decides that the agent runs its seat's procedure, and #2143 tracks it.

4. The agent goes on as the planning agent (`UC-083`), a worker agent (`UC-084`) or a lead agent (`UC-088`).

**Variants:**

- **1a.** The agent types a number into its clone: `pkit pm set-instance <N>`. In a [project](../../../../core/glossary.md#term-project--project) with a [topology](../../../glossary.md#term-topology--topology), the system refuses it, since a typed number could take a [seat](../../../glossary.md#term-seat--seat)'s number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

> [!WARNING]
> **Not built yet:** `set-instance` writes any positive number. DEC-059 point 6 decides that a project with a topology refuses a typed number, and #2141 tracks it.

- **1b.** The clone already holds a seat, which an earlier session in it took. The new session takes up that seat, since the clone's key outlives every session in it. The path goes on at step 3 ([DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat)).

> [!WARNING]
> **Not built yet:** no clone holds a seat. DEC-059 point 4 decides that a new session takes up the seat its clone holds, and #2141 tracks it.

- **1c.** No free seat matches what the agent asked for. The clone takes no seat, so it marks no [issue](../../../glossary.md#term-issue--issue) and is guarded by nothing ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)). The use case ends.
- **2a.** The topology names no [state issue](../../../glossary.md#term-state-issue--state-issue) for the seat, or the state issue cannot be read. The seat cannot be taken until a reviewed [change](../../../../core/glossary.md#term-change--change) names one ([DEC-059 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#3-each-seat-has-a-state-issue-which-the-topology-names)).

> [!WARNING]
> **Not built yet:** no topology names a state issue. DEC-059 point 3 decides that a seat without one cannot be taken, and #2140 tracks it.

- **2b.** The [default branch](../../../../core/glossary.md#term-default-branch--default-branch) cannot be resolved. The system takes no seat, and the use case ends ([DEC-059 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch)).

> [!WARNING]
> **Not built yet:** nothing reads a topology. DEC-059 point 1 decides that no clone takes a seat without the default branch, and #2140 tracks it.

- **3a.** The seat's agent plans and builds, as a lead agent does, and the request does not show which of the two the request asks for. The agent asks, and goes on once it is told (`project-manager.md`).
- **3b.** The seat names another [agent definition](../../../../core/glossary.md#term-agent-definition--agent-definition), such as a specialist's. That agent takes the seat and the seat's work, and lands that work through the same procedures of the `pm` [skill](../../../../core/glossary.md#term-skill--skill) ([DEC-059 point 8](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#8-the-agent-a-seat-names-runs-the-seats-role-through-the-pm-skill)).

> [!WARNING]
> **Not built yet:** the `pm` skill holds no procedure for an agent of another definition to follow. DEC-059 point 8 decides that every agent a seat names follows the same procedures, and #2136 tracks it.

- **4a.** The agent's work in the seat ends, and the agent releases the seat. Each issue its clone owned then counts as having no [owner](../../../glossary.md#term-owner--owner), with no write to the issue ([DEC-059 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#5-in-the-first-mode-a-seat-stays-taken-until-it-is-released)).

> [!WARNING]
> **Not built yet:** no command releases a seat. DEC-059 point 5 decides the release and what it frees, and #2141 tracks it.

- **4b.** The clone of a seat is gone for good, such as with its sandbox. The organizer seat's clone, or a person in any clone, releases the seat by force, with a reason the seat's state issue logs. A person who releases a seat by force decides the release, and no agent makes that decision for the person ([DEC-059 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#5-in-the-first-mode-a-seat-stays-taken-until-it-is-released)).

> [!WARNING]
> **Not built yet:** nothing releases a seat by force. DEC-059 point 5 decides who may, and #2141 tracks it.

- **4c.** The adopter retired the seat while the clone holds it. The clone releases the seat at its next command, as in variant 4a ([DEC-059 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#5-in-the-first-mode-a-seat-stays-taken-until-it-is-released)).

> [!WARNING]
> **Not built yet:** no seat can be retired. DEC-059 point 5 decides that a retired seat is released at its clone's next command, and #2141 tracks it.

- **5a.** Another clone took the seat first. This clone's taking counts for nothing, so the clone holds no seat, and writes nothing more ([DEC-058 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#6-the-first-claim-on-a-free-state-holds)). Its agent takes another free seat that matches what it asked for, or stops, as it judges ([DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat)).

> [!WARNING]
> **Not built yet:** nothing reads a state issue. DEC-058 point 6 decides that the first taking of a free seat holds, and #2138 tracks it.

**Postconditions:** The clone holds its [seat](../../../glossary.md#term-seat--seat), and its agent works as the [instance](../../../glossary.md#term-instance--instance) the seat names, in the direction the seat sets.

**Minimal guarantees:**

- A clone that holds no [seat](../../../glossary.md#term-seat--seat) marks no [issue](../../../glossary.md#term-issue--issue) and is guarded by nothing, as a clone with no number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).
- A clone holds at most one seat, and a seat is held by at most one clone ([DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat)).
- The clone's key never leaves the clone, so no commit carries it ([DEC-058 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#5-a-claim-on-a-state-issue-takes-the-shape-of-a-claim-on-a-task) and [DEC-035 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#1-activation-is-per-clone-and-opt-in)).
- Every command that acts as an [instance](../../../glossary.md#term-instance--instance) confirms the clone's seat on the seat's [state issue](../../../glossary.md#term-state-issue--state-issue) before it writes (DEC-059 point 6).

## Open for the design

What the agent needs here that no accepted record decides yet:

- **A seat's identity in a linked worktree.** A helper agent that a lead agent starts acts as the lead's [instance](../../../glossary.md#term-instance--instance). How a linked worktree of the clone reads that identity is left undecided by [project-management DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology). #1140 proposes that a linked worktree reads its clone's number.
- **Stricter modes.** In the first mode, the one decided, a [seat](../../../glossary.md#term-seat--seat) stays taken until it is released ([project-management DEC-059 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#5-in-the-first-mode-a-seat-stays-taken-until-it-is-released)). Modes that free a seat after its clone's silence are named, and no record decides one yet.

## Sources

The goal rests on [project-management DEC-059 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#4-a-clone-takes-a-seat-by-its-name-or-the-first-free-seat). That point holds the maintainer's decision of 26 October that a clone takes a [seat](../../../glossary.md#term-seat--seat) of the [topology](../../../glossary.md#term-topology--topology), and acts as that seat's agent.
