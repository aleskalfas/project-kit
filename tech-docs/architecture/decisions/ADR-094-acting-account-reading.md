---
id: ADR-094
title: The acting account is read once, in the backbone, from the hosting service's answer
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** pkit sometimes needs to know which account on the hosting service its credential acts as. The process engine needs it to check that an approval came from someone other than the actor it gates. `pkit report` needs it to tell the person which account a report will be posted as. project-management's commands need it for the membership gate and more. Each asks on its own today, and they fail in different ways. Under a GitHub App's token the usual question is refused, and the engine then takes a made-up actor that matches nobody, so every check that an actor did not approve their own work passes.

This record makes one reading in the backbone, which every reader uses:

- **Only the service names the account.** The reading names an account, and whether it is a user's or a bot's, only from the hosting service's own answer. Every other outcome is an unresolved identity, reported with its cause, and the reading falls back to nothing.
- **One spelling.** An account is written and compared as the service's own login, in which a bot's account carries the service's bot suffix. Users' logins are already written so, so the member lists projects hold need no migration.
- **An answer lasts one run.** Nothing kept from an earlier command counts as the service's answer.
- **No stand-ins.** The engine refuses a gate that must confirm another authority when it cannot name the actor, rather than pass it under a placeholder. `pkit report` posts only as an account it can name, and otherwise keeps the draft.
- **GitHub only, provisionally,** held in the backbone as the landing of pull requests is.
- **Each reader decides what it does without an answer:** the backbone's two readers in this record, a capability's commands in that capability's records.

## Context

**The terms.**

- **The acting account** is the account on the hosting service that a credential acts as: the one the service records as the author of each write made with it.
- **A reader** is code that needs the acting account.
- **The service's answer** is the hosting service's reply, to a request made with the credential, that names the account the credential acts as and the account's kind.
- **An account's kind** is what the service records it as: a user's account, or a bot's account, as the service records the account an app acts through. A user account kept for an agent, a machine user, is a user's account.
- **An unresolved identity** is every outcome of asking other than the service's answer, reported with its cause ([project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162)).
- **A run** is one invocation of one command, from its start to its exit, as the state-issue seam defines it ([ADR-071](ADR-071-state-issue-seam.md) point 8).

**What happens today.** Five readers ask the service on their own, and fail three ways:

- **The engine's default actor.** Where its caller names no actor, the engine's move asks the service for the login and takes the fixed value `operator` where the ask fails. Its status view and its check whether a move may be made take `operator` without asking. The engine's page warns a caller to name one actor on each call, or a sign-off gate can give two verdicts.
- **The cross-authority gate** passes where the authorisation's producer is not the actor, compared as two strings. `operator` equals no login, so a gate judged under it passes whoever merged, the actor included.
- **project-management's move** hands the engine its membership identity as the actor, and hands none where that identity is unresolved, so the placeholder decides.
- **`pkit report`** names the login in the confirmation it asks before it posts. Where the ask fails, it names "your gh CLI identity (login unresolved)", and posts once the person confirms.
- **project-management asks in three places of its own:** the membership gate, which reports an unresolved identity with its cause; the review command's check for a pull request of one's own; and workstream sync's check for comments of its own.

**What was measured.** On a trial of an agent working under a GitHub App installation's token ([project-kit#3004](https://github.com/aleskalfas/project-kit/issues/3004)), the request for the signed-in user was refused with "Resource not accessible by integration (HTTP 403)". Read afterwards under the maintainer's own credential ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)), the App's account has two spellings:

- **the service's REST interface** gives its login as `<name>[bot]`, of type `Bot`;
- **gh's JSON** gives the same account as `app/<name>`, marked as a bot.

Whether an installation's token can learn its own account and kind by any request is not measured: both attempts failed before they reached the agent.

**What the service documents.** An app's name may be its owner's own user or organization name. A user's login holds letters, digits and dashes, and for an enterprise's managed user an underscore and the enterprise's short code, so never a bracket.

**What the records already say.**

