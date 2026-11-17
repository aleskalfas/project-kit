---
id: DEC-055
title: A piece names the media it is shown in, its top declares the smallest text each allows, and the check fails a text drawn smaller
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a page shown on a screen at hand, on a screen across a room or on paper has a smallest text a reader there can read. A check compares each text with that size, and fails a text drawn smaller.

- **The piece names the media it is shown in,** from three the capability names: `screen`, `room` and `paper`. It names them alone, and each then shows every size the piece is drawn at. Or it names for every medium the sizes that medium shows. A deck drawn for a laptop and for a projector then shows its projector's pages in the room.
- **The piece's top component declares the smallest size,** for each medium its pages are made for. The value is a fixed size where the medium shows a page at its own size, as a screen at hand shows a web page. It is a share of the page where the medium fills what shows it with the page, as a room's screen shows a slide. No brand sets it.
- **The check measures each run of text.** It compares the run's font size with the smallest size of each medium that shows the size the run is drawn at. It takes a page as its medium shows it, and takes the brand's width at a size as the width the page is shown in. A narrower window or column, a zoom and a print's scale are not measured. It reads the scene, so one finding serves every renderer.
- **The finding lies in the piece's own file,** at the text's trace, as a finding on contrast does. The size comes from the component, the brand and the top together.
- **The check states what it measures and what it leaves out,** as every check a reader leans on does. It states them in its entry in the capability's list of checks, and in its code. It leaves out words inside a picture.
- **Where it could measure no text's size, it states so in the piece, as a fact.** It does so for a piece that names no medium, and for a medium its top declares nothing for. It does so too for a size no medium shows, and for a page whose smallest size it cannot work out.
- **A text such a fact covers counts as not measured,** though a finding on it stands for the medium it names. The reviewer then judges whether the text can be read where the piece is shown, as it does where no check measures.
- **A piece is held to the check only once it names a medium.** Its lock must also name a top that declares a smallest size for that medium. So the review is tested on designs whose every text was measured, and its verdict ends a loop only on a piece measured so.

## Context

The record of the principles of visual communication leaves "a text smaller than its medium allows" to a check, run on every render whether a rule binds or not, beside a text that spills out of its box and too little contrast ([visual-communication:DEC-028-principles-of-visual-communication] point 1). Its point on who can read a page leaves the smallest text size for a medium to that check (DEC-028 point 10). Its rule on legibility, `RS-GRAPHIC-005`, keeps for the review that "everything on a page can be read where the piece is shown", and that "a page is taken in at a glance". The record of the review's grades keeps it the checks', and records that the check was never built ([visual-communication:DEC-042-grades-bar-and-loop] point 2).

