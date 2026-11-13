---
id: DEC-040
title: An HTML page tells a reader's tools what each text is through HTML's own elements, and draws none of it
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a reader who does not see an HTML page gets each text with what it is from the elements the page already holds: a heading's text is a heading, a list's entries are a list. Each word lies once, but a link or a heading whose line broke where no space lies, as after a hyphen, is also named whole. None of it adds to the drawing. The page is written in the order a reader takes it, a picture's text is an element at the picture's place, and a copy gives the words as written. Find across a line break fails in Chrome and Firefox, which this record accepts for now. For example, a link the engine broke after "decisions never" takes one press of Tab, and a reader's tools get one link named "decisions never drift to match the code".

## Context

[visual-communication:DEC-020-html-page-drawing] chose a page of real HTML text over SVG shapes, so each text lies once. Its point 10 leaves to [project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740) how those elements carry the words [visual-communication:DEC-033-structure-for-readers] fixes, emphasis or a link across a line break among them. It also leaves how the page spells a reading order a component names, selection and find-in-page over lines placed apart, a keyboard reader, and a picture's text. DEC-033 point 3 has a medium that places a text's lines apart spell a link across them as its own record decides. [visual-communication:DEC-015-viewing-step-and-reviewer] point 3 leaves the viewing step to say what counts as dropped.

Terms:
- A *reader's tools* are as DEC-033 has them: a screen reader and its like, reading a page's *accessibility tree*, the tree a browser builds from the file for them.
- A line's *break character* is what the engine used up where it broke a paragraph's line: the spaces where it broke at a space; nothing where it broke after a hyphen, after a slash, between characters that take no space, or inside a word; and a line feed where a paragraph ends.

### What the test showed

The test took the showcase deck of the repository the capability is authored in, as `pkit visual look` drew its English page file through the HTML renderer, and added a page of its own. Structure was added to that file by hand: headings of two levels, a list from a `repeat` part, a table drawn as a `repeat` over rows read as a list of lists (DEC-033 point 4), emphasis across a line break, a link across two lines, a link in a text marked decoration, a block of code, two pictures, an instance's text, and a page whose reading order differs from its draw order. The added page broke lines after a hyphen, after a slash in an address and in a block of code, and between Japanese characters, and held a caption. Its code is thrown away, and the pages and the last run of each read, in the test's `results` folder, are the evidence of this record's pull request.

