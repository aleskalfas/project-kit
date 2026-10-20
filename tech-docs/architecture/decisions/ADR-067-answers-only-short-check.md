---
id: ADR-067
title: The required check skips the test suite on a pull request head that changed only answers since the most recent full run, which passed
status: proposed
date: 2026-10-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the `checks` job, the one status `main` requires, runs in one of two forms on a pull request. The *full run* is the check aggregator, `scripts/check.sh`, as before. The *short check* is the same aggregator without its test suite. A run takes the short form only on two conditions:
- **A passing full run.** GitHub's record of this workflow's runs shows that the most recent full run on this pull request passed.
- **Only answers since.** `pkit friction since` says every change from that run's head to this one lies inside `revalidated` blocks and `revisited` lists. A merge of the base counts only for what differs from git's merge of it.

Anything else, and any doubt, takes the full run. The decision is made by the base's code, the decider and the `pkit` it asks, not the pull request's.

**What the status then means.** A green `checks` no longer always means the test suite passed on this head. On a short check it means three things:
- every other check passed on this head, merged with the base as it stands
- the suite passed on an earlier head of the pull request, merged with the base as it stood then
- since then, only answers changed, and merges of the base

Point 7 says it in full. One predicate, `pkit friction since`, now decides two things: whether a person's authorisation covers a later head (project-management DEC-055 point 3), and whether the suite runs on that head. So a later head landed under an earlier authorisation has usually passed only the short check. The maintainer allowed this on 19 October, as option E of the design note on #1779, and #1798 carries it out.

## Context

**A round of answers.** A change answers in the front matter of each document it leaves stale ([COR-050](../../../.pkit/decisions/core/COR-050-anchors-and-friction.md) points 3 and 16). When a merge of the base leaves those answers stale, a round merges the base in, answers again and pushes. The landing command lets the person's authorisation cover that later head ([project-management:DEC-055](../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md) point 3). It asks the backbone whether every change since lies inside the answers, through `pkit friction since`.

**What each round costs.** Each push runs the required `checks` job. A full run takes about twenty minutes, and the test suite takes almost all of it. On 18 October, 35 pull requests landed after 94 rounds between them. An answer is not code, and almost no test reads one (point 8). So most of those minutes tested code that had already passed.

**What the status asks today.** `main`'s ruleset requires the `checks` status from GitHub Actions. It does not require a branch to be up to date with `main` ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5 rejected that), and `main` merges through no queue. So the status never promised that the suite ran on the merge that lands. A push to `main` runs the full aggregator after each landing.

**One home for the predicate.** Which changes lie inside the answers is computed in the backbone, in one place that every reader calls ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 2). That place is `pkit friction since`, as DEC-055 point 3 ("Who answers it") and the CLI reference's "Friction checks" name it. Answers are about to move into files of their own (#1779, #1797).

**Why an ADR.** Wiring CI alone is workflow mechanics, which COR-025 would place in a project record. This record also refines ADR-055 point 5, and it decides a trust boundary: whose code decides, and which of GitHub's records the status trusts. So it is an ADR, beside ADR-057.

## Decision

**On a pull request, the `checks` job runs the aggregator without its test suite when the most recent full run on the pull request passed and only answers changed since. In every other case, and on every doubt, it runs the full aggregator.**

### 1. One required job, two forms

The `checks` job keeps its name, and stays the one status `main` requires.
- **The full run** is `scripts/check.sh` with no argument, as before.
- **The short check** is `scripts/check.sh --short`. It runs every line of the aggregator but the test suite, so every check that reads the change still runs. That covers `pkit validate`, `pkit friction check`, the other diff-scoped checks, lint, format and the type check. Of the suite, it runs only the tests marked `answers` (point 8).
- **The changeset guard** runs on every pull request, in both forms.

### 2. Only on a pull request, by the workflow's own gate

The short check runs only on a `pull_request` event. The workflow says so in the condition of the short check's step, outside the decider. So a decider that answered `short` elsewhere would still leave the run full. The merge queue's run and a push to `main` always run in full.

### 3. The basis: the most recent full run on the pull request, which passed

