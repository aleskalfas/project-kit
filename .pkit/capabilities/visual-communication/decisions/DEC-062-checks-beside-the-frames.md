---
id: DEC-062
title: The viewing step reports what the checks the reviewer leans on found on what it drew
status: proposed
date: 2026-11-16
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the graphic-design reviewer leaves some measurements to checks. Where the checks of boxes ran, it does no sums of its own over the frames. So it must know what those checks found on the very pages it sees. A piece's findings record cannot tell it: it holds what the last render found, which may be of other files than the ones drawn. So the viewing step, which already computes the scenes it draws, runs those checks on the same scenes and puts their findings in its report, beside the frames. The report names each such check even where it found nothing, and says where it judged nothing, such as at a key whose brand gives no step of space. A check the report does not name did not judge those pages, so its silence is never read as "found nothing". A check of a text's size joins the report once the capability ships one.

## Context

[visual-communication:DEC-046-faults-lower-grades] point 3 adds two checks that measure the boxes of siblings: edges that nearly line up, and boxes that overlap. Where they ran, the reviewer does no sums over the frames, and where they did not, it reads the offsets from the frames. The point does not say where the reviewer learns which holds. Point 5 of the same record has a like need for a check of a text's size, which the capability does not ship yet. It has the reviewer tell from the capability's list of checks whether one exists.

The words it uses:
- **The viewing step** draws a piece's pages as images, in the clone's local folder. Beside them it writes the *frames*, each drawn element's box in the image's pixels, and a *report* of what the images cannot show ([visual-communication:DEC-015-viewing-step-and-reviewer]). It computes the piece's *scenes*, its pages as the engine lays them out, from the files as they stand, under the piece's lock (DEC-015 point 4). The frames are the boxes of those scenes.
- **A check** is a measurement a command makes on every render, with no judgement ([visual-communication:DEC-002-files-and-validation] point 7). Its *label* is the name its findings carry.
- **The findings record** is the file each render of a piece that is not final keeps beside the piece. It holds a key that fingerprints every file the scenes were computed from, and what computing them found. The check reads it while its key verifies against the files ([visual-communication:DEC-005-engine-and-plugins] point 13).
- **The reviewer** is the capability's agent that reads the images, the frames and the report, and reports what no check measures (DEC-015 point 7). It runs no command that could verify a key ([visual-communication:DEC-030-design-agents] point 7).

The findings record does not describe the pages the reviewer sees. It holds the last render's findings, while the frames show the scenes the step computed from the files as they stand. The two part whenever the files change after a render: a look that follows an edit with no render between, or a build pipeline's drawings of one commit beside a working tree's record. They part across releases too. The key holds no version of the engine, so a record written before the checks of boxes still verifies, and holds none of their findings. The reviewer can tell neither case. A reviewer that read such a record as the checks' judgement of its frames would skip the sums over a layout no check measured. The capability's list of checks cannot tell it either, since it says what the installed release ships, not what ran on the scenes drawn.

## Decision

**The viewing step's report carries, beside the frames, what each check the reviewer leans on found on the scenes the images were drawn from, and says where each judged nothing. The reviewer reads those checks there alone, so what it knows of them always describes what it sees.**

### 1. The report carries what each check the reviewer leans on found

- **What it carries.** For each check the reviewer leans on, the report holds the check's findings on every scene an image of the run was drawn from, under a forced palette too. The step computes them from those scenes, the ones the frames come from. So what the report says of the checks, and what the images show, are always one state of the piece, whatever changed since a render.
- **A check the reviewer leans on** is one whose judgement stands in for part of the reviewer's own reading. Where the check judged, the reviewer makes no measurement of its own there, or its report says that the check made it. Trusting such a check where it did not judge the scenes drawn would leave a defect unseen or a gap unnamed. The two checks of boxes are such checks, since where they judged, the reviewer does no sums over the frames (DEC-046 point 3). A check of a text's size is one too (point 4).
- **Not one:** a check whose findings the reviewer only names, while it looks for the same fault on the images whether the check found it or not, such as a text that leaves its box. Such a finding out of date changes at most how a fault is named, never whether it is seen, so the report leaves it to the findings record and the check.
- **The check's own measurement.** The step runs each such check as it runs on a render, so a finding means the same in the report and in the check, and no check is built twice. One difference holds. Where a check leaves out a place because the report already names it, such as a text the report names as covered, which an overlap of boxes would name again, the step leaves out exactly what its report names. A check run on a render can only approximate that, since no check reads the report (DEC-015 point 1).
- **Whatever the piece's state.** The step carries them for a final piece too, since they describe what its images show as the engine draws them today. That judges nothing of the piece for validation, which computes no final piece's scenes (DEC-002 point 7).
- **A new check of this kind** joins the report in the change that adds it. The capability's list of checks says, in the entry of each such check, that the report carries it.

### 2. A check's silence is never read as "found nothing"

