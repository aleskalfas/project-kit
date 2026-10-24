---
id: UC-080
title: Have a change's answers checked by a reviewer other than their writer
status: active
actor: core:ACT-merge-authoriser
other-actors:
  - core:ACT-developer
  - core:ACT-ai-agent
requirements: []
after:
  - [UC-001, environment]
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
        - COR-050#16
        - project-management:DEC-028
        - project-management:DEC-032#D1
        - project-management:DEC-055#3
        - project-management:DEC-055#5
        - COR-013
        - COR-017
        - COR-031
---

# UC-080 — Have a change's answers checked by a reviewer other than their writer

**Goal:** Have a reviewer other than their writer check a change's answers, so no merge I authorise rests on an answer that does not hold.

**Other actors:**

- **Developer** (`core:ACT-developer`): the person whose pull request it is. They mend each answer a `[block]` finding names, and say in the pull request what changed in each updated artefact.
- **AI agent** (`core:ACT-ai-agent`): the `docs-reviewer` of the code-review panel, which checks the answers and posts its verdict. It writes no answer, and changes nothing it reviews (core:REQ-021). The agent that wrote the answers, such as the `software-engineer`, never reviews them (COR-050 point 3).

**Preconditions:**

- **From UC-001, or Environment:** The change carries the answers it owes, written by the `software-engineer` agent, or by the developer as `core:UC-002` describes (COR-050 point 3).

**Assumptions:**

- The project has software-engineering installed, or registered in place where it is developed, and the adapter deploys its `docs-reviewer` agent definition (COR-013, COR-017 and COR-031).
- The merge gate requires the `docs-reviewer` on a pull request whose diff touches code, or that closes an issue with a `type`. project-management runs the reviewer on the pull request's head, and counts its verdict, as `project-management:UC-062` describes (project-management DEC-028 and DEC-032 point D1).
- Where the merge gate does not require it, such as on an unclassified pull request that changes only documents, no reviewer of the panel checks the answers. COR-050 point 3 does not name that case, and #1732 asks a record to decide it.
- The backbone's change check lists every answer the change wrote, in plain words, in its last section, "Answers written in this change". It flags each answer the change was not asked for (COR-050 point 3).
- The merge authoriser is told each sentence on an updated artefact, and each artefact left out of date, as `project-management:UC-062` describes (project-management DEC-055 point 3).

**Trigger:** The merge gate requires the `docs-reviewer` for a pull request, and project-management runs the reviewer on the pull request's head.

**Main path:**

1. The `docs-reviewer` runs the change check, `pkit friction check --base <base> --head <head>`, with the pull request's base branch and its head (software-engineering DEC-002 point 1).
2. The reviewer reads the answers from the check's last section, "Answers written in this change", never from an account the change's author wrote. The artefacts the check asked about are those its findings name above the list.
3. For each `unchanged` answer on an artefact the check asked about, the reviewer reads the diff of each anchor the list names as modified, and the artefact itself. It judges whether the reason holds against the change.
4. For each deferral the change writes or rewords, the reviewer judges whether its reason says truly why the artefact is left out of date. It reads the state of the follow-up issue the reason names, which must be open.
5. For each artefact revalidated as `updated`, the reviewer reads the sentence under `## What changed in each updated document` in the pull request's description. It reads the sentence as the commands that write the list of answers read it, and checks it against the diff of that artefact (project-management DEC-055 point 3).
6. For each revisit of a link's target, the reviewer reads the diff of the trigger fields the list names as modified, and what the target stands on at the head. It judges the revisit by its outcome (COR-050 point 16):
   - **Updated in this change:** the changed target contradicts nothing the modified trigger fields now say.
   - **Still accurate:** the entry's reason says truly why the target still stands against the change.
   - **Out of date, fixed later:** the entry's reason holds, and names a follow-up issue that is open.
7. The reviewer posts its verdict. Each answer that does not hold is a `[block]` finding, so the verdict requests changes (software-engineering DEC-002 point 3). After its findings, a short paragraph names the answers it checked and found holding.
8. With the verdict approving the change, the merge authoriser authorises the merge, relying on the reviewer for each reason, deferral and sentence (COR-050 point 3).

**Variants:**

- **1a.** The reviewer cannot run the change check. It posts a `[block]` finding that says why, since the answers would go unchecked, and the use case ends.
- **1b.** The change is committed to the default branch directly, with no pull request. Where the developer has the `docs-reviewer` review it before the commit, the reviewer checks its answers as on a pull request. A `[block]` finding stops the commit, as it would stop the merge (COR-050 point 3).

> [!WARNING]
> **Not built yet:** the reviewer starts from a pull request's number, and requests changes where it cannot fetch one. COR-050 point 3 decides that the reviewer checks a direct commit's answers before the commit, and #1966 tracks it.

- **2a.** The list says `none`, or the check reports that friction is dormant in the project. Nothing is left to check, and the path goes on at step 7.
- **2b.** The list flags "not asked for by this change" an answer on an artefact the check asked nothing about, or a reason for having no anchors. It flags a revisit entry the change was not asked for the same way. Each is the developer's decision, so the reviewer names it in an `[advisory]` finding, as UC-081 describes, and blocks on none of them.
- **2c.** The list flags "not asked for by this change" a deferral the change rewords on an artefact the check asked about. The reviewer judges it as at step 4 (software-engineering DEC-002 point 1).
- **3a.** A reason does not hold against the change: it is false, or it leaves out an edit that makes the artefact untrue. A `[block]` finding quotes the reason and the passage the change made untrue. The developer mends the answer, and the path rejoins at step 1 on the new head.
- **4a.** The change keeps a deferral as it was, with the anchor and the words the base had. The reviewer does not judge it again, since the review of the change that wrote it was to check it (COR-050 point 3).
- **4b.** A deferral's reason does not hold, or it names no issue, or a closed one. A `[block]` finding says which, and the path rejoins at step 1 once the developer mends it.
- **5a.** An `updated` artefact has no sentence, or no list item that starts with the artefact in a code span, such as an item naming it in bold. The commands read no sentence there, so a `[block]` finding quotes the item and gives the form ``- `path`: sentence``. The path rejoins at step 1 once the developer mends it.
- **5b.** The sentence does not match what changed in the artefact. A `[block]` finding says what is wrong, and the path rejoins at step 1 once the developer mends it.
- **6a.** A target the change revisited by changing it contradicts nothing, yet leaves part of the change unmet. The reviewer names that part in an `[advisory]` finding, and blocks on nothing (software-engineering DEC-002 point 3).
- **6b.** A revisit does not hold, such as a test that still checks the value the change replaced. A `[block]` finding names the trigger field and quotes the target, and the path rejoins at step 1 once the developer mends it.
- **7a.** The developer edits a sentence in the description after the verdict. An edit of the description makes no verdict stale, so nobody checks the edited sentence (project-management DEC-055 point 5).
- **7b.** The verdict requests changes, and a person bypasses the `docs-reviewer` on record, with a reason. The answers then stand checked by their writer alone, a limit COR-050 point 3 accepts (project-management DEC-055 point 5).

**Postconditions:** Each answer the change owed, and each revisit it owed, was checked against the change by a reviewer other than its writer. The verdict approves the change only where each holds.

**Minimal guarantees:**

- An answer that does not hold is a `[block]` finding, whatever the project's conventions say (software-engineering DEC-002 point 1).
- A change check the reviewer cannot run is a `[block]` finding, never an approval (`docs-reviewer.md`).
- The reviewer writes no answer, and changes nothing it reviews (core:REQ-021).
- The reviewer blocks on no answer that is the developer's decision (software-engineering DEC-002 point 1).
