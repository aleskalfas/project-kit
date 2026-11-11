---
id: DEC-034
title: A brand's drawing names its layout in its own file, and keeps the sizes and field names its top sets
status: accepted
date: 2026-11-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand draws its own form of a layout, such as the deck's cover, with a component whose file names the top and the layout it draws. The drawing takes only what content gives the top, keeps the sizes the top gives its pages, and names each part that shows a field after the field. So switching the brand changes neither what fits a page nor the trace id of what a field shows. A top printed at one size declares it in millimetres, and a base brand that begins to draw a top breaks no brand built on it. No drawing's look and no brand's values are decided here.

## Context

The record of layouts lets a brand hold its own drawing of a layout of a top whose library it names. The brand's drawing draws each instance it fits, in place of the top's own drawing, and along a chain of brands the brand nearest the root that serves a top keeps its form ([visual-communication:DEC-009-layout-defaults] points 2 to 6). That record adds no field. It leaves to the change that builds a brand's own form the declaration by which a brand says, for each layout it draws, the top, the layout and the component that draws it (point 8). Its Implications leave five more questions to that change:
- whether a drawing may give a page another physical size than its top declares
- how a top component that a brand holds relates to drawings, since a brand's version may hold components, a top among them
- whether what a slot places keeps its trace id under every drawing
- how a drawing written for a page alone draws where its top is placed inside another page
- the status a drawing carries, and whether the release's comparison reads a base that begins to serve a top

Three more records bear on it:
- **The record of sizes:** a brand's drawing at each size a piece is drawn at ([visual-communication:DEC-021-size-and-shape], Implications).
- **The record of the web page:** how a brand's drawing writes the height its page asks for ([visual-communication:DEC-022-web-site-and-parts] point 3 and Implications).
- **The record of the engine:** a top whose pages have a physical size declares it, and an export maps the scene's unit onto it, but no file carries one, so each renderer declares a mapping of its own as its unit ([visual-communication:DEC-005-engine-and-plugins] point 5).

## Decision

**A brand's drawing names its layout in its own file, and keeps the sizes and the field names its top sets.**

### 1. A drawing names in its own file the top and the layout it draws

- **The declaration.** A brand declares a drawing by holding a component whose file names, under the key `draws`, a top by `<library>/<component>` and one of its layouts: `draws: {top: <library>/<component>, layout: <layout>}`. Nothing else lists a brand's drawings.
- **Only a brand's component.** A component of a component library, or a piece's own, declares no `draws`.
- **A drawing is a component that declares `draws`,** in the format every component has. Every other component a brand holds is one that content may place, as any library's is (DEC-004 point 1).
- **One layout each.** A drawing draws one layout of one top, so a brand that draws two layouts alike holds two drawings.
- **It declares nothing the content gives.** It takes the top's: the layout's slots and the fields it declares for their lists, the top's other fields, its options with their words, its states and its colour (DEC-009 point 5). So its file holds none of the keys `fields`, `options`, `states`, `colour`, `lists`, `layouts` and `ends`.
- **What it holds includes** what it is for, under `about`, as every component, its parts, its own named values, the size its instance asks for (point 2), and the parts it exposes, by the names the top exposes them by (DEC-009 point 5).
- **No token of the top.** It reads none of the top's component tokens ([visual-communication:DEC-035-component-tokens] point 3).

### 2. What a page gets stays where the top writes it, and a drawing writes what its instance asks for

- **One owner, by where a size is written.** Each size a page asks for or gets (DEC-005 point 3) is the drawing's or the top's by where it is written, never by what its formula reads.
- **A top whose layouts are its pages' forms** writes what each page gets in its own file: the width, and the height where it asks for one, in its `preferred` (DEC-022 point 3), or the height its physical size sets (point 3). No drawing gives such a page another size.
- **Each drawing of such a layout writes what its page asks for:** its height, in its own `preferred`, as the top's own drawing writes it in the layout, and no width. It must write the height where the top asks for none, and may where the top asks for one (DEC-022 points 3 and 8).
- **A top whose one layout is the whole top,** a page alone or a top whose slot holds pages, has its parts as that layout's drawing (DEC-009 point 1), so the size it asks for, its `preferred`, is that drawing's. A brand's drawing of it writes its own `preferred` whole, but for a height a physical size sets (point 3). Where the top's slot holds pages, it gives each page its size by the parts that place it, as the top's own drawing does.

