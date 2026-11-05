---
id: DEC-066
title: Tasks that share a file are built one at a time, and those of one parent may be planned as one
status: accepted
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** every change pays a cost that does not shrink with its size. A builder reads the records and the code, the checks and the reviewers run, and the change lands. Two Tasks that share a file are built one at a time, so each pays that cost, and the second waits for the first.

So the planner plans such Tasks as one where they belong together: under one parent, in one Milestone or both in none, at one priority. The one Task stays within what one review can read and one build can finish. A Task already filed takes in such work only before it starts, and only with the person's approval.

## Context

Batch planning's slicing step carries a rule that no record holds: Tasks that share a file are built one at a time. It came from a wave of five pull requests in one family of modules, built at once (#1180). Each landing sent the others through another round of review. A clean merge of the base branch leaves every verdict standing ([project-management:DEC-028-agent-as-approver-paths]), but a conflict resolved is an edit the reviewers judge again.

Each change pays what this record calls the *per-change cost*, whatever its size. A builder starts and reads the records and the code, and the checks run. The change check asks its answers, each reviewer judges the change, and it lands. Two Tasks built one after the other pay it twice, and the second waits for the first to merge.

The record on parallel work keeps a conflict over code apart from a dependency of one outcome on another ([project-management:DEC-025-parallelization-primitive]). It names lanes for the first, each a lock on an area of the code, built once lived evidence settles them. Until then it leaves that conflict to a manual discipline, and the rule above is that discipline in batch planning. An EPIC on the cost of each change asks that Tasks that share a file pay it once where they can (#2630).

## Decision

**Tasks that share a file are built one at a time. Those of one parent, Milestone and priority are planned as one Task, within what one review can read and one build can finish. A Task already filed takes in such work only before it starts, and only with the person's approval.**

Here *the planner* is whoever slices work into Tasks, as [project-management:DEC-060-foundation-before-slices] defines the role, or files a Task outside a plan.

### 1. Tasks that share a file are built one at a time

Two Tasks *share a file* when their implementation notes, an optional section of a Task's body ([project-management:DEC-010-issue-body-minimum-structure]), name a file that both change. A file counts only where both Tasks change what is already in it. A file each Task only adds to does not count, as with a new section, a new test, a changeset or a list entry. Nor does a file the notes name only for context.

For a Task not yet filed, its notes are those the plan gives it. A Task whose notes name no file it changes shares a file with no Task.

Of two Tasks that share a file, the one planned or widened later names the earlier among its dependencies. It says there that they share a file ([project-management:DEC-005-linking-and-containment]). It starts only once the earlier has merged, whether the earlier is in the same plan or already open. Tasks that share no file may be built at once.

This is an order of building, for a conflict over code, not a dependency of one outcome on another. Saying so in the dependency lets a reader, and the record that builds lanes, tell the two apart (DEC-025).

### 2. Tasks of one parent, Milestone and priority that share a file are planned as one Task

Where Tasks would share a file, the planner *folds* them: it plans them as one Task in their place. It folds only Tasks of one parent, in the same Milestone or both in none, at the same priority. Point 1 orders the Tasks it does not fold.

- **Kept apart.** The planner may keep apart Tasks it could fold, and gives the person its reason, such as two records the person would accept apart.
- **Another record's order stands.** Tasks that another record builds one at a time stay apart, as a foundation's Tasks do (DEC-060 point 2).
- **The plan's review.** The count of issues that decides whether the critic reviews a plan ([project-management:DEC-029-project-manager-agent-shape]) is taken before the fold. So a fold never skips that review.

### 3. The one Task stays within what one review can read and one build can finish

A folded Task stays within two bounds: what one review can read whole, and what one build can finish in one run. The planner judges both from the work the Tasks describe, not by a count of files or lines. It states its estimate where the person sees the fold, so the person may split it. Past either bound, the work is split into the fewest Tasks within both, and point 1 orders them.

### 4. A Task already filed takes in work only before it starts, with the person's approval

A Task already filed takes in folded work only while it has not started: while it is in Todo or Backlog, with no branch. The person approves each such fold, at the plan's gate or before a Task filed outside a plan is widened. The planner reads the Task again just before writing its body, and leaves one started since as it is, telling the person.

- **Its classification, Milestone and state.** The work takes those of that Task. The planner shows the person where they differ from what the plan, or the filing, would give the work.
- **The work's dependencies.** That Task takes them, so the work still waits for what it waited for.
- **A Task started** keeps its body. Work that shares a file with it is a Task of its own, after it.

## Rationale

**Why fold.** The per-change cost is paid for each change, not for each line. Tasks that share a file are built one after another anyway, since point 1 lets none start before the one before it merges. So planning them as one Task loses no work done at once, and pays the cost once.

**Why one parent, Milestone and priority.** A fold must not move work the person placed. Folded across parents, one parent's work would close under another. Folded across Milestones or priorities, work would be built earlier or later than the person scheduled it. Two Tasks of one parent can still be two outcomes, so the planner may keep them apart, and the person sees why.

**Why these bounds.** A change too large to read whole is reviewed in parts, and a finding that spans them can be missed. A build too large for one run stops at its limit and waits for the person, as the build command's runs do ([project-management:DEC-063-task-builder] point 6). The planner states its estimate, so the person can split a fold it misjudged.

**Why a started Task keeps its body.** Whoever builds it works from its body as it stood when the build started. Where a build command writes the builder's brief, the brief holds that body (DEC-063 point 3). Widening it would change work under someone already doing it.

**Why the person approves a fold into a filed Task.** A filed Task's body is what the person scheduled, or left in Todo. Widening it changes that, and schedules the work as that Task is, so the person decides it, as the person holds scheduling ([project-management:DEC-006-state-machine-and-cascade]). A worker may start the Task between the gate and the edit, so its state is read again just before.

**Why the count comes before the fold.** Whether to fold, and how far, is a judgement the plan's review should see. Counted after the fold, the issues to file would fall below the threshold exactly where that judgement is made.

**Why record the rule.** Batch planning and filing order Tasks that share a file, and the fold rests on that order, so a record holds both.

**The cost.** A folded Task is larger. Its build takes longer, one blocking finding holds the whole of it, and none of it lands before the rest. A revert takes it whole, and the person approves or revises it whole.

### Alternatives considered

- **One Task for each piece, built one at a time.** Rejected: each pays the per-change cost, and waits for the one before.
- **Build them at once, and let the merge settle the overlap.** Rejected: where their changes overlap, the later landing conflicts, and the conflict resolved is an edit the reviewers judge again (DEC-028).
- **Fold every Task that shares a file.** Rejected: work of another parent, Milestone or priority would move with the fold, as "Why one parent, Milestone and priority" says.
- **Fold with no bound.** Rejected, as "Why these bounds" says.
- **Keep each Task, and land several in one change.** Rejected: one branch would carry several Tasks, against one branch for each Task ([project-management:DEC-013-branch-and-pr-conventions]), for the saving a fold makes.
- **Lanes, a lock on each area of the code (DEC-025).** Not taken here: they wait for lived evidence, and a lock keeps Tasks apart without folding them. The record that builds lanes refines point 1.

## Implications

- **The record on parallel work is refined in place** at its sentence on readiness before lanes are built, with a pointer to this record. It then says that readiness reckons nothing from the code a Task touches, but the planner orders Tasks that share a file through dependencies. It says too that the merge settles any other overlap.
- **DEC-029 is refined in place** in two places, each with a pointer to this record. Step 3 of its batch-planning steps then says that Tasks that share a file are built one at a time. Those of one parent, Milestone and priority, it adds, may be planned as one Task, within what one review reads and one build finishes. Its threshold for the critic then counts the issues before any are planned as one.
- **Batch planning's slicing step** states points 1 to 3, citing this record, and its review step counts the issues before the fold. Its gate shows each fold with its estimate, each Task kept apart with its reason, and each filed Task that takes in work. Its filing step files or names what such a Task now depends on, and reads the Task again, before it writes the body.
- **Filing a Task outside a plan** applies point 1, and asks the person before it widens a filed Task as point 4 says.
- **The project manager's storyboard** shows Tasks that share a file planned as one.
- **The analysis** gains the fold in its use case of planning across scopes. Its use case of planning an intent counts the critic's issues before the fold. In its use case of landing beside other agents, how review rounds of parallel landings are kept down is settled here.
- **No command changes.** Point 1 rests on dependencies, which stay prose (DEC-005). A filed Task takes in work through the capability's command that edits a body and a title.
