---
id: DEC-032
title: An order's first five places take five colour steps, which each brand gives
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the foundations declare five shared colour families that step in an order, and each brand gives them its values. Each step has a fill, a line and a text on the fill. The text holds the contrast body text needs, in every mode. The first step stands furthest from the page's background, so in a dark mode it is the lightest, not the darkest. A pattern may offer the steps under a word of one of its options. Where the content chooses that word, the pattern's first five places take the five steps, in order. A step shows where an item stands in an order, so no concept, component or state names one. An item that names a concept keeps its concept's colour, since today that colour is a concept's only mark. A brand that gives no steps draws each in its neutral family. The neutral brand's steps take its text colour's hue, and that colour is a grey, so its steps are grey.

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

What is missing for an order is a family that steps. Each family is one colour for one kind. No brand can give five ordered steps of one hue without taking the families notations map their concepts to. The engine draws one family for a whole list today. The starter lists a colour for each place among what it lacks ([project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576)).

The redesign of the showcase deck of the repository the capability is authored in needs it ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)). Its first page stacks five levels, from decisions down to code, and its lead says each level carries out the ones above it. In the seventh round of the redesign's drafts, which its critic passed:
- **The levels step in one ramp,** darkest at the source in light mode and lightest at the source in dark mode. They name no concept.
- **One text colour on every step** of a mode, the page's own background. White holds 5.06 to 1 on the lightest light step, and 14.5 on the darkest.
- **The lightness steps evenly,** in OKLCH from .28 to .54 in light mode and from .90 to .64 in dark mode. Its hue is that of the slate the round gives its text.
- **The design's reason:** lightness is the ordered variable, and a ramp of one hue says "one chain". The deck's one accent then keeps its one meaning.

The capability's rule sets are being written beside this record ([project-kit#2884](https://github.com/aleskalfas/project-kit/issues/2884)). One of their rules asks that a picture's differences be those its content has. On a page whose point is an order, the parts that show the order share one colour, or step in one shade.

Two rules bound how shared roles are added:
- **The foundations are released,** so a shared role added now carries a default that aliases an older role (DEC-004 point 7, [visual-communication:DEC-008-library-role-defaults] point 2).
- **A new top group of the shared roles** is a breaking change of the foundations, even where each of its roles has a default (DEC-004 point 5).

Five terms:
- An *order* is a list whose items stand in a sequence the content means. Examples are levels that each rest on the next, and the steps of a flow.
- Its *source* is the end it runs from, such as the level every other carries out, or a flow's first step.
- A *page whose point is an order* is a page that is there mainly to show the order its items stand in.
- The *families of kinds* are the colour families a notation maps a concept to: the neutral one and the five hues.
- A *step* is one of the colour families a brand gives for a place in an order.

## Decision

**The foundations declare five steps, in a sequence, each a colour family of a fill, a line and a text. A step is a family that only a place takes, or a part the content points at. A brand gives each step its values. In every combination of its modes, each step's text holds WCAG's level for text on its fill, and each step stands at least as far from the background as the next. A pattern may offer the steps under a word of an option, which gives its first five places the steps in their sequence. A concept still comes before a place. Each step defaults to the neutral family. The neutral brand's steps take its text colour's hue.**

### 1. Five steps, in a sequence, each a colour family

- **Five, the same for every brand.** The foundations declare the steps `order-1` to `order-5` as a sequence, from the source to the end. The checks read the order from that sequence, never from a name.
- **Each a family of three members.** A step has a `fill`, a `line` and a `text` on the fill, the members the foundations' families have. Each member is a shared colour role, `family.order-<n>.<member>`, such as `family.order-1.fill`. An item component paints a step with the members it paints any family with.
- **In the group of the families.** The roles lie in the top group that holds every family's roles, so the steps add no top group (DEC-004 point 5). No library or brand can hold a name there. The check refuses a brand's own token in a group of the shared roles, and no library takes a top group's name (DEC-004 point 7).
- **Apart from the families of kinds.** The foundations declare the steps apart from them, and no family shares a name with a step.
- **Public names.** A brand exports the steps as it exports every shared role (DEC-004 point 5).

### 2. What a brand gives, and the contrast each step holds

