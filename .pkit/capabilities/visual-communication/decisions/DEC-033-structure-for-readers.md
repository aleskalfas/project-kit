---
id: DEC-033
title: A component declares what its runs, texts and pictures are to a reader who does not see them, in words the format fixes
status: proposed
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a reader who does not see a piece, such as one who uses a screen reader, gets its words with what each of them is: a heading, a list, emphasis, a link or a picture's text. The format fixes these words, and each renderer spells them in its medium. A component says what each word of a field's run styles is, such as `strong`, and what each of its fields of text is, such as a heading or a caption. A heading's level comes from what holds it, and a list field reads as a list. A run may hold a link. A picture's text is content, in a field tied to the picture. A page reads in its draw order, unless a component names another. A brand's drawing changes none of this but the order of its own parts, and the pictures it chooses for its look. A PDF carries emphasis as a type of its own, mapped to a standard one. A format whose files are pictures, such as SVG, carries none of it but links, and no loss is reported for that. Every file format 1 accepted reads and draws as before.

## Context

The founding record has each renderer project one scene into its medium, and report what it lost ([visual-communication:DEC-001-visual-communication-discipline] point 2). The record of the engine has a text hold paragraphs of runs, each with its typography role, its paint, its fonts and perhaps a link. It promises documents and PDF files alternative text, a reading order, and structure such as headings, lists, tables and captions ([visual-communication:DEC-005-engine-and-plugins] point 5). No record says who declares them, or in which words. The Feature this record serves asks that links, a picture's text, a reading order and a run's structure reach the HTML page and the PDF, and that the PDF's declared losses for them go ([project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570)).

Four accepted records bear on it:
- **Runs.** A run's word is its field's own, and says nothing of structure to a renderer. A run's link is a key the format adds on a run, which refuses nothing ([visual-communication:DEC-012-text-runs], Implications).
- **Picture files.** What a reader who does not see a picture gets is left to this record ([visual-communication:DEC-025-picture-files] point 11).
- **The HTML page.** How its elements carry these words is [project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740)'s, which follows this record ([visual-communication:DEC-020-html-page-drawing] point 10).
- **The HTML page's modes.** A page holds no control and no script, so no switch takes a place in its reading order ([visual-communication:DEC-023-html-page-modes] point 4).

What format 1 holds today:
- **The scene** holds no structure, no link, no picture's text and no reading order. Draw order is the tree's order (DEC-005 point 5).
- **The PDF renderer** writes PDF 1.7, with no tags. Its declaration says under `not-carried` that it carries no alternative text, no reading order and no structure, and the HTML renderer's says the same. PDF 1.7's standard structure types hold code and a link, and none for emphasis. PDF 2.0 adds `Em` and `Strong`.
- **A picture a renderer does not draw.** Each renderer draws every image it is handed. It leaves out, and reports, an image with no picture for the combination it draws, and one it cannot read or decode (the capability's outputs page). An export refuses, before any renderer runs, a piece whose picture file is missing or cannot be read ([visual-communication:DEC-025-picture-files] point 9).
- **The check** reports as a loss each property of a scene that a renderer does not declare (DEC-005 point 9). The renderers it reads for a piece are the SVG renderer, which draws every piece's previews, and the renderer of each format the piece exports in (the capability's checks page, *Losses*).
- **The SVG renderer is for pictures:** a figure on a GitHub page, a picture inside another document, and a build with no browser (DEC-020). A documentation page shows its file as an image, and gives it its text alternative ([visual-communication:DEC-018-copy-follows-reader-mode] point 6).
- **A brand's drawing of a layout** takes what content gives the top, and draws it with parts of its own. It fits an instance only where it takes all the content gives ([visual-communication:DEC-009-layout-defaults] points 5 and 6).
- **A table** is no primitive and no word of the format. A component draws one as a `repeat` part over rows, each repeating over cells.
- **Format 1 grows only by additions** that every file written before still meets. No field becomes required, and no value accepted before is refused ([visual-communication:DEC-003-change-over-time] point 3).

Three terms:
- A *reader's side* is what a reader who does not see the drawing gets of a piece: its words, with what each of them is. A reader's tools, such as a screen reader, read it from the file.
- *Structure* is what a run, a text, a list field or a picture is on the reader's side, such as emphasis, a heading, a list or a picture's text.
- An *instance's text* is a text a component gives the whole one of its instances draws, such as a diagram of boxes and lines, apart from the texts the instance holds (point 5).

## Decision

**The format fixes the words of the reader's side, and each renderer spells them in its medium. A component gives each word of a field's run styles its structure, marks what each of its fields of text is, ties a picture's text to the picture, and may name its parts' reading order. A run may hold a link. A heading's level is computed, a list field reads as a list, and a page reads in its draw order by default. A renderer may say a format's files are pictures, which carry none of these words but links, and no loss is reported for them.**

### 1. The format fixes one vocabulary of structure, and each renderer spells it

- **Words that name no medium.** The scene holds structure in words of the format's own, such as `emphasis` or `heading`. Each renderer spells each word in its medium, and its reference page says how (DEC-001 point 2). So no renderer chooses its own words, and a piece reads alike in each medium that carries them.
- **The format fixes them, not a library.** A renderer spells a word in its code, and only the capability ships renderers (DEC-005 point 12). A word a library declared would reach no renderer. The foundations are a library too, released apart from the renderers.
- **The words:**
  - a run's structure: `emphasis`, `strong` and `code` (point 2), and a run's link (point 3)
  - a text's structure: `heading`, with its level, `caption`, `paragraph` and `decoration` (point 4)
  - a list, and its entries (point 4)
  - a picture's text, or that it needs none, and an instance's text (point 5)
  - a reading order (point 6)
