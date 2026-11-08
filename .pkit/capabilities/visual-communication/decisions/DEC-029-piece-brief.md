---
id: DEC-029
title: A piece's brief, one file beside its content, says what the piece must show and why it is designed so
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a piece may keep a *brief*, one file in its folder beside its content. The content says what the piece shows, in each language. The brief says what the content does not. It says what each picture must make visible, what the piece is for, and a page's point where the page states none. It also says why each choice of its design was made, each reason naming the design principle it rests on. It is written for whoever makes or reviews the piece, never shown and never translated. It has a part for the whole piece and a part for each page, so it serves a deck, a figure and a site alike. No command changes what it says.

## Context

A piece holds its content in each of its languages, and names the libraries it uses ([visual-communication:DEC-001-visual-communication-discipline] point 3). Its own file declares who it is for, where it is shown and whether it explains. Nothing says what its pictures must show, or why they look as they do.

The showcase deck of the repository the capability is authored in shows the cost ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)):
- **The point was lost in the port.** A slide on how the methodology fits together was first drawn as a stepped pyramid: narrow and darkest at the top, so a reader saw that decisions are the source and each layer carries out the one above. Moved into the capability, it became five equal bars in five unrelated hues. Equal widths show no order, and five hues say "five unrelated kinds".
- **Nothing could catch it.** Every check passed, and the drawing had no fault a reviewer of drawn pages looks for. That the order was the slide's point was written nowhere, so no reader of the files could know it was gone.
- **The reasons went with it.** Why the pyramid narrowed, and why its shades ran from dark to light, lived in the head of whoever drew it.

The maintainer has asked for a reason behind each page, item, place, colour and font of the capability's visual work ([project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584)). A reviewer can judge a drawing against its intent only where the intent is written down. A later designer can change one choice without breaking another only where the reasons are.

Three places could hold it. Two of them already have a job:
- **A content file** holds what the piece shows in one language. A second language is a second file of the same shape (DEC-001 point 3).
- **The piece's own file** holds its lock, which a draft's render rewrites ([visual-communication:DEC-002-files-and-validation] point 5).
- **A file of its own** in the piece's folder would hold the brief alone.

On 31 October the maintainer decided that the brief would be a field of each content file ([project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584)). A field there would be copied into every language, translated, and read as text the audience reads. This record puts the brief in a file of its own in place of that choice.

The capability's files are written so that a later refinement can read them as artefacts, with rules and anchors on their parts (DEC-002 point 4 and Implications).

## Decision

**A piece may keep one brief: a file of its own in the piece's folder, in the capability's format, which no renderer reads and no command changes the meaning of. It holds what the content does not: the relations each picture must show, the piece's goals, a page's takeaway where the page has no lead, and the reasons for its design, each naming the principle it rests on. It has a part for the whole piece and a part for each page it speaks of, keyed by the page's id, and it has no language of its own.**

### 1. One brief for each piece, in its folder

- **What it is.** A piece's *brief* says what the piece must show and why it is designed as it is. It is written for whoever makes or reviews the piece. No reader of the piece sees it. In this capability's records, *brief* alone means a piece's brief.
- **Where it lies.** In the piece's folder, beside its content, among the piece's sources ([visual-communication:DEC-002-files-and-validation] point 1). A piece keeps at most one.
- **Its name** is `brief.yaml`. No other file points to the brief, so every reader finds it by that one name. No content file takes the name, so a path that selects the content files never selects the brief (DEC-002 point 5).
- **No language of its own.** One brief serves every language of the piece. It is never translated, and is written in the language the piece's makers work in.
- **Optional.** Nothing that draws or checks a piece needs one. Whoever reviews a piece without one has no brief to judge against, and says so.

### 2. It holds what the content does not

