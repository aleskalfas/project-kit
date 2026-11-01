---
id: DEC-005
title: A small closed engine computes the scene, and three kinds of plugin meet it at a versioned seam
status: proposed
date: 2026-11-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the engine computes where every element of a piece lies, how big it is and which values it takes, with a small fixed set of tools: arithmetic formulas, a few layout operators, references between elements, and text it measures from committed fonts. The tools never grow into a programming language. Renderers, producers of pictures and code writers all meet the engine at one versioned seam, say what they can take, and report what they lost in one form. One document of a brand's resolved values feeds them all, and each piece's last render keeps the findings the check reads.

## Context

The capability's founding record makes the engine the capability's code that computes the *scene* from a piece's content and its libraries. Renderers only project the scene. The engine knows no component by name, and computes with a small set of general tools. It runs no program and reads only the project's files. Three kinds of plugin meet it: renderers, producers of pictures and code writers ([visual-communication:DEC-001-visual-communication-discipline] points 2, 4 and 8). This record decides the tools, what the scene holds, and the seam between the engine and its plugins.

The capability's design work ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)) found what the engine must do:
- **The talk's generator placed every box in code.** It estimated each text's width as a number of characters times a constant. Among 2,479 objects in two languages, 6 texts were estimated to wrap past their box.
- **A whiteboard service had no monospace font,** so code shown on it was drawn as a picture, by hand.
- **Arithmetic covered most slides.** A pyramid's levels, and arrows spread around a slot, needed only an item's index, the count of items and the theme's sizes. Arrows that end at a slot two levels down inside another box also need that slot's measured place.
- **A prototype drew four slides and a figure** with formulas and a few layout operators, measuring text from committed font files.

A review of existing tools found none that lays out one component specification for several media. It advised adopting an established library to shape text, fixing the formula grammar so it never grows into a programming language, and giving each size one owner.

## Decision

**The engine computes the scene with a closed set of tools. They are formulas of plain arithmetic, a few layout operators, references between elements that never loop, and text it measures from committed fonts and breaks into lines itself. It also resolves a brand's values into one document. Renderers, producers and code writers meet the engine at one seam, in one pattern, with one form of loss report. The seam and the document each have a version of their own. Only the capability ships plugins, until a project needs one it will not ship.**

### 1. A formula is arithmetic, and stays arithmetic

A *formula* computes one number in a component's data.
- **What it may use:** numbers with no unit, such as counts, factors and ratios, the four operations, parentheses, and a few functions of numbers, such as the least, the greatest and rounding. It may read the component's own named values, and an item's place in its list with the list's count.
- **Where lengths come from:** a role's value, the size the component gets, and the frames point 3 lets it read. A *frame* is an element's place and size. A literal length would be a raw value, which no component holds (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 5).
- **Dimensions are checked.** The terms of a sum share one dimension. A number with no unit may scale a length, and is never added to one.
- **What it never holds:** a comparison, a condition, a loop, text, or a function a library defines.
- **A choice is declared, never computed.** A component chooses between values or parts by an option, or by whether a field is filled, which its schema checks (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 6).
- **A new function or name is a new tool of the engine.** The capability's reference holds the grammar.

### 2. Layout operators arrange, and connectors route simply

- **Repetition** draws a component once for each item of a list in the content.
- **Layout operators** stack elements, align them, distribute them and give them equal sizes. They reach a list's first item, its last, or an item by its id. Their names follow CSS's flexible layout where the meanings match.
- **No operator chooses, filters or sorts items by what they hold.** The content's order and the declared options decide.
- **Connectors** join named elements, straight, with corners or curved, with their ends spread evenly. They never route around obstacles.
- **A layout no operator computes,** such as a graph's, is work outside the engine (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 8). A new operator is added when a need recurs, and built and tested once ([visual-communication:DEC-001-visual-communication-discipline] point 4).

### 3. An element asks for a size and gets one, and references never loop

