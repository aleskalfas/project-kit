---
id: DEC-052
title: A piece gets its pass only on library parts with no finding left open
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a piece draws with things it does not own: components, a brand's roles and a notation's signs, from its libraries. Each is a *library part*. A finding on a library part comes from one of three sources: the check on the library's own pages, the library's last review, or a person's word. That person is the library's owner or, for one project alone, whoever answers for the libraries that project receives. The finding is *open* until it ends, or until a person accepts the part with it. A piece that uses a library part with an open finding gets no pass, and no copy of it reaches readers. Drafts are never stopped: the question is asked when the piece's pass is made or the piece is published, and only of the library parts the piece really uses. **A library that was never reviewed refuses nothing,** and each pass that rests on one says so. Two things count without a review: a check that fails on the library's own pages, and a finding the library's owner has had written down. Each finding ends only through the kind of source that opened it: a check's when the check passes, a review's when a later review lists none, having read the part in the same variant after the files the part is drawn from changed, and a person's only by that person's word, shown the picture of the changed part. Changing the part ends nothing. What a library must show before it counts as reviewed is decided later, once a first library has been through a review.

## Context

A redesign was once built on libraries whose own review listed open findings. The pages inherited those faults, and a fix made on a page hid them. Nothing asked about the libraries, because the design process orders only a piece's own stages ([visual-communication:DEC-047-design-process]).

A library is shared. Many pieces, in many projects, use the same version, and it changes on its own schedule ([visual-communication:DEC-003-change-over-time]). So its state cannot be a stage of any one piece.

Three things limit what can be asked:
- **Drafting must go on.** A library is often mended while the pieces that need it are drawn. Refusing to start a page until every library is clean would stop both.
- **A piece uses a few library parts.** A finding on a component a piece never draws says nothing about that piece.
- **No library has yet been through the process.** So nobody has seen the review report of a library's own pages, and what such a review must cover cannot yet be stated from a case. The review that listed the open findings above was made before the process, and is no evidence of it.

## Decision

**A piece gets a pass, and reaches readers, only where no library part its pages use has a finding left open.**

### 1. The library parts a piece uses

- **A library part** is one thing a library offers: a component, a role of a brand, or a sign of a notation.
- **The library parts a piece uses** are those a page of the piece draws with, at the version the piece's lock names. A command reads them from what each page's stage read (DEC-047 point 4).
- **A local component is not one.** It is the piece's own, and is read with the piece's pages.

### 2. Asked when the pass is made and for readers' copies, never at a stage's start

- **When the pass is made.** A piece gets a pass only where, at that moment, no library part it uses has an open finding ([visual-communication:DEC-048-stage-evidence-and-refusals] point 4). The pass notes the state of each library part, by the part's digest, and whether the library's last review report has read the part. So a part that was accepted and never reviewed still reads as not reviewed.
- **A piece let through without a pass names what kept it from one.** The person's acceptance of such a piece names each open finding on a library part the piece uses, shown with its image (DEC-048 point 4).
- **For readers' copies.** The commands that publish, write a published piece's current copy or make a piece final ask for that pass (DEC-048 point 6).
- **Never at a stage's start.** No stage's command refuses on a library part. A piece is designed, drawn and reviewed while a library is being mended.
- **A draft is told.** The report on drafts asks for attention on a draft that uses a library part with an open finding, and names the library part and the finding (DEC-048 point 7).
- **A finding that appears later takes no pass back.** Where a library part gains an open finding after a piece's pass was made, the piece asks for attention and names the library part. Its pass stands, and its readers' copy does not fail. A withdrawn calibration is treated the same way ([visual-communication:DEC-051-no-reading-chooses-before-calibration] point 7).

### 3. The four states of a library part, and how a finding ends

A *library's review report* is any review report of the pages that show what the library draws, for the version in question. Where the last one is meant, this record says "the last".
It has *read* a library part where it read a page that draws the part, in at least one variant.

Three words about a finding on a library part, each used in one sense:
- **A finding stands** from when its source lists it until it ends.
- **A finding ends** only through the kind of source that opened it, as the list of sources below says. Nothing else ends one: not a change to the part, and not an acceptance.
- **A finding is open** while it stands and no person has accepted the part with it, for the part as it is (point 4). "A finding left open" means the same.

