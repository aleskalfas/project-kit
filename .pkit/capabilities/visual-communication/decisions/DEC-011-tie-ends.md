---
id: DEC-011
title: A tie names its two ends in fields its pattern declares, each by the keys and ids that lead to its item
status: accepted
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a *tie*, such as an arrow from one card to another, is an item of a list that its pattern draws between two other items, its ends. The pattern declares two fields on that list, for where a tie starts and where it ends. Content fills each with the keys and ids that lead to the item, such as `left[living-docs]` for an item of the list `left`, so it reaches an item inside a nested component, which exposes nothing for it. A tie whose end is not found is left out and reported, and a draft does not move to library versions that would lose one of its ends.

## Context

The record of a list's fields leaves to this one whether a field on an item may name another item ([visual-communication:DEC-010-list-item-fields] point 3). The capability's design work drew a slide whose cards in one column were each tied to items of a group that a pattern in the other column drew ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)). The slice that builds the engine's connectors ([visual-communication:DEC-005-engine-and-plugins] point 2) draws that slide ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501)), and until validation accepts files at an older format number, the format grows only by additions that every file format 1 accepted still meets ([visual-communication:DEC-003-change-over-time] point 3).

## Decision

**A pattern declares two end fields on its list of ties, and content fills each with the key path that leads to the item the tie ends at.**

### 1. A tie is an item whose two ends are fields its pattern declares

- **A tie** is an item that its pattern draws with the connector tool between two other items, its *ends*, such as an arrow from a card to a step (DEC-005 point 2). The list that holds it is a *list of ties*, and a part of the pattern repeats over it.
- **Two end fields, in order.** The pattern declares its list of ties and two *end fields* for it, such as `from` and `to`: the first where each tie starts, the second where it ends. Content says which items each tie joins, as it says what any list holds.
- **A kind of field of its own.** An end field is a field for the pattern's arrangement, which the founding record lets an item carry ([visual-communication:DEC-001-visual-communication-discipline] point 6), but no arrangement field: it names an item, has no default, and every tie gives it, where an arrangement field takes a word, has a default and names no item (DEC-010 points 2 and 3). Each kind keeps the rules that hold of all its fields.
- **Declared and read as arrangement fields are.** The pattern declares a list's end fields apart from its own fields and options, never in the list field's `items` schema, and reads them on the item, whose component never does (DEC-010 point 2). An end field takes the shape of a name, and no reserved key's name ([visual-communication:DEC-002-files-and-validation] point 4). A key that both the tie's component and its list declare is read by neither, so the tie lacks that end and is left out (point 4).
- **Given its ends.** The tie's component, the list's default or one content names (DEC-010 point 1), reads no end field. The pattern gives it its two ends, the elements drawn for the items or the points the ends name, with their frames, and a component that can be given them *takes ends*. Where a tie meets an end, and how the ties that meet one side spread, is the connector tool's (DEC-005 point 2).
- **Drawn where it is declared.** A list of ties is drawn by the component that declares its end fields, with a part of its own, or, for a top, of the drawing that draws its layout (point 5). No part passes it on to a component it places, so a slot that should hold a pattern of ties, such as a network, holds that pattern as content places it, with its own list of ties.
- **Every item a tie.** In a list of ties every item is a tie, one that names its own component included, and its component takes ends. A note beside a tie belongs to a list of its own.
- **Its own colour.** A tie takes its colour family as every item does, from its own concept, else its place, else its component (DEC-010 point 6), and from neither end.

### 2. An end field names an item, in the shape of an option's value

- **Its shape** is that of format 1's option that names an item: `{item: <key path>}`, or `{item: <key path>, point: <name>}` for a point its item exposes, as a connector ends at a picture's point ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 2). Its `item` holds a key path (point 3), where an option's holds an id alone.
- **Required.** An end has no default, as an option that names an item has none.
- **No arrangement field names an item.** A pattern names an item in an end field, which answers what the record of a list's fields leaves open (DEC-010 point 3).

### 3. Content names an end by its key path

