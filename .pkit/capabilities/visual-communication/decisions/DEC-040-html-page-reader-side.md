---
id: DEC-040
title: An HTML page tells a reader's tools what each text is through HTML's own elements, and draws none of it
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a reader who does not see an HTML page gets each text with what it is from the elements the page already holds: a heading's text is a heading, a list's entries are a list. Nothing is written twice, and none of it changes what the page draws. The page is written in the order a reader takes it, a picture's text is an element at the picture's place, and a copy keeps a space where a line broke. Find across a line break fails in Chrome and Firefox, which this record accepts. The viewing step reads what the browser tells a reader's tools. For example, a link the engine broke after "decisions never" takes one press of Tab, and a reader's tools get one link named "decisions never drift".

## Context

[visual-communication:DEC-020-html-page-drawing] chose a page of real HTML text over SVG shapes, so each text lies once. Its point 10 leaves to [project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740) how those elements carry the words [visual-communication:DEC-033-structure-for-readers] fixes, emphasis or a link across a line break among them. It also leaves how the page spells a reading order a component names, selection and find-in-page over lines placed apart, a keyboard reader, and a picture's text. DEC-033 point 3 has a medium that places a text's lines apart spell a link across them as its own record decides. [visual-communication:DEC-015-viewing-step-and-reviewer] point 3 leaves the viewing step to say what counts as dropped.

Terms:
- A *reader's tools* are as DEC-033 has them: a screen reader and its like, reading a page's *accessibility tree*, the tree a browser builds from the file for them.
- A line's *break character* is a space where the engine broke a paragraph's line, and a line break where a paragraph ends.

### What the test showed

The test took the showcase deck of the repository the capability is authored in, as `pkit visual look` drew its English page file through the HTML renderer. Structure was added to that file by hand: headings of two levels, a list from a `repeat` part, a table drawn as a `repeat` over rows read as a list of lists (DEC-033 point 4), emphasis across a line break, a link across two lines, a link in a text marked decoration, a block of code, two pictures, an instance's text, and a page whose reading order differs from its draw order. Its code is thrown away, and the page and its runs are the evidence of this record's pull request.

- **Chrome's accessibility tree,** read through its protocol. The renderer's file as it stands reads as plain text, and each layer as a picture with no name. The form point 1 decides reads each heading with its level, each list with its entries and depth, each run's structure, the link across two lines as one link named by all its words, the decoration's link alone, a picture by its text, a picture with no text as one, the instance's text as a group's name, and the page in its reading order.
- **What is drawn.** The added elements and the break characters changed no pixel in Chrome, Firefox or WebKit. Neither did a page drawn in its draw order by z-index.
- **Selection and copy.** In the renderer's file, Chrome and WebKit ran two words together at each line break, and two lines of code together. With the break characters, all three engines gave a space at a soft break and a line break between paragraphs and between texts. A selection across a page's parts followed its reading order. No picture's text or instance's text was selected.
- **Find.** A phrase within a line was found once in each engine, across spans and emphasis. A phrase across a line break was never found in Chrome or Firefox, by `window.find` or Chrome's text fragments, even with the break's space. WebKit found it with the space. No picture's text or instance's text was found.
- **The keyboard.** The link across two lines took one stop of Tab. Two plain links took two. WebKit's Tab reached no link, as Safari's own setting has it, and Option and Tab reached each once. With a rule of the file, the focus showed on both lines in each engine, as a box in Chrome and WebKit and a line under the words in Firefox. A later opaque shape hid the focus of a link under it, unless the focused link was raised over every shape. Under the flag that forces colours, Chrome gave links the forced palette's link colour.
- **The viewing step's own browser half** named nothing in its four reads of the form, in light and in dark.

**Reached:** Google Chrome 157, and Firefox 157 and WebKit 27.2 as Playwright builds them, on one Mac. **Not reached:** Firefox's and WebKit's accessibility trees, which Playwright does not read; Safari and Firefox as shipped, and their find bars; a caption, a heading past level six, a picture not drawn, a page in Czech, right-to-left text, Windows and Linux.

**A person's reading with VoiceOver:** pending. The project manager fills in this line once the maintainer has read the test's page. This record is not accepted before then.

## Decision

**An HTML page file spells the reader's side in HTML's own elements, on the elements its texts already are, adds an element only for what no text holds, and draws none of it.**

### 1. Each word takes the element HTML has for it

- **HTML's own element** spells each word of DEC-033 point 1: a text's mark, a list and its entries, a run's structure and a run's link. An ARIA role spells a word only where HTML has no element for it, or where its element alone does not reach a reader's tools.
- **On what is already there.** A text's own element takes its mark, each span sits inside the element of its run's structure, and the element of a list, or of an instance's text, holds the elements of what it holds. So each text still lies once (DEC-020 point 1).
- **A run's structure across a line break** splits at the line's edge, one element on each line, each read with its structure. A link does not split (point 3).

