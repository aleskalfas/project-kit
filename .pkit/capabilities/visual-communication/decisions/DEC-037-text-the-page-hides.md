---
id: DEC-037
title: A text another part covers, or the page's edge cuts, is reported as dropped
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when the viewing step draws a page through a browser, its report lists in `dropped` every text the page does not show in full. That is a text that drew no ink or lies wholly off its page, a text that runs past the page's edge, and a text another part covers, whether it loses all of its letters or only some. Each entry gives the share of the text's ink it lost. The step finds each one in what the browser drew, never in the scene's frames. How well a text that does show reads stays the check's and the reviewer's. Under forced colours, each text lies on one backplate, so its own lines cover none of it. For example, under the dark forced palette a footer's backplate covers a line, all but its last three letters. The report lists that line in `dropped` for that palette, as covered, with the share it lost.

## Context

[project-kit#3088](https://github.com/aleskalfas/project-kit/issues/3088) asks that the report list in `dropped` every text the drawn image does not show. On the showcase deck drawn at the projector size ([project-kit#2973](https://github.com/aleskalfas/project-kit/issues/2973)), the graphic-design-reviewer found lost text that `dropped` did not list. Under the forced palettes, a footer's and a limit's backplates covered lines in both languages, and notes and a legend ran past the page's edge or under another part.

The records leave these losses out by design. The check for dropped text asks nothing of what lies over a text, and it names a span that lies wholly off its page, never one that the page's edge cuts ([visual-communication:DEC-020-html-page-drawing] point 6). Under a forced palette it names a span off its page, or one that drew nothing ([visual-communication:DEC-027-forced-colours-viewing] point 4). A first probe of a page with each loss found that, in the start without forced colours, the report named only the text wholly off the page. Under a forced palette the ink read left other texts' backplates painted, so a span wholly under one was named as one that drew no ink, and a span partly under one was not named at all.

On 13 November 2026, after a first review of this record, the project manager chose five of its rules: what stays out of *covered*, the principle of a sliver, the share in each entry, the SVG renderer's notice, and that a cut or covered text is a fault the piece mends.

Terms:
- A *backplate* is the ground a text lies on under forced colours, in the forced palette's ground colour. A browser paints one behind each line. Point 5 has the file draw one behind each text instead.
- The *page drawn whole* is a page as its image shows it, in one key or forced palette, with every part painted.
- A span's *ink* is as [visual-communication:DEC-020-html-page-drawing] point 6 defines it: what the span draws alone. Its ink is *strong* where its letters cover most of a pixel, not a smoothed edge's part of one.

### What the probes showed

The probes drew one page of the HTML renderer, 700 by 340 px, in one face, through the viewing step's browser module, in Chrome 157 on one Mac. They read it in the start without forced colours and in both forced palettes, at device scales of 2 and 1.225, the scale the step's images use. Their code is thrown away.

Each row gives the share of the span's strong ink lost, at a scale of 2, or, where it says px², the area lost in px of the page at 1.225.

| Planted on the page | No forced colours | Light forced palette | Dark forced palette |
|---|---|---|---|
| Words under a later opaque box | 100% | 100% | 100% |
| Words, half under a later box | 52% | 52% | 52% |
| Words under a translucent fill | 0 | 0 | 0 |
| Words under a later text | 30% | 75% | 75% |
| A two-line heading at a line step of 1.1 em, with descenders: its first line | 0 | 5.6% | 5.7% |
| The same at 1.25 em | 0 | 0 | 0 |
| A box whose edge meets the foot of the descenders, px² | 0 | 8.0 | 8.6 |
| A box whose edge meets a letter's side, px² | 0 | 0 | 0 |
| A comma under a box, px² | 6.6 | 6.6 | 9.3 |
| A háček under a box, px² | 5.9 | 7.2 | 9.9 |
| A line set 9 px above the top of its file's first page: past the edge | 41% | 41% | 41% |

- **Hiding a span names text that shows.** Found by hiding the span, a white text on the page with no ground lost all its ink, a text in its box's colour 72%, and a white text on its own black ground 61%. Found by changing only its letters' colour, each lost none.
- **The ink read without other backplates.** Under both forced palettes, today's ink read saw a quarter of the ink of the words under a later text, and 94% of the heading's first line. With every line but the span's own hidden, it saw all of it, and the span kept the forced palette's text colour.
- **A heading's own lines.** At a step of 1.1 em, each line's backplate covered the descenders of the line above. A fix made by hand took each line's backplate away, left its spans to the browser's forcing, and put one ground in the reader's background colour behind each text. The first line then lost none, and the words under a later text still lost 75%.
- **A forced edge.** Where a box's edge met the descenders' foot, the edge a forced palette gives an opaque fill reached over their tips.
- **The top edge.** With no room above the first page, the line past its top lost nothing, so its cut was silent.
- **The cost.** At 1.225, today's ink read took 0.08 s for each text in each key or forced palette. The reads this record decides took 0.32 s, of which 0.04 s decoded the images in Python's standard library. They took six images of each span's box and an em around it. In bands as wide as the page, at a scale of 2, they took 0.7 to 1.5 s, most of it decoding.

**Not reached:** a picture under a text, a run's ground under the fix, a fixed page and its keyline, a page after the first, ink past a page's other edges, a span both cut and covered, a real forced palette, another browser, a Mac set to light.

## Decision

**Through a browser, the check for dropped text names each span that another part covers or the page's edge cuts, with the share of its ink lost, found in the browser's own drawing. Under forced colours, each text lies on one backplate, so its own lines cover none of it.**

### 1. A span the page does not show in full is dropped

- **What is named.** A span that left no ink, or lies wholly off its page, is named (DEC-020 point 6). So is a span that is cut or covered. A span is *cut* where part of its strong ink lies past its page's edge. A span is *covered* where the page drawn whole hides part of its strong ink on the page, under a later part or another text's backplate.
- **A sliver does not count.** A loss smaller than an area the step declares, in px of the page, names no span.
- **A fault the piece mends.** A cut or covered span is mended in the piece's layout or content, and no such loss is accepted.
- **Through a browser alone.** Through the SVG renderer, `dropped` keeps its meaning: what resvg drew nothing of ([visual-communication:DEC-015-viewing-step-and-reviewer] point 3). That report says that cover and cut were not read.

### 2. Each is an entry of `dropped`, with its cause and its share

- **No field of its own.** A cut or covered span is an entry of `dropped`, beside a span that left no ink and a span that lies off its page, and it names what those entries name.
- **Its cause.** Each entry says which it is: no ink, off the page, cut or covered. A span both cut and covered names both.
- **Its share.** A cut or covered entry gives the share of the span's strong ink that each of its causes loses.

### 3. It is found in the browser's drawing

- **Room past every edge.** The read gives each page room past each of its edges, enough for all the ink of each span that crosses one, and keeps each page's size.
- **A span's ink is drawn alone,** on the ink read's two grounds, with no other text and no other text's backplate. Past a fixed page's edge the read paints its own ground and hides the keyline.
- **What the page shows of it** is what changes in the page drawn whole when the span's letters alone change colour, its ground and its sign left as they are.
- **Never from the scene's frames** or its draw order.

### 4. What stays the reviewer's

- **A text that shows, yet reads poorly,** such as a faint text over a picture or a translucent fill, and a text in the colour of what lies under it. The check measures contrast where it can, and the reviewer judges the rest ([visual-communication:DEC-004-brands-and-notations] point 8).
- **A part that is no text,** such as a shape, a line or a picture, whether covered or cut.
- **The images themselves.** The reviewer reads in the images it is given what the report does not name, and its report says what it looked at (DEC-015 point 7).

### 5. Under forced colours, each text lies on one backplate

- **The file draws it,** behind all of the text's lines, in the reader's background colour. Its lines draw none of their own, and the browser still colours the text.

### 6. The first read plants each loss

- **Named in every start** (DEC-020 point 7): a span cut past its page's top edge, and, as covered, the text under a later box and a span wholly under another text, which is never named as one with no ink.
- **Left unnamed:** a text under a translucent fill, a text whose letter a part's edge meets, and the text in the colour of its ground.

## Rationale

**Why the report names these losses.** A text the page does not show is a part missing, whatever the cause, and the report names such a loss once for every image. Left to the eye, a line lost in one language under one forced palette is found only by reading that one image. A cut text is a fault of layout even where a browser shows it: a page clips no text (DEC-020 point 4), so the text spills onto what lies past the page, which no design holds.

**Why from the browser's drawing.** The scene does not know a backplate, or which fill hides what lies under it. A fill's opacity, a picture's transparent pixels and the colours a forced palette gives are all the browser's. Nor does the scene know the browser's own text widths, which can put a line past an edge that the engine's measure keeps inside. This is the reason the step judges what the tool drew, not the page's names (DEC-015, its Rationale).

**Why strong ink, and an area of the page.** A part's smoothed edge hides only a letter's faint rim, so counting strong ink alone leaves it out however long the edge runs, and a translucent fill lets strong ink through. A part that lies over a letter by a pixel, as a forced edge did (Context), is a cover, and its small share says so. An area keeps a lost comma or háček, which changes a word's meaning, and is the same at every device scale. A share of the span's ink would miss a long line that loses one short word. An eroded mask would wear away a háček's thin strokes at the step's scale.

**Why a cause and a share.** `dropped` already holds a span off its page, which is a loss of layout, not of drawing, and each of its readers takes an entry as a part missing. The cause says where the fix lies: a span with no ink in its paint or the file, a covered or cut span in the layout or the content. The share shows how much each entry loses, so a reader can sort them, and the sliver's area can change on the outputs page with no new record.

**Why a change of colour, not a hidden span.** Hiding a span hides its ground and its sign too, so a text on its own ground, or in the colour of what lies under it, read as lost (Context). A change of its letters' colour alone shows where the page lets them through, whatever their own colour.

**Why the colour of what lies under it stays out.** Nothing lies over such a text, and the contrast check already measures the pairs a brand declares (DEC-004 point 8). Naming it in `dropped` too would give one fault two lists.

**Why no other backplate in a span's ink.** With other texts' backplates painted, a span under one reads as a span that drew no ink, which sends its fix to the wrong place, and a span partly under one reads as whole.

**Why one backplate for each text.** A browser paints each line's backplate with that line, so where a text's line step is below its font's height, each line covers the descenders of the line above, in every forced image of every language (Context). The step comes from a brand, so no piece's layout mends it, and the report would fill with entries no piece can fix.

**Why no such loss is accepted.** A covered or cut text still reaches a reader's tools as words the page does not show. So type meant to be partly hidden is drawn as a shape or a picture, not a text.

**Why the SVG renderer waits.** Through resvg the page's frame clips a cut text, so it is gone for every reader. Its read needs a canvas past the page and a read of cover of its own, a change of resvg's module. Until then its report says what it did not read, so an empty list never reads as clean.

**The cost.** The read takes about four times as long as today's ink read, for each text in each key and forced palette (Context).

### Alternatives considered

- **A field of its own for covered and cut text:** the same fault would sit in two lists, and `dropped` already holds a span off its page.
- **The scene's frames and draw order, read by the check:** these are blind to a backplate, to which fill hides, and to the browser's text widths.
- **Only a span the page shows none of:** this misses a line that a backplate covers all but a few letters of.
- **The browser's hit testing of what lies over a span:** it knows no opacity and no backplate, and the layers take no pointer (DEC-020 point 3).
- **Leaving these losses to the reviewer:** every image would have to be read to find them.
- **Hiding the span to find what the page shows of it:** it names a text on its own ground, and a text in the colour of what lies under it.
- **A text in the colour of what lies under it as covered, or as a fifth cause:** the contrast check measures it where a brand declares the pair, and the reviewer elsewhere.
- **A sliver by its count of pixels, a share of the span or an eroded mask:** a seam grows with its length, a share misses one word in a long line, and erosion wears away thin strokes.
- **A text's lines in reverse order under forced colours:** the same overlap would cover the tops of the line below.
- **A text's lines flowing in one element, so the browser paints their backplates first:** flowing lines leave the place the engine gave them (DEC-020 point 2).
- **A list of accepted covers and cuts:** such a text still reaches a reader's tools.
- **The SVG renderer too, now:** a change of resvg's module of its own, while its report's notice keeps the gap seen.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-020 point 6, "Ink."** It comes to say that a span is drawn alone with no other text and no other text's backplate, with room past its page's edges, and that the read reports a cut or covered span with its cause and its share.
  - **DEC-020 point 6, "It asks nothing of what lies over a text".** It comes to say that the read names a text as far as a later part or another text's backplate hides its strong ink, and that a text in the colour of what lies under it, or one that shows and reads poorly, is for the check and the reviewer.
  - **DEC-027 point 4, "The four reads run in each forced image".** Its list of what that palette's reader loses comes to add a span the page's edge cuts, and a span a later part or another text's backplate covers.
  - **DEC-015 point 3, "Each text, or run of a text, the tool dropped".** It comes to add that through a browser it names each text the page drawn does not show in full, covered or cut by the page's edge, with the share lost, and that through resvg the report says that cover and cut were not read.
  - **DEC-031 point 5, "The reads hold".** "No read looks outside a page" comes to say that the read past a page's edge paints its own ground there and hides the keyline, so the planted page still needs no keyline.
  - **[visual-communication:DEC-023-html-page-modes] point 7, "Under forced colours".** "The browser colours the text itself" comes to add: on one backplate the file draws behind all of a text's lines, which draw none of their own.
  - **[visual-communication:DEC-022-web-site-and-parts], its Implications, "A brand's or a local part past a page's edge".** It comes to add that a text past it is named as cut.
- **The capability's page on outputs** comes to say, for each renderer, what `dropped` holds, its causes and shares, the numbers that set strong ink, what hides it and a sliver, and how the file draws a text's backplate. **The build loop's table** comes to say what mends each cause. Both in #3088's change.
- **#3088** builds points 1 to 3, 5 and 6, point 5 at a new version of the HTML renderer, with a test that draws a page with each loss and finds it in the report.
- **Read against this record, and left as they stand:**
  - DEC-020 point 7 and DEC-027 point 4's first read. The planted page holds one fault of each kind the reads name, and both starts name the same.
  - DEC-020 point 4, "A page clips no text". The read's room changes no page's size.
  - DEC-023 point 6. The reads run in each key drawn and in each forced palette, in each language's page file.
  - DEC-022 point 7. Each page is read whole, so a band's edge cuts no span.
  - [visual-communication:DEC-036-concept-signs] point 3. A run's ground and sign stay as they are when the read changes its letters' colour, and under point 5 the browser forces its spans as before.
- **Revisit this record** if a browser comes to paint a backplate or a forced fill in a way that makes the read name a text that shows, if the sliver's area names a text that shows or misses a mark a reader needs, or when the SVG renderer's read of cover and cut is built.
