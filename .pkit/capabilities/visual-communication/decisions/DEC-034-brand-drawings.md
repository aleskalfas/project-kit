---
id: DEC-034
title: A brand's drawing names its layout in its own file, and keeps the sizes and field names its top sets
status: proposed
date: 2026-11-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand draws a layout with a component of its own, whose file names the top and the layout, such as the deck's cover, and which takes only the content the top declares. A page keeps the size its top sets, and a drawing writes only what its page asks for. A top printed at one size declares that size in millimetres, and an export with physical pages scales each page onto it. A top a brand holds is drawn by the top's own drawing, which no other brand replaces. Each part that shows a field is named after the field, so what it shows keeps its trace id when the brand changes. One drawing draws a page in every language and at every size, and may leave a page's dressing out where its top lies inside another page. A drawing carries no status, and a base brand that begins to serve a top breaks nothing: its drawings win, and a brand built on it is asked to drop its own. No drawing's look and no brand's values are decided here.

## Context

The record of layouts lets a brand hold its own drawing of a layout of a top whose library it names. The brand's drawing draws each instance it fits, in place of the top's own drawing. Along a chain of brands, the brand nearest the root that serves a top keeps its form ([visual-communication:DEC-009-layout-defaults] points 2 to 6). That record adds no field. It leaves to the change that builds a brand's own form the declaration by which a brand says, for each layout it draws, the top, the layout and the component that draws it (point 8). Its Implications leave five more questions to that change:
- whether a drawing may give a page another physical size than its top declares
- how a top component that a brand holds relates to drawings, since a brand's version may hold components, a top among them
- whether what a slot places keeps its trace id under every drawing
- how a drawing written for a page alone draws where its top is placed inside another page
- the status a drawing carries, and whether the release's comparison reads a base that begins to serve a top

The record of sizes leaves one more: a brand's drawing at each size a piece is drawn at ([visual-communication:DEC-021-size-and-shape], Implications).

Five facts bear on the answers:
- **A physical size has no form yet.** The record of the engine has a top whose pages have a physical size declare it, and an export map the scene's unit onto it ([visual-communication:DEC-005-engine-and-plugins] point 5). No file carries one, so each renderer declares a mapping of its own as its unit.
- **A page asks for a size, and gets one,** as every element does (DEC-005 point 3). A top whose layouts are its pages' forms writes what its pages get in its own file, and each layout may write the height its page asks for. The record of the web page leaves open how a brand's drawing writes it ([visual-communication:DEC-022-web-site-and-parts] point 3 and Implications).
- **Trace ids follow the parts.** An element's trace id comes from the path of instances, parts and item ids (DEC-005 point 5). A lasting medium's record, a loss a person accepted and a frame that a program run while preparing reads each name an element by it (DEC-005 points 7, 9 and 11). The deck and the figure name each part that places a slot after that slot (DEC-009, Implications).
- **A piece may lock a second brand.** A piece uses its top's library and each library whose component it places, beside its brand. So a piece that places a brand's part locks that brand, whichever brand it names ([visual-communication:DEC-025-picture-files], Context). Two records rejected a default that would have every piece under a brand lock a second one, and mix two brands' forms (DEC-008 and DEC-009, Alternatives considered).
- **The format grows by additions.** Until validation accepts files at an older format number, no field becomes required, and no value a schema accepted is refused ([visual-communication:DEC-003-change-over-time] point 3).

## Decision

**A brand's drawing is a component of the brand whose file names the top and the layout it draws, and declares nothing the content gives. What a page gets stays where the top writes it, a physical size among it, and a drawing writes what its instance asks for. A top a brand holds is drawn by its own drawing alone. Each part that shows a field is named after it. One drawing draws an instance in every language and at every size, and may choose by whether its instance is a page. A drawing carries no status, and a base that begins to serve a top breaks nothing.**

### 1. A drawing names in its own file the top and the layout it draws

