---
id: ADR-094
title: The acting account is read once, in the backbone, from the hosting service's answer
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** pkit sometimes needs to know which account on the hosting service its credential acts as. `pkit report` needs it to tell the person which account a report will be posted as. project-management's commands need it for the membership gate, to name who makes a move, and more. Each asks on its own today, and they fail in different ways. Under a GitHub App's token the usual question is refused. The process engine asks too, and then takes a made-up actor that matches nobody, so its check that an authorisation came from someone other than the actor passes whoever gave it, the actor included.

This record makes one reading in the backbone, which every reader uses, and takes the engine out of the asking:

- **Only the service names the account.** The reading names an account, and whether it is a user's or a bot's, only from the hosting service's own answer. Every other outcome is an unresolved identity, reported with its cause, and the reading falls back to nothing.
- **One spelling.** Accounts are compared and written down in one spelling that carries the kind: a user's account by its login, a bot's with the service's `[bot]` suffix. Users' logins are already written that way, so no entry that names a person changes. A login given without its kind is no user's: it is granted nothing, and never read as another authority. Case is ignored.
- **An answer lasts one run.** Nothing kept from an earlier command counts as the service's answer.
- **The engine asks nobody.** It takes the actor its caller names, and none by default. A gate that must confirm another authority refuses where no actor is named, rather than pass under a placeholder, and it compares the actor with the authorisation's producer without regard to case. A caller whose actors are accounts on the hosting service names the account its credential acts as, from the reading.
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

**What happens today.** Five readers ask the service which account acts, each on its own: the engine's move, `pkit report`, and three of project-management's. They fail three ways: with no account, with a placeholder, or with the actor left to the engine.

- **The engine's default actor.** Where its caller names no actor, the engine's move asks the service for the login, and takes the fixed value `operator` where the ask fails. Its status view and its check whether a move may be made take `operator` without asking. The engine's page warns a caller to name one actor on each call, or a sign-off gate can give two verdicts.
- **What the placeholder does at the cross-authority gate.** The gate passes where the authorisation's producer is not the actor, compared as two strings, case and all. `operator` equals no login, so a gate judged under it passes whoever produced the authorisation, the actor included.
- **What project-management's move hands the engine.** It writes the move to the tracker first, then hands it to the engine to journal, and only warns where the engine refuses. So the engine's verdict decides what the journal records, and the move to Done is guarded by the capability's own approval check ([project-management:DEC-026](../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)). As the actor, it hands the engine its membership identity, which is `PM_INVOKER_LOGIN` wherever that is set, and may name the person an agent works for. Where that identity is unresolved, it hands none, and the placeholder decides.
- **`pkit report`** names the login in the confirmation it asks before it posts. Where the ask fails, it names "your gh CLI identity (login unresolved)", and posts once the person confirms.
- **project-management's three readers of its own:** the membership gate, which reports an unresolved identity with its cause; the review command's check for a pull request of one's own; and workstream sync's check for comments of its own.

**What was measured.** On a trial of an agent working under a GitHub App installation's token ([project-kit#3004](https://github.com/aleskalfas/project-kit/issues/3004)), the request for the signed-in user was refused with "Resource not accessible by integration (HTTP 403)". Read afterwards under the maintainer's own credential ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)), the App's account has two spellings:

- **the service's REST interface** gives its login as `<name>[bot]`, of type `Bot`;
- **gh's JSON** gives the same account as `app/<name>`, marked as a bot.

gh writes the second and takes the first. project-kit's own workflow that keeps the friction report's tracking issue lists its issues by the author `github-actions[bot]`, since a listing by `app/github-actions` matches nothing, and the issues listed then give their author as `app/github-actions`.

gh's own source says how its JSON writes an author ([cli/cli, `api/queries_issue.go`](https://github.com/cli/cli/blob/trunk/api/queries_issue.go)):

- **an author the service does not record as a user,** a bot among them, as `app/` and its login, marked as a bot, with no id;
- **a comment's author** by its login alone, with no kind. For an app's account, that is the bare name gh prefixes elsewhere.

Whether an installation's token can learn its own account and kind, by any request, is not measured. The trial's two attempts to have its agent ask failed before the agent was reached.

