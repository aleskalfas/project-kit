---
id: DEC-026
title: A printed page file sets its pages one after another, and cuts no slide
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when a reader prints a page file, its pages follow one another down the sheets, as they follow one another on screen. A sheet holds as many pages as fit. A page that does not fit the rest of a sheet moves whole to the next one. A deck's slide prints whole inside its keyline, the thin line that shows where it ends, and is never cut. A site's page taller than a sheet runs on across sheets. The backdrop, the tinted ground around the slides on screen, does not print. The sheet is the reader's: the file sets no size, margin or orientation. The file asks the browser to print its pages in their own colours, and picks no mode for print.

## Context

[project-kit#2824](https://github.com/aleskalfas/project-kit/issues/2824) asks what a printed page file is.
- **The HTML page's record** lists printing among what its test did not reach. It says a fault there revisits it ([visual-communication:DEC-020-html-page-drawing], Context and Implications).
- **The record of modes** lists printing in a dark mode the same way ([visual-communication:DEC-023-html-page-modes], Context and Implications).
- **The record of the backdrop** keeps its keyline and backdrop off a print until this record decides ([visual-communication:DEC-031-html-page-backdrop] point 4).

The fault came from the change that drew the page through a browser ([project-kit#2804](https://github.com/aleskalfas/project-kit/pull/2804), "Other engines" and "A person's look"):
- **Printed, the deck's page file runs its pages on** with no break, so a sheet's edge cuts a page.
- **In Firefox 157 under Playwright,** page 3's layers part from its text below the cut, each text one row below its own box.
- **Chrome 157's PDF** also cuts page 3 across two sheets, and keeps its text on its shapes. WebKit 27.2 cannot print to PDF under Playwright.
- **Whoever maintains the capability,** looking in Safari and Firefox as shipped, saw pages cut, and the print broken from page 3 on. The look did not say whether Safari parted text from shapes.

On 9 November 2026 whoever maintains the capability chose a compact print, over a sheet for each page ([project-kit#2824](https://github.com/aleskalfas/project-kit/issues/2824)). Pages follow one another on a sheet, each slide framed by a thin line. No slide is cut, and a page taller than a sheet runs on.

The terms used below:
- A *sheet* is one leaf of a print: a side of paper, or its like in a PDF the browser saves. Its *area* is the part inside its margins. A sheet is *upright* when it is taller than wide, and *turned* when it is wider than tall.
- A *page rule* is a rule of the file that sets the sheet: CSS's `@page`, naming the sheet's size, its margins or its orientation.
- The *dialog's scale* is the scale a reader sets in the print dialog, 1 unless they change it.
- A *fixed page*, its *keyline*, the *backdrop* and the *gutter* are as DEC-031 defines them. A deck's slide is a fixed page, and a site's page is none.

### What the test showed

The test took the showcase deck's page files, the deck of the repository the capability is authored in: four slides of 1,280 by 720 px. It added the figure `sockets`, 960 by 488 px. It also built a page of 1,280 by 2,880 px, standing for a site's page as tall as its content. It ran on one Mac, through Playwright 1.64.1, and its code is thrown away.
- **Chrome 157** printed through the browser protocol's print to PDF, at the dialog's margins of 0.4 in.
- **Firefox 157,** as Playwright builds it, printed through `window.print()` to its printer that saves a PDF, with no dialog shown.
- **Neither printed backgrounds,** as their dialogs default. Ghostscript drew each sheet for a look.

**Firefox's faults.** In each, a page's text lay at another scale than its layers, off its boxes:
- below a sheet's edge that cut the page, in the file with no print rule
- under each page rule tried: a size, a margin of none, a turned sheet
- at a dialog's scale other than 1, in the file with no print rule too
- once two pages of one file printed at different widths.

Chrome kept each page's text on its shapes in every case. A page rule naming the page's size gave each slide a sheet of 960 by 540 pt there, as in the PDF export.

**A bound on a page's height,** CSS's `vh`, measured the sheet's area in both browsers where the file held no page rule. A page shrunk by it to fit one sheet kept its text on its shapes in both, the tall page among them.

**The compact print,** run after that choice. Its file:
- asked to keep each page on one sheet, by CSS's `break-inside: avoid`
- kept the screen's gap between pages
- held no page rule
- kept each page's colours.

What it gave:
- **The deck.** On A4 upright, two slides lay on each sheet, four on two sheets, in both browsers. Each kept its text on its shapes. On Letter turned, Chrome gave each slide a sheet of its own.
- **The figure and the tall page,** in one file after the deck's slides. The figure did not fit the rest of the second sheet, and moved whole to the third. The tall page started the fourth sheet and ran on to the fifth, in both browsers.
- **The cut in the tall page.** Chrome kept its text on its shapes. In Firefox, below the cut, each text lay a row off its box, as #2804 found.

**The keyline in print,** tried four ways:
- **An outline outside the page,** as on screen, lost its sides where the page filled the area's width. It lost its top where the page began a sheet. Chrome drew that top as a stray line at the foot of the sheet before.
- **An outline just inside the page's edge** lay under the page's layers, and did not show.
- **A line drawn over the page's edge** printed whole in both browsers, over the page's outermost row.
- **A border around the page,** the page narrowed by a few px to leave it room, printed whole on every side in both browsers. The page and its border moved to the next sheet together.

**Modes and colours.**
- **Under a dark system,** a file holding a light and a dark mode drew dark on screen in both browsers, and printed light in both. One file was the deck's English page file holding every mode ([project-kit#2815](https://github.com/aleskalfas/project-kit/issues/2815)). Only the protocol's emulation of the dark signal, which the viewing step uses, printed dark.
- **Firefox, with its colours left to it,** darkened the dark key's text for paper until the title came near its ground. Asked to print the pages' colours exactly, by CSS's `print-color-adjust`, it kept them. Chrome kept them either way.
- **Asked to keep the whole document's colours,** Chrome printed its own dark ground under a dark page with no ground, though backgrounds were off. Asked to keep only the pages' colours, it printed none.

**Presentation tools that write HTML** name the slide's sheet. reveal.js names the presentation's size, and says this has "only been confirmed to work in Google Chrome and Chromium". Marp names a sheet of the slide's size with no margin.

**Not reached:**
- printing in Safari or WebKit, Firefox and Chrome as shipped, a real printer, a real change of the system's setting
- a print with backgrounds turned on
- forced colours, more contrast and a minimum font size, in print
- a file the renderer wrote with DEC-031's keyline, and a real site's pages.

## Decision

**A printed page file sets its pages one after another, and moves a page that does not fit whole to the next sheet. A fixed page fits one sheet, inside its keyline. The sheet is the reader's. The file keeps its pages' colours, and picks no mode for print.**

### 1. Pages follow one another down the sheets

- **As on screen.** Each page follows the one before it, in the middle of the sheet's area, after the gap the renderer declares (DEC-020 point 4).
- **A sheet holds as many pages as fit.** No break is forced before a page.
- **Each page kept whole where it fits.** The file asks the browser to keep each page on one sheet. So a page that does not fit the rest of a sheet moves whole to the next.
- **A page taller than a sheet's area runs on** across sheets, cut where each sheet ends. Point 2 keeps a fixed page from being one.

### 2. A page prints at most the sheet's width, and a fixed page fits one sheet

- **The sheet's area is the window.** A page shrinks to at most the area's width, and never grows past its own size, as in a narrow window (DEC-020 point 4).
- **A fixed page fits one sheet.** It also shrinks to at most the area's height, keeping its proportions. So no slide is cut, whatever its shape and the sheet's.
- **Any other page has no height bound.** A site's page or a figure taller than the area runs on (point 1).
- **No gutter in print.** The gutter is the backdrop's (DEC-031 point 4), and a print has no backdrop.
- **One scale where a file's pages share a width.** A deck's slides share one shape, and a site's pages take the top's width ([visual-communication:DEC-022-web-site-and-parts] point 3). A page alone is one page. Each of these prints at one scale.
- **Pages a top's slot declares** may differ in width, since the parts that place them give their size (DEC-031 point 2). Each prints at its own scale, by this point's rule. Firefox may then part their text from their shapes (Context).

### 3. A fixed page prints inside its keyline

- **The keyline prints, the backdrop does not.** Each fixed page prints inside its keyline (DEC-031 points 1 and 2), so a slide's edge shows on the sheet. The sheet around and between the pages stays bare.
- **Around the page, never on it.** The keyline lies outside the page's drawing, as on screen. In print the keyline and the page form one box, so the two move to a sheet together.
- **Room for it.** The page's drawing shrinks by the keyline's width, so the keyline lies inside the sheet's area. The drawing keeps its proportions.
- **Its colour as on screen.** It takes the mix of the browser's colours DEC-031 point 3 sets, under more contrast and forced colours too. Point 5 keeps that colour on paper.
- **It reads on paper.** Its share keeps DEC-031's floor of 3 to 1 against a white sheet too. A mix near half, as DEC-031 computed it, reaches about 3.7 to 1 there, in light and in dark.
- **In a dark mode,** the page's dark ground inside the keyline also sets it apart from the white sheet. That holds where the keyline takes the browser's text colour whole, under more contrast.
- **Inside the keyline,** a fixed page lies on the browser's own ground, as on screen (DEC-031 point 3).
- **A page that is no fixed page** prints with no keyline, as on screen: a figure, and a site's page.

### 4. The sheet is the reader's

- **The file names no sheet.** It holds no page rule, so no size, no margin and no orientation. The reader's dialog sets them, with its header, its footer and its scale.
- **A sheet of the page's own size** is the PDF export's, where a piece declares `pdf` ([visual-communication:DEC-001-visual-communication-discipline] point 3). A page file saved as a PDF has the reader's sheets.

### 5. The file keeps its colours, and picks no mode for print

- **Its pages' colours, exactly.** The file asks the browser to print each page, its ground and its keyline in their own colours, never adjusted for paper.
- **Nothing around its pages.** The browser's ground around them prints as the reader's setting for backgrounds says. So a page that is no fixed page, and has no ground, lies on the bare sheet where that setting is off (DEC-023 point 7).
- **No mode picked for print.** The modes stay under the reader's signals, as the browser sets them when it prints (DEC-023 point 4). A file of one mode prints that mode.
- **The rest as on screen:** the faces, the text as text, the draw order, and the rule for forced colours (DEC-023 point 7).

### 6. The renderer declares these choices

The scene sets none of them, so the renderer declares each beside how its pages lie on screen (DEC-001 point 2).
- **Values it declares:** the keyline's width and its shares, those DEC-031 point 3 sets for the screen.
- **Rules it names, with no value to set:** each rule of points 1 to 5.

### 7. What checks a print

- **A test on the file** holds what points 1 to 5 ask of it. A test holds how its pages lie on screen the same way (DEC-020 point 5).
- **No check reads a print.** The viewing step draws the screen alone, and a person looks at a print in each browser (DEC-020 point 5).
- **In print alone.** Every rule here holds in print alone. So the screen's rules, which the step's measures and images rest on, stay as DEC-020 and DEC-031 have them.

## Rationale

**Why one page after another.** A deck printed as a handout takes fewer sheets: two 16:9 slides share A4 upright. The keyline keeps each slide's edge on the bare sheet, so two slides on one sheet still read as two. On screen too, the slides follow one another, each in its keyline (DEC-031 point 1).

**Why no slide is cut.** A cut slide is no slide, and in Firefox a cut parts the text from the layers below it. Moving a slide whole to the next sheet kept it whole in both browsers. The bound on its height keeps a slide of any shape on one sheet, such as a 4:3 slide on a turned sheet.

**Why the fixed page draws that line.** A fixed page's top sets its height, so it is a frame designed whole, as a slide is. A page that asks for its own height may be of any length, so it runs on. A figure is one, so a figure taller than a sheet runs on too.

**Why a site's page runs on.** Shrunk to one sheet, a phone's page of 5,232 px, the height DEC-022 measured, prints at about a fifth of its size on A4. Its text could not be read.
- **Run on,** a site's page keeps its width's scale: the area's width over the page's width. A page 1,280 px wide prints at about 0.56 of its size on A4 upright.
- **The cost:** in Firefox, the text below each cut lies off its shapes.

**Why the sheet's width.** The screen's rule gives it, with the sheet's area as the window. Print adds only the bound on a fixed page's height. Pages of one width kept Firefox's text on its shapes.

**Why the keyline around the page.** A renderer adds nothing to a page, and may show only what lies around it (DEC-001 point 2).
- **Over the page's edge,** a line would cover the page's outermost row, which changes a piece's look.
- **An outline outside the page** lost its sides and tops at the edge of the area.
- **A border,** with the page narrowed to leave it room, printed whole. The cost: in print a fixed page is a few px narrower than the area.

**Why a border in print, an outline on screen.** DEC-031 rejects a border for the screen: the document would scroll sideways, and a page's proportions would move. Neither arises in print, where the page's drawing shrinks to leave the border room. On screen an outline takes no room, so the step's measures stand. Changing the screen is DEC-031's to revisit.

**Why the backdrop stays on screen.** On paper the bare sheet already sets a page apart, and the keyline marks its edge. A backdrop would print only where the reader turned backgrounds on.

**Why the reader's sheet, though tools name the slide's.** Firefox broke every page under each page rule tried. On a real printer the paper rarely matches a slide, and on a sheet of another size Chrome alone printed the page whole. The PDF export gives the page's own sheet in every reader. Its renderer draws each page as large as its frame (the capability's page on outputs).

**Why the pages' colours.** Firefox darkens text for paper, so a dark page's text came near its ground. Asked of the pages alone, both browsers keep their colours and leave the browser's ground around them to the reader. The costs:
- A page's own ground prints even where the reader turned backgrounds off, so a dark slide prints as solid ink.
- A page that is no fixed page, and has no ground, prints its light text on the bare sheet. Only a person catches it (DEC-023 point 7).

**Why no mode for print.** Both browsers tried already print the light mode under a dark system. A rule of the file would pick a mode by something other than a reader's signal, which DEC-023 point 4 refuses.

**Why Firefox's scale fault stays open.** At a dialog's scale other than 1, Firefox parts a page's text from its layers, in the file with no print rule too. No rule of the file mended it, and the dialog's scale is the reader's. So the fault lies in how a page scales with no script (DEC-020 point 2), and a bug takes it up (Implications).

**Why no check reads a print.** A test on the file holds the rules on every machine. A print through the step would run in Chromium alone, where every rule tried held. The faults seen lay in Firefox, which the step does not run, so a person looks.

### Alternatives considered

- **Each page whole on a sheet of its own,** every page shrunk to fit the sheet's area. Rejected. A deck takes a sheet for each slide, and a long page prints too small to read.
- **The pages run on with no print rule,** as #2804 tested them. Rejected. A sheet's edge cuts a slide, and Firefox parts its text from its layers.
- **A slide taller than a sheet run on,** with no bound on its height. Rejected. A slide of 4:3 on a turned sheet, or a tall slide on an upright one, would be cut.
- **A tall site's page cut into bands,** each a sheet's height. Rejected. A shape a band's edge crosses would lie twice, where each id lies once (DEC-020 point 4). A band is no page a reader asked for either.
- **A sheet of the page's own size, or a turned sheet, named in a page rule,** as reveal.js and Marp name it. Rejected. Firefox broke every page under each.
- **Printing left to the browser,** with the PDF export named as the way to print. Rejected. Each browser cuts pages with no print rule. A piece that declares `html` alone has no PDF.
- **No keyline in print.** Rejected. A white slide on a white sheet has no edge, and two slides on one sheet run together.
- **The keyline as an outline outside the page,** as on screen. Rejected. It lost its sides and tops where a page met the edge of the sheet's area.
- **The keyline drawn over the page's edge.** Rejected. It covers the page's outermost row, which a renderer may not change (DEC-001 point 2).
- **The backdrop printed too.** Rejected, for the reason above.
- **The colours left to the browser.** Rejected. Firefox darkened a dark page's text to near its ground.
- **The whole document's colours kept,** not only the pages'. Rejected. Chrome then printed its own dark ground against the reader's setting for backgrounds.
- **The light mode named for print.** Rejected for now. Both browsers tried print it already, and it comes back if a browser prints dark under a dark system.
- **A script that sets the sheet or the scale.** Rejected. The file holds no script (DEC-023 point 4), and CSS already reads the sheet's area.
- **A count of sheets in the viewing step.** Rejected, for the reason above.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-020 point 4, "The pages follow each other down the document".** It comes to add that in print they follow each other down the sheets, with no backdrop, as points 1 and 3 say. A page that fits a sheet is kept whole.
  - **DEC-020 point 4, "A page shrinks and never grows".** It comes to add that in print a page shrinks to fit the sheet's width (point 2). A fixed page shrinks to fit its height too.
  - **DEC-023 point 7, "The file names its schemes".** It comes to add that in print the file asks the browser to keep its pages' colours, and nothing around them, as point 5 says.
  - **DEC-031 point 3, "The keyline reads".** It comes to add that in print the keyline's share keeps the floor against a white sheet too (point 3).
  - **DEC-031 point 3, "Forced colours".** "CSS's outline" comes to say an outline on screen and a border in print, each of a kind a browser keeps there.
  - **DEC-031 point 4, "The keyline takes no room".** It comes to say this of the screen. In print the keyline and the page form one box, and the page's drawing shrinks by the keyline's width (point 3).
  - **DEC-031 point 4, "On screen alone".** It comes to say that the backdrop, the gutter and the room the gutter leaves are a screen's alone. In print a fixed page lies inside its keyline, as point 3 says.
  - **DEC-031 point 5, "What reads them instead".** "A keyline that takes no room" comes to say on screen, and the test comes to hold the print's keyline too.
  - **DEC-031's Rationale, "Why an outline", and its alternative "A border, or a shadow alone, as the keyline".** Each comes to speak of the screen, since in print the keyline is a border.
- **Read against this answer, and left as they stand:**
  - The renderer adds nothing to a page, and declares how its pages lie and what lies around them (DEC-001 point 2). The keyline lies around a page in print too.
  - Every length is a share of the page's width (DEC-020 point 2), so a page scales to the sheet with no script. It stands until the bug below is mended.
  - A page clips no text (DEC-020 point 4), and the file clips nothing in print.
  - A person in a browser covers printing (DEC-020 point 5).
  - What revisits DEC-020, DEC-023 and DEC-031 (their Implications), which this record answers for printing. Firefox's scale fault stays open, for the bug below.
  - No rule switches the layout by the window's width ([visual-communication:DEC-021-size-and-shape] point 8, DEC-023 point 5). The print's rules switch nothing by a window's width.
  - A site's page asks for no height, so it is no fixed page (DEC-022 point 3, DEC-031 point 2). The step's bands cut an image, never a print (DEC-022 point 7).
  - The modes lie under the reader's signals, with no script (DEC-023 point 4).
  - Whether a portal's pages need a keyline, which DEC-031 leaves open. On paper, two of them on one sheet may run together.
  - An export run makes each format in each mode ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7). So the PDF export stays the way to a sheet of the page's own size.
- **The Task that prints the page,** filed under [project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570) once this record is accepted, builds points 1 to 6 in the renderer.
  - Its output changes, so the renderer's own version rises ([visual-communication:DEC-005-engine-and-plugins] point 9). The seam's version stays, since no plugin reads anything new (DEC-005 point 8).
  - It builds on the keyline as the Task that builds DEC-031 leaves it, and on the file's modes as #2815 left them.
  - A test on the file holds the rules. The capability's page on outputs says, under the HTML renderer, how the page prints.
  - It closes with a person's print, which #2851 takes.
- **[project-kit#2851](https://github.com/aleskalfas/project-kit/issues/2851)'s body** comes to say, in its criterion on printing, what the person checks.
  - They print the deck's page file, which holds light and dark, in Safari, Firefox and Chrome as shipped, on a sheet upright and turned.
  - They print with the system set dark, then light, and say which mode printed. They print once with backgrounds on.
  - They say whether each slide lay whole inside its keyline, with its text on its shapes.
  - Its Dependencies come to name the Task that prints the page.
- **A bug is filed for the page's form** once this record is accepted. Its mend may need a record of its own. That record would revisit DEC-020 point 2, and this record where print rests on it.
  - **What it takes up:** in Firefox, a page's text parts from its layers below a cut, and at a dialog's scale other than 1. It parts too where a file's pages print at different widths.
  - **Why the page's form:** these call into question how a page scales with no script (DEC-020 point 2).
- **Revisit this record** in any of these cases:
  - a browser as shipped cuts a page that fits a sheet, or changes its colours in print
  - a keyline fades or is lost on paper
  - a browser prints a dark mode under a dark system
  - Firefox comes to keep a page's text on its shapes across a cut, at any dialog's scale, or under a page rule
  - a top comes to declare a physical size
  - the line between fixed pages and the rest moves (DEC-031 point 2)
  - a project comes to hand a site's pages out on paper.
