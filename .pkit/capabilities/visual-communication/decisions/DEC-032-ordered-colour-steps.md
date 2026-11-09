---
id: DEC-032
title: An order's places take colour steps, spread evenly between two ends each brand gives
status: proposed
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand gives an order two colours in each of its modes, one end for the order's source and one for its last place, and one text colour for every step. Where the content chooses a pattern's word for an order, every place of the list takes a step. The first place takes the source's end, the last place the other end, and the places between are spread evenly. So an order of three and an order of eight both run from one end to the other. The source's end stands out most from the page, so in a dark mode it is the lighter end, not the darker. The text holds the contrast body text needs on both ends, and the check measures each step as drawn. In a long order, neighbouring steps come close, and the check asks the author to look. A step shows where an item stands in an order, so no concept, component or state names one. An item that names a concept keeps its step as its fill, and its concept's colour becomes the line around it. That line is then the item's only colour mark, so it must stand 3 to 1 from what lies beside it, and a brand whose lines are faint fails such an item. Making the steps the default of a pattern already released breaks that pattern. A brand that gives no ends draws every step in its neutral colour. The neutral brand's ends take its text colour's hue.

## Context

The record of brands and notations has the foundations declare the colour families a notation maps its concepts to ([visual-communication:DEC-004-brands-and-notations] point 10). Each family is a fill, a line and a text on the fill. There are six: a neutral one and five hues. Each family's text on its fill is a pair that must reach WCAG's level for text, in every combination of the modes (point 8).

How an item takes its colour is decided ([visual-communication:DEC-001-visual-communication-discipline] point 6):
- **From the concept it names,** read with its notation.
- **Else from a default:** the pattern's for the item's place, else its item component's, else that of the component it sits in.
- **A state may change it,** and content may point one part at another role.

The record of a list's fields says how a place takes its colour ([visual-communication:DEC-010-list-item-fields] point 6):
- **A place** is an item's position among the items its list draws.
- **A pattern may give each place a family of its own,** in its data, and may switch those families on an option. A pyramid with no notation shades its levels so.
- **A place past those the pattern names** takes no family from the pattern, and goes on to its item component's.
- **That record rejected roles named by a place,** whose names would be computed from it, since every role a component reads is written in its file (DEC-010, Alternatives considered).

A scene names a role for each colour it holds, and takes each role's value from the engine's document of a brand's resolved values. So one scene serves every mode of the value axes ([visual-communication:DEC-005-engine-and-plugins] points 5 and 7). An HTML page paints each colour role with a custom property, whose value changes with the mode ([visual-communication:DEC-023-html-page-modes] point 3).

What is missing for an order is a family that steps. Each family is one colour for one kind. No brand can give a ramp of one hue without taking the families notations map their concepts to. The engine draws one family for a whole list today. The starter lists a colour for each place among what it lacks ([project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576)).

The redesign of the showcase deck of the repository the capability is authored in needs it ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)). Its first page stacks five levels, from decisions down to code, and its lead says each level carries out the ones above it. In the seventh round of the redesign's drafts, which its critic passed:
- **The levels step in one ramp,** darkest at the source in light mode and lightest at the source in dark mode. They name no concept.
- **One text colour on every step** of a mode, the page's own background. White holds 5.06 to 1 on the lightest light step, and 14.5 on the darkest.
- **The lightness steps evenly,** in OKLCH from .28 to .54 in light mode and from .90 to .64 in dark mode, at one chroma. Its hue is that of the slate the round gives its text.
- **The design's reason:** lightness is the ordered variable, and a ramp of one hue says "one chain". The deck's one accent then keeps its one meaning.
- **Order and a highlight never cross.** Order is only ever a block's fill. A highlight is only ever a line, a word or a tint region.

The principles of visual communication are accepted as two rule sets ([visual-communication:DEC-028-principles-of-visual-communication]). Their rule that the form says what the content says, RS-GRAPHIC-007, asks that a picture's differences be those its content has. On a page whose point is an order, the parts that show the order share one colour, or step in one shade. Each concept an item names keeps its colour on a mark of its own. That record leaves colour roles that step in an order to a later refinement of the record of brands and notations (DEC-028 point 11).

Two rules bound how shared roles are added:
- **The foundations are released,** so a shared role added now carries a default that aliases an older role (DEC-004 point 7, [visual-communication:DEC-008-library-role-defaults] point 2).
- **A new top group of the shared roles** is a breaking change of the foundations, even where each of its roles has a default (DEC-004 point 5).

Six terms:
- An *order* is a list whose items stand in a sequence the content means. Examples are levels that each rest on the next, and the steps of a flow.
- Its *source* is the end it runs from, such as the level every other carries out, or a flow's first step.
- A *page whose point is an order* is a page that is there mainly to show the order its items stand in.
- The *families of kinds* are the colour families a notation maps a concept to.
- An order's *ends* are the two colours a brand gives it in each combination of its modes. The *source's end* is the one the first place takes, and the *last end* the one the last place takes.
- A *step* is the colour family a place of an order takes, spread from the ends.

## Decision

**The foundations declare an order's two ends and its text, three shared colour roles beside the colour families. A brand gives them values in every combination of its modes. A pattern may give a list's places the steps of an order, under a word of an option. The engine then spreads the ends evenly in Oklab over the places the list draws: the first place takes the source's end, and the last place the last end. Each step is a family, whose fill and line are its colour and whose text is the order's text. A brand's check holds that text at WCAG's level for text on both ends, and on one side of both. It also holds the source's end at least as far from the background as the last end. A piece's check measures each step as drawn, and asks for attention where neighbouring steps come too close. On a step, an item that names a concept keeps the step as its fill, and takes its concept's colour as its line. The roles default to the neutral family, and the neutral brand's ends take its text colour's hue.**

### 1. Two ends and a text, each a shared colour role

