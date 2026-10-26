---
id: ADR-071
title: A state issue is read and written through one seam of its own, beside the ownership seam
status: proposed
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** this record is how project-kit builds a state issue ([project-management:DEC-058](../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md)). One module, the state-issue seam, does every read and write of a state issue. It sits beside the ownership seam ([ADR-041](ADR-041-instance-ownership-substrate-contract.md)). The two seams share one reader of an issue's comment log and one event builder, the audit-log facility's.
- **Its reads:** a state issue found by its number, or by its marker through the one read of issues. Each read takes the whole comment log, judges each author's right to write, and folds the counted comments to the current state.
- **Its writes:** a new state issue, one comment for each change, the description's region rewritten whole, and a reopen or a close.
- **The substrate:** comments, always, whatever substrate the ownership selector names for issues of work.
- **The marker and the key:** a hidden stamp in a comment and in the description, which names the kind of state and its key. One function reads it, and every read of issues tells a state issue by it.
- **What it never reads:** GitHub's search index, a clock, any configuration, the clone's runtime file and any issue of work. The caller passes the issue's number, the key, the members, and the clone's key and place.
- **The cost:** a read is one call for each hundred comments, and one call for each author the run has not yet judged. A run is one command, from its start to its exit. It reads a state issue before its first write as the holder, and reuses that read until it waits on something outside it.

## Context

DEC-058 keeps shared state that changes at run time in state issues, outside the work hierarchy. Its Implications ask for a seam of its own, a sibling of the ownership seam that ADR-041 pins, in a record authored before the build. [project-management:DEC-059](../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md) adds the first piece of such state: which clone holds each seat. Neither record says:
- which module reads and writes a state issue, and which other code it may read
- how a read gets the whole log, and how it judges an author's right to write
- where the marker lives, and which code reads it
- what a read before each write costs, and whether one run may reuse it

The two folds differ in the rules DEC-058's Rationale names. A Task's fold goes to the last authentic event, counts only the assignee's comments, and breaks a tie by the lower number. A state issue's fold keeps the first claim on a free state, and counts any author who may write. Both read the same kind of log, and both post the same shape of comment.

## Decision

**A state issue is read and written only through one seam of its own, beside the ownership seam. The seam reads a state issue, the listing of issues that finds one and GitHub's record of its authors, and takes everything else from its caller. It shares the reader of a comment log and the audit-log facility's event builder with the ownership seam.**

### 1. One module reads and writes every state issue

- **The module.** A module of its own in the capability's library, beside the ownership seam's module, does every read and write of a state issue. No other code reads a state issue's log, builds its marker or writes its description.
- **Its callers** are the capability's commands and modules. They include the commands that create, take, release and list seats (DEC-059 Implications), and every command that confirms its clone's seat before it writes (DEC-059 point 6).
- **The two seams stay apart.** Neither seam calls the other. A caller that needs both reads each one, and passes what one returns to the other, as ADR-041 point 7 says of the seats' holders.
- **What they share.** The state-issue seam reads each log through the reader that pages the ownership seam's logs (ADR-041 point 1), so both seams mean one thing by a log read whole (point 3). One builder builds and parses both seams' event comments (ADR-041 point 3). Each seam keeps a fold of its own.
- **The snapshot.** The module that reads the topology also builds each run's inputs for both seams: the members, the clone's key and place, the seats' holders and the time of reading, which is GitHub's (ADR-041 point 7). Commands take those inputs from it, and never read them on their own (point 8).
- **The guard** has the two halves ADR-041's Implications set for the ownership writes. A construction test holds that the callers obtain each write from the seam. A scan of the scripts holds that no code outside the seam and the shared builder builds a state issue's marker, an event comment for it or its description's region.

### 2. A read finds a state issue by its number, or by its marker

