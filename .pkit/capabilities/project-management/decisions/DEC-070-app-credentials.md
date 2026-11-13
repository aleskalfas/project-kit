---
id: DEC-070
title: Under a credential that names no person, the commands never act as one
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an agent may reach GitHub under a credential that names no person, such as a GitHub App installation's token or a CI workflow's. GitHub will not look such an account up as a user, and refuses it as an assignee.

Under such a credential, this capability's commands never take a person's identity for the account they act as, in a CI workflow and in an agent's session alike. Nothing an account that names no person writes counts as a person's claim on work or a person's approval, and no comment names a person as having authorised what it records. The person the agent works for, which the session names, serves only where naming a person grants nothing: as the default assignee, and to keep the agent off a Task assigned to someone else.

What a person accepting this weighs:

- **No instance ownership.** Such a clone claims no Task. In a project with a topology it builds nothing, and elsewhere two sessions under one such credential can start the same Task unseen.
- **Bots approve nothing in human mode.** In every project, an approval from an account GitHub records as a bot, or one the project registers as a reviewer agent's, does not count where a person's approval is required.
- **Closed-mode CI.** A workflow under its own token passes a closed membership gate only where its account is a member. Neither `PM_INVOKER_LOGIN` nor git's email stands for it.
- **Every board is checked first.** Under any credential, a command that reads or writes the project's board first confirms that the board answers, and refuses where it does not.
- **The caller's word stays unguarded.** A bypass, a held move or a release by force passes on the caller's word, as under any credential. Who may give that word in an agent's turn is a record of its own.

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

[project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162) has the commands report an identity they cannot resolve, with its cause. How they act under such a credential is this record's.

**What was measured** on the trial ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)):

- **The setup offers a credential that names the person.** It can grant the agent an OAuth sign-in or a personal access token beside the App's. Neither was granted to the trial's agent, so no command has run under one.
- **An app's credential saw none of a user's boards.** Asked for a user's boards, the person's own token, of a kind the measurement did not record, found three, one of them public. The App's token, under an App granted no project permission, found none, and gave no error.
- **An app's account is spelled differently on different surfaces.** Read under the person's credential, the comments the trial's App wrote give its login with a `[bot]` suffix and the type `Bot`, and name the App that performed each write. gh's JSON gives the same account, on its pull requests, with an `app/` prefix, marked as a bot.

**What was not measured:**

- **Whether an installation's token can learn its own account and kind.** Both attempts to ask from inside the trial's agent failed before reaching it. Point 1 says what holds without it.
- **Boards:** whether an organisation's board answers to an App granted access to it ([project-kit#3172](https://github.com/aleskalfas/project-kit/issues/3172)), how a configured board answers when it is out of reach, and which boards a fine-grained token, or a sign-in through a host's app, reaches. Point 8 rests on none of them.
- **Whether the service answers an app's account's write access to a repository,** which an open project's state issues read (point 7).
- **Whether a person's sign-in through a host's app marks the agent's writes as that app's.**

**What the records already say.**

- **The membership gate takes `PM_INVOKER_LOGIN` in CI and agent contexts,** sourced from a CI secret or a workflow input, never from a value the user controls (DEC-021, "Identity resolution"). The commands cannot tell where the variable was set.
- **A claim on an issue of work counts only from the assignee's account** ([project-management:DEC-043-ownership-substrate-selection] point 3). The ownership fold applies that filter in one place ([pkit:ADR-041]).
- **A gate's authorisation comes from another authority than the actor it gates** ([pkit:COR-033] P4).
- **In human mode, an `Approved` comment counts from the last commenter that is no bot** (DEC-026, Rationale, "Why the three-way OR"). The commands count it from any commenter but the author.
- **A comment names who authorised an act** where they differ from the account that posted it ([project-management:DEC-052-comment-house-style]).
- **A need that differs between machines is met by a property,** never by a host's name. A need not worth meeting is a limit, stated by its property with what meeting it would cost ([pkit:ADR-091] points 2 and 4).

## Decision

**Under a credential that names no person, this capability's commands never take a person's identity for the account they act as. Nothing an account that names no person writes counts as a person's claim or approval, and no comment names a person as its authoriser. The person the agent works for serves only where naming a person grants nothing. Under every credential, a board is used only where the credential reaches it.**

### 1. The commands read a credential's kind from the service's answer

