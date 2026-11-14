---
id: DEC-037
title: A text another part covers, or the page's edge cuts, is reported as dropped
status: accepted
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when the viewing step draws a page through a browser, its report lists in `dropped` every text the page does not show in full. That is a text that drew no ink or lies wholly off its page, a text that runs past the page's edge, and a text another part covers, whether it loses all of its letters or only some. Each entry names one cause, and the share of the text's ink that cause loses. The step finds each one in what the browser drew, never in the scene's frames. How well a text that does show reads stays the check's and the reviewer's. For example, where a later box covers a note's last three words, the report lists that note in `dropped`, as covered, with the share of its ink it lost.

## Context

[project-kit#3088](https://github.com/aleskalfas/project-kit/issues/3088) asks that the report list in `dropped` every text the drawn image does not show. On the showcase deck of the repository the capability is authored in, drawn at the projector size ([project-kit#2973](https://github.com/aleskalfas/project-kit/issues/2973)), the graphic-design-reviewer found lost text that `dropped` did not list. Under the forced palettes, the *backplates*, the grounds a browser paints behind lines of text, covered lines of a footer and of the line that says where a slide's claim stops holding, in both languages. Notes and a legend ran past the page's edge or under another part.

The check for dropped text asks nothing of what lies over a text ([visual-communication:DEC-020-html-page-drawing] point 6). Of the page's edge that point says only "A span outside the page is reported too", and nothing of a span the edge cuts. Under a forced palette the check names a span off its page, or one that drew nothing ([visual-communication:DEC-027-forced-colours-viewing] point 4). So naming a covered text overturns a sentence of DEC-020 point 6 in part, and naming a cut text, on which that point is silent, refines it. The first probe below, of a page with each loss, found that in the start without forced colours the report named only the text wholly off the page. Under a forced palette the ink read left other texts' backplates painted, so a span wholly under one was named as one that drew no ink, and a span partly under one was not named at all.

Terms:
- A line's *ground* under forced colours, and a *run of texts*, are as [visual-communication:DEC-039-forced-colours-grounds-and-edges] defines them.
- The *page drawn whole* is a page as its image shows it, in one key or forced palette, with every part painted.
- A span's *ink* is as DEC-020 point 6 defines it: what the span draws alone, in its own paint. Its *strong ink* is where its letters, drawn alone in one opaque colour on another, cover most of a pixel, not a smoothed edge's part of one.
- A *sliver* is a loss too small to name (point 1).
- The *edge control* is a planted text whose descenders' foot a box's edge touches, and the *háček plant* a planted háček under a box (point 5).

### What the probes showed

Seven probes drew a page of the HTML renderer, in one face, through the viewing step's browser module, in Chrome 157 on one Mac. They read it in the start without forced colours, under a light key, and in both forced palettes. The first four read one page at device scales of 2 and 1.225, the scale the step's images of a deck use, and the fourth's sweep of a fill's edge also at 0.625 and 1. The fifth read the edge control alone, and the sixth a háček at the command's text floor, each at 0.625, 1, 1.225 and 2. The seventh read the fourth sweep's box at the foot of a 16 px text's descenders, at a scale of 1, under a dark key too. The second to the seventh read a page in DEC-039's forms too, each as that record says. Their code is thrown away.

Each row gives the share of the span's strong ink lost, at a scale of 2. Where it says em², it gives the area lost in the span's em², at 1.225 unless it says otherwise, for a span at 16 px, or 24 px for a heading. The last row gives the share of all its ink.

| Planted on the page | No forced colours, a light key | Light forced palette | Dark forced palette |
|---|---|---|---|
| Words under a later opaque box | 100% | 100% | 100% |
| Words, half under a later box | 52% | 52% | 52% |
| Words in a colour at 30% alpha, half under a later box | 46% | 46% | 46% |
| Words under a translucent fill | 0 | 0 | 0 |
| Words under a later text, on the browser's backplates | 30% | 75% | 75% |
| The same, on a run's grounds (DEC-039) | 30% | 30% | 35% |
| A two-line heading at a line step of 1.1 em, with descenders: its first line, on the browser's backplates | 0 | 5.6% | 5.7% |
| The same, on the file's grounds | 0 | 0 | 0 |
| The same at 1.25 em | 0 | 0 | 0 |
| A heading set close above body text at 1.1 em, on the browser's backplates, em² at 2 and at 1.225 | 0 | 0.016 and 0.002 | 0.022 and 0.009 |
| The same, on a run's grounds | 0 | 0 | 0 |
| The same with a box between the two texts in the tree, em² at 2 and at 1.225 | 0 | 0.016 and 0.002 | 0.022 and 0.010 |
| A box whose edge, centred on its outline, touches the foot of the descenders, em², in two probes that placed the box differently | 0 | 0 to 0.031 | 0.003 to 0.034 |
| The same, its edge inside the fill (DEC-039), em² | 0 | 0 | 0.003 to 0.005 |
| Capitals whose feet rest on a later box's top edge, its edge centred or clipped with the fill, em² | 0 | 0.19 | 0.20 |
| The same, the box drawn as DEC-039 point 4 draws it, em² | 0 | 0 | 0 |
| The same on a path's top edge, drawn as DEC-039 point 4 draws it, at nine steps an eighth of a device pixel apart: em², at the steps where it lost ([project-kit#3122](https://github.com/aleskalfas/project-kit/issues/3122)) | 0.078 to 0.081, at 4 | 0.078 to 0.081, at 6 | 0.084 to 0.086, at 6 |
| A box whose edge meets a letter's side, em² | 0 | 0 | 0 |
| A comma under a box, em² | 0.026 | 0.026 | 0.036 |
| A háček under a box, em² | 0.023 | 0.028 | 0.039 |
| A line set 9 px above the top of its file's first page: its ink past the edge | 41% | 41% | 41% |

- **Hiding a span names text that shows.** Found by hiding the span, a white text on the page with no ground lost all its ink, a text in its box's colour 72%, and a white text on its own black ground 61%. Found by changing only its letters' colour, each lost none.
- **Two colours.** The probes changed a span's letters between the forced palette's text colour and its ground colour, which forcing keeps.
- **Strength in a draw of its own.** Drawn alone in those two colours, every span's strong ink lost what it lost when measured from its own paint on a white and a black ground. The words at 30% alpha had no strong ink in their own paint.
- **The ink read without other backplates.** Under both forced palettes, an ink read that left the other lines painted saw a quarter of the ink of the words under a later text, and 94% of the heading's first line. With every line but the span's own hidden, it saw all of it, and the span's letters took the forced palette's text colour.
- **A graze between texts.** Where a box lies between two texts in the tree, the heading's graze is named where it passes the sliver. At the step's scale it lost 0.002 em² in the light forced palette, below the sliver the probes used, 0.01 em², and 0.0104 em² in the dark, just past it, which another machine may not repeat.
- **A forced edge.** Centred on a box's outline, the edge a forced palette gives an opaque fill reached over the descenders' tips, by as much as the edge fell over them among the device's pixels, and over the feet of capitals resting on the box. Drawn as DEC-039 point 4 draws a box, the box hid the device row it hides in its own colours. In a dark image that row held more strong ink, since the read draws a span alone there light on a dark ground: at a scale of 1, three of its smoothed pixels reached 0.51 to 0.75 of the two colours' difference, where drawn dark on light none passed 0.49. Descenders whose foot the box's edge met lost 0.003 to 0.005 em² in the dark forced palette at 1.225. At a scale of 1, the edge over their foot by up to half a device pixel, they lost 0.0117 em², past the sliver the probes used, in a dark key without forced colours as in the dark forced palette, and none in a light key or the light forced palette. With its two colours swapped in a dark image, the draw alone found none there either. A path drawn so still hid a device row of the capitals at one or two of nine steps more than its own colours did, at each scale below 2 (DEC-039 point 4's known gap).
- **The sliver's room.** The most an unnamed plant lost in the first four probes was 0.003 em². Set at the planted page's 14 px, the edge control's last device row held 0.017 em² of strong ink at 1.225, and 0.036 at a scale of 1. The fifth probe set the control at ems of 17 to 40 device pixels. At each, its last device row held the same share of its em at all four scales, within two device pixels, and a box drawn as DEC-039 point 4 draws it, at nine steps an eighth of a device pixel apart, hid that row or nothing. The share does not fall with the em alone: from 17 to 28 device pixels the row held 0.020 to 0.031 em² in one mode or another, at 32 at most 0.015, and at 40 at most 0.006. The háček of a ž at 16 px, under a box, lost least at 0.625, where its em lands at the command's text floor of 10 device pixels: 0.0195 em², against 0.026 to 0.040 at the other scales. Set at that floor at each of the four scales, the sixth probe's háček lost two to five device pixels, 0.0195 to 0.05 em², at nine steps an eighth of a device pixel apart, in every mode. At the floor one device pixel is 0.01 em². At 0.625 and 1.225 the probes read it as 0.0098, and two as 0.0195, since they took the scale from an image's width rounded to whole pixels.
- **The top edge.** With no room above the first page, the line past its top lost nothing, so its cut was silent.
- **The cost.** Measured on that Mac at 1.225, in a naive form: each span read alone, one at a time, its four images taken and decoded in Python's standard library. That run timed taking and decoding the images, not comparing them or the room past the page's edges. The probes' own reads, which took, decoded and compared a span's four images in about 0.2 s, suggest those add little. Without these reads, DEC-020 point 6's four reads took 0.08 s for each span in each key or forced palette, and these reads added 0.21 to 0.26 s, about a fifth of it decoding. Each figure below is a saved run:
  - **One look of the showcase deck,** in one language and one key, 108 spans: 14 s without these reads, and 38 s with them on every span.
  - **The run in the CI of the repository the capability is authored in,** every language and key of the deck and of that repository's other piece: 58 s without these reads, and 2.7 minutes with them. On that CI's runner the run without them took 60 to 74 s in six runs on 13 November, its log shows, so the runner takes 1.04 to 1.28 times the Mac's time.
  - **The look at every page before the designer stops** ([visual-communication:DEC-030-design-agents] point 2), the deck in every language and key and under forced colours: 1.6 minutes without these reads, and 4.7 minutes with them.
  - **A pre-filter** by the browser's own boxes, widened by an em, left 85 of the deck's 108 spans to read, and 9 of the other piece's 15. It was counted, not timed.
  - **Extrapolated, not measured:** a look grows by about 0.22 s for each span in each key or forced palette it draws, so a piece three times the deck's size takes about two minutes a look in one key. On that CI's runner the deck's look in one language and one key would take 39 to 48 s with these reads, and its look in every language and key 2.4 to 2.9 minutes, against 46 to 57 s without them.

