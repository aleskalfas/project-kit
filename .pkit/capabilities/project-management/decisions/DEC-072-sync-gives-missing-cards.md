---
id: DEC-072
title: The board sync gives every open issue its card, and writes a Status only where the Status is a projection
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** every open issue belongs on the configured board, yet an issue can be left with no card there: filed outside the capability's commands, its add failed at filing, or its card removed on the board. Where the board's Status is the state's projection, the command that brings the board in line gives such an issue its card and its Status. Where the board holds the state, or the state degrades, that command refuses to run, and no command gives the card. This record has the command give the missing card in every project with a board, whatever carries the state. It writes a Status only where the Status is the state's projection. Where the board holds the state, the card it adds has no Status: the issue then shows on the board with none, and a person sets it there, since no command can read where the issue stands, and none guesses it.

## Context

**The terms.**

- *The configured board*, *the board holds the state*: as [project-management:DEC-070-filing-another-board] defines them.
- *The Status is the state's projection* where a board is configured and the state is carried off it, and *the state degrades* where a present substrate map leaves the state out or marks it unsupported, so that the capability writes no Status ([project-management:DEC-062-axes-chosen-in-the-map] point 5).
- *The board sync* is the command that brings the board's Status in line with the issues' states (DEC-062 point 5).
- *A missing card* is an open issue's lack of a card on the configured board.

**What the records say.**

- **Every issue belongs on the configured board from its filing** ([project-management:DEC-019-mandatory-issue-state]). A missing card on an existing issue is drift, at warning severity, for a person to fix. DEC-019's post-check workflow, where a project installs it and turns its remediation on, adds a missing card with no Status, whatever carries the state.
- **Membership is the board flag's question, never carriage's:** whether an issue has its card turns on a board being configured, not on what carries any axis ([pkit:ADR-096] point 5).
- **Where the board holds the state,** an open issue with no card, or whose card has no Status, has a position that is undetermined. It is reported apart, and never guessed from its labels or its milestone. A seat choosing work skips it, and a move refuses it ([project-management:DEC-051-axis-carriage-activation] point 6).
- **Who writes a Status** (DEC-062 point 5). Where the Status is the state's projection, the capability writes it from the issue's state. Where the board holds the state, a move writes it, from a position it read, and filing writes the first one, the state it files the issue into. Where the state degrades, the capability writes none, and the Status stays with the people who move it.
- **The board sync, when this record was written,** where the Status is the state's projection, reads every card on the board and every open issue, writes the Status on each card that differs, and adds a card for each open issue that has none, then sets its Status. Where the board holds the state, or the state degrades, it refuses, and reads nothing.

**The routes to a missing card.** An issue filed outside the capability's commands, such as in the host's own interface, gets no card from the capability. Filing reads the board before it creates the issue, and refuses where the board did not answer, yet an add can still fail after the issue exists, and filing then exits saying so ([pkit:ADR-096] point 4). A person can remove a card on the board. And a filing that names another board, where DEC-019's override stands, puts the issue there in the configured board's place.

**The gap.** Where the board holds the state, nothing but a person gives a missing card. The issue is absent from the board the people place work on, and only a command's warning names it: a seat skips it, a move refuses it, and the membership check reports it. Where the state degrades, the issue's position is read from the native primitives, so it stays workable, yet nothing but a person gives its card either.

