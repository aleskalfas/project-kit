---
id: DEC-079
title: A bot's account stands for no person, and in human mode neither does a reviewer agent's
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** in every project, under every credential, a bot's account stands for no person: an app's account, and any other the backbone's one spelling of accounts reads as a bot's ([pkit:ADR-094]). No command makes it an assignee or hands it a Task, since an assignee names a person, and no claim on work it writes counts wherever the claim names who wrote it. In human mode, no approval counts from a bot's account or from an account the project registers as a reviewer agent's, and human mode asks neither for a review. A bot's request for changes still holds a merge until a person approves after it. Where that spelling cannot tell an account's kind, as for a bot whose login the service gives with no `[bot]` suffix, a claim from it is held, and an approval from it counts for nothing.

## Context

**The terms.**

- **The backbone's spelling of accounts** is its one function that puts an account any surface names into one spelling that carries the account's kind, and compares accounts ([pkit:ADR-094] point 3).
- **A bot's account** is one that spelling reads as of the bot kind. An app's account is one.
- **An account of a kind unknown** is one that spelling reads as neither a user's nor a bot's, such as an account the service records as a bot's but gives with no `[bot]` suffix.
- **A reviewer agent's account** is one the project registers in the remote path's list ([project-management:DEC-028-agent-as-approver-paths]). It may be a user's account kept for an agent, which the service records as no bot.

**What the records say.**

- **Assignment names a person.** Every issue has an assignee, someone responsible, in closed mode a member and in open mode any account ([project-management:DEC-019-mandatory-issue-state], "Mandatory assignment").
- **A claim on an issue of work counts only from the assignee's account** ([project-management:DEC-043-ownership-substrate-selection] point 3), a filter the ownership fold applies in one place ([pkit:ADR-041] point 2). A claim on a state issue counts by its author's standing ([pkit:ADR-071] point 3), which this record leaves as it stands.
- **In human mode,** the gate passes on an approving review or an `Approved` comment from any non-author identity, and the members whose role matches, but the author, are assigned as reviewers ([project-management:DEC-027-review-modes], "Human path"). [project-management:DEC-026-work-ownership-lifecycle]'s tables count the comment from a commenter other than the author, and its Rationale ("Why the three-way OR") from the last commenter that is no bot. The commands count it from any commenter but the author, a bot among them. Of the reviews, they read DEC-026's "latest APPROVED review" as the latest review that approves, requests changes or was dismissed, and pass where it approves.

**What was measured.** On a trial where an agent ran under an App installation's token ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)), the comments the App wrote, read under a person's credential, gave its login with a `[bot]` suffix and the type `Bot`. gh's JSON gave the same account on its pull requests with an `app/` prefix, marked as a bot. The service also lets an app take its owner's own name, and lets some bots be assigned, as it lets its own coding agent be.

## Decision

**In every project, a bot's account stands for no person: no command makes it an assignee, no claim on work that names its author counts from it, and in human mode no approval counts from it or from a reviewer agent's account.**

Which account is a bot's, and whether two accounts are one, the commands read as the backbone's spelling of accounts has it (ADR-094 point 3), in each rule below.

### 1. An assignee is never a bot's account

- **No bot as an assignee.** No command makes a bot's account an assignee, at filing, on an assignment or by handing a Task to it, whether or not a member's entry names it, since assignment names a person (DEC-019). `handoff-issue` hands a Task from one person to another.
- **A kind it cannot tell.** A command given an assignee whose kind it cannot tell makes it no assignee either, as a use that cannot tell refuses (ADR-094 point 3).

### 2. A claim on work never counts from a bot's account

- **Never from a bot's.** A claim on an issue of work counts only from the assignee's account, and never from a bot's account, even one the service lets be assigned. The guard reads the author's kind, never whether the service lets that author be assigned.
- **A kind unknown.** A claim whose author is of a kind unknown is held, as a claim the ownership fold cannot judge (ADR-094 point 3). So a claim from an account the service records as a bot's but gives with no suffix is held, not counted and not freed.
- **Labels.** A label names no author, so under the label substrate the guard has nothing to read, and a label counts as [project-management:DEC-035-instance-ownership] has it.

### 3. In human mode, only a person's approval counts

- **Who approves.** An `Approved` comment or an approving review counts only from an account the spelling reads as a user's, and that the project does not register as a reviewer agent's. So an approval from a bot's account counts for nothing, nor does one from an account of a kind unknown.
- **The order of reviews.** The latest review that approves, requests changes or was dismissed decides, as the commands read DEC-026's "latest APPROVED review", and it passes only where it approves. An approval that does not count is left out of that order. So a bot's request for changes holds the merge until a person approves after it, as a person's request does, and a bot's approval clears nothing.
- **Who is asked.** Human mode assigns as a reviewer no member whose entry names a bot's account or a reviewer agent's account.

## Rationale

**Why an assignee is never a bot's account.** An assignee says who is responsible for the work (DEC-019). A bot answers for nothing it does: the person who set it to work does. Assigned to a bot, a Task names nobody responsible, and the bot's claims on it count for nothing (point 2).

**Why the guards read an author's kind.** A claim means something because only the assignee's own account can make it (DEC-043 point 3). A guard derived from the service refusing a bot as an assignee would fail once a bot can be assigned. Read from the author's kind, the guard holds for every bot, whatever the service lets it be, and alike on every machine, since an author's kind is the same wherever it is read.