**Not reached:** a picture under a text, a page that carries z-index, a fixed page and its keyline, a page after the first, ink past a page's other edges, a span both cut and covered, a light weight at a small size, a scale below 0.625 or above 2, a comma below 1.225, a real forced palette, another browser, Linux, a Mac set to light.

## Decision

**Through a browser, the check for dropped text names each span that another part covers or the page's edge cuts, in one entry for each cause with the share of its ink lost, found in what the browser drew.**

### 1. A span the page does not show in full is dropped

- **What is named.** A span that left no ink, or lies wholly off its page, is named (DEC-020 point 6). So is a span that is cut or covered. A span is *cut* where part of its strong ink lies past its page's edge. A span is *covered* where the page drawn whole hides part of its strong ink on the page, under a part drawn after it: a shape, a line of text, or under forced colours a text's ground.
- **A sliver does not count.** A loss smaller than an area the outputs page states, in the span's em², names no entry. Each cause is judged alone.
- **A fault mended where it arises.** A cut or covered span is mended where its cause lies: in the piece's layout or content, or in the spacing a component or a brand sets between lines and between texts. No such loss is accepted.
- **Through a browser alone.** Through the SVG renderer, `dropped` keeps its meaning: what resvg drew nothing of ([visual-communication:DEC-015-viewing-step-and-reviewer] point 3). That report says that cover and cut were not read.