- **A value for each member of each step,** in every combination of its modes, as for every shared role. A member a brand leaves out takes the neutral family's, which rarely holds on the fill the brand gives. A brand that gives a step's fill and not its text then fails that step's pair.
- **A default where it gives none.** Each member defaults to the same member of the neutral family: `family.order-<n>.fill` to `family.neutral.fill`, and so for the line and the text. So every brand released before the steps still draws, and draws each step as its neutral family.
- **Text on its fill, at WCAG's level for text.** The foundations declare each step's text on its fill as a pair at the level `text`, 4.5 to 1 (WCAG 1.4.3). It is checked in every combination of the axes that change a colour, as every pair is (DEC-004 point 8). At the defaults, each such pair falls on the neutral family's own, which every brand already holds.
- **No pair of a step's fill against the background.** No family carries one, and a step is a family. The order never rests on its shade alone (point 4). So a step's fill is not a graphic a reader needs to understand the order, which WCAG 1.4.11 asks 3 to 1 of. A brand may hold its steps to 3 to 1 against the background, as the neutral brand does (point 7).
- **A fill may be dark in a light mode,** where every other family's fill is pale. A part that an item component paints in a fixed role over its family's fill may then fail on a step. The contrast as drawn finds it (DEC-004 point 8).

### 3. The source stands out most, in every mode

- **Measured against the background.** Each step's fill contrasts with the page's background, a shared role, at least as much as the next step's fill does. That holds in every combination of the axes that change a colour. The contrast is WCAG's ratio, as the pairs measure it. So the first step stands furthest from the page, and the last nearest.
- **So a dark mode gives its steps the other way round.** On a light background the first step is the darkest. On a dark one it is the lightest. A brand gives each mode its own values. It never inverts one mode's ramp for another, which would sink the source into a dark page.
- **Equal steps pass.** A brand may draw two steps alike, or all five, as its defaults do, or as a mode of high contrast might. The order then shows by its other signs alone (point 4).
- **A background of a middle tone** may have steps on both sides of it. The rule still holds, and the brand judges the look.
- **Against the background alone.** Nothing is promised against another fill an order may lie on, such as a surface.

### 4. A pattern may give the first five places of an order their steps

- **Under a word of an option.** A pattern may offer the steps under a word of an option it declares, which switches its places' families (DEC-010 point 6). The content chooses that word where the page's point is the order. A pattern's owner may make it the option's default, where the pattern's job is an order. Content then chooses another word where its point is elsewhere.
- **As the families of its places.** Under that word, the pattern gives its places the steps, in its data, as the record of a list's fields lets it give a place a family (DEC-010 point 6). The first place takes the first step of the sequence, the second the second, and so up to the fifth.
- **From the first, one to a place, and nothing else.** A word that gives steps gives them from the first, one to each place, none skipped or given twice. It gives no place one of the families of kinds beside them. One family for every place of a list is never a step. So a place takes the same step in every order, and two orders compare place by place.
- **The source is drawn first.** A place counts from the first item the list draws (DEC-010 point 6), so the content lists the source first.
- **Past the fifth place,** an item takes no step. It takes its item component's family, as a place past those a pattern names does (DEC-010 point 6). The check asks the piece's author for attention, who may split the list, or draw it unshaded.
- **It shows where the item paints from its family.** An item component may paint its fill in a fixed role, such as a card on the surface. It then shows the step only in the parts it paints from its family, such as the card's bar. A pattern that offers the steps names a default item component that paints its fill from its family. Its option chooses only its places' families, never the item's look, which is the item component's (DEC-001 point 6).
- **Never the order's only sign.** A pattern that shades by place also shows the order by position, and by size, numbers or arrows where its form has them. Shades collapse under forced colours, and on a projector that washes them out.

### 5. A step reaches an item only through a place, or where the content points a part at it

