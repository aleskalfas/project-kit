---
id: DEC-046
title: A fault lowers the grade of the rule whose words name it
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the review of a piece was tested once. It graded a series of designs that an outside judge, a senior designer from outside the capability, had ranked beforehand. The test found four things the rules judge weakly or not at all. This record says where each belongs, and decides one thing that holds for every rule.
- **A defect lowers a grade.** The reviewer keeps a list of defects, such as an overlap. Each is a plain error of drawing, never a matter of design. Where a rule's own words name such a defect, a page that shows it is graded below *professional* on that rule.
- **Typography,** how a paragraph is set, gains a new rule, since no rule, defect or check judges it.
- **Craft,** whether parts line up, stand clear of each other and meet where they join, gains no rule. The list of defects and the rule on grouping judge it. Two new automatic checks find boxes that overlap and edges that nearly line up, and the reviewer judges each place they find.
- **Legibility at the medium's size,** whether a text is large enough where the piece is shown, gains no rule. Comparing a text's size with the smallest its medium allows is an automatic check's. Where that check judged no text's size, or while the capability ships none, the review can say only that a text cannot be read where the piece is shown, as far as the image lets the review judge, so the gap stays open there.
- **Colour** gains no rule. The rules on form and on the focal point judge it, and the rest is a brand's look or a matter of taste.

The new rule lands in a later change, which gives the rule set a new major version. The review is tested again only once that rule, the reviewer's new instructions, the new teaching on type and colour, and all three automatic checks have landed: the two of boxes and the one of a text's size (point 8).

## Context

[visual-communication:DEC-042-grades-bar-and-loop] point 2 has a refinement of the record of the principles ([visual-communication:DEC-028-principles-of-visual-communication]) decide where each gap belongs. This record is that refinement.

The words it uses:
- **The canon** is the published, established works of the field, which each rule is taken from (DEC-028 point 1).
- **The review** is what the capability's reviewer agent does: it reads the images of a piece's pages and reports. Its *body* is the file of instructions it works by.
- **A check** is a measurement a command makes on every render, with no judgement. A check's finding either *fails* or *asks for attention*. It asks for attention when someone is expected to act, and names who ([visual-communication:DEC-002-files-and-validation] point 7).
- **The capability's list of checks** is its page that lists each check and its findings, `checks.md`.
- **A fault** is one of the defects the reviewer's body lists, such as an overlap. It is a drawing that does not show what the content, the brand or a passing check says it should, and never a judgement of design ([visual-communication:DEC-030-design-agents] point 6).
- **A grade** is one of four words the review gives each rule on each page: *below competent*, *competent*, *professional* and *excellent* (DEC-042 point 1). A grade below professional is reported as a finding on its rule.
- **A bar** is a project's setting that names rules and the grade each page must reach on them, professional or excellent (DEC-042 point 3).
- **The designer** is the capability's agent that designs a piece and mends it after each review (DEC-030 point 2). Its *loop* is its rounds of mending (DEC-042 point 6).
- **An outside judge** is a senior designer, a person or an agent briefed as one, outside the capability. The judge ranks a *ladder*, a series of designs of one piece, before any run of the review on it (DEC-042, Context).
- **A calibration** is a run of the review on such a ladder, read against conditions fixed before the run (DEC-042 point 9). DEC-042's Context reports the first, which found the four gaps. This record calls it *the first calibration*.
- **The hold** is the switch by which the verdict read from the review's grades ends the designer's loop at the bar. It is on only where whoever maintains the capability has accepted a calibration's report (DEC-042 points 9 and 10).
- **The reading** is how the reviewer interprets a rule or a fault. It lies in the reviewer's body, or in the *design knowledge*, the folder that teaches what the field's practice is (DEC-030 point 8).
- **A brand** is the library that holds a piece's look as values: its typefaces, sizes, colours and spaces. Its *palette* is the colours it gives.
- **A typeface** is one design of letters, such as Helvetica.
- **A hue** is a colour's family, such as red or blue.
- **A box** is the rectangle a drawn part takes on the page. **The frames** are the file beside each image that gives every drawn part's box, in pixels.
- **Siblings** are the parts one part holds directly, such as the items of one list or the cards of one row.
- **A mode** is one variant a piece is drawn in, such as light or dark. Each image shows one mode.
- **A major** is the first number of a rule set's version. A project's set that takes rules from another names that set's major, as in `GRAPHIC@1`. That is its *pin* (COR-051 point 7).

