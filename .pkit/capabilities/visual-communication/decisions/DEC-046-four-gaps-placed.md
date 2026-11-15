---
id: DEC-046
title: Typography gains a rule in GRAPHIC, and craft, legibility and colour are left to the reviewer's reading and to checks
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the review of a piece was tested once against a designer's ranking. The test found four things the rules judge weakly or not at all. This record says where each belongs.
- **Typography,** how a paragraph is set, gains a new rule, since nothing judges it today.
- **Craft,** whether parts line up, stand clear of each other and meet where they join, gains no rule. The reviewer's list of defects and the rule on grouping judge it already. The reviewer is told to read them more exactly. Two new automatic checks find boxes that overlap and edges that nearly line up. A defect on that list now lowers the grade of the rule whose words name it.
- **Legibility at the medium's size,** whether a text is large enough where the piece is shown, is left wholly to an automatic check. That check is not built, and needs a record of its own first. Until it exists nothing judges a text's size, so this gap stays open through the next test of the review.
- **Colour** gains no rule. The rule on form judges it already, and the rest is a brand's look or a matter of taste.

The new rule lands in a later change, which gives the rule set a new major version.

## Context

[visual-communication:DEC-042-grades-bar-and-loop] point 2 has a refinement of the record of the principles ([visual-communication:DEC-028-principles-of-visual-communication]) decide where each gap belongs. This record is that refinement.

The words it uses:
- **The canon** is the published, established works of the field, which each rule is taken from (DEC-028 point 1).
- **The review** is what the capability's reviewer agent does: it reads the images of a piece's pages and reports. Its *body* is the file of instructions it works by.
- **A check** is a measurement a command makes on every render, with no judgement. A check's finding either *fails* or *asks for attention*, which means someone is expected to look.
- **A fault** is one of eight defects the reviewer's body lists, such as an overlap. It is a drawing that does not show what the content says it should, and never a judgement of design ([visual-communication:DEC-030-design-agents] point 6).
- **A grade** is one of four words the review gives each rule on each page: *below competent*, *competent*, *professional* and *excellent* (DEC-042 point 1). A grade below professional is reported as a finding on its rule.
- **A bar** is a project's setting that names rules and the grade each page must reach on them, professional or excellent (DEC-042 point 3).
- **The hold** is the switch by which meeting the bar ends the designer's work on a piece. It needs an accepted *calibration*, a test of the review against a designer's ranking of a series of designs (DEC-042 point 9).
- **The reading** is how the reviewer interprets a rule or a fault. It lies in the reviewer's body, or in the *design knowledge*, the folder that teaches what the field's practice is (DEC-030 point 8).
- **A brand** is the library that holds a piece's look as values: its typefaces, sizes, colours and spaces.
- **A typeface** is one design of letters, such as Helvetica.
- **A box** is the rectangle a drawn part takes on the page. **The frames** are the file beside each image that gives every drawn part's box, in pixels.
- **Siblings** are the parts one part holds directly, such as the items of one list or the cards of one row.
- **A mode** is one variant a piece is drawn in, such as light or dark. Each image shows one mode.
- **A major** is the first number of a rule set's version. A project's set that takes rules from another names that set's major, as in `GRAPHIC@1`. That is its *pin* (COR-051 point 7).

What judges each gap today:
- **Craft.** `RS-GRAPHIC-002` asks that what belongs together is "placed together and lined up", that "what is separate is set apart", and that steps "are joined in the order they are read". The reviewer's fault 7, alignment, covers parts that "plainly belong on one edge, one line or one even spacing" and do not lie there. Fault 6 covers overlaps, and fault 1 a part cut off. So craft is named, and the calibration still found it weak.
- **Typography.** No rule and no fault judges how long a text's lines are, how far apart they stand, or how they break. The design knowledge's topic on type teaches it, and nothing is graded on it.
- **Legibility at the medium's size.** `RS-GRAPHIC-005` asks that everything "can be read where the piece is shown". DEC-028 point 10 gives the smallest text size for a medium to a check, which was never built (DEC-042 point 2). The review graded the rule by how much a page holds.
- **Colour.** `RS-GRAPHIC-007` asks that every difference a reader takes for meaning is one the content has. DEC-028 point 11 gives "five unrelated hues on one chain" as a break of it. Contrast is a check's.

## Decision

