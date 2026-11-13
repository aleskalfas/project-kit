---
id: DEC-037
title: A text another part covers, or the page's edge cuts, is reported as dropped
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when the viewing step draws a page through a browser, its report lists in `dropped` every text the page does not show in full. That is a text that drew no ink or lies wholly off its page, a text that runs past the page's edge, and a text another part covers, whether it loses all of its letters or only some. Each entry names one cause, and the share of the text's ink that cause loses. The step finds each one in what the browser drew, never in the scene's frames. How well a text that does show reads stays the check's and the reviewer's. Under forced colours the grounds of a text's own lines cover none of it ([visual-communication:DEC-039-forced-colours-text-grounds]). For example, under the dark forced palette a footer's ground covers a line, all but its last three letters. The report lists that line in `dropped` for that palette, as covered, with the share it lost.

## Context

[project-kit#3088](https://github.com/aleskalfas/project-kit/issues/3088) asks that the report list in `dropped` every text the drawn image does not show. On the showcase deck drawn at the projector size ([project-kit#2973](https://github.com/aleskalfas/project-kit/issues/2973)), the graphic-design-reviewer found lost text that `dropped` did not list. Under the forced palettes, a footer's and a limit's backplates covered lines in both languages, and notes and a legend ran past the page's edge or under another part.

The records leave these losses out by design. The check for dropped text asks nothing of what lies over a text, and it names a span that lies wholly off its page, never one that the page's edge cuts ([visual-communication:DEC-020-html-page-drawing] point 6). Under a forced palette it names a span off its page, or one that drew nothing ([visual-communication:DEC-027-forced-colours-viewing] point 4). A first probe of a page with each loss found that, in the start without forced colours, the report named only the text wholly off the page. Under a forced palette the ink read left other texts' backplates painted, so a span wholly under one was named as one that drew no ink, and a span partly under one was not named at all.

On 13 November 2026, after a first review of this record, the project manager chose five of its rules: what stays out of *covered*, the principle of a sliver, the share in each entry, the SVG renderer's notice, and that a cut or covered text is a fault the piece mends. Later that day, after the architect's review and the critic's second, they moved how the file draws a text's ground under forced colours into a record of its own, DEC-039. They also chose one entry for each cause, a sliver in the span's em², and a read bound by what it measures, with its cost weighed.

Terms:
- A *backplate*, and a line's *ground* under forced colours, are as DEC-039 defines them.
- The *page drawn whole* is a page as its image shows it, in one key or forced palette, with every part painted.
- A span's *ink* is as [visual-communication:DEC-020-html-page-drawing] point 6 defines it: what the span draws alone. Its ink is *strong* where its letters cover most of a pixel, not a smoothed edge's part of one.

### What the probes showed

The probes drew one page of the HTML renderer, 700 by 340 px, in one face, through the viewing step's browser module, in Chrome 157 on one Mac. They read it in the start without forced colours and in both forced palettes, at device scales of 2 and 1.225, the scale the step's images use. A second probe read a page in the form DEC-039 decides, as that record says. Their code is thrown away.

Each row gives the share of the span's strong ink lost at a scale of 2, or, where it says px², the area lost in px of the page at 1.225. The last row gives the share of all its ink.

| Planted on the page | No forced colours | Light forced palette | Dark forced palette |
|---|---|---|---|
| Words under a later opaque box | 100% | 100% | 100% |
| Words, half under a later box | 52% | 52% | 52% |
| Words under a translucent fill | 0 | 0 | 0 |
| Words under a later text | 30% | 75% | 75% |
| A two-line heading at a line step of 1.1 em, with descenders: its first line, on the browser's backplates | 0 | 5.6% | 5.7% |
| The same, on the file's grounds (DEC-039) | 0 | 0 | 0 |
| The same at 1.25 em | 0 | 0 | 0 |
| A heading set close above body text, at a line step of 1.1 em | 0 | 1.3% | 1.5% |
| A box whose edge meets the foot of the descenders, px² | 0 | 8.0 | 8.6 |
| A box whose edge meets a letter's side, px² | 0 | 0 | 0 |
| A comma under a box, px² | 6.6 | 6.6 | 9.3 |
| A háček under a box, px² | 5.9 | 7.2 | 9.9 |
| A line set 9 px above the top of its file's first page: its ink past the edge | 41% | 41% | 41% |

- **Hiding a span names text that shows.** Found by hiding the span, a white text on the page with no ground lost all its ink, a text in its box's colour 72%, and a white text on its own black ground 61%. Found by changing only its letters' colour, each lost none.
- **Two colours.** The probes changed a span's letters between the forced palette's text colour and its ground colour, which forcing keeps.
- **The ink read without other backplates.** Under both forced palettes, today's ink read saw a quarter of the ink of the words under a later text, and 94% of the heading's first line. With every line but the span's own hidden, it saw all of it, and the span kept the forced palette's text colour.
- **Between texts.** On the file's grounds, the words under a later text still lost 74 to 77%, and the heading set close above body text 0.2 to 1.5%, as on the browser's backplates. The body text's ground covers the heading's descenders, so the heading is named, and the spacing between the two mends it.
- **A forced edge.** Where a box's edge met the descenders' foot, the edge a forced palette gives an opaque fill reached over their tips. Where it met a letter's side, it reached 0.5 px² in the dark forced palette at a scale of 2.
- **The top edge.** With no room above the first page, the line past its top lost nothing, so its cut was silent.
- **The cost.** At 1.225, today's ink read took 0.08 s for each span in each key or forced palette. The reads this record decides took 0.32 to 0.33 s for each span, about a sixth of it decoding images in Python's standard library. They took six images of each span's box and an em around it. Timed on that Mac:
  - **One look of the showcase deck,** in one language and one key, 108 spans, took about 15 s today, and 51 s with these reads on every span.
  - **A pre-filter** by the browser's own boxes, widened by an em, kept 85 of the 108.
  - **CI's run**, every language and key of the deck and of the project's other piece, took about 1 minute today, and about 4 minutes with these reads.
  - **The look before a designer stops**, the deck in every language and key and under forced colours, took about 1.5 minutes today, and about 6 minutes with these reads.

**Not reached:** a picture under a text, a fixed page and its keyline, a page after the first, ink past a page's other edges, a span both cut and covered, a text in a translucent colour, a light weight at a small size, a real forced palette, another browser, Linux, a Mac set to light.

## Decision

**Through a browser, the check for dropped text names each span that another part covers or the page's edge cuts, in one entry for each cause with the share of its ink lost, found in what the browser drew.**

### 1. A span the page does not show in full is dropped

- **What is named.** A span that left no ink, or lies wholly off its page, is named (DEC-020 point 6). So is a span that is cut or covered. A span is *cut* where part of its strong ink lies past its page's edge. A span is *covered* where the page drawn whole hides part of its strong ink on the page, under a part drawn after it: a shape, a line of text, or under forced colours a text's ground.
- **A sliver does not count.** A loss smaller than an area the step declares, in the span's em², names no entry. Each cause is judged alone.
- **A fault mended where it arises.** A cut or covered span is mended where its cause lies: in the piece's layout or content, or in the spacing a component or a brand sets between lines and between texts. No such loss is accepted.
- **Through a browser alone.** Through the SVG renderer, `dropped` keeps its meaning: what resvg drew nothing of ([visual-communication:DEC-015-viewing-step-and-reviewer] point 3). That report says that cover and cut were not read.

### 2. Each cause is an entry of `dropped`, with its share

- **No field of its own.** A cut or covered span is an entry of `dropped`, beside a span that left no ink and a span that lies off its page, and it names what those entries name.
- **One entry for each cause.** Each entry gives one cause in `why`: no ink, off the page, cut or covered. A span both cut and covered gives two entries.
- **Its share.** A cut or covered entry gives the share of the span's strong ink that its cause loses.
- **The command prints each entry** in words that read for its cause, with its share.

### 3. It is measured in what the browser drew

- **What is measured.** A span's strong ink, and how much of it the page drawn whole shows on the page. Each span is named or cleared from what the browser drew and where it laid each part out, never from the scene's frames or its draw order.
- **A span's ink is drawn alone,** in an opaque colour, with no other text and nothing drawn beneath another text. So a letter's strength is its shape's, whatever the alpha of its colour.
- **Room past every edge.** The read gives each page room past each of its edges, enough for all the ink of each span that crosses one, and keeps each page's size. Past a fixed page's edge the read paints its own ground and hides the keyline.
- **What the page shows of it** is what changes in the page drawn whole when the span's letters alone change between two colours that differ and that forcing keeps, such as two system colours. Its ground and its sign stay as they are.
- **Cheaper ways stay open.** The read may pass over a span whose box in the browser, widened by its em, stays inside its page and meets no box of a part drawn after it. It may change the colour of many spans at once, where their widened boxes do not meet.

### 4. What stays the reviewer's

- **A text that shows, yet reads poorly,** such as a faint text over a picture or a translucent fill, and a text in the colour of what lies under it. The check measures contrast where it can, and the reviewer judges the rest ([visual-communication:DEC-004-brands-and-notations] point 8).
- **A part that is no text,** such as a shape, a line or a picture, whether covered or cut.
- **The images themselves.** The reviewer reads in the images it is given what the report does not name, and its report says what it looked at (DEC-015 point 7).

### 5. The first read plants each loss

- **Named in every start** (DEC-020 point 7): a span cut past its page's top edge, and, as covered, the text under a later box and a span wholly under another text, which is never named as one with no ink.
- **Left unnamed:** a text under a translucent fill, a text with a part's edge beside a letter's side, at a gap of at least half the edge's width, and the text in the colour of its ground.
- **Its rule under forced colours is the renderer's.** Only a fill opaque in every key takes the reader's ground, so the translucent fill stays (DEC-023 point 7).
- **The span left to forcing** (DEC-039 point 5) runs over two lines, at a step below its font's height, and neither line is named. So where a browser paints its backplates again, the run stops.

## Rationale

**Why the report names these losses.** A text the page does not show is a part missing, whatever the cause, and the report names such a loss once for every image. Left to the eye, a line lost in one language under one forced palette is found only by reading that one image. A cut text is a fault of layout even where a browser shows it: a page clips no text (DEC-020 point 4), so the text spills onto what lies past the page, which no design holds.

**Why from the browser's drawing.** The scene does not know a backplate, or which fill hides what lies under it. A fill's opacity, a picture's transparent pixels and the colours a forced palette gives are all the browser's. Nor does the scene know the browser's own text widths, which can put a line past an edge that the engine's measure keeps inside. This is the reason the step judges what the tool drew, not the page's names (DEC-015, its Rationale). The browser's own boxes are its layout, so a read that passes over a span they show nothing near still rests on the browser.

**Why strong ink, from the letters' shape, and an area in the em.** A part's smoothed edge hides only a letter's faint rim, so counting strong ink alone leaves it out however long the edge runs, and a translucent fill lets strong ink through. Drawn in an opaque colour, a text in a translucent colour counts as any other. An area keeps a lost comma or háček, which changes a word's meaning. In the span's em², it keeps them at a legend's size as at body size, and at every device scale. A share of the span's ink would miss a long line that loses one short word. An eroded mask would wear away a háček's thin strokes at the step's scale.

**Why one entry for each cause.** `dropped` already holds a span off its page, which is a loss of layout, not of drawing, and each of its readers takes an entry as a part missing. The cause says where the fix lies: a span with no ink in its paint or the file, a covered or cut span in the layout, the content or the step. One cause to an entry keeps `why` one word, as its readers parse it, and gives each cause its own share. So a reader can sort the entries, and the sliver's area can change on the outputs page with no new record.

**Why a change between two colours, not a hidden span.** Hiding a span hides its ground and its sign too, so a text on its own ground, or in the colour of what lies under it, read as lost (Context). Changing its letters alone shows where the page lets them through, whatever their own colour. Two colours forcing keeps tell the letters from what lies over them in every key and forced palette.

**Why the colour of what lies under it stays out.** Nothing lies over such a text, and the contrast check already measures the pairs a brand declares (DEC-004 point 8). Naming it in `dropped` too would give one fault two lists.

**Why no other text in a span's ink.** With other texts and their grounds painted, a span under one reads as a span that drew no ink, which sends its fix to the wrong place, and a span partly under one reads as whole.

**Why no such loss is accepted.** A covered or cut text still reaches a reader's tools as words the page does not show. So type meant to be partly hidden is drawn as a shape or a picture, not a text.

**Why the SVG renderer waits.** Through resvg the page's frame clips a cut text, so it is gone for every reader. Its read needs a canvas past the page and a read of cover of its own, a change of resvg's module, which [project-kit#3111](https://github.com/aleskalfas/project-kit/issues/3111) builds. Until then its report says what it did not read, so an empty list never reads as clean.

**The cost, accepted.** These reads take about four times as long as today's ink read for each span, so the showcase deck's looks take three to four times as long (Context). The build loop looks at a page after each change, and under a minute a look still keeps that pace. The look before a designer stops runs once in a round, beside the reviewer's read of every image, so a few more minutes there slow no step that repeats. CI's run stays well inside its job's 30 minutes, with room for a slower runner and more pieces. So the cost is accepted as the price of a report that names every lost text. Point 3 leaves the build room to make the read cheaper.

### Alternatives considered

- **A field of its own for covered and cut text:** the same fault would sit in two lists, and `dropped` already holds a span off its page.
- **One entry for a span, its causes in a list:** `why` would no longer be the one word each reader of the report parses.
- **The scene's frames and draw order, read by the check:** these are blind to a backplate, to which fill hides, and to the browser's text widths.
- **Only a span the page shows none of:** this misses a line that a ground covers all but a few letters of.
- **The browser's hit testing of what lies over a span:** it knows no opacity and no ground, and the layers take no pointer (DEC-020 point 3).
- **Leaving these losses to the reviewer:** every image would have to be read to find them.
- **Hiding the span to find what the page shows of it:** it names a text on its own ground, and a text in the colour of what lies under it.
- **The span's letters changed to one colour:** a span already in that colour reads as wholly covered.
- **Strength from the span's own paint:** a text in a translucent colour has no strong ink, so none of its losses would be named.
- **A text in the colour of what lies under it as covered, or as a fifth cause:** the contrast check measures it where a brand declares the pair, and the reviewer elsewhere.
- **A sliver in px of the page, by its count of pixels, as a share of the span or by an eroded mask:** one area misses a comma at a legend's size, a seam grows with its length, a share misses one word in a long line, and erosion wears away thin strokes.
- **A list of accepted covers and cuts:** such a text still reaches a reader's tools.
- **A finding at validation, from the engine's measure, for a cut text:** it would reach a session with no browser, but it misses what a browser's widths push past an edge and reads no cover, so it waits with the SVG renderer's read (#3111).
- **The SVG renderer too, now:** a change of resvg's module of its own, while its report's notice keeps the gap seen.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-020 point 6, "Ink".** It comes to say that a span is drawn alone, in an opaque colour, with no other text and nothing drawn beneath another text, with room past its page's edges, and that the read reports a cut or covered span, in one entry for each cause, with its share.
  - **DEC-020 point 6, "It asks nothing of what lies over a text".** It comes to say that the read names a text as far as a part drawn after it hides its strong ink, and that a text in the colour of what lies under it, or one that shows and reads poorly, is for the check and the reviewer.
  - **DEC-027 point 4, "The four reads run in each forced image".** Its list of what that palette's reader loses comes to add a span the page's edge cuts, and a span a later part covers, a text's ground among them.
  - **DEC-015's summary, its Decision's sentence and point 3's heading.** "Text drawn to nothing never passes in silence" comes to say that no text the page does not show passes in silence, whether the tool drew it to nothing or, through a browser, the page hides or cuts it.
  - **DEC-015 point 3, "Each text, or run of a text, the tool dropped".** It comes to add that through a browser it names each text the page drawn does not show in full, covered or cut by the page's edge, in one entry for each cause with its share, and that through resvg the report says that cover and cut were not read.
  - **DEC-031 point 5, "The reads hold".** "No read looks outside a page" comes to say that the read past a page's edge paints its own ground there and hides the keyline, so the planted page still needs no keyline.
  - **[visual-communication:DEC-022-web-site-and-parts], its Implications, "A brand's or a local part past a page's edge".** It comes to add that a text past it is named as cut.
- **The reviewer's agent file** comes to say, in #3088's change, that a cut or covered entry is the fault of a part missing or blank, and is never accepted. A covered entry whose cover is another text is not counted again as text over text, which keeps the overlaps the report does not name. Where a run through the SVG renderer says that cover and cut were not read, the reviewer reads them in its images, and its report says it did.
- **The capability's page on outputs** comes to say, for each renderer, what `dropped` holds, its causes and shares, and the numbers that set strong ink, what hides it and a sliver. **The build loop's table** comes to say what mends each cause. Both in #3088's change.
- **This record rests on DEC-039,** and both are accepted in #3088's change.
- **#3088** builds points 1 to 5, with a test that draws a page with each loss and finds it in the report. Its changeset is `minor` for visual-communication.
- **The planted page** takes DEC-039's form under forced colours, as a page in the renderer's form does.
- **Before #3088 closes,** the forced start's first read runs once on Linux.
- **Read against this record, and left as they stand:**
  - DEC-020 point 7 and DEC-027 point 4's first read. The planted page holds one fault of each kind the reads name, and both starts name the same.
  - DEC-020 point 4, "A page clips no text". The read's room changes no page's size.
  - DEC-023 point 6. The reads run in each key drawn and in each forced palette, in each language's page file.
  - DEC-022 point 7. Each page is read whole, so a band's edge cuts no span.
  - [visual-communication:DEC-036-concept-signs] point 3. A run's ground and sign stay as they are when the read changes its letters' colour.
- **Revisit this record** if a browser comes to paint a forced fill or a ground in a way that makes the read name a text that shows, if the sliver's area names a text that shows or misses a mark a reader needs, or when #3111 builds the SVG renderer's read of cover and cut.