- **Two sizes for each element.** It asks for a size, from its content and its formulas. It gets one from its parent, by default the size it asked for.
- **One owner for each value.** An element's place and the size it gets, across and down, are each set by exactly one thing: its component, its measured text, or its parent's layout. A second writer is an error.
- **A formula reads its own component and what lies below it.** It reads its component's parts and the size its component gets. It reads the parts a component it places *exposes*, and a component may expose a part of a component it places in turn. Every component between keeps the rest private, so its library may change it freely. Removing or renaming an exposed part is a breaking change, as the record of change over time counts it ([visual-communication:DEC-003-change-over-time] point 6).
- **How a reference reads.** It names a part, then each exposed part below it, one name a step, then the measure of the frame it reads. A step into a list names the list, then the item, by its id or as the first or the last. An option that names an item of a list its own component declares gives the id alone (the record of files and validation, [visual-communication:DEC-002-files-and-validation] point 4). A role is named by its token path, marked apart from a part. A connector names its ends the same way.
- **Computed value by value,** in the order the references give, as a spreadsheet computes its cells. So a parent's width and a child's measured height form no loop. A loop is refused, naming every element in it.
- **A missing optional part** has zero size, at its place. Dividing by zero is an error that names the formula.
- **A component never places itself,** directly or through others, except over the items of its content, which end.

### 4. The engine measures text from committed fonts, and breaks its lines

- **Measured from the brand's fonts.** The engine shapes each run of text with an established shaping library, HarfBuzz, from the committed font file, and reads font metrics with an established font library. Where a font profile gives a table of widths or an estimate, it measures by that. The record of brands and notations decides fonts, font profiles and what a missing font does.
- **Lines broken by the engine.** It breaks text into lines by Unicode's rules and each language's own rules, kept as data in the engine. So a new language's rules arrive with a release of the capability. In Czech, for example, a one-letter word never ends a line.
- **A margin keeps lines stable.** The engine breaks against the planned width minus a small margin, and places the text in the planned width. So a renderer's slightly different metrics move no word, and centred text stays centred.
- **Text never shrinks to fit.** A word longer than its line breaks after a slash, or is marked as overflowing. There is no hyphenation and no justified text at first.
- **A renderer draws the lines as given.** A medium that wraps text itself, and whose edits come back as plain text, may wrap within the measured width, as a declared choice (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 2).

### 5. The scene holds every element's final frame, values and source

- **A tree of groups,** each with its frame relative to its parent. Lengths are in one unit. A top component whose pages have a physical size, such as a poster, declares it, and an export maps the unit onto it. A group may say which component drew it, with its library's version and options.
- **Primitives at the leaves:** a box, an ellipse, a text, a line and an image, with a path kept for later. Their properties take SVG's names. Draw order is the tree's order.
  - A text holds paragraphs of runs, each with a style role and perhaps a link. It holds its lines, its explicit line height, its measured height, its font, and how it was measured.
  - A line carries its whole shape. Its attached ends are hints for a medium with connectors of its own.
  - An image has a fit and a tint by role. One made while preparing holds its variants by key (the record of brands and notations), and its *exposed points*: named points in its pixels that the piece may point at, such as to place a label. The record of work outside the engine and outputs decides the rules on both. A formula or a connector reads an exposed point as it reads an exposed part, mapped into the image's frame.
  - Documents and PDF files get alternative text, a reading order, and structure such as headings, lists, tables and captions.
- **Values stay roles.** Each value that moves nothing, such as a colour or a picture, names its role. Its value comes from the document of point 7, so one scene serves every mode of the value axes. So the variants of one picture in one scene share one pixel size, and the same exposed points at the same places.
- **The root says what the scene is:** the piece, its lock, its language, the key over its size axes, and the seam's version.
- **Pages are declared by a slot.** A top component's slot says that its items are pages. A diagram is then a page alone, and part of a page inside a slide. A page inside a page is an error.
- **Every element carries its trace** (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 3). Its id comes from the path of instances, parts and item ids, or an item's place where it has no id, never from the order of drawing. Each property names its source: a content field, an option, a library's default, a role, or the engine.
- **Computed, never committed.** Order and rounding are fixed, so under one release of the capability the same files give the same scene on every machine, and two scenes compare.

