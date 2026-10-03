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
        - .pkit/capabilities/project-management/scripts/start-work.py
      record:
        - project-management:DEC-035
        - software-engineering:DEC-001
      artefact:
        - ACT-clone-session
        - ACT-developer-subagent
    revalidated:
      at: 2026-10-03T13:24:10Z
      outcome: unchanged
      unchanged-because: The software-engineer gains a section on answering the friction its own change owes; how the clone session starts the Task, dispatches the subagent and takes back its committed and pushed work is untouched, so the use case holds.
---

# UC-009 — Delegate a task to a developer subagent

**Goal:** A clone session hands a Task to a developer subagent, and neither the work's direction nor its ownership is lost if either session dies.

**Starts when:** A clone session decides to have a developer subagent implement a Task.

**Main path:**

1. The clone session starts the Task (`start-work --next`): the Task becomes this clone's and in progress, with an intent note saying where it is heading.
2. It dispatches the developer subagent with the Task, usually into an isolated worktree of the clone.
3. The subagent writes and commits the code on the Task's branch, and pushes it.
4. Whenever the subagent touches the tracker — to open the pull request, say — it acts as its clone: ownership and the guards apply as they do in the clone (gap J).
5. The subagent hands back its result; the clone session reviews it and moves the Task on.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **2a.** The clone session dies while the subagent works, and the subagent's session ends with it. A new clone session finds the Task in flight with its intent note (UC-001); pushed commits are on the branch, and commits made in the worktree stay in the clone's repository.
- **3a.** The subagent is interrupted before it pushes. Its commits stay in the worktree and its uncommitted work is lost; the intent note still gives the direction.
- **4a.** A stabilisation is on. The same guards hold the subagent's landing as the clone session's (UC-007).

**Done when:** The Task's work is on its branch or merged, and its ownership and latest intent note are its clone's — whichever session did the work.

**Design:** Situation S9 of the coordination design walk. Built today: the software-engineer agent the clone session dispatches (software-engineering DEC-001), and the clone-local instance id (DEC-035) — which a worktree does not see today, since it is read from a git-ignored file under the working tree's own root. No record decides how a clone session delegates a Task to a developer subagent: that is practice today, not a decision, so step 2 has no record anchor. Intended, not built yet: `start-work --next` is EPIC #943's (F1), in `start-work.py`; one instance id for every worktree of a clone is #1140, under EPIC #508, in `_lib/instance_identity.py`. Both paths are anchored here.

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **J, at step 4.** The instance id is read from a git-ignored file under the working tree's own root, and an isolated worktree has none, so tracker commands a subagent runs there act as a clone that never opted in: no claim, no clash guard, and work it starts missing from its clone's position. Proposed fix (pending authorisation; carried by #1140, under EPIC #508): a worktree inherits its clone's instance id through git's common directory. Open: whether a worktree's own id file wins, so that a worktree may act as an instance of its own (#1140 proposes it does). Either way it refines DEC-035 point 1, which makes the id clone-local.