What judged each gap when the first calibration ran:
- **Craft.** `RS-GRAPHIC-002` asks that what belongs together is "placed together and lined up", that "what is separate is set apart", and that steps "are joined in the order they are read". The reviewer's fault of alignment covers parts that belong on one edge, one line or one even spacing and do not lie there. Its fault of overlaps covers a part over a part, and its fault of a part missing or blank covers a part cut off. So craft was named, and the first calibration found it weak all the same.
- **Typography.** No rule and no fault judged how long a text's lines are, how far apart they stand, or how they break. The design knowledge's topic on type taught it, and nothing was graded on it.
- **Legibility at the medium's size.** `RS-GRAPHIC-005` asks that everything "can be read where the piece is shown". DEC-028 point 10 gives the smallest text size for a medium to a check, which had not been built (DEC-042 point 2). The review graded the rule by how much a page holds (DEC-042, Context).
- **Colour.** `RS-GRAPHIC-007` asks that every difference a reader takes for meaning is one the content has. DEC-028 point 11 gives "five unrelated hues on one chain" as a break of it. Contrast is a check's.

## Decision

**A fault lowers the grade of the rule whose words name it: a page that shows one is below professional on that rule. Of the four gaps, typography alone gains a rule, on how running text is set, which a later change lands; craft, legibility at the medium's size and colour gain none.**

### 1. How a gap is placed

DEC-042 point 2 gives four places. This record takes them in this order for each gap:
- **The reading,** where a rule or a fault names the gap. A second rule on the same test would make one defect fail twice.
- **A check,** for each part that needs no judgement (DEC-028 point 1).
- **A brand's values,** where the part is the look.
- **A rule of the canon,** only for what is left: a test that no rule, fault or check makes, which a source of the field states.

### 2. A fault lowers the grade of the rule whose words name it

This point holds for every rule the review grades, in `COMM` and in `GRAPHIC`.
- **When a fault cites a rule.** A fault cites a rule where the rule's words name the defect, and only there: no other rule is a ground of the fault (DEC-030 point 6). An offset between parts that belong together is named by "lined up" in `RS-GRAPHIC-002`, so that fault cites that rule. No rule of `GRAPHIC` names a wrong picture, so there that fault cites none. The reviewer's body holds which kind of fault cites which rule, for both sets.
- **Such a fault is a break the rule's text settles.** The rule's words name the defect, so no reading of the rule is left to choose (DEC-030 point 6). Whether the defect is on the page is the fault's own judgement, made on the image.
- **How far it moves the grade.** A page on which the review finds a fault that cites a rule takes a grade below professional on that rule, as a break a rule's text settles does (DEC-042 point 1). *Professional* is the work a professional designer hands over, and none hands over a page with such a defect. Which of the two lower grades it takes is a reading, since no rule's text names one for a fault.
- **Why two runs grade alike.** A bar asks professional or excellent, so no bar's verdict turns on which grade below professional a page takes. The same fault gives the same answer on every run, however small the defect.
- **One finding of the defect.** The fault is the one finding of what the reviewer observed (DEC-030 point 6). The rule's grade on that page is the rule's own finding, as every grade below professional is (DEC-042 point 1). It names the fault as its evidence, and does not describe the defect again.
- **A fault that cites no rule** moves no grade. The designer mends it as it mends any fault it judges right (DEC-030 point 2).
- **Among the faults, these are named by no rule of `GRAPHIC`:** a part the page does not draw at all; a wrong picture; a typeface the brand does not give a text's role, where every text of that kind looks alike; and a join that misses between parts that are not steps. Whether a rule of `COMM` names one of them is traced by the work on the reviewer's body.

### 3. Craft is the faults' and `RS-GRAPHIC-002`'s, with two checks

Craft gains no rule. Each part of it has a home, and this record found nothing left over that a rule could judge.

- **An edge out of line** is the fault of alignment. It cites `RS-GRAPHIC-002`, whose words "lined up" name it.
- **A part over a part** is the fault of overlaps. It cites the same rule: "what is separate is set apart".
- **A join that misses** joins the fault of overlaps: a line or an arrow that stops short of the part the content joins it to, or runs past it. The fault's name, in the reviewer's body and in the agent's description, says so. Between steps it cites the same rule, "joined in the order they are read". Between parts that are not steps it cites none.
- **A part cut off** is the fault of a part missing or blank.
- **Where the rule ends and the fault of alignment begins.** `RS-GRAPHIC-002` judges whether parts that belong together were given a shared line at all, which is a judgement of design. The fault judges whether parts that were given one lie on it. How the reviewer tells a shared line, and what a box does not show of what is drawn in it, is its body's.
- **Not a brand's value.** A brand sets the unit and the steps of space ([visual-communication:DEC-004-brands-and-notations]). Where parts lie is the piece's and its components'.

The two checks, which do the arithmetic:
- **Edges that nearly line up.** A check compares the boxes of siblings: their edges, their centres and the gaps between them. It reports a place where the values nearly agree and do not: they differ by more than a pixel of rounding and by less than the brand's smallest step of space. A difference that small is no spacing a brand offers, so it was hardly chosen.
- **Boxes that overlap.** A check reports two siblings whose boxes overlap, where neither holds the other. It leaves out lines and arrows, whose crossings stay the reviewer's to find.
- **Both ask for attention and never fail.** The arithmetic needs no judgement, so it is a check's (DEC-028 point 1). Whether the result is a defect does need one. A library's component may place one part on another on purpose, such as a badge on a corner, and a box may differ from what is drawn in it.
- **The reviewer judges each place the checks name,** on the image, and says whether it is a fault or is meant. Where the checks ran, it does no sums over the frames. Where they did not, it reads the offsets from the frames. A check that asks for attention has measured and has not judged, so this keeps "what a check measures stays the check's" (DEC-030 point 7).
- **An overlap that is meant.** The work that builds the checks settles how a component says an overlap is meant, so that it is not reported for ever. Where that adds a field, it drafts the record first (COR-065 point 3).

