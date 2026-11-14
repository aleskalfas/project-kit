---
id: ADR-094
title: The acting account is read once, in the backbone, from the hosting service's answer
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** pkit sometimes needs to know which account on the hosting service its credential acts as. `pkit report` needs it to tell the person which account a report will be posted as. project-management's commands need it for the membership gate, to name who makes a move, and more. Each asks on its own today, and they fail in different ways. Under a GitHub App's token the usual question is refused. The process engine asks too, and then takes a made-up actor that matches nobody, so its check that an approval came from someone other than the actor passes whoever approved.

This record makes one reading in the backbone, which every reader uses, and takes the engine out of the asking:

- **Only the service names the account.** The reading names an account, and whether it is a user's or a bot's, only from the hosting service's own answer. Every other outcome is an unresolved identity, reported with its cause, and the reading falls back to nothing.
- **One spelling.** Accounts are compared and written down in one spelling that carries the kind: a user's account by its login, a bot's with the service's `[bot]` suffix. Users' logins are already written that way, so no entry that names a person changes.
- **An answer lasts one run.** Nothing kept from an earlier command counts as the service's answer.
- **The engine asks nobody.** It takes the actor its caller names, and none by default. A gate that must confirm another authority refuses where no actor is named, rather than pass under a placeholder. A caller whose actors are accounts on the hosting service names the account its credential acts as, from the reading.
- **`pkit report` posts only as an account it can name,** and otherwise keeps the draft.
- **GitHub only, provisionally,** held in the backbone as the landing of pull requests is.
- **Each reader decides what it does without an answer:** `pkit report` in this record, a capability's commands in that capability's records.

## Context

**The terms.**

- **The acting account** is the account on the hosting service that a credential acts as: the one the service records as the author of each write made with it.
- **A reader** is code that needs the acting account.
- **The service's answer** is the hosting service's reply, to a request made with the credential, that names the account the credential acts as and the account's kind.
- **An account's kind** is what the service records it as: a user's account, or a bot's account, as the service records the account an app acts through. A user account kept for an agent, a machine user, is a user's account.
- **An unresolved identity** is every outcome of asking other than the service's answer, reported with its cause ([project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162)).
- **A run** is one invocation of one command, from its start to its exit. The state-issue seam defines the term for a capability's commands ([ADR-071](ADR-071-state-issue-seam.md) point 8), and this record takes it for every command, the backbone's among them.
- **The service's host** is the host a request to the hosting service goes to, such as an enterprise's own. It is no *agent host*, the software outside pkit that starts harness sessions for a person ([ADR-091](ADR-091-no-host-component.md)).

**What happens today.** Five readers ask the service on their own, and fail three ways:

- **The engine's default actor.** Where its caller names no actor, the engine's move asks the service for the login, and takes the fixed value `operator` where the ask fails. Its status view and its check whether a move may be made take `operator` without asking. The engine's page warns a caller to name one actor on each call, or a sign-off gate can give two verdicts.
- **The cross-authority gate** passes where the authorisation's producer is not the actor, compared as two strings. `operator` equals no login, so a gate judged under it passes whoever produced the authorisation, the actor included.
- **project-management's move** writes the move to the tracker first, then hands it to the engine to journal, and only warns where the engine refuses. So the engine's verdict decides what the journal records, and the move to Done is guarded by the capability's own approval check ([project-management:DEC-026](../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)). As the actor, it hands the engine its membership identity, which is `PM_INVOKER_LOGIN` wherever that is set, and may name the person an agent works for. Where that identity is unresolved, it hands none, and the placeholder decides.
- **`pkit report`** names the login in the confirmation it asks before it posts. Where the ask fails, it names "your gh CLI identity (login unresolved)", and posts once the person confirms.
- **project-management asks in three places of its own:** the membership gate, which reports an unresolved identity with its cause; the review command's check for a pull request of one's own; and workstream sync's check for comments of its own.

