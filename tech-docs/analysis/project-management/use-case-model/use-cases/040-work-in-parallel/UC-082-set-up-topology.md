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
  - at: 1
    issue: "#2140"
    record: project-management:DEC-059#2
  - at: 2
    issue: "#2141"
    record: project-management:DEC-059#6
  - at: 3
    issue: "#2141"
    record: project-management:DEC-045#1
  - at: 4
    issue: "#512"
    record: project-management:DEC-045#6
  - at: 5
    issue: "#2136"
    record: project-management:DEC-059#7
  - at: 6
    issue: "#2140"
    record: project-management:DEC-059#3
  - at: 7
    issue: "#2140"
    record: project-management:DEC-059
  - at: 8
    issue: "#2140"
    record: project-management:DEC-059#1
  - at: "1a"
    issue: "#2140"
    record: project-management:DEC-059#6
  - at: "2c"
    issue: "#2141"
    record: project-management:DEC-059#6
  - at: "4a"
    issue: "#512"
    record: project-management:DEC-045#6
  - at: "6a"
    issue: "#2141"
    record: project-management:DEC-059#3
  - at: "7a"
    issue: "#2140"
    record: project-management:DEC-059#9
  - at: "8a"
    issue: "#2140"
    record: project-management:DEC-059#1
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/set-instance.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
      record:
        - project-management:DEC-045#1
        - project-management:DEC-045#3
        - project-management:DEC-045#6
        - project-management:DEC-058#1
        - project-management:DEC-058#2
        - project-management:DEC-059
        - project-management:DEC-059#1
        - project-management:DEC-059#2
        - project-management:DEC-059#3
        - project-management:DEC-059#6
        - project-management:DEC-059#7
        - project-management:DEC-059#9
        - project-management:DEC-043#2
        - project-management:DEC-018
        - COR-017
        - COR-021
        - COR-054
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

