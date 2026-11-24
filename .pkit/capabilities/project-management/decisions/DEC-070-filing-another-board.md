---
id: DEC-070
title: Where the board holds the state, filing refuses a board other than the configured one
status: accepted
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> **Partially superseded by [project-management:DEC-071-filing-only-configured-board].** Filing refuses a board other than the configured one in every project with a board, and checks a board option naming a number below 1 first, refusing it with a message of its own. Overturned: that the override stands where the state is carried off the board or degrades, wherever DEC-070 says so or tests it, with the conclusion its Rationale's "Why only where the board holds the state" and its rejected alternative "Refuse wherever the map binds any axis to the board" draw for those projects; and the message its "What it says" gives a number below 1. The premises of that Rationale and that alternative stand, as does DEC-070's refusal where the board holds the state, with what counts as another board, when it comes, its code, and its message for every other number.

**In plain terms:** where a project's substrate map puts the issue state on its board, every command reads where an open issue stands from its card on the configured board, and from no other board. A filing that names another board would give the issue its only card on a board no command reads, so no command could place the issue. The filing command therefore refuses such a filing, before it writes anything or asks anything, and says how to file the issue instead. In every other project, this record leaves DEC-019's override as it is, so a filing there may name another board.

## Context

**The terms.**

- *The configured board* is the one board the project's configuration names, on which every issue belongs from its filing ([project-management:DEC-019-mandatory-issue-state]).
- *The board holds the state* where the substrate map binds the state to the board, so that the board's Status is the source of an open issue's position ([project-management:DEC-062-axes-chosen-in-the-map] point 5).
- *A filing that names another board* is one whose board option names a board number other than the configured board's.

**What the records say.**

- **DEC-019 lets one filing name another board** in place of the configured one ("Multi-board adopters at v1"). Such a filing adds the issue to the named board instead, so the issue has no card on the configured board.
- **Where the board holds the state, every command reads an open issue's position from its card on the configured board.** An issue with no card there has a position that is undetermined: reported apart, and never guessed from labels or a milestone ([project-management:DEC-051-axis-carriage-activation] point 6).

**The gap between them.** Where the board holds the state, an issue filed onto another board has no card on the board every command reads its position from, so its position is undetermined (DEC-051 point 6). A seat choosing work skips it, as that point has it. A command that moves it refuses, since no command acts on a position it could not read ([pkit:ADR-074] point 5). DEC-019 calls its missing card drift, which it warns of on an existing issue for a person to fix, and the post-check workflow it offers, as the capability ships it, does not add the card, even where a project installs the workflow and turns on its remediation, since the shipped remediation runs only on a finding that blocks, and drift never blocks. That card gets no Status from DEC-019, and a card whose Status is unset leaves the position undetermined too (DEC-051 point 6). No command gives the issue a Status from its native state either, since the capability keeps a board's Status as the state's projection only where the state is carried off the board (DEC-062 point 5). So no command places the issue.

**Other routes to the same state.** An issue reaches it too when it is filed outside this capability's commands, or when filing's add to the board fails after the issue exists. Those are a bypass and a failure. The override is the one route by which this capability's own command, asked to, files such an issue on purpose. This record closes that route alone. Whether a command repairs the state, whichever route an issue took to it, is a question of its own, left to [project-kit#3241](https://github.com/aleskalfas/project-kit/issues/3241).