- **A step shows where an item stands in an order,** as a place's family does when a pyramid with no notation shades its levels (DEC-001, Rationale). It never says what a thing is, or what state it is in. Named in a structure, it would become one more colour of a palette, in every brand.
- **What names one of the families of kinds names no step:** a notation's concept, a component's own default family and a state's family. A step named there is refused, as any name that is no such family is.
- **What takes either.** A pattern's place takes one of the families of kinds or a step, so a pattern whose places are no order still gives them families of kinds. A paint from the item's family paints from either.
- **Never by its name in a structure.** A part of a component never paints with a step's role by its name. No library's own role, and no component token, aliases a step's role as its default.
- **A brand's aliases run either way.** A brand may give a step's role an alias to another of its tokens, or give another role an alias to a step's. Its values are its own. A role means what the structure that reads it says, wherever its value comes from.
- **Content may point a part at a step's role,** as it may point a part at any role (DEC-001 point 6). Its author then says that the part shows a place.

### 6. A concept still comes before a place

- **The order stands** as the founding record and the record of a list's fields set it. An item's family is its concept's, else its place's, else its item component's, else that of the component it sits in. A state may change it (DEC-001 point 6, DEC-010 point 6).
- **So an item that names a concept keeps its concept's family,** where its place offers a step. Content may still point the parts that show the order at the step's roles (point 5).
- **A place before a concept** waits for a concept's mark of its own, such as its icon ([project-kit#2576](https://github.com/aleskalfas/project-kit/issues/2576)). Until then, a step before the concept would take the concept's only colour from the item.

### 7. What the neutral brand gives

The neutral brand stays a brand to start from, so its steps carry no project's identity (COR-014; DEC-001 point 9).
- **One hue, its text colour's own.** The steps read as one chain, a deepening of the text, and claim no kind. Where the text colour has no hue, as a pure grey, the steps have none either.
- **Apart from the accent.** A step never takes the accent's colour. Where the text colour's hue lies near the accent's, the steps stay far below the accent's chroma, so the accent keeps its one meaning.
- **Near-even steps of perceived lightness,** as OKLCH's lightness gives them.
- **One text colour on every step of a mode: the background's own.** No step's text differs from another's, so the text adds no difference the order lacks. A step whose text holds 4.5 to 1 then stands 4.5 to 1 from the background as well.

### 8. What the checks report, and how severely

Each finding below lies where the record of files and validation puts it. It fails or asks for attention by that record's policy ([visual-communication:DEC-002-files-and-validation] point 7).
- **Fails validation:**
  - in a brand: a step's text below WCAG's level for text on its fill, in some combination, as every declared pair below its contrast fails (DEC-004 point 11);
  - in a brand: a step whose fill contrasts with the background more than the fill of the step before it, in some combination;
  - in a notation, a component or a state: a step where one of the families of kinds is named, as any name that is no such family is refused;
  - in a component: a part that paints with a step's role by its name, or a component token whose default is a step's role;
  - in a library's roles: an own role whose default is a step's role;
  - in a pattern: a word that gives its places steps otherwise than from the first, one to each place;
  - in a pattern: a word that gives one of the families of kinds beside the steps, or one step to every place.
- **Asks the piece's author for attention:** a list whose places take the steps, and that draws more than five items.

### 9. What this adds, and what still holds

- **The foundations gain fifteen shared roles, each with a default,** and the sequence of the steps, declared apart from the families of kinds. A role with a default breaks nothing (DEC-004 point 5), so the foundations take a minor version ([visual-communication:DEC-013-shipped-library-releases] point 3).
- **The format grows by an addition** that every file written before still meets ([visual-communication:DEC-003-change-over-time] point 3). The schema of the foundations' roles gains the sequence, which no other library declares, as it declares no family.
- **The engine gains no tool.** A family for each place is the record of a list's fields'. The steps are families, so an item paints them as it paints any family.
- **Every brand draws every piece as before.** A piece meets the steps only where a pattern gives them to its places. Under a brand that gives none, such a place draws in the neutral family. An item that names a concept keeps its concept's colour.
- **No file is renamed or removed,** and no project file changes shape, so no migration is owed (COR-010).

## Rationale

**Why an order takes steps of its own, apart from the families of kinds.** Jacques Bertin's visual variables tell the two apart (*Sémiologie graphique*, 1967). Hue is selective: the eye splits items of five hues into five groups. Lightness is ordered: the eye reads five lightnesses as a sequence. Jock Mackinlay's expressiveness asks that a picture show the facts of its data and no others (1986). An order drawn in five hues shows five kinds and no sequence. Kept apart, a step never says a kind, and a concept never says a place.

