---
id: DEC-032
title: An order's places take colour steps, spread evenly between two ends each brand gives
status: proposed
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand gives an order two colours in each mode, one end for its source and one for its last place. It also gives one text colour for every step. Where the content chooses a pattern's word for an order, the engine spreads the two ends evenly over the list's places, whatever its length. That overturns an accepted record's refusal of a ramp from a first place's colour to the last's. The source's end stands out most from the page, so in a dark mode it is the lighter end. The text holds body text's contrast on both ends, and the check measures each step as drawn. A step shows only where an item stands, so no concept, component or state names one. An item that names a concept keeps its step as its fill. Its concept's colour becomes its line, held at 3 to 1 against what lies beside it. A brand whose lines are faint then fails such an item. Making the steps a released pattern's default breaks that pattern. A brand that gives no ends draws every step in its neutral colour.

## Context

Each colour family is a fill, a line and a text on the fill. The foundations declare six, a neutral one and five hues, and a notation maps its concepts to them ([visual-communication:DEC-004-brands-and-notations] point 10). Each family's text on its fill must reach WCAG's level for text, in every combination of the modes (DEC-004 point 8).

How an item takes its colour ([visual-communication:DEC-001-visual-communication-discipline] point 6):
- **From the concept it names,** read with its notation.
- **Else from a default:** the pattern's for the item's place, else its item component's, else that of the component it sits in.
- **A state may change it,** and content may point one part at another role.

How a place takes its colour ([visual-communication:DEC-010-list-item-fields] point 6):
- **A place** is an item's position among the items its list draws.
- **A pattern may give each place a family of its own,** in its data, and may switch those families on an option. A pyramid with no notation shades its levels so.
- **A place past those the pattern names** takes no family from the pattern, and the order goes on to its item component's.
- **Roles named by a place were refused,** "such as a ramp from a first level's role to the last's". A role's name would be computed from the place, where every role a component reads is written in its file (DEC-010, Alternatives considered).

A scene names a role for each colour it holds. It takes each role's value from the engine's document of a brand's resolved values, so one scene serves every mode ([visual-communication:DEC-005-engine-and-plugins] points 5 and 7). An HTML page paints each colour role with a custom property, whose value changes with the mode ([visual-communication:DEC-023-html-page-modes] point 3).

No colour family steps in an order. Each family is one colour for one kind, and a brand cannot give a ramp of one hue without taking the families notations map to. The engine draws one family for a whole list today. The starter lists a colour for each place among what it lacks ([project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576)).

The redesign of the showcase deck of the repository the capability is authored in needs such a ramp ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)). Its first page stacks five levels, from decisions down to code, each carrying out the ones above it. The seventh round of its drafts, which its critic passed, does this:
- **One ramp of one hue,** the slate of its text, at one chroma. Its OKLCH lightness steps evenly from .28 to .54 in light mode and from .90 to .64 in dark. So the source is darkest in light mode and lightest in dark. The levels name no concept.
- **One text on every step,** the page's own background. White holds 5.06 to 1 on the lightest light step, and 14.5 on the darkest.
- **Its reason:** lightness is the ordered variable, and one hue says "one chain". The deck's one accent then keeps its one meaning.
- **Order and a highlight never cross.** Order is only ever a block's fill. A highlight is only ever a line, a word or a tint region.

The record of the principles of visual communication accepts them as two rule sets. It leaves colour roles that step in an order to a later record ([visual-communication:DEC-028-principles-of-visual-communication] point 11).

The principles' rule that the form says what the content says, RS-GRAPHIC-007, asks that a picture's differences be those its content has. On a page whose point is an order, the parts that show the order share one colour, or step in one shade. Each concept an item names keeps its colour on a mark of its own.

Two rules bound how shared roles are added:
- **The foundations are released,** so a shared role added now carries a default that aliases an older role (DEC-004 point 7, [visual-communication:DEC-008-library-role-defaults] point 2).
- **A new top group of the shared roles** breaks the foundations, even where each of its roles has a default (DEC-004 point 5).

Seven terms:
- An *order* is a list whose items stand in a sequence the content means, such as a flow's steps or a stack's levels.
- Its *source* is the end it runs from, such as the level every other carries out, or a flow's first step.
- A *page whose point is an order* is there mainly to show the order its items stand in.
- The *families of kinds* are the colour families a notation maps a concept to.
- A *concept of a hue* is one its notation maps to a family of kinds that shows a hue, any but the neutral family.
- An order's *ends* are the two colours a brand gives it in each combination of its modes. The *source's end* is the one the first place takes, and the *last end* the one the last place takes.
- A *step* is the colour family a place of an order takes, spread from the ends.

## Decision

**Under a pattern's word, the engine spreads two ends a brand gives evenly over a list's places, as colour steps that share one text colour. A step shows only where an item stands, so on a step an item's concept gives only its line. This overturns DEC-010's refusal of a ramp, and keeps its refusal of a role named by a place.**

### 1. Two ends and a text, each a shared colour role

