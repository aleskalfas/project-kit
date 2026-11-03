---
id: DEC-064
title: The builder authors a foundation's records, and the critic and the architect review them
status: proposed
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a foundation's first Task holds a record of each architectural choice that its slices share. Whoever builds that Task in a session authors every one of those records, whatever kind of record each is. Before the person accepts a record, the critic reviews it, and then the architect agent, where the project deploys it. The architect cannot author them all: it writes nothing outside its own folders, and it creates no file at all. So the builder is the one author that every foundation has, and the architect's judgement reaches each record through its review. A records Task that the build command would build waits until a record decides how it is built there. This overturns the line of DEC-060 that had the architect author the records.

## Context

[project-management:DEC-060-foundation-before-slices] point 2 has one Task of a foundation hold a record of each architectural choice, and says: "The architect agent authors the records where the project deploys it, and the builder otherwise."

The architect writes only into the folders that the agents overlay resolves for its architecture documents and architecture records ([pkit:COR-024]). Its definition says that it owns no path under `.pkit/` and authors no capability's artefact. A foundation's records lie where the scope test of [pkit:COR-025] places each choice. A choice inside one capability's discipline is that capability's decision record. A project-wide choice that touches tooling, such as the package manager, is the project's own record, under `.pkit/decisions/project/`. The architect can author neither. Its tools also hold no Write and no shell, so it cannot create a record's file anywhere, even in its own folders. It can only edit a file that exists.

The build command adds a case of its own. In a project with a topology, [project-management:DEC-063-task-builder] has a fresh builder agent build each worker's Task, and that builder may start no agent (points 1 and 4). Inside such a build, neither the critic nor the architect can run. The commands that move the Task on refuse a commit that no recorded build produced (point 1), so the seat cannot edit the records either. That case is not live yet. DEC-063 is accepted but not built, and the worker's loop builds each Task in the seat's own session (the pm skill's work loop, step 4).

The second plan of EPIC #2423 met the first case. Its foundation, #2495, records five choices of one capability as that capability's decision records. The plan had the builder author them, and the critic, then the architect, review each, a judgement it showed at its approval gate (#2513).

## Decision

**The builder of a foundation's records Task authors each of its records, whatever kind of record it is. Before the person accepts a record, the critic reviews it, and then the architect, where the project deploys it. A records Task that the build command would build waits until a record decides how it is built.**

Here the builder is whoever builds the records' Task in a session: a person, a session the person directs, or a seat that builds in its own session, as the worker's loop does today (step 4). A builder agent that the build command starts is the case point 3 holds back.

### 1. The builder authors every record of the foundation

The builder authors each of the foundation's records, of whatever kind the scope test of COR-025 picks for its choice. The same holds for a record that changes one of the foundation's choices, which DEC-060 point 5 sends through a record "as point 2 says". The person accepts each record, as one of the Task's acceptance criteria (DEC-060 point 2).

### 2. The critic, then the architect, review each record before the person accepts it

- **The critic first,** then the architect where the project deploys it, as COR-024 orders the two.
- **The architect returns findings, and edits none of the records it reviews.** The builder tells it so when starting it, so each record keeps one author.
- **The builder settles each finding,** by changing the record or by saying why it stands.
- **A record changed to settle a finding is reviewed again,** where the change alters what the record decides. A wording fix is not, by the test that the decisions README applies to an edit of a record ("Refining an accepted record").
- **The reviews travel with the records.** The description of the change that proposes the records names each review that ran and its outcome, findings or none. It lists each finding and how it was settled, so the person reads them beside the records they accept there.
- **The reviews are one of the Task's acceptance criteria,** beside the person's acceptance of each record, so the Task cannot close before they have run and their findings are listed.

### 3. A records Task that the build command would build waits

A Task that holds a foundation's records, or a record that changes one of its choices, waits where the build command would build it (DEC-063 point 1). It waits until a record decides how such a Task is built through the command. Inside such a build, point 2's reviews cannot run, and their findings could not reach the builder, as the Implications say.

### What this overturns, and what stands

This record partially supersedes DEC-060. Overturned: point 2's sentence "The architect agent authors the records where the project deploys it, and the builder otherwise", which stays in DEC-060 as it stood. Among what stands: the records come first, one Task holds them, and the person's acceptance of each is one of that Task's acceptance criteria.

## Rationale

**Why the builder authors every record.** The builder is the one author that every foundation has. The architect writes only into its own folders, which each project's overlay resolves, and creates no file even there. The builder builds the records' Task in every project, whatever kind each record is. The foundation's choices also depend on each other, which is why DEC-060 builds them one Task at a time ("Why one Task at a time"). One author drafts them together, consistent with each other. Drafting a record decides nothing: the person decides each choice by accepting its record (DEC-060 point 2).

**Why a session's builder may write an architecture record.** COR-024's contract for the two agents reads: "The primary agent (or human) authors." The critic and the architect review. COR-025 makes the architect the custodian of the architecture records, not their only author: a project's people may author them directly. So a person, or the session working for them, may write one, and the architect answers for it by reviewing it. Whether a builder agent may write into the architect's folder is a question of its own, which point 3 waits on.

