---
id: DEC-078
title: Each act has one actor, the account its credential acts as, and no comment names another
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** each act the commands record, such as a move or a merge by bypass, has one actor: the account the hosting service says the credential acts as. The engine judges that actor on a move, and the journal records it. No comment the commands post names an authoriser beside the account that posts it, or carries an email. Where the service gives no login for the account, the act has no actor, and the commands refuse nothing for want of a name. They make the move, hand it to the engine with no actor where the engine takes none of its own, hand it none where the engine would take one, and report each move the engine does not record as a gap in the journal. This holds in every project, under every credential.

## Context

**The terms.**

- **The account the credential acts as** is the one the hosting service answers for the credential: a user's account, or an account that is no user's, given with its login ([project-management:DEC-073-reads-take-no-gate] point 2).
- **The commands know no acting account** where they learn from the service no login for the account the credential acts as, whatever the service answers, or where it answers nothing.

**What the records say.**

- **The authoriser a comment names.** A comment names who authorised an act only where they differ from the account that posted it, and the actor is taken for the authoriser ([project-management:DEC-049-audit-journal-model] point 4). [project-management:DEC-052-comment-house-style] keeps the authoriser where another account than the authoriser posts the comment, and its boundary rule keeps a comment from existing to restate its author and post time.
- **The template.** The audit-comment template names the authoriser by name and email, `Bypassed by <name> <<email>>: <reason>` ([project-management:DEC-014-validation-severity-model]), and the comment of an override of a reviewer records whoever overrode by name and email ([project-management:DEC-050-per-reviewer-override] point 4).
- **The audit record.** Every audit record has an actor, "login + display name; email where the source has it", its hidden stamp encodes the record's fields, the default render shows an `actor · timestamp` metadata line, and a project may override the render. The record leaves the default's exact aesthetic unfrozen ([project-management:DEC-044-audit-log-facility] points 1 to 4).
- **Comments that record a person's word.** The override of a refusal by `--force` leaves a comment naming who gave it ([project-management:DEC-055-pr-lists-answers] point 3), and a head a person names at a terminal leaves one naming the commit, the command and who named it ([project-management:DEC-067-heads-that-start-programs] point 4).
- **The actor under a user's credential.** Where the service answers that a credential acts as a user's account, that account is every reader's identity, the actor a move hands the engine among them ([project-management:DEC-021-team-membership-gate], "Why every reader of the invoker's identity takes that login"). Where it does not, DEC-021 leaves the other readers open.
- **The engine's gate.** A gate's authorisation comes from another authority than the actor it gates ([pkit:COR-033] P4). The engine's cross-authority gate compares the actor a command hands it with the account this capability's predicate reports as having merged the pull request.
- **The journal.** `move-issue` and its wrappers delegate the journal to the engine ([project-management:DEC-033-rebind-issue-lifecycle-onto-process-substrate] D5). Where a project keeps one, it holds one entry for each governed move, with its actor, and a move that fails to journal is surfaced, not dropped (DEC-049 point 1). The drift check flags a state change with no entry where labels carry the state, and is skipped where the board or a derivation carries it (DEC-049 point 3).

**What happens today.**

- **The comments.** The commands fill the template's name with the identity the membership gate checks, and its email with git's configured email. Under a user's credential, the name is the posting account's own login, and the email is whatever git's configuration on the machine names.
- **The engine is told after the move.** A command makes its change on the tracker and then hands the move to the engine, whose refusal never fails the move: it leaves a gap in the journal, which the command reports as a move the engine did not record. A move the command does not hand the engine, such as a close the workflow declares no transition for, is reported the same way. The transition from Review to Done has a gate on an authorisation artifact, the merge the landing command makes itself.
- **Where the commands resolve no login,** they hand the engine no actor. The engine asks the service itself, and where the service refuses, as it refuses an installation's token, takes a placeholder name of its own. Its gate passes wherever the account that merged does not bear that name, so an agent's own merge passes it, and the journal records the placeholder as the move's actor.
- **The key of an audit comment.** A retry of an audited move finds the comment it already posted by a key, and the same move made again later posts its own. Where a journal is kept, the key tells the two apart by the journal's count of entries.

