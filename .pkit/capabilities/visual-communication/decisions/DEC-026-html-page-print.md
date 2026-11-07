---
id: DEC-026
title: A printed page file puts each page whole on a sheet of its own, every page at one scale
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when a reader prints a page file, each page of the piece lies whole on a sheet of its own. A break comes before each page, and none inside one. Every page of the file prints at one scale, the largest at which each page fits the sheet, and never above the page's own size. The sheet is the reader's: its size, its margins and its header. The file sets nothing of the sheet, and a sheet of the page's own size is the PDF export's. The file asks the browser to print what it draws in its own colours, never adjusted for paper. Which mode prints is the browser's to read from the reader's signals, as on screen.

## Context

[project-kit#2824](https://github.com/aleskalfas/project-kit/issues/2824) asks what a printed page file is. The record of the HTML page lists printing among what its test did not reach, and says a fault there revisits it ([visual-communication:DEC-020-html-page-drawing], Context and Implications). The record of modes lists printing in a dark mode the same way ([visual-communication:DEC-023-html-page-modes], Context and Implications). The PDF renderer draws each page as large as its frame, 96 px to the inch, as its declaration states ([visual-communication:DEC-001-visual-communication-discipline] point 2, and the capability's page on outputs).

The fault came from the change that drew the page through a browser ([project-kit#2804](https://github.com/aleskalfas/project-kit/pull/2804), "Other engines" and "A person's look"):
- **Printed, the deck's page file runs its pages on** with no break, so a sheet's edge cuts a page.
- **In Firefox 157 under Playwright,** page 3's layers part from its text below the cut, each text one row below its own box. The heads of its three columns are lost in the break.
- **Chrome 157's PDF** also cuts page 3 across two sheets, and keeps its text on its shapes. WebKit 27.2 cannot print to PDF under Playwright.
- **Whoever maintains the capability,** looking in Safari and Firefox as shipped, saw pages cut, and the print broken from page 3 on.

The terms used below:
- A *sheet* is one leaf of a print: a side of paper, or its like in a PDF the browser saves. Its *area* is the part inside its margins. A sheet is *upright* when it is taller than wide, as in portrait, and *turned* when it is wider than tall, as in landscape.
- A *page rule* is a rule of the file that sets the sheet: CSS's `@page`, naming the sheet's size, its margins or its orientation.
- A page's *scale* in print is its printed width over its own width.
- The *dialog's scale* is the scale a reader sets in the print dialog, 1 unless they change it. The browser lays it over whatever the file asks.

### What the test showed

The test took the page files of the showcase deck, the deck of the repository the capability is authored in, in both languages and both keys: four slides of 1,280 by 720 px. It added the figure `sockets`, 960 by 488 px. It also built a page of 1,280 by 2,880 px, standing for a web page as tall as its content. That page stacks the deck's four slides in boxes of their own, so each of its layers is a slide's size, not the page's. The test ran on one Mac, through Playwright 1.64.1, and its code is thrown away.
- **Chrome 157** printed through the browser protocol's print to PDF, at the dialog's margins of 0.4 in.
- **Firefox 157,** as Playwright builds it, printed through `window.print()` to its printer that saves a PDF, silently, with no dialog shown. A run set A4, or left the paper at its default, Letter.
- **Neither printed backgrounds,** as their dialogs default. Ghostscript drew each sheet for a look.

**The file as written.**

| Browser, sheet | Sheets for the deck | What a sheet's edge did |
|---|---|---|
| Chrome, A4 upright | 2 | Cut page 3 across both. Its text stayed on its shapes |
| Chrome, Letter turned | 4 | Cut each of pages 2 to 4 |
| Firefox, Letter upright, its header and footer | 2 | Cut page 3. Below the cut each text lay a row below its box, as #2804 found |

The tall page took two sheets of A4 in each browser, cut across them. In Firefox at a dialog's scale of one half, the file's text lay at another scale than its layers on every page, cut or not.

**Print rules added to the file.** Each row adds its rules to a break before each page but the first, none inside one, and no gap.

| Rules | Chrome | Firefox |
|---|---|---|
| The break alone | The deck and the figure each page whole on a sheet of its own. The tall page cut across two sheets of A4, three of Letter turned | The same, the tall page cut across two sheets |
| Each page shrunk until its height fits the area too, the *height bound* | Every page whole on a sheet of its own, on A4 upright and Letter turned, its text on its shapes | The same on A4 and Letter upright, while every page printed at one width. Once one page printed narrower, the slides' text lay at another scale than their layers |
| Every page at one scale, set by the tall page | As above | Every page whole, its text on its shapes |
| A page rule naming a sheet of the page's size, with no margin | Each page on a sheet of its own size: 960 by 540 pt for a slide, as the PDF export has it. Told to use A4 or Letter instead, Chrome shrank each sheet whole onto it | No sheet of the page's size: Letter or A4, turned or upright. On every sheet each text lay at another scale than its layers, off its boxes and cut at its end |
| A page rule naming a margin of none, and no size | Not run | Each text at another scale than its layers, as above |
| A page rule naming a turned sheet, and no size | Each slide whole on turned A4 | Each text at another scale than its layers, as above |

- **The height bound** reads CSS's `vh`, which in both browsers measured the sheet's area where the file holds no page rule. In a file whose page rules named sheets of several sizes, Chrome read it from the first sheet alone.
- **A reader's settings in Firefox,** with every page at one scale. Margins of none printed every page whole, its text on its shapes. A dialog's scale of one half parted the text from the layers, as it did in the file as written.
- **So in Firefox,** a page's text kept to its shapes only at a dialog's scale of 1, with every page at one width, under no page rule of the file.

**Modes and colours.**
- **Under a dark system,** a file holding a light and a dark mode drew dark on screen in both browsers, and printed light in both. One such file was the deck's English page file as the renderer writes it once it holds every mode ([project-kit#2815](https://github.com/aleskalfas/project-kit/issues/2815)), and one was written by hand. Firefox's system was set dark by its own settings, and Chrome's by its flag that forces a dark theme. Only the protocol's emulation of the dark signal, which the viewing step uses, printed dark.
- **Firefox, with its colours left to it,** darkened every text of the dark key's file for paper. That deck draws its own ground of `#151515`, and the title came near it, the heads faded. Asked to print the colours of the pages exactly, with CSS's `print-color-adjust`, Firefox kept every text's colour. Chrome kept the colours either way.
- **A dark page with no ground** was the figure with its ground taken out, its file naming `color-scheme: dark`. Asked to keep the whole document's colours, Chrome printed its own dark ground under the page, though backgrounds were off. Asked to keep only the pages' colours, Chrome printed no ground, as Firefox printed none either way. On white, that page's light caption faded.

**Presentation tools that write HTML** name the slide's sheet. reveal.js prints through a print style sheet whose sheet is the presentation's size. Its guide asks for the dialog's PDF, turned, with no margins and with background graphics. It says this has "only been confirmed to work in Google Chrome and Chromium". Marp's print rules name a sheet of the slide's size with no margin, and a break before each slide.

**Not reached:** printing in Safari or WebKit, Firefox and Chrome as shipped, a real printer, a real change of the system's setting. A page rule other than a size, a margin or an orientation, such as one that sets the header. Forced colours and a minimum font size, in print. A real site's pages, which no top drew when the test ran.

## Decision

**Each page of a printed page file lies whole on a sheet of its own, and every page of the file prints at one scale. The sheet is the reader's, and the file holds no page rule. The file asks the browser to print what it draws in its own colours, and picks no mode for print.**

### 1. Each page lies whole on a sheet of its own

- **A break before each page but the first,** and none inside a page. So no sheet's edge cuts a page, and no sheet holds two.
- **No gap.** The gap that parts pages on screen (DEC-020 point 4) is dropped in print.
- **No page runs on** across sheets, however tall it is. Point 2's scale fits it to one.

### 2. Every page of a file prints at one scale

- **One scale for the file.** It is the largest at which every page of the file fits the sheet's area whole, width and height alike.
- **The tallest page sets it** wherever the file's pages share one width. Each size has a file of its own (DEC-020 point 4). A deck's and a site's pages then share one, since each gets the top's width ([visual-communication:DEC-022-web-site-and-parts] point 3), and a figure holds one page.
- **A file whose pages differ in width,** which no top the foundations ship makes, prints at one scale too. Firefox may then part its text from its shapes.
- **Never above 1.** A page smaller than the sheet's area keeps its own size, as a page never grows on screen (DEC-020 point 4).
- **Where it lies.** Centred across the sheet's area, as a page lies in the middle of the window on screen, and at the top of the area.
- **Read from the sheet,** by CSS alone. The file holds no script (DEC-023 point 4).

### 3. The sheet is the reader's

- **The file names no sheet.** It holds no page rule, so no size, no margin and no orientation. The reader's dialog sets them, with its header and footer, and the dialog's scale.
- **A sheet of the page's own size** is the PDF export's, where a piece declares `pdf`. The PDF renderer draws each page as large as its frame (DEC-001 point 2, and the capability's page on outputs). A page file saved as a PDF has the reader's sheets. So does every print of a piece that declares `html` alone.

### 4. The file keeps its colours, and picks no mode for print

- **The colours of what it draws, exactly.** The file asks the browser to print its pages in their own colours, never adjusted for paper.
- **Nothing around its pages.** The browser's own ground prints as the reader's setting for backgrounds says. So a page with no ground lies on the bare sheet where that setting is off (DEC-023 point 7).
- **No mode picked for print.** The modes stay under the reader's signals, as the browser sets them when it prints (DEC-023 point 4). So a file of one mode prints that mode.
- **The rest as on screen:** the faces, the text as text, and the draw order. The file's rule for forced colours holds in print too (DEC-023 point 7), and it adds nothing for a reader's minimum size.

### 5. What a deck, a figure and a web page get

- **A deck:** each slide whole on a sheet of its own. On a turned sheet a slide fills more of it.
- **A figure:** its one page, whole on one sheet, shrunk only where it is larger than the sheet's area.
- **A web page,** as tall as its content (DEC-022 point 3): each page of the site whole on a sheet of its own, every page at the scale of the tallest. So a print shows each page of the design whole, as an overview, and a long page's text may print too small to read. The print reports no loss, since the sheet is the reader's, as the window is.

### 6. The renderer declares these choices

The scene sets none of them, so the renderer declares each beside how its pages lie on screen (DEC-001 point 2). They are the sheet left to the reader, the break, the gap dropped, the one scale, where a page lies on the sheet, and the colours kept.

### 7. What checks a print

- **A test on the file** holds what points 1 to 4 ask of it, as a test on the file holds how its pages lie on screen (DEC-020 points 4 and 5).
- **No check reads a print,** and the viewing step draws the screen alone. A print in each engine is a person's to look at, as the HTML page's record leaves printing to a person in a browser (DEC-020 point 5).

## Rationale

**Why a sheet of its own, and never a cut.** A cut slide is no slide, and in Firefox a cut parts the layers from the text below it. A break before each page, with a scale that fits it to one sheet, kept every page whole in each engine tried.

**Why one scale.** Firefox drew a page's text at another scale than its layers whenever two pages of the file printed at different widths. One scale for the file mended it, and on screen pages of one width share one scale too. The cost falls on a site with one long page, whose every page prints as small as that one. The choice rests on Firefox's fault with the page's form, below.

**Why the reader's sheet, though tools name the slide's.** A sheet of the page's own size would match the PDF export, and presentation tools name it. reveal.js confirms it only in Chromium's family. Here Firefox broke every page under each page rule tried: a size, a margin and an orientation alike. On a real printer the paper rarely matches a slide, so a named sheet meets one of another size there. Chrome shrank such a sheet whole onto the paper, and Firefox broke it. The PDF export gives the page's own sheet in every reader. The cost: a page file saved as a PDF has the reader's sheets and margins, unlike the export. This choice too rests on Firefox's fault with the page's form.

**Why a tall page prints small.** A site is a drawn design (DEC-022 point 1), and a print shows each of its pages whole. The cost is text too small to read: a phone's page of 5,232 px, the height DEC-022 measured, prints at about a fifth of its size on A4. A page run on across sheets parts its layers from its text in Firefox. Cutting it into bands that each fit a sheet would need the sheet's height when the renderer writes the file, and only the reader's dialog knows it. A shape a band's edge crosses would also lie twice, where each id lies once (DEC-020 point 4). DEC-022's bands serve a reviewer, who reads a page's smallest text in each image ([visual-communication:DEC-015-viewing-step-and-reviewer] point 5). A print has no such reader. The screen shows a tall page at its own size, as does its PDF export where the piece declares one.

**Why the colours of what it draws.** Firefox darkens text for paper, so a dark page's text came near its ground. Asking for the pages' colours as written kept them readable in each engine tried. Asking it of the whole document made Chrome print its own dark ground against the reader's setting. Asked of the pages alone, both engines leave that ground to the reader. The cost: a dark page with no ground prints its light text on the bare sheet, the case only a person catches (DEC-023 point 7).

**Why no mode for print.** Both browsers tried already print the light mode under a dark system, so a file that holds one prints light. A rule of the file would pick a mode by something other than a reader's signal, which DEC-023 point 4 refuses, to do what both engines do already. A file of dark alone prints dark, the piece's one mode, as its PDF export does.

**Why Firefox's scale fault stays open here.** In Firefox a dialog's scale other than 1 parts a page's text from its layers, in the file as written too. A page rule, and a page that is not the file's widest, met the same fault, as if through a scale Firefox applies itself. No rule of the file tried mended it, and the dialog's scale is the reader's. So the fault lies in how a page scales with no script, every length a share of its width (DEC-020 point 2). Mending it is a decision on that point, for a change of its own (Implications). Until then, the sheet left to the reader and the one scale keep a print clear of it wherever the dialog's scale is 1.

**Why no check reads a print.** A test on the file holds the rules on every machine. A print through the step would cost one print for each file and key, in Chrome alone, where the rules held. The faults no test sees lay in other engines, which the step does not run. So a person looks.

### Alternatives considered

- **A sheet of the page's own size, named in a page rule,** as reveal.js and Marp name it. Rejected. Firefox broke every page under it, and on a sheet of another size Chrome alone printed the page whole.
- **A turned sheet named in a page rule for pages wider than tall,** with the size left to the reader. Rejected. Firefox broke every page under it too.
- **Printing left to the browser,** with the PDF export named as the way to print. Rejected. Every engine tried cuts pages as the file stands, and Firefox breaks them. A reader who prints what they opened is never told of the PDF, and a piece that declares `html` alone has none.
- **Each page at its own scale,** each fitting its own sheet as closely as it can. Rejected. Firefox broke the pages' text once two printed at different widths.
- **A page taller than its sheet run on across sheets,** at the sheet's width, as a web page usually prints. Rejected. The cut parts the layers from the text in Firefox.
- **A tall page cut into bands,** each a sheet's height, as the viewing step cuts its images. Rejected. The band's height needs the reader's sheet, and a shape a cut crosses would lie twice.
- **The colours left to the browser.** Rejected. Firefox darkened a dark page's text to near its ground.
- **The whole document's colours kept,** not only the pages'. Rejected. Chrome then printed its own dark ground against the reader's setting for backgrounds.
- **The light mode named for print, where the file holds one.** Rejected for now. Both engines tried print it already, and a rule would pick a mode by no reader's signal. It comes back if an engine prints dark under a dark system.
- **A script that sets the sheet or the scale before printing.** Rejected. The file holds no script (DEC-023 point 4), and a script cannot learn the reader's sheet either, so it gains nothing over CSS.
- **A count of sheets in the viewing step,** one print for each file and key in Chrome. Rejected, for the reason above.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-020, point 4, "The pages follow each other down the document".** It comes to add that in print each page lies whole on a sheet of its own, with no gap, every page of the file at one scale, as this record's points 1 and 2 say.
  - **DEC-020, point 4, "A page shrinks and never grows".** It comes to add that in print a page shrinks to the one scale at which every page of the file fits the sheet, and never grows past its own size.
  - **DEC-023, point 7, "The file names its schemes".** It comes to add that in print the file asks the browser to keep the colours of its pages and nothing around them. So a page with no ground lies on the bare sheet where the reader prints no backgrounds.
- **Read against this answer, and left as they stand:**
  - The renderer declares how its pages lie (DEC-001 point 2), and it declares the print's choices beside them (point 6).
  - Every length is a share of the page's width (DEC-020 point 2). The one scale sets only the width a page prints at, and every length inside follows it.
  - The file sets no colour around its pages (DEC-020 point 4), and it asks nothing of the colours around them in print either.
  - A page clips no text (DEC-020 point 4), and the file clips nothing in print. A text a reader's minimum size grows past its page may meet a sheet's edge, which the browser cuts.
  - A person in a browser covers another engine and printing (DEC-020 point 5), and still looks at a print in each engine.
  - The HTML page's summary says a page shrinks with a narrow window and never grows (DEC-020), as it shrinks to a sheet and never grows.
  - What revisits the HTML page's record (DEC-020, Implications), which this record answers for how a file prints. The fault in Firefox's scale lies in DEC-020 point 2, which that list raises, and the bug named below takes it up.
  - The modes lie under the reader's signals, with no script (DEC-023 point 4), and a print reads them under the signals as the browser sets them.
  - The modes' summary and the heading of their point on schemes (DEC-023 point 7) speak of the screen.
  - What revisits the modes' record (DEC-023, Implications), which this record answers for printing in a dark mode.
  - An export run makes each format in each mode (DEC-006 point 7), so the PDF export of each mode stays the way to a sheet of the page's own size.
  - A site is a drawn design, its pages share one width, and the viewing step draws a tall page in bands (DEC-022 points 1, 3 and 7). The bands cut an image, never a print.
  - What the viewing step draws, each image large enough that a page's smallest text reads ([visual-communication:DEC-015-viewing-step-and-reviewer] point 5). A print is no image of the step.
  - A top whose pages have a physical size declares it, and an export maps it ([visual-communication:DEC-005-engine-and-plugins] point 5). No top declares one yet, and a print would not read one.
- **The Task that prints the page,** filed under [project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570) once this record is accepted, builds points 1 to 6 in the renderer. Its output changes, so the renderer's own version rises (DEC-005 point 9). The seam's version stays, since no plugin reads anything new (DEC-005 point 8). A test on the file holds the rules, and a test holds that every top the foundations ship gives a file's pages one width. The step's planted page stays in the screen's form, since the step draws the screen. The capability's page on outputs says, under the HTML renderer, how the page prints. It builds on the file's rules as #2815 left them. It closes with a person's print in Safari and in Firefox as shipped, of each key's file, on a sheet upright and turned, and with margins of none. The person also says what a dialog's scale other than 1 does.
- **#2815's body** asks no edit. It closed before this record, and the Task that prints the page builds on what it built.
- **[project-kit#2817](https://github.com/aleskalfas/project-kit/issues/2817)'s body** comes to say, in its criterion on printing, what the person checks there. They print the deck's page file, which holds light and dark, with the system set dark and then light. They say which mode printed, and whether each page lay whole on a sheet of its own with its text on its shapes. That is the real file of two modes, which the Task that prints the page cannot reach. Its Dependencies come to name that Task.
- **A bug is filed for the page's form** once this record is accepted. In Firefox a dialog's scale other than 1 parts a page's text from its layers, in the file as written too. That calls into question how a page scales with no script (DEC-020 point 2). Its mend may need a record of its own, which revisits this one.
- **Revisit this record** in any of these cases:
  - a browser as shipped cuts a page, parts its text from its shapes, or changes its colours in print
  - an engine prints a dark mode under a dark system
  - Firefox comes to print a page whole at a dialog's scale other than 1, or the page's form comes to keep its text on its shapes at any scale. A page rule, a turned sheet and each page at its own scale could then serve, and a site's pages would no longer print as small as its longest
  - a top comes to declare a physical size
  - a top gives the pages of one file different widths
  - a project comes to hand a site's pages out on paper
