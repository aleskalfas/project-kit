---
id: DEC-082
title: The project-manager runs as many subagents at once as its pace allows, under a committed ceiling, and keeps them busy
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the project-manager agent may run several agents of its own at once: a builder for each Task, the reviewers of each change, the fixers after a merge and a lead's helpers. One setting in the capability's committed configuration gives the **ceiling** on how many. `off` runs one at a time, a number runs at most that many, and `max` runs as many as the work and the harness allow. Where the setting is absent it is `max`, so reviews and a coordinator's builders keep running together as they do today. Within its pace the agent keeps busy without being told. Whenever one of its runs ends, it first starts what its work in flight waits for, such as a review, then a Task its directing seat named, and then the next Task that nothing blocks, nearest the work just done. The seat that directs a worker may set the worker's pace below the ceiling, or back up to it, on the worker's state issue. A person may set any seat's pace, which the directing seat then only lowers, and which only a person clears. The build and review commands hold to the pace. A lowered pace stops nothing that runs, and the agent tells the person once in each session at what pace it runs.

## Context

**What stands.**

- **A builder for each Task.** In a project with a topology of seats, a fresh builder builds each of a worker's Tasks, started by the capability's build command in a sandboxed clone of its own ([project-management:DEC-063-task-builder] points 1 and 4). The seat's own working tree stays on the default branch, yet the architecture of the build command allows one build at a time in a seat's clone, and refuses a second while one runs ([pkit:ADR-073] point 5).
- **Reviewers at once.** The review command starts the reviewers of a change together, the whole set by default, and takes a cap on how many run at once.
- **Fixers after a merge.** The agent's run after a merge starts the fixers through the drift command where their confined form holds or the project's switch is on, with a cap of their own ([project-management:DEC-069-when-fixers-start] point 1).
- **One Task at a time, in practice.** The worker's loop in the pm skill takes a new Task only once nothing is in flight. A build that stops on a question ends the loop, and DEC-063 names "a seat taking other work while a question waits" among what it does not build.
- **A session with no seat** dispatches builders and reviewers as the person directs it, several at once where the person asks, as a session that coordinates a batch of Tasks in a project with no topology does.
- **The directing seat.** [project-management:DEC-081-delegation-between-seats], accepted with this record, has the topology name a worker's directing seat, and lets that seat's session message the worker.
- **Nothing bounds the count.** No record says how many of these runs the agent may have going at once, or that it starts the next without being asked.