- **Three roles.** The foundations declare `family.order.first`, the source's end, `family.order.last`, the last end, and `family.order.text`, the text on every step. Each is a shared colour role, to which a brand gives a value in every combination of its modes.
- **The ends declared, never read from a name.** The foundations declare, as data, which role is the source's end and which the last end. The engine and the checks read the ends from that declaration, never from a name.
- **In the group of the families.** The roles lie in the top group that holds every family's roles, so they add no top group (DEC-004 point 5). No library or brand holds a role of its own there, since each lies under a group named after its library, and no library takes a top group's name (DEC-004 point 7). A base that opens the whole group of the families to brands built on it opens the roles of an order too, as it opens any role the foundations add there (DEC-004 point 6).
- **Apart from the families of kinds.** The foundations declare the order's roles apart from the families, and no family is named `order`. So no concept can map to them (point 5).
- **Public names.** A brand exports the three roles as it exports every shared role (DEC-004 point 5). The steps between the ends are no role, and no brand exports them.
- **The neutral family marked.** The foundations mark the family of kinds that shows no hue, as they declare the ends. The engine and the checks read it from that mark, never from its name (point 6).

### 2. What a brand gives, and the contrast the text holds

- **A value for each role,** in every combination of its modes, as for every shared role. A role a brand leaves out takes its default, which rarely holds against the values the brand gives. A brand that gives the ends and not the text then fails the text's pairs.
- **A default where it gives none.** Both ends default to the neutral family's fill, `family.neutral.fill`, and the text to its text, `family.neutral.text`. So every brand released before the roles still draws, and draws every step alike, as its neutral family.
- **The text on both ends, at WCAG's level for text.** The foundations declare the order's text on each end as a pair at the level `text`, 4.5 to 1 (WCAG 1.4.3). Each is checked in every combination of the axes that change a colour, as every pair is (DEC-004 point 8). At the defaults, both pairs fall on the neutral family's own, which every brand already holds.
- **The text on one side of both ends.** In every combination, the order's text is lighter than both ends, or darker than both. A ramp from one side of the text to the other would pass through the text's own colour, and fail at some step between.
- **Each step measured as drawn.** Which steps a piece draws is known only from its lists, so a brand's check holds the ends alone. A piece's check measures each text on a step against that step as drawn, in every combination the piece is drawn in, as it measures every text (DEC-004 point 8).
- **A step may be dark in a light mode,** where every other family's fill is pale, and the order's text pale. A part that an item component paints in a fixed role over its family's fill may then fail on a step. So may the reverse: a part painted in its family's text over a fill in a fixed role, such as a card's text on the surface. The contrast as drawn finds both.
- **No pair of an end against the background.** No family carries one, and a step is a family. The order never rests on its shade alone (point 4). So a step is not a graphic a reader needs to understand the order, which WCAG 1.4.11 asks 3 to 1 of. A brand may still hold its ends far from the background, as the neutral brand's stand 4.5 to 1 from it (point 8).

### 3. The source stands out most, in every mode

- **Measured against the background.** The source's end contrasts with the page's background, a shared role, at least as much as the last end does. That holds in every combination of the axes that change a colour, by WCAG's ratio, as the pairs measure it. Between ends of one hue and chroma, the steps between lie between the ends in that ratio too. So where both ends lie on one side of the background, the first place stands furthest from the page, and the last place nearest.
- **So a dark mode gives its ends the other way round.** On a light background the source's end is the darker. On a dark one it is the lighter. A brand gives each mode its own ends. It never inverts one mode's for another, which would sink the source into a dark page.
- **Equal ends pass.** A brand may give both ends one colour, as its defaults do, or as a mode of high contrast might. Every step is then alike, and the order shows by its other signs alone (point 4).
- **A background of a middle tone** may lie between the ends. The rule still holds, though a step between then comes near the page, and the brand judges the look.
- **Against the background alone.** Nothing is promised against another fill an order may lie on, such as a surface.

### 4. A pattern may give an order's places their steps, spread over the list

- **Under a word of an option.** A pattern may offer the steps under a word of an option it declares, which switches its places' families (DEC-010 point 6). The content chooses that word where the page's point is the order. A pattern's owner may make it the option's default, where the pattern's job is an order, which breaks a pattern already released (point 10). Content then chooses another word where its point is elsewhere.
- **Spread evenly over the list.** Under that word, every place of the list takes a step. In a list that draws n places, place k takes the colour (k − 1) / (n − 1) of the way from the source's end to the last end. So the first place takes the source's end, the last place the last end, and the places between are spread evenly. A list of one place takes the source's end.
- **Evenly in Oklab.** The spread runs along the straight line between the two ends in Oklab, the colour space whose cylindrical form is OKLCH. So the lightness steps evenly. Between ends of one hue and chroma, only OKLCH's lightness changes.
- **Within the range of the ends.** Where a step falls outside the range of colours its ends are given in, the engine brings it in as CSS Color 4's gamut mapping does, lowering its chroma in OKLCH at its lightness and hue.
- **Alpha and rounding fixed.** Where an end has alpha, the spread premultiplies it, as CSS Color 4 interpolates. The engine rounds each step to a fixed precision, so the same files give the same steps on every machine (DEC-005 point 5).
- **In each combination apart.** The engine spreads each combination's own ends, at the scene's size. A place takes the same share of the way in every combination.
- **Each step is a family.** A step's `fill` and `line` are its colour, and its `text` is the order's text. An item component paints a step with the members it paints any family with. So a part that marks an item from its family's line, such as a card's bar, shows the step. A mark a component paints from its line on its own fill does not show on a step.
- **Every item counts, and nothing else is given.** Every item the list draws takes its place's step, an item that names its own component included, such as a note that ends a row. Content that ends an order with something outside it places that outside the list. A place counts from the first item the list draws (DEC-010 point 6), so the content lists the source first. A pattern names no role of an order, and under the word that gives the steps, it names no family for any place of that list.
- **It shows where the item paints from its family.** An item component may paint its fill in a fixed role, such as a card on the surface. It then shows the step only in the parts it paints from its family, such as the card's bar. Where no part an item draws takes a member of its step, the check asks the piece's author for attention. A pattern that offers the steps names a default item component that paints its fill from its family, and its line apart from that fill (point 6). Its option chooses only its places' families, never the item's look, which is the item component's (DEC-001 point 6). So that default holds under every word. No check judges that choice, and a line drawn on its fill fails at the piece (point 6).
- **One list, never ties.** A word gives the steps to the places of one list the pattern repeats. A list of ties takes none, since a tie stands in no order ([visual-communication:DEC-011-tie-ends]).
- **Never the order's only sign.** A pattern that shades by place also shows the order by position, and by size, numbers or arrows where its form has them. Shades collapse under forced colours, and on a projector that washes them out.