**What was measured.** On a trial of an agent working under a GitHub App installation's token ([project-kit#3004](https://github.com/aleskalfas/project-kit/issues/3004)), the request for the signed-in user was refused with "Resource not accessible by integration (HTTP 403)". Read afterwards under the maintainer's own credential ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)), the App's account has two spellings:

- **the service's REST interface** gives its login as `<name>[bot]`, of type `Bot`;
- **gh's JSON** gives the same account as `app/<name>`, marked as a bot.

gh writes the second and takes the first. project-kit's own workflow that keeps the friction report's tracking issue lists its issues by the author `github-actions[bot]`, since a listing by `app/github-actions` matches nothing, and the issues listed then give their author as `app/github-actions`.

Whether an installation's token can learn its own account and kind, by any request, is not measured. The trial's two attempts to have its agent ask failed before the agent was reached.

**What the service documents.**

- **A user's login** holds only letters, digits and dashes, and a managed user's adds an underscore and the enterprise's short code ([GitHub, "Username considerations for external authentication"](https://docs.github.com/en/enterprise-cloud@latest/admin/managing-iam/iam-configuration-reference/username-considerations-for-external-authentication)). So no user's login holds a bracket.
- **An app's name** may not be an existing account's, unless it is its owner's own user or organization name ([GitHub, "Registering a GitHub App"](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)). So an app's account may share its owner's name.
- **An installation's token** is refused by some REST endpoints. The service's guide gives a GraphQL query for the signed-in account, its `viewer`, as an example of a request made with one, and does not say what it answers ([GitHub, "Authenticating as a GitHub App installation"](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation)).
- **An account's name is looked up without regard to case,** as the REST reference says of a repository's owner ([GitHub, "REST API endpoints for assignees"](https://docs.github.com/en/rest/issues/assignees)).
- **A login given up by a rename** is free for anyone else to claim ([GitHub, "Changing your GitHub username"](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-personal-account-settings/changing-your-github-username)).

**What the records already say.**

- **A gate's authorisation must come from another authority than the actor it gates** ([COR-033](../../../.pkit/decisions/core/COR-033-process-substrate.md) P4). The engine confirms neither the actor nor the producer, so the gate holds only where the caller names the actor truthfully ([the process area's reference, "Gate-checkability"](../../../.pkit/process/README.md#gate-checkability-the-load-bearing-rule)).
- **The backbone may not depend on a capability** ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md), "The dependency direction cannot invert").
- **A capability's scripts reach the backbone by command, and each computation keeps one home** ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) points 1 and 2). A query a capability supplies runs with its environment marked offline (point 3).
- **The backbone's landing of pull requests** is GitHub-only, labelled, and placed provisionally, with the core question raised in [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222). It reads its host from the caller's environment, and its documents are a versioned contract ([ADR-061](ADR-061-hosting-service-acts-in-the-backbone.md) points 3, 4 and 7).
- **`pkit report`'s confirmation names the account it posts as,** so that a split between the command line's account and the browser's never misattributes a post ([project-kit#662](https://github.com/aleskalfas/project-kit/issues/662)). With nobody at the terminal, it keeps the draft and posts nothing ([ADR-047](ADR-047-report-cross-repo-write.md) point 2).
- **The membership gate** reads the service's login first, by the request its item 1 names, git's configured email second and an environment variable third. It leaves identity resolution's edge cases, the posture on network errors, and caching to its implementation ([project-management:DEC-021](../../../.pkit/capabilities/project-management/decisions/DEC-021-team-membership-gate.md), "Identity resolution" and "Why mechanism details are deferred"). The member list's schema describes a member's login as the value the service answers for that member.
- **A service's account in project-management's lists.** The capability admits a CI service's account as a member (DEC-021, Implications, "CI invocations"; [project-management:DEC-022](../../../.pkit/capabilities/project-management/decisions/DEC-022-methodology-mesh.md), "Authority"). It registers a remote reviewer agent's account, a bot's, an App's or a service account's, and matches a verdict's author against it ([project-management:DEC-028](../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md), "Path 1: Remote agent"). None fixes how such an account is spelled, and DEC-028's example writes one by a bare login.

## Decision

