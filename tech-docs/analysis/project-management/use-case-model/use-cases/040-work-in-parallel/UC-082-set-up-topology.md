---
id: UC-082
title: Set up my project's topology in the project's committed configuration, so that every clone reads the same seats
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
  - at: 4
    issue: "#512"
    record: project-management:DEC-045#6
  - at: 5
    issue: "#2136"
    record: project-management:DEC-059#7
  - at: "4a"
    issue: "#512"
    record: project-management:DEC-045#6
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/set-instance.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
        - .pkit/capabilities/project-management/scripts/_lib/topology.py
        - .pkit/capabilities/project-management/scripts/create-seats.py
        - .pkit/capabilities/project-management/scripts/check-topology.py
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

# UC-082 — Set up my project's topology in the project's committed configuration, so that every clone reads the same seats

**Goal:** Set up my project's topology in the project's committed configuration, so that every clone reads the same seats from the default branch.

**Other actors:**

- **Planning agent** (`ACT-planning-agent`), **Worker agent** (`ACT-worker-agent`) and **Lead agent** (`ACT-lead-agent`): each agent acts in a [seat](../../../glossary.md#term-seat--seat) that the agent's own clone holds, as `UC-092` describes. The seat's number tells the agent's work apart from the other agents' work ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).
- **Operator** (`core:ACT-operator`): is asked before a command changes a repository other than the session's own, so no such write happens silently ([core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-064](../010-plan/UC-064-define-milestones-and-workstreams.md):** The [project](../../../../core/glossary.md#term-project--project) declares the [workstreams](../../../glossary.md#term-workstream--workstream) its work falls into ([DEC-018](../../../../../../.pkit/capabilities/project-management/decisions/DEC-018-workstream-taxonomy-and-lifecycle.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and the commands of `pkit pm` ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).
- Each agent of the [topology](../../../glossary.md#term-topology--topology) works in the agent's own clone of the project's repository, on one machine or on a platform's sandboxes ([DEC-059](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md)).
- The backbone resolves the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), the project's settled state, in one way for every command ([COR-054](../../../../../../.pkit/decisions/core/COR-054-default-branch.md)).

**Trigger:** The adopter decides to run several AI agents on the [project](../../../../core/glossary.md#term-project--project) at once, or to alter the [seats](../../../glossary.md#term-seat--seat) of the project's [topology](../../../glossary.md#term-topology--topology).

**Main path:**

1. The adopter chooses the [seats](../../../glossary.md#term-seat--seat) of the [topology](../../../glossary.md#term-topology--topology), and writes the seats into the [project](../../../../core/glossary.md#term-project--project)'s configuration for project-management, `project/topology.yaml`, on a branch. Each seat says whether the seat is the organizer seat, and may give the seat's agent a [scope](../../../glossary.md#term-scope--scope) (DEC-059 points [1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch) and [2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#2-a-seat-has-a-name-a-role-an-agent-and-an-optional-scope)). Each seat also holds these:
   - the seat's name
   - whether the seat's agent plans, builds or does both
   - the [agent definition](../../../../core/glossary.md#term-agent-definition--agent-definition) that agent follows

2. The system derives each seat's number from the seat's place in the topology's list, counted from one. Nobody types a number into a clone, so no two clones take one number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

3. A clone that holds a seat takes the seat's name, so nobody types a name either ([DEC-045 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#1-instances-gain-a-human-readable-name) and DEC-059 point 6).

4. The system walks the adopter through each [workstream](../../../glossary.md#term-workstream--workstream), asking which seats' scopes name the workstream. Each scope names workstreams and changes none of the workstreams (DEC-045 points [3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#3-instances-reference-workstreams-1many-they-never-rebind-the-taxonomy) and [6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#6-a-guided-assignment-script--local-idempotent-drift-reconciling)). The system writes the scopes into the topology, for a [change](../../../../core/glossary.md#term-change--change) a person reviews ([DEC-059](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md)).

> [!WARNING]
> **Not built yet:** nothing walks the adopter through the workstreams, or writes the scopes into the topology. DEC-045 point 6 decides the guided assignment, and #512 tracks it.

5. The system warns of a workstream that no seat may take, and refuses nothing. Several seats that may take one workstream draw no warning, since those seats share the ready Tasks ([DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool)).

> [!WARNING]
> **Not built yet:** nothing warns of a workstream that no seat may take. DEC-059 point 7 decides the warning, and #2136 tracks it.

6. The adopter runs `pkit pm create-seats`, the command that creates the [state issue](../../../glossary.md#term-state-issue--state-issue) of each new seat, on the change that adds the seats. The system creates a state issue for each new seat, keyed by the seat's name ([DEC-058 point 2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#2-a-state-issue-holds-one-piece-of-state-named-by-its-key)). The system writes each state issue's number into the topology ([DEC-059 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#3-each-seat-has-a-state-issue-which-the-topology-names)). At the command's entry, the system checks the project's prerequisites, and that the repository is the session's own ([REQ-041](../../../requirements/functional/REQ-041-gates-before-writing.md) and [core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

7. The adopter runs the topology's check, `pkit pm check-topology`, on the change. The check compares the change's topology with the topology of the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), and says which commit the check read. The check reports each of these (DEC-059):
   - a seat's name held twice
   - more than one organizer seat
   - a seat whose state issue is not named
   - a scope that names an unknown workstream or kind of work
   - a seat deleted or moved against the default branch, rather than retired

8. A person reviews the change, and the change merges like any other. The topology binds once the topology is on the default branch. Every clone reads the topology from there, never from the clone's own branch or working tree (DEC-059 point 1).

**Variants:**

- **1a.** The adopter alters a [topology](../../../glossary.md#term-topology--topology) already in place. A new [seat](../../../glossary.md#term-seat--seat) goes at the end of the list, and a seat that leaves stays in the list, marked retired. Renaming a seat retires the seat and adds a new seat, so no seat's number moves (DEC-059 points [2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#2-a-seat-has-a-name-a-role-an-agent-and-an-optional-scope) and [6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)). The topology's check of step 7 reports a seat deleted or moved against the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), rather than retired.

- **2a.** A clone holds no seat. The clone marks no [issue](../../../glossary.md#term-issue--issue) and is guarded by nothing, as a clone with no number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).
- **2b.** The adopter asks a clone for the clone's number: `pkit pm set-instance --show` prints the number, or `unset` (`set-instance.py`).
- **2c.** The operator types a number into a clone: `pkit pm set-instance <N>`. In a [project](../../../../core/glossary.md#term-project--project) with a topology, the system refuses the number, since a typed number could take a seat's number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).

- **4a.** The adopter runs the assignment again after the [workstreams](../../../glossary.md#term-workstream--workstream) changed. The system names each workstream that no seat may take, and each [scope](../../../glossary.md#term-scope--scope) naming a removed workstream. The system walks the adopter through those workstreams and scopes. The system then writes the scopes into the topology, for a reviewed [change](../../../../core/glossary.md#term-change--change) ([DEC-045 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#6-a-guided-assignment-script--local-idempotent-drift-reconciling) and [DEC-059](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md)).

> [!WARNING]
> **Not built yet:** nothing walks the adopter through the workstreams. DEC-045 point 6 decides that the assignment runs again and reconciles the changes, and #512 tracks it.

- **6a.** The change that adds seats is closed unmerged. No seat names the change's [state issues](../../../glossary.md#term-state-issue--state-issue). The listing of the seats, `pkit pm seats`, names those state issues for a person to close ([DEC-059 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#3-each-seat-has-a-state-issue-which-the-topology-names)).

- **7a.** The project writes the [owner](../../../glossary.md#term-owner--owner) of each issue as a label. The topology's check refuses the topology, since a label cannot carry what an ownership names ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again) and [DEC-043 point 2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-043-ownership-substrate-selection.md#2-a-selector-in-instance-ownerships-own-schema-home)).

- **8a.** A clone has not fetched the default branch since the change merged. The clone reads the topology the clone last fetched. The commands that take and list seats say which commit the clone read ([DEC-059 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch)).

**Postconditions:** The [topology](../../../glossary.md#term-topology--topology) on the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) declares each [seat](../../../glossary.md#term-seat--seat), with the seat's number, [state issue](../../../glossary.md#term-state-issue--state-issue) and [scope](../../../glossary.md#term-scope--scope), where the seat has a scope. Each scope names the [workstreams](../../../glossary.md#term-workstream--workstream) or the kinds of work that the agent of the scope's seat takes work from.

**Minimal guarantees:**

- A clone that holds no [seat](../../../glossary.md#term-seat--seat) works as a clone with no number ([DEC-059 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#6-a-clones-identity-is-its-seats-name-and-its-number-comes-from-the-topology)).
- A [topology](../../../glossary.md#term-topology--topology) never changes a [workstream](../../../glossary.md#term-workstream--workstream) ([DEC-045 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#3-instances-reference-workstreams-1many-they-never-rebind-the-taxonomy)).
- The topology never says which clone holds a seat. Only the seat's [state issue](../../../glossary.md#term-state-issue--state-issue) shows the holder ([DEC-058 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md#1-what-a-person-reviews-is-configuration-and-what-changes-at-run-time-is-a-state-issue)).
- A topology on a branch binds no clone, since every clone reads the topology from the [default branch](../../../../core/glossary.md#term-default-branch--default-branch) ([DEC-059 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch)).

## Open for the design

What the adopter needs here that no accepted record decides yet:

- **A scope by a discipline that no kind of work carries,** such as design. [DEC-059 point 7](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) leaves such a [scope](../../../glossary.md#term-scope--scope) to a record that decides how a [Task](../../../glossary.md#term-task--task) carries such a discipline.

## Sources

The goal rests on [project-management DEC-059 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch). That point holds the maintainer's decision of 25 October, recorded on #512. He decided that "the agent work [topology](../../../glossary.md#term-topology--topology)" is "shared through the [project](../../../../core/glossary.md#term-project--project)'s committed pkit configuration, not kept per user on one machine".
