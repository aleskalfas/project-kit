---
id: UC-002
title: Answer what my change made stale
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
  - ACT-ci-pipeline
  - ACT-merge-authoriser
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/friction_check.py
        - src/project_kit/friction_write.py
        - src/project_kit/friction_resolve.py
        - src/project_kit/default_branch.py
        - .pkit/rules/core.md
      record:
        - COR-050#2
        - COR-050#3
        - COR-050#4
        - COR-050#6
        - COR-050#12
        - COR-050#13
        - COR-054#3
        - COR-054#4
        - software-analysis:DEC-001#5
      artefact:
        - ACT-developer
        - ACT-ai-agent
        - ACT-ci-pipeline
        - ACT-merge-authoriser
---

# UC-002 — Answer what my change made stale

**Goal:** Answer what my change made stale, letting an agent write the answers my change owes while a reviewer other than that agent checks them.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): an agent making the change writes, without asking, the answers the change owes and no other (COR-050 point 3).
- **CI pipeline** (`ACT-ci-pipeline`): runs the change check against the pull request's real base, named once for every check (COR-054 point 3). It is told when a shallow clone cut the history the check reads.
- **Merge authoriser** (`ACT-merge-authoriser`): is told what changed in each updated artefact, and which artefacts wait for which follow-up. Both come from the check's own list, never from an account an agent composed (COR-050 point 3).

**Preconditions:** The artefacts the change could make stale carry their anchors in a declared place (UC-005).

**Assumptions:**

- A reviewer the project chooses, other than the agent that wrote the answers, checks them. Nothing in the check tells whether the reviewer read them (COR-050 point 3).
- An agent writes no answer the change does not owe until a person accepts its words. Nothing at run time stops it (COR-050 point 3 and core rule 20).
- The branch is up to date with its base, or a merge queue runs the check again on the merge (COR-050 point 6).

**Trigger:** The developer, or the agent making the change, is about to push the change's branch.

**Main path:**

1. The developer runs `pkit friction check` on the change's branch.
2. The system compares the working tree with where the branch left its base, the default branch unless `--base` or `PKIT_CHECK_BASE` names another. It prints the base commit.
3. The system reports, as `friction`, each artefact with an anchor the change modified and no answer, upstream first along the anchors between artefacts.
4. For each one, the developer or the agent making the change reads what changed under its anchors, and judges whether the artefact still holds.
5. They update the artefact and run `pkit friction revalidate <artefact> --outcome updated`, or run it with `--outcome unchanged --because "<why it still holds>"`.
6. The system writes only the `revalidated` key of the artefact's `friction` block, once `--yes` or a prompt at a terminal gives consent.
7. The developer runs `pkit friction check` again. It reports no friction, and lists every answer the change wrote, word for word, under "Answers written in this change".
8. For each artefact revalidated as `updated`, the author says in one sentence what changed in it, in the pull request.
9. The CI pipeline runs `pkit friction check` on the pull request, with `PKIT_CHECK_BASE` naming the pull request's target, and the check passes.
10. A reviewer other than the agent that wrote the answers checks each `unchanged` and `deferred` reason against the change. It checks each sentence too, working from the check's own list.

**Variants:**

- **2a.** The base resolves to no commit. The check refuses, naming its fixes: fetch the base, declare the right default branch, or name another base. The use case ends.
- **2b.** The clone is shallow, and the history of an artefact whose `at` the change alters is cut behind the base. The check reads the value as new, and its header names the artefact.
- **3a.** No place is declared, or nothing in the places carries the `pkit` container. The check is dormant: it prints its counts, exits `0`, and the use case ends.
- **3b.** The change modified no anchor of any artefact. The check reports no friction, and the use case ends.
- **3c.** The base moved on after the branch left it. The check reports an `outdated-base` and never fails on it. The developer merges the base, and the path rejoins at step 1.
- **3d.** The change added an anchor that resolves to nothing, or removed what an anchor named. The check reports a `dead-anchor`, the developer mends the anchor, and the path rejoins at step 1.
- **5a.** The artefact can wait for a later change. They run `pkit friction defer <artefact> --anchor <anchor> --reason "<reason>"`, the reason naming an open follow-up issue, and the path goes on at step 6.
- **5b.** The artefact is an analysis artefact, and the change broke what it describes. A defect is reported, and the artefact is revalidated `unchanged`, its reason naming the defect. Where stale versus regressed is unclear, a person decides first (software-analysis DEC-001 point 5).
- **5c.** The agent would answer an artefact the change was not asked about. That answer is the person's decision, so the agent shows the person every word first. Where it cannot ask, it returns the commands and runs none (core rule 20).
- **5d.** `--because` repeats the justification already written, or still holds a placeholder such as `<why it still holds>`. The system refuses it and writes nothing, and the path rejoins at step 5.
- **6a.** The run has no terminal, and neither `--yes` nor `--dry-run` is given. The system refuses, writes nothing, and names the command to run with `--dry-run`.
- **6b.** The artefact's block would not pass validation once written. The system refuses and writes nothing, and the developer mends the block that `pkit validate` names.
- **7a.** The check reports a `bump`: `at` changed with nothing behind it, such as `updated` with no change to the content. The developer corrects the answer, and the path rejoins at step 5.
- **9a.** The project runs the change check in `warning` mode. The check reports what it finds and passes, so nothing holds the merge on it.
- **9b.** The pull request's base moved, and merging it conflicts inside a `revalidated` block. `pkit friction resolve` resolves the block's text, writes no answer, and names the revalidation still owed. The path rejoins at step 5.
- **10a.** A reason does not hold, a deferral names no open follow-up, or an `updated` artefact has no matching sentence. The reviewer blocks the merge, and the path rejoins at step 4.
- **10b.** The project chose no such reviewer, or a person skipped the review on record. The answers stand, checked by their writer alone, a limit the record accepts (COR-050 point 3).

**Postconditions:** Every artefact whose anchor the change modified carries an answer in the change: `updated`, `unchanged` with why, or deferred to an open follow-up. The check's list names each one, word for word.

**Minimal guarantees:**

- The change check writes nothing, whatever it finds (COR-050 point 13 and `friction_check.py`).
- A base that resolves to no commit stops the check with its fixes, and is never guessed (COR-054 point 4).
- In enforcing mode, the check fails on unanswered friction, a `bump` and a dead anchor the change made (COR-050 point 12). It fails on an unresolved kind too.
- A resolver that gives no answer leaves its anchor as `no-answer`, never read as unchanged (COR-050 point 2).
- A writer that lacks consent, or would leave the block invalid, writes nothing (`friction_write.py`).
- An `at` written back to a value the artefact carried before answers nothing, so reverting a revalidation brings back what it answered (COR-050 point 3).
- The list of answers is read from the artefacts, never composed, so it holds every answer the change wrote (COR-050 point 3).
