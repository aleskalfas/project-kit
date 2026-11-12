---
id: ACT-project-management
name: Project management
status: active
summary: "The project-management capability, where installed, which starts the analysis-resolver agent the project granted, in a run nobody can answer the agent during."
needs:
  - Have the agent the project granted propose an answer for each stale artefact of the analysis, with nobody to ask.
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/fix-drift.py
      record:
        - software-analysis:DEC-001#2
        - software-analysis:DEC-001#5
        - software-analysis:DEC-001#8
        - software-analysis:DEC-001#10
        - project-management:DEC-056#2
        - project-management:DEC-056#3
        - project-management:DEC-056#6
---

# ACT-project-management — Project management

The project-management capability, where installed, which starts the analysis-resolver agent the project granted, in a run nobody can answer the agent during. It is an actor because it triggers the [analysis](../../glossary.md#term-analysis--analysis)'s own agent on its own occasion ([DEC-001 point 2](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#2-where-it-keeps-them)).

**Occasions:** whenever a person runs its drift command at a terminal, on one commit of the [default branch](../../../core/glossary.md#term-default-branch--default-branch) ([project-management DEC-056 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-056-drift-fixers.md#3-a-command-starts-the-granted-fixers)).

**Context:**

- the [artefacts](../../../core/glossary.md#term-artefact--artefact) the [whole-repository check](../../../core/glossary.md#term-whole-repository-check--whole-repository-check) finds stale at that commit ([project-management DEC-056 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-056-drift-fixers.md#3-a-command-starts-the-granted-fixers))
- whether the [project](../../../core/glossary.md#term-project--project) granted the agent ([project-management DEC-056 point 2](../../../../../.pkit/capabilities/project-management/decisions/DEC-056-drift-fixers.md#2-the-person-grants-each-fixer))
- nobody to reply to a question (project-management DEC-056 point 3)

**Place in the model:** it takes part in [UC-073](../use-cases/020-revalidate/UC-073-revalidate-after-change.md), whose goal stays the developer's. Each [answer](../../../core/glossary.md#term-answer--answer) it holds waits until a person decides it ([DEC-001 point 5](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#5-revalidation)).

**Note:** software-analysis works without it, since the dependency on project-management is optional ([DEC-001 point 10](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#10-independent)).