- **An app's, only from a positive answer.** A credential is an app's only where the hosting service answers, for the credential, that its account is an app's, and gives its login. It is never read from a refusal, whose cause may be a rate limit, a suspended account or a network's rule as well as an app. Nor is it read from the host or the tool that issued the credential ([pkit:ADR-091] point 2).
- **Any other answer that names no person** leaves the identity unresolved, and the commands act on it as on an app's credential with no account they know.
- **Only a grant needs the app's own account.** The membership gate (point 2) and a seat's claim (point 7) read the app's login, since they grant the acting account something. Everything else this record decides holds under an unresolved identity too. So an answer misread grants nothing, and never lets a person's identity stand for the acting account.
- **Each guard reads the property it rests on:** the credential's answer for the acting account, the service's record of an author for what that author wrote (point 5), and the board's answer for the board (point 8).

Whether an installation's token receives a positive answer is unmeasured. Where it does not, such a token leaves the identity unresolved: everything below holds, except that its account can be neither a member (point 2) nor a seat's holder (point 7).

### 2. No person stands for the acting account

Under a credential that names no person, in a CI workflow and in an agent's session alike:

- **The acting account** is the app's, by the login the service gives it. Under an unresolved identity, the commands know no acting account.
- **One spelling.** An app's account is compared in one form, whichever surface named it: the member list, a claim's author, a review's author.
- **Git's configured email does not stand for it.** The email names whoever set up git on the machine, a person the credential does not act as.
- **Nor does `PM_INVOKER_LOGIN`.** Whoever starts the run or the session can set it, and the commands cannot tell who did. It names the person the agent works for (point 3).
- **The closed membership gate** matches an app's account by its login alone. A project lets such an account act by adding it as a member. That admits every session that holds the credential, whoever starts it, and the project decides so by adding it.
- **The member list changes under no such credential.** Membership grants authority, and an account that names no person has no one to stand behind a change to it. So a command that adds or removes a member refuses, and a person changes the list under their own credential. This holds while the gate is open too, where adding such an account as the first member would close the gate with no person in it.
- **An app's account in the member list is no person.** Where a command picks members as people, such as reviewers in human mode, it passes over an app's account.

Under a credential that names a person, this record changes nothing in how the acting account is resolved.

### 3. The person the agent works for serves only where naming a person grants nothing

- **Where it comes from.** Under a credential that names no person, `PM_INVOKER_LOGIN` names the person the agent works for. The setup sets it, as it sets whatever else the session needs ([pkit:ADR-091] point 7).
- **Where it serves.** It stands where the commands would name the acting account as a person, and grant nothing by doing so:
  - the default assignee at filing, and `--me` on an assignment (DEC-019);
  - `start-work`'s refusal of a Task assigned to someone else, and the assignee it writes (point 4);
  - which Tasks `next-task` hands out, since it hands out only what `start-work` takes.
- **Where it never serves.** It never stands where naming a person grants: the membership gate, a claim, an approval, or the authoriser a comment names. So `--me` on a command that changes the member list refuses (point 2).
- **Without it,** a command that needs a person refuses, and says that the account names no person and how the session can name one. `create-issue` still takes an assignee named in the call, as when a person files for another ([project-management:DEC-035-instance-ownership] point 5).

It is the caller's word, as an assignee the caller names is. Set wrongly, it lets the agent past the refusal that keeps it off another person's Task. Like DEC-035's clash guard, that refusal catches the mistakes of agents that follow the procedure, and is no security boundary.

### 4. `start-work` keeps its refusal, against the person the agent works for

Under a credential that names no person, in a project with no topology, `start-work`:

- **refuses a Task assigned to someone other than the person the agent works for,** and names `handoff-issue`, as DEC-026 has it;
- **assigns that person a Task with no assignee,** since DEC-019 needs one and the acting account cannot be it, and writes no assignee where that person is one already;
- **posts no claim,** since no claim it wrote would count (point 5);
- **refuses a Task an instance owns.** The clash guard reads the owner for such a clone, though the clone claims nothing. A reason overrides the refusal and posts an audit comment, as for any clash (DEC-035 point 6).

Every other ordinary lifecycle verb under such a credential reads the owner the same way. `handoff-issue` hands a Task from one person to another, and never to an app's account.

