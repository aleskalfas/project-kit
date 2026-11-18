---
id: ADR-100
title: A seat's clone runs its builds at once, one for each Task, and counts its runs in one register
status: proposed
date: 2026-11-18
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** [project-management:DEC-082-pace-of-subagents] lets the project-manager agent run several subagents at once in a clone, up to a pace, and has the build and review commands hold the agent's calls to that pace from a register of the clone's runs. [ADR-073](ADR-073-builder-runs.md) built the build command for one build at a time in a seat's clone. This record says how a clone runs at a pace:

- **Builds at once, one for each Task.** Each build keeps a state file of its own, keyed by its Task, written under a lock of its own from its first state on. For the builds beside it, a build is refused only where a build of the same Task runs or waits, or, on the agent's call, where no slot is free, and ADR-073's other refusals stand. A session acts on each build it finds as its work allows, and waits on none before other work.
- **Hand-backs take turns.** One hand-back at a time in a clone, each writing only its own reference and its Task's branch.
- **One register, each run entered once.** A build's state file is its entry while it holds a slot. Each other run of a command, and each helper a lead dispatches, has one entry, written by what runs it. An entry counts while a process it names lives, and a run that outlives its helper's entry counts against the pace itself, so no run the register holds counts nowhere. A command reads the register and enters its run under one lock.
- **The agent's call is told by its session.** The adapter declares, as data the backbone reads, how a command finds the harness session whose shell runs it. A command that finds one runs on the agent's call, and any other run is a person's. A harness requirement says what this asks of the harness, so a harness that stops finding the session is reported, not passed.

**Why an ADR.** The register spans the backbone, the adapter and the capability's commands: a declaration of the adapter, a reading the backbone gives, and the commands of project-management that count and start runs. How those parts share one clone's runs is what the project built, an architecture record's question ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md), "Distinct from PRJ"). This record realises DEC-082 as ADR-073 realises [project-management:DEC-063-task-builder].

## Context

**What stands.**

- **One build at a time.** The build command starts a build in a clone of its own, detached, and keeps its state in one file of the seat's clone, which the seat polls with `--wait`. It allows one build at a time in a seat's clone, and refuses a second while one runs (ADR-073 point 5). A session that starts in a clone with a build in that file goes on from it before any other work.
- **The hand-back.** A build's commits come back through a temporary reference of the seat's clone, signed there, and move the Task's branch as a reference (ADR-073 point 8).
- **Reviewers and fixers.** The review and drift commands start each reviewer and each fixer as a process of the backbone's run command ([ADR-066](ADR-066-unattended-agent-runner.md) point 10). Reviewers run unconfined in the seat's checkout.
- **The runtime folder.** The capability keeps a git-ignored folder in each working tree. It holds the clone's identity, with its key ([project-management:DEC-035-instance-ownership] point 1), and the build's state file. How a linked worktree reads its clone's identity is not decided ([project-management:DEC-059-topology-of-seats] point 6).
- **No adapter declares a fact of a live session.** The folder a session is rooted in, its anchor ([ADR-034](ADR-034-foreign-repo-mutation-guard.md)), is read by the backbone's guard against changing another repository under the name of Claude Code's own variable, and the capability keeps a copy of that reading in its own guard. No adapter declares it for the backbone to read.
- **The harness requirements.** The core declares what it requires of the harness, and each adapter answers how far its harness meets it ([COR-047](../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md)), as ADR-066 point 13 and ADR-073's Implications did for the runs they rest on.

**What DEC-082 decides.** One pace for each clone, all its sessions together, counted in slots. Every subagent the agent runs holds a slot while it runs, but a helper while it hands its slot to its own, a build keeps its slot through its checks, and a run a person starts themselves holds none. A register of the clone's runs, read by the build and review commands, holds the agent's calls to the pace, where a command can tell that call from a person's. A lead enters each helper with a share of its slots, and the runs a helper's commands start count within that share. A Task that waits holds no slot. DEC-082 leaves to this record a state file for each build, a `--wait` that names no Task, recovery over each build, how fetches, signing and hand-backs share one clone, the register's form, and the sign that tells the agent's call. DEC-082 rests on [project-management:DEC-081-delegation-between-seats], and both are accepted with this record.

