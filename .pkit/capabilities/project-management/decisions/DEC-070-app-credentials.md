---
id: DEC-070
title: An account that names no person never acts or counts as a person
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an agent may reach GitHub under a credential that names no person, such as a GitHub App installation's token or a CI workflow's. GitHub will not look such an account up as a user, and refuses it as an assignee.

Under such a credential, this capability's commands never take a person's identity for the account they act as, in a CI workflow and in an agent's session alike, and no comment they post names a person as its authoriser. The person the agent works for, which the session names, serves only where naming a person grants nothing: as the default assignee, and to keep the agent off a Task assigned to someone else. In every project, under every credential, nothing an account the service records as a bot writes counts as a person's claim on work or a person's approval.

What a person accepting this weighs:

- **No instance ownership.** Such a clone claims no Task. In a project with a topology it builds nothing, and elsewhere two sessions under one such credential can start the same Task unseen.
- **Bots approve nothing in human mode.** In every project, an approval from an account GitHub records as a bot, or one the project registers as a reviewer agent's, does not count where a person's approval is required.
- **Closed-mode CI changes.** A workflow under its own token passes a closed membership gate only where its account is a member. Neither `PM_INVOKER_LOGIN` nor git's email stands for it, which reverses what DEC-021 provides for CI.
- **An agent's local verdict names no person.** A reviewer agent's verdict posted on the local path attests only what the acting account ran, until the record on who may authorise in an agent's turn exists.
- **The caller's word stays unguarded.** A bypass, a held move or a release by force passes on the caller's word, as under any credential. Who may give that word in an agent's turn is a record of its own.
- **Building waits on where the reading lives.** Which account a credential acts as is read once, for these commands and the backbone's own reads alike. A record of its own places that reading in the backbone, and point 1 is built only once a person accepts it.

## Context

**The terms.**

- **A credential names a person** where the hosting service, asked which account the credential acts as, answers with a user's account.
- **A credential names no person** where the service answers, and its answer names no user's account. It is of one of two kinds:
  - **an app's credential,** where the answer says that the account is an app's, and gives its login;
  - **an unresolved identity,** where the answer is any other, such as a refusal, which the commands report with its cause ([project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162)).

  Where the service cannot be asked at all, such as with no network, [project-management:DEC-021-team-membership-gate] stands as it is.
- **An app's account** is the account an app's credential acts as. It names no person, and every session that holds the credential acts as it.
- **A user account kept for an agent,** a machine user, is a user's account. Its credential names a person, so this record reaches it only where the project registers it as a reviewer agent's (point 5).
- **The person the agent works for** is the person whose work the agent's session does.
- **The setup** is what prepares the machine and starts the agent's session or the workflow, outside this capability ([pkit:ADR-091] point 7).

**What happens today.** On a trial of software that starts agent sessions on hosted machines, an agent reached GitHub under an App installation's token ([project-kit#3004](https://github.com/aleskalfas/project-kit/issues/3004)). The commands resolve the acting account by looking it up as a user (DEC-021, "Identity resolution"), and the service refuses the lookup:

- **No default assignee.** `create-issue` cannot default the assignee to the filer ([project-management:DEC-019-mandatory-issue-state], "Mandatory assignment").
- **Every assignee is someone else.** `start-work` refuses every Task assigned to the person the agent works for, and sends it to `handoff-issue`, which cannot help ([project-management:DEC-026-work-ownership-lifecycle]).
- **A workaround.** The trial went on by unassigning the person, starting the work, and assigning the person back.
- **The engine's gate takes the person as the actor.** Where `PM_INVOKER_LOGIN` names the person, the commands hand that person to the engine's cross-authority gate as the actor of each move, so the agent's own merge reads as another authority's.

[project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162) has the commands report an identity they cannot resolve, with its cause. How they act under such a credential is this record's.

**What was measured** on the trial ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)):

- **The setup offers a credential that names the person.** It can grant the agent an OAuth sign-in or a personal access token beside the App's. Neither was granted to the trial's agent, so no command has run under one.
- **An app's account is spelled differently on different surfaces.** Read under the person's credential, the comments the trial's App wrote give its login with a `[bot]` suffix and the type `Bot`, and name the App that performed each write. gh's JSON gives the same account, on its pull requests, with an `app/` prefix, marked as a bot.

