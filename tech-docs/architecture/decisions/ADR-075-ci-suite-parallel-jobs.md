---
id: ADR-075
title: The required check runs the aggregator's parts as parallel jobs, behind one job named checks
status: proposed
date: 2026-10-29
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a full run of the required check runs the check aggregator in parts, as parallel jobs, instead of whole on one machine:
- **the slices**, each a share of the test suite, balanced by the time each test took when it was last measured;
- **the remainder**, every other line of the aggregator, with the tests that must run alone.

A job before the parts decides the form, full or short, as [ADR-067](ADR-067-answers-only-short-check.md) decides it. In the short form that job runs the short check itself, and no part starts. One job, still named `checks`, runs last and passes only when every part the form requires passed. It stays the one status `main` requires, on a pull request, in the merge queue and on a push.

The aggregator defines the parts, so the pre-push hook runs the same checks, whole, on one machine. `checks` marks the form by the same step names as before, so ADR-067's decider reads every run as it did. This record refines ADR-067 in place, on its acceptance.

## Context

**What a full run costs.** The `checks` job runs the check aggregator, `scripts/check.sh`, on one standard runner of four cores, with one test worker per core. Measured on 29 October, a full run took 33 to 48 minutes. On 13 to 15 October it took 8 to 14. The suite holds 20,665 tests, which took 8,706 seconds between them. The 2,065 tests that start real processes took 84% of that time. Four workers cannot run 8,706 seconds of tests in much under 36 minutes. So no setting of one such runner brings a full run near twenty minutes.

**Who waits.** Every round of a landing waits for `checks` on its head. ADR-067 assumed a full run of about twenty minutes. Its short check skips the suite only on a round that changed answers alone. Every other round, and every run in the merge queue and on `main`, runs the suite in full.

**What the issue asks.** #2308 asks for a full run in at most twenty minutes, with the suite split across parallel jobs and balanced by measured test time. `checks` stays the one result `main` requires. The tests that must run alone still run once, in one process. The short check keeps working. The aggregator still runs the whole suite on one machine for the pre-push hook. Making slow tests cheaper is separate work, and this record decides nothing about it.

**What stands.** The aggregator is the one source of what must pass, for the hook and CI alike. The required status is where a merge is blocked ([ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md) point 2). ADR-067 rejected a suite in a job of its own: the aggregator would no longer hold the suite, so the hook and CI would part (its "Alternatives considered"). It tells a run's form by the names of the steps its `checks` job ran (its point 3). Its decider is the base's copy (its point 5).

**Why an ADR.** How the required check is laid out across jobs is the deployment of the project's enforcement boundary. The layout also refines ADR-067. So it is an ADR, beside ADR-067.

## Decision

**In a full run, CI runs the aggregator's own parts as parallel jobs: slices of the suite, balanced by measured test times, and the remainder. A job before them decides the form. One job named `checks` passes only when every part its form requires passed.**

### 1. The aggregator defines its parts

The aggregator runs whole, as the short check, or as one part of its full run. Two kinds of part make up the full run:
- **A slice** is one of the n shares of the suite's parallel pass, the tests not marked `serial`. It runs its share in parallel workers, as the whole run does, and nothing else.
- **The remainder** is every line of the aggregator but the parallel pass: the tests marked `serial`, and every check that is not the suite.

Together, the remainder and the n slices are the full run. The aggregator makes each part by choosing among its own lines, and nothing outside it lists them. So a check added to the aggregator joins the remainder, the short check and the hook's run with one edit. The workflow says only how many slices there are.

**Every part sees what the whole run sees.** Each part checks out the run's one commit, with its full history. It gets the same base, and the same head of the change, that the change checks read ([ADR-068](ADR-068-friction-answer-folder.md) point 6). So a test meets in its slice what it would meet in a whole run, and every part judges one tree.

**The pre-push hook runs the aggregator whole,** on one machine, as before (ADR-067 point 10). A contributor may run any part by hand.

### 2. A job of its own decides the form, first

**The deciding job** runs before the parts, and they start only once it has ended.
- **On a pull request,** it runs the base's decider, as ADR-067 point 5 says. Before it answers, it runs only what the decision needs, so the parts wait as little as they can.
- **In the short form,** the deciding job then runs the short check itself, and the parts are skipped. So the short form stays one job.
- **In the full form, or with no answer,** the deciding job ends and the parts run. A deciding step that fails fails nothing, and leaves the run full.
- **On a merge queue's run and on a push to `main`,** it answers full at once and reads nothing.
- **Only a pull request may take the short form.** Each job that reads the answer says so in its own condition, outside the decider (ADR-067 point 2).
- **Only the deciding job reads the record of runs and the pull requests** (ADR-067 point 9). The parts read the repository's contents alone.

