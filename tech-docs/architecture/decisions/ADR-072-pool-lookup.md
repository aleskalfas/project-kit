---
id: ADR-072
title: The command that takes work looks up a seat's pools, and what it cannot read takes nothing
status: accepted
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** this record is how project-kit builds the pools of workers of [project-management:DEC-061](../../../.pkit/capabilities/project-management/decisions/DEC-061-pools-of-workers.md). It says which code reads a Milestone's pool, where the guard against a topology the code cannot read sits, and what each failure does.
- **The module that reads the topology reads no Milestone.** It reads the committed topology, the pools among it, and the seats' holders through the state-issue seam, and no other part of GitHub.
- **The command that takes the next Task reads the open Milestones once,** maps them to their pools, and hands the reckoning of ready work the seat's set of Milestone numbers. It hands nothing where the topology declares no pool, and the reckoning then keeps the one shared pool.
- **One parser reads the `Pool:` line,** beside the close trigger's parser, and the capability's schema for time containers declares its grammar. A Task's Milestone is its native field.
- **The topology's parse marks what it cannot read in full.** The commands that take work, take a seat or release one by force refuse on the mark. Listings warn, and work in flight goes on.
- **A failure takes nothing.** Milestones that cannot be read stop the take, with the exit of a failed read (3). A refusal by the guard exits as a checkout unfit to act does (2).

## Context

DEC-061 lets a project's topology declare pools of workers. A seat that builds chooses its work only from ready Tasks in an open Milestone of a pool it serves, and a Milestone joins a pool by a `Pool:` line in its description (points 2 and 5). DEC-061 point 9 also has code that cannot read the topology in full use none of the authority the topology grants. Its Implications ask for an architecture record on the pool lookup's boundaries, the guard's placement and the failure behaviour. This is that record.

Three records set the shape it fits:
- **The topology's reader.** The module that reads the topology builds each run's inputs for the ownership seam and the state-issue seam, and reads GitHub only through the state-issue seam ([ADR-071](ADR-071-state-issue-seam.md) point 1).
- **The ownership fold** takes its inputs from its caller, so it reads no other seam, and one run judges every claim at one instant ([ADR-041](ADR-041-instance-ownership-substrate-contract.md) point 7).
- **One reckoning of ready work.** Readiness is reckoned once ([project-management:DEC-025](../../../.pkit/capabilities/project-management/decisions/DEC-025-parallelization-primitive.md), "Readiness is reckoned once"), in the pool of [project-management:DEC-059](../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md) point 7, which DEC-061 routes through each seat's pools.

DEC-061 leaves open:
- which code reads a Milestone's pool, and which may not
- how the reckoning of ready work learns a seat's pools while it reads no GitHub
- where the `Pool:` line's grammar and its parser live
- where the guard marks a topology, and where it refuses
- what each failure exits with

## Decision

**A seat's pools are looked up by the command that takes work, never by the module that reads the topology. That command reads the open Milestones once, and hands the pure reckoning of ready work a set of Milestone numbers, or nothing where no pool is declared. One parser reads the `Pool:` line. The topology's parse marks what it cannot read in full, and each command decides what the mark means for it. A read that fails takes nothing.**

### 1. The module that reads the topology reads no Milestone

- **What it reads:** the topology, committed configuration read from the default branch (DEC-059 point 1), and each seat's holder through the state-issue seam (ADR-071 point 1). It reads no other part of GitHub.
- **The pools in it.** It parses the pools the topology declares, and the pools each seat serves, by name. It never reads which Milestones a pool holds.
- **The run's snapshot** that it builds for both seams (ADR-071 point 1) carries a seat's pools by name, never their Milestones.

### 2. The command that takes the next Task reads the open Milestones once, and hands the reckoning a set

