---
id: DEC-073
title: A component given no room gets less than it asks for, whatever gives it the size
status: proposed
date: 2026-11-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a component that asks for no width, or no height, takes what it is given there, and needs more than zero of it. Where it is given zero or less, the check reports it as a component that gets less than it asks for, `gets-less`, at the content, at its trace, whatever gave it the size: its list's `sizes`, a stretch, a `cross-size`, a part's formula, or the top its page lies in. A component that lies in one with no size there is not reported, since that one has none to give. And the engine holds every size it computes for a frame at zero or more, so no frame in the scene is turned inside out. For example, a row 16 px wide that shares its line equally among three cards as wide as they are given, 16 px apart, gives each card −5.33 px. Each card is reported, and drawn 0 px wide.

## Context

[visual-communication:DEC-038-size-by-place] point 5 has the check take an item that a row or a column sizes by place to ask across its line for more than zero. So a `cross-size` that gives it zero or less is reported at the content, as an item that gets less than it asks for, and its size is held at zero. The record leaves every other source of such a size to [project-kit#3113](https://github.com/aleskalfas/project-kit/issues/3113). Two of them give one today with no finding:
- **A list that shares its line,** by `sizes: equal` or `shares`, whose gaps take the whole line or more, gives each item zero or less.
- **A part's formula,** such as `width: "=:width - 2 * @space.4"` on a part that places a component, gives that component less than zero wherever its own component is narrower than the insets.

A component that asks for a size is reported wherever it gets less ([visual-communication:DEC-005-engine-and-plugins] points 3 and 14). One that asks for none, such as a card as wide as it is given, is never short of what it asks. So it is drawn with a frame below zero, and its parts with it, and the scene holds a width below zero, which no renderer can draw.

Terms:
- A component *asks for no size* along an axis, across or down, where its `preferred` gives none there. It then takes the size it is given (DEC-005 point 3).
- A component *lies in* the component whose part places it or repeats over its list, and a page in its top.

## Decision

**A component that asks for no size along an axis needs more than zero of it there, whatever gives it the size, and no frame the engine computes has a size below zero.**

### 1. A component that asks for no size needs more than zero of it

The check takes each component placed below the top that asks for no width, or no height, to ask there for more than zero. Where it is given zero or less, it is reported as a component that gets less than it asks for (DEC-005 point 14), whatever gave it the size: its list, by `sizes` along the line or by a stretch or a `cross-size` across it, a part's formula, or the top that gives its pages their size. A component that asks for a size is judged by what it asks, as before. A tie is judged by neither: it lies in its part's whole frame, and is drawn between its ends ([visual-communication:DEC-011-tie-ends] point 1). Nor is a part that draws a primitive, whose size is its component's own drawing (Rationale).

### 2. Not where the component it lies in has no size there

A component that asks for no size along an axis is not reported for it where the component it lies in has a size of zero there. That one has nothing to give, and is reported itself where it was short (point 1, DEC-005 point 14). Where it asked for zero, as a page that holds nothing asks for a height of zero, nothing is short.

### 3. No frame has a size below zero

The engine holds at zero every size it computes below zero for a frame: the size a component gets, the size a list gives each item, and the size a part's formula gives its part. Every reader of frames reads the size so held: a formula, a tie's end, the checks and every renderer (DEC-038 point 6). It names its source as before. A list that shares its line asks for the line it is given, as before, so its items carry the finding, never the list.

### 4. The finding lies at the content

The finding lies at the content, at the trace of the component given no room, as every finding of a component that gets less than it asks for does. So it fails validation wherever the component comes from, and wherever what gave it the size comes from, a released library included (DEC-005 point 14, [visual-communication:DEC-002-files-and-validation] point 7). Its message says that the component asks for no size there, and takes what it is given.

## Rationale

**Why the finding of a component that gets less.** A component that asks for no size takes what it is given, so the least it asks for is room to draw in, more than zero. Zero or less is short of that, and the check already names a component short of what it asks for, which each reader of findings reads, as DEC-038 point 5 reads a sized item's zero. A kind of finding for each source of the size would split one fault by what gave it, which the message says.

**Why at the content.** What gives a component no room is where the piece places it: a list with more items than its line holds gaps for, or a component placed in one narrower than its insets. The project mends that in its content, by giving the component more room, fewer items or another option, wherever the components come from. Reported in the component whose part gave the size, the finding would only ask for attention in a released library, though the project placed the component there, as DEC-038 found of a sized item's finding in its item's library.

**Why whatever gives the size.** The component is short of room whatever gave it the size, and its frame turns inside out the same way. A rule for each source leaves the next source silent, as `sizes: equal` and a part's formula were beside `cross-size`.

**Why a component that asks for a size is judged as before.** It asks for what it needs, and the check already reports it below that, zero or less included. One that asks for zero and gets it is not short.

**Why not inside a component with no size.** Inside a component with no size along an axis, each component that takes its size from it gets none, so each would repeat one fault, and a page that holds nothing would fail for the components that fill it. The component given no room carries the finding, and once it is mended, the check judges what lies in it. The cost: a component inside it that is short for a cause of its own is found only once the outer one is mended.

**Why every size is held at zero.** A frame below zero is no shape: SVG draws no rectangle of a width below zero, and each reader of frames would have to guess what it means. DEC-038 point 5 holds a sized item at zero for that reason, and the reason holds for every size. A part's own size is held too, since a component held at zero gives every part that reads its size, such as `=:width - 2 * @space.2`, less than zero. Holding each size where it is computed gives every reader of frames one answer, a formula that reads a part's frame among them.

**Why a part that draws a primitive is not reported.** A box, an ellipse, an image or a sign takes its size from its component's formula, read from the size the component gets. That is the component's own drawing, which its library keeps to itself (DEC-005 point 3). A box that fills a component that holds nothing is zero by design. A text given a width of zero or less is reported already, since every word overflows it (DEC-005 point 14). The cost: a box whose insets exceed the size its component gets, beside no text that shares them, draws nothing, with no finding.

### Alternatives considered

- **A kind of finding of its own,** such as `no-room`. Rejected: one fault, a component short of the room it needs, would take two names, and every reader of findings would learn a second one.
- **The finding in the component whose part, or whose list, gave the size.** Rejected: it would only ask for attention where a released library gave it, though the project mends it in its content.
- **Every part reported, a box or a text as a component.** Rejected: a part's size is its component's own drawing, so where the component gets what it asks for, a part at zero is a fault of its library that the project cannot mend, and a box that fills an empty component would fail.
- **Only a size below zero reported, zero let through.** Rejected: a component of zero width draws nothing of what the content gave it, as one below zero does.
- **The scene keeping a size below zero, reported but not held.** Rejected: every renderer would meet a frame it cannot draw, and the checks of frames would each read it their own way.
- **Each component inside one given no room reported too.** Rejected: one fault would give a finding for each component that fills it.
- **Leaving it undone.** Rejected: a piece whose cards fall to no width would pass its check, and its cards would vanish from the drawing.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - DEC-005 point 3, "Two sizes for each element", comes to add that the check takes a component below the top that asks for no size along an axis to ask there for more than zero, unless the component it lies in has no size there, and that the engine holds each size it computes below zero for a frame at zero (points 1 to 3).
- **Read against this record, and left as they stand:**
  - DEC-005 point 14, since a component given no room is a component that gets less than it asks for, which fails where the project can correct it, and what fails gains no kind (point 4).
  - DEC-005 point 5, since the scene holds every element's frame as before, only never below zero, and holds nothing new, so neither the seam's version nor any renderer's rises (DEC-005 points 8 and 9).
  - DEC-038 points 5 and 6, since a sized item still asks across its line for more than zero, wherever it lies, and is held at zero, as every size is (point 3), and every reader of frames meets the frame as before.
  - DEC-002 point 7, since the finding lies in the content, which the project can correct (point 4).
  - [visual-communication:DEC-003-change-over-time] point 8 and [visual-communication:DEC-001-visual-communication-discipline] point 7, since a draft meets the check at its next render, as it meets any new engine, and a final piece is not judged.
- **[project-kit#3113](https://github.com/aleskalfas/project-kit/issues/3113)** builds points 1 to 4 in the engine, with a test that draws a list sharing its line among more gaps than it holds and a part's formula that gives a component less than zero, and finds the report of each.
- **The page on checks:** the row of `gets-less` comes to name a component that asks for no size and is given zero or less, whatever gives it, and that one lying in a component with no size there is not reported.
- **The page on components:** the account of a list's `sizes`, the account of a part's places and sizes, and "What an element asks for, and what it gets" come to say what points 1 to 3 decide.
