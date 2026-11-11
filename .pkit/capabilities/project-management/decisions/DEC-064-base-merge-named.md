---
id: DEC-064
title: This capability's commands ask for a merge of the base only in named cases
status: accepted
date: 2026-11-04
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A pull request's branch leaves its base at one commit, and the base moves on as other pull requests land. Taking in the base, by merging it into the branch, makes a new head. A new head costs a run of the checks and answers asked again, as the Rationale sets out ("Why the base is not merged before every landing").

Leaving the base out has costs too. Friction results are valid only against an up-to-date base ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 6). The reviewers the ruled-artefact floor requires resolve from the rules where the branch left its base, an answer that holds only against an up-to-date base too ([project-management:DEC-032-conditional-reviewer-requirements] D1). The landing command checks the merge it would land, with the base as it stands just before the merge ([project-management:DEC-055-pr-lists-answers] point 6). Some hosts merge only an up-to-date branch.

A habit of merging the base before every landing pays a new head's costs on every open pull request after every merge. This record decides when this capability's commands and skills have a branch take in its base.

## Decision

**No command or skill of this capability merges the base into a pull request's branch, or tells its author to, only because the base has moved on. The landing command names that merge in five cases: a conflict with the base, a check of the merge that fails, a base that changed what the list of answers shows or the friction settings the change alters, a merge that brings the change's text under a rule whose reviewer the head does not require, and a host that merges only an up-to-date branch reading the branch as behind. This capability's commands and skills tell the pull request's author to take in the base where it conflicts, where the landing command names the merge, or where the author judges that a check failing only on the host's merge or the queue's needs it. A person may still merge it whenever they choose. Leaving the base out leaves two gaps open, which point 7 names.**

### 1. The merges the landing command names

A command names a merge when it stops and gives the merge of the base to make, with the command that makes it. It names one only where the head does not already hold the base's tip. The landing command names it in these cases, and in no other:

- **A conflict.** The host reads the pull request as conflicting with its base, or the merge the check of the merge builds conflicts (DEC-055 point 6).
- **A check that fails at the merge.** The change check fails on the merge as it would land, in the project's mode (DEC-055 point 6).
- **What the list shows.** The change wrote answers or alters the friction settings, and the base's commits since the head left it changed a file the list's words are on, or those settings. The list is the change check's list of the answers (refinement per [project-management:DEC-065-answers-read-from-check]). The friction settings are no part of it, and the landing command reads them beside it. The merge is named too where which of them the base changed cannot be read (DEC-055 point 3).
  - **The files the list's words are on** are the ones the change check names for its answers. Each is an answer file the change adds, or an artefact's own file, for an answer in its block or a target revisited by changing it.
- **A reviewer the merge requires.** In agent review mode, the merge requires a reviewer of the ruled-artefact floor, one the head does not require (DEC-032 D1). The base may have accepted a rule, widened a set's scope, or otherwise brought what the change alters under a rule. Point 8 sets out when the landing command asks, and what it asks.
- **A host that merges only an up-to-date branch.** Such a host reads the branch as behind its base, or refuses the merge of the head for it. Point 2 sets out when the landing command takes that reading.

### 2. When the host's reading is taken

- **With the checks.** The landing command reads whether the host reads the branch as behind in the same reading as the checks on the head, before the review and the ready stop. That reading is best effort.
- **A reading not settled.** A reading the host has not settled goes on, and so does one that names another block than a branch behind its base. On GitHub these read `UNKNOWN`, and `BLOCKED` rather than `BEHIND`.
- **A queue.** A pull request whose base merges through a queue is not stopped, since the queue builds the merge with the base itself ([project-management:DEC-026-work-ownership-lifecycle]). Where whether the base merges through a queue cannot be read, the landing command says so in one line and goes on.
- **At the merge.** Where the host refuses the merge of a head it reads as behind, the landing command names the merge then, unless the base merges through a queue. A behind branch the reading with the checks missed then costs a re-run after a clean merge of the base. It needs no new authorisation where nothing at the new head needs the person (DEC-055 point 3).

### 8. When the reviewers the merge requires are read

The check of the merge reads the reviewers the merge requires where the change check fails nothing at the merge, in either friction mode (DEC-055 point 6). It reads them whether or not the base merges through a queue, since a queue's checks resolve no reviewer.

