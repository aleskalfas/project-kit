---
id: DEC-065
title: The forward cascade writes nothing to an ancestor the board does not place, and the move stands
status: proposed
date: 2026-10-31
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where a project's board carries the issue state, the forward cascade can reach a container whose card says nowhere it stands. The cascade then writes nothing to that container, and tells the person which state to set on its card. The move that started the cascade stands, and the cascade goes on to the containers above.

A board that does not answer at all is different: it is a broken tool. The move still stands, but the cascade stops at that container. The run ends with the code that says a re-run finishes the cascade.

So the promise that a container is never behind its work ([project-management:DEC-006-state-machine-and-cascade]) gives way at a container the board does not place. This record partially supersedes DEC-006 there. The rule that a position is never guessed stands whole.

## Context

The forward cascade promises that a container is never behind the work under it (DEC-006, "Cascade rule"). When an issue moves forward, each ancestor behind it is brought up to its state, capped at In Progress. An ancestor moves only through the transitions the workflow declares, and each step is journaled from the state it left.

Where the substrate map binds state to the board, an open issue's position is its card's Status ([project-management:DEC-062-axes-chosen-in-the-map] point 5). A read of that Status either places the issue at an open state ([pkit:ADR-074]), or ends in one of four outcomes ([project-management:DEC-051-axis-carriage-activation] point 6). The board cannot be read, the issue has no card, its card has no Status, or its Status names no open state. The last three are **findings** about the issue, and the first is a fault of the tool.

None of the four is guessed, so no command acts on a position it could not read. At an ancestor the read does not place, that rule and the cascade's promise pull apart. As built, the walk stops there with a warning, and the move that started it stands. So that ancestor, and every container above it, stays where it was, possibly behind the work.

ADR-074 leaves which rule gives way to a record of this capability (its Boundaries). Its point 5 sets two limits on every command that reads the state. A command never acts on a guess, and it keeps a board that would not answer apart from a finding. Where its exit codes tell a broken tool from a refusal, an unreadable board takes the broken tool's code. Where the act the command exists for already stands, its code says instead that the act stands and what follows it is owed.

The cascade runs inside **the move command**, the command that moves one issue through the lifecycle. Before it writes the move, it reads each ancestor up the walk and prints its plan. A **composing command**, one that runs the move command as a step, may have written its own changes first, such as a branch or an assignee. After a close, a merge that closes a Task, or a re-run that finishes a cascade, the move that started it has already happened.

## Decision

**Where the board carries the state, the forward cascade writes nothing to an ancestor the board does not place, and never refuses or undoes the move that started it. Above a finding, the walk goes on. At a board that would not answer, it stops, and the run ends with the code that says the move stands and a re-run completes the cascade. The person is told which state to set on the card.**

The four outcomes, as the cascade meets them at an ancestor:

| What the read of the ancestor's card found | Written to the ancestor | The move | The walk above it | What the person is told |
|---|---|---|---|---|
| No card on the board | Nothing | Stands | Goes on | Add the card, with the state it is owed |
| A card with no Status | Nothing | Stands | Goes on | Set the Status to the state it is owed |
| A Status naming no open state, such as Done or Blocked | Nothing | Stands | Goes on | Set the Status to the state it is owed, or close the container where its work is done |
| The board cannot be read | Nothing | Stands | Stops | What the board said, and to re-run once it answers |

### 1. An ancestor the board does not place is written nothing

An ancestor **the board does not place** is one of two kinds. An **unplaced ancestor** is one whose card the board answered for, with a finding: no card, no Status, or a Status naming no open state. An **unread ancestor** is one whose card the board would not answer for. The cascade writes nothing to either: no Status, no card, no journal entry and no comment.

The cascade moves an ancestor only from where it stands, through declared transitions, and journals each step from that state. An ancestor the board does not place stands nowhere the cascade can read. So no declared step leads from it, and no step could be journaled.

### 2. The move that started the cascade stands

No ancestor the board does not place refuses the move that started the cascade, or undoes it. This holds for every move that runs the cascade.