**What was not measured:**

- **Whether an installation's token can learn its own account and kind.** Both attempts to ask from inside the trial's agent failed before reaching it. Point 1 says what holds without it.
- **Whether the service answers an app's account's write access to a repository,** which an open project's state issues read (point 7).
- **Whether a person's sign-in through a host's app marks the agent's writes as that app's.**

**What the records already say.**

- **The membership gate reads `PM_INVOKER_LOGIN` third,** after the service's login and git's email, where those natural sources do not apply, and a match on any of them passes (DEC-021, "Identity resolution"). DEC-021 reserves the variable for CI and agent contexts, sourced from a CI secret or a workflow input and never from a value the user controls, and its Implications let a CI workflow set it from a CI secret. The commands cannot tell where the variable was set.
- **A claim on an issue of work counts only from the assignee's account** ([project-management:DEC-043-ownership-substrate-selection] point 3). The ownership fold applies that filter in one place ([pkit:ADR-041]).
- **A gate's authorisation comes from another authority than the actor it gates** ([pkit:COR-033] P4). The engine's cross-authority gate compares the actor a command hands it with the account its predicate reports as having merged the pull request. Where the command hands it no actor, the backbone reads its own, and where that read fails, it takes a fixed placeholder as the actor.
- **In human mode, an `Approved` comment counts from the last commenter that is no bot** (DEC-026, Rationale, "Why the three-way OR"). The commands count it from any commenter but the author.
- **A comment names who authorised an act** where they differ from the account that posted it ([project-management:DEC-052-comment-house-style]).
- **A need that differs between machines is met by a property,** never by a host's name. A need not worth meeting is a limit, stated by its property with what meeting it would cost ([pkit:ADR-091] points 2 and 4).

## Decision

**Under a credential that names no person, this capability's commands never take a person's identity for the account they act as, and no comment names a person as its authoriser. In every project, nothing an account the service records as a bot writes counts as a person's claim or approval. The person the agent works for serves only where naming a person grants nothing.**

### 1. The commands read a credential's kind from the service's answer

- **One reading.** Which account a credential acts as, and of which kind, is read once from the hosting service, for this capability's commands and the backbone's own reads alike. A record of its own places that reading in the backbone (Implications, "First, where the reading lives"). This record decides what the commands need of it.
- **An app's, only from a positive answer.** A credential is an app's only where the hosting service answers, for the credential, that its account is an app's, and gives its login. It is never read from a refusal, whose cause may be a rate limit, a suspended account or a network's rule as well as an app. Nor is it read from the host or the tool that issued the credential ([pkit:ADR-091] point 2).
- **Any other answer that names no person** leaves the identity unresolved, and the commands act on it as on an app's credential with no account they know.
- **Only a grant needs the app's own account.** The membership gate (point 2) and a seat's claim (point 7) read the app's login, since they grant the acting account something. Everything else this record decides holds under an unresolved identity too. So in this capability's own guards an answer misread grants nothing, and never lets a person's identity stand for the acting account. The engine's cross-authority gate is the backbone's, and point 2 says what the commands hand it.
- **Each guard reads the property it rests on:** the credential's answer for the acting account, and the service's record of an author for what that author wrote (point 5). The credential's kind is a fact of the session, read where the commands act ([pkit:ADR-091] point 4, its second question). An author's kind is the same on every machine, so the guards that read it are changes right on every machine (its first question).

Whether an installation's token receives a positive answer is unmeasured. Where it does not, such a token leaves the identity unresolved: everything below holds, except that its account can be neither a member (point 2) nor a seat's holder (point 7).

### 2. No person stands for the acting account

Under a credential that names no person, in a CI workflow and in an agent's session alike:

- **The acting account** is the app's, by the login the service gives it. Under an unresolved identity, the commands know no acting account.
- **One spelling.** Every comparison of two accounts puts both in one spelling, through one function beside the reading (point 1), whichever surface named each. So no comparison spells an account its own way, as no command reads the labels its own way ([pkit:ADR-026]).
- **The actor of the engine's gate.** The actor the engine's cross-authority gate compares is the acting account in that one spelling, whether a command hands it or the engine reads it, and the gate's predicate reports the account that merged the pull request in the same spelling. It is never the person the agent works for. Under an unresolved identity, a command hands no actor, and what the engine then takes is the backbone's to decide (Implications, "Left out").
- **Git's configured email does not stand for it.** The email names whoever set up git on the machine, a person the credential does not act as.
- **Nor does `PM_INVOKER_LOGIN`.** Whoever starts the run or the session can set it, and the commands cannot tell who did. It names the person the agent works for (point 3).
- **The closed membership gate** matches an app's account by its login alone. A project lets such an account act by adding it as a member. That admits every session that holds the credential, whoever starts it, and the project decides so by adding it.
- **The member list changes under no such credential.** Membership grants authority, and an account that names no person has no one to stand behind a change to it. So a command that adds or removes a member refuses, and a person changes the list under their own credential. This holds while the gate is open too, where adding such an account as the first member would close the gate with no person in it.
- **An app's account in the member list is no person.** Where a command picks members as people, such as reviewers in human mode, it passes over an app's account.

Under a credential that names a person, this record changes nothing in how the acting account is resolved.

### 3. The person the agent works for serves only where naming a person grants nothing

- **Where it comes from.** Under a credential that names no person, `PM_INVOKER_LOGIN` names the person the agent works for. The variable is an input of the commands, documented with them, so its meaning is part of their public surface, which a setup uses as any adopter does ([pkit:ADR-091] point 7). One function of this capability reads it, for every command that needs that person.
- **Where it serves.** It stands where the commands would name the acting account as a person, and grant nothing by doing so:
  - the default assignee at filing, and `--me` on an assignment (DEC-019);
  - `start-work`'s refusal of a Task assigned to someone else, and the assignee it writes (point 4);
  - which Tasks `next-task` hands out, since it hands out only what `start-work` takes.
- **Where it never serves.** It never stands where naming a person grants: the membership gate, a claim, an approval, or the authoriser a comment names. So `--me` on a command that changes the member list refuses (point 2). Nor does it tell whether anyone is at the terminal, which is a property of the session's process ([pkit:ADR-091] point 5).
- **Without it,** a command that needs a person refuses, and says that the account names no person and how the session can name one. `create-issue` still takes an assignee named in the call, as when a person files for another ([project-management:DEC-035-instance-ownership] point 5).

It is the caller's word, as an assignee the caller names is. Set wrongly, it lets the agent past the refusal that keeps it off another person's Task. Like DEC-035's clash guard, that refusal catches the mistakes of agents that follow the procedure, and is no security boundary.

### 4. `start-work` keeps its refusal, against the person the agent works for

Under a credential that names no person, in a project with no topology, `start-work`:

- **refuses a Task assigned to someone other than the person the agent works for,** and names `handoff-issue`, as DEC-026 has it;
- **assigns that person a Task with no assignee,** since DEC-019 needs one and the acting account cannot be it, and writes no assignee where that person is one already;
- **posts no claim,** since no claim it wrote would count (point 5);
- **refuses a Task an instance owns.** The clash guard reads the owner for such a clone, though the clone claims nothing. A reason overrides the refusal and posts an audit comment, as for any clash (DEC-035 point 6).

Every other ordinary lifecycle verb under such a credential reads the owner the same way. `handoff-issue` hands a Task from one person to another, and never to an app's account.

Two sessions under one such credential, working for one person, can start the same Task, since neither claims it. Nothing tells them apart, as nothing tells apart two of a person's clones with no instance id (DEC-035 point 1). This is a limit (point 8).

In a project with a topology, such a clone starts no Task (point 7).

### 5. Nothing an account that names no person writes counts as a person's

The commands read the kind of an author from the service's record of that author, which says whether it is a bot. These guards hold for every account the service records as a bot, under whatever credential the command runs, and whether or not the service lets that account be assigned:

- **A claim on an issue of work** counts only from the assignee's account (DEC-043 point 3), and never from a bot's. So a clone under a credential that names no person takes no part in instance ownership on issues of work.
- **An approval in human mode.** An `Approved` comment or an approving review counts only from an account the service records as no bot, and that the project does not register as a reviewer agent's ([project-management:DEC-028-agent-as-approver-paths], the remote path's list). A request for changes holds the merge whoever made it, since holding a merge grants nothing. So human mode's gate rests on another authority than the actor, as COR-033 P4 asks.
- **A reviewer agent's verdict** counts in agent mode as DEC-028's paths have it. Under a credential that names no person, the local path's verdict is posted by the acting account. It attests what that account ran, and names no person responsible for it. That takes a person's name off an attestation no person made: under a person's credential, an agent's session posts the verdict in that person's name, though the person attested nothing. The local path rests on the trust of a bypass (point 6), and is revisited once the record on who may authorise in an agent's turn guards the caller's word.
- **An authoriser in a comment.** The authoriser the commands know is the acting account, which here names no person. So an override comment names no person as its authoriser (DEC-052). A reason the caller gives may report a person's word, and stays the caller's report.
- **A claim on a state issue** that an app's account writes is that account's own, and names no person ([project-management:DEC-058-state-issues] point 5). Point 7 says where it counts.

### 6. What passes on the caller's word stays as it is

Some acts pass on the caller's word under every credential: a merge by bypass, a move the user holds, a promotion on a person's request in the session, and a release of a seat by force on a person's word ([project-management:DEC-006-state-machine-and-cascade], DEC-026, [project-management:DEC-059-topology-of-seats] point 5). Under a credential that names no person they pass as they do elsewhere. Each is recorded as the acting account's act, with the caller's reason, and names no person as its authoriser (point 5).

This record guards none of them. Who may give that word in an agent's turn is a record of its own ([pkit:ADR-091], Implications, gap 5).

### 7. In a project with a topology, such a clone builds nothing

- **No seat that builds.** A worker's or a lead's seat rests on claims on Tasks that count (DEC-059 point 9), and such a clone's never do. So it takes no such seat (DEC-059 point 4).
- **No Task without a seat.** A clone with no seat marks no issue and is guarded by nothing (DEC-059 point 6). A Task it started would stand In Progress with no claim that counts, which a worker reads as ready to take over (DEC-059 point 7). So under such a credential `start-work` refuses.
- **A seat that builds nothing, where its claim counts.** An app's clone may hold a planner's seat, since its claim on the seat's state issue is its own account's. That claim counts only where DEC-058 point 4 counts its author: as a member where the gate is closed, and otherwise where the service answers that the account may write to the repository, which is unmeasured. An answer for such an account that the commands cannot read counts as a call that failed, and a failed call leaves the read incomplete and drops no claim ([pkit:ADR-071] point 3). Where the claim does not count, or the read is incomplete, the seat is not taken under that credential. Under an unresolved identity, the clone takes no seat.
- **A planner's filings** are assigned to the person the agent works for (point 3). Workers under that person's own credential take them. A worker under another person's credential meets `start-work`'s refusal, as it does with the filings of a planner under any one person's credential.

### 8. What stays unmet, and the setup's choice of credential

These needs stay unmet under a credential that names no person. Each is a limit, stated by its property with what meeting it would cost ([pkit:ADR-091] point 4):

- **Instance ownership on issues of work,** and so building in a project with a topology. Meeting it would count a claim from an account that names no person, which loosens DEC-043 point 3: anyone holding the credential could then claim work for any person. That loosening is a person's decision of its own.
- **Two sessions under one such credential, kept off one Task.** Meeting it needs a mark that such a clone makes and that other such clones read, a design of its own.
- **The closed membership gate under an unresolved identity.** Meeting it needs the service's positive answer for the credential (point 1).

A setup that needs one of them gives the agent another credential:

- **A credential that names the person the agent works for,** which the measured setup offers and which no command has run under yet. The commands then act as the person, and the agent's pull requests are the person's own, which the person cannot approve (DEC-028, "Self-approval degrade").
- **A machine user,** which is not recommended. The commands act as it as they act as a person, so the assignee would name no person responsible for the work (DEC-019).