### 6. A piece names the modes it is drawn in

- **Each axis, its modes.** A piece names, in one place of its own, the modes it is drawn in on each axis of its brand. An axis it names none for is drawn in its default. The font profile is the exception: each renderer of the piece's outputs names its own (point 10).
- **One scene for each language and each combination of size-axis modes,** font profiles included. The values of every combination named come with each scene.
- **Every combination named is checked and previewed.** Which combinations an export holds is the record of work outside the engine and outputs'.

### 7. The engine owns one document of a brand's resolved values

- **What it holds:** each exported token of a brand, resolved over its chain of bases, in each combination asked for, named by token path and key. It also holds the component tokens of the component libraries resolved with it.
- **Under a lock.** A piece's lock names every version. *Written code*, a brand written out by a code writer, is declared by the project like a piece, in a declaration the record of files and validation places ([visual-communication:DEC-002-files-and-validation] point 1). The declaration names the code writer, the version of the form it follows, and a lock of the brand, its bases and the component libraries it holds.
- **A person moves written code's lock,** on purpose, as a piece's lock moves, so written code changes only then. The declaration is then a file a command rewrites. So it is kept apart from content, and carried over at a change of format, as the records of files and validation ([visual-communication:DEC-002-files-and-validation] point 5) and of change over time ([visual-communication:DEC-003-change-over-time] point 2) treat such files.
- **A brand checked alone** takes the newest version the project holds of each major it builds on.
- **Who reads it.** A renderer takes the scene's roles from it. The code writer for JSON writes it out unchanged, and every other code writer writes it in its own language.
- **What a program run while preparing receives.** A command of the capability writes, for a producer or a helper, the values it declares. It adds the measured frames it declares, from a scene computed with that program's own output left out, so its output never changes what it measured. They come in the document's form.
- **Computed, never edited or committed,** like the scene.
- **No plugin reads another plugin's output.** Producers, helpers and code writers all read this document. So a game's runtime reading the JSON reads, under the same lock, exactly the values a picture was made from.

### 8. The seam and the document of values each have a version

- **The seam** is what the engine hands its plugins and takes back: the scene, each plugin's declaration and the loss report. Its version rises only when a plugin must read something differently. The engine refuses a plugin that does not read the version it writes.
- **The document of values, and each code writer's spelling, have versions of their own,** since written code carries them out of the capability. Each code writer keeps writing every version it shipped, so written code moves to a new one only when its declaration moves.
- **These versions are apart from the format number of the files a project keeps** (the record of change over time, [visual-communication:DEC-003-change-over-time] point 1). The seam is never kept, and the document reaches a project only as written code.

### 9. Three kinds of plugin share one pattern and one loss report

- **The three kinds:**
  - A *renderer* draws a scene in one medium.
  - A *producer* makes a picture while a piece is prepared, from its own inputs and the values it declares. A person or an agent runs it, never the engine (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 8). The record of work outside the engine and outputs decides the rules on its pictures.
  - A *code writer* writes the document of values as code in one language, under the naming rule of the record of brands and notations.
- **Each declares what it supports.** A renderer declares, for each primitive and property, whether it draws it, updates it in place, recreates it, or reads it back. A producer declares the inputs it takes and the kinds of value it can use. A code writer declares the kinds of value its language has a form for.
- **Each declares what it needs beyond the project's files:** the outside programs it calls, and any service it reaches, as the record of files and validation decides ([visual-communication:DEC-002-files-and-validation] point 8).
- **Each has a version of its own,** apart from the capability's. It rises when the same input could give another output, and reference outputs pinned to it in the capability's tests catch a change made without one. So a release that changes no plugin's output leaves no picture or written code stale.
- **Losses are known before a plugin runs.** The capability compares what a plugin will be handed with what it declares, and reports what it cannot take.
- **One form of loss report.** Each loss names what was lost, by trace id or token path, what the plugin did instead, and why. It approximated it, drew it as a picture, left it out, or refused it.
- **A known loss may be accepted** where the output is declared: in a piece for a renderer's or a producer's, and in written code's declaration for a code writer's. The check then stops repeating it.
- **One fallback for renderers.** A renderer may draw a part it cannot draw through the renderer of vector pictures, and place it as a picture. The fields under it are marked as never to be taken back from that medium.

