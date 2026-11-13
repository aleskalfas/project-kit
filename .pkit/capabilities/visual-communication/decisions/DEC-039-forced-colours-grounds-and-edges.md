---
id: DEC-039
title: Under forced colours, the HTML page draws its texts' grounds beneath their lines, and an opaque fill's edge inside the fill
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a reader who forces their own colours reads each line of text on a ground of their background colour, which the browser paints behind the line with the line itself. So where lines lie closer than their font is tall, each line's ground covers the descenders of the line above, within a text and from one text to the next, in every language. Under forced colours the HTML renderer's file draws those grounds instead: one for each line, over the area the browser's would cover, all beneath every line of a run of texts with nothing between them. The browser still colours the letters. The edge a forced palette gives an opaque fill lies inside the fill, so a box covers under forced colours what it covers in its own colours. For example, a two-line heading set at 1.1 em, or a heading set close above its body text, keeps the tails of its g, j, p and y under a forced palette, as it does in its own colours.

## Context

[project-kit#3088](https://github.com/aleskalfas/project-kit/issues/3088) asks that the look report name every text the drawn page does not show. Its probes found three covers that forced colours alone make, and that no piece can see in its own colours:
- **A text's own lines.** The browser paints each line's backplate with that line. At a line step of 1.1 em, the second line's backplate covered the descenders of the first, in both forced palettes.
- **One text over the next.** A heading set close above body text lost the foot of its descenders under the body's backplate, in both forced palettes, and nothing in its own colours.
- **A forced edge.** The record of modes gives a fill opaque in every key an edge in the reader's text colour under forced colours ([visual-communication:DEC-023-html-page-modes] point 7). Centred on the fill's outline, half of it lies outside the fill.

On 13 November 2026 the project manager moved how the file draws a text's ground out of the record of text the page hides ([visual-communication:DEC-037-text-the-page-hides]) into this one, after the architect's review of that record and the critic's second. They chose its shape: one ground for each line, beneath all of the text's lines, sized from the engine's measures with a declared margin, the edge inside the fill, and a run's ground taken into its line's where the same means covers it. Later that day, after the architect's second read and the critic's third, they widened the grounds to a run of texts with nothing between them, had each opaque fill clipped to its own shape, and had the renderer read the faces' ascent and descent as the engine reads them. After the architect's third read and the critic's fourth, they had a box, a rounded box and an ellipse drawn as a fill under an inset shape, kept the clip for a path and a sign in the forced rule alone, and left the clip to a test of the file and a person's look. On that revision's open points, they had DEC-037's edge control sized from the start's scale, and the cover a path leaves followed up in [project-kit#3122](https://github.com/aleskalfas/project-kit/issues/3122).

Terms:
- A *backplate* is the ground a browser paints behind text under forced colours, in the forced palette's ground colour. Each line of the renderer's page is a block of its own, and Chrome paints one for each, with that line.
- A line's *ground*, here, is what the file draws in its place.
- A text's *line step* is how far apart its lines' baselines lie.
- A *run of texts* is texts that follow one another among a page's leaves, in draw order, with no other part between them.

### What the probes showed

The second, third and fourth of the probes DEC-037 names drew one page of the HTML renderer in Chrome 157 on one Mac, through the viewing step's browser module, at device scales of 2 and 1.225, in the start without forced colours and in both forced palettes. The second read a ground for each text and a clip to each fill's box, the third the run of texts and a clip that reused each shape's geometry in every mode, and the fourth this record's form. The fifth read DEC-037's edge control alone in this record's form, at 0.625, 1, 1.225 and 2. Each text's lines and widths were the engine's, measured from the face the file embeds, its ascent and descent read as the engine reads them. Each wrote the page through the renderer's own code changed in the probe alone, with no script in the page. Their code is thrown away.

- **A text's own lines.** The first line of a 32 px heading at a step of 1.1 em lost 5.6 to 6.9% of its strong ink under the browser's backplates, and none on the file's grounds, in both forced palettes, at both scales.
- **A run's ground.** With its second line a run on a ground, the first line lost 6.4 to 7.1% in every mode. Under forced colours, on the file's grounds, it lost none. Outside forced colours it lost as much as before.
- **Between texts.** A 24 px heading set at a step of 1.1 em close above body text lost 0.016 and 0.022 em² under the body's backplate, in the light and the dark forced palette at a scale of 2, and 0.002 and 0.009 em² at 1.225. With the grounds of both beneath both, it lost none. Words under a later text lost 74 to 75% on the backplates, and 25 to 35% on the run's grounds, about what their letters' overlap loses in their own colours. With a box between the two texts in the tree, the heading lost as much as on the backplates.
- **The area a ground hides.** Over an earlier translucent fill at 1.225, the file's grounds hid every pixel the browser's backplates hid, and beyond them only the margin's strips, 50 to 120 px² for a 24 px text of two lines. At a scale of 2 the backplates also hid 33 and 38 px² beside a 16 px line with a sign or a run's ground: one device row at the line's foot, below every letter, where the browser's box of the span ends a fraction of a pixel lower than the file's ground. Beside a 16 px sign, the grounds also hid 184 to 193 px² the backplate left showing: the sign's gap and its square to the line's height, which the backplate leaves out. A box around each text's spans would have hidden 10 000 to 12 400 px², against 6 600 to 7 700 px² for the backplates.
- **The tails.** At a margin of 1 px, every line's spans lay inside its ground, with at least 0.98 px to spare at each end. The browser's boxes passed the faces' ascent and descent by at most 0.22 px, where no letter reached.
- **The colours.** On the file's grounds, the spans took the forced palette's text colour, a run's sign its fill and its edge, and each ground the palette's ground colour.
- **The edge beside a fill.** A centred 1 px forced edge lay half outside its fill: 65 to 91 px² outside a box, a rounded box, an ellipse and a triangle's path, each 60 by 30 px, at a scale of 2. Drawn as point 4 has it, each left outside its outline about what its own colours leave there, or less, at both scales, and so did a sign that does not fill its square and a shape with a hole drawn even-odd. Clipped by the non-zero rule, the hole's doubled edge showed whole, 76 to 95 px² outside.
- **A text resting on a fill's edge.** At 1.225, 16 px capitals whose feet rest on a later box's top edge lost nothing in their own colours, and 0.19 and 0.20 em² under the light and the dark forced palette, with the edge centred, or clipped with the fill as the third probe drew it. Placed at nine steps an eighth of a device pixel apart, a box drawn as point 4 has it lost at each step what it lost in its own colours, at both scales and in both palettes. A path lost its letters' last device row, 0.078 to 0.086 em², at two of the nine steps, from flush to an eighth below, where its own colours lost nothing, and a square sign lost what its own colours did. At a scale of 2, none lost anything in any mode.
- **The edge control.** Its em set to the same number of device pixels at each of the four scales, a box drawn as point 4 has it, its edge at the foot of the control's descenders, hid the control's last device row or nothing, at nine steps an eighth of a device pixel apart, in every mode.
- **Every reader's page.** Outside forced colours, the file in this record's form drew the same image as today's to the pixel, at both scales.
- **A lost clip.** With the clip left out, a path's and a sign's doubled edge lay a full declared width outside their outline, about twice what a centred edge spills: 188 against 104 px² outside the triangle at 1.225. A text resting on the path lost 0.05 to 0.17 em² at every step.

**Not reached:** a real forced palette on Windows, Firefox's forced colours, another browser, Linux, a reader's minimum font size or own text spacing, a sign that rises above its run's letters, right-to-left text, a run in two families, a fill in a moved group, a text resting on a curved edge, a link inside a line.

## Decision

**Under forced colours, the HTML renderer's file draws a ground in the reader's background colour for each line of a text, beneath all the lines of its run of texts, and keeps its lines out of the browser's backplate. The browser still colours the letters, and an opaque fill's forced edge lies inside the fill.**

### 1. Each line lies on a ground the file draws

- **Beneath a run of texts.** The grounds of a run of texts, one for each line, all lie beneath all of the run's lines in the order the browser paints. So no line's ground covers a line of its own text, or of another text in the run. Where a part lies between two texts, the later text's grounds lie over it, as the draw order has them. Where a `z-index` carries the draw order, a z-index below the run's texts carries the grounds' place.
- **Over the backplate's area, and a sign's square.** A line's ground covers what the browser's backplate would, from the line's start to its end and from the highest ascent to the lowest descent of its runs' faces, and the square of each sign on the line with its gap. Beyond it, only the margin at each end.
- **The lines take no backplate,** and the browser colours their letters in the reader's text colour.
- **A ground takes no pointer,** so a text under it can still be selected.
- **Outside forced colours** a line's ground draws nothing.

### 2. A ground is sized from the engine's measures, with no script

- **From the scene and the faces.** The renderer places each ground from the engine's width of the line, the text's anchor, and the ascent and descent of its runs' faces. It reads those from the faces it embeds, as the engine reads them, so the seam's version is unchanged ([visual-communication:DEC-005-engine-and-plugins] point 8). It widens each ground at each end by a margin it declares, for the browser's own widths. The file holds no script ([visual-communication:DEC-023-html-page-modes] point 4).
- **No line's tail lies outside its ground** at the sizes the file sets. The margin is wider than any difference found between the engine's width of a line and a browser's ([visual-communication:DEC-020-html-page-drawing], Context).

### 3. Under forced colours a run's ground lies in its line's ground

- **Under forced colours** a run's ground ([visual-communication:DEC-036-concept-signs] point 3) is part of its line's ground, and its span draws none of its own. So it covers no line above. Its sign keeps the rule DEC-036 point 4 gives it.
- **Outside forced colours** a run's ground keeps its colour and lies with its run. Where its text's line step is below its height, it covers the descenders of the line above, as letters that touch across such lines do. Both stay known gaps, which a wider line step in the brand's spacing mends until [project-kit#3114](https://github.com/aleskalfas/project-kit/issues/3114) lands.

### 4. An opaque fill's forced edge lies inside the fill

This holds for each fill opaque in every key with no stroke of its own, which DEC-023 point 7 gives an edge under forced colours.
- **A box, a rounded box and an ellipse.** Under forced colours the fill takes the reader's text colour, and over it the file draws the same shape inset by the edge's width, in the reader's background colour, with no clip and no edge. Outside forced colours one rule hides the inset shape. So such a fill covers under forced colours what it covers in its own colours, and nothing beside it.
- **A path and a sign.** Under forced colours alone, by the forced rule, each is clipped to its own shape, and its edge drawn twice as wide, so only its inner half shows. Its geometry lies once in the file, drawn through a use that carries the clip and clipped by a use of the same definition. The clip takes the shape's fill rule as its clip rule.
- **A known gap: a path's or a sign's outline pixel.** The fill and its clipped edge both smooth that pixel, so at the step's scale they may together hide a device row of a text that rests on the outline, which its own colours show. The report names it (DEC-037), and [project-kit#3122](https://github.com/aleskalfas/project-kit/issues/3122) follows it up.

### 5. What holds the grounds and the edge

- **The forced start's first read holds the grounds and the forcing.** The text left to forcing in the forced start's planted page ([visual-communication:DEC-027-forced-colours-viewing] point 4) lies on the file's grounds, its lines kept out of the backplate, as point 1 has it. So where a browser stops forcing a span in such a line, that span shows no ink, and the run stops.
- **The edge control is set in device pixels.** The forced start's first read sizes DEC-037's edge control so its em covers the same number of device pixels at every device scale a start uses, its box drawn as point 4 has it. So its last device row is the same share of its em in every start, and the sliver set once from that row leaves it unnamed at every scale (DEC-037 point 5).
- **#3088's test of the file and a person's look hold the edge,** since no plant catches a lost clip at every device scale. A browser that drops the clip shows a path's or a sign's doubled edge centred on its outline, a full declared width outside it. A box, a rounded box and an ellipse have no clip to lose.

## Rationale

**Which cover the renderer removes.** A cover only forced colours cause is the renderer's to remove: the piece's own images never show it, and a piece could mend it only by changing its page for every reader. A cover the piece's own images show is the piece's to mend. Two such covers stay, as exceptions the report names (DEC-037). One is a part between two texts in the draw order, which the later text's grounds lie over: telling a part that meets the text from one that does not asks the renderer to compute where parts meet, which the draw order avoids by construction (DEC-020 point 3). The piece mends it in its draw order, drawing the part before both texts or after both, which changes no other reader's page. The other is a path's or a sign's outline pixel (point 4).

**Why the file draws a line's ground.** A reader who forces their colours loses the descenders of each line set closer than its font is tall, within a text and from one text to the next. That holds in every language and every forced image, whether or not a report names it. The step between lines comes from a brand's typography, so no piece's layout mends it alone. The file draws the ground the browser would, in an order that covers no line of the run.

**Why a run of texts.** Nothing lies between such texts in the draw order, so drawing all of their grounds first hides nothing that order means to show. A later text's letters still lie over an earlier text's, as they do in the piece's own colours.

**Why one ground for each line.** It keeps the backplate's shape, so it hides little a backplate leaves showing. One ground behind a whole text would also hide what lies beside a short line or between paragraphs, such as a picture, a chart's line or a translucent fill. It would hide it in forced images alone, where nothing names a shape a text hides. A sign's square is the one place a ground hides more than a backplate, so a sign keeps a plain ground as its run's letters do.

**Why from the engine's measures, with a margin.** With no script, only the scene and the faces can size a ground. The engine measures each line from the face the file embeds, within a fraction of a pixel of each browser's widths, and the margin takes up the rest. Read as the engine reads them, the faces' metrics add no field to the seam. A browser on another system may size a line from another of the font's metric tables, which a look on Windows reaches. The trade: where a reader's minimum font size or own text spacing grows a line past the engine's measure, the part past its ground loses the backplate the browser would have grown with it. Under forced colours the page and every opaque fill take the reader's background colour, so such a tail still lies on that colour, unless it reaches a picture, a translucent fill or a line. That trade is taken knowingly.

**Why every line, and not only where a backplate would cover ink.** The file could draw grounds only where a backplate would cover a text's ink, where a text's line step is below its lines' height or a run's texts meet, and leave the browser its backplates elsewhere, which grow with a reader's settings. Finding where two texts meet asks the renderer to compute where elements meet, which the record of HTML pages avoids by construction (DEC-020 point 3). Two forms under forced colours would also each need a plant in the first read. So every line takes the file's ground, with the trade above.

**Why the browser still colours the letters.** The colours are the reader's, and the file adds none of its own (DEC-023 point 7).

**Why a run's ground joins its line's under forced colours.** There a run's ground takes the reader's background colour, as its line's does, so the line's ground shows it unchanged. Drawn with its run, it would cover the line above. Outside forced colours it keeps its own colour, and its place at the browser's widths, which only its span knows (DEC-020 point 2). Placing it beneath all of a text's lines there is #3114's work, and until then a wider line step mends the gap.

**Why the edge inside the fill, and two ways of drawing it.** Centred on the outline, half the edge lies over whatever lies beside the fill, in forced images alone. A fill clipped with its edge smooths its outline's pixel twice, once for the fill and once for the edge, so a text resting on it loses its feet there under forced colours alone. A fill in the text colour under an inset shape smooths that pixel once, as its own colours do, and holds nothing a browser can drop. SVG insets a box, a rounded box and an ellipse by their own attributes, but no path, so a path and a sign keep the clip. Their geometry, held once, gives a clip that refers to no shape it clips, and their fill rule keeps a hole's edge inside. Each applies under forced colours alone, so no other reader's page changes (DEC-020 point 1).

### Alternatives considered

- **One ground behind all of a text's lines:** it hides what lies beside a short line and between paragraphs.
- **A ground the size of the text's frame:** a short title blanks its frame's whole width.
- **A text's lines in reverse order:** the overlap would cover the tops of the line below.
- **A text's lines flowing in one element, so the browser paints their backplates first:** flowing lines leave the place the engine gave them (DEC-020 point 2).
- **Grounds sized in the page by a script:** the file holds none (DEC-023 point 4).
- **Each text's grounds beneath its own lines alone:** a later text's ground still covers the descenders of the text above it, a cover forced colours alone make.
- **A run's grounds beneath a part that lies between its texts, where the part does not meet them:** the renderer would compute where parts meet.
- **Grounds only where a backplate would cover ink:** the renderer would compute where texts meet.
- **The faces' metrics carried in the scene:** a new field raises the seam's version, for metrics the renderer reads from the faces it embeds.
- **The browser's backplates left as they are, and the loss named in the report:** the reader still loses the descenders, and no piece can mend it.
- **The edge centred on the outline, its cover left to the piece:** the piece's own images never show it.
- **The edge clipped to the fill's box:** half of it still lies outside a rounded box, an ellipse or a path.
- **A box, a rounded box and an ellipse clipped to their own shape:** a text resting on the fill loses its feet under forced colours alone.
- **The clip as an attribute every mode reads:** it changes every reader's fills.
- **A use of the shape that carries the clip as its own clip:** the clip refers to the shape it clips, a cycle a browser may refuse.
- **No edge on an opaque fill:** the fill would lose its outline on the reader's ground (DEC-023 point 7).

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-023 point 7, "Under forced colours".** "The browser colours the text itself" comes to add that each line lies on a ground the file draws in the reader's background colour, beneath all the lines of its run of texts, and takes no backplate. "With an edge in that text colour" comes to say that, for a fill with no stroke of its own, the edge lies inside the fill: a box, a rounded box or an ellipse takes the text colour under the same shape inset in the background colour, and a path or a sign is clipped to its own shape.
  - **DEC-023 point 7, "The renderer declares these choices".** It comes to name the grounds' margin beside the edge's width.
  - **DEC-020 point 4, "The file marks what the step reads".** It comes to add each line's ground, with its text's trace id, so the step finds it.
  - **DEC-036 point 3, "Held with the run".** It comes to add that under forced colours the HTML renderer draws a run's ground in its line's ground, and its span draws none of its own.
  - **DEC-027 point 4, "One more span with no paint, left to forcing".** It comes to add that what is left to forcing lies on the file's grounds, its lines kept out of the backplate.
- **#3088** builds points 1 to 5, at a new version of the HTML renderer (DEC-005 point 9). Its test of the file holds that the grounds lie beneath the lines of a run of texts and over a part between two texts, as the engine measures them with the margin, and take no pointer; that a sign and a run's ground still take forced colours; that a box, a rounded box and an ellipse take the inset shape, and a path, a sign that does not fill its square and a shape with a hole take the clip, with the fill rule as its clip rule; and that no clip and no inset shape applies outside the forced rule.
- **The capability's page on outputs** comes to say how the file draws a text's grounds and a fill's edge under forced colours, with the margin's number, in #3088's change.
- **Before #3088 closes,** a person looks at a page under a real forced palette, in Edge or Chrome on Windows and in Firefox, a rounded box and a path among its parts. The look on Windows also reaches a browser that sizes a line from another of the font's metric tables.
- **Read against this record, and left as they stand:**
  - DEC-020 point 1. Outside forced colours a fill is drawn unclipped and the inset shape is hidden, so the layers are drawn as the SVG renderer draws them.
  - DEC-020 point 2. A text stays one element, and no line flows. A run's grounds are elements of their own, and hold no text.
  - DEC-020 point 3. The draw order holds: a part between two texts lies over the first text and under the second's grounds. Point 1's grounds take no pointer and, where a z-index carries the draw order, lie below the run's texts by one, which [project-kit#2740](https://github.com/aleskalfas/project-kit/issues/2740) inherits.
  - DEC-020 point 4, "A page clips no text". A fill's clip clips nothing but its own fill.
  - DEC-023 point 4. The file holds no script.
  - [visual-communication:DEC-026-html-page-print] point 5. Print takes the rule for forced colours as the screen does, so the grounds and the edge reach print too.
  - [visual-communication:DEC-031-html-page-backdrop] point 3. Under forced colours a fixed page lies on the reader's background colour, the grounds' colour.
  - [visual-communication:DEC-033-structure-for-readers] points 2 and 3. A line is kept out of forcing and its spans are forced, so an element a later change puts inside a line, a link, emphasis or strong among them, keeps the reader's colours, and a link the reader's link colour (DEC-027 point 6). The change that builds links in the HTML page proves it.
  - DEC-033 point 6. A ground holds no text, so it takes no place in the reading order.
- **Revisit this record** if a browser paints a backplate behind a line kept out of it, or stops forcing a span in one, if a line's tail passes its ground in a browser, if a browser update stops honouring the clip, or if a real forced palette, or Firefox's, meets the grounds, the inset shape or the clip otherwise than Chrome did.
