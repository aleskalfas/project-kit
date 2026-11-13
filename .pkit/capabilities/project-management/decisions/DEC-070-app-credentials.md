---
id: DEC-070
title: Under an app's credential, the commands act as the app and never as a person
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an agent may reach GitHub under an app's credential, such as a GitHub App installation's token or a CI workflow's. Such a credential acts as an account that names no person. GitHub will not look that account up as a user, and refuses it as an assignee.

Under such a credential, this capability's commands act as the app's account, and never take a person's identity in its place. Nothing that account writes counts as a person's claim, approval or authorisation. A command that needs a person takes one named in the call where naming them grants nothing, and otherwise refuses and says why. A project with a board is left out for now, and its commands refuse under such a credential. A setup that needs more gives the agent a credential that acts as the person it works for.

## Context

**The terms.**

- **A credential acts as an app** where the hosting service reports that the account it acts as is an app's, not a user's. On GitHub, an App installation's token and a CI workflow's token do. GitHub answers a request to look such an account up as a user with `Resource not accessible by integration (HTTP 403)`, and refuses it as an assignee.
- **The app's account** is the account such a credential acts as. It names no person.
- **A user account kept for an agent,** a machine user, is a user's account. pkit acts as it as it acts as a person's, and this record does not reach it.
- **The person the agent works for** is whoever directs the agent.

**What happens today.** On a trial of an agent host, an agent reached GitHub under an App installation's token ([project-kit#3004](https://github.com/aleskalfas/project-kit/issues/3004)). The commands resolve the acting account by looking it up as a user ([project-management:DEC-021-team-membership-gate], "Identity resolution"), and that lookup fails.

- **No default assignee.** `create-issue` cannot default the assignee to the filer ([project-management:DEC-019-mandatory-issue-state], "Mandatory assignment").
- **Every assignee is someone else.** `start-work` refuses every Task assigned to the person the agent works for, and sends it to `handoff-issue`, which cannot help ([project-management:DEC-026-work-ownership-lifecycle]).
- **A workaround.** The trial went on by unassigning the person, starting the work, and assigning the person back.

pkit is to report an identity it cannot resolve, with its cause, rather than act as if the account were someone else ([project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162)). How such an account should act is this record's.

**What was measured.** Two facts were measured on the trial before this record was drafted ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)):

- **A credential that acts as the person is on offer.** The host's setup can grant the agent an OAuth sign-in or a personal access token beside the App's. Under either, pkit acts as on the person's own machine, and every comment and pull request reads as the person's own.
- **An app's credential sees no board a user owns.** Asked for the person's boards, the person's token found three, and the App's token none, with no error. An organisation's board, under an App granted access to organisation projects, was not measured.

**What the records already say.**

- **No identity comes from a value the user controls.** DEC-021 takes `PM_INVOKER_LOGIN` only from a CI secret or a workflow input.
- **A claim on an issue of work counts only from the assignee's account** ([project-management:DEC-043-ownership-substrate-selection] point 3). The ownership fold applies that filter in one place ([pkit:ADR-041]).
- **A gate's authorisation comes from another authority than the actor it gates** ([pkit:COR-033] P4).
- **A comment names who authorised an act** where they differ from the account that posted it ([project-management:DEC-052-comment-house-style]).
- **A state issue counts a comment from any account that may write** ([project-management:DEC-058-state-issues] point 4).
- **A need that differs between machines is met by a property,** never by a host's name. A need not worth meeting is a limit, stated by its property ([pkit:ADR-091] points 2 and 4).

## Decision

**Under a credential that acts as an app, this capability's commands act as the app's account, and never take a person's identity in its place. Nothing that account writes counts as a person's claim, approval or authorisation. A command that needs a person takes one named in the call where naming them grants nothing, and otherwise refuses and says why. A project with a board is left out for now, and under such a credential its commands refuse.**

### 1. pkit reads the property from the hosting service

A command knows that its credential acts as an app from what the hosting service answers, such as GitHub's refusal to look the account up as a user. It never knows it from the host or the tool that issued the credential ([pkit:ADR-091] point 2). The report of an identity pkit cannot resolve carries this cause ([project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162)), and the points below act on it.

### 2. The acting account is the app's, and no person stands in for it

Under such a credential, the identity DEC-021 resolves is the app's account, except where a CI workflow names another as DEC-021 provides:

- **Its login** is the one the hosting service gives that account. Where it gives none, the identity is unresolved, and pkit reports it with its cause.
- **Git's configured email does not stand for it.** The email names whoever set up git on the machine, a value the user controls. So where the membership gate is closed, it matches the app's account alone. A project lets an app's account act by adding it as a member, as DEC-021 adds a CI's service identity.
- **No agent's session sets `PM_INVOKER_LOGIN`.** An agent can set its session's environment for any command, so a value set there is one the user controls, which DEC-021 rules out. pkit cannot tell where the variable was set, so this binds the agent and the setup that starts its session.
- **A CI workflow keeps the variable,** set from a CI secret or a workflow input as DEC-021 provides. Where it names a user's account, pkit acts as that account, and points 3 and 4 do not apply.

