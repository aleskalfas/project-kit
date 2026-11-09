---
id: DEC-032
title: An order's first five places take five colour steps, which each brand gives
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the foundations declare five shared colour families that step in an order, and each brand gives them its values. Each step has a fill, a line and a text on the fill. The text holds the contrast body text needs, in every mode. The first step stands furthest from the page's background, so in a dark mode it is the lightest, not the darkest. A pattern may offer the steps under a word of one of its options. Where the content chooses that word, the pattern's first five places take the five steps, in order. A step shows where an item stands in an order, so no concept, component or state names one. An item that names a concept keeps its place's step as its fill, and its concept's colour becomes the line around it. So the order stays whole, and the item still says what it is. A brand that gives no steps draws each in its neutral family. The neutral brand's steps take its text colour's hue, and that colour is a grey, so its steps are grey.

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
- **Order and a highlight never cross.** Order is only ever a block's fill. A highlight is only ever a line, a word or a tint region.

The capability's rule sets, written beside this record, are accepted ([project-kit#2884](https://github.com/aleskalfas/project-kit/issues/2884)). One of their rules asks that a picture's differences be those its content has. On a page whose point is an order, the parts that show the order share one colour, or step in one shade. Each concept an item names keeps its colour on a mark of its own.

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

**The foundations declare five steps, in a sequence, each a colour family of a fill, a line and a text. A step is a family that only a place takes, or a part the content points at. A brand gives each step its values. In every combination of its modes, each step's text holds WCAG's level for text on its fill, and each step stands at least as far from the background as the next. A pattern may offer the steps under a word of an option, which gives its first five places the steps in their sequence. On a step, an item that names a concept keeps the step as its fill, and takes its concept's colour as its line. Each step defaults to the neutral family. The neutral brand's steps take its text colour's hue.**

### 1. Five steps, in a sequence, each a colour family

- **Five, the same for every brand.** The foundations declare the steps `order-1` to `order-5` as a sequence, from the source to the end. The checks read the order from that sequence, never from a name.
- **Each a family of three members.** A step has a `fill`, a `line` and a `text` on the fill, the members the foundations' families have. Each member is a shared colour role, `family.order-<n>.<member>`, such as `family.order-1.fill`. An item component paints a step with the members it paints any family with.
- **In the group of the families.** The roles lie in the top group that holds every family's roles, so the steps add no top group (DEC-004 point 5). No library or brand can hold a name there. The check refuses a brand's own token in a group of the shared roles, and no library takes a top group's name (DEC-004 point 7).
- **Apart from the families of kinds.** The foundations declare the steps apart from them, and no family shares a name with a step.
- **Public names.** A brand exports the steps as it exports every shared role (DEC-004 point 5).
- **The neutral family marked.** The foundations mark the family of kinds that shows no hue, as they declare the steps' sequence. The engine and the checks read it from that mark, never from its name (point 6).

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
- **Past the fifth place,** an item takes no step. It takes its family as an item at a place no pattern names does: its concept's, else its item component's (DEC-010 point 6). The check asks the piece's author for attention, who may split the list, or draw it unshaded.
- **It shows where the item paints from its family.** An item component may paint its fill in a fixed role, such as a card on the surface. It then shows the step only in the parts it paints from its family, such as the card's bar. A pattern that offers the steps names a default item component that paints its fill from its family, and its line apart from that fill (point 6). Its option chooses only its places' families, never the item's look, which is the item component's (DEC-001 point 6). So that default holds under every word. No check judges it, and a line drawn on its fill fails at the piece (point 6).
- **One list, never ties.** A word gives the steps to the places of one list the pattern repeats. A list of ties takes none, since a tie stands in no order ([visual-communication:DEC-011-tie-ends]).
- **Never the order's only sign.** A pattern that shades by place also shows the order by position, and by size, numbers or arrows where its form has them. Shades collapse under forced colours, and on a projector that washes them out.

### 5. A step reaches an item only through a place, or where the content points a part at it

- **A step shows where an item stands in an order,** as a place's family does when a pyramid with no notation shades its levels (DEC-001, Rationale). It never says what a thing is, or what state it is in. Named in a structure, it would become one more colour of a palette, in every brand.
- **What names one of the families of kinds names no step:** a notation's concept, a component's own default family and a state's family. A step named there is refused, as any name that is no such family is.
- **What takes either.** A pattern's place takes one of the families of kinds or a step, so a pattern whose places are no order still gives them families of kinds. A paint from the item's family paints from either.
- **Never by its name in a structure.** A part of a component never paints with a step's role by its name. No library's own role, and no component token, aliases a step's role as its default.
- **A brand's aliases run either way.** A brand may give a step's role an alias to another of its tokens, or give another role an alias to a step's. Its values are its own. A role means what the structure that reads it says, wherever its value comes from.
- **Content may point a part at a step's role,** as it may point a part at any role (DEC-001 point 6). Its author then says that the part shows a place.

