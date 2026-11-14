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
  itself, and found either a card on it among the cards of an issue from the
  same repository, or no card on the board at all. Otherwise the board did not
  answer. A stored board id is no answer.
- **An answer cut short, or asking for less than the whole, is no answer.** A
  command that would clear or alter a value it did not count refuses.
- **Only a write's own answer says the write was made.**

What a command does then follows what each read and write is to it. A read it
acts on stops what rests on it. A read it only reports says the board did not
answer, never that an issue is off the board, and never that a check passed.
Once the act is made it stands, and a step it requires that failed gets an exit
code saying so. Filing reads the board first where the board holds the issue's
state. A project with no board makes no call to one.

This refines the board read-path contract
([ADR-053](ADR-053-board-read-path-contract.md)) and the record on a
board-carried state ([ADR-074](ADR-074-board-carried-state-read.md)) in place.
It overturns one ruling of ADR-053: that the membership check stays outside the
contract, and judges from what the issue's own read carried. It also decides
what counts as adding an issue to the board, which no other record decides.

**What a person accepting this weighs:**

- **ADR-053 is partly overturned.** The membership check makes one request of
  its own, in a project with a board, where it judged from the issue's own read.
- **The health check stops every operation the capability's skill runs** where
  the board does not answer the credential in use, in every project with a
  board, whatever its map binds there. The check passed on a stored id. It reads
  the board instead, and its failure refuses each operation the skill runs
  (DEC-017). In the measured case, the agent runs no operation through the skill
  until it holds a credential the board answers, and the person files under
  their own meanwhile.
- **Filing refuses before it creates an issue** where the map binds the state to
  the board and the board did not answer. Its read of the board moves earlier,
  and adds no call. Elsewhere filing reads nothing first.
- **A failed add at filing exits with a code of its own,** saying the issue was
  filed and a later step failed, in every project with a board, rather than
  clean. A caller that does not know the code reads it as a failure, so the
  message leads with the filed issue.
- **New reports and refusals** reach projects whose credential the board does
  not answer, and boards that hold cards but none of the issues the request
  reads from the repository, since nothing then shows the board answered. The
  membership check reports the board unanswered, and removing a field's option
  refuses while a card may hold it whose value the command did not count.

## Context

**The terms.**

- **The configured board** is the board the project's configuration names: by
  its number, under its owner, and by its node where one is stored. Where the
  configuration gives no owner, the owner is the one the capability resolves
  for the repository
  ([project-management:DEC-023](../../../.pkit/capabilities/project-management/decisions/DEC-023-gh-host-and-owner.md)).
- **A read of the board itself** is addressed to the board, by its node where
  one is stored or by its owner and number. It reads the board's identity, its
  fields or its cards.
- **A filtered read** lists only what the credential may see, and leaves the
  rest out without saying so: the boards an owner holds, or an issue's own
  cards.
- **A request** is one call to the service. It carries one credential, to one
  host.
- **A witness** is a card on the configured board, found among the own cards of
  an issue from the same repository as the issue whose card is absent, in the
  same request as a read of the board itself (point 1).
- **A whole read** covers all that its question asks of the board, reads every
  page of it, and carries no error on the board or its cards. A walk of the
  board's cards covers every card on the board, and an issue's own cards every
  card of the issue, archived ones included in both. A read that asks for less
  is not whole, however many pages it reads.
- **A withheld card** is a card on a board the credential reads, whose issue
  lies in a repository the credential may not read. The board returns it marked
  as withheld, with nothing of its issue.

**What was measured**
([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)). An
App installation's token, asked for the boards of a person's account, answered
with none, a public one included, and no error. The person's own token saw
three.

**What was not measured.**

- **What such a token gets from a read of one board by its number:** an error,
  or an answer naming no board, each a board that did not answer (point 1). An
  answer naming the board with none of its cards falls under the premise below
  that the board leaves no card out unsaid.