**What the service documents.**

- **A user's login** holds only letters, digits and dashes, and a managed user's adds an underscore and the enterprise's short code ([GitHub, "Username considerations for external authentication"](https://docs.github.com/en/enterprise-cloud@latest/admin/managing-iam/iam-configuration-reference/username-considerations-for-external-authentication)). So no user's login holds a bracket.
- **An app's name** may not be an existing account's, unless it is its owner's own user or organization name ([GitHub, "Registering a GitHub App"](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)). So an app's account may share its owner's name.
- **An installation's token** is refused by some REST endpoints. The service's guide gives a GraphQL query for the signed-in account, its `viewer`, as an example of a request made with one, and does not say what it answers ([GitHub, "Authenticating as a GitHub App installation"](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation)).
- **An account's name is looked up without regard to case,** as the REST reference says of a repository's owner ([GitHub, "REST API endpoints for assignees"](https://docs.github.com/en/rest/issues/assignees)).
- **The service's search** names an app's account as `app/<name>`, as in `author:app/robot` ([GitHub, "Searching issues and pull requests"](https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests)).
- **A login given up by a rename** is free for anyone else to claim ([GitHub, "Changing your GitHub username"](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-personal-account-settings/changing-your-github-username)).

**What the records already say.**

- **A gate's authorisation must come from another authority than the actor it gates** ([COR-033](../../../.pkit/decisions/core/COR-033-process-substrate.md) P4). The engine confirms neither the actor nor the producer, so the gate holds only where the caller names the actor truthfully ([the process area's reference, "Gate-checkability"](../../../.pkit/process/README.md#gate-checkability-the-load-bearing-rule)).
- **The engine's cross-authority check** passes where the authorisation exists, names its producer, and the producer differs from the actor ([ADR-036](ADR-036-open-region-engine-strategy.md) point 4). Written so, it passes with no actor named, a case it never met while the engine always had a default.
- **A wait** is derived from the gates' verdicts: a subject with no legal move, or one whose only way on is a person's move, with no autonomous move open ([COR-034](../../../.pkit/decisions/core/COR-034-human-pause-gate.md)).
- **The journal's entries** record who moved the subject, one for each move the engine executes (COR-033 P7). Where project-management keeps a journal, it is the capability's canonical audit trail. A move that fails to journal is surfaced rather than dropped, and where labels carry the state, the drift check reads a state change with no entry as an out-of-band change or a governed move that failed to journal ([project-management:DEC-049](../../../.pkit/capabilities/project-management/decisions/DEC-049-audit-journal-model.md) points 1 and 3).
- **The backbone may not depend on a capability** ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md), "The dependency direction cannot invert").
- **A capability's scripts reach the backbone by command, and each computation keeps one home** ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) points 1 and 2). A query a capability supplies runs with its environment marked offline (point 3).
- **The backbone's landing of pull requests** is GitHub-only, labelled, and placed provisionally, with the core question raised in [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222). It reads its host from the caller's environment, and its documents are a versioned contract ([ADR-061](ADR-061-hosting-service-acts-in-the-backbone.md) points 3, 4 and 7).
- **`pkit report`'s confirmation names the account it posts as,** so that a split between the command line's account and the browser's never misattributes a post ([project-kit#662](https://github.com/aleskalfas/project-kit/issues/662)). With nobody at the terminal, it keeps the draft and posts nothing ([ADR-047](ADR-047-report-cross-repo-write.md) point 2).
- **The membership gate** reads the service's login first, by the request its item 1 names, git's configured email second and an environment variable third. Its code reads the variable first, in place of the login, wherever it is set. The record leaves identity resolution's edge cases, the posture on network errors, and caching to its implementation ([project-management:DEC-021](../../../.pkit/capabilities/project-management/decisions/DEC-021-team-membership-gate.md), "Identity resolution" and "Why mechanism details are deferred"). The member list's schema describes a member's login as the value the service answers for that member.
- **A service's account in project-management's lists.** The capability admits a CI service's account as a member (DEC-021, Implications, "CI invocations"; [project-management:DEC-022](../../../.pkit/capabilities/project-management/decisions/DEC-022-methodology-mesh.md), "Authority"). It registers a remote reviewer agent's account, a bot's, an App's or a service account's, and matches a verdict's author against it ([project-management:DEC-028](../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md), "Path 1: Remote agent"). None fixes how such an account is spelled, and DEC-028's example writes one by a bare login.