Where the board carries the state, the move is itself a write to the board. A write that fails leaves the move unmade, as for any move. That is the move's own failure, not the ancestor's.

### 3. Above an unplaced ancestor, the walk goes on

A finding is about that ancestor alone. Its record was read, so its parent is not in doubt, and the walk follows it as for any ancestor. A writer stops only at a parent in doubt ([pkit:ADR-035], on a parent the two records do not agree on). Each container above that the read places, and that is behind, is brought level.

The move then ends with the code a move ends with when its cascade is left incomplete for any other cause. That code reports the move, which landed, and the cascade's report gives the finding. A finding is no broken tool, so ADR-074 point 5's rule on codes does not reach it.

### 4. An unread ancestor stops the walk, and a re-run completes it

At an unread ancestor, the walk stops, and nothing above it is read or written. This holds wherever the cascade meets the board's silence, in its plan or after the move landed. The cascade may read an ancestor again just before it writes, to catch a move made since its plan. That read goes through the state's one reader (ADR-074 point 2), so it gives a placed ancestor or one of its four outcomes, each handled as above.

The run then ends with the code that says the act stands and a re-run completes what follows it (the capability's README, "Exit 4 — accepted, a re-run completes it"). ADR-074 point 5 gives a command that code where its act already stands when the board fails. The code is the run's last word: the move's own hooks fire first, as for any move that landed.

A composing command reads that code as its move made, with the cascade owed. It never reports the move as not made. It stops before any step of its own that cannot be undone, such as a merge, and ends with that code itself.

### 5. The person is told which state to set on the card

The cascade names each ancestor the board does not place, and which of the four outcomes it met. For a finding, the remedy lies on the board, and names the state the ancestor is owed. That is the state the cascade would have brought it to: the moved issue's state, capped at In Progress. For a Status naming no open state, closing the container where its work is done is the other way out.

So a person who adds the card, or sets its Status to that state, leaves the container level at once. A card set lower is brought level by the next forward move under the container. It is also brought level by a move of the issue that started the cascade to wherever that issue then stands.

For an unread ancestor, the report gives what the board said, and to re-run once the board answers. It never reports the broken board as a finding about the ancestor, and never reports a finding as a broken board.

The plan printed before the move is written names each ancestor the board does not place, and so does a dry run. Where the move command asks a person at a terminal to confirm the move, that person sees it first, and can set the card before the move.

The report goes to the output of the run, and is posted nowhere else. Each forward move under the container repeats it, and each command that reads the container's state reports its finding too ([pkit:ADR-074], Implications).

### 6. DEC-006's promise binds every container the read places

Where the board carries the state, DEC-006's promise reads: no container the read places is left behind the work under it. An unplaced container is written nothing, and is named with its remedy on each forward move under it, until its card places it. At and above an unread container, no container is read, and a re-run once the board answers brings each level.

The rule that a position is never guessed gives way nowhere. The promise gives way at an unplaced container while its card places it nowhere. It gives way at and above an unread container until a re-run.

### What this overturns, and what stands

This record partially supersedes DEC-006, where the board carries the state. Each overturned passage stays in DEC-006 as it stood.

- **Overturned in DEC-006,** at an ancestor the board does not place, and above an unread one:
  - the Cascade rule's "A container is never behind the work under it", and its "brings any that is behind up to the moved issue's state". Point 6 here replaces them there.
  - the Cascade rule's sentence that a Task's completed close brings "each ancestor behind" up to In Progress, and the same in the `manual-completed` closure trigger
  - the Implications' "forward cascade walks ancestors and bumps any behind"
  - the rejected alternative "Refuse to start a child whose ancestor is unscheduled, or leave the ancestor behind and report it", in its second half. Points 1, 2 and 5 here leave such an ancestor unwritten and report it.
- **Stands in DEC-006:**
  - the promise, and that rejected alternative, for every ancestor the read places, and in every project whose board does not carry the state
  - that an ancestor moves only through declared transitions, each step journaled with the move that caused it
  - that an ancestor at or past the target is left alone
  - that the cascade is not an authorisation and asks for none

## Rationale

**Why nothing is written to an ancestor the board does not place.** Writing would act on a position the read did not give. Setting the card to In Progress decides that the container was behind, which no read said. Adding a card decides the same for a container that has none. DEC-051 point 6 forbids both, since each acts on a guessed position.

A write would also erase what a person put on the board. A Done on an open container may mean that someone meant to close it, and a Blocked column means something to the project that made it. And a journal entry would record a move from no state, which the workflow does not declare.

Where the board carries the state, keeping each open issue's card and Status is the work of the project's people (DEC-062 point 5). A missing card is also a gap in board membership, which DEC-019's own checks find ([project-management:DEC-019-mandatory-issue-state]). So the cascade tells the people which state is owed, and leaves the act to them.

**Why the promise gives way, and not the rule against guessing.** DEC-006 refuses a container behind its work because it states something false to those planning and choosing work. Keeping that promise at an unplaced container would take a write no read grounds. No command reads such a container as behind, since each handles an issue the read gives no position ([pkit:ADR-074], Implications).

A person reading the board may still take a container with no card, or no Status, for one not started. The remedy is what ends that, and each forward move under the container repeats it. Above an unread container the promise waits on the board, which a re-run reads again.

**Why no ancestor stops the move.** A refusal before anything is written is possible only in part. The move command reads every ancestor up the walk before it writes the move. But a composing command may have written its own changes first, and a close, a merge's close and a re-run have already happened.

A real refusal would need every composing command to read the ancestors' cards at its early check. That would tie work to a card nobody doing the work may own. Every Task under the container would be refused until someone set its card. A seat that can start a Task may have no say over a container's card, and would find the same Task ready on its next round.

A column the workflow does not name, such as Blocked, would then stop all work beneath it, a power no record gives it. Without the refusal, such a column costs a warning on every forward move under the container. That noise is the cost of a Status that places nothing. DEC-062 point 5 asks each project to give its Status the five states.

A board that does not answer for an ancestor's card is no reason to refuse either. The move's own write to the board is the test the move needs. Where the board is down, that write fails, and nothing of the move is written, as a refusal would leave it. Where the fault passed, the work goes on, and only the cascade is owed.

**Why the walk goes on above an unplaced ancestor.** The walk follows each ancestor's parent from the ancestor's record, not from its card. The cascade's target comes from the issue that moved, never from an ancestor between. So passing an unplaced ancestor changes nothing the containers above it are owed. Stopping would leave each of them behind the work, the falsehood DEC-006 exists to prevent, and gain nothing.

**Why the walk stops at an unread ancestor.** The parent is known, but every read above it needs the same board. Going on would spend a call on each ancestor above, for a board that has just failed. A re-run once the board answers completes the walk, and repeats nothing done.

**Why the run ends with the code that says a re-run completes it.** A composing command reads the broken tool's code as a move not made. It would report a landed move as unmade, and name its changes for undoing. A code that says the act stands, and that a re-run completes what follows it, reports both truths. It still tells a broken tool from a refusal and from a finding, which is what ADR-074 point 5 protects.

**Why the remedy names the state owed.** The state a container is owed under the work is known: the moved issue's state, capped at In Progress. A person who sets that state leaves the container level at once, with no window in which it reads behind. Its step is a hand edit, not a journaled move, as is every card the project's people set on a board that carries the state.

### Alternatives considered

- **Refuse the move before anything is written.** Rejected: a composing command has written first, and a close, a merge or a re-run has already happened. Making it real would need every composing command to read the ancestors early, the cost of which follows.
- **Refuse at each composing command's early check.** Rejected: one unset card would stop all the work under its container. A seat would find the same Task ready again, and an unnamed column such as Blocked would stop work.
- **Refuse the move where its plan meets a board that cannot be read.** Rejected: the move would wait on a read it does not need, and its own write tests the board already. The same fault would be met two ways, by when it came.
- **Set the ancestor's card to the target, or add a card for it.** Rejected: it acts on a position no read gave, erases what a person set, and journals a move from no state.
- **Set the target only where nothing was set: no card, or a card with no Status.** Rejected: it still decides a position no read gave, and would be a write with no journaled origin. Keeping the cards is the project's people's work (DEC-062 point 5), and board membership is DEC-019's.
- **Post a notice on the unplaced ancestor, once for each finding.** Rejected: the notice goes stale once the card is set, and it would be a comment of a new kind, owed to no governed move ([project-management:DEC-049-audit-journal-model]). Each command that reads the container's state reports its finding already.
- **Ask the person whether to set the ancestor's card.** Rejected: the cascade asks for no authorisation (DEC-006), and most moves run with nobody at a terminal.
- **Fall back to the ancestor's labels or Milestone.** Rejected by DEC-051 point 6: a command would act on a position it guessed.
- **Stop the walk at the unplaced ancestor.** Rejected: it leaves every container above behind the work, though nothing about them is unknown.
- **Go on above an unread ancestor.** Rejected: every read above needs the same board, and a re-run completes the walk.
- **End with the broken tool's code after the move landed.** Rejected: a composing command would report a landed move as not made, and name its changes for undoing.
- **Give a finding the code that says a re-run completes the cascade.** Rejected here: a project that keeps a Blocked column would see every forward move under it end that way. Whether every cascade left incomplete, for a cause other than a board that would not answer, takes that code is a question of its own.

## Implications

- **DEC-006's top line names this record** as partially superseding it, with a pointer to "What this overturns, and what stands". Accepting this record overturns what an accepted record decides, so it needs the maintainer's sign-off.
- **ADR-074 point 5 is refined in place,** and so is ADR-053 point 2, which carries the same sentence. The architect writes the refinement in the change that proposes this record. Where the act a command exists for already stands when the board fails, its code says the act stands and what is still owed. That code is neither success's nor a refusal's. A person accepts the refinement no later than this record, since point 4 rests on it.
- **The cascade's walk** treats an ancestor the board does not place as points 1 to 4 say, in its plan, its dry run and its closing report. The report gives each one's outcome, the state it is owed, and how to finish (point 5). The remedy for a container names no Review, since a container never enters Review.
- **The move command gains the code that says a re-run completes what follows the act,** for a cascade an unread ancestor cut short. Each composing command passes that code on, as point 4 says.
- **The capability's README** says it, where it describes the forward cascade and where it lists the commands that end with that code.
- **Tests** cover each outcome at an ancestor, at the bottom, the middle and the top of the walk:
  - **No card, no Status, and a Status naming no open state:** nothing is written to the ancestor or journaled, the move stands, and a container above that the read places is brought level. The report names the outcome and the state owed, never Review.
  - **A board that cannot be read, in the plan and after the move landed:** the move stands, nothing above is read, the hooks fire, and the code says a re-run completes the cascade.
  - **The move's own write failing:** the move is not made, and the code is the broken tool's.
  - **The composing commands:** each passes the code on and never reports the move as not made, and no merge follows it.
  - **The finish:** a card set to the owed state reads level, and a card set lower is brought level by a move of the issue to where it stands.
- **A surface change** for the capability: the walk goes on where it stopped, and the move command and the commands that compose it gain an exit code. The build's changeset declares it, naming each command. No migration is owed, since no adopter file or schema changes.
- **Not decided here:**
  - what a move to done does on an open issue whose state the board carries, which is [#2304](https://github.com/aleskalfas/project-kit/issues/2304)'s question. Where such a move runs the cascade, this record governs it at an ancestor the board does not place.
  - whether every cascade left incomplete, for a cause other than a board that would not answer, takes the code that says a re-run completes it. ADR-074 point 5 rules that cause. A failed write of an ancestor's state, on the board or as a label, is among those causes, and stays as it is until that question is settled.
  - whether a container whose card reads Review is a finding. The read places it, though a container never enters Review, so the cascade leaves it alone, as DEC-006 leaves any ancestor at or past the target.
  - what a card a person drags by hand means, which DEC-006 leaves open