- **A word beyond these is an addition.** It refuses no file (DEC-003 point 3). A renderer reads it as something new, so the seam's version rises with it (DEC-005 point 8).
- **Declared as a property is.** A renderer declares each word it spells, as it declares each primitive and property it draws (DEC-005 point 9). One it does not spell it leaves undeclared, and the check reports it lost, but where point 9 exempts it.
- **Named as the web names them.** The words take WAI-ARIA's role names where the meanings match, as the scene's properties take SVG's (DEC-005 point 5). `decoration` is ARIA's presentation, named for what an author means by it. A word added later takes its name so.
- **Spelled by each renderer,** but where this record spells a case no renderer should settle alone: emphasis in a PDF (point 7), an instance's text (point 5), a picture a renderer does not draw (point 8) and a format whose files are pictures (point 9). Where two kinds of span cross, the format says which splits (point 3).
- **Spelled in the format by the changes that build it.** How a component writes each declaration below, and how the scene holds it, is set there. The first of them sets the scene's whole shape (point 10). Each spelling is a key that format 1's schemas do not know, so no file they accepted holds one.

### 2. A component gives each run style its structure

- **For each word of a field's run styles,** the component may name one run structure. A word that names none is plain text on the reader's side. Which structure a word names is the component's design, released in its library, never this record's.
- **What each says:**
  - `emphasis` stresses a span, as a voice stresses a word.
  - `strong` marks a span as important.
  - `code` marks a span as code, such as a command or a name a machine reads.
- **Content names a word, never a structure.** The component decides how a run looks, and decides with it what the run is on the reader's side (DEC-001 point 6). Switching the brand changes neither (DEC-001 point 5).
- **The words stay the field's own.** A run structure is no word content gives. So the record of runs' refusal of words the format fixes for every field still holds (DEC-012, Alternatives).
- **The first word may name one.** A field given as text then reads in it throughout, as code where its first word names `code`.
- **One span across runs.** Runs next to each other in one paragraph that take the same structure are one span of it. So a prompt and the command after it, each of a word that names `code`, read as one span of code.
- **A block of code.** A text read as a paragraph, whose every run is `code`, reads as one block of code, its paragraphs its lines, kept as written. A text marked otherwise, such as a heading, keeps its mark, and its runs read as spans of code (point 4).
- **One structure for the field, under every drawing.** It lies with the field's words, so each text part that shows the field carries it. A brand's drawing of a layout takes it with the words the top declares, and declares none of its own (DEC-009 point 5). It counts for no drawing's fit, as a run's concept does not (DEC-012 point 2).
- **What a change of it breaks.** A change of the structure a word names, one added or removed included, breaks no library. A word says what a run is. Its look and its structure are how the component shows that, to the eye and to a reader's tools. A change of either changes how a piece shows a word, as a change of a word's role or paint does (DEC-012 point 6). A piece meets it only when its lock moves (DEC-003 point 8).
- **Shown where a lock moves.** No image shows such a change. So the before-and-after names it: beside each page that differs, it names each structure, mark, picture's or instance's text and reading order that differs between its two scenes ([visual-communication:DEC-019-lock-moves-and-pruning] point 5). The lock and the before-and-after then protect each piece from it, as from a change of look (DEC-003 point 6).
- **Said where it is released.** The comparison a release makes of each stable component with its previous version states it too, as a fact, for whoever releases the library (DEC-003 point 7).

### 3. A run may hold a link, under the key `link`

- **The key.** The format adds `link` on a run, beside `text`, `style` and `concept`. A run's keys are the format's alone, so the key refuses nothing a run held before (DEC-012 point 1, [visual-communication:DEC-002-files-and-validation] point 4).
- **What it holds:** one address, as text, that a reader may follow. It is a web address of the `https` or `http` scheme, with a host, or a mail address of the `mailto` scheme. It is absolute, since an exported file travels alone ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7).
- **Letters of any language.** An address may hold letters outside ASCII, such as a Czech word. A renderer writes it as its medium asks: a host in its ASCII form, and the rest encoded as a web address encodes it.
- **Read by one standard.** The check reads an address by one published standard's syntax, so it answers the same on every machine. The change that builds links names the standard, and the code that reads it.
- **What the check refuses:** a link that is no text, is empty, or holds a space or a control character. It also refuses an address of another scheme, such as `javascript`, `data` or `file`, and a web address with no host. So is a web address that carries a user's name or password.
- **Never followed by the capability.** The engine reads no network, so no check follows a link, and a dead one passes (DEC-001 point 8).
- **One link across runs.** Runs next to each other in one paragraph whose addresses are the same text are one link. So a link may hold runs of several styles, and cross a line's break. The scene holds it as one link. A medium that places a text's lines apart spells it as its own record decides, and reports any loss ([visual-communication:DEC-020-html-page-drawing] point 10).
- **Within one paragraph.** A link ends where its paragraph ends. A linked run that goes on past a line feed gives a link of that address in each paragraph it reaches.
- **A link never splits.** Where a link and a span of one structure cross, the span splits at the link's edges, and each part keeps its structure. So every medium nests them alike.
- **In each language its own.** A run's link is part of its field's value, which differs between languages as its runs do (DEC-012 point 1). So each language may link to a page in its own language. Whether the check holds any link equal across languages is translation's to decide (DEC-012, Implications).
- **Its look is its word's.** The format gives a link no look, and a renderer adds none (DEC-001 point 2). A linked run looks as the word content gives it, whose look its component declares. Whether that look sets a link apart is judged by the graphic rules, under which colour is never the only signal (RS-GRAPHIC-006). The check asks for attention where a link is drawn as its neighbours are (point 11).
- **It takes focus in reading order,** in a medium where a keyboard moves through links. A link comes from content, so it is no focus stop a renderer adds (DEC-023 point 4).
- **A link always reads.** A text that takes no place in the reading order, one marked `decoration` or a field's later showing (point 4), still reads each of its links at its place, with the link's words. So no link a keyboard reaches is hidden from a reader's tools.
- **It counts for no drawing's fit,** as a run's concept does not.
- **Only on a run, for now.** A link on a picture or on a whole instance would take a key on a mapping that places a component. A field of that name may lie there at format 1 (DEC-002 point 4). A link to another page of the same piece needs an address of the piece's own. Each is left to a later change.