- **The declaration.** A brand declares a drawing by holding a component whose file names, under the key `draws`, a top by `<library>/<component>` and one of its layouts: `draws: {top: <library>/<component>, layout: <layout>}`. This is the declaration DEC-009 point 8 leaves to this change. Nothing else lists a brand's drawings, so a drawing and what it draws are read and checked as one file.
- **A drawing is a component that declares `draws`.** Every other component a brand holds is one that content may place, as any library's is (DEC-004 point 1).
- **One layout each.** A drawing draws one layout of one top. A brand that draws two layouts alike holds two drawings.
- **It declares nothing the content gives.** It takes the top's: the layout's slots and the fields it declares for their lists, the top's other fields, its options with their words, its states and its colour (DEC-009 point 5). So its file holds none of the keys `fields`, `options`, `states`, `colour`, `lists`, `layouts` and `ends`.
- **What it holds:** what it is for, under `about`, as every component, its parts, its own named values, the size its instance asks for (point 2), and the parts it exposes, by the names the top exposes them by (DEC-009 point 5).

### 2. What a page gets stays where the top writes it, and a drawing writes what its instance asks for

A page asks for a size and gets one (DEC-005 point 3). Each size is the drawing's or the top's by where it is written, never by what its formula reads.
- **A top whose layouts are its pages' forms** writes what each page gets in its own file: the width, and the height where it asks for one, in its `preferred` (DEC-022 point 3), or the height its physical size sets (point 3). Every page gets it under every drawing. So a drawing never gives such a page another size.
- **Each drawing of such a layout writes what its page asks for:** its height, in its own `preferred`, as the top's own drawing writes it in the layout. It must where the top asks for no height, and may where the top asks for one (DEC-022 points 3 and 8). It writes no width, since a page always gets the top's.
- **A top whose one layout is the whole top,** a page alone or a top whose slot holds pages, has its parts as that layout's drawing (DEC-009 point 1). The size it asks for, its `preferred`, belongs to that drawing. A brand's drawing of it writes its own `preferred` whole, and, where the top's slot holds pages, gives each page its size by the parts that place it, as the top's own drawing does. Where the top has a physical size, that sets its height (point 3).
- **So each size has one owner.** The check reads where a size is written, and reads no formula to learn what it depends on ([visual-communication:DEC-031-html-page-backdrop], Alternatives considered).

### 3. A top printed at one size declares it, and an export maps each page onto it

- **Under one key.** A top whose pages are printed at one size, such as a poster, declares that size under `physical-size`: its trim width and height, the size the printed sheet is cut to, in millimetres, each a positive number: `physical-size: {width: <mm>, height: <mm>}`. Each page of the top takes it. How a size with bleed, the margin printed past the trim and cut away, is declared is left open.
- **The kind of work's, not the brand's.** A top is printed at its size whichever brand draws it, so the size belongs to the top, where the record of the engine places it (DEC-005 point 5), and no brand gives it a value. No formula reads it, so it is no length a formula takes, and the scene's lengths stay in one unit (DEC-005 point 1).
- **Which tops.** A page alone, or a top whose layouts are its pages' forms. A top whose slot holds pages declares none, since its drawing gives its pages their sizes (point 2). Nor does a drawing or any other component.
- **The height follows the proportion.** The width is asked for as any top's is: in the top's `preferred` where its layouts are its pages' forms, or in its drawing's where it is a page alone (point 2). A top with a physical size asks for its height through it: the engine sets the height from that width and the size's proportion, and names itself as the height's source. So the top asks for no height by a formula, and nor does a drawing of a page alone. A layout's drawing may still ask for its page's height, and a page that asks for more than it gets is reported as any element is (DEC-005 point 14).
- **The width sets the scale.** The physical size sets how large a page prints. The width, a brand's value through a role ([visual-communication:DEC-021-size-and-shape] point 1), sets how large the brand's type and spacing print against it.
- **Only the piece's top prints at it.** Placed in another component's slot, or as a page of another top, a top with a physical size asks for its size as it does alone, its height still following the proportion, and gets what the part that places it gives.
- **An export maps each page onto it.** The scene's root holds the physical size of the piece's top, beside whether its pages are fixed pages (DEC-031 point 2), since every page of that top shares it. An export whose format has a physical page, as PDF has, draws each page at that size, by one scale for the whole page. A page with no physical size keeps the mapping its renderer declares as its unit.
- **Each renderer says what it does with it.** A renderer declares whether its format has a physical page, and whether it maps a physical size onto it. One whose format has a page and does not map the size reports the loss (DEC-005 point 9), and one whose format has none loses nothing. Every renderer is the capability's (DEC-005 point 12), so the change that adds the size gives each declaration its answer.
- **The seam's version rises.** A renderer that did not read the size would draw a printed page at its own unit, a wrong size with no error, so every renderer must read the root anew (DEC-005 point 8).
- **What breaks.** A top that comes to declare a physical size, ceases to, or changes its proportion breaks, since every page's height changes with it, as a top that starts or ceases to ask for a height does (DEC-022 point 8). A size changed in the same proportion changes only how large a page prints, which breaks nothing (DEC-003 point 6).

