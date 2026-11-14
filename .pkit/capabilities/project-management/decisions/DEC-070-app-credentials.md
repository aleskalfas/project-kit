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

- **No instance ownership.** A clone under such a credential claims no Task. In a project with a topology it builds nothing, and elsewhere two sessions under one such credential can start the same Task unseen.
- **Bots approve nothing in human mode.** In every project, an approval from an account GitHub records as a bot, or one the project registers as a reviewer agent's, does not count where a person's approval is required.
- **Closed-mode CI changes, overturning part of DEC-021 and DEC-022.** A workflow under its own token passes a closed membership gate only where its account is a member. Neither `PM_INVOKER_LOGIN` nor git's email stands for it, as those two records provide. Each stays accepted, and its top line names what this record overturns there.
- **No person is named beside a bot, overturning part of DEC-052.** Under such a credential, an override comment names no person as its authoriser, where DEC-052 keeps one beside the bot that posts it. DEC-052 stays accepted, with the same kind of top line.
- **A refused lookup under a person's own credential.** Where the service refuses to say which account a person's credential acts as, such as on a rate limit or for a suspended account, the identity is unresolved, as under any refusal. Git's email and the variable do not stand in, where the commands fall back to them today.
- **An agent's local verdict names no person.** A reviewer agent's verdict posted on the local path attests only what the acting account ran, until the record on who may authorise in an agent's turn exists.
- **The caller's word stays unguarded.** A bypass, a held move or a release by force passes on the caller's word, as under any credential. Who may give that word in an agent's turn is a record of its own.
- **Building waits on where the reading lives.** This record says what the commands need of the reading of the acting account. The backbone reads that account too, so where the reading lives is a record of its own, and point 1 is built only once a person accepts it.

## Context

**The terms.**

- **A credential names a person** where the hosting service, asked which account the credential acts as, answers with a user's account.
- **A credential names no person** where the service answers, and its answer names no user's account. It is of one of two kinds:
  - **an app's credential,** where the answer says that the account is an app's, and gives its login;
  - **an unresolved identity,** where the answer is any other, such as a refusal, which the commands report with its cause ([project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162)). A person's own credential whose lookup the service refuses is one.

  Where the service cannot be asked at all, such as with no network, [project-management:DEC-021-team-membership-gate] stands as it is.
- **An app's account** is the account an app's credential acts as. Every session that holds the credential acts as it.
- **An account names no person** where the service records it as a bot, as it records an app's account.
- **A user account kept for an agent,** a machine user, is a user's account, which the service records as no bot. Its credential names a person, so this record reaches it only where the project registers it as a reviewer agent's (point 5).
- **The person the agent works for** is the person whose work the agent's session does.
- **The setup** is what prepares the machine and starts the agent's session or the workflow, outside this capability.

**What happens today.** On a trial of software that starts agent sessions on hosted machines, an agent reached GitHub under an App installation's token ([project-kit#3004](https://github.com/aleskalfas/project-kit/issues/3004)). The commands resolve the acting account by looking it up as a user (DEC-021, "Identity resolution"), and the service refuses the lookup:

- **No default assignee.** `create-issue` cannot default the assignee to the filer ([project-management:DEC-019-mandatory-issue-state], "Mandatory assignment").
- **Every assignee is someone else.** `start-work` refuses every Task assigned to the person the agent works for, and sends it to `handoff-issue`, which cannot help ([project-management:DEC-026-work-ownership-lifecycle]).
- **A workaround.** The trial went on by unassigning the person, starting the work, and assigning the person back.
- **The engine's gate takes the person as the actor.** Where `PM_INVOKER_LOGIN` names the person, the commands hand that person to the engine's cross-authority gate as the actor of each move, so the agent's own merge reads as another authority's.

[project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162) has the commands report an identity they cannot resolve, with its cause. How they act under such a credential is this record's.

**What was measured** on the trial ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)):

- **The setup offers a credential that names the person.** It can grant the agent an OAuth sign-in or a personal access token beside the App's. Neither was granted to the trial's agent, so no command has run under one.
- **An app's account is spelled differently on different surfaces.** Read under the person's credential, the comments the trial's App wrote give its login with a `[bot]` suffix and the type `Bot`, and name the App that performed each write. gh's JSON gives the same account, on its pull requests, with an `app/` prefix, marked as a bot.
- **An App installation's token sees none of a user's boards.** Asked for the boards of the person's account, it answered with none, a public one included, and no error. The person's own token saw three.

**What was not measured:**

