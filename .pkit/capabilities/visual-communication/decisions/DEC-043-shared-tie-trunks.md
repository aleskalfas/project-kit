---
id: DEC-043
title: Ties that meet one side of an item may share a trunk, where the part that draws them declares it
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where two capabilities fill one slot, the slot can take one line, which the second filler's line joins, in place of two arrowheads side by side. The part that draws a list of ties may name one of the list's end fields its *trunk end*. The ties that meet one side of an item at that end, and draw alike, then meet it at one point. One of them, the *trunk*, runs as any connector does, and each other, a *branch*, runs along the trunk's first stretch and leaves it by a turn of its own, so that none cross. Where that cannot be drawn clear, they spread as without the declaration, and the check states it. Each tie stays a line of its own, its concept's sign where only it runs. Without the declaration, nothing changes.

## Context

The connector tool joins the two ends of a tie, straight or with corners, and spreads the ends that meet one side of an item evenly along it ([visual-communication:DEC-005-engine-and-plugins] point 2). Where a tie meets an end, and how the ties that meet one side spread, is the connector tool's ([visual-communication:DEC-011-tie-ends] point 1), so no pattern can ask for anything else.

[project-kit#3083](https://github.com/aleskalfas/project-kit/issues/3083) asks for a shared trunk, for the page of how capabilities connect in the deck of the repository the capability is authored in. It asks that a branch leave its trunk clear of the trunk's turns and turn on the connector's radius, that ties sharing a trunk never cross, and that the check report a crossing rather than draw it.

Terms, beside those of the record of tie ends (DEC-011 point 1):
- A connector with corners runs in *legs*, straight stretches at right angles to one another, which meet at its *turns*. Its *first leg* at an end is the leg that meets that end.
- A tie *meets a side* of an end's item, the side that faces its other end. Its *meeting point* with an end is where it meets it: on that side, at the place the side's spread gives it, or at the point the end names.
- *The ties' order* is the order of the parts that repeat over their lists, then each list's own order.
- How a connector routes, which this record's guarantees rest on, is decided by the edit this record names to DEC-005 point 2 (Implications): where its ends take their places along a side, where it turns, how round its turns are, and where a line that ends in an arrowhead stops.

## Decision

**Where the part that draws a list of ties declares a trunk end, the ties that meet one side of an item there and draw alike share one meeting point and branch off one trunk without crossing, or, where they cannot, spread as without the declaration.**

### 1. The part that draws a list of ties may declare a trunk at one of its end fields

- **On the part.** A part that repeats over a list of ties (DEC-011 point 1) may name one of the list's two end fields its *trunk end*, with the key `trunk`. At its other end, each tie meets its item as before.
- **Fixed in the part.** `trunk` takes an end field's name, never a switch, and no field or option of a tie chooses it. Where `when` chooses between two parts that draw one list, each declares its own.
- **Each drawing its own.** A trunk lies with the parts that draw the list: a pattern's own, the top's own drawing of a layout, or a brand's drawing of it ([visual-communication:DEC-009-layout-defaults] points 1 and 2). A drawing whose part declares none draws the list's ties spread, whatever another drawing declares.
- **Spread otherwise.** Without the declaration, the ties that meet one side of an item spread evenly along it (DEC-005 point 2). So they do where `trunk` names no end field of its list under the versions the piece's lock names, as after an experimental top renamed its end fields, and the finding lies in the version that declares the part (point 7).

### 2. The ties that share a trunk meet their item at one point

- **A group.** The ties of one list that meet one side of one item at their trunk end form a *group* there where all of them draw alike, each draws a connector with corners, and none reads a line's frame. Where they do not, each meets the side at a point of its own, as without the declaration.
  - **Alike.** Ties *draw alike* where they take the same component under the same options, the same state, the same stroke width and the same arrowheads, and the same paints as the scene holds them: a role or a step of an order, never a colour in one mode (DEC-005 point 5).
  - **Corners,** since a straight line cannot run along a leg and leave it.
  - **No line's frame.** A tie joins no group where a connector part of its component reads, in its radius, its stroke width or its arrowheads, the frame of a line the connector tool draws, as its formulas show without computing anything. The junctions read those values, so it would loop (DEC-005 point 3).
  - **A point.** A tie whose trunk end names a point its item exposes meets no side, joins no group, and ends at that point (DEC-011 point 2).
- **Several connector parts.** Where a tie's component draws more than one connector part, such as an outline under its line, the tie's radius and stroke width are the greatest across them, and its arrowhead at an end the longest any of them carries there.
- **One point.** A group meets the side at one point, and counts as one end among the side's ends. It takes its place among them by the middle of the span its ties' other ends' centres cover along the side, then by its first tie in the ties' order. Two lists may each have a group on one side. A group of one tie meets the side as that tie would alone.
- **Reach.** A tie of a group *reaches* as far as its meeting point with its other end lies from the group's point, along the side.
- **The trunk.** The tie that reaches least far, the first in the ties' order where two reach as far, is the *trunk*. It runs from the group's point to its other end as any connector with corners does.
- **The branches.** Every other tie is a *branch*. It runs from the group's point along the trunk's first leg and leaves it at its *junction* with a turn. It then runs its *middle leg* to the level of its meeting point with its other end, and turns once more into its *last leg*, which meets that end square to its side.

### 3. A branch leaves its trunk with full turns, the farthest-reaching first

- **Two least lengths.** The *group's radius* is the greatest of its ties' radii, zero where none turns round. Its *least leg* is twice the group's radius, and its *least gap* the group's radius, neither less than twice the group's stroke width.
- **Full turns.** Each leg of a branch next to a turn is at least the least leg long, so each of its turns takes the branch's own radius whole.
- **The junction span.** The junctions lie on the trunk's first leg, within its *junction span*. It starts the arrowhead's length at the group's point plus the least leg from the item, and ends the least gap short of where that leg ends: at the trunk's first turn, or, where the trunk turns nowhere, at its other end.
- **Apart.** Neighbouring junctions lie at least the least gap apart, and so do the last junction, the farthest from the item, and the end of the trunk's first leg.
- **The farthest-reaching first.** The branches leave in the order of how far they reach, the farthest nearest the item, the first in the ties' order where two reach as far.
- **A branch's limit** lies the least leg short of its meeting point with its other end, along the trunk's first leg, counted to the base of an arrowhead it ends in there.
- **Even places where they fit.** A junction's *even place* is where the junctions and the end of the trunk's first leg split that leg into equal parts, in their order. Where each even place lies within the junction span, the least gap from the next and within its branch's limit, the junctions take them. Otherwise each moves from its even place only as far as it must to keep the order, the junction span, the least gap and its branch's limit, by a fixed procedure the capability's reference gives. A group where these cannot all be kept has no room (point 5).
- **Around nothing.** A branch routes around no shape and no text (DEC-005 point 2). The drawing's layout gives its ties their room, and the graphic-design reviewer judges a line through a text or a card, among the faults its body lists, as an overlap ([visual-communication:DEC-015-viewing-step-and-reviewer] point 7).

### 4. Each tie stays a line of its own, whole from end to end

- **Its own connector.** A branch's connector runs from its start to its end, along the trunk's first leg between the group's point and its junction. It keeps its own trace, paints, arrowheads, state and concept, as every tie does (DEC-011 points 1 and 3).
- **Drawn once for each tie.** The trunk's first leg up to a junction is drawn by each tie that runs along it, in the scene's order. Since they draw alike, an opaque paint shows there as one line, and their arrowheads at the group's point as one head. A translucent paint shows darker, laid once for each tie.
- **Nothing new in the scene.** A branch's connector holds its route's points, and each end names the element it meets and the side, as before (DEC-005 point 5), so the seam keeps its version (DEC-005 point 8).

### 5. A group that cannot be drawn clear is drawn spread

- **Cannot be drawn clear.** A branch cannot be drawn clear where its group has no room (point 3), where its middle leg is shorter than the least leg, or where it would cross another tie.
- **Would cross.** A branch would cross another tie where its middle leg or its last leg meets or runs along that tie, anywhere but at its own junction or at a point where both ties end. Every tie of every list one instance draws counts, the ties the connector tool spreads together: a trunk, a branch, and a tie in no group, straight or not. Crossings are judged on the legs, which point 3 keeps clear of every turn's arc.
- **The whole group spread.** Where any branch of a group cannot be drawn clear, every tie of the group is drawn as without the declaration, spread with the side's other ends, and the check states it (point 7). No tie is left out, and nothing a trunk made is drawn crossing.
- **Judged together, in rounds.** The engine judges every group of the instance at once, and draws spread each one with a branch that cannot be drawn clear. It then judges the groups left again, with the meeting points computed anew, until each can be drawn clear: at most one round for each group and one more, each comparing pairs of ties. Where branches of two groups cross, both groups are drawn spread. Where a tie that is no branch crosses a branch, the branch's group is drawn spread, and that tie as it is.
- **No other crossing judged.** A tie drawn as without the declaration draws whatever lies between its ends as it lies, and its crossings are no finding.

### 6. A tie component places its sign on the tie's own stretch

- **The rule.** A component that takes ends and draws its concept's sign ([visual-communication:DEC-036-concept-signs] point 2) places it on the tie's *own stretch*, never on a stretch another tie of its group runs. No check reads where a component places its sign: the graphic-design reviewer judges one on a shared stretch as an overlap (point 3).
- **A tie's own stretch.** A trunk's runs from its group's last junction to its other end, and a branch's from its junction to its other end. A line that shares no stretch, a tie in no group or in a group drawn spread among them, has its whole length as its own.
- **Two measures of the engine.** A reference to a line reads two more measures, `own-center` and `own-middle`: across and down, the point halfway along its own stretch, measured along the route's points as the scene holds them, a round turn taken sharp. They are new names of the engine, so they add to the format (DEC-005 point 1). A curved connector's are left to the change that builds curves.
- **The frame's centre where nothing is shared.** A connector with corners turns halfway between its ends, and a line's frame bounds its route. So on a line whose own stretch is its whole length, `own-center` and `own-middle` read what `center` and `middle` read.

### 7. What the check reports

Each finding below fails validation where it lies in a file the project can correct, and elsewhere, as in a released library version, asks for attention and names who can correct it ([visual-communication:DEC-002-files-and-validation] point 7), unless it is stated as a fact.

- **Fails validation:**
  - `trunk` on a part that repeats over no list of ties, or naming neither of its list's end fields. It lies in the version that declares the part, a drawing's in its brand's (DEC-011 point 8).
  - a formula that reads `own-center` or `own-middle` of an element that is no line, as one that reads what it may not reach (DEC-005 point 14).
- **Stated as a fact:**
  - a group drawn spread, naming each branch that cannot be drawn clear and why (point 5);
  - ties that meet one side of an item at their trunk end and form no group, since they do not draw alike or a connector part reads a line's frame, naming what differs or the formula (point 2). Where all of them are straight and alike, nothing is stated.

  Each lies in the content file, at the first of those ties in the ties' order. It names the language and the size key where it arises, as an end that is not found does (DEC-011 point 4), and what would let the group form: the content, the lock, or a formula's component.

### 8. An addition that breaks nothing, where tie components keep point 6

- **Optional.** `trunk` is an optional key of a part, and no formula that format 1 accepted reads `own-center` or `own-middle`. So every file format 1 accepted reads and draws as before, and none of point 7's findings arises from one ([visual-communication:DEC-003-change-over-time] point 3).
- **A change of look.** Declaring a trunk, withdrawing it, or naming the other end field changes only how a piece looks, so it breaks nothing (DEC-003 point 6): no tie is lost, and no draft fails, since a group that cannot be drawn clear is drawn spread (point 5). That holds where each tie component that draws a sign keeps point 6. One that does not, such as one a draft's lock keeps from before the measures, may stand its sign on a shared stretch once a trunk is declared, which the reviewer judges (point 6).

## Rationale

**Why the part that draws the list declares it, each drawing its own.** The founding record has a pattern decide the arrows between its items ([visual-communication:DEC-001-visual-communication-discipline] point 6), and a trunk is shared by the ties that meet one side, which only what draws the list sees (DEC-011 point 1). The end fields lie with the top because content writes their names on every tie (DEC-011, Rationale). Content never writes a trunk end: a trunk is form, which the record of layouts gives a brand's drawing (DEC-009 point 2), and declared by the top it would bind every drawing to a form it did not choose. On the part, a brand declares it in its drawing, which holds no list of its own ([visual-communication:DEC-034-brand-drawings] point 1).

**Why a brand's drawing needs no fit of its own.** A drawing fits where it takes what the content gives and each tie's ends are found under it (DEC-009 point 6, DEC-011 point 5). A trunk takes nothing the content gives, and loses no end (point 5), so a drawing that declares one fits where it fitted before.

**Why at one end field.** The page that asked spreads the ties that leave each filler, and shares a trunk only where they meet a slot. A tie that branched at both its ends would leave one trunk and join another, each placed by the other. No pattern needs that, and allowing it later is an addition (DEC-003 point 3).

**Why no switch chooses it.** Two parts with `when` on an option already let that option choose the trunk, so a switch would add nothing.

**Why only ties that draw alike, all or none.** The record of tie ends refuses one tie to several items, whose lines would share one trace, one state and one concept (DEC-011, Rationale, "Why one item for each end"). A trunk shares a stretch, so this record meets that reason point by point:
- **The trace.** Each tie stays one item, drawn whole with its own trace, so an edit taken back from a renderer tells the ties apart.
- **The state and the paint.** A shared stretch shows those of the tie the scene draws last. Ties that differ in either form no group, so a broken tie shows its state on its whole line. Compared as the scene holds them, paints group alike in every mode, as one scene serves every mode (DEC-005 point 5).
- **The arrowheads.** Grouped ties carry the same heads, so one head at the group's point says what is true.

The cost lies in a translucent paint, laid once for each tie. The condition arranges no item by what it holds, which no operator may (DEC-005 point 2): each tie is drawn, keeps its place in its list and its order in the drawing, and joins the items it names. It decides only whether one stretch may be drawn once for several ties, which a difference in how they draw would make false. Grouping only the alike among a side's ties would choose items by what they hold, so a list's ties on a side form one group or none.

**Why reach is read at the meeting points.** A branch's last leg runs level with its meeting point with its other end, never with that end's centre. Where the far item has several ties on its side, two ties between one pair of items meet it at two points. Read at the centres, the trunk could reach farther than a branch, whose last leg would then cross the trunk's middle leg.
- **No loop.** A meeting point comes from its item's side and the ends that meet it there, in their order, which read the items' centres and which groups are drawn as declared, never a route. The engine computes them anew in each round from the groups still drawn as declared, a set that only shrinks, so the rounds end. A group's own place among a side's ends is read from centres, so no meeting point waits on another.

**Why the trunk reaches least far, and the farthest-reaching branch leaves first.** Of two ties that lie one way from the group's point, the one that reaches farther leaves the trunk's first leg nearer the item. Its middle leg then lies nearer the item than the other's, and its last leg runs beyond the other's reach, so neither meets the other tie past its junction. The trunk leaves the first leg last, at its first turn, so it reaches least far, and each of its later legs turns away from a branch's end or stops short of it: the first leg is the one stretch every branch passes. Ties that lie the two ways never meet. Two that reach exactly as far one way run level and meet, so the engine judges every branch rather than trust the order.

**Why the least leg and the least gap.** A turn takes at most half the shorter of its two legs, so legs twice the group's radius long let each turn take its full radius, as the issue asks, and turns the group's radius apart share no part of a leg. Where the group's radius is zero, two branches could run a hair apart and read as one line. Twice the stroke width keeps a gap at least as wide as the line beside it, read from the stroke the group already draws, so no number is added.

**Why even places, then each branch's limit.** Even places give each turn the most room, as ends are spread along a side, and keep the branches off the item's column where room allows. A branch whose other end lies close across cannot reach its even place, though one nearer the item would serve it, so each junction moves only as far as it must. The rule is the record's, and the procedure that keeps it the reference's.

**Why the whole group is drawn spread, judged together, and stated as a fact.**
- **No tie is lost,** and nothing a trunk made is drawn crossing, as the issue asks. A draft that did not change never fails because a library added a trunk, as the record of tie ends refuses to fail a piece for what a release changed (DEC-011, Rationale, "Why an end is found once").
- **The whole group.** Spreading only the branch that cannot be drawn clear would move the group's point, and every other branch's place with it, into a drawing its pattern never declared.
- **Together.** Judged one list at a time, two lists that each hold the other's far end would draw by which went first. Judged at once, the groups give one drawing whatever order they lie in, as every order the engine gives is fixed (DEC-005 point 5).
- **A fact.** Every page still draws, so nothing is broken that the project must mend, as for a brand's drawing that does not fit (DEC-009 point 9, and its Rationale). A finding that asks for attention cannot be accepted, as a loss can (DEC-005 point 9), so a deliberate difference, such as one tie marked broken, would ask for attention at every check. The fact still reports a crossing rather than draw it.

**Why a sign stands on its tie's own stretch, by a measure of the engine.** A sign says which concept its tie carries (DEC-036 point 2), so on a shared stretch it would say that every tie there carries it. The junctions that bound a tie's own stretch are the engine's to compute, and the centre of a branch's frame may lie off its legs, even on the trunk's, so only a measure of the engine finds that stretch. It reads the frame's centre on every line that shares no stretch, so no piece moves. On a corner, the drawn turn passes within three tenths of its radius of the point, across and down, so a sign at least six tenths of the radius wide still stands on its line.

**Why the reviewer, and no check, judges clearance and a sign.** The issue asks that each tie keep clear of the shapes and the text it passes, by distances one piece's design chose. A branch's middle leg runs nearer its item's column, where that item's neighbours stand, than a connector's runs without a trunk, so the hazard is this record's own, and its judge is named: the reviewer's fault of overlaps. The engine never moves a branch to keep clear (DEC-005 point 2), and a check that measured clearance would judge every connector, with lengths every brand resolves, so it would be a record of its own. A sign on a shared stretch is an overlap the same reviewer reads.

**Why each tie stays whole.** A branch drawn from its junction alone would hang its end, its arrowhead and its state on another tie's line, and a medium with connectors of its own attaches a line to items, never to another line (DEC-005 point 5).

### Alternatives considered

- **An option of the tie's component.** Rejected: that component is given its own two ends, never the other ties that meet the side.
- **An arrangement field on each tie.** Rejected: two ties of one side could disagree, and an arrangement field sets how the pattern sizes or places its own item ([visual-communication:DEC-010-list-item-fields] point 3).
- **Branches that leave at the trunk's turn, as a fork.** Rejected: two turns would take one part of the trunk, and the issue asks for a junction clear of its turns.
- **A junction a pattern places by a formula, or by a length it declares.** Rejected: a formula that set a junction could read no route without a loop, and the group already gives every length a junction needs.
- **A branch that cannot be drawn clear left out, its finding failing,** or only a branch that would cross. Rejected: a library release that adds a trunk would drop a tie from a draft that did not change, and fail it, which the record of tie ends refuses for a lost end.
- **A sign on a leg of the tie's own, which its component finds from its end's frame.** Rejected: a component cannot read where a branch's junction lies, and such a sign would move on every tie that shares no trunk.
- **A check that a grouped tie's sign meets no shared stretch,** failing in the project's own unreleased component and asking for attention in a released library (DEC-002 point 7). Rejected: the reviewer already reads the fault, which only a component that does not keep point 6 makes. It is the choice where a sign off every shared stretch is held an invariant, since an invariant needs a check.
- **One named point of a connector line, read as `line.<point>.x` and `.y`,** through the grammar of a picture's exposed points. It leaves a reference's last step a measure of the frame (DEC-005 point 3), and grows by one name for each later point instead of two. Rejected for now: no second point is needed.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - DEC-005 point 1, "Where lengths come from", comes to say that a formula also reads, of a line, the point halfway along the stretch of its route that it alone runs (point 6).
  - DEC-005 point 2, "Connectors", comes to say that connectors join named elements, straight, with corners or curved. The ends that meet one side of an item take their places along it by their other ends' centres, then by the ties' order, and split it into equal parts. A connector with corners turns halfway between its ends. Its turns are round at its radius, each taking at most half the shorter of its two legs, and a leg that ends in an arrowhead counts to the head's base. Where the part that draws a list of ties declares a trunk end, the ties that meet one side of an item there and draw alike meet it at one point, the others branching off the trunk clear of its turns, or, where a group cannot be drawn so, spread as without the declaration. Connectors never route around obstacles (points 2, 3 and 5).
  - DEC-005 point 2, "No operator chooses, filters or sorts items by what they hold", comes to add that ties share a trunk only where they draw alike, which arranges no item: every tie is drawn, in its order, between its ends, and the condition decides only whether one stretch is drawn once for several ties (point 2).
  - DEC-005 point 3, "How a reference reads", comes to say that a reference ends with the measure it reads: of the frame, or, of a line, of the middle of its own stretch (point 6).
  - DEC-011 point 1, "Given its ends", comes to say that where a tie meets an end, how the ties that meet one side spread, and how they share a trunk where the part that draws them declares one, is the connector tool's (points 1 and 2).
  - DEC-036 point 2, "The component places it", comes to add that a tie's component places it on the tie's own stretch (point 6).
- **Read against this record, and left as they stand:** DEC-001 point 6, DEC-002 point 7, DEC-003 points 3, 6 and 8, DEC-005 points 5, 8, 9 and 14, DEC-009 points 2, 6 and 9, DEC-010 points 2 and 3, DEC-011 points 3, 4, 5 and 8, DEC-015 point 7 and DEC-034 point 1.
- **A renderer that draws connectors of its own,** as a whiteboard service's would. A branch's whole route, its shared stretch included, is in its points (DEC-005 point 5), so a medium that honours them keeps the trunk. One that cannot declares them approximated, and the loss is reported for every connector with corners, branches among them (DEC-005 point 9), though not named as a trunk's. A sign placed at fixed coordinates does not follow the medium's own route, as for every connector with corners. The change that builds such a renderer adds a hint to the scene only if it must name that loss.
- **The build,** a Task of its own once this record is accepted:
  - points 1 to 8 in the engine, the component schema and the checks, with tests in every renderer;
  - the starter connector's sign moved to the two measures, with the starter's own word on where that sign stands, in the same change: the measures move no sign without a trunk, and a starter that kept the frame's centre would stand its signs on shared stretches from the first trunk declared;
  - the capability's reference: the measures, the trunk, the procedure that places the junctions, the rounds, and the findings.
- **The page that asked for this record:** declaring its slot end a trunk end is a change of its own, after the build, with its own visual review.