**Terms.** *The agent*, *a subagent*, *the pace*, *a slot* and *the ceiling* are DEC-082's.

- **The clone** is the working tree a command runs in, with the capability's runtime folder there, whether or not that folder holds an identity yet: a clone makes its key only when it first claims ([project-management:DEC-058-state-issues] point 5). **Its runtime folder** is that folder.
- **An entry** is one record of the register (point 5).
- **A session's process** is the process of the harness session whose shell runs a command, as the adapter finds it (point 9).

## Decision

**In a clone, builds run at once, as many as the pace allows on the agent's call, one for each Task, each with a state file of its own, and hand-backs take turns. The clone counts the runs that take its slots in one register: one entry for each run, written by what runs it, a build's state file being its entry while it holds a slot, and each entry counted while a process it names lives. A command reads the register and enters its run under one lock, and tells the agent's call by the harness session whose shell runs it, as the adapter finds it, on a harness requirement this record declares.**

### 1. Builds run at once, one for each Task

- **As many as the pace allows.** On the agent's call, the build command starts a build only where a slot is free (points 5 and 7). A build a person starts themselves takes none (point 9), as DEC-082 point 1 has it. This holds in a seat's clone, and in a clone with no seat, which runs at the ceiling (DEC-082 point 8).
- **One for each Task.** A Task has at most one build that runs or waits, on its question or on its hand-back. A build of a Task whose earlier build runs or waits is refused (exit 1), since `--answer` resumes that build and `--hand-back` finishes it (ADR-073 points 7 and 8).
- **No slot free.** On the agent's call, a build with no slot free is refused too (exit 1), with the pace and the count the command read, and nothing starts.
- **Each build's own.** Each build has its own state file, keyed by its Task, in the runtime folder. It has its own clone, settings folder and progress file, and its own temporary reference for its hand-back, named for its Task. So two builds write nothing in common but the register and, through their hand-backs, the seat's repository (point 4).
- **The seat's checkout stays as it is.** Builds at once leave the seat's working tree clean and on the default branch, as ADR-073 point 8 keeps it. What a reviewer may do to it is point 10's.

### 2. Each build's state has one writer at a time, and each build is recovered once

- **A lock for each build.** A build's state file is written only under a lock of its own, which the operating system releases when its holder ends, however it ends. Its writers:
  - the command that writes the build's first state, the build command or `--answer` for a run it resumes, which takes the lock before it writes;
  - the detached process that command starts, which holds the lock while it lives;
  - `--hand-back`, for its hand-back;
  - a command that recovers the build (ADR-073 point 5).
- **No gap at the start.** The command that writes the first state holds the lock until the detached process it starts holds it too, with no moment between in which neither does, such as by a lock the detached process inherits from it. It names that process in the state before it ends. So a command that reads a build's first state finds its lock held, and never takes a build that is starting for one that is lost.
- **The lock tells the process gone.** A command that reads a state that is not final, and takes its lock, knows that no writer lives. It reads the state again under the lock, and recovers that build as ADR-073 point 5's "Recovery" says. So two commands that find one build at once recover it once.
- **A session goes on from every build.** A session that starts in a clone reads each build's state before it takes other work. It then acts on each as DEC-082 point 4 orders its slots: a finished build as work in flight, a build that waits as its wait asks, and a running build left to run while the session fills its other slots. It waits on no running build before other work.

### 3. `--wait` waits on one Task's build, or on whichever of the clone's ends first

- **With a Task,** it waits on that Task's build, as ADR-073 point 5's "Waiting" says, and exits with that build's code.
- **With no Task,** it waits on every build of the clone that runs when it starts. It returns once one of them ends, naming its Task, with that build's code; where several have ended when it reads, with the code of the first to end, by the times their states name. Where none ends within the time, it exits 8. Where none runs when it starts, it says so and exits 1.
- **Every wait lists the clone's builds,** each with its Task and its state, so a session finds a build that ended while it was not waiting.

### 4. Hand-backs take turns, and each writes only its own references

