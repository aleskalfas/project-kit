---
id: DEC-078
title: The designer releases the project's own library, and no release hides a piece's failure
status: proposed
date: 2026-11-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the graphic designer runs the command that releases a version of the project's own library itself, rather than leaving it to the person. It does so where a piece needs the version released: once the person's ship call sends a piece that locks it to its audience as a final or published piece, which may lock only released versions, where a published piece is to take it, or where the person asks. Before it releases, it holds the version to the bar the project keeps for that library, and the release lands only with the change that holds it, which is read by that bar again. A shipped library's release stays with whoever maintains the capability. No release, the designer's or anyone's, turns a failure into a call for attention: a fault that a piece's scene shows inside a version of the project's own library fails whether or not the version is released, since the project corrects it in a new version that the piece's lock then names. That covers a fault only one piece's content triggers, which the release, reading the version alone, computes no scene to see.

## Context

[visual-communication:DEC-066-meant-overlaps] left to a record of its own whether the designer may release a version of the project's own library ([project-kit#3398](https://github.com/aleskalfas/project-kit/issues/3398)). Its reviews found that such a release turns a failure the designer's loop found into a call for attention, a way for a bad design to pass.

What holds:
- **What the designer writes and runs.** It writes a version not yet released of the project's own library, and never a released one. What commands write, a release among them, stays theirs, and the designer runs those commands where its body says ([visual-communication:DEC-030-design-agents] point 5). Its body leaves releasing a library version to the person, and names the command. Where the capability is authored, releasing a shipped library's version being built stays with whoever maintains the capability (DEC-030 point 5, [visual-communication:DEC-013-shipped-library-releases] point 1).
- **The owner's bar.** A form other pieces need goes into the library that holds such forms, in the project's own library into a version not yet released, and the owner judges it by the bar that owner keeps (DEC-030 point 4). The project owns its own library.
- **Which pieces need a release.** A draft may lock a version not yet released, and its lock moves at each render to the newest versions the project holds. A final or published piece locks only released versions ([visual-communication:DEC-003-change-over-time] point 8). So a piece is marked final or published only once each version of the project's own library that its lock names is released.
- **What a release reads.** The release reads the version in full, alone, and refuses a finding that fails. It computes no scene ([visual-communication:DEC-014-own-library-needed-release] point 1).
- **How severe a finding is.** A finding fails where an invariant is broken in a file the project can correct, a version of its own library not yet released among them. A fault inside a released library version never fails, since only its owner corrects it, in a new release, and it asks for attention, naming that owner ([visual-communication:DEC-002-files-and-validation] point 7, [visual-communication:DEC-005-engine-and-plugins] point 14). The level is worked out each time the check reads the finding, from the list's mark of release, and is never stored (the capability's list of checks, "A library version the project does not correct"). So a release changes it at once.
- **The designer's loop** mends each failure of a check before any review ([visual-communication:DEC-070-ship-call-and-one-round] point 2).

So a fault inside a component of the project's own library that a piece's scene shows fails while the version is not yet released, asks for attention once it is released, and leaves the loop nothing to mend. The release does not see such a fault where only some piece's content triggers it, such as a division by zero over an empty list, or a stand-in for an export's fact too long for its box ([visual-communication:DEC-016-what-an-export-reads] point 5), since it computes no scene. A person's release made while a loop runs does the same, and so does an edit to a piece that triggers a fault inside a version released before.

The words it uses:
- **The project's own library** is a library the location's list names from the project's own source, neither one the capability ships nor one from another repository (DEC-003 point 4).
- **The release** is the capability's command that releases a version of the project's own library (DEC-003 point 6).
- **A finding a piece's scene shows** is one the check gives from a scene it computes for a piece. A *finding of a version alone* is one it gives as it checks a library version with no piece (the capability's list of checks, "What each run judges").
- **The person, the ship call and the loop** are DEC-070's.

## Decision

**The designer runs the release of a version of the project's own library where a piece needs that version released, once it has held the version to the owner's bar, and the change that lands the release is read by that bar again. A finding that a piece's scene shows inside a version of the project's own library fails, released or not, wherever it fails while the version is not yet released, so no release turns such a failure into a call for attention.**

### 1. The designer releases the project's own library, and no other

- **It runs the release.** The release of a version of the project's own library is among the commands the designer runs (DEC-030 point 5), as points 2 and 3 say. It runs it itself, and does not leave it to the person.
- **Never by hand.** It writes no released version, and no mark of release in the list, which the release alone writes (DEC-030 point 5).
- **No other library.** Whoever maintains the capability releases a shipped library's version being built, where the capability is authored (DEC-013 point 1), and a repository's owner releases that repository's versions. The designer releases neither, and the release refuses both.

