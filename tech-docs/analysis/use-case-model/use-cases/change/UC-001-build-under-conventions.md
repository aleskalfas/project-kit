---
id: UC-001
title: Build my change under my project's conventions
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/software-engineer.md
        - .pkit/adapters/claude-code/_resolve_agent.py
        - .pkit/rules/core.md
        - .pkit/rules/project.md
      record:
        - software-engineering:DEC-001
        - COR-024
        - COR-050#3
        - ADR-052#3
      artefact:
        - ACT-developer
        - ACT-ai-agent
---

# UC-001 — Build my change under my project's conventions

**Goal:** Build my change with an agent that writes the change's code to my project's own conventions, read from wherever I keep them.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): the `software-engineer` agent finds its definition deployed, with the path to the project's conventions corpus where the project names one. It never invents a convention the corpus lacks (software-engineering DEC-001 point 5).

**Preconditions:** The project has installed the software-engineering capability, and the adapter has deployed its `software-engineer` agent.

**Assumptions:**

- The agent follows its definition. Nothing at run time holds it to the corpus, and no reviewer reads the corpus to check its code (software-engineering DEC-001 point 4).
- The agent asks the developer before a destructive operation, such as deleting files or rewriting history (core rule 8).
- The agent retries once a step that failed for a cause outside its own work, such as a locked signing key. Then it stops and reports (core rule 21).
- In project-kit, every commit the agent makes is signed, and the agent never switches signing off (project rule 4).

**Trigger:** The developer asks the `software-engineer` agent to make a change, such as the code an issue asks for.

**Main path:**

1. The developer asks the `software-engineer` agent to make the change.
2. The agent reads the conventions corpus at the path its deployed definition gives for `<project-conventions>`, before it writes any code.
3. The agent writes the change's code, applying the corpus to each choice it settles, such as naming, layout and error handling.
4. The agent reads its diff again against the corpus, and corrects what does not conform.
5. The agent hands the change to the reviewers (COR-024). The `critic` reviews a substantive design, and the `architect` reviews one that touches the big picture. The `convention-compliance-reviewer` reviews the diff.
6. The agent fixes each finding its reviewer marked blocking, and records each advisory in the pull request with how it was answered.

**Variants:**

- **2a.** The project names no corpus, or the corpus is empty or says nothing on a choice. The agent says so, as in "no project conventions found for X; proceeding as a careful generalist", and works by ordinary judgement. The path rejoins at step 3.
- **3a.** A design fork arises that the corpus does not settle. The agent names it and its trade-off in its hand-off, rather than choosing silently, and the path goes on at step 4.
- **3b.** The change makes an anchored artefact owe an answer. The agent writes the answers its own change owes, as UC-002 describes, and the path goes on at step 4.

**Postconditions:** The change's code conforms to the project's conventions corpus wherever the corpus speaks, and its reviewers have it, with each blocking finding fixed.

**Minimal guarantees:**

- A project that names no corpus still gets the agent deployed. The deployed definition drops the read, and the agent works as a generalist (ADR-052 point 3 and `_resolve_agent.py`).
