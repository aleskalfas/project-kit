---
id: DEC-065
title: A change's answers are derived from the change check, not read from its pull request's description
status: accepted
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a pull request's description no longer carries a list of the answers its change wrote. Whoever needs the answers derives them from the change check at the pull request's head. The reviewer of the answers, the move to review and the landing command each do so, and one command prints them for anyone else. Away from a clean checkout of the head, that command starts nothing the head holds. So on a project whose anchors need such a program, it prints no answer on any change. The author still writes one sentence on what changed in each updated document. The other merge commands and the host's button print no answer, so on such a project a person who merges there is told only the sentences, which falls short of what that person is owed (point 6).

## Context

[project-management:DEC-055-pr-lists-answers] has this capability write the change check's list of the answers a change wrote into its pull request's description (point 1). Its commands write the list, carry it across an edit, and read it at the move to review, trusting the head its start marker names (points 2 and 3).

The list repeats every answer. #2664 measured it on [#2653](https://github.com/aleskalfas/project-kit/pull/2653) at 71,400 characters, past the 65,536 the host keeps, and most of its entries said only "still accurate". It also brought a stop on a description too long to hold it, a refusal of words that would close an issue or hide its markers, and markers naming its head.

The reviewer of the answers works from the change check's own list, never from an account the change's author composed ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 3). So the copy was never what it checked.

## Decision

**No command of this capability writes the list of the answers a change wrote into its pull request's description, or carries one there. The landing command removes one an earlier run left. Each reader that needs the answers derives them from the change check at the pull request's head, and a command prints them for anyone not at the landing command, within the limit point 2 states. The author's sentences stay in the description, in the sentences' section (point 1). This overturns DEC-055 where it puts the list in the description: its points 1, 2 and 4, and each other passage of it that writes, carries, reads, prints or compares that list. Every other choice of DEC-055 stands.**

### 1. The description carries no list

- **A list an earlier run left** is its region: both its markers, what lies between them, and the heading directly above. That heading is `## Documentation this change affects`, or the earlier `## Friction answers`.
- **Removing it.** The commands that open the pull request and edit its description drop a region from the body they write, with a warning. The landing command removes one before it stops ready, asks or merges.
- **Nothing else is removed.** A section under either heading with no markers is the author's. A start marker with no end marker draws a warning, and the description stays as it is.
- **Until it is removed,** no reader of this capability treats a region as input: none that reads closing references or the `## Doc impact` section (DEC-013, DEC-015), or checks the template was filled (DEC-031). The host still reads it, and the squash commit of a merge through the other merge commands carries it.
- **The sentences' section stays.** `## What changed in each updated document` holds the sentences, as the author wrote them.
- **An unwritten `## Doc impact`.** The opt-in that fills it from the answers writes one line, counting the documents and pointing at the change check.

### 2. The answers are derived from the change check

Each reader that needs a change's answers derives them from the change check, at the pull request's head against its base (COR-050 points 6 and 12). None reads them from the description. The reviewer of the answers, the command that makes the pull request ready and the landing command each do so.

- **Anyone else** runs `pkit pm show-pr <N> --field answers`, the view. It changes no branch, and fetches the base and any head the clone lacks. It derives the answers as the landing command does, and prints what that command prints (point 4), with one limit: it never checks a head out to start that head's programs.
  - **What that costs.** The change check reads every anchor of every artefact on each run. So on a project where any anchor needs a program the head holds, the check refuses on every change away from a clean checkout at the head, and the view prints no answer. It says why, and that a run from such a checkout reads them.
  - **That run.** It starts the head's programs under the reader's account, and at such a checkout the command is the head's own (per [project-management:DEC-067-heads-that-start-programs]). So a reader makes it only on a head they trust, and an agent only on its person's word.
  - **Anything else.** Where the view cannot derive the answers for any other reason, it says why and prints nothing more.
- **"The list" in a record that stands.** Where a passage of DEC-055, or of [project-management:DEC-064-base-merge-named], speaks of the list of answers, it is the change check's list the landing command derives.

### 3. The move to review derives the answers at the head

The command that makes the pull request ready and requests reviewers derives the answers at the pull request's head, every time. It fetches that head where the clone lacks it.

- **What it refuses.** Each document the change check there marks `updated` that the description gives no sentence for, and each sentence that reads as a closing reference (point 5). The refusal is a `hard-reject`, which `--force` overrides (DEC-046 point 2).
- **What it cannot read stops it:** a description it cannot read, or a change check it cannot run at the head. Neither draws a refusal.
- **Under `--force`,** a change check it cannot run refuses nothing, and a warning says the sentences went unchecked.
- **A sentence on a document the change check does not mark `updated`** draws a warning naming the edit that removes it, as DEC-055 point 3 has it.
- **The other commands.** The command that opens the pull request derives the answers at the pushed head, and warns of a missing sentence and of one on a document not marked `updated`. It takes no temporary checkout, so a refusal there costs a warning line (per DEC-067). The command that edits the description derives nothing, and warns of neither. Each warns of an item in the sentences' section that it cannot read.

