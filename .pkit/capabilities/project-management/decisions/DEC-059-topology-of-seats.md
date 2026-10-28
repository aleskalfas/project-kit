---
id: DEC-059
title: Parallel clones take seats of a committed topology, and take their work from one shared pool
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> **Partially superseded by [DEC-061](DEC-061-pools-of-workers.md).** Where the topology declares pools of workers, a seat that builds chooses its work only from ready Tasks in an open Milestone of a pool it serves. Overturned for such a project: the one pool that every seat shares, wherever the title, the summary, the Decision's headline and point 7 state it, with point 7's bullets on who may take a Task and on the expected owner, the Rationale's case for one pool, and the rejection of work reserved for some seats. Among what stands: all of this record in a project with no pools, what makes a Task ready, the vertical slices, and a scope that reserves nothing. DEC-061's "What this overturns, and what stands" lists each passage, and what replaces it.

**In plain terms:** a project that runs several AI agents at once, each in a clone of its own, declares a **topology** in its committed configuration: a list of **seats**. Each seat has a name, a role (planner, worker or lead), the agent definition its agent follows and an optional scope. Where the topology declares pools of workers, a seat that builds also names the pools it serves ([project-management:DEC-061-pools-of-workers]). Every clone reads the topology from the default branch. A clone takes a free seat through the seat's state issue ([project-management:DEC-058-state-issues]), and then works as that seat's agent, under the seat's name. Workers take the next ready Task from one pool that every seat shares. The work renews a Task's claim, and a claim lapses when the work stops, so a dead session's Task returns to the pool. A seat stays taken until it is released, by its clone, by the organizer seat's clone or by a person. This replaces the topology that [project-management:DEC-045-named-per-user-instances] keeps per user, and changes parts of [project-management:DEC-035-instance-ownership] for a project with a topology.

## Context

DEC-035 tells one person's clones apart by a number that each clone is given by hand. DEC-045 adds a name to each clone, and a file that lists a person's clones with the workstreams each handles. That file is kept per user, on one machine, and never committed (DEC-045 point 2).

Agents now also run on a shared platform, each in a sandbox and a clone of its own. Each sandbox is another machine, so a file on one person's machine reaches none of them. The agent that plans needs to know which seats exist and what each covers. The other agents need to know their own seat, and which seats the others hold.

The maintainer decided on 25 October that the topology is the project's committed configuration, read by every clone, which overturns DEC-045 point 2 (#512). On 26 October, walking the analysis of parallel work with the project-manager agent, he decided the rest of the model (#512, #2096). The model has seats with state issues, and taking and releasing a seat. It sets the safeguards of a Task's claim, the shared pool of work, and a clone's identity. This record holds those decisions.

## Decision

**A project that runs agents in parallel declares a topology of seats in its committed configuration. A clone takes one seat through the seat's state issue, and acts as that seat's agent under the seat's name. Workers take ready work from one shared pool, and a Task's claim lapses once its work stops.**

### 1. The topology is committed configuration, read from the default branch

The topology is a file of the project's own configuration for this capability, committed and reviewed like any other change. Every clone reads it from the default branch, the project's settled state, through the backbone's one resolution of that branch ([pkit:COR-054] point 5). It never reads the topology from its own branch or working tree. So a change to the topology binds once it merges, and every clone that has read the default branch reads the same seats. A clone that has not fetched the default branch reads what it last fetched, and says which commit it read. Where the default branch cannot be resolved, no clone takes a seat (COR-054 point 4). Whoever may merge to the default branch may change the topology.

The topology may also declare pools of workers, and each seat that builds names the pools it serves (refinement per [project-management:DEC-061-pools-of-workers] point 1). Code that cannot read the topology in full, since it meets a key it does not know at any depth or a value it cannot read, uses none of the authority the topology grants. It takes no work, no seat and no release by force, and work already in flight goes on (DEC-061 point 9). So pools enter a project's topology only once every clone that may take a seat runs its taking commands from a checkout at or past the change that brings this guard, an order of work that DEC-061 point 9 keeps for each later addition to the topology's shape, and that no check enforces yet.

### 2. A seat has a name, a role, an agent and an optional scope

Each seat declares:

- **its name,** unique in the topology, which becomes the identity of the clone that holds the seat (point 6). A seat's name never changes: renaming a seat retires it and adds a new one.
- **its role,** one of three:
  - a planner slices the work and files it, and builds none of it
  - a worker takes ready work and builds it up to its merge
  - a lead plans and builds within its scope, and may start helper agents of its own
- **its agent definition,** the project-manager agent's by default (point 8)
- **its scope,** which is optional and narrows the work its agent takes (point 7)
- **its pools,** where the topology declares pools of workers: the pools a seat that builds serves (refinement per [project-management:DEC-061-pools-of-workers] point 1)
- **its state issue,** by number (point 3)
- **whether it is the organizer seat.** At most one seat is, typically the planner's. Its clone may release other seats by force (point 5), a privilege the reviewed change to the topology grants.

The topology also holds the settings its seats share. They include the mode in which a seat is released (point 5), and the limit after which a Task's claim lapses (point 9).

### 3. Each seat has a state issue, which the topology names

Which clone holds a seat is kept on a state issue of its own, keyed by the seat's name ([project-management:DEC-058-state-issues]). The topology names each seat's state issue by its number, and never says who holds a seat. A command that the adopter runs on the change that adds seats creates each new seat's state issue, and writes its number into the topology. So the change lands with its state issues, and clones find each one by its number, with no search and no race to create it. A seat whose state issue is not named, or cannot be read, cannot be taken until a reviewed change names one. A change closed unmerged leaves state issues that no seat names, and the listing of seats names them for a person to close.

### 4. A clone takes a seat by its name, or the first free seat

A clone takes the seat it is given by name. Otherwise it takes the first free seat in the topology's order, or the first free seat of the role it is given. It takes only a seat whose agent definition is the one its own session follows. Whoever starts a session for a seat named in advance starts it with that seat's definition.

Taking a seat is a claim on the seat's state issue, and the first claim on a free seat holds ([project-management:DEC-058-state-issues] points 5 and 6). A clone that loses a seat takes another free seat of that role, or stops, as its agent judges, the same choice a clash on a Task leaves it. A clone holds at most one seat, and a seat is held by at most one clone. A new session in a clone that holds a seat takes up that seat, since the clone's key outlives every session in it.

### 5. In the first mode, a seat stays taken until it is released

- **The tolerant mode.** In the first and most tolerant mode, a seat stays taken until its clone releases it, or until a release by force. No seat is freed for its clone's silence in this mode.
- **A release by force** comes from the clone of the organizer seat, or from a person in any clone. A person authorises it as a person authorises a held move, which an agent never authorises for itself ([project-management:DEC-006-state-machine-and-cascade]). Each release by force carries its reason, which the seat's state issue logs.
- **A seat's release frees its clone's work.** A claim on an issue counts only while the clone that made it holds the claim's seat (point 9). So when a seat is released, by its clone or by force, every claim its clone made stops counting, with no write to those issues. A dead clone's Tasks return to the pool, and its Backlog Tasks and containers lose their owner.
- **A seat retired while held** is released at its clone's next command, as its clone would release it.
- **Stricter modes,** which free a seat after a silence, are named and not built. The topology will choose one as a setting ([pkit:COR-007]).

### 6. A clone's identity is its seat's name, and its number comes from the topology

- **The name.** A clone that holds a seat is an instance, named by its seat ([project-management:DEC-035-instance-ownership] point 1, [project-management:DEC-045-named-per-user-instances] point 1).
- **The number** is derived from the topology, never typed: a seat's number is its place in the topology's list of seats, counted from one. Seats are only added at the end, and a seat that leaves the topology stays in the list, marked retired, so no seat's number moves.
- **What the number serves:** what DEC-035 uses it for, the tie-break between two claims on one Task and the `instance:N` label. The topology's seats are the pool of numbers, whatever their count ([project-management:DEC-035-instance-ownership] point 2).
- **No typed number.** In a project with a topology, a number is never typed into a clone, since it could take a seat's number. A clone that holds no seat marks no issue and is guarded by nothing, as a clone with no number.
- **Confirmed before each write.** Every command that acts as an instance confirms the clone's seat on the seat's state issue, by the clone's key, before it writes. The clone may keep its seat's name as a hint of where to look, and never acts on the hint without that read.
- **Helpers.** A helper agent that a lead starts acts as the lead's instance. How a linked worktree of the clone reads that identity is not decided here.

