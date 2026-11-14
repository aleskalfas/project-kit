---
id: DEC-043
title: Ties that meet one side of an item may share a trunk, where the part that draws them declares it
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the ties that meet one side of an item each meet it at a point of their own, spread evenly along the side. The part that draws a list of ties may name one of the list's two end fields its *trunk end*. The ties that meet one side of an item at that end, and draw alike, then meet it at one point. Of these, the tie that meets its other end nearest to that point, along the side, runs from there as any connector with corners does, and is the *trunk*. Each other tie, a *branch*, runs along the trunk's first leg, leaves it with a turn clear of every other turn, and turns once more to reach its own end. The branch that reaches farthest leaves nearest the item, so the ties of one trunk never cross. Where any branch of a group cannot be drawn so, the whole group is drawn spread, as without the declaration, and the check asks for attention. Each tie stays a line of its own, and its concept's sign stands on the stretch that it alone runs, which the engine gains a measure for. Without the declaration, ties spread evenly as before.

## Context

The connector tool joins the two ends of a tie, straight or with corners, and spreads the ends that meet one side of an item evenly along it, two of them at a third and at two thirds ([visual-communication:DEC-005-engine-and-plugins] point 2). Where a tie meets an end, and how the ties that meet one side spread, is the connector tool's ([visual-communication:DEC-011-tie-ends] point 1). So no pattern can ask for anything else.

