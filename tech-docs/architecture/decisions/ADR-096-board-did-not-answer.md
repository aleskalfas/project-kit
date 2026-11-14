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
  itself, and found a card on it among the cards of an issue from the same
  repository. Otherwise the board did not answer. A stored board id is no
  answer.
- **An answer cut short, or asking for less than the whole, is no answer.** A
  command that would clear or alter a value it did not count refuses.
- **Only a write's own answer says the write was made.**

What a command does then follows what each read and write is to it. A read it
acts on stops what rests on it. A read it only reports says the board did not
answer, and never reports an issue off the board or a check passed. A command
whose act needs a later write to the board, as filing needs the issue's card,
reads the board before it acts. Once the act is made it stands, and a step it
requires that failed gets an exit code saying so. A merge is landing work's
act, and the issue's Done after it mirrors the close the merge makes. What
the act sets off on other issues, such as the forward cascade, is the
capability's to settle, within the same rules: the command never acts on a
board that did not answer as though it had, and never takes a code that reads
as the act not made. A project with no board makes no call to one.

This refines the board read-path contract
([ADR-053](ADR-053-board-read-path-contract.md)) and the record on a
board-carried state ([ADR-074](ADR-074-board-carried-state-read.md)) in place,
and narrows the exit code filing takes for a failed link to a report, where
its card failed too. It overturns one ruling of ADR-053: that the membership
check stays outside the contract, and judges from what the issue's own read
carried. It also decides what counts as a write made on the board, an issue's
add among them, which no other record decides.

**What a person accepting this weighs:**

- **ADR-053 is partly overturned.** The membership check makes one request of
  its own, in a project with a board, where it judged from the issue's own read.
- **A command reads a fixed page of issues beside those it acts on,** where
  ADR-074 has it read their cards and no others, which this record widens. A
  request that could find an issue with no card carries, for each repository
  whose issues it reads, up to a hundred of that repository's recent issues,
  read only for a sign that the board answered, at no extra call. A read made
  in several requests carries an issue one request found carded into the
  others, where it counts only if its card shows again. That costs one call
  more for each request made before it was found that lacked one, made again
  once at the end, so at worst nearly twice the read's calls.
- **Filing refuses before it creates an issue** wherever a board is configured
  and the board did not answer, through the skill or not. Where the board holds
  the state, it refuses too where the board lacks the Status field, or the
  option of the state the issue is filed into. That is the record's own choice,
  not DEC-017's: an outage of the service's boards is then a filing outage in
  every project with a board, and an issue whose state lives on labels,
  workable until a later add, goes unfiled. The read first adds no read of the
  board where filing writes a first Status, and is one call more on each
  filing where the map leaves the state out.
- **A failed add at filing exits with a code of its own,** saying the issue was
  filed and a later step failed, rather than clean, and so does a first Status
  not written where the board holds the state. A caller that does not know the
  code reads it as a failure, so the message leads with the filed issue. Where
  a filing's link to a report failed beside such a write, filing takes this
  code rather than DEC-048's, and DEC-048 gains a sentence saying so. Wherever
  no such write failed, a failed link keeps DEC-048's code.
