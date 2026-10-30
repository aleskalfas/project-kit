---
id: ADR-078
title: A full run of the required check runs the aggregator as three parallel parts, behind one job named checks
status: proposed
date: 2026-10-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a full run of the required check runs the check aggregator as three parallel jobs, instead of whole on one machine:
- **two slices**, each half of the test suite's parallel pass, cut where the tests' measured times balance them;
- **the remainder**, every other line of the aggregator, with the tests that must run alone.

The aggregator defines the parts, as `scripts/check.sh --shard 1/2`, `--shard 2/2` and `--rest`, so the pre-push hook still runs the same checks whole, on one machine. A job before the parts decides the form, full or short, as [ADR-067](ADR-067-answers-only-short-check.md) decides it. In the short form that job runs the short check itself, and no part starts. One job, still named `checks`, runs last. It passes only when every step its form requires said that it passed. It stays the one status `main` requires, on a pull request, in the merge queue and on a push.

**What it buys, and what it costs.** A full run should take about 13 minutes on a slow runner, against a median of 29 today (Rationale, "What a full run takes"). It holds three runners at once instead of one. Where the account runs out of runners, parts wait, and a landing takes longer. This record refines ADR-067 in place, and one clause of ADR-055 point 5, on its acceptance (Implications).

## Context

**What a full run costs.** On 30 October, `main`'s full runs of `checks` took a median of about 29 minutes (#2308). The runner decides much of it: a run took 18 to 22 minutes on a fast runner and 28 to 30 on a slow one. The suite took about 22 minutes of a slow run, and the rest of the aggregator most of the other seven. On the runs of 29 October, setting up took 10 to 12 seconds, from checkout to `pkit sync`, and deciding the form 0 to 4.