[project-kit#3083](https://github.com/aleskalfas/project-kit/issues/3083) asks that a tie to an end which another tie already meets on the same side may branch off that tie and share its trunk, rather than meet the side at a point of its own. A slot that two capabilities fill, as on the showcase's page of how capabilities connect, would then take one line, which the second filler's line joins, in place of two arrowheads side by side. The issue asks that the branch leave the trunk clear of its turns, turn on the connector's radius and turn twice to its end, that ties sharing a trunk never cross, and that where a branch cannot avoid a crossing, the check report it rather than draw it.

Terms, beside those of the record of tie ends (DEC-011 point 1):
- A connector with corners runs in *legs*, straight stretches at right angles to one another, which meet at its *turns*. Its *first leg* at an end is the leg that meets that end. A leg that ends in an arrowhead counts to the head's base, where the line stops.
- A tie *meets a side* of an end's item: the side that faces its other end, as the connector tool chooses it. Its *meeting point* with an end is where it meets it: on that side, at the place the side's spread gives it, or at the point the end names.

## Decision

**The part that draws a list of ties may name one of the list's end fields its trunk end. The ties of the list that meet one side of one item there, and draw alike, then meet it at one point. The one that reaches least far is the trunk, and each other leaves the trunk's first leg with full turns, the farthest-reaching first. Where a branch cannot be drawn clear, its whole group is drawn spread and the check asks for attention. A tie's sign stands on the stretch it alone runs. Without the declaration, ends spread evenly as before.**

### 1. The part that draws a list of ties may declare a trunk at one of its end fields

- **On the part.** A part that repeats over a list of ties (DEC-011 point 1) may name one of the list's two end fields as its *trunk end*, with the key `trunk`. The ties of that list that meet one side of one item at their trunk end then share a trunk there, where point 2 lets them.
- **One end field at most.** At its other end, each tie meets its item as before.
- **Fixed in the part.** `trunk` takes an end field's name, never a switch, and no content field or option of a tie chooses it. Where `when` chooses between two parts that draw one list, each declares its own, as it gives any value of its own.
- **Each drawing its own.** A trunk is how a list's ties are drawn, never what content gives them, so it lies with the parts that draw the list: a pattern's own, the top's own drawing of a layout, or a brand's drawing of it ([visual-communication:DEC-009-layout-defaults] points 1 and 2). Each drawing declares its own trunks, and one whose part declares none draws the list's ties spread, whatever another drawing of the layout declares.
- **Without it,** the ties that meet one side of an item spread evenly along it (DEC-005 point 2).

### 2. The ties that share a trunk meet their item at one point

- **A group.** The ties of one list that meet one side of one item at their trunk end form a *group* there, where each draws a connector with corners and all of them draw alike: the same component, under the same options, in the same paint and the same state, with the same stroke and the same arrowheads.
  - **Ties that differ** form no group. Each meets the side at a point of its own, as without the declaration, and the check asks for attention (point 7).
  - **Straight ties** form none either, since a straight line cannot run along a leg and leave it. Where all of them are straight and alike, nothing is reported.
  - **A tie whose trunk end names a point** its item exposes meets no side, so it joins no group, and ends at that point as before (DEC-011 point 2).
- **One point.** A group meets the side at one point, and counts as one end among the ends that meet that side, which spread evenly along it (DEC-005 point 2). It takes its place among them by the middle of the span that its ties' other ends' centres cover along the side, as each end takes its place by its other end's centre, and then by the place of its first tie in its list. A group of one tie meets the side as that tie would alone.
- **How far a tie reaches.** A tie of a group *reaches* as far as its meeting point with its other end lies from the group's point, along the side.
- **The trunk.** The tie of the group that reaches least far is its *trunk*, the first in its list where two reach as far. It runs from the group's point to its other end as any connector with corners does, turning halfway between them.
- **The branches.** Every other tie of the group is a *branch*. It runs from the group's point along the trunk's first leg, leaves that leg at its *junction* with a turn, runs to the level of its meeting point with its other end, and turns once more to meet that end square to its side. So a branch turns twice. Past its junction it runs its *middle leg*, then its *last leg*.

### 3. A branch leaves its trunk with full turns, the farthest-reaching first

- **Two least lengths.** The group's *radius* is the greatest radius at which a connector of the group turns, zero where none turns round. Its *least leg* is twice its radius, and its *least gap* is its radius, neither less than twice the group's stroke width.
- **Full turns.** Each leg of a branch next to a turn is at least the least leg long, so each of its turns takes its full radius, since a turn takes at most half the shorter of its two legs. So its junction lies at least the arrowhead's length at the group's point plus the least leg from the item, and its middle leg and its last leg are each at least the least leg long.
- **The stretch.** The junctions lie on the trunk's first leg, on a *stretch* from the arrowhead's length plus the least leg past the item, to the least gap short of where that leg ends: at the trunk's first turn, or, where the trunk turns nowhere, at its other end.
- **Apart.** Neighbouring junctions lie at least the least gap apart, and so do the last junction and the end of the trunk's first leg. So no two turns take a common stretch of the leg, and no two branches lie nearer than twice their stroke width.
- **The farthest-reaching first.** The branches leave in the order of how far they reach, the farthest nearest the item, and the first in its list where two reach as far. So of the ties that lie one way from the group's point, each runs outside every tie that leaves after it and outside the trunk, so two ties of a group meet only where they reach exactly as far one way (point 5).
- **A branch's limit.** A branch's *limit* is the least leg short of its meeting point with its other end, along the trunk's first leg, counted to the base of an arrowhead it ends in there. A junction past it would leave the branch's last leg too short.
- **Evenly where they fit.** A junction's *even place* is where the junctions and the end of the trunk's first leg split that leg into equal parts, in their order. Where each even place lies on the stretch, at least the least gap from the next, and within its branch's limit, the junctions take their even places.
- **Within each branch's limit where they do not.** Otherwise each junction moves only as far as it must, in their order and in two passes:
  1. From the item outward, each lies no nearer the item than the stretch's start, or the least gap past the junction before it.
  2. From the end of the trunk's first leg inward, each lies no further out than its branch's limit, the stretch's end, or the least gap short of the junction after it.

  A group whose first junction then lies nearer the item than the stretch's start has no room (point 5).
- **Round turns, around nothing.** A branch's turns are drawn round at its connector's radius, as every connector's are, and it routes around no shape and no text (DEC-005 point 2). Its junction follows from its group's meeting points, radius, stroke and arrowheads alone.
- **Clear of shapes and text by its layout.** How far a branch keeps from the shapes and the text it passes is no check's: the drawing's layout gives its ties their room, and the graphic-design reviewer judges a line through a text or a card, its fault of overlaps ([visual-communication:DEC-015-viewing-step-and-reviewer] point 7).

### 4. Each tie stays a line of its own, whole from end to end

- **Its own connector.** A branch's connector runs from its start to its end, along the trunk's first leg between the group's point and its junction. It keeps its own trace, paints, arrowheads, state and concept, as every tie does (DEC-011 points 1 and 3).
- **Drawn once for each tie.** The stretch of the trunk's first leg between the group's point and a junction is drawn by each tie that runs along it, in the order the scene draws them. Since they draw alike, an opaque paint shows there as one line, and their arrowheads at the group's point as one head. A translucent paint shows darker there, laid once for each tie.
- **What the scene holds.** A branch's connector holds the points of its route, as any connector with corners does, and each of its ends names the element it meets and the side, as before (DEC-005 point 5). The scene holds nothing new, so the seam keeps its version (DEC-005 point 8).

### 5. A group that cannot be drawn clear is drawn spread

- **Cannot be drawn clear.** A branch cannot be drawn clear where its group has no room on the stretch (point 3), where a turn of it cannot take its full radius, its middle leg being shorter than the least leg, or where it would cross another tie of its list.
- **Would cross.** A branch would cross another tie of its list where its middle leg or its last leg meets that tie, or runs along it, anywhere but at the branch's own junction, where its middle leg leaves the trunk's first leg, or at a point where both ties end. Crossings are judged on the legs of the routes, which point 3 keeps clear of every turn's arc. Every other tie of the list counts: the trunk, a branch of the same group or of another, and a tie in no group, straight or not.
- **The whole group spread.** Where any branch of a group cannot be drawn clear, every tie of the group is drawn as it would be without the declaration, meeting the side at a point of its own, spread with the side's other ends, and the check asks for attention (point 7). No tie is left out, and nothing the trunk made is drawn crossing.
- **Groups fall back together.** The engine judges every group against the routes the list's ties take with every group that is still drawn as declared. Each group with a branch that cannot be drawn clear is drawn spread at once. Since a group drawn spread moves the meeting points on the side it meets, the engine then judges the groups left again, until each can be drawn clear. A group drawn spread is not judged again in that scene. So the drawing rests on no order among groups, as every order the engine gives is fixed (DEC-005 point 5):
  - where branches of two groups cross, both groups are drawn spread;
  - where a tie in no group, a straight one among them, crosses a branch, the branch's group is drawn spread, and that tie is drawn as it is.
- **No other crossing judged.** A tie drawn as without the declaration, a group drawn spread among them, draws whatever lies between its ends as it lies, and its crossings are no finding.

### 6. A tie's sign stands on the stretch it alone runs

- **On its own line, never on a shared stretch.** Where a tie's component draws its concept's sign ([visual-communication:DEC-036-concept-signs] point 2), it places the sign on the tie's own line, on the stretch no other tie of its group runs.
- **A tie's own stretch.** A trunk's own stretch runs from the junction nearest its first turn to its other end, and a branch's from its junction to its other end. A tie in no group, or in a group drawn spread, shares no stretch, so its own stretch is its whole route.
- **Two measures of the engine.** A reference to a line the connector tool draws reads two more measures, `own-center` and `own-middle`: across and down, the point halfway along its own stretch, measured along its legs as its route's points give them, the turns taken sharp. They are new names of the engine, so they add to the format (DEC-005 point 1). A formula that reads either of an element that is no such line reads what it may not reach.
- **Halfway, as today, without a trunk.** A connector with corners turns halfway between its ends, and a straight one turns nowhere, so the point halfway along a whole route is the centre of the connector's frame. There `own-center` and `own-middle` read what `center` and `middle` read. So a sign placed by them moves only on a tie that shares a trunk.

### 7. What the check reports

Each finding below fails validation where it lies in a file the project can correct, and elsewhere, as in a released library version, asks for attention and names who can correct it ([visual-communication:DEC-002-files-and-validation] point 7), unless it says otherwise.

- **Fails validation:**
  - `trunk` on a part that repeats over no list of ties, or that names neither of its list's end fields. It lies in the version that declares the part: a pattern's or a top's, or, for a drawing, its brand's (DEC-011 point 8).
  - a formula that reads `own-center` or `own-middle` of an element that is no line the connector tool draws, as one that reads what it may not reach (DEC-005 point 14).
- **Asks for attention, never failing:**
  - a group drawn spread because a branch cannot be drawn clear, naming each such branch and why (point 5);
  - ties that meet one side of an item at their trunk end and do not draw alike, naming what differs (point 2).

  Each lies in the content file, at the first of those ties in its list. It names both mends, the content and the lock, since the ties, the order of the items and the content's options decide where each item lies under the versions the lock names, as for an end that is not found (DEC-011 point 8).

### 8. An addition that breaks nothing

- **Optional.** `trunk` is an optional key of a part, and no formula that format 1 accepted reads `own-center` or `own-middle`. So every file format 1 accepted reads and draws as before, and none of point 7's findings arises from one ([visual-communication:DEC-003-change-over-time] point 3).
- **A change of look.** Declaring a trunk, withdrawing it, or naming the other end field changes only how a piece looks, so it breaks nothing (DEC-003 point 6). No tie is lost to it and no draft fails for it, since a group that cannot be drawn clear is drawn as before (point 5).
- **A sign that moves nowhere else.** A component that comes to place its sign by `own-center` and `own-middle` moves it only on a tie that shares a trunk (point 6).

## Rationale

**Why the part that draws the list declares it.** The founding record has a pattern decide the arrows between its items ([visual-communication:DEC-001-visual-communication-discipline] point 6). A trunk is shared by every tie that meets one side of an item, which only what draws the list sees, since it gives each tie's component that tie's two ends alone (DEC-011 point 1). The issue asks that a pattern declare it, and that a pattern that does not draw as before. On the part, the declaration lies where each drawing already holds what it draws: a pattern in its own file, a top in its own drawing, and a brand in its drawing, which holds no list of its own.

**Why each drawing declares its own, and not the top for every drawing.** The end fields lie with the top because content writes their names on every tie, so they are names a piece uses (DEC-011, Rationale), and content gives what the top declares, never what a brand's drawing declares (DEC-009 point 5). A trunk end is no such name: content never writes it, so that reason does not reach it. It is form, how the ties are drawn, and the record of layouts gives a brand's form to its drawing (DEC-009 point 2). Declared by the top, a trunk would bind every brand's drawing to a form it did not choose.

**Why a brand's drawing needs no fit and no finding of its own.** A brand's drawing fits where it takes what the content gives, and where each tie's ends are found under it (DEC-009 point 6, DEC-011 point 5). A trunk takes nothing the content gives, and a group that cannot be drawn clear is drawn spread, losing no end. So a trunk changes nothing a fit reads, and a drawing that declares one fits where it fitted before. Nor is a trunk a field the top declares, so the findings on what a drawing takes do not read it (DEC-009 point 9). What a drawing can get wrong, a `trunk` that names no end field, lies in its brand's version, as every finding on what a drawing declares does (DEC-011 point 8).

**Why at one end field.** A trunk lies at one end of each tie. The page that asked for it spreads the ties that leave each filler, and shares a trunk only where they meet a slot, so one declaration for the whole list would trunk both ends. A tie that branched at both its ends would leave one trunk and join another, each placed by the other. No pattern needs that, and allowing it later is an addition (DEC-003 point 3).

**Why no switch chooses it.** A choice is declared, never computed (DEC-005 point 1), and a word the part writes is one. No pattern needs to leave the trunk to content, and letting a switch on an option choose it later is an addition.

**Why only ties that draw alike.** The record of tie ends gives each end an item of its own, since one tie to several items would draw several lines that share one trace, one state and one concept: a state that marks one of them broken would mark them all, and an edit taken back from a renderer could not tell them apart (DEC-011, Rationale, "Why one item for each end"). A trunk brings back a shared line, on the trunk's first leg, so the record meets that reason point by point:
- **The trace.** Each tie stays one item, drawn whole as a connector of its own with its own trace, so an edit taken back from a renderer still tells the ties apart.
- **The state and the paint.** Drawn once for each tie, the shared stretch shows the state or the paint of whichever tie the scene draws last, for every tie or for none. Ties that differ in either form no group, so a broken tie never hides its state on a trunk: it keeps a point of its own, and its state shows on its whole line.
- **The arrowheads.** One head at the group's point reads as each tie carrying one. Ties grouped carry the same heads, so it says what is true.

What alike ties share says only that they run one way, which is what a trunk says. The cost lies in a translucent paint, which shows darker on the shared stretch, laid once for each tie. The check asks for attention where ties that differ meet one side, since the pattern declared a trunk that content's choices keep from forming, and someone is expected either to choose alike or to let the ties spread.

**Why one group on a side, or none.** Where some of a side's ties draw alike and others do not, a rule would have to choose which alike set is the group, and the ties left spread beside a trunk on the same side would meet its branches in crossings that no order settles. All the side's ties spread instead, as they are drawn today.

**Why reach is read at the meeting points.** A branch's last leg runs level with its meeting point with its other end, never with that end's centre. Where the item at the other end has several ties on its side, its meeting points lie away from its centre (DEC-005 point 2), so two ties between one pair of items, whose centres lie level, meet the far item at two points. Read at the centres, the trunk could reach farther than a branch, whose last leg would then cross the trunk's middle leg. Read at the meeting points, it never does.
- **No loop.** A tie's meeting point with its other end comes from that item's side and the order of its spread, which reads the centres of the items, never a route. Only one end field is the trunk end, so a tie's other end is never its own group's point.
- **The group's own place** among a side's ends is read from centres, as every end's is, so that no meeting point waits on another.

**Why the trunk reaches least far, and the farthest-reaching branch leaves first.** Take two ties that lie one way from the group's point. The one that reaches farther leaves the trunk's first leg nearer the item, so its middle leg lies nearer the item than the other tie's middle leg, and its last leg runs beyond the other tie's reach. Neither of its legs past its junction then meets the other tie, but where its middle leg leaves the leg they share. The trunk leaves that leg last, at its first turn, so it is the tie that reaches least far. Ties that lie the two ways never meet, so one order serves both. The order rests on where the ties meet their other ends, never on what they hold, and the list's order only breaks a tie. Two ties that reach exactly as far one way run level, and meet where their last legs overlap, so the check judges every branch for crossings (point 5) rather than trust the order alone.

**Why on the first leg.** It is the one stretch of the trunk that every branch passes. The trunk reaches least far, so each of its later legs turns away from a branch's end or stops short of it.

**Why the least leg and the least gap.** A turn drawn round takes at most half the shorter of its two legs, and a leg that ends in an arrowhead counts to the head's base. So legs at least twice the radius let each turn take its full radius, as the issue asks of a branch, and turns at least a radius apart take no common stretch of the leg. With no radius, both lengths would vanish: two branches could run a hair apart and read as one line, or a branch could run along its item's side. Twice the stroke width keeps a gap at least as wide as the line beside it, and is read from the stroke the group already draws, so no number is added.

**Why even places, then each branch's limit.** Even places give each turn the most room the leg has, spread as ends are spread along a side, and keep the branches off the item's column where room allows. A branch whose other end lies close across cannot reach its even place, though a place nearer the item would serve it. Moving each junction only as far as it must keeps the order, the least gap and the even places where they hold, and draws a group that even places alone would have to spread. It reads only what the group already gives, so no number is left for a pattern to declare.

**Why the whole group is drawn spread.**
- **No tie is ever lost.** The content says each tie, and the drawing shows each.
- **Nothing the trunk made is drawn crossing,** as the issue asks.
- **No draft fails for a library's look.** A draft that did not change never fails because a library added a trunk, as the record of tie ends refuses to fail a piece the project did not change for what a release changed (DEC-011, Rationale, "Why an end is found once").
- **The drawing is then exactly today's.** Where the group cannot be drawn clear, the reader sees the spread drawing every piece has had.

The finding asks for attention, never failing: no invariant is broken in the drawing, and someone is expected to act on the content or the lock, or accept the spread (DEC-002 point 7). Spreading only the branch that cannot be drawn clear would move the group's point among the side's ends, and every other branch's place with it, so the group would be judged anew in a drawing its pattern never declared.

**Why groups fall back together, and again.** A group drawn spread moves the meeting points on its side, which may bring another group's branch onto a tie it cleared before. Judging every group at once, and again until none fails, gives one drawing whatever order the groups are listed in, and it ends, since a group never takes its trunk back.

**Why a tie's sign stands on the stretch it alone runs, by a measure of the engine.** A sign says which concept its tie carries (DEC-036 point 2). On a shared stretch it would stand on every tie that runs there, saying they all carry its concept. A component places a sign by formulas, and a formula reads frames, never routes, so it cannot find where a tie's own stretch lies. The centre of a branch's frame, where a component reads `center` and `middle`, need not lie on any of the branch's legs, and may lie on the trunk's. The engine knows the route, so a measure it computes gives every component the same place. Measured along the legs as the route gives them, it is the centre of the frame for every tie that shares no trunk, so no piece moves. On a corner, the drawn turn passes within three tenths of its radius of the point, across and down, so a sign at least six tenths of the radius wide still stands on its line.

**Why each tie stays whole.** A tie is one item, with its own trace, state and concept (DEC-011 point 3). A branch drawn from its junction alone would hang its end, its arrowhead and its state on another tie's line, and a medium with connectors of its own attaches a line to items, never to another line (DEC-005 point 5). Drawn whole, a branch is a connector whose points every renderer already draws, so the seam stays as it is.

**Why at the tie, in the content, naming the content and the lock.** The ties, the order of the items and the content's options decide where each item lies under the versions the lock names. Content is a file every project can correct, and the lock moves to versions under which the group draws clear, as for an end that is not found (DEC-011 point 8).

**Why no check of how far a branch keeps from shapes and text.** The issue's What asks that each tie keep clear of the shapes and the text it passes, by distances one piece's design chose. This record brings a branch's middle leg nearer its item's column, where that item's neighbours stand, than any connector's middle leg comes today, so the hazard is this record's own. So its check is named: the graphic-design reviewer's fault of overlaps, a line through a text or a card (DEC-015 point 7). The engine never moves a branch to keep clear, since a connector routes around nothing (DEC-005 point 2). A check that measured it would judge every connector, not only branches, and would need lengths every brand resolves, so it is a record of its own.

### Alternatives considered

- **An option of the tie's component.** Rejected: that component is given its own two ends, never the other ties that meet the side.
- **An arrangement field on each tie,** so content chooses tie by tie. Rejected: a trunk is shared by every tie that meets a side, so two such ties could disagree, and an arrangement field sets how the pattern sizes or places its own item ([visual-communication:DEC-010-list-item-fields] point 3).
- **One declaration for the whole list.** Rejected: it trunks both ends of every tie, where the page that asked spreads one end.
- **The trunk end declared with the list's end fields, by the top for every drawing.** Rejected: content never writes it, so it is form, which is each drawing's ("Why each drawing declares its own").
- **The first tie of the list as the trunk.** Rejected: a branch that lies its way and reaches less far would cross it.
- **Reach read at the other ends' centres.** Rejected: two ties between one pair of items meet the far item at two points, so the order could make a branch cross its trunk.
- **A group of whichever ties draw alike, the others spread beside it, or a group of every tie whatever it draws.** Rejected, as "Why one group on a side, or none" and "Why only ties that draw alike" say.
- **Branches that leave at the trunk's turn, as a fork.** Rejected: two turns would take one stretch of the trunk, and the issue asks for a junction clear of its turns.
- **A branch drawn from its junction alone.** Rejected, as "Why each tie stays whole" says.
- **Junctions at their even places only.** Rejected: a branch whose end lies close across could not take its place, and its group would be drawn spread though a nearer junction served it.
- **Junctions placed as near the item as they fit.** Rejected: every branch would run its middle leg beside its item's column, where the even places leave room.
- **A junction a pattern places by a formula, or by a length it declares.** Rejected: a formula reads frames, not a route, and the junction follows from what the group already gives.
- **A branch that cannot be drawn clear left out, its finding failing.** Rejected: a library release that adds a trunk would drop a tie from a draft that did not change, and fail it, which the record of tie ends refuses for a lost end.
- **A group with no room drawn spread, and a branch that would cross left out.** Rejected: the crossing case still loses a tie and fails a draft that did not change, for a look a library chose.
- **Only the branch that cannot be drawn clear drawn spread.** Rejected, as "Why the whole group is drawn spread" says.
- **A sign on a leg of the tie's own, which its component finds from its end's frame.** Rejected: a component cannot read where a branch's junction lies, and such a sign would move on every tie that shares no trunk.
- **A branch that routes around the shapes and the text it passes.** Rejected: the connector tool routes around nothing (DEC-005 point 2).

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - DEC-005 point 1, "Where lengths come from", comes to say that a formula also reads, of a line the connector tool draws, the point halfway along the stretch of its route that it alone runs.
  - DEC-005 point 2, "Connectors", comes to say that connectors join named elements, straight, with corners or curved, with their ends spread evenly, or, where the part that draws a list of ties declares that the ties meeting one side of an item share a trunk, meeting it at one point, the others branching off the trunk clear of its turns; and, as before, that they never route around obstacles.
  - DEC-005 point 3, "How a reference reads", comes to say that a reference ends with the measure it reads: of the frame, or, of a line the connector tool draws, of the middle of its own stretch.
  - DEC-011 point 1, "Given its ends", comes to say that where a tie meets an end, how the ties that meet one side spread, and how they share a trunk where the part that draws them declares one, is the connector tool's.
- **Read against this record, and left as they stand:**
  - DEC-001 point 6, since a pattern already decides the arrows between its items.
  - DEC-009 points 2, 6 and 9, since a trunk is a drawing's form, adds nothing to whether a drawing fits, and is no field the top declares.
  - DEC-010 points 2 and 3, since the trunk end is no key an item carries, and no arrangement field names it.
  - DEC-011 points 3, 4, 5 and 8, since each tie keeps one item for each end, an end is found as before, the end fields stay the top's, and the findings on ends stand, this record's lying and naming their mends as they do.
  - DEC-036 point 2, since the component still places the sign, and this record says only where a tie's stands.
  - DEC-005 points 5, 8, 9 and 14, since the scene holds nothing new, the seam keeps its version, and point 7's findings take point 14's severities.
  - DEC-003 points 3, 6 and 8, since the trunk end and the measures are additions, declaring a trunk is a change of look, and no tie is lost, so no version is held back for it.
  - DEC-002 point 7 and DEC-015 point 7, since point 7's severities and the reviewer's faults stand as they decide them.
- **A renderer that draws connectors of its own,** as a whiteboard service's would, attaches each line to the items its ends name (DEC-005 point 5). A trunk and its branches attach alike, and the scene marks no shared stretch, so such a renderer cannot tell a branch from a tie that shares no trunk, and cannot report losing the trunk (DEC-005 point 9). The change that builds it adds what it needs to the scene, with the seam's version as DEC-005 point 8 decides.
- **The change that builds it,** which [project-kit#3083](https://github.com/aleskalfas/project-kit/issues/3083) asks for, builds points 1 to 8 in the engine and the component schema, with tests of two and three ties on one side, with a trunk and without, in both renderers, of a group drawn spread, and of the two measures.
- **The starter's connector** places its sign by `own-center` and `own-middle`, in place of the centre of its line's frame, in a release of the starter. Its description and its comment say the sign stands halfway along the line, and come to say it stands halfway along the stretch the tie alone runs. For every tie that shares no trunk, it stands where it stands today.
- **The page on components:** in "References", the two measures; in "Ties and connectors", the trunk end, how a group meets its side, where a branch leaves its trunk, and when a group is drawn spread. That section says a connector with corners turns twice, halfway between its ends, which comes to hold of every connector but a branch, which turns at its junction. **The page on checks:** the findings of point 7.