**`GRAPHIC` gains one rule, on how running text is set. Craft, legibility at the medium's size and colour gain none: rules, faults and checks name them already. This record corrects how they are read, adds two checks, and has a fault lower the grade of the rule whose words name it. No rule lands in this record's change. A later change adds the rule, in the words of point 3, and with it `GRAPHIC` becomes `GRAPHIC@2`.**

### 1. How a gap is placed

DEC-042 point 2 gives four places. This record takes them in this order for each gap:
- **The reading,** where a rule or a fault already names the gap. A second rule on the same test would make one defect fail twice.
- **A check,** for each part that needs no judgement (DEC-028 point 1).
- **A brand's values,** where the part is the look.
- **A rule of the canon,** only for what is left: a test that no rule, fault or check makes, which a source of the field states.

### 2. Craft is the faults' and `RS-GRAPHIC-002`'s, read more exactly, with two checks

Craft gains no rule. Each part of it has a home already, and this record found nothing left over that a rule could judge.

How alignment is read:
- **Fault 7 is an offset on the line the parts were given.** Siblings may share one of six lines: their left edges, their right edges, their tops, their bottoms, or their centres across or down. They are aligned where they share one. The fault is where they share none and nearly share one.
- **Parts that differ on purpose are no fault.** Cards centred in a row have different tops and bottoms and one centre line. Items of different widths in a centred column have different left and right edges and one centre line. Each shares a line, so each is aligned.
- **Even spacing is read the same way.** Gaps between siblings that are equal are even. Gaps that nearly agree are the fault.
- **What a box does not show.** A text's box is not its letters as drawn, and an icon's box may hold empty space around its drawing. Two labels may stand on one line of writing with different boxes. An icon may look out of line while its box is in line. The reviewer judges these on the image, where the boxes cannot settle them.
- **`RS-GRAPHIC-002`'s "lined up" keeps the judgement of design.** The rule judges whether parts that belong together were given a shared line at all. Fault 7 judges whether parts that were given one lie on it.
- **Not a brand's value.** A brand sets the unit and the steps of space ([visual-communication:DEC-004-brands-and-notations]). Where parts lie is the piece's and its components'.

The two checks, which do the arithmetic:
- **Edges that nearly line up.** A check compares the boxes of siblings. It reports one of the six lines, or the gaps between the siblings, where the values nearly agree and do not: they differ by more than a pixel of rounding and by less than the brand's smallest step of space. A difference that small is no spacing a brand offers, so it was hardly chosen.
- **Boxes that overlap.** A check reports two siblings whose boxes overlap, where neither holds the other. It leaves out lines and arrows, whose crossings stay the reviewer's to find.
- **Both ask for attention and never fail.** The arithmetic needs no judgement, so it is a check's (DEC-028 point 1). Whether the result is a defect does need one. A library's component may place one part on another on purpose, such as a badge on a corner, and a box may differ from what is drawn in it.
- **The reviewer judges each place the checks name,** on the image, and says whether it is a fault or is meant. It does no sums over the frames once the checks exist. Until they exist it reads the offsets from the frames, as its body says today. A check that asks for attention has measured and has not judged, so this keeps "what a check measures stays the check's" (DEC-030 point 7).
- **An overlap that is meant.** The work that builds the checks settles how a component says an overlap is meant, so that it is not reported for ever. Where that adds a field, it drafts the record first (COR-065 point 3).

Fault 6:
- **It becomes "Overlaps and joins that miss".** It gains a line or an arrow that stops short of the part the content joins it to, or runs past it. The reviewer's body and the agent's description both take the new name.

A fault lowers the grade of the rule whose words name it:
- **When a fault cites a rule.** A fault cites a rule where the rule's words name the defect, and only there. The reviewer's body lists the pairs. For `GRAPHIC` they are these:
  - **Fault 7, alignment,** cites `RS-GRAPHIC-002`: "lined up".
  - **Fault 6, overlaps and joins that miss,** cites `RS-GRAPHIC-002`. A part over a part breaks "what is separate is set apart". A join that misses between steps breaks "joined in the order they are read". Where the overlap loses letters, it cites `RS-GRAPHIC-005` too.
  - **Fault 4, a text that does not read over a picture,** and **fault 3, text over text,** cite `RS-GRAPHIC-005`: "can be read".
  - **Fault 1, a part missing or blank,** cites `RS-GRAPHIC-005` where a text on the page is cut off, hidden or drawn so that it cannot be seen.
  - **Fault 2, a wrong font,** cites `RS-GRAPHIC-004` where a text looks unlike the others of its kind: "the same meaning looks the same".
  - **Fault 8, a drawing that disagrees with a passing check,** cites what the fault it shows would cite.
  - **No rule of `GRAPHIC` names** a part the page does not draw at all, a wrong picture, a typeface the brand does not give that role where every text of the kind looks alike, or a join that misses between parts that are not steps. These cite none.
  - **The other set, `COMM`,** is traced the same way by the work on the reviewer's body.
