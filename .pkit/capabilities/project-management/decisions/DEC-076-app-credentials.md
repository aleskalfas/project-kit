---
id: DEC-076
title: Under a credential that names no user's account, no person stands for the acting account
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an agent may reach GitHub under a credential that GitHub does not answer for as a user's account, such as an App installation's token or a CI workflow's. Under such a credential, the commands take no person's identity for the account they act as: neither git's email nor `PM_INVOKER_LOGIN` passes that account at the membership gate, and the variable names only the person the agent works for, who serves where naming a person grants nothing, such as the default assignee. Such a clone claims no Task, builds nothing in a project with a topology, and changes no member list. Where GitHub gives no answer about a credential, a person's own among them, the commands treat it the same way. Each act's actor follows [project-management:DEC-078-one-actor-per-act], and whether an account is a bot's follows [project-management:DEC-079-bots-are-no-person].

## Context

**The terms.** Asking the hosting service which account a credential acts as has three outcomes, as [project-management:DEC-073-reads-take-no-gate] point 2 tells them apart:

- **A credential names a user's account** where the service answers with a user's account.
- **An app's credential** is one for which the service answers that its account is no user's: with an app's account and its login, or by refusing the request for the account because the credential is an integration's, which it tells by its status and words, and which gives no login.
- **An unresolved identity** is the outcome where the service gives no answer about who the credential is, for any of the causes DEC-073 point 2 names, a rate limit and a credential it does not accept among them. A person's own credential leaves the identity unresolved wherever the service gives no answer for it, and without that answer the commands cannot tell an app's credential from a person's.
- **A credential names no user's account,** as in DEC-073, wherever the service does not answer that it acts as a user's account: an app's credential, and an unresolved identity.
- **An app's account** is the account an app's credential acts as.
- **The commands know no acting account** under an app's credential whose login the service does not give, and under an unresolved identity (DEC-078).
- **A user account kept for an agent,** a machine user, is a user's account, so its credential names a user's account.
- **The person the agent works for** is the person whose work an agent's session does, or a workflow's run where no agent runs in it, as the session or the run names them (point 3).
- **The setup** is what prepares the machine and starts the agent's session or the workflow, outside this capability.

**What happens today.** On a trial of software that starts agent sessions on hosted machines, an agent reached GitHub under an App installation's token ([project-kit#3004](https://github.com/aleskalfas/project-kit/issues/3004)). The commands resolve the acting account by looking it up as a user ([project-management:DEC-021-team-membership-gate], "Identity resolution"), and the service refuses the lookup as an integration's, `Resource not accessible by integration (HTTP 403)` ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)):

- **No default assignee.** `create-issue` cannot default the assignee to the filer ([project-management:DEC-019-mandatory-issue-state], "Mandatory assignment").
- **Every assignee is someone else.** `start-work` refuses every Task assigned to the person the agent works for, and sends it to `handoff-issue`, which cannot help ([project-management:DEC-026-work-ownership-lifecycle]). The trial went on by unassigning the person, starting the work, and assigning the person back.
- **The person as the actor.** Where `PM_INVOKER_LOGIN` names the person, the commands hand that person to the engine's gate as each move's actor, so the agent's own merge reads as another authority's.

**What was measured** on the trial ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)):

- **A credential that names the person's account is on offer.** The setup can grant the agent an OAuth sign-in or a personal access token beside the App's.
- **An installation's token sees none of a user's boards.** Asked for the boards of the person's account, it answered with none and no error, where the person's own token saw three.

**What was not measured:**

- Whether an installation's token, a workflow's among them, can learn its own account's login.
- Whether the service answers an app's account's write access to a repository, and gives every reader the same answer (point 6).
- Whether a person's sign-in through a host's app marks the agent's writes as that app's.

**What the records say.**

