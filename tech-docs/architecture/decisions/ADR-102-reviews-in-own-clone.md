---
id: ADR-102
title: In a seat's clone, each reviewer works in a clone of its own
status: accepted
date: 2026-11-23
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a seat's clone is the clone of the repository that a seat of the project's topology works in ([project-management:DEC-059-topology-of-seats]). Its working tree stays on the default branch while the seat goes on working ([ADR-073](ADR-073-builder-runs.md) point 8). The review command runs a change's reviewers as agents of their own, unconfined, in the checkout it runs in ([ADR-066](ADR-066-unattended-agent-runner.md) point 10). In a seat's clone, that checkout is the seat's own. A reviewer that checks a change out there moves the seat's working tree onto unreviewed commits, and every command the seat runs next loads its code from them. Reviewers that run at once also write under one another there ([ADR-100](ADR-100-runs-in-seat-clone.md) point 10).

This record gives each reviewer, in a seat's clone, a clone of its own:
- The backbone makes it from the code host, at the default branch's head, in a folder no other session's sandboxed command writes.
- The runner holds the reviewer there to the permissions a person realized for the seat's clone, which the harness would otherwise drop in a folder nobody trusted.
- The reviewer reads the change through git, and keeps its files in its own clone.

So the seat's working tree stays where the seat left it, and no reviewer works where another does. Outside a seat's clone, reviewers work in the checkout the review command runs in.

## Context

- **Where reviewers work.** The review command's runs take the runner's unconfined form, and "work in the person's checkout" (ADR-066 point 10). They load the person's and the project's settings there, in the mode those or the harness choose, which may approve calls no rule allows. The command starts a review's reviewers at once (the project-management README, "The reviewers run at the same time").
- **What a seat relies on.**
  - In a project with a topology, a seat's working tree stays clean and on the default branch. The build command refuses a seat's clone whose working tree is elsewhere, so no tool, setting, hook or instruction the seat runs is a build's (ADR-073 point 8).
  - A reviewer may check out the change and run its code (ADR-073 point 10).
  - For a head that holds a sandboxed build's commits and that nobody named, the brief tells the reviewer to start nothing of it and to check it out nowhere ([project-management:DEC-067-heads-that-start-programs] point 5). That is an instruction, not a bound.
- **What runs at once.** Under ADR-100, a clone runs builds and reviews at once, up to its pace. Its point 10 leaves two cases open:
  - reviews of several changes at once write under one another and under the clone's own work;
  - a reviewer that checks out its change in a seat's checkout moves that working tree off the default branch while the seat goes on working. The agent's builds are then refused, and the seat's own commands run from a build's unreviewed commits.

  It asks a record to settle the second before a build relies on reviews running beside the seat's own work.
