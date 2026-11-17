---
id: DEC-067
title: The check of edges that nearly line up compares parts of different groups on one page
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the check of edges that nearly line up compares only siblings, the parts one group holds directly. So it never compares a title in a header with the paragraph in the body below it, nor the titles of two cards in one row, though a reader sees whether those line up. This record widens the check to every two parts of different groups on one page, and to the spacings of every two groups there. It tells a near miss from a difference meant by the tests it already makes of siblings: two values that differ by more than a pixel and by less than the brand's smallest step of space nearly agree, and a pair that lines up on one line of an axis is not reported on another line of it. A near miss that two parts show only because the groups they lie in show it is reported once, at the outermost parts that show it.
- **Left out:** two parts on different pages, a group with a part it holds, and the gap between two parts of different groups.
- **The reviewer** does no sums where the check measured. Where it did not measure two parts of different groups, such as at a key whose brand gives no step of space, the reviewer judges them on the image first, since no reader sums over most pairs of a page.
- **The check of boxes that overlap** is not widened: it compares siblings alone.

## Context

[visual-communication:DEC-046-faults-lower-grades] point 3 adds two checks of boxes, which compare the siblings of each scene: one reports edges that nearly line up, the other boxes that overlap. Each states its *reach*, the kinds of place it measures and those it leaves out, and a reader reads its silence as measured only at a kind its reach measures ([visual-communication:DEC-063-where-a-check-measures] points 1 and 3). When this record was decided, the reach of both left out two parts of different groups. There the reviewer judges on the image first, and reads the frames only where the image shows a near miss or an overlap (DEC-063 point 4). DEC-063 names the cost: a near miss too small to see goes unsummed there, in the craft the first calibration found the review weak on. It names this widening as the follow-up that makes the commonest of those places the check's (DEC-063, Rationale and Implications). DEC-046 point 3 decides what the check compares among siblings, so which pairs across groups it compares, and how it tells one meant to differ from a near miss, is this record's.

Three places a reader lines up across groups:
- **A margin.** A header group holds a title, and a body group holds a paragraph. Both groups start at the page's margin. The title is set 0 px in and the paragraph 3 px, under a brand whose smallest step of space is 4 px (DEC-063, Context).
- **The matching parts of a row.** Two cards stand in a row, their tops on one line. The first sets its title 16 px down and the second 18 px. The cards are siblings and line up. Their titles are not siblings.
- **One spacing.** Two lists on one page set their items 12 px and 14 px apart. Each list's own gaps are even.

The words it uses:
- **A part** is an element a scene draws, a group among them. A group **holds** only the parts it holds directly, as in DEC-063. A part lies **below** a group that holds it, and below each group that group lies below. **Siblings** are the parts one group holds.
- **Two parts of different groups** are two parts that different groups hold, neither below the other.
- **A page** is what parts are drawn on (DEC-046 point 3). A part lies **on** a page where it lies below it.
- **A box** is the rectangle a drawn part takes on the page (DEC-046, Context). A part lies **inside** another's box where its own box lies within the other's, within a pixel of rounding on each side.
- **The lines of an axis** are, across, the left edges, the centres and the right edges, and, down, the tops, the middles and the bottoms. A part's **insets** in a box it lies inside are its distances from that box's edges on the two sides of an axis.
- **A spacing** of a group is, on one axis, the gaps between its siblings that lie within a pixel of each other, each gap taken from a sibling to the nearest one after it that stands beside it, as DEC-046 point 3 takes them.
- **Nearly agree:** two values differ by more than a pixel of rounding and by less than the brand's smallest step of space at the scene's key (DEC-046 point 3). Two parts whose values on a line nearly agree show a **near miss** there.
- **Measured**, **a statement** and **a reader of the checks** are DEC-063's.

## Decision

**The check of edges that nearly line up compares every two parts of different groups on one page, and the spacings of every two groups there, by the tests it makes of siblings. A near miss is reported once, at the outermost pair of parts that shows it. Where the check did not measure two parts of different groups, the reviewer judges them on the image first.**

### 1. Two parts of different groups on one page are compared as two siblings are

