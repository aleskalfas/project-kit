---
id: DEC-082
title: The project-manager runs as many subagents at once as its pace allows, under a committed ceiling, and keeps them busy
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the project-manager agent may run several agents of its own at once: a builder for each Task, the reviewers of each change, the fixers after a merge and a lead's helpers. One setting in the capability's committed configuration gives the **ceiling** on how many run at once in one clone, all its sessions together. `off` runs one at a time, a number runs at most that many, and `max` runs as many as the work calls for, bounded only by the machine and the account's usage limits. Where the setting is absent it is 4. Within its pace the agent keeps busy without being told. Whenever one of its runs ends, it first starts what its work in flight waits for, such as a review, then a Task its directing seat named, and then the next Task that nothing blocks, nearest the work just done. The seat that directs a worker may set the worker's pace below the ceiling, or back up to it, on the worker's state issue. A person may set any seat's pace, which replaces what a directing seat set before it, and which a directing seat then only lowers. The build and review commands hold the agent's calls to the pace, and a run a person starts at a terminal takes no slot. A lowered pace stops nothing that runs, and the agent tells the person once in each session at what pace it runs.

## Context

**What stands.**

- **A builder for each Task.** In a project with a topology of seats, a fresh builder builds each of a worker's Tasks, started by the capability's build command in a sandboxed clone of its own ([project-management:DEC-063-task-builder] points 1 and 4). The seat's own working tree stays on the default branch, yet the architecture of the build command allows one build at a time in a seat's clone, and refuses a second while one runs ([pkit:ADR-073] point 5).
- **Reviewers at once.** The review command starts the reviewers of a change together, the whole set by default, and takes a cap on how many run at once.
- **Fixers after a merge.** The agent's run after a merge starts the fixers through the drift command where their confined form holds or the project's switch is on, with a cap of their own ([project-management:DEC-069-when-fixers-start] point 1).
- **No harness counts these runs.** The build command starts its run detached, as a process of its own (ADR-073 point 5), and the review and drift commands start each reviewer and each fixer through the backbone's run command, each a process of its own ([pkit:ADR-066] point 10). The session's harness started none of them, so it neither counts nor limits them.
- **One Task at a time, in practice.** The worker's loop in the pm skill takes a new Task only once nothing is in flight. A build that stops on a question ends the loop, and DEC-063 names "a seat taking other work while a question waits" among what it does not build.
- **A session with no seat** dispatches builders and reviewers as the person directs it, several at once where the person asks, as a session that coordinates a batch of Tasks in a project with no topology does.
- **The directing seat.** [project-management:DEC-081-delegation-between-seats], accepted with this record, has the topology name a worker's directing seat, and lets that seat's session message the worker.
- **Nothing bounds the count.** No record says how many of these runs the agent may have going at once, or that it starts the next without being asked.