### 2. It releases where a piece needs the version released

- **When.** It releases a version of the project's own library not yet released in one of three cases:
  - the person's ship call sends a piece that locks the version to its audience as a final or a published piece, which locks only released versions (DEC-003 point 8, DEC-070 point 1);
  - a published piece is to take the version, by a move of its lock that the person makes (DEC-003 point 8);
  - the person asks for the release.
- **Not before.** A draft may lock a version not yet released, so no round needs a release (DEC-003 point 8). A release fixes the version (DEC-003 point 6), so each mend the person asked for after it would take a new version.
- **Where the release refuses,** it mends the version and runs the release again. Where a mend changes what a piece the person shipped draws, that piece goes back to the person, whose ship call was on the piece as it stood (DEC-070 point 1).
- **It tells the person** of each version it released, among what it changed (DEC-030 point 2).

### 3. The owner's bar acts before the release and before it lands

The project owns its own library, so the owner's bar is the one the project keeps for it (DEC-030 point 4). It acts on a version the designer releases twice:
- **Before the release, through the designer.** The designer holds each change it made to the version to that bar, where the project keeps it in writing, as it holds any extension of a library (DEC-030 point 4). It releases no version with a change that falls short, and names what falls short to the person.
- **Before the release lands, through whoever judges the change.** The release lands only with the change that holds it, and whoever judges that change for the project reads the version by the owner's bar before it lands. A version that falls short there takes its mend in a new version, as any released version does (DEC-003 point 6), and leaves the change once no lock names it (DEC-003 point 4).

### 4. A release leaves failing what a piece's scene shows failing

- **The rule.** A finding that a piece's scene shows inside a released version of the project's own library takes the level it takes while that version is not yet released, where that level is to fail. So no release turns such a failure into a call for attention, whoever runs it, and whether or not the piece's loop runs.
- **The project corrects it.** It corrects such a fault in its own files: in a new version of its library, which the piece's lock then names. A draft's next render takes the new version, and a person moves a pinned draft's or a published piece's lock to it (DEC-003 point 8). A fault in its own library that a piece shows is the project's to correct, released or not, so the finding fails (DEC-002 point 7).
- **The faults a release cannot see.** It holds for a fault every piece shows, and for one only some piece's content triggers, such as a division by zero over an empty list, or a stand-in for an export's fact too long for its box. The release reads the version alone and computes no scene, so it sees neither. It holds too for a fault that an edit to a piece triggers inside a version released before.
- **What it leaves as it stands:**
  - a finding of a version alone, which in a released version asks its owner for attention (DEC-002 point 7). The release reads the version in full and refuses each such finding that fails (DEC-014 point 1), so no release hides one;
  - a finding inside a released version of a library the project does not own, a copy of a shipped library or a version from another repository, which asks that library's owner for attention (DEC-002 point 7, DEC-013 point 6);
  - a finding that does not fail while its version is not yet released, a call for attention or a fact, and the label that a released version's word gives in validation (DEC-066 point 2, [visual-communication:DEC-053-letters-across-lines] point 4);
  - a released version whose folder no longer matches its release, whose findings fail (DEC-002 point 7, DEC-003 point 9);
  - a final piece, whose scenes the check does not compute (DEC-002 point 7).
- **Read where the finding is read.** The level is worked out each time the check reads the finding, from the list's mark of release and the library's source, and is never stored. So a scene and a piece's findings record stay as they are (DEC-005 points 5 and 13), and validation and the viewing step read the level alike.

## Rationale

**Why the designer runs the release.** The release is a command's write on a version the designer built. It reads the version in full and refuses what fails (DEC-014 point 1), so the person who runs it adds no check of the files. What the person's own running of it gave was the owner's judgement of the version before the version was fixed. Point 3 keeps that judgement, before the release and before it lands, and point 4 takes away what a release could hide, whoever runs it.

**Why where a piece needs it.** A draft locks a version not yet released, so a release serves only a piece that may lock nothing else, or a move of a published piece's lock. Before the ship call, the person may ask for mends, and each mend to a released version takes a new one. After it, the piece stands as the person shipped it, so the release fixes what the person saw.

**Why the bar acts twice.** A release fixes a version for good (DEC-003 point 6), so a bar that acted only after it could refuse a version only by a new one. The designer holds the version to the bar first, where the project writes the bar down, as it does with any extension. Where the project writes none, or the designer misreads it, whoever judges the change that holds the release reads the version, as every file the designer changes is read before it lands. A version that falls short there leaves before it lands, so no landed piece locks it.

