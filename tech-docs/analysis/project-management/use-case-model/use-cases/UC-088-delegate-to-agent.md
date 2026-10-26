---
id: UC-088
title: Delegate a Task of my scope to an agent I start
status: active
actor: ACT-lead-agent
other-actors:
  - core:ACT-ai-agent
requirements:
  - REQ-061
  - REQ-062
after:
  - [UC-082]
  - [UC-083, UC-060]
shortfalls:
  - at: 1
    issue: "#519"
    record: project-management:DEC-035#3
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
      record:
        - project-management:DEC-029
        - project-management:DEC-035#1
        - project-management:DEC-035#3
        - project-management:DEC-026
        - project-management:DEC-012
        - project-management:DEC-045#3
        - COR-013
        - COR-017
      artefact:
        - ACT-lead-agent
        - REQ-061
        - REQ-062
---

# UC-088 — Delegate a Task of my scope to an agent I start

**Goal:** Delegate a Task of my scope to an agent I start, which acts as my instance while it builds the Task.

**Other actors:** **AI agent** (`core:ACT-ai-agent`): the agent the lead starts, which the [topology](../../glossary.md#term-topology--topology) does not name. It builds the [Task](../../glossary.md#term-task--task) and returns its whole result to the lead (DEC-029).

**Preconditions:**

- **From UC-082:** The lead's clone has its number, and the lead's [scope](../../glossary.md#term-scope--scope) names the [workstreams](../../glossary.md#term-workstream--workstream) it takes work from (DEC-035 point 1 and DEC-045 point 3).
- **From UC-083, or UC-060:** The [Task](../../glossary.md#term-task--task) is filed in the lead's scope (DEC-012).

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has project-management installed, and the adapter deploys the agents the lead starts (COR-013 and COR-017).
- The harness lets a session start agents, down to a limit on how deep they nest (DEC-029).

**Trigger:** The lead decides to have another agent build a [Task](../../glossary.md#term-task--task) of its [scope](../../glossary.md#term-scope--scope).

**Main path:**

1. The lead starts the [Task](../../glossary.md#term-task--task): `pkit pm start-work <N>`, as `UC-084` steps 4 to 6 describe. Its [instance](../../glossary.md#term-instance--instance) becomes the Task's [owner](../../glossary.md#term-owner--owner) (DEC-035 point 3).

> [!WARNING]
> **Not built yet:** `start-work` writes no owner. DEC-035 point 3 decides that starting an [issue](../../glossary.md#term-issue--issue) with no owner makes the instance its owner, and #519 tracks it.

2. The lead starts an agent for the Task through the harness, and passes it no name, so the agent's whole result comes back (DEC-029).
3. The agent builds the Task on the Task's branch, commits its work and pushes it.
4. The agent ends, and returns its result to the lead.
5. The lead reviews the result, and lands the Task, as `UC-089` describes.

**Variants:**

- **3a.** The lead's session dies while the agent works, and the agent's session ends with it. A new session of the lead takes up the [Task](../../glossary.md#term-task--task), as `UC-086` describes, and finds on the Task's branch what the agent pushed.

**Postconditions:** The [Task](../../glossary.md#term-task--task)'s work is on its branch, and the lead's [instance](../../glossary.md#term-instance--instance) still owns the Task.

**Minimal guarantees:**

- The lead's [instance](../../glossary.md#term-instance--instance) stays the [Task](../../glossary.md#term-task--task)'s [owner](../../glossary.md#term-owner--owner), whichever session builds the Task (DEC-035 point 3).
- The agent's result reaches the lead whole, since the lead passes it no name (DEC-029).

## Open for the design

What the lead needs here that no accepted record decides yet:

- **Whether the agent acts as the lead's instance** when it runs a command of project-management in a linked worktree of the clone. Today a worktree reads no number of its clone. #1140 proposes that it reads its clone's number, which refines DEC-035 point 1 and waits for the maintainer's sign-off.
- **Several delegations at once.** `start-work` checks each [Task](../../glossary.md#term-task--task)'s branch out in the lead's own clone, so the lead delegates one Task at a time. A second delegation at once needs a linked worktree, which reads no number today (#1140).
- **Which agents a lead may start.** A scratchpad note on which agent may start which, `2026-07-02-agent-dispatch-privilege-model`, has produced no record yet.
