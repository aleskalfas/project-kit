---
id: DEC-064
title: The builder authors a foundation's records, and the critic and the architect review them
status: proposed
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a foundation's first Task holds a record of each architectural choice that its slices share. The person builds that Task, or a session they direct, and authors every one of those records, whatever kind of record each is. Before the person accepts a record, the critic reviews it, and then the architect agent, where the project deploys it. The architect cannot author them all, since it writes nothing outside its own folders. An agent that follows a definition of its own, such as a worker seat's agent or the build command's builder, builds no such Task until a record decides whether and how it may. This overturns the line of DEC-060 that had the architect author the records.

## Context

[project-management:DEC-060-foundation-before-slices] point 2 has one Task of a foundation hold a record of each architectural choice, and says: "The architect agent authors the records where the project deploys it, and the builder otherwise."

The architect writes only into the folders that the agents overlay resolves for its architecture documents and architecture records ([pkit:COR-024]). Its definition says that it owns no path under `.pkit/` and authors no capability's artefact. A foundation's records lie where the scope test of [pkit:COR-025] places each choice. A choice inside one capability's discipline is that capability's decision record. A project-wide choice that touches tooling, such as the package manager, is the project's own record, under `.pkit/decisions/project/`. The architect can author neither. Its tools also hold neither Write nor a shell, the tools that create a record's file and run the authoring command.

Agents that work on their own add a case. A seat's agent follows an agent definition, the project-manager agent's by default ([project-management:DEC-059-topology-of-seats] point 2). That definition sends architecture decisions to the architect or a human. In a project with a topology, [project-management:DEC-063-task-builder] has a fresh builder agent build each worker's Task, and that builder may start no agent (points 1 and 4). DEC-063 is accepted, and not built yet. [pkit:COR-013] gives each managed path exactly one owning agent (point 2), and the architect owns its architecture records' folder. No record decides yet whether another agent may write a record there, or how an agent drafts a choice its definition leaves to others.

The second plan of EPIC #2423 met the first case. Its foundation, #2495, records five choices of one capability as that capability's decision records. The plan had the builder author them, and the critic, then the architect, review each, a judgement it showed at its approval gate (#2513).

## Decision

**The builder of a foundation's records Task authors each of its records, whatever kind of record it is. Before the person accepts a record, the critic reviews it, and then the architect, where the project deploys it. No agent that follows a definition of its own builds such a Task until a record decides whether and how it may.**

Here the builder is whoever builds the records' Task in a session that follows no agent definition of its own: the person, or a session the person directs. It is not the builder agent of DEC-063. An agent that follows a definition of its own is the case point 3 holds back.

### 1. The builder authors every record of the foundation

The builder authors each of the foundation's records, of whatever kind the scope test of COR-025 picks for its choice. The same holds for a record that changes one of the foundation's choices, which DEC-060 point 5 sends through a record "as point 2 says". The person accepts each record, as one of the Task's acceptance criteria (DEC-060 point 2).

### 2. The critic, then the architect, review each record before the person accepts it

- **The critic first,** then the architect where the project deploys it, as COR-024 orders the two.
- **The architect returns findings, and edits none of the records it reviews.** The builder tells it so when starting it, so each record keeps one author. An edit it made anyway would show in the change's diff.
- **The builder settles each finding,** by changing the record or by saying why it stands.
- **A record changed to settle a finding is reviewed again,** where the change alters what the record decides. Each reviewer that has not seen the changed decision reviews it, the critic before the architect. A wording fix is not reviewed again, by the test that the decisions README applies to an edit of a record ("Refining an accepted record").
- **The reviews travel with the records.** The description of the change that proposes the records names each review that ran and its outcome, findings or none. It lists each finding and how it was settled, so the person reads them beside the records they accept there.
- **The reviews are one of the Task's acceptance criteria,** beside the person's acceptance of each record. Whoever files the Task gives it the criterion: the first plan for a foundation's records, and the filer of a Task that changes one of its choices (DEC-060 point 5). The builder ticks it once the reviews have run and the description lists them.

