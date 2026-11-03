---
id: DEC-011
title: A tie names its two ends in fields its pattern declares, each by the keys and ids that lead to its item
status: proposed
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a *tie*, such as an arrow from one card to another, is an item of a list that a pattern draws between two other items, its ends. The pattern declares two fields on its list of ties, one for where a tie starts and one for where it ends. Content fills each as it fills an option that names an item. It gives the keys and ids that lead to the item, such as `left[living-docs]` for an item of a sibling list, or `right[groups].groups[project-management].items[doc-check]` for one inside a nested component. The path holds only what the content file holds, so it reaches an item that a nested component draws without that component exposing anything. A tie whose end is not found is left out, and the check names it. A draft does not move to library versions that would lose one of its ends. Every file format 1 accepted reads and draws as before.

## Context

The founding record lets a part of a piece name an item, which then carries an id, such as the step a panel lines up with. A component's option may name an item by its id. A state covers a broken tie ([visual-communication:DEC-001-visual-communication-discipline] points 3 and 6, and Rationale). An id is unique in its list, so whatever names an item names its list too, unless the list is one its own component declares ([visual-communication:DEC-002-files-and-validation] point 4).

The record of the engine gives it a tool that joins named elements, straight, with corners or curved, its *connector*. A formula reads its own component and what lies below it: its own parts, and the parts a component it places exposes. Every component between keeps the rest private, so its library may change it freely. A reference names a part, then each exposed part below it, and a step into a list names the list, then the item by its id. A connector names its ends the same way ([visual-communication:DEC-005-engine-and-plugins] points 2 and 3).

The record of a list's fields has a pattern declare, for each list it repeats, the *arrangement fields* its items carry. The pattern reads them, and the item's component never does. An arrangement field takes a word the pattern declares, its first word the default, and none names an item. That record leaves to this one whether an arrangement field may name an item ([visual-communication:DEC-010-list-item-fields] points 2 and 3).

Format 1 builds part of that:
- **An option that names an item** names one of a list over which exactly one part of its own component repeats. Content gives it as `{item: <id>}`, or as `{item: <id>, point: <name>}` for a point its picture exposes.
- **A formula** reads an item of a list through exposed parts, a step into a list written `<list>[<id>]`.
- **A place in a content file.** The check names one in a finding's location after `#`, by its keys joined by `.`, an item of a list as `[<id>]`, or by its place where it has no id.
- **A component placed by a part** may take its fields from the placing component's, under other names.
- **No connector** is built yet.

The capability's design work drew a slide in which capabilities fill each other's slots ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)). Two cards stood in a left column. A pattern of groups stood in the right one, as the column's one item, and its group held three items. Each card was tied to two of the group's items. The prototype named each end by a bare id, which it searched for at any depth below the pattern.

The capability's next slice builds connectors between items of different lists, and draws that slide ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501)). Until validation accepts files at an older format number, the format grows only by additions that every file written before still meets ([visual-communication:DEC-003-change-over-time] point 3). A new reserved key would refuse a field of its name that format 1 accepts (DEC-002 point 4).

## Decision

**A pattern declares two end fields for a list of ties, beside its arrangement fields: the first where a tie starts, the second where it ends. Each takes the shape of format 1's option that names an item. Content names the item by its key path: the content file's keys that lead to it, and in each list the item's id. The path names only what content holds, so it reaches the item wherever a component below the pattern draws it, with nothing exposed. A tie whose end is not found is left out and reported, and a draft does not move to versions that lose an end.**

### 1. A tie is an item whose two ends are fields its pattern declares

