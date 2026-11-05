---
id: DEC-016
title: An export reads what can change its files, and a stand-in measures what no file holds
status: proposed
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an export's record says what the export was made from, so a later look can tell whether the piece changed since. It reads every file a scene is computed from, and all of `piece.yaml` but a few named fields that can change no exported file. A field added later counts until a record names it. The key of the findings record keeps reading `piece.yaml` whole.

Files handed out and a copy lie in folders of their own, which no fingerprint reads. Form 1 of the fingerprint may change in place until a release carries it, and after that a new form takes the change. A version's number and its date lie in no file, so the check measures a fixed stand-in for each. Where the real text then overflows, the export refuses it.

## Context

Each export keeps a fingerprint of what it was made from ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7). Two steps come to read it. Marking a version final asks whether the piece changed after it. A published piece's copy fails when something it read changed (DEC-006 point 8).

What the fingerprint does today ([project-kit#2698](https://github.com/aleskalfas/project-kit/issues/2698)):
- **It reads `piece.yaml` whole.** So pinning a draft, setting its state or editing a field no scene reads fails it, as a move of the lock does.
- **Its inputs are built on the findings key's** ([visual-communication:DEC-005-engine-and-plugins] point 13), with the piece's formats beside them. One form number covers every kind of fingerprint, a released library's hash included.
- **Nothing verifies it yet.** The check reads only the binding of the record of exports. Format 1 takes the draft state alone, so no piece is final or published.
- **Form 1 has shipped in no release.** The capability has no release yet ([visual-communication:DEC-013-shipped-library-releases], Context), and no tag of the repository holds its folder. Every form the capability shipped is kept (DEC-006 point 6).

Two things reach the fingerprint from the accepted records:
- **A piece's folder gains files that are no input.** The version handed out is moved into it, and a published piece's copy may lie there (DEC-006 point 7).
- **A scene gains an input that is no file.** A component may show the version, its date, its language and the piece's state. How the check measures such text is left open (DEC-006 point 7). Four accepted points meet there:
  - the same files give the same answer ([visual-communication:DEC-002-files-and-validation] point 6)
  - the same files give the same scene (DEC-005 point 5)
  - findings are keyed by files (DEC-005 point 13)
  - overflow fails (DEC-005 point 14)

## Decision

**An export's fingerprint leaves out of `piece.yaml` only the named fields that can change no exported file. The findings key keeps `piece.yaml` whole, and no fingerprint reads files handed out or a copy. Form 1 may change in place until a release carries it. The check measures a fixed stand-in for a version's number and date, and an export refuses a real text that overflows.**

### 1. An export reads all of `piece.yaml` but the fields that can change no exported file

A piece has changed since an export where that export's fingerprint no longer verifies. Marking a version final and the check on a published piece's copy both read it so.
- **Left out.** The reading of `piece.yaml` leaves out these fields, and no other:
  - `state` and `pinned`, which say who moves the lock ([visual-communication:DEC-003-change-over-time] point 8)
  - `audience`, `shown` and `explains`, by which a check or a reviewer selects the piece ([visual-communication:DEC-001-visual-communication-discipline] point 3)
  - `accept-losses`, which says what the check stops repeating (DEC-005 point 9)
  - the field in which a published piece names the place of its copy (DEC-006 point 7)
- **What joins the list.** A field joins only where no value it holds can change a file an export writes. Every other field counts, the lock and the formats among them.
- **The state, which a component may show.** It stays on the list, since what a component shows is a fact of that export (point 5). A version keeps the state it was made in, and a published piece's copy is made while the piece is published.
- **A field added later counts.** It stays an input until a record names it here. A field on the list that a scene comes to read leaves the list the same way.
- **Every other input stands.** The piece's other own files are read whole, and so are each locked version's files and each font its scenes read.

### 2. The findings key keeps reading `piece.yaml` whole

- **Only the export's reading narrows.** The findings key, a produced output's record, written code's record and a released library's hash read the fields they read before.
- **The fields left out still change findings.** `accept-losses` decides which losses the findings record keeps, and a shown state is measured as it stands (point 5). A key without them would keep findings the files no longer give.
- **So the key stays as the record of the engine decides it** (DEC-005 point 13), a hash of every file its scenes were computed from. The folders of point 3 were never among those files.

### 3. Files handed out and a copy lie in folders no fingerprint reads

- **A folder for each.** The files of a version handed out lie in one folder within the piece's folder, and a published piece's copy in another. Each folder takes one fixed name in every piece.
- **Left out by place.** Every file under them is left out, whatever its name, as a produced output's pictures are.
- **From the export's fingerprint and the findings key alike.** No scene is computed from these files. Left in the key, each export that writes a copy would put the findings record out of date.
- **Never a source.** Nothing a scene reads lies in them. Should content come to name a file by its path, a path into them is refused.
- **A copy a documentation page shows** lies at the place the piece names, outside the piece's folder (DEC-006 point 7). No fingerprint reads it either.

### 4. Form 1 may change in place until a release carries it

- **While no release has carried it.** Every form the capability shipped is kept (DEC-006 point 6), and a form no release carried was never shipped. So the change that builds points 1 and 3 changes form 1 itself.
- **What carries it.** Any release made from a default branch that holds form 1 carries it, whichever versions that release moves.
- **What that leaves behind.** A record of exports written before that change no longer verifies, and nothing reads one yet. The next export writes one that does. Findings keys and library hashes keep their values, since no piece holds the folders yet.
- **If a release carries form 1 first,** that change writes form 2 instead. No release waits for it.
- **What form 2 then holds.** One number covers every kind, so form 2 differs from form 1 only as points 1 and 3 say. Every kept fingerprint verifies under the form it names, so no library hash is taken again. An export kept under form 1 reads `piece.yaml` whole, so a pin reads as a change there until the next export.
- **The form fixes the list and the folders.** Once a release has carried them, changing either is a new form.

### 5. The check measures a stand-in for what no file holds

Four facts of an export may show in a scene (DEC-006 point 7). A *stand-in* is one fixed text measured in place of a fact that no file holds.
- **The language and the state come from files.** Every scene shows them as the files hold them, so they need no stand-in.
- **A version's number and its date come from no file.** An export fixes them as it runs, and the next number is local to each clone.
- **A stand-in for each.** The check's scenes take one fixed text for the number and one for the date, in the form an export writes them. So the same files give the same answer on every machine, on any day.
- **Every scene a shared answer rests on takes them.** These are the check's scenes, those a render keeps findings from, and those a program's measured frames come from.
- **The findings record keeps what those scenes found,** under a key of files alone. So a render on any clone writes the same record.
- **What a person looks at shows real text.** A preview fills what this clone's next export would: its next number and today's date. Another clone may show another number, which harms nothing, since a preview is never committed. A before-and-after and the viewing step fill the same way.
- **A real text that overflows in a preview** is said in the render's output, and no record keeps it.
- **An export fills one number and one date.** They are the ones its record keeps, so every file of a version shows the same.
- **No fingerprint reads an export's facts.** The record of exports keeps the number, the time and the state, and each file's name holds the language. So a new number makes nothing stale.

### 6. An export refuses a real text that overflows where its stand-in fits

- **Measured where it is filled.** An export computes its scenes with the real text. It measures them as the check does, for a text that overflows its box and a component that gets less than it asks for.
- **Refused before any write.** An overflow that only the real text causes refuses the run. The refusal names the fact, its text and the element.
- **A library reserves no width.** A component declares no room for a fact, and a number that outgrows its box is met by the export that reaches it.
- **Where the stand-in overflows too,** the check reports it already (DEC-005 point 14), and the export runs as it does on any finding.
- **A refusal, not a finding.** The severity policy sets what a finding costs (DEC-002 point 7). A command may refuse what no finding reports, as an export refuses a stale output.

## Rationale

**Why a named list is left out, rather than read.** A list of fields to read would miss a later field a scene reads, so a stale copy would pass. A list left out fails closed: a slip costs a false "stale" that one export mends. Keeping the whole file costs that false "stale" at every change of state, or of a field nobody sees. On a published piece it fails validation, and the export that mends it draws the same files.

**Why `accept-losses` is on the list.** It sets what the check says, and no renderer reads it. Left in, accepting a loss on a published piece would fail its copy for a file that did not change.

**Why the findings key does not move.** The two mistakes cost differently. A findings record that does not verify has its scenes computed again, which costs time and fails nothing. A key that read too little would keep findings the files no longer give, and the check would trust them.

**Why folders.** A place is read from the path alone, as a produced output's pictures are. A name cannot tell a copy from a person's file, since a copy carries no number. A list of hashes would make a piece's inputs depend on the record of exports, which no fingerprint reads. Two folders keep the files that never change apart from those each export rewrites.

**Why form 1 may change in place.** The rule keeps every shipped form so that the fingerprints a project holds go on verifying. No project holds one from a release, and nothing verifies an export's fingerprint yet. Form 2 today would keep a second reading for good, for records nothing reads. If a release comes first, form 2 costs one reading and a wider schema, so no release need wait.

**Why a stand-in, and only for two facts.** One answer on every machine needs a text that depends on neither the clone nor the day. The language and the state already meet that, so they keep their real text. A measured frame takes a stand-in too, or each export's number could make a produced picture stale. The cost is that the check never sees the real text, which point 6 meets.

**Why a person sees real text.** A preview exists to show what the export will show, and it reaches nobody else. A render and an export then compute the scenes twice, only for a piece that shows a fact.

**Why an export refuses.** Nothing judges a file after it is made, and a file handed out cannot be mended. So the export is the last place the real text can be measured. A person mends a refusal by giving the text room. Where only a released library could give it, the piece moves its lock or places another component.

### Alternatives considered

- **A named list of the fields an export reads.** Rejected. A later field a scene reads would be missed, and a stale copy would pass.
- **Keeping `piece.yaml` whole.** Rejected. A change of state, or of a field nobody sees, would fail a published piece's copy.
- **A hash of the computed scene in place of files.** Rejected. It is exact, but the check would compute every scene (DEC-005 point 13), and a new engine would make exports stale.
- **The findings key narrowed with the export's.** Rejected. It saves some computing, and risks findings the files no longer give.
- **A name pattern, or the hashes the record of exports keeps, to leave out handed-out files.** Rejected, for the reasons above.
- **One folder for files handed out and a copy.** Rejected. Files that never change would lie among those each export rewrites.
- **Form 2 today, whether or not a release comes first.** Rejected. A second reading would stay for good, for records nothing reads.
- **Holding the release until form 1 changes.** Rejected. A release would wait on this change for a cost form 2 already meets.
- **A form for each kind of fingerprint.** Rejected. A second numbering would follow every kind, to spare one reading.
- **The check reading the next number and today's date.** Rejected. Its answer would differ between clones and between days.
- **The next number kept in a file the scene reads.** Rejected. Every export would put the findings record out of date, and the date would still lie in no file.
- **A width a library reserves for each fact.** Rejected. A number has no upper bound, and every library would owe a width.
- **An export that writes the overflow and says so.** Rejected. A file handed out would hold a broken line that no check ever reads.
- **A way past the refusal, as a person has past a stale output.** Not chosen. A stale picture is still a whole picture, and an overflow is a broken drawing.
- **A preview that fills the stand-ins.** Rejected. A person would see a text no export shows, and meet a real overflow only at the export.

## Implications

- **Edits to accepted records,** each made in place once this record is accepted, and citing it. Accepting this record accepts them (COR-066 point 5).
  - **The record of work outside the engine and outputs, point 6, "An input".** An input is a file, or a part of a file of the capability's format named by its path of keys. A form may read such a file without keys it names. The rest of the bullet stands.
  - **Its point 6, "Its version and hash".** A version also fixes the keys a reading leaves out, and the folders a piece's own files leave out.
  - **Its point 7, "The piece may show it too".** The check measures a version's number and its date by a stand-in, so the same files still give the same answer. That replaces the last sentence, and the sentence on a preview stands.
  - **Its point 7, "The record of exports".** The fingerprint is of what its scene was computed from: every such file, with `piece.yaml` read as this record's point 1 says.
  - **Its point 7, "What is committed, in the piece's folder".** The version handed out and a published piece's copy each lie in a folder of their own there, which no fingerprint reads.
  - **Its Implications, "Two branches".** Where a piece shows its version, the other version is exported again under the next free number, since its files hold the old one.
  - **The record of the engine and its plugins, point 5, "Computed, never committed".** The same files give the same scene where it takes the stand-ins. A scene drawn for a person or an export takes the real text.
  - **Its point 14, "Fails validation".** The overflow line adds: "An export refuses an overflow that only a fact's real text causes."
- **These need no edit:**
  - The record of files and validation's point 6, since the check still computes from the files alone.
  - The record of the engine's point 13, since its key stays a hash of files, and its findings come from the stand-ins.
  - The record of work outside the engine's points 5 and 8, whose words hold once this record says what an export read.
- **The pages.** The capability's reference pages on checks, outputs and components anchor these points, so they may owe answers once the edits land. No page changes its text in this change, since the changes below build what this record decides.
- **The change that builds the reading** carries out points 1, 3 and 4. It fixes the names of the two folders and of the copy's field, so that field needs no new form when it arrives. It reads whether a release has carried form 1 as it merges. Should form 2 be needed, the fingerprint's schema widens from one form to two, an addition the format allows (DEC-003 point 3).
- **The change that shows an export's facts** carries out points 5 and 6. It fixes each stand-in's text, which the capability's reference holds, wide enough that a usual real value fits. It adds no input to any fingerprint, so it needs no new form.
- **A later record of [project-kit#2572](https://github.com/aleskalfas/project-kit/issues/2572)** decides what marking final does with a version the piece changed after, reading "changed" as point 1 says.
- **A renderer that draws into a lasting medium** comes later (DEC-005 point 11). The change that builds it decides which text it fills.
- **A later reading of content** may write under the methodology's container key in a content file (DEC-002 point 4). Content files are read whole, so that write reads as a change until a record leaves the key out.