**What the maintainer decided.** On 17 November the maintainer decided how much work the agent runs at once (#3394):

- One setting, in the project's committed configuration of this capability, gives the number of subagents the agent runs at once. `off` runs one at a time, a number at most that many, and `max` as many as the work allows. Builders and reviewers count alike.
- The agent keeps its slots full, and does not wait to be told to work in parallel. Whenever a slot frees, it takes the next Task that nothing blocks. It looks first in what the current work belongs to, its Feature, its EPIC and its Milestone, and only then in the rest of its pool. A Task is not blocked where no open dependency stands before it, it shares no file with a Task in flight, and its seat may take it.
- A directing seat sets the pace of a seat it directs, within the ceiling the committed configuration gives. It writes the value in that seat's state issue, where the worker reads it at each step of its loop. A message through the harness only points the worker to the change. A worker with no pace set takes the configured value.
- The person keeps the ceiling. The committed value is the most any seat runs, and a lead may lower a worker's pace, or raise it back up to the ceiling, never past it.

This record holds those decisions. It settles what they leave open: the value where the key is absent, what bounds `max`, which runs count and in which unit, whose calls the commands hold and how, how a lead's helpers share its slots, a clone that holds no seat, how a review and a named Task wait for a slot, whose setting outranks whose, what a lowered pace does to a run already going, and how the agent tells the person its pace.

**Terms.**

- **The agent** is the agent that runs the pm skill's procedures in a session: the project-manager agent, or another agent definition a seat names in its place ([project-management:DEC-059-topology-of-seats] point 8).
- **A subagent** is an agent run that a session starts or resumes for the agent's work: through the harness's tools for starting agents or for messaging, or through a command of this capability, such as the build command's builder, each reviewer the review command starts and each fixer the drift command starts. A helper's own subagents are the agent's too. The session's own agent is none, and nor is a run a person starts at a terminal, which takes no slot (point 1).
- **The pace** is the most subagents the agent runs at once in one clone, all its sessions together. **A slot** is room for one subagent within the pace, and a slot is free while fewer subagents run than the pace allows.
- **The ceiling** is the pace the configuration gives, the most any clone runs.
- **Work in flight** is each Task the agent has started and not yet seen merged or closed: one it is building, or one waiting on its checks, its review, a fix round, a merge of the base or a question.

## Decision

**One setting of the capability's committed configuration, read from the default branch, gives the ceiling on how many subagents the agent runs at once in a clone, all its sessions together: `off`, a number or `max`, and 4 where it is absent. Every subagent the agent runs takes a slot, and a run a person starts at a terminal takes none. Within its pace, the agent starts first what its work in flight waits for, then a Task a directive named, then the next Task that nothing blocks, nearest the work just done. A worker's directing seat may set the worker's pace within the ceiling, on the worker's state issue, and a person may set any seat's, which replaces what a directing seat set before it and which a directing seat then only lowers. The build and review commands hold the agent's calls to the pace. A lowered pace stops nothing that runs, and the agent tells the person its pace once in each session.**

### 1. One committed setting gives the ceiling, and 4 where it is absent

- **Where it lives.** It is one key of the capability's configuration, beside its other settings, and not of the topology, since it binds a clone that holds no seat and a project with no topology too. The key's name is the build's.
- **Read from the default branch,** at the commit the backbone resolves it to, as the topology is read (DEC-059 point 1). So a change to the ceiling binds once a merge lands it, and no branch the agent works on raises its own pace.
- **Its values:**
  - `off` runs one subagent at a time, and `1` means the same. A worker at `off` still takes a new Task while earlier ones wait on their checks, a person or a question, since a Task that waits holds no slot (point 2).
  - A whole number of at least one runs at most that many at once.
  - `max` runs as many as the work calls for: as many runs as there are ready Tasks that share no file, with each review's reviewers beside them, bounded only by the machine and the account's usage limits (point 3).
- **Absent, it is 4.** A project that has not chosen runs at most four subagents at once in a clone: a review the agent starts runs no more than four of its reviewers together, a coordinator no more than four builders, and a worker fills no more than four slots.
- **A value that does not read,** such as zero or a word it does not know, runs one subagent at a time, and the agent says why. The configuration's schema refuses such a value on the change that writes it.
- **A person's own run.** A run a person starts at a terminal, of a command that starts subagents, keeps the command's own cap and its default, takes no slot, and is entered in no register (point 7). The ceiling binds the agent's calls alone: the agent passes each such command its free slots as the cap, and that cap wins over the command's other settings.

### 2. Every subagent takes a slot, whatever starts it

Each subagent takes one slot for as long as it runs:

- a builder, of a Task, of a fix round, of a merge of the base, or of a build resumed once its question is answered
- each reviewer of a change, so a review takes one slot for each of its reviewers that runs at once
- a reviewer of a plan, such as the critic that batch planning calls
- each fixer the agent's run starts after a merge
- a lead's helper while none of its own subagents runs, and each subagent the helper starts (below)
- a subagent the agent resumes by messaging (DEC-081 point 2)

The pace is the clone's, all its sessions together, not each session's or each agent's. A clone holds at most one seat, and each session in it takes that seat up (DEC-059 point 4), so its sessions share the seat's slots.

A lead's helper acts as the lead's instance (DEC-059 point 6), so it and the subagents it starts share the lead's slots:

- **A share for each helper.** The lead hands each helper it dispatches a share of its free slots, in the helper's brief, and enters the helper in the clone's register with that share, through a command of this capability (point 7).
- **The helper keeps to its share.** It passes what its share leaves free as each command's cap, and dispatches nothing past it.
- **A helper hands its slot on.** A helper holds one slot of its share while it works, and hands that slot to its own subagents while they run. So a helper and its subagents take at least one slot and never more than its share, and a helper whose share is one, as at `off`, still has its Task reviewed, one reviewer at a time.

A Task that waits on its checks, on its verdicts being posted, on a person or on a question runs no subagent, so it holds no slot. A Task a person directs to be built in the seat's own session, where no builder can start (DEC-063 point 1), runs no subagent either. It is built there alone, and the seat starts no other build until it ends.

### 3. The work bounds every pace, and only the machine and the account bound `max`

- **A pace is a ceiling, never a demand.** With nothing waiting and no Task that nothing blocks, slots stay free.
- **What bounds `max`.** No harness counts the runs the build, review and drift commands start (the Context). So `max` runs as many as the work calls for: as many runs as there are ready Tasks that share no file, with each review's reviewers beside them, bounded only by the machine and the account's usage limits. A project that sets it takes that cost on in a reviewed change (point 1).
- **The harness's own limit.** Where the harness limits how many subagents it starts itself, through its tools for starting agents, the agent starts none past that limit there, and a pace above it is no error.
- **No other limit.** This capability sets no number of its own beyond the ceiling and the work.

### 4. Work in flight comes first, then a named Task, then new work

Whenever a slot frees, and at the start of each round of its loop, the agent fills its free slots in this order, without being told:

1. **What its work in flight waits for:** a review whose checks have passed (DEC-063 point 8), a fix round on a verdict that asks for changes, a build that merges the base into a Task's branch, and a build resumed once its question is answered. After a merge, so too each fixer its run starts (DEC-069 point 1), which ends the merged Task's work. Each starts in the order it came to wait.
2. **Then a Task a directive named** (DEC-081 point 6), one for each slot still free, in the order the directives came.
3. **Then a reviewer of a plan** the agent has drafted, such as the critic that batch planning calls, since the plan's Tasks wait on it.
4. **Then new Tasks,** each the next that nothing blocks (point 5), one for each slot still free.

A lead's helper takes the place of the work it is dispatched for, and its share comes from the slots that work would take: a helper for work in flight among the first, and a helper for a new Task among the last.

So no new build takes a slot that a waiting review could use. The first review to wait starts once one running subagent ends, and each after it once one more ends.

- **A review takes the slots free when it starts,** at least one and no more than it has reviewers. It runs its other reviewers in turn within them.
- **A command that starts subagents,** such as the review command or the drift command, is passed the slots free as its cap on how many run at once.

### 5. A new Task is the next that nothing blocks, nearest the work just done

- **Nothing blocks a Task** that the one reckoning of ready work holds ready for the agent ([project-management:DEC-025-parallelization-primitive]):
  - No open issue stands among its dependencies ([project-management:DEC-005-linking-and-containment]).
  - It shares no file with a Task in flight. Of two Tasks that share a file, the later names the earlier among its dependencies, and starts only once the earlier has merged ([project-management:DEC-066-fold-tasks-that-share-a-file] point 1). So the first condition holds it back, and the reckoning reads nothing more from the code.
  - Its seat may take it, by the seat's scope (DEC-059 point 7), and by its pools where the topology declares them ([project-management:DEC-061-pools-of-workers] point 5).
- **Nearest first.** The agent takes first the Tasks that share the Feature of the Task whose work freed the slot, then those that share its EPIC, then those in its Milestone, each where it has one, and then the rest of what it may take. Within each, the Tasks rank by priority, the highest first. Where no Task's work freed the slot, as at the start of a session, priority alone orders them. So a Task of higher priority elsewhere waits until the nearer Tasks are taken.
- **A Task that waits on a question** keeps its claim and holds no slot (DEC-063 point 6). The agent tells the person, and goes on with its other work within its pace. A later session's first step finds the open question before it takes other work.

### 6. A worker's directing seat may set its pace, and a person may set any seat's

- **The directing seat** of a worker is the seat the topology names on the worker's seat to direct it (DEC-081 point 3).
- **Who sets a seat's pace:**
  - The clone that holds the worker's directing seat. The command that writes the pace confirms that seat first, as every command that acts as an instance does (DEC-059 point 6).
  - A person, for any seat, at a terminal or through the command run with its consent flag on the person's word, as a person authorises a release by force (DEC-059 point 5). An agent never gives that word for itself.
- **What it sets:** `off`, a number or `max`. A directing seat may also clear its own setting, and a person any setting. The command refuses a value past the ceiling, and, from a directing seat, a value past a person's setting that stands.
- **Where it lives.** The pace is shared state that changes while agents work, with no review of each change. So it lives on the seat's state issue, as [project-management:DEC-058-state-issues] point 1 has such state live, found by the number the topology names. It is a part of the seat's state, folded apart from its holder (DEC-058 points 2 and 5, refined in place). Each setting and each clear is an event of its own in the issue's comment log, naming its setter: the directing seat and its clone's key, or a person.
- **The fold.** A setting counts only where its author may write (DEC-058 point 4).
  - A person's setting stands until a person clears it or sets another. It replaces every setting of the directing seat written before it, which then counts for nothing.
  - The directing seat's last setting counts while the topology on the default branch names its setter as the worker's directing seat, and, where a person's setting stands, only where it was written after that setting. A setting from any other seat counts for nothing.
  - A person's clear of the directing seat's setting ends it, as a person's own setting would.
  - The fold reads the worker's state issue alone, and its caller, which reads the topology, gives it the directing seat. So no fold of one seat's state reads another's.
  - A setting belongs to the seat, not to a clone, so a release of either seat leaves it standing.
- **The lowest binds, at every read.** A seat runs at the lowest of the ceiling, the person's setting and its directing seat's, each where it counts. So a lower ceiling binds every seat at once, a person raises a seat's pace past what its directing seat set before, the directing seat may lower it again by a later setting, and a seat with no setting that counts runs at the ceiling.
- **A change of directing seat.** A directing seat the topology no longer names stops counting at the next read, so its worker rises to the person's setting or to the ceiling. That change is a reviewed merge a person authorised, and a person who wants a lower pace to outlast it sets that pace as theirs.
- **A guard, no boundary.** Like a claim on a state issue, a setting catches the mistakes of clones that follow the procedure (DEC-058 point 5). Where every clone works under one account, nothing proves who wrote it.

### 7. A seat reads its pace before each subagent it starts, and the commands hold the agent's calls to it

- **When it reads.** A seat reads its pace from its state issue at each round of its loop and before each subagent it starts. A command that holds the agent's calls to the pace reads it itself, in the read that confirms the seat (DEC-059 point 6). Before a dispatch through the harness's tools, the agent reads it with a command that shows its seat's state.
- **The register.** The clone keeps a register of the runs that take its slots, while they run, and never commits it: each run a command of this capability starts on the agent's call, where the command can tell that call, and each helper a lead dispatches, with its share (point 2). So a session in the clone counts what another runs beside it, or left running before it. The runs a helper's commands start count within the share its entry holds, and not again against the pace.
- **The commands hold the agent's calls.** Where a command can tell the agent's call from a person's, by a sign the build finds, such as the test by which the drift command tells a run a person watches (DEC-069's Terms), it holds the agent to the pace:
  - The build command and the review command read the pace and the register before they start a run on the agent's call. They start none past the pace, nor past the cap the agent passes them (point 4), and enter each run they start.
  - The drift command runs its fixers within the cap the agent passes it, and enters them.
  - A run a person starts at a terminal is held to no pace, and entered nowhere (point 1).