- **A tie** is an item that a pattern draws as a connector between two other items, its *ends*, such as an arrow from a card to a step (DEC-005 point 2). The list that holds it is a *list of ties*. A part of the pattern repeats over it, and draws each tie with the connector tool.
- **The pattern still decides the arrows.** The founding record has a pattern decide the arrows between its items (DEC-001 point 6). The pattern declares its list of ties and draws them, and content says which items each joins, as content says what any list holds.
- **Two end fields.** For a list of ties, the pattern declares two *end fields*, such as `from` and `to`, beside the arrangement fields it declares for the list (DEC-010 point 2). The first is where each tie starts, and the second where it ends. So one tie component serves every pattern, and its arrowheads know which way they point.
- **Read as arrangement fields are.** An end field lies on the item, the pattern reads it, and the item's component never does. A key that both the tie's component and its list declare is read by neither (DEC-010 point 2), so the tie then lacks that end, and is left out (point 4).
- **A kind of its own.** An arrangement field takes a word the pattern declares, has a default, and names no item (DEC-010 point 3). An end field names an item, has no default, and every tie gives it. So the two stay apart, and each keeps rules that hold of all its fields.
- **Its own colour.** A tie takes its colour family from its own concept, else its place, else its component, as every item does (DEC-010 point 6), and from neither end.
- **Given its ends.** The tie's component, the list's default or one content names (DEC-010 point 1), reads no end field. The pattern gives it its two ends: the elements drawn for the items, or the points the ends name, with their frames, in the frame of the component that reads them (DEC-005 point 3). Where a tie meets an end, and how the ties that meet one side spread, is the connector tool's (DEC-005 point 2).

### 2. An end field names an item, in the shape of an option's value

- **What content gives.** An end field takes the shape of the value of format 1's option that names an item: `{item: <key path>}`. Its `item` holds a key path (point 3), where an option's holds an id alone. An id holds no `.` and no `[`, so the two never read alike.
- **A point.** An end may also name a point its item exposes, as `{item: <key path>, point: <name>}`. So a tie ends at a picture's point as the record of work outside the engine has a connector do, by naming the item and the point ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 2).
- **Required.** An end has no default, as an option that names an item has none. A tie that gives no end is a finding (point 7).
- **What this answers.** The record of a list's fields leaves open whether an arrangement field may name an item (DEC-010 point 3). None does: a pattern names an item in an end field. A part of a piece that names an item is what the founding record gives an id for (DEC-001 point 3).

### 3. Content names an end by its key path

- **The key path.** It starts in the content mapping that holds the tie's list, at a field of that mapping. It names each field that leads to the item, joined by `.`, and in each list the item by its id, as `[<id>]`. It ends at an item. `left[living-docs]` names an item of the list `left`. `right[groups].groups[project-management].items[doc-check]` names an item of a list inside a component that the list `right` holds.
- **The content file's own keys.** Where a component passes content on to the pattern under other names, the path keeps the names the content file writes. So the path holds only keys and ids its author writes, and names no part of any component.
- **The format's grammar for a place in a content file.** A finding's location uses it after `#`. An end's path differs in two ways: it starts at the mapping that holds the tie's list, not at the file's top, and it names each item by its id alone.
- **Ids only, never a place.** Each item on the path carries an id, since a part of the piece names it (DEC-001 point 3). An item found by its place is found only while its list stays as it was at the render (DEC-001 point 3), and a tie holds while items are added, removed or reordered.
- **In every end,** even one in the pattern's own list. An end field names no list, so the id alone would name none (DEC-002 point 4).
- **Below the pattern.** Both ends lie below the pattern that draws the tie, as everything a component reads does (DEC-005 point 3). A tie between items of two components placed apart is drawn by a pattern that holds both. A pattern that passes its list of ties on to a component it places has that component draw the ties, and their ends then lie below it.
- **Two separate items.** An end is never a tie, the two ends are never one item, and neither lies in or below the other. A connector runs between the sides of two frames that lie apart, and never routes around anything (DEC-005 point 2). So it cannot draw a tie that ends at a line, at its own start, or at an item inside its other end.
- **One item for each end.** A tie that joins one item to several is several ties, each with its own trace, state and concept.
- **The same in every language,** since each language's content holds the same fields and the same ids (DEC-001 point 3).

### 4. An end is its item where a component draws it

