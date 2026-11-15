---
id: DEC-055
title: A piece names the media it is shown in, its top declares the smallest text each allows, and the check fails a text drawn smaller
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a page shown on a screen at hand, on a screen across a room or on paper has a smallest text a reader there can read. The piece names the media it is shown in, from three the capability names: `screen`, `room` and `paper`. It names them alone, and each then shows every size the piece is drawn at, or it names for every medium the sizes that medium shows, as a deck drawn for a laptop and for a projector shows its projector's pages in the room. The piece's top component declares how small a text may be in each medium its pages are made for. The value is a fixed size where the medium shows a page at its own size, as a screen at hand shows a web page. It is a share of the page where the medium fills what shows it with the page, as a room's screen shows a slide. The check compares each run of text with the smallest size of each medium that shows the size the run is drawn at, and fails a run drawn smaller. It judges a page as its medium shows it, and takes the brand's width at a size as the width the page is shown in: a narrower window or column, a zoom and a print's scale are not judged. The finding lies at the text's trace in the piece's own file, as a finding on contrast does, since the size comes from the component, the brand and the top together. The check reads the scene, so one finding serves every renderer. No brand sets the smallest size. A piece is held to it only once it names a medium and its lock names a top that declares one for it, and the check says so where it is not.

## Context

The record of the principles of visual communication leaves "a text smaller than its medium allows" to a check, run on every render whether a rule binds or not, beside a text that spills out of its box and too little contrast ([visual-communication:DEC-028-principles-of-visual-communication] point 1). Its point on who can read a page leaves the smallest text size for a medium to that check (DEC-028 point 10). Its rule on legibility, `RS-GRAPHIC-005`, keeps for the review that "everything on a page can be read where the piece is shown", and that "a page is taken in at a glance". The record of the review's grades keeps it the checks', and records that the check was never built ([visual-communication:DEC-042-grades-bar-and-loop] point 2).

