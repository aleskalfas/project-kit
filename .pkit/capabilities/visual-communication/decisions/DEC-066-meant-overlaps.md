---
id: DEC-066
title: A part names the parts it is drawn over on purpose
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a component may place one of its parts on another on purpose, such as a badge on a card's corner. The check of boxes that overlap cannot tell that from a fault. Unless the component says so, the check asks for attention at that place in every piece that uses the component, for ever. So a part may name the parts of its own component that it is drawn over on purpose, and the check leaves out each pair named so. The engine carries the names into the scene, which is what the check reads.
- **Only the check of overlaps.** The check of edges that nearly line up still compares the pair. That an overlap is meant says nothing of where the two parts' edges lie.
- **A library the capability ships** says it as it makes any other change: in the version it is building, which takes a patch at least.

## Context

[visual-communication:DEC-046-faults-lower-grades] point 3 has two checks do the arithmetic of craft among the *siblings* of each scene, the elements one group holds directly. One reports edges that nearly line up. The other reports two siblings whose boxes overlap, where neither holds the other. Both ask the reviewer for attention and never fail, since a component may place one part on another on purpose, such as a badge on a corner. The point leaves it to the work that builds the checks to settle how a component says an overlap is meant, so that it is not reported for ever. Where that adds a field, the work drafts the record first (COR-065 point 3).