- **Chrome's accessibility tree,** read through its protocol. The renderer's file as it stands reads as plain text, and each layer as a picture with no name. The form point 1 decides reads each heading with its level, each list with its entries and depth, each run's structure, the link across two lines as one link named by all its words, the decoration's link alone, a picture by its text, a picture with no text as one, the instance's text as a figure's name, and the page in its reading order. A caption's figure held the picture and its caption, unnamed, as Chrome holds a plain HTML figure (`probe-figure.txt`). An instance's figure that held a caption kept the instance's text as its name, where a caption's figure around it read unnamed. An entry element hidden from a reader's tools was left out of its list (`log-r3.txt`).
- **A name across a line break.** A link broken after a slash was named whole through `aria-label`, and with a space at the break through `aria-labelledby`. A heading broken after a hyphen was named with a space at the break whatever its break character, and whole through `aria-label`. One broken at a space was named with one space. Chrome puts a space both at each line placed alone and at each line's strut, an inline block. With the struts hidden from a reader's tools, each page drew as before at scales 1 and 1.225 in all three engines, and copied and found as before, and a heading's name lost its space only where its lines lay in one row. Each heading named from its lines ends with a space, from the line feed that ends its text (`log-r3.txt`).
- **What is drawn.** No line moved. The images were compared with the renderer's file whose spans are split where the test's structure starts, since a structure or a link starts at a run's edge, where the renderer already starts a span (DEC-033 points 2 and 3). Outside the two pictures the test's form adds, no pixel changed in Chrome, Firefox or WebKit, in light and dark, at scale 1, nor in Firefox and WebKit at the step's 1.225 (`log-pixels.txt`). In Chrome at 1.225 the ink of each line that holds a link or an emphasis moved down by under a device pixel, its layout not at all (`probe-shift.txt`). A picture's own element drew nothing, and at scale 1 neither did a page drawn in its draw order by z-index.
- **Selection and copy.** In the renderer's file, Chrome and WebKit ran two words together at each line break, and two lines of code together. With the break characters, all three engines gave each text as written, two spaces where the engine used up two, an address and a command whole, and a line break between paragraphs and between texts. A space at every break, as a first draft had it, gave "force- push", broke the code block's command at "github.com/ aleskalfas", and put a space between Japanese characters. A selection across a page's parts followed its reading order. No picture's text or instance's text was selected. Firefox put the `alt` of an `img` that draws nothing into a selection and into its copy (`log-r3.txt`).
- **Find,** read through `window.find` and Chrome's text fragments, the form a link to a phrase takes. A phrase within a line was found once in each engine, across spans and emphasis. A phrase across a line break was never found in Chrome or Firefox, with or without the break character. WebKit found it with the break character. In the deck, 3 % of two-word phrases and 7 % of three-word phrases cross a line break, 10 % and 20 % in a text that wraps (`measure.txt`). In lines kept in one flow, apart by a forced break or a line feed, Chrome found no phrase across a line, Firefox found each across a line feed, and WebKit lost what it found in the deck's form.
- **A text's lines kept in one row,** each moved into place by a relative offset measured in the browser, the form project-kit#3118 weighs (`log-row.txt`). Each engine found every phrase across lines, and so did Chrome's text fragment. The row drew as the deck in Chrome and Firefox at scale 1, and in Firefox at 1.225. Chrome at 1.225 moved ink on every page, up to 32 626 px of one at a worst difference of 237, though its struts lay within 0.013 CSS px of the deck's. WebKit moved ink on one page at scale 1 and on two at 1.225, up to 391 px at a worst difference of 119.
- **The keyboard.** The link across two lines took one stop of Tab. Two plain links took two. WebKit's Tab reached no link, as Safari's own setting has it, and Option and Tab reached each once. With a rule of the file, the focus showed on both lines in each engine, as a box in Chrome and WebKit and a line under the words in Firefox. A later opaque shape hid the focus of a link under it. Raising the focused link showed it on a page that carries no z-index, and not on one whose orders differ. Raising the text that holds it showed it on both (`log-focus-flow.txt`), on the second only by a rule marked `!important`: without it, as in the first run (`log.txt`), the element's own z-index won, and nothing was raised there (`log-r3.txt`). Under the flag that forces colours, Chrome gave links the forced palette's link colour.
- **The viewing step's own browser half,** at 1.225, in light, dark and both forced palettes, named nothing on the form (`step-r2.txt`). It read the words it expects from the same file, so it shows only that its four reads do not break on the new elements.

**Reached:** Google Chrome 157, and Firefox 157 and WebKit 27.2 as Playwright builds them, on one Mac, at device scales 1 and 1.225. **Not reached:** Firefox's and WebKit's accessibility trees, which Playwright does not read; Safari and Firefox as shipped; every browser's find bar, Chrome's among them; a browser without CSS's `:has()`; a heading past level six, a picture not drawn, a page in Czech, right-to-left text; a screen reader on a touch screen, where touching a link's later line finds a part hidden from a reader's tools; NVDA and JAWS; Windows and Linux.

**A person's reading with VoiceOver:** pending. This record is not accepted before it.

## Decision

**An HTML page file spells the reader's side in HTML's own elements, on the elements its texts already are, adds an element only for what no text holds, and draws none of it.**

### 1. Each word takes the element HTML has for it

- **HTML's own element** spells each word of DEC-033 point 1: a text's mark, a list and its entries, a run's structure and a run's link. An ARIA role spells a word only where HTML has no element for it, or where its element alone does not reach a reader's tools. So each list also carries `role="list"`, since WebKit, by its known behaviour, reads a list whose marker is taken away (point 2) as no list.
- **On what is already there.** A text's own element takes its mark, and each of its lines is a phrasing element, so a paragraph's element holds them. Each span sits inside the element of its run's structure, and the element of a list, or of an instance's text, holds the elements of what it holds. So each text still lies once (DEC-020 point 1).
- **A heading past level six** is written as the sixth, and reported `approximated` (DEC-033 point 4).
- **A caption** is a `figcaption`, which one `figure` holds with the element of what it captions (DEC-033 point 4):
  - **at the place of whichever comes first** in the reading order, so a part between them follows the figure, and point 5 counts that move as it counts any element's place;
  - **over an instance with an instance's text,** in that instance's own `figure`, whose name stays the instance's text (point 7);
  - **over a picture that needs no text,** alone in its `figure`, since that picture takes no element (point 7).
- **An entry left out of its list,** having nothing to read (DEC-033 point 4), keeps what it draws in an entry element of its own, hidden from a reader's tools, so a list's element holds entry elements alone and a reader counts only its entries.
- **A run's structure across a line break** splits at the line's edge, one element on each line, each read with its structure. A link stays one link to a reader (point 3).

