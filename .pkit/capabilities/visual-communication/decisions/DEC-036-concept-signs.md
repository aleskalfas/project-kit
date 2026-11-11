---
id: DEC-036
title: A concept shows a sign beside its colour, an icon its notation holds or a shape the foundations declare
status: proposed
date: 2026-11-11
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a concept that a piece shows by its colour shows a *sign* beside it too, so colour is never the only thing that tells it apart. The sign is an outline: an icon its notation holds, or else a shape the foundations declare. An item's component draws it in a part of its own, and a text part may draw it before a run, with a ground behind the run. The check asks for attention where a component or a notation leaves a concept to its colour alone, and where two concepts of a piece share one sign. For example, a store drawn as a green card shows the notation's store icon in its corner, in the green family's line colour, and a run that names the store in a sentence starts with the same icon.

## Context

The record of brands and notations lets a concept map to an icon among its notation's marks, tinted by a role of its family, and to a shape from a list the foundations declare, so that colour is never the only sign ([visual-communication:DEC-004-brands-and-notations] point 10). No file holds either yet, and no part draws either:
- **The record of runs** leaves a sign beside a run's colour, and a finding where two concepts of a piece share a family, to the change that builds icons and a legend ([visual-communication:DEC-012-text-runs], Implications).
- **The record of picture files** leaves a notation's marks to that change, and reads only PNG and JPEG files ([visual-communication:DEC-025-picture-files] point 5 and Implications).
- **The showcase deck** told the core's lines from yours by colour alone, which a reviewer caught under forced colours and a person mended by hand ([project-kit#2843](https://github.com/aleskalfas/project-kit/issues/2843)).

