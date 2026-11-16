---
id: DEC-063
title: A check's silence counts only where it judges
status: proposed
date: 2026-11-16
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a check that names nothing at a place has not always judged it. It may never compare that kind of place: the checks of boxes compare only the parts one group holds directly, so they say nothing of a title in one group beside a paragraph in another. Or it may judge nothing there: the check of edges that nearly line up finds nothing near where a brand gives no step of space. A reader that takes such a silence for "clean" skips a sum it should make. So each check says, in its entry in the capability's list of checks, which kinds of place it judges and which it leaves out. Where it could judge nothing at a place of a kind it judges, it states that in the piece, as a fact. A check's silence at a place then counts as judged and clean only where the place is of a kind the check judges and no such statement covers it. Everywhere else the check did not judge, and the reader does what the check's own record says for that case. Where the reviewer reads the findings and each check's reach is [visual-communication:DEC-062-checks-beside-the-frames]'s.

## Context

[visual-communication:DEC-046-faults-lower-grades] point 3 adds two checks that measure the boxes of siblings, edges that nearly line up and boxes that overlap. Where they ran, the reviewer does no sums over the frames, and where they did not, it reads the offsets from the frames. Point 5 of the same record has a check of a text's size state, as a fact, where it judged no text's size: once in its entry for a kind of text it never judges, and in the piece for a text it meets and cannot judge. No record says the same of any other check, nor reads a check's silence place by place.

A check that ran on a scene can be silent at a place it did not judge, in three ways:
- **A kind of place it never compares.** A header group holds a title, and a body group holds a paragraph. The groups' left edges agree, the title is set 0 px in and the paragraph 3 px, under a brand whose smallest step of space is 4 px. The checks of boxes compare the two groups, and the parts inside each only with each other, so they never compare the title with the paragraph. A line that stops 2 px short of the part it joins is passed over too, since the checks leave out lines.
- **A line its own rule passes over.** The check of edges that nearly line up does not report a near miss on one line of an axis where the pair lines up on another line of it (DEC-046 point 3). Two cards in a row whose tops agree, 200 and 203 px tall, are not judged on their bottoms.
- **A place it could not judge.** The same check finds nothing near at a key whose brand gives no step of space, since it measures nearness against that step.

A reader that took any of these silences for "judged and clean" would do no sums there, and pass an offset: the craft the first calibration found the review weak on (DEC-046, Context).

The words it uses:
- **A check** is a measurement a command makes on every render, with no judgement. Its finding fails, asks for attention and names who is to act, or states a fact, which asks no act ([visual-communication:DEC-002-files-and-validation] point 7). Its *label* is the name its findings carry.
- **The capability's list of checks** is its page that lists each check and its findings. A check's *entry* is its row there.
- **A scene** is a piece's pages as the engine lays them out, in one language and at one combination of its sizes, which a *key* names with its modes ([visual-communication:DEC-004-brands-and-notations] point 3).
- **A place** is what a finding names in one scene: an element, a pair or group of elements, or content.
- **A kind of place** is a class of places an entry can name, such as two siblings, two parts of different groups, a line, or a text inside a picture.
- **A check's reach** is the kinds of place it judges, for what it measures, and the kinds it leaves out.
- **A reader of the checks** is whoever reads what a check found so as to leave to it what it measures. The reviewer is one: the capability's agent that judges the drawn pages and reports what no check measures ([visual-communication:DEC-015-viewing-step-and-reviewer] point 7).
- **Siblings** are the parts one part holds directly. **The frames** are the file beside each image of the viewing step that gives every drawn part's box (DEC-046, Context).

## Decision

**Each check states its reach in its entry, and states as a fact where it could judge nothing at a place of a kind it judges. A check's silence at a place counts as judged and clean only where both allow. At every other place it did not judge, and the reader does there what the check's record says.**

### 1. Each check's entry states its reach

- **What it judges, and what it leaves out.** A check's entry says which kinds of place it judges, for what it measures, and which it leaves out. The checks of boxes judge siblings. They leave out two parts of different groups, lines and arrows, a group that draws only lines, an element of no area, and a page.
- **What its own rule passes over is left out.** A kind of place the check never reports, by a rule of its own, counts among what it leaves out, and its entry names it. The check of edges that nearly line up names the other lines of an axis on which a pair lines up on one line, and the insets on an axis of a held part that lies on one edge of its holder.
- **Once, in the entry.** A kind of place the check leaves out in every piece is stated there alone, never in each piece, as DEC-046 point 5 has the check of a text's size state a kind of text it never judges.
- **The record that decides a check decides its reach.** This point has the entry state it.

### 2. Where it could judge nothing, it states so, as a fact

