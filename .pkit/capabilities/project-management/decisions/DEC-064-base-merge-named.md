---
id: DEC-064
title: This capability's commands ask for a merge of the base only in named cases
status: proposed
date: 2026-11-04
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A pull request's branch leaves its base at one commit, and the base moves on as other pull requests land. Taking in the base, by merging it into the branch, makes a new head. A new head costs a run of the checks and answers asked again, as the Rationale sets out ("Why the base is not merged before every landing").

Leaving the base out has costs too. Friction results are valid only against an up-to-date base ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 6). The landing command checks the merge it would land, with the base as it stands just before the merge ([project-management:DEC-055-pr-lists-answers] point 6). Some hosts merge only an up-to-date branch.

A habit of merging the base before every landing pays a new head's costs on every open pull request after every merge. This record decides when this capability's commands and skills have a branch take in its base.

## Decision

**No command or skill of this capability merges the base into a pull request's branch, or tells its author to, only because the base has moved on. The landing command names that merge in four cases: a conflict with the base, a check of the merge that fails, a base that changed what the list of answers shows, and a host that merges only an up-to-date branch reading the branch as behind. This capability's commands and skills tell the pull request's author to take in the base where it conflicts, where the landing command names the merge, or where the author judges that a check failing only on the host's merge or the queue's needs it. A person may still merge it whenever they choose. Leaving the base out leaves two gaps open, which point 7 names.**

### 1. The merges the landing command names

A command names a merge when it stops and gives the merge of the base to make, with the command that makes it. It names one only where the head does not already hold the base's tip. The landing command names it in these cases, and in no other:

- **A conflict.** The host reads the pull request as conflicting with its base, or the merge the check of the merge builds conflicts (DEC-055 point 6).
- **A check that fails at the merge.** The change check fails on the merge as it would land, in the project's mode (DEC-055 point 6).
- **What the list shows.** The change wrote answers or alters the friction settings the list shows, and the base's commits since the head left it changed a file the list's words are on, or those settings. The merge is named too where which of them the base changed cannot be read (DEC-055 point 3).
  - **The files the list's words are on** are the ones the change check names for its answers. Each is an answer file the change adds, or an artefact's own file, for an answer in its block or a target revisited by changing it.
- **A host that merges only an up-to-date branch.** Such a host reads the branch as behind its base, or refuses the merge of the head for it. Point 2 sets out when the landing command takes that reading.

### 2. When the host's reading is taken

- **With the checks.** The landing command reads whether the host reads the branch as behind in the same reading as the checks on the head, before the review and the ready stop. That reading is best effort.
- **A reading not settled.** A reading the host has not settled goes on, and so does one that names another block than a branch behind its base. On GitHub these read `UNKNOWN`, and `BLOCKED` rather than `BEHIND`.
- **A queue.** A pull request whose base merges through a queue is not stopped, since the queue builds the merge with the base itself ([project-management:DEC-026-work-ownership-lifecycle]). Where whether the base merges through a queue cannot be read, the landing command says so in one line and goes on.
- **At the merge.** Where the host refuses the merge of a head it reads as behind, the landing command names the merge then, unless the base merges through a queue. A behind branch the reading with the checks missed then costs a re-run after a clean merge of the base. It needs no new authorisation where nothing at the new head needs the person (DEC-055 point 3).

### 3. What names no merge

- **The change check's report of an outdated base.** The change check reports a base that moved on, and fails nothing on it, since the fix is to update the branch and run again (COR-050 point 12). The check of the merge is that run again, with no new head: it judges the change with the base as it stands (DEC-055 point 6).
- **A refusal a new head might cure, where the host does not read the branch as behind.** An example is a check the base came to require after the head was pushed. The landing command reports it as a failed request, as it reports any other.
- **A check that fails on the host's merge, or the queue's, where the branch alone passes.** The base's changes then meet this change's. No command can tell a failure that taking in the base settles from one it does not, so none names the merge. The author judges it (point 4).

### 4. Where the pull request's author takes in the base

This capability's commands and skills tell the author of a pull request, an agent or a person, not to take in the base only because it moved on. They tell the author to take it in where one of these holds:

- **A conflict.** The pull request conflicts with its base.
- **A named merge.** The landing command names the merge (point 1).
- **A check that fails only on the host's merge or the queue's.** The author judges whether taking in the base settles it, and merges where they judge it does, or a person judges it and merges (point 3).

The change check's report of an outdated base, and the merge or rebase it advises, name no merge (point 3). In a project with a topology, the author makes the merge into a worker's Task branch through the build command ([project-management:DEC-063-task-builder] point 1). A person may still merge it whenever they choose (point 5).

### 5. A merge of the base a person makes

A person may merge the base into a pull request's branch whenever they choose: a clean merge keeps every verdict ([project-management:DEC-028-agent-as-approver-paths]), and an authorisation can cover the head it makes (DEC-055 point 3).

- **In a project with a topology,** the provenance check refuses such a merge into a worker's Task branch, unless it goes through a build (DEC-063 point 1).

### 6. An integration branch

A scope's pull requests may target an integration branch, a shared branch that reaches the default branch through a pull request of its own ([project-management:DEC-013-branch-and-pr-conventions]). For each pull request into it, the integration branch is the base, and points 1 to 5 hold as for any base. DEC-013 does not decide when an integration branch takes in the default branch outside its own pull request, and this record leaves it open. No command or skill of this capability merges the default branch into it there, or tells anyone to.

### 7. What leaving the base out leaves open

Accepting this record accepts two gaps.

- **A semantic conflict.** The checks on a pull request judged the change against the base as the pull request last saw it (DEC-026). The check of the merge judges it with the base, but runs the change check alone. So changes that merge cleanly but no longer work together can reach the default branch.
  - **No review catches it,** merging or not, since a clean merge of the base keeps every verdict (DEC-028).
  - **Its backstop runs after landing.** DEC-028 meets the same conflict, after a clean merge of the base, with the checks on the merged head, which run before the pull request lands. With the base left out, the checks that run on the default branch after each merge catch it, once it has landed.
  - **A queue, or a host that merges only an up-to-date branch,** runs the checks on the merged result before it lands (DEC-026).
- **A rule the base accepted.** An artefact no rule bound at the head may come under a rule the base accepted after the branch left it. The required reviewers resolve from the rules where the branch left its base, an answer that holds only against an up-to-date base ([project-management:DEC-032-conditional-reviewer-requirements] D1).
  - **The usual path.** Where the host does not require an up-to-date branch, this record makes leaving the base out the usual path, so the case is common. A change can then land text under that rule without the reviewer the rule would require.
  - **A reviewer required already** keeps its approval through a clean merge of the base (DEC-028).
  - **The follow-up #2661 closes it.** The check of the merge resolves the required reviewers on the merge, and names the merge where that adds one.

## Rationale

**Why the base is not merged before every landing.** A merge of the base makes a new head, and two costs follow.
- **The checks run again.** Every check on the pull request runs on the new head, for nothing the change's author did.
- **Answers are asked again.** Where the base answered a document the change answers too, the change answers it again, naming the base's answer ([COR-062](../../../decisions/core/COR-062-answers-in-own-files.md) point 4). Those answers are words the reviewer of the answers has not checked.

On a busy default branch every open pull request would pay both after every merge.

**Why the check of the merge stands in for a merge just before landing.** COR-050 point 6 holds friction results valid only against an up-to-date base. A project that enforces friction meets that point by requiring up-to-date branches, or by merging through a queue that re-runs the check on the merge it is about to make. The check of the merge does not meet that point. It stands in for a merge of the base just before landing. It runs the change check on the merge the landing command is about to make (DEC-055 point 6), as a run after such a merge would, without a new head.
- **Where it falls short.** The check does not hold the base still. A commit that reaches the base between the check and the merge lands unchecked against this change (DEC-055 point 5). A queue holds the base still, and an up-to-date host makes the branch take in each commit. So for a project that enforces friction, those two stay COR-050 point 6's requirement, not options. Point 1 names the merge an up-to-date host asks for.
- **A merge by another command.** A merge through this capability's other merge commands, or outside it, takes no check of the merge (DEC-055 point 5). A project that enforces friction and merges so, with neither an up-to-date host nor a queue, does not meet COR-050 point 6. Its host's settings are what meet that point, so this record leaves the case as it is.

