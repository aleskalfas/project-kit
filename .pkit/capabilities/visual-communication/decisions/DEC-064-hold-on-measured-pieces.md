---
id: DEC-064
title: Where a check takes a defect from a rule's grades, the verdict ends a loop only on a piece that check measured
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the review of a piece is tested before its verdict may end the designer's loop. One check changes which pages the review is shown. Where the check of a text's size measured a piece, a text under its medium's minimum fails, and is mended before any review. Where it did not, a page with such a text reaches the review. Reading a text's size from an image is where the first test found the review weak. So a test on pages the check passed says nothing of pages it never measured.

- **The test runs on measured pages.** The check measures every image of its designs, and each design passes it.
- **The verdict ends a loop only on a round in that state.** Three things hold of such a round:
  - the check measured each image the review read, and found it clean;
  - the review read the piece as the check measured it;
  - the designer wrote none of the values the check measured against or took as given.
- **Elsewhere the verdict informs.** Where the command that gives the verdict cannot tell, it informs too.
- **Where a piece is shown is the asker's to say.** The designer never changes that statement to clear a finding without asking.
- **The checks of boxes do not narrow the hold.** They fail no page, so a place they name reaches the review either way.

## Context

The verdict ends the designer's loop only where an accepted calibration reaches ([visual-communication:DEC-042-grades-bar-and-loop] points 9 and 10). Five things the accepted records say bear on how far that is:

- **The hold's reach reads no piece.** It reaches any project whose bar covers only rules with their own evidence, while nothing lapses it (DEC-042 point 10). Every condition is the project's.
- **A calibration waits for each check the reviewer's body is written to read.** Otherwise the verdict would end loops "for a review that does not run as it was measured" ([visual-communication:DEC-046-faults-lower-grades] point 8).
- **A check that has landed has not measured every piece.** A check's silence counts only where it measured ([visual-communication:DEC-063-where-a-check-measures] point 3). The check of a text's size measures a piece only where the piece names its media ([visual-communication:DEC-055-smallest-text-size] point 9). Every piece written before that check names none.
- **No agent reaches a switch of the hold.** No agent reads the bar, which lies in configuration the project reviews (DEC-042 point 3). Only the change that records an accepted calibration writes the calibrated data (DEC-042 point 9).
- **The designer writes some of what a piece is drawn with.** It writes a piece's local components and a version not yet released of the project's own library. It never writes a released version ([visual-communication:DEC-030-design-agents] point 5). A piece's top may be a local component (the components' page, "Patterns, blocks and top components"). A brand of the project's own lies in the project's own library, so the designer may write one in a version not yet released.

What a check's not measuring does differs by check:

- **The check of a text's size.**
  - **Where it measured,** a text under its medium's minimum fails the check (DEC-055 point 6). The designer mends a check's failure before any review (DEC-042 point 6). The text is the check's finding alone, and lowers no grade of `RS-GRAPHIC-005` (DEC-046 point 5, "No small text fails twice").
  - **Where it did not,** a page with such a text reaches the review. The review judges a text's size only as far as the image shows that the text cannot be read (DEC-046 point 5).
  - **Either way, the review reads a page alike.** It judges whether the drawn text can be read where the piece is shown, and never a text's size against a minimum (DEC-046 point 5).
  - **What the first calibration found.** The review was weak at "legibility at the medium's size" (DEC-042, Context).
  - **The only check that takes a defect.** The accepted records name a text under its medium's minimum alone as a check's finding that lowers no grade ([visual-communication:DEC-062-checks-beside-the-frames], Implications, on DEC-030 point 7). A fault any other check reports holds its rule's grade. That takes in the check's two siblings, of contrast and of a text that overflows its box ([visual-communication:DEC-028-principles-of-visual-communication] point 1).
- **The two checks of boxes.** Their findings ask for the reviewer's attention and fail nothing (the list of checks, `near-alignment`). Where one did not measure a place of a kind it measures, the reviewer reads from the frames what that check measures (DEC-063 point 4). The defect holds its rule's grade either way (DEC-063 point 4, "The same grade either way").

The command that gives the verdict reads no check. It gives the hold to any bar within the accepted report. It names four reasons that the hold is off: no report accepted, a bar that reaches past it, a lapse, and accepted data it cannot read (the outputs page, "When it ends the loop").

Terms:

- The *hold*, a *bar*, a *calibration*, its *held-out ladder*, the *verdict* and the *asker* are DEC-042's terms.
- A check *measured* a place, its *reach* and its *statement* are DEC-063's terms.
- A piece's *media* are the media it names that it is shown in (DEC-055 point 1).
- A check *takes a defect from a rule's grades* where an accepted record decides that a defect the check finds lowers no grade of that rule.

## Decision

**Only a check that takes a defect from a rule's grades narrows the hold. The checks of boxes take none, and this record chooses, for its cost, not to narrow the hold by them. Under a bar that covers such a rule, the verdict ends a loop only on a round that check measured and found clean. The review read that round as the check measured it, and the designer wrote none of the values the check measured against or took as given. Where the command cannot tell, the verdict informs. A calibration's ladder is read the same way. Where a piece is shown is the asker's statement, which the designer changes only on the asker's word.**

### 1. Only a check that takes a defect from a rule's grades narrows the hold

- **Which checks.** A check narrows the hold where it takes a defect from the grades of a rule a bar covers. A check that takes none does not.
- **Why such a check.** Where it measured, a page with the defect fails the check and is mended before any review (DEC-042 point 6). A ladder's designs pass it too (point 3). So no calibration shows the review such a page. Where the check did not measure, such pages reach the review.
- **The first.** The check of a text's size, an example, takes a text under its medium's minimum from the grades of `RS-GRAPHIC-005` (DEC-046 point 5). Context says which checks take a defect.
- **The checks of boxes do not narrow the hold, by choice.** A defect at a place they name holds its rule's grade, as one the reviewer finds from the frames does (DEC-063 point 4). They fail no page, so such a place reaches the review whether or not they measured it. So they take no defect. Their not measuring still changes who sums the frames, and this record chooses not to narrow the hold by it. The Rationale gives the reason, which is cost.
- **A later check.** The record that has a check take a defect from a rule's grades names this point. It says two things of its check:
  - what a piece states that the check measures by;
  - which values the check measures against or takes as given, and which file declares each.

  Point 2 says what it is for a check to have measured an image, and no check's record says that again. DEC-055 points 1, 2, 3 and 10 are the first case.

### 2. The hold reaches a round only where each such check measured it clean, as the review read it

Take a project's bar that covers a rule a check takes a defect from. The verdict then ends the designer's loop on a piece only where all three of these hold of the round's review:

- **The check measured each image the review read, and found it clean.** The viewing step's report names the check for the image. It gives the image no finding of that check: neither a statement that the check could measure nothing, nor a defect (DEC-062 point 2 and DEC-063 point 3).
- **The review read each image as the check measured it.** It left out nothing the piece states that the check measures by. The review leaves a piece's media out where they disagree with its `shown` field (DEC-055 point 12), and the hold then does not reach that round.
- **The designer wrote none of the values the check measured against or took as given.** A value the check takes as given is one it reads as a fact of how the piece is shown, and compares with nothing. Where a file declares a value of either kind, that file lies in a released version of a library, which the piece's lock names. The designer never writes one (DEC-030 point 5). For the check of a text's size, the files are two. The piece's top declares the smallest sizes (DEC-055 point 2). The piece's brand, with each brand it builds on, gives the width a page is drawn at, which the check takes as the width the page is shown in (DEC-055 point 3). So a piece gets no hold where its top is a local component, or where its top or its brand lies in a version not yet released.

What follows from the three:

- **Elsewhere the verdict informs,** and the loop ends as DEC-030 point 2 says.
- **Where the command cannot tell, the verdict informs.** The command says so among its reasons that the hold is off. That holds wherever the data it would read is missing, cannot be read or is of another round. It holds under every such bar while the command reads no such data (point 6).
- **A bar that covers no such rule** is reached as DEC-042 point 10 says, with nothing added.
- **Read on each piece, at each round.** The hold's other conditions are the project's. This one is the piece's, at the round the verdict is given for. A piece gains it by naming its media, under a released top that declares each and a released brand. A round loses it where one of the three fails.
- **A round the hold does not reach ends the loop of DEC-042 point 6.** That loop runs only over rounds the hold reaches.
  - **At its first review.** Where the hold does not reach the first review, the loop ends as DEC-030 point 2 says.
  - **At a later round.** The designer stops there, and hands over as DEC-042 point 6 says. It says which of the three failed. That round is never "the last round whose verdict met the bar".
  - **A piece that gains the hold afterwards** starts a new loop, with no round and no stuck grade counted from the old one.