- **One at a time in a clone.** A hand-back takes a lock of the clone's for its whole span: its check of the build's clone, its fetch, its signing and its move of the Task's branch (ADR-073 point 8). The operating system releases the lock when its holder ends. A hand-back that waits for the lock holds no slot.
- **Its own references.** It fetches into its build's temporary reference, and moves the Task's branch only from the commit the branch held when the hand-back began, so a branch that moved meanwhile is not moved. It writes no file of the repository that git's other commands write too, such as the record of the last fetch.
- **Git's other writers.** The seat's own commands write the same repository while builds run, such as a fetch of the default branch or a push. A hand-back that finds a lock of git's held waits and tries again, within a bound. One that still cannot write moves nothing, and the build waits on its hand-back (exit 9), as one that could not sign does, so `--hand-back` makes it again.
- **Signing in turn.** So a key that asks for its passphrase asks for one hand-back at a time. While its prompt is open, that hand-back holds the lock, and every other hand-back in the clone waits on the person.

### 5. One register: each run that takes a slot is entered once, by what runs it

- **Where it lives.** In the clone's runtime folder, beside its identity where it holds one, and never committed. The register is the entries there, with no list of its own. So whatever reads the clone's identity reads its register.
- **What an entry says:** what it counts, the slots it holds, the processes whose life bounds it (point 6), and, for a run within a helper's share, that helper's entry (point 8).
- **A build's state file is its entry while it holds a slot,** never a second record of the same run. It says whether the run it names started on the agent's call, the first run or one `--answer` resumed, and where it did, it holds one slot while its state is running, its checks included. It holds none while the build waits, on its question or on its hand-back, nor while it hands back or once it has ended. A state file that holds no slot, a person's build's among them, is no entry, though it still counts for the one build each Task may have (point 1).
- **A run of the review command or the drift command** on the agent's call has one entry, which that run writes before its first reviewer or fixer starts, and which names each reviewer's or fixer's process as it starts. It holds as many slots as that run has reviewers or fixers going at once, and lowers that count as its last ones end, never raising it (DEC-082 points 4 and 9).
- **A helper's entry** is written by the command the lead runs before it dispatches the helper, and holds the helper's share whole (point 8). The lead ends it when the helper returns, and the end of its session ends it at the latest (point 6).
- **What counts against the pace:** each entry's slots, but those of a run within a live helper's entry, which count within that helper's share alone. A run whose helper's entry no longer lives counts against the pace itself, for as long as it lives.

### 6. An entry counts only while a process it names lives

- **Its processes.** Each entry names the processes whose life bounds it:
  - for a build, its detached process, and, until that process starts, the command that wrote the build's first state, which names the detached process before it ends (point 2);
  - for a review or a drift run, the command's own process and each reviewer's or fixer's it starts;
  - for a helper, the session's process (point 9).
- **Named so it is not mistaken.** A process is named by its id and the time it started, so an id the system gives another process later is not taken for it.
- **An entry lives while any process it names lives.** A review's or a drift run's entry whose command has ended, such as one that was killed, holds one slot for each of its reviewers or fixers that still lives.
- **An ended process counts for nothing,** however it ended. The next command that counts removes an entry none of whose processes lives, but for a build's state file, which stays for its recovery (point 2).
- **No lapse.** No time limit ends an entry, since a run may outlast any bound.

### 7. A command reads the register and enters its run under one lock

- **One lock of the clone's,** which the operating system releases when its holder ends, so a holder that dies holds nothing up.
- **What it covers.** On the agent's call, the build command, the review command and the command that enters a helper (point 8) each take the lock, count the slots the live entries hold, and take what they may: no more than the pace leaves free, nor than the cap the agent passes (DEC-082 points 1 and 4). Each writes its entry, a build's under that build's lock too (point 2), and lets the lock go, and its run starts only once its entry is written. Where it may take no slot, it starts nothing and says so. So two of these commands started together cannot both pass the pace.
- **Nothing slow under it.** The command reads the pace before it takes the lock, in the read that confirms its seat (DEC-082 point 7). While it holds the lock, it reads no tracker and waits on no run. A pace that changes in between binds from the next start, as a lowered pace does (DEC-082 point 9).
- **The drift command** enters its fixers under the same lock, within the cap passed, and refuses none past the pace (DEC-082 point 7). So only the cap the agent passes it holds a drift run to the pace.
- **A register that cannot be read** lets nothing start on the agent's call, and the command says why.

### 8. A helper's share bounds what its commands start

