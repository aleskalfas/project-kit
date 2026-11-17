---
id: DEC-079
title: No claim or approval counts as a person's from a bot's account or a reviewer agent's
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** in every project, under every credential, nothing an account the hosting service records as a bot writes counts as a person's claim on work, and in human mode no approval counts from a bot's account or from an account the project registers as a reviewer agent's. A bot's request for changes still holds a merge until a person approves after it. The commands compare accounts in one spelling that keeps whether each is a bot's, and where they cannot tell an account's kind, the comparison grants nothing and frees nothing.

## Context

**The terms.**

- **A bot's account** is one the hosting service records as a bot, as it records an app's account.
- **An account's kind** is whether the service records it as a bot's.

**What the records say.**

- **A claim on an issue of work counts only from the assignee's account** ([project-management:DEC-043-ownership-substrate-selection] point 3), a filter the ownership fold applies in one place ([pkit:ADR-041]).
- **A claim on a state issue counts by its author's standing,** which each reader judges by the members' entries or, behind an open gate, by the service's answer about the author's write access ([pkit:ADR-071] point 3).
- **In human mode,** the gate passes on an approving review or an `Approved` comment from any non-author identity, and the members whose role matches, but the author, are assigned as reviewers ([project-management:DEC-027-review-modes], "Human path"). [project-management:DEC-026-work-ownership-lifecycle]'s tables count the comment from a commenter other than the author, and its Rationale ("Why the three-way OR") from the last commenter that is no bot. The commands count it from any commenter but the author, a bot among them.
- **A project registers its reviewer agents' accounts** in the remote path's list ([project-management:DEC-028-agent-as-approver-paths]). Such an account may be a user's account kept for an agent, which the service records as no bot.

**What was measured.** On a trial where an agent ran under an App installation's token ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)), the comments the App wrote, read under a person's credential, gave its login with a `[bot]` suffix and the type `Bot`. gh's JSON gave the same account on its pull requests with an `app/` prefix, marked as a bot. The service also lets an app take its owner's own name, and lets some bots be assigned, as it lets its own coding agent be.

## Decision

**In every project, nothing an account the hosting service records as a bot writes counts as a person's claim or approval, no approval counts in human mode from an account the project registers as a reviewer agent's, and every comparison of two accounts keeps their kind.**

### 1. Accounts compare in one spelling, which keeps their kind

- **One spelling.** Every comparison of two accounts the commands make puts both in one spelling, whichever surface named each, reading each account's kind from a surface that gives it. The spelling has one home, which every comparison uses. A bot's account and a user's never compare equal.
- **The member list** keeps each member's login in that spelling, its kind included. So a command that picks members as people, such as reviewers in human mode, tells an app's entry apart and passes over it.
- **A missing kind grants nothing and frees nothing.** Where no surface gives the kind a comparison turns on, no account passes on it as a member, an approver or another authority, and a claim it cannot judge is held. The ownership fold reports such a claim on an issue of work as one it cannot judge, which no consumer treats as free and the clash guard reads as one that counts. A state issue's read is left incomplete by it, as by a call that fails.

### 2. A claim on work never counts from a bot's account

The guard reads a claim's author from the service's record of that author, and holds for every bot's account, whether or not the service lets it be assigned. A claim on an issue of work counts only from the assignee's account, and never from a bot's. A label names no author, so under the label substrate the guard has nothing to read, and a label counts as [project-management:DEC-035-instance-ownership] has it.

### 3. In human mode, only a person's approval counts

- **Who approves.** An `Approved` comment or an approving review counts only from an account the service records as no bot, and that the project does not register as a reviewer agent's.
- **The order of reviews.** Of the reviews, the commands read the latest that approves, requests changes or was dismissed, and pass only where it approves. An approval that does not count is left out of that order. So a bot's request for changes holds the merge until a person approves after it, as a person's request does, and a bot's approval clears nothing.
- **Who is asked.** Human mode assigns no app's account in the member list as a reviewer (point 1).

## Rationale

**Why the guards read an author's kind.** A claim means something because only the assignee's own account can make it (DEC-043 point 3). A guard derived from the service refusing a bot as an assignee would fail once a bot can be assigned. Read from the author's kind, the guard holds for every bot, whatever the service lets it be, and alike on every machine, since an author's kind is the same wherever it is read. Counting a bot's claim for its assignee would let anyone who holds the bot's credential claim work for any person.

**Why the spelling keeps the kind.** The service lets an app take its owner's own name, so a spelling that drops the kind would compare an app's account equal to its owner's, and let it pass the closed gate, approve or claim as the owner. Each surface spells an app's account its own way (Context), so a comparison that spelled each its own way could miss a match that holds, or find one that does not. One home for the spelling keeps every comparison alike, as one home for the reading of the labels does ([pkit:ADR-026]).

**Why a missing kind grants nothing.** A comparison that cannot tell a bot from a user could pass an app as its owner. Holding a claim it cannot judge, rather than freeing it, keeps one clone off another's work for want of a field.

