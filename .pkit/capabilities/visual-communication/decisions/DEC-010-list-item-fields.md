---
id: DEC-010
title: Content names a list's component, and each item's arrangement, in fields its pattern declares
status: accepted
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> **Partially superseded by [visual-communication:DEC-032-ordered-colour-steps].** Overturned: the rejected alternative "Roles named by a place", so far as its example refuses a ramp from a first level's role to the last's. The rest stands, and that alternative stays as it stood.

**In plain terms:** a pattern, such as a row of cards, may declare for a list it repeats a field in which content may name one component for every item, and declares the fields an item may carry for how the pattern arranges it. Those that take a word, its arrangement fields, take one the pattern declares, never a number. A weight is such a field, and the pattern turns its word into a share of the row. A list of ties also carries two end fields, each naming an item (refinement per [visual-communication:DEC-011-tie-ends]). Where an item's component and its list both claim a key, neither reads it. Each page of a top whose layouts are its pages' forms, such as a deck's, names its layout with the key `layout`, or names its own component, and never names a layout by the component that draws it. A colour by place keys on where an item stands in its list, never on a word it carries. Every file format 1 accepted reads and draws as before.

## Context

[project-kit#2498](https://github.com/aleskalfas/project-kit/issues/2498) asks how content names a whole list's item component, and which fields a pattern declares for its items. The founding record promises content another component for a whole list than its pattern's default, and lets a pattern declare fields for its items' arrangement, while content holds no literal size ([visual-communication:DEC-001-visual-communication-discipline] points 3 and 6). The record of layouts leaves to this one how a page names its layout among a top's several ([visual-communication:DEC-009-layout-defaults] point 5, and Implications). The capability's prototype of a talk's slides ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)) and its next slice ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501)) need each of them, and a pattern that colours its items by their place.

## Decision

**A pattern may declare, for a list it repeats, a field in which content may name the list's component, and declares the fields its items may carry for its arrangement: arrangement fields, each taking a word it declares, and in a list of ties two end fields, each naming an item (refinement per [visual-communication:DEC-011-tie-ends]).**

### 1. Content names a list's component in a field its pattern declares

- **A field of the pattern's own.** A pattern lets content name one component for every item of a list by declaring a field for it, the list's *component field*, one for each list it lets content choose for. The pattern names the list's default component as well (DEC-001 point 6).
- **Spelled as content places a component.** Content gives the field a mapping that names a component by `use`, read with its library and never with a version ([visual-communication:DEC-002-files-and-validation] point 4). It may give words for that component's options, and `concept`, `state` and `override`, which mean there what they mean wherever content places a component, and the methodology's container keeps its key free there too.
- **It places nothing.** No component is drawn where the field lies, and no part of the pattern places it or passes it on. So the check reads the field as this point says, never as content placing a component: it asks none of the component's required fields of the field, and asks them of each item that takes it.
- **No id and no field.** The field gives no id and no field of its component.
- **Given to each item that names no component.** Such an item is drawn by the component the field names, and takes each key the field gives that it does not give itself. A key it gives replaces the field's whole, so an item that gives its own `override` takes none of the field's.
- **An item that names its own component takes nothing from the field,** its concept included, so it may be another kind of thing than its list's. In a list of ties every item is a tie, so an item that names its own component there is a tie too (refinement per [visual-communication:DEC-011-tie-ends]).
- **The item's choice first, then the list's, then the pattern's.** What draws an item is the component the item names, else the one its list's component field names, else the pattern's default.
- **A `use` like any other.** The piece locks the component's library (DEC-001 point 7), and content may not name there a component that a brand declares as a drawing, as it may name one nowhere (DEC-009 point 5). Every value an item takes from the field traces back to the field (DEC-001 point 3).
- **Where a pattern declares none,** content names a component item by item. This narrows the founding record's permission to name another component for a whole list (DEC-001 point 6) to the lists whose pattern declares a component field (Implications).

### 2. A pattern declares, for each list, the fields its items carry for its arrangement

- **Arrangement fields, and end fields** (refinement per [visual-communication:DEC-011-tie-ends]). For a list it repeats, a pattern declares the fields an item of that list may carry for the pattern's arrangement (DEC-001 point 6), and those that take a word are its *arrangement fields* (point 3). For a list of ties, each of which it draws as a connector between two other items, it also declares two *end fields*, each naming an item.
- **On the item, from a declaration of their own.** Both lie on the item, beside the fields and options of whichever component draws it, so an item's keys come from two declarations: its component's and its list's pattern's. The pattern declares them for each list, apart from its own fields and options and outside the list field's `items` schema, and the bullets below hold of both.
- **The pattern reads them, and the item component never does.** The pattern reads an arrangement field where it sizes or sets the item, such as the share of a row it takes (point 4). Nothing draws one as text.
- **Names.** Each takes the shape of a name, and no reserved key's name, as every field does (DEC-002 point 4).
- **A key both claim is read by neither.** Where two libraries released apart each declare keys of one mapping, neither reads a key that both declare. On an item, that is a field or an option of its component named as an arrangement field or an end field of its list: the component's field stays unfilled, the arrangement field takes its default, and an end field gives no end (refinement per [visual-communication:DEC-011-tie-ends]).
- **Versions that clash so do not fit together.** Versions under which an item of the piece carries a key that both its component and its list declare do not fit, for that piece, so a draft's render, which moves its lock only to versions that fit ([visual-communication:DEC-003-change-over-time] point 8), holds one of the two libraries back and states it (point 9). Only a clash the item does not show under the piece's lock counts, as only an end its lock finds does (DEC-011 point 4).
- **What holds nothing back.** A clash that content writes, or that a library the lock does not name yet brings, holds nothing back. Where a person moves a piece's lock to such versions, or content gives such a key, the item is a finding (point 9).

### 3. An arrangement field takes a word the pattern declares

- **An option given on each item.** An arrangement field takes one word from a list the pattern declares, as an option of words takes one (DEC-001 point 6). The first word is the default, which an item that leaves the field out takes, so no arrangement field is required, and adding one asks nothing of content.
- **Never a number, a size, a raw value or text.** What a word stands for, such as a share, lies in the pattern's data, where its formulas lie and a number with no unit may stand ([visual-communication:DEC-005-engine-and-plugins] point 1).
- **A size or a position in space, never a look.** A word sets how the pattern sizes its item and where it sets it, such as its share of a row or its side of a line. It never sets a colour, a role or a state. What an item is, its concept and its state say, and how it looks inside, its component draws (DEC-001 point 6, and point 6 below).
- **The pattern chooses by it as by an option** (refinement per [visual-communication:DEC-021-size-and-shape]). The pattern gives each word its effect, read for each item, as it gives an option's word its effect, so the choice is declared, never computed. A component chooses by an option, by whether a field is filled and by the size a piece is drawn at, and the content's order, the declared options and the size decide how items are arranged (DEC-005 points 1 and 2). This record widens the first, an option, to one given on each item, and changes nothing else in how a component chooses.
- **It never chooses, filters or sorts.** The items keep the content's order, and none is left out for what it holds (DEC-005 point 2).
- **No word names an item** (refinement per [visual-communication:DEC-011-tie-ends]). An option may name an item by its id (DEC-001 point 6), and an arrangement field names none: a list of ties names its ends in end fields (point 2).

### 4. A weight is an arrangement field, whose word the pattern turns into a share

- **Where it lies.** A weight is one of the arrangement fields a pattern declares for a list.
- **A share for each word.** The pattern gives each word of a weight a *share*, a number with no unit, in its data. The part that repeats over the list shares its length, which comes from the size the part gets and so from a brand's sizes, among the items in proportion to their shares, less the gaps between them.
- **Equal sizes are its plainest case,** where every item takes the same share. So a weight widens how the layout operator that gives equal sizes shares a length, and adds no operator (DEC-005 point 2).
- **An option where the shares are the pattern's.** A pattern whose shares follow from its arrangement alone gives them by an option of its own (DEC-001 point 6).

### 5. A page names its layout with the key `layout`

- **Where it applies.** In a top whose layouts are the forms its pages take, such as a deck's cover and slide, each page is drawn in a layout (DEC-009 point 1).
- **The field that holds the pages.** Such a top marks one of its fields, a list that lies in no layout, as holding its pages, each item a page. So in such a top a field the top marks declares its pages, where a top with one layout declares them by a slot (DEC-005 point 5).
- **A layout's slots are a page's fields.** Each layout's slots, which the top declares for that layout, are what a page in that layout fills, and no fields of the top. A drawing of the layout takes them, with the top's other fields, its options and its states (DEC-009 point 5).
- **The key `layout`.** Each page of such a top names its layout by the key `layout`, whose value is the name of one of the top's layouts. The format fixes the key, which binds only a page drawn in a layout, a mapping that places no component, so it refuses no field format 1 accepts, and such a top declares no slot named `layout` for its pages.
- **Every page names one.** A page names its layout, or the component that draws it, and no page takes a layout by default.
- **Never by its drawing.** A page whose form a brand may draw names its layout, never the component that draws that layout (DEC-009 point 5).
- **A page's content is its layout's.** A page carries `layout`, the reserved keys and the slots its layout declares, and nothing else (DEC-009, Implications), and the methodology's container keeps its key free there too. The check judges each page against the layout it names, and the layout, which chooses the drawing, is no content a drawing takes and counts for no drawing's fit (DEC-009 point 6).
- **Drawn by its layout's drawing.** That is the brand's, where the piece's brand draws the layout and its drawing fits the page, else the top's own (DEC-009 points 1, 2 and 6). A page in a layout has no item component.
- **A page that names its own component** by `use` is drawn by that component under every brand (DEC-009 point 2). Its keys are that component's, so it takes no layout: a `layout` key on it is that component's field, where the component declares one, and otherwise a key the check refuses.
- **No component field or arrangement field for pages.** The list of such a top's pages has neither, since a page's content is its layout's or its component's.
- **A top with one layout for the whole top:** its parts are that layout's drawing, and they place each page as an item, drawn by its item component (DEC-009 point 1). Its pages name no layout.

### 6. A place's colour keys on the item's position, never on what it carries

- **An item's place** is its position in the order of the items its list draws. A weight sets the item's share, never its place (point 3).
- **A family for each place.** A pattern may give each place of a list a colour family of its own, in its data, and may switch those families on an option (DEC-001 point 6). One family for every item of a list is the case where every place takes the same.
- **An order's steps, spread from two ends.** Under a word of an option, a pattern may give a list's places the steps of an order instead. The engine spreads the brand's two ends evenly over the places the list draws, and that is the one colour computed from a place, while no role's name is computed from one (refinement per [visual-communication:DEC-032-ordered-colour-steps] points 3 and 4).
- **A place past those the pattern names** takes no family from the pattern, and the order goes on to its item component's. The pattern's families do not start again from the first.
- **Never on an arrangement field** (point 3). An item says what it is by naming a concept, which a notation maps to a family ([visual-communication:DEC-004-brands-and-notations] point 10). A condition of the item, such as marked, is a state its component declares, which may change the family (DEC-001 point 6).
- **Items that belong together** name one concept, or are the items of an inner list that one item of an outer list holds. That outer item takes its family by its own concept or place, and passes it to what sits in it, where nothing nearer gives one (DEC-001 point 6).
- **The order stands.** An item's family is its concept's, else its place's, else its item component's, else that of the component it sits in, and a state may change it (DEC-001 point 6).

### 7. What breaks

A component field, an arrangement field and each of its words, the field that holds a top's pages, and a layout a page names are names a piece uses. So the record of change over time already counts removing or renaming any of them, or changing what it means, as a breaking change of its library (DEC-003 point 6). Beyond it:

- **Breaking, for a pattern:** marking a field it holds as a list's component field, since what content gave that field changes its meaning.
- **Breaking, for a top:** making its layouts its pages' forms, or ceasing to, since every page's content changes with it (point 5).
- **Not breaking:** a new component field, a new arrangement field, a new word or a new layout. Nor is a change of a word's share, of an arrangement field's default, of the family a place takes or of whether it takes a step (refinement per [visual-communication:DEC-032-ordered-colour-steps] point 8), which changes how pieces look. None changes what an item already says (DEC-003 point 6), and a piece meets each only when its lock moves (DEC-003 point 8).
- **A clash two releases make.** A new arrangement field, or a new field or option of an item component, may take a name the other already declares for the same item. Neither library can see it when it releases, so neither release breaks (point 2).

### 8. What this adds to format 1, and what still holds

- **Each addition is optional for a library:** a component field, arrangement fields and their words, a weight's shares, a family for each place, and a top whose layouts are its pages' forms. The schema of a content file names no key of an item or a page, so it gains none.
- **How content is read.** The check reads an item's keys against its component's fields and options, the reserved keys, and the arrangement fields and end fields of its list (refinement per [visual-communication:DEC-011-tie-ends]), and a page in a layout against that layout. A repeated list's `items` schema stays unread, as in format 1.
- **Format 1's files.** Every file format 1 accepted is read and drawn as before, and none of point 9's findings arises from one.

### 9. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct (DEC-002 point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it.

- **Where each lies.** A finding on what a component declares lies in that component's version. A clash with a pattern's default component is judged when the pattern's library is checked alone, against the newest version the project holds of each major it names, as a brand is checked ([visual-communication:DEC-008-library-role-defaults] point 1). A finding on what content gives lies in the content file, at the item, the page or the field. A clash that only the versions a piece locks show lies at the piece's lock, which combines them.
- **Fails validation:**
  - in a pattern: a component field or an arrangement field declared for a list the pattern does not repeat, a component field that is no field of the pattern, or one that a part of the pattern places or passes on
  - in a pattern: an arrangement field with no word or with one word twice, or a word whose effect sets a colour, a role or a state
  - in a pattern: an arrangement field that the list's default component also declares as a field or an option, since the pattern chose both
  - in a top whose layouts are its pages' forms: no field marked as holding its pages, or two; a slot named `layout`; or a component field or an arrangement field for its list of pages
  - in content: a word an arrangement field does not take, or a key on an item that is no field or option of its component, no arrangement field or end field of its list and no reserved key (refinement per [visual-communication:DEC-011-tie-ends])
  - in content: a component field that names no component, or gives an id or a field of its component
  - in content: a page that names neither a layout nor a component, a layout its top does not declare, or a key that is no slot of its layout and no reserved key
  - at a piece's lock: an item that carries a key that both its component and its list declare (point 2)
- **Stated as a fact:**
  - at a piece: a library that its draft's render held back for such a clash, with the item and the key
  - at a piece's lock: a key that both an item's component and its list declare, where no item carries it, so its author learns of the clash before writing one

## Rationale

**Why a field the pattern declares, and not a reserved key.** A field the pattern declares refuses nothing, since the pattern names it as it names its other fields, and it gives each of a pattern's lists a name of its own.

**Why the founding record's promise narrows.** A key the format gave every list, with no pattern declaring it, would need a name derived from the list's, which no spelling gives cleanly (Alternatives considered). Where a pattern declares none, content loses nothing format 1 gave it, and the promise holds wherever the starter is used.

**Why the field is spelled as content places a component, yet places nothing.** Content's author writes one shape wherever content names a component. The field differs from a slot's content only in that nothing is drawn where it lies, since it gives each item its component. The pattern's README names the field, and its name says what it holds.

**Why it gives no id and no field.** An id names one placed thing, and the field gives one component to many items. Were the field to give a field, an edit of one item taken back from a renderer would change every item, since every drawn part traces back to the field it shows (DEC-001 point 3). An option's word, a concept, a state and an override show no words, so each serves every item at once.

**Why arrangement fields lie apart from the list's `items` schema.** Format 1 never reads that schema for a repeated list, so a component format 1 accepted may hold one there that requires a field no item gives. A declaration of its own appears in no file format 1 accepted, and keeps what the pattern reads apart from what an item's component takes.

**Why neither reads a key both claim.** An item's keys come from two libraries released apart, and each owner can add a name in a release that breaks nothing on its own side (point 7). Read by neither, the key changes no meaning whichever library added it, and the check names it. The pattern chose its own default component, so a clash with it is the pattern's to mend.

**Why a draft does not move into a clash.** A library's addition fails no piece elsewhere: a library's own roles take defaults below every brand (DEC-008 point 1), and a top's own drawing draws what a brand's cannot (DEC-009 point 6). Holding a library back keeps it so here, and the render, which moves a draft's lock to the newest versions (DEC-003 point 8), already reads which libraries the content uses, so it reads which keys its items carry with no new source. A clash under the piece's lock comes from a person's move of the lock or from the content, both mended in the piece's own files, so holding a library back there would only stop the lock moving until they are.

**Why a word, never a number.** Content chooses only among what its libraries declare, and holds no literal size (DEC-001 point 3). A word from a declared list is checked by the schema and drawn once for each word, where no set of renders could show every number (DEC-001, Rationale). What an item shows is its component's, so an arrangement field holds no text either.

**Why an arrangement field is an option given on each item.** The pattern switches on its word as on an option's, so it adds no way for a component to choose beside the record of the engine's three: an option, a filled field and the size a piece is drawn at (refinement per [visual-communication:DEC-021-size-and-shape]). It is given on each item, since the choice is the item's own. A word that set a look would give content a second way to say what an item is, beside its concept and its state.

**Why a weight is an arrangement field.** An item's share of its row is the item's own, so it lies on the item, where the founding record lets a pattern declare fields for its arrangement (DEC-001 point 6).

**Why such a top marks the field that holds its pages.** Outside every layout, the list of pages puts no page inside a page, which the record of the engine counts an error (DEC-005 point 5), and a layout's slots are what a page fills, which is what the record of layouts has a drawing take (DEC-009 point 5, and Implications).

**Why a page names its layout with one key the format fixes.** A component content names draws under every brand, so naming a drawing would fix the page's form whatever the brand, where a named layout lets a switch of brand change how the page looks and leave its content as it is (DEC-001 point 5, DEC-009 point 5). One key lets the pages of every such top read alike, for people, agents and translators.

**Why every page names its layout.** Named on every page, a layout changes only when the content changes it.

**Why colour keys on place, never on a word an item carries.** Colour says what a thing is (DEC-001 point 6), and a notation's concept says it with guarantees that a pattern's own words lack: one meaning in every piece and under every brand, and an icon or a shape that keeps colour from being its only sign (DEC-004 point 10). A place says nothing of what an item is, and only the pattern colours by it.

**Why format 1's files are untouched.** Format 1's schemas refuse a key they do not know, so nothing they accepted declares any of the additions. Every item they accepted carries only its component's fields and options and the reserved keys, which keep their meaning.

### Alternatives considered

- **A new reserved key beside a list, which names its component.** Rejected: it refuses a field of its name that format 1 accepts, where the format grows only by additions until validation accepts older files (DEC-002 point 4, DEC-003 point 3).
- **A key for each list, joined from the list's name and `use` by a mark.** Rejected: it puts a path mark into a key, which DEC-002 point 4 keeps out of every name so that a later reading can name a part of a file by the keys that lead to it.
- **Keys spelled outside the shape of a name, such as with `_`, for a list's component and for arrangement fields.** Rejected: they refuse nothing and never clash, but read as marks of the format rather than words of the pattern, and fix how every pattern spells its own names, to remove a clash that point 2 keeps from changing any meaning.
- **A list written as a mapping that holds its component and its items.** Rejected: a list field would take two shapes, and every path to an item would change.
- **A component field that also gives each item a field.** Rejected: one field would show in every item.
- **Arrangement fields in the list field's `items` schema.** Rejected: it would refuse items format 1 accepted, where such a schema requires a field.
- **Arrangement fields under one key of each item.** Rejected: spelled as a name, that key is a new reserved key, and spelled outside the shape of a name, it is the alternative above.
- **The component's names first, or the arrangement field's first, where both claim a key.** Rejected: each lets one library's addition change what the other's items say, with no one told, such as a weight's word becoming text the card shows.
- **A clash that fails a draft at its next render.** Rejected: a release that breaks nothing on its own side would fail a piece the project did not change, which no other addition does.
- **Arrangement fields that hold numbers or text, such as a weight as a number with no unit.** Rejected: a number would be a size in all but name.
- **A layout field each top names for itself.** Rejected: each top would have to keep its pages' slots off that name.
- **A page that takes its top's first layout by default.** Rejected: a layout added before the first would move every page that named none into a layout with other slots, after a change counted as an addition (DEC-003 point 6).
- **A page that names its layout as the component that draws it,** such as a brand's drawing read with the brand's name. Rejected: content never names a brand's drawing (DEC-009 points 2 and 5).
- **The list of pages as a slot of every layout.** Rejected: each page would hold the list of pages again.
- **Shares only by an option of the pattern.** Rejected: an option serves a fixed shape, not a list of any length.
- **A family keyed on an arrangement field, such as a group the item names.** Rejected: it would be a concept that one pattern defines.
- **Families that start again past the last place a pattern names.** Rejected: two places would take one family with nothing to say they are alike.
- **Roles named by a place, such as a ramp from a first level's role to the last's.** Rejected. A role's name would be computed from the place, where every role a component reads is written in its file. A family for each place is written in the pattern.

## Implications

- **The capability's pages** hold the spelling of each addition, written there by the change that builds it.
- **The starter's patterns** each declare a component field for each list they repeat, and its README names each pattern's arrangement fields with their words, as it names its options; the arrangement fields count toward the guide of about four options a pattern holds ([visual-communication:DEC-007-starter-library] point 2).
- **The record of ties** ([visual-communication:DEC-011-tie-ends]) builds on how content gives a list, naming a tie's ends in the end fields of points 2 and 3.
- **Translation.** A page's layout, an item's component, and an arrangement field's or option's word are written in each language's content. Whether the check holds each equal in every language, and how it matches an item or a page of one language to another's, is left to translation (DEC-001 point 3, and Implications).
- **The release's comparison** of a library's stable components with its previous version (DEC-003 point 7) reads component fields, arrangement fields and their words, the field that holds a top's pages, and whether a top's layouts are its pages' forms, under point 7.
- **Trace ids.** An item's trace id comes from its list's part and the item's id or place, whatever component draws it (DEC-005 point 5).
- **Edits to five accepted records,** each citing this record:
  - DEC-001 point 6: content names another component for a whole list where its pattern declares a field for it.
  - DEC-002 point 3: the strict reading also takes the keys an item's list's pattern declares for it, and the slots a page's layout declares. Its point 4: the reserved keys and the methodology's container's key bind a component field's mapping and a page in a layout too, and the format fixes `layout` on a page in a layout alone.
  - DEC-003 point 8: versions under which an item of a piece carries a key that both its component and its list declare do not fit together for that piece, where it carries none under the piece's lock.
  - DEC-005 points 1 and 2: an option by which a component chooses may be one a pattern declares for each item. Its point 5: in a top whose layouts are its pages' forms, the field the top marks declares its pages.
  - DEC-009 point 5 and its Implications cite this record, in place of [project-kit#2498](https://github.com/aleskalfas/project-kit/issues/2498), for how a page names its layout, and say that a page in a layout has no item component, the list of pages has no component field, and a page that names its own component is drawn by it. They leave to the change that gives a top several layouts how the top draws each page by its layout's drawing.