### 7. Work reaches agents through one shared pool

By default, a worker takes the next ready Task from one pool that every seat shares, the highest in priority first ([project-management:DEC-012-classification-axes]). The owner keeps two agents off one Task ([project-management:DEC-035-instance-ownership] point 6). A ready Task is one of two kinds:

- an open Task in Backlog, with no owner, that names no open issue among its dependencies ([project-management:DEC-005-linking-and-containment])
- a Task In Progress whose claim no longer counts, since it lapsed or its seat was released (point 9). The worker takes it over and goes on from its branch ([project-management:DEC-035-instance-ownership] point 4).

How the pool is filled:

- **The planner slices the work vertically,** so that one agent can finish a Task, or a Feature, across the software's layers. Workstreams as layers of the software are not the partition. Where the slices would share a choice that nothing settles yet, they are planned once a foundation settles it ([project-management:DEC-060-foundation-before-slices]).
- **The planner files with no owner,** so its work enters the pool. A lead owns what it files, since it builds that work itself.

A seat's scope is an optional filter on that seat's own pool, and reserves nothing for it:

- **What a scope names:** workstreams ([project-management:DEC-045-named-per-user-instances] point 3), Task types from the type axis such as `test` or `docs` ([project-management:DEC-012-classification-axes]), or both. A Task falls in the scope where it matches each part the scope names. A type, like a workstream, is referenced and never rebound.
- **What waits:** a discipline the type axis does not carry, such as design, waits for a record that decides how a Task carries it.
- **Who may take a Task:** every seat that builds and has no scope, and every seat whose scope the Task falls in. A workstream that no seat may take is warned of and never blocked ([project-management:DEC-045-named-per-user-instances] point 4). Several seats that may take one workstream are the shared pool, and draw no warning.
- **The expected owner** of a Task is the seat that alone may take it. The guard warns when another instance takes it ([project-management:DEC-045-named-per-user-instances] point 5).

### 8. The agent a seat names runs the seat's role through the pm skill

- **The project-manager agent** in a seat reads the seat's role and runs that role's procedure from the pm skill. The role sets the agent's direction in place of inference from the request. A planner acts in PM direction, a worker in Implementer direction, and a lead in both within its scope ([project-management:DEC-029-project-manager-agent-shape], [project-management:DEC-008-pm-and-implementer-roles]).
- **Another agent definition,** such as a specialist's, may be named by a seat. Its agent takes the seat, claims work and lands it through the same procedure of the pm skill. So taking, claiming and landing are the same whichever agent a seat names.
- **A role never stands in for a person's authorisation,** such as filing an EPIC, scheduling work or authorising a merge ([project-management:DEC-006-state-machine-and-cascade], [project-management:DEC-008-pm-and-implementer-roles]).

### 9. A Task's claim is released, renewed, lapses, and is checked again

In a project with a topology, an instance's claim on a Task rests on four safeguards:

- **Release:** the owner releases the Task once it is done, at its merge or as won't-do ([project-management:DEC-035-instance-ownership] point 4). It also releases the Task once it stops work on it, with an abandon event ([project-management:DEC-043-ownership-substrate-selection] point 3).
- **Renewal:** the owner's work renews the claim, by an ownership event of its own each time. The capability's commands post one, and so does the role's procedure as it builds, before it pushes and at least once within a part of the limit. The audit-log facility renders a renewal compact ([project-management:DEC-044-audit-log-facility] point 4).
- **Lapse:** a claim on a Task In Progress that its work has not renewed within a generous limit lapses, so another agent may take the Task over. A Task in Review waits on its reviewers and a person, not on its owner, so its claim does not lapse, and nor does a claim on a container or on a Task in Backlog. The topology sets the limit, and its default outlasts a session paused at a usage limit or overnight.
- **A check before writing:** every command that writes as the owner reads the clone's seat and the Task's claim first. A push passes through no command of this capability, so the role's procedure checks before it pushes. Where the claim lapsed or passed to another clone, the session parks its work. It keeps what it built on a branch of its own, writes nothing to the Task's branch or pull request, and says on the Task where the parked work lies.

