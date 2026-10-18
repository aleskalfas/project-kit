---
id: ACT-planner
name: Planner
status: active
needs:
  - Plan an intent into an EPIC and its tasks against my project's use cases, and have them filed once I approve the plan.
  - Group the work into milestones and long-lived workstreams, and have a milestone that closes on its date roll its open work forward.
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-008
        - project-management:DEC-029
        - project-management:DEC-054#5
        - project-management:DEC-016
        - project-management:DEC-018
---

# ACT-planner — Planner

The person who plans a project's work at the level of its outcomes. An EPIC is filed only on their authority.

- **Human role:** only a person may commit the project to an outcome. The project-manager agent plans and files on their direction, and files a whole plan only once they approve it (project-management DEC-008 and DEC-029).
- **Occasions:** when an outcome is framed or work is scheduled, and as a milestone nears its close.
- **Context:** an intent, and the reference material that frames it, such as a scratchpad note or a related issue.
- **Note:** the role's id and name are not "project manager". That is the name of project-management's agent, which acts for this role and for the developer (DEC-029). project-management calls this role the PM (DEC-008).