### 5. A step reaches an item only through a place, or where the content points a part at a role of an order

- **A step shows where an item stands in an order,** as a place's family does when a pyramid with no notation shades its levels (DEC-001, Rationale). It never says what a thing is, or what state it is in. Named in a structure, it would become one more colour of a palette, in every brand.
- **What names one of the families of kinds names no role of an order:** a notation's concept, a component's own default family, a state's family and a pattern's family for a place. Such a name is refused, as any name that is no such family is.
- **What takes either.** A place takes one of the families of kinds, which its pattern names, or a step, which its pattern's word gives. A paint from the item's family paints from either.
- **Never by its name in a structure.** A part of a component never paints with a role of an order by its name. No library's own role, and no component token, aliases one as its default.
- **A brand's aliases run either way.** A brand may give a role of an order an alias to another of its tokens, or give another role an alias to one of them. Its values are its own. A role means what the structure that reads it says, wherever its value comes from.
- **Content may point a part at a role of an order,** as it may point a part at any role (DEC-001 point 6), such as a legend's swatch of the source's end. Its author then says that the part shows a place. The steps between the ends are no role, so content points at none of them.

### 6. On a step, an item's concept gives only its line

- **The step fills the item, and its concept outlines it.** Where an item's place takes a step and the item names a concept, the members `fill` and `text` resolve to the step's, and `line` to the concept's. Each part takes the member it paints with, and is measured as drawn. This rests on a component keeping `line` for its lines and marks, as each family paints one thing: its line, its fill and the text on it.
- **A concept of the neutral family gives nothing on a step.** That family marks no kind by a hue, so the item takes the step whole.
- **The text stays the order's,** since the order's text holds on both ends (point 2). A run that names a concept still takes its concept's family, measured as drawn on the step, as on any fill not its family's own ([visual-communication:DEC-012-text-runs] point 3). Its concept's text is tuned for its own family's fill, so such a run mostly fails on a step, and its author drops the run's concept or chooses no steps.
- **The line stands 3 to 1 from each colour beside it.** It is the item's only colour sign of its concept, a mark that is not text, so WCAG 1.4.11 asks 3 to 1 of it against the colours beside it. The check measures it as drawn, against each fill it borders, in every combination the piece is drawn in, as it measures a drawn text (DEC-004 point 8). No line of a hue holds 3 to 1 on every step, so the default item component draws its line apart from its fill (point 4). Only what the item lies on then lies beside the line. So here a family's `line` does more than edge a fill: a brand whose hues' lines are faint against its page fails such an item, and the finding names the brand's owner too.
- **Where no part the item draws takes its concept's line,** or none takes the step's fill or text, the check asks the piece's author for attention, for a concept of a hue. An item component with no line, or a fixed fill, may cause it, and so may content that points a part at another role. The author may name another item component, or draw the list unshaded.
- **Only a step splits an item's family so.** A place that gives one of the families of kinds still yields to the item's concept (DEC-001 point 6, DEC-010 point 6). A state its component gives a family still replaces both (DEC-001 point 6), and each run's family too (DEC-012 point 3). An outer item passes the step whole to what sits in it, where nothing nearer gives a family (DEC-010 point 6), and keeps its concept's line as its own mark.
- **Point 5 holds.** The step reaches the item through its place, and the line comes from one of the families of kinds. No concept names a role of an order.

### 7. A long order asks for attention where neighbouring steps come close

- **Neighbours come closer as places are added.** The ends stay where the brand set them, so each place added brings every two neighbouring steps closer.
- **Attention below 1.15 to 1.** Where two neighbouring places' steps, as drawn, stand less than 1.15 to 1 apart in some combination, the check asks the piece's author for attention. The author may split the list, or draw it unshaded.
- **Measured as drawn,** by WCAG's ratio between the two steps' fills, whether or not the items touch.
- **Ends alike ask nothing.** Where a brand gives both ends one colour in a combination, its steps are meant alike there (point 3).
- **Never a failure.** The order still shows by position, and by size, numbers or arrows where its form has them (point 4).

### 8. What the neutral brand gives

The neutral brand stays a brand to start from, so its ends carry no project's identity (COR-014; DEC-001 point 9).
- **One hue, its text colour's own.** Both ends take it, so the steps read as one chain, a deepening of the text, and claim no kind. Where the text colour has no hue, as a pure grey, the steps have none either.
- **Apart from the accent.** An end never takes the accent's colour. Where the text colour's hue lies near the accent's, the ends stay far below the accent's chroma, so the accent keeps its one meaning.
- **The order's text is the background's own colour.** So an end whose text holds 4.5 to 1 stands 4.5 to 1 from the background as well.
- **Each hue's line at 3 to 1 from the background,** in every combination, so a concept's line on a step holds where the item lies on the page (point 6).

### 9. What the checks report, and how severely

Each finding below lies where the record of files and validation puts it. It fails or asks for attention by that record's policy ([visual-communication:DEC-002-files-and-validation] point 7).
- **Fails validation:**
  - in a brand: the order's text below WCAG's level for text on an end, in some combination, as every declared pair below its contrast fails (DEC-004 point 11);
  - in a brand: the order's text lighter than one end and darker than the other, in some combination;
  - in a brand: a last end that contrasts with the background more than the source's end, in some combination;
  - at a piece's lock: a list given the steps under foundations that do not declare the roles of an order, where the piece's content chose the word or a person moved the lock there, as a fault only a combination of versions shows fails at the lock that combines them (DEC-002 point 7);
  - in a notation, a component, a state or a pattern's family for a place: a role of an order where one of the families of kinds is named, as any name that is no such family is refused;
  - in a component: a part that paints with a role of an order by its name, or a component token whose default is one;
  - in a library's roles: an own role whose default is a role of an order;
  - in a pattern: a word that gives a list the steps and names a family for some place of it;
  - at a piece: a concept's line on a step that stands less than 3 to 1 from a colour beside it, as drawn, in some combination, as a drawn text below its level fails (DEC-004 point 11). The finding also names the brand's owner.
