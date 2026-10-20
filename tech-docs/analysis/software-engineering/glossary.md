---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-adapter, name: adapter}
      - {id: TERM-agent-definition, name: agent definition}
      - {id: TERM-anchor, name: anchor}
      - {id: TERM-answer, name: answer}
      - {id: TERM-artefact, name: artefact}
      - {id: TERM-capability, name: capability}
      - {id: TERM-change, name: change}
      - {id: TERM-decision-record, name: decision record}
      - {id: TERM-finding, name: finding}
      - {id: TERM-methodology, name: methodology}
      - {id: TERM-project, name: project}
      - {id: TERM-pull-request, name: pull request}
      - {id: TERM-reviewer, name: reviewer}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Build my change with an agent that writes the change's code to my project's own conventions, read from wherever I keep them.
      - id: ACT-ai-agent
        name: AI agent
TERM-conventions-corpus:
  name: conventions corpus
  status: active
  definition: set of a project's own coding standards, kept where the project names it, which the agents that write and review its code read
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-engineering/agents/software-engineer.md
        record:
          - software-engineering:DEC-001#2
          - software-engineering:DEC-001#4
          - software-engineering:DEC-002#4
          - ADR-013
          - COR-001
          - COR-010
      revalidated:
        at: 2026-10-20T01:37:23Z
        outcome: unchanged
        unchanged-because: It moved into software-engineering's analysis, whose use case UC-001 alone uses it, with its definition, example and distinctions as they were. It gains COR-001 and COR-010, the records behind the core's term project, which its definition names.
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than software-engineering's floor, 1.0.0.
  - **Term:** [adapter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-adapter--adapter)
  - **Term:** [agent definition](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-agent-definition--agent-definition)
  - **Term:** [anchor](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-anchor--anchor)
  - **Term:** [answer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-answer--answer)
  - **Term:** [artefact](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-artefact--artefact)
  - **Term:** [capability](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-capability--capability)
  - **Term:** [change](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change--change)
  - **Term:** [decision record](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-decision-record--decision-record)
  - **Term:** [finding](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-finding--finding)
  - **Term:** [methodology](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-methodology--methodology)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [pull request](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-pull-request--pull-request)
  - **Term:** [reviewer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-reviewer--reviewer)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Build my change with an agent that writes the change's code to my project's own conventions, read from wherever I keep them.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)

## TERM-conventions-corpus — conventions corpus

**Example:** the `software-engineer` agent reads the conventions corpus before it writes a change's code, and checks its own diff against it.

**Distinctions:**

- **The methodology's conventions:** conventional commits, branch names and the no-shared-files invariant, which bind every project. The `convention-compliance-reviewer` checks them, and never reads the corpus (software-engineering DEC-001 point 4).
- **The reviewers' knowledge:** what each code-review agent knows of any project. The project's own rules come from the corpus alone (software-engineering DEC-002 point 4).