- **Which pairs.** Every two parts of different groups that lie on one page, of the parts the check compares among siblings: no line, no group that draws nothing but lines, no element of no area and no page (DEC-046 point 3).
- **Where on the page.** Their boxes lie in the frames of different groups. Each is taken where it lies on the page: its own place, with the places of the groups it lies below added.
- **What it compares.** What DEC-046 point 3 compares of two siblings: on each axis, their three lines; and, where one lies inside the other's box, the inner part's insets on the two sides of each axis, in place of those lines.
- **The same finding.** It reports a near miss as among siblings, naming the two parts and each line, or each inset, and the step. The finding asks the reviewer for attention and never fails (DEC-046 point 3).
- **This check alone.** The check of boxes that overlap compares siblings alone, as DEC-046 point 3 decides.

### 2. A near miss is told from a difference meant by the tests made of siblings

The check tells two parts meant to differ from a near miss by the tests DEC-046 point 3 makes of two siblings, and by no other.
- **The bound.** Two values nearly agree only where they differ by more than a pixel and by less than the brand's smallest step. A difference that small is no spacing the brand offers, whichever groups hold the two parts, so it was hardly chosen. A difference of a step or more may be a spacing, and the check reports none.
- **The line chosen.** A pair that lines up within a pixel on one line of an axis is not reported on another line of it. Texts of different widths on one margin differ at their right edges, and that near miss follows from the line chosen. A part inside another's box, within a pixel of one of that box's edges on an axis, lies on that edge, so its insets on that axis are not compared.
- **No test of distance, kind or depth.** A margin runs the length of a page, so a heading at its top and a note at its foot lie on one line for a reader, whatever lies between them. A text and a picture share a margin. The matching parts of two cards lie as deep below their page as each other, and a header's title and the paragraph of a body section do not.
- **The rest is the reviewer's.** A pair that passes these tests and is no fault, such as two parts of unrelated groups that lie a few pixels apart by chance, is named for the reviewer. It judges the place on the image, as it judges each place the check names (DEC-046 point 3).

### 3. A near miss is reported once, at the outermost pair that shows it

- **Outer pairs.** Take the nearest group that both parts of a pair lie below. On each side, the part itself and each group it lies below, beneath that group, are the side's *outer parts*. A pair's *outer pairs* are the pairs of one outer part from each side, other than the pair itself.
- **An outer pair's near miss.** Where an outer pair reports a near miss on a line, and the pair's values on that line differ by as much as the outer pair's, in the same direction and within a pixel, the near miss is the outer pair's. The check reports it there, and not again at the pair. A title set on its header's left edge misses the paragraph below by what the header misses it. Insets are read alike: the insets of the pair's inner part differ by as much as those of the outer pair's inner part, on the same side and within a pixel.
- **Only where the outer pair reports it.** An outer pair that passes the line over, since it lines up on another line of the axis, or since one of them lies inside the other's box, leaves the pair to be reported itself. A group's box holds room that draws nothing. A header and the paragraph below it may share their right edges while the title in the header is narrower, so their shared line is none a reader sees between the title and the paragraph.
- **The outermost.** Each outer pair is read by the same rule, so a near miss is reported at the outermost pairs that show it. A card's content set 2 px lower than its neighbour's sets every part of it 2 px lower, and one finding names the two contents. Where the outer pair is two siblings, its finding among siblings is that report.

### 4. The spacings of two groups on one page are compared

- **Two spacings that nearly agree.** Two groups on one page are reported where a spacing of one and a spacing of the other, on one axis, nearly agree. The finding names the two groups and the gaps of each spacing.
- **Each group's spacings** are those DEC-046 point 3 takes among its siblings.
- **Once.** Where one of the two groups also has a spacing within a pixel of the other's, the near miss lies among that group's own spacings, which the check reports among its siblings, and not again here.
- **Not the gap between two parts of different groups.** Such a gap is no spacing a component gave: it adds the two parts' places in their groups to the gap between those groups. The check compares those places and that gap where it compares the parts and the groups.

### 5. What it leaves out

- **Two parts that no one page holds,** on different pages, or one of them on no page. A page is drawn beside no other part (DEC-046 point 3).
- **A group and a part below it.** A group draws nothing of its own. Its box is the room its component was given, which the parts below it are placed in. A drawn edge round a part, such as a card's box behind its title, is a part the check compares with the title, among siblings or across groups (point 1).
- **What point 3 reports at an outer pair,** what point 4 reports among one group's spacings, and the gap between two parts of different groups (point 4).
- **What DEC-046 point 3 leaves out among siblings,** for the same reasons: a line, a group that draws nothing but lines, an element of no area, a page, and the lines and insets the line chosen passes over (point 2).

