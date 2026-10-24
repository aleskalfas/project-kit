---
id: REQ-041
title: A command that writes checks the project's prerequisites and the person's membership first
status: active
statement: "Before a command of project-management writes, it checks the project's prerequisites for the capability, and that whoever runs it is a team member."
measure: "Where the project does not meet the prerequisites, or a list of members leaves out the person, the command refuses before its first write. It names the cause, and changes nothing."
applies-to: "Every command of project-management that writes, whether a person runs it or an agent runs it for them. Where the team keeps no list of members, or an empty one, every person passes the second check."
actors:
  - core:ACT-developer
  - ACT-planner
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/bootstrap_gate.py
        - .pkit/capabilities/project-management/scripts/_lib/membership.py
        - tests/test_pm_bootstrap_gate.py
        - tests/test_pm_membership.py
      record:
        - project-management:DEC-017
        - project-management:DEC-021
      artefact:
        - ACT-planner
    revalidated:
      at: 2026-10-24T20:58:39Z
      outcome: updated
---

# REQ-041 · Functional · A command that writes checks the project's prerequisites and the person's membership first

**Verified by:** Tests of the first check find that a [project](../../../core/glossary.md#term-project--project) short of the prerequisites is refused, with the command to run. A project that meets them passes. Tests of the second find who the person is, from their login or their email. No test finds that every command that writes runs both checks first.

**Rationale:** The prerequisites are a hard gate on every operation, held by the commands rather than by an agent's reading of what a check reports (DEC-017). Where a team keeps a list of its members, only a member acts on its work, and the check runs before any other work (DEC-021).
