---
id: DEC-041
title: A printed page that is no fixed page breaks only between lines of text, and keeps each picture whole where it fits a sheet, at places its file offers
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where a printed figure or site's page runs on across sheets, it breaks only between lines of text, so no line is cut, and a picture that fits a sheet stays whole on one. A heading stays on the sheet of what it heads, and no line of a paragraph stands alone on a sheet, unless what they keep is taller than a sheet. The page file lays the page out in the rows of one grid, so the browser breaks between rows, while the document keeps its reading order, a reader's tools get each text whole, and on screen each line stays within a pixel of where it was. A deck's slides print as they do today. For example, a section's heading near a sheet's foot moves to the next sheet with the first two lines of its paragraph.

## Context

[project-kit#3011](https://github.com/aleskalfas/project-kit/issues/3011) asks where a page that runs on breaks in print. [visual-communication:DEC-026-html-page-print] point 1 asks that it break between a text's lines, never through one, and leaves the break to the browser until a record of its own decides it. The renderer places each text, line and layer absolutely ([visual-communication:DEC-020-html-page-drawing] points 2 and 3), so the browser breaks where the sheet ends, whatever lies there. Firefox's faults in print ([project-kit#3012](https://github.com/aleskalfas/project-kit/issues/3012)) may be mended in the page's form, which this record decides. The runs behind this record are the evidence of its pull request.

Terms:
- A *place a break may fall* is a height, across a page's whole width, that crosses no line of text (point 1).
- A *strip* is a part of a page as wide as the page, between two places its file offers (point 3). It is no *band* ([visual-communication:DEC-022-web-site-and-parts] point 7), which the viewing step cuts from a page's image.
- A *keep* is a stretch of a page the file asks the browser not to break: a picture (point 1), or a heading with what it keeps with and a paragraph's first or last lines (point 2). It holds where it fits a sheet's area.
- A *part* of a text, a layer or a run's grounds is the element that holds what of it lies in one strip. It is no part of a component ([visual-communication:DEC-033-structure-for-readers] point 6).
- A line's *step band* is the stretch one line step tall that the engine sets it in: from its text's top, its index times the step down.
- A text's *paragraph* is its runs up to a line feed ([visual-communication:DEC-012-text-runs] point 1). A *heading*, an *instance*, an instance's *text* and a *reading order* are as DEC-033 points 4 to 6 have them.
- A *sheet*, its *area* and a *fixed page* are as DEC-026 has them.

### What the test showed

The test drew a site's page of the neutral brand with the HTML renderer at 1.7.0, 1,280 and 390 px wide, holding headings, paragraphs of up to 40 lines and pictures holding lines of words. A script rewrote the page file into each form below, placing breaks from the engine's scene alone, each heading and its instance named by hand where DEC-033's marks will name them. Each was printed on A4 and Letter upright and A4 turned, at margins of 1 cm: in Chrome 157 as shipped, in Firefox 157 as Playwright builds it, once the page's faces had loaded, and in Firefox 148 as shipped, at a reader's scale of 1 and of 0.8. Further cases split one text into paragraphs of 3 lines, 2 lines and more; moved a phone's screen 845 px tall onto the narrow page; gave a heading a picture of 0.95 of A4 turned's area; put a picture holding words behind a section, taller than Letter's area, and marked it, in a second case, by its component as needing no text; set an aside at a 20 px line step, in paragraphs of 3 and 33 lines, beside a body at 24 px, 3 px lower, in paragraphs of 3, 14, 2 and 11; moved one place 3 px into a line's descenders over a section's tint; set a text of 100 lines of 16 px on a 20 px step, closer than its font is tall and taller than every sheet's area; and put a section's text in a list of three entries, another section in a figure, and beside a text across many strips a shape drawn and clipped as [visual-communication:DEC-039-forced-colours-grounds-and-edges] point 4 draws it, its clip applied for the test's sake.

- **Today's form.** Chrome printed lines across a sheet's edge, cut pictures that fit the area and set headings apart from their text. Firefox 157 lost lines and shapes past the first sheet, and Firefox 148 set text off its tints.
- **Rules on today's elements,** and **strips that hold nothing:** each browser printed as with no rule, or parted text from its shapes.
- **A stack of strip boxes in the flow:** the page held in all three browsers, but its document runs strip by strip, and on screen its later strip painted over a descender crossing the seam.
- **One grid, its keeps as `break-after: avoid` on a row's items:** Chrome kept them. Both Firefoxes ignored them, and cut pictures and set headings apart on the wide page.
- **One grid, a text one element spanning its rows:** Chrome and Firefox 148 printed lines across a sheet's edge, and both Firefoxes set headings apart from their text.
- **One grid, one place in a gap's middle:** on the wide page on A4 turned, Chrome cut the picture of 0.95 of the area, whose strip its gaps made taller than the area, and both Firefoxes set a heading apart from its text.
- **The decided form,** points 1 to 4 as this record decides them, in the tree's order and with every text before every layer, z-index carrying the draw order: in all three browsers, on every sheet, at both widths, and at 0.8 in Firefox 148, no line was lost, cut or printed twice, every line lay on its tint, no heading lay apart from what it keeps, and no paragraph left a line alone. No picture that fit the area was cut but the one its component marks as needing no text, which each browser cut as a shape. The picture taller than Letter's area broke between two of the lines over it. The phone's screen, taller than A4 turned's area, was cut where the sheet ended. The text set closer than its font is tall broke between its lines. The texts side by side met a place at least every 97 px.
- **Keeps merged where they overlap,** one box for each run of places some keep spans: on Letter, Chrome, Firefox 157 and Firefox 148 at scale 1 each left the last line of the text over the picture taller than the area alone on a sheet.
- **A line spanning its font's height uncut:** the text set closer than its font is tall was one strip, taller than every area. Chrome and both Firefoxes printed its lines across a sheet's edge, and Firefox 157 lost most of the narrow page's lines.
- **The reader's elements around a text's parts,** as [visual-communication:DEC-040-html-page-reader-side] spells them. Each text's element, the list, its entries and the figure laid out as no box, by `display: contents`, printed as the decided form in all three browsers, and drew the same pixels on screen in all three. Laid out as subgrids, they set a heading apart from its text or left a paragraph's line alone on a sheet in each browser. In Chrome's accessibility tree, read as DEC-040's test reads it, both forms gave the tree of DEC-040's form unparted, each heading with its level, each paragraph whole across its parts, the list with its three entries, the figure by its name and each picture, once each paragraph's element carried `role="paragraph"`. Without it, Chrome left each paragraph out and gave its lines alone.
- **A shape a seam parts,** defined once in the part of its first strip and drawn by reference in each: each HTML id lay once, and the shape printed in each part in all three browsers. Chrome printed the clipped shape clipped. Firefox 157 printed its edge unclipped, in parts as on a lone shape, wherever its clip holds a reference to the shape, and clipped it where the clip holds the path. Firefox 148 printed it wider than its outline too. On screen all three clipped it. Firefox's print also drew a lighter device row at each seam of the clipped shape, and at none of a shape without the clip.
- **Firefox 157's shrink.** Printing as soon as a page had loaded, before its faces had, under its option to shrink a page to fit, which is on by default, it shrank some prints of today's form and of a form in strips alike to 0.78 to 0.84 of their size, and printed the same file at full size in another run. Printed once their faces had loaded, none of its 132 prints shrank past the area's width, the decided form's 60 among them.
- **The screen,** in Chrome, Firefox and WebKit, at windows of 1,280, 700 and 390 px and device scales 1 and 2, the decided form against today's: the page's height changed by under 0.07 px, and no line's box moved by more than 0.031 px at the page's own size, or 0.141 px where the window shrank it. Outside pictures, whose resampling differed, the ink of some lines moved a device row while their boxes stayed: on the wide page at its own size, 9 of its 64 lines, in WebKit at scale 1 and in Chrome at both scales, there a whole CSS px, and none in Firefox; where the window shrank it, up to 9 lines in Chrome and 18 in Firefox and WebKit; on the narrow page, one line, in Firefox at 2. At the seam moved into descenders, no pixel differed, in the tree's order or with z-index.

**Not reached:** Safari, and WebKit's print, which printed nothing under the tool used; Windows and Linux; a print dialog's own header and footer; a reader's scale in Chrome and Firefox 157; pages of two widths in one file; a fixed page that runs on; a reader's minimum font size; a dark mode and forced colours in print, where the clipped shape's clip applies; the grounds of a run in parts, which the renderer does not yet draw; a link across a strip's seam, its focus and its raise; a selection, a copy and find across a text's parts; Firefox's and WebKit's accessibility trees, which Playwright does not read, and a screen reader; an instance with a text of its own, which changes only which text a heading keeps with, a rule of the plan that the Task's tests hold with no browser.

## Decision

**A printed page that is no fixed page breaks only between lines of text, and keeps each picture whole where it fits a sheet, at places its file offers as the rows of one grid that keeps the document in reading order and forces no break.**

### 1. A break never crosses a line of text, and a picture that fits a sheet stays whole

- **A line spans its font's height,** from the highest ascent to the lowest descent of its runs' faces around its baseline, as the engine sets lines, cut back to its step band where the band is shorter. No break crosses it.
- **A picture is kept whole where it fits a sheet,** a keep of its own. One its component marks as needing no text (DEC-033 point 5) is a shape. One whose text the content leaves empty is kept whole, as any picture is.
- **A box, a line, an ellipse or a path may cross a break,** and each sheet shows its part.
- **Side by side,** a break falls only where it crosses none of their lines.

### 2. A heading stays with what it heads, and no line of a paragraph stands alone

- **A heading keeps whole with the first text or picture of its instance after it in reading order that lies below it:** that text's first two lines, or the picture whole (DEC-033 points 4 and 6).
- **An instance with a text of its own** counts by the first text or picture it holds, since its own text is drawn nowhere (DEC-033 point 5).
- **A heading after which its instance holds nothing below it** keeps whole alone.
- **A paragraph keeps two lines on each side of a break,** so a paragraph of three lines or fewer keeps whole.
- **Nothing else keeps but a picture** (point 1), such as a card, a section or a diagram.

### 3. The file offers each place, and asks for each keep

- **Each gap between lines and pictures offers two places:** the highest and the lowest heights in it that cross the fewest shapes. Where those two lie within a px of each other, it offers one, in the middle of the widest stretch that crosses the fewest.
- **Where lines lie over or beside a picture,** each gap between those lines offers places by the same rule, inside the picture's keep.
- **A strip keeps whole on a sheet, and so does each keep where it fits,** so the browser breaks at the last place before the sheet's end that no fitting keep spans.
- **A keep taller than a sheet's area yields** at a place inside it, never through a line, and each keep it holds still holds.
- **No break is forced,** within a page or before one.
- **A strip taller than a sheet's area runs on,** as a page does (DEC-026 point 1), and the browser cuts it where the sheet ends, such as a picture taller than the area that no line lies over or beside, or texts side by side that offer no common place.

### 4. The page is one grid, its strips the rows, its document in reading order

- **One grid holds the page,** each element in the row of its strip. The document's order stays the reading order (DEC-020 point 3, as DEC-040 point 5 has it).
- **Each row's top lies at its strip's height in the scene,** rounded to a quarter of a page px, never at a sum of heights the browser rounded. Every length stays a share of the page's width (DEC-020 point 2).
- **A text in parts.** A text keeps its one element, laid out as no box, by `display: contents`. It holds a part in each strip its lines lie in, at the text's left and width in that strip's row, and the part holds the text's lines there, each still placed alone.
- **A layer in parts.** A run of shapes between two texts is one layer in each strip it reaches, showing what of each shape lies there. Its parts lie together at the layer's place, each part of a shape carrying the shape's trace id.
- **A run's grounds in parts** (DEC-039 point 1) are one element in each strip the run's lines reach, lying together at the grounds' place (DEC-040 point 5).
- **A shape a seam parts is defined once,** in the part of its first strip, and each part draws it by reference, so each HTML id still lies once. A clipped shape's definition and its clip lie there too, and each part's reference carries the clip (DEC-039 point 4).
- **The elements around texts** (DEC-040 point 1), such as a list, its entries and a figure, are laid out as no box too, so the parts they hold lie in the page's grid. A picture's element (DEC-040 point 7) spans the rows of its picture, and asks for no keep.
- **The draw order holds across a seam.** Where the document's order differs from the draw order, each part carries its whole's z-index, as DEC-040 point 5 has the whole carry it.
- **A keep is an empty box spanning its rows,** one for each keep.

### 5. A fixed page keeps its one element

- **A fixed page,** such as a deck's slide, lies as today, and where it runs on, it breaks where the browser picks (DEC-026 point 1).

### 6. A text in parts is still one text

- **The check for dropped text** matches a text's element, its parts' lines in order, as the scene's one text (DEC-020 point 6).
- **A reader's tools get it whole.** Each element DEC-040 point 1 gives a text, a list, an entry or a figure keeps its role while laid out as no box, and a paragraph's element carries `role="paragraph"` on a page in strips. While a link has focus, each part of its text is raised, since an element laid out as no box takes no z-index (DEC-040 points 1 and 4, which hold these rules by this record's edits).

## Rationale

**Point 1, lines and pictures.** A line cut, or moved over the next, cannot be read (DEC-026 point 1). The font's height is how the engine sets a line and sizes its ground under forced colours (DEC-039 point 1), the renderer reads it with no browser (DEC-020 point 1), and it holds the brand's accents, a háček on a capital among them. Cut back to its step band, a line of a text set closer than its font is tall, such as a heading at a step of 1.1 em, still leaves a place between it and the next, so no text, however it is set, is one strip that a sheet's end cuts through a line. Where a text's step is taller than its font, the font's height leaves a gap, so texts of different steps side by side still meet places. A picture may hold words, so it is kept whole where it fits, as a line is. Only the component's mark says that a picture shows nothing a reader lacks, such as a flourish (DEC-033 point 5). The content's empty text says only that the words around the picture already say it to a reader's tools, and a seeing reader may still read words it holds, such as a screenshot its paragraph describes. A box or a line in two parts reads as one, as a ruled box does across a book's pages. The costs: a diagram may part between its labels; ink past a line's font height, such as a stacked accent, may be cut at a sheet's end; and so may ink past its step band in a text set closer than its font is tall, such as a long descender at a step of 1.1 em.

**Point 2, the keeps.** A heading at a sheet's foot heads nothing on that sheet, and a lone line at a sheet's foot or head reads as a stray. A heading heads its own instance (DEC-033 point 4), and what lies above or beside it is on its sheet already. Two lines are CSS's own default for a paragraph's first and last lines at a break. The heading's rule rests on DEC-033's marks and reading order, so it reaches a piece as the scene comes to hold them. A card or a section kept whole would leave a sheet's foot empty wherever one is taller than what remains, for no line saved.

**Point 3, offered, never forced.** The renderer cannot know where a sheet ends, since the sheet is the reader's (DEC-026 point 4), and a forced break would spend the paper DEC-026 point 1's compact print saves. A place at each end of a gap keeps the gap out of the strips of the lines and pictures around it, so the picture of 0.95 of the area lay in a strip that fit the area, where one place in the gap's middle made the strip taller. Places between the lines over or beside a picture let a picture taller than a sheet break between lines, where its strip alone would be cut through one. A keep that could never yield would run on past the sheet's end, where Firefox 148 lost every line past it, so a keep yields where it does not fit. Each keep is a box of its own, so the keeps inside one that yields still hold, which keeps merged into one box did not.

**Point 4, one grid.** CSS breaks only between boxes in the document's flow, and a grid's rows are such boxes, whatever order the document gives its items. So the reading order, which a reader's tools, the keyboard and a selection follow (DEC-040 point 5), stays the document's, where a stack of strips would order the document strip by strip. In the tree's order the grid paints as today, and z-index carries the draw order where the orders differ, so no later strip paints over ink that crosses a seam. A text a break may part is in parts, since one element across rows was cut, and its element stays one, laid out as no box, so the text and the elements around it keep their place in the document, where a subgrid let keeps break. A keep is a box of its own, since Firefox ignored keeps set on a row's items. Row heights a browser rounds add up, so lines drift down a tall page unless each row's top is set from the scene. A shape drawn by reference lies once in the file however many strips it crosses.

**Point 5, fixed pages.** A fixed page shrinks to the area's width and the room its keyline leaves (DEC-026 points 2 and 3), and a 16:9 slide fits A4 and Letter either way up (`outputs.md`, Printing), so a slide never runs on. Strips would part its texts for nothing in print. The cost: a fixed page that runs on breaks where the browser picks, such as a handout's A4 page printed on Letter, which at Letter's width is taller than its area.

**Point 6, one text.** The step matches the scene's texts to the document (DEC-020 point 6), and a text in parts is still one text of the scene, in one element. A reader's tools follow elements, and an element laid out as no box keeps its place among them: Chrome kept each heading, list, entry and figure so. Chrome left out a paragraph so laid out, and the paragraph's role puts it back, as DEC-040 point 1 allows a role where an element alone does not reach a reader's tools. A z-index on an element laid out as no box raises nothing, so a focused link's raise lies on its text's parts.

### Alternatives considered

- **The break left to the browser,** as today: Chrome printed lines across a sheet's edge and cut pictures, and Firefox lost lines and shapes or set text off its tints.
- **Rules of the file on today's elements,** such as `break-inside: avoid` on each text: they print as no rule does, since the elements lie outside the flow (DEC-026, Alternatives).
- **Strips that hold nothing, under today's elements:** each browser set the elements by the sheet's end, and text parted from its shapes.
- **A stack of strip boxes in the flow:** its document runs strip by strip, not in reading order, and a later strip paints over ink that crosses a seam.
- **Strips that clip what overflows them,** on one axis or both: they cut a line's ink past its strip, against DEC-020 point 4, and the shrink they seemed to mend came from printing before the faces had loaded.
- **A text one element spanning its rows:** Chrome and Firefox 148 printed its lines across a sheet's edge, and Firefox set headings apart from their text.
- **The elements around a text's parts as subgrids:** each browser set a heading apart from its text or left a line alone.
- **Each part of a text an element of its own, with none around them:** a text would be several elements, where DEC-040 point 1 gives each text one, the element of its mark.
- **Keeps as `break-after: avoid` on a row's items:** Firefox ignored them in a grid.
- **Keeps that never yield:** a keep taller than a sheet runs on, where Firefox 148 lost every line past the sheet's end when each text was kept whole.
- **Keeps merged where they overlap:** each browser left a line alone on a sheet where the merged keep yielded.
- **A picture with a text over it as a ground, not a keep,** parting between the text's lines with only the text's keeps holding: a box for each keep already keeps that text's lines together, and a picture that would fit a fresh sheet would part.
- **A line's extent as its ink:** it differs with each string, so the place moves as the words change, and the renderer would have to draw each line to find it.
- **A line's extent as its step band alone:** texts side by side at different steps may then touch at no height, leaving no place.
- **A line's extent as its font's height, uncut:** a text set closer than its font is tall has no place between its lines, so where it is taller than a sheet, the sheet's end cuts it through a line, as Chrome and Firefox did.
- **One place in a gap's middle:** a strip then holds half of each gap around a picture, so a picture that fits a sheet may lie in a strip that does not, which Chrome cut.
- **A heading kept with what follows past its instance:** it would keep one instance's heading with another's, which it does not head.
- **Each instance kept whole where it fits,** such as a card or a diagram: one taller than what remains of a sheet leaves the rest of it empty.
- **Every picture cut as any shape, or each one marked as needing no text:** a picture may hold words, and one the content gives an empty text may too.
- **A shape a seam parts copied into each part:** each id would lie in every strip the shape reaches (DEC-020 point 4), and the test's file grew from under 1 MB to 22.8 MB.
- **A break forced before a page or a section:** the renderer does not know the sheet, and DEC-026 point 1's print is compact.
- **A page cut at a sheet the renderer assumes:** the sheet is the reader's (DEC-026 point 4).
- **A text's lines in the flow inside one element:** its shapes would still lie in layers the size of the page, which Firefox printed on the first sheet alone.
- **Strips on a fixed page too:** a slide never runs on, so its texts would part for nothing.

## Implications

- **Ordered after [visual-communication:DEC-037-text-the-page-hides], DEC-039 and DEC-040,** each drafted before it. This record is accepted after them, and its edits of DEC-020 and DEC-040 are written against their wording.
- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-026 point 1, "It is to break between a text's lines, never through one", comes to cite this record as the record on breaks. It refines the point.
  - DEC-026 point 1, "Until then the browser picks where it breaks", comes to say that a page that is no fixed page breaks only at the places its file offers, which forces none (points 1 to 4), and that a fixed page that runs on breaks where the browser picks (point 5). It replaces that bullet.
  - DEC-026 point 7, "A test on the file", comes to hold the places and the keeps a page's file offers too. It refines the point.
  - DEC-026's Rationale, "Point 1, pages one after another": "The break waits for a record of its own" comes to cite this record. It refines the passage.
  - DEC-020's term *layer* comes to read one `svg` element the size of a page, or of a strip of one (point 4). It refines the term.
  - DEC-020 point 2, "A text is one element" and "A text stays one element", come to say that on a page that is no fixed page, a text's one element is laid out as no box and holds a part in each strip its lines lie in, at the text's left and width in that strip's row (point 4). It overturns the point in part, since the element no longer lies at its frame there.
  - DEC-020 point 3, as DEC-040 words it, comes to say that a page that is no fixed page is one grid, each element in its strip's row; that a text's, a layer's or a run's grounds' parts lie together at its place in the document; and that each part carries its whole's z-index (point 4). It refines the point.
  - DEC-020 point 4, "The pages follow each other down the document", comes to say that in print a taller page that is no fixed page breaks only at the places its file offers (points 3 and 4). It refines the point.
  - DEC-020 point 4, "The file marks what the step reads", as DEC-039 words it, comes to add each part of a shape, with the shape's trace id. The shared drawing marks each shape so today, a mark that point does not name. It refines the point.
  - DEC-020 point 6, "The words", comes to read a text's lines through its parts, in order, as one text (point 6). It refines the point.
  - DEC-040 point 1, its first bullet, comes to add, after its list's role, that on a page in strips each paragraph's element carries `role="paragraph"`, since Chrome leaves a paragraph laid out as no box out of a reader's tools (point 6). Its second bullet's "a paragraph's element holds them" comes to add "through its parts, on a page in strips" (point 4). It refines the point.
  - DEC-040 point 4, "The text that holds a focused link draws over every shape of its page", comes to say that on a page in strips each part of that text is raised, since its element is laid out as no box (point 6). It refines the point.
- **Edits to the capability's page on outputs** (`outputs.md`), made in this change once this record is accepted, each anchored to it. Printing's "Where a page that runs on breaks" and "Firefox and a page narrower than the area" come to say that this record decides them, and what a reader gets in each browser before the Task below lands and after it: before, what they say now; after, a page that breaks only between lines, each picture that fits a sheet whole, each heading on the sheet of what it heads, and in Firefox a page narrower than the area with its text on its shapes, with Safari's print still a person's check. They link to this record's runs and copy none of them. The page anchors DEC-020 points 2, 3, 4 and 6 and DEC-026, so the edits above ask its answers in this change.
- **The Task that lays a page out in strips,** filed under [project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570) once this record is accepted, builds points 1 to 6 from their rules, not from the test's script, at a new version of the renderer ([visual-communication:DEC-005-engine-and-plugins] point 9). Its tests on the plan hold where places and keeps fall with no browser, an instance with a text of its own among them. Where DEC-040's Tasks land first, it lays their elements out as point 4 does, and where it lands first, each of them builds its elements so. Point 2's rule on a heading comes with DEC-033's change of a text's structure, which brings headings into the scene.
- **#3012's body,** edited once this record is accepted, comes to say that strips mended its cases where a sheet's end cut a page or parted text from its shapes, in Firefox 157 and 148; that Firefox 157 shrank a page it printed before the page's faces had loaded, in today's form and in strips alike, a cost no rule of the file mends; that Firefox's print leaves a clip that holds a reference to its shape unapplied, which DEC-039 point 4's clipped shape takes under forced colours; and that it tests its other cases on strips once the Task lands. Its Dependencies come to name the Task.
- **[project-kit#2851](https://github.com/aleskalfas/project-kit/issues/2851)'s body,** edited once this record is accepted, comes to ask the person to print a page that runs on in each browser once the Task lands, and to say whether any line, or any picture that fits a sheet, was cut, in place of its line that they print none.
- **[project-kit#3118](https://github.com/aleskalfas/project-kit/issues/3118)'s body,** edited once this record is accepted, comes to read against this record, since a text a break may part lies in parts (point 4).
- **Read against, and left as they stand:**
  - DEC-020 point 2's strut and shares of the page's width, which a row's height takes too.
  - DEC-020 point 4, "Each id lies once": a shape a seam parts is defined once, and its parts share its trace id, which is no HTML id.
  - DEC-020 point 4, "A page clips no text": no strip clips either.
  - DEC-022 point 7's bands, which cut a page's image, not its file.
  - DEC-026 point 2: a page in strips still shrinks only to the area's width.
  - DEC-026 point 6, under which the renderer declares the places and keeps its file offers, as rules of point 1.
  - DEC-026's alternative "A tall page cut into bands". This record takes on the cost DEC-026 rejected bands for: a shape a strip's edge crosses lies in each strip it reaches. The cost is acceptable here, since the shape's geometry lies once, drawn by reference, so each HTML id still lies once, and since a strip is no page a reader meets: its edges fall where no line lies, never at a sheet's height the renderer assumes, and the page stays one element.
  - DEC-026's revisit where the record on breaks has the file ask for a break: this record forces none.
  - [visual-communication:DEC-031-html-page-backdrop] points 1 to 4, since a fixed page keeps its form.
  - DEC-033 points 4 to 6, on which point 2 rests, and DEC-033 point 5's two marks of a picture that needs no text, of which point 1 lets only the component's cross a break.
  - DEC-037's reads: a seam clips and covers nothing, so a span cut or covered there is named as anywhere.
  - DEC-039 point 1: a line's ground lies in its line's strip, beneath the lines of its run as before.
  - DEC-039 point 4: a clipped shape a seam parts keeps its geometry once, its clip with it (point 4). Firefox's print leaves such a clip unapplied in parts as on a lone shape, so it is no cost of parts, and #3012 takes it up.
  - DEC-040 point 2, since the elements around texts, laid out as no box, are neither positioned nor a size container; point 5, since a whole in parts lies where the whole would, each part carrying its z-index as DEC-020 point 3 comes to say; and point 7, since a picture's element still lies at its picture's frame.
- **Revisit this record** if a browser as shipped breaks inside a strip that fits a sheet's area, or cuts a line in a strip that fits; if strips move a line's box on screen by a device pixel, read by layout, since a line's ink snaps to a device row; if Firefox shrinks a page in strips whose faces have loaded; if a reader's tools, a selection or find cannot take a text in parts as one; if #3118's record keeps a text's lines in one flow; if a piece needs a diagram kept whole on a sheet; or if a piece comes to need a fixed page that runs on.
