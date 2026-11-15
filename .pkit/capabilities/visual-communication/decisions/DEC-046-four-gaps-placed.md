---
id: DEC-046
title: Typography gains a rule in GRAPHIC, and craft, legibility and colour are left to the reviewer's reading and to checks
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the review of a piece was tested once against a designer's ranking. The test found four things the rules judge weakly or not at all. This record says where each belongs.
- **Typography,** how a text of several lines is set, gains a new rule, since nothing judges it today.
- **Craft,** whether parts line up, stand clear of each other and meet where they join, gains no rule. The reviewer's list of defects and the rule on grouping judge it already. The reviewer is told to read them more exactly, and a new automatic check finds boxes that overlap.
- **Legibility at the medium's size,** whether a text is large enough where the piece is shown, is left wholly to an automatic check. The rule on readability keeps what no check can see.
- **Colour** gains no rule. The rule on form judges it already, and the rest is a brand's look or a matter of taste.

The new rule lands in a later change, which gives the rule set a new major version.

## Context

[visual-communication:DEC-042-grades-bar-and-loop] point 2 has a refinement of the record of the principles ([visual-communication:DEC-028-principles-of-visual-communication]) decide where each gap belongs. This record is that refinement.

The words it uses:
- **The canon** is the published, established works of the field, which each rule is taken from (DEC-028 point 1).
- **The review** is what the capability's reviewer agent does: it reads the images of a piece's pages and reports. Its *body* is the file of instructions it works by.
- **A check** is a measurement a command makes on every render, with no judgement.
- **A fault** is one of eight defects the reviewer's body lists, such as an overlap. It is a drawing that does not show what the content says it should, and never a judgement of design ([visual-communication:DEC-030-design-agents] point 6).
- **A grade** is one of four words the review gives each rule on each page, from *below competent* to *excellent* (DEC-042 point 1).
- **A bar** is a project's setting that names rules and the grade each page must reach on them (DEC-042 point 3).
- **The hold** is the switch by which meeting the bar ends the designer's work on a piece. It needs an accepted *calibration*, a test of the review against a designer's ranking of a series of designs (DEC-042 point 9).
- **The reading** is how the reviewer interprets a rule or a fault. It lies in the reviewer's body, or in the *design knowledge*, the folder that teaches what the field's practice is (DEC-030 point 8).
- **A brand** is the library that holds a piece's look as values: its typefaces, sizes, colours and spaces.
- **The frames** are the file beside each image that gives every drawn part's box, in pixels.
- **A mode** is one variant a piece is drawn in, such as light or dark. Each image shows one mode.
- **A major** is the first number of a rule set's version. A project's set that takes rules from another names that set's major, as in `GRAPHIC@1`. That is its *pin* (COR-051 point 7).

What judges each gap today:
- **Craft.** `RS-GRAPHIC-002` asks that what belongs together is "placed together and lined up". The reviewer's fault 7, alignment, covers parts that "plainly belong on one edge, one line or one even spacing" and do not lie there. Fault 6 covers overlaps, and fault 1 a part cut off. So craft is named, and the calibration still found it weak.
- **Typography.** No rule and no fault judges how long a text's lines are, how far apart they stand, or how they break. The design knowledge's topic on type teaches it, and nothing is graded on it.
- **Legibility at the medium's size.** `RS-GRAPHIC-005` asks that everything "can be read where the piece is shown". DEC-028 point 10 gives the smallest text size for a medium to a check, which was never built (DEC-042 point 2). The review graded the rule by how much a page holds.
- **Colour.** `RS-GRAPHIC-007` asks that every difference a reader takes for meaning is one the content has. DEC-028 point 11 gives "five unrelated hues on one chain" as a break of it. Contrast is a check's.

## Decision

**`GRAPHIC` gains one rule, on how running text is set. Craft, legibility at the medium's size and colour gain none: rules, faults and checks name them already, and this record corrects how they are read and adds one check. No rule lands in this record's change. A later change adds the rule, in the words of point 3, and with it `GRAPHIC` becomes `GRAPHIC@2`.**

### 1. How a gap is placed

DEC-042 point 2 gives four places. This record takes them in this order for each gap:
- **The reading,** where a rule or a fault already names the gap. A second rule on the same test would make one defect fail twice.
- **A check,** for each part that needs no judgement (DEC-028 point 1).
- **A brand's values,** where the part is the look.
- **A rule of the canon,** only for what is left: a test that no rule, fault or check makes, which a source of the field states.

