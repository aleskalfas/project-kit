---
id: DEC-048
title: Each stage of the design process leaves evidence, and a piece without it is refused
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** each stage of the design process leaves *evidence*, tied to the exact files the stage read. A piece has a *pass* when every stage's evidence matches its files, and three more things hold that point 4 lists. The capability's commands refuse to run a stage whose earlier stages left none. A project's merge gate refuses a landing change whose pieces have no pass, and shows each verdict and the changed pages. Validation fails only what readers receive, and a report of its own says where each draft stands. Four limits are part of the decision. Commands write the evidence under the same account the agents use, so it catches a stage skipped by mistake or in haste, and stops no agent that forges it. For the same reason the refusals are the capability's own, and nothing shows them as a gate that another authority holds. What a pass asks about a piece's libraries refuses nothing until a library has been reviewed. And the merge check is a command of the capability's own, which a project may require in its pipeline. Only its place in a component's own landing command waits for that component's record.

## Context

The design process orders a piece's stages, and says no agent skips one ([visual-communication:DEC-047-design-process]). Agents run the stages, and an agent's word that a stage ran costs nothing to write. So the process needs something a command can read, and places where a piece without it is refused.

Whoever maintains the capability chose how hard "cannot skip" is: refused at the capability's commands and at the merge, with attention on a draft and a failure for what readers receive. A stronger form, evidence rewritten by a separate identity such as a build pipeline, is later work.

Three accepted rules bound the choice. Validation fails nothing for a subject in motion, or for what the project cannot correct in its files (COR-055 point 1). A reading of taste never fails ([visual-communication:DEC-002-files-and-validation] point 7). And a gate is sound only on a predicate the process engine works out, or on a trace the gated actor cannot write (COR-033 point P4). The last decides what the refusals here are (point 6).

## Decision

**Each stage leaves evidence tied to what it read. The commands refuse a stage without the earlier evidence, the merge gate refuses a landing change without a pass, and validation fails only what readers receive.**

### 1. Evidence is tied to what the stage read

- **By fingerprint.** Each stage's evidence carries a fingerprint of what that stage read (DEC-047 point 4), in the form every fingerprint of the capability takes ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] points 5 and 6). It reads values, not versions, and a section of a file by its keys. So an edit elsewhere in a file changes nothing.
- **Stale counts as absent.** Evidence whose fingerprint does not match the files is *stale*. The stage then has none.
- **Noted, never compared.** The evidence also notes what the stage ran with: the design knowledge and the reviewer's definition, each by a digest, the model, and the engine's version. A piece's evidence never goes stale by them, or every upgrade would send every piece of every project back to its first stage. Whether the reviewer may be relied on is another record's question ([visual-communication:DEC-051-no-reading-chooses-before-calibration]).

### 2. Three kinds of evidence, by who can vouch for it

- **Computed.** A command works it out again on every read, from the piece's files alone, as they are. It is a property of the work itself: that the brief's intent is complete, that the brief's part for a page is filled in, that the check finds no failure. Where that part holds a reason, such as why one form was chosen over another, what is computed is that the reason is written, and never that anything was weighed. Nothing is stored, and nothing can be claimed. Evidence is computed wherever it can be.
- **Recorded.** An entry that says something happened: that a command started a stage with the instructions it wrote, that a draft was shown, that the pages were brought up. Nobody witnessed it: the account that did the work wrote the entry. That is so whether a command wrote it or an agent did, and whether it lies in the evidence or in one of the piece's own files, as the brief's record of drafts does. It shows that a step was taken. It never shows that the work was done well. Evidence worked out from such an entry, or from a report that an actor recorded, is recorded evidence too, wherever and whenever it is worked out.
- **One stage may leave both.** Point 3 says of each stage which half is computed and which is recorded.
- **The person's.** An entry a command writes once the person has said so: an acceptance (point 4), what the person asked for (DEC-051 point 3), or a keep (point 3).

Recorded evidence is written under the account the agents share. So it is no trace of another authority, this record never calls it one, and no gate of the process definition reads it (point 6).

### 3. What each stage leaves

