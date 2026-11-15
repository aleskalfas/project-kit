---
id: DEC-047
title: A piece's drawn pages change only through one design process, and no stage of it is skipped
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** every change to what a piece draws goes through one *design process*. Its stages run in a fixed order: the intent, the piece's design system, each page, the drawing of every variant, the check, the review, and a critique at the professional level. Then the change lands. How small a change is decides only where it enters, and a command computes that. "No stage is skipped" means two refusals: the capability's commands refuse a stage whose earlier stages left no evidence, and the capability's merge check refuses a change whose pieces have no pass, wherever a project runs it. It does not mean an agent cannot break the process on purpose. The person who answers for a piece is shown its pages and told what the review found, with pictures, and gives no sign-off on a change that has a pass. Point 6 lists what that person decides. Two of those things matter most: letting through a piece short of a pass, and what is changed after a review, until a calibration, a test of the reviewer, has shown that the reviewer judges rightly.

## Context

A person with no design knowledge asks for a piece in a few sentences, and expects professional design back. The capability's agents, working alone, returned pages that no check and no review failed, and that were poor. The same pages reached a professional level when someone who read each design failed anything below that level. [project-kit#3148](https://github.com/aleskalfas/project-kit/issues/3148) asks the capability to do that by itself.

**What failed, by cause.**
- **The libraries** held general components, and too little that a piece's system could be chosen from.
- **The knowledge** states principles, and nothing made a change read them. A mend reads only the topics it seems to need ([visual-communication:DEC-030-design-agents] point 8), so most mends read none.
- **The system.** Nothing decided a piece's grid, type and colour meanings before its pages, so each page was mended alone.
- **The loop** ends when nothing is broken. A reading of taste is a note that never fails (DEC-030 point 6), and the designer stops after two rounds on a finding (DEC-030 point 2).
- **The tasks.** Work reached the designer as small fixes, such as "fit the words". Each fix skipped the method, and no test or reviewer had quality as its criterion.

**What the records hold.** The designer's method orders its choices (DEC-030 point 3). A brief holds a piece's intent and the reasons for its design ([visual-communication:DEC-029-piece-brief]). The review grades each rule in words ([visual-communication:DEC-042-grades-bar-and-loop]). None of them says that a change must go through the method, or leaves a trace that it did. Each step is asked of an agent, and an agent handed a narrow task leaves steps out.

**What a process cannot give.** Libraries that can draw good design, and knowledge that shows weak work beside strong, are content of the capability. A process makes sure they are used. It does not make them good.

## Decision

**A piece's drawn pages change only through one design process. Its stages run in order, a change enters at the stage a command computes, and no agent skips a stage.**

This record decides the process, its stages, where a change enters, and who may stop it.

In this record a *change* is a change to one piece, as one place defines it: everything done to the piece's files between two review reports of it, with the stages run on those files ([visual-communication:DEC-051-no-reading-chooses-before-calibration], Decision). What a project lets through to its default branch as one unit is another thing, a *landing change*, and is named in full every time ([visual-communication:DEC-048-stage-evidence-and-refusals] point 8).

Other records each decide one thing more:
- the piece's design system ([visual-communication:DEC-050-piece-design-system]);
- what each stage leaves, and where a piece without it is refused ([visual-communication:DEC-048-stage-evidence-and-refusals]);
- what the critique's verdict decides ([visual-communication:DEC-049-critique-step]);
- when a *reading* of a piece may choose its next change, and what counts as a reading ([visual-communication:DEC-051-no-reading-chooses-before-calibration]);
- what a piece's libraries must have shown before the piece has a pass ([visual-communication:DEC-052-library-parts-open-findings]).

### 1. One process for every change to what a piece draws