### 2. Each cause is an entry of `dropped`, with its share

- **No field of its own.** A cut or covered span is an entry of `dropped`, beside a span that left no ink and a span that lies off its page, and it names what those entries name.
- **One entry for each cause.** Each entry gives one cause in `why`: no ink, off the page, cut or covered. A span both cut and covered gives two entries. A span wholly off its page is named off the page alone.
- **Its share.** A cut or covered entry gives the share of the span's strong ink that its cause loses.
- **The command prints each entry** in words that read for its cause, with its share.

### 3. It is measured in what the browser drew

- **What is measured.** A span's strong ink, and how much of it the page drawn whole shows on the page. Each span is named or cleared from what the browser drew and where it laid each part out, never from the scene's frames, nor from its draw order, the tree's order, taken alone.
- **Strength in a draw of its own.** A span's strong ink is measured where its letters alone are drawn, with no other text and no text's ground: outside forced colours in the browser's text colour on its ground colour, CSS's `CanvasText` on `Canvas`, under the image's scheme ([visual-communication:DEC-031-html-page-backdrop] point 3), and under forced colours in the palette's. So a letter's strength is its shape's, whatever the alpha of its paint, and a dark image draws the span light on dark. The ink read keeps the span's own paint (DEC-020 point 6).
- **A dark image's residue errs toward naming.** Light on dark, more of a letter's smoothed edge counts as strong (Context). So the read may name in a dark image a graze that a light one leaves unnamed, and never leaves a lost text unnamed, a cost accepted.
- **Room past every edge.** The read gives each page room past each of its edges, enough for all the ink of each span that crosses one, and keeps each page's size. Past a fixed page's edge the read paints its own ground and hides the keyline ([visual-communication:DEC-031-html-page-backdrop] point 1).
- **What the page shows of it** is what changes in the page drawn whole when the span's letters alone change between the draw alone's two colours, which forcing keeps. Its ground and its sign stay as they are.
- **Cheaper ways stay open.** A *pre-filter* may pass over a span whose box in the browser, widened by its em, stays inside its page, with no other text near it and no box of a part painted after it. It takes the painting order, what is painted after a span, from the browser's painting, or from each element's z-index, a span taking its text's, and, among elements of equal z-index, their order in the document, within its page; never from the document's order alone. The read may draw many spans alone at once, and change many spans' colours at once, where their widened boxes do not meet.

