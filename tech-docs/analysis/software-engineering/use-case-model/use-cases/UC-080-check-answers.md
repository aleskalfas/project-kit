---
id: UC-080
title: Have a change's answers checked by a reviewer other than their writer
status: active
actor: core:ACT-merge-authoriser
other-actors:
  - core:ACT-developer
  - core:ACT-ai-agent
requirements: []
shortfalls:
  - at: "1b"
    issue: "#1966"
    record: COR-050#3
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/docs-reviewer.md
        - .pkit/capabilities/software-engineering/review-contributions.yaml
      record:
        - software-engineering:DEC-002#1
        - software-engineering:DEC-002#3
        - COR-050#3
        - COR-050#12
        - COR-050#16
        - COR-062#7
        - project-management:DEC-028
        - project-management:DEC-032#D1
        - project-management:DEC-032#D4
        - project-management:DEC-055#3
        - project-management:DEC-055#5
        - COR-064#4
        - COR-013
        - COR-017
        - COR-031
---

# UC-080 — Have a change's answers checked by a reviewer other than their writer

**Goal:** Have a reviewer other than their writer check a change's answers, so no merge I authorise rests on an answer that does not hold.

**Other actors:**

- **Developer** (`core:ACT-developer`): the person whose pull request it is. They, or the agent making the change for them, mend each answer a `[block]` finding names.
- **AI agent** (`core:ACT-ai-agent`): the code-review panel's `docs-reviewer`, which checks the answers and gives a verdict. The reviewer writes no answer, and changes nothing it reviews ([core:REQ-021](../../../core/requirements/functional/030-change/REQ-021-reviewer-changes-nothing.md)). The agent that wrote the answers, such as the `software-engineer`, never reviews them ([COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).

**Preconditions:** None.

**Assumptions:**

