---
id: UC-029
title: Get a delegated agent's result back whole
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
after:
  - [UC-014, UC-019]
pkit:
  friction:
    anchors:
      path:
        - .pkit/schemas/harness-requirements.yaml
        - src/project_kit/harness_support.py
        - .pkit/adapters/README.md
      record:
        - COR-047#2
        - COR-047#3
        - COR-047#4
      artefact:
        - ACT-ai-agent
        - ACT-operator
---

# UC-029 — Get a delegated agent's result back whole

**Goal:** Get a delegated agent's result back whole, never cut short while still reading as complete.

**Other actors:**

- **Operator** (`ACT-operator`): keeps the harness's settings under which the adapter's support declaration says the requirement holds. The operator's `pkit harness report` reads only the support declarations. So it resolves the requirement `indeterminate`, with the adapter's grade and cost, and never as met (COR-047 points 3 and 4).

**Preconditions:** **From UC-014 or UC-019:** An adapter for the project's harness answers the harness requirement `delegated-result-complete` with a grade and any cost (COR-047 point 2).

**Assumptions:**

- The harness delivers a delegated agent's whole result to the agent that delegated to it, with no further exchange needed to fetch the rest. The methodology states it as the harness requirement `delegated-result-complete`, whose truth only an agent inside a session can see (COR-047 point 4).
- The agent meets the cost the adapter's support declaration names, where it grades the requirement `at-cost`. Nothing at run time holds an agent to it (COR-047 point 2).

**Trigger:** The agent's work calls for another role's judgement, such as a review of its draft.

**Main path:**

1. The agent dispatches a delegated agent for that role through the harness's delegation tool. It does so at the cost the adapter's support declaration names. Claude Code's declaration, for one, grades it `at-cost`. It holds while the harness's agent teams are off, or for a delegated agent given no `name`.
2. The harness runs the delegated agent, which does its work and ends with its result.
3. The harness hands the whole result to the agent that delegated, uncut.
4. The agent acts on the whole result, such as fixing each finding that a review marked blocking.

**Variants:**

- **1a.** The agent dispatches the delegated agent without meeting the cost, such as with a `name` while Claude Code's agent teams are on. The harness cuts the result, at 4064 characters in the measurement the requirement cites (`.pkit/schemas/harness-requirements.yaml`). The part that arrives reads as a complete answer, and nothing in the system detects the cut.
- **3a.** The support declaration grades the requirement `not-achievable` for every version. No delegation brings the whole result back, and `pkit harness report` resolves the requirement `unsatisfied`, `computed` (COR-047 point 2).

**Postconditions:** The agent holds the delegated agent's whole result, and acts on all of it.

**Minimal guarantees:** A requirement that the support declaration leaves unanswered, or that no reading can observe, is never reported as met (COR-047 points 3 and 4).