- **Each check named.** The report names each check the reviewer leans on that the run made, even where it found nothing.
- **Where it judged nothing.** Where such a check could judge nothing on a scene drawn, the report says so, at the place it holds: a key, a page or an element, named by language, key and page as the report's other entries are. It gives the reason, such as a brand that gives no step of space at that key, where the check of edges that nearly line up has nothing to call near.
- **What a check never judges,** by what it is, such as the lines and arrows the checks of boxes leave out, is stated once, in the check's entry in the capability's list of checks, and not in each report. DEC-046 point 5 has it so for a check of a text's size.
- **How the reviewer reads it:**
  - a check the report names, with no finding at a place and no word that it judged nothing there, judged there and found nothing;
  - a check the report names as having judged nothing at a place did not judge there;
  - a check the report does not name did not judge the images of that run.
- **Where a check did not judge,** the reviewer does what the record that decides the check says for a check that did not run. For the checks of boxes it reads the offsets from the frames (DEC-046 point 3). For a check of a text's size, its report names the gap (DEC-046 point 5).

### 3. The reviewer reads these checks from the report alone

- **Never from the findings record.** The reviewer reads what a check it leans on found from the report of the run whose images it reads. It never reads it from the findings record, which holds the last render's scenes, under a key it cannot verify.
- **One run's images.** A report speaks for the images of its own run alone. For any other image, such as one a session hands the reviewer beside the step's (DEC-015 point 7), the reviewer reads these checks as not having judged it. A build pipeline's drawings are a look's folder, report and all, so their report speaks for their images, at the commit drawn ([visual-communication:DEC-024-outside-programs-sandbox] point 5).
- **The findings record stays the check's.** It keeps what a render found, for the check, as DEC-005 point 13 decides, and gains no field.
- **The report stays no record of findings.** It lies in the clone's local folder, nothing commits it, and no check reads it (DEC-015 points 1 and 4).

### 4. A check of a text's size joins the report

- **It is one the reviewer leans on.** Where such a check judged a text's size, a text under its medium's minimum is the check's finding alone and lowers no grade. Where it judged none, the reviewer's report says that no text's size was compared there (DEC-046 point 5). So the reviewer's report says what the check compared, as point 1 has it.
- **What the report carries of it,** once the capability ships one: its findings on the scenes the images were drawn from, and each statement that it judged no text's size, at the text whose size or minimum it could not work out. A kind of text it never judges stays stated once, in its entry in the list of checks (DEC-046 point 5).
- **How the reviewer tells whether one judged the images:** from the report beside them, which names each such check the run made, and not from the capability's list of checks, which says what ships, not what ran on the images.
- **The check stays another record's.** How it finds a text's size and its medium's minimum is the record's that decides the check (DEC-046 point 5). This record decides only where its findings reach the reviewer.

## Rationale

**Why the report, and not the findings record.** The step computes the scenes it draws, so the checks' findings on them cost only the checks' arithmetic, and describe the images exactly. A field in the findings record could say only which checks the last render ran, on files that may have changed since. With the report, nothing has to be kept in step: no field, no rule for reading a record a release wrote before a check existed, and no render to ask for first. The look a calibration runs carries the checks of the release it runs on, too ([visual-communication:DEC-042-grades-bar-and-loop] point 9).

**Why only the checks the reviewer leans on.** A wrong belief about whether a check judged leaves a defect unseen only where the reviewer hands part of its reading to the check. Elsewhere it looks on the image anyway, and a finding out of date changes only how a fault is named. Carrying every check would make the report a second findings record, and bind each new check to the step, with no reader who needs it.

**Why a check that found nothing is named, and where it judged nothing.** An empty list reads the same as a check that never ran, and the reviewer acts otherwise in the two cases. The check of edges that nearly line up judges nothing where the brand gives no step of space, since nothing is near without one. A reviewer told only that it found nothing would skip the sums there.

**Why what a check never judges is stated in its entry.** It holds for every piece, so each report would repeat a fact the list of checks gives once, as DEC-046 point 5 has it for a text's size.

**Why the step leaves out exactly what its report names.** A place the report already names, named again by a check, is one defect shown to the reviewer twice. Where a check's own definition leaves such a place out, the step holds both what the page hides and what the check found, so it can do so exactly. A check run on a render cannot read what a later look will name.

**Why the state of a size check is read from the report.** The list of checks ships with the reviewer and says whether such a check exists. It does not say whether one judged the images in hand: a pipeline's drawings of an older commit, or a folder a look of an older release left, may come from a release without it. The report says it of its own run.

### What it costs

- **Findings shown twice.** A place these checks name shows in the check's findings, at a render, when a person runs the check and in validation, and again in the report. A person who reads both reads it twice.
- **Two answers that may differ.** Where the files changed between a render and a look, or where the step leaves out what its report names, the two differ. Each is true of its own scenes, and the reviewer reads only the report, so it never chooses between them.
- **The step's work.** Each look does the checks' arithmetic, over the scenes it computes anyway.

### Alternatives considered

