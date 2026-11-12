---
id: DEC-027
title: Where asked, the viewing step also draws an HTML page as a reader who forces their own colours sees it
status: accepted
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where its caller asks, the viewing step also draws the HTML renderer's pages as a reader who forces their own colours sees them. The browser draws each page file in its own two forced palettes: dark text on light, and light text on dark. Each forced palette shows the mode a browser gives with it, so the dark one shows a file's dark mode where it holds one. A second start of the browser draws them, under the browser's own flag that forces its colours. Its emulation alone forces the text in some browsers and leaves it in the file's colours in others, so it never stands in: only the flag forces the colours the same way in every browser the step reached. That start's first read checks that the forced palette reached the text. The forced images lie apart, and the report names each one's forced palette. Nothing is drawn under forced colours unasked, and the SVG renderer's pages never are.

## Context

[project-kit#2847](https://github.com/aleskalfas/project-kit/issues/2847) asks whether the viewing step draws under forced colours, and how. Forced colours name no mode, so the step draws none of them ([visual-communication:DEC-023-html-page-modes], its two terms). Yet that record's point 7 gives a page's shapes the reader's colours under forced colours. And the step leaves a reader's own settings to a person in a browser ([visual-communication:DEC-020-html-page-drawing] point 5). So a check of a page under forced colours took a wrapper of the step, with a browser flag of its own ([project-kit#2843](https://github.com/aleskalfas/project-kit/issues/2843)).

Two terms:
- A *forced palette* is the set of colours a browser gives a page under forced colours, in place of the page's own. CSS names them as system colours, such as `Canvas` for a ground and `CanvasText` for a text. It is no palette of a brand's, which is a mode ([visual-communication:DEC-004-brands-and-notations] point 2).
- The *light forced palette* gives dark text on a light ground, and the *dark forced palette* the reverse.

### What the test showed

The test ran in Chrome 157, on one Mac set to dark. It read the showcase deck's first page, in a file of a light mode and a dark one, and the first read's planted page ([visual-communication:DEC-020-html-page-drawing] point 7). Its code is thrown away.

| Started | Set by emulation | What the image showed |
|---|---|---|
| As the step starts it | `forced-colors: active` | The file's rule gave the shapes the forced palette. Each text kept the file's own colour, a green head among them |
| With `--force-high-contrast` | `forced-colors` not set | Text and shapes took a dark forced palette, white on `#121212`, whichever scheme was set |
| The same | `forced-colors: active`, and a scheme | Text and shapes took the scheme's forced palette: black on white for light, and white on black for dark |
| The same | `forced-colors: none` | The shapes took the file's colours, and each text drew as a blank strip |

- **The emulation alone draws a page no reader gets:** its shapes forced, and its text not. The wrapper's builder found the same.
- **Under the flag,** `prefers-contrast: more` matched wherever emulation did not set it.
- **One start held both forced palettes.** A change between them repainted the page with no reload, and a change back gave the same bytes.
- **Files of one scheme.** Two copies of the deck's file, its dark rule taken out, named no scheme and the dark scheme alone. Each took either forced palette by the scheme set.
- **The planted page under the flag.** The four reads named every planted fault but the three spans with no paint. The forced palette painted those spans, as a reader's would. The step's own first read stopped: a scheme set without `forced-colors` repainted nothing.
- **The planted page, some of it kept out of forcing.** Its mode boxes and its spans with no paint were kept out, and every emulation set `forced-colors: active`. Each box then repainted by its own signal alone, scheme and contrast alike. The four reads named every planted fault, in both forced palettes.
- **What each forced palette held.** The browser gave each the ground and the text colour its name says. Both grounds of the ink read took the forced palette's own.
- **What it costs.** The step drew the deck's four pages, in one language and both modes, in 29 s. A forced start of that file draws as many images.

**Not reached:** a Mac set to light, Linux, and the Chromium builds a project may name. A real forced palette on Windows, and Firefox's own. A browser that reports its scheme apart from its forced palette. A file the renderer wrote with a contrast mode, a picture, or a translucent fill over a text.

**Reached since, without the flag:** Chrome for Testing 149 and 154 on a Mac, and Google Chrome 156 on Linux, force the text under the emulation alone, so the first read passes there, as point 4 decides. Chrome 157 does not.

## Decision

**Where its caller asks, the viewing step draws each page file it reads of the HTML renderer in the browser's two forced palettes too. A second start draws them, under the browser's flag that forces its colours, each forced palette set by emulation. Each shows the key the file holds for the signals a browser sets with it. The forced images lie apart, and the report names each one's forced palette.**

### 1. Only where asked, and only where the tool can force a palette

- **The caller asks** with a flag of the command. Without it, the step draws nothing under forced colours.
- **It adds images, and replaces none.** The run draws each key it picks as it would, and its page files under forced colours as well. A run replaces its folder ([visual-communication:DEC-015-viewing-step-and-reviewer] point 4), so both kinds of image lie in it.
- **Where the tool can force a palette.** Today that is the browser, for the HTML renderer's pages. resvg knows no forced colours, so a run through the SVG renderer that asks for them is refused, its folder as it was. Where a piece goes through the SVG renderer by default, the refusal names the HTML renderer as the way on.
- **The caller names no program and no browser flag.** The flag is the browser's module's own, so a caller still names no browser (DEC-020 point 7). It neither weakens the browser's sandbox nor lets a page read past its file ([visual-communication:DEC-024-outside-programs-sandbox] point 1).
- **Nothing reaches the seam.** The key each forced palette shows is read from the signal pairs the renderer's declaration already holds. So no field is added, and neither the seam's version nor the renderer's rises ([visual-communication:DEC-005-engine-and-plugins] points 8 and 9).

### 2. Which forced palettes, and which key each shows

- **Each page file in both,** the browser's light forced palette and its dark one. The step sets them, so the machine's own setting plays no part, as with a mode (DEC-023 point 6).
- **A forced palette sets the signals a browser sets with it.** These are the scheme of its darkness, as the emulation pairs them, and `prefers-contrast: more`, as the flag reported (Context).
- **The browser's module names each forced palette's signals,** since they are facts of the browser. The step reads from the declaration's signal pairs which key the file holds for them, so the module still knows no axis (DEC-023 point 6).
- **That key names the image.** In a file of a light and a dark mode, the light forced palette shows the light mode, and the dark one the dark mode. A file of one scheme shows its key in both.
- **So the caller's keys pick no forced palette.** They pick the page files, each at its size, and each file takes both. The `html` format reads only the signals a forced palette sets (DEC-023 point 5).

### 3. A start of its own, after the file's first

- **A second start of each page file draws its forced images,** after the start that draws its keys. Under the flag, a page drawn without forced colours is no page a reader gets (Context). So no start mixes the two.
- **By the flag, and by emulation.** The start passes the browser its flag that forces its colours. Every emulation in it sets `forced-colors: active` with the forced palette's signals.
- **The emulation never stands in for the flag,** since alone it forces the text in some browsers and not in others: Chrome 157 leaves the text in the file's colours (Context). Only the flag forces the colours the same way in every browser the step reached.
- **As the first start in all else:** one open of the file with no reload, at the same device scale and bounds (DEC-020 points 5 and 8). Its sandbox is any start's (DEC-024).
- **The browser's module owns both starts,** as it owns the one (DEC-020 point 9).

### 4. Its first read checks that the forced palette reached the text

- **The same planted page, its checks unchanged.** Its mode boxes and its spans with no paint are kept out of forcing. So the reads name every planted fault, as in the first start (DEC-020 point 7).
- **Each signal by its own box.** A change of scheme repaints the whole page under the flag, so the check that each signal repaints judges each by its own mode box.
- **One more span with no paint, left to forcing,** must show ink in each forced palette. Where it shows none, the forced palette did not reach the text, so the run stops.
- **Each forced palette is what its name says:** its ground lighter than its text in the light one, and darker in the dark, as the browser gives them. Otherwise the run stops.
- **A stop of this start stops the run,** with no image, as any start's stop does (DEC-020 point 8). Beside the ways on that point names, it names a run without forced colours.
- **The four reads run in each forced image,** as in each key drawn (DEC-023 point 6). Under a forced palette every text takes its text colour. So the ink read names what that palette's reader loses: a span off its page, or one that drew nothing.

### 5. How the images and the report name the forced palette

- **A folder for each forced palette,** inside the renderer's folder for the piece, under a name no image takes. Its images and frames take the names any image takes, by the key they show. So no forced image takes the name of a mode's image.
- **The report names the forced palette in a field of its own,** in each image and in each entry that lies on one. An image under no forced palette leaves it empty. So no reader parses a path to tell the two apart.
- **What drew them.** The report names the forced palettes drawn, and that the browser's flag forced them, beside the browser and its version (DEC-015 point 3). It says what the forced images do not show (point 6).
- **The ground.** A page with no ground of its own lies on its forced palette's ground, as it lies on the browser's own ground in a mode (DEC-015 point 5). The report says so, as it says where one lies on the browser's.
- **The command prints them apart,** naming the forced palette wherever it names a forced image.

### 6. What a forced image shows, and what it does not

- **It shows the browser's forced palette,** not a reader's own, which may hold other colours, such as a link's. It stands for that browser alone, as any image of the step does (DEC-015 point 6).
- **It shows no other pairing of forced palette and signals.** A reader whose browser reports its scheme apart from its forced palette, or another contrast, meets one the step does not draw.
- **That is a choice.** The flag alone gave one forced palette whichever scheme was set, so an image of such a pairing would hang on the machine (Context).
- **What it is evidence of.** A forced image shows what that palette's reader loses: a part missing or blank, or a text or a line that fades over a translucent fill or a picture. Its colours are the browser's, so no finding on it rests on a brand's colour, or sets it against the check.
- **The reviewer** names the forced palette in each finding on such an image, and the forced palettes it looked at in its report. Where a run through the HTML renderer drew none, it lists forced colours under what it did not see (DEC-015 point 7).

## Rationale

**Why only where asked.** A forced start draws as many images as the file's first start, with their reads (Context). So a run that asks takes about twice as long. Most runs check what forced colours leave as it is: the layout, the words and the fonts.

**Why the flag, and not the emulation alone.** In some browsers, such as Chrome 157, the emulation alone draws a state no reader gets, shapes forced and text not, and in others it forces both (Context). Either way, only the flag gives the same state in every browser the step reached. The emulation's image would read as forced colours, and mislead whoever judges it.

**Why the forced palette picks the key.** A browser sets a scheme and a contrast with its forced palette, as this one did. A key drawn in a forced palette that never shows it would show another key under its name.

**Why both forced palettes for every file.** A file's modes do not decide which forced palette its reader holds. A dark arrow on a page with no ground stayed faint under a dark one (DEC-020, its Context). DEC-023 point 7 mends the shapes, but a translucent fill or a picture may still fade, and only an image shows it.

**Why the reads run again.** Every image the step draws has its reads (DEC-015 point 3), and the flag puts the browser in a state no other start meets. Kept out of forcing, the planted page shows that every read holds there.

**Why the first read checks the text and the forced palette.** A browser's update could drop the flag, or leave the text unforced, as the emulation alone does in some browsers. Or the emulation could stop pairing a forced palette with its scheme. Forced images would then show what their names deny. Only a planted page shows that before anyone trusts them.

**Why a folder for each forced palette.** Its name after a key's could spell another key, since a brand names its axes and modes freely. A folder no image's name can take keeps every name as it stands.

### Alternatives considered

- **Forced colours as a mode, among the keys.** Rejected. They name no mode, and no brand gives them values (DEC-023, its two terms). A key would carry them into names that mean a combination of a brand's modes.
- **Every run draws under forced colours.** Rejected, for the cost above. A record that has a reviewer look at every page under forced colours can make it so.
- **A value for the flag: light, dark or both.** Left out. No caller needs one, and both forced palettes are what readers hold. It can come as a change of its own.
- **Each key the caller picks, in each forced palette.** Rejected. In a file of two schemes, the light key in the dark forced palette would show the dark key under the light key's name.
- **The flag's own forced palette alone.** Rejected. It gave one forced palette whichever scheme was set, so an image would hang on the machine.
- **The forced images in the first start.** Rejected. Under the flag, a drawing without forced colours shows each text as a blank strip (Context).
- **Only the ink read in the forced start.** Rejected. The flag puts the browser in a state no other start meets, so its words, fonts and requests are read there too.
- **The emulation alone, with a note in the report.** Rejected. An image of a state no reader gets misleads more than no image.
- **The forced palette's name after the key in an image's name.** Rejected, as the folder's reason says.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-015, point 1, "What it is".** It comes to add that where its tool can force a palette, the step draws each image under one forced palette or none. It defines a forced palette, and calls an image drawn under one a forced image.
  - **DEC-015, point 2, "Behind one module of its own".** It comes to add that the browser's module also takes whether to force the browser's colours, and names each forced palette's signals. A browser start that forces colours runs under the browser's own flag for it, and sets forced colours there by emulation, with each forced palette's signals.
  - **DEC-015, point 3, "What drew the page".** It comes to add that the report names the forced palettes drawn, and that the browser's flag forced them.
  - **DEC-015, point 5, "The caller picks".** It comes to add that the caller may also ask for each page file in the browser's two forced palettes. There each forced palette, not the caller, picks the key an image shows.
  - **DEC-015, point 5, "The ground".** It comes to add that an image under a forced palette lies on that palette's ground.
  - **DEC-015, point 6, "It shows one tool's drawing".** It comes to add that a forced image shows that browser's forced palette, not a reader's own.
  - **DEC-015, point 7, "Nothing unseen reads as clean".** It comes to add the forced palettes the reviewer looked at to what its report names. Where a run through the HTML renderer drew none, the report lists forced colours as not seen.
  - **DEC-015, point 7, "Its remit".** It comes to add that a forced image is evidence of what its palette's reader loses, and that no finding on it rests on a brand's colour.
  - **DEC-015, point 7, "Its findings".** It comes to add that a finding on a forced image names its forced palette.
  - **DEC-020, point 5, "It reads the page file as the renderer wrote it".** It comes to say that a file takes one start for each set of flags its images need. Its pages share one device scale in every start, and the browser's flag that forces its colours takes a start of its own.
  - **DEC-020, point 5, "What an image does not show".** It comes to say that a reader's own settings beyond the modes the file holds stay a person's, but for forced colours in the browser's two forced palettes where the step drew them.
  - **DEC-020, point 6, "Ink".** It comes to add that under a forced palette the browser paints both grounds in that palette's ground colour, and each span in the palette's text colour, so the read names what that palette's reader loses.
  - **DEC-020, point 7, "What may not".** It comes to add that a start that forces its colours reads the planted page as this record's point 4 says, each signal judged by its own box.
  - **DEC-020, point 8, "It names what is missing".** It comes to add that a stop of a start that forces its colours also names a run without forced colours, and that the run through the SVG renderer it names is one too.
  - **DEC-023, point 6, "Every key it draws, in the file's one start".** It comes to say "in the file's first start", as this record's point 3 names it. It comes to add that an image drawn in a forced palette is a forced image, and that forced images take a start of their own, as point 3 says.
  - **DEC-023, point 6, "Each read of the check for dropped text runs in each key drawn".** It comes to add: and in each forced palette drawn.
- **The Task that draws under forced colours** ([project-kit#2847](https://github.com/aleskalfas/project-kit/issues/2847)) builds these points. They are the flag, the second start and its first read, the folders, the report and what the command prints. Its tests need no browser, since the forced start's first read holds the real one. It checks on the showcase deck that each forced image gives text and shapes the forced palette (DEC-023 point 7).
  - **The pages it brings to them:** the reviewer's agent file, the viewing step's page and the command's entry. The viewing step's page names the folders, and says when a forced look is worth asking for, such as for a page with a translucent fill or a picture under a text.
  - **`pkit visual pages`** comes to name the forced palettes the tool can draw.
- **Before that Task closes,** a person draws the deck once on a Mac set to light. A forced palette that differs there reopens point 2.
- **The Task for the pipeline's drawings** (DEC-024, Implications) covers the flag and the folders where a project's pipeline asks for them. It draws in the forced palettes once on its Linux runner. Whether the pipeline where the capability is authored asks for them is that project's choice.
- **The Task for steps 2 and 3 of DEC-024 point 7** takes the forced start and its first read into what a look reads of a page, for the drawing tool. The flag stays the tool's own and fixed, so nothing a command passes it chooses what it runs.
- **Revisit this record:**
  - if a browser's update drops the flag, or leaves text unforced under it;
  - if a real forced palette on Windows meets a page otherwise than the emulation does;
  - if a format comes to read a signal a forced palette does not set (DEC-023 point 5);
  - if a reader's need calls for a forced palette of their own.
