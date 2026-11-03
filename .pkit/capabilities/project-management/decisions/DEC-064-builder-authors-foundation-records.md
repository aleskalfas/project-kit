---
id: DEC-064
title: The builder authors a foundation's records, and the critic and the architect review them
status: proposed
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a foundation's first Task holds a record of each architectural choice that its slices share. Whoever builds that Task authors every one of those records, whatever kind of record each is. Before the person accepts a record, the critic reviews it, and then the architect agent, where the project deploys it. The architect cannot author them all: it writes no record outside its own folders, and none inside a build that the build command runs, whose builder may start no agent. So the builder is the one author that every foundation has, and the architect's judgement reaches each record through its review. This overturns the line of DEC-060 that had the architect author the records.

## Context

[project-management:DEC-060-foundation-before-slices] point 2 has one Task of a foundation hold a record of each architectural choice, and says: "The architect agent authors the records where the project deploys it, and the builder otherwise."

Wherever it runs, the architect writes only into the folders that the agents overlay resolves for its architecture documents and architecture records ([pkit:COR-024]). Its definition says that it owns no path in the methodology's own tree and authors no capability's artefact. A foundation's records lie where the scope test of [pkit:COR-025] places each choice, and a choice inside one capability's discipline is that capability's decision record, which lies in that tree. Nor can the architect author any record inside a build that the build command runs. The builder there may start no agent, and the commands that move the Task on refuse a commit that no recorded build produced ([project-management:DEC-063-task-builder] points 1 and 4). DEC-060's setting, a project with a topology, builds each worker's Task that way.

The second plan of EPIC #2423 met the first case. Its foundation, #2495, records five choices of one capability as that capability's decision records. The plan had the builder author them, and the critic, then the architect, review each, a judgement it showed at its approval gate (#2513).

## Decision

**The builder of a foundation's records Task authors each of its records, whatever kind of record it is. Before the person accepts a record, the critic reviews it, and then the architect, where the project deploys it.**

Here the builder is whoever builds the records' Task: a builder agent that the build command starts (DEC-063), a session, or a person.

### 1. The builder authors every record of the foundation

The builder authors each of the foundation's records, of whatever kind the scope test of COR-025 picks for its choice. The same holds for a record that changes one of the foundation's choices, which DEC-060 point 5 sends through a record "as point 2 says". The person accepts each record, as one of the Task's acceptance criteria (DEC-060 point 2).

### 2. The critic, then the architect, review each record before the person accepts it

- **The critic first,** then the architect where the project deploys it, as COR-024 orders the two.
- **The builder settles each finding,** by changing the record or by saying why it stands.
- **The findings travel with the records.** The description of the change that proposes the records lists each finding and how it was settled, so the person reads them beside the records they accept there.

### What this overturns, and what stands

This record partially supersedes DEC-060. Overturned: point 2's sentence "The architect agent authors the records where the project deploys it, and the builder otherwise", which stays in DEC-060 as it stood. Among what stands: the records come first, one Task holds them, and the person's acceptance of each is one of that Task's acceptance criteria.

## Rationale

**Why the builder authors every record.** The builder is the one author that every foundation has. The architect writes only into its own folders, which each project's overlay resolves, and writes nothing inside a build whose builder may start no agent. The builder builds the records' Task in every project, whatever kind each record is. The foundation's choices also depend on each other, which is why DEC-060 builds them one Task at a time ("Why one Task at a time"), and one author drafts them together, consistent with each other. Drafting a record decides nothing: the person decides each choice by accepting its record (DEC-060 point 2).

**Why the builder may write an architecture record.** COR-025 makes the architect the custodian of the architecture records, not their only author: it authors them, or reviews those that others author. It answers for a foundation's records by reviewing each before the person accepts it.

**Why the critic, then the architect, review each record.** COR-024 has the critic review a draft record before a person sees it, and the architect review a proposal that touches the big picture, as a foundation's shared choices do. The critic goes first, finding a draft's own gaps cheaply, so that the architect judges fit on a draft clean of them. Point 2 applies this to every record of a foundation, whatever its kind and whoever builds it, and has the findings travel with the records.

**Why the findings go in the change's description.** The person accepts a record within the change that proposes it ([pkit:COR-066] point 1). There they read the findings, and how each was settled, beside the text they accept.

**The cost.** Where the architect could author an architecture record, it reviews it instead, and a builder that knows the project's architecture less well drafts it. And inside a build that the build command runs, nothing starts the reviews yet, as the Implications say.

### Alternatives considered

- **The architect authors the foundation's architecture records where the project deploys it, and the builder every other record, which the architect reviews.** Not taken. It cannot be carried out inside a build whose builder may start no agent. It splits records whose choices depend on each other between two authors, and leaves each architecture record with no other judge of its architectural fit than its author. Which records it gives the architect would turn on what each project's overlay resolves.
- **One author either way: the architect authors every record where all of them lie in its folders, and the builder authors them all otherwise.** Not taken. It cannot be carried out inside a build whose builder may start no agent either. Who authors would turn on where each choice's record lies, which the scope test settles only as the records are written. And the architect's records would have no other judge of their architectural fit.
- **Widen the architect's scope to every folder that a foundation's records lie in,** or to folders a project names for it in the agents overlay. Rejected: it changes a core agent for every project, for one step of one capability's planning. The architect still could not author inside a build that may start no agent, and it would judge the fit of its own records alone.
- **The architect drafts each record's text as advice, and the builder writes the file.** Rejected: it blurs who authored the record, and a review gives the same judgement with one author.
- **Leave DEC-060 point 2 as it stands, each plan judging the case at its gate.** Rejected: the same judgement returns at every foundation, and a plan's gate keeps no rule for the next plan.

## Implications

- **DEC-060** gains a top line saying it is partially superseded by this record, for point 2's line on who authors the records. Point 2 stays as it stood.
- **Acceptance.** This record overturns part of the accepted DEC-060, so accepting it needs the maintainer's sign-off. It and DEC-060's top line land in one change, accepted together.
- **The pm skill.** Batch planning's "The records come first" and the worker's loop, on a Task that holds a foundation's records, say who authors the records and who reviews them. The worker's loop lists the findings in the pull request's description.
- **The architect's definition and scope do not change,** nor do COR-013, COR-024 and COR-025.
- **No command changes.**
- **Named, and not decided here,** for a records' Task that the build command builds:
  - **Who starts the reviews.** Its builder may start no agent (DEC-063 point 4), so it cannot start the critic or the architect, and no finding of theirs reaches a fix round, whose brief takes only the verdicts' findings (DEC-063 point 3). The same holds for any Task whose work is a decision record, so a record of its own decides it. Until then point 2 holds: the person accepts no record before its reviews have run.
  - **An architecture record written by a builder agent.** COR-013 says which agent answers for a path, not whether another agent may write it under that owner's review, and software-engineering's [software-engineering:DEC-004-skeleton-conventions-in-corpus] point 4 keeps its own agent out of a path that another agent owns. Whether the builder agent may write into the architect's folder is core's to settle.