- **A piece's drawn pages** are what its renderers draw: every page, in every variant the piece names (point 3).
- **The design process** is the one way they change. It covers a new piece, a redesign, a mend, a change of words, and a library change that reaches a piece through its *lock*, the piece's list of the exact library versions it uses ([visual-communication:DEC-003-change-over-time] point 8).
- **A library's and a brand's look.** The pages that show what a library draws are a piece, and go through the process as any piece does (DEC-052 point 6). A change to a library or a brand reaches every other piece through its lock. A change to one that no piece draws with yet is seen by no command, and only the session's rule binds it (point 7).
- **No lesser path.** No change is a fix that goes through fewer stages. How small a change is decides where it enters (point 4), never which stages follow.
- **Looking is free.** A render, a look or a check made to see a page records nothing, and is never refused. Only a stage's own command records that the stage ran (DEC-048 point 6). What a look may not do is choose the next change by another's reading (DEC-051).
- **A final piece** is outside the process, since nothing changes a final piece ([visual-communication:DEC-017-final-and-published-states] point 3).

### 2. The stages, in order

A *stage* is one step of the process, with what it must leave before the next begins. There are seven, and then the landing.

1. **Intent.** The brief holds the piece's goals and relations, and each page's point, as its lead or its takeaway (DEC-029 point 2). The piece's own file says who it is for and where it is shown. Whoever asked for the piece has seen them (DEC-030 point 2).
2. **System.** The piece's design system is decided before its pages (DEC-050).
3. **Pages.** For each page, the designer names the content's structure and the order of explanation, weighs at least two forms, and chooses one with its reason (DEC-030 point 3). It takes type, colour and space from the system.
4. **Drawing.** Every variant of every page is drawn (point 3).
5. **Check.** The capability's check finds no failure on the piece ([visual-communication:DEC-002-files-and-validation] point 6).
6. **Review.** The reviewer reads every page in every variant, and grades each rule (DEC-042 point 1). Until the reviewer is calibrated in the project (DEC-051 point 1), one review is made, its findings go to the person, and the next change waits for the person's word (DEC-051 points 2 to 4). Once it is calibrated there, the designer mends in rounds as the accepted records have it (DEC-030 point 2; DEC-042 point 6). Each mend is a change, and re-enters (point 4).
7. **Critique.** A command gives a verdict on the piece at the professional level. Until the reviewer is calibrated, it reads that verdict from the last review report. Once it is calibrated, the reviewer reads the piece again, started fresh (DEC-049).

**Then the landing.** The change reaches the default branch, or the piece reaches readers, only with a pass (DEC-048). The landing is no stage of the piece. It is where a pass is asked for.

Two things are true of every run:
- **The design knowledge, whole.** The system stage and the pages stage are given every topic of the design knowledge (DEC-030 point 8), in the instructions their command writes for the designer (DEC-048 point 3). Reading it is no stage of its own, since reading leaves nothing a check can see.
- **The pages stage is done page by page.** It is done once every page has its evidence.

### 3. Every variant a piece names is drawn and read

A *variant* is one combination in which a piece's pages reach a reader: a language, a combination of modes, a size, a renderer the piece's outputs use, and a forced palette where a browser draws the page ([visual-communication:DEC-027-forced-colours-viewing]).
- **All of them, every run.** The drawing stage draws them all. The review and the critique read them all. A variant nobody read is named as not seen, and the stage is not done ([visual-communication:DEC-015-viewing-step-and-reviewer] point 7).
- **The same drawing is read once.** Where a command finds that two combinations give the same drawing, one image serves both, as one picture serves the combinations that give it the same values ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 3). The record says which.
- **A variant that cannot be drawn,** such as where no browser starts, stops the process at the drawing stage (point 5).

### 4. A change enters at the first stage that read what it changed

- **Computed, never declared.** Each stage's evidence is tied to what that stage read (DEC-048 point 1). A command finds the earliest stage whose evidence does not match the files, and the piece stands there. Nobody who makes a change, or hands it to an agent, says which stages it needs.
- **Worked out from the files on every check.** Where a piece stands is worked out each time from its files and its evidence. Nothing keeps a position between two checks, so this is the detection over reality that the methodology's process substrate asks for, and no stored position (COR-033, Implications). Reading a position from files that agents write is nothing new: the lifecycle of work items is detected from marks that agents set ([project-management:DEC-033-rebind-issue-lifecycle-onto-process-substrate] D2).
- **What each stage reads:**
  - the intent reads the brief's goals, relations and takeaways, and whom the piece is for and where it is shown;
  - the system reads the brief's part for the system, and each library version the lock names;
  - a page reads its form: its components, its layout, its local components and its pictures;
  - the drawing reads everything the pages are drawn from, the words among them, in every language, and the variants the piece names (point 3);
  - the check, the review and the critique read the drawing. The review also reads the brief's reasons.
