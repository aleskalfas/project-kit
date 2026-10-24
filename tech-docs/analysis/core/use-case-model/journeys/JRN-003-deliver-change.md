---
id: JRN-003
title: Deliver a change
status: active
actor: ACT-developer
steps:
  - UC-037
  - UC-002
  - UC-003
  - UC-034
  - UC-007
relies-on:
  - UC-049
  - UC-040
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/rules/core.md
        - src/project_kit/visibility.py
        - src/project_kit/friction_check.py
        - src/project_kit/release.py
        - src/project_kit/pull_request_landing.py
        - src/project_kit/friction_repository.py
      record:
        - COR-008
        - COR-009
        - COR-025
        - COR-050#1
        - COR-050#3
        - COR-050#5
        - COR-050#9
        - COR-051#4
        - COR-051#5
        - PRJ-002
        - ADR-009#3
        - ADR-055#5
        - ADR-061#5
      artefact:
        - ACT-developer
        - UC-037
        - UC-002
        - UC-003
        - UC-034
        - UC-007
        - UC-049
        - UC-040
---

# JRN-003 — Deliver a change

**Goal:** Deliver my change, built only on accepted records, to the default branch, with its changesets declared and every artefact it made stale answered there.

**Steps:**

1. UC-037 — Record my decision beside the methodology's
   - **Needs from UC-049 (outside this journey):** the system installed in the project and committed for the team. Where the adopter keeps the system out of the shared repository, `.pkit/` is excluded whole. Git then ignores each record of the project's own stamped under `.pkit/decisions/project/` (ADR-009 point 3).
   - **Assumed:** the change is planned before the record, by the developer or by an installed capability that plans work, such as `project-management`. The change's branch names the issue that plans it, and no step of this journey reads that plan (COR-008).
   - **Assumed:** artefacts saying what the change must do are revised before the record is written, where an installed capability keeps them, such as `software-analysis`. The backbone reads them only as artefacts in the places that capability declares (COR-050 point 1).
2. UC-002 — Answer what my change made stale
   - **Needs from step 1 (UC-037):** the record the change adds or refines. The change check reports friction on each artefact anchored to that record, or to a point the change altered (COR-050 point 5). A new record raises none, since no artefact anchors it yet.
   - **Needs from UC-040 (outside this journey):** the record accepted before the change builds on it. No check reads what a change builds on, save a rule's origin (COR-051 point 5). Elsewhere, a change built on a proposed record passes every check (core rule 2).
   - **Assumed:** the change is built, with each document it makes untrue revised in the same change, where an installed capability keeps documents, such as `living-docs`. The change check reads such a document only as an artefact in its place (COR-050 point 1).
3. UC-003 — Declare what my change means for the next release
   - **Needs from step 1 (UC-037):** the record, whose meaning for the next release the developer judges. A record whose text changes what adopters do declares `patch` or above. One recording a feature that a later change ships declares `none` (PRJ-002). The changeset guard reads only paths, so it cannot tell the two apart.
4. UC-034 — Land my change on the default branch
   - **Needs from step 2 (UC-002):** the change check's list of answers, at the head the merge authoriser authorises. The landing pins that head and merges nothing else, but derives no list and runs no check there (ADR-061 point 5). A list read at an earlier head can pass for this one, unless the caller that runs the landing derives it again.
   - **Needs from step 3 (UC-003):** the changesets, which the CI pipeline checks before the landing. On a base with no merge queue, the landing passes an administrator merge through, past a failing changeset guard (ADR-061 point 5). The `skip-changeset` label waives the guard's surface check too (UC-003 variant 7a).
5. UC-007 — Resolve what the default branch left out of date
   - **Needs from step 4 (UC-034):** the landed change, from which each debt it left is dated. Friction the change deferred, or left unanswered in `warning` mode, is debt on the default branch (COR-050 point 9). Unless the project's own CI runs the whole-repository check, no report brings that debt to the developer, who lists it with `pkit friction debt` (ADR-055 point 5).

**Variants:**

- **1a.** The accepted records settle every choice the change needs. The developer records nothing, and the path goes on at step 2.
- **3a.** The change touches no path of the backbone or of a component. The developer declares no changeset, and the path goes on at step 4 (UC-003 variant 1a).
- **4a.** The merge authoriser asks the developer to revise the change before authorising the merge. The developer revises it, and the path rejoins at step 2.
- **4b.** The developer works alone, and commits the change straight to the default branch (UC-034 variant 1a). No pull request carries it, and the path goes on at step 5.
- **5a.** The change left no debt on the default branch, and the path ends after step 4.

**Postconditions:** The change is on the default branch, built on accepted records, with its changesets waiting for the next release step. Each artefact anchored to what the change altered carries an answer there: `updated`, `unchanged` with why, or deferred to an open follow-up.

**Minimal guarantees:**

- Friction that a stopped path leaves on the default branch is never lost. The whole-repository check derives the debt from git at each run, never from a ledger (COR-050 point 9 and `friction_repository.py`).
- The landing merges nothing but the head the merge authoriser authorised (ADR-061 point 5).
