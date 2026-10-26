---
id: ACT-lead-agent
name: Lead agent
status: active
summary: "An AI agent of a topology that plans and builds the work of the agent's scope, delegating Tasks to helper agents the agent starts."
needs:
  - Plan and build the work of my scope, and leave every other scope's work to that scope's own agent.
  - Delegate a Task of my scope to a helper agent, which acts as my instance while the helper agent builds the Task.
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-029
        - project-management:DEC-035#3
        - project-management:DEC-008
---

# ACT-lead-agent — Lead agent

An AI agent of a topology that plans and builds the work of the agent's scope, delegating Tasks to helper agents the agent starts. The lead agent's [instance](../../glossary.md#term-instance--instance) owns the work the lead agent files ([DEC-035 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md#3-a-clone-claims-at-creation-for-the-whole-tree)).

**Role holders:** an AI agent that plans and builds through the `pm` [skill](../../../core/glossary.md#term-skill--skill), such as the project-manager agent ([DEC-008](../../../../../.pkit/capabilities/project-management/decisions/DEC-008-pm-and-implementer-roles.md) and [DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).

**Occasions:** whenever its [scope](../../glossary.md#term-scope--scope) holds work to plan or to build.

**Context:**

- its [scope](../../glossary.md#term-scope--scope)
- its [instance](../../glossary.md#term-instance--instance)'s number
- the harness's limit on how deep agents may start further agents ([DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md))

**Note:**

- One session that starts helper agents for all of a [project](../../../core/glossary.md#term-project--project)'s work is one lead agent whose [scope](../../glossary.md#term-scope--scope) is the whole project. project-kit's own work ran that way in October 2026.
- The lead agent is an AI agent (`core:ACT-ai-agent`) with its own job in a [topology](../../glossary.md#term-topology--topology), as the other agents of a topology are.
