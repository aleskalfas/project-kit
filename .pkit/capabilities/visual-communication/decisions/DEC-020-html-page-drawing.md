---
id: DEC-020
title: An HTML page holds SVG drawings, and the viewing step reads that file with no browser
status: proposed
date: 2026-11-06
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the HTML renderer writes one file for each language. Each page is an SVG drawing in that web document, one under the other. A page shrinks with a narrow window, keeps its proportions, and never grows past its own size. Each face lies once in the file, and a line is written from its start, with each span at the place the engine's widths give. The viewing step reads that same file: it cuts each page out, hands its tool what the drawing needs, and leaves the file in its folder for a person to open. A session may also hand the reviewer images another tool drew.

A test found four faults a reader sees in a browser and the tool's image does not show: faces held page by page, a file that does not say its encoding, WebKit's own measure of a line, and a page with no ground under a reader's forced colours. A test on the file holds the answer to the first three. The fourth goes to the record of how a page holds its modes ([project-kit#2738](https://github.com/aleskalfas/project-kit/issues/2738)). What ships takes no browser: whoever maintains the capability looks for the next fault of what the renderer writes, in more than one browser engine, and a person's look covers what a piece brings of its own. What a reader who does not see the drawing gets is left to a record of its own ([project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740)).

Two judgements carry this record, and neither is a test's result. A line's baseline does not choose between SVG and HTML elements, the records allow both, and the readers lean to HTML text. The tool draws no HTML text, so that lean asks for a browser in what ships, or an image of a form no reader opens. This record holds that a browser costs more than what was measured for those readers, and that the step reads what a reader gets. So it sets the lean aside, which departs from the order set by the issue that asks for this record ([project-kit#2737](https://github.com/aleskalfas/project-kit/issues/2737)), a reader first and the step last. One cover is then a run that issue's list of covers does not name.

## Context

[project-kit#2737](https://github.com/aleskalfas/project-kit/issues/2737), called *the issue* here, asks for this record. A piece is to be drawn as a web page ([project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570)). A format whose medium switches modes while open holds them in one file ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7). No record says what that page is, how its pages lie, or how the capability sees it.

The accepted records set these limits:
- **A renderer adds nothing.** It draws each line as given, and adds no place, size, colour or font of its own. It declares what its medium needs and the scene leaves open ([visual-communication:DEC-001-visual-communication-discipline] point 2, [visual-communication:DEC-005-engine-and-plugins] point 4).
- **The viewing step fits its tool to the page.** It is defined over a renderer's drawn output, never over one format. Its tool, resvg, reads SVG ([visual-communication:DEC-015-viewing-step-and-reviewer] points 1 and 2).
- **A browser enters here, if anywhere.** DEC-015's Implications name this record as where one would come. Chrome cannot be pinned, and stopped in every sandbox tried (DEC-015, Context).

Five terms serve the rest:
- A *page file* is the file the HTML renderer writes: the pages of one language, at one size, in one web document.
- A *reader's side* is what a page file gives a reader who does not see the drawing.
- A *strut* is an empty inline block of known height whose foot sits on a line's baseline. It places that baseline with no help from the font's metrics.
- The *form* is what the renderer writes whatever the piece: a page file's head and layout, and how it writes faces, lines and pages.
- A *fault* here is what a reader would find wrong in a browser: a text that cannot be read, a wrong glyph, or a line more than one device pixel from the engine's place. The reviewer's list of faults (DEC-015 point 7) is another thing, and point 9 alone speaks of it.

### What the test showed

The test took the four pages of the showcase deck of the repository the capability is authored in, in both languages and both keys, as the SVG renderer drew them. That is 16 pages, each 1280 px wide, with 100 lines of text in each language, in one brand's three faces. It wrapped them in several-page documents of one key each. Its code is thrown away. It ran on one Mac, on macOS 26.6.

What drew them:
- **The viewing step's tool:** resvg 0.48.1, through the pinned wheel.
- **Chrome 157, Firefox 157 and WebKit 27.2,** the last two Playwright's own builds, through a driver written for this test. [project-kit#2736](https://github.com/aleskalfas/project-kit/issues/2736)'s browser script had not landed.
- **WebKit as macOS ships it,** through a web view, on the third fault and on the final file. Safari uses this browser engine.

What the tool did with a document:
- **The whole file** it refused: the document has no SVG root.
- **HTML text in a `foreignObject`** it drew to nothing, with no warning.
- **Each page cut out of the file,** as the SVG renderer wrote it, gave the same bytes as the step's image of that renderer's page, on all 16 pages. A parser of HTML found each page by its trace id with the same result, in a file that a script and loose markup had made no XML, and with the file's whole style sheet handed over.
- **Its check for dropped text** ran unchanged on the pages cut out. It named the texts of a face taken out of the file, and a text whose paint was taken out.

The first fault: what one document does to faces.
- **Each page with its own faces.** A document holds one set of faces, whichever `<style>` holds a rule. So 10 faces met under 3 names, and each browser loaded them all and reported nothing.
- **What a reader gets.** Three of the four pages changed, in all three browsers. In Chrome and Firefox, 11 to 15 of a language's 100 lines came out over 0.25 px from the engine's width, and 1 or 2 over 1 px, at worst 1.39 px. The likely cause is kerning lost across several subsets.
- **What the tool shows.** Nothing: each page drew from its own faces, byte for byte as the step's image.
- **Each face once for the file.** In Chrome and Firefox no line came out over 0.25 px, at worst 0.19 px, and the file was half the size.

The second fault: a file with no encoding. With the encoding taken out of a file, WebKit guessed windows-1252 and drew each Czech letter as two wrong ones. Chrome and Firefox guessed UTF-8. The tool showed nothing, since the test decoded the file before the tool saw it.

The third fault: what WebKit does with a width it measures.
- **A run left to follow the last.** The SVG renderer wrote no place for a run after a line's first. WebKit opened a wider gap at that edge. Of the 86 lines of more than one run, at device scale 2, 11 ended over 1 CSS px past the same line set as HTML, at worst 3 px. WebKit as macOS ships it did the same at scale 1, on 5 of the 17 such lines on two pages. The gap shows to the eye.
- **A line anchored at its middle or end.** The deck holds none, so a hand-made page anchored the deck's own lines. Of 44 lines of one run anchored at their end, 26 ended over 1 px off the same line as HTML, at worst 5.5 px. As macOS ships it, 21 did, at worst 6 px.
- **Why.** WebKit appears to measure a line with no kerning and draw it with kerning: its widths matched Chrome's with kerning off on 195 of 200 lines. That was read from outside and not proved. The same line set as HTML stands in these figures for the engine's place, since its ink ends where a kerned line ends.
- **Who shows it.** Neither the tool, nor Chrome, nor Firefox.
- **A line written from its start, each span at the engine's place.** No line stayed over one device pixel in either WebKit, at any anchor, nor in windows down to 375 px. The tool's image moved by a mean of at most 0.0039 of 255, and nothing dropped.
- **What that form costs.** With embedded faces refused, in Firefox, spans that followed each other stayed apart, and spans placed ran together by up to 7.9 px.

The fourth fault: a page with no ground of its own, under a reader's forced colours. With the ground taken out of one page, Chrome's forced dark laid black behind a text that stayed dark, and the page's title went all but unread. The tool's image of such a page lies on white (DEC-015 point 5). Every page of the deck draws a ground, so this came from a page cut for the test.

A line's baseline. Each of the 200 lines was set at the engine's coordinates, black on white, and its ink read back. The table gives the worst distance from the engine's baseline, in CSS pixels. *Line box* is an element whose `line-height` is the engine's step, the ordinary way. Chrome's rows use its real path for a device scale, since an emulated scale leaves HTML text on whole CSS pixels.

| Browser, device scale | SVG text | Line box | Strut |
|---|---|---|---|
| Chrome, 1 | 0.49 | 1.33 | 0.49 |
| Chrome, 1.225 | 0.40 | 0.96 | 0.81 |
| Chrome, 2 | 0.24 | 0.63 | 0.24 |
| Firefox, 1 | 0.49 | 0.56 | 0.49 |
| Firefox, 2 | 0.24 | 0.42 | 0.24 |
| WebKit, 1 | 0.91 | 0.52 | 0.49 |
| WebKit, 2 | 0.44 | 0.26 | 0.24 |

- **A line box is not the engine's place.** In Chrome it passed one device pixel at every scale, and each browser moved the lines otherwise.
- **A strut is.** In Chrome and Firefox at scales 1 and 2 it lay exactly on the SVG line. Half a pixel at scale 1 is a line rounded to a pixel row, which SVG text does too.
- **In a narrow window too.** With every length a share of the page's width, which takes no script, strut lines stayed under one device pixel from the baseline. That held in all three browsers, at scale 1, on three of the pages, at windows from 1024 to 375 px.
- **Layout's word is not enough.** The browsers' own positions called the strut exact where the ink lay a device pixel off.

What a reader's own settings did:
- **Forced colours,** a reader's high-contrast setting, left the SVG drawing as the brand set it, in all three browsers. HTML text over that drawing took the reader's colours in Chrome and Firefox. In Chrome they came as a plate behind each line, legible, on a drawing they left alone. In WebKit neither form changed.
- **A minimum font size,** set in Chrome, left SVG text at its drawn size. HTML text grew, and ran past its panel and the page's edge. Chrome reported 20 px for both, so only the ink showed the difference.
- **A browser's zoom,** run as the narrower window it gives a page, in Chrome. At 200%, a page in a window of 1280 px grew by nothing, and in 1920 px by 1.5 times.
- **A pinch,** run as Chrome's own page scale, enlarged the page past the window, with no change to its layout.

A browser in a sandbox. Each browser ran once, on one page, in a hand-written sandbox on the same Mac, with the network denied and writes held to a few folders, on its own defaults. That is the kind of sandbox DEC-015 tried.
- **Chrome** stopped, unable to open a local socket.
- **Firefox,** Playwright's build, stopped, its own sandbox refused inside this one.
- **WebKit,** Playwright's build of 78.9 MiB, drew the same bytes as outside the sandbox. A request from its page reached the network, where the same sandbox refused a plain request made outside a browser. So this sandbox did not hold all of it.

The final form, in all three browsers:
- **A page in a window.** At six widths from 1920 to 375 px, in both languages, each page kept its proportions and nothing scrolled sideways, with no script.
- **The file whole.** Every face loaded and no id repeated. With the other pages hidden, each page's lines lay within one image pixel of the tool's.
- **No other fault showed,** by these measures or by eye.
- **An id repeated across pages** drew no fault, in any browser, even with the page holding the first one hidden.

What the test did not reach:
- **In the deck:** a picture, an ellipse, a line through several points, a run measured in more than one family, a right-to-left language, pages of two sizes, and a brand's faces other than these three. A line anchored at its middle or end was reached on the hand-made page alone.
- **In the file:** more than one mode.
- **Browsers:** Safari as an application, Firefox as shipped, Linux, Windows, a phone, and a real screen of high density. Chrome's scale came from its own flag, and its narrow windows ran at scale 1. A browser advanced within a span as the engine did on this one Mac, and point 5 rests on that. Text fitted to a screen's pixels on another system may not.
- **Readers:** a screen reader, a keyboard, selection and find-in-page, which are #2740's, and printing.
- **Sandboxes:** a project's real sandbox, Linux, and a browser with its own sandbox turned off.

## Decision

**The HTML renderer draws each page as SVG, in one web document for each language. Each face lies once in that file, and a line is written from its start, each span at the place the engine's widths give. A page shrinks with a narrow window and never grows. The viewing step reads that file with the tool it has, and leaves it in its folder. A session may hand the reviewer another tool's images. What ships takes no browser.**

### 1. SVG draws a page

- **Each page is an SVG drawing** in the document, drawn as the SVG renderer draws it, but for what points 4 and 5 say and what #2738 says of its paints.
- **Each text a reader sees lies in that drawing,** as SVG text.
- **HTML elements do not draw a page.** The tool draws no HTML text, so such a page takes a browser in what ships, or gives an image of a form no reader opens. This record takes neither, which sets the readers' lean aside. Rationale weighs it, and says what it costs.
- **This settles the drawing alone.** What the page gives a reader who does not see it adds to this drawing, and point 11 says what stays open.

### 2. A file holds a language's pages, one under the other

- **One file for each language.** A page file holds every page of that language, in the scene's order. Where a piece has several sizes, each has a file of its own. How a file holds a piece's modes, and what names it, is #2738's record.
- **Its head says what a browser would otherwise guess:** its encoding, its language and its viewport.
- **The pages follow each other down the document,** each in the middle of the window, with a gap between them. The renderer declares that gap as a choice of its medium (DEC-001 point 2).
- **Around the pages the file sets no colour of its own,** so the browser's own ground shows. A page drawn on white can then meet that ground with no edge to see.

### 3. A page shrinks with a narrow window, and never grows

- **In a window at least as wide,** a page keeps its own size.
- **In a narrower window** it shrinks as one drawing, to the window's width, and keeps its proportions. So the document never scrolls sideways.
- **It never grows** past its own size. A browser's zoom stops at a page that fills the window, since a page at the window's width follows the window. A pinch enlarges past it.
- **It takes no script,** and the renderer declares this as a choice of its medium, as it does point 2's gap.

### 4. A document is one scope, so a face and an id lie once

- **Each face lies once in the file's style sheet,** under its family and weight, subset to every character the file draws in it. No face lies once for each page.
- **A rule the drawings share** lies once in that sheet too.
- **No id repeats in the file.** A page's markers carry ids of their own, so no page's drawing rests on another page.
- **A picture** lies in each page that draws it, so a page cut out of the file holds it. How a page holds a picture's variants is #2738's.

### 5. A line is written from its start

- **A line stands where the engine's widths put it,** anchored at its start, whatever anchor the scene gives it. Its place is the anchor's place less the share of its width that the anchor lays before it.
- **A line of more than one run** gives each span its own place too: the line's start plus the widths of the spans before it.
- **The scene holds those widths,** so the renderer adds no place of its own.
- **A line of one run anchored at its start** needs nothing more.
- **A text with right-to-left characters** is left out of this point. It keeps its anchor, and its spans follow each other, since the scene holds no direction and spans placed in their order would read backwards. The third fault stands on such a text.
- **The drawing's direction stays left to right,** so that a line's start is its left edge.

### 6. The viewing step reads the page file

- **The renderer's own output, never a second drawing.** The step reads the page file as the renderer wrote it, at one key. So an image comes out of the form a reader opens.
- **How a key reaches the tool,** where a file holds several modes, is #2738's. It may have the renderer write a file of one key, in this same form, which no reader opens.
- **Each page's `svg` is well-formed XML,** as the SVG renderer's pages are. The rest of the file is plain HTML, so a script or markup a later record adds binds on nothing here.
- **What reaches the tool:** each page's `svg`, found by a parser of HTML by its trace id, with the file's style sheet. A trace id found twice under one key is refused. On one key's page the sheet holds the faces, the rules the drawings share and the file's layout, which left the image unchanged. The tool reads a part of CSS, so what a later rule does there is that record's to say. Each face is handed over the way the step hands over a page's faces (DEC-015 point 2).
- **The cut lies in the module that holds the tool,** so the rest of the step stays free of any one format (DEC-015 points 1 and 2).
- **What it finds dropped.** The check of DEC-015 point 3 runs on each page cut out, as it does on a page of the SVG renderer. How it sees a paint a sheet holds is #2738's.

### 7. An image shows the drawing, not the document

- **How far it differs from the SVG renderer's image:** for one key's page, by what points 4 and 5 move, which on the deck was a mean of at most 0.0039 of 255. The same scene gives the same drawing, by design. So an image proves that the file holds the right drawing. It says nothing of what the document adds around it, and it stands in for no browser.
- **What it cannot show, and who covers each:**
  - A face or an id held twice, a line not written as point 5 asks, an `svg` that is not well-formed, or a head that lacks what point 2 asks: a test on the file.
  - How a browser reads a face, which the tool may draw where a browser would not: a person, in a browser.
  - A line of several runs with right-to-left characters, which the tool's own handling of spans may draw in another order: the report (DEC-015 point 3), and a person, in a browser. That was read from the tool's code, and not run.
  - How pages lie, and what a page does in a narrow window: a test of what the file writes, and a person.
  - How one browser engine draws a line, and a line a pixel off its place: whoever maintains the capability, by the run of point 10. Nothing shipped, and no one browser, covers this.
  - What a reader's own settings do to a page: the run of point 10 for the form, a person for a piece, and #2738 for a reader's colours.
  - A mode switched while open: a test and a person, as #2738 decides.
  - A reader's side, a followed link and a screen reader's reading: a test, the report and a person, as #2740 decides.
  - How a page prints: a person.

### 8. A person opens the file the step read

- **A run leaves the page file it read** in its folder, beside the images. A person opens it in a browser.
- **The report says so.** It names the file, and says the image stands in for no browser, so each run asks a person to look.
- **It is no export.** It takes no number, writes no record of exports, and is never committed. The next run replaces it, as it does the images (DEC-015 point 4).
- **At one key.** Where #2738 has the step read a file of one key, the file left shows that key alone, and what a person needs past it is #2738's.
- **A render writes no preview of this renderer.** The step's file serves that need.

### 9. A session may hand the reviewer another tool's images

- **Whose images.** The reviewer reads the step's images. A session may also hand it images of the same pages that another tool drew.
- **They promise nothing,** as the step's do not (DEC-015 point 6).
- **Its report says which tool drew each image.** A difference between two tools' images of one page is a note, unless the reviewer's list of faults names it.
- **A finding on such an image** names the page and the tool. It names a trace id where the step's frames show the element.
- **The reviewer draws nothing.** The session runs each tool, and the reviewer only reads.

### 10. What ships takes no browser

- **The faults found.** A browser showed all four. The first and the third came unforeseen, and the other two from asking what a file without a thing would do.
- **The first three lie in the form, and the fourth where a piece and the form meet.** Points 2, 4 and 5 answer the three, but for point 5's exception, and a test on the file holds each answer. #2738 decides the fourth.
- **The maintainer's run looks for the next fault of the form.** It is a run in real browsers, in more than one browser engine, by whoever maintains the capability. It reads pages that hold each kind of thing a scene allows, and pages that lack what a scene may leave out, on a browser's defaults and under a reader's forced colours and minimum size. It comes at each rise of the renderer's version, and the first stands before a piece can declare the format of point 11. That version's release says which browser engines and systems the run reached, and a fault it finds is mended or filed before that version ships. It lies where the capability is authored, so nothing ships and no project runs it. A fault a browser brings between two versions, or that shows only on a system the run did not reach, reaches readers first.
- **What a piece brings,** alone or where it meets the form, past the pages the run read, is a person's look (point 8). A brand's face a browser will not read is one such thing.
- **What a browser can show besides,** such as a switch pressed while open, is no such fault. Point 7 covers those.
- **Where a browser may sit.** On the machine of whoever maintains the capability, for that run, and in a session that hands the reviewer images (point 9), outside any confined build. Never in the step, a render or validation.
- **The step's tool stays resvg** (DEC-015 point 2). What the permission model adds for an outside program stays open with [project-kit#2575](https://github.com/aleskalfas/project-kit/issues/2575).

### 11. What this record leaves to other records

- **What a reader who does not see the drawing gets** is #2740's: the form of a reader's side, selection, find-in-page, a keyboard reader, and what the step does with that side.
- **Its forms stay open over this drawing,** which keeps its text (point 1). A layer of real elements over the drawing then holds each text twice. A layer that alone holds a text is HTML text over SVG shapes, which reopens point 1 at the price Rationale names.
- **What it takes from this test:** a line can be placed as real text at the engine's baseline by a strut, in a narrow window too. A reader's forced colours and minimum size reach HTML text and not the drawing, and such a text can outgrow the place the engine gave it.
- **A reader who needs a page larger than the window** is not served by the drawing (point 3). #2740 weighs that reader too.
- **How a page holds its modes,** how a paint is spelled and the reader's switch are #2738's, and so is what a reader's forced colours meet on a page with no ground (Implications).
- **A format a piece exports** in this medium, with what it loses, is left to the change that adds it. That change comes after #2740's comparison has answered and the first maintainer's run (point 10) has been made, so that no reader meets the form before then.

## Rationale

**The figure, and what it did not decide.** The issue asks a line's baseline to choose between the two. The figure is the worst distance of a line from the engine's baseline, read from the painted ink, since the page's structure called lines exact that were not. A form is rejected where that distance passes one device pixel, in any browser at any scale reached. That threshold was chosen on reading the results, as the least a reader could see move. It rejects the line box, in Chrome. It keeps SVG text and the strut, the strut narrowly: 0.81 CSS px at Chrome's fractional scale is 0.99 of a device pixel. So HTML elements stand, and the figure leaves the choice open.

**Why SVG.** The issue weighs a reader first, then the records, and the step last. Taken in that order:

- **A reader who sees the page, on a browser's own settings,** gets nearly the same page either way. HTML text lies nearer the baseline in WebKit, and SVG text at Chrome's fractional scale. HTML text gets for free the place point 5 has to write, so it holds no third fault on the text point 5 leaves out. Otherwise no fault separates them.
- **A reader who sets their own size or colours** leans to HTML text. A minimum size reaches it, and forced colours reach it as a plate behind each line. Neither reaches the drawing. Against that, text grown to a minimum size ran off the page, and on a page that draws its own ground the drawing stayed as legible as the brand drew it.
- **A reader who does not see the page** leans to HTML elements too, where each text lies once in a native tree. What an SVG form may cost that reader is #2740's list: each text held twice, find-in-page meeting it twice, a link taking focus where nothing shows, and emphasis split across lines. How far that lean goes is unmeasured, since no screen reader met either form, and one SVG form holds each text once.
- **The records** do not choose. A web page is the medium (DEC-006 point 7). What a renderer cannot draw it may draw through the renderer of vector pictures and place as a picture (DEC-005 point 9). So HTML text over SVG shapes is open to them, in the tree's own order.
- **The step** has two roads to HTML text, since the tool draws none of it. It takes a browser, or it reads the SVG renderer's page of the same scene.

**What sets the lean aside.** Two judgements, and neither is a test's result. The issue's order has the step serve a form the readers and the records leave open. The records leave it open and the readers lean, so these two depart from that order.

- **A browser costs more than what was measured for those readers.** Each measured loss carries a counter-cost. The loss of a reader who does not see is unmeasured, and #2740's to measure on a real page. The cost of a browser is the next passage, and it stands however a page is drawn.
- **The step reads what a reader gets.** DEC-015 point 1 allows the other road, since the SVG renderer's page is a renderer's output. But the issue asks that an image shows the file a reader gets. On that road the image shows another form, so a reviewer could pass a page whose text a reader gets otherwise, and the check for dropped text reads a form no reader gets. This is the lighter of the two: in this test the reading caught only what a test on the file also holds.

**What a browser costs, however a page is drawn.** Three costs stand whichever way this record chooses.

- **An outside program to draw.** The step draws in the command's own process, and calls no outside program (DEC-015 point 2). What the permission model adds for one stays open with [project-kit#2575](https://github.com/aleskalfas/project-kit/issues/2575).
- **A sandbox that may stop it, or may not hold it.** Run once each on one Mac, in a sandbox of DEC-015's kind, Chrome and Firefox stopped on their own defaults, and WebKit's page reached the network from inside it. So a build that confines what it runs may lose the step, or confine only part of a browser. That is expected, not settled, since a project's real sandbox was not reached.
- **A program that moves with the machine, or one more download.** Chrome cannot be pinned. A pinned build, such as Playwright's WebKit at 78.9 MiB, is a program the methodology does not install, so the step would check for it and name what is missing ([visual-communication:DEC-002-files-and-validation] point 8). A person without it would get no image.

**What setting the lean aside costs.** The cost that stands is a reader's: a reader's size and colours do not reach the text, and a reader's side holds each text twice or rests on SVG's roles. The cost of being wrong is larger. If #2740 finds a reader's need that no form over this drawing meets and HTML text does, point 1 reopens. The change that draws the pages and the change that has the step read them are then reworked, with #2738's paints, #2740's chosen form and the edits this record makes. The step then takes a browser, which reopens point 10, DEC-015 point 2 and #2575, or it reads the SVG renderer's page, which gives up point 6 and point 8's file, and with them an image of what a reader gets. What bounds that price is reach: point 8's file is no export, so until a piece declares this format no reader meets the form. So the gate lies at the format (point 11), and not at the first page, which would otherwise stand behind the words a reader's side says ([project-kit#2739](https://github.com/aleskalfas/project-kit/issues/2739)) and a person reading with a screen reader.

**Why each face once for the file.** The first fault decides it, and the file is half the size. A page in a document is not a file of its own: its rules and ids reach the whole document, so the document is the scope to write for.

**Why a line is written from its start.** The engine measured each span, so writing its place draws the line as given (DEC-005 point 4). An anchor, or a span left to follow the last, rests on the browser's own measure, and WebKit's is not the engine's. A place written on a span also starts a stretch of text of its own, and an anchor acts on each stretch alone. So a span placed under a middle or end anchor would stand wrong in every browser, which is why the line is anchored at its start. The costs are three. The image moves by under 0.004 of 255. Where a browser's widths differ from the engine's, a centred line sits half that difference off centre, which embedded faces kept under 0.1 px in Chrome and Firefox, and within one device pixel in WebKit. And a reader whose browser refuses embedded faces gets spans that run together, where spans left to follow each other would flow. That reader has lost the engine's widths across the page, and the fault removed reaches a reader of WebKit on its default settings.

**Why a page stops at the window.** The two rules meet in a reader who zooms: a page that never scrolls sideways follows the window, and zoom narrows the window. So on a laptop zoom gives little or nothing, where the web's guidance on text asks for 200%. That reader has a pinch or the system's magnifier. A page that kept its own size in every window would give zoom its full reach, at the cost of a sideways scroll on every window narrower than the page, a phone's above all, on a page that could then not be seen whole. A page is one fixed layout, so either rule fails a reader. This record keeps the whole page in view, because a pinch reaches past it and nothing reaches back. It is one rule to change if a reader needs it.

**Why the step cuts the page out of the file.** The step is defined over a renderer's output (DEC-015 point 1), and the issue asks that an image shows the file a reader gets. A drawing handed over from memory would show what the renderer held, not the form a reader opens. In this test that reading caught only what a test on the file also holds. Its worth is a design's: a reviewer reading the file's own drawing is placed to meet a fault nobody foresaw. The tool reads SVG, so the step fits it to the page, as it does with faces (DEC-015 point 2).

**Why no browser ships.** With SVG drawn, a browser is worth its cost where it finds what nothing else can, for someone who can act on what it finds. For the form, that someone maintains the capability: a project cannot mend the form, since it adds no renderer of its own (DEC-005 point 12). So a browser belongs on that machine, in more than one browser engine, since WebKit showed three of the four faults, Chrome two, and no one engine all. An adopter's build is no place for it. For what a piece brings, an adopter can act, and the cost decides: the test met one such fault, on a page cut for it, and #2738 decides that one. That leaves a thin cover: nothing makes a person look, and the eye sees a gap and not a line a pixel off. The Revisit watches what gets past it.

**How the maintainer's run reads the issue.** The issue lets a test, the report or a person cover an item, and bars a project's own tool, since this record ships. The run is none of the three, and it sits close to that bar: it is tooling of the project that authors the capability, though never of one that adopts it. So it is a cover the issue's list does not name. A project takes its result with the release, as it takes the capability's checks ([visual-communication:DEC-013-shipped-library-releases] point 6). It lies where those lie, and unlike them it comes at a version's rise, and no required check holds it.

**Why the file is left for a person, and no preview from a render.** A person needs to open the form a reader gets, and the step's file is that form once the step has run, at one key until #2738 says otherwise. A preview from a render would add a second writer of it, and a change to each command and page that assumes a preview is SVG.

**Why a file sets no colour around its pages.** A renderer adds no colour of its own (DEC-001 point 2, DEC-005 point 4), and a scene says nothing of what lies around a page. So the browser's ground shows, and a page with no ground meets it, which is where the fourth fault lies.

**Why a session may hand over images the step does not draw.** A session can hold a tool the step may not, a browser among them, and the issue asks for this. The images promise nothing, so nothing rests on them, and the capability carries no such tool.

### Alternatives considered

- **HTML elements placed by CSS at the engine's coordinates, over all of a page.** Rejected. A line, its arrowhead and a route through several points have no HTML element, so this comes to the next one.
- **HTML text over SVG shapes, the step taking a browser,** each shape drawn through the renderer of vector pictures (DEC-005 point 9). One tree, a reader's settings reach the text, and point 5 is not needed. Left out on what a browser costs. The Revisit says what brings it back.
- **HTML text over SVG shapes, the step reading the SVG renderer's page of the same scene,** with the maintainer's run on its ink and point 9 for a browser's images. The nearest of these: no browser ships, the readers' lean is served, and DEC-015 point 1 allows it. The image would barely differ. Left out on the second judgement alone, since the image would show a form no reader opens. It is the road to weigh first if #2740's test reopens point 1.
- **A layer of real elements over the drawing, for what the eye sees.** Left out here. As a reader's side it is #2740's to weigh.
- **Each face once for each page.** Rejected. It gives the first fault, at twice the size.
- **A reader's window filled, a page growing past its size.** Rejected. A renderer would choose a size no reader asked for, and a browser's zoom gives the same.
- **A page that keeps its own size in every window.** Rejected, as Rationale says.
- **One page at a time, with a control to turn it.** Left out. It needs a script and words of its own, which nothing here asks for.
- **Waiting for #2740 before the first page.** Left out, as Rationale says: the gate lies at the format.
- **Chrome as a second tool of the step, shipped.** Rejected, as Rationale says.
- **A pinned WebKit as a tool a project opts into,** such as Playwright's build, or as an outside program on the path that needs it (DEC-002 point 8). A pin removes Chrome's first objection, and it is the browser engine that showed the third fault. As a second tool of the step it would serve what a piece brings, where the test met one fault on a page cut for it, and point 9 lets a session hand over its images with nothing shipped. As the tool that draws HTML text it would serve the readers' lean too. Left out on an outside program whose place in the permission model is open, and a download for each project that takes it. A sandbox of the kind tried did not hold it, which one run does not settle.
- **A check of each face with the font check browsers run,** shipped with no browser. It would answer the case point 10 names, a face a browser will not read. Not tried, so left to a later change.
- **Handing the tool the pages the renderer held in memory.** Rejected. Nothing would then read the file.
- **The whole file as well-formed XML, read as XML.** Rejected. It would bind what #2738 and #2740 add to XML's rules, and a tree that parses as XML can differ from the one a browser builds.
- **Cutting each page out of the text by a search, with no parse.** Rejected. A script or a sheet of a later record could hold the same marks.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). All but the last lie in [visual-communication:DEC-015-viewing-step-and-reviewer]:
  - **Its summary.** It says the tool reads the SVG renderer's pages, the step writes images with the frames and a report, and the reviewer reads them. It comes to say the tool reads those and each page of the HTML renderer's file, the step leaves that file beside them, and a session may hand the reviewer another tool's images too.
  - **Its point 2, "Over the SVG, behind one module".** It comes to say that the module takes a renderer's drawn page, and cuts it out of the file where a renderer writes one file for its pages.
  - **Its point 2, "The page's faces".** It comes to say that the step takes each face from the `@font-face` rules of the page, or of the file that holds it.
  - **Its point 2, "What it draws otherwise".** It comes to add that the tool's handling of spans may draw a line of several runs with right-to-left characters in another order, so that point 3's report names each.
  - **Its point 3.** It comes to add that the report of a run over a renderer's file names that file, and says the image stands in for no browser.
  - **Its point 4, "What it writes, and where".** It comes to read: only the images, the frames and the report beside them, the page file the step read where a renderer writes one, and point 2's transient files. DEC-015's command stays their named writer (DEC-002 point 9).
  - **Its point 6, "It shows this tool's drawing, not a browser's".** It comes to say that point 2 and DEC-020 say where the two are known to differ.
  - **Its point 7, "It reads, and does not draw".** It comes to add that a session may also hand the reviewer images of the same pages that another tool drew, which promise nothing either, and that its report says which tool drew each.
  - **Its point 7, "Its findings".** It comes to add that a finding on another tool's image names that tool, and a trace id where the step's frames show the element.
  - **Its Implications, the Revisit's last item.** It comes to read: if DEC-020's point 1 or point 10 reopens on a browser, which refines point 2 alone.
  - **DEC-005 point 4, "A margin keeps lines stable".** It comes to say that centred text stays centred, to within half of a renderer's difference in width where it writes a line from its start (DEC-020 point 5).
- **The change that draws a piece's pages** builds points 1 to 5, and its tests hold what point 7 gives a test on the file. It changes what the two renderers share ([project-kit#2741](https://github.com/aleskalfas/project-kit/issues/2741)), and says where the renderer declares the choices of points 2 and 3.
- **The change that has the step draw the page** builds points 6 to 8, and settles which renderer a run reads and how a caller names it.
- **The change that teaches the reviewer** builds point 9.
- **The maintainer's run** needs a record of its own from the project that maintains the capability, on its means, the browsers' builds and the pages that hold what the deck lacks. #2736's script reaches Chrome alone. It stands before the format's change, so the change that draws a piece's pages does not wait on it. Its record also tries a pinned build in that project's real sandbox, which this test did not reach.
- **Two Tasks take on what this record hands them,** by an edit to each before it starts:
  - **#2738** takes up what a reader's forced colours meet on a page with no ground.
  - **#2740's test** holds the same page with its text as HTML elements beside its four forms, so that point 1's revisit has something to answer to. Its second form reads against point 11: a layer over this drawing holds each text twice.
- **The SVG renderer's own pages hold the third fault.** A reader of its file in WebKit gets that gap, and a line anchored at its middle or end stands off its place. Point 5 belongs where the two renderers share their drawing, since nothing in its reasons is HTML's alone. That is a change of its own, with the SVG renderer's version rise, and it ends the difference point 7 names. It weighs first a program that ignores `@font-face`, where placed spans may collide.
- **What anchors the edited points** may owe answers when those edits are made, and its text changes with the changes that build this record.
- **[project-kit#2700](https://github.com/aleskalfas/project-kit/issues/2700)** asks how a published copy holds modes, and #2738 reads it. Whichever of its record and this one lands second reconciles the two.
- **The seam's version does not move here.** What a renderer is handed for several modes is #2738's.
- **Revisit this record:**
  - if a fault reaches a reader that the maintainer's run could not have found, and a browser a project could ship would have shown it, which reopens point 10, and point 1 with it, since the first judgement's cost would then be paid;
  - if what the permission model adds for an outside program is settled (#2575), or a pinned browser proves to hold in a project's real sandbox, which weighs the same two again;
  - if #2740's test finds a reader's need that no form over this drawing meets and the same page as HTML text does, which reopens point 1 at the price Rationale names;
  - if a rise of the renderer's version ships with no maintainer's run, since nothing else holds that run;
  - if what Context lists as not reached shows a fault.