### 4. A component marks what each of its texts is, and a list field reads as a list

- **A mark on the field.** A component marks a field of text, or a slot of a layout, with one text structure, as it marks a field of runs (DEC-012 point 1). Each text part that shows the field carries the mark.
- **The marks:**
  - `heading`: the text heads what its instance holds.
  - `caption`: the text says what another field or slot of its component shows, which the mark names, such as the field that holds a figure's picture. What that field shows and its caption read as one captioned whole, at the place of whichever of the two comes first in reading order. A caption of a field that shows nothing, empty or not drawn, reads as a paragraph.
  - `paragraph`: the text is running text.
  - `decoration`: the text says nothing a reader lacks, such as a running footer. It takes no place in the reading order.
- **Who: the component that declares the field.** Content writes the field, and its component says what it is (DEC-001 point 6). A brand's drawing of a layout takes the mark with the top's field, as it takes the field's words (DEC-009 point 5). A caption names a field, which every drawing takes, never a part, which each drawing has of its own. So switching the brand changes no heading and no caption.
- **A field passed on.** Where a `use` part passes a field on, the mark of the field the content writes holds. Where that field has none, the mark of a field it fills holds, the nearest first. Where none has one, it is a paragraph. So a block that marks its head gives a heading where a pattern passes it an unmarked field. A pattern that marks a field `paragraph` keeps a block's heading out.
- **A top's field takes the top's mark alone.** A brand's drawing chooses what it passes a top's field to. So a top's field that has no mark reads as a paragraph, under every drawing, whatever block draws it.
- **Whose heading.** A heading belongs to the instance whose field the content wrote, wherever the text part that draws it lies.
- **A heading reads before what it heads.** Where a component names no reading order, a heading it draws after another text of its instance asks for attention (point 11). Its component then names an order (point 6).
- **A heading's level is computed,** within its page. An instance *holds* another where its parts draw the other, at any depth. A heading's level is one more than that of the nearest instance that holds its own and draws a heading with text in the scene. Where no instance within its page does, its level is 1.
- **So a block moves freely.** A card's head inside a slide whose title is a heading is of level 2, and the same card on a page alone is of level 1. An instance whose optional head is left empty adds no level, so no level is skipped.
- **Six levels.** A renderer whose medium holds six levels of heading writes a deeper one as its sixth, and reports it `approximated`.
- **Two headings of one level.** A component whose own fields head at two levels, such as a title over a subtitle that heads, is left to a later change. Until then each takes its instance's level.
- **Each field reads once.** A field that two texts show reads on the reader's side at the first in reading order, which the component orders (point 6). Every other text that shows it is decoration, as a summary that repeats a title is.
- **Not a typography role.** A role gives a text its look, and a brand gives the role its value (DEC-001 point 5). A large text need not be a heading, and a role names no level.
- **A list field reads as a list.** The items a `repeat` part draws from it are the list's entries, in the content's order (DEC-005 point 2). A list inside an entry is a list of its own. A list of ties reads as no list, and neither do a top's pages (point 6).
- **Or as no list, where its field is marked so.** A component marks a list field, or a slot, to read as a list or as no list. Its entries then read one after another, as parts do, such as the sections of a page.
- **The mark passes on as a text's mark does.** Where a `use` part passes a list field on, the mark of the field the content writes holds, then that of the nearest field it fills that has one. Where none has one, it reads as a list. A top's field takes the top's mark alone. So a brand's drawing, which repeats a top's field with parts of its own, changes no list.
- **An entry with nothing to read** is left out of its list. A list none of whose entries has anything to read is no list.
- **A table, later.** A table needs words for its rows, its cells and its header cells. They join the vocabulary in a change of their own (Implications). Until then a table drawn as a `repeat` part over rows reads as a list of its rows, each a list of its cells.
- **What a change of it breaks.** A mark added, removed or changed breaks no library, as point 2 says of a run's structure. A caption pointed at another field breaks, as a picture's text does (point 5).

### 5. A picture's text is content, in a field tied to the picture

- **A picture's text** is what the reader's side gets in the picture's place. Words stay out of a picture, and are translated with the content (DEC-006 point 2). So its text is content, given in each language as any text is.
- **A picture the content names** lies in a field that `content` or `produced` reads (DEC-025 point 1). That field's mark names the field of its text, as a field of runs carries its words (DEC-012 point 1). So every image part that shows the picture, under every drawing, carries the same text.
- **A picture field passed on.** Where a `use` part passes a picture field on, the mark of the field the content writes holds. Where that field has none, the mark of a field it fills holds, the nearest first, as for a text's mark (point 4).
- **A picture the component chose,** by `file` or by `role`, is shown by its image part alone. That part names the field of its text, or says the picture needs none.
- **A field of plain text, read by the image alone.** The field of a picture's text is a field of text of the component, or a slot. It takes no runs, since a field of runs is shown by a text part alone (DEC-012 point 2). No text part shows it, so a reader does not meet its words twice.
- **One text in every mode.** A picture's variants, and the files a picture role takes in each mode, show one thing, so they share its text (DEC-006 point 3, DEC-025 point 4).
- **It counts for no drawing's fit,** nor does an instance's text. A drawing that shows the picture carries its text, so the text adds nothing a drawing must take. A brand's look never falls back to the top's for a text no seeing reader sees (DEC-009 point 6).
- **A picture that needs none** says so in one of two ways:
  - **The component,** on its image part, for a picture it chose, that says nothing a reader lacks. Examples are a flourish, or a logo beside the name it shows. For a picture of `role` the brand chooses the file, so the mark holds only while no brand's file shows more than the role names, such as words the component does not show (Implications).
  - **The content,** by giving the field empty text, `""`, for a picture that the words around it already say. A field left out is not this, and asks for attention (point 11).