### 3. One job named `checks` stands for every part

The job that `main`'s ruleset requires keeps the name `checks`. No other job takes the name, since the decider refuses a run with two, and the ruleset could read either. `checks` runs last, after the deciding job and every part, and runs nothing of the aggregator itself.
- **It runs whatever became of the jobs before it.** GitHub counts a required check whose job was skipped as passing. A `checks` skipped because a part failed would let the merge through.
- **In the full form,** it passes only when the remainder and each slice concluded with success.
- **In the short form,** it passes only when the deciding job concluded with success, the short check included. The parts are not required.
- **Anything else fails it:** a part that failed, was cancelled or timed out, and a part the form requires that was skipped or never started. A `checks` that is itself cancelled does not pass.
- **The three events alike.** A pull request, the merge queue's run and a push to `main` require `checks` in the same way. Only a pull request may take the short form.
- **The changeset guard** is no line of the aggregator. It runs on every pull request, in both forms, in the job that runs the short check or the remainder. So `checks` requires it with that job.
- **A part re-run alone** is judged with the rest of its run: the same commit, in the same form. A re-run of the deciding job decides again, and a re-run is always full (ADR-067 point 6).

### 4. `checks` marks the form by the same step names

ADR-067's decider tells a run's form by the steps its `checks` job ran, read by their names (its point 3). `checks` keeps one step for each form, each under the name the decider reads:
- **the step that holds the full form** carries the name of the step that ran the full aggregator;
- **the step that holds the short form** carries the name of the short check's step.

Exactly one of them runs, by the form. It fails where the parts its form requires did not all pass. So the decider reads a run of either layout the same way, with no change to it. A run from before this record reads as full, as it did. A base whose decider predates this record reads the new runs right, from the first pull request that brings them. The decider stays the base's copy (ADR-067 point 5), and runs in the deciding job.

### 5. The slices are balanced by a committed table of test times

Which tests fall in each slice is computed from **the table of test times**: a committed file of the time each test took in a full run in CI.
- **A module's tests stay together.** The tests of one module share costly setting-up, so the split assigns whole modules, weighed by the sum of their tests' times.
- **Each slice computes the same split.** It reads the tests it collected and the table, both fixed by the run's commit, and splits them by a rule with no randomness. So the slices of one run agree, and a contributor can run the same slice again on a machine of their own.
- **Every test runs in exactly one slice.** The split covers the tests collected, not the tests the table names. A test the table lacks is weighed at a default, and an entry that no test bears is ignored. Each slice also says which suite it split, and how. `checks` fails unless every slice split the same suite the same way.
- **The table holds a time for each test, not for each slice.** So changing how many slices there are needs no new table.
- **A stale table costs time, never coverage.** As tests are added or grow slower, the slices drift apart, and the longest sets the run's time. The `checks` summary shows each part's time (point 7). When the slices drift apart, a change refreshes the table from a recent full run's measured times. The times come from CI's own runners, never from a contributor's machine. No run writes the table, in the tree or in a cache another run reads.

### 6. The tests that run alone, and the tests of the answers

- **The tests marked `serial`** run once in a full run, in one process, in the remainder. The remainder runs no parallel pass, so no worker shares its machine, which is what the mark asks for ([the tests README](../../../tests/README.md), "Running the suite"). They run beside the slices, not after one of them. So they add nothing to the run's time while the remainder stays shorter than a slice. The slices leave them out.
- **The tests marked `answers`** run in the short form, in one process, in the deciding job, as ADR-067 point 8 says. In the full form they run in their slice, like any other test.

### 7. A failure is named by the part that found it

- **No part stops another.** A part that fails cancels no other, and each runs all its lines and tests to the end, as the aggregator does. So one run names every failure.
- **Each part names its own failures** in its job's summary. A slice names each failing test, says which slice it is, and says how to run that slice again. The remainder names each failing line. GitHub shows every job's summary on the run's page, under the job's name, so a failing test appears beside the job that ran it.
- **`checks` names the parts.** Its summary says which form ran and why. It lists each part the form requires, with how it ended and how long it took. It does not copy a part's failures.
- **The deciding job's summary** says which form ran and why, as ADR-067 point 9 says. Where the decider gave no answer, `checks` says that the run is full, and how the deciding step ended.

