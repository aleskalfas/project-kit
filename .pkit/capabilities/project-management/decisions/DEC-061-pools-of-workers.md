---
id: DEC-061
title: Pools of workers — seats that build choose their work only from the pools they serve
status: proposed
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a project's topology may declare **pools of workers**. Each seat that builds names the pools it serves. A person puts a line of work into a pool by marking its Milestone with the pool's name, and a worker chooses its next Task only from ready Tasks whose Milestone is in one of its pools. So several planners can each run a line of work, and a person decides how many workers each line gets. Starting or finishing a line changes no committed configuration. Where the topology declares no pool, every seat takes from the one shared pool of [project-management:DEC-059-topology-of-seats]. And every topology, with pools or without, now grants nothing to code that cannot read it in full, which changes DEC-059 point 1.

## Context

[project-management:DEC-059-topology-of-seats] has every seat that builds take ready work from one pool that all seats share. A seat's scope narrows its own seat's work and reserves nothing (point 7). So any worker may take any ready Task in Backlog. A person can neither hold work back from the workers nor give one line of work more of them than another.

On 28 October the maintainer set four needs for running agents in parallel (#2256). A *line of work* is the work a person schedules into one Milestone.

1. Workers take only what a person put into their pool.
2. Several planners work at once, each on its own line of work.
3. Finishing a line of work, or starting one, changes no committed configuration.
4. A person controls capacity: more workers on what matters most, one on housekeeping.

A seat's scope that named Milestones would meet the first need, but each new line of work would then be a reviewed change to the topology, against the third ("Alternatives considered"). The maintainer decided pools, after a critic's and an architect's review. This record holds that decision.

## Decision

**A project's topology may declare pools of workers, and each seat that builds names the pools it serves. A person puts a Milestone into a pool by a line in its description, and each Task in the Milestone goes with it. A seat that builds chooses its work only from ready Tasks in an open Milestone of a pool it serves. Where no pool is declared, DEC-059's one shared pool stands.**

### 1. The topology declares pools, and each seat that builds names those it serves

- **The pools.** The topology may declare a list of pools, each by a neutral name, such as `alpha`. The name says nothing of the work, since what a pool holds changes as its lines of work start and finish. A pool's name never changes, as a seat's never does ([project-management:DEC-059-topology-of-seats] point 2). The list's presence declares pools, so where it is empty, the seats that build take nothing of their own choosing (point 8).
- **Retiring a pool, or every pool.** A pool is retired by removing it from each seat's pools, and then its name from the list. Its open Milestones then fall into no pool, with a warning (point 2). A project goes back to the one shared pool by removing the list from the topology and the pools from every seat.
- **A seat that builds,** a worker or a lead, names the pools it serves. Point 8 says what a seat that names none takes.
- **A planner names no pool,** and the topology's check refuses a planner's seat that names one (point 10). It files into the Milestones the person gives it. So several planners can each run a line of work at once, each in a seat of its own (DEC-059 point 4). Only what the person gives each planner keeps them apart, and no part of the topology does.
- **A pool is no part of a scope.** A pool reserves its work for the seats that serve it, and a scope narrows its own seat's work and reserves nothing (DEC-059 point 7). A seat's scope narrows what its pools hold.
- **Capacity moves through review.** Moving workers from one pool to another is an edit of the seats' pools, a reviewed change to the topology like any other (DEC-059 point 1).

### 2. A Milestone joins a pool by a line in its description

A Milestone's description puts the Milestone into a pool with a line `Pool: <name>`, beside its `Close trigger:` and `Rollforward target:` lines ([project-management:DEC-016-time-bound-containers]). The line is read as a whole line wherever it stands, and is never required first. A Milestone with no such line is in no pool.

- **Each `Pool:` line counts.** Every line that opens with `Pool:` counts, well formed or not. Two such lines, a malformed one, or one naming a pool the topology does not declare, put the Milestone in no pool, with a warning.
- **A change replaces the line.** A change of the Milestone's pool replaces its line, and never adds a second. The record of the change's consent, which point 6 keeps in the description, never takes the `Pool:` form.

### 3. A Milestone's pool lives on the Milestone

- **Where it lives.** A Milestone's pool is an attribute of the Milestone, the top item of the hierarchy of work ([project-management:DEC-004-six-level-hierarchy]), and a reader finds it in the repository's open Milestones. [project-management:DEC-058-state-issues] point 1 keeps in a state issue "shared data that changes while agents work, with no review of each change, and that belongs to no issue of work". The pool changes only by a person's act of scheduling, and belongs to an item of work as an issue's owner belongs to its issue. So it is neither a state issue's nor committed configuration.
- **Written whole.** A Milestone's description is written whole: its writer reads it, changes it and writes it back. So two writes at once can lose one change. That is rare, since a person paces these writes, and the writer reads the description again right before it writes.
- **Outside review on purpose.** The topology says which seats serve each pool, and the Milestones say what each pool holds. So a line of work starts and finishes with no change to the topology (need 3).
- **A guard, no boundary.** Like the guard on a claim of a state issue (DEC-058 point 5), the pools catch the mistakes of clones that follow the procedure. They are no security boundary.

### 4. A Task is in the pool of its Milestone

A Task's Milestone is its native Milestone field ([project-management:DEC-005-linking-and-containment]), never the `Milestone:` line of its body, which links a parent. An issue is in at most one Milestone ([project-management:DEC-016-time-bound-containers]), so a Task is in at most one pool. A pool holds the lines of work of its open Milestones: a line finishes when its Milestone closes, and a new line starts with a new Milestone marked with the pool. A Task in no Milestone, in a closed one, or in one of no pool, is in no pool.

### 5. A seat that builds chooses its work only from its pools

Where the topology declares pools, a seat that builds chooses a ready Task only where the Task's Milestone is an open Milestone of a pool it serves. A ready Task is what DEC-059 point 7 says, and the Tasks rank as there. The seat's scope then narrows what its pools hold.

- **What the pools bound.** They bound what a seat takes of its own choosing, its next ready Task. A person who directs a seat to a particular Task makes that choice, and the seat takes it. The take makes its own check of the Task's pool against the seat's pools, and warns of a Task outside them: a warning, never a gate ([project-management:DEC-045-named-per-user-instances] point 5).
- **The seat's own Tasks.** The pools hold back a Task in Backlog that the seat owns, such as one whose Milestone moved to another pool, and the listing of seats warns of it (point 10). A Task In Progress whose Milestone moved to another pool stays its holder's to finish.

The expected owner of a Task is the seat that alone may take it, by its pools and then its scope. It replaces DEC-059 point 7's expected owner, as "What this overturns, and what stands" says.

### 6. Putting work into a pool is the person's act

- **What asks.** Marking a Milestone with a pool, or changing or clearing its pool, asks the person. So does each write that brings a Task into a pool, or moves a Task from one pool to another.
- **What asks nothing.** A write that takes a Task out of a pool, to no Milestone or to a Milestone in no pool, narrows what workers may take, so it asks nothing. Neither does a move between two Milestones of one pool, nor the rollforward of a close the person authorised (point 7).
- **How it asks.** The person answers at a terminal, or the command runs with its consent flag, given only on the person's word. Off a terminal without that flag, the write is refused. It is a held act, like the moves the user authorises at hard-reject severity ([project-management:DEC-006-state-machine-and-cascade]), and never bypassed with an audit. An agent never gives the person's word for itself.
- **Where the consent is logged.** A write that sets a Task's Milestone records the consent in the Task's own audit comment. A change of a Milestone's pool records it in the Milestone's description, since a Milestone holds no comments.
- **A plan's approval.** A planner that files the Tasks of an approved plan has the person's word for their pools only where the plan shown at the approval gate of [project-management:DEC-029-project-manager-agent-shape] names each Task's Milestone and that Milestone's pool.

### 7. Closing a Milestone rolls its open Tasks forward within its pool

Where the topology declares pools, and neither a closing Milestone's description nor its close names a rollforward target, its open Tasks roll forward within its pool ([project-management:DEC-016-time-bound-containers], refined in place). A Milestone in a pool rolls them to the next open Milestone of its category in the same pool, and a Milestone in no pool to the next open one of its category in no pool. The next is counted by the number in the Milestone's title, which each category numbers apart (DEC-016), never by the number GitHub gives the Milestone. The person is asked where there is none, or more than one.

- **A target in another pool.** The description's `Rollforward target:` line, or a target the close names, may name a Milestone in another pool. The close's consent prompt then names that target and its pool, so the person's consent to the close covers the move.
- **A forced close.** A close forced past the open children that would otherwise hold it leaves them on the closed Milestone, where they are in no pool (point 4). The close reports each Task it so leaves in no pool, in Backlog or In Progress.

### 8. Without pools the shared pool stands, and with them a failure takes nothing

- **No pools declared:** DEC-059's one shared pool, with the move to Backlog as the gate ([project-management:DEC-006-state-machine-and-cascade]).
- **Pools declared:** a seat that builds and names no pool takes nothing of its own choosing.
- **Milestones that cannot be read:** the seat takes nothing, and never falls back to the whole Backlog.
- **Saying why:** where nothing is ready, the seat says why in terms of its pools, such as a pool with no open Milestone.

### 9. Code that cannot read the topology in full uses none of the authority it grants

- **What it cannot read:**
  - a key it does not know, at any depth
  - a value of a known key that it cannot read, such as a list written as a string, an unknown role or release mode, or an unknown version of the topology's schema
- **What refuses:** each command that would use authority the topology grants, so such code takes no work, no seat and no release by force. A listing, such as that of the seats, warns. Work already in flight goes on, such as renewing a claim, or reviewing and finishing a change.
- **Why it fails closed:** an ignored key could widen what an agent takes of its own choosing, as an ignored pool would. So the topology fails closed, unlike the backbone configuration's forgiving read ([pkit:COR-048] point 4).
- **The order of work, kept by the operator.** The guard protects only the commands run from a checkout that holds it, and whether one holds it is a property of each checkout, not of a clone. So pools enter a project's topology only once every clone that may take a seat runs its taking commands from a checkout at or past the change that brings the guard. Code older than that ignores the pools, and its seat would choose from the whole Backlog. Each later addition to the topology's shape enters once those checkouts read it, since one that cannot takes no work.
- **No check yet.** No check enforces this order: it is the operator's discipline. A version of the code stamped in each claim is one possible check, named here and not decided.

### 10. The check refuses an undeclared pool, and the listings warn of stranded work

- **The topology's check** refuses a seat that names a pool the topology does not declare, a seat that names pools where the topology declares none, and a planner's seat that names any pool.
- **The listing of seats, and taking a seat,** show each pool's open Milestones, each by the number GitHub gives it and its title.
- **They warn of work left stranded:** a pool no seat serves, a pool with no open Milestone, a seat that builds and names no pool, and a Milestone that names an undeclared pool.
- **The listing of seats counts the Tasks in no pool.** It reports how many Tasks in Backlog are in no pool, such as those a forced close left (point 7), as a count rather than each Task.
- **The listing of seats counts the Tasks a seat owns outside its pools.** For each seat, it warns with a count of the Tasks in Backlog that the seat owns and its pools hold back from it (point 5). The owner releases each such Task, so that a seat that serves its pool may take it.

### What this overturns, and what stands

This record partially supersedes DEC-059, for a project whose topology declares pools. Each overturned passage stays in DEC-059 as it stood.

- **Overturned in DEC-059:**
  - the one pool that every seat shares, in the title, the summary, the Decision's headline, and point 7's title and opening sentence. Each seat that builds takes from its own pools (point 5 here).
  - in point 7, the bullets "Who may take a Task", with its "Several seats that may take one workstream are the shared pool", and "The expected owner". In their place, a seat that builds takes of its own choosing only from the pools it serves, and the expected owner is reckoned by its pools, then its scope (point 5 here).
  - the Rationale's "Why one shared pool, and vertical slices", where it defends one pool, its "no routing to keep up" included. The Milestones route the work to its pool (point 2 here).
  - the rejected alternative "A scope that reserves its work for its seat", where it rejects work reserved for some seats. A pool reserves its work for the seats that serve it, and a scope still reserves nothing (point 1 here).
- **Stands in DEC-059:**
  - all of it, in a project whose topology declares no pool (point 8 here)
  - the seats, their roles, state issues and names, taking and releasing a seat, a clone's identity and a Task's claim (points 2 to 6, 8 and 9)
  - in point 7: what makes a Task ready, the vertical slices, the planner that files with no owner, a scope that narrows its own seat's work and reserves nothing, and, from the bullet "Who may take a Task", the warning of a workstream that no seat may take
  - the Rationale's case for vertical slices
- **Refined in place:**
  - DEC-059's summary, points 1 and 2, and its Implications' "No mesh interaction", where the shared pool is the repository's own
  - DEC-016's Milestone description and rollforward, and DEC-006's scheduling gate
  - DEC-025's summary, the Decision's headline, the "Readiness in sequence" row of its design at a glance, and "Readiness is reckoned once", where a project with pools routes readiness through each seat's pools
  - DEC-025's preamble to its open questions, and question 7, which a topology settles whether it declares pools or not
- **Unchanged:** DEC-045 and DEC-004.

## Rationale

**Why pools.** One shared pool hands any worker any ready Task. Pools let a person decide what each worker may take, and how many workers each line of work gets (needs 1 and 4). A seat's pools change through review, as its other parts do, and what each pool holds changes with the Milestones.

**Why a Milestone carries the pool.** Lines of work start and finish often, and a reviewed change to the topology each time would slow every one of them (need 3). A Milestone already holds each issue a person schedules into it, one Milestone for each issue ([project-management:DEC-016-time-bound-containers]). So marking one Milestone puts every Task of its line into the pool, with no marker on each Task.

**Why the native Milestone field.** The `Milestone:` line of an issue's body links a parent, and an issue whose parent is no Milestone has none ([project-management:DEC-004-six-level-hierarchy]). The native field holds every issue's one Milestone, so a Task's pool is never in doubt.

**Why a pool stands apart from a scope.** A scope narrows its own seat, so the other seats keep all the work (DEC-059 point 7). A pool reserves work for the seats that serve it. Kept apart, each stays one thing: a seat's pools say what it may take, and its scope narrows that.

**Why the person puts work into a pool.** Scheduling work is the person's commitment ([project-management:DEC-006-state-machine-and-cascade]), and a pool decides which workers build it. The gate lies outside reviewed configuration so that lines of work come and go with no review, and the person's consent at each write takes the place of review. Taking a Task out of a pool only narrows what workers may take, so it needs no consent. Clearing a Milestone's pool narrows too, yet it asks, since the `Pool:` line stays the person's own to write.

**Why a failure takes nothing.** A seat that fell back to the whole Backlog, where the Milestones could not be read, would take work no person put into its pool. Taking nothing costs a pause, and a later read takes the work up.

**Why the guard fails closed.** The backbone's configuration is forgiving when read, since a typo there blocks no ordinary work ([pkit:COR-048] point 4). The topology grants authority instead. Code that ignored a seat's pools would let that seat choose from the whole Backlog, the very work the pools hold back from it.

**Why rollforward stays in the pool.** Rolling a closing Milestone's open Tasks into another pool's Milestone would hand them to other workers, with no act of the person. Rolling them to the next Milestone of its category in its own pool keeps them with their workers. A target in another pool is the person's to approve, so the close's consent prompt names it.

**Why pools are optional.** Pools need Milestones, and a feature-driven flat project runs none ([project-management:DEC-016-time-bound-containers]). So pools apply only where a project declares them, and a project with none keeps the shared pool ([pkit:COR-014]).

### Alternatives considered

- **A seat's scope that names Milestones.** Rejected: each new line of work is a reviewed change to the topology (need 3). A scope also reserves nothing, so seats with no scope still take the line's work.
- **A pool named on each Task.** Rejected: a person would mark every Task rather than one Milestone, and a Task's pool could drift from its Milestone's.
- **The topology maps Milestones to pools.** Rejected: a change to the topology each time a line of work starts or finishes (need 3).
- **A state issue that lists each pool's Milestones.** Rejected: the pool is an attribute of the Milestone, an item of the hierarchy of work, and a state issue sits outside that hierarchy ([project-management:DEC-058-state-issues] point 3).
- **Fall back to the whole Backlog where the Milestones cannot be read.** Rejected, as "Why a failure takes nothing" says.
- **Warn only, on a topology the code cannot read in full.** Rejected, as "Why the guard fails closed" says.

## Implications

- **The topology's schema** gains the pools and each seat's pools, under its present schema version. It is a pure addition, so no migration ships ([pkit:COR-010]).
- **A Milestone's description** gains the `Pool:` line, declared with the close trigger's grammar in the capability's schema for time containers. One reader parses it, beside the close trigger's.
- **Commands.** Creating a Milestone may name its pool, and a command of its own sets or clears a Milestone's pool. The writes that set a Task's Milestone ask the person where point 6 says. Closing a Milestone rolls within its pool, names a target in another pool in its consent prompt, and reports the Tasks a forced close leaves in no pool (point 7). Taking the next Task, the listing of seats, taking a seat and the topology's check do what points 5, 9 and 10 say.
- **The pm skill's** work loop and batch plan say which Milestones a planner files into, and that a worker chooses its work only from its pools.
- **An architecture record.** The maintainer's sign-off on this record covers an architecture record on the pool lookup's boundaries, the guard's placement and the failure behaviour, and the rewording of "the shared pool" in [pkit:ADR-041]. The architect authors both in this change, once this record is accepted.
- **A project adds pools to its topology** only once every clone that may take a seat runs its taking commands from a checkout at or past the change that brings the guard, a discipline no check enforces yet (point 9).
- **The changeset** of the build declares that a topology key the code does not know now refuses rather than warns, for every adopter with a topology. The release notes carry the order of work that point 9 sets.
- **Acceptance:** this record partially supersedes the accepted DEC-059, and refines it, DEC-016, DEC-006 and DEC-025 in place, so accepting it needs the maintainer's sign-off. The refinements land only with this record accepted.
