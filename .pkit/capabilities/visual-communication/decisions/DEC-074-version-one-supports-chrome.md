---
id: DEC-074
title: Version 1 of the capability supports one browser, Chrome
status: proposed
date: 2026-11-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** version 1 of the capability supports one browser, Chrome. What a browser draws of the capability's, the HTML page and an SVG figure a web page shows, is built for Chrome, checked in Chrome and looked at in Chrome. No work of version 1 tests it in Safari, Firefox or any other browser, and a fault only another browser shows is filed and waits. What is already built for another browser stays as it is, such as the lengths the HTML renderer writes for Firefox's print. Support for another browser comes in a later version, by a record of its own. For example, the person's look at the showcase deck's HTML page in Safari and in Firefox becomes a look in Chrome, and the looks in the other two wait for that record.

## Context

Several accepted records of the HTML page, and the record of a figure that follows the reader's mode, ask for work in browsers other than Chrome:
- **Looks.** A person looks in Safari, Firefox or Edge, as shipped, before a Task closes ([visual-communication:DEC-020-html-page-drawing], [visual-communication:DEC-023-html-page-modes], [visual-communication:DEC-026-html-page-print], [visual-communication:DEC-031-html-page-backdrop], [visual-communication:DEC-039-forced-colours-grounds-and-edges]).
- **Revisits.** A record is revisited where a fault shows in an engine the viewing step does not use, or where Firefox comes to draw otherwise than its test found ([visual-communication:DEC-018-copy-follows-reader-mode], DEC-020, DEC-026, DEC-039).
- **Faults.** Firefox's faults in print went to a bug of their own, mended in part in the renderer ([project-kit#3012](https://github.com/aleskalfas/project-kit/issues/3012)), the rest a report to Firefox's tracker ([project-kit#3510](https://github.com/aleskalfas/project-kit/issues/3510)).

The viewing step draws only through a browser of the Chromium family (DEC-020 point 7). So an agent's check reaches none of that work.

On 27 November 2026 whoever maintains the capability decided ([project-kit#3534](https://github.com/aleskalfas/project-kit/issues/3534)): "We need to have first functional version on chrome, then we can add another. So official supported browser will be just chrome for now." They asked too that testing in the other browsers stop, and that the faults only those browsers show be put off.

Terms:
- *Version 1* of the capability designs web pages, portals and decks under a brand, handed out as HTML and PDF ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)), as [visual-communication:DEC-025-picture-files] has it. A *later version* is any that follows it.
- *A file a browser draws* is the HTML renderer's page file (DEC-020), or a file of the SVG renderer where a web page shows it as an image, the switching file among them (DEC-018).
- A browser is *supported* where the files a browser draws are built for it, checked in it and looked at in it, and where a fault it shows is mended in that version.

## Decision

**Version 1 of the capability supports one browser, Chrome. Each file a browser draws is built, checked and looked at in Chrome alone. No work of version 1 tests in another browser or mends a fault only another browser shows, and what is already built for one stays as built. Support for another browser comes in a later version, by a record of its own.**

### 1. Version 1 supports Chrome alone

- **What it covers.** Each file a browser draws: the HTML page, and an SVG figure where a web page shows it. A PDF, read in a PDF viewer, and the code writers' files, which a project's own code reads, are outside this record.
- **Built for Chrome.** Where a form of such a file is chosen, it is chosen by how Chrome draws it.
- **Checked in Chrome.** The viewing step stays as DEC-020 point 7 has it. It draws through a browser of the Chromium family, which draws with Chrome's own engine, so its checks are version 1's checks in Chrome. A test or a probe that draws in a browser draws there too. A test on a file draws in no browser, and stays as it is.
- **Looked at in Chrome.** Where a record asks a person to look, they look in Chrome as shipped, on the system the record names, such as Windows for a real forced palette.
- **What Chrome is.** Google's browser as it ships, drawing with its own engine. Where it draws with another, as browsers generally do on an iPhone (DEC-018), it counts as another browser. So does a browser built on Chrome's engine, such as Edge.

### 2. Another browser is no work of version 1

- **No test and no look.** No Task, test, probe or look of version 1 draws a file in another browser.
- **A fault only another browser shows** is filed as a bug that names that browser, outside version 1's work, and waits for point 4's record. Version 1 mends nothing for it.
- **A fault Chrome shows too** is version 1's, in whichever browser it was first seen. A look in Chrome tells which it is.
- **A revisit** that an accepted record names, and that only another browser could set off, waits for point 4's record too.
- **What a test found in another browser,** in a record's Context, stays as it stood. It is a fact found on a date, and point 4's record reads it.

### 3. What is built stays as built

- **A form that serves another browser stays.** Such forms are the lengths the HTML renderer writes as shares of a box for Firefox's print ([project-kit#3012](https://github.com/aleskalfas/project-kit/issues/3012)), and the keyline's floor on each browser's ground that DEC-023's test measured (DEC-031 point 3). No work of version 1 checks such a form in its browser.
- **The tests on the file that hold them stay,** since they draw in no browser.
- **Chrome comes first.** A change for Chrome that cannot keep such a form may undo it, and names what it undid, for point 4's record. No other change undoes it.
- **The records' decisions stay as they are.** Only the browser they are built for, checked in and looked at in narrows. What a file gives every browser by construction stays with them, such as a figure's floor: a whole figure, in one of its modes (DEC-018 point 5).

### 4. Another browser comes by a record of its own

- **In a later version.** Support for each further browser comes in a later version of the capability, by a record that brings it.
- **What that record decides:** which browser, the test that reaches it, which of the faults filed for it its version mends, and what becomes of the revisits waiting for it.
- **Until then** nothing promises a reader more in another browser than point 3 keeps.

## Rationale

**Why one browser.** It is the maintainer's choice: a first version that works, in one browser, before another (Context). Each further browser costs a person's looks, probes of its own, and the faults only it shows. Firefox's print alone took a bug, a mend in the renderer and a report to Firefox's tracker (#3012, #3510). WebKit, in a web view, drew a figure's mode by chance from one load to the next (DEC-018, Context). With one browser the work of version 1 finishes sooner, and the record that brings the next browser starts from a page that works.

**Why Chrome.** Every check of the capability already draws with Chrome's engine: the viewing step and a pipeline's drawings (DEC-020 point 7; [visual-communication:DEC-024-outside-programs-sandbox] point 5). Most of the probes the records rest on ran in Chrome too. DEC-020 rejected WebKit as the step's browser (its Alternatives considered). So in Chrome what an agent checks and what a person sees agree, and no check is lost.

**Why a fault only another browser shows waits, and is not closed.** The maintainer asked that such faults be put off, not dropped. Filed, a fault keeps what was seen for the record that brings its browser, which decides whether its version mends it. A fault Chrome shows too is a fault of the supported browser, wherever it was first seen.

**Why what is built stays.** Removing a form that serves another browser is work that gains nothing in Chrome. The tests that hold it draw in no browser, so they cost nothing to keep, and the record that brings that browser starts from it. The cost: no work checks the form in its browser, so it may stop serving there unseen. A change for Chrome may undo it too, and names what it undid, so that record reads it there.

**Why the records' tests stay as they stood.** Each Context says what a test found, in each browser, on its date. A narrower support makes none of it untrue, and the record that brings a browser reads it first.

**Why the records are edited in place.** The records decide how a page is drawn, how it holds its modes, how it prints and how it shows under forced colours, and each of those decisions stands. What narrows is the browser they are built for, checked in and looked at in. So each passage that asks for a look, a mend or a revisit in another browser is narrowed where it stands, with a pointer to this record, and no record is overturned.

**What it costs.** A reader in another browser may meet a fault no work of version 1 looked for. That holds in Firefox, and in Safari, the browser of many readers on a phone (DEC-018). A project that hands out a page file hands it to them too, so the capability's pages say which browser version 1 supports. What the records give every browser by construction stays, such as a figure's floor (point 3).

### Alternatives considered

- **Chrome and Firefox.** Not taken: the maintainer named Chrome alone, and the step draws in no Firefox, so each look and each fault there would stay a person's work.
- **Every browser on Chrome's engine, Edge among them.** Not taken: the maintainer named Chrome. A fault such a browser shares with Chrome is version 1's anyway (point 2).
- **The looks in Safari and Firefox kept once, with nothing they find mended in version 1.** Rejected: the maintainer asked that testing there stop. A look whose findings all wait spends a person's time for a later record, which looks again at what it then builds.
- **What serves another browser removed.** Rejected, for the reason above.
- **The tests in other browsers taken out of each record's Context.** Rejected: they are facts found on a date.
- **The records overturned in part, each with a top line.** Rejected: their decisions stand. A top line would send a reader to this record for a narrowing that a pointer shows where it applies.
- **A word in each page file or export that names Chrome.** Rejected: a renderer adds no words to a page ([visual-communication:DEC-023-html-page-modes] point 4), and a project reads the capability's pages.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). Each narrows its record in place, and its decision stands, so no record takes a top line. Each edit's words end with a forward pointer, `(refinement per [visual-communication:DEC-074-version-one-supports-chrome] point N)`, or `points N and M`, naming the points the edit gives below. The pointer stands at the end of the words, before a full stop that ends them, unless the edit places it otherwise.
  - **DEC-018, its summary's second paragraph.** After "On an iPhone, browsers generally run on WebKit, so that engine stands for many readers." a sentence follows: "Version 1 of the capability supports Chrome alone, so no work of it tests the file in another browser." Points 1 and 2.
  - **DEC-018 point 5, "The reach".** A sentence ends it: "In version 1 of the capability that promise narrows to Chrome: no work tests the file in another browser, or mends a fault only another browser shows." Points 1 and 2.
  - **DEC-018's Implications, "Revisit this record".** This edit's one pointer stands on its lead, before its colon, naming point 2. In its first item, "in a browser the test saw follow it" comes to read "in Chrome". Its second item comes to read "if an engine the test saw vary does worse than a figure in the other mode, readable where it paints a ground, once a version of the capability supports a browser on that engine;". In its third item, "if a browser or a host drops" comes to read "if Chrome or a host drops".
  - **DEC-020 point 5, "What an image does not show".** Its sentence "A person, in a browser, covers another engine, a reader's own settings, a narrow window and printing." comes to read "A person, in Chrome as shipped, covers a reader's own settings, a narrow window and printing, and no work of version 1 of the capability covers another browser." Points 1 and 2.
  - **DEC-020's Rationale, "Why no standing run in other browsers".** Its last two sentences, "The form has met neither Safari as an application nor Firefox as shipped, so a person looks in each once. After that a fault only another engine shows reaches a reader first, and this record accepts that risk.", come to read "The form has met neither Safari as an application nor Firefox as shipped, and version 1 of the capability supports Chrome alone, so no person looks in either. A fault only another engine shows reaches a reader first, and waits for the version that supports that browser. This record accepts that risk." The pointer stands after "so no person looks in either", naming points 1 and 2.
  - **DEC-020's Implications, the Task that builds the step's browser half.** "It closes with a person's look in Safari and in Firefox." comes to read "It closes with a person's look in Chrome as shipped." Point 1.
  - **DEC-020's Implications, "The SVG renderer keeps WebKit's gap".** It comes to read "**The SVG renderer keeps WebKit's gap,** for a change of its own once a version of the capability supports a browser on WebKit." Point 2.
  - **DEC-020's Implications, "Revisit this record".** It comes to read "**Revisit this record** if a browser's update stops point 7's first read, if #2740's test finds a need these elements cannot meet, or if what Context lists as not reached shows a fault in Chrome. A fault that reaches a reader only in an engine the step does not use waits for the record that brings a browser on that engine." Points 2 and 4.
  - **DEC-023's Implications, "The Task that draws the showcase deck".** "in Safari and in Firefox" comes to read "in Chrome as shipped". Point 1.
  - **DEC-026 point 7, "The viewing step reads no print".** "A person looks at a print in each browser (DEC-020 point 5). Safari gets the same rules, and that print is its only check." comes to read "A person looks at a print in Chrome as shipped (DEC-020 point 5). Every browser gets the same rules, and in version 1 of the capability no print is looked at in another." Points 1 and 2.
  - **DEC-026's Rationale, "Point 7, the checks".** "a person's print reaches each browser as shipped" comes to read "a person's print reaches Chrome as shipped". Point 1.
  - **DEC-026's Implications, "#2851's body".** "in each browser as shipped" comes to read "in Chrome as shipped". Point 1.
  - **DEC-026's Implications, "A bug for Firefox's faults in print".** A sentence ends it: "What the renderer cannot mend of them waits for a version of the capability that supports Firefox." Point 2.
  - **DEC-026's Implications, "Revisit this record".** Its case "Firefox comes to keep a page's text on its shapes across a cut, at any scale the reader sets, or under a page rule" comes to end ", once a version of the capability supports Firefox". Point 2.
  - **DEC-031's Implications, the Task that builds this record.** "It closes with a person's look in Safari and in Firefox, in light, dark, more contrast and forced colours." comes to read "It closes with a person's look in Chrome as shipped, in light, dark, more contrast and forced colours." Point 1.
  - **DEC-039's Implications, "Before #3088 closes".** "in Edge or Chrome on Windows and in Firefox" comes to read "in Chrome on Windows". Point 1.
  - **DEC-039's Implications, "Revisit this record".** ", or Firefox's," goes from "if a real forced palette, or Firefox's, meets the grounds", and the pointer ends the bullet, before its full stop. Point 2.
- **Read against this record, and left as they stand:**
  - each record's Context, its tests and looks in other browsers among them, since they are facts found on a date (point 2);
  - DEC-018 points 1 to 4, 6 and 7, and its Rationale and alternatives, which weigh the form by what its test found in each engine on its date. Its Implications' "A test in a browser holds that each way repaints" draws in Chrome (point 1);
  - DEC-020 point 7 and its Rationale "Why the Chromium family, no pin, and no Playwright", since the step draws with Chrome's engine (point 1), and its alternative "WebKit as the step's browser";
  - DEC-023 point 7's "No check reads that ground, which differs between browsers", and its revisit, which reads a fault only another browser shows as point 2 has it;
  - DEC-026's Rationale and alternatives on Firefox's print, which are what its runs found, and its Implications' "Read against this answer", whose Firefox faults are the bug's;
  - [visual-communication:DEC-027-forced-colours-viewing] whole. It names Firefox only in its Context, its forced palettes are drawn under the flag of the step's browser, and its revisit on a real forced palette on Windows reads Chrome there (point 1);
  - DEC-031 point 3, whose keyline keeps its floor on each browser ground DEC-023's test measured (point 3), its point 5's "A person judges their look in a browser", which point 1 makes Chrome, and its revisit, read as point 2 has it;
  - DEC-039's Rationale "Why a clipped shape's cover stays", whose weighing of what Firefox kept is a reason found on its date;
  - [visual-communication:DEC-015-viewing-step-and-reviewer] point 6, since an image of the HTML renderer's page stands for the browser that drew it.
- **Edits to the capability's page on outputs** (`outputs.md`), made in this change once this record is accepted, each anchored to this record:
  - **The HTML renderer** says at its head that version 1 supports Chrome alone. The page file is built for Chrome, checked in Chrome and looked at in Chrome, and another browser may show a fault no work of version 1 looked for (points 1 and 2).
  - **The HTML renderer's pages, "What an image does not show",** sends a person to open the page file in Chrome, the one browser version 1 supports.
  - **Printing, "Where a page that runs on breaks",** says that version 1 checks no print in Safari, in place of "so Safari's only check is a person's print". **"Firefox and a page at another width" and "Firefox and a run's size"** say that the renderer keeps these forms as built, and that version 1 checks them in no browser (point 3).
  - **The switching file, "What a reader sees",** says that version 1 promises the reach in Chrome alone, and that the test's findings in Firefox and WebKit stand as found on their date.
- **Issues, edited once this record is accepted:**
  - **[project-kit#2851](https://github.com/aleskalfas/project-kit/issues/2851)** comes to ask a person's look in Chrome as shipped, in its title too. Its looks in Safari and Firefox go to an issue of their own, outside version 1's milestone, for point 4's record.
  - **[project-kit#2774](https://github.com/aleskalfas/project-kit/issues/2774)'s** person opens the figure's real page in Chrome.
  - **[project-kit#3011](https://github.com/aleskalfas/project-kit/issues/3011)** weighs where a page breaks in Chrome's print, and what it would mend of Firefox's waits (point 2).
  - **[project-kit#3118](https://github.com/aleskalfas/project-kit/issues/3118)'s** test reaches Chrome at the step's scale, and the other engines wait.
  - **#3510** stays outside version 1's milestone, for the record that brings Firefox.
  - **Each fault filed for another browser alone** is kept out of version 1's milestone (point 2).
- **Its changeset.** The change that makes these edits declares one for the capability, whose note says that version 1 supports Chrome alone. No file the capability writes changes, so it owes no migration (COR-010).
- **Revisit this record** if the viewing step's browser comes to draw otherwise than Chrome as shipped, so that its checks no longer stand for Chrome, or if a project needs another browser before version 1 ships.