- **The health check reads the board on each run, and never passes on a stored
  id.** Its failure stops what DEC-017 has it stop: every operation the
  capability's skill runs, those that touch no board among them, migrate, and a
  CI job that gates on it. So in a project with a board, an outage of the
  service's boards, or a credential the board does not answer, stops them all,
  and a CI job under the workflow's own token, which reaches no board, fails on
  each run. Whether the check fails or warns there is DEC-017's to decide, and
  [project-kit#3193](https://github.com/aleskalfas/project-kit/issues/3193)
  proposes that it warn.
- **New reports and refusals** reach projects whose credential the board does
  not answer, and boards on which no issue the read sees shows a card, such as
  an empty board, or a repository's first issues on a shared board. The
  membership check reports the board unanswered there, at the drift severity,
  and removing a field's option refuses while a card may hold it whose value the
  command did not count. A stored node naming a board under another owner than
  the one the capability resolves reads as a board that did not answer, until
  the configuration names that owner.
- **The post-check workflow's template gains a setting for a credential the
  board answers.** The workflow's own token reaches no board, by the service's
  documentation. Under it, the membership check reports the board unanswered on
  each issue, and where the map binds an axis to the board, the presence gate's
  raise (ADR-053 point 2) fails each issue once that gate reads the board. A
  credential set there is exposed to a job that anyone who can open an issue
  starts, and to the tools that job fetches at run time.
- **Four premises about the service, none measured.** Where one of the first
  three fails, its case is as it is without this record. Where a host refuses
  an argument a request carries, each read through such a request reports the
  board unanswered there, the membership check's among them.

## Context

**The terms.**

- **The configured board** is the board the project's configuration names: by
  its number, under its owner, and by its node where one is stored. Where the
  configuration gives no owner, the owner is the one the capability resolves
  for the repository
  ([project-management:DEC-023](../../../.pkit/capabilities/project-management/decisions/DEC-023-gh-host-and-owner.md)).
  Where one filing names another board in its place, as DEC-019 lets it, that
  board is the configured board for that filing's own reads and writes, and for
  nothing else. It is read by its number, since no node is stored for it.
- **A read of the board itself** is addressed to the board, by its node where
  one is stored or by its owner and number. It reads the board's identity, its
  fields or its cards.
- **A filtered read** lists only what the credential may see, and leaves the
  rest out without saying so: the boards an owner holds, or an issue's own
  cards.
- **A request** is one call to the service. It carries one credential, to one
  host.
- **A witness** is a card on the configured board, found among the own cards of
  an issue from the same repository as the issue whose card is absent, the
  repository told by its node id, in the same request as a read of the board
  itself (point 1).
- **The page** a witness is sought in is a fixed page of one repository's
  issues that the seam adds to a request, in two orders: those most recently
  created, of every state, and the open ones most recently updated. It holds no
  more than a hundred issues in all, and no more than ten of each one's own
  cards. The seam fixes how many it takes in each order, and its tests hold the
  numbers. It is read only for a witness (point 1).
- **A whole read** covers all that its question asks of the board, reads every
  page of it, and carries no error on the board or its cards. A walk of the
  board's cards covers every card on the board, and an issue's own cards every
  card of the issue, archived ones included in both. A read that asks for less
  is not whole, however many pages it reads. The page is no read that must be
  whole: what it leaves unread takes away a witness, and nothing else.
- **A withheld card** is a card on a board the credential reads, whose issue
  lies in a repository the credential may not read. The board returns it marked
  as withheld, with nothing of its issue.
- **A command's act** is the change it is run to make, the one its success
  reports: an issue filed, an issue moved, a field set, an option removed, a
  pull request merged. Where a command makes a change that cannot be undone,
  as a merge cannot
  ([project-management:DEC-026](../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md),
  its failure semantics), that change is its act, and what it does after it
  follows the act: landing work merges, and then moves its issue to Done. A
  change made first to prepare the act, such as the branch or the pull request
  a command makes before it moves the issue, comes before the act, and is no
  write that follows it. What the act sets off on another issue, such as the
  forward cascade's moves of the issue's ancestors
  ([project-management:DEC-006](../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)),
  is no part of it (point 4).
- **A later step** is any step a command makes after its act, on the board or
  off it, such as filing's add of the issue's card, its link to a report, or a
  hook.

**What was measured**
([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)). An
App installation's token, asked for the boards of a person's account, answered
with none, a public one included, and no error. The person's own token saw
three.

**What was not measured.**

- **What such a token gets from a read of one board by its number.** An error,
  or an answer naming no board, is a board that did not answer (point 1). An
  answer naming the board answers for the board's identity. Each absence then
  turns on its witness, and a walk of the board's cards on the premise below
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

**What this record rests on.** Four premises about the service, none of them
measured. Where one of the first three fails, its case is left as it stands
without this record, and never made worse. The fourth is the exception, and
says what its failure costs:

- **One repository's issues are filtered alike.** A credential that sees the
  card of one of a repository's issues on a board sees the card of each of them
  there. Point 1's witness rests on it. Were it wrong, an issue whose card the
  credential cannot see would read as off the board.
- **The board leaves no card out unsaid, and withholds only what the credential
  may not read.** Its own read of its cards marks a withheld card rather than
  dropping it, withholds a card only where the credential may not read its
  issue's repository, and returns archived cards where asked. Point 2's count
  rests on it, as do a command that sets a withheld card aside because it acts
  only on its own repository's issues, and one that decides from a walk that an
  issue has no card, such as a sync. Were it wrong, a card the walk dropped, or
  withheld from a credential that reads its repository, would go uncounted, and
  its issue would read as having none.
- **A field's options are kept by their ids.** Adding an option, or renaming
  one, keeps every card's value, as the capability's option writes assume.
  Point 2 lets such a change go on because of it. Were it wrong, the change
  would clear values.
- **The host takes every argument a request carries,** such as those that ask
  for archived cards and set the orders of the page a witness is sought in.
  Every read here rests on it. Were it wrong on some host, the service there
  would refuse each request that carries the argument, whole, and each read
  through such a request would report the board unanswered, naming the
  argument. That is worse than without this record for a read that carries no
  such argument without it: the membership check there would never be
  determined.

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
  issue's, has a command read the cards of the issues it acts on and no
  others, and reads a listing whole or not at all (ADR-074 point 6). Each
  command decides what an outcome means, within two limits: it never guesses,
  and it keeps a broken board apart from a finding (ADR-074 point 5).
- **The substrate write-path contract** names adding an issue to a board out of
  the one constructor for field values
  ([ADR-031](ADR-031-substrate-write-path-contract.md) point 3), and says
  nothing of what counts as an add made.
- **Every issue of a project with a board belongs on it:** a missing card is a
  reject at filing, and drift at warning severity on an existing issue
  ([project-management:DEC-019](../../../.pkit/capabilities/project-management/decisions/DEC-019-mandatory-issue-state.md)).
- **A move brings each ancestor behind the issue up to it,** the forward
  cascade, so that a container is never behind the work under it (DEC-006).
  What it does at an ancestor whose position cannot be read is left to a
  project-management record (ADR-074, Boundaries). A closed issue is done
  whatever its card says
  ([project-management:DEC-062](../../../.pkit/capabilities/project-management/decisions/DEC-062-axes-chosen-in-the-map.md)
  point 5).
- **The environment health check gates each operation** the capability's skill
  runs, and migrate, and a CI job may gate on it too. A failed prerequisite
  refuses the operation, and a declared board that does not resolve is one
  ([project-management:DEC-017](../../../.pkit/capabilities/project-management/decisions/DEC-017-prerequisites-bootstrap-migrate-discipline.md)).
  It checks the environment, and scans no issue's state (DEC-019).
  The check degrades rather than refuses where an axis's substrate is
  unsupported
  ([project-management:DEC-036](../../../.pkit/capabilities/project-management/decisions/DEC-036-substrate-pluggable-adoption.md)
  point 3), and a declared board that does not resolve is no such axis, as
  ADR-031 point 5 has it for back-fill, which counts it among the checks that
  still fail where a board field is to be written.
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
2. **Where a witness is sought, and in what order:** among the board's own
   cards, in the board's order or filtered to the repository, or among the
   issues of the repository whose issue's card is absent, in one order or two
   that the seam sets.
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
  board, agreeing with each of its names, the owner the capability resolves
  among them where the configuration gives none. An error, an answer with no
  board or no node in it, or one naming another board, is a board that did not
  answer. Whether the configured board answers is read only so, never from an
  owner's list of boards. The add, and every read the seam makes by number,
  address the board by its number under that owner, so a stored node naming a
  board under another owner names one they miss.
- **A card found is an answer.** A card on the configured board, found among an
  issue's own cards, is the board's answer that the issue is on it.
- **An absence needs a witness.** A filtered read says a card is absent only
  where the same request read the board itself, the board answered, and a
  witness shows that the credential's filtered reads see the board: a card on
  the configured board, among the own cards of an issue from the same
  repository as the issue whose card is absent, the repository told by its node
  id. Otherwise the board did not answer, whatever the board holds, an empty
  board among them.
- **Where the witness is sought.** Among that repository's issues the request
  reads, and on the page of that repository's issues that the seam adds to the
  same request, one page for each repository. It reads nothing more to find
  one, save an issue carried in from another request of a read made in several
  (below). The page, and an issue so carried, are only a search for a witness.
  A card found there witnesses, and nothing they read is reported of any
  issue: an issue the command acts on that also lies on the page is judged
  from the command's own read of it. An error placed on either, or a part of
  the page left unread, takes away a witness it might have given, and nothing
  else: it never fails the command's read, and never on its own makes the
  board unanswered. A request that fails whole, with no error placed on any
  part of it, fails every read it carries, as any request does, and the page's
  weight is among its possible causes.
- **The witness is in the request.** A stored board id names a board. It was
  written under some credential at some time, and says nothing of this one.
  Another request's answer, an earlier run's or another credential's is no
  sign.
- **A read made in several requests carries a witness across them,** such as a
  listing read in batches. Once one of its requests finds an issue's card on
  the configured board, each request made after it carries that issue for its
  repository. Each request made before it that found no witness for that
  repository is made again once, after the read's last request, carrying an
  issue found for each repository it lacks one for. So the read costs at most
  one call more for each request made before a witness was found. A carried
  issue witnesses only where the request carrying it shows its card again.
  The request made again is the one that answers: its absences are judged from
  it alone, and nothing of the first is kept. So a request lacks a witness
  where nothing it reads for its repository, its own issues, its page or an
  issue carried into it, shows a card on the board. Carrying an issue
  never takes a request past what the service lets one request ask, such as
  how many issues it may name.
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
  for every read of the board, the lookup of one issue's card among them, and
  the search for a witness excepted, the page and an issue carried in for one
  (point 1). A walk that leaves archived cards out is such a read, however
  many pages it reads.
- **An error, placed by its path.** The paths of the search for a witness are
  placed first: an error whose path lies within the page, or within an issue
  carried in from another request only as a witness, is that search's,
  whatever it points at, and takes away a witness, and nothing else (point 1).
  Any other error on the board, on its cards, or one the seam cannot place,
  makes the board not answer. An error on an issue's own node, outside its
  cards, is that issue's read failing, never the board's (ADR-074 point 2).
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
  command's own, and takes the broken tool's code where its codes tell one. A
  command choosing among many takes nothing there, as a seat choosing work
  does (DEC-051 point 6).
- **Any other read is one the command reports:** a check of an issue or of the
  setup, a value a command shows, or a note after its act. A board that did not
  answer is reported as that, where the finding or the value would stand. It is
  never reported as a finding about the issue, an unset value or a check
  passed.
  - **A check of an issue or of the setup** reports it at the severity the
    check gives that outcome, and that severity sets the command's code. Where
    the severity lets through what the check gates, an issue or an operation,
    the command exits as that severity does, which may be the code a clean run
    takes, and its report says what it could not see. Where it stops what it
    gates, the command takes the broken tool's code where its codes tell one,
    never the code of a finding.
  - **The environment health check's** severity, and what its failure stops,
    are DEC-017's. Beside its read of the board it carries the page, and where
    the page shows no witness, it warns, and never fails on it. The warning
    says that the credential's reach to the board's cards could not be shown,
    names no issue, and gives both causes it can be: the repository's recent
    issues all off the board, or none yet, or a credential whose filtered
    reads miss it.
  - **Any other read it reports,** such as a value it shows, takes the broken
    tool's code where the command's codes tell one. A note after the command's
    act takes no code of its own: the command exits as its act does.
- **A write that is the act,** such as setting a field, or adding a card where
  that is all the command does. Not made, it is the act not made, and the
  command says so with the board's words.
- **A write that follows the act, and that the act requires:** the card filing
  adds, since an issue belongs on the board from its filing (DEC-019), or a
  value of the same issue whose source is the board, that the command writes
  itself, such as the first Status where the map binds the state to the board.
  The Done of an issue the command or its act closes is none: it mirrors that
  close (below). Not made, the act stands, since undoing it is a write too, and
  a destructive one. The command says what stands, gives the write not made
  with the board's words and the remedy, and exits with a code saying the act
  was made and a later step failed. That code is one of its own, beside
  filing's code for an issue filed whose link failed (DEC-048 point 4), which
  keeps its meaning.
- **Any other write that follows the act mirrors** a value another substrate
  carries, such as the Status where labels carry the state, or the Done of an
  issue that is closed, or that the command or its act closes, since a closed
  issue is done whatever its card says (DEC-062 point 5). Landing work's Done
  is such a write: its merge closes the issue, or the command closes it after,
  and a merge closes its issue with no board in the loop (DEC-062's
  Rationale). Not made, it is one line saying what stands and what repairs it,
  and takes no code of its own: the command exits as its act does.
- **An act of many writes,** such as a sync of many cards, or merging one
  option into another, which rewrites each card holding the one before it
  removes it. Each write made stands. A write that rests on one not made is not
  tried, such as removing an option while a card holds it. The command names
  each write not made, and where some were made, exits with a code saying the
  act was made in part.
- **What the act sets off on another issue,** such as the forward cascade's
  reads and moves of the issue's ancestors (DEC-006), is none of these.
  "Before it" below asks no read of such an issue before the act, and whether
  the act waits on one is not decided here (Boundaries). Once the act is made,
  it stands whatever becomes of them. What the command does where the board did
  not answer for such an issue, or a write to it was not made, is for a
  project-management record not yet written, which ADR-074's Boundaries leave
  the cascade to. The two limits above hold there, and once the act is made,
  no code the command takes for it reads as the act not made ("After it").

Two rules order these around the act:

- **Before it.** Where a write to the board that the act requires follows the
  act (above), the command first reads from the board what that write needs,
  and refuses before it acts where the board did not answer, or where its
  answer lacks what the write names, such as the Status field, or the option
  of the state the command writes. Where that write makes a read anyway, that
  read is the one, made before the act and carried to the write. Filing is
  such a command in every project with a board, since an issue owes its card
  from filing (DEC-019), and its read asks the board the filing adds to. The
  refusal says why the board did not answer, or what its answer lacks, gives
  the service's words, and names the way out that cause gives (point 6).
- **After it.** Once the act is made, no read or write of the board after it
  takes a code that reads as the act not made, whether it is a write the act
  requires, a mirror, a note, or a read or write of another issue the act set
  off. A write the act requires that was not made takes no code that reads as
  a clean success. The message leads with what stands, such as the filed
  issue. Where a write the act requires was not made, and another later step
  that takes a code of its own failed too, such as filing's link to a report,
  the message names each, and the command takes the code saying the act was
  made and a later step failed, never one that names only the other. Each of
  the capability's callers that acts on such a code, a loop that files many
  issues among them, reads it as the act made. Where only later steps off the
  board failed, the command takes the code it gives them, which this record
  does not set.

These are limits on every command, as ADR-053 point 2's and ADR-074 point 5's
are. They name no code. Within them, each command's choice stays its own, and
its codes with it (DEC-020), recorded with the command's discipline, as a seat's
choice is (DEC-051 point 6). Where a record fixes a code they forbid, this
record narrows that record in place, as it does DEC-048 point 4 for a link that
fails beside a write filing requires.

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
  issue off the board. That severity lets the issue through, so the check exits
  as it does (point 4). A fault of the check's credential is none of the
  issue's, so it never takes the reject DEC-019 gives an issue off the board at
  filing, nor the broken tool's code.
- **The flag's, not carriage's.** Membership applies where a board is
  configured, and never routes through carriage (ADR-053, Boundaries). A project
  with no board makes no call for it.

### 6. Every read of the board goes through the seam, and a scan holds it

- **The seam owns every read of the board** (ADR-053 point 1). A read made
  outside it decides for itself what counts as the board's answer, which is how
  a stored id comes to stand in for one. So each goes through the seam.
- **The seam builds a filtered read into one request with the board's own read
  and the reads a witness needs,** so no caller can pair it with a stored id or
  an earlier answer, and point 1 holds by construction rather than by each
  caller remembering it.
- **The seam says which it is:** the board answered, with what it said, or the
  board did not answer, with why. The cause is the service's words verbatim, an
  answer naming no board or another, a read not whole, or an absence with no
  witness, with the service's words for the page where it failed. Each message
  names the way out its cause gives: a credential the board answers, the
  configuration's names put right, or a later try. For an absence with no
  witness, it says that no issue the read saw shows a card on the board, and
  names the way out of each cause it can be: the issue added to the board
  where it is off it, or a credential whose reads see the board where it is on
  it.
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
  not answer for, or whose write was not made, nor whether a move refuses for
  it. The cascade is what a move sets off on other issues (point 4). That
  stays with a project-management record not yet written, which ADR-074's
  Boundaries leave it to, and the limits hold there: no ancestor moves on a
  position the cascade could not read, and the move, once made, takes no code
  that reads as not made.
- **Not one home for the add.** ADR-031 point 3 keeps the add out of the
  constructor for field values, and point 3 here binds every place an add is
  made.
- **Not the override at filing.** DEC-019 lets one filing name a board other
  than the configured one, and that board stands in for the configured one in
  the filing's own reads and writes (the terms): its read first asks that
  board, and its add and first Status go to it. Every other command reads the
  configured board, so an issue added only to another has no card there.
  Whether a filing may name another board where the map binds the state to the
  board is the capability's to decide.
- **Not the health check's gate.** DEC-017 sets what its failure stops, and
  [project-kit#3193](https://github.com/aleskalfas/project-kit/issues/3193)
  proposes that it warn where the board does not answer. This record says what
  counts as the board's answer to it, and adds a warning beside it that fails
  nothing.

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

**Why the witness is sought among the repository's issues, in two orders the
seam sets.** The board's own cards come in the board's order, which no command
chooses. A board whose first cards are drafts or pull requests, or an
organisation's board whose first cards are withheld from a credential that
reads one repository, would give no witness among them. Every issue truly off
such a board would then read as unanswered, and DEC-019's drift would go
unfound there. The credential reads the repository of the issue it checks, so
none of that repository's cards is withheld from it, and the premise the
witness rests on is about one repository.

That repository's issues come in orders the seam asks for, each covering where
the other fails. The most recently created, of every state, are the issues
filed since the board, which filing adds to it, finished ones included, since a
closed issue keeps its card (ADR-074's Rationale). Automation that touches old
issues, such as a bot marking stale ones or a migration relabelling them,
moves when an issue was updated, never when it was created, so it cannot bury
them. The open issues most recently updated are the work in flight, which
finds the cards of a board adopted for work already under way, where few
issues were filed since. Both halves ride in the request the command makes
anyway, so the second order costs no call.

The page is a fixed size, whatever the board or the repository holds, so it is
no bound of the kind ADR-074 rejects for a walk of the board: past a walk's
bound, cards go unread, while past the page lies only a witness not found. It
holds no more issues than one batch of a listing read, a hundred (ADR-074's
alternatives), and no more than ten cards of each, which covers an issue on ten
boards. So its weight is fixed for each repository a request reads, and grows
with neither the board nor any repository's issues. How many it takes in each
order is a tuning within that ceiling, left to the seam and to measurement.

A read made in several requests, such as a listing in batches, would otherwise
fail whole on one request whose issues and page show no card, while another of
its requests showed the board answered: a batch of a repository's newest
issues, all off the board, among older ones on it. That is the size past which
choosing work takes nothing on each run, which ADR-074's Rationale rejects. So
an issue one request found carded is read again in the others: from the start
in each request after it, and in each request before it that lacked a
witness, made again once after the read's last request. It witnesses there
only where its card shows again, since only what the request shows is in the
request. A request then lacks a witness where nothing it reads for the
repository, its own issues, its page or the issue carried into it, shows a
card, and such a request fails the read, as any batch that cannot judge its
absences does. Made again once, at the end, a request costs one call more however many
repositories it lacks a witness for.

What is left is a board on which no issue the read sees shows a card: an empty
board, a repository's first issues on a shared board, or a repository none of
whose recent issues, by either order, nor any issue the read lists, is on it.
It reads as unanswered, at the drift severity where the membership check reads
it, and its message names both causes it can be and their ways out.

**Why an empty board is no answer either.** With the witness drawn from the
repository, an empty board is one case of no issue the read sees showing a
card. It is reported unanswered at the drift severity, with adding the issue
as one way out, so taking it as the board's answer would change only the
label. And where a credential gets the board named with none of its cards, a
case unmeasured for the very credential that prompted this record, an empty
answer would take a board that did not answer for one that answered empty.

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
mis-attribution ADR-074 point 2 refuses. The page a witness is sought in is no
read the command needs: an issue it acts on that also lies on the page is
judged from the command's own read of it. An error there takes away a witness,
while a fault of the board itself shows in the command's own reads. So the
page's paths are placed first, and an error on a page issue's cards is the
page's, never the board's. An issue carried in from another request is read
for the same sign and nothing else, so its paths are placed with the page's:
an issue the command never asked about cannot fail its read. Where the page
so fails and no other witness is
found, the issue reads as a board that did not answer, with the page's words.
That is not the mis-attribution ADR-074 point 2 refuses, a failed read of the
issue named as the board's: the cause it names is the page's read, and its
message names the way out of each cause the absence can be.

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
read only reported must not report what it did not see. A check that lets
through what it gates, an issue or an operation, stops nothing on its read, so
a board that did not answer there is a report at that severity, and takes that
severity's code. A check that stops what it gates on it stops for the tool, so
it takes the broken tool's code: a finding's would send the person to repair
an issue. Any other read only
reported, such as a value a command shows, lets nothing through at a severity,
so it keeps the broken tool's code, where a clean one would read as the value
seen. A note after the act is part of an act made. A write after the act
cannot be the act not made. An act of many writes, failing part way, is an act
made in part, so neither the code of an act not made nor a clean one fits it,
and a write that rests on one not made would act on what never happened.

**Why a command whose act needs a later write to the board reads first.**
Once the act is made, a write it requires that fails leaves the act standing
without it, a repair the command then owes, and undoing the act is a
destructive write. A read before the act finds a board that does not answer,
or one whose answer lacks what the write names, while nothing is made yet.
Where the write makes a read anyway, that read moves before the act, adding no
read of the board. So each such command meets a board that did not answer
before its act, by its own read, and none leaves such a write unmade for want
of a gate before it.

Filing is such a command in every project with a board: an issue owes its card
from filing, and DEC-019 rejects at filing an issue with none. Where the board
holds the state, the first Status is such a write too, and an issue filed
without it has no position, which every command that reads a position refuses
or skips. So filing refuses first: it files no issue DEC-019 rejects, save one
that names another board, as DEC-019's own override lets it (Boundaries), and
leaves no partial state. The price is this record's own choice, not DEC-017's:
an outage of the service's boards, or a credential the board does not answer,
is a filing outage in every project with a board, through the skill or not, and
an issue whose state lives on labels, workable without its card until a later
add, goes unfiled. ADR-053's reason against a fused call, that it would make a
board outage a filing outage on paths that never touch a board, does not reach
it: filing in a project with a board touches the board.

Where filing writes a first Status, as it does unless the map leaves the state
out, the read first is the read of the Status field that write makes, made
before the issue is created, so it adds no read of the board. Where the map
leaves the state out, it reads the board itself, one call more on each filing.
It asks no witness, since a board holding none of the repository's issues has
none to give before the repository's first filing. A board that answered with
no single-select Status field, or with one that has no option for the state
the issue is filed into, answered, yet lacks what the first Status names.
Where the board holds the state, filing refuses there before it acts: ADR-074
point 1 counts a board with no such field as one that cannot be read for the
state, and with no such option the first Status cannot be written. Where the
Status only mirrors the state, filing goes on, and the Status not written is
one line (point 4). The add's own answer then shows the card made (point 3). A
credential that reads the board and may not change it passes this read, and
its add not made is a later step failed (point 4). A credential whose filtered
reads alone miss the board passes it too, and later reads report the board
unanswered, never an issue off it.

**Why what an act sets off on another issue stays outside the write classes,
within the limits.** The forward cascade moves the ancestors of an issue whose
move is the act, so that a container is never behind the work under it
(DEC-006). Its writes land on other issues, the move needs none of them to
stand, and running the move again finishes a cascade cut short. Taken as
writes the act requires, they would make a move refuse for an ancestor's card,
a question ADR-074's Boundaries leave to a project-management record. And a
cascade cut short after a move made would take a code that the commands
composing the move read as the issue not moved, so they would report a move
that stands as unmade. So the cascade stays outside the write classes and the
read first, and whether a move waits on an ancestor is left open. The limits
hold there, and once the move is made, its code says so.

**Why a change that cannot be undone is the act, and a Done a close makes a
mirror.** A code that reads as the act not made invites the act again, and
where the change cannot be undone, it also misreports what stands for good.
Landing work merges and then moves its issue to Done, and the merge cannot be
undone (DEC-026). Taken as preparation for the move, as a branch is, the merge
would read as not made wherever the move after it failed. So a change that
cannot be undone is the act, and what follows it a later step. A branch or a
pull request made before a move can be undone, and a code saying the move was
not made is true of it, so it stays preparation. The Done of an issue that is
closed, or that the command or its act closes, is no write the act requires: a
closed issue is done whatever its card says (DEC-062 point 5), so its Done
mirrors the close. A merge closes its issue with no board in the loop, and no
board read stands between a merge and the closure cascade (DEC-062's
Rationale). So this record adds no read of the board before a merge for its
Done, and a board that did not answer after it is one line, never a code that
reads as the merge not made.

**Why an act made keeps a code apart.** A clean success hides that a step the
act requires is missing. A code that reads as the act not made invites a caller
to make it again, filing a second issue. DEC-024 keeps a hook's failure out of
the exit, so that a step an adopter chose to add cannot make every filing fail
from an agent's view and discourage hooks. The card, and a value whose source
is the board that the command writes itself, are no such step: DEC-019 requires
the card from filing, and DEC-024's first hook fires only once the issue is
filed and added. A value only a hook writes, such as priority or workstream
bound to the board, stays the hook's, with its clean exit. A code of its own
tells the agent that the issue exists and what it owes, as DEC-048 point 4's
does for a link not made. Taking that code would change the one meaning DEC-048
gives it. Where the add and the link both fail, a code that names one sends the
caller to repair only that one, so filing names both and takes the code for a
later step failed. Where the link fails beside a step that takes no code of its
own, such as a hook or a Status that only mirrors, DEC-048's code still names
every failure that takes one, so it stands: a project with no board, or whose
board took each write filing requires, keeps exit 4 as DEC-048 gives it. A
caller that knows only the earlier codes reads the new one as a failure, which
is why the message leads with the filed issue and the capability's own callers
read the code as filed.

**Why the health check reads the board.** DEC-017's check exists so that an
operation stops before it starts in an environment it cannot finish in, rather
than halfway through a mutation, and it rules out a check that reports a pass
it never computed. A stored id was written under some credential at some time,
and says nothing of this one, so a pass on it reports an environment the check
never looked at. So the check reads the board, as point 1 tells it. Carrying
the page beside that read, it also sees, at no extra call, a credential that
gets the board while its filtered reads find no card of the repository's. It
cannot tell that from recent issues all off the board, or none yet, so it
warns, naming both, and fails on neither. The page keeps the check to the
environment, as DEC-019 and DEC-020 have it: it is a fixed sample, read for the
credential's reach, and the warning names no issue, so the check scans no
issue's state.

What the check's failure stops is DEC-017's gate: every operation the skill
runs, those that touch no board among them, migrate, and a CI job that gates
on the check. That cost, and the live call each run of the check makes, follow
from DEC-017's gate meeting a check that reads the board, as DEC-017's check
asks. Under this record, every command meets a board that did not answer at
its own reads, in the posture point 4 gives each, and a command whose act
needs a later write to the board meets it before it acts. So without the
gate's stop, no command leaves a board write its act requires unmade for a
board that did not answer. The stop keeps two things from happening even so:
an operation of several commands running its first before a later one
refuses on the board, and a board write no act requires going unmade, such as
a Status that only mirrors the state, which point 4 reports with its repair.
Whether the check fails or only warns there is DEC-017's to decide, a record of
the capability's own, and
[project-kit#3193](https://github.com/aleskalfas/project-kit/issues/3193)
proposes that it warn. This record holds either way.

ADR-053 refuses a call that fuses where an axis lives with the board's read,
since a board outage would then become a filing outage on paths that never
touch a board. This record fuses nothing: carriage reads no board, and no
command that touches no board reads one. The stop such paths meet is DEC-017's
gate, which stops each operation on a gap in the environment before any
command reads. Through it, an outage of the service's boards stops each
operation the skill runs in a project with a board, with migrate and a CI job
that gates on the check, the harm ADR-053 names, reached through another
layer, and the Summary's weigh list names it.

**Why membership comes under the contract.** The membership check's one read is
a filtered read that names no board. Under a credential the board does not
answer, it reports every issue off the board, and where the post-check workflow
runs under such a credential, it says so on every issue it checks. ADR-053 kept
the check apart because it judged from a payload already fetched. That payload
is the read that cannot tell nothing from nothing visible. Read as every card
is, membership has one account of an issue's card, as a state has (ADR-074 point
6), at one request in a project with a board and none without.

**Why a board that did not answer is reported at the drift severity, and exits
as it.** It is a fault of the check's credential, not of the issue. The reject
DEC-019 gives an issue off the board at filing judges the issue, and giving it
to a fault of the credential would fail every issue the check sees, for
something no issue can repair. The broken tool's code would do the same
wherever the check runs as a status check, as the post-check workflow does,
which fails on any code but a clean one. ADR-053 keeps a membership that cannot
be determined at DEC-019's drift severity, and this record keeps that, with
the code that severity takes. It loses no stop the check makes on an existing
issue, whose drift DEC-019 lets through, and the report says what the check
could not see. A gate's verdict on a value the map binds to the board is
another matter: its finding would stop the issue, so it keeps ADR-053 point
2's raise, and under a credential the board does not answer, the post-check
workflow fails each issue such a gate checks. That is a stop for the tool,
which a credential the board answers repairs, never a finding about the issue.

**Why these limits sit in this record.** They bind every command that reads or
writes the board, as ADR-053 point 2's raise and ADR-074 point 5's limits do,
and say what no command may choose. Set in each command's own record, they would
be one account for each command of what a board that did not answer means: the
drift the seam exists to end. Each command's choice within them stays with the
capability, as DEC-051 point 6 records a seat's. They name no exit code: each
command's codes are its contract with its callers, the capability's to set
(DEC-020). They say only what any code may claim about a board that did not
answer or a write not made, as ADR-053 point 2's sentence on the broken tool's
code already does. Where a capability's record fixes a code they forbid, as
DEC-048 point 4 does where filing's link fails beside its card, this record
narrows that record in place, and the code itself stays the capability's. They
bind only where a read or write of the board failed: a later step off the
board, failing alone, keeps the code its command gives it, which is not this
record's subject. An adopter meets them in each command's message, which names
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
  board's order, which no command chooses, so a board led by drafts or pull
  requests, or by cards withheld from the credential, gives none, and each
  issue off such a board reads as unanswered.
- **Seek the witness through the board's own read, filtered to the repository**
  by the search its card list takes. The case: no order to choose, and a card
  it finds that its issue's own cards do not list would show, in the same
  request, that the credential's filtered reads miss the board, a cause the
  page cannot tell apart. The health check's warning could then tell it too.
  Rejected: the card list takes a search, but how it treats a filter on the
  repository is unmeasured, and a host whose service lacks the argument would
  refuse the whole request. The page asks only for states and orders, whose
  meanings the service's schema fixes.
- **Take a page of the repository's issues in the service's own order.**
  Rejected: that order is unstated, and where it runs oldest first, a
  repository whose first issues predate its board gives no witness, so each
  issue truly off the board reads as unanswered.
- **Take the page in one order only,** the open issues most recently updated,
  or the issues most recently created. The case: one order to state and test.
  Rejected: when an issue was updated moves whenever automation touches it, so
  a bot marking stale issues, or a relabelling migration, can fill the first
  order with old issues off the board. When it was created misses a board
  adopted for work already in flight, where few issues were filed since. Each
  order covers the other's failure, in the same request, at no call.
- **Take a page of the largest size the service allows.** The case: more
  issues to find a witness among. Rejected: the two orders cover different
  failures, which no size of one covers, and a larger page weighs more in
  every request that carries it, and with it the chance of the whole request
  failing.
- **Store which issue witnessed last, and test it in the next request.** The
  case: no order to choose. Rejected: it is a state each project's commands
  must write and keep, which the first run lacks, and the page finds a witness
  without it.
- **Take each request's witness alone,** in a read made in several requests.
  The case: no request made again. Rejected: a batch of a repository's newest
  issues, all off the board, would fail a whole listing whose other batches
  showed the board answered (ADR-074 point 6), so a seat would take nothing on
  each run.
- **Count a witness another request of the same read found, without reading it
  again.** The case: no issue added to a request. Rejected: two requests share
  a credential and a host only where whatever makes them makes them alike, the
  pairing within a run this record rejects. Read again, the witness is in the
  request.
- **Make each earlier request again as soon as a later one finds a witness.**
  The case: an answer sooner. Rejected: a request lacking witnesses for two
  repositories, found in different later requests, would be made again for
  each. Made once after the read's last request, it carries every witness
  found, at one call more.
- **Carry the page only in a read's first request for each repository, and
  from then on only the issue it found carded.** The case: each later request
  weighs one issue for its witness rather than up to a hundred. Rejected: a
  request whose carried issue does not show its card again would have no page to
  fall back on, and would need a request more to read one, while the page's
  weight is already fixed, no more than a listing's own batch.
- **Take a whole read of the board's cards that holds none as its answer.** The
  case: an issue off a board before its first card reads as off it. Rejected:
  the witness reports that case unanswered at the drift severity, with adding
  the issue as a way out, so the rule would change only the label. And where a
  credential gets the board named with none of its cards, it would take a board
  that did not answer for one that answered empty.
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
- **Let the health check warn where the board does not answer, or narrow its
  stop to the operations that read or write the board.** The case: an outage of
  the boards, or a credential the board does not answer, would stop no
  operation that touches no board, migrate, or a CI job, while every command
  meets a board that did not answer at its own reads, and one whose act needs
  a later write to the board meets it before it acts (point 4). ADR-031
  point 5 gates back-fill on the board in this way, only where a board field
  is to be written. Not decided here: what the check's failure stops is
  DEC-017's, and a change to it is a
  record of the capability's own, which
  [project-kit#3193](https://github.com/aleskalfas/project-kit/issues/3193)
  proposes. This record holds with it or without it.
- **Let the health check fail where the page shows no witness.** The case: the
  measured kind of token, one that may get the board and no witness, would
  stop at the check. Rejected: the check cannot tell that from a repository
  whose recent issues are all off the board, an empty board among them, so it
  would stop every operation of a project that has just set up its board.
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
  or reporting and going on everywhere. Rejected: refusing everywhere would make
  a check that only reports, such as the membership check, fail every issue it
  sees for a fault of the credential, and would stop a move whose state lives
  on labels for a Status that only mirrors it. Going on everywhere files issues
  whose state lives on a board no command can reach.
  DEC-017's gate is no such posture: it stops each operation on a gap in the
  environment, before any command reads, and stands.
- **Give a board that did not answer the broken tool's code in every check.**
  Rejected: a check whose own finding there would let the issue through loses
  no stop by reporting at that severity, while the broken tool's code would
  fail the issue for something no issue can repair. The post-check workflow
  fails on any code but a clean one, so under a credential the board does not
  answer, every issue it checks would fail. ADR-053 keeps a membership that
  cannot be determined at the drift severity. A gate whose finding would stop
  the issue keeps the raise.
- **Bind the broken tool's code only to the reads a command acts on.** Rejected:
  a check that stops the issue on a board that did not answer could then take a
  finding's code, and send the person to repair an issue, and a command that
  shows a value it could not read could exit clean.
- **Read first only where the board holds the state, or only where filing
  writes a first Status.** The case: no call added where the map leaves the
  state out, and where labels carry the state, an outage of the boards is no
  filing outage: the issue is workable without its card, which a later add
  repairs. Rejected: in every project with a board, DEC-019 rejects at filing
  an issue with no card, so filing it would file what that rule rejects, owing
  a repair, and undoing it is a destructive write. Reading first costs a call
  only where the map leaves the state out.
- **Read first only at filing.** The case: the rule reaches only the command
  known to need it. Rejected: another command whose act needs a later write to
  the board would then act on a board none of its reads asked, and only the
  health check's stop would keep that write from going unmade.
- **Bring what an act sets off on another issue under the read first and the
  write classes,** the forward cascade's moves of the issue's ancestors among
  them. The case: one rule for every write whose source is the board. Rejected:
  a move would refuse for an ancestor's card, which ADR-074's Boundaries leave
  to a project-management record, and a cascade cut short after a move made
  would take a code that the commands composing the move read as the issue
  not moved.
- **Take every change made before a move as preparation, a merge among them.**
  The case: one test for the act, what the success reports last. Rejected: a
  move that failed after a merge would read as the work not landed, though the
  merge cannot be undone (DEC-026).
- **Take the Done landing work writes as a write its merge requires,** reading
  the board before the merge. The case: a Done never left unwritten. Rejected:
  the merge closes the issue, which is then done whatever its card says, and a
  merge closes its issue with no board in the loop (DEC-062 point 5 and its
  Rationale), so the read would refuse a merge for a mirror.
- **Give the code for a later step failed wherever two later steps failed,**
  the link among them. The case: one rule, whatever failed. Rejected: it would
  take DEC-048's code from a link that fails beside a hook or a mirrored
  Status, in a project with no board among them, where no write the board owes
  went unmade and this record has nothing to say.
- **File, then report a first Status that cannot be written,** where the board
  holds the state and its answer lacks the Status field or the state's option.
  Rejected: the issue would stand with no position, which the read first
  showed before the act.
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
  rest once measured. Rejected: where one of the first three premises fails,
  its case is left as it stands without this record and never made worse, so
  holding back what rests on one gains nothing. The fourth, the host's, every
  whole read rests on, split or not, since ADR-074 point 6's account of an
  issue's card asks for archived cards.

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

  - **Refined in place,** each with the pointer "(refinement per ADR-096)" on
    the sentence it rewrites or adds, reading "(refinement per ADR-074 and
    ADR-096)" where the sentence carries ADR-074's, and each changing what
    ADR-053 decides. They reach reads only:
    - **the Summary's first paragraph, its last sentence:** "Every command that
      reads the board holds to the same ruling, gate or not", in place of
      "Every command that reads a board-carried state holds to the same ruling,
      gate or not", followed by "A read that lists only what the credential may
      see, and shows no card of the issue on the configured board, is the
      board's answer only where the same request shows the board answered, and
      a read that is not whole is no answer.";
    - **the Summary's second paragraph:** "**what a failure means** (the
      caller's decision, within limits every caller keeps)", in place of
      "**what a failure means** (the caller's decision)";
    - **point 1, its Layer 2:** "it returns a result object saying whether the
      board answered, as ADR-096 points 1 and 2 tell it, and what it said or
      why it did not, with `gh`'s stderr verbatim when `gh` failed", in place
      of "it returns a result object saying whether the board answered and
      what it said, with `gh`'s stderr verbatim on failure";
    - **point 2's first paragraph,** a sentence added: "A read that is not
      whole, or that lists only what the credential may see and shows no card
      of the issue on the configured board without the witness ADR-096 point 1
      requires, is a read that did not succeed.";
    - **point 2's reach paragraph,** rewritten whole: "**That a board which
      will not answer is a broken tool, never a missing value, reaches every
      command that reads the board, gate or not.** The raise stays a gate's,
      within point 3's scope. What an outcome means to such a command is its
      own to decide, within the limits ADR-096 point 4 sets; a seat choosing
      work, for one, takes nothing. But it reports a board that will not answer
      as that, with what the board said, and never as a finding about the
      issue, nor a finding as a broken board. Where its exit codes tell a
      broken tool from a refusal, a board that will not answer takes the broken
      tool's code, but in two cases: once the command's act (ADR-096's terms)
      is made, whole or in part, it takes the code that says so, and a check
      that reports it at a severity that lets through what the check gates, an
      issue or an operation, exits as that severity does.";
    - **point 5, the seam's shape:** "whether the board answered, what it said
      or why it did not, and `gh`'s stderr verbatim when `gh` failed", in place
      of "whether the board answered, what it said, and `gh`'s stderr verbatim
      when it did not";
    - **its Implications' bullet on the field-value read:** "carrying why the
      board did not answer on the latter, with `gh`'s stderr verbatim when `gh`
      failed", in place of "carrying `gh`'s stderr verbatim on the latter".
  - **Standing as written,** checked to agree:
    - **point 3, the Summary's scope of the raise, and its one-line contract:**
      the raise stays where carriage said `board`. Point 4 here adds no raise
      outside it. Its other stops are a command's own, or a check's, made only
      in a project with a board, on a read the command makes of the board;
    - **the rejected "Raise on any board read failure anywhere":** for the same
      reason, no project acquires a failure from a feature it does not use;
    - **the Summary's reason that a fused call would make a board outage a
      filing outage on paths that never touch a board:** this record fuses
      nothing, and carriage reads no board. Filing in a project with a board
      touches the board, adding its card, so its refusal there is on no such
      path. The stop an outage brings such paths through DEC-017's gate is that
      gate's, and the weigh list above names it;
    - **the Rationale's "a warning that passes is the same failure with better
      prose":** it argues a gate's verdict, which point 4 here keeps as the
      raise. A check that lets the issue through reports a board that did not
      answer at its severity, as the Boundaries' membership bullet, standing in
      that part, has it;
    - **the other sentences on `gh`'s stderr:** the Context's account of the
      surfaces "as they stand", which describes the code as it stood; point
      2's remedy that `gh` prints in the stderr the seam carries; the
      Rationale's raise that arrives with `gh`'s stderr as its remedy; and the
      Implications' gate failure path, whose message carries the seam's verbatim
      error. Each speaks of words the seam carries verbatim, `gh`'s where `gh`
      failed, and a cause with no such words is carried as the refined Layer 2
      says, with the way out point 6 here names;
    - **the Boundaries' "Not a change to the label read path or the substrate
      write path":** the edits reach reads only, and point 3 here decides writes
      itself, keeping ADR-031's neutrality;
    - **its Implications' "DEC-019's membership requirement is untouched":**
      this record changes how membership is read, not what it requires.
- **ADR-074 is refined in place,** each edit with the pointer on the sentence it
  rewrites or adds, and each changing what it decides:
  - **its Summary's third bullet:** "the command decides what a failed or empty
    read means to it, within limits every command keeps", in place of "the
    command decides what a failed or empty read means to it";
  - **its Summary's sentence on cards:** "A command reads the cards of the
    issues it acts on, and others only to find a sign that the board answered,
    and never takes part of a listing for the whole.", in place of "A command
    reads the cards of the issues it acts on and no others, and never takes
    part of a listing for the whole.";
  - **its Decision's opening, its last sentence:** "A command reads the cards
    of the issues it acts on, and others only to find a sign that the board
    answered.", in place of "A command reads only the cards of the issues it
    acts on.";
  - **point 5, its second limit, from its sentence on the broken tool's code:**
    "Where a command's exit codes tell a broken tool from a refusal, a board
    that will not answer takes the broken tool's code, but in two cases: once
    the command's act (ADR-096's terms) is made, whole or in part, it takes the
    code that says so, and a check that reports it at a severity that lets
    through what the check gates, an issue or an operation, exits as that
    severity does. ADR-053 point 2 rules this for every command that reads
    the board, gate or not, a reach this record gives it for the state's
    readers, on the same ground, and ADR-096 for the rest.", in place of
    "Where a command's exit
    codes tell a broken tool from a refusal, an unreadable board takes the
    broken tool's code. ADR-053 point 2 rules this for a gate; this record
    rules it for every command that reads the state, on the same ground. This
    refines ADR-053 point 2, its reach.";
  - **point 5, its second paragraph:** "Each other command chooses its own
    within the limits, and within those ADR-096 point 4 sets for every read and
    write of the board", in place of "Each other command chooses its own within
    the limits";
  - **point 6, its title:** "A command reads the cards of the issues it acts on,
    and others only to find a sign that the board answered", in place of "A
    command reads the cards of the issues it acts on, and no others";
  - **point 6, a paragraph added** after the one that gives one account of an
    issue's card: "Beside them, a request that could find an issue with no card
    carries, for each repository whose issues it reads, a fixed page of that
    repository's issues, the most recently created and the open ones most
    recently updated, whose cards the seam reads only to find a sign that the
    board answered (ADR-096 point 1). An issue the command acts on that also
    lies on that page is judged from the command's own read of it. A listing
    read in several batches carries an issue whose card one batch found into
    each batch after it, and into each batch before it that found no such
    sign, made again once after the last. The issue is a sign there only
    where that batch's request shows its card again. No error placed on the
    page, or on an issue so carried, fails the command's read.";
  - **its Rationale's "Why a listing reads the listed issues' cards":** "A
    listing is bounded by what the command lists, and by a fixed page for each
    repository each of its requests reads, which grows with neither the board
    nor any repository's issues.", in place of "A listing is bounded by what
    the command lists.";
  - **its Implications' bullet on a Status write, its last sentence:** "Filing
    handles a failed Status write as ADR-096 point 4 sets for a write after the
    issue is created: the issue stays filed", in place of "Filing handles a
    failed Status write as it handles every other write after the issue is
    created: the issue stays filed".

  Standing as written, checked to agree:
  - **point 5's two limits' leading words,** which speak of a state, since
    point 4 here holds them for every read and write itself;
  - **point 2's "The state's reader asks only the board",** and its Rationale's
    reason: the reader reads no issue of its own. The page is the seam's, read
    beside the issue's cards in the board's request, and an error placed on it
    takes away a witness, never fails the issue's read, and never makes that
    read the board's;
  - **point 6's two bounds,** a cascade's reads "bounded by the hierarchy's
    depth" and a listing's "bounded by what it lists, not by the board": the
    page rides in each request, and grows with neither the board nor the
    repository, and a request made again to carry a witness is one of the
    listing's own batches, so what the reads grow with stands;
  - **point 6's whole-or-nothing,** since the page is no batch of a listing,
    and a batch whose request, carrying a witness from another, shows none
    fails the whole listing as any failed batch does;
  - **the rejected "Read every card on the board once",** since the page reads
    issues' own cards, a fixed page whatever the board holds.
- **DEC-048 is refined in place,** changing what it decides, with the pointer
  "(refinement per [pkit:ADR-096])" on the sentence it adds:
  - **point 4, a sentence added after its sentence on the exit code:** "Where
    a write to the board that the filing requires failed too, such as the add
    of its card, filing names each failure and exits with the code it takes
    for that write, not exit 4 (refinement per [pkit:ADR-096])."

  Standing as written, checked to agree: point 4's title, warn loudly and never
  roll back; its sentence on the exit code, whose exit 4 stands wherever no
  write the filing requires failed, a hook, a mirrored Status or the native
  link failing beside the link or not; the Rationale's warn-don't-rollback; and
  the Implications' "exit code 4 = created-but-unlinked", the one meaning that
  code keeps.
- **ADR-031 has a fact corrected,** its decision standing, so the edit takes
  no pointer. The add is made wherever an issue is added to a board, and point
  3 here binds each place:
  - **point 3, its sentence on membership:** "The two covered substrates are
    field-value and milestone (the attribute writes); board-membership is a
    distinct operation, made outside the field-value constructor wherever an
    issue is added to a board, and neither subsumed by nor in tension with that
    constructor.", in place of "The two covered substrates are field-value and
    milestone (the attribute writes); board-membership is a distinct operation
    with its own single site, neither subsumed by nor in tension with the
    field-value constructor it sits near in `create-issue.py`.";
  - **point 3, its paragraph on the guard:** "(membership — out of scope)", in
    place of "(membership — out of scope, its own site)".

  Standing as written, checked to agree: its Context's enumeration of the
  sites, whose "(single) site" for the add that enumeration gives as of its
  authoring, as it says of itself; point 3 keeps the add out of the
  constructor, and point 3 here says what counts as an add made; point 5's
  back-fill gate keeps its member that the board resolves, read as point 1
  here tells it; and point 6's neutrality holds.
- **How the edits are sorted.** The decisions README edits a record in place
  where its decision stands, narrowed, widened or completed, and supersedes it,
  in whole or in part, where another record decides otherwise ("Refining an
  accepted record", its opening). Its one test then asks of each edit made in
  place whether it changes what the record decides. Each edit here does, save
  ADR-031's, and each that does is a person's.
  - **Overturned:** ADR-053 weighed the membership check against the value
    read, and kept them apart ("Both stand; neither is the model for the
    other"). This record takes the other side of that choice, so that bullet
    is overturned.
  - **Narrowed and completed:** ADR-053 point 2 and ADR-074 point 5 chose that
    a board which will not answer is a broken tool, never a missing value or a
    finding, and never takes a refusal's code. This record keeps that choice.
    It narrows where the broken tool's code itself is taken, in two cases:
    once the act is made, whole or in part, the code that says so, and in a
    check that lets through what it gates, that severity's code, as ADR-053's
    Boundaries have it for membership. Neither is a refusal's code. The second
    is the code the check's own findings at that severity take, which may be
    the code a clean run takes, while its report never says the check passed.
    Elsewhere the broken tool's code stands, for a value a command shows among
    the rest. So those sentences are refined, and ADR-074 takes no superseded
    line.
  - **Narrowed:** ADR-053 and ADR-074 leave to each command what an outcome
    means to it. This record keeps that choice, and holds each command's
    within point 4's limits: ADR-053's Summary on what a failure means and its
    point 2's reach paragraph, and ADR-074's Summary third bullet and point 5's
    second paragraph. ADR-074's Implications on a failed Status write at filing
    narrow with them, to point 4's code where the board holds the state.
    DEC-048 point 4 chose to warn, never roll back, and give an issue filed and
    not linked a code of its own. This record keeps that choice, and that code
    wherever the link fails, save where a write to the board that the filing
    requires failed too, where filing takes its code for that write. Each
    command decides within the limits, so each choice stands.
  - **Widened:** ADR-074 point 6 chose the issues' own cards over a walk of
    the board, so that a listing's reads are bounded by what it lists, not by
    the board. The page a witness is sought in reads issues' own cards too, a
    fixed page whatever the board holds, and the command judges no issue from
    it. A batch made again to carry a witness is one of the listing's own. So
    "and no others" is widened, and the choice stands.
  - **The rest** widen a reach or complete a definition: ADR-053's Summary on
    every command that reads the board, its Layer 2, the sentence added to its
    point 2, its point 5's seam shape and its Implications' field-value read.
    Each choice ADR-053 and ADR-074 made among their alternatives stands.
  - **A fact corrected:** ADR-031 point 3's single site described the add as
    filing made it. The choice that membership stays out of the constructor
    stands, so the sentence is corrected, as a fact is.
- **Accepting this record signs off each edit above**
  ([COR-064](../../../.pkit/decisions/core/COR-064-answer-delegate.md) point 6;
  [COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md)
  point 5).
- **Standing unedited:**
  - **DEC-017:** its board check is a live read of the declared board, and its
    gate refuses on the check's failure, in the skill, in migrate and in a CI
    job that gates on it. Its list of checks names the tool its first version
    used for each. The board check keeps what it asks, that the declared board
    resolves, read through the seam as point 6 has every read. This record says
    what counts as the board's answer to it, and adds a warning beside it, where
    the page shows no witness, which fails nothing. Whether the check fails or
    warns where the board does not answer stays DEC-017's, and
    [project-kit#3193](https://github.com/aleskalfas/project-kit/issues/3193)
    proposes that it warn.
  - **DEC-036 point 3:** the check degrades where an axis's substrate is
    unsupported, and a declared board that does not resolve is no such axis.
  - **DEC-019:** an issue off the board keeps its severities. The override at
    filing stays its own, its board standing in for the configured one in that
    filing's own reads and writes (the terms). The health check stays
    environment health, no per-issue scan: the page is a fixed sample, read for
    the credential's reach, and its warning names no issue.
  - **DEC-020:** each command's exit codes stay its contract, and the health
    check no per-issue scan, as for DEC-019.
  - **DEC-024:** a hook keeps its clean exit.
  - **DEC-026:** a merge is never rolled back on a later failure, and, since
    it cannot be undone, is landing work's act (the terms).
  - **DEC-006 and DEC-062 point 5:** the forward cascade, what a move sets off
    on other issues, stays outside point 4's write classes and within its
    limits, and the Done of an issue that is closed, or that the command or
    its act closes, mirrors that close, so this record adds no read of the
    board before a merge (DEC-062's Rationale).
  - **DEC-051 point 6:** it follows ADR-053, so its outcome that an issue has no
    card takes point 1's account here, and each command's choice its limits,
    through ADR-053's refined Layer 2 and point 2.
- **Tests hold each case:**
  - **a board that does not answer,** where its own read fails, names no board
    or another, or where a stored node names a board other than the
    configured number under the resolved owner: the membership check
    reports the board unanswered and exits as the drift severity does, filing
    in a project with a board refuses before it creates the issue, a state
    read reports a board that cannot be read, and the health check reports it
    at DEC-017's severity, never as a pass, a stored id or not;
  - **filing's read first:** where filing writes a first Status, the read that
    answers is the one that Status is written from, with no read of the board
    added. Where the board holds the state and answers with no single-select
    Status field, or with no option for the state the issue is filed into,
    filing refuses before it creates the issue. Where the Status only mirrors,
    filing goes on, and reports the Status not written in one line. A filing
    that names another board reads that board first, by its number;
  - **a command whose act needs a later write to the board** reads the board
    before its act, and refuses there where the board does not answer;
  - **what an act sets off on another issue:** where the board does not answer
    for an ancestor the forward cascade reaches, or a write to it is not made,
    after the issue's move is made, the move stands, and the command takes no
    code that reads as the move not made;
  - **landing work:** where, after the merge, the board does not answer for the
    issue's Done, or its write is not made, the merge stands, the command says
    so in one line, and the Done takes no code of its own. Where a read or
    write of the board fails for another issue the merge closes, or for an
    ancestor, the command takes no code that reads as the merge not made. No
    read of the board is added before the merge for the Done;
  - **the health check's page:** where the board answers and the page shows no
    witness, the check warns, naming both causes, and does not fail;
  - **an absence with no witness,** where the board answers but no issue the
    read sees shows a card on it, an empty board among them: the board did not
    answer, and the message names both causes it can be;
  - **an absence with a witness,** among the issues the command reads or on the
    page the seam adds, an archived card among them: the membership check
    reports the drift;
  - **the page:** for each repository whose issues the request reads, it asks
    for the issues most recently created, of every state, and the open issues
    most recently updated, as many of each as the seam fixes, no more than a
    hundred in all, with no more than ten cards of each. A witness found in
    either order witnesses. An error placed on it, one on the repository's node
    or on a page issue's cards among them, or an issue on it whose cards run
    past those read, takes away a witness and fails nothing. An issue of a
    repository renamed or transferred is matched by the repository's node id;
  - **a read made in several requests:** where one request's issues and page
    show no card and a later request of the read finds one, the issue found is
    carried from the start into each request after it, and into the first,
    made again once after the read's last request, carrying an issue for each
    repository it lacks one for. It witnesses there where it shows its card
    again, and the absences are judged from the request made again alone.
    Where the carried issue does not show its card again, and none of that
    request's own issues or its page shows one, that request lacks a witness,
    and the read fails whole; where one of them does, it witnesses. A full
    batch, at the most issues one
    request may name, carries a witness within what one request may ask. An
    error on a carried issue takes away a witness, and fails nothing;
  - **a read not whole,** cut short at a page bound, asking only for cards that
    are not archived, or carrying an error on the board or its cards: the board
    did not answer. An error whose path points at an issue's cards, outside the
    page, is the board's, though it leaves the issue's node empty. An error on
    an issue's own node alone is that issue's read failing;
  - **a write not made after the act:** where filing's add, or its first Status
    where the board holds the state, fails, the issue stays filed and filing
    exits with its own code for a later step failed, apart from DEC-048's.
    Where the add and the link both fail, filing names both and takes that
    code. Where the link fails and each write filing requires was made, filing
    takes DEC-048's code, whether a hook, a mirrored Status or the native link
    failed beside it or not, in a project with no board too. Where the Status
    only mirrors, or a closed issue's Done is not written, the command gives
    one line, and exits as its act does;
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
  needs no migration: nothing an installed project holds is renamed or removed,
  a copy of the template being the project's own, and a stored board id stays
  where it is, read as a name. Each command whose act needs a later write to
  the board reads the board first (point 4), filing among them, and the tests
  hold each. Landing work, whose act is the merge, takes after it no code that
  reads as the merge not made where a read or write of the board fails, for
  its own issue or another the merge closes. The health check's advice for a
  board under another owner than the repository's names the owner in the
  configuration (DEC-023), rather than a stored node alone.
- **The post-check workflow's template gains a setting for a credential the
  board answers,** in the work, unset as it ships. Without it, the template
  runs under the workflow's own token, which by the service's documentation
  reaches no board. Under that token, the membership check reports the board
  unanswered on each issue the workflow checks, at the drift severity, and lets
  the issue through. Where the map binds an axis to the board, the presence
  gate's raise (ADR-053 point 2), once that gate reads the board, fails each
  issue the workflow checks. The way out of both is a credential the board
  answers, for which the template has no place, so the setting ships with the
  work rather than after it.
  - **What the setting exposes.** The job runs on each issue opened, edited or
    reopened, which anyone who can open an issue starts, and it runs tools it
    fetches at run time. A credential set there reaches whatever runs in a step
    that holds it, so only the steps that read or add on the board hold it.
    Those steps run the tools the job fetches, so the credential reaches those
    tools too: keeping it to those steps shields it from the job's other
    steps, and from nothing those steps run. For a person's board, the
    service's documentation names a person's token, long-lived and as broad as
    its scopes. For an organisation's board, it names an App, whose token
    expires within the hour, so the job mints one on each run from the App's
    key, the secret the project keeps instead. Which to set, if any, is the
    project's choice, made in its own copy.
  - **One owner.** The template's add addresses the board as point 1 has it,
    under the owner the capability resolves, and keeps no owner of its own: with
    two, a board with the same number under the other owner could answer the add
    with a card, and the add would count as made (point 3).
  - **Remediation.** A copy that remediates only on a finding that blocks adds
    no missing card, since the membership check's drift never blocks. Whether
    a copy should, on an issue off the board or on one the board did not answer
    for, is the capability's to decide (DEC-019). Where it does, the add's own
    answer settles whether it was made (point 3), and a card it makes is a
    witness for the repository's later reads.
  - **A copy made earlier.** A project's copy of the workflow is its own
    (DEC-019), so the setting reaches a copy made earlier only once the person
    copies the template again.
- **This change** carries this record and, on its acceptance, the edits to
  ADR-053, ADR-074, DEC-048 and ADR-031 above, and none of the work. The
  walks' reading of archived cards is project-kit#3191's.
