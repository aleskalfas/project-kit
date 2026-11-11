---
id: DEC-033
title: A piece tells a reader who does not see it what each of its texts and pictures is
status: accepted
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a reader who does not see a piece, such as one who uses a screen reader, gets its words with what each of them is: a heading, a list, emphasis, a link or a picture's text. The format fixes these words. A component says what each of its run styles, texts and pictures is, content writes a picture's text and a run's link, and each renderer spells them in its medium. The check reports what a renderer leaves out, but for the reader's side of a format read whole, as an image is, such as SVG's, links aside. No file format 1 accepted fails, and a picture with no text only asks for attention. For example, a card's head is a heading because its component marks the field so: level 2 inside a slide whose title is a heading, level 1 on a page alone, under every brand.

## Context

[project-kit#2739](https://github.com/aleskalfas/project-kit/issues/2739) asks who declares what a reader who does not see a piece gets, and in which words. The accepted records leave it open:
- **The founding record** has each renderer project one scene into its medium, and report what it lost ([visual-communication:DEC-001-visual-communication-discipline] point 2).
- **The record of the engine** promises documents and PDF files alternative text, a reading order, and structure such as headings, lists, tables and captions, and names no author ([visual-communication:DEC-005-engine-and-plugins] point 5).
- **The record of runs** gives a run's word no structure a renderer reads, and leaves a run's link, a key the format adds, to a later change ([visual-communication:DEC-012-text-runs], Implications).
- **The record of picture files** leaves what a reader gets of a picture to this record ([visual-communication:DEC-025-picture-files] point 11).
- **The HTML page's record** leaves how its elements carry these words to [project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740), which follows this record ([visual-communication:DEC-020-html-page-drawing] point 10).

The Feature this record serves asks that links, a picture's text, a reading order and a run's structure reach the HTML page and the PDF, and that the PDF's declared losses for them go ([project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570)).

Terms:
- A *reader's side* is what a reader who does not see the drawing gets of a piece: its words, with what each of them is. A reader's tools, such as a screen reader, read it from the file.
- *Structure* is what a run, a text, a list field or a picture is on the reader's side, such as emphasis, a heading, a list or a picture's text.
- An *instance's text* is a text a component gives to the whole that an instance of it draws, such as a diagram of boxes and lines, apart from the texts inside it (point 5).
- A *brand's drawing* of a layout, and whether it *fits* an instance, are as [visual-communication:DEC-009-layout-defaults] points 5 and 6 define them.

## Decision

**A piece tells a reader who does not see it what each of its texts and pictures is.**

### 1. The format fixes one vocabulary of structure, and each renderer spells it

- **Words of the format's own,** which name no medium, hold structure in the scene, such as `emphasis` or `heading`. No library declares one.
- **The words:**
  - a run's structure: `emphasis`, `strong` and `code` (point 2), and a run's link (point 3)
  - a text's structure: `heading`, with its level, `caption`, `paragraph` and `decoration` (point 4)
  - a list, and its entries (point 4)
  - a picture's text, or that it needs none, and an instance's text (point 5)
  - a reading order (point 6)
- **Named as the web names them:** WAI-ARIA's role names where the meanings match, as the scene's properties take SVG's (DEC-005 point 5). `decoration` is ARIA's presentation. A later word is named so.
- **A later word is an addition.** It refuses no file ([visual-communication:DEC-003-change-over-time] point 3), and the seam's version rises with it (DEC-005 point 8).
- **Each renderer spells each word** in its medium, and its reference page says how (DEC-001 point 2). This record settles five cases: where a link and a span cross (point 3), an instance's text (point 5), emphasis in a PDF (point 7), a picture not drawn (point 8) and a format read whole (point 9).
- **Declared as a property is.** A renderer declares each word it spells, as it declares each primitive and property (DEC-005 point 9). The check reports a word it leaves undeclared as lost, but where point 9 exempts the format.

### 2. A component gives each run style its structure

- **For each word of a field's run styles,** the component may name one run structure. A word that names none is plain text on the reader's side. Which structure a word names is the component's design, released in its library.
- **The run structures:**
  - `emphasis` stresses a span, as a voice stresses a word.
  - `strong` marks a span as important.
  - `code` marks a span as code, such as a command or a name a machine reads.
- **Content names a word, never a structure.** A run structure is no word content gives, so DEC-012's refusal of words the format fixes for every field still holds.
- **The first word may name one.** A field given as text then reads in it throughout.
- **One span across runs.** Runs next to each other in one paragraph that take the same structure are one span of it.
- **A block of code.** A text read as a paragraph, whose every run is `code`, reads as one block of code, its paragraphs its lines, kept as written. A text marked otherwise, such as a heading, keeps its mark, and its runs read as spans of code (point 4).
- **One structure under every brand.** It lies with the field's words, so each text part that shows the field carries it. A brand's drawing takes it with the words the top declares, and declares none of its own (DEC-009 point 5).
- **It counts for no drawing's fit,** as a run's concept does not (DEC-012 point 2).

### 3. A run may hold a link, under the key `link`

- **The key.** The format adds `link` on a run, beside `text`, `style` and `concept`. A run's keys are the format's alone, so the key refuses nothing a run held before (DEC-012 point 1, [visual-communication:DEC-002-files-and-validation] point 4).
- **One absolute address** a reader may follow: a web address of the `https` or `http` scheme, or a mail address of the `mailto` scheme. It may hold letters outside ASCII, which a renderer writes as its medium asks.
- **What the check refuses:** a link that is no text, is empty, or holds a space or a control character; an address of another scheme, such as `javascript`, `data` or `file`; a web address with no host; and a web address that carries a user's name or password.
- **Read by one published standard's syntax.** The change that builds links names the standard, and the code that reads it.
- **Never followed.** The engine reads no network, so no check follows a link, and a dead one passes (DEC-001 point 8).
- **One link across runs.** Runs next to each other in one paragraph whose addresses are the same text are one link in the scene, which may hold runs of several styles and cross a line's break. A medium that places a text's lines apart spells it as its own record decides, and reports any loss (DEC-020 point 10).
- **Within one paragraph.** A link ends where its paragraph ends, so a linked run that goes on past a line feed gives a link of that address in each paragraph it reaches.
- **A link never splits.** Where a link and a span of one structure cross, the span splits at the link's edges, and each part keeps its structure.
- **In each language its own.** A run's link is part of its field's value, which differs between languages as its runs do (DEC-012 point 1). Whether the check holds any link equal across languages is translation's to decide (DEC-012, Implications).
- **No look of its own.** The format and the renderer give a link none (DEC-001 point 2). A linked run looks as the word content gives it, whose look its component declares.
- **A link drawn as its neighbours are asks for attention:** a run that holds a link, drawn in the same role and paint as a run of its text that holds none. The finding names the run. The content's author may give it another word, or the component's owner declare one. A text whose every run is one link has nothing to compare, and is not judged.
- **It takes focus in reading order,** in a medium where a keyboard moves through links. A link comes from content, so it is no focus stop a renderer adds ([visual-communication:DEC-023-html-page-modes] point 4).
- **A link always reads.** In a text that takes no place in the reading order, one marked `decoration` or a field's later showing (point 4), each link still reads at its place, with its words.
- **A link counts for no drawing's fit,** as a run's concept does not (DEC-012 point 2).
- **Only on a run, for now.** A link on a picture or on a whole instance, and a link to another page of the same piece, are each left to a later change.

### 4. A component marks what each of its texts is, and a list field reads as a list

- **A mark on the field.** The component that declares a field of text, or a slot of a layout, may mark it with one text structure, as it marks a field of runs (DEC-012 point 1). Each text part that shows the field carries the mark.
- **The marks:**
  - `heading`: the text heads what its instance holds.
  - `caption`: the text says what another field or slot of its component shows, which the mark names, never a part. The two read as one captioned whole, at the place of whichever comes first in reading order. A caption of a field that shows nothing, empty or not drawn, reads as a paragraph.
  - `paragraph`: the text is running text.
  - `decoration`: the text says nothing a reader lacks, such as a running footer.
- **A field passed on.** Where a `use` part passes a field on, the mark of the field the content writes holds, then that of the nearest field it fills that has one. Where none has one, it is a paragraph.
- **A top's field takes the top's mark alone,** under every drawing and whatever block draws it (DEC-009 point 5). So one with no mark reads as a paragraph.
- **Whose heading.** A heading belongs to the instance whose field the content wrote, wherever the text part that draws it lies.
- **A heading reads before what it heads.** Where a component names no reading order, a heading it draws after another text of its instance asks for attention, and its component then names an order (point 6).
- **A heading's level is computed,** within its page. An instance *holds* another where its parts draw the other, at any depth. A heading's level is one more than that of the nearest instance that holds its own and draws a heading with text in the scene, or 1 where none within its page does, so an instance whose optional head is left empty adds no level.
- **Six levels.** A renderer whose medium holds six levels of heading writes a deeper one as its sixth, and reports it `approximated`.
- **Two headings of one level.** A component whose own fields head at two levels, such as a title over a subtitle that heads, is left to a later change. Until then each takes its instance's level.
- **Each field reads once in a page,** at the first text that shows it in reading order, which the component orders (point 6). Every other text that shows it is decoration.
- **A list field reads as a list.** The items a `repeat` part draws from it are the list's entries, in the content's order (DEC-005 point 2). A list inside an entry is a list of its own. A list of ties reads as no list, and neither do a top's pages (point 6).
- **Or as no list, where its field is marked so.** A component may mark a list field, or a slot, to read as a list or as no list. The entries of no list read one after another, as parts do, such as the sections of a page. The mark passes on as a text's mark does, and where none holds, the field reads as a list.
- **An entry with nothing to read** is left out of its list, and a list none of whose entries has anything to read is no list.
- **A table, later.** A table's words, for its rows, its cells and its header cells, join the vocabulary in a change of their own. Until then a table drawn as a `repeat` part over rows reads as a list of its rows, each a list of its cells.

### 5. A picture's text is content, in a field tied to the picture

- **A picture's text** is what the reader's side gets in the picture's place. It is content, given in each language as any text is ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 2).
- **A picture the content names,** in a field that `content` or `produced` reads (DEC-025 point 1), takes its text from the field that field's mark names. A picture field passed on takes its mark as a text's field does (point 4).
- **A picture chosen by `file` or by `role`,** in a component or in a brand's drawing, is shown by its image part alone. That part names the field of its text, or says the picture needs none.
- **The field of a picture's text** is a field of text of the component, or a slot. It takes no runs, and no text part shows it.
- **One text in every mode.** A picture's variants, and the files a picture role takes in each mode, show one thing, so they share its text (DEC-006 point 3, DEC-025 point 4).
- **A picture that needs none** says so in one of two ways:
  - **The component,** on its image part, for a picture it chose that says nothing a reader lacks, such as a flourish. For a picture of `role`, the mark holds only while no brand's file shows more than the role names, such as words the component does not show.
  - **The content,** by giving the field empty text, `""`, for a picture the words around it already say. A field left out is not this.
- **A picture with no text,** not marked as needing none, takes its place as a picture whose text is missing, which a renderer marks where its medium can. A component may require its field, as it requires any.
- **An instance may take a text too.** A component may name a field, under the same rules, as the text of the whole its instance draws, the same under every drawing. A renderer gives a reader's tools that text before what the instance holds, in its reading order, never in its stead.
- **An instance's text is never asked for.** An instance with none reads what it holds, and none is marked as needing none.
- **Neither text counts for a drawing's fit,** a picture's nor an instance's.

### 6. A reading order follows the tree, unless a component names another

- **The draw order by default.** A page reads in the tree's order, each component's parts in the order it writes them (DEC-005 point 5).
- **A component may name another,** by listing its parts in the order a reader takes them. A part it leaves out follows, in draw order.
- **One order for every option and size, for now.** A switch of the order by an option or by a size is an addition left to the change that needs it.
- **Only its own parts.** A component never orders the parts of a component it places, which reads in its own order where its part lies (DEC-005 point 3).
- **A brand's drawing orders its own parts,** as it draws them. So switching the brand may change the order a page reads in.
- **Content orders nothing but a list's entries** (point 4).
- **What takes a place:** a text, a picture, and an instance with text. A shape, a text marked `decoration` and a picture that needs none take none, but for the links a text holds (point 3).
- **A piece's pages** read one after another, in the scene's order of its pages, each whole before the next.
- **Nothing of a renderer's own takes a place.** A page holds no control and no script (DEC-023 point 4), and what a renderer draws around its pages adds no element ([visual-communication:DEC-031-html-page-backdrop] point 4).

### 7. Emphasis in a PDF counts as carried

- **The case.** The PDF renderer writes PDF 1.7, whose standard structure types hold none for emphasis.
- **The form.** The renderer writes `emphasis` and `strong` as structure types of the file's own, a form PDF 1.7 defines.
- **Carried.** Its declaration names both words, and no loss stands for them. That this form counts as carried is a judgement, not a test's finding, and accepting this record accepts it.
- **PDF 2.0, later.** PDF 2.0 holds both as standard types. A move to it is a version of the renderer of its own, after a test of the tools that read it.

### 8. A picture a renderer does not draw keeps its text

- **Which pictures.** A renderer leaves out an image with no picture for the combination it draws, or one it cannot read or decode, and reports it (DEC-005 point 9), as does a renderer that refuses an image. An export refuses a piece whose picture file is missing or cannot be read before any renderer runs (DEC-025 point 9), so this point serves a picture the check passed.
- **Its text stays,** at the picture's place in the reading order, as the text of a picture not drawn, with nothing drawn. Each renderer's reference page names the form it takes.
- **Nothing stays** for a picture that needs none, nor for one the engine draws nowhere: an image whose field the content leaves empty, or a picture role the brand gives no value (DEC-025 points 1 and 4).
- **The fallback.** Where a renderer draws as a picture a part it cannot draw (DEC-005 point 9), the picture takes as its text the text of the instance the part draws, where its component names one, or else the texts of the part, in their reading order. The renderer reports as lost the structure, the links and the pictures' texts inside it.

### 9. A format read whole carries no reader's side but links

- **A fact of a format.** A renderer's declaration may say, beside a format, that it is *read whole*, as it names a format that holds modes (DEC-005 point 9): each of its files is read as one whole, as an image is, and the document that shows it gives its text.
- **The format fixes what such a format leaves out:** the words of point 1, but a run's link. Nothing a seeing reader sees is among them, such as a frame, a paint, a font or a text's words.
- **No loss for them.** For a format read whole, neither the check nor the renderer reports a loss of these words.
- **The one exception** to a renderer reporting what it does not draw (DEC-001 point 2), with its cost: a file of such a format handed out alone has no document around it to give its text, so a reader who does not see it gets none of its structure, and nothing reports that. Accepting this record accepts both.
- **A later word joins** what such a format leaves out only when its change says so, and only a word no seeing reader acts on. So a link on a picture or on an instance (point 3) would be carried, or reported lost.
- **The SVG renderer's two formats are read whole** (DEC-020, [visual-communication:DEC-018-copy-follows-reader-mode] point 4): the SVG format and its format of a switching file. The renderer draws a run's link. That a keyboard reader who opens such a file alone moves through its links in draw order is a loss its reference page states and no check reports.
- **The PDF and HTML renderers' formats** are not read whole, and carry each word from the change that brings it into the scene.

### 10. What this adds to format 1, and what a change of it breaks

- **Added to the format, each optional:**
  - a run structure for each word of a field's run styles
  - the key `link` on a run
  - a field's mark of its text's structure, a caption's with the field it captions
  - a list field's mark that it reads as a list or as no list
  - a picture field's mark that names the field of its text, an image part's field of text or its mark that it needs none, and a component's field of its instance's text
  - a component's reading order of its parts
- **Added to the seam,** whose version is apart from the format's (DEC-005 point 8):
  - in the scene, each of these, with a heading's level and each list
  - in a renderer's declaration, each word it spells, and the fact that a format is read whole
- **Spelled in the format by the changes that build it.** How a component writes each declaration, and how the scene holds it, is set by the change that builds it.
- **The format number stays 1** (DEC-003 points 1 and 3). Each addition is a key format 1's schemas do not know, no field becomes required, and each finding that fails reads a key format 1 refused, so no file format 1 accepted takes a new failure.
- **New attention, on files format 1 accepted.** Point 11's finding on a picture with no field for its text reaches each component that shows one today. This is less than DEC-012 point 7 promised for runs, under which no finding arose at all.
- **The seam's version rises** in the change that first gives the scene its shape for every word of point 1. A change that fills that shape raises nothing, and one that must reshape it raises the seam again.
- **What a change of a library breaks.** A change of the structure a component gives a word, of a text's or a list field's mark, or of a reading order, one added or removed included, breaks no library, and a piece meets it only when its lock moves (DEC-003 point 8). A field of a picture's or an instance's text added where there was none breaks nothing. Pointing a picture's text, an instance's text or a caption at another field, or giving a picture's field up for needing none, breaks.
- **Shown where a lock moves.** Beside each page that differs, the before-and-after names each structure, mark, picture's or instance's text and reading order that differs between its two scenes ([visual-communication:DEC-019-lock-moves-and-pruning] point 5).
- **Said where it is released.** The comparison a release makes of each stable component with its previous version states each such change, as a fact, for whoever releases the library (DEC-003 point 7).

### 11. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct (DEC-002 point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it.

- **Where each lies.** A finding on what a component declares lies in the component's version, and one on a brand's drawing in the brand's. A finding on a run lies in the content file, at the run (DEC-012 point 8). A finding on what a piece draws lies at the piece.
- **Fails validation:**
  - in a component: a run structure that is not `emphasis`, `strong` or `code`, or one for a word its field does not declare
  - in a component: a text's mark that is not `heading`, `caption`, `paragraph` or `decoration`, or one anywhere but on one of its fields of text or on a slot; a caption that names no other field or slot of the component, or one another caption names
  - in a component: a mark that a field reads as a list or as no list, on a field or slot that holds no list
  - in a component: a picture's or an instance's text that names no field of text of the component, or names a field of runs, or a field a text part shows
  - in a component or a brand's drawing: an image part of `file` or `role` that both names a field for its text and says it needs none; or a mark that a picture needs none on an image of `content` or `produced`
  - in a component or a brand's drawing: a reading order that names a part it does not hold, or one part twice
  - in content: a `link` point 3 refuses
- **Asks for attention, never failing:**
  - in a component: a picture with no field for its text, neither on its field of `content` or `produced`, nor on its image part of `file` or `role`, which does not say it needs none. It lies once, in the component's version, and names its owner.
  - in a component: a heading drawn after another of its texts (point 4)
  - at a piece that exports a format not read whole: a picture whose text field the content leaves out. It names the field and the content's author.
  - at a piece: a link drawn as its neighbours are (point 3)
- **A brand's drawing is judged as a component** on a picture's text that an image part of `file` or `role` names, and on a heading it draws after another text (DEC-009 point 9).

## Rationale

**Point 1, one vocabulary.** The format already fixes what every renderer reads, such as the primitives and their properties (DEC-005 point 5), and only the capability ships renderers (DEC-005 point 12). Words that name no medium leave no renderer to choose its own, so a piece reads alike in each medium that carries them. The name `decoration` says what an author means. The five cases are ones no renderer should settle alone.

**Point 2, a run's structure.** A run's word already says what the run is, such as a prompt or a strong phrase (DEC-012, Rationale). The component decides how the word looks (DEC-001 point 6), so it decides with it what the word is to a reader's tools, and content names only words its component declares (DEC-001 point 3). Every run already written gains its structure when its library declares one, with no content changed. `emphasis`, `strong` and `code` are the spans a reader's tools tell apart in both media that carry the reader's side, the HTML page and the PDF. Other spans, such as a quotation or a term defined, are additions when a slice needs them.

**Point 3, a run's link.** A link that runs a script or reads a local file is no place a reader goes, and a handed-out file should carry no password. Web and mail addresses are what a deck or a page links to, and a later scheme is an addition. One standard's syntax makes the check answer the same on every machine. A link across a strong phrase, or across a line's break, is still one place to go, and the engine breaks lines across runs (DEC-012 point 4). Both media need spans that nest: a split link would read as two links to one place, and a split emphasis reads as before. Each language may link to a page in its own language. Through the word that holds it, a link's look stays the brand's, and the check compares what is drawn, since two words may share one role and one paint (DEC-012 point 2). A link a keyboard reaches is never hidden from a reader's tools. A link on a picture or on an instance would take a key on a mapping that places a component, where a field of that name may lie at format 1 (DEC-002 point 4), and a link to another page of the piece needs an address of the piece's own.

**Point 4, a text's mark.** Where a slide's title is a heading, it is one under every brand, because of what the field is, not how a drawing draws it. A mark on the component as a whole would not say which of its texts heads. The component that declares the field the content writes knows what that text is, such as a slide's title, and a block it passes the field to knows only its own kind of text. A top's field is drawn by each brand's drawing, which may pass it to another block, so only the top's own mark holds there. A field shown twice, such as a title in a page's footer, is one text to a reader: read twice it is noise, and a duplicate heading misleads.

**Point 4, a heading's level and a list.** A project reuses small parts most (DEC-001, Context), and the engine knows what holds each instance, so it computes a level as it computes a frame. Counting only a heading drawn with text keeps a level from being skipped, which a reader's tools report as a fault, and each page is read on its own, so its headings start at 1. A list holds items of one kind in the content's order, such as steps, links, cards or a form's fields, which is what a list is to a reader. A page's sections or a set of panels need not read as one, so a component marks those, and no other component changes. A list of lists still reads in order, so until a table's words come a reader loses only which header heads a cell.

**Point 5, a picture's text.** Words stay out of a picture and are translated with the content (DEC-006 point 2). A picture the content names lies in a field every drawing of a top takes, so a text tied to that field reaches every drawing that shows the picture, the same under each, as the field's words do, and no drawing need take it to fit. A field of runs is shown by a text part alone (DEC-012 point 2), and a text no text part shows is not met twice. HTML's empty `alt` says a picture needs none, so an author who knows the web knows `""`, and a field left out stays a question, so a forgotten text still asks for attention. A component knows whether a picture it chose needs none, such as a flourish, but not one the content chose, such as a chart, and the brand chooses a role's file. A diagram's labels, read one after another, do not say which joins which, and a text read first says so.

**Point 6, the reading order.** The draw order is fixed and known: a component writes its parts in order, mostly the order a reader takes them, as a title before its body, and the content orders its items. A component's inside is private, so its library may change it freely (DEC-005 point 3). A brand's drawing has parts no other drawing shares, so only it can order them. A reading order follows where parts lie, which is the drawing's: a drawing that sets a subtitle above its title reads it first, as a seeing reader does.

**Point 7, emphasis in a PDF.** It keeps the file at PDF 1.7. The cost is that some tools read the file's own types as less than the HTML page's own element.

**Point 8, a picture not drawn.** A reader who sees the page sees the gap, which the loss report names for whoever can mend it (DEC-005 point 9). Where the engine draws a picture nowhere, nothing lies there to stand for.

**Point 9, formats read whole.** A file read whole has no reader's side inside it: the page that shows it gives its text (DEC-018 point 6). The SVG renderer draws the previews of every piece and the figures of documentation pages, so without the fact every piece would be told of a loss on every list and heading. With nothing a seeing reader sees in the format's list, no loss of the drawing hides in the fact. No piece is told of a loss while a word waits for the PDF or the HTML renderer.

**Point 10, format 1 and what breaks.** A renderer reads what it did not read before, so the seam rises with the scene's shape (DEC-005 point 8). The record of change over time counts as breaking a change of a name a piece uses, or of what it means (DEC-003 point 6). A word means what content says by choosing it, and that stays. Its look and its structure are the component's way of showing it, to the eye and to a reader's tools, so a change of its structure is of the kind a change of its role or paint is (DEC-012 point 6). Changing the first word breaks for another reason: every run that names no word becomes another word (DEC-012 point 6). Content fills a field of a picture's text, or of a caption, to say something of another field, so pointing it elsewhere changes what it says. No image shows a change of the reader's side, so the before-and-after names it, and the lock and the before-and-after protect each piece from it, as from a change of look (DEC-003 point 6).

**Point 11, the checks.** A piece drawn only in formats read whole gives no picture's text to any reader, so asking for one there is noise no one need answer.

### Alternatives considered

- **Words each library declares, or the foundations:** a renderer spells a word in its code, so a library's word would reach none, and the foundations would fix the words at a version apart from the renderers' (DEC-001 point 7).
- **A run that names its structure, as `structure: emphasis`:** content would make a second choice, which its component did not declare.
- **`emphasis` and `code` alone, `strong` read as emphasis:** it would merge two spans both media hold apart.
- **A change of a word's structure counted as breaking:** it changes how a word shows, not what content says by it.
- **An address relative to the file, or to the repository:** an exported file travels alone (DEC-006 point 7).
- **A link given its look by the format, such as an underline:** the renderer would add a look no brand gives.
- **A heading declared by a key on its text part:** each drawing of a layout could declare it otherwise, though content is written against the top (DEC-009 point 5).
- **A heading read from its typography role:** a role is a look a brand gives a value, and names no level, and a large text need not be a heading (DEC-001 point 5).
- **A heading level the component declares:** a reused block would keep its level wherever it lies.
- **A caption of its whole instance:** on a page drawn in a layout the instance is the page, so it would caption the slide, its title included.
- **A caption that names the part it captions:** a brand's drawing has parts of its own, so the part would be undefined under it.
- **A list field that reads as a list only where it is marked:** most lists hold items a reader takes as a list, so most components would need the mark.
- **The mark that a list reads as no list, on the `repeat` part:** a brand's drawing repeats a top's field with parts of its own, so switching the brand could change what is a list.
- **A table's words in this record:** a header cell heads cells across two repeats, which no word here does, and needs a design of its own.
- **A reserved key `alt` on every mapping that places a component:** it would refuse a field of that name that format 1 accepts (DEC-002 point 4, DEC-003 point 3).
- **A picture's text in its picture file's name, as `{file: team.jpg, text: …}`:** every picture field would take a mapping, and its text would stay apart from the component that knows the picture.
- **A picture's text named by each image part, whatever the picture's source:** two drawings of one layout could give one picture two texts.
- **A picture's text that counts for a drawing's fit:** a text no seeing reader sees would swap a brand's look for the top's own (DEC-009 point 6).
- **A picture role's text that the brand gives,** left to later: a brand holds no language, and a logo's text may need one.
- **A picture's text required,** rejected for format 1: a field that becomes required refuses files format 1 accepted (DEC-003 point 3, DEC-012 point 7).
- **An instance's text read in place of what it holds:** it would hide the texts, links and headings a diagram's cards hold.
- **A reading order computed from where elements lie:** it misreads two columns, and changes with a page's size.
- **A reading order that reaches into placed components:** it would break when a placed component changed its private parts.
- **A reading order of the top's fields, which every drawing takes, as it takes their marks:** a drawing sets where the fields lie, so a reader who does not see would take them in another order than a seeing reader does, and an order of fields would reach into the blocks a drawing passes them to.
- **PDF 2.0, which holds emphasis in standard types,** rejected for now: the renderer would have to meet PDF 2.0 throughout, untried with the tools that read it, for two words.
- **Emphasis in a PDF reported as `approximated`:** the file holds the emphasis in a form PDF 1.7 defines, which a tool that reads the file's own types reads.
- **A picture not drawn that takes its text out too:** a reader who does not see the page would lose a text that a fault of the drawing took.
- **Losses of the reader's side reported for the formats a piece exports, and never for its previews:** a figure handed out or shown as SVG is read whole, and the document gives its text, so each of its lists and headings would be a loss no one could mend.
- **A state each renderer declares for each property, "not for its medium":** its bound would rest on each declaration, where the format's own list holds it by construction.
- **SVG's links counted among what a format read whole leaves out:** a seeing reader who opens the file alone follows a link, so a loss would hide.

## Implications

- **The change of a text's structure and a reading order** builds points 4 and 6 and the fact that a format is read whole, which the SVG renderer's two formats come to declare, gives the scene and a renderer's declaration their shape for every word, and makes the before-and-after name each difference (point 10).
- **The change of a run's link and structure** builds points 2 and 3, with code that reads an address on the terms the capability's code takes (DEC-002 point 8), and the SVG renderer's drawing of a link.
- **The change of a picture's text** builds points 5 and 8.
- **The shipped libraries' components** come to declare what they give the reader's side, each in a release of its library ([visual-communication:DEC-013-shipped-library-releases]), as its component's design, not this record's. A release that gives every picture a field for its text leaves no attention of point 11 on its library.
- **The PDF renderer** becomes a tagged PDF in these changes. Its `not-carried`, a list in its declaration that no check reads, loses each item as it comes to carry it, a table included since it reads as lists, and goes when it is empty.
- **The HTML renderer** spells the reader's side as #2740's record decides, and its `not-carried` goes the same way.
- **#2740's body** comes to say that its test's table reads as a list of lists, until the change of a table's words.
- **The Feature's criterion on links** is met by a run's link.
- **The capability's pages,** each edit anchored to this record:
  - in this change, once this record is accepted: `outputs.md`, *What the PDF renderer does not carry yet*: the form a later version gives emphasis, an instance's text and a picture not drawn, which tools read each, and PDF 2.0 as a later step
  - with the change of a run's link and structure: `outputs.md`, *The SVG renderer*: how it draws a run's link, and the order a keyboard takes its links in; `outputs.md`, *Plugins*: how a renderer writes an address that holds letters outside ASCII
  - with the change that builds each: `components.md`, *Text*, *Lists* and *Parts*: an example of one span across runs, a field passed on, a heading's computed level, a field shown twice, a picture that needs none, and a reading order a component names
  - the rest of each page describes what a change builds, with that change
- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-001 point 2, "What a renderer cannot draw", comes to add that a renderer may say a format is read whole, which carries none of the reader's side the format lists but links, and reports no loss of it: the one exception to a renderer reporting what it does not draw (point 9).
  - DEC-001 point 3, "Runs", comes to add that a run may also hold a link, which may differ between languages (point 3).
  - DEC-001 point 5, "Switching the brand changes how a piece looks", comes to add that it may also change the order a page reads in and the text of a picture the brand's drawing chose, and changes no structure (points 2, 4, 5 and 6).
  - DEC-002 point 3, "Strict", and point 4, "Reserved keys": the keys they name on a run, `text`, `style` and `concept`, come to include `link`.
  - DEC-003 point 6, "What breaks", comes to add that a change of the structure, a mark or the reading order a component gives does not break, and that pointing a picture's text, an instance's text or a caption at another field, or giving a picture's field up for needing none, breaks (point 10).
  - DEC-003 point 7, "The promise is checked", comes to add that the comparison states, as a fact, each change of what a stable component declares of the reader's side (point 10).
  - DEC-005 point 5, "Primitives at the leaves": a text's bullet comes to add a run's structure and a text's mark, a heading with its level.
  - DEC-005 point 5, "Draw order is the tree's order", comes to add that the reading order follows it, unless a component names another (point 6).
  - DEC-005 point 5, the bullet on documents and PDF files, comes to say that the scene holds the reader's side in the words of point 1, which each renderer spells, and that tables stay promised, for a later change.
  - DEC-005 point 9, "Each declares what it supports", comes to add that a renderer declares each word it spells, and names each of its formats that is read whole.
  - DEC-005 point 9, "Losses are known before a plugin runs", comes to add that a format read whole loses none of the reader's side the format lists.
  - DEC-005 point 9, "One fallback for renderers", comes to add that the picture takes the text of the instance the part draws, or else the part's texts in their reading order (point 8).
  - DEC-006 point 2, "None of the piece's words", comes to add that a picture's text is content too, in a field tied to the picture.
  - DEC-009 point 5, "A drawing is written against the top", comes to add that a drawing takes what the top declares of the reader's side, and declares none of its own but the texts of the pictures it chose by `file` or `role` and the reading order of its own parts.
  - DEC-009 point 6, "A drawing that does not fit", comes to add that a run's structure, a run's link, a picture's text and an instance's text count for no drawing's fit.
  - DEC-009 point 9 comes to add point 11's findings on a brand's drawing: its pictures' texts and its reading order among those that fail, a heading drawn after another text among those that ask for attention.
  - DEC-012's summary: "a mapping of its `text`, its `style` and perhaps its `concept`" comes to add "or its `link`", and "The format fixes a run's three keys" comes to read: the format fixes a run's keys.
  - DEC-012's Decision's opening: "a mapping of `text`, `style` and `concept`, keys the format fixes on a run" comes to read: a mapping of `text`, `style`, `concept` and `link`.
  - DEC-012 point 1, its bullets "A run" and "Keys the format fixes": a run may also hold `link`, which the format fixes with the other three.
  - DEC-012 point 2, "Only how the run is set": a run's word also chooses the run's structure, which its field declares for the word.
  - DEC-012 point 8's finding on a run with another key comes to name `link` among the keys it allows.
  - DEC-012's Implications, "Left to later changes": the bullets on a run's link and on a run's structure leave that list, and DEC-012's Implications come to say that this record decides both.
  - DEC-019 point 5, "The before-and-after stays a command": "prints each page that differs" comes to add that it names each difference of the reader's side between its two scenes (point 10).
  - DEC-020 point 10, "What a reader who does not see the page gets": its citation of #2739 comes to cite this record. "what a shape or a picture says" comes to read: how the page spells a picture's text, since a shape is decoration here and a picture's text is content. "a reading order that differs from the draw order" comes to read: how the page spells a reading order a component names.
  - DEC-025 point 1, "`content: <field>`", comes to add that the field's mark may name the field of the picture's text.
  - DEC-025 point 11, "A picture's text", comes to cite this record in place of the issue.
- **Read against, and left as they stand:** DEC-003 point 3, DEC-005 points 3 and 8, [visual-communication:DEC-010-list-item-fields], [visual-communication:DEC-011-tie-ends], DEC-018 point 6, DEC-023 point 4 and DEC-031 point 4.
- **Left to later changes,** beside those the Decision and the Alternatives name:
  - whether a list reads as ordered, where its pattern numbers its items
  - a line under or through a text, which a brand would give a typography role
  - a page's regions, such as its header, its navigation, its main part and its footer, which a reader's tools move between
  - a run's language, where a phrase is in another language than its piece, which a reader's tools pronounce by
  - whether a picture's text says what the picture shows, which a graphic rule or the reviewer would judge
  - a file's own title, which a reader's tools announce first
  - how the agent that translates carries a picture's text and a run's link
- **Revisit this record** in any of these cases:
  - #2740's test finds a word a reader's tools cannot get from the HTML page
  - a screen reader misreads the PDF's own types, or a figure with nothing drawn
  - a computed level misleads in a real piece
  - the PDF renderer moves to PDF 2.0
  - a renderer whose medium is no picture yet holds no reader's side, such as a whiteboard service's, which revisits point 9.
