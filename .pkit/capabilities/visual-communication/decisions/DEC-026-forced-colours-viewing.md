---
id: DEC-026
title: Where asked, the viewing step also draws an HTML page as a reader who forces their own colours sees it
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where its caller asks, the viewing step also draws the HTML renderer's pages as a reader who forces their own colours sees them. The browser draws each page file in its own two palettes: dark text on light, and light text on dark. Each palette shows the mode a browser gives with it, so the dark palette shows a file's dark mode where it holds one. A second start of the browser draws them, under the browser's own flag that forces its colours. Its emulation alone leaves text in the file's colours, so it never stands in. That start's first read checks that the palette reached the text. The forced images lie in a folder of their own for each palette, and the report names each one's palette. Nothing is drawn under forced colours unasked, and the SVG renderer's pages never are.

## Context

[project-kit#2847](https://github.com/aleskalfas/project-kit/issues/2847) asks whether the viewing step draws under forced colours, and how. Forced colours name no mode, so the step draws none of them ([visual-communication:DEC-023-html-page-modes], its two terms). Yet that record's point 7 gives a page's shapes the reader's colours under forced colours. And the step leaves a reader's own settings to a person in a browser ([visual-communication:DEC-020-html-page-drawing] point 5). So a check of a page under forced colours took a wrapper of the step, with a browser flag of its own ([project-kit#2843](https://github.com/aleskalfas/project-kit/issues/2843)).

Two terms:
- A *forced palette* is the set of colours a browser gives a page under forced colours, in place of the page's own. CSS names them as system colours, such as `Canvas` for a ground and `CanvasText` for a text.
- The *light palette* gives dark text on a light ground, and the *dark palette* the reverse.

### What the test showed

The test ran in Chrome 157, on one Mac set to dark. It read the showcase deck's first page, in a file of a light mode and a dark one, and the first read's planted page ([visual-communication:DEC-020-html-page-drawing] point 7). Its code is thrown away.

| Started | Set by emulation | What the image showed |
|---|---|---|
| As the step starts it | `forced-colors: active` | The file's rule gave the shapes the palette. Each text kept the file's own colour, a green head among them |
| With `--force-high-contrast` | `forced-colors` not set | Text and shapes took a dark palette, white on `#121212`, whichever scheme was set |
| The same | `forced-colors: active`, and a scheme | Text and shapes took the scheme's palette: black on white for light, and white on black for dark |
| The same | `forced-colors: none` | The shapes took the file's colours, and each text drew as a blank strip |

- **The emulation alone draws a page no reader gets:** its shapes forced, and its text not. The wrapper's builder found the same.
- **Under the flag,** `prefers-contrast: more` matched wherever emulation did not set it.
- **One start held both palettes.** A change between them repainted the page with no reload, and a change back gave the same bytes.
- **Files of one scheme.** Two copies of the deck's file, its dark rule taken out, named no scheme and the dark scheme alone. Each took either palette by the scheme set.
- **The planted page under the flag.** The four reads named every planted fault but the three spans with no paint. The palette painted those spans, as a reader's would. The step's own first read stopped: a scheme set without `forced-colors` repainted nothing.
- **The planted page as point 4 reads it.** Its mode boxes were kept out of forcing, and every emulation set `forced-colors: active`. Each signal then repainted a box, scheme and contrast alike. The browser gave each palette the ground and text colour its name says.
- **The ink read's two grounds** both took the palette's own ground under a palette.
- **What it costs.** The step drew the deck's four pages, in one language and both modes, in 29 s. A forced start of that file draws as many images.

**Not reached:** a Mac set to light, Linux, and the Chromium builds a project may name. A real forced palette on Windows, and Firefox's own. A browser that reports its scheme apart from its palette. A file the renderer wrote with a contrast mode, a picture, or a translucent fill over a text.

## Decision

**Where its caller asks, the viewing step draws each page file it reads of the HTML renderer on the browser's two forced palettes too. A second start draws them, under the browser's flag that forces its colours, each palette set by emulation. Each palette shows the key the file holds for the signals a browser sets with that palette. The forced images lie apart, and the report names each one's palette.**

### 1. Only where asked, and only through the HTML renderer

- **The caller asks** with a flag of the command. Without it, the step draws nothing under forced colours.
- **It adds images, and replaces none.** The run draws each key it picks as it would, and its page files under forced colours as well. A run replaces its folder ([visual-communication:DEC-015-viewing-step-and-reviewer] point 4), so both kinds of image lie in it.
- **The HTML renderer's pages alone.** resvg knows no forced colours, so a run through the SVG renderer that asks for them is refused, its folder as it was. Where a piece goes through the SVG renderer by default, the refusal names the HTML renderer as the way on.
- **The caller names no program and no browser flag.** The flag is the browser's module's own, so a caller still names no browser (DEC-020 point 7). It neither weakens the browser's sandbox nor lets a page read past its file ([visual-communication:DEC-024-outside-programs-sandbox] point 1).
- **A build pipeline's look** may ask for forced colours as any look does, as the project chooses (DEC-024 point 5).

### 2. Which palettes, and which key each shows

- **Each page file on both palettes,** the browser's light one and its dark one. The step sets the palette, so the machine's own setting plays no part, as with a mode (DEC-023 point 6).
- **A palette sets the signals a browser sets with it.** The step sets the scheme of the palette's darkness, as the emulation pairs them, and `prefers-contrast: more`, as the flag reported (Context).
- **The file shows the key it holds for those signals,** and that key names the image. In a file of a light and a dark mode, the light palette shows the light mode, and the dark palette the dark one. A file of one scheme shows its key on both.
- **Any other signal the file reads** is set as for each key the run picks.
- **So the caller's keys pick no palette.** They pick the page files, each at its size, and each file takes both palettes.

### 3. A start of its own, after the file's first

- **A second start of each page file draws its forced images,** after the start that draws its keys. Under the flag, a page drawn without forced colours is no page a reader gets (Context). So no start mixes the two.
- **By the flag, and by emulation.** The start passes the browser its flag that forces its colours. Every emulation in it sets `forced-colors: active` with the palette's signals.
- **The emulation never stands in for the flag,** since alone it leaves text in the file's colours.
- **As the first start in all else:** one open of the file with no reload, at the same device scale and bounds (DEC-020 points 5 and 8). Its sandbox is any start's (DEC-024).

### 4. Its first read checks that the palette reached the text

- **The same planted page,** its mode boxes kept out of forcing. So DEC-020 point 7's check that each signal repaints holds unchanged in this start.
- **In each palette, the reads name every planted fault but the spans with no paint,** and those show ink. A span with no paint left with no ink means the palette did not reach the text, so the run stops.
- **Each palette is what its name says:** its ground lighter than its text in the light palette, and darker in the dark, as the browser gives them. Otherwise the run stops.
- **A stop of this start stops the run,** with no image, as any start's stop does (DEC-020 point 8). Beside the ways on that point names, it names a run without forced colours.
- **The four reads run in each forced image,** as in each key drawn (DEC-023 point 6). Under a palette both grounds of the ink read are the palette's, and every text takes its text colour. So the ink read names what that palette's reader loses: a span off its page, or one that drew nothing.

### 5. How the images and the report name the palette

- **A folder for each palette,** `forced-light/` and `forced-dark/`, inside the renderer's folder for the piece. Its images and frames take the names any image takes, by the key they show. So no forced image takes the name of a mode's image.
- **The report names the palette in a field of its own,** in each image and in each entry that lies on one. An image under no palette leaves it empty. So no reader parses a path to tell the two apart.
- **The report names the palettes drawn,** and that the browser's flag forced them, beside the browser and its version (DEC-015 point 3). It says what the forced images do not show (point 6).
- **The ground.** A page with no ground of its own lies on its palette's ground. The report says so, as it says where one lies on the browser's (DEC-015 point 5).
- **The command prints them apart,** naming the palette wherever it names a forced image.

### 6. What a forced image shows, and what it does not

- **It shows the browser's palette,** not a reader's own, which may hold other colours, such as a link's. It stands for that browser alone, as any image of the step does (DEC-015 point 6).
- **It shows no other pairing of palette and signals.** A reader whose browser reports its scheme apart from its palette, or another contrast, meets one the step does not draw.
- **That is a choice.** The flag alone gave one palette whichever scheme was set, so an image of such a pairing would hang on the machine (Context).
- **The reviewer reads a forced image as any image.** Its findings on one name the palette, and its report names the palettes it looked at. Where a run through the HTML renderer drew none, it lists forced colours under what it did not see (DEC-015 point 7).

## Rationale

**Why only where asked.** A forced start draws as many images as the file's first start, with their reads (Context). So a run that asks takes about twice as long. Most runs check what forced colours leave as it is: the layout, the words and the fonts.

**Why the flag, and not the emulation alone.** The emulation alone draws a state no reader gets, shapes forced and text not (Context). Its image would read as forced colours, and mislead whoever judges it.

**Why the palette picks the key.** A browser sets a scheme and a contrast with its palette, as this one did. A key drawn on a palette that never shows it would show another key under its name.

**Why both palettes for every file.** A file's modes do not decide which palette its reader holds. A dark arrow on a page with no ground stayed faint under a dark palette (DEC-020, its Context). DEC-023 point 7 mends the shapes, but a translucent fill or a picture may still fade, and only an image shows it.

**Why the reads run again.** Every image the step draws has its reads (DEC-015 point 3), and the flag puts the browser in a state no other start meets. The planted page shows that the reads hold there, but for the ink the palette gives.

**Why the first read checks the text and the palette.** A browser's update could drop the flag, or leave the text unforced, as the emulation does. Or the emulation could stop pairing a palette with its scheme. Forced images would then show what their names deny. Only a planted page shows that before anyone trusts them.

**Why a folder for each palette.** A palette's name after a key could spell another key, since a brand names its axes and modes freely. A folder no image's name can take keeps every name as it stands.

### Alternatives considered

- **Forced colours as a mode, among the keys.** Rejected. They name no mode, and no brand gives them values (DEC-023, its two terms). A key would carry them into names that mean a combination of a brand's modes.
- **Every run draws under forced colours.** Rejected, for the cost above. A record that has a reviewer look at every page under forced colours can make it so.
- **A value for the flag: light, dark or both.** Left out. No caller needs one, and both palettes are what readers hold. It can come as a change of its own.
- **Each key the caller picks, on each palette.** Rejected. In a file of two schemes, the light key on the dark palette would show the dark key under the light key's name.
- **The flag's own palette alone.** Rejected. It gave one palette whichever scheme was set, so an image would hang on the machine.
- **The forced images in the first start.** Rejected. Under the flag, a drawing without forced colours shows each text as a blank strip (Context).
- **Only the ink read in the forced start.** Rejected. The flag puts the browser in a state no other start meets, so its words, fonts and requests are read there too.
- **The emulation alone, with a note in the report.** Rejected. An image of a state no reader gets misleads more than no image.
- **The palette's name after the key in an image's name.** Rejected, as the folder's reason says.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-015, point 1, "What it is".** It comes to add that an image of the HTML renderer's page may lie under a forced palette, as this record says.
  - **DEC-015, point 2, "Behind one module of its own".** It comes to add that the browser's module also takes the palettes to force, and forces them by the browser's flag.
  - **DEC-015, point 5, "The caller picks".** It comes to add that the caller may ask for the HTML renderer's page files under forced colours too, as this record's points 1 and 2 say.
  - **DEC-015, point 5, "The ground".** It comes to add that an image under a forced palette lies on that palette's ground.
  - **DEC-015, point 7, "Nothing unseen reads as clean".** It comes to add the palettes the reviewer looked at to what its report names. Where a run through the HTML renderer drew none, the report lists forced colours as not seen.
  - **DEC-020, point 5, "It reads the page file as the renderer wrote it".** It comes to say that each file takes one start, and a second where forced colours are asked, at the same scale.
  - **DEC-020, point 5, "What an image does not show".** It comes to say that a reader's own settings stay a person's, but for forced colours in the browser's two palettes where the step drew them.
  - **DEC-020, point 6, "Ink".** It comes to add that under a forced palette both grounds are the palette's, as this record's point 4 says.
  - **DEC-020, point 7, "What may not".** It comes to add that a start that forces its colours reads the planted page as this record's point 4 says.
  - **DEC-020, point 8, "It names what is missing".** It comes to add that a stop of a start that forces its colours also names a run without forced colours.
  - **DEC-023, point 6, "Every key it draws, in the file's one start".** It comes to add that forced images take a start of their own, as this record's point 3 says.
  - **DEC-023, point 6, "Each read of the check for dropped text runs in each key drawn".** It comes to add: and in each palette drawn.
- **The Task that draws under forced colours** ([project-kit#2847](https://github.com/aleskalfas/project-kit/issues/2847)) builds these points. They are the flag, the second start and its first read, the folders, the report and what the command prints. Its tests need no browser, since the forced start's first read holds the real one. It checks on the showcase deck that each forced image gives text and shapes the palette (DEC-023 point 7). It brings the reviewer's agent file and the viewing step's pages to it.
- **Before that Task closes,** a person draws the deck once on a Mac set to light. A palette that differs there reopens point 2.
- **Revisit this record:**
  - if a browser's update drops the flag, or leaves text unforced under it;
  - if a real forced palette on Windows meets a page otherwise than the emulation does;
  - if a reader's need calls for a palette of their own.