### 3. Nothing defaults to a person

The app's account is never an assignee, since the hosting service refuses it. So under such a credential, a command never makes the acting account an assignee:

- **`create-issue`** takes the assignee named in the call. It refuses a filing that names none, and says that the account names no person. Filing so is filing for another, as a person may ([project-management:DEC-035-instance-ownership] point 5).
- **`assign-issue --me`** refuses, for the same reason.

Naming the assignee grants the app's account nothing. The assignee names who is responsible for the issue (DEC-019), and only the assignee's own account can claim it (point 5).

### 4. `start-work` works under the assignee the Task has

Under such a credential, `start-work` writes no assignee, and counts no assignee as someone else. It refuses a Task with no assignee, since DEC-019 needs one and the account cannot be it, and it names `assign-issue`. The assignee stays the person responsible for the Task, as DEC-019 keeps the filer responsible until the issue is reassigned.

Every other command that compares the acting account with an assignee reads an app's account the same way, as neither the assignee nor another person. `handoff-issue` hands a Task from one person to another, and never to the app's account.

### 5. Nothing the app's account writes counts as a person's

A comment or a review that the app's account writes is that account's. It never stands for a person's claim, approval or authorisation, since an actor never authorises itself through another's name ([pkit:COR-033] P4). This record keeps the guard the records state, and loosening it is a person's decision of its own:

- **A claim on an issue of work.** A claim counts only from the assignee's account (DEC-043 point 3, [pkit:ADR-041]), and the app's account is never one. So a clone under such a credential takes no part in instance ownership on issues of work, and posts no claim.
  - **With no topology,** a command acts as for a clone with no instance id ([project-management:DEC-035-instance-ownership] point 1), and says why.
  - **With a topology,** the clone takes no seat whose role builds, since such a seat's work rests on claims that count ([project-management:DEC-059-topology-of-seats] point 9).
- **A claim on a state.** A claim the app's account writes on a state issue is that account's own, and names no person (DEC-058 point 4). So the app's account may hold a state as itself, such as a planner's seat.
- **An approval.** In `done-work`'s human mode, an `Approved` comment or an approving review counts only from a user's account, never from an app's. A reviewer agent's verdict is no person's approval, and DEC-028's paths count it as they stand ([project-management:DEC-028-agent-as-approver-paths]).
- **An authorisation in a comment.** The authoriser pkit knows is the acting account, here the account that posts. So an override comment names no person as its authoriser (DEC-052). A reason the caller gives may report a person's word, and stays the caller's report alone.

### 6. A project with a board is left out for now

An app's credential reaches no board a user owns, and the hosting service says nothing of it: the board is simply absent from its answers. Whether such a credential reaches an organisation's board, once its app is granted that access, is unmeasured.

So this record decides how the commands act only in a project with no board (DEC-019, "Auto-add to board"). In a project whose configuration names a board, a command that reads or writes the board refuses under such a credential, before it changes anything. It says that the board may be out of the credential's reach. A record of its own decides what the commands do there, once an organisation's board is measured.

### 7. Where a need stays unmet, the setup chooses the credential

Two needs stay unmet under such a credential, each a limit stated by its property ([pkit:ADR-091] point 4):

- **Work a clone owns on an issue of work,** and so a seat that builds. Meeting it would loosen the guard of point 5, which is a person's decision.
- **A project with a board.** Meeting it waits on a measurement and a record (point 6).

A setup that needs them gives the agent a credential that acts as the person it works for, which the measured setup offers. pkit then acts as on the person's own machine, and everything the agent writes reads as that person's. Which credential an agent holds is its setup's choice ([pkit:ADR-091] point 7).

## Rationale

**Why the app's account, and never the person.** pkit knows a person's identity only from a credential that acts as that person. Any other value that names the person is the caller's word. Acting as the person on that word would make each act of the app's account read as the person's own, in the tracker and in every check that reads it. Acting as the app's account keeps that record true, since the hosting service shows which account wrote each change.

**Why `PM_INVOKER_LOGIN=<person>` is not enough.** Set in the session, it would let `start-work` write the person as assignee. Three things stand against it:

- **It names the person as the actor of every act.** Each override comment would name the person as its authoriser, beside the app's account that posted it (DEC-052), whether or not the person authorised anything.
- **It is a value the user controls.** DEC-021 takes the variable from a CI secret or a workflow input, which what runs cannot change. An agent sets its session's environment at will, so no session meets that rule.
- **It still would not make a claim count.** The ownership fold reads who wrote a claim, never the variable (DEC-043 point 3). So instance ownership stays out of reach.