- **One read in a run.** Where the topology declares pools, the command that takes the next Task reads the repository's open Milestones once in its run, through the module that reads Milestones. Every Task of the run is judged against that one read, as every claim is judged against one state of the seats (ADR-041 point 7).
- **No read without pools.** Where the topology declares no pool, it reads no Milestone, so a project with no pools pays no call and meets no failure for them.
- **The set.** From that read it takes the seat's set of Milestone numbers: the open Milestones of each pool the seat serves (point 3). It hands the set to the reckoning of ready work, which reads no GitHub and takes the set as an input, beside the seat's scope.
- **Nothing, and the empty set.** It hands nothing where the topology declares no pool, and the reckoning then filters by no Milestone: DEC-059's shared pool, with the move to Backlog as the gate ([project-management:DEC-006](../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)). It hands the empty set where the topology declares pools and the seat names none, or none of its pools has an open Milestone, and then no Task is ready. Neither ever stands for the other.
- **What the set narrows.** A candidate is kept only where its Milestone's number is in the set, the seat's own Tasks among them (DEC-061 point 5). The seat's scope then narrows what the set kept.
- **The other readers.** The listing of seats and taking a seat, which show each pool's open Milestones (DEC-061 point 10), read them the same way, once in a run.

### 3. One parser reads the `Pool:` line, beside the close trigger's

- **The grammar** is declared in the capability's schema for time containers, beside the lines of the close trigger and the rollforward target ([project-management:DEC-016](../../../.pkit/capabilities/project-management/decisions/DEC-016-time-bound-containers.md)).
- **The parser** is one function in the module that reads Milestones, beside the parser of the close trigger. It reads every line that opens with `Pool:`, wherever it stands, and gives the pool's name, or no pool with its reason: no such line, two of them, or one it cannot read (DEC-061 point 2). It reads no GitHub and no topology.
- **A Milestone's pool** is given by one pure function, from the Milestone's description and the pools the topology declares, which its caller passes. It is the parser's name where the topology declares that pool, and otherwise no pool, with the reason. Every reader of a Milestone's pool calls it: the take of the next Task, the take's own check of a Task's pool (DEC-061 point 5), the consent of DEC-061 point 6, the rollforward of DEC-061 point 7 and the listings of DEC-061 point 10. So no two of them disagree on what a pool holds.
- **The line a write puts in place** is built in the same module, from the same grammar, and replaces the line it finds. No other code parses or builds a `Pool:` line.

### 4. A Task's Milestone is its native field

The reckoning reads a Task's Milestone from the native Milestone field that the one listing of issues returns (DEC-061 point 4). It never reads the body's `Milestone:` line, which links a parent and is the containment seam's to read ([ADR-035](ADR-035-containment-resolution-contract.md)). A Task in no Milestone is in no pool, so no set holds it.

### 5. The topology's parse marks what it cannot read in full, and each command decides what the mark means

- **The mark.** The one parse of the topology marks a reading where it meets a key it does not know, at any depth, or a value of a known key it cannot read, such as an unknown role, release mode or schema version, or a list written as a string (DEC-061 point 9). The mark names each such thing. Every reading of the topology passes through the parse, from the default branch, the working tree or a commit, so none is read without it. The reading still gives what the parse could read, so work in flight confirms its seat on it.
- **It refuses nothing.** The parse reports, as it reports the file's other problems, and as the seams report their outcomes (ADR-041 point 5, ADR-071 point 9). The mark stands apart from those other problems, such as a seat name used twice, whose handling it leaves as it stands.
- **Commands that take refuse.** The choice of the next Task, the claim that starts a Task, taking a seat and a release by force each refuse on the mark, before they take anything, and say what the code did not understand.
- **Listings warn.** The listing of seats, and any other listing, shows what it read and warns of what it did not understand.
- **Work in flight goes on.** A renewal, the check before writing, reviewing and finishing a change, and a clone's release of its own seat each go on, since none takes anything new.

### 6. A read that fails takes nothing, and the exit says why

