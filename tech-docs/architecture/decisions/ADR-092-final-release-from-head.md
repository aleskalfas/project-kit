---
id: ADR-092
title: A candidate is cut from a branch's head, and every final release is the ordinary release PR
status: proposed
date: 2026-11-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** every final release takes the ordinary path, whatever candidates are out: a release PR from the default branch's head, merged only while that head is the commit it was planned from, and tagged once it merges. No command asks whether a line runs. A candidate is cut from the head of the branch the release workflow is started on, once that branch has taken in the default branch's head. A person withdraws a candidate with a tag beside its own, which `pkit upgrade --pre` and later cuts read. A cut's number counts every candidate the remote holds, so with `2.2.0rc1` cut from one branch, the next cut, from a branch with a breaking change, is `3.0.0rc2`. A tester's project moves only to a newer candidate, each move running every folder since the last final release it finished, and it leaves by leaving the testers' branch.

## Context

[PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md) decides that a change that must be tested before it ships is tested on its own branch before it merges, and that every final release is the ordinary release from the default branch's head. [ADR-089](ADR-089-release-candidates.md) points 1, 2, 3 and 9 build the opposite. A candidate is cut from the default branch's head alone, a cut refuses while a line runs at another version, and the final release is cut from the last candidate's source commit and tagged before its pull request. The merge refuses what cannot wait, and every other release PR while a line runs.

ADR-089 points 5 and 8 rest on no other release shipping while a line runs. A move between candidates runs only the folders above the candidate it leaves, and a project at a candidate is handed over to the release that ends its line. Under PRJ-016 the default branch releases while lines are out, and a branch merges once its testing passes, whether or not a release PR is open.

