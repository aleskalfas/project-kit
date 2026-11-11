---
id: DEC-036
title: A concept shows a sign beside its colour, an icon its notation holds or a shape the foundations declare
status: proposed
date: 2026-11-11
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a concept that a piece shows by its colour shows a *sign* beside it too, so colour is never the only thing that tells it apart. The sign is an icon its notation holds, drawn in a colour of the concept's family, or a shape the foundations declare. An item's component draws the sign in a part of its own, and a text part may draw it before a run, with a ground of the family's fill behind the run. The check asks for attention where a concept shows by colour alone, or where two concepts share a sign. For example, a store drawn as a green card shows the notation's store icon in its corner, in the green family's line colour, and a run that names the store in a sentence starts with the same icon.

## Context

The record of brands and notations lets a concept map to an icon among its notation's marks, tinted by a role of its family, and to a shape from a list the foundations declare, so that colour is never the only sign ([visual-communication:DEC-004-brands-and-notations] point 10). No file holds either yet, and no part draws either:
- **The record of runs** leaves a sign beside a run's colour, and a finding where two concepts of a piece share a family, to the change that builds icons and a legend ([visual-communication:DEC-012-text-runs], Implications).
- **The record of picture files** leaves a notation's marks to that change, and reads only PNG and JPEG files ([visual-communication:DEC-025-picture-files] point 5 and Implications).
- **The showcase deck** told the core's lines from yours by colour alone, which a reviewer caught under forced colours and a person mended by hand ([project-kit#2843](https://github.com/aleskalfas/project-kit/issues/2843)).