**Why the call names the assignee.** The assignee says who is responsible, and grants nothing: no claim, approval or authorisation follows from it. A caller already names an assignee when it files for another. A setting that named the person on each machine would make a value the user controls the default person. A project setting is the same on every clone, while the person differs from clone to clone ([pkit:ADR-091] point 5).

**Why `start-work` goes on under the assignee.** The refusal keeps one person off another's work, and points them to a handover. The app's account is no person, so it rivals nobody, and no handover can make it the assignee. The cost is that an agent may start a Task assigned to someone it does not work for. pkit could check that only against the caller's word, and the membership gate already decides which accounts may act at all.

**Why the guard stays.** A claim means something because only the assignee's own account can make it (DEC-043 point 3). Counting an app's claim for the assignee would let anyone who holds the credential claim work for any person. An approval or an authorisation that the actor writes for a person is the self-authorisation COR-033 P4 rules out.

**Why a building seat is refused, not only its claims.** A seat stays taken until it is released (DEC-059 point 5). A clone that took a building seat and could claim no Task would hold the seat while doing none of its work.

**Why a project with a board refuses.** A board the credential cannot see answers as empty. A command reading it would find no state, and might move an issue from a state it cannot see, or report a filed issue missing from the board. A refusal costs such a project its app's credential until a record decides otherwise, and misleads nobody.

**Why not only a limit.** The first measurement allows a shorter record: since the setup can offer the person's credential, every need could be a limit. But most of what the commands do needs no person at all. Under the person's credential, nothing the agent writes can be told from the person's own. Acting as the app's account keeps that line visible, and costs a few refinements.

### Alternatives considered

- **State a limit and nothing more:** the commands act only under a credential that acts as a person. Rejected: most of what they do needs no person, and the person's credential hides which acts were the agent's.
- **Set `PM_INVOKER_LOGIN` to the person.** Rejected, for the three reasons above.
- **A setting on each machine that names the person the agent works for,** as the default assignee and as `--me`. Rejected: a value the user controls would stand for a person by default, and the call names the assignee at no cost.
- **Count an app's claim for the assignee,** loosening DEC-043 point 3. Not taken: it would let anyone holding the credential claim for any person, and loosening the guard is a person's decision.
- **Give `start-work` the person the agent works for,** and refuse a Task assigned to anyone else. Rejected: the check would rest on the caller's word alone, a flag that guards nothing.
- **Act in a project with a board as elsewhere.** Rejected: a board out of reach answers as empty, so a command would act on state it cannot see.

## Implications

- **Edits once accepted.** Once a person accepts this record, each record below is refined in place in this change, with the pointer `(refinement per [project-management:DEC-070-app-credentials])`:
  - **DEC-019, "Mandatory assignment":** under a credential that acts as an app, the filer is no person. So `create-issue` takes the assignee named in the call and refuses without one, and `assign-issue --me` refuses. "Auto-add to board" says such a credential leaves a project with a board to a record of its own, and its commands refuse there.
  - **DEC-021, "Identity resolution":** under such a credential, the identity is the app's account, by the login the hosting service gives it. Git's configured email does not stand for it, and no agent's session sets `PM_INVOKER_LOGIN`.
  - **DEC-026:** the `start-work` row of "The seven commands", and the assignee-conflict row of "Sub-decisions index", say that under such a credential `start-work` writes no assignee, counts none as someone else, and refuses a Task with none. The `done-work` row of each table says that in human mode an `Approved` comment or an approving review counts only from a user's account, never from an app's.
  - **DEC-035 point 1:** a clone under such a credential takes no part in instance ownership on issues of work, as a clone with no instance id.
  - **DEC-043 point 3:** an app's account is never an assignee, so no marker it writes counts.
  - **DEC-052, the roster's override row:** under such a credential, the authoriser pkit knows is the posting account, so the comment names no person as authoriser.
  - **DEC-058 point 4:** a claim an app's account writes on a state issue counts as that account's own, never a person's.
  - **DEC-059 point 4:** a clone under such a credential takes no seat whose role builds.
- **The work** is planned once this record is accepted. It builds on the report of an unresolved identity that [project-kit#3162](https://github.com/aleskalfas/project-kit/issues/3162) adds, whose cause tells an app's credential apart (point 1). It covers points 2 to 6, with their messages and the tests that hold them. It changes how the commands act under an app's credential, so it declares a `minor` change for project-management.
- **Left out, for records of their own:**
  - **The backbone's own reads of who is acting,** such as the cross-authority gate's default actor and the account `pkit report` posts as. A follow-up issue holds them.
  - **Who may authorise in a turn that a chat started** ([pkit:ADR-091], Implications, gap 5).
  - **A project with a board under such a credential,** once an organisation's board is measured (point 6). A follow-up issue holds it.
- **This change** lands the record with a `none` changeset for project-management, since no behaviour changes until it is built. It needs no migration.