- **Found through what draws it.** The end is the element the engine draws for that item, wherever a component below the pattern draws it, under the content's options. That may be the pattern's own list, or a list that a component below it draws, at any depth. The pattern reads the element and its frame, as it reads an exposed part's frame (DEC-005 point 3).
- **Nothing exposed by the components between.** An end names no part, and reads only the element drawn for its item. Each component between keeps its parts' names private, and its library may rename or rearrange them without a breaking change (DEC-005 point 3). A point an end names is one its item's own component exposes, as format 1 asks of every point.
- **What becomes visible.** How a component draws the items content gives it, where each lies and whether it is drawn once, now reaches the pattern above it. A moved item moves a tie's end, which changes only how a piece looks. A lost end is held back from a draft, as the next bullets say.
- **Found once.** The end is not found where the pattern draws its item nowhere, such as in a list a component leaves undrawn, or more than once, such as in a list two parts repeat over. A tie whose end is not found is left out of the drawing, and the rest of its list is drawn. The check reports it (point 7).
- **On one page.** A tie and both its ends lie on one page, since a line is drawn on one page (DEC-005 point 5). A tie that does not is left out, and reported.
- **Versions that lose an end do not fit together.** A draft's render moves its lock only to versions that fit together (DEC-003 point 8). Versions do not fit, for a piece, where an end that its lock finds once would find its item drawn other than once. So the render holds back a library whose newer version loses the end, as for a key that an item's component and its list both declare (DEC-010 point 2). It states the library, the tie and the end. Where a person moves a lock to such versions, the tie is a finding.
- **Computed like any value.** The frames of the ends are computed in the order the references give, and a loop through them is refused (DEC-005 point 3).

### 5. What breaks

The record of change over time already counts removing or renaming an end field, or changing what it means, as a breaking change of its library ([visual-communication:DEC-003-change-over-time] point 6). Beyond it:

- **Breaking, for a pattern:** declaring end fields for a list it already repeats, since each item of that list then needs two ends. So is swapping which end field a tie starts at, which turns every arrow around.
- **Not breaking:** a new list of ties with its end fields. Nor is a change of where a component draws an item, which moves a tie's end with it and changes only how pieces look (DEC-003 point 6).
- **A loss two releases make.** A component's new version may draw a list's items twice, or not at all, in a piece whose tie ends there. It may lie in another library than the pattern's, and neither release can see the other's drawing, so neither breaks. A draft's render does not move into it, and a person who moves a lock into it meets it as a finding (point 4).

### 6. What this adds to format 1, and what still holds

- **Added, each optional:**
  - a pattern's list of ties, with its two end fields
  - the key path as an end's value, with a point where an end names one
  - a pattern's reading of the item an end names, wherever a component below it draws that item
  - a part that repeats over a list of ties and draws each with the connector tool, which comes with the change that builds connectors (DEC-005 point 2)
- **The schema of a content file keeps its keys.** It names no key of an item, so end fields add none there.
- **An option keeps its form.** A component's option that names an item still names one of a list it repeats over, by its id alone.
- **Arrangement fields keep theirs.** Each still takes a word, with a default, and none names an item.
- **What still holds.** Format 1's schemas refuse a key they do not know, so no component they accepted declares an end field. Every item format 1 accepted carries only its component's fields and options and the reserved keys, which keep their meaning. Every file format 1 accepted is read and drawn as before, and none of point 7's findings arises from one.

### 7. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, as the record of files and validation decides ([visual-communication:DEC-002-files-and-validation] point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it. A final piece's drawing is not judged, as that record decides.

- **Where each lies.**
  - A finding on what a pattern declares lies in the pattern's version.
  - A finding on an end that the content and the components' fields decide lies in the content file, at the tie's end field.
  - An end whose item the pattern draws other than once, or on another page, lies at the piece, since the components its lock names draw it.
  - A key that both the tie's component and its list declare is a finding of the record of a list's fields (DEC-010 point 9).
- **Fails validation:**
  - in a pattern: end fields for a list that no part of it repeats over as ties, or more or fewer than two for one list
  - in a pattern: an end field with the name of an arrangement field of its list, or one that the list's default component also declares, since the pattern chose both
  - in content: a tie that leaves an end field out, or fills it with another shape than point 2's
  - in content: a key path that names a key no component on the way declares as a field, steps into a list with no id or into a field that is no list with one, names an id its list lacks, or ends at no item
  - in content: an end that names a tie, two ends that name one item, or an end that lies in or below the other
  - in content: a point that the item's component does not expose
  - at a piece: an end whose item the pattern draws nowhere, or more than once, or a tie whose ends do not lie on its page
