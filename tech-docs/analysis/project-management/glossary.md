---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-change, name: change}
      - {id: TERM-pull-request, name: pull request}
      - {id: TERM-reviewer, name: reviewer}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - File a Task under its parent, with its title and the sections its body needs checked as it is filed.
          - Move my issue through its lifecycle, with each move checked and the moves that need my authorisation never made without it.
          - Have the reviewer agents my change requires review my pull request, each verdict standing only while I change nothing its reviewer checks.
TERM-epic:
  name: EPIC
  noun-forms: [EPICs]
  status: active
  definition: "issue that states an outcome spanning several quarters, under which the work that delivers it is filed"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/issue-types.yaml
        record:
          - project-management:DEC-004
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than project-management's floor, 1.144.0.
  - **Term:** [change](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change--change)
  - **Term:** [pull request](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-pull-request--pull-request)
  - **Term:** [reviewer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-reviewer--reviewer)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - File a Task under its parent, with its title and the sections its body needs checked as it is filed.
    - Move my issue through its lifecycle, with each move checked and the moves that need my authorisation never made without it.
    - Have the reviewer agents my change requires review my pull request, each verdict standing only while I change nothing its reviewer checks.

## TERM-epic — EPIC

**Example:** #1643 is an EPIC, and #1890 is filed under it, since its body opens `EPIC: #1643`.

**Distinctions:**

- **Milestone:** a container of the hosting service bound to a date. An EPIC sits directly under one, and never deeper (DEC-004).
- **Feature:** an issue for a cluster of Tasks that delivers one coherent outcome, with acceptance criteria. It sits under an EPIC, or straight under a Milestone where the project skips the EPIC (DEC-004).
- **Umbrella:** an issue for related Tasks that share a theme, with no acceptance criteria (DEC-004).
