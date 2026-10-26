---
id: JRN-004
title: Direct several AI agents that work on my project at once
status: active
actor: ACT-director
steps:
  - UC-082
  - UC-090
  - UC-091
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
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
        - .pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py
      record:
        - project-management:DEC-045
        - project-management:DEC-035#1
        - project-management:DEC-035#3
        - project-management:DEC-035#4
        - project-management:DEC-035#7
        - project-management:DEC-035#8
        - project-management:DEC-028
      artefact:
        - ACT-director
        - UC-082
        - UC-090
        - UC-091
        - UC-064
        - UC-083
        - UC-084
        - UC-087
        - UC-089
---

# JRN-004 — Direct several AI agents that work on my project at once

**Goal:** Run several AI agents on my project at once, each on its own scope, and see and measure their work.

**Steps:**

1. UC-082 — Set up the topology my project runs, so that every agent reads the same one
   - **Needs from UC-064 (outside this journey):** the [workstreams](../../glossary.md#term-workstream--workstream) the [project](../../../core/glossary.md#term-project--project) declares, which each agent's [scope](../../glossary.md#term-scope--scope) names (DEC-045 point 3). The Tasks of a workstream that no scope names reach no agent (UC-084 step 1). DEC-045 point 4 has the system warn of such a workstream, and UC-082 step 5 shows that nothing warns yet.
2. UC-090 — See which agent works on which issue, without visiting each agent
   - **Needs from step 1 (UC-082):** each agent's clone with a number of its own, which makes the clone an [instance](../../glossary.md#term-instance--instance) (DEC-035 point 1). A clone that sets no number marks no [issue](../../glossary.md#term-issue--issue), so its agent's issues show in the listing with no [owner](../../glossary.md#term-owner--owner).
   - **Needs from UC-083 (outside this journey):** the Tasks the planning agent filed for each scope, each owned by the planning agent's instance (DEC-035 point 3). Until #519 is done, `create-issue` writes no owner, so these Tasks show with none.
   - **Needs from UC-084 (outside this journey):** each [Task](../../glossary.md#term-task--task) a worker agent took, owned by that agent's instance (DEC-035 point 3). Until #519 is done, `start-work` writes no owner either. So the listing tells a Task in flight from one that nobody took only by each Task's state.
   - **Needs from UC-087 (outside this journey):** each finished piece's Task closed, which clears the Task's owner, and each Task handed to another instance, owned by that instance (DEC-035 point 4). Until #521 is done, `handoff-issue` hands an issue from one person to another only, so no hand-over between instances shows.
3. UC-091 — Measure one topology against another on comparable work
   - **Needs from step 1 (UC-082):** each [topology](../../glossary.md#term-topology--topology) to compare, set up in turn. GitHub records no topology beside a [pull request](../../../core/glossary.md#term-pull-request--pull-request), so the director keeps which topology did which work.
   - **Needs from UC-089 (outside this journey):** each Task's pull request merged, with the [verdict](../../glossary.md#term-verdict--verdict) of each review round naming the [head](../../../core/glossary.md#term-head--head) that round reviewed (DEC-028). A pull request still open gives no time to its merge, so all the work compared must have landed.

**Variants:**

- **2a.** The listing shows a [scope](../../glossary.md#term-scope--scope) whose Tasks no agent takes, or one agent with far more work than the others. The director alters the [topology](../../glossary.md#term-topology--topology), and the path rejoins at step 1.
- **3a.** The director runs one topology only, and has none to compare it with. The path ends after step 2.

**Postconditions:** The director knows which [instance](../../glossary.md#term-instance--instance) works on each open [issue](../../glossary.md#term-issue--issue). For each [topology](../../glossary.md#term-topology--topology), the director holds the time from its first [pull request](../../../core/glossary.md#term-pull-request--pull-request) to its last merge, and each pull request's review rounds.

**Minimal guarantees:**

- A [topology](../../glossary.md#term-topology--topology) never changes a [workstream](../../glossary.md#term-workstream--workstream), so a path stopped at any step leaves the [project](../../../core/glossary.md#term-project--project)'s workstreams as they were (DEC-045 point 3).
- The [owner](../../glossary.md#term-owner--owner) is never an input to a gate or a move of the [issue lifecycle](../../glossary.md#term-issue-lifecycle--issue-lifecycle) (DEC-035 point 8). So a path stopped with owners written leaves each [issue](../../glossary.md#term-issue--issue) to move as before.

## Sources

The goal rests on DEC-045, which decides the [topology](../../glossary.md#term-topology--topology) and the [scope](../../glossary.md#term-scope--scope) the topology gives each agent. It rests on DEC-035 point 7 too, which decides the listing of issues signed with their [owner](../../glossary.md#term-owner--owner). Measuring one topology against another is a goal that #2096 names, as the sources of UC-091 say.
