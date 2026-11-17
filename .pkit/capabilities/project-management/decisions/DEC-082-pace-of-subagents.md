---
id: DEC-082
title: The project-manager runs as many subagents at once as a committed pace allows, and keeps them busy
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the project-manager agent may run several agents of its own at once, a builder for each Task and the reviewers of each change. One setting in the capability's committed configuration says how many. `off` runs one at a time, a number runs at most that many, and `max` runs as many as the work and the harness allow. That value is the **ceiling**, and where it is absent it is `off`. Within its pace the agent keeps busy without being told. Whenever one of its runs ends, it first starts what its work in flight waits for, such as a review, and then takes the next Task that nothing blocks, nearest the work just done. The seat that directs a worker may set the worker's pace below the ceiling, or back up to it, on the worker's state issue, which the worker reads before each run it starts. A lowered pace stops nothing that runs, and the agent tells the person once in each session at what pace it runs.

## Context

**What stands.**

- **A builder for each Task.** In a project with a topology of seats, a fresh builder builds each of a worker's Tasks, started by the capability's build command in a sandboxed clone of its own ([project-management:DEC-063-task-builder] points 1 and 4). The seat's own working tree stays on the default branch, so nothing in the seat keeps two builds from running at once.
- **Reviewers at once.** The review command starts the reviewers of a change together, and takes a cap on how many run at once.
- **One Task at a time, in practice.** The worker's loop in the pm skill takes a new Task only once nothing is in flight. A build that stops on a question ends the loop, and DEC-063 names "a seat taking other work while a question waits" among what it does not build.
- **A session with no seat** dispatches builders and reviewers as the person directs it, such as a session that coordinates a batch of Tasks in a project with no topology.
- **Nothing bounds the count.** No record says how many of these runs the agent may have going at once, or that it starts the next without being asked.