- **Three roles.** The foundations declare `family.order.first`, the source's end, `family.order.last`, the last end, and `family.order.text`, the text on every step. A brand gives each a value in every combination of its modes, as for every shared role.
- **Declared, never read from a name.** The foundations declare, as data, which role is the source's end and which the last end. They mark the family of kinds that shows no hue the same way. The engine and the checks read the ends and that family from these declarations.
- **In the group of the families.** The roles lie in the top group that holds every family's roles, so they add no top group (DEC-004 point 5). No library or brand holds a role of its own there. Each lies under a group named after its library, and no library takes a top group's name (DEC-004 point 7). A base that opens the group of the families to brands built on it opens these roles too (DEC-004 point 6).
- **Apart from the families of kinds.** The foundations declare the roles apart from the families, and no family is named `order`, so no concept can map to them (point 5).
- **Public names.** A brand exports the three roles as it exports every shared role (DEC-004 point 5). The steps between the ends are no role, and no brand exports them.

### 2. What a brand gives, and the contrast the text holds

- **Defaults.** Both ends default to the neutral family's fill, `family.neutral.fill`, and the text to its text, `family.neutral.text`. So every brand released before the roles still draws, with every step alike, as its neutral family. A default rarely holds against values a brand gives, so a brand that gives the ends but not the text mostly fails the text's pairs.
- **The text on both ends.** The foundations declare the order's text on each end as a pair at the level `text`, 4.5 to 1 (WCAG 1.4.3). Each pair is checked in every combination of the axes that change a colour, as every pair is (DEC-004 point 8). At the defaults, both pairs are the neutral family's own, which every brand already holds.
- **The text on one side of both ends.** In every combination, the order's text is lighter than both ends, or darker than both, by WCAG's relative luminance.
- **Each step measured as drawn.** A brand's check holds the ends alone. A piece's check measures each text on a step as drawn, in each combination the piece is drawn in (DEC-004 point 8).
- **Parts in a fixed role.** A step may be dark in a light mode, where every other family's fill is pale, and the order's text pale. So a part painted in a fixed role over its family's fill may fail on a step. So may a part painted in its family's text over a fixed fill, such as a card's text on the surface. The contrast as drawn finds both.
- **No pair of an end against the background.** A brand may still hold its ends far from the background, as the neutral brand does (point 7).

### 3. The source stands out most, in every mode

- **Measured against the background.** The source's end contrasts with the page's background at least as much as the last end does, by WCAG's ratio. That holds in every combination of the axes that change a colour, with an end that has alpha measured over the background. Where both ends lie on one side of the background and share one hue and chroma, each step lies between them in that ratio. The first place then stands furthest from the page, and the last place nearest.
- **So a dark mode gives its ends the other way round.** On a light background the source's end is the darker, and on a dark one it is the lighter. A brand gives each mode its own ends, and never inverts one mode's for another.
- **Equal ends pass,** as at the defaults, or as a mode of high contrast might give them. Every step is then alike, and the order shows by its other signs alone (point 4).
- **A background of a middle tone** may lie between the ends. The rule still holds, though a step between then comes near the page, which the brand judges.
- **Against the background alone.** Nothing is promised against another fill an order lies on, such as a surface.

### 4. A pattern may give an order's places their steps, spread over the list

- **Under a word of an option.** A pattern may offer the steps under a word of an option that switches its places' families (DEC-010 point 6). The content chooses that word where the page's point is the order. A pattern's owner may make it the option's default where the pattern's job is an order, which breaks a released pattern (point 9). Content then chooses another word where its point lies elsewhere.
- **Spread evenly.** Where a list draws n places, place k takes the colour (k − 1) / (n − 1) of the way from the source's end to the last. A list of one place takes the source's end. The engine spreads each combination's own ends, at the scene's size, and a place takes the same share in every combination.
- **In Oklab.** The spread runs along the straight line between the ends in Oklab, the colour space whose cylindrical form is OKLCH, so the lightness steps evenly. Between ends of one hue and chroma, only OKLCH's lightness changes.
- **Within the ends' range.** The engine brings back a step that falls outside the range of colours its ends are given in, as CSS Color 4's gamut mapping does. It lowers the step's chroma in OKLCH, at its lightness and hue.
- **Alpha and rounding.** Where an end has alpha, the spread premultiplies it, as CSS Color 4 interpolates. The engine rounds each step to a fixed precision, so the same files give the same steps on every machine (DEC-005 point 5).
- **Each step is a family.** Its `fill` and `line` are its colour, and its `text` is the order's text. An item component paints a step with the members it paints any family with. So a card painted on the surface shows the step only in the parts it paints from its family, such as its bar. A mark a component paints from its line on its own fill does not show it.
- **Every item counts.** Every item the list draws takes its place's step, an item that names its own component included. Content that ends an order with something outside it, such as a note that ends a row, places that outside the list. Places count from the first item the list draws (DEC-010 point 6), so the content lists the source first.
- **Nothing else is given.** A pattern names no role of an order. Under the word that gives the steps, it names no family for any place of that list.
- **Where no part shows the step.** Where no part an item draws takes a member of its step, the check asks the piece's author for attention. An item that names a concept of a hue takes point 6's findings instead.
- **A default item component for the steps.** A pattern that offers the steps names a default item component painting its fill from its family, and its line apart from it (point 6). An option chooses only the places' families, never the item's look, which is the item component's (DEC-001 point 6). So that default holds under every word. No check judges that choice, and a line drawn on its fill fails at the piece (point 6).
- **One list, never ties.** A word gives the steps to the places of one list the pattern repeats. A list of ties takes none, since a tie stands in no order ([visual-communication:DEC-011-tie-ends]).
- **Never the order's only sign.** A pattern that shades by place also shows the order by position, and by size, numbers or arrows where its form has them. Shades collapse under forced colours, and on a projector that washes them out.
- **Neighbouring steps, judged in review.** The ends stay where the brand set them, so each place added brings neighbouring steps closer. No check measures how close they come. That is the judgement of the piece's author, seen in review ([visual-communication:DEC-030-design-agents] point 6).