Two sessions under one such credential, working for one person, can start the same Task, since neither claims it. Nothing tells them apart, as nothing tells apart two of a person's clones with no instance id (DEC-035 point 1). This is a limit (point 9).

In a project with a topology, such a clone starts no Task (point 7).

### 5. Nothing an account that names no person writes counts as a person's

The commands read the kind of an author from the service's record of that author, which says whether it is a bot. These guards hold for every account the service records as a bot, under whatever credential the command runs, and whether or not the service lets that account be assigned:

- **A claim on an issue of work** counts only from the assignee's account (DEC-043 point 3), and never from a bot's. So a clone under a credential that names no person takes no part in instance ownership on issues of work.
- **An approval in human mode.** An `Approved` comment or an approving review counts only from an account the service records as no bot, and that the project does not register as a reviewer agent's ([project-management:DEC-028-agent-as-approver-paths], the remote path's list). A request for changes holds the merge whoever made it, since holding a merge grants nothing. So human mode's gate rests on another authority than the actor, as COR-033 P4 asks.
- **A reviewer agent's verdict** counts in agent mode as DEC-028's paths have it. Under a credential that names no person, the local path's verdict is posted by the acting account. It attests what that account ran, and names no person responsible for it.
- **An authoriser in a comment.** The authoriser the commands know is the acting account, which here names no person. So an override comment names no person as its authoriser (DEC-052). A reason the caller gives may report a person's word, and stays the caller's report.
- **A claim on a state issue** that an app's account writes is that account's own, and names no person ([project-management:DEC-058-state-issues] point 5). Point 7 says where it counts.

### 6. What passes on the caller's word stays as it is

Some acts pass on the caller's word under every credential: a merge by bypass, a move the user holds, a promotion on a person's request in the session, and a release of a seat by force on a person's word ([project-management:DEC-006-state-machine-and-cascade], DEC-026, [project-management:DEC-059-topology-of-seats] point 5). Under a credential that names no person they pass as they do elsewhere. Each is recorded as the acting account's act, with the caller's reason, and names no person as its authoriser (point 5).

This record guards none of them. Who may give that word in an agent's turn is a record of its own ([pkit:ADR-091], Implications, gap 5).

### 7. In a project with a topology, such a clone builds nothing

- **No seat that builds.** A worker's or a lead's seat rests on claims on Tasks that count (DEC-059 point 9), and such a clone's never do. So it takes no such seat (DEC-059 point 4).
- **No Task without a seat.** A clone with no seat marks no issue and is guarded by nothing (DEC-059 point 6). A Task it started would stand In Progress with no claim that counts, which a worker reads as ready to take over (DEC-059 point 7). So under such a credential `start-work` refuses.
- **A seat that builds nothing, where its claim counts.** An app's clone may hold a planner's seat, since its claim on the seat's state issue is its own account's. That claim counts only where DEC-058 point 4 counts its author: as a member where the gate is closed, and otherwise where the service answers that the account may write to the repository, which is unmeasured. Where the claim does not count, the seat cannot be taken under that credential. Under an unresolved identity, the clone takes no seat.
- **A planner's filings** are assigned to the person the agent works for (point 3). Workers under that person's own credential take them. A worker under another person's credential meets `start-work`'s refusal, as it does with the filings of a planner under any one person's credential.

### 8. A board is used only where the credential reaches it

Under every credential, a command that reads or writes the project's board first confirms that the service answers with the configured board under that credential (DEC-019, "Auto-add to board"). Only that answer counts. Where the service refuses, fails, or answers without the board, the command refuses before changing anything, and says that the board may be out of the credential's reach.

A board out of reach may answer empty rather than fail, as the listing of a user's boards did under an app's credential. Whether a read of the configured board does too is unmeasured. A command that read it empty would find no state, and might move an issue from a state it cannot see. A check that counts only a positive answer holds however a read out of reach answers, and under every kind of credential.

### 9. What stays unmet, and the setup's choice of credential

These needs stay unmet under a credential that names no person. Each is a limit, stated by its property with what meeting it would cost ([pkit:ADR-091] point 4):

- **Instance ownership on issues of work,** and so building in a project with a topology. Meeting it would count a claim from an account that names no person, which loosens DEC-043 point 3: anyone holding the credential could then claim work for any person. That loosening is a person's decision of its own.
- **Two sessions under one such credential, kept off one Task.** Meeting it needs a mark that such a clone makes and that other such clones read, a design of its own.
- **The closed membership gate under an unresolved identity.** Meeting it needs the service's positive answer for the credential (point 1).