So a projected slide can carry 12 px notes and pass every check ([project-kit#3185](https://github.com/aleskalfas/project-kit/issues/3185)). The engine's only smallest size sizes the viewing step's images, so that a reader of them can read a page's smallest text, and fails nothing ([visual-communication:DEC-015-viewing-step-and-reviewer] point 5). The review graded legibility by how much a page holds, not by whether its text reads at its size (DEC-042, Context).

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

## Decision

**A piece names the media it is shown in, from three the capability names, and may name for every medium the sizes it shows. Its top declares the smallest size of each medium its pages are made for, as a fixed length or as a share of the page. The check compares each run of text with the smallest size of each medium that shows the run's key, judging each page as its medium shows it, and fails a run drawn smaller, at the text's trace in the piece's file.**

### 1. The piece names the media it is shown in, and may name for every medium the sizes it shows

- **Under one field.** A piece names its media under `media`, in one of two forms, and one form holds for the whole piece. Either names one medium at least:
  - a list of the capability's words, each once, where each medium shows every size the piece is drawn at, such as `media: [screen, room]`;
  - a mapping from each medium's word to the sizes it shows, each a size the piece is drawn at and named once under it, such as `media: {screen: [desktop], room: [projector]}`. Every medium a mapping holds names its sizes, and one that shows every size names each.
- **Three media:**
  - `screen`, a screen at hand, read at arm's length or nearer: a desk's, a lap's or a hand's;
  - `room`, a screen read from across a room, projected or not;
  - `paper`, a printed page.
- **Each size judged in each medium that shows it.** A deck read on a laptop at `desktop` and projected at `projector`, under a brand that gives both, names `media: {screen: [desktop], room: [projector]}`. Its projector's texts are held to the room's smallest size, and its desktop's to the screen's. A deck projected that names no size names `media: [room]`, and its texts at `desktop` are held to the room's.
- **A size, as a component reads it.** A key's size is the mode it holds on the size axis, else the axis's default (DEC-021 point 3). So a piece that names no size is drawn at `desktop`, and a mapping may name it.
- **The capability's words.** The piece's format names them, as it names the formats of its exports. So a medium means the same under every top, and a command reads it with no top.
- **The size never chooses it.** A size mode chooses the values a brand gives for what a piece is drawn for (DEC-021 point 1). The medium says where the piece is shown, and the two may differ: a deck projected in a room may be drawn at `desktop` alone. A mapping is the piece saying which of its files each medium shows, never a size choosing its medium.
- **`shown` stays words,** for a reviewer, and says the place as well as the medium. The review judges a page by it under `RS-GRAPHIC-005`, and the check by `media` alone. Both are the piece's author's, who keeps them in agreement. Where they disagree, each judges by its own, and no command compares them, since none reads a medium from words.
- **Read by the check alone.** No scene reads it, so an export's reading leaves it out, as it leaves out the losses a piece accepts ([visual-communication:DEC-016-what-an-export-reads] point 1). A medium named or changed changes no exported file. The key of the findings record reads the piece's file whole (DEC-016 point 2), so the next check judges it.

### 2. The top declares each medium's smallest size

- **Under one key.** A top declares its smallest sizes under `smallest-text`, a value for each medium its pages are made for, by the medium's word, such as `smallest-text: {screen: 12, room: "=:height / 40"}`.
- **The top's alone,** as its physical size is (DEC-034 point 3): a fact of the top's pages, which DEC-001 point 5 comes to name beside the physical size (Implications). No brand gives it a value, no role or component token holds it, and no other formula reads it.
- **Only the piece's top is read for it.** A top placed in another component's slot, or as a page of another top, is shown in the piece's media, and its own declaration is not read there.
- **A value, never a switch.** It switches neither by an option nor by a size. So content never chooses its own smallest size, and a size chooses no medium.
- **A medium it declares nothing for** has no smallest size under that top, and no text of a piece it tops is judged in that medium.

### 3. A fixed length or a share of the page, each judging the page as its medium shows it

The value takes one of two forms. The top chooses, for each medium, the form that fits how that medium shows its pages, and the check judges each page as so shown:
- **A fixed length,** a positive number in px, for a medium that shows the top's pages at their own size. On a screen at hand a px of the page is then a px of the screen, which CSS sets by the angle it takes at arm's length. On paper, a page with no physical size prints at the unit its renderer declares (DEC-034 point 3). That unit is the capability's, as every renderer is (DEC-005 point 12), so a fixed length on paper names a printed size no project moves, such as the PDF export's px, 96 to the inch.
- **A share of the page,** a formula that gives a length and reads only the size of the page the run lies on, `:width` and `:height`, with numbers, such as `"=:height / 40"`. It serves a medium that fills what shows it with the page: a room's screen, which shows a slide as large as its image whatever its px, or paper at the top's physical size, which takes the page by one scale. So the smallest size follows the page's size, whatever width a brand gives the page. It reads `:height` only at a page that asks for a height: a page that asks for none is as tall as its content (DEC-022 point 3), so a share of its height would grow with the text it judges (point 7).
- **What the check takes as given.** A page shown in less width than its own shrinks, as a page of the HTML renderer shrinks in a narrower window and keeps its own size in a wider one (DEC-020 point 4). So the check takes the brand's width at the size a page is drawn at as the width the page is shown in, such as a browser's window or a document's column.
  - A device or a column narrower than that width shrinks every text on the page, by the ratio of the two widths.
  - A page file shown on a room's screen wider than the page fills that screen only once the presenter enlarges it.
  - Neither is judged. The window, a zoom, and the scale a presenter or a print dialog sets are the reader's or the presenter's, as the sheet and its scale are (DEC-026 point 4).

Neither form reads a role. A brand moves the smallest size only through the size of the page it gives, never by a value of its own.

### 4. The check compares each run with the smallest size of each medium that shows its key

- **What it compares.** Each run of each text a scene draws, by its font size as the scene holds it, against the smallest size the top declares for each medium that shows the scene's key, for the page the run lies on.
- **At each key, in each medium that shows it.** Each key the piece names is held to each medium that shows its size (point 1). The run's size is the brand's value at the scene's key, and a share reads the page's size there. So a projector's larger type meets the room's smallest size where the piece shows its projector's pages in the room, and a deck drawn at `desktop` alone and named for the room is held to the room's all the same.
- **At the smallest size, a run passes.** A run below it is reported. Both are compared at the scene's rounding of a length, to 1/100 px.
- **What it leaves out.** Words inside a picture, made while preparing or elsewhere, are pixels, and no text the scene holds. How large a face's letters stand in their font size is not compared: a face whose letters are small for their size is the review's to judge on the drawn page, under `RS-GRAPHIC-005`.

### 5. The check reads the scene, so one finding serves every renderer

- **One finding for all of them.** A renderer adds no size to a page (DEC-001 point 2), so a run's size in the scene is its size in every renderer's output. The check reads the scene, before any renderer runs, and its finding holds for the previews and for each export alike, each page judged as point 3 says.
- **A physical page.** A format with a physical page draws each page onto it by one scale (DEC-034 point 3), so a share of the page keeps its share on paper.
- **What a viewer does** is not judged: the window, a browser's zoom or a print dialog's scale (point 3).
- **The scene holds nothing new,** so neither the seam's version nor any renderer's rises (DEC-005 points 8 and 9).
- **The viewing step keeps its own smallest size,** which sizes its images for whoever reads them, and judges no medium (DEC-015 point 5).

### 6. The finding fails, at the text's trace in the piece's file

- **Its label,** `text-too-small`. It is a finding of the scenes, found when a scene is computed, and kept in the findings record as each of theirs is (DEC-005 points 13 and 14).
- **Where it lies:** `<piece>/piece.yaml#<trace>`, the trace of the text whose run is too small, as a finding on contrast lies (the checks' page, `contrast-drawn`). It names no library version.
- **Its message** names the run, its typography role and its size, the medium, its smallest size, the top that declares it and, for a share, the page's size it was read from. Its fix names the ways to mend it:
  - another style for the run, or an option or a component that sets the text in a larger role;
  - a brand that sizes the role larger at that size;
  - where the run's size is shown elsewhere, and another of the piece's sizes in that medium, its media naming the sizes each shows (point 1);
  - where its brand gives a size whose type is larger, such as `projector` for a room, the piece drawn at that size, with the medium naming it in place of the run's size. A size added alone mends nothing, since the medium still shows the run's.
- **It fails** ([visual-communication:DEC-002-files-and-validation] point 7). This record owns the invariant, and the project corrects a break of it in its own files: its content's styles and options, its own components, a brand of its own built on another, or the sizes the piece names and the media that show each.
- **At some sizes, in several media, and on several pages,** it is reported as every finding of the scenes is: once where every key finds it alike, and otherwise for each key whose scene finds it, its message opening with the key; and once for a field the top draws on every page. A run under the smallest size of several media is reported once, naming each.
- **Where nothing is judged,** the check states one fact, `text-size-unjudged`, at `<piece>/piece.yaml#media`: for a piece that names no medium; for each medium it names whose smallest size its top does not declare, naming the top and, where the piece maps its media, the sizes that medium shows; and for each size it is drawn at that no medium shows, naming the size. So a reviewer sees each medium no text's size was judged in, and at which sizes, and each size no medium shows.

### 7. What the check refuses

When it reads the piece and the component, the check reports:
- in a piece's `media`: a list or a mapping that names no medium; a word the capability does not name; in its list, a word named twice; in its mapping, a medium that names no size, a size named twice under one medium, or a size the piece is not drawn at; each as `piece-unreadable`, as a mode the brand lacks is. A medium a mapping names twice is a key written twice, which the reader refuses in every file of the capability's format (`file-unreadable`; the files' page, "How the files are read");
- `smallest-text` on a component that is no top, or on a brand's drawing; a key in it that names no medium; and a value that is a number not positive, or a switch, each as a key or a value its format does not allow (`component-shape`);
- a formula that gives no length, or reads anything but `:width`, `:height` and numbers, as a formula's own findings (`formula-dimension`, `formula-reach`).

When it computes a scene, the check reports a share that reads `:height` at a page that asks for no height as a formula that reads what it may not reach (`formula-reach`), at the top's file, `#smallest-text.<medium>`, naming each such page, as severely as any formula's finding (DEC-005 point 14). No text of such a page is judged in that medium.

### 8. The shipped tops declare it, each value with its source

- **The foundations' tops** declare a smallest size for each medium their pages are made for, as each top's account of its pages names those media.
- **Each value names its source beside it,** a standard or a guideline of legibility for that medium, such as the display image size standard that DEC-028 point 10 names for a projected image (ANSI/INFOCOMM V202.01). Which media a top declares, and the value for each, are the foundations' data, reviewed in the change that sets them, as a brand's scales are.

### 9. An addition, which reaches a piece through its media and its lock

- **Format 1.** `media` on a piece, in either form, and `smallest-text` on a top are optional, so every file format 1 accepted reads and draws as before ([visual-communication:DEC-003-change-over-time] point 3). A medium the capability names later is an addition too, since it refuses no word accepted before.
- **A top that comes to declare one, or raises it,** renames and removes nothing, so it breaks nothing (DEC-003 point 6). A draft moves to it at its next render, as to any newer version the project holds, and may then fail where a text is too small (DEC-003 point 8).
- **So a piece is held to it only where it names a medium,** at the sizes that medium shows, and the version of its top that its lock names declares that medium's smallest size. Elsewhere the check states the fact of point 6.

## Rationale

**Why a check, and not the review.** Comparing a run's size with a number needs no judgement, so DEC-028 point 1 gives it to a check, and DEC-042 point 2 keeps it there. What `RS-GRAPHIC-005` asks in its own words stays the rule's: that "everything on a page can be read where the piece is shown", and that a page is taken in at a glance. A run at the smallest size may still not read as drawn, and the review judges that on the page.

**Why the piece names its media.** Where a piece is shown is the piece's, as the person who makes it already says in `shown`. Its size does not say it. A piece that names no size is drawn at `desktop` (DEC-021 point 3), and under a brand with no size it can name no other (DEC-021 point 2). So a smallest size chosen by the size would judge a deck projected in a room at the default size as a slide on a desk, the case in Context, and under such a brand the piece could not mend it. Nor does the top say it, since one top's pages reach readers in several media, and one page file may be read on a laptop and projected.

**Why the capability names the media.** A word the capability names means the same under every top. So a command reads a piece's media with no top, a reviewer reads them beside `shown`, and a piece that switches its top keeps them. How a page reaches the eye is the format's to name, as the formats of a piece's exports are, and no library's look. A medium needed later is an addition to the format.

**Why the top holds the values.** How small a text may be in a medium rests on how far the reader sits from what shows the page, and how large the page stands there. A poster on paper is read from metres away, and a figure in a printed document from a hand's length. A slide fills a room's screen, and a web page keeps its own size on a screen at hand. These are facts of the kind of page and its size, which the top names. The engine knows no top by name (DEC-001 point 4), so the top says it in its data. A project's own top, such as a poster, then declares its own with no change to the foundations. It is the reason a physical size is the top's: a fact of the pages the top makes, which no brand gives (DEC-034 point 3). This record is the second to read DEC-001 point 5 that way, after DEC-034, and that point comes to name both facts, so that a third reads the class there rather than anew (Implications). Nor is the smallest size the first threshold a library declares, which a brand's values are held to: the foundations declare the pairs of colour roles that must contrast, each with the level it must reach, and the check holds every brand to them in every combination (DEC-004 point 8). The smallest size is the second.

**Why no brand sets it.** The brand gives the sizes the check judges. A smallest size it gave would be judged by itself, a brand built on another could lower it, and two brands would hold one piece to two smallest sizes in one medium. Contrast is kept so already: the brand gives the colours, and the level a declared pair of the foundations' roles must reach is the foundations', never a brand's (DEC-004 point 8). So the declaration reads no role, and a brand reaches it only through the size of the page it gives.

**Why two forms.** A screen at hand shows a page at its own size where its window holds it (DEC-020 point 4), and CSS sets a px by the angle it takes at arm's length, so a fixed px is a size its reader sees. A room's screen shows a page as large as its image, whatever its px, so only a share of the page says how large its text stands in the room, and the standard on projected images states its sizes against the image's height. A sheet takes a page at the top's physical size by one scale, so a share of the page is a size on paper. Which form fits depends on the kind of page as well as the medium, so the top chooses. Neither form reads more than the page's size, so neither lets a brand in. A share reads a height only at a page that asks for one, since a page as tall as its content would move its own smallest size with every line it gains. Whether a page asks for one is not the top's alone: a brand's drawing of a page alone writes its own height, and the part that places a page in a top's slot gives it its size (DEC-034 point 2). So the check looks for a share's `:height` where the formula reads it, on the scene, page by page, and judges from the component alone only what the formula's own text shows, its dimension and its reach.

**Why the brand's width stands for the width a page is shown in.** The check knows no reader's window or document's column. The brand's width at a size is the one statement the files make of it: how wide a page is drawn for that device (DEC-021 point 1, DEC-022 point 3). Against any other width the check would need one no file gives. So on a screen at hand, a brand that draws its pages wider than its devices' windows shrinks every text there, and the check does not see it, as it does not see a reader's zoom. In a room it does not escape, since a share reads the page's own size.

**Why a piece may name the sizes each medium shows.** Each size a piece is drawn at has a scene and files of its own (DEC-005 point 6, DEC-023 point 1), and which file is shown where is the piece's to say, as its media are. Held each to each, a deck drawn at `desktop` for a laptop and at `projector` for a room would hold its desktop texts to the room's smallest size too, a bar the laptop's reader does not need. Where its brand gives the slide one width at both sizes, as the neutral brand does, that bar is one length at both, and the projector's larger type would gain the check nothing. A piece that names its media in a list still has each show every size. So a deck that names no size, or whose brand gives none but the default, is held to the room at `desktop` ("Why the piece names its media"). A mapping names only sizes the piece is drawn at, so each medium it holds shows one size at least, and a size no medium shows is stated, never passed in silence. The cost: the check cannot tell that the file shown in a room is the one the media name, as it cannot tell that a piece is shown where its media say.

**Why the page's size, and not the top's.** The smallest size is about the page as its medium shows it. For a page alone, and for a top whose layouts are its pages' forms, as each top the foundations ship is, the two are one. A top whose slot holds pages of their own sizes would otherwise hold each to the top's.

**Why the font size.** It is what a typography role gives, what the scene holds for each run, and the size every guideline states. How tall a face's letters stand in it differs by face, and the drawn page shows it, so that is a reading's, under the rule.

**Why at each key.** A brand's values and a page's size both differ by key, and each key has its own scene (DEC-005 point 6). A key's larger type is the piece's way to meet a stricter medium that shows it, so each key is judged with its own values.

**Why one finding for every renderer.** A renderer projects the scene and adds no size (DEC-001 point 2). What differs between formats is how a viewer shows a page, and no file records it. Judging each renderer's output would judge what the reader or the presenter sets, and would report one fault several times.

**Why at the piece's file.** A run's size is the brand's value for the role the component chose, held to the top's smallest size for the medium the piece names: three libraries and the piece together, none of the libraries at fault alone. Contrast is such a combination too, and its finding lies at the piece's file and names no version, so its level stands. The piece's author mends it in the project's own files. A finding at the component's part would lie in a released version and only ask its owner for attention, while every piece that used the component stayed unreadable.

**Why it fails.** A text too small for its medium is lost to its reader, as a text that spills out of its box is, and DEC-028 point 1 gives both to the checks alike. The project corrects it in its own files (DEC-002 point 7). It holds a piece only where the piece names a medium and its lock names a top with a smallest size for it, so an upgrade of the capability alone fails no piece.

**Why a fact where nothing is judged.** A check that judges nothing in silence is how this gap stayed open (Context). The fact names what went unjudged and asks no act, since every piece written before this record names no medium, and a piece may lock an older top on purpose.

### Alternatives considered

- **The top's smallest size chosen by the size the piece is drawn at, with a fact naming the branch that judged it.** Rejected: a piece that names no size, or whose brand gives none, would be judged as a slide on a desk wherever it is shown ("Why the piece names its media"). The fact would show that, and mend nothing.
- **One smallest size for each mode of the size axis, in the foundations.** Rejected, for the same reason, and since at `desktop` a slide fills its screen and a web page does not, so one number would hold one of them wrongly.
- **Media each top names, which a piece picks among.** Rejected: a medium would mean what each top says, so no command or reviewer could read it without the top, and a piece that switched its top could name a medium the new top lacks ("Why the capability names the media").
- **Media the foundations declare, as they declare the shared axes.** Rejected: a medium is neither a value a brand varies nor a structure, and a piece's medium would then mean only what its locked foundations say.
- **A table of each medium's smallest size, in the capability.** Rejected: how small a text may be in a medium depends on the kind of page and its size ("Why the top holds the values").
- **Each size held to each medium the piece names, always.** Rejected: a deck drawn for a laptop and for a room would hold its laptop's texts to the room's smallest size, a bar its laptop's reader does not need ("Why a piece may name the sizes each medium shows").
- **A deck shown in two media made as two pieces, one for each.** Rejected: one design laid out at each size a person chooses is what the size axis is for (DEC-021, Context), and two pieces would keep one content twice, to drift apart.
- **Every medium paired with its sizes, with no list.** Rejected: a piece that names no size, or shows each size in each medium, would name its sizes for nothing, and gain a new size unjudged.
- **The medium read from the piece's `shown`.** Rejected: no command reads a medium from words.
- **The field named `seen-in`, in place of `media`.** Not taken here: `media` keeps the word DEC-028 uses for how a page reaches a reader's eye, and the Terms set it apart from a renderer's. Against it, the capability already calls the format a renderer draws into a medium (DEC-001 point 2), so `media` on a piece may be read as the formats it is drawn into, which its exports name. `seen-in` meets no word the capability uses. A rename once format 1 accepts the field would refuse what it accepted, which waits until validation reads older files (DEC-003 point 3), so the name is chosen before the field ships.
- **A role a brand gives, such as a smallest type size.** Rejected: the brand would set the smallest size it is judged by ("Why no brand sets it").
- **A setting in the capability's configuration.** Rejected: one smallest size for a project cannot tell a slide from a web page. A project's stricter taste is a rule set of its own (DEC-028 point 1).
- **A table in the check, by the top's name.** Rejected: the engine knows no top by name (DEC-001 point 4), and a project's own top would have no entry.
- **A share of the page for every medium.** Rejected: a web page is as tall as its content, and a screen at hand shows a page at its own size, so its reader's px stay what they are whatever the page's width.
- **A fixed length for every medium.** Rejected: a room's screen shows a page as large as its image, whatever its px, so a page's px say nothing of how large its text stands there.
- **Judging each export by how its viewer shows a page.** Rejected: the window, a zoom and a print's scale are the reader's or the presenter's, and no file records them ("Why one finding for every renderer").
- **A smallest size for each renderer, from its declaration.** Rejected: a renderer adds no size ("Why one finding for every renderer").
- **The height of the letters, such as the x-height, in place of the font size.** Rejected ("Why the font size").
- **The finding at the component's part that chooses the style, or at the brand's role.** Rejected ("Why at the piece's file").
- **Asking for attention, never failing.** Rejected: an overflow and too little contrast fail, and DEC-028 point 1 gives all three to the checks alike.
- **The top's own size in the share's formula.** Rejected ("Why the page's size, and not the top's").
- **A piece that accepts a text too small, for a run or at a size, as it accepts a loss.** Not taken: the piece drawn for two media, the need "Why a piece may name the sizes each medium shows" names, says where each size is shown, which is a fact and accepts no fault. A text too small for the medium that shows it is lost to its reader whoever accepts it. Allowing it later is an addition.
- **The viewing step's smallest size as the medium's.** Rejected: it sizes images for whoever reads them, and says nothing of where a piece is shown.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - **DEC-001 point 5, "Roles stand between structure and values,"** comes to add that a fact of a top's pages that no brand gives is the top's to hold, and no raw value, since no role may stand for it: its physical size (DEC-034 point 3) and the smallest text size it declares for a medium (points 2 and 3).
  - **DEC-005 point 1, "What it may use,"** comes to add that the formula of a top's smallest text size reads only the size of the page a run lies on, as `:width` and `:height`, and numbers (point 3), as `cross-size` alone reads `:place` and `:places` ([visual-communication:DEC-038-size-by-place] point 2). Its "Where lengths come from" stands, since a fixed smallest size is no formula's, and DEC-001 point 5 comes to name it no raw value.
  - **DEC-005 point 14, "Fails validation,"** comes to add a text drawn smaller than the smallest size the piece's top declares for a medium that, as the piece names it, shows the key it is drawn at (points 4 and 6).
  - **DEC-028 point 10,** at its sentence "A smallest text size for a medium is a check's, run always (point 1)", takes the pointer alone, and decides nothing new.
- **Read against this record, and left as they stand:**
  - DEC-001 point 2, since a renderer still adds no size, and what a viewer does is no renderer's.
  - DEC-001 point 3, since `media` is a field a check selects a piece by, which that point lets a piece declare, and `shown` stays words.
  - DEC-002 point 7, since the finding follows its policy.
  - DEC-003 points 3, 6 and 8, since the field, the key and a medium named later are additions, and a smallest size added or raised breaks nothing (point 9).
  - DEC-004 point 8, since the pairs a library declares, and the level each must reach, stay its own, and the smallest size is a second threshold of that kind, declared apart from the brand whose values meet it.
  - DEC-005 point 3, since the formula of a smallest size reads no part: its `:width` and `:height` name the size of the page a run lies on, a page of the top's own or one its slot places, so it reads nothing above the top.
  - DEC-015 point 5, since the viewing step's smallest size stays its own.
  - DEC-016 points 1 and 2, since `media` passes the first's test, as the losses a piece accepts do, and the findings key still reads the piece's file whole. The reference's list of the fields an export leaves out gains it, as point 1 has a change do.
  - DEC-020 points 2 and 4, since a page's lengths stay shares of its width, and a page still shrinks with a narrower window and keeps its own size in a wider one. The check judges it as point 3 says.
  - DEC-021 points 1 to 3 and 8, since a size mode still chooses a brand's values and a component's shape, and chooses no medium, and a page file still holds one size. A piece names its media, and the sizes each shows, whatever sizes its brand gives, and this record reads a key's size as DEC-021 point 3 has a component read it.
  - DEC-022 point 3, since a page's width at a size stays the brand's, which the check takes as the width a page drawn at that size is shown in, and a page that asks for no height stays as tall as its content, whose height no share reads (point 7).
  - DEC-023 point 1, since a file still serves one size, the unit a medium's sizes name.
  - DEC-026 point 4, since the sheet and its scale stay the reader's.
  - DEC-028 point 1 and the rest of point 10, since the smallest size stays a check's.
  - DEC-034 point 3, since a physical size stays the top's, which DEC-001 point 5 comes to name beside the smallest size, and a share of the page keeps its share on paper.
  - DEC-042 point 2, since the check it names is this one.
  - `RS-GRAPHIC-005`, which judges a page where the piece is shown "as its `shown` field names", and rests on DEC-028 point 10, which this record edits. It holds as it stands: the review still reads the words in `shown`, `media` is the check's alone, and what the rule asks, that "everything on a page can be read where the piece is shown" and a page is taken in at a glance, stays the review's. Where `shown` and `media` disagree, the piece's author mends them, as point 1 says.
- **[project-kit#3185](https://github.com/aleskalfas/project-kit/issues/3185)** builds points 1 to 9 in the engine, the schemas of a piece and of a component, and the check. It sets which media each of the foundations' tops declares, and each value with its source (point 8). For each medium those tops declare, it tests a text below and a text at its smallest size. It also tests a deck that names `media: [room]` and no size, and a deck drawn at `desktop` and `projector` in each form of mapping: `media: {screen: [desktop], room: [projector]}`, which passes with desktop type below the room's smallest size and at the screen's, and states no fact; and `media: {room: [projector]}`, which states the fact for `desktop`. It tests the fact for a piece that names no medium, for a medium its top declares nothing for, in a list and in a mapping, where the fact names the sizes that medium shows, and for a size no medium shows. It tests each refusal of point 7, and the share that reads `:height` at a page that asks for no height. It changes these pages and files:
  - the checks' page: its findings table, which gains `text-too-small` and `text-size-unjudged`, and whose rows `piece-unreadable`, `component-shape`, `formula-reach` and `formula-dimension` widen (point 7); and its list of the fields an export leaves out, which gains `media`;
  - the files' page, whose table of `piece.yaml` gains the field, in both its forms;
  - the components' page: the key in the table of a component's file, and a section beside "A physical size";
  - each shipped top's account of the media its pages are made for;
  - the account of the size axis's modes, in the foundations' roles file and on the files' page, which comes to say that a mode names what a piece is drawn for, and the piece's media where it is shown;
  - the command that starts a piece, which takes the media as it takes where the piece is shown, and the skill's page on a piece and the designer's agent file, which name the field beside `shown`.
- **The foundations take a new version** whose tops declare their smallest sizes, released as the capability's shipped libraries are ([visual-communication:DEC-013-shipped-library-releases]).
- **No migration.** The field and the key are additions, and nothing a project holds changes (COR-010).
- **Revisit this record** if a medium is found to show pages otherwise than point 3 takes as given, such as pieces shown in rooms from page files kept at their own size; if a file an export makes comes to serve more than one size, since a medium's sizes name files; or if a second size axis is declared, since a medium's sizes are modes of one axis (point 1).