- **Milestones that cannot be read,** where the topology declares pools: the command that takes the next Task takes nothing, and never falls back to the whole Backlog (DEC-061 point 8). It exits 3, as when the open issues cannot be read. It never gives the exit that says no Task is ready (5), which it cannot know.
- **The listing of seats** that cannot read the Milestones shows the rest, says so, and exits 3, as for its other failed reads. **Taking a seat** warns and still takes the seat, since no Milestone decides which seat a clone takes.
- **The take's own check** of a Task's pool warns where it cannot read the Milestone, since that check is a warning, never a gate (DEC-061 point 5).
- **A `Pool:` line that cannot be read** puts its Milestone in no pool, with a warning, and stops no command (DEC-061 point 2).
- **A refusal by the guard** exits 2 in each command that refuses on the mark. It is the exit each of them gives for a capability not bootstrapped, a checkout not fit to act. Updating the checkout mends it, where a retry does not.
- **No Task ready.** Where the set is empty, or nothing in it is ready, the command exits 5 and says why in terms of the seat's pools, such as a pool with no open Milestone or a seat that names no pool (DEC-061 point 8).

## Rationale

**Why the module that reads the topology reads no Milestone.** It reads what a reviewed change decides and who holds each seat, and every command that acts as a seat reads it before it writes (DEC-059 point 6). A Milestone's pool is an attribute of an item of work, which changes with no review (DEC-061 point 3). Read there, the Milestones would cost every such command a call, and could stop it on a failure it has no use for.

**Why the command reads once and hands over a set.** A reckoning that takes its inputs is tested with no GitHub, as the ownership fold is (ADR-041, "Why the fold takes its inputs from its caller"). One read in a run judges every Task against one state of the Milestones. A command that reads no Milestone where no pool is declared leaves every project without pools as it stood.

**Why nothing and the empty set differ.** Read as one, either a seat whose pools hold no open Milestone would take the whole Backlog, which DEC-061 point 8 forbids, or every project with no pools would take nothing.

**Why one parser, and one function for a Milestone's pool.** The take, the listings, the consent and the rollforward all ask which pool a Milestone is in. Two parsers, or two judgements of an undeclared pool, could put one Milestone in a pool for the listing and in none for the take: the drift that one reader prevents ([ADR-026](ADR-026-substrate-map-read-path-contract.md)). The grammar sits in the schema that declares the description's other lines, so a reader finds them together.

**Why the parse marks and the command decides.** Only the parse knows every key and value the code understands, so only the parse can tell that it met one it does not. What to do about it differs by command: a take refuses, a listing warns, work in flight goes on. A parse that refused would stop the listings and the work in flight with it. A check of keys in each command would put knowledge of the topology's shape in each.

**Why these exits.** Exit 3 is what these commands give for a read that failed, which a retry may mend. A refusal by the guard is mended only by updating the checkout, so it takes the exit of a checkout not fit to act, and shares no exit with a failure a retry mends. Exit 5 says the seat has nothing to do, which a failed read cannot say.

### Alternatives considered

- **The module that reads the topology reads the Milestones into the run's snapshot.** Rejected: every command that confirms its seat would read the Milestones, as "Why the module that reads the topology reads no Milestone" says.
- **The reckoning reads the Milestones itself.** Rejected: it would read GitHub, and its tests would need it.
- **An empty set where no pool is declared.** Rejected: every project without pools would take nothing.
- **A Task's Milestone from the body's `Milestone:` line.** Rejected by DEC-061 point 4, since that line links a parent.
- **The parse raises on what it cannot read.** Rejected: the listings and the work in flight would stop too.
- **Each command checks the topology for the keys it knows.** Rejected: knowledge of the topology's shape in every command.
- **Exit 3 for a refusal by the guard.** Rejected: a retry never mends it.
- **Exit 5 for Milestones that cannot be read.** Rejected: it would say that nothing is ready when the run does not know.

## Implications

- **The build of #2256** realizes this record. Until it lands, no command reads a pool.
- **Tests** run the reckoning with a set, with nothing and with the empty set, and the parser and the function for a Milestone's pool, all with no GitHub.
- **ADR-041** says "the pool" for the pool a worker takes from: DEC-059's shared pool, or the seat's pools where the topology declares pools of workers. Its fold and its consumers stand as they are.
- **ADR-071** stands as it is: the run's snapshot carries a seat's pools by name, and the module that reads the topology reads GitHub only through the state-issue seam.
- **Acceptance.** The maintainer's sign-off on DEC-061 covers this record, as DEC-061's Implications say. It builds on DEC-061 and on the records DEC-061 refines, DEC-059, DEC-016, DEC-006 and DEC-025, all accepted.
