---
id: DEC-065
title: A change's answers are read from the change check, not from its pull request's description
status: proposed
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a pull request's description no longer carries a list of the answers its change wrote. Whoever needs the answers runs the change check at the pull request's head: the reviewer of the answers, the command that makes the pull request ready, and the landing command. The author still writes one sentence on what changed in each updated document, in the description's own section. The landing command still prints what the person who authorises the merge is told, and removes a list an earlier run left in the description.

## Context

[project-management:DEC-055-pr-lists-answers] has this capability write the change check's list of the answers a change wrote into its pull request's description (point 1). The commands that open the pull request and land it write the list, and the command that edits the description carries it (point 2). The command that makes the pull request ready reads the list there, and trusts the head its start marker names to decide whether to derive the list again (point 3).

No reader needs the list there:

- **The reviewer of the answers** works from the change check's own list, never from an account the change's author composed ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 3). The software-engineering capability's docs reviewer runs the change check itself, and reads the sentences from the author's own section of the description.
- **The person who authorises the merge** needs what changed in each updated document and which are left out of date until which follow-up (COR-050 point 3). The author's section gives the first. The landing command's printout, before it stops ready, asks or merges, gives both.
- **The list repeats every answer.** On [#2653](https://github.com/aleskalfas/project-kit/pull/2653) it made the description 71,400 characters, past the 65,536 the host keeps, and 50 of its 56 entries said only "still accurate".

The list also carries machinery of its own. The landing command stops on a description too long to hold it, and refuses words that would close an issue or hide its markers. Its markers name the head it was derived for.

## Decision

**No command of this capability writes the list of the answers a change wrote into its pull request's description, or carries one there, and the landing command removes one an earlier run left. Each reader that needs the answers derives them from the change check at the pull request's head. The author's sentences stay in the description's own section. This overturns DEC-055 where it puts the list in the description: its points 1, 2 and 4, and each passage of its points 3, 5 and 6 that writes, carries, reads or compares that list. Every other choice of DEC-055 stands.**

### 1. The description carries no list

No command of this capability writes the change check's list of the answers into a pull request's description. None carries one across an edit.

- **A body that carries one.** The commands that open the pull request and edit its description drop such a section from the body they write, with a warning. The section is the one under the list's heading, or under the heading an earlier run wrote it under.
- **A list an earlier run left.** The landing command removes it from the description before it stops ready, asks or merges. A section under its heading that no command wrote is removed too.
- **Until it is removed,** every reader of the description strips the section before it reads, as DEC-055 point 4 has it. Nothing in it is input, and nothing in it closes an issue.
- **The author's section stays.** The sentences on what changed in each updated document stay in the description's own section, as the author wrote them. The squash commit carries them as it carries the rest of the description.

### 2. The answers are read from the change check

Each reader that needs a change's answers derives them from the change check, at the pull request's head against its base (COR-050 points 6 and 12). The reviewer of the answers, the command that makes the pull request ready and the landing command each do so. None reads them from the description.

The sentences are read from the author's section. Where a passage of DEC-055 that stands, or [project-management:DEC-064-base-merge-named], speaks of the list of answers, it is the change check's list the landing command derives.

### 3. The move to review derives the answers at the head

The command that makes the pull request ready and requests reviewers derives the answers at the pull request's head, every time. It fetches that head where the clone lacks it.

- **What it refuses.** Each document the change check there marks `updated` that the description gives no sentence for. The refusal is a `hard-reject`, which `--force` overrides, as DEC-055 point 3 has it.
- **What it cannot read stops it:** a description it cannot read, or a change check it cannot run at the head. Neither draws a refusal.
- **Under `--force`,** a change check it cannot run refuses nothing, and a warning says the sentences went unchecked.
- **A sentence on a document the change check does not mark `updated`** draws a warning naming the edit that removes it, as DEC-055 point 3 has it.
- **The other commands.** The command that opens the pull request derives the answers at the pushed head. It warns of a missing sentence, and of a sentence on a document not marked `updated`. The command that edits the description derives nothing, and warns of neither. Each command warns of an item under the sentences' heading that it cannot read.

### 4. What the landing command prints

The landing command derives the answers at the head it merges, as DEC-055 point 3 has it. Before it stops ready, asks or merges, it prints what the person who authorises the merge is told (COR-050 point 3):

- **What changed** in each updated document, in the author's sentence, or that the author gave none.
- **What is left out of date:** each document and each target of a link, with the words that name its follow-up.
- **The answers a person decided:** each answer the change check did not ask for, and each reason for having no anchors, with its words ([COR-064](../../../decisions/core/COR-064-answer-delegate.md)).
- **Each friction setting** the change alters, as it was and as it is.

It prints no line for any other answer, such as a document still accurate. Beside these lines it prints each revalidation the merge would leave answered apart, as DEC-055 point 3 has it. This is information, not a gate: a change with answers merges under the same authorisation as any other.

### 5. What goes with the list, and what stays

What went only with the list's place in the description goes with it:

- the stop on a description too long to hold the list
- the refusal of a word, or an author's sentence, that reads as a closing reference or holds an HTML comment's delimiter
- the markers that name the head the list was derived for

What guards the answers themselves stays, as DEC-055 point 3 has it. The landing command merges nothing where the answers cannot be derived, or where a file the change touches cannot be read for answers. Nor does it where the base's commits since the head left it changed a file the answers' words are on, or the friction settings. The merge would then land answers other than those the reviewer checked and the person was told.

## Rationale

**Why no list.** The list was a second copy of what the change check derives, and no reader of the description needed it. The reviewer must work from the check's own list (COR-050 point 3), so the copy was never what it checked. The person who authorises the merge needs what changed and what is left out of date. The author's section and the landing command's printout tell them that, without the answers that leave a document as it is. Most of a long list is such answers, so the list grew past what the host keeps while telling no one anything.

**Why each reader derives the answers at the head.** The change check at the pull request's head is the one source every reader can trust. A list in the description went out of date on the next fix round, which is why the move to review compared its marker with the head. With no list, there is nothing to compare. DEC-055 already ran the change check on every move to review whose list was for another head. A run of the check is cheaper than the review round a missing sentence would spend.

**Why `--force` then refuses nothing.** Under DEC-055 the description's list stood in for a check that could not run. With no list, nothing stands in. `--force` is the operator's choice to pass the refusal (DEC-046 point 2), so it passes it whole. The reviewer of the answers still blocks a missing sentence.

**Why the command that edits the description warns of nothing.** It derives nothing, since a run of the change check on every edit was rejected (DEC-055, Alternatives considered). Its warnings read the list the description carried. With no list it has nothing to warn from, and the move to review refuses what it would have warned of.

**Why the landing command prints the answers a person decided.** Each was shown to a person, or decided by the delegate they named, before it was written (COR-064). A run at a later head an earlier head's authorisation covers stops on one (DEC-055 point 3). The list showed which answers those were. The printout now shows them.

**Why the author's sentences stay in the description.** COR-050 point 3 has the author say what changed where the reviewer and the person who authorises the merge read it. Both read the description, and the squash commit carries it. The change check cannot supply the sentence: it knows that a document changed, not what the change means.

**Why the landing command removes a list an earlier run left.** Pull requests opened before this record carry one. Left there, it would land in the squash commit as the list of an earlier head, unchecked against the head that merges.

**Why the stop on a base that moved on stays.** It guards what merges, not the description. The answers' words sit in the files the change check names for them. A base that changed one of those files merges words the reviewer did not check and the person was not told. A base that changed the friction settings changes what the merged check asks.

### Alternatives considered

- **A shorter list, of the answers that matter.** Rejected. It would still be a second copy of what the check derives, which no reader needs. It would keep the size stop, the refusal of words and the markers.
- **The list in a pull-request comment.** Rejected. A comment is read by no reader either, and a later comment does not replace an earlier one.
- **The description's list kept to save a run of the change check.** Rejected. The move to review trusted the list only where its marker named the head, and a fix round moves the head. So most moves to review ran the check anyway, and the list cost a write on every landing.
- **Superseding DEC-055 whole.** Rejected. Its authorisation, its findings' hold, its rule on a later head and its check of the merge stand. Restating them would add words and decide nothing.

## Implications

- **DEC-055** gains a first line saying it is partially superseded by this record, for the list in the description. The line says the description carries no list and every reader derives the answers at the head. It names what is overturned: points 1, 2 and 4, and each passage of points 3, 5 and 6 that writes, carries, reads or compares that list. Every other choice stands.
- **[project-management:DEC-053-doc-check-slot] point 2** says that the answers are read from the change check, and that no section of the description carries them (refinement per this record). It says so in place of its sentence that this capability lists them in the description.
- **[project-management:DEC-056-drift-fixers]** cites this record's point 4 for the landing command's printout of a change to the friction settings, in point 2. Its Rationale's "as no word of the list of answers is an agent's" cites COR-050 point 3, the change check's own list. Neither edit changes what DEC-056 decides.
- **The commands.** The commands that open the pull request, edit its description and land it write no list. The landing command removes one an earlier run left. The move to review derives the answers at the head every time. The opt-in that fills an unwritten `## Doc impact` from the answers writes one line. It counts the documents and points at the change check, still naming no path and no reason.
- **The documentation.** The capability README documents each command's part. The docs reviewer reads the sentences from the author's section alone. The pm skill and the analysis name no list in the description.
- **No migration.** No file of an adopter's moves. A description an earlier run wrote is mended by the landing command, at no adopter's step.
- **A surface change** for the capability: what the commands write and what the move to review runs. Its changeset declares it.