The decider finds the basis in GitHub's own record of runs, through the Actions API, with the token the workflow already holds.
- **Which runs.** Runs of this workflow file, for `pull_request` events, on this pull request's branch of this repository, that started before this run. GitHub must list each of them for this pull request's number. A run it lists for no pull request, or for another, cannot be told, and makes this run full: passed over, it might be the most recent full run, which failed.
- **All of them.** The decider reads up to three pages of runs. A branch with more runs than that makes this run full, so the decision never rests on the order GitHub lists runs in.
- **Newest first.** A short run is passed over, whether it passed or failed. The next short check runs again all that a short run ran.
- **The first full run decides.** It must have finished with success, and its head is the basis. A full run that failed, or was cancelled, makes this run full, even where an older full run passed. This is stricter than the issue's "the last head that passed the full run", on purpose: keyed on the last head that passed, a failed full run could hide behind a later push of answers.
- **Telling the forms apart.** A run is full when its `checks` job ran the step that runs the full aggregator. It is short when that step was skipped and the short check's step ran. The two steps' names are the mark, as GitHub records them for each job.
- **A run that cannot be told.** A run that has not finished, or that ran neither step, makes this run full.
- **Nothing a contributor writes names it.** No label, title, description, commit message or file of the pull request names the basis. The head branch's name only narrows the listing.
- **One pull request, one base.** GitHub lists a branch's runs for every open pull request of that branch, not for the one that started each run. A run made for another pull request, or against another base, ran that base's workflow, which may run no suite. So the branch must have been the head of this pull request alone, open or closed. The pull request's events must show no change of its base.
- **On the head's own line.** What makes the basis this branch's code is point 4: the basis must lie on the head's own line of commits.

### 4. The predicate is `pkit friction since`

The decider asks `pkit friction since <basis> --head <head> --base <base> --json`, and reads its `all_inside`.
- **The head** is the pull request's head commit, not the merge commit the job checks out.
- **The base** is the pull request's base branch, as the aggregator reads it.
- **A merge of the base** counts only for what differs from git's merge of its two parents. So a clean merge counts as none, and so does a merge whose conflicts were resolved inside the answers. All the base's code such a merge brings counts as none. This is DEC-055 point 3's rule for the same question.
- **A rewritten branch.** A basis that no longer lies on the head's own line of commits, after a force-push or a rebase, answers no.
- **One home.** The workflow reads no friction block itself (ADR-057 point 2). When answers move into files of their own, the command's predicate moves with them. Its document may then change version, and the decider reads only the version it knows, so runs are full until the decider on `main` reads the new one.

### 5. The base's copy decides

On a pull request, the workflow checks the base's tree out beside the pull request's, as a worktree of the same clone. It runs the base's decider, in an environment built from the base's tree, so the `pkit` it asks is the base's too. That `pkit` runs in the base's tree, so the code it loads from the tree it runs in, such as the ownership predicate, is the base's as well. Both read the pull request's history, as data.
- **Why.** The code that decides is the base's, which passed the full run of the pull request that landed it. A pull request that changes the decider, or the code behind `friction since`, cannot judge its own run with that change.
- **What is still the pull request's.** The steps before the decision, such as `uv sync` and `pkit sync`, run the pull request's code. What they set for later steps, such as where the deciding step finds `uv`, `git` and `gh`, is trusted as the pull request's workflow is ("What the status trusts").
- **A base with no decider** leaves the run full.
- **On any other event,** the tree's own decider runs, and only says why the run is full.

### 6. Every doubt runs the full suite

The decider chooses the short check only by naming it, as its last act. Anything else leaves the full run, among others:
- a re-run. Its own first attempt is left out of the runs read, so a full run that failed could otherwise pass on its re-run with no suite.
- a branch another pull request has had as its head, or a pull request whose base was changed
- no full run on the pull request, or none among the runs read
- a full run that failed, was cancelled or has not finished
- an answer from GitHub that cannot be read, or a run that cannot be told, such as one listed for no pull request or for another
- more runs, events or pull requests of the branch than the decider reads
- a checkout that is not the merge of the head judged, point 7
- a pull request from a fork, whose runs lie on no branch of this repository
- `pkit friction since` unable to answer, as in a shallow clone, or answering in a version the decider does not know
- a base that cannot be checked out, or that holds no decider
- the deciding step itself failing, which never fails the job

### 7. What a green `checks` means

On a full run, as before. On the merge of this head with the base as the run saw it, every line of the aggregator passed, the suite included, and so did the changeset guard.

On a short check, these hold together:
- **This head.** On its merge with the base as the run saw it, every line of the aggregator but the suite passed, and so did the tests marked `answers` and the changeset guard. The decider checks that the commit the run checked out is that merge: its second parent is the head it judged.
- **An earlier head.** The suite passed on the basis, merged with the base as that run saw it.
- **Between them.** Only answers changed, and merges of the base, clean or resolved inside the answers. The base may also have moved on with no merge on the branch.
- **Who said so.** The base's decider, reading GitHub's record of runs and the base's `pkit friction since`.

So the suite never ran on this head, nor on its merge with the base as it now stands. The first full run of that combination is the push to `main` after the landing. This is the gap the short check leaves, declared here as an enforcement gate declares its residual gap ([ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md) point 3).

### 8. The tests that read the answers

The suite is skipped on the premise that an answer changes nothing a test finds. A test that asserts what the repository's own answers hold breaks that premise. Two do today:
- one holds every declared place to a revalidation
- one holds the shipped analysis rule set's judgement rules to no deferral

