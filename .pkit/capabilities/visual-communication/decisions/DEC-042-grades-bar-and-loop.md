---
id: DEC-042
title: The review grades each rule in words, and the designer's loop ends at the bar a project sets
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability's review grades each rule of `COMM` and `GRAPHIC` on each page in words: below competent, competent, professional or excellent, measured against professional work. A project sets its *bar*, such as "every page is professional on every rule", as an accepted rule in a rule set of its own, and the review gives a verdict against it. The designer's loop runs until the verdict meets the bar, goes on into polish within a bound, and then hands the person what still blocks it. The designer changes alone every word that is not the asker's, and asks only for what it cannot settle alone. A failing finding still names only where its fix belongs. The verdict holds that loop and nothing else: no merge, no validation and no other review. Where the canon lacks a measure, a rule is added through the record of the principles. The verdict starts to hold the loop once a calibration of the canon's grades meets the conditions set before the first one ran, which that first calibration did not.

## Context

The record of the design agents has the designer mend what it judges right, and stop when the reviewer's reading of every page reports nothing it would mend ([visual-communication:DEC-030-design-agents] point 2). The reviewer's findings inform, and hold nothing (DEC-030 point 6). No finding says how far a page is from good work, and no project says how good is enough. So the designer stops once it no longer agrees with what is left, however far that is from professional work.

