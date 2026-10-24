---
id: REQ-050
title: An agent proposes what the analysis records, and a person decides it
status: active
statement: An agent proposes each revalidation outcome, candidate, freed id and change to a declared structure, and a person decides each before it is committed.
measure: The analysis-resolver's definition grants no tool that edits a file in place, and owns no path. Its proposal hands each writer's command to a person. The analysis-author skill asks a person to confirm each candidate, and to accept each entry that frees an id or changes a declared structure.
applies-to: "The analysis-resolver agent, in a session or a run, and an agent onboarding a project, freeing ids or choosing parts with the analysis-author skill."
actors:
  - core:ACT-developer
  - core:ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/agents/analysis-resolver/analysis-resolver.md
        - tests/test_software_analysis_resolver.py
        - .pkit/capabilities/software-analysis/skills/analysis-author/analysis-author.md
        - .pkit/capabilities/software-analysis/skills/analysis-author/choose-templates.md
        - .pkit/capabilities/software-analysis/skills/analysis-author/build-analysis.md
      record:
        - software-analysis:DEC-001#1
        - software-analysis:DEC-001#3
        - software-analysis:DEC-001#5
        - software-analysis:DEC-001#9
        - COR-050#3
    revalidated:
      at: 2026-10-24T01:59:08Z
      outcome: unchanged
      unchanged-because: The change has the build read the declared surface before any candidate, and the measures after the last step. A person still decides each candidate, and a reason for having no anchors is written only once a person accepts it.
---

# REQ-050 · Functional · An agent proposes what the analysis records, and a person decides it

**Verified by:** Tests of the agent definition find that it grants Read, Glob, Grep, Bash and Write alone, and owns no path. They find that it gives each writer as a command for the person, with no consent flag. Nothing confines its Write or its Bash at run time. No test holds what the skill asks of an agent, and no test runs an agent.

**Rationale:** Whether a change was meant is a question of intent, and where intent is unclear only a person knows (DEC-001 point 5). On a brownfield project, a person confirms the candidates (DEC-001 point 9). Only the project frees an id, and no tool infers one (DEC-001 point 3). A kind's parts are the project's own choice as it adopts the capability (DEC-001 point 1).