## Rationale

**Why spread the suite across machines.** One standard runner has four cores. At four workers, the suite's 8,706 seconds take some 36 minutes, however the aggregator is arranged. Only more machines bring a full run near twenty minutes.

**Why the aggregator defines the parts.** ADR-067 kept the suite in the aggregator so that the hook and CI could not part. That ground holds for a split suite too. If the workflow called the test runner for each slice, the markers, the worker count and the serial pass would live in two places. With the parts defined in the aggregator, the hook's run is the union of CI's parts by construction. The enforcement boundary stays where ADR-019 point 2 puts it.

**Why the decision comes first, in a job of its own.** Which jobs a job waits for is fixed when the workflow is written. To skip the slices in the short form, they must wait for the answer, so the answer must come from a job that ends before them. The full form pays for it with one setting-up in series: the deciding job's, then the parts' side by side. ADR-067 counted setting up twice against a suite job. At the cost the Context measures, one runner's suite costs several times more than a second setting-up. Running only what the decision needs before the answer keeps the wait short. It also runs less of the pull request's code before the decision.

**Why the short check runs in the deciding job.** The short form is the frequent one in rounds of answers, and it holds no suite to split. Run where it was decided, it sets up once, as it did in one job. A job of its own, after the deciding job, would set up twice in series, for nothing.

**Why `checks` always runs.** GitHub counts a required check whose job was skipped as passing. A job that waits for others is, by default, skipped when one of them fails. That would turn every failure into a pass. So `checks` runs whatever happened, and decides from the outcomes itself.