- **A stage's result is read by the next.** The system rests on the intent, each page on the system, and the drawing on every page.
- **A stage run again may leave its result as it is.** A changed intent sends the piece to the system stage. The designer reads the change there, and may leave the system as it stands. The pages then stand too, since each page rests on what the system says, and not on the fact that its stage ran again. So a corrected word in a goal, a replaced picture or a library's patch costs one stage read again, and no redesign.
- **A text or a choice of form.** A page's form is read by the keys of its content that choose a component, a layout or a picture, and by how many entries each component is given. A text is read by the drawing alone. This needs the content's schema to tell the two apart by key. A key it cannot place counts as form.
- **A new variant enters at the drawing.** A language, a mode, a size or a renderer added to a piece is drawn and read whole. Where a page's form does not fit it, a finding says so, and its mend enters at that page.
- **Every later stage, for the whole piece.** The drawing, the check, the review and the critique always cover the whole piece, since a change on one page shows in how the pages read together.
- **A mend is a change.** A mend after a review or a critique enters by what it changed. Where the words no longer fit a page's form, a finding says so, and its mend enters at that page.

### 5. No agent skips a stage, and a stage that cannot run stops the process

- **No agent skips, reorders or stands in for a stage.** That binds the designer, the reviewer, and the session that runs the process.
- **The session that runs the process** is the session that takes a change through the stages. It runs each stage's command, or does that stage's work by hand where the command is not built yet. It designs the piece itself, or dispatches the designer. These records use this one name for it, and the record of the grades calls it whoever dispatches the designer (DEC-042 point 6). It is an actor and no role: it decides nothing that point 6 gives to a role.
- **A stage that cannot run stops the process there.** Examples are a variant no tool draws, a harness that reads no image and a design the libraries cannot draw (DEC-030 point 4). The stop goes to the person, with what the stage needs. A session tells its own user, who is the person or carries the stop to the person. The piece stands at that stage until it runs.
- **A person who edits a piece by hand** changes its files as anyone does. The piece then stands at the stage the edit reaches.

### 6. Who decides what, and what the person is told

Six roles decide something in the design process. One human may hold several of them, or all six.
- **The person** is whoever answers for the piece. That is the asker, unless the project has given the piece to someone else to answer for. Wherever these records say "the person", they mean this one role.
- **The asker** is whoever asked for the piece. Its intent, and the asker's words, are theirs (DEC-042 point 7).
- **Whoever authorises the merge** decides whether a change lands.
- **A library's owner** is whoever answers for a library, and for what each of its released versions holds. For a library the capability ships, that is whoever maintains the capability. For a project's own library, that is whoever authorises the project's merges, unless the project has given the role to someone else.
- **Whoever answers for a project's received libraries** decides, for that project alone, about the parts of a library the project receives from elsewhere. That is whoever authorises the project's merges, unless the project has given the role to someone else.
- **Whoever maintains the capability** decides its records, accepts or withdraws a calibration, and confirms the ranking of the designs a calibration grades (DEC-042 point 9; DEC-051 points 7 and 9).

Where a project names who holds a role:
- **In its own documents, and no command reads it.** A project that gives a piece, or a role, to someone else says so where it keeps such choices. No command of the capability reads who holds a role, and none checks whose word it records. Should a command come to read it, the record of that command decides where the choice is kept.
- **Where one human holds two roles,** what one role is shown about the other's decision is shown to the human who made it. Where several people hold one role, any of them may give its word, another's finding taken back among them ([visual-communication:DEC-052-library-parts-open-findings] point 3).

