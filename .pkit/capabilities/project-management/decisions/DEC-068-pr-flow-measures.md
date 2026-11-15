---
id: DEC-068
title: How a merged pull request flowed is measured the same way in every project
status: proposed
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** this capability reports how a project's merged pull requests flowed, so the project can see where its time goes and whether a change to its process helped. This record says what each count means.

- **A review round** is a head that reviewers gave verdicts on.
- **A blocking finding** is a `[block]` finding in a verdict, counted by its reviewer and by the rule it cites.
- **A merge of the base** is a merge commit on the branch, which git makes again to tell whether it conflicted.
- **A failed CI run** is one failed attempt, and a re-run is a later attempt of the same run.
- **The answers a pull request added** are those its landing brought that no later answer of its own replaced.
- **Two times:** from opening to merge, and from the last push to merge.

Each measure reads only what the methodology or the host defines, never one project's own markers. What another pull request did counts for that pull request alone. The report writes no ref, no tracked file and nothing on the host, and runs nothing a pull request's head brings, such as a script or a hook. A count it cannot read is reported as not read, never as zero.

## Context

A project that changes how its pull requests are built, reviewed and landed wants to know whether the change helped. It counts, over the pull requests merged before and after, how many rounds of review each took, how often the base was merged in, how many answers were written and how often CI failed. A count from before and one from after compare only when both count the same thing.

The measures rest on artefacts this capability and the backbone already define:

- **Verdicts.** A reviewer's verdict carries a marker, which names the head it reviewed where the reviewer path stamps one, and each finding under it carries a tag saying what it does to the merge ([project-management:DEC-028-agent-as-approver-paths], "The verdict signal" and "Finding tags").
- **Merges of the base.** The freshness rule tells a merge of the base from the author's own commits, and makes it again with git (DEC-028, "Stale-verdict handling"). This capability's commands ask for such a merge only in named cases ([project-management:DEC-064-base-merge-named]).
- **Answers.** A change writes its answers to friction in answer files of its own, in one folder the backbone fixes ([COR-062](../../../decisions/core/COR-062-answers-in-own-files.md) points 1 to 3). This capability reads no answer file itself ([project-management:DEC-055-pr-lists-answers] point 3, "Who answers it").
- **The landing.** This capability lands a pull request as one squash commit on its base ([project-management:DEC-013-branch-and-pr-conventions]).
- **Heads that start programs.** A command of this capability starts a head's programs only for a head it may trust ([project-management:DEC-067-heads-that-start-programs] point 1).