- **Whether an organisation's board answers such a token**
  ([project-kit#3172](https://github.com/aleskalfas/project-kit/issues/3172)).
  Either answer falls under point 1. It decides only which projects meet the
  refusals.
- **Whether the board returns a withheld card's values, or lets such a card be
  written.** Point 2 keys on a value the command did not count, so either answer
  changes only how often it refuses.
- **Whether the service's answer that a credential may change a board reflects
  an App's token, or a token's scopes.** Point 3 takes that answer as advice.
- **Whether a workflow's own token reaches any board.** By the service's
  documentation it reaches none. Point 5 holds either way.
- **Whether one request's reads see one state of the board.** The witness tests
  the credential's reach, not how fresh each read is. A card added just before
  the request may show on the board's side and not yet on the issue's. The
  issue then reads as having no card for that request, a finding the next read
  clears.

**What this record rests on.** Three premises about the service, none of them
measured. Where one fails, its case is left as it stands without this record,
and never made worse:

- **One repository's issues are filtered alike.** A credential that sees the
  card of one of a repository's issues on a board sees the card of each of them
  there. Point 1's witness rests on it. Were it wrong, an issue whose card the
  credential cannot see would read as off the board.
- **The board leaves no card out unsaid.** Its own read of its cards marks a
  withheld card rather than dropping it, and returns archived cards where asked.
  Point 2's count and point 1's empty board rest on it. Were it wrong, a card
  the read dropped would go uncounted, and a board that hid every card would
  read as empty.
- **A field's options are kept by their ids.** Adding an option, or renaming one,
  keeps every card's value, as the capability's option writes already assume.
  Point 2 lets such a change go on because of it. Were it wrong, the change
  would clear values.

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
- **A walk of the board's cards** asks for cards that are not archived, sets
  aside the cards of state issues, and takes a withheld card for a card with no
  issue. A command that removes a field's option counts the cards holding it
  from that walk, so the cards it left out or set aside go uncounted.
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
- **The environment health check gates each operation** the capability's skill
  runs. A failed prerequisite refuses the operation, and a declared board that
  does not resolve is one
  ([project-management:DEC-017](../../../.pkit/capabilities/project-management/decisions/DEC-017-prerequisites-bootstrap-migrate-discipline.md)).
- **Each command's exit codes are its contract** with its callers
  ([project-management:DEC-020](../../../.pkit/capabilities/project-management/decisions/DEC-020-methodology-as-executable-commands.md)).
- **A hook's failure leaves the exit clean,** so that one flaky hook does not
  make every filing fail from an agent's view. The first hook fires once the
  issue is filed and added to the board
  ([project-management:DEC-024](../../../.pkit/capabilities/project-management/decisions/DEC-024-lifecycle-hooks.md)).
- **A link that fails after an issue is filed** leaves the issue standing, and
  filing exits with a code of its own for it, meaning created but unlinked
  ([project-management:DEC-048](../../../.pkit/capabilities/project-management/decisions/DEC-048-from-report-auto-link.md)
  point 4).

The architecturally significant pins, each against a plausible alternative:

1. **What tells a board that did not answer from one that answered empty:** the
   empty answer itself, the credential's kind, its grants, a premise about the
   service, or a witness the same request carries.
2. **Where a witness is sought:** among the board's own cards, or among the
   issues of the repository whose issue's card is absent.
3. **Where that sign is read:** in the same request, in the same run, or from a
   stored id or an earlier answer.
4. **Whether an answer cut short, asking for less than the whole, or holding a
   card the command could not count, counts.**
5. **What tells a board that can be written:** a read, the service's answer on
   the credential's permission, or only the write.
6. **What a command does then:** one posture for every command, one chosen by
   each command, or one set by what each read and write is to it.
7. **Whether the membership check comes under the contract.**

## Decision

**An answer that a card is absent counts only where the same request shows the
board answered, and only where it is whole. Only a write's answer says it was
made. A read a command acts on stops what rests on it. A read it only reports
says the board did not answer. Once the act is made it stands, with an exit code
that says so.**

### 1. An absence counts only where the same request shows the board answered

- **A read of the board itself** answered where its answer names the configured
  board, agreeing with every name the configuration gives it. An error, an
  answer with no board or no node in it, or one naming another board, is a
  board that did not answer. Whether the configured board answers is read only
  so, never from an owner's list of boards.
- **A card found is an answer.** A card on the configured board, found among an
  issue's own cards, is the board's answer that the issue is on it.
- **An absence needs a sign that the board answered.** A filtered read says a
  card is absent only where the same request read the board itself, the board
  answered, and one of two signs holds. Otherwise the board did not answer.
  - **A witness:** a card on the configured board, among the own cards of an
    issue from the same repository as the issue whose card is absent. The seam
    seeks it among that repository's issues the command reads, and among a page
    of that repository's issues it adds to the same request, and reads nothing
    more to find one.
  - **An empty board:** the board's own read of its cards is whole and holds
    none.
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

- **Cut short.** A read that is not whole is a board that did not answer: one
  stopped at a page bound, by a batch that failed or by pages it did not read,
  or one that asked for less than its question covers. It is never an answer
  that lacks what it did not read. This holds ADR-074 point 6's whole-or-nothing
  for every read of the board, the lookup of one issue's card among them. A walk
  that leaves archived cards out is such a read, however many pages it reads;
  [project-kit#3191](https://github.com/aleskalfas/project-kit/issues/3191)
  makes the capability's walks read them.
- **An error, placed by its path.** An error on the board, on its cards, or one
  the seam cannot place, makes the board not answer. An error on an issue's own
  node, outside its cards, is that issue's read failing, never the board's
  (ADR-074 point 2).
- **A value the command did not count.** A walk of the board's cards that
  returns a withheld card did not read its issue, and read its values only where
  the board returned them.
  - **A command that would clear or alter a value refuses while a card may hold
    it whose value the command did not count:** a withheld card whose values
    the board did not return, or a card its walk set aside for a reason of its
    own. Removing an option, or merging it into another, is such a command.
    Adding an option, or renaming one in place, alters no card's value, and goes
    on.
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
  gate's verdict. A board that did not answer stops what rests on it. For a
  gate's verdict on a value the map binds to the board, that stop is ADR-053
  point 2's raise, within the scope its point 3 sets. Any other stop is the
  command's refusal, with the broken tool's code where its codes tell one, or,
  choosing among many, the command takes nothing (DEC-051 point 6).
- **Any other read is one the command reports:** a check of an issue or of the
  setup, a value a command shows, or a note after its act. A board that did not
  answer is reported as that, where the finding or the value would stand, and a
  check reports it at its own severity. It is never a finding about the issue,
  never an unset value and never a check passed. The environment health check's
  severity is DEC-017's: a declared board that does not resolve fails it, and
  the capability's skill then refuses each operation.
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
  failed. That code is one of its own, beside filing's code for an issue filed
  whose link failed (DEC-048 point 4), which keeps its meaning.
- **Any other write that follows the act mirrors** a value another substrate
  carries, such as the Status where labels carry the state. Not made, it is one
  line saying what stands and what repairs it, and the command exits as its act
  does.
- **An act of many writes,** such as a sync of many cards, or a merge that
  rewrites each card holding an option before it removes the option. Each write
  made stands. A write that rests on one not made is not tried, such as removing
  an option while a card holds it. The command names each write not made, and
  where some were made, exits with a code saying the act was made in part.

Two rules order these around the act:

- **Before it.** Where a command's act would create an issue whose position the
  board holds, as filing does where the map binds the state to the board, the
  command reads the board itself first, and refuses before it acts where the
  board did not answer. Its refusal says why the board did not answer, gives the
  service's words, and names the way out that cause gives (point 6).
- **After it.** Nothing takes a code that reads as the act not made, and a write
  the act requires that was not made takes no code that reads as a clean
  success. The message leads with what stands, such as the filed issue. Where
  more than one later step failed, the message names each, and the command
  takes no code that names only one of them. Each of the capability's callers
  that acts on such a code, a loop that files many issues among them, reads it
  as the act made.

These are limits on every command, as ADR-053 point 2's and ADR-074 point 5's
are. They name no code. Within them, each command's choice stays its own, and
its codes with it (DEC-020), recorded with the command's discipline, as a seat's
choice is (DEC-051 point 6).

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
- **The seam builds a filtered read into one request with the board's own read
  and the reads a sign needs,** so no caller can pair it with a stored id or an
  earlier answer, and point 1 holds by construction rather than by each caller
  remembering it.
- **The seam says which it is:** the board answered, with what it said and
  whether that is whole, or the board did not answer, with why. The cause is
  the service's words verbatim, an answer naming no board or another, a read
  not whole, or an absence with no sign. Each message names the way out its
  cause gives: a credential the board answers, the configuration's names put
  right, one of the repository's issues added to the board, or a later try.
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
- **Not the override at filing.** DEC-019 lets one filing name a board other
  than the configured one. Every other command reads the configured board, so
  an issue added only to another has no card there. Whether a filing may name
  another board where the map binds the state to the board is the capability's
  to decide.
- **Not the health check's gate.** DEC-017 sets what its failure stops. This
  record says only what counts as the board's answer to it.

## Rationale

**Why a witness in the same request.** The service leaves out of a filtered
read what the credential may not see, and says nothing. So its empty answer is
the same for "nothing there" and "nothing you may see", and no reading of that
answer alone tells them apart. A read of the board itself names the board only
to a credential that reaches it. It does not show that the same credential's
filtered reads see the board: that the two agree is a premise about the
service, unmeasured for the very credential that prompted this record. A card on
the board, found among the own cards of an issue from the same repository in the
same request, shows it for that credential, that board and that repository. The
board's read and the witness travel in the request the command makes anyway, so
they cost no call.

**Why the witness is sought in the issue's own repository.** The board's own
cards come in the board's order. An empty board, one whose first cards are
drafts or pull requests, or an organisation's board whose first cards are
withheld from a credential that reads one repository, would give no witness
among them. Every issue truly off such a board would then read as unanswered,
and DEC-019's drift would go unfound there. The credential reads the repository
of the issue it checks, so none of that repository's cards is withheld from it,
the board's order does not touch them, and the premise they rest on is about one
repository. Where the board holds no card at all, nothing can witness, so a
whole read of its cards that finds none is its answer. What is left is a board
holding cards, none of them of the repository's issues the request reads, such
as a repository's first issues on a shared board. It reads as unanswered, and
its message names that cause and its way out: add one of the repository's
issues to the board.

**Why the request, and not the run.** Reach is a fact of the credential at the
time. A token is revoked, an app's grant changes, a board is shared or unshared,
without notice. A stored id was written under whatever credential set the
project up, and the credentials this record is for are the ones that differ from
it. Two reads in one request share one credential and one host by construction.
Two reads in one run need not, since one may take its host from the
repository's remote and another from the environment, and a test cannot see
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
id. A read that asks for less than its question covers lacks the rest before it
starts, so reading every page it asked for makes it no more whole. An archived
card is where the board's walk and an issue's own cards part (ADR-074's
Rationale), and a walk that leaves it out reads as whole by its own pages.

**Why an error is placed by its path.** One request carries the board's read and
the issues' reads. An issue deleted or moved between the command's read of it
and the seam's leaves an error on that issue's node alone. Taking it for the
board's would turn one failed issue read into a board that did not answer, the
mis-attribution ADR-074 point 2 refuses.

**Why a value not counted decides the refusal.** Removing an option, or merging
it into another, changes the value of every card that holds it, counted or not.
Removing one that no card it counted holds would clear the value of a card it
did not count, withheld or set aside: the overwrite of a value never read that
ADR-053 point 4 calls a defect where back-fill's emitted script does it
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
cannot be the act not made. An act of many writes, failing part way, is an act
made in part, so neither the code of an act not made nor a clean one fits it,
and a write that rests on one not made would act on what never happened.

**Why filing reads first only where the board holds the state.** An issue filed
where the board holds its state, and then left with no card, has no position.
Every command that reads a position refuses or skips it, and undoing the filing
is a destructive write. So where the board does not answer the credential,
filing gives no command anything to act on, and refusing first loses nothing.
Filing reads the board's Status field to write the first Status already: read
first and carried to that write, the read moves rather than adds a call. The
read asks the board itself and no witness, since a board holding none of the
repository's issues has none to give before the repository's first filing. The
add's own answer then shows the card made (point 3). A credential
whose filtered reads alone miss the board passes this read, and later reads
report the board unanswered, never an issue off it. Where only priority or
workstream lives on the board, an issue is workable without its card. A hook
writes those values (ADR-053 point 6), and a later add and write repair the
card. Refusing there would stop filing for a card the issue can do without.
Through the capability's skill, the health check stops filing sooner wherever
the board does not answer (DEC-017). This point sets what filing does wherever
it runs.

**Why an act made keeps a code apart.** A clean success hides that a step the
act requires is missing. A code that reads as the act not made invites a caller
to make it again, filing a second issue. DEC-024 keeps a hook's failure out of
the exit, so that a step an adopter chose to add cannot make every filing fail
from an agent's view and discourage hooks. The card, and a value the map binds
to the board that the command writes itself, are no such step: DEC-019 requires
the card from filing, and DEC-024's first hook fires only once the issue is
filed and added. A value only a hook writes, such as priority or workstream
bound to the board, stays the hook's, with its clean exit. A code of its own
tells the agent that the issue exists and what it owes, as DEC-048 point 4's
does for a link not made. Taking that code would change the one meaning DEC-048
gives it. A caller that knows only the earlier codes reads the new one as a
failure, which is why the message leads with the filed issue and the
capability's own callers read the code as filed.

**Why the health check fails on a board that did not answer.** DEC-017's check
exists so that an operation stops before it starts in an environment it cannot
finish in, rather than halfway through a mutation. In a project with a board,
filing owes each issue its card (DEC-019), whatever the map binds, so a board
that does not answer is such an environment. A pass on a stored id lets every
operation start on a board none of them can read. The check is stricter than
some commands it gates: where the board only mirrors the labels, filing run
directly would go on and report its card not made. DEC-017 chose to stop on any
gap in the environment before an operation starts, and this record leaves that
choice where it stands.

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
capability, as DEC-051 point 6 records a seat's. They name no exit code: each
command's codes are its contract with its callers, the capability's to set
(DEC-020). They say only what any code may claim about a board that did not
answer or a write not made, as ADR-053 point 2's sentence on the broken tool's
code already does. An adopter meets them in each command's message, which names
the cause and the way out, and in the capability's reference for the command.

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
  sign of the credential's kind could tell where it fails. The witness narrows
  it to one repository and tests it in the same request, at no call.
- **Seek the witness among the board's own cards.** Rejected: they come in the
  board's order, so an empty board, one led by drafts or pull requests, or one
  led by cards withheld from the credential gives none, and each issue off such
  a board reads as unanswered.
- **Take a board with no card as unanswered too.** Rejected: before its first
  card every issue off the board would read as unanswered, and the premise that
  the board leaves no card out unsaid is one point 2 rests on already.
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
  credential at another time, no command takes it as the sign either, and a
  pass on it lets every operation the check gates start on a board none can
  read.
- **Let the health check warn where the board does not hold the state,** so
  that a project whose board only mirrors goes on. Rejected: DEC-017 counts a
  declared board that does not resolve as a failed prerequisite, DEC-019 owes
  each issue its card from filing in every project with a board, and what the
  check's failure stops is DEC-017's to change.
- **Decide membership from a walk of the board's cards.** Rejected for ADR-074
  point 6's reasons: a cost and a page bound set by the board's history, and a
  second account of which card is an issue's. A withheld card leaves the walk no
  more whole.
- **Decide that an issue has no card only from its own cards,** in every
  command. Rejected: a whole walk, archived cards included, agrees with the
  issues' own cards on every card the credential reads, and a command that acts
  on the whole board, such as a sync, would read each issue's cards where one
  walk serves.
- **Keep the membership check off the contract** (ADR-053, Boundaries).
  Rejected: its one read is the filtered read that answers empty.
- **Refuse any change to a field's options while a withheld card remains.**
  Rejected: adding or renaming an option alters no card's value.
- **Leave a withheld card, or one the walk set aside, out of the count, and go
  on.** Rejected: removing an option no card it counted holds clears the value
  of a card it did not count.
- **Refuse early on the service's answer that the credential may not change the
  board.** Rejected: that answer is unmeasured for an app's token and a token's
  scopes, and a wrong "no" refuses with no way out.
- **One posture for every command,** refusing wherever the board did not answer,
  or reporting and going on everywhere. Rejected: refusing everywhere stops
  filing on a board that only mirrors the labels. Going on everywhere files
  issues whose state lives on a board no command can reach. DEC-017's gate is no
  such posture: it stops each operation on a gap in the environment, before any
  command reads, and stands.
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
- **Give a step that fails after the act the code a broken tool takes before
  it.** Rejected: that code reads as the act not made, and invites a second
  filing.
- **Give a failed add at filing the code of a link not made.** Rejected: DEC-048
  gives that code one meaning, created but unlinked.
- **Split the record,** accepting at once what rests on no premise, and the
  rest once measured. Rejected: where a premise fails, its case is left as it
  stands without this record and never made worse, so holding back what rests on
  one gains nothing.

## Implications

- **ADR-053 is partly superseded, and refined in place,** on this record's
  acceptance and in this change
  ([the decisions README, "Refining an accepted record"](../../../.pkit/decisions/README.md#refining-an-accepted-record)):
  - **Its top line,** one paragraph before its Summary, with its Boundaries'
    membership bullet left as it stands:

    > **Partially superseded by [ADR-096](ADR-096-board-did-not-answer.md).**
    > The board-membership check comes under this contract, and reads an
    > issue's card through the board read seam as every card is read.
    > Overturned: the Boundaries' bullet on the membership check, but for its
    > rules that membership stays with the flag, never routes through carriage,
    > and is reported at DEC-019's drift severity where it cannot be determined.
    > ADR-096's "What this overturns in ADR-053, and what stands" lists each
    > passage. The rest of ADR-053 stands.

  - **Refined in place,** each with the pointer "(refinement per ADR-096)", and
    each changing what ADR-053 decides. They reach reads only:
    - **the Summary's first paragraph, its last sentence:** "Every command that
      reads the board holds to the same ruling, gate or not", in place of
      "Every command that reads a board-carried state holds to the same ruling,
      gate or not", followed by "A read that lists only what the credential may
      see, and shows no card of the issue on the configured board, is the
      board's answer only where the same request shows the board answered, and
      a read that is not whole is no answer.";
    - **the Summary's second paragraph:** "**what a failure means** (the
      caller's decision, within limits every caller keeps)";
    - **point 1, its Layer 2:** "it returns a result object saying whether the
      board answered, as ADR-096 point 1 tells it, whether its answer is whole,
      and what it said", in place of "it returns a result object saying whether
      the board answered and what it said";
    - **point 2's first paragraph,** a sentence added: "A read that is not
      whole, or that lists only what the credential may see and shows no card
      of the issue on the configured board without a sign ADR-096 point 1
      requires, is a read that did not succeed.";
    - **point 2's reach paragraph:** "every command that reads the board, gate
      or not" in place of "every command that reads a board-carried state, gate
      or not", "its own to decide, within the limits ADR-096 point 4 sets" in
      place of "its own to decide", and as its last sentence "Where its exit
      codes tell a broken tool from a refusal, an unreadable board takes the
      broken tool's code, and once the command's act is made, a code that also
      says the act stands."
  - **Standing as written,** checked to agree:
    - **point 3, the Summary's scope of the raise, and its one-line contract:**
      the raise stays where carriage said `board`. Point 4 here adds no raise
      outside it. Its other stops are a command's refusal, made only in a
      project with a board, on a read the command's own act makes of the board;
    - **the rejected "Raise on any board read failure anywhere":** for the same
      reason, no project acquires a failure from a feature it does not use;
    - **the Boundaries' "Not a change to the label read path or the substrate
      write path":** the edits reach reads only, and point 3 here decides writes
      itself, keeping ADR-031's neutrality;
    - **its Implications' "DEC-019's membership requirement is untouched":**
      this record changes how membership is read, not what it requires.
- **ADR-074 is refined in place,** each edit with the pointer, and each changing
  what it decides:
  - **point 5, its sentence on the broken tool's code:** "Where a command's exit
    codes tell a broken tool from a refusal, an unreadable board takes the
    broken tool's code, and once the command's act is made, a code that also
    says the act stands.";
  - **point 5, its second paragraph:** "Each other command chooses its own
    within the limits, and within those ADR-096 point 4 sets for every read and
    write of the board", in place of "Each other command chooses its own within
    the limits";
  - **its Implications' bullet on a Status write, its last sentence:** "Filing
    handles a failed Status write as ADR-096 point 4 sets for a write after the
    issue is created: the issue stays filed", in place of "Filing handles a
    failed Status write as it handles every other write after the issue is
    created: the issue stays filed".

  Standing as written: point 5's two limits, which speak of a state, since
  point 4 here holds them for every read and write itself; its account of where
  ADR-053 point 2's ruling came from; and its Summary's "the command decides
  what a failed or empty read means to it", since this record says what counts
  as an answer and leaves what each outcome means to the command.
- **How the edits are sorted,** by the decisions README's one test: where this
  record decides otherwise on a choice a record made, that record is overturned
  in part, and where the choice stands, narrowed, widened or completed, it is
  refined. ADR-053 weighed the membership check against the value read, and kept
  them apart ("Both stand; neither is the model for the other"). This record
  takes the other side of that choice, so that bullet is overturned. ADR-053
  point 2 and ADR-074 point 5 chose that an unreadable board is a broken tool,
  never a finding, and give it the broken tool's code where a command's codes
  tell one from a refusal. This record keeps that choice. After the act, the
  code tells a broken tool from a refusal, and says too that the act stands, a
  case those sentences do not tell apart. So they are completed, not
  overturned, and ADR-074 takes no superseded line. Every other edit widens a
  reach or completes a definition, and each choice ADR-053 and ADR-074 made
  among their alternatives stands.
- **Accepting this record signs off each edit above**
  ([COR-064](../../../.pkit/decisions/core/COR-064-answer-delegate.md) point 6;
  [COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md)
  point 5).
- **Standing unedited:**
  - **ADR-031:** its point 3 keeps the add out of the constructor, and point 3
    here says what counts as an add made. Its point 5's back-fill gate keeps
    its member that the board resolves, read as point 1 here tells it, and its
    point 6's neutrality holds.
  - **DEC-017:** its board check is a live read of the declared board, and its
    gate refuses on the check's failure. This record says only what counts as
    the board's answer to it.
  - **DEC-019:** an issue off the board keeps its severities, and the override
    at filing stays its own.
  - **DEC-024:** a hook keeps its clean exit.
  - **DEC-048:** point 4's code keeps its meaning, and point 4 here asks for a
    code of its own beside it.
  - **DEC-051 point 6:** it follows ADR-053, so its outcome that an issue has no
    card takes point 1's account here, and each command's choice its limits,
    through ADR-053's refined Layer 2 and point 2.
- **Tests hold each case:**
  - **a board that does not answer,** where its own read fails, names no board
    or another, or where a stored node and the configured number name two
    boards: the membership check reports the board unanswered, filing where the
    map binds the state to the board refuses before it creates the issue, a
    state read reports a board that cannot be read, and the health check fails,
    a stored id or not;
  - **an absence with no sign,** where the board answers and holds cards, but
    no issue from the repository in the request shows one: the board did not
    answer, and the message names that cause;
  - **an absence with a sign,** a witness among the repository's issues the seam
    adds, or a board whose whole read holds no card: the membership check
    reports the drift;
  - **a read not whole,** cut short at a page bound, asking only for cards that
    are not archived, or carrying an error on the board or its cards: the board
    did not answer. An error on an issue's own node alone is that issue's read
    failing;
  - **a write not made after the act:** where filing's add, or its first Status
    where the board holds the state, fails, the issue stays filed and filing
    exits with its own code for a later step failed, apart from DEC-048's. Where
    the Status only mirrors, filing gives one line, and exits as its act does;
  - **an act of many writes** failing part way: the writes made stand, a write
    resting on one not made is not tried, and the command exits with a code
    saying the act was made in part;
  - **a card not counted:** removing or merging an option refuses while a
    withheld card, or one the walk set aside, may hold it, and counts an
    archived card that holds it. Adding or renaming one goes on, and a command
    over its own repository's issues sets a withheld card aside;
  - **a project with no board:** the membership check and the add make no call,
    as ADR-053 point 3's no-board test holds for a composing gate;
  - **the scan** of point 6.
- **The work** is a surface change of the project-management capability. It
  needs no migration: nothing is renamed or removed, and a stored board id stays
  where it is, read as a name. A project's copy of the post-check workflow is
  its own (DEC-019), and makes its own add where it remediates, so point 3
  reaches a copy made earlier only once the person copies the template again.
  Where the board does not answer a copy's token, the workflow reports the board
  unanswered on each issue it checks, at the drift severity, until the person
  gives it a credential the board answers.
- **This change** carries this record and, on its acceptance, the edits to
  ADR-053 and ADR-074 above, and none of the work. The walks' reading of
  archived cards is project-kit#3191's.
