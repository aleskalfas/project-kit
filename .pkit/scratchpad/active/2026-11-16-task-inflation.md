---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-11-16
---

# Task inflation: why a coordinator's Tasks multiplied though the rules to fold them existed

Exploratory note (COR-012). It retires by producing changes to the project-management capability, its project-manager agent and its pm skill, and the records those changes need, or by being dropped. Its worked case is one milestone's run in project-kit (Milestone 8, DAM integration, November 2026), coordinated by the project-manager agent with builders and reviewers in parallel, in a project with no topology of seats. The maintainer reports the same shape on other projects, not yet measured.

## The question

The capability already decides how work is folded and ordered:
- **DEC-066:** Tasks that share a file are built one at a time, those of one parent, Milestone and priority are planned as one, and a filed Task takes in work only before it starts, with the person's approval.
- **create-issue's judgements 5 and 6:** a reviewer's follow-up gets the Milestone only when it blocks one of its acceptance criteria or is a correctness defect in a check that already enforces something, and a new Task is ordered after an open one it shares a file with, or folded into it.
- **batch-plan's slicing:** a record that serves one Task rides that Task, with no Task of its own.

Yet the milestone's Tasks multiplied. Why did these rules not fire, and what would make them fire, or what should change, so that a milestone closes sooner, with fewer rounds and fewer calls for the person?

## What happened

Over about three days the milestone reached some seventy issues. Forty-odd pull requests merged, each through a builder, four or five reviewers, CI and the merge check, while the open count stayed in the thirties.

1. **Follow-ups were filed into the milestone.** A builder's hand-off ends with what it left out, and a reviewer's verdict with advisories. The coordinator filed most of these as Tasks in Milestone 8, one at a time through create-issue, not through batch-plan:
   - #3310, a crash on an outcome of the wrong type, and #3330, a version check that took `true` for 1. Both are correctness defects in a reading, which judgement 5 lets into the milestone.
   - #3323, a document contract that left out one outcome, whose case is less clear.
   - #3313, marks on sets a merged change did not reach, and #3332, sets no page lists. Neither blocks a criterion of the milestone, so judgement 5 would have left them out of it.

   The coordinator applied neither judgement 5 nor judgement 6's ordering to them. It put each in the milestone, with no dependency on the open Task it shared files with.
2. **Folding was barred where it would have helped.** Most findings touched files that a started Task was changing. DEC-066 point 4 keeps a started Task's body, so a separate Task after it was the record's answer, and the coordinator was right not to widen it. Late in the run the coordinator planned to land #3332 with #3294, which had started, in one pull request. That is the alternative DEC-066 rejects, and the plan was withdrawn.
3. **Large Tasks were split.** #3293 became #3314, #3315 and #3316, and #3316 then gave up #3320, each when its build grew past what one build could finish. DEC-066 point 3 sanctions that bound. Each part still paid a Task's whole cost.
4. **Records stood as Tasks of their own.** About fifteen open Tasks say "a record decides…". Some pair with a Task that builds what the record decides, such as #3193 and #3243 on pre-check's board warning, against batch-plan's rule that a record rides the Task it serves.
5. **Changes to the hub documents bred rounds.** Most changes touched the project-management README or the CLI reference, pages anchored to whole trees, which the 2026-10-01 note on review load already named as the cause of its remaining rounds.
   - Every merge left the others' answers to name the base's new answer files once they took in the base (COR-062 point 4). #3308 rewrote 29 answers after a conflict on the manifest reference made it take in main.
   - A revalidation that replaced answers made apart had to judge their combined state (COR-062 point 7). #3329 and #3331 were each blocked on one whose reason judged its own change alone.
   - Two pull requests each ended the same stale deferral in their own answer files.

   DEC-066 point 1 does not count a file each Task only adds to, so these collisions fell outside its order.
6. **Calls for the person came one at a time.** Each record needs the person's acceptance, each `[person]` finding holds its merge, and each fold into a filed Task needs approval. Core rule 17 asks one decision per turn, so with many small pull requests the asks queued. The person's standing "merge without asking" removed the merge authorisations but not the rest.

## What each Task costs

Most of a Task's cost to build is fixed:
- a worktree, `start-work`, and a builder's read of the rules and records its files lead to;
- a pull request body;
- four or five reviewers;
- a CI run of 16 to 26 minutes;
- the merge check, `land-work`, and the fixers' run after the merge.

A fix round repeats the reviewers and CI. Review grows with a change's size too, since each reviewer reads the whole diff, and DEC-032's floors draw fewer reviewers onto a documentation-only change.

Filing a Task costs almost nothing. The cost is in building it, so a lever at dispatch, when the next Task is chosen, weighs more than one at filing.

These claims are not measured. The 2026-10-01 note's way of counting rounds by cause would show how much of the run's time went to CI, to review, to fix rounds and to waiting for the person.