### 2. None of it is drawn

- **The elements draw nothing of their own.** The file sets back each look a browser gives them, such as a heading's size, a link's colour and underline, a list's marker or a paragraph's margin, so the page draws the scene alone (DEC-001 point 2, DEC-033 point 3). At a device scale other than 1, Chrome may move the ink of a line that holds one by under a device pixel, as it rounds the element's box.
- **What stays the reader's:** the focus the browser shows (point 4), and the colours a reader forces, a link's among them.
- **Hidden from a reader's tools:** each layer, what the file defines once for its layers, such as its arrowheads, and a text marked decoration, all but its links (DEC-033 points 3 and 6).

### 3. A link across a line break is one link

- **One link to a reader's tools and to the keyboard.** Its first part is the link they reach, named by the words of all its parts. Each later part follows it under the pointer alone, hidden from a reader's tools and out of the keyboard's order.
- **Named by its parts' own words,** through `aria-labelledby`, so no word lies twice. Where two of its parts meet at a break that used up no space, it is named instead by its words whole in `aria-label`, since `aria-labelledby` joins parts with a space.
- **Its focus shows on every part.**

### 4. A keyboard reader sees where the focus lies

- **Links take focus in the document's order,** which is the reading order (point 5). The file sets no order of its own, and adds no focus stop (DEC-023 point 4).
- **The browser's own sign of focus** stays on every link.
- **The text that holds a focused link draws over every shape** while the link has focus, so a later shape never hides where the focus lies. Its rule is marked `!important`, so it wins over the z-index point 5 writes into each element's own style.
- **Both rest on CSS's `:has()`,** the focus on every part (point 3) and the raise. A browser without it shows the focus on a link's first part alone, and raises nothing.

### 5. The document's order is the reading order

- **A page's elements follow its reading order** (DEC-033 point 6), so a reader's tools, the keyboard and a selection take them in it.
- **Each element lies where its part falls in that order,** which a component's list and the draw order give every part, one that takes no place in the reading order included, such as a text marked decoration (DEC-033 point 6). So a decoration's links read at that place (DEC-033 point 3). A layer lies where its first shape falls.
- **A list's entries lie together,** since the part that repeats over its field takes one place in its component's order. So a list's element holds entry elements alone (point 1).
- **Where the document's order of a page's elements, its layers included, differs from their draw order,** each element of that page carries its place in the draw order by z-index, within the page, so the page draws as before (DEC-020 point 3). A page whose every element lies in its draw order carries none.

### 6. A line ends with what the engine used up at its break

- **Each line ends with its break character,** taking no width. So a copy gives a text's words as written, and two texts apart.
- **A heading whose lines meet at a break that used up no space** is named by its words whole in `aria-label`, as a link is (point 3), since Chrome names a heading from its lines with a space at each line placed alone. Its words then lie twice in the file.
- **What lines placed alone cost** (DEC-020 point 2): Chrome's and Firefox's find meets no phrase across a line break, and every other heading's name in Chrome ends with a space, from the line feed that ends its text, which a listener does not hear and a tool that compares names does. The renderer's reference page states both, and no check reports them.

### 7. A picture's text is an element at the picture's frame

- **A picture's text is a picture to a reader's tools,** an element of its own at the picture's frame, in the picture's place in the reading order, named by that text. The picture stays in its layer (DEC-020 point 1).
- **A picture with no text** takes the same element with no name, so a reader's tools show that its text is missing (DEC-033 point 5). A picture that needs none takes no element.
- **A picture not drawn** keeps its element and its text, over nothing drawn (DEC-033 point 8).
- **An instance's text names a `figure`** that holds the elements of what the instance holds, so a reader's tools give it before them (DEC-033 point 5).
- **Neither text is drawn, selected or found.** Each lies only in what the file tells a reader's tools.

### 8. The viewing step reports none of it dropped

- **Its four reads stay on spans** (DEC-020 point 6). What only a reader's tools get, such as a picture's text, a link's name or a break character, is no span and draws nothing, so the step never reports it dropped (DEC-015 point 3). Putting the document in reading order breaks no read, since the words read matches each text by its trace id, and the ink read both lists the spans and marks the one it draws alone by their order in the document.
- **A screen reader stays a person's** (DEC-020 point 5).

## Rationale