### 3. A top printed at one size declares it, and an export maps each page onto it

- **Under one key.** A top whose pages are printed at one size, such as a poster, declares it under `physical-size`: its trim width and height, the size the printed sheet is cut to, in millimetres, each a positive number: `physical-size: {width: <mm>, height: <mm>}`. Each page of the top takes it.
- **The top's alone.** It belongs to the top, where the record of the engine places it (DEC-005 point 5), and no brand gives it a value. No formula reads it, so it is no length a formula takes.
- **Which tops.** A page alone, or a top whose layouts are its pages' forms. A top whose slot holds pages declares none, and nor does a drawing or any other component.
- **The height follows the proportion.** A top with a physical size asks for its width as any top does (point 2), and for its height through the size: the engine sets the height from that width and the size's proportion, and names itself as the height's source. So neither the top nor a drawing of its page alone asks for a height by a formula. A layout's drawing may still ask for its page's height, and a page that asks for more than it gets is reported as any element is (DEC-005 point 14).
- **The width sets the scale.** The page's width, a brand's value through a role (DEC-021 point 1), sets how large the brand's type and spacing print against the physical size.
- **Only the piece's top prints at it.** Placed in another component's slot, or as a page of another top, a top with a physical size asks for its size as it does alone, its height still following the proportion, and gets what the part that places it gives.
- **The scene's root holds it.** The root holds the physical size of the piece's top, beside whether its pages are fixed pages ([visual-communication:DEC-031-html-page-backdrop] point 2).
- **An export maps each page onto it.** An export whose format has a physical page, as PDF has, draws each page at that size, by one scale for the whole page. A page with no physical size keeps the mapping its renderer declares as its unit.
- **Each renderer says what it does with it.** A renderer declares whether its format has a physical page, and whether it maps a physical size onto it. One whose format has a page and does not map the size reports the loss (DEC-005 point 9), and one whose format has none loses nothing.
- **The seam's version rises,** so every renderer reads the root anew (DEC-005 point 8).
- **What breaks.** A top that comes to declare a physical size, ceases to, or changes its proportion breaks, as a top that starts or ceases to ask for a height does (DEC-022 point 8). A size changed in the same proportion breaks nothing ([visual-communication:DEC-003-change-over-time] point 6).

### 4. A top a brand holds is drawn by its own drawing alone

- **The holding brand serves it.** A brand may hold a top, as any library may (DEC-001 point 5). It draws each of the top's layouts by the top's own drawing, which is the brand's form, so it lacks none of them (DEC-009 points 4 and 6).
- **No brand declares a drawing of it.**
- **Under another brand.** A piece whose top a brand holds, drawn under a brand that is neither that brand nor built on it, is drawn by the top's own drawing, in its own brand's values. Its lock names the holding brand too, as it names the library of each component the piece uses. The check asks the piece's author for attention, naming the top and both brands, and that finding does not fail.

### 5. What a field shows keeps one trace id under every drawing

- **Named after the field.** In every drawing of a layout, the top's own and a brand's, each field the drawing shows is shown by a part at the drawing's top level that takes the field's name, and a part at the top level named after a field shows that field. The field is a slot of the layout, or another field of the top. A part *shows* a field where it places the component the field holds, draws the field's text or the picture file it names, or repeats over its items.
- **The ids that stay.** The instance keeps its id under every drawing: the top's name, or its page's path, never the drawing's name. The path to what a field shows is the instance's id and the field's name, under the top's own drawing and a brand's. How an id is derived does not change.
- **The drawing stays traced.** The instance's group names the drawing that drew it, with its brand's version (DEC-005 point 5), so each element traces back to its drawing through that group (DEC-009 point 2).
- **What keeps no id.** A drawing's other parts take ids of their own, which differ between drawings, as a private part's do (DEC-005 point 11). So does a second part that shows a field, as the record of sizes accepts (DEC-021 point 4).
- **A field passed on.** A part that passes a field to a component it places by `use` shows it one level down, at another id, so a drawing that shows a field only so breaks the rule.
- **In a top's own drawing,** a break of the rule asks the top's owner for attention, never failing.

### 6. One drawing draws an instance in every language and at every size