### 6. Where the check did not measure, the reviewer judges parts of different groups on the image first

- **Where it measured, no sums.** At two parts of different groups that the check measured, as DEC-063 point 3 reads its silence, the reviewer does no sums over the frames for what the check measures, as among siblings (DEC-046 point 3).
- **Where it did not, the image first.** Two parts of different groups that the check did not measure, such as at a key whose brand gives no step of space, the reviewer judges on the image first. It reads the frames there only where the image shows a near miss. Siblings the check did not measure, it reads from the frames (DEC-063 point 4).
- **The statement covers every place the check measures at its key:** each pair and group of siblings, and each two parts of different groups and each two groups on one page (DEC-063 point 2).

## Rationale

**Why every two parts of one page.** A reader sees the lines of a page, not its groups. A margin, a column or the top of a row runs across groups, so a part a few pixels off it is as plain beside a part of another group as beside a sibling. Groups are how components place their parts, and a reader never sees them (DEC-063, Context). A narrower set, such as the parts of two sibling groups alone, would leave out pairs a reader lines up as surely: the deeper parts of two cards, or a title and a paragraph that lie at different depths. Its edge would follow the components' structure, which no reader sees.

**Why the tests made of siblings.** Each rests on a reason that does not depend on which group holds a part. The bound rests on the brand's steps, which place parts through every group: a difference under the smallest step is no spacing the brand offers, whichever groups hold the two. The line chosen holds alike: two texts on one margin differ at their right edges whether or not one group holds both. Tests of their own across groups would tell a difference meant from a near miss by something other than what DEC-046 point 3 gives its reasons for.

**Why no test of distance, kind or depth.** Each would leave out a near miss a reader sees: a margin a heading and a far note share, a text and a picture on one margin, matching parts at different depths. What they would leave out that is meant, the reviewer judges on the image, at the cost of a look, as it judges every place the check names.

**Why once, at the outermost pair.** A card's content set 2 px lower than its neighbour's sets each part inside it 2 px off its match. Reported at every pair, one offset would be a finding at each pair of parts, each asking the reviewer to judge the same defect again. Reported at the outermost parts that show it, it is one finding, and it names where the mend lies: the content's place, not each part's.

**Why only where the outer pair reports it.** A group's box holds room that draws nothing, so an outer pair may share a line no reader sees, and pass over a near miss the parts inside it show. Were a pair left to an outer pair that passes it over, the title 3 px off the paragraph would be named nowhere. So an outer pair takes a near miss only where it reports it.

**Why spacings across groups.** One spacing used across a page is a line of its own: a reader sees two lists set 12 px and 14 px apart as one spacing missed. The gap between two parts of different groups is no spacing a component gave: it adds the gap between their groups to the parts' places in them, which the check compares on their own.

**Why a group is not compared with a part below it.** A group's box is the room its component was given, which the parts below it are placed in, so a part's insets in it measure the part against no edge drawn. The edges a reader sees round a part are drawn parts, a card's box or a panel's ground, which the check compares with the part, among siblings or across groups.

**Why the image first where the check did not measure.** DEC-063 point 4 has the reviewer read from the frames what a check of boxes measures wherever it did not measure a place of a kind its reach measures. Read so once the check measures across groups, a key whose brand gives no step of space would send the reviewer to sum most pairs of a page, which DEC-063 rejects for any reader ("The reviewer sums the frames at every kind of place the checks of boxes leave out"). Two parts of different groups that the check did not measure are judged as DEC-063 point 4 judges a kind of place a reach leaves out, so widening the check takes sums from the reviewer and asks it none.

### What it costs

- **More places for the reviewer to judge,** each on the image: the pairs of different groups that nearly agree by chance and are no fault.
- **Sums over many pairs of a page,** which the check makes alike each time. The work keeps them to the pairs whose values on a line lie within a step of each other.
- **What stays unsummed:** a near miss between parts of different groups too small to see, on an image the check did not measure, or at a key whose brand gives no step of space.

### Alternatives considered

