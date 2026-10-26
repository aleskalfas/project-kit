---
id: JRN-004
title: Set up the topology my project runs, and adjust the topology on what I measure
status: active
actor: core:ACT-adopter
steps:
  - UC-082
  - UC-091
  - UC-082
relies-on:
  - UC-064
  - UC-083
  - UC-084
  - UC-087
  - UC-089
  - UC-092
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
        - .pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py
      record:
        - project-management:DEC-045
        - project-management:DEC-059
        - project-management:DEC-059#1
        - project-management:DEC-059#7
        - project-management:DEC-035#1
        - project-management:DEC-035#8
        - project-management:DEC-028
      artefact:
        - UC-082
        - UC-091
        - UC-064
        - UC-083
        - UC-084
        - UC-087
        - UC-089
        - UC-092
---

# JRN-004 — Set up the topology my project runs, and adjust the topology on what I measure

**Goal:** Run several AI agents on my project at once, each in a separate seat, and adjust the topology on the figures of the agents' work.

**Steps:**

1. [UC-082](../use-cases/040-work-in-parallel/UC-082-set-up-topology.md) — Set up my project's topology in the project's committed configuration, so that every clone reads the same seats
   - **Needs from [UC-064](../use-cases/010-plan/UC-064-define-milestones-and-workstreams.md) (outside this journey):** the [workstreams](../../glossary.md#term-workstream--workstream) the [project](../../../core/glossary.md#term-project--project) declares, which a [seat](../../glossary.md#term-seat--seat)'s [scope](../../glossary.md#term-scope--scope) may name ([DEC-045 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#3-instances-reference-workstreams-1many-they-never-rebind-the-taxonomy)). [DEC-059 point 7](../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool) has the system warn of a workstream that no seat may take. UC-082 step 5 shows that nothing warns yet.
2. [UC-091](../use-cases/040-work-in-parallel/UC-091-measure-topologies.md) — Measure one topology against another on comparable work
   - **Needs from step 1 (UC-082):** each [topology](../../glossary.md#term-topology--topology) to compare, set up in turn. Each topology is committed on the [default branch](../../../core/glossary.md#term-default-branch--default-branch), so the branch's history shows which topology was in force for each [pull request](../../../core/glossary.md#term-pull-request--pull-request) ([DEC-059 point 1](../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#1-the-topology-is-committed-configuration-read-from-the-default-branch)).
   - **Needs from [UC-092](../use-cases/040-work-in-parallel/UC-092-take-seat.md) (outside this journey):** each seat of the topology taken by a clone, whose agent acts as that seat's agent. A seat that no clone takes has no agent, so none of the topology's work is done in that seat.
   - **Needs from [UC-083](../use-cases/040-work-in-parallel/UC-083-plan-across-scopes.md) (outside this journey):** the Tasks of each plan the planner approved, each [Task](../../glossary.md#term-task--task) filed with the workstream of the Task's work. These Tasks are the work a topology does.
   - **Needs from [UC-084](../use-cases/040-work-in-parallel/UC-084-take-next-task.md) (outside this journey):** each Task a worker agent took and built, with the Task's pull request open. A topology's time runs from the topology's first pull request.
   - **Needs from [UC-087](../use-cases/040-work-in-parallel/UC-087-hand-over-to-next-scope.md) (outside this journey):** what each next piece of the work needs from an earlier piece, landed on the default branch. The next piece's Task can start only after that landing. So the last merge of a topology's work comes only once every piece is handed on.
   - **Needs from [UC-089](../use-cases/040-work-in-parallel/UC-089-land-alongside-others.md) (outside this journey):** each Task's pull request merged, with the [verdict](../../glossary.md#term-verdict--verdict) of each review round naming the [head](../../../core/glossary.md#term-head--head) that round reviewed ([DEC-028](../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)). A pull request still open gives no time to the pull request's merge, so all the work compared must have landed.
3. [UC-082](../use-cases/040-work-in-parallel/UC-082-set-up-topology.md) — Set up my project's topology in the project's committed configuration, so that every clone reads the same seats
   - **Needs from step 2 (UC-091):** each topology's figures, which show the topology that serves the project better. The adopter sets that topology up again for the work that follows.

**Variants:**

- **1a.** The adopter runs one [topology](../../glossary.md#term-topology--topology) only, with no other topology to compare. The path ends after step 1, while the agents work.
- **2a.** The topology set up last serves the [project](../../../core/glossary.md#term-project--project) better. That topology is already in place, so the path ends after step 2.

**Postconditions:** The [project](../../../core/glossary.md#term-project--project) runs the [topology](../../glossary.md#term-topology--topology) that served the project better. For each topology compared, the adopter holds the time from the topology's first [pull request](../../../core/glossary.md#term-pull-request--pull-request) to the topology's last merge. The adopter also holds each pull request's review rounds.

**Minimal guarantees:**

- A [topology](../../glossary.md#term-topology--topology) never changes a [workstream](../../glossary.md#term-workstream--workstream), so a path stopped at any step leaves the [project](../../../core/glossary.md#term-project--project)'s workstreams as they were ([DEC-045 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-045-named-per-user-instances.md#3-instances-reference-workstreams-1many-they-never-rebind-the-taxonomy)).
- The [owner](../../glossary.md#term-owner--owner) is never an input to a gate or a move of the [issue lifecycle](../../glossary.md#term-issue-lifecycle--issue-lifecycle) ([DEC-035 point 8](../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#8-the-instance-marker-is-a-pm-domain-side-effect-never-engine-state)). So a path stopped with owners written leaves each [issue](../../glossary.md#term-issue--issue) to move as before.

## Sources

The goal rests on [project-management DEC-059](../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md), which decides the [topology](../../glossary.md#term-topology--topology), the topology's [seats](../../glossary.md#term-seat--seat) and each seat's [scope](../../glossary.md#term-scope--scope). Measuring one topology against another is a goal that #2096 names, as the sources of [UC-091](../use-cases/040-work-in-parallel/UC-091-measure-topologies.md) say. Adjusting the topology on the figures is setting the topology up again, as [UC-082](../use-cases/040-work-in-parallel/UC-082-set-up-topology.md) describes.