**Why five, the same for every brand.**
- **Enough for the orders a page shows,** such as the redesign's stack of five levels, or a flow of four or five steps. A longer order still shows by position and numbers, and the check points its author to a split.
- **Few enough to tune and to tell apart.** Each step is three more values a brand tunes in every combination of its modes. Each step added within the range the text pair allows also brings the neighbours closer. The redesign's five light steps stand about 1.3 to 1 apart, across 14.5 to 5.06 to 1 against white.
- **The same for every brand.** The names are public, so code outside the capability knows them, and the foundations declare their pairs. A count each brand chose would give neither.
- **Revisited** if a brand needs more (Implications).

**Why each step is a family, in a declared sequence.** An item component paints with its family's members. A step that lacked one, such as a line, would leave a card's bar unpainted, and reported. As families, the steps need no new way to paint, and the record of a list's fields gives them to places. The checks of points 3 and 4 read a sequence declared as data, never the names. So no role's name is computed from a place, which that record rejected (DEC-010, Alternatives considered).

**Why in the group of the families, and why defaults.** A new shared role needs a default, or a major release that every library and brand moves to on purpose (DEC-004 points 5 and 7). A new top group is a breaking change even with defaults. The group of the families exists, and the steps are families.

**Why the defaults are the neutral family.** A default is the fairest stand-in until a brand gives a value (DEC-008 point 2). The neutral family is the starter's own default for its blocks. So a brand that gives no steps draws an order's places in a family it already tuned. That adds no difference its owner never chose. Its pairs already hold, and the order shows by position.

**Why a text pair, and no pair of a fill against the background.** WCAG 1.4.3 asks 4.5 to 1 of body text on what lies under it, and an item's text lies on its step's fill. WCAG 1.4.11 asks 3 to 1 of a graphic a reader needs to understand the content, against the colours beside it. An order's shade is a second sign of what position already shows, so it is no such graphic. No family carries such a pair, and the neutral family's quiet fill would fail one at the defaults.

**Why measured from the background.** What makes a step stand out is its distance from the page, not its darkness.
- **Material's colour roles** take one tone of a tonal palette in a light scheme and another in a dark one. Its primary colour is tone 40 in light and tone 80 in dark, so the role keeps its emphasis in both. Its surface containers, from low to highest, step away from the surface's tone in both schemes. In light they darken from tone 96 to 90, and in dark they lighten from 10 to 22.
- **Carbon's colour tokens** name a layer by its place, and each theme gives each layer a value of its own. So a role named for its place takes a value for each mode.
- **One rule on the distance from the background** holds in each mode, high contrast included, with no rule for each scheme. An inverted ramp would put the darkest step at the source on a dark page, where it stands out least.

**Why the first five places, from the source.** The record of a list's fields writes a family for each place in the pattern (DEC-010 point 6). The steps fit it as they stand, and ask the engine for nothing. A place takes the same step in every order, so the second level of a short stack looks like the second level of a long one. A short order takes the steps that stand out most, which suits a page that shows few.

**Why past the fifth place an item takes its component's family.** It is the rule the record of a list's fields set for a place no pattern names (DEC-010 point 6). The other ways each add a difference the content lacks: steps given again read as a pair, and the rest on the last step read as a group. The page then shows a difference its content lacks, so the check asks the author to act.

**Why only a place takes a step.** A notation's concept, a component's own family and a state each say what a thing is, or how it stands. A step among them would show a place in an order where there is none. A step a component or a library's role names becomes one more colour of a palette, and the steps stop meaning an order. The content may point a part at a step, since there its author places the part.

**Why a concept still comes before a place.** Placed after the concept, the step would erase the concept's colour, and today that is a concept's only mark. Format 1 draws no concept's icon ([visual-communication:DEC-012-text-runs], Context). A run that names a concept paints its family's text, which suits that family's pale fill, not a dark step. The redesign needs no change of the order, since its levels name no concept. The founding record's own example is a pyramid with no notation that shades its levels by their place (DEC-001, Rationale).