- **The membership gate** reads the account `gh api user` gives first, git's email second, as a fallback "when `gh` is unavailable", and `PM_INVOKER_LOGIN` third, reserved for CI and agent contexts and "sourced from a CI secret or workflow input, never from user-controllable env" (DEC-021, "Identity resolution"). Where the service answers with a user's account, its login alone is the invoker's identity, for the gate and for every other reader. Where it does not, a match at the gate on any of the three passes, and DEC-021 leaves to evidence of its own whether git's email and the variable name the invoker for the other readers (its Rationale, "Why a user's login the hosting service answers stands alone"). Its Implications let a CI workflow whose credential the service does not answer for as a user's pass the gate by setting the variable from a CI secret.
- **Instance ownership.** A clone with no instance id behaves as if instance ownership were not there, with no guard, and the id is the sole activation gate ([project-management:DEC-035-instance-ownership] point 1). In a project with a topology, a clone that holds no seat marks no issue and is guarded by nothing ([project-management:DEC-059-topology-of-seats] point 6).

**A rule held provisionally.** project-kit's own record on agent hosts holds that a need that differs between machines is met by reading a property, never a host's name, that a need not worth meeting is a limit, stated by its property with what meeting it would cost, and that a setup uses pkit's public surface as any adopter does and its choices are its own ([pkit:ADR-091] points 2, 4 and 7). It holds those rules provisionally, and they reach no adopter as rules, so this record states for itself what it takes from them.

## Decision

**Where the hosting service does not answer that a credential acts as a user's account, the commands take no person's identity for the account they act as, and the person the agent works for serves only where naming a person grants nothing.**

Where the service answers with a user's account, this record changes nothing in the identity the membership gate checks, which DEC-021 takes as that account's login alone.

### 1. The commands read a credential's kind from the service's answer

- **One reading, in one home.** Which account a credential acts as, and of which kind, is read once from the hosting service, and every command of this capability takes it from that reading. The backbone reads the acting account too, so the reading lives in one home outside this capability, which a record of the backbone's places.
- **An app's, only from the service's answer:** an app's account with its login, or a refusal of the request for the account because the credential is an integration's, as DEC-073 point 2 reads it. Where the service refuses `gh api user` so, the app's login comes from another request that answers with an app's account and its login, where the service gives one. A credential is never read as an app's from a refusal for another cause, from the credential's own form, or from the host or the tool that issued it.
- **No answer leaves the identity unresolved,** under every credential, and the commands act on it as on an app's credential whose account they do not know. They never fall back to a value that names a person. Whether an earlier answer the service gave for the same credential, kept on the machine, counts as its answer is for the record that places the reading.
- **Only a grant needs the app's login:** the membership gate (point 2) and a seat's claim (point 6). Everything else this record decides holds without it, except that under an unresolved identity a clone that holds an instance id refuses (point 4). So an answer misread in this capability's guards grants nothing. The credential's kind is a fact of the session, read where the commands act.

**An installation's token with no login.** Under the request DEC-021 names, an installation's token receives the integration's refusal, as on the trial, so it is an app's credential, and the commands know no acting account under it unless another request gives its login. Its account can then be neither a member (point 2) nor a seat's holder (point 6), so behind a closed gate it passes no command that takes the gate. Its acts name no actor, so none of its moves is recorded in the journal (DEC-078 point 3). A clone under it that holds an instance id goes on as an app's clone does (point 4).

### 2. No person stands for the acting account

Under a credential that names no user's account, in a CI workflow and in an agent's session alike:

- **The acting account** is the app's, by the login the service gives it. Where the service gives none, the commands know no acting account.
- **Git's configured email does not stand for it.** The email names whoever set up git on the machine, a person the credential does not act as, or one the commands cannot tell it acts as.
- **Nor does `PM_INVOKER_LOGIN`.** Whoever starts the run or the session can set it, and the commands cannot tell who did. It names the person the agent works for (point 3).
- **The closed membership gate** matches an app's account by its own login, in the spelling DEC-079 point 1 gives, with no person's login beside it, and matches nothing where the commands know no acting account. A project lets such an account act by adding it as a member. That admits every session that holds a credential whose account the entry names, whoever starts it and for whomever it works, a non-member among them. For a workflow's own token, that is every workflow the repository runs, whichever writer pushed its file and on whatever branch.
- **The member list changes under no such credential.** Membership grants authority, and an app's account, or one the commands do not know, has no person to stand behind a change to it. So a command that adds or removes a member refuses, while the gate is open too, where adding such an account as the first member would close the gate with no person in it. A person changes the list under their own credential.

