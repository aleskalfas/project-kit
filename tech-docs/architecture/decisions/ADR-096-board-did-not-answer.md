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

- **An absence counts only where the same request shows the board answered.** A
  read that lists only what the credential may see, such as an issue's own
  cards, says a card is absent only where the same request read the board
  itself and found a card on it among some issue's own cards. Otherwise the
  board did not answer. A stored board id is no answer.
- **An answer cut short is no answer,** and a command that would clear or alter
  a value it did not read refuses.
- **Only a write's own answer says the write was made.**

What a command does then follows what each read and write is to it. A read it
acts on stops the act, as a broken tool. A read it only reports says the board
did not answer, never that an issue is off the board, and never that a check
passed. Once the act is made it stands, and a step it requires that failed gets
an exit code of its own. Filing reads the board first where the board holds the
issue's state. A project with no board makes no call to one.

This refines the board read-path contract
([ADR-053](ADR-053-board-read-path-contract.md)) and the record on a
board-carried state ([ADR-074](ADR-074-board-carried-state-read.md)) in place.
It overturns one ruling of ADR-053: that the membership check stays outside the
contract, and judges from what the issue's own read carried. It also decides
what counts as adding an issue to the board, which no other record decides.

**What a person accepting this weighs:**

- **ADR-053 is partly overturned.** The membership check makes one request of
  its own, in a project with a board, where it judged from the issue's own read.
- **Filing refuses before it creates an issue** where the map binds the state to
  the board and the board did not answer. Its read of the board moves earlier,
  and adds no call. Elsewhere filing reads nothing first.
- **A failed add at filing exits with a code saying the issue was filed and a
  later step failed,** in every project with a board, rather than clean.
- **New reports and refusals** reach projects whose credential the board does
  not answer. So does a board that returns the credential no card of an issue
  it reads, since nothing then shows the board answered. The membership check
  reports the board unanswered, the health check fails where it passed on a
  stored id, and removing a field's option refuses while a card holds a value
  the command could not read.

## Context

**The terms.**

- **The configured board** is the board the project's configuration names.
- **A read of the board itself** is addressed to the board, by its node where
  one is stored or by the owner and number the configuration gives. It reads the
  board's identity, its fields or its cards.
- **A filtered read** lists only what the credential may see, and leaves the
  rest out without saying so: the boards an owner holds, or an issue's own
  cards.
- **A request** is one call to the service. It carries one credential, to one
  host, at one moment.
- **A witness** is a card on the configured board, found among some issue's own
  cards in the same request as a read of the board itself (point 1).
- **A whole read** is one that read every page it asked for, and whose reply
  carries no error beside its data.
- **A withheld card** is a card on a board the credential reads, whose issue
  lies in a repository the credential may not read. The board returns it marked
  as withheld, with nothing of its issue.

**What was measured**
([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)). An
App installation's token, asked for the boards of a person's account, answered
with none, a public one included, and no error. The person's own token saw
three.

**What was not measured, and what rests on it.**

- **What such a token gets from a read of one board by its number:** an error,
  or an answer naming no board. Either is a board that did not answer (point 1).
