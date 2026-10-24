---
id: ACT-planner
name: Planner
status: active
summary: "The person who plans a project's work at the level of its outcomes."
needs:
  - Plan an intent against my project's use cases into an EPIC and its work, which are filed once I approve the plan.
  - Define the Milestones and long-lived workstreams the work falls into, and have a date-based Milestone roll its open work forward when it closes.
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-008
        - project-management:DEC-029
        - project-management:DEC-054#5
        - project-management:DEC-016
        - project-management:DEC-018
    revalidated:
      at: 2026-10-23T08:53:49Z
      outcome: unchanged
      unchanged-because: It moved into project-management's analysis with its id, its anchors and every word, since only project-management meets its needs. The role and its needs hold.
---

# ACT-planner — Planner

The person who plans a project's work at the level of its outcomes. An [EPIC](../../glossary.md#term-epic--epic) is filed only on their authority.

- **Human role:** only a person may commit the [project](../../../core/glossary.md#term-project--project) to an outcome. The project-manager agent plans and files on their direction, and files a whole plan only once they approve it (project-management DEC-008 and DEC-029).
- **Occasions:**
  - when an outcome is framed
  - when work is scheduled
  - as a date-based [Milestone](../../glossary.md#term-milestone--milestone) nears its due date
- **Context:** an intent, and the reference material that frames it, such as a scratchpad note or a related [issue](../../glossary.md#term-issue--issue).
- **Note:** the planner comes with project-management, which calls it the PM (DEC-008). Its id and name are not `project-manager`, which is the name of project-management's agent. That agent acts for the planner and for the developer (DEC-029). An actor's id is permanent once stamped, so this one names the planner alone.
