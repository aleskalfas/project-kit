---
id: UC-003
title: Declare what my change means for the next release
status: active
actor: ACT-developer
other-actors:
  - ACT-ci-pipeline
requirements:
  - REQ-004
  - REQ-005
after:
  - [UC-014, UC-049]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/changesets.py
        - src/project_kit/release.py
        - src/project_kit/cli.py
        - .github/workflows/checks.yml
      record:
        - PRJ-002#D1
        - PRJ-002#D2
        - PRJ-002#D4
        - COR-054#4
      artefact:
        - ACT-developer
        - ACT-ci-pipeline
        - REQ-004
        - REQ-005
---

# UC-003 — Declare what my change means for the next release

**Goal:** Declare what my change means for the next release, in changesets naming what it moves, the backbone or a component, and the segment I judge.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the [changeset](../../../glossary.md#term-changeset--changeset) guard on the [pull request](../../../glossary.md#term-pull-request--pull-request) with no person to reply. It reads the `skip-changeset` label as the guard's escape hatch.

**Preconditions:** **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](../050-adopt/UC-049-install-system.md):** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:**

- The [project](../../../glossary.md#term-project--project) declares, in [changesets](../../../glossary.md#term-changeset--changeset) under `.changes/unreleased/`, what each [change](../../../glossary.md#term-change--change) means for its [release step](../../../glossary.md#term-release-step--release-step), as project-kit does ([PRJ-002 D1](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d1--surface-changes-are-declared-not-applied-per-pr)).
- Surface is a person's judgement ([PRJ-002 D2](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d2--the-bump-segment-is-a-human-surface-judgment-not-a-function-of-the-commit-type)). The guard reads only paths, so it can flag a change that moves no surface, or miss one that does (`release.py`).
- The change edits no [version](../../../glossary.md#term-version--version) number, such as `.pkit/VERSION` or a [component](../../../glossary.md#term-component--component)'s `version`, since only the release step writes them (PRJ-002 D1).

**Trigger:** The developer's [change](../../../glossary.md#term-change--change) touches the surface of the [backbone](../../../glossary.md#term-backbone--backbone) or of a [component](../../../glossary.md#term-component--component).

**Main path:**

1. The developer judges whose surface the [change](../../../glossary.md#term-change--change) moves, the [backbone](../../../glossary.md#term-backbone--backbone)'s or a [component](../../../glossary.md#term-component--component)'s, and by which segment: `patch`, `minor`, `major` or `none`.
2. The developer adds a [changeset](../../../glossary.md#term-changeset--changeset) for each under `.changes/unreleased/`, with `changie new` or by hand. Each gives its `component`, `kind` and `body`.
3. The developer commits the changesets, and runs `pkit release lint` to check their format.
4. The developer runs `pkit release check`, which compares the committed change with where the branch left its [base](../../../glossary.md#term-base--base).
5. The [system](../../../glossary.md#term-system--system) finds the backbone and each component whose paths the change touches. It checks that a changeset the change adds or edits names each one.
6. The system passes: `changeset guard: every touched component has a changeset in this diff — ok.`
7. The CI pipeline runs `pkit release check` with `--base` naming the [pull request](../../../glossary.md#term-pull-request--pull-request)'s target, and the guard passes.

**Variants:**

- **1a.** The [change](../../../glossary.md#term-change--change) touches no path of the [backbone](../../../glossary.md#term-backbone--backbone) or of a [component](../../../glossary.md#term-component--component), such as a change to `tech-docs/` alone. The developer adds no [changeset](../../../glossary.md#term-changeset--changeset), and the path goes on at step 4.
- **1b.** The change moves no surface, yet touches a component's paths, such as an internal refactor under `src/project_kit/`. The developer adds a `none` changeset for it, and the path goes on at step 3.
- **1c.** What the change moves comes to need a backbone, or a [version](../../../glossary.md#term-version--version) of another [capability](../../../glossary.md#term-capability--capability). Its changeset says so in `requires_backbone`, `requires_capabilities` or `runs_on_capabilities`, as `release` or a shipped version. The [release step](../../../glossary.md#term-release-step--release-step) then raises the floor, or widens the bound ([PRJ-002 D4](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d4--the-release-step-writes-every-floor-and-upper-bound-and-a-floor-rises-only-in-a-final-release)).
- **2a.** The change records a decision. Its changeset declares `none` where the decision's feature ships in a later change. Where the decision's text itself changes what adopters do, it declares `patch` or above ([PRJ-002](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)).
- **3a.** A changeset's format is wrong, such as a `body` that is no sentence. `pkit release lint` names it, and the path rejoins at step 2.
- **4a.** The [base](../../../glossary.md#term-base--base) resolves to no commit. The guard refuses and names the fix. The use case ends.
- **6a.** A touched component has no changeset in the change. The guard fails with `surface change without a changeset for: <component>.`, naming the fixes. They are a changeset, a `none` changeset, or the `skip-changeset` label, and the path rejoins at step 2.
- **6b.** Only a pending changeset that the change leaves alone names the component. It declares another [pull request](../../../glossary.md#term-pull-request--pull-request)'s change, so it does not count. The guard fails as in 6a.
- **6c.** A changeset declares a floor or an upper bound for a component the change neither touches nor moves. The guard fails, and no escape hatch waives it ([PRJ-002 D4](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d4--the-release-step-writes-every-floor-and-upper-bound-and-a-floor-rises-only-in-a-final-release)).
- **6d.** The change edits the [range](../../../glossary.md#term-range--range) of an existing `requires_capabilities` entry, other than to correct one that excludes the version the tree carries. The guard fails, and no escape hatch waives it (`release.py`).
- **6e.** The change is only what `pkit release apply` writes. The guard reads it as a [release](../../../glossary.md#term-release--release) pull request, and exempts it from the surface check.
- **7a.** The pull request carries the `skip-changeset` label. The CI pipeline passes it to the guard as `PKIT_CHANGESET_SKIP`, which skips the surface check. The guard still checks floors, bounds and range edits.
- **7b.** The pull request reaches a merge queue. The guard does not run on the queue's merge, which carries no labels, since it judged the pull request's diff already.

**Postconditions:** For the [backbone](../../../glossary.md#term-backbone--backbone) and each [component](../../../glossary.md#term-component--component) whose surface the [change](../../../glossary.md#term-change--change) moves, a [changeset](../../../glossary.md#term-changeset--changeset) in the change names it and its segment. Each waits under `.changes/unreleased/` for the next [release step](../../../glossary.md#term-release-step--release-step).

**Minimal guarantees:**

- No escape hatch waives a floor or an upper bound declared for a [component](../../../glossary.md#term-component--component) the [change](../../../glossary.md#term-change--change) neither touches nor moves ([PRJ-002 D4](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d4--the-release-step-writes-every-floor-and-upper-bound-and-a-floor-rises-only-in-a-final-release)).
- No escape hatch waives a branch's edit of an existing [range](../../../glossary.md#term-range--range) either (`release.py`).
- A [changeset](../../../glossary.md#term-changeset--changeset) counts only where the change adds or edits it, so another [pull request](../../../glossary.md#term-pull-request--pull-request)'s declaration never passes this one (`release.py`).
- A [base](../../../glossary.md#term-base--base) that resolves to no commit refuses the run with its fix, and is never guessed ([COR-054 point 4](../../../../../../.pkit/decisions/core/COR-054-default-branch.md#4-unresolved-report-never-guess)).
