---
id: DEC-031
title: A deck's HTML page shows each slide inside a keyline, on a backdrop of the browser's colours
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the HTML page of a deck is a viewer of its slides at their own size. Each slide lies inside a thin line, the keyline, on a backdrop that fills the window around and between the slides. So a slide's empty part reads as the slide's, and the gap after it reads as a gap. A file does this where its pages take the height their top asks for, as a deck's slides do. A site's page and a figure lie as DEC-020 has them. The keyline and the backdrop mix the browser's own colours, so they follow the page's mode. The keyline stays clear against the backdrop and against the browser's ground. Under forced colours both take the reader's colours. A slide keeps its size and its content, and still shrinks in a narrow window. The viewing step draws each slide alone, as it draws any page. This refines the line of DEC-020 that the file sets no colour around its pages. It also says, in the founding record, what a renderer may show around a piece's pages.

## Context

Whoever maintains the capability looked at the HTML page of the showcase deck, the deck of the repository the capability is authored in, in Safari and in Firefox ([project-kit#2851](https://github.com/aleskalfas/project-kit/issues/2851)). The page shows its slides one under another, with no edge. So a slide's own empty lower part, and the gap after it, read as unexplained white space. The file sets no colour around its pages ([visual-communication:DEC-020-html-page-drawing] point 4). A page with no ground lies on the browser's own ground ([visual-communication:DEC-023-html-page-modes] point 7). The neutral brand's slide is white, on the browser's white in light. In dark it is `#151515`, on Chrome's `#121212`.

On 8 November 2026 whoever maintains the capability chose that a deck's web page is a viewer of its slides at their own size ([project-kit#2886](https://github.com/aleskalfas/project-kit/issues/2886)). In that choice's words, each slide lies "in a frame, on a ground". It shrinks in a narrow window, as DEC-020 point 4 has it, and never reflows. A page that switches between sizes by the window's width, which a site may need, is left to a record of its own.

The records already use *frame* for an element's place and size, *ground* for a page's own background and the browser's, and *edge* and *inset* for a page's boundary and a part's spacing. So this record names the parts of that choice otherwise:
- A *fixed page* is a page of a top whose layouts are its pages' forms, where that top asks for a height, so the page gets it ([visual-communication:DEC-022-web-site-and-parts] point 3). A page alone asks for its own height, so it is none.
- A *keyline* is a thin line around a fixed page.
- The *backdrop* fills the window around and between the fixed pages.
- The *gutter* is the width of backdrop at each side of a fixed page.

### What the test showed

The test took the showcase deck's page file as the renderer writes it, cut to its first two slides. It added rules for a keyline and a backdrop. It drew the file in Chrome 157, through the viewing step's own browser module, on one Mac. Its code is thrown away.

The rules it added:
- **The backdrop:** the document's background, a mix of 7% of the browser's text colour into its ground colour.
- **The keyline:** an outline of 1 px, a mix of 22%, then 45%. It took the browser's text colour under more contrast and under forced colours.
- **Inside the keyline:** each slide's own background, the browser's ground colour, which the slide's ground part covers.
- **The gutter:** 32 px, or 4% of the window's width where that is less.

| Mode set through the browser | Backdrop | Keyline at 22% | Page's own background |
|---|---|---|---|
| Light | `#ededed` | `#c7c7c7`, 1.4 to 1 against the backdrop | `#ffffff` |
| Dark | `#232323` | `#464646`, 1.7 to 1 | `#121212` |
| Light, more contrast | `#ededed` | `#000000` | `#ffffff` |
| Dark, more contrast | `#232323` | `#ffffff` | `#121212` |
| Forced colours, emulated, light and dark | `#ffffff`, `#000000` | `#000000`, `#ffffff` | `#ffffff`, `#000000` |

- **A slide reads whole.** Its empty lower part lay inside its keyline, and the gap between two slides lay on the backdrop, in each mode.
- **Close grounds.** In dark, the neutral slide's `#151515` lies at 1.2 to 1 against the backdrop's `#232323`. There the keyline alone sets them apart, and at 22% it was faint.
- **A share near half.** Computed by the same mix, and not drawn, 48% gives `#858585` in light and `#848484` in dark. They reach 3.1 and 4.2 to 1 against the backdrop, and 3.7 and 5.0 to 1 against the browser's ground. At 45% the light keyline reached 2.9 to 1 against the backdrop, short of 3.
- **Forced colours** were set by the browser protocol's emulation. It turned on the media query, and gave the backdrop a background colour no rule of the file set. The outline took the text colour. The emulation left the slides' text in the file's colours, so it was no real forced palette.
- **A slide drew the same at a device scale of 1.** Each slide's image, cut as the step cuts a page, held the same bytes with the rules and without them. The window was wider by the gutter on each side.
- **At 1.225,** the scale the step's images use, the same images differed by a mean of 1.7 to 3.3 of 255. The gutter put the page off whole device pixels, so its text rounded otherwise. No outermost row or column of an image changed, so no keyline reached one.
- **A narrow window.** In a window 500 px wide, each slide shrank to 460 px, with the backdrop at its sides. Nothing scrolled sideways.

**Not reached:** Safari as an application, Firefox as shipped, a real forced palette in any browser, a phone, printing. A brand whose slide's ground matches the backdrop. A page file the renderer wrote with these rules.

## Decision

**A page file whose pages are fixed pages shows each inside a keyline, on a backdrop. Both mix the browser's own colours, so they follow the page's mode, and the keyline contrasts at least 3 to 1. A fixed page keeps its size and its content. The viewing step draws it alone, as it draws any page.**

### 1. A fixed page lies inside a keyline, on a backdrop

- **What the file adds.** A keyline around each fixed page, and a backdrop that fills the window around and between them.
- **What that shows.** A page's empty part lies inside its keyline, so it reads as the page's. The gap between two pages lies on the backdrop, so it reads as a gap.
- **What stays.** The pages follow each other down the document, each in the middle of the window, with the gap the renderer declares (DEC-020 point 4).
- **A viewer of pages.** The file shows fixed pages at their own size, as a viewer shows slides, and never reflows them.

### 2. A file shows them where its pages take their top's height

- **What decides it.** Whether a page is a fixed page: a page of a top whose layouts are its pages' forms, which gets the height that top asks for (DEC-022 point 3). The piece declares that through its top. The top's name decides nothing, since the engine knows no kind of work by name ([visual-communication:DEC-001-visual-communication-discipline] point 4).
- **A deck's slides are fixed pages.** The deck asks for a height, and each slide gets it, a slide drawn by its own component too. So is each page of a project's own top whose layouts are its pages' forms, where it asks for a height, such as a handout's.
- **A site's pages are none.** The site asks for no height, so each page takes its own. How a site's page meets the window is left to the record of a page that switches sizes by the window's width.
- **A page alone is none,** the figure among them. Its top is the page, and asks for its own height. It is a picture that stands alone, with no gap after it.
- **Pages a top's slot declares are none.** The parts that place them give their size, and their top hands them no height of its own.
- **The scene's root says it.** The root says whether the scene's pages are fixed pages. So the renderer reads it there, and names no component.
- **All or none in a file.** One scene is one language at one size, as one file is. So a file's pages are all fixed pages or none is, and a file never mixes the two.
- **The seam's version does not rise** ([visual-communication:DEC-005-engine-and-plugins] point 8). A renderer that does not read the fact still draws every page as the scene sets it. So none draws wrong with no error, which the version guards against ([visual-communication:DEC-025-picture-files]'s Rationale). The fact lies on the root, where no renderer declares what it draws (DEC-005 point 9). So no renderer's declaration of what it draws changes.

### 3. The keyline and the backdrop mix the browser's colours

- **Mixes of the browser's own colours.** Each mixes the browser's ground colour and its text colour, CSS's system colours `Canvas` and `CanvasText`. The renderer declares each share. The file writes no colour value for them, and reads no role of a brand.
- **They follow the page's mode.** A system colour takes the scheme the file names in CSS's `color-scheme` (DEC-023 point 7). That scheme follows the signal that picks the page's mode. So a dark page lies on a dark backdrop, and a file of light alone keeps a light backdrop on a dark system.
- **The keyline reads.** Its share gives it a contrast of at least 3 to 1 against the backdrop, and against the browser's ground. That holds in light and dark, on each browser ground DEC-023's test measured. It is WCAG's level for a mark that is no text, which the records already ask of such marks ([visual-communication:DEC-004-brands-and-notations] point 8).
- **More contrast.** Where the reader asks for more contrast, by `prefers-contrast: more`, the keyline takes the browser's text colour whole. The keyline is no mode of the page, so it reads that signal whatever modes the file holds.
- **Forced colours.** The backdrop and each fixed page take the reader's background colour, and the keyline the reader's text colour. The keyline is of a kind a browser keeps there, CSS's outline. A shadow may add depth beside it, never in its place, since forced colours remove a shadow.
- **Inside the keyline,** a fixed page lies on the browser's own ground, as every page does (DEC-023 point 7). So a page with no ground of its own shows no tint of the backdrop.
- **A browser that cannot mix colours.** The keyline falls back to the browser's text colour, and the backdrop to the browser's ground.
- **The renderer declares these choices** (DEC-001 point 2): each share, the keyline's width and the gutter. Whoever maintains the capability sets their values in the renderer's declaration, within this point's floor. No project setting changes them.

### 4. A fixed page keeps its size and its content

- **No element changes.** The keyline and the backdrop add no element, and move no place, size or value of one. The scene's root gains only the fact point 2 names. Since no element is added, the check for dropped text still paints its ground over all the file holds.
- **The keyline takes no room.** It lies outside the page, as CSS's outline does, so the page keeps its size and its proportions. So the step's check that a page measures its size, and its cut of each image, stay as they are.
- **The backdrop shows on every side,** at the gutter, in px of the window. In a narrow window the gutter narrows to a share of the window's width, as a page shrinks with it. No rule switches the layout by the window's width (DEC-023 point 5).
- **A page shrinks and never grows** (DEC-020 point 4). It shrinks with the room the gutter leaves it. At the sizes the file sets, the document never scrolls sideways.
- **The keyline keeps its width** in px of the window as a page shrinks.
- **On screen alone.** The keyline and the backdrop are rules for a screen. So a print holds neither, until the record of how the page prints decides what of them it keeps ([project-kit#2824](https://github.com/aleskalfas/project-kit/issues/2824)).

### 5. The viewing step draws a fixed page alone

- **Each image is one page,** or one band of it ([visual-communication:DEC-022-web-site-and-parts] point 7), cut to the page as DEC-020 point 5 has it. The keyline and the backdrop lie outside every image.
- **The step holds a page at its own size.** Its window is as wide as the widest page, with the gutter on each side. It takes the gutter from the renderer's declaration, as it takes the file's marks, and widens the window for every file. So it needs no knowledge of which pages are fixed. A window too narrow for a page stops the run, since the page would not measure its size.
- **Pixels may round otherwise.** The gutter moves a page's place in the window. At a device scale that is not whole, that changes how its pixels round, as a second page's place does already. Images promise nothing about pixels ([visual-communication:DEC-015-viewing-step-and-reviewer] point 6).
- **The reads hold.** The check for dropped text paints its own ground over the page and the backdrop, and compares a band of the page with itself. Its first read's planted page needs no keyline, since no read looks outside a page (DEC-020 points 6 and 7).
- **The reviewer meets no keyline or backdrop.** They are the renderer's, the same around every fixed page, and nothing a piece holds changes them.
- **What reads them instead.** A test on the file covers each page's keyline, the backdrop, the floor of point 3 from the declared shares, the rules for more contrast and forced colours, and a keyline that takes no room. A person judges their look in a browser, as DEC-020 point 5 leaves a reader's settings to a person.

## Rationale

**Why a keyline and a backdrop, and no reflow.** A slide is designed at one size, and its empty part belongs to that design. A keyline shows where the slide ends, so the empty part reads as the slide's. A layout that answers the window's width is another design. The record of sizes lays one design out at each size a person names, and nothing answers a window's width ([visual-communication:DEC-021-size-and-shape] point 8).

**Why the height a page gets decides it.** The engine knows it already, from the top, so no formula has to be read for what sets a height. A deck's slides all take one height, and their empty parts and the gaps between them are the fault. A project's own top that asks for a height shows the same, with nothing declared again.

**Why a page alone and a site are none.** A page alone is the piece itself, with no gap after it to misread. A site's page is a page for a browser, whose meeting with the window is a question of its own. Each can gain a keyline later, if a person's look calls for one.

**Why the renderer decides them, and the founding record says so.** The keyline and the backdrop lie outside every page, so the scene sets nothing of them. They are how the medium shows the pages, which DEC-001 point 2 lets a renderer declare, as it declares the gap. Their shares are a look of the renderer's own, outside any piece, made of the medium's colours. No piece's look changes, which that point keeps to the logical layer. The other records let a renderer write only the reader's own colours, under forced colours (DEC-023 point 7). So the founding record comes to say where a renderer may compose a colour, and from what, rather than leave this record as the example.

**Why the browser's colours, and no role of a brand.** A brand's roles paint a page. A shared role for the keyline and the backdrop would sit in every brand for the sake of one renderer. A role a brand has would not serve: a page may fill its ground with any role, so no role is sure to differ from every page's ground. Under forced colours the browser sets the colours either way.

**Why mixes, and no grey of the renderer's own.** A fixed grey would stand apart from the browser's ground, which differs between browsers (DEC-023's Context). A mix stays close to that ground in each, and follows the scheme the file names with no rule for each scheme.

**Why a floor of 3 to 1.** Where a brand's page ground lies close to the backdrop, as the dark neutral slide does, the keyline alone tells where a page ends. That is the meaning this record exists for, so the keyline must read for every reader, not only one who asks for more contrast.

**Why an outline.** A border adds to a page's size. In a narrow window the document would then scroll sideways, and the page's proportions would move. A shadow alone vanishes under forced colours.

**Why the step leaves them out.** The images show what a piece holds, and the reviewer judges a piece. Nothing of a piece reaches the keyline or the backdrop, so the step's images, element frames and reads stay as they are.

**What it costs.** A keyline that reads is a visible line, heavier than a faint one. A site's layout that says a set height gives a page with an empty part, and no keyline. A portal's pages, one under another, keep their gap on the browser's ground. A line a reader's minimum font size pushes past its page crosses the keyline onto the backdrop.

### Alternatives considered

- **A keyline and a backdrop around every page, a site's and the figure's too.** Rejected. A page alone has no gap after it, and a site's page meets the window as a record of its own decides.
- **A page fixed where none of its parts sets its height.** Rejected. The engine would have to read each formula, through named values, to learn what sets a height. A site's layout of a set height would gain a keyline, and a page alone would too.
- **The fact read from the source each page's height names.** Rejected. A source traces a value (DEC-001 point 3), and the engine names itself as the source of other heights too, such as a site's own. The renderer would read a trace as layout, and the sources would become part of the seam's contract.
- **The fact on each page.** Rejected. Each renderer's declaration of what it draws would have to name it, or the check would report it as a loss in every page of every deck.
- **The choice by the top's name, or by a field of the piece.** Rejected. The engine knows no kind of work by name, and a field would repeat what the top's height says.
- **A key the top declares, such as one in the deck's file.** Rejected. It would say again what the top's height says. A deck would gain the keyline only once its lock moved to a release of the foundations that declares the key.
- **Roles of the brand for the keyline and the backdrop,** its own or new shared ones. Rejected, for the reasons above.
- **A keyline in the browser's text colour always.** Rejected. It meets the floor, but heavier than a line near half that meets it too. A reader who asks for more contrast gets it.
- **A keyline alone, on the browser's own ground.** Rejected. Where a page's ground matches the browser's, nothing but a faint line would tell its empty part from the gap.
- **A border, or a shadow alone, as the keyline.** Rejected, for the reasons above.
- **A top that draws a surround in the scene.** Rejected. Every renderer would draw it, and a PDF or an SVG picture needs none. The scene and the step's images would change too.
- **The step's images with the keyline and the backdrop, or with them switched off by a style the step adds.** Rejected. The first moves every element frame by the gutter, and shows the reviewer the renderer's look. The second would read a file other than the one the renderer wrote (DEC-020 point 5).

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-020 point 4, "The pages follow each other down the document".** "The file sets no colour around them" comes to say that the file sets no colour value around them. It adds that a file whose pages are fixed pages shows each inside a keyline, on a backdrop of the browser's colours, as this record's points 1 to 3 say.
  - **DEC-020 point 4, "A page shrinks and never grows".** It comes to add that a fixed page shrinks with the room its gutter leaves it.
  - **DEC-020's Implications, the Task that builds the step's browser half, "It keeps the window at the page's width".** It comes to say that the window holds each page at its own size, the gutter included, as this record's point 5 says.
  - **DEC-023 point 7, "The file names its schemes".** "The file still sets no colour around its pages (DEC-020 point 4)" comes to say that the file sets no colour value around them. It adds that a keyline and a backdrop mix the browser's colours, as this record's point 3 says.
  - **DEC-023 point 7, "Under forced colours".** It comes to add that the backdrop and each fixed page take the reader's background colour, and the keyline the reader's text colour, as this record's point 3 says.
  - **DEC-005 point 5, "The root says what the scene is".** It comes to add whether the scene's pages are fixed pages, as this record's point 2 says.
  - **DEC-001 point 2, "A renderer".** "It decides nothing the scene sets, so it adds no place, size, colour or font of its own" comes to end "of its own to a page".
  - **DEC-001 point 2, "What a renderer may decide is bounded".** It comes to add that outside every page, where the scene sets nothing, a renderer may declare how its medium shows the pages. That covers how they lie, and what lies around them in the medium's own colours. It is never a colour value or a brand's role, and it changes no piece's look.
- **Read against this answer, and left as they stand:**
  - DEC-001's summary and Decision sentence, "adding no design of its own", since what a renderer shows around the pages is no design of a piece.
  - DEC-001 point 2, "A different look comes only from the logical layer", since no piece's look changes.
  - DEC-015 point 5, "The ground", since a page still lies on the browser's own ground inside its keyline.
  - DEC-015 point 6, since images promise nothing about pixels.
  - DEC-020 point 5, since an image still shows one page, cut to the page.
  - DEC-020 point 7, since no read looks outside a page, so the planted page needs no keyline.
  - DEC-021 point 8 and DEC-023 point 5, since no rule switches the layout by the window's width.
  - DEC-022 points 1 and 3, since a site asks for no height, so none of its pages is a fixed page.
  - DEC-022 point 7, since bands cut a page as before.
  - DEC-023 point 4, since the keyline is no mode, and adds no control or script.
  - DEC-023 point 6, since the step sets each signal its format's declaration pairs, `prefers-contrast` among them.
  - DEC-023 point 7, "The renderer declares these choices", since its colours, the reader's own, are those of forced colours alone.
- **The Task that builds this record,** filed once it is accepted:
  - The scene's root says whether its pages are fixed pages.
  - The renderer draws the keyline and the backdrop, declares each share, the keyline's width and the gutter, and raises its version.
  - The step widens its window by the gutter. A test holds the file to points 1 to 4.
  - The capability's pages change with it: what a scene holds, the HTML renderer's page file and its declared choices, and what a reader of a deck's page file gets. So do the docstrings of the renderer's declaration and the step's browser module.
  - It closes with a person's look in Safari and in Firefox, in light, dark, more contrast and forced colours. That look sits beside the redesign of the showcase deck, the deck of the repository the capability is authored in ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)).
- **Left open:** whether a portal's pages, one under another, need a keyline.
- **Revisit this record** if a person's look finds a keyline that fades in a browser or a mode, if a site's page or a page alone comes to need one, or if what Context lists as not reached shows a fault.
