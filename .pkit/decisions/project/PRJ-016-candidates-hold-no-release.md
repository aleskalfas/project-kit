---
id: PRJ-016
title: A release candidate holds no release back
status: proposed
date: 2026-11-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

**In plain terms:** a release candidate is a tagged preview of the next release, and it holds no release back. The final release is cut from the default branch's head like any other release. A person who wants it to ship exactly what was tested cuts one more candidate just before it. For example, a fix merges while `2.1.0rc1` is under test: `2.1.0` may ship from the head at once, fix included, or right after a `2.1.0rc2` that tests it.

[PRJ-002](PRJ-002-version-bump-policy.md) D5 lets a candidate line hold every other release back. Its final release is cut from the last candidate's source commit. A change merged after that commit waits for a later release, or needs another candidate first. [ADR-089](../../../tech-docs/architecture/decisions/ADR-089-release-candidates.md) builds that into the release step, and none of it is built yet ([#2211](https://github.com/aleskalfas/project-kit/issues/2211)).

The maintainer chose on 12 November 2026 that no release waits on another ([#3075](https://github.com/aleskalfas/project-kit/issues/3075)): "fixing release process first but in that way that we would not need to wait on it in future if it is possible and logic." [ADR-092](../../../tech-docs/architecture/decisions/ADR-092-final-release-from-head.md) records the release step's side, accepted with this record.

## Decision

**A release candidate holds no release back: every final release is cut from the default branch's head, the one at a candidate's version included.**

### 1. Every final release is cut from the default branch's head

While candidates are out, the release step cuts each final release as PRJ-002 D3 cuts any, from the default branch's head and the changesets pending there. Nothing refuses a release because candidates are out, and nothing ties one to a candidate's source commit.

### 2. Shipping exactly what was tested is a choice for each release

A final release ships each change merged before its release PR lands, whether or not a candidate held it. The person who cuts it may first cut one more candidate from the same head, and then land the release PR before anything else merges.

### 3. A line ends with the first final release at or above its version

A line runs from its first candidate's tag until a final release at or above its version ships, its own or a later one that overtakes it. Lines at different versions may run at once, and an overtaken line's version is never released.

### 4. No candidate number is reused, whatever its version

Each candidate takes a number `N` that no earlier candidate took, at any version, so each pre-release version a candidate writes names one content.

### What this overturns in PRJ-002, and what stands

Overturned:

- in D3, the qualifier "that ends no candidate line", and the paragraph on the final release that ends a candidate line
- in D5, a line's end "until its final release's tag", and the bullets "The final release is cut from the last candidate's source commit", "What cannot wait" and "No other release ships while a line runs"
- in "Policy, not mechanics", ADR-089 as the home of the counter and of the final release's cut from the source commit, which ADR-092 takes
- in the Rationale, the source commit as the final release's commit, in "Why version numbers reach `main` only through the release step" and in "Why a candidate's versions live only in its tag", and the paragraphs "Why the final release is cut from the last candidate's source commit" and "Why some changes merged since cannot wait"
- the alternative of a final release cut from a later commit a person judges safe, which points 1 and 2 take
- in the Implications, the exception for the final release that ends a line, whose tag is cut before its PR opens

Standing: the rest of PRJ-002. Among it are a candidate's definition and source commit, its versions only in its tag, its floors waiting for the final release, and the rejection of a `main` held while candidates are tested.

## Rationale

**Releases go on.** A candidate consumes no changeset, so the head and the changesets pending there make the next release at any time (PRJ-002, "Why a candidate's versions live only in its tag"). A line that held every release made each fix wait on its testers, though nothing in the release needed the wait.

**One path for the final release.** Its cut from the source commit kept untested changes out, at the cost of a second path for one release. That path tagged before its pull request, brought an older commit's versions into a moved default branch, and refused what it would lose or break. One more candidate just before the release gives the same guarantee to whoever wants it, on the path every release takes.

**The costs.** A release may ship a change no candidate held, which the maintainer accepts so that no release waits. A change a candidate held may also be taken out before the release. Where that leaves a component below the candidate's version of it, a project on the candidate cannot move to the release, since a transition never moves a component down ([ADR-065](../../../tech-docs/architecture/decisions/ADR-065-upgrade-runs-the-transition.md) point 7). Its tester leaves the testers' branch (ADR-089 point 8).

**A line's end.** A project on a candidate moves on once the latest release is newer than that candidate (ADR-065 point 9). Any final release at or above a line's version is newer than each of its candidates.

**Numbers across versions.** A candidate computes each component's version from the versions the default branch records. Two candidates of different versions can then move a component to the same version, both cut from the same recorded versions, or cut either side of a release that left the component unmoved. A transition tells a move by comparing versions (PRJ-002, "Why each moved component carries the suffix"), so only a number no candidate took keeps the two apart.

### Alternatives considered

- **Keep the line holding every release,** as PRJ-002 D5 sets it. Rejected: each fix waits on testers, which the maintainer chose against.
- **Cut the final release from the last candidate's source commit while other releases go on from the head.** Rejected: both would consume the same changesets, at different versions.
- **Refuse a release that ships a change no candidate held.** Rejected: every merged change would need another candidate first, the wait this record removes.
- **Refuse a release that leaves a component below a candidate's version of it.** Rejected: the release would wait on a change taken out, where the tester can leave the testers' branch.
- **Count numbers for each version, with one line at a time among candidates.** Rejected: a major's first candidate would wait until the running line was released or overtaken.
- **Count numbers from 1 again after each release.** Not taken: a component a candidate moved, and the release then left unmoved, could take the same version again.

## Implications

- **PRJ-002** gains this line at the top of its body, before its Context, and its text stays as it is under it:

  > **Partially superseded by [PRJ-016](PRJ-016-candidates-hold-no-release.md).** A release candidate holds no release back: every final release is cut from the default branch's head, and a line ends with the first final release at or above its version. Overturned: the final release cut from the last candidate's source commit, in D3, D5 and the Rationale, with D5's "What cannot wait" and "No other release ships while a line runs". PRJ-016's "What this overturns in PRJ-002, and what stands" lists each passage. The rest of PRJ-002 stands.
- **PRJ-004, refined in place:** its Implications bullet on release notes publishes them from the release workflow's run "for a candidate", in place of "for a candidate and for the final release that ends a line", with the pointer `(refinement per PRJ-016)`.
- **ADR-092** records the release step's side, and names its edits to ADR-089.
- **The analysis anchored on PRJ-002** is answered in the change that makes these edits.
- **No migration,** and the project's `CLAUDE.md` needs no change.