### 2. Craft is the faults' and `RS-GRAPHIC-002`'s, read more exactly, with a check for overlap

Craft gains no rule. Each part of it has a home already, and this record found nothing left over that a rule could judge.

- **Fault 7, alignment, is read from the frames on every page.** The reviewer compares the edges of the parts one list, row or column holds, and the gaps between them, by their boxes. It does not judge them by eye. An offset larger than a pixel of rounding is the fault.
- **Fault 6, overlaps, also covers a join that misses.** A line or an arrow that stops short of the part the content joins it to, or runs past it, is this fault.
- **`RS-GRAPHIC-002`'s "lined up" keeps the judgement of design.** The rule judges whether parts that belong together were given a shared edge at all. Fault 7 judges whether parts that were given one lie on it.
- **One finding, and one grade.** An offset between parts that belong together is one finding, a fault, which cites `RS-GRAPHIC-002` too (DEC-030 point 6). The page's grade on that rule counts the offset as its evidence. Where the grade falls below professional, its finding names the fault and describes the defect no second time. So a bar over `GRAPHIC` sees misalignment through that rule's grade.
- **A check for what needs no judgement.** It reports two boxes in one container that overlap, where neither holds the other. It leaves out lines and arrows, whose crossings stay fault 6's. It asks for attention and never fails, since a library's component may place one part on another on purpose, such as a badge on a corner. The work that builds it settles how a component says an overlap is meant, so that such an overlap is not reported for ever. Where that adds a field, it drafts the record first (COR-065 point 3).
- **Beside the check.** Once the check exists, an overlap of boxes is the check's. The reviewer names it in one line and judges it no second time (DEC-030 point 7).
- **Not a brand's value.** A brand sets the unit and the steps of space ([visual-communication:DEC-004-brands-and-notations]). Where parts lie is the piece's and its components'.

### 3. Typography gains a rule

**`RS-GRAPHIC-008`, running text is set to be read.** *Running text* is a text of more than one line. The rule's statement, in the words `graphic.md` would hold:

> ## RS-GRAPHIC-008 — Running text is set to be read
>
> A text that runs over several lines is set so that a reader keeps their place. Its lines are neither too long nor too short for its size. The space between its lines suits their length. Its uneven edge is even enough: no line but the last ends far short of the others.
>
> - **What it does not judge.** A text of one line, such as a title or a label. A text whose lines the content breaks, such as code. A text that only stands for text, such as the lines of a mock-up, and what lies inside a picture made elsewhere. Which text ranks first, which is `RS-GRAPHIC-001`'s. Whether a kind of text keeps one look, which is `RS-GRAPHIC-004`'s. Whether a text can be read at all where it is shown, which is `RS-GRAPHIC-005`'s. Whether a text is large enough for its medium, which is a check's.
> - **From the text:** nothing, since a line's length and its spacing show only once the page is drawn.
> - **On the drawn page:** the whole rule, on each image, so in each language and at each size the piece is drawn in.

The source of each clause:
- **Line length.** Robert Bringhurst: "Choose a comfortable measure". The *measure* is the length of a line, which he counts in characters, and he gives a range that reads well for one column of text (*The Elements of Typographic Style*). Matthew Butterick gives a range of characters to a line too, and asks a writer to keep within it (*Practical Typography*).
- **Line spacing.** Bringhurst: "Choose a basic leading that suits the typeface, text and measure". *Leading* is the space between lines, and a longer line needs more of it, so that the eye finds the start of the next line. Butterick gives line spacing as a share of the type size.
- **The uneven edge.** A text set flush on one side has an uneven edge on the other, which typographers call the *rag*. Ellen Lupton asks that it look evenly uneven, with no line much longer or shorter than the others (*Thinking with Type*).
- **On each size.** Tim Brown: on a screen, size, line length and line spacing are relations that change together as the reading conditions change (*Flexible Typesetting*). So the rule is judged on each size the piece is drawn at.

