---
id: ADR-074
title: A board-carried state is read through the board read seam, and the command that reads it decides what each outcome means
status: accepted
date: 2026-10-29
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** where a project's substrate map puts the issue state on its
Projects v2 board, a command learns where an open issue stands by reading the
Status of the issue's card. This record says where that read sits. It keeps the
three layers that the board read-path contract
([ADR-053](ADR-053-board-read-path-contract.md)) sets for every board read:

- *where does the state live* is answered from the map alone, and cannot fail;
- the board read seam reads the Status and reports what happened;
- the command decides what a failed or empty read means to it.

The part of the engine that works out an issue's state stays pure: the Status is
one more input to it, read before it is called. A command reads the cards of the
issues it acts on and no others, and never takes part of a listing for the whole.

The board flag carries no axis
([project-management:DEC-062](../../../.pkit/capabilities/project-management/decisions/DEC-062-axes-chosen-in-the-map.md)),
and the state may live on the board
([project-management:DEC-051](../../../.pkit/capabilities/project-management/decisions/DEC-051-axis-carriage-activation.md)
point 6). In places, ADR-053 and the label read-path contract
([ADR-026](ADR-026-substrate-map-read-path-contract.md)) say otherwise, and this
record refines both: Context names the chief places, and Implications lists them
all.

## Context

DEC-062 lets a project choose, in its substrate map, where each axis lives. The
board flag says only that a board exists, and carries no axis (its point 1).
Where the map binds state to the board, the board's Status is the source of an
open issue's position, and a closed issue is Done whatever its card says (its
point 5).