### 10. A renderer names its font profile, with a default

- **By default, the brand's own files.** A renderer that can draw the brand's font files draws in the default profile, pointed at those files, never at the machine's.
- **A medium with fonts of its own,** such as a whiteboard service, has a renderer that names the profile it draws in.
- **A brand without that profile** is drawn in its default profile, and the renderer reports each font it cannot draw as a loss. It never swaps a font silently.

### 11. A renderer that draws into a lasting medium commits a record of what it last drew

- **Which renderers.** One whose medium keeps objects between renders, such as a board on a whiteboard service, keeps a record for each place it draws to.
- **What it holds:** for each element's trace id, the medium's id for the object, a hash of each property drawn, and the scene it came from. Where the medium can keep a trace id on the object itself, the record holds less.
- **Why it is committed.** The next render, from any clone, updates in place only what changed. An edit made in the medium is found by comparing the medium with the record, as a later record of taking edits back decides.
- **A file a command rewrites.** A change of its format carries it over as the record of change over time decides for such files ([visual-communication:DEC-003-change-over-time] point 2). How trace ids are derived is part of that format, and changes only with a map from old ids to new. A library that renames a private part changes the ids below it, and the next render recreates those objects.
- **Rewritten at each render, never by hand.** The record of files and validation keeps it apart from content ([visual-communication:DEC-002-files-and-validation] point 5). A renderer that writes files keeps none: its files are exports. Two branches that draw to one place conflict in its record, as on the board, and the change that builds such a renderer settles how.

### 12. A project adds no plugin, for now

- **Every plugin is the capability's.** A plugin is code the capability runs with the trust its commands have, and the seam is too new to promise to code outside it.
- **The ways out today:** a project's own program run while preparing is a helper, and makes a picture a producer would (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 8). Code reads the JSON a code writer writes. A project that needs another medium asks for its renderer.
- **When to revisit:** once a project needs a plugin the capability will not ship. The seam's own version lets it open then without a break.

### 13. The scene check reads each piece's last render, and computes only what changed

Validation runs each validator under a fixed bound, and the work of computing every scene grows with a project's pieces, languages and combinations. So the check judges what it can read from the files without computing every scene.
- **Each render keeps a record of its piece's findings,** beside the piece, keyed by a hash of every file its scenes were computed from, as the record of work outside the engine and outputs gives such a key its form. The project commits it, so a fresh clone reads it. It is a file a command rewrites, apart from content (the record of files and validation, [visual-communication:DEC-002-files-and-validation] point 5).
- **A record that verifies is read.** Its findings are the check's for that piece. The engine's version is not in the key, since a new engine reaches a piece only at a render a person runs (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 7).
- **A piece whose record is missing or does not verify** has its scenes computed by the check, in that run, from the files alone. So the work grows with what a change touched, not with the project, and no result kept outside the repository is needed.
- **A final piece's scenes are not computed** (the record of files and validation, [visual-communication:DEC-002-files-and-validation] point 7).

### 14. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, as the record of files and validation decides ([visual-communication:DEC-002-files-and-validation] point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it (COR-055 points 1 and 4). A final piece's drawing is not judged, as that record decides.
- **Fails validation:**
  - a formula that cannot be read, reads what it may not reach, adds a number with no unit to a length, or divides by zero
  - a loop of references, a value with two owners, a reference to an exposed part or point that is missing, or a component that places itself
  - a page inside a page, or a mode a piece names that its brand lacks
  - a text that overflows its box, or a component that gets less than it asks for, measured from a font file
- **Asks for attention, never failing:** an overflow measured from a table or by an estimate, and a loss nobody has accepted.

## Rationale