### 5. A step reaches an item only through a place, or where the content points a part at a role of an order

- **A step shows where an item stands in an order,** as a place's family does in a pyramid with no notation (DEC-001, Rationale). It never says what a thing is, or what state it is in.
- **Never where a family of kinds is named.** A notation's concept, a component's own default family, a state's family and a pattern's family for a place each name a family of kinds. A role of an order there is refused, as any name that is no such family is.
- **What a place takes.** A place takes one of the families of kinds, which its pattern names, or a step, which its pattern's word gives. A paint from the item's family paints from either.
- **Never by its name in a structure.** No part of a component paints with a role of an order by its name. No library's own role, and no component token, aliases one as its default.
- **A brand's aliases run either way.** A brand may alias a role of an order to another of its tokens, or another role to one of them. Its values are its own. A role means what the structure that reads it says, wherever its value comes from.
- **Content may point a part at a role of an order,** as at any role (DEC-001 point 6). An example is a legend's swatch of the source's end. Its author then says that the part shows a place. The steps between the ends are no role (point 1), so content points at none of them.

### 6. On a step, an item's concept gives only its line

- **The step fills the item, and its concept outlines it.** Where an item's place takes a step and the item names a concept of a hue, its members `fill` and `text` resolve to the step's. Its member `line` resolves to the concept's. Each part takes the member it paints with, and is measured as drawn. This rests on a component keeping `line` for its lines and marks.
- **A concept of the neutral family gives nothing on a step.** That family marks no kind by a hue, so the item takes the step whole.
- **A text run keeps its concept.** A run that names a concept still takes its concept's family ([visual-communication:DEC-012-text-runs] point 3). It is measured as drawn on the step, as on any fill not its family's own. Such a run mostly fails on a step, and its author drops the run's concept or chooses no steps.
- **The line at 3 to 1 against each colour beside it.** The check measures the concept's line as drawn against each fill it borders, in every combination the piece is drawn in (WCAG 1.4.11).
- **Beside nothing the piece draws, not measured,** as a text over nothing is not. An HTML page with no ground lies on the browser's own ([visual-communication:DEC-023-html-page-modes] point 7). There point 7 holds the neutral brand's lines off its background.
- **A family's line carries a promise here.** Elsewhere a family's line only edges its fill, which a brand may draw faint. Here a brand whose hues' lines are faint against its page fails such an item, and the finding names the brand's owner too.
- **Where the item cannot show both,** for a concept of a hue, the check asks the piece's author for attention. That is where no part the item draws takes its concept's line, or none takes the step's fill or text. An item component with no line or a fixed fill may cause it, and so may content that points a part at another role. The author may name another item component, or draw the list unshaded.
- **Only a step splits an item's family so.** A place that gives one of the families of kinds still yields to the item's concept (DEC-001 point 6, DEC-010 point 6). A state its component gives a family still replaces both (DEC-001 point 6), and each run's family too (DEC-012 point 3).
- **An outer item passes the step whole** to what sits in it, where nothing nearer gives a family (DEC-010 point 6). It keeps its concept's line as its own mark.

### 7. What the neutral brand gives

The neutral brand stays a brand to start from, so its ends carry no project's identity (COR-014 and DEC-001 point 9).
- **One hue, its text colour's own.** Both ends take it. Where the text colour has no hue, as a pure grey, the steps have none either.
- **Apart from the accent.** An end never takes the accent's colour. Where the text colour's hue lies near the accent's, the ends stay far below the accent's chroma.
- **The order's text is the background's own colour.** So an end whose text holds 4.5 to 1 stands 4.5 to 1 from the background as well.
- **Each hue's line at 3 to 1 from the background,** in every combination. So a concept's line on a step holds where the item lies on the page (point 6).

### 8. What the checks report, and how severely

Each finding lies where the record of files and validation puts it, and fails or asks for attention by that record's policy ([visual-communication:DEC-002-files-and-validation] point 7).
- **Fails validation:**
  - **in a brand, in some combination:**
    - the order's text below WCAG's level for text on an end, as every declared pair below its contrast fails (DEC-004 point 11)
    - the order's text lighter than one end and darker than the other
    - a last end that contrasts with the background more than the source's end
  - at a piece's lock: steps under foundations lacking an order's roles, where the content chose the word, or a person moved the lock there. A fault only a combination of versions shows fails at the lock that combines them (DEC-002 point 7).
  - in a notation, component, state or pattern's family for a place: a role of an order where a family of kinds is named
  - in a component: a part that paints with a role of an order by its name, or a component token whose default is one
  - in a library's roles: an own role whose default is a role of an order
  - in a library other than the foundations: a declaration of an order's ends, or a mark of the neutral family
  - in a pattern: a word that gives a list the steps and names a family for some place of it
  - at a piece, in some combination: a concept's line on a step below 3 to 1 against a colour beside it, as drawn. The finding also names the brand's owner.
