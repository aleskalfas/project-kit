---
id: DEC-037
title: A row or a column may size each item across its line by a formula on the item's place
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a row or a column may give each of its items its size across the line by a formula on where the item stands in its list. So a column of levels can narrow each level's frame itself, not only what the level draws inside it: a tie into a level then ends at its edge, and every reference, check and renderer meets that edge as it meets any frame. For example, a column with `align-items: center` and `across: "=levels.width * (2 + :index) / (2 + :count)"` draws three levels three fifths, four fifths and the whole of its width, centred one under another.

## Context

[project-kit#3095](https://github.com/aleskalfas/project-kit/issues/3095) asks the starter's `layers` to draw a stepped form, its levels narrowing by their place, with a tie into a level ending at the level's drawn edge. Its builder stopped before writing code, since nothing lets that be drawn:
- **A tie's end reads only the element drawn for its item, and names no part** ([visual-communication:DEC-011-tie-ends] point 4). A level that narrows its box inside its frame by its own place, as a local component of the showcase deck does, takes a tie at its frame, beside the box.
- **An item cannot ask for a width that follows its line.** The only length of its line it can read is the size it gets, which is the size it asks for, so the engine refuses the loop ([visual-communication:DEC-005-engine-and-plugins] point 3).
- **No record lets a pattern size an item across its line by the item's place.** A row or a column stretches an item across its line, or gives it the size it asks for (DEC-005 points 2 and 3).

The builder saw two ways: a tie that ends at a part its item exposes, or a pattern that sizes each item across its line by the item's place. This record takes the second, and weighs the first among its alternatives.

Terms:
- A row or a column lays a list's items along a *line*. An item's *size across* is its size at right angles to the line: its height in a row, its width in a column.
- An item's *place* is its position among the items its list draws ([visual-communication:DEC-010-list-item-fields] point 6). A formula reads it from 1 as `:index`, and how many items the list draws as `:count`.

## Decision

**A row or a column may size each item across its line by a formula on the item's place, and that size makes the item's frame, which every reader of frames meets as any other.**

### 1. `across` gives each item its size across the line

A row or a column takes `across`, a formula that gives a length, which may switch on an option or a size as any of a part's values may. Where a part gives it, each item its list draws, a *sized item*, gets across the line the formula's value at that item's place, and the operator is that size's one owner (DEC-005 point 3).

### 2. The formula reads what the pattern reads, and the item's place

`across` reads what the pattern's other formulas read, its part's own frame among them, and there `:index` and `:count` give the place of the item it sizes. It reads nothing else of the item, and the pattern's own place reaches it only through one of the pattern's named values.

### 3. A sized item takes no stretch

`align-items` places a sized item on its line, `stretch` as `start`, as CSS's flexible layout places an item whose size across is set. The size is no stretch, so the item passes none on to a component it places.

### 4. A line that is given no size across takes its largest item's

Where the part gives no size across, it is as large across as the greatest size `across` gives.

### 5. What an item asks for stays its own

The item asks for its size as before, and where `across` gives it less than it asks for, the check reports it as it reports any component that gets less than it asks for (DEC-005 point 14).

### 6. Every reader of frames meets the sized frame unchanged

A tie's end, a reference to the item, the checks and every renderer, a connector's attached ends included, read a sized item's frame as they read any item's (DEC-011 point 4, DEC-005 point 5). The scene holds nothing new, so neither the seam's version nor any renderer's rises (DEC-005 points 8 and 9).

### 7. The check judges `across` as any formula

The check judges `across` as it judges any formula of the component, and adds no finding of its own (DEC-005 point 14).

### 8. An addition to format 1

`across` is optional, so every file format 1 accepted reads and draws as before, and a pattern that adds or changes it changes only how a piece looks ([visual-communication:DEC-003-change-over-time] points 3 and 6).

## Rationale

**Why the pattern sizes the item.** The founding record has a pattern decide its items' sizes ([visual-communication:DEC-001-visual-communication-discipline] point 6), and only the pattern holds the line an item lies on. With the frame at the drawn edge, everything that reads frames is right as it stands, so any item component steps and content writes nothing new. The cost: a stepped form is the pattern's, and an item component cannot step by itself where its pattern gives no `across`.

**Why a formula on place.** The design work found that a pyramid's levels need only an item's index, the count and the theme's sizes (DEC-005, Context). A formula keeps the step in the pattern's data, read from the brand's sizes, where content holds no size (DEC-001 point 3).

**Why `:index` names the sized item.** One name keeps one meaning in a formula, an item's place. A pattern that needs its own place in `across` is rare, and a named value carries it.

**Why no stretch.** The operators' names follow CSS's flexible layout where the meanings match (DEC-005 point 2), and CSS stretches only an item whose size across is not set. A size `equal` gives along the line passes nothing on either, so the two directions agree.

**Why a short item is a finding.** A pattern can leave a level too narrow for its text. The finding names it where the step is set. An item grown past its step instead would break the form in silence.

**Why the name `across`.** CSS names no size a container sets on each item. The word says where the size lies, beside `sizes`, which shares the line along it.

### Alternatives considered

- **A tie that ends at a part its item exposes.** Rejected: content would name a part its author never sees, or each item component would declare which part is its edge (DEC-011, Rationale), and the frame would stay wider than the drawing, so every other reader of frames would have to learn the part too.
- **Leaving it undone.** Rejected: the starter would keep no stepped form, and each piece would draw its own, with arrows of its own parts in place of ties content names.
- **An item that asks for its width by its place, from roles alone.** Rejected: its steps would not follow its line, so a stack in a narrow column would overflow it.
- **An engine name for the line's size across, such as `:line`.** Rejected: the part's own frame gives it, and a new name is a new tool (DEC-005 point 1).
- **An arrangement field by which each item names its width.** Rejected: content would write the form, item by item, and a level added would mean rewording the others.
- **`stretch` refused beside `across`.** Rejected: `stretch` is the default, so every sized list would have to name an alignment, where CSS reads `stretch` beside a set size already.
- **The size passed on, as a stretch is.** Rejected: an item's own formulas already read the size it gets, so the item decides where it goes inside.
- **A formula along the line too.** Rejected for now: `sizes` already shares the line, and no form needs a size along it by place.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - DEC-005 point 1, "What it may use", comes to add that in the formula by which a row or a column sizes its items across, an item's place is that of the item it sizes (point 2).
  - DEC-005 point 2, "Layout operators", comes to add that they may give each item a size across its line by a formula on its place (point 1).
- **Read against this record, and left as they stand:**
  - DEC-001 point 6, since a pattern already decides its items' sizes.
  - DEC-010 points 3 and 6, since an arrangement field keeps its words and an item's place its meaning.
  - DEC-011 point 4, since an end still reads the element drawn for its item, whose sized frame it meets (point 6).
  - DEC-003 point 6 and DEC-005 point 14, since what breaks and what fails gain nothing (points 7 and 8).
- **[project-kit#3095](https://github.com/aleskalfas/project-kit/issues/3095)** builds points 1 to 8 in the engine, the component schema and the page on components, and draws `layers`' stepped form with them. Its What and Doc impact come to name this record in place of the two ways they leave open.