A brief holds four things:
- **Relations.** A *relation* is what a picture must make visible between the parts it shows. Examples are levels that each rest on the one below, a flow read in one direction, and kinds of one thing kept apart. It says so in words, and names the parts it relates as point 3 says.
- **Goals.** What the piece, or one page, must achieve with its audience, such as what the audience can do after it.
- **A takeaway, only where a page has no lead.** A page's *takeaway* is the one point a reader should leave it with. A page's *lead* is the text its content gives to state the page's point, such as a slide's lead under its title. No field declares which text that is, so whether a page has a lead is read from its content, by whoever designs or reviews it. Where it has one, the lead is its takeaway, and the brief does not restate it. A cover or a section page often has none. Whether a lead states the point well is a reviewer's to judge, against the page's relations and goals.
- **Reasons.** A *reason* says why one choice of the design was made, and names the principle it rests on, by its name and its source. Each is about one of six *aspects*:
  - **structure:** what the content's structure is, such as levels or a sequence;
  - **form:** the form chosen for it, and the visual variables that carry the structure. A *visual variable* is a property of a mark that can carry a difference, such as its position, size, lightness or hue (Jacques Bertin's term);
  - **hierarchy:** what is seen first, and what is ranked below it;
  - **type:** the brand's roles for text that the page takes;
  - **colour:** the brand's colour roles that the page takes, and what each colour marks;
  - **space:** the spacing and alignment the page takes from the brand.

  A reason names the part of the page it is about, or the whole page. A brief lists its reasons in the order of these aspects, which is the order the choices are made in.

What a brief never holds:
- **What the content holds:** the text, the pictures, which component shows each part, and any value or layout (DEC-001 point 3).
- **What the piece's own file declares:** who the piece is for, where it is shown, whether it explains, its libraries and its lock.
- **A reason for a library's own choice,** such as why a brand's accent is the colour it is. That reason lives with the library that made the choice.
- **A rule.** A requirement that binds more than this piece lives in a rule set (COR-051).

### 3. The shape of its schema, in outline

- **Bound like every file of the format.** Its top names its schema and its format number (DEC-002 point 3). Its schema is strict, and refuses a key it does not declare.
- **A part for the whole piece, and a part for each page.** The part for the whole piece holds the relations, goals and reasons that concern the piece, or more than one of its pages. Each page's part is keyed by the id of the page it speaks of, and holds that page's relations, goals, takeaway and reasons. A piece of one page, such as a figure, which has no list of pages, keeps all of it in the part for the whole piece, its takeaway included.
- **Keyed by page, for every kind of work.** Every piece has pages, while a page's fields are the slots of its layout, which differ from one top component to another (DEC-001 point 4). So the same shape serves a deck, a figure and a site.
- **A page or item it names carries an id** in the content, as whatever another part of the piece names does (DEC-001 point 3). A brief names an item by its key path, as a tie's end names one: the fields and ids that lead to it, never its place in a list ([visual-communication:DEC-011-tie-ends] point 3). A page's part starts the path at its page. The part for the whole piece starts it at the content's top, so it reaches a page alone, or a field of the top such as a site's shared header.
- **What it names in words.** A part inside a local component, or an element of shared content the piece reads (DEC-001 point 3), it names in words, since the key path reaches only the piece's own content.
- **A reason** holds its aspect, by one of the six names of point 2, the part it is about, its text, and the principle it rests on.
- **Room kept for a later reading.** Its top, and each mapping in it, keeps the methodology's container's key free, as a content file does (DEC-002 point 4).
- **An addition to the format.** A piece without a brief reads as before, so the brief needs no new format number ([visual-communication:DEC-003-change-over-time] point 1).

### 4. Who writes it, and what reads it

- **People write it,** or an agent working for one. Its goals and relations come from whoever asks for the piece. Its reasons are written by whoever designs it, as they design.
- **No command changes what it says.** A command may carry it with the rest of the piece, and changes nothing it says. Such a command copies a whole piece into a new one ([visual-communication:DEC-017-final-and-published-states] point 8), or moves the location. A rewrite into a new format that a person asks for carries it too (DEC-003 point 2). An id renamed in the content fails the brief until a person mends it (point 5).
- **Nothing it holds is drawn.** No renderer, export or producer reads it. A change to it moves no lock, changes no scene, and stales no output.
- **Read by people and by a reviewer,** who judges the drawn pages against it. How the capability's agents write and read it is decided with them.
- **Its pages come first in the content.** A page's part names a page the content holds. Before a page exists, its intent is written in the part for the whole piece. Whoever designs the piece gives the page its id in the content when it starts it.

### 5. What the check reports

- **Its shape** is the core's data validation's, against the schema it names (DEC-002 point 6).
- **What it names must be there.** A page id or a key path that names nothing in the content of the source language fails, since the project corrects it in its own files (DEC-002 point 7). Ids are the same in every language (DEC-002 point 4), so one language answers for all.
- **Whether the drawing meets it** is no check's. It is a reading, and never fails validation (DEC-002 point 7).
- **A final piece:** the check reads its brief no more than its content (DEC-002 point 7).

## Rationale

**Why a brief at all.** The deck lost its point in a port that every check passed. A drawing can be clean and say the wrong thing, and only its intent tells the two apart. Written down, the intent lets a reviewer fail a page that hides the point, and lets a later designer keep it.

**Why reasons, each naming its principle.** A reason with no principle is taste, and nobody can judge it. Named, a reason can be checked against the drawing and against the practice it cites, and a reader learns from it. The aspects run in the order the choices rest on each other: the structure picks the form, the form the visual variables that carry it, and the hierarchy, type, colour and space follow.

**Why not in each content file.** Content is what a piece shows (DEC-001 point 3), and the brief is never shown.
- **A second language would copy it.** Every language holds the same shape, so a brief in each would be one copy per language, free to drift, or a field one language holds and the others lack.
- **It would be read as shown text.** A translation renders each text of the content in another language. Once content is an artefact, rules for what the audience reads would judge its prose too (DEC-001, Implications). The brief's prose is for the piece's makers.

**Why not in the piece's own file.** A draft's render rewrites that file's lock (DEC-002 point 5). Whoever watches the brief for a change would see one at each render. Once the file is an artefact, each move of a lock would alter the brief's artefact too.

**Why one file for the piece, keyed by page.** A piece's goals, and what holds across its pages, belong to the whole piece. A file for each page would leave them no home, and would follow the page's place in the piece. An id stays with its page when pages move, as an item's does (DEC-001, Rationale, "Why ids are text, and every drawn part traces back").

**Why the takeaway only where a page has no lead.** A lead states the page's point to its audience, in each language. A takeaway beside it would state the point a second time, in one language, and where the two differed no reader could tell which holds. What a port can lose, the brief keeps in the page's relations and goals, against which a reviewer reads the lead.

**Why failing a name that names nothing.** A brief that names a page or an item the content lost speaks of something that is not there. The reviewer would judge a page against intent meant for another. The project mends it in its own file, as it mends any reference.

**Why a file of the capability's format.** Every file of the capability's own format names its schema at its top (DEC-002 point 3). So the check can read what a brief names, and the brief keeps the room a later reading needs.

**Why no command changes what it says.** It is a person's intent. A command that changed it would have to decide what the piece is for.

### Alternatives considered

- **A field of each content file,** as the maintainer decided on 31 October. Rejected for the reasons above: it would be copied into every language, translated, and judged as shown text.
- **The piece's own file.** Rejected: a draft's render rewrites it.
- **A Markdown document beside the piece, or the speaker's notes.** Rejected. The notes are content, which a presenter sees and a translator translates. A Markdown document names no schema, so the check could not read what it names (DEC-002 point 3).
- **A file for each page.** Rejected: the piece's goals would have no home.
- **A brief keyed by a deck's slots.** Rejected: only a deck has slides, and a figure or a site would need a brief of another shape.
- **Reasons in a file apart from the intent.** Rejected: a reason serves the intent beside it, and two files of one piece's intent drift.
- **A takeaway on every page,** with a reading that reports where the lead drifts from it. Rejected: the point would be stated twice, and a page's relations and goals already give a reviewer the intent to read the lead against.
- **A brief every piece must keep.** Rejected. A quick figure needs none, and no check can judge whether one says enough.
- **A name that names nothing asks for attention only, while the piece is a draft.** Rejected: the page parts come once the pages do (point 4), so nothing written in order meets the failure.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-001 point 3, its opening,** comes to say that a piece also keeps at most one brief, which says what its content must show and why its design is as it is, and has no language. **"Ids and traces"** comes to count a page or an item the piece's brief names among what another part of the piece names, and so carries an id.
  - **DEC-002 point 1, "Each piece's sources are one folder",** comes to count the piece's brief among its sources.
  - **DEC-002 point 5** comes to add that a piece's brief lies apart from both its content and what commands rewrite. It holds no content, no command changes what it says, and its name tells it apart from the content files.
  - **DEC-003 point 2, "The files people write are read in memory", "A rewrite only on request" and "No other write into an older file,"** come to count a piece's brief among the files people write, beside a content file, a local component and a library version. **"The files commands write are carried over"** comes to count it among what that migration never writes.
- **Read against this record, and left as they stand:**
  - DEC-002 point 3, since the brief names its schema as every file of the format does.
  - DEC-002 point 7, since the brief's one failing finding is a reference the project corrects in its own files.
  - DEC-003 points 1 and 3, since a piece without a brief reads as before.
  - [visual-communication:DEC-015-viewing-step-and-reviewer] point 4, since the viewing step writes nothing in a piece's folder.
  - DEC-017 point 8, since the copy of a final piece takes the brief with the rest of its folder.
- **The Task that builds the brief,** filed under [project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584) once this record is accepted, writes its schema and the check of what it names. It also adds the brief to the files reference, and to the skill that guides building a piece.
- **How the capability's agents write and read a brief** is decided with them, in a record of its own.
- **Later, an artefact.** A refinement of the core that lets a capability declare places within its working folder would make content an artefact (DEC-002, Implications). The brief can then become one too, with no change of its format, since its container's key is free. Its reasons could then anchor to the records and libraries they rest on.