**Point 1, HTML's own elements.** An element of HTML carries its meaning to a reader's tools and to other tools that read a page's elements, such as a reader view. A role tells a reader's tools alone, and restates what an element would say, so it is kept for a word no element carries to them, as a list without its marker in WebKit. Putting the meaning on the elements the texts already are keeps DEC-020's ground: each text lies once, so a reader's tools, a selection and a find meet it once. A line that were no phrasing element would close the paragraph around it, as an HTML parser closes one. A run's structure split at a line reads as before, as DEC-033 point 3 foresaw, since a reader's tools read emphasis from each part. A `figure` is HTML's element for a whole, captioned or named, such as a diagram, so a captioned instance is one figure. A list's element holds only entries in HTML, so a left-out entry's shapes take an entry no reader counts.

**Point 2, nothing drawn.** A renderer draws the scene and adds no look (DEC-001 point 2). The test showed the reset elements leave each line where it was, and what Chrome moves at another scale is its rounding of a box, not a look. The focus and forced colours belong to the reader's own settings, which a renderer leaves alone. A layer read as a picture with no name is noise to a screen reader, and so is a decoration's text, which DEC-033 keeps out of the reading order but for its links.

**Point 3, one link.** DEC-033 point 3 keeps a link across runs one link, since two would read as two places. The lines are placed apart, so no one element can hold the link's words alone. Naming the first part by its parts' words keeps the words once, where a copy in an attribute would hold them twice. Where a break used up no space, as in an address broken after a slash, the space that joins the parts would split a word, so there a copy is the lesser loss. The pointer still follows the link from any part, as a seeing reader expects.

**Point 4, the focus.** A keyboard reader who cannot see the focus is lost. DEC-020 lets a later shape lie over a text, and the test showed such a shape hides the focus too. A text that carries a z-index keeps its link's own raise inside it, so the whole text is raised, its other lines with it, and only while its link has focus, the reader's own state. An element's own style wins over the file's rules but one marked `!important`. Every browser the test reached holds `:has()`.

**Point 5, the reading order.** A reader's tools, the keyboard and a selection all follow the document's order, so one order serves all three. DEC-020's own test drew the same image with z-index, and so did this test. Placing every element by DEC-033's order keeps a decoration's links where that record reads them, so a component that draws a footer first and wants its links read last names its order. Comparing every element, layers included, keeps a ground under the texts it backs where the reading order moves its layer after them, which comparing only what takes a place in that order would not. A page whose elements lie in their draw order keeps its file as it is.

**Point 6, copying and find.** A copy that runs two words together, or splits one, breaks the text a reader takes elsewhere, and characters that take no width mend it at no cost to the drawing. The line feed that ends a text keeps two texts apart in a copy, which is worth more than a space at the end of a heading's name. A reader's tools list a page by its headings' names, so a name that splits a word is worth a copy of the words, as a link's is. Find in Chrome and Firefox stops at each line placed alone, about one two-word phrase in ten in a text that wraps, and a link to such a phrase finds nothing. Lines kept in one row and each moved into place were found, but their offsets rest on the browser's widths of the lines before, which a renderer does not know, so whether they can keep a line where DEC-020 point 2 holds it is a follow-up's question. A phrase is found within each of its lines, and a reader's tools read it whole, so the loss is accepted for now, and stated once rather than on every text that wraps, though a reader who finds nothing is not told why.

**Point 7, a picture's text.** A layer holds pictures and shapes in draw order, hidden whole, so a picture's text cannot lie there in reading order. An element of its own at the picture's frame stands in the reading order, and a reader's tools that show where they are show the picture's place. A picture with no name is how a reader's tools learn a text is missing.

**Point 8, the step.** A reader's text draws nothing by design, so a read of ink would report each one. Whether the step reads the reader's side, and against what, waits on a comparison and a timing no test has made.

### Alternatives considered