**What has been tried.** The rewrite of the slow tests (#2313) moved most tests that started a process into the test's own process, and all its slices have merged. What stays slow is mostly `git`, in the friction and analysis tests ([the tests README](../../../tests/README.md), "Running the suite"). Running only the tests a change can reach (#2330) was dropped: the shipped templates make nearly every slow test reach every shipped file. #2308 waited for the rewrite, to be taken up again if a full run still took over twenty minutes. It does.

**Who waits.** Every round of a landing waits for `checks` on its head. ADR-067's short check skips the suite only on a round that changed answers alone. Every other round, and every run in the merge queue and on `main`, runs the suite in full.

**What the issue asks.** #2308 asks for a full run in at most twenty minutes, with the suite split across parallel jobs and balanced by measured test time. `checks` stays the one result `main` requires. The tests that must run alone still run once, in one process. The short check keeps working. The aggregator still runs the whole suite on one machine for the pre-push hook.

**How many runners.** The repository is public, so its standard runners cost nothing, but a free personal account runs about 20 jobs at once. Of the last 100 runs of `checks`, at most 10 overlapped, and 5 or fewer most of the time. So the maintainer chose three parallel parts on 30 October, not more.

**What stands.** The aggregator is the one source of what must pass, for the hook and CI alike. The required status is where a merge is blocked ([ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md) point 2). ADR-067 rejected a suite in a job of its own: the aggregator would no longer hold the suite, so the hook and CI would part, and every run would set up twice (its "Alternatives considered"). It tells a run's form by the names of the steps its `checks` job ran (its point 3). Its decider is the base's copy (its point 5).

**Why an ADR.** How the required check is laid out across jobs is the deployment of the project's enforcement boundary. The layout also refines ADR-067. So it is an ADR, beside ADR-067.

## Decision

**In a full run, CI runs the aggregator as three parallel jobs: two slices of the suite's parallel pass, cut by measured test times, and the remainder. A job before them decides the form. One job named `checks` passes only when every step its form requires said that it passed.**

### 1. The aggregator defines its parts

The aggregator runs whole, as the short check, or as one part of a full run.
- **A slice,** `--shard i/N`, runs the i-th of N shares of the suite's parallel pass, the tests not marked `serial`. It runs them in parallel workers, as the whole run does, and nothing else.
- **The remainder,** `--rest`, runs every line of the aggregator but the parallel pass: every check that is not the suite, and the tests marked `serial`.
- **A full run in CI** is two slices and the remainder, three jobs side by side. The workflow names each part as a job of its own, and says nothing of what a part runs.

The remainder and the N slices together are the whole run. The aggregator makes each part by choosing among its own lines, so a check added to it joins the remainder, the short check and the hook's run with one edit. `--short` takes no `--shard`, since the short form has no suite to split.

**Every part sees what the whole run sees.** Each part checks out the run's one commit, with its full history, and sets up as the whole run did. It reads the base the deciding job pinned (point 2), and the change's own head, as the change checks read them ([ADR-068](ADR-068-friction-answer-folder.md) point 6). So a test meets in its slice what it would meet in a whole run, and every part judges one tree against one base.

**The pre-push hook runs the aggregator whole,** on one machine, as before (ADR-067 point 10). A contributor may run any part by hand.

### 2. A job of its own decides the form, first

**The deciding job** runs before the parts, and they start only once it has named the form.
- **On a pull request,** it runs the base's decider, as ADR-067 point 5 says. Before the decision it runs only what the decision needs, so the parts wait as little as they can.
- **It pins the base.** It resolves the base to one commit and hands it to every part: on a pull request the base branch's tip as it fetched it, on the merge queue the queue's base, and on a push `main`'s tip. A part reads that commit, not the branch, so a base that moves while the parts run moves none of them.
- **In the short form,** the deciding job then runs the short check itself, and the parts are skipped. So the short form keeps one job that runs checks.
- **The changeset guard** runs in the deciding job, after the decision, on every pull request in both forms. It is no line of the aggregator (ADR-067 point 1), and this gives it one home.
- **In the full form, or with no answer from the decider,** the deciding job names the form full, and the parts start. A deciding step that fails fails nothing, and leaves the run full (ADR-067 point 6).
- **On a merge queue's run and on a push to `main`,** it names the form full at once, and reads neither runs nor pull requests.
- **Only a pull request may take the short form.** Each job and step that reads the form says so in its own condition, outside the decider (ADR-067 point 2).
- **The parts start on the form named, not on the job's success.** A step after the decision that fails, such as the changeset guard, stops no part, so one run still names every failure. A deciding job that fails before it names the form starts no part, and `checks` fails. A re-run decides again, and a re-run is always full (ADR-067 point 6).
- **Only the deciding job reads the record of runs and the pull requests** (ADR-067 point 9). The parts and `checks` read the repository's contents alone.

### 3. One job named `checks` stands for every part

The job that `main`'s ruleset requires keeps the name `checks`. No other job takes the name, since the decider refuses a run with two, and the ruleset could read either. `checks` runs last, after the deciding job and every part, and runs nothing of the aggregator itself.
- **It runs whatever became of the jobs before it,** the run's cancellation included. GitHub counts a required check whose job was skipped as passing. A `checks` skipped because a part failed would let the merge through.
- **A step passes only by saying so.** Every step a form requires writes an output that says it passed, as its last act once it has passed. `checks` reads those outputs, not the jobs' conclusions alone. A job ends in success with a step its condition skipped, so a conclusion cannot tell a check that passed from one that never ran.
- **In the full form,** it passes only when each slice and the remainder ended in success and said it passed, and the slices agree (point 5). On a pull request, the changeset guard must also have said it passed.
- **In the short form,** it passes only when the deciding job ended in success, and the short check and the changeset guard each said it passed. The parts are not required.
- **Anything else fails it:** a part that failed, was cancelled or timed out, a part the form requires that was skipped or never started, and a deciding job that named no form. A `checks` that is itself cancelled does not pass.
- **The three events alike.** A pull request, the merge queue's run and a push to `main` require `checks` in the same way. Only a pull request may take the short form, and only a pull request runs the changeset guard.
- **A part re-run alone** is judged with the rest of its run: the same commit, base and form. A re-run of the deciding job decides again, and is always full.

### 4. `checks` marks the form by the same step names

ADR-067's decider tells a run's form by the steps its `checks` job ran, read by their names (its point 3). `checks` keeps one step for each form, each under the name the decider reads:
- **the step that holds the full form** carries the name of the step that ran the full aggregator;
- **the step that holds the short form** carries the name of the short check's step.

Exactly one of them runs. The short form's step runs only where a pull request's deciding job named the short form. The full form's step runs in every other case, a deciding job that named no form included, and fails there, since the parts it requires never started. So the decider reads a run of either layout the same way, with no change to it, and reads a run with no form as a full run that did not pass. A run from before this record reads as full, as it did. A base whose decider predates this record reads the new runs right, from the first pull request that brings them. The decider stays the base's copy (ADR-067 point 5), and runs in the deciding job.

### 5. The slices are cut by a committed table of test times

- **The cut.** Each slice lists the tests it collected, in the order pytest collects them, module by module. It cuts that list into N runs of consecutive tests, where the running weight crosses each Nth of the total. A test weighs its time in **the table of test times**, a committed file of the time each test took in a full run in CI.
- **Balance within one test.** A cut misses its mark by at most one test's time, under a minute for the slowest test measured ([the tests README](../../../tests/README.md), "Running the suite"). So the balance needs no measure of the heaviest module.
- **Modules stay whole, but where a cut falls.** Consecutive tests keep each module in one slice, save the module a cut falls in, which runs in both. Only that module's own setting-up, its module-scoped fixtures and the adopter templates only its tests ask for, is paid twice. A template many modules share is built once in each slice that asks for it, however the tests are cut, since each slice is a session of its own ([the tests README](../../../tests/README.md), "Built once, copied for each test").
- **Each slice computes the same cut.** It reads the tests it collected and the table, both fixed by the run's commit, and cuts them by a rule with no randomness. So the slices of one run agree, and a contributor can run the same slice again on a machine of their own.
- **Every test runs in exactly one slice.** The cut covers the tests collected, not the tests the table names. A test the table lacks weighs the table's median, and an entry that no test bears is ignored.
- **Each slice reports what it ran.** Its job hands on a digest of the cut's inputs (the tests collected, the table and N), the number of tests collected, and the number its share held, as pytest counted them. `checks` fails unless every slice reports the same digest and the same number collected, and the shares add up to it. Agreement on the inputs alone would not show what ran.

### 6. The maintainer keeps the table, from CI's own times

- **A time for each test, not for each slice.** So changing how many slices there are needs no new table.
- **A stale table costs time, never coverage.** As tests are added or grow slower, the slices drift apart, and the longer sets the run's time.
- **Where the times come from.** A command writes the table from the tests' times in a full run on `main`, which each slice of such a run keeps as an artifact of the run. The times come from CI's own runners, never from a contributor's machine. No run writes the table, in the tree or in a cache another run reads.
- **When it is refreshed, and by whom.** The project's maintainer owns the table. It is refreshed when a tenth of the tests collected are missing from it, or when full runs on `main` take longer than the tests README holds them to. `checks`'s summary shows both signals: each slice's time, and how many tests collected the table lacks. Two slices' times are not compared to tell drift, since one runner can take half as long again as another.

### 7. The tests that run alone, and the tests of the answers

- **The tests marked `serial`** run once in a full run, in one process, in the remainder. The remainder runs no parallel pass, so no worker shares its machine, which is what the mark asks for ([the tests README](../../../tests/README.md), "Running the suite"). They run beside the slices, not after one of them. So they add nothing to the run's time while the remainder stays shorter than a slice. The slices leave them out.
- **The tests marked `answers`** run in the short form, in one process, in the deciding job, as ADR-067 point 8 says. In the full form they run in their slice, like any other test.

### 8. A failure is named by the part that found it

- **No part stops another.** A part that fails cancels no other, and each runs all its lines and tests to the end, as the aggregator does. So one run names every failure.
- **Each part names its own failures** in its job's summary. A slice names each failing test, says which slice it is, and says how to run that slice again. The remainder names each failing line. GitHub shows every job's summary on the run's page, under the job's name, so a failing test appears beside the job that ran it.
- **Each part times itself.** It measures how long its step of the aggregator took, and hands the time on as an output. So `checks` reads every part's time with no token that reads the record of runs.
- **`checks` names the parts.** Its summary says which form ran. It lists each part the form requires, with how it ended and how long it took, and whether the slices agree. It does not copy a part's failures.
- **The deciding job's summary** says which form ran and why, as ADR-067 point 9 says. Where the decider gave no answer, `checks` says that the run is full, and how the deciding step ended.

### 9. What a run holds, and for how long

- **At most three runners at once.** A full run holds one runner for the deciding job, then three side by side for the parts, then one for `checks`. A short run holds one, then one. A landing holds at most three at once: its pull request's last run, then the run on `main` after the merge, one after the other.
- **At the account's limit,** a part that finds no free runner waits for one, and its run ends that much later. Nothing fails. Five full runs at once, as most of the time, hold 15 of the 20 or so runners. Ten, the peak of the last 100 runs, would want 30, so some parts wait. Other workflows share the limit.
- **A newer run on a pull request cancels the older one.** On a `pull_request` event, a run cancels any run of this workflow still going on the same pull request, so a superseded head holds no runner. A cancelled full run leaves the next run full, as an unfinished one would. A cancelled short run is passed over, as any short run is, since the next short check runs again all it ran.
- **A merge queue's run and a run on `main` cancel nothing,** and are never cancelled this way. The run on `main` after each landing is the backstop that ADR-067 point 7 names.
- **Time limits.** Each job but `checks` stops after 30 minutes, more than twice what a slice should take on a slow runner. `checks` stops after 5. A job stopped so fails `checks`, where a hung test today holds its runner for GitHub's default of six hours. The deciding step keeps ADR-067's bound of fifteen minutes on `pkit friction since`.

## Rationale

**Why spread the suite across machines.** One standard runner has four cores, and the suite took about 22 minutes of a slow run after the rewrite took most processes out of it (#2313). Running only the tests a change can reach fails on the shipped templates (#2330). Only more machines bring a full run well under twenty minutes.

**Why two slices and the remainder.** The maintainer chose three parts, for the runners each run holds (Context). Two slices and the remainder keep each part plain: a slice runs only tests, and the remainder every other line. The remainder runs beside the slices, not after one of them, so it costs the run nothing until it is as long as a slice. Three slices, with the other lines folded into one of them, would end a run a minute or two sooner, by the estimate below. The cut would then have to weigh lines that are not tests against the table, and their times change apart from it.

**What a full run takes.** The run is as long as the deciding job, its longest part and `checks`, one after another. A run of three parts meets a slow runner more often than a run of one, so the slow runner's figure is the one to plan on.

| Stretch | On a slow runner | Rests on |
|---|---|---|
| The deciding job | about 20 s | measured on 29 October: setting up 10 to 12 s, deciding 0 to 4 s, a job's start 2 to 3 s |
| A slice | about 12 min | half the suite's 22 minutes, measured, and the slice's own collection and template builds, estimated at under a minute |
| The remainder, beside the slices | about 7 min | the run less its suite, both measured on 30 October |
| `checks` | under 30 s | estimated: a job's start, a checkout and the verdict |
| **The run** | **about 13 min** | about 9 on a fast runner, by the same ratio, and any wait for a runner on top |

The estimates are measured on the pull request that builds this, and the record's figures are held to what it finds. A decision that takes its full fifteen minutes adds them to the run, as it does today in one job. The run keeps some seven minutes inside twenty, which the suite would use only by growing about half again.

**Why the aggregator defines the parts.** ADR-067 kept the suite in the aggregator so that the hook and CI could not part. That ground holds for a split suite too. If the workflow called the test runner for each slice, the markers, the worker count and the serial pass would live in two places. With `--shard` and `--rest` in the aggregator, the hook's run is the union of CI's parts by construction, and the short check is one more choice among the same lines. The enforcement boundary stays where ADR-019 point 2 puts it.

**Why the decision comes first, in a job of its own.** Which jobs a job waits for is fixed when the workflow is written. To skip the parts in the short form, they must wait for the answer, so it must come from a job that ends before them. The full form pays with one setting-up in series: the deciding job's, then the parts' side by side. ADR-067 counted setting up twice against a suite job, and that ground holds here too. It is outweighed: setting up took 10 to 12 seconds, where only more machines bring the suite down. Running only what the decision needs before the answer keeps the wait short, and runs less of the pull request's code before the decision.

**Why one job decides, not each part.** A run can finish between two parts' calls to the decider. One part could read that run unfinished and run its share, while another reads it passed and skips its own. One answer, named once, gives every part the same form.

**Why the deciding job pins the base.** The parts start at different moments, and the base may move between them. A part that fetched the base branch itself could judge the change against another base than its siblings did. One commit, named once, gives every part one base.

**Why the short check runs in the deciding job.** The short form is the frequent one in rounds of answers, and it holds no suite to split. Run where it was decided, it sets up once, as it did in one job. A job of its own, after the deciding job, would set up twice in series, for nothing.

**Why `checks` always runs.** GitHub counts a required check whose job was skipped as passing. A job that waits for others is, by default, skipped when one of them fails. That would turn every failure into a pass. So `checks` runs whatever happened, and decides from the outcomes itself.

**Why each step says it passed.** A job ends in success when its condition skipped a step. A short check skipped by a slip in its condition would leave the deciding job green, and `checks` with it. An output that a step writes only once it has passed cannot be left by a step that never ran.

**Why a job for each part, not a matrix.** A matrix hands on one set of outputs for all its legs, the last leg's to finish. `checks` could then not read each slice's digest and counts. A job for each part has outputs of its own. Changing the number of slices is an edit of the workflow's jobs, and needs no new table.

**Why keep the step names.** The decider reads the names as GitHub records them. A job's outputs live only within its run, and nothing else a job can set, that a later run can read, marks the form (ADR-067's Rationale, "Why the steps' names mark the form"). Kept, they need no change to the base's decider. So no window opens, before or after the first pull request lands, in which runs of one layout read wrong. The full form's step names the whole run its parts make up, not what the step itself does. That is the cost of keeping the mark.

**Why a committed table of times.** Every slice of a run must cut the suite the same way, or a test could fall in no slice or in two. A committed table gives each slice the same input, at the run's commit. A contributor can then run a slice again, with the same tests, which matters for a failure that depends on the tests around it. The table is reviewed like any change, and a pull request's run cannot write what later runs read. The cut covers what was collected, so a stale table costs only time.

**Why a cut of consecutive tests.** It balances within one test's time and keeps every module whole but one. Assigning whole modules would balance only within the heaviest module's time, which no run in CI has measured, and could not place a module heavier than a share. Assigning single tests freely would spread each module across both slices, and each slice would pay every module's own setting-up.

**Why a newer run cancels the older one.** A run that holds three runners makes a superseded run three times as costly at the account's limit. The required status is read on a pull request's head, so a run on an older head decides nothing once a newer head is pushed. The run on `main` after a landing is the short check's backstop, and a merge queue's run tests the merge it is about to make, so neither is cancelled.

**Why a failure is named where it happened.** Each part is the one account of what it found. `checks` reads only the parts' outcomes, which GitHub records whatever a part did, and the few outputs each hands on. Gathering every failing test into `checks` would need files each part hands on, which a cancelled part never writes. It would be a second account, able to disagree with the first.

### Alternatives considered

- **A larger runner, with one job.** Rejected: a larger runner is billed by the minute, where a public repository's standard runners are not, and its gain stops at one machine's size.
- **Slices that call the test runner from the workflow,** beside a job that runs the aggregator without its suite. Rejected on ADR-067's ground: the workflow would hold how the suite is run, and the hook and CI would part.
- **The whole aggregator in each slice's job,** with a share of the suite. Rejected: every other line would run in each slice, the checks of the change would report several times, and each part would take the remainder's time on top of its share.
- **Three slices, the other lines in one of them.** Not taken: a minute or two sooner, by the estimate, for a cut that must weigh lines that are not tests.
- **Three slices and the remainder,** four parts. Not taken: each run would hold four runners, more than the maintainer chose for the account's limit.
- **One job per line of the aggregator.** Rejected: the workflow would hold the list of checks.
- **Require every part by name in the ruleset,** with no `checks` job. Rejected: the ruleset would change with the number of slices, could not tell a part the short form skips from a failure, and the decider's mark lives on one job.
- **Start the slices beside the decision,** and leave them out of the short form. Rejected: `checks` waits for every job it depends on, so the short check would take as long as a full run, and the slices would hold runners that other runs need.
- **Each part runs the decider itself.** Rejected: it fails open. A run can finish between two parts' calls, so the parts of one run could take different forms, and a part that took the short form would skip its share.
- **A job of its own for the short check,** after the deciding job. Rejected: the frequent form would set up twice in series.
- **Judge each part by its job's conclusion alone.** Rejected: a job ends in success with a step its condition skipped.
- **A matrix of slices.** Rejected: it hands on one set of outputs for all its legs. Reports handed on as artifacts instead would need a download in `checks`, a second channel beside the outputs.
- **Give the steps new names,** and teach the decider both. Rejected: the decider would read two marks for good, and new runs would read as neither until the base's decider learnt the new names.
- **Assign whole modules,** weighed by a table of times per module, or split only a module heavier than a share. Not taken: it balances only within the heaviest module's time, which no run in CI has measured. A cut of consecutive tests balances within one test, and keeps all but one module whole.
- **Split by a hash of each test's id,** with no table. Rejected: it scatters each module across every slice, and leaves the balance to chance.
- **A shared queue the parts draw tests from.** Rejected: it needs a service outside GitHub Actions, and a slice's tests are not known before it runs, so a failure cannot be run again with the same tests around it.
- **Compute the cut once, in the deciding job,** and hand it to the slices. Rejected: a collection of the suite would come before every slice, and the cut would sit outside the aggregator.
- **Keep the table in a cache that each run refreshes.** Rejected: the slices of one run could read different tables and cut differently, and a pull request's run would write what later runs read.
- **Run the serial tests after one slice's parallel pass,** as the aggregator does on one machine. Not taken: that slice would run longer than the balance says, while the remainder has room beside the slices.
- **Stop every part at the first failure.** Rejected: one run would no longer name every failure, and the parts it cancelled would show as failures of their own.
- **Let every run on a pull request finish.** Not taken: a superseded run would hold three runners for nothing, at the account's limit.
- **Run only the tests a change can reach** (#2330). Rejected: the shipped templates make nearly every slow test reach every shipped file, so the selection would run nearly the whole suite.

## Implications

- **ADR-067 is refined in place on this record's acceptance.** The architect rewrites each passage below to state what holds, with a forward pointer to this record, and checks that the rest of the record agrees ([the decisions README, "Refining an accepted record"](../../../.pkit/decisions/README.md#refining-an-accepted-record)).
  - The Summary's first paragraph, where the `checks` job runs in one of two forms and the full run is the aggregator "as before" (this record's points 1 and 3).
  - The Decision's opening line, "the `checks` job runs the aggregator without its test suite" (points 2 and 3).
  - Point 1's "The full run is `scripts/check.sh` with no argument, as before" (point 1).
  - Point 2's "The workflow says so in the condition of the short check's step" (point 2).
  - Point 3's "Telling the forms apart", which reads "the step that runs the full aggregator" (point 4).
  - Point 5's "What is still the pull request's", whose steps before the decision are only those the decision needs (point 2).
  - Point 7's green full run, "every line of the aggregator passed, the suite included", which holds across the parts, on the run's one commit and one base (points 1 to 3).
  - Point 9's "The job's summary" and "The job's token", which become the deciding job's and `checks`'s, each part timing itself (points 2 and 8).
  - The Rationale's "Why the steps' names mark the form", its last sentence, on the full run's step keeping its name (point 4).
  - The alternative "Make the suite a job of its own". It stays rejected, on its first ground, for a suite job outside the aggregator. Its second ground, that every run would set up twice, holds for the parts too, and this record outweighs it (Rationale, "Why the decision comes first").
  - The Implications' "The workflow", which names the steps the job gains and its token (points 2 and 3).
- **ADR-055 point 5 is refined in one clause.** Its "since the aggregator is the unit GitHub requires" becomes the aggregator, run whole or in its parts behind one job, with a forward pointer to this record ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5). Every check the aggregator runs is still a gate.
- **Why refine, not supersede.** Every choice ADR-067 made among alternatives stands. Those are one required status with two forms, the short form's conditions and basis, the base's decider, the full form on every doubt, the form marked by the names of the `checks` job's steps, and the aggregator as the one holder of the suite. Its rejected alternative is narrowed, not reversed. Even so, rewriting point 1's full run changes what ADR-067 decides, and ADR-055's clause what it says the status stands for. Both stay a person's decision ([COR-064](../../../.pkit/decisions/core/COR-064-answer-delegate.md) point 6), and a person's acceptance of this record is the sign-off for both edits.
- **ADR-068 point 6 stands as written.** Every part gets the base and the head the change checks read.
- **The workflow.** `.github/workflows/checks.yml` gains the deciding job, a job for each part and a `checks` job that waits for them all and judges their outputs. Only the deciding job may read runs and pull requests. The ruleset is unchanged.
- **The aggregator** takes `--shard i/N` and `--rest`. Tests pin that the parts together are the whole run, and that the cut is deterministic and puts each collected test in exactly one slice, whatever the table holds. They pin `checks`'s verdict for each outcome of each part, and for each missing output, on each event, and the step names the decider reads.
- **The table of test times** is committed beside the suite, with the command that writes it. The tests README says where it lives, when and how to refresh it, and the time a full run is held to.
- **Runner minutes.** Each part sets up on its own, so a full run uses a few more runner minutes than one job, about 32 against 29 by the estimate, though it ends sooner. Once the merge queue is on, each landing adds a full run in the queue, three runners more for its length.
- **The documentation and its comments.** The tests README ("Running the suite"), `CONTRIBUTING.md` ("Running checks"), project rule 2 and the workflow's comments say how a full run is split. `scripts/short_check.py`'s opening comment, where one job runs `check.sh` or `check.sh --short`, and `scripts/check.sh`'s header, where CI runs it whole, say the deciding job and the parts instead.
- **A `none` changeset at most, and no migration.** Nothing here ships to adopters. It is project-kit's own CI.
- **Revisit** if the remainder grows as long as a slice, if full runs often wait for runners, if the table comes due faster than it is refreshed, once the merge queue is turned on, or once cheaper tests let fewer parts keep to the time.
- **Stands on** ADR-019, ADR-055, ADR-067, ADR-068 and COR-064, all accepted.
