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

- **CI pipeline** (`ACT-ci-pipeline`): opens the release pull request. Once the release pull request lands, the pipeline tags the release commit, with no person there to confirm the push. No step of the CI pipeline's workflows merges a release pull request, so someone decides that each release lands (`release-pr.yml`).

**Preconditions:** Changesets wait under `.changes/unreleased/`, each declaring what a merged change means for the next release (UC-003).

**Assumptions:**

- Each changeset's segment is a person's judgement of the change's surface, and the release takes the segment as written (PRJ-002 D2).
- Where the release ships a backbone migration that adds a missing default, the changelog entry names that default, from a pending changeset. No command checks for that sentence, so the maintainer looks for it at step 8 (COR-010).

**Trigger:** The weekly schedule of `release-pr.yml` comes round, or the maintainer starts that workflow by hand.

**Main path:**

1. The CI pipeline runs `pkit release plan --json` on the default branch.
2. The system groups the pending changesets by what each names, the backbone or a component, and takes the highest segment for each. It computes the new version of the backbone and of each moving component from the versions the default branch carries.
3. The CI pipeline creates the branch `release/v<version>`, and runs `pkit release apply --yes` on it.
4. The system writes the release into these files:
   - the new backbone version in `.pkit/VERSION`, and as `backbone_version` and `completed_version` in the self-host `.pkit/manifest.yaml` (PRJ-007)
   - each moving component's `version:` in its `package.yaml`
   - each component's `requires_backbone`, its upper bound widened to cover the new backbone's minor
   - each floor and upper bound a changeset declares (UC-009)
   - an entry at the top of `CHANGELOG.md`, from the notes of the changesets of the backbone and of each moving component
5. The system deletes the changesets it consumed.
6. The CI pipeline commits `chore(release): v<version>`, pushes the branch and opens the release pull request. The pull request's body lists these:
   - the move of the backbone and of each component, with the floors and upper bounds declared for it
   - any warning on a migration's folder
   - the new changelog entry
7. The CI pipeline runs the project's checks on the release pull request. The changeset guard reads the release pull request's diff as only what `pkit release apply` writes, and exempts that diff from the surface check (UC-003).
8. The maintainer reviews the new versions and the changelog entry.
9. The maintainer runs `pkit release merge <pr>`. The system checks that the pull request is a release pull request: a `release/` head branch under a `chore(release):` title.
10. The system also checks that the release pull request is open, mergeable and green in every check it shows. The system lands the release pull request as one squash commit whose subject is the pull request's title, and deletes the head branch.
11. On the push to the default branch, the CI pipeline runs `release-tag.yml`. That workflow finds no tag for the version in `.pkit/VERSION`, and runs `pkit version tag --push`.
12. The system tags the release commit `v<version>` with an annotated tag, and pushes the tag (PRJ-004). The CI pipeline runs in no harness session, so the cross-repository guard has nothing to compare with and does not fire. Nobody is asked to confirm the push (ADR-061 point 6).
13. The CI pipeline runs `pkit release publish-notes <version>`. The system publishes a GitHub release for the tag. The GitHub release's notes are that version's section of `CHANGELOG.md`.

**Variants:**

- **1a.** The maintainer releases by hand. The maintainer runs `pkit release plan`, then runs `pkit release apply` on a release branch, and confirms `Write these versions and consume the changesets?`. The maintainer then commits the release and opens its release pull request, and the path goes on at step 7.
- **1b.** On the path of 1a, no pending changeset moves a version. `pkit release apply` asks nothing, writes no version and no changelog entry, and deletes the pending `none` changesets. The use case ends.
- **2a.** No pending changeset moves a version, as when only `none` changesets wait. `release-pr.yml` ends with `No pending changesets move a version — nothing to release.` The `none` changesets wait for the next release, and the use case ends.
- **2b.** A changeset names a component the tree does not hold. The system refuses the release, naming the changeset and the components it knows. `release-pr.yml` opens no pull request, and the use case ends.
- **2c.** A changeset declares a floor or an upper bound the release cannot write. The system refuses before writing anything, such as with `cannot raise a requires_backbone floor:` and the changeset's problem. The use case ends.
- **2d.** The release would leave a capability whose range excludes the version of a capability it depends on. The system refuses before writing anything, listing each such range, and the use case ends (PRJ-002 D4).
- **2e.** A backbone migration's folder names a version above the current backbone's version, and the release does not compute that version. The system warns that the folder `does not match the computed backbone release`, and goes on. The release pull request's body shows the warning (UC-010).
- **3a.** A release pull request is already open, on a `release/` branch. `release-pr.yml` opens no second one, and the use case ends.
- **7a.** The project gave `release-pr.yml` no token of its own, so the release pull request starts no checks. The maintainer starts them by hand, and the path goes on at step 7. Where nobody starts them, the release pull request shows no check, and step 10 reads that as green.
- **9a.** The pull request is no release pull request. The system refuses it, and points to `pkit project-management merge-pr` for an issue's pull request. The use case ends.
- **10a.** The release pull request has a conflict, or a check that is red or still running. The system refuses with the reason, and merges nothing. The path rejoins at step 8.
- **10b.** Merges into the default branch go through a queue. The system enqueues the release pull request at the head commit whose checks it read. The system then waits for the queue to merge the pull request. Where the wait ends with the release pull request still queued, the system exits 4 and deletes nothing. A later run deletes the head branch once the release pull request merges.
- **10c.** The queue does not squash, or its squash defaults are not the pull request's title and body. The system refuses, enqueues nothing, and the use case ends.
- **10d.** The queue drops the release pull request, or the release pull request's head commit moves after the checks were read. The system exits 3 and deletes nothing, and the path rejoins at step 7.
- **11a.** The version in `.pkit/VERSION` already has its tag, as after any push that is no release. `release-tag.yml` cuts no tag and publishes no notes.
- **11b.** The run of `release-tag.yml` for the release push fails. The next push to the default branch finds the version untagged, and tags that push's commit instead of the release commit.
- **13a.** A release that moved only components came between this release and the previous backbone release. That release's changelog section is headed by its date, so no GitHub release's notes carry it (`release.py`).

**Postconditions:** The release commit on the default branch carries the tag `v<version>`, which adopters install, upgrade to and pin (PRJ-004). That version's changelog section, and the notes of its GitHub release, say what each change the release carries means for adopters.

**Minimal guarantees:**

- A release the system refuses for a changeset's declaration, or for a range, writes nothing. Each of those refusals comes before the first write (`release.py` and PRJ-002 D4).
- No workflow merges a release pull request. A release pull request lands only when someone merges it (`release-pr.yml` and `release-tag.yml`).
- A version is tagged once. `release-tag.yml` tags only a version with no tag, locally or on the remote, and `pkit version tag` refuses a tag the clone already holds (`versioning.py`).
- A GitHub release carries notes only, never a file to install from (PRJ-004).
