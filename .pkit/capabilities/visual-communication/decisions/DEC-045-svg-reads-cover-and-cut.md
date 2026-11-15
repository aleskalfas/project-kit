---
id: DEC-045
title: Through the SVG renderer, the viewing step names a text another part covers, or the page's edge cuts, as dropped
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when the viewing step draws a page of the SVG renderer through resvg, its report lists in `dropped` each text the page does not show in full, as it does through a browser (DEC-037). A text the page's edge cuts, and a text a part drawn after it covers, each take one entry with the cause and the share of the text's strong ink the cause loses. The tool's own drops take a cause too, so every entry of `dropped` names one in `why`. The notice that cover and cut were not read goes. For example, where a later box covers the last words of a note, the report lists that note as covered, with its share.

## Context

[visual-communication:DEC-037-text-the-page-hides] has a browser's report name the texts a page hides, and leaves the SVG renderer's report to say that cover and cut were not read until [project-kit#3111](https://github.com/aleskalfas/project-kit/issues/3111) builds the read. Through resvg a cut text is gone for every reader, since the page's frame clips it, so a reader of the report has less to find it by than through a browser, where it spills past the page.

Terms are DEC-037's: a span's *strong ink*, a *sliver*, a text *cut* and *covered*.

This record departs from DEC-037 in three places, each its point below. The sliver is resvg's own number (point 1), since DEC-037's was set from a browser's drawing. The tool's own drops take a `why`, which DEC-037 point 2 asks of every entry (point 2). The SVG renderer's report no longer carries `dropped-not-read` (point 2).

### What the probes showed

Probes drew a page of the SVG renderer through the tool's module, resvg 0.48.1 in `resvg-py` 0.5.0, on one Mac, in one face (Source Sans Pro Regular). Each set a text at an em in image pixels and drew it at five scales: 0.5, 1, 1.225 and 2, which are DEC-037's, and 0.8167, at which a 1920 by 1080 page is drawn 1568 pixels wide (DEC-015 point 5). A graze and a háček were drawn at the same eight ems, 10 to 40. Their code is thrown away.

- **A graze.** A later box's top edge stepped a quarter of an image pixel across the foot of the descenders of "Typography gypsy". resvg hides a pixel only where the box wholly covers it, so the loss came in whole rows. The table gives the least a graze lost, one row, the range over the five scales, in em².
- **A háček.** A later box over the háček of a ž, at the same ems and scales. It lost 2 to 39 pixels, the range over the five scales in the table.
- **Phase.** Moving the text by an eighth of a pixel changed no háček's loss.

| em, image px | 10 | 12 | 16 | 20 | 24 | 30 | 35 | 40 |
|---|---|---|---|---|---|---|---|---|
| least graze | 0.08 to 0.13 | 0.042 to 0.125 | 0.016 to 0.020 | 0.005 to 0.063 | 0.037 to 0.061 | 0.011 to 0.041 | 0.010 to 0.035 | 0.004 to 0.009 |
| háček | 0.020 to 0.030 | 0.014 to 0.021 | 0.020 to 0.023 | 0.020 to 0.025 | 0.021 to 0.023 | 0.021 to 0.022 | 0.020 to 0.023 | 0.023 to 0.024 |

A háček never lost under 0.0139 of its em squared, 2 pixels at an em of 12. A graze's least row lost under 0.0125 only from an em of 20 up, and then at some scales alone: it depends on how much ink the last row of the foot holds. At an em of 10, 12, 16 and 24 it lost more than 0.0125 at every scale. The text floor is 10 pixels (DEC-015 point 5), where one pixel is 0.01 em². DEC-037's 0.01 does not hold on these: the graze of the control at 40 stays under it, but a háček at 12 loses 0.0139, over the sliver set below by little. Not probed: another face, a picture under a text, another machine, an alpha under a part's fill.

## Decision

**Through resvg, the tool's module names each span that another part covers or the page's edge cuts, in one entry for each cause with the share of its strong ink lost, found in what resvg drew.**

### 1. How it is measured

- **Strong ink, in a draw of its own.** A span is drawn alone, as the check for ink draws it, its letters opaque black on the white ground, with no other span of its text. A pixel is strong where it lies nearer black than white, so a letter's strength is its shape's, whatever the alpha of its paint.
- **Room past the page.** The band that holds the span reaches a page's width past each of the page's sides, and two of the span's largest font sizes either way of its baseline, past the page's top and foot too. A page's frame clips nothing in this draw. A text that runs further than the band counts as far as the band holds, so its share is of the ink inside it, and it is cut all the same. The band is first drawn with room for two font sizes, and drawn again at a page's width where it shows no strong ink or the ink comes within a font size of its side. The draw's cost grows with its width.
- **Cut and covered.** Strong ink past the page's edge is cut. For cover the page is drawn whole twice on the span's ink, its letters black and then white, all else as it stands, and strong ink on the page that the two draws show alike is covered. A span with strong ink on the page is cut or covered, or neither. A span with none on the page, all of it past an edge, is off the page (point 2).
- **The sliver is resvg's.** A cause hiding less than 0.0125 of the span's em squared, in image pixels, and never a single pixel, names no entry, and each cause is judged alone. It lies under every háček the probes drew, the least 0.0139, and over the most a thin last row of a graze lost, 0.0111 at an em of 30, 0.0098 at 35 and 0.0088 at 40. At an em of 12 it is 1.8 pixels and a háček's 2 pixels pass it. Where it comes under 1.5 pixels, which is below an em of 11, the second bound holds a single pixel unnamed: a one-pixel háček at the text floor, 0.01 of its em squared, is unnamed by design.
- **What it spares, and what it names.** It spares a graze only above an em of about 20 image pixels, and then only where the last row of the foot is thin. Below that a graze is named: its least row hides 0.016 to 0.13 of the em squared, as much as a háček and more, so no number tells the two apart there. At 24 px text on a 1920 page drawn at 0.8167, an em of 19.6, a descender's foot a later box touches is named covered. That is the loss as the page shows it, a row of ink a reader of a text that small misses, and DEC-037 accepted that a graze grows and shrinks with the device scale: here it grows as the em shrinks. The cure is the layout's.
- **What stands round a text.** The reads draw a span alone at its place, so they follow a group's move and nothing else. The renderer writes round a text groups that hold the page's marks, `data-id`, `data-component` and `data-version`, and a `translate` as their move, and no clip, mask, opacity, filter or other transform. The tool fails a page whose group carries any other attribute or transform, naming the group, rather than read ink a clip hides as a cover. A test draws the renderer's groups and finds no other.
- **What stands round the page.** The bands carry the page's own `<style>`, `text{white-space:pre}` among its rules, and the page's root carries no attribute a text inherits: only its size, view and marks. The tool fails a page whose root carries any other. resvg 0.48 reads `white-space:pre` in neither the page nor a band, so the spaces of a text collapse alike in both, and a test plants a text of triple spaces and finds it named neither way. The carried rules hold the bands to the page's if resvg comes to read them.
- **Neither a pre-filter nor a batch is built** (the cost, below). SVG paints in document order, so the parts drawn after a span are known exactly, which a pre-filter for the cover read would use. But one draw of the page with all text removed shows the earlier parts as well, a ground or a panel the span lies on, so no band of it is blank; and a layer of only the later parts is a draw for each span, the cost it was to save. A box for every later part needs the whole of the path data the renderer writes, arcs and relative moves among it. The cover draw is cropped to the span's ink, which cut a draw from 1.06 s to about 0.1 s.

### 2. Entries and report

- **An entry of `dropped`,** as DEC-037 point 2 sets it: the element, the characters, `why`, and for `cut` and `covered` `share`. Every entry names one cause in `why`.
- **The tool's own drops take a cause.** A text or run resvg drew nothing of is `no ink`, or `off the page` where the span has no strong ink on the page, all of it past an edge. The entry keeps `whole`, true for a whole text and false for a run lost from a line, so a reader of it is unchanged. A span past an edge with any strong ink on the page is cut, so a text 100% past the edge is off the page and one 99% past is cut with a share of 0.99: one fault takes one cause, by how much of it lies on the page. The strong ink is read for each span before the drawing of its own paint, so a span wholly past an edge reaches it. A text that starts further past a side than the band holds, a page's width, finds no ink in it, and is told from a text with no ink by the engine's own geometry of its line, which the look holds: where the line lies wholly past a side, by its start, its measured width and its anchor, it is `off the page`. That is the line's geometry, so a span further past a side than a page's width on a line that starts on the page reads `no ink`, a line wider than two pages.
- **A text whose runs left for two causes** gives an entry for each run, with `whole` false.
- **`dropped-not-read` goes,** with the command's line that said it. A reader of the key breaks. It came with #3088's change, which no release holds yet, so no released reader does. The readers in the repository are the reviewer's agent file, the `visual-author` skill's build loop and the command's own print, all edited in this change.

### 3. What stays as it was

- **What the reviewer reads** is DEC-037 point 4's.
- **A finding at validation, from the engine's own measure, for a cut text,** is not taken. It reads no cover, and the engine's measure of a line and resvg's shaping differ (DEC-015), so its frame would call a text cut that resvg draws inside the page, and miss one resvg draws past it. In its strongest form, a finding at validation first and the read at the look as its backstop, it would stay a second place a cut text is named, to be kept in step with the first, for a measure that is wrong where resvg is the judge. The read at the look is the one place a text is named.

## Rationale

**Why the same two draws.** DEC-037's reasons for a draw alone and a change between two colours hold for resvg: the scene knows no cover, and changing one span's letters shows where the page lets them through, whatever their own colour. Others do not: resvg has no backplates, no forced palette and no z-index, so the document's order tells the painting order whole, and what hides a span is a later part's fill, its opacity, or a picture's alpha.

**Why room in the document the tool is given.** The page's frame clips a cut text away, so a read of the page as drawn finds a cut text whole or none of it. A band that reaches past the page holds the ink to count. The `_drew` draw of the tool's own drops has no room past the page, which is why a text wholly off it left no ink there and is told from a text with no ink by the read that has room.

**Why one `why` for every entry.** DEC-037 point 2 has each entry give one cause in `why` because its readers parse that as one string. An entry without one would break that for the SVG renderer's report alone. Every entry names one, so a reader sorts them by cause as through a browser, and `whole` stays for a reader that wants the text or run.

**Why the sliver is resvg's own.** A browser smooths a box's edge over the pixels it touches, and DEC-037 set its number between that graze and a háček's loss. resvg's graze comes in whole rows, and a row costs more of a small em than of a large one: at the text floor a row hides 0.08 to 0.13 of the em squared and a háček 0.02, so no number set between them spares the graze there. The number is set where it can hold: under every háček drawn, so none is lost, and over the thinnest last row of a graze at the sizes where one is thin, so the control at 40 stays unnamed. The cost is the graze named below an em of about 20, stated in point 1.

**The cost, accepted.** Measured on the same Mac, loaded, on one look of the showcase deck, 104 spans, in one language and one key, in CPU time, which a loaded machine inflates less than the clock: 8.0 s without these reads and 28.6 s with them, 3.6 times. Of the time the look spent in its reads, the cut read took about 0.37, 0.1 s a span, the cover read about 0.53, 0.07 to 0.09 s for each of its 208 draws, and the check for ink about 0.10. A look at every language and key of the deck, four looks, took 136 s of CPU, 34 s each, with the machine more loaded. The wall time under load, 33 to 58 s for one look, is not used here. On the CI's runner, 1.04 to 1.28 times that Mac's time (DEC-037), a look of the deck takes 30 to 44 s of CPU, under the minute DEC-037 sets, by a margin the Revisit watches. So the cost is accepted as the price of a report that names every lost text, and the build loop keeps its pace. The repository holds one deck. Before the cover read was cropped to the span's ink, one look of the deck took 4.4 minutes.

**Batching the reads, weighed and not built.** Drawing spans at once where their bands do not meet saves a draw's fixed cost, 0.007 s of a call with one face, against the cut read's 0.1 s a span: most of that read is the walk over its pixels, which batching does not shorten. For the cover read the page is drawn whole for a batch of spans whose ink does not meet, a page 0.25 to 0.37 s on three pages of the deck and 3.4 s on the fourth, twice for each group of spans: 8.6 s for one group on every page against the 15 to 18 s the cover read takes now, with one group a page, and the heavy page alone costing 6.8 s for it. Two texts whose ink meets fall in different groups, since drawing both in one colour at once would read the later one's ink as moved. The saving is about a quarter of the look at best, for a regrouping of the read, so it is left until a look comes to pass its minute (the Revisit).

### Alternatives considered

- **Keeping the notice:** a clean list would stay unreadable as clean, though a read now stands behind it.
- **DEC-037's sliver:** it sits on the control's graze at one scale, so the read would name a text that shows.
- **The page drawn once with the frame cleared:** it shows a cut text but never what covers one.
- **A pre-filter by the later parts' boxes:** point 1.
- **A group's clip or transform followed by the reads:** the renderer writes neither, so the code to follow them would have nothing to run on.

## Implications

- **Edits to accepted records,** made in this record's change and accepted with it, each citing it (COR-066 point 5). The first overturns one bullet of DEC-037 in part, and each of the others refines its record in place.
  - **DEC-037's top line** reads *Partially superseded by* this record, as [visual-communication:DEC-003-change-over-time] shapes it. Overturned: point 1's last bullet and the Rationale's "Why the SVG renderer waits", and what the Alternatives, the Implications and the Revisit say of that report and of the SVG renderer's read.
  - **DEC-037 point 1, its last bullet, "Through the SVG renderer".** It comes to say that through the SVG renderer `dropped` names a cut or covered span too, as this record sets. Its Rationale's "Why the SVG renderer waited" says so. Its Alternatives' two lines on a finding at validation and on the SVG renderer in the same change, its Implications' sentence on the reviewer's report and its line on DEC-015's summary, and its Revisit's last clause each say what stands.
  - **DEC-015's summary, its Decision's sentence and point 3's heading.** "Through a browser" comes out, so that no text the page does not show passes in silence, whether the tool drew it to nothing or the page hides or cuts it.
  - **DEC-015 point 3, "Each text, or run of a text, the tool dropped".** Its last sentence comes to say that through resvg too it names each text the page shows in part, in one entry for each cause with its share.
- **The capability's page on outputs** comes to say what `dropped` holds through the SVG renderer, with `why` on each entry, and the sliver's number and its floor. **The graphic-design reviewer's agent file** and **the `visual-author` skill's build loop** come to say it, and that `dropped-not-read` is gone. All three in #3111's change.
- **#3111** builds points 1 and 2, with a test that draws a page with each loss through SVG and finds it in the report, a test of the sliver's two sides at the scales above, and a test of the groups. In the repository the capability is authored in, its changeset is `minor` for visual-communication.
- **Revisit this record** if the sliver names a text resvg shows or misses a mark a reader needs, if in the CI of the repository the capability is authored in a look of one of that repository's pieces, divided by its languages and keys, passes a minute, which batching the cover read, weighed above, is the first cure for, or if the renderer comes to write a clip, a mask or another transform round a text.