- **By number,** where configuration records one, as the topology does for each seat (DEC-059 point 3). The caller passes the number and the key. The read accepts the issue where the earliest marker comment from an author who may write names that key (points 3 and 6). A marker comment from an author who may not write is passed over. Otherwise the read reports that the issue is no state issue for that key.
- **By marker,** where no number is recorded. The seam asks the one read of issues for the state issues among the open ones, never GitHub's search, whose results lag (DEC-058 point 2). It keeps those whose description names the key, and reads each as by number.
- **Two for one key.** The issue GitHub numbered first holds the state (DEC-058 point 2). A caller that finds state issues by marker lists them again before it claims, and again when it reads after claiming. It writes only to the first.
- **A creation left half done** is found by its description's marker, as by marker above. The creating command, run again, finishes it.

### 3. A read takes the whole log, and counts only what an author who may write wrote

- **The whole log.** The shared reader pages an issue's comments to their end, in the order of their ids, which is the order GitHub lists them in. For each comment it gives the id, the author's login, the time GitHub records for its creation and the body. A read that cannot reach the end reports itself incomplete, and no fold reads comments from a listing, which may return a log cut short.
- **What counts.** A comment counts only where its body carries a state-issue event's stamp that names this issue's key, and its author may write. The seam judges the stamp first, and asks about an author only for a comment that carries one. A comment's present text counts, whoever edited it (Rationale, "Why an edit is not judged").
- **Who may write, where the membership gate is closed:** an author whose login a member's entry names ([project-management:DEC-021](../../../.pkit/capabilities/project-management/decisions/DEC-021-team-membership-gate.md)). The caller passes the members as the default branch holds them, the project's settled state, as for the topology (DEC-059 point 1). It passes the gate's mode too, as the members or as open, so the seam never infers it. DEC-021's check of who runs a command reads the members as that record leaves it, so on a branch that edits them the two readings can differ.
- **Who may write, where the gate is open:** an account that GitHub records as having write access to the repository, or more. The seam asks GitHub once for each such author in a run, and the run keeps the answer.
- **An answer and a failure.** A definite answer that the author has less than write access, and a comment whose author no longer exists, count as an author who may not write. Only a call that fails, such as on the network or a token that cannot read permissions, makes the read incomplete, and the outcome names the cause. The read never drops a comment for a failed call, since dropping a claim could free a held state.
- **Judged when read.** GitHub keeps no history of an author's access, so the seam judges it at reading. An account that loses its access, or is deleted, stops counting in every log it wrote in, and the fold reads those logs again without it (point 4).

### 4. The fold keeps the first claim on a free state

The fold is a function of the counted events alone, in their order (DEC-058 points 5 and 6).
- **A claim** on a free state makes its claimant the holder: the comment's author, the clone's key and the place the claim names. A claim by the holder's account and key changes nothing. Any other claim on a held state is void, and stays void after the holder releases.
- **A release** frees the state where it names the holder's account and key. Any other release is void.
- **A release by force** frees the state that holds when it lands, from any author who may write, and carries its reason. A caller reads the holder just before it writes one, so a holder that changes in between is the one it frees. Whether its author may release by force is the caller's check (DEC-059 point 5), since the fold cannot tell a person from an agent under one account.
- **No clock.** A state lapses only where the record that adds it says so, and no record does, so the fold takes no time. A state that lapses would take the time of reading from its caller, as the ownership fold does (ADR-041 point 7).
- **What it returns:** the holder, or that the state is free. It keeps the counted events, the void ones marked, for a person to read.

A comment that leaves the log changes the fold, and the fold reads what remains. A comment leaves when it is deleted, when an edit removes its stamp, or when its author stops counting (point 3).
- **A void claim may then hold,** where the removal makes it the first claim on a free state, even after its clone has moved on.
- **An earlier holder may return,** where the removal takes away the release by force that freed it, such as one by an organizer whose account was removed.

Like the guard, the fold catches the mistakes of clones that follow the procedure, and is no security boundary (DEC-058 point 5). A person mends a seat whose holder such a removal changed with a release by force (Implications).

### 5. Each write is built in one place

