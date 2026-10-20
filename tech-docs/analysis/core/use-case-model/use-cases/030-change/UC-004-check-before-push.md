---
id: UC-004
title: Know before I push that my change passes my project's checks
status: active
actor: ACT-developer
other-actors:
  - ACT-ci-pipeline
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
      artefact:
        - ACT-developer
        - ACT-ci-pipeline
    revalidated:
      at: 2026-10-20T01:38:23Z
      outcome: updated
---

# UC-004 — Know before I push that my change passes my project's checks

**Goal:** Know before I push that my change passes the checks my project gates its merges on.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the same checks on the pull request with no person to answer. It names the base once, for every check (COR-054 point 3).

**Preconditions:** The project runs the system: it is the methodology's source repository, or the system is installed in it.

**Assumptions:**

- The clone has fetched the default branch as the remote holds it. A check tells that its base moved on only as far as this clone can tell (COR-050 point 6).
- The pull request targets the branch the developer's checks read as their base, as project-kit's pull requests target the default branch (`.github/workflows/checks.yml`).

**Trigger:** The developer is about to push the change.

**Main path:**

1. The developer runs the checks the project's merges wait on. In project-kit, `scripts/check.sh` runs them, the full test suite among them, and the pre-push hook `.githooks/pre-push` runs `scripts/check.sh` before each push (project rule 2).
2. Each check that compares the change reads one base: `PKIT_CHECK_BASE` where set, else the remote's copy of the default branch (COR-054 points 2 and 3).
3. `pkit validate` checks the working tree's state through every registered validator, the backbone's and each installed component's (COR-055 point 3). It fails only on an `error` finding (COR-055 point 5).
4. The checks that compare a change, such as `pkit friction check`, `pkit migrations check-diff` and `pkit decisions check-diff`, compare it with where the branch left the base.
5. Every check passes. In project-kit, the aggregator runs them all without stopping at the first failure, and ends with `✓ all checks passed`.
6. The developer pushes, and the CI pipeline runs the same checks on the pull request, with `PKIT_CHECK_BASE` naming its target.

**Variants:**

- **1a.** A check fails, and the developer fixes what it found before pushing. In project-kit, the aggregator marks the check `FAILED` and ends with `✗ checks FAILED`. It exits non-zero, so the push stops. The path rejoins at step 1.
- **1b.** In project-kit, the clone has not opted into the hook, which `git config core.hooksPath .githooks` does. Nothing runs at the push, so the developer runs `scripts/check.sh` by hand.
- **1c.** The project's merges also wait on the changeset guard, which needs the pull request's labels. project-kit's aggregator leaves it out, so the developer runs `pkit release check` by hand (UC-003).
- **2a.** The repository has no remote. The default branch is read from the local branch, and a `warning:` line says so (COR-054 point 2).
- **2b.** The base resolves to no commit. Each check that has something to compare refuses (COR-054 point 4). It names its fixes: fetching the base, declaring the right default branch, or naming another base.
- **3a.** A registered validator cannot run, ends abnormally or overruns its time. It yields an `error` finding, never a clean pass. Where `pkit sync` has not provisioned its environment in this clone, it says "environment not provisioned — run `pkit sync`".
- **4a.** The base moved on after the branch left it. The change check reports an `outdated-base` and passes. The developer merges the base and runs the checks again.
- **6a.** The developer pushes with `git push --no-verify`, so the hook does not run. The CI pipeline still runs the checks on the pull request.

**Postconditions:** Before the push, the developer has the answer the project's checks give on the change, against the base CI will name.

**Minimal guarantees:**

- A validator that gives no answer fails validation, and never passes it (COR-055 point 6).
- No base named for one run reaches a validator (ADR-058 point 7). So `pkit validate` answers the same for the same working tree, HEAD, fetched history and default-branch commit.
- A base that resolves to no commit is reported with its fixes, and never guessed (COR-054 point 4).