- **A field in the findings record naming the checks that ran.** Rejected. The record holds the last render's findings, and the frames show the files as they stand. Where the two part, the field still names the checks, so it tells the reviewer they judged a layout they never measured, and the reviewer, which verifies no key, would skip the sums there. It would also add a committed field, a rule for which checks it names and a rule for reading a record without it.
- **That field, with the report saying whether the findings record matches what the step drew.** Rejected. Where the record matches, the report tells the reviewer no more than its own findings of the checks would. Where it does not, as after any edit not yet rendered, the reviewer falls back to its own sums, which the checks exist to spare it (DEC-046 point 3). It keeps a field and a comparison, to give less.
- **The session renders before each look.** Rejected. A render of a draft moves its lock and rewrites a committed file ([visual-communication:DEC-003-change-over-time] point 8, DEC-005 point 13), which the viewing step exists to avoid (DEC-015 point 1). The reviewer could not confirm that the render happened, and a pipeline's drawings of one commit would still lie beside a working tree's record.
- **The reviewer reads the capability's list of checks,** as DEC-046 point 5 has it for a text's size. Rejected. The list says what the installed release ships, not what judged the scenes drawn. A findings record that release wrote before the files changed still holds another layout's findings.
- **The checks of boxes in the report alone.** Rejected. They are checks, run on every render (DEC-046 point 3), so a person sees each place at a render and in validation, with nothing drawn. Moving them into the step would overturn that point.

## Implications

- **This change adds a record, and changes nothing a project could observe.** It declares no changeset and owes no migration. The work that builds the record changes the report's form, and declares its own.
- **Edits to accepted records,** made in this change once this record is accepted, each citing it (COR-066 point 5). Accepting this record accepts them.
  - **DEC-015 point 3,** its list of what the report holds. Before "A run of the step that draws no image", it gains a bullet: "**What the checks the reviewer leans on found,** on the scenes the images were drawn from, and where each judged nothing. The report names each such check the run made, even where it found nothing (refinement per [visual-communication:DEC-062-checks-beside-the-frames])."
  - **DEC-046 point 3,** the bullet "The reviewer judges each place the checks name". Its sentences "Where the checks ran, it does no sums over the frames. Where they did not, it reads the offsets from the frames." come to read: "Where the viewing step's report says the checks judged the scenes its images were drawn from, it does no sums over the frames. Where the report does not name them, or says they judged nothing, it reads the offsets from the frames (refinement per [visual-communication:DEC-062-checks-beside-the-frames])." The rest of the bullet stands.
  - **DEC-046 point 5,** the bullet "Who says where no text's size was judged". "That statement is what tells the reviewer" comes to read: "That statement, which the viewing step's report carries for the scenes its images were drawn from, is what tells the reviewer (refinement per [visual-communication:DEC-062-checks-beside-the-frames])". Its other sentences stand.
  - **DEC-046 point 5,** the bullet "One reading, with the check or without it". "The reviewer tells which state holds from the capability's list of checks, which ships with the reviewer, and never from a piece's findings alone" comes to read: "The reviewer tells which state holds from the viewing step's report, which names each such check the run made, and never from the capability's list of checks or a piece's findings alone (refinement per [visual-communication:DEC-062-checks-beside-the-frames])".
  - **DEC-046's Implications,** the last item of the reviewer's body, "How the reviewer tells that the capability ships no check of a text's size". It comes to read: "How the reviewer tells that no check of a text's size judged the images it reads. From the viewing step's report, as point 5 says, and not from the capability's list of checks or a piece's findings alone: a check that passed every text may state nothing of their sizes, and only the report names a check that found nothing (refinement per [visual-communication:DEC-062-checks-beside-the-frames])."
- **Read against this record, and left as they stand:**
  - DEC-015 point 1's "No render, and no export", since the findings the report carries are no record of findings: nothing commits them, and no check reads them;
  - DEC-015 point 4, since they lie in the report, in the clone's local folder, so nothing the step writes reaches a commit;
  - DEC-005 point 13, since the findings record stays the check's and gains no field;
  - DEC-030 point 7's "With the checks", since the measurement stays the check's: the step carries it, and judges nothing;
  - DEC-046 point 8, since a check the reviewer's body, the file of instructions it works by, is written to read from the report has landed for the reviewer only once the report carries it.
- **The work that builds it,** under [project-kit#3335](https://github.com/aleskalfas/project-kit/issues/3335):
  - the step runs each check the reviewer leans on, through the check's own code, on each scene an image is drawn from, and writes into the report its findings and where it judged nothing;
  - the checks of boxes say where they judge nothing, such as a key whose brand gives no step of space, so that the step can report it;
  - the outputs page gives the report's form for these checks, and says that the step keeps no findings record, where it says that it keeps no findings;
  - the list of checks says, in the entry of each such check, that the report carries it, and what the check never judges;
  - tests show that a look after an edit with no render carries the checks' findings on the edited scenes, that a check which found nothing is named, and that a key with no step of space reads as judged nothing.
- **The reviewer's body** reads these checks from the report, in the change that teaches it what the checks find ([project-kit#3328](https://github.com/aleskalfas/project-kit/issues/3328)).
- **The findings record's schema, and the commands that write it,** are left as they are.
