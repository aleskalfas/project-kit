---
id: DEC-016
title: An export reads what can change its files, and a stand-in measures what no file holds
status: proposed
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an export keeps a fingerprint, which says what it was made from, so a later look can tell whether the piece changed since. Today pinning a draft or setting its state reads as a change, and that would fail a published piece's copy. So the fingerprint leaves out of the piece's own file the fields that change nothing an export draws, beyond what the export itself shows. Each entry of the fingerprint names what it left out, so an earlier fingerprint goes on verifying. The findings record stays keyed by the whole file.

Files handed out and a copy lie in folders of their own, which no fingerprint reads. A component may show a version's number and its date, which lie in no file, so the check measures a fixed stand-in for each. An export measures the real text. It stops on a number or a date that overflows, and the person who runs it may name that fact to use its text as it is.

## Context

Each export keeps a fingerprint of what it was made from ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7). Two steps come to read it. Marking a version final asks whether the piece changed after it. A published piece's copy fails when something it read changed (DEC-006 point 8).

What the fingerprint does today ([project-kit#2698](https://github.com/aleskalfas/project-kit/issues/2698)):
- **It reads the piece's own file whole.** So pinning a draft, setting its state or editing a field no scene reads fails it, as a move of the lock does.
- **It reads a produced output's record whole.** That record holds the time and the machine, which are never compared (DEC-006 point 5). So a producer run again with the same pixels reads as a change.
- **Its inputs are built on the findings key's** ([visual-communication:DEC-005-engine-and-plugins] point 13), with the piece's formats beside them. One form number covers every kind of fingerprint, a released library's hash included.
- **Nothing verifies it yet.** The check reads only the binding of the record of exports. Format 1 takes the draft state alone, so no piece is final or published.
- **A project holds some already.** A piece's record of exports keeps each version's fingerprint. Every form the capability shipped is kept, and the check verifies a fingerprint under the form it names (DEC-006 point 6).

Two things reach the fingerprint from the accepted records:
- **A piece's folder gains files that are no input.** The version handed out is moved into it, and a published piece's copy may lie there (DEC-006 point 7).
- **A scene gains an input that is no file.** A component may show the version, its date, its language and the piece's state. How the check measures such text is left open (DEC-006 point 7). Four accepted points meet there:
  - the same files give the same answer ([visual-communication:DEC-002-files-and-validation] point 6)
  - the same files give the same scene (DEC-005 point 5, and [visual-communication:DEC-001-visual-communication-discipline] point 8)
  - findings are keyed by files (DEC-005 point 13)
  - overflow fails (DEC-005 point 14)

## Decision

**An export's fingerprint leaves out only fields that can change no exported file, or change one only as a fact of that export, and each input names what it left out. The findings key keeps the piece's own file whole, and no fingerprint reads files handed out or a copy. The check measures a fixed stand-in for a version's number and date. An export measures the real text, and stops on a number or a date that overflows unless the person who runs it names that fact to use its text as it is.**

### 1. An export reads all of the piece's own file but the fields one test allows

A piece has changed since an export where that export's fingerprint no longer verifies. Marking a version final reads it so. The check on a published piece's copy reads it so too, in the version that wrote the copy.
- **The test.** The reading leaves a field out only where its value can change no exported file's bytes, or changes them only as a fact of that export (point 5). Every other field counts, the lock and the formats among them.
- **Who holds the list.** The capability's reference names the fields that pass, and a test holds them to what scenes read.
- **A field added later counts.** It stays an input until a change shows it passes and adds it to the list. A listed field that a scene comes to read, other than as a fact, leaves the list the same way.
- **The state, which a component may show,** passes, since what a component shows is a fact of that export. A version keeps the state it was made in.
- **The losses a piece accepts** pass. They set what the check says, and no renderer reads them.
- **The place of a published piece's copy** passes. It changes where an export writes, not what it writes.
- **A produced output's record** is read the same way, without what it only records (DEC-006 point 5).
- **Every other input stands.** The piece's other own files are read whole, and so are each locked version's files, each font its scenes read and any shared content it reads.

### 2. The findings key keeps reading the piece's own file whole

- **Only the export's reading narrows.** The findings key, a produced output's fingerprint, written code's fingerprint and a released library's hash leave no field out.
- **The fields left out still change findings.** The losses a piece accepts decide what the findings record keeps, and a shown state is measured as it stands (point 5). A key without them would keep findings the files no longer give.
- **So the key stays as the record of the engine decides it** (DEC-005 point 13), a hash of every file its scenes were computed from. The folders of point 3 were never among those files.

### 3. Files handed out and a copy lie in folders no fingerprint reads

- **A folder for each.** The files of a version handed out lie in one folder within the piece's folder, and a published piece's copy in another. Each folder takes one fixed name in every piece.
- **Left out by place.** Every file under them is left out, whatever its name, as a produced output's pictures are.
- **From the export's fingerprint and the findings key alike.** No scene is computed from these files. Left in the key, each export that writes a copy would put the findings record out of date.
- **Never a source.** Nothing a scene reads lies in them. Should content come to name a file by its path, a path into them is refused.
- **A copy a documentation page shows** lies at the place the piece names, outside the piece's folder (DEC-006 point 7). No fingerprint reads it either.

### 4. Each input says what it left out

- **In the input.** An input that leaves fields out names each field of the list it applied, whether the file held that field or not (DEC-006 point 6). So a field set later stays left out. An input that names none read the whole file.
- **The check reads as the input says.** It reads such a file without the fields the input names, whatever the list holds today. So a kept fingerprint verifies as it was written.
- **What that leaves alone.** Form 1 stands, and both readings live in it, told apart by the input. So nothing turns on the form, and no library hash is taken again. A later change of the list takes no new form either.
- **A field that later leaves the list** counts from the next export. Until then a kept fingerprint skips it, as a new engine makes no export stale (DEC-006 point 7).
- **The folders need no form.** No fingerprint lists a file in them, unless a piece already holds a folder of that name. Such a piece reads as changed once, and one export mends it.
- **An export made before this reading** read the whole file, so a pin reads as a change since it. Each later export writes the new reading.

### 5. The check measures a stand-in for what no file holds

Four facts of an export may show in a scene (DEC-006 point 7). A *stand-in* is one fixed text measured in place of a fact that no file holds.
- **The language and the state come from files.** Every scene shows them as the files hold them, so they need no stand-in.
- **A version's number and its date come from no file.** An export fixes them as it runs, from the clock and from what this clone holds.
- **A stand-in for each.** The check's scenes take one fixed text for the number and one for the date, in the form an export writes them in that language. So the same files give the same answer on every machine, on any day.
- **A stand-in's text is the engine's.** The capability's reference holds it, and a new text reaches a piece as a new engine does, at a render (DEC-005 point 13).
- **Every scene a shared answer rests on takes them.** These are the check's scenes, those a render keeps findings from, and those a program's measured frames come from.
- **The findings record keeps what those scenes found,** under a key of files alone. So a render on any clone writes the same record.
- **A stand-in that overflows** is a finding at the element that shows the fact, and it names the component. It fails where the project can correct that component, and asks for attention in a released library (DEC-005 point 14).
- **What a person looks at shows real text.** A preview fills what this clone's next export would: its next number and the date of this run. Another clone may show another number, which harms nothing, since a preview is never committed. A before-and-after and the viewing step fill the same way.
- **Where a preview cannot read the next number,** as in a record of exports that conflicts on a merge, it takes the stand-ins and says so.
- **A real text that overflows in a preview** is said in the render's output, and no record keeps it.
- **An export fills one number and one date.** They are the ones its record keeps, so every file of a version shows the same.
- **A version that lost its number to another branch** is not renamed where the piece shows its number, since its files hold the old one (DEC-006, Implications). Its entry goes, and the next export takes the next free number.
- **An export's fingerprint reads none of these facts.** The record of exports keeps the number, the time and the state, and each file's name holds the language. So a new number makes nothing stale.
- **The seam stays as it is.** The engine gains one kind of source, and a renderer still gets plain text. So the seam's version does not move (DEC-005 point 8).

### 6. An export stops on a number or a date that overflows

- **Measured where it is filled.** An export computes its scenes with the real text. It measures each element that shows a version's number or its date, and each component around it, as the check does, from a font file. It looks for a text that overflows its box and a component that gets less than it asks for.
- **It stops before any write.** It names the fact, its text and the element. It stops whether or not the stand-in overflowed too, and in any library.
- **The person may name a fact to use its text as it is,** as they name each stale output (DEC-006 point 7). A fact nobody named still stops. The export then writes its files, and its record keeps each text let through.
- **What that leaves.** A published piece's copy made so is a finding until a version fits. It fails where the project can correct the component, and asks for attention in a released library, naming its owner (DEC-002 point 7).
- **The language and the state** come from files, so the check measures them as they stand, and nothing here stops on them.
- **An overflow measured from a table or by an estimate** stops nothing. The run says it in its output, since the check only asks attention for it (DEC-005 point 14).
- **What stays unseen.** A longer text may wrap within its box and move what lies beside it, with nothing overflowing and no component getting less. Neither the check nor the export sees that, so it is left to a person or a reviewer looking at the page ([visual-communication:DEC-015-viewing-step-and-reviewer]).
- **A final piece.** Its drawing is not judged (DEC-005 point 14). What its export does is left to [project-kit#2699](https://github.com/aleskalfas/project-kit/issues/2699)'s record.

## Rationale

**Why a named list is left out, rather than read.** A list of fields to read would miss a later field a scene reads, so a stale copy would pass. A list left out fails closed for every field not on it: a slip costs a false "stale" that one export mends. Keeping the whole file costs that false "stale" at every change of state, or of a field nobody sees. A listed field that a scene came to read would pass unseen, so a test holds the list to what scenes read (point 1).

**Why the losses a piece accepts pass.** Left in, accepting a loss on a published piece would fail its copy, though nothing drawn changed.

**Why the findings key does not move.** The two mistakes cost differently. A findings record that does not verify has its scenes computed again, which costs time and fails nothing. A key that read too little would keep findings the files no longer give, and the check would trust them.

**Why folders.** A place is read from the path alone, as a produced output's pictures are. A name cannot tell a copy from a person's file, since a copy carries no number. A list of hashes would make a piece's inputs depend on the record of exports, which no fingerprint reads. Two folders keep the files that never change apart from those each export rewrites.

**Why each input says what it left out.** The rule of keeping every form exists so that the fingerprints a project holds go on verifying. A list the form fixed would cost a new form, or a record that no longer verifies, at each change of it. Which of the two applied would turn on whether a release came first. A fingerprint already says what it read, input by input, so it says this too. The cost is that the form no longer fixes the whole of an input set, and a field leaving the list reaches a kept fingerprint only at the next export.

**Why a stand-in, and only for two facts.** One answer on every machine needs a text that depends on neither the clone nor the day. The language and the state already meet that, so they keep their real text. A measured frame takes a stand-in too, or each export's number could make a produced picture stale. The check then never sees the real text, which point 6 meets, and a component narrower than the stand-in fails on a text nobody reads, so the stand-in is kept to what a usual real value needs.

**Why a person sees real text.** A preview exists to show what the export will show, and it reaches nobody else. A render and an export then compute the scenes twice, only for a piece that shows a fact.

**Why an export stops, and why a person may go past it.** No check sees the real number or date, so the export is the last place they can be measured. A person should choose before a broken line goes out. A stop with no way past would cost more, since a number only grows and only an export mends a stale copy. A published piece could then fail validation until someone redesigned it, even where only a released library could give the text room (DEC-002 point 7).

### Alternatives considered

- **A named list of the fields an export reads.** Rejected. A later field a scene reads would be missed, and a stale copy would pass.
- **Keeping the piece's own file whole.** Rejected. A change of state, or of a field nobody sees, would fail a published piece's copy.
- **A hash of the computed scene in place of files.** Rejected. It is exact, but the check would compute every scene (DEC-005 point 13), and a new engine would make exports stale.
- **The findings key narrowed with the export's.** Rejected. It saves some computing, and risks findings the files no longer give.
- **A name pattern, or the hashes the record of exports keeps, to leave out handed-out files.** Rejected, for the reasons above.
- **One folder for files handed out and a copy.** Rejected. Files that never change would lie among those each export rewrites.
- **A list the form fixes, changed in form 1 or by a form 2.** Rejected. Changed in place, a kept record stops verifying with no input changed. A form 2 is one more number to keep at each change of the list, and which of the two applied would turn on whether a release came first.
- **A form for each kind of fingerprint.** Rejected. A second numbering would follow every kind, to spare one reading.
- **The check reading the next number and today's date.** Rejected. Its answer would differ between clones and between days.
- **The next number kept in a file the scene reads.** Rejected. Every export would put the findings record out of date, and the date would still lie in no file.
- **A width each component declares for a fact.** Rejected. A stand-in gives one width with no new field, where each library would otherwise owe one.
- **An export that writes the overflow and says so.** Rejected. A person would learn of it only once the file is made, and nobody would have chosen it.
- **A stop with no way past.** Rejected, for the reasons above.
- **A check that warns as a number nears its box.** Left out. A stop with a way past costs little, and a later change may add it.
- **A preview that fills the stand-ins.** Rejected. A person would see a text no export shows, and meet a real overflow only at the export.

## Implications

- **Edits to accepted records,** each made in place once this record is accepted, and citing it. Accepting this record accepts them (COR-066 point 5).
  - **The founding record, point 8, "The engine runs no helper".** It computes only from the project's files and the facts of an export, so the same files and facts give the same scene on every machine. Its check takes stand-ins for the facts no file holds, so it can run within validation. That replaces the bullet's last sentence.
  - **The record of the engine and its plugins, point 5.**
    - "The root says what the scene is" adds: two scenes with one root differ only in the text of an export's facts.
    - "Every element carries its trace" adds an export's fact to the sources a property may name.
    - "Computed, never committed" reads: order and rounding are fixed, so under one release of the capability the same files and facts give the same scene on every machine, and two such scenes compare. A scene the check computes takes the stand-ins.
  - **Its point 7, "What a program run while preparing receives".** Its second sentence adds that the scene its measured frames come from takes the stand-ins.
  - **Its point 13, "Each render keeps a record".** The findings come from scenes that take the stand-ins, and the key is a hash of every file those scenes were computed from.
  - **The record of work outside the engine and outputs, point 6, "An input".** An input is a file, or a part of a file of the capability's format named by its path of keys. It may read such a file without fields it names, and the check reads it so. The rest of the bullet stands.
  - **Its point 6, "Its version and hash".** A version fixes how each kind of thing is read, apart from the fields an input names.
  - **Its point 7, "The piece may show it too".** The check measures a version's number and its date by a stand-in, so the same files still give the same answer. That replaces the last sentence. The sentence on a preview adds that it takes the stand-ins where it cannot read the next number.
  - **Its point 7, "The record of exports".** Its first sentence adds that each file is read as this record's points 1 and 4 say. The rest stands.
  - **Its point 7, "What it only records".** It also names each number or date the version let through.
  - **Its point 7, "No stale output".** A bullet follows it: an export stops on a number or a date that overflows, and names it, and the person who runs it may name that fact to use its text as it is.
  - **Its point 7, "What is committed, in the piece's folder".** A sentence goes before the last: the version handed out and a published piece's copy each lie in a folder of their own there, which no fingerprint reads.
  - **Its point 8.** A published piece's current copy made with a number or a date let through joins "They fail validation" where the project can correct the component, and "They ask for attention" in a released library.
  - **Its Implications, "Two branches".** Where a piece shows its version, the other version is not renamed, since its files hold the old number. Its entry goes, and the next export takes the next free number.
- **These need no edit:**
  - The record of files and validation's point 6, since the check still computes from the files alone.
  - Its point 7. A stand-in's overflow and a copy let through take that point's severity, so nothing fails for what only a library's owner corrects.
  - The record of work outside the engine's point 5, whose words hold once this record says what an export read.
  - The record of the viewing step's point 1. "It takes no number" means it uses none up, and it may read the next one for its text.
- **The pages.** The capability's reference pages on checks, outputs and components anchor these points, so they may owe answers once the edits land. No page changes its text in this change, since the changes below build what this record decides.
- **The change that builds the reading** carries out points 1, 3 and 4. It fixes the names of the two folders and of the copy's field, and writes the list in the capability's reference. The fingerprint's schema takes the new shape of an input, an addition the format allows (DEC-003 point 3). The check takes what the kept inputs name, and what the reference and the code say of a form fixing an input set changes with it. A test holds the list to what scenes read: changing a listed field, the state as a fact aside, changes no scene.
- **The change that shows an export's facts** carries out points 5 and 6. It fixes each stand-in's text, wide enough that a usual real value fits. What fills the facts is a required argument of computing a scene, so no caller takes one by default. A before-and-after works out one filling and gives it to both sides.
- **The changes that write and hold a published piece's copy** owe that it is made while the piece is published, which no fingerprint enforces.
- **[project-kit#2699](https://github.com/aleskalfas/project-kit/issues/2699)'s record** decides what marking final does with a version the piece changed after, reading "changed" as point 1 says. It also decides what marking final does with a version that let a number or a date through, and with one made before this reading, which reads as changed after a pin.
- **A renderer that draws into a lasting medium** comes later (DEC-005 point 11). Its record is rewritten at each render, so the change that builds it leaves that record out of every fingerprint, and decides which text it fills.
- **A later reading of content** may write under the methodology's container key in a content file (DEC-002 point 4). Content files are read whole, so that write reads as a change until a record leaves the key out.
