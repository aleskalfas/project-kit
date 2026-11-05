---
id: REQ-062
title: An instance's work in flight is found again only from GitHub, the instance's number and, under a topology, the clone key
status: active
statement: "The issues an instance owns, and each issue's branch, are found only from GitHub, the instance's number and, under a topology, the clone key."
measure: "After every earlier session died, a new session in the instance lists the issues the instance owns, and finds each one's branch."
applies-to: "Every instance, whichever way the project writes the owner of an issue."
obligation: v1:sha256:30df0c31183829b2f49c50b538058faa7eef0943da85ccbc4dc0b3ae3cde9943
actors:
  - ACT-worker-agent
  - ACT-lead-agent
  - ACT-planner
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
      record:
        - project-management:DEC-035
        - project-management:DEC-035#1
        - project-management:DEC-035#7
        - project-management:DEC-043#4
        - project-management:DEC-059#9
        - project-management:DEC-013
      artefact:
        - ACT-worker-agent
        - ACT-lead-agent
        - ACT-planner
---

# REQ-062 · Functional · An instance's work in flight is found again only from GitHub, the instance's number and, under a topology, the clone key

**Verified by:** None.

**Rationale:** [Clones](../../../glossary.md#term-clone--clone) coordinate through GitHub, so with no [topology](../../../glossary.md#term-topology--topology) the only state the clones keep is each clone's number and the [ownerships](../../../glossary.md#term-ownership--ownership) on the issues ([DEC-035](../../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md)). Under a topology, each clone also keeps a [clone key](../../../glossary.md#term-clone-key--clone-key). There, an ownership names that key, and counts only while the key's clone holds the ownership's [seat](../../../glossary.md#term-seat--seat) ([DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)).

[EPIC](../../../glossary.md#term-epic--epic) #943 sets the outcome this requirement serves: with every session killed, each clone finds where the clone was from GitHub and the clone's number. The [owner](../../../glossary.md#term-owner--owner) is written on the [issue](../../../glossary.md#term-issue--issue) itself, so the owner survives a session that died ([DEC-043 point 4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-043-ownership-substrate-selection.md#4-the-current-owner-is-mirrored-into-the-issue-description-as-a-derived-regenerable-view)). Each [Task](../../../glossary.md#term-task--task)'s branch is named after the Task, so the branch is found from the issue ([DEC-013](../../../../../../.pkit/capabilities/project-management/decisions/DEC-013-branch-and-pr-conventions.md)).

## Open for the design

Where the work was heading beyond the work's branch is decided by no record yet, as `UC-086` says. #2096 asks that an agent's direction be found from GitHub alone. This requirement holds what the records decide: what an [instance](../../../glossary.md#term-instance--instance) owns, and each [Task](../../../glossary.md#term-task--task)'s branch.
