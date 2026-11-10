---
id: DEC-032
title: An order's places take colour steps, spread evenly between two ends each brand gives
status: proposed
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where a list's items stand in an order, such as a stack of levels from decisions down to code, the content, or the pattern by default, may have them shaded by their place. A brand gives two colours for each mode, one for the order's first item and one for its last, and one text colour for every shade. The engine spreads the two colours evenly over the list, whatever its length, and hands each shade to the renderers with the scene. A brand that gives none draws every shade alike. This record decides that method, and what every brand and library follows to use it, not how a library draws the shades or which colours a brand gives. It overturns parts of two accepted records, which refused such a ramp and kept the engine's model of colour as it stood.

## Context

Terms:
- An *order* is a list whose items stand in a sequence the content means, such as a stack's levels. Its *source* is its first item, the one the rest follow from, such as the level every other carries out.
- An order's *ends* are the two colours a brand gives it in each combination of its modes: the *first end*, which its first place takes, and the *last end*, which its last place takes.
- A *step* is the fill, line and text a place of an order takes where it would take a colour family. Its fill and line are spread from the ends, and its text is the order's text.

A *colour family* is a fill, a line and a text on the fill, whose text reaches WCAG's level for text in every combination of the modes. The foundations declare the families, and a notation maps each concept to one ([visual-communication:DEC-004-brands-and-notations] points 8 and 10). An item's family is its concept's, else its place's, else its item component's, else that of the component it sits in, and a state may change it ([visual-communication:DEC-001-visual-communication-discipline] point 6). A *place* is an item's position among the items its list draws, and a pattern may give each place a family in its data ([visual-communication:DEC-010-list-item-fields] point 6). Roles named by a place were refused, "such as a ramp from a first level's role to the last's" (DEC-010, Alternatives considered).

A scene names a role for each colour it holds, and takes each role's value from the engine's document of a brand's resolved values, so one scene serves every mode ([visual-communication:DEC-005-engine-and-plugins] points 5 and 7). No colour family steps in an order, and a brand cannot give a ramp of one hue without taking the families notations map to ([project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576)). The redesign of the showcase deck needs one: its first page stacks five levels, each carrying out the ones above it ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)).

The record of the principles of visual communication keeps the engine's model of colour, and rejects the order's colour in it: the engine cannot tell a page's point, and content can point the parts that show an order at one role. It leaves colour roles that step in an order to a later record ([visual-communication:DEC-028-principles-of-visual-communication] point 11, Rationale and Alternatives considered).

A shared role added to the released foundations carries a default that aliases an older role, and a new top group of the shared roles breaks them (DEC-004 points 5 and 7, [visual-communication:DEC-008-library-role-defaults] point 2).

## Decision

**Under a word of a pattern's option, the engine spreads two ends a brand gives evenly over a list's places, as colour steps that share one text colour, and hands their values with the scene. A brand that gives no ends draws every step alike. This overturns the refusal of a ramp in DEC-010, and the statement in DEC-028 that the model of colour stays.**

### 1. A brand gives two ends and a text, as three shared roles

- **Three roles.** The foundations declare `family.order.first`, the first end, `family.order.last`, the last end, and `family.order.text`, the text on every step. Each has a value under every brand in every combination of its modes, given or from its default, and a brand exports them as every shared role (DEC-004 point 5).
- **Declared, never read from a name.** The foundations alone declare, as data, which role is the first end and which the last, and the engine and the checks read the ends from that. A name is a word for readers: the naming rule fixes its shape, and nothing it means (DEC-004 point 4).
- **In the group of the families, apart from them.** The roles lie in the top group that holds every family's roles, so they add no top group, and a base that opens that group opens them too (DEC-004 points 5 and 6). They form no family, and no family takes the name `order`, so no concept maps to them.
- **Defaults.** Both ends default to the fill of `family.neutral`, the foundations' family that marks no kind by a hue, and the text to its text. So a brand that gives no ends, as every brand released before the roles, draws every step alike, as that family.
- **The steps between are no role,** and no file names one.

### 2. What every brand's ends hold