- **Already failing:** a text on a step below its level as drawn, as every drawn text below its contrast fails (DEC-004 point 11).
- **Asks the piece's author for attention:**
  - an item on a step that names no concept of a hue, where no part it draws takes a member of its step (point 4)
  - an item on a step that names a concept of a hue, where no part it draws takes its concept's line (point 6)
  - such an item where no part it draws takes the step's fill or text (point 6)

### 9. The engine spreads the steps, their values come with the scene, and what breaks

- **One general tool.** The spread of point 4 is a tool of the engine, built and tested once in the capability (DEC-001 point 4). It is the one colour the engine computes from a place.
- **The scene names a step's roles.** A step's colour in the scene names the two roles it is spread between and its place's share of the way. Both are the same in every mode. A drawn step traces back to the two ends and its place ([visual-communication:DEC-005-engine-and-plugins] point 5).
- **Its values come with the scene.** The engine computes a step's value in each combination named, from those roles' values, at the scene's size. It hands them among the values of each scene (DEC-005 point 6), beside a role's from the document of a brand's resolved values. So a renderer takes every colour from one set, one scene still serves every mode, and no renderer spreads.
- **The document of values holds no step.** The document of a brand's resolved values is unchanged (DEC-005 point 7), so no code writer writes a step out.
- **The seam's version rises,** since a renderer must read the new kind of value (DEC-005 point 8).
- **Breaking, for a pattern already released:** a release that makes the steps the default for one of its lists, by a new option or by a changed default. Its items' concepts of a hue then give only their line, which changes what naming a concept means there (point 6). A pattern whose first release gives the steps by default breaks nothing. As every break, it needs a major release only where the pattern's status promises one (DEC-003 point 7).
- **A draft holds a pattern back.** Versions under which a pattern gives a list the steps by default, without foundations declaring an order's roles, do not fit together for a piece. So a draft does not move into them ([visual-communication:DEC-003-change-over-time] point 8). As for a key claimed twice, only a misfit the piece does not show under its lock counts. Where the piece's content chose the word, or a person moved its lock there, the check fails it at the lock (point 8).

### 10. What this adds to the libraries and the format, what it overturns, and what still holds

- **The foundations gain three shared roles, each with a default,** with the declaration of the ends and the neutral family's mark. A role with a default breaks nothing (DEC-004 point 5), so the foundations take a minor version ([visual-communication:DEC-013-shipped-library-releases] point 3).
- **The format grows by an addition** that every file written before still meets (DEC-003 point 3). The schema of a library's roles gains the declaration of the ends and the neutral family's mark. Only the foundations hold them, as only they declare families. The schema of a pattern gains a word that gives a list the steps.
- **Every brand draws every piece as before,** except where a pattern gives a list the steps. There, under a brand that gives no ends, every place draws as the neutral family, and a concept of a hue gives its line.
- **No file is renamed or removed,** and no project file changes shape, so no migration is owed (COR-010).
- **It overturns one refusal of the record of a list's fields** ([visual-communication:DEC-010-list-item-fields]), of a ramp from a first level's role to the last's. Its reason still holds of roles, since a step is no role (point 9). That refusal stays as it stood, under a *Partially superseded by* top line, and the rest is refined in place (Implications).

## Rationale

**Why an order takes steps of its own, apart from the families of kinds.** Jacques Bertin's visual variables tell the two apart (*Sémiologie graphique*, 1967).
- **Hue is selective:** the eye splits items of five hues into five groups.
- **Lightness is ordered:** the eye reads five lightnesses as a sequence.
- **A picture shows the facts of its data and no others,** by Jock Mackinlay's expressiveness (1986). An order drawn in five hues shows five kinds and no sequence.

**Why the steps are spread over the list.**
- **Every order spans the whole ramp.** Whatever the list's length, the source takes the end that stands out most, and the last place the other. A short order is not drawn in the ramp's strongest end alone, and a long one never runs out of steps.
- **A sequential scheme fits its count.** ColorBrewer's sequential schemes pick their colours again for each number of classes (Cynthia Brewer). So a class's colour depends on the count, as a place's does here. Those schemes widen their range as the classes grow. Here the brand fixes the range, so neighbours come closer instead.
- **The cost, accepted.** The second item of a short list looks different from the second item of a long one. A page whose point is an order compares its places within one order, and two orders still compare by position and numbers.

**Why the steps overturn DEC-010's refusal of a ramp, and keep its reason.** That record refused roles named by a place. A role's name would then be computed from the place, where every role a component reads is written in a file. The steps keep that reason, since the two roles they spread between are written in the foundations (point 9). What they take is a colour computed from a place, which a ramp needs to span the whole order at any length.

**Why two ends for each mode.** Two colours are the least that fix a ramp: which step stands out most, and how near the page the last one comes. The brand chooses both, in each mode. An even spread in a space the eye sees evenly makes near-equal steps between them, so the middle needs no tuning.

**Why Oklab.** Oklab spaces lightness close to how the eye sees it (Björn Ottosson, 2020), so equal steps of it look near-equal. A straight line in it needs no rule for hue, and reproduces the redesign's ramp, whose ends share one hue and chroma. Between two far hues its middle loses chroma, which the brand sees in its own steps.

**Why a list of one takes the source's end.** A list of one is its own source, and a list that grows from one keeps its first item's colour.

**Why the engine computes the steps.** Only a brand holds a raw value (DEC-001 point 5), and a renderer adds no colour of its own (DEC-001 point 2). A need that recurs becomes a general tool of the engine, built and tested once (DEC-001 point 4). So every medium draws the steps the check measured. The spread is one fixed rule, so a brand's owner knows every step its ends give, at any count.