- **Entered within the free slots.** The command that enters a helper takes the lock, and refuses a share past the slots free. It prints the entry's name, which the lead puts in the helper's brief beside the share (DEC-082 point 2).
- **Runs within the share.** The helper passes its entry to each command it calls. A command given a live helper's entry starts at most the share less the runs already running within it, writes its own entry within the share, and counts nothing against the pace. So the helper's own slot passes to its runs while they run. A run that outlives the helper's entry counts against the pace from then on (point 5).
- **No entry passed, or one no longer live:** the command counts against the pace, where the share is already held, and says so. A helper that leaves its entry off, or a lead that ended it early, costs slots and passes no pace.

### 9. A command tells the agent's call by the session whose shell runs it

- **The adapter finds the session.** The project's adapter declares how a command finds the harness session whose shell runs it, and that session's process. The declaration is data the backbone reads, as it reads an adapter's other declarations, running none of the adapter's code (the adapters README, "What an adapter declares as data"), and its fields are the build's. A command of the capability learns it from the backbone, so the command names no harness (ADR-066).
- **The first fact of a live session an adapter declares.** No adapter declares one today (the Context). A session's anchor stays where it is. The same declaration could later carry the anchor, or the session's own name that DEC-081's measurement 2 asks after, and this record decides neither.
- **The agent's call.** A command that finds a session runs on the agent's call. Any other run is a person's: at their own terminal, or in a script or pipeline of theirs. So a person's run takes no slot, whatever its streams, and an agent's call is held whether or not its shell gives it a terminal.
- **It errs toward holding.** DEC-082's Terms make the agent the project-manager agent, or the definition a seat names, running the pm skill's procedures in a session. The sign finds every session, so it also holds a run that another agent's session in the clone starts, and a person's command through a session's shell (below). A run it so misreads costs the slot it takes, and never passes the pace.
- **The same process bounds a helper's entry** (point 6), so that entry ends with its session.
- **No session found, no hold.** Where no adapter declares how to find a command's session, no command can tell the agent's call. None holds a caller or enters a run, no helper is entered, and the agent holds itself to the pace, the gap DEC-082 point 7 names. Where a declared adapter's harness stops finding the session, the same follows, and the harness requirement (point 12) is how it is told.
- **A guard, not a boundary.** A command the person runs through the session's own shell counts as the agent's, and an agent can start a command outside its session's shell. Like the clash guard on a claim (DEC-035 point 6), the sign catches the mistakes of an agent that follows the procedure, and stops no agent that means to pass as a person.

### 10. What stays open

Each item says what holds the intent and what is left ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) point 3).

- **A linked worktree.** Its runtime folder is its own, so a session in a linked worktree of the clone counts in a register of its own, as it reads an identity of its own, until a record decides how a linked worktree reads its clone's (DEC-059 point 6). Sessions in two working trees of one clone may then each run the pace.
- **A helper the lead does not end.** Its entry holds its share until its session ends. That slows the clone, and starts nothing past the pace.
- **Subagents started through the harness's tools,** other than helpers, are counted by the agent alone, and no other session sees them (DEC-082 point 7).
- **Reviews of several changes at once** run their reviewers unconfined in the seat's checkout (ADR-066 point 10). A reviewer that writes there writes under the other reviews and under the seat's own work, until a record confines the reviewers' runs (ADR-073 point 10).
- **The seat's checkout beside reviewers.** A reviewer that checks out its change in the seat's checkout, a case ADR-073 point 10 allows for, moves that working tree off the default branch while the seat goes on working. The agent's builds are then refused (exit 1), and the seat's own commands run from a build's unreviewed commits. This record does not settle it. A record settles it before the build relies on reviews running beside the seat's own work: that reviewers never check out in the seat's checkout, or that the agent's commands refuse while it is off the default branch.
- **What runs at once costs the machine.** Each build makes its own clone, caches and sandbox, and reaches its build's hosts, so the pace bounds disk, memory and network use only by bounding the runs.
- **A command outside its session's shell** passes as a person's run (point 9).

### 11. The probe

Before the build rests anything on them, a probe confirms on each platform the adapter supports:

- The adapter's declaration finds the session from a command the session's shell runs and from one a helper's shell runs, and finds none for a command a person runs at their own terminal. The session's process it names ends when the session ends.
- A process's id with its start time tells a live process from one that ended, and from another that took its id.
- A lock the operating system holds for a process in the runtime folder is released when that process is killed.
- A build's lock passes from the command that writes its first state to the detached process it starts with no gap: a `--wait` that reads that first state before the detached process has started finds the lock held, and recovers nothing.
- Two build commands started together on the agent's call, at a pace of one, start one build.
- A review command killed while its reviewers run leaves an entry that holds one slot for each reviewer still running.
- Two hand-backs started together take turns, and a hand-back beside the seat's own fetch and push moves only its own references.

A fact the probe disproves refines or supersedes this record.

### 12. The harness requirement

The commands hold the agent's calls only where the adapter's declaration finds the session (point 9). Where a declared adapter's harness stops finding it, every one of the agent's calls passes as a person's: no pace is held, no helper is entered, and nothing in the commands says so. So the pace rests on a property of the harness ([COR-047](../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md)), which this record words in terms any harness could meet:

> A command that a session's own shell runs, or the shell of a helper the session starts, can tell which session it runs within, and can name that session's process, which ends when the session ends.

- **Observation point:** inside a session, where a command its shell runs reads what the declaration finds.
- **Evidence:** DEC-082 point 7, a design dependency (COR-047 point 9). It is no transient defect, so it names no retirement condition.
- **What depends on it:** the register's hold on the agent's calls, each helper's entry, and the end of a helper's entry with its session (points 5 to 9).
- **Declared with DEC-082's build.** That build adds it to the requirement set. Each adapter answers it in its support declaration (the adapters README, "Harness requirements"). The Claude Code adapter's answer holds for the versions the probe (point 11) tested, and only an author who tests a newer version widens it (COR-047 point 2).

### What this overturns in ADR-073, and what stands

Overturned:

- in point 5, "One build at a time in a seat's clone. A build started while one runs is refused", which point 1 replaces
- in point 5's "Recovery", "before any other work: it waits on a running one", which point 2 replaces
- in point 5's "Waiting", "exits with the state's code", for a `--wait` that names no Task where no build runs when it starts, which exits 1 (point 3)
- in point 6's exit 1, "a build already running", narrowed to a build of the same Task that runs or waits, beside a build with no slot free on the agent's call (point 1)

Refined in place, each completed with a case this record adds:

- point 6's exit 1, which gains a `--wait` that names no Task where no build runs when it starts (point 3)
- point 6's exit 9, which gains a hand-back that still cannot write once git's lock has been retried within its bound (point 4)
- point 8's bullet on a signature that fails, beside which such a hand-back moves nothing, and its build waits on its hand-back (exit 9), as one that could not sign does (point 4)

Standing, each read for every build: point 5's state file, its waiting for a `--wait` that names a Task, and its recovery, each a build's own (points 1 to 3); the Summary's file the seat polls; exit 8, which for a `--wait` with no Task means that none of the builds it waited on ended (point 3); and point 8's hand-back, which takes turns (point 4). The rest of ADR-073 stands.

## Rationale

**Why builds at once, and one for each Task.** DEC-082 has a worker keep several Tasks in flight and run as many subagents as its pace allows, builders among them. One build at a time in a clone would hold every worker to one builder, whatever its pace. Each build already runs in a clone of its own, under its own rules, and comes back only through its hand-back, so builds of different Tasks share nothing but the repository they come back to. Two builds of one Task would race for its branch, its claim and its question, so a Task keeps one build. A build that waits keeps its Task until `--answer` or `--hand-back` ends the wait, since the Task's record on the tracker shows the wait, and its claim does not lapse while it does (ADR-073 point 5, "The claim").

**Why a build's state file is its entry.** A build already keeps its state in a file its process writes, which names the process and whether the build runs. A second record of the same run would be written at another moment, and could show a build running where its state shows it ended. One record of each run cannot disagree with itself. A state file that holds no slot is no entry, so a person's build, or one that waits, is in no register, and the Task's one build is still found by its state file.

**Why the first writer holds the build's lock until the detached process does.** The command that starts a build writes its first state before the process that runs it exists. A lock taken only by that process would leave a moment in which a state that is not final has no holder, and another session's command would recover a build that is only starting. A lock held from the first write, and passed with no gap, closes that moment.

