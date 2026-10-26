---
id: DEC-058
title: Shared state that changes while agents work lives in state issues, outside the work hierarchy
status: proposed
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** several agents, each in a clone of its own, share one project through GitHub. Some of what they share changes while they work and belongs to no issue of work, such as which clone holds a seat of the project's topology. This record gives such data a home: a **state issue**, one for each piece of shared state, outside the hierarchy of work and its lifecycle. Its comments log each change, and its description shows the current value rebuilt from them, the way an issue's owner is kept ([project-management:DEC-043-ownership-substrate-selection] points 3 and 4). Where the state says who holds something, a clone claims it and gives it up with events shaped like an instance's claim on a Task. The first claim on a free state holds, and a later one while it is held counts for nothing. What a person reviews before it binds stays in committed configuration.

## Context

Clones of one project coordinate through GitHub, the substrate they share ([project-management:DEC-003-github-bound-substrate], [project-management:DEC-035-instance-ownership]). The project's committed configuration is the other place they share. A person reviews a change to it, and a clone sees the change once it reads the default branch.

Some shared data changes while agents work, with no review of each change, and belongs to no issue of work. Running agents in parallel needs one such piece at once: which clone holds each seat of the project's topology ([project-management:DEC-059-topology-of-seats] describes the topology). Neither home the capability has fits it:

- **Committed configuration** needs a commit and a merge for each change, and a clone sees the change only once it fetches. Two clones that change it at once conflict.
- **An issue of work** carries a type, a parent, a classification and a state in the lifecycle. The rules for work would refuse a piece of state, or count it as work in every listing and plan.