- **How far it moves the grade.** A page with an open fault that cites a rule takes a grade below professional on that rule. *Professional* is the work a professional designer hands over (DEC-042 point 1), and none hands over a page with such a defect. Which of the two lower grades it takes is a reading, as it is for any break a rule's text settles (DEC-042 point 1).
- **Why two runs grade alike.** A bar asks professional or excellent, so its verdict turns only on whether a grade is below professional. The same fault gives the same answer on every run, however small the offset. The checks name the same places on every run.
- **Two findings, and the defect described once.** The fault describes the defect. The finding that carries the rule's grade names the fault as its evidence, and does not describe the defect again. This refines "one observation, one finding" (DEC-030 point 6), which this record's Implications list as an edit.
- **A fault that cites no rule** moves no grade. The designer mends it as it mends any fault it judges right (DEC-030 point 2).

### 3. Typography gains a rule

**`RS-GRAPHIC-008`, running text is set to be read.** The rule's statement, in the words `graphic.md` would hold:

> ## RS-GRAPHIC-008 — Running text is set to be read
>
> Running text is text meant to be read continuously, line after line, such as a paragraph. It is set so that a reader keeps their place. Its lines are neither too long nor too short to read with ease, for its typeface, its size and the number of columns it stands in. The space between its lines suits their length. Where its lines share a straight edge on one side only, their other ends look pleasantly uneven: neither almost straight nor ragged, with no line much longer or shorter than the rest, and forming no regular shape, such as a wedge or a curve.
>
> - **What it does not judge.** A heading, a title, a label, a cell of a table and an item of a list, however many lines each takes. A text whose lines the content breaks, such as code. Placeholder lines that stand for text in a drawing of a screen, and what lies inside a picture made elsewhere. A text in a script written without spaces between words. The ends of the lines of a centred text. The gaps between the words of a text set with two straight edges. Which text ranks first, which is `RS-GRAPHIC-001`'s. Whether a kind of text keeps one look, which is `RS-GRAPHIC-004`'s. Whether a text can be read at all where it is shown, which is `RS-GRAPHIC-005`'s. Whether a text is large enough for its medium, which is a check's.
> - **From the text:** nothing, since a line's length and its spacing show only once the page is drawn.
> - **On the drawn page:** the whole rule, on each image, so in each language and at each size the piece is drawn in.

These words are the maintainer's to accept with this record.

The source of each clause:
- **Line length, from two sources.** Robert Bringhurst: "Choose a comfortable measure". The *measure* is the length of a line, counted in characters. His range: "Anything from 45 to 75 characters is widely regarded as a satisfactory length of line for a single-column page set in a serifed text face in a text size." For several columns he gives another: "For multiple column work, a better average is 40 to 50 characters" (*The Elements of Typographic Style*, section 2.1.2). Matthew Butterick: "Aim for an average line length of 45–90 characters, including spaces" (*Practical Typography*). His figure is an average over a text, not a limit for each line. So the rule names the typeface, the size and the number of columns, and judges a text's lines together.
- **Line spacing, from one source.** Bringhurst: "Choose a basic leading that suits the typeface, text and measure" (section 2.2.1). *Leading* is the space between lines. A longer line needs more of it, so that the eye finds the start of the next line.
- **The uneven line ends, from one source, not yet checked.** A text whose lines share one straight edge ends unevenly on the other side, which typographers call the *rag*. Ellen Lupton, as recalled from the book and not checked against it: "A good rag looks pleasantly uneven, with no lines that are excessively long or short, and with hyphenation kept to a minimum. A rag is considered 'bad' when it looks too even (or too uneven), or when it begins to form regular shapes, like wedges, moons, or diving boards" (*Thinking with Type*, Text, Alignment). **These words are checked against the book before this record is accepted.** Where hers differ, the clause takes hers.
  - **The rule takes her whole test:** pleasantly uneven, neither too even nor too uneven, no line much longer or shorter, and no regular shape.
  - **It leaves out her words on hyphenation.** The engine never hyphenates, so there is nothing to keep low.
