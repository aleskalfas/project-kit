---
id: DEC-078
title: Each act has one actor, the account its credential acts as, and no comment names another
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** each act the commands record, such as a move or a merge by bypass, has one actor: the account the hosting service says the credential acts as. The engine judges that actor on a move, and the journal records it. No comment the commands post names an authoriser beside the account that posts it, or carries an email. Where the service gives no login for the account, the act has no actor: the commands make the move, hand it to no engine and report it as a gap in the journal, and refuse nothing for want of a name. This holds in every project, under every credential.

## Context

**The terms.**

- **The account the credential acts as** is the one the hosting service answers for the credential: a user's account, or an app's account with its login ([project-management:DEC-073-reads-take-no-gate] point 2).
- **The commands know no acting account** where the service gives no login for that account: where it refuses the request for the account because the credential is an integration's, as it refuses an App installation's token, and where it gives no answer at all. These are the outcomes of DEC-073 point 2 that name no account.

**What the records say.**

- **The authoriser a comment names.** A comment names who authorised an act only where they differ from the account that posted it, and the actor is taken for the authoriser ([project-management:DEC-049-audit-journal-model] point 4). [project-management:DEC-052-comment-house-style] keeps the authoriser where another account than the authoriser posts the comment, and its boundary rule keeps a comment from existing to restate its author and post time.
- **The template.** The audit-comment template names the authoriser by name and email, `Bypassed by <name> <<email>>: <reason>` ([project-management:DEC-014-validation-severity-model]), and the comment of an override of a reviewer records whoever overrode by name and email ([project-management:DEC-050-per-reviewer-override] point 4).
- **The audit record.** Every audit record has an actor, "login + display name; email where the source has it", its hidden stamp encodes the record's fields, the default render shows an `actor · timestamp` metadata line, and a project may override the render ([project-management:DEC-044-audit-log-facility] points 1 to 4).
- **The actor under a user's credential.** Where the service answers that a credential acts as a user's account, that account is every reader's identity, the actor a move hands the engine among them ([project-management:DEC-021-team-membership-gate], "Why every reader of the invoker's identity takes that login"). Where it does not, DEC-021 leaves the other readers open.
- **The engine's gate.** A gate's authorisation comes from another authority than the actor it gates ([pkit:COR-033] P4). The engine's cross-authority gate compares the actor a command hands it with the account this capability's predicate reports as having merged the pull request.

**What happens today.**

- **The comments.** The commands fill the template's name with the identity the membership gate checks, and its email with git's configured email. Under a user's credential, the name is the posting account's own login, and the email is whatever git's configuration on the machine names.
- **The engine is told after the move.** A command makes its change on the tracker and then hands the move to the engine, whose refusal never fails the move: it leaves a gap in the journal, which the command reports as a move the engine did not record. A move the command does not hand the engine, such as a close the workflow declares no transition for, is reported the same way. The transition from Review to Done has a gate on an authorisation artifact, the merge the landing command makes itself.
- **Where the commands resolve no login,** they hand the engine no actor. The engine asks the service itself, and where the service refuses, as it refuses an installation's token, takes a placeholder name of its own. Its gate passes wherever the account that merged does not bear that name, so an agent's own merge passes it, and the journal records the placeholder as the move's actor.

## Decision

**Under every credential, each act the commands record has one actor, the account the hosting service answers the credential acts as, and no comment names an authoriser beside the account that posts it; where the commands know no acting account, an act names no actor and its move is handed to no engine.**

### 1. Each act's actor is the account the credential acts as

- **One actor.** Each act the commands record, a move or another such as a merge by bypass, a refusal overridden by `--force`, an override of a reviewer or a head named at a terminal, has one actor: the account the service answers the credential acts as, a user's account or an app's.
- **Nothing beside it is the actor:** not `PM_INVOKER_LOGIN`, git's configured email or the person the agent works for, wherever they stand at the membership gate.
- **For a move,** the commands hand that account to the engine's cross-authority gate as the actor, and this capability's predicate for the gate reports the account that merged in the same spelling. The journal records it, where the project keeps one.

Under a user's credential, DEC-021 already takes that account for every reader of the invoker's identity, so this point adds there only what point 2 does.

### 2. No comment names an authoriser beside its poster, or carries an email