### 4. A top a brand holds is drawn by its own drawing alone

- **The brand's own kind of work.** A brand may hold a top, as any library may (DEC-001 point 5). It draws each of the top's layouts by the top's own drawing, which is the brand's form. So it serves the top, and lacks none of its layouts (DEC-009 points 4 and 6).
- **No brand declares a drawing of it.** The brand that holds it draws it already, and a brand built on that brand keeps its form (DEC-009 point 4). Another brand's drawing would replace that brand's form. A kind of work meant for many brands lies in a component library, whose tops each brand may draw (DEC-009 point 3).
- **Under another brand.** A piece whose top a brand holds, drawn under a brand that is neither that brand nor built on it, is drawn by the top's own drawing, in its own brand's values. Its lock names the holding brand too, as it names the library of each component the piece uses. The check asks the piece's author for attention, naming the top and both brands, since the piece shows one brand's form in another's values. It does not fail, since format 1 accepted such a piece (DEC-003 point 3).

### 5. What a field shows keeps one trace id under every drawing

- **A part named after a field shows it.** In every drawing of a layout, the top's own and a brand's, each field the drawing shows is shown by a part at the drawing's top level that takes the field's name. The field is a slot of the layout, or another field of the top, as a site's header is. A part *shows* a field where it places the component the field holds, draws the field's text or the picture file it names, or repeats over its items. A part at the top level named after a field shows that field.
- **So the ids stay.** The instance keeps its id under every drawing: the top's name, or its page's path, never the drawing's name. The path to what a field shows is the instance's id and the field's name, under the top's own drawing and a brand's. So switching the brand keeps each id that a lasting medium's record, an accepted loss or a frame a program reads names (DEC-005 points 7, 9 and 11). How an id is derived does not change.
- **The drawing stays traced.** The instance's group names the drawing that drew it, with its brand's version (DEC-005 point 5). So each element traces back to its drawing through that group (DEC-009 point 2).
- **What keeps no id.** A drawing's other parts take ids of their own, which differ between drawings, as a private part's do (DEC-005 point 11). So does a second part that shows a field, as the record of sizes accepts (DEC-021 point 4).
- **A field passed on.** A part that passes a field to a component it places by `use` shows it one level down, at another id. A drawing that shows a field only so breaks the rule (point 10).

### 6. One drawing draws an instance in every language and at every size

- **Fit at every size and in every language.** A brand's drawing fits an instance only where it fits it in each language the piece holds, at every key over the size axes the piece names, each end it must find found at each key (DEC-009 point 6, DEC-021 point 7). A field's runs may take other words in another language (DEC-012), so a fit can differ there too. Where the drawing does not fit in one language or at one key, the top's own drawing draws that instance in every language and at every key, and the piece states it, naming the language or the key.
- **So a page keeps one form across its sizes and languages,** and what its fields show keeps one id. This decides the brand's drawing at each key that the record of sizes leaves open.
- **What it costs.** Choosing the drawing for one scene, such as a preview in one language at one size, places the piece in every language and at every key it names, as the search for a lock already does (DEC-021 point 7).

### 7. A drawing may choose by whether its instance is a page

