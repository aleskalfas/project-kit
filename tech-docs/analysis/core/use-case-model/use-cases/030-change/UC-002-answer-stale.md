---
id: UC-002
title: Answer what my change made stale
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
  - ACT-ci-pipeline
  - ACT-merge-authoriser
  - ACT-operator
requirements:
  - REQ-002
  - REQ-004
  - REQ-005
  - REQ-006
  - REQ-007
  - REQ-009
  - REQ-012
  - REQ-018
  - REQ-019
  - REQ-020
  - REQ-021
after:
  - [UC-014]
shortfalls:
  - at: 11
    issue: "#1765"
    record: ADR-034#1
  - at: 6
    issue: "#1873"
    record: COR-062#1
  - at: "5e"
    issue: "#1873"
    record: COR-062#5
  - at: "9b"
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/friction_check.py
        - src/project_kit/friction_write.py
        - src/project_kit/friction_resolve.py
        - src/project_kit/default_branch.py
        - .github/workflows/checks.yml
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
        - COR-062#1
        - COR-062#3
        - COR-062#4
        - COR-062#5
        - COR-062#7
        - COR-062#10
        - ADR-034#1
        - ADR-068#6
      artefact:
        - ACT-developer
        - ACT-ai-agent
        - ACT-ci-pipeline
        - ACT-merge-authoriser
        - ACT-operator
        - REQ-002
        - REQ-004
        - REQ-005
        - REQ-006
        - REQ-007
        - REQ-009
        - REQ-012
        - REQ-018
        - REQ-019
        - REQ-020
        - REQ-021
    revalidated:
      at: 2026-10-23T09:43:09Z
      outcome: updated
---

# UC-002 — Answer what my change made stale

**Goal:** Answer what my change made stale, letting an agent write the answers my change owes and a reviewer other than that agent check them.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): an agent making the change writes, without asking, the answers the change owes. A reviewer agent, where the project chose one, checks them, writes none and changes nothing it judges (COR-050 point 3 and REQ-021).
- **CI pipeline** (`ACT-ci-pipeline`): runs the change check against the pull request's target, named once for every check (COR-054 point 3). It reads the pull request's head as the change's own (COR-062 point 4). It is told when a shallow clone cut the history the check reads.
- **Merge authoriser** (`ACT-merge-authoriser`): is told, for each updated artefact, the sentence the change's author wrote on what changed, which a reviewer checked against the diff. From the check's own list, it is also told which artefacts wait for which follow-up (COR-050 point 3). It is told too of each revalidation on the base's tip that an answer of the change did not read (COR-062 point 7).
- **Operator** (`ACT-operator`): is asked before a command that writes an answer changes a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-014:** The project runs the system: it is the methodology's source repository, or the system is installed in it.

**Assumptions:**

- A reviewer the project chooses, other than the agent that wrote the answers, checks them. Nothing in the check tells whether the reviewer read them (COR-050 point 3).
- An agent writes no answer the change does not owe until a person accepts its words. Nothing at run time stops it (COR-050 point 3 and core rule 20).
- The branch is up to date with its base, or a merge queue runs the check again on the merge (COR-050 point 6).

**Trigger:** The developer, or the agent making the change, is about to push the change's branch.

**Main path:**