What the person is told and shown:
- **Told, not asked.** A piece that has a pass lands without the person's sign-off on that change. Whoever authorises the merge sees each piece's last verdict as it was written.
- **Shown the pages first.** Before a person is asked to decide anything about a piece's pages, that person is shown the drawn pages. A finding, a verdict or a library part that is put to a person comes with the image it is about, the element pointed out where the review named one. The command that shows it draws the image again where the clone's local folder has lost it.
- **What showing is.** Drawing the pages for a person is showing. So is naming their image files for that person to open, where the harness shows no image. Where neither is possible, the person asked is told so, and is not asked to decide from words alone.
- **Before and after, side by side.** The pages are shown beside the same pages as they stood when the person last kept them. The person *keeps* pages by saying so at a showing, and an acceptance or a kept result of a series is a keep too (DEC-051, Decision). Once the commands ship, the showing command records each keep. Until then, and where no keep is recorded, the baseline is the default branch's pages, or nothing where the piece is new there.
- **The baseline moves only once the person has said so.** A comparison with the pages last shown would hide a slow drift, since each of ten small steps can look no worse than the one before. The default branch's pages move too, with every landing, and a piece may land after each change (DEC-051 point 2). So they serve only where no keep is recorded. Which of two pictures is better is a judgement that a person who is no designer can make.
- **A series ends the same way.** A named series of rounds ends with its first pages and its last side by side, and the person keeps the result or goes back to where the series started (DEC-051 point 3).
- **A merge is a decision about the pages.** Authorising a merge that changes a piece's drawn pages decides about them. So whoever authorises it is shown the changed pages beside the baseline, with each verdict (DEC-048 point 8).
- **Until these commands ship,** no keep is recorded and no series runs. The session's rule asks for the default branch's pages beside the new ones, where the session can draw both (point 7).
- **What the person decides about a piece:**
  - **A piece without a pass.** The person may accept it as it stands, send it back with their words, or drop the change. Nothing else lets a piece through short of a pass. An acceptance is recorded on the person's word, for the files as they stood (DEC-048 point 4).
  - **What is changed after a review.** Until the reviewer is calibrated, no change to the piece starts after a review report or a reading without the person's word, given once the person was shown it and the pages. That covers which findings are mended, and every other change, a mend of the designer's own slip among them (DEC-051 points 3 and 4). Once it is calibrated, the accepted records say what the designer mends and what it hands the person (DEC-030 point 2; DEC-042 point 6).
  - **A named series of rounds** under a reviewer that is not calibrated, once told what that means, and whether to keep its result (DEC-051 point 3).
  - **The bound of the critique's rounds, lowered for the rounds that follow one failing verdict** ([visual-communication:DEC-049-critique-step] point 5).
- **What the person asks for beyond these** is a request like any other, and is recorded as one where it follows an uncalibrated review report (DEC-051 point 4).
- **Where the person and whoever authorises the merge differ.** About the piece, the person's word counts and no other. A named mend, a request, an approved work item, a named series and an acceptance are the person's, and whoever authorises the merge cannot give one in the person's place. At the merge, whoever authorises it decides whether the landing change lands, and sees what the person decided. They may hold back any landing change, one whose pieces have a pass among them.
- **What a library's owner decides.** A library's owner may accept one of its parts with its finding, or have a finding written down. Whoever answers for a project's received libraries may do the same for that project alone (DEC-052 points 3 to 5).

### 7. A rule binds every session to the process

A rule of the capability's loaded rule set binds each session's work to the process. It alone binds what no command and no check sees (DEC-048 point 9). A session reads the rule and not these records (COR-065 point 7). So the rule states each of its terms in its own words, and holds a session that loads nothing else as these records hold it. Its asks come in two parts, by when each ships.

Three asks ship with these records (point 8). Each is a rule of its own in the set, with its own id and its own lead, and each holds one ask. They ask a session:
- **To let no reading choose the next change.** Until the reviewer is calibrated, no reading of a piece's design chooses the next change to that piece or any other, or to a library or a brand either draws with, and a review's findings go to the person as written (DEC-051 point 2). The rule says in its own words:
  - what a reading is and who gives one: any agent or critic, the session that dispatched whoever builds the change among them (DEC-051, Decision);
  - what is none: the judgement of whoever builds a change the person asked for, of the piece's existing pages too, and a judgement of text that states no piece's design;
  - which command's answer makes the reviewer calibrated, and that it is not calibrated before;
  - that a calibration's held-out designs are outside the rule only where a rule of the repository's own names them and never lets them become another piece's design (DEC-051 point 8).