DEC-051 point 6 says what a read of that Status yields. An issue whose card's
Status names one of the open states is **placed**. Beside that, the read has four
outcomes: the board cannot be read, the issue has no card, its card has no
Status, or its Status names no open state. In the last three the issue's position
is **undetermined**, a finding about the issue. The first is a fault of the
tool. Each outcome is reported apart, and none falls back to the issue's labels
or its Milestone. A seat choosing work skips, with a warning, a Task whose
position is undetermined, and takes nothing where the board cannot be read. How
the read finds the Status field and maps its options to states is left to this
record (DEC-051's Implications).

The chief passages of the read-path contracts that say otherwise, which the
Implications of DEC-051 and DEC-062 leave to the architect:

- ADR-053 point 6 admits the board arm on `priority` and `workstream` only, finds
  a field by the axis's own name, and keeps `state` out because reading a Status
  field "needs a detector kind that does not exist".
- ADR-053 point 2's edge has carriage key "on the board flag alone", and its
  ruling that an unreadable board raises speaks of a gate. A command that reads
  the state is not always a gate.
- ADR-026 point 4 reconciles the label read path with a switch between board and
  labels, driven by the flag at each site, beneath the adopter's binding. Its
  Boundaries place the carriage composition beside a flag that "governs carriage
  where the map is silent".

The architecturally significant pins, each against a plausible alternative:

1. **Which field holds the state:** a field found by the axis's own name, as for
   priority and workstream, or the board's built-in Status field.
2. **Where the Status read lives:** in the board read seam, in a reader of its
   own, or inside **the state inference**, the part of the lifecycle engine that
   works out where an issue stands from what has been read of it.
3. **How board carriage composes with the label read path:** as one of the map's
   bindings, which the label read seam reports like every other, or through a
   switch between board and labels kept beneath that seam.
4. **Whether the state inference reads the board:** the inference performs the
   read, or the command performs it and passes the result in.
5. **Who decides what each outcome of the read means:** the seam, the inference,
   or the command.
6. **How a command that needs many issues' states reads the board:** every card
   on the board once, the listed issues' cards in batches, or one read per issue.

## Decision

**In plain terms:** the state reads from the board's Status field, through the
same seam as every other board read. Where the state lives is answered from the
map alone. The command reads the Status, hands it to a pure inference, and
decides itself what each outcome means. A command reads only the cards of the
issues it acts on.

### 1. The state reads from the board's Status field

DEC-051 point 2 admits `board: true` on `state` together with this read, so the
arm is admissible on `priority`, `workstream` and `state`. `type` stays excluded,
for ADR-053's reason: PR-title alignment reads the type label, and a board field
is invisible from a pull request. Reading the Status needs no detector kind of
its own. The lifecycle's classifier, the one predicate by which the process
engine places an issue ([ADR-062](ADR-062-classified-detection.md) point 15),
passes the Status read to the state inference as one more input (point 4). This
refines ADR-053 point 6, its second bullet.

The arm stays parameterless. Priority and workstream find their field by the
axis's own name. State reads the board's **Status** field: the name Projects v2
gives its built-in single-select field, and the field the capability writes as
the state's projection where it keeps one
([project-management:DEC-006](../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)).
The field is no write parameter on a hook, since the commands that move an issue
write it. This refines ADR-053 point 6, its first bullet, for state.

A Status option maps to a state by the state's display name in the lifecycle's
workflow definition, matched exactly first, then case-insensitively. A write maps
a state to an option by the same rule, so an open state the capability writes
reads back as itself. Done is no open position: a closed issue is Done by its
native close, whatever its card says, and a card at Done places an open issue
nowhere.

A board with no field named Status, or whose Status is not single-select, answers
but can place no issue. It counts as a board that cannot be read, and the message
names the field: the remedy lies on the board, not on any issue.

### 2. The Status read goes through the board read seam

Reading a card's Status is a board read, so it goes through the board read seam,
which answers neutrally (ADR-053 point 5). Above the seam sits **the state's
reader**: a thin layer that turns what the seam answered into a placed issue or
one of DEC-051 point 6's four outcomes, as a value, and decides nothing about
what the outcome means.

The state's reader asks only the board. The issue's **node id**, GitHub's global
id by which its card is found, comes from the command's own read of the issue.
So an issue that could not be read is the command's failed issue read, never a
board that could not be read.

### 3. Carriage is answered from the map alone, on both read paths

The carriage resolver is pure and cannot fail (ADR-053 point 1), and it consults
the map, never the flag (DEC-062 point 1). Whether the board's Status is the
state's source, its projection, or neither is answered with no I/O, from
carriage and from whether a board is configured. So a project with no board, or
one whose state degrades, makes no network call for its state (ADR-053 point 3).
Every path that asks where an axis lives asks the carriage resolver. The flag
answers only which board a project has, and that every issue belongs on it.

A map that binds an axis to the board, under a configuration naming no board,
resolves to board carriage, and the seam refuses with no network call. So the
map's binding decides carriage, not the flag, and an axis bound to a board that
is not configured is never handed to another substrate. This refines ADR-053
point 2, its edge.

The label read path has no board switch beneath it. With no map, the kit's own
labels carry an axis, board or no board (DEC-062 point 2), and so they do where
the map binds it with `kit-label: true` (DEC-062 point 3). The board carries an
axis only through the map's `board:` arm, which the label read seam reports as
binding shape, like every other arm. So the composition order ADR-026 point 4
pins, the adopter's binding first, holds with nothing beneath it, and no site
reads the flag to decide carriage. This refines ADR-026 point 4, and its
Boundaries' account of where the carriage composition sits.

### 4. The state inference stays pure

The state inference performs no I/O. Where the map binds state to the board, it
takes the Status read as one more input, beside the issue's labels, its
Milestone and whether it is closed. A closed issue is Done, whatever its card
says. An open issue is placed by the read alone. Where the read placed nothing,
or no read was given, the inference gives the issue no position, and never falls
back to the labels or the Milestone.

The command performs the read before calling the inference, and passes the
result in. It holds the read, so it can say which outcome left the issue without
a position. The lifecycle's classifier reads in the same way: it reads the issue
and its card, and passes both to the inference. So the engine's position and a
command's own reading are one inference over the same inputs. ADR-062 stands:
the classifier answers no state, with the finding as its reason, where the
position is undetermined, and leaves its states indeterminate where the board
cannot be read, as it does for any read that fails.

A closed issue's card has two uses all the same. Where a command needs where the
work stood before the close, such as the forward cascade telling finished work
from a won't-do close, it reads the card's Status as that origin. A read that
places nothing leaves the origin unknown, and the command says which outcome it
was. And the capability writes the card's Status to Done, as a projection of the
native close.

### 5. Each command decides what an outcome of the read means

Neither the seam, nor the state's reader, nor the inference decides what an
outcome means. The command decides, at its own boundary, within two limits:

- **It never guesses.** It does not act on a position it could not read
  (DEC-051 point 6).
- **It keeps a broken board apart from a finding.** A board that would not answer
  is reported as that, with what the board said, and never as one of the three
  findings about the issue; a finding is never reported as a broken board. Where
  a command's exit codes tell a broken tool from a refusal, an unreadable board
  takes the broken tool's code. The act such a command exists for may already
  stand when the board cannot be read. The broken tool's code would then report
  the act as not made. So the command's code says instead that the act stands
  and what follows it is owed. That code is neither success's nor a refusal's.
  ADR-053 point 2 rules this limit for a gate; this record rules it for every
  command that reads the state, on the same ground. This refines ADR-053
  point 2, its reach.

DEC-051 point 6 fixes one posture: a seat choosing work skips, with a warning, a
Task whose position is undetermined, and takes nothing where the board cannot be
read. Each other command chooses its own within the limits. For example, a
command that moves one issue cannot check the move from a position it does not
know, so it refuses and names the outcome.

### 6. A command reads the cards of the issues it acts on, and no others

A command acting on one issue reads that issue's card. Where its forward cascade
walks the hierarchy, it reads each ancestor's card in turn, so its reads are
bounded by the hierarchy's depth.

A command that needs the state of many issues makes one **listing read**: it
reads those issues' cards in batches, keyed by the node ids its own read of
those issues gave, and joins each card to its issue by that id. Its reads are
bounded by what it lists, not by the board.

Both reads give one account of which card is an issue's: the issue's card on the
configured board, found among the issue's own cards, an archived card included.

A listing read is whole or nothing. A batch that fails makes the board one that
could not be read, for the whole listing. A listing never takes the issues of a
failed batch for issues with no card.

### Boundaries: what this record is not

- **Not the missing-value question for other axes.** For priority and
  workstream, a board that answers *unset* is the open question ADR-053 point 2
  leaves. For state, DEC-051 point 6 settles it.
- **Not where the state lives.** That is the project's choice, in its map
  (DEC-062).
- **Not what the forward cascade does at an ancestor the read cannot place.**
  DEC-006 holds that a container is never behind the work under it, and DEC-051
  point 6 that no command acts on a position it could not read. At such an
  ancestor the two pull apart, and which gives way is a question for a
  project-management record, not for this one.
- **Not what a card a person moves by hand means.** Whether a card dragged back
  from In Progress is a move back, owing a reason and releasing the owner, is the
  question DEC-006 leaves open. The read says where a card stands, and nothing of
  how it came there.
- **Not a change to the label read path's contract.** ADR-026's single seam, its
  ternary, its fail-closed posture and its sole constructor stand. Point 3
  refines only point 4's account of a switch the flag drives.
- **Not the migration.** The configuration migration that writes each project's
  map is DEC-062 point 6's.

## Rationale

**Why the Status field, and not a field named after the axis.** Projects v2
gives every board a single-select field named Status, and the capability writes
that field as the state's projection where it keeps one. A board carries a field
named after the axis only if its people add one. Reading the field the capability
writes, and mapping options by the rule the write uses, makes an open state read
back as written, by construction. A board that lacks the field is at fault
itself, so it reads as a board that cannot be read, not as a finding against
every issue on it.

**Why through the seam.** The seam is the single home for board reads, on
ADR-053 point 5's grounds. A second reader with board reads of its own would be a
second account of what counts as a board that answered, and it would drift from
the first. The outcomes DEC-051 point 6 tells apart depend on that account.

**Why the state's reader asks only the board.** Were it to read the issue too, a
failed issue read would have to come out as one of the four outcomes. The only
one that fits, a board that cannot be read, names the wrong tool: the
mis-attribution ADR-053 point 2 exists to prevent. The command reads the issue
before it reads the card, so passing the node id costs nothing.

**Why the inference stays pure.** The inference is consulted wherever a state is
needed, and most of it runs on data a command has read. If it read the board
itself, every caller would acquire a network dependency, every test of it would
need a fake board, and the failure posture would sit inside the engine instead of
with the command that knows what a failure costs. This is ADR-053 point 1's
layering, applied to the state.

**Why the command decides, within two limits.** The same outcome costs
different commands different things. A command acting on one issue cannot
proceed on a position it does not know. A seat choosing among many issues can
skip one and go on. Only the command knows which it is, as ADR-053 holds for
every board read. The two limits are what no command may choose: acting on a
guess is what DEC-051 point 6 refuses, and a broken board reported as a finding,
or a finding as a broken board, is the mis-attribution ADR-053 point 2 exists to
prevent, whichever command makes it.

**Why the map alone answers carriage, on both read paths.** DEC-062 makes the map
the one place that says where an axis lives. A flag read left on either read path
would be a second answer, able to disagree with the map, and it would tie the
scoping of ADR-053 point 3 to two declarations instead of one.

**Why a listing reads the listed issues' cards, not the whole board.** A board
keeps the card of every issue placed on it, closed ones included, and an
organisation's board holds the cards of many repositories. A read of every card
makes a listing's cost grow with the board's history and with other
repositories' work, and any bound on the pages it reads becomes a size past which
choosing work takes nothing on every run. A listing is bounded by what the command
lists. Reading the issues' own cards also gives one account of which card is an
issue's, for one issue and for many. A read of the whole board is a second
account, and the two part on a card one counts and the other does not, such as an
archived one: an issue the move command places would then have no card for a
seat choosing work.

**Why whole or nothing.** A batch silently missing from a listing would make
every issue in it look as if it had no card. That turns a tooling fault into a
finding about issues: the mis-attribution ADR-053 point 2 exists to prevent.

### Alternatives considered

- **Find the state's field by the axis's own name.** Rejected: a board carries no
  such field unless its people add one, and the capability writes Status.
- **Let the board arm name its field.** Rejected for the reasons ADR-053 point 6
  and DEC-051 give for every axis: a field name in the map is a second place that
  answers "which field", and a claim the map cannot check.
- **Keep a switch between board and labels beneath the label read seam.**
  Rejected: the switch would decide nothing the map's `board:` arm does not say,
  and a second place deciding it could disagree with the map.
- **A state reader with reads of its own, of the board or of the issue.**
  Rejected: a second account of board reads, the scatter the seam ends, or an
  issue read whose failure passes for a broken board.
- **The inference reads the board.** Rejected: it puts the network inside the
  pure engine, and the failure posture with it.
- **Read every card on the board once, and join the listing to it.** Rejected:
  cost, and a page bound, set by the board's history and other repositories'
  cards rather than by the listing, and a second account of an issue's card.
- **One read per issue in a list.** Rejected: one call for every issue listed,
  where one batch serves a hundred.
- **Fall back to the labels or the Milestone where the board places nothing.**
  Rejected by DEC-051 point 6: a command would act on a position it guessed.
- **Leave ADR-026 point 4 to a later record.** Rejected: DEC-062 point 1 leaves
  the flag no carriage, so point 4 describes a switch that has no place beneath
  the map, and DEC-062's Implications leave its refinement to the architect.

## Implications

- **ADR-053 and ADR-026 are refined in place on this record's acceptance.** The
  architect rewrites each passage below to state what holds, carrying the pointer
  "(refinement per ADR-074)", and checks that the rest of each record agrees
  ([the decisions README, "Refining an accepted record"](../../../.pkit/decisions/README.md#refining-an-accepted-record)).
  - **In ADR-053:** the Summary's "(or the flag)"; the Context's "the board flag
    governs only where the map is silent", and its board arm "admissible on
    `priority` and `workstream` only"; point 1's "board-versus-label only
    underneath"; point 2's "Carriage keys on the board flag alone", with the
    reasoning on "flag set, id unset" that follows it, and the reach of its
    ruling, which names a gate (this record's points 3 and 5); point 6's first
    bullet, which keeps every field's identity on a hook and finds it by the
    axis's own name, and its second, "`state` is excluded for now" (this
    record's point 1); and the Boundaries' missing-value bullet, which for state
    DEC-051 point 6 settles.
  - **In ADR-026:** point 4's account, whole, of a switch between board and
    labels beside the adopter's binding: the flag read at each site that decides
    it, the composition in which it applies beneath the binding, "the switch
    stays outside the seam and the seam composes over it", the later unification
    it leaves unpinned, and the note that its kit-internal half is aging; the
    Boundaries bullet on where the carriage composition sits, with its "while
    the board flag governs carriage where the map is silent"; the Rationale's
    aside on "the kit-internal board-vs-label switch the schemas already and
    legitimately hold"; and the rejected alternative "Fold the board-versus-label
    switch into the seam", which closes "The seam composes over the switch"
    (this record's point 3).

  This refines the two records rather than partly superseding them, because
  every choice they make among alternatives stands (the three layers, the raise
  on an unreadable board, an axis bound to a board that is not configured kept
  on board carriage, the adopter's binding composed first), and each passage
  above either restates the flag's carriage, which DEC-062 ended, or completes
  what ADR-053 left open for state. Even so, rewriting ADR-053 point 2's
  carriage key from the flag to the map changes what that record decides, which
  stays a person's decision
  ([COR-064](../../../.pkit/decisions/core/COR-064-answer-delegate.md) point 6):
  a person's acceptance of this record is the sign-off for that edit.
- **The no-board silence is a tested property for the state.** A project with no
  board, one whose map leaves state out, and one whose map binds state to the
  board under a configuration naming no board make no network call for the
  state. Tests assert this, as ADR-053 point 3 requires.
- **Every consumer of the state inference handles an issue it gives no
  position.** A consumer that filters issues on their state without doing so
  counts every issue whose state the board carries as in none of the states, and
  says nothing. That is the silent miss ADR-053 exists to end, and a defect.
- **A Status write keeps the substrate write path's neutrality**
  ([ADR-031](ADR-031-substrate-write-path-contract.md) point 6): the write
  reports what happened and decides nothing. A command handles a failed Status
  write as it handles a failed write of the substrate that carries the state, or,
  where the Status only projects the state, as it handles any projection left
  behind (DEC-006). Filing handles a failed Status write as it handles every
  other write after the issue is created: the issue stays filed.
- **No migration is owed by this record.** It renames, removes and restructures
  nothing an adopter holds. The configuration migration that writes each
  project's map is DEC-062 point 6's.