- **The substrate.** Every event is a comment in the state issue's log, whatever the ownership selector names for issues of work (DEC-058 point 5).
- **The builder.** The audit-log facility's module builds each event's comment from its type and payload, and parses a comment back into an event or nothing ([project-management:DEC-044](../../../.pkit/capabilities/project-management/decisions/DEC-044-audit-log-facility.md) points 1 and 2). It builds the ownership seam's events too (ADR-041 point 3). The seam's writer posts each comment and reports the outcome.
- **The frame.** Each event's comment carries DEC-044's machine stamp, which holds the event's fields. It also wears the frame of [project-management:DEC-052](../../../.pkit/capabilities/project-management/decisions/DEC-052-comment-house-style.md): its kind's marker and the provenance footer. Each event type is a kind in DEC-052's roster.
- **The payload.** A state-issue event's stamp names the state's key, the clone's key and the clone's place, and a release by force names its reason. The stamp's grammar encodes free text, so no value can end the stamp.
- **One act, one id.** Each event's stamp also carries an id that the run makes once for that act. So the skip of a comment already posted, in DEC-044 point 2, finds a retry of the same act, and never a second act with the same fields, such as a clone's second claim after a release. The fold reads no time from the id.
- **A retry** after a failed post reads the log first, and posts nothing where the event landed.
- **Always posted.** The events are the state's record (DEC-058 point 4), never a projection, so the setting of [project-management:DEC-049](../../../.pkit/capabilities/project-management/decisions/DEC-049-audit-journal-model.md) point 2 never holds one back.
- **The description** holds the marker, a region that shows the state and the provenance footer. Every write of it goes through the provenance seam ([ADR-037](ADR-037-provenance-write-path-contract.md)). After each event it posts, the seam rewrites the region whole from the fold of its next read. A read that finds the description's marker gone restores it, the one write a read makes.
- **A new state issue** has a title for people, the description, and the marker's comment, posted first, right after the issue is created. [project-management:DEC-041](../../../.pkit/capabilities/project-management/decisions/DEC-041-version-provenance-stamp.md)'s filing comment follows it. The issue takes no type and no parent (DEC-058 point 3), and needs no label (DEC-058 point 2). This record adds that it takes no assignee and no milestone, since nothing reads them.
- **Reopen and close.** A write to a closed state issue reopens it first (DEC-058 point 3). The seam closes a state issue only when its caller says that its state has left use. A person closes a stray one, such as one that no seat names, on GitHub, since no command of the lifecycle acts on a state issue (DEC-059 point 3).
- **A claim** is a read, the claim's comment, and a read again that finds who holds the state (DEC-058 point 6). The claimant writes no further event, whatever the second read finds.

Two writes at once can leave the region showing a state one event old, until the next write rewrites it. The region is a view, and nothing reads it as the state (DEC-058 point 4).

### 6. One function reads the marker, and every read of issues uses it

- **What the marker names:** that the issue is a state issue, the kind of state, its key and the marker's version. The kind keeps two kinds of state from sharing a key, such as the seat `planner` and a later state named alike. A key is matched exactly, case included. The marker's written form is the capability's schema (DEC-058 Implications).
- **Where it sits:** in the marker's comment, which GitHub records with its author, and in the description, outside the region the seam rewrites (DEC-058 point 2). The comment's marker decides what a read accepts, and the description's marker is the one a listing sees.
- **The function.** One function in the seam's module takes a text, a description or a comment, and gives the marker's kind, key and version, or nothing. It reads no GitHub and imports no helper that does. No other code parses the marker, and the marker is no event, so the fold passes over it.
- **Every read of issues** tells a state issue by that function. The one read of issues that every consumer goes through (DEC-058 Implications) lists them, and a command also reads a single issue by its number, or the board. All three shapes of read call the function, so a state issue reaches none of them as work.
- **What a caller gets:** the issues of work, and only the state-issue seam asks for state issues. A command that would write to a state issue as to an issue of work refuses it, and a check passes over it as no work.
- **What it costs.** A marker removed from a description by hand puts that state issue in the listings of work until the seam's next read or write restores it. A marker pasted into an issue of work takes that issue out of them, and the listing of seats names it among the state issues no seat names (DEC-059 point 3). The marker catches mistakes and is no security boundary, as DEC-058 point 5 says of the guard.

### 7. What the seam never reads

