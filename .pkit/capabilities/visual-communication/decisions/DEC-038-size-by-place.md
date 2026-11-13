---
id: DEC-038
title: A row or a column may size each item across its line by a formula on the item's place
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a row or a column may give each of its items its size across the line by a formula on where the item stands in its list. So a column of levels can narrow each level's frame itself, not only what the level draws inside it: a tie into a level then ends at its edge, and every reference, check and renderer meets that edge as it meets any frame. For example, a column `levels` that is given its width, with `align-items: center` and `across: "=levels.width * (2 + :index) / (2 + :count)"`, draws three levels three fifths, four fifths and the whole of that width, centred one under another.

## Context

[project-kit#3095](https://github.com/aleskalfas/project-kit/issues/3095) asks the starter's `layers` to draw a stepped form, its levels narrowing by their place, with a tie into a level ending at the level's drawn edge. Its builder stopped before writing code, since nothing lets that be drawn:
- **A tie's end reads only the element drawn for its item, and names no part** ([visual-communication:DEC-011-tie-ends] point 4). A level that narrows its box inside its frame by its own place takes a tie at its frame, beside the box.
- **An item's frame cannot follow both its place and its line.** Under a stretch its frame is the line's size across. Otherwise it is the size the item asks for, which may read its place and the brand's sizes but not the line's, since the only size the item reads is the one it gets, and asking from that is a loop the engine refuses ([visual-communication:DEC-005-engine-and-plugins] point 3).
- **No record lets a pattern size an item across its line by the item's place.** A row or a column stretches an item across its line, or gives it the size it asks for (DEC-005 points 2 and 3).

The builder saw two ways: a tie that ends at a part its item exposes, or a pattern that sizes each item across its line by the item's place. This record takes the second, and weighs the first among its alternatives.

Terms:
- A row or a column lays a list's items along a *line*. An item's *size across* is its size at right angles to the line: its height in a row, its width in a column.
- An item's *place* is its position among the items its list draws ([visual-communication:DEC-010-list-item-fields] point 6). A formula reads it from 1 as `:index`, and how many items the list draws as `:count`.

## Decision

**A row or a column may size each item across its line by a formula on the item's place, and that size makes the item's frame, which every reader of frames meets as any other.**

### 1. `across` gives each item its size across the line

A row or a column takes `across`, a formula that gives a length, which may switch on an option or a size as any of a part's values may, and a branch of its switch may give none, leaving the list without `across` there. Where a part gives it, each item its list draws, a *sized item*, gets across the line the formula's value at that item's place, and the operator is that size's one owner (DEC-005 point 3).

### 2. The formula reads what the pattern reads, and the item's place

`across` reads what the pattern's other formulas read, and there `:index` and `:count` give the place of the item it sizes. It reads nothing else of the item. It reads its part's size across only where the part gives one, and no named value that reads `:index` or `:count`.

### 3. A sized item is placed as an item of set size, and passes its size on

`align-items` places a sized item on its line as CSS's flexible layout places an item whose size across is set, an alignment left unnamed as `start`, and a `stretch` written beside `across` is refused. What `across` gives past what the item asks for passes on as a stretch does, so a last part that places a component and gives no size across ends where the item ends.

### 4. A line that is given no size across takes its largest item's

Where the part gives no size across, it is as large across as the greatest size `across` gives.

### 5. What an item asks for stays its own

The item asks for its size as before, and where `across` gives it less than it asks for, the check reports it as it reports any component that gets less than it asks for (DEC-005 point 14).

### 6. Every reader of frames meets the sized frame unchanged

A tie's end, a reference to the item, the checks and every renderer, a connector's attached ends included, read a sized item's frame as they read any item's (DEC-011 point 4, DEC-005 point 5). The scene holds nothing new, so neither the seam's version nor any renderer's rises (DEC-005 points 8 and 9).

### 7. The check judges `across` as any formula

The check reports a part's size across that `across` reads where the part gives none as a loop of references, a named value point 2 keeps from it as a formula that reads what it may not reach, and a `stretch` point 3 refuses as a value with two owners (DEC-005 point 14). It judges `across` otherwise as any formula of the component, so a loop through the part's size along the line, where an item's size along rests on its size across, is refused as any loop, and it adds no kind of finding.

### 8. An addition to format 1

`across` is optional, so every file format 1 accepted reads and draws as before ([visual-communication:DEC-003-change-over-time] point 3). A pattern that adds or changes `across` changes only how a piece looks, which breaks nothing (DEC-003 point 6), and a draft that moves to it may then fail where an item gets less than it asks for (point 5, DEC-003 point 8).

## Rationale

**Why a tool of the engine.** A need becomes a tool of the engine when it recurs ([visual-communication:DEC-001-visual-communication-discipline] point 4, DEC-005 point 2), and this one has: the talk the design work studied drew a pyramid's levels from their place (DEC-005, Context), and a deck's stepped pyramid was lost when the deck moved into the capability ([visual-communication:DEC-029-piece-brief] and [visual-communication:DEC-030-design-agents], Context).

**Why the pattern sizes the item.** The founding record has a pattern decide its items' sizes (DEC-001 point 6), and only the pattern holds the line an item lies on. With the frame at the drawn edge, everything that reads frames is right as it stands, so any item component steps and content writes nothing new. The cost: a stepped form is the pattern's, and an item component cannot step by itself where its pattern gives no `across`.

**Why a formula on place.** A level's step reads its place and, to follow its line, the line's size, which the pattern holds and its item cannot read. So the formula lies in the pattern's data, read from the brand's sizes and the line's, where content holds no size (DEC-001 point 3), as a pattern's colour family for each place does (DEC-010 point 6).

**Why `across` reads so little.** Where the part gives no size across, that size is the greatest `across` gives (point 4), so reading it would read `across` itself. A named value is computed once for the pattern, so `:index` in it gives the pattern's own place where the pattern is itself an item, and moving a term of `across` into one would change its meaning in silence. The cost: the pattern's own place reaches no item's size, which no known form needs.

**Why a sized item is placed so, and passes its size on.** The operators' names follow CSS's flexible layout where the meanings match (DEC-005 point 2), and CSS stretches no item whose size across is set. A `stretch` written beside `across` would set that size a second time, where one owner sets each value (DEC-005 point 3). A last part that gives no size across has its component end where its item ends, as a panel that holds panels ends with its row's other panels, and a sized item keeps that.

**Why the check judges only what an item asks for.** An item whose component asks for its size across, such as a tag as wide as its label, is reported where `across` gives it less, since growing it past its step would break the form in silence. One that asks for none, such as a card as wide as it is given, wraps its text to the size it gets and grows along the line, as in any narrow line, with no finding. The cost: a stepped list of cards draws its narrow levels taller than its wide ones. How `layers` keeps its levels one height is [project-kit#3095](https://github.com/aleskalfas/project-kit/issues/3095)'s to build, for example by giving each level its height, and a level too narrow for its text then gets less height than it asks for, which is reported.

**What it costs a draft.** A pattern that adds `across` narrows its items, as one that narrows a part's width already may, and a draft takes such a change of look at its next render (DEC-003 point 8), where an item that then gets less than it asks for fails it. A library keeps it from drafts by giving a stepped form under an option, never as its default, as `layers` does in #3095, so no draft changes unasked.

**Why the name `across`.** CSS's flexible layout sets no item's size from its container, and CSS Grid's track sizes do so for tracks, which a row or a column lacks. Beside `sizes`, which shares the line along it, the word names the size the operator gives across it.

### Alternatives considered

- **A tie that ends at a part its item exposes.** Rejected: only an item component that narrowed its own box and exposed it would step, so content that names another component for a level loses the step, where under `across` any item component steps.
- **An item that narrows its own frame inside a stretch, by an inset it declares.** Rejected: as above, only an item component that declares one steps.
- **Leaving it undone.** Rejected: the starter would keep no stepped form, and each piece would draw its own, with arrows of its own parts in place of ties content names.
- **An item that asks for its width by its place, from roles alone.** Rejected: its steps would not follow its line, so a stack in a narrow column would overflow it.
- **A fixed word of narrowing, such as `across: narrowing`.** Rejected: it draws one form, where one formula also draws a diamond, a funnel or an upturned pyramid.
- **A share of the line's size across, with no unit.** Rejected: a step by the brand's sizes, such as a role's length less at each place, could not be said, and a line given no size across has none to share.
- **An engine name for the line's size across, such as `:line`.** Rejected: where the part gives that size `across` reads it already, where it gives none the size rests on `across` (point 4), and in an item's own formulas it would read upward (DEC-005 point 3).
- **A name of its own for the sized item's place.** Rejected: a named value, computed once for the pattern, could not read it either, so the check would stay, and an item's place would take two names.
- **An arrangement field by which each item names its width.** Rejected: content would write the form, item by item, and a level added would mean rewording the others.
- **Every `stretch` refused beside `across`, the default included.** Rejected: every sized list would have to name an alignment.
- **A written `stretch` read as `start`.** Rejected: a list that names `stretch` and gains `across`, as `layers` would, would draw its items at the line's start in silence.
- **The size kept from a component the item places.** Rejected: a last part that gives no size across would end at what its component asks for, short of the item's frame, the gap between frame and drawing this record closes.
- **A formula along the line too.** Rejected for now: `sizes` already shares the line, and no form needs a size along it by place.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-005 point 1, "What it may use", comes to add that in the formula by which a row or a column sizes its items across, an item's place is that of the item it sizes (point 2).
  - DEC-005 point 2, "Layout operators", comes to add that they may give each item a size across its line by a formula on its place (point 1).
- **Read against this record, and left as they stand:**
  - DEC-001 point 6, since a pattern already decides its items' sizes.
  - DEC-010 points 3 and 6, since an arrangement field keeps its words and an item's place its meaning.
  - DEC-011 point 4, since an end still reads the element drawn for its item, whose sized frame it meets (point 6).
  - DEC-005 points 3 and 14, since the operator is a sized item's one owner across, and what fails gains no kind (points 1, 3 and 7).
  - DEC-003 points 6 and 8, since what breaks gains nothing, and a draft takes `across` as any change of look (point 8).
- **[project-kit#3095](https://github.com/aleskalfas/project-kit/issues/3095)** builds points 1 to 8 in the engine, the component schema and the page on components, and draws `layers`' stepped form with them, under an option and never as its default. Its What and Doc impact come to name this record in place of the two ways they leave open.
