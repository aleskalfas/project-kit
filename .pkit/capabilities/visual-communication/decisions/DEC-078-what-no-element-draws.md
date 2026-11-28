---
id: DEC-078
title: What no element draws is counted beside its type, and no renderer declares it
status: proposed
date: 2026-11-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** most of what a scene holds on an element describes it as drawn: its place and size, its paints, its text and lines, its picture, its route. A few properties say something about the element instead: which component drew a group, at which version and under which options, that a group is a page, and which parts a part lies over on purpose. No medium shows them, so no renderer draws them. This record keeps them all in one place: one list, beside the element's type, its trace id, its sources and its children, which the comparison that finds a renderer's losses before it runs reads for every type alike. No renderer's declaration lists any of them, and no renderer reports a loss of one. A renderer may still write one into its file as a mark a tool reads, as it writes a trace id. A property a later change adds takes its place by the same test.

## Context

A renderer declares, for each primitive and property, whether it draws it, and before it runs the capability compares each scene with that declaration and reports what it cannot take ([visual-communication:DEC-005-engine-and-plugins] point 9). Some properties a scene holds say nothing a medium could show. When this record was drafted, the capability kept them in two places:
- **A group's `component`, `version`, `options` and `page`,** which say which component drew it, at which version and under which options, and that it is a page (DEC-005 point 5; the capability's page on components, "What a scene holds"). Each renderer's declaration listed them under `group`, as properties it draws.
- **An element's `lies-over`,** the parts its part lies over on purpose. [visual-communication:DEC-066-meant-overlaps] point 2 counts it "among what no element draws, beside the element's type, its trace id, its sources and its children", in the code that finds the losses, so that no declaration lists it. Its Rationale, "Why it is no property the element draws", says why, and its Implications leave one rule for both open, for a follow-up to pick "before a third such property copies whichever it finds first". [project-kit#3407](https://github.com/aleskalfas/project-kit/issues/3407) is that follow-up.

