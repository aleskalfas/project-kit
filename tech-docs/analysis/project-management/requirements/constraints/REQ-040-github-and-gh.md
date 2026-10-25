---
id: REQ-040
title: project-management works on GitHub alone, through an authenticated gh
status: active
statement: "project-management reads and changes a project's work only on GitHub, through `gh` authenticated for the project's host."
measure: "Each command reaches the project's issues and pull requests on GitHub alone, through `gh` or the backbone's commands for pull requests. The prerequisite check fails where `gh auth status` reports no authenticated host."
applies-to: "Every command of project-management, its skill and its agents, wherever a project runs them."
actors:
  - core:ACT-developer
  - ACT-planner
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/pre-check.py
      record:
        - project-management:DEC-003
      artefact:
        - ACT-planner
---

# REQ-040 · Constraint · project-management works on GitHub alone, through an authenticated gh

**Verified by:** The prerequisite check, `pkit pm pre-check`, runs `gh auth status`, and fails where no host is authenticated. No test covers that check, and nothing checks that a command reaches no other tracker.

**Imposed by:** Every [project](../../../core/glossary.md#term-project--project) the [capability](../../../core/glossary.md#term-capability--capability) served when its records were written lived on GitHub. GitHub's issues, sub-issues and [Milestones](../../glossary.md#term-milestone--milestone) carry much of what those records decide. A tracker hidden behind an abstraction would cost a translation at every write, for a switch of tracker nobody has asked for ([DEC-003](../../../../../.pkit/capabilities/project-management/decisions/DEC-003-github-bound-substrate.md)).
