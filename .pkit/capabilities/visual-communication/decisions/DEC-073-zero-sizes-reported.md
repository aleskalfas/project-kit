---
id: DEC-073
title: A component placed below the top needs more than zero along each axis, whatever gives it the size
status: accepted
date: 2026-11-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a component placed below the top needs room to draw in: more than zero of width and of height, unless it asks for zero, as a page that holds nothing does. Where it gets zero or less, whatever gave it the size, the check reports it as a component that gets less than it asks for, `gets-less`, and names what gave the size: its list and the list's gaps, the list's stretch, or a part and its formula. A component whose own formula asks for less than zero is reported too. The finding fails at the content where the size rests on what the content placed, and otherwise lies in the library of the component that gave the size, where a released version only asks for attention. A component that takes its size from one with no size there is not reported, since that one asked for zero or is reported itself. And the engine holds every size it computes for a frame at zero or more, so no frame in the scene is turned inside out. For example, a row 16 px wide that shares its line equally among three cards as wide as they are given, 16 px apart, gives each card −5.33 px. Each card is reported at the content, since the content gave the row more cards than its gaps leave room for, and each is drawn 0 px wide.

## Context

[visual-communication:DEC-038-size-by-place] point 5 has the check take an item that a row or a column sizes by place to ask across its line for more than zero. So a `cross-size` that gives it zero or less is reported at the content, as an item that gets less than it asks for, and its size is held at zero. The record leaves every other source of such a size to [project-kit#3113](https://github.com/aleskalfas/project-kit/issues/3113). Three of them give one today with no finding:
- **A list that shares its line,** by `sizes: equal` or `shares`, whose gaps take the whole line or more, gives each item zero or less.
- **A part's formula,** such as `width: "=:width - 2 * @space.4"` on a part that places a component, gives that component less than zero wherever its own component is narrower than the insets.
- **A component's own formula** may ask for less than zero, such as `=@space.1 - @space.2`, and a component that gets what it asks for is never short of it.

A component that asks for a size is reported wherever it gets less ([visual-communication:DEC-005-engine-and-plugins] points 3 and 14). One that asks for none, such as a card as wide as it is given, is never short of what it asks. So each such component is drawn with a frame below zero, and its parts with it, and the scene holds a width below zero, which no renderer can draw.

Terms:
- A component *asks for no size* along an axis, across or down, where its `preferred` gives none there. It then takes the size it is given (DEC-005 point 3).
- A component *lies in* the component whose part places it or repeats over its list, and a page in its top. That component *gives it its size* along an axis where its part sets the size there.
- A component *takes a size from where it is placed* where what places it sets that size: a part's formula, its list's share of its line, a stretch or a `cross-size`, or, for a page, its top. A size it asks for and gets as asked, as the top does, is its own formula's.

## Decision

**A component placed below the top gets more than zero along each axis, unless it asks for zero there, or asks for no size there and lies in one with no size there; one that asks for a size gets at least it, and an item its list sizes by place gets more than zero wherever it lies. No frame the engine computes has a size below zero.**

### 1. A component placed below the top needs more than zero along each axis

The check takes each component placed below the top to need more than zero of width and of height. One that gets zero or less along an axis, and does not ask for zero there, is reported as a component that gets less than it asks for (DEC-005 point 14), save where point 2 says otherwise:
- **One that asks for no size there** takes what it is given, and needs more than zero of it, whatever gives it: its list, by `sizes` along its line or by a stretch across it, a part's formula, or the top that gives its pages their size.
- **One that asks for a size there** is judged by what it asks, as before. One whose own formula asks for less than zero asks for no room, and is reported where it gets no more than zero. Where a part gives it more, it draws at that size, and is not reported.
- **An item its list sizes by place** keeps DEC-038 point 5: it needs more than zero across its line, wherever it lies.

The top and a tie are not judged so. The top lies in nothing, so it gets what it asks for, and a top of no size leaves the whole piece empty, which no render of it hides. A tie lies in its part's whole frame and is drawn between its ends (the page on components, "Repeating over a list"), so its line is drawn whatever size its frame has. Nor is a part that draws a primitive, such as a box or an image, whose size is its component's own drawing (Rationale).

### 2. Not where the component it lies in has no size there

A component that asks for no size along an axis is not reported for it where the component it lies in has a size of zero there, unless its list sizes it by place (DEC-038 point 5). The component it lies in either asked for zero there, as a page that holds nothing asks for a height of zero, so nothing in it is short, or it is reported itself, by point 1, whether it asks for no size there, a size or less than zero, or it lies in turn in one of no size there. So the exemption hides no fault, save in the top and a tie, which point 1 leaves unjudged: the finding of the outermost component of no size names what emptied it, and once that one is mended, the check judges what lies in it.

Its limit: a component inside one of no size, whose own size a formula gives from roles alone, is not reported either, though the outer one's size does not reach it. It is found once the outer one is mended, and never inside one that asks for zero.

### 3. No frame has a size below zero

The engine holds at zero every size it computes below zero for a frame: the size a component gets, the size a list gives each item, and the size a part's formula gives its part. Every reader of frames reads the size so held: a formula, a tie's end, the checks and every renderer (DEC-038 point 6). It names its source as before.
- **Where held items lie.** Each item of a list lies along its line as before: its place advances from the one before by that one's held size and the gap. So an item held at zero keeps its gaps, and where the gaps take the whole line or more, the last items lie past the line's end.
- **What a list asks for** follows from the sizes it holds: under `sizes: own`, its items' held sizes and its gaps along the line, and across, the greatest size it holds. A list that shares its line asks for the line it is given, as before, so its items carry the finding, never the list.

### 4. The finding lies where the size can be mended

The finding lies at the trace of the component given no room: at the content where the size rests on what the content placed, and otherwise in the library of the component that gave the size, where a released version only asks for attention ([visual-communication:DEC-002-files-and-validation] point 7).
- **What the content placed.** A size rests on it where it follows from the size the giving component takes from where it is placed, or from how many items its list draws.
  - **A formula** rests on it where it reads, itself, through a named value or through a part of its own component, a size its component takes from where it is placed, its component's place in its list, `:index` or `:count`, an item of a list or an end of a tie, the size of a list, which follows from its count, or the size of what the content places in a slot. A size its component asks for and gets as asked rests on what its component's own formula reads. A role, an option's word and a text's measured size do not rest on it.
  - **A list that shares its line** rests on it where its gaps take a line of more than zero, since the content gave it more items than its gaps leave room for. Where its line is zero, the part's formula decides.
- **One that asks for less than zero** has its finding in the library of its own component, since its own formula is at fault, or at the content where that formula rests on what the content placed, as one that reads `:count` does.
- **An item its list sizes by place** keeps its finding at the content (DEC-038 point 5).
- **Its message** names what gave the size: the list, with its line, its gaps and how many items it draws; the list's stretch, with its line; or the part, with its formula. For one that asks for less than zero, it names that formula.

## Rationale

**Why the finding of a component that gets less.** A component that asks for no size takes what it is given, so the least it asks for is room to draw in, more than zero. Zero or less is short of that, and the check already names a component short of what it asks for, which each reader of findings reads, as DEC-038 point 5 reads a sized item's zero. A kind of finding for each source of the size would split one fault by what gave it, which the message says.

**Why the finding lies where the size can be mended.** What gives a component no room is either where it is placed or the component that gave it the size. A list given more items than its line holds gaps for, or a component placed in one narrower than its part's insets, is the content's to mend, by giving the component more room or fewer items, wherever the components come from: so the finding fails at the content, under a released library too. A formula that gives no room from roles alone, wherever its component is placed, is its library's to mend, and only the library's owner can mend it, in a new release: so the finding lies in that library, and in a released version it asks for attention, as every fault the project cannot correct in its own files does (DEC-002 point 7). An option's word and a text's measured size come from the content too, yet what a component draws from them is its own drawing: a branch that gives no room, or insets wider than a short word, is its library's to mend. The check reads what a formula reads, not why its value falls below zero. The cost is twofold:
- **A formula that reads the size its component takes,** yet gives no room wherever that component is placed, such as `=:width - :width - @space.1`, lies at the content, which cannot mend it.
- **Where a library's own part places the giving component,** the size that component takes there is the library's, yet a formula that reads it lies at the content, which mends it only by placing other components.

**Why one that asks for less than zero is reported.** A formula that asks for less than zero asks for no room, which no frame can hold, so the engine holds what the component gets at zero, and the component is then never short of what it asks. Unreported, it would vanish in silence, and by point 2 so would every component that takes its size from it. Its own formula is at fault, so its finding lies in its library, save where that formula reads what the content placed, as a width that falls by `:count` meets a list too long for it. Where a part gives it more than zero, it draws at that size, and nothing is lost.

**Why whatever gives the size.** The component is short of room whatever gave it the size, and its frame turns inside out the same way. A rule for each source leaves the next source silent, as `sizes: equal` and a part's formula were beside `cross-size`.

**Why zero, and not only below zero.** A library that means a part not to be drawn hides it by `when`, and the part then has zero size at its place (DEC-005 point 3). It never gives a component it places a size of zero for that. So a component placed at zero is no library's way of leaving it out, and it draws nothing of what the content gave it, as one below zero draws nothing. Asking for zero is the one way to mean it, as a page that holds nothing does.

**Why a component that asks for a size is judged as before.** It asks for what it needs, and the check already reports it below that, zero or less included. One that asks for zero and gets it is not short.

**Why not inside a component with no size.** Two reasons. A page that holds nothing asks for a height of zero, so every component that takes its height from it gets none: reported, an empty page would fail for the components that fill it. And a component of no size that did not ask for zero is reported itself, by point 1, so the fault that empties what lies in it has its finding, and once it is mended, the check judges what lies in it. The cost is the limit point 2 names.

**Why a sized item is reported wherever it lies.** DEC-038 point 5 takes a sized item to need more than zero across its line by its place, whatever holds it, since its size is the pattern's formula meeting the content's number of items. This record leaves that point as it stands, so point 2 does not reach it.

**Why the top and a tie are not judged.** The top lies in nothing, so no component gives it its size: it gets what it asks for, held at zero (point 3). One that asks for zero or less draws a piece of no size, which every render of it shows at once, where a card that vanishes among others may go unseen. A tie's frame is its part's whole frame, which it is given and does not draw in: its line runs between its ends, so a frame of zero hides nothing of it.

**Why every size is held at zero.** A frame below zero is no shape: SVG draws no rectangle of a width below zero, and each reader of frames would have to guess what it means. DEC-038 point 5 holds a sized item at zero for that reason, and the reason holds for every size. A part's own size is held too, since a component held at zero gives every part that reads its size, such as `=:width - 2 * @space.2`, less than zero. Holding each size where it is computed gives every reader of frames one answer, a formula that reads a part's frame among them. A held item keeps its place and its gaps, so the items after it move for nothing but the fault the finding names. A list asks for what it holds, so its frame holds its items, save a list that shares its line, which asks for the line it is given so that its items carry the finding: the cost is that its last items, held at zero, lie past its frame's end.

**Why a part that draws a primitive is not reported.** A box, an ellipse, an image or a sign takes its size from its component's formula, read from the size the component gets, and a drawn shape at zero is often meant: a bar whose share comes to nought, or a box that fills a component that holds nothing. The check cannot tell such a part from one that lost its room, so it judges none of them. A text given a width of zero or less is reported already, since every word overflows it (DEC-005 point 14). The cost: an `image` that shows the piece's own picture, which the content names ([visual-communication:DEC-025-picture-files] point 1), and a `sign` that shows the sign of the concept the content names ([visual-communication:DEC-036-concept-signs] point 2), vanish with no finding where their component's formula gives them no room, and so does a box whose insets exceed its component.

### Alternatives considered

- **A kind of finding of its own,** such as `no-room`. Rejected: one fault, a component short of the room it needs, would take two names, and every reader of findings would learn a second one.
- **The finding always at the content.** Rejected: a size a library gives from roles alone would fail in every project that places its component, under a released version too, though only the library's owner can mend it (DEC-002 point 7).
- **The finding always in the component whose part, or whose list, gave the size.** Rejected: a list given more items than its line holds, or a component placed in too little room, is the content's to mend, yet under a released library the finding would only ask for attention.
- **One finding at the list that shares its line,** not one at each item. Rejected: such a list already reports at its trace each item that gets less than it asks for, so a finding at the list for the items that ask for none would report one fault two ways in one list. And the trace a reader looks for is the item that vanished.
- **Points 1 and 2 applied to a part that draws a box, an ellipse, an image or a sign.** Left for now: a drawn shape at zero is often meant, and nothing in a part says whether its zero is, so the check would fail a bar at nought and the fill of an empty component. Telling the two apart would take a word in the format, which no case has asked for yet, and the cost of waiting is the one the Rationale names.
- **Only a size below zero reported, zero let through.** Rejected: a library hides a part by `when`, never by placing a component at zero, so no library means a component placed at zero, and it draws nothing of what the content gave it, as one below zero does.
- **The scene keeping a size below zero, reported but not held.** Rejected: every renderer would meet a frame it cannot draw, and the checks of frames would each read it their own way.
- **Each component inside one of no size reported too.** Rejected: an empty page would fail for the components that fill it, and inside one reported itself, the outer one's finding already names what emptied them.
- **Leaving it undone.** Rejected: a piece whose cards fall to no width would pass its check, and its cards would vanish from the drawing.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - **DEC-005 point 3,** "Two sizes for each element". After its last sentence, "The check takes an item a row or a column sizes by place to ask across the line for more than zero (refinement per [visual-communication:DEC-038-size-by-place] points 3 and 5).", it gains: "No size the engine computes for a frame is below zero: one that comes out below is held at zero. A component placed below the top gets more than zero along each axis, unless it asks for zero there, or asks for no size there and lies in one with no size there, where its list does not size it there by place; one that asks for a size gets at least it (refinement per [visual-communication:DEC-073-zero-sizes-reported] points 1 to 3)."
- **No other edit.** DEC-038's Implications bullet on #3113 stays as it stands: this record refines no point of DEC-038, and the bullet's words, that #3113 decides the other sources with a record of its own, stay true.
- **Read against this record, and left as they stand:**
  - DEC-005 point 14, since a component given no room is a component that gets less than it asks for, which fails where the project can correct it, and what fails gains no kind (point 4). Its "measured from a font file" bounds the failing finding to a size measured exactly. A size this record judges is a list's share of its line, a stretch or a formula's value, from roles and frames, so the finding falls on the side that fails, where it lies in a file the project can correct. Where a formula reads a text measured otherwise, the finding is read as every finding of a component that gets less than it asks for is, which this record changes in nothing.
  - DEC-005 point 5, since the scene holds every element's frame as before, only never below zero, and holds nothing new, so neither the seam's version nor any renderer's rises (DEC-005 points 8 and 9).
  - DEC-038 point 5, since a sized item still needs more than zero across its line, wherever it lies, inside a component of no size too, and its finding stays at the content (points 2 and 4).
  - DEC-038 point 6, since every reader of frames meets a frame as before, held at zero as a sized item's is (point 3).
  - DEC-002 point 7, since the finding fails only where the project can correct it: at the content where the size rests on what the content placed, and otherwise in the library that gave the size, where a released version asks for attention (point 4).
  - [visual-communication:DEC-010-list-item-fields] point 4, since the part still shares its length among its items less the gaps, in proportion to their shares. Where the gaps take the whole length, each share comes out at zero or less, and point 3 holds it at zero and places each item by its held size and the gap, which DEC-010 point 4 does not decide.
  - DEC-025 point 1 and DEC-036 point 2, since an image whose field is empty, and a sign with no concept to draw, are not drawn and have zero size at their place, with no finding, as before. A part that draws either is not judged by this record, whatever size its component's formula gives it (point 1, and the cost the Rationale names).
  - [visual-communication:DEC-003-change-over-time] point 8 and [visual-communication:DEC-001-visual-communication-discipline] point 7, since a draft meets the check at its next render, as it meets any new engine, and a final piece is not judged.
- **[project-kit#3113](https://github.com/aleskalfas/project-kit/issues/3113)** builds points 1 to 4 in the engine, with a test that draws each source of a size of zero or less: a list sharing its line among more gaps than it holds, a stretch to no size, a part's formula, a top's slot of pages, a component that asks for less than zero, and an item its list sizes by place inside a component of no size. It finds the report of each, and where each lies, at the content and in the component that gave the size.
- **The page on checks:** the row of `gets-less` comes to name a component placed below the top that gets zero or less, whatever gives it, one that asks for less than zero, what is not judged, the message, and where the finding lies.
- **The page on components:** the account of a list's `sizes`, the account of a part's places and sizes, and "What an element asks for, and what it gets" come to say what points 1 to 4 decide.
