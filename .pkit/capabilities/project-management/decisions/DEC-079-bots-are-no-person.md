---
id: DEC-079
title: A bot's account stands for no person, and in human mode neither does a reviewer agent's
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** in every project, under every credential, a bot's account stands for no person: an app's account, and any other the backbone's one spelling of accounts reads as a bot's ([pkit:ADR-094]). No command makes it an assignee or hands it a Task, since an assignee names a person, and a command makes a bare login an assignee only where the hosting service answers that it names a user's account. No claim on work a bot writes counts wherever the claim names who wrote it. In human mode, no approval counts from a bot's account or from an account the project registers as a reviewer agent's, and human mode asks neither for a review. A bot's request for changes still holds a merge until a person approves after it. Where that spelling cannot tell an account's kind, as for a bot whose login the service gives with no `[bot]` suffix, its claim is held where its login is the assignee's and void otherwise, and its approval counts for nothing.

## Context

**The terms.**

- **The backbone's spelling of accounts** is its one function that puts an account any surface names into one spelling that carries the account's kind, and compares accounts ([pkit:ADR-094] point 3).
- **A bot's account** is one that spelling reads as of the bot kind. An app's account is one.
- **An account of a kind unknown** is one that spelling reads as neither a user's nor a bot's, such as an account the service records as a bot's but gives with no `[bot]` suffix.
- **A reviewer agent's account** is one the project registers in the remote path's list ([project-management:DEC-028-agent-as-approver-paths]). It may be a user's account kept for an agent, which the service records as no bot.

**What the records say.**

- **Assignment names a person.** Every issue has an assignee, someone responsible, in closed mode a member and in open mode any account ([project-management:DEC-019-mandatory-issue-state], "Mandatory assignment"). Its checks at filing are `hard-reject` findings of [project-management:DEC-014-validation-severity-model]'s, which the `--force` of [project-management:DEC-046-override-flag-convention] overrides.
- **A claim on an issue of work counts only from the assignee's account** ([project-management:DEC-043-ownership-substrate-selection] point 3), a filter the ownership fold applies in one place ([pkit:ADR-041] point 2). A claim on a state issue counts by its author's standing ([pkit:ADR-071] point 3), which this record leaves as it stands.
- **In human mode,** the gate passes on an approving review or an `Approved` comment from any non-author identity, and the members whose role matches, but the author, are assigned as reviewers ([project-management:DEC-027-review-modes], "Human path"). [project-management:DEC-026-work-ownership-lifecycle]'s tables count the comment from a commenter other than the author, and its Rationale ("Why the three-way OR") from the last commenter that is no bot.

**What happens today.**

- **Approvals in human mode.** The commands count an `Approved` comment from any commenter but the author, a bot among them. Of the reviews, they read DEC-026's "latest APPROVED review" as the latest review that approves, requests changes or was dismissed, and pass where it approves.
- **Assignees.** A command takes an assignee named in the call as it is given, and the service decides whether that account can be assigned.

**What was measured.** On a trial where an agent ran under an App installation's token ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)), the comments the App wrote, read under a person's credential, gave its login with a `[bot]` suffix and the type `Bot`. gh's JSON gave the same account on its pull requests with an `app/` prefix, marked as a bot. The service also lets an app take its owner's own name, and lets some bots be assigned, as it lets its own coding agent be. Whether the field the service declares to hold an issue's assignees, as users' accounts, gives such a bot is not measured ([project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171)).

## Decision

**In every project, a bot's account stands for no person: no command makes it an assignee, no claim on work that names its author counts from it, and in human mode no approval counts from it or from a reviewer agent's account.**

Which account is a bot's, and whether two accounts are one, the commands read as the backbone's spelling of accounts has it (ADR-094 point 3), in each rule below.

### 1. An assignee is never a bot's account