**Why an entry lives with its processes, and lapses at no time.** The register counts runs, and each run is bounded by a process. The operating system knows when a process ends, whether it finished, failed or was killed, so an entry bounded by its processes outlives neither its runs nor, for a helper, its session. A run can outlive what entered it, a reviewer its killed command, or a build its helper's session, so an entry names each run's process, and a run whose helper's entry has ended counts against the pace itself. A time limit would either outlast a dead run, whose slot nobody then uses, or end before a long one, so that the next command starts past the pace.

**Why one lock, and nothing slow under it.** Two commands that each count the register and then enter a run can both find the last slot free. A lock over the count and the entry closes that, and a lock the operating system releases cannot be left held by a run that died. A read of the tracker under the lock would hold every other command in the clone on the network. So the pace is read before, and a pace that changes in between is read one start late, as DEC-082 point 9 already allows.

**Why hand-backs take turns.** A hand-back's check, fetch, signing and move are seconds of work on the one repository every build comes back to, beside the seat's own commands. Taking turns keeps each hand-back's check and move together, and a key that asks for its passphrase asks once at a time, at the cost of a hand-back that waits seconds for another, or, while a passphrase prompt is open, waits on the person who answers it. A hand-back that writes only its own references, from the commit it expects, stays out of the way of git's other writers. One that still cannot write waits on its hand-back, as one that could not sign does, so nothing is lost but time.