## Decision

**Which account a credential acts as is read once, in the backbone, and only the hosting service's answer names the account and its kind. Every reader uses that reading, compares accounts in one spelling that fails closed where a kind is unknown, and decides in its own record what it does with an unresolved identity. The process engine reads no account: it judges a cross-authority gate only for an actor its caller names, without regard to case, and never takes a placeholder. `pkit report` never posts as an account it cannot name. The placement is GitHub's, and provisional.**

### 1. One reading of the acting account, in the backbone

- **One home.** One module of the backbone, the acting-account reading, asks the service which account the credential acts as. Nothing else in pkit asks.
- **Every reader takes it from there:** the account `pkit report` posts as (point 6), and each command of a capability that needs the account its credential acts as (point 8), the actor it names to the engine among them (point 5). No reader asks the service a way of its own, a tool's own shorthand for the signed-in account among them.
- **How a reader reaches it.** The backbone's code imports it. A capability's scripts reach it through a reading command of the backbone, whose output is a document with a schema version, under the contract ADR-061 point 7 sets for the hosting service's documents.
- **What the document gives:** the account in the one spelling (point 3), its kind, the numeric id the service gives it, and its login as the service answered it. Under an unresolved identity, it gives the cause.
- **The request is chosen by measurement.** Before the reading's request is fixed, the build asks each request the service documents for the signed-in account under three credentials: a user's, an App installation's token, and a workflow's token.
  - **What holds.** A request holds for a credential only where it names the account the service records for it, with that account's kind: the user's own account as a user's, and the App's own account as a bot's. A request that answers an installation's token with another account, or with the App's account as a user's, does not hold for it.
  - **What is taken.** The build takes a request that holds under all three, where one does. Where none holds under the two tokens, it takes one that holds under a user's credential and answers such a token with no account, so that the token reads as unresolved.
  - **What is known.** The REST request for the signed-in user is refused under an installation's token, as measured.
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
- **It carries whether the account is a bot's.** No user's login can hold the suffix's brackets, and every bot's spelling holds them. So a bot's account never reads as a user's, even where an app took its owner's own name.
- **A login with no kind.** The one function beside the reading (below) spells an account only from a kind a surface gives:
  - a type the service records for the account;
  - the suffix in the login;
  - the form of an entry pkit holds, which is written in the spelling (below);
  - gh's mark of an author the service does not record as a user, its `app/` prefix and its bot flag, which the function reads as a bot's. gh sets it on every such author, an imported placeholder account among them, which then reads as a bot's and is granted nothing a bot's would not be.

  A surface that gives a bare login and nothing more leaves the kind unknown, and the function gives that login no spelling. gh's JSON for a comment's author is such a surface, and for an app's account it gives the bare name (Context). So a reader that compares an account reads its kind from a surface that gives it, such as the REST interface's record of a comment's author, with its type.
- **Which way a comparison fails.** A comparison either grants something or tells two authorities apart, and each fails closed where a kind is unknown:
  - **To grant,** an account must match an entry: as a member, as the registered remote reviewer, or as a claim's author against its assignee. Two accounts match only where both kinds are known and their spellings are equal. An account of unknown kind matches nothing.
  - **To tell apart,** two accounts must differ for something to pass: the actor and an authorisation's producer, or a reviewer and the pull request's author. Two accounts are one authority where their spellings are equal. Where either's kind is unknown, they are one authority where their logins are equal once the suffix and the prefix are set aside. So a missing kind never reads as another authority.
  - **An app that took its owner's name** is another authority than its owner wherever both kinds are known, as the service records them.
