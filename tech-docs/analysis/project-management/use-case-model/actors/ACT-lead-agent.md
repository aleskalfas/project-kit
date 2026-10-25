---
id: ACT-lead-agent
name: Lead agent
status: active
summary: "An AI agent of a topology that plans and builds the work of its scope, delegating Tasks to agents it starts itself."
needs:
  - Plan and build the work of my scope, and leave every other scope's work to its own agent.
  - Delegate a Task of my scope to an agent I start, which acts as my instance while it builds the Task.
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-029
        - project-management:DEC-035#3
        - project-management:DEC-008
---

# ACT-lead-agent — Lead agent

An AI agent of a topology that plans and builds the work of its scope, delegating Tasks to agents it starts itself. Its [instance](../../glossary.md#term-instance--instance) owns the work it files (DEC-035 point 3).

**Role holders:** an AI agent that plans and builds through the `pm` [skill](../../../core/glossary.md#term-skill--skill), such as the project-manager agent (DEC-008 and DEC-029).

**Occasions:** whenever its [scope](../../glossary.md#term-scope--scope) holds work to plan or to build.

**Context:** its [scope](../../glossary.md#term-scope--scope), its [instance](../../glossary.md#term-instance--instance)'s number, and the harness's limit on how deep agents may start further agents (DEC-029).

**Note:** one session that starts agents for all of a [project](../../../core/glossary.md#term-project--project)'s work is one lead agent whose [scope](../../glossary.md#term-scope--scope) is the whole project. project-kit's own work ran that way in October 2026. Like the other agents of a [topology](../../glossary.md#term-topology--topology), it is an AI agent (`core:ACT-ai-agent`) with a part of its own.
