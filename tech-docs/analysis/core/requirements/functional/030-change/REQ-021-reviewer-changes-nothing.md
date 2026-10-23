---
id: REQ-021
title: A reviewer never changes the work it judges
status: active
statement: A reviewer never changes the work it judges, nor the repository that work lives in.
measure: "After a review, no file the repository tracks has changed, and nothing was staged, committed or pushed for it. Each working file of the review lies in the agent workspace."
applies-to: Every reviewer that judges a draft or a change, an agent or a person, the core's reviewer agents and a component's included, whatever it judges.
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
---

# REQ-021 · Functional · A reviewer never changes the work it judges

**Verified by:** Tests find that every reviewer agent that can run commands states the same section on what its read-only covers. Its source and its deployed copy both state it, and name the workspace for its working files. Nothing checks at run time what a reviewer changed.

**Rationale:** A reviewer's verdict is worth only its independence, as the agents README says of the role. COR-024 keeps the critic read-only to preserve that independence, and COR-057 point 1 says the rule-set reviewer changes nothing it reviews.
