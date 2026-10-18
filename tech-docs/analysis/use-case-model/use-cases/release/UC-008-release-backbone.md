---
id: UC-008
title: Release the backbone so adopters can upgrade and pin to it
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-ci-pipeline
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/release.py
        - src/project_kit/versioning.py
        - src/project_kit/changesets.py
        - src/project_kit/cli.py
        - src/project_kit/pull_request_landing.py
        - src/project_kit/session_guard.py
        - .github/workflows/release-pr.yml
        - .github/workflows/release-tag.yml
      record:
        - PRJ-002#D2
        - PRJ-002#D3
        - PRJ-002#D4
        - PRJ-004
        - PRJ-007
        - COR-010
        - ADR-061#6
      artefact:
        - ACT-methodology-maintainer
        - ACT-ci-pipeline
---

# UC-008 — Release the backbone so adopters can upgrade and pin to it

**Goal:** Release the backbone so adopters can upgrade and pin to it, and know what each change since the last release means for them.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): opens the release pull request, and tags the release once it lands, with no person there to confirm the push. It holds no right to merge, so a person decides that each release lands (`release-pr.yml`).

**Preconditions:** Changesets wait under `.changes/unreleased/`, each declaring what a merged change means for the next release (UC-003).

**Assumptions:**

- Each changeset's segment is a person's judgement of the change's surface, and the release takes it as written (PRJ-002 D2).
- Where the release ships a backbone migration that adds a missing default, a pending changeset names that default. No command checks it, so whoever releases checks it (COR-010).

**Trigger:** The weekly schedule of `release-pr.yml` comes round, or the maintainer starts the workflow by hand.

**Main path:**

1. The CI pipeline runs `pkit release plan --json` on the default branch.
2. The system groups the pending changesets by component, and takes the highest segment of each. It computes each moving component's new version from the version the default branch carries.
3. The CI pipeline creates the branch `release/v<version>`, and runs `pkit release apply --yes` on it.
4. The system writes the release into these files:
   - the new backbone version in `.pkit/VERSION`, and as `backbone_version` and `completed_version` in the self-host `.pkit/manifest.yaml` (PRJ-007)
   - each moving component's `version:` in its `package.yaml`
   - each component's `requires_backbone`, its upper bound widened to cover the new backbone's minor
   - each floor and upper bound a changeset declares (UC-009)
   - an entry at the top of `CHANGELOG.md`, from the notes of each moving component's changesets
5. The system deletes the changesets it consumed.
6. The CI pipeline commits `chore(release): v<version>`, pushes the branch and opens the release pull request. The pull request's body lists each version's move with its declared floors and bounds, any warning on a migration's folder, and the new changelog entry.
7. The CI pipeline runs the project's checks on the release pull request. The changeset guard reads its diff as only what `pkit release apply` writes, and exempts it from the surface check (UC-003).
8. The maintainer reviews the new versions and the changelog entry.
9. The maintainer runs `pkit release merge <pr>`. The system checks that the pull request is a release one, with a `release/` head branch and a `chore(release):` title.
10. The system also checks that the pull request is open, mergeable and green in every required check. It lands the pull request as one squash commit whose subject is its title, and deletes the head branch.
11. On the push to the default branch, the CI pipeline runs `release-tag.yml`. The workflow finds no tag for the version in `.pkit/VERSION`, and runs `pkit version tag --push`.
12. The system tags the release commit `v<version>` with an annotated tag, and pushes the tag (PRJ-004). The pipeline holds no session's anchor, so the cross-repository guard does not fire, and nobody is asked to confirm the push (ADR-061 point 6).
13. The CI pipeline runs `pkit release publish-notes <version>`. The system publishes a GitHub release for the tag, whose notes are that version's section of `CHANGELOG.md`.

**Variants:**

- **1a.** The maintainer releases by hand. The maintainer runs `pkit release plan`, then `pkit release apply` on a release branch, and confirms `Write these versions and consume the changesets?`. The maintainer then commits the release and opens its pull request, and the path goes on at step 7.
- **2a.** No pending changeset moves a version, as when only `none` changesets wait. The workflow ends with `No pending changesets move a version — nothing to release.` The `none` changesets wait for the next release, and the use case ends.
- **2b.** A changeset names a component the tree does not hold. The system refuses the release, naming the changeset and the components it knows. The workflow opens no pull request, and the use case ends.
- **2c.** A changeset declares a floor or an upper bound the release cannot write. The system refuses before writing anything, such as with `cannot raise a requires_backbone floor:` and the changeset's problem. The use case ends.
- **2d.** The release would leave a capability whose range excludes the version of a capability it depends on. The system refuses before writing anything, listing each such range, and the use case ends (PRJ-002 D4).
- **2e.** A backbone migration's folder names a version above the current backbone that the release does not compute. The system warns that the folder `does not match the computed backbone release`, and goes on. The release pull request's body shows the warning (UC-010).
- **3a.** A release pull request is already open, on a `release/` branch. The workflow opens no second one, and the use case ends.
- **7a.** The project gave the workflow no token of its own, so the release pull request starts no checks (`release-pr.yml`). The maintainer starts them by hand, and the path goes on at step 7.
- **9a.** The pull request is no release one. The system refuses it, and points to `pkit project-management merge-pr` for an issue's pull request. The use case ends.
- **10a.** The pull request has a conflict, or a required check that is red or still running. The system refuses with the reason, and merges nothing. The path rejoins at step 8.
- **10b.** The default branch merges through a queue. The system enqueues the pull request at the head whose checks it read, and waits for the queue to merge it. Where the wait ends with the pull request still queued, the system exits 4 and deletes nothing. A later run deletes the head branch once the pull request merges.
- **10c.** The queue drops the pull request, or its head moves after the checks were read. The system exits 3 and deletes nothing, and the path rejoins at step 7.
- **11a.** The version in `.pkit/VERSION` already has its tag, as after any push that is no release. The workflow cuts no tag and publishes no notes.

**Postconditions:** The release commit on the default branch carries the tag `v<version>`, which adopters install, upgrade to and pin (PRJ-004). That version's changelog section, and the notes of its GitHub release, say what each change since the last release means for adopters.

**Minimal guarantees:**

- A release the system refuses writes nothing. Each refusal of a changeset's declaration or of a range comes before the first write (`release.py` and PRJ-002 D4).
- Nothing merges a release on its own. The workflows hold no right to merge, so a person merges each release pull request (`release-pr.yml`).
- A version is tagged once. `pkit version tag` refuses a tag that exists, and the workflow tags only a version without one (`versioning.py` and `release-tag.yml`).
- A GitHub release carries notes only, never a file to install from (PRJ-004).