- **Known gaps.** Where a command has no such sign, it holds no caller to the pace and enters nothing, so the agent holds itself to the pace: it counts the run, and passes the command its free slots as the cap. So too for a subagent the agent starts through the harness's tools, other than a lead's helper, since such a dispatch passes no command of this capability. A run the agent counts alone is one that another session in the clone does not see.
- **No message carries a pace.** A directive that names no Task (DEC-081 points 1 and 8) may wake the worker to read its state issue, and passes DEC-081 point 5's check as any directive does. The worker acts on what it reads there, never on a value a message states, and answers with the pace it read (point 10). A worker that no message reaches finds the change at its next read.
- **A setting that does not read** counts for nothing, and the worker says it found one. Where the seat cannot be confirmed, the command refuses, as DEC-059 point 6 says, and nothing new starts.

### 8. A clone that holds no seat runs at the ceiling, or a session lower on the person's word

- **Its pace is the ceiling,** read as point 1 says, for all the clone's sessions together. No state issue holds a pace for it, no seat directs it, and the commands hold the agent's calls in it to the ceiling as they hold a seat's to its pace (point 7).
- **The person directing a session may lower it** in words, for that session's runs alone. The agent says the new pace back, and passes as each command's cap the lower of that pace and the clone's free slots. Nobody raises it past the ceiling in words: the agent names the setting, and the change to the configuration that would raise it.
- **A session's pool is the work the person gave it,** such as a batch of Tasks. It keeps its slots full from that work as points 4 and 5 say, with no open dependency before a Task it takes. It takes nothing beyond that work unless the person says so, since a session with no seat acts on what the person asks of it ([project-management:DEC-029-project-manager-agent-shape]).