- **When it asks.** In agent review mode, where a contribution in force names the ruled-artefact floor, a reviewer of that floor is missing from those the head requires, and the base has moved on. Elsewhere the merge can add no reviewer the merge gate requires, so nothing is asked. In human review mode the merge gate requires no reviewer agent ([project-management:DEC-027-review-modes]).
- **What it reads of the project.** The contributions in force, the opt-outs and the project's other review settings are read where the command runs, as for the head's required set (DEC-032 D5). They are not read at the merge.
- **One question.** The landing command asks the backbone once which artefacts the change alters or brings under a rule, from the base's tip to the merge the check builds. The floor counts what that answer lists, as it counts the answer at the head (DEC-032 D1).
- **What it names.** Where the answer lists an artefact the floor counts, the landing command names the merge, with each reviewer the head lacks. After a clean merge of the base, the head requires that reviewer, and the review runs it. As at any later head, that head needs no new authorisation where nothing at it needs the person (DEC-055 point 3). A `[person]` finding in the added reviewer's verdict is among what does.
- **An answer that cannot be read** stops the landing with nothing merged, and names no merge, as a check of the merge that gives no answer does (DEC-055 point 6). Where only the merge gives such an answer, running again meets it again, and the ways out are those DEC-032 D1 names for an answer that cannot be read.

### 3. What names no merge

- **The change check's report of an outdated base.** The change check reports a base that moved on, fails nothing on it, and names no remedy (COR-050 point 12). The check of the merge runs the change check again, with no new head: it judges the change with the base as it stands (DEC-055 point 6).
- **A refusal a new head might cure, where the host does not read the branch as behind.** An example is a check the base came to require after the head was pushed. The landing command reports it as a failed request, as it reports any other.
- **A check that fails on the host's merge, or the queue's, where the branch alone passes.** The base's changes then meet this change's. No command can tell a failure that taking in the base settles from one it does not, so none names the merge. The author judges it (point 4).
- **A reviewer required already.** Where the head requires every reviewer of the ruled-artefact floor, the merge adds none, so nothing is asked (point 8). A clean merge of the base would keep each one's approval (DEC-028), so it would cost a new head and send no reviewer back to judge. Point 7 names what that leaves open.

### 4. Where the pull request's author takes in the base

This capability's commands and skills tell the author of a pull request, an agent or a person, not to take in the base only because it moved on. They tell the author to take it in where one of these holds:

- **A conflict.** The pull request conflicts with its base.
- **A named merge.** The landing command names the merge (point 1).
- **A check that fails only on the host's merge or the queue's.** The author judges whether taking in the base settles it, and merges where they judge it does, or a person judges it and merges (point 3).

The change check's report of an outdated base names no merge (point 3). In a project with a topology, the author makes the merge into a worker's Task branch through the build command ([project-management:DEC-063-task-builder] point 1). A person may still merge it whenever they choose (point 5).

### 5. A merge of the base a person makes

A person may merge the base into a pull request's branch whenever they choose: a clean merge keeps every verdict ([project-management:DEC-028-agent-as-approver-paths]), and an authorisation can cover the head it makes (DEC-055 point 3).

- **In a project with a topology,** the provenance check refuses such a merge into a worker's Task branch, unless it goes through a build (DEC-063 point 1).

### 6. An integration branch

A scope's pull requests may target an integration branch, a shared branch that reaches the default branch through a pull request of its own ([project-management:DEC-013-branch-and-pr-conventions]). For each pull request into it, the integration branch is the base, and points 1 to 5 and 8 hold as for any base. DEC-013 does not decide when an integration branch takes in the default branch outside its own pull request, and this record leaves it open. No command or skill of this capability merges the default branch into it there, or tells anyone to.

### 7. What leaving the base out leaves open

Accepting this record accepts two gaps.

- **A semantic conflict.** The checks on a pull request judged the change against the base as the pull request last saw it (DEC-026). The check of the merge judges it with the base, but runs none of the host's checks, only the change check and the question of point 8. So changes that merge cleanly but no longer work together can reach the default branch.
  - **No review catches it,** merging or not, since a clean merge of the base keeps every verdict (DEC-028).
  - **Its backstop runs after landing.** DEC-028 meets the same conflict, after a clean merge of the base, with the checks on the merged head, which run before the pull request lands. With the base left out, the checks that run on the default branch after each merge catch it, once it has landed.
  - **A queue, or a host that merges only an up-to-date branch,** runs the checks on the merged result before it lands (DEC-026).
- **A rule the base accepted.** What the change alters may come under a rule, or a rule's wording, that the base accepted after the branch left it. The ruled-artefact floor reads the rules where the branch left its base (DEC-032 D1).
  - **The usual path.** Where the host does not require an up-to-date branch, this record makes leaving the base out the usual path, so the case is common.
  - **A reviewer the merge adds** stops the landing command, which names the merge (points 1 and 8).
  - **A reviewer required already** keeps its approval through a clean merge of the base (DEC-028). It judged the head with the head's rules, so a change can land text under the base's rule that nobody judged against it. A person who wants it judged merges the base and forces the review (DEC-028).
  - **Human review mode** requires no reviewer agent at the head or at the merge (DEC-027). So no required reviewer judges the change's text under the base's rule, and the person's approval alone gates it.
  - **What point 8 does not read.** A contribution the base installs, an opt-out it withdraws, or another review setting it changes, is read where the command runs, not at the merge. Nor is a rule that reaches the base after the check, or through a queue's own merge (DEC-055 point 5).
  - **A merge by another command** takes no check of the merge (DEC-055 point 5), so nothing there reads a reviewer the merge adds.