A library part is in one of four states:
- **Open finding:** at least one finding on the part is open. A piece that uses the part gets no pass.
- **Accepted:** findings stand on the part, and each is accepted for the part as it is. This refuses nothing, and every merge of a piece that uses the part shows the acceptance (point 4).
- **Not reviewed:** no finding stands on the part, and the library's last review report has not read it, or the library has none. This refuses nothing, and each pass that uses the library part says so.
- **Reviewed:** the library's last review report has read the library part, and no finding stands on it.

An example, with one component of a library:
- Nobody has reviewed the library. The component is *not reviewed*, and a piece that draws with it gets its pass, with a note.
- The library's owner has a fault written down: the component's label overlaps its icon. The finding *stands* and is *open*. The piece now gets no pass.
- The owner looks at the picture and accepts the component as it is. The finding still stands, and is no longer open. The component is *accepted*, and the piece gets its pass. Each merge shows the acceptance.
- The component is then changed. The acceptance was for the old component, so it falls. The finding still stands, and is open again.
- A review of the library's pages now lists nothing on the component. That ends nothing, since no review opened this finding. The owner looks at the picture of the changed component and has the finding taken back. It has *ended*. A review report has read the component and no finding stands on it, so it is *reviewed*.

One of three sources opens a finding on a library part, and only the same source ends it:
- **The check.** The capability's check fails on the library's own pages. The failure opens a finding on the library part that draws the element it names. A failure that names a page and no element opens one on each library part that page draws. It ends when the check finds no such failure. No review is needed for this, since a failing check stops the pages before any review.
- **The library's review report.** It lists a finding whose fix belongs to that library part, and that is one of these:
  - a fault ([visual-communication:DEC-030-design-agents] point 6), whether or not the reviewer was calibrated;
  - a covered finding, as DEC-051 point 1 defines one.

  It ends when a later library's review report has read the part and lists no such finding on it. Four things bound that:
  - **Read in the variant the finding named.** A later report counts, for one finding, only where it read the part in the variant that finding named (DEC-047 point 3). A review that drew the part in another mode, where the fault does not show, ends nothing.
  - **After the part's own files changed.** A report ends a finding on a library part only where the files that part is drawn from differ from those the last report that listed it read. An edit elsewhere in the library changes none of them, so a review made again after such an edit ends nothing. Nor does a second review of the same files. The reviewer's verdicts split from one reading to the next, so a review made again until it was silent would end a fault with nothing mended.
  - **A covered finding ends only by a report the reviewer was calibrated for.** Only a report from a reviewer's run that the reviewer was calibrated for ends a covered finding. A report from a reviewer's run on a model the calibration did not cover can list no covered finding at all, so its silence says nothing. A fault ends by any later report within the two bounds above.
  - **The last such report is the whole account.** For a part in a variant, the last review report that may end its findings is the whole account of the review's findings there. What it lists stands, and what an earlier one listed and it does not has ended. So nobody has to decide whether a later finding is the same one.
- **A person's word.** The library's owner ([visual-communication:DEC-047-design-process] point 6) may have a finding written down on one of its library parts. That is how a finding known before the process is made to count. It ends only when whoever holds that role has it taken back, by the same command, shown the image of the part as it then is. The command refuses where that image was not brought up (DEC-048 point 6). No review ends it, and no check. Where several people hold the role, any of them may take back a finding that another had written down (DEC-047 point 6).

What a review report makes count, and what it never does:
- **By name.** A finding whose fix belongs in a library names the library part, as it names the page and the element. The command that records a review report refuses one that names a library and no library part (DEC-048 point 3).
- **Matched against the page.** A command confirms that the named library part is one the page draws with.
- **A reading all the same.** Which library part a fault belongs to is the reviewer's reading, and nobody has tested that reading. So a fault placed on the wrong part keeps the wrong pieces from a pass, until a person accepts the part or a later review of the changed pages places the fault elsewhere. That is the cost of letting a fault count before any calibration, and the person who is asked to accept sees the picture first (point 4).
- **It stands across a change to the part.** A finding follows the library part by its name, and a change to the part alone ends nothing. A part under a new name carries no finding (point 7).
- **Never from a review report:** a note of taste, a brief finding, a grade on a rule no calibration covers, and a grade the review marked as a need or as the asker's ([visual-communication:DEC-042-grades-bar-and-loop] point 4).
- **Never for a piece that does not use the library part.**