- **Already failing:** a text on a step below its level as drawn, as every drawn text below its contrast fails (DEC-004 point 11).
- **Asks the piece's author for attention:**
  - two neighbouring places of an order whose steps, as drawn, stand less than 1.15 to 1 apart in some combination where the ends differ (point 7);
  - an item on a step where no part it draws takes a member of its step (point 4);
  - an item on a step that names a concept of a hue, where no part it draws takes its concept's line, or none takes the step's fill or text.

### 10. The engine spreads the steps, their values come with the scene, and what breaks

- **The engine gains one general tool,** the spread of point 4, built and tested once in the capability (DEC-001 point 4). It is the one colour the engine computes from a place. Where a concept meets a step, the engine takes the item's line from one family and the rest from another, and the check measures that line as drawn (point 6).
- **The scene names a step's roles.** In the scene, a step's colour names the two roles it is spread between and its place's share of the way, the same in every mode. A drawn step traces back to the two ends and its place ([visual-communication:DEC-005-engine-and-plugins] point 5).
- **Its values come with the scene.** The engine computes a step's value in each combination named from those roles' values, at the scene's size. It hands them with the values of every combination named, which come with each scene (DEC-005 point 6). So one scene still serves every mode, and no renderer spreads. The check measures the same values.
- **The document of values holds no step.** The document of a brand's resolved values is unchanged (DEC-005 point 7), so no code writer writes a step out.
- **The seam's version rises,** since a renderer must read the new kind of value (DEC-005 point 8).
- **Breaking, for a pattern already released:** a release that makes the steps the default for one of its lists, by a new option or by a changed default. A draft that moves into it could newly fail a concept's line (point 6), on a change its project never made. A pattern whose first release gives the steps by default breaks nothing.
- **A draft holds a pattern back.** Versions under which a pattern gives a list the steps by its default, and the foundations do not declare the roles of an order, do not fit together for a piece. So a draft does not move into them ([visual-communication:DEC-003-change-over-time] point 8). Where the piece's content chose the word, or a person moved its lock there, the check fails it at the lock (point 9).

### 11. What this adds to the libraries and the format, and what still holds

- **The foundations gain three shared roles, each with a default,** and the declaration of the ends, apart from the families of kinds. A role with a default breaks nothing (DEC-004 point 5), so the foundations take a minor version ([visual-communication:DEC-013-shipped-library-releases] point 3).
- **The format grows by an addition** that every file written before still meets (DEC-003 point 3). The schema of a library's roles gains the declaration of the ends and the neutral family's mark, which only the foundations hold, as only they declare families. The schema of a pattern gains a word that gives a list the steps.
- **Every brand draws every piece as before.** A piece meets the steps only where a pattern gives them to a list. Under a brand that gives no ends, every place there draws as the neutral family, and an item there that names a concept of a hue takes its concept's line.
- **No file is renamed or removed,** and no project file changes shape, so no migration is owed (COR-010).

## Rationale

**Why an order takes steps of its own, apart from the families of kinds.** Jacques Bertin's visual variables tell the two apart (*Sémiologie graphique*, 1967). Hue is selective: the eye splits items of five hues into five groups. Lightness is ordered: the eye reads five lightnesses as a sequence. Jock Mackinlay's expressiveness asks that a picture show the facts of its data and no others (1986). An order drawn in five hues shows five kinds and no sequence. Kept apart, a step never says a kind, and a concept never says a place.

**Why the steps work from the data.**
- **Every order spans the whole ramp.** The source always takes the end that stands out most, and the last place the other end, whatever the list's length. A short order is not drawn in the ramp's strongest end alone, and a long one never runs out of steps.
- **A sequential scheme fits its count.** ColorBrewer's sequential schemes pick their colours again for each number of classes (Cynthia Brewer), so a class's colour depends on the count, as a place's does here. They also widen their range as the classes grow. Here the brand fixes the range, so neighbours come closer instead, which point 7 watches.
- **The cost, accepted.** A place's colour depends on the list's length, so the second item of a short list looks different from the second item of a long one. A page whose point is an order shows its places against each other, within one order. Two orders still compare place by place, by position and numbers.

**Why two ends for each mode.**
- **The least a ramp needs.** Two colours fix where a ramp starts and ends, so which step stands out most, and how near the page the last one comes. The brand chooses both, in each mode.
- **The middle needs no tuning.** An even spread in a space whose lightness the eye sees evenly gives near-equal steps. A set of stops would be three times the colours to tune, for a middle no page needed.
- **One colour is too few.** A ramp derived from one colour leaves its other end to the tool. Nobody then chooses the light end, and the derived end can fail its text.

**Why the engine computes the steps between.** Only a brand holds a raw value (DEC-001 point 5), and the ends are the brand's. The engine computes the scene from the libraries (DEC-001 point 2), and a need that recurs becomes a general tool of the engine, built and tested once (DEC-001 point 4). The spread is one fixed rule, so a brand's owner knows every step its ends give, at any count. A renderer adds no colour of its own (DEC-001 point 2), so the engine spreads, and every medium draws the same steps, the ones the check measured.

**Why a step's values come with the scene, and the document of values holds none.** The document of a brand's resolved values holds the brand's tokens, and a code writer writes it out (DEC-005 point 7). A step is no token, and which steps a piece draws depends on its lists. So the engine computes each step's value for the piece, and hands it with the values that come with each scene, as it hands each role's (DEC-005 point 6). The scene names the two roles and the share, the same in every mode, so a step traces back to the brand, and a change of the brand's values changes no scene.

**Why a default of the steps breaks a released pattern.** A change of how something looks does not break, since a lock and its before-and-after protect each piece (DEC-003 point 6). A draft, though, moves into each release at its next render (DEC-003 point 8). Under the steps, a concept's line is measured against what lies beside it (point 6), so a draft that drew well could newly fail, on a release that a change of look alone would let in. The record of a list's fields refused a release that fails a piece its project did not change (DEC-010, Alternatives considered). Counted as breaking, the steps by default come only with a new major, which a person takes on purpose.

