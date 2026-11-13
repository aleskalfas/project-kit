---
id: PRJ-016
title: A release candidate holds no release back
status: proposed
date: 2026-11-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

**In plain terms:** a change that must be tested before it ships is tested on its own branch, and merges only once its testing passes. Whatever merges into the default branch ships with its next release, tested or not, so the default branch can release whenever no migration script merged into an old version's folder holds it, and every final release is the ordinary one from its head. A candidate cut from a branch previews the release the default branch would make once that branch merges, and a tester tries each candidate fresh, from a final release its branch has taken in. For example, a major is built on its branch and tested as `3.0.0rc1`. A fix merged meanwhile ships at once as `2.1.1`. The branch takes in the default branch again and is cut as `3.0.0rc2`, and a tester leaves the testers' branch, a branch in the tester's own project, and enters `3.0.0rc2` from the final release the project stood at. Once its testing passes, the branch merges, and the next release is `3.0.0`.

[PRJ-002](PRJ-002-version-bump-policy.md) D5 lets a candidate line hold every other release back. Its final release is cut from the last candidate's source commit, and a change merged after that commit waits for a later release or needs another candidate first. [ADR-089](../../../tech-docs/architecture/decisions/ADR-089-release-candidates.md) builds that into the release step, and moves a tester's project from each candidate to the next and on to the final release. None of it is built ([#2211](https://github.com/aleskalfas/project-kit/issues/2211)).

The maintainer chose on 12 November 2026 ([#3075](https://github.com/aleskalfas/project-kit/issues/3075)):
- **No release waits on another:** "fixing release process first but in that way that we would not need to wait on it in future if it is possible and logic."
- **A change is tested before it merges.** Of three ways to test a change while releases go on, he chose to test it on its branch before it merges into the default branch. The other two were a fix that ships with a change under test or waits for it, and a side path that releases fixes from the last release's tag.
- **Each candidate is tried fresh.** Asked how a tester moves from one candidate to the next, he answered "B": a project never moves from a candidate to another release, and its tester leaves the testers' branch and enters the next candidate from the project's last final release. The other way was an upgrade in place, `pkit upgrade --pre` from one candidate to the next.

[ADR-092](../../../tech-docs/architecture/decisions/ADR-092-final-release-from-head.md) records the release step's side, accepted with this record.

## Decision

**A change that must be tested before it ships is tested on its own branch before it merges, every final release is the ordinary release from the default branch's head, and a project tries each candidate fresh, from a final release.**

### 1. Every final release is the ordinary release from the default branch's head

The release step cuts each final release of project-kit as PRJ-002 D3 cuts any, from the default branch's head and the changesets pending there, and its tag names the content its release PR merged. Nothing refuses a release because candidates are out, and no release is cut from a candidate's commit.

### 2. What merges into the default branch ships with its next release

A change merged into project-kit's default branch ships with the next release, whether or not a candidate held it, so the default branch can release whenever no stranded migration script holds it (ADR-092 point 8). A change that must be tested before it ships, such as a major, stays on its own branch until its testing passes. Such a branch lives longer than [COR-009](../core/COR-009-pr-workflow.md) point 4's short-lived default, a departure COR-009 lets a project record, still only as long as its pull request, and pays for its drift with the take-in point 3 requires.

### 3. A candidate previews the release a branch's merge would make

A candidate of project-kit is cut from the head of the branch that holds the change, once that branch has taken in the default branch's head. It holds the versions the release step computes from the versions the default branch records and the changesets pending there and on the branch. Once its testing passes, the branch merges, and the next release ships it. A candidate may also be cut from the default branch's head, to try the next release.

### 4. A project tries each candidate fresh, from a final release its branch has taken in

A project moves onto a candidate only from a final release no newer than the last one the candidate's branch took in, or a candidate's `init` installs it there, and from a candidate it moves to no other release, candidate or final. Its tester leaves a candidate by leaving the testers' branch, a branch in the tester's own project, and from the final release the project stood at enters a later candidate, or upgrades; a project a candidate's `init` installed starts again from a final release's `init`. This binds every project that tests a candidate.

### 5. The release step reuses no candidate number, whatever its version or branch

project-kit's release step gives each candidate a number `N` that no earlier candidate took, so each pre-release version a candidate writes names one content. That holds for every cut the release workflow makes whose branch keeps that workflow and the `pkit` it runs as the default branch has them (ADR-092 point 10). A candidate's tag is never moved or deleted, withdrawn or not ([PRJ-004](PRJ-004-distribution-channel.md)), so `pkit version untag` refuses one; a deletion by hand lies outside, as any act write access allows.

### What this overturns in PRJ-002, and what stands

Overturned:

- in the Context, "A release may also need testing before it ships", which point 2 makes a change tested on its branch before it merges
- in the Decision's lead on candidates, in D4 and in D5, a candidate as the preview of the next final release, and a source commit as the head of `main`, which point 3 restates as the release a branch's merge would make and the commit it is cut from, and the candidate line, which no rule reads once each candidate is tried fresh (point 4)
- in D3, "that ends no candidate line", the paragraph on the final release that ends a candidate line, and a candidate's commit "made on top of `main`'s head"
- in D5, "from the head of `main`" in "Cut on request", "by marking its Release so" in "One version, one content", which ADR-092 point 4 takes, and the bullets "The final release is cut from the last candidate's source commit", with its last candidate withdrawn needing another candidate first, "What cannot wait" and "No other release ships while a line runs"
- in "Policy, not mechanics", ADR-089 as the home of the counter and of the final release's cut from the source commit and its refusals, which ADR-092 takes
- in the Rationale, "its head unless a candidate line ends" in "Why version numbers reach `main` only through the release step", all but the first sentence of "Why each moved component carries the suffix", whose reason point 5's replaces, and the paragraphs "Why the final release is cut from the last candidate's source commit" and "Why some changes merged since cannot wait"
- the alternative of a final release cut from a later commit a person judges safe, which point 2 takes: a person judges a change releasable when it merges
- in the alternative "A candidate's components at release versions", "and a project moving between them would run none of the migrations added in between", a move no project makes (point 4)
- in the Implications, the exception for the final release that ends a line, whose tag is cut before its PR opens, and "off `main`" for where a candidate is cut

Standing: the rest of PRJ-002. Among it are a candidate consuming no changeset, its versions only in its tag, a person withdrawing a candidate found unfit while its tag and number stay, its floors waiting for the final release, and the rejection of a `main` held while candidates are tested.

## Rationale

**Points 1 and 2, the default branch releases whenever no stranded script holds it.** The release step computes from every changeset pending at the default branch's head (PRJ-002 D3). So a change merged there is in every later release, and a major merged before its testing would make each one the major: a fix would then ship it untested or wait for its testing. Kept on its branch until it passes, a change under test holds no release back, and the default branch needs no second path to release a fix. The tagged commit is the state an install of the release's version is built from (PRJ-002 D3), so it holds what the release PR merged and nothing merged after it.

**Point 3, a preview of the merge.** Having taken in the default branch's head, the branch holds the versions the default branch records and every changeset pending there, beside its own. So its candidate holds what the default branch would release once the branch merges, where a branch behind would preview a release that cannot happen. A candidate consumes no changeset, so cutting one changes nothing the default branch releases (PRJ-002, "Why a candidate's versions live only in its tag").

**Point 4, each candidate tried fresh.** A move from a candidate runs another release's migrations over what the candidate's scripts did, a state no project reaches on the path without candidates. That move would be safe only under rules of its own: a window from the last final release on each move, the scripts a candidate shipped kept as they were, and the default branch's scripts numbered after a branch's. A final release made since the branch last took in the default branch holds scripts and state the candidate never held, and a move from it would skip the branch's scripts in folders at or below that release. From a release the branch took in, every move a tester makes runs the window an adopter's runs, and leaving the testers' branch takes the project's files back, so a branch may change its scripts until it merges (ADR-092 points 8 and 9).

**Point 5, numbers across versions and branches.** A candidate computes each component's version from the versions the default branch records. Two candidates can then move a component to the same version: cut from two branches at one base, or either side of a release that left the component unmoved. So only a number no candidate took keeps each version to one content (PRJ-002 D5, "One version, one content").

**The costs.** A change merged into the default branch ships untested unless a candidate cut from its head tried it, which the maintainer accepts so that the default branch releases whenever no stranded script holds it. Changes tested on two branches ship together without being tested together, unless such a candidate tries them. A tester makes one entry, and one move from a final release, for each candidate, waits for the next cut where the default branch released since the last, and carries work done on the testers' branch over by hand. Leaving that branch takes back only the files git tracks, so what a migration did elsewhere, such as a label renamed on the host or a file git ignores, stays, and the project's own branch at its final release, and a later candidate's scripts, run over it.

### Alternatives considered

- **Keep the line holding every release,** as PRJ-002 D5 sets it. Rejected: each fix waits on testers, which the maintainer chose against.
- **Test a change after it merges,** so a fix made during its testing ships with it or waits. Rejected: a major under test would make every release the major, and the maintainer chose the test before the merge.
- **Release fixes on a side path from the last release's tag.** Rejected: a second release path, with versions, a changelog and migration folders of its own beside the default branch's, and the maintainer chose the test before the merge.
- **Move a tester's project from one candidate to the next in place,** by `pkit upgrade --pre`. Rejected: the maintainer chose to try each candidate fresh, which keeps every move a tester makes on the path without candidates (point 4).
- **Refuse a final release from the commit a withdrawn candidate was cut from.** Not taken: a release starts only when a person asks (ADR-089 point 9), and the next merge moves the head past that commit, so the refusal would hold back nothing a person's choice does not.
- **Count numbers for each version, or from 1 again after each release.** Rejected: two candidates of one version, from two branches or either side of a release that left a component unmoved, would give one version two contents.

## Implications

- **PRJ-002** gains this line at the top of its body, before its Context, and its text stays as it is under it but for the refinements below:

  > **Partially superseded by [PRJ-016](PRJ-016-candidates-hold-no-release.md).** A change that must be tested before it ships is tested on its own branch before it merges, a candidate is cut from that branch's head, a project tries each candidate fresh from a final release, and every final release is the ordinary release from `main`'s head. Overturned: the final release cut from the last candidate's source commit, in D3, D5 and the Rationale, with D5's "What cannot wait" and "No other release ships while a line runs", a candidate cut from `main`'s head alone, and the candidate line. PRJ-016's "What this overturns in PRJ-002, and what stands" lists each passage. The rest of PRJ-002 stands.
- **PRJ-002, refined in place:**
  - with the pointer `(refinement per PRJ-016 point 3)`: "the commit it is cut from" in place of "its source commit" in D4's "Its tree keeps the floors its source commit carries" and in D5's "From the pending changesets"
  - with the pointer `(refinement per PRJ-016 point 1)`: in "Why a candidate's versions live only in its tag", "So `main`'s head and the changesets pending there make the next final release" in place of the sentence that names commits of `main`, and in D3 and in the Implications, the tag is cut on "the commit that holds the content its release PR merged" in place of "the commit its release PR leaves there" and "the commit it leaves on `main`"
- **PRJ-004, refined in place:**
  - with the pointer `(refinement per PRJ-016 point 2)`: its candidate tag serves whoever chooses "to test a change before it merges" in place of "to test the next final release before it ships"
  - with the pointer `(refinement per PRJ-016 point 1)`: its Implications bullet on release notes publishes them from the release workflow's run "for a candidate" in place of "for a candidate and for the final release that ends a line"
  - with the pointer `(refinement per PRJ-016 point 5)`: its list of refs gains `withdrawn/v<candidate>`, a candidate's withdrawal, which names no install, since no reader of release and candidate tags takes a tag under `withdrawn/` for either
- **ADR-092** records the release step's side, and names its edits to ADR-089, ADR-065, ADR-063 and ADR-049.
- **The analysis anchored on PRJ-002** is answered in the change that makes these edits.
- **The project's `CLAUDE.md`, "Versioning",** gains: a change that must be tested before it ships stays on its branch until its testing passes, and no coordinator lands it before.
- **No migration.**