None of those points is built ([#2211](https://github.com/aleskalfas/project-kit/issues/2211)). The default branch's ordinary release starts by hand, and a release PR's body past its cap links the changelog section on the release branch.

## Decision

**Every final release is the ordinary release PR, planned from the default branch's head and merged only while that head stands, a candidate is cut from a branch that has taken in that head, numbered across every candidate and withdrawn by a tag, and a project on a candidate moves only to a newer one, each move running every folder since the last final release it finished.**

### 1. Every final release is the ordinary release PR

`pkit release plan` and `apply` without `--pre` plan and write a final release from the default branch's head, and the release-tag workflow tags the commit its release PR leaves there (PRJ-002 D3). No cut, plan, write or merge reads whether a line runs.

### 2. A candidate is cut from a commit that has the default branch's head in its history

`pkit release plan --pre` and `apply --pre` plan from the commit they run at: the versions it records and the changesets pending in its tree, the default branch's and its own branch's (PRJ-016 point 3). They refuse, before writing anything, where the default branch's head, read from the remote, is not in that commit's history. The release workflow's pre-release run cuts from the head of the branch a person starts it on.

### 3. A cut's number counts every candidate, and a cut is held to the candidates in its history

- **The counter.** `N` is one past the highest number any candidate tag on the remote carries, whatever its version, and 1 where there is none.
- **The candidates a cut is held to** are those not withdrawn whose source commit is in the history of the commit it cuts from. ADR-089 point 2 refuses a cut where a component's version is below its version in any of them, and where the commit is the source commit of one of them.

### 4. A withdrawal is a tag

A person withdraws a candidate by pushing the tag `withdrawn/v<candidate>` on the candidate's commit, and its Release says so. The tag is never moved or deleted, and names no install. A cut reads it (point 3), `pkit upgrade --pre` passes by the candidate it names, and ADR-089 point 5's add-only rule reads it, as that point is refined (Implications).

### 5. A run without the input is the ordinary release run

The release workflow, started without its "pre-release" input, refuses on any branch but the default branch. There it runs ADR-089 point 5's folder test on the head, and then opens the ordinary release PR. It first finishes the notes an earlier run left unpublished, and where that fails it says so and goes on. Past a pull request's cap, the release PR's body links its changelog section on its release branch, since its tag is cut only once it merges.

### 6. A release PR merges only while the default branch's head is the commit its plan read

`pkit release merge` refuses a release PR unless the default branch's head, read from the remote, is the commit the release's plan was computed from. Where the head moved, the release is planned again from the new head, by running the release workflow again.

### 7. A move from a candidate runs every folder since the last final release the project finished

A transition of a tier whose completion the project records at a candidate takes as its lower bound the last release version the project finished for that tier. Where the project finished none, the backbone runs every folder, as where `completed_version` is missing (ADR-065 point 5), and a component runs from the version its manifest records. The project records that version for each tier, and keeps it while the tier moves through candidates; where it is kept, and under what name, are the build's.

### 8. A project leaves a candidate by leaving the testers' branch

A plain `pkit upgrade`, with routing not bypassed, never moves a project whose manifest records a candidate onto a final release, and `pkit upgrade --pre` moves it only to a candidate, as `pkit pin` naming one does. A project leaves its candidates by leaving the testers' branch, and once the candidate's branch has shipped, it upgrades to the final release as any project does.

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
- in point 8:
  - the bullet "A withdrawn candidate is still found", which point 4 overturns
  - in the bullet "A plain `pkit upgrade`", its second sentence, which hands a project at a candidate over once the final release ships, and which point 8 overturns
- in point 9:
  - "on the default branch's head, the source commit" in "The pre-release run", which point 2 takes
  - "and for a final release its pull request" in "Runs kept apart, and resumed", and all but the first sentence of "How the next run finds what was left"
  - the release PR's link to its section at the version's tag
  - the bullets "The final release that ends a line" and "A final release that ends no line", which point 1 takes
- in the Rationale:
  - for point 2, "and a test of the line read from it could miss the line, and cut from `main`'s head a final release no candidate tested", and its last two sentences, on one line at a time and a line left without its final release, which PRJ-016 point 4 decides
  - for point 3, its first three paragraphs, and in its fourth "and an adopter whose own tags include one such as `v1.0.0rc1` would seem to run a line"
  - for point 5, "since the final release ships its last candidate's folders (point 3)", and the sentence that each move through candidates reaches the state the later folder reaches alone, and the final release's folder the state of the path without candidates, which points 7 and 8 overturn
  - for point 8, its last sentence, on a withdrawn candidate staying the newest
  - for point 9, the reason its first sentence gives, and the sentence on a release tag above the version the default branch records
- in the alternatives:
  - the rejections of a final release cut from a later commit a person judges safe, of its tag cut on its PR's merge commit, of a release PR built on `main`'s head, and of a change that cannot wait mended after its PR merges
  - the cost named for "A 'final' input of its own"
- in the Implications, the release README's docs on a running line, the cut from the source commit, what cannot wait and the merge's check

Standing: the rest of ADR-089, with points 5 and 7 refined (Implications). Among it are the start on request alone, which rests on the maintainer's choice for [#2232](https://github.com/aleskalfas/project-kit/issues/2232), the default branch holding release versions alone, and the path without candidates, on which each script runs once (point 5).

## Rationale

**Point 1.** Every part of ADR-089 point 3 existed because the final release shipped an older commit than the head. Those parts are the source commit found from the tags, the tag before the pull request, the squash of the tagged commit into a moved default branch, and the refusals of what cannot wait. Cut from the head, the final release needs none of them.

**Point 2.** A commit with the default branch's head in its history holds the versions that branch records and every changeset pending there, beside its own branch's. So its plan is the one the default branch's release would compute once the branch merges. The remote is read since a clone's copy of the default branch may lag behind it.

**Point 3.** A counter for each backbone version kept candidates apart only while one line ran at a time (PRJ-016 point 6). A shared counter keeps them apart however lines overlap, from the remote's tags alone. Its cost is that a version's first candidate may not be `rc1`. A commit's history holds its branch's earlier candidates and those of the default branch it took in, and none of a branch dropped apart from it. So a cut is held to the candidates a tester of its line may come from, and to no other branch's.

**Point 4.** `pkit upgrade --pre` reads the remote's tags alone, as ADR-063 point 1's lookup does, and needs nothing of the host's own interface. A tag on the candidate's commit puts the withdrawal where that lookup reads, and a tag that is never moved keeps it. A reader of `v`-prefixed tags passes a tag under `withdrawn/` by.

**Point 5.** Only the run that ended a line pushed a final release's tag before its pull request, so without it a run without the input is the ordinary one. On another branch it would release what has not merged. A pull request's folder test reads the default branch as it was when that request ran (ADR-089, Rationale for point 5), so the run tests the tree the release ships, which point 6 keeps until the merge. A candidate's tag is fixed, so notes that cannot publish would otherwise stop every later run. A link at a tag cut later cannot resolve while the PR is reviewed. The branch link stops resolving once the PR merges and its branch is deleted, when the section is at the tag and on the default branch.

**Point 6.** A release PR consumes the changesets pending at the commit its plan read, and its tag takes the commit its merge leaves (point 1). A change merged after that commit would ship in the tag with its changesets pending and its migrations unrun, so the tag would not be the coherent state PRJ-002 D3 makes it. PRJ-016 makes such a merge routine, since a branch merges once its testing passes. The cost is that a merge into the default branch while a release PR is open means the release is cut again.

**Point 7.** A branch that takes in a release brings that release's folders, which sit below its candidates' version, so a window from the candidate would skip them, and its testers would run the release's code without its migrations. From the last release the project finished, each move runs every folder the path without candidates runs up to the candidate's version. Each move runs those folders again, and on the first move after the branch took in a release, that release's folder runs after the candidate's folder had run, the reverse of that path. A backbone script, safe over any state (COR-010), holds both. A component's script is held to its own idempotence alone, which ADR-089's Rationale for point 5 finds not enough where an earlier script runs over a later one's output, so a tester who needs the exact state enters the line again from the latest release.

**Point 8.** A final release at or above a candidate's version may ship without the candidate's branch (PRJ-016 point 4), and its version alone cannot tell it from the release that ships the branch. Leaving the testers' branch takes a project back to where it stood before its first candidate, whichever release ends the line. So every project reaches a final release on the path without candidates, where each script runs once (ADR-089 point 5), and no path through candidates need reach a final release's state. A run with routing bypassed, such as a raise by `pkit pin`, is a person's own choice, as ADR-089 point 7's guard takes it. The cost is that a project left on a candidate stays there until a person moves it. While several lines are out, `pkit upgrade --pre` takes the newest candidate of any of them, so a tester who follows another names its next candidate with `pkit pin` (ADR-089 point 6).

**The migration rules.** A branch and the default branch may add scripts to one folder while a candidate of the branch is out. Numbered after every script a candidate not withdrawn shipped there, on any branch, each addition reaches a later candidate of that line after what the earlier ones shipped. A script such a candidate shipped is never edited, renumbered or removed, and a candidate a release overtakes without its branch is withdrawn (PRJ-016 point 4). So a later candidate of a line extends each folder an earlier one shipped, and a move along the line runs it in the order a candidate shipped it. A dropped branch's scripts reach no folder of the default branch.

### Alternatives considered

- **ADR-089 point 3's path for the final release at a candidate's version, beside ordinary releases.** Rejected: PRJ-016 tests a change before it merges, so no release needs it.
- **A candidate cut from a commit without the default branch's head in its history.** Rejected: it would preview a release the default branch cannot make.
- **A cut held to the highest-numbered candidate at its version.** Rejected: candidates of two branches at one version would hold each other, and a dropped branch's would hold every later cut at its version.
- **The withdrawal read from the candidate's Release.** Not taken: `--pre` would read the host's interface beside the remote's tags.
- **A counter for each component.** Rejected: ADR-089 point 1 gives a cut one `N`, and the counter would read every candidate's tree.
- **The release PR's section linked at its head commit, which outlives the branch.** Not taken: the body is built before that commit exists.
- **A release PR brought level with the default branch by merging it in.** Rejected: it would bring in changesets its plan did not consume.
- **The lower bound recorded in the candidate's tree, as the last release its branch took in.** Rejected: a tester who entered the line from an older release would skip the folders between the two.
- **A cut's notes telling testers to enter the line again whenever its branch takes in a release.** Not taken: a tester who misses the notes runs that release's code without its migrations.
- **A hand-over from a candidate to the latest release once a final release at or above its version ships.** Rejected: where that release overtakes the candidate, it hands testers to a release without their branch.

## Implications

- **ADR-089** gains this line at the top of its body, before its Summary, and its text stays as it is under it but for the refinements below:

  > **Partially superseded by [ADR-092](ADR-092-final-release-from-head.md).** Every final release, the one at a candidate's version included, is the ordinary release PR from the default branch's head, and no command asks whether a line runs ([PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md)). A candidate is cut from the head of a branch that has taken in the default branch's head, a withdrawal is a tag, a cut's number counts every candidate the remote holds, and a project leaves a candidate by leaving the testers' branch. Overturned: the cut from the default branch's head alone (points 1 and 2), the counter for each version and the refusal of a cut while a line runs at another version (point 2), the final release cut from the last candidate's source commit (point 3, but its last two bullets), a withdrawn candidate found by `--pre` and the hand-over from a candidate once the final release ships (point 8), and the run that ends a line (point 9). ADR-092's "What this overturns in ADR-089, and what stands" lists each passage. The rest of ADR-089 stands.
- **ADR-089 point 5, refined in place,** each bullet with the pointer `(refinement per ADR-092)`:
  - its window bullet takes, from a completion at a candidate, the lower bound ADR-092 point 7 sets
  - its add-only bullet keeps a script a candidate not withdrawn shipped, and numbers every script added to its folder on any branch, not only a correction, after every script such a candidate shipped there
  - its bullet on the order of scopes says the same of any manifest-schema script added there
- **ADR-089 point 7, refined in place:** `pkit unpin`'s message names "leaving the testers' branch, or `pkit upgrade --pre` to a newer candidate (point 8, refinement per ADR-092)", in place of "leaving the testers' branch, or `pkit upgrade` once the final release ships (point 8)".
- **ADR-065, refined in place,** each with the pointer `(refinement per ADR-092)`:
  - point 3's bullet on the backbone's window, and point 4's steps 4 to 6: from a completion at a candidate, the lower bound ADR-092 point 7 sets
  - point 4's "any other upgrade": beside the refusal of a candidate nobody asked for, the refusal of a move from a project whose manifest records a candidate onto a final release, unless routing is bypassed
  - point 8's candidate row: its state is a recorded target at a candidate, above the running pkit or not, its message names leaving the testers' branch beside `pkit upgrade --pre`, and "No final release finishes it" stands in place of "No latest release finishes it while its line runs"
  - point 9's first case: a project whose manifest records a candidate makes no hand-over to a final release, and under `--pre` hands over only where the newest release is a candidate
  - point 9's second case: its message names leaving the testers' branch beside `pkit upgrade --pre`, "since no final release finishes that move" in place of "since no latest release finishes that move while its line runs"
- **PRJ-004 needs no edit:** the withdrawal's tag names no install, and no reader of release or candidate tags meets it.
- **#2211's build plan** drops the cut from the source commit, the refusals of what cannot wait, the merge's check of a running line, the resumed final release's PR and the hand-over from a candidate to the final release. It adds the cut from a branch's head, the counter across every candidate tag, the withdrawal's tag and its readers, the ordinary run's folder test, point 6's refusal at the merge, point 7's recorded version and window, and point 8's upgrade from a candidate.
- **The release README, with the build:** the counter, the cut from a branch, the withdrawal, the final release's one path, the release PR's link, and that the migration-dir warning leaves a folder a candidate shipped where it is.
- **The release README's section on merging the release PR, with the build:** its preconditions gain point 6's refusal, and its way on, the release workflow run again.
- **The lifecycle reference and the migration-authoring skill, with the build:** the add-only rule and the order of an added script, as ADR-089 point 5 is refined, and in the lifecycle reference the window's lower bound from a candidate.
- **The CLI reference, with the build:** `pkit unpin`'s message, and a plain upgrade from a candidate.
- **No migration:** nothing installed changes shape, nothing overturned was built, and no project is at a candidate before the build.