### 9. A lowered pace stops nothing that runs

- **Each running subagent finishes.** A pace lowered below the number that run ends none of them. The agent starts no new one until fewer run than its new pace.
- **A review already started** keeps the cap it started with, since one run of the command starts its reviewers. The lower pace binds from the next start.
- **A raised pace** fills its new slots at the next read, in point 4's order.

### 10. The agent tells the person its pace once in each session

- **Once, before its first subagent** in the session, the agent says in one line the pace it runs at, where the pace comes from and the ceiling. The pace comes from the ceiling, from a setting on the seat's state issue, with its setter, or from the person's word.
- **A change it reads later** takes one line more: the new pace and where it comes from.
- **Nothing at each start.** A session that starts no subagent says nothing of its pace, and no line counts the slots as each subagent starts.
- **Where it says it:** in the session's own output, where a person reads it, as the session runs or afterwards.

## Rationale

**Why one setting the person keeps.** How many agents run at once has a cost in money, in the machine's capacity and the account's usage, and in the reviews and questions that reach the person. Each project weighs those apart, so the person chooses once, in a reviewed change, and only a reviewed change raises it. Read from the default branch, it is the same value for every clone, and no branch the agent works on raises its own pace.

**Why 4 where it is absent.** No harness counts the runs the commands start, so `max` by default would run, in a project that never chose, as many as its ready Tasks and their reviews call for, bounded only by its machine and its account's usage limits, with what follows for money and for the person's reviews, before anyone weighed it. `off` by default would turn every adopter's reviews serial, and stop a coordinator's builds at once. Four lets a review run several reviewers together, and a worker keep a few Tasks building, while what a project that never chose runs at once stays within what one person can follow. Any default is a judgement, and a project that weighs it otherwise sets its own number, or `max`, in one reviewed change. What changes for a project that sets nothing is named in the build's changeset: a review of more than four reviewers that the agent starts runs them four at a time, and a coordinator starts at most four builders at once. A person's own run of the review command at a terminal keeps its whole set at once (point 1).