**Where the question came from.** The work on filing onto another board ([project-kit#3205](https://github.com/aleskalfas/project-kit/issues/3205)) named it, and left it to [project-kit#3241](https://github.com/aleskalfas/project-kit/issues/3241).

## Decision

**The board sync gives each open issue with a missing card its card on the configured board, in every project with a board, whatever carries the state. It writes a Status only where the Status is the state's projection. Where the board holds the state, it writes none, so a person sets the new card's Status on the board, and no command guesses where the issue stands.**

### 1. The sync gives every missing card, wherever a board is configured

- **Where.** Where the board holds the state, and where the state degrades, the sync reads every card on the configured board and every open issue, as it does where the Status is the state's projection, and adds a card for each open issue that has none. What carries the state is no ground for a refusal, and nor is a board with no Status field where the sync writes no Status. Where no board is configured, it refuses, whatever the map says.
- **What it leaves alone, and how it asks:** as where the Status is the state's projection. It reads only what it reads there, leaves alone what it leaves alone there, asks before its first write, and writes nothing in a dry run.
- **Why there:** whether an issue has its card is the board flag's question (ADR-096 point 5), so whether the sync gives one turns on a board being configured, and on nothing that carries an axis.

### 2. It writes a Status only where the Status is the state's projection

- **Where the Status is the state's projection:** from the issue's state, on each card that differs and on each card it adds, as DEC-062 point 5 has the capability keep it.
- **Where the board holds the state:** it writes no Status, on a card it adds or on any other. The issue's position stays undetermined until a person sets its card's Status on the board (DEC-051 point 6).
- **Where the state degrades:** it writes no Status, and the Status stays with the people who move it (DEC-062 point 5).

### 3. What it says

- **Its plan** names each card it will add, and, where it writes no Status, says that the card will have none.
- **Where the board holds the state,** the plan says that each added issue's position stays undetermined until a person sets its card's Status on the board, to where the issue stands. It says too that a board's own automation may set a Status on a card when it is added, which every command then reads as the issue's position, so the person checks each added card's Status.
- **After the run,** it names each card it added, and each it could not add, with the board's words.

### What this refines, and what stands

- **Refined in DEC-062 point 5:** its last sentence, "Elsewhere the project's people do both on the board", which reads instead "Elsewhere that command gives each open issue its card, and the project's people set each card's Status on the board."
- **Stands:** DEC-051 point 6, DEC-019's severities and its post-check workflow, ADR-096, and the sync's work where the Status is the state's projection.

## Rationale

**Why the sync gives the card.** DEC-019 puts every issue on the configured board, and that is the board flag's question, not carriage's. A card needs no position to be given, only the board's answer. The sync already reads every card and every open issue to give the missing cards where the Status is the state's projection, and the same read finds them where it is not. The post-check workflow already gives such a card with no Status, whatever carries the state, so this gives the same card from a command a person runs.

**Why no Status where the board holds the state.** The issue's position is undetermined, and DEC-051 point 6 has no command guess it as it reads. A command that wrote a guess onto the board would do worse: the board holds the state, so the guess would then read as the issue's position, and every command would act on it. A person knows where the issue stands, and sets it on the board, as on any card whose Status places it nowhere. The two writers of the Status there each know the state they write: a move reads the position it moves from, and filing writes the state it files the issue into.

**Why the card helps without its Status.** The add changes no issue's position, since an issue with no card and one whose card has no Status are both undetermined (DEC-051 point 6). It brings the issue onto the board the people place work on, where a card with no Status is shown apart, rather than leaving it off the board, named only in a command's warning. What remains is one value set on the board.

**Why a board's own automation does not stop it.** The capability does not control a board's automation, such as one that sets a Status when a card is added. Such automation reaches a card the sync adds as it reaches one a person adds on the board, so keeping the sync from adding cards keeps no issue from it. The sync says so before it asks, so the person checks what the board set.

**Why only when someone runs it.** As where the Status is the state's projection: DEC-019 keeps a scan of every issue's board state out of each command, and the sync is the command a person runs to bring the board level.

### Alternatives considered

- **Keep the sync refusing where the board holds the state or the state degrades, and leave each missing card to a person.** Not chosen. Each issue stays off the board until someone finds it from a command's warning and adds it by hand, one at a time. A project whose agents do its work, with no person at the board, has no way to add one but the host's own commands. It writes nothing on a board that holds the state, but the card this record adds changes no issue's position there either.
- **Give the card, and write the Status a person names.** Not chosen. It places an issue with no position read, so the transitions of the state machine and the gates on them could not apply: an issue could be placed straight into In Progress or Review, past the claim that starting work makes. A command cannot tell a person's word from an agent's guess, since an agent passes an option as easily as a person does, as [project-management:DEC-069-when-fixers-start] weighs for a flag that says a person started a run. It also adds a writer of the state's source that is not a move. A later record can weigh it, should setting the Status on the board prove too costly, such as in a project run by agents.
- **Give the card, and write the Status filing would: Backlog for an issue with a milestone, Todo otherwise.** Rejected. For an issue someone has worked on, that moves it back, and nothing says so. It is the guess DEC-051 point 6 forbids at reading, written where every command then reads it as the issue's position. Filing writes that state because it is the state it files the issue into. A later run cannot tell which route left an issue without its card, so it cannot know the issue was never worked on.
- **Give the card, and read the Status from the issue's labels and milestone,** as the sync does where the Status is the state's projection. Rejected, for the same reason: where the board holds the state, the labels carry no state, so the read gives only what the milestone gives, the guess above.
- **A command of its own for missing cards, apart from the sync.** Not chosen. It would read the same cards and issues the sync reads, so two commands would each decide which issue has a card, and each would need to meet ADR-096's tests.
- **Have the membership check add the card.** Rejected. The check reports, and writes nothing. It reads one issue at a time, by hand or in the post-check workflow, whose own credential reaches no board (ADR-096), and the workflow already has its own remediation for a project that turns it on.

## Implications

- **The board sync,** where the board holds the state or the state degrades, reads the board and the open issues, and adds a card for each open issue that has none, writing no Status, with what point 3 says. Where no board is configured, it refuses, as point 1 says. Its tests hold:
  - in both cases, that each open issue with no card gets one, that no Status is written on any card, that a board with no Status field does not stop it, and that a dry run writes nothing;
  - that the plan says the added cards will have no Status, and, where the board holds the state, says what point 3 says of the position and the board's automation;
  - that where the Status is the state's projection, the sync writes the Status as point 2 says.
- **The messages that report a missing card** name the sync among the ways to add it: a move's refusal, a seat's warning, the membership check's finding and filing's report of a failed add. Where the board holds the state, they still say that the Status is set on the board.
- **The sync's reference,** its own help and the capability's README, says where it runs and what it writes in each case. It changes with the build, once this record is accepted.
- **The edit to DEC-062,** made once this record is accepted: point 5's last sentence reads "Elsewhere that command gives each open issue its card, and the project's people set each card's Status on the board", with the refinement pointer *(refinement per [project-management:DEC-072-sync-gives-missing-cards])* on it. The rest of DEC-062 stays as it stood.
- **No other record is edited.** DEC-019, DEC-051 point 6 and ADR-096 stand, and this record follows them.
- **A surface change** for the capability, once built. A call that refused before now writes, after the person's consent, where the board holds the state or the state degrades. The build's changeset declares it. It changes no state a project holds and no option's signature, so it owes no migration.
- **Acceptance:** this record refines the accepted DEC-062, so accepting it needs the maintainer's sign-off.