- **A gate's authorisation must come from another authority than the actor it gates** ([COR-033](../../../.pkit/decisions/core/COR-033-process-substrate.md) P4).
- **The backbone may not depend on a capability** ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md), "The dependency direction cannot invert"). This is the rule the engine's default-actor code cites when it says the binary must not depend on a capability tree.
- **A capability's scripts reach the backbone by command, and each computation keeps one home** ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) points 1 and 2).
- **The backbone's landing of pull requests** is GitHub-only, labelled, and placed provisionally, with the core question raised in [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222). It reads its host from the caller's environment, and its documents are a versioned contract ([ADR-061](ADR-061-hosting-service-acts-in-the-backbone.md) points 3, 4 and 7).
- **`pkit report`'s confirmation names the account it posts as,** so that a split between the command line's account and the browser's never misattributes a post ([project-kit#662](https://github.com/aleskalfas/project-kit/issues/662)). With nobody at the terminal, it keeps the draft and posts nothing ([ADR-047](ADR-047-report-cross-repo-write.md) point 2).
- **The membership gate** reads the service's login first, git's configured email second and an environment variable third, and leaves how a failed read is handled to its implementation ([project-management:DEC-021](../../../.pkit/capabilities/project-management/decisions/DEC-021-team-membership-gate.md), "Identity resolution"). The member list's schema describes a member's login as the value the service answers for that member.

## Decision

**Which account a credential acts as is read once, in the backbone, and only the hosting service's answer names the account and its kind. Every reader uses that reading, compares accounts in one spelling, and decides in its own record what it does with an unresolved identity. The engine's gate never takes a placeholder for an actor it cannot name, and `pkit report` never posts as an account it cannot name. The placement is GitHub's, and provisional.**

### 1. One reading of the acting account, in the backbone

- **One home.** One module of the backbone, the acting-account reading, asks the service which account the credential acts as. Nothing else in pkit asks.
- **Every reader takes it from there:** the engine's default actor (point 5), the account `pkit report` posts as (point 6), and each command of a capability that needs the account its credential acts as (point 8). No reader asks the service a way of its own, a tool's own shorthand for the signed-in account among them.
- **How a reader reaches it.** The backbone's code imports it. A capability's scripts reach it through a reading command of the backbone, whose output is a document with a schema version, under the contract ADR-061 point 7 sets for the hosting service's documents.
- **Apart from the local readings.** The reading reaches the network, so it stays apart from the reading of the repository, which needs none (ADR-061 point 2). For the same reason no query calls it: no resolver, filler or validator (ADR-057 point 3). It changes nothing, so it runs no cross-repository guard.
- **The host** comes from the caller's environment, never from a configuration of the backbone's (ADR-061 point 4). A capability that keeps its own host passes it on through the environment.
- **Bounded.** An ask is bounded in time, and one that runs out is no answer.

### 2. Only the service's answer names the account and its kind

- **Resolved** only where the service, asked with the credential, answers with the account the credential acts as and that account's kind. The reading gives the account in the one spelling (point 3), with its kind.
- **Unresolved** in every other outcome, each reported with its cause:
  - a refusal, whatever its cause;
  - no answer, such as with the tool missing, no network, a timeout, or something other than the service answering;
  - an answer that names no account, or an account of a kind the reading does not know.
- **Never from anything else:**
  - the wording of a refusal, which a rate limit or a suspended account can give as well as an app;
  - the credential's own form;
  - the record the issuing tool keeps of who signed in;
  - git's configured identity, or a variable or setting that names an account;
  - the name of the host or tool that issued the credential, which pkit never tests ([ADR-091](ADR-091-no-host-component.md) point 2).
- **No fallback.** The reading gives no account the service did not answer with. What a reader does under an unresolved identity is decided in the reader's own record: points 5 and 6 for the backbone's readers, and a capability's records for its commands (point 8).
- **What it does not need.** Whether an installation's token receives an answer is unmeasured. The reading holds either way: where it does not, every such credential reads as unresolved, and each reader acts as its record says for that.

### 3. One spelling of an account, its kind included

- **The spelling** is the login as the service's REST interface gives it. A user's account is spelled by its login. A bot's account is spelled by its login with the service's bot suffix, as `name[bot]`.
- **It carries the kind.** No user's login can hold the suffix's brackets. So a bot's account never reads as a user's, even where an app took its owner's own name.
- **One function** beside the reading puts an account named by any surface into the one spelling, such as gh's JSON, which writes a bot's account with an `app/` prefix. Where a surface gives an account's kind apart from its login, a reader asks for the kind with the login, since the bare login of an app's account may be its owner's.
- **Where it binds.** Every comparison of two accounts compares them in this spelling, and every account pkit writes down is written in it. The backbone's code calls the function. A capability's scripts reach it through the backbone's reading command, and keep no copy of it (ADR-057 point 2).
- **No migration.** A user's login is already in this spelling, and the member list's schema describes a member's login as the value the service answers for that member. So the member lists projects hold need no migration. Whether an app's account may be a member is the capability's to decide. Where it may, its entry is written in this spelling.

