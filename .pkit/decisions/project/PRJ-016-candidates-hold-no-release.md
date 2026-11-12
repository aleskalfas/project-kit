---
id: PRJ-016
title: A release candidate holds no release back
status: proposed
date: 2026-11-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

**In plain terms:** a change that must be tested before it ships is tested on its own branch, and merges only once its testing passes. Whatever merges into the default branch ships with its next release, tested or not, so the default branch can release at any time, and every final release is the ordinary one from its head. A candidate cut from a branch previews the release the default branch would make once that branch merges. For example, a major is built on its branch and tested as `3.0.0rc1`, cut from that branch's head. A fix merged meanwhile ships at once as `2.1.1`. The branch takes in the default branch again and is tested as `3.0.0rc2`, and once its testing passes it merges, and the next release is `3.0.0`.

[PRJ-002](PRJ-002-version-bump-policy.md) D5 lets a candidate line hold every other release back. Its final release is cut from the last candidate's source commit, and a change merged after that commit waits for a later release or needs another candidate first. [ADR-089](../../../tech-docs/architecture/decisions/ADR-089-release-candidates.md) builds that into the release step, and none of it is built ([#2211](https://github.com/aleskalfas/project-kit/issues/2211)).

The maintainer chose on 12 November 2026 ([#3075](https://github.com/aleskalfas/project-kit/issues/3075)):
- **No release waits on another:** "fixing release process first but in that way that we would not need to wait on it in future if it is possible and logic."
- **A change is tested before it merges.** Of three ways to test a change while releases go on, he chose to test it on its branch before it merges into the default branch. The other two were a fix that ships with a change under test or waits for it, and a side path that releases fixes from the last release's tag.

[ADR-092](../../../tech-docs/architecture/decisions/ADR-092-final-release-from-head.md) records the release step's side, accepted with this record.

## Decision

**A change that must be tested before it ships is tested on its own branch before it merges, and every final release is the ordinary release from the default branch's head.**

### 1. Every final release is the ordinary release from the default branch's head

The release step cuts each final release as PRJ-002 D3 cuts any, from the default branch's head and the changesets pending there. Nothing refuses a release because candidates are out, and no release is cut from a candidate's commit.

### 2. What merges into the default branch ships with its next release

A change merged into the default branch ships with the next release, whether or not a candidate held it, so the default branch can release at any time. A change that must be tested before it ships, such as a major, stays on its own branch until its testing passes.

### 3. A candidate previews the release a branch's merge would make

A candidate is cut from the head of the branch that holds the change, once that branch has taken in the default branch's head. It holds the versions the release step computes from the versions the default branch records and the changesets pending there and on the branch. Once its testing passes, the branch merges, and the next release ships it. A candidate may also be cut from the default branch's head, to try the next release.

### 4. A line ends with the release that ships its branch, or with a withdrawal

The candidates cut from one branch make its line. The line runs from its first candidate's tag until a final release ships the branch at or above its last candidate's version. A person withdraws each candidate that no such release will end: a dropped branch's, one whose branch is released below its version, and one that a final release at or above its version overtakes without the branch.

### 5. A withdrawn candidate holds nothing back

Nothing that reads candidates is held to it (ADR-092 point 4), and its testers leave it as every tester leaves a candidate, by leaving the testers' branch, which takes back what its migrations did (ADR-092 point 8). So a script a dropped branch's candidate shipped leaves with its testers, and never reaches the default branch, since that branch never merges. A script shipped for a change later taken out of a branch stays, undone where needed by a later script, until each candidate that shipped it is withdrawn.

### 6. No candidate number is reused, whatever its version or branch

Each candidate takes a number `N` that no earlier candidate took, so each pre-release version a candidate writes names one content.

### What this overturns in PRJ-002, and what stands

Overturned:

- in the Decision's lead on candidates and in D5, a candidate as the preview of the next final release, a line as the candidates of one final release running until that release's tag, and a source commit as the head of `main`, which points 3 and 4 restate
- in D3, "that ends no candidate line", the paragraph on the final release that ends a candidate line, and a candidate's commit "made on top of `main`'s head"
- in D5, "from the head of `main`" in "Cut on request", and the bullets "The final release is cut from the last candidate's source commit", with its last candidate withdrawn needing another candidate first, "What cannot wait" and "No other release ships while a line runs"
- in "Policy, not mechanics", ADR-089 as the home of the counter and of the final release's cut from the source commit and its refusals, which ADR-092 takes
- in the Rationale, "its head unless a candidate line ends" in "Why version numbers reach `main` only through the release step", the commits it names in "Why a candidate's versions live only in its tag", and the paragraphs "Why the final release is cut from the last candidate's source commit" and "Why some changes merged since cannot wait"
- the alternative of a final release cut from a later commit a person judges safe, which point 2 takes: a person judges a change releasable when it merges
- in the Implications, the exception for the final release that ends a line, whose tag is cut before its PR opens, and "off `main`" for where a candidate is cut

Standing: the rest of PRJ-002. Among it are a candidate consuming no changeset, its versions only in its tag, a withdrawn candidate's tag and number kept, its floors waiting for the final release, and the rejection of a `main` held while candidates are tested.

## Rationale

**Points 1 and 2, the default branch releases at any time.** The release step computes from every changeset pending at the default branch's head (PRJ-002 D3). So a change merged there is in every later release, and a major merged before its testing would make each one the major: a fix would then ship it untested or wait for its testing. Kept on its branch until it passes, a change under test holds no release back, and the default branch needs no second path to release a fix.

**Point 3, a preview of the merge.** Having taken in the default branch's head, the branch holds the versions the default branch records and every changeset pending there, beside its own. So its candidate holds what the default branch would release once the branch merges, where a branch behind would preview a release that cannot happen. A candidate consumes no changeset, so cutting one changes nothing the default branch releases (PRJ-002, "Why a candidate's versions live only in its tag").

**Points 4 and 5, a line's end.** A line's candidates hold later work to them: the cuts in their history, and the scripts they shipped, which stay as they are and set the order of every script added after them (ADR-092 points 3 and 4). The release that ships the branch carries those scripts on to every project. A dropped branch makes no such release, and one released below its candidates' version, or overtaken, must ship them in another folder. Its candidates' tags outlive the branch, so only a person's act ends such a line. Leaving the testers' branch takes a project back to where it stood before its first candidate. So once a withdrawn candidate's testers have left, no path a project takes runs on from it, and nothing need keep that path safe.

**Point 6, numbers across versions and branches.** A candidate computes each component's version from the versions the default branch records. Two candidates can then move a component to the same version: cut from two branches at one base, or either side of a release that left the component unmoved. A transition tells a move by comparing versions (PRJ-002, "Why each moved component carries the suffix"), so only a number no candidate took keeps the two apart.

**The costs.** A change merged into the default branch ships untested unless a candidate cut from its head tried it, which the maintainer accepts so that the default branch releases at any time. Changes tested on two branches ship together without being tested together, unless such a candidate tries them. A branch whose candidate the default branch's release overtakes cuts its line again, and its testers enter anew, so a line of a minor is overtaken by each minor the default branch releases, and a major's only by another major. A tester who moves on from a candidate onto a release without its branch, rather than leave the testers' branch, runs that release's migrations over what its scripts did, which nothing holds safe.

### Alternatives considered

- **Keep the line holding every release,** as PRJ-002 D5 sets it. Rejected: each fix waits on testers, which the maintainer chose against.
- **Test a change after it merges,** so a fix made during its testing ships with it or waits. Rejected: a major under test would make every release the major, and the maintainer chose the test before the merge.
- **Release fixes on a side path from the last release's tag.** Rejected: a second release path, with versions, a changelog and migration folders of its own beside the default branch's, and the maintainer chose the test before the merge.
- **A line that ends when its branch is deleted, with no act of its own.** Not taken: a candidate's tag outlives its branch, and the tags cannot tell a branch deleted from one merged.
- **Refuse a final release from the source commit of a withdrawn candidate.** Not taken: the default branch holds only what may ship (point 2), so a candidate found unfit there is mended there.
- **Count numbers for each version, or from 1 again after each release.** Rejected: two candidates of one version, from two branches or either side of a release that left a component unmoved, would give one version two contents.

## Implications

- **PRJ-002** gains this line at the top of its body, before its Context, and its text stays as it is under it:

  > **Partially superseded by [PRJ-016](PRJ-016-candidates-hold-no-release.md).** A change that must be tested before it ships is tested on its own branch before it merges, a candidate is cut from that branch's head, and every final release is the ordinary release from the default branch's head. Overturned: the final release cut from the last candidate's source commit, in D3, D5 and the Rationale, with D5's "What cannot wait" and "No other release ships while a line runs", and a candidate cut from `main`'s head alone. PRJ-016's "What this overturns in PRJ-002, and what stands" lists each passage. The rest of PRJ-002 stands.
- **PRJ-004, refined in place:** its Implications bullet on release notes publishes them from the release workflow's run "for a candidate", in place of "for a candidate and for the final release that ends a line", with the pointer `(refinement per PRJ-016)`.
- **ADR-092** records the release step's side, and names its edits to ADR-089 and ADR-065.
- **The analysis anchored on PRJ-002** is answered in the change that makes these edits.
- **No migration,** and the project's `CLAUDE.md` needs no change.