### 6. On a step, an item's concept gives only its line

- **The step fills the item, and its concept outlines it.** Where an item's place takes a step and the item names a concept, the members `fill` and `text` resolve to the step's, and `line` to the concept's. Each part takes the member it paints with, and is measured as drawn. This rests on a component keeping `line` for its lines and marks, as each family paints one thing: its line, its fill and the text on it.
- **A concept of the neutral family gives nothing on a step.** That family marks no kind by a hue, so the item takes the step whole.
- **The text stays the step's,** since the step's text holds its pair on the step's fill (point 2). A run that names a concept still takes its concept's family, measured as drawn on the step, as on any fill not its family's own ([visual-communication:DEC-012-text-runs] point 3). Its concept's text is tuned for its own family's fill, so such a run mostly fails on a step, and its author drops the run's concept or chooses no steps.
- **The line stands 3 to 1 from each colour beside it.** It is the item's only colour sign of its concept, a mark that is not text, so WCAG 1.4.11 asks 3 to 1 of it against the colours beside it. The check measures it as drawn, against each fill it borders, in every combination the piece is drawn in, as it measures a drawn text (DEC-004 point 8). No line of a hue holds 3 to 1 on every step, so the default item component draws its line apart from its fill (point 4). Only what the item lies on then lies beside the line. So here a family's `line` does more than edge a fill: a brand whose hues' lines are faint against its page fails such an item, and the finding names the brand's owner too.
- **Where no part the item draws takes its concept's line,** or none takes the step's fill or text, the check asks the piece's author for attention, for a concept of a hue. An item component with no line, or a fixed fill, may cause it, and so may content that points a part at another role. The author may name another item component, or draw the list unshaded.
- **Only a step splits an item's family so.** A place that gives one of the families of kinds still yields to the item's concept (DEC-001 point 6, DEC-010 point 6). A state its component gives a family still replaces both (DEC-001 point 6), and each run's family too (DEC-012 point 3). An outer item passes the step whole to what sits in it, where nothing nearer gives a family (DEC-010 point 6), and keeps its concept's line as its own mark.
- **Point 5 holds.** The step reaches the item through its place, and the line comes from one of the families of kinds. No concept names a step.

### 7. What the neutral brand gives

The neutral brand stays a brand to start from, so its steps carry no project's identity (COR-014; DEC-001 point 9).
- **One hue, its text colour's own.** The steps read as one chain, a deepening of the text, and claim no kind. Where the text colour has no hue, as a pure grey, the steps have none either.
- **Apart from the accent.** A step never takes the accent's colour. Where the text colour's hue lies near the accent's, the steps stay far below the accent's chroma, so the accent keeps its one meaning.
- **Near-even steps of perceived lightness,** as OKLCH's lightness gives them.
- **One text colour on every step of a mode: the background's own.** No step's text differs from another's, so the text adds no difference the order lacks. A step whose text holds 4.5 to 1 then stands 4.5 to 1 from the background as well.
- **Each hue's line at 3 to 1 from the background,** in every combination, so a concept's line on a step holds where the item lies on the page (point 6).

### 8. What the checks report, and how severely

Each finding below lies where the record of files and validation puts it. It fails or asks for attention by that record's policy ([visual-communication:DEC-002-files-and-validation] point 7).
- **Fails validation:**
  - in a brand: a step's text below WCAG's level for text on its fill, in some combination, as every declared pair below its contrast fails (DEC-004 point 11);
  - in a brand: a step whose fill contrasts with the background more than the fill of the step before it, in some combination;
  - in a notation, a component or a state: a step where one of the families of kinds is named, as any name that is no such family is refused;
  - in a component: a part that paints with a step's role by its name, or a component token whose default is a step's role;
  - in a library's roles: an own role whose default is a step's role;
  - in a pattern: a word that gives its places steps otherwise than from the first, one to each place;
  - in a pattern: a word that gives one of the families of kinds beside the steps, or one step to every place;
  - at a piece: a concept's line on a step that stands less than 3 to 1 from a colour beside it, as drawn, in some combination, as a drawn text below its level fails (DEC-004 point 11). The finding also names the brand's owner.