- **No bot as an assignee.** No command makes a bot's account an assignee, at filing, on an assignment or by handing a Task to it, whether or not a member's entry names it, since assignment names a person (DEC-019). `handoff-issue` hands a Task from one person to another.
- **The form of an assignee.** An assignee a command is given, in the call, by `--me` or by default, is a value that stands for an account, read by its form (ADR-094 point 3). A bare login names a user's account, `<name>[bot]` and `app/<name>` a bot's, and a string with no spelling names none.
- **A bare login, on the service's word.** A command makes a bare login an assignee only where the service answers that it names a user's account. Where the login is the acting account the backbone's reading named as a user's, that reading is the answer. Otherwise the command looks the login up with the service, as `add-member` does (ADR-094 point 3). It refuses where the lookup answers an account of another kind, such as a bot's whose login carries no `[bot]` suffix or an organization's, or answers none. It refuses a bot's spelling, and a string with no spelling, without asking. Each command asks once for each assignee it names, and each already reaches the service.
- **No override.** These refusals are preconditions of their commands, never a `hard-reject` finding of DEC-014's, so the `--force` DEC-046 gives such a finding does not reach them.

### 2. A claim on work never counts from a bot's account

- **Never from a bot's.** A claim on an issue of work counts only from the assignee's account, and never from a bot's account, even one the service lets be assigned. The guard reads the author's kind, never whether the service lets that author be assigned.
- **A kind unknown.** A claim whose author is of a kind unknown is held, as a claim the ownership fold cannot judge, where its login is the assignee's once the `[bot]` suffix and gh's `app/` prefix are set aside. It is void where the assignee is a user of another login (ADR-094 point 3). So a claim from an account the service records as a bot's but gives with no suffix is void on a person's Task, and held, neither counted nor freed, on a Task whose assignee bears its login.
- **Labels.** A label names no author, so under the label substrate the guard has nothing to read, and a label counts as [project-management:DEC-035-instance-ownership] has it.

### 3. In human mode, only a person's approval counts

- **Who approves.** An `Approved` comment or an approving review counts only from an account the spelling reads as a user's, that is another account than the pull request's author, and that the project does not register as a reviewer agent's. So an approval from a bot's account counts for nothing, nor does one from an account of a kind unknown, or from one the comparison cannot tell from the author.
- **The order of reviews.** The latest review that approves, requests changes or was dismissed decides, as the commands read DEC-026's "latest APPROVED review", and it passes only where it approves. An approval that does not count is left out of that order. So a bot's request for changes holds the merge until a person approves after it, as a person's request does, and a bot's approval clears nothing.
- **Who is asked.** Human mode assigns as a reviewer no member whose entry names a bot's account or a reviewer agent's account. It leaves out the author, and any member the comparison cannot tell from the author.
- **An entry with no spelling.** An entry of the remote path's list with no spelling, such as `@bot`, leaves the comparison unable to tell any account from it (ADR-094 point 3). So until a person mends it, no approval counts in human mode and no member is asked for a review. The refusal names the entry, and why it names no account.

## Rationale

**Why an assignee is never a bot's account.** An assignee says who is responsible for the work (DEC-019). A bot answers for nothing it does: the person who set it to work does. Assigned to a bot, a Task names nobody responsible, and the bot's claims on it count for nothing (point 2).

**Why the service confirms a bare login.** A bare login names a user's account by its form, but the service lets some bots be assigned by a login with no suffix, as its own coding agent. Read by its form alone, such a bot would be made an assignee through the commands. The lookup reads the kind the service records, at one request for each assignee named, in a command that already reaches the service.

**Why the guards read an author's kind.** A claim means something because only the assignee's own account can make it (DEC-043 point 3). A guard derived from the service refusing a bot as an assignee would fail once a bot can be assigned. Read from the author's kind, the guard holds for every bot, whatever the service lets it be, and alike on every machine, since an author's kind is the same wherever it is read.

**Why an account of a kind unknown is held, not counted as a bot's.** The backbone's spelling leaves a bot whose login carries no suffix of a kind unknown, since nothing measured says every surface gives it one login (ADR-094 point 3). This record follows that spelling, so such an account's claim is held where its login is the assignee's, as the fold holds every claim it cannot judge. That hold no reader can judge, and the clash guard reads it as a claim that counts (DEC-035 point 6), until a person assigns the Task to another or removes the comment. A claim such an account writes on a person's Task is void, as any other account's is, since the person's login tells the two apart (ADR-094 point 3). Counted as a bot's instead, the claim would free a Task whose claim no reader can tell from its assignee's, on a reading no measurement backs.