- **To start no change after a review or a reading without the person's word.** Until the reviewer is calibrated, after a review report or a reading of a piece, a session starts no change to the piece, or to a library or a brand it draws with, without the person's word (DEC-051 points 3 and 4). The wait covers the piece read. Another piece is held by the first ask alone, which forbids a reading of one piece to choose the change to another. The rule says in its own words:
  - that the word counts once given after that report or reading, by the person shown it and the pages, and that a word given ahead starts nothing;
  - that a mend of the session's own slip is included, and that its own look at pages it just built starts nothing, so planned work goes on between looks;
  - which review reports hold a session: one kept for the piece in the clone's local folder, or one the session knows of.
- **To show the pages before asking about them.** A session shows a person a piece's drawn pages, and each finding with its image, before asking that person to decide anything about them (point 6). The rule says in its own words:
  - what showing is, and that where it is not possible the session says so and asks for no decision;
  - that the default branch's same pages stand beside them, where the session can draw both. No keep is recorded before the showing command ships, so that is the whole baseline until then;
  - that authorising a merge that changes a piece's drawn pages is such a decision.

Six asks join the rule when the stage commands ship:
- **The named series of rounds.** It is the one word that reaches ahead, on the conditions DEC-051 point 3 sets, each of which the rule names. It runs only once the capability's command records it and keeps its starting state, and it ends with its first pages beside its last. No series runs before that command ships. So until then "a word given ahead starts nothing" needs no exception.
- **The stop.** A session stops and tells the person where a stage cannot run, or where a command of the capability refuses for evidence the session cannot supply, such as the person's word. The rule names the stages, each of which has its command by then. A session tells its own user, who is the person or carries the stop to the person. A refusal that names a file the session can mend is no such stop: the session mends the file and runs the command again.
- **The person's last keep as the baseline.** Once the showing command records each keep, the showing rule names the pages the person last kept as what the new pages stand beside (point 6).
- **Three asks that name the capability's commands:**
  - to change what a piece draws, and the look of a library or a brand, only through the design process, each stage through its command, and never to hand over or take a change as a fix that skips a stage;
  - to record a person's acceptance, or what a person asked for, only on that person's word;
  - to record a review report whole before it acts on anything.

Five things about the rule:
- **The showing is refused where it was left out, and rests on the rule beyond that.** The command that records any of the person's five words refuses where the command that shows the person the pages and the findings was not run for that review report (DEC-051 point 3). The command that records an acceptance of a library part, or takes back a person's finding on one, refuses in the same way where the part's image was not brought up (DEC-052 points 3 and 4). A command cannot tell that the person looked, or that an agent's question came with the picture, since the agent that asks is the one that records the answer. So the refusal catches a showing left out by mistake or in haste, as every refusal on recorded evidence does (DEC-048 point 9). The rule alone asks for the rest.
- **Nothing about the designer's loop after a calibration.** What the rule asks of that loop then is decided with a calibration's acceptance (DEC-051 point 6).
- **Wider than the commands.** A command sees a recorded review report, and a change to a piece. The rule's wait also starts at any other reading, and also holds a change to a library or a brand the piece draws with. The rule also forbids a reading of one piece to choose the change to another piece, which waits for nothing. Before the commands record a report, the rule holds a session only to a report it finds or knows of (DEC-051 points 4 and 5).
- **Only what binds everywhere.** The rule holds only what binds wherever the capability is installed (COR-070 point 1). Of the designs a calibration grades it says one thing: they are outside it only where a rule of the repository's own names them and never lets them become another piece's design. Without that sentence, rounds on a ladder would break a rule that binds over a project's own. With it, no session sets a design apart by its own statement, and a project that calibrates nothing has no such rule (DEC-051 point 8). The rule's wording is its own, accepted with the landing change that adds each part.
- **Only the sessions that load it.** A loaded rule binds a session that loads its file, and a harness may start a helper that loads none (COR-070). Such a helper is bound by nothing here, and DEC-051 point 5 says so.

### 8. What never ships apart, and what a calibration's acceptance waits for