- **What needs none is decoration.** It takes no place in the reading order (point 6).
- **A picture with no text,** not marked as needing none, still takes its place, as a picture whose text is missing. A renderer marks it so where its medium can.
- **Never required.** At format 1 no field becomes required, and no file it accepted takes a new failure (DEC-003 point 3, DEC-012 point 7). So a picture with no text only asks for attention. A component may still require its field, as it requires any.
- **An instance may take a text too,** as a diagram of boxes and lines may. A component names a field, under the same rules, as the text of the whole its instance draws, the same under every drawing. The reader's side gets that text first, then what the instance holds, in its reading order. So the text says what joins the labels, and hides nothing they hold.
- **Read before, never in place.** A renderer gives a reader's tools an instance's text before what the instance holds, and never in its stead. A form that stands in for what it holds, as a PDF's `Alt` on the element that holds them does, hides them, so a renderer writes the text in another form, which its reference page names.
- **An instance's text is never asked for.** An instance with none reads what it holds, and none is marked as needing none.
- **What a change of it breaks.** A field of a picture's or an instance's text added where there was none breaks nothing. Pointing the text at another field, or a field given up for needing none, changes what the text content fills says. So it breaks, as DEC-003 point 6 counts such a change.

### 6. A reading order follows the tree, unless a component names another

- **The default is the draw order.** A page reads in the tree's order: each component's parts in the order it writes them, and a list's entries in the content's order (DEC-005 point 5).
- **A component may name another.** Where its parts should read in another order than they lie on one another, it lists them in the order a reader takes them. A part it leaves out follows, in draw order. So a label drawn last, over its picture, may read first.
- **One order for every option and size, for now.** A switch of the order by an option or by a size, as other declarations take, is an addition left to the change that needs it.
- **Only its own parts.** A component orders its own parts, never those of a component it places, which reads in its own order where its part lies. So each component's inside stays its own (DEC-005 point 3).
- **A brand's drawing orders its own parts,** as it draws them. So switching the brand may change the order a page reads in, as it changes where each part lies. It changes no structure and no text but the pictures it chose by `file` or `role` (points 2, 4 and 5).
- **Content orders only a list,** by the order of its items, as it does for the drawing (DEC-005 point 2).
- **What takes a place:** a text, a picture, and an instance with text (point 5). A shape, a text marked `decoration`, and a picture that needs none, take none.
- **A piece's pages** read one after another, in the scene's order of its pages, each whole before the next.
- **The focus order follows it.** A link takes focus in reading order, where a keyboard moves through links (point 3).
- **No switch takes a place.** A page holds no control and no script, so nothing of a renderer's own enters its reading order (DEC-023 point 4). What a renderer draws around its pages adds no element ([visual-communication:DEC-031-html-page-backdrop] point 4).
- **What a change of it breaks.** A change of a component's reading order breaks no library, as point 2 says.

### 7. Emphasis in a PDF takes a type of the file's own, mapped to a span

- **The case.** The PDF renderer writes PDF 1.7, whose standard structure types hold `Code` and `Link`, and none for emphasis.
- **The way in.** The renderer writes `emphasis` and `strong` as structure types of the file's own, named `Em` and `Strong`. The file's role map maps each to the standard `Span`. PDF 1.7 lets a file define a type of its own so.
- **What a reader's tool gets.** A tool that reads the file's own types reads the emphasis. One that reads through the role map, as common tools do, reads a span, and loses the emphasis alone. No tool that reads the file's own types was tried for this record.
- **So the PDF holds emphasis,** in a form PDF 1.7 defines. It reaches fewer tools than the HTML page's own element does, since a tool that reads through the role map gets a span. Its declaration and its reference page say how, and that a tool may read it as a span. No loss stands for it.
- **A judgement accepted with the record.** Whether that form counts as carried, for the Feature's aim that the PDF's declared losses go, is a judgement, not a test's finding. Accepting this record accepts it.
- **PDF 2.0, later.** `Em` and `Strong` are standard types of PDF 2.0, in its own namespace of types. A move to it is a version of the renderer of its own, after a test of the tools that read it.

### 8. A picture a renderer does not draw keeps its text

- **Which pictures.** A renderer leaves out an image with no picture for the combination it draws, or one it cannot read or decode, and reports it (DEC-005 point 9). One that refuses an image does the same. An export refuses a piece whose picture file is missing or cannot be read before any renderer runs (DEC-025 point 9), so this point serves a picture the check passed that a renderer still leaves out.
- **Its text stays,** at the picture's place in the reading order, as the text of a picture not drawn. So a reader who does not see the page loses nothing they would have had. A reader who sees it sees the gap, which the loss report names.
- **In a PDF,** it is a `Figure` element whose `Alt` holds the text, with the image's frame as its bounding box, and nothing drawn in it.
- **In an HTML page,** it is the element #2740 decides for a picture's text, with nothing drawn.
- **A picture that needs none** leaves nothing.
- **A picture the engine draws nowhere** leaves nothing either: an image whose field the content leaves empty, or a picture role the brand gives no value (DEC-025 points 1 and 4). Nothing lies there to stand for.
- **The fallback.** A renderer may draw a part it cannot draw as a picture (DEC-005 point 9). That picture takes as its text the text of the instance the part draws, where its component names one. Otherwise it takes the texts of the part, in their reading order. The structure, the links and the pictures' texts inside it are lost, and the renderer reports each.

### 9. A format whose files are pictures carries no reader's side but links