Under every credential, a board the credential does not reach is refused (point 8). Meeting that needs a credential that reaches the board.

A setup that needs one of them gives the agent another credential:

- **A credential that names the person the agent works for,** which the measured setup offers and which no command has run under yet. The commands then act as the person, and the agent's pull requests are the person's own, which the person cannot approve (DEC-028, "Self-approval degrade").
- **A machine user,** which is not recommended. The commands act as it as they act as a person, so the assignee would name no person responsible for the work (DEC-019).

Which credential an agent holds is its setup's choice ([pkit:ADR-091] point 7).

## Rationale

**Why the commands never take the person's identity.** The commands know a person's identity only from a credential that names that person. Any other value that names the person is the caller's word. Acting as the person on that word would make each act of the account read as the person's own, in the tracker and in every check that reads it. Acting as the account the service names keeps that record true, since the service shows which account wrote each change.

**Why `PM_INVOKER_LOGIN` names no acting account, in CI as in a session.** Set to the person, it would let `start-work` write the person as assignee. Two things stand against it:

- **It names the person as the actor of every act.** Each override comment would name the person as its authoriser, beside the account that posted it (DEC-052), whether or not the person authorised anything.
- **It would not make a claim count.** The ownership fold reads who wrote a claim, never the variable (DEC-043 point 3). So instance ownership stays out of reach.

DEC-021 meant to keep the variable from a value the user controls, and trusted a CI workflow to keep it so. That line does not hold. A workflow's input is typed by whoever dispatches the run, and an earlier step can set the environment of later ones. A pipeline that runs an agent's session on one prompt is both a CI workflow and an agent's session ([pkit:ADR-091], Rationale, "Why the test should hold beyond DAM"). So the variable is read the same way in both: as the caller's word, where the caller's word grants nothing.

**Why git's email does not stand for the account.** Under any credential the email is a value the user controls, and that hole is no question of this record's. Under a credential that names no person, there is a reason of its own: the email names a person the credential does not act as.

**Why the person the agent works for grants nothing.** Most of what the commands do with a person's login says whose the work is: the assignee at filing, and whether a Task is someone else's. A wrong value there misleads, and grants nothing, since a claim, an approval and membership are each read from the account that wrote or acts, never from the assignee. A command that takes an assignee from the caller, when a person files for another, takes the caller's word the same way.