- **At a place of a kind it judges.** A check that could judge nothing at such a place states so in the piece, with the reason. The check of edges that nearly line up does so at a key whose brand gives no step of space. DEC-046 point 5 has the check of a text's size do so for a text whose size or minimum it cannot work out. This point has every check the capability ships do so, whichever record decides it.
- **What a statement covers.** A statement names how far it reaches: one place, a page, a key or the scene. It covers each place there of a kind the check judges. So the check of edges that nearly line up states it once at each such key, and covers every pair and group of siblings at that key.
- **A fact.** It asks no act of the project, since nothing in the piece's files is wrong: a brand may give no step of space by choice. A reader that relies on the check judges the places it covers itself, as part of its own reading, which no finding asks of it (DEC-002 point 7). So it fails nothing, and names no one to act.
- **A finding of its check, like any other.** The check's code states it, wherever that code runs. A render keeps it in the piece's findings record, and validation shows it as it shows each finding that record holds while its key verifies ([visual-communication:DEC-005-engine-and-plugins] point 13). A findings record a release wrote before its check made the statement holds none of it, so validation shows none until the piece's next render. Where each reader reads the statement is the record of that reader's reading.

### 3. How a check's silence is read

Per check, and per place:
- **Judged and clean:** a place of a kind the check's reach judges, in a scene the check ran on, where the check gave no finding and no statement of its covers the place. It is judged only for what that check measures: a pair of siblings the check of boxes that overlap judged is judged for overlap, not for its edges.
- **Not judged:** every other place. That takes in a kind of place the reach leaves out, a place a statement covers, and every place in a scene the check did not run on.
- **By the reach of the code that judged.** A reader reads each check's reach as the code that judged the place states it, since the reach may change from one release, or one commit, to the next. Where the reviewer reads it, and the findings, is DEC-062's.

### 4. Where a check did not judge, the reader does what the check's record says

- **The checks of boxes.** Where one of them did not judge a place, the reviewer reads from the frames there what that check measures: the edges, centres, insets and gaps of siblings for the check of edges that nearly line up, and the overlap of their boxes for the check of boxes that overlap (DEC-046 point 3).
- **A check of a text's size.** Where it judged no text's size, the review's report names the gap (DEC-046 point 5).
- **Every other check.** What it measures is the reviewer's to judge at that place, as is everything no check measures (DEC-015 point 7).
- **A passing check is one that judged.** A drawing disagrees with a passing check only at a place the check judged and found clean ([visual-communication:DEC-030-design-agents] point 6). Where the check did not judge the place, a fault the page shows there is of its own kind, and blames no check.

## Rationale

**Why silence is read per place and per check.** A check that ran on a scene names nothing at a place it never compares, nor at one it could not judge. Read per scene, its silence says that the title and the paragraph of two groups were compared, when they were not (Context). Read per place but not per check, a key where the check of edges that nearly line up judged nothing would lose the overlaps the check of boxes that overlap still judged there. Only the place and the check together say what was measured.

**Why the entry states the reach.** The reach is the check's, and changes when its code changes. Written once beside the check, it stays one statement, in step with the check, that every reader reads alike. A reader that kept its own account of each check would drift from it.

**Why what a check's own rule passes over counts as left out.** DEC-046 point 3 has the check of edges that nearly line up pass over a near miss that follows from the line chosen, so that an icon and a label centred in a row are not called near at their tops. Two cards whose tops agree and whose heights differ by 3 px are passed over by the same rule, yet whether they are a fault is a judgement on the image. Read as left out, those lines go to the reader, who measures them, rather than to a silence that seems to pass them.

**Why a place it could not judge is stated in the piece.** Whether a brand gives a step of space at a key is the piece's brand's, and differs from piece to piece and key to key, so no entry could state it. Only the check knows where it judged nothing, so it states it where that happens. A kind of place it leaves out in every piece is stated once, in its entry, so that no piece carries a fact for it (DEC-046, "Why the check says where it judged no size").

**Why a fact, and not a call for attention.** A call for attention expects someone to act, and names who (DEC-002 point 7). Nothing in the piece is to mend: a brand that gives no step of space may mean it. A call for attention would ask the piece's author to act on every piece drawn under such a brand, for ever. The reader judges the places it covers as part of its reading, as it does wherever no check judges.

**Why every check, in a record of its own.** The reading of silence holds for every check a reader leans on, not only the two of boxes and the one of a text's size, and for every reader, wherever it reads the findings. Each later check's record rests on it, and looks for it under what it decides, not under the record of the viewing step. DEC-062 decides where the reviewer reads the findings and each check's reach. This record decides how a reader reads them.

**Why validation shows the statement too.** It is the check's own finding, made by the code a render runs. A person who runs the check sees where it judged nothing, as the reviewer does. A record written before a check made the statement holds none of it, so the two may differ until the next render, and each shows what its own run found.

### Alternatives considered

