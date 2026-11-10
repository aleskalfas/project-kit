---
id: DEC-026
title: A printed page file sets its pages one after another, each whole where it fits a sheet
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when a reader prints a page file, its pages follow one another down the sheets, as they follow one another on screen. A sheet holds as many pages as fit. A page that does not fit the rest of a sheet moves whole to the next one, and a page taller than a sheet runs on across sheets. Such a page is to break between lines of text, never through one, and a record of its own decides how. Until then the browser picks where it breaks. Only a fixed page, such as a deck's slide, prints inside its keyline, the thin line that shows where it ends on screen. A figure and a web page print with none. The backdrop, the tinted ground around the slides on screen, does not print. The sheet is the reader's: the file sets no size, margin or orientation. Each page prints in its own colours, and the file picks no mode for print. For example, a deck's slides printed on A4 sheets held upright lie two to a sheet, each whole inside its thin line.

## Context

[project-kit#2824](https://github.com/aleskalfas/project-kit/issues/2824) asks what a printed page file is. Three records leave it open:
- **The HTML page's record** lists printing among what its test did not reach, and is revisited where a fault shows there ([visual-communication:DEC-020-html-page-drawing], Context and Implications).
- **The record of modes** lists printing in a dark mode the same way ([visual-communication:DEC-023-html-page-modes], Context and Implications).
- **The record of the backdrop** keeps its keyline and backdrop off a print until this record decides ([visual-communication:DEC-031-html-page-backdrop] point 4). The renderer writes them for a screen alone, so a print holds neither.

The fault came from the change that drew the page through a browser ([project-kit#2804](https://github.com/aleskalfas/project-kit/pull/2804), "Other engines" and "A person's look"). Printed, the page file of the showcase deck, the deck of the repository the capability is authored in, ran its pages on with no break, so a sheet's edge cut a page, and in Firefox the text below the cut parted from its shapes. The runs behind this record are the evidence of its pull request ([project-kit#2850](https://github.com/aleskalfas/project-kit/pull/2850)).

On 9 November 2026 whoever maintains the capability chose a compact print, over a sheet for each page, from a mock-up of a deck's slides on A4 sheets. [The comment on #2824 that records it](https://github.com/aleskalfas/project-kit/issues/2824#issuecomment-6740449104) reads: "Pages print compact: they follow each other on a sheet, so several fit on one. Each page is framed by a thin line, and a page that would be cut at a sheet's foot starts the next sheet whole. A page taller than a sheet still runs on."

Later that day, from a picture of this record's print, that person decided two things more, which [a comment on #2824](https://github.com/aleskalfas/project-kit/issues/2824#issuecomment-6753276666) records:
- **The thin line.** Asked whether a figure and a web page get the thin line on paper too, or only a deck's slides, they answered "slides only".
- **A break.** Where the picture cut a heading's letters at a sheet's foot: "A page that runs on across sheets must break between lines, never through one."

This record reads the thin line as the keyline DEC-031 draws around a fixed page on screen (point 1), and "slides only" as fixed pages, the pages DEC-031 draws it around (point 2).

The terms used below:
- A *sheet* is one leaf of a print: a side of paper, or its like in a PDF the browser saves. Its *area* is the part inside its margins.
- A *page rule* is a rule of the file that sets the sheet: CSS's `@page`, naming the sheet's size, its margins or its orientation.
- A *fixed page*, its *keyline*, the *backdrop* and the *gutter* are as DEC-031 defines them. A deck's slide is a fixed page, and a site's page is none.

## Decision

**A printed page file sets its pages one after another, and moves a page that does not fit the rest of a sheet whole to the next. A page taller than a sheet runs on. It is to break between a text's lines, never through one, and until a record of its own decides how, the browser picks where. Only a fixed page prints inside its keyline. The sheet is the reader's. Each page prints on the browser's ground in its own colours, and the file picks no mode for print.**

### 1. Pages follow one another down the sheets

- **As on screen.** Each page follows the one before it, in the middle of the sheet's area, after the gap the renderer declares (DEC-020 point 4).
- **A sheet holds as many pages as fit.** No break is forced before a page.
- **Each page kept whole where it fits.** The file asks the browser to keep each page on one sheet. So a page that does not fit the rest of a sheet moves whole to the next.
- **A page taller than a sheet's area runs on** across sheets. That holds for a fixed page too, since point 2 sets no bound on a page's height.
- **It is to break between a text's lines, never through one,** as whoever maintains the capability asked. A record of its own, the *record on breaks*, decides how (Implications).
- **Until then the browser picks where it breaks.** The file holds no rule on it, since none reaches the renderer's absolutely placed lines and layers (Rationale). So a break may cut a line of text, or move it off the place DEC-020 point 2 gives it, and cut or lose a shape. This record accepts that until the record on breaks lands.

### 2. A page prints at most the sheet's width

- **The sheet's area is the window.** A page shrinks to at most the area's width, and never grows past its own size, as in a narrow window (DEC-020 point 4).
- **No bound on its height.** A page keeps the scale its width gives it, however tall it is, and runs on (point 1).
- **No gutter in print.** The gutter is the backdrop's (DEC-031 point 4), and a print has no backdrop.
- **Each page by its own width.** Pages of one width print at one scale. Pages a top's slot declares may differ in width, since the parts that place them give their size (DEC-031 point 2), and each prints at its own scale.

### 3. A fixed page prints inside its keyline

- **The keyline prints, the backdrop does not.** Each fixed page prints inside its keyline (DEC-031 points 1 and 2), so a slide's edge shows on the sheet. No backdrop prints around or between the pages.
- **Around the page, never on it.** The keyline lies outside the page's drawing, as on screen. In print it is the page's own border, so the keyline and the page form one box, and the two move to a sheet together. It adds no element (DEC-031 point 4).
- **Room for it.** The area, less the keyline on each side, is a fixed page's window. So the keyline lies inside the sheet's area, and the page's drawing shrinks only where it would not fit, keeping its proportions.
- **Its colour as on screen.** It takes the mix of the browser's colours DEC-031 point 3 sets, under more contrast and forced colours too. Point 5 keeps that colour on paper.
- **It reads on paper.** Its share keeps DEC-031's floor of 3 to 1 against a white sheet too, in light and in dark. Under more contrast, where the keyline takes the browser's text colour whole, a dark page's keyline is white on a white sheet, and the page's own ground marks its edge there.
- **Only a fixed page.** A deck's slide and a handout's page print inside their keylines. A page that is no fixed page prints with no keyline, as on screen: a figure, and a site's page.

### 4. The sheet is the reader's

- **The file names no sheet.** It holds no page rule, so no size, no margin and no orientation. The reader's print dialog sets them, with its header, its footer and its scale.
- **A sheet of the page's own size** is the PDF export's, where a piece declares `pdf` ([visual-communication:DEC-001-visual-communication-discipline] point 3). A page file saved as a PDF has the reader's sheets.

### 5. Each page prints on the browser's ground, in its own colours

- **On the browser's ground.** Each page prints on the browser's ground colour, as it lies on screen (DEC-023 point 7). A page with a ground of its own covers it.
- **Its colours, exactly.** The file asks the browser to print each page, that ground and a fixed page's keyline in their own colours, never adjusted for paper. So a page's text keeps the ground it was drawn against, even where the reader turned backgrounds off.
- **Nothing around its pages.** The sheet around and between them prints as the reader's setting for backgrounds says, and stays bare where that setting is off.
- **No mode picked for print.** The modes stay under the reader's signals, as the browser sets them when it prints (DEC-023 point 4). A file of one mode prints that mode.
- **The rest as on screen:** the faces, the text as text, the draw order, and the rule for forced colours (DEC-023 point 7).

### 6. The renderer declares these choices

The scene sets none of them, so the renderer declares each beside how its pages lie on screen (DEC-001 point 2).
- **Values it declares:** none of print's own. The keyline's width and its share are the ones DEC-031 point 3 declares, read on screen and in print alike, so the two never drift apart. That one share meets the floor against the backdrop, the browser's ground and a white sheet. No project setting changes them.
- **Rules it names, with no value to set:** each rule of points 1 to 5 the file holds. Where a page that runs on breaks is the record on breaks' (point 1).

### 7. What checks a print

- **A test on the file** holds what points 1 to 5 ask of it, all but where a page that runs on breaks, as a test holds how its pages lie on screen (DEC-020 point 5). Where the machine has the step's browser, the test may also print the file there and count its sheets. That print lies in the test, never in the step's shipped code, and it asserts no mode.
- **The viewing step reads no print.** It draws the screen alone, and a person looks at a print in each browser (DEC-020 point 5). Safari gets the same rules, and that person's print is its only check.
- **In print alone.** Every rule here holds in print alone. So the screen's rules, which the step's measures and images rest on, stay as DEC-020 and DEC-031 have them.

## Rationale

**Why one page after another.** It is the maintainer's choice: "Pages print compact". A deck printed as a handout takes fewer sheets than with a sheet for each slide. The keyline keeps each slide's edge on the bare sheet, so two slides on one sheet still read as two, as the slides follow one another on screen, each in its keyline (DEC-031 point 1).

**Why a page moves whole.** A page cut at a sheet's foot reads as two halves, and in Firefox a cut parts the text from the shapes below it.

**Why a tall page runs on, a slide too.** It is the maintainer's choice: "A page taller than a sheet still runs on." Shrunk to one sheet, a site's tall page prints too small to read. Run on, a page keeps the scale its width gives it.
- **A slide needs no bound.** A 16:9 slide fits the area of A4 and Letter either way up. A bound on a fixed page's height would reach only a slide of another shape, and would shrink a tall fixed page as far as it would a site's page.
- **The cost:** a page taller than the area breaks where the sheet ends, a figure, a site's page and a slide of another shape alike. The reader can print it on a sheet taller than wide, or take the PDF export where the piece declares `pdf`.

**Why the break waits for the record on breaks.** CSS's rules on breaks, which keep a block whole, a heading with what follows, or a paragraph's lines together, act on boxes in the document's flow. Every text, line and layer of the renderer's page is placed absolutely, where the engine put it (DEC-020 points 2 and 3). So no rule of the file chooses the break. What mends it changes how the renderer writes a page that runs on, or what the scene tells it. That is DEC-020's to decide, so the record on breaks takes it up, not a rule of print.

**Why the sheet's width.** The screen's rule gives it, with the sheet's area as the window, and print adds nothing to that rule. The cost: pages a slot declares at different widths print at different scales, where Firefox may part their text from their shapes.

**Why the keyline around a fixed page alone.** It is the maintainer's choice: "slides only". This record reads it as fixed pages, so the fact on the scene's root that names them means the same on screen and on paper (DEC-031 point 2). A line around a figure or a site's page would show on paper a look the screen does not have, and would come through DEC-031's own revisit, for both media together. The cost: two of a site's pages on one sheet are told apart by the gap between them alone.

**Why the keyline is a border in print.** A renderer adds nothing to a page, and may show only what lies around it (DEC-001 point 2). So the keyline lies around the page's drawing, never over its edge. An outline outside the page, as on screen, was lost at the edges of the sheet's area. A border, with the page's drawing narrowed to leave it room, prints whole and moves to a sheet with its page. The cost: in print a fixed page is narrower than the area by its keyline. DEC-031 rejects a border on screen, where the document would scroll sideways and a page's proportions would move. Neither arises in print, where the page's drawing shrinks to leave it room.

**Why the backdrop stays on screen.** On paper the bare sheet already sets a page apart, and the keyline marks its edge. A backdrop would print only where the reader turned backgrounds on.

**Why the reader's sheet, though presentation tools name the slide's.** Firefox broke every page under each page rule tried. On a real printer the paper rarely matches a slide. The PDF export gives the page's own sheet in every reader.

**Why each page on the browser's ground, in its own colours.** A page's colours belong to the piece, and a renderer draws the scene's colours and lets no medium change them (DEC-001 point 2). Left to adjust colours for paper, Firefox darkened a dark page's text toward its ground. A page with no ground of its own was drawn against the browser's ground. Left to the bare sheet, a file of a dark mode alone would print its light text on white paper.
- **The one setting of a reader's it overrides.** Every other rule of the page follows the reader's own settings: forced colours, more contrast, the scheme. Here a page's colours print even where the reader turned backgrounds off. The reader's setting still governs the sheet around the pages, which lies outside every page.
- **The cost:** a dark page prints as solid ink, its ground included, even where the reader turned backgrounds off.

**Why no mode for print.** A rule of the file would pick a mode by something other than a reader's signal, which DEC-023 point 4 refuses. The browsers tried print the light mode under a dark system already. An export run makes each format in each mode ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7), so the PDF export stays the way to a print in a mode the browser does not print.

**Why Firefox's faults stay open.** Firefox parts a page's text from its shapes in cases no rule of the file reaches, such as a scale the reader sets in the print dialog. So a bug takes them up by what was seen (Implications).

**Why the step reads no print.** A test on the file holds the rules on every machine. A print through the step would run in Chromium alone, where every rule of this record held but where a page that runs on breaks, which is the record on breaks' (point 1). Firefox's faults lie where the step does not run, so a person looks. The test asserts no mode, since the step's emulated dark signal printed dark where a real dark system printed light.

### Alternatives considered

- **Each page whole on a sheet of its own,** every page shrunk to fit the sheet's area. Rejected. A deck takes a sheet for each slide, and a long page prints too small to read.
- **The pages run on with no print rule,** as #2804 tested them. Rejected. A sheet's edge cuts a slide, and Firefox parts its text from its shapes.
- **A fixed page shrunk to fit one sheet's height too.** Rejected. It goes past the maintainer's "A page taller than a sheet still runs on". No 16:9 slide needs it on A4 or Letter, and it would shrink a tall fixed page past reading.
- **A tall page cut into bands,** each a sheet's height. Rejected. A shape a band's edge crosses would lie twice, where each id lies once (DEC-020 point 4). A band is no page a reader asked for either. Parts cut where no element crosses are another design, for the record on breaks to weigh.
- **A sheet named in a page rule,** such as one of the page's own size. Rejected. Firefox broke every page under each page rule tried.
- **Printing left to the browser,** with the PDF export named as the way to print. Rejected. Each browser cuts pages with no print rule. A piece that declares `html` alone has no PDF.
- **No keyline in print.** Rejected. A white slide on a white sheet has no edge, and two slides on one sheet run together.
- **A thin line around every page in print,** a figure's and a site's too. Rejected by the maintainer: "slides only".
- **A text kept whole by a rule of the file,** such as `break-inside: avoid` on each text. Rejected. It gives no hold on an absolutely placed box.
- **The keyline as an outline outside the page,** as on screen. Rejected. It was lost where a page met the edge of the sheet's area.
- **The keyline drawn over the page's edge.** Rejected. It covers the page's outermost row of pixels, which a renderer may not change (DEC-001 point 2).
- **The backdrop printed too.** Rejected, for the reason above.
- **The colours left to the browser.** Rejected. A browser may darken a dark page's text toward its ground.
- **A page with no ground left on the bare sheet.** Rejected. A file of a dark mode alone would print its light text on white paper.
- **The whole document's colours kept,** not only the pages'. Rejected. The browser's own ground then prints around the pages against the reader's setting for backgrounds.
- **The light mode named for print.** Rejected for now. The browsers tried print it already, and it comes back if a browser prints dark under a dark system.
- **A script that sets the sheet or the scale.** Rejected. The file holds no script (DEC-023 point 4), and CSS already reads the sheet's area.
- **A count of sheets in the viewing step.** Rejected, for the reason above.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-020 point 4, "The pages follow each other down the document".** It comes to add that in print they follow each other down the sheets, with no backdrop, as this record's points 1 and 3 say. A page that fits a sheet is kept whole, and a page taller than a sheet runs on.
  - **DEC-020 point 4, "A page shrinks and never grows".** It comes to add that in print a page shrinks with the sheet's area as the window, and a fixed page with the room its keyline leaves, as this record's points 2 and 3 say.
  - **DEC-023 point 7, "The file names its schemes".** It comes to add that in print each page lies on the browser's ground, and the file asks the browser to keep the colours of its pages and their keylines exactly, and nothing around them, as this record's point 5 says.
  - **DEC-031 point 3, "The keyline reads".** It comes to add that in print the keyline's share keeps the floor against a white sheet too. Where a dark page's keyline takes the browser's text colour whole, under more contrast, the page's own ground marks its edge on the sheet, as this record's point 3 says.
  - **DEC-031 point 3, "Forced colours".** "CSS's outline" comes to say an outline on screen and a border in print, each of a kind a browser keeps there.
  - **DEC-031 point 4, "The keyline takes no room".** It comes to say this of the screen. In print the keyline is the page's own border, and the sheet's area, less the keyline on each side, is the page's window, as this record's point 3 says.
  - **DEC-031 point 4, "On screen alone".** It comes to say that the backdrop, the gutter and the room the gutter leaves are a screen's alone. In print a fixed page lies inside its keyline, as this record's point 3 says.
  - **DEC-031 point 5, "What reads them instead".** "A keyline that takes no room" comes to say on screen, and the test comes to hold the print's keyline too.
  - **DEC-031's Rationale, "Why an outline", and its alternative "A border, or a shadow alone, as the keyline".** Each comes to speak of the screen. "Why an outline" comes to add that in print, where the page's drawing shrinks to leave it room, the keyline is a border, as this record's point 3 says.
- **Edits to the capability's page on outputs** (`outputs.md`), made in this change once this record is accepted, each anchored to it:
  - The HTML renderer, a new section Printing: it says the renderer does not yet print as this record decides, until the Task below lands. It gives the sheets a 16:9 slide fits whole, and the scale a page prints at.
  - Printing: the keyline's contrast against a white sheet, in light and in dark, and how much narrower a fixed page prints.
  - Printing: what each browser does where a page that runs on breaks, until the record on breaks lands.
  - Fixed pages, "On screen alone": a print holds neither the keyline nor the backdrop until the Task below lands, and Printing says what it will hold.
- **Read against this answer, and left as they stand:**
  - The step emulates the dark signal, since emulated and real dark gave the same pixels (DEC-023's Rationale, and its revisit if the emulation stops matching a reader's dark mode). In print the two differ, and the step reads no print.
  - Every length is a share of the page's width (DEC-020 point 2), so a page scales to the sheet with no script. It stands, and the bug below may come to question it.
  - Each line is placed alone, and each run of shapes is one layer the size of the page (DEC-020 points 2 and 3). They stand, and are why the browser picks where a page that runs on breaks.
  - A renderer reports what it cannot draw as the scene sets it (DEC-001 point 2). Where a print breaks lies with the reader's sheet, which the renderer does not know, so it reports nothing of it.
  - A page clips no text (DEC-020 point 4), and the file clips nothing in print.
  - Each of DEC-020, DEC-023 and DEC-031 is revisited where what its Context did not reach shows a fault (their Implications), which this record answers for printing. Firefox's faults stay open, for the bug below.
  - No rule switches the layout by the window's width ([visual-communication:DEC-021-size-and-shape] point 8, DEC-023 point 5), and the print's rules switch nothing by a window's width.
  - A site's page asks for no height, so it is no fixed page ([visual-communication:DEC-022-web-site-and-parts] point 3, DEC-031 point 2).
  - Whether a portal's pages need a keyline, which DEC-031 leaves open.
- **The Task that prints the page,** filed under [project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570) once this record is accepted, builds points 1 to 6 in the renderer.
  - Its output changes, so the renderer's own version rises ([visual-communication:DEC-005-engine-and-plugins] point 9). The seam's version stays, since no plugin reads anything new (DEC-005 point 8).
  - It builds on the keyline as [project-kit#2944](https://github.com/aleskalfas/project-kit/issues/2944) left it, and on the file's modes as [project-kit#2815](https://github.com/aleskalfas/project-kit/issues/2815) left them. It adds the print's rules beside the screen's, and changes none of the screen's.
  - The page on outputs comes to say that the renderer prints as its Printing section says. Its line that a print holds neither keyline nor backdrop gives way to that, and so do the renderer's docstrings that say the same.
  - It closes with a person's print, which [project-kit#2851](https://github.com/aleskalfas/project-kit/issues/2851) takes.
- **#2851's body,** edited once this record is accepted, comes to say in its criterion on printing that a person prints points 1 to 5 in each browser as shipped, in each mode and under more contrast (point 7), though no page that runs on, whose break waits for the record on breaks. Its Dependencies come to name the Task that prints the page.
- **#2815's and [project-kit#2817](https://github.com/aleskalfas/project-kit/issues/2817)'s bodies** ask no edit. Both closed before this record, and the person's print they left open is #2851's.
- **The record on breaks** decides how a page that runs on is to break between a text's lines, never through one, as point 1 asks. Its issue is filed under #2570 once this record is accepted.
  - **What it weighs:** whether a block is kept whole, and a heading with what follows it. The scene names neither today, so these may wait on how a text's structure is declared ([project-kit#2739](https://github.com/aleskalfas/project-kit/issues/2739)). It weighs too a picture that holds text, which a browser cuts like any image.
  - **What it revisits:** DEC-020 where a page's form changes, and this record's point 1 where the file comes to ask for a break.
  - **What it mends:** the harm a break does to a line today, with the bug below where the mend lies in the page's form.
- **A bug is filed for Firefox's faults** in print once this record is accepted, by what was seen. Its mend may lie in a rule of print, in a report to Firefox, in the page's form, which the record on breaks decides, or in how a page scales with no script. Only the last needs a record of its own, which would revisit DEC-020 point 2, and this record where print rests on it.
- **Revisit this record** in any of these cases:
  - a browser as shipped cuts a page that fits a sheet, or changes its colours in print
  - a keyline fades or is lost on paper
  - a browser prints a dark mode under a dark system
  - Firefox comes to keep a page's text on its shapes across a cut, at any scale the reader sets, or under a page rule
  - a top comes to declare a physical size
  - the line between fixed pages and the rest moves (DEC-031 point 2)
  - a piece comes to need a fixed page that fits no sheet's area
  - a person's print asks for a line around a figure or a site's page
  - a record lets a page switch its layout by the window's width, since the sheet's area would then pick a layout too
  - a project comes to hand a site's pages out on paper.