A finding written on a person's word:
- **Recorded by a command, on that person's word.** An agent runs the command only once the person has said so, as it records an acceptance (DEC-048 point 4). No agent writes one by itself.
- **Shown with its image,** as an acceptance is (point 4).
- **Whatever its source.** The library's owner may have a note of taste written down, or a finding from before the process. What the list above keeps out is a reading that counts by itself. Here the library's owner decides to hold a part of the library back, and that decision is theirs.
- **No review's silence ends it.** A changed value in the part, and one review that lists nothing on it, leave the finding standing. Only the owner's word takes it back, given with the image of the changed part in front of them.
- **In a project that receives the library,** whoever answers for the project's received libraries (DEC-047 point 6) may have a finding written on a library part too. It is kept in the project's own file and counts in that project alone (point 5). Only the word of whoever holds that role there ends it.

### 4. A person may accept a library part with its findings

- **Who.** The library's owner may accept a library part as it stands, with the findings that stand on it.
- **What an acceptance does.** Those findings are then accepted, and are not open, for the part as it then is. The part refuses nothing. The findings have not ended. Where the part changes, the acceptance falls with the old part (point 5), and each finding that still stands is open again.
- **Shown the image.** The acceptance is asked with the image the finding is on (DEC-047 point 6). A fault is something blank, missing or overlapping, so a person who is no designer can see whether it is there. The command that records the acceptance refuses where that image was not brought up (DEC-048 point 6). It cannot tell that the person looked.
- **Recorded on that person's word,** by a command, for the library part as it then is, as a piece's acceptance is (DEC-048 point 4).
- **Shown.** Every merge of a piece that uses the library part shows the acceptance beside the piece's verdict (DEC-048 point 8). Where one human holds both roles, that shows the acceptance to the one who gave it.
- **For a library a project receives,** the owner's acceptance comes with the library's state (point 5). Whoever answers for the project's received libraries may also accept a library part for that project alone.

### 5. Where the state is kept: two files, each with one owner

- **The library owner's state.** A library's owner keeps a file that says, for each library part of a released version, whether it was reviewed, each finding that stands on it, the owner's own among them, and each acceptance of the owner's, tied to the library part's digest. It lies beside the library's record of releases and outside every released version's own files, which never change (DEC-003). A change of its own writes it, never a release, and no hash of a version covers it.
- **The project's own word.** A project that receives a library keeps its own acceptances, and the findings its own person had written down, in a file in its own tree. The project never writes the owner's file, and the owner never writes the project's. Whoever answers for the project's received libraries gives the word that file records (DEC-047 point 6).
- **A format number in each,** from its first version, as the evidence has (DEC-048 point 5).
- **By value, but for a finding.** That a library part was reviewed, and each acceptance of it, are tied to what the part is, by its digest, and not to the version's number. A library part that a new version leaves unchanged keeps them, and a changed part loses them. A finding is tied to the part by its name, and stands on the changed part until its own source ends it (point 3).
- **What carries a later change to a project.** A project reads the owner's state as its copy of the library has it, and runs nothing. A finding or an acceptance the owner adds later reaches a project only when the project next takes the capability's or the library's files again. Until then the project reads the older state, and its pieces are told nothing.
- **For a library still being built,** in the project's own files, the state is read from the library's own evidence as it stands.
- **A version from before this record** has no state. Its library parts are *not reviewed*, and refuse nothing, unless the owner writes down a finding.

### 6. A library's own pages do not wait for the library they show

- **A library's pages are a piece.** They go through the design process as any piece does.
- **No library part waits for itself.** The run of a library's pages asks nothing of the library they show. It asks only of the other libraries those pages draw with.
- **No cycle.** A library part's state is read from a review report, a check or a person's word, and never from another piece's pass. So no library's pages wait on a pass that waits on them. This rests on that, and on no fixed order among libraries.

### 7. What waits for a later record, and what this does not stop meanwhile

Two things are not decided here, and a refinement of this record decides them once a first library has been through the design process and has a review report:
- **What a library's pages must show** before a library part counts as reviewed: which layouts, modes and sizes of a component, and what showing means for a brand's role and for a notation's sign.
- **Whether a library part that is not reviewed then refuses a pass.**