### 4. Typography gains a rule

**`RS-GRAPHIC-008`, running text is set to be read.** The words the rule lands with:

> ## RS-GRAPHIC-008 — Running text is set to be read
>
> Running text is text meant to be read continuously, line after line, such as a paragraph. It is set so that a reader keeps their place. Its lines are neither too long nor too short to read with ease, for its typeface, its size and the number of columns it stands in. The space between its lines suits their length. Where its lines share a straight edge on one side only, their other ends look pleasantly uneven: neither almost straight nor ragged, with no line much longer or shorter than the rest, and forming no regular shape, such as a wedge or a curve.
>
> - **What it does not judge.** A heading, a title, a label, a cell of a table and an item of a list, however many lines each takes. A text whose lines the content breaks, such as code. Placeholder lines that stand for text in a drawing of a screen, and what lies inside a picture made elsewhere. A text in a script written without spaces between words. How short the last line of a paragraph is, since it ends where the text ends. The ends of the lines of a centred text. The gaps between the words of a text set with two straight edges. Which text ranks first, which is `RS-GRAPHIC-001`'s. Whether a kind of text keeps one look, which is `RS-GRAPHIC-004`'s. Whether a text can be read at all where it is shown, which is `RS-GRAPHIC-005`'s.
> - **From the text:** nothing, since a line's length and its spacing show only once the page is drawn.
> - **On the drawn page:** the whole rule, on each image, so in each language and at each size the piece is drawn in.

Accepting this record decides that the rule lands in these words. From the change that adds the rule, the `GRAPHIC` set holds its statement, as a set holds each of its rules' (COR-051 point 2). A rewording after that is made in the set, by the set's own path.

The source of each clause:
- **Line length, from two sources.** Robert Bringhurst: "Choose a comfortable measure". The *measure* is the length of a line, counted in characters. His range: "Anything from 45 to 75 characters is widely regarded as a satisfactory length of line for a single-column page set in a serifed text face in a text size." For several columns he gives another: "For multiple column work, a better average is 40 to 50 characters" (*The Elements of Typographic Style*, section 2.1.2). Matthew Butterick: "Aim for an average line length of 45–90 characters, including spaces" (*Practical Typography*). His figure is an average over a text, not a limit for each line. So the rule names the typeface, the size and the number of columns, and judges a text's lines together.
- **Line spacing, from one source.** Bringhurst: "Choose a basic leading that suits the typeface, text and measure" (section 2.2.1). *Leading* is the space between lines. A longer line needs more of it, so that the eye finds the start of the next line.
- **The uneven line ends, from one source.** A text whose lines share one straight edge ends unevenly on the other side, which typographers call the *rag*. Ellen Lupton: "A good rag looks pleasantly uneven, with no lines that are excessively long or short, and with hyphenation kept to a minimum. A rag is considered 'bad' when it looks too even (or too uneven), or when it begins to form regular shapes, like wedges, moons, or diving boards" (*Thinking with Type*, Text, Alignment).
  - **The rule takes her whole test:** pleasantly uneven, neither too even nor too uneven, no line much longer or shorter, and no regular shape. It leaves out only a paragraph's last line, for the reason given below.
  - **It leaves out her words on hyphenation.** The engine never hyphenates, so there is nothing to keep low.
- **On each size.** Tim Brown: on a screen, size, line length and line spacing are relations that change together as the reading conditions change (*Flexible Typesetting*). So the rule is judged on each size the piece is drawn at.

What the rule's words mean, and where they stop:
- **Running text is told by its kind,** never by how many lines it takes. It is what the content gives as a paragraph or as body text. Typographers use the term for exactly this, and the rule's sources speak of continuous reading.
- **Headings, labels, cells and list items are out.** No source of the rule speaks of them. A title on two short lines, a label that wraps, and a bullet on two lines break nothing here. A break in one that looks wrong is a note (DEC-030 point 6).
- **Centred text.** Both its sides are uneven, and Lupton's test is for a text with one straight edge. The clauses on line length and line spacing judge it. The clause on line ends does not.
- **Text with two straight edges,** which typographers call *justified*. It has no uneven ends, so that clause has nothing to judge. Its defect would be uneven gaps between words, which the rule does not judge. The engine sets a text from its start, its middle or its end, and never with two straight edges, so no piece draws one.
- **A paragraph's last line** ends where the text ends, so the rule's words leave out how short it is. Here the statement departs from Lupton's test, which names no such exception: a last line is shorter than the rest in nearly every paragraph, however well the text is set, so counting it would fail nearly every paragraph.
- **A script without spaces between words,** such as Chinese or Japanese. The sources count characters and words of scripts that part words by spaces. The rule's text leaves such a text out, so it takes no grade there, and the review says so (DEC-042 point 1).
- **Little or nothing to judge.** A deck of short bullets, a diagram with labels only and a board people fill in hold no running text. The rule takes no grade on such a page, and the review says so (DEC-042 point 1).
- **A grade on each page.** The rule judges pages one at a time.