## Rationale

**Why the base is not merged before every landing.** A merge of the base makes a new head, and two costs follow.
- **The checks run again.** Every check on the pull request runs on the new head, for nothing the change's author did.
- **Answers are asked again.** Where the base answered a document the change answers too, the change answers it again, naming the base's answer ([COR-062](../../../decisions/core/COR-062-answers-in-own-files.md) point 4). Those answers are words the reviewer of the answers has not checked.

On a busy default branch every open pull request would pay both after every merge.

**Why the check of the merge stands in for a merge just before landing.** COR-050 point 6 holds friction results valid only against an up-to-date base. A project that enforces friction meets that point by requiring up-to-date branches, or by merging through a queue that re-runs the check on the merge it is about to make. The check of the merge does not meet that point. It stands in for a merge of the base just before landing. It runs the change check on the merge the landing command is about to make (DEC-055 point 6), as a run after such a merge would, without a new head.
- **Where it falls short.** The check does not hold the base still. A commit that reaches the base between the check and the merge lands unchecked against this change (DEC-055 point 5). A queue holds the base still, and an up-to-date host makes the branch take in each commit. So for a project that enforces friction, those two stay COR-050 point 6's requirement, not options. Point 1 names the merge an up-to-date host asks for.
- **A merge by another command.** A merge through this capability's other merge commands, or outside it, takes no check of the merge (DEC-055 point 5). A project that enforces friction and merges so, with neither an up-to-date host nor a queue, does not meet COR-050 point 6. Its host's settings are what meet that point, so this record leaves the case as it is.

**Why these merges are named.** In each case the pull request cannot land as it stands, or would land what nobody checked. A conflict, or a host that merges only an up-to-date branch, stops every merge until the branch takes in its base. A check that fails at the merge needs the change to answer what the merge would land. A base that changed the list's files would land words the list does not show, and one that changed the friction settings the change alters would change what the merged check asks (DEC-055 point 3). Where which of them it changed cannot be read, the merge is named too, since once the branch holds the base nothing is left to read. A merge that requires a reviewer the head does not would land text under a rule that no reviewer it requires has judged.

**Why a reviewer the merge adds is cured by naming the merge.** A reviewer of the floor, such as the rule-set reviewer, judges what the change alters or brings under a rule at the head it reviews, with that head's rules ([COR-057](../../../decisions/core/COR-057-rule-set-reviewer.md) point 1). At a head without the base's rule, it finds nothing under that rule to judge. So the cure is a head that holds the base, which a merge of the base makes without costing a verdict (DEC-028). The check of the merge builds that merge already, so one question to the backbone tells whether it requires the reviewer.
- **Only the ruled-artefact floor.** The closing issues' classification and the changed paths are the change's own, and the review settings are read where the command runs. So only what binds rules on artefacts can differ between the head and the merge: the rules, their scopes, the declared places and their types.
- **The settings where the command runs.** The merge gate reads the contributions and the other review settings where it runs (DEC-032 D5). Reading them at the merge would give the landing command a required set the gate does not check.
- **Only where a reviewer could be added.** Each question costs one run of the backbone, which reads the rule sets at two states of the repository. Where no contribution in force names the floor, where the head requires every reviewer of it already, or where the head holds the base's tip, the answer can add nobody. So nothing is asked there.
- **What that leaves to pay.** The question still runs on most landings of a change the floor does not reach at the head, once the base has moved on, and most such runs add nobody. That run is the price of finding the reviewer the merge adds, at the one moment the merge is built.
- **Asked at the merge alone.** The question could also run with the checks, as the host's reading does (point 2), and stop before the review. It would then need a second run at the merge for a base that moved since, so this record asks once.
- **Agent review mode alone.** In human review mode a person's approval is the gate, and the merge gate requires no reviewer agent (DEC-027). So the merge can add none that the gate requires.
- **An answer that cannot be read stops the landing.** Where the ruled artefacts cannot be read, the required set fails, and no command proceeds without the reviewer (DEC-032 D1). It names no merge, since nothing tells whether a merge would cure it.

**Why the host's reading is taken with the checks.** The early reading buys one thing: where the host's reading has settled, the first run, before any authorisation, never stops ready on a head the host would refuse as it stands. A reading not settled, one of another block, and a queue that cannot be read go on rather than stop on a guess. Where one of them hides a branch behind its base, the host's refusal at the merge costs a re-run after a clean merge of the base. It needs no new authorisation where nothing at the new head needs the person, since the authorisation covers the head such a merge makes (DEC-055 point 3).