- **It fits in all, or draws in none.** A brand's drawing fits an instance only where it fits it in each language the piece holds, at every key over the size axes the piece names, each end it must find found at each key (DEC-009 point 6, DEC-021 point 7). Where it does not fit in one language or at one key, the top's own drawing draws that instance in every language and at every key, and the piece states it, naming the language or the key.
- **Chosen for the whole piece.** To choose the drawing for one scene, such as a preview in one language at one size, the engine places the piece in every language and at every key it names, as the search for a lock already does (DEC-021 point 7).

### 7. A drawing may choose by whether its instance is a page

- **A marked name says which.** A drawing of a layout reads whether its instance is a page, or part of a page, by the marked name `:as`. Its values are `page`, the default, and `part`, and no other. It reads it in a switch or a `when` that names the default, and a value it does not name takes the default's branch, as with a size (DEC-021 point 3).
- **Set by the engine,** from where the instance lies within its piece, never by content, so the name adds no scene, and a value it chose names `:as` as its source, a kind of its own (DEC-005 point 5).
- **Only a drawing of a layout reads it,** the top's own or a brand's.
- **A drawing that reads none** draws alike in both, as DEC-009 point 2 has it.

### 8. A drawing carries no status, and a base that begins to serve a top breaks nothing

- **No status.** A drawing's file holds none, and a change of its look breaks nothing (DEC-003 point 6).
- **A component that becomes a drawing.** A component the earlier version marks stable or deprecated, which the later declares a drawing, breaks, as one removed does (DEC-003 point 7, DEC-009 point 7). A drawing that ceases to be one is a new component.
- **A base that begins to serve a top breaks nothing.** Its drawings win along the chain (DEC-009 point 4). A brand built on it that drew that top draws it no more, and each piece under that brand states it (DEC-009 point 9). The change is one of how pages look, as a brand's beginning to draw a layout is (DEC-009 point 7), and the release's comparison does not read it.
- **A drawing of a top the base serves.** A brand's drawing of a layout of a top that its base serves asks the brand's owner for attention, to remove it, never failing.
- **DEC-009 overturned in part:** its point 7 counts the change as breaking for a base, and its point 9 fails such a drawing.

### 9. What this adds to format 1

- **Added, each optional:** the key `draws` on a brand's component, the key `physical-size` on a top, and the marked name `:as`. No file format 1 accepted declares `draws` or `physical-size`, or reads `:as`.

### 10. Where a finding lies, and how severely

- **Where it lies.** A finding on a drawing lies in the brand's version, judged when the brand is checked alone (DEC-009 point 9). One on a top lies in the top's library version, and one on a piece at the piece.
- **It fails, unless its point says otherwise.** A file that breaks a rule points 1 to 8 decide fails validation where it lies in a file the project can correct, and elsewhere, as in a released library version, asks for attention, naming who can correct it ([visual-communication:DEC-002-files-and-validation] point 7). A rule they restate from another record keeps the severity that record gives it.
- **What the release reads.** What points 3 and 8 count as breaking is read by the release's comparison, never by validation.

## Rationale

**Point 1, the drawing's own file.** A drawing's parts are written against one layout of one top (DEC-009 point 5), so the check reads that top to judge each reference they make. A file that names what it draws is judged alone, as any component is, and two drawings of one layout are two files, which DEC-009 point 9 already reports. Content gives the top what the top declares, whichever drawing draws it, and options of a drawing's own would let a brand ask content for words the top never offered. Why a drawing reads none of the top's tokens is DEC-035's to say, in its point 3 and its Alternatives considered.

**Point 2, sizes by where they are written.** Content is written against the top, and the top sets the room each page offers. A drawing that changed a deck's page size would change what fits on a slide under each brand. What a page asks for is its drawing's, since only the drawing knows its lowest part (DEC-022, Rationale). Splitting by where a size is written keeps the two apart. A top whose one layout is the whole top has no page size of its own to keep, since its parts are its drawing.