- **Whether an installation's token can learn its own account and kind.** Both attempts to ask from inside the trial's agent failed before reaching it. Point 1 says what holds without it.
- **Whether the service answers an app's account's write access to a repository,** which an open project's state issues read (point 7).
- **Whether a person's sign-in through a host's app marks the agent's writes as that app's.**

**What the records already say.**

- **The membership gate reads `PM_INVOKER_LOGIN` third,** after the service's login and git's email, where those natural sources do not apply, and a match on any of them passes (DEC-021, "Identity resolution"). DEC-021 reserves the variable for CI and agent contexts, sourced from a CI secret or a workflow input and never from a value the user controls. Its Implications let a CI workflow pass the gate by setting the variable from a CI secret, and [project-management:DEC-022-methodology-mesh], "Authority", says the same of its scheduled workflow. The commands cannot tell where the variable was set.
- **A claim on an issue of work counts only from the assignee's account** ([project-management:DEC-043-ownership-substrate-selection] point 3). The ownership fold applies that filter in one place ([pkit:ADR-041]).
- **A gate's authorisation comes from another authority than the actor it gates** ([pkit:COR-033] P4). The engine's cross-authority gate compares the actor a command hands it with the account this capability's predicate reports as having merged the pull request. Where the command hands it no actor, the backbone reads its own, and where that read fails, it takes a fixed placeholder as the actor.
- **In human mode, an `Approved` comment counts** from a commenter other than the author in DEC-026's tables, and from the last commenter that is no bot in its Rationale ("Why the three-way OR"). The commands count it from any commenter but the author, a bot among them.
- **A comment names who authorised an act** only where they differ from the account that posted it, and the actor is taken for the authoriser ([project-management:DEC-049-audit-journal-model] point 4). [project-management:DEC-052-comment-house-style] keeps the authoriser on a comment a bot posts.

**A rule held provisionally.** project-kit's own record on agent hosts holds that a need that differs between machines is met by reading a property, never a host's name, and that a need not worth meeting is a limit, stated by its property with what meeting it would cost ([pkit:ADR-091] points 2 and 4). It holds those rules provisionally, and they reach no adopter as rules, so this record states for itself what it takes from them (points 1 and 8).

## Decision

**Under a credential that names no person, this capability's commands never take a person's identity for the account they act as, and no comment names a person as its authoriser. In every project, nothing an account the service records as a bot writes counts as a person's claim or approval. The person the agent works for serves only where naming a person grants nothing.**

### 1. The commands read a credential's kind from the service's answer

- **One reading.** Which account a credential acts as, and of which kind, is read once from the hosting service, and every command of this capability takes it from that reading. The backbone reads the acting account too, so where the reading lives is a record of its own (Implications, "First, where the reading lives"). This record decides what the commands need of it.
- **An app's, only from a positive answer.** A credential is an app's only where the hosting service answers, for the credential, that its account is an app's, and gives its login. It is never read from a refusal, whose cause may be a rate limit, a suspended account or a network's rule as well as an app. Nor is it read from the host or the tool that issued the credential, whose names say nothing of the account and may change without notice.
- **Any other answer that names no person** leaves the identity unresolved, and the commands act on it as on an app's credential with no account they know.
- **Only a grant needs the app's own account.** The membership gate (point 2) and a seat's claim (point 7) read the app's login, since they grant the acting account something. Everything else this record decides holds under an unresolved identity too. So in this capability's own guards an answer misread grants nothing, and never lets a person's identity stand for the acting account. The engine's cross-authority gate is the backbone's, and point 2 says what the commands hand it.
- **Each guard reads the property it rests on:** the credential's answer for the acting account, and the service's record of an author for what that author wrote (point 5). The credential's kind is a fact of the session, read where the commands act. An author's kind is the same wherever it is read, so the guards that read it hold alike on every machine.

Whether an installation's token receives a positive answer is unmeasured. Where it does not, such a token leaves the identity unresolved: everything below holds, except that its account can be neither a member (point 2) nor a seat's holder (point 7).

### 2. No person stands for the acting account

Under a credential that names no person, in a CI workflow and in an agent's session alike:

- **The acting account** is the app's, by the login the service gives it. Under an unresolved identity, the commands know no acting account.
- **One spelling.** Every comparison of two accounts puts both in one spelling, through one function beside the reading (point 1), whichever surface named each. So no comparison spells an account its own way, as no command reads the labels its own way ([pkit:ADR-026]).
- **The actor the commands hand the engine.** The actor the commands hand the engine's cross-authority gate is the acting account in that one spelling, and this capability's predicate for the gate reports the account that merged the pull request in the same spelling. The actor is never the person the agent works for. Under an unresolved identity, the commands hand no actor, and what the engine takes then is the backbone's to decide (Implications, "Left out").
- **Git's configured email does not stand for it.** The email names whoever set up git on the machine, a person the credential does not act as.
- **Nor does `PM_INVOKER_LOGIN`.** Whoever starts the run or the session can set it, and the commands cannot tell who did. It names the person the agent works for (point 3).
- **The closed membership gate** matches an app's account by its login alone. A project lets such an account act by adding it as a member. That admits every session that holds the credential, whoever starts it, and the project decides so by adding it.
- **The member list changes under no such credential.** Membership grants authority, and an account that names no person has no one to stand behind a change to it. So a command that adds or removes a member refuses, and a person changes the list under their own credential. This holds while the gate is open too, where adding such an account as the first member would close the gate with no person in it.
- **An app's account in the member list is no person.** Where a command picks members as people, such as reviewers in human mode, it passes over an app's account.

Where the service answers with a user's account, this record changes nothing in how the acting account is resolved. A person's own credential whose lookup the service refuses leaves the identity unresolved, and everything above holds for it.

### 3. The person the agent works for serves only where naming a person grants nothing

- **Where it comes from.** Under a credential that names no person, `PM_INVOKER_LOGIN` names the person the agent works for. The variable is an input of the commands, documented with them, so its meaning is part of their public surface, which a setup uses as any adopter does ([pkit:ADR-091] point 7). One function of this capability reads it, for every command that needs that person.
- **Where it serves.** It stands where the commands would name the acting account as a person, and grant nothing by doing so:
  - the default assignee at filing, and `--me` on an assignment, held like any assignee to a member where the gate is closed (DEC-019);
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
- **refuses a Task an instance owns.** The clash guard reads the owner for a clone under such a credential, though the clone claims nothing. A reason overrides the refusal and posts an audit comment, as for any clash (DEC-035 point 6).

Every other ordinary lifecycle verb under such a credential reads the owner the same way. `handoff-issue` hands a Task from one person to another, and never to an app's account.

Two sessions under one such credential, working for one person, can start the same Task, since neither claims it. Nothing tells them apart, as nothing tells apart two of a person's clones with no instance id (DEC-035 point 1). This is a limit (point 8).

In a project with a topology, a clone under such a credential starts no Task (point 7).

### 5. Nothing an account that names no person writes counts as a person's

The commands read the kind of an author from the service's record of that author, which says whether it is a bot. These guards hold for every account the service records as a bot, under whatever credential the command runs, and whether or not the service lets that account be assigned:

- **A claim on an issue of work** counts only from the assignee's account (DEC-043 point 3), and never from a bot's. So a clone under a credential that names no person takes no part in instance ownership on issues of work.
- **An approval in human mode.** An `Approved` comment or an approving review counts only from an account the service records as no bot, and that the project does not register as a reviewer agent's ([project-management:DEC-028-agent-as-approver-paths], the remote path's list). A request for changes holds the merge whoever made it, since holding a merge grants nothing. So human mode's gate rests on another authority than the actor, as COR-033 P4 asks.
- **A reviewer agent's verdict** counts in agent mode as DEC-028's paths have it. Under a credential that names no person, the local path's verdict is posted by the acting account. It attests what that account ran, and names no person responsible for it. That takes a person's name off an attestation no person made: under a person's credential, an agent's session posts the verdict in that person's name, though the person attested nothing. The local path rests on the trust of a bypass (point 6), and is revisited once the record on who may authorise in an agent's turn guards the caller's word.
- **An authoriser in a comment.** The only authoriser the commands know is the acting account, which posts the comment and here names no person, or is none they know. A comment names the authoriser only where the poster is someone else (DEC-049 point 4), so an override comment names no person as its authoriser. A reason the caller gives may report a person's word, and stays the caller's report.
- **A claim on a state issue** that an app's account writes is that account's own, and names no person ([project-management:DEC-058-state-issues] point 5). Point 7 says where it counts.

### 6. What passes on the caller's word stays as it is

Some acts pass on the caller's word under every credential:

- a merge by bypass, and a promotion on a person's request in the session (DEC-026);
- a move the user holds ([project-management:DEC-006-state-machine-and-cascade]);
- a release of a seat by force on a person's word ([project-management:DEC-059-topology-of-seats] point 5).

Under a credential that names no person they pass as they do elsewhere. Each is recorded as the acting account's act, with the caller's reason, and names no person as its authoriser (point 5).

This record guards none of them. Who may give that word in an agent's turn, such as a turn a chat started, is a record of its own ([pkit:ADR-091], Implications).