## Decision

**Under every credential, each act the commands record has one actor, the account its credential acts as, and no comment names an authoriser beside its poster; where the commands know no acting account, an act has none, and its move reaches the engine only where the engine takes no actor of its own.**

### 1. Each act's actor is the account the credential acts as

- **One actor.** Each act the commands record, a move or another such as a merge by bypass, a refusal overridden by `--force`, an override of a reviewer or a head named at a terminal, has one actor: the account the service answers the credential acts as.
- **Nothing beside it is the actor:** not `PM_INVOKER_LOGIN`, git's configured email or the person the agent works for, wherever they stand at the membership gate.
- **For a move,** the commands hand that account to the engine's cross-authority gate as the actor, which the gate compares with the account this capability's predicate reports as having merged. The journal records it, where the project keeps one.

Under a user's credential, DEC-021 takes that account for every reader of the invoker's identity, so this point adds there only what point 2 does.

### 2. No comment names an authoriser beside its poster, or carries an email

- **No authoriser beside the poster.** An audit comment's authoriser is its act's actor, kept only where the poster is someone else (DEC-049 point 4). The account the credential acts as posts the comment, so no comment names an authoriser beside it.
- **Who gave a word.** A comment that records who gave `--force` (DEC-055 point 3), or who named a head at a terminal (DEC-067 point 4), names them as the account that posts it, the act's actor, and names nobody beside it.
- **No email,** in a comment's visible text or in its hidden stamp. An audit record's actor is the account's login.
- **A reason the caller gives** may report a person's word, and stays the caller's report.
- **The default render** shows no actor on its metadata line, since the account that posts a comment is its actor, and the service shows that account beside the comment. A project's own template stays its own (DEC-044 point 3).

### 3. Where the commands know no acting account, an act names no actor

- **An empty actor.** The audit record of such an act holds no login or email, and its comment names no authoriser.
- **The move, with no actor, where the engine takes none of its own.** Where the engine takes only the actor its caller names, and none by default, as [pkit:ADR-098] has it, the command hands it the move with no actor. The engine then records the move, or refuses its entry, as it judges a move no actor is named for.
- **No move, where the engine would take an actor of its own.** Where the engine takes an actor of its own for a move handed none, the command hands it none.
- **Each move the engine does not record** the command reports, as it reports one the engine refused. Where the project keeps a journal, each is a gap there. Where labels carry the state, the drift check shows it (DEC-049 point 3). Where the board or a derivation carries the state, the check is skipped, and the command's report is the only trace.
- **One comment for each audited move.** The key by which a retry finds its own audit comment counts something that grows with each move made, journaled or not. So a move made again after one the journal missed posts its own comment (DEC-049 point 4).
- **Nothing refused for want of an actor.** A merge by bypass, an authorisation to merge given up front, the move to Done after a merge, and the record of a move to Done after a merge already made each pass as they do elsewhere, and each move among them reaches the engine as this point says.

## Rationale

**Why the actor is the account the credential acts as.** COR-033 P4 asks that an authorisation come from another authority than the actor. The predicate reports who merged the pull request as an account, so the comparison means something only against an account, and the account that makes the move is the one its credential acts as. A name in its place, from the variable or git's email, makes an agent's own merge read as another authority's. Naming the account keeps the journal in step with the service's own record of who wrote each change, and gives the journal and the comments one actor, as DEC-049 has the comments project the journal (points 1 and 2).

**Why no authoriser beside the poster, under every credential.** Under a user's credential, the template's name is the posting account's own login, as DEC-021 takes it: a restatement, which DEC-049 point 4 and DEC-052's boundary rule already leave off a comment. The email is a setting of the machine, made by its user or its setup, which may name anyone (DEC-021, "Why a user's login the hosting service answers stands alone"), so beside the posting account it may name another person, the mixed stamp DEC-021 names as a cost. Under a credential that names no user's account, any name beside the poster comes from the caller's word, and reads as the authoriser of an act the service records as the poster's. That holds for a person at a terminal too: a name beside the posting account would be what the session says of them, never what the service records. Dropping both loses nothing the commands can vouch for, and keeps whether a comment names someone beside its poster from turning on which credential a setup holds. An email kept only in the hidden stamp is posted all the same, and whoever reads the comment's source reads it.