**Point 3, the physical size.** The size a page is printed at belongs to the kind of work, whichever brand draws it, and an order for the print relies on it, so switching the brand never sends a poster to the printer at another size. Kept out of formulas, it leaves the scene's lengths in one unit (DEC-005 point 1). A top whose slot holds pages gives its pages their sizes by its drawing (point 2), so it has none to declare. A brand tunes its type, spacing and widths to one another. Mapped at a renderer's fixed unit, a poster's text would print at the size a brand chose for a screen, and every brand would owe each poster sizes of its own before one read well. Scaled, a poster takes the brand's proportions as a slide does. Every page of the piece's top shares its size. A renderer that did not read it would draw a printed page at its own unit, a wrong size with no error. A change of proportion changes every page's height, where a change of size alone changes only how large a page prints. The known cost is a size that follows a region, such as A4 in Europe and US Letter in the United States.

**Point 4, a top a brand holds.** The holding brand made that form, as a base makes the form of a top it serves, so a brand built on it keeps it (DEC-004 point 6). A kind of work meant for many brands has its place in a component library, whose tops each brand may draw (DEC-009 point 3). A piece may already lock a second brand by placing one of its parts ([visual-communication:DEC-025-picture-files], Context). What the piece's author needs to know is that its form is another brand's, drawn in its own brand's values, which two records name as the cost of mixing brands (DEC-008 and DEC-009, Alternatives considered).

**Point 5, the naming rule.** Ids that changed with the brand would recreate every object on a board, repeat each loss a person accepted, and leave a program's frame unfound (DEC-005 points 7, 9 and 11). A field's name is part of the top that every drawing is written against, so the rule ties ids to no private part. Its cost is the reuse of a field's look: a brand cannot pass a slot into one title band of its own shared by its cover and its slide. It may still share the band, and repeats in each drawing only the part that shows the field. A brand's drawing is new, so its rule may fail. A top's own drawing was accepted, so its rule asks, since where it is broken what the field shows takes another id under a brand's drawing.

**Point 6, one drawing everywhere.** A page drawn at three sizes, or in two languages, is one design, which a reviewer compares across them. A page drawn by the brand's drawing in one and by the top's own in another would show two owners' forms of one page, and its fields would change ids between them. A field's runs may take other words in another language (DEC-012), so a fit can differ there too. The cost is that a drawing which fails in one gives way in all.

**Point 7, a marked name, and not a frame.** A brand's drawing draws its instance as the piece's top and placed in another component's slot alike (DEC-009 point 2), and the need is page dressing, such as a backdrop or the brand's mark, drawn only where an instance is a page. A drawing that reads `:as` keeps one form for one layout. Two drawings, or a frame drawn around the top's own drawing, would add a second kind of drawing for a brand to keep in step. The name is a declared choice, as a size is (DEC-021 point 3), so formulas stay arithmetic (DEC-005 point 1). It lets a placer change what a drawing draws, which the record of sizes keeps from every other component, each answering to its placer only by formulas on `:width` (DEC-021 point 6). A top's instance alone is a page in one piece and a part in another.

**Point 8, no status, and a base that begins to serve a top.** A component's status says what its library promises to what names the component (DEC-003 point 7), and no content names or places a drawing (DEC-009 point 5), so a status on a drawing would warn pieces that never name it. A base that begins to serve a top leaves every page drawing, in the base's form, and the brand built on it keeps every value and every other drawing. A piece meets that change only when a person moves its lock (DEC-001 point 7). Read as a break, any brand could become a base, and a brand cannot know which brands are built on it. So every brand would need a major to draw a top published after it, as the use case of adding a kind of piece asks of each brand a project uses, and a major moves every brand built on it in turn. Failing the brand built on the base would make the same change a break by another road, letting a base's minor release stop the check of a project's own brand built on it. The brand's drawing then draws nothing and breaks no rule a piece relies on, so the check asks its owner to act (DEC-002 point 7). The cost falls on that owner: a minor release of the base may replace the brand's form of a top with the base's, at the next render of a draft.

**Points 9 and 10, the format and the findings.** Until validation accepts files at an older format number, no field becomes required, and no value a schema accepted is refused (DEC-003 point 3). The release's comparison reads an earlier version, so it is a command, not validation (DEC-003 point 7).

### Alternatives considered