### 2. None of it is drawn

- **The elements draw nothing of their own.** The file sets back each look a browser gives them, such as a heading's size, a link's colour and underline, a list's marker or a paragraph's margin, so the page draws the scene alone (DEC-001 point 2, DEC-033 point 3).
- **What stays the reader's:** the focus the browser shows (point 4), and the colours a reader forces, a link's among them.
- **Hidden from a reader's tools:** each layer, what the file defines once for its layers, such as its arrowheads, and a text marked decoration, all but its links (DEC-033 points 3 and 6).

### 3. A link across a line break is one link

- **One link to a reader's tools and to the keyboard.** Its first part is the link they reach, named by the words of all its parts. Each later part follows it under the pointer alone, hidden from a reader's tools and out of the keyboard's order.
- **Named by its parts' own words,** never by a copy of them, so no word lies twice.
- **Its focus shows on every part.**

### 4. A keyboard reader sees where the focus lies

- **Links take focus in the document's order,** which is the reading order (point 5). The file sets no order of its own, and adds no focus stop (DEC-023 point 4).
- **The browser's own sign of focus** stays on every link.
- **A focused link draws over every shape,** so a later shape never hides where the focus lies.

### 5. The document's order is the reading order

- **A page's elements follow its reading order** (DEC-033 point 6), so a reader's tools, the keyboard and a selection take them in it.
- **Where it differs from the draw order,** each element of that page carries its place in the draw order by z-index, within the page, so the page draws as before (DEC-020 point 3). A page whose two orders agree carries none.

### 6. Copying gives the words as written

- **Each line ends with its break character,** taking no width, and a text's last line with a line break. So a selection gives a text's words as written, and two texts apart.
- **A phrase across a line break** is not found by Chrome's or Firefox's find, since each line is placed alone (DEC-020 point 2). The renderer's reference page states this, and no check reports it.

### 7. A picture's text is an element at the picture's frame

- **A picture's text is a picture to a reader's tools,** an element of its own at the picture's frame, in the picture's place in the reading order, named by that text. The picture stays in its layer (DEC-020 point 1).
- **A picture with no text** takes the same element with no name, so a reader's tools show that its text is missing (DEC-033 point 5). A picture that needs none takes no element.
- **A picture not drawn** keeps its element and its text, over nothing drawn (DEC-033 point 8).
- **An instance's text names a group** that holds the elements of what the instance holds, so a reader's tools give it before them (DEC-033 point 5).
- **Neither text is drawn, selected or found.** Each lies only in what the file tells a reader's tools.

### 8. The viewing step reads the reader's side

- **Its four reads stay on spans** (DEC-020 point 6). What a reader alone gets, such as a picture's text, a link's name or a break character, is no span and draws nothing, so the step never reports it dropped (DEC-015 point 3).
- **A fifth read takes the browser's accessibility tree** of each page. The report lists each page's texts and pictures in reading order, with their structure, and each link with its address. It reports each difference from the scene's reader's side, matched by trace id, as it reports the words.
- **The file marks each element the reader's side adds** with the trace id of what it stands for (DEC-020 point 4).
- **A screen reader stays a person's.** The tree is one browser's, not what a screen reader says (DEC-020 point 5).

## Rationale

**Point 1, HTML's own elements.** An element of HTML carries its meaning to every tool that reads a page, a reader's tools, a reader view and a search engine's. A role tells only a reader's tools, and restates what an element would say. Putting the meaning on the elements the texts already are keeps DEC-020's ground: each text lies once, so a reader's tools, a selection and a find meet it once. A run's structure split at a line reads as before, as DEC-033 point 3 foresaw, since a reader's tools read emphasis from each part.

**Point 2, nothing drawn.** A renderer draws the scene and adds no look (DEC-001 point 2), and the test showed the elements reset leave every pixel as it was. The focus and forced colours belong to the reader's own settings, which a renderer leaves alone. A layer read as a picture with no name is noise to a screen reader, and so is a decoration's text, which DEC-033 keeps out of the reading order but for its links.

**Point 3, one link.** DEC-033 point 3 keeps a link across runs one link, since two would read as two places. The lines are placed apart, so no one element can hold the link's words alone. Naming the first part by its parts' words keeps the words once, where a copy in an attribute would hold them twice. The pointer still follows the link from any part, as a seeing reader expects.

**Point 4, the focus.** A keyboard reader who cannot see the focus is lost. DEC-020 lets a later shape lie over a text, and the test showed such a shape hides the focus too. Raising the focused link changes the drawing only while it is focused, the reader's own state.

**Point 5, the reading order.** A reader's tools, the keyboard and a selection all follow the document's order, so one order serves all three. DEC-020's own test drew the same image with z-index, and so did this test. A page whose orders agree keeps its file as it is.

