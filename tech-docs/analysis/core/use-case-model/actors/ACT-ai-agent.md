---
id: ACT-ai-agent
name: AI agent
status: active
summary: "An AI agent working under the methodology, acting on the system from outside."
needs:
  - Start every session with the project's operational rules and conventions loaded.
  - Find my agent definition deployed, with the project's own paths filled in and my own permission grants applied.
  - Create a methodology file through its paired skill and stamp, so its id, location and front matter come out right.
  - Keep my intermediate files in the agent workspace, which no commit carries and no confirmation guards.
  - Get a delegated agent's result back whole, never cut short while still reading as complete.
  - Read the precise contract of each area, capability and adapter I use, for the installed version, in files beside what they describe.
pkit:
  friction:
    anchors:
      record:
        - COR-013
        - COR-024
        - COR-044#2
        - COR-057#5
        - COR-068
        - COR-005
        - COR-047
        - ADR-060#1
        - ADR-060#3
---

# ACT-ai-agent — AI agent

An AI agent working under the methodology, acting on the system from outside.

- **Role holders:** the main session acting for a person, or an agent it dispatches under one [agent definition](../../glossary.md#term-agent-definition--agent-definition) (in the core: critic, architect, methodology-reviewer, convention-compliance-reviewer, rule-set-reviewer, process-author).
- **Occasions:** whenever work is done. It keeps no memory between sessions beyond what the repository holds.
- **Context:** None.
- **Place in the model:** when it does a <!-- pkit:not-the-term -->role's work, it appears as a step in that <!-- pkit:not-the-term -->role's use cases.
- **Core:** the agent architecture, the rules loaded into every session and the [adapter](../../glossary.md#term-adapter--adapter)'s deployment make this actor exist. The core's [reviewer](../../glossary.md#term-reviewer--reviewer) agents advise, and no core gate counts their verdict.