The claims rest on the comment log:

- **The comment substrate.** A project with a topology keeps its ownership marker in the comment log, the selector's `comment` value and its default ([project-management:DEC-043-ownership-substrate-selection] point 2, refined in place). The topology's check refuses a topology under `label`, since a label cannot carry what a claim names.
- **What a claim names.** A claim on an issue names the seat, its number and the clone's key. It counts only while that clone holds that seat, so a clone that takes the seat later never inherits an earlier clone's claims.
- **Time.** Renewal and lapse use the time GitHub records for each comment, never a time a clone writes, so the clocks of the sandboxes decide nothing.
- **Claims from before the topology.** A claim made under a typed number names no seat, so it stops counting once the topology lands. Its issue returns to the pool, and the clone that worked on it claims it again from its seat.

A claim that no longer counts is no claim, so the guard does not refuse on it ([project-management:DEC-035-instance-ownership] point 6). A project with no topology keeps DEC-035's release and hand-over as they stand.

### What this overturns, and what stands

This record partially supersedes DEC-045 and DEC-035. Each overturned passage stays in its record as it stood.

- **Overturned in DEC-045:**
  - point 2, a topology kept in a per-user file on one machine and never committed. The topology is the project's committed configuration (point 1 here).
  - wherever the record places the topology, the reference to workstreams or the source of the expected owner in that file or in local configuration. That covers the title, the summary, the Decision's headline, the Context's "the operator's own correction is the resolution", points 3 and 5, the Rationale, the Alternatives and the Implications. A seat's scope, in the topology, holds the reference (point 7 here).
  - in point 4, full coverage as the default, and the warning of a workstream that several instances handle, with the Rationale's "Why soft partition at `warning`" where it defends them. Under the shared pool, several seats may take one workstream (point 7 here).
  - in point 5, the expected owner as the instances that reference the issue's workstream. It is the seat that alone may take the issue (point 7 here).
  - in point 6, a local script, and its drive toward each workstream handled by exactly one instance. The guided assignment writes the scopes of the seats that have one into the committed topology, for a reviewed change.
  - in point 7 and the Implications' "Two new scripts", the scaffolded `set-instance` name and topology entry. The new clone takes a seat in its first session (point 4 here).
  - in point 8 and the Implications, the deferral of any team-shared topology
- **Overturned in DEC-035, for a project with a topology:**
  - in point 1, the typed number, and the id as the sole sign that a clone takes part. A clone takes part by taking a seat, and its number is the seat's (point 6 here).
  - in point 2, the pool of numbers for each assignee, four by default, with the Implications' constant of four. The seats are the pool (point 6 here).
  - in point 3, the claim at creation by a clone in a planner's seat, with the Rationale's "Why claim-at-creation for the whole tree" for that seat. Its work enters the pool with no owner (point 7 here).
  - in the Rationale's "Why opt-in by clone-local id, no committed config", that no committed registry is needed, and that the per-clone id and the labels are the feature's whole persistent state
- **Stands in DEC-045:**
  - a clone's name, which point 1, refined in place, makes the seat's name
  - a reference to workstreams that never rebinds them (point 3)
  - the warning of a workstream that no one takes (point 4)
  - an expected owner that feeds only the guard, with its three cases of one, several or none (point 5)
  - a guided assignment that runs again and reconciles the workstreams' drift (point 6)
  - provisioning that asks before it touches the file system, and stays on the person's machine (point 7)
  - the deferred decomposition of a project (point 8)
- **The privileged writer DEC-045 rejected** stays rejected: no clone writes the topology, and a change to it is reviewed. The organizer seat's one privilege, the release by force, is granted in that reviewed change. It rests on a key each clone asserts. Like DEC-035's guard, which is no lock, it catches mistakes, and it is no security boundary.
- **Stands in DEC-035:** all of it, in a project with no topology. In a project with one, the marker and the owner pair stand, with the claim at creation by every other clone, the release on close, and the hand-over. So do the clash guard and its tie-break by the lower number, the signed listing, and realm-blindness. Points 1, 4 and 6 gain what DEC-058 and this record add, refined in place.