**Which account a credential acts as is read once, in the backbone, and only the hosting service's answer names the account and its kind. Every reader uses that reading, compares accounts in one spelling, and decides in its own record what it does with an unresolved identity. The process engine reads no account: it judges a cross-authority gate only for an actor its caller names, and never takes a placeholder. `pkit report` never posts as an account it cannot name. The placement is GitHub's, and provisional.**

### 1. One reading of the acting account, in the backbone

- **One home.** One module of the backbone, the acting-account reading, asks the service which account the credential acts as. Nothing else in pkit asks.
- **Every reader takes it from there:** the account `pkit report` posts as (point 6), and each command of a capability that needs the account its credential acts as (point 8), the actor it names to the engine among them (point 5). No reader asks the service a way of its own, a tool's own shorthand for the signed-in account among them.
- **How a reader reaches it.** The backbone's code imports it. A capability's scripts reach it through a reading command of the backbone, whose output is a document with a schema version, under the contract ADR-061 point 7 sets for the hosting service's documents.
- **What the document gives:** the account in the one spelling (point 3), its kind, the numeric id the service gives it, and its login as the service answered it. Under an unresolved identity, it gives the cause.
- **The request is chosen by measurement.** Before the reading's request is fixed, the build asks each request the service documents for the signed-in account, under a user's credential and under an installation's token. It takes one that answers with the account and its kind under both, where one does. Where none answers under an installation's token, it takes one that answers under a user's credential, and an installation's token reads as unresolved. The REST request for the signed-in user is refused under an installation's token, as measured.
- **Apart from the local readings.** The reading reaches the network, so it stays apart from the reading of the repository, which needs none (ADR-061 point 2). For the same reason no query calls it: no resolver, filler or validator. Under the offline marker a query's run carries (ADR-057 point 3), it asks nothing, and the identity is unresolved, with that cause. It changes nothing, so it runs no cross-repository guard.
- **The service's host** comes from the caller's environment, never from a configuration of the backbone's (ADR-061 point 4). A capability that keeps its own host passes it on through the environment.
- **Bounded.** An ask is bounded in time, and one that runs out is no answer.

### 2. Only the service's answer names the account and its kind

- **Resolved** only where the service, asked with the credential, answers with the account the credential acts as and that account's kind. A login the service answers with the bot suffix names a bot's account, since no user's login can carry it. The reading gives the account in the one spelling (point 3), with its kind.
- **Unresolved** in every other outcome, each reported with its cause:
  - a refusal, whatever its cause;
  - no answer, such as with the tool missing, no network, a timeout, the offline marker, or something other than the service answering;
  - an answer that names no account, or an account of a kind the reading does not know.
- **Never from anything else:**
  - the wording of a refusal, which a rate limit or a suspended account can give as well as an app;
  - the credential's own form;
  - the record the tool that issued the credential keeps of who signed in;
  - git's configured identity, or a variable or setting that names an account;
  - which agent host started the session, which pkit never tests (ADR-091 point 2).
- **No fallback.** The reading gives no account the service did not answer with. What a reader does under an unresolved identity is decided in the reader's own record: point 6 for `pkit report`, and a capability's records for its commands (point 8).
- **Installation tokens.** Whether one gets an answer decides only which credentials resolve. Where none does, every such credential reads as unresolved, and each reader acts as its record says for that.

### 3. One spelling of an account, its kind included