### 4. An answer lasts one run

- **Within a run,** the reading asks at most once and reuses its answer. A capability's command that reaches it by command keeps the answer for its own run. Where it starts a backbone command that takes the account, such as the engine's move, it hands the account on.
- **Across runs, nothing is kept.** An answer kept from an earlier run, even for the same credential, is no answer of the service's. So each run asks.

### 5. The engine's actor is the reading's account, and never a placeholder

- **The default actor.** Where its caller names no actor, the engine takes the reading's account. Every engine command that judges a gate does so: the status view, the check whether a move may be made, and the move. So the check and the move judge one actor.
- **An actor a caller names** is the caller's word, which the engine cannot check. The actor a gate judges is the account the move is made as (COR-033 P4), so a caller names that account, as the reading gives it.
- **One spelling at the gate.** The engine puts the actor and the authorisation's producer through the one function (point 3) before it compares them.
- **Under an unresolved identity, the engine knows no actor:**
  - a gate that must confirm its authorisation came from another authority refuses, since nothing can confirm it. It says that pkit cannot tell which account is acting, why, and how a caller names an actor;
  - a move none of whose gates compares the actor goes on, and its journal entry records the actor as unresolved, in a form no account's spelling takes.
- **No placeholder.** No fixed value stands for an actor the engine cannot name.

### 6. `pkit report` posts only as an account it can name

- **The confirmation** names the reading's account, and says when it is a bot's.
- **Under an unresolved identity,** the command posts nothing through the service. It says it cannot tell which account it would post as, and why, and keeps the payload as a draft, as it does with nobody at the terminal (ADR-047 point 2). The draft is posted later, by a person, once the reading names the account, or through the prefilled form, whose account the browser decides, as ADR-047 already warns.
- **The listing of one's own reports** filters by the reading's account. Under an unresolved identity, it says it cannot tell whose reports to list.

### 7. GitHub only, through `gh`, and provisional

- **Written for GitHub.** The request the reading makes, the kinds it knows and the spelling are GitHub's. Its reference says so, and its document uses GitHub's vocabulary.
- **Provisional, on ADR-061 point 3's ground.** The backbone's engine and its report command need the reading, and the backbone cannot depend on a capability (COR-010). Whether core content may read or act on one hosting service under a label is raised in [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222), and this placement joins that question.
- **On another service,** `gh` cannot answer, so the identity is unresolved. Each reader then acts as its record says for no answer, and none takes a wrong account. The engine there judges a cross-authority gate only for an actor its caller names (point 5).
- **When to revisit:**
  - when [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222) is decided;
  - when a second hosting service is supported. The reading's document then becomes a contract in a vocabulary of its own, and the spelling names the service, since two services' logins may coincide.

### 8. The backbone reads; each reader decides

- **The backbone** holds the reading and the spelling, and decides here what its own readers do (points 5 and 6). It reads no capability's files or settings for the account, and calls no capability to learn it (COR-010).
- **A capability's commands** take the acting account and its spelling from the backbone, by command (ADR-057 point 1). Each capability decides in its own records:
  - what its commands do with an unresolved identity, or with a bot's account;
  - which other values, such as an email or a variable that names a person, may stand beside the reading's account.

  The reading gives none of them.
- **project-management's commands** are one reader. The membership gate takes its first surface, the service's login, from the reading, in the one spelling. Its other surfaces stay as DEC-021 decides them.

## Rationale

**Why one reading.** Five readers ask on their own today, and fail three ways: with no account, with the placeholder, or with the actor left to the engine. That is the recurrence that calls for one home ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)). The copies already disagree where it costs most. Where project-management cannot name its account, it hands the engine no actor. The engine's own ask fails the same way, and it takes the placeholder, so the agent's own merge reads as another authority's.