- **These records never without four things that follow them:** the designer's body, the passages on the reviewer and on what a session mends by itself in the skill that guides building a piece, the sentences on mending in the capability's reference page, and the rule's three asks that ship with them (point 7). All four change in one landing change, the one that accepts these records. No release carries the rule of one review and then the person (DEC-051 point 2) while the designer's body makes rounds by itself before a calibration, or while the skill tells a session that builds a piece itself to mend what the reviewer found.
- **What each of the four binds.** The body binds the designer alone. The skill guides a session that designs the piece itself, and the reference page tells a person what the designer will do. A session that runs the process with a designer and a critic it dispatched makes rounds that the designer never made by itself, and only the loaded rule binds that session. None of the four needs a command. So from the first day the rule holds in every session that loads its file (point 7), the body holds the designer, and the skill and the reference page say what both say. One thing waits for a command all the same: a named series of rounds, which does not run before the command that records it ships (DEC-051 point 3). The rule's passage on it ships with that command.
- **Their words are reviewed as these records are.** The body's, the skill's and the reference page's new words are part of the landing change that accepts these records. They go through the same reviews as the records before a person accepts that landing change.
- **No stage's command without the refusal after an uncalibrated review report** (DEC-051 point 5). A stage's command without it would run rounds under a reviewer nobody has tested.
- **No stage's command without the command that shows a landing change's causes and verdicts** (DEC-048 point 8). Where no component that carries out merges shows them, the landing change's author does. So each cause is seen beside its review report by somebody before the merge check exists.
- **The rule's six later asks never before the stage commands.** Three tell a session to run each stage through its command, and no project can switch the rule off (COR-070). Shipped earlier, they could not be kept. The stop names the stages, two of which have no command, body or skill text before. The passages on a named series and on a keep say nothing a session can use while no series runs and no keep is recorded.
- **The pass never without the question about library parts** (DEC-052 point 2), **and that question never without the command that records a person's finding on a library part** (DEC-052 point 3). Without that command, a fault known before any library was reviewed could not be made to count.
- **The merge check's command with the stage commands, and its place in a component's landing command never before that component's record decides it** (DEC-048 point 8).
- **No calibration is accepted before the designer's loop after it is decided.** This set decides nothing about the designer's loop after a calibration. What it does decide for that time is the critique's (DEC-049 point 5) and the library parts' (DEC-052 point 3). The landing change that accepts one decides how the designer's loop runs from then on, or a record accepted before it does (DEC-051 point 6).

## Rationale

**Why one process, with no lesser path.** The poor pages came from changes handed over as fixes. Each skipped the method and met only its own narrow criterion. A shorter path would be the one every hurried change takes, and whoever hands the change over would choose it.

**Why these stages, in this order.** The order is the designer's method (DEC-030 point 3) with what was missing around it. The system comes before the pages, since pages mended alone never read as one piece. The critique comes after the review, since the review serves the mending and the critique judges the result.

**Why the knowledge is no stage.** A stage must leave something a check can read. Reading leaves nothing. What can be shown is that the command put the knowledge, whole, in front of whoever designed. So the knowledge goes into two stages' instructions, and the piece has no position called "knowledge read".

**Why entry is computed from what each stage read.** A stage named by whoever makes the change is the lesser path again. Evidence tied to what a stage read falls when that changes, with no one deciding so. Tying each stage to what it read itself, and not to the whole piece, keeps a change of words from counting as a redesign.

**Why looking is free.** A designer who cannot draw a half-made page cannot design. Refusing a render would slow every stage and prove nothing.

**Why the person is told, and not asked, at the landing.** A person with no design knowledge cannot judge a verdict, and a sign-off asked at every landing is given by habit. So a piece with a pass lands without one, and the person keeps the decision only a person can make: to let through a piece that has no pass.

**Why the person is asked before each change after a review, until a calibration.** That is another question than a sign-off. Until the reviewer is calibrated, nobody has shown that a reading points the right way, so the person's word starts each change after a review or a reading, a mend of a slip and a corrected word among them (DEC-051 points 3 and 4). That word may be given by habit too. It does not check the reading. It keeps an untested reading from choosing by itself, and DEC-051 says what that is worth and what it costs.