- **The spelling.** A user's account is spelled by its login. A bot's account is spelled by its login with the service's bot suffix, as `name[bot]`, which is the login the service's REST interface gives an app's account. Where a bot's login lacks the suffix, the spelling adds it. An account of another kind, such as an organization's, is spelled by its login, since only an app may take another account's name.
- **It carries the kind.** No user's login can hold the suffix's brackets, and every bot's spelling holds them. So a bot's account never reads as a user's, even where an app took its owner's own name. A bare login given with no kind reads as a user's.
- **Case.** The service looks an account's name up without regard to case, so every comparison of two spellings ignores case. A spelling is written down in the case the service answered.
- **One function** beside the reading puts an account named by any surface into the one spelling, and compares two spellings. gh's JSON is such a surface: it writes a bot's account with an `app/` prefix. The function takes many accounts in one call. Where a surface gives an account's kind apart from its login, a reader asks for the kind with the login, since the bare login of an app's account may be its owner's.
- **Where it binds.** Every comparison of two accounts compares them in this spelling, and every account pkit writes down is written in it. The backbone's code calls the function. A capability's scripts reach it through the backbone's reading command, and keep no copy of it (ADR-057 point 2). A request to the service that names an account names it by the login the service answered.
- **Stored accounts.** A user's login is already in this spelling, and the member list's schema describes a member's login as the value the service answers for that member, so no entry that names a user changes. An entry that names a service's account, as a member or as the remote reviewer, is written in this spelling, an App's as `name[bot]`. One already written with an App's bare login reads as a user's login, so it does not match the App's account. No migration rewrites such an entry, since a bare login cannot be told from a user's without asking the service. A comparison against it fails closed: what the App's account writes stops counting, and nothing counts that did not before. How a capability's commands point to such an entry is the capability's (point 8).

### 4. An answer lasts one run

- **Within a run,** the reading asks at most once and reuses its answer. A capability's command that reaches it by command keeps the answer for its own run.
- **Handed on.** Where a run starts a command that takes the account as an argument, such as the engine's move, which takes it as the actor, it hands the account on. The command it starts takes the account as its caller's word.
- **Across runs, nothing is kept.** An answer kept from an earlier run, even for the same credential, is no answer of the service's. So each run that needs the account asks.

### 5. The engine reads no account, and takes no placeholder

- **The actor is the caller's.** The actor a gate judges is the authority the move is made by, in the terms of the binding whose gate judges it (COR-033 P4). The engine takes it from its caller and from nowhere else: it asks no service, and takes no default. An actor named blank names none.
- **One rule in every command.** Every engine command that judges a gate, such as the status view, the check whether a move may be made and the move, judges it for the actor named, or for none. So a precheck and its move judge one actor.
- **What it compares.** The engine compares the actor with the producer the binding's predicate reports, as given, and confirms neither.
- **With no actor named:**
  - a gate that must confirm its authorisation came from another authority refuses, since nothing can confirm it. It says that no actor was named, and that a caller names the authority the move is made by: never one it acts for, and never a placeholder;
  - a move none of whose gates compares the actor goes on, and its journal entry records that no actor was named, in a form no named actor can take.
- **No placeholder.** No fixed value stands for an actor no caller named.
- **A binding whose authorities are accounts on the hosting service,** as project-management's are, names as its actor the account the move is made as: the account its credential acts as, from the reading, never a person the caller acts for. That is this record's reading of P4 for such a binding: its predicates report each producer as an account, so the actor compared with them is an account too. A person and an agent working under one credential are then one actor. The binding's wrapper names the actor, and its predicates report each producer, in the one spelling and in the case the service answered, so the engine's comparison as given compares like with like. Which other value may stand for that account where the reading is unresolved is the capability's (point 8).
- **A binding whose authorities are no such accounts,** such as one whose sign-off is a name in a file, names its actors in its own terms.

### 6. `pkit report` posts only as an account it can name

- **The confirmation** names the reading's account, and says when it is a bot's.
- **Under an unresolved identity,** the command posts nothing through the service. It says it cannot tell which account it would post as, and why, and keeps the payload as a draft, as it does with nobody at the terminal (ADR-047 point 2). The draft is posted later, by a person, once the reading names the account, or through the prefilled form, whose account the browser decides, as ADR-047 already warns.
- **The listing of one's own reports** filters by the reading's account. Under an unresolved identity, it says it cannot tell whose reports to list.

### 7. GitHub only, through `gh`, and provisional

