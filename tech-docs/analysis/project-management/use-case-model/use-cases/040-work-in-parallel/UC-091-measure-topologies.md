---
id: UC-091
title: Measure one topology against another on comparable work
status: active
actor: core:ACT-adopter
other-actors: []
requirements: []
after:
  - [UC-082]
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py
        - .pkit/capabilities/project-management/scripts/_lib/audit.py
      record:
        - project-management:DEC-028
        - project-management:DEC-049#2
        - project-management:DEC-003
        - project-management:DEC-059#9
---

# UC-091 — Measure one topology against another on comparable work

**Goal:** Measure one topology against another on comparable work, by figures GitHub holds.

**Other actors:** None.

**Preconditions:** **From [UC-082](UC-082-set-up-topology.md):** Each [topology](../../../glossary.md#term-topology--topology) to compare is set up.

**Assumptions:**

- GitHub keeps, for each [pull request](../../../../core/glossary.md#term-pull-request--pull-request), when the pull request opened and when the pull request merged ([DEC-003](../../../../../../.pkit/capabilities/project-management/decisions/DEC-003-github-bound-substrate.md)).

**Trigger:** The adopter wants to know which [topology](../../../glossary.md#term-topology--topology) serves the [project](../../../../core/glossary.md#term-project--project) better.

**Main path:**

1. The adopter has each [topology](../../../glossary.md#term-topology--topology) work on comparable work, until all of that work has landed.
2. The adopter reads, for each topology, when each [pull request](../../../../core/glossary.md#term-pull-request--pull-request) opened and when that pull request merged.
3. The adopter counts the review rounds of each pull request from the pull request's [verdicts](../../../glossary.md#term-verdict--verdict), since each verdict names the [head](../../../../core/glossary.md#term-head--head) reviewed ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).
4. Where the [project](../../../../core/glossary.md#term-project--project) set its [audit comments](../../../glossary.md#term-audit-comment--audit-comment) to `full`, the adopter reads each write the agents made, with the write's versions ([DEC-049 point 2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-049-audit-journal-model.md#2-github-comments-are-a-configurable-provenance-stamped-projection-with-three-intensities)).
5. The adopter compares the topologies on these figures.

**Variants:** None.

**Postconditions:** The adopter holds, for each [topology](../../../glossary.md#term-topology--topology), the time from the topology's first [pull request](../../../../core/glossary.md#term-pull-request--pull-request) to the topology's last merge. The adopter also holds the review rounds of each pull request.

**Minimal guarantees:** None.

## Open for the design

What the adopter needs here that no accepted record decides yet:

- **How the topologies get comparable work,** in one of three ways:
  - a copy of the [project](../../../../core/glossary.md#term-project--project) for each [topology](../../../glossary.md#term-topology--topology)
  - the topologies run one after the other on comparable backlogs
  - one backlog split between the topologies
- **What else to record:**
  - the topology and the [seat](../../../glossary.md#term-seat--seat) behind each event. An ownership names its seat ([project-management DEC-059 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#9-a-tasks-claim-is-released-renewed-lapses-and-is-checked-again)), and no other event names a seat
  - the time from a plan's approval to its last merge
  - the person's own time
  - the tokens each agent spends
  - the work dropped or done twice
- **A command that prints the figures.** No record decides such a command.

## Sources

The goal is one #2096 names, under [EPIC](../../../glossary.md#term-epic--epic) #564. No record decides the goal yet, and the maintainer reviews the goal with these use cases.