- **Wherever its top is drawn.** A brand's drawing draws its instance as the piece's top, and placed in another component's slot (DEC-009 point 2). A drawing written for a page alone, such as one that draws a page's backdrop and the brand's mark, would draw them inside a slide too.
- **A marked name says which.** A drawing of a layout reads whether its instance is a page, or part of a page, by the marked name `:as`. Its values are `page`, the default, and `part`. It reads it in a switch or a `when` that names the default, and a value it does not name takes the default's branch, as with a size (DEC-021 point 3). So one drawing leaves its backdrop out where its figure lies in a slide.
- **Set by the engine,** from where the instance lies, never by content: a choice declared, never computed (DEC-005 point 1). An instance is a page or a part within its piece, so the name adds no scene. A value it chose names `:as` as its source, a kind of its own (DEC-005 point 5).
- **Only a drawing of a layout reads it,** the top's own or a brand's. Only a top's instance is a page in one piece and part of a page in another. Every other component answers to the part that places it only by formulas on `:width` (DEC-021 point 6).
- **A drawing that reads none** draws alike in both, as DEC-009 point 2 has it.

### 8. A drawing carries no status, and a base that begins to serve a top breaks nothing

- **No status.** A component's status says what its library promises to what names the component (DEC-003 point 7). No content names a drawing, and none places one (DEC-009 point 5). So a drawing promises no piece anything, and its file holds no status. A change of its look breaks nothing (DEC-003 point 6).
- **A component that becomes a drawing.** A component the earlier version marks stable or deprecated, which the later declares a drawing, breaks, as one removed does (DEC-003 point 7, DEC-009 point 7). The release's comparison reads it. A drawing that ceases to be one is a new component.
- **A base that begins to serve a top breaks nothing.** Its drawings win along the chain (DEC-009 point 4). A brand built on it that drew that top draws it no more, and each piece under that brand states it (DEC-009 point 9). Every page still draws, in the base's form, and a piece meets the change only when a person moves its lock (DEC-001 point 7). So it changes how pages look, as a brand that begins to draw a layout does (DEC-009 point 7). The release's comparison does not read it.
- **So a drawing of a top its base serves asks for attention, never failing.** It names the brand's owner, who removes the drawing. The drawing draws nothing and breaks no rule a piece relies on, so the check asks its owner to act and fails nothing (DEC-002 point 7). A failure would also make a base's minor release stop the check of a project's own brand built on it. This overturns DEC-009 in part: its point 7 counts the change as breaking for a base, and its point 9 fails such a drawing.

### 9. What this adds to format 1

- **Added:** the key `draws` on a component of a brand, the key `physical-size` on a top, and the marked name `:as`. Each is optional, so no field becomes required (DEC-003 point 3).
- **A drawing's file** takes the format every component has (DEC-004 point 1), with `draws`. It refuses the keys point 1 names, `status` and `physical-size`. Every other component requires a status. A drawing of a layout of a top whose layouts are its pages' forms writes only a height in its `preferred`.
- **Nothing accepted is refused.** No file format 1 accepted declares `draws` or `physical-size`, or reads `:as`. Its tops have no physical size, so each renderer maps their pages as before. Two findings that a file format 1 accepted could meet ask for attention, and fail nothing: a top's own drawing that names no part after a field it shows (point 5), and a piece whose top a brand outside its brand's chain holds (point 4).

### 10. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, as the record of files and validation decides ([visual-communication:DEC-002-files-and-validation] point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it. A finding on a drawing lies in the brand's version, judged when the brand is checked alone (DEC-009 point 9). One on a top lies in the top's library version, and one on a piece at the piece.
- **Fails validation:**
  - `draws` on a component outside a brand, a library's or a local one, or on a component that holds a key point 1 names, `status` or `physical-size` (points 1 and 9)
  - a drawing of a top that a brand holds (point 4)
  - a brand's drawing of a layout of a top whose layouts are its pages' forms that writes a width, or writes no height where the top asks for none (point 2)
  - in a brand's drawing, a field it shows by no part at its top level named after the field, or a part at its top level named after a field that it does not show (point 5)
  - `physical-size` on a component that is no top, or on a top whose slot holds pages (point 3)
  - a physical size whose width or height is not a positive number (point 3)
  - a height asked for by a formula in a top with a physical size, or in a drawing of its page alone (point 3)
  - a switch or a `when` by `:as` outside a drawing of a layout, or one that names a value `:as` lacks or leaves out the default (point 7)
- **Asks for attention, never failing:**
  - in a top's own drawing, a field it shows by no part at its top level named after the field, or a part so named that does not show it. What the field shows then takes another trace id under a brand's drawing. It names the top's owner. Format 1 accepted such a top, so it does not fail (DEC-003 point 3).
  - a piece whose top a brand holds, drawn under a brand that is neither that brand nor built on it, naming the top and both brands (point 4)
  - a drawing of a layout of a top that the brand's base serves (point 8)
