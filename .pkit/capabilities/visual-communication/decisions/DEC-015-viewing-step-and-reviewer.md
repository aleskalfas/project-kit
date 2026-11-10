---
id: DEC-015
title: A piece's drawn pages are seen as images nothing else reads, and a reviewer reports what no check measures
status: accepted
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** whoever builds a piece can see its pages as images while it is built. The *viewing step* draws what a renderer drew, and writes images, with the frames and a report beside them, in the clone's local folder. It is no plugin and no render, and no check, export or producer reads what it writes. Text its tool drew to nothing never passes in silence. For the SVG renderer's pages that tool is resvg, through the pinned `resvg-py` wheel, which calls no outside program. For the HTML renderer's it is a browser (refinement per [visual-communication:DEC-020-html-page-drawing]). The images promise nothing about their pixels. `graphic-design-reviewer` reads them on demand, reports what no check measures, and in this first form only advises.

## Context

A piece's drawn result is seen today only by opening a preview or an export. Whoever builds a piece learns that the checks passed, not what the page shows ([project-kit#2672](https://github.com/aleskalfas/project-kit/issues/2672)). The records already leave part of the drawing to a reviewer, such as a text over a picture ([visual-communication:DEC-004-brands-and-notations] point 8). The founding record leaves the capability's agents to later records ([visual-communication:DEC-001-visual-communication-discipline], Implications).

Three tools were tried on real pages, on one Mac: the starter's reference pieces, one in Czech, and one with a produced picture.
- **resvg over the SVG,** through the `resvg-py` wheel, draws a page in about 50 ms from a wheel of under 2 MB. It gives the same bytes in separate processes, shows pictures, and ran with the network denied in hand-written sandboxes. It ignores `@font-face`. Left to the committed font files, it dropped every text whose family differs from the file's own name, and said nothing. Given the page's faces under the names their rules give, it matched Chrome by eye.
- **Headless Chrome over the SVG** draws no better: by eye the two differ in edge smoothing, with no shift of layout. It takes about a second a page and weighs 2.1 GB. It cannot be pinned, and it died in every sandbox tried.
- **pdfium over the PDF** shows no picture, since the PDF renderer refuses images.

What was not measured, where any failure reopens the tool (Implications):
- **Where it runs:** Linux, the real sandbox profile and the `uv run --script` path. The sandboxes tried were written by hand, and the wheel ran from a virtual environment. That the step needs no sandbox change is expected, not settled.
- **What it draws:** a detailed picture, a role with two families and TrueType outlines. The one picture drawn was a solid square, every role held one family, and every font was CFF. Read from resvg's code and not run, its fallback sets a line of two families otherwise than a browser.
- **Whether the step can learn what the tool dropped, down to a run.** The tool returns only the image, and logs a family it could not match to the process's output.
- **The licence of the resvg the wheel bundles.** The wheel's own licence reads as MIT, and its package data gives resvg's as Apache-2.0 or MIT. Neither text has been read.

## Decision

**A person or an agent sees a piece's drawn pages through a viewing step that is no plugin and no render, and adds nothing to the seam. It draws a renderer's output as images, by page, band, language and key, into the clone's local folder (refinement per [visual-communication:DEC-022-web-site-and-parts]). Text its tool drew to nothing never passes in silence. Its tool is resvg for the SVG renderer's pages, through the pinned `resvg-py` wheel, and a browser for the HTML renderer's. Each lies behind one module of its own (refinement per [visual-communication:DEC-020-html-page-drawing]). Its images promise nothing about their pixels. `graphic-design-reviewer`, read-only and in this first form advisory, reads them on demand and reports what no check measures.**

### 1. The viewing step draws a renderer's output, and adds nothing to the seam