What the rule leaves to others:
- **No figure.** The rule names no number of characters and no share of the size. The two ranges nearly agree. Each is given for one script, one kind of typeface and one medium, though, and a piece may be in none of them. The design knowledge says what each source teaches. A project that wants a limit adds it in a set of its own (DEC-028 point 1).
- **A brand's values.** A brand's text style holds its size and its line spacing. They are the look. Butterick ties line spacing to the size of the type alone: "For most text, the optimal line spacing is between 120% and 145% of the point size". That is what a brand's style sets. Where it does not suit the lines a piece draws, the finding's fix belongs to the brand.
- **Whether a text is large enough for its medium** is not this rule's. Point 5 places it.
- **Who can mend it.** A line's length follows from the width a layout or a component gives the text. The designer may choose another width or layout, and may reword or cut any word that is not the asker's (DEC-042 point 7). So nearly every finding of this rule is the designer's to mend, in the piece, a component or a library.
- **Rarely a need.** A *need* marks a grade only where no fix the designer may make would raise it, and only a tool the engine lacks would (DEC-042 point 4). The engine breaks lines by filling each one. Another way of breaking is such a tool, yet a new width or a reworded line nearly always mends the same edge. So the review marks a need here only where it says why neither would.
- **Languages.** Each language is judged on its own images, so a break that is bad in one translation is found there alone. Long compound words, as in German, make line ends rough in a narrow column, which is the rule's to find.
- **No "from the text" part.** Content sets no size and no spacing. A component does, and a text names a brand's style for its kind. So the text alone shows nothing of this rule.
- **No check and no new brand value.** A longest line a brand allows would be a limit, which is a project's taste or a check's threshold, and never a value a piece draws with (DEC-028 point 1; DEC-030 point 8).

### 5. The medium's smallest text size is the check's, and `RS-GRAPHIC-005` keeps whether a text can be read

Legibility gains no rule. The canon names it, and DEC-028 point 10 divides it: the smallest text size for a medium is a check's, and the rest is the rule's.

- **Comparing a text with its medium's minimum is the check's.** Comparing a text's size with the smallest its medium allows needs no judgement, so it is a check's (DEC-028 point 1). How the check finds a text's size and its medium's minimum is the check's own work, and this record decides none of it.
- **What the rule's first sentence judges,** on the drawn page: whether a reader can read each text as it was drawn, where the piece is shown (DEC-030 point 6). That stays the reviewer's wherever no check measures it ([visual-communication:DEC-015-viewing-step-and-reviewer] point 7). How the review reads it is the reviewer's body's.
- **"As it was drawn" takes in where the piece is shown.** The review reads each image as a reader would in the place the piece declares it is shown ([visual-communication:DEC-001-visual-communication-discipline] point 3, "What a piece declares"; DEC-030 point 6, "What it judges"). The rule's text names that place "as its `shown` field names, such as projected in a room, on a screen, or printed". The review takes the place from that declaration. It judges whether the drawn text can be read there, and never a text's size against a minimum, which keeps it apart from the alternative "The review judging text size from an image scaled to the medium", rejected below.
- **What its second sentence judges:** whether the page is taken in at a glance. How much a page holds is evidence for this sentence alone, and never for whether a text can be read.
- **One grade, and the finding names the sentence** it rests on.
- **A fault the rule's words name,** such as a text that does not read over a picture, holds its grade as point 2 says.
- **No small text fails twice.** Where the check judged a text's size, a text under its medium's minimum is the check's finding alone, since what a check measures stays the check's (DEC-030 point 7). It lowers no grade of `RS-GRAPHIC-005`, and the review's report names it in one line.
- **Anywhere the check judged no text's size,** or while the capability ships no such check, the review judges a text's size only as far as the image shows that the text cannot be read. It does not say that a text is too small for its medium.
- **Who says where no text's size was judged.** Where the check states that it judged no text's size, that statement is what tells the reviewer, and the review's report names it in one line, as it names a fault the check already reports (DEC-030 point 7). While the capability ships no such check, the review's report says that no text's size was compared with its medium's minimum. Either way the gap is named where it stays open.
- **One reading, with the check or without it.** The reviewer's body words this point's reading for both states, a check of a text's size and none, since the review also runs while the capability ships no such check. In each, the report names the gap as the bullet above says.
- **The check itself is not this record's.** DEC-042's Implications list it as later work. This record adds only how the reading and the check divide the rule.

