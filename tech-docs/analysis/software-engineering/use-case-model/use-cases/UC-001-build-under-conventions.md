---
id: UC-001
title: Build my change under my project's conventions
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
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
        - software-engineering:DEC-002#4
        - project-management:DEC-028
        - project-management:DEC-032#D1
        - COR-024
        - COR-050#3
        - ADR-052#3
        - ADR-052#6
        - COR-013
        - COR-017
        - COR-031
    revalidated:
      at: 2026-10-20T10:10:43Z
      outcome: unchanged
      unchanged-because: Project rule 2 adds that CI skips the suite on a pull request whose only changes since a passing full run are answers. The agent still runs the tests of what it changed and leaves the full suite to the pre-push hook and CI, as the use case says.
---

# UC-001 — Build my change under my project's conventions

**Goal:** Build my change with an agent that writes the change's code to my project's own conventions, read from wherever I keep them.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `software-engineer` agent, and the reviewer agents that judge its change. The engineer never invents a convention the corpus lacks (software-engineering DEC-001 point 5).

**Preconditions:** None.

**Assumptions:**

- The project has the software-engineering capability installed, and the adapter has deployed its `software-engineer` agent definition. The core provides both: a capability is installed, or registered in place where it is developed (COR-017, COR-031), and an adapter deploys its agents (COR-013).
- The running agent finds the corpus the project names. The adapter writes its path into the deployed definition's front matter only, and the agent definition's text keeps `<project-conventions>` (ADR-052 points 3 and 6).
- Nothing at run time holds the agent to the corpus. Where the project runs the code-review panel, its agents read the corpus too (software-engineering DEC-002 point 4).
- The change builds only on accepted decision records (core rule 2).
- The agent asks before a destructive operation, such as `git push --force` or deleting files outside `project/` (core rule 8).
- The agent works within the permission model, never around it (core rules 14 and 15).
- The agent changes no other repository, unless the person it works for confirms it (core rule 19).
- The agent retries once a step that failed for a cause outside its own work, such as a locked signing key. It first checks that the step did not take effect. If it fails again, the agent stops and reports (core rule 21).
- In project-kit, the agent runs the tests of what it changed, and leaves the full suite to the pre-push hook and CI (project rule 2).
- In project-kit, every commit is signed, and signing is never switched off. A commit that fails to sign waits a minute before its one retry (project rule 4).

**Trigger:** The developer asks the `software-engineer` agent to make a change, such as the code an issue asks for.

**Main path:**

1. The developer asks the `software-engineer` agent to make the change.
2. The agent reads the conventions corpus the project names, before it writes any code.
3. The agent writes the change's code, applying the corpus to each choice it settles, such as naming, layout and error handling.
4. The agent reads its diff again against the corpus, and corrects what does not conform.
5. The agent hands the change on for review, and invokes no reviewer itself (COR-024).
6. The reviewers judge the change: COR-024's stack where the change calls for it, and the reviewers the merge gate requires (project-management DEC-032).
7. The agent fixes each finding its reviewer marked blocking, and records each advisory in the pull request with how it was answered. A finding marked for a person waits for that person (project-management DEC-028).

**Variants:**

- **2a.** The project names no corpus, as project-kit names none today, or the corpus is empty or silent on a choice. The agent says so, as in "no project conventions found for X; proceeding as a careful generalist", and works by ordinary judgement. The path rejoins at step 3.
- **3a.** A design fork arises that the corpus does not settle. The agent names it and its trade-off, rather than choosing silently. The developer decides, asked one decision at a time with the agent's recommendation (core rule 17), and the path rejoins at step 3.
- **3b.** The change makes an anchored artefact owe an answer. The agent writes the answers its own change owes, as `core:UC-002` describes, and says in its hand-off that the change wrote answers. It composes no list of them, and the path goes on at step 4.

**Postconditions:** The change's code conforms to the project's conventions corpus wherever the corpus speaks, and its reviewers have judged it, with each blocking finding fixed.

**Minimal guarantees:**

- A project that names no corpus still gets the agent definition deployed. The deployed definition drops the read, and the agent works as a generalist (ADR-052 points 3 and 6, and `_resolve_agent.py`).