- **A copy of each text for a reader's tools, in either of #2740's two forms that hold one:** DEC-020's elements hold each text once, and a find meets a copy twice.
- **ARIA roles on the elements the renderer writes today:** a role reaches a reader's tools alone, where an element of HTML reaches other tools too.
- **A group with a role for an instance's text:** a role where HTML has `figure`.
- **A captioned instance as a figure inside the caption's figure:** the outer one reads unnamed, so a reader meets one whole twice.
- **Two links where a link crosses a line:** two stops of the keyboard and two links to one place.
- **A link named by a copy of its words wherever it crosses a line:** the same tree, with its words twice.
- **A reading order by an owner attribute or a tab index, the document left in draw order:** each reaches only one of a reader's tools, the keyboard and a selection.
- **What takes no place in the reading order gathered at a page's end:** a decoration's links would leave the place DEC-033 point 3 reads them at.
- **What takes no place in the reading order placed before the next part that has one:** a ground would stay under the text it backs, and fewer pages would carry z-index, but it edits DEC-033 point 6, under which such a part follows those its component lists.
- **Lines left with no break character, or a space at every break:** a copy runs words together, or splits a word broken after a hyphen or a slash.
- **Each line's strut hidden from a reader's tools, for a heading's name:** where each line is placed alone, Chrome still names the heading with a space at the break, so it mends the name only in lines kept in one row (#3118).
- **A hidden copy of each wrapped phrase, so find meets it:** each text would lie twice.
- **A picture's text on the picture in its layer, or the picture as an HTML image:** the first lies in draw order, hidden with its layer, and the second ends a layer at each picture, against DEC-020 point 1, for what an element of its own carries.
- **An `img` whose `alt` holds a picture's text, drawing nothing:** it would reach a reader view too, but Firefox copies its `alt` with a selection, against point 7.
- **The focused link raised alone:** on a page whose elements carry z-index, its text keeps the raise inside it.
- **A raise by `:focus-within` where `:has()` is missing:** it raises a text whatever inside it has focus, for browsers the test did not reach.
- **The focus left under a later shape:** a keyboard reader loses where they are.
- **The step reading the browser's accessibility tree now:** its comparison and its cost are not yet known.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-015 point 3, "Each text, or run of a text, the tool dropped", comes to add that what only a reader's tools get, such as a picture's text, is no text the tool draws, and is never reported dropped (point 8).
  - DEC-020 point 3 comes to say that the document's order is the reading order, in its heading and its first and third bullets: the renderer writes a page in its reading order, a layer is still a run of shapes between two texts in the tree's order, and each element of a page whose elements, layers included, do not all lie in their draw order carries its place in the draw order by z-index (point 5).
  - DEC-020 point 5, "What an image does not show", comes to add a reader's tools, such as a screen reader, to what a person covers (point 8).
  - DEC-020 point 10, "What a reader who does not see the page gets", comes to cite this record in place of #2740, as what it decides.
  - DEC-033 point 3, "One link across runs": "spells it as its own record decides" comes to cite this record (point 3).
  - DEC-033's Implications, "The HTML renderer spells the reader's side as #2740's record decides", comes to cite this record.
- **No edit to DEC-020 points 6 and 7, or to [visual-communication:DEC-027-forced-colours-viewing] point 4.** Whether the viewing step reads the reader's side is [project-kit#3115](https://github.com/aleskalfas/project-kit/issues/3115)'s, which decides it with a record of its own, a prototype and a timing.
- **Answers the edits may ask,** in this change: of the capability's page on outputs (`outputs.md`), which anchors DEC-015 point 3, DEC-020 points 3 and 5 and DEC-033, and of the capability's README and its loaded rule set `VIS`, which anchor DEC-020 point 5. No page changes its text here: the Tasks below change it with what they build.
- **The Task that gives a reader the reading order** builds points 1, 2, 5, 6 and 8 for a text's mark, a list and the reading order, with DEC-033's change of a text's structure and a reading order. Its image tests draw at scale 1. It closes with a person's reading with a screen reader.
- **The Task of links and alternative text** builds points 1 to 4 and 7 for a run's structure, a run's link and the texts of pictures and instances, with DEC-033's changes of a run's link and structure and of a picture's text. Its image tests draw at scale 1. It tests a focused link under a later shape on a page whose orders differ, raised by a rule marked `!important`.
- **A follow-up, project-kit#3118, weighs lines kept in one row,** each moved into place by a relative offset, against DEC-020 point 2: find across a line break against where each line's ink lies.
- **Read against, and left as they stand:** DEC-020 point 2, each line placed alone, whose revisit on #2740's test point 6 answers by accepting find's loss until the follow-up; DEC-023 point 4; [visual-communication:DEC-026-html-page-print], since nothing here is drawn; [visual-communication:DEC-031-html-page-backdrop] point 4; DEC-033 point 6, whose order of a page's parts point 5 follows; [visual-communication:DEC-036-concept-signs] point 5.
- **Revisit this record** if a screen reader misreads a word as point 1 spells it, a link across lines or a picture's text; if a browser comes to find a phrase, or name a heading, across lines placed apart as written; or if the follow-up finds a form that keeps each line's ink where DEC-020 point 2 holds it.
