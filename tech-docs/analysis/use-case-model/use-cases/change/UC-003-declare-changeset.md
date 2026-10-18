---
id: UC-003
title: Declare what my change means for the next release
status: active
actor: ACT-developer
other-actors:
  - ACT-ci-pipeline
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
    revalidated:
      at: 2026-10-18T20:04:41Z
      outcome: unchanged
      unchanged-because: This change stops release apply writing, and release plan listing, the note of a none changeset. The use case covers declaring changesets and the guard that checks them, which this change leaves as they were.
---

# UC-003 — Declare what my change means for the next release

**Goal:** Declare what my change means for the next release, in changesets naming what it moves, the backbone or a component, and the segment I judge.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the changeset guard on the pull request with no person to answer. It reads the `skip-changeset` label as the guard's escape hatch.

**Preconditions:** The project declares its releases in changesets under `.changes/unreleased/`, as project-kit does (PRJ-002 D1).

**Assumptions:**

- Surface is a person's judgement (PRJ-002 D2). The guard reads only paths, so it can flag a change that moves no surface, or miss one that does (`release.py`).
- The change edits no version number, such as `.pkit/VERSION` or a component's `version`, since only the release writes them (PRJ-002 D1).

**Trigger:** The developer's change touches the surface of the backbone or of a component.

**Main path:**

1. The developer judges whose surface the change moves, the backbone's or a component's, and by which segment: `patch`, `minor`, `major` or `none`.
2. The developer adds a changeset for each under `.changes/unreleased/`, with `changie new` or by hand. Each gives its `component`, `kind` and `body`.
3. The developer commits the changesets, and runs `pkit release lint` to check their format.
4. The developer runs `pkit release check`, which compares the committed change with where the branch left its base.
5. The system finds the backbone and each component whose paths the change touches. It checks that a changeset the change adds or edits names each one.
6. The system passes: `changeset guard: every touched component has a changeset in this diff — ok.`
7. The CI pipeline runs `pkit release check` with `--base` naming the pull request's target, and the guard passes.

**Variants:**

- **1a.** The change touches no path of the backbone or of a component, such as a change to `tech-docs/` alone. The developer adds no changeset, and the path goes on at step 4.
- **1b.** The change moves no surface, yet touches a component's paths, such as an internal refactor under `src/project_kit/`. The developer adds a `none` changeset for it, and the path goes on at step 3.
- **1c.** What the change moves comes to need a backbone, or a version of another capability. Its changeset says so in `requires_backbone`, `requires_capabilities` or `runs_on_capabilities`, as `release` or a shipped version. The release then raises the floor, or widens the bound (PRJ-002 D4).
- **2a.** The change records a decision. Its changeset declares `none` where the decision's feature ships in a later change. Where the decision's text itself changes what adopters do, it declares `patch` or above (PRJ-002).
- **3a.** A changeset's format is wrong, such as a `body` that is no sentence. `pkit release lint` names it, and the path rejoins at step 2.
- **4a.** The base resolves to no commit. The guard refuses and names the fix. The use case ends.
- **6a.** A touched component has no changeset in the change. The guard fails with `surface change without a changeset for: <component>.`, naming the fixes. They are a changeset, a `none` changeset, or the `skip-changeset` label, and the path rejoins at step 2.
- **6b.** Only a pending changeset that the change leaves alone names the component. It declares another pull request's change, so it does not count. The guard fails as in 6a.
- **6c.** A changeset declares a floor or an upper bound for a component the change neither touches nor moves. The guard fails, and no escape hatch waives it (PRJ-002 D4).
- **6d.** The change edits the range of an existing `requires_capabilities` entry, other than to correct one that excludes the version the tree carries. The guard fails, and no escape hatch waives it (`release.py`).
- **6e.** The change is only what `pkit release apply` writes. The guard reads it as a release pull request, and exempts it from the surface check.
- **7a.** The pull request carries the `skip-changeset` label. The CI pipeline passes it to the guard as `PKIT_CHANGESET_SKIP`, which skips the surface check. The guard still checks floors, bounds and range edits.
- **7b.** The pull request reaches a merge queue. The guard does not run on the queue's merge, which carries no labels, since it judged the pull request's diff already.

**Postconditions:** For the backbone and each component whose surface the change moves, a changeset in the change names it and its segment. Each waits under `.changes/unreleased/` for the release.

**Minimal guarantees:**

- No escape hatch waives a floor or an upper bound declared for a component the change neither touches nor moves (PRJ-002 D4).
- No escape hatch waives a branch's edit of an existing range either (`release.py`).
- A changeset counts only where the change adds or edits it, so another pull request's declaration never passes this one (`release.py`).
- A base that resolves to no commit refuses the run with its fix, and is never guessed (COR-054 point 4).
