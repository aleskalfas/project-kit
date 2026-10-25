---
id: ACT-worker-agent
name: Worker agent
status: active
summary: "An AI agent of a topology that takes the Tasks of its scope one at a time, and builds each up to its merge."
needs:
  - Take my next Task from my scope, one that no other agent works on, and build it up to its merge.
  - Never work on a Task that another agent already works on.
  - Hand the next part of the work to the scope that does it, with what that part needs from mine.
  - Take up my instance's work in flight after my session died, without losing what it had done.
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

An AI agent of a topology that takes the Tasks of its scope one at a time, and builds each up to its merge. It plans nothing beyond the [Task](../../glossary.md#term-task--task) it builds.

**Role holders:** an AI agent that follows the `pm` [skill](../../../core/glossary.md#term-skill--skill) on a developer's direction, such as the project-manager agent (DEC-008 and DEC-029).

**Occasions:**

- whenever its [scope](../../glossary.md#term-scope--scope) holds a [Task](../../glossary.md#term-task--task) it can start
- each time one of its sessions starts again after the last one ended

**Context:** its [scope](../../glossary.md#term-scope--scope), its [instance](../../glossary.md#term-instance--instance)'s number, and the Tasks filed in its scope.

**Note:** it is an AI agent (`core:ACT-ai-agent`) with a part of its own in a [topology](../../glossary.md#term-topology--topology). It does for a [Task](../../glossary.md#term-task--task) what the developer does, through the same commands (DEC-008 and DEC-026). The developer's use cases give those steps, such as `UC-061` and `UC-062`. A lead agent does the same within its own [scope](../../glossary.md#term-scope--scope), and plans too.