- **Case.** The service looks an account's name up without regard to case, so every comparison ignores case, the engine's among them (point 5). A spelling is written down in the case the service answered.
- **One function** beside the reading puts accounts named by any surface into the one spelling, many in one call, and compares two accounts either way. Every comparison of two accounts in pkit goes through it, save the engine's, whose two sides the binding spells with it (point 5). Every account pkit writes down is written in the spelling. The backbone's code calls the function. A capability's scripts reach it through the backbone's reading command, and keep no copy of it (ADR-057 point 2).
- **Requests.** A request to the service that names an account names it in the form that request takes, made from the login the service answered and the account's kind. The service's search, for one, names an app's account `app/<name>`. A stored spelling of a bot's account is never turned back into a login, since the spelling may have added the suffix.
- **Stored accounts.** An entry pkit holds is in the spelling, so its kind is read from its form: a bare entry names an account that is no bot's.
  - **Users' entries.** A user's login is already in this spelling, and the member list's schema describes a member's login as the value the service answers for that member, so no entry that names a user changes.
  - **A service's account,** as a member or as the remote reviewer, is written in this spelling, an App's as `name[bot]`. One written in gh's form, `app/name`, reads as `name[bot]`, and needs no rewrite.
  - **An App's bare login,** already written, reads as no bot's, so it does not match the App's account. What the App's account writes stops counting, and nothing counts that did not before. No migration rewrites such an entry, since a bare login cannot be told from a user's without asking the service.
  - **The refusal names it instead.** Where a bot's account matches no entry, but an entry holds its login bare, the function says so. A reader that refuses for want of a match names that entry, and the spelling that would name the bot.

### 4. An answer lasts one run

- **Within a run,** the reading asks at most once and reuses its answer. A capability's command that reaches it by command keeps the answer for its own run.
- **Handed on.** Where a run starts a command that takes the account as an argument, such as the engine's move, which takes it as the actor, it hands the account on. The command it starts takes the account as its caller's word.
- **Across runs, nothing is kept.** An answer kept from an earlier run, even for the same credential, is no answer of the service's. So each run that needs the account asks.

### 5. The engine reads no account, and takes no placeholder

- **The actor is the caller's.** The actor a gate judges is the authority the move is made by, in the terms of the binding whose gate judges it (COR-033 P4). The engine takes it from its caller and from nowhere else: it asks no service, and takes no default. An actor named blank names none.
- **One rule in every command.** Every engine command that judges a gate, such as the status view, the check whether a move may be made and the move, judges it for the actor named, or for none. So a precheck and its move judge one actor.
- **What it compares.** The engine compares the actor with the producer the binding's predicate reports, without regard to case, and confirms neither. To the engine, under any binding, two names that differ only in case are one authority, which can only refuse more.
- **With no actor named:**
  - **A gate that must confirm its authorisation came from another authority is not judged,** since nothing can confirm it. The engine still runs its predicate and reports what it answered, the producer included, and a predicate it cannot evaluate stays indeterminate, with its reason.
  - **A gate not judged refuses the move.** The refusal says that no actor was named, and that a caller names the authority the move is made by, in its binding's terms: never one it acts for, and never a placeholder.
  - **The missing actor makes no wait.** For a wait, the engine reads a gate it did not judge as one that may be open, so it neither shows nor journals a wait that only the missing actor made (COR-034).
  - **A move none of whose gates compares the actor goes on.** Its journal entry records the actor as empty, the form a blank actor takes, which names none, and the status view shows it as made by no named actor.