Such a test is marked `answers`, and the short check runs the marked tests.
- **No mark is needed** for a test that only runs a validator over the tree. The short check runs `pkit validate` itself.
- **The mark is held.** The short check passes where no test is marked. So a test of the full suite holds the two tests named above to the mark, and a change that drops it runs in full.
- **The residual gap.** It is wider than the tests that assert what the answers hold. Any test that reads an artefact file's bytes can break on an answer: one that compares the file whole with a copy, hashes it, reads its line numbers, or meets it through a fixture or a template copied from this tree. Unmarked, such a test is skipped. An answer that only such a test rejects passes the short check, and the full run on `main` finds it after the landing.

### 9. What the job says, and what its token can do

The job's summary says which form ran and why: the basis, with its run, or the reason the run is full. Where the deciding step gave no answer, as when it failed before the decider started, the full run's step says that the run is full, and how the deciding step ended. What a file's author or a tool named is set in code spans there, so none of it renders as Markdown.

The job's token may only read the repository's contents, its runs and its pull requests. The checkout keeps the token out of the clone's configuration. Of the steps that run the project's code, only the deciding step is handed it.

### 10. What the pre-push hook runs

The pre-push hook runs the full aggregator, as before, and decides nothing. So a round pushed from a clone with the hook still waits for the suite there. Whether the hook may skip it too is left out of this record. `--short` by hand runs the short check locally, and no gate reads that run.

## Rationale

**Why skip the suite.** The suite takes about twenty of a full run's twenty-one minutes. The rest takes under two. An answer cannot change what the suite finds, save through the marked tests. Rounds are frequent, so the waiting adds up across every open pull request.

**What the short check gives up.** A round happens because the base changed a file the pull request answers on, as the landing command's firm stop says (DEC-055 point 3), or because two answers conflicted. Two answers on one document usually mean both changes touched what that document anchors. So the run a short check skips is not a random one. It is the one most likely to catch a clash between this change and the change that just landed. On `main` today, that run is the only test of the pair before the landing. Under this record, the push to `main` after the landing is the first. A merge queue would test the pair before the landing again (Alternatives).

**Why the most recent full run, not the last one that passed.** Keyed on the last head that passed, a failure could hide. A full run that fails, followed by a push of answers only, would pass the short check against the older head. The most recent full run must itself have passed, so a failed run always makes the next run full. The critic raised this on the design note.

**Why GitHub's record of runs.** The basis must be a run that really passed. A label, a comment or a file in the pull request would let the contributor name any head. GitHub's record of a run, its job's steps and their conclusions is written by the Actions service, from the workflow the run used. The token the workflow holds can read it, with no secret added.

**Why the steps' names mark the form.** The Actions API returns each job's steps with their conclusions. It gives no other field a step can set, and an Actions job's check run carries no output. A line in a job's summary or log could be printed by any test. A marker file uploaded beside the run would need another permission and a download per run. The full run's step keeps the name it had, so runs from before this record read as full.

**Why the base decides.** On a `pull_request` event everything runs from the pull request's own commits. A decider from those commits would judge a change to itself. A slip that read code as an answer would give that very push the short check, and skip the tests that would find the slip. The base's decider passed the full run of the pull request that landed it. A slip in a pull request's decider is caught by that pull request's own full run, before it decides anything. `main`'s tip may itself be broken, as the Implications say, so what the base's code has for it is that run, not a run of the tip.

**Why `pkit friction since`.** DEC-055 point 3 already decides, with it, whether a person's authorisation covers a later head. CI asks the same question of the same heads. A second reading of the answers would drift from the first, and would not follow when answers move into files of their own.

**Why a merge of the base counts only for its difference.** The status never covered the pair that lands, since a branch need not be up to date. A round's full run tested the merge of that moment, and later landings outdate it anyway. The short check gives up that test, as "What the short check gives up" says. The full run on `main` after each landing stays the backstop.

**Why the aggregator with a flag.** The aggregator is the one source of what must pass, for the hook and CI alike. Leaving out only the suite keeps every check that reads the change. A check added to the aggregator joins the short check with no second edit.