- **GitHub's search index,** whose results lag (point 2)
- **The description as the state.** The seam reads the description for its marker and to rewrite the region, and never takes the state from it.
- **A state issue's labels, issue type, parent, assignee, milestone and board fields**
- **GitHub's association of a comment's author,** which does not prove the right to write (DEC-058 Implications)
- **A time,** from a stamp or a clock
- **An issue of work, or the ownership seam's fold** (point 1)
- **The topology, any other configuration and the clone's runtime file.** The caller passes the issue's number, the key, the members, the gate's mode, and the clone's key and place.

### 8. What a read costs, and how long a run keeps it

- **A run** is one invocation of one command of the capability, from its start to its exit.
- **A read** is one call for each hundred comments in the log, and one more for the description and whether the issue is open. A seat's log grows by two comments each time a clone takes the seat and releases it, and by one for each claim that loses. So a read stays one or two calls for a long time.
- **The authors.** Where the membership gate is open, each author of a stamped comment that a run has not yet judged adds one call. The run keeps each answer, and no answer outlives the run.
- **Before a write as the holder,** a run reads the state issue once, before its first such write, and reuses that read for its later writes. A run that waits on something outside it, such as a check, a review or a person's answer, reads again before its next write. DEC-058's Implications leave this reuse to this record, and every command confirms its seat before its first write (DEC-059 point 6).
- **One snapshot.** The run reads its own seat, the seats' holders it needs and the time of reading at its start, and reads them again after a wait. A command on one Task reads the seats that Task's claims name right after it reads the Task's log (ADR-041 point 7). So one run judges every claim against one state of the seats, at one instant.
- **A claim's second read** always follows the claim's comment, and is never a read taken before it.
- **Across runs** nothing is kept. So a release by force stops the holder at its next command (DEC-058 point 5).
- **The seats' holders** that the ownership fold takes cost one read for each seat the run needs. A command on one Task reads the seats its claims name, and the shared pool reads every seat (ADR-041 point 7).

### 9. The seam is failure-posture-neutral, and serves the capability's commands alone

- **Neutral outcomes.** A read reports a fold, an incomplete read with its cause, or a failure, and the outcome of restoring a missing marker where it did. Each write reports that it wrote or that it failed, and the rewrite of the region also reports that it rebuilt a region a hand had changed. Each caller decides what an outcome means, as ADR-041 point 5 says of the ownership seam.
- **Never the engine's.** A state issue is never an input to a gate, a move of the lifecycle or the cascade (DEC-058 point 3). The engine reads no marker, and the seam has no caller in it.

## Rationale

**Why a seam of its own.** The two folds differ in which claim holds and in whose comments count, in every project. One fold holding both would carry two contracts in one place, and a change to one could reach the other. The two seams share what is truly the same, the reader of a log and the builder of a comment, and keep a fold each, testable alone.

**Why one reader of a log, and one builder.** Both seams need a log read whole, with one meaning of incomplete, so two pagers would drift. Both post the same shape of comment, and DEC-044 makes one builder for every such comment. The builder parses what it builds, so the stamp's grammar and its version have one owner.

**Why the seam reads no configuration.** A fold whose inputs all come from its caller is tested with no GitHub and no configuration. The module that reads the topology reads the members too, once, from the default branch, so every clone judges by the same settled state. The seam then serves any state that says who holds something, since it knows no seat. A state of another shape adds its own fold behind the same reads and writes.

**Why the whole log.** A fold of a log cut short could miss the holder's release, or the claim that holds, and name a wrong holder. An incomplete read stops its caller, which costs a retry, never a wrong holder.

**Why an edit is not judged.** A comment's author may edit it, and so may any account with write access to the repository. Where the membership gate is closed, such an account may be no member, and its edit then speaks under a member's login. The guard is no security boundary (DEC-058 point 5), so this record accepts that. Dropping an edited comment would cost more: a typo's fix would free a held state, and a void claim could then hold, which DEC-058's Rationale refuses ("Why a later claim is void").

**Why a failed call stops the read, and a definite answer does not.** Dropping the author's comments on a failed call could turn a held state free, and a second clone would then take it. A retry mends a failed call. A definite answer never changes on a retry, so treating it as a failure would leave the state unreadable for good.