### 3. No agent that follows a definition of its own builds a records Task yet

A Task that holds a foundation's records, or a record that changes one of its choices, is built by no agent that follows a definition of its own. That covers a seat's agent, worker or lead, and a builder agent that the build command starts (DEC-063). The person builds it, or a session they direct, until a record decides whether and how such an agent may. A worker that takes such a Task builds none of it, says so on the Task, and leaves it to the person. Three questions stand open for such an agent, as the Implications say.

### What this overturns, and what stands

- **DEC-060, partially superseded.** Overturned: point 2's sentence "The architect agent authors the records where the project deploys it, and the builder otherwise", which stays in DEC-060 as it stood. Among what stands: the records come first, one Task holds them, and the person's acceptance of each is one of that Task's acceptance criteria.
- **DEC-059 and DEC-063, refined in place,** each narrowed by point 3: DEC-059 point 2, whose seats build ready work, and DEC-063 point 1, whose build command builds each worker's Task. Neither builds a Task that holds a foundation's records. Each gains a forward pointer to point 3, and the rest of both records stands.

## Rationale

**Why the builder authors every record.** The person can build the records' Task in every project, whatever kind each record is, and accepts each record in any case. The architect writes only into its own folders, which each project's overlay resolves. The foundation's choices also depend on each other, which is why DEC-060 builds them one Task at a time ("Why one Task at a time"). One author drafts them together, consistent with each other. Drafting a record decides nothing: the person decides each choice by accepting its record (DEC-060 point 2).

**Why the person, or a session they direct, may write an architecture record.** COR-025 makes the architect the custodian of the architecture records, not their only author: its custody "doesn't preclude humans", who may author them directly. COR-024 leaves the primary agent, or the person, "responsible for the final shape of any proposal", while the critic and the architect review it. This record reads a session the person directs as the person's own authoring, since it follows no agent definition with paths or limits of its own. An agent that follows one is the case point 3 holds back.

**Why the critic, then the architect, review each record.** COR-024 has the critic review a draft record before a person sees it, and the architect review a proposal that touches the big picture, as a foundation's shared choices do. The critic goes first, finding a draft's own gaps cheaply, so that the architect judges fit on a draft clean of them. Point 2 applies this to every record of a foundation, whatever its kind. The architect's definition lets it edit in its own folders. The instruction it is started with keeps it to findings, so the definition need not change.

**Why a changed record is reviewed again only where its decision changes.** A finding settled by changing what a record decides leaves a new draft of that decision, which a reviewer has not seen. A wording fix leaves every choice as it stood, so a second review would find nothing new.

**Why the reviews go in the change's description, and in the criteria.** The person accepts a record within the change that proposes it ([pkit:COR-066] point 1). There they read each review, its findings and how each was settled, beside the text they accept. A review with no findings is named too, so the person sees that it ran. The builder ticks the reviews' criterion itself, as the actor that ticks answers for it ([project-management:DEC-007-checkbox-validation]). It attests that the reviews ran, and the person checks that against the description before accepting.

**Why an agent that follows a definition of its own waits.** Three questions stand open for such an agent, as the Implications say. A seat's agent meets the first and the third. It would write into a folder another agent owns, under a definition that sends architecture decisions elsewhere. The build command's builder meets all three. Built by either before a record settles them, a foundation's records would rest on a reading of COR-013, and of the agents' definitions, that no record has made. The person builds the Task meanwhile, as they accept its records in any case.

**The cost.** In a project with a topology, a worker no longer builds a foundation's records Task. The person builds it, or a session they direct, and the slices wait on that. A session that may know the project's architecture less well than the architect drafts even the architecture records, and the architect's judgement reaches them only through its review.

### Alternatives considered