**Why a bot approves nothing in human mode.** Human mode asks for a person's approval. DEC-026's Rationale already counts the comment only from a commenter that is no bot, and reading the author's kind brings DEC-026's tables, DEC-027 and the commands to that rule, and applies it to reviews too. A reviewer agent's account names no person, whatever the service records of it, and the project already names those accounts (DEC-028), so leaving them out costs nothing. A request for changes stays in the order, since holding a merge back grants nothing, and a person's later approval clears it as it clears a person's request.

### Alternatives considered

- **Drop every review by a bot in human mode,** requests for changes included. The case: one rule for every bot's review. Rejected: a bot's request for changes would stop holding a merge, which loosens a guard for no gain.
- **Treat only the accounts the service records as bots as no person.** The case: one source for an account's kind. Rejected: a reviewer agent's user account would then approve in human mode.
- **A spelling that drops an account's kind,** such as the bare login. The case: the simplest to compare. Rejected: an app's account would compare equal to its owner's.
- **Count a bot's claim for its assignee,** loosening DEC-043 point 3. The case: a clone under a bot's credential could take part in instance ownership. Rejected: anyone holding the credential could claim work for any person.
- **Free a claim whose author's kind no surface gives.** The case: no claim held for want of a field. Rejected: one clone could act on another's work.

## Implications

- **What changes in every project,** each counting less or holding more:
  - in human mode, an approval from a bot's account, or from an account the project registers as a reviewer agent's, no longer counts, and such an account's approval no longer clears an earlier request for changes;
  - an app's account in the member list is no longer assigned as a reviewer;
  - a claim whose author's kind no surface gives is held, as one the ownership fold cannot judge.
- **Refined in place,** each with the pointer `(refinement per [project-management:DEC-079-bots-are-no-person])`, citing this record's points as DEC-079 point N. This record overturns nothing.
  - **DEC-026, narrowed:**
    - the `done-work` row of "The seven commands", and the `done-work` approval-gate row of the "Sub-decisions index": in human mode, an `Approved` comment or an approving review counts only from an account the service records as no bot and the project does not register as a reviewer agent's. Of the reviews, the commands read the latest that approves, requests changes or was dismissed, and pass only where it approves, and an approval that does not count is left out of that order.
    - the human-mode bullet of "Reviewer assignment", and the reviewer-assignment row of the "Sub-decisions index": human mode passes over an app's account in the member list.
  - **DEC-027, narrowed:**
    - steps 1 and 2 of "Human path: role-based reviewer assignment", the `human` row of the "Two modes" table, and the "Role-based reviewer query" row of the "Sub-decisions index": the query passes over an app's account in the member list, so none is assigned as a reviewer.
    - step 3 of "Human path", its paragraph on a query that returns no eligible reviewers, the refusal template's "from a non-author identity", the human-mode bullet of "Open mode and review-mode", and the "Open mode + human mode" row of the "Sub-decisions index": an approving review or an `Approved` comment counts only from a non-author account the service records as no bot and the project does not register as a reviewer agent's.
  - **DEC-043 point 3, its bullet "Authenticity rides `author.login`," narrowed and completed:** a marker counts only from the assignee's account, and never from a bot's. A marker from another account is ignored, as a forgery is. One whose author cannot be told from the assignee for want of a kind is a claim the ownership fold cannot judge, which no consumer treats as free.
- **Architecture records,** refined in place by the architect, whose custody they are in, with the same pointer:
  - **[pkit:ADR-041], points 1 and 2 and its Implications, point 5's third bullet, and the Summary's sentence that a claim the seam cannot judge is never treated as free, narrowed and completed:** the fold's filter keeps a marker only from the expected assignee's account, and never from a bot's, reading each author's kind from a surface that gives it, whichever read of the issue's comments it folds: the shared reader's, or a command's read of one issue. A marker from another account is ignored, as a forgery is. One whose author cannot be told from the expected assignee for want of a kind is a claim the fold cannot judge, in every project, and point 1 has the fold return each such claim with its reason. Point 5's third bullet and the Summary state, for every project, that no consumer treats such a claim as free and that the clash guard refuses as on a claim that counts, the Summary's sentence standing apart from its paragraph on a topology.
  - **[pkit:ADR-071] point 3, narrowed and completed:** an author's login is compared with the members' entries in one spelling, which keeps the account's kind. Where the gate is closed, an author whose kind no surface gives, and whose login a member's entry names, makes the read incomplete, as a call that fails does. Where the gate is open, so does an author whose kind no surface gives, since a request about an account's write access names it by a login whose form turns on its kind, and an answer about a bot's write access that the seam cannot read counts as a call that failed. The Rationale's "Why a failed call stops the read, and a definite answer does not" says why these stop the read though a retry does not change them: reading the author as one who may not write could free a held state, so the read stays incomplete until a person deletes the comment.
- **Left out, for records of their own:**
  - **Where the spelling's one home lies.** The engine's gate compares accounts too, so a record of the backbone's places it, beside the reading of the acting account.
  - **Which `Approved` comment counts in human mode:** the last that is no bot's, as DEC-026's Rationale has it, or any but the author's, as its tables have it. That is no question of an account's kind, and this record leaves it as DEC-026 states it.