- **The clones the methodology makes for agents' runs.**
  - The backbone's run command makes, checks and removes a confined run's clone, and keeps a working run's for its caller. Each lies in a folder of the backbone's that only the person's account writes, sharing no object with the person's repository (ADR-066 point 7, ADR-073 point 1).
  - A drift command makes the clone its unconfined run works in (ADR-066 point 10).
  - Claude Code ignores a project's allow rules in a folder nobody trusted, so a working run's runner passes the rules itself (ADR-073's Context and point 2).
- **What a sandboxed command can write.** Code that runs outside the sandbox without a person choosing it never comes from a place a sandboxed command can write. Such a place widens what that code allows only where a person, shown the widening, makes it. The rule binds every later architecture record ([ADR-095](ADR-095-hook-out-of-reach.md) point 1). The methodology's own commands are such code, and on macOS they run outside the sandbox ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) point 2). Only realizing widens the hook's bound, and the bound that holds a session in a realized folder is the snapshot a person realized there (ADR-095 point 3).

## Decision

**In a seat's clone, each reviewer works in a clone of its own:**
- **the backbone makes it** from the code host, at the default branch's head, in a folder only the person's account writes;
- **the runner bounds it** by the permissions a person realized for the seat's clone.

**So no reviewer works in the seat's checkout, or where another reviewer works.**

### 1. Where it binds

- **In a seat's clone:** a clone of the repository whose runtime folder holds a seat of the project's topology (DEC-059). The review command tells one as the build command does (ADR-073 point 8). Without that seat, the clone holds no seat's claim, so no build of the seat's runs there either.
- **Not in a linked worktree of a seat's clone,** which reads no seat until a record decides how it reads its clone's identity (DEC-059 point 6).
- **Elsewhere,** reviewers work in the checkout the review command runs in (ADR-066 point 10).

### 2. Each reviewer gets a clone of its own

- **A reviewer's clone** is a clone in git's sense, made for one reviewer's run. It is no seat's clone. The review command asks the backbone's run command for one for each reviewer it runs, and names the commit, the remote and the references to fetch.
- **Made, recorded and removed by the run command,** as it does a confined run's clone (ADR-066 point 7):
  - It lies in a folder of the backbone's that only the person's account writes, outside every working tree and outside the per-user temp folder. So it lies outside the default reach of every other session's and run's sandboxed commands (ADR-095 point 2, "Not where a sandboxed command writes by default").
  - Where the run command cannot write such a folder, as from inside a sandbox on Linux, it refuses the run (ADR-066 point 7, "Where it cannot"). The review command then refuses the review, and names a review started at the person's own terminal as the way out.
  - The run command removes the clone once the reviewer's run ends, whatever its verdict. It removes a clone a killed review left only once the process its record names reads as ended, and keeps it where the backbone cannot tell (refinement per [ADR-103](ADR-103-process-liveness-reading.md)).
- **What it holds.**
  - A git folder of its own, with no hook, sharing no object with the seat's repository.
  - One remote, at the address the code host gives for the pull request's base repository. It takes the name of the remote the default branch resolves through ([COR-054](../../../.pkit/decisions/core/COR-054-default-branch.md)), with that remote's default-branch reference set. Its push address is one no push can use.
  - What the run command fetches from the code host:
    - the default branch;
    - the change's base branch's head;
    - the change's head, through the code host's reference for the pull request, which serves a fork's head too.

    Where the head does not resolve to the head the review command names, the one it stamps in the verdict's marker ([project-management:DEC-028-agent-as-approver-paths], "The verdict signal"), the run command refuses the run, so no other commit is reviewed. The fetch may leave out the contents of files the review does not read.
- **At the default branch's head,** as the code host holds it when the review starts, checked out with no branch. These load from that commit:
  - the harness's settings and instructions;
  - the reviewer's definition and the runner;
  - the methodology's commands the reviewer runs.

  So the methodology's commands resolve the default branch there as in the seat's clone, and the code host's command line finds the repository and the pull request.
- **Its agent workspace.** The run command makes it, refusing where the commit holds anything at that path, with the guards [ADR-060](ADR-060-path-scoped-workspace-allow.md) points 1 and 2 give, as a drift command makes its run's (ADR-066 point 10).
- **The person's local settings** are carried into the clone, as for a drift command's unconfined run (ADR-066 point 10).
- **The reviewer's definition** is found in the clone as a drift command's unconfined run finds a fixer's (ADR-066 point 10). A name no place of the methodology ships is refused where the clone's commit deploys no copy of it, since a change cannot alter its own reviewer. The person's own agents folder is found as in any session.

### 3. The reviewer keeps the seat's permissions in its clone

Claude Code ignores a project's allow rules in a folder nobody trusted, and no realized folder holds the clone (ADR-073's Context, ADR-066 point 9). So the runner gives the run the permissions that hold a session in the seat's clone:
- **The bound.** The core from the copy chooses the snapshot that binds the seat's clone, and checks it, as it chooses a session's bound (ADR-095 point 2, "One verdict"; point 3). The runner copies that snapshot into the run's settings folder, a guarded folder the run does not write (ADR-095 point 2).
- **Where that snapshot cannot be used** (ADR-095 point 4), the run is refused, and the review names the realizing command.
- **The hook.** Where the seat's clone's settings register the permission hook, the runner registers it from the copy (ADR-095 point 2) and names that snapshot as its bound (ADR-095 point 3, "A bound a runner names"). The registration the clone's own settings carry runs beside it with no bound, giving its own verdicts and the clone's model's narrowing (ADR-095 point 4). The harness keeps the stricter of the two hooks' verdicts.
- **The native rules.** It passes the allow, ask and deny rules of the seat's clone's settings file as the run's settings. The harness keeps that file from sandboxed writes (ADR-095's precondition). The settings it passes carry those rules and that registration alone: no mode, no sandbox setting, no added folder, and no other hook or server.
- **Where no snapshot binds the seat's clone,** the runner names none, and the reviewer is held as it would be in the seat's clone.