Until then, said plainly:
- **A library that was never reviewed refuses nothing.** The pass says "not reviewed", and whoever authorises the merge sees it.
- **Not reviewing is the easier road until then.** A library that runs its pages can gain findings that refuse. One that never runs them refuses nothing. Only the owner's word, and the note at each merge, stand against that.
- **A new name is an easier road too.** A finding follows a part by its name. A part given a new name, or a new part made beside the old one, carries no finding and is not reviewed. Only the owner's word, and the note at each merge, stand against that as well.
- **A library whose own pages fail the check refuses all the same,** reviewed or not (point 3).
- **A fault found before a library went through the process counts only once the library's owner has it written down** (point 3). A review made before the process is no evidence of it, and nothing makes the owner write its findings down.

## Rationale

**Why when the pass is made, and not at the start.** What must not happen is that work built on a known fault lands, or reaches readers. Drafting on it harms nobody, and is often how the fault is found.

**Why each library part the piece uses.** A finding on one component would otherwise stop every piece on that version, most of which never draw it. The process already knows which library parts a page uses.

**Why a pass is not taken back.** A pass read live against the library's state would vanish when a later review of the library arrived, with no change to the piece, and would fail a published copy for something the project cannot mend at once. Noting the state and asking for attention says the same and fails nothing, as a withdrawn calibration does.

**Why a fault always counts.** A calibration gives its evidence on grades, rule by rule (DEC-042 point 10). So a fault that waited for a calibrated reviewer would wait for a calibration that covered its rule, and a known fault would land meanwhile. A fault is something blank, missing, overlapping or drawn in the wrong font, and no judgement of design (DEC-030 point 6). A person who is no designer can confirm it from a picture. Two things make that true in practice: the acceptance is asked with the image, and the finding names its library part. A piece's own faults are shown to the person at that piece's merge. A library's fault would reach every piece unseen. A mend or one acceptance, once, shows it to a person once for all of them.

**Why a failing check is an open finding, on the part it names.** A check is computed and needs no reviewer. Left out, a library whose pages fail the check before any review would have no review report, and would refuse less than one that was reviewed and found faulty. A failure opens a finding on the library part it names, as a review's finding does. Opening one on every part the library's pages draw would stop every piece on that version for one failing element.

**Why a change to the part alone ends no finding.** A state tied only to what the part is would clear every finding at the first edit, mended or not. A check's failure has no such gap, since its finding stands until the check passes. Tying a finding to the part's name gives the other two sources the same footing: a review's finding stands until a later review of the changed part lists none, and a person's until that person takes it back.

**Why each finding ends only through the source that opened it.** A review by a reviewer that is not calibrated is a reading nobody has tested, and its verdicts have split from one reading to the next (DEC-042, Context). If its silence could end a finding the owner had written down, one changed value and one review would clear a known fault with no person shown anything. That is the road this record starts from. A review's silence may end what a review opened, since that finding rested on the same kind of reading. The cost is that a person's finding needs that person again, with the picture, even after a true mend. The rule also needs nobody to judge whether two findings are the same one: a check's result and a review's last report each replace the earlier whole, and the person speaks for their own.

**Why a person may have a finding written down, whatever its source.** The faults this record starts from were found by a review made before the process. Without the owner's word they would count for nothing. The owner's word is no reading that counts by itself. It is the decision of the library's owner to hold a part back, and a project that disagrees may accept the part for itself (point 4).

**Why a note or an uncovered grade never counts.** They would let a reading nobody has tested decide what lands. The set lets no such reading decide for a piece: before a calibration the review's findings go to the person (DEC-051 point 2) and the critique's verdict informs ([visual-communication:DEC-049-critique-step] point 4). Counting them here would ask more of a library than a piece is asked. A fault is the one exception, and it is named as one: which part it belongs to is an untested reading, and it counts all the same (point 3).

**Why a later review ends a finding only in the variant it named and once the part's own files changed, and a covered finding only by a report the reviewer was calibrated for.** A review that never drew the part where the fault showed has seen nothing of it, and its silence is no evidence. A second review of files nobody changed can differ from the first only by the reviewer's own unsteadiness, so its silence is none either. An edit elsewhere in the library leaves the part as it was, so the same holds after one. That is why the comparison is of the files the part is drawn from, and not of everything the report read. A reviewer's run on a model the calibration did not cover can list no covered finding, so it would end every covered finding on a library just by being made, and the session chooses the model.

