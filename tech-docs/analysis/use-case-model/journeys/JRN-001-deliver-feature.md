---
id: JRN-001
title: Deliver a feature
status: active
actor: ACT-developer
steps:
  - UC-009
  - UC-010
  - UC-001
  - UC-011
  - UC-002
  - UC-003
  - UC-012
  - UC-007
relies-on:
  - UC-008
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/use_case_citations.py
        - .pkit/capabilities/software-analysis/scripts/fill-use-cases.py
        - .pkit/capabilities/software-analysis/scripts/check-numbers.py
        - .pkit/capabilities/software-analysis/scripts/_lib/revalidation.py
        - .pkit/capabilities/software-analysis/skills/analysis-author/analysis-author.md
        - .pkit/capabilities/living-docs/scripts/_lib/doc_check.py
        - .pkit/capabilities/project-management/scripts/_lib/friction_answers.py
        - .pkit/capabilities/project-management/scripts/land-work.py
        - .pkit/capabilities/project-management/scripts/done-work.py
        - src/project_kit/release.py
        - .github/workflows/checks.yml
        - src/project_kit/friction_repository.py
        - .pkit/rules/core.md
      record:
        - project-management:DEC-054#4
        - project-management:DEC-054#5
        - project-management:DEC-055#2
        - project-management:DEC-055#3
        - project-management:DEC-055#5
        - project-management:DEC-015
        - software-analysis:DEC-001#3
        - software-analysis:DEC-001#6
        - software-analysis:DEC-001#11
        - COR-009
        - COR-050#3
        - COR-050#6
        - COR-050#8
        - COR-050#9
        - PRJ-002#D1
      artefact:
        - ACT-developer
        - UC-009
        - UC-010
        - UC-001
        - UC-011
        - UC-002
        - UC-003
        - UC-012
        - UC-007
        - UC-008
---

# JRN-001 — Deliver a feature

**Goal:** Deliver my feature from its planned intent to the default branch, leaving every artefact it made stale answered there.

**Steps:**

1. UC-009 — Revise the analysis ahead of a change
   - **Needs from UC-008 (outside this journey):** the issue that plans the change, and the use cases its `## Use cases` section names. A use case cited before it settled on the default branch draws only a warning (project-management DEC-054 point 4). Its number on a branch can still go to another use case first, since the first to land keeps a number (software-analysis DEC-001 point 3). The citation then names that other use case, and passes with no warning, since the check is of existence only (project-management DEC-054 point 4).
2. UC-010 — Record my decision beside the methodology's
   - **Needs from step 1 (UC-009):** the use cases the decision must meet. While the record is proposed, it is no source of a use case's goal (the `analysis-author` skill). Nothing asks a use case for the anchor on the record once the record is accepted. And the record anchors no use case, so a later revision of a use case asks nothing of the record (software-analysis DEC-001 point 11).
3. UC-001 — Build my change under my project's conventions
   - **Needs from step 1 (UC-009):** the revised use cases on the default branch, and the planned record's gaps, each naming the issue that builds the missing behaviour. Nothing marks a use case of unbuilt behaviour as planned, save its record's gap (software-analysis DEC-001 point 6). No check asks the build to anchor the use case on the code it adds.
   - **Needs from step 2 (UC-010):** the accepted records the change builds on. A record still proposed binds nothing, and nothing at run time stops a build that cites one (core rule 2).
4. UC-011 — Write a page for its reader, anchored to what makes it true
   - **Needs from step 3 (UC-001):** the code the page describes, in the same pull request (project-management DEC-015). Code of the declared surface that no artefact anchors is reported as uncovered (COR-050 point 8). A use case's anchor on that code meets the obligation as a page's would, so such code draws no obligation for a page (`doc_check.py`).
5. UC-002 — Answer what my change made stale
   - **Needs from step 3 (UC-001):** the change's diff. The change check flags each artefact anchored to what the diff modified. An artefact whose anchors miss something it rests on is asked nothing (COR-050 point 6).
6. UC-003 — Declare what my change means for the next release
   - **Needs from step 3 (UC-001):** the paths the change touched, which the changeset guard reads. A surface change can still land with no changeset. The `skip-changeset` label waives the guard, and a `none` changeset can declare a surface change as none. A surface change only in a path the guard does not read, such as a core skill under `.pkit/skills/`, slips through (`release.py`).
7. UC-012 — Land my change on the default branch
   - **Needs from step 5 (UC-002):** the change check's list of answers, for the head that merges. `land-work` derives the list again at the head it pins (project-management DEC-055 point 2). A landing through `done-work`, or outside project-management, writes no list. The pull request's description may then carry an earlier head's list, or none (project-management DEC-055 point 5).
   - **Needs from step 6 (UC-003):** the changesets, checked by the CI the landing waits for. Where the target branch merges with no queue, `done-work` with `--bypass-ci` lands a pull request whose guard failed (`done-work.py`).
8. UC-007 — Resolve what the default branch left out of date
   - **Needs from step 7 (UC-012):** the landed commit, from which each debt the change left is dated. Friction the change deferred, or left unanswered in `warning` mode, is debt on the default branch (COR-050 point 9).

**Variants:**

- **1a.** The feature alters nothing users do, such as a refactor. The analysis is not revised, and the path goes on at step 2 (project-management DEC-054 point 5).
- **1b.** The revision rides in the build's pull request, rather than landing first. Its use cases settle only with the code, so no issue can cite them before then. The path goes on at step 2.
- **2a.** The accepted records settle every choice the feature needs. No record is written, and the path goes on at step 3.
- **4a.** No page describes what the feature changes, and the feature adds no surface a page must describe. No page is written, and the path goes on at step 5.
- **6a.** The change touches no path of the backbone or of a component, so it declares no changeset. The path goes on at step 7.
- **7a.** The merge authoriser asks for a change before authorising the merge. The path rejoins at step 3.
- **8a.** The change left no debt on the default branch, and the path ends after step 7.

**Postconditions:** The feature is on the default branch. Each artefact anchored to what the feature changed carries an answer there: updated, still true, or deferred to an open follow-up.

**Minimal guarantees:**

- A `land-work` run given `--expect-head` merges only the authorised head, or a later head that authorisation covers (project-management DEC-055 point 3, and `land-work.py`).
- Friction that a stopped path leaves on the default branch is not lost. The whole-repository check derives the debt from git at each run, never from a ledger (COR-050 point 9, and `friction_repository.py`).

## Sources

- **The goal** joins what these records decide:
  - a planned intent is sliced against the use cases (project-management DEC-054 point 5)
  - a change lands on the default branch as COR-009 sets out
  - each artefact a change made stale carries an answer before the change merges (COR-050 point 3)
  - what is left unanswered is debt on the default branch (COR-050 point 9)