- **Stated as a fact,** at a piece: an instance drawn by the top's own drawing because the brand's drawing does not fit it in one language or at one key, naming it (point 6).
- **Read by the release, never by validation:** a stable or deprecated component a brand comes to declare a drawing (point 8), and a physical size a top comes to declare, ceases to declare, or gives another proportion (point 3). The comparison reads an earlier version, so it is a command (DEC-003 point 7).

## Rationale

**Why the drawing's own file names what it draws.** A drawing's parts are written against one layout of one top (DEC-009 point 5). So the check reads that top to judge each reference they make. A file that names what it draws is judged alone, as any component is. Two drawings of one layout are two files, which DEC-009 point 9 already reports. A list in the brand's library file would leave a drawing unreadable without it, and keep one fact in two places.

**Why it declares nothing the content gives.** Content gives the top what the top declares, whichever drawing draws it (DEC-009 point 5). A field a drawing declared could never be given to it. Options of its own would let a brand ask content for words the top never offered.

**Why what a page gets stays where the top writes it.** Content is written against the top, and the top sets the room each page offers. A drawing that changed a deck's page size would change what fits on a slide under each brand. What a page asks for is its drawing's, since only the drawing knows its lowest part (DEC-022, Rationale). Splitting by where a size is written keeps the two apart with no reading of formulas, which the record of the deck's page backdrop rejected as a test (DEC-031, Alternatives considered). A top whose one layout is the whole top has no page size of its own to keep, since its parts are its drawing.

**Why a physical size belongs to the top.** The size a page is printed at belongs to the kind of work, and an order for the print relies on it. So no brand gives it, and switching the brand never sends a poster to the printer at another size. The known cost is a size that follows a region, such as A4 in Europe and US Letter in the United States: a top offered at both waits for a change of its own (Alternatives considered).

**Why a physical size scales a page whose width a role gives.** A brand tunes its type, spacing and widths to one another. Mapped at a renderer's fixed unit, a poster's text would print at the size a brand chose for a screen, and every brand would owe each poster sizes of its own before one read well. Scaled, a poster takes the brand's proportions as a slide does, and the width role sets how large its type prints against the paper, which a width already is a brand's value for (DEC-021 point 1). The proportion comes from the physical size, so the page's height has one owner, and no pair of roles can disagree with the paper. Paper sizes are given in millimetres, ISO's and printers' alike.

**Why a top a brand holds is drawn by its own drawing alone.** The holding brand made that form, as a base makes the form of a top it serves, so a brand built on it keeps it (DEC-004 point 6). Another brand's drawing would replace that form. A kind of work meant for many brands has its place in a component library.

**Why a held top under another brand asks, and does not fail.** Format 1 accepted a piece whose top any library holds, a brand among them, so failing it would refuse a file it accepted (DEC-003 point 3). A piece may already lock a second brand by placing one of its parts ([visual-communication:DEC-025-picture-files], Context). What the piece's author needs to know is that its form is another brand's, drawn in its own brand's values, which two records name as the cost of mixing brands (DEC-008 and DEC-009, Alternatives considered). The finding tells them.

**Why a naming rule keeps the ids.** Ids that changed with the brand would recreate every object on a board, repeat each loss a person accepted, and leave a program's frame unfound (DEC-005 points 7, 9 and 11). A field's name is part of the top that every drawing is written against, so the rule ties ids to no private part. It keeps the derivation of ids as it is, so no map from old ids to new is needed (DEC-005 point 11). Its cost is the reuse of a field's look: a brand cannot pass a slot into one title band of its own shared by its cover and its slide. A brand's drawing is new, so its rule may fail. A top's own drawing was accepted, so its rule asks.

**Why one drawing in every language and at every size.** A page drawn at three sizes, or in two languages, is one design, which a reviewer compares across them. A page drawn by the brand's drawing in one and by the top's own in another would show two owners' forms of one page, and its fields would change ids between them. The cost is that a drawing which fails in one gives way in all.