- **The text on both ends.** The foundations declare the order's text on each end as a pair at the level `text`, 4.5 to 1 (WCAG 1.4.3), checked in every combination of the axes that change a colour (DEC-004 point 8). A piece's check measures each text on a step as drawn, as every drawn text.
- **The text on one side of both ends.** In every combination, the order's text is lighter than both ends, or darker than both, by WCAG's relative luminance.
- **The first end stands out most.** In every combination, the first end contrasts with the shared role `background`, the page's ground, at least as much as the last end does, by WCAG's ratio, an end with alpha measured over it. So with both ends darker than a light background the first end is the darker, and with both lighter than a dark one the lighter. Equal ends pass. Nothing is promised against another fill an order lies on, such as a surface.

### 3. A pattern gives an order's places their steps, under a word

- **Under a word of an option** that switches its places' families (DEC-010 point 6). A person chooses it, the content's author by the word or the pattern's owner by its default, and the engine never does.
- **One list, its places alone.** Each word gives the steps to one list the pattern repeats, spread over that list's places alone, and the pattern then names no family for any place of it.
- **Every item counts,** an item that names its own component included, so content that ends an order with something outside it places that outside the list. Places count from the first item the list draws, so the content lists the source first.
- **A step stands in for a place's family,** wherever a family goes. So an item's concept, and a state that gives a family, still come before it (DEC-001 point 6). An outer item passes its step to what sits in it, where nothing nearer gives a family (DEC-010 point 6).
- **Never the order's only sign.** The pattern also shows the order by position, and by size, numbers or arrows where its form has them, since shades collapse under forced colours.
- **Shown by the list's default item component.** A pattern that offers the steps names, for that list, a default item component that paints its fill from its family, the fill the order's text is checked on (point 2). No check judges this or the order's other signs: the pattern's owner does, in review, as for a default (DEC-008 point 2).
- **Without the roles, no step.** Under foundations that declare no ends, a place takes no step, and its item goes on to its item component's family, as at a place past those a pattern names (DEC-010 point 6).

### 4. The engine spreads the steps evenly, in Oklab

- **Evenly over the places drawn.** Where a list draws n places, place k takes the colour (k − 1) / (n − 1) of the way from the first end to the last, and a list of one place takes the first end. The engine spreads each combination's own ends, at the scene's size.
- **In Oklab,** along the straight line between the ends, so lightness steps evenly. A step outside the wider of the ranges of colours its ends are given in comes back by CSS Color 4's gamut mapping, and alpha is premultiplied, as CSS Color 4 interpolates. Each step is computed in a fixed order and rounded, as the scene is, so under one release the same files give the same steps on every machine (DEC-005 point 5).
- **A step paints as a family.** Its `fill` and `line` are its colour, and its `text` is the order's text. An item component paints a step with the members it paints any family with. So a mark painted from its line over its own fill does not show the step. And a step may lie far in lightness from every family's fill, so two parts may fail where they are measured as drawn: a part painted in a role from outside its family, over the step, and a part painted in the order's text over a fill from outside its family, such as a card's text on the surface.
- **One general tool,** built and tested once (DEC-001 point 4), and the one colour the engine computes from a place.

### 5. A step's values travel with the scene

- **The scene names a step by its ends:** the two roles it is spread between, and its place's share of the way, the same in every mode (DEC-005 point 5).
- **Its values come with the scene.** The engine computes a step's value in each combination named, and hands them among the values that come with each scene (DEC-005 point 6). So a renderer takes every colour from the values that come with each scene, each role's from the document of a brand's resolved values and each step's computed for that scene, and spreads nothing.
- **The document of a brand's resolved values holds no step** (DEC-005 point 7), so no code writer writes one out.
- **The seam's version rises,** since a renderer reads a new kind of value (DEC-005 point 8).

### 6. Only a place takes a step

- **Never where a family is named.** A notation's concept, a component's own family, a state's family and a pattern's family for a place each name a family, never a role of an order. A step shows where an item stands, never what it is or what state it is in.
- **Never by its name in a library.** No part of a component paints with a role of an order by its name, and no library's own role or component token aliases one as its default.
- **Content may point a part at one,** as at any role (DEC-001 point 6), such as a legend's swatch of the first end.

### 7. What the checks fail