- **The key path** starts at a field of the content mapping that holds the tie's list. It names each field that leads to the item, joined by `.`, and in each list the item by its id, as `[<id>]`, and it ends at an item: `left[living-docs]` names an item of the list `left`. Each item on the path carries an id, as whatever a part of the piece names does (DEC-001 point 3).
- **The content file's own keys.** Where a component passes content on under other names, the path keeps the names the content file writes. So it holds only keys and ids its author writes, and names no part of any component.
- **The grammar of a place in a content file,** which a finding's location writes after `#` (DEC-002 point 4), with two differences: the path starts at the mapping that holds the tie's list, not at the file's top, and it names each item by its id alone, never by its place.
- **In every end,** one in the pattern's own list included, and the same in every language, since each language's content holds the same fields and ids (DEC-001 point 3).
- **Below the pattern.** Both ends lie below the pattern that draws the tie, so a tie between items of two components placed apart is drawn by a pattern that holds both.
- **Two separate items, one for each end.** An end is never a tie, the two ends are never one item, and neither end's path leads through the other's. A tie that joins one item to several is several ties, each with its own trace, state and concept.
- **Judged in content.** The check reads these from the key paths alone. Whether two ends whose paths lie apart but whose items overlap in the drawing are a finding is left to the change that builds connectors.

### 4. An end is its item where a component draws it

- **Found through what draws it.** The end is the element the engine draws for its item, under the content's options, wherever a component below the pattern draws it: in the pattern's own list, or in one a component below it draws, at any depth. The pattern reads the element and its frame as it reads an exposed part's frame (DEC-005 point 3). The frames are computed in the order the references give, and a loop through them is refused.
- **Nothing exposed by the components between.** An end names no part, and reads only the element drawn for its item, so each component between keeps its parts' names private, and its library may rename or rearrange them without a breaking change (DEC-005 point 3). A point an end names is one its item's own component exposes, as format 1 asks of every point.
- **What becomes visible.** Where a component draws the items content gives it, and whether it draws each once, reaches the pattern above it. A moved item moves a tie's end, which changes only how a piece looks.
- **Found once, on the tie's page, at each key** (refinement per [visual-communication:DEC-021-size-and-shape]). An end is judged at each key the piece names. It is *found* at a key where its item is drawn exactly once, on the page its tie is drawn on, and not where its item is drawn nowhere or more than once. Two parts that repeat over one list under options, or sizes, that never hold together draw each of its items once.
- **Left out where it cannot be drawn.** A tie whose end is not found at a key, or that does not lie on one page with both its ends, is left out of the drawing there, and the rest of its list is drawn. The check reports it at that key (point 8).
- **Versions that lose an end do not fit together** (refinement per [visual-communication:DEC-021-size-and-shape]). A draft's render moves its lock only to versions that fit together (DEC-003 point 8), and versions do not fit, for a piece, where an end that its lock finds at a key would not be found there. The render holds such versions back, though the loss may show only in a combination of them, and states the versions it held back, with the tie, the end and the key. Where a person moves a lock to such versions, the tie is a finding.
- **An end its lock does not find holds nothing back,** as under a new piece's first lock, for a library a piece names for the first time, or for a tie just written. Where such versions lose the end, the tie is a finding. A person mends it by moving the lock by hand to older versions under which the end is found, where the project holds them, or by changing the tie or the content's options, and from then on the render keeps the draft from versions that lose the end.

### 5. In a top whose layouts a brand may draw, the top declares the end fields

- **Declared with the layout's slots.** Where a list of ties is a slot of a layout, such as a slide's ties between its two columns, the top declares the list's end fields in the layout, as it declares the slots ([visual-communication:DEC-009-layout-defaults] point 1, DEC-010 point 5). Content gives them as it gives what the top declares, never what a brand's drawing declares (DEC-009 point 5).
- **Every drawing takes them.** A drawing of the layout takes the list's end fields with its slots, and draws each tie between its ends with a part of its own (point 1). A brand's drawing declares no end field of its own. The record of layouts' findings on a drawing read the end fields as fields the top declares, so a drawing that takes one the top does not declare fails, and one that does not take one the top declares asks for attention (DEC-009 point 9).
- **A drawing that loses an end does not fit.** A brand's drawing fits an instance only where each end of the ties the instance gives is found under it (point 4). Where one is not, the top's own drawing draws the instance whole (DEC-009 point 6), and the check states it (DEC-009 point 9).
- **No draft held back for a brand's drawing.** A brand version whose drawing would lose an end loses none in the piece, since the top's own drawing then draws that instance, so the versions fit together under point 4, and only how the instance looks changes. Where the drawing that draws the instance loses an end, point 4 holds.
- **A tie that only a brand's drawing finds.** Where the top's own drawing loses an end that the brand's drawing finds, the tie is a finding once the piece switches to a brand that leaves the layout to the top, and the finding names the top.

### 6. What breaks

The record of change over time counts removing or renaming an end field, or changing what it means, as a breaking change of its library ([visual-communication:DEC-003-change-over-time] point 6). Beyond it:

- **Breaking, for a pattern or a top:** declaring end fields for a list field or a slot it holds, whether or not a part of it repeats over that list, and swapping which end field a tie starts at.
- **Breaking, for a component:** ceasing to take ends.
- **Not breaking:** a new list of ties with its end fields, or a change of where a component draws an item (point 4, DEC-003 point 6).
- **A loss a release and a tie make together.** A component's new version may draw a list's items twice, or not at all, where a piece's tie ends. Its library cannot see the piece's tie when it releases, and may lie apart from the pattern's, so the release breaks nothing on its own side, and point 4 takes the loss up.

### 7. What this adds to format 1, and what still holds

- **Every addition is optional.** Every file format 1 accepted is read and drawn as before, and none of point 8's findings arises from one.
- **An option keeps its form,** naming an item of a list its component repeats over by its id alone, and arrangement fields keep theirs. The schema of a content file gains no key, since it names no key of an item.

### 8. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct (DEC-002 point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it. A final piece's drawing is not judged.

- **Where each lies.**
  - A finding on what a pattern, a top or a brand's drawing declares lies in its version, a drawing's in its brand's. A list of ties whose default component takes no ends is judged when the declaring library is checked alone, as a clash with that component is (DEC-010 point 9), and a brand's drawing when the brand is checked alone (DEC-009 point 9).
  - A finding on an end, or on a tie's component, lies in the content file, at the tie. One on an end that is not found, or on a tie off its page, names both mends, the content and the lock, since the tie and the content's options decide it under the versions the lock names.
  - A key that both the tie's component and its list declare is the record of a list's fields' finding (DEC-010 point 9).
- **Fails validation:**
  - in a pattern or a top: end fields for a list that no part of it repeats over as ties, or more or fewer than two for one list
  - in a pattern or a top: an end field that does not take the shape of a name, or takes a reserved key's name
  - in a pattern or a top: an end field with the name of an arrangement field of its list, or one that the list's default component also declares, since the pattern chose both
  - in a pattern or a top: a list of ties whose default component takes no ends
  - in a component: a part that passes a field on to a list of ties of the component it places
  - in a brand's drawing: an end field of its own, or a list of ties whose default component takes no ends, or declares a field or an option with the name of an end field the top declares
  - in content: a tie whose component, named by its list's component field or by its own `use`, takes no ends
  - in content: a tie that leaves an end field out, or fills it with another shape than point 2's
  - in content: a key path that names a key no component on the way declares as a field and no layout as a slot, steps into a list with no id or into a field that is no list with one, names an id its list lacks, or ends at no item
  - in content: an end that names a tie, two ends that name one item, or an end whose path leads through the other's
  - in content: a point that the item's component does not expose
  - in content: an end that is not found under the versions the lock names, or a tie that does not lie on one page with both its ends
- **Stated as a fact:**
  - at a piece, versions that its draft's render held back because an end would be lost, with the tie and the end
  - at a piece, an instance that the top's own drawing draws because the brand's drawing would lose an end of its tie, as the record of layouts states a drawing that does not fit (DEC-009 point 9)

## Rationale

**Why fields the pattern declares, and not options of the tie's component.** The ends lie below the pattern, which the tie's component neither holds nor reads, and a reference reads only below its own component (DEC-005 point 3). Which items a tie joins is the pattern's to draw, as the founding record has a pattern decide the arrows between its items (DEC-001 point 6). Kept on the list, the ends also stay with a tie that names its own component, whatever that component declares.

**Why end fields stand apart from arrangement fields.** Counted as an arrangement field, an end would break each rule that defines one, and adding one to a list would ask something of content. As a kind of its own, it shares with arrangement fields only what the record of a list's fields says of every key a list declares on its items (DEC-010 point 2), and arrangement fields keep their rules whole.

**Why two end fields, in order.** A connector may carry an arrowhead at its start, at its end or at both, so a tie has a direction. The pattern names its ends as fits its subject, and the tie's component reads neither name, so their order gives that component its start and its end, and one tie component serves every pattern.

**Why the tie's component is given elements, not only frames.** Whatever spreads the ties that meet one side of an item must know which item each tie meets (DEC-005 point 2). A medium with connectors of its own attaches a line to an object, so the scene keeps which element each end meets (DEC-005 point 5). Two frames of numbers would lose both.

**Why a list of ties is drawn where it is declared.** Content writes the end fields' names on every tie, so they are names a piece uses, which the release of the component that declares them keeps (DEC-003 point 6). A component that a part places is its placer's private choice (DEC-005 point 3), so a placer that swapped it would rename every tie's ends in a release that breaks nothing it promised.

**Why every item of a list of ties is a tie.** The pattern gives each item's component two ends. An item drawn by a component that takes no ends, such as a note, would have nowhere to draw, and its ends nothing to join.