**Why the move reaches the engine with no actor only where the engine takes none of its own.** An engine that takes an actor of its own enters a name the commands never knew, which reads as an account, passes its gate on any merge, the agent's own among them, and stands in the journal as the move's actor (Context). An engine that takes only the actor its caller names judges the move as one nobody named, so handing it the move loses nothing the commands can vouch for, and the journal misses only the moves that engine does not record. Keyed to what the engine takes, the rule holds under either engine. A move left unrecorded leaves what the gate's refusal leaves on an agent's own merge, a gap in the journal, and the gap is surfaced, as DEC-049 point 1 asks of a move that fails to journal. Nothing is refused, so what passes on the caller's word, such as a bypass or an authorisation given up front, passes as it does elsewhere. A refusal would go further than the gate it stood in for, which refuses only the entry, never the move, and where the service gives no login, no second run would mend it.

**Why the key counts moves made.** A key that counts the journal's entries stays put while moves go unrecorded. The same audited move made again would then render the comment already posted, and post none, which breaks DEC-049 point 4's one comment per audited mutation.

**What it costs.** Where the engine would take an actor of its own, every move a session makes where the commands know no acting account is a gap in the journal: each step of a forward cascade reports as not completed, and no wait is journaled when a move parks the issue. Where the engine takes none of its own, the gaps are only the moves it does not record, such as a move through a gate that must confirm another authority. In a project that keeps a journal, the journal then misses those moves, and the tracker's timeline, with the service's record of who wrote each change, is their only trail. Where the board or a derivation carries the state, nothing but the command's report shows the gap. Where a journal is kept, the key needs a count the journal does not give on its own.

**Why an empty actor, and not a placeholder.** A placeholder reads as an account, can match one of that name, and records a name the commands never knew. An empty actor grants nothing, and the service records which account posted each comment.

### Alternatives considered

- **Each act's actor only under a credential that names no user's account,** leaving the name and the email the template gives a comment under a user's credential. The case: no comment changes in a project that runs no agent under such a credential. Rejected: the name there restates the poster, the email may name another person, and whether a comment names someone beside its poster would turn on the setup's credential.
- **Keep the email in the hidden stamp only.** The case: tooling keeps a field DEC-044 point 1 gives, and no reader of the rendered comment sees it. Rejected: the stamp is posted with the comment, and names the same setting of the machine.
- **Let the engine take its own actor where the commands know none.** The case: nothing for the commands to decide. Rejected: an engine's own choice reads as an account and passes its gate on any merge (Context).
- **Hand the engine no move with no actor, whatever the engine takes.** The case: one rule, which asks nothing of the engine. Rejected: an engine that takes only the actor its caller names records each move none of whose gates compares the actor, and the journal would miss all of them for no guard gained.
- **A placeholder in place of an empty actor,** such as `unknown`. Rejected: it reads as an account (Rationale).
- **Refuse a move whose transition's gate needs an actor, where the commands know none,** such as the move to Done. The case: no move goes past the gate. Rejected: the gate refuses only the journal entry, never the move, so the refusal would go further than the gate, stop a bypass, an authorisation given up front and a merge a person approved, and no second run would mend it where the service gives no login.
- **Refuse every act that leaves an audit record where the commands know no acting account,** so that every record keeps an actor. Rejected: it would stop every bypass and every audited override under a credential whose login the service does not give, and wherever a lookup fails, for want of a name the commands never knew.

## Implications

- **What changes in every project.**
  - Each audit comment the commands render loses the name and the email the template gives its authoriser, and carries no email in its stamp. The default render's metadata line shows no actor.
  - A comment that records who gave `--force`, or who named a head at a terminal, names them as the account that posts it. Under a credential that acts as another account than that of the person who gave the word, it names that account.
  - The key of an audited move's comment counts moves made, journaled or not.
  - A run under a person's own credential that the service gives no answer for, where a command still acts, hands its moves to the engine as point 3 has it, and its audit records' actor is empty rather than taken from git's configured email.
  - Under a user's credential with `PM_INVOKER_LOGIN` set to another account, DEC-021 has the commands hand the engine, record and name the account the credential acts as (DEC-021, "Every reader of the invoker's identity"), so nothing else changes there.