**Why each act carries an id of its own.** DEC-044's skip of a comment already posted suits a retry, whose second copy says nothing new. Two claims, or two releases, by one clone carry the same fields and are still two acts. Skipping the second would lose a release, and the seat would stay held. An id made once for each act keeps the skip for retries, and keeps it from ever merging two acts.

**Why a run may reuse its read.** The guard catches the mistakes of clones that follow the procedure, and is no lock (DEC-058 point 5). A run that waits reads again, so a reused read is never older than the run's own work since its last wait. A release by force lands between commands, and the next command reads afresh. Reading before every write would multiply the calls of a command that writes many times, such as one that files a tree of issues, with no gain the guard promises.

**Why the region is rewritten after a write.** The state changes only when an event lands, and the seam posts every event itself. A rewrite on every read would make each read a write, and each listing of seats a burst of writes. A missing marker is the exception, since a missing marker lets the state issue into the listings of work.

**Why the marker's comment comes first.** A read accepts an issue by the earliest comment that carries a marker. Posting it right after creation keeps DEC-041's filing comment, and any other comment, from deciding what the issue is.

**Why one function reads the marker.** Every read that leaves state issues out, and the read that accepts one, must agree on what a state issue is. Two parsers could disagree, and a state issue would then reach a listing of work. A function that reads no GitHub can be built and tested apart from the reads that call it.

### Alternatives considered

- **Widen ADR-041's seam with a mode for state issues.** Rejected: two contracts in one fold, as "Why a seam of its own" says.
- **A fold that reads the topology to learn its seat.** Rejected: the seam would serve one piece of state only, and its tests would need the configuration.
- **Read each log from a listing's comments.** Rejected: a listing may return a log cut short.
- **Drop an edited comment.** Rejected: a typo's fix would free a held state, as "Why an edit is not judged" says.
- **Each event names the last counted event it read,** so a claim counts only on the state its claimant saw. Not taken: a claim on a free state could then be void, which DEC-058 point 6 does not allow. It would keep a void claim void after a removal, and a release by force on the holder it meant.
- **Keep a read across runs, in the clone.** Rejected: a release by force would not reach the holder's next command.
- **Read before every write.** Rejected: more calls, with no gain the guard promises.
- **Find a state issue through GitHub's search.** Rejected by DEC-058 point 2, since search results lag.
- **Rewrite the region on every read.** Rejected: every read would become a write.
- **Members from the working tree.** Rejected: a Task's branch that edits the members would fold a seat differently from the default branch, and clones would disagree about its holder.

## Implications

- **#2138** builds the module of point 1: its reads, its fold, its writes and the function that reads the marker, with tests that fake `gh`. With it come:
  - the reader of a comment log, paged to its end, which both seams use
  - the audit-log facility's builder and parser, with the state-issue event types, and the ownership events moved onto it with the new ownership stamp (ADR-041 point 3)
  - the event types as kinds in DEC-052's roster, in its table or in the schema the roster moves to, whichever holds the roster then
  - the capability's schema for the marker, the kind, the key and the event types
  - the clone's key in the clone's runtime file
- **#2139** builds the one read of issues, and the single issue's read and the board's read beside it, each calling the marker's function (point 6). The function lands with #2138 first, or with #2139 if #2139 lands first.
- **#2140 and #2141** build the module that reads the topology and each run's inputs, and the seam's first callers: the command that creates the seats' state issues, and the commands that take, release and list seats.
- **ADR-041** holds the ownership seam's share: its point 3 makes the audit-log facility's builder build both seams' events, and its point 7 has the ownership fold take its inputs from its caller.
- **The project-management README** describes state issues when #2138 lands, as #2138's Doc impact says. It tells a person two things no code enforces:
  - after an account loses its access or is deleted, check the listing of seats, and release by force each seat whose holder changed (point 4)
  - a Task that a board's automation moves back to In Progress may lapse at once (ADR-041 point 7)
- **Acceptance.** This record is accepted before #2138 and #2139 build on it. Its acceptance also confirms two readings of accepted records that point 5 makes:
  - one DEC-044 machine stamp inside DEC-052's frame, each event type a kind of DEC-052's roster
  - state-issue events as the state's record, which DEC-049 point 2's setting never holds back
- **No behaviour changes** until #2138 lands. This record changes no code.