**Why the shape of an option's value.** Content then writes one shape wherever it names an item, `{item: …}`, with a point beside it where it ends at one. An end field names no list, so its `item` holds the key path, and an id, which holds no `.` and no `[`, is never read as one.

**Why the key path, in every end.** An id is unique only in its list, so whatever names an item names its list too (DEC-002 point 4), and an end field, unlike an option's declaration, names no list. The key path names each list on the way, so an end's meaning rests on its own text, and items added, removed or reordered elsewhere never move it. Its cost is its length, an id on each item on the way, and quotes inside a flow mapping.

**Why the content file's keys, not the parts that draw them.** Content knows its keys, not the parts: a list's part may take another name than its field, a field may be passed on under another name, and a component placed below keeps its parts private unless it exposes them. Through parts, every library whose items content may tie to would expose the part that repeats over each of its lists, and content would write names its author never sees. A component's own data knows its parts, so a connector it draws names its ends through exposed parts (DEC-005 point 3).

**What a pattern's reading of an item takes from what the engine keeps private.** The record of the engine keeps a component's inside, its parts, its own, so its library may change it freely (DEC-005 point 3 and Rationale). An item content wrote is the content's, not a part, so reading it takes nothing the engine keeps private. The coupling it makes, where a component draws an item and how often, the lock takes up: a moved end shows when the lock moves, and a lost end holds a draft back.

**Why an end is found once, and why versions that lose one do not fit.** A tie that guessed among the places its item is drawn would point at a place no one chose, since which part draws first is a component's private order. Format 1 refuses the like for an option that names an item of a list two declared parts repeat over. An end counts what is drawn, since it is read in a piece, and a size may hide a part as an option does, so it is judged at each key (refinement per [visual-communication:DEC-021-size-and-shape]). Whether an item is drawn once depends on every component on the way, often of several libraries released apart, so failing a draft at its next render would fail a piece the project did not change, as the record of a list's fields finds for a key both libraries claim (DEC-010, Alternatives). The loss may come from a combination, so the render blames no one library. The cost: a library whose new version draws a list a second time, such as in a legend, holds back every draft that ties into that list for as long as its newer versions keep the second drawing, since a key path names no part to choose between the two.

**Why a tie whose end is not found is left out.** A line to a guessed place would say something false. Format 1 leaves out an item it cannot draw, such as one that repeats an id, and draws the rest of its list, and the finding fails where the project can correct it, in its content or its lock.

**Why a brand's drawing that loses an end does not fit.** No piece fails for what its brand lacks, since the top's own drawing draws whatever a brand's drawing cannot take (DEC-009 point 6). Counted as no fit, the instance goes to the top's own drawing, and the brand's other instances keep its form. Content declares nothing for a drawing, so switching the brand changes no content (DEC-009 point 5). A loss in the top's own drawing is the top's, which draws for every brand without a drawing of the layout, and point 4 compares versions, not brands.

**Why two separate items, on one page, below the pattern.** The connector joins two named elements, straight, with corners or curved, and never routes around anything (DEC-005 point 2). A tie from an item to itself would have to loop, and one to an item inside it would cross its own end's frame. A tie's own frame is a line's, with no side another connector could meet. A line is a leaf of the scene's tree, and no page lies inside another, so a line lies on one page at most (DEC-005 point 5). References read downward, so a component's drawing never depends on what lies beside it (DEC-005 point 3).

**Why one item for each end.** One tie to several items would draw several lines that share one trace, one state and one concept. A state that marks one of them broken would mark them all, and an edit taken back from a renderer could not tell them apart (DEC-001 point 3).

**Why those changes break.** Content may hold items in a list that comes to declare end fields, and each then needs two ends. Swapping the end fields turns every arrow around, and a component that ceases to take ends leaves each tie it draws with none.

**Why format 1 holds.** Format 1's schemas refuse a key they do not know, so no component they accepted declares an end field, and every item they accepted carries only its component's fields and options and the reserved keys, which keep their meaning. Their shapes of a name and an id hold no `.`, `[` or `]`, so keeping those marks out of names and ids refuses nothing they accepted.

### Alternatives considered