**Why the pages first, and a picture with every finding.** The person is often no designer. A finding in words asks them to trust the reading it came from, and a list of findings with no page beside it asks them to choose blind. The pages let them judge the piece as a reader would, and the image lets them see at least what is blank, missing or overlapping. A command can tell only whether the pages were brought up, and refuses to record a word of the person's where they were not. That the person looked, the rule alone asks, and the record says so.

**Why before and after.** A count of rounds, or a list of findings mended, does not tell a person whether the pages got better. Two pictures side by side do, and comparing them needs no design knowledge. So a person who asked for rounds under an untested reviewer can see what the rounds did, and can go back. For every other showing the pages beside the new ones are those the person last kept. Compared with what was shown last, ten small steps could each look no worse while the whole got worse. The default branch's pages would move with every landing, whoever looked. A keep moves the baseline only once the person has said so, so ten named mends, each landed, are still compared with pages the person chose.

**Why a merge's authoriser is shown the pages.** A change that ends in a review needs no word of the person's to land. Without this, a changed piece could land with nobody shown its new pages, only verdicts and the images of failing grades. Whether the pages got worse shows in the pages.

**Why say what "skipped" means.** Commands and agents work under one account, so no refusal here stops an agent that means to break the process. Saying so keeps the promise true: a skipped stage is refused by the commands and seen at the merge.

**Why a stage run again may leave its result.** If every changed word of a goal redesigned every page, a correction would cost a redesign, and people would stop correcting goals. The stage still runs, with the knowledge in front of the designer. What it decides is the designer's.

**Why one role is called the person.** A named mend, a request and an acceptance each need one answer to "whose word". Where two roles could give it, an agent could take the word of whichever was easier to reach. Where several people hold one role, the same weakness stays inside that role, and point 6 says so.

**Why the rule states its terms itself.** A session that loads only the rule has never read these records. A rule that said "as the record lets the person ask" would bind such a session to words it cannot see, and a looser paraphrase would let through the loop the records refuse. So the rule carries each condition, briefly, and cites the point it comes from.

**Why three rules, each with one ask, and the rest later.** Every session of every project that installs the capability loads these rules, whether it designs or not. One rule that carried every condition put its second ask in its seventh sentence, under a lead that named only the first. Three rules give each ask its own lead. A passage no session can use before a command ships, such as the conditions of a named series, waits for that command, and costs no session its words meanwhile.

**Why some parts never ship apart.** Each would promise what only the missing part keeps. The records alone would say no round while the designer's body made two. The skill and the reference page, left as they were, would tell a session to mend what the reviewer found while the rule told it to hand the findings to the person, so the capability would give one session two instructions. The body alone would leave the session that runs the process free to run the same loop by hand. A stage command alone would run rounds, and one without the showing of causes would let a cause that nobody gave pass unseen. The asks that name commands, shipped alone, would name commands that do not exist. A pass alone would say nothing of the libraries, and one that asked about them with no way to write a known fault down would let that fault through. A check that a component's landing command ran before that component's record decided how would join a gate by a way nobody decided.

**Why a calibration's acceptance waits.** Once a reviewer is calibrated the designer's loop runs on its findings, as the accepted records have it. Whether that is right under a calibration over a few rules is best judged with such a reviewer's reports in hand. Holding the acceptance until it is decided keeps that question from being passed over.

### Alternatives considered

- **The method kept as the agents' instructions alone.** Rejected: that is what failed.
- **A shorter path for small changes.** Rejected: whoever hands a change over would choose it.
- **The stage a change enters at named by its author.** Rejected: the lesser path again.
- **A stage for reading the knowledge, with citations a check matches.** Rejected: a citation is cheap to write unread, and the check would be a match of words.
- **Every change runs every stage.** Rejected: a typo would count as a redesign.
- **The person signs off every change at its landing.** Rejected by whoever maintains the capability: acceptance by habit, and no piece would be made alone. The word that starts a change after a review is another thing, and is asked only until a calibration (DEC-051 point 4).
- **The default branch's pages as the one baseline.** Not taken: they move with every landing, so ten named mends, each landed, would each be compared with the one before.
- **One loaded rule that carries every condition.** Not taken: it ran to several times the length of a core rule, in every session, and hid its second ask.
- **A short loaded rule, with its terms defined in the capability's reference page.** Not taken: a session that did not read the page would be held by words it cannot see.
- **A changed intent redesigns every page.** Rejected: a corrected word in a goal would cost a redesign.
- **A render refused until the earlier stages have evidence.** Rejected: it throttles looking, which is how a page is designed.