**Why a step's values come with the scene.** A step is no token of the brand, and which steps a piece draws depends on its lists. The scene names only the two roles and the share, so a change of the brand's values changes no scene.

**Why a default of the steps breaks a released pattern.** A change of how something looks does not break, nor does a change of the family a place takes (DEC-003 point 6, DEC-010 point 7). By default, though, the steps change what naming a concept means on the pattern's items. A concept of a hue gave its whole family there, and gives only its line. That breaks, so they reach a stable pattern only in a new major, taken on purpose (DEC-003 points 6 and 7).

**Why the ends and the neutral family are declared, not read from names.** The engine and the checks act on which end is the source, and on which family has no hue. The naming rule gives a name no rank or hue (DEC-004 point 4).

**Why one text on every step.** A text that differed from step to step would add a difference the order lacks. One role is one value a brand tunes in each mode.

**Why a brand's check holds the ends, and a piece's each step.** A brand cannot know how many places its pieces draw, but a piece's lists are known. Between ends of one hue and chroma, a text on one side of both ends that holds on both holds on every step between. Between two far hues, a step may fail where both ends pass, and the piece's check finds it where it is drawn.

**Why the text lies on one side of both ends.** A text holding 4.5 to 1 on both ends lies between them only as a middle grey, between a near-black end and a near-white one. A ramp between such ends passes through the text's own colour, so some step fails at almost every count. Refused in the brand, that fault is its owner's to mend, not each piece's.

**Why no pair of an end against the background.** WCAG asks 4.5 to 1 of body text on what lies under it (1.4.3), and an item's text lies on its step. It asks 3 to 1 of a graphic a reader needs to understand the content (1.4.11). An order's shade is a second sign of what position already shows, so it is no such graphic. No family carries such a pair, and the neutral family's quiet fill would fail one at the defaults.

**Why measured from the background.** What makes a step stand out is its distance from the page, not its darkness. Material's colour roles keep their emphasis so: its primary colour is tone 40 in a light scheme and tone 80 in a dark one. Its surface containers step away from the surface in both, from tone 96 to 90 in light and from 10 to 22 in dark. One rule on the distance holds in every mode, high contrast included, where an inverted ramp would sink the source into a dark page.

**Why no check of neighbouring steps.**
- **A reading of the drawing.** How close is too close depends on the page and where it is shown, which only the drawing shows.
- **No level to hold.** WCAG asks no contrast between two fills that each carry their own text and a second sign of their place. The order never rests on its shade alone (point 4).
- **For scale:** at the lightness the neutral brand's ends start from (Implications), neighbouring steps of an order of five stand 1.23 to 1.33 to 1 apart. In an order of nine they stand 1.11 to 1.16.

**Why the defaults are the neutral family.** A default is the fairest stand-in until a brand gives a value (DEC-008 point 2). The neutral family is the starter's own default for its blocks, which every brand already tuned and whose pairs already hold. So a brand that gives no ends adds no difference its owner never chose, and the order shows by position.

**Why only a place takes a step.** A notation's concept, a component's own family and a state each say what a thing is, or how it stands. A step among them would show a place in an order where there is none. A role of an order that a component or a library's role names would become one more colour of a palette, in every brand. The content may point a part at one, since there its author places the part.

**Why, on a step, the concept takes the line.**
- **Each part carries one variable.** The fill carries the place by its lightness, Bertin's ordered variable. The line carries the kind by its hue, his selective one. The redesign's seventh round keeps that split on every page, and RS-GRAPHIC-007 has each concept keep its colour on a mark of its own.
- **A state may still fill the item.** A state is a difference the content has, and its look is its component's (DEC-001 point 6). Today that look is a family, so a state on a step leaves the chain's shade. A state's look other than a family, such as a line, is left to a later change.

**Why the line is measured against each colour beside it.** On a step the line is a concept's only colour mark, so WCAG 1.4.11 asks 3 to 1 of it against the colours beside it. The neutral brand's lines of the five hues stand 1.0 to 2.6 to 1 from the seventh round's ramp, in both modes. From its pages they stand 5.7 to 8.0 to 1. So the default item component draws the line apart from its fill, with the page on both its sides, as the round's picture does.

**Why a neutral concept gives nothing, and an outer item passes the step whole.** A neutral concept's line, a quiet rule 1.4 to 1 from a light page in the neutral brand, marks no kind by a hue. At the defaults, where the step is the neutral family too, the item then looks as it would with its concept first. What sits in an item lies on the step, where no line of a hue holds 3 to 1. The outer item's line already marks the concept.

**Why a missing line asks for attention, and does not fail.** WCAG 1.4.11 binds a mark that is drawn, so a weak line fails as a weak text does. Whether a concept is marked at all is a reviewer's judgement, under the rule that the same meaning looks the same (RS-GRAPHIC-004). Its author may mark the concept another way, or choose no steps.

**Why the neutral brand's ends follow these principles.**
- **One hue, the text's.** Cynthia Brewer's single-hue sequential schemes step lightness in one hue, so the eye reads a sequence and no kinds. The text colour's hue reads as a deepening of the text, not as a brand's colour, so the neutral brand stays one to start from.
- **Far below the accent.** Kept far below the accent's chroma, the steps leave the accent its one job. Where one hue ends and another starts is a judgement no check makes. So no check holds the neutral brand's ends off its accent, and whoever reviews its release judges it.
- **The text in the background's colour** makes the pair and the distance from the page one measure.

