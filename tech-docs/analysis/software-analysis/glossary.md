---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-artefact, name: artefact}
      - {id: TERM-change, name: change}
      - {id: TERM-project, name: project}
      - {id: TERM-system, name: system}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Revise the analysis before a proposed change is built, naming the design I reviewed and pinning the text I read.
          - Revalidate the analysis after a change, from an agent's proposed outcome for each flagged artefact, and never rewrite the analysis to match broken code.
          - Describe my existing project from its code, documents and decisions, with an agent deriving candidates that I confirm.
          - Free the ids of artefacts nothing cites, such as an abandoned pilot, so new artefacts may take those ids again.
      - id: ACT-adopter
        name: Adopter
        needs:
          - Choose the parts of each kind of analysis artefact as I adopt software analysis, keeping, relabelling or adding to the shipped ones.
TERM-use-case:
  name: use case
  noun-forms: [use cases]
  status: active
  definition: "description of how the system fulfils one actor's goal, in a main path of steps and the variants that branch from it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/schemas/use-case.schema.json
        record:
          - software-analysis:DEC-001#1
          - software-analysis:DEC-001#3
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than software-analysis's floor, 1.149.0.
  - **Term:** [artefact](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-artefact--artefact)
  - **Term:** [change](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change--change)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [system](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-system--system)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Revise the analysis before a proposed change is built, naming the design I reviewed and pinning the text I read.
    - Revalidate the analysis after a change, from an agent's proposed outcome for each flagged artefact, and never rewrite the analysis to match broken code.
    - Describe my existing project from its code, documents and decisions, with an agent deriving candidates that I confirm.
    - Free the ids of artefacts nothing cites, such as an abandoned pilot, so new artefacts may take those ids again.
  - **Actor:** [Adopter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-adopter.md)
    - Choose the parts of each kind of analysis artefact as I adopt software analysis, keeping, relabelling or adding to the shipped ones.

## TERM-use-case — use case

**Example:** the core's UC-014 says how the methodology maintainer develops the methodology in its source repository, with variant 2c for a pin the system refuses.

**Distinctions:**

- **Journey:** one actor's path across several use cases, with the seams between them where the path can break (DEC-001 point 1).
- **User story:** a need in one sentence. It is an actor's need and a use case's goal, never an artefact of its own (DEC-001 point 1).
- **Step and variant:** a numbered part of a use case's main path, and a lettered branch from one step. Neither is ever renumbered or removed (DEC-001 point 3).