### 4. What stays the reviewer's

- **A text that shows, yet reads poorly,** such as a faint text over a picture or a translucent fill, and a text in the colour of what lies under it. The check measures contrast where it can, and the reviewer judges the rest ([visual-communication:DEC-004-brands-and-notations] point 8).
- **A part that is no text,** such as a shape, a line or a picture, whether covered or cut.
- **The images themselves.** The reviewer reads in the images it is given what the report does not name, and its report says what it looked at (DEC-015 point 7).

### 5. The first read plants each loss

- **Named in every start** (DEC-020 point 7): a span cut past its page's top edge, and, as covered, the text under a later box, the háček plant, a span wholly under another text, which is never named as one with no ink, and a span whose cover lies earlier in the document but over it by z-index, as DEC-020 point 3 allows.
- **The cover by z-index lies on a page of its own** in the planted file. The other plants stay on its first page, which carries no z-index, so each start meets the pre-filter on both kinds of page.
- **Left unnamed:** a text under a translucent fill, the edge control, and the text in the colour of its ground.
- **Two plants are set in device pixels.** Each start's first read sets the edge control's em at the one number of device pixels the outputs page states, and the háček plant's at the command's text floor (DEC-015 point 5), each from its page's drawn width and its start's device scale. So each holds the same share of its em in every start.
- **The sliver lies between them.** The area the outputs page states is set once: above the most strong ink the control's last device row holds in any key or forced palette, and below the háček plant's loss. So the control holds the read's threshold, that a graze of its last device row stays unnamed wherever the box's edge falls among the device's pixels, and each start's first read holds both sides of the sliver. A page too wide for one image may set text below the floor, and its report already says that its smallest text may not read ([visual-communication:DEC-022-web-site-and-parts] point 7).
- **Its rule under forced colours is the renderer's.** Only a fill opaque in every key takes the reader's ground, so the translucent fill stays ([visual-communication:DEC-023-html-page-modes] point 7).
- **The text left to forcing,** which holds DEC-039's grounds in the forced start, is as DEC-039 point 5 sets it.

