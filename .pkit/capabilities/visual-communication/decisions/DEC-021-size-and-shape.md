---
id: DEC-021
title: A component follows the page's size through a switch on one shared axis
status: accepted
date: 2026-11-06
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person designs one page, and the engine lays it out at each size they choose: desktop, tablet or phone. The foundations declare those three as one axis, and a brand says how wide each is. A component reads the size by a marked name, in a switch. So a row can become a column, and a part can hide. A size a component does not name draws as the default does, so a new size breaks no released component. A brand with no size stays as it is, and a piece cannot ask it for one. A page that reflows live in a browser stays out.

## Context

Version 1 of the capability designs a web page or a portal: one design, laid out at the sizes a person chooses ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)). A page that reflows live stays out, as the founding record keeps live views outside ([visual-communication:DEC-001-visual-communication-discipline] point 9). In this record a *size* is a mode of a size axis a piece can name.

A size axis changes a brand's values, and each combination of its modes has a scene of its own ([visual-communication:DEC-004-brands-and-notations] point 2, [visual-communication:DEC-005-engine-and-plugins] point 6). So a number can follow a size. A shape cannot: a component chooses by an option or a field, and a formula holds no comparison (DEC-005 point 1). Values are computed after parts are built, so a choice by a width cannot work. What the engine knows before it builds is the scene's key.

Format 1 gives a component these tools:
- **A switch,** `{by: <option>, <word>: <value>}`, chooses a value by an option's word, and names every word.
- **A `when`** says whether a part is drawn: by a filled field, as `when: head`, or by an option's words, as `when: {widths: [own]}`.
- **A `repeat` part** draws a component for each item of a list, laid out by its `row` or its `column`.
- **A *marked name*** is one the engine hands a component, after `:`, as `:width` is the width it gets.