- **What it is** (refinement per [visual-communication:DEC-022-web-site-and-parts]). The *viewing step* draws, as an image, what a renderer drew for one page or one band of a page (point 5), in one language, under one key ([visual-communication:DEC-004-brands-and-notations] point 3). Where its tool can force a palette, it draws each image under one forced palette or none. A *forced palette* is the colours a browser gives a page under forced colours, and an image drawn under one is a *forced image* (refinement per [visual-communication:DEC-027-forced-colours-viewing]). It is defined over that drawn output, never over one format, so a later renderer that writes its pages to files fits it. A command of the capability runs it. Only a person or an agent reads what it writes, never a check, an export or a producer.
- **No plugin.** It is none of the three kinds, and adds nothing to the seam: it uses the seam from the engine's side, as render and export do ([visual-communication:DEC-005-engine-and-plugins] points 8 and 9). So it has no declaration and no version of its own.
- **No render, and no export.** It moves no lock and keeps no record of findings, as a render does ([visual-communication:DEC-003-change-over-time] point 8, DEC-005 point 13). It takes no number and rewrites no record of exports, as an export does ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7).
- **It runs no helper or producer** (DEC-006 point 1). A produced picture is drawn as it stands, stale or not (refinement per [visual-communication:DEC-020-html-page-drawing]).

### 2. Each tool lies behind one module of its own

- **Behind one module of its own** (refinement per [visual-communication:DEC-020-html-page-drawing]). Each tool lies behind one module of the capability. That module takes what the renderer drew, a page or a page file, with the regions of it to draw (refinement per [visual-communication:DEC-022-web-site-and-parts]), and gives images and what the tool dropped. Nothing else of the step calls the tool. Reading the SVG renderer's pages is how resvg works, not what the step is. The browser's module also takes the reader's signals to set (refinement per [visual-communication:DEC-023-html-page-modes] point 6). It also takes whether to force the browser's colours, and names each forced palette's signals. A browser start that forces colours runs under the browser's own flag for it, and sets forced colours there by emulation, with each forced palette's signals (refinement per [visual-communication:DEC-027-forced-colours-viewing]).
- **resvg is pinned, and in the command's own process** (refinement per [visual-communication:DEC-020-html-page-drawing]). The wheel is pinned exactly, as the capability's scripts pin their packages, and runs as a library. So drawing with it needs no other runtime and no network ([visual-communication:DEC-002-files-and-validation] point 8). It calls no outside program to draw.
- **The page's faces, for resvg** (refinement per [visual-communication:DEC-020-html-page-drawing]). resvg ignores `@font-face`. So the step takes each face from the page's `@font-face` rules, and hands it over under the family and the weight its rule names. resvg reads no font of the machine (DEC-004 point 9). The faces are transient files, in a temporary folder inside the clone's local folder, which the run removes.
- **What resvg draws otherwise** (refinement per [visual-communication:DEC-020-html-page-drawing]). resvg's fallback may draw a run measured in more than one family otherwise than a browser does (Context). A face a browser could not read may still draw in resvg.
- **The browser** (refinement per [visual-communication:DEC-020-html-page-drawing]). The browser is an outside program, called only for the HTML renderer's pages. It reads the faces itself, and may draw a run in a font of the machine. It keeps its own sandbox on, and leaves a session's sandbox only as [visual-communication:DEC-024-outside-programs-sandbox] allows (refinement per DEC-024).

### 3. Text drawn to nothing never passes in silence