**Why in the backbone.** The engine and `pkit report` are the backbone's, and need the reading whatever a project installs. The backbone cannot depend on a capability (COR-010), and asking one by command, optionally, as `pkit report` asks project-management for a workstream ([ADR-050](ADR-050-report-context-sourcing.md) point 2), fails wherever the capability is absent. A capability reaches the backbone by command (ADR-057 point 1). So the backbone is the one home every reader can reach, as ADR-061 found for landing a pull request.

**Why only the service's answer.** Any other source is a second reading that can disagree with the service:

- **A refusal** has many causes, an app's credential among them.
- **A credential's form** is the issuer's convention. It can disagree with the service's answer in a case nobody has measured, a person's sign-in through an app, and reading it means reading the secret.
- **The issuing tool's record** of who signed in is overridden by a token passed in the environment.
- **Git's configured identity** names whoever set the machine up.

Without the service's answer, pkit cannot tell an app's credential from a person's. Any fallback would make a person the acting account, under an app's credential, whenever its ask fails.

**Why the reading offers no fallback, and leaves the response to each reader.** What a reader may do without an answer turns on what it guards. The engine guards a cross-authority check, `pkit report` guards a public post, and the membership gate keeps its own sources by its own record. One fallback in the reading would decide all three at once, and would carry a capability's choice into the backbone.

**Why the service's REST spelling.** It is the service's own login, and carries the kind in its form, so no field is added, and the member lists hold it already. gh's form is a tool's spelling, which the service's other surfaces do not use. A bare login would drop the kind, and an app may take its owner's name, so the app's account would compare equal to its owner's.

**Why the engine respells both sides.** The engine's comparison is the check COR-033's Rationale calls load-bearing. A predicate that reports the producer in another surface's spelling would make an actor's own merge read as another authority's. The function and the engine share the backbone, so this costs no boundary. A value in no service's spelling passes through it unchanged, so the engine stays content-free for any other process.

**Why an answer lasts one run.** An answer kept across runs needs a key for the credential, which means reading the secret or trusting the issuing tool's record (point 2). It can also go stale: a login renamed, or a setup that swaps one credential for another, would act on the earlier account. What it would save is one request a run, and resolution offline, where the readers can rarely do their work anyway: the engine's sign-off gates read the service, and a report posts to it.

**Why no placeholder actor.** A placeholder equals no account, so every cross-authority gate passes under it. Refusing such a gate costs a caller one named actor, or a second run once the service answers. A move none of whose gates compares the actor loses nothing by an unknown actor, so it goes on, and the journal says so plainly.