**Why `start-work` keeps its refusal.** Without a person to compare with, an account that names no person is nobody's assignee. The refusal would then either catch every assignee, as on the trial, or none, which would let an agent start any member's Task. The refusal is a mistake-catcher, as are its neighbours (DEC-058 point 5, and DEC-059's release by force, which "catches mistakes, and it is no security boundary"). On the caller's word, it keeps catching the mistakes of agents that follow the procedure.

**Why the clash guard reads for such a clone.** A person's clone with no instance id may opt into ownership, and is guarded once it does (DEC-035 point 1). A clone under a credential that names no person cannot opt in, since none of its claims counts. Reading the owner is then the only guard it can have, and it grants nothing.

**Why the guards read the author's kind.** A claim means something because only the assignee's own account can make it (DEC-043 point 3). A guard derived from the service refusing a bot as an assignee would fail once a bot can be assigned, as GitHub lets its own coding agent be. Read from the author's kind, the guard holds for every bot, whatever the service lets it be. Counting a bot's claim for its assignee would let anyone who holds the credential claim work for any person.

**Why a bot approves nothing in human mode, in every project.** Human mode asks for a person's approval. DEC-026 counts the comment from the last commenter that is no bot, and the commands count it from any commenter but the author. Reading the author's kind aligns the two. It also leaves out the accounts the project registers as its reviewer agents', which name no person whatever the service reports. A request for changes still holds, since holding a merge back grants nothing.

**Why DEC-028's local path stands.** DEC-028 rests the local path on the developer's attestation, the trust of a bypass, rather than on a trace from another authority. Under a credential that names no person, a bypass passes all the same (point 6). Refusing the local path would push such an agent to a bypass, which records less: no verdict, no reviewer, no head reviewed. What changes is that the attestation names no person, and point 5 says so.

**Why such a clone builds nothing in a topology.** A seat stays taken until it is released (DEC-059 point 5). A clone that took a building seat and could claim no Task would hold the seat while doing none of its work. A Task it started without a seat would read as ready to take over, and a worker would take it over from under the agent.

**Why the board is checked under every credential.** ADR-091 point 4 asks first for a change that is right on every machine. A board out of reach could answer empty under other credentials than an app's too, such as a fine-grained token, or a sign-in limited by the app it passed through, which is unmeasured. Keyed to the board, the check covers them. It also lets a board that an app does reach work at once, such as an organisation's if #3172 shows it, with nothing waiting on a record. The cost is one read before each command that touches the board.

**Why act as the account, and not only state a limit.** The setup offers a credential that names the person, so every need could be a limit. But most of what the commands do needs no person at all. And under the person's credential, the agent's pull request is the person's own, which the person cannot approve (DEC-028, "Self-approval degrade"). Under an account that names no person, the person can approve it, by a review or an `Approved` comment. That is the trace from another authority that COR-033 P4 asks of a gate.

### Alternatives considered

- **State a limit and nothing more:** the commands act only under a credential that names a person. The case: one sentence, and nothing to build. Rejected: most of what the commands do needs no person, and the person could not approve their agent's pull requests.
- **A limit, plus a mark the commands add to what an agent's session writes.** The case: no edits to other records, and instance ownership keeps working under the person's credential. Rejected: the mark is the session's own word, so the line it draws is weaker than the service's record of which account wrote, and the person still cannot approve the agent's pull requests.
- **`PM_INVOKER_LOGIN` names the acting account,** in an agent's session, or only in a CI workflow as DEC-021 provides. The case: `start-work` and `create-issue` work as under the person's credential, with nothing new. Rejected, for the reasons above, and because no line between a workflow and a session holds.
- **`start-work` works under whatever assignee the Task has,** with no person named. The case: nothing rests on the caller's word, and the setup gives nothing. Rejected: an agent could start any member's Task, which drops a mistake-catcher that costs one value to keep.
- **A setting kept for the clone names the person the agent works for,** written by the setup through a command, in place of the variable. The case: it lasts across sessions, and ADR-091 point 7 names such a setting as what a setup writes. Not taken: it needs a command and a stored value of its own, a CI run would write it each time, and the variable already serves these contexts.
- **No clash guard for such a clone,** as for a person's clone with no instance id. The case: one rule for every clone with no id. Rejected: a person's clone can opt in and such a clone cannot, so without the read it would act on a Task another of the person's clones is building, with nothing to warn it.
- **Count a bot's claim for its assignee,** loosening DEC-043 point 3. The case: instance ownership, and building in a topology, under such a credential. Not taken: anyone holding the credential could claim work for any person, and loosening the guard is a person's decision.
- **Drop every review by a bot in human mode,** requests for changes included. The case: one rule for every bot review. Rejected: a bot's request for changes would stop holding a merge, which loosens a guard for no gain.
- **Treat only accounts the service records as bots as no person.** The case: one source for an account's kind. Rejected: a reviewer agent's machine user would then approve in human mode, and the project already names its reviewer agents' accounts (DEC-028), so leaving them out costs nothing.
- **Refuse DEC-028's local path under such a credential,** asking another account to post the verdict. The case: no verdict that the actor posts on its own pull request. Rejected: a bypass passes there all the same (point 6), and records less.
- **Refuse a project with a board under an app's credential,** until an organisation's board is measured. The case: no new read under any credential, and nothing rests on how a board out of reach answers. Rejected: too broad, since it refuses a board an app does reach, and too narrow, since it misses any other credential that does not reach the board.
- **Read an app's credential from the service's refusal to look the account up.** The case: it is what the trial saw. Rejected: a refusal has other causes, and gives no account to act as.

## Implications

- **Edits once accepted.** Once a person accepts this record, each record below is refined in place in this change, with the pointer `(refinement per [project-management:DEC-070-app-credentials])`:
  - **DEC-019, "Mandatory assignment":** under a credential that names no person, the default assignee at filing and `--me` are the person the agent works for. Without one, `create-issue` takes the assignee named in the call and refuses a filing that names none, and `assign-issue --me` refuses. No command makes such an account an assignee. **"Auto-add to board":** under every credential, a command that reads or writes the board first confirms that the service answers with the configured board, and refuses before changing anything where it does not.
  - **DEC-021, "Identity resolution":** the service is asked first. Under a credential it answers as an app's, the identity is the app's account, by its login, compared in one spelling across surfaces. Under any other answer that names no person, the identity is unresolved. Under either, neither git's email nor `PM_INVOKER_LOGIN` stands for the acting account, in a CI workflow and in an agent's session alike, and the variable names the person the agent works for. **"Membership change authority":** under such a credential, a command that adds or removes a member refuses. **Implications, the CI invocations:** a workflow under a credential that names no person passes the closed gate only where its account is a member.
  - **DEC-022, "Authority":** the scheduled workflow, under a credential that names no person, passes the closed gate only where its account is a member, and `PM_INVOKER_LOGIN` does not stand for it.
  - **DEC-026:**
    - the `start-work` row of "The seven commands", and the assignee-conflict row of "Sub-decisions index": under such a credential, `start-work` compares the Task's assignee with the person the agent works for, refuses another's Task as under a person's credential, assigns that person a Task with none, posts no claim, refuses a Task an instance owns, and refuses where the session names no person or the project has a topology;
    - the `done-work` row of each table: in human mode, an `Approved` comment or an approving review counts only from an account the service records as no bot and the project does not register as a reviewer agent's;
    - "Reviewer assignment": human mode passes over an app's account in the member list;
    - the `handoff-issue` row: a Task is never handed to an app's account.
  - **DEC-028, "Path 2: Local agent":** under a credential that names no person, the verdict is posted by the acting account, attests what that account ran, and names no person responsible for it.
  - **DEC-035 point 1:** a clone under such a credential takes no part in instance ownership on issues of work, and the clash guard of point 6 reads the owner for it.
  - **DEC-043 point 3:** a marker counts only from the assignee's account, and never from an account the service records as a bot.
  - **DEC-052, the roster's override row:** under such a credential, the authoriser the commands know is the posting account, so the comment names no person as its authoriser.
  - **DEC-058 point 4:** a comment an app's account writes on a state issue counts by the same test as any author's, as that account's own, and never as a person's.
  - **DEC-059 points 4 and 6:** a clone under such a credential takes no seat that builds, and under an unresolved identity no seat at all. With no seat, it starts no Task.
- **The work** is planned once this record is accepted. It builds on the report of an unresolved identity that [project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162) adds. It covers points 1 to 8, with their messages and the tests that hold them, and:
  - first, which answer of the service tells an app's credential, measured under an installation's token (point 1);
  - the member list's description of a login, which names one lookup's spelling (point 2);
  - the pm skill's procedure on these refusals: the agent tells the person what the session lacks, and never sets a person's login as the acting account;
  - pkit's page on running with nobody at the terminal, which states the limits of point 9 with their costs ([pkit:ADR-091] point 7).

  It declares a `minor` change for project-management. It adds behaviour, and changes no installed file, name or schema, so it needs no migration. Three of its changes reach projects that run no agent under such a credential: a bot's approval in human mode, a closed-mode workflow that passes by the variable or by git's email, and the read before each board command. Each refuses more, or counts less, and its message names the way out. Whether any of them weighs as `major` is a person's judgment, made when the work's changeset is written.
- **Left out, for records of their own:**
  - **The backbone's own reads of who is acting,** such as the cross-authority gate's default actor and the account `pkit report` posts as ([project-kit#3171](https://github.com/aleskalfas/project-kit/issues/3171)). They need point 1's reading too, and two readings of one credential could disagree. Whether one reading serves both, and where it lives, is that issue's first question, and an architectural one.
  - **Who may authorise in a turn that a chat started** ([pkit:ADR-091], Implications, gap 5), which decides the acts of point 6.
  - **Git's email and `PM_INVOKER_LOGIN` beside a person's login.** Under a credential that names a person, DEC-021 lets the email match a member the resolved login does not, and the variable take the login's place. That holds on every machine, and is no question of a credential that names no person.
  - **An organisation's board under an app's credential,** measured on [project-kit#3172](https://github.com/aleskalfas/project-kit/issues/3172). Point 8 waits on nothing from it: it tells whether such a setup can use a board at all.
- **This change** lands the record with a `none` changeset for project-management, since no behaviour changes until it is built. It needs no migration.