Three things stand in the way:
- **Every brand holds every shared axis,** though "a brand has the shared axes it needs" (DEC-004 point 2). A shared size axis would take every brand from four combinations to twelve, and the CSS writer would refuse them all.
- **A new mode counts as no break** (DEC-004 point 5). Yet the brand reader refuses a brand that lacks a context for a mode, a released brand included.
- **A new shared axis breaks the foundations** once they are released (DEC-004 point 5), and their first release is due ([project-kit#2611](https://github.com/aleskalfas/project-kit/issues/2611)).

## Decision

**The foundations declare one size axis, `device`, and a piece chooses among its modes. A brand has only the sizes it or its base gives. A component reads the size by a marked name, in a switch or a `when` that names the axis's default. A mode it does not name draws as the default does. A size hides a part as an option hides one. The axis lands after the foundations' first release, as an addition.**

### 1. The foundations declare one size axis

- **The axis.** `device`, with the modes `desktop`, `tablet` and `phone`, and the default `desktop`.
- **A person chooses among its modes,** where a piece names its modes (DEC-005 point 6).
- **A width is a brand's value.** A piece names none, since a size would then have two owners.
- **Three sizes for now.** A brand adds no mode to a shared axis, so a fourth size is a new mode of the foundations.

### 2. A brand has only the sizes it or its base gives

- **What it has.** A brand with no base has a shared size axis where its Resolver document gives it a modifier. It has the modes that modifier gives, the default among them. A brand built on another has its base's sizes (DEC-004 point 6).
- **So a brand with no size changes nothing.** Its combinations and its written code stay as they are, and a new mode of the axis does not reach it.
- **A piece that names a size its brand does not have fails,** as a mode its brand lacks does (DEC-005 point 14). Otherwise the shape would follow the size, and the widths would not.
- **A value axis stays whole.** Every brand has every mode of every shared value axis. A mode it does not give takes its values at the axis's default, and a brand built on another keeps its base's there. So a new mode reads no released brand as broken.

### 3. A component reads the size in a switch or a `when`

- **A marked name.** A component reads an axis by its name after `:`, as `:device`, as it reads `:width`. So it never meets an option, and nothing has to give it. No axis takes a name the engine holds.
- **What it reads.** The mode the scene's key holds, else the axis's default. So a piece that names no size draws the default's shape.
- **A switch** chooses by it wherever a switch chooses by an option: `{by: ":device", desktop: "=@space.3", phone: "=@space.1"}`.
- **A `when` by a size** is such a switch. Each branch says yes, no, or what a `when` says already: `{by: ":device", desktop: head, phone: false}`.
- **The default is named, and takes what is left out.** Each names the axis's default, and a mode it does not name takes that branch. So `tablet` above follows `desktop`. A new mode draws the default's shape until a component names it.
- **Only a size axis a piece can name.** One scene serves every mode of a value axis (DEC-004 point 2). A renderer names a font profile, and a renderer picks no shape (DEC-001 point 2). A drawing of a layout also reads `:as`, which says whether its instance is a page (refinement per [visual-communication:DEC-034-brand-drawings] point 7).
- **No line declares it.** The marked name is the declaration, found where it is used.

### 4. A list changes direction on two parts

- **Two `repeat` parts over one list,** one a `row` and one a `column`, each with a `when` by the size.
- **What it costs.** No option names an item of such a list, as of any list two parts repeat over. An item's trace id differs by size. Each formula that reads the list's frame reads both parts.

### 5. A size hides a part as an option hides one

- **Every rule for a part not drawn holds.** It has zero size at its place, so a formula that reads its frame holds (DEC-005 point 3). An exposed part reads the same, and a slot's content is not drawn.
- **What must find a hidden item fails at that key,** as it does where an option hides the list. That covers a formula that reads the item, by an option or a step into the list, and a tie's end (DEC-011 point 4).
- **Hidden content is stated.** Content drawn at one key a piece names and not at another is a fact. So a reviewer sees what a reader at that size does not get.

### 6. The size is the page's, not the slot's

A component reads the size the piece is drawn at, whatever room its placer gives it. So a row at `desktop` stays a row in a narrow slot, and no placer changes that. A component answers to its slot only by formulas on `:width`, which change numbers. A drawing of a layout also answers to whether its instance is a page (refinement per [visual-communication:DEC-034-brand-drawings] point 7).

### 7. What the scene and the checks read

- **The scene.** A value a size chose names the axis as its source, a kind of its own (DEC-005 point 5).
- **The search for a lock** places a piece at each key it names, in each language. An end lost at one key holds its versions back, and what the render states names the key (DEC-011 point 4).
- **A library checked alone** places nothing, at any size or under any option, so a size adds no new blind spot. A fault shows in a piece, and a component's reference renders draw each mode it names (DEC-007 point 3).
- **Fails validation,** as the record of files and validation decides ([visual-communication:DEC-002-files-and-validation] point 7):
  - a `when` or a switch by a marked name that reads no size axis a piece can name, or names a mode the foundations lack, other than one by `:as` in a drawing of a layout (refinement per [visual-communication:DEC-034-brand-drawings] point 7)
  - such a `when` or switch that leaves out the default
  - two parts over one list whose `when`s by a size say yes or no, where not exactly one says yes at each mode
  - at the lock, a component that reads an axis the locked foundations lack
  - in a drawing of a layout, a `when` or a switch by `:as` that names a value other than `page` and `part`, or leaves out the default, `page` (refinement per [visual-communication:DEC-034-brand-drawings] points 7 and 10)
- **Stated as a fact,** at its key: hidden content, and a piece drawn in a value mode neither its brand nor its base gives.

### 8. Written code

- **The CSS writer** writes a brand's value axes at the default size, and reports as a loss each token a size changes. Nothing answers a window's width, since a page that reflows live stays out.
- **A page file holds one size** ([visual-communication:DEC-020-html-page-drawing] point 4). It takes each mode's values at that key, as [visual-communication:DEC-023-html-page-modes] point 3 says.
- **The JSON writer's document** gains the keys of a brand's size axes, and its form stays.

### 9. The axis lands after the foundations' first release

- **A new shared axis is an addition while no brand can hold an axis of its own,** since its name can meet none until then.
- **So the first release does not wait.** The axis goes into the version being built after it.
- **The axis stays unreleased until it is proved.** Its version waits for the Task of the first web page, which draws one at two sizes. Whoever maintains the capability holds that.
- **Point 3's form lands with its proof.** The next release of the capability fixes the form (DEC-003 point 3). So the change that builds it tests it on a page alone at two sizes.

## Rationale

**Why one shared axis.** A shared component can name only what every brand reads alike. The record of brands already gives the device as an example, and three sizes cover a web page.

**Why a `when` and a switch.** They are the tools a component chooses with, and what they read is known before the engine builds parts. They add no comparison to a formula, and nothing for content to give.

**Why a `when` by a size is a switch.** A released component cannot be corrected (DEC-003 point 6), and a new mode breaks nothing. A `when` needs three states, yes, no and not named, and a list of words has two. `[desktop, tablet]` and `[phone]` both miss a new mode, and a list on those two parts vanishes. A switch names its default, so a new mode draws as the default does.

**Why a size axis and a value axis differ here.** A value mode moves nothing, so a brand that does not give one still draws the same page. Format 1 accepts such a piece, so it may not be refused (DEC-003 point 3). A size moves everything: at the default's values, a component would show a phone's shape at a desktop's width. No piece names a size axis yet, so a brand's size axes can narrow and refuse nothing. No brand then pays for a choice it never made.

**Why a piece chooses among three modes.** The cost is that another width needs a brand of one's own. A fourth size needs a release of the foundations, and of each brand that gives it. Letting a brand add a mode later refuses nothing, so it can wait.

**Why fail first.** A hidden end and a size a brand lacks both fail. Turning a failure into a fact later refuses nothing, and the reverse would. So two parts that do not hold apart fail too, while that check can still be added.

**Why the axis does not hold the first release.** That first release would wait for this record and a release of the capability, and fix `device` before any web page is drawn. The clash the record of brands guards against needs a brand's own axis, which format 1 refuses. Holding the axis has a cost. A library has one version being built, so no fix to the foundations is released meanwhile. That wait ends at the first web page.

### Alternatives considered

- **An option that follows the axis.** It moves a mode in one line. Rejected. It adds a kind of option that content and a placer must be kept from giving, and a source a scene must name.
- **A role that holds a word a brand gives.** Rejected. DTCG has no such type, and the search for a lock reads no brand's values.
- **A formula that compares `:width`.** Rejected. A formula holds no comparison, and values come after parts.
- **A drawing for each size.** Rejected. It copies the parts, and each copy must be kept in step.
- **A row that wraps.** Rejected. It neither hides a part nor forces a column.
- **A `when` that lists a size's words, as it lists an option's.** Rejected, for the reason above.
- **One `repeat` part whose direction switches.** Rejected. `row` and `column` are fixed keys the engine reads throughout, and two parts already work.
- **One line that declares the axes a component follows.** Rejected. It says again what the marked name says, and a check or a reference render can read the marked names.
- **A size a brand lacks, drawn at the default's values.** It would need no failure. Rejected, since the shape would follow and the widths would not.
- **A width a piece names.** Rejected. A size would have two owners.
- **A brand with no base that adds a mode to a shared size axis.** Put off, as no need has shown.
- **The axis before the first release, or a major of the foundations after it.** Rejected. The first fixes `device` too early. The second stays the way back if point 9 proves wrong.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-004 point 1, "The modes are one Resolver document"** comes to hold each axis a brand varies as a modifier, with a default, and each mode it gives as a context.
  - **DEC-004 point 2, "The foundations name the shared axes"** comes to say that a brand has every shared value axis whole. A mode it does not give takes its values at the default, or its base's. It has a shared size axis only as this record's point 2 says, and adds no mode to a shared axis. A piece keeps a mode of a value axis when its brand is switched, and a size its brand lacks fails.
  - **DEC-004 point 5, "Breaking changes"** comes to count a new shared axis as breaking only once a brand can hold an axis of its own. **"Not breaking"** comes to add a new shared axis with a default until then, and a brand that comes to give a size.
  - **DEC-004's Rationale, "Why a key leaves defaults out"** comes to say a new shared axis waits for a major once a brand holds its own.
  - **DEC-005 point 1, "A choice is declared, never computed"** comes to add a size axis a piece can name, read by its marked name.
  - **DEC-005 point 2, "No operator chooses"** comes to say that the content's order, the declared options and the size decide how items are arranged.
  - **DEC-005 point 5, "Every element carries its trace"** comes to add a size among a property's sources.
  - **DEC-007 point 3** comes to add, to a component's reference renders, each mode of a size axis it names, drawn once.
  - **DEC-010 point 3, "The pattern chooses by it as by an option", and its Rationale** come to name a size as a third way to choose.
  - **DEC-011 point 4 and its Rationale, "Why an end is found once"** come to say that an end is judged at each key. Two parts may also hold apart under sizes, as under options.
  - **DEC-003 point 8, "No end of a tie lost"** comes to say "at any combination of sizes the piece names".
- **Read against this answer, and left as they stand:**
  - DEC-001 point 5, since a failure reports what a brand lacks.
  - DEC-001 point 6, since a size is no option.
  - DEC-003 point 3, since this adds, and refuses nothing format 1 accepts.
  - DEC-003 point 6, since a shape that follows a size is how a piece looks.
  - DEC-004 point 6, since a brand built on another still adds no axis.
  - DEC-005 point 10, since a renderer still names its profile.
  - DEC-005 point 14, since a brand lacks a size neither it nor its base gives, and lacks no mode of a shared value axis.
  - DEC-009 point 6, since no piece fails for a layout its brand lacks, and a mode is no layout.
  - DEC-012's Context, since it tells what that record's question met.
- **The Task of the size axis** declares the axis, narrows what a brand has and lets it give some modes. It changes the CSS writer. The release's comparison comes to read a new shared axis as an addition, and to read the modes a brand gives.
- **The Task that changes a shape by size** builds points 3 to 7, and tests them as point 9 says. The brand that reference renders draw with comes to give the sizes then.
- **The Task of the first web page** ends point 9's hold on the axis.
- **[project-kit#2738](https://github.com/aleskalfas/project-kit/issues/2738) is edited before it starts,** to weigh that a file at one size needs that size's values, where the CSS writer writes the default's.
- **The capability's pages** change with these Tasks.
- **Left open:**
  - **A brand's own axes** wait for a later change, which makes a new shared axis breaking again. A mode a brand adds to a shared size axis waits with them, since it could meet a later shared mode.
  - **A brand's drawing at each key** is decided by [visual-communication:DEC-034-brand-drawings] point 6. Its fit rests on a found end.
  - **A font profile** is a size axis too (DEC-004 point 2), but a piece's `modes` do not name one (DEC-005 point 6). So one scene for each key serves a profile only once a renderer's profile joins the keys.