The Feature [project-kit#3148](https://github.com/aleskalfas/project-kit/issues/3148) asks the designer to work under its own review until every page reaches a bar the project sets, and then hand the person only what still blocks it. Its Task, [project-kit#3151](https://github.com/aleskalfas/project-kit/issues/3151), ran two experiments before this record was drafted. That Task's pull request gives their figures.

**A calibration on a ladder.** The reviewer graded a ladder of earlier designs of one deck, from a first draft to designs a senior critic had judged professional and then polished, and the deck as the default branch draws it. It graded each design several times, in two arms: the canon's rules alone, and the canon's rules beside the senior critic's own measures. What it showed:
- **No design passed,** in either arm and in any run, the critic's professional designs included. So the conditions the Task set before the review may hold the loop were not all met (point 9).
- **The canon alone did not order the ladder as it was ordered with the critic's measures beside it.** It could not tell the last design from the first. On pages that were the same image in two designs, its page verdicts split from run to run. With the measures beside it, they agreed.
- **The rules on words failed pages across the whole ladder alike.** The ladder held its words nearly fixed, so those rules told no design from another. Graded on the `GRAPHIC` rules alone, the canon ordered the ladder much as the critic had. Where a design did change its words, the rule on sources graded the change.
- **Four of the critic's measures had no counterpart among the rules, or only a weak one:** craft, typography, legibility at the medium's size, and colour. One fault the critic blocked on judges design, and no rule names it.
- **Each review's verdict followed from its own grades,** read by the bar's text, in every run.

**Convergence on one page.** A page outside that deck was designed twice from the same starting page, by the same designer and reviewer agents. In both, the designer could change every word but the page's lead. The two loops differ only in how a failing finding states its fix:
- **Findings that name only where the fix belongs:** the first review failed the page, and the review after one round of mending passed it.
- **Findings that prescribe the fix:** the page passed after three rounds of mending. In the first review, two prescriptions changed what the designer could not: the page's lead, and a part that a relation of the brief names. The designer took neither. In a later round the review judged, from the browser's drawing, that the wording it prescribed would fit on one line. The engine's own measure broke it onto two, the render failed, and the designer took the review's fallback.
- **Neither loop needed the person.** The one question the designer raised went unanswered, and the review settled it by the rule it cited.

Each loop ran once, so the second experiment shows a direction, not a measure.

## Decision

**The review grades each rule of `COMM` and `GRAPHIC` on each page in words, against professional work, and gives a verdict against the bar a project sets as an accepted rule of its own. It sees the drawn pages, the brief and its own earlier verdicts, reads the designer's reasons only after it has judged, and names where a fix belongs without prescribing it. The designer's loop runs to the bar, on into polish within a bound, and then hands the person what blocks it. The designer changes alone every word that is not the asker's. The verdict holds that loop alone, once a calibration of the canon's grades meets the conditions point 9 names. Where the canon lacks a measure, a rule is added through [visual-communication:DEC-028-principles-of-visual-communication].**

### 1. The review grades each rule in words

- **A grade for each rule, on each page.** For each page, the review grades each rule of `COMM` and `GRAPHIC` that judges the piece (DEC-028 point 3). It judges the rule on every image of the page it reads, so a break in one language, mode or size counts. A *grade* is one of four words, from the lowest: *below competent*, *competent*, *professional* and *excellent*. Where a rule's own text leaves a page out, as the rule on the story's order leaves out a piece of one page, the page takes no grade on that rule, and the review says so. Each grade gives its evidence in a line.
- **Against professional work.** A grade measures what a reader sees against the work a professional designer hands over for that audience and medium. It never weighs effort, what the engine can draw today, or how far a page has come since an earlier round.
- **A rule finding carries its grade.** Each rule graded below professional, or below what the project's bar asks of it, is a rule finding as DEC-030 point 6 defines one, and carries its grade.
- **The verdict.** Where a project sets a bar (point 3), the review's report ends with its *verdict*: whether each page meets the bar, and whether the piece does. The verdict is read from the grades by the bar's text, with no judgement of its own.
- **A grade is a reading.** No rule's text settles a grade. So a rule finding on a grade, once its rule binds, is always for a person (DEC-030 point 6), at the merge too, and never fails a merge alone.
- **What stands.** A fault never judges how well a page is designed, and a note never fails (DEC-030 point 6).

### 2. Where the canon lacks a measure, a rule is added through the record of the principles

- **The gaps.** The calibration found four measures that the rules name weakly or not at all: *craft*, how cleanly each part is finished and joined to the next; *typography*, how the type is set; *legibility at the medium's size*, whether the text reads at the size the medium shows it, apart from whether the page is taken in at a glance; and *colour*, whether the colours work as one scheme, in each mode the piece is shown in.
- **Each closes through DEC-028.** Each gap takes a rule from the canon, with its source, in a refinement of [visual-communication:DEC-028-principles-of-visual-communication] that a person accepts in a change of its own (DEC-028 point 1). Where a rule names a measure only in part, as `RS-GRAPHIC-005` names legibility beside its glance test, that refinement chooses between a new rule and a clearer statement of the old one.
- **No borrowed measure becomes a rule.** The measures the calibration set beside the canon were one critic's, written for one deck. They show where the canon is thin, and are never a rule's source (DEC-028 point 1).
- **A blocking fault that judges design is a rule,** graded at the bottom: a page that shows it takes *below competent* on that rule. It never joins the reviewer's list of faults, which never judge design (DEC-030 point 6).
- **What stays the checks'.** Contrast, a text that overflows its box and a text smaller than its medium allows stay the checks' (DEC-028 point 1). A rule judges only what no check measures.

### 3. The bar is an accepted rule of the project's own

- **What a bar is.** A project's *bar* says which grade each page must reach on which rules, such as "every page is professional on every rule". It is a rule in a rule set of the project's own that inherits `COMM` and `GRAPHIC` (COR-051 point 7), accepted by a person like every rule (COR-051 point 4). It is the project's taste, so the capability ships none (DEC-028 point 1).
- **Read from its file.** The review reads the bar from that set's file, as it reads the rule sets (DEC-030 point 6), never from whoever dispatches it. A proposed bar is no bar.
- **No bar, no hold.** A project that sets no bar holds its designer to none. The review still grades each rule, and gives no verdict. The designer's loop then ends as DEC-030 point 2 says.
- **It binds no file of a piece.** While a piece's files are no artefacts, no rule binds on them, the bar included (DEC-028 point 5). The bar holds the designer's loop because this record says so (point 8), and nowhere else.
- **A default bar for adopters** waits for the evidence of the capability's trials ([project-kit#3150](https://github.com/aleskalfas/project-kit/issues/3150)).

### 4. What the review sees

- **What it reads.** Every image the viewing step drew of the piece, with the frames and the report; the brief; its own earlier verdicts on the piece; the rule sets, the bar's set among them; and the design knowledge (DEC-030 point 8). It checks the piece's facts against their sources, as DEC-030 point 7 says.
- **Its earlier verdicts, unaltered.** It reads the reports of the loop's earlier rounds as it wrote them. Nobody summarises, filters or answers them first, the designer included. It reads them so that its grades hold across rounds: where it grades a part lower than before and the part did not change, it says why.
- **The designer's reasons, after it has judged.** It reads the brief's reasons only once it has graded the page (DEC-030 point 6). It reads no account of the designer's of what it changed.
- **A need, not a round.** A finding whose only fix is a tool the engine lacks is a *need*. It names the missing tool and the rule it blocks. It leaves the loop as a question to the person, as DEC-030 point 4's stop does, and the verdict names it apart. It fails the bar in no round, so the loop spends no round on it.

### 5. A failing finding names where its fix belongs, and prescribes no fix

A failing finding names what fails, where, what it rests on and where its fix belongs, and never what the fix is, as DEC-030 point 7 decides. The convergence experiment points the same way (Context): the loop whose findings named where the fix belongs converged in one round of mending, and the loop whose findings prescribed the fix in three. Each prescription that missed did so for a reason only the designer could see: a word the asker had fixed, a relation of the brief, or the engine's own measure of a text. Each loop ran once, so this is a direction, which agrees with the reason DEC-030 gives: a reviewer that redesigns becomes a second designer.

### 6. The loop runs to the bar, into polish, within a bound

This point holds where a project sets a bar, and the verdict holds the loop (points 8 and 9).
- **A round** is one mend of the piece by the designer, then a render, a look and a review of every page (DEC-030 point 2). The designer's *loop* is the rounds from the first review on.
- **To the bar.** While the verdict fails the bar, each round mends each failing finding the designer may mend (point 7), as DEC-030 point 2 has it mend.
- **Into polish.** Once the verdict meets the bar, the loop goes on into *polish*: rounds that mend what the review graded below excellent, and the notes the designer agrees with. Where a polish round's verdict fails the bar, the next round mends that first. Polish ends when the review reports nothing below excellent and no note the designer would act on, or at the bound.
- **Within a bound.** The loop runs no more than a bound of rounds, to the bar and in polish together. *Open in this draft:* the bound, and whether a finding two rounds did not clear stops the loop as DEC-030 point 2 has it, or goes to the person at the loop's end while the loop goes on.
- **Then the person.** When the loop ends, the designer hands the person what blocks the piece: each finding that still fails the bar, each need, and each question it could not settle. It hands over the review's last report as the review wrote it, and says what it changed (DEC-030 point 2).
- **What a check measures stays the check's.** The designer mends what a check fails before any round's review, as it renders and checks (DEC-030 point 2), and no round counts a check's failure.

### 7. What the designer changes alone, and what it asks

This is the capability's default until the core decides how much agents decide without asking ([project-kit#2801](https://github.com/aleskalfas/project-kit/issues/2801)).
- **The asker's words.** A piece's intent belongs to whoever asked for it, the *asker* (DEC-029 point 4). So do the words that carry it: the brief's goals, relations and takeaway, and each page's lead, which stands as the page's takeaway ([visual-communication:DEC-029-piece-brief] point 2). A goal may name other words of the content as the asker's, such as a quote. The designer changes none of them without the asker's word.
- **Every other word is the designer's.** It may reword, cut or move any other text, in every language alike, where each goal and relation of the brief still holds. It may cut a fact, or correct one to what its source says. A fact it adds names its source (`RS-COMM-005`). It tells the person afterwards what it changed and why, as DEC-030 point 2 has it tell.
- **What it asks.** It asks the person only where a fix would change the asker's words, where a fix needs a write it may not make (DEC-030 point 5), and where point 6 hands over what the loop could not clear. Each time it says what it recommends.
- **A finding only the asker's words can mend** leaves the loop as a question to the person, as a need does (point 4), and fails the bar in no later round.

### 8. Where the verdict binds

- **On the designer's loop on a piece.** The verdict says whether the loop has reached the bar (point 6). While the verdict fails the bar, the designer neither ends the loop as passed nor hands the piece over as meeting the bar.
- **Nowhere else.** Elsewhere the reviewer's findings inform their owner, who decides, and a verdict holds nothing. That covers the starter's entry review ([visual-communication:DEC-007-starter-library] point 3), a role's default as a fair stand-in ([visual-communication:DEC-008-library-role-defaults] point 2), a picture with the piece's words drawn into it ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 2), and a review a person asks for outside a loop.
- **No validation, no merge.** The verdict joins no validation, since a reading of taste never fails ([visual-communication:DEC-002-files-and-validation] point 7), and holds no merge. Whether the review is required at the merge is [project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)'s.