So a projected slide can carry 12 px notes and pass every check ([project-kit#3185](https://github.com/aleskalfas/project-kit/issues/3185)). The engine's only smallest size sizes the viewing step's images, so that a reader of them can read a page's smallest text, and fails nothing ([visual-communication:DEC-015-viewing-step-and-reviewer] point 5). The review graded legibility by how much a page holds, not by whether its text reads at its size (DEC-042, Context).

Three records bind the check before it is built:
- **How the check and the review divide the rule.** Comparing a text's size with its medium's minimum is the check's ([visual-communication:DEC-046-faults-lower-grades] point 5). Whether a text can be read as drawn stays the review's. A text under the minimum is the check's finding alone, and lowers no grade.
- **What a check of a text's size states.** It states, as a fact, where it measured no text's size. A kind of text it never measures, it states once, in its entry (DEC-046 point 5). The review's calibration waits for this check (DEC-046 point 8).
- **What every check a reader leans on states.** It states which kinds of place it measures, and which it leaves out. It states them in its entry and in its code ([visual-communication:DEC-063-where-a-check-measures] point 1). The record that decides a check decides what it measures.
- **How its silence is read.** Where the check could measure nothing at a place of a kind it measures, it states so in the piece (DEC-063 point 2). Its silence counts as measured and clean only where both allow (DEC-063 point 3).
- **Where the reviewer reads it.** The reviewer reads what any check found from the viewing step's report alone, and reads there what each check measures ([visual-communication:DEC-062-checks-beside-the-frames] points 2 and 3). The reviewer's instructions read this check's silence, so the change that lands the check states what it measures (DEC-062, Implications).

What the files say today of where a piece is shown:
- **The piece's `shown` field** says it in words, for a reviewer ([visual-communication:DEC-001-visual-communication-discipline] point 3). No command reads a size from words.
- **The size axis `device`** names what a piece is drawn for: a desktop, a tablet, a phone, or a projector, a screen read from across a room ([visual-communication:DEC-021-size-and-shape] point 1). A brand gives each mode its values, such as a larger type on a projector, and each key has a scene of its own. A piece that names no size is drawn at the axis's default, `desktop` (DEC-021 point 3). A brand has only the sizes it or its base gives, and a piece that names a size its brand lacks fails (DEC-021 point 2).
- **The top** says what its pages are, and how large. A deck's slides are as wide as the brand's slide and nine sixteenths as tall. A site's pages are web pages, as wide as the brand's site at each size, and as tall as their content ([visual-communication:DEC-022-web-site-and-parts] point 3). A top whose pages print at one size declares that size, which no brand gives ([visual-communication:DEC-034-brand-drawings] point 3).
- **A page of the HTML renderer** writes every length as a share of the page's width. It shrinks with a window narrower than itself, and keeps its own size in a wider one ([visual-communication:DEC-020-html-page-drawing] points 2 and 4). A PDF draws a page at the top's physical size, or at its own size in its renderer's unit (DEC-034 point 3; [visual-communication:DEC-026-html-page-print] point 4).
- **A scene's run** holds its font size, in px, as its typography role gives it at the scene's key ([visual-communication:DEC-005-engine-and-plugins] point 5).

So neither the size a piece is drawn at nor its top says where it is shown. A deck projected in a room that names no size is drawn at `desktop`, and under a brand with no size it can name no other. One page file may be read on a laptop and projected. A piece drawn at two sizes has its own files at each, since a file an export makes serves one size ([visual-communication:DEC-023-html-page-modes] point 1), and no file says which is shown where. And how large a page stands depends on how it is shown: the width it is shown in and the format it reaches its reader in both change it.

Terms:
- A page's *medium*, in DEC-028's sense and this record's, is how the page reaches a reader's eye. It is not a renderer's medium, the format a renderer draws into (DEC-001 point 2).
- A medium's *smallest size* is the least font size a text may take on a page shown in it.
- A *scene check*, a check's *reach*, a *place* and the *list of checks* with its *entries* are DEC-063's terms. A *statement* is the fact a check states where it could measure nothing (DEC-063 point 2). A check *measures*, and the reviewer *judges* (DEC-063, Context).

## Decision

**A piece names the media it is shown in, from three the capability names, and may name for every medium the sizes it shows. Its top declares the smallest size of each medium its pages are made for, as a fixed length or as a share of the page. The check measures each run of text against the smallest size of each medium that shows the run's key, taking each page as its medium shows it, and fails a run drawn smaller, at the text's trace in the piece's file. It states its reach, and states as a fact where it could measure no text's size. A calibration measures every text's size, and the verdict ends a loop only on a piece measured so.**

### 1. The piece names the media it is shown in, and may name for every medium the sizes it shows

- **Under one field.** A piece names its media under `media`, in one of two forms, and one form holds for the whole piece. Either names one medium at least:
  - a list of the capability's words, each once, where each medium shows every size the piece is drawn at, such as `media: [screen, room]`;
  - a mapping from each medium's word to the sizes it shows, each a size the piece is drawn at and named once under it, such as `media: {screen: [desktop], room: [projector]}`. Every medium a mapping holds names its sizes, and one that shows every size names each.
- **Three media:**
  - `screen`, a screen at hand, read at arm's length or nearer: a desk's, a lap's or a hand's;
  - `room`, a screen read from across a room, projected or not;
  - `paper`, a printed page.
- **Each size held to each medium that shows it.** A deck read on a laptop at `desktop` and projected at `projector`, under a brand that gives both, names `media: {screen: [desktop], room: [projector]}`. Its projector's texts are held to the room's smallest size, and its desktop's to the screen's. A deck projected that names no size names `media: [room]`, and its texts at `desktop` are held to the room's.
- **A size, as a component reads it.** A key's size is the mode it holds on the size axis, else the axis's default (DEC-021 point 3). So a piece that names no size is drawn at `desktop`, and a mapping may name it.
- **The capability's words.** The piece's format names them, as it names the formats of its exports. So a medium means the same under every top, and a command reads it with no top.
- **The size never chooses it.** A size mode chooses the values a brand gives for what a piece is drawn for (DEC-021 point 1). The medium says where the piece is shown, and the two may differ: a deck projected in a room may be drawn at `desktop` alone. A mapping is the piece saying which of its files each medium shows, never a size choosing its medium.
- **`shown` stays words,** and says the place as well as the medium. The review judges a page by it under `RS-GRAPHIC-005`, and the check measures by `media` alone. Both are the piece's author's, who keeps them in agreement. No command compares them, since none reads a medium from words, and the review reads both (point 12).
- **No scene reads it,** so an export's reading leaves it out, as it leaves out the losses a piece accepts ([visual-communication:DEC-016-what-an-export-reads] point 1). A medium named or changed changes no exported file. The key of the findings record reads the piece's file whole (DEC-016 point 2), so the next check measures by it.

### 2. The top declares each medium's smallest size

- **Under one key.** A top declares its smallest sizes under `smallest-text`, a value for each medium its pages are made for, by the medium's word, such as `smallest-text: {screen: 12, room: "=:height / 40"}`.
- **The top's alone,** as its physical size is (DEC-034 point 3): a fact of the top's pages, which DEC-001 point 5 comes to name beside the physical size (Implications). No brand gives it a value, no role or component token holds it, and no other formula reads it.
- **Only the piece's top is read for it.** A top placed in another component's slot, or as a page of another top, is shown in the piece's media, and its own declaration is not read there.
- **A value, never a switch.** It switches neither by an option nor by a size. So content never chooses its own smallest size, and a size chooses no medium.
- **A medium it declares nothing for** has no smallest size under that top, and no text of a piece it tops is measured in that medium.

### 3. A fixed length or a share of the page, each taking the page as its medium shows it

The value takes one of two forms. The top chooses, for each medium, the form that fits how that medium shows its pages, and the check takes each page as so shown:
- **A fixed length,** a positive number in px, for a medium that shows the top's pages at their own size. On a screen at hand a px of the page is then a px of the screen, which CSS sets by the angle it takes at arm's length. On paper, a page with no physical size prints at the unit its renderer declares (DEC-034 point 3). That unit is the capability's, as every renderer is (DEC-005 point 12), so a fixed length on paper names a printed size no project moves, such as the PDF export's px, 96 to the inch.
- **A share of the page,** a formula that gives a length and reads only the size of the page the run lies on, `:width` and `:height`, with numbers, such as `"=:height / 40"`. It serves a medium that fills what shows it with the page: a room's screen, which shows a slide as large as its image whatever its px, or paper at the top's physical size, which takes the page by one scale. So the smallest size follows the page's size, whatever width a brand gives the page. It reads `:height` only at a page that asks for a height: a page that asks for none is as tall as its content (DEC-022 point 3), so a share of its height would grow with the text it is compared with (point 7).
- **What the check takes as given.** A page shown in less width than its own shrinks, as a page of the HTML renderer shrinks in a narrower window and keeps its own size in a wider one (DEC-020 point 4). So the check takes the brand's width at the size a page is drawn at as the width the page is shown in, such as a browser's window or a document's column.
  - A device or a column narrower than that width shrinks every text on the page, by the ratio of the two widths.
  - A page file shown on a room's screen wider than the page fills that screen only once the presenter enlarges it.
  - Neither is measured. The window, a zoom, and the scale a presenter or a print dialog sets are the reader's or the presenter's, as the sheet and its scale are (DEC-026 point 4).

Neither form reads a role. A brand moves the smallest size only through the size of the page it gives, never by a value of its own.

### 4. The check measures each run against the smallest size of each medium that shows its key

- **What it measures.** The font size of each run of each text a scene draws, as the scene holds it. It compares that size with the smallest size the top declares for each medium that shows the scene's key. The smallest size is the one for the page the run lies on.
- **At each key, in each medium that shows it.** Each key the piece names is held to each medium that shows its size (point 1). The run's size is the brand's value at the scene's key, and a share reads the page's size there. So a projector's larger type meets the room's smallest size where the piece shows its projector's pages in the room. A deck drawn at `desktop` alone and named for the room is held to the room's all the same.
- **At the smallest size, a run passes.** A run below it is reported. Both are compared at the scene's rounding of a length, to 1/100 px.
- **What it leaves out:**
  - **Words inside a picture,** made while preparing or elsewhere. They are pixels, and no text the scene holds. DEC-046 point 5 decides that such a check never measures them, and states so once, in its entry.
  - **How large a face's letters stand in their font size.** A face whose letters are small for their size is the review's to judge on the drawn page, under `RS-GRAPHIC-005`. This point decides it.
  - **How a viewer shows a page:** the window, a zoom and a scale (point 3).
- **Left out in its reach, with no fact on each piece.** Each of the three is a clause of the check's reach (point 11). The reviewer reads them from the reach the viewing step's report carries for the check (DEC-062 point 3). It never reads them from the entry it has at hand.

### 5. The check reads the scene, so one finding serves every renderer

- **One finding for all of them.** A renderer adds no size to a page (DEC-001 point 2), so a run's size in the scene is its size in every renderer's output. The check reads the scene, before any renderer runs, and its finding holds for the previews and for each export alike, each page taken as point 3 says.
- **A physical page.** A format with a physical page draws each page onto it by one scale (DEC-034 point 3), so a share of the page keeps its share on paper.
- **What a viewer does** is not measured: the window, a browser's zoom or a print dialog's scale (point 3).
- **The scene holds nothing new,** so neither the seam's version nor any renderer's rises (DEC-005 points 8 and 9).
- **The viewing step keeps its own smallest size,** which sizes its images for whoever reads them, and measures no medium (DEC-015 point 5).

### 6. The finding fails, at the text's trace in the piece's file

- **Its label,** `text-too-small`. It is a finding of the scenes, found when a scene is computed, and kept in the findings record as each of theirs is (DEC-005 points 13 and 14).
- **Where it lies:** `<piece>/piece.yaml#<trace>`, the trace of the text whose run is too small, as a finding on contrast lies (the list of checks, `contrast-drawn`). It names no library version.
- **Its message** names the run, its typography role and its size, the medium, its smallest size, the top that declares it and, for a share, the page's size it was read from. Its fix names the ways to mend it:
  - another style for the run, or an option or a component that sets the text in a larger role;
  - a brand that sizes the role larger at that size;
  - where the run's size is shown elsewhere, and another of the piece's sizes in that medium, its media naming the sizes each shows (point 1);
  - where its brand gives a size whose type is larger, such as `projector` for a room, the piece drawn at that size, with the medium naming it in place of the run's size. A size added alone mends nothing, since the medium still shows the run's.
- **It fails** ([visual-communication:DEC-002-files-and-validation] point 7). This record owns the invariant, and the project corrects a break of it in its own files: its content's styles and options, its own components, a brand of its own built on another, or the sizes the piece names and the media that show each.
- **Given scene by scene.** The check gives each finding in the scene that finds it (DEC-063 point 1). The finding carries that scene's language and key, and the page the run lies on. It merges none across scenes or pages. A run under the smallest size of several media is one place, and takes one finding that names each.
- **Merged by the render's code alone,** for the findings record, as every scene finding is. That code gives a finding once where every key finds it alike, and otherwise for each key, its message opening with the key. It gives once a finding in a field the top draws on every page.
- **Where it measured nothing,** the check states so (point 10).

### 7. What the check refuses

When it reads the piece and the component, the check reports:
- in a piece's `media`: a list or a mapping that names no medium; a word the capability does not name; in its list, a word named twice; in its mapping, a medium that names no size, a size named twice under one medium, or a size the piece is not drawn at; each as `piece-unreadable`, as a mode the brand lacks is. A medium a mapping names twice is a key written twice, which the reader refuses in every file of the capability's format (`file-unreadable`; the files' page, "How the files are read");
- `smallest-text` on a component that is no top, or on a brand's drawing; a key in it that names no medium; and a value that is a number not positive, or a switch, each as a key or a value its format does not allow (`component-shape`);
- a formula that gives no length, or reads anything but `:width`, `:height` and numbers, as a formula's own findings (`formula-dimension`, `formula-reach`).

When it computes a scene, a share may give no smallest size at a page, in three ways:
- **It reads `:height` at a page that asks for no height.** That is a formula that reads what it may not reach (`formula-reach`).
- **It divides by zero there.** That is a formula's own finding too (`division-by-zero`).
- **It gives a length of zero or less there,** such as a difference of the page's width and height on an upright page. That is a value its format does not allow, as a number not positive is (`component-shape`).

Each is reported as severely as any formula's finding (DEC-005 point 14), and names each such page:
- **Where the top alone shows it,** it lies at the top's file, at that medium's value. A page of the top's own that asks for no height is such a case.
- **Where only the lock's combination of versions shows it,** it lies at the piece's lock and names no version. A brand's drawing, or a page a slot places, may show it so. Every fault that only a lock shows lies so (the list of checks, "Under a lock").
- **Beside it, the check states its own fact** for that page (point 10). A formula's finding is another check's, and says nothing of what this check measured.

### 8. The shipped tops declare it, each value with its source and the measure that source states

- **The foundations' tops** declare a smallest size for each medium their pages are made for, as each top's account of its pages names those media.
- **Each value names its source beside it,** a standard or a guideline of legibility for that medium, and the measure that source states. Which media a top declares, and the value for each, are the foundations' data, reviewed in the change that sets them, as a brand's scales are.
- **A source may state another measure than a font size.** The display image size standard that DEC-028 point 10 names for a projected image (ANSI/INFOCOMM V202.01) is one. Its publisher's account of its terms states the height of an *element* in relation to the image's height ([AVIXA, "Display Image Size"](https://www.avixa.org/standards/discas-calculators/discas/learn-more-about-display-size)). An element there is a group of pixels that conveys an item of information, such as a character, and its share varies with the content. A character stands less tall than its font size.
- **A value from such a source says how it became a font size:** the share the source gives, and the share of its font size a character is taken to stand at.
- **This record sets no value, and rests none on that standard.** It rests on the publisher's account of the terms alone. The standard's own text, its range of shares and its formula are not read here. The work that sets a room's value reads the standard first, in the edition it cites.

### 9. An addition, which reaches a piece through its media and its lock

- **Format 1.** `media` on a piece, in either form, and `smallest-text` on a top are optional, so every file format 1 accepted reads and draws as before ([visual-communication:DEC-003-change-over-time] point 3). A medium the capability names later is an addition too, since it refuses no word accepted before.
- **A top that comes to declare one, or raises it,** renames and removes nothing, so it breaks nothing (DEC-003 point 6). A draft moves to it at its next render, as to any newer version the project holds, and may then fail where a text is too small (DEC-003 point 8).
- **So a piece is held to it only where it names a medium,** at the sizes that medium shows, and the version of its top that its lock names declares that medium's smallest size. Elsewhere the check states the fact of point 10.

### 10. Where it could measure no text's size, the check states so, as a fact

The check states one fact, `text-size-unmeasured`, in four cases. Each statement names how far it covers, in the terms of DEC-063 point 2:
- **A piece that names no medium:** the scene, in every language and at every key.
- **A medium the piece names whose smallest size its top does not declare:** each key that medium shows. The statement names the medium and the top, and the sizes that medium shows where the piece maps its media.
- **A size the piece is drawn at that no medium shows:** each key at that size, which the statement names.
- **A page where a share gives no smallest size** (point 7): that page, at each key where it happens. The statement names the medium.

What holds for each of them:
- **It covers every run of text there.** A run it covers counts as not measured, whatever else the check compared it with (point 12).
- **A finding of this check, given scene by scene.** The check's code states it when it computes a scene, with the scene's language and key, and its page where it covers one. That holds even where the piece's file alone shows the cause, as for a piece that names no medium. A statement that holds in every language, or at every key, says so in place of naming one (DEC-063 point 1). So the findings record keeps it, and the viewing step's report gives it (DEC-063 point 2, DEC-062 point 1).
- **Where it lies:** `<piece>/piece.yaml#media`, and for a page, at the page's trace in that file.
- **A fact,** which fails nothing and asks no act (DEC-063 point 2). So a reviewer sees each medium no text's size was measured in, at which sizes and on which pages, and each size no medium shows.

### 11. The check states its reach

A scene check whose silence a reader leans on states its reach (DEC-063 point 1). It states it in its entry and in its code, beside an id of its own. The reviewer's instructions read this check's silence (DEC-046 point 5), so the change that lands the check states its reach. This record decides its clauses:
- **It measures:** the font size of each run of each text a page draws, as the scene holds it. It measures that size against the smallest size the piece's top declares for each medium that, as the piece names it, shows the scene's key. It takes the page at its own size, as its medium shows it (points 3 and 4).
- **It leaves out:**
  - **Words inside a picture** (DEC-046 point 5).
  - **How large a face's letters stand in their font size** (point 4).
  - **How a viewer shows a page:** a width other than the brand's, a zoom, and a scale a presenter or a print sets (point 3).
- **It states** `text-size-unmeasured`, in the four cases of point 10, each with what it covers.
- **It compares scenes across no axis.** Each of its findings rests on its own scene alone, and its code says so (DEC-063 point 1).
- **Every other path its code passes over** is found by the audit DEC-063 point 1 asks of the work. Each becomes a clause that cites its record, or a statement. One that departs from this record is fixed, or filed and stated meanwhile.

### 12. How the check's silence is read, and what the review reads

- **Per run, and never per medium.** A run counts as measured and clean only where no statement covers it and the check gave no finding on it. A run a statement covers counts as not measured, though the check compared it with another medium's smallest size. DEC-063 point 3 reads it so, and this record changes none of it.
- **A finding stands for each medium it names,** whatever a statement covers. So a text under a medium's minimum stays the check's finding alone, and lowers no grade (DEC-046 point 5).
- **Where the check did not measure,** the review reads as DEC-046 point 5 says. It judges a text's size only as far as the image shows that the text cannot be read where the piece is shown. Its report names the statement in one line.
- **Measured for its size alone.** The check measures a run's font size against the smallest sizes of the media the piece names. A run measured and clean was measured for that, and for nothing else (DEC-063 point 3). Whether it can be read as drawn stays the review's. So a text that cannot be read where `shown` says, in a medium `media` does not name, blames no check.
- **The review reads `media` beside `shown`.** The reviewer reads the piece's file, and `media` in it. Where the piece names for each medium the sizes it shows, the review reads an image as shown in the media that show its size. It takes the place there from `shown`, as the rule has it. Where `shown` and `media` disagree, its report says so in one line, and it judges by `shown`.

### 13. A calibration measures every text's size, and the verdict ends a loop only on a piece measured so

A piece is held to the check only where it names a medium (point 9). So the review runs in two states: with every text's size measured, and with some or none.
- **A calibration runs in the first.** Its held-out ladder names its media, under a top that declares the smallest size of each. So the check measures every text's size on it, and states `text-size-unmeasured` nowhere. Its report names those media and smallest sizes (DEC-046 point 8).
- **The hold reaches a piece only in that state.** Where a project's bar covers `RS-GRAPHIC-005`, the verdict ends the designer's loop on a piece only where the check measured each image the review read. The viewing step's report then names the check for each of those images, and gives no statement of it for any (DEC-062 point 2). Elsewhere the verdict informs, and the loop ends as DEC-030 point 2 says. DEC-042 point 10 comes to say so (Implications).
- **Where the command cannot tell,** the verdict informs.
- **The smallest sizes lapse no hold.** They are each top's own, and differ from piece to piece by design. A text under one fails, and the designer mends a check's failure before any review (DEC-042 point 6). So under the hold the review grades no page that holds one. The check's code, its reach and its statements lapse the hold as every check's do (DEC-062, Implications, "What lapses the hold").

## Rationale

**Why a check, and not the review.** Comparing a run's size with a number needs no judgement, so DEC-028 point 1 gives it to a check, and DEC-042 point 2 and DEC-046 point 5 keep it there. What `RS-GRAPHIC-005` asks in its own words stays the rule's: that "everything on a page can be read where the piece is shown", and that a page is taken in at a glance. A run at the smallest size may still not read as drawn, and the review judges that on the page.

**Why the piece names its media.** Where a piece is shown is the piece's, as the person who makes it already says in `shown`. Its size does not say it. A piece that names no size is drawn at `desktop` (DEC-021 point 3), and under a brand with no size it can name no other (DEC-021 point 2). So a smallest size chosen by the size would hold a deck projected in a room at the default size to a slide's on a desk, the case in Context, and under such a brand the piece could not mend it. Nor does the top say it, since one top's pages reach readers in several media, and one page file may be read on a laptop and projected.

**Why the capability names the media.** A word the capability names means the same under every top. So a command reads a piece's media with no top, a reviewer reads them beside `shown`, and a piece that switches its top keeps them. How a page reaches the eye is the format's to name, as the formats of a piece's exports are, and no library's look. A medium needed later is an addition to the format.

**Why the top holds the values.** How small a text may be in a medium rests on how far the reader sits from what shows the page, and how large the page stands there. A poster on paper is read from metres away, and a figure in a printed document from a hand's length. A slide fills a room's screen, and a web page keeps its own size on a screen at hand. These are facts of the kind of page and its size, which the top names.
- **In its data.** The engine knows no top by name (DEC-001 point 4), so the top says it in its data. A project's own top, such as a poster, then declares its own with no change to the foundations.
- **As its physical size is.** A physical size is the top's for the same reason: a fact of the pages the top makes, which no brand gives (DEC-034 point 3). This record is the second to read DEC-001 point 5 that way, after DEC-034. That point comes to name both facts, so that a third reads the class there rather than anew (Implications).
- **A second threshold a library declares.** The foundations declare the pairs of colour roles that must contrast, each with the level it must reach, and the check holds every brand to them in every combination (DEC-004 point 8). The smallest size is the second such threshold.

**Why no brand sets it.** The brand gives the sizes the check measures. A smallest size it gave would be held to itself, a brand built on another could lower it, and two brands would hold one piece to two smallest sizes in one medium. Contrast is kept so already: the brand gives the colours, and the level a declared pair of the foundations' roles must reach is the foundations', never a brand's (DEC-004 point 8). So the declaration reads no role, and a brand reaches it only through the size of the page it gives.

**Why two forms.** Each form fits how one kind of medium shows a page:
- **A fixed length for a screen at hand.** It shows a page at its own size where its window holds it (DEC-020 point 4). CSS sets a px by the angle it takes at arm's length. So a fixed px is a size its reader sees.
- **A share for a room.** A room's screen shows a page as large as its image, whatever its px. So only a share of the page says how large its text stands in the room. The standard on projected images states an element's height in relation to the image's height too (point 8).
- **A share for a sheet.** A sheet takes a page at the top's physical size by one scale, so a share of the page is a size on paper.
- **The top chooses,** since which form fits depends on the kind of page as well as the medium. Neither form reads more than the page's size, so neither lets a brand in.

**Why a share reads a height only where a page asks for one.** A page as tall as its content would move its own smallest size with every line it gains. Whether a page asks for a height is not the top's alone: a brand's drawing of a page alone writes its own height, and the part that places a page in a top's slot gives it its size (DEC-034 point 2). So the check looks for a share's `:height` where the formula reads it, on the scene, page by page. From the component alone it finds only what the formula's own text shows, its dimension and its reach.

**Why a share's fault lies at the top, or at the lock.** A top whose own page asks for no height shows the fault alone, so the fault lies in that top, where its owner mends it. Under a brand's drawing, or at a page a slot places, neither version is at fault alone. A finding in a released top would then ask its owner to mend what only a combination shows. So it lies at the lock, as every fault that only a lock shows does.

**Why the check states its own fact beside a formula's finding.** The formula's finding says that a formula could not be worked out. It is another check's, which states no reach, so it says nothing a reader may take for this check's silence. With no statement of this check's own, the texts of that page would read as measured and clean (DEC-063 point 3). DEC-046 point 5 has the check state a text whose minimum it cannot work out, in the piece where it meets one.

**Why the brand's width stands for the width a page is shown in.** The check knows no reader's window or document's column. The brand's width at a size is the one statement the files make of it: how wide a page is drawn for that device (DEC-021 point 1, DEC-022 point 3). Against any other width the check would need one no file gives. So on a screen at hand, a brand that draws its pages wider than its devices' windows shrinks every text there, and the check does not see it, as it does not see a reader's zoom. In a room it does not escape, since a share reads the page's own size.

**Why a piece may name the sizes each medium shows.** Each size a piece is drawn at has a scene and files of its own (DEC-005 point 6, DEC-023 point 1), and which file is shown where is the piece's to say, as its media are.
- **Held each to each,** a deck drawn at `desktop` for a laptop and at `projector` for a room would hold its desktop texts to the room's smallest size too, a bar the laptop's reader does not need. Where its brand gives the slide one width at both sizes, as the neutral brand does, that bar is one length at both, and the projector's larger type would gain the check nothing.
- **A list still has each medium show every size.** So a deck that names no size, or whose brand gives none but the default, is held to the room at `desktop` ("Why the piece names its media").
- **A size no medium shows is stated.** A mapping names only sizes the piece is drawn at, so each medium it holds shows one size at least, and a size no medium shows is stated, never passed in silence.
- **The cost.** The check cannot tell that the file shown in a room is the one the media name, as it cannot tell that a piece is shown where its media say.

**Why the page's size, and not the top's.** The smallest size is about the page as its medium shows it. For a page alone, and for a top whose layouts are its pages' forms, as each top the foundations ship is, the two are one. A top whose slot holds pages of their own sizes would otherwise hold each to the top's.

**Why the font size.** It is what a typography role gives, and what the scene holds for each run. So the check reads it with no font's measures, and a brand's author sets it directly.
- **Not every source states it.** The standard on projected images states an element's height in relation to the image's height (point 8). A value from such a source is converted once, where the top declares it, and says how.
- **The letters' height is a reading's.** How tall a face's letters stand in their font size differs by face. The drawn page shows it, so the review judges it, under the rule.

**Why at each key.** A brand's values and a page's size both differ by key, and each key has its own scene (DEC-005 point 6). A key's larger type is the piece's way to meet a stricter medium that shows it, so each key is measured with its own values.

**Why one finding for every renderer.** A renderer projects the scene and adds no size (DEC-001 point 2). What differs between formats is how a viewer shows a page, and no file records it. Measuring each renderer's output would measure what the reader or the presenter sets, and would report one fault several times.

**Why at the piece's file.** A run's size is the brand's value for the role the component chose, held to the top's smallest size for the medium the piece names: three libraries and the piece together, none of the libraries at fault alone. Contrast is such a combination too, and its finding lies at the piece's file and names no version, so its level stands. The piece's author mends it in the project's own files. A finding at the component's part would lie in a released version and only ask its owner for attention, while every piece that used the component stayed unreadable.

**Why it fails.** A text too small for its medium is lost to its reader, as a text that spills out of its box is, and DEC-028 point 1 gives both to the checks alike. The project corrects it in its own files (DEC-002 point 7). It holds a piece only where the piece names a medium and its lock names a top with a smallest size for it, so an upgrade of the capability alone fails no piece.

**Why a fact where nothing is measured.** DEC-046 point 5 has every check of a text's size state where it measured none. DEC-063 point 2 makes that statement a fact, and each gives its reasons. This record adds only which cases the check meets. None asks an act: every piece written before this record names no medium, and a piece may lock an older top on purpose.

**Why the statement is given when a scene is computed.** A piece that names no medium could be found with no scene. But the viewing step's report gives only what a check finds on a scene (DEC-062 point 1). That report is what tells the reviewer (DEC-046 point 5). A statement found elsewhere would reach validation and never the review.

**Why the check gives its findings unmerged.** DEC-063 point 1 asks it of every scene check. A check that merged its own findings would give one finding for many places, and the report could place it on one image only. The other images would read as measured and clean (DEC-062, "Why the image is the unit").

**Why the reach is decided here.** A clause that says a check measures a kind of place comes only from that check's record (DEC-063 point 1). With no reach, the check's silence counts for nothing, and the report names it for no image (DEC-063 point 1, DEC-062 point 2). The check would then never land for the reviewer, and the calibration that waits for it could not run (DEC-062 point 4).

**Why silence is read per run, and not per medium.** A check of colour is read per combination, since each image shows one combination (DEC-063 point 3). A medium picks no image: one image of a deck's `desktop` pages is shown on a laptop and in a room alike. So a reading per medium would tell the reviewer nothing more of the image before it. The statement already names the medium, and the review's report repeats it in one line.
- **It fails safe.** A run read as not measured costs the reviewer its own judgement of that text, which errs toward naming a text that cannot be read. A run read as measured where a medium went unmeasured would pass a text nobody compared.
- **It changes no accepted record.** A reading per medium would refine DEC-063 point 3 and DEC-062 points 1 and 2, and give the report's findings and reaches a medium. Those records are what the reviewer's instructions and the report are being built on.
- **What it costs.** Where a piece names two media and its top declares one, the check's measurement in the declared one is lost to the review. The review then judges those texts on the image, though the check passed them for one medium. A finding still stands for its medium, so no small text fails twice. The piece's author ends the cost by naming only the media the top declares, or by a top that declares both.

**Why a run is measured for its size alone.** DEC-063 point 3 reads a place as measured only for what its check measures. This check measures a font size against the smallest sizes of the media the piece names. So a text that cannot be read in a place `shown` names and `media` does not is a fault of its own kind. It would otherwise blame a check that did as the piece told it.

**Why the review reads `media`.** A piece that maps its media says which of its sizes each medium shows. The review reads each image as a reader would where the piece is shown (DEC-046 point 5). Without `media`, it would read a laptop's page as projected, and name a text too small to read in a room that never shows it. The check would hold that page to the screen's smallest size, and the review to the room.
- **No new input.** The reviewer already reads the piece's file.

**Why a calibration measures every text's size.** DEC-046 point 8 holds the calibration back for this check, so that the review is tested as it runs. With the check, a text under its medium's minimum is the check's and lowers no grade. Without it, the review judges that text on the image. A ladder that named no medium would test the second state, the one the wait was meant to end.

**Why the hold reaches only a piece measured so.** The verdict ends loops by what a calibration measured (DEC-042 points 9 and 10). A calibration measures the review beside a check that takes every small text. On a piece that names no medium, nothing takes them, and the review says only what the image shows. So the verdict would end a loop there for a review that does not run as it was measured (DEC-046 point 8).
- **It fails safe.** A verdict that informs is safe, as a lapse is (DEC-042 point 9).
- **What a project does.** A project that wants the verdict to end its loops says where its pieces are shown.

**Why the smallest sizes lapse no hold.** DEC-042 point 9 lapses the hold on what could move the grades, compared with the accepted data. A smallest size decides only which texts are the check's alone. Under the hold, those texts fail, and are mended before any review (DEC-042 point 6). And the values are each top's by design, a project's own top among them, so no accepted data could hold every piece's.

### What it costs

- **A reach for the check,** in its entry and its code, with a test that holds the two equal. Each clause and statement takes a planted case, and each change to the check repeats the audit (DEC-063 point 1).
- **The reviewer's own judgement** of each text a statement covers, a text the check compared with another medium among them (point 12).
- **A narrower hold,** for a bar that covers `RS-GRAPHIC-005`. The verdict ends no loop on a piece that names no medium, or whose top declares none for a medium it names (point 13).

### Alternatives considered

- **The top's smallest size chosen by the size the piece is drawn at, with a fact naming the branch that chose it.** Rejected: a piece that names no size, or whose brand gives none, would be held to a slide's on a desk wherever it is shown ("Why the piece names its media"). The fact would show that, and mend nothing.
- **One smallest size for each mode of the size axis, in the foundations.** Rejected, for the same reason, and since at `desktop` a slide fills its screen and a web page does not, so one number would hold one of them wrongly.
- **Media each top names, which a piece picks among.** Rejected: a medium would mean what each top says, so no command or reviewer could read it without the top, and a piece that switched its top could name a medium the new top lacks ("Why the capability names the media").
- **Media the foundations declare, as they declare the shared axes.** Rejected: a medium is neither a value a brand varies nor a structure, and a piece's medium would then mean only what its locked foundations say.
- **A table of each medium's smallest size, in the capability.** Rejected: how small a text may be in a medium depends on the kind of page and its size ("Why the top holds the values").
- **Each size held to each medium the piece names, always.** Rejected: a deck drawn for a laptop and for a room would hold its laptop's texts to the room's smallest size, a bar its laptop's reader does not need ("Why a piece may name the sizes each medium shows").
- **A deck shown in two media made as two pieces, one for each.** Rejected: one design laid out at each size a person chooses is what the size axis is for (DEC-021, Context), and two pieces would keep one content twice, to drift apart.
- **Every medium paired with its sizes, with no list.** Rejected: a piece that names no size, or shows each size in each medium, would name its sizes for nothing, and gain a new size unmeasured.
- **The medium read from the piece's `shown`.** Rejected: no command reads a medium from words.
- **The field named `seen-in`, in place of `media`.** Not taken here: `media` keeps the word DEC-028 uses for how a page reaches a reader's eye, and the Terms set it apart from a renderer's. Against it, the capability already calls the format a renderer draws into a medium (DEC-001 point 2), so `media` on a piece may be read as the formats it is drawn into, which its exports name. `seen-in` meets no word the capability uses. A rename once format 1 accepts the field would refuse what it accepted, which waits until validation reads older files (DEC-003 point 3), so the name is chosen before the field ships.
- **The statement's label saying *unjudged*.** Rejected: a check measures and never judges (DEC-063, Context), and the label ships, so its word is chosen before it does. The statement of the check of edges that nearly line up says *unmeasured* too.
- **A role a brand gives, such as a smallest type size.** Rejected: the brand would set the smallest size it is held to ("Why no brand sets it").
- **A setting in the capability's configuration.** Rejected: one smallest size for a project cannot tell a slide from a web page. A project's stricter taste is a rule set of its own (DEC-028 point 1).
- **A table in the check, by the top's name.** Rejected: the engine knows no top by name (DEC-001 point 4), and a project's own top would have no entry.
- **A share of the page for every medium.** Rejected: a web page is as tall as its content, and a screen at hand shows a page at its own size, so its reader's px stay what they are whatever the page's width.
- **A fixed length for every medium.** Rejected: a room's screen shows a page as large as its image, whatever its px, so a page's px say nothing of how large its text stands there.
- **Measuring each export by how its viewer shows a page.** Rejected: the window, a zoom and a print's scale are the reader's or the presenter's, and no file records them ("Why one finding for every renderer").
- **A smallest size for each renderer, from its declaration.** Rejected: a renderer adds no size ("Why one finding for every renderer").
- **The height of the letters, such as the x-height, in place of the font size.** Not taken, though it is nearer what the standard on projected images states (point 8). The scene holds a run's font size and no height of its letters. That height differs by face, so a brand's choice of face would move what a top declares. A value converts once instead, and the review judges a face whose letters stand small ("Why the font size").
- **The finding at the component's part that chooses the style, or at the brand's role.** Rejected ("Why at the piece's file").
- **A share's fault always at the top's file.** Rejected: under a brand's drawing or in a slot, it would lie in a released version not at fault alone.
- **A formula's finding alone where a share gives no smallest size.** Rejected: the texts of that page would read as measured and clean ("Why the check states its own fact beside a formula's finding").
- **Asking for attention, never failing.** Rejected: an overflow and too little contrast fail, and DEC-028 point 1 gives all three to the checks alike.
- **The top's own size in the share's formula.** Rejected ("Why the page's size, and not the top's").
- **A piece that accepts a text too small, for a run or at a size, as it accepts a loss.** Not taken: the piece drawn for two media, the need "Why a piece may name the sizes each medium shows" names, says where each size is shown, which is a fact and accepts no fault. A text too small for the medium that shows it is lost to its reader whoever accepts it. Allowing it later is an addition.
- **The viewing step's smallest size as the medium's.** Rejected: it sizes images for whoever reads them, and says nothing of where a piece is shown.
- **The leave-outs learnt from the check's entry in the list of checks.** Rejected: the reviewer reads a check's reach from the report of the run it reads (DEC-062 point 3).
- **The check's silence read per medium, as a check of colour's is read per combination.** Not taken, though it keeps the measurement in one medium where another went unmeasured. A medium picks no image, so the reviewer gains nothing it can read on the image before it. It would also refine two records and the report's form ("Why silence is read per run, and not per medium"). A later record may still refine DEC-063 point 3 so, if pieces often name a medium their top does not declare.
- **`media` kept from the review.** Rejected: under a mapping the review would read a laptop's page as projected ("Why the review reads `media`").
- **The hold reaching every piece, with the gap named in the review's report.** Not taken. It edits nothing in DEC-042, and the review's reading of a page is the same in both states. But a loop would end by the verdict on a piece whose small texts nothing compared. Its evidence was gathered beside a check that compared them ("Why the hold reaches only a piece measured so").
- **A calibration in each state,** with evidence for each. Rejected: two ladders and two sets of evidence for one rule, to let loops end where a piece does not say where it is shown.
- **`media` required of every piece.** Rejected: format 1 would refuse files it accepted (DEC-003 point 3).
- **The smallest sizes compared with the accepted data, to lapse the hold.** Rejected ("Why the smallest sizes lapse no hold").

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - **DEC-001 point 5, "Roles stand between structure and values,"** comes to add that a fact of a top's pages that no brand gives is the top's to hold, and no raw value, since no role may stand for it: its physical size (DEC-034 point 3) and the smallest text size it declares for a medium (points 2 and 3).
  - **DEC-005 point 1, "What it may use,"** comes to add that the formula of a top's smallest text size reads only the size of the page a run lies on, as `:width` and `:height`, and numbers (point 3), as `cross-size` alone reads `:place` and `:places` ([visual-communication:DEC-038-size-by-place] point 2). Its "Where lengths come from" stands, since a fixed smallest size is no formula's, and DEC-001 point 5 comes to name it no raw value.
  - **DEC-005 point 14, "Fails validation,"** comes to add a text drawn smaller than the smallest size the piece's top declares for a medium that, as the piece names it, shows the key it is drawn at (points 4 and 6).
  - **DEC-028 point 10,** at its words "A smallest text size for a medium is a check's, run always (point 1)", takes the pointer alone, and decides nothing new. The rest of that sentence, as DEC-046 edits it, stands.
  - **DEC-042 point 10,** after the bullet "Any project within what was calibrated", gains a bullet: "**Only a piece whose texts' sizes were measured.** Where the bar covers `RS-GRAPHIC-005`, the verdict ends the loop on a piece only where the check of a text's size measured each image the review read. The check must also have stated for none of them that it measured no text's size. Elsewhere, and where the command cannot tell, it informs (refinement per [visual-communication:DEC-055-smallest-text-size] point 13)." It narrows the point.
  - **DEC-046 point 5,** the bullet "'As it was drawn' takes in where the piece is shown". After "The review takes the place from that declaration.", it comes to add: "Where the piece names for each medium the sizes it shows, the review reads an image as shown in the media that show its size, and takes the place there from that declaration (refinement per [visual-communication:DEC-055-smallest-text-size] point 12)."
  - **DEC-046 point 8,** after the sentence DEC-062 added on when a check has landed, comes to add: "A calibration's ladder names its media under a top that declares the smallest size of each, so that the check of a text's size measures every text's size on it (refinement per [visual-communication:DEC-055-smallest-text-size] point 13)."
- **Read against this record, and left as they stand:**
  - DEC-001 point 2, since a renderer still adds no size, and what a viewer does is no renderer's.
  - DEC-001 point 3, since `media` is a field a check selects a piece by, which that point lets a piece declare, and `shown` stays words.
  - DEC-002 point 7, since the finding follows its policy, and its "Attention or a fact" already names a check's statement that it could measure nothing.
  - DEC-003 points 3, 6 and 8, since the field, the key and a medium named later are additions, and a smallest size added or raised breaks nothing (point 9).
  - DEC-004 point 8, since the pairs a library declares, and the level each must reach, stay its own, and the smallest size is a second threshold of that kind, declared apart from the brand whose values meet it.
  - DEC-005 point 3, since the formula of a smallest size reads no part: its `:width` and `:height` name the size of the page a run lies on, a page of the top's own or one its slot places, so it reads nothing above the top.
  - DEC-005 point 13, since the statement is a scene finding the findings record keeps like any other.
  - DEC-015 point 5, since the viewing step's smallest size stays its own.
  - DEC-016 points 1 and 2, since `media` passes the first's test, as the losses a piece accepts do, and the findings key still reads the piece's file whole. The reference's list of the fields an export leaves out gains it, as point 1 has a change do.
  - DEC-020 points 2 and 4, since a page's lengths stay shares of its width, and a page still shrinks with a narrower window and keeps its own size in a wider one. The check takes it as point 3 says.
  - DEC-021 points 1 to 3 and 8, since a size mode still chooses a brand's values and a component's shape, and chooses no medium, and a page file still holds one size. A piece names its media, and the sizes each shows, whatever sizes its brand gives, and this record reads a key's size as DEC-021 point 3 has a component read it.
  - DEC-022 point 3, since a page's width at a size stays the brand's, which the check takes as the width a page drawn at that size is shown in, and a page that asks for no height stays as tall as its content, whose height no share reads (point 7).
  - DEC-023 point 1, since a file still serves one size, the unit a medium's sizes name.
  - DEC-026 point 4, since the sheet and its scale stay the reader's.
  - DEC-028 point 1 and the rest of point 10, since the smallest size stays a check's.
  - DEC-030 point 7, since what a check measures stays the check's, and the reviewer, which reads the piece's file, runs nothing more to read `media`.
  - DEC-034 point 3, since a physical size stays the top's, which DEC-001 point 5 comes to name beside the smallest size, and a share of the page keeps its share on paper.
  - DEC-042 point 2, since the check it names is this one, and point 9, since its list of what lapses the hold gains nothing from this record (point 13).
  - DEC-046 point 5's other bullets, each for its own reason:
    - **"Who says where no text's size was measured":** this check states words inside a picture in its entry. It states in the piece each text whose minimum it cannot work out (points 4 and 10).
    - **"No small text fails twice"** holds through a finding that stands for its medium (point 12).
    - **"While the capability ships no such check"** holds, image by image, wherever the viewing step's report names no such check, as DEC-062 reads it. On a piece that names no medium, the check is named and its statement covers the scene, so the review names that statement.
  - DEC-062 points 1 to 4, each for its own reason:
    - **Point 1:** the check is a scene check, so the report gives its findings and statements with no special case.
    - **Point 2:** the report names it for an image, and carries its reach, as for any check with a reach. The report's form gains no medium, since silence is read per run (point 12).
    - **Point 3:** the reviewer reads the check from the report alone.
    - **Point 4:** the check lands for a calibration as that point says.
  - DEC-063 points 1 to 4. The check states its reach and its statements as points 1 and 2 ask, and each statement names what it covers in point 2's terms. Point 3 reads its silence unchanged (point 12), and point 4's bullet on a check of a text's size stands.
  - `RS-GRAPHIC-005`, which judges a page where the piece is shown "as its `shown` field names", and rests on DEC-028 point 10, which this record edits. It holds as it stands: the review still takes the place from `shown`, and reads `media` only for which sizes each medium shows (point 12). What the rule asks, that "everything on a page can be read where the piece is shown" and a page is taken in at a glance, stays the review's.
- **The order.** [project-kit#3185](https://github.com/aleskalfas/project-kit/issues/3185) builds on the code [project-kit#3335](https://github.com/aleskalfas/project-kit/issues/3335) split, which gives each finding with its check's id, scene by scene. It lands the check that DEC-046 point 8 and DEC-062 point 4 have the calibration wait for. The reviewer's reading of what the check reports is [project-kit#3328](https://github.com/aleskalfas/project-kit/issues/3328)'s, which also words the reading of `media` (point 12).
- **#3185 builds points 1 to 12** in the engine, the schemas of a piece and of a component, and the check. It sets which media each of the foundations' tops declares. Each value takes its source, the measure that source states and its conversion (point 8). It reads the display image size standard itself before it sets a room's value from it.
- **The check's reach, in #3185's change** (point 11, DEC-063 point 1):
  - The check's entry states its reach and its statements, and shows the check's id.
  - The check's code states them in the entry's words, beside that id, and states that it compares scenes across no axis.
  - A test joins the entry and the code on the id, and holds the two texts equal.
  - The check gives its findings and statements scene by scene, unmerged (points 6 and 10).
  - An audit finds each path on which its code passes over a run. Each is made a clause or a statement, or is a departure, fixed or filed.
- **Its tests:**
  - **For each medium the shipped tops declare,** a text below and a text at its smallest size.
  - **For each clause of the reach,** a planted case. A run below a medium's smallest size is reported. Words inside a picture give no finding, and nor does a face whose letters stand small for their size.
  - **For each statement,** a planted case that states it with what it covers, in each of point 10's four cases. A medium its top declares nothing for is planted in a list and in a mapping. A share that gives no smallest size is planted in each of point 7's three ways.
  - **For a piece of two media whose top declares one,** that a run below the declared medium's smallest size is still reported, beside the statement.
  - **For a deck that names `media: [room]` and no size,** that its texts at `desktop` are held to the room's.
  - **For a deck drawn at `desktop` and `projector`,** each form of mapping. `media: {screen: [desktop], room: [projector]}` passes with desktop type below the room's smallest size and at the screen's, and states nothing. `media: {room: [projector]}` states the fact for `desktop`.
  - **For each refusal of point 7,** and for where a share's fault lies: at the top's file, and at the lock.
  - **For the viewing step's report,** that it names the check for an image, carries its reach, and gives each statement to the images it covers.
- **The pages and files #3185 changes:**
  - **The list of checks.** Its table of the scene checks gains the check's row, with `text-too-small`, `text-size-unmeasured` and its reach. The rows `piece-unreadable`, `component-shape`, `formula-reach` and `division-by-zero` widen (point 7). Its line on the findings that lie at `piece.yaml` and name no version gains both labels. Its list of the fields an export leaves out gains `media`.
  - **The files' page,** whose table of `piece.yaml` gains the field, in both its forms.
  - **The components' page:** the key in the table of a component's file, and a section beside "A physical size".
  - **Each shipped top's account** of the media its pages are made for.
  - **The account of the size axis's modes,** in the foundations' roles file and on the files' page. It comes to say that a mode names what a piece is drawn for, and the piece's media where it is shown.
  - **The command that starts a piece,** which takes the media as it takes where the piece is shown. The skill's page on a piece and the designer's agent file name the field beside `shown`.
- **The hold.** The command that gives the verdict comes to tell whether the check measured each image the review read (point 13). It needs to tell so only for a bar that covers `RS-GRAPHIC-005`. #3185 files that as a follow-up, beside [project-kit#3296](https://github.com/aleskalfas/project-kit/issues/3296), which has the command compare the checks the review reads. Until it lands, the command cannot tell, so under such a bar the verdict informs.
- **The foundations take a new version** whose tops declare their smallest sizes, released as the capability's shipped libraries are ([visual-communication:DEC-013-shipped-library-releases]).
- **No migration.** The field and the key are additions, and nothing a project holds changes (COR-010).
- **Revisit this record** in each of these cases:
  - A medium is found to show pages otherwise than point 3 takes as given. An example is pieces shown in rooms from page files kept at their own size.
  - A file an export makes comes to serve more than one size, since a medium's sizes name files.
  - A second size axis is declared, since a medium's sizes are modes of one axis (point 1).
  - Pieces often name a medium their top does not declare, since the reading per run then loses measurements the review could use (point 12).