- **A fact of a format.** A renderer's declaration may say of a format that its files are *pictures*: each read as one whole, whose text the document that shows it gives. It says so beside the format, as it names a format that holds modes (DEC-005 point 9).
- **The format fixes what a picture leaves out:** the words of point 1, but a run's link. A link stays out of it, since a seeing reader who opens the file alone follows one. Nothing a seeing reader sees is among them, such as a frame, a paint, a font or a text's words. So no loss of the drawing hides in the fact.
- **No loss for them.** For a format whose files are pictures, the check reports no loss of these words, and neither does the renderer.
- **A later word joins only when its change says so,** and only a word no seeing reader acts on. So a link on a picture, left to a later change (point 3), stays out of it.
- **The cost.** A file of such a format handed out alone has no document around it to give its text. A reader who does not see it gets none of its structure, and nothing reports that.
- **The first exception** to a renderer reporting what it does not draw (DEC-001 point 2). Accepting this record accepts it, with its cost.
- **The SVG renderer's two formats are pictures** (DEC-020, [visual-communication:DEC-018-copy-follows-reader-mode] point 4): the SVG format and its format of a switching file. It draws a run's link, as SVG's own link. A keyboard reader who opens such a file alone moves through its links in draw order, a small loss its reference page states.
- **The PDF and HTML renderers' formats** are not pictures, and carry each word. The change that brings a word into the scene makes both carry it, so no piece is told of a loss in between. Where one cannot yet, the check reports the loss until it does.

### 10. What this adds to format 1, and what still holds

- **Added to the format, each optional:**
  - a run structure for each word of a field's run styles
  - the key `link` on a run
  - a field's mark of its text's structure, a caption's with the field it captions
  - a list field's mark that it reads as a list or as no list
  - a picture field's mark that names the field of its text, an image part's field of text or its mark that it needs none, and a component's field of its instance's text
  - a component's reading order of its parts
- **Added to the seam,** whose version is apart from the format's (DEC-005 point 8):
  - in the scene, each of these, with a heading's level and each list
  - in a renderer's declaration, each word it spells, and the fact that a format's files are pictures
- **The format number stays 1.** Each is an addition that every file written before still meets (DEC-003 points 1 and 3). Format 1's schemas know none of these keys, so no file they accepted holds one, and no field becomes required.
- **No new failure on a file format 1 accepted.** Each finding that fails reads a key format 1 refused.
- **New attention, on files format 1 accepted.** A picture with no field for its text asks for attention, once in the version of each component that shows one today. This is less than DEC-012 point 7 promised for runs, under which no finding arose at all. It refuses nothing (DEC-003 point 3).
- **The seam's version rises in the first change.** A renderer reads what it did not read before, so the seam rises in the change of a text's structure and a reading order (DEC-005 point 8). That change sets the scene's shape for every word of point 1. So the changes of a run's link and structure, and of a picture's text, fill it with no rise of their own. A later change that must reshape it raises the seam again.
- **A renderer's own version** rises in each change that alters its output (DEC-005 point 9). The PDF and HTML renderers' rise with each of the three changes, the first included, since every list field then reads as a list. The SVG renderer's rises only with the change of a run's link.

### 11. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct (DEC-002 point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it.

- **Where each lies.** A finding on what a component declares lies in the component's version, and one on a brand's drawing in the brand's. A finding on a run lies in the content file, at the run (DEC-012 point 8). A finding on what a piece draws lies at the piece.
- **Fails validation:**
  - in a component: a run structure that is not `emphasis`, `strong` or `code`, or one for a word its field does not declare
  - in a component: a text's mark that is not `heading`, `caption`, `paragraph` or `decoration`, or one anywhere but on one of its fields of text or on a slot; a caption that names no other field or slot of the component, or one another caption names
  - in a component: a mark that a field reads as a list or as no list, on a field or slot that holds no list
  - in a component or a brand's drawing: a picture's or an instance's text that names no field of text, a field of runs, or a field a text part shows
  - in a component or a brand's drawing: an image part of `file` or `role` that both names a field for its text and says it needs none; or a mark that a picture needs none on an image of `content` or `produced`
  - in a component or a brand's drawing: a reading order that names a part it does not hold, or one part twice
  - in content: a `link` that is no text, or an address point 3 refuses
- **Asks for attention, never failing:**
  - in a component: a picture with no field for its text, neither on its field of `content` or `produced`, nor on its image part of `file` or `role`, which does not say it needs none. It lies once, in the component's version, and names its owner.
  - in a component that names no reading order: a field it marks `heading` whose text part it draws after another of its text parts (point 4).
  - at a piece that exports a format whose files are not pictures: a picture whose text field the content leaves out. It names the field and the content's author.
  - at a piece: a run that holds a link and is drawn in the same role and paint as a run of its text that holds none. It names the run. The content's author may give it another word, or the component's owner declare one. A text whose every run is one link has nothing to compare, and is not judged.
- **What a brand's drawing adds** to the findings on drawings: a picture's text named by an image part of `file` or `role`, a reading order, and a heading drawn after another text, each judged as in a component (DEC-009 point 9).

## Rationale

**Why the format fixes the words.** A word reaches a reader only where a renderer spells it, and every renderer is the capability's code (DEC-005 point 12). Words a library declared would each need a renderer that knows them. The foundations would fix them at a version apart from the renderers' (DEC-001 point 7). The format already fixes what every renderer reads, such as the primitives and their properties (DEC-005 point 5).

**Why the component gives each run style its structure.** A run's word already says what the run is, such as a prompt or a strong phrase (DEC-012, Rationale). The component decides how the word looks (DEC-001 point 6), so it decides with it what the word is to a reader's tools. Content names only words its component declares (DEC-001 point 3). A structure named on each run would be a second choice content makes, which no component declared. And every run already written gains its structure when its component's library declares one, with no content changed.

**Why `emphasis`, `strong` and `code`.** They are the spans a reader's tools tell apart in both media the Feature serves: HTML's `em`, `strong` and `code`, and PDF 2.0's `Em` and `Strong` beside PDF 1.7's `Code`. Stress and importance differ in both. Other spans, such as a quotation or a term defined, are additions when a slice needs them.