The Feature this record serves asks for a legend drawn from a piece's notations, and for a run that names a concept to show a sign beside its colour, as an item does ([project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576)). The questions are its Task's ([project-kit#2984](https://github.com/aleskalfas/project-kit/issues/2984)).

Terms:
- A *sign* is what shows a concept beside its colour: its icon, or its shape where it maps no icon.
- A run's *ground* is a paint drawn behind the run, as a chip lies behind its label.

## Decision

**A concept shows a sign beside its colour, an outline its notation or the foundations declare, which an item's component draws in a part and a text part draws before a run.**

### 1. A sign is an outline: an icon its notation holds, or a shape the foundations declare

- **One form.** An icon and a shape are each a closed outline in SVG's path data, within a square whose side the outline names.
- **Who holds them.** A notation holds its icons in its own file. The foundations declare each shape by a name, which a notation maps a concept to.
- **No role.** No brand gives an outline a value, so a sign reads the same under every brand, and only its paints follow the brand.
- **Fitted by its square,** whole, centred and as large as its frame allows, so every sign takes the same room ([visual-communication:DEC-025-picture-files] point 6).
- **The scene holds it as a path,** the primitive [visual-communication:DEC-005-engine-and-plugins] point 5 keeps for later, so a renderer knows no sign by name.

### 2. A sign part draws an item's concept's sign

- **Which concept.** A sign part draws the sign of the concept its instance names, or, where the instance takes its family from the instance it sits in, of that instance's concept ([visual-communication:DEC-010-list-item-fields] point 6).
- **Painted as a box is,** with a fill, a stroke and the stroke's width, and an override reaches it as it reaches a box ([visual-communication:DEC-001-visual-communication-discipline] point 6).
- **None to draw.** Where the instance has no such concept, or the concept maps no sign, the part is not drawn and has zero size at its place, as an empty picture has (DEC-025 point 1).
- **A state changes the paint, never the sign.**
- **The component places it,** as it places any part.

### 3. A text part may draw a run's sign, and a ground behind a run

- **Chosen by the run's style.** Beside its typography role and its paint, a text part that shows a field of runs chooses by each run's style whether a run that names a concept draws its sign, and the run's ground, a paint or none. A text part that chooses neither draws every run as before.
- **The sign** lies before the run's first character that is no space or line feed, on that character's line, in the run's own paint. No line breaks between the two.
- **The ground** lies behind each piece of the run on each line it spans, its sign included, and is the fill the run is measured against ([visual-communication:DEC-004-brands-and-notations] point 8).
- **Measured within the line.** The engine measures the sign in the run's typography role, and gives the ground room at the run's two ends, within the line (DEC-012 point 4).
- **One span for runs that run on.** Runs next to each other in one paragraph that name one concept and draw its sign draw one sign, before the first. Those that take one ground take it once, with room at the span's two ends alone.
- **Held with the run.** The scene's line holds each run's sign and ground with the run's piece, and the room the engine gave them, and each renderer draws them with the run.

### 4. Under forced colours, a sign keeps its outline

- **No rule of its own.** A sign and a ground are fills and strokes, which [visual-communication:DEC-023-html-page-modes] point 7 gives the reader's colours in the HTML page, so a sign's outline shows in the reader's text colour.

### 5. A reader who does not see the page gets a concept from words alone

- **A sign and a ground take no place in the reading order,** as no shape does ([visual-communication:DEC-033-structure-for-readers] point 6).
- **Words content writes give the concept,** such as an instance's text (DEC-033 point 5) or a legend's labels (point 6).

### 6. A legend reads content alone, and content gives each concept's label

- **Its entries are items** content lists, each naming a concept, so each draws its concept's family and sign as any item does (point 2).
- **Its labels are content,** given in each language as any text is (DEC-001 point 3). A notation gives no concept a label, for now.

### 7. What breaks, and which versions rise

- **Removing or renaming a shape breaks the foundations,** as any name a library built on them names ([visual-communication:DEC-003-change-over-time] point 6). A new shape breaks nothing.
- **Nothing else here breaks:** an outline, a concept's sign or family, a sign part, and a text part's choice of a sign or a ground each change only how a piece looks.
- **The format number stays 1.** Each addition is optional, and each finding that fails reads something format 1 did not hold (DEC-003 point 3).
- **The seam's version rises** in the change that first gives the scene its shape for a path and for a run's sign and ground, and a change that fills that shape raises nothing (DEC-005 point 8). Each renderer's version rises as it comes to draw them (DEC-005 point 9).

### 8. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, and elsewhere asks for attention, naming who can correct it ([visual-communication:DEC-002-files-and-validation] point 7).
- **Fails validation:**
  - in a notation: an icon that is no closed outline within its square, or a shape the foundations do not declare
  - in the foundations: a shape whose outline is no closed outline within its square
  - at a piece: a sign none of whose paints reaches WCAG's contrast for other marks against the fill under it, as a drawn text below its own fails (DEC-004 point 8). A sign over a picture is not measured.
- **Asks for attention, never failing,** each once, where its owner mends it:
  - in a component's version: a part painted from its family where the component holds no sign part, and a text part that paints a run style from the run's family with no sign chosen for it. Each leaves a concept to its colour alone.
  - in a notation's version: a concept that maps no sign.
  - at a piece, in each language: two concepts its content names whose signs are one outline, naming both and their notations.

## Rationale

**Point 1, an outline.** One form for icons and shapes gives renderers one new primitive, sharp at every size and in print, with a fill and a stroke the HTML page already gives the reader's colours. A later icon or shape then comes in a release of its notation or of the foundations, with no renderer changed, and the path is SVG's, as every property of the scene is (DEC-005 point 5). A sign tells concepts apart only while every brand draws it alike. The cost: an icon drawn as strokes, as many icon sets are, is turned into outlines first, and an icon holds one colour and no shading.

**Point 2, an item's sign.** The component decides how its instance looks (DEC-001 point 6), and only it knows where a sign fits. The concept the family comes from is the one whose colour the part shows, so the sign says what the colour says. A state says a condition, not what a thing is. One part serves an icon and a shape, as a run's sign does.

**Point 3, a run's sign and ground.** A run has no frame of its own (DEC-012, Alternatives), so the text part sets its sign and ground as it sets its role and paint. Chosen, never drawn by default, they leave every text drawn before as it was. Kept with the run's first letter, a sign reads before the words it marks, and a break never strands it. A span split for its styles is still one thing. Held with the run's piece, the sign and the ground move with the run wherever a renderer sets it, as the HTML page sets runs at the browser's widths ([visual-communication:DEC-020-html-page-drawing] point 2). A ground puts a run's family's text on its family's fill, the pair the foundations promise, on any surface.

**Point 4, forced colours.** There every colour is the reader's, so a sign's outline is what still tells concepts apart.

**Point 5, a reader who does not see.** Colour reaches no such reader either. A sign read out as its concept's label would need the concept's words outside the content, which wait for translation (DEC-004 point 10). The cost: a run's concept reaches that reader only where its words say it.

**Point 6, a legend.** Words are content, translated with it. A content file's top holds only its top's fields, so a key for labels there would refuse a field of that name (DEC-002 point 4). Entries as items need nothing new. The cost: an author writes each legend's entries in each language, and nothing checks them against the page.

**Point 7, the seam.** A renderer built before would draw no sign and no ground, with no error.

**Point 8, the checks.** Signs are new, so their failures refuse nothing written before. Under forced colours, or for a reader without colour vision, no colour tells concepts apart, so a sign is asked of every concept, not only of those past the families' bound, and the bound's finding becomes two concepts with one sign. Each attention lies once, where its owner mends it, as DEC-033 point 11 has it. The shared sign is judged at the piece, where two notations meet.

### Alternatives considered

- **An icon as a PNG drawn in one colour through its alpha:** every renderer would learn a new operation, an icon would blur in print, and forced colours would need a rule of their own.
- **An SVG file as an icon:** a new encoding, with refusals of its own, such as scripts and outside references. DEC-025 leaves it open.
- **A font of icons:** a reader's tools read its glyphs as letters, and a brand's fonts would carry a notation's meaning.
- **An icon in its own colours:** the notation would hold values.
- **Shapes as names each renderer draws:** a new shape would wait for every renderer.
- **A shape a brand restyles:** two brands could draw two concepts' shapes alike.
- **A concept's shape as its item's outline:** a card would reflow its text into a diamond, and the look is the component's.
- **A part for the icon and one for the shape:** a concept that maps both would show both, and no condition reads which a concept maps.
- **A sign painted only from its family's members,** as DEC-004 point 10 words it: a component could not draw it in a shared role, such as its text's, which an override already reaches on every other part.
- **A run's sign and ground as primitives placed apart from the text:** a renderer that sets runs at its own widths would set them apart from the run.
- **A run's sign drawn wherever its concept shows by colour, unchosen:** every text drawn before would move.
- **A run's sign after the run, or at each line it spans:** it would read after the words it marks, or mark one span many times.
- **A run's ground from the brand, by a role of its own:** a run style's look is its component's (DEC-012 point 2).
- **Labels in the notation, in each language:** a library would hold the words a piece shows, which DEC-004 point 10 leaves to translation.
- **A legend the engine fills from a page's concepts:** a list the engine computes, which no part repeats over today (DEC-005 point 2), with an order to decide, and labels keyed by concept that content still writes in each language.
- **The colour-alone finding at each instance of a piece:** it would repeat for every instance of a released component, naming an owner who mends it once.
- **The bound failing validation:** it would refuse a piece format 1 accepted (DEC-003 point 3).
- **The bound judged in each notation alone:** two notations meet only in a piece.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-004 point 10, "What a concept maps to": "an icon among the notation's marks" comes to read "an icon the notation holds as an outline", and the point comes to add that a concept's sign is its icon, or else its shape (point 1).
  - DEC-004 point 10, "Colour is never the only sign": "An icon or a shape tells the rest apart" comes to say that every concept shown by colour shows a sign, and that the check asks for attention where a component or a notation leaves one to its colour, and where two concepts of a piece share a sign (point 8).
  - DEC-004 point 10, "An icon follows the brand": "tinted by a role of its concept's family" comes to read "painted as its part or its run is" (points 2 and 3).
  - DEC-004 point 10, "A notation's file", comes to add that it holds its icons' outlines and gives no concept a label, for now, a legend's labels being content (points 1 and 6).
  - DEC-004 point 8, "Checked as drawn", comes to add that each sign is measured against the fill under it, at the level for other marks (point 8).
  - DEC-005 point 1, "A choice is declared, never computed": the choice by a run's style comes to set also whether the run draws its concept's sign, and its ground (point 3).
  - DEC-005 point 5, "Primitives at the leaves": the path comes to draw a sign, its square mapped into its frame (point 1), and a text's runs come to hold their signs and grounds, with the room the engine gave them (point 3).
  - DEC-012 point 2, "Only how the run is set": a run's word comes to choose also whether the run draws its concept's sign, and its ground (point 3).
  - DEC-012 point 4 comes to add that a run's sign is measured within its line, before its first character that is no space or line feed, with no break between them, and that a ground has room at its span's ends (point 3).
  - DEC-012 point 8, "a choice by a run's style anywhere but the typography role and paint", comes to allow its sign and its ground too.
  - DEC-012's Implications: the bullet on a sign beside a run's colour leaves "Left to later changes", and they come to say this record decides it.
  - DEC-025's Implications, "A notation's marks", come to say that a notation's icons are outlines this record decides, and that its other marks wait.
- **Read against this record, and left as they stand:** DEC-001 point 5, DEC-002 point 4, DEC-003 point 3, DEC-010 point 6, DEC-020 point 2, DEC-023 point 7, DEC-025 point 5, [visual-communication:DEC-027-forced-colours-viewing] and DEC-033 point 6.
- **The Tasks that build it,** filed under [project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576) once this record is accepted, each bringing the pages it changes:
  - signs: the foundations' shapes, a notation's icons, the sign part, and the path in the scene and each renderer (points 1, 2 and 4)
  - a run's sign and ground (point 3)
  - the checks of point 8
  - the starter's legend and its components' sign parts, with the showcase deck's install slide taking a legend in place of its line that names its colours (points 2 and 6)
- **#2576's body,** edited once this record is accepted: its criterion "A legend draws from a piece's notations" comes to say that a legend's entries name concepts, whose families and signs come from the piece's notations (point 6).
- **Left to later changes:** a picture as an icon, a PNG or an SVG file; a shape a component names itself; a concept's label from its notation, with translation, which revisits points 5 and 6; a legend the engine fills.
- **Revisit this record** if an icon a project needs cannot be drawn as a filled outline, or a browser loses a sign's outline under forced colours.