Each finding lies where the record of files and validation puts it ([visual-communication:DEC-002-files-and-validation] point 7):
- in a brand, in some combination: the order's text lighter than one end and darker than the other, or a last end that contrasts with the background more than the first end. The order's text below its level, on an end or on a drawn step, already fails (DEC-004 point 11).
- in a library other than the foundations: a declaration of an order's ends
- in a notation, a component, a state, a pattern or a library's roles: a breach of point 6
- in a pattern: a word that gives a list the steps and names a family for some place of it

Stated as a fact, at a piece's lock: a list that takes the steps by its word, under foundations that declare no ends (point 3).

### 8. What it adds, and what it overturns

- **The foundations gain three roles with defaults,** which break nothing, so they take a minor version ([visual-communication:DEC-013-shipped-library-releases] point 3). The schemas of a library's roles and of a pattern grow by additions every file written before still meets ([visual-communication:DEC-003-change-over-time] point 3), so no migration is owed (COR-010).
- **Every brand draws every piece as before,** except where a list takes the steps. A release that makes the steps a pattern's default changes how its places look, as a change of a place's family does, and an item's concept still comes first, so it breaks nothing (DEC-003 point 6, DEC-010 point 7). A part may then fail at a draft's next render, as point 4 says. So the pattern's owner audits its own item components for both cases before such a release. An item component of another library, which content or an item names, is its draft's author's to catch at render, as any change of look is (DEC-001 point 7).
- **Two accepted records are overturned in part.** Each stays accepted, with the passages overturned as they stood, under a *Partially superseded by* top line:
  - **DEC-010's refusal of a ramp** in its rejected alternative "Roles named by a place". Its reason still holds of roles: the two roles the steps spread between are written in the foundations, and a step is no role (point 1).
  - **DEC-028's statement that the model of colour stays,** in its Rationale, and its rejected alternative "The order's colour in the engine's model". Of that alternative's two reasons, the engine still judges no page's point (point 3). The other, that content can point an order's parts at a role, still holds, but no role gives a ramp, so it does not meet the need.

## Rationale

**Why an order takes steps apart from the families.** In Jacques Bertin's visual variables (*Sémiologie graphique*, 1967), hue is selective and lightness is ordered: the eye splits five hues into five groups, and reads five lightnesses as a sequence. A picture shows the facts of its data and no others, by Jock Mackinlay's expressiveness (1986), so an order drawn in five hues shows five kinds and no sequence.

**Why two ends, spread over the list.** Two colours are the least that fix a ramp: which step stands out most, and how near the page the last one comes. Spread over the list, every order spans the whole ramp, whatever its length, as ColorBrewer's sequential schemes pick their colours again for each number of classes (Cynthia Brewer). The cost, accepted: the second item of a short list differs from that of a long one, and a long order's neighbours come closer. A page that shows an order compares places within one order.

**Why Oklab.** Oklab spaces lightness close to how the eye sees it (Björn Ottosson, 2020), so equal steps of it look near-equal and the middle needs no tuning. A straight line in it needs no rule for hue.

**Why the engine computes the steps, and their values come with the scene.** A renderer adds no colour of its own, and a need that recurs becomes a general tool of the engine (DEC-001 points 2 and 4), so every medium draws the steps the check measured. Which steps a piece draws depends on its lists, so they are no token of the brand, and the scene names only the roles and the share.

**Why the first end stands out most, measured from the background.** Which place of an order leads is what the content means, and switching the brand changes how a piece looks, never its content (DEC-001 point 5). So every brand puts the emphasis on the same end, and the first takes it, since the rest of an order follows from its source. What makes a step stand out is its distance from the page, not its darkness, as Material's primary colour is darker than the page in a light scheme and lighter in a dark one. One rule on the distance holds in every mode, where an inverted ramp would sink the source into a dark page.

**Why one text, on one side of both ends.** A text that differed by step would add a difference the order lacks. A text holding 4.5 to 1 on two ends it lies between is a middle grey between a near-black end and a near-white one, which some step between meets. Refused in the brand, that fault is its owner's to mend once. A brand cannot know how many places its pieces draw, so its check holds the ends, and a piece's check each step. Between ends of far hues, or after gamut mapping, a step may still fail where both ends pass, and the piece's check finds it where it is drawn.

