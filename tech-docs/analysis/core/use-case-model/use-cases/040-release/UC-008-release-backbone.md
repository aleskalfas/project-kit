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
        - src/project_kit/stranded_migrations.py
        - .github/workflows/release-pr.yml
        - .github/workflows/release-tag.yml
        - scripts/latest_tag.py
        - scripts/release_pr.py
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
        - ADR-061#8
        - ADR-092#6
        - ADR-092#8
      artefact:
        - ACT-methodology-maintainer
        - ACT-ci-pipeline
        - ACT-operator
        - REQ-005
        - REQ-009
        - REQ-012
---

# UC-008 — Release the backbone so adopters can upgrade and pin to it

**Goal:** Release the backbone so adopters can upgrade and pin to it, and know what each change since the last release means for them.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): opens the [release pull request](../../../glossary.md#term-release-pull-request--release-pull-request). Once the release pull request lands, the pipeline puts a [release tag](../../../glossary.md#term-release-tag--release-tag) on the commit it landed, with no person there to confirm the push. No step of the CI pipeline's workflows merges a release pull request, so someone decides that each [release](../../../glossary.md#term-release--release) lands (`release-pr.yml`).
- **Operator** (`ACT-operator`): is asked before `pkit release merge` or `pkit release apply` changes a repository other than the session's own. So no such write happens silently ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:**

- **From [UC-014](../010-develop/UC-014-develop-methodology.md):** The [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository) runs the [system](../../../glossary.md#term-system--system) as written, so its [release step](../../../glossary.md#term-release-step--release-step) runs the code it releases.
- **From UC-008, or Environment:** The [default branch](../../../glossary.md#term-default-branch--default-branch) records the [backbone](../../../glossary.md#term-backbone--backbone)'s current [version](../../../glossary.md#term-version--version) in `.pkit/VERSION`. The last [release](../../../glossary.md#term-release--release) wrote it there, or, before the first release, the source repository held it ([PRJ-002 D3](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d3--every-version-that-reaches-main-is-written-there-by-the-release-pr)).
- **From [UC-003](../030-change/UC-003-declare-changeset.md):** Each [change](../../../glossary.md#term-change--change) the release carries declares, in [changesets](../../../glossary.md#term-changeset--changeset), what it means for the release of the backbone or of a [component](../../../glossary.md#term-component--component).
- **From [UC-034](../030-change/UC-034-land-change.md):** The changes the release carries landed on the default branch, so their changesets wait under `.changes/unreleased/`.

**Assumptions:**

- Each [changeset](../../../glossary.md#term-changeset--changeset)'s [bump segment](../../../glossary.md#term-bump-segment--bump-segment) is a person's judgement of the [change](../../../glossary.md#term-change--change)'s [surface](../../../glossary.md#term-surface--surface), and the [release step](../../../glossary.md#term-release-step--release-step) takes the bump segment as written ([PRJ-002 D2](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d2--the-bump-segment-is-a-human-surface-judgment-not-a-function-of-the-commit-type)).
- Where the [release](../../../glossary.md#term-release--release) ships a [backbone](../../../glossary.md#term-backbone--backbone) [migration](../../../glossary.md#term-migration--migration) that adds a missing default, the changelog entry names that default, from a pending changeset. No command checks for that sentence, so the maintainer looks for it at step 8 ([COR-010](../../../../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)).

**Trigger:** The maintainer starts `release-pr.yml` by hand.

**Main path:**

1. The CI pipeline runs `pkit release plan --json` on the [default branch](../../../glossary.md#term-default-branch--default-branch).
2. The [system](../../../glossary.md#term-system--system) groups the pending [changesets](../../../glossary.md#term-changeset--changeset) by what each names, the [backbone](../../../glossary.md#term-backbone--backbone) or a [component](../../../glossary.md#term-component--component), and takes the highest [bump segment](../../../glossary.md#term-bump-segment--bump-segment) for each. It computes the new [version](../../../glossary.md#term-version--version) of the backbone and of each moving component from the versions the default branch carries.
3. The CI pipeline creates the branch `release/v<version>`, and runs `pkit release apply --yes` on it.
4. The system writes the [release](../../../glossary.md#term-release--release) into these files:
   - the new backbone version in `.pkit/VERSION`, and as `backbone_version` and `completed_version` in the self-host `.pkit/manifest.yaml` ([PRJ-007](../../../../../../.pkit/decisions/project/PRJ-007-release-maintains-self-host-manifest.md))
   - each moving component's `version:` in its `package.yaml`
   - each component's `requires_backbone`, its upper bound widened to cover the new backbone's minor
   - each floor and upper bound a changeset declares ([UC-009](UC-009-release-component.md))
   - an entry at the top of `CHANGELOG.md`, from the notes of the changesets of the backbone and of each moving component
5. The system deletes the changesets it consumed. Last, it prints a line naming the commit of the default branch the release was planned from, `Release-plan-commit: <commit>` ([ADR-092 point 6](../../../../../architecture/decisions/ADR-092-final-release-from-head.md#6-a-release-pr-lands-only-what-its-release-step-wrote-onto-the-commit-its-plan-read)).
6. The CI pipeline commits `chore(release): v<version>`, with that line as the message's last paragraph. It pushes the branch and opens the [release pull request](../../../glossary.md#term-release-pull-request--release-pull-request). The [pull request](../../../glossary.md#term-pull-request--pull-request)'s body lists these:
   - the move of the backbone and of each component, with the floors and upper bounds declared for it
   - any warning on a [migration](../../../glossary.md#term-migration--migration)'s folder
   - the new changelog entry
   - last, the line naming the commit the release was planned from
7. The CI pipeline runs the [project](../../../glossary.md#term-project--project)'s checks on the release pull request. The [changeset guard](../../../glossary.md#term-changeset-guard--changeset-guard) reads the release pull request's diff as only what `pkit release apply` writes, with any answers those writes need. The guard exempts that diff from the [surface](../../../glossary.md#term-surface--surface) check ([UC-003](../030-change/UC-003-declare-changeset.md)).
8. The maintainer reviews the new versions and the changelog entry.
9. The maintainer runs `pkit release merge <pr>`. The system checks that the pull request is a release pull request: a `release/` head branch under a `chore(release):` title.
14. At its entry, before it reads the pull request, `pkit release merge` checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md) and [ADR-061 point 6](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#6-the-command-guards-the-changes-it-makes)).
10. The system also checks that the release pull request is open, mergeable and green in every check it shows. The system then reads the default branch's [head](../../../glossary.md#term-head--head) from the remote, which must be the commit the release was planned from. The release must hold only what the [release step](../../../glossary.md#term-release-step--release-step) wrote and the [answer files](../../../glossary.md#term-answer-file--answer-file) it adds (ADR-092 point 6). The system lands one squash commit whose subject and body are the pull request's title and body, and deletes the head branch.
11. On the push to the default branch, the CI pipeline runs `release-tag.yml`. That workflow finds no tag for the version in `.pkit/VERSION`, and runs `pkit version tag --push`.
12. The system puts the [release tag](../../../glossary.md#term-release-tag--release-tag) `v<version>`, an annotated tag, on the commit the release pull request landed, and pushes the tag ([PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)). The CI pipeline runs in no [harness](../../../glossary.md#term-harness--harness) session, so the [cross-repository guard](../../../glossary.md#term-cross-repository-guard--cross-repository-guard) has nothing to compare with and does not fire. Nobody is asked to confirm the push (ADR-061 point 6).
13. The CI pipeline runs `pkit release publish-notes <version>`. The system publishes a GitHub release for the release tag. The GitHub release's notes are that version's section of `CHANGELOG.md`.
15. Last, the CI pipeline runs `python3 scripts/latest_tag.py --push`. The script reads the remote's tags, and points the tag `latest` at the commit of the highest release tag, which is this release's. It force-pushes `latest`, leased on the value it read, so `uv tool install` with `@latest` gets the new release (PRJ-004).

**Variants:**

- **1a.** The maintainer releases by hand, running `pkit release plan`, then `pkit release apply` on a `release/` branch cut from the [default branch](../../../glossary.md#term-default-branch--default-branch)'s [head](../../../glossary.md#term-head--head). At its entry, before it prints its plan, `pkit release apply` checks the repository as step 14 does. The maintainer confirms `Write these versions and consume the changesets?`, then commits the [release step](../../../glossary.md#term-release-step--release-step)'s writes with the line step 5 prints. The maintainer opens their [release pull request](../../../glossary.md#term-release-pull-request--release-pull-request) with that line in its body, and the path goes on at step 7.

> [!WARNING]
> **Not built yet:** `pkit release apply` runs the check only when `--tag --push` asks it to push a tag. Without them, it writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **1b.** On the path of 1a, no pending [changeset](../../../glossary.md#term-changeset--changeset) moves a [version](../../../glossary.md#term-version--version). `pkit release apply` asks nothing, writes no version and no changelog entry, and deletes the pending `none` changesets. The use case ends.
- **1c.** On the path of 1a, the maintainer first passes `--dry-run` to `pkit release apply`, to see each edit it would make. The [system](../../../glossary.md#term-system--system) names each edit, and writes nothing ([REQ-009](../../../requirements/quality/REQ-009-preview-before-change.md)).

> [!WARNING]
> **Not built yet:** `pkit release apply` takes no `--dry-run`, and refuses the flag. [COR-004](../../../../../../.pkit/decisions/core/COR-004-cli-surface.md) decides that it offers one, and #1884 tracks it.

- **2a.** No pending changeset moves a version, as when only `none` changesets wait. `release-pr.yml` ends with `No pending changesets move a version — nothing to release.` The `none` changesets wait for the next [release](../../../glossary.md#term-release--release), and the use case ends.
- **2b.** A changeset names a [component](../../../glossary.md#term-component--component) the tree does not hold. The system refuses the release step, naming the changeset and the components it knows. `release-pr.yml` opens no [pull request](../../../glossary.md#term-pull-request--pull-request), and the use case ends.
- **2c.** A changeset declares a floor or an upper bound the release step cannot write. The system refuses before writing anything, such as with `cannot raise a requires_backbone floor:` and the changeset's problem. The use case ends.
- **2d.** The release step would leave a [capability](../../../glossary.md#term-capability--capability) whose [range](../../../glossary.md#term-range--range) excludes the version of a capability it depends on. The system refuses before writing anything, listing each such range, and the use case ends ([PRJ-002 D4](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d4--the-release-step-writes-every-floor-and-upper-bound-and-a-floor-rises-only-in-a-final-release)).
- **2e.** A [backbone](../../../glossary.md#term-backbone--backbone) [migration](../../../glossary.md#term-migration--migration)'s folder names a version above the current backbone's version, and the release step does not compute that version. The system warns that the folder `does not match the computed backbone release`, and goes on. The release pull request's body shows the warning ([UC-010](UC-010-migrate-backbone-change.md)).
- **2f.** A migration script sits in a folder at or below the version its backbone or component records at the newest final [release tag](../../../glossary.md#term-release-tag--release-tag). The first final release tag recording that version lacks the script, as when a pull request landed after a release its checks did not see. The system refuses before writing anything, naming each such script with a folder above the version the default branch records ([ADR-092 point 8](../../../../../architecture/decisions/ADR-092-final-release-from-head.md#8-a-branchs-scripts-are-its-own-until-it-merges-and-no-release-ships-one-stranded)). The use case ends.
- **2g.** The system cannot read the remote's release tags, or the clone lacks the commit of one, as a shallow clone may. The system refuses before writing anything, since it cannot tell whether 2f holds ([ADR-092 point 8](../../../../../architecture/decisions/ADR-092-final-release-from-head.md#8-a-branchs-scripts-are-its-own-until-it-merges-and-no-release-ships-one-stranded)). The use case ends.
- **3a.** A release pull request is already open, on a `release/` branch. Its body names the default branch's head as the commit the release was planned from. `release-pr.yml` opens no second one, and the use case ends.
- **3b.** A run that failed after its push left the branch `release/v<version>` on the remote, and no release pull request is open from it. The CI pipeline creates the branch `release/v<version>-<run id>` instead, and the path goes on (`scripts/release_pr.py`). Step 9 takes that branch too, as a `release/` branch.
- **3c.** An open release pull request's body names no commit, or an older one, as the one the release was planned from. `release-pr.yml` closes it and deletes its branch, since it can no longer land. The path goes on at step 3, with a release planned from the default branch's head ([ADR-092 point 6](../../../../../architecture/decisions/ADR-092-final-release-from-head.md#6-a-release-pr-lands-only-what-its-release-step-wrote-onto-the-commit-its-plan-read)).
- **6a.** The new changelog entry would take the pull request's body past the 65,536 characters GitHub keeps. The body then holds each move and warning whole, and links `CHANGELOG.md` on the pushed branch instead of the entry (`scripts/release_pr.py`).
- **7a.** The [project](../../../glossary.md#term-project--project) gave `release-pr.yml` no token of its own, so the release pull request starts no checks. The maintainer starts them by hand, and the path goes on at step 7. Where nobody starts them, the release pull request shows no check, and step 10 reads that as green.
- **9a.** The pull request is no release pull request. The system refuses it, saying that `pkit release merge` merges only release pull requests. Where the pull request's head branch is no `release/` branch, the refusal names `pkit pull-request land`, the backbone's own command for landing any other pull request. The use case ends.
- **10a.** The release pull request has a conflict, or a check that is red or still running. The system refuses with the reason, and merges nothing. The path rejoins at step 8.
- **10b.** Where merges into the default branch go through a queue, the system enqueues the release pull request at the head commit whose checks it read. The system then waits for the queue to merge the pull request. Where the wait ends with the release pull request still queued, the system exits 4 and deletes nothing. A later run deletes the head branch once the release pull request merges.
- **10c.** The queue does not squash, or its squash defaults are not the pull request's title and body. The system refuses, enqueues nothing, and the use case ends.
- **10d.** The queue drops the release pull request, or the release pull request's head commit moves after the checks were read. The system exits 3 and deletes nothing, and the path rejoins at step 7.
- **10e.** The default branch moved after the release was planned, or the release's [change](../../../glossary.md#term-change--change) holds more than `pkit release apply` wrote and the [answer files](../../../glossary.md#term-answer-file--answer-file) it adds. The system refuses and merges nothing ([ADR-092 point 6](../../../../../architecture/decisions/ADR-092-final-release-from-head.md#6-a-release-pr-lands-only-what-its-release-step-wrote-onto-the-commit-its-plan-read)). The refusal says to run the release again from the default branch's head, and never to amend the `chore(release):` commit. The use case ends.
- **10f.** The `chore(release):` commit or the pull request's body lacks the line naming the commit the release was planned from, or the two name different commits. The system refuses as in 10e, and the use case ends.
- **10g.** Merges into the default branch go through a queue, and the queue holds another pull request ahead of the release pull request. The system refuses, enqueues nothing, and names the pull requests ahead. The maintainer runs `pkit release merge` again once they have left the queue. Where any of them merged, the release runs again, as in 10e.
- **11a.** The version in `.pkit/VERSION` already has its release tag, as after any push that is no release. `release-tag.yml` cuts no tag and publishes no notes, and the path goes on at step 15.
- **11b.** The run of `release-tag.yml` for the release push fails. The next push to the default branch finds the version untagged, and tags that push's commit instead of the one the release pull request landed.
- **13a.** A release step that moved only components came between this release and the previous one. That step's changelog section is headed by its date, so no GitHub release's notes carry it (`release.py`).
- **13b.** The version's changelog section is longer than the 125,000 characters a GitHub release keeps. The notes then hold the section's heading, a link to the section in `CHANGELOG.md` at the tag, and each component's new version (`release.py`).
- **15a.** `latest` already points at that commit, as after a push that is no release. The script pushes nothing.
- **15b.** Another run moved `latest` after this run read it, and the remote refuses the leased push. The script reads the remote's tags again. Where `latest` points at that commit, the run passes. Otherwise the run fails, `latest` stays where the other run put it, and the next push to the default branch runs step 15 again.
- **15c.** The remote holds a branch named `latest`, which uv can take before the tag. The script refuses, pushes nothing, and the run fails until someone deletes the branch.
- **14a.** The repository is another, and the operator declines. Or nobody can reply, and the maintainer passed no `--allow-foreign-repo`. The system refuses, merges nothing, and the use case ends.

**Postconditions:** The commit that lands the [release](../../../glossary.md#term-release--release)'s [versions](../../../glossary.md#term-version--version) on the [default branch](../../../glossary.md#term-default-branch--default-branch) carries the [release tag](../../../glossary.md#term-release-tag--release-tag) `v<version>`, which adopters <!-- pkit:not-the-term -->install, upgrade to and pin ([PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)). The tag `latest` points at the same commit, so `uv tool install` with `@latest` gets this release. That version's changelog section, and the notes of its GitHub release, say what each [change](../../../glossary.md#term-change--change) the release carries means for adopters.

**Minimal guarantees:**

- A [release step](../../../glossary.md#term-release-step--release-step) the [system](../../../glossary.md#term-system--system) refuses for a [changeset](../../../glossary.md#term-changeset--changeset)'s declaration, or for a [range](../../../glossary.md#term-range--range), writes nothing. Each of those refusals comes before the first write (`release.py` and [PRJ-002 D4](../../../../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md#d4--the-release-step-writes-every-floor-and-upper-bound-and-a-floor-rises-only-in-a-final-release)).
- Just before its request, `pkit release merge` refuses a [release](../../../glossary.md#term-release--release) that would land more than its release step wrote and the [answer files](../../../glossary.md#term-answer-file--answer-file) it adds. It also refuses one that would land onto a commit other than the one the release was planned from (`release.py` and [ADR-092 point 6](../../../../../architecture/decisions/ADR-092-final-release-from-head.md#6-a-release-pr-lands-only-what-its-release-step-wrote-onto-the-commit-its-plan-read)).
- No workflow merges a [release pull request](../../../glossary.md#term-release-pull-request--release-pull-request). A release pull request lands only when someone merges it (`release-pr.yml` and `release-tag.yml`).
- A [version](../../../glossary.md#term-version--version) is tagged once. `release-tag.yml` tags only a version with no tag, locally or on the remote, and `pkit version tag` refuses a tag the clone already holds (`versioning.py`).
- A GitHub release carries notes only, never a file to download ([PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)).
- A run of `release-tag.yml` never moves `latest` back to an older release. Its push is leased on the value it read (`scripts/latest_tag.py`).
- In a repository other than the session's own, `pkit release merge` changes nothing without the operator's yes or `--allow-foreign-repo` ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md) and `session_guard.py`).
