---
id: UC-009
title: Delegate a task to a developer subagent
status: active
actor: ACT-clone-session
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/agents/project-manager/project-manager.md
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
        - .pkit/capabilities/software-engineering/agents/software-engineer.md
      record:
        - project-management:DEC-029
        - project-management:DEC-035
        - software-engineering:DEC-001
      artefact:
        - ACT-clone-session
        - ACT-developer-subagent
---

# UC-009 — Delegate a task to a developer subagent

**Goal:** A clone session hands a Task to a developer subagent, and neither the work's direction nor its ownership is lost if either session dies.

**Starts when:** A clone session decides to have a developer subagent implement a Task.

**Main path:**

1. The clone session starts the Task (`start-work --next`): the Task becomes this clone's and in progress, with an intent note saying where it is heading.
2. It dispatches the developer subagent with the Task, usually into an isolated worktree of the clone.
3. The subagent writes and commits the code on the Task's branch, and pushes it.
4. Whenever the subagent touches the tracker — to open the pull request, say — it acts as its clone: the worktree reads the clone's instance id, so ownership and the guards apply as they do in the clone.
5. The subagent hands back its result; the clone session reviews it and moves the Task on.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **2a.** The clone session dies while the subagent works, and the subagent's session ends with it. A new clone session finds the Task in flight with its intent note (UC-001); pushed commits are on the branch, and commits made in the worktree stay in the clone's repository.
- **3a.** The subagent is interrupted before it pushes. Its commits stay in the worktree and its uncommitted work is lost; the intent note still gives the direction.
- **4a.** A stabilisation is on. The same guards hold the subagent's landing as the clone session's (UC-007).

**Done when:** The Task's work is on its branch or merged, and its ownership and latest intent note are its clone's — whichever session did the work.

**Design:** Situation S9 of the coordination design walk. Built today: the project-manager agent and how it dispatches helpers (project-management DEC-029), the software-engineer agent (software-engineering DEC-001), and the clone-local instance id (DEC-035) — which a worktree does not see today, since it is read from a git-ignored file under the working tree's own root. Intended, not built yet — EPIC #943: `start-work --next`, and one instance id for every worktree of a clone.
