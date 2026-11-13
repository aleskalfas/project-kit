---
id: DEC-037
title: A text another part covers, or the page's edge cuts, is reported as dropped
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when the viewing step draws a page through a browser, its report lists in `dropped` every text the drawing does not show in full. That is a text that drew no ink or lies wholly off its page, a text another part covers, and a text that runs past the page's edge, whether it loses all of its letters or only some. The step finds each one in what the browser drew, never in the scene's frames. How well a text that does show reads is for the check and the reviewer to judge. For example, under the dark forced palette a footer's backplate covers a line, all but its last three letters. The report lists that line in `dropped` for that palette, as covered.

## Context

[project-kit#3088](https://github.com/aleskalfas/project-kit/issues/3088) asks that the report list in `dropped` every text the drawn image does not show. On the showcase deck drawn at the projector size ([project-kit#2973](https://github.com/aleskalfas/project-kit/issues/2973)), the graphic-design-reviewer found lost text that `dropped` did not list. Under the forced palettes, a footer's and a limit's backplates covered lines in both languages, and notes and a legend ran past the page's edge or under another part.

The records leave these losses out by design. The check for dropped text asks nothing of what lies over a text, and it names a span that lies wholly off its page, never one that the page's edge cuts ([visual-communication:DEC-020-html-page-drawing] point 6). Under a forced palette it names a span off its page, or one that drew nothing ([visual-communication:DEC-027-forced-colours-viewing] point 4). A probe of a page with each loss found that the report named only the text wholly off the page. It also found that the ink read leaves other texts' backplates painted. So a span wholly under one is named as one that drew no ink, and a span partly under one is not named at all.

Terms:
- A *backplate* is the ground a browser paints behind each line of text under forced colours, in the forced palette's ground colour.
- The *page drawn whole* is a page as its image shows it, in one key or forced palette, with every part painted.
- A span's *ink* is as [visual-communication:DEC-020-html-page-drawing] point 6 defines it: what the span draws alone.

## Decision

**Through a browser, the check for dropped text names in `dropped` each span that the page drawn whole does not show in full, whether another part covers it or the page's edge cuts it, and finds each one in the browser's own drawing.**

### 1. A span the page does not show in full is dropped

- **What is named.** A span that left no ink, or lies wholly off its page, is named (DEC-020 point 6). So is a span that is cut or covered. A span is *cut* where part of its ink lies past its page's edge. A span is *covered* where part of its ink on the page does not show in the page drawn whole: under a later part, under a later text's backplate, or in the colour of what lies under it.
- **In part counts.** A span is named whether it loses all of its ink or only part of it. A sliver, such as a smoothed edge where a letter meets another part, does not count, and the step declares how large a sliver may be.
- **Through a browser alone.** Through the SVG renderer, `dropped` keeps its meaning: what resvg drew nothing of ([visual-communication:DEC-015-viewing-step-and-reviewer] point 3).

### 2. Each is an entry of `dropped`, with its cause

- **No field of its own.** A cut or covered span is an entry of `dropped`, beside a span that left no ink and a span that lies off its page, and it names what those entries name.
- **Its cause.** Each entry says which of the four it is: no ink, off the page, cut or covered.

### 3. It is found in the browser's drawing

- **A span's ink is drawn alone,** with no other text painted and no backplate, on the ink read's two grounds, in a band that reaches past its page's edge.
- **What the page shows of it** is what changes in the page drawn whole when the span alone is hidden.
- **Never from the scene's frames** or its draw order.

### 4. What stays the reviewer's

- **A text that shows, yet reads poorly,** such as a faint text over a picture or a translucent fill. The check measures contrast where it can, and the reviewer judges the rest ([visual-communication:DEC-004-brands-and-notations] point 8).
- **A part that is no text,** such as a shape, a line or a picture, whether covered or cut.
- **The images themselves.** The reviewer reads every image the run drew, for all that the report does not name (DEC-015 point 7).

## Rationale

**Why the report names these losses.** A text a reader cannot see is a part missing, whatever the cause, and the report is where such a loss is named once for every image. Left to the eye, a line lost in one language under one forced palette is found only by reading that one image. That is how the showcase's lost lines were found.

**Why from the browser's drawing.** The scene does not know a backplate, or which fill hides what lies under it. A fill's opacity, a picture's transparent pixels and the fills a forced palette makes opaque are all the browser's. Nor does the scene know the browser's own text widths, which can put a line past an edge that the engine's measure keeps inside. This is the reason the step judges what the tool drew, not the page's names (DEC-015, its Rationale).

**Why a partial loss counts.** A line that loses a word is lost to its reader. In the probe, a backplate covered a line all but three of its letters. A sliver is left out, since a smoothed edge where a letter meets another part would otherwise name every text that touches a line.

**Why `dropped`, and why a cause.** `dropped` already holds a span off its page, which is a loss of layout, not of drawing, and each of its readers takes an entry as a part missing. A field of its own would give the same fault two lists. The cause says where the fix lies. A span with no ink is mended in its paint or in the file. A covered or cut span is mended in the layout or the content.

**Why no backplate in a span's ink.** With other texts' backplates painted, a span under one reads as a span that drew no ink, which sends its fix to the wrong place, and a span partly under one reads as whole.

**The cost.** The ink read draws more of each page, in each key and forced palette, so a run takes longer.

### Alternatives considered

- **A field of its own for covered and cut text:** the same fault would sit in two lists, and `dropped` already holds a span off its page.
- **The scene's frames and draw order, read by the check:** these are blind to a backplate, to which fill hides, and to the browser's text widths.
- **Only a span the page shows none of:** this misses a line that a backplate covers all but a few letters of.
- **The browser's hit testing of what lies over a span:** it knows no opacity and no backplate, and the layers take no pointer (DEC-020 point 3).
- **Leaving these losses to the reviewer:** every image would have to be read to find them.
- **The SVG renderer too, now:** that is a change to resvg's module that no loss has asked for, and it can follow as a change of its own.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-020 point 6, "Ink."** It comes to say that a span is drawn alone with no other text and no backplate painted, in a band that reaches past its page's edge, and that the read reports a cut or covered span with its cause.
  - **DEC-020 point 6, "It asks nothing of what lies over a text".** It comes to say that the read names a text whatever lies over or under it, as far as the page does not show its ink, and that how well a text that shows reads is for the check and the reviewer.
  - **DEC-027 point 4, "The four reads run in each forced image".** Its list of what that palette's reader loses comes to add a span the page's edge cuts, and a span that a later text's backplate, or a fill the palette made opaque, covers.
  - **DEC-015 point 3, "Each text, or run of a text, the tool dropped".** It comes to add that through a browser it names each text the page drawn does not show in full, whether covered or cut by the page's edge.
  - **DEC-031 point 5, "The reads hold".** "No read looks outside a page" comes to say that the read past a page's edge paints its own ground there too, so the planted page still needs no keyline.
- **The capability's page on outputs and the build loop's table** come to say what `dropped` holds through a browser, its causes and the size of a sliver, in #3088's change.
- **#3088** builds points 1 to 3, with a test that draws a page with each loss and finds it in the report.
- **Read against this record, and left as they stand:**
  - DEC-020 point 7 and DEC-027 point 4's first read. The planted page holds one fault of each kind the reads name, so it gains a cut span and a covered span.
  - [visual-communication:DEC-023-html-page-modes] point 6. The reads run in each key drawn and in each forced palette, in each language's page file.
  - [visual-communication:DEC-022-web-site-and-parts] point 7. Each page is read whole, so a band's edge cuts no span.
- **Revisit this record** if a browser comes to paint a backplate or a forced fill in a way that makes the read name a text that shows, or if a loss through the SVG renderer is found by the reviewer and missed by the report.