- **Overturned in part.** Each record below stays accepted, and its overturned words stay as they stood. Its top line, its first paragraph, reads *Partially superseded by [project-management:DEC-078-one-actor-per-act]* and says in the line itself:
  - **DEC-014,** above "Context": "Under every credential, a bypass's audit comment names no authoriser beside the account that posts it, by name or by email, and the template's line reads `Bypassed: <reason>`. Overturned: the audit-comment template's `by <name> <<email>>`, in '`bypassable-with-audit`' and in the Implications' bullet that names the template the canonical form. The rest stands."
  - **DEC-044,** above "In plain terms": "Under every credential, an audit record's actor is its act's actor, the account the credential acts as, by its login, with no email, and where the commands know no acting account it is empty. Overturned: point 1's 'login + display name; email where the source has it'. The rest stands."
  - **DEC-050,** above its quoted summary: "Under every credential, the audit comment of an override of a reviewer names nobody beside the account that posts it. Overturned: point 4's '(name + email)', by which the comment records who overrode. The rest stands."
  - **DEC-052,** above its quoted summary: "The authoriser the commands know is the account that posts the comment, so an override comment names none beside it. Overturned: the Implications' parenthetical that keeps the authoriser on the bot-authored path. The rest stands."
- **Refined in place,** each with the pointer `(refinement per [project-management:DEC-078-one-actor-per-act])`, citing this record's points as DEC-078 point N:
  - **DEC-021, completed:** the Rationale's sentence that "whether git's email and the variable should name the invoker there rests on evidence of its own", for the actor each act names: each act's actor is the account the service answers the credential acts as, and none where the commands know no acting account, never git's email or the variable (DEC-078 points 1 and 3).
  - **DEC-033 D5, narrowed:** a move whose actor the commands do not know is handed to no engine that would take an actor of its own (DEC-078 point 3).
  - **DEC-044 point 4, completed:** its metadata line, which the point leaves to the default's aesthetic, "not frozen here": the default render shows the timestamp and no actor, since a comment's actor is the account that posts it (DEC-078 point 2). A project's own template stays its own.
  - **DEC-049 point 1, completed:** a governed move the engine does not record because the commands know no acting account, whether the command handed it with no actor or not at all, is surfaced as a move that failed to journal. An entry the engine records for such a move names no actor (DEC-078 point 3).
  - **DEC-055 point 3, completed:** the audit comment a `--force` override leaves names who gave it as the account that posts it, the act's actor, and names nobody beside it (DEC-078 point 2).
  - **DEC-067 point 4, completed:** the comment a head named at a terminal leaves names the commit and the command, and who named the head as the account that posts it, the act's actor, naming nobody beside it (DEC-078 point 2).
- **Facts corrected in place,** with no pointer:
  - **DEC-021's Implications, "The email beside the login on an audit comment":** its head reads "No email on an audit comment", and it says that no audit comment carries an email or names an authoriser beside the account that posts it (DEC-078 point 2), so git's configuration on the machine puts no person's email beside that account.
  - **DEC-047 point 5:** its parenthetical names the bypass's line of the audit-comment template, as the validation-severity schema holds it, in place of its quotation of DEC-014's `Bypassed by` line, so the freeform comment verb refuses a first line in that line's form.
- **A stamp that carries an email** changes its shape when the email goes, which takes an explicit version bump of the stamp (DEC-044 point 2).
- **Accepted with or after [pkit:ADR-098],** which point 3 cites for an engine that takes no actor of its own. Point 3's rule holds under either engine, so refusing ADR-098 changes nothing here but that citation.
- **Left out, for a record of its own: what the gate on the move to Done reads as its authorisation.** The predicate reports who merged, so after an agent merges its own approved pull request the gate refuses the entry, as it does for a person's own merge, and the move is a gap in the journal. Whether the predicate should report the approval rather than the merge is a question under every credential.
