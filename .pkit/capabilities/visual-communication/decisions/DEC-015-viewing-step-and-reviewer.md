---
id: DEC-015
title: A piece's drawn pages are seen as images nothing else reads, and a reviewer reports what no check measures
status: proposed
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** whoever builds a piece can see its pages as images while it is built. The *viewing step* draws what a renderer drew, and writes only images and the boxes beside them. It is no plugin, and no check, export or producer reads what it writes. Its tool today is resvg, a pinned Python wheel that reads the SVG renderer's pages, so it needs no outside program and no network. The images promise nothing about their pixels. `graphic-design-reviewer` looks at them on demand, reports what no check measures, and only advises.

## Context

A piece's drawn result is seen today only by opening a preview or an export. Whoever builds a piece learns that the checks passed, not what the page shows ([project-kit#2672](https://github.com/aleskalfas/project-kit/issues/2672)). The records already leave part of the drawing to a reviewer, such as a text over a picture ([visual-communication:DEC-004-brands-and-notations] point 8). The founding record leaves the capability's agents to later records ([visual-communication:DEC-001-visual-communication-discipline], Implications).

Three tools were tried on real pages, on one Mac: the starter's reference pieces, one in Czech, and one with a produced picture.
- **resvg over the SVG** draws a page in about 50 ms from a wheel of under 2 MB. It gives the same bytes in separate processes, shows pictures, and ran with the network denied in hand-written sandboxes.
- **Headless Chrome over the SVG** draws no better: by eye the two differ in edge smoothing, with no shift of layout. It takes about a second a page and weighs 2.1 GB. It cannot be pinned, and it died in every sandbox tried.
- **pdfium over the PDF** shows no picture, since the PDF renderer refuses images.
- **resvg ignores `@font-face`.** Left to the committed font files, it dropped every text whose family differs from the file's own name, and said nothing. Given the page's faces under the names their rules give, it matched Chrome by eye.

What was not measured:
- **Linux,** and whether it gives the same pixels.
- **A detailed picture.** The one picture drawn was a solid square, so resampling is unknown.
- **The real sandbox profile.** The sandboxes tried were written by hand.
- **The bundled resvg's licence.** The wheel's own licence reads as MIT, and the resvg it bundles was not read.

## Decision

**A person or an agent sees a piece's drawn pages through a viewing step that is no plugin and takes no part in the seam. It draws a renderer's output as images, by page, language and key, and writes nothing committed. Its tool today is resvg, a pinned Python wheel behind one module of the capability. Its images promise nothing about their pixels. `graphic-design-reviewer`, read-only and advisory, looks at them on demand and reports what no check measures.**

### 1. The viewing step draws a renderer's output, outside the seam

- **What it is.** The *viewing step* draws, as an image, what a renderer drew for one page, in one language, under one key ([visual-communication:DEC-004-brands-and-notations] point 3). It is defined over that drawn output, never over one format, so a later renderer fits it. Its command is `pkit visual look`.
- **No plugin.** It is none of the three kinds, and takes no part in the seam ([visual-communication:DEC-005-engine-and-plugins] points 7 and 9). So it has no declaration and no version of its own.
- **Read by a person or an agent alone.** No check, export or producer reads what it writes.
- **It runs no program.** No helper or producer runs ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 1). A produced picture is drawn as it stands, stale or not.

### 2. Its tool today is resvg, a pinned Python wheel, behind one module

- **Over the SVG.** The tool reads the SVG renderer's pages. That is how the step works today, not what the step is.
- **Pinned, and in the command's own process.** The wheel is pinned exactly, as the capability's scripts pin their packages, and runs as a library. So drawing needs no outside program, no other runtime and no sandbox change ([visual-communication:DEC-002-files-and-validation] point 8).
- **Offline.** Drawing reads no network. A base commit (point 5) comes from the clone's history, and one the clone lacks is refused.
- **One narrow module.** One module of the capability holds the tool. It takes a renderer's drawn page and gives an image, and nothing else calls the wheel. No facility of the backbone serves it.
- **A browser** comes only with the HTML renderer, in that Feature's own record ([project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570)). A tool that renderer needs goes behind the same module.
- **Outside programs, for this step alone.** The change that builds the first real producer decides what the capability adds to the permission model for a producer's outside programs (DEC-006, Implications). This step is no producer and calls none to draw, so it adds nothing. The question stays open for a producer, and for a renderer that calls such a program.