The answer meets five things that already hold:
- **A renderer projects the scene.** The scene holds each element's place, size and values, and where each came from. A renderer reports what it cannot draw as the scene sets it ([visual-communication:DEC-001-visual-communication-discipline] point 2).
- **The seam's version** rises only when a plugin must read something differently, and a renderer's own version only when the same input could give another output (DEC-005 points 8 and 9).
- **Every plugin is the capability's** (DEC-005 point 12), so every declaration is too.
- **Renderers take a scene's pages from its root,** which names them in order. The mark `page: true` on a page's group says the same of that one group, and a check reads it there (the page on components, "What a scene holds").
- **A renderer may write a mark a tool reads.** When this record was drafted, the SVG renderer wrote each element's trace id into its file, and a group's component and version (the capability's page on outputs, "The SVG renderer").

## Decision

**What the scene says about an element, rather than of it as drawn, is counted once, in one list beside the element's type, its trace id, its sources and its children, which the comparison that finds a renderer's losses before it runs reads for every type alike. No renderer's declaration lists any of it, and no renderer reports a loss of it.**

### 1. What no element draws

- **The test.** A property of an element is one *no element draws* where it says something about the element rather than describing it as drawn: what kind of element it is, which element it is, where it and its values came from, how the piece's elements fall into groups and pages, or what the owner of the part that drew it says of it to a check. Every other property is *drawn*: it describes the element as a medium shows it to a reader, or carries it to a reader's tools. Its frame, its paints and lengths, its text, its lines and how far they reach, its picture, its route and its ends are drawn, and so is the reader's side ([visual-communication:DEC-033-structure-for-readers] point 1).
- **What it covers.** When this record was drafted: an element's type, its trace id, its sources and its children; a group's `component`, `version` and `options`; a page's group's `page`; and an element's `lies-over`.
- **By what it says, not by who reads it.** A drawn property is drawn even where no renderer the capability ships reads it, such as a text's measured height. Each renderer says in its declaration whether it draws it, and a renderer added later may.
- **On every type alike.** A property no element draws on one type is one on every type. So its name names no drawn property of any type.
- **Of an element.** The scene's root is no element. What a renderer takes of it stays as its records give it, such as a top's physical size ([visual-communication:DEC-034-brand-drawings] point 3).
- **Its source stays its own.** This record changes no property's source: a group's options name where each option's value came from, and `lies-over` names none (DEC-005 point 5, DEC-066 point 2).

### 2. One list, in the comparison that finds the losses, and in no declaration

- **Where it is kept.** The comparison of a scene with a renderer's declaration, which finds what the renderer will lose before it runs (DEC-005 point 9), holds one list of what no element draws, and passes over each property in it, on an element of any type. No other place lists them.
- **In no declaration.** A renderer declares each primitive it draws, and each drawn property of it. It lists nothing that no element draws, under any type.
- **No loss of it.** No renderer reports a loss of what no element draws, before it runs or as it draws. An output that leaves one out shows its reader everything the scene sets for a medium, so nothing is lost.
- **A mark is no drawing.** A renderer may write a property no element draws into its file as a mark a tool reads, as one writes an element's trace id, or a group's component and version. Writing it draws nothing, and leaving it out loses nothing, so its declaration does not name it for that.

### 3. A property a later change adds takes its place by the test

- **About the element:** it joins the list, and no declaration names it. It takes a name that no drawn property of any type holds.
- **Drawn:** each renderer that draws it declares it under each type that holds it, and the comparison reports a loss of it for each renderer that does not, as for any drawn property (DEC-005 point 9).
- **The change that adds it** says which it is, by point 1's test.

## Rationale

**Why one list, and not each declaration.** DEC-066's reason for `lies-over` holds for each property this record covers. Listed in a declaration, a property stands under each type that may hold it, and a renderer added later must list it under each, or report a loss of it in every piece that holds it. The group's four stand on a group alone, so each declaration listed them once. But the declaration then said that its renderer draws what it does not draw, and a renderer added later would copy that claim, or report a loss that no reader of its output would miss. In the list, each is one entry, in the one place that reads it.

**Why the test is what a property says.** Which properties a renderer reads is that renderer's, and its declaration states it. A test by what the renderers shipped today read would move a property between the list and the declarations as renderers change. A renderer added later that draws by it could then not declare it, since no declaration would hold it. What a property says does not change with the renderers.

**Why the four that were counted already fit.** An element's type, its trace id, its sources and its children say what kind it is, which it is, where its values came from and how the elements nest. The test is the one that already set them apart, stated so that a later property can be read by it.

**Why a page's mark is no drawn property.** A page is drawn: each renderer draws each page apart. Yet the scene names its pages, in order, on its root, which every renderer reads them from, and the comparison reads no root as an element. The mark on a page's group says the same of that one group, for a reader of one element at a time, such as a check. So it says how the elements fall into pages, as `children` says how they nest. What a page shows, its elements draw.

**Why a text's measured height and the like stay drawn.** A text's measured height and whether it overflows say how far its lines reach. An image's exposed points are places in its picture, and a line's attached ends name the elements it meets, which a medium with connectors of its own draws by (DEC-005 point 5). Each describes the element as drawn, though no renderer the capability ships read some of them when this record was drafted. In the declarations, a renderer added later says whether it draws them. And a name such as `points`, drawn on a line, could not stand in a list that is read for every type.

**Why a mark is no drawing.** A mark such as a trace id lets a tool find an element in a file. What a reader sees, and what a reader's tools read, is the same with or without it. So leaving one out loses nothing, and a declaration that listed what its renderer marks would claim that it draws it.

### What it costs

- **A name taken from every type.** A property no element draws holds its name on every type, so no drawn property may take it later on another (point 1).
- **A judgement at each new property.** The test reads what a property says, which the change that adds it judges (point 3), and no check can test that. A drawn property misjudged as one no element draws is never compared, so a renderer that cannot draw it reports no loss of it.
- **A declaration says less of the scene.** It names each drawn property, not every property a scene holds. A reader learns what the scene says about an element from the list and from the page on components.

### Alternatives considered

- **Every declaration lists them all,** `lies-over` under each type. Rejected, for the reason above: each renderer, and each added later, would list under each type what it never draws, or report a loss that no reader misses.
- **The scene keeps them apart, under one key of each element,** beside its sources, which the comparison passes over whole. A reader would see the two kinds in the data. Not taken. It moves keys that the checks, the viewing step and a renderer's marks read, so a renderer that marks one would read differently and the seam's version would rise (DEC-005 point 8). It changes the scene's form for every reader of scenes, for what one entry in one list gives. Its trigger to revisit: a plugin, or a reader outside the capability, that must tell the two kinds apart from the scene alone.
- **Each declaration names what its renderer leaves aside,** beside what it draws. Rejected: every renderer, and each added later, would repeat the same names, the two places this record joins, multiplied by the renderers.
- **The list in the seam,** handed to each plugin with the scene. Not taken: no plugin reads it, and only the capability's comparison does. The seam is what the engine hands its plugins and takes back (DEC-005 point 8).
- **A test by whether a renderer the capability ships reads the property.** Rejected, for the reason above: it moves a property as renderers change, and keeps a renderer added later from declaring what it draws.
- **Each left where it was.** Rejected: two rules, and a third such property would copy whichever it found first.

## Implications

- **This record changes no file a project keeps, and no output.** The work moves the group's four out of each renderer's declaration into the list. No renderer reported a loss of them before, since each declaration listed them, and none reports one after. So no scene, output or loss changes. The seam's version stays (DEC-005 point 8), and so does each renderer's (DEC-005 point 9). It adds no tool, field or accepted value, which a change declares by [visual-communication:DEC-014-own-library-needed-release] point 2, and it owes no migration: no file a project holds changes meaning.
- **Each edit below refines its record in place, and this record overturns none.** The edits are made in this change once this record is accepted (COR-066 point 5), and accepting this record accepts them. Each takes a forward pointer to this record.
  - **DEC-005 point 9,** the bullet "Each declares what it supports". Its first sentence, "A renderer declares, for each primitive and property, whether it draws it, updates it in place, recreates it, or reads it back.", comes to read: "A renderer declares, for each primitive and each property that describes it as drawn, whether it draws it, updates it in place, recreates it, or reads it back. What the scene says about an element rather than of it as drawn, such as which component drew a group, no renderer declares: the capability counts it apart, beside the element's type, its trace id, its sources and its children, and no renderer reports a loss of it (refinement per [visual-communication:DEC-078-what-no-element-draws] points 1 and 2)." The rest of the bullet stands.
  - **DEC-066's Implications,** the item "One rule for what no renderer draws" under "Left open". After its last sentence, it comes to add: "[visual-communication:DEC-078-what-no-element-draws] picks it: each is counted beside an element's type, and no renderer's declaration lists it (refinement per [visual-communication:DEC-078-what-no-element-draws] point 2)." The item's other words stay as they stood.
- **Read against this record, and left as they stand:**
  - DEC-001 point 2's "What a renderer cannot draw", which has a renderer report what it cannot draw as the scene sets it. The scene sets what no element draws for no medium, so a renderer that leaves it out loses nothing, and a format read whole stays the one exception that bullet names;
  - DEC-005 point 5's "A tree of groups", whose group says which component drew it, with its library's version and options, and whose element names the parts it lies over on purpose, which is "no property it draws". Point 1 counts each so, and changes the source of none;
  - DEC-005 point 8, since no plugin reads anything differently, and point 9's "Losses are known before a plugin runs", whose comparison holds the list (point 2), and "Each has a version of its own", since no output changes;
  - DEC-005 point 12, since every declaration is the capability's, so one change moves the group's four out of each;
  - DEC-066 point 2's "No property the element draws", which counts `lies-over` as point 1 does, and its Rationale "Why it is no property the element draws", whose reason point 2 follows, and whose sentences on the group's four say what held when it was drafted;
  - DEC-033 points 1 and 9, since each word of the reader's side is carried to a reader's tools, so it is drawn, a renderer declares it, and a format read whole loses none of it.
- **The work that builds it,** under [project-kit#3407](https://github.com/aleskalfas/project-kit/issues/3407), in this change, which lands only once this record is accepted:
  - the comparison that finds a renderer's losses before it runs holds the one list point 2 names: an element's type, its trace id, its sources and its children, its `lies-over`, and a group's `component`, `version`, `options` and `page`. Each renderer's declaration the capability ships drops the four from its `group`, and says that it declares each drawn property;
  - tests. A scene whose group holds all four, and an element of each type that holds `lies-over`, gives no loss under each renderer's declaration the capability ships. A declaration that does not name a drawn property still gives its loss. No declaration the capability ships names a property of the list, under any type. Each renderer's reference outputs stay as they were;
  - the capability's page on outputs, where it says what a renderer's declaration lists: each primitive it draws and each drawn property, and none of what no element draws, of which no renderer reports a loss. Its sentences that the SVG and PDF renderers' declarations name every primitive and property a scene of format 1 holds come to name every drawn property;
  - the page on components, under what a scene holds: which properties no element draws, by point 1's test, where it says so of `lies-over`.