**What the status trusts.** Before this record, nothing could skip the suite on a pull request. Now the status trusts three things it did not, and the rest as before.
- **New: the base's decider and `friction since` being right.** A bug in either, not only an attacker, can now skip the suite on a change that is not answers only. The guard is that both are the base's, so a change to either is tested by its own pull request's full run before it decides anything. Project-management DEC-055 point 3 trusts the same predicate, so one misjudgement now meets neither safeguard (Implications).
- **New: GitHub's record of runs being whole.** The basis trusts that GitHub lists every run of this workflow on the branch, and records each job's steps and their conclusions as they ran. Point 3 refuses a run it cannot tell, a run listed for no pull request or another, and a listing longer than the decider reads. Someone who can delete runs can still take away the most recent full run, which failed. Someone who can push a branch to this repository can make a run pass with no suite, through a pull request against a base of their own; point 3 refuses the two routes that would carry such a run to this pull request, another pull request on the branch and a change of base. Both could already put a green `checks` on any head, since `main`'s rule names only the app that writes the status.
- **New: the commit tested is the merge of the head judged.** The decider checks it, point 7, so this rests on the checkout's history as git reads it.
- **As before: the pull request's own commits.** The workflow, the aggregator, the short check's step and the steps before the decision run from them, as every check of a pull request does. A contributor who edits them can make the job say anything, with or without this record, such as through what an earlier step sets for the deciding step. Such an edit shows in the pull request's diff, as an edit to the aggregator that skips the suite would.

### Alternatives considered

- **Key on the last head that passed.** Rejected, for the hidden failure above.
- **Let the pull request name its basis,** by a label or a comment. Rejected: the contributor would choose what the status trusts.
- **Let the pull request's own copy decide.** Rejected, for the slip above.
- **Skip the workflow by paths.** Rejected. A skipped workflow reports no status, so `main`'s rule would wait for ever. A path filter also cannot tell an answer from the text beside it in one file.
- **Make the suite a job of its own,** which the decision skips and the required job waits on. Its conclusion would mark the form more plainly than steps' names. Rejected: the aggregator would no longer hold the suite, so the hook and CI would part, and every run would set up twice.
- **Move the two assertions on the answers out of the suite,** into a line of the aggregator, so that no mark is needed. Not taken: both tests assert much besides the answers, and the mark keeps them whole.
- **Cache the suite's result by a tree with the answers taken out.** Rejected. It needs a second reading of the answers, and a pull request's run can write a cache that a later run trusts.
- **Run only the tests a change affects.** Rejected: no reliable map from a change to the tests it can break exists here.
- **Pair the short check with a merge queue.** Already the end state that ADR-055 point 5 decided, and its tooling has landed (#1011). Turning it on is a setting of `main`'s ruleset, which the operator applies. A queue's run is always full (point 2), on the merge it is about to make, so every landing would be tested on the true pair first. The short check would then leave no gap before the landing, and point 8's residual gap would close too. Until then, point 7's gap is interim.
- **Keep the full run on every push.** The status quo. Rejected by the maintainer for the cost above.

## Implications

- **The workflow.** `.github/workflows/checks.yml` gains the deciding step and the short check's step. Its job may only read contents, runs and pull requests, and its checkout keeps no token. `scripts/short_check.py` decides, and `scripts/check.sh` takes `--short`. Tests pin the decision, the deciding step's shell, the workflow's gates and the short form.
- **The first pull request.** The pull request that brings this record finds no decider on its base, so its own runs are full. The short check starts once it lands.
- **The suite.** A test that asserts what the repository's own answers hold carries the `answers` mark. `tests/README.md` says so.
- **The documentation.** `CONTRIBUTING.md`, under "Running checks", and `tests/README.md` say when the short check runs. Project rule 2 says CI may skip the suite on a head that changed only answers.
- **ADR-055 point 5.** Its statement that every check the aggregator runs is a gate holds, but for the suite on a head the short check passes. It points here.
- **DEC-055 point 3's "its checks pass".** The landing command lets a person's authorisation cover a later head when only answers changed and its checks pass. On such a head the checks are now the short check. So one predicate, `pkit friction since`, decides both whether the person's authorisation covers the head and whether the suite runs on it. A misjudgement in it, which the suite used to catch on its own, can now land a change that no person reviewed and no suite tested before the landing. The full run on `main` after the landing still finds what the suite would.
- **The deciding step's cost.** Every pull request run now builds the base's environment and asks `friction since` before either form starts. `friction since` is bounded at fifteen minutes, and one that overruns is no answer, so the run is full.
- **Two effects to watch.**
  - Nothing ties a failure on `main` to a landing that a short check passed. The job's summary names the basis, which is where to look.
  - A broken `main` turns every full run of a pull request red, since each tests its merge with `main`. A short check skips the suite, so a pull request it passes stays green on a broken `main`.
- **A `none` changeset and no migration.** Nothing here ships to adopters. It is project-kit's own CI. Project rule 2 lies in the backbone's tree, so a backbone `none` changeset covers its edit.
- **When answers move into files of their own (#1779).** The predicate follows through `pkit friction since`. Whether the short check is still worth keeping is decided then.
- **Revisit** if a test that reads the repository's own answers, or an artefact file's bytes, is found without the mark, if the full run on `main` starts to find what a short check passed, if the deciding step grows to a share of a full run, or once the merge queue is turned on.
- **Stands on** COR-050, ADR-019, ADR-055, ADR-057 and project-management DEC-055, all accepted.