**Why a marked name, and not a frame.** The need is page dressing, such as a backdrop or a mark, drawn only where an instance is a page. A drawing that reads `:as` keeps one form for one layout. Two drawings, or a frame drawn around the top's own drawing, would add a second kind of drawing for a brand to keep in step. The name is a declared choice, as a size is (DEC-021 point 3), so formulas stay arithmetic (DEC-005 point 1). It lets a placer change what a drawing draws, which the record of sizes keeps from every other component (DEC-021 point 6). A top's instance alone is a page in one piece and a part in another, so only its drawing reads it.

**Why no status.** A status promises something to what names a component, and nothing names a drawing. A status on a drawing would warn pieces that never name it.

**Why a base that begins to serve a top breaks nothing.** Every page still draws, in the base's form, and the brand built on it keeps every value and every other drawing. That is what DEC-009 calls a change of how pages look, which a piece meets only when its lock moves. Read as a break, any brand could become a base, and a brand cannot know which brands are built on it. So every brand would need a major to draw a top published after it, as the use case of adding a kind of piece asks of each brand a project uses, and a major moves every brand built on it in turn. Failing the brand built on the base would make the same change a break by another road. The cost falls on the owner of a brand built on the base: a minor release of the base may replace that brand's form of a top with the base's, at the next render of a draft, and the owner is only asked to act.

### Alternatives considered