- **Stated as a fact:** at a piece, a library that its draft's render held back because an end would be lost, with the tie and the end.

## Rationale

**Why fields the pattern declares, and not options of the tie's component.** The ends lie below the pattern, which the tie's component neither holds nor reads. A reference reads only what lies below its own component (DEC-005 point 3), and an option names an item of a list its own component repeats over. Where the tie runs is the pattern's arrangement, which the pattern reads from fields it declares on the item (DEC-010 point 2). Kept on the list, the ends also stay with a tie that names its own component (DEC-010 point 1), whatever that component declares.

**Why end fields stand apart from arrangement fields.** Named as an arrangement field, an end would differ from every other on each rule that defines one. It takes no word, has no default, is required, and adding one to a list asks something of content. As a kind of its own, it shares with arrangement fields what the record of a list's fields says of every key a list declares on its items: where it lies, who reads it, and a key both libraries claim (DEC-010 point 2). Arrangement fields keep their rules whole, and still never name an item.

**Why not a new reserved key.** A reserved key such as `from` would refuse a field of that name, which format 1 accepts (DEC-002 point 4), and the format grows only by additions until validation accepts older files (DEC-003 point 3). A reserved key also means the same in every mapping, and an end means something only on an item a pattern draws as a tie. The pattern names its two ends as fits its subject.

**Why two end fields, in order.** A connector may carry an arrowhead at its start, at its end or at both, so a tie has a direction. The pattern names its ends freely, and the tie's component reads neither. Their order gives that component its start and its end, so one connector serves every pattern's ties.

**Why the tie's component is given elements, not only frames.** The ties that meet one side of an item spread along it (DEC-005 point 2), so whatever spreads them must know which item each tie meets. A medium with connectors of its own attaches a line to an object, so the scene keeps which element each end meets (DEC-005 point 5). Two frames of numbers would lose both.

**Why the shape of an option's value.** Content then writes one shape wherever it names an item, `{item: …}`, with a point beside it where it ends at one (DEC-006 point 2). An option's `item` holds an id, since its declaration names the list. An end field names no list, so its `item` holds the key path, and an id can never be read as one.

**Why the key path, in every end.** An id is unique only in its list, so whatever names an item names its list too (DEC-002 point 4). The prototype found each end by a bare id at any depth, which held only while no two items below the pattern shared one. An item added elsewhere with the same id would then move a tie, or break it, with nothing in the tie changed. The key path names each list on the way, so an end's meaning rests on its own text, and an item added elsewhere never moves it. One form serves every end, wherever it lies.

**Why not a bare id that the check holds unique below the pattern.** It would cost less to write, and need no quotes. But it would widen an id's uniqueness from its list to every list below the pattern, against the record of files and validation (DEC-002 point 4). And an item added in any list below the pattern, such as a step in one group, could fail a tie elsewhere on the slide, though nothing it ties changed.

**What the key path costs.** It is longer than a bare id, and each item on the way carries an id. Inside a flow mapping, where YAML reads `[` as the start of a list, it is quoted; in a block mapping it needs no quotes. The founding record measures what content costs for each page (DEC-001, Implications), and the slice that draws the slide measures it again ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501)).

**Why the content file's keys, not the parts that draw them.** The record of the engine has a connector name its ends as a reference: a part, then each exposed part below it (DEC-005 point 3). That form serves a component's own data, which knows its parts, and it stays theirs. Content knows its keys. A list's part may take another name than its field, a component may pass a field on under another name, and a component placed below keeps its parts private unless it exposes them. Through parts, every library whose items content may tie to would expose the part that repeats over each of its lists, and content would write names its author never sees.