**Why these merges are named.** In each case the pull request cannot land as it stands, or would land what nobody checked. A conflict, or a host that merges only an up-to-date branch, stops every merge until the branch takes in its base. A check that fails at the merge needs the change to answer what the merge would land. A base that changed the list's files or settings would land words the list does not show (DEC-055 point 3). Where which of them it changed cannot be read, the merge is named too, since once the branch holds the base nothing is left to read.

**Why the host's reading is taken with the checks.** The early reading buys one thing: where the host's reading has settled, the first run, before any authorisation, never stops ready on a head the host would refuse as it stands. A reading not settled, one of another block, and a queue that cannot be read go on rather than stop on a guess. Where one of them hides a branch behind its base, the host's refusal at the merge costs a re-run after a clean merge of the base. It needs no new authorisation where nothing at the new head needs the person, since the authorisation covers the head such a merge makes (DEC-055 point 3).

**Why a refusal a new head might cure is not named.** Telling it from a refusal no new head cures needs the host's rules for the base branch, which not every account may read. Naming a merge on a guess would ask for merges that cure nothing.

**Why the author judges a check that fails only on the host's merge.** Only a reading of the failure tells whether the base's changes caused it, and no command reads one. Naming a merge on every such failure would ask for merges that cure nothing where the change itself caused it.

**Why naming a merge costs no verdict.** A clean merge of the base is no change of the author's, for the reasons DEC-028 gives. So a merge point 1 names keeps every verdict, and the authorisation can cover the head it makes (DEC-055 point 3).

**Why the gaps are accepted.** The semantic conflict is this record's own gap, not the one DEC-028 accepts. There, the checks on a merge of the base run before landing. Here, they run on the default branch after it, so such a conflict can land before any check finds it. The record takes that risk rather than have every open pull request merge the base after every merge. A project that will not bear it runs a queue, or a host that merges only an up-to-date branch. The rule gap is left open for now, not for good. A cheap test would close it: one reading, by the backbone, of what the change alters or brings under a rule, from the base's tip to the merge the check of the merge builds. It need run only where a contribution in force names the `touches-ruled-artefact` floor and the base moved on (#2661).

**Why the record binds only this capability's commands and skills.** It decides what this capability's commands do, and what they and its skills tell an author. A person's own merge is their choice (point 5). An integration branch is a construct of its own (DEC-013).

### Alternatives considered

- **Merging the base before every landing.** Rejected. Every open pull request would pay a run of the checks and answers asked again after every merge.
- **Merging the base once, just before landing, by default.** Rejected. The check of the merge runs the change check on that merge without making a new head. A merge first adds a head, a run of the checks and answers written again. That merge would also run the checks on the merged result, which this record leaves to the run after the merge.
- **Naming no merge, leaving each to the host's refusal.** Rejected. A check that fails at the merge, or a base that changed the list's words, would merge what nobody checked wherever the host does not refuse it.
- **A rule for every branch.** Rejected. It would bind a person's own choice and the integration-branch construct, neither of which this capability's commands need to bind.

## Implications

- DEC-055 points 3 and 6 stop the landing, and cite this record for the merge each stop names.
- The landing command reads whether the host reads the branch as behind with the checks on the head, unless the base merges through a queue (point 2). It names the merge there, and where the host refuses the merge of such a head. The capability README lists the cases.
- The pm skill's landing step says where the author takes in the base (point 4).
- In a project with a topology, a merge this record names is built through the build command, since the provenance check refuses a commit on a worker's Task branch that no recorded build produced (DEC-063 point 1). So the provenance check finds it among a build's commits.
- The backbone's change check advises a merge or a rebase with its report of an outdated base, and COR-050 point 12 names updating the branch as the fix. #2662 has the backbone state the fact and leave the remedy to the workflow, and rewords COR-050 point 12 to match.