- **A list of a brand's drawings in its library file.** Rejected. A drawing could not be read alone, and the fact would lie in two places.
- **A drawing that declares fields or options of its own.** Rejected. Content could never give them.
- **A drawing, or a brand, that gives a page of a deck another size, or a top another physical size.** Rejected. What fits a page, and the size a piece prints at, would change with the brand.
- **A size owned by what its formula reads.** Rejected. The engine would read each formula, through named values, to learn what owns a size, as DEC-031 rejected.
- **A physical size mapped at the renderer's fixed unit.** Rejected. A brand's sizes for a screen would print too small on a poster, and every brand would owe each poster its own.
- **A physical size the top maps at a ratio it declares, in px per millimetre.** Rejected. It would set a page's width apart from the brand, against DEC-021 point 1, though it prints a piece's type at one size under every brand.
- **A page's width and height each by a role, the proportion checked against the paper.** Rejected. The proportion would have two owners, and a brand's values could fail a piece.
- **A physical size by the name of a paper, such as `a1`.** Rejected. A list the capability keeps would make a project's own paper a change of the capability.
- **A top offered at several physical sizes, chosen by an option.** Put off until a top needs it.
- **A top a brand holds that other brands may draw.** Rejected. One brand would replace another's form.
- **A top a brand holds, failing under a brand outside its chain.** Rejected. It would refuse a piece format 1 accepted.
- **A top a brand holds, used under any brand with nothing said.** Rejected. The piece's author would not learn that its form is another brand's.
- **No top held by a brand.** Rejected. The format reads one already, and refusing it would refuse a file format 1 accepted.
- **A field's id derived from the field's name by the engine, whatever part shows it.** Rejected. A field shown by two parts would give two elements one id, and the derivation of every id would change, with a map from old ids to new.
- **A second key on each element that shows a field, kept beside its trace id for a lasting medium to match by.** Rejected. Every reader of an id, a loss and a program's frame among them, would learn a second name.
- **Ids that differ from one drawing to another.** Rejected, for the costs above.
- **A brand's drawing chosen at each size, or in each language, alone.** Rejected. One page would show two forms across its sizes or its languages.
- **A brand's drawing that draws only where its top is a page.** Rejected. A brand's figure would lose its form in every slide, against DEC-009 point 2.
- **Two drawings of a layout, one for a page and one for a part, or a frame around the top's own drawing** (DEC-009, Alternatives considered). Rejected for this need, for the reason above. A frame may still come as a kind of drawing of its own.
- **A drawing that carries a status, as any component does.** Rejected. It would promise nothing.
- **A base that begins to serve a top needs a major, and the release's comparison reads it.** Rejected. Every brand a project uses would need a major to draw a top published after it, and every brand built on it a major in turn.
- **A base that begins to serve a top left as a break no release reads.** Rejected. A break would ship in a minor release, and fail the brands built on it.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-009 point 2, "A component of the brand,"** comes to say that the drawing's own file names the top and the layout it draws, under `draws`, and declares nothing the content gives (point 1).
  - **DEC-009 point 2, "It wins,"** comes to add that a drawing may choose by whether its instance is a page or part of one (point 7).
  - **DEC-009 point 2, "Traced,"** comes to say that an element traces back to its drawing through its instance's group, which names the drawing, and that what a field shows keeps the field's id under every drawing (point 5).
  - **DEC-009 point 4, "Serving,"** comes to add that a brand that holds a top draws each of its layouts by the top's own drawing, and so serves it (point 4).
  - **DEC-009 point 6, "A drawing that does not fit,"** comes to say that a brand's drawing fits an instance only where it fits it in each language the piece holds and at every key over the size axes it names, and that otherwise the top's own drawing draws it in all of them (point 6).
  - **DEC-009 point 8, "Added later, as an addition,"** comes to say that the declaration is the key `draws` in the drawing's own file (point 1).
  - **DEC-009's Implications, "A brand's own form is built later,"** come to say that [visual-communication:DEC-034-brand-drawings] decides the questions they list, and that the Tasks it names build it.
  - **DEC-009's top line** comes to read as below, for the reasons point 8 gives.
    > **Partially superseded by [visual-communication:DEC-034-brand-drawings].** Overturned: point 7's "Breaking, for a base", since a base that begins to serve a top breaks nothing. Also overturned: point 9's failure of a drawing of a layout of a top that the brand's base serves, which asks for attention instead. The rest stands.
  - **DEC-005 point 1, "A choice is declared, never computed,"** comes to add that a drawing of a layout may also choose by whether its instance is a page, read by `:as` (point 7).
  - **DEC-005 point 3, "Two sizes for each element,"** comes to add that a top with a physical size asks for its height through it, as point 3 of this record says.
  - **DEC-005 point 5, "A tree of groups,"** comes to say that a top declares its physical size under `physical-size`, in millimetres, and that the engine sets its height from the width asked for and the size's proportion. An export whose format has a physical page draws each page of the piece's top at that size, by one scale. **"The root says what the scene is"** comes to add the physical size of the piece's top (point 3).
  - **DEC-005 point 5, "Every element carries its trace,"** comes to add that an instance keeps its id under every drawing, that what a field shows takes the field's name, and that `:as` is a source of its own (points 5 and 7).
  - **DEC-005 point 9, "Each declares what it supports,"** comes to add that a renderer declares whether its format has a physical page, and whether it maps a top's physical size onto it (point 3).
  - **DEC-003 point 7's opening** comes to say that each library component but a drawing carries a status, since a drawing carries none (point 8).
  - **DEC-021 point 3, "Only a size axis a piece can name,"** comes to add that a drawing of a layout also reads `:as` (point 7). **Point 6** comes to add that a drawing of a layout also answers to whether its instance is a page. **Point 7's list of what fails** comes to except `:as` in a drawing of a layout from "a marked name that reads no size axis", and to add point 10's findings on `:as`. **Its Implications, "Left open,"** come to say that this record decides a brand's drawing at each key (point 6).
  - **DEC-022 point 3, "A page's height,"** comes to add that a brand's drawing writes its page's height in its own file, as a layout does (point 2). **"What a page gets"** comes to add that a top with a physical size asks for a height through it (point 3). **Its Implications, "Left open,"** come to say that this record decides how a brand's drawing of a site's layout writes its page's height.