- **On each size.** Tim Brown: on a screen, size, line length and line spacing are relations that change together as the reading conditions change (*Flexible Typesetting*). So the rule is judged on each size the piece is drawn at.

What the rule's words mean, and where they stop:
- **Running text is told by its kind,** never by how many lines it takes. It is what the content gives as a paragraph or as body text. Typographers use the term for exactly this, and the rule's sources speak of continuous reading.
- **Headings, labels, cells and list items are out.** No source of the rule speaks of them. A title on two short lines, a label that wraps, and a bullet on two lines break nothing here. A break in one that looks wrong is a note (DEC-030 point 6).
- **Centred text.** Both its sides are uneven, and Lupton's test is for a text with one straight edge. The clauses on line length and line spacing judge it. The clause on line ends does not.
- **Text with two straight edges,** which typographers call *justified*. It has no uneven ends, so that clause has nothing to judge. Its fault would be uneven gaps between words, which the rule does not judge. The engine sets a text from its start, its middle or its end, and never with two straight edges, so no piece draws one today.
- **A paragraph's last line** ends where the text ends, so the review does not count it among the line ends. This is this record's reading. Lupton's words make no such exception.
- **A script without spaces between words,** such as Chinese or Japanese. The sources count characters and words of scripts that part words by spaces. The rule's text leaves such a text out, so it takes no grade there, and the review says so (DEC-042 point 1).
- **Little or nothing to judge.** A deck of short bullets, a diagram with labels only and a board people fill in hold no running text. The rule takes no grade on such a page, and the review says so (DEC-042 point 1).
- **A grade on each page.** The rule judges pages one at a time.

What the rule leaves to others:
- **No figure.** The rule names no number of characters and no share of the size. The two ranges nearly agree. Each is given for one script, one kind of typeface and one medium, though, and a piece may be in none of them. The design knowledge says what each source teaches. A project that wants a limit adds it in a set of its own (DEC-028 point 1).
- **A brand's values.** A brand's text style already holds its size and its line spacing (`lineHeight`). They are the look. Butterick ties line spacing to the size of the type alone: "For most text, the optimal line spacing is between 120% and 145% of the point size". That is what a brand's style sets. Where it does not suit the lines a piece draws, the finding's fix belongs to the brand.
- **Who can mend it.** A line's length follows from the width a layout or a component gives the text. The designer may choose another width or layout, and may reword or cut any word that is not the asker's (DEC-042 point 7). So nearly every finding of this rule is the designer's to mend, in the piece, a component or a library.
- **Rarely a need.** A *need* marks a grade only where no fix the designer may make would raise it, and only a tool the engine lacks would (DEC-042 point 4). The engine breaks lines by filling each one. Another way of breaking is such a tool, yet a new width or a reworded line nearly always mends the same edge. So the review marks a need here only where it says why neither would.
- **Languages.** Each language is judged on its own images, so a break that is bad in one translation is found there alone. Long compound words, as in German, make line ends rough in a narrow column, which is the rule's to find.
- **No "from the text" part.** Content sets no size and no spacing. A component does, and a text names a brand's style for its kind. So the text alone shows nothing of this rule.
- **No check and no new brand value.** A longest line a brand allows would be a limit, which is a project's taste or a check's threshold, and never a value a piece draws with (DEC-028 point 1; DEC-030 point 8).

### 4. Whether a text is large enough is the check's, and `RS-GRAPHIC-005` keeps what no check sees

Legibility gains no rule. The canon names it already, and DEC-028 point 10 already divides it: the smallest text size for a medium is a check's, and the rest is the rule's.

- **Size is wholly the check's.** The review never judges whether a text is large enough for its medium. The frames give each text's box and the image's size, so the share of the page a text takes can be worked out. Working it out and comparing it with a minimum is arithmetic, which is a check's (DEC-028 point 1). The viewing step's report already marks a page too wide for its smallest text in this way.
- **What the rule's first sentence still judges,** on the drawn page: what makes a text hard to read at any size. Examples are a typeface too ornate for its use, letters whose strokes are too thin, and a text that fades into a picture or a busy background.
- **Faults count here too.** A text over a picture stays fault 4, text over text fault 3, and a text cut off or hidden fault 1. Each cites this rule and holds its grade below professional (point 2).
- **What its second sentence judges:** whether the page is taken in at a glance. How much a page holds is evidence for this sentence only.
- **One grade, and the finding names the sentence** it rests on.
- **No small text fails twice.** Once the check exists, a text under its medium's minimum fails the check alone. It lowers no grade of `RS-GRAPHIC-005`, and the reviewer names it in one line.
- **Until the check exists,** nothing judges a text's size, and the review's report says so. This gap stays open until then.
- **The check itself stays DEC-042's work.** DEC-042's Implications list it. This record adds only that the reading leaves size to it.

