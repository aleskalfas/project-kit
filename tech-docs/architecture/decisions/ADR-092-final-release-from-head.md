---
id: ADR-092
title: A candidate is cut from a branch's head, and every final release is the ordinary release PR
status: proposed
date: 2026-11-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** every final release takes the ordinary path, whatever candidates are out: a release PR from the default branch's head, merged only onto the commit it was planned from, and tagged once it merges. No command asks whether a line runs. A candidate is cut from the head of the branch the release workflow is started on, once that branch has taken in the default branch's head. A cut's number counts every candidate the remote holds, so with `2.2.0rc1` cut from one branch, the next cut, from a branch with a breaking change, is `3.0.0rc2`. A tester enters a candidate from a final release and leaves it only by leaving the testers' branch, so a branch may change its migration scripts until it merges.

## Context

[PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md) decides that a change that must be tested before it ships is tested on its own branch before it merges, that every final release is the ordinary release from the default branch's head, and that a project tries each candidate fresh, from a final release. [ADR-089](ADR-089-release-candidates.md) points 1, 2, 3 and 9 build the opposite. A candidate is cut from the default branch's head alone, a cut refuses while a line runs at another version, and the final release is cut from the last candidate's source commit and tagged before its pull request. The merge refuses what cannot wait, and every other release PR while a line runs.

ADR-089 points 5 and 8 move a project from each candidate to the next and on to the final release, each move running the final release's folder again. Scripts a candidate shipped kept add-only, and folders idempotent as a whole, keep those moves safe while no other release ships. Under PRJ-016 the default branch releases while candidates are out, and a branch merges once its testing passes, whether or not a release PR is open.