**Why a failure a piece's scene shows fails, released or not.** A release fixes a version. It does not move a fault in the project's own library out of the project's reach, since the project corrects it in a new version that the piece's lock names. DEC-002 point 7 sets a finding's level by whether the project can correct it, so the level stays the same across the release. Read so, the hole closes for every release: the designer's, a person's made while a loop runs, and one made before an edit triggers the fault. A check at the release could close only the first, and only for the pieces it computed.

**Why the line runs at the scene.** The release reads a version in full, alone, and refuses what fails there (DEC-014 point 1). What it cannot read is what a piece's content does with the version, which only the piece's scene shows. A finding of a version alone is another matter: a new version leaves the old version's finding where it lies, and only the old version's removal clears it, which a lock may forbid. A library the project does not own it cannot correct in a new version of its own, so a fault there asks that library's owner for attention (DEC-002 point 7).

**Why DEC-002 point 7 is refined, and not overturned.** The point decides that a finding fails where the project can correct it in its own files, and never fails where it cannot. Its example of a fault inside a released library version, "which only its owner corrects in a new release", rests on that reason. Where the library is the project's own and a piece's scene shows the fault, the project is the owner, and corrects it in a new version and the piece's lock, which are its own files. So the edit narrows the example to what its reason reaches, and adds that case to what the project can correct. The decision stands, so the edit refines the point in place (the decisions README, "Refining an accepted record"). DEC-005 point 14 follows DEC-002 point 7, and its example is narrowed the same way.

**Why DEC-030 points 4 and 5 are refined.** Point 5 has the designer run a command where its body says, and this record says where for the release. Point 4 has the owner judge an extension by its bar, and this record says how that bar acts on a version the designer releases. Neither decision changes.

### What it costs

- **A published piece fails** where it locks a released version of the project's own library whose fault its scene shows, where it asked for attention. Its mend is a new version, its release and a move of its lock that the person makes (DEC-003 point 8). A pinned draft's mend takes the person's move too. A change to the capability that adds or tightens a check can so fail such a piece in a project that changed nothing else.
- **A version spent.** A released version that the owner's bar refuses before it lands takes a new version for its mend.
- **A bar in writing.** The designer applies the owner's bar only where the project writes it down. Elsewhere the bar acts only where the change lands.
- **A shipped piece sent back.** Where the release refuses, and the mend changes what a piece the person shipped draws, the person makes the ship call again.

### Alternatives considered

- **The release left to the person,** as the designer's body has it. Not taken: the person runs a command the designer can run, and point 3 keeps what the person's running gave, the owner's judgement before the version is fixed.
- **The designer releasing each version once it judges it done,** with no piece needing it. Not taken: a draft needs no release, and a version released before the person's ship call takes a new version for each mend the person asks for.
- **The release computing the scenes of each piece that locks the version, and refusing a failure it finds inside it.** Not taken: it would not see a fault that an edit made after the release triggers, and it would compute scenes in a command that reads a version alone (DEC-014 point 1).
- **A failure a piece's scene shows kept failing at a draft alone.** Not taken: the release most often serves a piece the person sends to its audience, and at a published piece that locks the version, the failure would turn into a call for attention at the release.
- **A mark that a piece's loop runs, read by the check.** Rejected: validation reads the files as they are, no file records a loop, and the designer would write the mark it is judged by.
- **Every finding inside a released version of the project's own library failing, a finding of a version alone included.** Not taken: a new version leaves the old version's finding where it lies, so only the old version's removal would clear it, which a lock may forbid. A change to the capability that tightens a check would fail every project that holds an older version.
- **Every finding the check gives as it judges a piece.** Not taken: beyond its scenes, the check reads for a piece its lock, the libraries its lock names, which the release reads in full itself, and what the person chose at an export, such as a copy whose fact's text the person let through (DEC-016 point 6). The scene is what a release cannot read at all.

## Implications