### 5. Colour gains no rule

Each part of the gap has a home, or no source states it as a test.

- **Whether the colours match what the content has is `RS-GRAPHIC-007`'s.** That covers hues with no kinds behind them, and an order shown by unrelated hues. The reviewer's body tells the review to count the hues a page draws against the kinds its content names.
- **Where the strong colour sits is `RS-GRAPHIC-001`'s and `RS-GRAPHIC-007`'s.** The first ranks what is seen first, by colour among other means. The second allows emphasis only where the page's point needs it.
- **Strong colour used sparingly, over muted large areas, is a note of taste.** Edward Tufte, after the map-maker Eduard Imhof, teaches it for the design of information, maps first (*Envisioning Information*). A brand may fill a title page with its strongest colour, so it is no test every piece must pass. The design knowledge's topic on colour teaches it already, and a note names it (DEC-030 point 6).
- **Whether a palette's colours go together is the brand's.** A palette is a brand's look, and its author answers for it. No source states a test of it that a piece could fail.
- **Nothing is said of modes.** The review grades each image, and each image shows one mode. So each mode is judged already.
- **Contrast stays the checks'.**

### 6. The shape of the new rule

- **The shape DEC-028 gives.** `RS-GRAPHIC-008` judges every piece, as `GRAPHIC` does (DEC-028 point 3). It says apart what the text and the drawing show (DEC-028 point 4). It binds on nothing until a piece's content is an artefact (DEC-028 point 5).
- **Its sources are the canon's.** The designer who ranked the calibration's designs used measures of their own. No wording, figure or example of those measures enters the rule, a check or a reading this record places (DEC-042 point 2).
- **It names no grade.** A rule's text names a grade only where a break of it blocks a bar (DEC-042 points 1 and 2). No source calls a break of this rule unworkable.
- **Its origin is this record.** The rule names point 3 as the point it rests on, so a later change to point 3 flags the rule to be read again.

## Rationale

**Why typography alone gains a rule.** A rule duplicates nothing only where no rule, fault or check makes its test. Line length, line spacing and the line ends have no home today. Two sources state the first as a test, and one each the second and the third. Without a rule the review gives them no grade, so no bar can ask for them.

**Why running text is told by its kind.** The first draft took every text of more than one line. That reached a title on two lines, a label that wraps and a bullet, which the sources do not speak of: Bringhurst's range is for a page of text, and Butterick's for body text. A rule that failed a two-line title for short lines would be the reviser's, not the canon's.

**Why craft gains none.** An edge out of line is fault 7 and `RS-GRAPHIC-002`. An overlap, and a join that misses, are fault 6 and the same rule. A part cut off is fault 1. A rule on craft would give one misaligned edge three findings. The calibration found craft weak while these existed, so what failed was the reading: the review judged alignment by eye, though the frames give each box.

**Why checks do the arithmetic.** Comparing the edges of every list on every page is sums over a file, which the reviewer does unevenly and a command does the same way each time. The checks leave the reviewer the part that is a judgement: whether the place they name is a defect.

**Why a fault moves a grade.** A bar reads grades alone (DEC-042 point 1). If an offset between grouped parts left `RS-GRAPHIC-002`'s grade as it was, no bar would see it. DEC-030 point 6 gives one observation one finding, a fault before a rule finding. DEC-042 point 1 makes each grade below professional a rule finding. Neither says what a fault does to a grade, so this record decides it, and lists the edit.

**Why the grade falls below professional, whatever the fault's size.** A scale of how far each fault lowers a grade would be a reading, and two runs would differ on it. One step that every fault takes gives two runs the same verdict.

**What this costs.** A fault that cites no rule moves no grade, so a bar's verdict does not read it. Those are the four kinds point 2 lists. The designer mends each fault it judges right (DEC-030 point 2). That is no guarantee: where the verdict ends the loop, the loop may end with such a fault open. Whether a page with one may meet a bar stays DEC-042's question. For craft the cost is small, since only a join between parts that are not steps cites no rule.