- **Written for GitHub.** The request the reading makes, the kinds it knows and the spelling are GitHub's. Its reference says so, and its document uses GitHub's vocabulary.
- **Provisional, on ADR-061 point 3's ground.** The backbone's report command needs the reading, and the backbone cannot depend on a capability (COR-010). Whether core content may read or act on one hosting service under a label is raised in [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222), and this placement joins that question.
- **The engine stays out of it.** It reads no account and respells none (point 5), so nothing of GitHub's reaches it.
- **On another service,** `gh` cannot answer, so the identity is unresolved. Each reader then acts as its record says for no answer, and none takes a wrong account.
- **When to revisit:**
  - when [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222) is decided;
  - when a second hosting service is supported. The reading's document then becomes a contract in a vocabulary of its own, and the spelling names the service, since two services' logins may coincide.

### 8. The backbone reads; each reader decides

- **The backbone** holds the reading and the spelling. It decides here what its own reader does (point 6), and what the engine takes as an actor (point 5). It reads no capability's files or settings for the account, and calls no capability to learn it (COR-010).
- **A capability's commands** take the acting account and its spelling from the backbone, by command (ADR-057 point 1). Each capability decides in its own records:
  - what its commands do with an unresolved identity, or with a bot's account;
  - which other values, such as an email or a variable that names a person, may stand beside the reading's account, within point 5 where its commands name the engine's actor.

  The reading gives none of them.
- **project-management's commands** are one reader. The membership gate takes its first surface, the service's login, from the reading, in the one spelling. Its other surfaces are the capability's records' to decide.
- **What this binds:** pkit's own code and the capabilities project-kit ships. The reading command and its document are part of pkit's public surface, so a capability another project writes may use them. Nothing here binds it to, since an architecture record reaches no other project ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)). No such capability is known to need the acting account, so no core record is proposed for one.

## Rationale

**Why one reading.** Five readers ask on their own today, and fail three ways: with no account, with the placeholder, or with the actor left to the engine. That is the recurrence that calls for one home ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)). The copies already disagree where it costs most. Where project-management cannot name its account, it hands the engine no actor. The engine's own ask fails the same way, and it takes the placeholder, so the agent's own merge is journaled as another authority's.

**Why in the backbone.** `pkit report` is the backbone's, and needs the reading whatever a project installs. The backbone cannot depend on a capability (COR-010), and asking one by command, optionally, as `pkit report` asks project-management for a workstream ([ADR-050](ADR-050-report-context-sourcing.md) point 2), fails wherever the capability is absent. A capability reaches the backbone by command (ADR-057 point 1). So the backbone is the one home every reader can reach, as ADR-061 found for landing a pull request.

**Why only the service's answer.** Any other source is a second reading that can disagree with the service:

- **A refusal** has many causes, an app's credential among them.
- **A credential's form** is the issuer's convention. It can disagree with the service's answer in a case nobody has measured, a person's sign-in through an app, and reading it means reading the secret.
- **The issuing tool's record** of who signed in is overridden by a token passed in the environment.
- **Git's configured identity** names whoever set the machine up.

Without the service's answer, pkit cannot tell an app's credential from a person's. Any fallback would make a person the acting account, under an app's credential, whenever its ask fails.

**Why the reading offers no fallback, and leaves the response to each reader.** What a reader may do without an answer turns on what it guards. `pkit report` guards a public post, project-management's move names the actor of a cross-authority check, and the membership gate keeps its own sources by its own record. One fallback in the reading would decide all of them at once, and would carry a capability's choice into the backbone.

**Why the engine reads no account.** The engine is content-free (COR-033): an actor is whatever authority a binding means, and only the binding knows which. The process area's walkthrough binds a sign-off read from a file, whose actors are names that no account of the service's would match. A default read from the service would tie every binding to one service's accounts. It would also cost callers that need none of it: each status view would ask the service, and a binding whose checks read only local files would wait out the time bound offline, then refuse. And it guards nothing a named actor does not. Any caller may name an actor, and the engine takes its word, so a default helps only an honest caller who left the actor out. So the caller that knows the binding's terms names the actor, and the engine refuses where it is told none.

**Why a binding of accounts names the account its credential acts as.** P4 asks that an authorisation come from another authority than the actor. Where a binding's predicates report producers as accounts, the comparison means something only against an account, and the account that makes the move is the one its credential acts as. A person's name in its place would make an agent's own merge read as another authority's, the person's. Naming the account makes a person and their agent under one credential one actor, which is what the service records.