**Why a person may let a library part through.** Without that, one finding that cannot be mended would stop every project's pieces, with no decision open to anyone. The person may already let a piece through (DEC-047 point 6).

**Why a local component is the piece's own, and what that costs.** It is drawn and reviewed with the piece's pages, so it is asked what the piece is asked. The cost is plain: a fault in a library part refuses a pass, and the same fault copied into a local component does not. So copying is the cheaper road here too. Fixing at the root stays the designer's rule (DEC-030 point 3), and it is the rule, and no refusal, that stands against the copy.

**Why two files.** One file written by the library's owner and by each project would have two owners, and the next delivery of the library would write over what the project added (COR-001).

**Why "not reviewed" refuses nothing yet.** A test of what a library must show, written before any library was reviewed, would be a guess. A wrong guess would either stop every piece or prove nothing. Refusing would also stop every piece that draws on a library nobody has reviewed, which at first is every piece of every project. Said plainly at each pass, the gap is at least seen.

### Alternatives considered

- **A stage refuses to start on a library part with an open finding.** Rejected: it forbids drafting while a library is mended.
- **The whole version ready or not.** Rejected: a finding on a library part the piece does not use would stop it.
- **Any finding left open, notes included.** Rejected: an untested reading would decide, and a library would be asked more than a piece.
- **A fault counts only once the reviewer is calibrated.** Rejected: a calibration gives its evidence on grades, rule by rule, so a known fault would land until one covered its rule.
- **A failing check opens a finding on every library part the library's pages draw.** Rejected: one failing element would stop every piece on that version.
- **An agent writes down a known finding.** Rejected: a refusal in every project would then rest on an agent's word.
- **A library whose pages fail the check is "not reviewed".** Rejected: failing the check would then refuse less than a review.
- **The pass read live against the library's present state.** Rejected: a pass would vanish with no change to the piece.
- **One state file that the owner and each project both write.** Rejected: two owners of one file.
- **No decision by a person.** Rejected: one stuck finding would stop every project.
- **A library part with no review refuses a pass from the start.** Not taken: every version in use would refuse on the day it shipped, and the test of what must be shown cannot be stated before a library has been reviewed.
- **State compared by version.** Rejected: a version changes when a library part did not.
- **A finding ends when its library part changes.** Rejected: any edit to the part would clear it, with no mend confirmed.
- **A later review that lists nothing ends a person's finding.** Rejected: the silence of a review nobody has tested would clear a fault its owner had written down.
- **An acceptance ends a finding.** Rejected: the finding would be gone when the part next changed, though nothing mended it.
- **A library's state as stages of each piece.** Rejected: one library would be reviewed again in every piece.

## Implications

- **Edits made in this record's landing change, once this record is accepted,** each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-030 point 4:** a library part added to a library for a piece is asked about when that piece's pass is made, as any library part is. The designer need not wait for it while it drafts (point 2).
  - **DEC-042 point 5 and DEC-030 point 7, "It reports, and never redesigns":** a finding whose fix belongs in a library names the library part (point 3).
  - **[visual-communication:DEC-013-shipped-library-releases] point 2:** the state of each released version's library parts is the owner's file, beside the library's record and outside every released version's own files. A change of its own writes it, a release never does, and no hash covers it (point 5).
- **Read against this record, and left as they stand:** DEC-003 point 8, since a lock moves as before; DEC-030 point 3, since the designer fixes at the root as before; DEC-013 point 3, since a released version's hash covers its own files alone.
- **Work once this record is accepted,** each in a later landing change:
  - working out which library parts a piece uses, from its pages;
  - the library owner's state file and the project's own file, each with its schema and format number;
  - the commands that record a person's finding on a library part, take it back, and record an acceptance. The pass's question about library parts never ships before the first of them (DEC-047 point 8);
  - the library parts' place in the pass, in the validator of readers' copies, in the report on drafts and in the merge check;
  - the pages that show each shipped library, and their run.
- **Left open:** what point 7 names; and a way for a project to learn of a later finding without taking the library's files again.
- **No migration.** A version without the state reads as not reviewed (COR-010).
