---
id: DEC-041
title: A printed page breaks only between lines of text and around pictures, where its file offers a place
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where a printed page runs on across sheets, it breaks only where no line of text and no picture lies, so no line is cut and no picture is split. A heading stays on the sheet of what it heads, and no line of a paragraph stands alone on a sheet. The page file is written as a stack of strips, one between each two places a break may fall, and the browser keeps each strip on one sheet, so it breaks at the last such place before the sheet ends. The file forces no break, and on screen the page looks as before. For example, a section's heading near a sheet's foot moves to the next sheet with the first two lines of its paragraph, and a picture of a screen full of words moves there whole.

## Context

[project-kit#3011](https://github.com/aleskalfas/project-kit/issues/3011) asks where a page that runs on breaks in print. [visual-communication:DEC-026-html-page-print] point 1 leaves the break to the browser until a record of its own decides it. The renderer places each text, line and layer absolutely ([visual-communication:DEC-020-html-page-drawing] points 2 and 3), so the browser breaks where the sheet ends, whatever lies there. Firefox's faults in print ([project-kit#3012](https://github.com/aleskalfas/project-kit/issues/3012)) may be mended in the page's form, which this record decides.

Whoever maintains the capability chose, on 9 November 2026, from a print that cut a heading's letters at a sheet's foot: "A page that runs on across sheets must break between lines, never through one" ([a comment on #2824](https://github.com/aleskalfas/project-kit/issues/2824#issuecomment-6753276666)).

Terms:
- A *place a break may fall* is a height, across a page's whole width, at which points 1 and 2 let a break fall.
- A *strip* is a part of a page as wide as the page, between two places a break may fall. It is no *band* ([visual-communication:DEC-022-web-site-and-parts] point 7), which the viewing step cuts from a page's image.
- A text's *paragraph* is its runs up to a line feed ([visual-communication:DEC-012-text-runs] point 1). A *heading*, an *instance* and a *reading order* are as [visual-communication:DEC-033-structure-for-readers] points 4 and 6 have them.
- A *sheet*, its *area* and a *fixed page* are as DEC-026 has them.

### What the test showed

The test drew a site's page of the neutral brand through `pkit visual render` and `pkit visual look`, with the HTML renderer at 1.7.0, at two sizes: 1,280 by 4,324 px, and 390 by 4,400 px. It held a header, seven sections and a footer: headings, paragraphs of up to 24 lines, 40 on the narrow page, and three pictures each holding fourteen lines of words. A script rewrote the page file into each form below. Each was printed to PDF on A4 upright, Letter upright and A4 turned, at margins of 1 cm, backgrounds off: in Chrome 157 as shipped, in Firefox 157 as Playwright builds it, through its printer that saves a PDF, and in Firefox 148 as shipped, through WebDriver BiDi's print, which also took a reader's scale of 0.8. Its code is thrown away, and its pages and prints are the evidence of this record's pull request.

- **Today's form.** Chrome moved a line the sheet's end crossed to the next sheet's top, over the line after it, and cut a picture through a line of its words. Firefox 157 lost most shapes past the first sheet, and on Letter ran its text on to a fourth sheet where Chrome took three. Firefox 148 printed the shapes of both pages at another scale than their text, at a reader's scale of 1 and of 0.8.
- **Rules on today's elements,** `break-inside: avoid` on each text and line, and `break-after: avoid` on each heading: Chrome and Firefox 157 printed every sheet as with no rule.
- **Strips that hold nothing,** under today's elements: Chrome and Firefox 157 set the layers and the texts by the sheet's end, not by the strips', so text and shapes parted.
- **Strips that hold the page** (point 4): in all three browsers, on every sheet and at both sizes, each break fell between two strips. No ink crossed a sheet's edge, as it did at 11 of the wide page's 29 breaks in today's form, no line was cut or moved, each picture moved whole, each heading lay on the sheet of its paragraph's first lines, and every sheet held its shapes with their text, in Firefox 148 at 0.8 too. On screen, in Chrome at a window of 1,280 px and at device scales 1 and 2, no text's pixels moved, and the pictures differed by their resampling. At a window of 700 px the page was one pixel taller.
- **Strips cut only between texts,** each text whole: the narrow page's long paragraph made a strip taller than A4 turned's area, which ran on. Chrome kept its lines, Firefox 157 lost the line at the sheet's end, and Firefox 148 lost every line past it.
- **Firefox 157 and the narrow page in strips:** it printed the page at about three quarters of its size, its text on its shapes, until each strip clipped what overflowed it, on either axis.

**Reached:** Chrome 157 and Firefox 157 and 148, on one Mac, on A4 and Letter upright and A4 turned, at a reader's scale of 1, and of 0.8 in Firefox 148. **Not reached:** Safari, and WebKit, which printed nothing under the tool of #3010's runs; Windows and Linux; a print dialog's own header, footer and margins; two pages of different widths in one file; a fixed page that runs on; texts side by side; a picture taller than a sheet's area; a reader's minimum font size; a dark mode or forced colours in print; the screen in Firefox and WebKit; a reader's tools.

## Decision

**A printed page breaks only where no line of text and no picture lies, at the places its file offers, and its file forces no break.**

### 1. A break never crosses a line of text or a picture

- **Between lines.** A break falls only where no line of text crosses, from the line's top to its foot as the engine set it: between two lines of a text, between two texts, or between any other elements.
- **Around a picture.** No break crosses a picture. The renderer cannot tell a picture that holds words from one that holds none, so it keeps each whole.
- **Through any other shape.** A box, a line, an ellipse or a path may cross a break, and each sheet shows its part. No shape holds a text (DEC-020 point 1).
- **Side by side.** Where texts or pictures stand side by side, a break falls only where none of them crosses.

### 2. A heading stays with what it heads, and no line of a paragraph stands alone

- **A heading is kept whole,** and on the sheet of what its instance holds next in reading order: the first two lines of a text, or a picture whole (DEC-033 points 4 and 6).
- **A paragraph keeps two lines on each side of a break,** so a paragraph of three lines or fewer is kept whole.
- **Nothing else is kept whole,** such as a card, a section or a diagram. Each parts between its lines and around its pictures.

### 3. The file offers each place a break may fall, and forces none

- **It offers each place, and no other.** It asks the browser to keep whole what lies between two places, as it asks of each page (DEC-026 point 1), so the browser breaks at the last place before the sheet's end.
- **No break is forced,** within a page or before one.
- **What lies between two places and is taller than a sheet's area runs on,** as a page does (DEC-026 point 1), such as a picture taller than the area, or texts side by side that leave no place between them. A browser may cut or lose what the sheet's end crosses there.

### 4. A page lies in strips

- **A page is a stack of strips** in the document's flow, one between each two places a break may fall, so each is kept whole on a sheet where it fits.
- **Each strip holds what lies in it,** at the engine's coordinates less the strip's top, in the tree's order (DEC-020 points 2 and 3).
- **A text in parts.** A text whose lines lie in several strips is one element in each, holding its lines there, each line still placed alone. Each part carries the text's trace id.
- **A layer in parts.** A run of shapes between two texts is one layer in each strip it reaches, the size of the strip, showing the part of each of its shapes there. Each part of a shape carries the shape's trace id.
- **On screen nothing changes.** The strips draw nothing, and every length stays a share of the page's width (DEC-020 point 2).
- **Every page lies so,** a fixed page and a page that fits a sheet included, since the sheet is the reader's (DEC-026 point 4).

### 5. A text in parts is still one text

- **The check for dropped text** matches a text's parts to the scene's text as one (DEC-020 point 6).
- **A reader's tools** get a text, a list or a figure that strips cut as #2740's record spells it, with the rest of the reader's side (DEC-020 point 10).

## Rationale

**Point 1, lines and pictures.** It is the maintainer's choice: a line cut, or moved over the next, cannot be read. A picture's words are text to a reader as much as a line is, and nothing in the scene says which pictures hold them. A shape holds no text, and a box or a line in two parts reads as one, as a ruled box does across a book's pages. The cost: a diagram may part across sheets between its labels.

**Point 2, the keeps.** A heading at a sheet's foot heads nothing on that sheet, and a lone line at a sheet's foot or head reads as a stray. Two lines are CSS's own default for a paragraph's first and last lines at a break. The heading's rule rests on DEC-033's marks and reading order, so it reaches a piece as the scene comes to hold them. A card or a section kept whole would leave a sheet's foot empty wherever one is taller than what remains, for no line saved.

**Point 3, offered, never forced.** The renderer cannot know where a sheet ends, since the sheet is the reader's (DEC-026 point 4). A forced break would fall where the sheet does not, and spend the paper the maintainer's compact print saves. A place the file never offers needs no browser to honour a keep, so the keeps hold in every engine that keeps a box whole, as each did in the test.

**Point 4, strips.** CSS breaks only between boxes in the document's flow. Each element of today's page lies outside it, so no rule on them reached a break, and strips that held nothing left the elements to the sheet's end. A strip that holds its own lines and shapes moves with them, whole, in each engine tried, and Firefox, which printed a layer the size of the page on its first sheet alone, printed every strip. The cost: a text a break may part is no longer one element (DEC-020 point 2), and a shape a break may cross lies once in each strip it reaches, under its one trace id (DEC-020 point 4). Every page takes the form, since a page that fits one sheet may not fit another.

**Point 5, one text.** The step matches the scene's texts to the document (DEC-020 point 6), and a text in parts is still one text of the scene. How a reader's tools join its parts belongs with the rest of the reader's side.

### Alternatives considered

- **The break left to the browser,** as today: Chrome moved a line over the next and cut a picture's words, and Firefox lost shapes.
- **Rules of the file on today's elements,** such as `break-inside: avoid` on each text: they print as no rule does, since the elements lie outside the flow (DEC-026, Alternatives).
- **Strips that hold nothing, under today's elements:** each browser set the elements by the sheet's end, and text parted from its shapes.
- **Each text kept whole,** strips cut only between texts: a text taller than a sheet's area runs on, where Firefox lost its lines, and a long paragraph leaves a sheet's foot empty.
- **Each instance kept whole where it fits,** such as a card or a diagram: one taller than what remains of a sheet leaves the rest of it empty.
- **A picture cut as any shape:** a picture may hold words.
- **The keeps as CSS's rules on breaks,** such as `break-after: avoid`, `orphans` and `widows`: they act on boxes and lines in the flow, which a strip's elements are not.
- **A break forced before a page or a section:** the renderer does not know the sheet, and the maintainer chose a compact print.
- **A page cut at a sheet the renderer assumes:** the sheet is the reader's (DEC-026 point 4).
- **A text's lines in the flow inside one element, so it breaks between them:** its shapes would still lie in layers the size of the page, which Firefox printed on the first sheet alone.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-026 point 1, "It is to break between a text's lines, never through one", comes to cite this record as the record on breaks.
  - DEC-026 point 1, "Until then the browser picks where it breaks", comes to say that the file offers each place a break may fall and forces none, so a page that runs on breaks only between lines of text and around pictures (points 1 to 3).
  - DEC-026 point 7, "A test on the file", comes to hold where a page that runs on may break too.
  - DEC-026's Rationale, "Point 1, pages one after another": "The break waits for a record of its own" comes to cite this record.
  - DEC-020's term *layer* comes to read one `svg` element the size of a page's strip (point 4).
  - DEC-020 point 2, "A text is one element" and "A text stays one element", come to say that a text whose lines lie in several strips is one element in each, carrying its trace id (point 4).
  - DEC-020 point 3, "The renderer walks the page's tree in order", comes to say that each run of shapes between two texts is one layer in each strip it reaches (point 4).
  - DEC-020 point 4: "The pages follow each other down the document" comes to add that each page is a stack of strips, and that in print a taller page runs on between them (points 3 and 4). "Each id lies once" comes to add that a shape a break may cross lies in each strip it reaches, under its one trace id. "The file marks what the step reads" comes to add each strip, and each part of a text and of a shape (point 4).
  - DEC-020 point 6, "The words", comes to match a text's parts as one text (point 5).
- **Edits to the capability's page on outputs** (`outputs.md`), made in this change once this record is accepted, each anchored to it: Printing's "Where a page that runs on breaks" comes to say that this record decides it, that the renderer does not yet break so until the Task below lands, and what each browser did with the strips in this record's test. The page anchors DEC-020 points 2, 3, 4 and 6 and DEC-026, so the edits above ask its answers in this change.
- **The Task that writes a page in strips,** filed under [project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570) once this record is accepted, builds points 1 and 3 to 5 and point 2's rule on a paragraph, and raises the renderer's version ([visual-communication:DEC-005-engine-and-plugins] point 9). Point 2's rule on a heading comes with DEC-033's change of a text's structure, which brings headings into the scene.
- **#3012's body,** edited once this record is accepted, comes to say that point 4 mends its cases where a sheet's end cut a page, and that it tests its other cases on the strips once the Task lands. Its Dependencies come to name the Task.
- **[project-kit#2851](https://github.com/aleskalfas/project-kit/issues/2851)'s body,** edited once this record is accepted, comes to ask the person to print a page that runs on in each browser once the Task lands, and to say whether any line or picture was cut, in place of its line that they print none.
- **[project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740)'s body,** edited once this record is accepted, comes to ask its record to spell a text, a list and a figure that strips cut (point 5).
- **[project-kit#3118](https://github.com/aleskalfas/project-kit/issues/3118)'s body,** edited once this record is accepted, comes to read against this record, since a text a break may part lies in parts (point 4).
- **Read against, and left as they stand:**
  - DEC-020 point 2's strut and shares of the page's width, which a strip's height takes too.
  - DEC-020 point 4, a page clips no text: no strip clips one either.
  - DEC-022 point 7's bands, which cut a page's image, not its file.
  - DEC-026 point 6, under which the renderer declares the places its file offers, as a rule of DEC-026 point 1.
  - DEC-026's revisit where the record on breaks has the file ask for a break: this record answers it with the edits above, and the file forces none.
  - [visual-communication:DEC-031-html-page-backdrop] points 1 to 4, since a fixed page's keyline lies around the page, outside its strips.
  - DEC-033 points 4 and 6, on which point 2 rests.
- **Revisit this record** if a browser as shipped breaks inside a strip that fits a sheet, if a reader's tools or a selection cannot take a text in parts as one, if [project-kit#3118](https://github.com/aleskalfas/project-kit/issues/3118)'s record keeps a text's lines in one flow, if a piece needs a diagram kept whole on a sheet, or if the strips change the page on screen.