**Where the question came from.** The work on a board that did not answer ([project-kit#3176](https://github.com/aleskalfas/project-kit/issues/3176)) named it, and left it to this capability ([project-kit#3205](https://github.com/aleskalfas/project-kit/issues/3205)).

## Decision

**Where the substrate map binds the state to the board, the filing command refuses a filing that names a board other than the configured one, before it writes anything or asks the person anything. There, every command reads an open issue's position from its card on the configured board alone, as DEC-051 point 6 has it, so an issue filed onto another board would have a position no command reads. Elsewhere this record leaves the override as DEC-019 has it.**

- **Where.** In a project whose substrate map binds the state to the board, whatever it binds the other axes to. Where the state is carried off the board, or degrades, the refusal does not apply.
- **What counts as another board.** A board number other than the configured board's, each read as a number. A filing that names the configured board's own number names no other board, and goes on. Where the configuration gives no board number to compare with, every board a filing names counts as another. One that declares no board gives none, and DEC-051 point 2 refuses `board: true` under it.
- **When.** Before the issue is created, before anything else is written, and before the person is asked anything. The refusal needs only the configuration, the map and the filing's options, so it comes before any read of a board, and a dry run meets it as a filing does.
- **What it says.** That the board holds the state, and that every command reads an open issue's position from the configured board, so an issue filed onto the named board would have a position no command reads. It names two ways out. One is to file the issue onto the configured board, by leaving the board option out. The other, where the project wants the issue on the other board too, is to add a card there after filing, by the host's own means, which the message names. That card carries no position (DEC-051 point 6). Where the configuration gives no board number, there is no configured board to file onto, so the message names that fault in place of the ways out.
- **Its code.** The code the filing command gives a filing it refuses for its options, never one that reads as the issue filed. A command's exit codes are its contract ([project-management:DEC-020-methodology-as-executable-commands]).

### What this overturns, and what stands

- **Overturned in DEC-019,** for a project whose map binds the state to the board: the per-invocation override in "Multi-board adopters at v1", "per-invocation override at filing time via `create-issue.py --board=<N>`". The refusal replaces it there.
- **Stands in DEC-019:**
  - the override, in every other project
  - every issue's card on the configured board from filing, and the severities of an issue without one
  - the single default board, with several boards for one project deferred
- **Stands elsewhere:** DEC-051 point 6 and DEC-062 point 5, which the Decision follows.

## Rationale

**Why refuse.** Where the board holds the state, the configured board is where every command reads where open work stands. An issue filed onto another board starts with no position any command can read: a move refuses it, a seat skips it, and no command gives it a Status on the configured board, since the capability keeps a board's Status as the state's projection only where the state is carried off the board (DEC-062 point 5). It is also the issue DEC-019 rejects at every filing that does not use the override: one with no card on the configured board. That outcome, an issue on the named board and not on the configured one, is all the refusal takes away. The rest the filing can still get: the issue goes onto the configured board when the option is left out, and a card added to the other board afterwards puts the issue there too, without touching its position. A refusal is also the narrowest answer. Should a project need such filings where the board holds the state, a later record can widen it, as DEC-019 defers several boards for one project until one is asked for.

**Why the refusal comes before anything is written or asked.** All it needs is in the configuration, the map and the filing's options. Refused there, the filing leaves nothing to undo, asks the person nothing it then refuses, and turns on no answer from a board.

**Why only where the board holds the state.** The refusal rests on the position. Where the state is on the board, an issue with no card on the configured board has no position, and no command guesses one (DEC-051 point 6). Where the map binds only priority or workstream to the board, such an issue has no value for them on the configured board until it has a card there. Yet its position is read off the board, so the issue stays workable. Whether a value of priority or workstream must be present, and where that is demanded, the board read-path contract leaves open ([pkit:ADR-053], "Boundaries"). An issue with no card on the configured board lacks those values in the same way as one whose card leaves them unset. Refusing it would settle that open question for this one route alone.

### Alternatives considered

- **Add the issue to the configured board as well as the named one.** Rejected, for three reasons:
  - the board option would mean "in place of" in one project and "as well as" in another, by the map alone;
  - the second card would carry a Status no command keeps after filing, since each move writes only the configured board's, so it would show a position the issue left at its first move;
  - filing would owe two adds, each a write that can fail after the issue exists.

  Adding a card to the other board after filing gives the same second card, without the option changing meaning.
- **Make the option add a second card in every project, writing no Status on it.** The first two reasons above do not reach it: the option would mean "as well as" in every project, and the second card would carry no Status to go stale. Not chosen here: it changes what the option means for every caller in every project, where the refusal changes it only where the override leaves an issue no command can place. Whether the option should come to mean this is part of the question of its place in other projects, below. A record that chooses it decides too whether this refusal gives way to it, since under it the issue keeps its card on the configured board, and the refusal's ground is gone.
- **Allow it, and state the consequence.** The filing goes on, and its output says that the issue has no position until it has a card and a Status on the configured board. Rejected: it files, knowingly, an issue that every command then refuses or skips, whose repair is by hand on the board. A warning read once at filing leaves the issue unworkable.
- **File onto the configured board, ignoring the option, and warn.** Rejected: the filing would do other than it was asked, with a warning read once as the only sign. A refusal says the same, and does nothing the caller did not ask for.
- **Read the position from whichever board holds the issue's card.** Rejected: it would overturn DEC-051 point 6 for a route this record can close instead. An issue's position would turn on which boards it happens to be on, a second place that says where the state lives, and every command would have to read each board an issue could be on, which no configuration lists.
- **Refuse wherever the map binds any axis to the board.** Rejected, as "Why only where the board holds the state" says.
- **Remove the override in every project.** Not decided here, for three reasons. Where the state is off the board, an issue filed onto another board keeps a position every command reads, so the override leaves no issue unworkable there. Removing the override, or changing what it does, would change every call that uses it. And that change wants evidence of the option's use, which this record has not gathered: when this record was written, none of this capability's own commands, skills, agents or tests passed the option, so what is missing is how the projects that adopt the capability use it. The question, with what the override costs there, is weighed in [project-kit#3241](https://github.com/aleskalfas/project-kit/issues/3241). This record decides only the projects where the override leaves an issue no command can place.

## Implications

- **The filing command** refuses, where the map binds the state to the board, a board option naming a number other than the configured board's, with the message and the code the Decision gives. It refuses before it writes anything or asks the person anything, in a dry run too. That includes the confirmation it asks for before it changes a repository other than the session's (COR-039), so it reads the map before that question. Its tests hold:
  - the refusal, and that nothing is written and nothing asked before it, that confirmation included;
  - that an option naming the configured board's number goes on, the two compared as numbers, so a number the configuration writes as a string matches the same number given to the option;
  - that where the state is off the board, or degrades, the option is not refused. They hold nothing more of what the override then does, which this record does not decide.
- **The reference for the board option,** the option's own help and the procedure the capability gives an agent for filing an issue, says that where the board holds the state the option is refused unless it names the configured board. It changes with the build, once this record is accepted.
- **The edit to DEC-019,** made once this record is accepted: its top line reads *Partially superseded by [project-management:DEC-070-filing-another-board]*, and says in the line itself: "Where the substrate map binds the state to the board, filing refuses a board other than the configured one. Overturned there: the per-invocation override at filing in 'Multi-board adopters at v1'. It stands for every other project." The rest of DEC-019 stays as it stood.
- **No other record is edited.** DEC-051 point 6 and DEC-062 point 5 already read the position from the configured board, and the Decision follows them.
- **A surface change** for the capability, once built. A call that succeeded before is refused in a project whose map binds the state to the board, so the change breaks such a project's use of the option. The build's changeset declares it, and weighs its segment as such a break. It changes no state a project holds and no option's signature, so it owes no migration.
- **Acceptance:** this record partially supersedes the accepted DEC-019, so accepting it needs the maintainer's sign-off.
