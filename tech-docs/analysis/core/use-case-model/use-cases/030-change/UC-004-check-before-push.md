---
id: UC-004
title: Know before I push that my change passes my project's checks
status: active
actor: ACT-developer
other-actors:
  - ACT-ci-pipeline
requirements:
  - REQ-004
  - REQ-005
  - REQ-006
  - REQ-007
  - REQ-015
  - REQ-018
  - REQ-019
after:
  - [UC-014, UC-049]
pkit:
  friction:
    anchors:
      path:
        - scripts/check.sh
        - .githooks/pre-push
        - .github/workflows/checks.yml
        - src/project_kit/validate.py
        - src/project_kit/validators.py
        - src/project_kit/command_runner.py
        - src/project_kit/default_branch.py
        - .pkit/rules/project.md
      record:
        - COR-050#6
        - COR-054#2
        - COR-054#3
        - COR-054#4
        - COR-055#3
        - COR-055#5
        - COR-055#6
        - ADR-019#2
        - ADR-058#7
        - ADR-068#6
      artefact:
        - ACT-developer
        - ACT-ci-pipeline
        - REQ-004
        - REQ-005
        - REQ-006
        - REQ-007
        - REQ-015
        - REQ-018
        - REQ-019
---

# UC-004 — Know before I push that my change passes my project's checks

**Goal:** Know before I push that my change passes the checks my project gates its merges on.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the same checks on the [pull request](../../../glossary.md#term-pull-request--pull-request) with no person to reply. It names the [base](../../../glossary.md#term-base--base) once, for every check (COR-054 [point](../../../glossary.md#term-point--point) 3).

**Preconditions:** **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:**

- The clone has fetched the [default branch](../../../glossary.md#term-default-branch--default-branch) as the remote holds it. A check tells that its [base](../../../glossary.md#term-base--base) moved on only as far as this clone can tell (COR-050 [point](../../../glossary.md#term-point--point) 6).
- The [pull request](../../../glossary.md#term-pull-request--pull-request) targets the branch the developer's checks read as their base, as project-kit's pull requests target the default branch (`.github/workflows/checks.yml`).

**Trigger:** The developer is about to push the [change](../../../glossary.md#term-change--change).

**Main path:**

1. The developer runs the checks the [project](../../../glossary.md#term-project--project)'s merges wait on. In project-kit, `scripts/check.sh` runs them, the full test suite among them, and the pre-push hook `.githooks/pre-push` runs `scripts/check.sh` before each push (project rule 2).
2. Each check that compares the [change](../../../glossary.md#term-change--change) reads one [base](../../../glossary.md#term-base--base): `PKIT_CHECK_BASE` where set, else the remote's copy of the [default branch](../../../glossary.md#term-default-branch--default-branch) (COR-054 points 2 and 3).
3. `pkit validate` checks the working tree's state through every registered validator, the [backbone](../../../glossary.md#term-backbone--backbone)'s and each installed [component](../../../glossary.md#term-component--component)'s (COR-055 [point](../../../glossary.md#term-point--point) 3). It fails only on an `error` [finding](../../../glossary.md#term-finding--finding) (COR-055 point 5).
4. The checks that compare a change, such as `pkit friction check`, `pkit migrations check-diff` and `pkit decisions check-diff`, compare it with where the branch left the base.
5. Every check passes. In project-kit, the aggregator runs them all without stopping at the first failure, and ends with `✓ all checks passed`.
6. The developer pushes, and the CI pipeline runs the same checks on the [pull request](../../../glossary.md#term-pull-request--pull-request), with `PKIT_CHECK_BASE` naming its target and `PKIT_CHECK_HEAD` naming its [head](../../../glossary.md#term-head--head).

**Variants:**

- **1a.** A check fails, and the developer fixes what it found before pushing. In project-kit, the aggregator marks the check `FAILED` and ends with `✗ checks FAILED`. It exits non-zero, so the push stops. The path rejoins at step 1.
- **1b.** In project-kit, the clone has not opted into the hook, which `git config core.hooksPath .githooks` does. Nothing runs at the push, so the developer runs `scripts/check.sh` by hand.
- **1c.** The [project](../../../glossary.md#term-project--project)'s merges also wait on the [changeset](../../../glossary.md#term-changeset--changeset) guard, which needs the [pull request](../../../glossary.md#term-pull-request--pull-request)'s labels. project-kit's aggregator leaves it out, so the developer runs `pkit release check` by hand (UC-003).
- **2a.** The repository has no remote. The [default branch](../../../glossary.md#term-default-branch--default-branch) is read from the local branch, and a `warning:` line says so (COR-054 [point](../../../glossary.md#term-point--point) 2).
- **2b.** The [base](../../../glossary.md#term-base--base) resolves to no commit. Each check that has something to compare refuses (COR-054 point 4). It names its fixes: fetching the base, declaring the right default branch, or naming another base.
- **3a.** A registered validator cannot run, ends abnormally or overruns its time. It yields an `error` [finding](../../../glossary.md#term-finding--finding), never a clean pass. Where `pkit sync` has not provisioned its environment in this clone, it says "environment not provisioned — run `pkit sync`".
- **3b.** A [documentation root](../../../glossary.md#term-documentation-root--documentation-root) the [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration) declares does not exist yet. [Validation](../../../glossary.md#term-validation--validation) warns of it, and does not fail on it (REQ-015).
- **4a.** The base moved on after the branch left it. The [change check](../../../glossary.md#term-change-check--change-check) reports an `outdated-base` and passes. The developer merges the base and runs the checks again.
- **6a.** The developer pushes with `git push --no-verify`, so the hook does not run. The CI pipeline still runs the checks on the pull request.
- **6b.** In project-kit, the push changes only answers since the pull request's most recent full run in CI, which passed. The CI pipeline runs every check but the test suite on it (project rule 2). Where the hook ran, it ran the whole aggregator before the push.

**Postconditions:** Before the push, the developer has the result the [project](../../../glossary.md#term-project--project)'s checks give on the [change](../../../glossary.md#term-change--change), against the [base](../../../glossary.md#term-base--base) CI will name.

**Minimal guarantees:**

- A validator that gives no result fails [validation](../../../glossary.md#term-validation--validation), and never passes it (COR-055 [point](../../../glossary.md#term-point--point) 6).
- No [base](../../../glossary.md#term-base--base) named for one run reaches a validator (ADR-058 point 7). So `pkit validate` answers the same for the same working tree, HEAD, fetched history and default-branch commit.
- A base that resolves to no commit is reported with its fixes, and never guessed (COR-054 point 4).