**What the maintainer decided.** On 17 November the maintainer decided how much work the agent runs at once (#3394):

- One setting, in the project's committed configuration of this capability, gives the number of subagents the agent runs at once. `off` runs one at a time, a number at most that many, and `max` as many as the work allows. Builders and reviewers count alike.
- The agent keeps its slots full, and does not wait to be told to work in parallel. Whenever a slot frees, it takes the next Task that nothing blocks. It looks first in what the current work belongs to, its Feature, its EPIC and its Milestone, and only then in the rest of its pool. A Task is not blocked where no open dependency stands before it, it shares no file with a Task in flight, and its seat may take it.
- A directing seat sets the pace of a seat it directs, within the ceiling the committed configuration gives. It writes the value in that seat's state issue, where the worker reads it at each step of its loop. A message through the harness only points the worker to the change. A worker with no pace set takes the configured value.
- The person keeps the ceiling. The committed value is the most any seat runs, and a lead may lower a worker's pace, or raise it back up to the ceiling, never past it.

This record holds those decisions. It settles what they leave open: the value where the key is absent, what bounds `max`, a session with no seat, how a review waits for a slot, what a lowered pace does to a run already going, and how the agent tells the person its pace.

**Terms.**

- **A subagent** is an agent run that the project-manager agent starts for its work. It starts one through the harness's tool for starting agents, or through a command of this capability that starts one, such as the build command's builder or each reviewer the review command starts. The agent's own session is none, and nor is a run a person starts at a terminal, such as a fixer's ([project-management:DEC-056-drift-fixers]).
- **The pace** is the most subagents the agent runs at once. **A slot** is room for one subagent within the pace, and a slot is free while fewer subagents run than the pace allows.
- **The ceiling** is the pace the configuration gives, the most any session of the agent runs.
- **Work in flight** is each Task the agent has started and not yet seen merged or closed: one it is building, or one waiting on its checks, its review, a fix round, a merge of the base or a question.

## Decision

**One setting of the capability's committed configuration, read from the default branch, gives the ceiling on how many subagents the project-manager agent runs at once: `off`, a number or `max`, and `off` where it is absent. Builders and reviewers count alike. Within its pace, the agent starts first what its work in flight waits for, then the next Task that nothing blocks, nearest the work just done. A worker's directing seat, or a person, may set the worker's pace within the ceiling on the worker's state issue, which the worker reads before each subagent it starts. A session with no seat runs at the ceiling, or lower on the person's word. A lowered pace stops nothing that runs, and the agent tells the person its pace once in each session.**

### 1. One committed setting gives the ceiling, and `off` where it is absent

- **Where it lives.** It is one key of the capability's configuration, beside its other settings, and not of the topology, since it binds a session that holds no seat and a project with no topology too. The key's name is the build's.
- **Read from the default branch,** at the commit the backbone resolves it to, as the topology is read ([project-management:DEC-059-topology-of-seats] point 1). So a change to the ceiling binds once a merge lands it, and no branch the agent works on raises its own pace.
- **Its values:**
  - `off` runs one subagent at a time, and `1` means the same.
  - A whole number of at least one runs at most that many at once.
  - `max` runs as many as the work and the harness allow (point 3).
- **Absent, it is `off`.** A project that has not chosen runs one subagent at a time.
- **A value that does not read,** such as zero or a word it does not know, runs one subagent at a time, and the agent says why. The configuration's schema refuses such a value on the change that writes it.

### 2. Every subagent takes a slot, builders and reviewers alike

Each subagent takes one slot for as long as it runs, whatever its kind:

- a builder, of a Task, of a fix round or of a merge of the base
- each reviewer of a change, so a review takes one slot for each of its reviewers that runs at once
- a reviewer of a plan, such as the critic that batch planning calls
- a lead's helper

A Task that waits on its checks, on its verdicts being posted, on a person or on a question runs no subagent, so it holds no slot.

### 3. The harness and the work bound every pace

- **A pace is a ceiling, never a demand.** Where the harness limits how many subagents, or commands in the background, a session runs together, the agent starts none past that limit. `max`, and a number above the limit, run at the harness's limit, which is no error.
- **Only what the work calls for.** With nothing waiting and no Task that nothing blocks, slots stay free.
- **No other limit.** This capability sets no number of its own above the harness's limit and the work's.

### 4. Work in flight comes before new work

Whenever a slot frees, and at the start of each round of its loop, the agent fills its free slots in this order, without being told:

1. **What its work in flight waits for:** a review whose checks have passed (DEC-063 point 8), a fix round on a verdict that asks for changes, and a build that merges the base into a Task's branch. Each starts in the order it came to wait.
2. **Then new Tasks,** each the next that nothing blocks (point 5), one for each slot still free.

So no new build takes a slot that a waiting review could use, and a review waits at most until one running subagent ends.

- **A review takes the slots free when it starts,** at least one and no more than it has reviewers. It runs its other reviewers in turn within them.
- **A command that starts reviewers** is passed that number as its cap on how many run at once.

### 5. A new Task is the next that nothing blocks, nearest the work just done

- **Nothing blocks a Task** that the one reckoning of ready work holds ready for the agent ([project-management:DEC-025-parallelization-primitive]):
  - No open issue stands among its dependencies ([project-management:DEC-005-linking-and-containment]).
  - It shares no file with a Task in flight. Of two Tasks that share a file, the later names the earlier among its dependencies, and starts only once the earlier has merged ([project-management:DEC-066-fold-tasks-that-share-a-file] point 1). So the first condition holds it back, and the reckoning reads nothing more from the code.
  - Its seat may take it, by the seat's scope (DEC-059 point 7), and by its pools where the topology declares them ([project-management:DEC-061-pools-of-workers] point 5).
- **Nearest first.** The agent takes first the Tasks that share the Feature of the Task whose work freed the slot, then those that share its EPIC, then those in its Milestone, each where it has one, and then the rest of its pool. Within each, the Tasks rank as the pool ranks them, the highest in priority first. Where no Task's work freed the slot, as at the start of a session, the pool's ranking alone orders them.
- **A Task that waits on a question** keeps its claim and holds no slot (DEC-063 point 6). The agent tells the person, and goes on with its other work within its pace. A later session's first step finds the open question before it takes other work.

### 6. A worker's directing seat, or a person, sets the worker's pace on its state issue

- **The directing seat.** The topology may name, on a worker's seat, one seat that directs it: a planner's or a lead's, not retired. A seat directs only the workers whose seats name it, and a planner's or a lead's seat names none. The topology's check refuses a worker's seat that names a seat the topology does not hold, a retired seat, itself or another worker's seat. It refuses a planner's or a lead's seat that names any.
- **Who sets a seat's pace:**
  - The clone that holds the worker's directing seat. The command that writes the pace confirms that seat first, as every command that acts as an instance does (DEC-059 point 6).
  - A person, for any seat, at a terminal or through the command run with its consent flag on the person's word, as a person authorises a release by force (DEC-059 point 5). An agent never gives that word for itself.
- **What it sets:** `off`, a number or `max`, never past the ceiling, which the command refuses. Or it clears the setting, so the seat runs at the ceiling again.
- **Where it lives.** The pace is shared state that changes while agents work, with no review of each change. So it lives on the seat's state issue, under the seat's name, as part of the seat's one piece of state, found by the number the topology names ([project-management:DEC-058-state-issues] points 1 and 2). Each setting is an event of its own in the issue's comment log, naming its setter: the directing seat and its clone's key, or the person. The seat's claims fold as DEC-058 point 6 says, and its pace folds apart.
- **The fold.** A seat's setting is the last that counts. One counts where its author may write (DEC-058 point 4), and where it comes from a person or from the seat that the topology on the default branch names as the seat's directing seat. A setting from a seat that the topology does not name as its directing seat counts for nothing. A setting belongs to the seat, not to a clone, so a release of either seat leaves it standing.
- **The ceiling binds at every read.** A seat runs at its setting or at the ceiling, whichever is lower, so a lower ceiling binds every seat at once. A seat with no setting that counts runs at the ceiling.
- **A guard, no boundary.** Like a claim on a state issue, a setting catches the mistakes of clones that follow the procedure (DEC-058 point 5). Where every clone works under one account, nothing proves who wrote it.

### 7. A seat reads its pace before each subagent it starts, and a message only points to it

- **When it reads.** A seat reads its pace from its state issue at each round of its loop and before each subagent it starts, in the read that confirms its seat (DEC-059 point 6). So a change reaches it at its next start, with no read of its own.
- **No message carries a pace.** A message that reaches a worker, by whatever channel an accepted record gives it, at most points it to its state issue. The worker acts on what it reads there, never on a value a message states. A worker that no message reaches finds the change at its next read.
- **A setting that does not read** counts for nothing, and the worker says it found one. Where the seat cannot be confirmed, the command refuses, as DEC-059 point 6 says, and nothing new starts.

### 8. A session with no seat runs at the ceiling, or lower on the person's word

- **Its pace is the ceiling,** read as point 1 says. No state issue holds a pace for it, and no seat directs it.
- **The person directing the session may lower it** in words, for that session alone, and the agent says the new pace back. Nobody raises it past the ceiling in words: the agent names the setting, and the change to the configuration that would raise it.
- **Its pool is the work the person gave it,** such as a batch of Tasks. It keeps its slots full from that work as points 4 and 5 say, with no open dependency before a Task it takes. It takes nothing beyond that work unless the person says so, since a session with no seat takes its direction from the request ([project-management:DEC-029-project-manager-agent-shape]).

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

**Why one setting the person keeps.** How many agents run at once has a cost in money, in the harness's capacity, and in the reviews and questions that reach the person. Each project weighs those apart, so the person chooses once, in a reviewed change, and only a reviewed change raises it. Read from the default branch, it is the same value for every session, and no branch the agent works on raises its own pace.

**Why `off` where it is absent.** A project that never chose sees no change: it runs one subagent at a time. Several at once multiplies the cost and what waits on the person, and only the person can judge that their project wants it. A small number by default would be a guess that fits no project in particular.

**Why every subagent counts alike.** A builder and a reviewer each take a run of the harness, with its cost and its capacity. Counting builders only would let the reviews of a few Tasks, each with several reviewers, run far past what the person set.

**Why the harness and the work bound `max`.** The harness knows how many runs it carries at once, and the work knows how many are worth starting. A number of the capability's own would be wrong on some harness. A number set above the harness's limit asks only for what the harness can give, so it is no error.

**Why work in flight first.** A review is the step that brings a built Task to its merge. A new build that took its slot would make a finished Task wait for one that is only starting. Taking what waits first bounds a review's wait to the end of one running subagent, and costs a new build only that review's time. A slot kept for reviews would sit empty where none waits, and at `off` would leave none for building.

**Why nearest the work just done.** The Tasks of one Feature finish one outcome, which the person scheduled together. Taking them first closes the Feature sooner, and the next build reads the same records and code as the last. The cost is that a Task of higher priority elsewhere in the pool waits until the nearer Tasks are taken.

**Why a shared file rides the dependencies.** DEC-066 point 1 has the later of two Tasks that share a file name the earlier among its dependencies, so the one reckoning of ready work already holds it back. Reading the implementation notes of every Task in flight at each take would reckon readiness from the code a second way, which DEC-025 leaves to lanes until lived evidence settles them. Builds run at once give that evidence, and the merge settles any other overlap.

**Why a waiting Task holds no slot.** A question waits on a person, who may answer hours later. A slot it held would sit idle, and at `off` it would stop the seat's whole loop on one Task. The Task keeps its claim, so no other agent takes it (DEC-063 point 6), and the person answers in their own time.

**Why the state issue carries the pace, and a message only points.** The pace changes while the work goes on, with no review of each change, and belongs to one seat. That is what a state issue holds (DEC-058 point 1). Its comment log keeps who set what and when, every clone reads the same value, and the worker reads it in a read it makes anyway. A message can be lost or delayed, its sender cannot be proven, and a harness may carry none. A value in a message would be a second source that drifts from the first. A pointer that is lost costs only the time until the worker's next read.

**Why the topology names the directing seat.** Who may slow a worker is authority, so a reviewed change grants it, as the topology grants the organizer seat its release by force (DEC-059 point 2). One directing seat for each worker keeps the setter plain. The person directs a planner's or a lead's seat, and sets its pace directly.

**Why a setting is the seat's, and the ceiling binds at every read.** A setting that counted only while its setter's clone held the directing seat would lapse whenever a lead's session ended, and its workers would rise to the ceiling with nobody choosing it. Counted by the seat the topology names, it stands until someone with the right changes it, and counts for nothing where the topology does not grant that right. Taking the lower of setting and ceiling at each read makes a lowered ceiling bind every seat at once, with no write to any state issue.

**Why a lowered pace stops nothing.** A builder stopped in its run loses its work and leaves its clone half built, and a reviewer stopped posts no verdict, so its review runs again. Finishing what runs costs at most the length of the runs in flight.

**Why a session with no seat runs at the ceiling.** It has no state issue and no directing seat, so the committed value is all it has, and the person who directs it is there to lower it. Raising it past the ceiling in words would let one session's word outrank the reviewed value, which holds for every session alike. Taking only the work it was given keeps it off work that another person or session may hold.

**Why tell the person once.** The person should know what runs on their behalf, and at what cost, without a line at each start. One line before the first subagent, and one at each change, says it where the person reads the session.

### Alternatives considered

- **`max` where the key is absent.** Rejected: every project would run as many agents as its harness allows from its next sync, with the cost and the reviews that follow, before anyone chose it.
- **A small number by default, such as three.** Rejected, as "Why `off` where it is absent" says.
- **A cap of the capability's own on `max`.** Rejected, as "Why the harness and the work bound `max`" says.
- **The ceiling in the topology.** Rejected: a session with no seat, and a project with no topology, would have none, and each new key of the topology waits until every clone reads it (DEC-061 point 9).
- **The ceiling read from the working tree.** Rejected: a branch the agent works on could raise its own pace.
- **Count builders only.** Rejected, as "Why every subagent counts alike" says.
- **A slot kept for reviews.** Rejected, as "Why work in flight first" says.
- **A review that waits for a slot for each of its reviewers.** Rejected: at a low pace, a review with many reviewers would wait for every build to end.
- **The highest priority first, whatever the work just done.** Not the maintainer's decision. A seat's work would scatter across Features, and each would close later.
- **Read the implementation notes of every Task in flight at each take.** Not taken, as "Why a shared file rides the dependencies" says. The record that builds lanes may refine point 5.
- **A waiting Task that holds its slot, or ends the loop.** Rejected, as "Why a waiting Task holds no slot" says.
- **A state issue of its own for each seat's pace.** Rejected: a second issue to create, name and find for every seat, where the seat's own already holds its state.
- **The pace carried in the message.** Rejected, as "Why the state issue carries the pace, and a message only points" says.
- **A setting that counts only while its setter's clone holds the directing seat.** Rejected, as "Why a setting is the seat's" says.
- **Stop the newest runs when the pace is lowered.** Rejected, as "Why a lowered pace stops nothing" says.
- **Leave who directs a worker to a later record.** Rejected: this record cannot rest on a record not yet accepted, and the pace needs to know who may set it.
- **Tell the person at each start, or never.** Rejected: a line at each start buries the work, and silence hides what runs on the person's behalf.

## Implications

- **Edits to accepted records,** made once this record is accepted, sorted by record:
  - **DEC-059, refined in place:**
    - Point 2: a worker runs as many builds and reviews at once as its pace allows. Among what a seat declares, a worker's seat may name the seat that directs it, a planner's or a lead's (refinement per DEC-082 points 2 and 6).
    - Point 3: a seat's state issue keeps its pace beside which clone holds it, each folded apart (refinement per DEC-082 point 6).
    - Point 7 gains a sentence after its opening: whenever a slot frees, the ready Tasks nearest the work that freed it come first, those of its Feature, then its EPIC, then its Milestone, and priority ranks within each (refinement per DEC-082 point 5). The opening sentence stays as it stood, since DEC-061 overturns it in part.
  - **DEC-061, refined in place:** point 5's "the Tasks rank as there" gains "nearest the work that freed the seat's slot first" (refinement per DEC-082 point 5).
  - **DEC-063, refined in place:**
    - Point 1, where no builder can start: the agent starts no other build, and the loop ends once the subagents it runs have ended.
    - Point 6: "The seat tells the person, and ends the loop" becomes that the seat tells the person, and goes on with its other work within its pace (refinement per DEC-082 point 5).
    - Its Implications' "Named, not built" drops a seat taking other work while a question waits, which DEC-082 decides.
- **What stands:**
  - DEC-025's one reckoning of ready work, which ranks the nearest first
  - DEC-029's reviewer threshold and dispatch discipline, whose dispatches each take a slot
  - DEC-058, under which a seat's state issue holds one piece of state under one key
  - DEC-066's order of Tasks that share a file, and its fold
  - DEC-068's withheld tools, so this record gives the agent no message to send
- **A build Task** brings:
  - the configuration key and its schema
  - the pace's events on a seat's state issue, their fold, and the command that sets or clears a pace
  - the directing seat in the topology, its schema and its check
  - an option of the reckoning of ready work to rank the Tasks nearest a given Task first
  - the agent passing each command that starts reviewers its free slots as the cap
  - the steps of the agent's definition and of the pm skill's work loop
  - the capability's README, where seats, the work loop and the configuration are described, and the agent's storyboard, with a worker that runs several builds at once
- **The order of work.** The directing seat is a new key of the topology, so it enters a project's topology only once every clone that may take a seat runs code that reads it (DEC-061 point 9).
- **Until the build command exists** (#2287), a worker builds each Task in its own clone, one at a time, so its pace bounds only its reviews.
- **Acceptance:** this record refines the accepted DEC-059, DEC-061 and DEC-063 in place, so accepting it needs the maintainer's sign-off. The refinements land only with this record accepted.
- **No behaviour changes** until the build, so the record lands with a `none` changeset.