**Why the binding spells both sides, and the engine compares as given.** The engine's comparison is the check COR-033's Rationale calls load-bearing. A producer reported in another spelling than the actor's makes an actor's own merge read as another authority's. Respelling in the engine would carry one service's spellings into a content-free engine. The binding's wrapper and its predicates both reach the backbone's function, so the two arrive in one spelling, and the process area's reference states this as part of the predicate's contract.

**Why the service's REST spelling.** It is the service's own login for an app's account, and carries the kind in its form, so no field is added, and the member lists hold users' logins in it already. gh takes it as input and writes its own form only as output, as project-kit's own friction workflow found (Context). gh's form is a tool's spelling, which the service's other surfaces do not use. A bare login would drop the kind, and an app may take its owner's name, so the app's account would compare equal to its owner's. The suffix is added where a bot's login lacks it, so the spelling carries the kind for every bot, an app's or another.

**Why comparisons ignore case.** The service looks an account's name up without regard to case, so two spellings that differ only in case name one account. At a cross-authority comparison, unequal reads as another authority, so a comparison that heeded case would fail open on a login typed in another case.

**Why an answer lasts one run.** An answer kept across runs needs a key for the credential, which means reading the secret or trusting the issuing tool's record (point 2). It can also go stale: a login renamed, and perhaps claimed by another account, or a setup that swaps one credential for another, would act on the earlier account. What it would save is a request for each run that needs the account. That is more than one a command: a command that starts others, as a landing starts a merge and a move, costs one in each unless it hands the account on (point 4), and an installation's tokens share one limit on requests across every session that holds them. It buys no work offline, since every reader reads or writes the service in the run that asks.

**Why no placeholder actor.** A placeholder equals no account, so every cross-authority gate passes under it. Refusing such a gate costs its caller a named actor. Under a credential that never resolves, it costs more. project-management makes a move first and journals it after, so each of its moves through such a gate is left out of the journal, with a warning, and the journal's drift check reports the gap. That is the honest record of a move whose gate nobody judged. A move none of whose gates compares the actor loses nothing by an unknown actor, so it goes on, and the journal says so plainly.

