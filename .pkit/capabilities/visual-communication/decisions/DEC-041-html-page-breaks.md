---
id: DEC-041
title: A printed page that is no fixed page breaks only between lines of text and around pictures, where its file offers a place
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where a printed figure or site's page runs on across sheets, it breaks only where no line of text and no picture lies, so no line is cut and no picture is split. A heading stays on the sheet of what it heads, and no line of a paragraph stands alone on a sheet, unless what they keep is taller than a sheet. The page file lays the page out in the rows of one grid, so the browser breaks between rows, while the document keeps its reading order and the screen looks as before. A deck's slides print as they do today. For example, a section's heading near a sheet's foot moves to the next sheet with the first two lines of its paragraph.

## Context

[project-kit#3011](https://github.com/aleskalfas/project-kit/issues/3011) asks where a page that runs on breaks in print. [visual-communication:DEC-026-html-page-print] point 1 leaves the break to the browser until a record of its own decides it. The renderer places each text, line and layer absolutely ([visual-communication:DEC-020-html-page-drawing] points 2 and 3), so the browser breaks where the sheet ends, whatever lies there. Firefox's faults in print ([project-kit#3012](https://github.com/aleskalfas/project-kit/issues/3012)) may be mended in the page's form, which this record decides. The runs behind this record are the evidence of its pull request.

Whoever maintains the capability chose, on 9 November 2026, from a print that cut a heading's letters at a sheet's foot: "A page that runs on across sheets must break between lines, never through one" ([a comment on #2824](https://github.com/aleskalfas/project-kit/issues/2824#issuecomment-6753276666)).

Terms:
- A *place a break may fall* is a height, across a page's whole width, at which points 1 and 2 let a break fall.
- A *strip* is a part of a page as wide as the page, between two places a break may fall. It is no *band* ([visual-communication:DEC-022-web-site-and-parts] point 7), which the viewing step cuts from a page's image.
- A *keep* is a stretch of a page in which the file asks the browser not to break, where the stretch fits a sheet's area.
- A text's *paragraph* is its runs up to a line feed ([visual-communication:DEC-012-text-runs] point 1). A *heading*, an *instance*, an instance's *text* and a *reading order* are as [visual-communication:DEC-033-structure-for-readers] points 4 to 6 have them.
- A *sheet*, its *area* and a *fixed page* are as DEC-026 has them.

### What the test showed

The test drew a site's page of the neutral brand with the HTML renderer at 1.7.0, 1,280 and 390 px wide, holding headings, paragraphs of up to 40 lines and pictures holding lines of words. A script rewrote the page file into each form below, placing breaks from the engine's scene alone by points 1 to 3, each heading and its instance named by hand where DEC-033's marks will name them. Each was printed on A4 and Letter upright and A4 turned, at margins of 1 cm: in Chrome 157 as shipped, in Firefox 157 as Playwright builds it, and in Firefox 148 as shipped, also at a reader's scale of 0.8. Further cases moved a phone's screen 845 px tall onto the narrow page, gave a heading a picture of 0.95 of A4 turned's area, put a picture behind a section, set an aside at a 20 px line step beside a body at 24 px, 3 px lower, and moved one place 3 px into a line's descenders over a section's tint.

- **Today's form.** Chrome printed lines across a sheet's edge and cut pictures. Firefox 157 lost lines and shapes past the first sheet, and Firefox 148 set text off its tints.
- **Rules on today's elements,** and **strips that hold nothing:** each browser printed as with no rule, or parted text from its shapes.
- **A stack of strip boxes in the flow,** the first draft's form: the page held in all three browsers, but its document runs strip by strip, and on screen its later strip painted over a descender crossing the seam.
- **One grid, its keeps as `break-after: avoid` on a row's items:** Chrome kept them. Firefox 157 and 148 ignored them, and cut pictures and set headings apart on the wide page.
- **One grid, a text one element spanning its rows:** Chrome and Firefox 148 printed lines across a sheet's edge, and both Firefoxes set headings apart from their text.
- **One grid, its keeps as boxes spanning their rows, one place in a gap's middle:** the page and the seam held in all three browsers. On the wide page on A4 turned, Chrome cut the picture of 0.95 of the area, whose strip its gaps made taller than the area, and both Firefoxes set a heading apart from its text.
- **The decided form,** one place at each end of a gap, in the tree's order and in an order unlike it carried by z-index: in all three browsers, on every sheet, at both widths, and at 0.8 in Firefox 148, no line was lost, cut or printed twice, no picture that fit the area was cut, every line lay on its tint, and no heading lay apart from what it keeps. The texts side by side met a place every 120 px. A picture taller than the area was cut where the sheet ended, and one needing no text was cut as a shape. Where a picture holding words lay behind a text and was taller than Letter's area, each browser left that text's last line alone on a sheet.
- **Firefox 157's shrink.** Printing as soon as a page had loaded, it shrank some prints to 0.78 to 0.84 of their size, today's form among them, and printed the same file at full size in another run. Printing once the page's faces had loaded, it shrank none of 63. A text part bounded to the page's width shrank alike, and the strips that clipped what overflowed them were printed only the first way.
- **The screen,** in Chrome and Firefox, at windows of 1,280, 700 and 390 px and device scales 1 and 2: the page's height changed by less than 0.1 px, and no line moved by more than 0.03 px at the page's own size, or 0.15 px where the window shrank it. Pixels differed inside pictures, by their resampling, and at the edges of glyphs and shapes those moves shifted. At the seam, no pixel differed.

**Not reached:** Safari, and WebKit, which printed nothing under the tool used; Windows and Linux; a print dialog's own header and footer; a reader's scale in Chrome and Firefox 157; pages of two widths in one file; a fixed page that runs on; a reader's minimum font size; a dark mode or forced colours in print; a reader's tools on a text in parts.

## Decision

**A printed page that is no fixed page breaks only where no line of text and no picture lies, at places its file offers as the rows of one grid that keeps the document in reading order and forces no break.**

### 1. A break never crosses a line of text or a picture

- **A line spans its font's height,** from the highest ascent to the lowest descent of its runs' faces around its baseline, as the engine sets lines. No break crosses it.
- **A picture is kept whole,** but one marked as needing no text (DEC-033 point 5), which a break may cross as a shape.
- **A box, a line, an ellipse or a path may cross a break,** and each sheet shows its part.
- **Side by side,** a break falls only where it crosses none of their lines and pictures.

### 2. A heading stays with what it heads, and no line of a paragraph stands alone

- **A heading keeps whole with the first text or picture of its instance after it in reading order that lies below it:** that text's first two lines, or the picture whole (DEC-033 points 4 and 6).
- **An instance with a text of its own** counts by the first text or picture it holds, since its own text is drawn nowhere (DEC-033 point 5).
- **A heading after which its instance holds nothing below it** keeps whole alone.
- **A paragraph keeps two lines on each side of a break,** so a paragraph of three lines or fewer keeps whole.
- **Nothing else keeps,** such as a card, a section or a diagram.

### 3. The file offers each place, and asks for each keep where it fits

- **Each gap between lines and pictures offers two places:** its highest and its lowest height that cross the fewest shapes, or one, where the gap is narrower than a px. So a strip holding a line or a picture holds none of the gap around it.
- **A strip keeps whole on a sheet, and so does each keep where it fits,** so the browser breaks at the last place before the sheet's end that no fitting keep spans.
- **A keep taller than a sheet's area breaks at a place inside it,** never through a line. A smaller keep it holds may then part.
- **No break is forced,** within a page or before one.
- **A strip taller than a sheet's area runs on,** as a page does (DEC-026 point 1), such as one holding a picture taller than the area, and the browser cuts it where the sheet ends.

### 4. The page is one grid, its strips the rows, its document in reading order

- **One grid holds the page,** each element in the row of its strip. The document's order stays the reading order (DEC-020 point 3, as DEC-040 point 5 has it).
- **A text in parts.** A text whose lines lie in several strips is one element in each of their rows, holding its lines there, each still placed alone. Its parts lie together at the text's place in the document, each carrying the text's trace id.
- **A layer in parts.** A run of shapes between two texts is one layer in each strip it reaches, showing the part of each shape there. Its parts lie together at the layer's place, each part of a shape carrying the shape's trace id, and each HTML id still lies once.
- **The draw order holds across a seam.** Where the document's order differs from the draw order, each part carries its whole's place in the draw order by z-index, as DEC-040 point 5 has the whole carry it.
- **A keep is an empty box spanning its rows.**
- **On screen the page draws as before.** Every length stays a share of the page's width, and each row's top lies at its strip's height in the scene, never at a sum of heights the browser rounded.

### 5. A fixed page keeps its one element

- **A fixed page,** such as a deck's slide, lies as today, and where it runs on, it breaks where the browser picks (DEC-026 point 1).

### 6. A text in parts is still one text

- **The check for dropped text** matches a text's parts, in order, as the scene's one text (DEC-020 point 6).
- **A reader's tools** get a text, a list or a figure that strips part as DEC-040 spells it (DEC-020 point 10).

## Rationale

**Point 1, lines and pictures.** It is the maintainer's choice: a line cut, or moved over the next, cannot be read. The font's height is how the engine sets a line and sizes its ground under forced colours (DEC-039 point 1), the renderer reads it with no browser (DEC-020 point 1), and it holds the brand's accents, a háček on a capital among them. It leaves a gap wherever a text's step is taller, so texts of different steps side by side still meet places. A picture may hold words, but one marked as needing none says nothing a reader lacks. A box or a line in two parts reads as one, as a ruled box does across a book's pages. The costs: a diagram may part between its labels, and ink past a font's height, such as a stacked accent, may be cut at a sheet's end.

**Point 2, the keeps.** A heading at a sheet's foot heads nothing on that sheet, and a lone line at a sheet's foot or head reads as a stray. A heading heads its own instance (DEC-033 point 4), and what lies above or beside it is on its sheet already. Two lines are CSS's own default for a paragraph's first and last lines at a break. The heading's rule rests on DEC-033's marks and reading order, so it reaches a piece as the scene comes to hold them. A card or a section kept whole would leave a sheet's foot empty wherever one is taller than what remains, for no line saved.

**Point 3, offered, never forced.** The renderer cannot know where a sheet ends, since the sheet is the reader's (DEC-026 point 4), and a forced break would spend the paper the maintainer's compact print saves. A place at a gap's end lets a strip hold no more than its lines and pictures, so a picture that fits a sheet lies in a strip that fits it too, and a divider in the gap lies whole. A keep that could never yield would run on past the sheet's end, where a browser may lose its lines, so a keep yields where it does not fit. Browsers weigh every keep they break alike, so a smaller keep inside it may part.

**Point 4, one grid.** CSS breaks only between boxes in the document's flow, and a grid's rows are such boxes, whatever order the document gives its items. So the reading order, which a reader's tools, the keyboard and a selection follow (DEC-040 point 5), stays the document's, where a stack of strips would order the document strip by strip. In the tree's order the grid paints as today, and z-index carries the draw order where the orders differ, so no later strip paints over ink that crosses a seam. A text a break may part is in parts, since one element across rows was cut. A keep is a box of its own, since Firefox ignored keeps set on a row's items. Row heights a browser rounds add up, so lines drift down a tall page unless each row's top is set from the scene.

**Point 5, fixed pages.** A fixed page shrinks to the area's width and the room its keyline leaves (DEC-026 points 2 and 3), and a 16:9 slide fits A4 and Letter either way up (`outputs.md`, Printing), so a slide never runs on. Strips would part its texts for nothing in print. The cost: a fixed page of another shape that runs on breaks where the browser picks.

**Point 6, one text.** The step matches the scene's texts to the document (DEC-020 point 6), and a text in parts is still one text of the scene. How a reader's tools join its parts belongs with the rest of the reader's side.

### Alternatives considered

- **The break left to the browser,** as today: Chrome printed lines across a sheet's edge and cut pictures, and Firefox lost lines and shapes or set text off its tints.
- **Rules of the file on today's elements,** such as `break-inside: avoid` on each text: they print as no rule does, since the elements lie outside the flow (DEC-026, Alternatives).
- **Strips that hold nothing, under today's elements:** each browser set the elements by the sheet's end, and text parted from its shapes.
- **A stack of strip boxes in the flow:** its document runs strip by strip, not in reading order, and a later strip paints over ink that crosses a seam.
- **Strips that clip what overflows them,** on one axis or both: they cut a line's ink past its strip, against DEC-020 point 4, and the shrink they seemed to mend came from printing before the faces had loaded.
- **A text one element spanning its rows:** Chrome and Firefox 148 printed its lines across a sheet's edge, and Firefox set headings apart from their text.
- **Keeps as `break-after: avoid` on a row's items:** Firefox ignored them in a grid.
- **Keeps that never yield:** a keep taller than a sheet runs on, where Firefox 148 lost every line past the sheet's end when each text was kept whole.
- **A line's extent as its ink:** it differs with each string, so the place moves as the words change, and the renderer would have to draw each line to find it.
- **A line's extent as its step:** texts side by side at different steps may then touch at no height, leaving no place.
- **One place in a gap's middle:** a strip then holds half of each gap around a picture, so a picture that fits a sheet may lie in a strip that does not, which Chrome cut.
- **A heading kept with what follows past its instance:** it would keep one instance's heading with another's, which it does not head.
- **Each instance kept whole where it fits,** such as a card or a diagram: one taller than what remains of a sheet leaves the rest of it empty.
- **A picture cut as any shape:** a picture may hold words.
- **A break forced before a page or a section:** the renderer does not know the sheet, and the maintainer chose a compact print.
- **A page cut at a sheet the renderer assumes:** the sheet is the reader's (DEC-026 point 4).
- **A text's lines in the flow inside one element:** its shapes would still lie in layers the size of the page, which Firefox printed on the first sheet alone.
- **Strips on a fixed page too:** a slide never runs on, so its texts would part for nothing.

## Implications

- **Ordered after DEC-037, DEC-039 and DEC-040,** each drafted before it and edited by none of it. This record is accepted after them, and its edits to DEC-020 are written against their wording.
- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-026 point 1, "It is to break between a text's lines, never through one", comes to cite this record as the record on breaks.
  - DEC-026 point 1, "Until then the browser picks where it breaks", comes to say that a page that is no fixed page breaks only at the places its file offers, which forces none (points 1 to 4), and that a fixed page that runs on breaks where the browser picks (point 5).
  - DEC-026 point 7, "A test on the file", comes to hold the places and the keeps a page's file offers too.
  - DEC-026's Rationale, "Point 1, pages one after another": "The break waits for a record of its own" comes to cite this record.
  - DEC-020's term *layer* comes to read one `svg` element the size of a page, or of a strip of one (point 4).
  - DEC-020 point 2, "A text is one element" and "A text stays one element", come to say that a text whose lines lie in several strips is one element in each, carrying its trace id (point 4).
  - DEC-020 point 3, as DEC-040 words it, comes to say that a page that is no fixed page is one grid, each element in its strip's row; that a text's or a layer's parts lie together at its place in the document; and that each part carries its whole's z-index (point 4).
  - DEC-020 point 4, "The pages follow each other down the document", comes to say that in print a taller page breaks only at the places its file offers (points 3 and 4).
  - DEC-020 point 4, "The file marks what the step reads", as DEC-039 words it, comes to add each part of a text, with the text's trace id, and each part of a shape, with the shape's. The shared drawing marks each shape so today, a mark that point does not name.
  - DEC-020 point 6, "The words", comes to match a text's parts as one text (point 6).
- **Edits to the capability's page on outputs** (`outputs.md`), made in this change once this record is accepted, each anchored to it. Printing's "Where a page that runs on breaks" and "Firefox and a page narrower than the area" come to say that this record decides them, that the renderer does not yet break so until the Task below lands, and what each browser did in this record's test. The page anchors DEC-020 points 2, 3, 4 and 6 and DEC-026, so the edits above ask its answers in this change.
- **The Task that lays a page out in strips,** filed under [project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570) once this record is accepted, builds points 1 to 6 from their rules, not from the test's script, at a new version of the renderer ([visual-communication:DEC-005-engine-and-plugins] point 9). It waits for DEC-040's acceptance, for the reader's side of a text in parts. Point 2's rule on a heading comes with DEC-033's change of a text's structure, which brings headings into the scene.
- **#3012's body,** edited once this record is accepted, comes to say that strips mended its cases where a sheet's end cut a page or parted text from its shapes, in Firefox 157 and 148; that Firefox 157 shrank a page it printed before the page's faces had loaded, in today's form and in strips alike, a cost no rule of the file mends; and that it tests its other cases on strips once the Task lands. Its Dependencies come to name the Task.
- **[project-kit#2851](https://github.com/aleskalfas/project-kit/issues/2851)'s body,** edited once this record is accepted, comes to ask the person to print a page that runs on in each browser once the Task lands, and to say whether any line or picture was cut, in place of its line that they print none.
- **[project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740)'s body,** edited once this record is accepted, comes to ask DEC-040 to spell a text, a list and a figure that strips part (point 6).
- **[project-kit#3118](https://github.com/aleskalfas/project-kit/issues/3118)'s body,** edited once this record is accepted, comes to read against this record, since a text a break may part lies in parts (point 4).
- **Read against, and left as they stand:**
  - DEC-020 point 2's strut and shares of the page's width, which a strip's height takes too.
  - DEC-020 point 4, "Each id lies once": a shape's parts share its trace id, which is no HTML id, and a marker is still defined once.
  - DEC-020 point 4, "A page clips no text": no strip clips either.
  - DEC-022 point 7's bands, which cut a page's image, not its file.
  - DEC-026 point 2: a page in strips still shrinks only to the area's width.
  - DEC-026 point 6, under which the renderer declares the places and keeps its file offers, as rules of point 1.
  - DEC-026's alternative "A tall page cut into bands": strips lie where no line and no picture crosses, the design it leaves to this record, are no pages, and keep each HTML id once.
  - DEC-026's revisit where the record on breaks has the file ask for a break: this record forces none.
  - [visual-communication:DEC-031-html-page-backdrop] points 1 to 4, since a fixed page keeps its form.
  - DEC-033 points 4 to 6, on which point 2 rests.
  - DEC-037's reads: a seam clips and covers nothing, so a span cut or covered there is named as anywhere.
  - DEC-039 point 1: a line's ground lies in its line's strip, beneath the lines of its run as before.
- **Revisit this record** if a browser as shipped breaks inside a strip that fits a sheet's area, or cuts a line; if strips move a line or a shape on screen by a device pixel; if Firefox shrinks a page in strips whose faces have loaded; if a reader's tools or a selection cannot take a text in parts as one; if #3118's record keeps a text's lines in one flow; if a piece needs a diagram kept whole on a sheet; or if a piece comes to need a fixed page that runs on.