In every other way the run stays unconfined, in the mode the settings choose (ADR-066 point 10).

### 4. What a reviewer does in it

- **It reads the change through git.** The brief tells the reviewer two things. Its working tree holds the default branch's head, not the change. It reads the change by its diff and by its files at the head's commit. The contract lives in the brief, as DEC-067 point 5's does, so no reviewer's definition changes.
- **It checks out only in its clone.** A reviewer that checks out the change, writes a file or runs a program in its working folder does so in its own clone. Where the brief tells it to check out the head nowhere (DEC-067 point 5), that also holds.
- **The review command posts the verdict.** It reads the verdict from the reviewer's last message and posts it on the code host. Nothing in the clone is carried out.

### 5. What this closes, and what stays open

- **The seat's working tree** stays where the seat left it, whatever a reviewer does in its working folder, and the seat's commands go on loading their code from it.
- **In a seat's clone, no reviewer works where another does.** Each reviewer, of one review or of several at once, has a working folder of its own.
- **Beyond its clone,** a reviewer that names the seat's checkout or another clone by path is bounded as any of the person's runs is:
  - where the person's sandbox is on, its shell writes only its working folder and the per-user temp folder;
  - the hook asks, in every mode, before a file tool writes outside the session's repository and before a call leaves the sandbox ([ADR-093](ADR-093-writes-outside-the-repository.md) point 1, ADR-095 point 4), and a run nobody watches refuses an ask.

  A session whose sandbox is off, and a command the sandbox exempts, pass those bounds (ADR-095 point 7, "Limits of the protection"). They stay open until a record confines the reviewers' runs (ADR-073 point 10).
- **The change's code.** A reviewer that checks out the change in its clone and runs its code runs a build's commits outside a sandbox, with the seat's access (ADR-073 point 10).
- **The code a reviewer runs.** A reviewer's own shell writes its working folder, its clone, from which its later commands load their code. That is the member of ADR-095 point 1's class that ADR-066 point 11 names for what an unconfined run loads from its clone, and that ADR-073 point 10 names for the reviewers' runs. This record leaves it as they decide, and only the reviewer itself reaches it.
- **What the runtime folder steers.** The review command tells a seat's clone from the identity its runtime folder holds, which a sandboxed command writes. One that removes the identity sends reviewers back to the checkout, as in a clone with no seat. It also removes the seat's claim, so no build of the seat's runs there (ADR-100 point 5, "What the runtime folder steers").
- **A linked worktree of a seat's clone** runs its reviewers in its own checkout (point 1), until a record decides how it reads its clone's identity (DEC-059 point 6).
- **Which repository.** The review command finds the pull request, and so the base repository the clone fetches from, through the checkout's configuration, as every capability command finds its own (ADR-100 point 5, "The folder they find").
- **A clone with no seat.** There, reviews of several changes at once still write under one another (ADR-100 point 10).
- **A drift command's unconfined run** loses the project's allows in its clone the same way. This record leaves it as ADR-066 point 10 decides.
- **A process a reviewer leaves behind,** such as one that daemonised, may outlive its clone's removal (ADR-066 point 11).

### 6. The probe

Before the build rests on it, a probe confirms these on each platform the adapter supports:
- in its clone, under the settings the runner passes, a reviewer runs the code host's command line, git and the methodology's checks with no prompt;
- with two registrations of the hook, the stricter verdict holds, and the runner's registration judges by the snapshot it names;
- a snapshot that cannot be used refuses the run;
- a file tool's write into the seat's checkout is asked, and refused in a run nobody watches.