None of those points is built ([#2211](https://github.com/aleskalfas/project-kit/issues/2211)). The default branch's ordinary release starts by hand. `pkit release merge` lands a release PR through the merge queue where the base has one, the release-tag workflow tags the head of the push that brings a new `.pkit/VERSION`, and a release PR's body past its cap links the changelog section on the release branch.

## Decision

**Every final release is the ordinary release PR, merged only onto the commit its plan read, a candidate is cut from a branch that has taken in the default branch's head and numbered across every candidate, and a project on a candidate moves to no other release, so a branch's scripts are its own until it merges.**

### 1. Every final release is the ordinary release PR

`pkit release plan` and `apply` without `--pre` plan and write a final release from the default branch's head, and its release PR is tagged once it merges (PRJ-002 D3; point 6). No cut, plan, write or merge reads whether a line runs.

### 2. A candidate is cut from a commit that has the default branch's head in its history

`pkit release plan --pre` and `apply --pre` plan from the commit they run at: the versions it records and the changesets pending in its tree, the default branch's and its own branch's (PRJ-016 point 3). They refuse, before writing anything, where the default branch's head, read from the remote, is not in that commit's history. The release workflow's pre-release run cuts from the head of the branch a person starts it on.

### 3. A cut's number counts every candidate

`N` is one past the highest number any candidate tag on the remote carries, whatever its version, and 1 where there is none.

### 4. A withdrawal is a tag, and `pkit upgrade --pre` passes the candidate it names by

`pkit upgrade --pre` takes the newest release as ADR-089 point 8 sets, whatever branch a candidate was cut from, and passes by a withdrawn candidate. A person withdraws a candidate by pushing the tag `withdrawn/v<candidate>` on the candidate's commit, and its Release says so. The tag is never moved or deleted, and names no install: every reader of release and candidate tags matches the full reference, `refs/tags/v…`.

### 5. A run without the input is the ordinary release run

The release workflow, started without its "pre-release" input, refuses on any branch but the default branch, and there opens the ordinary release PR. It first finishes the notes an earlier run left unpublished, and where that fails it says so and goes on. Past a pull request's cap, the release PR's body links its changelog section on its release branch, since its tag is cut only once it merges.

### 6. A release PR merges only onto the commit its plan read

- **The refusal at the merge.** The check the default branch requires fails a release PR in the merge queue's run where the queue's base, `merge_group.base_sha`, is not the commit its plan read. On a base with no queue, `pkit release merge` refuses unless the default branch's head, read from the remote, is that commit.
- **The tag.** The release-tag workflow tags the commit that changed `.pkit/VERSION`, never the head of the push that brought it.
- **The way on.** The release workflow, run while a release PR whose plan read an older head of the default branch is open, replaces that PR with one planned from the new head.

### 7. A project on a candidate moves to no other release

Every `pkit upgrade`, with or without `--pre`, and every raise by `pkit pin` refuses, before it writes anything, to move a project whose manifest records a candidate to any release but that candidate (PRJ-016 point 4). `pkit upgrade --pre` there targets that candidate, so it only finishes a move to it cut short. The message names the one way off: leave the testers' branch, and from the project's last final release enter a later candidate, or upgrade.

### 8. A branch's scripts are its own until it merges

A script a candidate shipped may be edited, renumbered, moved or removed until its branch merges, as any script on a branch. When the branch takes in the default branch, it moves each of its scripts out of a folder the default branch has since released, as `pkit migrations check-diff` requires of a script a change adds. A cut refuses, before writing anything, where `check-diff` against the default branch's head fails.

### What this overturns in ADR-089, and what stands

Overturned:

- in the Summary and the Decision's lead, a candidate as the preview of the next final release, that release cut from the commit the last candidate came from, and the example of a tester moving from `3.0.0rc1` to `3.0.0rc2` and on to `3.0.0`
- in the Context, the maintainer's choices 4 and 7, and "and on" in choice 5, which his choices of 12 November 2026 replace (PRJ-016)
- in point 1, "from the source point 3 sets", the plan from the default branch's head in "One plan", and the commit made on top of the default branch's head in "Where it writes", which point 2 takes
- in point 2, the counter for each backbone version, which point 3 takes, and the refusals of a cut while a line runs at another backbone version, anywhere but the default branch's head, with a component below its version in the line's previous candidate, and from the last candidate's source commit
- point 3, but for its last two bullets
- in point 5:
  - "and the next move runs that folder again, whole" in "The window"
  - the bullets "A migration a pre-release shipped is add-only", "The scope order yields to it", "A folder a pre-release ships is idempotent as a whole", "A test holds the folder rule" and "Where the two rules bind", which points 7 and 8 overturn
  - the last sentence of "Each script runs once on the path without candidates", on a tester who follows every candidate
- in point 8:
  - the bullet "A withdrawn candidate is still found", which point 4 overturns
  - the second sentence of "A plain `pkit upgrade`", which hands a project at a candidate over once the final release ships, and "or a newer one" in "A move onto a candidate cut short", which point 7 overturns
- in point 9:
  - in "The pre-release run", its first run of point 5's folder test, and "on the default branch's head, the source commit", which point 2 takes
  - "and for a final release its pull request" in "Runs kept apart, and resumed", and all but the first sentence of "How the next run finds what was left"
  - the release PR's link to its section at the version's tag
  - the bullets "The final release that ends a line" and "A final release that ends no line", which point 1 takes
- in the Rationale:
  - for point 1, its last sentence, on each move between candidates
  - for point 2, "and a test of the line read from it could miss the line, and cut from `main`'s head a final release no candidate tested", and its last four sentences, on a component older in the next candidate, a cut from the last candidate's source commit, one line at a time and a line left without its final release
  - for point 3, its first three paragraphs, and in its fourth "and an adopter whose own tags include one such as `v1.0.0rc1` would seem to run a line"
  - for point 5, "The lower bound in PEP 440 order makes the next move run that folder again, whole, with every script added since", its second and third paragraphs, and in its fourth the sentence on the folder rule asking more than COR-010
  - for point 8, its sentence on a tester asking with `--pre` on each move, and its last sentence, on a withdrawn candidate staying the newest
  - for point 9, the reason its first sentence gives, the sentence on the folder test reading the plan, and the sentence on a release tag above the version the default branch records
- in the alternatives:
  - the rejections of edits kept open for scripts a candidate shipped, of the add-only rule alone, of a final release cut from a later commit a person judges safe, of its tag cut on its PR's merge commit, of a release PR built on `main`'s head, and of a change that cannot wait mended after its PR merges
  - `pkit pin <later candidate>` as the way within a line
  - the cost named for "A 'final' input of its own"
- in the Implications, the release README's docs on a running line, the cut from the source commit, what cannot wait and the merge's check, the add-only rule, the folder rule and the order a correction takes in the lifecycle reference and the migration-authoring skill, and in each candidate's notes, that a rerun may restore a removed default

Standing: the rest of ADR-089, with point 7 refined (Implications). Among it are the start on request alone, which rests on the maintainer's choice for [#2232](https://github.com/aleskalfas/project-kit/issues/2232), the default branch holding release versions alone, `pkit upgrade --pre` and the first hop as the way into a candidate, and the path without candidates, on which each script runs once (point 5).

## Rationale

**Point 1.** Every part of ADR-089 point 3 existed because the final release shipped an older commit than the head. Those parts are the source commit found from the tags, the tag before the pull request, the squash of the tagged commit into a moved default branch, and the refusals of what cannot wait. Cut from the head, the final release needs none of them.

**Point 2.** A commit with the default branch's head in its history holds the versions that branch records and every changeset pending there, beside its own branch's. So its plan is the one the default branch's release would compute once the branch merges. The remote is read since a clone's copy of the default branch may lag behind it. The cost is a cut refused when a merge lands before it, run again once the branch takes in the new head.

**Point 3.** A counter for each backbone version kept candidates apart only while one line ran at a time (PRJ-016 point 5). A shared counter keeps them apart however branches' candidates overlap, from the remote's tags alone. Its cost is that a version's first candidate may not be `rc1`. No project moves from one candidate to another (point 7), so a cut answers to no earlier candidate: a component lower than in an earlier one, or a second cut of one commit, breaks no move.

**Point 4.** `pkit upgrade --pre` reads the remote's tags alone, as ADR-063 point 1's lookup does, and needs nothing of the host's own interface. A dropped branch's candidate may stay the newest for good, so a withdrawal must reach that lookup, and a tag on the candidate's commit puts it there, where a tag never moved keeps it. A git pattern such as `v*` also matches the tail of `withdrawn/v…`, which only a full reference keeps out. `--pre` picks a way in, and a tester of another branch's candidate names it with `pkit pin` (ADR-089 point 6).

**Point 5.** Only the run that ended a line pushed a final release's tag before its pull request, so without it a run without the input is the ordinary one. On another branch it would release what has not merged. A candidate's tag is fixed, so notes that cannot publish would otherwise stop every later run. A link at a tag cut later cannot resolve while the PR is reviewed. The branch link stops resolving once the PR merges and its branch is deleted, when the section is at the tag and on the default branch.

**Point 6.** A release PR consumes the changesets pending at the commit its plan read, and its tag takes the commit its merge leaves. A change merged after that commit would ship in the tag with its changesets pending and its migrations unrun, so the tag would not be the coherent state PRJ-002 D3 makes it. PRJ-016 makes such a merge routine, since a branch merges once its testing passes. The queue builds the merge it tests on its own base, which `pkit release merge` never reads, so the refusal sits in the queue's run. On a base with no queue, a merge that lands in the seconds between the command's check and its squash is a cost accepted. A push may carry more than one merge, and the commit that changed `.pkit/VERSION` holds the release and nothing merged after it. The release workflow skips while a release PR is open, so a stale PR left open would hold every release. The costs: a merge that lands first means the release is planned, reviewed and run through CI again, about half an hour (ADR-078), and answers written on the replaced release branch are written again.

**Point 7.** A raise runs its target's upgrade through the bypass (ADR-049 point 5), so the refusal sits in every upgrade from the first candidate on, the candidate's own and each later release's, and in the pin's raise. A move cut short goes on with the command that started it (ADR-089 point 8), so `--pre` finishes the move to the recorded candidate and takes no newer one. The message names the one way off, so a tester who takes a later release to carry their branch learns that none does.

**Point 8.** A script in a folder the default branch has released runs for no project that upgrades past that release, since the window runs only folders above the version a project records (the lifecycle reference, "Which version a migration targets"). No project moves on from a candidate (point 7), so each move that runs a branch's script starts from a final release, wherever the branch has since put the script. The default branch then numbers its scripts as it always has. A cut with a script left in such a folder would preview a release its branch cannot make as it stands, as a cut without the default branch's head would (point 2).

### Alternatives considered

- **ADR-089 point 3's path for the final release at a candidate's version, beside ordinary releases.** Rejected: PRJ-016 tests a change before it merges, so no release needs it.
- **A candidate cut from a commit without the default branch's head in its history.** Rejected: it would preview a release the default branch cannot make.
- **The withdrawal read from the candidate's Release.** Not taken: `--pre` would read the host's interface beside the remote's tags.
- **`--pre` following the project's own branch, read from a tag beside each candidate's.** Not taken: a project on a candidate moves nowhere (point 7), so `--pre` only picks a way in, which `pkit pin` names exactly.
- **A candidate named to `pkit upgrade --pre`.** Not taken: `pkit pin` names one already (ADR-089 point 6).
- **A counter for each component.** Rejected: ADR-089 point 1 gives a cut one `N`, and the counter would read every candidate's tree.
- **The release PR's section linked at its head commit, which outlives the branch.** Not taken: the body is built before that commit exists.
- **A release PR brought level with the default branch by merging it in.** Rejected: it would bring in changesets its plan did not consume.
- **Merges into the default branch held while a release PR is open.** Not taken: every merge would wait out each release's review and run, where a replaced PR costs that one release a second run.
- **The refusal of a move off a candidate in the plain upgrade alone.** Rejected: `--pre` and a raise by `pkit pin` make the same move.
- **A script a candidate shipped kept add-only, with the default branch's scripts numbered after it.** Rejected: a branch's script left in a folder the default branch released would run for no project upgrading past that release.

## Implications

- **ADR-089** gains this line at the top of its body, before its Summary, and its text stays as it is under it but for the refinement below:

  > **Partially superseded by [ADR-092](ADR-092-final-release-from-head.md).** Every final release, the one at a candidate's version included, is the ordinary release PR from the default branch's head, and no command asks whether a line runs ([PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md)). A candidate is cut from the head of a branch that has taken in the default branch's head, a cut's number counts every candidate the remote holds, and a withdrawal is a tag `--pre` reads. A project on a candidate moves to no other release, and leaves it by leaving the testers' branch, so a candidate's scripts bind nothing until its branch merges. Overturned: the cut from the default branch's head alone (points 1 and 2), the counter for each version and four of the cut's refusals (point 2), the final release cut from the last candidate's source commit (point 3, but its last two bullets), the add-only rule and the folder rule (point 5), a withdrawn candidate found by `--pre` and every move on from a candidate (point 8), and the run that ends a line (point 9). ADR-092's "What this overturns in ADR-089, and what stands" lists each passage. The rest of ADR-089 stands.
- **ADR-089 point 7, refined in place:** `pkit unpin`'s message names "leaving the testers' branch (point 8, refinement per ADR-092)", in place of "leaving the testers' branch, or `pkit upgrade` once the final release ships (point 8)".
- **ADR-049 point 3, refined in place:** in a project whose manifest records a release candidate, neither `pkit pin <version>` nor `pkit upgrade` raises the pin to any release but that candidate (refinement per ADR-092 point 7).
- **ADR-065, refined in place,** each with the pointer `(refinement per ADR-092)`:
  - point 4: each of its two lists of upgrade's own checks opens with the refusal ADR-092 point 7 sets, and step 4 drops "so a completion at a candidate sits below its final release's folder, and the next transition runs that folder again", since no transition starts from one
  - point 8's candidate row: `pkit upgrade --pre` "hands over to that candidate", and "No other release finishes it" in place of "No latest release finishes it while its line runs"
  - point 9's first case: under `pkit upgrade --pre`, a candidate the manifest records takes the latest release's place
  - point 9's second case: "since no other release finishes that move" in place of "since no latest release finishes that move while its line runs"
- **PRJ-004 needs no edit from this record:** the withdrawal's tag names no install (point 4).
- **#2211's build plan** drops the cut from the source commit, the refusals of what cannot wait, the merge's check of a running line, the resumed final release's PR, the hand-over from a candidate to the final release, the add-only rule, the folder rule and its test, and the cut's refusals of a component below an earlier candidate's version and of a second cut of one commit. It adds the cut from a branch's head and its run of `check-diff`, the counter across every candidate tag, the withdrawal's tag and `--pre`'s reading of it, point 6's check in the merge queue's run, refusal at `pkit release merge`, tag of the commit that changed `.pkit/VERSION` and replacement of a stale release PR, and point 7's refusal.
- **The release README, with the build:** the counter, the cut from a branch and its refusals, the withdrawal, the final release's one path and the release PR's link. Its section on merging the release PR gains the check in the merge queue's run, the command's refusal and the seconds it leaves open on a base with no queue, and the way on, the stale PR replaced. Its section on the automated flow says that the release-tag workflow tags the commit that changed `.pkit/VERSION`, and that the release workflow replaces a stale release PR.
- **The lifecycle reference, with the build:** a script on a branch may be renumbered or moved until the branch merges, whether or not a candidate shipped it, as point 8 sets.
- **The CLI reference, with the build:** the refusal of `pkit upgrade` and `pkit pin` on a candidate, with its message, and `pkit unpin`'s message.
- **No migration:** nothing installed changes shape, nothing overturned was built, and no project is at a candidate before the build.