- **The architect authors the foundation's architecture records where the project deploys it, and the builder every other record, which the architect reviews.** Not taken. It splits records whose choices depend on each other between two authors. Each architecture record would have no other judge of its architectural fit than its author. And the architect's tools today hold neither Write nor a shell, to create a record's file.
- **One author either way: the architect authors every record where all of them lie in its folders, and the builder authors them all otherwise.** Not taken. Who authors would turn on where each choice's record lies, which the scope test settles only as the records are written. And the architect's records would have no other judge of their architectural fit.
- **Widen the architect's scope to every folder that a foundation's records lie in,** or to folders a project names for it in the agents overlay. Rejected: it changes a core agent for every project, for one step of one capability's planning. And it would judge the fit of its own records alone.
- **The architect drafts each record's text as advice, and the builder writes the file.** Rejected: it blurs who authored the record, and a review gives the same judgement with one author.
- **Leave DEC-060 point 2 as it stands, each plan judging the case at its gate.** Rejected: the same judgement returns at every foundation, and a plan's gate keeps no rule for the next plan.
- **A worker seat's agent authors the records in its own session, as the worker's loop has it build every Task.** Not taken here. The seat meets two of the three open questions, which are the follow-up record's to settle.
- **Decide here how an agent that follows a definition of its own builds a records Task.** Not taken. The first open question is core's, under COR-013. The second changes how DEC-063 runs its reviewers and its fix rounds. The Implications name the first candidate.

## Implications

- **DEC-060** gains a top line saying it is partially superseded by this record, for point 2's line on who authors the records. Point 2 stays as it stood.
- **DEC-059 point 2 and DEC-063 point 1** each gain a sentence with a forward pointer to point 3: no seat, and no build command, builds a Task that holds a foundation's records.
- **The anchored artefacts.** The top line and the two refinements flag the artefacts anchored on DEC-060, DEC-059 and DEC-063, and the change that adds them answers each.
- **Acceptance.** This record overturns part of the accepted DEC-060 and narrows the accepted DEC-059 and DEC-063, so accepting it needs the maintainer's sign-off. It, DEC-060's top line and the two refinements land in one change, accepted together.
- **The pm skill.** Batch planning's "The records come first" says who builds the records Task, who authors and who reviews the records, and gives the Task the reviews' criterion. The worker's loop, on a Task that holds a foundation's records, builds none of it, says so on the Task and leaves it to the person.
- **No agent's definition changes.** The architect's scope stays as COR-024 and COR-025 set it. The project-manager agent builds no records Task, so its line sending architecture decisions to the architect or a human stands. Nor do COR-013, COR-024 and COR-025 change.
- **No command changes.**
- **Named, and not decided here: whether and how an agent that follows a definition of its own builds a foundation's records Task.** A record of its own decides it, and point 3 holds such a Task until then. That record settles three questions:
  - **An agent writing into a folder another agent owns.** COR-013 gives each managed path exactly one owning agent (point 2), and the architect owns its architecture records' folder. Software-engineering's [software-engineering:DEC-004-skeleton-conventions-in-corpus] point 4 keeps its own agent's corpus entries out of a path another agent owns. Whether a seat's agent or a builder agent may write an architecture record there, under the architect's review, is core's to settle.
  - **How the reviews' findings reach the build command's builder.** The builder may start no agent (DEC-063 point 4), and its run has ended by the time the seat could start the reviews. The seat may not edit the records itself, under the provenance check (point 1). A fix round's brief carries only the blocking findings of the verdicts (point 3).
  - **The agents' own definitions.** The project-manager agent sends architecture decisions to the architect or a human. Software-engineering's producer, where the records leave an architectural choice open, makes none in its place and says so on the Task (its definition, "When you build a walking skeleton"). The build command's builder never guesses a decision that is not its own, and a question about a record or a shared choice is the person's (DEC-063 points 5 and 6).
  - **The first candidate, for the build command.** On a records Task, the critic and the architect run as reviewers that give verdicts, so their blocking findings reach the builder through the fix round that exists. It must weigh two things. COR-024 has the critic review a draft before a person sees it, not a diff. And a fix round carries only blocking findings, where point 2 has the builder settle every finding.