### 6. Colour gains no rule

Each part of the gap has a home, or no source states it as a test.

- **Whether the colours match what the content has is `RS-GRAPHIC-007`'s.** That covers hues with no kinds behind them, and an order shown by unrelated hues. The reviewer's body tells the review to count the hues a page draws against the kinds its content names.
- **Where the strong colour sits is `RS-GRAPHIC-001`'s and `RS-GRAPHIC-007`'s.** The first ranks what is seen first, by colour among other means. The second allows emphasis only where the page's point needs it.
- **Strong colour used sparingly, over muted large areas, is a note of taste.** Edward Tufte, after the map-maker Eduard Imhof, teaches it for the design of information, maps first (*Envisioning Information*). A brand may fill a title page with its strongest colour, so it is no test every piece must pass. The design knowledge's topic on colour teaches it, and a note names it (DEC-030 point 6).
- **Whether a palette's colours go together is the brand's.** A palette is a brand's look, and its author answers for it. No source states a test of it that a piece could fail.
- **Nothing is said of modes.** The review grades each image, and each image shows one mode. So each mode is judged.
- **Contrast stays the checks'.**

### 7. The shape of the new rule

- **The shape DEC-028 gives.** `RS-GRAPHIC-008` judges every piece, as `GRAPHIC` does (DEC-028 point 3). It says apart what the text and the drawing show (DEC-028 point 4). It binds on nothing until a piece's content is an artefact (DEC-028 point 5).
- **Its sources are the canon's.** The first calibration's outside judge ranked its ladder by measures of its own. No wording, figure or example of those measures enters the rule, a check or a reading this record places (DEC-042 point 2).
- **It names no grade.** A rule's text names a grade only where a break of it blocks a bar (DEC-042 points 1 and 2). No source calls a break of this rule unworkable.
- **Its origin is this record, and it anchors as its set's rules do.** The rule names DEC-028 points 3 and 4 among the points it rests on, as every rule of `GRAPHIC` does, and this record's point 4. So a later change to any of them flags the rule to be read again.

### 8. The calibration waits for each check whose output the review reads

A calibration of DEC-042 point 9 runs only once each check whose output the review reads has landed. Here those are the two checks of boxes of point 3 and the check of a text's size of point 5.