- **Asks the piece's author for attention:**
  - a list whose places take the steps, and that draws more than five items;
  - an item on a step where no part it draws takes a member of its step;
  - an item on a step that names a concept of a hue, where no part it draws takes its concept's line, or none takes the step's fill or text.

### 9. What this adds, and what still holds

- **The foundations gain fifteen shared roles, each with a default,** and the sequence of the steps, declared apart from the families of kinds. A role with a default breaks nothing (DEC-004 point 5), so the foundations take a minor version ([visual-communication:DEC-013-shipped-library-releases] point 3).
- **The format grows by an addition** that every file written before still meets ([visual-communication:DEC-003-change-over-time] point 3). The schema of the foundations' roles gains the sequence and the neutral family's mark, which no other library declares, as it declares no family.
- **The engine gains no tool.** A family for each place is the record of a list's fields'. The steps are families, so an item paints them as it paints any family. Where a concept meets a step, the engine takes the item's line from one family and the rest from another, and the check measures that line as drawn (point 6).
- **Every brand draws every piece as before.** A piece meets the steps only where a pattern gives them to its places. Under a brand that gives none, such a place draws in the neutral family, and an item there that names a concept of a hue takes its concept's line.
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

**Why past the fifth place an item takes no step.** It is the rule the record of a list's fields set for a place no pattern names (DEC-010 point 6). The other ways each add a difference the content lacks: steps given again read as a pair, and the rest on the last step read as a group. The page then shows a difference its content lacks, so the check asks the author to act.

**Why only a place takes a step.** A notation's concept, a component's own family and a state each say what a thing is, or how it stands. A step among them would show a place in an order where there is none. A step a component or a library's role names becomes one more colour of a palette, and the steps stop meaning an order. The content may point a part at a step, since there its author places the part.

**Why, on a step, the concept takes the line.** Each of the other two ways loses one of the item's two facts.
- **The concept's fill breaks the order.** One item of the chain would take its concept's hue, a difference on the very chain the page is about. On such a page, the rule sets' rule on form asks that the parts that show the order take no concept's hue.
- **The step alone leaves the item unmarked.** A concept's colour is its only mark today, since format 1 draws no concept's icon (DEC-012, Context).
- **Each part carries one variable.** The fill carries the place by its lightness, Bertin's ordered variable. The line carries the kind by its hue, his selective one. The redesign's seventh round keeps the same split on every page, and the rule sets have each concept keep its colour on a mark of its own.
- **The text stays the step's,** since a concept's text is tuned for its family's own fill, and would fail its pair on a step.
- **A state may still fill the item.** A state is a difference the content has, and its look is its component's (DEC-001 point 6). Today a state's look is a family, so a state on a step leaves the chain's shade. A state's look other than a family, such as a line, is left to a later change.

**Why a neutral concept gives nothing on a step, and an outer item passes the step whole.** A neutral concept's line is a quiet rule, 1.4 to 1 from a light page in the neutral brand, and marks no kind by a hue. At the defaults, where the step is the neutral family too, the item then looks as it would with its concept first, and meets no new finding. What sits in an item lies on the step's fill, where no line of a hue holds 3 to 1. A concept's line passed to it would fail where nothing is wrong, since the outer item's line already marks the concept.

**Why a family's line now carries a promise.** The foundations have treated a family's line as its fill's edge, which a brand may draw faint. On a step it is a concept's only colour, so the record holds it to 3 to 1 where it is drawn, and the neutral brand to 3 to 1 for each hue's line. A brand with faint lines still draws every other piece as before.

**Why the line is measured against each colour beside it.** WCAG 1.4.11 asks 3 to 1 against the colours beside a mark, and a step's fill cannot hold it. In a light mode a step is about as dark as a line. The neutral brand's lines of the five hues stand 1.0 to 2.6 to 1 from the seventh round's steps, in both modes, and 5.7 to 8.0 to 1 from its pages. So the default item component draws the line apart from its fill, as the round's picture does, leaving the page on both its sides. Where items touch, or a component draws the line on its fill, the check finds it.

**Why measured as drawn, and not as a pair.** A pair of a family's line against the background judges a brand, but not what a line borders where it is drawn: the step's fill, or the next item where items touch. It would also bind every family's line where it marks nothing. Only a drawing shows where a concept's line is an item's only mark, and what lies beside it.

