---
id: DEC-045
title: Through the SVG renderer, the viewing step names a text another part covers, or the page's edge cuts, as dropped
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when the viewing step draws a page of the SVG renderer through resvg, its report lists in `dropped` each text the page does not show in full, as it does through a browser (DEC-037). A text the page's edge cuts, and a text a part drawn after it covers, each take one entry with the cause and the share of the text's strong ink the cause loses. The notice that cover and cut were not read goes. For example, where a later box covers the last words of a note, the report lists that note as covered, with its share.

## Context

[visual-communication:DEC-037-text-the-page-hides] has a browser's report name the texts a page hides, and leaves the SVG renderer's report to say that cover and cut were not read until [project-kit#3111](https://github.com/aleskalfas/project-kit/issues/3111) builds the read. Through resvg a cut text is gone for every reader, since the page's frame clips it, so a reader of the report has less to find it by than through a browser, where it spills past the page.

Terms are DEC-037's: a span's *strong ink*, a *sliver*, a text *cut* and *covered*. The tool's module draws a page whole, or one span alone, in a document it builds itself, so it can give its drawing room past the page and change one span's letters as the browser's module does.

**Not probed.** DEC-037's probes drew a page in Chrome. This record's build ran the tool's read on planted pages, a cut text, a covered text, both, a graze and a text neither cut nor covered, and measured no cost and no other device scale. Its sliver is DEC-037's, set from probes of a browser's drawing.

## Decision

**Through resvg, the tool's module names each span that another part covers or the page's edge cuts, in one entry for each cause with the share of its strong ink lost, found in what resvg drew.**

### 1. How it is measured

- **Strong ink, in a draw of its own.** A span that drew ink is drawn alone, as the check for ink draws it, its letters opaque black on the white ground, with no other span of its text and no text's ground. A pixel is strong where it lies nearer black than white. So a letter's strength is its shape's, whatever the alpha of its paint.
- **Room past the page.** The band that holds the span reaches a page's width past each of the page's sides, and two of the span's largest font sizes either way of its baseline, past the page's top and foot too. A page's frame clips nothing in this draw.
- **Cut.** Strong ink that lies past the page's edge.
- **Covered.** The page is drawn whole twice on the same band, the span's letters black and then white, all else as it stands. Strong ink on the page that the two draws show alike is covered.
- **The sliver is DEC-037's,** 0.01 of the span's em squared, both in image pixels. Each cause is judged alone, and a span both cut and covered gives two entries.
- **Cheaper ways stay open.** The read has no pre-filter, and may draw many spans at once, where their bands do not meet.

### 2. Entries and report

- **An entry of `dropped`,** as DEC-037 point 2 sets it: the element, the characters, `why`, `cut` or `covered`, and `share`.
- **The tool's own drops keep their shape.** A text or run resvg drew nothing of keeps `whole` and no `why`, as before. A text wholly off the page is such a drop here.
- **The report no longer says** that cover and cut were not read: `dropped-not-read` goes, with the command's line that said it.

### 3. What stays as it was

- **What the reviewer reads** is DEC-037 point 4's.
- **A finding at validation, from the engine's own measure, for a cut text,** is weighed and not decided here: it would put one fault in two lists, and it misses what a browser's widths push past an edge and reads no cover.

## Rationale

**Why the same two draws.** The scene knows no cover, and the engine's frames are blind to what a later shape hides. What resvg drew is the measure DEC-015 takes for the SVG renderer's pages. Changing one span's letters between two colours shows where the page lets them through, whatever their own colour, as DEC-037 gives for a browser.

**Why room in the document the tool is given.** The frame of a page clips a cut text away, so a read of the page as drawn finds a cut text whole or none of it. A band that reaches past the page holds the ink to count.

**Why no new entry shape.** Both renderers' `dropped` lists are read alike by the build loop and the reviewer, and one `why` and `share` serve both.

**Why the sliver is not probed again.** DEC-037 sets it from a browser's drawing of text and edges. resvg smooths edges its own way, so the number may need its own probe, which is the cost accepted here.

### Alternatives considered

- **Keeping the notice:** a clean list would stay unreadable as clean, though a read now stands behind it.
- **A finding at validation alone:** it reads no cover, and misses what a browser's widths push past an edge. Left to a record of its own if wanted.
- **The page drawn once with the frame cleared:** it shows a cut text but never what covers one.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-037 point 1, "Through a browser alone".** It comes to say that through the SVG renderer `dropped` names a cut or covered span too ([visual-communication:DEC-045-svg-reads-cover-and-cut]), its Rationale's "Why the SVG renderer waits" comes to say so, and the top line reads *Partially superseded by* this record, as DEC-003 shapes it.
  - **DEC-015 point 3, "Each text, or run of a text, the tool dropped".** Its last sentence comes to say that through resvg too it names each text the page shows in part, in one entry for each cause with its share.
- **The capability's page on outputs,** **the graphic-design reviewer's agent file** and **the `visual-author` skill's build loop** come to say it, in #3111's change.
- **#3111** builds points 1 and 2, with a test that draws a page with each loss through SVG and finds it in the report. In the repository the capability is authored in, its changeset is `minor` for visual-communication.
- **Revisit this record** if the sliver, set from a browser's probes, names a text resvg shows or misses a mark a reader needs, if a look through resvg comes to hold up a build loop, or if a finding at validation for a cut text is wanted.