**Why only a place takes a step, and an item's concept still comes first.** A concept, a component's own family and a state say what a thing is, or how it stands, so a step among them would show an order where there is none. A brand tunes and checks its ends for steps alone (point 2), so a library that painted with them elsewhere would paint with colours nothing checked for that use. This record changes how a place takes its colour, not how an item does. So on a page whose point is an order, an item that names a concept still takes its concept's colour, and a hue among the steps breaks the chain, which RS-GRAPHIC-007 asks against. Its author names no such concept there, or chooses no steps.

**Why the defaults, and the fall-back without the roles.** The neutral family's pairs already hold in every brand, and it marks no kind, so a brand that gives no ends adds neither a difference nor a meaning its owner never chose (DEC-008 point 2). A library names the foundations by major alone (DEC-001 point 5), so a piece may lock a pattern that gives the steps with foundations older than the roles. Its places then fall back as any place with no family does, and no rule of which versions fit together is needed.

### Alternatives considered

- **A ramp for each family of kinds,** as Material keeps a tonal palette for each key colour. Rejected: each family would need its own ends, and a page whose point is an order needs its order shown, not its kinds.
- **A full set of stops for each mode.** Rejected: three times the colours to tune, for a middle no page needed.
- **One colour a brand gives, from which the engine derives the rest.** Rejected: nobody chooses the light end, and the derived end can fail its text.
- **Steps spread in sRGB's values, or in OKLCH.** Rejected: equal steps of sRGB do not look equal, and OKLCH needs a rule for hue, which a grey lacks.
- **Steps of a pattern's own library.** Rejected: a brand gives a library's roles values only where it names that library (DEC-008 point 4), and every library that draws an order needs them.
- **A step's line in the order's text.** Rejected: a part painted from its family's line would show the text's colour, not the step.
- **The roles under a top group of their own,** such as `order.first`. Rejected: a new top group breaks the foundations (DEC-004 point 5). The group of the families takes `order` as a name no family may take.
- **A pair of each end against the background, at 3 to 1.** Rejected: an order's shade is a second sign of what position shows, so WCAG 1.4.11 asks no such contrast of it.
- **The steps in the document of a brand's resolved values, or spread by a renderer.** Rejected: a code writer writes that document out, so one piece's steps would leave the capability as a brand's code, and a renderer adds no colour of its own.

## Implications

### Edits to accepted records

Each is made once a person accepts this record, in the change that proposes it, and accepting this record accepts them ([COR-066](../../../decisions/core/COR-066-accepted-before-landing.md) point 5). Each edit ends with a pointer to this record and the point it names, in the form the accepted records use. Below, a point in brackets is this record's. The findings of point 7 stay this record's.

- **The founding record (DEC-001), point 6,** gains a bullet (points 3 and 6): "**An order's steps.** A pattern may give an order's places steps that the engine spreads from two ends a brand gives, in place of a family for each place. A step stands in for a place's family. No concept, component or state names a role of an order, and no part of a component paints with one by its name."
- **The record of brands and notations (DEC-004):**
  - Point 8 gains a bullet (point 2): "**An order's ends.** The order's text on each of its two ends is a declared pair, and the text is lighter than both ends, or darker than both. In every combination, the first end stands at least as far from the background as the last end, by WCAG's ratio."
  - Point 10 gains a bullet (points 1 and 6): "**An order's roles.** The foundations also declare an order's two ends and its text, apart from the families a notation maps to, and which end is the first. No concept maps to a role of an order." Its Implications' first bullet names these among what the foundations declare.
- **The record of the engine and its plugins (DEC-005):**
  - Its plain terms and its Decision name, among the engine's tools, the spread of an order's steps between two colours (point 4). Its plain terms' sentence on the one document of values adds that a step of an order comes with the scene instead (point 5).
  - Point 5's bullet "Values stay roles" reads (point 5): "**Values stay roles.** Each value that moves nothing, such as a colour or a picture, names its role, or, for a step of an order, the two roles it is spread between and its place's share of the way, the same in every mode. A role's value comes from the document of point 7, and a step's with the scene (point 6), so one scene serves every mode of the value axes. So the variants of one picture in one scene share one pixel size, and the same exposed points at the same places." Its bullet on an image names a tint by a step of an order beside a tint by role.
  - Point 6's sentence "The values of every combination named come with each scene" reads (point 5): "The values of every combination named come with each scene, a value for each step of an order among them, which the engine spreads from its two roles' values at the scene's size."
  - Point 7's bullet "Who reads it" says that a renderer takes each step's value among the values that come with each scene, computed for that scene and never from this document, and its Rationale "Why the engine owns the resolved values" that a step, which depends on a piece's lists, reaches renderers alone (point 5).