[project-kit#3327](https://github.com/aleskalfas/project-kit/issues/3327) is that work. It asks three things: how a component says it; whether saying it also leaves the pair out of the check of edges that nearly line up; and how a library the capability ships says it, in a new version ([visual-communication:DEC-013-shipped-library-releases]).

The answer meets four things that already hold:
- **Parts are drawn in the order written,** and the scene keeps that order among each group's elements. So of two siblings, the later is drawn over the earlier ([visual-communication:DEC-005-engine-and-plugins] point 5). A part's name ends the trace id of what it draws. Parts are written in a component's `parts`, in a top's drawing of a layout, and in a brand's drawing ([visual-communication:DEC-009-layout-defaults] point 1, [visual-communication:DEC-034-brand-drawings] point 1).
- **The checks of boxes read the scene:** each element's box and trace id. They read no component's file.
- **A check's reach** names each kind of place the check leaves out, and the reviewer judges a kind left out on the image first ([visual-communication:DEC-063-where-a-check-measures] points 1 and 4).
- **A released version never changes.** A change goes into the version being built, and raises its number as far as the change needs (DEC-003 point 6, DEC-013 points 3 and 4).

## Decision

**A part names, under `over`, the parts written before it in the same `parts` that it is drawn over on purpose. The engine carries those names into the scene, and the check of boxes that overlap leaves out each pair named so. No other check does.**

### 1. A part names the parts it is drawn over on purpose

- **`over`** is a key any part may take: a list of the names of parts written before it in the same `parts`, and so drawn before it. It says that the part lies over each of them on purpose. A badge drawn over a card's box writes `over: [box]`.
- **Wherever parts are written:** in a library's component or a piece's own, in a top's drawing of a layout, and in a brand's drawing. It names parts of that same `parts` alone: never a part inside a component it places, and never one item of a list. A part that repeats over a list is named whole, as the check compares it.
- **Always, or not at all.** It takes no switch. Wherever the two parts overlap, under any option, at any key and in any language, the overlap is meant. Where they do not overlap, or where the check never compares them, as where one is a line, it changes nothing.
- **Refused when the component is read:** a name that is no part of the same `parts`, the part's own name, the name of a part written after it, and a name written twice. A refused name says nothing, so the check reports that pair as before. The order of drawing decides which part lies over which, so a part that named one drawn after it would say the opposite of what is drawn.

### 2. The scene carries it, and the check of overlaps leaves each such pair out

- **In the scene.** The element that a part with `over` draws holds `over`: the trace ids of what the parts it names draw. A scene already says which component drew a group (DEC-005 point 5). This adds what that component meant of where its parts lie. The seam's version stays as it is, since no plugin must read anything differently (DEC-005 point 8).
- **The check of boxes that overlap** leaves out two siblings where the later names the earlier so. Its reach names that kind of place among those it leaves out, citing this point (DEC-063 point 1).
- **Every other reading of the pair stays.** The viewing step still names a text that a part drawn after it covers, where it reads what covers a text ([visual-communication:DEC-037-text-the-page-hides] point 1). The check of contrast still measures a text against the fill under it. The reviewer still judges the pair on the image, as at every place a check's reach leaves out (DEC-046 point 3, DEC-063 point 4). A component's word that an overlap is meant explains why the check is silent there. It never says that the drawing reads well.

### 3. The check of edges that nearly line up compares the pair as before

- **`over` speaks of an overlap, not of a line.** The check of edges that nearly line up still compares the pair's edges and centres, as it compares every two siblings neither of which holds the other (DEC-046 point 3).
- **A near miss still points at a fault.** Two edges that differ by more than a pixel and by less than the brand's smallest step of space lie at no spacing a brand offers (DEC-046 point 3), whether or not their parts overlap. A tab meant to lie over its panel's top edge, flush with the panel's left edge, may still lie off that edge by more than a pixel and by less than a step.
- **What it costs.** A part centred on another's edge, such as a dot on a card's corner, has its own edge on that side half its size away from the other's. Where the part measures less than twice the brand's smallest step across, the check reports that near miss, which follows from a line the check does not compare: a centre set on an edge. The report asks for attention and fails nothing, as every near miss does.
- **Not decided here:** whether a component may say that a near miss is meant.

### 4. A library the capability ships says it in the version it builds

- **In the version being built.** A component of a library the capability ships, whose parts overlap on purpose, comes to say so in the library's version being built. A released version never changes, so it never says so (DEC-003 point 6, DEC-013 point 4). Whoever maintains the capability judges which overlaps are meant, as the owner of any library does.
- **A patch at least.** Saying it, or ceasing to, changes no look and nothing that a piece or a library built on the library names. So it is neither a break nor an addition (DEC-003 point 6), and the version being built takes a patch at least, as for any change to it (DEC-013 point 3).
- **The release it needs is one that reads `over`.** An older engine refuses a key it does not know (DEC-003 point 1). So the change that teaches the engine `over` lands no later than the first shipped version that uses it. That version's release then names the capability's current version, as every shipped version's release does (DEC-013 point 3).
- **A piece under a released version** is still asked for attention at that overlap, until its lock moves to a version that says it is meant. Who moves the lock is what the piece's state says (DEC-003 point 8). The attention fails nothing meanwhile.

## Rationale

**Why the component says it, not each piece.** The overlap is the component's design. Every piece that uses the component draws it, and none of their authors chose it. Said once, where the parts are written, it reaches every piece, and holds as long as the parts it names do. A piece that accepted the overlap, as it accepts a renderer's loss, would have to say it again in every piece: the repetition this record removes.

**Why a part names parts.**
- **Not a flag on the part.** `over: true` would leave out every overlap of that part. A badge meant to lie over the card's box, but pushed over its head by a long title, would then go unreported. Naming each part keeps the check's attention on every pair the component did not mean.
- **Not a list of pairs on the component.** It would say the same thing, but away from the parts it names. Each top's drawing of a layout, and each brand's drawing, would need such a list of its own. And a pair would have to say which part lies on top, which the order of drawing already says. On the part, the key lies beside the place it explains.

**Why only parts drawn before it.** What the component means is that one part lies on top. The order of drawing decides which does (DEC-005 point 5), so the key reads in that order. A badge moved before the box would be hidden under it, which is a fault. The reading then refuses the name, and the check reports the pair again, rather than stay silent over a badge no one can see.

**Why the scene carries it.** The check reads scenes, and compares siblings by their trace ids. A check that read each component's file would have to find again, for each group, the version and the drawing that drew it, which the engine has already done. A scene says which component drew each group for the same reason.

**Why the check of edges that nearly line up still compares the pair.** A word a component says silences only what its words name. That an overlap is meant says where two parts share room, not where their edges lie. A near miss between two parts that overlap is no more likely to be chosen than one between two parts that stand apart (point 3). Leaving the pair out of both checks would let a meant overlap hide a part set a little off the edge it was meant to lie on. The cost of keeping the check, which point 3 names, is small.

### Alternatives considered

- **The check infers what is meant,** such as a small part on a corner. Rejected: whether an overlap is a fault needs a judgement, and only what needs none is a check's (DEC-028 point 1).
- **The frames tell the reviewer what a component means,** beside each part's box. Rejected: the review judges what is drawn. A component's word explains why the check is silent, and says nothing of whether the drawing reads well. The reviewer judges the pair on the image, as at every place a check's reach leaves out.
- **Two items of one list may be named.** A pattern lays out its items with an operator, and no component asks for two of its items to overlap. An overlap of two items stays reported. A later record may decide otherwise, once a component needs it.
- **A word for a near miss that is meant,** beside `over`. Not this record's: point 3 leaves it open.

## Implications

- **This change adds a record.** Its work adds a key to the format of a component. That is an addition, which leaves the format number as it is (DEC-003 point 1). The work declares a change of the capability that moves its version, as every change that adds a field does (DEC-014 point 2): a `minor`, since a project's components may use the key. It owes no migration: no file a project holds changes meaning.
- **Edits to accepted records,** made in this change once this record is accepted, each citing it (COR-066 point 5). Accepting this record accepts them.
  - **DEC-046 point 3,** the bullet "An overlap that is meant". Its two sentences come to read: "A part of a component may name the parts it is drawn over on purpose, such as a badge over a card's box, and the check of overlaps leaves out each pair named so. The check of edges that nearly line up compares those pairs as before (refinement per [visual-communication:DEC-066-meant-overlaps] points 1 to 3)."
  - **DEC-005 point 5,** the bullet "A tree of groups". After "A group may say which component drew it, with its library's version and options.", it comes to add: "An element may name, by their trace ids, the siblings drawn before it that its part says it lies over on purpose (refinement per [visual-communication:DEC-066-meant-overlaps] point 2)."
- **Read against this record, and left as they stand:**
  - DEC-046 point 3's "Boxes that overlap" and "Both ask for attention and never fail". Each pair the check still compares asks for attention as before, and the point's bullet on an overlap that is meant says which pairs it leaves out;
  - DEC-063 point 1: a clause of a reach that leaves a kind of place out cites the record that decides it, and the new clause cites this one;
  - DEC-037 point 1 and DEC-004 point 8, whose readings of a covered text and of contrast read the pair as before (point 2);
  - DEC-013 points 3 and 4, which point 4 follows for a library the capability ships;
  - DEC-030 point 7, since the check still measures and the reviewer still judges.
- **The work that builds it,** under #3327, in this change once this record is accepted:
  - the component's schema and the engine take `over` on every part, and refuse what point 1 refuses, with a finding that names the part and the name refused;
  - the scene's element holds `over`, as point 2 says, and the list of what a scene holds says so;
  - the check of boxes that overlap leaves out each pair named so. Its reach gains the clause, in its entry and in its code, held equal by the test that joins the two. A test plants a pair named so that overlaps, which gives no finding; the same pair not named, which gives one; and a near miss in a pair named so, which the check of edges that nearly line up still reports;
  - the capability's page on components says how a part says an overlap is meant, under its parts. The capability's list of checks drops, from the entry of the check of overlaps, the sentence that such an overlap is reported until a component can say it is meant, and names the pairs that check leaves out;
  - the page on what a release compares says that a part's `over` is neither a break nor an addition;
  - the reference pieces of the libraries the capability ships are read for an overlap of a component's parts. Each component whose parts overlap on purpose says so in its library's version being built, as point 4 says. Where none does, no shipped library changes.
