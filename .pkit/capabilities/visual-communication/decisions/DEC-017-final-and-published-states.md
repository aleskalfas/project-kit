---
id: DEC-017
title: A piece marked final takes back its version's lock, and no command writes it after
status: accepted
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person marks a piece final by naming the version that was handed out. The file went out whatever the piece became after, so no change since stops the command. It puts back the lock that version was made under, moves the version's files into the piece's folder, and says what else changed. After that no command changes the piece, and an export refuses it, which overturns one sentence of an accepted record.

The check reads only a final piece's files and its lock, and the way back from final is a new piece copied from it. A published piece keeps a current copy, the unnumbered files a page links. It goes back to a draft by hand, or is marked final, and that copy stays on either move.

An export refuses a lock that differs from the one its current copy was made under. So a new library version reaches a page only through a proposed move. Only a person removes a current copy or a piece, and what a page links stays the page's.

## Context

The accepted records decide the states, and leave open what happens at their edges ([project-kit#2699](https://github.com/aleskalfas/project-kit/issues/2699)).

Two words carry two senses here. A *current copy* is the set of unnumbered files a published piece keeps ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7). A *copy of a final piece* is a new piece, which starts as a pinned draft ([visual-communication:DEC-003-change-over-time] point 8). A *version* alone is a numbered export run, and a *library version* is what a lock names.

What the records leave open:
- **A version the piece changed after.** A file is often handed out before its piece is marked final (DEC-003, Rationale). So the piece, and a draft's lock, may have moved on. A copy of a final piece draws as the piece it copies, and the record of exports keeps no lock of its own.
- **Three cases left to this record** ([visual-communication:DEC-016-what-an-export-reads], Implications). The first is a version the piece changed after. The second let a number or a date through. The third was made before the reading that leaves a pin out.
- **A final piece's check.** It computes no scene ([visual-communication:DEC-002-files-and-validation] point 7). Its other passes are not named.
- **A final piece's render.** "Each render keeps a record" of its findings ([visual-communication:DEC-005-engine-and-plugins] point 13), and the check reads none for a final piece.
- **A final piece's commands.** Making its pictures again would change it (DEC-006, Rationale), and its exports use its outputs as they were handed out (DEC-006 point 7). What its export does is left here (DEC-016 point 6).
- **Moves.** A person sets a state, in a file a person writes (DEC-003 point 8). So a state can be reached with nothing behind it, and a move out of one has no rule.
- **A current copy's end.** "Removing the piece removes the copy" names an act no command performs (DEC-006 point 7). Nothing says what becomes of one at a place the piece stops naming.
- **The writers.** A command writes only the files a record names it the writer of (DEC-002 point 9).

## Decision

**Marking a piece final names the version handed out and puts back its lock, whatever changed since. After it no command changes the piece, and an export refuses it, overturning one sentence of DEC-006 point 7. The check reads only a final piece's files and its lock, and nothing leads out of final. A published piece goes to a draft by hand or to final by that command, and only a person removes its current copy.**

### 1. Marking final takes the version named, whatever changed since

A file that went out is a fact, which no later edit of the piece undoes. So the command that marks a piece final refuses no version for a change since it.
- **It puts back the lock.** The piece takes the lock the version was made under, whatever lock it holds. So a copy of the final piece locks the library versions the freeze named.
- **Read from the fingerprint.** An export's fingerprint reads every file of each library version its lock named, and each such input names its library and that version. Those pairs are the lock. A later form of the fingerprint keeps them, or keeps the lock another way.
- **Only the lock comes back.** The record of exports keeps hashes, so no command can give back a content file. A person who wants the sources as they were restores them from history first. Otherwise a copy holds later words under the older lock, and may need a person to move that lock before it draws.
- **A published piece's lock goes back so too.** This one step takes no proposal and no before-and-after (DEC-003 point 8). The piece stops being published there, and the file its page shows does not change (point 5).
- **It says what else changed.** It reads "changed" as DEC-016 point 1 does, with the lock put back, so the lock's own move counts for nothing. It names the lock it put back, and each input that still does not verify. That stops nothing.
- **A version made before that reading** read the piece's own file whole, so a pin reads as a change. The command says the file was read whole. The lock comes from other inputs, so such a version loses nothing.
- **A number or a date let through** is named too, and stops nothing. No check judges a final piece's drawing, and nothing can mend a file that went out. An element of a switching file let through (DEC-006 point 7) is named the same way, and stops nothing (refinement per [visual-communication:DEC-018-copy-follows-reader-mode] point 1).

### 2. What marking final needs, and what it writes

- **The version's files.** Every file of the version lies in the clone's local folder, with the hash the record of exports keeps. Otherwise the command refuses, naming each file. So a version made on another clone is marked where its files lie.
- **A file lost.** A version that lost a file stays unmarked, since the check would fail its freeze. A later change may let a person name the file lost.
- **A fingerprint it can read.** It refuses a version whose fingerprint is missing, or no longer matches its own inputs, since no lock can be read from that.
- **A lock that no longer holds refuses nothing.** Where a library version the lock names is gone, changed or not released, the run says so and goes on. The piece then carries the finding its lock takes (DEC-002 point 7, DEC-003 point 9). A project's own library version not released fails, so such a mark lands once it is released.
- **One version, whole.** It moves every file of the version into the folder for files handed out, under the names they carry (DEC-016 point 3). A piece with a version handed out refuses a second.
- **One field names it.** The record of exports names the version handed out, in one field of its own. So two branches that mark two versions conflict on merge. That field is no input of any fingerprint.
- **What it leaves.** Every other byte of the piece's own file stays. Every other version stays on the machine that made it (DEC-006 point 7).

### 3. No command changes a final piece after, but for three acts

A piece is *final* to every command where its state says so, or the record of exports names a version handed out. So a slip of the state moves no lock. Where that record cannot be read, as on a conflicted merge, a command takes the piece as final. Once a piece is final, no command changes what its folder holds, but for the three acts below.
- **Three acts stand apart.** A change of format reaches it as DEC-003 point 2 says, and moving the location takes its folder whole (DEC-002 point 1). The command of point 1 takes a piece set final by hand, with no version handed out (point 6).
- **A render** draws its previews in the clone's local folder, and prints what it finds. It moves no lock and writes no record of findings, since the check reads none. A record left from before stays, and nothing reads it.
- **A preview** has no next export to fill in, so it takes the stand-ins and says so (DEC-016 point 5). That is a choice of taste.
- **The commands that frame a program's run** refuse it, a producer's run included. Making its pictures again would change it.
- **An export refuses it,** and names the command that copies it. A final piece was handed out, and handing it out anew is new work. This overturns one sentence of DEC-006 point 7 (Implications).
- **What only reads runs,** such as the check, the viewing step and the command that copies it.

### 4. The check reads a final piece's files and its lock, and no more

- **What it reads:**
  - the binding of each of its files
  - its lock as it stands, against what the project holds (DEC-002 point 7, DEC-003 point 9)
  - that lock against the one point 1 reads from the version handed out (point 6)
  - each file of the version handed out, against its hash (DEC-006 point 8)
- **What it leaves:** its content against its components, its ids, its notations, its brand and the libraries read under its lock. Each of these reads the piece through today's capability, as a scene does.
- **Its produced outputs** go unread too. Only an edit of a final piece could mend one, which would change nothing handed out.
- **So no lock is held to the content.** A library the content came to use after the version is no finding, since the content goes unread.
- **What goes unread is read later.** A copy of the final piece is a draft, and the check reads it in full.
- **Nothing compares a final piece's other files with its freeze.** An edit there changes no file handed out, and a reviewer reads its diff.

### 5. Published leads to a draft or to final, and final leads nowhere

- **From published to a draft.** A person sets the state by hand. The current copy stays where it lies, so a page goes on showing it. No check holds it to its sources, and a draft's export does not write it. The check asks for attention until it goes or the piece is published again (point 6).
- **Back to published.** A person sets the state by hand, and the current copy is held again to the version that wrote it. So the next export mends what changed, where the lock has not moved.
- **The export's gate.** An export refuses a published piece whose lock differs from the one point 1 reads from the version that last wrote its current copy. So a state changed and changed back, or a lock written by hand, brings no new library version to a page.
- **Two ways past the gate.** The gate stops only an export a person runs, and its refusal names both ways. One is the command that proposes a move of the lock (DEC-003 point 8), which makes its own run and leaves no difference. The other is writing back that lock, which is no move of it.
- **What the gate reads.** The gate reads the record, not the files, so removing the copy changes nothing. Where the record holds no current copy of the piece's own, nothing compares, and the export runs. A fingerprint it cannot read refuses, and names the record.
- **From published to final.** The command of point 1 does it. The current copy stays, and a page goes on showing it. No export can mend it, so no check holds it. The command says so where the version named did not write it.
- **Out of final, no move.** Its lock never moves, and its exports are its freeze (DEC-003 point 8). A copy of it is the way back. A mark made in error is undone by reverting the change, and its files go back to the clone's local folder by hand.
- **The files handed out** lie only in a final piece, so no move touches them.

### 6. A state reached by hand owes what stands behind it

A person writes `state` in the piece's own file, so the check holds each state to what it needs. Each of these fails, as an invariant this record owns in a file the project can correct (DEC-002 point 7):
- **`state: final` with no version handed out.** The fix names the command of point 1, which takes such a piece, or setting the state back.
- **A version handed out, and another state.** The fix names setting it back to final, and a copy of it for new work.
- **A version handed out, and another lock,** as a hand or a merge may leave. The fix names writing back the lock the version was made under, which is no move of it.
- **`state: published` with no format.** The fix names declaring one.
- **`state: published` with no whole current copy.** It has none of its own, or a file of it is missing or changed, in its folder or at the place it names. The fix names the export, once a changed file at a place is removed.

One asks the piece's author for attention, since a page may rely on what stands:
- **A draft with a file of its current copy standing,** at the path the record of exports names. Its hash does not count, so changing a byte leaves the finding. The fix names removing it, or publishing the piece again.

### 7. Only a person removes a current copy or a piece

A current copy at a place the piece names lies outside the piece, and a page may rely on it. So no command removes it.
- **The record keeps what it wrote.** The record of exports names the piece and the version that wrote the current copy, and each file's path and hash. A path in the piece's folder is read from that folder, so a rename or a move of the location leaves it true.
- **Whose copy it is.** A current copy is a piece's own where the record names that piece, or a piece the location no longer holds. So a rename keeps it, and a folder copied by hand brings none while the original stands. Every rule here on a piece's current copy reads it so, the check's included.
- **Left behind.** An export names each file of the last current copy that it did not write again. One may lie at a place the piece stopped naming. The file stays where it lies, and a person removes it.
- **In the piece's folder,** an export replaces the current copy whole, since that folder holds nothing else.
- **What a page links lies outside the capability.** No check follows a page's image path. So a page that keeps the old path goes on showing the old figure, or a dead image once the file goes. Mending it is the page's change.
- **Removing a piece is a person's act.** A person deletes its folder, which takes a current copy in that folder along. The person first reads any place from the piece's own file, and removes what lies there too.
- **A page's anchor reaches that act.** A page anchors what produced its figure ([living-docs:DEC-002-visual-elements] point 4). So removing the piece leaves a dead anchor, an error on the change that removes it (COR-050 point 7). A page with no such anchor is not flagged.

### 8. The writers

Each command below is the writer of what it names (DEC-002 point 9).
- **The command that marks a piece final:** `state` and `lock` in the piece's own file, the field in the record of exports, and the version's files, moved into their folder.
- **The command that copies a final piece:** a new piece's folder, from a piece with a version handed out, under a name the person gives that no piece holds.
  - It copies the folder whole, but for what only that piece's past holds. That is each record a command rewrites of its exports, findings and drawing, and the folders of files handed out and a current copy.
  - In the new piece's own file it sets a draft, pins the lock of the version handed out, and drops the current copy's place.
- **An export:** the current copy, in its folder or at the place the piece names.
  - A place lies inside the repository where version control keeps it, outside the location and the methodology's own folder. A path through a link refuses.
  - It writes over only a file of that piece's current copy (point 7), with the hash the record keeps. Any other file at a path it writes refuses the run. The run names it, and a person names another place, or removes a file they mean to replace.
- **The command that proposes a move of the lock** writes the current copy too, under the same rules (refinement per [visual-communication:DEC-019-lock-moves-and-pruning]).

## Rationale

**Why no version is refused for a change since.** A refusal would ask a person to undo later work to record what already happened. The records expect the case, since a file often goes out before its piece is marked final. The freeze lies in the files, so it does not depend on the sources.

**Why the lock is put back, and only the lock.** The lock a piece holds may name versions no handed-out file was drawn under. A copy of the final piece would then start from a look nobody handed out. Content cannot come back, since only its hash is kept. So a copy holds the piece's words, which may be later than the file's.

**Why a lock that no longer holds refuses nothing.** The file went out under that lock, and the fault is one the check keeps in sight. A refusal would leave a handed-out file in one clone's uncommitted folder, for good where only another's release could mend it. The record of shipped library releases expects a final piece on a shipped number not released ([visual-communication:DEC-013-shipped-library-releases] point 5).

**Why the fingerprint gives the lock.** It is already there, in every version a project holds. A field of its own would be a second home for one fact, and absent from those versions.

**Why the run says what changed, and does not stop.** Naming the version is the person's word that this file went out. An export stops because a person can still choose before a file goes out, and here it already went. A stop would also fire for nothing on every version made before the reading.

**Why one field of the record of exports.** The piece's own file then gains no field that a fingerprint must leave out. One field, rather than a mark on each version, turns two marks into a conflict a merge shows. It repeats the piece's `state`, which the accepted records own, so point 6 guards each against the other. A lock field would repeat what each version holds, but no file yet says which version went out.

**Why either the state or the field makes a piece final to a command.** Each alone is a fault the check fails. Until it is mended, a command that took the kinder reading could move a lock that never moves.

**Why no command changes a final piece.** One rule answers for the render, the producer and the export. Anything written there could only differ from the freeze, or lie beside it unread.

**Why an export refuses a final piece.** Only the lock comes back, so an export would draw later words under an older lock, which no check judges. It would also take a number in a closed record, and its file would go out with no piece keeping it. A copy costs one command, and gives new work a state, a lock and a full check. So this overturns one sentence of DEC-006 point 7, which let such an export run.

**Why DEC-006's sentence is overturned, and DEC-003's "only" narrowed.** A sentence with no case left is overturned, and one that keeps its cases and gains a bounded exception is narrowed. "Only" keeps every case in which a new lock reaches a page. Marking final sits on an edge that record never decided, and neither exception changes what a page shows.

**Why the check stops at files and lock.** Each other pass reads the piece through today's capability, so a stricter release could fail a talk already given. Its mend would change nothing handed out. A failure with no reader behind it teaches people to bypass the check (DEC-002, Rationale).

**Why a final piece's render keeps no record.** No check reads one. It would only show as a change in a frozen folder at each look.

**Why nothing leads out of final.** A way back would need a rule for the files handed out, and for a lock that never moves. A copy already gives a person a draft, and leaves the freeze whole.

**Why a published piece may go back to a draft.** A figure can leave its page, and the move costs one word, which the diff shows. A rework the page goes on showing needs no such move, since it lands with its export.

**Why a current copy stays on either move.** A page may rely on it, and a change of state is no reason to break the page. A draft's copy asks for attention, since someone may act. A final piece's asks for nothing, since no export can mend it.

**Why the gate lies at the export.** It is the one step that reaches a page, so one comparison there covers a state changed and changed back, a hand and a merge. A hold on a draft's render would leave a person a way round, by removing the copy as a finding says. It compares two locks and sees no review, so only the proposing command's own run goes past it. That keeps DEC-003 point 8 whole.

**Why a place lies where it does.** A current copy is committed (DEC-006 point 7), so a place must be one version control keeps, or another clone lacks the file. Inside the location, a move of it would leave the record's path wrong. The methodology's folder is refreshed at each sync, and a link could lead outside all of this.

**Why a copy of a final piece drops the place.** The new piece is a draft, and writes no current copy. Kept, two pieces would claim one path.

**Why no command removes a current copy.** The file lies outside the piece, and only a person can see what relies on it. A stop would leave no way past where a page still links the file. So a file left behind is named, and that case is rare enough to stay a person's.

**Why the record names the piece.** A folder copied by hand carries the same record and the same hash, so neither shows whose file it is. Without the name, the draft's finding sends a person to the other piece's file. An export may also write over it, where the two names meet. Two folders can still claim one copy where the original is renamed after a hand copy, a rare case its diff shows.

**Why removing a piece needs no command.** A piece is one folder, and its own file names where its current copy lies. A file left behind at an earlier place was named once, and no record keeps it. A page that anchors the piece fails the change that removes it, so the act is silent only for a page that declared nothing. A command would add a thing to keep for a rare act, and a later change may add one if the act recurs.

**Choices of taste.** No design reason decides these, so each takes the plainest answer:
- A record of findings left from before stays in a final piece's folder, unread.
- A copy of a final piece keeps the words of the piece's own file as they stand, such as who it is for.
- Removing a final piece asks no step beyond removing any other.
- A piece marked final keeps its pin, which then means nothing.
- A final piece's preview takes the stand-ins, rather than the facts of the version handed out.

### Alternatives considered

- **Refusing a version the piece changed after.** Rejected, for the reasons above.
- **Keeping the lock the piece holds.** Rejected. A copy would lock versions no file went out under.
- **Refusing a lock that no longer holds.** Rejected, for the reasons above.
- **A stop a person names their way past,** as an export has. Rejected, for the reasons above.
- **A freeze that names a file lost.** Left out. It needs a shape of its own for a rare case, and a later change may add it.
- **A lock written into each entry of the record of exports.** Rejected. It repeats what the inputs hold, and no version a project holds carries it.
- **The version handed out named in the piece's own file.** Rejected. The list of fields an export leaves out would grow by one.
- **Two versions handed out.** Rejected. A piece holds one lock, so two versions under two locks cannot both be its freeze.
- **A mark on each version of the record.** Rejected. Two branches could mark two versions and merge in silence.
- **An export of a final piece, under a new number.** Rejected, for the reasons above.
- **A render of a final piece that keeps a record.** Rejected. Nothing reads it.
- **A check of a final piece's content, notations or brand.** Rejected. A new release could fail a piece nobody should change.
- **A move from final back to a draft.** Rejected. It would need rules a copy makes needless.
- **No move from published back to a draft.** Rejected. A figure that left its page would stay held to its sources for good.
- **A draft that gives up its current copy, or fails while one stands.** Rejected. The move would break a page to change one word.
- **A draft's lock held while a current copy stands.** Rejected. A person who removes the copy goes round it, and a render would read paths outside the location.
- **A command for each move of state.** Rejected. Marking final aside, a move writes one word.
- **A mark a proposal leaves for the gate to read.** Rejected. A hand can write it.
- **An export that removes what it left behind.** Rejected. A page may still link the file, which a person can see and a command cannot.
- **An export that stops on a file left behind.** Rejected. A file a page still links would stop it with no way past.
- **A command that removes a piece.** Left out, for the reasons above.

## Implications

- **Edits to accepted records,** each made once this record is accepted, and citing it. Accepting this record accepts them (COR-066 point 5).
  - **The record of files and validation, point 7, "A final piece is judged by its files and its lock".** A sentence follows "against today's engine". It reads no content, notation, brand or produced output, nor the libraries under its lock, and a copy meets them as a draft. The sentence on a move of the lock adds that writing back its version's lock is no such move.
  - **The record of change over time, point 8, "A pinned draft".** A sentence ends the bullet: where the sources changed after the version handed out, a copy holds later words, and may need its lock moved.
  - **Its point 8, "Final".** It names "the version handed out", in place of "which of the piece's exports were handed out". A sentence goes before "Its lock never moves": the command that marks it puts back the lock that version was made under. A sentence ends the bullet: no state leads out of final, and a copy of the piece takes it up again.
  - **Its point 8, "Published".** Two sentences follow the one on a proposed change. Marking it final alone moves its lock otherwise, back to the lock of the version named. Writing back the lock its current copy was made under is no move of it. A sentence ends the bullet: a person may set it back to a draft or mark it final, and its current copy stays.
  - **Its point 9, "These fail".** The sentence on a final piece's lock adds that writing back its version's lock is no move of it.
  - **The record of the engine and its plugins, point 13, "Each render keeps a record".** It opens: "Each render of a piece that is not final keeps a record of its piece's findings". The rest stands.
  - **Its point 13, "A final piece's scenes are not computed".** It reads: the check computes no final piece's scenes (DEC-002 point 7), and a render of one keeps no record, since the check reads none.
  - **The record of work outside the engine and outputs, its top line.** It reads *Partially superseded by* [visual-communication:DEC-017-final-and-published-states], in the shape the record of change over time's takes. Overturned: point 7's sentence that a final piece's exports use its outputs as they were handed out, which let such an export run. The rest stands, and that sentence stays as it stood.
  - **Its point 7, "The record of exports".** Three sentences end the bullet. An export's inputs name every library version of its lock. It names the version handed out. It names the piece and the version that wrote the current copy, and each file's path and hash.
  - **Its point 7, after "No number or date that overflows".** A bullet follows. An export a person runs refuses a published piece whose lock differs from that of the version that last wrote its current copy. The command that proposes a move of the lock makes its own run.
  - **Its point 7, "What is committed".** The sentence on one folder ends: "but for a copy at a place it names".
  - **Its point 7, "A published piece's current copy".** Its last sentence reads: whoever removes the piece removes a copy at such a place, and an export names a file it leaves behind there.
  - **Its point 8, "They fail validation".** It adds [visual-communication:DEC-017-final-and-published-states] point 6 as bullets. Two are a piece marked final with no version handed out, and a version handed out with another state or lock. It also adds a published piece with no format or no whole current copy.
  - **Its point 8, "They ask for attention".** It adds a draft with a file of its current copy standing.
  - **Its point 8, "Never reported".** Its first sentence names any finding on a final piece's outputs of point 1, not only a stale one. No bullet above reaches them. The rest stands.
  - **Its Implications, "Two branches".** A sentence ends the bullet. The name of the version that wrote the current copy follows that version, and where its entry goes it names the version kept.
  - **The record of what an export reads, point 6, "A final piece".** It reads: a final piece takes no export ([visual-communication:DEC-017-final-and-published-states] point 3), so nothing here reaches it.
  - **Its Implications, the bullet on the issue's record.** Its first words read "[visual-communication:DEC-017-final-and-published-states] point 1", in place of the issue. "As point 1 says" reads "as point 1 here says".
- **These need no edit:**
  - The founding record's point 7. Nothing handed out is redrawn, and no release reaches a piece through a lock put back.
  - The record of files and validation's point 9, since this record names the writers.
  - The record of change over time's point 8, "Released versions only". The command writes the lock as the version used it, and the check holds it to that bullet.
  - The record of the engine's point 14, whose last sentence already leaves a final piece's drawing unjudged.
  - The record of shipped library releases' point 5, which already expects a final piece on a shipped number not released.
  - The record of the viewing step's points 1 and 4. It reads a final piece and writes in the clone's local folder alone.
  - The record of what an export reads, point 5. A final piece has no next number, so the stand-ins it names serve that piece's preview and viewing step.
  - The findings point 4 takes out of a final piece's check, such as a component's standing and a concept (DEC-003 point 9, DEC-004 point 11). They sit under DEC-002 point 7's policy, which this record edits.
- **The pages.** What anchors these points may owe answers once the edits land. No page changes its text in this change, since the changes below build what this record decides.
- **The change that lets a piece's format take `final` and `published`** writes the state this record reads. It lands with, or after, a render that reads the state, so a final or a published lock holds still. It widens the state the record of exports keeps.
- **The change that builds marking final** carries out points 1, 2 and 8's first bullet, and a final piece's render of point 3. It adds the field to the record of exports, an addition the format allows (DEC-003 point 3). It names the command. A test holds that an export's inputs name its whole lock, which rests on an export's refusal of a lock that does not hold.
- **The change that judges a final piece** carries out point 4, point 6's findings on a version handed out, and point 3's refusals. It sorts the lock's findings by DEC-002 point 7. Its refusals land before marking final does, or with it.
- **The change that copies a final piece** carries out point 8's second bullet. It names the command.
- **The changes that write and hold a current copy** carry out point 5's gate, point 7's first four bullets and point 8's third bullet. They also carry out point 6's findings on a published piece. [visual-communication:DEC-018-copy-follows-reader-mode] point 3 says what the hash is taken of.
- **[visual-communication:DEC-019-lock-moves-and-pruning]** decides what a proposal carries, which leaves no difference at point 5's gate. Until its command exists a published lock cannot move, which fails closed.
- **[visual-communication:DEC-019-lock-moves-and-pruning]** names that command a writer of the copy, and decides a move of a piece none of whose copy's files stand.
- **What removing a library version no lock names spares.** That is decided by [visual-communication:DEC-019-lock-moves-and-pruning] point 9. A library version named only by kept fingerprints, other than that of the version that wrote a current copy, is no lock's, so marking final an export made under it leaves a finding until it is back.
- **A check that follows a page's image path** is living-docs' to weigh, and nothing here waits for it.