**Why the ends and the neutral family are declared, not read from names.** The engine and the checks act on which end is the source, and on which family has no hue. A name is a word for readers, and the naming rule gives a name no rank or hue (DEC-004 point 4). So each is a fact the foundations declare, and no rule rests on a word.

**Why Oklab.**
- **Even to the eye.** Oklab spaces lightness close to how the eye sees it (Björn Ottosson, 2020), so equal steps of it look near-equal. Equal steps of sRGB's values do not.
- **One rule for any two ends.** A straight line needs no rule for hue, which OKLCH would need between two hues, and which a grey lacks. Between ends of one hue and chroma, it steps OKLCH's lightness alone, as the redesign's ramp does. Between two far hues its middle loses chroma, which the brand sees in its own steps.

**Why a list of one takes the source's end.** A list of one is its own source. The first place takes the source's end in every list, so a list that grows from one keeps its first item's colour.

**Why one text on every step.** A text that differed from step to step would add a difference the order lacks. One role is one value a brand tunes in each mode.

**Why a brand's check holds the ends, and a piece's each step.** A brand cannot know how many places its pieces draw, so its check holds what every order shares: its two ends, and the text on one side of both. Between ends of one hue and chroma, that holds the text on every step between. A piece's lists are known, so its check measures each step as drawn, as it measures every text (DEC-004 point 8). So a step that fails between two ends that pass, such as between two far hues, is found where it is drawn.

**Why the text lies on one side of both ends.** A text that holds 4.5 to 1 on both ends can lie between them only as a middle grey, between a near-black end and a near-white one. A ramp between such ends passes through the text's colour, so some step fails at almost every count. Refused in the brand, that fault is its owner's to mend, not each piece's.

**Why measured from the background.** What makes a step stand out is its distance from the page, not its darkness.
- **Material's colour roles** take one tone of a tonal palette in a light scheme and another in a dark one. Its primary colour is tone 40 in light and tone 80 in dark, so the role keeps its emphasis in both. Its surface containers, from low to highest, step away from the surface's tone in both schemes. In light they darken from tone 96 to 90, and in dark they lighten from 10 to 22.
- **One rule on the distance from the background** holds in each mode, high contrast included, with no rule for each scheme. An inverted ramp would put the darkest end at the source on a dark page, where it stands out least.

**Why a long order asks for attention, at 1.15 to 1.**
- **A reading of taste.** WCAG asks no contrast between two fills that each carry their own text and a second sign of their place. A level that no record makes an invariant asks for attention, never fails (DEC-002 point 7).
- **What the level lets pass.** At the lightness the neutral brand's ends start from (Implications), neighbouring steps stand 1.26 to 1.33 to 1 apart in an order of five places in light mode, 1.17 to 1.21 in seven, and 1.12 to 1.16 in nine. In dark mode, where the lighter colours stand closer by WCAG's ratio, they stand 1.23 to 1.29 in five, 1.15 to 1.18 in seven, and 1.11 to 1.14 in nine. So an order of up to six places passes in both modes, the redesign's five levels among them, and one of seven in light mode alone.
- **WCAG's ratio, as every contrast here.** The capability's checks measure contrast by one ratio. The ratio narrows among light colours, so a dark mode asks from fewer places than a light one.
- **The order still shows.** Position, and numbers or arrows where its form has them, carry the order (point 4). So a long order is no failure, and its author may split it, or draw it unshaded.
- **Ends alike are chosen.** A brand that gives both ends one colour, or gives none, draws every step alike on purpose, so the check asks nothing of it.

**Why the defaults are the neutral family.** A default is the fairest stand-in until a brand gives a value (DEC-008 point 2). The neutral family is the starter's own default for its blocks. So a brand that gives no ends draws an order's places in a family it already tuned. That adds no difference its owner never chose. Its pairs already hold, and the order shows by position.

**Why a text pair, and no pair of an end against the background.** WCAG 1.4.3 asks 4.5 to 1 of body text on what lies under it, and an item's text lies on its step. WCAG 1.4.11 asks 3 to 1 of a graphic a reader needs to understand the content, against the colours beside it. An order's shade is a second sign of what position already shows, so it is no such graphic. No family carries such a pair, and the neutral family's quiet fill would fail one at the defaults.

**Why only a place takes a step.** A notation's concept, a component's own family and a state each say what a thing is, or how it stands. A step among them would show a place in an order where there is none. A role of an order that a component or a library's role names becomes one more colour of a palette, and the steps stop meaning an order. The content may point a part at one, since there its author places the part.

**Why, on a step, the concept takes the line.** Each of the other two ways loses one of the item's two facts.
- **The concept's fill breaks the order.** One item of the chain would take its concept's hue, a difference on the very chain the page is about. On such a page, the rule that the form says what the content says asks that the parts that show the order take no concept's hue (RS-GRAPHIC-007).
- **The step alone leaves the item unmarked.** A concept's colour is its only mark today, since format 1 draws no concept's icon (DEC-012, Context).
- **Each part carries one variable.** The fill carries the place by its lightness, Bertin's ordered variable. The line carries the kind by its hue, his selective one. The redesign's seventh round keeps the same split on every page, and RS-GRAPHIC-007 has each concept keep its colour on a mark of its own.
- **The text stays the order's,** since a concept's text is tuned for its family's own fill, and would fail its pair on a step.
- **A state may still fill the item.** A state is a difference the content has, and its look is its component's (DEC-001 point 6). Today a state's look is a family, so a state on a step leaves the chain's shade. A state's look other than a family, such as a line, is left to a later change.

**Why a neutral concept gives nothing on a step, and an outer item passes the step whole.** A neutral concept's line is a quiet rule, 1.4 to 1 from a light page in the neutral brand, and marks no kind by a hue. At the defaults, where the step is the neutral family too, the item then looks as it would with its concept first, and meets no new finding. What sits in an item lies on the step, where no line of a hue holds 3 to 1. A concept's line passed to it would fail where nothing is wrong, since the outer item's line already marks the concept.