DEC-029's mode surface and its procedure carrier, and DEC-043's selector and its read cost, are refined in place.

## Rationale

**Why committed configuration.** Every clone must read the same seats, on one machine or on a platform's sandboxes, and the planner must see what each seat covers. A committed file answers DEC-045's reasons against a shared registry. Git gives it to every clone, so it has no single point of failure. No clone writes it at run time, and a change to it passes the same review as any other. The topology's commit also names the shape a run of agents worked in, so two runs can be compared.

**Why the default branch.** A change binds once it is reviewed and merged, and not while it sits on a branch. Every clone that has fetched the default branch reads the same topology, as every reader of a use case reads the same settled set ([project-management:DEC-054-use-case-validation]).

**Why seats in configuration and their holders in state issues.** What a person decides, which seats exist and what each does, is reviewed. Which clone holds a seat changes as clones start and stop, with no review ([project-management:DEC-058-state-issues] point 1). A card kept in each clone would hide each clone's seat from all the others.

**Why the topology names each state issue.** Clones that start at once would all reach for the first seat. If taking a seat created its state issue, each might create one and find only its own claim. Created with the reviewed change and named by number, each state issue exists before any clone starts, and no clone searches for it.

**Why by name, or the first free seat.** A platform that starts several sandboxes at once needs no setup for each: each takes the first free seat of a role. An operator who wants one seat names it. A session takes only a seat of its own agent definition, so it never fills a seat meant for another agent.

**Why the tolerant mode first.** Freeing a seat after a silence would let a second clone take a seat whose first clone is only paused. Both would then act as one instance. A seat that stays taken holds back its clone's work only until the organizer seat's clone or a person frees the seat, which frees that work too. Stricter modes wait for evidence of what a silence means ([pkit:COR-007]).

**Why the number comes from the topology.** A typed number can repeat between sandboxes, and the guard then cannot tell them apart. A number derived from the seat is as unique as the seat's name, and every clone computes the same one. Seats keep their place, so a claim in flight keeps its number, as a record's points keep their ids ([pkit:COR-058]).

**Why one shared pool, and vertical slices.** Agents split by layer must coordinate across layers for every Feature. One pool, with one owner for each Task, keeps agents apart with no routing to keep up. A scope stays for a seat that does one kind of work only. It narrows that seat's own work and reserves nothing, so other seats keep the whole pool.

**Why a scope may name a Task's type.** The maintainer put a scope by discipline first, for a specialist's seat. The type axis already says of every Task whether it is a test or docs, so a testing seat can take test Tasks with no new marker. A discipline the axis does not carry, such as design, would need a new classification, which DEC-045 refused to add for instances. Referencing a type, as a scope references a workstream, changes neither.

**Why a planner files with no owner.** Under DEC-035 point 3, a planner with an instance would own all it files. Every worker would then have to take each Task over first (DEC-035 point 4). Owning what it files still serves a lead, which builds what it plans.

**Why these safeguards for a Task's claim.** A dead session's claim holds a Task that any worker could take up from its branch. So the work renews the claim, a lapse returns the Task to the pool, and a session that comes back checks before it writes over another's work. The key in each claim keeps a new holder of a seat from passing as the clone that went away. A Task in Review has finished its work, and waits on others, so its claim stands.

**Why a claim counts only while its seat is held.** Releasing a dead clone's claims one by one would write to every issue it owned, and could stop halfway. It would also need an event that releases on another's behalf, from another account, which the ownership log does not trust ([pkit:ADR-041] point 2). Judged when it is read, the seat's release frees every claim at once, and leaves nothing half done.

**Why a topology takes the comment log.** A claim names the seat, the clone's key and a time, and a label has room for none of them. Reading the time a label was added from the issue's timeline would add a read for each Task that no seam covers. The comment log is the selector's default, and works in every repository (DEC-043 point 2). Renewal and lapse rest on that log and on the topology's limit. So a project with no topology keeps DEC-035 as it stands, where a person hands a dead clone's work over.