**Why the neutral brand's ramp follows these principles.**
- **One hue.** Cynthia Brewer's single-hue sequential schemes step lightness in one hue, so the eye reads a sequence and no kinds.
- **Near-even lightness.** Oklab, whose cylindrical form is OKLCH, spaces lightness close to how the eye sees it (Björn Ottosson, 2020). So near-equal steps look near-equal.
- **The text colour's hue** reads as a deepening of the text, not as a brand's colour, so the neutral brand stays one to start from. Kept far below the accent's chroma, the steps leave the accent its one job.
- **The text in the background's colour** makes the pair and the distance from the page one measure. A step whose text holds 4.5 to 1 stands 4.5 to 1 from the page.
- **Why on the neutral brand alone.** Where one hue ends and another starts is a judgement no check makes. So the foundations do not hold a brand's steps off its accent, and a reviewer judges it.

### Alternatives considered

- **A ramp the engine derives from one colour a brand gives,** lighter and darker in OKLCH. Rejected. The engine would compute values, which only a brand holds (DEC-001 point 5). A brand may still derive its steps with any tool, as Material's theme builder derives tonal palettes, and hold the results as values.
- **A count each brand chooses.** Rejected (Rationale, "Why five, the same for every brand").
- **Three steps, or seven, or nine.** Not chosen, for the same reasons.
- **A ramp for each of the families of kinds,** as Material keeps a tonal palette for each key colour. Not chosen. Six families of five steps are ninety roles every brand tunes. A page whose point is an order needs its order shown.
- **Steps of a pattern's own library,** such as the starter's. Rejected. Each library that draws an order would declare its own. A brand gives them values only where it names that library (DEC-008 point 4). A meaning every library needs is a shared role's (DEC-008 point 2).
- **The steps under a top group of their own,** such as `order.1.fill`. Rejected. A new top group is a breaking change of the foundations (DEC-004 point 5).
- **No defaults, in a major release of the foundations.** Rejected. Every brand would give fifteen values before it read the new major, and every lock would move on purpose.
- **Defaults that alias the text colour and the background,** a solid block in the text's colour. Rejected. A brand that never chose it would draw an order as heavy blocks, an emphasis its owner never chose.
- **A pair of each step's fill against the background, at 3 to 1.** Rejected in the foundations (Rationale). The neutral brand holds it by its own principle (point 7).
- **Steps spread over the list by its length,** such as steps 1, 3 and 5 for three items. Not chosen. The engine would compute a family from the place and the count, which the record of a list's fields rejected (DEC-010, Alternatives considered). A place's shade would change with the list's length, so two orders could not be compared place by place. ColorBrewer picks its colours again for each number of classes, which a brand's five fixed steps cannot do.
- **Past the fifth place, every item on one step, or the last step repeated.** Not chosen. The first needs the same computed count. The second reads as a group the content lacks.
- **The step before the concept, now.** Not chosen (Rationale, "Why a concept still comes before a place"). It would take the only colour sign of each concept on a shaded item.
- **Content points each item's parts at its step,** with no family for each place. Kept for an item that names its concept (point 6), and not chosen as the way. Each item would carry its place in its content. An item inserted would leave every later one on the wrong step.
- **The steps as a component's own family, or a state's,** such as a block drawn solid in the first step. Rejected. The step would show a place in an order where there is none, and become a palette's colour.
- **The engine tells whether a page's point is an order.** Rejected. It cannot, so the content chooses it by a word.
- **A renderer mixes the steps,** such as with a colour mix in CSS. Rejected. A renderer adds no colour of its own (DEC-001 point 2).

## Implications

