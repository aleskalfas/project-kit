---
id: UC-008
title: Release the backbone so adopters can upgrade and pin to it
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-ci-pipeline
  - ACT-operator
after:
  - [UC-014]
  - [UC-008, environment]
  - [UC-003]
  - [UC-034]
requirements:
  - REQ-005
  - REQ-009
  - REQ-012
shortfalls:
  - at: "1a"
    issue: "#1765"
    record: ADR-034#1
  - at: "1c"
    issue: "#1884"
    record: COR-004
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
        - scripts/latest_tag.py
      record:
        - PRJ-002#D2
        - PRJ-002#D3
        - PRJ-002#D4
        - PRJ-004
        - PRJ-007
        - COR-010
        - COR-004
        - ADR-034#1
        - ADR-061#6
      artefact:
        - ACT-methodology-maintainer
        - ACT-ci-pipeline
        - ACT-operator
        - REQ-005
        - REQ-009
        - REQ-012
    revalidated:
      at: 2026-10-25T14:39:29Z
      outcome: updated
---

# UC-008 — Release the backbone so adopters can upgrade and pin to it

**Goal:** Release the backbone so adopters can upgrade and pin to it, and know what each change since the last release means for them.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): opens the [release](../../../glossary.md#term-release--release) [pull request](../../../glossary.md#term-pull-request--pull-request). Once the release pull request lands, the pipeline tags the release commit, with no person there to confirm the push. No step of the CI pipeline's workflows merges a release pull request, so someone decides that each release lands (`release-pr.yml`).
- **Operator** (`ACT-operator`): is asked before `pkit release merge` or `pkit release apply` changes a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:**

- **From UC-014:** The [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository) runs the [system](../../../glossary.md#term-system--system) as written, so its [release step](../../../glossary.md#term-release-step--release-step) runs the code it releases.
- **From UC-008, or Environment:** The [default branch](../../../glossary.md#term-default-branch--default-branch) records the [backbone](../../../glossary.md#term-backbone--backbone)'s current [version](../../../glossary.md#term-version--version) in `.pkit/VERSION`. The last [release](../../../glossary.md#term-release--release) wrote it there, or, before the first release, the source repository held it (PRJ-002 D3).
- **From UC-003:** Each [change](../../../glossary.md#term-change--change) the release carries declares, in [changesets](../../../glossary.md#term-changeset--changeset), what it means for the release of the backbone or of a [component](../../../glossary.md#term-component--component).
- **From UC-034:** The changes the release carries landed on the default branch, so their changesets wait under `.changes/unreleased/`.

**Assumptions:**

- Each [changeset](../../../glossary.md#term-changeset--changeset)'s segment is a person's judgement of the [change](../../../glossary.md#term-change--change)'s surface, and the [release step](../../../glossary.md#term-release-step--release-step) takes the segment as written (PRJ-002 D2).
- Where the [release](../../../glossary.md#term-release--release) ships a [backbone](../../../glossary.md#term-backbone--backbone) [migration](../../../glossary.md#term-migration--migration) that adds a missing default, the changelog entry names that default, from a pending changeset. No command checks for that sentence, so the maintainer looks for it at step 8 (COR-010).

**Trigger:** The weekly schedule of `release-pr.yml` comes round, or the maintainer starts that workflow by hand.

**Main path:**

1. The CI pipeline runs `pkit release plan --json` on the [default branch](../../../glossary.md#term-default-branch--default-branch).
2. The [system](../../../glossary.md#term-system--system) groups the pending [changesets](../../../glossary.md#term-changeset--changeset) by what each names, the [backbone](../../../glossary.md#term-backbone--backbone) or a [component](../../../glossary.md#term-component--component), and takes the highest segment for each. It computes the new [version](../../../glossary.md#term-version--version) of the backbone and of each moving component from the versions the default branch carries.
3. The CI pipeline creates the branch `release/v<version>`, and runs `pkit release apply --yes` on it.
4. The system writes the [release](../../../glossary.md#term-release--release) into these files:
   - the new backbone version in `.pkit/VERSION`, and as `backbone_version` and `completed_version` in the self-host `.pkit/manifest.yaml` (PRJ-007)
   - each moving component's `version:` in its `package.yaml`
   - each component's `requires_backbone`, its upper bound widened to cover the new backbone's minor
   - each floor and upper bound a changeset declares (UC-009)
   - an entry at the top of `CHANGELOG.md`, from the notes of the changesets of the backbone and of each moving component
5. The system deletes the changesets it consumed.
6. The CI pipeline commits `chore(release): v<version>`, pushes the branch and opens the release [pull request](../../../glossary.md#term-pull-request--pull-request). The pull request's body lists these:
   - the move of the backbone and of each component, with the floors and upper bounds declared for it
   - any warning on a [migration](../../../glossary.md#term-migration--migration)'s folder
   - the new changelog entry
7. The CI pipeline runs the [project](../../../glossary.md#term-project--project)'s checks on the release pull request. The changeset guard reads the release pull request's diff as only what `pkit release apply` writes, and exempts that diff from the surface check (UC-003).
8. The maintainer reviews the new versions and the changelog entry.
9. The maintainer runs `pkit release merge <pr>`. The system checks that the pull request is a release pull request: a `release/` head branch under a `chore(release):` title.
14. At its entry, before it reads the pull request, `pkit release merge` checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012 and ADR-061 [point](../../../glossary.md#term-point--point) 6).
10. The system also checks that the release pull request is open, mergeable and green in every check it shows. The system lands the release pull request as one squash commit whose subject is the pull request's title, and deletes the head branch.
11. On the push to the default branch, the CI pipeline runs `release-tag.yml`. That workflow finds no tag for the version in `.pkit/VERSION`, and runs `pkit version tag --push`.
12. The system tags the release commit `v<version>` with an annotated tag, and pushes the tag (PRJ-004). The CI pipeline runs in no [harness](../../../glossary.md#term-harness--harness) session, so the cross-repository guard has nothing to compare with and does not fire. Nobody is asked to confirm the push (ADR-061 point 6).
13. The CI pipeline runs `pkit release publish-notes <version>`. The system publishes a GitHub release for the tag. The GitHub release's notes are that version's section of `CHANGELOG.md`.
15. Last, the CI pipeline runs `python3 scripts/latest_tag.py --push`. The script reads the remote's tags, and points the tag `latest` at the commit of the highest release, the release commit. It force-pushes `latest`, leased on the value it read, so `uv tool install` with `@latest` gets the new release (PRJ-004).

**Variants:**

- **1a.** The maintainer releases by hand. The maintainer runs `pkit release plan`, then runs `pkit release apply` on a [release](../../../glossary.md#term-release--release) branch, and confirms `Write these versions and consume the changesets?`. At its entry, before it prints its plan, `pkit release apply` checks the repository as step 14 does. The maintainer then commits the [release step](../../../glossary.md#term-release-step--release-step)'s writes and opens their release [pull request](../../../glossary.md#term-pull-request--pull-request), and the path goes on at step 7.

> [!WARNING]
> **Not built yet:** `pkit release apply` runs the check only when `--tag --push` asks it to push a tag. Without them, it writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **1b.** On the path of 1a, no pending [changeset](../../../glossary.md#term-changeset--changeset) moves a [version](../../../glossary.md#term-version--version). `pkit release apply` asks nothing, writes no version and no changelog entry, and deletes the pending `none` changesets. The use case ends.
- **1c.** On the path of 1a, the maintainer first passes `--dry-run` to `pkit release apply`, to see each edit it would make. The [system](../../../glossary.md#term-system--system) names each edit, and writes nothing (REQ-009).

> [!WARNING]
> **Not built yet:** `pkit release apply` takes no `--dry-run`, and refuses the flag. COR-004 decides that it offers one, and #1884 tracks it.

- **2a.** No pending changeset moves a version, as when only `none` changesets wait. `release-pr.yml` ends with `No pending changesets move a version — nothing to release.` The `none` changesets wait for the next release, and the use case ends.
- **2b.** A changeset names a [component](../../../glossary.md#term-component--component) the tree does not hold. The system refuses the release step, naming the changeset and the components it knows. `release-pr.yml` opens no pull request, and the use case ends.
- **2c.** A changeset declares a floor or an upper bound the release step cannot write. The system refuses before writing anything, such as with `cannot raise a requires_backbone floor:` and the changeset's problem. The use case ends.
- **2d.** The release step would leave a [capability](../../../glossary.md#term-capability--capability) whose [range](../../../glossary.md#term-range--range) excludes the version of a capability it depends on. The system refuses before writing anything, listing each such range, and the use case ends (PRJ-002 D4).
- **2e.** A [backbone](../../../glossary.md#term-backbone--backbone) [migration](../../../glossary.md#term-migration--migration)'s folder names a version above the current backbone's version, and the release step does not compute that version. The system warns that the folder `does not match the computed backbone release`, and goes on. The release pull request's body shows the warning (UC-010).
- **3a.** A release pull request is already open, on a `release/` branch. `release-pr.yml` opens no second one, and the use case ends.
- **7a.** The [project](../../../glossary.md#term-project--project) gave `release-pr.yml` no token of its own, so the release pull request starts no checks. The maintainer starts them by hand, and the path goes on at step 7. Where nobody starts them, the release pull request shows no check, and step 10 reads that as green.
- **9a.** The pull request is no release pull request. The system refuses it, saying that `pkit release merge` merges only release pull requests. Where the pull request's head branch is no `release/` branch, the refusal names `pkit pull-request land`, the backbone's own command for landing any other pull request. The use case ends.
- **10a.** The release pull request has a conflict, or a check that is red or still running. The system refuses with the reason, and merges nothing. The path rejoins at step 8.
- **10b.** Where merges into the [default branch](../../../glossary.md#term-default-branch--default-branch) go through a queue, the system enqueues the release pull request at the [head](../../../glossary.md#term-head--head) commit whose checks it read. The system then waits for the queue to merge the pull request. Where the wait ends with the release pull request still queued, the system exits 4 and deletes nothing. A later run deletes the head branch once the release pull request merges.
- **10c.** The queue does not squash, or its squash defaults are not the pull request's title and body. The system refuses, enqueues nothing, and the use case ends.
- **10d.** The queue drops the release pull request, or the release pull request's head commit moves after the checks were read. The system exits 3 and deletes nothing, and the path rejoins at step 7.
- **11a.** The version in `.pkit/VERSION` already has its tag, as after any push that is no release. `release-tag.yml` cuts no tag and publishes no notes, and the path goes on at step 15.
- **11b.** The run of `release-tag.yml` for the release push fails. The next push to the default branch finds the version untagged, and tags that push's commit instead of the release commit.
- **13a.** A release step that moved only components came between this release and the previous one. That step's changelog section is headed by its date, so no GitHub release's notes carry it (`release.py`).
- **15a.** `latest` already points at that commit, as after a push that is no release. The script pushes nothing.
- **15b.** Another run moved `latest` after this run read it, and the remote refuses the leased push. The script reads the remote's tags again. Where `latest` points at that commit, the run passes. Otherwise the run fails, `latest` stays where the other run put it, and the next push to the default branch runs step 15 again.
- **15c.** The remote holds a branch named `latest`, which uv can take before the tag. The script refuses, pushes nothing, and the run fails until someone deletes the branch.
- **14a.** The repository is another, and the operator declines. Or nobody can reply, and the maintainer passed no `--allow-foreign-repo`. The system refuses, merges nothing, and the use case ends.

**Postconditions:** The [release](../../../glossary.md#term-release--release) commit on the [default branch](../../../glossary.md#term-default-branch--default-branch) carries the tag `v<version>`, which adopters <!-- pkit:not-the-term -->install, upgrade to and pin (PRJ-004). The tag `latest` points at the same commit, so `uv tool install` with `@latest` gets this release. That [version](../../../glossary.md#term-version--version)'s changelog section, and the notes of its GitHub release, say what each [change](../../../glossary.md#term-change--change) the release carries means for adopters.

**Minimal guarantees:**

- A [release step](../../../glossary.md#term-release-step--release-step) the [system](../../../glossary.md#term-system--system) refuses for a [changeset](../../../glossary.md#term-changeset--changeset)'s declaration, or for a [range](../../../glossary.md#term-range--range), writes nothing. Each of those refusals comes before the first write (`release.py` and PRJ-002 D4).
- No workflow merges a [release](../../../glossary.md#term-release--release) [pull request](../../../glossary.md#term-pull-request--pull-request). A release pull request lands only when someone merges it (`release-pr.yml` and `release-tag.yml`).
- A [version](../../../glossary.md#term-version--version) is tagged once. `release-tag.yml` tags only a version with no tag, locally or on the remote, and `pkit version tag` refuses a tag the clone already holds (`versioning.py`).
- A GitHub release carries notes only, never a file to download (PRJ-004).
- A run of `release-tag.yml` never moves `latest` back to an older release. Its push is leased on the value it read (`scripts/latest_tag.py`).
- In a repository other than the session's own, `pkit release merge` changes nothing without the operator's yes or `--allow-foreign-repo` (REQ-012 and `session_guard.py`).