### 3. A calibration's ladder is read as point 2 reads a round

A calibration whose bar covers such a rule fixes this of its held-out ladder before it runs, as it fixes the rest (DEC-042 point 9):

- **All three conditions of point 2 hold of it.** They are read of every image of every design, and of the calibration's review:
  - each such check measured the image, and found it clean;
  - the review left out nothing the ladder states that the check measures by;
  - each value the check measured against or took as given lies in a released version of a library.
- **Why each design passes the check.** The designer mends a check's failure before a loop's review (DEC-042 point 6), and point 2 gives no hold to a round where one stayed. A ladder's designs are fixed, and nobody mends one. So each is drawn to pass, and the outside judge ranks the designs as they then stand.
- **Its report names what each such check measured by, and against.** An example is the ladder's media and the smallest size of each (DEC-055 points 1 and 2).
- **A ladder that cannot be read so.** A calibration then takes another ladder that can, leaves the rule out of its bar, or waits. An example is a ladder shown in a medium whose smallest size no top declares. The calibration takes a ladder shown in another medium.

### 4. Where a piece is shown is the asker's statement

This point holds wherever the designer mends a piece, under a bar or not, as DEC-042 point 7 does.

- **The asker's.** A piece's `shown` field and its media say where it is shown, and are the asker's statement. The designer writes them from what the asker says. It shows them to the asker as it shows the goals and relations (DEC-030 point 2).
- **Changed only on the asker's word.** A fix that would change either is asked of the person, as a fix that would change the asker's words is (DEC-042 point 7). The designer says what it recommends.
- **Naming media on a piece that names none is such a change.** The designer may recommend the media its `shown` field reads as. It writes them once the asker agrees.
- **At every level.** This holds at every level of the setting by which the core will decide how much agents decide without asking ([project-kit#2801](https://github.com/aleskalfas/project-kit/issues/2801)). The asker's words are kept so too (DEC-042 point 7).
- **What stays the designer's.** It changes alone what the piece is drawn with, such as a style, a brand of the project's own, or a size the piece is drawn at. Where the piece maps its media, a size it adds reaches a medium only once the asker says that medium shows it. A top or a brand it writes itself gets no hold (point 2).
- **Who the piece is for is not taken in.** The piece's `audience` field steers the review's grades (DEC-042 point 1). It decides none of point 2's conditions, and no check measures by it. Whose it is to change is left open (Implications).
- **Kept by the designer's own rule.** No command can tell whose word changed a field of the piece's file. The designer tells the person each change it made to either, as it tells every change (DEC-030 point 2). A breach also shows in the committed change to the piece's file, to whoever reads it.

### 5. What such a check measures against lapses no hold

- **The values are not compared.** A value such a check measures against, such as a top's smallest size, is not compared with the accepted data, and lapses nothing.
- **A value decides which pages reach the review, as having no value does.** The two differ by degree, and by who sets the value:
  - **By degree.** With no value, a text of any size reaches the review. With a poor value, only a text between that value and a better one does.
  - **By who sets it.** The designer wrote no value the hold rests on (point 2). A released version passed its owner's check when it was released ([visual-communication:DEC-003-change-over-time] point 6). A shipped top's value names its source beside it (DEC-055 point 8).
- **The check's code, its reach and its statements** lapse the hold as every check's do (DEC-062, Implications, "What lapses the hold").
- **What the narrowing does not guard against.** It guards against no comparison at all, and a value the designer wrote. It guards too against a review that read the piece otherwise than the check measured it. Five cases still get the hold:
  - a piece measured against a poor value of a released top, such as one of the project's own library, or under a released brand that draws its pages wider than the windows that show them;
  - a piece moved to another released top, which declares less;
  - a piece whose `shown` field and media agree, and are both wrong;
  - a piece whose `shown` field and media disagree, where the review missed it. Whether they disagree is the reviewer's reading of words. The review then reads by the media, and nobody judges a place only `shown` names;
  - a piece shown in a room farther than a room's value assumes (DEC-055 point 8).

  Whether a text can be read where the piece is shown stays the review's to grade in each.

### 6. The command comes to tell from data a later record decides

- **With the first such check, a reason and no data.** The change that lands a check that narrows the hold gives the command its reason of point 2. Until the command can tell, that reason holds under every bar that covers the check's rule.
- **Then the command comes to tell.** A follow-up has it read whether the three conditions of point 2 hold of the round ([project-kit#3372](https://github.com/aleskalfas/project-kit/issues/3372)). The reason then holds only where one fails, or where the command cannot tell.
- **What the data must be.** Three things bind whichever source the follow-up takes:
  - **Of the round.** It describes the images that round's review read, and the lock they were drawn under. A file a later look replaces does not, once it is replaced.
  - **Given again.** Anyone gives the verdict again from the same report (DEC-042 point 1), so the data stays with the round.
  - **Not the designer's to compose.** The designer writes none of its content. The review's report, kept as the reviewer wrote it (DEC-042 point 4), is not the designer's, whoever's session keeps the file. Nor is a file a command writes (DEC-030 point 5).
- **A record decides the source,** as a refinement of this point. Two candidates stand:
  - **The round's kept report carries it.** The reviewer replies with its report, and whoever dispatched it keeps the report as written (the outputs page, "Where the review's reports are kept").
  - **The command reads a copy of the viewing step's report.** The look command would keep that copy for the round. No check reads that report today (DEC-062 point 3).
- **The review's line is data either way.** Whether the review left out what a piece states that a check measures by is the review's own to say. A command reads it only as a field of the report's fixed form.
- **The order, for economy.** The reason keeps the command safe in any order, and this point decides no wait. But a follow-up that lands after a calibration forces a new one:
  - the field changes the reviewer's definition, whose digest lapses the hold (DEC-042 point 9);
  - a kept copy changes the viewing step's code, which lapses the hold once the command compares it (DEC-062, Implications, "What lapses the hold").

  So the later work settles the source, and lands the report's field, before a calibration runs (Implications).

## Rationale

**Why the hold reaches only a piece measured so.** The verdict ends loops by what a calibration measured (DEC-042 points 9 and 10). A calibration shows the review only pages the check passed (point 3). On a piece that names no medium, a page with a text under its minimum reaches the review. The review says of that text only what the image shows (DEC-046 point 5). That reading is where the first calibration found the review weak (DEC-042, Context). The verdict would end a loop there for a review that does not run as it was measured (DEC-046 point 8).

- **It fails safe.** A verdict that informs is safe, as a lapse is (DEC-042 point 9).
- **What a project does.** A project that wants the verdict to end its loops says where its pieces are shown.

**Why a check that takes a defect, and not every check the reviewer reads.** The two kinds of check differ in what their not measuring changes:

- **A check that takes a defect changes which pages reach the review.** Measured, a page with the defect fails and is mended, so the review never meets it. Unmeasured, the review meets it. How the review reads a page is the same in both states (Context). So a calibration gives no evidence of the review on the pages only the unmeasured state shows it.
- **A check of boxes changes who sums the frames.** Its findings fail nothing, so a near miss reaches the review measured or not. A calibration therefore shows the review such pages. Unmeasured, the reviewer sums the frames itself, and the defect lowers the same grade (DEC-063 point 4).
- **That difference is real.** Who does the arithmetic is what failed at the first calibration (DEC-046, "Why craft gains none" and "Why checks do the arithmetic"). A calibration measured by the checks of boxes does not test the reviewer's own sums.
- **The term is the reason for point 3.** Each design of a ladder must pass a check only where the check's finding lowers no grade ("Why each design of the ladder passes the check").
- **What the term misses.** A check could fail a page, keep its defect's grade, and measure only a piece that opts in. Its unmeasured pieces would show the review pages no calibration did. Point 1 would not narrow the hold for it. The Implications name it as a case to revisit.

**Why the checks of boxes do not narrow the hold.** The reason is cost and rarity, and not that nothing is lost:

- **Their unmeasured state is rare.** A check of boxes measures every piece, but for a key whose brand gives no step of space, or a scene its code stopped on. The check of a text's size measures no piece until the piece names its media.
- **Today the cost is a second rule with no hold.** The command reads no check's statements until the follow-up. Until then, narrowing by them would take the hold from every bar over `RS-GRAPHIC-002`, on every piece.
- **After the follow-up the cost is small,** since rarity makes narrowing cheap too. The record that settles the follow-up's source weighs it then (Implications).

**Why one root is named.** Four things follow from a check whose finding lowers no grade:

- each design of a ladder must pass it;
- the hold narrows by piece;
- a finding stands where a statement also covers its place (DEC-055 point 12);
- a round where the check's finding stayed gets no hold.

A later consequence of that choice of DEC-046 point 5 is recognised as one by the term this record defines.

**Why a record of its own.** The rule reaches every check that takes a defect from a rule's grades, whichever record decides the check. Two pieces of work look for it under the hold. One has the command compare the checks the review reads, and the other has it tell whether a check measured. Neither would look in the record of one check's sizes and media.

**Why measured and clean.** A text under its minimum lowers no grade, and the command reads grades alone (DEC-042 point 1). The designer mends a check's failure before any review, but that is its procedure, and no fact of every round. Two of the check's fixes change where the piece is shown, and wait on the asker (point 4). So a page the check fails can stand at a review. The verdict could then meet the bar on it. DEC-042 point 6 would hand over that round as the last that met the bar, and it would fail validation.

**Why the designer wrote none of the values.** DEC-042 keeps every switch of the hold from an agent. The designer may write a piece's top, as a local component or in a version not yet released (DEC-030 point 5). A top that declares a tiny smallest size passes every run. The check then measured the piece and found it clean, and `shown` and the media still agree.

- **A value the check takes as given serves as well.** On a screen at hand the check compares a fixed length with a text's size at the width the brand gives the page (DEC-055 point 3). The designer may write a brand of the project's own, in a version not yet released. A brand that draws its pages wider, with its type scaled by as much, passes texts that shrink below the smallest size in the window that shows them. The check again measured the piece and found it clean.
- **Nothing else would stop it.** A change to the media alone makes `shown` disagree, and the review then leaves the media out. A change to a value shows nowhere.
- **A released version is the test a command can make.** The designer never writes one, of a brand as of a top, and the piece's lock names the version (DEC-030 point 5).
- **What it costs.** A piece under a top or a brand the project is still drafting gets no hold until that version is released.

**Why the review must have read the piece as the check measured it.** Take a deck whose `shown` says it is projected, and whose media name a screen at hand alone. The check measures every run against the screen, and states nothing. The review leaves the media out, and judges the room as far as the image shows (DEC-055 point 12). That is the unmeasured state, on a piece every image of which the check measured.

**Why a round the hold does not reach ends the loop.** DEC-042 point 6 assumes a hold that stays through a run. Read at each round, it can go: the review finds that `shown` and the media disagree, a check's finding waits on the asker, or the asker changes where the piece is shown.

- **Each cause needs the person,** so the loop would wait on a question either way.
- **It fails safe.** A round the verdict did not govern is never handed over as one that met the bar.
- **Going on would need more rules.** A loop that paused and resumed would count rounds and stuck grades across rounds no verdict governed.

**Why the command informs wherever it cannot tell.** The reason needs no data: the bar covers the rule, and the command cannot tell. So the hold is narrowed from the day the check lands, and no order of later work has to keep it. Once the command reads its data, the same sentence covers data that is missing or of another round. So the accepted text needs no second edit when the follow-up lands.

**Why each design of the ladder passes the check.** On a measured piece, a text under its minimum lowers no grade, and the verdict reads grades alone (DEC-042 point 1). The outside judge ranks by the rules the bar covers, and would rank such a design down. The review could not. So the conditions of DEC-042 point 9 could fail for no fault of the review.

**Why where a piece is shown is the asker's.** A piece's media lie in its own file, which the designer writes (DEC-030 point 5). Changing them changes what the check measures, what the review reads and whether the hold is on. So the designer could clear a failing check, and gain the hold, by saying the piece is shown elsewhere.

- **It is the asker's in fact.** Where a piece is shown is known to whoever asked for it, as its intent is (DEC-030 point 2).
- **`shown` beside the media.** Whether the two agree is a condition of the hold (point 2), and the review judges by `shown` where they do not (DEC-055 point 12). A designer free to change `shown` alone could make them agree, and steer the review.
- **Why naming media on an old piece is asked.** It is the act that gains the hold on every piece written before the check.
- **Why at every level.** A setting that lets agents decide more must not let the designer switch the hold its own loop ends by.
- **Why the audience is left out.** Nothing in point 2 reads it, so it switches no hold. It does steer the grades. Taking it in would widen DEC-042 point 7 past what this record's reason carries.

**Why no command holds it, where DEC-042 holds its other switches by where they lie.** The bar lies in configuration the project reviews, and one change alone writes the calibrated data. This switch lies in the piece's file, which is the designer's to write, and a first draft needs the field written. So it alone is kept by the designer's own rule. The asker's words are kept that way (DEC-042 point 7), but they switch no hold, so this departs from DEC-042's standard for switches. The committed change to the piece's file shows a breach, which is more than the designer telling on itself.

**Why the values such a check measures against lapse no hold.** DEC-042 point 9 lapses the hold on what could move the grades, compared with the accepted data.

- **No accepted data could hold the values.** They are each top's by design, a project's own top among them.
- **A poor value is a lesser case of no value.** Both let pages reach the review that a calibration did not show it. Point 5 says how they differ. Point 2 closes the case where the designer sets the value.
- **What this leaves to the review.** A poor value in a released top or brand still gets the hold. Whether a text can be read where the piece is shown is graded all the same.

### What it costs

- **A narrower hold,** for a bar that covers `RS-GRAPHIC-005`. The verdict ends no loop on a round where any of these holds:
  - the piece names no medium, or its top declares no smallest size for a medium it names;
  - the piece is drawn at a size no medium shows, or a share gives no smallest size on a page (DEC-055 point 10);
  - the review left the media out, or a finding of the check stayed;
  - the piece's top is a local component, or its top or its brand lies in a version not yet released.
- **No piece shown in a room, under a shipped top,** until a top declares a room's value. That waits on reading the standard (DEC-055 point 8). A room is a deck's usual medium.
- **No hold at all under such a bar, until the command can tell.** That takes in a bar over `GRAPHIC` whole, on every piece, from the check's landing to the follow-up's. The check the calibration waited for leaves its rule's hold waiting on one more piece of work.
- **A question to the asker** wherever a fix would change where the piece is shown, and before a piece that names no medium comes to name one.
- **A loop that ends early,** at a round the hold does not reach.
- **A guard no command keeps.** A designer that changes a piece's media against point 4 is found by the person it tells, or by whoever reads the change to the piece's file.
- **The reviewer's sums from the frames stay untested** by a calibration, where a check of boxes did not measure.

### Alternatives considered

- **The clause kept in the record of the check of a text's size, for that check alone.** Rejected: the reason reaches every check that takes a defect from a rule's grades. The work on the command would look for it under the hold ("Why a record of its own").
- **Every check the reviewer's body reads narrows the hold, the checks of boxes among them.** Not taken, for its cost today ("Why the checks of boxes do not narrow the hold"). It would guard the reviewer's own sums, which no calibration tests.
- **The checks of boxes narrowing the hold through their statement, from the follow-up on.** Not decided here. It costs nothing now and little then. The record that settles the follow-up's source weighs it, since that record decides what the command reads of a check (Implications).
- **The hold keyed on any check whose unmeasured state is common,** whatever it does to grades. Not taken: one check fits that today, and it also takes a defect. "Common" would need a measure that no record gives. The Implications name the check the term would miss.
- **The hold reaching every piece, with the gap named in the review's report.** Not taken. It edits nothing in DEC-042. But a loop would end by the verdict on a piece whose small texts nothing compared. Its evidence was gathered beside a check that compared them.
- **A calibration in each state,** with evidence for each. Rejected: two ladders and two sets of evidence for one rule, to let loops end where a piece does not say where it is shown.
- **The hold off for a whole project while any of its pieces is unmeasured.** Rejected: one old draft would end no loop on any piece, and a piece's state is read at its own round.
- **The command left as built, and its follow-up ordered before any calibration's report is accepted.** Not taken, though it spares the time in which no bar over the rule gets the hold. Only memory would keep that order, and a slip would end loops on pieces nothing measured.
- **The command taught to tell in the change that lands the check.** Not taken, though no time without the hold would then open. Where the command reads the data needs a record of its own (point 6). The check, which the calibration waits for, would wait on that record too.
- **The ladder's designs left as first drawn, a text under its minimum among them.** Rejected: the outside judge would rank down what the review cannot grade.
- **A round with a finding of the check counted as measured.** Rejected: the verdict would meet the bar on a page that fails validation ("Why measured and clean").
- **The designer changing a top's smallest size, or the piece's top, only on the person's word.** Not taken. It is a second guard kept by the designer's own rule, where a command can check a released version.
- **A value the designer wrote named as an accepted gap.** Rejected: unlike a change to the media, nothing shows it.
- **A loop that goes on through a round the hold does not reach,** and resumes when the hold returns. Rejected ("Why a round the hold does not reach ends the loop").
- **The piece's `audience` field taken in beside `shown`.** Not taken here ("Why the audience is left out").
- **A piece's media kept where no agent writes, such as the capability's configuration.** Rejected: where a piece is shown differs by piece, and the designer writes a piece's file whole from the asker's words.
- **A digest of the media the asker has seen, kept in the brief for the command to compare.** Not taken here. It would let a command find a change the asker never saw, as the makers' record of drafts does for words. It adds a field and a comparison for a guard no trial has shown to fail. The Implications name when to weigh it again.
- **The values a check measures against compared with the accepted data, to lapse the hold.** Rejected ("Why the values such a check measures against lapse no hold").

## Implications

- **This change adds a record, and changes nothing a project could observe.** The work that builds it changes the command that gives the verdict, and declares its own changeset.
- **Accepted with DEC-055,** in the same change.
  - **This record rests on** DEC-055 points 1, 2, 3, 9, 10 and 12: a piece's media, a top's smallest size, the width the check takes as given, when the check measures a piece, its statement, and what the review leaves out.
  - **Resting on this record:** DEC-055 point 13, on points 1 to 3 and 5, and DEC-055 points 1 and 6, on point 4.
- **Edits to accepted records,** made in this change once this record is accepted, each with a refinement pointer to this record. Accepting this record accepts them (COR-066 point 5).
  - **DEC-042's plain-terms summary.** After "Until then the grades only inform.", it comes to add: "Where a check takes a defect from the grades of a rule the bar covers, so that the defect lowers none of them, the loop runs so only on a round that check measured and found clean, as point 10 says (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] points 1 and 2)."
  - **DEC-042 point 6, its scope sentence.** After "Elsewhere the designer's loop ends as DEC-030 point 2 says.", it comes to add: "Point 10 reads the hold on each round where a check takes a defect from the grades of a rule the bar covers. A loop whose first review the hold does not reach ends as DEC-030 point 2 says. A loop the hold reached ends at the first later round the hold does not reach, by this point's hand-over (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] point 2)."
  - **DEC-042 point 6, the bullet "Then the person, with the last round that met the bar".** After "or at its last round where none did.", it comes to add: "A round the hold does not reach (point 10) is never the last round whose verdict met the bar. Where the loop ends at such a round, the designer says which of point 10's three conditions failed (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] point 2)."
  - **DEC-042 point 10, the bullet "Any project within what was calibrated".** "while nothing point 9 names lapses the hold." comes to read: "while nothing point 9 names lapses the hold. Where a check takes a defect from the grades of a rule the bar covers, the next bullet narrows that to the rounds the check measured (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] points 1 and 2)."
  - **DEC-042 point 10,** after the bullet "Any project within what was calibrated", gains a bullet: "**Only a round measured by each check that takes a defect from a covered rule's grades.** Where a check takes a defect from the grades of a rule the bar covers, the verdict ends the loop only on a round of which three things hold. That check measured each image the round's review read, with no statement of it and no defect it found on the image. The review read each image as the check measured it. Each value the check measured against or took as given lies in a released version of a library. Elsewhere it informs. Where the command cannot tell, it informs, and says so among its reasons. A round the hold does not reach ends the loop of point 6 (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] points 1 and 2)." It narrows the point.
  - **DEC-042 point 9,** the bullet "a held-out ladder". After "Each calibration takes a fresh ladder", it comes to add: "Where a check takes a defect from the grades of a rule the bar covers, the ladder is read as point 10 reads a round. That check measures every image of every design, with no statement of it and no defect it found on any. The calibration's review reads each image as the check measured it, and each value the check measured against or took as given lies in a released version of a library. So each design passes that check, and the outside judge ranks the designs as they then stand. The calibration's report names what each such check measured by, and against. For the check of a text's size, an example, that is the ladder's media and the smallest size of each (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] point 3)."
  - **DEC-042 point 7,** after the bullet "By where they came from", gains a bullet: "**Where the piece is shown is the asker's too.** A piece's `shown` field and the media it names are the asker's statement of where it is shown. The designer writes them from what the asker says, and shows them to the asker as it shows the goals. A fix that would change either is asked as one that would change the asker's words. So is naming media on a piece that names none (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] point 4)." The bullet lies outside the last two, so it holds at every level of the setting.
  - **DEC-042 point 7, "What it asks".** "where a fix would change the asker's words or cut a fact a goal or relation rests on" comes to read "where a fix would change the asker's words or where the piece is shown, or cut a fact a goal or relation rests on".
  - **DEC-030 point 2, "What it asks the person,"** in its first case. After that case's refinement pointer, it comes to add: "A fix that would change where the piece is shown, as its `shown` field and its media say it, is asked so too (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] point 4)."
  - **DEC-030 point 2, "How much it decides alone".** "the asker's words stay the asker's at every level" comes to read "the asker's words, and where the piece is shown, stay the asker's at every level".
  - **DEC-063 point 4, "The same grade either way".** "A check's reach moves no grade." comes to read: "A check's reach moves no grade, but for a check that takes a defect from a rule's grades (refinement per [visual-communication:DEC-064-hold-on-measured-pieces] point 1)."
- **Read against this record, and left as they stand:**
  - DEC-042 point 3, since the bar still lies where no agent reads it.
  - DEC-042 point 9's list of what lapses the hold, which gains nothing from this record (point 5).
  - DEC-030 point 5, since the designer may still write a piece's own file. Point 4 says which of its fields it changes only on the asker's word.
  - DEC-046 point 5, since the check still takes a small text from the grades, and this record only names that.
  - DEC-046 point 8, since a calibration still waits for each check to land. Its bullet on the report stands. What the report names of each check is DEC-042 point 9's, by the edit above.
  - DEC-062 point 3's "no check reads it", since the command reads no report of the viewing step until a record decides so (point 6).
  - DEC-063 point 3, since a check's silence is read as before.
- **UC-111,** "Have a piece designed and judged by the principles of visual communication", is revised in this change, once this record is accepted, in two places:
  - **Its variant 5b** comes to say that, under a bar that covers `RS-GRAPHIC-005`, the loop runs to the bar only on a piece that names its media.
  - **Its standing requirement** that the AI agent never changes the developer's words comes to take in where the piece is shown. Point 4 holds under a bar or not.
- **What [project-kit#3185](https://github.com/aleskalfas/project-kit/issues/3185) builds of this record,** with the check of a text's size:
  - **The command's reason.** The command that gives the verdict gains a reason that the hold is off. It holds where the bar covers `RS-GRAPHIC-005`, and says that the command cannot tell whether the check measured each image the review read. It reads no data for it.
  - **Its test:** under such a bar the command ends no loop and gives the reason, with every other reason absent.
  - **Its pages.** The outputs page, "When it ends the loop", gains the reason, and the verdict's document carries it in `why`.
  - **The designer's body and the skill's page on a piece** come to say point 4, and that a round the hold does not reach ends the loop (point 2).
- **The follow-up, [project-kit#3372](https://github.com/aleskalfas/project-kit/issues/3372),** has the command tell (point 6). It stands beside [project-kit#3296](https://github.com/aleskalfas/project-kit/issues/3296), which has the command compare the checks the review reads.
  - **It settles the source first,** in a record that refines point 6. That record also weighs whether the checks of boxes narrow the hold through their statement.
  - **Its scope takes in the three conditions of point 2:** whether the check measured each image clean, the review's line that it left the media out, and whether the piece's top and its brand are released.
  - **Until it lands,** no bar that covers `RS-GRAPHIC-005` gets the hold.
- **The order of the later work, for economy.** No wait is decided here (point 6).
  - **The review's field.** [project-kit#3328](https://github.com/aleskalfas/project-kit/issues/3328) words the review's reading of `media`. Its scope comes to take in the field by which the review's report says that it left the media out.
  - **The source's record** is accepted, and the follow-up lands, before a calibration runs. Landed later, the follow-up forces a new calibration.
- **Left open: whose the piece's `audience` field is to change.** It steers the grades and switches no hold (point 4). A refinement of DEC-042 point 7 would decide it.
- **No migration.** Nothing a project holds changes (COR-010).
- **Revisit this record** in each of these cases:
  - A round that got the hold carries a statement of a check of boxes, `near-alignment-unmeasured`. The reviewer's own sums then ended a loop untested.
  - A record has a second check take a defect from a rule's grades.
  - A check comes to fail a page and to measure only a piece that opts in, while its defect keeps its rule's grade. Its unmeasured pieces show the review pages no calibration did.
  - A designer is found to have changed where a piece is shown without the asker's word. A digest of the media the asker saw is then the guard to weigh.
  - A released top of a project's own library is found to declare a smallest size that lets unreadable text pass.