**Why a family's line carries a promise on a step.** Elsewhere a family's line is its fill's edge, which a brand may draw faint. On a step it is a concept's only colour, so the record holds it to 3 to 1 where it is drawn, and the neutral brand to 3 to 1 for each hue's line. A brand with faint lines still draws every other piece as before.

**Why the line is measured against each colour beside it.** WCAG 1.4.11 asks 3 to 1 against the colours beside a mark, and a step cannot hold it. In a light mode a step is about as dark as a line. The neutral brand's lines of the five hues stand 1.0 to 2.6 to 1 from the seventh round's ramp, in both modes, and 5.7 to 8.0 to 1 from its pages. So the default item component draws the line apart from its fill, as the round's picture does, leaving the page on both its sides. Where items touch, or a component draws the line on its fill, the check finds it.

**Why measured as drawn, and not as a pair.** A pair of a family's line against the background judges a brand, but not what a line borders where it is drawn: the step, or the next item where items touch. It would also bind every family's line where it marks nothing. Only a drawing shows where a concept's line is an item's only mark, and what lies beside it.

**Why a missing line asks for attention, and does not fail.** WCAG 1.4.11 binds a mark that is drawn, so a weak line fails as a weak text does. Whether a concept is marked at all is a judgement the rule sets give a reviewer, in their rule that the same meaning looks the same (RS-GRAPHIC-004). Its author may mark the concept another way, or choose no steps. The check names the item, as it names a long order.

**Why the neutral brand's ends follow these principles.**
- **One hue.** Cynthia Brewer's single-hue sequential schemes step lightness in one hue, so the eye reads a sequence and no kinds.
- **The text colour's hue** reads as a deepening of the text, not as a brand's colour, so the neutral brand stays one to start from. Kept far below the accent's chroma, the steps leave the accent its one job.
- **The text in the background's colour** makes the pair and the distance from the page one measure. An end whose text holds 4.5 to 1 stands 4.5 to 1 from the page.
- **Why on the neutral brand alone.** Where one hue ends and another starts is a judgement no check makes. So the foundations do not hold a brand's ends off its accent, and a reviewer judges it.

**Why in the group of the families, and why defaults.** A new shared role needs a default, or a major release that every library and brand moves to on purpose (DEC-004 points 5 and 7). A new top group is a breaking change even with defaults. The group of the families exists, and a step is a family.

### Alternatives considered

- **A full set of stops for each mode,** such as five colours a brand tunes, which the steps take or spread between. Rejected. It is three times the colours to tune, for a middle no page needed.
- **One colour a brand gives, from which the engine derives the rest,** lighter and darker in OKLCH. Rejected. Nobody chooses the light end, and the derived end can fail its text.
- **Five fixed steps, the same for every brand, one to each place from the first.** Rejected. A short order takes only the ramp's strongest end, and a place past the fifth takes no step. Each step is three more colours a brand tunes. What it gains, a place drawn alike in every order, serves a comparison across orders that a page whose point is one order does not make.
- **Steps spread in OKLCH, its hue taken along the shorter arc.** Not chosen. Between ends of one hue and chroma it gives Oklab's steps. Elsewhere it needs a rule for hue, which a grey lacks.
- **Steps spread in sRGB's values.** Rejected. Equal steps of them do not look equal.
- **A ramp for each of the families of kinds,** as Material keeps a tonal palette for each key colour. Not chosen. Each of six families would need its own ends, and a page whose point is an order needs its order shown, not its kinds.
- **Steps of a pattern's own library,** such as the starter's. Rejected. Each library that draws an order would declare its own. A brand gives them values only where it names that library (DEC-008 point 4). A meaning every library needs is a shared role's (DEC-008 point 2).
- **The roles under a top group of their own,** such as `order.first`. Rejected. A new top group is a breaking change of the foundations (DEC-004 point 5).
- **No defaults, in a major release of the foundations.** Rejected. Every brand would give three values in every combination before it read the new major, and every lock would move on purpose.
- **Defaults that alias the text colour and the background,** a solid block in the text's colour. Rejected. A brand that never chose it would draw an order as heavy blocks, an emphasis its owner never chose.
- **A pair of each end against the background, at 3 to 1.** Rejected in the foundations (Rationale, "Why a text pair, and no pair of an end against the background"). The neutral brand's ends stand further from it by its own principle (point 8).
- **Neighbouring steps below the level fail validation.** Not chosen. The level is a reading of taste, and the order still shows by its other signs (Rationale, "Why a long order asks for attention").
- **No check of neighbouring steps.** Not chosen. A long order's steps would blur with no one told.
- **Neighbouring steps measured by their distance in Oklab.** Not chosen. It would ask at the same count in both modes, where WCAG's ratio asks earlier in a dark one. The capability measures every contrast by WCAG's ratio, so one measure judges them all.
- **A step's line in the order's text.** Rejected. A card's bar on the surface would take the order's text, pale in a light mode, and the step would show nowhere on the card.
- **The steps in the document of a brand's resolved values.** Rejected. A code writer writes that document out, so the steps of one piece's lists would leave the capability as a brand's code (DEC-005 point 7).
- **Each step's value in each mode held in the scene itself.** Not chosen. A renderer would take colours by two routes, and a change of a brand's values would change a scene, for its steps alone.
- **The steps as a pattern's default, breaking nothing.** Rejected. A draft could newly fail on a release that changed only a look (Rationale, "Why a default of the steps breaks a released pattern").
- **The concept's whole colour before the step,** as a place that gives a family of kinds yields to it. Rejected. One item of the chain would take its concept's fill, and the order would break where it stands (Rationale, "Why, on a step, the concept takes the line").
- **The step alone, with the concept unmarked.** Rejected. The item would lose its concept's only mark today.
- **The concept's colour on the item's text.** Rejected. A concept's text, tuned for its family's own fill, would fail its pair on a step.
- **The line measured against what the item lies on alone.** Rejected. A line drawn on the step would pass, and be lost against it.
- **A pair of each family's line against the background, at 3 to 1, or of each hue's.** Rejected (Rationale, "Why measured as drawn, and not as a pair").
- **A neutral concept's line drawn on a step,** or exempt from the check. Rejected. It would mark no kind, and either fail where nothing is wrong or stand unjudged.
- **Content points each item's parts at its step,** with no family for each place. Rejected. The steps between the ends are no role, and an item inserted would leave every later one on the wrong colour.
- **The roles of an order as a component's own family, or a state's,** such as a block drawn solid in the source's end. Rejected. The step would show a place in an order where there is none, and become a palette's colour.
- **The engine tells whether a page's point is an order.** Rejected. It cannot, so the content chooses it by a word.
- **A renderer spreads the steps,** such as an HTML page that mixes the two ends' properties in Oklab in CSS. Rejected. A renderer adds no colour of its own (DEC-001 point 2). A browser brings a step outside the range back its own way, so a page could draw a colour other than the one the check measured, and a medium with no such mix would still need the values.

