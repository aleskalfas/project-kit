---
id: DEC-043
title: Ties that meet one side of an item may share a trunk, where the part that draws them declares it
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the part that draws a list of ties may name one of the list's end fields its *trunk end*. The ties that meet one side of an item at that end, and draw alike, then meet it at one point. One of them, the *trunk*, runs as any connector does, and each other, a *branch*, runs along the trunk's first leg and leaves it by a turn of its own. Where that has no room, or would add a crossing, they spread along the side, and the check states it. Each tie stays a line of its own, and what its component draws beside the line, such as its concept's sign, keeps off any stretch it shares. Without the declaration, nothing changes. For example, where two capabilities fill one slot, the slot can take one line, which the second filler's line joins, in place of two arrowheads side by side.

## Context

The connector tool joins the two ends of a tie, straight or with corners, and spreads the ends that meet one side of an item evenly along it ([visual-communication:DEC-005-engine-and-plugins] point 2). Where a tie meets an end, and how the ties that meet one side spread, is the connector tool's ([visual-communication:DEC-011-tie-ends] point 1), so before this record a pattern could ask nothing else of it.

How a connector routes, which this record's guarantees rest on, was the connector tool's alone, and no record decided it. The ends that meet one side take their places along it by their other ends' centres, then by the ties' order, and split it into equal parts. A connector with corners turns halfway between its ends. Its turns are round at its radius, each taking at most half the shorter of its two legs, and a leg that ends in an arrowhead counts to the head's base. This record decides the four in the edit it names to DEC-005 point 2 (Implications).