**Why every subagent counts alike, whatever starts it.** A builder, a reviewer, a fixer and a helper each take a run of their own, with its cost, and so does a resumed one. Counting builders only would let the reviews of a few Tasks, each with several reviewers, run far past what the person set.

**Why the clone's runs, all its sessions together.** A clone holds at most one seat, and each session in it takes that seat up (DEC-059 point 4). A pace for each session would multiply a seat's pace by the sessions open in its clone, and a second session would run the whole pace beside the first. The register the commands read is the clone's, so the pace they hold is the clone's too.

**Why a helper holds a share, and hands its slot on.** A helper is started through the harness's tools, which pass no command of this capability, so without an entry no command a helper calls would count it, nor the other helpers, and three helpers at a pace of three would each see the whole pace. An entry with its share lets each command count the helpers, and the share in the brief tells each helper what it may start. A helper that kept its own slot while its subagents ran would wait, at a share of one, for a slot it holds itself, and its Task's review would never start. Handing the slot on bounds a helper and its subagents by its share.

**Why the pace bounds subagents, and not Tasks in flight.** What costs money and capacity is a run, and a Task that waits on its checks, a person or a question runs nothing. A bound on Tasks in flight would leave slots idle while Tasks wait, and a bound of one would stop the loop on each waiting Task. What a worker may take at all is the work the person scheduled into its pools, and a person who wants fewer Tasks waiting on them lowers the pace, or schedules less.

**Why nothing of the capability's own bounds `max`.** A project that sets `max` chooses, in a reviewed change, to run as many as the work calls for, with that cost stated (point 3). A number of the capability's own under it would be a second ceiling that no one set, wrong for some machine or account, and a project that wants a bound writes it as the ceiling. The default of 4 already bounds a project that never chose. A pace above the harness's own limit on the subagents it starts asks only for what the harness can give, so it is no error.

**Why work in flight first, then a named Task.** A review is the step that brings a built Task to its merge. A new build that took its slot would make a finished Task wait for one that is only starting. Taking what waits first bounds the first review's wait to the end of one running subagent, and costs a new build only that review's time. The fixers after a merge end a Task's work, so they rank with what work in flight waits for. A Task a directive named comes before the nearness order, since the directing seat named it for a sequence that order does not show (DEC-081, "Why a directive may reorder"). A plan's reviewer comes before new Tasks, since the plan's Tasks wait on it. A helper takes the place of its work, so the order holds whichever agent runs that work. A slot kept for reviews would sit empty where none waits, and at `off` would leave none for building.

**Why nearest the work just done.** The Tasks of one Feature finish one outcome, which the person scheduled together, and taking them first closes the Feature sooner. Two costs follow. A Task of higher priority elsewhere waits until the nearer Tasks are taken, which overturns DEC-059's priority first where a Task's work freed the slot. And sibling Tasks in flight together are the likeliest to touch one file their implementation notes missed, as the wave of pull requests DEC-066 records did, which the merge then settles at the cost of another round of review.

**Why a shared file rides the dependencies.** DEC-066 point 1 has the later of two Tasks that share a file name the earlier among its dependencies, so the one reckoning of ready work already holds it back. Reading the implementation notes of every Task in flight at each take would reckon readiness from the code a second way, which DEC-025 leaves to lanes until lived evidence settles them. Builds run at once give that evidence, and the merge settles any other overlap.