**Why `pkit report` keeps the draft.** The confirmation names the posting account so that a person never posts a public issue as an account they did not expect ([project-kit#662](https://github.com/aleskalfas/project-kit/issues/662)). With the identity unresolved, it cannot name one, so the post waits for a way that can, as it does with nobody at the terminal.

**Why GitHub only, provisionally.** One service is all pkit supports. A neutral vocabulary would be GitHub's renamed, and COR-007 extracts a common form only once a second instance shows what is common. The conflict between a GitHub-only backbone and the core records is the one ADR-061 point 3 raised, and the same core decision settles both.

### Alternatives considered

- **Each reader keeps its own ask.** Rejected: the copies already disagree, and at the engine's gate the disagreement turns an actor's own merge into another authority's.
- **The reading in project-management, which the backbone asks by command.** Rejected: the engine and `pkit report` would lose the reading wherever the capability is not installed (COR-010).
- **An interim reading in project-management, moved to the backbone later.** Rejected: until the move, two readings of one credential run side by side, and they already disagree at the engine's gate.
- **The kind read from the credential's form,** such as the prefix the service gives each kind of token. Rejected: it is a second reading that can disagree with the service, the secret must be read to see it, and an unknown form leaves the identity unresolved anyway.
- **An app's credential read from the service's refusal.** Rejected: a refusal has other causes, and names no account to act as.
- **A fallback in the reading,** to git's identity, a variable or the tool's record. Rejected: without the service's answer, a fallback makes a person the acting account under an app's credential, and it decides for every reader what only each reader's record should.
- **An answer kept across runs, keyed by a digest of the credential.** Not taken: it needs the secret read, it can go stale, and it saves one request a run. It is weighed again if the service's limits on requests are seen to bite.
- **A spelling with the kind as a field of its own.** Rejected: every member list and every stored account would need a migration, and the service's login already carries the kind.
- **gh's spelling, with its `app/` prefix.** Rejected: it is a tool's spelling, which the service's other surfaces do not use, and the member list's schema already describes the service's.
- **The bare login.** Rejected: an app may take its owner's name, so its account would compare equal to its owner's and pass as the owner.
- **The engine compares as given, and each producer of an account keeps the spelling.** Rejected: one producer's slip makes an actor's own merge pass as another authority's, and the engine can prevent that at no cost of boundary.
- **The engine takes no default actor, and a caller always names one.** Rejected: every actor would then be the caller's own word, which can name an authority other than the one acting. The service's answer is a word the actor did not give.
- **The engine refuses every move under an unresolved identity.** Rejected: a move whose gates compare no actor would stop for nothing.
- **`pkit report` posts under an unresolved identity once the person confirms,** as it does today. Rejected: the confirmation exists to name the posting account, and here it cannot (point 6).
- **A reading neutral to the hosting service now.** Rejected: with one service, the neutral form is GitHub's renamed (COR-007; ADR-061 point 3).

## Implications

- **Edits, once a person accepts this record,** made in this change. Each is a refinement in place, and none overturns a passage. Each takes a forward pointer to this record: `(refinement per [pkit:ADR-094])` in a capability's record, and the same pointer as a relative link in an architecture record.
  - **[ADR-047](ADR-047-report-cross-repo-write.md) point 2,** which the architect refines. The posting account the confirmation names is the reading's, said to be a bot's where it is one. Under an unresolved identity, `pkit report` posts nothing through the service, says why, and keeps the payload as a draft. This completes the point: it has the confirmation name the posting account, and states no outcome where pkit cannot name it.
  - **[project-management:DEC-021](../../../.pkit/capabilities/project-management/decisions/DEC-021-team-membership-gate.md), "Identity resolution", item 1 and the paragraph on matching,** which whoever makes this change refines. The service's login is the account the hosting service answers the credential acts as, read through the backbone's reading of the acting account, in place of the request the item names. A login is matched against a member's in the one spelling. Items 2 and 3, and what a failed read leads to, stand as DEC-021 has them. This completes the section: DEC-021 left how the login is read and matched to its implementation ("Why mechanism details are deferred"), and this record settles both.
- **Records not edited.**
  - **[ADR-041](ADR-041-instance-ownership-substrate-contract.md) and ADR-071 point 3** compare a comment's author with an assignee or a member. Point 3 here governs those comparisons, and neither record states a spelling of its own.
  - **[ADR-020](ADR-020-process-engine-code-home.md) and ADR-061** stand. This record places one more read of the hosting service beside the acts ADR-061 placed.
  - **COR-033** is realised, not changed. PRJ-008 stands.
- **The work,** once this record is accepted:
  - the reading and the one function, with the reading command and its document, and tests that fake `gh`;
  - the engine's status view, move check and move take the reading's account as their default actor, compare in the one spelling, refuse a cross-authority gate under an unresolved identity, and journal the actor as unresolved;
  - `pkit report`'s confirmation, its draft under an unresolved identity, and its listing by the reading's account;
  - project-management's readers move onto the reading command, and its move hands the engine the reading's account. The member list's schema describes a login in the one spelling;
  - the engine's page, which describes the default actor, and the CLI reference, where it describes the gate's actor and the account `pkit report` posts as.

  None of it changes the form of anything a project holds, so it ships no migration. The engine's default actor and `pkit report`'s refusal under an unresolved identity are surface changes, so the changes that build them declare changesets, of a segment a person judges.
- **The measurement is not due before the build.** Nothing here rests on whether an installation's token can learn its own account. Only how often an app's credential resolves does.
- **Left out, for records of their own:**
  - what a capability's commands do with an unresolved identity or a bot's account, which project-management decides in its own record ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164));
  - git's email and the variable beside a person's login, at the membership gate ([project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175));
  - the person an agent works for, which names no account the credential acts as, so it is no reading of the acting account. The record on who may authorise in a turn a chat started (ADR-091, Implications) may give the backbone a reading of it;
  - whether the predicate of project-management's gate on the move to Done reports the approval rather than the merge ([project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171));
  - how far the reading holds for another hosting service (point 7, [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222)).
- **Stands on** COR-007, COR-010, COR-033, PRJ-008, ADR-020, ADR-041, ADR-047, ADR-050, ADR-057, ADR-061, ADR-071, ADR-091 and project-management DEC-021, all accepted.