**Point 6, copying and find.** A copy that runs two words together breaks the text a reader takes elsewhere, and the break character mends it at no cost to the drawing. Find in Chrome and Firefox stops at each line placed apart, and only lines flowing in one element would mend it, which DEC-020 point 2 rejected for moving each line's ink. A phrase is found within each of its lines, and a reader's tools read it whole. So the loss is accepted, and stated once rather than reported on every text that wraps.

**Point 7, a picture's text.** A layer holds pictures and shapes in draw order, hidden whole, so a picture's text cannot lie there in reading order. An element of its own at the picture's frame stands in the reading order, and a reader's tools that show where they are show the picture's place. A picture with no name is how a reader's tools learn a text is missing.

**Point 8, the step.** A reader's text draws nothing by design, so a read of ink would report each one. The accessibility tree is what a reader's tools get from the browser, and an HTML parser refuses nothing (DEC-020 point 6), so only the browser's tree shows that the reader's side reached them. The browser's protocol gives that tree over the pipe the step already uses (DEC-020 point 9).

### Alternatives considered

- **A copy of each text for a reader's tools, in either of #2740's two forms that hold one:** DEC-020's elements hold each text once, and a find meets a copy twice.
- **ARIA roles on the elements the renderer writes today:** a role reaches a reader's tools alone, where an element of HTML reaches every tool.
- **Two links where a link crosses a line:** two stops of the keyboard and two links to one place.
- **The link named by a copy of its words in an attribute:** the same tree, with its words twice.
- **A reading order by an owner attribute or a tab index, the document left in draw order:** each reaches only one of a reader's tools, the keyboard and a selection.
- **Lines left with no break character:** a copy runs words together.
- **A hidden copy of each wrapped phrase, so find meets it:** each text would lie twice.
- **A picture's text on the picture in its layer, or the picture as an HTML image:** the first lies in draw order, hidden with its layer, and the second ends a layer at each picture, against DEC-020 point 1, for what an element of its own carries.
- **The focus left under a later shape:** a keyboard reader loses where they are.
- **The step reading the file's elements, or running a screen reader:** the first misses what a browser builds, and the second ties the step to one reader on one system.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-015 point 3, "Each text, or run of a text, the tool dropped", comes to add that what a reader alone gets, such as a picture's text, is no text the tool draws, and is never reported dropped (point 8).
  - DEC-020 point 3, "Where a reading order differs", comes to say that the document's order is the reading order, and that each element of a page whose reading order differs carries its place in the draw order by z-index (point 5).
  - DEC-020 point 4, "The file marks what the step reads", comes to add each element the reader's side adds, with the trace id of what it stands for (point 8).
  - DEC-020 point 5, "What an image does not show", comes to add a reader's tools, such as a screen reader, to what a person covers, the step reading one browser's accessibility tree alone (point 8).
  - DEC-020 point 6 comes to read five things of the browser, the fifth "The reader's side": the browser's accessibility tree of each page, listed in the report, each difference from the scene's reader's side reported (point 8).
  - DEC-020 point 10, "What a reader who does not see the page gets", comes to cite this record in place of #2740, as what it decides, with a person's reading with a screen reader still a person's.
  - DEC-033 point 3, "One link across runs": "spells it as its own record decides" comes to cite this record (point 3).
  - DEC-033's Implications, "The HTML renderer spells the reader's side as #2740's record decides", comes to cite this record.
- **Answers the edits may ask,** in this change: of the capability's page on outputs (`outputs.md`), which anchors DEC-015 point 3, DEC-020 points 3 to 6 and DEC-033, and of the capability's README and its loaded rule set `VIS`, which anchor DEC-020 point 5. No page changes its text here: the Tasks below change it with what they build.
- **The Task that gives a reader the reading order** builds points 1, 2, 5, 6 and 8 for a text's mark, a list and the reading order, with DEC-033's change of a text's structure and a reading order. It closes with a person's reading with a screen reader.
- **The Task of links and alternative text** builds points 1 to 4 and 7 for a run's structure, a run's link and the texts of pictures and instances, with DEC-033's changes of a run's link and structure and of a picture's text.
- **Read against, and left as they stand:** DEC-020 point 2, each line placed alone, whose revisit on #2740's test point 6 answers by accepting find's loss; DEC-023 point 4; [visual-communication:DEC-026-html-page-print], since nothing here is drawn; [visual-communication:DEC-031-html-page-backdrop] point 4; [visual-communication:DEC-036-concept-signs] point 5.
- **Revisit this record** if a screen reader misreads a word as point 1 spells it, a link across lines or a picture's text; if a browser comes to find a phrase across lines placed apart, or a reader's need for it outweighs the place DEC-020 point 2 holds a line to; or if a browser's tree drops a word the file holds.