**Why a waiting Task holds no slot.** A question waits on a person, who may answer hours later. A slot it held would sit idle, and at `off` it would stop the seat's whole loop on one Task. The Task keeps its claim, so no other agent takes it (DEC-063 point 6), and the person answers in their own time.

**Why the state issue carries the pace, and a message only points.** The pace changes while the work goes on, with no review of each change, and belongs to one seat. That is what a state issue holds (DEC-058 point 1). Its comment log keeps who set what and when, every clone reads the same value, and the worker reads it in a read it makes anyway. A message can be lost or delayed, its sender cannot be proven, and a harness may carry none. A value in a message would be a second source that drifts from the first. A pointer that is lost costs only the time until the worker's next read.

**Why the directing seat may set the pace.** DEC-081 gives a worker one directing seat, named in the reviewed topology, which may already decide the order of the worker's Tasks. How many the worker runs at once is part of the same directing, so the same seat sets it, and the setter stays plain. The person directs a planner's or a lead's seat, and sets its pace directly.

**Why a person's setting outranks the directing seat's.** A seat directs a worker within what the person decides (DEC-081 point 6), so the person's pace is a bound the seat works under, not a value it replaces. A person's setting replaces what a directing seat set before it, and a person may clear any setting, so a person may raise a worker's pace as well as lower it. The directing seat then lowers it again only by a later setting, which is the seat's directing within the person's bound. A setting that lasts until a person clears it is one the person can rely on, whoever directs the worker later.

**Why a setting is the seat's, and the lowest binds at every read.** A directing seat's setting that counted only while its setter's clone held the seat would lapse whenever a lead's session ended, and its workers would rise with nobody choosing it. Counted by the seat the topology names, it stands until someone with the right changes it, and counts for nothing where the topology does not grant that right. Taking the lowest at each read makes a lowered ceiling, or a person's setting, bind at once, with no write to any other setting.

**Why the commands hold the agent's calls, and a person's run takes no slot.** A pace that rests on the agent counting its own runs leaves the limit to the agent that would lose count, as DEC-063's "Why a mechanism, not an instruction" says of the clean start. The build and review commands start most of a seat's runs, so their reading of the pace and of the clone's register makes the pace hold for those runs, and for another session that finds runs the first left. The pace bounds what the agent runs on the person's behalf, not what the person runs, so a person at a terminal keeps the command's own cap. Where a command cannot tell the two apart, holding every caller would hold the person too, so it holds none, and the pace stays the agent's own step there, named as the gap it is, as for a dispatch through the harness's tools.

**Why a lowered pace stops nothing.** A builder stopped in its run loses its work and leaves its clone half built, and a reviewer stopped posts no verdict, so its review runs again. Finishing what runs costs at most the length of the runs in flight.

**Why a clone with no seat runs at the ceiling.** It has no state issue and no directing seat, so the committed value is all it has, and the person who directs a session is there to lower it for that session. Raising it past the ceiling in words would let one session's word outrank the reviewed value, which holds for every clone alike. Taking only the work it was given keeps a session off work that another person or session may hold.

**Why tell the person once.** The person should know what runs on their behalf, and at what cost, without a line at each start. One line before the first subagent, and one at each change, says it where the person reads the session.

### Alternatives considered