- **Edits to accepted records,** made once a person accepts this record, in the change that proposes it. Accepting this record accepts them (the decisions README, "The acceptance gate"). Each edit ends with a pointer to this record and the point it names, in the form the accepted records use.
  - **The founding record's point 6** gains a bullet: "An order's steps are colour families that only a place takes, or a part the content points at. No concept, component or state names one, and no part of a component names one's role" (point 5).
  - **The record of brands and notations' point 7** gains, beside its bullet on a component token's default: "No component token's default aliases a step's role" (point 5).
  - **Its point 8** gains a bullet: "Each step's text on its fill is a declared pair. In every combination, each step's fill stands at least as far from the background as the next" (points 2 and 3).
  - **Its point 10** gains a bullet: "The foundations also declare the five steps of an order, in a sequence, apart from the families a notation maps to. A pattern may give them to an order's places, and no concept maps to one" (points 1 and 5).
  - **Its point 11's list of what fails validation** gains "a brand's steps out of order against the background in some combination" (point 8). A step's text below its level already fails there as a declared pair.
  - **Its Implications' first bullet** names the order's steps among what the foundations declare.
  - **The record of library role defaults' point 3** gains a bullet: "No default of a library's own role, or of a component token, aliases a step's role." **Its point 9** fails such a default (point 5).
  - **The record of a list's fields' point 6,** "A family for each place", gains: "A pattern may offer the steps of an order under a word of an option. Under it, its places take the steps from the first, one to each place, with none of the families of kinds beside them. One family for a whole list is never a step" (point 4). **Its point 9** gains the pattern's finding and the finding that asks for attention, of this record's point 8.
  - **Its Alternatives considered,** "Roles named by a place", ends: "Steps of an order are not rejected here: a pattern writes them for each place in its data, and no step's name is computed from a place," with the pointer to this record (point 4). Its rejection then reads as one of a role's name computed from a place.
- **If the record of #2884 is accepted before this change lands,** this change makes three edits to it and to its rule:
  - **That record's point 11,** "What it leaves as it is", ends: "Colour roles that step in an order refine the record of brands and notations in" this record, cited by its id. That replaces its words "are a later refinement of the record of brands and notations".
  - **Its Implications' "Left to other records"** ends: "and the principles a shipped brand follows, refining the record of brands and notations", with its citation of that record. That replaces its words from "the colour roles that step in an order" to "both refining the record of brands and notations".
  - **Its rule RS-GRAPHIC-007,** "From the text", reads: "on a page whose point is an order, whether the content points the parts that show the order at one role, rather than each at its concept's. Or, where those items name no concept, whether their pattern gives their places the steps of an order." The rule's anchors gain this record's point 4. The change settles whether the edit moves the set's version, under the record of rule sets (COR-051 point 7).
- **The principles every shipped brand follows** stay to a later record refining the record of brands and notations, whichever change lands first. This record decides only the neutral brand's steps (point 7).
- **The Tasks it implies,** under the Feature of the deck's redesign ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)):
  - **The foundations:** the fifteen roles with their defaults, the sequence of the steps and their pairs, in a minor version. The schema of a library's roles gains the sequence, which the check refuses in any library but the foundations.
  - **The engine and the check:** a family for each place, which the record of a list's fields decided and the engine does not draw yet, and the findings of point 8.
  - **The starter:** each pattern that draws an order offers the steps by an option's word. Its default item component paints from its family (point 4). Its owner chooses the option's default word, judged in review as the starter's other choices are ([visual-communication:DEC-007-starter-library] point 3). Its reference drops a colour for each place from what it lacks. A library names its bases by major alone (DEC-001 point 5). So the Task decides which finding a piece meets that locks the starter with foundations older than the steps, and where it lies.
  - **The neutral brand:** the steps' values under point 7, in a minor version. Its values start from the seventh round's lightness steps, in its text colour's hue. A step's line is weighed there too. That round draws a block with no edge, while a card's bar paints the same member and is a mark.
  - **The capability's reference:** the foundations' roles, which names a component's family and a state's may take, how a pattern gives the steps, and the new findings, each on its page.
  - **The analysis's glossary:** an order, its source and a step.
- **The seventh round's slate** comes only with a change that gives the neutral brand's text colour a hue. That changes a brand shipped to every adopter, and this record does not decide it.
- **The redesign's other blocks.** A block that holds no place in an order takes no step, such as the seventh round's blocks for capabilities, which have no rank. A solid family for such a block is another meaning, which this record leaves to the redesign.
- **Revisit this record** if a brand needs more than five steps, or once a concept has a mark of its own (point 6). Also revisit it if a pattern needs a mark of its own at its source, which point 5 refuses.
- **Left open:**
  - an order whose source is drawn last, such as a stack whose base is its source;
  - steps for a quantity, such as a heat map's, which a chart would need;
  - a ramp for each of the families of kinds;
  - a floor for a library that uses a shared role a minor version of the foundations adds.
