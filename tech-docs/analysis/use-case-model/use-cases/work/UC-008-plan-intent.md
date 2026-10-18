---
id: UC-008
title: Plan an intent into an EPIC and its tasks
status: active
actor: ACT-planner
other-actors:
  - ACT-ai-agent
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/agents/project-manager/project-manager.md
        - .pkit/capabilities/project-management/skills/pm/batch-plan.md
        - .pkit/capabilities/project-management/scripts/create-issue.py
        - .pkit/capabilities/project-management/scripts/edit-issue.py
        - .pkit/capabilities/project-management/scripts/decline-use-case-task.py
        - .pkit/capabilities/project-management/scripts/_lib/use_case_task.py
        - .pkit/capabilities/project-management/scripts/_lib/use_case_citations.py
        - .pkit/capabilities/software-analysis/scripts/fill-use-cases.py
        - .pkit/rules/core.md
      record:
        - project-management:DEC-008
        - project-management:DEC-029
        - project-management:DEC-054#3
        - project-management:DEC-054#4
        - project-management:DEC-054#5
        - project-management:DEC-006
        - project-management:DEC-010
        - software-analysis:DEC-001#8
        - COR-024
      artefact:
        - ACT-planner
        - ACT-ai-agent
---

# UC-008 — Plan an intent into an EPIC and its tasks

**Goal:** Plan an intent against my project's use cases into an EPIC and its work, which are filed once I approve the plan.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): the `project-manager` agent plans and files on the planner's direction. The `critic`, and for a wide plan the `architect`, review the slicing and never veto it (project-management DEC-029 and COR-024).

**Preconditions:** The project tracks its work in GitHub issues through project-management, which has deployed the `project-manager` agent.

**Assumptions:**

- Only the planner commits the project to an outcome, so an EPIC is filed on the planner's authority (project-management DEC-008). No script checks who asks for an EPIC. The `project-manager` agent refuses a developer who asks to file one alone.
- The agent files nothing before the planner approves the plan (project-management DEC-029 and the `pm` skill's `batch-plan`). Nothing at run time holds the agent to it, since `create-issue` files on `--yes`.
- The agent decides the slicing, the order, the dependencies, each issue's classification and the use cases it serves. The planner corrects them at the gate (project-management DEC-029 and DEC-054 point 5).
- Scheduling an issue is the planner's decision, given per issue and in the session. The agent acts on no standing authorisation across sessions (project-management DEC-006 and the `project-manager` agent).
- The agent writes no use case. It plans their authoring as work (project-management DEC-054 point 5).
- The planner is asked one decision at a time, with the agent's recommendation (core rule 17).

**Trigger:** The planner states an intent, with the reference material that frames it, such as a scratchpad note.

**Main path:**

1. The planner asks the `project-manager` agent to plan the intent.
2. The agent reads the use cases settled on the default branch, with `pkit connections resolve pkit::work-tracking:use-cases --json`. In project-kit, software-analysis's `fill-use-cases` answers it (software-analysis DEC-001 point 8).
3. The agent walks the active use cases against the intent, and reads each one's document where its entry gives a `path` (project-management DEC-054 point 5).
4. The agent slices the intent into an EPIC and the Features and Tasks under it, with the dependencies between them. Each Feature and Task that serves a use case names it, in a `## Use cases` section.
5. The agent has the plan reviewed (project-management DEC-029):
   - by the `critic`, for three issues or more
   - by the `architect` too, where the plan touches three components or more, or adds an abstraction
6. The agent shows the plan at one approval gate: its issues, their dependencies, the reviewers' findings and the use cases each issue serves. The plan also shows both kinds of gap:
   - a use case the intent touches that no planned issue names
   - behaviour the plan builds that no use case describes
7. The planner approves the plan.
8. The agent files the issues, parents first, each with `create-issue.py` and then its planned body with `edit-issue.py --body-file <file> --yes`. Each body is validated as it is written (project-management DEC-010).

**Variants:**

- **2a.** Nothing defines or fills the use-case point. The plan says nothing of use cases, and the path goes on at step 4 (project-management DEC-054 point 3).
- **2b.** The point cannot be read, such as in a clone that has not fetched the default branch. The plan says the use cases could not be read, and why. The agent never reads the unread point as an empty set, and the path goes on at step 4 (project-management DEC-054 points 3 and 5).
- **2c.** The point answers without a filler that was meant to answer. The agent walks the use cases it holds, and the plan names the filler that did not answer. Behaviour no held use case describes is shown as a possible gap, and the path goes on at step 4.
- **3a.** No use case has settled yet, and some planned work touches what users do. The plan includes a Task to author the use cases first. Only the issues that touch what users do depend on that Task. They state their goals as text, and cite no use case (project-management DEC-054 point 5). The path goes on at step 5.
- **3b.** A use case the work needs lies on a branch only, not yet on the default branch. The agent suggests no id for it, since its number may still change before it lands (software-analysis DEC-001 point 3). The path goes on at step 4.
- **3c.** No use case has settled yet, and the planner declined the Task earlier the same day in this checkout. `pkit pm decline-use-case-task --show --json` reads that answer. The plan leaves the Task out, and says when it was declined. The path goes on at step 5.
- **4a.** The intent takes one issue only. The agent files it directly, through the `pm` skill's `create-issue`, with no reviewer (project-management DEC-029). The use case ends.
- **7a.** The planner revises the plan. The agent slices again, and runs the reviewers again where the revision is not trivial. Nothing is filed in any revision, and the path rejoins at step 6.
- **7b.** The planner revises the Task to author the use cases away. The agent runs `pkit pm decline-use-case-task` before filing, so plans from this checkout leave the Task out for the rest of the day. The plan's topmost new issue says in prose that it was planned without use cases (project-management DEC-054 point 5). The path goes on at step 8.
- **7c.** The planner cancels the plan. The agent says `Cancelled. Nothing filed.`, keeps nothing, and the use case ends.
- **8a.** `edit-issue.py` refuses a body over a rule it breaks: `[refused] validation surfaced hard-reject findings. Pass --force to write anyway (records an audit comment).` The issue is filed already, with its template body. The agent names the rule, proposes a fix, and waits for the planner. The path rejoins at step 8 for that body.
- **8b.** `edit-issue.py` warns that a body cites a use case the point does not hold, such as a mistyped id. The warning never refuses the edit (project-management DEC-054 point 4). The agent fixes or drops the id, and runs `edit-issue.py` again.

**Postconditions:** The EPIC and its issues are filed as the planner approved them, each with its planned body. Each Feature and Task that serves a settled use case names it.

**Minimal guarantees:**

- A use-case point that cannot be read is never taken for an empty set. A citation is then reported as not checked, never as unknown. No Task to author use cases follows from it (project-management DEC-054 point 3, and `use_case_citations.py`).
- A use-case citation never stops a filing or an edit (project-management DEC-054 point 4).
- `edit-issue.py` writes no body with a hard-reject finding over an issue, unless `--force` is given, which posts an audit comment (`edit-issue.py`).
- `create-issue.py` files no issue whose title, workstream, parent's type or kind its rules refuse (`create-issue.py`).
- A declined answer that cannot be read hides nothing, so the Task to author use cases is offered (project-management DEC-054 point 5, and `use_case_task.py`).
