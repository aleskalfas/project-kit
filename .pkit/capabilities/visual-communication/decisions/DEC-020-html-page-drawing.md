---
id: DEC-020
title: An HTML page is real text over SVG shapes, and the viewing step draws it through a browser
status: accepted
date: 2026-11-06
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the HTML renderer writes one file for each language. A page in it is real HTML text, each line where the engine put it, over SVG shapes, lines and pictures, in the scene's draw order. A page shrinks with a narrow window and never grows. Writing that file takes no browser, but seeing it does, and no other format needs one. The viewing step draws the file through a browser of the Chromium family it finds on the machine, and reports each text it lost or drew in a font of the machine. Where no browser runs, it leaves the file and a report, and names what is missing. So a build in a sandbox cannot see such a page yet: each Chromium build tried stopped there on its own defaults. The SVG renderer stays as it is, for pictures: a figure on a GitHub page, a picture inside another document, and a build with no browser.

## Context

[project-kit#2737](https://github.com/aleskalfas/project-kit/issues/2737) asks how the HTML renderer draws a page, and how the capability sees it. Whoever maintains the capability settled the main question: the `html` format needs a browser, and a page is real HTML text over SVG shapes, since HTML has nothing for a routed line with arrowheads. The viewing step's tool today is resvg, which reads SVG alone ([visual-communication:DEC-015-viewing-step-and-reviewer] point 2). This record settles the rest.

Three terms:
- A *page file* is the file the HTML renderer writes: one language's pages, at one size, in one web document.
- A *strut* is an empty inline block whose foot sits on a line's baseline. It places that baseline with no help from the font's metrics.
- A *layer* is one `svg` element the size of a page, holding a run of shapes with no text between them in the tree.

### What the test showed

The test took the showcase deck of the repository the capability is authored in: four pages in two languages, 200 lines of text, one brand's three faces. It ran on one Mac, in Chrome 157, and in Firefox 157 and WebKit 27.2 as Playwright builds them. Its code is thrown away.

**A line's place.** Each row is the worst of 200 lines against the engine, in px of the page, with each line set as point 2 says.

| Browser, device scale | Baseline by layout | Baseline by ink | Width |
|---|---|---|---|
| Chrome, 1 | 0.024 | 0.49 | 0.06 |
| Chrome, 1.225 | 0.016 | 1.12 | 0.05 |
| Chrome, 2 | 0.008 | 0.24 | 0.03 |
| Firefox, 1 | 0.010 | 0.49 | 0.19 |
| Firefox, 2 | 0.010 | 0.24 | 0.19 |
| WebKit, 1 | 0.024 | 0.49 | 0.41 |
| WebKit, 2 | 0.024 | 0.24 | 0.41 |

- **The strut holds.** On plain lines it stayed within 0.015 px by layout in all three browsers. Half a pixel of ink at scale 1 is a line rounded to a pixel row.
- **Other ways do not.** A `line-height` set to the engine's step passed one device pixel in Chrome at every scale. Lines flowing in one element, each opened by a strut of fractional height, moved ink by up to 0.89 px at scale 1.
- **Scale 1.225,** which the step's images use, put the worst line 1.37 device pixels off, for a cause not found.
- **`cqw`, a share of the page's width, scaled it with no script.** Every line stayed within one device pixel down to a window of 512 px. At 375 px Chrome held. Firefox and WebKit read a quarter of the lines over, at worst 1.44 device pixels. Nothing scrolled sideways.

**The tree's order.** No page of the deck lays a shape over a text: a scan of its eight pages found none. So the test made one: on its first page, a box between the title and the lead, then an opaque box, a translucent box, an arrow and a text on top. The figure is the mean difference, out of 255, from the SVG renderer's page of that scene in the same browser, on four regions.

| Browser, device scale | A layer for each run of shapes | Every shape under every text |
|---|---|---|
| Chrome and Firefox, 1 and 2 | 0.00 | 1.39 to 13.86 |
| Chrome, 1.225 | 0.00 to 1.34 | 2.70 to 14.06 |
| WebKit, 1 and 2 | 0.00 to 3.53 | 3.42 to 13.62 |

In each region the first figure lies below the second, at worst 3.53 against 4.83. WebKit's rest is its SVG text, a pixel off its HTML text. A `z-index` on each element, with the texts reversed in the document, gave the same image in all three browsers. The deck's pages hold 5 to 17 layers, and an arrowhead defined once in the file drew in each.

**What only a browser showed.** Faces held page by page moved up to 15 of a language's 100 lines, at worst 1.39 px. A file with no encoding garbled Czech in WebKit. WebKit also opened a gap in SVG text, up to 6 px, in a line of several runs.

**A reader's settings.** Forced colours reached HTML text and not the shapes, so a dark arrow on a page with no ground stayed faint. A minimum size of 20 px grew text past its panels, and 50 px past the window.

**The step.** A driver written for the test, on Python's standard library alone, spoke to the browser over a pipe. It drew four pages and checked 169 spans in 9.3 s in Chrome. A small page planted with one fault of each kind the check reads took 0.36 s, and each was named. An image differs from resvg's of the SVG renderer's page by a mean of 1.07 to 2.44 of 255.

| Planted in the file | What the check said |
|---|---|
| A span with no paint, alone, between two lines, or beside a span | That span, no ink |
| A line off the page | That line |
| A face left out, or broken | 52 spans drawn in Times, a font of the machine |
| A weight with no face | That family and weight |
| A character the face lacks | That span, and the font that drew the character |
| A request to the network, or for a file beside the page | Refused, and named |
| A `<` left in a run, so the parser swallowed the rest, or a span taken out | Nothing by ink or font. That text, once the document was matched to the scene |
| Nothing, a text under a later box, or a text the colour of its ground | Nothing, as resvg's check says of the last two |

**Builds, and a sandbox.** The sandbox was written by hand, with the network denied and writes held to a few folders. Each browser ran there once.

| Browser | Size | Its image | In the sandbox |
|---|---|---|---|
| Chrome 157 | 2.1 GB | | Stopped, a local socket refused |
| Chromium 149, Playwright's | 344 MB | Same pixels as Chrome | Stopped, the same |
| Headless shell 149, Playwright's | 192 MB | Same pixels as Chrome | Stopped on its own sandbox. With that turned off it drew the same pixels, and its page's request was refused |

**Not reached:** a picture, an ellipse, a run in two families, right-to-left text, pages of two sizes, several modes. Safari as an application, Firefox as shipped, Linux and its containers, Windows, a phone, a real screen of high density, a second machine. A screen reader, a keyboard, selection, find-in-page, printing. A project's real sandbox. A browser that hangs.

## Decision

**A page of the HTML renderer is real HTML text at the engine's coordinates, over SVG layers that keep the tree's order. The viewing step draws its file through a browser of the Chromium family found on the machine, and names what is missing where none runs.**

### 1. A page is real text over SVG shapes

- **Each text of the scene is real HTML text.** No text of a page lies in SVG.
- **Boxes, ellipses, lines and pictures lie in layers,** drawn as the SVG renderer draws them, by code the two renderers share.
- **Writing the file takes no browser,** so a render, an export and a check of this format run where none does.

### 2. A line lies where the engine put it

- **A text is one element** at its frame: its left, top and width.
- **Each line is a child placed alone,** never flowing after the line before it. A text stays one element.
- **A strut places its baseline.** The line opens with a strut of one whole number of page px, taller than any run rises. The line's top is its baseline less that height.
- **A line never wraps,** since the engine broke it ([visual-communication:DEC-005-engine-and-plugins] point 4). Its `text-anchor` is its alignment in the text's frame.
- **Runs follow each other,** at the browser's own widths. No span takes a place of its own.
- **Every length is a share of the page's width,** so a page scales with no script.

### 3. The document's order is the tree's order

- **The renderer walks the page's tree in order** (DEC-005 point 5). Each text is written as point 2 says. Each run of shapes between two texts is one layer. So order holds by construction, and nothing computes where shapes meet.
- **A layer takes no pointer,** so a text under it can still be selected.
- **Where a reading order differs,** `z-index` can carry the draw order, and leave the document's order to a reader.

### 4. What holds of a file

- **One file for each language,** holding its pages in the scene's order, at one key until how a file holds its modes is settled (point 10). Each size has a file of its own.
- **Its head declares** its encoding, its language and its viewport, so no browser guesses.
- **The pages follow each other down the document,** each in the middle of the window, with a gap the renderer declares ([visual-communication:DEC-001-visual-communication-discipline] point 2). The file sets no colour around them.
- **A page shrinks and never grows.** In a narrower window it shrinks with the window and keeps its proportions. In a wider one it keeps its own size. At the sizes the file sets, the document never scrolls sideways.
- **A page clips no text.** A reader's minimum size may push a line past its panel or the window, and the document then scrolls. A later shape still lies over that line.
- **A file holds all it needs,** so it asks for nothing. Its pictures lie inside it, and each face once, subset to every character the file draws in it.
- **Each id lies once.** A marker defined once serves every layer and page.
- **The file marks what the step reads:** each page, each layer, and each text with its trace id (DEC-005 point 5).

### 5. The viewing step draws this page through a browser

- **Which renderer a run reads.** A piece that declares `html` is read through this renderer, since a reviewer of a web page should see that page. Any other piece goes through the SVG renderer and resvg. The caller may name either.
- **Each renderer has a folder of its own for the piece,** this one's beside the SVG renderer's, under a name no piece can take. The SVG renderer's stays where it lies. A run replaces only its own, so a stop of this renderer deletes no image the SVG renderer drew.
- **It reads the page file as the renderer wrote it,** so an image shows what a reader gets in that browser. Frames are as for any page. Each file takes one browser start, and its pages share one device scale, the largest any of them asks (DEC-015 point 5), since a browser's flag binds a whole start.
- **A person gets the images and the file.** A run leaves the page file beside the images, to open in their own browser. It is no export, and is never committed. A render writes no preview of this renderer.
- **A reviewer gets the images, the frames and the report,** which names the renderer and the browser with its version, and says an image stands for that browser alone.
- **A session may hand the reviewer other images** of the same pages, from another tool or renderer. They promise nothing either. The reviewer's report says which drew each, under which lock, and a finding on one names it.
- **What an image does not show.** A test on the file covers what point 4 asks and a layer out of the tree's order. A person, in a browser, covers another engine, a reader's own settings, a narrow window and printing.

### 6. What the check for dropped text reads

The report (DEC-015 point 3) keeps each loss the renderer reports, and reads four things of the browser:
- **The words.** Each text of the scene is matched to the document, element by element, its runs in order and in number. Any difference is reported. An HTML parser refuses nothing, so nothing else would show it.
- **Ink.** Each span is drawn alone, as resvg's check draws it: the other spans unpainted, the layers hidden from outside the file, on a white ground and then a black one. A span that changes nothing left no ink. A span outside the page is reported too.
- **The font.** A span whose family and weight have no loaded face in the file is reported. So is a span the browser drew, even in part, in a font of the machine, with that font.
- **Requests.** The step refuses each request but the page file's own and a `data:` address, and names it.

It asks nothing of what lies over a text: a text under a later box, or in the colour of its ground, was drawn.

### 7. Which browser, and how it is found

- **A browser of the Chromium family.** The step looks where Chrome and Chromium install themselves, and takes the first it finds. The methodology installs and pins none.
- **A project may name another in its configuration,** such as a pinned build of Playwright's, as it turns on a plugin that reaches a service ([visual-communication:DEC-002-files-and-validation] point 8). A caller may not: a command starts what it is told with no prompt, so the choice lies in a file the project reviews, never in a flag.
- **What may differ between machines.** Pixels may, and nothing compares two machines' images (DEC-015 point 6).
- **What may not.** Point 6 holds on every machine. So each browser start first reads a small page of its own, in the renderer's form, planted with one fault of each kind point 6 reads. If the check does not name each, with the font that drew the planted span, the run stops and says so.

### 8. Where no browser runs

- **The step still writes the page file and a report,** in this renderer's folder, and no image. It ends as a stop. The report says what stopped it and under which lock, so no one reads the folder as clean. A browser that stops part way, or a first read that fails (point 7), ends the same way, with no partial images.
- **It names what is missing** (DEC-002 point 8): where it looked, or the program it started and what that said. It also names the SVG renderer as a way to go on.
- **Each call to the browser is bounded, and so is its close,** so a long piece still finishes. A browser that hangs counts as one that stopped, and the step ends it.
- **A sandbox may stop the browser,** and the step says so. It does not turn off the browser's own sandbox, until what the permission model adds for an outside program is settled ([project-kit#2775](https://github.com/aleskalfas/project-kit/issues/2775)). That Task lies in version 1 of the capability.
- **That leaves a build in a sandbox** the file, and the same scene through the SVG renderer and resvg. Those images show the layout, never this page. The browser's look falls to a session outside the sandbox.

### 9. The shipped step is its own code

The step's browser half lies behind one module of the capability, on the standard library alone. It takes no wheel and no runtime of another language (DEC-002 point 8), so every other format pays nothing for it. What it asks of a page it asks in JavaScript, which the browser runs, so it needs no runtime of its own. It rests on no tool of the repository the capability is authored in, such as its script that draws a page in a browser ([project-kit#2736](https://github.com/aleskalfas/project-kit/issues/2736)).

### 10. What this leaves to other records

- **How a page holds its modes is [project-kit#2738](https://github.com/aleskalfas/project-kit/issues/2738)'s.** resvg no longer reads this page, so its limits on a paint fall away. #2738 keeps a mode settable from outside the file, so the step can read the real file.
- **What a reader who does not see the page gets is [project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740)'s,** and it shrinks, since each text now lies once. It keeps how these elements carry the words of a run's structure ([project-kit#2739](https://github.com/aleskalfas/project-kit/issues/2739)), emphasis or a link across a line break among them. It keeps a reading order that differs from the draw order, selection and find-in-page over lines placed apart, a keyboard reader, what a shape or a picture says, and a person's reading with a screen reader.

## Rationale

**Why a stop still replaces this renderer's folder.** Old images beside a new file would read as current. The cost: in one clone, a run in a sandbox deletes what a session outside it drew.

**Why the Chromium family, no pin, and no Playwright.** The step must learn which font drew each span. This family's protocol says so, over a pipe with no port and no driver. The other engines were not tried for this. A pin is a download for a promise images do not make. Playwright's wheel carries Node, at 120 MB, and in the command's header it would reach every project that looks at a figure.

**Why no standing run in other browsers.** The step looks in a real browser at each run, so a standing run would add only other engines. Of the two faults WebKit alone showed, its gap lay in SVG text, and a test on the file holds the encoding. So such a run does not earn its cost. The form has met neither Safari as an application nor Firefox as shipped, so a person looks in each once. After that a fault only another engine shows reaches a reader first, and this record accepts that risk.

**Why a page shrinks with the window.** A page that kept its size would make every narrower window scroll sideways. The cost: a browser's zoom gives little on a laptop, where a pinch or the system's magnifier serves that reader.

### Alternatives considered

- **Each page drawn as SVG, read by resvg with no browser.** Rejected. A reader's size and colours would not reach the text, and a reader's tools would need each text twice. SVG stays the form for pictures.
- **WebKit as the step's browser,** at 79 MiB the smallest build. Rejected. It needs Playwright, and its page reached the network from inside the sandbox.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). All but the last lie in DEC-015, and go past the one point its Revisit foresaw:
  - **Its summary and Decision sentence** come to say that the tool is resvg for the SVG renderer's pages and a browser for the HTML renderer's.
  - **Point 1, "It runs no program"** comes to read "It runs no helper or producer".
  - **Point 2's heading and "Over the SVG, behind one module"** come to say that each tool lies behind one module of its own, which takes what the renderer drew, a page or a page file, and gives images and what the tool dropped.
  - **Point 2, "Pinned, and in the command's own process", "The page's faces" and "What it draws otherwise"** come to say this of resvg. The browser is an outside program, called only for the HTML renderer's pages. It reads the faces itself, and may draw a run in a font of the machine.
  - **Point 3** comes to add that a browser's drops are learned as this record's point 6 says, that a run in a font of the machine or with no face counts as drawn otherwise, that the report names the renderer, the browser and each request refused, and that a run with no image still leaves a report, saying so.
  - **Point 4, "What it writes, and where"** comes to add the page file where a renderer writes one, and a browser's throwaway profile among the transient files, in the same local folder, which a run removes, even one that stops, and that a browser may write files of its own elsewhere, such as a crash database, or a socket in the system's temporary folder.
  - **Point 4, "A run replaces what an earlier run left"** comes to say that each renderer has a folder of its own for the piece, that a run replaces what an earlier run left in that folder, so it never mixes two runs, and that the report names the lock as the frames do.
  - **Point 5, "The caller picks"** comes to add the renderer, by default as this record's point 5 says.
  - **Point 6, "It shows this tool's drawing, not a browser's"** comes to say that an image of the HTML renderer's page shows one browser's drawing, and stands for no other.
  - **Point 7, "It reads, and does not draw" and "Its findings"** come to add that a session may hand the reviewer other images of the same pages, which promise nothing either, that its report says which drew each and under which lock, and that a finding on one names it.
  - **The Revisit's last item goes,** since this record brought the browser.
  - **[visual-communication:DEC-006-work-outside-the-engine-and-outputs]'s Implications, the bullet on the first real producer, "It decides too what the capability adds to the permission model"** comes to say that this change takes that from a record of its own, #2775, for the outside programs a producer or the viewing step calls. The step does not wait for it.
- **The Task that draws a piece's pages** adds the renderer and builds points 1 to 4, at one key. Its tests hold what point 5 gives a test on the file. The format a piece declares comes with the Task of the `html` format, after the Task that holds every mode in one file.
- **The Task that builds the step's browser half** builds points 5 to 9, and settles how a caller names a renderer and a project a browser. It keeps the window at the page's width, and sets a device scale by the browser's own flag, since an emulated scale leaves HTML text on whole pixels. A stop that leaves the file and the report is a new exit of the command, since a refusal today leaves the folder as it was. Its tests need no browser. Point 7's first read holds the real one, so a fault there shows as a stop, never as a clean report. It closes with a person's look in Safari and in Firefox.
- **The change that teaches the reviewer** lands with that Task. The reviewer comes to find this renderer's folder, to take other images as point 5 says, and to read a folder with a report and no image as a stop.
- **#2738 and #2740 are edited before they start,** to what point 10 leaves them. #2738 also takes up a shape on a page with no ground, under forced colours. #2740's test comes to read the page the step draws, so it waits on that Task, not on #2736's script.
- **The SVG renderer keeps WebKit's gap,** for a change of its own.
- **Revisit this record** if a fault reaches a reader in an engine the step does not use, if a browser's update stops point 7's first read, if #2775 settles what the permission model adds, if #2740's test finds a need these elements cannot meet, or if what Context lists as not reached shows a fault.