- **Edits made in this change once this record is accepted** (COR-066 point 5). Accepting this record accepts them. Each refines its record in place and takes a forward pointer to this record, save the item that leaves DEC-066's Left open.
  - **DEC-030 point 4, "Extend a library, through its owner's bar":** after "The owner judges it by the bar that owner keeps, such as the starter's bar for entry (DEC-007 point 3).", it comes to add: "In the project's own library, that bar acts on a version the designer releases before the release, where the designer holds the version to it, and before the release lands, where whoever judges the change that holds it reads the version by it (refinement per [visual-communication:DEC-078-designer-releases-own-library] point 3)."
  - **DEC-030 point 5, "What commands write":** after "It runs those commands where its body says.", it comes to add: "It runs the release of a version of the project's own library itself, where a piece needs that version released, and never the release of a library the capability ships or of another repository's (refinement per [visual-communication:DEC-078-designer-releases-own-library] points 1 and 2)."
  - **DEC-002 point 7, "What fails":** after "The project can correct its pieces, its locks, its configuration and any version of its own libraries not yet released.", it comes to add: "It can also correct a fault that a piece's scene shows inside a released version of its own library, in a new version of that library and the piece's lock that names it, so such a finding fails as it does in a version not yet released (refinement per [visual-communication:DEC-078-designer-releases-own-library] point 4)."
  - **DEC-002 point 7, "What never fails":** "Examples are a fault inside a released library version, which only its owner corrects in a new release," comes to read "Examples are a fault inside a released library version, which only its owner corrects in a new release, save one that a piece's scene shows inside the project's own library (refinement per [visual-communication:DEC-078-designer-releases-own-library] point 4),". The rest of the sentence stands.
  - **DEC-005 point 14's lead:** "Elsewhere, as in a released library version, it asks for attention and names who can correct it (COR-055 points 1 and 4)." comes to read "Elsewhere, as in a released version of a library the project does not own, it asks for attention and names who can correct it (COR-055 points 1 and 4). One that a piece's scene shows inside a released version of the project's own library fails (refinement per [visual-communication:DEC-078-designer-releases-own-library] point 4)."
  - **DEC-066's Implications, "Left open":** the item "The designer's release" goes, since this record decides it.
- **Read against this record, and left as they stand:**
  - DEC-030 point 5's "Never", since the designer writes no released version and no mark of release, which the release writes; its "Where the capability is authored", since a shipped library's release stays with whoever maintains the capability; and point 2's "What it tells the person", under which it names each version it released;
  - DEC-003 point 6, whose release of a project's own library reads the version in full and fixes it, whoever runs it; and point 8, whose states say which pieces need a release and who moves each lock;
  - DEC-014 point 1, since the release reads a version alone and computes no scene, which point 4 leaves as it is;
  - DEC-013 points 1 and 6 and DEC-003 point 9, since a shipped library's release, and the level of a finding inside its copy, stay as they are;
  - DEC-066 point 2 and DEC-053 point 4, whose labels a released version's word gives in validation alone. A release by the designer gives them as a person's release does, and the review reads neither word, so no design passes by them;
  - DEC-066's "What it costs", "A mark written by hand gives the fact too", since the designer writes no mark by hand;
  - DEC-016 point 6's "What that leaves" and DEC-006 point 8's items on a published piece's current copy made with a number or a date let through, since that finding is no finding a piece's scene shows: the person let the text through at an export, which the designer leaves to the person;
  - DEC-070 points 1, 2 and 4, since the ship call stays the person's, the round mends each failure of a check before any review, a failure inside a released version of the project's own library among them, and a move of a lock only a person moves is one the designer names to the person.
- **The work that builds it,** under [project-kit#3398](https://github.com/aleskalfas/project-kit/issues/3398), in this change once this record is accepted:
  - **the check's reading:** a finding a piece's scene shows that lies inside a released version of the project's own library, and fails in a version not yet released, reads as failing, through the one reading that applies a finding's level in validation and in the viewing step. A finding of a version alone, and a finding inside a copy of a shipped library or a version from another repository, read as they do;
  - **the capability's list of checks:** its section "A library version the project does not correct", and each row whose level names a released library, such as `text-overflow`'s sentence on a stand-in, say so;
  - **the designer's body:** releasing a version of the project's own library moves from what it leaves to the person into what it runs, by points 1 to 3. It says that it mends a failure inside a released version of the project's own library in a new version, and that a shipped library's release stays with whoever maintains the capability. Its reads gain this record. This is the account of what the designer runs and what it leaves to the person;
  - **tests:** a component of a version of the project's own library not yet released, whose fault only a piece's content triggers, a division by zero over an empty list and a stand-in for an export's fact too long for its box, fails at a draft that triggers it, and at none that does not. The release releases the version, refusing nothing, and the finding fails at that piece after the release too, in validation and in the viewing step's report. The same fault asks its owner for attention inside a released copy of a shipped library and inside a released version from another repository;
  - **its changeset:** the change moves a finding's level, so a project's validation may fail where it asked for attention, and it declares that in its changeset for the capability's next release. It owes no migration, since no file a project holds changes shape (COR-010).
- **A person merges it.** The change widens what the designer runs, so its merge waits for a person at every level of the delegation setting (COR-072 point 7).