A fact the probe disproves refines or supersedes this record.

## Rationale

**Why a clone of its own.** It keeps the seat's working tree where it was, whatever a reviewer does in its working folder. That holds for a reviewer that checks out despite its brief, and needs no check before each of the seat's commands.

**Why one for each reviewer, not one for each review.** A review's reviewers run at once. In a clone they shared, the first to check out the change would move it under the others. Their commands would then run the change's own code, and a change that rewrote a check could pass its own review.

**Why at the default branch's head, not the change's.** A reviewer's commands load their code from its clone. At the change's head, every one of them would run the change's unreviewed code, unconfined, from the start. At the default branch's head, what the harness loads and what the reviewer runs are what has merged: the commit the seat's own working tree holds.

**Why from the code host, sharing no object.** Git trusts the objects of a repository it borrows from without hashing them again, and a fetch skips the objects that repository holds. So a clone that borrowed the seat's objects would check out what a sandboxed command of the seat's could have rewritten. That includes the clone's settings, whose hooks and servers run outside the sandbox (ADR-095 point 1). A fetch that leaves out the files the review does not read keeps the cost near one checkout's.

**Why in a folder only the person's account writes.** The reviewer's commands, the runner and the hooks the clone's settings register run outside the sandbox, from the clone. The per-user temp folder, which a sandboxed command writes by default (ADR-095 point 2), would let another session's command rewrite them before they run.

**Why the run command makes it.** The folder is the backbone's, and its run command makes, records and removes the clones that live there (ADR-066 point 1). Its record of each run tells a killed review's clone from a live one. Reviews run at once and the folder is shared by every project of the person's, so a sweep by any other test could remove a clone a live review uses. It is the third maker of a clone for an agent's run, after the confined form and the drift command, so the run command takes it rather than a third copy ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)).

**Why the seat's snapshot, not the model at the clone's commit.** The model at the default branch's head may allow what has merged but nobody realized. A bound read from it would widen the hook from the repository's history, as ADR-095's alternatives reject for a clone made for an unconfined run. The snapshot that binds the seat's clone is what a person realized there. So a reviewer in its clone is held as it was in the seat's checkout, and the native rules come from the settings file the harness keeps from sandboxed writes.

**Why a remote at the code host.** The code host's command line finds the repository through the remote. The brief's way to read a diff the code host will not serve names the base through it, and the default branch resolves through it (COR-054). A remote at the code host that never pushes keeps all three working. The hazard a remote can bring is one at the person's repository, which would let a push write its references.

**Why only in a seat's clone.** Only a seat's working tree must stay on the default branch while the seat goes on working (ADR-073 point 8). Elsewhere the checkout is the one the person chose to review in, often on the change's branch with their environment set up. Clones there would cost a fetch for each reviewer and, on Linux, the agent's reviews, against a hazard that checkout does not carry.

**Why not only tell reviewers never to check out.** The reviewers' runs are unconfined, and may run in a mode that approves calls no rule allows (ADR-066 point 10). An instruction catches only a reviewer that follows it, and a reviewer that does not follow it is the case this record settles.

**Why not refuse the seat's commands while its checkout is off the default branch.**
- The seat's harness session loads its settings, instructions, skills and agents' definitions from the working tree, and a command's refusal reaches none of them.
- A refusal stops every command of the seat while any review runs, which undoes running at once.
- It never puts the tree back.
- The refusing command loads its code from the checkout it guards.

**Why not a linked worktree of the seat's clone.** It shares the seat's git folder: its configuration, its hooks and its references. Git run there would run the seat's hooks, and could move references the seat uses. The runner's records reject it for a drift command's run and for a builder on the same grounds (ADR-066's Rationale, "Why a clone with a git folder of its own"; ADR-073's alternative, "A linked worktree for the builder").

