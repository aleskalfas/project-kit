---
id: REQ-042
title: A move a person holds is made only on that person's authorisation
status: active
statement: "No command of project-management makes a move of the issue lifecycle that a person holds without that person's authorisation for that issue."
measure: "With no terminal, no confirmation flag, and no reason where the move asks one, the command refuses the move and changes nothing."
applies-to: "Every command of project-management that moves an issue through the issue lifecycle, or merges the pull request whose merge moves it. The moves of the cascade are outside this requirement, since they ask for no authorisation."
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
        - tests/test_pm_close_issue.py
      record:
        - project-management:DEC-006
        - project-management:DEC-014
        - project-management:DEC-046#1
        - project-management:DEC-055#3
      artefact:
        - ACT-planner
---

# REQ-042 · Functional · A move a person holds is made only on that person's authorisation

**Verified by:** Tests of `move-issue` find that a [bypass](../../glossary.md#term-bypass--bypass) with no reason is refused, and that a retried bypass posts its [audit comment](../../glossary.md#term-audit-comment--audit-comment) once. Tests of `done-work` find that an empty bypass is refused, and that an approval by the [change](../../../core/glossary.md#term-change--change)'s author does not count. Tests of `close-issue` find that each close the person holds is refused with no terminal and no `--yes`, and writes nothing. Those closes are a won't-do close, a parent [issue](../../glossary.md#term-issue--issue)'s close, a close through a merged [pull request](../../../core/glossary.md#term-pull-request--pull-request), and a [Task](../../glossary.md#term-task--task)'s close as completed without one.

**Rationale:** Scheduling and ending the work are commitments an agent must not make on its own. A person holds the move back from In Progress too, since that move settles what becomes of the scheduling. Held as refusals the agent cannot pass, the gates make the [methodology](../../../core/glossary.md#term-methodology--methodology)'s authority mechanical ([DEC-006](../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)). The [authorisation](../../glossary.md#term-authorisation--authorisation) to merge stays the person's, whatever a [reviewer](../../../core/glossary.md#term-reviewer--reviewer) approved ([DEC-055 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).
