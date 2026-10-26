---
id: ACT-planning-agent
name: Planning agent
status: active
summary: "An AI agent of a topology that slices a project's work and files it for the other agents, and builds none of it."
needs:
  - Plan my planner's intent into Tasks that each fall in one scope of the topology, ordered where one scope needs another's work.
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/skills/pm/batch-plan.md
      record:
        - project-management:DEC-029
        - project-management:DEC-008
---

# ACT-planning-agent — Planning agent

An AI agent of a topology that slices a project's work and files it for the other agents, and builds none of it. It plans on the planner's direction, and files nothing before the planner approves the plan (DEC-029).

**Role holders:** an agent that follows the `pm` [skill](../../../core/glossary.md#term-skill--skill)'s `batch-plan` procedure, such as the project-manager agent (DEC-029).

**Occasions:** whenever the planner gives it an intent to plan.

**Context:** the planner's intent, the [topology](../../glossary.md#term-topology--topology)'s scopes, and the [project](../../../core/glossary.md#term-project--project)'s use cases where the project keeps them (DEC-054).

**Note:** it is not the planner, the person whose intent it plans and who approves its plan (DEC-008). It is an AI agent (`core:ACT-ai-agent`) with its own job in a [topology](../../glossary.md#term-topology--topology).