- **The record of library role defaults (DEC-008),** point 3, gains after its bullet "A component token's default" (point 6): "**Never a role of an order.** No default of a library's own role, or of a component token, aliases a role of an order."
- **The record of a list's fields (DEC-010):**
  - Point 6 gains, after its bullet "A family for each place" (points 3 and 4): "**An order's steps, spread from two ends.** A pattern may give a list's places the steps of an order instead, under a word of an option. The engine spreads the brand's two ends evenly over the places the list draws, from the first end at the first place to the last end at the last. That is the one colour computed from a place, and no role's name is computed from one."
  - Point 7's bullet "Not breaking" names, beside a change of the family a place takes, a change of whether a place takes a step (point 8).
  - **Its top line** (point 8) reads *Partially superseded by* [visual-communication:DEC-032-ordered-colour-steps], in the shape of the top line of the record of change over time (DEC-003). Overturned: its rejected alternative "Roles named by a place", so far as its example refuses a ramp from a first level's role to the last's. The rest stands, and that alternative stays as it stood.
- **The record of an HTML page's modes (DEC-023), point 3,** its bullet "One custom property for each colour role the file paints", gains (point 5): "Each step of an order the file paints takes a custom property of its own too, under a name no role's spelling by the CSS writer can take. Its value in each mode is the step's, which comes with the scene."
- **The record of the principles of visual communication (DEC-028):**
  - **Its top line** (point 8) reads *Partially superseded by* [visual-communication:DEC-032-ordered-colour-steps], in the same shape. Overturned: in the Rationale's paragraph "Why the form rule narrows a reason, and leaves the model", the sentence "A change to how the engine resolves colour would rest on a judgement the engine cannot make: what a page's point is", and that the model stays, in its heading and its last sentence. Also overturned: the rejected alternative "The order's colour in the engine's model". The rule's narrowing of the principle stands, as does the rest, and those passages stay as they stood.
  - Point 11's sentence "Colour roles that step in an order are a later refinement of the record of brands and notations" reads "An order's colour steps are a later record's, which adds the two ends they spread between to the record of brands and notations." In its Implications' "Left to other records", "the colour roles that step in an order" reads "the colour steps of an order". Each takes a forward refinement pointer to this record.
  - **Its rule RS-GRAPHIC-007's "From the text"** reads (point 3): "on a page whose point is an order, whether the content points the parts that show the order at one role, or gives their list the steps of an order with no item naming a concept, rather than each at its concept's." The rule's anchors gain this record's point 3. The edit adds a way to meet the rule and tightens none, so the set takes no new major (COR-051 point 7).

### Tasks and what is left

- **The Tasks it implies** lie under the Feature of the deck's redesign ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)): the foundations' three roles, their declaration of the ends and their checks; the engine's spread, tested against fixed values on more than one platform, a step's values with the scene and the seam's version, with the renderers that read them; and the design of the starter's patterns and of the neutral brand's ends. The neutral brand gives its ends before, or with, any starter pattern that makes the steps its default, since without them every place of such a list draws alike.
- **Left open:**
  - how one item shows both the concept it names and its step. A split of an item's family member by member, or content pointing a part at its own place's step, changes how an item takes its colour (DEC-001 point 6), so it comes as a record of its own.
  - the other principles every shipped brand follows, as DEC-028 leaves them
  - an order whose emphasis falls on its last place, or whose source is drawn last, which content would choose by a word of its own, never a brand by its ends; and an order continued over two lists
  - a picture a producer makes, or a live view, that must match a step. Only the ends reach them, so each would spread them by this record's rule.
  - steps for a quantity, such as a heat map's
- **Revisit this record** if a brand needs to tune the middle of its ramp.
