---
id: UC-015
title: Get a delegated agent's result back whole
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
pkit:
  friction:
    anchors:
      path:
        - .pkit/schemas/harness-requirements.yaml
        - .pkit/capabilities/project-management/agents/project-manager/project-manager.md
        - CLAUDE.md
        - .pkit/adapters/README.md
      record:
        - COR-047
        - project-management:DEC-029
      artefact:
        - ACT-ai-agent
        - ACT-operator
---

# UC-015 — Get a delegated agent's result back whole

**Goal:** Get a delegated agent's result back whole, never cut short while still reading as complete.

**Other actors:**

- **Operator** (`ACT-operator`): where the harness's agent-teams feature is on, the `project-manager` agent tells the operator so, once in the session. A named dispatch would then cut a review short (project-management DEC-029).

**Preconditions:** None.

**Assumptions:**

- The harness delivers a helper's whole result to the agent that delegated to it, with no further exchange needed to fetch the rest. The methodology declares this as the harness requirement `delegated-result-complete` (COR-047). No adapter declares its support yet, and no report reads it, so nothing in the system tells whether it holds (`.pkit/adapters/README.md`).
- The agent passes no `name` when it dispatches a helper. The `project-manager` agent's definition asks it (project-management DEC-029), and in project-kit, `CLAUDE.md` asks it of every session. Nothing at run time holds an agent to it.

**Trigger:** The agent's work calls for another role's judgement, such as a review of its draft.

**Main path:**

1. The agent dispatches a helper agent for that role through the harness's delegation tool, such as Claude Code's `Agent` tool, and passes no `name`.
2. The harness runs the helper, which does its work and ends with its result.
3. The harness hands the whole result to the agent, uncut.
4. The agent acts on the whole result, such as fixing each finding a review marked blocking.

**Variants:**

- **1a.** The delegation tool offers a `name` parameter, so the harness's agent-teams feature is on. The agent still passes no `name`. The `project-manager` agent tells the operator so, once in the session (project-management DEC-029).
- **1b.** The agent passes a `name`. The harness makes the helper a persistent teammate, and cuts its result at 4064 characters, ending `[result truncated — ask the agent for the rest via SendMessage]`. The part that arrives reads as complete, and nothing in the system detects the cut (COR-047).

**Postconditions:** The agent holds the helper's whole result, and acts on all of it.

**Minimal guarantees:** None.
