---
id: REQ-041
title: A command that writes first checks the project's prerequisites and the membership of whoever runs it
status: active
statement: "Before writing, a project-management command checks the project's prerequisites, and that whoever runs it, a user's account wherever GitHub names one, is a team member."
measure: "Where the project does not meet the prerequisites, the command refuses before its first write. The same holds where a list of members leaves out whoever runs the command. Wherever GitHub names a user's account a command runs as, that account is whoever runs it, not the person an agent works for. The command names the cause, and changes nothing."
applies-to: "Every command of project-management that writes, whether a person runs it or an agent runs it for them. Some commands are exempt from the first check, such as `bootstrap`, which makes the prerequisites, and `migrate`, which runs its own check. Where the team keeps no list of members, or an empty one, whoever runs a command passes the second check."
obligation: v1:sha256:e8be9fda46fcfdc48cb2eed9c93391388f2bb4c72d3b5a453a5b164cc5afcdf4
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
        - project-management:DEC-003
        - project-management:DEC-017
        - project-management:DEC-021
        - COR-009
        - ADR-061#3
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

# REQ-041 · Functional · A command that writes first checks the project's prerequisites and the membership of whoever runs it

**Verified by:** Tests of the first check find that a [project](../../../core/glossary.md#term-project--project) short of the prerequisites is refused, with the command to run. A project that meets them passes. Tests of the second find whoever runs the command from what GitHub answers, never from git's email or the person an agent works for. No test finds that every command that writes runs both checks first.

**Rationale:** The prerequisites are a hard gate on every operation, held by the commands rather than by an agent's reading of what a check reports ([DEC-017](../../../../../.pkit/capabilities/project-management/decisions/DEC-017-prerequisites-bootstrap-migrate-discipline.md)). Where a team keeps a list of its members, only a member acts on its work, and the check runs before any other work ([DEC-021](../../../../../.pkit/capabilities/project-management/decisions/DEC-021-team-membership-gate.md)). project-management is bound to GitHub ([DEC-003](../../../../../.pkit/capabilities/project-management/decisions/DEC-003-github-bound-substrate.md)). Where GitHub names a command's account as a user's, the second check judges that account, not the person an agent works for (DEC-021).