### 3. The faces come from the page, and a missing face refuses

- **The page's own faces.** The step takes each face from the page's `@font-face` rules, under the family and the weight its rule names. It reads no font of the machine ([visual-communication:DEC-004-brands-and-notations] point 9).
- **A missing face refuses.** A page with a text drawn in a family that has no face is refused, naming the family and the page. resvg would otherwise drop that text in silence.
- **A family only listed needs no face.** A text lists every family of its role, and the page holds a face only for those it is drawn in.

### 4. It reads under the lock, and writes nothing committed

- **Under the lock.** It computes the scenes under the lock `piece.yaml` holds, and never moves it. It refuses a piece with no lock, naming the render that writes one.
- **What it writes.** Only the images and the boxes beside them (point 5). This record names its command the writer of both ([visual-communication:DEC-002-files-and-validation] point 9).
- **Where.** In the clone's local folder, or a folder its caller names. A folder the caller names lies outside the repository, or is one version control ignores, so nothing it writes reaches a commit.
- **Never an export.** It never goes through an export run, which takes a number and rewrites the record of exports (DEC-006 point 7). It writes no record of findings, and records no location.

### 5. What it draws

- **The caller picks** pages, languages and modes. By default it draws the source language, in the first combination of modes the piece names, in key order. That is the combination of defaults wherever the piece names it.
- **The size.** Each image is 1568 px on its long edge.
- **Boxes.** Beside each image lies each element's box, in the image's pixels, with its trace id (DEC-005 point 5). So a finding names the element, and through it the field.
- **A before-and-after.** Given a base commit, it draws the piece from that commit's files and from the working tree, in one run on one machine. It keeps both images of each page that differs, and none of the rest. A page on one side alone differs.
- **What a before-and-after shows.** The installed capability draws both sides. So it shows what the files changed, never what a change of the engine or of a renderer did.
- **Reference renders.** It reaches a library's reference renders ([visual-communication:DEC-007-starter-library] point 3) as it reaches a piece. Where the capability is authored, they lie in its test fixtures, outside any location.

### 6. It promises nothing about pixels

- **No contract.** The images may change with the tool, its version or the machine. No test and no check compares them as a contract, and no reference image is kept.
- **What a test holds:** one image for each page, language and key, its size, that it is not blank, each refusal, and which pages a before-and-after keeps.
- **The one comparison** is the before-and-after's, inside one run on one machine. It only picks pages, and promises nothing beyond that run.
- **It shows this tool's drawing.** A face rule a browser could not read may still draw here.

### 7. The reviewer's first form

- **Whose.** `graphic-design-reviewer` is the capability's agent, since its work implies the capability's discipline (COR-026). It is read-only and advisory.
- **On demand.** A session dispatches it, since a builder starts no reviewer ([project-management:DEC-063-task-builder] point 4).
- **Its remit** is what no check measures on the drawn result:
  - a closed list of gross faults: a part missing or blank, a wrong font, text over text, a wrong picture
  - a label over a picture (DEC-004 point 8)
  - overlaps and alignment
  - a drawing that disagrees with a passing check