[project-kit#3083](https://github.com/aleskalfas/project-kit/issues/3083) asks for a shared trunk, for the page of how capabilities connect in the deck of the repository the capability is authored in. It asks that a branch leave its trunk clear of the trunk's turns and turn on the connector's radius, that ties sharing a trunk never cross, and that the check report a crossing rather than draw it.

Terms, beside those of the record of tie ends (DEC-011 point 1):
- A connector runs in *legs*, straight stretches: one where it is straight, and, where it has corners, legs at right angles to one another, which meet at its *turns*. Its *first leg* at an end is the leg that meets that end.
- A tie *meets a side* of an end's item, the side that faces its other end. Its *meeting point* with an end is where it meets it: on that side, at the place the side's spread gives it, or at the point the end names.
- *The ties' order* is the order of the parts that repeat over their lists, then each list's own order.

## Decision

**Where the part that draws a list of ties declares a trunk end, the ties that meet one side of an item there and draw alike share one meeting point and branch off one trunk, or, where that has no room or adds a crossing, spread along the side.**

### 1. The part that draws a list of ties may declare a trunk at one of its end fields

- **On the part.** A part that repeats over a list of ties (DEC-011 point 1) may name one of the list's two end fields its *trunk end*, with the key `trunk`. At its other end, each tie meets its item as before.
- **Fixed in the part.** `trunk` takes an end field's name, never a switch, and no field or option of a tie chooses it. Where `when` chooses between two parts that draw one list, each declares its own.
- **Each drawing its own.** A trunk lies with the parts that draw the list: a pattern's own, the top's own drawing of a layout, or a brand's drawing of it ([visual-communication:DEC-009-layout-defaults] points 1 and 2). A drawing whose part declares none draws the list's ties spread, whatever another drawing declares.
- **Spread otherwise.** Without the declaration, the ties that meet one side of an item spread evenly along it (DEC-005 point 2). So they do where `trunk` names no end field of its list under the versions the piece's lock names, as after an experimental top renamed its end fields, and the finding lies in the version that declares the part (point 7).

### 2. The ties that share a trunk meet their item at one point

- **A group.** The ties of one list that meet one side of one item at their trunk end form a *group* there where all of them draw alike, each draws with corners, and none reads a line's frame or own stretch. Where they do not, each meets the side at a point of its own, spread with the side's other ends.
  - **Alike.** Ties *draw alike* where they take the same component under the same options, the same state, the same stroke width and the same arrowheads, and the same paints as the scene holds them: a role or a step of an order, never a colour in one mode (DEC-005 point 5).
  - **Corners,** since a straight line cannot run along a leg and leave it.
  - **No line's frame.** A tie joins no group where a connector part of its component reads, in its radius, its stroke width or its arrowheads, directly or through another part's formula, the frame or the own stretch (point 6) of a line the connector tool draws, as its formulas show without computing anything. The junctions read those values, so it would loop (DEC-005 point 3).
  - **A point.** A tie whose trunk end names a point its item exposes meets no side, joins no group, and ends at that point (DEC-011 point 2).
- **Several connector parts.** Where a tie's component draws more than one connector part, such as an outline under its line, the tie draws with corners only where each of them does, so a component that draws a straight one beside one with corners forms no group. The tie's radius and stroke width are the greatest across them, and its arrowhead at an end the longest any of them carries there.
- **One point.** A group meets the side at one point, and counts as one end among the side's ends. It takes its place among them by the middle of the range its ties' other ends' centres cover along the side, then by its first tie in the ties' order. Two lists may each have a group on one side. A group of one tie meets the side as that tie would alone.
- **Reach.** A tie of a group *reaches* as far as its meeting point with its other end lies from the group's point, along the side.
- **The trunk.** The tie that reaches least far, the first in the ties' order where two reach as far, is the *trunk*. It runs from the group's point to its other end as any connector with corners does.
- **The branches.** Every other tie is a *branch*. It runs from the group's point along the trunk's first leg and leaves it at its *junction* with a turn. It then runs its *middle leg* to the level of its meeting point with its other end, and turns once more into its *last leg*, which meets that end square to its side.

### 3. A branch leaves its trunk with full turns, the farthest-reaching first

- **Least lengths.** A tie's *least gap* is its radius, zero where it turns nowhere, and never less than twice its stroke width. In a group, the *group's radius* is the greatest of its ties' radii. Its *least leg* is twice the group's radius, and its *least gap* the group's radius, neither less than twice the stroke width its ties share, so its least gap is the greatest of its ties'.
- **Full turns.** Each leg of a branch next to a turn is at least the least leg long, so each turn of each of its connector parts takes that part's own radius whole.
- **The junction span.** The junctions lie on the trunk's first leg, within its *junction span*. It starts the arrowhead's length at the group's point plus the least leg from the item, and ends the least gap short of where that leg ends: at the trunk's first turn, or, where the trunk turns nowhere, at its other end.
- **Apart.** Neighbouring junctions lie at least the least gap apart.
- **The farthest-reaching first.** The branches leave in the order of how far they reach, the farthest nearest the item, the first in the ties' order where two reach as far.
- **A branch's limit** lies the least leg short of its meeting point with its other end, along the trunk's first leg, counted to the base of an arrowhead it ends in there.
- **Even places where they fit.** A junction's *even place* is where the junctions and the end of the trunk's first leg split that leg into equal parts, in their order. Where each even place lies within the junction span, the least gap from the next and within its branch's limit, the junctions take them. Otherwise they take *least places*: places that keep the order, the junction span, the least gap and each branch's limit, from which no junction could come nearer its even place without another going farther from its own. Where several sets of places are each least, the fixed procedure the capability's reference gives picks one, the same in every renderer. A group where no places keep all four has no room (point 5).
- **Around nothing.** A branch routes around no shape and no text (DEC-005 point 2). Where the items stand gives the ties their room, and the graphic-design reviewer judges a line through a text or a card, among the faults its body lists, as an overlap ([visual-communication:DEC-015-viewing-step-and-reviewer] point 7).

### 4. Each tie stays a line of its own, whole from end to end

- **Its own connector.** A branch's connector runs from its start to its end, along the trunk's first leg between the group's point and its junction. It keeps its own trace, paints, arrowheads, state and concept, as every tie does (DEC-011 points 1 and 3).
- **Drawn once for each tie.** The trunk's first leg up to a junction is drawn by each tie that runs along it, in the scene's order. Since they draw alike, an opaque paint shows there as one line, and their arrowheads at the group's point as one head. A translucent paint shows darker, laid once for each tie.
- **Nothing new in the scene.** A branch's connector holds its route's points, and each end names the element it meets and the side, as before (DEC-005 point 5), so the seam keeps its version (DEC-005 point 8).

### 5. A group that cannot be drawn clear is drawn spread

- **A crossing.** Two ties *cross* where a leg of one meets a leg of the other, in one of two kinds: the two legs *pass across* each other, a touch included, or they *run side by side* closer than the greater of their two least gaps, on one line included (point 3). The stretch two ties of one group share, the junction where one leaves the other, and a point where both end are no crossing. Legs are read from the route's points as the scene holds them, a round turn taken sharp, and a curved connector's are left to the change that builds curves.
- **Cannot be drawn clear.** A group cannot be drawn clear where it has no room (point 3), where a branch's middle leg is shorter than the least leg, where two of its ties cross, or where it adds a crossing.
- **A crossing added.** The *spread routes* are the routes of the instance's ties with every group spread, as without the declaration, and the *declared routes* those with the groups drawn as declared. A crossing that the declared routes have is judged by its kind: it is *added* where the spread routes have its two ties cross nowhere, or only pass across where the declared routes have them run side by side. It is added by each group drawn as declared on a side that either of its two ties meets, since that group holds the tie or moved it along the side. So a crossing that joins ties of two groups is added by both.
- **Every tie counts.** Crossings are judged between every two ties of every list one instance draws, the ties the connector tool spreads together: a trunk, a branch, and a tie in no group, straight or not.
- **The whole group spread.** Where a group cannot be drawn clear, each of its ties meets the side at a point of its own, spread with the side's other ends, and the check states it (point 7).
- **Judged together, in rounds.** The engine judges every group of the instance at once, and draws spread each that cannot be drawn clear. It then judges the groups left again, with the meeting points and the routes computed anew, until each can be drawn clear. A group drawn spread is not judged again, so there are at most one round for each group and one more. Each round computes the routes once and compares pairs of ties, against the spread routes, which are the same in every round and computed once.
- **What is drawn.** No tie is left out, no two ties of a group drawn as declared cross, and two ties drawn crossing cross in the spread routes too, running side by side only if they do there, so the declarations add no crossing. A crossing they do not add is no finding, as without a trunk.

### 6. A tie component keeps what it draws beside its line off a shared stretch, and centres none on its group's other lines

- **The rule.** A component that takes ends keeps every part it draws but its connectors, such as its concept's sign ([visual-communication:DEC-036-concept-signs] point 2) or a text, off the stretches its tie shares, and centres none on the line of another tie of its group. No part of such a part's frame lies on a stretch its tie shares, and the centre of its frame lies farther from each leg of another tie of its group than half that tie's stroke width, legs read as point 5 reads them. A part it places on its line stands on the tie's *own stretch*. The check finds a part that does not keep this (point 7).
- **At an end.** A part whose frame holds its tie's meeting point with an end, such as a dot or a head, is left out of this rule and of the check where every tie of its group draws a part that shows the same there, since one thing that every tie shows at one place states nothing false of any of them.
- **A tie's own stretch.** A trunk's runs from its group's last junction to its other end, and a branch's from its junction to its other end. A line that shares no stretch, such as a tie in no group or in a group drawn spread, has its whole length as its own.
- **No room for parts.** The least gap keeps lines apart, and makes no room for a part. A sign or a text that only covers another tie's leg, its centre off that tie's line, is an overlap, as without a trunk, which the reviewer judges (point 3).
- **Two measures of the engine.** A reference to a line reads two more measures, `own-center` and `own-middle`: across and down, the point halfway along its own stretch, measured along the route's points as the scene holds them, a round turn taken sharp. They are new names of the engine, so they add to the format (DEC-005 point 1). A curved connector's are left to the change that builds curves.
- **The frame's centre where nothing is shared.** A connector with corners that branches off no trunk turns halfway between its ends, and a line's frame is the least box that holds its route (DEC-005 points 2 and 3, as this record edits them). So on a line whose own stretch is its whole length, `own-center` and `own-middle` read what `center` and `middle` read, and a part placed by them does not move.

### 7. What the check reports

Each finding below fails validation where it lies in a file the project can correct, and elsewhere, as in a released library version, asks for attention and names who can correct it ([visual-communication:DEC-002-files-and-validation] point 7), unless it is stated as a fact.

- **Fails validation:**
  - `trunk` on a part that repeats over no list of ties, or naming neither of its list's end fields. It lies in the version that declares the part, a drawing's in its brand's (DEC-011 point 8).
  - a formula that reads `own-center` or `own-middle` of an element that is no line, as one that reads what it may not reach (DEC-005 point 14).
  - a part that a component that takes ends draws, other than its connectors, any part of whose frame lies on a stretch its tie shares, or whose centre lies on the line of another tie of its group, unless point 6 leaves it out at its tie's end. A piece shows it, and it lies in the component's version, once for each version, as a component's fault does.
- **Stated as a fact:**
  - a group drawn spread, naming why: no room, a branch's short middle leg, two of its ties that cross, or a crossing it adds, with the two ties (point 5);
  - ties that meet one side of an item at their trunk end and form no group, since they do not draw alike, a connector part is straight beside one with corners, or one reads a line's frame or own stretch, naming what differs, the straight part or the formula (point 2). Where all of them are straight and alike, nothing is stated.

  Each fact lies in the content file, at the first of those ties in the ties' order, and names what would let the group form: the content, the lock, or a formula's component. Each finding a piece shows names the language and the size key where it arises, as a piece is placed in each language at each key ([visual-communication:DEC-021-size-and-shape] point 7).

### 8. An addition that breaks nothing

- **Optional.** `trunk` is an optional key of a part, and no formula that format 1 accepted reads `own-center` or `own-middle`. So every file format 1 accepted reads and draws as before, and none of point 7's findings arises from one ([visual-communication:DEC-003-change-over-time] point 3).
- **A change of look.** Declaring a trunk, withdrawing it, or naming the other end field changes only how a piece looks, so it breaks nothing (DEC-003 point 6). No tie is lost, and a group that cannot be drawn clear fails no draft, since it is drawn spread (point 5).
- **The cost.** A tie component that places its sign by its line's frame, such as one a draft's lock keeps from before the measures, may stand it on a shared stretch once a trunk is declared, or centre it on the line of another tie of its group. The check finds both (point 7), which fail only in a version the project can correct, and the reviewer judges a sign that only covers another tie's leg as an overlap (point 6).

## Rationale

**Why the part that draws the list declares it, each drawing its own.** The founding record has a pattern decide the arrows between its items ([visual-communication:DEC-001-visual-communication-discipline] point 6), and a trunk is shared by the ties that meet one side, which only what draws the list sees (DEC-011 point 1). The end fields lie with the top because content writes their names on every tie (DEC-011, Rationale). Content never writes a trunk end: a trunk is form, which the record of layouts gives a brand's drawing (DEC-009 point 2), and declared by the top it would bind every drawing to a form it did not choose. On the part, a brand declares it in its drawing, which holds no list of its own ([visual-communication:DEC-034-brand-drawings] point 1).

**Why a brand's drawing needs no fit of its own.** A drawing fits where it takes what the content gives and each tie's ends are found under it (DEC-009 point 6, DEC-011 point 5). A trunk takes nothing the content gives, and loses no end (point 5), so a drawing that declares one fits where it fitted before.

**Why at one end field.** The page that asked spreads the ties that leave each filler, and shares a trunk only where they meet a slot. A tie that branched at both its ends would leave one trunk and join another, each placed by the other. No pattern needs that, and allowing it later is an addition (DEC-003 point 3).

**Why no switch chooses it.** Two parts with `when` on an option already let that option choose the trunk, so a switch would add nothing.

**Why only ties that draw alike, all or none.** The record of tie ends refuses one tie to several items, whose lines would share one trace, one state and one concept (DEC-011, Rationale, "Why one item for each end"). A trunk shares a stretch, so this record meets that reason point by point:
- **The trace.** Each tie stays one item, drawn whole with its own trace, so an edit taken back from a renderer tells the ties apart.
- **The state and the paint.** A shared stretch shows those of the tie the scene draws last. Ties that differ in either form no group, so a broken tie shows its state on its whole line. Compared as the scene holds them, paints group alike in every mode, as one scene serves every mode (DEC-005 point 5).
- **The arrowheads.** Grouped ties carry the same heads, so one head at the group's point says what is true.

The cost lies in a translucent paint, laid once for each tie.

**The exception this makes.** No operator may arrange items by what they hold (DEC-005 point 2), and whether ties draw alike reads each tie's state and its concept's paint. So the condition is an exception, bounded and declared in that point: the connector tool chooses only between two arrangements its part declares, spread or sharing a trunk, since a shared stretch would state something false of ties that do not draw alike. With whether one stretch is drawn once for several ties, it decides where each tie on that side meets it, the ties of other lists included. It decides nothing else: each tie is drawn, keeps its place in its list and in the ties' order, and joins the items it names. Grouping only the alike among a side's ties would also choose which ties join by what they hold, so a list's ties on a side form one group or none.

**Why a connector routes as it does.** Each of the four behaviours this record decides in DEC-005 point 2 has one reason:
- **Ends ordered by where they go,** so ties that leave one side towards several items do not cross beside it, and equal parts give each end the same room.
- **A turn halfway,** so a connector's two outer legs take one length, and its route stays within the box between its ends, which is its frame. Its halfway point along the route is then its frame's centre (point 6).
- **A turn of at most half the shorter leg,** so two turns on one leg never overlap, and a short leg narrows its turns rather than bend the line back.
- **A leg to the arrowhead's base,** since the line stops there, and a turn fitted on the whole leg would round into the head.

**Why reach is read at the meeting points.** A branch's last leg runs level with its meeting point with its other end, never with that end's centre. Where the far item has several ties on its side, two ties between one pair of items meet it at two points. Read at the centres, the trunk could reach farther than a branch, whose last leg would then cross the trunk's middle leg.
- **No loop.** A meeting point comes from its item's side, the ends that meet it there, ordered by the items' centres and the ties' order, and which groups are drawn as declared, never from a route. The engine computes them anew in each round from the groups still drawn as declared, a set that only shrinks, so the rounds end. A group's own place among a side's ends is read from centres, so no meeting point waits on another.

**Why the trunk reaches least far, and the farthest-reaching branch leaves first.** Of two ties that lie one way from the group's point, the one that reaches farther leaves the trunk's first leg nearer the item. Its middle leg then lies nearer the item than the other's, and its last leg runs beyond the other's reach, so neither meets the other tie past its junction. The trunk leaves the first leg last, at its first turn, so it reaches least far, and each of its later legs turns away from a branch's end or stops short of it: the first leg is the one stretch every branch passes. Ties that lie the two ways never meet. Two that reach exactly as far one way run level and meet, so the engine judges crossings rather than trust the order.

**Why the least leg and the least gap.** A turn takes at most half the shorter of its two legs, so legs twice the group's radius long let each turn take its full radius, as the issue asks, and turns the group's radius apart share no part of a leg. Two lines nearer than twice the stroke width read as one, so neither length is less, and two legs that run side by side closer than the least gap meet as a crossing does. The lengths are read from the radius and the stroke the ties already draw, so no number is added.

**Why even places, then the least places.** Even places give each turn the most room, as ends are spread along a side, and keep the branches off the item's column where room allows. A branch whose other end lies close across cannot reach its even place, though one nearer the item would serve it, so a junction moves only as its neighbours and its limit force. Two junctions may trade their moves, so the record fixes that the result is least, and the reference's procedure which of the least sets it is.

**Why a crossing is judged against the spread routes.**
- **Every tie a declaration moves.** A group takes several of a side's ends into one, so the trunk, the branches and every other end on that side take new places, and any of them may cross where it did not. Only a group moves the ties on its side, so each crossing a declaration adds has a group that added it. Judging every pair against the spread routes catches each such crossing, whichever tie it falls on, and leaves alone a crossing every piece without a trunk draws.
- **Both groups.** A crossing between ties that two groups placed may be either's doing. Telling which would need the routes with each group spread apart, a computation for each, and a crossing either group would add alone would then survive both. So both are drawn spread, at the cost that a group may be drawn spread that would draw clear alone.
- **By kind.** Two legs that pass across meet at one point, and each still reads as its own line. Two that run side by side meet along a whole stretch, nearer than the least gap keeps lines apart, and on one line read as one (point 3). So where two ties only pass across in the spread routes, declarations that have them run side by side add a meeting the spread routes lack.
- **A group's own ties, without the comparison.** Two ties that reach exactly as far may run side by side in the spread routes too, as where the farther runs on along the nearer's last leg, so judged against them, a group whose ties run on one line past their junction would stand, though the issue asks that ties sharing a trunk never cross.

**Why the whole group is drawn spread, judged together, and stated as a fact.**
- **No tie is lost,** and the declarations add no crossing, as the issue asks. A draft that did not change never fails because a library added a trunk that cannot be drawn clear, as the record of tie ends refuses to fail a piece for what a release changed (DEC-011, Rationale, "Why an end is found once").
- **The whole group.** Spreading only the branch that cannot be drawn clear would move the group's point, and every other branch's place with it, into an arrangement its pattern never declared.
- **Together.** Judged one list at a time, two lists that each hold the other's far end would be drawn by which went first. Judged at once, the groups give one scene whatever order they lie in, as every order the engine gives is fixed (DEC-005 point 5).
- **A fact.** Every page draws whole, so nothing is broken that the project must mend, as for a brand's drawing that does not fit (DEC-009 point 9, and its Rationale). A known loss may be accepted, and the check then stops repeating it (DEC-005 point 9), but a finding that asks for attention stands at every check. A deliberate difference, such as one tie marked broken, would then ask at every check for an act nobody is to take. The fact reports a crossing rather than draw it, as the issue asks.

**Why a part keeps off a shared stretch, and a measure of the engine finds the own stretch.** A sign says which concept its tie carries (DEC-036 point 2), and a text says something of its tie, so on a shared stretch either would say it of every tie there, and centred on another tie's line, of that tie. The junctions that bound a tie's own stretch are the engine's to compute, and the centre of a branch's frame may lie off its legs, even on the trunk's, so only a measure of the engine finds that stretch. On a corner, the drawn turn passes within three tenths of its radius of the point, across and down, so a sign at least six tenths of the radius wide stands on its line.

**Why a check finds a part on a shared stretch, and the reviewer judges clearance.**
- **A part on a shared stretch, or centred on another line of its group,** is decided by the scene's routes. The ties there draw alike and lie on one another, so a sign on a shared stretch looks like a sign on its own line, and no image tells them apart. Nor does one tell a sign centred on another tie's line from that tie's own, since the two draw alike, while a sign that only covers a neighbour's leg shows as an overlap, as without a trunk. The check reads the routes, the stroke widths and the part's frame exactly, and needs no length but the stroke the ties already draw. Point 6 binds the component, which keeps it under every trunk by the measures, so the finding is that component's fault (DEC-002 point 7), not one that only a combination of versions shows.
- **Clearance.** The issue asks that each tie keep clear of the shapes and the text it passes, by distances one piece's design chose. A branch's middle leg runs nearer its item's column, where that item's neighbours stand, than a connector's runs without a trunk, so the hazard is this record's own, and its judge is named: the reviewer's fault of overlaps. The engine never moves a branch to keep clear (DEC-005 point 2), and a check that measured clearance would judge every connector, with lengths every brand resolves, so it would be a record of its own.

**Why each tie stays whole.** A branch drawn from its junction alone would hang its end, its arrowhead and its state on another tie's line, and a medium with connectors of its own attaches a line to items, never to another line (DEC-005 point 5).

### Alternatives considered

- **An option of the tie's component.** Rejected: that component is given its own two ends, never the other ties that meet the side.
- **An arrangement field on each tie.** Rejected: two ties of one side could disagree, and an arrangement field sets how the pattern sizes or places its own item ([visual-communication:DEC-010-list-item-fields] point 3).
- **Branches that leave at the trunk's turn, as a fork.** Rejected: two turns would take one part of the trunk, and the issue asks for a junction clear of its turns.
- **A junction a pattern places by a formula, or by a length it declares.** Rejected: a formula that set a junction could read no route without a loop, and the group already gives every length a junction needs.
- **A branch that cannot be drawn clear left out, its finding failing,** or only a branch that would cross. Rejected: a library release that adds a trunk would drop a tie from a draft that did not change, and fail it, which the record of tie ends refuses for a lost end.
- **A sign on a leg of the tie's own, which its component finds from its end's frame.** Rejected: a component cannot read where a branch's junction lies, and such a sign would move on every tie that shares no trunk.
- **The graphic-design reviewer judging a part on a shared stretch, as an overlap.** Set aside: a sign on a shared stretch looks like a sign on its own line, and the fault is decided by the scene's routes, which no image shows.
- **One named point of a connector line, read as `line.<point>.x` and `.y`,** through the grammar of a picture's exposed points. It leaves a reference's last step a measure of the frame (DEC-005 point 3), and grows by one name for each later point instead of two. Rejected for now: no second point is needed.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - DEC-005 point 1, "Where lengths come from", comes to say that a formula also reads, of a line, the point halfway along the stretch of its route that it alone runs (point 6).
  - DEC-005 point 2, "Connectors", comes to say that connectors join named elements, straight, with corners or curved. The ends that meet one side of an item take their places along it by their other ends' centres, then by the ties' order, and split it into equal parts, a group of ties that share a trunk counting as one end, placed by the middle of the range its ties' other ends' centres cover. A connector with corners turns halfway between its ends, unless it branches off a trunk (DEC-043). Its turns are round at its radius, each taking at most half the shorter of its two legs, and a leg that ends in an arrowhead counts to the head's base. Where the part that draws a list of ties declares a trunk end, the ties that meet one side of an item there and draw alike meet it at one point, the others branching off the trunk clear of its turns, or, where that has no room or adds a crossing, spread with the side's other ends. Connectors never route around obstacles (points 2, 3 and 5).
  - DEC-005 point 2, "No operator chooses, filters or sorts items by what they hold", comes to add one bounded exception: the connector tool chooses between two arrangements its part declares, spread or sharing a trunk, by whether the side's ties draw alike, since a shared stretch would state something false of ties that do not. This is the one place where what an item holds decides where ties meet a side (point 2).
  - DEC-005 point 3, "How a reference reads", comes to say that a reference ends with the measure it reads: of the frame, or, of a line, of the middle of its own stretch, a line's frame being the least box that holds its route (point 6).
  - DEC-011 point 1, "Given its ends", comes to say that where a tie meets an end, how the ties that meet one side spread, and how they share a trunk where the part that draws them declares one, is the connector tool's (points 1 and 2).
  - DEC-036 point 2, "The component places it", comes to add that a tie's component keeps it, as every part it draws beside the tie's line, off any stretch where that line runs along other ties' lines, and centres it on none of those lines, unless it stands at the tie's end and each of those ties draws the same there (point 6).
- **Read against this record, and left as they stand:** DEC-001 point 6, DEC-002 point 7, DEC-003 points 3, 6 and 8, DEC-005 points 5, 8, 9 and 14, DEC-009 points 2, 6 and 9, DEC-010 points 2 and 3, DEC-011 points 3, 4, 5 and 8, DEC-015 point 7, DEC-021 point 7 and DEC-034 point 1.
- **A renderer that draws connectors of its own,** as a whiteboard service's would. A branch's whole route, its shared stretch included, is in its points (DEC-005 point 5), so a medium that honours them keeps the trunk. One that cannot declares them approximated, and the loss is reported for every connector with corners, branches among them (DEC-005 point 9), though not named as a trunk's. A sign placed at fixed coordinates does not follow the medium's own route, as for every connector with corners. The change that builds such a renderer adds a hint to the scene only if it must name that loss.
- **The build,** a Task of its own once this record is accepted:
  - points 1 to 8 in the engine, the component schema and the checks, with tests in every renderer;
  - the starter connector's sign moved to the two measures, with the starter's own word on where that sign stands, in the same change, since a starter that kept the frame's centre would stand its signs on shared stretches from the first trunk declared;
  - the capability's reference: the measures, the trunk, the procedure that places the junctions, the rounds, and the findings.
- **The page that asked for this record:** declaring its slot end a trunk end is a change of its own, after the build, with its own visual review.
