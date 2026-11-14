---
id: DEC-043
title: Ties that meet one side of an item may share a trunk, where their pattern declares it
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the ties that meet one side of an item each meet it at a point of their own, spread evenly along the side. A pattern may declare, for one of a list's two end fields, that the ties meeting one side of an item at that end *share a trunk*. They then meet the side at one point. The tie whose other end lies nearest that point, along the side, runs from there as any connector with corners does, and is the *trunk*. Each other tie, a *branch*, runs along the trunk's first leg, leaves it at a point clear of every turn, and turns once more to reach its own end. The branch that reaches farthest leaves nearest the item, so the ties of one trunk never cross. Each tie stays a line of its own, whole from end to end. A branch that cannot leave its trunk clear, or would cross another tie of its list, is reported. Without the declaration, ties spread evenly as before.

## Context

The connector tool joins the two ends of a tie, straight or with corners, and spreads the ends that meet one side of an item evenly along it, two of them at a third and at two thirds ([visual-communication:DEC-005-engine-and-plugins] point 2). Where a tie meets an end, and how the ties that meet one side spread, is the connector tool's ([visual-communication:DEC-011-tie-ends] point 1). So no pattern can ask for anything else.

[project-kit#3083](https://github.com/aleskalfas/project-kit/issues/3083) asks that a tie to an end which another tie already meets on the same side may branch off that tie and share its trunk, rather than meet the side at a point of its own. A slot that two capabilities fill, as on the showcase's page of how capabilities connect, would then take one line, which the second filler's line joins, in place of two arrowheads side by side. The issue asks that the branch leave the trunk clear of its turns and turn twice to its end, that ties sharing a trunk never cross, and that where a branch cannot avoid a crossing, the check report it rather than draw it.

Terms, beside those of the record of tie ends (DEC-011 point 1):
- A connector with corners runs in *legs*, straight stretches at right angles to one another, which meet at its *turns*. Its *first leg* at an end is the leg that meets that end.
- A tie *meets a side* of an end's item: the side that faces its other end, as the connector tool chooses it.

## Decision

**A pattern may declare one end field of a list of ties at which its ties share a trunk. The ties of that list that meet one side of one item at that end then meet it at one point. The one whose other end lies nearest is the trunk, and each other leaves the trunk's first leg clear of every turn, the farthest-reaching first, and turns once more to reach its own end. Without the declaration, ends spread evenly as before.**

### 1. A pattern declares a trunk at one end field of a list of ties

- **Beside the end fields.** A pattern that declares a list's two end fields (DEC-011 point 1) may name one of them the list's *trunk end*. The ties of that list that meet one side of one item at their trunk end then share a trunk there.
- **One end field at most.** At its other end, each tie meets its item as before.
- **The pattern's, in its own file.** No content field, option or switch chooses it, so it holds wherever the pattern draws the list.
- **In a top whose layouts a brand may draw,** the top declares the trunk end with the list's end fields in the layout, and every drawing of the layout takes it, as it takes the end fields (DEC-011 point 5).
- **Without it,** the ties that meet one side of an item spread evenly along it (DEC-005 point 2).

### 2. The ties that share a trunk meet their item at one point

- **A group.** The ties of one list that meet one side of one item at their trunk end form a *group* there. A tie joins a group only where its component draws a connector, and each connector it draws has corners. Any other tie meets the side at a point of its own, as without the declaration, since a straight line cannot run along a leg and leave it.
- **One point.** A group meets the side at one point, and counts as one end among the ends that meet that side, which spread evenly along it as the connector tool spreads them (DEC-005 point 2). It takes its place among them by the middle of the span that its ties' other ends' centres cover along the side. A group of one tie meets the side as that tie would alone.
- **The trunk.** The tie of the group whose other end's centre lies nearest the group's point, along the side, is the group's *trunk*, the first in its list where two lie as near. It runs from the group's point to its other end as any connector with corners does.
- **The branches.** Every other tie of the group is a *branch*. It runs from the group's point along the trunk's first leg, leaves that leg at a point of its own, its *junction*, with a turn, and turns once more to meet its other end square to its side. So a branch turns twice.

### 3. A branch leaves its trunk clear of every turn, the farthest-reaching first

- **On the trunk's first leg.** Each junction lies on the trunk's first leg, between the item and the trunk's first turn, and nearer the item than the branch's own other end. A trunk that turns nowhere has one leg, which runs to its other end.
- **The group's radius** is the greatest radius at which a connector of the group's ties turns, zero where none turns round.
- **Clear of every turn.** Each turn on the trunk's first leg, the trunk's own and each branch's turn off it, takes the stretch of the leg within the group's radius before its corner. No two turns take a common stretch, and no turn reaches the item.
- **Spread evenly.** The junctions spread evenly along the leg, from the group's radius past the item to the group's radius short of the trunk's first turn, or of its other end where it turns nowhere, as ends spread along a side.
- **The farthest-reaching first.** The branches leave in the order of how far their other ends' centres lie from the group's point, along the item's side: the farthest nearest the item, and the first in its list where two lie as far. So of the branches that lie one way from the group's point, each runs outside the trunk and outside every branch that leaves after it, and the ties of a group never cross.
- **Round turns.** A branch's turns are drawn round at its connector's radius and fitted to its legs, as every connector's turns are.
- **Around nothing.** A branch routes around no shape and no text, as no connector does (DEC-005 point 2). Its junction follows from its group's ends and radius alone.

### 4. Each tie stays a line of its own, whole from end to end

- **Its own connector.** A branch's connector runs from its start to its end, along the trunk between the group's point and its junction. It keeps its own trace, paints, arrowheads, state and concept, as every tie does (DEC-011 points 1 and 3). So the stretch of the trunk between the group's point and a junction is drawn by each tie that runs along it, in the order the scene draws them.
- **What the scene holds.** A branch's connector holds the points of its route, as any connector with corners does, and each of its ends names the element it meets and the side, as before (DEC-005 point 5). The scene holds nothing new, so the seam keeps its version (DEC-005 point 8).

### 5. What the check reports

- **A branch that cannot leave its trunk clear:** where the stretch point 3 spreads the junctions along has no length, or holds them less than the group's radius apart, or where the branch's junction lies no nearer the item than its own other end.
- **A branch that would cross another tie of its list:** where one of its legs past its junction meets another tie of its list, or runs along one.
- **Where each lies.** In the content file, at the tie, naming the pattern. The ties, the order of the items and the content's options decide where the items lie under the versions the lock names, so it names both mends, the content and the pattern, as a finding on an end does (DEC-011 point 8).
- **Open in this draft:** what is drawn in place of such a branch, how severe each finding is, and whether a draft's render holds back versions under which a branch would be reported, the questions file's Q1. Whether the check also measures how far a branch keeps from the shapes and the text it passes, its Q2.
- **In a pattern or a top, a trunk end that is not one of its list's two end fields** fails validation where it lies in a file the project can correct, and elsewhere, as in a released library version, asks for attention (DEC-005 point 14).
- **No other crossing is judged.** A trunk, and a tie that shares no trunk, are drawn as the connector tool draws them without the declaration, and their crossings are no finding.

### 6. An addition that breaks nothing

- **Optional.** The trunk end is an optional key of a list of ties' declaration, so every file format 1 accepted reads and draws as before, and none of point 5's findings arises from one ([visual-communication:DEC-003-change-over-time] point 3).
- **A change of look.** Declaring a trunk, withdrawing it, or naming the other end field changes only how a piece looks, so it breaks nothing (DEC-003 point 6).

## Rationale

**Why the pattern declares it.** The founding record has a pattern decide the arrows between its items ([visual-communication:DEC-001-visual-communication-discipline] point 6). A trunk is shared by every tie that meets one side of an item, which only the pattern sees, since it gives each tie's component only that tie's two ends (DEC-011 point 1). The issue asks that a pattern declare it, and that a pattern that does not draw as before.

**Why at one end field, beside the end fields.** A trunk lies at one end of each tie. The page that asked for it spreads the ties that leave each filler, and shares a trunk only where they meet a slot, so one declaration for the whole list would trunk both ends. Naming an end field ties the declaration to what it is about, where the end fields are declared. A tie that branched at both its ends would leave one trunk and join another, each placed by the other. No pattern needs that, and allowing it later is an addition (DEC-003 point 3).

**Why no option chooses it.** A choice is declared, never computed (DEC-005 point 1), and a declaration fixed in the pattern's file is one. No pattern needs to leave the trunk to content, and letting a switch on an option choose it later is an addition.

**Why the nearest tie is the trunk, and the farthest-reaching branch leaves first.** A branch's last leg runs level with its own end, from its junction to that end. Where it lies the trunk's way and reaches less far than the trunk, that leg crosses the trunk's leg that turns towards the trunk's end, so the trunk is the tie that reaches least far. Of two branches that lie one way, the one whose junction lies further from the item runs inside the other, so the one that reaches farthest leaves first. Branches that lie the two ways never meet, so one order serves both. The order rests on where the ends lie, never on what the ties hold, as the side's spread does (DEC-005 point 2), and the list's order only breaks a tie between two that lie as near.

**Why on the first leg.** It is the one stretch of the trunk that every branch passes: the trunk reaches least far, so each of its later legs turns away from a branch's end or stops short of it. Spread evenly along it, the junctions give each turn the most room the leg has, and no number is left for a pattern to declare.

**Why clear of every turn by the greatest radius.** A turn drawn round leaves its leg up to its radius before its corner, and the renderer may fit it smaller on a short leg, never larger. Clearing the greatest radius among a group's connectors clears each, so no two arcs meet on the trunk, and a branch reads as leaving the trunk, not as one of its turns.

**Why each tie stays whole.** A tie is one item, with its own trace, state and concept (DEC-011 point 3). A branch drawn from its junction alone would hang its end, its arrowhead and its state on another tie's line, and a medium with connectors of its own attaches a line to items, never to another line (DEC-005 point 5). Drawn whole, a branch is a connector whose points every renderer already draws, so the seam stays as it is. The cost: the shared stretch is drawn once for each tie that runs along it, so ties of one group in different paints, as under a state, show there the paint of the one drawn last. Their arrowheads at the group's point lie one on another.

**Why only a branch is judged for crossing.** A trunk, and a tie that shares none, take the route the connector tool gives without the declaration, which draws whatever lies between as it lies (DEC-005 point 2). A branch's legs past its junction are what the declaration adds, and the issue promises that a branch crosses no tie of its list.

**Why at the tie, in the content.** The ties, the order of the items and the content's options decide where each item lies under the pattern the lock names. Content is a file every project can correct, as it is for an end that is not found (DEC-011 point 8).

### Alternatives considered

- **An option of the tie's component.** Rejected: that component is given its own two ends, never the other ties that meet the side.
- **An arrangement field on each tie,** so content chooses tie by tie. Rejected: a trunk is shared by every tie that meets a side, so two such ties could disagree, and an arrangement field sets how the pattern sizes or places its own item ([visual-communication:DEC-010-list-item-fields] point 3).
- **One declaration for the whole list.** Rejected: it trunks both ends of every tie, where the page that asked spreads one end.
- **The first tie of the list as the trunk.** Rejected: a branch that lies its way and reaches less far would cross it.
- **Branches that leave at the trunk's turn, as a fork.** Rejected: two turns would take one stretch of the trunk, and the issue asks for a junction clear of its turns.
- **A branch drawn from its junction alone.** Rejected, as "Why each tie stays whole" says.
- **A junction a pattern places by a formula.** Rejected: a formula reads frames, not a route, and the junction follows from the ends and the radius.
- **A branch that routes around the shapes and the text it passes.** Rejected: the connector tool routes around nothing (DEC-005 point 2).

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - DEC-005 point 2, "Connectors", comes to say that connectors join named elements, straight, with corners or curved, with their ends spread evenly or, where a pattern declares that the ties meeting one side of an item share a trunk, meeting it at one point, the others branching off the trunk clear of its turns; and, as before, that they never route around obstacles.
  - DEC-011 point 1, "Given its ends", comes to say that where a tie meets an end, how the ties that meet one side spread, and how they share a trunk where the pattern declares one, is the connector tool's.
- **Read against this record, and left as they stand:**
  - DEC-001 point 6, since a pattern already decides the arrows between its items.
  - DEC-010 points 2 and 3, since the trunk end is no key an item carries, and no arrangement field names it.
  - DEC-011 points 3, 4 and 8, since each tie keeps one item for each end, an end is found as before, and the findings on ends stand.
  - DEC-005 points 5, 8 and 14, since the scene holds nothing new, and point 5 gives the findings this record adds.
  - DEC-003 points 3 and 6, since the trunk end is an addition, and declaring it a change of look.
- **[project-kit#3083](https://github.com/aleskalfas/project-kit/issues/3083)** builds points 1 to 6 in the engine and the component schema, with tests of two and three ties on one side, with a trunk and without, in both renderers.
- **The page on components,** in "Lists" and "Ties and connectors": the trunk end, how a group meets its side, where a branch leaves its trunk, and what is refused. **The page on checks:** the findings of point 5.
