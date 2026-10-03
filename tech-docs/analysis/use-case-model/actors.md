---
ACT-clone-session:
  name: Clone session
  status: active
  needs:
    - Work out where it was and where it was heading from the tracker and its clone's instance id alone.
    - Tell its own work from other clones' work, and find work that is free to pick.
    - Know whether a stabilisation is on before it starts or lands anything.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/agents/project-manager/project-manager.md
          - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
        record:
          - project-management:DEC-029
          - project-management:DEC-035
      revalidated:
        at: 2026-10-03T01:47:00Z
        outcome: unchanged
        unchanged-because: The project-manager's batch planning gains a use-case walk before it slices, and DEC-029's sub-procedure names that step and what the approval gate shows; who the clone session is and what it needs from the tracker — its position, its own work apart from other clones', whether a stabilisation is on — are untouched.
ACT-developer-subagent:
  name: Developer subagent
  status: active
  needs:
    - Carry out one delegated Task in its own worktree, and act as its clone whenever it touches the tracker.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-engineering/agents/software-engineer.md
      revalidated:
        at: 2026-09-30T23:14:25Z
        outcome: unchanged
        unchanged-because: The software-engineer gains one line on handling review findings (fix the blocking ones, record advisories in the PR body); the subagent still carries out one delegated Task in its worktree and acts as its clone at the tracker, which is all this actor states.
ACT-operator:
  name: Operator
  status: active
  needs:
    - Never lose the direction of the work in any clone, even when every session has died.
    - See from any clone, in seconds, what every clone holds, where each is heading and whether a stabilisation is on.
    - Cut a release while unfinished work exists, with only release scope reaching the default branch.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/set-instance.py
        record:
          - project-management:DEC-035
          - project-management:DEC-045
      revalidated:
        at: 2026-09-30T23:02:10Z
        outcome: unchanged
        unchanged-because: "#840's lint and format pass reshapes the anchored code without changing what it does, so this page still describes it as it is"
---

# Actors

Who uses the system, and what each needs from it. Each actor's id is stable; its name may change.

## ACT-clone-session — Clone session

An agent session working in one clone, which it knows by the clone's instance id. In project-kit it is usually the project-manager agent booted in that clone (project-management DEC-029), which files, starts, pauses and lands work through the work-tracking commands. Any session in the clone counts, though: one authoring a decision record through the `decision-author` skill, say (UC-006).

It can be killed at any moment — by the operator, by the harness, by a crash. What it knew only in its own context dies with it. What it wrote to the tracker, and the clone's instance id, survive.

## ACT-developer-subagent — Developer subagent

A helper session that a clone session dispatches to implement one Task. In project-kit it is the software-engineering capability's software-engineer agent, the anchor above. No record decides how a clone session delegates development to it: that is practice today, not a decision. It usually runs in an isolated worktree of the clone, writes and commits code, and may push the branch and open the pull request.

It does not plan: the clone session that dispatched it owns the Task's position and direction. Its session ends when it hands back its result, or when the session that dispatched it dies.

## ACT-operator — Operator

The person who runs several clones of one repository, each with its own agent session, and directs them. They set each clone's instance id once, start and restart sessions, stabilise a Milestone when a release is near, decide what to defer, and cut the release. In project-kit this is the maintainer.

They are one tracker account across all their clones, so the tracker's assignee alone cannot tell their clones apart (project-management DEC-035).