**Why a change of structure breaks no library.** The record of change over time counts as breaking a change of a name a piece uses, or of what it means (DEC-003 point 6). A word means what content says by choosing it, and that stays. Its look and its structure are the component's way of showing it, to the eye and to a reader's tools. A change of a word's role or paint is not breaking (DEC-012 point 6), and a change of its structure is the same kind. Changing the first word breaks for another reason: every run that names no word becomes another word (DEC-012 point 6). A field of a picture's text, or of a caption, is another matter: content fills it to say something of another field, so pointing it elsewhere changes what it says (points 4 and 5).

**Why `link`, absolute, of three schemes.** An exported file travels alone, so an address relative to it leads nowhere. A link that runs a script or reads a local file is no place a reader goes, and a handed-out file should carry no password. Web and mail addresses are what a deck or a page links to. A later scheme is an addition.

**Why runs with one address are one link, and a link never splits.** A link across a strong phrase, or across a line's break, is still one place to go. The engine breaks lines across runs (DEC-012 point 4), so a link must cross them too. Both media need spans that nest. A split link would read as two links to one place, and a split emphasis reads as before.

**Why a link's look is its word's.** The renderer adds nothing to a page (DEC-001 point 2), and a link drawn in a look of the format's own would be a look no brand gives. A word the component declares keeps the look the brand's. The check compares what is drawn, since two words may share one role and one paint (DEC-012 point 2).

**Why a mark on the field.** A slide's title is a heading under every brand, because of what the field is, not how a drawing draws it. A key on a text part would let each drawing say otherwise, though content is written against the top (DEC-009 point 5). A mark on the component as a whole would not say which of its texts is the heading. A typography role is a look a brand gives a value, and names no level.

**Why the field the content writes decides, then the field it fills, but not on a top.** The component that declares the field the content writes knows what that text is, such as a slide's title. A block it passes the field to knows only its own kind of text. So the outer mark holds, and the block's mark serves where the outer one says nothing. A top's field is drawn by each brand's drawing, which may pass it to another block, so only the top's own mark holds there.

**Why a computed level, within the page.** A level written in a component would hold only where that component lies. A card whose head was level 2 inside a slide would be level 2 on a page of its own, and a project reuses small parts most (DEC-001, Context). The engine knows what holds each instance, so it computes the level, as it computes a frame. Counting only a heading drawn with text keeps a level from being skipped, which a reader's tools report as a fault. Each page is read on its own, so its headings start at 1.

**Why each field reads once.** A field shown twice, such as a title in a page's footer, is one text to a reader. Read twice, it is noise, and a duplicate heading misleads.

**Why a list field reads as a list, unless marked, and why the mark lies on the field.** A list holds items of one kind in the content's order, which is what a list is to a reader, such as steps, links, cards or a form's fields. A page's sections or a set of panels need not read as one, so a component marks those, and no other component changes. The mark lies on the field, as a text's does, for the same reason: a brand's drawing repeats a top's field with parts of its own, so a mark on a part would let switching the brand change what is a list.

**Why a table later.** A table is drawn as a repeat of rows, each repeating over cells. A header cell heads the cells of its column or its row, across two repeats, which no word here does: each says what one text, list or picture is. Its words need a design of their own, with how a component declares them. A list of lists still reads in order, so a reader loses which header heads a cell, and nothing else.

**Why a picture's text is tied to the picture.** A picture the content names lies in a field, which every drawing of a top takes. Its text tied to that field reads the same under every drawing, as a field's words do. Named by each image part, two drawings could give one picture two texts. A reserved key, such as `alt`, would refuse a field of that name that format 1 accepts (DEC-002 point 4). A key on a picture's name would turn every picture field into a mapping.

**Why a picture's text counts for no drawing's fit.** A drawing that fails to fit is replaced, whole, by the top's own (DEC-009 point 6). An author who adds a text no seeing reader sees should not change what every seeing reader sees. Tied to the picture's field, the text reaches every drawing that shows the picture anyway.

**Why empty text says a picture needs none, and the component only for its own.** HTML's empty `alt` says the same, so an author who knows the web knows it. A field left out stays a question, so a forgotten text still asks for attention. A component knows whether a picture it chose is decoration, such as a flourish. It cannot know that of a picture the content chose, such as a chart.

**Why the finding at a piece only where a format carries pictures' texts.** A piece drawn only as pictures gives no picture's text to any reader, so asking for one there is noise no one need answer.

**Why an instance's text comes first, and hides nothing.** A diagram's labels, read one after another, do not say which joins which. A text read first says so, and the labels then read in their order, with their links and headings. A text read in their place would hide what a card in the diagram holds.

**Why the draw order by default.** It is fixed and known: the component writes its parts in order, and the content orders its items. A component writes its parts mostly in the order a reader takes them, as a title before its body. An order computed from where elements lie on a page would misread two columns, and change with a page's size.

**Why a component orders only its own parts, and a drawing its own.** A component's inside is private, so its library may change it freely (DEC-005 point 3). An order that reached into a placed component would break when that component changed. A brand's drawing has parts of its own, which no other drawing shares, so only it can order them. A reading order follows where parts lie, which is the drawing's: a drawing that sets a subtitle above its title reads it first, as a seeing reader does. So switching the brand may change the order, as it changes where each part lies, and changes no structure.

**Why emphasis in a PDF takes a type of its own.** It keeps the file at PDF 1.7, and holds the emphasis in a form that version defines. A tool that reads only the standard types reads a span, so the emphasis reaches fewer tools than the HTML page's does. A move to PDF 2.0 carries it as a standard type, but the renderer would have to meet PDF 2.0 throughout, and no tool that reads it was tried, for two words.

**Why a picture not drawn keeps its text.** A reader who does not see the page should not lose a text that a fault of the drawing took. The loss report names the gap for whoever can mend it (DEC-005 point 9).

