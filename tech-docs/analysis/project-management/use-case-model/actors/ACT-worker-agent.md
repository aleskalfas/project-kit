---
id: ACT-worker-agent
name: Worker agent
status: active
summary: "An AI agent of a topology that takes ready Tasks one at a time, and builds each up to its merge."
needs:
  - Take my next ready Task, one that no other agent works on, and build it up to its merge.
  - Never work on a Task that another agent already works on.
  - Hand the next piece of the work to the scope that does that piece, with what that piece needs from my piece.
  - Take up my instance's work in flight after my session died, without losing what that session had done.
  - Land my finished Task on the default branch while other agents land theirs, each merge judged at its own head.
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-026
        - project-management:DEC-035#3
        - project-management:DEC-008
---

# ACT-worker-agent — Worker agent

An AI agent of a topology that takes ready Tasks one at a time, and builds each up to its merge. The worker agent plans nothing beyond the [Task](../../glossary.md#term-task--task) it builds.

**Role holders:** an AI agent that follows the `pm` [skill](../../../core/glossary.md#term-skill--skill) on a developer's direction, such as the project-manager agent ([DEC-008](../../../../../.pkit/capabilities/project-management/decisions/DEC-008-pm-and-implementer-roles.md) and [DEC-029](../../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).

**Occasions:**

- whenever a [Task](../../glossary.md#term-task--task) it can start waits in Backlog
- each time a new session of the worker agent starts after the last session ended

**Context:**

- its [seat](../../glossary.md#term-seat--seat), and the seat's [scope](../../glossary.md#term-scope--scope) where the seat has a scope
- its [instance](../../glossary.md#term-instance--instance)'s number
- the Tasks in Backlog

**Note:** the worker agent is an AI agent (`core:ACT-ai-agent`) with its own job in a [topology](../../glossary.md#term-topology--topology). The worker agent does for a [Task](../../glossary.md#term-task--task) what the developer does, through the same commands ([DEC-008](../../../../../.pkit/capabilities/project-management/decisions/DEC-008-pm-and-implementer-roles.md) and [DEC-026](../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)). The developer's use cases give those steps, such as `UC-061` and `UC-062`. A lead agent does the same within its own [scope](../../glossary.md#term-scope--scope), and plans too.