## Rationale

**Why the report names these losses.** A text the page does not show is a part missing, whatever the cause, even where the browser drew it, and the report names such a loss once for every image. Left to the eye, a line lost in one language under one forced palette is found only by reading that one image. A cut text is a fault of layout even where a browser shows it: a page clips no text (DEC-020 point 4), so the text spills onto what lies past the page, which no design holds.

**Why from the browser's drawing.** The scene does not know a backplate, or which fill hides what lies under it. A fill's opacity, a picture's transparent pixels and the colours a forced palette gives are all the browser's. Nor does the scene know the browser's own text widths, which can put a line past an edge that the engine's measure keeps inside. This is the reason the step judges what the tool drew, not the page's names (DEC-015, its Rationale). The browser's own boxes are its layout, so the pre-filter, which passes over a span they show nothing near, still rests on the browser. On a page that carries z-index (DEC-020 point 3), the document's order no longer tells what is drawn after a span, and a read that took it alone would pass over a covered span in silence. On a page that carries none it tells the painting's order whole, so the first read holds the pre-filter on each kind of page.

**Why strong ink, in a draw of its own, and an area in the em.** A part's smoothed edge hides only a letter's faint rim, so counting strong ink alone leaves it out however long the edge runs, and a translucent fill lets strong ink through. Drawn alone in one opaque colour on another, a text in a translucent colour counts as any other. The ink read keeps the span's own paint, so a span with no paint is still named as one with no ink. The same two colours serve the draw alone and the page drawn whole, so no other ground is needed. An area keeps a lost comma or háček, which changes a word's meaning. In the span's em², it keeps them at a legend's size as at body size. A graze along an edge, a row of pixels, still grows and shrinks with the device scale, so the reviewer reads what the sliver leaves. A share of the span's ink would miss a long line that loses one short word. An eroded mask would wear away a háček's thin strokes at the step's scale.

**Why both plants are set in device pixels.** A graze is a device row, so a control set in px of the page loses a larger share of its em at a smaller scale: at a scale of 1 its last row passed a háček's loss, and no one sliver both cleared it and kept the háček. Set in device pixels, it loses the same share in every start, so one sliver serves them all, where its em leaves that row below a háček's loss. Planted at the command's text floor, the smallest size at which a start keeps a page's text, a háček stops the run in every start where the sliver, changed on the outputs page, would leave it unnamed.

**Why one entry for each cause.** `dropped` already holds a span off its page, which is a loss of layout, not of drawing, and each of its readers takes an entry as a part missing. The cause says where the fix lies: a span with no ink in its paint or the file, a covered or cut span in the layout, the content or the step. One cause to an entry keeps `why` one string, as its readers parse it, and gives each cause its own share. A span wholly off its page loses all of its ink to one cause, its place. So a reader can sort the entries, and the sliver's area can change on the outputs page with no new record.

**Why a change between two colours, not a hidden span.** Hiding a span hides its ground and its sign too, so a text on its own ground, or in the colour of what lies under it, read as lost (Context). Changing its letters alone shows where the page lets them through, whatever their own colour. Two colours forcing keeps tell the letters from what lies over them in every key and forced palette.

**Why the colour of what lies under it stays out.** Nothing lies over such a text, and the contrast check already measures the pairs a brand declares (DEC-004 point 8). Naming it in `dropped` too would give one fault two lists.

**Why no other text in a span's draw alone.** With other texts and their grounds painted, a span under one reads as a span that drew no ink, which sends its fix to the wrong place, and a span partly under one reads as whole.

**Why no such loss is accepted.** A covered or cut text still reaches a reader's tools as words the page does not show. So type meant to be partly hidden is drawn as a shape or a picture, not a text.