The step reports what it cannot show as the renderer set it, in a report beside the images, so a later reader has it too:
- **Each loss the renderer reports** (DEC-005 point 9), since a colour left out can draw a text to nothing.
- **Each text, or run of a text, the tool dropped,** naming the page and the element, whatever the cause. How the step learns of one from resvg is left to the command ([project-kit#2674](https://github.com/aleskalfas/project-kit/issues/2674)). A browser's drops are learned as [visual-communication:DEC-020-html-page-drawing] point 6 says.
- **Each run the tool is known to draw otherwise** (point 2), naming the page and the element. A run in a font of the machine, or with no face, counts as drawn otherwise (refinement per [visual-communication:DEC-020-html-page-drawing]).
- **What drew the page** (refinement per [visual-communication:DEC-020-html-page-drawing]). The report names the renderer, and where a browser drew, the browser and each request refused. It names the forced palettes drawn, and that the browser's flag forced them (refinement per [visual-communication:DEC-027-forced-colours-viewing]).
- **A run of the step that draws no image** leaves a report, which says so (refinement per [visual-communication:DEC-020-html-page-drawing]).

### 4. It reads under the lock, and writes nothing committed

- **Under the lock.** It reads the piece's own file with its lock, computes the scenes under that lock, and never moves it. It refuses a piece with no lock, naming the render that writes one.
- **What it writes, and where** (refinement per [visual-communication:DEC-020-html-page-drawing]). Only the images, the frames, the report beside them (points 3 and 5), the page file where a renderer writes one, and its transient files. All of them lie in the clone's local folder alone (DEC-002 point 1). So nothing it writes reaches a commit. This record names its command their writer (DEC-002 point 9). Its transient files are point 2's faces and a browser's throwaway profile, which a run removes, even one that stops. A browser may write files of its own elsewhere, such as a crash database, or a socket in the system's temporary folder.
- **A run replaces what an earlier run left** in its renderer's folder, so that folder never mixes two runs (refinement per [visual-communication:DEC-020-html-page-drawing]). Each renderer has a folder of its own for the piece. The frames name the lock the images were drawn under, and the report names it too.

### 5. What it draws

- **The caller picks** pages, languages, modes and the renderer (refinement per [visual-communication:DEC-020-html-page-drawing]). By default it draws the source language, in one combination of the modes the piece names. That is the first key in the order a picture's variant uses (DEC-004 point 3), so the combination of defaults wherever the piece names it. The renderer's default is as [visual-communication:DEC-020-html-page-drawing] point 5 says. The caller may also ask for each page file in the browser's two forced palettes. There each forced palette, not the caller, picks the key an image shows (refinement per [visual-communication:DEC-027-forced-colours-viewing]).
- **The size.** Each image is large enough that a page's smallest text reads. The number is left to the command (#2674).
- **A tall page in bands** (refinement per [visual-communication:DEC-022-web-site-and-parts]). A page too tall for one such image is drawn in *bands*, strips of its height each as wide as the page, as DEC-022 point 7 says.
- **Frames.** Beside each image lies each element's frame, in the image's pixels, with its trace id (DEC-005 point 5). So a finding names the element, and through it the field.
- **The ground.** Where a page draws no ground of its own, its image lies on white, which the piece never set. An image of the HTML renderer's page lies instead on the browser's own ground in the mode it is drawn in (refinement per [visual-communication:DEC-023-html-page-modes] point 7). An image under a forced palette lies on that palette's ground (refinement per [visual-communication:DEC-027-forced-colours-viewing]). A text over nothing is judged knowing this.

### 6. It promises nothing about pixels

- **No contract.** The images may change with the tool, its version or the machine. No test and no check compares them as a contract, and no reference image is kept.
- **It shows one tool's drawing** (refinement per [visual-communication:DEC-020-html-page-drawing]). An image of the SVG renderer's page shows resvg's drawing, not a browser's, and point 2 says where the two are known to differ. An image of the HTML renderer's page shows one browser's drawing, and stands for no other. An image under a forced palette shows that browser's forced palette, not a reader's own (refinement per [visual-communication:DEC-027-forced-colours-viewing]).

### 7. The reviewer's first form

- **Whose.** `graphic-design-reviewer` is the capability's agent, since its work implies the capability's discipline (COR-026). It is read-only and advisory, and a session dispatches it on demand.
- **It reads, and does not draw** (refinement per [visual-communication:DEC-020-html-page-drawing]). The session runs the step. The reviewer reads the images, with the piece and the brand, and the frames and the report beside them. A session may hand it other images of the same pages, which promise nothing either. Its report says which tool or renderer drew each, and under which lock. It also reads the piece's brief, the rule-set files, and the sources in the repository that the piece's facts name (refinement per [visual-communication:DEC-030-design-agents]).
- **Its remit** is what no check measures on the drawn result, such as the contrast of a text over a picture (DEC-004 point 8). The agent's body holds the list of faults. It also judges whether the piece keeps the rules the rule sets hold for it, and shows what its brief asks (refinement per [visual-communication:DEC-030-design-agents]). A forced image is evidence of what its palette's reader loses, and no finding on it rests on a brand's colour (refinement per [visual-communication:DEC-027-forced-colours-viewing]).
- **Its findings** are of four kinds, kept apart by what they cite (refinement per [visual-communication:DEC-030-design-agents]). A *fault* is one that list names, and never a judgement of how well a page is designed. A *rule finding* cites a rule, and a *brief finding* a part of the brief. A *note* is anything else worth a look. Each names the page, and the element's trace id where the element was drawn. A finding on an image a session handed it names that image (refinement per [visual-communication:DEC-020-html-page-drawing]). A finding on a forced image names its forced palette (refinement per [visual-communication:DEC-027-forced-colours-viewing]).
- **Nothing unseen reads as clean.** Its report says which pages, languages and modes it looked at, and names the bands of each page it read (refinement per [visual-communication:DEC-022-web-site-and-parts]). It names the sizes it looked at, the brief it read or that the piece has none, and the rule sets it read (refinement per [visual-communication:DEC-030-design-agents]). It names the forced palettes it looked at. Where a run through the HTML renderer drew none, it lists forced colours as not seen (refinement per [visual-communication:DEC-027-forced-colours-viewing]). It needs a harness that reads images, and where the harness reads none, it stops and says so. On a folder a stop left, it passes the ways on that the stop names to whoever asked it (refinement per [visual-communication:DEC-024-outside-programs-sandbox]).
- **Advice, for now.** Its findings join no validation, and hold no merge until a record gives them a place there ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)). The starter's owner judges a component's entry, and the findings only inform that review ([visual-communication:DEC-007-starter-library], Implications).
- **Left to others** (refinement per [visual-communication:DEC-028-principles-of-visual-communication] and [visual-communication:DEC-030-design-agents]). The rules of visual communication are DEC-028's, and the reviewer judges a piece against the rule sets that hold them. The capability's agents and their boundaries are DEC-030's. The agent that translates is [project-kit#2582](https://github.com/aleskalfas/project-kit/issues/2582)'s.

