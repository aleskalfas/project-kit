---
id: DEC-026
title: Where asked, the viewing step draws an HTML page under forced colours, in a browser start of its own
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where its caller asks, the viewing step also draws the HTML renderer's pages as a reader who forces their own colours sees them. The browser draws them in its own two palettes: dark text on light, and light text on dark. Each key takes each palette under which the page shows a reader that key. A second start of the browser draws them, forced by its own switch, since its emulation leaves text in the file's colours. That start's first read checks that the palette reached the text. The images, their frames and the report name the palette, so no one takes such an image for a mode's. Nothing is drawn under forced colours unasked, and the SVG renderer's pages never are.

## Context

[project-kit#2847](https://github.com/aleskalfas/project-kit/issues/2847) asks whether the viewing step draws under forced colours, and how. Forced colours name no mode, so the step draws none of them ([visual-communication:DEC-023-html-page-modes], its two terms). Yet that record's point 7 gives a page's shapes the reader's colours under forced colours. And the step leaves a reader's own settings to a person in a browser ([visual-communication:DEC-020-html-page-drawing] point 5). So a check of a page under forced colours took a wrapper of the step, with a switch of its own ([project-kit#2843](https://github.com/aleskalfas/project-kit/issues/2843)).

Two terms:
- A *forced palette* is the set of colours a browser gives a page under forced colours, in place of the page's own. CSS names them as system colours, such as `Canvas` for a ground and `CanvasText` for a text.
- The *light palette* gives dark text on a light ground, and the *dark palette* the reverse.

### What the test showed

The test ran in Chrome 157, on one Mac set to dark. It read the showcase deck's first page, in a file of a light key and a dark one. It read the first read's planted page too ([visual-communication:DEC-020-html-page-drawing] point 7). Its code is thrown away.

| Started | Set by emulation | What the image showed |
|---|---|---|
| As the step starts it | `forced-colors: active` | The file's rule gave the shapes the palette. Each text kept the file's own colour, a green head among them |
| With `--force-high-contrast` | No forced colours | Text and shapes took a dark palette, white on `#121212`, whichever scheme was set |
| The same | `forced-colors: active`, and a scheme | Text and shapes took the scheme's palette: black on white for light, and white on black for dark |
| The same | `forced-colors: none` | The shapes took the file's colours, and each text drew as a blank strip |

- **The emulation alone draws a page no reader gets:** its shapes forced, and its text not. The wrapper's builder found the same.
- **One start held both palettes.** A switch between them repainted the page with no reload, and a switch back gave the same bytes.
- **The planted page under the switch.** The four reads named every planted fault but the three spans with no paint. The palette painted those spans, as a reader's would. The first read, as the step reads it, stopped there: a scheme set alone repainted nothing.
- **Under the switch,** `prefers-contrast: more` matched wherever it was not set by emulation.

**Not reached:** a Mac set to light, Linux, and the Chromium builds a project may name. A real forced palette on Windows, and Firefox's own. A palette whose darkness differs from the scheme a browser reports. A page with a picture, or a translucent fill over a text.

## Decision

**Where its caller asks, the viewing step draws each key it picks of the HTML renderer's pages under forced colours too. A second start of the browser draws them, forced by the browser's own switch, each palette set by emulation. A key takes each palette under which the file shows it. Every image, frame and report entry under forced colours names its palette.**

### 1. Only where asked, and only through the HTML renderer

- **The caller asks** with a flag of the command. Without it, the step draws nothing under forced colours.
- **The flag adds images, and replaces none.** The run draws each key it picks as it would, and under forced colours as well. A run replaces its folder ([visual-communication:DEC-015-viewing-step-and-reviewer] point 4), so both kinds of image lie in one folder.
- **The HTML renderer's pages alone.** resvg knows no forced colours, so a run through the SVG renderer that asks for them is refused, its folder as it was.
- **The caller names no program and no switch.** The switch is the browser's module's own, so a caller still names no browser in a flag (DEC-020 point 7).

### 2. Which palettes a key is drawn on

- **The browser's two palettes, light and dark.** The step sets the palette, so the machine's own setting plays no part, as with a mode (DEC-023 point 6).
- **A key takes each palette under which the file shows it.** The step sets each palette with the scheme of its darkness, as the emulation pairs them (Context).
- **In a file that switches between light and dark,** the light key takes the light palette, and the dark key the dark one.
- **A file that does not switch** shows its keys under either scheme, so each key takes both palettes. DEC-023's test found its fault there: a light file's dark arrow on a dark palette.
- **The other signals are the key's,** set as for any image of it.

### 3. A start of its own, after the file's first

- **A second start of each page file draws its forced images,** after the start that draws its keys. Under the switch, a page drawn without forced colours is no page a reader gets (Context). So no start mixes the two.
- **By the switch, and by emulation.** The start passes the browser the switch that forces its palette. Each image then emulates `forced-colors: active`, its palette's scheme and the key's other signals.
- **The emulation never stands in for the switch,** since it leaves text in the file's colours.
- **As the first start in all else:** one open of the file with no reload, at the same device scale, under the same bounds (DEC-020 points 5 and 8). Its sandbox is any start's ([visual-communication:DEC-024-outside-programs-sandbox]).

### 4. Its first read checks that the palette reached the text

- **The same planted page,** read in each palette (DEC-020 point 7). The reads must name every planted fault but the spans with no paint, and those must show ink.
- **A span with no paint left with no ink** means the palette did not reach the text, so the run stops.
- **A switch of palette must repaint the planted page,** or the run stops, as a signal that does not repaint stops the start before it.
- **A stop of this start stops the run,** with no image, as any start's stop does (DEC-020 point 8). The way on it names adds a run without forced colours.
- **The four reads run in each forced image,** as in each key drawn (DEC-023 point 6). Under a palette a span with no paint has ink, so the ink read names what that palette's reader loses.

### 5. How the images and the report name the palette

- **An image and its frames add the palette after the key,** as `forced-light` or `forced-dark`, before a page's number. So `<piece>.<language>.<key>.forced-dark.png` lies beside `<piece>.<language>.<key>.png`, and never takes its name.
- **The report names the palette in a field of its own,** in each image and in each entry that lies on one. An image under no palette leaves it empty. So no reader parses a name to tell the two apart.
- **The report names the palettes drawn,** and that the browser's switch forced them, beside the browser and its version (DEC-015 point 3).
- **The ground.** A page with no ground of its own lies on its palette's ground, and the report says so, as it says where it lies on the browser's (DEC-015 point 5).
- **The command prints them apart,** naming the palette wherever it names a forced image.

### 6. What a forced image shows, and what it does not

- **It shows the browser's palette,** not a reader's own, which may hold other colours, such as a link's. It stands for that browser alone, as any image of the step does (DEC-015 point 6).
- **It never shows a palette whose darkness differs from the scheme** in a file that switches on the scheme. The emulation pairs them, and the switch alone gave one palette whichever scheme was set.
- **The reviewer reads a forced image as any image.** Its findings on one name the palette, and its report names the palettes it looked at. Where a run drew none, it lists forced colours under what it did not see (DEC-015 point 7).

## Rationale

**Why only where asked.** A forced image costs a second start and the four reads again. So a run that asks takes about twice as long, or more where a key takes both palettes. Most runs check what forced colours leave as it is: the layout, the words and the fonts.

**Why the switch, and not the emulation alone.** The emulation alone draws a state no reader gets, shapes forced and text not (Context). Its image would read as forced colours, and mislead whoever judges it.

**Why a key takes only the palettes under which the file shows it.** The emulation sets the palette and the scheme together. In a file that switches, a light key on the dark palette would show the dark key under the light key's name.

**Why both palettes in a file that does not switch.** Its readers meet it on either. DEC-023's test found its faults there, and that record's point 7 mends only the shapes. A translucent fill or a picture may still fade, and only an image shows it.

**Why the reads run again.** A forced image with no read behind it would read as clean (DEC-015 point 3). The planted page shows that the reads hold under the switch, but for the ink the palette gives.

**Why the first read checks the text.** A browser's update could drop the switch, or leave the text unforced, as the emulation does. Forced images would then show the file's colours under a palette's name. Only a planted page shows that before anyone trusts them.

### Alternatives considered

- **Forced colours as a mode, among the keys.** Rejected. They name no mode, and no brand gives them values (DEC-023, its two terms). A key would carry them into names that mean a combination of a brand's modes.
- **Every run draws under forced colours.** Rejected, for the cost above. A record that has a reviewer look at every page under forced colours can make it so.
- **A value for the flag: light, dark or both.** Left out. The file decides which palettes a key meets, so a caller who picks one may leave a reader's palette unseen.
- **The switch's own palette alone.** Rejected. It gave one palette whichever scheme was set, so a light key's image would hang on the machine.
- **The forced images in the first start.** Rejected. Under the switch, a drawing without forced colours shows each text as a blank strip (Context).
- **The emulation alone, with a note in the report.** Rejected. An image of a state no reader gets misleads more than no image.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-015, point 1, "What it is".** It comes to add that the step may draw a page of the HTML renderer under a forced palette too, as this record says.
  - **DEC-015, point 2, "Behind one module of its own".** It comes to add that the browser's module also takes the palette to force, and forces it by the browser's switch.
  - **DEC-015, point 5, "The caller picks".** It comes to add that the caller may ask for the HTML renderer's pages under forced colours too, as this record's points 1 and 2 say.
  - **DEC-015, point 5, "The ground".** It comes to add that an image under forced colours lies on its palette's ground.
  - **DEC-015, point 7, "Nothing unseen reads as clean".** It comes to add the palettes the reviewer looked at to what its report names.
  - **DEC-020, point 5, "It reads the page file as the renderer wrote it".** It comes to say that each file takes one start, and a second where forced colours are asked, at the same scale.
  - **DEC-020, point 5, "What an image does not show".** It comes to say that a reader's own settings stay a person's, but forced colours in the browser's two palettes where the step drew them.
  - **DEC-020, point 7, "What may not".** It comes to add that a start that forces a palette reads the planted page as this record's point 4 says.
  - **DEC-023, point 6, "Every key it draws, in the file's one start".** It comes to add that forced images take a start of their own, as this record's point 3 says.
- **The Task that draws under forced colours** ([project-kit#2847](https://github.com/aleskalfas/project-kit/issues/2847)) builds these points: the flag, the second start and its first read, the names, the report and what the command prints. Its tests need no browser, but for the first read's. It checks on the showcase deck that each forced image gives text and shapes the palette (DEC-023 point 7). It brings the reviewer's agent file and the viewing step's pages to it.
- **Revisit this record** if a browser's update drops the switch or leaves text unforced under it, or if a real forced palette on Windows meets a page otherwise than the emulation does. Revisit it too if a reader's need calls for a palette of their own.