**Why a bot approves nothing in human mode.** Human mode asks for a person's approval. DEC-026's Rationale already counts the comment only from a commenter that is no bot, and reading the approver's kind brings DEC-026's tables, DEC-027 and the commands to that rule, and applies it to reviews too. A request for changes stays in the order, since holding a merge back grants nothing, and a person's later approval clears it as it clears a person's request.

**Why a reviewer agent's account approves nothing, and is not asked.** A reviewer agent's account names no person, whatever the service records of it, and the project already names those accounts (DEC-028). Asked for a review, it would be asked for an approval that cannot count. This assumes a project registers no person's own account as a reviewer agent's. A maintainer whose own account runs the remote reviewer, such as through their own token, loses their approvals in human mode, so such a project registers an account of the agent's own. An account kept for an agent that the project does not register is a user's account, so its approval counts in human mode: registering it is what tells it from a person's.

**Why an entry with no spelling stops every approval.** Such an entry is most likely a login mistyped, and the comparison cannot tell any account from it (ADR-094 point 3). Read as naming no account, it would let the reviewer agent it was meant to name approve as a person. Read as *cannot tell*, it grants nothing, and the refusal names it, so a person mends it. What that costs is every human-mode approval until then.

**What it costs a project that assigns work to a bot,** such as the service's own coding agent. The commands refuse to assign it (point 1), so the project assigns it on the service's own surface. What the commands then read of the Task turns on whether the field of an issue's assignees gives that bot, which is not measured (Context):

- **Where it does not,** the commands read the Task as unassigned, `start-work` assigns whoever starts it, and the bot's claim on it is void, since that person's login tells the two apart.
- **Where it does,** that field gives a bot's account a user's kind, so the backbone reads no user's kind from it until a record decides how it is read (ADR-094 point 1, "Other kinds"), and this record's costs are weighed again in that record.

### Alternatives considered

- **Assign a bot's account where the service lets it be assigned.** The case: a project hands work to the service's coding agent through the commands. Rejected: the assignee would name nobody responsible, and the bot's claims would count for nothing.
- **Read a bare assignee by its form alone,** with no lookup. The case: no request beyond those the command makes. Rejected: a bot whose login carries no suffix, such as the service's coding agent, would be made an assignee through the commands, in open mode, and in closed mode wherever a member's bare entry names it.
- **Drop every review by a bot in human mode,** requests for changes included. The case: one rule for every bot's review. Rejected: a bot's request for changes would stop holding a merge, which loosens a guard for no gain.
- **Treat only the accounts the service records as bots as no person.** The case: one source for an account's kind. Rejected: a reviewer agent's user account would then approve in human mode.
- **Count a bot's claim for its assignee,** loosening DEC-043 point 3. The case: a clone under a bot's credential could take part in instance ownership. Rejected: anyone holding the credential could claim work for any person.
- **Read an account the service records as a bot's but gives with no suffix as a bot's.** The case: its claim does not count, so it holds nothing. Not taken: the backbone's spelling leaves its kind unknown, its spelling across surfaces unmeasured, and the hold costs only where such an account writes a claim on a Task whose assignee bears its login.

## Implications

- **What changes in every project,** each counting less or holding more:
  - no command makes a bot's account an assignee or hands a Task to one, and a bare login becomes an assignee only where the service answers that it names a user's account;
  - in human mode, an approval from a bot's account, from an account of a kind unknown, from one the comparison cannot tell from the author, or from an account the project registers as a reviewer agent's does not count, and does not clear an earlier request for changes;
  - human mode assigns no member whose entry names a bot's account or a reviewer agent's as a reviewer;
  - an entry with no spelling in the remote path's list stops every approval in human mode, and every request for a review, until it is mended;
  - a claim on work from a bot's account does not count, and one from an account of a kind unknown is held where its login is the assignee's, and void otherwise.

  The order of reviews is the one the commands read, so a person's review changes nothing.