**Why keep the step names.** The decider reads the names as GitHub records them, and nothing else a job can set marks the form (ADR-067's Rationale, "Why the steps' names mark the form"). Kept, they need no change to the base's decider. So no window opens, before or after the first pull request lands, in which runs of one layout read wrong. The full form's step names the whole run its parts make up, not what the step itself does. That is the cost of keeping the mark.

**Why a committed table of times.** Every slice of a run must split the suite the same way, or a test could fall in no slice or in two. A committed table gives each slice the same input, at the run's commit. A contributor can then run a slice again, with the same tests, which matters for a failure that depends on the tests around it. The table is reviewed like any change, and a pull request's run cannot write what later runs read. The split covers what was collected, so a stale table costs only time.

**Why a module's tests stay together.** Tests share costly setting-up within a module: the adopter templates built once per session ([the tests README](../../../tests/README.md), "Built once, copied for each test") and the fixtures scoped to the module. A split by test would scatter each module across every slice, and each slice would pay for every module's setting-up. A slice holds many modules, so a split by module still balances.

**Why a failure is named where it happened.** Each part is the one account of what it found. `checks` reads only the parts' outcomes, which GitHub records whatever a part did. Gathering every failing test into `checks` would need files each part hands on, which a cancelled part never writes. It would be a second account, able to disagree with the first.

### Alternatives considered

- **A larger runner, with one job.** Rejected: a larger runner is billed by the minute, where a public repository's standard runners are not, and its gain stops at one machine's size.
- **Slices that call the test runner from the workflow,** beside a job that runs the aggregator without its suite. Rejected on ADR-067's ground: the workflow would hold how the suite is run, and the hook and CI would part.
- **The whole aggregator in each slice's job,** with a share of the suite. Rejected: every other line would run n times, the checks of the change would report n times, and each part would take the remainder's time on top of its slice.
- **One job per line of the aggregator.** Rejected: the workflow would hold the list of checks.
- **Require every part by name in the ruleset,** with no `checks` job. Rejected: the ruleset would change with the number of slices, could not tell a part the short form skips from a failure, and the decider's mark lives on one job.
- **Start the slices beside the decision,** and leave them out of the short form. Rejected: `checks` waits for every job it depends on, so the short check would take as long as a full run, and the slices would hold runners that other runs need.
- **A job of its own for the short check,** after the deciding job. Rejected: the frequent form would set up twice in series.
- **Give the steps new names,** and teach the decider both. Rejected: the decider would read two marks for good, and new runs would read as neither until the base's decider learnt the new names.
- **Split by a hash of each test's id,** with no table. Rejected: it scatters each module across every slice, and leaves the balance to chance.
- **A shared queue the parts draw tests from.** Rejected: it needs a service outside GitHub Actions, and a slice's tests are not known before it runs, so a failure cannot be run again with the same tests around it.
- **Compute the split once, in the deciding job,** and hand it to the slices. Rejected: a collection of the suite would come before every slice, and the split would sit outside the aggregator.
- **Keep the table in a cache that each run refreshes.** Rejected: the slices of one run could read different tables and split differently, and a pull request's run would write what later runs read.
- **Run the serial tests after one slice's parallel pass,** as the aggregator does on one machine. Not taken: that slice would run longer than the balance says, while the remainder has room beside the slices.
- **Stop every part at the first failure.** Rejected: one run would no longer name every failure, and the parts it cancelled would show as failures of their own.

## Implications

- **ADR-067 is refined in place on this record's acceptance.** The architect rewrites each passage below to state what holds, carrying the pointer "(refinement per ADR-075)", and checks that the rest of the record agrees ([the decisions README, "Refining an accepted record"](../../../.pkit/decisions/README.md#refining-an-accepted-record)).
  - The Summary's first paragraph, where the `checks` job runs in one of two forms and the full run is the aggregator "as before" (this record's points 1 and 3).
  - The Decision's opening line, "the `checks` job runs the aggregator without its test suite" (points 2 and 3).
  - Point 1's "The full run is `scripts/check.sh` with no argument, as before" (point 1).
  - Point 2's "The workflow says so in the condition of the short check's step" (point 2).
  - Point 3's "Telling the forms apart", which reads "the step that runs the full aggregator" (point 4).
  - Point 5's "What is still the pull request's", whose steps before the decision are only those the decision needs (point 2).
  - Point 7's green full run, "every line of the aggregator passed, the suite included", which holds across the parts, on the run's one commit (points 1 and 3).
  - Point 9's "The job's summary" and "The job's token", which become the deciding job's and `checks`'s (points 2 and 7).
  - The Rationale's "Why the steps' names mark the form", its last sentence, on the full run's step keeping its name (point 4).
  - The alternative "Make the suite a job of its own". It stays rejected for a suite job outside the aggregator. Its ground that every run would set up twice does not bear on the full form (this record's Rationale).
  - The Implications' "The workflow", which names the steps the job gains and its token (points 2 and 3).

  This refines ADR-067 rather than superseding it in part, because every choice it made among alternatives stands. Those are one required status with two forms, the short form's conditions and basis, the base's decider, the full form on every doubt, the form marked by the names of the `checks` job's steps, and the aggregator as the one holder of the suite. Its rejected alternative is narrowed, not reversed. Even so, rewriting point 1's full run changes what ADR-067 decides, which stays a person's decision ([COR-064](../../../.pkit/decisions/core/COR-064-answer-delegate.md) point 6). A person's acceptance of this record is the sign-off for that edit.
- **ADR-055 point 5 and ADR-068 point 6 stand as written.** The aggregator, run whole or in parts, is still the unit the required status stands for ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5). Every part gets the base and the head the change checks read.
- **The workflow.** `.github/workflows/checks.yml` gains the deciding job, the parts, and a `checks` job that waits for them all. The ruleset is unchanged.
- **The aggregator** takes the part to run. Tests pin that the parts together are the whole run, that the split is deterministic and puts each collected test in exactly one slice whatever the table holds, `checks`'s verdict for each outcome of each part on each event, and the step names the decider reads.
- **The table of test times** is committed beside the suite, with a command that writes it from a full run's measured times. The tests README says where it lives, how to refresh it, and the time a full run is held to.
- **Runner minutes and runners at once.** Each part sets up on its own, so a full run uses more runner minutes, though it ends sooner. A full run holds the n slices and three jobs more. An account runs a limited number of jobs at once, so many full runs together can wait for runners.
- **The documentation.** The tests README ("Running the suite"), `CONTRIBUTING.md` ("Running checks"), project rule 2 and the workflow's comments say how a full run is split.
- **A `none` changeset at most, and no migration.** Nothing here ships to adopters. It is project-kit's own CI.
- **Revisit** if the remainder grows longer than a slice, if full runs wait for runners, if the slices drift apart faster than the table is refreshed, or once cheaper slow tests let fewer slices keep to the time.
- **Stands on** ADR-019, ADR-055, ADR-067, ADR-068 and COR-064, all accepted.