**What the maintainer decided.** On 17 November the maintainer decided how much work the agent runs at once (#3394):

- One setting, in the project's committed configuration of this capability, gives the number of subagents the agent runs at once. `off` runs one at a time, a number at most that many, and `max` as many as the work allows. Builders and reviewers count alike.
- The agent keeps its slots full, and does not wait to be told to work in parallel. Whenever a slot frees, it takes the next Task that nothing blocks. It looks first in what the current work belongs to, its Feature, its EPIC and its Milestone, and only then in the rest of its pool. A Task is not blocked where no open dependency stands before it, it shares no file with a Task in flight, and its seat may take it.
- A directing seat sets the pace of a seat it directs, within the ceiling the committed configuration gives. It writes the value in that seat's state issue, where the worker reads it at each step of its loop. A message through the harness only points the worker to the change. A worker with no pace set takes the configured value.
- The person keeps the ceiling. The committed value is the most any seat runs, and a lead may lower a worker's pace, or raise it back up to the ceiling, never past it.

This record holds those decisions. It settles what they leave open: the value where the key is absent, what bounds `max`, which runs count, how the commands hold to the pace, a session with no seat, how a review and a named Task wait for a slot, whose setting outranks whose, what a lowered pace does to a run already going, and how the agent tells the person its pace.

**Terms.**

- **The agent** is the agent that runs the pm skill's procedures in a session: the project-manager agent, or another agent definition a seat names in its place ([project-management:DEC-059-topology-of-seats] point 8).
- **A subagent** is an agent run that a session starts or resumes for the agent's work: through the harness's tools for starting agents or for messaging, or through a command of this capability, such as the build command's builder, each reviewer the review command starts and each fixer the drift command starts. A helper's own subagents are the session's too. The session's own agent is none, and nor is a run a person starts at a terminal.
- **The pace** is the most subagents a session runs at once. **A slot** is room for one subagent within the pace, and a slot is free while fewer subagents run than the pace allows.
- **The ceiling** is the pace the configuration gives, the most any session runs.
- **Work in flight** is each Task the agent has started and not yet seen merged or closed: one it is building, or one waiting on its checks, its review, a fix round, a merge of the base or a question.

## Decision

**One setting of the capability's committed configuration, read from the default branch, gives the ceiling on how many subagents a session runs at once: `off`, a number or `max`, and `max` where it is absent. Every subagent the session runs takes a slot. Within its pace, the agent starts first what its work in flight waits for, then a Task a directive named, then the next Task that nothing blocks, nearest the work just done. A worker's directing seat may set the worker's pace within the ceiling, on the worker's state issue, and a person may set any seat's, which a directing seat only lowers. The build and review commands hold to the pace. A lowered pace stops nothing that runs, and the agent tells the person its pace once in each session.**

### 1. One committed setting gives the ceiling, and `max` where it is absent

- **Where it lives.** It is one key of the capability's configuration, beside its other settings, and not of the topology, since it binds a session that holds no seat and a project with no topology too. The key's name is the build's.
- **Read from the default branch,** at the commit the backbone resolves it to, as the topology is read (DEC-059 point 1). So a change to the ceiling binds once a merge lands it, and no branch the agent works on raises its own pace.
- **Its values:**
  - `off` runs one subagent at a time, and `1` means the same. A worker at `off` still takes a new Task while earlier ones wait on their checks, a person or a question, since a Task that waits holds no slot (point 2).
  - A whole number of at least one runs at most that many at once.
  - `max` runs as many as the work and the harness allow (point 3).
- **Absent, it is `max`.** A project that has not chosen keeps its reviews and a coordinator's builders running together, and its workers fill as many slots as the work and the harness allow.
- **A value that does not read,** such as zero or a word it does not know, runs one subagent at a time, and the agent says why. The configuration's schema refuses such a value on the change that writes it.
- **A person at a terminal** who runs a command that starts subagents keeps the command's own cap and its default. The ceiling binds the agent, which passes each such command its free slots as the cap, and that cap wins over the command's other settings.

### 2. Every subagent takes a slot, whatever starts it

Each subagent takes one slot for as long as it runs:

- a builder, of a Task, of a fix round, of a merge of the base, or of a build resumed once its question is answered
- each reviewer of a change, so a review takes one slot for each of its reviewers that runs at once
- a reviewer of a plan, such as the critic that batch planning calls
- each fixer the agent's run starts after a merge
- a lead's helper, and each subagent the helper starts
- a subagent the agent resumes by messaging (DEC-081 point 2)

The pace is the session's, not each agent's. A lead's helper acts as the lead's instance (DEC-059 point 6), so the subagents it starts share the lead's slots.

A Task that waits on its checks, on its verdicts being posted, on a person or on a question runs no subagent, so it holds no slot. A Task a person directs to be built in the seat's own session, where no builder can start (DEC-063 point 1), runs no subagent either. It is built there alone, and the seat starts no other build until it ends.

### 3. The harness and the work bound every pace

- **A pace is a ceiling, never a demand.** Where the harness limits how many subagents, or commands in the background, a session runs together, the agent starts none past that limit. `max`, and a number above the limit, run at the harness's limit, which is no error.
- **Only what the work calls for.** With nothing waiting and no Task that nothing blocks, slots stay free.
- **No other limit.** This capability sets no number of its own above the harness's limit and the work's.

### 4. Work in flight comes first, then a named Task, then new work

Whenever a slot frees, and at the start of each round of its loop, the agent fills its free slots in this order, without being told:

1. **What its work in flight waits for:** a review whose checks have passed (DEC-063 point 8), a fix round on a verdict that asks for changes, a build that merges the base into a Task's branch, and a build resumed once its question is answered. Each starts in the order it came to wait.
2. **Then a Task a directive named** (DEC-081 point 6), one for each slot still free, in the order the directives came.
3. **Then new Tasks,** each the next that nothing blocks (point 5), one for each slot still free.

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
- **What it sets:** `off`, a number or `max`, or it clears its own setting. The command refuses a value past the ceiling, and, from a directing seat, a value past a person's setting that stands.
- **Where it lives.** The pace is shared state that changes while agents work, with no review of each change. So it lives on the seat's state issue, as [project-management:DEC-058-state-issues] point 1 has such state live, found by the number the topology names. It is a part of the seat's state, folded apart from its holder (DEC-058 points 2 and 5, refined in place). Each setting is an event of its own in the issue's comment log, naming its setter: the directing seat and its clone's key, or a person.
- **The fold.** A setting counts only where its author may write (DEC-058 point 4).
  - A person's setting stands until a person clears it or sets another.
  - The directing seat's last setting counts while the topology on the default branch names its setter as the worker's directing seat. A setting from any other seat counts for nothing.
  - The fold reads the worker's state issue alone, and its caller, which reads the topology, gives it the directing seat. So no fold of one seat's state reads another's.
  - A setting belongs to the seat, not to a clone, so a release of either seat leaves it standing.
- **The lowest binds, at every read.** A seat runs at the lowest of the ceiling, the person's setting and its directing seat's, each where it counts. So a lower ceiling binds every seat at once, a directing seat only ever lowers a person's pace, and a seat with no setting that counts runs at the ceiling.
- **A change of directing seat.** A directing seat the topology no longer names stops counting at the next read, so its worker rises to the person's setting or to the ceiling. That change is a reviewed merge a person authorised, and a person who wants a lower pace to outlast it sets that pace as theirs.
- **A guard, no boundary.** Like a claim on a state issue, a setting catches the mistakes of clones that follow the procedure (DEC-058 point 5). Where every clone works under one account, nothing proves who wrote it.

### 7. A seat reads its pace before each subagent it starts, and the commands hold to it

- **When it reads.** A seat reads its pace from its state issue at each round of its loop and before each subagent it starts. The build and review commands read it themselves, in the read that confirms the seat (DEC-059 point 6). Before a dispatch through the harness's tools, the agent reads it with a command that shows its seat's state.
- **The register.** Each run a command of this capability starts is entered, while it runs, in a register the clone keeps and never commits. So a later session in the clone counts what an earlier one left running.
- **The commands hold to it.** The build command and the review command read the pace and the register before they start a run, and start none past the pace, nor past the cap the agent passes them (point 4). The drift command runs its fixers within the cap the agent passes it, and enters them in the register.
- **A known gap.** A subagent the agent starts through the harness's tools passes no command of this capability, so the pace binds it only as the agent's own step: the agent counts it, and passes each command its free slots with it counted.
- **No message carries a pace.** A directive that names no Task (DEC-081 points 1 and 8) may wake the worker to read its state issue, and passes DEC-081 point 5's check as any directive does. The worker acts on what it reads there, never on a value a message states, and answers with the pace it read (point 10). A worker that no message reaches finds the change at its next read.
- **A setting that does not read** counts for nothing, and the worker says it found one. Where the seat cannot be confirmed, the command refuses, as DEC-059 point 6 says, and nothing new starts.

### 8. A session with no seat runs at the ceiling, or lower on the person's word

- **Its pace is the ceiling,** read as point 1 says. No state issue holds a pace for it, no seat directs it, and the commands hold it to the ceiling as they hold a seat to its pace.
- **The person directing the session may lower it** in words, for that session alone. The agent says the new pace back, and passes it as each command's cap. Nobody raises it past the ceiling in words: the agent names the setting, and the change to the configuration that would raise it.
- **Its pool is the work the person gave it,** such as a batch of Tasks. It keeps its slots full from that work as points 4 and 5 say, with no open dependency before a Task it takes. It takes nothing beyond that work unless the person says so, since a session with no seat acts on what the person asks of it ([project-management:DEC-029-project-manager-agent-shape]).

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

**Why `max` where it is absent.** Reviews run their whole set at once today, and a session that coordinates a batch dispatches builders together on the person's word. `max` keeps both, so a project that never chose loses no speed it has. What changes for it is the worker's loop, which fills its slots, as the maintainer decided. The cost is a worker that may run as many builds as its harness allows once the build lands, with what follows for money and for the person's reviews, so the build's changeset says so and names the setting that lowers it. `off` by default would turn every adopter's reviews serial, and stop a coordinator's builds at once, before anyone chose it. A small number by default would be a guess that fits no project in particular.

**Why every subagent counts alike, whatever starts it.** A builder, a reviewer, a fixer and a helper each take a run of the harness, with its cost and its capacity, and so does a resumed one. Counting builders only would let the reviews of a few Tasks, each with several reviewers, run far past what the person set. Counting the session's runs, not each agent's, keeps a lead's helpers within the pace the person set for the lead's seat.

**Why the pace bounds subagents, and not Tasks in flight.** What costs money and the harness's capacity is a run, and a Task that waits on its checks, a person or a question runs nothing. A bound on Tasks in flight would leave slots idle while Tasks wait, and a bound of one would stop the loop on each waiting Task. What a worker may take at all is the work the person scheduled into its pools, and a person who wants fewer Tasks waiting on them lowers the pace, or schedules less.

**Why the harness and the work bound `max`.** The harness knows how many runs it carries at once, and the work knows how many are worth starting. A number of the capability's own would be wrong on some harness. A number set above the harness's limit asks only for what the harness can give, so it is no error.

**Why work in flight first, then a named Task.** A review is the step that brings a built Task to its merge. A new build that took its slot would make a finished Task wait for one that is only starting. Taking what waits first bounds the first review's wait to the end of one running subagent, and costs a new build only that review's time. A Task a directive named comes before the nearness order, since the directing seat named it for a sequence that order does not show (DEC-081, "Why a directive may reorder"). A slot kept for reviews would sit empty where none waits, and at `off` would leave none for building.

**Why nearest the work just done.** The Tasks of one Feature finish one outcome, which the person scheduled together, and taking them first closes the Feature sooner. Two costs follow. A Task of higher priority elsewhere waits until the nearer Tasks are taken, which overturns DEC-059's priority first where a Task's work freed the slot. And sibling Tasks in flight together are the likeliest to touch one file their implementation notes missed, as the wave of pull requests DEC-066 records did, which the merge then settles at the cost of another round of review.

**Why a shared file rides the dependencies.** DEC-066 point 1 has the later of two Tasks that share a file name the earlier among its dependencies, so the one reckoning of ready work already holds it back. Reading the implementation notes of every Task in flight at each take would reckon readiness from the code a second way, which DEC-025 leaves to lanes until lived evidence settles them. Builds run at once give that evidence, and the merge settles any other overlap.

**Why a waiting Task holds no slot.** A question waits on a person, who may answer hours later. A slot it held would sit idle, and at `off` it would stop the seat's whole loop on one Task. The Task keeps its claim, so no other agent takes it (DEC-063 point 6), and the person answers in their own time.

**Why the state issue carries the pace, and a message only points.** The pace changes while the work goes on, with no review of each change, and belongs to one seat. That is what a state issue holds (DEC-058 point 1). Its comment log keeps who set what and when, every clone reads the same value, and the worker reads it in a read it makes anyway. A message can be lost or delayed, its sender cannot be proven, and a harness may carry none. A value in a message would be a second source that drifts from the first. A pointer that is lost costs only the time until the worker's next read.

**Why the directing seat may set the pace.** DEC-081 gives a worker one directing seat, named in the reviewed topology, which may already decide the order of the worker's Tasks. How many the worker runs at once is part of the same directing, so the same seat sets it, and the setter stays plain. The person directs a planner's or a lead's seat, and sets its pace directly.

**Why a person's setting outranks the directing seat's.** A seat directs a worker within what the person decides (DEC-081 point 6), so the person's pace is a bound the seat works under, not a value it replaces. A setting that lasts until a person clears it is one the person can rely on, whoever directs the worker later.

**Why a setting is the seat's, and the lowest binds at every read.** A directing seat's setting that counted only while its setter's clone held the seat would lapse whenever a lead's session ended, and its workers would rise with nobody choosing it. Counted by the seat the topology names, it stands until someone with the right changes it, and counts for nothing where the topology does not grant that right. Taking the lowest at each read makes a lowered ceiling, or a person's setting, bind at once, with no write to any other setting.

**Why the commands hold to the pace.** A pace that rests on the agent counting its own runs leaves the limit to the agent that would lose count, as DEC-063's "Why a mechanism, not an instruction" says of the clean start. The build and review commands start most of a seat's runs, so their reading of the pace and of the clone's register makes the pace hold for those runs, and for a later session that finds runs an earlier one left. A dispatch through the harness's tools passes no command, so for it the pace stays the agent's step, named as the gap it is.

**Why a lowered pace stops nothing.** A builder stopped in its run loses its work and leaves its clone half built, and a reviewer stopped posts no verdict, so its review runs again. Finishing what runs costs at most the length of the runs in flight.

**Why a session with no seat runs at the ceiling.** It has no state issue and no directing seat, so the committed value is all it has, and the person who directs it is there to lower it. Raising it past the ceiling in words would let one session's word outrank the reviewed value, which holds for every session alike. Taking only the work it was given keeps it off work that another person or session may hold.

**Why tell the person once.** The person should know what runs on their behalf, and at what cost, without a line at each start. One line before the first subagent, and one at each change, says it where the person reads the session.

### Alternatives considered

- **`off` where the key is absent.** Rejected, as "Why `max` where it is absent" says: every adopter's reviews would run one reviewer at a time, before anyone chose it.
- **A small number by default, such as three.** Rejected, as "Why `max` where it is absent" says.
- **A cap of the capability's own on `max`.** Rejected, as "Why the harness and the work bound `max`" says.
- **The ceiling in the topology.** Rejected: a session with no seat, and a project with no topology, would have none, and each new key of the topology waits until every clone reads it (DEC-061 point 9).
- **The ceiling read from the working tree.** Rejected: a branch the agent works on could raise its own pace.
- **Count builders only.** Rejected, as "Why every subagent counts alike" says.
- **Count each agent's subagents apart, a helper's against a pace of its own.** Rejected: a lead at a pace of three, with three helpers each running a review of three, would run a dozen at once.
- **Bound Tasks in flight too.** Not taken, as "Why the pace bounds subagents, and not Tasks in flight" says.
- **A slot kept for reviews.** Rejected, as "Why work in flight first" says.
- **A review that waits for a slot for each of its reviewers.** Rejected: at a low pace, a review with many reviewers would wait for every build to end.
- **The highest priority first, whatever the work just done.** Not the maintainer's decision. A seat's work would scatter across Features, and each would close later.
- **A named Task after the nearness order.** Rejected: the directing seat named it for a sequence the order does not show.
- **Read the implementation notes of every Task in flight at each take.** Not taken, as "Why a shared file rides the dependencies" says. The record that builds lanes may refine point 5.
- **A waiting Task that holds its slot, or ends the loop.** Rejected, as "Why a waiting Task holds no slot" says.
- **A state issue of its own for each seat's pace.** Rejected: a second issue to create, name and find for every seat, where the seat's own already holds its state.
- **The pace carried in the message.** Rejected, as "Why the state issue carries the pace, and a message only points" says.
- **The last setting counts, whoever wrote it.** Rejected, as "Why a person's setting outranks the directing seat's" says: a lead's later setting would replace the person's without a word.
- **A setting that counts only while its setter's clone holds the directing seat.** Rejected, as "Why a setting is the seat's" says.
- **The pace held by the agent's own count alone.** Rejected, as "Why the commands hold to the pace" says.
- **Stop the newest runs when the pace is lowered.** Rejected, as "Why a lowered pace stops nothing" says.
- **The person's word raises a session's pace past the ceiling, with a warning.** Rejected: one session's word would outrank the reviewed value, which holds for every session alike.
- **Tell the person at each start, or never.** Rejected: a line at each start buries the work, and silence hides what runs on the person's behalf.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([pkit:COR-066] point 5), sorted by kind and then by record:
  - **Overturned in part.** Each record stays accepted, and its overturned words stay as they stood.
    - DEC-059's top line, which names DEC-061, names this record too, in one paragraph. DEC-061's sentences stay, but "Among what stands: all of this record in a project with no pools" reads "Among what stands: all of this record in a project with no pools, as far as DEC-061 goes". The line adds: "Whenever a Task's work frees a slot of a seat, the seat's ready Tasks rank nearest that Task first: those of its Feature, then its EPIC, then its Milestone, then the rest, by priority within each. Overturned there by DEC-082: point 7's 'the highest in priority first', where a Task's work freed the slot. Priority alone orders the Tasks where no Task's work freed the slot."
    - DEC-061 gains a top line that reads: "Partially superseded by DEC-082. Whenever a Task's work frees a slot of a seat, the ready Tasks of its pools rank nearest that Task first: those of its Feature, then its EPIC, then its Milestone, then the rest, by priority within each. Overturned: point 5's 'the Tasks rank as there', so far as it ranks them by priority alone. The rest stands."
  - **Refined in place,** each with a forward refinement pointer to this record:
    - DEC-058 point 2, completed: one piece of state may hold parts, each folded apart under the piece's one key, such as a seat's holder and its pace, and the record that adds a part says how it folds.
    - DEC-058 point 5, completed: the holder's release frees the holding, and the record that adds another part says whether a release clears it.
    - DEC-059 point 2, widened: a worker builds and reviews as many Tasks at once as its pace allows.
    - DEC-059 point 3, completed: the seat's state issue keeps the seat's pace too, folded apart from its holder.
    - DEC-063 point 1, completed: where no builder can start, the seat starts no other build, and its loop ends once the subagents it runs have ended. A Task the person directs to be built in the seat's session is built there alone.
    - DEC-063 point 6, widened: "The seat tells the person, and ends the loop" reads that the seat tells the person, and goes on with its other work within its pace.
  - **A fact corrected,** with no pointer, since no decision changes: DEC-063's Implications' "Named, not built" drops a seat taking other work while a question waits, which this record decides.
- **Architecture records,** which the architect authors in this change once this record is accepted, under the maintainer's sign-off on it:
  - **ADR-073, overturned in part by a new record:** its one build at a time in a seat's clone, and exit 1's "a build already running", narrowed to a build of the same Task. The new record decides a state file for each build, keyed by its Task, recovery over each build, fetches, signing and hand-backs that run at once in one clone, and the register of runs and how the build and review commands read it (point 7). It lands before the build command is built (#2287), so that the command is not built for one build at a time.
  - **ADR-071, refined in place** for the pace ([pkit:ADR-071]): point 4's fold returns the person's setting and the directing seat's beside the holder, point 5's payload names a setting's setter, point 7's caller passes the directing seat from the topology, and point 8's count of a seat's log grows by one comment for each setting.
- **What stands:**
  - DEC-025's one reckoning of ready work, which ranks nothing. The nearness order is an option the build adds to the take (point 5).
  - DEC-029's reviewer threshold and dispatch discipline, whose dispatches each take a slot
  - DEC-066's order of Tasks that share a file, and its fold
  - DEC-081 point 1, under which a pointer to a new pace is a directive that only wakes, and point 5, its check
  - [pkit:ADR-072]'s pool lookup, whose take gains as an input the Task whose work freed the slot
- **A build Task** brings, after DEC-081's build, which brings the directing seat to the topology:
  - the configuration key and its schema
  - the pace's events on a seat's state issue, their fold, and the command that sets or clears a pace
  - an option of the take to rank the Tasks nearest a given Task first
  - the register of runs, and the build and review commands holding to the pace
  - the agent passing each command that starts subagents its free slots as the cap
  - the steps of the agent's definition and of the pm skill's work loop and batch plan
  - the capability's README, where seats, the work loop, the configuration and the review command's cap are described, and the agent's storyboard, with a worker that runs several builds at once
- **What the build changes for every adopter,** which its `minor` changeset declares: a worker keeps several Tasks in flight at any pace, where it took a new one only once nothing was in flight; it takes the Tasks nearest the work just done first; the review and drift commands run at most the slots free when the agent starts them; and a project that sets no ceiling runs at `max`.
- **Acceptance:** this record overturns the accepted DEC-059 and DEC-061 in part, and refines DEC-058, DEC-059 and DEC-063 in place, so accepting it needs the maintainer's sign-off, which covers the two architecture records above. It rests on DEC-081, accepted with it in this change, for the directing seat (point 6) and the directive that wakes (point 7). Refusing DEC-081 leaves point 6 with no directing seat, so this record is then revised to decide one of its own, or waits.
- **No behaviour changes** until the build, so the record lands with a `none` changeset.
