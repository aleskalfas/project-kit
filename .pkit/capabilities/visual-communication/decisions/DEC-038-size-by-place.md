---
id: DEC-038
title: A row or a column may size each item across its line by a formula on the item's place
status: accepted
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a row or a column may give each of its items its size across the line by a formula on where the item stands in its list. So a column of levels can narrow each level's frame itself, not only what the level draws inside it: a tie into a level then ends at its edge, and every reference, check and renderer meets that edge as it meets any frame. For example, a column `levels` that is given its width, with `align-items: center` and `cross-size: "=levels.width * (2 + :place) / (2 + :places)"`, draws three levels three fifths, four fifths and the whole of that width, centred one under another. The record also states, for a stretch as for `cross-size`, how an item given more than it asks for across the line passes the rest on to the last part it draws.

## Context

[project-kit#3095](https://github.com/aleskalfas/project-kit/issues/3095) asks the starter's `layers` to draw a stepped form, its levels narrowing by their place, with a tie into a level ending at the level's drawn edge. Its builder stopped before writing code, since nothing lets that be drawn:
- **A tie's end reads only the element drawn for its item, and names no part** ([visual-communication:DEC-011-tie-ends] point 4). A level that narrows its box inside its frame by its own place takes a tie at its frame, beside the box.
- **An item's frame cannot follow both its place and its line.** Under a stretch its size across the line is the line's. Otherwise it is the size the item asks for, which may read its place and the brand's sizes but not the line's, since the only size the item reads is the one it gets, and asking from that is a loop the engine refuses ([visual-communication:DEC-005-engine-and-plugins] point 3).
- **No record lets a pattern size an item across its line by the item's place.** A row or a column stretches an item across its line, or gives it the size it asks for (DEC-005 points 2 and 3).

The builder saw two ways: a tie that ends at a part its item exposes, or a pattern that sizes each item across its line by the item's place. This record takes the second, and weighs the first among its alternatives.

Terms:
- A row or a column lays a list's items along a *line*. An item's *size across* the line, CSS's *cross size*, is its size at right angles to the line: its height in a row, its width in a column.
- An item's *place* is its position among the items its list draws ([visual-communication:DEC-010-list-item-fields] point 6). Its own formulas read it from 1 as `:index`, and how many items the list draws as `:count`.

## Decision

**A row or a column may size each item across its line by a formula on the item's place, and that size makes the item's frame, which every reader of frames meets as any other.**

### 1. `cross-size` gives each item its size across the line

A row or a column takes `cross-size`, a formula that gives a length, which may switch, as any of a part's values may, on an option or a size, or in a drawing of a layout on `:as`. A branch of its switch may give none, leaving the list without `cross-size` there. Where a part gives it, each item its list draws, a *sized item*, gets across the line the formula's value at that item's place, and `cross-size` is that size's one writer (DEC-005 point 3). A part whose items are pages takes none.

### 2. The formula reads what the pattern reads, and the item's place by names of its own

`cross-size` reads what the pattern's other formulas read, and the place of the item it sizes as `:place`, from 1, with how many items its list draws as `:places`, marked names ([visual-communication:DEC-021-size-and-shape], Context) that no other formula reads. It reads nothing the item carries, so it switches on no arrangement field. It reads its part's size across the line only where the part gives one.

### 3. A sized item is placed as one of set size, and a list's extra size across the line passes to the item's last part

`align-items` places a sized item on its line as CSS's flexible layout places an item whose size across the line is set, an alignment left unnamed as `start`, and a `stretch` written beside `cross-size` is refused. Where such a `stretch` is drawn, the engine places the sized items as though `align-items` were left unnamed. What a list gives an item across the line past what the item asks for, by a stretch or by `cross-size`, passes on to the last part the item draws where that part places a component and gives no size across the line, and that component passes it on the same way. The size passed on names `engine` as its source, and the item's own formulas still read that last part at the size the part asks for. An item that asks for no size across the line passes nothing on, nor does a component that a part's formula gives more than it asks for.

### 4. A part asks across its line for the greatest size `cross-size` gives

A part that gives `cross-size` asks across its line for the greatest size the formula gives at any place, or zero, whichever is greater, and for zero where its list draws no item, whether or not the part gives its own size across the line. Where it gives none, the part is that size, and where it gives less, the check reports the part as a list that gets less than it asks for (DEC-005 point 14).

### 5. What an item asks for stays its own, and a sized item needs more than zero

The item asks for its size as before, and the check takes a sized item to ask across the line for more than zero besides. Where `cross-size` gives it less than it asks for, zero or less included, the check reports it as any component that gets less than it asks for (DEC-005 point 14). Where it gives zero or less, the size the item gets across the line is held at zero, so its frame never inverts.

### 6. Every reader of frames meets the sized frame unchanged

A tie's end, a reference to the item, the checks and every renderer, a connector's attached ends included, read a sized item's frame as they read any item's (DEC-011 point 4, DEC-005 point 5). Its size across the line names as its source what a part's formula names: the option, the size axis or `:as` that chose it, the one role it reads, or its pattern's own value. The scene holds nothing new, so neither the seam's version nor any renderer's rises (DEC-005 points 8 and 9).

### 7. The check judges `cross-size` as any formula, and its refusals when it reads the component

When it reads the component, the check reports:
- `cross-size` on a part whose items are pages (point 1), as a key its format does not allow;
- `:place` or `:places` in any formula but `cross-size`, as a formula that reads what it may not reach;
- `cross-size` that reads its part's size across the line where the part gives none, itself or through a named value, as a loop of references;
- a `stretch` written beside a `cross-size` that gives a size, as a value with two owners.

It judges the loop and the two owners for each set of options or sizes that hold together. It judges `cross-size` otherwise as any formula, so a loop through an item of its own list, another part, its part's size along the line or its component's own size is found when the scene is computed, as any loop is, and it adds no kind of finding.

### 8. An addition to format 1

`cross-size` is optional, and `:place` and `:places` are marked names format 1 refused, so every file format 1 accepted reads and draws as before ([visual-communication:DEC-003-change-over-time] point 3). A pattern that adds or changes `cross-size` changes only how a piece looks, which breaks nothing (DEC-003 point 6), and a draft that moves to it may then fail where an item gets less than it asks for (point 5, DEC-003 point 8).

## Rationale

**Why a tool of the engine.** Data can narrow what an item draws, but not its frame by both its place and its line (Context). A need data cannot express is met for one piece by a helper, and becomes a general tool of the engine where it recurs ([visual-communication:DEC-001-visual-communication-discipline] points 4 and 8). A form in a shared library, such as the starter's `layers`, serves every piece that uses it, which no helper, run for one piece, can serve. Stepping inside a component already costs a component of its own: a deck's pyramid, lost in its port ([visual-communication:DEC-029-piece-brief], Context), steps again only through one.

**Why the pattern sizes the item.** The founding record has a pattern decide its items' sizes (DEC-001 point 6), and only the pattern holds the line an item lies on. With the frame at the drawn edge, everything that reads frames is right as it stands, so any item component that draws to the size it gets steps, and content writes nothing new. One that draws at its own size, such as the starter's `link`, steps only its frame, as a stretch widens only its frame today. The size is the pattern's value, written in its data as a part's formula is, so it names its source as one does, and an edit taken back finds the option or the pattern that set it. The cost: a stepped form is the pattern's, and an item component cannot step by itself where its pattern gives no `cross-size`.

**Why a formula on place.** A level's step reads its place and, to follow its line, the line's size, which the pattern holds and its item cannot read. So the formula lies in the pattern's data, read from the brand's sizes and the line's, where content holds no size (DEC-001 point 3), as a pattern's colour family for each place does (DEC-010 point 6).

**Why `:place` and `:places`.** Names that only `cross-size` reads keep every reach in a formula's own text: `:index` and `:count` mean the component's own place wherever they are written, and `:place` written in a named value or a part's formula fails as any formula that reads what it may not reach. They take the word by which a pattern already gives each place its colour (DEC-010 point 6), and as numbers with no unit they are never read as a frame's place, which is a length. The cost: a step that varies by place is written inline in `cross-size`, never in a named value.

**Why `cross-size` reads so little.** Where the part gives no size across the line, that size is the greatest `cross-size` gives (point 4), and the frame of each item of its list is computed with every size it gives, so reading either would read `cross-size` itself. The check finds a read of the part's size, directly or through a named value, when it reads the component, so no empty list hides it, and judges it for each set of options or sizes that hold together, since the part's size may itself be switched. A read through another part, or through the component's own size, is found when the scene is computed, as every other loop is. It reads nothing an item carries, since the form is the pattern's and content would otherwise write it item by item, and allowing such a read later is an addition (DEC-003 point 3).

**Why not over pages.** A tie lies on one page with both its ends (DEC-011 point 4), so the need this record meets never arises for a page. The refusal limits where `cross-size` reaches: refusing now can be lifted later as an addition (DEC-003 point 3), where allowing now could not be taken back within format 1.

**Why a sized item is placed as one of set size.** The operators' names follow CSS's flexible layout where the meanings match (DEC-005 point 2), and CSS stretches no item whose size across the line is set.

**Why a `stretch` beside `cross-size` is refused.** Both settings are the parent's layout, yet each writes the size apart, so a `stretch` beside `cross-size` is a second writer of one size (DEC-005 point 3). CSS reads such a `stretch` as `start`, and this record departs from it on purpose (Alternatives considered). Judging it for each set of options or sizes that hold together lets a library switch between a stretch and `cross-size`, and finds, in the library's own check, a pair that only some piece's options would draw. Drawn anyway, the size stays `cross-size`'s, as a text keeps its measured height beside a height its part gives.

**Why a list's extra size passes to the item's last part.** Passing it on lets a last part that gives none end where its item ends, for an item that asks for its size across the line, as a panel that holds panels ends with its row's other panels. The item's own formulas read that part at what it asks for, so what the item asks never rests on what it is given. No formula writes the size passed on, so the engine that computes it is its source.

**Why a part asks for the greatest size `cross-size` gives.** A part that asked what its items ask would let a step wider than the part spill out of it with no finding, and would need a size from an item that asks for none.

**Why the check judges only what an item asks for.** An item whose component asks for its size across the line, such as a tag as wide as its label, is reported where `cross-size` gives it less, since growing it past its step would break the form in silence. One that asks for none, such as a card as wide as it is given, wraps its text to the size it gets and grows along the line, as in any narrow line, with no finding of its size, though a word wider than its narrowest step overflows its box. The cost: a stepped list of cards draws its narrow levels taller than its wide ones.

**Why a sized item needs more than zero.** A step that falls to zero or below at a late place is the pattern's formula meeting the content's number of items, not a fault of the item's component. As an item that gets less than it asks for, it is reported at the content, which the project can correct, so it fails validation (DEC-005 point 14), even where the item's component comes from a released library. Holding the size it gets at zero keeps a frame below zero from every reader of frames (point 6).

**What it costs a draft.** A pattern that adds `cross-size` narrows its items, as one that narrows a part's width already may, and a draft takes such a change of look at its next render (DEC-003 point 8), where an item that then gets less than it asks for fails it. A library keeps it from drafts by giving a stepped form under an option, never as its default, as `layers` does in #3095, so no draft changes unasked.

**Why the name `cross-size`.** CSS's flexible layout calls an item's size at right angles to its line its cross size, and the operators take CSS's names where the meanings match (DEC-005 point 2). The capability says across and down for width and height (DEC-005 point 3), so a key named `across` would have set a height in a row.

### Alternatives considered

- **A tie that ends at a part its item exposes.** Rejected: only an item component that narrowed its own box and exposed it would step, so content that names another component for a level loses the step, where under `cross-size` any item component that draws to the size it gets steps.
- **An item that narrows its own frame inside a stretch, by an inset it declares.** Rejected: as above, only an item component that declares one steps.
- **A tie that ends at the outer edge of what its item draws, not at its frame.** Rejected: every tie's end would move, a mark drawn past an item's frame would move its ties, and references and the checks would still meet the frame.
- **Leaving it undone.** Rejected: the starter would keep no stepped form, and each piece would draw its own, with arrows of its own parts in place of ties content names.
- **An item that asks for its width by its place, from roles alone.** Rejected: its steps would not follow its line, so a stack in a narrow column would overflow it.
- **A fixed word of narrowing, such as `cross-size: narrowing`.** Rejected: the engine would know a form by name, where it knows none and computes with general tools (DEC-001 point 4), of which a formula is one.
- **A share of the part's size across the line, with no unit.** Rejected: a step by the brand's sizes, such as a role's length less at each place, could not be said, and a part given no size across the line has none to share.
- **A marked name for the part's size across the line, such as `:line`.** Rejected: where the part gives that size `cross-size` reads it already, where it gives none the size rests on `cross-size` (point 4), and in an item's own formulas it would read upward (DEC-005 point 3).
- **`:index` and `:count` in `cross-size` for the sized item's place, with a check on the named values it reads.** Rejected: one name would mean two places by where it is written, and the check would have to follow named values and parts to keep the pattern's own place out of an item's size.
- **`cross-size` that reads what an item carries, such as an arrangement field's word by which it names its width.** Rejected: a level added would mean rewording the others.
- **A sized item given zero or less reported as a component given no size.** Rejected: the finding would lie in the item's library, in a released version only asking for attention, and say "none" of a size below zero.
- **Every `stretch` refused beside `cross-size`, the default included.** Rejected: every sized list would have to name an alignment.
- **A written `stretch` read as `start`, as CSS reads it.** Rejected: a list that names `stretch` and gains `cross-size`, as `layers` would, would draw its items at the line's start in silence.
- **The size kept from a component the item places.** Rejected: a last part that gives no size across the line would end at what its component asks for, short of the item's frame, the gap between frame and drawing this record closes.
- **A formula along the line too.** Rejected for now: `sizes` already shares the line, and no form needs a size along it by place.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - DEC-005 point 1, "What it may use", comes to add that the formula by which a row or a column sizes its items across their line reads the place of the item it sizes, and how many items its list draws, by marked names no other formula reads (point 2).
  - DEC-005 point 2, "Layout operators", comes to add that they may give each item a size across its line by a formula on its place, where its items are no pages (point 1).
  - DEC-005 point 3, "Two sizes for each element", comes to add that what a list gives an item across its line past what the item asks for passes on to the last part the item draws where that part places a component and gives no size across the line, from an item that asks for that size, on the terms of DEC-038 point 3, naming `engine` as its source; and that the check takes an item a row or a column sizes by place to ask across the line for more than zero (points 3 and 5).
- **Read against this record, and left as they stand:**
  - DEC-001 points 4 and 6, since a recurring need becomes a general tool, and a pattern already decides its items' sizes.
  - [visual-communication:DEC-007-starter-library] point 2, since `layers` keeps its one job, what rests on what, with its stepped form under an option.
  - DEC-010 points 3 and 6, since an item's place keeps its meaning, and an arrangement field its words: point 3 decides who may choose by an arrangement field and for what, not which of the pattern's tools must take one.
  - DEC-011 point 4, since an end still reads the element drawn for its item, whose sized frame it meets (point 6).
  - DEC-005 points 5 and 14, since a sized item's size names a source the scene already knows, and what fails gains no kind (points 6 and 7).
  - [visual-communication:DEC-034-brand-drawings] point 2, since it decides who writes a page's size, not which tools may write it, and `cross-size` reaches no page (point 1).
  - DEC-003 points 3, 6 and 8, since `cross-size` is an addition, what breaks gains nothing, and a draft takes `cross-size` as any change of look (point 8).
- **[project-kit#3095](https://github.com/aleskalfas/project-kit/issues/3095)** builds points 1 to 8 in the engine, the component schema and the pages on components and checks, draws `layers`' stepped form with them under an option, never its default, and renders that option in the languages that stress text ([visual-communication:DEC-007-starter-library] point 3).
- **[project-kit#3113](https://github.com/aleskalfas/project-kit/issues/3113)** decides whether and how a size below zero from another source is reported, as an item's under a list with `sizes: equal` whose gaps exceed its line, or a placed component's under a part's formula, with a record of its own if the choice needs one. Point 5 decides it for `cross-size` alone.
- **The lines of the page on components that #3095 changes:**
  - the formula table's row "`:index`, `:count`", beside which `:place` and `:places` come;
  - what the engine finds when it reads the component, which comes to hold `:place` and `:places` outside `cross-size`, the loop through the part's own size, the refusal over pages and the `stretch` refusal, and what it finds when it computes the scene, which comes to leave that loop out;
  - the operator table's `align-items` row, and "The part's own size, where it gives none";
  - "A stretch reaches the part drawn last", which comes to cite this record, and "Only a stretch passes on", rewritten so that `cross-size` passes on too;
  - `engine` among the sources, which names an item's frame.
- **The rows of the page on checks that #3095 widens:** `two-owners`, `gets-less`, `loop`, `formula-reach` and `component-shape`.
- **The component schema's description of `align-items-value`,** which names `stretch` the default, as a value left out beside `cross-size` no longer is.