**What it costs.**
- **A clone for each reviewer:** a fetch from the code host and one checkout's files, for as long as the reviewer runs.
- **The harness's own state.** The harness keeps state in the person's home for each folder it runs in, so each clone leaves some.
- **No prepared environment.** A reviewer that runs the change's tests prepares what they need in its clone.
- **Working files.** A reviewer's working files go with its clone. The verdict and the reviewer's last message are what the review command keeps.
- **Linux.** In a seat's clone on Linux, an agent's review is refused, as its build is, until [project-kit#3427](https://github.com/aleskalfas/project-kit/issues/3427) places the run's folders there. A review the person starts at their own terminal runs.
- **An uncommitted reviewer.** A reviewer the project keeps only in an uncommitted copy is refused.

### Alternatives considered

- **Reviewers never check out, by their instructions alone.** Rejected: an unconfined run is bound by nothing an instruction says.
- **The seat's commands refuse while its checkout is off the default branch.** Rejected: it reaches none of what the seat's session loads, and stops the seat while any review runs.
- **One clone for each review, shared by its reviewers.** Rejected: one reviewer's checkout would move it under the others.
- **A clone at the change's head.** Rejected: every command a reviewer runs there loads the change's unreviewed code.
- **A linked worktree of the seat's clone.** Rejected: it shares the seat's hooks, configuration and references.
- **A clone that borrows the seat's objects.** Rejected: a sandboxed command of the seat's could choose what the clone checks out.
- **A clone in the per-user temp folder.** Rejected: a sandboxed command writes there by default.
- **The review command makes and sweeps the clones itself.** Rejected: it would make clones in the backbone's folder with no record that tells a live one from a left one.
- **The bound and the rules read at the clone's commit.** Rejected: they would widen the hook from the repository's history, with no person shown the widening.
- **A clone with no remote, as a drift command's.** Rejected: the code host's command line, the brief's diff of a large change and the default branch's resolution each need one.
- **A clone for each reviewer in every checkout, not only a seat's.** Not taken: it costs every project, for a hazard only a seat's clone carries.
- **Confine the reviewers' runs now.** Not taken: it needs rules for what a reviewer may read and run, and a mode that cannot bypass them, a design ADR-066 point 10 leaves open.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md) point 5):
  - **Overturned in part.** ADR-066 gains this line at the top of its body, before its Summary, and its words stay as they stood under it:

    > **Partially superseded by [ADR-102](ADR-102-reviews-in-own-clone.md).** In a seat's clone, each reviewer works in a clone of its own, which the backbone's run command makes from the code host at the default branch's head, and the runner holds that run to the snapshot that binds the seat's clone. Overturned, so far as they reach a review in a seat's clone: point 9's "That folder is the person's checkout for a review", point 10's "**The review command's runs** work in the person's checkout.", and point 11's "A reviewer runs in the person's checkout, and may write there." Refined in place: points 1, 2, 9, 10 and 11. The rest stands.

  - **Refined in place,** each edit ending "(refinement per [ADR-102](ADR-102-reviews-in-own-clone.md))":
    - **ADR-066 point 1:**
      - what the backbone's run command does gains: "it makes, records and removes a reviewer's clone, and the folder that holds its run's rules, removing a clone a killed review left only once the process its record names has ended";
      - "What stays with the caller," after "Where that folder is a clone, the caller makes it (point 10).", gains: "For a run in a reviewer's clone, the run command makes the folder, and the caller names the commit, the remote and the references it fetches."
    - **ADR-066 point 2:**
      - what the caller passes gains, after the bullet for an unconfined run: "for an unconfined run in a reviewer's clone, in place of the folder it runs in, the commit, the remote and the references the clone fetches, and the seat's clone whose snapshot and settings file give the run's rules";
      - the list of refusals before a run starts gains: "for a run in a reviewer's clone, the clone or the folder for its rules cannot be made, the pull request's head does not resolve to the head its caller names, the commit holds anything at the workspace's path, the snapshot that binds the seat's clone cannot be used, or the agent's name is one no place ships and the commit deploys no copy of it".
    - **ADR-066 point 9,** after "such as the person's checkout for a review.", gains: "In a reviewer's clone, the runner also registers the hook naming a copy of the snapshot that binds the seat's clone, which the hook judges by beside the clone's own registration."
    - **ADR-066 point 10:**
      - its list's first item, "works in the folder its caller names, under the person's and the project's settings there", gains: ", or, in a reviewer's clone, in the clone the run command makes";
      - its list of what each unconfined run gets gains: "in a reviewer's clone, is also passed, as its settings, the allow, ask and deny rules of the seat's clone's settings file and the permission hook's registration naming that clone's snapshot, and nothing else";
      - its sentence "The run command makes a clone, names its folders in the brief, and copies a run's files, only for a confined run (point 7)." gains "It also makes and removes a reviewer's clone."
    - **ADR-066 point 11,** after "point 10 stands as it decides until a record applies that rule to it.", gains: "A reviewer's clone lies where ADR-102 puts it, out of the default reach of every other session's sandboxed commands. What its run loads from it, which its own shell writes, stays as point 10 decides."
    - **ADR-095 point 2, "Its scope,"** gains: "A reviewer's run in its own clone also runs the copy's hook, which its runner registers naming the snapshot it copied."
    - **ADR-095 point 3, "A bound a runner names,"** gains: "A reviewer's runner names so a copy of the snapshot that binds the seat's clone."
    - **ADR-100 point 1, "The seat's checkout stays as it is":** its last sentence reads "No reviewer works in it."
    - **ADR-100 point 10, "Reviews of several changes at once,"** reads: "In a seat's clone, each reviewer works in a clone of its own (ADR-102), so none writes under another or under the seat's own work. In a clone with no seat, reviews of several changes at once run their reviewers unconfined in its checkout (ADR-066 point 10), and a reviewer that writes there writes under the other reviews, until a record confines the reviewers' runs (ADR-073 point 10)."
    - **ADR-100 point 10, "The seat's checkout beside reviewers,"** reads: "**The seat's checkout beside reviewers.** No reviewer works in it (ADR-102)."
    - **ADR-100 point 10, "The run's folders on Linux,"** gains: "An agent's review in a seat's clone is refused there too, since the run command cannot make the reviewer's clone, and project-kit#3427 takes that folder there as well."
  - **Facts corrected,** edits that change no decision, each citing this record:
    - ADR-073 point 10, the bullet on the reviewers' runs: "**The reviewers' runs** are unconfined, each in a clone of its own outside the seat's clone ([ADR-102](ADR-102-reviews-in-own-clone.md)). A reviewer that checks out the change there and runs its code runs a build's commits outside a sandbox, with the seat's access, until a record confines the reviewers' runs."
    - ADR-100's Context, "Reviewers and fixers": "Reviewers run unconfined in the checkout, and in a seat's clone each in a clone of its own ([ADR-102](ADR-102-reviews-in-own-clone.md))."
    - DEC-067 point 5, its first sentence: "A local reviewer runs unconfined in the checkout the review command runs in, or, in a seat's clone, in a clone of its own ([pkit:ADR-066] point 10, [pkit:ADR-102] point 2)."
- **Acceptance.** A person accepts this record in this change. [project-management:DEC-082-pace-of-subagents]'s build, [project-kit#3462](https://github.com/aleskalfas/project-kit/issues/3462), relies on reviews running beside the seat's own work only once this record's build has landed.
- **The build** is [project-kit#3467](https://github.com/aleskalfas/project-kit/issues/3467). It brings:
  - the backbone's run command making, recording and removing a reviewer's clone;
  - the adapter's runner giving its run the seat's bound and native rules, and the adapter's README on the flag that adds;
  - the review command's call for a clone for each reviewer in a seat's clone, its refusals, and the brief's contract;
  - the adapter's enforcement declaration, the project-management README's account of where reviewers work, the probe of point 6, and the tests.
- **No behaviour changes until the build,** so this record needs no migration. Its build declares changesets for the backbone, the Claude Code adapter and project-management, where the refusal on Linux is a surface change (PRJ-002).