What the rule leaves to others, and how it is read:
- **No figure.** The rule names no number of characters and no share of the size. The sources' ranges differ, and each is given for its own script and medium. The design knowledge says what each source teaches. A project that wants a limit adds it in a set of its own (DEC-028 point 1).
- **A brand's values.** A brand's text style already holds its size and its line spacing (`lineHeight`). They are the look. Where the line spacing does not suit the lines a piece draws, the finding's fix belongs to the brand.
- **Who can mend it.** A line's length follows from the width a layout or a component gives the text. So the fix belongs to the piece, where it can choose another layout or cut the text, or else to a component or a library. The engine breaks lines by filling each one, and never hyphenates. Where only another way of breaking would even the edge, the grade is a *need*, a tool the engine lacks (DEC-042 point 4).
- **Languages.** Each language is judged on its own images, so a break that is bad in one translation is found there alone. Long compound words, as in German, make an edge rough in a narrow column, which is the rule's to find. Where a text is in a script none of the rule's sources speaks of, such as one written without spaces, the review gives line length no grade there and says so.
- **Little or nothing to judge.** A deck of short bullets, a diagram with labels only and a board people fill in hold no running text. The rule takes no grade on such a page, and the review says so (DEC-042 point 1).
- **A grade on each page.** The rule judges pages one at a time.
- **No "from the text" part.** Content sets no size and no spacing. A component does, and a text names a brand's style for its kind. So the text alone shows nothing of this rule.
- **No check and no new brand value.** A longest line a brand allows would be a limit, which is a project's taste or a check's threshold, and never a value a piece draws with (DEC-028 point 1; DEC-030 point 8).

### 4. Whether a text is large enough is the check's, and `RS-GRAPHIC-005` keeps what no check sees

Legibility gains no rule. The canon names it already, and DEC-028 point 10 already divides it: the smallest text size for a medium is a check's, and the rest is the rule's.

- **Size is wholly the check's.** The review never judges whether a text is large enough for its medium. It cannot: the viewing step enlarges a page until its smallest text is at least 10 pixels, so the image is built so that the text reads. The reviewer runs no command, and a piece's `shown` field holds words, not a size.
- **What the rule's first sentence still judges,** on the drawn page: what makes a text hard to read at any size. Examples are a face too thin or too ornate for its use, a weight too light, and a text that fades over a picture or a busy ground. A text over a picture stays fault 4 first.
- **What its second sentence judges:** whether the page is taken in at a glance. How much a page holds is evidence for this sentence only.
- **One grade, and the finding names the sentence** it rests on.
- **No small text fails twice.** Once the check exists, a text under its medium's minimum fails the check alone. It lowers no grade of `RS-GRAPHIC-005`, and the reviewer names it in one line.
- **Until the check exists,** nothing judges a text's size, and the review's report says so.
- **The check itself stays DEC-042's work.** DEC-042's Implications list it. This record adds only that the reading leaves size to it.

### 5. Colour gains no rule

Each part of the gap has a home, or no source states it as a test.

- **Whether the colours match what the content has is `RS-GRAPHIC-007`'s.** That covers hues with no kinds behind them, and an order shown by unrelated hues. The reviewer's body tells the review to count the hues a page draws against the kinds its content names.
- **Where the strong colour sits is `RS-GRAPHIC-001`'s and `RS-GRAPHIC-007`'s.** The first ranks what is seen first, by colour among other means. The second allows emphasis only where the page's point needs it.
- **Strong colour used sparingly, over muted large areas, is a note of taste.** Edward Tufte, after the map-maker Eduard Imhof, teaches it for maps and charts (*Envisioning Information*). A brand may fill a title page with its strongest colour, so it is no test every piece must pass. The design knowledge's topic on colour teaches it already, and a note names it (DEC-030 point 6).
- **Whether a palette's colours go together is the brand's.** A palette is a brand's look, and its author answers for it. No source states a test of it that a piece could fail.
- **Nothing is said of modes.** The review grades each image, and each image shows one mode. So each mode is judged already.
- **Contrast stays the checks'.**

### 6. The shape of the new rule

- **The shape DEC-028 gives.** `RS-GRAPHIC-008` judges every piece, as `GRAPHIC` does (DEC-028 point 3). It says apart what the text and the drawing show (DEC-028 point 4). It binds on nothing until a piece's content is an artefact (DEC-028 point 5).
- **Its sources are the canon's.** The designer who ranked the calibration's designs used measures of their own. No wording, figure or example of those measures enters the rule, a check or a reading this record places (DEC-042 point 2).
- **It names no grade.** A rule's text names a grade only where a break of it blocks a bar (DEC-042 points 1 and 2). No source calls a break of this rule unworkable.
- **Its origin is this record,** and it anchors to point 3.