- **Each finding** names the page and the element's trace id.
- **Advice only.** Its findings join no validation and hold no merge. The starter's owner judges a component's entry, and the findings only inform that review (DEC-007 point 3).
- **It needs a harness that reads images** (COR-014). Where the harness reads none, it stops and says so, so a page nobody saw never reads as clean.
- **Left to others.** Who judges a piece against the rules of visual communication is [project-kit#2583](https://github.com/aleskalfas/project-kit/issues/2583)'s question. The boundaries among the capability's three agents are [project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584)'s record, which cites this one.

## Rationale

**Why no plugin.** A plugin meets the engine at the seam, and no plugin reads another's output (DEC-005 point 7). This step reads a renderer's output, and nothing downstream reads its own. A plugin also pins reference outputs to its version (DEC-005 point 9), which is the promise point 6 refuses.

**Why resvg for now.** It is the one tool tried that shows pictures and can be pinned. Chrome draws no better, and would be a large outside program that moves with the machine. pdfium cannot show a picture while the PDF renderer refuses images. What was not measured costs little to get wrong, since the tool sits behind one module and promises no pixels.

**Why the faces come from the page, and a missing face refuses.** The page's faces are what the page asks for, so a character missing from a face shows in the image. A dropped text leaves empty space, which an agent would take for missing content. A refusal names the cause.

**Why 1568 px.** A page's smallest measured text, 16 px, lands near 20 px and reads easily. On a page twice as wide, it lands near 10 px and still reads.

**Why no promise about pixels.** A test that held pixels would tie the capability to a tool chosen for now, and fail on a machine nobody measured. A reader needs the page, not its bytes. So the tool can change with no change of contract.

**Why the installed capability draws both sides.** Drawing the base with that commit's own code would need that code's dependencies, and older code to run. The record of a library's needed release rejects such a run ([visual-communication:DEC-014-own-library-needed-release], Alternatives considered). A change of the engine is reviewed on the drawing it gives, page by page.

**Why the reviewer advises, on demand.** It reads a drawing by judgement, and a reading of taste never fails (DEC-002 point 7). A required review needs a way to find a piece's change, and rules to cite, so it waits for them ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)).

### Alternatives considered

- **Headless Chrome now.** Rejected. It draws no better, cannot be pinned, and stops inside a sandbox.
- **pdfium over the PDF.** Rejected. A page shows no picture while the PDF renderer refuses images.
- **A fourth kind of plugin.** Rejected. Nothing reads its output, so a seam would carry nothing.
- **A step defined over the SVG previews.** Rejected. A renderer of another medium would not fit it.
- **Drawing through an export.** Rejected. Every look would take a number and rewrite the record of exports.
- **Faces from the committed font files, or from the machine.** Rejected. The first drops text in silence, and the second draws in a font the brand never named.
- **Refusing a text that merely lists a family with no face.** Rejected. It would refuse a sound page of any brand with a second family.
- **Reference images in the tests.** Rejected. They would make a promise of pixels.
- **A required review at the merge now.** Not chosen. Its record comes first ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)).

## Implications

- **Edits to accepted records,** each citing this record once it is accepted. A person accepts each edit (the decisions README, "Refining an accepted record").
  - **The record of files and validation's point 1.** Its last bullet reads: "What a render, an export or the viewing step makes that is not committed, such as a preview, an export nobody has handed out or a page's image, lies in the methodology's own folder". The rest of the bullet stands. It adds: "The viewing step may write to a folder its caller names instead, outside the repository or ignored by version control".
  - **Its point 9.** "Reads or writes" adds: "The viewing step's command also writes to a folder its caller names, which may lie outside the project".
  - **No edit to the record of work outside the engine and outputs, or to the starter's record.** The first's question stays open for a producer (point 2), and the second's review stays its owner's (point 7).
- **The change that builds the command** ([project-kit#2674](https://github.com/aleskalfas/project-kit/issues/2674)):
  - It reads the licence of the resvg the wheel bundles before it pins the wheel.
  - It sees to it that the wheel reaches a machine before an offline run. The methodology provisions only query commands, which only read, and this command writes. So the change provisions the wheel from within the capability, with no change to the backbone. A query command whose script pins it is one way.
  - It measures the real sandbox profile, and Linux. Its tests are the first run on Linux.
  - Its criterion on a family with no face reads as point 3 says: a family the text is drawn in.
- **The reviewer** is built by [project-kit#2675](https://github.com/aleskalfas/project-kit/issues/2675).
- **Revisit this record:**
  - if the wheel does not run on Linux or in the real sandbox;
  - if a detailed picture draws too poorly to judge;
  - when the HTML renderer's record brings a browser, which may replace resvg behind the same module.