project-kit measured its baseline with a collector of its own ([project-kit#2633](https://github.com/aleskalfas/project-kit/issues/2633)). Some of its counts read project-kit's own text, such as one check's timeout message and its check aggregator's output lines. Those counts mean nothing in another project. Others rest on choices nobody recorded, such as which verdicts count when a reviewer runs twice on one head.

## Decision

**Each measure of how a merged pull request flowed is defined below on what the methodology or the host defines, never on a project's own markers, so each count means the same in every project. Work another pull request brought counts for that pull request alone, and a measure that cannot be read is reported as not read, never as zero.**

### 1. The window

- **Which pull requests.** Each pull request merged within the window, into any base, by when it merged. It counts however it merged: through this capability's commands, the host's own merge or a merge queue. A pull request closed without merging is in no window.
- **Its bounds** are whole days in UTC, the first and the last both included.
- **Under a parent.** A window narrowed to a parent issue holds each pull request that names, with a closing keyword (DEC-013), the parent or an issue under it at any depth ([project-management:DEC-005-linking-and-containment]). The keyword is read whatever the base, since the host closes issues only from a pull request into the default branch.
- **What the window reports.** Each measure is counted for each pull request. For the window the report gives its total, its mean and median per pull request, and how many pull requests had any. Each is taken over the pull requests the measure was read for (point 10).

### 2. A pull request's commits, its landing, and another's work

- **Its commits** are those the host lists for it when it merged, and each commit a force-push of its branch replaced, as its timeline names it.
- **Its landing** is the commit the host records the merge as. Its first parent is the base's tip just before the landing, as a squash or a merge commit has it.
  - **A fast-forward or a rebase** shows no such tip. The landing is then one of the pull request's own commits, or its first parent is a commit the host ties to the same pull request. Points 3 and 6 are then not read.
- **When a commit arrived** is when the host created its earliest check suite on that commit, and no earlier than the pull request's opening. It is never read from the commit's own dates. Where the host records no check suite on it, its arrival is not read.
- **The head at a time** is, of its commits that had arrived by then, the one that arrived last.
- **Another pull request's work.** A commit of its branch that another pull request, merged before it, brought is that pull request's, and counts for it alone. Such a commit is one that pull request's head held, or that pull request's landing. So a stacked pull request does not count again its parent's merges of the base. Nor does the pull request that lands an integration branch count again what the pull requests landed into it brought.

### 3. A merge of the base, and whether it conflicted

- **A merge of the base** is a merge commit of the pull request's own on its branch's line of commits, its first parents. The line runs back from the head that merged to the first commit the base's tip before the landing holds. The merge's second parent is a commit that tip holds. That is the reading DEC-028's freshness rule makes. The walk runs against a named commit, so it never works out where a branch left the default branch, which is the backbone's ([COR-054](../../../decisions/core/COR-054-default-branch.md) point 5).
  - **Not a merge of the base:** a merge of another branch, and a merge the host or a queue builds to test or land the change, which is no commit of the branch.
- **Whether it conflicted.** git makes the merge again from its two parents (`git merge-tree --write-tree`), with git's default merge settings, whatever the reader's own configuration.
  - **Conflicting** where git reports a conflict. The report names each file git names.
  - **Clean** where git merges with no conflict, whatever the author changed inside the merge.
  - **Not read** where git cannot make it, with why.

### 4. A review round

- **A counted verdict** is a comment in the pull request's conversation, never a review on the host, posted before the merge. It carries the verdict marker, and its first line is in the verdict grammar (DEC-028, "Verdict-line grammar and the consumer scan contract").
  - **Its reviewer** is the name in a local verdict's first line, or the author of a remote verdict's comment.
  - **Any reviewer.** Which reviewers the project registered, or required of the pull request, is not read.
- **Its head** is the head its marker names. A verdict whose marker names none is placed on the pull request's head at the time it was posted (point 2). Where that head is not read, the verdict is in no round, and the pull request's rounds are not read.
- **A round** is each head that received at least one counted verdict. Several reviewers on one head make one round.
- **A re-review** is a further verdict of a reviewer on a head it already judged, such as one forced to run again there. It adds no round, and it is counted apart.
- **The round's verdicts.** Only each reviewer's latest verdict on a head counts toward that round's findings (point 5). This is this record's own rule, kin to DEC-028's latest verdict per reviewer, which DEC-028 takes across heads and this record takes on each head.
- **A person's review** on the host is no verdict, and makes no round.

### 5. A blocking finding

- **A blocking finding** is each `[block]` finding (DEC-028, "Finding tags") of a reviewer's latest verdict on a head (point 4), read with the tag grammar's lenience. A `[person]` or an `[advisory]` finding is none.
  - **Again on a later head.** A finding raised again in a later round counts again, since each round asked the author for a fix.
  - **Changes requested with none.** A `CHANGES_REQUESTED` verdict with no `[block]` finding is counted apart. Its reviewer may tag no finding, or could not review the change (DEC-028, "Finding tags"). So it never reads as no finding.
- **By reviewer:** the verdict's reviewer (point 4).
- **By the rule it cites:** the first rule id in the finding's lead paragraph, its text before its first sub-item or blank line. Where it names no rule, it is the first record id there. Each is read in the citation forms of the decisions README, "Citing".
  - **A rule id** is read without the component in front, since a rule's id is unique across rule sets.
  - **A record id** keeps its component as written, with its slug and any point dropped. A bare `DEC-NNN` stays bare, since a comment names no capability for it.
  - **No citation.** A finding that cites neither is counted under no rule.
  - **One rule each.** Each finding counts under one rule, so the counts by rule add up to the findings.

### 6. The answers a pull request added

- **Those it added** are the answers live at its landing (COR-062 point 5), in the answer files the landing adds against the base's tip before it. An answer file another pull request's work added (point 2) is that pull request's. This is this record's own reading: an answer the change replaced with a later one of its own counts nowhere.
- **The unit** is an answered artefact: each artefact such an answer is on, once.
  - **Its kind** is its revalidation's outcome, `updated` or `unchanged`, where it has one. Otherwise it is `deferred`, or else `revisited`. A deferral kept beside a revalidation adds nothing.
- **What writes no answer.** An answer moved from an artefact's block, and an answer file put back, write no new answer (COR-062 point 3), so neither counts.
- **Where they lie.** They are counted on the artefact each names, and by the document that artefact lies in.
- **Read by the backbone.** This capability needs the backbone to read the answers, from git objects alone, and to say whether each of the two commits holds the answer folder (Implications). It parses no answer file itself (DEC-055 point 3). The report runs no change check, so it runs nothing a head brings (point 9).

### 7. A failed CI run, and a re-run

- **A run** is one attempt of a host's workflow on one of the pull request's commits (point 2), made while the pull request was open, for any event. A workflow the host runs again is a second attempt, and each attempt is a run of its own.
- **A failed run** is one that failed, timed out or failed to start. Any other conclusion is no failure, a cancelled or skipped run among them.
  - **What failed.** For each failed run, the report names each failed job and each failed step, by the names the host gives them. It reads no log and matches no text a project's own checks print.
- **A re-run** is a second or later attempt, which only a request to run the workflow again makes.
  - **One no change cured.** A re-run that passed where the attempt before it failed is reported so.
- **Another run on one commit.** A further run of a workflow on a commit it already ran on, started by another event, is counted apart, by its event. It is no re-run, since its event may have changed what it checks, as a changed label can.
- **A queue run** is a run on a merge a queue built to land the pull request, where the host names the pull request for it. Queue runs, and their failures, are counted apart from the runs on its commits.

### 8. The two times

- **Open to merge:** from when the pull request was opened, as a draft or not, to when it merged.
- **Last push to merge:** from when the head that merged arrived (point 2) to when it merged. It is not read where that arrival is not read.

### 9. The report only reads

- **It changes nothing the project or the host holds:** no branch or ref of the clone, no file the project tracks, nothing on the host. It fetches each commit the clone lacks by its object name, writing no ref, as the merge gate does (DEC-028, "Stale-verdict handling"). Those objects, and the ones git writes to make a merge again, are the clone's.
- **It starts no head's programs.** It checks no head out, and runs no change check or hook there (DEC-067 point 1). It reads git objects and the host, so it reads a fork's pull request as it reads any other.
- **The engine journal.** No measure rests on it, since journal logging is the project's choice, off by default ([project-management:DEC-049-audit-journal-model] point 1). Where logging is on, the report may add the governed moves the journal holds, in lines of their own and in no measure.

### 10. A measure not read is never zero

- **For a pull request.** A measure the report cannot read for it is reported as not read, with why. The pull request is then left out of that measure's figures, and counted apart. That holds for:
  - its rounds and findings, where it carries verdict-shaped comments and none carries the marker: its verdicts carry no marker
  - its rounds and findings, where no verdict-shaped comment was posted: no verdict reviewed it
  - its rounds, where a verdict cannot be placed on a head (point 4)
  - its merges and answers, where its landing shows no base tip (point 2)
  - its answers, where neither the base's tip before the landing nor the landing holds the answer folder: the project kept no answers in answer files
  - its runs, where no run of the host's workflows was made on any of its commits: its CI ran elsewhere, or none ran
  - its last push to merge, where its head's arrival is not read
- **For the window.** Where no pull request of the window holds what a measure reads, the report names what is missing: verdicts with the marker, an answer folder, or runs of the host's workflows.

### 11. What the measures do not see

- **A rebase onto the base** leaves no merge commit, so no merge of the base is counted for it.
- **A semantic conflict,** where two changes merge cleanly but no longer work together, is clean (point 3).
- **A review by a person on the host** makes no round (point 4).
- **An untagged finding under an approval** counts as `[advisory]` (DEC-028), so it is no blocking finding.
- **CI partly outside the host's workflows:** the runs inside are counted, and the rest are not seen.
- **Why a re-run passed.** A failure a re-run cured is told apart from one a change cured, not from its cause.
- **Answers written again.** An answer the change replaced before it landed, such as one written again after a merge of the base, is not counted (point 6).

## Rationale

**Why the measures rest only on what the methodology or the host defines.** Every project that installs this capability reads verdicts by the same marker and tags, keeps its answers in the same folder, and lands through the same host ([project-management:DEC-003-github-bound-substrate]). Measures defined on those mean the same in each, so a baseline and a later count compare. A project's own markers, such as one check's timeout message, mean nothing in another project ([COR-014](../../../decisions/core/COR-014-universal-applicability.md)). Naming a failing step by the host's name keeps what the project chose to call it, with no reading of its output. A project that wants a cause told apart gives that check a step of its own.

**Why another pull request's work counts for it alone.** A stacked pull request's branch holds its parent's commits, merges of the base among them. The pull request that lands an integration branch adds every answer file the pull requests landed into it added. Counting either again would count one piece of work twice in a window.

**Why the landing's first parent, and when the host's check suites say a commit arrived.** This capability lands by squash (DEC-013), and a squash or a merge commit has the base's tip as its first parent. A fast-forward or a rebase lands the pull request's own commits, which the host ties to it, so the report can tell one and leave it unread rather than miscount it. The host records no time for an ordinary push, and a commit's own dates are set by the committer's clock and kept by a rebase. The host makes a check suite as a pushed commit arrives, so its earliest one is the nearest record of the push. The floor at the opening keeps a commit pushed before the pull request from making the wait longer than the pull request's life.

**Why a round is a head.** A round is the cycle in which the author pushes and the reviewers judge what was pushed. The marker names the head each verdict judged, so the rounds are exact. Several reviewers on one head are one round. A head no reviewer judged cost no round, so it is none. Grouping verdicts by time instead would split one round run slowly, and join two run quickly.

**Why a verdict that names no head is placed by time.** DEC-028 judges such a verdict by when it was posted, against the commits that came before. Placing it on the head of that moment follows that text, with the arrival this record reads. Where the arrivals cannot be read, a guess would join two rounds or split one, so the rounds are not read.

**Why re-reviews are counted apart, and only the latest verdict on a head gives findings.** A reviewer run again on one head cost a review but no round. Its earlier verdict there is replaced by the later one, as DEC-028 replaces a reviewer's earlier verdicts. Counting both would double that round's findings. A finding raised again on a later head is a fix the author was asked for twice, so it counts twice.

**Why registration is not read.** The measures count the review the change took, not whether a gate was met. A reviewer the project no longer registers still reviewed. The cost: anyone who posts the marker and a verdict line by hand adds a verdict, which the gate would drop by registration. Such a comment stands in the pull request's conversation, where a reader of the report can find it.

**Why a change requested with no blocking finding is counted apart.** The tags bind every reviewer, and a remote reviewer gets no brief, so whoever sets it up has it write them (DEC-028, "Finding tags"). One set up without them requests changes with no `[block]` finding. Its findings would otherwise read as none.

**Why one rule for each finding, the first rule before a record.** A count by rule should add up to the findings, so each finding counts once. This record takes the rule as what a finding is about, since a rule is the narrowest thing a finding cites. The lead paragraph is where a finding states its claim. A record's slug and point are dropped, so a record cited with or without them is one key.

**Why the merge is read on the branch's own line and made again with git's defaults.** DEC-028 reads a merge of the base so. So does the backbone's reading of whether a later head's changes lie in the change's answer files (DEC-055 point 3, "Who answers it"). So the report and the gate agree on which commits are merges of the base. A commit's message cannot say whether it conflicted, since the author may change it. git, given the two parents, says what the base forced the author to resolve. Its default settings make the answer one for every reader, where a reader's own settings, such as rename detection, could turn a clean merge into a conflict. The gate makes its merges under the reader's settings, so the two can differ on whether a merge was clean.

**Why the answers are those live at the landing, read by the backbone.** The landing is what the base received. An answer file the branch still holds after the base pruned it is not added by the landing, while a comparison with the branch's head would count it. The live answers are the change's judgments as it landed them. An answer the change replaced was judged again by the answer that replaced it, so counting both would count one judgment twice. COR-062 gives the answer files' form to the backbone, and this capability reads none of them (DEC-055 point 3). A count asks nothing a resolver answers. The told answers do, since whether an answer was asked for needs the resolver's file list ([project-management:DEC-065-answers-read-from-check], "Alternatives considered"). So the count can come from git objects, and start nothing a head holds.

**Why an answered artefact is the unit.** A revalidation re-states each deferral it keeps (COR-062 point 5). Counting those too would rise with the deferrals an artefact carries, not with the answers a change wrote. Each answered artefact is one judgment the change's author made and a reviewer checked.

**Why a re-run is a later attempt of one run.** A request to run a workflow again repeats its event. So a re-run that passes after a failure shows one no change cured, such as a timeout or a fault of the host, on every project and with no reading of a log. Another run on one commit may follow a changed label or a second event, whose input differs. Counting it as a re-run would report a cure where the input changed.

**Why queue runs are counted apart.** A queue run judges the merge the queue built, not a commit of the pull request. Its failure drops the pull request from the queue, a wait of its own.

**Why no measure rests on the engine journal.** Logging is off by default, and a clone-local journal holds only the moves made from that clone (DEC-049 points 1 and 3). A measure resting on it would mean one thing in one project and nothing in another.

**Why a measure not read is never zero.** The report exists to show a change in the counts. A zero that means "not read" reads as a gain. A project whose verdicts carry no marker would appear to need no review at all.

### Alternatives considered

- **Rounds as verdicts posted within a span of time.** Rejected. The span is a guess, and a slow reviewer splits one round.
- **Rounds as heads pushed.** Rejected. A head no reviewer judged cost no review.
- **Only the reviewers the gate requires.** Rejected. The report counts the review taken, and the required set depends on rules a later configuration may have changed.
- **Every verdict's findings, those replaced on their head included.** Rejected. A forced re-run on one head would double its findings.
- **Each rule a finding cites.** Rejected. The counts by rule would exceed the findings.
- **A conflict read from the merge's message.** Rejected. The message is the author's to change, and many hosts write none.
- **The answers from the change check at each merged head.** Rejected. Run from git objects, the check gives no answers where an anchor needs a resolver (DEC-067 point 3). Run from a checkout of each head, it starts that head's programs.
- **The answers parsed by this capability.** Rejected. The form is the backbone's (COR-062 point 1), and DEC-055 point 3 keeps this capability from reading an answer file.
- **The answers against the branch's head.** Rejected. An answer file the base pruned after the branch last took it in would read as added.
- **Each revalidation, deferral and revisit entry as one answer.** Rejected. A kept deferral would count on every revalidation that keeps it.
- **A re-run as any later run on one commit.** Rejected. A changed label or a second event starts such a run, with an input of its own.
- **The host's check suites rather than its workflow runs.** Rejected. They would cover CI of other applications, but such a suite names no step.
- **A project's own markers in the failing runs' logs,** such as patterns the project declares. Rejected. The measures would then differ between projects, and a log is a check's output, which the check's owner may reword.
- **The fetched objects in a repository of the report's own.** Rejected. The backbone reads the clone's objects, so it could not see them there.
- **The measures from the engine journal.** Rejected. It is off by default.

## Implications

- **The command.** This capability gains a reading command that reports these measures for a window. Its name follows the verb-subject convention ([project-management:DEC-020-methodology-as-executable-commands]). It reads the host through this capability's own layer for it, in queries small enough for the host's limits. It reads verdicts through the capability's one parser of the verdict grammar and its tags (DEC-028). The capability README names the command, its options and its machine-readable document, and its changeset declares it.
- **The backbone's reading of answers.** The command needs a reading, from git objects alone, of the answers in the answer files one commit holds and an earlier one does not.
  - **What it gives:** each answer file by name, and each answered artefact by its path, its id and its location. For each answer, its kind, what it read and whether it is live at the later commit. It marks the answers moved and the files put back, says whether each commit holds the answer folder, and names each file it cannot read.
  - **What it runs:** nothing a head holds, and no working tree, so it is safe on a fork's head (DEC-067).
  - **No answer is never an empty one:** in a shallow clone, for an unknown commit, or with a git too old for it.
  - **Where it is decided.** The backbone's reading of what changed since a commit names answer files, not what they say. A record of the backbone's architecture decides the new reading, refining the backbone's answer reader ([pkit:ADR-057] point 2). Its edit to that record comes with it, not with this record.
  - **Until it lands,** the command reports the answers as not read, naming the missing reading. The command's changeset then declares the backbone it needs.
- **Left open: one reading of when a commit arrived.** DEC-028 judges a verdict that names no head by when it was posted, against the pull request's commits. Whether the merge gate reads a commit's arrival as point 2 does is left to a later record. A commit's own dates can make such a verdict read fresh over a commit pushed after it.
- **Left open: one home for a merge made again.** The gate, the backbone's reading of a later head's changes and the command each make a merge of the base again, each with the merge settings it chooses. Whether the capability gives that one home (COR-007) is left open.
- **No accepted record changes.** This record edits none of the records it cites.
- **No migration.** The record adds a command and moves no file of an adopter.