### 3. The person the agent works for serves only where naming a person grants nothing

- **Where it comes from.** Under a credential that names no user's account, `PM_INVOKER_LOGIN` names the person the agent works for. The variable is an input of the commands, documented with them, so its meaning is part of their public surface, which a setup uses as any adopter does. The commands read it in one place.
- **Beside a user's account,** the variable is no identity, since DEC-021 takes that account's login alone for every reader. Under a user's credential that is not the person's own, such as a machine user's, the variable set to the person names nobody the commands take.
- **Where it serves:** where the commands would name the acting account as a person, and grant nothing by doing so.
  - The default assignee at filing, and `--me` on an assignment, held like any assignee to a member where the gate is closed (DEC-019).
  - `start-work`'s refusal of a Task assigned to someone else, and the assignee it writes (point 4), and so which Tasks `next-task` hands out.
  - A report of the work assigned to whoever runs it (DEC-073 point 2). A listing's `mine` stays the clone's own claims (DEC-035 point 7), and such a clone has none.
- **Where it never serves:** the membership gate, a claim, an approval, an act's actor or a comment's authoriser (DEC-078). So `--me` on a command that changes the member list refuses (point 2). Nor does it tell whether anyone is at the terminal, which is a property of the session's process.
- **Without it,** a command that needs a person refuses. It says why it knows no person, with the cause DEC-073 point 2 has the resolution give, and how the session can name one. A report that rests on that person reports it as resting on nobody, as DEC-073 point 2 has it. `create-issue` still takes an assignee named in the call, as when a person files for another (DEC-035 point 5).

It is the caller's word, as an assignee the caller names is. Set wrongly, it lets the agent past the refusal that keeps it off another person's Task. Like DEC-035's clash guard, that refusal catches the mistakes of agents that follow the procedure, and is no security boundary.

### 4. `start-work` keeps its refusal, against the person the agent works for

Under a credential that names no user's account, in a project with no topology, `start-work`:

- **refuses a Task assigned to someone other than the person the agent works for,** and names `handoff-issue`, as DEC-026 has it;
- **assigns that person a Task with no assignee,** and writes no assignee where that person is one already;
- **posts no claim,** since no claim it wrote would count (DEC-079 point 2);
- **refuses a Task an instance owns,** whatever instance id the clone holds. The clash guard reads the owner for such a clone, though the clone claims nothing. A reason overrides the refusal and posts an audit comment, as for any clash (DEC-035 point 6).

**Under an unresolved identity, a clone that holds an instance id refuses.** Every command that acts as an instance refuses there, says why, and is run again. A person's clone that holds an id would otherwise start the Task, post no claim, and leave it In Progress with no owner, where another of the person's clones may act on it. A clone with no id claims nothing under any credential, so it goes on as this point says, and so does an app's clone, with or without its login, whatever id it holds.

Every other lifecycle verb under such a credential reads the owner the same way. `handoff-issue` hands a Task from one person to another, and never to an app's account.

Two sessions under one such credential, working for one person, can start the same Task, since neither claims it, as two of a person's clones with no instance id can. Nor is a person's own clone kept off a Task such a session started for that person: the Task carries no claim, so the person's clones read it as nobody's. Each is a limit (point 7).

In a project with a topology, such a clone starts no Task (point 6).

### 5. What passes on the caller's word stays as it is

- **The caller's word.** What passes on the caller's word under every credential, such as a merge by bypass or an authorisation to merge given up front, passes the same under a credential that names no user's account, and is recorded as DEC-078 has it. This record guards none of it. Who may give that word in an agent's turn is a record of its own.
- **A reviewer agent's verdict on the local path** ([project-management:DEC-028-agent-as-approver-paths]) is posted under such a credential by the acting account. It attests what that account ran, and names no person responsible for it. The path rests on the trust of a bypass, as it does under any credential.
- **The refusals this record adds offer no override,** but the clash guard's on a Task an instance owns, which a reason overrides (point 4). An override would put back what each keeps out. Each is a precondition of its command, never a `hard-reject` finding of DEC-014's, so the `--force` DEC-046 gives such a finding does not reach it. A gate another record decides keeps the override it has there, such as `done-work`'s approval check, which a bypass overrides, and the membership gate, which nothing overrides.