**Why the size of a text is wholly the check's.** A minimum size by medium needs no judgement, so it is a check's (DEC-028 points 1 and 10). A review that judged it too would fail one small text twice.

**Why colour gains none.** The record's first draft gave colour a rule on "one scheme". Its example, five hues that read as no scheme, is DEC-028's own example of a break of `RS-GRAPHIC-007`. A rule on muted grounds would fail a brand's full-colour title page. A rule on how many hues a page draws would fail a diagram whose eight concepts each keep their colour, as `RS-GRAPHIC-004` asks.

**Why the rule's statement is in this record.** Accepting this record accepts the rule's words, so the maintainer reads them here. The later change that adds the rule to `graphic.md` shows it again in the list of what that change makes accepted (COR-066 point 3). Other words there would need a refinement of this record.

**Why no rule lands in this change.** A new rule makes a new major (COR-051 point 7), which every project that pins `GRAPHIC@1` must answer. That belongs with the reviewer's body and the design knowledge that read the rule, in a change that declares it.

### Alternatives considered

- **A rule on craft.** Rejected, as above. Its trigger to revisit: a craft defect found that no fault and no rule names.
- **Widening `RS-GRAPHIC-002`'s text.** Not needed: its words already say "lined up", "set apart" and "joined".
- **The reviewer comparing every edge from the frames, with no check.** Rejected, as above.
- **A fault that cites a rule and leaves its grade alone.** Rejected: no bar would see the fault.
- **A rule on every text that wraps.** Rejected, as above. Its trigger to revisit: a calibration finds headings or list items that wrap badly, and a source states a test for them.
- **Half of Lupton's test,** only the lines much shorter than the rest. Not taken: the rule would state a test its source does not.
- **A clause on the gaps between words in a text with two straight edges.** Not taken: the engine draws no such text. Its trigger to revisit: the engine gains it.
- **A rule on colour as one scheme.** Rejected, as above.
- **"Strong colour sparingly" as a clause of `RS-GRAPHIC-001` or `RS-GRAPHIC-003`.** Rejected: a brand may want the opposite.
- **The review judging text size from an image scaled to the medium.** Rejected: no piece declares a size or a viewing distance, and the judgement is arithmetic.
- **`RS-GRAPHIC-005` split in two rules,** one for each sentence. Not taken: with size left to the check, both sentences rest on one reading of the page. Its trigger to revisit: the review still grades the rule by how much a page holds.
- **A brand's longest line, with a check.** Rejected, as point 3 says.
- **A clause on a lone last word, and one on a heading parted from its text.** Dropped. For the first, this record found no source that states the test for every language. For the second, the engine flows no text from page to page, and nearness is `RS-GRAPHIC-002`'s.
- **A check of boxes that fails unless accepted,** as a loss is accepted in a piece. Rejected: an overlap a library's component means would need accepting in every piece that uses it.
- **The rule landed in this change.** Rejected, as above.

## Implications

- **This change adds no rule and changes nothing a project could observe.** Its changeset, the file by which a change declares its effect on the next release, declares none. It owes no migration (COR-010).
- **Edits to DEC-028,** made in this change once this record is accepted (COR-066 point 5). Each is worded to hold before and after the rule lands.
  - **Its summary,** "this record names its source". It gains that a later record names the source of a rule it adds (refinement per this record, point 6).
  - **Its Decision line,** the same sentence, the same way.
  - **Point 1,** "Each is taken from a source this record names". The same way.
  - **Point 8,** the bullet on `RS-GRAPHIC-002`. It gains that a fault the rule's words name, such as an offset or an overlap, holds the rule's grade on that page below professional. It gains too that the rule keeps whether parts that belong together were given a shared line (refinement per this record, point 2).
  - **Point 10,** the bullet on `RS-GRAPHIC-005`. It gains that the review never judges a text's size, and that the rule's first sentence judges what no check sees, such as a typeface, the thickness of its strokes and a background (refinement per this record, point 4).
  - **Its Rationale,** "Why the reasons live in a record": "The record gives each rule's id, title, sources and reason". It gains that a later record gives them for a rule it adds.
  - **Its Implications,** "Each rule cites this record as its origin". It gains that a rule a later record adds cites that record.
  - **Its Implications,** "Left to other records". The list gains that this record places the four gaps of the first calibration.