**What a pattern's reading of an item takes from what the engine kept private.** The record of the engine keeps a component's inside its own, so its library may change it freely (DEC-005 point 3 and Rationale). An end reads no part, and names nothing a library declares, so no part's name becomes a promise, and a library still renames or rearranges its parts without a breaking release. What the end makes visible is how a component draws the items content gives it: where each lies, and whether each is drawn once. A change to either was unseen above the component, and now moves a tie's end or loses it. The lock takes up that coupling. A moved end changes how a piece looks, which a person sees when the lock moves, and a lost end holds a draft back. So the record of the engine keeps what it protects, a library's freedom to change its inside without a breaking release, and no longer keeps unseen how a component draws its content's items.

**Why an end is found once, and why versions that lose one do not fit.** A tie that guessed among the places its item is drawn would point at a place no one chose, since which part draws first is a component's private order. Format 1 asks the same of an option that names an item: exactly one part repeats over its list. Whether an item is drawn once depends on every component on the way, often of several libraries released apart. A library that comes to draw a list twice breaks nothing on its own side. As the record of a list's fields finds for a key both libraries claim, failing a draft at its next render would fail a piece the project did not change (DEC-010, Alternatives). So the draft holds back the library whose newer version loses the end, and names it, so its owner learns what lost the end.

**Why a tie whose end is not found is left out.** Format 1 leaves out an item it cannot draw, such as one that repeats an id, and draws the rest of its list. A line to a guessed place would say something false. The finding fails where the project can correct it, in its content or its lock.

**Why two separate items, on one page.** The engine's connectors run straight, with corners or curved, between named elements, and never route around anything (DEC-005 point 2). A tie from an item to itself, or to an item inside it, has no gap between two frames to cross. A tie's own frame is a line's, with no side another connector could meet. A line is drawn on one page, and no page lies inside another (DEC-005 point 5).

**Why one item for each end.** The prototype let one tie end at several items. One tie would then draw several lines that share one trace, one state and one concept. A state that marks one of them broken would mark them all, and an edit taken back from a renderer could not tell them apart (DEC-001 point 3).

**Why a tie joins only what lies below its pattern.** References read downward, so a component's drawing never depends on what lies beside it (DEC-005 point 3). Two items placed apart are joined by the arrangement that holds them both.

### Alternatives considered

- **The tie's component declares its ends as options.** Rejected. An option names an item of a list its own component repeats over, and a reference reads only below its component. The tie's component repeats over nothing, and a tie that named a component without such options would have no ends.
- **An option of the pattern, given once.** Rejected. It gives one value for every tie of the list.
- **An end field as an arrangement field that names an item.** Rejected. It would break each rule that holds of every other arrangement field: a word, a default, no field required, and none that asks anything of content when added.
- **New reserved keys, such as `from` and `to`.** Rejected. They refuse a field of their name that format 1 accepts (DEC-002 point 4, DEC-003 point 3).
- **A bare id, found at any depth below the pattern, as the prototype did.** Rejected. An id is unique only in its list, so an item added elsewhere could move a tie in silence.
- **A bare id that the check holds unique below the pattern.** Rejected, for the reasons above: it widens an id's uniqueness, and an item added below the pattern could fail a tie that did not change.
- **The id alone where the end lies in a list of the pattern, and the key path elsewhere.** Rejected. One end would take two forms, and the id alone would hold only while no other list below the pattern shared it.
- **An end field that names the lists its ends lie in, as an option names its list.** Rejected. It would add a declaration, make taking a list off it a breaking change, and keep ends out of a pattern's slots, for no gain: where an end lies is what content says.
- **A path through exposed parts, as a formula reads.** Rejected. Content would name parts its author never sees, and every library would expose each part that repeats over a list.
- **A component that declares which of its lists a tie may reach into,** as it exposes its parts. It keeps a promise for each list in sight, as exposure does for parts, and leaves the record of the engine's privacy as it is. Rejected. Every library would declare each list before any tie needs it, and a list no one declared could never be tied to, while a key path needs no promise.
- **A component that promises to draw each list field's items once.** Rejected. It binds every component for a case few lists meet, and one library's release cannot judge how another draws with it.
- **A component that marks which of its parts a tie meets, where two repeat over one list.** Rejected. Which drawing a tie means is the content's question, which a finding puts to its author. A library cannot choose for ties it cannot see.
- **The tie's component given only the frames of its ends.** Rejected. Spreading the ties that meet one side, and a medium's own connectors, need to know which element each end meets.
- **A path joined by `/`.** Rejected. A finding already names a place in a content file with `.` and `[<id>]`, after `#`, and two grammars for one place would read apart.
- **An item named by its place, as `#<place>`.** Rejected. It holds only while its list stays as it was.
- **An end that names several items.** Rejected. One tie would draw several lines with one trace, state and concept.
- **Ends that reach above or beside their pattern.** Rejected. A component's drawing would depend on what lies outside it.
- **The first part that draws an item, where several do.** Rejected. Which part is first is the component's private order.
- **A loss of an end that fails a draft at its next render.** Rejected. A release that breaks nothing on its own side would fail a piece the project did not change.