- **A list of a brand's drawings in its library file:** the fact would lie in two places.
- **A drawing that declares fields or options of its own:** content could never give them.
- **A drawing, or a brand, that gives a page of a deck another size, or a top another physical size:** for the reasons the Rationale gives under points 2 and 3.
- **A size owned by what its formula reads:** the engine would read each formula, through named values, to learn what owns a size, which the record of the deck's page backdrop rejected as a test (DEC-031, Alternatives considered).
- **A physical size mapped at the renderer's fixed unit:** for the reason the Rationale gives under point 3.
- **A physical size the top maps at a ratio it declares, in px per millimetre:** it would set a page's width apart from the brand, against DEC-021 point 1, though it prints a piece's type at one size under every brand.
- **A page's width and height each by a role, the proportion checked against the paper:** the proportion would have two owners, and a brand's values could fail a piece.
- **A physical size in a unit its file names, such as inches:** every reader of the size would convert it, and one paper could be written two ways. Millimetres are ISO's unit and printers'.
- **A physical size by the name of a paper, such as `a1`:** a list the capability keeps would make a project's own paper a change of the capability.
- **A top offered at several physical sizes, chosen by an option:** put off until a top needs it.
- **A top a brand holds that other brands may draw:** one brand would replace another's form.
- **A top a brand holds, failing under a brand outside its chain:** it would refuse a piece format 1 accepted, whose top any library may hold, a brand among them (DEC-003 point 3).
- **A top a brand holds, used under any brand with nothing said:** for the reason the Rationale gives under point 4.
- **No top held by a brand:** the format reads one already, and refusing it would refuse a file format 1 accepted.
- **A field's id derived from the field's name by the engine, whatever part shows it:** a field shown by two parts would give two elements one id, and the derivation of every id would change, with a map from old ids to new.
- **A second key on each element that shows a field, kept beside its trace id for a lasting medium to match by:** every reader of an id, a loss and a program's frame among them, would learn a second name.
- **Ids that differ from one drawing to another:** for the costs the Rationale gives under point 5.
- **A brand's drawing chosen at each size, or in each language, alone:** for the reason the Rationale gives under point 6.
- **A brand's drawing that draws only where its top is a page:** a brand's figure would lose its form in every slide, against DEC-009 point 2.
- **Two drawings of a layout, one for a page and one for a part, or a frame around the top's own drawing** (DEC-009, Alternatives considered): rejected for this need, for the reason the Rationale gives under point 7.
- **A drawing that carries a status, as any component does:** for the reason the Rationale gives under point 8.
- **A base that begins to serve a top needs a major, and the release's comparison reads it:** for the reason the Rationale gives under point 8.
- **A base that begins to serve a top left as a break no release reads:** a break would ship in a minor release.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-009 point 2, "A component of the brand,"** comes to say that the drawing's own file names the top and the layout it draws, under `draws`, and declares nothing the content gives (point 1).
  - **DEC-009 point 2, "It wins,"** comes to add that a drawing may choose by whether its instance is a page or part of one (point 7).
  - **DEC-009 point 2, "Traced,"** comes to say that an element traces back to its drawing through its instance's group, which names the drawing, and that what a field shows keeps the field's id under every drawing (point 5).
  - **DEC-009 point 4, "Serving,"** comes to add that a brand that holds a top draws each of its layouts by the top's own drawing, and so serves it (point 4).
  - **DEC-009 point 6, "A drawing that does not fit,"** comes to say that a brand's drawing fits an instance only where it fits it in each language the piece holds and at every key over the size axes it names, and that otherwise the top's own drawing draws it in all of them (point 6).
  - **DEC-009 point 8, "Added later, as an addition,"** comes to say that the declaration is the key `draws` in the drawing's own file (point 1).
  - **DEC-009's Implications, "A brand's own form is built later,"** come to say that [visual-communication:DEC-034-brand-drawings] decides the questions they list, and that the Tasks it names build it.
  - **DEC-009's top line** comes to read as below (point 8).
    > **Partially superseded by [visual-communication:DEC-034-brand-drawings].** Overturned: point 7's "Breaking, for a base", since a base that begins to serve a top breaks nothing. Also overturned: point 9's failure of a drawing of a layout of a top that the brand's base serves, which asks for attention instead. The rest stands.
  - **DEC-005 point 1, "A choice is declared, never computed,"** comes to add that a drawing of a layout may also choose by whether its instance is a page, read by `:as` (point 7).
  - **DEC-005 point 3, "Two sizes for each element,"** comes to add that a top with a physical size asks for its height through it (point 3).
  - **DEC-005 point 5, "A tree of groups,"** comes to say that a top declares its physical size under `physical-size`, in millimetres, that the engine sets its height from the width asked for and the size's proportion, and that an export whose format has a physical page draws each page of the piece's top at that size, by one scale (point 3).
  - **DEC-005 point 5, "The root says what the scene is,"** comes to add the physical size of the piece's top (point 3).
  - **DEC-005 point 5, "Every element carries its trace,"** comes to add that an instance keeps its id under every drawing, that what a field shows takes the field's name, and that `:as` is a source of its own (points 5 and 7).
  - **DEC-005 point 9, "Each declares what it supports,"** comes to add that a renderer declares whether its format has a physical page, and whether it maps a top's physical size onto it (point 3).
  - **DEC-003 point 7's opening** comes to say that each library component but a drawing carries a status (point 8).
  - **DEC-021 point 3, "Only a size axis a piece can name,"** comes to add that a drawing of a layout also reads `:as` (point 7).
  - **DEC-021 point 6** comes to add that a drawing of a layout also answers to whether its instance is a page (point 7).
  - **DEC-021 point 7's list of what fails** comes to except `:as` in a drawing of a layout from "a marked name that reads no size axis", and to add the findings on `:as` (points 7 and 10).
  - **DEC-021's Implications, "Left open,"** come to say that this record decides a brand's drawing at each key (point 6).
  - **DEC-022 point 3, "A page's height,"** comes to add that a brand's drawing writes its page's height in its own file, as a layout does (point 2).
  - **DEC-022 point 3, "What a page gets,"** comes to add that a top with a physical size asks for a height through it (point 3).
  - **DEC-022's Implications, "Left open,"** come to say that this record decides how a brand's drawing of a site's layout writes its page's height (point 2).