## Rationale

**Why no plugin.** A plugin meets the engine at the seam, and no plugin reads another's output (DEC-005 point 7). This step reads a renderer's output, and nothing downstream reads its own. A plugin also pins reference outputs to its version (DEC-005 point 9), which is the promise point 6 refuses.

**Why resvg for now.** It is the one tool tried that shows pictures and can be pinned. Chrome draws no better, and would be a large outside program that moves with the machine. pdfium cannot show a picture while the PDF renderer refuses images. A difference of pixels costs little, since the tool sits behind one module and promises none. A tool that cannot run or ship costs more, since no tried tool stands behind it, so such a failure reopens the choice.

**Why the rule is on what the tool drew, not on the page's names.** A dropped text leaves empty space, which an agent would take for missing content. The engine refuses a missing font or character before any page exists (DEC-004 point 9), so a guard on the page's names never fires. Only the tool's result shows what it dropped.

**Why no promise about pixels.** A test that held pixels would tie the capability to a tool chosen for now, and fail on a machine nobody measured. A reader needs the page, not its bytes. So the tool can change with no change of contract.

**Why the reviewer advises, on demand.** It reads a drawing by judgement, and a reading of taste never fails (DEC-002 point 7). A required review needs a way to find a piece's change, and rules to cite, so it waits for them ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)).

### Alternatives considered

- **Headless Chrome now, or pdfium over the PDF.** Rejected, for the reasons above. Chrome also stops inside a sandbox.
- **A step defined over the SVG previews.** Rejected. A renderer that writes another format would not fit it.
- **Faces from the committed font files, or from the machine.** Rejected. The first drops text in silence, and the second draws in a font the brand never named.
- **Refusing a page whose text has no face.** Rejected. It could never fire, and text could still vanish.
- **A before-and-after from a base commit.** Left out. The word is the record of change over time's, for what a lock's move changes (DEC-003 point 8). It would read as nothing changed in ordinary cases, such as a change to a translation alone. A person may try a move in the working tree, which stands in for no before-and-after.
- **A folder the caller names.** Left out. No caller needs one, and a path into another worktree or behind a link could still reach a commit.

## Implications

- **One edit to an accepted record,** refined in place once this record is accepted, and citing it. Accepting this record accepts the edit (COR-066 point 5).
  - **The record of files and validation's point 1.** Its last bullet reads: "What a render, an export or the viewing step makes that is not committed, such as a preview, an export nobody has handed out or a page's image, lies in the methodology's own folder". The rest of the bullet stands.
- **The change that builds the command** (#2674) settles how the step learns what the tool dropped (point 3), and an image's size (point 5). It sees to it that the wheel reaches a machine before an offline run, and measures what Context lists as not measured. A route for the wheel that needs a change to the backbone is a decision of its own. [project-kit#2675](https://github.com/aleskalfas/project-kit/issues/2675) builds the reviewer.
- **Revisit this record:**
  - if anything Context lists as not measured fails, which reopens the tool: the wheel does not run there, what it draws is too poor to judge, or the step cannot learn what the tool dropped;
  - if the licence of the resvg the wheel bundles does not let the capability use it.