### 7. In a project with a topology, a clone under such a credential builds nothing

- **No seat that builds.** A worker's or a lead's seat rests on claims on Tasks that count (DEC-059 point 9), and such a clone's never do. So it takes no such seat (DEC-059 point 4).
- **No Task without a seat.** A clone with no seat marks no issue and is guarded by nothing (DEC-059 point 6). A Task it started would stand In Progress with no claim that counts, which a worker reads as ready to take over (DEC-059 point 7). So under such a credential `start-work` refuses.
- **A seat that builds nothing, where its claim counts.** An app's clone may hold a planner's seat, since its claim on the seat's state issue is its own account's. That claim counts only where DEC-058 point 4 counts its author: as a member where the gate is closed, and otherwise where the service answers that the account may write to the repository, which is unmeasured. An answer for such an account that the commands cannot read counts as a call that failed, and a failed call leaves the read incomplete and drops no claim ([pkit:ADR-071] point 3). Where the claim does not count, or the read is incomplete, the seat is not taken under that credential. Under an unresolved identity, the clone takes no seat.
- **A planner's filings** are assigned to the person the agent works for (point 3). Workers under that person's own credential take them. A worker under another person's credential meets `start-work`'s refusal, as it does with the filings of a planner under any one person's credential.

### 8. What stays unmet, and the setup's choice of credential

These needs stay unmet under a credential that names no person. Each is a limit, accepted with this record, stated by its property with what meeting it would cost ([pkit:ADR-091] point 4):

- **Instance ownership on issues of work,** and so building in a project with a topology. Meeting it would count a claim from an account that names no person, which loosens DEC-043 point 3: anyone holding the credential could then claim work for any person. That loosening is a person's decision of its own.
- **Two sessions under one such credential, kept off one Task.** Meeting it needs a mark that such a clone makes and that other such clones read, a design of its own.
- **The closed membership gate under an unresolved identity.** Meeting it needs the service's positive answer for the credential (point 1).

A setup that needs one of them gives the agent another credential:

- **A credential that names the person the agent works for,** which the measured setup offers and which no command has run under yet. The commands then act as the person, and the agent's pull requests are the person's own, which the person cannot approve (DEC-028, "Self-approval degrade").
- **A machine user,** which is not recommended. The commands act as it as they act as a person, so the assignee would name no person responsible for the work (DEC-019).

Which credential an agent holds is its setup's choice ([pkit:ADR-091] point 7).

### What this overturns, and what stands

This record overturns parts of DEC-021, DEC-022 and DEC-052, each under a credential that names no person. Each record stays accepted, and each overturned passage stays in it as it stood, under a top line that names this record (Implications).

- **Overturned in DEC-021:**
  - in "Identity resolution", git's email and `PM_INVOKER_LOGIN`, items 2 and 3, as sources of the acting account's identity, with the match on any surface's value so far as it lets either of them stand for that account. The acting account is the app's, by its login, or none the commands know (points 1 and 2 here).
  - item 3's reservation of the variable for CI and agent contexts where the natural sources do not apply. The variable names the person the agent works for, and grants nothing (point 3 here).
  - in the Implications' "CI invocations", a workflow that passes the gate by setting the variable from a CI secret. It passes the closed gate only where its own account is a member (point 2 here).
  - "Bootstrap: the first member self-adds", "Membership change authority", and the "Tooling surface"'s `add-member.py` and `remove-member.py`, so far as they let such an account add or remove a member, while the gate is open too. A person changes the list under their own credential (point 2 here).
- **Stands in DEC-021:** the gate, its two modes, the member list's shape and the recovery from a lockout. Every source of identity stands where the service answers with a user's account, and [project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175) settles how DEC-021 reads them there. Every source stands as DEC-021 states it where the service cannot be asked at all. A service identity added to the member list like any other member stands, as point 2 here has it.
- **Overturned in DEC-022:** in "Authority", a scheduled workflow that passes the closed gate by `PM_INVOKER_LOGIN` set from a CI secret, and the same variable in the Implications' "Membership gate (DEC-021)". The workflow passes only where its own account is a member (point 2 here).
- **Stands in DEC-022:** the rest, the workflow's identity added to the member list among it.
- **Overturned in DEC-052:** in the Implications' refinement of DEC-049 point 4, the parenthetical that keeps the authoriser on a comment a bot posts. The only authoriser the commands know is the account that posts, so the comment names none (point 5 here).
- **Stands in DEC-052:** the rest, the roster's override row among it, which names the authoriser where the poster differs from them.
- **Stands in DEC-049, unedited:** point 4's rule, that the actor is the authoriser, kept only where the poster is someone else. Under such a credential the actor is the account that posts (point 2 here), so the rule names no authoriser.

