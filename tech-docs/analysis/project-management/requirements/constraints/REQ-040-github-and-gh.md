---
id: REQ-040
title: project-management works on GitHub alone, through an authenticated gh
status: active
statement: "project-management reads and changes a project's work only on GitHub, through `gh` authenticated for the project's host."
measure: "Each command reaches the project's issues and pull requests on GitHub alone, through `gh` or the backbone's commands for pull requests. The prerequisite check fails where `gh auth status` shows no authenticated host."
applies-to: "Every command of project-management, its skill and its agents, wherever a project runs them."
obligation: v1:sha256:d434597d7c5c895bdfbe61406b5f14854ecc1731dac53b5b0fdfd6bcca45c62e
actors:
  - core:ACT-developer
  - ACT-planner
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/pre-check.py
        - tests/test_pm_pre_check_gh_auth.py
      record:
        - project-management:DEC-003
        - project-management:DEC-017
        - project-management:DEC-023
        - ADR-061#1
        - ADR-061#3
        - COR-009
        - PRJ-002#D1
        - PRJ-002#D2
        - COR-050#3
        - COR-050#6
        - COR-050#9
        - COR-051#4
        - COR-066#1
        - COR-066#2
      artefact:
        - ACT-planner
---

# REQ-040 · Constraint · project-management works on GitHub alone, through an authenticated gh

**Verified by:** The prerequisite check, `pkit pm pre-check`, runs `gh auth status` for the [project](../../../core/glossary.md#term-project--project)'s host alone, and fails where that host is not authenticated. Tests find that a failing second host leaves the check passing, whether the project's host is configured or is `gh`'s default host. Nothing checks that a command reaches no other tracker.

**Imposed by:** Every [project](../../../core/glossary.md#term-project--project) the [capability](../../../core/glossary.md#term-capability--capability) served when its records were written lived on GitHub. GitHub's issues, sub-issues and [Milestones](../../glossary.md#term-milestone--milestone) carry much of what those records decide. A tracker hidden behind an abstraction would cost a translation at every write, for a switch of tracker nobody has asked for ([DEC-003](../../../../../.pkit/capabilities/project-management/decisions/DEC-003-github-bound-substrate.md)).