- **Whether an organisation's board answers such a token**
  ([project-kit#3172](https://github.com/aleskalfas/project-kit/issues/3172)).
  Either answer falls under point 1. It decides only which projects meet the
  refusals.
- **Whether an issue's own cards list its card on every board the credential
  reaches.** Nothing rests on it: point 1 counts an absence only where the same
  request carries a witness. What point 1 takes from the service is the shape
  of its filter: that it parts what a credential sees by the board and by the
  issue. The witness tests the board, and the command's own read of the issue
  tests the issue.
- **Whether the board returns a withheld card's values, or lets such a card be
  written.** Point 2 keys on a value the command did not read, so either answer
  changes only how often it refuses.
- **Whether the service's answer that a credential may change a board reflects
  an App's token, or a token's scopes.** Point 3 takes that answer as advice.
- **Whether a workflow's own token reaches any board.** By the service's
  documentation it reaches none. Point 5 holds either way.

**The faults it answers.**

- **The membership check** reads the list of cards the issue's own read
  carries. The list names no board, so an empty one reads as "not on the
  configured board", and any card as on it. The capability's post-check
  workflow runs this check under the workflow's own token.
- **The seam's read of the board's identity** reports success where the service
  answers with no board. Reads of the identity outside the seam run at setup, at
  filing and in the environment health check (DEC-019's third layer), which
  passes on a stored id without asking the board.
- **The lookup of one issue's card** for a write reads one page of the issue's
  cards, and reports no card where the card lies past it.
- **A walk of the board's cards** takes a withheld card for a card with no
  issue, and a command that removes a field's option counts the cards holding it
  from that walk.
- **Filing** adds the issue's card after it creates the issue. Where the add
  fails, it warns and exits clean, whatever the board holds.

**What the records already say.**

- **The board read-path contract** gives every read of the board to the seam,
  which reports whether the board answered and what it said, and a gate raises
  where carriage said `board` and the read did not succeed (ADR-053 points 1, 2
  and 5). What an outcome means to another command is that command's own to
  decide. Its Boundaries keep the membership check off the contract: an
  undetermined membership "is reported as a finding at DEC-019's own drift
  severity, over a payload the gate already fetched", a question "resolved from
  incidental data", and "neither is the model for the other".
- **The record on a board-carried state** gives one account of which card is an
  issue's, and reads a listing whole or not at all (ADR-074 point 6). Each
  command decides what an outcome means, within two limits: it never guesses,
  and it keeps a broken board apart from a finding (ADR-074 point 5).
- **The substrate write-path contract** names adding an issue to a board out of
  the one constructor for field values
  ([ADR-031](ADR-031-substrate-write-path-contract.md) point 3), and says
  nothing of what counts as an add made.
- **Every issue of a project with a board belongs on it:** a missing card is a
  reject at filing, and drift at warning severity on an existing issue
  ([project-management:DEC-019](../../../.pkit/capabilities/project-management/decisions/DEC-019-mandatory-issue-state.md)).
- **A hook's failure leaves the exit clean,** so that one flaky hook does not
  make every filing fail from an agent's view. The first hook fires once the
  issue is filed and added to the board
  ([project-management:DEC-024](../../../.pkit/capabilities/project-management/decisions/DEC-024-lifecycle-hooks.md)).
- **A link that fails after an issue is filed** leaves the issue standing, and
  filing exits with a code of its own for it
  ([project-management:DEC-048](../../../.pkit/capabilities/project-management/decisions/DEC-048-from-report-auto-link.md)
  point 4).

The architecturally significant pins, each against a plausible alternative:

1. **What tells a board that did not answer from one that answered empty:** the
   empty answer itself, the credential's kind, its grants, a premise about the
   service, or a witness the same request carries.
2. **Where that sign is read:** in the same request, in the same run, or from a
   stored id or an earlier answer.
3. **Whether an answer cut short, or holding a card the command could not read,
   counts.**
4. **What tells a board that can be written:** a read, the service's answer on
   the credential's permission, or only the write.
5. **What a command does then:** one posture for every command, one chosen by
   each command, or one set by what each read and write is to it.
6. **Whether the membership check comes under the contract.**

## Decision

**An answer that a card is absent counts only where the same request shows the
board answered, and only where it is whole. Only a write's answer says it was
made. A read a command acts on stops the act as a broken tool. A read it only
reports says the board did not answer. Once the act is made it stands, with an
exit code that says so.**

### 1. An absence counts only where the same request shows the board answered

- **A read of the board itself** answered where its answer names the configured
  board. An error, an answer with no board or no node in it, or one naming
  another board, is a board that did not answer. Whether the configured board
  answers is read only so, never from an owner's list of boards.
- **A card found is an answer.** A card on the configured board, found among an
  issue's own cards, is the board's answer that the issue is on it.
- **An absence needs a witness.** A filtered read says a card is absent only
  where the same request read the board itself, the board answered, and the
  request carries a witness: some issue's own cards list a card on that board,
  such as the issue of a card the board's own read returned, or another issue
  the command reads. Otherwise the board did not answer.
- **The sign is in the request.** A stored board id names a board. It was
  written under some credential at some time, and says nothing of this one.
  Another request's answer, an earlier run's or another credential's is no sign.
- **No sign is read from the credential's kind,** an app's, a workflow's or a
  person's, nor from the host or the tool that issued it. Every credential meets
  the same test.
- **A project with no board** is untouched. Every read here stops before the
  network where no board is configured (ADR-053 point 3), and so does every
  write, the add among them.

### 2. A read that is not whole answers nothing

- **Cut short.** A read that stops short of its end, at a page bound, a batch
  that failed or pages it did not read, or whose reply carries an error beside
  its data, is a board that did not answer. It is never an answer that lacks
  what it did not read. This holds ADR-074 point 6's whole-or-nothing for every
  read of the board, the lookup of one issue's card among them.
- **A value the command did not read.** A walk of the board's cards that
  returns a withheld card did not read its issue, and read its values only where
  the board returned them.
  - **A command that would clear or alter a value of a card it did not read
    refuses,** such as one that removes an option, or merges it into another,
    while such a card remains. Adding an option, or renaming one in place,
    alters no card's value, and goes on.
  - **A command that acts only on its own repository's issues** sets a withheld
    card aside. The credential reads that repository, so no card withheld from
    it holds one of its issues.

### 3. A write is made only where the board answers that it was

- **An add counts as made** only where the board answers with the issue's card,
  and a field write only where the board accepts it with no error beside it.
  Anything else is a write not made, whatever the tool's exit status.
- **No read says the board can be written.** A credential may read a board it
  may not change, by a read-only grant or a token's scope. Where the service
  answers whether the credential may change the board, that answer is advice: a
  command reports it beside a write not made, and neither refuses on it nor
  trusts it.
- **The add keeps its own place,** outside the constructor for field values
  (ADR-031 point 3), with that constructor's neutrality: it reports what the
  board answered, and decides nothing. This point binds every place an add is
  made.

### 4. What a command does follows what each read and write is to it

ADR-074 point 5's two limits hold for every read and write of the board, not
only a state's: a command never acts on a value it could not read, and it keeps
a board that did not answer, or a write not made, apart from a finding about an
issue. Within them, each read and write takes the posture its use gives it, and
a command that makes several takes each:

- **A read the command acts on:** its answer decides the command's act, or a
  gate's verdict on a value the map binds to the board. A board that did not
  answer stops what rests on it. The command refuses, with the broken tool's
  code where its codes tell one, or, choosing among many, takes nothing (DEC-051
  point 6). This is ADR-053 point 2's raise.
- **Any other read is one the command reports:** a check of an issue or of the
  setup, a value a command shows, or a note after its act. A board that did not
  answer is reported as that, where the finding or the value would stand, and a
  check reports it at its own severity. It is never a finding about the issue,
  never an unset value and never a check passed.
- **A write that is the act,** such as setting a field, or adding a card where
  that is all the command does. Not made, it is the act not made, and the
  command says so with the board's words.
- **A write that follows the act, and that the act requires:** the card filing
  adds, since an issue belongs on the board from its filing (DEC-019), or a
  value the map binds to the board that the command writes itself, such as the
  first Status where the map binds the state to the board. Not made, the act
  stands, since undoing it is a write too, and a destructive one. The command
  says what stands, gives the write not made with the board's words and the
  remedy, and exits with a code saying the act was made and a later step
  failed, such as filing's code for an issue filed whose link failed (DEC-048
  point 4).
- **Any other write that follows the act mirrors** a value another substrate
  carries, such as the Status where labels carry the state. Not made, it is one
  line saying what stands and what repairs it, and the command exits as its act
  does.

Two rules order these around the act:

- **Before it.** Where a command's act would create an issue whose position the
  board holds, as filing does where the map binds the state to the board, the
  command reads the board first, and refuses before it acts where the board did
  not answer. Its refusal says the board did not answer the credential in use,
  gives the service's words, and names a credential the board answers as the
  way out.
- **After it.** Nothing takes a code that reads as the act not made, and a write
  the act requires that was not made takes no code that reads as a clean
  success.

These are limits on every command, as ADR-053 point 2's and ADR-074 point 5's
are. Within them, each command's choice stays its own, recorded with the
command's discipline, as a seat's is (DEC-051 point 6).

### 5. Membership is read as every card is

- **One account of an issue's card.** An issue is on the board where it has a
  card on the configured board, found among the issue's own cards, an archived
  card included. That is ADR-074 point 6's account, held for membership too. So
  the membership check reads through the seam, under point 1, and not from the
  list of cards the issue's own read carries. That list names no board, so it
  cannot tell the configured board from another, and its empty answer cannot
  tell nothing from nothing visible.
- **Three outcomes.** A card on the configured board satisfies the check. A
  board that answered with no card for the issue is the drift DEC-019 names, at
  the severity the check gives it. A board that did not answer is reported as
  that, at DEC-019's drift severity wherever the check runs, and never as an
  issue off the board. A fault of the check's credential is none of the issue's,
  so it never takes the reject DEC-019 gives an issue off the board at filing.
- **The flag's, not carriage's.** Membership applies where a board is
  configured, and never routes through carriage (ADR-053, Boundaries). A project
  with no board makes no call for it.

### 6. Every read of the board goes through the seam, and a scan holds it

- **The seam owns every read of the board** (ADR-053 point 1). A read made
  outside it decides for itself what counts as the board's answer, which is how
  a stored id comes to stand in for one. So each goes through the seam.
- **The seam builds a filtered read into one request with the board's own
  read,** so no caller can pair it with a stored id or an earlier answer, and
  point 1 holds by construction rather than by each caller remembering it.
- **The seam says which it is:** the board answered, with what it said and
  whether that is whole, or the board did not answer, with the service's words
  verbatim.
- **A stored board id is written only from the board's own answer,** and read
  only as a name: to address the board's own read, and to know the configured
  board's card among an issue's.
- **A scan of the scripts holds that no script outside the seam builds a read of
  the board,** the cards in an issue's own read among them. It is the guard the
  write constructor has (ADR-031 point 4), on the read side.

### What this overturns in ADR-053, and what stands

Overturned, in the Boundaries' bullet on the board-membership check:

- "Not the board-membership check": point 5 brings the check under the
  contract;
- that membership is judged "over a payload the gate already fetched", a
  question "resolved from incidental data": point 5 reads it through the seam;
- "neither is the model for the other": membership is read as every card is;
- that a membership that cannot be determined is reported "as a finding": it is
  reported as a board that did not answer.

Standing, in that bullet: membership stays with the flag and never routes
through carriage, one that cannot be determined is reported at DEC-019's drift
severity, and the gate's raise and the check's report both stand. The rest of
ADR-053 stands, refined as the Implications name.

### Boundaries: what this record is not

- **Not which credential an agent holds,** or which account the commands act as.
  Those are the project-management capability's to decide. This record holds
  under every credential alike.
- **Not the missing-value question** for priority and workstream, which ADR-053
  point 2 leaves open. A board that answered *unset* there is that question.
- **Not a hook's posture.** A hook's write after the command's act keeps
  DEC-024's report-and-continue, and its clean exit. It is never the command's
  act, nor a write the act requires.
- **Not the severities of mandatory issue state.** The membership check keeps
  DEC-019's for an issue off the board.
- **Not back-fill's drift-skip** (ADR-053 point 4). A card back-fill cannot read
  is one it skips, as is any read it cannot make.
- **Not what the forward cascade does at an ancestor** whose card the board did
  not answer for. That stays with the project-management record ADR-074's
  Boundaries leave it to, and the limits hold there: no ancestor moves on a
  position the cascade could not read.
- **Not one home for the add.** ADR-031 point 3 keeps the add out of the
  constructor for field values, and point 3 here binds every place an add is
  made.

## Rationale

**Why a witness in the same request.** The service leaves out of a filtered
read what the credential may not see, and says nothing. So its empty answer is
the same for "nothing there" and "nothing you may see", and no reading of that
answer alone tells them apart. A read of the board itself names the board only
to a credential that reaches it. It does not show that the same credential's
filtered reads see the board: that the two agree is a premise about the
service, unmeasured for the very credential that prompted this record. A card on
the board, found among an issue's own cards in the same request, shows it for
that credential, that board and that moment. The board's read and the witness
travel in the request the command makes anyway, so they cost no call.

**Why the request, and not the run.** Reach is a fact of the credential at the
time. A token is revoked, an app's grant changes, a board is shared or unshared,
without notice. A stored id was written under whatever credential set the
project up, and the credentials this record is for are the ones that differ from
it. Two reads in one request share one credential, one host and one moment by
construction. Two reads in one run need not, since one may take its host from
the repository's remote and another from the environment, and a test cannot see
that they parted.

**Why not the credential's kind.** A board leaves out what any credential may
not see: an app's token, a workflow's, a person's token without the project
scope, or a person's token on a board not shared with them. A rule keyed to the
kind would miss the next credential with the same property, as
[ADR-091](ADR-091-no-host-component.md) point 2 says of a host's name, and
reading the kind is a read that can fail too.

**Why a read not whole answers nothing.** A read cut short lacks what it did not
read, and taking it for the whole turns a tooling fault into a finding about
issues: the mis-attribution ADR-053 point 2 exists to prevent. ADR-074 point 6
rules so for a listing. A single issue's card lookup is the same read with one
id.

**Why a value not read decides the refusal.** Removing an option, or merging it
into another, changes the value of every card that holds it, read or not.
Removing one that no card it read holds would clear the value of a card it
could not read: the overwrite of a value never read that ADR-053 point 4 calls a
defect where back-fill's emitted script does it
([#816](https://github.com/aleskalfas/project-kit/issues/816)). Adding an option
or renaming one keeps every card's value, so it refuses nothing. A command
acting on its own repository's issues loses nothing by setting a withheld card
aside, since such a card holds none of them.

**Why only a write's answer says it was made.** Read and write access part on a
read-only grant and on a token's scope, so a board that answers a read may
refuse the write. The service's answer on whether a credential may change the
board is unmeasured for an app's token and for a token's scopes. A wrong "no"
would refuse with no way out, since no sign is read from the credential's kind,
while a write not made after the act is reported and can be repaired. So that
answer stays advice.

**Why each read and write, not each command, takes the posture.** The same
failure costs different uses different things, which is why ADR-053 leaves the
posture to the caller. Keyed by the command as a whole, the classes overlap,
since one command reads to decide, writes, and reports after its act. Keyed by
each read and write, each falls in one class, and the two limits fix what each
class may do. A read acted on would otherwise be an act on a value never read: a
guessed position, which the record on axis carriage refuses
([project-management:DEC-051](../../../.pkit/capabilities/project-management/decisions/DEC-051-axis-carriage-activation.md)
point 6), or a classification judged unread, which ADR-053 point 2 refuses. A
read only reported must not report what it did not see. A write after the act
cannot be the act not made.

**Why filing reads first only where the board holds the state.** An issue filed
where the board holds its state, and then left with no card, has no position.
Every command that reads a position refuses or skips it, and undoing the filing
is a destructive write. So filing under a credential the board does not answer
gives no command anything to act on, and refusing first loses nothing. Filing
reads the board's Status field to write the first Status already: read first and
carried to that write, the read moves rather than adds a call. Where only
priority or workstream lives on the board, an issue is workable without its
card. A hook writes those values (ADR-053 point 6), and a later add and write
repair the card. Refusing there would stop filing for a card the issue can do
without, at a call on every filing.

**Why an act made keeps a code apart.** A clean success hides that a step the
act requires is missing. A code that reads as the act not made invites a caller
to make it again, filing a second issue. DEC-024 keeps a hook's failure out of
the exit, so that a step an adopter chose to add cannot make every filing fail
from an agent's view and discourage hooks. The card and a value the map binds to
the board are no such step: DEC-019 requires the card from filing, and DEC-024's
first hook fires only once the issue is filed and added. A code of its own tells
the agent that the issue exists and what it owes, as DEC-048 point 4's
code does for a link not made.

**Why membership comes under the contract.** The membership check's one read is
a filtered read that names no board. Under a credential the board does not
answer, it reports every issue off the board, and where the post-check workflow
runs under such a credential, it says so on every issue it checks. ADR-053 kept
the check apart because it judged from a payload already fetched. That payload
is the read that cannot tell nothing from nothing visible. Read as every card
is, membership has one account of an issue's card, as a state has (ADR-074 point
6), at one request in a project with a board and none without.

**Why a board that did not answer is reported at the drift severity.** It is a
fault of the check's credential, not of the issue. The reject DEC-019 gives an
issue off the board at filing judges the issue, and giving it to a fault of the
credential would fail every issue the check sees, for something no issue can
repair.

**Why these limits sit in this record.** They bind every command that reads or
writes the board, as ADR-053 point 2's raise and ADR-074 point 5's limits do,
and say what no command may choose. Set in each command's own record, they would
be one account for each command of what a board that did not answer means: the
drift the seam exists to end. Each command's choice within them stays with the
capability, as DEC-051 point 6 records a seat's. An adopter meets them in each
command's message, which names the cause and the way out, and in the
capability's reference for the command.

**Why a scan.** The seam's ownership of every read was stated and not enforced,
and reads grew outside it, each with its own sense of an answer, a stored id
standing in for one among them. A stated single home is provisional until a test
holds it, the lesson ADR-031 point 4 draws for writes.

### Alternatives considered

- **Take an empty answer as the board's.** The case: no extra read. Rejected:
  under a credential the board leaves out, every issue reads as off the board
  and every listing as empty, the measured case.
- **Take every empty answer as a board that did not answer.** The case: no
  premise about the service. Rejected: an issue truly off the board could never
  be reported, so DEC-019's drift would never be found.
- **Take the board's own read as enough,** trusting an issue's own cards to list
  its card on every board the credential reaches. Rejected: that premise is
  unmeasured, least of all for the credential that prompted this record, and no
  sign of the credential's kind could tell where it fails. The witness tests it
  in the same request, at no call.
- **Pair the reads within one run,** from one constructor, environment and host.
  Rejected: it holds only where each read takes its host and credential the same
  way, which a test of the pair cannot see. One request holds them by
  construction.
- **Read the sign from the credential's kind,** trusting an empty answer under a
  person's token and not under an app's or a workflow's. Rejected: a person's
  token can meet the same silence, and the kind is a read that can fail.
- **Ask the service for the credential's grants** before reading, such as its
  scopes or an installation's permissions. Rejected: each kind of credential
  reports its grants its own way or not at all, and no grant says whether a
  board was shared with the account.
- **Trust a stored board id as the sign,** so the health check is no stricter
  than the commands it serves. Rejected: the id was written under another
  credential at another time, and under this record no command takes it as the
  sign either.
- **Decide membership from a walk of the board's cards.** Rejected for ADR-074
  point 6's reasons: a cost and a page bound set by the board's history, and a
  second account of which card is an issue's. A withheld card leaves the walk no
  more whole.
- **Keep the membership check off the contract** (ADR-053, Boundaries).
  Rejected: its one read is the filtered read that answers empty.
- **Refuse any change to a field's options while a withheld card remains.**
  Rejected: adding or renaming an option alters no card's value.
- **Leave a withheld card out of the count, and go on.** Rejected: removing an
  option no card it read holds clears the value of a card it could not read.
- **Refuse early on the service's answer that the credential may not change the
  board.** Rejected: that answer is unmeasured for an app's token and a token's
  scopes, and a wrong "no" refuses with no way out.
- **One posture for every command,** refusing wherever the board did not answer,
  or reporting and going on everywhere. Rejected: refusing everywhere stops
  filing on a board that only mirrors the labels. Going on everywhere files
  issues whose state lives on a board no command can reach.
- **Refuse filing first wherever the map binds an axis to the board.** Rejected:
  where only priority or workstream lives there, the issue is workable without
  its card, which a later add repairs, and the read would cost a call on every
  filing.
- **Undo the act when a write it requires fails after it,** such as by closing
  the issue just filed. Rejected: it is destructive, it is a second write that
  can fail as the first did, and reading the board first leaves little to undo.
- **Give a failed add at filing a clean exit and a warning.** Rejected: DEC-019
  requires the card from filing, and a caller reading the exit takes the filing
  as whole.
- **Give a write that fails after the act the broken tool's code.** Rejected:
  that code reads as the act not made, and invites a second filing.
- **Split the record,** accepting at once what rests on nothing unmeasured, and
  the rest once measured. Rejected: the witness, the key on a value not read,
  and the permission answer taken as advice leave nothing resting on a
  measurement.

## Implications

- **ADR-053 is partly superseded, and refined in place,** on this record's
  acceptance and in this change
  ([the decisions README, "Refining an accepted record"](../../../.pkit/decisions/README.md#refining-an-accepted-record)):
  - **Its top line,** before its Summary, with its Boundaries' membership bullet
    left as it stands:

    > **Partially superseded by [ADR-096](ADR-096-board-did-not-answer.md).**
    > The board-membership check comes under this contract: it reads an issue's
    > card through the board read seam, as every card is read, and reports a
    > board that did not answer as that. Overturned, in the Boundaries' bullet
    > on the membership check: that the check is outside the contract, that it
    > judges over a payload the gate already fetched, from incidental data, that
    > neither it nor a value read is the model for the other, and that an
    > undetermined membership is reported as a finding. ADR-096's "What this
    > overturns in ADR-053, and what stands" lists each passage. The rest of
    > ADR-053 stands.

  - **Refined in place,** each with the pointer "(refinement per ADR-096)", and
    each changing what ADR-053 decides:
    - **the Summary's first paragraph:** "Every command that reads or writes the
      board holds to the same ruling", in place of "Every command that reads a
      board-carried state holds to the same ruling". It gains that a read
      listing only what the credential may see is no answer from the board when
      it comes back empty, unless the same request shows the board answered,
      and that a read not whole is no answer;
    - **the Summary's second paragraph:** "what a failure means (the caller's
      decision, within limits every caller keeps)";
    - **point 1, its Layer 2:** the seam returns "whether the board answered, as
      ADR-096 point 1 tells it, whether its answer is whole, and what it said";
    - **point 2's first paragraph** gains that a read not whole, or one listing
      only what the credential may see that came back empty without the witness
      ADR-096 point 1 requires, is a read that did not succeed, on which the
      gate raises;
    - **point 2's reach paragraph:** "every command that reads or writes the
      board" in place of "every command that reads a board-carried state", and
      "its own to decide, within the limits ADR-096 point 4 sets for each read
      and write" in place of "its own to decide". Its last sentence, on the
      broken tool's code, holds before the command's act, and after it the
      command exits as ADR-096 point 4 sets.
  - **The rest of ADR-053 is checked to agree,** its Implications' "DEC-019's
    membership requirement is untouched" among it.
- **ADR-074 point 5 is refined in place,** with the pointer, which changes what
  it decides. Its two limits hold for every read and write of the board. "Each
  other command chooses its own within the limits and within ADR-096 point 4"
  stands in place of "Each other command chooses its own within the limits", and
  its sentence on the broken tool's code holds before the command's act, as in
  ADR-053.
- **No edit rests on a premise about the service.** Each says only that an empty
  filtered read is no answer without what ADR-096 point 1 requires, and points
  here for when it is one.
- **Accepting this record signs off each edit above**
  ([COR-064](../../../.pkit/decisions/core/COR-064-answer-delegate.md) point 6;
  [COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md)
  point 5).
- **ADR-031, DEC-019, DEC-024 and DEC-048 stand unedited, and so do ADR-074's
  other points.** ADR-074's state reads go through the seam and take its account
  of an answer, so point 1 reaches them through ADR-053's refined Layer 2, and
  point 2 here holds ADR-074 point 6's whole-or-nothing for every read. ADR-031
  point 3 keeps the add out of the constructor, and point 3 here says what
  counts as an add made. An issue off the board keeps DEC-019's severities.
  DEC-024's hooks keep their clean exit. DEC-048 point 4's code is of the kind
  point 4 here asks for after the act.
- **Tests hold each case:**
  - **a board that does not answer,** where its own read fails, or names no
    board or another board: the membership check reports the board unanswered,
    filing where the map binds the state to the board refuses before it creates
    the issue, a state read reports a board that cannot be read, and the health
    check fails;
  - **an absence with no witness,** where the board answers but no issue's own
    cards in the request list a card on it: the board did not answer;
  - **an absence with a witness:** the membership check reports the drift;
  - **a read not whole,** cut short at a page bound or carrying an error beside
    its data: the board did not answer;
  - **a write not made after the act:** where filing's add, or its first Status
    where the board holds the state, fails, the issue stays filed and filing
    exits with its code for a later step failed. Where the Status only mirrors,
    filing gives one line, and exits as its act does;
  - **a withheld card:** removing or merging an option refuses while a card
    holds a value the command did not read, adding or renaming one goes on, and
    a command over its own repository's issues sets the card aside;
  - **a project with no board:** the membership check and the add make no call,
    as ADR-053 point 3's no-board test holds for a composing gate;
  - **the scan** of point 6.
- **The work** is a surface change of the project-management capability. Its
  refusals and reports reach each project whose credential the board does not
  answer, each message naming the way out. The health check stops passing on a
  stored id in the same change that stops each command taking it as the sign.
  It needs no migration: nothing is renamed or removed, and a stored board id
  stays where it is, read as a name. A project's copy of the post-check workflow
  is its own (DEC-019), so point 3 reaches a copy made earlier only once the
  person copies the template again.
- **The post-check workflow** runs the membership check under the workflow's own
  token. Where the board does not answer that token, the workflow reports the
  board unanswered on each issue it checks, at the drift severity, and the
  person gives the workflow a credential the board answers, or keeps the report.
- **The measured case,** an App installation's token on a person's board:
  filing refuses where the map binds the state to the board, and elsewhere files
  and exits with its code for a later step failed. The person files under a
  credential the board answers, such as their own, until the agent holds one.
- **This change** carries this record and, on its acceptance, the edits to
  ADR-053 and ADR-074 above, and none of the work.