- **No placeholder.** No fixed value stands for an actor no caller named.
- **A binding whose authorities are accounts on the hosting service,** as project-management's are, names as its actor the account the move is made as: the account its credential acts as, from the reading, never a person the caller acts for.
  - **Why an account.** That is this record's reading of P4 for such a binding: its predicates report each producer as an account, so the actor compared with them is an account too. A person and an agent working under one credential are then one actor.
  - **Under every credential the reading names,** whatever value a capability lets stand beside that account elsewhere, such as at its membership gate. Which other value may stand for it where the reading is unresolved is the capability's (point 8).
  - **One spelling on both sides.** The binding's wrapper names the actor, and its predicates report each producer, in the one spelling, so the engine's comparison compares like with like. A predicate that cannot learn its producer's kind names no producer, and the engine refuses, as for any authorisation that names none (point 3).
  - **By hand.** A person who names the actor by hand names it as the binding's reference says. The engine takes their word, as it takes every caller's, so a misspelt actor is a false one (the process area's reference, "Gate-checkability").
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
- **What this binds:** pkit's own code and the capabilities project-kit ships. project-kit's own repository scripts are neither, such as the one that keeps the friction report's tracking issue, which lists by one fixed author.
- **What it leaves free.** The reading command and its document are part of pkit's public surface, so a capability another project writes may use them. Nothing here binds such a capability to them, since an architecture record reaches no other project ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)). No such capability is known to need the acting account, so no core record is proposed for one.

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

**Why the binding spells both sides, and the engine ignores only case.** The engine's comparison is the check COR-033's Rationale calls load-bearing. A producer reported in another spelling than the actor's makes an actor's own merge read as another authority's. Respelling in the engine would carry one service's spellings into a content-free engine. Ignoring case carries none: it reads no form, and can only refuse more. The binding's wrapper and its predicates both reach the backbone's function, so the two arrive in one spelling, and the process area's reference states this as part of the predicate's contract. A person who names the actor by hand is taken at their word, as every caller is, so the reference also says where a binding's actors come from.

**Why the service's REST spelling.** It is the login the service's REST interface gives an app's account, and carries the kind in its form, so no field is added, and the member lists hold users' logins in it already. gh's listing by author took it where gh's own form matched nothing, as project-kit's own friction workflow found (Context). gh's form is what the service's search takes for an app's account, but the service gives no account that login, so a request that searches makes the form from the spelling (point 3). A bare login would drop the kind, and an app may take its owner's name, so the app's account would compare equal to its owner's. The suffix is added where a bot's login lacks it, so the spelling carries the kind for every bot, an app's or another.

**Why a login with no kind is never a user's.** Read as a user's, a bare login turns missing information into an answer:

- **Where two accounts must differ,** it reads an app's comment on its own pull request as another authority's. gh writes the pull request's author as the app's, and the comment's author by the app's bare name (Context).
- **Where an account must match,** a bare entry and a bare author agree whichever account each means, an app that took its owner's name among them.

So a comparison that cannot learn a kind takes the side that fails closed: it grants nothing, and it tells no two authorities apart. An app and its owner are still two authorities where both kinds are known. The service records them apart, and the owner stands behind an app whatever it is named, so a rule that joined them only where the names coincide would refuse those owners alone.

**Why comparisons ignore case.** The service looks an account's name up without regard to case, so two spellings that differ only in case name one account, and no two accounts' names differ only in case. So ignoring case grants nothing to another account. Where two accounts must differ, unequal reads as another authority, so a comparison that heeded case would fail open on a login typed in another case. The refusal of a move with no actor now sends people to name one, so the engine meets such logins.

**Why an answer lasts one run.** An answer kept across runs needs a key for the credential, which means reading the secret or trusting the issuing tool's record (point 2). It can also go stale: a login renamed, and perhaps claimed by another account, or a setup that swaps one credential for another, would act on the earlier account. What it would save is a request for each run that needs the account. That is more than one a command: a command that starts others, as a landing starts a merge and a move, costs one in each unless it hands the account on (point 4), and an installation's tokens share one limit on requests across every session that holds them. It buys no work offline, since every reader reads or writes the service in the run that asks.

**Why no placeholder actor.** A placeholder equals no account, so every cross-authority gate passes under it. Refusing such a gate costs its caller a named actor. Under a credential that never resolves, it costs more. project-management makes a move first and journals it after, so each of its moves through such a gate is left out of the journal, with a warning. That is the honest record of a move whose gate nobody judged. The capability surfaces a move that failed to journal rather than drop it, and where labels carry the state, its drift check reports the gap (project-management:DEC-049 points 1 and 3). A move none of whose gates compares the actor loses nothing by an unknown actor, so it goes on, and the journal says so plainly.

**Why a gate not judged makes no wait.** A wait tells a person what a subject waits on (COR-034). A gate read as shut for want of an actor would show a wait nobody is in, and a move would journal its start, then its end at the next move that names an actor. Reading the gate as one that may be open, for a wait alone, loosens no guard, since a move through it still refuses. The predicate still runs, so a person who checks a gate without naming an actor still sees what it answers.

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
- **The engine compares exactly, as it does today.** Rejected: a name typed in another case reads as another authority, which fails open, and the refusal of a move with no actor sends people to name one.
- **A move with no actor named is journaled, its gate marked as not judged,** in place of refusing it. Not taken. The engine answers the move check and the move alike (point 5), and a wrapper that checks before it writes, as the process area's reference orders it, reads that answer as leave to write. A "not judged" answer would be a yes there, which takes the caller's word for the gate, as P4 forbids, or a no, which is this record's refusal. And an entry for a move the engine refused is no entry for a move it executes (COR-033 P7). It is weighed again if a credential that never resolves proves the usual one in a project that keeps a journal.
- **Accounts compared by kind and numeric id,** with logins kept for display and the member lists. Not taken:
  - the member lists and the registered reviewer hold logins, and a predicate names its producer by one string, so both forms would change and every entry would migrate;
  - the kind an id would settle is settled by reading it from a surface that gives it (point 3), and the surface the gate's predicate reads gives no id for a bot's account, since gh writes one as `app/<name>` with none (Context);
  - the risk only an id closes is a login renamed and then claimed by another account, which reaches only an entry kept past the rename.

  The document gives the id, so a record that comes to need it compares by it without a new version of the document (ADR-061 point 7).
- **A spelling with the kind as a field of its own.** Rejected: every member list and every stored account would need a migration, and the service's login already carries the kind.
- **gh's spelling, with its `app/` prefix.** Rejected: the service gives no account that login, gh's own listing by author matched nothing in it (Context), and the member list's schema already describes the login the service answers. The service's search takes it, so a request that searches makes it from the spelling (point 3).
- **The bare login.** Rejected: an app may take its owner's name, so its account would compare equal to its owner's and pass as the owner.
- **A login with no kind read as a user's.** Rejected: where two accounts must differ, it reads an app's comment on its own pull request as another authority's, and where one must match, it lets a bare entry match whichever account a bare author means (Rationale).
- **Comparisons by bare name wherever two accounts must differ,** so that an app that took its owner's name is one authority with its owner. Not taken: the service records the two apart, and the owner stands behind an app whatever it is named, so the rule would refuse only the owners whose apps share their name. A missing kind is read so (point 3), since it could be either.
- **Bare entries rewritten by a migration.** Not taken: a bare login cannot be told from a user's without asking the service, and a migration asks nothing. The refusal names the entry instead (point 3).
- **Comparisons that heed case.** Rejected: two spellings of one account would read as two authorities.
- **The engine refuses every move with no actor named.** Rejected: a move whose gates compare no actor would stop for nothing.
- **`pkit report` posts under an unresolved identity once the person confirms,** as it does today. Rejected: the confirmation exists to name the posting account, and here it cannot (point 6).
- **A reading neutral to the hosting service now.** Rejected: with one service, the neutral form is GitHub's renamed (COR-007; ADR-061 point 3).

## Implications

- **Edits, once a person accepts this record,** made in this change. Each is a refinement in place, and none overturns a passage. Each takes a forward pointer to this record: `(refinement per [pkit:ADR-094])` in a capability's record, and the same pointer as a relative link in an architecture record.
  - **[ADR-047](ADR-047-report-cross-repo-write.md) point 2,** which the architect refines. The confirmation names the reading's account as the posting account, said to be a bot's where it is one. Under an unresolved identity, `pkit report` posts nothing through the service, says why, and keeps the payload as a draft. A narrowing: the point's first bullet confirms "under your gh identity" and posts, and its refinement from [project-kit#662](https://github.com/aleskalfas/project-kit/issues/662) has the confirmation name the posting login, so where no login can be named the point leaves no outcome but to confirm and post. This takes that case out of "confirm, then post" and into the draft, and the never-silent gesture stands. The edit is folded into the point's body, and the point's two dated refinement blocks are folded in with it as plain statements, with no date, changing nothing they decide. Their issue numbers stay, as evidence.
  - **[ADR-036](ADR-036-open-region-engine-strategy.md) point 4, its second bullet,** which the architect refines. The engine passes the gate where the authorisation exists, names its producer, an actor is named, and the producer differs from the actor without regard to case. With no actor named, the gate is not judged, and refuses the move. A completion and a narrowing: read as written, the bullet's formula passes with no actor named, a case it never met while the engine always had a default, and this supplies that case's outcome; comparing without regard to case passes fewer moves. A fact correction is folded in with it: a producer is named only by a string with something in it, as the engine has required since [project-kit#2542](https://github.com/aleskalfas/project-kit/issues/2542). The point's decision, that the conjunction lives in the binding's wrapper and the cross-authority half stays a gate the engine computes, stands.
  - **[project-management:DEC-021](../../../.pkit/capabilities/project-management/decisions/DEC-021-team-membership-gate.md), "Identity resolution", item 1,** which the change's author refines. The service's login is the account the hosting service answers the credential acts as, read through the backbone's reading of the acting account once in a run and kept from no earlier run. It is matched against a member's login in the one spelling, without regard to case. A completion: item 1 names a request for the login, a mechanism this replaces, and item 1 keeps its place among the three surfaces. DEC-021 defers identity resolution's edge cases, and caching, to its implementation ("Identity resolution", its last paragraph, and "Why mechanism details are deferred"), and this settles two of them for that read: the spelling a login is matched in, and that no answer is cached across runs. The edit touches none of items 2 and 3, the paragraph on matching, and the paragraph on what is deferred, which stands for every other read.
  - **[project-management:DEC-028](../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md), "Two paths, two registration lists", "Path 1: Remote agent", step 3 of "Gate-checker algorithm", and the "Sub-decisions index" row "Remote-path identity check",** which the change's author refines. A registered remote reviewer's login is the agent's account in the one spelling: an App's is written `<name>[bot]`, and a machine user's by its login. A verdict's author is read with its kind, from a surface that gives it. It matches the registered account as point 3 grants, and it is told apart from the pull request's author as point 3 tells two authorities apart. The registration list's example and its comment say so. A completion: DEC-028 registers an account it means for a bot, an App or a service account, and fixes no spelling or kind for it. No migration rewrites an entry, for the reason point 3 gives.
- **Records not edited.**
  - **[ADR-041](ADR-041-instance-ownership-substrate-contract.md) and ADR-071 point 3** compare a comment's author with an assignee or a member. Point 3 here governs those comparisons, and neither record states a spelling of its own.
  - **DEC-021's Implications and DEC-022's "Authority"** admit a service's account as a member, and neither fixes or shows a spelling for it. Point 3 here governs how such an entry is spelled and compared.
  - **DEC-021's item 2 and its paragraph on what is deferred** still read true beside the edited item 1. The reading asks the service through `gh` (point 7), so "when `gh` is unavailable" still names a case in which item 1 has no answer, and which other cases let git's email stand is the capability's (point 8). The deferred paragraph's caching and edge cases stand for every read but item 1's, and item 1's refinement names the two it settles.
  - **[ADR-020](ADR-020-process-engine-code-home.md) and ADR-061** stand. This record places one more read of the hosting service beside the acts ADR-061 placed, and keeps it out of the engine ADR-020 placed.
  - **COR-033** is realised, not changed. P4 is held more strictly. P7's "who moved the subject" is the actor the caller names, so an entry records it as empty where the caller names none. PRJ-008 stands.
  - **COR-034** stands: a wait is still derived from the gates' verdicts, and a gate not judged gives none.
  - **project-management:DEC-049** stands. Its journal surfaces a move that fails to journal, which the warning keeps. Its drift check reads such a gap as an out-of-band change or a governed move that failed to journal. Its entries record the actor named, empty where none is.
- **The work,** once this record is accepted:
  - **The reading:** first the measurement that chooses its request (point 1), then the reading and the one function, with the reading command and its document, and tests that fake `gh`. Accepting this record waits on no measurement, since the reading holds whatever it shows (point 2).
  - **The engine:**
    - its status view, move check and move take no default actor;
    - a cross-authority gate with no actor named is not judged: its predicate still runs and its producer is reported, it refuses a move, and it makes no wait;
    - the actor and the producer are compared without regard to case;
    - a move that names no actor is journaled with an empty actor, which the status view shows as made by no named actor.

    The tests that pin the placeholder change with it. The engine's page and the process area's reference state the actor's contract (point 5), the predicate's duty to report a producer as its binding names actors, and the walkthrough's advice on naming the actor.
  - **`pkit report`:** its confirmation, its draft under an unresolved identity, and its listing by the reading's account.
  - **project-management:**
    - its three readers and the membership gate's first surface move onto the reading command;
    - its move names its actor from the reading, as point 5 has it, and none where the reading is unresolved, unless a record of its own lets another value stand for that account;
    - its gate's predicate reports the merging account in the one spelling;
    - its readers that compare accounts read each author's kind from a surface that gives it. gh's JSON for a comment's author gives none, and the REST interface's record of the comment does. So the remote reviewer's match moves off gh's comment JSON in the change that moves it onto the function, or no verdict of its counts;
    - its refusals name a bare entry that would match a bot's account with the suffix (point 3);
    - the schemas that describe a login describe the one spelling.

    The membership gate keeps the order its code has today, the variable in place of the reading's login wherever it is set, until a record of the capability's changes it, such as the one on [project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175). Where the variable so stands, one run's membership identity, and the actor its audit comment names, can be another account than its journal's actor. What its comments name is the capability's.
  - **The CLI reference,** where it describes the engine's actor, the reading command, and the account `pkit report` posts as.

  None of it changes the form of anything a project holds, so it ships no migration (point 3). The journal's empty actor is a string, as its schema asks. Its surface changes are each declared by a changeset of the component they change, of a segment a person judges. In the backbone, they are the engine's lost default, its comparison without regard to case, and `pkit report`'s refusal under an unresolved identity. In project-management, they are the actor its move names, and the remote reviewer's match in one spelling. What they cost, for whoever judges the segments:
  - **Callers that name no actor.** A direct caller of the engine's status view or move check, a person running a move by hand, and a capability another project writes whose code moves a subject with no actor named, each names an actor or sees cross-authority gates refuse.
  - **Moves to Done under a credential that never resolves,** such as an installation's token if no request answers it. Each of project-management's moves through the gate on Done is left out of the journal, with a warning. Where labels carry the state, the drift check reports the gap. Where the board or a derivation carries it, the check is skipped, and the warning is the only trace. One the acting account merged is refused today under a credential that resolves, since the gate refuses an actor's own merge ([project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171)), so the loss that matters is a move to Done after another account merged.
  - **Workflows that set the variable.** Their moves are journaled today under the variable's value. Under a credential the reading names, the actor is that credential's account, so a merge that account made is refused, as a person's own merge is. Under one it cannot name, the move names no actor, unless a record of the capability's lets the variable stand for its account.
  - **An App registered by its bare login,** as a member or as the remote reviewer, stops matching its own account until its entry is respelled, and the refusal names the entry.
- **Left out, for records of their own:**
  - what a capability's commands do with an unresolved identity or a bot's account, which is project-management's to decide, in a record of its own ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164));
  - git's email and the variable beside a person's login, at the membership gate ([project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175)). That record does not reach the actor the engine's gate compares, which point 5 settles;
  - the person an agent works for, which names no account the credential acts as, so it is no reading of the acting account. The record on who may authorise in a turn a chat started (ADR-091, Implications) may give the backbone a reading of it;
  - whether the predicate of project-management's gate on the move to Done reports the approval rather than the merge ([project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171));
  - how far the reading holds for another hosting service (point 7, [project-kit#1222](https://github.com/aleskalfas/project-kit/issues/1222)).
- **Stands on** COR-007, COR-010, COR-025, COR-033, COR-034, PRJ-008, ADR-020, ADR-036, ADR-041, ADR-047, ADR-050, ADR-057, ADR-061, ADR-071, ADR-091, and project-management's DEC-021, DEC-022, DEC-026, DEC-028 and DEC-049, all accepted.