### Alternatives considered

- **A full set of stops for each mode,** such as five colours a brand tunes, which the steps take or spread between. Rejected. It is three times the colours to tune, for a middle no page needed.
- **One colour a brand gives, from which the engine derives the rest,** lighter and darker in OKLCH. Rejected. Nobody then chooses the light end, and the derived end can fail its text.
- **Five fixed steps, the same for every brand, one to each place from the first.** Rejected. A short order takes only the ramp's strongest end, and a place past the fifth takes no step. Each step is three more colours a brand tunes. A place drawn alike in every order serves a comparison across orders that a page whose point is one order does not make.
- **Steps spread in OKLCH, its hue taken along the shorter arc.** Not chosen. Between ends of one hue and chroma it gives Oklab's steps. Elsewhere it needs a rule for hue, which a grey lacks.
- **Steps spread in sRGB's values.** Rejected. Equal steps of them do not look equal.
- **A ramp for each of the families of kinds,** as Material keeps a tonal palette for each key colour. Not chosen. Each of six families would need its own ends, and a page whose point is an order needs its order shown, not its kinds.
- **Steps of a pattern's own library,** such as the starter's. Rejected. Each library that draws an order would declare its own, and a brand gives them values only where it names that library (DEC-008 point 4). A meaning every library needs is a shared role's (DEC-008 point 2).
- **The roles under a top group of their own,** such as `order.first`. Rejected. A new top group is a breaking change of the foundations (DEC-004 point 5).
- **No defaults, in a major release of the foundations.** Rejected. Every brand would give three values in every combination before it read the new major, and every lock would move on purpose.
- **Defaults that alias the text colour and the background,** a solid block in the text's colour. Rejected. A brand that never chose it would draw an order as heavy blocks, an emphasis its owner never chose.
- **A pair of each end against the background, at 3 to 1.** Rejected in the foundations (Rationale, "Why no pair of an end against the background").
- **A check of how close neighbouring steps come,** asking for attention or failing below a level, such as 1.15 to 1. Rejected (Rationale, "Why no check of neighbouring steps").
- **A step's line in the order's text.** Rejected. A card's bar on the surface would take the order's text, pale in a light mode, and the step would show nowhere on the card.
- **The steps in the document of a brand's resolved values.** Rejected. A code writer writes that document out, so the steps of one piece's lists would leave the capability as a brand's code (DEC-005 point 7).
- **Each step's value in each mode held in the scene itself.** Not chosen. A change of a brand's values would change a scene, for its steps alone.
- **The steps as a pattern's default, breaking nothing.** Rejected. The release changes what naming a concept means on the pattern's items (Rationale, "Why a default of the steps breaks a released pattern").
- **A draft held back from a release that makes the steps a default,** as from versions that claim a key twice (DEC-010 point 2). Rejected. A hold waits for another library's version to mend a clash between two, and none mends the pattern's own change. The draft would stay behind each later release until a person moves it, as a break asks, with no major to say so.
- **The concept's whole colour before the step,** as a place that gives a family of kinds yields to it. Rejected. One item of the chain would take its concept's hue, a difference on the very chain the page is about, which RS-GRAPHIC-007 refuses.
- **The step alone, with the concept unmarked.** Rejected. A concept's colour is its only mark today, since format 1 draws no concept's icon (DEC-012, Context).
- **The concept's colour on the item's text.** Rejected. A concept's text, tuned for its family's own fill, would fail its pair on a step.
- **The line measured against what the item lies on alone.** Rejected. A line drawn on the step would pass, and be lost against it.
- **A pair of each family's line against the background, at 3 to 1, or of each hue's.** Rejected. It judges a brand, but not what a line borders where it is drawn: the step, or the next item where items touch. It would also bind every family's line where it marks nothing.
- **A neutral concept's line drawn on a step,** or exempt from the check. Rejected. It would mark no kind, and either fail where nothing is wrong or stand unjudged.
- **Content points each item's parts at its step,** with no family for each place. Rejected. The steps between the ends are no role, and an item inserted would leave every later one on the wrong colour.
- **The roles of an order as a component's own family, or a state's,** such as a block drawn solid in the source's end. Rejected (Rationale, "Why only a place takes a step").
- **The engine tells whether a page's point is an order.** Rejected. It cannot, so the content chooses it by a word.
- **A renderer spreads the steps,** such as an HTML page that mixes the two ends' properties in Oklab in CSS. Rejected: a renderer adds no colour of its own (DEC-001 point 2). A browser brings a step outside the range back its own way, so a page could draw another colour than the check measured. A medium with no such mix would still need the values.

## Implications

### Edits to accepted records

Each is made once a person accepts this record, in the change that proposes it, and accepting this record accepts them ([COR-066](../../../decisions/core/COR-066-accepted-before-landing.md) point 5). Each edit ends with a pointer to this record and the point it names, in the form the accepted records use.

- **The founding record (DEC-001), point 6:**
  - It gains a bullet (point 5): "An order's steps are colour families the engine spreads over a list's places, from two ends a brand gives. No concept, component or state names one, and no part of a component names a role of an order."
  - Its bullet "Colour says what a thing is" gains, after its sentence on a default (point 6): "Where an item names a concept of a hue and its place takes a step of an order, its members `fill` and `text` take the step's. Its member `line` takes its concept's."