- **The parts of two sibling groups alone.** Rejected, for the reason above: it leaves out the deeper parts of two cards, and parts at different depths.
- **Only pairs whose groups line up on the line compared.** Rejected: a heading in a sidebar and one in the main column, whose groups start at different heights, would be left out, though the headings nearly share a top.
- **Only parts that stand beside each other, with nothing between.** Rejected, for the reason above: a margin runs the length of a page.
- **Parts of one kind alone,** such as texts with texts. Rejected: a text and a picture share a margin.
- **Every pair reported, with no outer pairs.** Rejected: one group's offset would be a finding at each pair of its parts.
- **Each near miss reported at the innermost parts,** those that draw. Rejected: one offset would be a finding at each drawn part inside the group, none of which names where the mend lies.
- **A pair passed over wherever an outer pair passes the line over.** Rejected, for the reason above: a group's box may share a line no reader sees.
- **The gap between two parts of different groups.** Rejected, for the reason above.
- **A group compared with a part below it.** Rejected, for the reason above.
- **The parts a tie draws, such as its sign, left out across groups.** Not taken. A tie's sign lies where the tie's route puts it, and a near miss of it with a part beside it is seen like any other. The reviewer judges each such place on the image, as it judges every place the check names.
- **The reviewer reads two parts of different groups from the frames wherever the check did not measure them.** Rejected, for the reason above.
- **Widening the check of boxes that overlap in the same change.** Not taken. This record answers a near miss too small to see, which DEC-063 found unsummed across groups. An overlap is seen on the image, and where the viewing step reads what covers a text, it names a text that a part of another group covers ([visual-communication:DEC-037-text-the-page-hides] point 1). Its trigger to revisit: a calibration finds the review missing overlaps across groups.

## Implications

- **This record changes nothing a project could observe.** The work that builds it changes a check's findings, and declares that in its changeset, in the same change.
- **It lands before the calibration,** as DEC-063's Implications place this widening, for economy and by no wait this record decides ([visual-communication:DEC-042-grades-bar-and-loop] point 9).
- **Each edit below refines its record in place, and this record overturns none.** Each is made in this change once this record is accepted, and cites it (COR-066 point 5). Accepting this record accepts them.
  - **DEC-046 point 3,** the bullet "Edges that nearly line up". After its first sentence, "A check compares the boxes of siblings: their edges, their centres and the gaps between them.", it comes to add: "It compares every two parts of different groups on one page too, and the spacings of every two groups there, by the same tests (refinement per [visual-communication:DEC-067-edges-across-groups] points 1 to 5)."
  - **DEC-046 point 3,** the bullet "The reviewer judges each place the checks name". Its sentence "Where it did not measure a place of a kind its reach measures, the reviewer reads from the frames what that check measures." comes to read: "Where it did not measure a place among siblings of a kind its reach measures, the reviewer reads from the frames what that check measures. Two parts of different groups that it did not measure, the reviewer judges on the image first, and reads the frames there only where the image shows a near miss (refinement per [visual-communication:DEC-067-edges-across-groups] point 6)." In its next sentence, "such as two parts of different groups" comes to read "such as lines and arrows". The rest of the bullet stands.
  - **DEC-063's summary.** Its sentence "It may never compare that kind of place: the checks of boxes compare only the parts one group holds directly, so they say nothing of a title in one group beside a paragraph in another." comes to read: "It may never compare that kind of place: the check of boxes that overlap compares only the parts one group holds directly, so it says nothing of a title in one group that runs into a paragraph in another." Its sentence "The kinds of place their reach leaves out, it judges on the image first, and reads the frames there where it sees a near miss or an overlap." comes to read: "The kinds of place their reach leaves out, and two parts of different groups a check did not measure, it judges on the image first, and reads the frames there where it sees a near miss or an overlap (refinement per [visual-communication:DEC-067-edges-across-groups] point 6)."
  - **DEC-063's Context,** the bullet "A kind of place it never compares". Its sentence "The checks of boxes compare the two groups, and the parts each holds only with each other, so they never compare the title with the paragraph." comes to read: "When this record was decided, the checks of boxes compared the two groups, and the parts each holds only with each other, so they never compared the title with the paragraph. The check of boxes that overlap compares them so."
  - **DEC-063 point 2,** the bullet "What a statement covers". Its sentence "So the check of edges that nearly line up states it once at each such key, and covers every pair and group of siblings at that key." comes to read: "So the check of edges that nearly line up states it once at each such key, and covers every pair and group of siblings at that key, and every two parts and every two groups on one page there (refinement per [visual-communication:DEC-067-edges-across-groups] point 6)."
  - **DEC-063 point 4,** the bullet "The checks of boxes". Its sentence "Where one of them did not measure a place of a kind its reach measures, the reviewer reads from the frames what that check measures." comes to read as the edit to DEC-046 point 3 above has it: "Where one of them did not measure a place among siblings of a kind its reach measures, the reviewer reads from the frames what that check measures. Two parts of different groups that it did not measure, the reviewer judges on the image first, and reads the frames there only where the image shows a near miss (refinement per [visual-communication:DEC-067-edges-across-groups] point 6)." The rest of the bullet stands.
  - **DEC-063's Rationale,** "Why siblings from the frames, and the rest on the image first". Its sentence "The kinds the checks' reach leaves out take in every pair of parts in different groups, and, for every pair that lines up on one line of an axis, the other lines of it: most pairs on a page." comes to read: "The places the reviewer judges on the image first take in every pair of parts in different groups that a check of boxes did not measure, and, for every pair that lines up on one line of an axis, the other lines of it: most pairs on a page." Its sentence "A near miss too small to see goes unsummed there, until widening the check to edges across groups makes the commonest of those places the check's (Implications)." comes to read: "A near miss too small to see goes unsummed there, wherever the check of edges that nearly line up did not measure it (refinement per [visual-communication:DEC-067-edges-across-groups] point 6)."