The capability already keeps one piece of changing shared data on each issue of work: its owner, in a log of comments with a summary in the description ([project-management:DEC-043-ownership-substrate-selection] points 3 and 4, and [pkit:ADR-041]). GitHub creates each comment whole, each comment names its author, and the log keeps its history. The maintainer decided on 26 October to use that pattern for any shared data that changes at run time, in an issue of its own (#512). In his words, a "living state issue".

## Decision

**A piece of shared data that changes while agents work, with no review of each change, and that belongs to no issue of work, is kept in a state issue: an issue outside the work hierarchy, whose comments log each change and whose description shows the current value. What a person reviews before it binds stays in committed configuration.**

### 1. What a person reviews is configuration, and what changes at run time is a state issue

Data that a person reviews before it binds is committed configuration, read from the default branch, the project's settled state ([pkit:COR-054]). An example is the seats a topology declares. Shared data that changes while agents work, with no review of each change, and that belongs to no issue of work, is kept in a state issue. An example is which clone holds a seat. Each datum lives on one side only: configuration never records who holds what, and a state issue never holds a value that configuration declares. State that an accepted record already places stays where that record places it, such as an issue's owner on the issue itself. A record that adds a piece of shared state says which side it is on, and for a state issue it names the key, who may change the state, and how a reader finds the state issue (point 2).

### 2. A state issue holds one piece of state, named by its key

- **One piece, one key.** Each state issue holds one piece of shared state, named by a key, such as a seat's name.
- **The marker.** A hidden stamp this capability owns says that the issue is a state issue, and gives its key. It sits in the issue's first comment, and in its description outside the part that is rewritten, so every rewrite keeps it. It needs no label, so a repository that cannot create labels holds state issues too ([project-management:DEC-043-ownership-substrate-selection] point 2).
- **Finding it.** A reader finds a state issue by a number that configuration records, or by its marker, through a listing that GitHub's search index plays no part in, since search results lag.
- **Two for one key.** Where two state issues carry one key, the one GitHub numbered first holds the state. A reader that finds state issues by their marker lists them again before it claims and when it reads after claiming, and writes only to the first.

### 3. It sits outside the work hierarchy and the lifecycle

A state issue holds no work. It takes none of the issue types of the hierarchy, and has no parent and no children ([project-management:DEC-004-six-level-hierarchy]). The rules for an issue of work do not bind it: its classification, its title and body, its state in the lifecycle and its place on the board. This capability's one read of its issues leaves state issues out by their marker, so every listing, check and plan of work gets the issues of work alone. The cascade never reaches a state issue, since it has no parent and no children, and the engine reads no marker. Like an issue's owner, a state issue is never an input to a gate, a move of the lifecycle or the cascade ([project-management:DEC-035-instance-ownership] point 8). A state issue is closed once its state leaves use, and one closed by hand while its state is in use is reopened by the next command that writes to it.

### 4. The comments are the record, and the description shows the current state

- **Each change is one comment,** created whole, with the machine stamp and a line a person reads, built by the audit-log facility ([project-management:DEC-044-audit-log-facility]). Clones that each post their own comment never overwrite each other. This capability never edits a comment on a state issue.
- **A comment counts only when its author may write it,** read from GitHub's record of the comment: a member where the membership gate is closed ([project-management:DEC-021-team-membership-gate]), and otherwise an account with write access to the repository.
- **The current state is the fold of the counted comments,** in the order of their ids, which is the order GitHub lists an issue's comments in.
- **The description shows that state,** derived from the comments and rewritten whole. A stray edit to it is rebuilt, and nothing is lost ([project-management:DEC-043-ownership-substrate-selection] point 4).

### 5. A claim on a state issue takes the shape of a claim on a Task

Where the state says who holds something, such as a seat, a clone claims it and gives it up through the audit-log facility, with event types of its own. They take the shapes of a Task's claim and release ([project-management:DEC-043-ownership-substrate-selection] point 3), and add a release by force:

- **The mark:** a claim is an ownership event in the state issue's comment log, whichever substrate the selector names for issues of work, since a label carries no author and no order of its own.
- **The claimant:** a claim names the account, and a key that the clone generates the first time it claims and keeps beside its instance id, never committed ([project-management:DEC-035-instance-ownership] point 1). So a read after a claim tells one clone's claim from another's under one account, whether or not either clone has an instance number. The claim also says where the clone lies, in words a person reads, such as its machine and folder.
- **The guard:** a clone acts under a claim it holds, and never under one it does not. A command that acts as the holder reads the claim first, and refuses a clone that does not hold it.
- **The release:** the holder's release event frees the state. The record that adds the state says whether a claim also lapses, and when.
- **The release by force:** an event of its own, carrying its reason. The record that adds the state says who may release by force. Taking over is a release by force and then a claim, two events. A claim by another clone between them holds, as point 6 says.

Two clones that share one key, such as copies of one snapshot, cannot be told apart. Whoever copies a clone clears its runtime file, as for its number. Like DEC-035's guard, which is no lock, this guard catches the mistakes of clones that follow the procedure, and is no security boundary.

### 6. The first claim on a free state holds

The fold reads the counted comments in order. While the state is free, the first claim makes its claimant the holder. While the state is held, another clone's claim is void, and stays void after the holder releases. The holder's release, or a release by force, frees the state again, and the next claim after it holds. A clone that claims reads the state issue again after writing, and finds that it holds, or that another clone does. It then goes on without writing anything more. A Task keeps DEC-035's tie-break by the lower number ([project-management:DEC-035-instance-ownership] point 6).

## Rationale

**Why an issue, not committed configuration.** A value that changes several times a day would need a commit, a review and a merge each time. A clone would see it only after fetching, and two clones writing it at once would conflict. Reviewed configuration is the right home for what a person decides, such as the seats, and the wrong one for what agents change as they work.

**Why outside the work hierarchy.** A piece of state is never built, reviewed or landed. Under the rules for work it would need a type, a parent and a state, and it would show up in every listing and plan as work to do. Leaving it outside keeps both clean: the work rules stay as they are, and the state carries none of them.

**Why the comments hold the record, and the description a view.** This is DEC-043's reasoning, applied again. A description is one object, read and written whole, so two clones writing it at once lose a write. Comments are created whole, one per change, and each names its author. So the log survives concurrent writes, shows who wrote what, and keeps the history. The description gives the current value at a glance, and is safe to rewrite because it is not the source of truth.

**Why one issue for each piece of state.** Each piece is then read and written alone. A clash over one seat touches no other, and the log of one seat stays short enough to read. One issue for all the state would put every clone's writes on one thread, and every read would fold all of it.

**Why the first claim on a free state, and not the lower number.** A claimant may have no instance number, since a piece of state may be the very thing that gives a clone its identity. So the tie-break cannot rest on a number. DEC-035 rejected an earliest-claim-wins tie-break because it "needs event-history reads and ties on the same second". Here the comment log is the history the fold reads anyway, and two comments never share an id.

**Why a later claim is void, and the loser writes nothing.** If a loser had to release its own claim, a loser that died before it did so would hold the state once the winner released. A void claim leaves nothing behind, whatever happens to the clone that made it. A read that lags can let a later claimant believe it holds the state. Every command that acts as the holder reads the claim first, so that belief lasts until the claimant's next command.

**Why the shape of a Task's claim.** A claim and a release take the shapes the ownership log already holds, built by one facility ([project-management:DEC-044-audit-log-facility]). The rest differs, and says so. A Task's fold goes to the last authentic event, counts only the assignee's comments, and breaks a tie by the lower number ([pkit:ADR-041]). A state issue's fold keeps the first claim on a free state, counts any author who may write, and orders by comment id.

### Alternatives considered

- **A committed file for run-time state.** Rejected: a commit and a merge for each change, conflicts between clones, and a lag until each clone fetches.
- **A store outside GitHub, or a Projects field.** Rejected: the capability binds to GitHub's issues ([project-management:DEC-003-github-bound-substrate]). A Projects field is not on every repository, as DEC-043 found for the ownership marker.
- **One state issue for all run-time state.** Rejected: every clone's writes on one thread, and every read folding all of it.
- **The description as the record.** Rejected by DEC-043: a write to the description replaces it whole, so concurrent writes are lost.
- **A label as the mark of a claim on a state issue.** Rejected: a label carries no author, and a repository may not be able to create one.
- **The lower number wins a claim on a state issue.** Rejected: a claimant may have no instance number.
- **Each loser releases its own claim.** Rejected: a loser that dies first leaves a claim that holds the state later.

## Implications

- **A schema of this capability** holds the marker's form, the key and the event types of a state issue. The machine stamp is the audit-log facility's ([project-management:DEC-044-audit-log-facility]).
- **A seam of its own.** The fold of a state issue's comments, and the rewrite of its description, form a sibling of the ownership read seam ([pkit:ADR-041]), pinned by a new architecture record. ADR-041 is refined in place so that its event writer, the audit-log facility's builder, serves both. The architect authors both once this record and DEC-059 are accepted, before the build. The new record also says what a read of a state issue before each write costs, and whether one run may reuse it. This share of the change to ADR-041 is accepted under the maintainer's sign-off that DEC-059 needs.
- **Authenticity by write access** needs a read of each author's permission on the repository, kept for the run, since GitHub's association of a comment's author does not prove write access.
- **One read leaves state issues out.** The exclusion lives in the one read of issues that every consumer goes through, never in each consumer, as the one reader of labels does ([pkit:ADR-026]). So no check of an issue of work, such as those of [project-management:DEC-019-mandatory-issue-state], ever sees a state issue.
- **Finding state issues by their marker,** where no number is recorded, lists the repository's open issues, with no label to narrow the list. A record that adds state read often records the number instead.
- **The clone key** joins the instance id in the clone's git-ignored runtime file ([project-management:DEC-035-instance-ownership] point 1, refined in place).
- **The first piece of state** is which clone holds each seat ([project-management:DEC-059-topology-of-seats]). This record adds no command of its own.
- **No behaviour changes** until a state issue is built, so the record lands with a `none` changeset.
