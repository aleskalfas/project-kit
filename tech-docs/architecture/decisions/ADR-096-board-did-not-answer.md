---
id: ADR-096
title: A board that did not answer is never taken for one that answered empty
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** some reads of a Projects v2 board list only what the
credential may see, and leave out the rest without an error. Asked for a
person's boards, an App installation's token got none back, a public one
included, and no error, where the person's own token saw three
([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)). An
empty answer can then mean "there is nothing" or "you may not see it". A command
that takes one for the other reports an issue off the board, or passes a check,
on a board it never read.

This record says what counts as the board's answer, under every credential:

- **An empty answer counts only once the board has answered.** A read that lists
  only what the credential may see, such as an issue's own cards, answers empty
  only where the board itself answered the same credential in the same run.
  Otherwise the board did not answer. A stored board id is no answer.
- **An answer cut short, or holding a withheld card, is not whole.** A card
  whose issue the credential may not read comes back withheld. A command that
  acts on every card refuses, and one that acts on its own repository's issues
  sets the card aside.
- **No read says the board can be written.** Only a write's own answer says the
  write was made.

What a command does then follows what the board is to it. Where the board holds
a value the command reads or sets, a board that did not answer is a broken tool,
and the command refuses, before it acts wherever it can. Where the board only
mirrors what another substrate carries, the command reports the write it could
not make and goes on, as today. A check reports a board that did not answer as
that, never as an issue off the board and never as a pass. A project with no
board makes no call to one.

This completes the board read-path contract
([ADR-053](ADR-053-board-read-path-contract.md)) and widens it to the membership
check and to adding an issue to the board. It overturns nothing there, or in the
record on a board-carried state ([ADR-074](ADR-074-board-carried-state-read.md)).

**What a person accepting this weighs:**

- **Filing reads the board first** where the map binds an axis to the board, and
  refuses where the board did not answer. Where only priority or workstream
  lives on the board, that is one call more on each filing.
- **The membership check makes a read of its own,** in a project with a board,
  where it read the list of cards the issue's own read carried.
- **Projects whose credential the board does not answer see new reports and
  refusals:** the membership check reports the board unanswered where it
  reported issues off the board, the health check fails where it passed on a
  stored id, and a change to a field's options refuses where a card is withheld.
- **One premise is unmeasured:** that an issue's own cards list its card on every
  board the credential reaches (Context, and Implications).

## Context

**The terms.**

- **A read of the board itself** is addressed by the board's number or its node:
  its identity, its fields, its cards.
- **A filtered read** lists only what the credential may see, and leaves the
  rest out without saying so: the boards an owner holds, or an issue's own cards.
- **The board answered** where a read of the board itself names the board. A
  filtered read's answer is the board's where such a read answered the same
  credential in the same run. **It answered empty** where it answered and holds
  nothing of what was asked, such as no card for an issue.
- **The board did not answer** where a read fails, returns no board, is not
  whole, or comes back empty from a filtered read with no answer from the board
  itself.
- **A withheld card** is a card on a board the credential reads, whose issue
  lies in a repository the credential may not read. The board returns it marked
  as withheld, with nothing of its issue.
- **A run** is one invocation of a command.

**What was measured**
([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)). An
App installation's token, asked for the boards of a person's account, answered
with none, a public one included, and no error. The person's own token saw
three.

**What was not measured.**

- **What such a token gets from a read of one board by its number:** an error,
  or an answer naming no board. Either is a board that did not answer (point 1),
  so nothing here rests on which.