## Why the rules did not fire

- **The coordinator filed from its own view of the work.** Judgements 5 and 6 sit in the create-issue sub-procedure, which the coordinator read early and then worked from memory across a long session that compacted its context. Nothing at the point of filing put them in front of it, and the script checks neither.
- **The milestone was never re-planned.** batch-plan's gate, where the critic reviews and folds apply, ran on no part of the milestone after its first slicing. Follow-ups arrived one at a time, each its own small decision.
- **DEC-066's shared file leaves out the hub edits.** A file each Task only adds to does not count, and an entry added to the CLI reference or a section of the README is that kind of edit. The record's order never reached the pages where most collisions happened.
- **Parallelism was the person's instruction.** "Do as much as possible in parallel" put builders onto Tasks that met on the hub pages. Changing that is the person's call, and the note can only show its cost.
- **The closed brief and the blocker-only fix round send other work back as Tasks.** Both were cures for earlier rounds (the 2026-10-01 note, #1180), and loosening them would bring those rounds back.

## Ways to make them fire, and what to change

These are not yet decided.

- **Keep the milestone to its criteria.** Apply judgement 5 at every follow-up: the rest goes on no Milestone, or on the rolling maintenance Milestone (DEC-016), and waits. This is the cheapest change, and it needs no record.
- **Fold at dispatch, behind one gate.** File follow-ups freely, which also gives each deferral the open follow-up it must name (COR-050 point 3). Before the next Task is dispatched, re-slice the Tasks not yet started under DEC-066, and show every fold at one gate, as batch-plan's gate does. Each fold is still shown, not taken under a standing acceptance (COR-064).
- **Let records ride their Tasks.** Merge each "a record decides" Task into the Task that builds it, where they serve one outcome, as batch-plan already says.
- **Count the hub edits, or remove the hubs.** Either refine DEC-066 point 1 so that an add-only edit to a named hotspot document counts as sharing it, which then orders those changes, or narrow the hub pages' whole-tree anchors and split them by what a reader looks up, as the 2026-10-01 note proposed. COR-062 did not take splitting the documents many changes answer on, since it moves the conflicts. That reason needs weighing against the anchors' scope.
- **Let advisories ride a round already running.** An advisory joins a fix round only where one is happening for a blocking finding, and nothing is pushed onto an approved head for one.
- **Turn recurring wording calls into rules.** Where reviewers raise the same `[person]` call again and again, such as a series of two in a sentence or a fact stated twice, a rule in the writing set settles it once (COR-007). Delegating them is closed: the project-manager's section 10 keeps a finding left for a person as the person's.
- **Queue the person's calls.** One decision per turn stays, but the coordinator asks them back to back, each with its recommendation, rather than as each pull request comes up. Batching them into one list clashes with core rule 17, and COR-064 did not take one batch for answers, since the person would judge each without its context.
- **Tune the reviewers to the change.** DEC-032's floors could draw fewer reviewers onto a change of a few lines.

Weighed and not taken: **one branch and one pull request for several Tasks.** DEC-066 rejected it against one branch for each Task (DEC-013). DEC-013 allows a pull request that closes several issues only where the work is tightly coupled and the issues share a parent. A squash merge would make one commit of several logical units, which COR-008 point 2 forbids. It also meets each Task's own build record and claim in a project with seats (DEC-063, DEC-059). An integration branch (DEC-013, DEC-040) and a topology of seats for parallel landing are the other routes to weigh before any such record.

## Candidate changes

Every change lands in the capability, which projects install, so each must hold with a topology of seats and without one (COR-014).

- **create-issue:** a check at filing that warns where a new Task names files an open Task changes, or where a follow-up is filed into a Milestone without the reason judgement 5 asks. This turns judgements 5 and 6 from prose into a check (COR-007).
- **batch-plan:** a re-slice of the Tasks not yet started, run before dispatch, with one gate for its folds.
- **The project-manager's body:** before filing a follow-up, run judgements 5 and 6, and prefer the rolling maintenance Milestone.
- **DEC-066:** a refinement counting add-only edits to named hotspot documents, if that route is taken.
- **DEC-032:** reviewer floors by a change's size, if that route is taken.
- **The writing rule set:** the wording calls that recur.

## Open questions

- For each follow-up filed, did judgements 5 and 6 and DEC-066 apply, and which produced the new Task?
- Which base merges did #3308, #3329 and #3331 take in, and under which case of DEC-064 point 1?
- How many of the milestone's issues pass judgement 5's test?
- How do the person's calls split: merges, `[person]` findings, record acceptances, fold approvals?
- How does a re-slice at dispatch meet a topology of seats, where a seat claims one Task (DEC-059), and the builder's brief is the Task's body (DEC-063)?
- Is this milestone unusual, set beside earlier ones?