- **In agent mode** this record changes nothing. ADR-094's edit of DEC-028 tells an App that took its owner's name apart from its owner, so its verdict on the owner's pull request counts there, as DEC-028 already counts a registered App's verdict on its owner's pull request wherever their names differ.
- **Refined in place,** each with the pointer `(refinement per [project-management:DEC-079-bots-are-no-person])`, citing this record's points as DEC-079 point N. Each edit that tells an account apart from another states the comparison in its own words and cites [pkit:ADR-094] point 3 for it. This record overturns nothing.
  - **DEC-019, narrowed:** "Methodologically NOT a classification axis", its "Assignment names a person", and the schema's `values_constrained_to: members`, open in open mode: the assignee is never a bot's account, whether or not a member's entry names it, and a bare login is made an assignee only where the service answers that it names a user's account (DEC-079 point 1).
  - **DEC-026:**
    - completed and narrowed: the `done-work` row of "The seven commands", and the `done-work` approval-gate row of the "Sub-decisions index". In human mode, an `Approved` comment or an approving review counts only from an account read as a user's, that the project does not register as a reviewer agent's, and that is another account than the pull request's author. Each account is read with its kind from a surface that gives it, and the two are compared as ADR-094 point 3 compares accounts, the case of ASCII letters and surrounding whitespace set aside, so an approver the comparison cannot tell from the author counts for nothing. Of the reviews, the latest that approves, requests changes or was dismissed decides, and passes only where it approves, and an approval that does not count is left out of that order. Completed: the rows tell the approver from the author, and fix no spelling or kind for either. Narrowed: no approval counts from a bot's account, a reviewer agent's, an account of a kind unknown, or one that differs from the author only in case or surrounding whitespace.
    - narrowed and widened: the human-mode bullet of "Reviewer assignment", and the reviewer-assignment row of the "Sub-decisions index": human mode passes over a member whose entry names a bot's account or a reviewer agent's, and leaves out the author and any member the comparison cannot tell from the author. An App that took its owner's name is another account than its owner, as the service records them, so on the App's pull request the owner is assigned.
    - narrowed: the `handoff-issue` row of "The seven commands": a Task is never handed to a bot's account.
  - **DEC-027, completed, narrowed and widened:** the `human` row of the "Two modes" table, steps 1 to 3 of "Human path: role-based reviewer assignment", its paragraph on a query that returns no eligible reviewers, the refusal template's "from a non-author identity", the human-mode bullet of "Open mode and review-mode", and the "Role-based reviewer query" and "Open mode + human mode" rows of the "Sub-decisions index". An approving review or an `Approved` comment counts only from an account read as a user's, that the project does not register as a reviewer agent's, and that is another account than the author, each read with its kind and compared as ADR-094 point 3 compares accounts. The query passes over a member whose entry names a bot's account or a reviewer agent's, and leaves out the author and any member the comparison cannot tell from the author. The sorts are those of DEC-026's rows above.
  - **DEC-043 point 3, its bullet "Authenticity rides `author.login`," completed, narrowed and widened:** a marker is trusted only where its author and the assignee are one account: the same login and the same kind, each read from a surface that gives the kind, the case of ASCII letters and surrounding whitespace set aside, as ADR-094 point 3 compares them. It is never trusted from a bot's account, even where the bot is the assignee. A marker from another account is ignored, as a forgery is. One whose author the comparison cannot tell from the assignee, for want of a kind, is a claim the ownership fold cannot judge, which no consumer treats as free. Completed: the bullet trusts a marker by its author's login, and states no outcome for an author a missing kind leaves in doubt. Narrowed: requiring both kinds known trusts fewer markers and frees none, and a bot's marker counts for no assignee. Widened: setting case and surrounding whitespace aside widens the match, only to other spellings of one account.
  - **[pkit:ADR-041] point 2, its bullet "Authenticity rides `author.login`," completed, narrowed and widened,** by the architect, whose custody it is in, with the same pointer: the fold's filter, as DEC-043 point 3's edit above states it, the fold reading each marker's author and the issue's assignees with their kinds. The record's other mentions of that filter name it, and read true with the bullet so edited.
- **Accepted with or after [pkit:ADR-094],** which it cites for an account's kind and the comparison of accounts. Refusing ADR-094 leaves this record no way to tell whether an account is a bot's, so it is then revised to state one.
- **Left out, for a record of its own: which of the approvals that count decides in human mode** ([project-kit#3182](https://github.com/aleskalfas/project-kit/issues/3182)): only the last `Approved` comment among those that count, as DEC-026's Rationale has the last non-bot commenter's, or any of them, as its tables have it. This record leaves that as DEC-026 states it.