**Why a missing line asks for attention, and does not fail.** WCAG 1.4.11 binds a mark that is drawn, so a weak line fails as a weak text does. Whether a concept is marked at all is a judgement the rule sets give a reviewer, in their rule that the same meaning looks the same. Its author may mark the concept another way, or choose no steps. The check names the item, as it names a list longer than five.

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
- **The concept's whole colour before the step,** as a place that gives a family of kinds yields to it. Rejected. One item of the chain would take its concept's fill, and the order would break where it stands (Rationale, "Why, on a step, the concept takes the line").
- **The step alone, with the concept unmarked.** Rejected. The item would lose its concept's only mark today.
- **The concept's colour on the item's text.** Rejected. A concept's text, tuned for its family's own fill, would fail its pair on a step.
- **The line measured against what the item lies on alone.** Rejected. A line drawn on the step's fill would pass, and be lost against it.
- **A pair of each family's line against the background, at 3 to 1, or of each hue's.** Rejected (Rationale, "Why measured as drawn, and not as a pair").
- **A neutral concept's line drawn on a step,** or exempt from the check. Rejected. It would mark no kind, and either fail where nothing is wrong or stand unjudged.
- **Content points each item's parts at its step,** with no family for each place. Not chosen. Each item would carry its place in its content. An item inserted would leave every later one on the wrong step.
- **The steps as a component's own family, or a state's,** such as a block drawn solid in the first step. Rejected. The step would show a place in an order where there is none, and become a palette's colour.
- **The engine tells whether a page's point is an order.** Rejected. It cannot, so the content chooses it by a word.
- **A renderer mixes the steps,** such as with a colour mix in CSS. Rejected. A renderer adds no colour of its own (DEC-001 point 2).

## Implications

- **Edits to accepted records,** made once a person accepts this record, in the change that proposes it. Accepting this record accepts them (the decisions README, "The acceptance gate"). Each edit ends with a pointer to this record and the point it names, in the form the accepted records use.
  - **The founding record's point 6** gains a bullet: "An order's steps are colour families that only a place takes, or a part the content points at. No concept, component or state names one, and no part of a component names one's role" (point 5). **Its bullet "Colour says what a thing is"** gains, after its sentence on a default: "Where an item names a concept of a hue and its place takes a step of an order, its members `fill` and `text` take the step's, and `line` its concept's" (point 6).
  - **The record of brands and notations' point 7** gains, beside its bullet on a component token's default: "No component token's default aliases a step's role" (point 5).
  - **Its point 8** gains a bullet: "Each step's text on its fill is a declared pair. In every combination, each step's fill stands at least as far from the background as the next" (points 2 and 3). **Its bullet "Checked as drawn"** gains: "It also measures a concept's line on an item that takes a step against each colour beside it, at WCAG's level for other marks" (point 6).
  - **Its point 10** gains a bullet: "The foundations also declare the five steps of an order, in a sequence, apart from the families a notation maps to. A pattern may give them to an order's places, and no concept maps to one" (points 1 and 5). **Its bullet "Colour is never the only sign"** reads "The families a notation maps to bound how many concepts one piece tells apart by colour" (point 1).
  - **Its point 11's list of what fails validation** gains "a brand's steps out of order against the background in some combination" and "a concept a notation maps to a step" (point 8). A step's text below its level already fails there as a declared pair. Its item on a declared pair or a drawn text below its contrast also names a concept's line drawn on a step (points 6 and 8).
  - **Its Implications' first bullet** names the order's steps among what the foundations declare.
  - **The record of library role defaults' point 3** gains a bullet: "No default of a library's own role, or of a component token, aliases a step's role." **Its point 9** fails such a default (point 5).
  - **The record of a list's fields' point 6,** "A family for each place", gains: "A pattern may offer the steps of an order under a word of an option. Under it, its places take the steps from the first, one to each place, with none of the families of kinds beside them. One family for a whole list is never a step" (point 4). **Its bullet "The order stands"** gains: "Where the place takes a step, a concept of a hue gives the item only its line" (point 6). **Its bullet "Items that belong together"** gains: "Where the outer item's place takes a step, it passes the step whole" (point 6). **Its point 9** gains the pattern's findings and the findings that ask for attention, of this record's point 8.
  - **Its Alternatives considered,** "Roles named by a place", ends: "Steps of an order are not rejected here: a pattern writes them for each place in its data, and no step's name is computed from a place," with the pointer to this record (point 4). Its rejection then reads as one of a role's name computed from a place.