## Rationale

**Why the commands never take the person's identity.** The commands know a person's identity only from a credential that names that person. Any other value that names the person is the caller's word. Acting as the person on that word would make each act of the account read as the person's own, in the tracker and in every check that reads it. Acting as the account the service names keeps that record true, since the service shows which account wrote each change.

**Why `PM_INVOKER_LOGIN` names no acting account, in CI as in a session.** Set to the person, it would let `start-work` write the person as assignee. Three things stand against it:

- **It names the person as the actor of every act.** Each override comment would name the person as its authoriser, beside the account that posted it (DEC-052), whether or not the person authorised anything.
- **It hands the engine's gate the wrong actor.** The gate would compare the person with the account that merged, so the agent's own merge would read as another authority's (COR-033 P4).
- **It would not make a claim count.** The ownership fold reads who wrote a claim, never the variable (DEC-043 point 3). So instance ownership stays out of reach.

DEC-021 meant to keep the variable from a value the user controls, and trusted a CI workflow to keep it so. The commands cannot tell whether it did, under any credential. A workflow's input is typed by whoever dispatches the run, and an earlier step can set the environment of later ones. A pipeline that runs an agent's session on one prompt is both a CI workflow and an agent's session. So under a credential that names no person, the variable is read the same way in both: as the caller's word, where the caller's word grants nothing. Under a credential that names a person, the variable keeps the place DEC-021 gives it, and [project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175) settles how DEC-021 reads that place.

**Why a partial supersession, not a refinement.** DEC-021 decided outright, in item 3 and in its Implications, that a CI workflow may pass the gate by the variable, and DEC-022 decided the same for its scheduled workflow. DEC-052 decided outright that a comment a bot posts keeps the authoriser beside it. This record decides otherwise in the very case each provision was written for, so it overturns each in part. DEC-021 left the edge cases of identity resolution to its implementation (Rationale, "Why mechanism details are deferred"), which covers the order in which the sources are read, but not a provision its Implications make or a context it reserves a source for. The rest of each record stands, so none is replaced whole, and each states what it decides for every other credential.

**Why git's email does not stand for the account.** Under any credential the email is a value the user controls, and that hole is no question of this record's ([project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175)). Under a credential that names no person, there is a reason of its own: the email names a person the credential does not act as.

**Why the person the agent works for grants nothing.** Most of what the commands do with a person's login says whose the work is: the assignee at filing, and whether a Task is someone else's. A wrong value there misleads, and grants nothing, since a claim, an approval and membership are each read from the account that wrote or acts, never from the assignee. A command that takes an assignee from the caller, when a person files for another, takes the caller's word the same way.

