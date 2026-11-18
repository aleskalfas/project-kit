---
id: DEC-069
title: A leader ends at what it explains, by a course the eye can follow, and a page's layers read apart
status: proposed
date: 2026-11-18
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** many pages are drawn in layers. A *base*, such as a process, a schema, a map or a chart, lies under *layers* that add to it, such as notes, labels or a route. A *leader* is the line that ties a note or a label to what it explains or names. No rule of `GRAPHIC` judges where a leader ends or how it runs, and the reviewer's fault of a join that misses moves no grade where the line is a leader. This record decides three things:
- **A new rule, `RS-GRAPHIC-009`.** Each leader ends at one thing its note or label explains or names, or forks to each thing its note explains alike, and a reader tells at once what it joins. It crosses another leader only where no arrangement of the notes and labels avoids it, and then at a clear angle. It crosses any other line only at a clear angle, and runs along no other line. A join that misses between a leader and its thing comes to cite it.
- **Two readings** for a page drawn in layers, which the reviewer's body holds. By `RS-GRAPHIC-002`, layers that share a place read apart. A note or a label with no leader lies on what it explains or names, or nearer to it than to anything else it could be read as naming, and one with a leader stands as near to it as the page's arrangement of notes allows. By `RS-GRAPHIC-007`, a leader takes no look by which the page draws its base's relations, so no note reads as a step or a link. An arrowhead that points at what a leader ends at is no such look.
- **The set's next major.** A new rule gives the set its next major, the next after the one the default branch holds when the rule lands.

The rule, the readings, a topic of the design knowledge and the designer's method land in this record's change, once it is accepted.

## Context