**Why `pkit report` keeps the draft.** The confirmation names the posting account so that a person never posts a public issue as an account they did not expect ([project-kit#662](https://github.com/aleskalfas/project-kit/issues/662)). With the identity unresolved, it cannot name one, so the post waits for a way that can, as it does with nobody at the terminal.

**Why GitHub only, provisionally.** One service is all pkit supports. A neutral vocabulary would be GitHub's renamed, and COR-007 extracts a common form only once a second instance shows what is common. The conflict between a GitHub-only backbone and the core records is the one ADR-061 point 3 raised, and the same core decision settles both.

### Alternatives considered

- **Each reader keeps its own ask.** Rejected: the copies already disagree, and at the engine's gate the disagreement turns an actor's own merge into another authority's.
- **The reading in project-management, which the backbone asks by command.** Rejected: `pkit report` would lose the reading wherever the capability is not installed (COR-010).
- **An interim reading in project-management, moved to the backbone later.** Rejected: until the move, two readings of one credential run side by side, and they already disagree at the engine's gate.
- **The kind read from the credential's form,** such as the prefix the service gives each kind of token. Rejected: it is a second reading that can disagree with the service, the secret must be read to see it, and an unknown form leaves the identity unresolved anyway.
- **An app's credential read from the service's refusal.** Rejected: a refusal has other causes, and names no account to act as.
- **A fallback in the reading,** to git's identity, a variable or the tool's record. Rejected: without the service's answer, a fallback makes a person the acting account under an app's credential, and it decides for every reader what only each reader's record should.
- **An answer kept across runs, keyed by a digest of the credential.** Not taken: it needs the secret read, it can go stale, and it saves a request for each run that needs the account. It is weighed again if the service's limits on requests are seen to bite.
- **The engine's default actor is the reading's account,** where its caller names none. Rejected: it ties a content-free engine to one service's accounts, which a binding of names in a file cannot use. Every status view would ask the service, and a binding of local checks would wait offline. And it guards nothing a named actor does not, since any caller may name one.
- **A flag that has the engine take the reading's account.** Not taken: it puts the hosting service back into the engine, for what a person gets by naming the account the reading command shows.
- **The engine respells the actor and the producer.** Rejected: it carries one service's spellings into a content-free engine, and the binding's wrapper and predicates already reach the function.
- **A move with no actor named is journaled, its gate marked as not judged,** in place of refusing it. Not taken: every entry of a journal is a move the engine made past its gates (COR-033 P3), and journaling one whose gate nobody judged would take the caller's word for the gate, which P4 forbids. The gap is reported instead. It is weighed again if a credential that never resolves proves the usual one in a project that keeps a journal.
- **Accounts compared by kind and numeric id,** with logins kept for display and the member lists. Not taken: the member lists and the registered reviewer hold logins, and a predicate names its producer by one string, so both forms would change and every entry would migrate. The risk it closes is a login renamed and then claimed by another account, which reaches only an entry kept past the rename. The document gives the id, so a record that comes to need it compares by it without a new version of the document (ADR-061 point 7).
- **A spelling with the kind as a field of its own.** Rejected: every member list and every stored account would need a migration, and the service's login already carries the kind.
- **gh's spelling, with its `app/` prefix.** Rejected: it is a tool's output, which gh itself does not take as input and the service's other surfaces do not use, and the member list's schema already describes the service's.
- **The bare login.** Rejected: an app may take its owner's name, so its account would compare equal to its owner's and pass as the owner.
- **Comparisons that heed case.** Rejected: two spellings of one account would read as two authorities.
- **The engine refuses every move with no actor named.** Rejected: a move whose gates compare no actor would stop for nothing.
- **`pkit report` posts under an unresolved identity once the person confirms,** as it does today. Rejected: the confirmation exists to name the posting account, and here it cannot (point 6).
- **A reading neutral to the hosting service now.** Rejected: with one service, the neutral form is GitHub's renamed (COR-007; ADR-061 point 3).

## Implications

- **Edits, once a person accepts this record,** made in this change. Each is a refinement in place, and none overturns a passage. Each takes a forward pointer to this record: `(refinement per [pkit:ADR-094])` in a capability's record, and the same pointer as a relative link in an architecture record.
  - **[ADR-047](ADR-047-report-cross-repo-write.md) point 2,** which the architect refines. The confirmation names the reading's account as the posting account, said to be a bot's where it is one. Under an unresolved identity, `pkit report` posts nothing through the service, says why, and keeps the payload as a draft. A narrowing: the point's first bullet confirms "under your gh identity" and posts, and its refinement from [project-kit#662](https://github.com/aleskalfas/project-kit/issues/662) has the confirmation name the posting login, so where no login can be named the point leaves no outcome but to confirm and post. This takes that case out of "confirm, then post" and into the draft, and the never-silent gesture stands. The edit is folded into the point's body, and the point's two dated refinement blocks are folded in with it, changing nothing they decide.
  - **[project-management:DEC-021](../../../.pkit/capabilities/project-management/decisions/DEC-021-team-membership-gate.md), "Identity resolution", item 1,** which the change's author refines. The service's login is the account the hosting service answers the credential acts as, read through the backbone's reading of the acting account once in a run and kept from no earlier run. It is matched against a member's login in the one spelling, without regard to case. A completion: item 1 names a request for the login, a mechanism this replaces while the service's login stays first. DEC-021 defers identity resolution's edge cases, and caching, to its implementation ("Identity resolution", its last paragraph, and "Why mechanism details are deferred"), and this settles two of them for that read: the spelling a login is matched in, and that no answer is cached across runs. The edit touches none of items 2 and 3, the paragraph on matching, and the paragraph on what is deferred, which stands for every other read.
  - **[project-management:DEC-028](../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md), "Two paths, two registration lists", "Path 1: Remote agent", and the "Sub-decisions index" row "Remote-path identity check",** which the change's author refines. A registered remote reviewer's login is the agent's account in the one spelling: an App's is written `<name>[bot]`, and a machine user's by its login. A verdict's author matches it in that spelling. The registration list's example and its comment say so. A completion: DEC-028 registers an account it means for a bot, an App or a service account, and fixes no spelling for it. No migration rewrites an entry, for the reason point 3 gives.
- **Records not edited.**
  - **[ADR-041](ADR-041-instance-ownership-substrate-contract.md) and ADR-071 point 3** compare a comment's author with an assignee or a member. Point 3 here governs those comparisons, and neither record states a spelling of its own.
  - **DEC-021's Implications and DEC-022's "Authority"** admit a service's account as a member, and neither fixes or shows a spelling for it. Point 3 here governs how such an entry is spelled and compared.
  - **[ADR-020](ADR-020-process-engine-code-home.md) and ADR-061** stand. This record places one more read of the hosting service beside the acts ADR-061 placed, and keeps it out of the engine ADR-020 placed.
  - **COR-033** is realised, not changed. PRJ-008 stands.
- **The work,** once this record is accepted:
  - **The reading:** first the measurement that chooses its request (point 1), then the reading and the one function, with the reading command and its document, and tests that fake `gh`. Accepting this record waits on no measurement, since the reading holds whatever it shows (point 2).
  - **The engine:** its status view, move check and move take no default actor, refuse a cross-authority gate where no actor is named, and journal a move that names none as having none. The tests that pin the placeholder change with it. The engine's page and the process area's reference state the actor's contract (point 5), the predicate's duty to report a producer as its binding names actors, and the walkthrough's advice on naming the actor.
  - **`pkit report`:** its confirmation, its draft under an unresolved identity, and its listing by the reading's account.
  - **project-management:** its three readers and the membership gate's first surface move onto the reading command. Its move names its actor from the reading, as point 5 has it, and none where the reading is unresolved, unless a record of its own lets another value stand for that account. Its gate's predicate reports the merging account in the one spelling, and the remote reviewer's match compares in it. The schemas that describe a login describe the one spelling. The order in which the membership gate tries its surfaces stays as it stands, for the record on [project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175) to decide.
  - **The CLI reference,** where it describes the engine's actor, the reading command, and the account `pkit report` posts as.

  None of it changes the form of anything a project holds, so it ships no migration (point 3). Its surface changes are each declared by a changeset of the component they change, of a segment a person judges. In the backbone, they are the engine's lost default and `pkit report`'s refusal under an unresolved identity. In project-management, they are the actor its move names and the remote reviewer's match in one spelling. What they cost, for whoever judges the segments:
  - a direct caller of the engine's status view or move check, and a person running a move by hand, names an actor, or sees cross-authority gates refuse;
  - under a credential that never resolves, such as an installation's token if no request answers it, each of project-management's moves through the gate on Done is left out of the journal, with a warning, and the drift check reports the gap. A workflow whose moves are journaled under the variable's value meets the same, unless a record of the capability's lets the variable stand for its account;
  - an App registered by its bare login, as a member or as the remote reviewer, stops matching its own account until its entry is respelled.
- **Left out, for records of their own:**
  - what a capability's commands do with an unresolved identity or a bot's account, which is project-management's to decide, in a record of its own ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164));
  - git's email and the variable beside a person's login, at the membership gate ([project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175));
  - the person an agent works for, which names no account the credential acts as, so it is no reading of the acting account. The record on who may authorise in a turn a chat started (ADR-091, Implications) may give the backbone a reading of it;
  - whether the predicate of project-management's gate on the move to Done reports the approval rather than the merge ([project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171));
  - how far the reading holds for another hosting service (point 7, [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222)).
- **Stands on** COR-007, COR-010, COR-025, COR-033, PRJ-008, ADR-020, ADR-041, ADR-047, ADR-050, ADR-057, ADR-061, ADR-071, ADR-091, and project-management's DEC-021, DEC-022, DEC-026 and DEC-028, all accepted.