**Why one agent that reads its role.** One entry point keeps the project-manager agent a thin dispatcher, with the role's steps in the skill ([project-management:DEC-029-project-manager-agent-shape], [pkit:COR-006]). A specialist that takes the same steps keeps taking, claiming and landing the same in every seat.

### Alternatives considered

- **Keep DEC-045's per-user file, and copy it into each sandbox.** Rejected: each copy drifts, and no copy shows the other people's seats.
- **A git-ignored card in each clone, holding its role and scope.** Rejected: no clone sees another's role or scope. The guard loses its expected owner, and a workstream no seat takes goes unnoticed.
- **A committed file for each GitHub user.** Rejected: seats belong to the project, not to a person. Agents on a platform that all work under one account would share one file anyway.
- **The holder of each seat written in the topology.** Rejected: a commit and a merge each time a clone takes a seat ([project-management:DEC-058-state-issues] point 1).
- **Create a seat's state issue when a clone first takes the seat.** Rejected: clones that start at once race to create it, as "Why the topology names each state issue" says.
- **Free a seat after a silence, in the first mode.** Deferred, as "Why the tolerant mode first" says.
- **Typed numbers, checked against the topology.** Rejected: one more value to keep in step with the seats, on every clone.
- **Workstreams as the default partition of work.** Rejected: a split by layer makes agents coordinate across layers for every Feature.
- **A scope that reserves its work for its seat.** Rejected: the shared pool would split into as many pools as scopes, and a seat with no scope could take nothing a scope names.
- **An agent definition for each role.** Rejected: three entry points to learn and keep in step, against DEC-029's single dispatcher.

## Implications

- **A schema for the topology,** in the project's configuration for this capability. Its check reports a duplicate seat name, more than one organizer seat, a seat with no state issue named, and a scope that names an unknown workstream or type. It also reports a seat deleted or moved rather than retired, against the default branch, with COR-054's override of the base.
- **Commands:**
  - one that creates the new seats' state issues and writes their numbers into the topology
  - one that takes a seat, by its name or its role, and prints the seat's role and agent definition
  - one that releases a seat, by its clone or by force, with the claims of its clone
  - a listing of the seats and their holders
  - In a project with a topology, `set-instance` refuses a typed number. The commands' names are the build's.
- **The pm skill gains a procedure for each role** that batch planning does not already serve, the worker's loop among them, with the renewal and the check before each push. The project-manager agent's first step reads its seat ([project-management:DEC-029-project-manager-agent-shape]).
- **ADR-041 is refined in place** ([pkit:ADR-041]). Its fold takes from its caller the time of reading, the limit, the Task's state in the lifecycle and the seats' holders, so the ownership seam reads no other seam. Its consumers grow by the pool, the check before writing and the seat's release. The description mirror can no longer stand for the fold, since lapse depends on the time of reading. The fold reads the logs of Tasks In Progress, the only claims that lapse, and pages a long log, so it never reads one cut short. The maintainer's sign-off on this record covers that refinement, which the architect authors once this record is accepted.
- **The ownership stamp gains a version,** carrying the seat and the clone's key ([project-management:DEC-044-audit-log-facility] point 2). Readers still accept the stamps written before it.
- **No mesh interaction.** The topology is the project's own configuration, outside what the mesh compares across repositories ([project-management:DEC-022-methodology-mesh]), and the shared pool is the repository's own. In a project whose topology declares pools of workers, the work routes through each seat's pools instead, and they too are the repository's own, since they hold its own Milestones ([project-management:DEC-061-pools-of-workers]).
- **DEC-045's guided assignment** writes the scopes of the seats that have one into the committed topology, and the change lands through review like any other.
- **Named, not built:** a scope by a discipline the type axis does not carry, stricter modes for a seat, GitHub accounts of the agents' own, and typed dependencies between Tasks.
- **Acceptance:** this record partially supersedes the accepted DEC-035 and DEC-045, and refines them, DEC-029 and DEC-043 in place, so accepting it needs the maintainer's sign-off. It builds on DEC-058, which is accepted first or with it. The refinements on DEC-029, DEC-035, DEC-043 and DEC-045 land only with both records accepted.
- **No behaviour changes** until the topology is built, so the record lands with a `none` changeset.