- **Whether an organisation's board answers such a token**
  ([project-kit#3172](https://github.com/aleskalfas/project-kit/issues/3172)).
  Either answer falls under point 1.
- **Whether an issue's own cards list its card on every board the credential
  reaches.** Point 1 rests on this: where the board itself answered, an issue's
  own cards are taken to list its card there.
- **Whether the service tells an App's token if it may change a board, and
  whether that answer reflects a token's scopes.** Point 3 rests on neither.

**What happens today.** The read path keeps the two answers apart in some places
and not in others:

- **A board-carried state** is read through the board read seam. The Status
  read keys an issue's cards on the board's node, which the seam read live in the
  same run (ADR-074 points 2 and 6). But the seam's identity read reports success
  where the service answers with no board.
- **The membership check** reads the list of cards the issue's own read carries.
  The list names no board, and an empty one reads as "not on the configured
  board". The capability's post-check workflow runs this check under the
  workflow's own token.
- **Reads of the board's identity outside the seam** run at setup, on filing
  beside a stored board id, and in the health check, which passes on a stored id
  without asking the board.
- **Filing** adds the issue's card after it creates the issue. Where the add
  fails, it warns and goes on, whether or not the board carries a value of the
  issue.
- **The lookup of one issue's card** for a write reads one page of the issue's
  cards, and reports no card where the card lies past it.
- **A walk of the board's cards** takes a withheld card for a card that holds no
  issue. A command that removes a field's option counts the cards that hold it
  from that walk.

**What the records already say.**

- **The board read-path contract** gives every read of the board to the seam,
  which reports whether the board answered and what it said. A gate raises where
  carriage said `board` and the read did not succeed (ADR-053 points 1, 2 and
  5). Its Boundaries keep the membership check off the contract: membership
  stays with the board flag, and one that cannot be determined is reported at the
  drift severity of the record on mandatory issue state, over a payload the
  check already fetched.
- **The record on a board-carried state** keys an issue's cards on the board's
  node, gives one account of which card is an issue's, and reads a listing whole
  or not at all (ADR-074 point 6). Each command decides what an outcome means,
  within two limits: it never guesses, and it keeps a broken board apart from a
  finding (ADR-074 point 5).
- **The substrate write-path contract** names adding an issue to a board out of
  the one constructor for field values and milestones
  ([ADR-031](ADR-031-substrate-write-path-contract.md) point 3). It says nothing
  of what counts as an add made.
- **Every issue of a project with a board belongs on it,** and a missing card on
  an existing issue is drift at warning severity
  ([project-management:DEC-019](../../../.pkit/capabilities/project-management/decisions/DEC-019-mandatory-issue-state.md)).
- **A hook's write after the command's own act** reports and goes on
  ([project-management:DEC-024](../../../.pkit/capabilities/project-management/decisions/DEC-024-lifecycle-hooks.md)).

The architecturally significant pins, each against a plausible alternative:

1. **What tells a board that did not answer from one that answered empty:** the
   empty answer itself, the credential's kind, the credential's grants, or the
   board's own answer.
2. **Where that sign is read:** in each run, under its credential, or from a
   stored id or an earlier answer.
3. **Whether an answer cut short, or holding a withheld card, counts.**
4. **What tells a board that can be written:** a read, or only a write.
5. **What a command does then:** one posture for every command, or one set by
   what the board is to the command.
6. **Whether the membership check comes under the contract.**

## Decision

**A read of the board answers empty only where the board itself answered the
same credential in the same run, and only where the answer is whole. No read
says the board can be written. Where the board holds a value a command reads or
sets, a board that did not answer is a broken tool and the command refuses;
where the board only mirrors, the command reports and goes on; a check reports
it as that.**

### 1. An empty answer counts only once the board has answered

- **A read of the board itself** answered where its answer names the board. An
  error, an answer with no board in it, or one with no node, is a board that did
  not answer.
- **A filtered read** answers empty, or answers that the configured board is not
  among what it lists, only where a read of the board itself answered the same
  credential in the same run. Otherwise the board did not answer.
- **The sign is the board's own answer, in the run, under the credential.** A
  stored board id names a board. It was written under some credential at some
  time, and says nothing of this one now. Another credential's answer, or an
  earlier run's, is no sign either. A write's answer that names the board's
  card, such as the card an add returns, is a sign.
- **No sign is read from the credential's kind,** an app's, a workflow's or a
  person's, nor from the host or the tool that issued it. Every credential gets
  the board's own answer alike.
- **A project with no board** is untouched. Every read and write here, the
  membership check's and the add among them, stops before the network where no
  board is configured (ADR-053 point 3).

### 2. A read that is not whole answers nothing

- **Cut short.** A read that stops short of its end, at a page bound, a batch
  that failed or pages it did not read, is a board that did not answer. It is
  never an answer that lacks what it did not read. This holds ADR-074 point 6's
  whole-or-nothing for every read of the board, the lookup of one issue's card
  among them.
- **A withheld card.** A walk of the board's cards that returns a withheld card
  did not read that card's issue. What that means depends on what the command
  acts on:
  - **A command that acts on the board as a whole,** such as one that changes or
    removes the options of a field every card's value rests on, refuses. A card
    it could not read may hold the option, and the change would alter that
    card's value unread.
  - **A command that acts only on its own repository's issues** sets a withheld
    card aside. The credential reads that repository, so no card withheld from
    it holds one of its issues.

### 3. A write is made only where the board answers that it was

- **An add counts as made** only where the board answers with the issue's card,
  and a field write only where the board accepts it. Anything else is a write
  not made, whatever the tool's exit status.
- **No read says the board can be written.** A credential may read a board it
  may not change, by a read-only grant or a token's scope. Where the board's own
  answer says the credential may not change it, a command that would write a
  value the board holds refuses before it acts (point 4). An answer that it may
  promises nothing, and the write's own answer decides.
- **The add keeps its own place,** outside the constructor for field values
  (ADR-031 point 3), and that constructor's neutrality: it reports what the
  board answered, and decides nothing.

### 4. What a command does follows what the board is to it

ADR-074 point 5's two limits hold for every command that reads or writes the
board: it never acts on a value it could not read, and it keeps a board that did
not answer apart from a finding about an issue. Within those limits, what the
board is to the command decides:

- **The board holds a value the command reads or sets:** a value the substrate
  map binds to the board, read to decide or written as the act, or the card such
  a value lives on. A board that did not answer, or a write not made, is a
  broken tool.
  - **Refuse first.** The command refuses before it acts wherever a read can
    tell it first, and where its exit codes tell a broken tool from a refusal,
    it takes the broken tool's code. A command that would set such a value, or
    add the card it lives on, reads the board before it acts: the board's own
    answer, and where the service gives one, whether the credential may change
    it. Filing in a project whose map binds an axis to the board is one: it
    reads the board before it creates the issue.
  - **An act already made stands.** Where a write fails after the act, the
    command leaves the act standing, since undoing it is a write too, and a
    destructive one. It says what stands, and reports the write not made with
    the board's words and the remedy. It takes no exit code that reads as a
    clean success, and none that reads as the act not made.
- **The board only mirrors what another substrate carries, or holds a card with
  no value on it:** the Status where labels and milestones carry the state, or
  the card in a project whose map binds no axis to the board. The act stands,
  and the write not made is one line saying what stands and what repairs it, as
  today.
- **A check reports on issues or on the setup,** such as whether an issue is on
  the board, or whether the board resolves. A board that did not answer is
  reported as that, at the check's own severity. It is never drift found on the
  issue, and never a check passed.

### 5. Membership is read as every card is

- **One account of an issue's card.** An issue is on the board where it has a
  card on the configured board, found among the issue's own cards, an archived
  card included. That is ADR-074 point 6's account, held for membership too. So
  the membership check reads through the seam, under point 1, and not from the
  list of cards the issue's own read carries. That list names no board, so it
  cannot tell the configured board from another, and its empty answer cannot
  tell nothing from nothing visible.
- **Three outcomes.** A card on the configured board satisfies the check. A
  board that answered and holds no card for the issue is the drift DEC-019
  names, at its severity. A board that did not answer is reported as that, at
  the same severity, and never as an issue off the board.
- **The flag's, not carriage's.** Membership applies where a board is
  configured, and never routes through carriage (ADR-053, Boundaries). A project
  with no board makes no call for it.

### 6. Every read of the board goes through the seam, and a scan holds it

- **The seam owns every read of the board** (ADR-053 point 1). A read made
  outside it decides for itself what counts as the board's answer, and the reads
  made outside it are where a stored id stands in for one. So each goes through
  the seam.
- **A filtered read takes the board's own answer as its input,** from the same
  run, never a bare id. So no caller can key one on a stored id, and point 1
  holds by construction rather than by each caller remembering it.
- **The seam says which it is:** the board answered, with what it said and
  whether that is whole, or the board did not answer, with the service's words
  verbatim.
- **A stored board id is written only from the board's own answer,** and read
  only as a name.
- **A scan of the scripts holds that no script outside the seam builds a read of
  the board,** the cards in an issue's own read among them. It is the guard the
  write constructor has (ADR-031 point 4), on the read side.

### Boundaries: what this record is not

- **Not which credential an agent holds,** or which account the commands act as.
  Those are the project-management capability's to decide. This record holds
  under every credential alike.
- **Not the missing-value question** for priority and workstream, which ADR-053
  point 2 leaves open. A board that answered *unset* there is that question.
- **Not a hook's posture.** A hook's write after the command's own act keeps
  DEC-024's report-and-continue. It is never the command's act.
- **Not the severities of mandatory issue state.** The membership check keeps
  DEC-019's.
- **Not back-fill's drift-skip** (ADR-053 point 4). A card back-fill cannot read
  is one it skips, as is any read it cannot make.
- **Not one home for the add.** ADR-031 point 3 keeps the add out of the
  constructor for field values. Point 3 here binds every place an add is made.

## Rationale

**Why the board's own answer.** The service leaves out of a filtered read what
the credential may not see, and says nothing. So its empty answer is the same for
"nothing there" and "nothing you may see", and no reading of that answer alone
tells them apart. A read of the board itself names the board only to a
credential that reaches it. Once that has answered, the same credential's
filtered read sees the board, and its empty answer means empty.

**Why in the run, under the credential.** Reach is a fact of the credential at
the time. A token is revoked, an app's grant changes, a board is shared or
unshared, without notice. A stored id was written under whatever credential set
the project up, and the credentials this record is for are the ones that differ
from it. Taking the stored id as the sign spares a call by giving the sign that
fails under them. The board's own read is a call most board commands make
already, and one more where they do not.

**Why not the credential's kind.** A board leaves out what any credential may not
see: an app's token, a workflow's, a person's token without the project scope, or
a person's token on a board not shared with them. A rule keyed to the kind would
miss the next credential with the same property, as
[ADR-091](ADR-091-no-host-component.md) point 2 says of a host's name, and
reading the kind is a read that can fail too.

**Why a read not whole answers nothing.** A read cut short lacks what it did not
read, and taking it for the whole turns a tooling fault into a finding about
issues: the mis-attribution ADR-053 point 2 exists to prevent. ADR-074 point 6
rules so for a listing. A single issue's card lookup is the same read with one
id.

**Why a withheld card splits by what the command acts on.** A command that
changes a field's options changes the value of every card that holds one,
whether it read the card or not. Removing an option no card it read holds would
clear the value of a card it could not read: the overwrite of a value never read
that ADR-053 point 4 calls a defect where back-fill's emitted script does it
([#816](https://github.com/aleskalfas/project-kit/issues/816)). A command acting
on its own repository's issues loses nothing by setting a withheld card aside,
since such a card holds none of them.

**Why only a write's answer says it was made.** Read access and write access part
on a read-only grant and on a token's scope, so a board that answers a read may
refuse the write. The board's answer about the credential's permission can say
no in advance, and a command that holds the value there should hear it before it
acts. It may not reflect everything that refuses a write, so it never stands for
the write's own answer.

**Why the posture follows what the board is to the command.** The same failure
costs commands different things, which is why ADR-053 leaves the posture to the
caller. Where the board holds a value a command reads, acting on an unread value
is a guess, which the record on axis carriage refuses
([project-management:DEC-051](../../../.pkit/capabilities/project-management/decisions/DEC-051-axis-carriage-activation.md)
point 6), and where it holds a value a command sets, a write
not made leaves that value where no command can read it. Where the board only
mirrors, the value lives elsewhere, the act is whole without the mirror, and a
repair writes the mirror later. A check has no act: its whole output is a
report, so the one thing it must not do is report something it did not see.

**Why read before acting.** A filing that creates an issue and then finds the
board does not answer leaves an issue whose board-carried values no command can
set or read, and undoing it is a destructive write. Where the board carries the
state, filing reads the board's Status field after the add already, so reading it
first costs nothing. Where only priority or workstream lives there, it costs one
call.

**Why an act already made keeps a code apart.** A clean success hides that the
act's own result is missing. A code that reads as the act not made invites a
caller to make it again, filing a second issue.

**Why membership comes under the contract.** The membership check's one read is a
filtered read that names no board. Under a credential the board does not answer,
it reports every issue off the board, and where the post-check workflow runs
under such a credential, it posts that on every issue. Reading it as every card is gives one account of which card is an
issue's, for membership as for a state (ADR-074 point 6), at a call or two for a
project with a board and none without.

**Why a scan.** The seam's ownership of every read was stated and not enforced,
and reads grew outside it, each with its own sense of an answer, a stored id
standing in for one among them. A stated single home is provisional until a test
holds it, the lesson ADR-031 point 4 draws for writes.

### Alternatives considered

- **Take an empty answer as the board's, as the reads do today.** The case: no
  extra read. Rejected: under a credential the board leaves out, every issue
  reads as off the board and every listing as empty, the measured case.
- **Take every empty answer as a board that did not answer.** The case: no
  premise about the service. Rejected: an issue truly off the board could never
  be reported, so DEC-019's drift would never be found.
- **Read the sign from the credential's kind,** trusting an empty answer under a
  person's token and not under an app's or a workflow's. Rejected: a person's
  token can meet the same silence, and the kind is a read that can fail.
- **Ask the service for the credential's grants** before reading, such as its
  scopes or an installation's permissions. Rejected: each kind of credential
  reports its grants its own way or not at all, and no grant says whether a
  board was shared with the account. The board's own answer is one read every
  credential gets.
- **Trust a stored board id as the sign,** so the health check is no stricter
  than the commands it serves. Rejected: the id was written under another
  credential at another time, and under this record no command takes it as the
  sign either.
- **Decide membership from a walk of the board's cards.** Rejected for ADR-074
  point 6's reasons, a cost and a page bound set by the board's history and a
  second account of which card is an issue's, and a withheld card leaves the
  walk no more whole.
- **One posture for every command,** refusing wherever the board did not answer,
  or reporting and going on everywhere. Rejected: refusing everywhere stops
  filing on a board that only mirrors the labels, though nothing filing sets
  lives there. Going on everywhere files issues whose values live on a board no
  command can reach.
- **Undo the act when a board write fails after it,** such as by closing the
  issue just filed. Rejected: it is destructive, it is a second write that can
  fail as the first did, and reading the board first leaves little to undo.
- **Report a failed write as a mirror's is, where the board holds the value.**
  Rejected: the act's own result is missing, and a caller reading the exit
  status takes the act as done.
- **Keep the membership check off the contract,** as ADR-053's Boundaries had it.
  Rejected: its one read is the filtered read that answers empty.
- **Leave a withheld card out of the count, and go on.** Rejected: a command that
  removes an option no card it read holds clears the value of a card it could not
  read.
- **Trust the board's answer that the credential may change it.** Rejected: it
  may not reflect everything that refuses a write, so only the write's own answer
  says the write was made.

## Implications

- **ADR-053 is refined in place on this record's acceptance.** The architect
  rewrites each passage below to state what holds, with the pointer
  "(refinement per ADR-096)", and checks that the rest of the record agrees
  ([the decisions README, "Refining an accepted record"](../../../.pkit/decisions/README.md#refining-an-accepted-record)):
  - **the Summary's first paragraph** gains that a read which comes back empty
    counts as the board's answer only where the board itself answered the same
    credential in the run, and only whole;
  - **point 1, its Layer 2,** where the seam reports "whether the board answered
    and what it said", reports the board answered only as this record's point 1
    tells it, says whether the answer is whole, and gives the service's words
    verbatim where the board did not answer;
  - **point 2's first paragraph** says that a read which answered empty with no
    answer from the board itself in the run, or which is not whole, is a read
    that did not succeed;
  - **the Boundaries' membership bullet** says that membership stays with the
    flag and never routes through carriage, is read through the seam as every
    card is (this record's point 5), and, where the board did not answer, is
    reported as that at DEC-019's drift severity, the gate's raise and the
    check's report standing side by side. Its "over a payload the gate already
    fetched" and "resolved from incidental data" go.

  This refines ADR-053 and overturns no part of it. Its three layers, its raise,
  its scope by carriage, its silence for a project with no board, back-fill's
  skip and the neutral seam all stand. The Boundaries edit widens the contract to
  a read it left out, which changes what ADR-053 decides, so a person's
  acceptance of this record is the sign-off for that edit
  ([COR-064](../../../.pkit/decisions/core/COR-064-answer-delegate.md) point 6).
- **ADR-074, ADR-031, DEC-019 and DEC-024 stand unedited.** ADR-074's state reads
  key on the board's own answer in the run already, and point 2 here holds its
  point 6's whole-or-nothing for every read. ADR-031 point 3 keeps the add out
  of the constructor for field values, and point 3 here says what counts as an
  add made. DEC-019's severities and DEC-024's hooks are untouched.
- **Measured before the work builds:** whether an issue's own cards list its card
  on every board the credential reaches, under a person's token and an App
  installation's. Where it does not hold, a filtered read is not enough even
  after the board answered, and this record is revisited before work rests on
  point 1.
- **Tests hold each case:**
  - **a board that does not answer,** where the board's own read fails or names
    no board while a filtered read answers empty: the membership check reports
    the board unanswered, filing in a project whose map binds an axis to the
    board refuses before it creates the issue, a state read is unreadable, and
    the health check fails;
  - **a board that answers but cannot be written:** where the board answers
    that the credential may not change it, a command that would write a value it
    holds refuses before it acts; where a write fails after a read that
    answered, the act stands and the write is reported not made, with the broken
    tool's code where the board holds the value and one line where it only
    mirrors;
  - **a board with a withheld card:** a command that changes a field's options
    refuses, and one that acts on its own repository's issues sets the card
    aside;
  - **a project with no board,** where the membership check and filing make no
    call, as ADR-053 point 3's test asserts for every composing gate;
  - **the scan** of point 6.
- **The work** is a surface change for the project-management capability, and
  declares its changeset with it, its segment the person's judgment. It reaches
  projects whose credential the board does not answer, each change with a
  message that names the way out: filing refuses where the map binds an axis to
  the board, the membership check reports the board unanswered, the health check
  fails where it passed on a stored id, and a change to a field's options refuses
  where a card is withheld. It needs no migration: nothing is renamed or removed,
  and a stored board id stays where it is, read as a name.
- **This change** lands the record alone, and needs no changeset.