## Rationale

**Why typography alone gains a rule.** A rule duplicates nothing only where no rule, fault or check makes its test. Line length, line spacing and the uneven edge have no home today, and three sources state them as tests. Without a rule the review gives them no grade, so no bar can ask for them.

**Why craft gains none.** An edge out of line is fault 7 and `RS-GRAPHIC-002`. An overlap, and a line that misses its end, are fault 6. A part cut off is fault 1. A rule on craft would give one misaligned edge three findings. The calibration found craft weak while these existed, so what failed was the reading: the review judged alignment by eye, though the frames give each box.

**Why a fault still moves a grade.** A bar reads grades alone (DEC-042 point 1). If an offset between grouped parts left `RS-GRAPHIC-002`'s grade as it was, no bar would see it. One finding that cites the rule, and one grade that counts it, keeps "one observation, one finding" (DEC-030 point 6).

**What this costs.** An overlap, or a line that misses its end, breaks no rule, so no grade shows it and a bar's verdict does not read it. The designer mends every fault whatever the bar (DEC-030 point 2). Whether a page with an open fault may meet a bar is DEC-042's question, left open below.

**Why the size of a text is wholly the check's.** A judgement the reviewer's images cannot support would repeat the calibration's failure. A minimum size by medium needs no judgement, so it is a check's (DEC-028 points 1 and 10).

**Why colour gains none.** The record's first draft gave colour a rule on "one scheme". Its example, five hues that read as no scheme, is DEC-028's own example of a break of `RS-GRAPHIC-007`. A rule on muted grounds would fail a brand's full-colour title page. A rule on how many hues a page draws would fail a diagram whose eight concepts each keep their colour, as `RS-GRAPHIC-004` asks.

**Why the rule's statement is in this record.** Accepting this record accepts the rule's words, so the maintainer reads them here. The later change that adds the rule to `graphic.md` shows it again in the list of what that change makes accepted (COR-066 point 3). Other words there would need a refinement of this record.

**Why no rule lands in this change.** A new rule makes a new major (COR-051 point 7), which every project that pins `GRAPHIC@1` must answer. That belongs with the reviewer's body and the design knowledge that read the rule, in a change that declares it.

### Alternatives considered

- **A rule on craft.** Rejected, as above. Its trigger to revisit: a craft defect found that no fault and no rule names.
- **Widening `RS-GRAPHIC-002`'s text.** Not needed: its words already say "lined up".
- **A rule on colour as one scheme.** Rejected, as above.
- **"Strong colour sparingly" as a clause of `RS-GRAPHIC-001` or `RS-GRAPHIC-003`.** Rejected: its source teaches it for maps and charts, and a brand may want the opposite.
- **The review judging text size from an image scaled to the medium.** Rejected: no piece declares a size or a viewing distance, and the reviewer runs no command.
- **`RS-GRAPHIC-005` split in two rules,** one for each sentence. Not taken: with size left to the check, both sentences rest on one reading of the page. Its trigger to revisit: the review still grades the rule by how much a page holds.
- **A brand's longest line, with a check.** Rejected, as point 3 says.
- **A clause on a lone last word, and one on a heading parted from its text.** Dropped. For the first, this record found no source that states the test for every language. For the second, the engine flows no text from page to page, and nearness is `RS-GRAPHIC-002`'s.
- **An overlap check that fails unless accepted,** as a loss is accepted in a piece. Rejected: an overlap a library's component means would need accepting in every piece that uses it.
- **The rule landed in this change.** Rejected, as above.

## Implications