The Feature this record serves asks for a legend drawn from a piece's notations, and for a run that names a concept to show a sign beside its colour, as an item does ([project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576)). The questions are its Task's ([project-kit#2984](https://github.com/aleskalfas/project-kit/issues/2984)).

Terms:
- A *sign* is a concept's icon or its shape, drawn beside the colour its family gives.
- A *tint* is the paint an image is drawn in, in place of its own colours.
- A run's *ground* is a paint drawn behind the run, as a chip lies behind its label.

## Decision

**A concept shows a sign beside its colour, an icon its notation holds or a shape the foundations declare, which an item's component draws in a part and a text part draws before a run.**

### 1. An icon is a PNG the notation holds, drawn in its tint through its alpha

- **The file.** A concept's icon is a picture file of its notation's version, named by its bare name, under the rules a library's own picture files take ([visual-communication:DEC-025-picture-files] points 2 and 3).
- **A PNG with transparency,** of an encoding DEC-025 point 5 reads.
- **A tint fills its alpha.** The renderer draws the tint's colour wherever the icon is not transparent, in the share its alpha gives, and none of the icon's own colours.
- **One file under every brand and in every mode.** The tint carries the brand's colour.
- **A fifth source.** An image part may show its instance's concept's icon, beside the four sources of DEC-025 point 1, and names its tint, a paint as a box's fill is. Only an image of that source takes a tint, for now.
- **The scene names the icon as a picture file of a library's version, with its tint, which stays a role** ([visual-communication:DEC-005-engine-and-plugins] point 5, DEC-025 point 7). Each renderer fills the alpha with the role's value in each mode it draws, or reports a loss (DEC-005 point 9).

### 2. A shape is an outline the foundations declare, drawn by a part of its own

- **The foundations declare each shape** by a name and an outline: a closed path in a square of side one, in SVG's path data. A notation maps a concept to a shape by its name.
- **A shape is no role.** No brand gives it a value, so it reads the same under every brand.
- **A shape part draws its instance's concept's shape,** painted as a box is, with a fill, a stroke and the stroke's width.
- **Fitted as a picture is:** whole, centred and as large as its frame allows, keeping its proportions (DEC-025 point 6).
- **The scene holds it as a path,** the primitive DEC-005 point 5 keeps for later, its outline mapped into the part's frame, so a renderer knows no shape by name.

### 3. A part of an item's component draws its concept's sign

- **Which concept.** A part draws the sign of the concept the instance names, or, where the instance takes its family from the instance it sits in, of that instance's concept ([visual-communication:DEC-010-list-item-fields] point 6).
- **None to draw.** Where no concept gives the instance its family, or the concept maps nothing of the part's kind, the part is not drawn and has zero size at its place, as an empty picture has (DEC-025 point 1).
- **A state changes the paint, never the sign.** A state that gives the instance another family paints its sign in that family.
- **The component places it,** as it places any part.

### 4. A text part may draw a run's sign before it, and a ground behind it

- **Chosen by the run's style.** Beside its typography role and its paint, a text part that shows a field of runs chooses by each run's style whether a run that names a concept draws its sign, and its ground, a paint or none. A text part that chooses neither draws every run as before.
- **The sign** is the concept's icon, or its shape where it maps no icon, in the run's own paint.
- **Before the run's first character, on its line.** No line breaks between the two, and the engine measures the sign within the line, in the run's typography role.
- **One sign for runs that run on.** Runs next to each other in one paragraph that name one concept and draw a sign draw one, before the first.
- **The ground** lies behind each piece of the run on each line it spans, its sign included, and is the fill the run is measured against ([visual-communication:DEC-004-brands-and-notations] point 8). The engine gives it room at the run's two ends, measured within the line.
- **Primitives of their own.** The scene holds each run's sign and ground as primitives beside the text, placed where the engine measured them: a ground as a box drawn before the text, a sign as a tinted image or a path.

### 5. Under forced colours, a tinted picture takes the reader's text colour

- **In the HTML page,** the file's rule for forced colours gives each tinted picture the reader's text colour, as it gives each line ([visual-communication:DEC-023-html-page-modes] point 7).
- **A shape and a ground are fills,** which that point gives the reader's colours as it stands.

### 6. A reader who does not see the page gets a sign's meaning from words alone

- **An icon is a picture its component chose,** so its image part names the field of its text or says it needs none, as one of `role` does ([visual-communication:DEC-033-structure-for-readers] point 5).
- **A shape, a run's sign and a ground take no place in the reading order,** as no shape does (DEC-033 point 6).
- **Words content writes say the rest,** such as an instance's text (DEC-033 point 5) or a legend's labels (point 7).

### 7. A legend reads content alone, and content gives each concept's label

- **Its entries are items** content lists, each naming a concept, so each takes its concept's family and sign as any item does (point 3).
- **Its labels are content,** given in each language as any text is ([visual-communication:DEC-001-visual-communication-discipline] point 3). A notation gives no concept a label.

### 8. What breaks, and which versions rise

- **Removing or renaming a shape breaks the foundations,** as any name a library built on them names ([visual-communication:DEC-003-change-over-time] point 6). A new shape breaks nothing.
- **Nothing else here breaks:** a concept's icon, shape or family, a part that draws a sign, a text part's choice of a sign or a ground, and a shape's outline each change only how a piece looks.
- **The format number stays 1.** Each addition is optional, and each finding that fails reads something format 1 did not hold (DEC-003 point 3).
- **The seam's version rises once,** in the change that first gives the scene a tint, a path, or a run's sign and ground (DEC-005 point 8). Each renderer's version rises as it comes to draw them (DEC-005 point 9).

### 9. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, and elsewhere asks for attention, naming who can correct it ([visual-communication:DEC-002-files-and-validation] point 7).
- **Fails validation:**
  - in a notation: an icon that names no picture file of its version, or one with no transparency; a shape the foundations do not declare
  - in the foundations: an outline that is no closed path inside the square of side one
  - in a component: an image of a concept's icon with no tint, or a tint on an image of another source
  - at a piece: a sign below WCAG's contrast for other marks against the fill under it, as a drawn text below its own fails (DEC-004 point 8). A sign over a picture is not measured.
- **Asks for attention, never failing:**
  - at a piece: a concept shown by its colour with no sign beside it. That is an instance whose part paints from the family its concept gives, while no part of it or of what it holds draws that concept's sign, or a run whose paint reads its concept's family and that draws no sign. It names the component's owner, or the notation's where the concept maps no sign the part draws.
  - at a piece, in each language: two concepts its content names that share their sign, the same icon or none and the same shape or none. It names both and their notations, and says whether they share a family too.

## Rationale

**Point 1, the icon.** A tint through the alpha keeps the icon a PNG, which every renderer already reads, and SVG, CSS and PDF each fill a picture's alpha with one colour. A tint that kept the icon's own shading would blend in each medium its own way. The notation holds meaning and no values (DEC-001 point 5), so the tint's role carries the brand. The cost: a PNG blurs past its pixels (DEC-025 point 6), so a notation saves each icon at its largest size.

**Point 2, the shape.** The foundations already declare the families a notation maps to (DEC-004 point 10). Declared as an outline, a later shape comes in a release of the foundations alone, with no renderer changed, and the path is SVG's, as every property of the scene is (DEC-005 point 5). A shape tells concepts apart only while every brand draws it alike.

**Point 3, an item's sign.** The component decides how its instance looks ([visual-communication:DEC-001-visual-communication-discipline] point 6), and only it knows where a sign fits. The concept that gives the family is the one whose colour the part shows, so the sign says what the colour says. A state says a condition, not what a thing is.

**Point 4, a run's sign and ground.** A run has no frame of its own (DEC-012, Alternatives), so the text part sets its sign and ground as it sets its role and paint. Chosen, never drawn by default, they leave every text drawn before as it was. Kept with the run's first character, a sign reads before the words it marks, and a break never strands it at a line's end. A span split for its styles is still one thing. A renderer already draws boxes, images and paths, so only the engine learns where a run's sign goes. A ground puts a run's family's text on its family's fill, the pair the foundations promise, on any surface.

**Point 5, forced colours.** There every colour is the reader's, so a sign is what still tells concepts apart. A tinted picture is a mark in one colour, as a line is, and left to the browser it may keep the brand's colour on the reader's ground, or take that ground, and fade.

**Point 6, a reader who does not see.** Colour reaches no such reader either. DEC-033 already gives every picture and shape its place on the reader's side, and a label read out for every sign would need a concept's words outside the content, which wait for translation (DEC-004 point 10). The cost: a run's concept, and an icon marked as needing none, reach that reader only where words say them.

**Point 7, a legend.** Words are content, translated with it. A content file's top holds only its top's fields, so a key for labels there would refuse a field of that name (DEC-002 point 4). Entries as items need nothing new. The cost: an author writes each legend's entries in each language, and nothing checks them against the page.

**Point 8, what breaks.** A notation names a shape, so it breaks as a role does. The seam rises because a renderer built before would draw a tinted icon in its own colours, with no error, as DEC-025 points out for picture files.

**Point 9, the checks.** Signs are new, so their failures refuse nothing written before. A concept shown by colour alone, and two concepts with one sign, are judged on content format 1 accepted, so they ask for attention. The bound is read at the piece, where two notations meet.

### Alternatives considered

- **An SVG icon:** sharp at every size, but a new encoding every renderer must draw alike, with refusals of its own, such as scripts and outside references. DEC-025 leaves it open, and it comes later as an addition.
- **A font of icons:** a reader's tools read its glyphs as letters, and a brand's fonts would carry a notation's meaning.
- **An icon in its own colours, one file for each brand and mode:** the notation would hold values.
- **A tint that multiplies the icon's colours:** a dark icon tinted for a dark mode would vanish.
- **Shapes as names each renderer draws:** a new shape would wait for every renderer.
- **A shape a brand restyles:** two brands could draw two concepts' shapes alike.
- **A concept's shape as its item's outline:** a card would reflow its text to fit a diamond, and the look is the component's.
- **A run's sign drawn wherever its concept shows by colour, unchosen:** every text drawn before would move.
- **A run's sign after the run, or at each line it spans:** it would read after the words it marks, or mark one span many times.
- **A run's ground from the brand, by a role of its own:** a run style's look is the component's (DEC-012 point 2).
- **A run's sign that reads as its concept's label:** the label would come from outside the content.
- **Labels in the notation, in each language:** a library would hold the words a piece shows, which DEC-004 point 10 leaves to translation.
- **A legend the engine fills from a page's concepts:** its labels would have to come from outside the content.
- **The bound failing validation:** it would refuse a piece format 1 accepted (DEC-003 point 3).
- **The bound judged in each notation alone:** two notations meet only in a piece.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-004 point 10, "What a concept maps to", comes to add that an icon is a PNG with transparency in the notation's version, and a shape a name whose outline the foundations declare (points 1 and 2).
  - DEC-004 point 10, "Colour is never the only sign", comes to add that the check asks for attention where a concept shows by colour with no sign, and where two concepts of a piece share their sign (point 9).
  - DEC-004 point 10, "An icon follows the brand", comes to add that its tint fills its alpha, one file under every brand (point 1).
  - DEC-004 point 10, "A notation's file", comes to add that a notation gives no concept a label, and a legend's labels are content (point 7).
  - DEC-005 point 5, "Primitives at the leaves": the path comes to draw a shape, its outline mapped into its frame (point 2), an image's tint comes to fill the picture's alpha, an icon's alone for now (point 1), and a text's runs come to hold their signs and grounds as primitives beside it (point 4).
  - DEC-012 point 2, "Only how the run is set": a run's word comes to choose also whether the run draws its concept's sign, and its ground (point 4).
  - DEC-012 point 4 comes to add that a run's sign is measured within its line before its first character, with no break between them, and a ground's room at the run's ends (point 4).
  - DEC-012 point 8, "a choice by a run's style anywhere but the typography role and paint", comes to allow its sign and its ground too.
  - DEC-012's Implications: the bullet on a sign beside a run's colour leaves "Left to later changes", and they come to say this record decides it.
  - DEC-023 point 7, "Under forced colours", comes to give each tinted picture the reader's text colour (point 5).
  - DEC-025 point 1, "What an `image` part shows", comes to name a fifth source, its instance's concept's icon, and point 9's finding on an image part's sources comes to count it (point 1).
  - DEC-025's Implications, "A notation's marks", come to cite this record.
  - DEC-033 points 5 and 11: "of `file` or `role`" comes to read "of `file`, `role` or a concept's icon" (point 6).
- **Read against this record, and left as they stand:** DEC-001 point 5, DEC-002 point 4, DEC-003 point 3, DEC-004 point 8, DEC-010 point 6 and [visual-communication:DEC-027-forced-colours-viewing].
- **The Tasks that build it,** filed under [project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576) once this record is accepted, each bringing the pages it changes:
  - icons and their tint, in the notation, the scene, each renderer and the HTML page's rule for forced colours (points 1 and 5)
  - shapes, in the foundations, the notation, a shape part and each renderer (point 2)
  - a run's sign and ground (point 4)
  - the checks of point 9
  - the starter's legend and its components' signs, with the showcase deck's install slide taking a legend in place of its line that names its colours (points 3 and 7)
- **Left to later changes:** an SVG icon; a tint on another picture; a shape a component names itself; a concept's label from its notation, with translation, which revisits points 6 and 7; a legend the engine fills.
- **Revisit this record** if a renderer cannot fill a picture's alpha with one colour, a browser loses a tinted picture under forced colours, or an icon blurs where the starter draws it in print.