Which credential an agent holds is its setup's choice ([pkit:ADR-091] point 7).

## Rationale

**Why the commands never take the person's identity.** The commands know a person's identity only from a credential that names that person. Any other value that names the person is the caller's word. Acting as the person on that word would make each act of the account read as the person's own, in the tracker and in every check that reads it. Acting as the account the service names keeps that record true, since the service shows which account wrote each change.

**Why `PM_INVOKER_LOGIN` names no acting account, in CI as in a session.** Set to the person, it would let `start-work` write the person as assignee. Three things stand against it:

- **It names the person as the actor of every act.** Each override comment would name the person as its authoriser, beside the account that posted it (DEC-052), whether or not the person authorised anything.
- **It hands the engine's gate the wrong actor.** The gate would compare the person with the account that merged, so the agent's own merge would read as another authority's (COR-033 P4).
- **It would not make a claim count.** The ownership fold reads who wrote a claim, never the variable (DEC-043 point 3). So instance ownership stays out of reach.

DEC-021 meant to keep the variable from a value the user controls, and trusted a CI workflow to keep it so. That line does not hold, under any credential. A workflow's input is typed by whoever dispatches the run, and an earlier step can set the environment of later ones. A pipeline that runs an agent's session on one prompt is both a CI workflow and an agent's session ([pkit:ADR-091], Rationale, "Why the test should hold beyond DAM"). So the variable is read the same way in both: as the caller's word, where the caller's word grants nothing.

**This reverses what DEC-021 and DEC-022 provide for CI.** Under a credential that names no person, a workflow stands for a member only by its own account, never by the variable or by git's email. It is made as a refinement in place, not a partial supersession: DEC-021 left the edge cases of identity resolution to its implementation (Rationale, "Why mechanism details are deferred"), and its principle, that only members act, stands. Under a credential that names a person, the variable and git's email keep the place DEC-021 gives them, and #3175 settles which reading of that place DEC-021 means.