## Implications

- **Edits to accepted records,** made once a person accepts this record, in the change that proposes it. Accepting this record accepts them ([COR-066](../../../decisions/core/COR-066-accepted-before-landing.md) point 5). Each edit ends with a pointer to this record and the point it names, in the form the accepted records use.
  - **The founding record's point 6** gains a bullet: "An order's steps are colour families the engine spreads over a list's places, from two ends a brand gives. No concept, component or state names one, and no part of a component names a role of an order" (point 5). **Its bullet "Colour says what a thing is"** gains, after its sentence on a default: "Where an item names a concept of a hue and its place takes a step of an order, its members `fill` and `text` take the step's, and `line` its concept's" (point 6).
  - **The record of brands and notations' point 7** gains, beside its bullet on a component token's default: "No component token's default aliases a role of an order" (point 5).
  - **Its point 8** gains a bullet: "An order's text on each of its two ends is a declared pair, and the text is lighter than both ends or darker than both. In every combination, the source's end stands at least as far from the background as the last end" (points 2 and 3). **Its bullet "Checked as drawn"** gains: "It also measures a concept's line on an item that takes a step of an order against each colour beside it, at WCAG's level for other marks" (point 6).
  - **Its point 10** gains a bullet: "The foundations also declare an order's two ends and its text, apart from the families a notation maps to, and mark the family that shows no hue. A pattern may give an order's places steps spread between the ends. Each step is a colour family too, whose fill and line the engine spreads from the two ends' roles and whose text is the order's text, and no concept maps to a role of an order" (points 1, 4 and 5). So its bullet "What a concept maps to" defines the colour families a notation maps to, and this bullet the families of an order. **The first sentence of its bullet "Colour is never the only sign"** reads "The families a notation maps to bound how many concepts one piece tells apart by colour" (point 1).
  - **Its point 11's list of what fails validation** gains "an order's text lighter than one end and darker than the other, in some combination", "a brand's last end that contrasts with the background more than its source's end, in some combination" and "a concept a notation maps to a role of an order" (point 9). The order's text below its level on an end already fails there as a declared pair, and a text on a step as a drawn text. Its item on a declared pair or a drawn text below its contrast also names a concept's line drawn on a step (points 6 and 9).
  - **Its Implications' first bullet** names an order's ends and text, and the mark of the neutral family, among what the foundations declare.
  - **The record of change over time's point 6,** its bullet "What breaks", gains after "A change of how something looks does not break, since the lock and the before-and-after protect each piece": "One such change breaks: a release that makes the steps of an order the default for a list of a pattern already released, since a draft that moves into it could newly fail" (point 10).
  - **Its point 8** gains a bullet, beside "No key claimed twice on an item": "**No steps without their roles.** Versions under which a pattern gives a list of a piece the steps of an order by its default, and the foundations do not declare the roles of an order, do not fit together for that piece" (point 10).
  - **The record of the engine and its plugins' Decision,** and its plain terms, name among the engine's tools the spread of an order's steps between two colours (point 10).
  - **Its point 5,** its bullet "Values stay roles": its sentence "Its value comes from the document of point 7, so one scene serves every mode of the value axes" reads "Its value comes from the document of point 7, or with the scene for a step of an order (point 6), so one scene serves every mode of the value axes". It gains: "A step of an order names the two roles it is spread between and its place's share of the way, the same in every mode" (point 10). **Its bullet "Every element carries its trace"** names among a property's sources a step of an order, by its two roles and its share (point 10).
  - **Its point 6,** its bullet "One scene for each language and each combination of size-axis modes", ends: "The values of every combination named come with each scene, a value for each step of an order among them, which the engine spreads from its two roles' values at the scene's size" (point 10).
  - **The record of an HTML page's modes' point 3,** its bullet "One custom property for each colour role the file paints", gains: "Each step of an order the file paints takes a custom property of its own too, under a name the renderer gives it, which no role's spelling by the CSS writer can take. No code outside the page reads it. Its value in each mode is the step's, which comes with the scene" (point 10).
  - **The record of library role defaults' point 3** gains a bullet: "No default of a library's own role, or of a component token, aliases a role of an order." **Its point 9's list of what fails validation** gains "a default that aliases a role of an order" (point 5).
  - **The record of a list's fields' point 6** gains, after its bullet "A family for each place", the bullet: "**An order's steps, spread from two ends.** A pattern may give a list's places the steps of an order instead, under a word of an option. The engine then spreads the brand's two ends evenly over the places the list draws, from the source's end at the first place to the last end at the last. That is the one colour computed from a place. Every other colour a place takes is a family the pattern writes in its data, and no other colour, and no role's name, is computed from a place" (point 4). **Its bullet "The order stands"** gains: "Where the place takes a step, a concept of a hue gives the item only its line" (point 6). **Its bullet "Items that belong together"** gains: "Where the outer item's place takes a step, it passes the step whole" (point 6). **Its point 9's list of what fails validation** gains "in a pattern: a word that gives a list the steps and names a family for some place of it" (point 9). The findings that ask for attention stay this record's (point 9).
  - **Its point 7,** under "Breaking, for a pattern", gains: "a release that makes the steps of an order the default for one of its lists, by a new option or by a changed default". **Its bullet "Not breaking"** reads, in its sentence on changes of look: "Nor is a change of a word's share, of an arrangement field's default or of the family a place takes, which changes how pieces look, save a release that makes the steps of an order a list's default" (point 10).
  - **Its Alternatives considered,** "Roles named by a place": its example "such as a ramp from a first level's role to the last's" is replaced by "such as a role `level-3` that the third place takes". Its reason reads: "A role's name would be computed from the place, where every role a component reads is written in a file: its own, its pattern's data, a notation, or the foundations' declaration of an order's ends. A family for each place is written in the pattern. An order's steps are no such role: the engine spreads them between two roles the foundations name, and no role's name is computed from a place", with the pointer to this record (point 4). Its rejection then reads as one of a role's name computed from a place.
