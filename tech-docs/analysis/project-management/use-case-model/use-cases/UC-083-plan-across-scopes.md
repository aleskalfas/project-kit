---
id: UC-083
title: Plan an intent into work for each scope of the topology
status: active
actor: ACT-planning-agent
other-actors:
  - ACT-planner
  - ACT-worker-agent
  - ACT-lead-agent
requirements:
  - REQ-040
  - REQ-041
after:
  - [UC-082]
  - [UC-064]
shortfalls:
  - at: 8
    issue: "#519"
    record: project-management:DEC-035#3
  - at: "1a"
    issue: "#519"
    record: project-management:DEC-035#3
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/skills/pm/batch-plan.md
        - .pkit/capabilities/project-management/scripts/create-issue.py
      record:
        - project-management:DEC-029
        - project-management:DEC-054#5
        - project-management:DEC-005
        - project-management:DEC-012
        - project-management:DEC-018
        - project-management:DEC-035#1
        - project-management:DEC-035#3
        - project-management:DEC-045#3
        - project-management:DEC-045#5
        - COR-013
        - COR-017
      artefact:
        - ACT-planning-agent
        - ACT-planner
        - ACT-worker-agent
        - ACT-lead-agent
        - REQ-040
        - REQ-041
---

# UC-083 — Plan an intent into work for each scope of the topology

**Goal:** Plan my planner's intent into Tasks that each fall in one scope of the topology, ordered where one scope needs another's work.

**Other actors:**

- **Planner** (`ACT-planner`): approves the whole plan before any [issue](../../glossary.md#term-issue--issue) of it is filed (DEC-029).
- **Worker agent** (`ACT-worker-agent`) and **Lead agent** (`ACT-lead-agent`): take the Tasks of their scopes. Each [Task](../../glossary.md#term-task--task) names the Tasks it waits on, so they never start it too early (`batch-plan.md`).

**Preconditions:**

- **From UC-082:** The [topology](../../glossary.md#term-topology--topology) gives each agent its [scope](../../glossary.md#term-scope--scope), which names [workstreams](../../glossary.md#term-workstream--workstream) (DEC-045 point 3).
- **From UC-064:** The [project](../../../core/glossary.md#term-project--project) declares the workstreams its work falls into (DEC-018).

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has project-management installed, and the adapter deploys the `project-manager` agent and the `pm` [skill](../../../core/glossary.md#term-skill--skill) (COR-013 and COR-017).

**Trigger:** The planner gives the planning agent an intent to plan for the [topology](../../glossary.md#term-topology--topology)'s agents.

**Main path:**

1. The planner gives the planning agent an intent, with its reference material, as `UC-063` step 1 describes.
2. The agent reads the intent, its references and the [project](../../../core/glossary.md#term-project--project)'s use cases, as `UC-063` steps 2 and 3 describe (DEC-054 point 5).
3. The agent slices the intent into an [EPIC](../../glossary.md#term-epic--epic), Features and Tasks, and gives each [Task](../../glossary.md#term-task--task) the [workstream](../../glossary.md#term-workstream--workstream) of the work it does (DEC-012 and DEC-029). The Task then lies in each [scope](../../glossary.md#term-scope--scope) that names that workstream (DEC-045 point 3).
4. Where two Tasks edit the same files, the later one names the earlier in its `## Dependencies` section. It is built once the earlier has merged (`batch-plan.md` and DEC-005).
5. Where a Task needs what a Task of another scope builds, it names that Task in its `## Dependencies` section too (`batch-plan.md` and DEC-005).
6. The agent has the plan reviewed, and shows it to the planner, as `UC-063` steps 5 and 6 describe (DEC-029).
7. The planner approves the plan (DEC-029).
8. The agent files the issues, as `UC-063` steps 8 and 9 describe. Its [instance](../../glossary.md#term-instance--instance) owns each [issue](../../glossary.md#term-issue--issue) it files, the parents and the Tasks alike (DEC-035 point 3). The agent of each scope takes its Tasks over, as `UC-084` variant 2a describes.

> [!WARNING]
> **Not built yet:** `create-issue` writes no [owner](../../glossary.md#term-owner--owner). DEC-035 point 3 decides that the instance that files an issue owns it, and #519 tracks it.

9. The agent reports each issue it filed, with its number, its link and its workstream.

**Variants:**

- **1a.** A lead agent plans the work of its own [scope](../../glossary.md#term-scope--scope), in place of a planning agent. Its [instance](../../glossary.md#term-instance--instance) owns each [issue](../../glossary.md#term-issue--issue) it files, the parents and the Tasks alike, and builds them itself (DEC-035 point 3).

> [!WARNING]
> **Not built yet:** `create-issue` writes no [owner](../../glossary.md#term-owner--owner). DEC-035 point 3 decides that the instance that files an issue owns it, and #519 tracks it.

- **7a.** The planner asks for changes, or cancels the plan, as `UC-063` variants 7a and 7c describe.
- **8a.** The planning agent's clone has set no number. No issue it files has an owner, so the agent of each scope may start its Tasks at once (DEC-035 point 1).

**Postconditions:** Each [Task](../../glossary.md#term-task--task) of the approved plan is filed with the [workstream](../../glossary.md#term-workstream--workstream) of its work. Each Task that waits on another names it in its `## Dependencies` section.

**Minimal guarantees:**

- No [issue](../../glossary.md#term-issue--issue) is filed before the planner approves the whole plan (DEC-029).
- A [Task](../../glossary.md#term-task--task) that edits the same files as an earlier Task names that Task in its `## Dependencies` section (`batch-plan.md`).

## Open for the design

What the planning agent needs here that no accepted record decides yet:

- **How the planning agent reads the topology.** Without it, the agent cannot check that each [workstream](../../glossary.md#term-workstream--workstream) it gives lies in some agent's [scope](../../glossary.md#term-scope--scope), nor name the work that falls in none.
- **How one scope gives another what it needs,** such as an interface two scopes share. A contract between scopes is proposed only, in an unmerged note (draft PR #566). Typed `Blocked by:` lines, and the Tasks ready to start that they give, are DEC-025's, which is proposed.
- **Who owns what the planning agent files.** DEC-035 point 3 makes the filer the [owner](../../glossary.md#term-owner--owner), so each agent of a scope must take over each of its Tasks. DEC-045 point 5 expects instead the [instance](../../glossary.md#term-instance--instance) whose scope names the [Task](../../glossary.md#term-task--task)'s workstream. The [topology](../../glossary.md#term-topology--topology)'s design chooses between them.
- **Work that passes through stages,** such as design, development and testing, where each stage needs the work of the stage before. No record decides how such work is planned.
