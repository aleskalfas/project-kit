---
id: UC-081
title: Decide each answer my change was not asked for
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/software-engineer.md
        - .pkit/capabilities/software-engineering/agents/docs-reviewer.md
        - .pkit/rules/core.md
      record:
        - COR-050#1
        - COR-050#3
        - COR-050#6
        - COR-050#12
        - COR-050#16
        - software-engineering:DEC-002#1
        - COR-013
        - COR-017
        - COR-031
---

# UC-081 — Decide each answer my change was not asked for

**Goal:** Decide each answer the change check did not ask of my change, named for me in the agent's hand-off, before anything writes it.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `software-engineer` agent, which names each such answer in its hand-off and writes none of them. Also the code-review panel's `docs-reviewer`, which names each such answer it finds in the pull request, and judges none (software-engineering DEC-002 point 1).

**Preconditions:** None.

**Assumptions:**

- The project has software-engineering installed, or registered in place where software-engineering is developed (COR-017 and COR-031). The adapter deploys software-engineering's `software-engineer` and `docs-reviewer` agent definitions (COR-013).
- The change check flags each answer the change was not asked for, "not asked for by this change". The whole-repository check reports each debt (COR-050 points 6 and 12).
- A dispatched agent's hand-off reaches the agent that dispatched it whole, as `core:UC-029` describes (COR-047).
- The `software-engineer` agent keeps to its definition. Nothing at run time stops an agent writing an answer the change does not owe (COR-050 point 3).
- The developer, or another agent the developer directs, writes each answer the developer accepted, as `core:UC-002` describes (COR-050 point 3 and core rule 20).

**Trigger:** While making a change, as UC-001 describes, the `software-engineer` agent finds an answer the change check did not ask of the change.

**Main path:**

1. The agent finds an answer the change check did not ask of the change (COR-050 points 3 and 16). It may be:
   - an answer on an artefact the change check did not ask about, or for a debt the whole-repository check reports
   - a revisit entry for a target the change asks no revisit of, or one whose outcome alone changed
   - a reason for having no anchors
2. The agent writes none of these answers (`software-engineer.md`).
3. The agent names each in its hand-off, for the developer to decide (`software-engineer.md`).
4. The developer is shown each answer's words, and accepts them or declines the answer, as `core:UC-002` describes in its variant 5c (COR-050 point 3).
5. Each answer the developer accepted is written with those words, by the developer or by another agent the developer directs.
6. The `docs-reviewer` reviews the pull request, as UC-080 describes. The reviewer names in an `[advisory]` finding each such answer the change check flags "not asked for by this change" (software-engineering DEC-002 point 1). The finding says that the answer is the developer's decision.
7. The developer says in the pull request whether they accepted each answer the reviewer named.

**Variants:**

- **4a.** The developer declines an answer. Nothing writes it, and the artefact stays as it was.
- **4b.** The developer changes an answer's words. The words the developer gives are the ones written, since the developer has seen them and accepted them.
- **6a.** Such an answer is `updated`. The reviewer still checks its sentence against the diff, and blocks where the sentence is missing or wrong (software-engineering DEC-002 point 1).
- **6b.** The merge gate does not require the `docs-reviewer` for the pull request, such as an unclassified pull request that changes only documents. No reviewer names the answers, and the use case ends at step 5.
- **6c.** The change is committed straight to the default branch, with no pull request. The developer, as the person the agent works for, decided each answer at step 4, and the use case ends at step 5.

**Postconditions:** Each answer the change check did not ask of the change is written only with words the developer accepted, or not at all. The pull request says which of them the developer accepted.

**Minimal guarantees:**

- The `software-engineer` agent writes no answer the change check did not ask of its change (`software-engineer.md`).
- The `docs-reviewer` blocks on no such answer, which the developer decides, but for an `updated` one's sentence (software-engineering DEC-002 point 1).