**Why `start-work` keeps its refusal.** Without a person to compare with, an account that names no person is nobody's assignee. The refusal would then either catch every assignee, as on the trial, or none, which would let an agent start any member's Task. The refusal is a mistake-catcher, as are its neighbours (DEC-058 point 5, and DEC-059's release by force, which "catches mistakes, and it is no security boundary"). On the caller's word, it keeps catching the mistakes of agents that follow the procedure.

**Why the clash guard reads for such a clone.** A person's clone with no instance id may opt into ownership, and is guarded once it does (DEC-035 point 1). A clone under a credential that names no person cannot opt in, since none of its claims counts. Reading the owner is then the only guard it can have, and it grants nothing.

**Why the guards read the author's kind.** A claim means something because only the assignee's own account can make it (DEC-043 point 3). A guard derived from the service refusing a bot as an assignee would fail once a bot can be assigned, as GitHub lets its own coding agent be. Read from the author's kind, the guard holds for every bot, whatever the service lets it be. Counting a bot's claim for its assignee would let anyone who holds the credential claim work for any person.

**Why a bot approves nothing in human mode, in every project.** Human mode asks for a person's approval. DEC-026's Rationale counts the comment only from a commenter that is no bot, and its tables and the commands count it from any commenter but the author, a bot among them. Reading the author's kind brings the tables and the commands to the Rationale's rule on whose comment counts. It also leaves out the accounts the project registers as its reviewer agents', which name no person whatever the service reports. A request for changes still holds, since holding a merge back grants nothing.

**Why DEC-028's local path stands, for now.** DEC-028 rests the local path on the developer's attestation, the trust of a bypass, rather than on a trace from another authority. Under a credential that names no person, a bypass passes all the same (point 6). Refusing the local path would push such an agent to a bypass, which records less: no verdict, no reviewer, no head reviewed. Keeping it loosens nothing: under a person's credential, an agent's session already posts the verdict in the person's name, though the person attested nothing, and under a credential that names no person the verdict names no person, which is true. The reason lasts only while a bypass passes on the caller's word. Once the record on who may authorise in an agent's turn guards that word, the local path is the weakest way past the gate under such a credential, and is revisited.

**Why such a clone builds nothing in a topology.** A seat stays taken until it is released (DEC-059 point 5). A clone that took a building seat and could claim no Task would hold the seat while doing none of its work. A Task it started without a seat would read as ready to take over, and a worker would take it over from under the agent.

**Why act as the account, and not only state a limit.** The setup offers a credential that names the person, so every need could be a limit. But most of what the commands do needs no person at all. And under the person's credential, the agent's pull request is the person's own, which the person cannot approve (DEC-028, "Self-approval degrade"). Under an account that names no person, the person can approve it, by a review or an `Approved` comment. That is the trace from another authority that COR-033 P4 asks of a gate.

**Why building waits on where the reading lives.** The backbone reads the acting account too: the cross-authority gate's actor, where no command hands one, and the account `pkit report` posts as. Two readings of one credential can disagree, and at the engine's gate they already can. Where a command hands no actor and the backbone's own read fails, the gate's actor is a placeholder, and under an app's credential the two sides may spell one account two ways. In both cases the gate reads the agent's own merge as another authority's. A reading built in this capability first adds one more copy before its home is decided. A capability's script reaches the backbone only by command ([pkit:ADR-057] point 1), the backbone cannot depend on a capability a project may not install, and a computation keeps one home ([pkit:ADR-057] point 2). So the one home both can read lies outside this capability, and a record of the backbone's places it, as [pkit:ADR-061] placed the hosting service's acts.

### Alternatives considered

- **State a limit and nothing more:** the commands act only under a credential that names a person. The case: one sentence, and nothing to build. Rejected: most of what the commands do needs no person, and the person could not approve their agent's pull requests.
- **A limit, plus a mark the commands add to what an agent's session writes.** The case: no edits to other records, and instance ownership keeps working under the person's credential. Rejected: the mark is the session's own word, so the line it draws is weaker than the service's record of which account wrote, and the person still cannot approve the agent's pull requests.
- **`PM_INVOKER_LOGIN` names the acting account,** in an agent's session, or only in a CI workflow as DEC-021 provides. The case: `start-work` and `create-issue` work as under the person's credential, with nothing new, and this record would overturn nothing in DEC-021, DEC-022 or DEC-052. Rejected, for the reasons above, and because no line between a workflow and a session holds.
- **Refine DEC-021, DEC-022 and DEC-052 in place.** The case: each keeps stating its decision whole, and DEC-021 left identity resolution's edge cases to its implementation. Not taken: a refinement in place narrows, widens or completes a decision that stands, and the provisions this record reverses were each decided outright.
- **An interim reading in this capability, in one seam** that every comparison of accounts goes through, for [project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171) to move into the backbone later. The case: the capability's work starts at once, without waiting on a record of the backbone's, and the later move touches one seam. Not taken: until the move, two readings of one credential run side by side, and they already disagree at the engine's gate. The cost is a second copy of the reading, kept in step with the backbone's by hand until the move, and a spelling every comparison relies on, which changes again if the backbone settles another.
- **`start-work` works under whatever assignee the Task has,** with no person named. The case: nothing rests on the caller's word, and the setup gives nothing. Rejected: an agent could start any member's Task, which drops a mistake-catcher that costs one value to keep.
- **A setting kept for the clone names the person the agent works for,** written by the setup through a command, in place of the variable. The case: it lasts across sessions, and [pkit:ADR-091] point 7 names such a setting as what a setup writes. Not taken: it needs a command and a stored value of its own, a CI run would write it each time, and the variable already serves these contexts.
- **No clash guard for such a clone,** as for a person's clone with no instance id. The case: one rule for every clone with no id. Rejected: a person's clone can opt in and such a clone cannot, so without the read it would act on a Task another of the person's clones is building, with nothing to warn it.
- **Count a bot's claim for its assignee,** loosening DEC-043 point 3. The case: instance ownership, and building in a topology, under such a credential. Not taken: anyone holding the credential could claim work for any person, and loosening the guard is a person's decision.
- **Drop every review by a bot in human mode,** requests for changes included. The case: one rule for every bot review. Rejected: a bot's request for changes would stop holding a merge, which loosens a guard for no gain.
- **Treat only accounts the service records as bots as no person.** The case: one source for an account's kind. Rejected: a reviewer agent's machine user would then approve in human mode, and the project already names its reviewer agents' accounts (DEC-028), so leaving them out costs nothing.
- **Refuse DEC-028's local path under such a credential,** asking another account to post the verdict. The case: no verdict that the actor posts on its own pull request. Rejected: a bypass passes there all the same (point 6), and records less.
- **Read an app's credential from the service's refusal to look the account up.** The case: it is what the trial saw. Rejected: a refusal has other causes, and gives no account to act as.

## Implications

- **Top lines, once accepted.** Once a person accepts this record, the top lines of DEC-021, DEC-022 and DEC-052 each read *Partially superseded by [project-management:DEC-070-app-credentials]*, in the shape of DEC-035's line for DEC-059: one sentence of what this record decides there, the passages it overturns, what stands among the rest, and a pointer to this record's "What this overturns, and what stands". Each overturned passage stays as it stood, and no other word of the three records changes.
  - **DEC-021's line:** under a credential that names no person, neither git's email nor `PM_INVOKER_LOGIN` stands for the acting account, and no such account adds or removes a member. Overturned there: "Identity resolution"'s items 2 and 3, with its match on any surface, so far as they let either stand for that account; item 3's reservation of the variable for CI and agent contexts; the Implications' "CI invocations", so far as a workflow passes by the variable; and "Bootstrap", "Membership change authority" and the "Tooling surface", so far as they let such an account change the list. Among what stands: the gate, its modes and the list, and every source of identity where the service answers with a user's account or cannot be asked.
  - **DEC-022's line:** under a credential that names no person, the scheduled workflow passes the closed gate only where its own account is a member. Overturned there: "Authority"'s variable set from a CI secret, and the variable in the Implications' "Membership gate (DEC-021)". The rest stands.
  - **DEC-052's line:** under a credential that names no person, the authoriser the commands know is the account that posts, so an override comment names no person as its authoriser. Overturned there: the Implications' parenthetical that keeps the authoriser on a comment a bot posts. The rest stands, the roster's override row among it.
  - **DEC-049** takes no line and no edit, since its point 4 stands whole.
- **Refinements, once accepted.** Each record below is refined in place in this change, and each passage named takes the pointer `(refinement per [project-management:DEC-070-app-credentials])`:
  - **DEC-019, "Mandatory assignment" and its "Self-assignment shorthand":** the filer, whom the default at filing, the schema's `default_at_filing: filer` and the Context name, is the acting account resolved per DEC-021, and under a credential that names no person, the person the agent works for. That person is held to `values_constrained_to: members` as any assignee is, so is a member where the gate is closed. Without one, `create-issue` takes the assignee named in the call and refuses a filing that names none, and `assign-issue --me` refuses. No command makes an account that names no person an assignee.
  - **DEC-026:**
    - the `start-work` row of "The seven commands", and the assignee-conflict row of the "Sub-decisions index": under such a credential, `start-work` compares the Task's assignee with the person the agent works for, refuses another's Task as under a person's credential, assigns that person a Task with none, posts no claim, refuses a Task an instance owns, and refuses where the session names no person or the project has a topology;
    - the `done-work` row of "The seven commands", and the `done-work` approval-gate row of the "Sub-decisions index": in human mode, an `Approved` comment or an approving review counts only from an account the service records as no bot and the project does not register as a reviewer agent's;
    - the human-mode bullet of "Reviewer assignment", and the reviewer-assignment row of the "Sub-decisions index": human mode passes over an app's account in the member list;
    - the `handoff-issue` row of "The seven commands": a Task is never handed to an app's account.
  - **DEC-028, wherever its local path has the developer post or attest the verdict:** the Decision's top line, "Path 2: Local agent", "Invocation command (local path)", "Self-approval degrade", "Allowlist as attestation, not security", and the "Sub-decisions index"'s rows for the two paths, the local path's identity check and the allowlist. Each states it of the account that runs the command: a person's under a credential that names one, and under a credential that names no person, the account it acts as, whose verdict attests what that account ran and names no person responsible for it. The path rests on the trust of a bypass under either.
  - **DEC-035 point 1:** the presence of the id is the sole activation gate under a credential that names a person. Under one that names no person, a clone takes no part in instance ownership on issues of work, whatever id it holds, and the clash guard of point 6 reads the owner for it.
  - **DEC-043 point 3:** a marker counts only from the assignee's account, and never from an account the service records as a bot.
  - **DEC-058 point 4:** a comment an app's account writes on a state issue counts by the same test as any author's, as that account's own, and never as a person's.
  - **DEC-059 point 4:** a clone under such a credential takes no seat that builds. It takes a planner's seat only where its claim on the seat's state issue counts, as DEC-058 point 4 counts its author, and not where the read of that issue is incomplete. Under an unresolved identity it takes no seat. **Point 6:** a clone under such a credential that holds no seat starts no Task.
- **Architecture records, edited once accepted.** The architect, whose custody they are in, refines each in place in this change, with the same pointer:
  - **[pkit:ADR-041], points 1 and 2 and its Implications:** the ownership fold's filter keeps a marker only from the expected assignee's account, and never from an account the service records as a bot. So the shared reader gives each author's kind.
  - **[pkit:ADR-071] point 3:** an author's login is compared with the members' entries in one spelling. Where the gate is open, an answer about an author's write access that the seam cannot read for a bot counts as a call that failed, which leaves the read incomplete.
- **First, where the reading lives.** Building point 1, and every point that rests on it, waits on an accepted record that decides where the reading of the acting account lives, which [project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171)'s first question asks. What this record needs of it is that the account is read once, its kind only from the service's positive answer (point 1), and that every comparison of accounts uses one spelling (point 2). That record is the architect's to draft, and whether it is drafted now is a person's to decide. Before it, the answer of the service that tells an app's credential is measured under an installation's token (point 1). The guards of point 5 that read only an author's kind need no reading of the acting account, and may be built before it.
- **The work** is planned once this record and that one are accepted. It builds on the report of an unresolved identity that [project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162) adds. It covers points 1 to 7, with their messages and the tests that hold them, and:
  - the member list's description of a login, which names one lookup's spelling (point 2);
  - the one function that reads the person the agent works for (point 3);
  - the capability's README, which documents `PM_INVOKER_LOGIN` as an input of the commands, with what it names under each kind of credential (point 3);
  - the cross-repository guard, which stops reading the variable as a sign that nobody is at the terminal, and reads that from the session's process (point 3);
  - the pm skill's procedure on these refusals: the agent tells the person what the session lacks, and never sets a person's login as the acting account;
  - pkit's page on running with nobody at the terminal, which states the limits of point 8 with their costs ([pkit:ADR-091] point 7).

  It declares a `minor` change for project-management. It adds behaviour, and changes no installed file, name or schema, so it needs no migration. Three of its changes reach projects that run no agent under such a credential: a bot's approval in human mode, a closed-mode workflow that passes by the variable or by git's email, and a person's own credential whose lookup the service refuses. Each refuses more, or counts less, and its message names the way out. Whether any of them weighs as `major` is a person's judgment, made when the work's changeset is written.
- **Left out, for records of their own:**
  - **The backbone's own reads of who is acting,** such as the cross-authority gate's actor and the account `pkit report` posts as ([project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171)). Where a command hands the engine no actor, the backbone reads its own, and where that read fails, it takes a fixed placeholder as the actor. The gate then reads every merge, the agent's own included, as another authority's. That is the disagreement between two readings that [project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171) must settle, and the record above answers its first question.
  - **Who may authorise in a turn that a chat started** ([pkit:ADR-091], Implications), which decides the acts of point 6, and when DEC-028's local path is revisited (point 5).
  - **The person the agent works for, in the backbone.** One function of this capability reads it (point 3). The backbone already posts for a person an agent works for, in `pkit report`, and the record on who may authorise in a chat's turn needs that person too. A variable named for this capability is no name the backbone can depend on, so [project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171) or that record may lift the reading into the backbone.
  - **Git's email and `PM_INVOKER_LOGIN` beside a person's login** ([project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175)). Under a credential that names a person, DEC-021 reads git's email where the service's login is not available, and the variable third, where neither applies, and passes a match on any of them. The commands read the variable first, in place of the login, and let the email match a member beside a resolved login that is no member's. Which reading DEC-021 means holds on every machine, and is no question of a credential that names no person.
  - **Which `Approved` comment counts in human mode:** the last that is no bot's, as DEC-026's Rationale has it, or any but the author's, as its tables and the commands have it. That is no question of an account's kind, and this record leaves it as DEC-026 states it.
  - **How a read of the board tells a board that did not answer from one that answered empty,** under every credential, which [project-kit#3176](https://github.com/aleskalfas/project-kit/issues/3176) decides. An App installation's token is one credential that a user's board answers empty, with no error (Context). Whether an organisation's board answers to such a token is measured on [project-kit#3172](https://github.com/aleskalfas/project-kit/issues/3172).
- **This change** lands the record with a `none` changeset for project-management, since no behaviour changes until it is built. It needs no migration.