- **`max` where the key is absent.** Rejected, as "Why 4 where it is absent" says: a project that never chose would run as many as its ready work calls for, bounded only by its machine and its account.
- **`off` where the key is absent.** Rejected, as "Why 4 where it is absent" says: every adopter's reviews would run one reviewer at a time, before anyone chose it.
- **Another number by default.** Not taken: any default is a judgement, as "Why 4 where it is absent" says, and a project that weighs it otherwise sets its own.
- **A cap of the capability's own on `max`.** Rejected, as "Why nothing of the capability's own bounds `max`" says.
- **The ceiling in the topology.** Rejected: a clone with no seat, and a project with no topology, would have none, and each new key of the topology waits until every clone reads it (DEC-061 point 9).
- **The ceiling read from the working tree.** Rejected: a branch the agent works on could raise its own pace.
- **Count builders only.** Rejected, as "Why every subagent counts alike" says.
- **A pace for each session.** Rejected, as "Why the clone's runs, all its sessions together" says.
- **Count each agent's subagents apart, a helper's against a pace of its own.** Rejected: a lead at a pace of three, with three helpers each running a review of three, would run a dozen at once.
- **Helpers outside the register, counted by the lead alone.** Rejected, as "Why a helper holds a share, and hands its slot on" says.
- **Bound Tasks in flight too.** Not taken, as "Why the pace bounds subagents, and not Tasks in flight" says.
- **A slot kept for reviews.** Rejected, as "Why work in flight first" says.
- **A review that waits for a slot for each of its reviewers.** Rejected: at a low pace, a review with many reviewers would wait for every build to end.
- **The highest priority first, whatever the work just done.** Not the maintainer's decision. A seat's work would scatter across Features, and each would close later.
- **A named Task after the nearness order.** Rejected: the directing seat named it for a sequence the order does not show.
- **Read the implementation notes of every Task in flight at each take.** Not taken, as "Why a shared file rides the dependencies" says. The record that builds lanes may refine point 5.
- **A waiting Task that holds its slot, or ends the loop.** Rejected, as "Why a waiting Task holds no slot" says.
- **A state issue of its own for each seat's pace.** Rejected: a second issue to create, name and find for every seat, where the seat's own already holds its state.
- **The pace carried in the message.** Rejected, as "Why the state issue carries the pace, and a message only points" says.
- **The last setting counts, whoever wrote it.** Rejected, as "Why a person's setting outranks the directing seat's" says: a lead's later setting could raise the pace past the person's without a word.
- **A person who clears only their own setting.** Rejected: a directing seat's lower setting would then hold, whatever the person said, until the seat cleared it or a reviewed merge named another.
- **A setting that counts only while its setter's clone holds the directing seat.** Rejected, as "Why a setting is the seat's" says.
- **The pace held by the agent's own count alone.** Rejected, as "Why the commands hold the agent's calls" says.
- **The commands hold every caller in the clone, a person past the pace only by the override flag with its reason.** Rejected, as "Why the commands hold the agent's calls" says: a person would need an override to run a review at a terminal as the command runs it today.
- **Stop the newest runs when the pace is lowered.** Rejected, as "Why a lowered pace stops nothing" says.
- **The person's word raises a session's pace past the ceiling, with a warning.** Rejected: one session's word would outrank the reviewed value, which holds for every clone alike.
- **Tell the person at each start, or never.** Rejected: a line at each start buries the work, and silence hides what runs on the person's behalf.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([pkit:COR-066] point 5), sorted by kind and then by record:
  - **Overturned in part.** Each record stays accepted, and its overturned words stay as they stood.
    - DEC-059's top line, which names DEC-061, names this record too, in one paragraph. Its clause that DEC-081 rewords, "as far as DEC-061 goes", serves this record too, so this record rewords none of the line's sentences. The line adds, after the sentences of DEC-061 and DEC-081, as sentences of this record's own: "Whenever a Task's work frees a slot of a seat, the seat's ready Tasks rank nearest that Task first: those of its Feature, then its EPIC, then its Milestone, then the rest, by priority within each. Overturned there by DEC-082: point 7's 'the highest in priority first', where a Task's work freed the slot. Priority alone orders the Tasks where no Task's work freed the slot."
    - DEC-061 gains a top line that reads: "Partially superseded by DEC-082. Whenever a Task's work frees a slot of a seat, the ready Tasks of its pools rank nearest that Task first: those of its Feature, then its EPIC, then its Milestone, then the rest, by priority within each. Overturned: point 5's 'the Tasks rank as there', where a Task's work freed the slot, so far as it ranks them by priority alone. Priority alone orders them where no Task's work freed the slot. The rest stands."
    - DEC-063 gains a top line that reads: "Partially superseded by DEC-082. A seat whose build waits on a question tells the person, and goes on with its other work within its pace. Overturned: point 6's 'The seat tells the person, and ends the loop'. The rest stands."
  - **Refined in place,** each with a forward refinement pointer to this record:
    - DEC-058 point 2, completed: one piece of state may hold parts, each folded apart under the piece's one key, such as a seat's holder and its pace, and the record that adds a part says how it folds.
    - DEC-058 point 5, completed: the holder's release frees the state, which is free while no clone holds it, whatever its other parts hold, and the record that adds another part says whether a release clears it. So point 6's free state, the summary's and ADR-071 point 4's keep their one sense.
    - DEC-059 point 2, widened: a worker builds and reviews as many Tasks at once as its pace allows.
    - DEC-059 point 3, completed: the seat's state issue keeps the seat's pace too, folded apart from its holder.
    - DEC-063 point 1, completed: where no builder can start, the seat starts no other build, and its loop ends once the subagents it runs have ended. A Task the person directs to be built in the seat's session is built there alone.