**Why a fact of a format, and the format's list of words.** A picture has no reader's side inside it: the page that shows it gives its text (DEC-018 point 6). The SVG renderer draws the previews of every piece and the figures of documentation pages. Without the fact, every piece would be told of a loss on every list and heading. A per-property state that each renderer wrote would hold its bound only by what each declaration said. The format's own list holds it by construction: no property a seeing reader sees, and no link, can take it.

### Alternatives considered

- **Words each library declares, or the foundations.** Rejected. No renderer would know them, and the foundations would fix them apart from the renderers.
- **A run that names its structure, as `structure: emphasis`.** Rejected. Content would make a choice its component did not declare.
- **`emphasis` and `code` alone, `strong` read as emphasis.** Rejected. Both media tell stress and importance apart.
- **A change of a word's structure as breaking.** Rejected. What content says by the word stays, and a change of how a word shows does not break (DEC-012 point 6).
- **An address relative to the file, or to the repository.** Rejected. An exported file travels alone.
- **A link given its look by the format, such as an underline.** Rejected. The renderer would add a look no brand gives.
- **A heading declared by a key on its text part.** Rejected. Each drawing of a layout could declare it otherwise.
- **A heading read from its typography role.** Rejected. A role is a look, and names no level.
- **A heading level the component declares.** Rejected. A reused block would keep its level wherever it lies.
- **A caption of its whole instance.** Rejected. On a page drawn in a layout the instance is the page, so a caption would caption the slide, its title included.
- **A caption that names the part it captions.** Rejected. A brand's drawing has parts of its own, so the part would be undefined under it.
- **A list field that reads as a list only where it is marked.** Rejected. Most lists hold items a reader takes as a list, so most components would need the mark.
- **The mark that a list reads as no list, on the `repeat` part.** Rejected. A brand's drawing repeats a top's field with parts of its own, so switching the brand could change what is a list.
- **A table's words in this record.** Left to a change of its own. A header cell reaches across two repeats, which needs a design of its own.
- **A reserved key `alt` on every mapping that places a component.** Rejected. It would refuse a field of that name that format 1 accepts (DEC-002 point 4, DEC-003 point 3).
- **A picture's text in its picture file's name, as `{file: team.jpg, text: …}`.** Rejected. Every picture field would take a mapping, and its text would stay apart from the component that knows the picture.
- **A picture's text named by each image part, whatever the picture's source.** Rejected. Two drawings of one layout could give one picture two texts.
- **A picture's text that counts for a drawing's fit.** Rejected. A text no seeing reader sees would swap a brand's drawing for the top's own.
- **A picture role's text that the brand gives.** Left to later. A brand holds no language, and a logo's text may need one. Until then a component can only mark such a picture as needing none, or name a field for its text.
- **A picture's text required.** Rejected for format 1. A field that becomes required refuses files format 1 accepted (DEC-003 point 3).
- **An instance's text read in place of what it holds.** Rejected. It would hide the texts, links and headings a diagram's cards hold.
- **A reading order computed from where elements lie.** Rejected. It misreads columns, and changes with a page's size.
- **A reading order that reaches into placed components.** Rejected. It would break when a placed component changed its private parts.
- **A reading order of the top's fields, which every drawing takes, as it takes their marks.** Rejected. A drawing sets where the fields lie, so a reader who does not see would take them in another order than a seeing reader does. An order of fields would also reach into the blocks a drawing passes them to.
- **PDF 2.0, with `Em` and `Strong` as standard types.** Rejected for now. The renderer would have to meet PDF 2.0 throughout, untried with the tools that read it, for two words.
- **Emphasis in a PDF reported as `approximated`.** Rejected. The file holds the emphasis in a form PDF 1.7 defines, which a tool that reads the file's own types reads (point 7).
- **A picture not drawn that takes its text out too.** Rejected. A reader who does not see the page would lose a text that a fault of the drawing took.
- **Losses of the reader's side reported for the formats a piece exports, and never for its previews.** Rejected. A figure handed out or shown as SVG is a picture whose text the document gives, so each of its lists and headings would be a loss no one could mend.
- **A state each renderer declares for each property, "not for its medium".** Rejected. Its bound would rest on each declaration, not on the format.
- **SVG's links counted among what a picture leaves out.** Rejected. A seeing reader who opens the file alone follows a link, so a loss would hide.

## Implications

