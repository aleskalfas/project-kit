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
  - UC-006
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
        - COR-017
        - COR-025
        - COR-050#1
        - COR-050#3
        - COR-050#5
        - COR-050#9
        - COR-050#12
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
        - UC-006
---

# JRN-003 — Deliver a change

**Goal:** Deliver my change, built only on accepted records, to the default branch, with its changesets declared and every artefact it made stale answered there.

**Steps:**

1. [UC-037](../use-cases/030-change/UC-037-record-decision.md) — Record my decision beside the methodology's
   - **Needs from [UC-049](../use-cases/050-adopt/UC-049-install-system.md) (outside this journey):** the [system](../../glossary.md#term-system--system) installed in the [project](../../glossary.md#term-project--project) and committed for the team. Where the adopter keeps the system out of the shared repository, `.pkit/` is excluded whole. Git then ignores each record of the project's own stamped under `.pkit/decisions/project/` ([ADR-009 point 3](../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#3-private--make-the-whole-footprint-git-invisible-via-gitinfoexclude)).
   - **Assumed:** the [change](../../glossary.md#term-change--change) is planned before the record, by the developer or by an installed [capability](../../glossary.md#term-capability--capability) that plans work, such as `project-management` ([COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)). No step of this journey reads the plan, which the change's branch names by its issue ([COR-008](../../../../../.pkit/decisions/core/COR-008-git-conventions.md)).
2. [UC-002](../use-cases/030-change/UC-002-answer-stale.md) — Answer what my change made stale
   - **Needs from step 1 (UC-037):** the record the change adds or refines. The [change check](../../glossary.md#term-change-check--change-check) reports [friction](../../glossary.md#term-friction--friction) on each [artefact](../../glossary.md#term-artefact--artefact) anchored to that record, or to a [point](../../glossary.md#term-point--point) the change altered ([COR-050 point 5](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#5-when-an-anchor-has-changed-and-what-answers-it)). An artefact that a new record makes untrue raises none, since nothing anchors the new record yet. The dependants of a record the new one supersedes are flagged only once an edit marks that record `superseded` (UC-037 variant 1d).
   - **Needs from [UC-040](../use-cases/030-change/UC-040-accept-through-review.md) (outside this journey):** the record accepted before the change builds on it. No check of the [backbone](../../glossary.md#term-backbone--backbone) reads what a change builds on, save a [rule](../../glossary.md#term-rule--rule)'s origin ([COR-051 point 5](../../../../../.pkit/decisions/core/COR-051-rule-sets.md#5-origins-checked-deterministically)). A change built on a proposed record passes those checks, though the [acceptance gate](../../glossary.md#term-acceptance-gate--acceptance-gate) forbids it (core rule 2).
   - **Assumed:** artefacts saying what the change must do are revised before the change is built, where an installed capability keeps them, such as `software-analysis` (COR-017). The change check reads them only as artefacts in their places ([COR-050 point 1](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts)).
   - **Assumed:** the change is built, and each document it makes untrue is revised in the same change. An installed capability may carry either part, such as `software-engineering` for the build and `living-docs` for the documents the change makes untrue (COR-017). The change check reads such a document as any artefact in a [place](../../glossary.md#term-place--place), as [UC-005](../use-cases/030-change/UC-005-anchor-document.md) anchors one (COR-050 point 1).
3. [UC-003](../use-cases/030-change/UC-003-declare-changeset.md) — Declare what my change means for the next release
   - **Needs from step 1 (UC-037):** the record, where it lies in a path the [changeset](../../glossary.md#term-changeset--changeset) guard reads, such as a core record or a capability's decision (`release.py`). One whose text changes what adopters do declares `patch` or above. One recording a feature that a later change ships declares `none` ([PRJ-002](../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)). The guard reads only paths, so it cannot tell the two apart.
4. [UC-034](../use-cases/030-change/UC-034-land-change.md) — Land my change on the default branch
   - **Needs from step 2 (UC-002):** the change check's list of answers, at the [head](../../glossary.md#term-head--head) the merge authoriser authorises. The developer names that head to the landing. The landing merges nothing else, and derives no list and runs no check there ([ADR-061 point 5](../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#5-the-command-makes-requests-and-reports-facts-the-caller-decides)). A list read at an earlier head can pass for this one, unless the developer derives it again at that head.
   - **Needs from step 3 (UC-003):** the changesets, which the CI pipeline checks before the landing. With `--admin` on a [base](../../glossary.md#term-base--base) with no merge queue, the landing merges past every failing required check, the changeset guard included (ADR-061 point 5). The `skip-changeset` label waives the guard's surface check too (UC-003 variant 7a).
   - **Needs from [UC-006](../use-cases/030-change/UC-006-gate-merges.md) (outside this journey):** the project's merges made to wait on the system's checks. Where the change check runs in `warning` mode, or the CI job is no required status, unanswered friction holds no merge ([COR-050 point 12](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding)). That friction then lands as [debt](../../glossary.md#term-debt--debt) for step 5.
5. [UC-007](../use-cases/030-change/UC-007-resolve-debt.md) — Resolve what the default branch left out of date
   - **Needs from step 4 (UC-034):** the landed change, from which each debt it left is dated. Friction the change deferred, or left unanswered, is debt on the [default branch](../../glossary.md#term-default-branch--default-branch) ([COR-050 point 9](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger)). Unless the CI pipeline runs the [whole-repository check](../../glossary.md#term-whole-repository-check--whole-repository-check), no whole-repository report brings that debt to the developer, who lists it with `pkit friction debt` ([ADR-055 point 5](../../../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md#5-friction-check-enforcing-from-the-day-it-exists)).

**Variants:**

- **1a.** The accepted records settle every choice the [change](../../glossary.md#term-change--change) needs. The developer records nothing, and the path goes on at step 2.
- **3a.** The change touches no path of the [backbone](../../glossary.md#term-backbone--backbone) or of a [component](../../glossary.md#term-component--component). The developer declares no [changeset](../../glossary.md#term-changeset--changeset), and the path goes on at step 4 ([UC-003](../use-cases/030-change/UC-003-declare-changeset.md) variant 1a).
- **4a.** The merge authoriser asks the developer to revise the change before authorising the merge. The developer revises it, and the path rejoins at step 2.
- **4b.** The developer works alone, and commits the change straight to the [default branch](../../glossary.md#term-default-branch--default-branch) ([UC-034](../use-cases/030-change/UC-034-land-change.md) variant 1a). No [pull request](../../glossary.md#term-pull-request--pull-request) carries it, and the path goes on at step 5.
- **5a.** The change left no [debt](../../glossary.md#term-debt--debt) on the default branch, and the path ends after step 4.

**Postconditions:** The [change](../../glossary.md#term-change--change) is on the [default branch](../../glossary.md#term-default-branch--default-branch), built on accepted records, with its [changesets](../../glossary.md#term-changeset--changeset) waiting for the next [release step](../../glossary.md#term-release-step--release-step). Each [artefact](../../glossary.md#term-artefact--artefact) anchored to what the change altered carries an [answer](../../glossary.md#term-answer--answer) there: `updated`, `unchanged` with why, or deferred to an open follow-up.

**Minimal guarantees:**

- The [whole-repository check](../../glossary.md#term-whole-repository-check--whole-repository-check) derives the [debt](../../glossary.md#term-debt--debt) that a stopped path leaves from git at each run, never from a ledger ([COR-050 point 9](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger) and `friction_repository.py`).
- The landing merges nothing but the [head](../../glossary.md#term-head--head) the developer names ([ADR-061 point 5](../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#5-the-command-makes-requests-and-reports-facts-the-caller-decides)).
