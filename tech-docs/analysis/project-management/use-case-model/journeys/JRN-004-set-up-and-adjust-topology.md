---
id: JRN-004
title: Set up the topology my project runs, and adjust it on what I measure
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
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
        - .pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py
      record:
        - project-management:DEC-045
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
---

# JRN-004 — Set up the topology my project runs, and adjust it on what I measure

**Goal:** Run several AI agents on my project at once, each on its own scope, and adjust their topology on what I measure of their work.

**Steps:**

1. UC-082 — Set up the topology my project runs, so that every agent reads the same one
   - **Needs from UC-064 (outside this journey):** the [workstreams](../../glossary.md#term-workstream--workstream) the [project](../../../core/glossary.md#term-project--project) declares, which each agent's [scope](../../glossary.md#term-scope--scope) names (DEC-045 point 3). The Tasks of a workstream that no scope names reach no agent (UC-084 step 1). DEC-045 point 4 has the system warn of such a workstream, and UC-082 step 5 shows that nothing warns yet.
2. UC-091 — Measure one topology against another on comparable work
   - **Needs from step 1 (UC-082):** each [topology](../../glossary.md#term-topology--topology) to compare, set up in turn. GitHub records no topology beside a [pull request](../../../core/glossary.md#term-pull-request--pull-request), so the adopter keeps which topology did which work.
   - **Needs from UC-083 (outside this journey):** the Tasks of each plan the planner approved, each filed with the workstream of its work. These Tasks are the work a topology does.
   - **Needs from UC-084 (outside this journey):** each [Task](../../glossary.md#term-task--task) a worker agent took and built, with its pull request open. A topology's time runs from its first pull request.
   - **Needs from UC-087 (outside this journey):** what each next piece of the work needs from an earlier piece, landed on the [default branch](../../../core/glossary.md#term-default-branch--default-branch). The next piece's Task can start only after that landing, so a topology's work reaches its last merge only once every piece is handed on.
   - **Needs from UC-089 (outside this journey):** each Task's pull request merged, with the [verdict](../../glossary.md#term-verdict--verdict) of each review round naming the [head](../../../core/glossary.md#term-head--head) that round reviewed (DEC-028). A pull request still open gives no time to its merge, so all the work compared must have landed.
3. UC-082 — Set up the topology my project runs, so that every agent reads the same one
   - **Needs from step 2 (UC-091):** each topology's figures, which show the one that serves the project better. The adopter sets that topology up again for the work that follows.

**Variants:**

- **1a.** The adopter runs one [topology](../../glossary.md#term-topology--topology) only, and has none to compare it with. The path ends after step 1, while the agents work.
- **2a.** The topology set up last serves the [project](../../../core/glossary.md#term-project--project) better. It is already in place, so the path ends after step 2.

**Postconditions:** The [project](../../../core/glossary.md#term-project--project) runs the [topology](../../glossary.md#term-topology--topology) that served it better. For each topology compared, the adopter holds the time from its first [pull request](../../../core/glossary.md#term-pull-request--pull-request) to its last merge, and each pull request's review rounds.

**Minimal guarantees:**

- A [topology](../../glossary.md#term-topology--topology) never changes a [workstream](../../glossary.md#term-workstream--workstream), so a path stopped at any step leaves the [project](../../../core/glossary.md#term-project--project)'s workstreams as they were (DEC-045 point 3).
- The [owner](../../glossary.md#term-owner--owner) is never an input to a gate or a move of the [issue lifecycle](../../glossary.md#term-issue-lifecycle--issue-lifecycle) (DEC-035 point 8). So a path stopped with owners written leaves each [issue](../../glossary.md#term-issue--issue) to move as before.

## Sources

The goal rests on DEC-045, which decides the [topology](../../glossary.md#term-topology--topology) and the [scope](../../glossary.md#term-scope--scope) the topology gives each agent. Measuring one topology against another is a goal that #2096 names, as the sources of UC-091 say. Adjusting the topology on what the measure shows is setting it up again, as UC-082 describes.
