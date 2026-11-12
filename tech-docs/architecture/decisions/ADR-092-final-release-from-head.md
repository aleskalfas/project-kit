---
id: ADR-092
title: A candidate is cut from a branch's head, and every final release is the ordinary release PR
status: proposed
date: 2026-11-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** every final release takes the ordinary path, whatever candidates are out: a release PR from the default branch's head, tagged once it merges, and no command asks whether a line runs. A candidate is cut from the head of the branch the release workflow is started on, once that branch has taken in the default branch's head. A person withdraws a candidate with a tag beside its own, which `pkit upgrade --pre` and later cuts read. A cut's number counts every candidate the remote holds, so with `2.2.0rc1` cut from one branch, the next cut, from a branch with a breaking change, is `3.0.0rc2`.

## Context

[PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md) decides that a change that must be tested before it ships is tested on its own branch before it merges, and that every final release is the ordinary release from the default branch's head. [ADR-089](ADR-089-release-candidates.md) points 1, 2, 3 and 9 build the opposite. A candidate is cut from the default branch's head alone, a cut refuses while a line runs at another version, and the final release is cut from the last candidate's source commit and tagged before its pull request. The merge refuses what cannot wait, and every other release PR while a line runs.

None of those points is built ([#2211](https://github.com/aleskalfas/project-kit/issues/2211)). The default branch's ordinary release starts by hand, and a release PR's body past its cap links the changelog section on the release branch.

## Decision

**Every final release is the ordinary release PR from the default branch's head, a candidate is cut from the head of a branch that has taken in the default branch's head, a withdrawal is a tag, and a cut's number counts every candidate the remote holds.**

### 1. Every final release is the ordinary release PR

`pkit release plan` and `apply` without `--pre` plan and write a final release from the default branch's head, and the release-tag workflow tags the commit its release PR leaves there (PRJ-002 D3). No cut, plan, write or merge reads whether a line runs.

### 2. A candidate is cut from a commit that has the default branch's head in its history

`pkit release plan --pre` and `apply --pre` plan from the commit they run at: the versions it records and the changesets pending in its tree, the default branch's and its own branch's (PRJ-016 point 3). They refuse, before writing anything, where the default branch's head, read from the remote, is not in that commit's history. The release workflow's pre-release run cuts from the head of the branch a person starts it on.

### 3. A cut's number counts every candidate, and a cut is held to the candidates in its history

- **The counter.** `N` is one past the highest number any candidate tag on the remote carries, whatever its version, and 1 where there is none.
- **The candidates a cut is held to** are those not withdrawn whose source commit is in the history of the commit it cuts from. ADR-089 point 2 refuses a cut where a component's version is below its version in any of them, and where the commit is the source commit of one of them.

### 4. A withdrawal is a tag

A person withdraws a candidate by pushing the tag `withdrawn/v<candidate>` on the candidate's commit, and its Release says so. The tag is never moved or deleted, and names no install. A cut reads it (point 3), and so do `pkit upgrade --pre` and the add-only rule, as ADR-089 points 8 and 5 are refined (Implications).

### 5. A run without the input is the ordinary release run

The release workflow, started without its "pre-release" input, refuses on any branch but the default branch. There it runs ADR-089 point 5's folder test on the head, and then opens the ordinary release PR. It first finishes the notes an earlier run left unpublished, and where that fails it says so and goes on. Past a pull request's cap, the release PR's body links its changelog section on its release branch, since its tag is cut only once it merges.

### What this overturns in ADR-089, and what stands

Overturned:

- in the Summary and the Decision's lead, a candidate as the preview of the next final release, and that release cut from the commit the last candidate came from
- in the Context, the maintainer's choice 7, which his choices of 12 November 2026 replace (PRJ-016)
- in point 1, "from the source point 3 sets", the plan from the default branch's head in "One plan", and the commit made on top of the default branch's head in "Where it writes", which point 2 takes
- in point 2:
  - the counter for each backbone version
  - the refusals of a cut while a line runs at another backbone version, and anywhere but the default branch's head
  - "the line's previous candidate" and "the default branch's head is the last candidate's source commit" in two refusals, which point 3 restates
- point 3, but for its last two bullets
- in point 8, the bullet "A withdrawn candidate is still found", which point 4 overturns
- in point 9:
  - "on the default branch's head, the source commit" in "The pre-release run", which point 2 takes
  - "and for a final release its pull request" in "Runs kept apart, and resumed", and all but the first sentence of "How the next run finds what was left"
  - the release PR's link to its section at the version's tag
  - the bullets "The final release that ends a line" and "A final release that ends no line", which point 1 takes
- in the Rationale:
  - for point 2, "and a test of the line read from it could miss the line, and cut from `main`'s head a final release no candidate tested", and its last two sentences, on one line at a time and a line left without its final release, which PRJ-016 point 4 decides
  - for point 3, its first three paragraphs, and in its fourth "and an adopter whose own tags include one such as `v1.0.0rc1` would seem to run a line"
  - for point 5, "since the final release ships its last candidate's folders (point 3)"
  - for point 8, its last sentence, on a withdrawn candidate staying the newest
  - for point 9, the reason its first sentence gives, and the sentence on a release tag above the version the default branch records
- in the alternatives:
  - the rejections of a final release cut from a later commit a person judges safe, of its tag cut on its PR's merge commit, of a release PR built on `main`'s head, of its PR merged with no check of its head, and of a change that cannot wait mended after its PR merges
  - the cost named for "A 'final' input of its own"
- in the Implications, the release README's docs on a running line, the cut from the source commit, what cannot wait and the merge's check

Standing: the rest of ADR-089, with points 5, 7 and 8 refined (Implications). Among it are the start on request alone, which rests on the maintainer's choice for [#2232](https://github.com/aleskalfas/project-kit/issues/2232), and the default branch holding release versions alone.

## Rationale

**Point 1.** Every part of ADR-089 point 3 existed because the final release shipped an older commit than the head. Those parts are the source commit found from the tags, the tag before the pull request, the squash of the tagged commit into a moved default branch, and the refusals of what cannot wait. Cut from the head, the final release needs none of them.

**Point 2.** A commit with the default branch's head in its history holds the versions that branch records and every changeset pending there, beside its own branch's. So its plan is the one the default branch's release would compute once the branch merges. The remote is read since a clone's copy of the default branch may lag behind it.

**Point 3.** A counter for each backbone version kept candidates apart only while one line ran at a time (PRJ-016 point 6). A shared counter keeps them apart however lines overlap, from the remote's tags alone. Its cost is that a version's first candidate may not be `rc1`. A commit's history holds its branch's earlier candidates and those of the default branch it took in, and none of a branch dropped apart from it. So a cut is held to the candidates a tester of its line may come from, and to no other branch's.

**Point 4.** `pkit upgrade --pre` reads the remote's tags alone, as ADR-063 point 1's lookup does, and needs nothing of the host's own interface. A tag on the candidate's commit puts the withdrawal where that lookup reads, and a tag that is never moved keeps it. A reader of `v`-prefixed tags passes a tag under `withdrawn/` by.

**Point 5.** Only the run that ended a line pushed a final release's tag before its pull request, so without it a run without the input is the ordinary one. On another branch it would release what has not merged. A pull request's folder test reads the default branch as it was when that request ran (ADR-089, Rationale for point 5), so the run tests the tree the release ships. A candidate's tag is fixed, so notes that cannot publish would otherwise stop every later run. A link at a tag cut later cannot resolve while the PR is reviewed. The branch link stops resolving once the PR merges and its branch is deleted, when the section is at the tag and on the default branch.

**The migration rules.** A branch and the default branch may add scripts to one folder while a candidate of the branch is out. Numbered after every script a candidate not withdrawn shipped there, on any branch, each addition extends that candidate's folder. A script such a candidate shipped is never edited, renumbered or removed, and a candidate a release overtakes without its branch is withdrawn (PRJ-016 point 4). So each folder a final release ships extends the folder of each candidate not withdrawn that shipped it, and every path through candidates runs it in the order a candidate shipped it. A dropped branch's scripts reach no folder of the default branch.

**A project on a candidate** moves on through ADR-065 point 9's hand-over to a newer latest release, so a line needs no code of its own to end. While several lines are out, `pkit upgrade --pre` takes the newest candidate of any of them, so a tester who follows another names its next candidate with `pkit pin` (ADR-089 point 6).

### Alternatives considered

- **ADR-089 point 3's path for the final release at a candidate's version, beside ordinary releases.** Rejected: PRJ-016 tests a change before it merges, so no release needs it.
- **A candidate cut from a commit without the default branch's head in its history.** Rejected: it would preview a release the default branch cannot make.
- **A cut held to the highest-numbered candidate at its version.** Rejected: candidates of two branches at one version would hold each other, and a dropped branch's would hold every later cut at its version.
- **The withdrawal read from the candidate's Release.** Not taken: `--pre` would read the host's interface beside the remote's tags.
- **A counter for each component.** Rejected: ADR-089 point 1 gives a cut one `N`, and the counter would read every candidate's tree.
- **The release PR's section linked at its head commit, which outlives the branch.** Not taken: the body is built before that commit exists.

## Implications

- **ADR-089** gains this line at the top of its body, before its Summary, and its text stays as it is under it but for the three refinements below:

  > **Partially superseded by [ADR-092](ADR-092-final-release-from-head.md).** Every final release, the one at a candidate's version included, is the ordinary release PR from the default branch's head, and no command asks whether a line runs ([PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md)). A candidate is cut from the head of a branch that has taken in the default branch's head, a withdrawal is a tag, and a cut's number counts every candidate the remote holds. Overturned: the cut from the default branch's head alone (points 1 and 2), the counter for each version and the refusal of a cut while a line runs at another version (point 2), the final release cut from the last candidate's source commit (point 3, but its last two bullets), a withdrawn candidate found by `--pre` (point 8), and the run that ends a line (point 9). ADR-092's "What this overturns in ADR-089, and what stands" lists each passage. The rest of ADR-089 stands.
- **ADR-089 point 5, refined in place:** its add-only bullet keeps a script a candidate not withdrawn shipped, and numbers every script added to its folder on any branch, not only a correction, after every script such a candidate shipped there. Its bullet on the order of scopes says the same of any manifest-schema script added there. Both take the pointer `(refinement per ADR-092)`.
- **ADR-089 point 7, refined in place:** `pkit unpin`'s message names "`pkit upgrade` once a final release at or above the candidate's version ships (point 8, refinement per ADR-092)", in place of "`pkit upgrade` once the final release ships (point 8)".
- **ADR-089 point 8, refined in place:**
  - `pkit upgrade --pre` moves a project to "the newest release, candidates included and withdrawn ones passed by (refinement per ADR-092)".
  - A plain `pkit upgrade` keeps a project at its candidate pin "until a final release at or above the candidate's version ships, and then hands it over to the latest release (ADR-065 point 9, refinement per ADR-092)", in place of "until the final release ships, and then takes it there (ADR-065 point 9)".
- **ADR-065 needs no edit:** no latest release finishes a move to a candidate before a final release at or above its version ships, so its rows on a running line hold as written.
- **PRJ-004 needs no edit:** the withdrawal's tag names no install, and no reader of release or candidate tags meets it.
- **#2211's build plan** drops the cut from the source commit, the refusals of what cannot wait, the merge's check and the resumed final release's PR. It adds the cut from a branch's head, the counter across every candidate tag, the withdrawal's tag and its readers, and the ordinary run's folder test.
- **The release README, with the build:** the counter, the cut from a branch, the withdrawal, the final release's one path, the release PR's link, and that the migration-dir warning leaves a folder a candidate shipped where it is.
- **The lifecycle reference and the migration-authoring skill, with the build:** the add-only rule and the order of an added script, as ADR-089 point 5 is refined.
- **No migration:** nothing installed changes shape, and nothing overturned was built.