- **Read against this record, and left as they stand:**
  - DEC-046 point 3's "Boxes that overlap", since that check compares siblings alone (point 1);
  - DEC-046 point 3's "Both ask for attention and never fail", since a near miss across groups asks for attention as one among siblings does;
  - DEC-046 point 2, and point 3's "An edge out of line", since the fault of alignment cites `RS-GRAPHIC-002`'s "lined up" whichever groups hold the parts;
  - DEC-063 point 1, whose duties the check's reach meets as it widens: its id stays, and its entry and its code state the new clauses;
  - DEC-063's Implications, the follow-up that widens the check, which this record and the work below carry out;
  - DEC-063's Alternatives, "The reviewer sums the frames at every kind of place the checks of boxes leave out", since point 6 rests on it;
  - [visual-communication:DEC-062-checks-beside-the-frames]'s Context, which says what DEC-046 point 3 adds, and point 2, since the report carries the check's reach as the code that ran states it;
  - [visual-communication:DEC-030-design-agents] point 7's "With the checks" and [visual-communication:DEC-015-viewing-step-and-reviewer] point 7's "Its remit", since what the check measures stays the check's where it measured, and the reviewer's to judge where it did not.
- **The work that builds it,** under [project-kit#3343](https://github.com/aleskalfas/project-kit/issues/3343), in this change once this record is accepted:
  - the check compares every two parts of different groups on one page, and the spacings of every two groups there, as points 1 to 5 say, and names in each finding the two parts or the two groups. It keeps its sums to the pairs whose values on a line lie within a step of each other;
  - its reach, in its entry and in its code, beside its id, which stays. It comes to measure the lines and the insets of two parts of different groups on one page (point 1) and the spacings of two groups on one page (point 4), each clause citing this record. It comes to leave out two parts no one page holds, a group and a part below it, the gap between two parts of different groups, the lines and insets of a pair an outer pair of which reports its near miss, and a spacing near another group's where one of the two groups has both (points 3 to 5), each citing this record. Its clause that leaves out two parts of different groups, since it compares siblings alone, goes from its reach, and stays in that of the check of boxes that overlap. Its statement at a key with no step covers each place it measures there, and says so in its words. Tests plant a case for each new clause, and the work repeats the audit of each path the check's code passes over (DEC-063 point 1);
  - the list of checks: the check's row, and its paragraph on what the checks of boxes read, say what it compares across groups;
  - the reviewer's body: where the check did not measure two parts of different groups, it judges them on the image first (point 6). Its reading of alignment names the lines parts of different groups may share, such as a page's margin, a column, and the tops of the matching parts of a row's cards;
  - its changeset, which declares that the check names places it did not name before.