- **Silence read per scene,** as DEC-046 point 3 words it. Rejected: it reads the title and the paragraph of two groups as compared (Context).
- **The check of edges that nearly line up judges every line of an axis.** Not taken: DEC-046 point 3 decides that a near miss which follows from the line chosen is not reported. The lines it passes over go to the reader instead (point 1).
- **A call for attention where a check could judge nothing.** Rejected, for the reason above.
- **Each kind of place a check leaves out stated as a fact in every piece.** Rejected: it would repeat a fact of the check in every piece, as DEC-046 point 5 found for a kind of text the check of a text's size never judges.
- **The reach kept in the reader's own instructions,** such as the reviewer's body. Rejected: the reach is the check's, and changes with its code, so a copy elsewhere would drift.
- **These points in DEC-062.** Rejected: they hold for every check and every reader, whatever DEC-062 decides of the viewing step, and a later check's record must find them.

## Implications

- **This change adds a record, and changes nothing a project could observe.** It declares no changeset and owes no migration. The work that builds it changes the list of checks and a check's findings, and declares its own.
- **Accepted with DEC-062,** in the same change. Each rests on the other: this record reads a check's silence by the reach the code that judged states, which DEC-062 has the viewing step's report carry, and DEC-062 has the reviewer read the report as this record reads a check's silence.
- **Edits to accepted records,** made in this change once this record is accepted, each citing it (COR-066 point 5). Accepting this record accepts them.
  - **DEC-002 point 7,** the bullet "Attention or a fact". After "such as a piece that uses a component its library may still change in any release", it comes to add: "A check's statement that it could judge nothing at a place, or at every place of a page or a key, is such a fact: a reader that relies on the check judges those places itself (refinement per [visual-communication:DEC-063-where-a-check-judges] point 2)."
  - **DEC-046 point 3,** the bullet "Edges that nearly line up". After "Lines and arrows are left out, as from the check of overlaps.", it comes to add: "At a key whose brand gives no step of space, nothing is near, and the check states as a fact that it judged nothing there (refinement per [visual-communication:DEC-063-where-a-check-judges] point 2)."
  - **DEC-046 point 3,** the bullet "The reviewer judges each place the checks name". Its sentences "Where the checks ran, it does no sums over the frames. Where they did not, it reads the offsets from the frames." come to read: "Where one of the two checks judged a place, as [visual-communication:DEC-063-where-a-check-judges] point 3 reads a check's silence, from the viewing step's report ([visual-communication:DEC-062-checks-beside-the-frames] point 3), it does no sums over the frames there for what that check measures: the edges, centres, insets and gaps of siblings for the check of edges that nearly line up, and the overlap of their boxes for the check of boxes that overlap. Where a check did not judge a place, it reads from the frames there what that check measures (refinement per [visual-communication:DEC-063-where-a-check-judges] point 4)." The rest of the bullet stands.
  - **DEC-046 point 5,** the bullet "Who says where no text's size was judged". After its last sentence, "Either way the gap is named where it stays open.", it comes to add: "Every other check the capability ships states too where it could judge nothing, and states in its entry the kinds of place it judges and leaves out (refinement per [visual-communication:DEC-063-where-a-check-judges] points 1 and 2)."
  - **DEC-046's Implications,** in the reviewer's body's list, the item "How the reviewer judges the places the two checks name." comes to read: "How the reviewer judges the places the two checks name, and the places each does not judge, read as [visual-communication:DEC-063-where-a-check-judges] reads a check's silence."
- **Read against this record, and left as they stand:**
  - DEC-002 point 6's "Two levels", whose "Each record decides the checks it owns" holds: each record decides what its check judges, what it finds and how severely. This record adds two statements every check makes of its own reach, a duty shared across checks as DEC-046 point 5's is, which that sentence does not exclude;
  - DEC-005 point 13, since a statement that a check could judge nothing is a scene finding the findings record keeps like any other, and the record gains no field;
  - DEC-030 point 6's "A fault", since "a passing check" is a check that judged a place and found it clean, as point 3 reads it;
  - DEC-030 point 7's "With the checks" and DEC-015 point 7's "Its remit", since what a check measures stays the check's where it judged, and is the reviewer's where it did not, as what no check measures is;
  - DEC-046 point 3's "Edges that nearly line up", whose sentence on a near miss that follows from the line chosen stands: point 1 has the entry name those lines as left out, and the reviewer measures them.
- **The work that builds it,** under [project-kit#3335](https://github.com/aleskalfas/project-kit/issues/3335), in one change with DEC-062's:
  - each check's entry in the list of checks states its reach, where it does not yet. The entry of the check of edges that nearly line up names as left out the lines of an axis it passes over, and the insets of a held part on its holder's edge;
  - the check of edges that nearly line up states, as a fact, each key whose brand gives no step of space;
  - the reviewer's body reads a check's silence per check and per place, as point 3 says, and reads from the frames what a check that did not judge a place measures, as point 4 says;
  - tests show that a key with no step of space gives the statement, and that a findings record holds it like any other scene finding.