- **Planning agent** (`ACT-planning-agent`), **Worker agent** (`ACT-worker-agent`) and **Lead agent** (`ACT-lead-agent`): each acts in a [seat](../../../glossary.md#term-seat--seat) that its own clone holds, as `UC-092` describes. The seat's number tells its work apart from the others' ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).
- **Operator** (`core:ACT-operator`): is asked before a command changes a repository other than the session's own, so no such write happens silently (core:REQ-012).

**Preconditions:** **From UC-064:** The [project](../../../../core/glossary.md#term-project--project) declares the [workstreams](../../../glossary.md#term-workstream--workstream) its work falls into ([DEC-018](../../../../../../.pkit/capabilities/project-management/decisions/DEC-018-workstream-taxonomy-and-lifecycle.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).
- Each agent of the [topology](../../../glossary.md#term-topology--topology) works in a clone of the project's repository of its own, on one machine or on a platform's sandboxes ([DEC-059](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md)).
- The backbone resolves the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), the project's settled state, in one way for every command ([COR-054](../../../../../../.pkit/decisions/core/COR-054-default-branch.md)).

**Trigger:** The adopter decides to run several AI agents on the [project](../../../../core/glossary.md#term-project--project) at once, or to alter the [seats](../../../glossary.md#term-seat--seat) of its [topology](../../../glossary.md#term-topology--topology).

**Main path:**

1. The adopter chooses the [seats](../../../glossary.md#term-seat--seat) of the [topology](../../../glossary.md#term-topology--topology), and writes them into the [project](../../../../core/glossary.md#term-project--project)'s configuration for project-management, on a branch. Each seat holds its name, whether its agent plans, builds or does both, and the [agent definition](../../../../core/glossary.md#term-agent-definition--agent-definition) that agent follows. Each seat also says whether it is the organizer seat, and may give its agent a [scope](../../../glossary.md#term-scope--scope) (DEC-059 points [1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch) and [2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#2-a-seat-has-a-name-a-role-an-agent-and-an-optional-scope)).

> [!WARNING]
> **Not built yet:** no configuration of project-management holds a topology. DEC-059 point 2 decides what each seat declares, and #2140 tracks it.

2. The system derives each seat's number from the seat's place in the topology's list, counted from one. Nobody types a number into a clone, so no two clones take one number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

> [!WARNING]
> **Not built yet:** each clone's number is typed into it, with `pkit pm set-instance <N>`. DEC-059 point 6 decides that a seat's number is its place in the topology, and #2141 tracks it.

3. A clone that holds a seat takes the seat's name, so nobody types a name either ([DEC-045 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#1-instances-gain-a-human-readable-name) and DEC-059 point 6).

> [!WARNING]
> **Not built yet:** `set-instance` takes a number alone, and no clone carries a name. DEC-045 point 1 decides that a clone's name is the name of its seat, and #2141 tracks it.

4. The system walks the adopter through each [workstream](../../../glossary.md#term-workstream--workstream), asking which seats' scopes name it. Each scope names workstreams and changes none of them (DEC-045 points [3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#3-instances-reference-workstreams-1many-they-never-rebind-the-taxonomy) and [6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#6-a-guided-assignment-script--local-idempotent-drift-reconciling)). The system writes the scopes into the topology, for a [change](../../../../core/glossary.md#term-change--change) a person reviews ([DEC-059](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md)).

> [!WARNING]
> **Not built yet:** nothing walks the adopter through the workstreams, and no topology holds a scope. DEC-045 point 6 decides the guided assignment, and #512 tracks it.

5. The system warns of a workstream that no seat may take, and refuses nothing. Several seats that may take one workstream draw no warning, since they share the ready Tasks ([DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool)).

> [!WARNING]
> **Not built yet:** nothing reads the seats' scopes, so nothing warns. DEC-059 point 7 decides the warning, and #2136 tracks it.

6. The adopter runs the command that creates the [state issue](../../../glossary.md#term-state-issue--state-issue) of each new seat, on the change that adds the seats. The system creates a state issue for each new seat, keyed by the seat's name ([DEC-058 point 2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#2-a-state-issue-holds-one-piece-of-state-named-by-its-key)). It writes each state issue's number into the topology ([DEC-059 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#3-each-seat-has-a-state-issue-which-the-topology-names)). At the command's entry, the system checks the project's prerequisites, and that the repository is the session's own (REQ-041 and core:REQ-012).

> [!WARNING]
> **Not built yet:** no command creates a state issue. DEC-059 point 3 decides that the change adding seats lands with their state issues, and #2140 tracks it.

7. The system checks the topology (DEC-059). It reports a seat's name held twice, and more than one organizer seat. It reports too a seat whose state issue is not named, and a scope that names an unknown workstream or kind of work. It also reports a seat deleted or moved against the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), rather than retired.

> [!WARNING]
> **Not built yet:** no check reads a topology. DEC-059 decides what the topology's check reports, and #2140 tracks it.

8. A person reviews the change, and the change merges like any other. The topology binds once it is on the default branch. Every clone reads it from there, never from the clone's own branch or working tree (DEC-059 point 1).

> [!WARNING]
> **Not built yet:** nothing reads a topology. DEC-059 point 1 decides that every clone reads it from the default branch, and #2140 tracks it.

**Variants:**

- **1a.** The adopter alters a [topology](../../../glossary.md#term-topology--topology) already in place. A new [seat](../../../glossary.md#term-seat--seat) goes at the end of the list, and a seat that leaves stays in the list, marked retired. Renaming a seat retires it and adds a new one, so no seat's number moves (DEC-059 points [2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#2-a-seat-has-a-name-a-role-an-agent-and-an-optional-scope) and [6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

> [!WARNING]
> **Not built yet:** no topology exists to alter. DEC-059 point 6 decides that seats are only added and retired, and #2140 tracks it.

- **2a.** A clone holds no seat. It marks no [issue](../../../glossary.md#term-issue--issue) and is guarded by nothing, as a clone with no number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).
- **2b.** The adopter asks a clone for its number: `pkit pm set-instance --show` prints it, or `unset` (`set-instance.py`).
- **2c.** The operator types a number into a clone: `pkit pm set-instance <N>`. In a [project](../../../../core/glossary.md#term-project--project) with a topology, the system refuses it, since a typed number could take a seat's number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

> [!WARNING]
> **Not built yet:** `set-instance` writes any positive number. DEC-059 point 6 decides that a project with a topology refuses a typed number, and #2141 tracks it.

- **4a.** The adopter runs the assignment again after the [workstreams](../../../glossary.md#term-workstream--workstream) changed. The system names each workstream that no seat may take, and each [scope](../../../glossary.md#term-scope--scope) naming a removed workstream. It walks the adopter through them, and writes the scopes into the topology, for a reviewed [change](../../../../core/glossary.md#term-change--change) ([DEC-045 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#6-a-guided-assignment-script--local-idempotent-drift-reconciling) and [DEC-059](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md)).

> [!WARNING]
> **Not built yet:** nothing walks the adopter through the workstreams. DEC-045 point 6 decides that the assignment runs again and reconciles the changes, and #512 tracks it.

- **6a.** The change that adds seats is closed unmerged. Its [state issues](../../../glossary.md#term-state-issue--state-issue) are named by no seat, and the listing of the seats names them for a person to close ([DEC-059 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#3-each-seat-has-a-state-issue-which-the-topology-names)).

> [!WARNING]
> **Not built yet:** no command lists the seats. DEC-059 point 3 decides that the listing names each state issue no seat names, and #2141 tracks it.

- **7a.** The project writes the [owner](../../../glossary.md#term-owner--owner) of each issue as a label. The topology's check refuses the topology, since a label cannot carry what an ownership names ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again) and [DEC-043 point 2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-043-ownership-substrate-selection.md#2-a-selector-in-instance-ownerships-own-schema-home)).

> [!WARNING]
> **Not built yet:** no check reads a topology. DEC-059 point 9 decides that a topology keeps its owners in the log of comments, and #2140 tracks it.

- **8a.** A clone has not fetched the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) since the change merged. It reads the topology it last fetched, and says which commit it read ([DEC-059 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch)).

> [!WARNING]
> **Not built yet:** nothing reads a topology, nor names the commit read. DEC-059 point 1 decides that a clone names the commit it read, and #2140 tracks it.

**Postconditions:** The [topology](../../../glossary.md#term-topology--topology) on the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) declares each [seat](../../../glossary.md#term-seat--seat), with its number and its [state issue](../../../glossary.md#term-state-issue--state-issue), and the [scope](../../../glossary.md#term-scope--scope) of each seat that has one. Each scope names the [workstreams](../../../glossary.md#term-workstream--workstream) or the kinds of work its seat's agent takes work from.

**Minimal guarantees:**

- A clone that holds no [seat](../../../glossary.md#term-seat--seat) works as a clone with no number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).
- A [topology](../../../glossary.md#term-topology--topology) never changes a [workstream](../../../glossary.md#term-workstream--workstream) ([DEC-045 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#3-instances-reference-workstreams-1many-they-never-rebind-the-taxonomy)).
- The topology never says which clone holds a seat, which the seat's [state issue](../../../glossary.md#term-state-issue--state-issue) alone shows ([DEC-058 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#1-what-a-person-reviews-is-configuration-and-what-changes-at-run-time-is-a-state-issue)).
- A topology on a branch binds no clone, since every clone reads the topology from the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) ([DEC-059 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch)).

## Open for the design

What the adopter needs here that no accepted record decides yet:

- **A scope by a discipline that no kind of work carries,** such as design. [DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) leaves it to a record that decides how a [Task](../../../glossary.md#term-task--task) carries such a discipline.

## Sources

The goal rests on [project-management DEC-059 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch). It holds the maintainer's decision of 25 October, recorded on #512. He decided that "the agent work [topology](../../../glossary.md#term-topology--topology)" is "shared through the [project](../../../../core/glossary.md#term-project--project)'s committed pkit configuration, not kept per user on one machine".
