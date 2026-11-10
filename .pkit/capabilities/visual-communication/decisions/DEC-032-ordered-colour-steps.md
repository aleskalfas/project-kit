---
id: DEC-032
title: An order's places take colour steps, spread evenly between two ends each brand gives
status: accepted
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where a list's items stand in an order, as a stack's layers do, a pattern may shade each item by its place, where the content asks or by its default. A brand gives each mode two colours, one for the order's first item and one for its last, and one text colour for every shade. The engine spreads the two evenly over the list, whatever its length: a stack of three layers, for example, takes the first colour, the colour halfway and the last. An item that names a concept keeps its concept's colour.

## Context

No colour family steps in an order, and a brand cannot give a ramp of one hue without taking the families notations map to ([project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576)). The redesign of the showcase deck, the deck of the repository the capability is authored in, needs one: its first page stacks five levels, each carrying out the ones above it ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)). Two accepted records stand in the way:
- **The record of a list's fields** refused roles named by a place, a ramp among its examples ([visual-communication:DEC-010-list-item-fields], Alternatives considered).
- **The record of the principles of visual communication** keeps the engine's model of colour, rejects an order's colour in it, and leaves colour roles that step in an order to a later record ([visual-communication:DEC-028-principles-of-visual-communication] point 11, Rationale and Alternatives considered).