**Why the session, and not the terminal.** DEC-082 holds the agent's calls, and a person's own runs take no slot. The test of a terminal answers another question, whether a person can answer here ([project-management:DEC-069-when-fixers-start]'s Terms). It would hold a person's run in a script or a pipe as the agent's, and pass an agent's call where the harness's shell gives a terminal or the agent fakes one (ADR-066 point 11). What makes a call the agent's is the session whose shell runs it, so the commands read that. The register needs the session's process in any case, so that a helper's entry ends with its session, and one declaration of the adapter gives both.

**Why the declaration is data.** Every build and review command on the agent's call reads it, so reading it runs none of the adapter's code, as the backbone reads an adapter's other declarations. A registered command of the adapter, as its runner is, would put another process before every start.

**Why a harness requirement.** A declared adapter whose harness release stops finding the session would pass every call as a person's, with no pace held, no helper entered and nothing to say so: a degraded result shaped like a correct one, which COR-047 exists to report. An adapter with no declaration leaves the gap point 9 names, and the requirement resolves indeterminate there, never satisfied (COR-047 point 3).

**Why a helper's share is held whole.** The lead hands each helper a share of its free slots, and the helper may fill it at any moment, with no command of the lead's in between. Holding the share whole keeps the lead's other runs and the other helpers out of it, so a helper's command never finds its share taken. A helper's runs count within its share and not against the pace again, so the share is counted once.

### Alternatives considered

- **A register file of its own, beside the builds' state files.** Rejected, as "Why a build's state file is its entry" says.
- **Entries that lapse after a time, renewed while their runs run.** Rejected, as "Why an entry lives with its processes" says.
- **The test of a terminal as the sign of a person's run.** Not taken, as "Why the session, and not the terminal" says.
- **A flag the agent passes on each call, marking it as the agent's.** Rejected: a call that left it off would pass as a person's, which leaves the pace to the agent's own count, as DEC-082's "Why the commands hold the agent's calls" rejects.
- **Hand-backs at once, each to its own references.** Not taken: git's own locks would allow it, but two hand-backs would sign at once, and more writers would meet on the seat's repository at once, for a saving of seconds.
- **The register in the git folder that every working tree of the clone shares.** Not taken: it would decide how a linked worktree shares its clone's state, which DEC-059 point 6 leaves open, while the clone's identity sits in the runtime folder of its working tree.
- **A state file for each build rather than for each Task,** so that a Task could have several. Rejected, as "Why builds at once, and one for each Task" says.
- **A new build that replaces a Task's waiting build.** Rejected: the Task's record would still show its question or its hand-back waiting, and its claim would not lapse.
- **The harness's event at a subagent's end, ending a helper's entry.** Named, not decided: where an adapter declares such an event, it would end the entry with the helper rather than with the lead's call. A later record may decide it.
- **A command that ends its reviewers or fixers when it ends, in place of naming their processes.** Not taken: a command killed outright ends nothing, so its runs would count nowhere.
- **A build's lock taken first by its detached process.** Rejected, as "Why the first writer holds the build's lock until the detached process does" says.
- **No harness requirement, the gap point 9 names standing for every harness.** Rejected, as "Why a harness requirement" says.
- **The session's anchor moved onto the new declaration in this record.** Not taken: no record needs the anchor declared, and moving it would change the guard against changing another repository for a reason this record does not have.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md) point 5):
  - **Overturned in part.** ADR-073 gains this line at the top of its body, before its Summary, and its words stay as they stood under it:

    > **Partially superseded by [ADR-100](ADR-100-runs-in-seat-clone.md).** A clone runs several builds at once, as many as its pace allows on the agent's call ([project-management:DEC-082-pace-of-subagents]), one for each Task, each with a state file of its own, keyed by its Task. A session acts on each build it finds as its work allows, and hand-backs in one clone take turns. Overturned: point 5's "One build at a time in a seat's clone. A build started while one runs is refused"; in point 5's "Recovery", "before any other work: it waits on a running one"; in point 5's "Waiting", "exits with the state's code", for a `--wait` that names no Task where no build runs when it starts, which exits 1; and in point 6's exit 1, "a build already running", which refuses only a build of the same Task that runs or waits, and, on the agent's call, a build with no slot free. Point 5's state file, its waiting for a `--wait` that names a Task, and its recovery are each build's own, as ADR-100 points 1 to 3 say. ADR-100's "What this overturns in ADR-073, and what stands" lists each passage. The rest stands.

  - **Refined in place,** in ADR-073, each completed with a forward refinement pointer to this record:
    - point 6's exit 1 row, which gains, among its refusals, a `--wait` that names no Task where no build runs when it starts (point 3)
    - point 6's exit 9 row, which gains a hand-back that still cannot write once git's lock has been retried within its bound (point 4)
    - point 8's bullet on a signature that fails, completed by a sentence: a hand-back that still cannot write past git's lock moves nothing in the same way, and its build waits on its hand-back (exit 9), so `--hand-back` makes it again (point 4)
  - **An edit that changes no decision:** none.
- **Acceptance.** This record rests on DEC-082, and through it on DEC-081, both proposed in this change. A person accepts it here, no earlier than DEC-082, and the change lands only once it is accepted. The sign-off on DEC-082 authorises the overturn of ADR-073 in part. Accepting this record accepts its text, the line above and the refinements in place it names. Refusing DEC-082 leaves this record nothing to realise, so it is closed with it. Refusing DEC-081 leaves this record waiting on DEC-082 as it is then revised.
- **Before the build command.** It lands before #2287 builds the build command, which is then built for builds at once (DEC-082's Implications).
- **DEC-082's build** brings:
  - a state file for each build, keyed by its Task, with its lock, and `--wait` with no Task
  - the register, its entries, its lock and its count, and the build, review and drift commands entering their runs
  - the command that enters a helper, and the option by which a helper passes its entry to each command it calls, each named by the build
  - the hand-back's turns
  - the register's entries in the capability's runtime ignore list ([ADR-009](ADR-009-git-footprint-visibility.md) point 7)
  - the harness requirement (point 12) in the core's requirement set, the Claude Code adapter's answer to it in its support declaration, bounded to the versions the probe tested, and the account of each in the adapters README's "Harness requirements" and the Claude Code adapter's README's "Harness support". Declaring it edits no accepted record.
- **The adapters' contract** gains the declaration of how a command finds the session whose shell runs it, with that session's process, as data the backbone reads (point 9), and the backbone gains a reading of it for a capability's command. It is the first fact of a live session an adapter declares. The Claude Code adapter declares it once the probe (point 11) passes.
- **Changesets.** This record moves nothing, so it needs none of its own. The builds declare their components' changes (PRJ-002): project-management, the backbone and the Claude Code adapter.
- **No migration.** Nothing it changes is built yet.
- **Stands on:** ADR-073, ADR-071, ADR-066, ADR-034 and ADR-009; DEC-082, DEC-081, DEC-063, DEC-059, DEC-058, DEC-069 and DEC-035 of project-management; COR-028, COR-047 and COR-066.
