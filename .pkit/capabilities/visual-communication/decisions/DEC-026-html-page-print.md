---
id: DEC-026
title: A printed page file sets its pages one after another, each whole where it fits a sheet
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a printed page file sets its pages down the sheets as they follow one another on screen, as many to a sheet as fit. A page that would be cut at a sheet's foot moves whole to the next, and a page taller than a sheet runs on. Only a fixed page, such as a deck's slide, prints inside a thin line. The reader picks the paper, and each page keeps its own colours. For example, a deck's slides printed on A4 sheets held upright lie two to a sheet, each whole inside its thin line.

## Context

[project-kit#2824](https://github.com/aleskalfas/project-kit/issues/2824) asks what a printed page file is. Three records leave it open:
- **The HTML page's record** lists printing among what its test did not reach, and is revisited where a fault shows there ([visual-communication:DEC-020-html-page-drawing], Context and Implications).
- **The record of modes** lists printing in a dark mode the same way ([visual-communication:DEC-023-html-page-modes], Context and Implications).
- **The record of the backdrop** keeps its keyline and backdrop off a print until this record decides ([visual-communication:DEC-031-html-page-backdrop] point 4).

The fault came from the change that drew the page through a browser ([project-kit#2804](https://github.com/aleskalfas/project-kit/pull/2804), "Other engines" and "A person's look"). Printed, the page file of the showcase deck, the deck of the repository the capability is authored in, ran its pages on with no break. So a sheet's edge cut a page, and in Firefox the text below the cut parted from its shapes. The runs behind this record are the evidence of its pull request ([project-kit#2850](https://github.com/aleskalfas/project-kit/pull/2850)).

Whoever maintains the capability chose, on 9 November 2026:
- **A compact print,** over a sheet for each page, from a mock-up of a deck's slides on A4 sheets ([the comment on #2824 that records it](https://github.com/aleskalfas/project-kit/issues/2824#issuecomment-6740449104)): "Pages print compact: they follow each other on a sheet, so several fit on one. Each page is framed by a thin line, and a page that would be cut at a sheet's foot starts the next sheet whole. A page taller than a sheet still runs on."
- **The thin line on slides only.** Later that day, from a picture of this record's print, they were asked whether a figure and a web page get the thin line on paper too. They answered "slides only" ([a comment on #2824](https://github.com/aleskalfas/project-kit/issues/2824#issuecomment-6753276666)).
- **A break between lines,** where that picture cut a heading's letters at a sheet's foot, in the same comment: "A page that runs on across sheets must break between lines, never through one."

Terms:
- A *sheet* is one leaf of a print: a side of paper, or its like in a PDF the browser saves. Its *area* is the part inside its margins.
- A *page rule* is a rule of the file that sets the sheet: CSS's `@page`, naming the sheet's size, its margins or its orientation.
- A *fixed page*, its *keyline*, the *backdrop* and the *gutter* are as DEC-031 defines them.

## Decision

**A printed page file sets its pages one after another on the sheets its reader picks, each whole where it fits one.**

### 1. Pages follow one another down the sheets

- **Each page follows the one before it,** as on screen, in the middle of the sheet's area, after the gap the renderer declares (DEC-020 point 4).
- **A sheet holds as many pages as fit.** No break is forced before a page.
- **The file asks the browser to keep each page on one sheet,** so a page that does not fit the rest of a sheet moves whole to the next.
- **A page taller than a sheet's area runs on** across sheets, a fixed page too.
- **It is to break between a text's lines, never through one.** A record of its own, the *record on breaks*, decides how.
- **Until then the browser picks where it breaks,** and the file holds no rule on it. A break may cut a line of text, or move it off the place DEC-020 point 2 gives it, and cut or lose a shape, which this record accepts until then.

### 2. A page prints at most the sheet's width

- **The sheet's area is the window.** A page shrinks to at most the area's width, and never grows past its own size, as in a narrow window (DEC-020 point 4).
- **No bound on its height.** A page keeps the scale its width gives it, however tall it is.
- **No gutter in print.**
- **Each page by its own width.** Pages of one width print at one scale. Pages a top's slot declares may differ in width (DEC-031 point 2), and each prints at its own scale.

### 3. A fixed page prints inside its keyline

- **Each fixed page prints inside its keyline** (DEC-031 point 1). No backdrop prints around or between the pages.
- **In print the keyline is the page's own border,** around the page's drawing as on screen, never over it. The two form one box and move to a sheet together, and the keyline adds no element (DEC-031 point 4).
- **A fixed page's window is the sheet's area less the keyline on each side.** So the keyline lies inside the area, and the page's drawing shrinks only where it would not fit, keeping its proportions.
- **Its colour is the screen's:** the mix of the browser's colours DEC-031 point 3 sets, under more contrast and forced colours too. Point 5 keeps it on paper.
- **Its share keeps DEC-031's floor of 3 to 1 against a white sheet too,** in light and in dark. Under more contrast a dark page's keyline is white on a white sheet, and the page's own ground marks its edge there.
- **Only a fixed page,** such as a deck's slide or a handout's page, prints inside a keyline. A figure and a site's page are no fixed pages (DEC-031 point 2), and print with none, as on screen.

### 4. The sheet is the reader's

- **The file holds no page rule,** so no size, no margin and no orientation. The reader's print dialog sets them, with its header, its footer and its scale.
- **A sheet of the page's own size is the PDF export's,** where a piece declares `pdf` ([visual-communication:DEC-001-visual-communication-discipline] point 3). A page file saved as a PDF has the reader's sheets.

### 5. Each page prints on the browser's ground, in its own colours

- **Each page prints on the browser's ground colour,** as it lies on screen (DEC-023 point 7). A page with a ground of its own covers it.
- **The file asks the browser to print each page, that ground and a fixed page's keyline in their own colours,** never adjusted for paper, even where the reader turned backgrounds off.
- **The sheet around and between the pages** prints as the reader's setting for backgrounds says, and stays bare where that setting is off.
- **No mode is picked for print.** The modes stay under the reader's signals, as the browser sets them when it prints (DEC-023 point 4). A file of one mode prints that mode.
- **The rest is as on screen:** the faces, the text as text, the draw order, and the rule for forced colours (DEC-023 point 7).

### 6. The renderer declares these choices

- **The renderer declares each rule of points 1 to 5 the file holds,** beside how its pages lie on screen (DEC-001 point 2).
- **Print has no value of its own.** The keyline's width and its share are the ones DEC-031 point 3 declares, read on screen and in print alike. No project setting changes them.

### 7. What checks a print

- **A test on the file** holds what points 1 to 5 ask of it, all but where a page that runs on breaks, as a test holds how its pages lie on screen (DEC-020 point 5). Where the machine has the step's browser, the test may also print the file there and count its sheets. That print lies in the test, never in the step's shipped code, and it asserts no mode.
- **The viewing step reads no print.** A person looks at a print in each browser (DEC-020 point 5). Safari gets the same rules, and that print is its only check.
- **Every rule here holds in print alone,** so the screen's rules stay as DEC-020 and DEC-031 have them.

## Rationale

**Point 1, pages one after another.** It is the maintainer's choice (Context). A page cut at a sheet's foot reads as two halves. The cost: a page taller than the area breaks where the sheet ends, a figure, a site's page and a slide of another shape alike. The reader can print it on a sheet taller than wide, or take the PDF export where the piece declares `pdf`. The break waits for a record of its own, since mending it changes how the renderer writes a page that runs on, or what the scene tells it. That is DEC-020's to decide, not a rule of print.

**Point 2, the sheet's width.** Print adds nothing to the screen's rule. A 16:9 slide fits the area of A4 and Letter either way up, so a bound on a fixed page's height would reach only a slide of another shape. The gutter is the backdrop's (DEC-031 point 4), which does not print. The cost: pages a slot declares at different widths print at different scales, where Firefox may part their text from their shapes.

**Point 3, the keyline.** The maintainer's thin line is read as the keyline DEC-031 draws around a fixed page on screen (point 1), and "slides only" as fixed pages. So the fact on the scene's root that names them means the same on screen and on paper (DEC-031 point 2). A line around any other page would come through DEC-031's own revisit, for both media together. A border prints whole on every side. DEC-031 rejects a border on screen, where the document would scroll sideways and a page's proportions would move. Neither arises in print, where the page's drawing shrinks to leave it room. The cost: in print a fixed page is narrower than the area by its keyline, and two of a site's pages on one sheet are told apart by the gap between them alone.

**Point 4, the reader's sheet.** On a real printer the paper rarely matches a slide. The PDF export gives a slide's own sheet in every reader.

**Point 5, the page's own colours.** A page's colours belong to the piece, and a renderer draws the scene's colours and lets no medium change them (DEC-001 point 2). A page with no ground of its own was drawn against the browser's ground. So the setting for backgrounds is the one setting of a reader's the file overrides. The sheet around the pages lies outside every page, so it is not the piece's. Forced colours, more contrast and the scheme stay the reader's. The cost: a dark page prints as solid ink, its ground included. An export run makes each format in each mode ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7), so the PDF export is the way to a print in a mode the browser does not print.

**Point 6, the renderer's declaration.** The scene sets none of these choices, and a renderer declares what it chooses (DEC-001 point 2). One width and one share for both media keep the keyline on paper from drifting apart from the screen's.

**Point 7, the checks.** A test on the file holds the rules on every machine, and a person's print reaches each browser as shipped. The step's emulated dark signal printed dark where a real dark system printed light. The step's measures and images rest on the screen's rules.

### Alternatives considered

- **Each page whole on a sheet of its own,** every page shrunk to fit the sheet's area: a deck takes a sheet for each slide, and a long page prints too small to read.
- **The pages run on with no print rule,** as #2804 tested them: each browser then cuts a page at a sheet's edge.
- **A fixed page shrunk to fit one sheet's height too:** it goes past the maintainer's "A page taller than a sheet still runs on", and would shrink a tall fixed page past reading.
- **A tall page cut into bands,** each a sheet's height: a shape a band's edge crosses would lie twice, where each id lies once (DEC-020 point 4), and a band is no page a reader asked for. Parts cut where no element crosses are another design, for the record on breaks to weigh.
- **A text kept whole by a rule of the file,** such as `break-inside: avoid` on each text: CSS's rules on breaks act on boxes in the document's flow, and the renderer places every text, line and layer absolutely (DEC-020 points 2 and 3).
- **A sheet named in a page rule,** such as one of the page's own size, as presentation tools name the slide's: Firefox broke every page under each page rule tried.
- **Printing left to the browser,** with the PDF export named as the way to print: a piece that declares `html` alone has no PDF.
- **No keyline in print:** a white slide on a white sheet has no edge, and two slides on one sheet run together.
- **A thin line around every page in print,** a figure's and a site's too: the maintainer chose "slides only", and it would show on paper a look the screen does not have.
- **The keyline as an outline outside the page,** as on screen: it was lost where a page met the edge of the sheet's area.
- **The keyline drawn over the page's edge:** it covers the page's outermost row of pixels, and a renderer adds nothing to a page, showing only what lies around it (DEC-001 point 2).
- **The backdrop printed too:** the bare sheet already sets a page apart, the keyline marks its edge, and a backdrop would print only where the reader turned backgrounds on.
- **The colours left to the browser:** Firefox darkened a dark page's text toward its ground for paper.
- **A page with no ground left on the bare sheet:** a file of a dark mode alone would print its light text on white paper.
- **The whole document's colours kept,** not only the pages': the browser's own ground then prints around the pages against the reader's setting for backgrounds.
- **The light mode named for print,** rejected for now: the browsers tried print it already under a dark system.
- **A script that sets the sheet or the scale:** the file holds no script (DEC-023 point 4), and CSS already reads the sheet's area.
- **A print, or a count of sheets, in the viewing step:** it would run in Chromium alone, where every rule held but where a page that runs on breaks. Firefox's faults lie where the step does not run.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-020 point 4, "The pages follow each other down the document", comes to add that in print they follow each other down the sheets with no backdrop, a page that fits a sheet kept whole and a taller one run on (points 1 and 3).
  - DEC-020 point 4, "A page shrinks and never grows", comes to add that in print the sheet's area is the window, and for a fixed page the room its keyline leaves (points 2 and 3).
  - DEC-023 point 7, "The file names its schemes", comes to add that in print each page lies on the browser's ground, and the file asks the browser to keep the colours of its pages and their keylines exactly, and nothing around them (point 5).
  - DEC-031 point 3, "The keyline reads", comes to add that in print its share keeps the floor against a white sheet too, and that under more contrast a dark page's own ground marks its edge there (point 3).
  - DEC-031 point 3, "Forced colours": "CSS's outline" comes to say an outline on screen and a border in print, each of a kind a browser keeps there.
  - DEC-031 point 4, "The keyline takes no room", comes to say so of the screen, and that in print the keyline is the page's own border, with the sheet's area less the keyline on each side as the page's window (point 3).
  - DEC-031 point 4, "On screen alone", comes to say that the backdrop, the gutter and the room the gutter leaves are a screen's alone, and that in print a fixed page lies inside its keyline (point 3).
  - DEC-031 point 5, "What reads them instead": "a keyline that takes no room" comes to say on screen, and the test comes to hold the print's keyline too.
  - DEC-031's Rationale, "Why an outline", and its alternative "A border, or a shadow alone, as the keyline", each come to speak of the screen. "Why an outline" adds that in print, where the page's drawing shrinks to leave it room, the keyline is a border (point 3).
- **Edits to the capability's page on outputs** (`outputs.md`), made in this change once this record is accepted, each anchored to it:
  - The HTML renderer gains a section Printing. It says the renderer does not yet print as this record decides, until the Task below lands. It gives the sheets a 16:9 slide fits whole, the scale a page prints at, the keyline's contrast against a white sheet in light and in dark, how much narrower a fixed page prints, and what each browser does where a page that runs on breaks, until the record on breaks lands.
  - Fixed pages, "On screen alone", comes to say that a print holds neither the keyline nor the backdrop until the Task below lands, and that Printing says what it will hold.
- **The Task that prints the page,** filed under [project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570) once this record is accepted, builds points 1 to 6 in the renderer, and closes with the person's print [project-kit#2851](https://github.com/aleskalfas/project-kit/issues/2851) takes.
- **#2851's body,** edited once this record is accepted, comes to ask in its criterion on printing that a person prints points 1 to 5 in each browser as shipped, in each mode and under more contrast, with no page that runs on (point 7). Its Dependencies come to name the Task that prints the page.
- **[project-kit#2815](https://github.com/aleskalfas/project-kit/issues/2815) and [project-kit#2817](https://github.com/aleskalfas/project-kit/issues/2817)** ask no edit. Both closed before this record, and the person's print they left open is #2851's.
- **The record on breaks** (point 1) has its issue filed under #2570 once this record is accepted.
- **A bug for Firefox's faults in print** is filed once this record is accepted, by what was seen. Firefox parts a page's text from its shapes in cases no rule of the file reaches, such as a scale the reader sets in the print dialog.
- **Read against this answer, and left as they stand:**
  - DEC-001 point 2, a renderer reports what it cannot draw. Where a print breaks lies with the reader's sheet, which the renderer does not know, so it reports nothing of it.
  - DEC-020 points 2 and 3: every length a share of the page's width, so a page scales to the sheet with no script. Each line is placed alone, and each run of shapes is one layer the size of the page.
  - DEC-020 point 4, a page clips no text. The file clips nothing in print.
  - The revisits of DEC-020, DEC-023 and DEC-031 that Context names. This record answers them for printing, all but Firefox's faults, which are the bug's.
  - [visual-communication:DEC-021-size-and-shape] point 8 and DEC-023 point 5, no rule switching the layout by the window's width. The print's rules switch nothing by it either.
  - DEC-023's choice that the step emulates the dark signal (its Rationale and its revisit), since the step reads no print (point 7).
  - Whether a portal's pages need a keyline, which DEC-031 leaves open.
- **Revisit this record** in any of these cases:
  - a browser as shipped cuts a page that fits a sheet, or changes its colours in print
  - a keyline fades or is lost on paper
  - a browser prints a dark mode under a dark system
  - Firefox comes to keep a page's text on its shapes across a cut, at any scale the reader sets, or under a page rule
  - the record on breaks comes to have the file ask for a break (point 1)
  - a record changes how a page scales with no script (DEC-020 point 2), the one mend of the bug that needs a record of its own
  - a top comes to declare a physical size
  - the line between fixed pages and the rest moves (DEC-031 point 2)
  - a piece comes to need a fixed page that fits no sheet's area
  - a person's print asks for a line around a figure or a site's page
  - a record lets a page switch its layout by the window's width, since the sheet's area would then pick a layout too
  - a project comes to hand a site's pages out on paper.