- **An edit to DEC-030,** made the same way.
  - **Point 6,** "One observation, one finding". It gains that a fault cites a rule where the rule's words name the defect, that such a fault is evidence for that rule's grade, and that the grade's finding names the fault and does not describe the defect again (refinement per this record, point 2).
- **An edit to DEC-042,** made the same way.
  - **Point 1,** "A rule finding". It gains that a page with an open fault that cites a rule takes a grade below professional on that rule (refinement per this record, point 2).
- **Later work under [project-kit#3148](https://github.com/aleskalfas/project-kit/issues/3148),** each in a change of its own. A calibration grades by the rules, the reviewer's body and the design knowledge as shipped (DEC-042 point 9).
  - **The rule.** It adds `RS-GRAPHIC-008` to `graphic.md` as point 3 words it, accepted, with this record as its origin. It has `RS-GRAPHIC-002`, `RS-GRAPHIC-005` and `RS-GRAPHIC-007` name points 2, 4 and 5 among the points they rest on. It rewords the set's opening sentence, which says DEC-028 names each source. The calibration waits for it.
  - **The reviewer's body.** Fault 7 as point 2 reads it. Fault 6 under its new name, in the body and in the agent's description. The pairs of fault and rule, for `GRAPHIC` as point 2 lists them and for `COMM` traced the same way. The grade a fault holds a rule to. How the reviewer judges the places the two checks name. The readings of `RS-GRAPHIC-005` and `RS-GRAPHIC-007` of points 4 and 5. How `RS-GRAPHIC-008` is read. This joins the reviewer's body DEC-042's Implications list. The calibration waits for it.
  - **The design knowledge.** The topic on type gains the uneven line ends and what each source says of line length and line spacing, with Lupton and Butterick among its works. The topic on colour gains a question on strong colour over large areas. The calibration waits for it.
  - **The two checks of boxes** of point 2, each with its entry in the capability's list of checks. The calibration waits for them. The reviewer's body tells the review to judge the places they name, and a body changed after a calibration lapses the hold (DEC-042 point 9). The first calibration also found craft weak because this arithmetic was done by eye.
  - **The check for a text smaller than its medium allows** stays DEC-042's item. Its work must first give a piece's medium a form a command can read, since `shown` holds words, and name a standard for each medium. That is a record of its own. The calibration does not wait for it: the check moves no grade, and the hold reaches only rules a calibration tested (DEC-042 point 10). The calibration's report says that nothing judged text size.
  - **The calibration** DEC-042 point 9 describes, last.
- **What `GRAPHIC@2` brings,** in the change that lands the rule:
  - **Adopters' pins.** A project's set that takes rules from `GRAPHIC@1` fails validation until the project reads the new rule and moves its pin (COR-051 point 7). Until then no rule of `GRAPHIC` binds through that set.
  - **Bars.** A bar that names `GRAPHIC@1` fails the capability's check until the project names `GRAPHIC@2` (DEC-042 point 3).
  - **The hold.** A new major lapses a hold (DEC-042 point 9). No calibration is accepted yet, so none exists to lapse. Later, the hold reaches a bar only where a calibration tested every rule the bar names (DEC-042 point 10). So a bar that names all of `GRAPHIC@2` ends no designer's work until a calibration has tested `RS-GRAPHIC-008` too. A bar that names single rules, each one tested, gets the hold meanwhile.
  - **Its changeset and migration.** That change declares, in its changeset, that the set has a new major, and its release notes tell a project to read the rule and move its pin and its bar. No migration moves a pin or a bar, since the project's own review is what a pin waits for (COR-051 point 7). That change runs the check for owed migrations, and carries one only if the check names it.
- **Left open:**
  - **The one fault the first calibration's designer blocked on that judges design.** DEC-042 point 2 gives it to a rule. Neither DEC-042 nor the repository says which defect it was, so this record cannot place it. Whoever maintains the capability names it, and a refinement of this record gives it to the rule that names it, with *below competent*. The calibration does not wait: its new designer ranks by the rules the bar covers (DEC-042 point 9), and never by a measure of their own.
  - **Whether a page with an open fault that cites no rule may meet a bar.** The verdict reads grades alone. It stays DEC-042's question, decided by a refinement of that record.
  - **Lupton's words,** until they are checked against the book.