- **Intent, computed:** the brief's intent is complete for the piece and for each page.
- **Intent, recorded:** two entries, neither of which shows that the asker read anything.
  - The command that shows the asker the brief's goals and relations records that it ran, for the goals and relations as they then stood ([visual-communication:DEC-047-design-process] point 2).
  - The brief's record of drafts lists no draft the asker has not seen. The designer writes that record by hand, and clears a draft once the asker has seen it ([visual-communication:DEC-042-grades-bar-and-loop] point 7).
- **System and pages, computed:** the brief's part for the system, or for the page, is filled in ([visual-communication:DEC-050-piece-design-system]; [visual-communication:DEC-030-design-agents] point 3). Each page's evidence also names the system's fingerprint, so a changed system makes every page stale.
- **System and pages, recorded:** the stage's command writes the stage's instructions for the designer. They carry the design knowledge whole, the piece's intent, and the libraries the piece draws on. The command records the digest of what it put in, and that it started the stage.
- **Drawing (recorded):** which variants were drawn, for the fingerprint of what they were drawn from.
- **Check (computed):** the check's result.
- **Review (recorded):** the review report in its fixed form (DEC-042 point 4), which names the model and the effort the review ran on. While the reviewer is not calibrated in the project, the review report is recorded before any agent acts on it (DEC-051 points 1 and 2). The command refuses a review report that leaves out a page or a variant, or that places a fix in a library without naming the library part ([visual-communication:DEC-052-library-parts-open-findings] point 3).
- **Critique (recorded):** the verdict, whole, as [visual-communication:DEC-049-critique-step] gives it. Until the reviewer is calibrated a command reads it from the review report. That report is recorded evidence, so the verdict read from it is recorded evidence too. Once the reviewer is calibrated the verdict is recorded from the critique's own reviewer's run.
- **The review's and the critique's entries** also say whether the reviewer was calibrated for that reviewer's run, and under which calibration (DEC-051 point 1). So a pass names the calibration it was made under.
- **What caused a change.** A named mend, a request in the person's own words, a work item approved after the review report and a named series of rounds are recorded on the person's word, each after the review report it follows. Nothing else is recorded as a cause (DEC-051 points 3 and 4).
- **The showing (recorded):** the command that shows the person a review report's pages and findings records that it ran, for that report. The entry says that the pages were brought up, and never that the person looked ([visual-communication:DEC-047-design-process] point 7). Beside the pages the command draws the same pages as they stood when the person last kept them (DEC-047 point 6).
- **A keep (the person's).** The showing command records each keep once the person has said so, with the state of the piece's files that the person kept. An acceptance, and the kept result of a named series, count as one. Where no keep is recorded, the command draws the default branch's pages, or nothing where the piece is new there. So the baseline moves only once the person has said so, and a slow drift across many named mends shows against it.
- **Where a named series started (recorded).** The command that records a named series of rounds notes the state of the piece's files at that moment. The stage commands keep that state reachable until the series ends. So its first pages can be drawn beside its last, and the piece can be put back to where the series started. No series runs before this command exists (DEC-051 point 3).
- **Only what cannot be worked out again is stored.** The images stay in the clone's local folder ([visual-communication:DEC-015-viewing-step-and-reviewer] point 4). The evidence says what was drawn and read, and carries no picture.

### 4. A pass, and the person's acceptance

- **A pass.** A command makes a piece's *pass* where all of these are true. This list is the whole definition, and the records it cites define its terms only.
  - Every stage's evidence matches the piece's files as they are.
  - Where the critique's verdict decides, it meets the level the accepted calibration's bar asked, on the covered rules. It decides where the reviewer was calibrated for the critique's own reviewer's run, and that bar asked the professional level (DEC-049 point 5). Everywhere else the verdict informs, and this condition asks nothing.
  - While the piece's last review report is an uncalibrated one, and the reviewer is not calibrated in the project, each change made to the piece after that report carries its cause: a word of the person's that starts a change, given after that report (DEC-051 point 4). The critique of the files that report read belongs to the change the report closed, and needs no cause (DEC-051, Decision). At any other time this condition asks nothing.
  - At that moment, no library part the piece uses has an open finding, as DEC-052 point 3 defines one (DEC-052 point 2).
- **What the pass notes.** The calibration it was made under, or that there was none, and the state of each library part the piece uses, by the part's digest.
- **For one state of the files.** A pass stands for the files it was made from, and for no later change.
- **It is not taken back by what happens elsewhere.** A withdrawn calibration, or a finding that appears later on a library part, asks for attention on the piece and removes no pass (point 7).
- **An acceptance is apart from a pass.** The person may let through a piece that has no pass (DEC-047 point 6). The acceptance names the files' fingerprint, the last verdict it was given over, each stage that had no evidence, and each open finding on a library part that kept the piece from a pass. The person is shown each such finding with its image before accepting, so no piece is let through on a part its owner held back without the person being told why it had no pass. It covers those files and no later change.
- **Written on the person's word.** A command writes it. An agent runs that command only once the person has said so, as an agent writes a record's acceptance only on a person's word (COR-064 point 6). The command refuses where the pages were not shown first (point 6).
- **Wherever this record asks for a pass,** an acceptance for the same files serves.

### 5. Where the evidence lies

- **Committed with the piece,** among what commands write and apart from what people write (DEC-002 points 5 and 9).
- **No file that two changes both edit.** Evidence is kept so that two changes to one piece never rewrite one file, as answers on artefacts are kept (COR-062).
- **A format number from its first version,** so a later move of the evidence is a migration that can be written (COR-010).
- **A process mark in the piece's own file.** A piece that stands in the process says so in its own file, in the lines commands rewrite. So evidence that was removed shows as missing, and never as a piece from before the process (point 10).
- **The rest is the work's, but for one name.** The files' shape, names and schema are the choice of the work that builds them. It takes no file name that another capability's validator claims. The capability that keeps citations reads every file that carries its evidence file's name as a scope of citations, so a file of that name here would be read as one. The word "evidence" names something else there: a source a claim cites, and nothing a stage left.

### 6. The commands refuse, as the capability's own precondition

- **A stage's command asks first.** Each stage has a command that carries it out or records it. It refuses where an earlier stage's evidence is missing or stale, and names the stage the piece stands at.
- **Where a piece stands is detected once.** The process definition detects a piece's position from its files and its evidence, through the methodology's process engine (DEC-047 point 4). A stage command, the report on drafts and the merge check each ask that one detection, and none works a position out again. So the position a piece is shown at and the position a command reads never disagree.
- **A command may still refuse a move the position lists.** Two refusals below lie outside the definition: the cause after an uncalibrated review report, and the showing. Only the first is lifted by the person's word alone, and under it every change after such a report waits for that word (DEC-051 point 4). The work that builds the definition shows such a piece as waiting on a person, through the substrate's own wait, and the showing is part of the question that wait puts (COR-034; DEC-047, Implications). The showing refusal is lifted by running the showing command, which is no act of the person's, so it is no wait of its own. Until the definition shows the wait, the stage command's refusal is where a session learns of it.
- **Started through the backbone's runner where a command starts an agent.** A command of the capability starts an agent only through the runner the backbone gives commands for that, which the project's adapter registers (the adapters README, "The agent runner"). On that path the command sets the effort the agent runs at. It sets no model: a runner's request has no key for one, and a runner refuses a key it does not know. Where a harness lets only a session start an agent, the command sets neither. So on every path the command learns the model only from the agent's report (DEC-051 point 1).
- **The refusal is the command's own.** A stage command declines to run from where the piece stands. That is a precondition of the capability's command. It is no gate of the process definition, and nothing shows it as a gate that another authority holds.
- **No gate of the definition reads recorded evidence.** Recorded evidence and the person's entries are written under the account the agents share, so neither is the trace of another authority that a gate needs (COR-033 point P4). A gate of the process definition rests only on computed evidence (point 2). Where a stage leaves both kinds, a gate may read its computed half and never its recorded half. So a gate on the intent stage reads that the brief's intent is complete, and never that the asker saw it. The critique stage's evidence is recorded, before a calibration and after it (point 3). So no gate of the definition rests on the critique stage at either time.
- **The critique's verdict decides through the capability's commands.** The command that makes a pass reads it (point 4), and the commands that write readers' copies ask for that pass. The definition has no gate on the verdict.
- **After an uncalibrated review report.** While a piece's last review report is an uncalibrated one, and the reviewer is not calibrated in the project, a stage command runs for that piece, on files changed since that report, only once the change's cause is recorded: a word of the person's that starts a change, given after that report (DEC-051 point 4). The critique that follows the review runs on the files the report read. It is the last stage of the change that report closed, so this refusal never catches it, and every piece can get its pass before a calibration.
- **Where the pages were not shown.** The command that records a named mend, a request in the person's own words, a work item approved after the review report, a named series of rounds or an acceptance refuses where the command that shows the person the pages and the findings was not run for that review report. For an acceptance of a piece with no review report, it asks that the pages were shown for the files the acceptance names (DEC-051 point 3). The command that records an acceptance of a library part, or takes back a person's finding on one, refuses where the image of that part, as it then is, was not brought up ([visual-communication:DEC-052-library-parts-open-findings] points 3 and 4).
- **Readers' copies.** The command that publishes a piece, an export that writes a published piece's current copy, and the command that makes a piece final each refuse without a pass. The pass is asked for the files the copy or the version was made from. So making a piece final takes the version named, whatever changed since ([visual-communication:DEC-017-final-and-published-states] point 1). Each such command writes, with the copy, which pass or acceptance it was made on.
- **An export of a draft runs.** A numbered version is local, and the person may need it to judge the piece (DEC-006 point 7).
- **A piece that is not in the process** is refused nothing, the publishing of it included (point 10). Only the merge check makes such a piece enter, where a project runs it (point 8).

### 7. Validation fails only what readers receive, and a report of its own says where each draft stands

Two things read a piece's state, and they are kept apart. A validator reads what readers received, and walks nothing. A report on drafts asks where each piece stands, and is no part of validation.

The validator, apart from the capability's check:
- **What readers receive fails without a pass.** For a piece that carries the process mark, that is a published piece's current copy, or a version handed out, whose own entry names no pass and no acceptance for the files it was made from.
- **That one failure walks nothing.** It is read from the copy's own entry and the piece's files, as a stale output is (DEC-002 point 7). It asks the engine for no position. The project mends it in its own files: by a pass, or by the person's acceptance.
- **A readers' copy whose pass something later touched asks for attention.** That is a pass made under a withdrawn calibration, which names the calibration (DEC-051 point 7), and a pass whose library part has since gained a finding, which names the part (DEC-052 point 2). It is read from what the pass notes, the calibrated data and the library's state, and walks nothing. It fails nothing.
- **A piece that is not in the process** is never failed. A copy of it that names no pass is as it was before the process (point 10).
- **What the machine lacks never fails.** Where no browser starts or the harness reads no image, the stage stops and reports it (DEC-002 point 7). The person's acceptance needs neither.

The report on drafts:
- **A command of its own, or a part of the capability's status command.** Which of the two is the work's to choose. It is no validator, since validation keeps reports on subjects in motion out, as commands of their own (COR-055 point 1). So it can never fail a project's validation, by what it finds or by the time it takes.
- **It asks the engine, piece by piece.** For each piece it asks the process engine where that one piece stands (point 6), and works nothing out again. Nothing rides on what it says.
- **A draft without a pass asks for attention,** and names the stage it stands at, or the library part with an open finding (DEC-052 point 2). So does a draft whose pass something later touched, as above.
- **An answer the engine cannot give asks for attention too.** Where the engine's answer for one piece is indeterminate, the report says so for that piece, goes on to the next, and fails nothing.
- **A piece that is not in the process** states a fact, and asks nothing.

### 8. The merge gate refuses a landing change whose pieces have no pass

A *landing change* is what a project lets through to its default branch as one unit. It may hold changes to several pieces. This point names it in full every time, since *a change* alone is a change to one piece (DEC-051, Decision).

The capability ships a *merge check*: a command that compares a landing change with its base, and refuses one whose pieces have no pass. It compares two states, so it is a command of its own and no validator (COR-055 point 2). It is no gate of the process definition (point 6). It adds a refusal and authorises nothing, so the merge stays authorised as the gate's own component decides, and the gate rule holds there (COR-033 point P4).
- **A pass at the landing change's head,** for each piece the landing change reaches. A piece from before the process that it reaches must enter the process (point 10).
- **Asked of the engine, piece by piece,** as the report on drafts asks (point 7). One thing differs. Where the engine's answer for a piece is indeterminate, the check refuses, as it does where it cannot run, since it feeds a gate. The report on drafts only asks for attention there.
- **Which pieces a landing change reaches.** A landing change *reaches* a piece where it changes something a stage of that piece read (DEC-047 point 4): the piece's own files, content it shares with other pieces, or a library part it uses, through its lock. A command computes this from the fingerprints. A landing change that touches the engine alone reaches no piece, since the engine's version is noted and never compared (point 1). The engine's own tests answer for what it draws.
- **It judges a head.** Two landing changes whose pieces each have a pass can merge into files nobody gave a pass. The piece on the default branch then has no pass, and asks for attention as any draft does (point 7).
- **A calibration's ladder needs no pass.** A *ladder* is the series of designs a calibration grades. The gate shows it as a ladder, and checks its ladder mark (DEC-051 point 8).
- **No live evidence removed from a piece that stays.** A piece's *live evidence* is what its position and its last pass or acceptance read. The check refuses a landing change that removes a piece's process mark or its live evidence while the piece stays. The rest may be pruned, as answers on artefacts are (COR-062), or every run would add files for ever.
- **A piece removed whole.** A landing change may delete a piece with its process mark and its evidence. The gate shows it as a piece removed. What a published or final piece may do is its own record's (DEC-017).
- **Each verdict shown.** Whoever authorises the merge sees each piece's last verdict, each acceptance the landing change records, and each cause with the review report it follows (DEC-051 points 3 and 4). A failing grade is shown with its image (DEC-047 point 6). A command lists them, and it ships with the stage commands (DEC-047 point 8). The component that carries out merges shows its output or, without one, the landing change's author does.
- **The changed pages shown.** Authorising a merge that changes a piece's drawn pages is a decision about them (DEC-047 point 6). So the same command draws, for each piece whose pages the landing change changes, those pages beside the baseline: the pages the person last kept or, where no keep is recorded, the default branch's (point 3). A change to a piece that ended in a review needs no word of the person's to land, so without this nobody need have seen its new pages.
- **This showing is the one check by another authority.** Where no component shows it, it rests on the author's word, as the list of what a landing change makes accepted does (COR-066 point 3).
- **Whose word counts.** What the person decided about a piece is the person's, and whoever authorises the merge decides whether the landing change lands (DEC-047 point 6).
- **The check is the capability's, and where it plugs in is the gate's owner's.** The check command is built with the stage commands, and depends on no other capability. Two things are kept apart:
  - **Any project may require it.** A project wires the command into its pipeline as a status each landing change must have, as a project makes the documentation check a required status ([project-management:DEC-053-doc-check-slot] point 3). That needs no record of any other component. Where the command cannot run, it refuses, since it feeds a gate.
  - **A component's own landing command waits for that component's record.** A gate belongs to whoever runs it (COR-057, Rationale), and a component takes what others contribute through a point that it owns (COR-052 point 1). So how a component that carries out merges runs this check itself, and what it shows of it, is that component's to decide, in a record of its own and in the form it chooses. This capability asks three things of that record: that a capability can address a role, and depend on no component that fills it; that a contributed check which cannot run refuses; and that the gate judges a head. A point of that kind already takes a landing change's documentation obligations ([project-management:DEC-053-doc-check-slot]).
- **A project that does not run the check** keeps the commands' refusals, validation, the author's showing and the session's rule (DEC-047 point 7). There, only the rule stops a landing change that is committed and pushed. Three things in this point act only where the check runs: the refusal of a landing change without a pass; the ladder mark's refusals; and making a piece from before the process enter it. Two things need no check. The stage commands refuse a change to a piece that has no cause (point 6). And the showing is given by the landing change's author, from the command's output.

### 9. What nothing prevents

- **A forged entry.** An agent that writes evidence by hand, or records a review report nobody wrote, breaks the session's rule. No check tells its entry from a true one.
- **A reading done badly.** Recorded evidence shows a stage ran, never how well.
- **A loop outside the commands.** A loop run by hand, or steered by another critic, leaves the evidence of one run (DEC-051 point 5).
- **A library nobody reviewed.** It refuses nothing (DEC-052 point 7).
- **A piece nobody enters.** Where a project does not run the merge check, nothing makes a piece from before the process enter it. Such a piece is refused nothing, the publishing of it included (points 6, 8 and 10).
- **A session that loads no rule.** The session's rule binds only a session that loads its file, and a harness may start a helper that loads none (COR-070). What only the rule holds, nothing holds there.
- **A showing nobody looked at.** A command can tell that the pages were brought up, and never that the person looked (DEC-047 point 7).
- **What this gives.** A stage skipped by mistake, by haste or under a narrow task is refused by the commands, and seen at the merge. Resisting an agent that forges on purpose needs a channel agents do not have, which is later work.

### 10. A piece from before the process

- **It stays as it is.** It carries no process mark, and no command or validator refuses or fails it.
- **It enters at its first change.** One of two ways: the process runs whole, from the intent, or the person accepts the piece as it stands. That acceptance stands in for the stages before the drawing, for the files it names. Later changes then enter where DEC-047 point 4 says.
- **A published piece that enters has its current copy written again.** Once a piece carries the process mark, its readers' copy fails where the copy's own entry names neither a pass nor an acceptance (point 7). So the landing change in which a published piece enters the process writes its current copy again, on the pass or the acceptance the piece enters by. No copy published before the process fails unless its piece enters.
- **A new piece** takes its process mark from the command that starts it.

## Rationale

**Why evidence a check can read.** An agent's statement that a stage ran costs nothing. A fingerprint says exactly what a stage read, so an edit makes its evidence stale with no one deciding so.

**Why say which evidence is only recorded.** Three things can be worked out from the piece's files alone: the check's result, that the brief's intent is complete, and that the brief's part for the system or for a page is filled in. Each is a property of the work, and no claim that a step was taken. Everything else says that something happened. That the asker was shown the goals and relations, and that the asker has seen each draft, are such claims, the second written by the designer's own hand in the brief. The drawing's coverage is one too, since the images stay in the clone's local folder (point 3). These are an actor's note that a step was taken, and a gate that read one would pass on the gated actor's own word. The critique's verdict before a calibration is worked out by a command, but from a report that an agent's account recorded, so it is vouched for no better than that report and is recorded too. Calling that a trace of another authority would turn "run" into "judged". Named honestly, it does its job: the stage that was left out shows.

**Why the knowledge is sealed in instructions the command writes.** A reason that cites a topic can be written without reading it, and a check that matches the citation matches words. A command that puts the knowledge whole into the stage's instructions, and records that it did, shows the one thing that can be shown.

**Why one detection of where a piece stands.** A command with a detection of its own beside the process definition would be a second machine, and the definition a picture of it. One detection, asked by the command, the report on drafts and the merge check, cannot disagree with itself.

**Why the refusals are the capability's own, and no gate of the definition.** The process substrate's gate rule asks for a predicate the engine evaluates, or a trace made by another authority than the gated actor (COR-033 point P4). Evidence a command recorded under the agents' account is neither, and a capability's record cannot change a rule of the core. So the definition keeps its gates to what is computed. The refusals on recorded evidence are named as what they are: a command of the capability declining to run. Should the core decide that such evidence may feed a gate, the definition can take the refusals over. Should it decide otherwise, nothing here has claimed more than it holds.

**Why a draft never fails, and why its report is no validator.** Every half-made piece would otherwise fail the project's validation, its hooks and its pipeline. Mending it needs a browser, a harness that reads images, two agents and sometimes a person. Validation fails nothing the project cannot correct in its files at once. A report that asks the engine about every piece, one at a time, is also slow where a project holds many, and a validator that overruns its time is a failing finding (COR-055 point 6). Inside validation, a report meant never to fail could fail it by taking too long. As a command of its own it cannot.

**Why the merge check is apart from where it plugs in.** The check compares a landing change with its base, which is the capability's own knowledge. Which gate runs it is the gate's owner's. Kept together, the check would wait for a record of one component, and a project without that component would never get it. Kept apart, any project can require the command in its pipeline at once, and the component that carries out merges takes it up when its own record says how.

**Why what readers receive fails, and how.** A copy that readers see is no subject in motion. That it was made from files with a pass is a fact about the copy and its files, which the project mends by a pass or by the person's acceptance. Reading it from the copy's own entry keeps the one failure off a walk through every piece. Where the critique's verdict decides, a pass rests on it (point 4), so a reading does reach validation here, through the pass and for readers' copies only. Whoever maintains the capability chose that, and the records that keep readings out of validation say so (Implications).

**Why a pass is not taken back.** A pass that vanished when a library gained a finding, or a calibration was withdrawn, would fail a published copy with no change to the piece, and for something the project cannot mend at once. Noting what the pass was made on, and asking for attention when that changes, tells the project the same thing and fails nothing.

**Why an acceptance is apart from a pass.** Folded into the pass, an acceptance would read as "judged good". Kept apart, the merge shows which pieces have a pass and which the person let through.

**Why a process mark in the piece's own file.** Without it, deleting the evidence would turn a piece that failed into a piece from before the process, which fails nothing.

**Why evidence the capability keeps, for now.** The methodology has no shared store for evidence tied to content. The capability keeps its own, with a format number, so that a core record can take the store over later by a migration.

**Why a piece from before the process may enter by acceptance.** Its first change would otherwise be a redesign, however small. The person, who alone lets a piece through, takes it in as it stands.

### Alternatives considered

- **A stage's evidence as the agent's own report.** Rejected: it costs nothing to write.
- **Validation that fails every piece without a pass.** Rejected: it fails subjects in motion, against COR-055 point 1.
- **Validation that fails nothing.** Rejected by whoever maintains the capability: what readers receive must have a pass.
- **Refusals in the commands alone, or at the merge alone.** Rejected: the first leaves a hand edit unseen, and the second gives a project without a merge gate nothing.
- **The report on drafts as a validator.** Rejected: a report on subjects in motion belongs outside validation (COR-055 point 1), and one that walks every piece could fail validation by overrunning its time.
- **The merge check built only once a component's record decides its place.** Rejected: the check is the capability's own command, and a project can require it in its pipeline with no such record.
- **Each command computing its refusal from the fingerprints itself.** Rejected: a second reader of where a piece stands, beside the process definition.
- **The refusals as gates of the process definition.** Rejected: a gate would then rest on evidence the gated actor's account wrote, against COR-033 point P4.
- **A pass read live against each library part's present state.** Rejected: a pass would vanish with no change to the piece.
- **One evidence file for each piece.** Rejected: two changes to one piece would conflict on it.
- **Evidence in the clone's local folder.** Rejected: no gate on another machine could read it.
- **Export refused without a pass.** Rejected: the person may need the export to judge the piece.
- **Evidence written by a separate identity,** such as a build pipeline that draws and checks again. Not taken yet: it is the stronger form, and later work for what such a pipeline can run cheaply.
- **The review's brief findings as a gate on the reasons.** Not taken: a brief finding is never a covered finding (DEC-051 point 1).

## Implications

- **Edits made in this record's landing change, once this record is accepted,** each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-002 point 5:** the design process's evidence, and the process mark in the piece's own file, are among what commands rewrite. **Point 6:** the validator of readers' copies stands apart from the check, and the report on drafts is no validator. **Point 7, "What fails":** for a piece that carries the process mark, a published piece's current copy, or a version handed out, fails where its own entry names neither a pass nor the person's acceptance. A piece without the mark is never failed for it (point 10). **"A reading of taste never fails":** the lead stands as accepted, and three sentences are added. The failure of a readers' copy is read from the copy's own entry, and is no reading. A reading reaches validation only through what a pass needs, which point 4 states. A draft without a pass fails nothing (points 4 and 7).
  - **DEC-042 point 8:** the verdict the loop reads joins no validation. The critique's verdict has a place at the merge and behind readers' copies, by this record and DEC-049.
  - **DEC-015 point 7, "Advice, for now", and DEC-030 point 6, "Advice":** the findings of the designer's loop stay advice. The critique's verdict is shown at the merge and, where it decides, a pass needs it (point 4).
  - **DEC-017 point 2:** making a piece final refuses a version made from files with no pass and no acceptance, for a piece in the process. **Point 3:** recording the person's acceptance of the version handed out is a fourth act on a final piece.
  - **DEC-006 point 7, "The export's gate":** for a piece that carries the process mark, an export refuses to write a published piece's current copy from files with no pass and no acceptance of the person who answers for the piece, and writes with the copy which of the two it was made on. **Point 8, "They fail validation":** for such a piece, a copy whose entry names neither fails. A copy of a piece without the mark is never failed for it. **Point 8, "They ask for attention":** a readers' copy whose pass was made under a calibration since withdrawn, or whose library part has since gained a finding, asks for attention and fails nothing (point 7).
  - **Each of the edits that fail a copy is scoped to a piece that carries the process mark,** as DEC-017's is. Read without that scope, each would fail every copy published before the process, against point 10 and against the rule that existing debt never fails (COR-055 point 1). The words of each are the pull request's to show whole, and accepting this record accepts them.
- **Read against this record, and left as they stand:**
  - COR-033 point P4, the rule that a gate needs a predicate the engine evaluates or a trace by another authority. This record keeps it: no gate of the process definition reads recorded evidence, the recorded half of a stage's evidence included, or evidence worked out from it. Only three things are computed: the check's result, that the brief's intent is complete, and that the brief's part for the system or a page is filled in (point 3). The commands' refusals are the capability's own preconditions (points 2 and 6);
  - DEC-017 point 1, since the pass is asked for the version's own files;
  - DEC-015 points 1 to 6, since the viewing step writes nothing committed.
- **What a project sees on upgrade.** Nothing changes for an existing piece until it next changes. Its first change then needs a whole run or the person's acceptance. Where that piece is published, the same landing change writes its current copy again (point 10). A new piece is different: once the stage commands ship, it takes its process mark from the command that starts it, and publishing it then needs a pass (point 10). The release that ships the refusals says both in its notes.
- **A harness requirement.** A pass needs a harness that reads images. A project's harness that reads none is reported as such, and fails nothing (COR-047).
- **Work once this record is accepted,** each in a later landing change:
  - the evidence: its schema, its fingerprints, the process mark, and the commands that write each entry, the person's among them;
  - the instructions each stage's command writes for the designer;
  - the command that makes a pass;
  - the command that shows the asker the brief's goals and relations, and records that it ran;
  - the command that shows the person a review report's pages and findings beside the baseline and records each keep, the keeping of a named series' starting state, and the command that lists a landing change's causes and verdicts and draws its changed pages beside the baseline;
  - the validator of readers' copies, and the report on drafts;
  - the refusals of the commands that publish, write a current copy and make a piece final, and the entry each writes with the copy;
  - the merge check's command, built with the stage commands;
  - the merge check's place in a component's landing command, once that component's record is accepted.
- **Left open:**
  - **what an evidence commit trips.** Evidence is committed with the piece, so each run of the stages ends in a commit that moves the head. Unless a project exempts it, that commit does three things, each with its own owner: it makes reviewers' verdicts on the landing change stale, which the owner of the merge gate decides; it runs a project's pipeline again, which the project decides; and it can flag anchors on the paths it touches, which the record of the friction checks decides (COR-050 point 5). Until each has answered, a design run under a merge gate stales every review of its landing change;
  - a core refinement that decides whether evidence a command records under the gated actor's account may feed a gate of a process definition. It is proposed where the core is kept, and until it is accepted no gate reads such evidence (point 6);
  - a core record on evidence tied to content, which may take the store over;
  - evidence written again by a build pipeline, for the drawing and the check. For the drawing the route is nearer than for the rest: a project's pipeline may already draw every piece on each change it checks ([visual-communication:DEC-024-outside-programs-sandbox]);
  - whether the review's own findings block a merge, which stays [project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)'s.
- **No migration.** The evidence and the process mark are additions, and a piece without them reads as before (COR-010).
