---
id: UC-029
title: Get a delegated agent's result back whole
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
after:
  - [UC-014, UC-019, UC-049]
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

- **Operator** (`ACT-operator`): keeps the [harness](../../../glossary.md#term-harness--harness)'s settings under which the [adapter](../../../glossary.md#term-adapter--adapter)'s support declaration says the requirement holds. The operator's `pkit harness report` reads only the support declarations. So it resolves the requirement `indeterminate`, with the adapter's grade and cost, and never as met (COR-047 points [3](../../../../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md#3-silence-is-indeterminate-never-satisfaction) and [4](../../../../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md#4-every-requirement-names-its-observation-point-what-cannot-be-observed-is-reported-not-passed)).

**Preconditions:** **From UC-014, UC-019 or UC-049:** An [adapter](../../../glossary.md#term-adapter--adapter) for the [project](../../../glossary.md#term-project--project)'s [harness](../../../glossary.md#term-harness--harness) answers the harness requirement `delegated-result-complete` with a grade and any cost ([COR-047 point 2](../../../../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md#2-each-adapter-declares-its-support-graded-and-may-bound-it-by-harness-version)).

**Assumptions:**

- Where the agent meets the cost the [adapter](../../../glossary.md#term-adapter--adapter)'s support declaration names, the [harness](../../../glossary.md#term-harness--harness) delivers the delegated agent's whole result, with no further exchange needed. The [methodology](../../../glossary.md#term-methodology--methodology) states this as the harness requirement `delegated-result-complete`, whose truth only an agent inside a session can see ([COR-047 point 4](../../../../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md#4-every-requirement-names-its-observation-point-what-cannot-be-observed-is-reported-not-passed)).
- No [operational rule](../../../glossary.md#term-operational-rule--operational-rule) of the core tells the agent that cost, and nothing at run time holds the agent to it ([COR-047 point 2](../../../../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md#2-each-adapter-declares-its-support-graded-and-may-bound-it-by-harness-version)).

**Trigger:** The agent's work calls for another agent's judgement, such as a review of its draft.

**Main path:**

1. The agent dispatches a delegated agent for that judgement through the [harness](../../../glossary.md#term-harness--harness)'s delegation tool, at the cost the [adapter](../../../glossary.md#term-adapter--adapter)'s support declaration names. Claude Code's declaration, for one, grades `delegated-result-complete` as `at-cost`. The result arrives whole while the harness's agent teams are off, or for a delegated agent given no `name`.
2. The harness runs the delegated agent, which does its work and ends with its result.
3. The harness hands the whole result to the agent that delegated, uncut.
4. The agent acts on the whole result, such as fixing each [finding](../../../glossary.md#term-finding--finding) that a review marked blocking.

**Variants:**

- **1a.** The agent dispatches the delegated agent without meeting the cost, such as with a `name` while Claude Code's agent teams are on. The [harness](../../../glossary.md#term-harness--harness) cuts the result, at 4064 characters in the measurement the requirement cites (`.pkit/schemas/harness-requirements.yaml`). The part that arrives reads as a complete result, and nothing in the [system](../../../glossary.md#term-system--system) detects the cut.
- **3a.** The support declaration grades the requirement `not-achievable`, with `harness_versions: unbounded`. No delegation brings the whole result back, and `pkit harness report` resolves the requirement `unsatisfied`, `computed` ([COR-047 point 2](../../../../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md#2-each-adapter-declares-its-support-graded-and-may-bound-it-by-harness-version)).

**Postconditions:** The agent holds the delegated agent's whole result, and acts on all of it.

**Minimal guarantees:** A requirement that the support declaration leaves unanswered, or that no reading can observe, is never reported as met (COR-047 points [3](../../../../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md#3-silence-is-indeterminate-never-satisfaction) and [4](../../../../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md#4-every-requirement-names-its-observation-point-what-cannot-be-observed-is-reported-not-passed)).
