---
id: UC-006
title: Make my merges wait on the system's checks
status: active
actor: ACT-adopter
other-actors:
  - ACT-ci-pipeline
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/project_config.py
        - src/project_kit/cli.py
        - src/project_kit/friction_check.py
        - src/project_kit/validate.py
        - src/project_kit/validators.py
        - .github/workflows/checks.yml
      record:
        - COR-050#2
        - COR-050#6
        - COR-050#12
        - COR-054#3
        - COR-055#6
        - ADR-019#2
        - ADR-055#5
      artefact:
        - ACT-adopter
        - ACT-ci-pipeline
    revalidated:
      at: 2026-10-18T19:50:15Z
      outcome: unchanged
      unchanged-because: This change makes pkit migrations check-diff also fail a migration script at a released version, read at the base it already compares with, and makes pkit new migration choose its version. This use case names that check only among the project's other checks, each exiting non-zero on what fails it, and how pkit validate and pkit friction check hold a merge is untouched.
---

# UC-006 — Make my merges wait on the system's checks

**Goal:** Make my merges wait on the system's checks, knowing they bind only once my CI requires them.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs every check with no terminal and no person to answer, and gates the merge on the exit status. It names the base once, for every check (COR-054 point 3).

**Preconditions:** The system is installed in the project, and the project's continuous integration can run `pkit` on a checkout of each pull request.

**Assumptions:**

- The hosting service holds a merge until a required status passes. The backbone ships no workflow that runs these checks, so the adopter wires the required status (ADR-019 point 2).
- Branches are kept up to date with their base, or a merge queue runs the checks again on each merge (COR-050 point 6).

**Trigger:** The adopter decides that the project's merges should wait on the system's checks.

**Main path:**

1. The adopter runs `pkit config set friction.mode enforcing --yes`.
2. The system validates the whole configuration file with the new value, and writes it. It prints `set friction.mode = enforcing  (.pkit/project/config.yaml)`.
3. The adopter adds a job to the project's CI that runs `pkit sync`, then `pkit validate`, `pkit friction check` and the project's other checks. The job sets `PKIT_CHECK_BASE` to the pull request's target. In project-kit, that job is `.github/workflows/checks.yml`.
4. The adopter makes that job a required status of the default branch, on the hosting service.
5. On each pull request, the CI pipeline runs the job with no terminal, and no check asks anything.
6. Each check exits non-zero on what fails it. `pkit validate` fails on an `error` finding. The change check fails on unanswered friction, a `bump`, a dead anchor, an unresolved kind or a resolver's missing answer.
7. The hosting service holds the merge until the job passes.

**Variants:**

- **1a.** The value is not a mode, such as `loud`. The system refuses it with the schema's message, and writes nothing.
- **1b.** The adopter keeps the default, `warning` mode. The change check reports what it finds and passes, so only validation's errors and the other checks fail the job.
- **1c.** The adopter writes `friction.mode` by hand, with a value that is no mode. The change check reads it as `warning`, with a warning line, and `pkit validate` fails on it (COR-050 point 12).
- **3a.** The job does not run `pkit sync` first. A registered validator then says "environment not provisioned — run `pkit sync`", an `error` finding, so `pkit validate` fails.
- **3b.** The job's checkout lacks the base. Each check that compares refuses with its fixes, such as fetching the base or naming another.
- **3c.** The job's checkout is shallow. The change check names, in its header, each artefact whose history the cut hides (UC-002).
- **4a.** The adopter never makes the job required. The checks run and report, and nothing holds the merge (COR-050 point 12). The use case ends.
- **6a.** The base moved on after the branch left it. The change check reports an `outdated-base` and never fails on it, since the fix is to update the branch.
- **6b.** No place is declared yet, or nothing in the places carries the `pkit` container. The change check is dormant and passes.
- **7a.** Someone with the right bypasses the required status, or commits straight to the default branch. The job does not hold that change.

**Postconditions:** No pull request merges into the default branch through the hosting service's protection while a check of the required job fails on it.

**Minimal guarantees:**

- An invalid friction mode fails validation, so enforcement is never switched off silently (COR-050 point 12).
- A validator that gives no answer fails validation, and never passes it (COR-055 point 6).
- In enforcing mode, a resolver that gives no answer fails the change check, which could not judge its anchor (COR-050 points 2 and 12).
- An outdated base is reported, and never fails the change check (COR-050 point 12).