## Implications

- **The change that builds connectors** ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501), T8) builds the list of ties, its end fields, the key path and the part that repeats over the ties. It sets how a pattern declares its end fields, and how a tie's component takes its ends. It draws the arrowheads, and decides whether the engine or the part spreads the ends (DEC-005 point 2). The capability's pages describe each with that change, the quotes a key path takes in a flow mapping among them.
- **One path for a place in a content file.** The same change finds an item by its key path through each component that passes content on under other names. It makes the scene's content sources and the findings' locations name the keys the content file writes there too, so that an end, a source and a finding name one place alike (DEC-005 point 5).
- **One order for the lock search.** The same change has a draft's render hold back versions that lose an end. Whether versions lose one shows only on a whole combination, so the render judges each combination it reaches. It sets one order for the search under both rules of fit, this record's and the record of a list's fields' (DEC-010 point 2), and names the library it holds back.
- **The starter's network pattern** declares a list of ties with its two end fields, and its README names them, when the change that composes the starter's patterns builds it (#2501, T12).
- **Trace ids stay as they are.** A tie's trace id comes from its list's part and its id or place, as any item's does (DEC-005 point 5). The ends it is given name its end fields as their source.
- **The release's comparison** of a library's stable components with its previous version (DEC-003 point 7) reads a pattern's lists of ties and their end fields, in their order, under point 5.
- **Left to later changes:**
  - whether a component's option, given once, may name an item by its key path too, such as the step a panel lines up with (DEC-001 point 3). The change that needs it adds it.
  - whether an end may be a component that content places in a field, rather than an item of a list
  - a list whose items each point at one item, such as notes that point at what they explain
- **Five accepted records take an edit once this one is accepted,** each citing this record. A person accepts each edit (the decisions README, "Refining an accepted record"). Three of them are being edited for the record of a list's fields ([project-kit#2536](https://github.com/aleskalfas/project-kit/issues/2536)), and these edits follow that one.
  - The record of a list's fields' point 2: a pattern declares, for a list of ties, end fields beside its arrangement fields, and its rule for a key both claim holds of both. Its point 3: no arrangement field names an item, with a forward pointer to this record. Its Implications on ties cite this record, in place of [project-kit#2499](https://github.com/aleskalfas/project-kit/issues/2499).
  - The record of files and validation's point 3: the strict reading also takes the end fields an item's list declares. Its point 4: content names an item of another list by its key path. It also states each mark's job once: `#` opens a place in a file, `.` and `[<id>]` join its keys and ids, and `/` joins a library to its component and the steps of a trace id. So a name or an id holds no `.`, `[` or `]`, and a later reading names a place in a content file in the same grammar.
  - The record of change over time's point 8: versions under which an end of a piece's tie, found once under its lock, would find its item drawn other than once do not fit together for that piece.
  - The record of the engine's point 1: a tie's component also reads the ends its parent gives it. Its point 3: content names a connector's ends by key path, and a pattern reads the item an end names wherever a component below draws it, through no exposed part. A connector that a component's own data draws still names its ends through exposed parts. Its Rationale on exposure says what this record makes visible.
  - The record of work outside the engine's point 2: a connector ends at a picture's point by an end field too, which names the item and the point.