1. The developer runs `pkit friction check` on the change's branch.
2. The system compares the working tree with where the branch left its base, the default branch unless `--base` or `PKIT_CHECK_BASE` names another. It prints the commit where the branch left the base.
3. The system reports, as `friction`, each artefact with an anchor the change modified and no answer, upstream first along the anchors between artefacts.
4. For each one, the developer or the agent making the change reads what changed under its anchors, and judges whether the artefact still holds.
5. They update the artefact and run `pkit friction revalidate <artefact> --outcome updated`, or run it with `--outcome unchanged --because "<why it still holds>"`.
11. At its entry, before it writes, the command checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit friction revalidate` and `pkit friction defer` run no such check, and write in whatever repository holds their working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

6. Once `--yes` or a prompt at a terminal gives consent, the system writes the answer to an answer file of the change's own. The answer names, in `read`, every other answer file on that artefact. The artefact's own file stays as it was (COR-062 points 1 and 4).

> [!WARNING]
> **Not built yet:** the system writes the answer as the `revalidated` key of the artefact's `friction` block. COR-062 point 1 decides that a change writes its answers in answer files of its own, never in the artefact, and #1873 tracks it.

7. The developer runs `pkit friction check` again. It reports no friction, and lists every answer the change wrote, word for word, under "Answers written in this change".
8. For each artefact revalidated as `updated`, whoever made the change says in one sentence what changed in it, in the pull request.
9. The CI pipeline runs `pkit friction check` on the pull request, with `PKIT_CHECK_BASE` naming the pull request's target and `PKIT_CHECK_HEAD` naming its head, and the check passes.
10. A reviewer other than the agent that wrote the answers checks each `unchanged` and `deferred` reason against the change, and each sentence against the diff. It works from the check's own list, and does not judge again a deferral the change kept as it was.

**Variants:**

- **2a.** No place is declared, or nothing in the places carries the `pkit` container. The check is dormant and needs no base. It prints its counts and exits `0`. The use case ends.
- **2b.** The base resolves to no commit. The check refuses, and names its fixes: fetching the base, declaring the right default branch, or naming another base. The use case ends.
- **2c.** The clone is shallow, and cuts the history of an artefact whose `at` the change alters. Where the value was first carried inside the clone, the check reads it as new, and its header names the artefact. Where the file already carries it at the cut, the value answers nothing, and the path goes on at step 3.
- **3a.** The change modified no anchor of any artefact. The check reports no friction, and the use case ends.
- **3b.** The base moved on after the branch left it. The check reports an `outdated-base`, and never fails on it. The developer merges the base, and the path rejoins at step 1.
- **3c.** The change added an anchor that resolves to nothing, or removed what an anchor named. The check reports a `dead-anchor`, an error (REQ-020). The developer mends the anchor, and the path rejoins at step 1.
- **5a.** The artefact can wait for a later change. They run `pkit friction defer <artefact> --anchor <anchor> --reason "<reason>"`, the reason naming an open follow-up issue. The path goes on at step 11.
- **5b.** The artefact still describes what is wanted, and the change broke what it describes. A defect is reported, and the artefact is revalidated `unchanged`, its reason naming the defect.
- **5c.** An artefact the change was not asked about needs an answer too. That answer is a person's decision. The agent making the change writes it only once the person has seen every word and accepted it. Where it cannot ask, it names the answer and its command in its hand-off, and runs none (COR-050 point 3 and core rule 20).
- **5d.** `--because` repeats the justification already written, or still holds a placeholder such as `<why it still holds>`. The system refuses it and writes nothing. The path rejoins at step 5.
- **5e.** The artefact carries deferrals. The revalidation re-states only those `--keep` names, or those a prompt at a terminal keeps. It reads the rest and replaces them (COR-062 point 5). The revalidation itself then answers what each replaced deferral had put off (COR-050 point 4).

> [!WARNING]
> **Not built yet:** the revalidation removes the rest from the artefact's block. COR-062 point 5 decides that it replaces each deferral it read and does not re-state, which stays in the deferral's own answer file. #1873 tracks it.

- **6a.** The run has no terminal, and neither `--yes` nor `--dry-run` is given. The system refuses and writes nothing. It names the command to run with `--dry-run`, and the path rejoins at step 5.
- **6b.** The artefact's block would not pass validation once written. The system refuses and writes nothing. The developer mends the block that `pkit validate` names, and the path rejoins at step 5.
- **7a.** The check reports a `bump`: `at` changed with nothing behind it, such as `updated` while the content stayed as it was. The developer corrects the answer, and the path rejoins at step 5.
- **7b.** The change wrote an answer file as COR-062 forbids. In enforcing mode, the check fails on each such answer file (COR-062 points 3, 4 and 10):
  - an answer file its base holds, rewritten
  - an answer file with no live answer, removed beside answers added
  - an answer whose `read` leaves out an answer file on its artefact at the change's own head
  - an answer on what its artefact does not hold

  The developer mends the answer files, and the path rejoins at step 7.
- **7c.** The change moved answers word for word out of the artefacts' blocks into answer files. The check lists them apart, under "Answers moved in this change", and nobody is asked to accept them (COR-062 point 3).
- **7d.** An artefact the change revalidates in an answer file has a live revalidation on the base's tip that the change's answer did not read. The check reports that revalidation as `answered-apart`, and never fails on it. Once merged, the two are debt until a revalidation reads both (COR-062 point 7).
- **9a.** The project runs the change check in `warning` mode. The check reports what it finds and passes, so nothing holds the merge on it.
- **9b.** The pull request's target moved on, and merging the target into the branch conflicts inside a `revalidated` block. `pkit friction resolve` checks the repository as step 11 does. It resolves the block's text, and writes no answer of its own. It names the revalidation still owed, and the path rejoins at step 5.

> [!WARNING]
> **Not built yet:** `pkit friction resolve` runs no such check. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **10a.** The reviewer finds a passage that does not hold:
  - a reason that does not hold against the change
  - a deferral that names no open follow-up
  - an `updated` artefact with no sentence, or one that does not match the diff

  The reviewer blocks the merge, and the path rejoins at step 4.
- **10b.** The project chose no such reviewer, or a person skipped the review on record. The answers stand, checked by their writer alone, a limit the record accepts (COR-050 point 3).
- **10c.** No gate brings the chosen reviewer to the change, such as an unclassified pull request that changes only documents. The answers stand, checked by their writer alone, a case COR-050 point 3 does not name.

**Postconditions:** Every artefact whose anchor the change modified carries an answer in the change: `updated`, `unchanged` with why, or deferred to an open follow-up. The check's list names each one, word for word.

**Minimal guarantees:**

- The change check writes nothing, whatever it finds (COR-050 point 13 and `friction_check.py`).
- A base that resolves to no commit stops a check that has something to compare, and is never guessed (COR-054 point 4).
- In enforcing mode, the check fails on unanswered friction and on a `bump` (COR-050 point 12). It fails too on a dead anchor the change made, on an unresolved kind, and on an answer file written as COR-062 point 10 forbids.
- A resolver that gives no answer leaves its anchor as `no-answer`, never read as unchanged (COR-050 point 2).
- A writer that lacks consent, or would leave the block invalid, writes nothing (`friction_write.py`).
- An `at` written back to a value the artefact carried before answers nothing, so reverting a revalidation brings back what it answered (COR-050 point 3).
- The list of answers is read from the artefacts and the answer files, never composed. A file whose front matter does not parse is named as unread, never left out silently (COR-050 point 3 and `friction_check.py`).
