---
id: ACT-ai-agent
name: AI agent
status: active
needs:
  - Start every session with the project's rules and conventions loaded.
  - Find my role definition deployed, with the project's own paths filled in and my own permission grants applied.
  - Create a methodology artefact through its paired skill and stamp, so its id, place and front matter come out right.
  - Keep my intermediate files in a workspace that no commit carries and no confirmation guards.
  - Get a delegated agent's result back whole, never cut short while still reading as complete.
pkit:
  friction:
    anchors:
      record:
        - COR-013
    revalidated:
      at: 2026-10-14T09:21:10Z
      outcome: updated
---

# ACT-ai-agent — AI agent

An AI agent working under the methodology, acting on the system from outside.

- **Role holders:** the main session acting for a person, or an agent that session dispatches for one role (in the core: critic, architect, methodology-reviewer, convention-compliance-reviewer, rule-set-reviewer, process-author).
- **Occasions:** whenever work is done. It keeps no memory between sessions beyond what the repository holds.
- **Context:** None.
- **Place in the model:** when it does a role's work, it appears as a step in that role's use cases.
- **Core:** the agent architecture, the rules loaded into every session and the adapter's deployment make this actor exist. The core's reviewer agents advise, and no core gate counts their verdict.
