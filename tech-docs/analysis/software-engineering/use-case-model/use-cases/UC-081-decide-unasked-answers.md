---
id: UC-081
title: Decide each answer my change was not asked for
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-001]
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
        - COR-050#16
        - software-engineering:DEC-002#1
        - COR-013
        - COR-017
        - COR-031
---

# UC-081 — Decide each answer my change was not asked for

**Goal:** Decide each answer the change check did not ask of my change, from its words in the agent's hand-off, before it is written.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `software-engineer` agent, which names each such answer in its hand-off and writes none of them. Also the code-review panel's `docs-reviewer`, which names each such answer it finds in the pull request, and judges none (software-engineering DEC-002 point 1).

**Preconditions:**

- **From UC-001:** The `software-engineer` agent made the change, and wrote the answers the change check asks of it.

**Assumptions:**

- The project has software-engineering installed, or registered in place where it is developed (COR-017 and COR-031). The adapter deploys its `software-engineer` and `docs-reviewer` agent definitions (COR-013).
- The change check flags each answer the change was not asked for, "not asked for by this change". The whole-repository check reports each debt (COR-050 points 3 and 6).
- An agent writes no answer the change does not owe until a person accepts its words. Nothing at run time stops it (COR-050 point 3 and core rule 20).
- An answer the developer accepted is written as `core:UC-002` describes, by the developer or by an agent the developer directs (COR-050 point 3).

**Trigger:** The `software-engineer` agent finds that an artefact needs an answer the change check did not ask of the change.

**Main path:**

1. The agent finds an answer the change check did not ask of the change. It may be on an artefact the change did not flag, or on a target of a link the change asks no revisit of. It may be for a debt the whole-repository check reports, or a reason for having no anchors (COR-050 points 1 and 3).
2. The agent writes none of these answers, and runs no command that would write one (core rule 20).
3. The agent names each in its hand-off, for the developer to decide. It gives the artefact, the outcome and the reason, word for word, with the command that would write it (COR-050 point 3).
4. The developer reads each answer, and accepts its words or declines it.
5. Each answer the developer accepted is written with the words the developer accepted, as `core:UC-002` describes in its variant 5c.
6. The `docs-reviewer` reviews the pull request, as UC-080 describes. The reviewer names in an `[advisory]` finding each answer the change check flags "not asked for by this change" (software-engineering DEC-002 point 1). The finding says that the answer is the developer's decision.
7. The developer says in the pull request whether they accepted each answer the reviewer named.

**Variants:**

- **4a.** The developer declines an answer. Nothing writes it, and the artefact stays as it was.
- **4b.** The developer changes an answer's words. The words the developer gives are the ones written, since the developer has seen them and accepted them.
- **6a.** Such an answer is `updated`. The reviewer still checks its sentence against the diff, and blocks where the sentence is missing or wrong (software-engineering DEC-002 point 1).
- **6b.** The merge gate does not require the `docs-reviewer` for the pull request, such as an unclassified pull request that changes only documents. No reviewer names the answers, and the use case ends at step 5.

**Postconditions:** Each answer the change check did not ask of the change is written only with words the developer accepted, or not at all. The pull request says which of them the developer accepted.

**Minimal guarantees:**

- The `software-engineer` agent writes no answer the change check did not ask of its change (COR-050 point 3).
- The `docs-reviewer` blocks on no such answer, since it cannot tell whether the developer accepted it (software-engineering DEC-002 point 1).
