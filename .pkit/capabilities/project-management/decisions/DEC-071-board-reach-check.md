---
id: DEC-071
title: A run uses the project's board only once the board answers
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a project that keeps its issues' classification on a board reads and writes that board in many of its commands. Under some credentials, the hosting service may answer for a board the credential does not reach with nothing, rather than an error. A command that read such a board would find no state, and might act on an issue from a state it cannot see.

So under every credential, a run that reads or writes the project's board first confirms that the service answers with the configured board. It does so once in the run, and refuses before changing anything where the service does not.

What a person accepting this weighs:

- **One read more in each run that uses the board,** in every project with a board, under every credential. A project with no board is untouched.
- **A board out of reach is refused,** with its cause, where today a command may go on with what it read.
- **The check waits on where it sits.** It runs in the one path that every read and write of the board goes through. No such path exists yet, and choosing one is an architecture record's, which comes before the check is built.

## Context

**What the records already say.**

- **The board holds the classification.** In a project that keeps it on a board, an issue's classification lives on its item on the board, and an issue off the board has none ([project-management:DEC-019-mandatory-issue-state], Context). The commands read the board to find where an issue stands, and write it to move an issue, to set a field and to add a new issue.
- **What is checked today.** DEC-019's environment pre-check confirms that the configured board resolves, when a person or a schedule runs it, under the credential it runs with. DEC-019 rules out scanning every issue's board state in each command, as too costly ("Auto-add to board").

**What was measured** on a trial in which an agent reached GitHub under a GitHub App installation's token ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164), [project-kit#3004](https://github.com/aleskalfas/project-kit/issues/3004)): asked for a user's boards, the person's own token, of a kind the measurement did not record, found three, one of them public. The App's token, under an App granted no project permission, found none, and gave no error.

**What was not measured:**

- how a read of the configured board answers where the credential does not reach it, with an error or with nothing;
- whether an organisation's board answers to an App granted access to it ([project-kit#3172](https://github.com/aleskalfas/project-kit/issues/3172));
- which boards a fine-grained token, or a person's sign-in through another app, reaches.

This record rests on none of them.

## Decision

**Under every credential, a run that uses the project's board first confirms, once, that the service answers with the configured board, and refuses before changing anything where it does not.**

### 1. Only the service's positive answer counts

Before a run first reads or writes the configured board, it asks the service for that board under the run's credential. Only an answer that gives the configured board counts. Where the service refuses, fails, or answers without the board, the command refuses before changing anything. Its message names the board and the cause the service gave, and says that the board may be out of the credential's reach.

### 2. The check reads the board, under every credential

The check asks about the board, and never which kind of account the credential acts as. It runs the same under a person's credential, an app's, and one the commands cannot resolve.

### 3. Once in a run, in the one path to the board

- **Once.** The check runs once in a run, and the run keeps its answer.
- **In one path.** It runs in the one path that every read and write of the board goes through, never in each command. So no command can skip it, and a run that calls several of them reads the board once.
- **No scan.** It reads the board itself, never an issue's place on it. So it is no scan of every issue's board state, which DEC-019 rules out.

## Rationale

**Why only a positive answer.** A board out of reach may answer empty rather than fail, as the listing of a user's boards did under an app's credential. Whether a read of the configured board does too is unmeasured. A check that counts only a positive answer holds however a read out of reach answers.

**Why under every credential.** [pkit:ADR-091] point 4 asks first for a change that is right on every machine, before anything keyed to a property of the session. A board out of reach could answer empty under other credentials than an app's too, such as a fine-grained token, or a sign-in limited by the app it passed through. Keyed to the board, the check covers them all, and needs no reading of which credential it runs under. It also lets a board that an app does reach work at once, such as an organisation's if #3172 shows it, with nothing waiting on another record.

**Why once in a run, in one path.** A check in each command would sit in as many places as there are commands that touch the board, each a place for it to be missed. One path that every read and write goes through holds it in one place, as one reader holds the labels ([pkit:ADR-026]).

**Why not leave it to the pre-check.** The pre-check runs when someone runs it, under that person's credential. A session under another credential, such as an agent's, may reach a different set of boards. Only the run knows its own credential.

**The cost** is one read of the board in each run that uses it.

### Alternatives considered

- **Refuse a project with a board under an app's credential,** until an organisation's board is measured. The case: no new read under any credential, and nothing rests on how a board out of reach answers. Rejected: too broad, since it refuses a board an app does reach, and too narrow, since it misses any other credential that does not reach the board. It also needs the credential's kind, which this check never reads.
- **Check in each command that touches the board.** The case: it needs no shared path, so it can be built at once. Rejected: as many places as commands, each a place to miss it, and a run that calls several commands reads the board several times.
- **Trust what a read of the board answers.** The case: no new read. Rejected: an empty answer cannot be told from a board out of reach, and a command acting on it could move an issue from a state it cannot see.
- **Leave it to the environment pre-check.** The case: it already confirms that the board resolves. Rejected: it runs under whoever runs it, not under each run's credential.

## Implications

- **Edit once accepted.** Once a person accepts this record, DEC-019 is refined in place in this change, with the pointer `(refinement per [project-management:DEC-071-board-reach-check])`:
  - **"Auto-add to board: three enforcement layers":** under every credential, a run that reads or writes the configured board first confirms, once, that the service answers with the board, in the one path every read and write of the board goes through. Where the service does not, the command refuses before changing anything. The check reads the board, never an issue's place on it, so the rule against scanning every issue's board state in each command stands.
- **First, the path to the board.** Building the check waits on an architecture record that names the one path every read and write of the board goes through. [pkit:ADR-031]'s single construction point covers writes to a board's fields, and leaves adding an issue to a board out (its point 3). Reads of the board go through no one part. That record is the architect's. Whether it is drafted now is a person's to decide.
- **The work** is planned once this record and that one are accepted. It builds the check, its message and the tests that hold it. It declares a `minor` change for project-management: it adds a read and a refusal in every project with a board, and changes no installed file, name or schema, so it needs no migration. Whether it weighs as `major` is a person's judgment, made when the work's changeset is written.
- **This change** lands the record with a `none` changeset for project-management, since no behaviour changes until it is built. It needs no migration.
