---
id: UC-112
title: Have a change's code reviewed for correctness and security
status: active
actor: core:ACT-merge-authoriser
other-actors:
  - core:ACT-developer
  - core:ACT-ai-agent
requirements:
  - REQ-060
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/code-reviewer.md
        - .pkit/capabilities/software-engineering/agents/security-reviewer.md
        - .pkit/capabilities/software-engineering/review-contributions.yaml
        - .pkit/capabilities/project-management/scripts/_lib/review_opt_outs.py
      record:
        - software-engineering:DEC-002
        - software-engineering:DEC-003
        - project-management:DEC-027
        - project-management:DEC-028
        - project-management:DEC-032#D1
        - project-management:DEC-032#D3
        - project-management:DEC-032#D4
        - project-management:DEC-050
        - project-management:DEC-055#3
        - COR-013
        - COR-017
        - COR-031
        - COR-050#3
        - COR-051#4
        - COR-066#1
        - COR-066#3
        - COR-009
        - ADR-061#3
        - PRJ-002#D1
        - PRJ-002#D2
        - COR-050#6
        - COR-050#9
        - COR-066#2
        - COR-024
        - COR-044#2
        - COR-057#5
        - COR-068
      artefact:
        - REQ-060
---

# UC-112 — Have a change's code reviewed for correctness and security

**Goal:** Have a change's code reviewed for correctness and security before I authorise its merge.

**Other actors:**

- **Developer** (`core:ACT-developer`): the person whose pull request it is. They, or the agent making the change for them, fix each `[block]` finding.
- **AI agent** (`core:ACT-ai-agent`): the code-review panel's `code-reviewer` and `security-reviewer`, each of which judges the change's code and gives a verdict. Neither changes anything it reviews ([core:REQ-021](../../../../core/requirements/functional/030-change/REQ-021-reviewer-changes-nothing.md)).

**Preconditions:** None.

**Assumptions:**

- The project has software-engineering installed, or registered in place where software-engineering is developed. The adapter deploys its `code-reviewer` and `security-reviewer` agent definitions ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md), [COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-031](../../../../../../.pkit/decisions/core/COR-031-capability-origin.md)).
- The merge gate requires both reviewers where a pull request's diff touches code, whatever the issues it closes ([project-management DEC-032 point D1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d1--the-required-local-reviewer-set-resolves-from-the-prs-closing-issues)). project-management runs each reviewer on the pull request's head, posts its verdict and counts it, as `project-management:UC-062` describes ([project-management DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).
- The project's list of paths that are not code narrows what touches code. A pull request that changes only such paths needs neither reviewer (project-management DEC-032 point D1).
- Where the project opts out of a reviewer, with a reason, the merge gate does not require it (`review_opt_outs.py`). The change's code then merges without that reviewer's judgement.
- In human review mode, both verdicts only advise, and a person's approval satisfies the merge gate ([project-management DEC-027](../../../../../../.pkit/capabilities/project-management/decisions/DEC-027-review-modes.md) and [DEC-032 point D3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d3--the-resolved-set-is-and-composed-the-gate-checker-generalises-across-paths-the-singleton-cap-lifts)).
- Each reviewer carries only knowledge that holds in any project. It reads the project's own standards from the conventions corpus the project names ([software-engineering DEC-002 point 4](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#4-knowledge-split)).
- Only its definition holds each reviewer to when it blocks, and to the knowledge it carries. Neither is a contract a check validates ([software-engineering DEC-002](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md), "Implications"). A verdict is an AI agent's judgement, which can miss a defect.

**Trigger:** The merge gate requires the `code-reviewer` and the `security-reviewer` for a pull request, and project-management runs them on the pull request's head.

**Main path:**

1. The `code-reviewer` and the `security-reviewer` each read the pull request and its diff (`code-reviewer.md` and `security-reviewer.md`).
2. Each reviewer reads the conventions corpus the project names, and notes which of its standards bear on the diff ([software-engineering DEC-002 point 4](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#4-knowledge-split)).
3. The `code-reviewer` judges the diff's correctness, the quality of its code and the design of its interfaces ([software-engineering DEC-002 point 1](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#1-the-panel)).
4. The `security-reviewer` judges the diff for security defects (DEC-002 point 1). Two such defects are a secret on a command line and a shell command built from outside input. It judges the change's code against [REQ-060](../../../requirements/quality/REQ-060-secret-off-command-line.md): a secret never goes on a command line.
5. Each reviewer tags each of its findings ([project-management DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)):
   - `[block]`: an objective failure in its remit that the change owns, one the change introduces, exposes, moves, copies or widens ([software-engineering DEC-002 point 3](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#3-block-threshold-discipline-per-agent))
   - `[person]`: a passage the change owns, where an accepted rule of the conventions corpus binds and does not settle the reading. The finding cites the rule by its id.
   - `[advisory]`: any other finding, such as a point of taste
6. Each reviewer gives its verdict, which project-management posts on the pull request. A `[block]` finding withholds that reviewer's approval (project-management DEC-028).
7. With both verdicts approving the change, the merge authoriser authorises the merge, after reading each `[person]` finding ([project-management DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).

**Variants:**

- **1a.** A reviewer cannot fetch the pull request, or read its diff. Its verdict requests changes and says why, since it cannot approve what it cannot read ([project-management DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md) and `code-reviewer.md`). The path goes on at step 6.
- **1b.** The pull request changes more than 300 files, so `gh pr diff` refuses its diff. The reviewer reads the same diff from the local checkout, and the path goes on at step 2 (`code-reviewer.md`).
- **2a.** The project names no conventions corpus, or the corpus is empty or silent on a choice. The reviewer says so, and judges by the knowledge its definition carries. It blocks on no standard the corpus lacks, and the path goes on at step 3.
- **5a.** The reviewer finds a defect that the change did not introduce, expose, move, copy or widen, and the change claims nothing about it. The reviewer tags it `[advisory] (pre-existing: <reason>)`, the reason saying why no claim of the change is false ([software-engineering DEC-002 point 3](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#3-block-threshold-discipline-per-agent)).
- **5b.** The change claims to fix or guard against such a defect, in the pull request's title or body, or in text its diff adds. Where the defect survives in the reviewer's remit, the claim is false, so the finding is a `[block]` ([DEC-002 point 3](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#3-block-threshold-discipline-per-agent)). It names the claim and the surviving defect.
- **6a.** A verdict requests changes. The developer, or the agent making the change for them, fixes each `[block]` finding, as [UC-001](../010-build/UC-001-build-under-conventions.md) describes in its step 7. The reviewers judge the new head, as `project-management:UC-062` describes, and the path rejoins at step 1.
- **6b.** A verdict requests changes, and the developer bypasses that reviewer on record, with a reason, as `project-management:UC-062` describes in its variant 13c. The merge then rests on code that reviewer did not approve ([project-management DEC-050](../../../../../../.pkit/capabilities/project-management/decisions/DEC-050-per-reviewer-override.md)).

**Postconditions:** The `code-reviewer` and the `security-reviewer` each judged the change's code at the pull request's head. Each approves the change only where none of its findings is a `[block]`.

**Minimal guarantees:**

- A reviewer that cannot read the change's diff never approves it ([project-management DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md) and `code-reviewer.md`).
- Neither reviewer changes anything it reviews (`code-reviewer.md`, `security-reviewer.md` and [core:REQ-021](../../../../core/requirements/functional/030-change/REQ-021-reviewer-changes-nothing.md)).
