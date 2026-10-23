---
id: REQ-042
title: A move a person holds is made only on that person's authorisation
status: active
statement: "No command of project-management makes a move of the issue lifecycle that a person holds without that person's authorisation for that issue."
measure: "With no terminal, no confirmation flag, and no reason where the move asks one, the command refuses the move and changes nothing."
applies-to: "Every command of project-management that moves an issue through the issue lifecycle, or merges the pull request whose merge moves it. The moves of the cascade are outside it, since they ask for no authorisation."
actors:
  - core:ACT-developer
  - ACT-planner
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/schemas/workflow.yaml
        - tests/test_pm_move_issue.py
        - tests/test_pm_done_work.py
      record:
        - project-management:DEC-006
        - project-management:DEC-014
        - project-management:DEC-046#1
        - project-management:DEC-055#3
      artefact:
        - ACT-planner
---

# REQ-042 · Functional · A move a person holds is made only on that person's authorisation

**Verified by:** Tests of `move-issue` find that a bypass with no reason is refused, and that a retried bypass posts its audit comment once. Tests of `done-work` find that an empty bypass is refused, and that an approval by the change's author does not count. `close-issue` closes with no terminal and no flag, which #1936 tracks, and no test covers it.

**Rationale:** The start and the end of work are commitments an agent must not make on its own. Held as refusals the agent cannot pass, the gates make the methodology's authority mechanical (DEC-006). The authorisation to merge stays the person's, whatever a reviewer approved (DEC-055 point 3).