- The project has software-engineering installed, or registered in place where software-engineering is developed, and the adapter deploys software-engineering's `docs-reviewer` agent definition ([COR-013](../../../../../.pkit/decisions/core/COR-013-agent-architecture.md), [COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-031](../../../../../.pkit/decisions/core/COR-031-capability-origin.md)).
- The change carries the answers it owes, written by the agent making it or by the developer, as `core:UC-002` describes ([COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).
- The merge gate requires the `docs-reviewer` where a pull request's diff touches code, or its closing issue has a `type` ([project-management DEC-032 point D1](../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d1--the-required-local-reviewer-set-resolves-from-the-prs-closing-issues)). project-management runs the reviewer on the pull request's head, posts the reviewer's verdict and counts it, as `project-management:UC-062` describes ([project-management DEC-028](../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)). It runs the reviewer a capability contributes even where the project registers no local reviewer of its own ([project-management DEC-032 point D4](../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d4--review-pr-invokes-the-resolved-set)).
- Where the project opts out of the `docs-reviewer`, and chooses no other reviewer of the answers, the answers stand checked by their writer alone. COR-050 point 3 accepts that limit.
- Where the merge gate does not require the `docs-reviewer`, as for an unclassified pull request changing only documents, the panel checks no answer. COR-050 point 3 does not name that case, and #1732 asks a record to decide it.
- The backbone's change check lists every answer the change wrote, in plain words, in its last section, "Answers written in this change". It flags each answer the change was not asked for (COR-050 points 3 and [12](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding)).
- The merge authoriser is told each sentence on an updated artefact, and each artefact left out of date, as `project-management:UC-062` describes ([project-management DEC-055 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).

**Trigger:** The merge gate requires the `docs-reviewer` for a pull request, and project-management runs the reviewer on the pull request's head.

**Main path:**

1. The `docs-reviewer` runs the change check, `pkit friction check --base <base> --head <head>`, with the pull request's base branch and the pull request's head ([software-engineering DEC-002 point 1](../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#1-the-panel)).
2. The reviewer reads the answers from the check's last section, "Answers written in this change", never from an account the change's author wrote. The artefacts the check asked about are those its findings name above the list.
3. For each `unchanged` answer the check asked for, the reviewer reads the artefact and the diff of each anchor the list names as modified. It judges whether the reason holds against the change.
4. Next come the deferrals the change writes or rewords on an artefact the check asked about. For each, the reviewer judges whether its reason says truly why the artefact is left out of date. It reads the state of the follow-up issue the reason names, which must be open.
5. For each artefact revalidated as `updated`, the reviewer reads the sentence under `## What changed in each updated document` in the pull request's description. It reads the sentence as the commands that write the list of answers read it ([project-management DEC-055 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)). It checks the sentence against the diff of that artefact.
6. For each revisit of a target that owes an answer, the reviewer reads the diff of the trigger fields the list names as modified. The reviewer also reads what the target stands on at the head. It judges each revisit by its outcome ([COR-050 point 16](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#16-a-link-may-ask-for-a-revisit-of-its-targets-when-its-source-changes)):
   - **Updated in this change:** the changed target contradicts nothing the modified trigger fields now say.
   - **Still accurate:** the entry's reason says truly why the target still stands against the change.
   - **Out of date, fixed later:** the entry's reason holds, and names a follow-up issue that is open.
7. The reviewer gives its verdict, which project-management posts on the pull request. Each answer that does not hold is a `[block]` finding, so the verdict requests changes (software-engineering DEC-002 point 1). After its findings, a short paragraph names the answers it checked and found holding.
8. With the verdict approving the change, the merge authoriser authorises the merge, relying on the reviewer for each reason, deferral and sentence ([COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).

**Variants:**

- **1a.** The reviewer cannot run the change check. It gives a `[block]` finding that says why, since the answers would go unchecked, and the use case ends.
- **1b.** The agent making the change is to commit it straight to the default branch, with no pull request. Before the commit, the agent has the `docs-reviewer` check the answers as on a pull request ([COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)). A `[block]` finding stops the commit, and the merge authoriser, here the person the agent works for, is told the sentences first.

> [!WARNING]
> **Not built yet:** the reviewer starts from a pull request's number, and requests changes where it cannot fetch one. COR-050 point 3 decides that the reviewer checks a direct commit's answers before the commit, and #1966 tracks it.

- **2a.** The list says `none`, or the check reports itself dormant in the project. Nothing is left to check, and the path goes on at step 7.
- **2b.** The list flags as "not asked for by this change" an answer no change owes, which the developer or the delegate decided, as [UC-081](UC-081-decide-unasked-answers.md) describes:
  - an answer on an artefact the check asked nothing about
  - a reason for having no anchors
  - a revisit entry the check did not ask for

  The reviewer checks each against what it answers, whoever decided it, through `pkit friction explain` at the base ([COR-064 point 4](../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#4-a-reviewer-checks-every-answer-no-change-owes)). One that does not hold is a `[block]` finding. It also names each in an `[advisory]` finding, since it cannot tell who decided it.
- **2c.** The list flags "not asked for by this change" a deferral the change rewords on an artefact the check asked about. The reviewer judges it as at step 4 ([software-engineering DEC-002 point 1](../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#1-the-panel)).
- **2d.** The check reports a revalidation on the base's tip that the change's answer on an artefact did not read. Merged, the two are answered apart, debt that the next revalidation of the artefact judges ([COR-062 point 7](../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#7-answers-made-apart-are-debt-not-a-conflict)). No change owes an answer for that debt, so the reviewer blocks on nothing. The landing command tells the merge authoriser of each such revalidation, as information ([project-management DEC-055 point 3](../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).
- **3a.** A reason does not hold against the change: it is false, or it leaves out an edit that makes the artefact untrue. A `[block]` finding quotes the reason and the passage the change made untrue. The answer is mended, and the path rejoins at step 1 on the new head.
- **3b.** The list flags a revalidation as replacing revalidations answered apart, whose combined state nobody has judged ([COR-062 point 7](../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#7-answers-made-apart-are-debt-not-a-conflict)). The reviewer reads what changed since each replaced revalidation through `pkit friction explain` at the base. An `unchanged` reason, or an `updated` artefact, that does not hold against what changed since each is a `[block]` finding. The path rejoins at step 1 once the answer is mended.
- **4a.** The change keeps a deferral as it was, with the anchor and the words the base had. The reviewer does not judge it again, since the review of the change that wrote it was to check it ([COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).
- **4b.** A deferral's reason does not hold, or it names no issue, or a closed one. A `[block]` finding says which, and the path rejoins at step 1 once the deferral is mended.
- **5a.** An `updated` artefact has no sentence, or only an item the commands cannot read, such as one naming the artefact in bold. The commands read a sentence only from an item that opens with the artefact in a code span. So a `[block]` finding quotes the item, and gives the form ``- `path`: sentence``. The path rejoins at step 1 once the item is mended.
- **5b.** The sentence does not match what changed in the artefact. A `[block]` finding says what is wrong, and the path rejoins at step 1 once the sentence is mended.
- **6a.** A target the change revisited by changing it contradicts nothing, yet leaves part of the change unmet. The reviewer names that part in an `[advisory]` finding, and blocks on nothing ([software-engineering DEC-002 point 3](../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#3-block-threshold-discipline-per-agent)).
- **6b.** A revisit does not hold, such as a test that still checks the value the change replaced. A `[block]` finding names the trigger field and quotes the target, and the path rejoins at step 1 once the revisit is mended.
- **7a.** The developer edits a sentence in the description after the verdict. An edit of the description makes no verdict stale, so nobody checks the edited sentence ([project-management DEC-055 point 5](../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#5-what-this-does-not-verify)).
- **7b.** The verdict requests changes, and a person bypasses the `docs-reviewer` on record, with a reason. The answers then stand checked by their writer alone, a limit [COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation) accepts ([project-management DEC-055 point 5](../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#5-what-this-does-not-verify)).

**Postconditions:** A reviewer other than their writer checked each answer and each revisit the change owed against the change. It checked each answer no change owes against what that answer answers. The verdict approves the change only where each holds.

**Minimal guarantees:**

- An answer that does not hold is a `[block]` finding, whatever the project's conventions say ([software-engineering DEC-002 point 1](../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#1-the-panel) and `docs-reviewer.md`).
- A change check the reviewer cannot run is a `[block]` finding, never an approval (`docs-reviewer.md`).
- The reviewer writes no answer, and changes nothing it reviews ([core:REQ-021](../../../core/requirements/functional/030-change/REQ-021-reviewer-changes-nothing.md)).
- An answer no change owes that does not hold is a `[block]` finding, whoever decided it (software-engineering DEC-002 point 1 and [COR-064 point 4](../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#4-a-reviewer-checks-every-answer-no-change-owes)).