**Why git's email does not stand for the account.** Under any credential the email is a value the user controls, and that hole is no question of this record's (#3175). Under a credential that names no person, there is a reason of its own: the email names a person the credential does not act as.

**Why the person the agent works for grants nothing.** Most of what the commands do with a person's login says whose the work is: the assignee at filing, and whether a Task is someone else's. A wrong value there misleads, and grants nothing, since a claim, an approval and membership are each read from the account that wrote or acts, never from the assignee. A command that takes an assignee from the caller, when a person files for another, takes the caller's word the same way.

**Why `start-work` keeps its refusal.** Without a person to compare with, an account that names no person is nobody's assignee. The refusal would then either catch every assignee, as on the trial, or none, which would let an agent start any member's Task. The refusal is a mistake-catcher, as are its neighbours (DEC-058 point 5, and DEC-059's release by force, which "catches mistakes, and it is no security boundary"). On the caller's word, it keeps catching the mistakes of agents that follow the procedure.

**Why the clash guard reads for such a clone.** A person's clone with no instance id may opt into ownership, and is guarded once it does (DEC-035 point 1). A clone under a credential that names no person cannot opt in, since none of its claims counts. Reading the owner is then the only guard it can have, and it grants nothing.

**Why the guards read the author's kind.** A claim means something because only the assignee's own account can make it (DEC-043 point 3). A guard derived from the service refusing a bot as an assignee would fail once a bot can be assigned, as GitHub lets its own coding agent be. Read from the author's kind, the guard holds for every bot, whatever the service lets it be. Counting a bot's claim for its assignee would let anyone who holds the credential claim work for any person.

**Why a bot approves nothing in human mode, in every project.** Human mode asks for a person's approval. DEC-026 counts the comment from the last commenter that is no bot, and the commands count it from any commenter but the author. Reading the author's kind aligns the two. It also leaves out the accounts the project registers as its reviewer agents', which name no person whatever the service reports. A request for changes still holds, since holding a merge back grants nothing.

**Why DEC-028's local path stands, for now.** DEC-028 rests the local path on the developer's attestation, the trust of a bypass, rather than on a trace from another authority. Under a credential that names no person, a bypass passes all the same (point 6). Refusing the local path would push such an agent to a bypass, which records less: no verdict, no reviewer, no head reviewed. Keeping it loosens nothing: under a person's credential, an agent's session already posts the verdict in the person's name, though the person attested nothing, and under a credential that names no person the verdict names no person, which is true. The reason lasts only while a bypass passes on the caller's word. Once the record on who may authorise in an agent's turn guards that word, the local path is the weakest way past the gate under such a credential, and is revisited.

**Why such a clone builds nothing in a topology.** A seat stays taken until it is released (DEC-059 point 5). A clone that took a building seat and could claim no Task would hold the seat while doing none of its work. A Task it started without a seat would read as ready to take over, and a worker would take it over from under the agent.

**Why act as the account, and not only state a limit.** The setup offers a credential that names the person, so every need could be a limit. But most of what the commands do needs no person at all. And under the person's credential, the agent's pull request is the person's own, which the person cannot approve (DEC-028, "Self-approval degrade"). Under an account that names no person, the person can approve it, by a review or an `Approved` comment. That is the trace from another authority that COR-033 P4 asks of a gate.

**Why building waits on where the reading lives.** The backbone reads the acting account too: the cross-authority gate's actor, where no command hands one, and the account `pkit report` posts as. Two readings of one credential can disagree, and at the engine's gate they already can. Where a command hands no actor and the backbone's own read fails, the gate's actor is a placeholder, and under an app's credential the two sides may spell one account two ways. In both cases the gate reads the agent's own merge as another authority's. A reading built in this capability first adds one more copy before the placement is decided. A capability's script reaches the backbone only by command ([pkit:ADR-057] point 1), the backbone cannot depend on a capability a project may not install, and a computation keeps one home (ADR-057 point 2). So the one home both can read is the backbone, as [pkit:ADR-061] reasoned for the hosting service's acts, which it placed there provisionally and on GitHub alone.

### Alternatives considered

- **State a limit and nothing more:** the commands act only under a credential that names a person. The case: one sentence, and nothing to build. Rejected: most of what the commands do needs no person, and the person could not approve their agent's pull requests.
- **A limit, plus a mark the commands add to what an agent's session writes.** The case: no edits to other records, and instance ownership keeps working under the person's credential. Rejected: the mark is the session's own word, so the line it draws is weaker than the service's record of which account wrote, and the person still cannot approve the agent's pull requests.
- **`PM_INVOKER_LOGIN` names the acting account,** in an agent's session, or only in a CI workflow as DEC-021 provides. The case: `start-work` and `create-issue` work as under the person's credential, with nothing new. Rejected, for the reasons above, and because no line between a workflow and a session holds.
- **Supersede DEC-021 in part, for its provision for CI.** The case: the record reverses a provision DEC-021 made, and a partial supersession says so at DEC-021's top. Not taken: DEC-021 left identity resolution's edge cases to its implementation, and its principle stands, so refining it keeps one record stating the gate. A person who reads the reversal as overturning DEC-021 in part takes this instead.
- **An interim reading in this capability, in one seam** that every comparison of accounts goes through, for #3171 to move into the backbone later. The case: the capability's work starts at once, without waiting on a record of the backbone's, and the later move touches one seam. Not taken: until the move, two readings of one credential run side by side, and they already disagree at the engine's gate. The cost is a second copy of the reading, kept in step with the backbone's by hand until the move, and a spelling every comparison relies on, which changes again if the backbone settles another.
- **`start-work` works under whatever assignee the Task has,** with no person named. The case: nothing rests on the caller's word, and the setup gives nothing. Rejected: an agent could start any member's Task, which drops a mistake-catcher that costs one value to keep.
- **A setting kept for the clone names the person the agent works for,** written by the setup through a command, in place of the variable. The case: it lasts across sessions, and ADR-091 point 7 names such a setting as what a setup writes. Not taken: it needs a command and a stored value of its own, a CI run would write it each time, and the variable already serves these contexts.
- **No clash guard for such a clone,** as for a person's clone with no instance id. The case: one rule for every clone with no id. Rejected: a person's clone can opt in and such a clone cannot, so without the read it would act on a Task another of the person's clones is building, with nothing to warn it.
- **Count a bot's claim for its assignee,** loosening DEC-043 point 3. The case: instance ownership, and building in a topology, under such a credential. Not taken: anyone holding the credential could claim work for any person, and loosening the guard is a person's decision.
- **Drop every review by a bot in human mode,** requests for changes included. The case: one rule for every bot review. Rejected: a bot's request for changes would stop holding a merge, which loosens a guard for no gain.
- **Treat only accounts the service records as bots as no person.** The case: one source for an account's kind. Rejected: a reviewer agent's machine user would then approve in human mode, and the project already names its reviewer agents' accounts (DEC-028), so leaving them out costs nothing.
- **Refuse DEC-028's local path under such a credential,** asking another account to post the verdict. The case: no verdict that the actor posts on its own pull request. Rejected: a bypass passes there all the same (point 6), and records less.
- **Read an app's credential from the service's refusal to look the account up.** The case: it is what the trial saw. Rejected: a refusal has other causes, and gives no account to act as.

## Implications

- **Edits once accepted.** Once a person accepts this record, each record below is refined in place in this change, with the pointer `(refinement per [project-management:DEC-070-app-credentials])`:
  - **DEC-019, "Mandatory assignment":** under a credential that names no person, the default assignee at filing and `--me` are the person the agent works for. Without one, `create-issue` takes the assignee named in the call and refuses a filing that names none, and `assign-issue --me` refuses. No command makes such an account an assignee.
  - **DEC-021, "Identity resolution":** the service is asked first. Under a credential it answers as an app's, the identity is the app's account, by its login, compared in one spelling across surfaces. Under any other answer that names no person, the identity is unresolved. Under either, neither git's email nor `PM_INVOKER_LOGIN` stands for the acting account, in a CI workflow and in an agent's session alike, and the variable names the person the agent works for. Item 3 says that the variable is an input of the commands, documented with them, and that the commands cannot tell who set it under any credential, in place of "never from user-controllable env". **"Membership change authority":** under such a credential, a command that adds or removes a member refuses. **Implications, the CI invocations:** a workflow under a credential that names no person passes the closed gate only where its account is a member, and the variable does not stand for it.
  - **DEC-022, "Authority":** the scheduled workflow, under a credential that names no person, passes the closed gate only where its account is a member, and `PM_INVOKER_LOGIN` does not stand for it.
  - **DEC-026:**
    - the `start-work` row of "The seven commands", and the assignee-conflict row of "Sub-decisions index": under such a credential, `start-work` compares the Task's assignee with the person the agent works for, refuses another's Task as under a person's credential, assigns that person a Task with none, posts no claim, refuses a Task an instance owns, and refuses where the session names no person or the project has a topology;
    - the `done-work` row of each table: in human mode, an `Approved` comment or an approving review counts only from an account the service records as no bot and the project does not register as a reviewer agent's;
    - "Reviewer assignment": human mode passes over an app's account in the member list;
    - the `handoff-issue` row: a Task is never handed to an app's account.
  - **DEC-028, "Path 2: Local agent":** under a credential that names no person, the verdict is posted by the acting account, attests what that account ran, and names no person responsible for it. The path rests on the trust of a bypass, and is revisited once the record on who may authorise in an agent's turn guards the caller's word.
  - **DEC-035 point 1:** a clone under such a credential takes no part in instance ownership on issues of work, and the clash guard of point 6 reads the owner for it.
  - **DEC-043 point 3:** a marker counts only from the assignee's account, and never from an account the service records as a bot.
  - **DEC-052, the roster's override row:** under such a credential, the authoriser the commands know is the posting account, so the comment names no person as its authoriser.
  - **DEC-058 point 4:** a comment an app's account writes on a state issue counts by the same test as any author's, as that account's own, and never as a person's.
  - **DEC-059 points 4 and 6:** a clone under such a credential takes no seat that builds, and under an unresolved identity no seat at all. With no seat, it starts no Task.
- **Architecture records, edited once accepted.** The architect, whose custody they are in, refines each in place in this change, with the same pointer:
  - **[pkit:ADR-041], points 1 and 2 and its Implications:** the ownership fold's filter keeps a marker only from the expected assignee's account, and never from an account the service records as a bot. So the comment reader gives each author's kind.
  - **[pkit:ADR-071] point 3:** an author's login is compared with the members' entries in one spelling. Where the gate is open, an answer about an author's write access that the seam cannot read for a bot counts as a call that failed, which leaves the read incomplete.
- **First, where the reading lives.** Building point 1, and every point that rests on it, waits on an accepted record that places the reading of the acting account in the backbone, which answers #3171's first question. What this record needs of it is that the account is read once, its kind only from the service's positive answer (point 1), and that every comparison of accounts uses one spelling (point 2). It would hold the reading on GitHub alone and provisionally, as [pkit:ADR-061] point 3 holds the hosting service's acts. That record is the architect's to draft, and whether it is drafted now is a person's to decide. Before it, the answer of the service that tells an app's credential is measured under an installation's token (point 1). The guards of point 5 that read only an author's kind need no reading of the acting account, and may be built before it.
- **The work** is planned once this record and that one are accepted. It builds on the report of an unresolved identity that [project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162) adds. It covers points 1 to 7, with their messages and the tests that hold them, and:
  - the member list's description of a login, which names one lookup's spelling (point 2);
  - the one function that reads the person the agent works for (point 3);
  - the capability's README, which documents `PM_INVOKER_LOGIN` as an input of the commands, with what it names under each kind of credential (point 3);
  - the cross-repository guard, which stops reading the variable as a sign that nobody is at the terminal, and reads that from the session's process (point 3);
  - the pm skill's procedure on these refusals: the agent tells the person what the session lacks, and never sets a person's login as the acting account;
  - pkit's page on running with nobody at the terminal, which states the limits of point 8 with their costs ([pkit:ADR-091] point 7).

  It declares a `minor` change for project-management. It adds behaviour, and changes no installed file, name or schema, so it needs no migration. Two of its changes reach projects that run no agent under such a credential: a bot's approval in human mode, and a closed-mode workflow that passes by the variable or by git's email. Each refuses more, or counts less, and its message names the way out. Whether either weighs as `major` is a person's judgment, made when the work's changeset is written.
- **Left out, for records of their own:**
  - **The backbone's own reads of who is acting,** such as the cross-authority gate's actor and the account `pkit report` posts as ([project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171)). Where a command hands the engine no actor, the backbone reads its own, and where that read fails, it takes a fixed placeholder as the actor. The gate then reads every merge, the agent's own included, as another authority's. That is the disagreement between two readings that #3171 must settle, and the record above answers its first question.
  - **Who may authorise in a turn that a chat started** ([pkit:ADR-091], Implications, gap 5), which decides the acts of point 6, and when DEC-028's local path is revisited (point 5).
  - **The person the agent works for, in the backbone.** One function of this capability reads it (point 3). The backbone already posts for a person an agent works for, in `pkit report`, and the record for gap 5 needs that person too. A variable named for this capability is no name the backbone can depend on, so #3171 or that record may lift the reading into the backbone.
  - **Git's email and `PM_INVOKER_LOGIN` beside a person's login** ([project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175)). Under a credential that names a person, DEC-021 reads git's email where the service's login is not available, and the variable third, where neither applies, and passes a match on any of them. The commands read the variable first, in place of the login, and let the email match a member beside a resolved login that is no member's. Which reading DEC-021 means holds on every machine, and is no question of a credential that names no person.
  - **Whether a credential reaches the project's board,** decided under every credential apart from this record ([project-management:DEC-071-board-reach-check]), and an organisation's board under an app's credential, measured on [project-kit#3172](https://github.com/aleskalfas/project-kit/issues/3172).
- **This change** lands the record with a `none` changeset for project-management, since no behaviour changes until it is built. It needs no migration.
