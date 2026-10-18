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
        - .pkit/capabilities/project-management/scripts/_lib/friction_answers.py
        - .pkit/capabilities/project-management/scripts/land-work.py
        - src/project_kit/release.py
        - .github/workflows/checks.yml
        - src/project_kit/friction_repository.py
        - .pkit/rules/core.md
      record:
        - project-management:DEC-054#4
        - project-management:DEC-055#3
        - project-management:DEC-015
        - software-analysis:DEC-001#3
        - software-analysis:DEC-001#6
        - software-analysis:DEC-001#11
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

**Goal:** Deliver my feature from its planned intent to the default branch, leaving every description it made stale answered there.

**Steps:**

1. UC-009 — Revise the analysis ahead of a change
   - **Needs from UC-008 (outside this journey):** the issue that plans the change, and the use cases its `## Use cases` section names. A use case cited before it settled on the default branch draws only a warning (project-management DEC-054 point 4). Its number on a branch can still change before it lands, since the first to land keeps a number (software-analysis DEC-001 point 3).
2. UC-010 — Record my decision beside the methodology's
   - **Needs from step 1 (UC-009):** the use cases the decision must meet. The record anchors none of them (software-analysis DEC-001 point 11). So a later revision of a use case asks nothing of a record that answers it.
3. UC-001 — Build my change under my project's conventions
   - **Needs from step 1 (UC-009):** the revised use cases, and the planned record's gaps, each naming the task that builds it. Nothing marks a use case of unbuilt behaviour as planned, and nothing makes the build add its code anchor (software-analysis DEC-001 points 6 and 11).
   - **Needs from step 2 (UC-010):** the accepted records the change builds on. A record still proposed binds nothing, and nothing at run time stops a build that cites one (core rule 2).
4. UC-011 — Write a page for its reader, anchored to what makes it true
   - **Needs from step 3 (UC-001):** the code the page describes, in the same pull request (project-management DEC-015). Code of the declared surface that no page anchors is reported as uncovered (COR-050 point 8).
5. UC-002 — Answer what my change made stale
   - **Needs from step 3 (UC-001):** the change's diff, which flags each artefact anchored to what it modified. An artefact whose anchors miss what it rests on is asked nothing (COR-050 point 6).
6. UC-003 — Declare what my change means for the next release
   - **Needs from step 3 (UC-001):** the paths the change touched, which the changeset guard reads. A touched component with no changeset fails the guard only where CI runs `pkit release check` (`release.py` and `.github/workflows/checks.yml`).
7. UC-012 — Land my change on the default branch
   - **Needs from step 5 (UC-002):** the change check's list of answers, for the head that merges. A list derived at another head would tell the merge authoriser of answers that did not land. So the landing derives the list again at the head it pins (project-management DEC-055 point 3).
   - **Needs from step 6 (UC-003):** the changesets, checked by the CI the landing waits for. The `skip-changeset` label lets a change land without one.
8. UC-007 — Resolve what the default branch left out of date
   - **Needs from step 7 (UC-012):** the landed commit, from which each debt the change left is dated. Friction the change deferred, or left unanswered in `warning` mode, is debt on the default branch (COR-050 point 9).

**Variants:**

- **1a.** The feature alters nothing users do, such as a refactor. The analysis is not revised, and the path goes on at step 2 (project-management DEC-054 point 5).
- **1b.** The revision lands on the default branch before the build, in a pull request of its own (UC-012). Later tasks can then cite its use cases as settled, and the path goes on at step 2.
- **2a.** The accepted records settle every choice the feature needs. No record is written, and the path goes on at step 3.
- **4a.** No page describes what the feature changes, and the feature adds no surface a page must describe. No page is written, and the path goes on at step 5.
- **6a.** The change touches no path of the backbone or of a component, so it declares no changeset. The path goes on at step 7.
- **7a.** The merge authoriser asks for a change before authorising the merge. The path rejoins at step 3.
- **8a.** The change left no debt on the default branch, and the path ends after step 7.

**Postconditions:** The feature is on the default branch. Each artefact anchored to what the feature changed carries an answer there: updated, still true, or deferred to an open follow-up.

**Minimal guarantees:**

- A path that stops at step 7 merges no head it was not authorised to merge. Given `--expect-head`, only the authorised head merges, or a later head that authorisation covers (project-management DEC-055 point 3, and `land-work.py`).
- Friction that a stopped path leaves on the default branch is never lost. The whole-repository check derives it as debt at each run, dated from its commit (COR-050 point 9, and `friction_repository.py`).
