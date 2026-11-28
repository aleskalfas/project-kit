---
id: DEC-074
title: The capability supports one browser, Chrome
status: accepted
date: 2026-11-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability supports one browser, Chrome. What a browser draws of the capability's, the HTML page and an SVG figure, is built for Chrome, checked through Chrome's engine and looked at in Chrome as Google ships it. No work tests it in Safari, Firefox or any other browser, and a fault only another browser shows is filed and waits. What is already built for another browser is kept as built, such as the lengths the HTML renderer writes for Firefox's print. Until a record brings another browser, the capability supports Chrome alone. For example, a person prints the showcase deck, the deck of the repository the capability is authored in, in Chrome as shipped, and in no other browser.

## Context

Several accepted records of the HTML page, and the record of a figure that follows the reader's mode, ask for work in browsers other than Chrome, or promise a reader something there:
- **Looks.** A person looks in Safari, Firefox or Edge, as shipped ([visual-communication:DEC-020-html-page-drawing], [visual-communication:DEC-023-html-page-modes], [visual-communication:DEC-026-html-page-print], [visual-communication:DEC-031-html-page-backdrop], [visual-communication:DEC-039-forced-colours-grounds-and-edges]).
- **A promise.** A figure follows the reader's mode as far as a test found each browser carry it ([visual-communication:DEC-018-copy-follows-reader-mode] point 5).
- **Revisits.** A record is revisited where a fault shows in an engine the viewing step does not use, or in Firefox (DEC-018, DEC-020, DEC-026, DEC-039).
- **Faults.** Firefox's faults in print went to a bug of their own, worked around in part in the renderer ([project-kit#3012](https://github.com/aleskalfas/project-kit/issues/3012)), the rest a report to Firefox's tracker ([project-kit#3510](https://github.com/aleskalfas/project-kit/issues/3510)).

The viewing step draws only through a browser of the Chromium family (DEC-020 point 7). So an agent's check reaches none of that work.

On 27 November 2026 whoever maintains the capability decided, in three messages:
- "postpone all bugs from different browsers than chrome."
- "Actually stop test it on them."
- "We need to have first functional version on chrome, then we can add another. So official supported browser will be just chrome for now."

[project-kit#3534](https://github.com/aleskalfas/project-kit/issues/3534) asks for the record that writes it down. The first functional version is version 1 of the capability, which designs web pages, portals and decks under a brand, handed out as HTML and PDF ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)), as [visual-communication:DEC-025-picture-files] has it.

Terms:
- *A file a browser draws* is the HTML renderer's page file (DEC-020), or a file of the SVG renderer where a web page shows it as an image, the switching file among them (DEC-018), or where a browser opens it in a tab.
- A browser is *supported* where the files a browser draws are built for it, checked for it and looked at in it, and where each fault it shows is mended, worked around or reported upstream.

## Decision

**The capability supports one browser, Chrome. Each file a browser draws is built for Chrome, checked through Chrome's engine and looked at in Chrome as shipped. No work tests or looks in another browser, or mends a fault only another browser shows, and what is built for one is kept as built. Until a record brings another browser, the capability supports Chrome alone.**

### 1. The capability supports Chrome

- **The supported browser** is Chrome as Google ships it, in its current stable release, drawing with its own engine. Chrome on Android and on Linux counts as Chrome, though no person looks there. Where Chrome draws with another engine, as browsers generally do on an iPhone (DEC-018), it counts as another browser. So does a browser built on Chrome's engine, such as Edge.
- **What it covers.** Each file a browser draws: the HTML page, an SVG figure a web page shows, and an SVG a browser opens in a tab.
- **What it leaves out.** A PDF, which a PDF viewer reads, though a fault in one that only another browser's own PDF viewer shows waits too (point 2). The code writers' files, such as the CSS writer's style sheet: they reach a browser only inside pages a project builds itself, which the capability neither draws nor checks, so which browsers those pages serve is the project's.
- **Built for Chrome.** Where a form of such a file is chosen, it is chosen by how Chrome draws it. Where Chrome draws two forms alike, the standard one is chosen.
- **What stands as a check of Chrome.** The viewing step's browser of the Chromium family (DEC-020 point 7), and the browser of that family a test draws in, draw with Chrome's engine. Their checks stand for Chrome as far as the step's first read holds (DEC-020 point 7). Their images still stand only for the browser that drew them ([visual-communication:DEC-015-viewing-step-and-reviewer] point 6). A test on a file draws in no browser, and stays as it is.
- **Looked at in Chrome.** A person's look in Chrome as shipped covers what the checks do not. Where a record asks a person to look, they look in Chrome as shipped, on the system the record names, such as Windows for a real forced palette.

### 2. No work tests, looks or mends in another browser

- **No test and no look.** No Task, test, probe or look draws a file in another browser. The viewing step's browser of the Chromium family, and the browser of that family a test draws in, are no other browser here (point 1).
- **A fault only another browser shows** is filed as a bug that names that browser, and waits for the record that brings that browser. No work mends it meanwhile.
- **A fault Chrome shows too** is the capability's to mend, work around or report upstream, in whichever browser it was first seen. A look in Chrome tells which it is.
- **A revisit** an accepted record names, that only a fault of another browser would set off, waits for the record that brings that browser. A revisit that a fault in Chrome would set off stands as it is.
- **What a test found in another browser,** in a record's Context or its Rationale, stays as it stood, a fact found on a date.

### 3. What is built for another browser is kept as built

- **Kept, and checked in no browser.** A form a file holds for another browser stays, such as the lengths the HTML renderer writes as shares of a box for Firefox's print ([project-kit#3012](https://github.com/aleskalfas/project-kit/issues/3012)), and the keyline's floor on each browser ground DEC-023's test measured (DEC-031 point 3). No work checks in a browser that it still serves the browser it was built for. The tests on the file that hold it stay, since they draw in no browser.
- **A change to it is like any other.** Where an accepted record decides such a form, changing it needs a record, as any change to what such a record decides does (COR-065 point 3).
- **A figure's floor holds by construction.** A whole figure, in one of the piece's modes (DEC-018 point 5), rests on how the file is drawn and exported, not on what a browser was checked to do. So it holds in another browser as DEC-018 states it, and no work checks it there.

### 4. Another browser comes by a record of its own

- **Each further browser** comes by a record that brings it. Until a record brings another browser, the capability supports Chrome alone.

## Rationale

**Why one browser.** It is the maintainer's choice: a first version that works, in one browser, before another (Context). Each further browser costs a person's looks, probes of its own, and the faults only it shows. Firefox's print alone took a bug, a workaround in the renderer and a report to Firefox's tracker (#3012, #3510). WebKit, in a web view, drew a figure's mode by chance from one load to the next (DEC-018, Context). With one browser the work finishes sooner, and the record that brings the next browser starts from pages that work.

**Why Chrome.** Every check of the capability that draws in a browser already draws with Chrome's engine: the viewing step, a test, and a pipeline's drawings, which the pipeline where the capability is authored makes on a real Chrome (DEC-020 point 7; [visual-communication:DEC-024-outside-programs-sandbox] point 5). Most of the probes the records rest on ran in Chrome too. DEC-020 rejected WebKit as the step's browser (its Alternatives considered). So in Chrome what an agent checks and what a person sees agree.

**Why Chrome as shipped, with the step's browser as its check.** A reader gets Chrome as Google ships it, so that is where a person looks. The step's browser may be Chromium, or a pinned build a project names (DEC-020 point 7), and its pixels may differ from Chrome's (DEC-015 point 6). Its reads still hold wherever its first read passes, since that read stops a run whose check would miss a planted fault. So its checks stand for Chrome that far, and a person's look covers what only Chrome as shipped shows, such as a reader's own settings, a narrow window and a print. Held to Chrome as shipped alone, the step would refuse the builds DEC-020 lets a project name, for no read it gains.

**Why Chrome on any system that runs its engine.** Chrome on Android and on Linux draws with the engine Chrome draws with elsewhere, so a fault seen there is a fault of the supported browser. A person's look on each system would cost what a further browser costs, so none is asked. Chrome on an iPhone draws with WebKit, so a fault only it shows is WebKit's.

**Why the scope ends where it does.** A browser draws the page file and an SVG, whether a page shows the SVG or a tab opens it, so they lie inside. A PDF viewer draws a PDF, and the capability hands a PDF out to be read in one. A browser's own PDF viewer is part of that browser, so a fault only another browser's viewer shows waits, as that browser's other faults do. The code writers' files reach a browser only inside a project's own pages, which the capability neither draws nor sees, so it could check nothing of them there.

**Why a fault only another browser shows waits, and is not closed.** The maintainer asked that such faults be put off, not dropped. Filed, a fault keeps what was seen for the record that brings its browser. A fault Chrome shows too is a fault of the supported browser, wherever it was first seen.

**Why a revisit waits only where another browser's fault alone would set it off.** A revisit asks whether a record still holds for the readers it serves. A fault in Chrome asks that of the supported browser, so such a revisit stands. A fault only another browser shows reaches no supported reader, so it waits with the faults point 2 files. Read so, one rule reaches every revisit the records name, and none is edited.

**Why what is built stays.** Removing a form that serves another browser is work that gains nothing in Chrome. The tests that hold it draw in no browser, so they cost nothing to keep, and the record that brings that browser starts from it. The cost: no work checks the form in its browser, so it may stop serving there unseen.

**Why the standard form.** Where Chrome draws two forms alike, either serves the supported browser. The standard one is the form another browser is likeliest to draw alike, so it leaves less to mend when a record brings one, at no cost in Chrome.

**Why the records are edited in place.** The decisions README refines a record in place where its decision stands, narrowed, widened or completed, and has another record supersede it in part where that record decides otherwise. Each clause edited here asks for a look, or makes a promise, in browsers no record chose to serve: "in a browser", "in each browser", "a person looks in each once", Safari's print as "its only check", and the reach a test found. The set of browsers served was left unbounded, and this record bounds it to Chrome. So each clause narrows with it, and what its record decides of a page, a print or a figure stands. DEC-020's partial supersession is no precedent against this. [visual-communication:DEC-037-text-the-page-hides] overturned what DEC-020's check reads, which came to name a cover its sentence said it asked nothing of. Here no page, check or print comes to do anything otherwise. Three edits negate words outright: "covers another engine" and "so a person looks in each once" in DEC-020, and "that print is its only check" in DEC-026. Each was weighed as a partial supersession. Each removes a browser from a look, and decides nothing of a page. Under a top line, its words would stand where a reader sent to the point reads them, an order to look in a browser no work looks in. So these are edited in place too, each with a pointer where its words stood.

**What it costs.** A reader in another browser may meet a fault no work looked for. That holds in Firefox, and in Safari, the browser of many readers on a phone (DEC-018). A project that hands out a page file hands it to them too, so the capability's pages say which browser it supports. A figure's floor still holds there by construction, unchecked (point 3).

### Alternatives considered

- **Chrome and Firefox.** Not taken: the maintainer named Chrome alone, and the step draws in no Firefox, so each look and each fault there would stay a person's work.
- **Every browser on Chrome's engine, Edge among them.** Not taken: the maintainer named Chrome. A fault such a browser shares with Chrome is the capability's anyway (point 2).
- **The step's browser held to Chrome as shipped.** Rejected, for the reason above.
- **Support tied to version 1, with another browser in a later version.** Rejected. A version's number says nothing of which browsers a record has brought, and a record may bring one whenever its work is ready, before a release or after it. So the support ends where a record ends it.
- **The looks in Safari and Firefox kept once, with nothing they find mended.** Rejected: the maintainer asked that testing there stop. A look whose findings all wait spends a person's time for a later record, which looks again at what it then builds.
- **What serves another browser removed.** Rejected, for the reason above.
- **The tests in other browsers taken out of each record's Context.** Rejected: they are facts found on a date.
- **Each revisit edited to name the browser it waits for.** Rejected: one rule reads them all (point 2), and an edit to each would add words to records whose decisions stand.
- **The records overturned in part, each with a top line.** Rejected, for the reasons above.
- **A word in each page file or export that names Chrome.** Rejected: a renderer adds no words to a page (DEC-023 point 4), and a project reads the capability's pages.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). Each narrows its record in place, and its decision stands, so no record takes a top line. Each edit's words end with a forward pointer, `(refinement per [visual-communication:DEC-074-supports-chrome-alone] point N)`, or `points N and M`, naming the points the edit gives below. The pointer stands at the end of the words, before a full stop that ends them, unless the edit places it otherwise.
  - **DEC-018 point 5, "The reach".** A sentence ends it: "Beyond the floor, that promise holds in Chrome alone, and no work checks how far another browser carries the mode." Points 1 and 2.
  - **DEC-020 point 5, "What an image does not show".** Its sentence "A person, in a browser, covers another engine, a reader's own settings, a narrow window and printing." comes to read "A person, in Chrome as shipped, covers a reader's own settings, a narrow window and printing, and no work covers another engine." Points 1 and 2.
  - **DEC-020's Rationale, "Why no standing run in other browsers".** Its last two sentences, "The form has met neither Safari as an application nor Firefox as shipped, so a person looks in each once. After that a fault only another engine shows reaches a reader first, and this record accepts that risk.", come to read "The form has met neither Safari as an application nor Firefox as shipped, and the capability supports neither, so no person looks in them. A fault only another engine shows reaches a reader first, and this record accepts that risk." The pointer stands after "so no person looks in them", naming points 1 and 2.
  - **DEC-026 point 7, "The viewing step reads no print".** "A person looks at a print in each browser (DEC-020 point 5). Safari gets the same rules, and that print is its only check." comes to read "A person looks at a print in Chrome as shipped (DEC-020 point 5). Every browser gets the same rules, and no print is checked in another." Points 1 and 2.
  - **DEC-026's Rationale, "Point 7, the checks".** "a person's print reaches each browser as shipped" comes to read "a person's print reaches Chrome as shipped". Point 1.
- **Read against this record, and left as they stand:**
  - each record's Context, its tests and looks in other browsers among them, and each passage of a Rationale or an alternative that weighs what such a test found, since they are facts found on a date (point 2). Among them are DEC-018's "Why the record goes on", DEC-026's on Firefox's print, DEC-031's "Why mixes", whose mix keeps close to each browser's ground, Chrome's among them, and DEC-039's "Why a clipped shape's cover stays", which Chrome's own loss decides;
  - each record's revisits, read as point 2 reads them, so none is edited. A case that only a fault of another browser would set off waits, such as DEC-039's on Firefox's forced palette, and every other case stands, such as DEC-036's on a browser that loses a sign's outline, where that browser is Chrome. DEC-026's case of Firefox coming to keep a page's text on its shapes names no fault and asks no look, so it stands. DEC-037's case of a browser that comes to paint a forced fill or a ground otherwise reads the step's browser, the one its read runs in (point 1);
  - the closing conditions of Tasks already closed, spent with their Tasks: DEC-020's on the Task that builds the step's browser half, DEC-023's on the Task that draws the showcase deck, DEC-031's on the Task that builds it, and DEC-039's "Before #3088 closes" (#2785, #2817, #2944 and #3088);
  - DEC-026's Implications on #2851's body and on the outputs page, each an edit made when that record was accepted, and its bug for Firefox's faults in print, filed as point 2 files a fault. What #2851 asks falls under the rule on issues below;
  - DEC-020's Implications "The SVG renderer keeps WebKit's gap, for a change of its own", a mend of a fault only WebKit showed, which waits (point 2);
  - DEC-018's summary and its other points, its point 5's floor, which holds by construction (point 3), its Implications' test in a browser, which draws in the step's (point 1), and its look at a figure's real page, which point 1 makes a look in Chrome. So too its narrowing of UC-094 and the glossary, which say the figure takes the mode the reader's browser tells an image, as far as the browser carries it, and name no browser;
  - DEC-020 point 7, its Rationale "Why the Chromium family, no pin, and no Playwright" and its alternative "WebKit as the step's browser", since the step draws with Chrome's engine (point 1);
  - DEC-023 point 7's "No check reads that ground, which differs between browsers", whose person looks in Chrome (point 1);
  - [visual-communication:DEC-027-forced-colours-viewing] whole. It names Firefox only in its Context, its forced palettes are drawn under the flag of the step's browser, and its revisit on a real forced palette on Windows reads Chrome there (point 1);
  - DEC-031 point 3, whose keyline keeps its floor on each browser ground DEC-023's test measured (point 3), and its point 5's "A person judges their look in a browser", which point 1 makes Chrome;
  - DEC-015 point 6, since an image of the HTML renderer's page stands for the browser that drew it (point 1).
- **Edits to the capability's page on outputs** (`outputs.md`), made in this change once this record is accepted, each anchored to this record:
  - **The HTML renderer** says at its head that the capability supports Chrome alone. The page file is built for Chrome, checked through Chrome's engine and looked at in Chrome as shipped, and another browser may show a fault no work looked for (points 1 and 2).
  - **The HTML renderer's pages, "What an image shows",** says that an image stands only for the browser that drew it, that the step's checks stand for Chrome as far as its first read holds, and that a person's look in Chrome as shipped covers the rest (point 1).
  - **The HTML renderer's pages, "What an image does not show",** sends a person to open the page file in Chrome as shipped, the one browser the capability supports, and says that no work looks at it in another (points 1 and 2).
  - **Printing, "Where a page that runs on breaks",** says that no work checks a print in Safari, in place of "so Safari's only check is a person's print". **"Firefox and a page at another width" and "Firefox and a run's size"** say that the renderer keeps these forms as built, and that no work checks them in Firefox (point 3).
  - **The switching file, "What a reader sees",** says that the reach is promised in Chrome alone, that the floor holds in another browser by construction and no work checks it there, and that the test's findings in Firefox and WebKit stand as found on their date (points 1 to 3).
- **Issues,** edited once this record is accepted. Each open issue whose criteria ask for a look, a test or a mend in another browser alone moves out of the version 1 milestone, or, where its criteria ask for work in Chrome too, is narrowed to Chrome. A fault filed for another browser alone stays out of that milestone (point 2).
- **Its changeset.** The change that makes these edits declares one for the capability, whose note says that the capability supports Chrome alone. No file the capability writes changes, so it owes no migration (COR-010).
- **Revisit this record** if a person's look finds Chrome as shipped drawing a fault the step's browser does not, so that the step's checks no longer stand for Chrome.