**Why a refusal a new head might cure is not named.** Telling it from a refusal no new head cures needs the host's rules for the base branch, which not every account may read. Naming a merge on a guess would ask for merges that cure nothing.

**Why the author judges a check that fails only on the host's merge.** Only a reading of the failure tells whether the base's changes caused it, and no command reads one. Naming a merge on every such failure would ask for merges that cure nothing where the change itself caused it.

**Why naming a merge costs no verdict.** A clean merge of the base is no change of the author's, for the reasons DEC-028 gives. So a merge point 1 names keeps every verdict, and the authorisation can cover the head it makes (DEC-055 point 3). A merge point 8 names adds a reviewer, which runs once at that head.

**Why the gaps are accepted.** The semantic conflict is this record's own gap, not the one DEC-028 accepts. There, the checks on a merge of the base run before landing. Here, they run on the default branch after it, so such a conflict can land before any check finds it. The record takes that risk rather than have every open pull request merge the base after every merge. A project that will not bear it runs a queue, or a host that merges only an up-to-date branch. Of the rule gap, point 8 covers a reviewer the merge adds, and the rest stays open.
- **A reviewer required already.** No merge would send it back to judge, since a clean merge keeps its approval (DEC-028). Every command that judges whether a verdict stands applies DEC-028's one rule, so none disagrees about it. Closing that part would take a change to that rule, which is DEC-028's to decide.
- **Human review mode.** The person's approval is the gate there by the project's choice (DEC-027), so no reviewer agent is asked for.
- **Settings the base changes, and a base that moves after the check.** They are read as the merge gate reads them, and the check does not hold the base still ("Where it falls short" above).
- **A merge by another command.** Its host's settings meet an up-to-date base, as for friction ("A merge by another command" above).

**Why the record binds only this capability's commands and skills.** It decides what this capability's commands do, and what they and its skills tell an author. A person's own merge is their choice (point 5). An integration branch is a construct of its own (DEC-013).

### Alternatives considered

- **Merging the base before every landing.** Rejected. Every open pull request would pay a run of the checks and answers asked again after every merge.
- **Merging the base once, just before landing, by default.** Rejected. The check of the merge runs the change check on that merge without making a new head. A merge first adds a head, a run of the checks and answers written again. That merge would also run the checks on the merged result, which this record leaves to the run after the merge.
- **Naming no merge, leaving each to the host's refusal.** Rejected. A check that fails at the merge, or a base that changed the list's words, would merge what nobody checked wherever the host does not refuse it.
- **Resolving the required reviewers against the base's tip, at the head.** Rejected. The reviewer would be required, but it would judge the head with the head's rules, so it would find nothing under the base's rule. Its approval of nothing would then survive the clean merge (DEC-028), so the rule would never be judged.
- **Running the reviewer on the merge the check builds.** Rejected. A verdict stands for a head of the pull request (DEC-028), and the merge lies on no branch, so the merge gate could not count it.
- **Naming the merge wherever it brings text under a rule.** Rejected where the reviewer is required already. A clean merge keeps its approval (DEC-028), so the merge would cost a new head and send no reviewer back to judge.
- **Naming the merge and a forced review where the reviewer is required already.** Rejected. Forcing the review on every such merge would give the landing command a freshness rule of its own, while DEC-028 has every command judge a verdict by one rule. DEC-028 leaves the forced review to a person who wants the change judged as it stands.
- **Resolving the reviewers at the merge in the merge gate, for every merge.** Rejected. The landing command is where this capability checks the merge it would land (DEC-055 point 6). A project that merges through another command meets an up-to-date base through its host's settings, as for friction ("A merge by another command" above).
- **A rule for every branch.** Rejected. It would bind a person's own choice and the integration-branch construct, neither of which this capability's commands need to bind.

## Implications

- DEC-055 points 3 and 6 stop the landing, and cite this record for the merge each stop names. DEC-055 point 6 says too that, where the change check fails nothing at the merge, in either mode, the step stops where the merge requires a reviewer the head does not (point 8).
- The landing command reads whether the host reads the branch as behind with the checks on the head, unless the base merges through a queue (point 2). It names the merge there, and where the host refuses the merge of such a head. The capability README lists the cases.
- In agent review mode, where the base moved on and a reviewer of the ruled-artefact floor is missing from those the head requires, the check of the merge asks the backbone the question of point 8. It names the merge where the answer adds a reviewer. The capability README lists the case.
- The pm skill's landing step says where the author takes in the base (point 4).
- In a project with a topology, a merge this record names is built through the build command, since the provenance check refuses a commit on a worker's Task branch that no recorded build produced (DEC-063 point 1). So the provenance check finds it among a build's commits.
- The backbone's report of an outdated base names no remedy (COR-050 point 12), so it advises no merge of the base.