### 9. The verdict holds the loop once a calibration meets its issue's conditions

- **The conditions.** The Task that calibrated the review let it hold the designer's loop only where four conditions all hold on the ladder ([project-kit#3151](https://github.com/aleskalfas/project-kit/issues/3151)). The grades order the ladder as the critic ordered it. The last design the critic failed fails, and the first it passed passes. The verdict is stable across runs. The deck as the default branch draws it fails.
- **Not met yet.** The first calibration did not meet them. No design passed, the first the critic passed included, and the canon alone did not tell the last design from the first (Context). The conditions that held, held only because every verdict was a fail. So the verdict holds no loop yet.
- **Until then.** The review grades each rule and gives its verdict, which informs. The designer's loop ends as DEC-030 point 2 says.
- **Then.** Once the gaps of point 2 are closed, the calibration runs again on the same ladder, grading by the canon alone, since the canon is what the capability ships. Where it meets all four conditions, the verdict holds the loop from then on, as point 8 says.

## Rationale

**Why grades in words.** A pass or a fail on each rule hides how far a page is from the bar, and leaves polish nothing to aim at. Words read alike to the designer, the reviewer and a person, and each names a level of work. A number would invite sums that no rule supports, such as a mean in which one strong rule hides a weak one. The bar reads each rule apart. In the calibration, every review's verdict followed from its grades, so a verdict read from grades adds no second judgement.