**Why the critic, then the architect, review each record.** COR-024 has the critic review a draft record before a person sees it, and the architect review a proposal that touches the big picture, as a foundation's shared choices do. The critic goes first, finding a draft's own gaps cheaply, so that the architect judges fit on a draft clean of them. Point 2 applies this to every record of a foundation, whatever its kind. The architect's definition lets it edit in its own folders. The instruction it is started with keeps it to findings, so the definition need not change.

**Why a changed record is reviewed again only where its decision changes.** A finding settled by changing what a record decides leaves a new draft of that decision, which no reviewer has seen. A wording fix leaves every choice as it stood, so a second review would find nothing new.

**Why the reviews go in the change's description, and in the criteria.** The person accepts a record within the change that proposes it ([pkit:COR-066] point 1). There they read each review, its findings and how each was settled, beside the text they accept. A review with no findings is named too, so the person sees that it ran. As an acceptance criterion, the reviews hold the Task open until they have run, as the person's acceptance does ([project-management:DEC-007-checkbox-validation]).

**Why a records Task that the build command would build waits.** Inside such a build, three things stand open, as the Implications say. Built there before a record settles them, a foundation's records would reach the person unreviewed, or with findings nobody could settle. The wait holds nothing back yet, since no Task is built through the command until DEC-063 is built.

**The cost.** A builder that may know the project's architecture less well than the architect drafts even the architecture records. The architect's judgement reaches them only through its review. And once DEC-063 is built, a project with a topology holds its foundation's records Task, and the slices behind it, until the follow-up record lands.

### Alternatives considered

- **The architect authors the foundation's architecture records where the project deploys it, and the builder every other record, which the architect reviews.** Not taken. The architect creates no file, so it could only edit a record that someone else had stamped. It splits records whose choices depend on each other between two authors. And each architecture record would have no other judge of its architectural fit than its author.
- **One author either way: the architect authors every record where all of them lie in its folders, and the builder authors them all otherwise.** Not taken. The architect creates no file, so it could not author them even there. Who authors would turn on where each choice's record lies, which the scope test settles only as the records are written. And the architect's records would have no other judge of their architectural fit.
- **Widen the architect's scope to every folder that a foundation's records lie in,** or to folders a project names for it in the agents overlay. Rejected: it changes a core agent for every project, for one step of one capability's planning. The architect would need a tool that creates files too. And it would judge the fit of its own records alone.
- **The architect drafts each record's text as advice, and the builder writes the file.** Rejected: it blurs who authored the record, and a review gives the same judgement with one author.
- **Leave DEC-060 point 2 as it stands, each plan judging the case at its gate.** Rejected: the same judgement returns at every foundation, and a plan's gate keeps no rule for the next plan.
- **Decide here how the build command builds a records Task.** Not taken. It changes how DEC-063 runs its reviewers and its fix rounds, and it needs the three open questions settled. The Implications name its first candidate.

## Implications

- **DEC-060** gains a top line saying it is partially superseded by this record, for point 2's line on who authors the records. Point 2 stays as it stood. The top line flags each artefact anchored on DEC-060, and the change that adds it answers each.
- **Acceptance.** This record overturns part of the accepted DEC-060, so accepting it needs the maintainer's sign-off. It and DEC-060's top line land in one change, accepted together.
- **The pm skill.** Batch planning's "The records come first" says who authors the records and who reviews them. The first plan gives the records Task the reviews' acceptance criterion. The worker's loop, on a Task that holds a foundation's records, has the worker author them, start the reviews and list them in the pull request's description.
- **Whoever implements DEC-063** reads this record when rewriting the worker's loop, step 4, so that a records Task waits as point 3 says.
- **The architect's definition and scope do not change,** nor do COR-013, COR-024 and COR-025.
- **No command changes.**
- **Named, and not decided here: how a foundation's records Task is built through the build command.** A record of its own decides it, and point 3 holds such a Task until then. That record settles three questions:
  - **A builder agent writing into a folder another agent owns.** COR-013 gives each managed path exactly one owning agent (point 2), and the architect owns its architecture records' folder. Software-engineering's [software-engineering:DEC-004-skeleton-conventions-in-corpus] point 4 keeps its own agent's corpus entries out of a path another agent owns. Whether a builder agent may write an architecture record there, under the architect's review, is core's to settle.
  - **How the reviews' findings reach the builder.** The builder may start no agent (DEC-063 point 4), and its run has ended by the time the seat could start the reviews. The seat may not edit the records itself, under the provenance check (point 1). A fix round's brief carries only the blocking findings of the verdicts (point 3).
  - **The default builder's bar on architectural choices.** Software-engineering's producer, where the records leave an architectural choice open, makes none in its place and says so on the Task (its definition, "When you build a walking skeleton"). A builder never guesses a decision that is not its own, and a question about a record or a shared choice is the person's (DEC-063 points 5 and 6).
  - **The first candidate.** On a records Task, the critic and the architect run as reviewers that give verdicts. Their blocking findings then reach the builder through the fix round that exists.