### 6. In a project with a topology, a clone under such a credential builds nothing

- **No seat that builds.** A worker's or a lead's seat rests on claims on Tasks that count (DEC-059 point 9), and such a clone's never do. So it takes no such seat.
- **No Task without a seat.** A Task such a clone started without a seat would stand In Progress with no claim that counts, which a worker reads as ready to take over (DEC-059 point 7). So `start-work` refuses there.
- **A planner's seat, only behind a closed gate.** An app's clone may hold a planner's seat, since its claim on the seat's state issue is its own account's. That claim counts only where [project-management:DEC-058-state-issues] point 4 counts its author: as a member where the gate is closed, and otherwise where the service answers that the account may write to the repository. Every reader judges a member by the same entries, read from the default branch, so a member's claim counts alike for every reader. Whether the service answers alike about an app's account's write access, to every reader, is unmeasured. So an app's clone claims a seat only where the gate is closed and its own account is a member, which it reads before it claims. Where the gate is open, or where the commands know no acting account, it takes no seat.
- **The organizer seat** is held on the same terms. An app's clone that holds it releases other seats by force as that seat's clone does (DEC-059 point 5). A project that admits an app's account admits to that privilege every session that holds a credential whose account the entry names, as to the gate (point 2).
- **A planner's filings** are assigned to the person the agent works for (point 3).

A claim whose author's standing differs between readers splits the seat. A reader whose call about the app's account fails reads the issue as incomplete, and one that gets a definite no reads the seat as free while the app's clone holds it. This capability never edits a comment on a state issue (DEC-058 point 4), so only a person deleting the comment ends either.

### 7. What stays unmet

These needs stay unmet under a credential that names no user's account. Each is a limit, stated by its property with what meeting it would cost:

- **Instance ownership on issues of work,** and so building in a project with a topology. Meeting it would count a claim from a bot's account, which loosens DEC-043 point 3: anyone holding the credential could then claim work for any person.
- **Two sessions under one such credential, kept off one Task.** Meeting it needs a mark that such a clone makes and other such clones read, a design of its own.
- **A person's own clones, kept off a Task such a clone started for that person.** Meeting it needs the same mark, read by the person's clones too.
- **The closed membership gate where the commands know no acting account.** Meeting it needs the service's answer with the account's login (point 1).
- **A planner's seat behind an open gate.** Meeting it needs the service's answer about an app's account's write access, measured alike for every reader (point 6).

A setup that needs one of them gives the agent another credential, which is the setup's own choice.

## Rationale

**Why the commands take no person's identity where the service names none.** There, any value that names a person is the caller's word, or git's record of whoever set the machine up. Acting as the person on it would make each act of the account read as the person's own, in the tracker and in every check that reads it. Acting as the account the service names keeps that record true, since the service shows which account wrote each change.

**Why no answer leaves the identity unresolved, under every credential.** Without the service's answer, the commands cannot tell an app's credential from a person's. A fallback to git's email or the variable would make the person the acting account under an app's credential whenever its lookup times out, on the very machine a setup prepares for an agent, which names the person in the variable and likely in git's email. Failing closed costs little. A command that cannot reach the service can rarely do its work, since every write it makes goes there ([project-management:DEC-003-github-bound-substrate]), and it says why and is run again. Each command that takes the gate or names who runs it already asks the service (DEC-021, "The request for the account"), and a command that only reads and reports asks only where its report rests on who runs it (DEC-073 point 2). A machine user's workflow that sets the variable refuses wherever that call fails. The posture is decided only for the acting account's identity, and every other read keeps the posture DEC-021 leaves to its implementation.

**Why an integration's refusal is an app's answer.** The service tells it from a refusal for any other cause by its status and words (DEC-073 point 2), so it says that no person acts. Reading it as no answer would refuse an app's clone that holds an instance id at every command, though no second run could change the answer, and no claim it wrote would count either way.