- **The record of brands and notations (DEC-004):**
  - Point 7 gains, beside its bullet on a component token's default (point 5): "No component token's default aliases a role of an order."
  - Point 8 gains a bullet (points 2 and 3): "An order's text on each of its two ends is a declared pair. The text is lighter than both ends, or darker than both. In every combination, the source's end stands at least as far from the background as the last end, by WCAG's ratio."
  - Point 8's bullet "Checked as drawn" gains (point 6): "The engine also measures a concept's line on an item that takes a step of an order against each colour beside it, at WCAG's level for other marks."
  - Point 10 gains a bullet (points 1, 4 and 5): "The foundations also declare an order's two ends and its text, apart from the families a notation maps to, and mark the family that shows no hue. A concept a notation maps to any other family is a concept of a hue. A pattern may give an order's places steps spread between the ends. Each step is a colour family too, whose fill and line the engine spreads from the ends' roles and whose text is the order's text. No concept maps to a role of an order." Its bullet "What a concept maps to" keeps its text, and so defines the families a notation maps to, beside the new bullet's families of an order.
  - The first sentence of point 10's bullet "Colour is never the only sign" reads (point 1): "The families a notation maps to bound how many concepts one piece tells apart by colour."
  - Point 11's list of what fails validation gains "an order's text lighter than one end and darker than the other, in some combination", "a brand's last end that contrasts with the background more than its source's end, in some combination" and "a concept a notation maps to a role of an order" (point 8). The order's text below its level already fails there, on an end as a declared pair and on a step as a drawn text. Its item on a declared pair or a drawn text below its contrast also names a concept's line drawn on a step (points 6 and 8).
  - Its Implications' first bullet names an order's ends and text, and the mark of the neutral family, among what the foundations declare.
- **The record of change over time (DEC-003):**
  - Point 6's bullet "What breaks" gains, after "A change of how something looks does not break, since the lock and the before-and-after protect each piece" (point 9): "One such change breaks: a release that makes the steps of an order the default for a list of a pattern already released. An item's concept of a hue then gives only its line there, which changes what naming it means."
  - Point 8 gains a bullet beside "No key claimed twice on an item" (point 9): "**No steps without their roles.** Versions under which a pattern gives a list of a piece the steps of an order by its default, and the foundations do not declare the roles of an order, do not fit together for that piece. As for a key claimed twice, only a misfit the piece does not show under its lock counts."
- **The record of the engine and its plugins (DEC-005):**
  - Its Decision and its plain terms name among the engine's tools the spread of an order's steps between two colours (point 9).
  - Point 5's bullet "Values stay roles" gains (point 9): "A step of an order is no role. It names the two roles it is spread between and its place's share of the way, the same in every mode. Its value comes among the values that come with each scene (point 6), as every role's does."
  - Point 5's bullet "Every element carries its trace" names among a property's sources a step of an order, by its two roles and its share (point 9).
  - Point 6's bullet "One scene for each language and each combination of size-axis modes": its last sentence, "The values of every combination named come with each scene", reads (point 9): "The values of every combination named come with each scene, a value for each step of an order among them. The engine spreads each step from its two roles' values at the scene's size."
- **The record of an HTML page's modes (DEC-023), point 3,** its bullet "One custom property for each colour role the file paints", gains (point 9): "Each step of an order the file paints takes a custom property of its own too. The renderer gives it a name that no role's spelling by the CSS writer can take, and no code outside the page reads it. Its value in each mode is the step's, which comes with the scene."
- **The record of library role defaults (DEC-008):** point 3 gains, after its bullet "A component token's default", the bullet "**Never a role of an order.** No default of a library's own role, or of a component token, aliases a role of an order." Its point 9's list of what fails validation gains "a default that aliases a role of an order" (point 5).
- **The record of a list's fields (DEC-010):**
  - Point 6 gains, after its bullet "A family for each place" (point 4): "**An order's steps, spread from two ends.** A pattern may give a list's places the steps of an order instead, under a word of an option. The engine then spreads the brand's two ends evenly over the places the list draws, from the source's end at the first place to the last end at the last. That is the one colour computed from a place. Every other colour a place takes is a family the pattern writes in its data, and no other colour, and no role's name, is computed from a place."
  - Point 6's bullet "The order stands" gains (point 6): "Where the place takes a step, a concept of a hue gives the item only its line." Its bullet "Items that belong together" gains (point 6): "Where the outer item's place takes a step, it passes the step whole."
  - Point 7, under "Breaking, for a pattern", gains (point 9): "a release that makes the steps of an order the default for one of its lists, by a new option or by a changed default". Its bullet "Not breaking" ends its sentence on changes of look with ", save a release that makes the steps of an order a list's default".
  - Point 9's list of what fails validation gains "in a pattern: a word that gives a list the steps and names a family for some place of it" (point 8). The findings that ask for attention stay this record's.
  - **Its top line** reads *Partially superseded by* [visual-communication:DEC-032-ordered-colour-steps], in the shape the record of change over time's takes (point 10). Overturned: its rejected alternative "Roles named by a place", so far as its example refuses a ramp from a first level's role to the last's. The rest stands, and that alternative stays as it stood.