### 4. What the landing command prints

The landing command derives the answers at the head it merges. Before it stops ready, asks or merges, it prints what the person who authorises the merge is told (COR-050 point 3):

- **What changed** in each updated document, in the author's sentence, or that the author gave none.
- **What is left out of date:** each document and each target of a link, with the words that name its follow-up.
- **The answers a person or their delegate decided:** each answer the change check did not ask for, and each reason for having no anchors, with its words ([COR-064](../../../decisions/core/COR-064-answer-delegate.md)).
- **Each friction setting** the change alters, as it was and as it is. The friction settings decide what the check asks: the places it reads and the files it leaves out (COR-050 points 1, 7 and 14). They are no part of the change check's list, and the command reads them beside it. A change to the delegate's name is not shown at the merge, which #2122 tracks.
- **How many files** the change check could not read.

It prints no line for any other answer, such as a document still accurate. Beside these lines it prints each revalidation the merge would leave answered apart, as DEC-055 point 3 has it, and each change to the fixers' grant list (DEC-056 point 2). This is information, not a gate: a change with answers merges under the same authorisation as any other.

A run authorised up front prints these lines after the authorisation, so two of them hold it at the ready stop:

- **A missing sentence.** An updated document with no sentence holds the run until the author writes one, as a sentence on a document not marked `updated` does (DEC-055 point 3).
- **More left out of date at a later head.** At a later head an earlier head's authorisation covers, a line on what is left out of date that the head authorised would not print holds the run. So do answers that cannot be read at the head authorised.

### 5. What goes with the list, and what stays

The refusal of a word or a sentence that holds an HTML comment's delimiter goes with the list. So does the showing of the change check's flags on an answer, other than "not asked for": they stay in its own list, for the reviewer.

**A sentence that reads as a closing reference stays refused.** A sentence stays in the description and the squash commit, and the host reads both, with a parser this capability cannot make skip a section. So the move to review refuses such a sentence, and the landing command refuses it with nothing to override that. The refusal reads as widely as the host does: `fixed #12` is refused, which the host would close past the checkbox gate (DEC-007) and the cascade.

What guards the answers themselves stays, as DEC-055 point 3 has it, since it guards what merges. The landing command merges nothing where the answers cannot be derived, or where a file the change touches cannot be read for answers. Nor does it where the base's commits since the head left it changed a file the answers' words are on, or those friction settings the change alters.

### 6. What this gives up