- **Architecture records:**
  - **ADR-073, overturned in part by a new architecture record,** whose scope is the runs in a seat's clone. The architect drafts it, it is proposed in this change, and a person accepts it there, no earlier than this record. The change lands only once it is accepted. The sign-off on this record authorises the overturn, and accepts none of the new record's text. Overturned: point 5's one build at a time in a seat's clone; its recovery's "before any other work: it waits on a running one", since a session acts on each finished build and fills its other slots while builds run; and exit 1's "a build already running", narrowed to a build of the same Task. The single state file, and a `--wait` that names no Task, follow from these, and the new record decides them. It also decides a state file for each build, keyed by its Task, recovery over each build, fetches, signing and hand-backs that run at once in one clone, and the register of runs (point 7). It lands before the build command is built (#2287), so that the command is not built for one build at a time.
  - **ADR-071, refined in place** for the pace ([pkit:ADR-071]), each edit with a forward refinement pointer to this record. The architect makes them in this change once this record is accepted, before the build, and the maintainer's sign-off on this record covers them. Each is a sentence of its own, beside the sentences DEC-081 edits for the session, so each sentence has one editor:
    - the Summary's "What it never reads", completed: for a seat's pace, the caller also passes the seat's directing seat
    - point 1's snapshot, completed: it builds each worker's directing seat from the topology among each run's inputs
    - point 4's opening, widened: the fold is a function of the counted events alone, in their order, but for the pace, which takes the directing seat from its caller
    - point 4, completed by a bullet after "What it returns": the fold also returns the person's setting and the directing seat's, each where it counts, and a release clears neither
    - point 5, completed by a bullet after the payload: a setting of a pace names its value and its setter, a person or the directing seat with its clone's key, and a person's setting written from a clone with no key yet names none, since a clone makes its key only when it first claims (DEC-058 point 5)
    - point 7's last bullet, completed: the caller also passes a seat's directing seat
    - point 8, completed by a sentence after the count of a seat's log: each setting or clear of its pace adds one comment
    - point 8, completed by a bullet after "Before a write as the holder": a run that writes a pace for a seat its clone does not hold reads that seat's state issue first, in the same run, and refuses a directing seat's value past a person's setting that stands
- **What stands:**
  - DEC-025's one reckoning of ready work, which ranks nothing. The nearness order is an option the build adds to the take (point 5).
  - DEC-029's reviewer threshold and dispatch discipline, whose dispatches each take a slot
  - DEC-063's Implications' "Named, not built", whose seat taking other work while a question waits this record decides
  - DEC-066's order of Tasks that share a file, and its fold
  - DEC-081 point 1, under which a pointer to a new pace is a directive that only wakes, and point 5, its check
  - [pkit:ADR-072]'s pool lookup, whose take gains as an input the Task whose work freed the slot
- **A build Task** brings, after DEC-081's build, which brings the directing seat to the topology:
  - the configuration key and its schema, read as 4 where it is absent
  - the pace's events on a seat's state issue, their fold, and the command that sets or clears a pace
  - an option of the take to rank the Tasks nearest a given Task first
  - the register of runs, a helper's entry with its share, and the build and review commands holding the agent's calls to the pace where they can tell them
  - the agent passing each command that starts subagents its free slots as the cap, and each helper its share in the brief
  - the steps of the agent's definition and of the pm skill's work loop and batch plan
  - the capability's README, where seats, the work loop, the configuration and the review command's cap are described, and the agent's storyboard, with a worker that runs several builds at once
- **What the build changes for every adopter,** which its `minor` changeset declares:
  - A worker keeps several Tasks in flight at any pace, where it took a new one only once nothing was in flight, and takes the Tasks nearest the work just done first.
  - A project that sets no ceiling runs at most four subagents at once in a clone. So a review of more than four reviewers that the agent starts runs them four at a time, and a coordinator starts at most four builders at once.
  - The review and drift commands, called by the agent, run at most the slots free when it starts them. A person's own run at a terminal keeps each command's own cap and default.
  - The changeset names the setting that raises or lowers the ceiling, and what `max` costs: as many runs as there are ready Tasks that share no file, with their reviews' reviewers, bounded only by the machine and the account's usage limits.
- **Acceptance:** this record overturns the accepted DEC-059, DEC-061 and DEC-063 in part, and refines DEC-058, DEC-059 and DEC-063 in place, so accepting it needs the maintainer's sign-off. That sign-off covers ADR-071's refinement, and authorises the overturn in part of ADR-073, which the new architecture record makes, proposed in this change and accepted there by a person. This record rests on DEC-081, accepted with it in this change: point 2 on the resume by messaging (DEC-081 point 2), point 4 on the named Task (DEC-081 point 6), point 6 on the directing seat (DEC-081 point 3), point 7 on the directive that only wakes, its check and its answer (DEC-081 points 1, 5 and 8), and the Rationale on why a directive may reorder. Refusing DEC-081 leaves each of those with nothing to refer to, so this record is then revised to decide them itself, or waits.
- **No behaviour changes** until the build, so the record lands with a `none` changeset.