- **No rule lands in this change, and no surface moves.** Its changeset is `none`. It owes no migration (COR-010).
- **Edits to DEC-028,** made in this change once this record is accepted (COR-066 point 5). Each is worded to hold before and after the rule lands.
  - **Its summary,** "this record names its source". It gains that a later record names the source of a rule it adds (refinement per this record, point 6).
  - **Its Decision line,** the same sentence, the same way.
  - **Point 1,** "Each is taken from a source this record names". The same way.
  - **Point 8,** the bullet on `RS-GRAPHIC-002`. It gains that an offset between parts that belong together is read from the frames, as a fault that cites the rule, and that the rule keeps whether such parts were given a shared edge (refinement per this record, point 2).
  - **Point 10,** the bullet on `RS-GRAPHIC-005`. It gains that the review never judges a text's size, and that the rule's first sentence judges what no check sees, such as a face, a weight and a ground (refinement per this record, point 4).
  - **Its Rationale,** "Why the reasons live in a record": "The record gives each rule's id, title, sources and reason". It gains that a later record gives them for a rule it adds.
  - **Its Implications,** "Each rule cites this record as its origin". It gains that a rule a later record adds cites that record.
  - **Its Implications,** "Left to other records". The list gains that this record places the four gaps of the first calibration.
- **No edit to DEC-042 or DEC-030.** DEC-042 point 2 names this refinement, and its Implications list it as later work.
- **Later work under [project-kit#3148](https://github.com/aleskalfas/project-kit/issues/3148),** each in a change of its own. A calibration grades by the rules, the reviewer's body and the design knowledge as shipped (DEC-042 point 9). So it waits for the first three, and not for the checks, which move no grade.
  - **The rule.** It adds `RS-GRAPHIC-008` to `graphic.md` as point 3 words it, accepted, with this record as its origin. It anchors `RS-GRAPHIC-002`, `RS-GRAPHIC-005` and `RS-GRAPHIC-007` to points 2, 4 and 5. It rewords the set's opening sentence, which says DEC-028 names each source. The calibration waits for it.
  - **The reviewer's body.** Faults 6 and 7 as point 2 reads them. How a fault that cites a rule moves that rule's grade. The readings of `RS-GRAPHIC-005` and `RS-GRAPHIC-007` of points 4 and 5. How `RS-GRAPHIC-008` is read, by language and by page. This joins the reviewer's body DEC-042's Implications list. The calibration waits for it.
  - **The design knowledge.** The topic on type gains the uneven edge and what each source says of line length and line spacing, with Lupton and Butterick among its works. The topic on colour gains a question on strong colour over large areas. The calibration waits for it.
  - **The overlap check** of point 2, with its entry in the capability's list of checks. The calibration does not wait for it.
  - **The check for a text smaller than its medium allows** stays DEC-042's item. Its work must first give a piece's medium a form a command can read, since `shown` holds words, and name a standard for each medium. That is a record of its own. The calibration does not wait for it, and its report says that nothing judged text size.
  - **The calibration** DEC-042 point 9 describes, last.
- **What `GRAPHIC@2` brings,** in the change that lands the rule:
  - **Adopters' pins.** A project's set that takes rules from `GRAPHIC@1` fails validation until the project reads the new rule and moves its pin (COR-051 point 7). Until then no rule of `GRAPHIC` binds through that set.
  - **Bars.** A bar that names `GRAPHIC@1` fails the capability's check until the project names `GRAPHIC@2` (DEC-042 point 3).
  - **The hold.** A new major lapses a hold (DEC-042 point 9). No calibration is accepted yet, so none exists to lapse. Later, a bar that covers all of `GRAPHIC@2` gets the hold only once a calibration gives `RS-GRAPHIC-008` evidence of its own. A bar may name single rules meanwhile (DEC-042 points 3 and 10).
  - **Its changeset and migration.** That change declares the surface change in its changeset, and its release notes tell a project to read the rule and move its pin and its bar. No migration moves a pin or a bar, since the project's own review is what a pin waits for (COR-051 point 7). That change runs the check for owed migrations, and carries one only if the check names it.
- **Left open:**
  - **The one fault the first calibration's designer blocked on that judges design.** DEC-042 point 2 gives it to a rule. Neither DEC-042 nor the repository says which defect it was, so this record cannot place it. Whoever maintains the capability names it, and a refinement of this record gives it to the rule that names it, with *below competent*. The calibration does not wait: its new designer ranks by the rules the bar covers (DEC-042 point 9), and never by a measure of their own.
  - **Whether a page with an open fault may meet a bar.** The verdict reads grades alone. Whoever maintains the capability decides it, by a refinement of DEC-042.
  - **Whether `RS-GRAPHIC-005` is split,** if the review still grades it by how much a page holds.