**Why an account of a kind unknown is held, not counted as a bot's.** The backbone's spelling leaves a bot whose login carries no suffix of a kind unknown, since nothing measured says every surface gives it one login (ADR-094 point 3). This record follows that spelling, so such an account's claim is held, as the fold holds every claim it cannot judge. It costs a Task such an account is assigned and claims a hold no reader can judge, which the clash guard reads as a claim that counts (DEC-035 point 6), until a person assigns the Task to another or removes the comment. A claim such an account writes on a person's Task is void, as any other account's is, since the person's login tells the two apart (ADR-094 point 3). Counted as a bot's instead, the claim would free a Task whose claim no reader can tell from its assignee's, on a reading no measurement backs.

**Why a bot approves nothing in human mode.** Human mode asks for a person's approval. DEC-026's Rationale already counts the comment only from a commenter that is no bot, and reading the approver's kind brings DEC-026's tables, DEC-027 and the commands to that rule, and applies it to reviews too. A request for changes stays in the order, since holding a merge back grants nothing, and a person's later approval clears it as it clears a person's request.

**Why a reviewer agent's account approves nothing, and is not asked.** A reviewer agent's account names no person, whatever the service records of it, and the project already names those accounts (DEC-028). Asked for a review, it would be asked for an approval that cannot count. This assumes a project registers no person's own account as a reviewer agent's. A maintainer whose own account runs the remote reviewer, such as through their own token, loses their approvals in human mode, so such a project registers an account of the agent's own.

**What it costs a project that assigns work to a bot,** such as the service's own coding agent. It assigns the bot on the service's own surface, outside the commands, and the commands read the Task as another's: `start-work` refuses it, as it refuses any Task assigned to someone else, and no claim the bot writes counts.

### Alternatives considered

- **Assign a bot's account where the service lets it be assigned.** The case: a project hands work to the service's coding agent through the commands. Rejected: the assignee would name nobody responsible, and the bot's claims would count for nothing.
- **Drop every review by a bot in human mode,** requests for changes included. The case: one rule for every bot's review. Rejected: a bot's request for changes would stop holding a merge, which loosens a guard for no gain.
- **Treat only the accounts the service records as bots as no person.** The case: one source for an account's kind. Rejected: a reviewer agent's user account would then approve in human mode.
- **Count a bot's claim for its assignee,** loosening DEC-043 point 3. The case: a clone under a bot's credential could take part in instance ownership. Rejected: anyone holding the credential could claim work for any person.
- **Read an account the service records as a bot's but gives with no suffix as a bot's.** The case: its claim does not count, so it holds nothing. Not taken: the backbone's spelling leaves its kind unknown, its spelling across surfaces unmeasured, and the hold costs only where such an account writes a claim.

## Implications

- **What changes in every project,** each counting less or holding more:
  - no command makes a bot's account an assignee or hands a Task to one;
  - in human mode, an approval from a bot's account, from an account of a kind unknown, or from an account the project registers as a reviewer agent's does not count, and does not clear an earlier request for changes;
  - human mode assigns no member whose entry names a bot's account or a reviewer agent's as a reviewer;
  - a claim on work from a bot's account does not count, and one from an account of a kind unknown is held.

  The order of reviews is the one the commands read, so a person's review changes nothing.
- **Refined in place,** each with the pointer `(refinement per [project-management:DEC-079-bots-are-no-person])`, citing this record's points as DEC-079 point N. This record overturns nothing.
  - **DEC-019, narrowed:** "Mandatory assignment", its `--assignee` and the schema's `values_constrained_to: members`, open in open mode: the assignee is never a bot's account, whether or not a member's entry names it, since assignment names a person (DEC-079 point 1).
  - **DEC-026:**
    - narrowed and completed: the `done-work` row of "The seven commands", and the `done-work` approval-gate row of the "Sub-decisions index": in human mode, an `Approved` comment or an approving review counts only from an account read as a user's that the project does not register as a reviewer agent's. Of the reviews, the latest that approves, requests changes or was dismissed decides, and passes only where it approves, and an approval that does not count is left out of that order.
    - narrowed: the human-mode bullet of "Reviewer assignment", and the reviewer-assignment row of the "Sub-decisions index": human mode passes over a member whose entry names a bot's account or a reviewer agent's.
    - narrowed: the `handoff-issue` row of "The seven commands": a Task is never handed to a bot's account.
  - **DEC-027, narrowed:**
    - steps 1 and 2 of "Human path: role-based reviewer assignment", the `human` row of the "Two modes" table, and the "Role-based reviewer query" row of the "Sub-decisions index": the query passes over a member whose entry names a bot's account or a reviewer agent's, so none is assigned as a reviewer.
    - step 3 of "Human path", its paragraph on a query that returns no eligible reviewers, the refusal template's "from a non-author identity", the human-mode bullet of "Open mode and review-mode", and the "Open mode + human mode" row of the "Sub-decisions index": an approving review or an `Approved` comment counts only from a non-author account read as a user's that the project does not register as a reviewer agent's.
  - **DEC-043 point 3, its bullet "Authenticity rides `author.login`," narrowed:** a marker counts only from the assignee's account, and never from a bot's, even where the bot is the assignee.
  - **[pkit:ADR-041] point 2, its bullet "Authenticity rides `author.login`," narrowed,** by the architect, whose custody it is in, with the same pointer: the fold keeps no marker from a bot's account, even where the bot is the expected assignee. The record's other mentions of that filter name it, and read true with the bullet so narrowed.
- **Accepted with or after [pkit:ADR-094],** which it cites for an account's kind and the comparison of accounts. Refusing ADR-094 leaves this record no way to tell whether an account is a bot's, so it is then revised to state one.
- **Left out, for a record of its own: which `Approved` comment counts in human mode:** the last that is no bot's, as DEC-026's Rationale has it, or any but the author's, as its tables have it. That is no question of an account's kind, and this record leaves it as DEC-026 states it.