- **The record of the principles of visual communication (DEC-028) and its rule RS-GRAPHIC-007,** each edit citing this record by its id where it names a point of it:
  - Point 11's paragraph "What it leaves as it is" reads whole (points 4 and 6): "How an item takes its colour stays as the founding record decides it (DEC-001 point 6). The engine judges no page's point. Content says it by pointing the parts that show the order at another role, as that point allows. Or it says it by a pattern's word that gives its places the steps of an order. The content chooses that word, or a pattern made for orders takes it by default. On a step, an item's concept of a hue colours only its line. Elsewhere an item's colour still comes from the concept it names, and an icon takes its concept's colour family ([visual-communication:DEC-004-brands-and-notations] point 10). So a piece meets the rule with what the model holds." That drops its words that the founding record's point stays true, since this record adds to that point, and its last sentence on colour roles that step in an order.
  - Its Rationale "Why the form rule narrows a reason, and leaves the model" ends (points 4 and 6): "So the rule narrows the principle behind the model. The steps of an order change the model on no such judgement. The content, or a pattern made for orders by default, chooses them by a word, and the model resolves them." That replaces "So the rule narrows the principle behind the model, and the model stays."
  - Its rejected alternative "The order's colour in the engine's model" becomes "The engine judging a page's point" (point 4): "Rejected: it cannot tell a page's point, and content tells it, by pointing parts at a role or by a pattern's word for the steps of an order."
  - Its Implications' "Left to other records" drops the colour roles that step in an order. After the citation of project-kit#2584 it ends "; and the principles a shipped brand follows, refining the record of brands and notations", citing that record.
  - RS-GRAPHIC-007's "From the text" ends, after "rather than each at its concept's": ", or whether the order's places take the steps of an order". The rule's anchors gain this record's points 4 and 6. The edit adds a way to meet the rule and tightens none, so the set takes no new major (COR-051 point 7).

### Tasks and what is left

- **The principles every shipped brand follows** stay to a later record refining the record of brands and notations, as DEC-028 leaves them. This record decides only the neutral brand's ends (point 7).
- **The Tasks it implies,** under the Feature of the deck's redesign ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)):
  - **The foundations:** the three roles with their defaults, the declaration of the ends, the two text pairs and the neutral family's mark, in a minor version. The check refuses the declaration of the ends, and the neutral family's mark, in any library but the foundations.
  - **The engine and the check:** a family for each place, which the record of a list's fields decided and the engine does not draw yet. Also the spread of point 4, the scene's new kind of value, the seam's version it moves, and each renderer's reading of it. Also a concept's line on a step, measured as drawn against each colour beside it (point 6), and the findings of point 8. The release comparison counts as a break, for a stable pattern, an option whose default comes to give the steps (point 9).
  - **The starter:** each pattern that draws an order offers the steps by an option's word. Its owner chooses the default word, judged in review as the starter's other choices are ([visual-communication:DEC-007-starter-library] point 3). Its default item component paints its fill from its family, and its line apart from that fill, under every word (point 4). The Task weighs how that line looks, in a step's own colour and in pieces that draw no steps.
  - **The starter's audit and pages:** the Task audits its components for parts in a fixed role over a step, or in the family's text over a fixed fill (point 2). It also audits them for marks painted from the line on the family's own fill (point 4). Its README says that on a step a concept's line is the item's only colour mark, at 3 to 1 (point 6). Its reference drops a colour for each place from what it lacks.
  - **The starter's releases:** making the steps the default of a pattern already released breaks it (point 9). An experimental pattern may take that break in any release, as it may any other (DEC-003 point 7). A library names its bases by major alone (DEC-001 point 5). So a piece may lock the starter with foundations older than the roles of an order, which point 9 settles.
  - **The neutral brand:** the ends and the text under point 7, in a minor version. Its ends start from the seventh round's OKLCH lightness, .28 and .54 in light and .90 and .64 in dark, in its text colour's hue. Whoever reviews its release judges its ends kept off its accent.
  - **The capability's reference:** the foundations' roles, the names a component's or a state's family may take, how the steps are given and spread, and the new findings. Also how an item's family resolves member by member on a step, and what passes to what sits in it.
  - **The design reviewer:** what records leave to its reading gains how close an order's neighbouring steps come (point 4).
  - **The analysis's glossary:** an order, its source, its ends and a step.
- **The seventh round's slate** comes only with a change that gives the neutral brand's text colour a hue. That changes a brand shipped to every adopter, and this record does not decide it.
- **The redesign's other blocks.** A block that holds no place in an order takes no step, such as the seventh round's blocks for capabilities, which have no rank. A solid family for such a block is another meaning, which this record leaves to the redesign.
- **Revisit this record** if:
  - a brand needs to tune the middle of its ramp
  - a pattern needs a mark of its own at its source, which point 5 refuses
  - reviews keep finding long orders whose neighbouring steps blur
- **Left open:**
  - an order whose source is drawn last, such as a stack whose base is its source
  - an order continued over two lists, such as over two pages, whose second list starts again at the source's end
  - a picture a producer makes, or a live view, that must match a step. Only the ends reach them, through the document of a brand's resolved values, so each would spread them by this record's rule.
  - a concept's icon, or another mark a component keeps for a concept, on an item that takes a step, where it lies on the step
  - a concept's mark measured as drawn elsewhere, where it is an item's only colour sign, such as a plain card's bar
  - steps for a quantity, such as a heat map's, which a chart would need
  - a ramp for each of the families of kinds
  - a floor for a library that uses a shared role a minor version of the foundations adds