- **The other merge commands and the host's button print no answer.** DEC-055 point 5 accepted that a merge through them "may carry the list of an earlier head, or none". This widens that limit: such a merge shows the person no answer, and nothing holds it. A project that runs no checks on its pull requests lands only this way, since the landing command waits for checks (DEC-055 point 5). The person there runs the view, or the agent they direct does. On a project whose anchors need the head's programs, that prints nothing. There the person is told only the sentences, so COR-064 point 5's telling of what a delegate decided, and COR-050 point 3's of what is left out of date, fall short. [project-kit#2696](https://github.com/aleskalfas/project-kit/issues/2696) closes this gap.
- **An agent's relay.** A person who directs an agent is told what the agent passes on, the case DEC-055's Context feared. The printout's words are the command's, and the view gives them first-hand where it can derive them (point 2).
- **No record of what was told.** The printout goes where the run's output goes, and nothing keeps it. The answer files that land hold what was answered, not what was shown.
- **A reader with no clone** reads the sentences alone, since the view runs the change check. So does a reader away from the head, on a project whose anchors need the head's programs. Either may read the answer files the change adds in its diff on the host.
- **The landing command still starts a head's programs.** It and the move to review take the checkout the view refuses, but run only a head that passes DEC-067's test or that a person named (per that record). Whoever runs them starts that head's programs.

## Rationale

**Why no list.** DEC-055 wanted the answers kept in the default branch's history, and the answer files that land with the change keep them there.

**Why the printout answers DEC-055's rejection of spilling the list.** DEC-055 rejected "Spilling an over-long list elsewhere", since the person "would authorise the merge from a description that does not hold what they are told". That held while the description was where they read the answers. The landing command already printed more than the description held, each finding among it. So the printout becomes the place the person is told, for the head that merges, at any length.

**Why the move to review derives on every run, and what that costs.** A list in the description went out of date on the next fix round, so the move to review compared its marker with the head. With no list, the head is all it can read. DEC-055 ran the check only where the list was for another head, and never on a description with no list. Now a failed fetch or a run past its timeout stops every move, and `--force`, the only way past, passes the move's other findings too. That run is still cheaper than the review round a missing sentence would spend.

**Why `--force` then refuses nothing.** Under DEC-055 the description's list stood in for a check that could not run. With no list, nothing stands in, and `--force` is the operator's choice to pass the refusal whole (DEC-046 point 2). A reviewer of the answers then blocks a missing sentence. A project that chose no reviewer, or reviews in `human` mode, has no one to block it, and only point 4's line and hold remain.

**Why the command that edits the description warns of no missing sentence.** Before review, the move to review refuses what it would have warned of. After review no move runs and an edit stales no verdict, so point 4's hold takes its place.

**Why the holds of point 4.** A line printed just before a merge tells a person who authorised up front nothing in time. A missing sentence after the review has no other stop. A deferral first written at a later head is what COR-050 point 3 says the person is told, so the run compares with the head authorised, as it does for a change to the grant list (DEC-056 point 2).

**Why the landing command removes a list an earlier run left.** Pull requests opened before this record carry one. Left there, it would land in the squash commit as the list of an earlier head. A merge through the other merge commands still lands it so, until no such pull request is open.

**Why only a region is removed.** DEC-055 removed a section no command wrote so that it was not shown beside the list. No list remains, so such a section is the author's, and its plain heading invites one. A start marker with no end may be quoted, and removing what follows it could take the author's text and a closing reference.

**Why the view starts no program of the head.** A person turns to this view to look at a change before trusting it, and a head may come from a fork. A view that checked the head out would run its programs at that moment, under the reader's account. So away from a checkout at the head it gives up the answers, and leaves that run to the reader. A reader already at such a checkout has made that choice.

### Alternatives considered

- **A shorter list, of the answers that matter.** Rejected. It would still be a second copy of what the check derives, and it would keep the size stop and the markers.
- **A pull-request comment.** Rejected for the list: it keeps the second copy, and a later comment does not replace an earlier one. Not taken for what the person is told alone: it would keep a record of that, at the cost of a write on every run. Point 6 states the gap.
- **The other merge commands printing what the person is told.** Not taken. It would reach the person on every path of this capability, at the cost of a run of the change check, in a checkout of the head, on each merge. The view was to give the same lines to whoever asks. Point 2's limit leaves that short on some projects (point 6), so [project-kit#2696](https://github.com/aleskalfas/project-kit/issues/2696) weighs this again.
- **Keeping the view's checkout where the head's resolvers match the base's.** Not taken. A resolver loads more than its own file, so two equal scripts prove nothing.
- **Reading the answer files a change adds, as data.** Not taken. It would start nothing. But whether an answer was asked for needs the file list a resolver gives, so the line a delegate's telling rests on could not come from the files.
- **A comment stamped with the head, from the move to review or from CI.** Left to [project-kit#2696](https://github.com/aleskalfas/project-kit/issues/2696). It would reach every reader with nothing run on their machine, at the cost of a write on each move.
- **Superseding DEC-055 whole.** Rejected. Its authorisation, its findings' hold, its rule on a later head and its check of the merge stand. Restating them would add words and decide nothing.

## Implications

- **DEC-055** gains a first line saying it is partially superseded by this record, for the list in the description. The line names what the Decision overturns: points 1, 2 and 4, and each other passage of it that writes, carries, reads, prints or compares that list.
- **[project-management:DEC-053-doc-check-slot] point 2** says that the answers are read from the change check, and that no section of the description carries them (refinement per this record). It says so in place of its sentence that this capability lists them in the description.
- **[project-management:DEC-056-drift-fixers]** cites this record's point 4 for the landing command's printout of a change to the friction settings, in point 2. Its Rationale's "as no word of the list of answers is an agent's" becomes that the reviewer works from the change check's own list, never an account an agent composed, citing COR-050 point 3. Neither edit changes what DEC-056 decides.
- **[project-management:DEC-064-base-merge-named]** keeps a base that changed the friction settings among the merges it names, with those settings no part of the list. Its Decision's third case becomes "a base that changed what the list of answers shows or the friction settings the change alters". Point 1, in its case "What the list shows", says the list is the change check's list of the answers (refinement per this record), and the landing command reads the settings beside it. Its Rationale, under "Why these merges are named", says such a base would change what the merged check asks. Each case still names the same merge.
- **ADR-068 point 5** says the landing command prints the revalidations answered apart "beside what it tells the person", in place of "beside the list". The edit changes nothing the record decides.
- **The documentation.** The capability README, the software-engineering README, the pm skill and the analysis say what each command does, and name no list in the description.
- **No migration.** No file of an adopter's moves. A description an earlier run wrote is mended by the landing command, at no adopter's step.
- **A surface change** for the capability: what the commands write, what the move to review runs, and the new field. Its changeset declares it.