**Why the variable names no acting account, in CI as in a session.** Taken for the acting account, it would name the person as the actor and authoriser of acts the service records as another account's (DEC-078), hand the engine's gate the wrong actor ([pkit:COR-033] P4), and still make no claim count, since the ownership fold reads who wrote a claim (DEC-043 point 3). DEC-021 meant to keep the variable from a value the user controls, and trusted a CI workflow to keep it so. The commands cannot tell whether it did: a workflow's input is typed by whoever dispatches the run, an earlier step can set the environment of later ones, and a pipeline that runs an agent's session is both a CI workflow and an agent's session. So under a credential that names no user's account the variable is read alike in both, as the caller's word, where the caller's word grants nothing. Whether it names the person the agent works for or nobody the commands take is told by the service's answer, a property the commands read.

**Why git's email does not stand for the account.** Under any credential the email is a value the user controls, and beside a person's resolved login DEC-021 takes the login alone ([project-kit#3175](https://github.com/aleskalfas/project-kit/issues/3175)). Where the service names no user's account, the email names a person the credential does not act as, or one the commands cannot tell it acts as.

**Why the person the agent works for grants nothing.** Most of what the commands do with a person's login says whose the work is: the assignee at filing, and whether a Task is someone else's. A wrong value there misleads and grants nothing, since a claim, an approval and membership are each read from the account that wrote or acts, never from the assignee.

**Why `start-work` keeps its refusal.** Without a person to compare with, an app's account is nobody's assignee, so the refusal would catch every assignee, as on the trial, or none, which would let an agent start any member's Task. It is a mistake-catcher, as are its neighbours (DEC-058 point 5, and DEC-059's release by force), and on the caller's word it keeps catching the mistakes of agents that follow the procedure.

**Why a clone that holds an instance id refuses under an unresolved identity.** Such a clone means to claim what it starts, and the commands cannot tell whether its claim would count. Going on would leave the Task with no owner, where a second run, once the service answers, tells whether its claim would count. An app's clone the service answered for starts the Task with no claim too, but no second run mends that, so it is a limit (point 7), not a refusal.

**Why the clash guard reads for such a clone.** A person's clone with no instance id may opt into ownership, and is guarded once it does (DEC-035 point 1). A clone under a credential that names no user's account cannot opt in, so reading the owner is the only guard it can have, and it grants nothing.

**Why DEC-028's local path stands.** Under such a credential a bypass passes all the same (point 5), so refusing the local path would push such an agent to a bypass, which records less: no verdict, no reviewer, no head reviewed. Under a person's credential, an agent's session already posts the verdict in the person's name, though the person attested nothing. Under a credential that names no user's account, the verdict names no person, which is true. The reason lasts while a bypass passes on the caller's word.

**Why such a clone builds nothing in a topology.** A seat stays taken until it is released (DEC-059 point 5), so a clone that took a building seat and could claim no Task would hold the seat while doing none of its work. A Task it started without a seat would be taken over from under it.

**Why an app's clone claims a seat only behind a closed gate.** Behind a closed gate, every reader judges a claim by the same members. Behind an open gate, each reader asks the service about the author's write access, and a claim judged differently by different readers splits the seat, which only a person's hand ends (point 6).

**Why an app's clone may hold the organizer seat.** The privilege already goes to whichever clone takes the seat, so an app's clone in it grants no more than the project granted by admitting the app's account. Keeping it out would leave such a clone no seat at all, since the planner's seat is typically the organizer's.

**Why act as the account, and not only state a limit.** The setup offers a credential that names the person's account, so every need could be a limit. But most of what the commands do needs no person. And under the person's credential, the agent's pull request is the person's own, which the person cannot approve (DEC-028, "Self-approval degrade"). Under a credential that names no user's account, the person can approve it, and `done-work`'s approval check reads a trace from another authority, as COR-033 P4 asks of a gate.

**Why the reading lives outside this capability.** The backbone reads the acting account too, and two readings of one credential can disagree, as they can at the engine's gate, where the two sides may spell one account two ways. A capability's script reaches the backbone only by command ([pkit:ADR-057] point 1), the backbone cannot depend on a capability a project may not install, and a computation keeps one home (ADR-057 point 2). So the one home both read lies outside this capability, and a record of the backbone's places it, as [pkit:ADR-061] placed the hosting service's acts.

**Which edits overturn, and which refine.** One test sorts every edit this record names, by what the passage states for the case this record decides:

- **Overturned in part,** where it states an outcome this record contradicts: a named fallback or provision, or an explicit no. The passage stays as it stood, under a top line that names this record.
- **Narrowed in place,** where it grants something to a general class, and this record takes the credentials or accounts it decides for out of that class, while the grant stands for the rest.
- **Widened in place,** where it names the ways to an outcome, and this record adds one.
- **Completed in place,** where it states no outcome for the case, as a question it left open or a term it fixes only for a person.
- **A fact corrected in place,** where the passage's rule stands, and only a fact stated beside the rule reads false.

The test asks what a passage states, not what case it was written for, so one passage may take two sorts. DEC-021 states an outcome for the gate where the service does not answer with a user's account, the match on any surface, so it is overturned there. It leaves the other readers open by name, so it is completed for them.

### Alternatives considered

- **State a limit and nothing more:** the commands act only under a credential that names a user's account. The case: nothing to build. Rejected: most of what the commands do needs no person, and the person could not approve their agent's pull requests.
- **A limit, plus a mark the commands add to what an agent's session writes.** The case: instance ownership keeps working under the person's credential. Rejected: the mark is the session's own word, weaker than the service's record of which account wrote, and the person still cannot approve the agent's pull requests.
- **`PM_INVOKER_LOGIN` names the acting account,** in an agent's session, or only in a CI workflow as DEC-021 provides. The case: `start-work` and `create-issue` work as under the person's credential. Rejected, for the reasons above, and because no line between a workflow and a session holds.
- **Fall back to git's email and the variable where the service cannot be asked,** as DEC-021 provides. The case: a person's own credential keeps passing the gate with no network. Rejected: without the answer the commands cannot tell an app's credential from a person's, and with no network little they do succeeds anyway.
- **Read a credential's kind from its own form,** such as the prefix the service gives each kind of token. The case: a property read on the machine, even where the service refuses the lookup. Rejected: a second reading of the kind can disagree with the service's answer, a form the commands do not know leaves the identity unresolved anyway, and the command must read the secret itself to see its form.
- **Read an app's credential from any refusal, or leave an integration's refusal unresolved.** The case: one outcome for every refusal. Rejected: a rate limit or a token revoked says nothing of the credential's kind, and the service's status and words tell an integration's refusal from those (DEC-073 point 2), so treating it as no answer refuses for no guard gained.
- **A variable of its own for the person the agent works for.** The case: each variable keeps one meaning on every machine. Not taken: neither variable stands for the acting account once no answer leaves the identity unresolved, and under a user's credential the one variable stands for no account, so a second name closes nothing and costs every setup an input to learn.
- **The person the agent works for as a second check at a closed gate.** The case: it catches an agent that works for a non-member. Not taken: it would refuse only a session that names a non-member truthfully, and keeps out no session the project did not admit by adding the app's account. A project that wants non-members' agents kept out gives them no credential whose account it admitted.
- **An interim reading in this capability, in one seam,** moved into the backbone later. The case: the capability's work starts at once. Not taken: two readings of one credential would run side by side until the move, and they already disagree at the engine's gate.
- **`start-work` works under whatever assignee the Task has.** Rejected: an agent could start any member's Task, which drops a mistake-catcher that costs one value to keep.
- **A setting kept for the clone names the person the agent works for,** in place of the variable. Not taken: it needs a command and a stored value of its own, a CI run would write it each time, and the variable already serves.
- **No clash guard for such a clone.** Rejected: it would act on a Task another of the person's clones is building, with nothing to warn it.
- **`start-work` reports that it posted no claim under an unresolved identity, and goes on.** Rejected: the Task is left with no owner all the same, where a second run would have mended it.
- **An app's clone claims a seat as any clone does, or behind an open gate too.** Not taken: a claim no reader can judge, or one readers judge differently, splits the seat, which only a person's hand ends.
- **Keep an app's clone out of the organizer seat.** Not taken: the privilege already passes to whichever clone takes the seat, and such a clone would be left no seat at all.
- **Refuse DEC-028's local path under such a credential.** Rejected: a bypass passes there all the same, and records less.

## Implications

- **What changes in projects that run no agent under such a credential,** each refusing more, with a message that names the way out:
  - a closed-mode workflow under its own token that passes by the variable or by git's email, on a command that takes the gate, refuses until its own account is a member;
  - a workflow under a machine user's token with the variable set asks the service which account it acts as, and refuses wherever it gets no answer;
  - a person's own credential the service gives no answer for passes the gate by neither git's email nor the variable;
  - no command makes a bot's account an assignee, or hands a Task to an app's account.
- **Overturned in part.** Each record below stays accepted, and its overturned words stay as they stood. Its top line, its first paragraph, names this record as *Partially superseded by [project-management:DEC-076-app-credentials]* and says in the line itself:
  - **DEC-021,** above "Context": "Where the hosting service does not answer that a credential acts as a user's account, neither git's email nor `PM_INVOKER_LOGIN` passes the acting account at the membership gate, and the variable names the person the agent works for, who grants nothing. Overturned: 'Identity resolution''s match on any surface, so far as it passes the acting account on git's email or the variable there, item 2's fallback where `gh` is unavailable among them; item 3's 'never from user-controllable env', so far as it binds the variable where it names the person the agent works for; and the Implications' 'CI invocations', so far as a workflow whose credential is no user's passes by the variable. Among what stands: the gate, its modes and the list, and its identity resolution where the service answers with a user's account."
  - **DEC-035,** whose line names both records that overturn part of it, in one paragraph, each as a link to its file. DEC-059's sentences stay, but "A project with no topology keeps this record whole" reads "A project with no topology keeps this record whole, as far as DEC-059 goes". It adds: "Under a credential that names no user's account, a clone takes no part in instance ownership on issues of work, whatever id it holds, the clash guard reads the owner for it, and under an unresolved identity a clone that holds an id refuses. Overturned there by DEC-076: point 1's id as the sole activation gate, and its 'no guard' for a clone with no id, with the summary and the Rationale's 'Why opt-in by clone-local id' where they restate them."
  - **DEC-059,** whose line names DEC-061 and this record, in the form DEC-035's line takes. DEC-061's sentences stay, but "Among what stands: all of this record in a project with no pools" reads "Among what stands: all of this record in a project with no pools, as far as DEC-061 goes". It adds: "Under a credential that names no user's account, a clone that holds no seat starts no Task. Overturned there by DEC-076: point 6's 'is guarded by nothing' for a clone that holds no seat."
- **Refined in place,** each with the pointer `(refinement per [project-management:DEC-076-app-credentials])`, citing this record's points as DEC-076 point N:
  - **DEC-019, completed:** "Mandatory assignment" and its "Self-assignment shorthand": the filer, whom the default at filing, the schema's `default_at_filing: filer` and the Context name, is the acting account resolved per DEC-021, and under a credential that names no user's account, the person the agent works for. That person is held to `values_constrained_to: members` as any assignee is, so is a member where the gate is closed. Without one, `create-issue` takes the assignee named in the call and refuses a filing that names none, and `assign-issue --me` refuses. No command makes a bot's account an assignee.
  - **DEC-021:**
    - narrowed: "Bootstrap: the first member self-adds", "Membership change authority", and the "Tooling surface"'s `add-member.py` and `remove-member.py`: no command adds or removes a member under a credential that names no user's account, while the gate is open too, and a person changes the list under their own credential.
    - widened: "Identity resolution"'s item 1: where the service refuses `gh api user` because the credential is an integration's, the first source is a request that answers, for the credential, with an app's account and its login, where the service gives one, and that account is the acting account (DEC-076 point 1).
    - completed: the last paragraph of "Identity resolution", and the Rationale's "Why mechanism details are deferred": of the posture on network errors, the read of the acting account's identity fails closed under every credential, since every outcome but the service's answer leaves the identity unresolved, and the commands report its cause. Every other read keeps the posture left to the implementation.
    - completed: the Rationale's sentence that "whether git's email and the variable should name the invoker there rests on evidence of its own": on that evidence ([project-kit#3164](https://github.com/aleskalfas/project-kit/issues/3164)), neither names the acting account there for any reader, each act's actor is the account the service names, or none (DEC-078 point 1), and under a credential that names no user's account the variable names the person the agent works for, whom a reader takes only where naming a person grants nothing (DEC-076 points 2 and 3). The sentence's first clause, that the record decides there only the match on any surface, stays as it stands.
  - **DEC-026:**
    - completed: the `start-work` row of "The seven commands", and the assignee-conflict row of the "Sub-decisions index": under such a credential, `start-work` compares the Task's assignee with the person the agent works for, refuses another's Task as under a person's credential, assigns that person a Task with none, posts no claim, refuses a Task an instance owns, and refuses where the session names no person, where the project has a topology, and, under an unresolved identity, where the clone holds an instance id.
    - narrowed: the `handoff-issue` row of "The seven commands": a Task is never handed to an app's account.
  - **DEC-028, completed,** wherever its local path has the developer post or attest the verdict: the Decision's top line, the Context's "Local path" bullet, "Path 2: Local agent", "Invocation command (local path)", "Self-approval degrade", "Allowlist as attestation, not security", the Rationale's "Why relax author-exclusion for the local path", the Alternatives' rejection of the agent's name in the remote path's verdict line, the Implications' `review-pr` bullet, and the "Sub-decisions index"'s rows "Two execution paths", "Local-path identity check", "Invocation command (local path)" and "Allowlist framing". Each states it of the account that runs the command: the user's account under a credential that names one, as DEC-021 takes it, and under a credential that names no user's account, the account it acts as, whose verdict attests what that account ran and names no person responsible for it. The path rests on the trust of a bypass under either.
  - **DEC-058 point 5, narrowed:** a clone under a credential that names no user's account claims on a state issue only where the membership gate is closed and its own account is a member, which it reads before it claims, by the test point 4 applies to any author.
  - **DEC-059 point 4, narrowed:** a clone under such a credential takes no seat that builds. It takes a planner's seat, the organizer seat among them where it is one, only where its claim on the seat's state issue may stand, as DEC-058 point 5 has it. Where the commands know no acting account, it takes no seat.
  - **[pkit:ADR-071] point 3, completed,** by the architect, whose custody it is in, with the same pointer: before a clone under a credential that names no user's account claims, the seam judges the clone's own account by the members the caller passes, and such a clone claims only behind a closed gate (DEC-058 point 5).
- **Facts corrected in place,** with no pointer:
  - **DEC-019,** the parenthetical of `validate-issue.py`'s hard reject at filing, "shouldn't happen given default-to-filer": where the credential names no user's account and the session names no person, no filer is defaulted, and `create-issue`'s refusal of a filing that names no assignee keeps the check from meeting one.
  - **DEC-073:**
    - its term for a credential that names no user's account, the sentence "Under it, the gate can match only `PM_INVOKER_LOGIN` or git's email.": under it, the gate can match only the account the service answers the credential acts as, by its login, and nothing where the service gives none (DEC-076 point 2).
    - point 6's bullet on an entry or a variable for a workflow's check, its sentence on what an entry admits: an entry added to the list for a workflow admits, to every command that can write, every session that holds a credential whose account the entry names (DEC-076 point 2).
    - the Rationale's "Why not give the workflow an identity the gate admits", its sentence "Under a credential that names no user's account, the gate can match only `PM_INVOKER_LOGIN` or git's email, which may name anyone.": under such a credential, the gate can match only the account the credential acts as, which every session that holds a credential for that account acts as, or nothing where the service gives no login (DEC-076 point 2).
- **Left out, for records of their own:**
  - **Where the reading of the acting account lives,** with whether an earlier answer kept on the machine counts as the service's (point 1).
  - **Who may authorise in a turn that a chat started** ([pkit:ADR-091], Implications), which decides the acts of point 5 and when DEC-028's local path is revisited.
  - **The person the agent works for, in the backbone.** The backbone's reporting command already posts for such a person, and a variable named for this capability is no name the backbone can depend on.
  - **How a read of the board tells a board that did not answer from one that answered empty,** under every credential, which [pkit:ADR-096] decides. An installation's token is one credential that a user's board answers empty.