## Implications

- **Edits made in this record's landing change, once this record is accepted,** each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-030 point 8, "Read by need":** the system stage and the pages stage are given every topic, in the instructions their command writes. A change that enters at the drawing or later reads by need (points 2 and 4).
  - **DEC-029 point 1, "Optional":** drawing and checking a piece need no brief, and the design process needs one from its first stage.
  - **DEC-042 point 6, "Then the person":** the critique follows the loop's end, the person is told at the landing, and each grade handed over comes with its image (points 2 and 6).
- **Read against this record, and left as they stand:**
  - DEC-030 point 2, which another record overturns in part until the reviewer is calibrated, and which stays as it stood (DEC-051, Implications). This record takes nothing from it. What it adds about the designer is decided here: the designer changes a piece's drawn pages only through the process (point 1), its stop ends the review stage and never the process (point 2), a stage that cannot run goes to the person (point 5), and what it puts to the person comes with its image (point 6);
  - DEC-029's summary and Decision line, "a piece may keep a brief", since a piece that no change has taken through the process needs none (DEC-048 point 10);
  - DEC-030 points 1 and 5, since the capability keeps two design agents, with their writes and boundaries;
  - DEC-042 points 1, 2 and 4, since the review grades as before, and point 10 but for the bullet DEC-051 refines;
  - [visual-communication:DEC-028-principles-of-visual-communication], since no rule binds on a piece by this record;
  - DEC-003 point 8, since a lock moves as before, and a move is a change that enters at the system, where the designer may leave the system as it stands (point 4).
- **A loaded rule, proposed in the capability's loaded set.** Its three asks that ship with these records are added in this set's own landing change, as three rules, and its six later asks in the landing change that ships the stage commands. Each rule has its own origin, and anchors on every point it cites. Each part's wording lives in the rule, where a person accepts it. It carries what point 7 lists and ships as point 8 says. It binds every session of a project from the release that ships it, and a project cannot switch it off (COR-070).
- **Shipped with these records, never after them:** the designer's body that stops after one review until the reviewer is calibrated, the passage on the reviewer in the skill that guides building a piece, the reference page's sentences on mending, and the rule's three asks that ship with these records (point 8).
- **Work once this record is accepted,** each in a later landing change:
  - the process definition, bound to the methodology's process substrate (COR-033). Its states are the work's to choose, and need not be one for each stage. Its gates rest on computed evidence alone, and the commands' refusals stay the capability's own (DEC-048 point 6). A piece's position is detected through the substrate's own detection for one subject. The stage commands, the report on drafts and the merge check each ask that detection, piece by piece, and none builds a second one (DEC-048 points 6 to 8);
  - in that definition, a piece that waits for the person's word is shown as waiting on a person. One refusal of the stage commands is lifted by the person's word alone: the cause after an uncalibrated review report, under which every change to the piece after such a report waits (DEC-048 point 6; DEC-051 point 4). The definition's route for it is the substrate's wait on a person, a move only a person takes, with the question it puts (COR-034). The showing of that report's pages and findings is part of the question, and no wait of its own, since running the showing command lifts its refusal. That adds no gate on recorded evidence, since whoever calls the engine holds the move to a person, and the engine does not. The position then says that the piece waits on the person, and for what;
  - the reviewer's body, and the rest of the designer's body and of the skill that guides building a piece, rewritten to the stages;
  - the rule's six later asks, and the capability's reference pages;
  - the design knowledge: a topic on a piece's design system, and worked lessons in each topic that show a weak form beside a strong one.
- **Left open:**
  - whether one piece is drawn under more than one brand, which the record of brands decides ([visual-communication:DEC-004-brands-and-notations]). Each brand would then be a variant.
- **No migration.** The process adds to what a piece may hold, and a piece from before it reads as before (DEC-048 point 10).