Whoever maintains the capability chose, on 9 November 2026, that a record decides a method, never a design element ([project-kit#2896](https://github.com/aleskalfas/project-kit/issues/2896)). So this record decides neither how a library draws the steps nor which colours a brand gives.

Terms:
- An *order* is a list whose items stand in a sequence the content means, such as a stack's levels. Its *source* is its first item, the one the rest follow from, such as the level every other carries out.
- An order's *ends* are the two colours a brand gives it in each combination of its modes: the *first end*, which its first place takes, and the *last end*, which its last place takes.
- A *step* is the colour an order gives one of its places (point 4).
- A *colour family* is a fill, a line and a text on the fill, whose text reaches WCAG's level for text in every combination of the modes. The foundations declare the families, and a notation maps each concept to one ([visual-communication:DEC-004-brands-and-notations] points 8 and 10).
- A *place* is an item's position among the items its list draws. A pattern may give each place a family in its data, which an item takes after its concept's and a state's, and before its item component's (DEC-010 point 6, [visual-communication:DEC-001-visual-communication-discipline] point 6).
- A scene names a role for each colour it holds, and takes each role's value from the engine's *document of a brand's resolved values*, so one scene serves every mode ([visual-communication:DEC-005-engine-and-plugins] points 5 and 7).

## Decision

**An order's places may take colour steps, spread evenly between two ends each brand gives.**

### 1. A brand gives two ends and a text, as three shared roles

- **Three roles.** The foundations declare `family.order.first`, the first end, `family.order.last`, the last end, and `family.order.text`, the text on every step. Each has a value under every brand in every combination of its modes, given or from its default, and a brand exports them as every shared role (DEC-004 point 5).
- **Declared, never read from a name.** The foundations alone declare, as data, which role is the first end and which the last, and the engine and the checks read the ends from that.
- **In the group of the families, apart from them.** The roles lie in the top group that holds every family's roles, so they add no top group, and a base that opens that group opens them too (DEC-004 points 5 and 6). They form no family, and no family takes the name `order`.
- **Defaults.** Both ends default to the fill of the neutral family, the foundations' family that marks no kind by a hue, and the text to its text. So a brand that gives no ends, as every brand released before the roles, draws every step alike, as that family.
- **The steps between are no role,** and no brand, library or content names one.

### 2. What every brand's ends hold

In every combination of the axes that change a colour (DEC-004 point 8):
- **The text on both ends.** The foundations declare the order's text on each end as a pair at the level for text, 4.5 to 1 (WCAG 1.4.3). A piece's check measures each text on a step as drawn, as every drawn text.
- **The text on one side of both ends.** The order's text is lighter than both ends, or darker than both, by WCAG's relative luminance.
- **The first end stands out most.** The first end contrasts with the page's ground, the shared role the foundations declare for it, at least as much as the last end does, by WCAG's ratio, an end with alpha measured over it. Equal ends pass. Nothing is promised against another fill an order lies on, such as a surface.

### 3. A pattern gives an order's places their steps, under a word

- **Under a word of an option** that switches its places' families (DEC-010 point 6). A person chooses it, the content's author by the word or the pattern's owner by its default, and the engine never does.
- **One list.** Each word gives the steps to one list the pattern repeats, and the pattern then names no family for any place of it.
- **Every item counts,** an item that names its own component included, and places count from the first item the list draws. So content that ends an order with something outside it places that outside the list, and lists the source first.
- **A step stands in for a place's family,** wherever a family goes, so an item's concept, and a state that gives a family, still come before it (DEC-001 point 6). An outer item passes its step to what sits in it, where nothing nearer gives a family (DEC-010 point 6).
- **Never the order's only sign.** The pattern also shows the order by position, and by size, numbers or arrows where its form has them.
- **Shown by the list's default item component.** A pattern that offers the steps names, for that list, a default item component that paints its fill from its family, the fill the order's text is checked on (point 2). No check judges this or the order's other signs: the pattern's owner does, in review, as for a default ([visual-communication:DEC-008-library-role-defaults] point 2).
- **Without the roles, no step.** Under foundations that declare no ends, a place takes no step, and its item goes on to its item component's family, as at a place past those a pattern names (DEC-010 point 6).

### 4. The engine spreads the steps evenly, in Oklab

- **Evenly over the places drawn.** Where a list draws n places, place k takes the colour (k − 1) / (n − 1) of the way from the first end to the last, and a list of one place takes the first end. The engine spreads each combination's own ends, at the scene's size.
- **In Oklab,** along the straight line between the ends. Under one release, the same files give the same steps on every machine (DEC-005 point 5).
- **A step paints as a family.** Its fill and line are its colour, and its text is the order's text. An item component paints a step with the members it paints any family with.
- **One general tool,** built and tested once (DEC-001 point 4), and the one colour the engine computes from a place.

### 5. A step's values travel with the scene

- **The scene names a step by its ends:** the two roles it is spread between, and its place's share of the way, the same in every mode (DEC-005 point 5).
- **Its values come with the scene.** The engine computes a step's value in each combination named, and hands them among the values that come with each scene (DEC-005 point 6). A renderer takes each step's value from them, and spreads nothing.
- **The document of a brand's resolved values holds no step** (DEC-005 point 7).
- **The seam's version rises** (DEC-005 point 8).

### 6. Only a place takes a step

- **Never where a family is named.** A notation's concept, a component's own family, a state's family and a pattern's family for a place each name a family, never a role of an order.
- **Never by its name in a library.** No part of a component paints with a role of an order by its name, and no library's own role or component token aliases one as its default.
- **Content may point a part at one,** as at any role (DEC-001 point 6), such as a legend's swatch of the first end.

### 7. What the checks fail

Each finding lies where the record of files and validation puts it ([visual-communication:DEC-002-files-and-validation] point 7):
- in a brand, in some combination: a breach of point 2's "The text on one side of both ends" or "The first end stands out most". The order's text below its level on an end already fails as a declared pair (DEC-004 point 11).
- in a library other than the foundations: a declaration of an order's ends
- in a notation, a component, a state, a pattern or a library's roles: a breach of point 6
- in a pattern: a list given the steps by a word that also names a family for some place of it

Stated as a fact, at a piece's lock: a list that takes the steps by its word, under foundations that declare no ends (point 3).

### 8. What it adds, and what it overturns

- **The foundations gain three roles with defaults,** which break nothing, so they take a minor version ([visual-communication:DEC-013-shipped-library-releases] point 3). The schemas of a library's roles and of a pattern grow by additions every file written before still meets ([visual-communication:DEC-003-change-over-time] point 3), so no migration is owed (COR-010).
- **Every brand draws every piece as before,** except where a list takes the steps. A release that makes the steps a pattern's default breaks nothing (DEC-003 point 6, DEC-010 point 7).
- **A pattern's owner audits its own item components on the steps** before a release that makes them its default. An item component of another library, which content or an item names, is its draft's author's to catch at render, as any change of look is (DEC-001 point 7).
- **Two accepted records are overturned in part.** Each stays accepted, with the passages overturned as they stood:
  - DEC-010's rejected alternative "Roles named by a place", so far as its example refuses a ramp from a first level's role to the last's.
  - DEC-028's Rationale paragraph "Why the form rule narrows a reason, and leaves the model": its sentence "A change to how the engine resolves colour would rest on a judgement the engine cannot make: what a page's point is", and that the model stays, in its heading and its last sentence. Also DEC-028's rejected alternative "The order's colour in the engine's model". The rule's narrowing of the principle stands, as does the rest.

## Rationale

**Point 1, two ends apart from the families.** In Jacques Bertin's visual variables (*Sémiologie graphique*, 1967), hue is selective and lightness is ordered: the eye splits five hues into five groups, and reads five lightnesses as a sequence. A picture shows the facts of its data and no others, by Jock Mackinlay's expressiveness (1986), so an order drawn in five hues shows five kinds and no sequence. Two colours are the least that fix a ramp: which step stands out most, and how near the page the last one comes.

**Point 1, declared, with defaults.** A name is a word for readers, whose shape the naming rule fixes and nothing it means (DEC-004 point 4). A shared role added to the released foundations carries a default that aliases an older role (DEC-004 point 7, DEC-008 point 2). The neutral family's pairs already hold in every brand, and it marks no kind, so a brand that gives no ends adds neither a difference nor a meaning its owner never chose.

**Point 2, the first end.** Which place of an order leads is what the content means, and switching the brand changes how a piece looks, never its content (DEC-001 point 5). So every brand puts the emphasis on the same end, and the first takes it, since the rest of an order follows from its source. What makes a step stand out is its distance from the page, not its darkness, as Material Design's primary colour is darker than the page in a light scheme and lighter in a dark one. So one rule on the distance holds in every mode, where an inverted ramp would sink the source into a dark page.

**Point 2, one text on one side.** A text that differed by step would add a difference the order lacks. A text holding 4.5 to 1 on two ends it lies between is a middle grey between a near-black end and a near-white one, which some step between meets, so the brand refuses it and its owner mends it once. A brand's check cannot know how many places its pieces draw. Between ends of far hues, or after gamut mapping, a step may still fail where both ends pass, and the piece's check finds it where it is drawn.

**Point 3, chosen by a person.** Whether a list shows an order is a page's point, which the engine cannot judge. Shades collapse under forced colours. This record changes how a place takes its colour, not how an item does. The cost: a concept's hue among the steps breaks the chain RS-GRAPHIC-007 asks for, so the author of a page whose point is an order names no concept there, or chooses no steps.

**Point 3, without the roles.** A library names the foundations by major alone (DEC-001 point 5), so a piece may lock a pattern that gives the steps with foundations older than the roles, and a fall-back needs no rule of which versions fit together.

**Point 4, an even spread.** Spread over the list, every order spans the whole ramp, whatever its length, as ColorBrewer's sequential schemes pick their colours again for each number of classes (Cynthia Brewer). The cost, accepted: the second item of a short list differs from that of a long one, and a long order's neighbours come closer. A page that shows an order compares places within one order.

**Point 4, in Oklab, by the engine.** Oklab spaces lightness close to how the eye sees it (Björn Ottosson, 2020), so equal steps of it look near-equal and the middle needs no tuning. A straight line in it needs no rule for hue. A need that recurs becomes a general tool of the engine (DEC-001 point 4), so every medium draws the steps the check measured.

**Point 5, values with the scene.** Which steps a piece draws depends on its lists, so they are no token of the brand. A renderer reads a new kind of value.

**Point 6, only a place.** A concept, a component's own family and a state say what a thing is, or how it stands, so a step among them would show an order where there is none. A brand tunes and checks its ends for steps alone (point 2), so a library that painted with them elsewhere would paint with colours nothing checked for that use.

**Point 8, what it adds and overturns.** A release that makes the steps a default changes only how a pattern's places look, as a change of a place's family does, and leaves every concept's colour. A step may lie far in lightness from every family's fill, so a part that keeps its contrast on every family may fail on a step, measured as drawn. DEC-010's reason still holds of roles, since the two roles the steps spread between are written in the foundations, and a step is no role (point 1). Of the two reasons of DEC-028's rejected alternative, the engine still judges no page's point (point 3), and content can still point an order's parts at a role, but no role gives a ramp, so that does not meet the need.

### Alternatives considered

- **A ramp for each family of kinds,** as Material Design keeps a tonal palette for each key colour: each family would need its own ends, and a page whose point is an order needs its order shown, not its kinds.
- **A full set of stops for each mode:** three times the colours to tune, for a middle no page needed.
- **One colour a brand gives, from which the engine derives the rest:** nobody chooses the light end, and the derived end can fail its text.
- **Steps spread in sRGB's values, or in OKLCH:** equal steps of sRGB do not look equal, and OKLCH needs a rule for hue, which a grey lacks.
- **Steps of a pattern's own library:** a brand gives a library's roles values only where it names that library (DEC-008 point 4), and every library that draws an order needs them.
- **A step's line in the order's text:** a part painted from its family's line would show the text's colour, not the step.
- **The roles under a top group of their own,** such as `order.first`: a new top group breaks the foundations (DEC-004 point 5).
- **A pair of each end against the background, at 3 to 1:** an order's shade is a second sign of what position shows, so WCAG 1.4.11 asks no such contrast of it.
- **The steps in the document of a brand's resolved values, or spread by a renderer:** a code writer writes that document out, so one piece's steps would leave the capability as a brand's code, and a renderer adds no colour of its own (DEC-001 point 2).

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each ending with a pointer to this record and the point it names. A bare point below is this record's. Accepting this record accepts them ([COR-066](../../../decisions/core/COR-066-accepted-before-landing.md) point 5). The findings of point 7 stay this record's.
  - DEC-001 point 6 gains a bullet, "An order's steps": a pattern may give an order's places steps in place of their families, and only a place takes one (points 3 and 6).
  - DEC-004 point 8 gains a bullet, "An order's ends", holding point 2's rules on the order's text and its ends.
  - DEC-004 point 10 gains a bullet, "An order's roles": the foundations declare an order's two ends, its text and which end is the first, apart from the families, and no concept maps to them (points 1 and 6). Its Implications' first bullet names them among what the foundations declare.
  - DEC-005's plain terms and the lead of its Decision name the spread of an order's steps among the engine's tools (point 4). Its plain terms' sentence on the one document of values adds that a step comes with the scene instead (point 5).
  - DEC-005 point 5, "Values stay roles", comes to name a step as the scene names it, its value coming with the scene (point 5). Its bullet on an image names a tint by a step beside a tint by role.
  - DEC-005 point 6's sentence "The values of every combination named come with each scene" adds a value for each step, spread by the engine at the scene's size (point 5).
  - DEC-005 point 7, "Who reads it", comes to say a renderer takes each step's value with the scene, never from that document (point 5). Its Rationale "Why the engine owns the resolved values" adds that a step, which depends on a piece's lists, reaches renderers alone.
  - DEC-008 point 3 gains, after its bullet "A component token's default", a bullet "Never a role of an order", holding point 6's rule on defaults.
  - DEC-010 point 6 gains, after its bullet "A family for each place", a bullet "An order's steps, spread from two ends": under a word of an option, the brand's ends spread evenly over the places a list draws, the one colour computed from a place, while no role's name is computed from one (points 3 and 4).
  - DEC-010 point 7, "Not breaking", names a change of whether a place takes a step beside a change of the family it takes (point 8).
  - DEC-010's and DEC-028's top lines read *Partially superseded by* [visual-communication:DEC-032-ordered-colour-steps], in the shape of DEC-003's, over the passages point 8 names.
  - [visual-communication:DEC-023-html-page-modes] point 3, "One custom property for each colour role the file paints", gains one for each step the file paints (point 5). Its name is one no role's spelling by the CSS writer can take, and its value in each mode comes with the scene.
  - DEC-028 point 11's sentence on colour roles that step in an order comes to say that an order's colour steps are a later record's, which adds their two ends to the record of brands and notations. Its Implications' "Left to other records" names "the colour steps of an order" in place of "the colour roles that step in an order". Each takes a forward refinement pointer to this record.
  - In the GRAPHIC rule set (`rule-sets/graphic.md`), RS-GRAPHIC-007's "From the text" comes to accept a list given the steps, with no item naming a concept, on a page whose point is an order (point 3). Its anchors gain point 3. The edit adds a way to meet the rule and tightens none, so the set moves from 1.0.0 to 1.1.0 (COR-051 point 7).
- **The Tasks that build it,** under the Feature of the deck's redesign ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)), each writing on the capability's pages what it builds:
  - the foundations' roles and their checks
  - the engine's spread, with the renderers that read it
  - the design of the starter's patterns and of the neutral brand's ends
- **Left open:**
  - how one item shows both the concept it names and its step, which changes how an item takes its colour (DEC-001 point 6) and so needs a record of its own
  - the other principles every shipped brand follows, as DEC-028 leaves them
  - an order whose emphasis falls on its last place, or whose source is drawn last, which content would choose by a word of its own, never a brand by its ends
  - an order continued over two lists
  - a picture a producer makes, or a live view, that must match a step: only the ends reach them, so each would spread them as the engine does
  - steps for a quantity, such as a heat map's
- **Revisit this record** if a brand needs to tune the middle of its ramp.
