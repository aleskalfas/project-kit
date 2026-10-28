---
id: DEC-061
title: Pools of workers — seats that build take only from the pools they serve
status: proposed
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a project's topology may declare **pools of workers**. Each seat that builds names the pools it serves. A person puts a line of work into a pool by marking its Milestone with the pool's name, and a worker takes only ready Tasks whose Milestone is in one of its pools. So several planners can each run a line of work, and a person decides how many workers each line gets. Starting or finishing a line changes no committed configuration. Where the topology declares no pool, every seat takes from the one shared pool of [project-management:DEC-059-topology-of-seats].

## Context

[project-management:DEC-059-topology-of-seats] has every seat that builds take ready work from one pool that all seats share. A seat's scope narrows its own seat's work and reserves nothing (point 7). So any worker may take any ready Task in Backlog. A person can neither hold work back from the workers nor give one line of work more of them than another.

On 28 October the maintainer set four needs for running agents in parallel (#2256). A *line of work* is the work a person schedules into one Milestone.

1. Workers take only what a person put into their pool.
2. Several planners work at once, each on its own line of work.
3. Finishing a line of work, or starting one, changes no committed configuration.
4. A person controls capacity: more workers on what matters most, one on housekeeping.

A seat's scope that named Milestones met the first need, but each new line of work would then be a reviewed change to the topology, against the third. The maintainer decided pools in its place, after a critic's and an architect's review. This record holds that decision.

## Decision

**A project's topology may declare pools of workers, and each seat that builds names the pools it serves. A person puts a Milestone into a pool by a line in its description, and each Task in the Milestone goes with it. A seat that builds takes only ready Tasks in an open Milestone of a pool it serves. Where no pool is declared, DEC-059's one shared pool stands.**

### 1. The topology declares pools, and each seat that builds names those it serves

- **The pools.** The topology may declare a list of pools, each by a neutral name. A pool's name never changes, as a seat's never does ([project-management:DEC-059-topology-of-seats] point 2).
- **A seat that builds,** a worker or a lead, names the pools it serves. Point 8 says what a seat that names none takes.
- **A planner names no pool.** It files into the Milestones the person gives its line of work. So several planners can each run a line at once, each in a seat of its own (DEC-059 point 4).
- **A pool is no part of a scope.** A pool reserves its work for the seats that serve it, and a scope narrows its own seat's work and reserves nothing (DEC-059 point 7). A seat's scope narrows what its pools hold.
- **Capacity moves through review.** Moving workers from one pool to another is an edit of the seats' pools, a reviewed change to the topology like any other (DEC-059 point 1).

### 2. A Milestone joins a pool by a line in its description

A Milestone's description puts the Milestone into a pool with a line `Pool: <name>`, beside its `Close trigger:` and `Rollforward target:` lines ([project-management:DEC-016-time-bound-containers]). The line is read as a whole line wherever it stands, and is never required first. A description with two such lines, or one naming a pool the topology does not declare, puts the Milestone in no pool, with a warning. A Milestone with no such line is in no pool.

### 3. A Milestone's pool lives on the Milestone

- **Where it lives.** A Milestone's pool is neither committed configuration nor a state issue ([project-management:DEC-058-state-issues] point 1). It is an attribute of a container of work, written by a person's act of scheduling, as an issue's owner lives on the issue. A reader finds it in the repository's open Milestones.
- **Outside review on purpose.** The topology says which seats serve each pool, and the Milestones say what each pool holds. So a line of work starts and finishes with no change to the topology (need 3).
- **A guard, no boundary.** Like the guard on a claim of a state issue (DEC-058 point 5), the pools catch the mistakes of clones that follow the procedure. They are no security boundary.

### 4. A Task is in the pool of its Milestone

A Task's Milestone is its native Milestone field ([project-management:DEC-005-linking-and-containment]), never the `Milestone:` line of its body, which links a parent. An issue is in at most one Milestone ([project-management:DEC-016-time-bound-containers]), so a Task is in at most one pool. A pool's lines of work are its open Milestones: a line finishes when its Milestone closes, and a new line is a new Milestone marked with the pool. A Task in no Milestone, in a closed one, or in one of no pool, is in no pool.

### 5. A seat that builds takes only from its pools

Where the topology declares pools, a seat that builds takes a ready Task only where the Task's Milestone is an open Milestone of a pool it serves. A ready Task is what DEC-059 point 7 says, and the Tasks rank as there. The seat's scope then narrows what its pools hold. The pools hold back the seat's own Tasks too, such as one it owns whose Milestone moved to another pool.

The expected owner of a Task is the seat that alone may take it, by its pools and then its scope (DEC-059 point 7, refined in place).

### 6. Putting work into a pool is the person's act

- **What asks.** Marking a Milestone with a pool, or changing or clearing its pool, asks the person. So does each write that puts a Task into a Milestone in a pool, or moves a Task from one pool to another.
- **How it asks.** The person answers at a terminal, or the command runs with its confirmation flag, given only on the person's word. An agent never gives that word for itself, as it never authorises a gate the person holds ([project-management:DEC-006-state-machine-and-cascade]).
- **The log.** A change of a Milestone's pool is logged in the Milestone's description, since a Milestone holds no comments.
- **What needs nothing new.** A move between two Milestones of one pool asks nothing new, and nor does the rollforward of a close the person authorised (point 7). A planner that files the Tasks of a plan the person approved has the person's word for their Milestones.

### 7. Closing a Milestone rolls its open Tasks forward within its pool

Where a closing Milestone is in a pool and its description names no rollforward target, its open Tasks roll forward to the next-numbered open Milestone of its category in the same pool ([project-management:DEC-016-time-bound-containers], refined in place). The person is asked where there is none, or more than one. A forced close that leaves Tasks in Backlog in no pool reports each of them.

### 8. Without pools the shared pool stands, and with them a failure takes nothing

- **No pools declared:** DEC-059's one shared pool, with the move to Backlog as the gate ([project-management:DEC-006-state-machine-and-cascade]).
- **Pools declared:** a seat that builds and names no pool takes nothing.
- **Milestones that cannot be read:** the seat takes nothing, and never falls back to the whole Backlog.
- **Saying why:** where nothing is ready, the seat says why in terms of its pools, such as a pool with no open Milestone.

### 9. Code that cannot read the topology in full uses none of the authority it grants

- **What it cannot read:** an unknown key at the top level or in a seat, an unknown value of a field with fixed choices, such as a seat's role, or an unknown version of the topology's schema.
- **What refuses:** each command that would use authority the topology grants, such as taking work, taking a seat or a release by force. A listing, such as that of the seats, warns. Work already in flight goes on, such as renewing a claim, or reviewing and finishing a change.
- **Why it fails closed:** an ignored key could widen what an agent may take, as an ignored pool would. So the topology fails closed, unlike the backbone configuration's forgiving read ([pkit:COR-048] point 4).
- **A standing rule.** The guard protects only clones that run it. So each addition to the topology's shape, pools the first, enters a project's topology only once every held seat's clone runs code that reads it.

### 10. The check refuses an undeclared pool, and the listings warn of stranded work

- **The topology's check** refuses a seat that names a pool the topology does not declare, and a seat that names pools where the topology declares none.
- **The listing of seats, and taking a seat,** show each pool's open Milestones, each by its number and title.
- **They warn of work left stranded:** a pool no seat serves, a pool with no open Milestone, a seat that builds and names no pool, a Milestone that names an undeclared pool, and Tasks in Backlog that a forced close left in no pool.

### What this overturns, and what stands

This record partially supersedes DEC-059, for a project whose topology declares pools. Each overturned passage stays in DEC-059 as it stood.

- **Overturned in DEC-059:**
  - the one pool that every seat shares, in the title, the summary, the Decision's headline, and point 7's title and opening sentence. Each seat that builds takes from its own pools (point 5 here).
  - the Rationale's "Why one shared pool, and vertical slices", where it defends one pool, its "no routing to keep up" included. The Milestones route the work to its pool (point 2 here).
  - the rejected alternative "A scope that reserves its work for its seat", where it rejects work reserved for some seats. A pool reserves its work for the seats that serve it, and a scope still reserves nothing (point 1 here).
- **Stands in DEC-059:**
  - all of it, in a project whose topology declares no pool (point 8 here)
  - the seats, their roles, state issues and names, taking and releasing a seat, a clone's identity and a Task's claim (points 2 to 6, 8 and 9)
  - in point 7: what makes a Task ready, the vertical slices, the planner that files with no owner, and a scope that narrows its own seat's work and reserves nothing
  - the Rationale's case for vertical slices
- **Refined in place:** DEC-059 points 1 and 7, DEC-016's Milestone description and rollforward, DEC-006's scheduling gate, and DEC-025's open question 7. DEC-045 and DEC-004 stand as they are.

## Rationale

**Why pools.** One shared pool hands any worker any ready Task. Pools let a person decide what each worker may take, and how many workers each line of work gets (needs 1 and 4). A seat's pools change through review, as its other parts do, and what each pool holds changes with the Milestones.

**Why a Milestone carries the pool.** Lines of work start and finish often, and a reviewed change to the topology each time would slow every one of them (need 3). A Milestone already holds each issue a person schedules into it, one Milestone for each issue ([project-management:DEC-016-time-bound-containers]). So marking one Milestone puts every Task of its line into the pool, with no marker on each Task.

**Why the native Milestone field.** The `Milestone:` line of an issue's body links a parent, and an issue whose parent is no Milestone has none ([project-management:DEC-004-six-level-hierarchy]). The native field holds every issue's one Milestone, so a Task's pool is never in doubt.

**Why a pool stands apart from a scope.** A scope narrows its own seat, so the other seats keep all the work (DEC-059 point 7). A pool reserves work for the seats that serve it. Kept apart, each stays one thing: a seat's pools say what it may take, and its scope narrows that.

**Why the person puts work into a pool.** Scheduling work is the person's commitment ([project-management:DEC-006-state-machine-and-cascade]), and a pool decides which workers build it. The gate lies outside reviewed configuration so that lines of work come and go with no review. So the person's consent at each write takes the place of review, and the Milestone's log shows each change of its pool.

**Why a failure takes nothing.** A seat that fell back to the whole Backlog, where the Milestones could not be read, would take work no person put into its pool. Taking nothing costs a pause, and a later read takes the work up.

**Why the guard fails closed.** The backbone's configuration is forgiving when read, since a typo there blocks no ordinary work ([pkit:COR-048] point 4). The topology grants authority instead. Code that ignored a seat's pools would let that seat take from the whole Backlog, the very work the pools hold back.

**Why rollforward stays in the pool.** Rolling a line of work into another pool's Milestone would hand its Tasks to other workers, with no act of the person. The next Milestone of its category in its own pool keeps the line with its workers.

**Why pools are optional.** Pools need Milestones, and a feature-driven flat project runs none ([project-management:DEC-016-time-bound-containers]). So pools apply only where a project declares them, and a project with none keeps the shared pool ([pkit:COR-014]).

### Alternatives considered

- **A seat's scope that names Milestones.** Rejected: each new line of work is a reviewed change to the topology (need 3). A scope also reserves nothing, so seats with no scope still take the line's work.
- **A pool named on each Task.** Rejected: a person would mark every Task rather than one Milestone, and a Task's pool could drift from its Milestone's.
- **The topology maps Milestones to pools.** Rejected: a change to the topology each time a line of work starts or finishes (need 3).
- **A state issue that lists each pool's Milestones.** Rejected: the pool belongs to a container of work, and a state issue holds only state that belongs to none (DEC-058 point 1).
- **Fall back to the whole Backlog where the Milestones cannot be read.** Rejected, as "Why a failure takes nothing" says.
- **Warn only, on a topology the code cannot read in full.** Rejected, as "Why the guard fails closed" says.

## Implications

- **The topology's schema** gains the pools and each seat's pools, under its present schema version. It is a pure addition, so no migration ships ([pkit:COR-010]).
- **A Milestone's description** gains the `Pool:` line, declared with the close trigger's grammar in the capability's schema for time containers. One reader parses it, beside the close trigger's.
- **Commands.** Creating a Milestone may name its pool, and a command of its own sets or clears a Milestone's pool. The writes that set a Task's Milestone ask the person where point 6 says. Taking the next Task, the listing of seats, taking a seat and the topology's check do what points 5, 9 and 10 say.
- **The pm skill's** work loop and batch plan say which Milestones a planner files into, and that a worker takes only from its pools.
- **An architecture record** follows this record's acceptance. The architect authors it on the pool lookup's boundaries, the guard's placement and the failure behaviour, and rewords "the shared pool" in [pkit:ADR-041].
- **A project adds pools to its topology** only once every held seat's clone runs code that reads them (point 9).
- **Acceptance:** this record partially supersedes the accepted DEC-059, and refines it, DEC-016, DEC-006 and DEC-025 in place, so accepting it needs the maintainer's sign-off. The refinements land only with this record accepted.