- **No authoriser beside the poster.** An audit comment's authoriser is its act's actor, kept only where the poster is someone else (DEC-049 point 4). The account the credential acts as posts the comment, so no comment names an authoriser beside it. A comment that names who gave a word, or who named a head, names them as the account that posts it.
- **No email,** in a comment's visible text or in its hidden stamp. An audit record's actor is its login and display name.
- **A reason the caller gives** may report a person's word, and stays the caller's report.
- **The default render** shows no actor on its metadata line, since the account that posts a comment is its actor, and the service shows that account beside the comment. A project's own template stays its own (DEC-044 point 3).

### 3. Where the commands know no acting account, an act names no actor

- **An empty actor.** The audit record of such an act holds no login, display name or email, and its comment names no authoriser.
- **No move handed to the engine.** The command makes the move on the tracker as it would, hands it to no engine, and reports it as a move the engine did not record, as it reports one the engine refused. Where the project keeps a journal, each such move is a gap there, which the drift check shows (DEC-049 point 3).
- **Nothing refused for want of an actor.** A merge by bypass, an authorisation to merge given up front, the move to Done after a merge, and the record of a move to Done after a merge already made each pass as they do elsewhere, and each move among them is reported unrecorded like any other.

## Rationale

**Why the actor is the account the credential acts as.** COR-033 P4 asks that an authorisation come from another authority than the actor. The predicate reports who merged the pull request as an account, so the comparison means something only against an account, and the account that makes the move is the one its credential acts as. A name in its place, from the variable or git's email, makes an agent's own merge read as another authority's. Naming the account keeps the journal in step with the service's own record of who wrote each change, and gives the journal and the comments one actor, as DEC-049 has the comments project the journal (points 1 and 2).

**Why no authoriser beside the poster, under every credential.** Under a user's credential, the template's name is the posting account's own login, as DEC-021 takes it: a restatement, which DEC-049 point 4 and DEC-052's boundary rule already leave off a comment. The email is a setting of the machine, made by its user or its setup, which may name anyone (DEC-021, "Why a user's login the hosting service answers stands alone"), so beside the posting account it may name another person, the mixed stamp DEC-021 names as a cost. Under a credential that names no user's account, any name beside the poster comes from the caller's word, and reads as the authoriser of an act the service records as the poster's. Dropping both loses nothing true, and keeps whether a comment names someone beside its poster from turning on which credential a setup holds. An email kept only in the hidden stamp is posted all the same, and whoever reads the comment's source reads it.

**Why hand the engine no move where no actor is known.** Handed no actor, the engine takes one of its own, which reads as an account, passes its gate on any merge, the agent's own among them, and enters the journal under a name the commands never knew (Context). Reported unrecorded, the move leaves what the gate's refusal leaves on an agent's own merge, a gap in the journal, and the gap is surfaced, as DEC-049 point 1 asks of a move that fails to journal. Nothing is refused, so what passes on the caller's word, such as a bypass or an authorisation given up front, passes as it does elsewhere. A refusal would go further than the gate it stood in for, which refuses only the entry, never the move, and where the service gives no login, no second run would mend it.

**What it costs.** Every move a session makes where the commands know no acting account is a gap in the journal, which the drift check flags. In a project that keeps a journal, the journal then misses that session's work, and the tracker's timeline, with the service's record of who wrote each change, is its only trail.

**Why an empty actor, and not a placeholder.** A placeholder reads as an account, can match one of that name, and records a name the commands never knew. An empty actor grants nothing, and the service records which account posted each comment.

**Which edits overturn, and which refine.** A passage is overturned in part where it states, for the case this record decides, an outcome this record contradicts: a named provision, an explicit no, or a form it gives every comment or record of a kind. It is completed in place where it leaves open what this record supplies, and a fact is corrected where only a fact stated beside its rule reads false.

### Alternatives considered