**Why against professional work, and not against progress or the engine.** A review that graded progress would pass a weak page that improved. One that graded what the engine draws today would pass the engine's limits as the piece's quality. A missing tool is a need instead (point 4), so the person sees it, and the grade stays honest.

**Why the gaps close through the record of the principles.** The rules are the canon's, each with its source, and a project or a talk that shows a rule at work confirms it and is never its source (DEC-028 point 1). The calibration showed where the canon is thin. One critic's measures for one deck would carry that critic's taste to every project.

**Why a blocking fault on design is a rule at the bottom.** The reviewer's faults stay facts about the drawing, which is why a fault never judges design (DEC-030 point 6). A fault of design is a reading. As a rule graded at the bottom, it blocks the bar while it keeps the citation, the source and the acceptance of every rule.

**Why the bar is the project's own rule.** How good is good enough is a project's taste (DEC-028 point 1). As a rule of its own set, it has an id, a status and a person's acceptance, and the review reads it as it reads every rule, from its file. A shipped bar would carry one project's taste to every project (COR-014). The trials of [project-kit#3150](https://github.com/aleskalfas/project-kit/issues/3150) show whether a default would serve.

**Why the review sees its earlier verdicts, and not the designer's account.** In the calibration, the canon's page verdicts on the same images split from run to run. A review that sees what it said before can hold its grades across rounds, or say why it moved one. An account of what the designer changed would show the review the page through the designer's eyes, as reading the reasons first would (DEC-030, "Why the reasons are read last").

**Why a need, or a finding only the asker's words can mend, leaves the loop.** No mend of the designer's reaches either. A round spent on one would end at the bound with no news for the person. The calibration shows the case: the rules on words failed pages in every design, whose words were held, and a loop that counted those failures would fail every round.

**Why a finding names where its fix belongs.** Only the designer renders, so only the designer learns whether a fix fits. The engine's measure of a text decides its line breaks, and a review that judges from a drawing can be wrong about them. A prescription also meets limits the review does not weigh, such as words the asker fixed. The convergence experiment shows both, in one run of each loop.

**Why polish, and why within a bound.** A loop that stopped at the first pass would hand over work just at the bar. Polish spends a few rounds on what the review still grades below excellent. The review varies from run to run, so a loop with no bound could chase that variation for ever. A bound ends it, and the person gets what still blocks.

**Why every other word is the designer's.** The brief's goals and relations, and a page's lead, say what the piece is for, so they are the asker's (DEC-029 points 2 and 4). The other words carry that intent, as the form does, and the designer shapes them as it shapes the form. In both loops of the convergence experiment, the designer changed titles, cut facts with no source and reworded parts in nearly every round, and neither loop needed the person. A designer that asked before each such change would converge only as fast as the person answers.

**Why the verdict binds only the loop.** A grade is a reading, which never fails validation (DEC-002 point 7). Elsewhere, an owner judges by a bar of their own, such as the starter's bar for entry, and the review informs that owner.

**Why the verdict waits for a calibration.** A verdict that holds a loop must tell good work from weak work, and say the same of the same page twice. The first calibration showed the canon alone doing neither on the ladder. A loop held to that verdict would mend for noise, and could never pass work the critic judged professional. The conditions are the Task's own, set before it ran.

### Alternatives considered

- **The critic's measures beside the canon, as the calibration graded them.** Rejected: they were one critic's, written for one deck, and no source of the canon's names them (DEC-028 point 1). The gaps they showed close through the canon instead (point 2).
- **The `GRAPHIC` rules alone as the measure.** Rejected: the ladder held its words, so the calibration cannot show that the rules on words grade badly, only that they told those designs apart by nothing. The one change of words the ladder made, `RS-COMM-005` caught. A project that wants a bar on `GRAPHIC` alone writes its bar so.
- **A pass or a fail on each rule, with no grade.** Rejected: polish would have nothing to aim at, and nobody could tell a page near the bar from one far below it.
- **Grades as numbers.** Rejected: a sum or a mean lets a strong rule hide a weak one, and no rule says what a mean means.
- **A bar the capability ships.** Not taken now: it waits for the trials ([project-kit#3150](https://github.com/aleskalfas/project-kit/issues/3150)).
- **A bar in the capability's configuration.** Rejected: it would have no acceptance and no review, and the bar is a requirement on pieces, which is what a rule is (DEC-030 point 8).
- **Findings that prescribe their fix.** Rejected: in the convergence experiment, prescribing slowed the loop, and one prescription was wrong where only the engine's measure could tell.
- **The verdict holding the loop at once, on the canon as it is.** Rejected: the calibration did not meet its Task's conditions, and the canon alone did not tell the last design from the first.
- **A loop with no bound, until the bar.** Rejected: the review varies from run to run, and a loop could chase that variation for ever.
- **The designer asking before any change of words.** Rejected: no loop would converge alone, since the convergence experiment changed words in nearly every round.

## Implications

- **Edits made in this change once this record is accepted,** each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-030 point 2, "When it stops,"** comes to say that where a project sets a bar and the verdict holds the loop, the designer stops as this record's point 6 says, and hands the person what blocks the piece. Elsewhere it stops as it stands.
  - **DEC-030 point 2, "What it mends by itself,"** comes to add every word that is not the asker's (point 7).
  - **DEC-030 point 2, "What it asks the person,"** comes to read: a fix would change the asker's words, the brief's intent or a page's lead among them; a fix needs a change it may not make; or point 6 hands over what the loop could not clear. Its third case follows what point 6 settles of the bound.
  - **DEC-030 point 2, "How much it decides alone,"** comes to add that this record's point 7 is the capability's default until then.
  - **DEC-030 point 6, "A rule finding,"** comes to add that it carries its grade in words, and that each rule graded below professional, or below what the bar asks, is one (point 1).
  - **DEC-030 point 6, "Advice,"** comes to add the verdict against the project's bar, which holds the designer's loop as this record's points 8 and 9 say, and holds no merge.
  - **DEC-030 point 7, "It reports, and never redesigns,"** comes to add the engine to where a fix belongs, for a need (point 4). The rest of the point stands: a finding prescribes no fix (point 5).
  - **DEC-015 point 7, "It reads, and does not draw,"** comes to add its own earlier verdicts on the piece, as it wrote them, and the bar's rule set (point 4).
  - **DEC-015 point 7, "Its findings,"** comes to add that a rule finding carries its grade, and that the report ends with a verdict against the project's bar where one is set (point 1).
  - **DEC-015 point 7, "Advice, for now,"** comes to add that the verdict holds the designer's loop on a piece, as this record's points 8 and 9 say, and nothing else.
  - **DEC-029 point 4, "People write it,"** comes to add that the goals, relations and takeaway are the asker's words, and so is a page's lead where it stands as the takeaway. A goal may name other words of the content as the asker's, and every other word is whoever designs the piece's to change within them (point 7).
- **Read against this record, and left as they stand:**
  - DEC-030 point 6's faults and notes, since a fault never judges design and a note never fails;
  - DEC-030 point 8, since the bar is a rule of a project's set, and the design knowledge holds no requirement;
  - DEC-002 point 7, since the verdict joins no validation;
  - DEC-015's summary, since the reviewer still advises at the merge, and holding the designer's loop is the designer's rule;
  - DEC-006 point 2, DEC-007 point 3 and DEC-008 point 2, since the review informs their owners;
  - DEC-028 and the rule sets, until the refinement of point 2.
- **UC-111,** "Have a piece designed and judged by the principles of visual communication", comes to say that the capability converges alone, held to the bar a project set. It is revised in this change, once this record is accepted.
- **Tasks filed under [project-kit#3148](https://github.com/aleskalfas/project-kit/issues/3148) once this record is accepted:**
  - **The refinement of DEC-028** that closes the gaps of point 2, each with a rule from the canon, in a change a person accepts;
  - **The second calibration** of point 9, on the same ladder, once that refinement lands. Its figures go in its pull request;
  - **The reviewer's body:** the grades, the verdict, its earlier verdicts, needs, and what it reads only after it has judged. Where the loop keeps the review's reports between rounds is that Task's to settle, in the clone's local folder, as the viewing step keeps its images (DEC-015 point 4);
  - **The designer's body and the skill that guides building a piece:** the loop, polish and the bound, the asker's words, and what goes to the person;
  - **project-kit's own bar,** an accepted rule in a set of its own, as [project-kit#3148](https://github.com/aleskalfas/project-kit/issues/3148) asks.
- **Left open:**
  - a default bar for adopters ([project-kit#3150](https://github.com/aleskalfas/project-kit/issues/3150));
  - the review at the merge ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)), which needs the review's verdict stable across runs, as point 9's calibration measures it;
  - how much the designer decides without asking, once the core decides a project's setting for it ([project-kit#2801](https://github.com/aleskalfas/project-kit/issues/2801)). This record's point 7 is the default it replaces.
- **No migration.** Nothing a project holds changes (COR-010).
