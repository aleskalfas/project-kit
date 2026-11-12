---
id: ADR-092
title: Every final release is the ordinary release PR from the default branch's head
status: proposed
date: 2026-11-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** every final release takes the ordinary path, whatever candidates are out: a release PR from the default branch's head, tagged once it merges. No command asks whether a candidate line runs. A candidate's number counts every candidate the remote holds, so with `2.2.0rc1` out and a breaking change merged, the next cut is `3.0.0rc2`.

## Context

[PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md) decides that a release candidate holds no release back. [ADR-089](ADR-089-release-candidates.md) points 2, 3 and 9 build the opposite. A cut refuses while a line runs at another version, and the final release is cut from the last candidate's source commit and tagged before its pull request. The merge refuses what cannot wait, and every other release PR while a line runs.

None of those points is built ([#2211](https://github.com/aleskalfas/project-kit/issues/2211)). The default branch's ordinary release starts by hand, and a release PR's body past its cap links the changelog section on the release branch.

## Decision

**Every final release is the ordinary release PR from the default branch's head, tagged once it merges, and a candidate's number counts every candidate the remote holds.**

### 1. Every final release is the ordinary release PR

`pkit release plan` and `apply` without `--pre` plan and write a final release from the default branch's head, and the release-tag workflow tags the commit its release PR leaves there (PRJ-002 D3). No cut, plan, write or merge reads whether a line runs.

### 2. A cut's number counts every candidate the remote holds

`N` is one past the highest number any candidate tag on the remote carries, whatever its version, and 1 where there is none. In ADR-089 point 2's refusals that stand, the previous and the last candidate are the highest-numbered at the version the cut previews.

### 3. A run without the input is the ordinary release run

The release workflow, started without its "pre-release" input, opens the ordinary release PR at any time, and a resumed run finishes only a candidate's notes. Past a pull request's cap, the release PR's body links its changelog section on its release branch, since its tag is cut only once it merges.

### What this overturns in ADR-089, and what stands

Overturned:

- the sentences of the Summary and of the Decision's lead on the final release cut from the last candidate's source commit
- in point 1, "from the source point 3 sets"
- in point 2, the counter for each backbone version, and the refusal of a cut while a line runs at another backbone version
- point 3, but for its last two bullets
- in point 9:
  - the bullet "The final release that ends a line", and "A final release that ends no line"
  - the final release's pull request in "Runs kept apart, and resumed" and in "How the next run finds what was left"
  - the release PR's link to its section at the version's tag
- in the Rationale, the reasons for each passage above, including:
  - in point 2, one line at a time, and that leaving a line without its final release is not decided there, which PRJ-016 point 3 decides
  - in point 5, "since the final release ships its last candidate's folders (point 3)"
  - in point 9, the reason no schedule starts the release workflow
- in the alternatives:
  - the rejections of a final release cut from a later commit a person judges safe, of its tag cut on its PR's merge commit, of a release PR built on `main`'s head, and of its PR merged with no check of its head, each of which point 1 takes
  - the cost named for "A 'final' input of its own"
- in the Implications, the release README's docs on a running line, the cut from the source commit, what cannot wait and the merge's check

Standing: the rest of ADR-089, with points 7 and 8 refined (Implications). Among it are the start on request alone, which rests on the maintainer's choice for [#2232](https://github.com/aleskalfas/project-kit/issues/2232), and the default branch holding release versions alone.

## Rationale

**Point 1.** Every part of ADR-089 point 3 existed because the final release shipped an older commit than the head. Those parts are the source commit found from the tags, the tag before the pull request, the squash of the tagged commit into a moved default branch, and the refusals of what cannot wait. Cut from the head, the final release needs none of them.

**Point 2.** A counter for each backbone version kept candidates apart only while one line ran at a time (PRJ-016 point 4). A shared counter keeps them apart however lines overlap, and across a release that left a component unmoved, from the remote's tags alone. Its cost is that a version's first candidate may not be `rc1`.

**Point 3.** Only the run that ended a line pushed a final release's tag before its pull request, so without it a run without the input is the ordinary one. A link at a tag cut later cannot resolve while the PR is reviewed. The branch link stops resolving once the PR merges and its branch is deleted, when the section is at the tag and on the default branch.

**The migration rules stand.** ADR-089 point 5 holds a correction numbered last safe because the final release ships its last candidate's folders. Cut from the head, the final release ships folders that extend each candidate's, since a script a pre-release shipped is never edited, renumbered or removed. So every path runs a folder in the order a candidate shipped it. A folder an overtaken line's candidate shipped keeps its name by the same rule, and the window runs it for every project that starts below it.

**A project on a candidate** moves on through ADR-065 point 9's hand-over to a newer latest release, so an overtaken line needs no code of its own. Under `--pre` the newest release may be another line's candidate, and a tester who follows one line names its candidates with `pkit pin` (ADR-089 point 6).

### Alternatives considered

- **ADR-089 point 3's path for the final release at a candidate's version, beside ordinary releases.** Rejected, as PRJ-016's alternatives reject it.
- **A plan that says whether the head is the last candidate's source commit.** Not taken: the person who starts the run knows, the line could not vouch for what merges before the PR lands, and every plan would read the remote.
- **A counter for each component.** Rejected: ADR-089 point 1 gives a cut one `N`, and the counter would read every candidate's tree.
- **The release PR's section linked at its head commit, which outlives the branch.** Not taken: the body is built before that commit exists.

## Implications

- **ADR-089** gains this line at the top of its body, before its Summary, and its text stays as it is under it but for the two refinements below:

  > **Partially superseded by [ADR-092](ADR-092-final-release-from-head.md).** Every final release, the one at a candidate's version included, is the ordinary release PR from the default branch's head, and no command asks whether a line runs ([PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md)). A cut's number counts every candidate the remote holds. Overturned: the final release cut from the last candidate's source commit (point 3, but its last two bullets), the counter for each version and the refusal of a cut while a line runs at another version (point 2), and the run that ends a line (point 9). ADR-092's "What this overturns in ADR-089, and what stands" lists each passage. The rest of ADR-089 stands.
- **ADR-089 point 7, refined in place:** `pkit unpin`'s message names "`pkit upgrade` once a final release at or above the candidate's version ships (point 8, refinement per ADR-092)", in place of "`pkit upgrade` once the final release ships (point 8)".
- **ADR-089 point 8, refined in place:** a plain `pkit upgrade` keeps a project at its candidate pin "until a final release at or above the candidate's version ships, its line's own or a later one, and then takes it to the latest release (ADR-065 point 9, refinement per ADR-092)", in place of "until the final release ships, and then takes it there (ADR-065 point 9)".
- **ADR-065 needs no edit:** a line runs until a final release at or above its version ships, so its rows on a running line hold as written.
- **#2211's build plan** drops the cut from the source commit, the refusals of what cannot wait, the merge's check and the resumed final release's PR, and counts every candidate tag.
- **The release README, with the build:** the counter, the final release's one path, the release PR's link, and that the migration-dir warning leaves a folder a candidate shipped where it is.
- **No migration:** nothing installed changes shape, and nothing overturned was built.
