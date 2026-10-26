---
id: ACT-planning-agent
name: Planning agent
status: active
summary: "An AI agent of a topology that slices a project's work and files it for the other agents, and builds none of it."
needs:
  - Plan my planner's intent into Tasks that one agent can each finish, ordered where one Task needs another's work.
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/skills/pm/batch-plan.md
      record:
        - project-management:DEC-029
        - project-management:DEC-008
        - project-management:DEC-059#7
---

# ACT-planning-agent — Planning agent

An AI agent of a topology that slices a project's work and files it for the other agents, and builds none of it. It plans on the planner's direction, and files nothing before the planner approves the plan ([DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)). It files the work with no [owner](../../glossary.md#term-owner--owner), so the work joins the ready Tasks that every [seat](../../glossary.md#term-seat--seat) shares ([DEC-059 point 7](../../../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md#7-work-reaches-agents-through-one-shared-pool)).

**Role holders:** an agent that follows the `pm` [skill](../../../core/glossary.md#term-skill--skill)'s `batch-plan` procedure, such as the project-manager agent ([DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).

**Occasions:** whenever the planner gives it an intent to plan.

**Context:** the planner's intent, the [topology](../../glossary.md#term-topology--topology)'s scopes, and the [project](../../../core/glossary.md#term-project--project)'s use cases where the project keeps them ([DEC-054](../../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md)).

**Note:** it is not the planner, the person whose intent it plans and who approves its plan ([DEC-008](../../../../../.pkit/capabilities/project-management/decisions/DEC-008-pm-and-implementer-roles.md)). It is an AI agent (`core:ACT-ai-agent`) with its own job in a [topology](../../glossary.md#term-topology--topology).
