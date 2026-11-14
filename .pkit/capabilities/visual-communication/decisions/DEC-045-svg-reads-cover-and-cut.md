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

Probes drew a page of the SVG renderer through the tool's module, resvg 0.48.1 in `resvg-py` 0.5.0, on one Mac, in one face (Source Sans Pro Regular). Each set a text at an em in image pixels and drew it at five scales: 0.5, 1, 1.225 and 2, which are DEC-037's, and 0.8167, at which a 1920 by 1080 page is drawn 1568 pixels wide (DEC-015 point 5). Their code is thrown away.

- **A graze.** A later box's top edge stepped an eighth of an image pixel across the foot of the descenders of "Typography gypsy". resvg hides a pixel only where the box wholly covers it, so the loss came in whole rows: at an em of 40 the smallest row lost 6 to 16 pixels, 0.004 to 0.010 em², and the next 54 to 72. At an em of 24 the smallest lost 0.031 to 0.061 em², at 17 0.048 to 0.097 and at 10 0.12 to 0.14.
- **A háček.** A later box over the háček of a ž, set at 10, 12 and 16 image pixels: it lost 2 to 3 pixels at 10, 0.020 to 0.030 em², 2 to 3 at 12, 0.014 to 0.021, and 5 to 6 at 16, 0.020 to 0.023. The text floor is 10 pixels (DEC-015 point 5), where one pixel is 0.01 em².
- **Phase.** Moving the text by an eighth of a pixel changed no háček's loss.

DEC-037's 0.01 does not hold on these. The graze of the control at 40, which is to stay unnamed, reached 0.0100 at a scale of 1.225, as much as that sliver, so it sits on the threshold. A háček at the floor loses as little as 2 pixels, 0.02 em². Not probed: another face, a picture under a text, another machine, an alpha under a part's fill.

## Decision

**Through resvg, the tool's module names each span that another part covers or the page's edge cuts, in one entry for each cause with the share of its strong ink lost, found in what resvg drew.**

### 1. How it is measured

- **Strong ink, in a draw of its own.** A span is drawn alone, as the check for ink draws it, its letters opaque black on the white ground, with no other span of its text. A pixel is strong where it lies nearer black than white, so a letter's strength is its shape's, whatever the alpha of its paint.
- **Room past the page.** The band that holds the span reaches a page's width past each of the page's sides, and two of the span's largest font sizes either way of its baseline, past the page's top and foot too. A page's frame clips nothing in this draw. A text that runs further than the band counts as far as the band holds, so its share is of the ink inside it, and it is cut all the same. The band is first drawn with room for two font sizes, and drawn again at a page's width where it shows no strong ink or the ink comes within a font size of its side. The draw's cost grows with its width.
- **Cut and covered.** Strong ink past the page's edge is cut. For cover the page is drawn whole twice on the span's ink, its letters black and then white, all else as it stands, and strong ink on the page that the two draws show alike is covered. A span with strong ink on the page is cut or covered, or neither. A span with none on the page, all of it past an edge, is off the page (point 2).
- **The sliver is resvg's.** A cause hiding less than 0.0125 of the span's em squared, in image pixels, and never a single pixel, names no entry, and each cause is judged alone. It lies between what the probes showed: above the most a graze of the control lost at 40, 0.0100, and below the least a háček at the text floor lost, 0.020, with room at both ends. At the floor it is 1.25 pixels, under the pixel and a half the second bound sets, so two pixels name an entry and one does not. Where an em is under 11 pixels, as on a page too wide for its smallest text to read, the sliver comes under that bound, which holds a single pixel unnamed.
- **What stands round a text.** The reads draw a span alone at its place, so they follow a group's move and nothing else. The renderer writes round a text groups that hold the page's marks, `data-id`, `data-component` and `data-version`, and a `translate` as their move, and no clip, mask, opacity, filter or other transform. The tool fails a page whose group carries any other attribute or transform, naming the group, rather than read ink a clip hides as a cover. A test draws the renderer's groups and finds no other.
- **No pre-filter.** SVG paints in document order, so the parts drawn after a span are known exactly, which a pre-filter for the cover read would use. It is not built: it needs a box for every later part, and a part's box means reading the whole of the path data the renderer writes, arcs and relative moves among it. The cover draw is cropped to the span's ink, which cut a draw from 1.06 s to about 0.1 s. The reads may draw many spans at once where their bands do not meet.

### 2. Entries and report

- **An entry of `dropped`,** as DEC-037 point 2 sets it: the element, the characters, `why`, and for `cut` and `covered` `share`. Every entry names one cause in `why`.
- **The tool's own drops take a cause.** A text or run resvg drew nothing of is `no ink`, or `off the page` where the span has no strong ink on the page, all of it past an edge. The entry keeps `whole`, true for a whole text and false for a run lost from a line, so a reader of it is unchanged. A span past an edge with any strong ink on the page is cut, so a text 100% past the edge is off the page and one 99% past is cut with a share of 0.99: one fault takes one cause, by how much of it lies on the page. The strong ink is read for each span before the drawing of its own paint, so a span wholly past an edge reaches it.
- **A text whose runs left for two causes** gives an entry for each run, with `whole` false.
- **`dropped-not-read` goes,** with the command's line that said it. A reader of the key breaks. It came with #3088's change, which no release holds yet, so no released reader does. The readers in the repository are the reviewer's agent file, the `visual-author` skill's build loop and the command's own print, all edited in this change.