- **The ends as options of the tie's component.** Rejected: that component repeats over no list, and a tie drawn by one without such options would have no ends.
- **An option of the pattern, given once.** Rejected: it gives one value for every tie of the list.
- **New reserved keys, such as `from` and `to`.** Rejected: they refuse a field of their name that format 1 accepts (DEC-002 point 4, DEC-003 point 3), and an end means something only on an item a pattern draws as a tie.
- **A bare id, found at any depth below the pattern, as the prototype did.** Rejected: an item added elsewhere with the same id could move a tie in silence.
- **A bare id that the check holds unique below the pattern.** Rejected: it widens an id's uniqueness from its list to every list below the pattern (DEC-002 point 4), so an item added there could fail a tie that did not change.
- **The id alone where the end lies in a list of the pattern, and the key path elsewhere.** Rejected: one end would take two forms, and the id would hold only while no other list below the pattern shared it.
- **An item named by its place, as `#<place>`.** Rejected: it holds only while its list stays as it was at the render (DEC-001 point 3).
- **A path joined by `/`.** Rejected: a finding names a place in a content file with `.` and `[<id>]` after `#`, and two grammars for one place would read apart.
- **An end field that names the lists its ends lie in, as an option names its list.** Rejected: it adds a declaration, makes taking a list off it a breaking change, and keeps ends out of a pattern's slots, where content says where an end lies.
- **A component that declares which of its lists a tie may reach into,** as it exposes its parts. Rejected: every library would declare each list before any tie needs it, and a list no one declared could never be tied to.
- **A component that promises to draw each list field's items once.** Rejected: it binds every component for a case few lists meet, and one library's release cannot judge how another draws with it.

## Implications

- **Trace ids stay as they are.** A tie's trace id comes from its list's part and its id or place, as any item's does (DEC-005 point 5), and the ends it is given name its end fields as their source.
- **One path for a place in a content file.** The scene's content sources and the findings' locations name the keys the content file writes, so an end, a source and a finding name one place alike (DEC-005 point 5).
- **The release's comparison** of a library's stable components with its previous version (DEC-003 point 7) reads a pattern's or a top's lists of ties, their end fields in order, and whether a component takes ends, under point 6.
- **Left to later changes:**
  - whether a component's option, given once, may name an item by its key path too, such as the step a panel lines up with (DEC-001 point 3)
  - a mark, the library's to give as an addition, by which a component says which of its parts draws an item for others where two of them repeat over one list, letting a tie end there and lifting format 1's refusal of an option that names such an item
  - an end in content a piece shares with other pieces, such as a model several views read (DEC-001 point 3), which a key path, starting in the content file, does not reach
  - whether an end may be a component that content places in a field, rather than an item of a list
  - a list whose items each point at one item, such as notes that point at what they explain
- **Six accepted records take an edit once this one is accepted,** each citing this record, and a person accepts each edit (the decisions README, "Refining an accepted record"):
  - DEC-010's summary and Decision: an arrangement field takes a word, and a list of ties also carries two end fields, each naming an item.
  - DEC-010 point 1: every item of a list of ties is a tie, one that names its own component included.
  - DEC-010 point 2: arrangement fields are those that take a word, and end fields, declared beside them, share its rules on where such a field lies, who reads it, its names, a key both claim and versions that clash, an end field in such a clash giving no end.
  - DEC-010 point 3: no arrangement field names an item, with a forward pointer to this record in place of [project-kit#2499](https://github.com/aleskalfas/project-kit/issues/2499).
  - DEC-010 point 8, "How content is read": the check also reads an item's keys against its list's end fields.
  - DEC-010 point 9: the content finding names a key on an item that is no end field of its list either.
  - DEC-010's Implications on ties cite this record in place of the issue.
  - DEC-002 point 3: the strict reading also takes the end fields an item's list declares.
  - DEC-002 point 4: an end names its item by its key path, in every end. `#`, `.` with `[<id>]`, and `/` each keep one job, so no name or id holds `.`, `[` or `]`, and a later reading names a place in a content file in that grammar.
  - DEC-003 point 8: versions under which an end that a piece's lock finds would not be found, its item drawn other than once or off the tie's page, do not fit together for that piece.
  - DEC-005 point 1: a tie's component also reads the ends its parent gives it.
  - DEC-005 point 3: content names a connector's ends by key path, read wherever a component below draws the item, through no exposed part. A connector that a component's own data draws names its ends through exposed parts.
  - DEC-005's Rationale on exposure: an item content wrote is the content's, not a part of the component that draws it, and the patterns above see where and how often it is drawn. These three edits refine the record of the engine in place, and supersede none of it.
  - DEC-006 point 2: a connector ends at a picture's point by a tie's end field too, which names the item by its key path and the point.
  - DEC-009 point 6: a brand's drawing fits an instance only where it takes the end fields of the instance's ties, and each of their ends is found under it.
  - DEC-009 point 9: the end fields a top declares for a list in a layout count among the top's fields, for the findings on a drawing.