- **Why it waits for them.** Such a check changes how the review grades the rule it bears on, `RS-GRAPHIC-002` or `RS-GRAPHIC-005`. Yet the command that gives the verdict compares with the accepted data only what DEC-042 point 9's list of what lapses the hold names, and that list names no check ([project-kit#3296](https://github.com/aleskalfas/project-kit/issues/3296) is the follow-up that would add them). So a calibration accepted before such a check lands keeps the hold on once it lands, vouching for a review that does not run as it was measured.
- **What else it waits for.** The calibration also waits for the rule of point 4 and for the work on the reviewer's body and the design knowledge. A change to any of them lapses the hold (DEC-042 point 9), so for them the wait is a matter of economy: a report accepted before one lands would lapse when it lands.
- **What it costs.** Only an accepted calibration's report switches the hold on (DEC-042 point 9), so the hold waits on the check of a text's size too ([project-kit#3185](https://github.com/aleskalfas/project-kit/issues/3185)). Until the hold is on, the verdict informs, and the designer's loop ends after two rounds and the person (DEC-030 point 2).
- **Its report says where no text's size was compared** with its medium's minimum. Which checks ran, and where, bounds the evidence each covered rule has. A calibration's report shows enough to weigh each covered rule's own evidence (DEC-042 point 9).

## Rationale

**Why a fault moves a grade.** A bar reads grades alone (DEC-042 point 1). If an offset between grouped parts left `RS-GRAPHIC-002`'s grade as it was, no bar would see it. DEC-030 point 6 gives one observation one finding, a fault before a rule finding. DEC-042 point 1 makes each grade below professional a rule finding. Neither says what a fault does to a grade, so this record decides it.

**Why the grade's finding is no second finding of the defect.** The review grades each rule on every image, whether or not it found a fault there (DEC-042 point 1), and each grade below professional is that rule's finding. So the review gives the rule its grade anyway, and the fault only decides which side of professional that grade falls on. This record says what the grade rests on, and keeps the defect described once, in the fault.

**Why the grade falls below professional, whatever the fault's size.** A scale of how far each fault lowers a grade would be a reading, and two runs would differ on it. One step that every fault takes gives two runs the same verdict.

**Why that decision has a point of its own.** It holds for every rule of both sets, and the edits to two other records rest on it. A point of its own lets each rule a fault cites anchor to it, so a change to it flags those rules and no others (DEC-028, "Why the reasons live in a record").

**What this costs.** A fault that cites no rule moves no grade, so a bar's verdict does not read it. Point 2 names the kinds no rule of `GRAPHIC` names. The designer mends each fault it judges right (DEC-030 point 2). That is no guarantee: where the verdict ends the loop, the loop may end with such a fault open. Whether a page with one may meet a bar stays DEC-042's question. For craft the cost is small, since only a join that misses between parts that are not steps cites no rule.

**Why typography alone gains a rule.** A rule duplicates nothing only where no rule, fault or check makes its test. Line length, line spacing and the line ends have no other home. Two sources state the first as a test, and one each the second and the third. Without a rule the review gives them no grade, so no bar can ask for them.

**Why running text is told by its kind.** The rule's sources speak of continuous reading: Bringhurst's range is for a page of text, and Butterick's for body text. So the rule judges what the content gives as a paragraph or as body text, where its sources state a test, and nothing else.

**Why craft gains none.** An edge out of line is the fault of alignment and `RS-GRAPHIC-002`. An overlap, and a join that misses, are the fault of overlaps and the same rule. A part cut off is the fault of a part missing or blank. A rule on craft would judge the same edge once more. The first calibration found craft weak while these existed, so what failed was the reading: the review judged alignment by eye, though the frames give each box.

**Why checks do the arithmetic.** Comparing the edges of every list on every page is sums over a file, which the reviewer does unevenly and a command does the same way each time. The checks leave the reviewer the part that is a judgement: whether the place they name is a defect.

**Why the medium's minimum is the check's, and the review keeps whether a text can be read.** A minimum size by medium needs no judgement, so it is a check's (DEC-028 points 1 and 10). The reviewer's remit is what no check measures (DEC-015 point 7), so whether a text as drawn can be read stays the review's. Where the check judged a text's size, a review that judged the minimum too would fail one small text twice.

**Why colour gains none.** Each test a source states has a home: `RS-GRAPHIC-007` judges hues against the kinds the content has, and `RS-GRAPHIC-001` what is seen first. What is left, strong colour used sparingly and whether a palette's colours go together, no source states as a test every piece must pass.

**Why the rule's words are in this record.** A person accepts a rule's words before the rule binds (COR-066 point 1), and reads them best beside the sources and reasons its origin gives. The change that adds the rule to its set shows it again, in the list of what that change makes accepted (COR-066 point 3). From then on the set holds the statement, as DEC-028 has it for every rule ("Why the reasons live in a record").

**Why no rule lands in this change.** A new rule makes a new major (COR-051 point 7), which every project that pins `GRAPHIC@1` must answer. That belongs with the reviewer's body and the design knowledge that read the rule, in a change that declares it.

### Alternatives considered

- **A rule on craft.** Rejected: the faults and `RS-GRAPHIC-002` judge each part of it, so the rule would judge one defect once more. Its trigger to revisit: a craft defect found that no fault and no rule names.
- **Widening `RS-GRAPHIC-002`'s text.** Not needed: its words say "lined up", "set apart" and "joined".
- **The reviewer comparing every edge from the frames, with no check.** Rejected: sums over a file are done unevenly by a reviewer and alike each time by a command.
- **A fault that cites a rule and leaves its grade alone.** Rejected: no bar would see the fault.
- **A scale of how far each kind of fault lowers a grade.** Rejected: it would be a reading, and two runs would differ on it.
- **The fault's lowering of a grade restated at each rule a fault cites.** Rejected: one decision would have many homes, and a change to it would have to find each.
- **A rule on every text of more than one line.** Rejected: it would reach a title on two lines, a label that wraps and a bullet, which no source of the rule speaks of. A rule that failed a two-line title for short lines would state a test the canon does not. Its trigger to revisit: a calibration finds headings or list items that wrap badly, and a source states a test for them.
- **Half of Lupton's test,** only the lines much shorter than the rest. Not taken: the rule would state a test its source does not.
- **Lupton's words on hyphenation kept in the rule.** Not taken: the engine never hyphenates, so there is nothing to keep low. Its trigger to revisit: the engine gains hyphenation.
- **A clause on the gaps between words in a text with two straight edges.** Not taken: the engine draws no such text. Its trigger to revisit: the engine gains it.
- **A rule that a page's colours form one scheme.** Rejected: its break, hues that read as no scheme, is DEC-028's own example of a break of `RS-GRAPHIC-007` (DEC-028 point 11).
- **A rule on muted grounds.** Rejected: it would fail a brand's title page in its strongest colour.
- **A rule on how many hues a page draws.** Rejected: it would fail a diagram whose eight concepts each keep their colour, as `RS-GRAPHIC-004` asks.
- **"Strong colour sparingly" as a clause of `RS-GRAPHIC-001` or `RS-GRAPHIC-003`.** Rejected: a brand may want the opposite.
- **The review judging text size from an image scaled to the medium.** Rejected: comparing a text's size with its medium's minimum is arithmetic, so it is a check's (DEC-028 point 1), and a review that made it too would fail one small text twice.
- **The review judging nothing of a text's size where no check judged it.** Rejected: whether a reader can read what was drawn is the reviewer's remit wherever no check measures it (DEC-015 point 7), and a text that cannot be made out in the image would pass unseen.
- **`RS-GRAPHIC-005` split in two rules,** one for each sentence. Not taken: with the minimum left to the check, both sentences rest on one reading of the page. Its trigger to revisit: the review grades the rule by how much a page holds.
- **A brand's longest line, with a check.** Rejected: it would be a limit, which is a project's taste, and no value a piece draws with.
- **A clause on a lone last word, and one on a heading parted from its text.** Not taken. For the first, this record found no source that states the test for every language. For the second, the engine flows no text from page to page, and nearness is `RS-GRAPHIC-002`'s.
- **A check of boxes that fails unless accepted,** as a loss is accepted in a piece. Rejected: an overlap a library's component means would need accepting in every piece that uses it.
- **The rule landed in this change.** Rejected: its new major belongs in a change that declares it, with the reviewer's body and the design knowledge that read the rule.
- **Calibrating before the check of a text's size,** with the report saying where no text's size was compared. Rejected: the command compares only what DEC-042 point 9's list names, and that list names no check, so a calibration accepted before the check lands keeps the hold on once it lands, for a review that does not run as it was measured. Its trigger to revisit: [project-kit#3296](https://github.com/aleskalfas/project-kit/issues/3296)'s refinement lands, after which waiting is a matter of economy, not safety.

## Implications

- **This change adds no rule and changes nothing a project could observe.** Its changeset, the file by which a change declares its effect on the next release, declares none. It owes no migration (COR-010).
- **Edits to DEC-028,** made in this change once this record is accepted (COR-066 point 5). Each holds before the rule lands and after it.
  - **Its summary.** "Each rule is taken from the established principles of its field, and this record names its source" comes to add: or, for `RS-GRAPHIC-008`, on running text, this record does (refinement per this record, point 7).
  - **Its Decision line.** "Each rule is taken from the established canon of its field, and this record names its source" comes to add the same.
  - **Point 1.** "Each is taken from a source this record names" comes to add: or, for `RS-GRAPHIC-008`, from one this record names (refinement per this record, point 7).
  - **Point 8,** the bullet on `RS-GRAPHIC-002`. After "the rule's judgement is mostly which parts belong together", it comes to say that whether parts that belong together were given a shared line is the rule's too, and that whether parts given one lie on it is the reviewer's fault of alignment, which cites the rule (refinement per this record, point 3).
  - **Point 10,** the bullet on `RS-GRAPHIC-005`. After "the glance test is the rule's", it comes to say that how much a page holds is evidence for the glance test alone, and never for whether a text can be read (refinement per this record, point 5).
  - **Its Rationale,** "Why the reasons live in a record". "The record gives each rule's id, title, sources and reason" comes to add that this record gives them for `RS-GRAPHIC-008`. "The rule's statement is its set's" stands.
  - **Its Implications.** "Each rule cites this record as its origin" comes to add: but `RS-GRAPHIC-008`, whose origin is this record (refinement per this record, point 7).
- **An edit to DEC-030,** made the same way.
  - **Point 6,** "One observation, one finding". Its three sentences stand, and two follow them. After the edit the bullet reads, whole: "**One observation, one finding.** Where one rests on more than one ground, it cites each. It takes the first of these kinds that applies: a fault, then a rule finding, then a brief finding. A rule is a ground of a fault only where the rule's words name the defect, so a fault cites that rule and no other. Where such a fault holds that rule's grade below professional, the grade's rule finding is no second finding of the observation: it names the fault as its evidence, and does not describe the defect again (refinement per this record, point 2)."
- **Edits to DEC-042,** made the same way.
  - **Point 1,** "Settled, or for a person". After its first sentence, it comes to say that a fault that cites a rule is a break that rule's text settles, so a page that shows one takes a grade below professional on the rule (refinement per this record, point 2). Its sentence "Every other grade is a reading" stands. This is the one place among the edited records that restates the decision of point 2.
  - **Point 9,** "A calibration". After "none runs before the refinement of point 2 has landed", it comes to add that none runs before each check whose output the review reads has landed either (refinement per this record, point 8).
  - **Its Implications,** the calibration among the work under project-kit#3148. After "once the refinement of DEC-028 lands", it comes to add: and each check whose output the review reads (refinement per this record, point 8).
- **Read against this record, and left as they stand:**
  - DEC-030 point 6's "A fault" and "A rule finding", since a fault stays no judgement of design, and the grade it holds is the rule's finding;
  - DEC-030 point 6's "A binding rule finding, settled or for a person", since its sentence on a break a rule's text settles holds of a fault that cites the rule;
  - DEC-030 point 2's "What it mends by itself", since the designer mends each fault it judges right, whether it cites a rule or not;
  - DEC-030 point 6's "What it judges" and DEC-015 point 7's "Its remit", since whether a reader can read a text as drawn stays the reviewer's wherever no check measures it (point 5);
  - DEC-030 point 7's "With the checks", since the two checks of boxes measure, and the reviewer judges the places they name;
  - DEC-028 point 9 and point 10's bullet on `RS-GRAPHIC-006`, since colour gains no rule and no reading of theirs changes;
  - DEC-028 point 11, since its words on `RS-GRAPHIC-007` hold as they are: point 6 says how the review finds the break they name, by counting the hues a page draws against the kinds its content names, and that reading is the reviewer's body's;
  - DEC-028's Implications, "which finding the reviewer makes where a rule and its list of faults name one defect", since DEC-030 point 6 answers it with the fault, and point 2 keeps that answer;
  - DEC-042 point 2's "A blocking fault that judges design is a rule's", which stays open below.
- **Later work under [project-kit#3148](https://github.com/aleskalfas/project-kit/issues/3148),** each in a change of its own. A calibration grades by the rules, the reviewer's body, the design knowledge and the checks whose output the review reads, as shipped (DEC-042 point 9).
  - **The rule.** It adds `RS-GRAPHIC-008` to the `GRAPHIC` set in the words of point 4, accepted, with this record as its origin and the anchors of point 7. It has each rule a fault cites, in either set, name point 2 among the points it rests on. It has `RS-GRAPHIC-002`, `RS-GRAPHIC-005` and `RS-GRAPHIC-007` name points 3, 5 and 6 too. It rewords the set's opening sentence, which says DEC-028 names each source. The calibration waits for it (point 8).
  - **The reviewer's body.**
    - How alignment is read: which lines siblings may share, that parts which differ on purpose and share a line are aligned, how even spacing is read, and what a box does not show of the letters or the drawing in it.
    - The fault of overlaps with the join that misses, named so in the body and in the agent's description.
    - Which kind of fault cites which rule, in both sets, by point 2, and the grade such a fault holds its rule to.
    - How the reviewer judges the places the two checks name.
    - The readings of `RS-GRAPHIC-005` and `RS-GRAPHIC-007` of points 5 and 6, the first worded for a check of a text's size and for none, and how `RS-GRAPHIC-008` is read.
    - How the reviewer tells that the capability ships no check of a text's size. Not from a piece's findings alone: a check that passed every text may state nothing of their sizes, as a check that is not shipped states nothing. It tells it from what the check's output can state, as the capability's list of checks gives it: the list names a finding for a text smaller than its medium allows only while the capability ships such a check.

    This joins the reviewer's body DEC-042's Implications list. The calibration waits for it (point 8).
  - **The design knowledge.** The topic on type gains the uneven line ends and what each source says of line length and line spacing, with Lupton and Butterick among its works. The topic on colour gains a question on strong colour over large areas. The calibration waits for it (point 8).
  - **The two checks of boxes** of point 3, each with its entry in the capability's list of checks. The calibration waits for them (point 8).
  - **The check for a text smaller than its medium allows,** under whichever record decides it, is the work DEC-042's Implications list, and how it finds a text's size and its medium's minimum is that work's to decide. The calibration waits for it (point 8).
  - **The calibration** DEC-042 point 9 describes, last.
- **What `GRAPHIC@2` brings,** in the change that lands the rule:
  - **Adopters' pins.** A project's set that takes rules from `GRAPHIC@1` fails validation until the project reads the new rule and moves its pin (COR-051 point 7). Until then no rule of `GRAPHIC` binds through that set.
  - **Bars.** A bar that names `GRAPHIC@1` fails the capability's check until the project names `GRAPHIC@2` (DEC-042 point 3).
  - **The hold.** No hold is on when `GRAPHIC@2` lands: the calibration waits for the rule, so no calibration's report is accepted before it. A bar that names `RS-GRAPHIC-008`, or all of `GRAPHIC@2`, gets the hold only where the calibration that follows tested each rule the bar names (DEC-042 points 9 and 10).
  - **Its changeset and migration.** That change declares, in its changeset, that the set has a new major, and its release notes tell a project to read the rule and move its pin and its bar. No migration moves a pin or a bar, since the project's own review is what a pin waits for (COR-051 point 7). That change runs the check for owed migrations, and carries one only if the check names it.
- **Left open:**
  - **The one fault the first calibration's outside judge blocked on that judges design.** DEC-042 point 2 gives it to a rule. Neither DEC-042 nor the repository the capability is authored in says which defect it was, so this record places none. Whoever maintains the capability names it, and a refinement of this record gives it to the rule that names it, with *below competent*. A calibration does not wait for it: its outside judge ranks by the rules the bar covers (DEC-042 point 9), and never by measures of its own.
  - **Whether a page with a fault that cites no rule may meet a bar.** The verdict reads grades alone. It stays DEC-042's question, decided by a refinement of that record.
  - **A change to a check whose output the review reads.** DEC-042 point 9 lapses the hold on anything that could move the grades, but the command compares only what that point's list names, and the list names no check. So until [project-kit#3296](https://github.com/aleskalfas/project-kit/issues/3296)'s refinement adds the checks the review reads to that list, the command does not see a change to one of them, and the verdict goes on ending loops.
