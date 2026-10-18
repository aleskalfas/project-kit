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
        - .github/workflows/checks.yml
      record:
        - PRJ-002#D1
        - PRJ-002#D2
        - PRJ-002#D4
        - COR-054#4
      artefact:
        - ACT-developer
        - ACT-ci-pipeline
---

# UC-003 — Declare what my change means for the next release

**Goal:** Declare what my change means for the next release in a changeset that names each component and the segment I judge.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the changeset guard on the pull request with no person to answer. It reads the `skip-changeset` label as the guard's escape hatch.

**Preconditions:** The project declares its releases in changesets under `.changes/unreleased/`, as project-kit does (PRJ-002 D1).

**Assumptions:**

- Surface is a person's judgement. The guard reads only paths, so it can flag a change that moves no surface, or miss one that does. Review still judges the surface (PRJ-002 D2).
- The change edits no version number, such as `.pkit/VERSION` or a component's `version`, since only the release writes them (PRJ-002 D1).

**Trigger:** The developer's change touches the surface of a component, or of the backbone.

**Main path:**

1. The developer judges which components the change's surface moves, and by which segment: `patch`, `minor`, `major` or `none`.
2. The developer adds a changeset for each under `.changes/unreleased/`, with `changie new` or by hand, giving its `component`, `kind` and `body`.
3. The developer commits the changesets, and runs `pkit release lint` to check their format.
4. The developer runs `pkit release check`, which compares the committed change with where the branch left its base.
5. The system finds each component whose files the change touches, and checks that a changeset the change adds or edits names it.
6. The system passes: `changeset guard: every touched component has a changeset in this diff — ok.`
7. The CI pipeline runs `pkit release check` with `--base` naming the pull request's target, and the guard passes.

**Variants:**

- **1a.** The change moves no surface, such as an internal refactor. The developer adds no changeset, and the path goes on at step 4.
- **1b.** The component comes to need a backbone, or a version of another capability. Its changeset says so in `requires_backbone` or `requires_capabilities`, as `release` or a shipped version, and the release raises the floor (PRJ-002 D4).
- **2a.** The change records a decision. A decision whose feature ships later declares `none`, and one whose text itself changes what adopters do declares a real segment (PRJ-002).
- **3a.** A changeset's format is wrong, such as a `body` that is no sentence. `pkit release lint` names it, and the path rejoins at step 2.
- **4a.** The base resolves to no commit. The guard refuses, naming the fix, and the use case ends.
- **6a.** A touched component has no changeset in the change. The guard fails with `surface change without a changeset for: <component>.`, naming the fixes. They are a changeset, a `none` changeset, or the `skip-changeset` label, and the path rejoins at step 2.
- **6b.** Only a pending changeset that the change leaves alone names the component. It declares another pull request's change, so it does not count, and the guard fails as in 6a.
- **6c.** A changeset declares a floor for a component the change neither touches nor moves. The guard fails, and no escape hatch waives it (PRJ-002 D4).
- **6d.** The change edits the range of an existing `requires_capabilities` entry, other than to correct one that excludes the version the tree carries. The guard fails, and no escape hatch waives it (PRJ-002 D1).
- **6e.** The change is only what `pkit release apply` writes. The guard reads it as a release pull request, and exempts it from the surface check.
- **7a.** The pull request carries the `skip-changeset` label. The CI pipeline passes it to the guard as `PKIT_CHANGESET_SKIP`, which skips the surface check, and the guard still checks floors and range edits.

**Postconditions:** For each component whose surface the change moves, a changeset in the change names it and its segment, and waits under `.changes/unreleased/` for the release.

**Minimal guarantees:**

- No escape hatch waives a floor declared for a component the change leaves alone (PRJ-002 D4). None waives a branch's edit of an existing range either (PRJ-002 D1).
- A changeset counts only where the change adds or edits it, so another pull request's declaration never passes this one (`release.py`).
- A base that resolves to no commit refuses the run with its fix, and is never guessed (COR-054 point 4).