- **The change of a text's structure and a reading order** sets the scene's whole shape of the reader's side, and raises the seam (point 10). It builds a field's marks, a heading's computed level, each list and a list field's mark, a component's reading order, and the fact that a format's files are pictures. It sets how a component writes them, how the scene holds them, and how a renderer declares each word it spells. The before-and-after comes to name each difference of the reader's side (point 2). The PDF and HTML renderers carry each word it brings in, and the SVG renderer's two formats say their files are pictures.
- **The change of a run's link and structure** builds the key `link`, the check of its address, and a run structure for each word of a field's run styles. It names the standard an address is read by, and code that reads it on the terms the capability's code takes ([visual-communication:DEC-002-files-and-validation] point 8). The SVG renderer comes to draw links, and its version rises.
- **The change of a picture's text** builds a picture field's mark that names its text, an image part's field of text and its mark that it needs none, an instance's text, and a picture not drawn that keeps its text (point 8).
- **The shipped libraries' components** come to declare their marks, their words' structures, their pictures' texts and their reading orders, each in a release of its library ([visual-communication:DEC-013-shipped-library-releases]). What each declares is its component's design, not this record's. A release that gives every picture a field for its text leaves no attention of point 11 standing on its library.
- **The PDF renderer** becomes a tagged PDF in these changes. It writes each structure as its reference page says, and emphasis as point 7 says. Its declaration comes to name each word it spells. Its `not-carried`, a list no check reads, loses each item as it comes to carry it, and goes when it is empty. A table reads as lists then, so no loss stands for one.
- **The HTML renderer** spells the reader's side as #2740's record decides, and its `not-carried` goes the same way.
- **#2740's body** comes to say that its test's table reads as a list of lists, until the change of a table's words.
- **The Feature's criterion on links** is met by a run's link.
- **The capability's pages,** `components.md`, `files.md`, `checks.md` and `outputs.md`, describe each with the change that builds it. No page changes its text here.
- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). They wait for that acceptance.
  - **DEC-001, point 2, "What a renderer cannot draw".** It comes to add that a renderer may say a format's files are pictures. Such a file carries none of the reader's side the format lists, links aside, and no loss is reported for it. This is the one exception to a renderer reporting what it does not draw.
  - **DEC-001, point 3, "Runs".** It comes to add that a run may also hold a link, which may differ between languages, as its text does.
  - **DEC-001, point 5, "Switching the brand changes how a piece looks".** It comes to add that switching the brand may also change the order a page reads in, as it changes where each part lies, and the text of a picture the brand chose. It changes no structure.
  - **DEC-002, point 3, "Strict".** "A run's known keys are `text`, `style` and `concept`" comes to name `link` too.
  - **DEC-002, point 4, "Reserved keys".** "It fixes `text`, `style` and `concept` on a run" comes to read `text`, `style`, `concept` and `link`.
  - **DEC-003, point 6, "What breaks".** It comes to add that a change of the structure a component gives a word or a field, or of its reading order, does not break, as a change of look does not. Pointing a picture's, an instance's or a caption's text at another field, or giving a picture's field up for needing none, breaks.
  - **DEC-003, point 7, "The promise is checked".** It comes to add that the comparison also states, as a fact, each change of a stable component's run structures, text marks, fields of a picture's or an instance's text, and reading order.
  - **DEC-005, point 5, "Primitives at the leaves".** A text's bullet comes to add that each run holds its structure where its word names one, and that a text holds its mark, a heading with its level. "Draw order is the tree's order" comes to add that the reading order follows it, unless a component names another. The bullet on documents and PDF files comes to say that the scene holds the reader's side in words that name no medium, which each renderer spells. Those are each run's structure and link, each text's structure, each list, each picture's or instance's text, and each reading order a component names. Tables stay promised, and come with a later change.
  - **DEC-005, point 9, "Each declares what it supports".** It comes to add that a renderer declares each word of the reader's side it spells, as it declares each primitive and property, and names each of its formats whose files are pictures. "Losses are known before a plugin runs" comes to add that a format whose files are pictures loses none of the reader's side the format lists. "One fallback for renderers" comes to add that the picture takes the text of the instance the part draws, or else the texts of the part in their reading order.
  - **DEC-006, point 2, "None of the piece's words".** It comes to add that a picture's text is content too, in a field tied to the picture.
  - **DEC-009, point 5, "A drawing is written against the top".** It comes to add that a drawing takes the structure and the marks the top declares for each word and each field, a picture's text with its field, and declares none of its own but the texts of the pictures it chose by `file` or `role`, and the reading order of its own parts. **Point 6, "A drawing that does not fit"** comes to add that a run's structure, a run's link, a picture's text and an instance's text count for no drawing's fit. **Point 9** comes to add, to the findings that fail validation, a drawing's picture's text named by an image part of `file` or `role`, and its reading order, and to those that ask for attention, a heading drawn after another text, each judged as in a component (point 11).
  - **DEC-012, its summary.** "a mapping of its `text`, its `style` and perhaps its `concept`" comes to add "or its `link`". **Point 1**, its bullet "A run" that names a run's keys, and "Keys the format fixes": a run may also hold `link`, and the format fixes it with the other three. **Point 2, "Only how the run is set"**: a run's word also chooses the run's structure, which its field declares for the word. **Point 8**'s finding on a run with another key comes to name `link` among the keys it allows. **Implications, "Left to later changes"**: the bullets on a run's link and on a run's structure come to cite this record.
  - **DEC-020, point 10, "What a reader who does not see the page gets".** Its citation of #2739 comes to cite this record. Its item "what a shape or a picture says" comes to read: how the page spells a picture's text. This record decides that a shape is decoration and a picture's text is content. Its item "a reading order that differs from the draw order" comes to read: how the page spells a reading order a component names.
  - **DEC-019, point 5, "The before-and-after stays a command".** "prints each page that differs" comes to add: and names each structure, mark, picture's or instance's text and reading order that differs between its two scenes.
  - **DEC-025, point 1, "`content: <field>`".** It comes to add that the field's mark may name the field of the picture's text. **Point 11, "A picture's text"** comes to cite this record in place of the issue.
- **Read against, and left as they stand:** DEC-003 point 3, DEC-005 points 3 and 8, [visual-communication:DEC-010-list-item-fields], [visual-communication:DEC-011-tie-ends], DEC-018 point 6, DEC-023 point 4 and DEC-031 point 4.
- **Left to later changes:**
  - a table's words, for its rows, its cells and its header cells
  - whether a list reads as ordered, where its pattern numbers its items
  - a component's own fields that head at two levels
  - a reading order that switches by an option or a size
  - a link on a picture or on a whole instance, and a link to another page of the same piece
  - a line under or through a text, which a brand would give a typography role
  - a page's regions, such as its header, its navigation, its main part and its footer, which a reader's tools move between
  - a run's language, where a phrase is in another language than its piece, which a reader's tools pronounce by
  - whether a picture's text says what the picture shows, which a graphic rule or the reviewer would judge
  - a picture role's text that the brand gives
  - a file's own title, which a reader's tools announce first
  - how the agent that translates carries a picture's text and a run's link
- **Revisit this record** if #2740's test finds a word a reader's tools cannot get from the HTML page, or if a screen reader misreads the PDF's own types or a figure with nothing drawn. Revisit it too if a computed level misleads in a real piece, or if the PDF renderer moves to PDF 2.0. A renderer whose medium is no picture yet holds no reader's side, such as a whiteboard service's, revisits point 9.