- **The accepted record of #2884** takes five edits, to it and to its rule. Each cites this record by its id where it names a point of it:
  - **That record's point 11,** "What it leaves as it is", reads whole: "The engine judges no page's point. Content says it, by pointing the parts that show the order at another role, as the founding record allows (DEC-001 point 6), or by a pattern's word that gives its places the steps of an order, which the content chooses, or which a pattern made for orders takes by default. On a step, an item's concept of a hue colours only its line, and elsewhere an item's colour still comes from the concept it names. An icon takes its concept's colour family (DEC-004 point 10). So a piece meets the rule with what the model holds" (points 4 and 6).
  - **Its Rationale, "Why the form rule narrows a reason, and leaves the model",** ends: "The steps of an order rest on no such judgement: the content, or a pattern made for orders by default, chooses them by a word, and the model resolves them" (points 4 and 6).
  - **Its rejected alternative, "The order's colour in the engine's model",** becomes "The engine judging a page's point", with the reason: "it cannot tell a page's point, and content tells it, by pointing parts at a role or by a pattern's word for the steps of an order" (point 4).
  - **Its Implications' "Left to other records"** ends: "and the principles a shipped brand follows, refining the record of brands and notations", with its citation of that record. That replaces its words from "the colour roles that step in an order" to "both refining the record of brands and notations".
  - **Its rule RS-GRAPHIC-007,** "From the text", reads: "on a page whose point is an order, whether the content points the parts that show the order at one role, rather than each at its concept's, or whether their pattern gives their places the steps of an order." The rule's anchors gain this record's points 4 and 6. The edit adds a way to meet the rule and tightens none, so the set takes no new major (COR-051 point 7).
- **The principles every shipped brand follows** stay to a later record refining the record of brands and notations, as the record of #2884 leaves them. This record decides only the neutral brand's steps (point 7).
- **The Tasks it implies,** under the Feature of the deck's redesign ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)):
  - **The foundations:** the fifteen roles with their defaults, the sequence of the steps and their pairs, and the neutral family's mark, in a minor version. The schema of a library's roles gains the sequence, which the check refuses in any library but the foundations.
  - **The engine and the check:** a family for each place, which the record of a list's fields decided and the engine does not draw yet. Also a concept's line on a step, measured as drawn against each colour beside it (point 6), and the findings of point 8.
  - **The starter:** each pattern that draws an order offers the steps by an option's word. Its default item component paints its fill from its family, and its line apart from that fill (point 4). That default holds under every word, so the Task weighs the change for pieces that draw no steps. Its README's colour section says that on a step a concept's line is the item's only colour mark, measured at 3 to 1 (point 6). Its owner chooses the option's default word, judged in review as the starter's other choices are ([visual-communication:DEC-007-starter-library] point 3). Its reference drops a colour for each place from what it lacks. A library names its bases by major alone (DEC-001 point 5). So the Task decides which finding a piece meets that locks the starter with foundations older than the steps, and where it lies.
  - **The neutral brand:** the steps' values under point 7, in a minor version. Its values start from the seventh round's lightness steps, in its text colour's hue. A step's line is weighed there too. The default item component draws it apart from the fill, and that round draws a block with no edge. A card's bar paints the same member and is a mark. On an item that names a concept of a hue, the concept's line takes its place.
  - **The capability's reference:** the foundations' roles, which names a component's family and a state's may take, how a pattern gives the steps, and the new findings, each on its page. Also how an item's family resolves member by member on a step, and what passes to what sits in it, where the pages say an item takes one family.
  - **The analysis's glossary:** an order, its source and a step.
- **The seventh round's slate** comes only with a change that gives the neutral brand's text colour a hue. That changes a brand shipped to every adopter, and this record does not decide it.
- **The redesign's other blocks.** A block that holds no place in an order takes no step, such as the seventh round's blocks for capabilities, which have no rank. A solid family for such a block is another meaning, which this record leaves to the redesign.
- **Revisit this record** if a brand needs more than five steps, or if a pattern needs a mark of its own at its source, which point 5 refuses.
- **Left open:**
  - an order whose source is drawn last, such as a stack whose base is its source;
  - a concept's icon, or another mark a component keeps for a concept, on an item that takes a step, where it lies on the step's fill;
  - a concept's mark measured as drawn elsewhere, where it is an item's only colour sign, such as a plain card's bar;
  - steps for a quantity, such as a heat map's, which a chart would need;
  - a ramp for each of the families of kinds;
  - a floor for a library that uses a shared role a minor version of the foundations adds.