**Why the SVG renderer waits.** Through resvg the page's frame clips a cut text, so it is gone for every reader. Its read needs a canvas past the page and a read of cover of its own, a change of resvg's module, which [project-kit#3111](https://github.com/aleskalfas/project-kit/issues/3111) builds. Until then its report says what it did not read, so an empty list never reads as clean.

**The cost, accepted.** These reads add about 0.22 s for each span in each key or forced palette to the 0.08 s DEC-020 point 6's four reads take without them, so the looks of the showcase deck of the repository the capability is authored in take two and a half to three times as long (Context). The build loop a designer works looks at a page after each change, and a look of a piece the deck's size stays under a minute, which keeps that pace. A larger piece's look grows with its spans, so the cost is revisited where a look comes to hold up a build loop. The look at every page before the designer stops (DEC-030 point 2) runs once in a round, beside the reviewer's read of every image, so a few more minutes there slow no step that repeats. In that repository's CI, the run stays well inside its job's 30 minutes, with room for a slower runner and more pieces. So the cost is accepted as the price of a report that names every lost text. Point 3 leaves the build room to make the read cheaper.

### Alternatives considered

- **A field of its own for covered and cut text:** the same fault would sit in two lists, and `dropped` already holds a span off its page.
- **One entry for a span, its causes in a list:** `why` would no longer be the one string each reader of the report parses.
- **The scene's frames and draw order, read by the check:** these are blind to a backplate, to which fill hides, and to the browser's text widths.
- **Only a span the page shows none of:** this misses a line that a ground covers all but a few letters of.
- **The browser's hit testing of what lies over a span:** it knows no opacity and no ground, and the layers take no pointer (DEC-020 point 3).
- **Leaving these losses to the reviewer:** every image would have to be read to find them.
- **Hiding the span to find what the page shows of it:** it names a text on its own ground, and a text in the colour of what lies under it.
- **The span's letters changed to one colour:** a span already in that colour reads as wholly covered.
- **Strength from the span's own paint, on a white and a black ground:** a text in a translucent colour has no strong ink, so none of its losses would be named, and it takes two images more for each span.
- **The ink read itself drawn in an opaque colour:** a span with no paint would show ink, so the read that names it, and its plants, would go blind.
- **A text in the colour of what lies under it as covered, or as a fifth cause:** the contrast check measures it where a brand declares the pair, and the reviewer elsewhere.
- **A sliver in px of the page, by its count of pixels, as a share of the span or by an eroded mask:** one area misses a comma at a legend's size, a seam grows with its length, a share misses one word in a long line, and erosion wears away thin strokes.
- **The edge control set in px of the page, the sliver set from its last row at the smallest scale a start uses:** at a scale of 1 that row passed a háček's loss.
- **A list of accepted covers and cuts:** such a text still reaches a reader's tools.
- **A finding at validation, from the engine's measure, for a cut text:** a complement for SVG runs and for sessions with no browser, which #3111 weighs, and no replacement, since it misses what a browser's widths push past an edge and reads no cover.
- **The cover by z-index planted on the page that holds the other plants:** that page would carry z-index, so no plant would meet the pre-filter on a page that carries none.
- **The SVG renderer too, in the same change:** a change of resvg's module of its own, while its report's notice keeps the gap seen.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). The first overturns one sentence of DEC-020 in part, and each of the others refines its record in place.
  - **DEC-020's top line** reads *Partially superseded by* [visual-communication:DEC-037-text-the-page-hides], in the shape of [visual-communication:DEC-003-change-over-time]'s. Overturned: point 6's last sentence, "It asks nothing of what lies over a text", so far as a text under a part drawn after it, which the check names as covered through a browser. The rest stands, a text in the colour of its ground among it, and that sentence stays as it stood.
  - **DEC-020 point 6, "Ink".** It comes to say that each span is drawn alone in its own paint, with no other text and no text's ground, with room past its page's edges; that a span's strength is measured in a draw of its own, its letters alone, outside forced colours in the browser's text colour on its ground colour, `CanvasText` on `Canvas`, under the image's scheme, and under forced colours in the palette's; and that the read reports a span the page's edge cuts, as cut, with the share of its strong ink past the edge.
  - **DEC-020 point 7, "What may not".** Its "a small page" and "reads that page" come to speak of the planted file and its pages, as the edit to DEC-027's "The same planted page" below does, and its "That page also holds a mode" and "the box in which that page holds the signal's mode" come to speak of the planted file's first page. It comes to add that the planted file also holds the plants the check must name as covered (this record's point 5): the text under a later box, the háček plant, a span wholly under another text, never named as one with no ink, and, on a page of its own, a span whose cover lies earlier in the document but over it by z-index. It also comes to add that the planted file's first page holds the plants this record's point 5 leaves unnamed, that the edge control and the háček plant are set in device pixels from each start's device scale, and that the run stops where the check names a plant it must leave unnamed.
  - **DEC-027 point 4, "The same planted page, its checks unchanged".** "The same planted page" comes to read "the same planted file and its pages", and the bullet's last sentence to say that the reads name, and leave unnamed, what the first start does.
  - **DEC-027 point 4, "The four reads run in each forced image".** The list of what the ink read names comes to add a span the page's edge cuts, and the bullet comes to add that the read of the page drawn whole, this record's point 3, names there a span a later part covers, a text's ground among them.
  - **DEC-015's summary, its Decision's sentence and point 3's heading.** "Text drawn to nothing never passes in silence" comes to say that no text the page does not show passes in silence, whether the tool drew it to nothing or, through a browser, the page hides or cuts it.
  - **DEC-015 point 3, "Each text, or run of a text, the tool dropped".** It comes to add that through a browser it names each text the page drawn does not show in full, covered or cut by the page's edge, in one entry for each cause with its share, and that through resvg the report says that cover and cut were not read.
  - **DEC-031 point 5, "The reads hold", and the line of its Implications on DEC-020 point 7.** Each "no read looks outside a page" comes to say that the read past a page's edge paints its own ground there and hides the keyline, and each "planted page" comes to read "the planted file's pages", which need no keyline.
  - **[visual-communication:DEC-022-web-site-and-parts], its Implications, "A brand's or a local part past a page's edge".** It comes to add that a text past it is named as cut.