- **The record of the principles of visual communication** (DEC-028) **and its rule RS-GRAPHIC-007** take five edits. Each cites this record by its id where it names a point of it:
  - **Its point 11,** "What it leaves as it is", reads whole: "How an item takes its colour stays as the founding record decides it (DEC-001 point 6). The engine judges no page's point. Content says it, by pointing the parts that show the order at another role, as that point allows, or by a pattern's word that gives its places the steps of an order. The content chooses that word, or a pattern made for orders takes it by default. On a step, an item's concept of a hue colours only its line. Elsewhere an item's colour still comes from the concept it names, and an icon takes its concept's colour family ([visual-communication:DEC-004-brands-and-notations] point 10). So a piece meets the rule with what the model holds" (points 4 and 6). Its words that the founding record's point stays true are dropped, since this record adds to that point, and so is its last sentence, which leaves colour roles that step in an order to a later record.
  - **Its Rationale, "Why the form rule narrows a reason, and leaves the model",** ends: "So the rule narrows the principle behind the model. The steps of an order change the model on no such judgement: the content, or a pattern made for orders by default, chooses them by a word, and the model resolves them" (points 4 and 6). That replaces its last sentence, "So the rule narrows the principle behind the model, and the model stays."
  - **Its rejected alternative, "The order's colour in the engine's model",** becomes "The engine judging a page's point", with the reason: "Rejected: it cannot tell a page's point, and content tells it, by pointing parts at a role or by a pattern's word for the steps of an order" (point 4).
  - **Its Implications' "Left to other records"** ends: "and the principles a shipped brand follows, refining the record of brands and notations", with its citation of that record. That replaces its words from "the colour roles that step in an order" to "both refining the record of brands and notations".
  - **RS-GRAPHIC-007's "From the text"** reads: "on a page whose point is an order, whether the content points the parts that show the order at one role, rather than each at its concept's, or whether their pattern gives their places the steps of an order." The rule's anchors gain this record's points 4 and 6. The edit adds a way to meet the rule and tightens none, so the set takes no new major (COR-051 point 7).
- **The principles every shipped brand follows** stay to a later record refining the record of brands and notations, as DEC-028 leaves them. This record decides only the neutral brand's ends (point 8).
- **The Tasks it implies,** under the Feature of the deck's redesign ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)):
  - **The foundations:** the three roles with their defaults, the declaration of the ends, the two text pairs, and the neutral family's mark, in a minor version. The schema of a library's roles gains the declaration of the ends, which the check refuses in any library but the foundations.
  - **The engine and the check:** a family for each place, which the record of a list's fields decided and the engine does not draw yet. Also the spread of point 4, with the scene's new kind of value and the version of the seam it moves, and each renderer's reading of it. Also a concept's line on a step, measured as drawn against each colour beside it (point 6), neighbouring steps measured as drawn (point 7), and the findings of point 9.
  - **The starter:** each pattern that draws an order offers the steps by an option's word. Its default item component paints its fill from its family, and its line apart from that fill (point 4). On an item that names no concept of a hue, that line is the step's own colour, so the Task weighs how it looks. That default holds under every word, so the Task weighs the change for pieces that draw no steps too. The Task audits its components for parts painted in a fixed role over a step, or in the family's text over a fixed fill, and for marks painted from the line on the family's own fill (points 2 and 4). Its README's colour section says that on a step a concept's line is the item's only colour mark, measured at 3 to 1 (point 6). Its owner chooses the option's default word, judged in review as the starter's other choices are ([visual-communication:DEC-007-starter-library] point 3). Making the steps the default of a pattern already released breaks the starter (point 10). Its reference drops a colour for each place from what it lacks. A library names its bases by major alone (DEC-001 point 5), so a piece may lock the starter with foundations older than the roles of an order, which point 10 settles.
  - **The neutral brand:** the ends and the text under point 8, in a minor version. Its ends start from the seventh round's, OKLCH lightness .28 and .54 in light mode and .90 and .64 in dark mode, in its text colour's hue.
  - **The capability's reference:** the foundations' roles, which names a component's family and a state's may take, how a pattern gives the steps and how they are spread, and the new findings, each on its page. Also how an item's family resolves member by member on a step, and what passes to what sits in it, where the pages say an item takes one family.
  - **The analysis's glossary:** an order, its source, its ends and a step.
- **The seventh round's slate** comes only with a change that gives the neutral brand's text colour a hue. That changes a brand shipped to every adopter, and this record does not decide it.
- **The redesign's other blocks.** A block that holds no place in an order takes no step, such as the seventh round's blocks for capabilities, which have no rank. A solid family for such a block is another meaning, which this record leaves to the redesign.
- **Revisit this record** if a brand needs to tune the middle of its ramp, if the level of point 7 misjudges the orders pieces draw, or if a pattern needs a mark of its own at its source, which point 5 refuses.
- **Left open:**
  - an order whose source is drawn last, such as a stack whose base is its source;
  - an order continued over two lists, such as over two pages, whose second list starts again at the source's end;
  - a picture a producer makes, or a live view, that must match a step. Only the ends reach them, through the document of a brand's resolved values, so each would spread them by this record's rule;
  - a concept's icon, or another mark a component keeps for a concept, on an item that takes a step, where it lies on the step;
  - a concept's mark measured as drawn elsewhere, where it is an item's only colour sign, such as a plain card's bar;
  - steps for a quantity, such as a heat map's, which a chart would need;
  - a ramp for each of the families of kinds;
  - a floor for a library that uses a shared role a minor version of the foundations adds.
