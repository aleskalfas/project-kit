---
id: REQ-021
title: A reviewer agent never changes the work it judges
status: active
statement: A reviewer agent never changes the work it judges.
measure: "After a review, the work under review holds what it held before, and nothing was staged, committed or pushed for the review. Each working file of the review lies in the agent workspace."
applies-to: "Every reviewer agent that judges a draft or a change, the core's and a component's. The architect's edits of the architecture documents and decision records it keeps, which COR-024 grants it, fall outside it."
actors:
  - ACT-developer
  - ACT-merge-authoriser
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_reviewer_agents.py
        - .pkit/agents/README.md
      record:
        - COR-024
        - COR-057#1
      artefact:
        - ACT-developer
        - ACT-merge-authoriser
    revalidated:
      at: 2026-10-25T00:34:35Z
      outcome: unchanged
      unchanged-because: The agents README's Friction writers now says where the writers write and drops the answer owed after a conflict. A reviewer still writes nothing on what it judges.
---

# REQ-021 · Functional · A reviewer agent never changes the work it judges

**Verified by:** Tests find that every [reviewer](../../../glossary.md#term-reviewer--reviewer) agent that can run commands states the same section on what its read-only covers. Its source and its deployed copy both state it, and name the workspace for its working files. Nothing checks at run time what a reviewer changed.

**Rationale:** A [reviewer](../../../glossary.md#term-reviewer--reviewer)'s verdict is worth only its independence, as the agents README says of reviewers. COR-024 keeps the critic read-only to preserve that independence, and COR-057 [point](../../../glossary.md#term-point--point) 1 says the rule-set reviewer changes nothing it reviews.
