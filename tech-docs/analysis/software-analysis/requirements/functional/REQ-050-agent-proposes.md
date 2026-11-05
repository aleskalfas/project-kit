---
id: REQ-050
title: An agent proposes what the analysis records, and a person decides it
status: active
statement: An agent proposes each revalidation outcome, candidate, freed id and edit to a declared structure, and a person decides each before it is committed.
measure: The analysis-resolver's agent definition grants no tool that edits a file in place, and owns no path. Its revalidation proposal hands each command that writes to a person. The analysis-author skill asks a person to confirm each candidate, and to accept each entry that frees an id or changes a declared structure.
applies-to: "The analysis-resolver agent, in a session or a run, and an agent describing an existing project, freeing ids or choosing parts with the analysis-author skill."
obligation: v1:sha256:afc9e9c83309c262747a03596b0c9da9d16181fed545310f979012536298d37f
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
        - ADR-060#6
        - COR-050#3
        - COR-009
        - ADR-061#3
        - PRJ-002#D1
        - PRJ-002#D2
        - COR-050#6
        - COR-050#9
        - COR-051#4
        - COR-066#1
        - COR-066#2
        - COR-001
        - COR-010
        - COR-053#8
        - COR-059#3
---

# REQ-050 · Functional · An agent proposes what the analysis records, and a person decides it

**Verified by:** Tests of the [agent definition](../../../core/glossary.md#term-agent-definition--agent-definition) find that it grants Read, Glob, Grep, Bash and Write alone, and owns no path. They find that it gives each command that writes to the person, with no consent flag. In a session, nothing at run time confines the agent's Write to the agent workspace (ADR-060 point 6). No test holds what the [skill](../../../core/glossary.md#term-skill--skill) asks of an agent, and no test runs an agent.

**Rationale:** Whether a [change](../../../core/glossary.md#term-change--change) was meant is a question of intent, and where intent is unclear only a person knows ([DEC-001 point 5](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#5-revalidation)). On a [project](../../../core/glossary.md#term-project--project) that has code, documents and decisions already, a person confirms the [candidates](../../glossary.md#term-candidate--candidate) ([DEC-001 point 9](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#9-brownfield-onboarding)). Only the project frees an id, and no tool infers one ([DEC-001 point 3](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#3-identifiers)). The parts of each artefact kind and of the revalidation record's kind are the project's own choice as it adopts the [capability](../../../core/glossary.md#term-capability--capability) ([DEC-001 point 1](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape)).