### 3. What stays as it was

- **What the reviewer reads** is DEC-037 point 4's.
- **A finding at validation, from the engine's own measure, for a cut text,** is not taken. On the SVG renderer's own terms the step judges what resvg drew (DEC-015), and the engine's frames know neither resvg's shaping nor what a later shape hides. In its strongest form, a finding at validation first and the read at the look as its backstop, it would name one cut text twice and cover not at all, and the read at the look stays the one place a text is named.

## Rationale

**Why the same two draws.** DEC-037's reasons for a draw alone and a change between two colours hold for resvg: the scene knows no cover, and changing one span's letters shows where the page lets them through, whatever their own colour. Others do not: resvg has no backplates, no forced palette and no z-index, so the document's order tells the painting order whole, and what hides a span is a later part's fill, its opacity, or a picture's alpha.

**Why room in the document the tool is given.** The page's frame clips a cut text away, so a read of the page as drawn finds a cut text whole or none of it. A band that reaches past the page holds the ink to count. The `_drew` draw of the tool's own drops has no room past the page, which is why a text wholly off it left no ink there and is told from a text with no ink by the read that has room.

**Why one `why` for every entry.** DEC-037 point 2 has each entry give one cause in `why` because its readers parse that as one string. An entry without one would break that for the SVG renderer's report alone. Every entry names one, so a reader sorts them by cause as through a browser, and `whole` stays for a reader that wants the text or run.

**Why the sliver is resvg's own.** A browser smooths a box's edge over the pixels it touches, and DEC-037 set its number between that graze and a háček's loss. resvg's graze comes in whole rows, which at an em of 40 reach as far as the sliver. The two numbers lie in the same pixels at the text floor, so they are set apart by probing resvg.

**The cost, accepted.** Measured on the same Mac, loaded, on one look of the showcase deck, 104 spans, in one language and one key: 12.3 s without these reads and 32.9 s with them. The cut read took 9.2 s, 0.09 s a span, and the cover read 11.9 s, 0.06 s for each of its 208 draws, 0.11 s a span. The look of the other piece, 60 spans: 7.7 s and 17.2 s. A look at every language and key of the deck took 105 s of CPU for four looks, 26 s each, and 4.8 minutes with the machine loaded. On the CI's runner, 1.04 to 1.28 times that Mac's time (DEC-037), a look of the deck takes 34 to 42 s, under the minute DEC-037 sets. So the cost is accepted as the price of a report that names every lost text, and the build loop keeps its pace. The repository holds one deck. Before the cover read was cropped to the span's ink, one look of the deck took 4.4 minutes.

### Alternatives considered

- **Keeping the notice:** a clean list would stay unreadable as clean, though a read now stands behind it.
- **DEC-037's sliver:** it sits on the control's graze at one scale, so the read would name a text that shows.
- **The page drawn once with the frame cleared:** it shows a cut text but never what covers one.
- **A pre-filter by the later parts' boxes:** point 1.
- **A group's clip or transform followed by the reads:** the renderer writes neither, so the code to follow them would have nothing to run on.

## Implications

- **Edits to accepted records,** made in this record's change and accepted with it, each citing it (COR-066 point 5). The first overturns one bullet of DEC-037 in part, and each of the others refines its record in place.
  - **DEC-037's top line** reads *Partially superseded by* this record, as [visual-communication:DEC-003-change-over-time] shapes it. Overturned: point 1's last bullet and the Rationale's "Why the SVG renderer waits", and what the Alternatives, the Implications and the Revisit say of that report and of the SVG renderer's read.
  - **DEC-037 point 1, "Through a browser".** It comes to say that through the SVG renderer `dropped` names a cut or covered span too, as this record sets. Its Rationale's "Why the SVG renderer waited" says so. Its Alternatives' two lines on a finding at validation and on the SVG renderer in the same change, its Implications' sentence on the reviewer's report and its line on DEC-015's summary, and its Revisit's last clause each say what stands.
  - **DEC-015's summary, its Decision's sentence and point 3's heading.** "Through a browser" comes out, so that no text the page does not show passes in silence, whether the tool drew it to nothing or the page hides or cuts it.
  - **DEC-015 point 3, "Each text, or run of a text, the tool dropped".** Its last sentence comes to say that through resvg too it names each text the page shows in part, in one entry for each cause with its share.
- **The capability's page on outputs** comes to say what `dropped` holds through the SVG renderer, with `why` on each entry, and the sliver's number and its floor. **The graphic-design reviewer's agent file** and **the `visual-author` skill's build loop** come to say it, and that `dropped-not-read` is gone. All three in #3111's change.
- **#3111** builds points 1 and 2, with a test that draws a page with each loss through SVG and finds it in the report, a test of the sliver's two sides at the scales above, and a test of the groups. In the repository the capability is authored in, its changeset is `minor` for visual-communication.
- **Revisit this record** if the sliver names a text resvg shows or misses a mark a reader needs, if in the CI of the repository the capability is authored in a look of one of that repository's pieces, divided by its languages and keys, passes a minute, or if the renderer comes to write a clip, a mask or another transform round a text.