- **The reviewer's agent file** comes to say, in #3088's change, that a cut or covered entry is the fault of a part missing or blank, and is never accepted. A covered entry whose cover is another text is not counted again as text over text, which keeps the overlaps the report does not name. Where a run through the SVG renderer says that cover and cut were not read, the reviewer reads them in its images, and its report says it did.
- **The capability's page on outputs** comes to say, for each renderer, what `dropped` holds, its causes and shares, and the numbers that set strong ink and what hides it: the sliver's area and the edge control's em in device pixels. **The `visual-author` skill's build loop,** in its table of what to do with each entry of the report, comes to say what mends each cause, and that the draw order mends both of DEC-039's exceptions (its Rationale): a part between two texts drawn before both, or after both where it meets neither text's letters, and a clipped shape, such as a path or a sign, drawn before the text that rests on it, whose cure [project-kit#3122](https://github.com/aleskalfas/project-kit/issues/3122) follows up. Both in #3088's change.
- **This record rests on DEC-039,** and the two are accepted together, in #3088's change.
- **#3088** builds points 1 to 5, point 3's pre-filter among them, drawing many spans alone at once, with a test that draws each loss and finds it in the report. In the repository the capability is authored in, its changeset is `minor` for visual-communication.
- **The planted file's pages** take DEC-039's form under forced colours, as a page in the renderer's form does.
- **Before #3088 closes,** the forced start's first read runs once on Linux.
- **Read against this record, and left as they stand:**
  - DEC-020 point 4, "A page clips no text". The read's room changes no page's size.
  - DEC-023 point 6. The reads run in each key drawn and in each forced palette, in each language's page file.
  - DEC-022 point 7. Each page is read whole, so a band's edge cuts no span.
  - [visual-communication:DEC-036-concept-signs] point 3. A run's ground and sign stay as they are when the read changes its letters' colour.
- **Revisit this record** if a browser comes to paint a forced fill or a ground in a way that makes the read name a text that shows, if the sliver's area names a text that shows or misses a mark a reader needs, if a graze named in a dark image alone comes to cost a person's look, which a draw alone in a dark image with its two colours swapped, dark on light, cures, if a start comes to draw at a device scale below 0.625, below which no probe showed the edge control left unnamed and the háček plant named, if the command's text floor falls, if, in the CI of the repository the capability is authored in, a look of one of that repository's pieces, divided by its languages and keys, passes a minute, if the reads come to hold up a piece's build loop, or when #3111 builds the SVG renderer's read of cover and cut.
