---
id: DEC-039
title: Under forced colours, the HTML page draws each line's ground beneath all of its text's lines
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a reader who forces their own colours reads each line of text on a ground of their background colour, which the browser paints behind the line with the line itself. So where a text's lines lie closer than its font is tall, each line's ground covers the descenders of the line above, in every language. Under forced colours the HTML renderer's file draws those grounds instead: one for each line, over the area the browser's would cover, all beneath every line of the text. The browser still colours the letters. The edge a forced palette gives an opaque fill lies inside the fill, so it covers nothing beside it. For example, a two-line heading set at 1.1 em keeps the tails of its g, j, p and y under a forced palette, as it does in its own colours.

## Context

[project-kit#3088](https://github.com/aleskalfas/project-kit/issues/3088) asks that the look report name every text the drawn page does not show. Its probes found two covers that forced colours alone make, and that no piece can see in its own colours:
- **A text's own lines.** The browser paints each line's backplate with that line. At a line step of 1.1 em, the second line's backplate covered the descenders of the first, in both forced palettes.
- **A forced edge.** The record of modes gives a fill opaque in every key an edge in the reader's text colour under forced colours ([visual-communication:DEC-023-html-page-modes] point 7). Centred on the fill's outline, half of it lies outside the fill, and where the fill met the foot of a text's descenders it reached over their tips.

On 13 November 2026 the project manager moved how the file draws a text's ground out of the record of text the page hides ([visual-communication:DEC-037-text-the-page-hides]) into this one, after the architect's review of that record and the critic's second. They chose its shape: one ground for each line, beneath all of the text's lines, sized from the engine's measures with a declared margin, the edge inside the fill, and a run's ground taken into its line's where the same means covers it.

Terms:
- A *backplate* is the ground a browser paints behind text under forced colours, in the forced palette's ground colour. Each line of the renderer's page is a block of its own, and Chrome paints one for each, with that line.
- A line's *ground*, here, is what the file draws in its place.
- A text's *line step* is how far apart its lines' baselines lie.

### What the probe showed

The probe drew one page of the HTML renderer in Chrome 157 on one Mac, through the viewing step's browser module, at device scales of 2 and 1.225, in the start without forced colours and in both forced palettes. Each text's lines and widths were the engine's, measured from the face the file embeds. It read two files of that page: one as the renderer writes it, and one in this record's form, written by the renderer's own code changed in the probe alone, with no script in the page. Its code is thrown away.

- **A text's own lines.** The first line of a 32 px heading at a step of 1.1 em lost 5.6 to 6.9% of its strong ink under the browser's backplates, and none on the file's grounds, in both forced palettes, at both scales.
- **A run's ground.** With its second line a run on a ground, the first line lost 6.4 to 7.1% in every mode. Under forced colours, on the file's grounds, it lost none. Outside forced colours it lost as much as before.
- **The area a ground hides.** Over an earlier translucent fill, the file's grounds hid every pixel the browser's backplates hid, and beyond them only the margin's strips, 50 to 120 px² for a text of two lines. A box around each text's spans would have hidden 10 000 to 12 400 px², against 6 600 to 7 700 px² for the backplates.
- **The tails.** At a margin of 1 px, every line's spans lay inside its ground, with at least 0.99 px to spare at each end. The browser's boxes passed the font's ascent and descent by at most 0.22 px, where no letter reached.
- **The colours.** On the file's grounds, the spans took the forced palette's text colour, a run's sign its fill and its edge, and each ground the palette's ground colour.
- **The edge.** A box's 1 px forced edge lay half outside it: 91 of 180 px² at a scale of 2. Drawn 2 px wide and clipped to the box's outline, none of it lay outside.
- **Between texts nothing changed.** Words under a later text lost 74 to 77% in both forced palettes, and a heading set close above body text lost 0.2 to 1.5%, in both files.

**Not reached:** a real forced palette on Windows, Firefox's forced colours, another browser, Linux, a reader's minimum font size, a fill other than a rectangle, a sign that rises above its run's letters, right-to-left text, a run in two families.

## Decision

**Under forced colours, the HTML renderer's file draws a ground in the reader's background colour for each line of a text, beneath all of that text's lines, and keeps its lines out of the browser's backplate. The browser still colours the letters, and an opaque fill's forced edge lies inside the fill.**

### 1. Each line lies on a ground the file draws

- **All first.** A text's grounds, one for each of its lines, all lie beneath all of its lines. So no line's ground covers another line of the same text.
- **Over the backplate's area.** A line's ground covers what the browser's backplate would: from the line's start to its end, and from the highest ascent to the lowest descent of its runs' fonts, a sign's reach included. So beside a short line it hides nothing a backplate leaves showing.
- **The lines take no backplate,** and the browser colours their letters in the reader's text colour.
- **Outside forced colours** a line's ground draws nothing.

### 2. A ground is sized from the engine's measures, with no script

- **From the scene.** The renderer places each ground from the engine's width of the line, the text's anchor and its runs' fonts' ascent and descent. It widens it at each end by a margin it declares, for the browser's own widths. The file holds no script ([visual-communication:DEC-023-html-page-modes] point 4).
- **No line's tail lies outside its ground** at the sizes the file sets. The margin is wider than any difference found between the engine's width of a line and a browser's ([visual-communication:DEC-020-html-page-drawing], Context).

### 3. Under forced colours a run's ground lies in its line's ground

- **Under forced colours** a run's ground ([visual-communication:DEC-036-concept-signs] point 3) is part of its line's ground, and its span draws none of its own. So it covers no line above. Its sign keeps the rule DEC-036 point 4 gives it.
- **Outside forced colours** a run's ground keeps its colour and lies with its run. Where its text's line step is below its height, it covers the descenders of the line above, as letters that touch across such lines do. Both stay known gaps, which the step that sets the lines mends.

### 4. An opaque fill's forced edge lies inside it

- **Inside the outline.** The edge DEC-023 point 7 gives a fill opaque in every key lies inside the fill, along its outline, at the width the renderer declares. So a fill covers under forced colours what it covers in its own colours, and nothing beside it. A sign's fill takes the same (DEC-036 point 4).

### 5. The forced start's first read holds it

- **The span left to forcing** in the forced start's planted page ([visual-communication:DEC-027-forced-colours-viewing] point 4) lies in a line kept out of the backplate, on the file's ground, as point 1 has it. So where a browser stops forcing a span in such a line, that span shows no ink, and the run stops.

## Rationale

**Why the file draws a line's ground.** A reader who forces their colours loses the descenders of each line but a text's last, wherever its line step is below its font's height. That holds in every language and every forced image, whether or not a report names it. No piece's layout mends it, since the step comes from a brand's typography. The file draws the ground the browser would, in an order that covers no line of the same text.

**Why one ground for each line.** It keeps the backplate's shape, so it hides nothing a backplate leaves showing. One ground behind a whole text would also hide what lies beside a short line or between paragraphs, such as a picture, a chart's line or a translucent fill. It would hide it in forced images alone, where nothing names a shape a text hides.

**Why from the engine's measures, with a margin.** With no script, only the scene can size a ground. The engine measures each line from the face the file embeds, within a fraction of a pixel of each browser's widths, and the margin takes up the rest. The cost: a reader's minimum font size, which may push a line past its panel (DEC-020 point 4), may push its tail past its ground too, onto what lies under it.

**Why the browser still colours the letters.** The colours are the reader's, and the file adds none of its own (DEC-023 point 7).

**Why a run's ground joins its line's under forced colours.** There a run's ground takes the reader's background colour, as its line's does, so the line's ground shows it unchanged. Drawn with its run, it would cover the line above. Outside forced colours it keeps its own colour, and its place at the browser's widths, which only its span knows (DEC-020 point 2). So a run's ground beneath all of a text's lines waits there for a way to place it.

**Why the edge inside the fill.** Centred on the outline, half the edge lies over whatever lies beside the fill, in forced images alone, as a backplate's cover does. Inside, a fill covers the same in every mode.

### Alternatives considered

- **One ground behind all of a text's lines:** it hides what lies beside a short line and between paragraphs.
- **A ground the size of the text's frame:** a short title blanks its frame's whole width.
- **A text's lines in reverse order:** the overlap would cover the tops of the line below.
- **A text's lines flowing in one element, so the browser paints their backplates first:** flowing lines leave the place the engine gave them (DEC-020 point 2).
- **Grounds sized in the page by a script:** the file holds none (DEC-023 point 4).
- **The browser's backplates left as they are, and the loss named in the report:** the reader still loses the descenders, and no piece can mend it.
- **The edge centred on the outline, its cover left to the piece:** the piece's own images never show it.
- **No edge on an opaque fill:** the fill would lose its outline on the reader's ground (DEC-023 point 7).

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-023 point 7, "Under forced colours".** "The browser colours the text itself" comes to add that each line lies on a ground the file draws in the reader's background colour, beneath all of its text's lines, and takes no backplate. "With an edge in that text colour" comes to say that the edge lies inside the fill.
  - **DEC-023 point 7, "The renderer declares these choices".** It comes to name the grounds' margin beside the edge's width.
  - **DEC-036 point 4, "No rule of its own".** It comes to add that under forced colours a run's ground lies in its line's ground, and its span draws none of its own.
  - **DEC-027 point 4, "One more span with no paint, left to forcing".** It comes to add that the span lies in a line kept out of the backplate, on the file's ground.
- **#3088** builds points 1 to 5, at a new version of the HTML renderer ([visual-communication:DEC-005-engine-and-plugins] point 9). Its test of the file holds that the grounds lie beneath the lines, as the engine measures them with the margin, that a sign and a run's ground still take forced colours, and that the edge lies inside the fill.
- **The capability's page on outputs** comes to say how the file draws a text's grounds and a fill's edge under forced colours, with the margin's number, in #3088's change.
- **Before #3088 closes,** a person looks at a page under a real forced palette, in Edge or Chrome on Windows, and in Firefox.
- **Revisit this record** if a browser paints a backplate behind a line kept out of it, or stops forcing a span in one, if a line's tail passes its ground in a browser, or if a real forced palette, or Firefox's, meets the grounds otherwise than Chrome did.