**Why formulas stay arithmetic.** A schema checks data, and an agent writes data against it. A formula with conditions and loops would be a program inside the data. A choice made by an option is declared, checked, and drawn once for each value. Vega's limited expressions draw the same line, and list operations live in the operators. Lengths come from roles so a brand's spacing reaches every component.

**Why references, with one owner and reading downward.** Stacks and equal sizes put a note under the tallest card. An arrow to a slot inside another box, or a label at a picture's exposed point, needs a measured place no operator gives. Two sizes per element are how CSS and Flutter let a parent stretch a child. One owner per value, the rule of the Bluefish diagram library, keeps two writers from fighting over a size. Exposure through each component between keeps every component's inside its own.
- **The name of exposed points.** A picture's named points are read as a component's exposed parts are, so they share the word. "Anchor" is what an artefact rests on in this methodology (COR-050). "Landmark" names a page's regions in the accessibility markup of web and tagged outputs.

**Why the engine measures from committed fonts, and breaks lines.** The estimate served the talk, yet every text past its box was a broken drawing, and exact measuring costs nothing more where a font file exists. A font found on the machine differs between machines. Shaping is the hardest part of the stack, so the engine adopts a library. If renderers wrapped text, a small error in a width would move a word and push down every box below.

**Why the engine owns the resolved values.** A producer that read a code writer's output would depend on that writer's spelling. A picture's record of its inputs must hold the exact values the picture read. One document gives renderers, pictures and code the same values.

**Why versions apart, and why written code is declared with a lock.** The files a project keeps change with what people write, the seam with what plugins read, and the document with what code outside reads. A game's runtime has no lock of its own, and every component moves with the methodology's version, so a code writer keeps each form it shipped. Written code changes only when a person moves its declaration, as a piece's lock moves.

**Why one pattern for three kinds.** Each kind meets the same two questions: what can it take, and what did it lose (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 2). One declaration and one loss report give one check, and one way to accept a loss.

**Why the check reads each piece's last render.** Validation runs each validator under one fixed bound, and its validators are declared once, so neither can grow with a project. Computing every scene in every run would fail a large project for its size, for no fault in its files. A record keyed by what the scenes were computed from is a fact about the files, as a stale picture's record is, and a change touches few pieces. Keeping the engine's version out of the key follows the founding record: a piece meets a new engine at a render a person runs ([visual-communication:DEC-001-visual-communication-discipline] point 7).

### Alternatives considered

- **A constraint solver,** such as Cassowary. Rejected. Its results are hard to predict, and a conflict is hard to explain.
- **Layout operators only, with no references.** Rejected. An arrow to a nested slot cannot be said.
- **Formulas with conditions, or literal lengths.** Rejected. Each pattern would become a small language, and a brand's spacing would not reach it.
- **Renderers that wrap text, or text measured in a browser.** Rejected. A browser is heavy, and a whiteboard service's fonts are not in one.
- **A scene for every combination of modes.** Rejected. Colours would multiply scenes, and a page could not switch modes while open.
- **One version for everything, a producer reading a code writer's JSON, or written code that follows the newest values.** Rejected for the reasons above.
- **Every scene computed in every run, split among several validators where one cannot.** Rejected. The validators are declared once, so the split cannot follow a project's size.
- **A stale record of findings failing validation until the piece is rendered again.** Rejected. A draft goes stale at every edit, and would hold every change of the project.

## Implications

- **The capability's reference** lists the formula's functions and names, the operators, the primitives and each plugin's declaration. Its schemas hold the forms of the seam and of the document of values.
- **The walking skeleton** draws one pattern with one item component, using a formula and a layout operator. It measures text from a committed font in one profile, and breaks lines in the engine. A small program reads the values it declares, and the piece places a label at its picture's exposed point. The renderer of vector pictures draws the scene and reports what it could not draw. Its render keeps the record of findings the check reads (point 13).
- **Later slices** build the whiteboard renderer with its profile and its record, the web page renderer, producers, and taking edits back.
- **The record of work outside the engine and outputs** decides a produced picture's rules, its variants, exposed points and the record of what it was made from, and where written code goes.