- **Each act's actor only under a credential that names no user's account,** leaving the name and the email the template gives a comment under a user's credential. The case: no comment changes in a project that runs no agent under such a credential. Rejected: the name there restates the poster, the email may name another person, and whether a comment names someone beside its poster would turn on the setup's credential.
- **Keep the email in the hidden stamp only.** The case: tooling keeps a field DEC-044 point 1 gives, and no reader of the rendered comment sees it. Rejected: the stamp is posted with the comment, and names the same setting of the machine.
- **Let the engine take its own actor where the commands know none.** The case: nothing for the commands to decide. Rejected: the engine's own choice reads as an account and passes its gate on any merge (Context).
- **A placeholder in place of an empty actor,** such as `unknown`. Rejected: it reads as an account (Rationale).
- **Refuse a move whose transition's gate needs an actor, where the commands know none,** such as the move to Done. The case: no move goes past the gate. Rejected: the gate refuses only the journal entry, never the move, so the refusal would go further than the gate, stop a bypass, an authorisation given up front and a merge a person approved, and no second run would mend it where the service gives no login.
- **Refuse every act that leaves an audit record where the commands know no acting account,** so that every record keeps an actor. Rejected: it would stop every bypass and every audited override under a credential whose login the service does not give, and wherever a lookup fails, for want of a name the commands never knew.
- **Leave the move with no actor to a record of the backbone's,** which decides what the engine takes where a command hands it none, before the commands change. Not taken: what the commands hand the engine is this capability's to decide, and handing none needs nothing of the backbone. A record of the backbone's may still let the engine take such a move.

## Implications

- **What changes in every project.**
  - Each audit comment the commands render loses the name and the email the template gives its authoriser, and carries no email in its stamp. The default render's metadata line shows no actor.
  - A run under a person's own credential that the service gives no answer for, where a command still acts, hands the engine none of its moves, and its audit records' actor is empty rather than taken from git's configured email.
  - Under a user's credential with `PM_INVOKER_LOGIN` set to another account, the commands already hand the engine, record and name the account the credential acts as (DEC-021, "Every reader of the invoker's identity"), so nothing else changes there.
- **Overturned in part.** Each record below stays accepted, and its overturned words stay as they stood. Its top line, its first paragraph, reads *Partially superseded by [project-management:DEC-078-one-actor-per-act]* and says in the line itself:
  - **DEC-014,** above "Context": "Under every credential, a bypass's audit comment names no authoriser beside the account that posts it, by name or by email. Overturned: the audit-comment template's `by <name> <<email>>`, in '`bypassable-with-audit`' and in the Implications' bullet that names the template the canonical form. The rest stands."
  - **DEC-044,** above "In plain terms": "Under every credential, an audit record's actor carries no email, and where the commands know no acting account an act's actor is empty. Overturned: point 1's 'email where the source has it', and its 'login + display name' for an act that names no actor. The rest stands."
  - **DEC-050,** above its quoted summary: "Under every credential, the audit comment of an override of a reviewer names nobody beside the account that posts it. Overturned: point 4's '(name + email)', by which the comment records who overrode. The rest stands."
  - **DEC-052,** above its quoted summary: "The authoriser the commands know is the account that posts the comment, so an override comment names none beside it. Overturned: the Implications' parenthetical that keeps the authoriser on the bot-authored path. The rest stands."
- **Completed in place,** each with the pointer `(refinement per [project-management:DEC-078-one-actor-per-act])`, citing this record's points as DEC-078 point N:
  - **DEC-044 point 1,** a sentence of its own after its field list: for an act that names an actor, the record's actor is the act's actor, the account the credential acts as (DEC-078 point 1), with its display name where the reading of that account gives one, and otherwise its login.
  - **DEC-044 point 4,** its metadata line: the default render shows the timestamp and no actor, since a comment's actor is the account that posts it (DEC-078 point 2). A project's own template stays its own.
- **Facts corrected in place,** with no pointer:
  - **DEC-021's Implications, "The email beside the login on an audit comment":** its head reads "No email on an audit comment", and it says that no audit comment carries an email or names an authoriser beside the account that posts it (DEC-078 point 2), so git's configuration on the machine puts no person's email beside that account.
  - **DEC-047 point 5:** its parenthetical names the bypass's line of the audit-comment template, as the validation-severity schema holds it, in place of its quotation of DEC-014's `Bypassed by` line, so the freeform comment verb refuses a first line in that line's form.
- **Left out, for records of their own:**
  - **The acting account where the backbone needs it:** the account the backbone's reporting command posts as, how the engine takes and compares the actor the commands hand it, and whether it may take a move a command hands it no actor for.
  - **What the gate on the move to Done reads as its authorisation.** The predicate reports who merged, so after an agent merges its own approved pull request the gate refuses the entry, as it does for a person's own merge, and the move is a gap in the journal. Whether the predicate should report the approval rather than the merge is a question under every credential.