- **The Tasks that build it,** each under [project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573), filed once this record is accepted. They take the five Tasks that the Feature's closure audit drafted, which [project-kit#2965](https://github.com/aleskalfas/project-kit/issues/2965) names: a brand draws a layout, the check judges a brand's drawings alone, a brand built on a base, a top's physical page size, and a poster end to end. Trace ids join the first Task, and a top a brand holds the third. A drawing's status and the release take a Task of their own, and so does `:as`. Each Task adds the findings of its own points to `checks.md`.
  - **A brand draws a layout of the deck, and a piece is drawn by that drawing where it fits.** It takes the audit's Task of a brand that draws a layout, with points 1, 2, 5 and 6. It builds `draws` and the drawing's file, with no status. It builds the choice of drawing for each instance in every language and at every key, with its fit and the facts a piece states (DEC-009 points 2, 5 and 6), and the failure of content that places a drawing. It also builds the size a drawing writes, the naming of a part that shows a field, on a top's own drawing too, and the drawing named in the instance's group. It changes `components.md` on a component's file, layouts, trace ids, what a scene holds and sources, `files.md` on a brand's version, `outputs.md` where a renderer marks the component that drew a page, `checks.md`, the component schema, the analysis's glossary with the term drawing, and UC-104, step 2, and UC-105, step 6, whose notes that this is not built yet it removes.
  - **The check judges a brand's drawings alone, and a brand's version states each top it serves.** It takes the audit's Task as drafted, after the first: the findings of DEC-009 point 9 and those DEC-011 and DEC-012 place on a brand's drawing, with the finding of a drawing of a top its base serves at attention. It changes `checks.md`, and UC-104, variant 4a, and UC-105, step 7, whose notes that this is not built yet it removes.
  - **A brand built on a base draws only the tops its base does not serve, and a top a brand holds is drawn by its own drawing.** It takes the audit's Task of a brand built on a base, after the first, with point 4. It changes `files.md` on open roles, on the lock and on a move onto another brand, `checks.md`, and UC-104 and UC-106, variant 2a of each, whose notes that this is not built yet it removes.
  - **The release reads a brand's components.** New, for point 8, after the first. It reads a component that becomes a drawing. It also compares a brand's other components as a component library's are compared, which DEC-003 point 7 already decides and the comparison does not do for a brand. It changes `files.md` on what a release compares.
  - **A top declares its physical size, and the exports map its pages onto it.** It takes the audit's Task of a top's physical page size, with point 3. It gives each renderer's declaration its answer, raises the seam's version, and raises the PDF renderer's. It changes `components.md` on a component's file, on layouts and on what a scene holds, `outputs.md` on the PDF renderer's pages, each renderer's unit and fixed pages, `files.md` on what a release compares, `checks.md`, the component schema, and the analysis's glossary with the term physical size.
  - **A drawing chooses by whether its instance is a page.** New, for point 7, after the first. It changes `components.md` on switches and sources, and `checks.md`.
  - **A project adds a poster, and its brand draws it.** It takes the audit's poster, after the Tasks of a drawing and of a physical size. A test project adds a poster to a library of its own, with its physical size, and a brand of its own draws its layout. A piece of it renders, checks and exports, and no file of the capability changes. UC-104 says what is built.
- **The pages take the examples this record leaves out,** each with the Task that builds what it shows, since the pages say what is built:
  - `components.md`, Layouts: the deck cover's drawing, and a title band drawn alike in two drawings (the first Task)
  - `components.md`, Trace ids: the id of what a field shows, and of a second part that shows it (the first Task)
  - `components.md`, A component's file: a poster's physical size, and a paper size given in inches (the Task of a physical size)
- **Read against this answer, and left as they stand:**
  - DEC-001 point 5, since a library may hold a top, and a physical size is the top's, which no brand gives a value.
  - DEC-003 points 3 and 6, since each change to the format is an addition, and a physical size changed in the same proportion is a change of how pages look.
  - DEC-004 point 1, since a drawing takes the format every component has, with the keys point 9 lists. Point 5, since this adds no way for a brand to break. Point 6, since a brand built on a base keeps the form of a top its base holds.
  - DEC-005 point 11, since the derivation of trace ids does not change.
  - DEC-010 point 5, since a page names its layout, never its drawing.
  - DEC-011 and DEC-012, since a drawing's fit to ends and runs holds as they decide, in each language and at each key.
  - DEC-013 points 3 and 6, since beginning to serve a top breaks nothing, so a brand the capability ships may do it within a major.
  - DEC-021 point 1, since a width stays a brand's value, and sets a printed page's scale.
  - DEC-025 point 8, since the command that moves a piece onto another brand reads the brand the piece names. A held top under another brand locks a second brand, as a part placed from a brand already does.
  - DEC-031 point 2, since a top with a physical size whose layouts are its pages' forms asks for a height through it, so its pages are fixed pages, and a poster that is a page alone is none.
- **Left open:**
  - whether a brand may name a brand other than its base, and so place that brand's parts
  - a physical size with bleed, and a top offered at several physical sizes
  - a frame around the top's own drawing, as a kind of drawing of its own
