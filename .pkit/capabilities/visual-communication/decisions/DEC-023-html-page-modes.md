---
id: DEC-023
title: One HTML file holds a page's modes at its size, and follows the reader's system
status: accepted
date: 2026-11-06
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** for each language and size, one HTML file holds the modes a reader's system can name, and the page follows that system while it is open. It holds no control and no script, so a reader cannot pick a mode in the page. Each colour is a CSS custom property, and a mode is a set of their values at the file's own size. A switch changes colours, never the layout, and a window's width never changes the size. The viewing step sets a mode through the browser, and reads the real file. A page with no ground lies on the browser's own ground for that mode. Under forced colours its shapes take the reader's colours. A mode no system setting names takes a file of its own.

## Context

[project-kit#2738](https://github.com/aleskalfas/project-kit/issues/2738) asks how an HTML page holds the modes of the value axes, and how a reader switches them while it is open. A format whose medium switches modes holds them in one file ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7). The page's own form is settled, and this question is left open ([visual-communication:DEC-020-html-page-drawing] point 10). A page file holds one size, and how it takes its values at that size is this question's too ([visual-communication:DEC-021-size-and-shape] point 8). That point has the CSS writer write a brand's value axes at the default size alone.

Two terms:
- A *reader's signal* is a CSS media feature that names a mode a reader wants, such as `prefers-color-scheme`. A browser sets it from its reader's system or its own settings. `forced-colors` names no mode, so it is none.
- A *signal pair* joins a mode to the value of a signal that names it.

### What the test showed

A small page in DEC-020's form held four keys over the foundations' two value axes, at one size, on two pages, one with no ground. Each paint was a custom property. One arrowhead was defined once, and a translucent box lay over one text. The test ran on one Mac, set to dark, and its code is thrown away.

| Read | Chrome 157, Chromium 149, headless shell 149 | Firefox 148 as shipped | WebKit, in a web view never shown |
|---|---|---|---|
| A mode set from outside | All four keys in one start, by the browser protocol's emulation of the signals | Light and dark, by its own setting | Light and dark, by the view's appearance |
| A switch on the open page | Every paint repainted, the arrowhead and an alpha included, with no reload | The same | The same |
| The system's own dark mode | At load, the same pixels as the emulated mode, but the shell read light | Followed it | Not tried |
| The browser's ground in dark | `#121212` | `#1c1b22` | `#1e1e1e` |

- **A page with no ground.** With `color-scheme: light dark`, the dark mode's text had a contrast of 14.1 to 15.9 to 1 on those grounds. With none, Chrome kept a white ground under a dark system, and that contrast fell to 1.18 to 1. A file of dark alone, naming `dark`, kept the dark ground under a light reader in both Chromium builds.
- **Forced colours,** read in Chrome started forced, and in Firefox by its own setting. Each browser gave HTML text the reader's colours, and left the shapes alone. So a light file's dark arrow on the page with no ground had a contrast of 1.52 to 1 in Chrome, and 1.7 to 1 in Firefox, on dark palettes. Point 7's rule made that 18.7 and 21 to 1, on both pages and over an opaque fill. The same held for a dark file on Firefox's light palette. The text under the translucent box kept a contrast of 4.9 to 12.1 to 1.
- **An image in the page** held a rule on each signal, and a script. On a page that names both schemes, `prefers-color-scheme` reached it in all three. `prefers-contrast` reached it in Firefox and not in Chrome. The script ran in none.

**Not reached:** a real change of the system's setting on an open page. `prefers-contrast` from the system, alone in Firefox, and in WebKit at all. Forced colours in WebKit, and a real forced palette on Windows. Safari as an application, Linux, a phone. Printing in a dark mode. A file at a size other than the default, since no brand gives one yet. A page the renderer wrote: this one was written by hand.

## Decision

**A page file holds, for one language and one size, the modes a reader's signal names. Each is a set of values of CSS custom properties at that size. The browser picks among them from the reader's system. It holds no control and no script. The viewing step sets a mode through the browser. A mode no signal names takes a file of its own.**

### 1. A file holds the modes a signal names, and takes the first key it serves

- **What shares a file.** Combinations of modes share a file where they differ only in modes of the signal pairs its format reads (point 5). So a file serves one key over the size axes, called below the file's size. It serves one language too (DEC-020 point 4).
- **Any other mode** takes a file of its own in this format, drawn from the scene of the file's size.
- **Its name.** An export names it as it names any file, with the extension `.html` and no page number. Its key is the first it serves, in the order a picture's variant takes ([visual-communication:DEC-004-brands-and-notations] point 3). So a piece of light and dark takes the default key, and its file at the phone's size takes the key that names the phone alone. A piece of dark alone takes dark's.

### 2. A format that holds modes hands its renderer the keys in one call

- **One call for each set of keys that share a file.** The renderer is handed the format, the scene, those keys, and each key's colours and pictures. The keys share the scene's size, so their colours are that size's. What it gives back keeps its form. Any other format's renderer is handed one key at a time.
- **Its declaration names each such format,** with the signal pairs it reads. What hands the keys groups them by those pairs, read as data, and holds none of its own.
- **The seam's version rises once,** since this renderer must read something differently ([visual-communication:DEC-005-engine-and-plugins] point 8). The engine refuses a plugin on another version, so every declaration moves with it. No other renderer's output changes, so no other renderer's own version rises.

### 3. A paint is a custom property

- **One custom property for each colour role the file paints,** in the CSS writer's spelling. HTML text and the shapes of a layer read the same property.
- **A mode is a set of their values.** So text and shapes change together, an arrowhead defined once for a role serves every mode, and a colour's alpha lies in its value.
- **At the file's size.** Each mode's values are its key's, and that key's combination takes the file's size. So a colour a size changes takes that size's value in every mode of the file.
- **The renderer writes these rules itself,** for the keys the file holds and the roles it paints. It shares the writer's spelling, never its output (DEC-005 point 7).

### 4. The reader's system switches the page

- **The page picks a mode by a reader's signals, and nothing else.** A reader switches a mode where their system or browser sets it, and the open page repaints.
- **No control, and no script.** So a renderer adds nothing to the scene, and no words, reading order or focus order arise.
- **The plain rule is the first key's.** Each other key lies in a rule under the signals that part it from the first. A piece's keys are every combination of its modes (DEC-005 point 6), so a reader's signals always meet one key.
- **A switch moves no frame.** The keys a file holds share its size, and a value axis moves nothing (DEC-004 point 2). So one scene serves them all. A page keeps one variant of each picture (point 8), so a switch changes colours alone.

### 5. A renderer's declaration ties a mode to its signal

- **The tie lies in the declaration,** beside each format that holds modes, since a signal belongs to where a file is read. Computing a scene reads no pair, so a scene names no axis as light or dark.
- **What it pairs, settled here once,** since [project-kit#2700](https://github.com/aleskalfas/project-kit/issues/2700) asks the same of a published copy. `colour-scheme`'s `light` and `dark` pair with the same values of `prefers-color-scheme`. `contrast`'s `standard` and `high` pair with `prefers-contrast`'s `no-preference` and `more`.
- **A value axis alone.** Each combination of size-axis modes takes a scene and a file of its own. The size is the whole page's, so a rule on a window's width would put one size's colours on another's layout (DEC-021 points 6 and 8). The file holds none, and a narrow window shrinks the page (DEC-020 point 4).
- **Each format reads the pairs its medium reaches.** The `html` format reads each of these. A new pair is a new version of its renderer, after a test.
- **Not in the foundations.** They name no medium, so no library changes.

### 6. The step sets a mode through the browser

- **By the browser's emulation of a key's signals.** A file holds no switch for the step, so the step reads what a reader's browser reads. It takes a key's signals from the declaration, and hands them to the browser's module, which knows no axis.
- **Every key it draws, in the file's first start,** with no reload (DEC-020 point 5). A file holds every key point 1 gives it, whichever the caller picks. The step sets each signal the file reads, so the machine's light or dark plays no part. An image the browser draws in a *forced palette*, the colours a browser gives a page under forced colours, is a *forced image*. Forced images take a start of their own (refinement per [visual-communication:DEC-027-forced-colours-viewing] point 3).
- **Each read of the check for dropped text runs in each key drawn** (DEC-020 point 6), and in each forced palette drawn (refinement per [visual-communication:DEC-027-forced-colours-viewing]).
- **The first read holds this too.** Its small page holds a mode for each signal the file reads, and the run stops if setting one does not repaint it, since those keys would then read as one (DEC-020 point 7).

### 7. A page with no ground lies on the browser's own ground

- **The file names its schemes.** CSS's `color-scheme` names the scheme of each mode paired with `prefers-color-scheme`. The browser's ground then follows the mode, and the file sets no colour value around its pages (DEC-020 point 4). A keyline and a backdrop mix the browser's colours (refinement per [visual-communication:DEC-031-html-page-backdrop] point 3). In print each page lies on the browser's ground, and the file asks the browser to keep the colours of its pages and their keylines exactly, and nothing around them (refinement per [visual-communication:DEC-026-html-page-print] point 5).
- **No check reads that ground,** which differs between browsers. A file with no such mode names no scheme, so its page lies on the browser's default ground, white in the test. Only a person catches a light text that fades there.
- **Under forced colours,** one rule of the file gives each line, stroke and arrowhead the reader's text colour. A fill opaque in every key the file holds takes the reader's background colour, with an edge in that text colour. The browser colours the text itself. The backdrop and each fixed page take the reader's background colour, and the keyline the reader's text colour (refinement per [visual-communication:DEC-031-html-page-backdrop] point 3).
- **A translucent fill stays.** A line over it, or over a picture, may fade.
- **The renderer declares these choices,** the edge's width among them ([visual-communication:DEC-001-visual-communication-discipline] point 2). The colours are the reader's, so it adds none of its own.

### 8. A picture keeps one variant, and a loss names its mode

- **A picture** keeps the first key's variant, and each key whose variant differs reports a loss. No producer ships yet, so the change that ships the first ([project-kit#2575](https://github.com/aleskalfas/project-kit/issues/2575)) decides how a page holds every variant.
- **A renderer's loss in one mode of such a file names its key,** in a field no other loss carries. A role with no colour in one key draws nothing there, and reports that loss.

## Rationale

**Why the system's preference alone.** It meets a page that switches while open, with no words, no place and no focus stop, which a renderer may not add. Both shared value axes have a signal, though the system's contrast signal went unread (Context). The cost is that a reader cannot pick a mode in the page. A person who shows a deck shows that machine's mode. Naming one mode alone fixes that, and takes the other mode from the piece's PDF too.

**Why a media feature.** A control or a script cannot reach an image in a page, since an image runs no script. A media feature can, as far as the browser carries it (Context).

**Why a custom property, not rules that name a role.** A role paints text, fills and strokes alike, so rules would need a selector for each use in each mode. A property takes one declaration for each role in each mode. Arrowheads stay one for each role, not one for each colour.

**Why a file takes its own size's values.** A size axis may change any value, a colour included (DEC-004 point 2). A phone's file that took the default size's colours would show a colour wrong in every mode wherever a size changes it. The CSS writer keeps the default's because its one sheet has nothing to choose a size by. A page file is one size already, so its own size's values cost nothing.

**Why the step emulates, not an attribute on the root.** An attribute would write every rule twice, and the step would read a path no reader takes. Emulated and real dark gave the same pixels (Context).

**Why a mode with no signal takes a file of its own.** Held in a shared file, no reader could reach it. Refused, a brand's own palette could never reach a page. A file of its own keeps the mode, and loses only the switch to it.

**Why the first key names the file.** The records already hold that rule, so a key gains no new meaning. The cost is that a piece of dark alone that gains light changes its file's name, and a link to its copy may break.

### Alternatives considered

- **A control in the page, alone or beside the system's preference.** Rejected for now. It needs a script, words in each language, and a place in the page and its focus order, and the aim needs none of them. It can come back as a change of its own.
- **The page takes the CSS writer's style sheet.** Rejected. No plugin reads another plugin's output (DEC-005 point 7). The sheet would also hold the default size's values alone (DEC-021 point 8), and switches a mode by an attribute, which no reader's signal sets.
- **The page takes the default size's colours, and reports a loss for each a size changes, as the CSS writer does.** Rejected. A page file is one size already, so it would report a fault it need not have.
- **Every fill taking the reader's background colour under forced colours.** Rejected. A translucent shape over a text or a picture would turn opaque and hide it, and nothing would report that.
- **Only lines taking the reader's text colour.** Rejected. A line could land on a fill of its own colour, such as a page's ground, and vanish.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-006, point 3, "Every variant travels with the scene".** It comes to add that the HTML page keeps the first key's variant, with a loss in each other mode, until the change this record's point 8 names.
  - **DEC-006, point 7, "What a run makes".** Its last sentence comes to say that such a format holds in one file, for each language and each key over the size axes, the modes a reader's signal names. It adds that what becomes of any other mode is that format's own.
  - **DEC-005, point 9, "Each declares what it supports".** It comes to add that a renderer names each format that holds modes, with the signal pairs it reads.
  - **DEC-005, point 9, "One form of loss report".** It comes to add that a renderer's loss in one mode of such a file names its key.
  - **DEC-004, point 3, "A picture's variant takes the first key it serves".** A sentence ends the bullet: a file that holds several combinations takes its key the same way.
  - **[visual-communication:DEC-015-viewing-step-and-reviewer], point 2, "Behind one module of its own".** It comes to add that the browser's module also takes the signals to set.
  - **DEC-015, point 5, "The ground".** It comes to add that an image of the HTML renderer's page lies on the browser's own ground in that mode.
  - **DEC-020, point 4, "One file for each language".** It comes to say that a file holds the modes this record's point 1 gives it, at its size's values. "At one key until how a file holds its modes is settled" goes.
  - **DEC-020, point 4, "The pages follow each other down the document".** It comes to add that the file names its schemes, and gives its shapes the reader's colours under forced colours, as this record's point 7 says.
  - **DEC-020, point 7, "What may not".** It comes to add that the small page holds a mode for each signal the file reads, and that the run stops if setting one does not repaint it.
  - **DEC-020, point 10, "How a page holds its modes".** It comes to cite this record in place of the issue.
  - **DEC-021, point 8, "A page file holds one size".** It comes to say that the file takes its values at that key as this record's point 3 says, in place of naming the issue.
- **#2575's body** comes to name how a page holds every variant.
- **The Task that holds every mode in one file** builds these points in the renderer and the step. It builds point 1's grouping whole, so a mode with no pair never lies unreached in a shared file. Only a test reaches that, until a piece can name a value mode no signal names. A new mode or value axis of the foundations may bring one, as may a brand's own axis. A test holds each pair to what each shipped major of the foundations declares, the axis's kind included.
- **A test of a colour a size changes** lands with whichever comes second: the Task that holds every mode in one file, or the Task of the size axis (DEC-021, Implications). It holds a file at such a size to that size's colour in each mode.
- **The Task of the `html` format** names the file, and widens the name patterns that allow only `.svg` and `.pdf`.
- **The Task that draws the showcase deck** closes with a person's switch on an open page, in Safari and in Firefox, by the system's real setting.
- **#2700 and #2772** read point 5 again before they go on.
- **Revisit this record** if a person's look finds a signal that does not reach a reader, if what Context lists as not reached shows a fault, if the emulation stops matching a reader's dark mode, if a value axis comes to change a value other than a colour or a picture, or if a reader's need calls for a control.