The `GRAPHIC` rule set judges how a piece looks, each rule taken from the canon with its source named in a record ([visual-communication:DEC-028-principles-of-visual-communication]). The review of a piece grades each rule, and a fault whose rule's words name it holds that rule's grade below professional ([visual-communication:DEC-046-faults-lower-grades] point 2). [project-kit#3342](https://github.com/aleskalfas/project-kit/issues/3342), under [project-kit#3148](https://github.com/aleskalfas/project-kit/issues/3148), has the review, the design knowledge and the designer work with a page drawn in layers. Its rule and its readings are choices later work builds on, so this record decides their words first ([COR-065](../../../decisions/core/COR-065-records-and-projection.md) point 3).

What judges a page drawn in layers today:
- **`RS-GRAPHIC-002`** asks that what belongs together is placed together, that what is separate is set apart, and that steps are joined in the order they are read.
- **The reviewer's fault of overlaps** covers a line through a text or a card that is not its end. It covers too a *join that misses*: a line that stops short of the part the content joins it to, or runs past it. That one cites `RS-GRAPHIC-002` between steps, and no rule between parts that are not steps (DEC-046 points 2 and 3). So a leader that misses its thing moves no grade.
- **`RS-GRAPHIC-006` and `RS-GRAPHIC-007`** judge colour as a signal, and a difference a page adds or drops. The reviewer counts a page's hues against the kinds its content names (DEC-046 point 6).
- **The design knowledge** teaches that crossings and broken paths cost a reader most in a diagram, that a line joining two parts groups them, and that words belong near what they describe. No topic speaks of leaders. Of layers, `diagrams.md` speaks of Tufte's layering: a page layered so that the content lies in front and its frame behind lets the content come forward.

So no rule, fault or check judges which thing a leader ends at, or the course it takes. DEC-046 point 1 places such a gap: in the reading where a rule names it, in a check for each part that needs no judgement, in a brand's values where it is the look, and in a rule of the canon only for what is left.

What the engine draws. A *tie* is an item its pattern draws between two other items, its ends ([visual-communication:DEC-011-tie-ends] point 1). The connector tool draws a tie straight or with two turns, square to each end's side and halfway between them. It never routes around anything ([visual-communication:DEC-005-engine-and-plugins] point 2). A tie leaves each end's frame by the side that faces its other end: its left or right side where the two frames lie further apart across than down, else its top or bottom. Several ties on one side of an item spread along it, ordered by where their other ends lie. A tie that names a point an item exposes ends at that point (the capability's components page, "Ties and connectors"). Of the starter library's patterns:
- **`layers`** places notes to the right of its stack of levels, in one column, sharing the stack's height in equal parts. Its ties join a note or a level to another, each drawn by the starter's `connector`, and end at a level's drawn edge. The `connector` draws every tie in one look, its family's text at one width. It draws a tie straight unless the content asks for corners, an arrowhead at the tie's end unless the content asks otherwise, and the colour and the sign of a concept its tie names. So a note's tie and a tie between levels look alike unless the content gives them another arrowhead, route or concept.
- **`network`** draws ties between its items. A tie between two of its items is the base's own link. An item may be drawn by a component that exposes a picture's points, and a column may hold labels tied to those points. Each such tie is then a label's line, a leader, by its job and not by its component.
- **The test library's `callout`** places a label at a point a picture exposes, with no line (the capability's outputs page, "A label at an exposed point").

Each word below was judged by the test that whoever maintains the capability sets for a rule's words: no bad design passes, and no good design fails. It was traced on six cases: a process with notes, a schema with labels, a map with routes, a chart with callouts, a figure whose labels sit on what they name with no line, and the shipped components that draw ties. The traces confirm the words, and are no source of them (DEC-028 point 1).

The words this record uses are DEC-046's (its Context), and these:
- **The base** of a page is what it shows, such as a process, a schema, a map or a chart.
- **A layer** is a set of marks of one kind laid over the base, such as the page's notes, its labels or a route. *The layers of a page* are its base and every layer over it. The word is the field's, as in Edward Tufte's layering. It is not the starter's pattern `layers`, whose levels are parts of a base.
- **A note** is a text that explains a thing the page shows, and **a label** a text that names one. Each is a mark of a layer over the base. A text of the base itself, such as a step's head, is neither.
- **A leader** is a line drawn from a note or a label to what it explains or names, as the rule's words define it (point 1).
- **Pinned.** A note or a label is pinned to what it explains or names, by a leader or by its place alone.
- **A leader's course** is the path its line takes from its note or label to its end.

## Decision

**`GRAPHIC` gains `RS-GRAPHIC-009`: each leader ends at one thing its note or label explains or names, or forks to each thing its note explains alike, and a reader tells at once what it joins. Its course crosses another leader only where no arrangement of the notes and labels avoids it, crosses any line only at a clear angle, and runs along none. `RS-GRAPHIC-002` and `RS-GRAPHIC-007` gain readings for a page drawn in layers, in the reviewer's body. A join that misses between a leader and its thing cites the new rule. The rule gives the set its next major.**

### 1. `RS-GRAPHIC-009`, a leader ends at what it explains

The words the rule lands with:

> ## RS-GRAPHIC-009 — A leader ends at what it explains, by a course the eye can follow
>
> A leader is a line drawn from a note or a label to what it explains or names. Each leader ends at one thing its note or label explains or names, and a reader tells at once what it joins. A leader may fork to each thing its note explains alike. It crosses another leader only where no arrangement of the notes and labels avoids it, and then at a clear angle. It crosses any other line only at a clear angle, and runs along no other line.
>
> - **Over a picture made elsewhere.** The clauses on a leader's course judge a leader the piece draws against the lines a reader sees in a picture under it, such as a map's roads or a drawing's outlines, on the image.
> - **What it does not judge.** A line that is no leader, such as an arrow from one step to the next, a link between two items or a route on a map: how such lines cross or run along each other. A mark that spans the parts a note explains, such as a bracket or a band. Whether a note or a label takes a leader at all, which is `RS-GRAPHIC-003`'s where the leader is extra, and where one with none stands, which is `RS-GRAPHIC-002`'s. A leader over a part that is not its end, such as through a card or a text, which `RS-GRAPHIC-002` sets apart. Whether a leader can be seen where the piece is shown, which is `RS-GRAPHIC-005`'s. Whether the leaders keep one look, which is `RS-GRAPHIC-004`'s, and what their look says, which is `RS-GRAPHIC-007`'s. What lies inside a picture made elsewhere.
> - **From the text:** whether the content ties each note or label it gives a leader to an item its words explain or name.
> - **On the drawn page:** whether a reader tells which note or label and which things each leader joins, and whether its course crosses or runs along another line as the rule allows.

Accepting this record decides that the rule lands in these words. From the change that adds the rule, the `GRAPHIC` set holds its statement, as a set holds each of its rules' (COR-051 point 2). A rewording after that is made in the set, by the set's own path.

### 2. The sources of its clauses

Each clause rests on a work of the canon, and claims no more than the work teaches:
- **What a leader is for.** Richard Mayer's spatial contiguity principle: people learn better when words lie near the pictures they describe (*Multimedia Learning*). A note or a label that cannot stand by what it explains is tied to it by a line. That step, from words that lie near a picture to a line that joins them, is this record's own reading, not Mayer's. Stephen Palmer and Irvin Rock's uniform connectedness: a line that joins two parts groups them, where distance alone would keep them apart ("Rethinking Perceptual Organization: The Role of Uniform Connectedness"). So a leader groups its note with what it touches.
- **One thing, told at once.** The same connectedness groups a note with each thing its leader touches. A leader that ends where two things meet, or between them, groups it with both or with neither.
- **No leader crosses another that an arrangement avoids.** Helen Purchase: of the ways a graph is drawn, fewer crossings of its edges helped people understand it most ("Which Aesthetic Has the Greatest Effect on Human Understanding?"). Colin Ware, Helen Purchase, Linda Colpoys and Matthew McGill: after a path's length, its continuity and the crossings on it cost a reader most in finding a path ("Cognitive Measurements of Graph Aesthetics", *Information Visualization* 1 (2), 2002). Both measured the edges of graphs. The rule takes their finding for the line a reader follows from a note to its thing. Drafting asks the same of leaders themselves: a drawing avoids crossing them (ANSI Y14.2M-1979, *Line Conventions and Lettering*, 3.6.3.7). That an arrangement of the notes can avoid such crossings, and when, is this record's own reasoning, no source's ("Why leaders alone").
- **Any other line at a clear angle.** Weidong Huang, Seok-Hee Hong and Peter Eades: in tracing paths, the time a reader took fell as the angle of a crossing grew, and the fall levelled off near a right angle. So the crossings that remain should take angles as large as can be ("Effects of Crossing Angles", IEEE Pacific Visualization Symposium, 2008). They measured crossings of a graph's edges. The rule takes their finding for a leader that crosses a base's lines.
- **Along no other line.** Max Wertheimer's laws of grouping: what lies close is seen as one, and so is what continues along one line ("Untersuchungen zur Lehre von der Gestalt II"). Ware: the eye traces a path most easily along a smooth, continuous line (*Information Visualization: Perception for Design*). A leader that lies on another line, or close beside it, joins it as one line, so the eye follows the two as one. Drafting avoids leaders that are parallel to adjacent dimension, extension or section lines (ANSI Y14.2M-1979, 3.6.3.7).
- **How each was read.** The works the design knowledge already cites are taken as its topics read them: Mayer, Palmer and Rock, Purchase, Wertheimer and Ware's book. The papers of Imhof, of Ware and his colleagues, and of Huang and his colleagues were read in their published abstracts alone, and each is cited for no more than its abstract says. Imhof is cited for placing names alone (point 5). Of drafting's conventions, the American standard's 1979 edition, ANSI Y14.2M-1979, published by the American Society of Mechanical Engineers and continued as ASME Y14.2, was read in its section on leaders, 3.6.3, in the text of a scan the Internet Archive keeps. No current edition of ASME Y14.2 was read, nor ISO 128-22, and nothing rests on either.

### 3. What its words mean, and where they stop

- **A leader is told by its job,** never by its look. It is a line the content draws from a note or a label to what that text explains or names, such as a tie from a note of `layers` to a level, or a line a component draws for its label. A line that joins the base's own parts is no leader, however it is drawn.
- **Several leaders may leave one note,** one to each thing it explains, or one leader may fork to each thing its note explains alike. They leave it together, and cross nothing there.
- **Ends at.** On the thing's edge, inside it, or so near it that it points at that thing alone. Whether a gap is small enough to point at its thing alone is this reading's, on the drawn page. The reviewer's join that misses is a leader that ends at another thing, or at none near enough to point at any, or runs on past its thing, and leaves the gap to this reading (point 4).
- **One thing.** A part, a group drawn as one, a point or a line, such as a step, a region, a dot on a chart or a route. A group the content gives as one, or a mark that spans it, such as a bracket, counts as one thing.
- **Tells at once.** Without following the line back and forth. A leader whose start lies between two notes, or whose course winds so that a reader must trace it to tell where it goes, fails, whatever it crosses.
- **No arrangement avoids it.** No order or place the page could give its notes and labels, each beside what it explains, ends the crossing, as where leaders fork to things that interleave so that every arrangement crosses. A crossing that only a library's layout forces, where another layout of the notes would avoid it, is no such case: the rule fails it, and the fix is the library's ("Who mends it", below).
- **Crosses.** One line passes over another. A leader that ends on a line, such as a route it names, ends there, and does not cross it. The outline of the thing a leader ends at is no line it crosses.
- **A clear angle** is one at which the eye sees a crossing, and does not go on along the other line. Only a glancing crossing fails.
- **Runs along.** Lies on another line, or close beside it, for a stretch, so that the two read as one line or as a pair. Two lines that keep one direction far apart do not run along each other.
- **Any other line** is a line the base draws, such as an arrow, a link, a road, a gridline, an axis or an outline, or a line of another layer, such as a route. Over a picture made elsewhere, it is a line a reader sees in the picture, on the image (point 1).
- **No figure.** The rule names no angle, no distance and no length. Its sources give none as a limit. A project that wants one adds it in a set of its own, and a threshold a check measures is the check's (DEC-028 point 1).
- **From the text.** The content names each tie's two ends and gives each note's words. So whether a note is tied to what its words explain is judged from the text: a note on what is cached, tied to a level that caches nothing, fails there. How a leader runs, and whether a reader tells what it joins, only the drawn page shows.
- **A grade on each page** that holds a leader. A page with none takes no grade on the rule, and the review says so ([visual-communication:DEC-042-grades-bar-and-loop] point 1).
- **Who mends it.** The designer, in the piece, a component or a library. It may move or reorder the notes and the labels, split a note, place a note or a label by what it explains with no line, give a tie a straight or a cornered route, move the base's parts, or make a local component. It may reword or cut any word that is not the asker's (DEC-042 point 7). A local component that breaks `RS-GRAPHIC-004`, by drawing its own where a library has a component for the job, is no remedy. A crossing forced by a library is that library's to mend, and the finding names the library as where its fix belongs (DEC-030 point 7).
- **Rarely a need.** A *need* marks a grade only where no fix the designer may make would raise it, and only a tool the engine lacks would (DEC-042 point 4). The connector tool routes around nothing, and turns only halfway between its ends. So a course that bends round a part, or turns where the designer chooses, is such a tool. The review marks a need only where it says why no fix of the bullet above gives a course the rule allows.
- **With a check of leaders and without.** No check measures a leader's course. Where two lines cross, at what angle, and where one runs along another is arithmetic over a scene's lines, which a check could do (DEC-028 point 1). The engine's ties to a note tell a leader by its key path, which names the note, as a tie of `layers` names an item of its `notes`. Whether another line is a leader, whether an angle reads as clear, and whether a reader tells what a leader joins are judgements. So the reviewer's body reads the rule both ways. With no such check, the reviewer judges each leader on the image. A later check of leaders states each crossing it measured, with its angle, as a fact, and the reviewer judges whether the angle is clear. Its reach leaves out the lines of a picture made elsewhere, which the reviewer judges on the image. Where one lands, what it measures stays the check's, and the reviewer judges each place it names and reads its silence by its reach ([visual-communication:DEC-063-where-a-check-measures] point 3), as for the checks of boxes (DEC-046 point 3). Whether to build one is a later record's.

### 4. Its place among the set's rules and the faults

- **A rule of its own.** In DEC-046 point 1's order, the gap goes first to a reading where a rule's words name it. None names a leader's end or course: `RS-GRAPHIC-002` names grouping, lining up, setting apart and joining steps, and `RS-GRAPHIC-007` a difference added or dropped. A check can do the arithmetic, and tell the engine's ties to a note by their key paths, but cannot tell every leader from another line or say whether a crossing reads. No brand's value draws a course. So what is left is a rule of the canon.
- **Beside `RS-GRAPHIC-002`.** A leader joins what belongs together, which that rule asks. That rule judges whether a note and its thing are placed together, and where a note or a label stands, one with no leader among them (point 5). Whether a note takes a leader at all is `RS-GRAPHIC-003`'s, where the leader is extra. This rule judges where a leader ends and how it runs. A leader over a part that is not its end is the fault of overlaps, which cites `RS-GRAPHIC-002` (DEC-046 point 3). A bracket or a band over the parts a note explains is a grouping, which that rule judges too.
- **Beside `RS-GRAPHIC-007`.** What a leader's look says, its arrowhead and its hue included, is that rule's (point 6).
- **Beside the other rules.** That every leader keeps one look across the piece is `RS-GRAPHIC-004`'s. That a reader can see a leader and read its note, where the piece is shown, is `RS-GRAPHIC-005`'s. A leader or a layer told from the base by its hue alone is `RS-GRAPHIC-006`'s. A layer seen before what the page's point is about is `RS-GRAPHIC-001`'s.
- **The fault it names.** A join that misses between a leader and its thing: a leader that ends at another thing than the one the content ties it to, or at none near enough to point at any, or runs on past its thing. The rule's words "ends at one thing" name that defect. Whether a gap is small enough to point at its thing alone is the rule's reading (point 3), not the fault's, since a fault never judges design (DEC-030 point 6). So the fault cites `RS-GRAPHIC-009` and holds its grade below professional on the page that shows it (DEC-046 point 2). A join that misses between other parts that are not steps cites no rule.
- **Every piece.** The rule judges every piece, whatever its purpose, as `GRAPHIC` does (DEC-028 point 3).

### 5. `RS-GRAPHIC-002` reads a page drawn in layers

The reading the reviewer's body holds, in these words:

> **`RS-GRAPHIC-002`, on a page drawn in layers.**
>
> - **Layers read apart where they share a place.** A note, a label or a route laid over the base, or over another layer, shares its place, so no space sets the two apart. There the rule's clause on setting apart what is separate judges whether a reader can tell which layer each mark belongs to, and follow each one, the base among them. Whether a layer outranks another is `RS-GRAPHIC-001`'s. Whether a hue alone tells a layer apart is `RS-GRAPHIC-006`'s. Whether a text or a line stands out from what lies under it is the checks' of contrast, and the fault of a text that does not read over a picture. A part of one layer over a part it should stand clear of is the fault of overlaps.
> - **A note or a label with no leader** lies on what it explains or names, or nearer to it than to anything else it could be read as explaining or naming, so that a reader tells at once which thing that is. One that stands as near to another such thing, or nearer, is not placed with what it belongs with.
> - **A note about a whole** stands beside the whole or the group it explains, nearer to it than to anything outside it. A note beside the levels it holds across passes, though it stands beside each of them.
> - **A note or a label with a leader** is pinned by its leader, which `RS-GRAPHIC-009` judges. It stands as near to what it explains as the page's arrangement of notes allows. A column of notes kept in the order of their ends, as an atlas's margin is, passes.

The reading rests on the rule's words, "placed together" and "set apart", and on the practice that teaches them for layers: Tufte, as the design knowledge's topics read him (*Envisioning Information*). Wertheimer's proximity and Palmer's common region: a label grouped by what lies nearest, or by the region it lies inside ("Common Region: A New Principle of Perceptual Grouping"). Mayer's spatial contiguity (point 2). For a name placed with no line, Eduard Imhof, on the lettering of maps: a name is positioned in relation to the feature it names, and the map's legibility and clarity depend on that position ("Positioning Names on Maps", *The American Cartographer* 2 (2), 1975).

### 6. `RS-GRAPHIC-007` reads a leader

The reading the reviewer's body holds, in these words:

> **`RS-GRAPHIC-007`, on a leader.**
>
> - **A leader shows that it pins, and no relation of the base.** The content gives a leader and a relation of its base as two kinds of line: one pins a note or a label to what it explains or names, the other joins the base's parts, such as a step to the next. So a leader takes no look by which the page draws its base's relations, such as the line and the arrowhead of its flow, and a reader takes no note or label for a step, a part or a link. A leader drawn so shows a relation the content lacks, and drops a difference it has.
> - **An arrowhead** at a leader's end, pointing at what the leader ends at, shows that the leader points there, which the content gives. On a page that draws none of its relations with that arrowhead, it shows no order.
> - **Its hue,** as any hue: a difference the content lacks only where it tells apart leaders the content gives as alike, such as two ties of one list, neither of which names a concept ("Count the hues against what the content names"). A leader in the hue of the series it ends on shows a difference the content has, the series, and breaks nothing.

The reading rests on the rule's words, "every difference a reader takes for meaning is one the content has", and on the practice that teaches what a line says. Ware: in a diagram, a line that joins two things reads as a relation between them, and its weight or style tells the relation's kind (*Information Visualization: Perception for Design*). Yuri Engelhardt: linking by a connector is one of the structures of a graphic's space that carry meaning (*The Language of Graphics*). Julie Heiser and Barbara Tversky: an arrow may mean pointing, a sequence, a change over time, a path, a motion or a force, and in many diagrams the context leaves unclear which ("Arrows in Comprehending and Producing Mechanical Diagrams"). So an arrowhead on a leader reads as pointing where nothing else on the page gives it another sense. Drafting ends a leader that ends on an object's outline with an arrowhead, and one that ends within it with a dot (ANSI Y14.2M-1979, 3.6.3).

**One drawing may break both readings,** as where leaders are drawn as the flow's arrows: a reader can neither follow the notes apart from the flow, nor take them for anything but steps. The finding then cites each rule, as one observation cites each of its grounds ([visual-communication:DEC-030-design-agents] point 6).

### 7. The rule gives the set its next major

A new accepted rule needs a new major of its set (COR-051 point 7). So the change that adds `RS-GRAPHIC-009` gives the set its next major: the next after the one the default branch holds when the rule lands. Where [project-kit#3396](https://github.com/aleskalfas/project-kit/issues/3396) lands first, in the same release, with a new major of its own, both join that one major. The readings of points 5 and 6 change no rule's text, so they need no major.

### 8. Its shape, its origin and its anchors

- **The shape DEC-028 gives.** The rule judges every piece (DEC-028 point 3), says apart what the text and the drawing show (DEC-028 point 4), and binds on nothing until a piece's content is an artefact (DEC-028 point 5).
- **Its sources are the canon's.** No outside judge's measure is a source of the rule, of a reading or of a word this record places (DEC-042 point 2).
- **It names no grade.** A rule's text names a grade only where a break of it blocks a bar (DEC-042 points 1 and 2). No source calls a break of this rule unworkable, so which lower grade a break takes is a reading.
- **Its origin is this record,** as [visual-communication:DEC-046-faults-lower-grades] is the origin of `RS-GRAPHIC-008`. This record gives the rule's id, title, words, sources and reasons.
- **Its anchors.** The rule names DEC-028 points 3 and 4 among the points it rests on, as every rule of `GRAPHIC` does, DEC-046 points 2 and 3, since a fault cites it, and this record's points 1 to 4 and 8. `RS-GRAPHIC-002` comes to name point 5 too, and `RS-GRAPHIC-007` point 6. So a later change to any of them flags the rule to be read again.

## Rationale

**Why a rule, and not a reading of `RS-GRAPHIC-002`.** Reading "set apart" to forbid two leaders crossing would make that rule judge a path, which its sources do not state: proximity and connection say what groups, not how a line runs. A rule of its own gives the test the sources that state it, and lets a change to its reasons flag this rule alone (DEC-028, "Why the reasons live in a record").

**Why leaders alone, and not every line.** A base's own lines cross where its content does. A network that cannot be drawn without a crossing crosses somewhere, so "crosses no other line" would fail it, and Purchase and Ware ask fewer crossings, never none. A route runs along roads by what it is. A leader's course is the designer's alone. This record's own reasoning, which no source states, says when an arrangement avoids a crossing. Where each note takes one straight leader and two notes can trade places, trading the places of two notes whose leaders cross makes the two leaders shorter in sum, since a straight line is the shortest path between its ends. So of the arrangements, the one whose leaders are shortest in sum crosses nowhere. A note with several leaders or a forked one, or notes that cannot trade places, may cross in every arrangement, and there the rule asks a clear angle.

**Why "ends at", not "ends on".** A chart may stop a callout's leader a little short of the dot it explains, so that the dot stays clear, and the reader still tells at once which dot it means. "Ends on" would fail it. "Ends at" takes in such a gap, and still fails a leader that stops where it could point at another thing too. The join that misses takes only a leader that ends at another thing, or at none near enough to point at any, or runs on past its thing, and leaves the gap to the rule's reading.

**Why a reader's test beside the course's.** The three clauses on the course miss a leader whose start lies between two notes, and one that winds through a crowd of lines without crossing any at a glancing angle. "Tells at once" fails both.

**Why "any other line", and why "along no other line".** A leader meets the base's lines as well as those of the layers over it, so the rule names any line. Two leaders that run along each other merge as surely as a leader and a road do, so the clause on running along takes in other leaders too. The starter's `layers` draws exactly that where two cornered ties turn in one gap.

**Why no figure.** Huang and his colleagues found the cost fall as the angle grows, and gave no angle below which a crossing fails. The rule asks the angle the eye reads as a crossing, as `RS-GRAPHIC-008` asks a comfortable measure and names no number of characters (DEC-046 point 4).

**Why the readings, and not more rules.** `RS-GRAPHIC-002`'s words, "placed together" and "set apart", already name a label's place and layers that read apart, and `RS-GRAPHIC-007`'s words name a leader whose look shows a relation the content lacks. A rule on either would judge one test twice (DEC-046 point 1).

**Why the layers' reading leaves hue to `RS-GRAPHIC-006`.** That rule already fails layers told apart by a hue alone: whatever a colour tells apart is told another way too. A reading that asked more than a hue would fail the same page on a second rule, by the same test.

**Why the no-line reading speaks of what a label could be read as naming.** A label always stands nearer to something than to what it names: a town's name beside its dot may lie nearer a road than the dot. A reader does not take it for the road's name, so it is placed with its town. The test is the reader's: of the things it could name, it stands nearest to its own.

**Why an arrowhead may end a leader.** An arrow has many senses, pointing among them (Heiser and Tversky). An arrowhead that points at what a leader ends at says what the content says, that the note points there. It shows an order only where the page draws its relations with it too, and there the reading fails the leader by its look.

**Why the next major, in the change that lands the rule.** A new major makes every project that pins the set's major before it read the rule and move its pin (COR-051 point 7). That belongs with the reviewer's body and the design knowledge that read the rule, in a change that declares it, as DEC-046 has it for `RS-GRAPHIC-008` ("Why no rule lands in this change"). Two changes that land in one release give a project one new major to read, not two.

**Why DEC-028 is refined as the record that says where each rule's source is named.** DEC-028 names the source of each rule of the set, and says that DEC-046 names it for `RS-GRAPHIC-008` and is that rule's origin. This record names the sources of `RS-GRAPHIC-009` and gives its words, so it is that rule's origin in the same way, and DEC-028 comes to say so wherever it says it for `RS-GRAPHIC-008`.

### How each word was traced

The six cases are a process whose notes stand beside its steps (P), a schema whose labels name its parts and links (S), a map with routes and names (M), a chart with callouts (C), a figure whose labels sit on what they name with no line (F), and the shipped components that draw ties (K). Each bullet says where a word passes good design and fails bad, and why.

- **What a leader is** (point 1).
  - P, S, M and C: a note's line to a step, a label's to a part, a name's to its town and a callout's to its point are leaders. The flow's arrows, the schema's links, a route, a series' line, a gridline and an axis are not, so their own crossings and runs are not judged. That passes a metro map whose routes run side by side on one track, as good maps draw them.
  - F: no leader, so the rule takes no grade, and the labels' places are the no-line reading's.
  - K: in `layers`, a tie from a note to a level is a leader, and a tie between two levels is not. A tie of `network` between two of its items is not. Where an item of `network` exposes a picture's points and a column of labels is tied to those points, each such tie is a leader, by its job. The test library's `callout` draws no line.
- **"Ends at one thing its note or label explains or names."**
  - P: passes a leader that ends on the step its note explains, a note with one leader to each of two steps, and a leader that forks to both. It fails one that ends on the arrow between two steps, where a reader cannot tell which step is meant. A brace over three steps is no leader, so it is not failed for spanning them, and a leader that ends at the brace ends at one thing.
  - S: fails a leader that ends at the corner where two boxes meet. Passes one that ends inside its part.
  - M: passes a leader that ends on its town's dot. Fails one that stops in an empty field between two dots.
  - C: passes a callout's leader that stops a small gap before the dot it plainly reaches. Fails one that ends between two close dots.
  - K: `layers` ends each tie at a level's drawn edge, so its leaders pass, save where the content ties a note to a level it does not explain, which the text shows. A tie of `network` that names a picture's point ends at that point.
- **"A reader tells at once what it joins."**
  - P and S: fails a leader that starts between two notes set close, and one that winds through others until a reader traces it twice. Passes a short leader in one stroke.
  - M: fails a long leader through a crowded quarter, where the eye loses it among the streets.
  - K: `layers` leaves a note's tie by the side of the note that faces the level, its left side where the two lie further apart across than down. Where the note lies further above or below the level than beside it, the tie leaves by the note's top or bottom, between two notes, and fails. Straight or with corners, it then runs over the note beside it and over the levels between, which is the fault of overlaps. `network` leaves a label's tie to a point the same way.
- **"It crosses another leader only where no arrangement of the notes and labels avoids it, and then at a clear angle."**
  - P: fails notes above a flow whose leaders cross because the notes stand in another order than their steps. Reordering them mends it.
  - S and C: fails two labels' or two callouts' leaders that cross in a crowd. Placing them on both sides, or reordering them, mends it.
  - S: passes leaders that fork to parts that interleave, where every arrangement crosses, and they cross at a clear angle.
  - K: `layers` with straight ties fails where its notes stand in another order than their levels, and reordering the notes mends it. A note tied to the first and third levels, with another note tied to the second, crosses in every order of one column of notes, and a note on the left would avoid it. The rule fails that page, as a designer would not hand it over. The designer may split the note where its words allow. Otherwise the crossing is forced by the library, which places notes to the right of the stack alone, and the finding names the library as where the fix belongs (DEC-030 point 7). A local component that sets the other note on the left draws its own where the library has a component for the job, which breaks `RS-GRAPHIC-004`, so it is no remedy.
  - K: labels of `network` in one column, each tied straight to a picture's point, cross unless the content orders them so that they do not. Where the labels are alike in height, and each tie leaves its label by the side that faces the picture, some order avoids it ("Why leaders alone").
- **"Crosses any other line only at a clear angle."**
  - P: passes a leader that crosses a flow's arrow at a slant the eye still reads as a crossing. Fails one that crosses it at a glancing angle, where the eye goes on along the arrow.
  - M: passes a leader across a road at a right angle. Fails one that meets a route at a shallow angle. On a map made elsewhere, a name's leader the piece draws is judged against the roads a reader sees in it, on the image, and the map itself is not judged.
  - C: passes a leader across gridlines at a right angle. Fails one that crosses a series' line at a glancing angle, where it reads as part of the series.
  - S: a leader that ends inside its part meets that part's outline, which is no line it crosses, so the rule does not judge that angle.
  - K: the `connector` with corners runs in legs across and down, so it crosses a line that runs across or down square. A straight tie may cross at any angle, and the drawn page shows which.
- **"It runs along no other line."**
  - P: fails a leader that runs along a flow's arrow to reach a far step, where it reads as the arrow.
  - M: fails a name's leader that runs along a road.
  - C: fails a leader that lies on a gridline. Passes one between gridlines.
  - K: `layers` with `route: corners` turns every note's tie halfway across the one gap between the notes and the stack. Two ties whose turns overlap down that gap run along each other, and fail. `route: straight` mends it.
- **"What it does not judge."**
  - P and K: a brace or a band over the parts a note explains, and a tie between levels, are not judged here, so the rule fails no grouping and no relation of the base.
  - S: a label's line through another part is the fault of overlaps, and is not judged here a second time.
  - F: a leader drawn to a label that already sits on what it names is extra, which `RS-GRAPHIC-003` judges, not this rule.
- **"From the text."**
  - K: content of `layers` that ties a note to a level its words do not explain fails from the text.
  - C: a callout tied to another point than the one its words explain fails the same way.
- **The layers read apart** (point 5).
  - F: passes labels on a drawing, which read apart by being text.
- **A note or a label with no leader** (point 5).
  - F: passes labels inside the parts they name, which their region groups them with. Fails a label on a small part that spills onto its neighbour.
  - S: passes a label on its link. Fails one midway between two links that run side by side.
  - M: passes a town's name beside its dot near a road, which "nearer to it than to anything else" would fail, since the road lies nearer. Fails a name that stands as near to two towns.
  - C: passes a label at the end of its series. Fails one as near the end of another.
  - K: the test library's `callout` sets its label beside a picture's point, judged so.
- **A note about a whole** (point 5).
  - K: a note of `layers` with no tie, beside the levels it holds across, passes, though it stands as near to each of them.
  - P: fails a note on the whole flow set beside its last step alone, nearer to that step than to the rest.
- **A note or a label with a leader** (point 5).
  - M: passes names in an atlas's margin, kept in the order of the places their leaders end at. Fails a name set far down the margin, its leader across the map, where a place beside what it names is free.
  - K: `layers` sets its notes in one column beside the stack, in the content's order. A column kept in the order of the levels its notes tie to passes.
- **A leader shows no relation of the base** (point 6).
  - P: fails leaders drawn with the flow's line and arrowhead, which read as steps. Passes thin leaders with no arrowhead, or with a dot at the end.
  - S: fails leaders drawn as the schema's links, which read as links.
  - K: the `connector` draws a note's tie and a tie between levels in one look, each with an arrowhead at its end unless the content asks otherwise. A page that ties levels too and leaves a note's tie at that default fails. A note's tie given no arrowhead, where the level ties keep theirs, passes. Where the level ties draw no arrowhead, the starter gives a note's tie no look of its own beyond a route, or a concept's colour and sign. Whether those tell it apart is judged on the drawn page, and a look the `connector` lacks is the library's to mend (DEC-030 point 7).
- **An arrowhead that points** (point 6).
  - S: passes a leader that ends in an arrowhead on a schema that draws no arrow, where the arrowhead only points. Without this bullet, a leader with any arrowhead would fail, even where it only points.
  - K: fails a tie of `layers` that runs from the level to its note, its arrowhead at the note, which says that the level points at the note. Passes one from the note to the level.
- **A leader's hue** (point 6).
  - C: passes callouts whose leaders each take the hue of the series they end on, which shows the series. Fails leaders in hues of their own that match no series, where the content gives the callouts as alike.
  - K: the `connector` takes the colour and the sign of a concept its tie names, which the content gives, so it passes.

### Alternatives considered

- **The rule's clauses as readings of `RS-GRAPHIC-002`.** Rejected: that rule's sources state no test of a line's course ("Why a rule").
- **"Ends on one thing", as project-kit#3342's body words it.** Rejected: it fails a callout that stops short of its dot to keep it clear ("Why 'ends at'").
- **"A line of another layer",** as that body words what a leader crosses only at a clear angle and never runs along. Rejected: the base's lines are no layer over it, and two leaders, of one layer, may run along each other, so it would pass both.
- **The course's clauses for every line of a page.** Rejected: a base's own lines cross where its content does ("Why leaders alone"). Its trigger to revisit: a calibration finds a base's lines crossing at glancing angles that no rule grades, and a source states a test for them.
- **A figure for the angle,** such as the least angle a crossing may take. Rejected: no source gives one as a limit, and a limit is a project's taste or a check's threshold (DEC-028 point 1).
- **"Set apart by more than a hue",** as that body words the layers' reading. Rejected: `RS-GRAPHIC-006` judges that test already ("Why the layers' reading leaves hue").
- **"Nearer to what it explains than to anything else",** as that body words the no-line reading. Rejected: it fails a town's name beside a road ("Why the no-line reading").
- **An arrowhead as an order the content lacks,** as that body gives it for an example. Rejected: an arrowhead that points says what the content says ("Why an arrowhead may end a leader").
- **The no-line reading as a clause of `RS-GRAPHIC-009`.** Rejected: a label with no line has no leader, and where it stands is a matter of what belongs together, `RS-GRAPHIC-002`'s.
- **A rule that each note or label takes a leader.** Rejected: a label on what it names is good design, and a leader there would be extra, which `RS-GRAPHIC-003` judges.
- **A rule naming *below competent* for a leader that ends at the wrong thing.** Not taken: no source calls a break unworkable, and the content shows a wrong end from the text, where the designer mends it ("It names no grade").
- **A check of leaders in this record.** Not taken: the reading holds with a check and without one (point 3), and the check is a choice of its own, with its reach and its findings, for a record of its own.
- **Technical drawing's convention for leader lines, ISO 128-22, as a source.** Not taken: this record could not read the standard, so it rests nothing on it. Of drafting's conventions it cites only what it read, the American standard's 1979 edition (point 2). The topic may cite ISO 128-22 once it is read.

## Implications

- **This change, first, adds this record alone,** proposed. Nothing rests on it until a person accepts it (COR-066 point 1). The work below follows, in this change.
- **Edits to [visual-communication:DEC-046-faults-lower-grades],** made in this change once this record is accepted (COR-066 point 5):
  - **Point 2,** its bullet "Among the faults, these are named by no rule of `GRAPHIC`". Its last item, "a join that misses between parts that are not steps", comes to add: save between a leader and its thing, which `RS-GRAPHIC-009` names (refinement per DEC-069, point 4).
  - **Point 3,** its bullet "A join that misses". "Between parts that are not steps it cites none" comes to read: between a leader and its thing, where the leader ends at another thing, or at none near enough to point at any, or runs on past its thing, it cites `RS-GRAPHIC-009`, whose words "ends at one thing" name it, and whether a gap is small enough to point at its thing alone is that rule's reading (refinement per DEC-069, point 4); between other parts that are not steps it cites none.
  - **Its Rationale,** "What this costs". Its last sentence, "For craft the cost is small, since only a join that misses between parts that are not steps cites no rule", comes to say that such a join cites no rule save between a leader and its thing (refinement per DEC-069, point 4).
- **Edits to [visual-communication:DEC-028-principles-of-visual-communication],** made the same way. Each adds `RS-GRAPHIC-009` where the record says it of `RS-GRAPHIC-008`:
  - **Its summary.** "This record names its source, or, for `RS-GRAPHIC-008`, on running text, DEC-046 does" comes to add: and, for `RS-GRAPHIC-009`, on leaders, DEC-069 does (refinement per that record, point 8).
  - **Its Decision line.** The same addition.
  - **Point 1.** "Each is taken from a source this record names, or, for `RS-GRAPHIC-008`, from one DEC-046 names" comes to add: or, for `RS-GRAPHIC-009`, from one DEC-069 names (refinement per that record, point 8).
  - **Its Rationale,** "Why the reasons live in a record". "The record gives each rule's id, title, sources and reason, or, for `RS-GRAPHIC-008`, DEC-046 does" comes to add that DEC-069 gives them for `RS-GRAPHIC-009`.
  - **Its Implications.** "Each rule cites this record as its origin, but `RS-GRAPHIC-008`, whose origin is DEC-046" comes to add: and `RS-GRAPHIC-009`, whose origin is DEC-069 (refinement per that record, point 8).
- **Read against this record, and left as they stand:**
  - DEC-028 points 3, 4 and 5, since the rule takes the shape they give, and points 8 and 11, since the readings of points 5 and 6 read their rules' words without changing them, and a reading is the reviewer's body's;
  - DEC-030 point 3, since the designer's steps are its body's, and point 8, since it asks at least six topics, and one more joins them;
  - DEC-030 point 6, since a finding that breaks both readings cites each ground, and a fault judges no design, as it says, and point 7, since a crossing a library forces names the library as where its fix belongs;
  - DEC-042 points 1 to 4, 9 and 10, since a page with no leader takes no grade, the rule names none, a bar pins the new major, and a new major lapses the hold;
  - DEC-005 point 2 and DEC-011, since this record asks nothing new of the engine or of a tie;
  - [visual-communication:DEC-007-starter-library], since the starter's `layers`, `network` and `connector` stay as they are. What this record finds of them is for whoever owns the starter to weigh:
    - **One column of notes.** `layers` places its notes to the right of the stack alone. A note tied to two levels, with another note tied to a level between them, crosses in every order of the column, where a note on the left would not.
    - **Cornered ties in one gap.** With `route: corners`, every note's tie turns halfway across the one gap between the notes and the stack, so two whose turns overlap down that gap run along each other.
    - **A tie's side.** A note's tie leaves by the side that faces its level. Where the note lies further above or below the level than beside it, the tie leaves by the note's top or bottom, between two notes, and runs over the note beside it and over the levels between, straight or with corners.
    - **One look for every tie.** The `connector` draws a note's tie and a tie between levels in one look. Only an arrowhead, a route or a concept tells them apart, so where a page draws its level ties with no arrowhead, the starter gives a leader no look of its own.
    - **Labels with lines.** `network` draws a label's line wherever a column of labels is tied to the points an item exposes. Such ties are leaders. In one column they cross unless the content orders the labels so that they do not, and a label further above or below its point than beside it is left by its top or bottom, between two labels, as in `layers`.
    - **Where the fix belongs.** A crossing a library forces is that library's to mend, where the finding says its fix belongs (DEC-030 point 7). A local component that breaks `RS-GRAPHIC-004` is no remedy.
- **The work under project-kit#3342 that follows the acceptance,** in this change:
  - **The rule.** `RS-GRAPHIC-009` joins `GRAPHIC` in the words of point 1, accepted, with this record as its origin and the anchors of point 8. `RS-GRAPHIC-002` and `RS-GRAPHIC-007` gain their anchors on points 5 and 6. The set's opening sentence, which names the records that give each rule's source, comes to name this record for `RS-GRAPHIC-009`. The set takes its next major (point 7).
  - **The reviewer's body.** Under "Reading some rules", the readings of points 5 and 6 in their words, and how `RS-GRAPHIC-009` is read, by point 3: what a leader is, "ends at", "at once", an arrangement that avoids a crossing, a clear angle and running along, with a check of leaders and without one, and when a grade on it is a need. Under "Which rule a fault cites", the join that misses between a leader and its thing, a leader that ends at another thing, or at none near enough to point at any, or runs on past its thing, cites `RS-GRAPHIC-009` (point 4). Under "Grades", the rule takes a grade on each page, and none on a page with no leader, which goes under `not-graded`.
  - **The design knowledge.** A topic, "Working in layers": naming a page's layers, setting them apart, pinning a note or a label to what it explains, and how a layered page fails. Each idea names its source as it was read, by point 2's last bullet. It gives no count of layers and does not restate the rule (DEC-030 point 8). Its line in the index says when to read it.
  - **The designer's method.** Step 2 names a page's layers, its base and each layer over it, and what each note or label explains or names, as a reason of structure. Step 4 chooses what sets each layer apart, and how each note or label is pinned, by its place or by a leader and its course, as reasons of form. Each points at the topic. The brief's six aspects stay as they are ([visual-communication:DEC-029-piece-brief] point 2).
  - **The new major wherever the shipped set's major is meant,** such as the example of a pin in the capability's files page, the configuration schema's comment and the tests.
- **What the new major brings,** in the change that lands the rule:
  - **Adopters' pins.** A project's set that inherits the major before it fails validation until the project reads the new rule and moves its pin (COR-051 point 7). Until then no rule of `GRAPHIC` binds through that set.
  - **Bars.** A bar that names the set at the major before it, or one of its rules at that major, fails the capability's check until the project moves it (DEC-042 point 3). The bar of the repository the capability is authored in names `RS-GRAPHIC-001` to `RS-GRAPHIC-007` at `@2` today. Moving them is a change to that bar, which its file asks its maintainer's own yes for, and whether it covers `RS-GRAPHIC-009` is that maintainer's choice too.
  - **The hold.** A new major of a set a bar covers lapses the hold (DEC-042 point 9). A bar that covers `RS-GRAPHIC-009` gets the hold only where an accepted calibration gave that rule evidence of its own (DEC-042 point 10).
  - **Its changeset and migration.** That change declares, in its changeset, that the set has a new major, and its release notes tell a project to read the rule and move its pin and its bar. No migration moves a pin or a bar, since the project's own review is what a pin waits for (COR-051 point 7). That change runs the check for owed migrations, and carries one only if the check names it.
- **Open, for when this change meets project-kit#3396.** That change proposes new words for `RS-GRAPHIC-001`, `RS-GRAPHIC-003` and `RS-GRAPHIC-007`, and nothing here rests on them. The set's major is point 7's. One question waits for the two to meet:
  - **The reading of `RS-GRAPHIC-007`.** Point 6 reads that rule as the default branch words it. Where its words change first, the reading is read again against them before this change lands.
- **Left open:**
  - **A check of leaders,** that measures where lines cross, at what angle, and where one runs along another, with its reach and its findings. A record of its own decides whether to build it. The reviewer's body is worded for both states (point 3).
  - **Leaders drawn untidily,** at mixed angles or out of column: whether they break a rule. Drafting asks that two or more leaders to adjacent areas be drawn parallel, and that each be a single straight inclined line, neither horizontal nor vertical, bent only where that cannot be avoided. It asks a drawing to avoid long leaders, and small angles between a leader and the surface it ends at (ANSI Y14.2M-1979, 3.6.3).