- **The Tasks that build it,** each under [project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573), filed once this record is accepted. They take the five Tasks that the Feature's closure audit drafted, which [project-kit#2965](https://github.com/aleskalfas/project-kit/issues/2965) names, and add two. Each builds the findings of its own points.
  - **A brand draws a layout, and a piece is drawn by that drawing where it fits:** points 1, 2, 5 and 6, first.
  - **The check judges a brand's drawings alone:** the findings DEC-009 point 9, DEC-011 and DEC-012 place on a brand's drawing, after the first.
  - **A brand built on a base, and a top a brand holds:** point 4, after the first.
  - **The release reads a brand's components,** new: point 8, and the comparison of a brand's other components that DEC-003 point 7 decides, after the first.
  - **A top's physical size, and the exports that map it:** point 3, giving each renderer's declaration its answer, since every renderer is the capability's (DEC-005 point 12).
  - **A drawing chooses by whether its instance is a page,** new: point 7, after the first.
  - **A project adds a poster, and its brand draws it:** after the Tasks of a drawing and of a physical size. A test project's own poster and brand render, check and export, and no file of the capability changes.
- **Read against this answer, and left as they stand:**
  - DEC-001 point 5, since a library may hold a top, and a physical size is the top's, which no brand gives a value.
  - DEC-003 points 3 and 6, since each change to the format is an addition, and a physical size changed in the same proportion is a change of how pages look.
  - DEC-004 point 1, since a drawing takes the format every component has, with `draws`. Point 5, since this adds no way for a brand to break. Point 6, since a brand built on a base keeps the form of a top its base holds.
  - DEC-005 point 11, since the derivation of trace ids does not change.
  - DEC-010 point 5, since a page names its layout, never its drawing.
  - DEC-011 and DEC-012, since a drawing's fit to ends and runs holds as they decide, in each language and at each key.
  - DEC-013 points 3 and 6, since beginning to serve a top breaks nothing, so a brand the capability ships may do it within a major.
  - DEC-021 point 1, since a width stays a brand's value, and sets a printed page's scale.
  - DEC-025 point 8, since the command that moves a piece onto another brand reads the brand the piece names.
  - DEC-031 point 2, since a top with a physical size whose layouts are its pages' forms asks for a height through it, so its pages are fixed pages, and a poster that is a page alone is none.
- **Left open:**
  - whether a brand may name a brand other than its base, and so place that brand's parts
  - a physical size with bleed, the margin printed past the trim and cut away
  - a frame around the top's own drawing, as a kind of drawing of its own
  - what gives the tokens of a brand's own components their values, which DEC-035 point 7 leaves to the change that builds a brand's own components
