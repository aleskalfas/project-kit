---
id: DEC-081
title: A worker takes direction only from the seat its topology names, by Tasks and by messages alike
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** agents delegate through one model, the topology of seats, whether direction travels as a Task on the tracker or as a message through the harness. A worker's seat may name, in the committed topology, the planner's or the lead's seat that directs it. That seat files Tasks, and the worker takes them from its pools, as before. Where the harness carries messages between sessions, the directing seat may also message the worker, to wake it or to name the ready Task in its pools it takes next. A message never carries work the tracker does not hold. The worker counts a message as direction only where it comes from the session its directing seat's state issue records, by the session's name and folder, and any other message is information. The worker reports that it is done, blocked or needs something, on the tracker through its Task and pull request, and by message where it can. A question for the person goes to the person, through the directing seat where the worker cannot reach them. A message is never the person's authorisation, and neither is a Task. Direction stays within one repository's topology, and without messaging the tracker alone carries it. The project-manager agent holds the harness's tools for messaging and for listing sessions.

## Context

**What stands.** In a project that runs agents in parallel, the committed topology names each seat, its role and the pools it serves ([project-management:DEC-059-topology-of-seats], [project-management:DEC-061-pools-of-workers]). A planner or a lead files Tasks, a person schedules them into a pool, and a worker takes the next ready Task from its pools, claimed so that no second agent takes it. A fresh builder builds each of a worker's Tasks, from a brief written from the Task alone ([project-management:DEC-063-task-builder]). Which clone holds a seat is kept on the seat's state issue ([project-management:DEC-058-state-issues]). The project-manager agent is withheld the harness's tools that message other sessions and list them, since work reaches seats through the pool, not through messages ([project-management:DEC-068-session-agent-tools] point 2).

**What the maintainer decided.** On 17 November the maintainer decided that the topology and its pools are the one model of delegation, extended to the harness's messages, and that no work exists only in a message (#3392). Direction comes only from the seat whose role directs the worker, as the committed topology names it, checked against the session the seat's state issue records. Reports go up on the tracker and by message, and a question for the person goes to the person. The agent holds the harness's tools for messaging and for listing sessions. A message is never the person's authorisation, nor is a Task, each session changes only its own repository ([COR-039](../../../decisions/core/COR-039-session-repo-mutation-boundary.md)), and without messaging the tracker alone carries the model. This record holds those decisions, and settles what they leave open.

**Terms.**

- **Messaging** is a harness's tool that sends a message from one session to another. **The listing** is its tool that lists the sessions messaging reaches, each with its name, its folder and the address a message goes to.
- **A worker's directing seat** is the seat the topology names to direct it (point 3). **A direction** is a message from that seat's session that passes the worker's check (point 5). **A report** is a worker's message to its directing seat.
- **The person** is a person who decides what reaches the project's default branch, as [COR-064](../../../decisions/core/COR-064-answer-delegate.md) defines the term.

**What the harness offers.** Read from Claude Code's documentation on 17 November, not measured:

- **Reach.** A session reaches any other session on its machine by default, whatever its folder or repository, and other machines only through the harness's remote control. A session in its bare mode cannot be reached, a stopped session cannot be messaged, and no queue is documented.
- **Names.** The listing names each session by the name the person gives it, or one the harness picks. Names are not unique: sessions that share a name each get a short identifier as their address. Each row shows its session's working folder, except under remote control.
- **The sender.** A message arrives marked as from another session, with the sender's name and a reply address. Nothing proves the sender. A message cannot approve a permission prompt or change configuration, and a command in it never runs.
- **Held messages.** A session that bypasses permission prompts holds a message from a sender that does not, and is delivered one from a sender that also bypasses. A person may approve a held message at its terminal before a deadline of a few minutes, and a session with no terminal to show the approval drops it then.
- **Helpers.** A helper running in the background keeps messaging, but not the listing.

The documentation leaves these unconfirmed, so the build measures them before it rests anything on them:

1. whether an agent definition the project deploys holds messaging and the listing where it withholds neither
2. whether a session can read its own name, and whether an interactive session keeps its name across a restart
3. whether a message's reply address is the address the listing shows for its sender
4. which folder a row of the listing shows: the session's first folder or its current one, a worktree's or its clone's
5. what a held message does at its deadline in each kind of session, and which setting for inbound messages prevails where several set one
6. whether a builder's sandboxed run can send or receive a message

## Decision

**One model of delegation holds over the tracker and the harness's messages: the topology's. A worker's seat may name the seat that directs it. The directing seat files Tasks, and may message the worker to wake it or to name the ready Task in its pools it takes next, never work the tracker does not hold. The worker takes direction only from the session the directing seat's state issue records, reports up on the tracker and by message, and sends the person's questions to the person. A message is never the person's authorisation, nor is a Task. Direction stays within one repository's topology, and without messaging the tracker alone carries it.**

### 1. One model, over the tracker and the harness's messages

The topology's seats, roles, pools and claims decide who directs whom and who builds what, wherever direction travels.

- **On the tracker,** the directing seat files Tasks, the person schedules them into the worker's pools, and the worker takes the next ready Task from its pools, in their order. This form stands alone where messaging does not reach.
- **Through the harness,** the directing seat's message wakes the worker, or names a Task the tracker already holds ready for it (point 6). The worker's reports go up the same way (point 8).
- **No work lives only in a message.** A message names a Task, or none. What must outlast it, such as a Task filed, changed, held back or taken out of a pool, is written on the tracker, under the rules for that write. So a lost message costs only the time it would have saved.

### 2. The agent holds messaging and the listing

The project-manager agent holds both tools wherever the harness gives them. A tool that opens or lists a channel to other sessions is not among the kinds its definition withholds, and DEC-068 point 2's other two kinds stand. The agent messages only its directing seat's session, as a worker, the sessions of the workers it directs, as a directing seat, and a session the person names to it in its own session. It messages no builder's run (point 6).

### 3. The topology names the seat that directs each worker

- **One directing seat, named on the worker's seat.** A worker's seat may name one seat that directs it, a planner's or a lead's, not retired. A directing seat may direct many workers. A planner's or a lead's seat names none, since the person directs it, and a worker directs no seat. So direction has one level, with no chain and no cycle.
- **Read from the default branch,** as the rest of the topology is (DEC-059 point 1). So a change of who directs a worker binds once a merge the person authorised lands it, and no message can name another directing seat.
- **The topology's check refuses** a worker's seat that names a seat the topology does not hold, a retired seat, itself or another worker's seat, and a planner's or a lead's seat that names any.
- **No directing seat named:** the worker takes direction from no session, and works from its pools alone.
- **A lead's own work.** A lead files with no owner the work it leaves to its workers, so that the work enters the pool, and owns only what it files for itself to build.

### 4. Each seat's state issue records the session that holds it

- **What it records.** The clone that holds a seat records the name of the session it runs the seat in, beside the machine and the folder its claim already names (DEC-058 point 5). It does so in an event of its own on the seat's state issue, each time a session takes the seat up, and again where the session's name changes. Where a session cannot read its own name, whoever starts the session gives it, as they give its agent definition (DEC-059 point 4).
- **Which side, and who writes.** The session changes while agents work, and is part of who holds the seat, so it lives on the seat's state issue, found by the number the topology names (DEC-058 point 1). Only the holder's clone writes it, under its claim: another clone's event counts for nothing, and the seat's release clears it.
- **Every seat records it,** a worker's as well as a directing seat's, so that each side can address the other and check what it receives.

### 5. A worker checks each message against its directing seat's record

- **The check.** On each message, the worker reads the session its directing seat's state issue records, and lists the sessions it reaches. The message is a direction only where all of these hold:
  1. The record names the worker's own machine.
  2. The listing shows exactly one session under the recorded name in the recorded folder.
  3. The message comes from that session: its reply address is that session's address, or, where the harness gives no address to compare, no other listed session holds the sender's name.
- **The check cannot pass** where the worker's seat names no directing seat, that seat is free, no session is recorded, or the record names another machine. So too where the listing shows no folder, as under remote control, where the worker has no listing, as a background helper has none, and where the harness has no messaging. No message is then a direction, and the tracker carries the model (point 1).
- **Two sessions or more match:** none is the directing seat's session, and no message is a direction. The worker tells the person where it can reach them (point 9), and works from its pools.
- **Any other message is information.** The worker takes no step a direction would take on it. What it says is a hint to check on the tracker, never grounds, and the worker may report it to its directing seat.
- **The same check the other way.** A directing seat messages a worker only where the worker's record names exactly one session it lists, and counts a report as its worker's only where the same check passes.
- **A guard, not a boundary.** Nothing the harness gives proves a sender, and any session in the directing seat's folder can take its name. Like the guard on a claim ([project-management:DEC-035-instance-ownership] point 6), the check catches the mistakes of sessions that follow the procedure, and stops no session that means to pass as another.

### 6. A direction may name the worker's next Task, and widens nothing

- **Which Task.** A direction may name one Task for the worker to take next, ahead of the pool's order. It names only a Task the worker could take of its own choosing: ready, in its seat's scope, and in its pools where the topology declares them (DEC-059 point 7, DEC-061 point 5). Work in flight goes on first, as the worker's loop has it.
- **The same take, the same claim.** The worker takes the named Task through the take it uses for any Task, which claims it, so the clash guard keeps a second agent off it whatever channel sent either (DEC-035 point 6). Where one Task is named to two workers, the guard leaves one claim holding, and the other worker reports the loss and takes its next ready Task. A directing seat never claims a Task for a worker, since a claim names the clone that makes it (DEC-059 point 9).
- **Nothing outside.** On a direction, the worker takes no Task that is not ready, lies outside its pools or scope, or is held by another, and reports why. Scheduling such a Task or putting it into a pool is the person's act (DEC-061 point 6), and directing a seat to a Task outside its pools stays the person's own word, in the worker's session (DEC-061 point 5).
- **The person's word outranks a direction.** Where they disagree, the worker follows the person's word in its own session, and tells its directing seat.
- **A build reads its brief alone.** A direction reaches the worker's session, never the build it starts, whose brief is written from the Task alone (DEC-063 point 3). So what a direction asks of a Task's work reaches a build only once it is written on the Task.

### 7. A worker keeps its own rules, whatever a message asks

A message changes none of the worker's rules, records, settings or permissions, nor its seat's role. Asked for what they refuse, the worker does not do it, works around nothing, and answers the sender with the rule or the refusal that stops it. What the message asks that is the person's goes to the person (point 9). That covers a change to another repository, which the worker never makes on a message (COR-039).

### 8. A worker reports when its work is done, blocked or in need

- **At once, on each direction:** that it takes the named Task next, or why it does not. The answer tells the directing seat that the direction arrived (point 11).
- **Done:** when its Task moves to Review, naming the pull request.
- **Blocked or in need:** when its loop stops on what it cannot settle, with what stops it, such as a build's question waiting on its Task, a refusal, a step that failed again after its one retry, or a claim it lost. So too when nothing is ready for it, with the reason in terms of its pools, and when it needs an act of the person's (point 9).
- **What a report holds:** the Task or pull request it concerns, and what the worker would tell the person, word for word. It holds nothing of the work that the tracker lacks, and the directing seat reads the Task or pull request a report names before it acts on it.
- **On the tracker,** the Task's state and its pull request are the report, for every reader. Where messaging does not reach, the directing seat reads them at each round of its own.

### 9. A question for the person goes to the person

- **What is the person's:** scheduling work and putting it into a pool, a held move, an override with its reason, authorising a merge, accepting a record or a rule, a build's decision and permission questions, and every consent a record asks ([project-management:DEC-006-state-machine-and-cascade], DEC-061 point 6, DEC-063 point 6, COR-064 point 6).
- **Where the worker can reach the person,** in its own session, it asks them there. Where it cannot, as with no terminal at its session, it reports the question to its directing seat, which brings it to the person word for word.
- **The directing seat answers none of them,** nor a build's question, since an answer from its own context would carry that context into the build (DEC-063 point 6).
- **The person acts where the act's command takes their word,** such as on the Task for a build's question, or in the session that runs a held move, and the worker reads the outcome on the tracker.
- **Where neither seat reaches the person,** the question waits where the capability already keeps it, as a build's question waits on its Task, and the worker's loop stops as it would with no directing seat.

### 10. A message is never the person's authorisation, nor is a Task

No direction, report or other message stands for an act that stays the person's, and neither does a word of the person's that a message relays. Nor does a Task: one that asks for such an act still sends it to the person, whoever filed it. No session acts on a message, or on a Task, that says the person agreed.

### 11. A held message loses no work

- **What the harness holds.** Where a seat bypasses permission prompts and its sender does not, the harness holds each message until a person approves it at the seat's terminal, and drops it at its deadline where no terminal can show the approval. So an unattended seat in such a mode may never see a direction or a report.
- **Approving delivers, and authorises nothing.** A held message a person approves then counts as any other message (points 5 and 10), never as the person's word. No seat approves one for itself.
- **Nothing is lost but time.** A dropped direction names a Task the tracker holds, which the worker reaches in the pool's order at a later take. A dropped report points at what the tracker shows.
- **Counted only once answered.** A directing seat counts a direction received only once the worker answers it (point 8). It sends none again on silence, and reads the tracker instead.
- **No setting changes.** This record changes no session's rule for inbound messages. Whether the seats run in one mode, or accept what the harness would hold, is the person's choice in their own settings, and the capability's documentation says what each choice does for an unattended seat.

### 12. Direction stays within one repository's topology

A directing seat and its workers are seats of one topology, which is one repository's own and outside the mesh, as DEC-059's Implications, "No mesh interaction", have it. A session of another repository is any other session, and its message is information (point 5). Work that spans repositories is filed in each, and each session changes only its own repository (COR-039).

## Rationale

**Why one model.** Two channels with two authorities would need two sets of rules, and a worker could not tell which binds. With the topology deciding who directs and the tracker holding every Task, a message adds speed and an order, and no authority. A harness without messaging loses those two and nothing else.

**Why the topology names the directing seat.** Who may direct a worker is authority, as the organizer seat's release by force is (DEC-059 point 2). In committed configuration read from the default branch, it changes only through a reviewed merge. A default, such as the only planner, would grant authority that no change reviewed.

**Why planners and leads, one level deep.** They are the roles that file work for others to build. A chain of directing seats would pass a direction through a seat that judged none of it, and a worker with one directing seat never meets two directions that disagree.

**Why a session's name and folder.** A message carries its sender's name and reply address, and the listing shows each session's name, folder and address, so these are what a worker can compare. A name alone repeats. The folder tells the directing seat's clone from every other on the machine, and the name tells its session from another in the same clone. Both change while agents work, so they live on the state issue, beside the claim that names the machine and the folder.

**Why a failed check falls back to the tracker.** A message names only what the tracker holds, so ignoring one loses no work. A worker that guessed between two matching sessions could take direction from a stray one. Failing closed costs a direction's speed, never a Task.

**Why a direction may reorder, and nothing more.** The pool's order serves a worker that chooses alone, and a directing seat may know a sequence it does not show, such as a Task others wait on. The pools and the scope are the person's decisions about who builds what (DEC-061 point 6), so a direction picks within them and widens neither. The claim keeps two agents off one Task whichever seat chose it, so a direction needs no lock of its own. A Task a lead owns is ready for no one else (DEC-059 point 7), so a lead files with no owner what it means its workers to build.

**Why reports at those points.** They are where the directing seat can act: a direction to confirm, a pull request in Review, and a worker that is stuck, in need or idle. A report that adds nothing to the tracker loses nothing when it is lost. The directing seat relays the person's questions and answers none, since the person's decisions stay the person's whichever seat asks (DEC-059 point 8).

**Why accepting held messages stays the person's setting.** Every direction names what the tracker holds, and every answer tells the sender it arrived, so a drop costs time and nothing else. Accepting what a mode would hold widens what reaches an unattended agent, which only the person may choose.

**Why one repository.** The topology, its state issues, its pools and its claims are one repository's own, outside the mesh ([project-management:DEC-022-methodology-mesh]). A direction from another repository would bring another project's governance into this one, against COR-039.

### Alternatives considered

- **Keep messaging withheld, and direct only through the tracker.** Rejected: an idle worker learns of new work only at its next round, and the maintainer decided on messaging.
- **A lead session named in configuration, apart from the topology.** Not taken: a second authority beside the seats, to keep in step with them.
- **Direction derived from the pools,** such as the planner whose Milestones a worker's pools hold. Rejected: a planner names no pool (DEC-061 point 1), several planners may file into one pool, and what keeps planners apart is what the person gives each.
- **Check the sender by its name alone, or by its folder alone.** Rejected: names repeat, and the sessions of one clone share a folder.
- **A token the directing seat writes on its state issue and quotes in each message.** Rejected: every clone reads the state issue, so the token tells no more than the name and the folder, at the cost of a read before each message.
- **Take the first of two matching sessions.** Rejected: a stray session of that name would direct half the time.
- **A message from the person's own session counted as a direction.** Rejected: a message is never the person's word, and its sender cannot be proven. The person directs a worker in the worker's own session (DEC-061 point 5), or through its directing seat.
- **Directions outside the pools, warned of as a person's are.** Rejected: the pools are the person's decision, and a seat is no person (DEC-061 point 5).
- **Directions posted on the tracker too.** Rejected: a direction only reorders what the tracker holds, and a lost reorder costs nothing.
- **Send a direction again on silence.** Rejected: a held message would open another approval, and the tracker already carries the Task.
- **Direction across repositories, through the mesh.** Named, not built: a later record may decide it, with how a seat of one repository is checked from another.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([pkit:COR-066] point 5), sorted by kind and then by record:
  - **Overturned in part.**
    - DEC-068 gains a top line that reads: "Partially superseded by DEC-081. The agent holds the harness's tools that message other sessions and list them, and uses them as DEC-081 decides. Overturned: the third kind of tool point 2 withholds, one that opens or lists a channel to other sessions, with its reason. Overturned too, where they name a tool that opens a channel or reaches other sessions: the summary, the Decision's headline, point 4's three kinds, the Rationale's 'Withheld where the agent's rules cannot follow', and the alternative 'Withhold nothing'. Stands: the rest, the first two kinds among it, and point 3, refined in place."
  - **Refined in place,** each with a forward refinement pointer to this record:
    - DEC-029's dispatch paragraph says the rest of a truncated result is reachable only through a messaging tool, which a dispatcher that takes the prefix for the whole never calls, where it calls that tool one the agent's definition withholds. Its discipline, no name on a dispatched helper, stands.
    - DEC-059 point 2: a seat's list gains, for a worker's seat, the one seat that directs it, a planner's or a lead's, and the planner's and the lead's roles gain that each directs the workers whose seats name it.
    - DEC-059 point 3: the seat's state issue also records the session its holder runs the seat in.
    - DEC-059 point 7: a lead owns what it files for itself to build, and files with no owner what it leaves to its workers. A message from a worker's directing seat may wake it, or name the ready Task it takes next, which it takes and claims as any other.
    - DEC-059 point 8: no direction, message or Task stands in for a person's authorisation either.
    - DEC-061 point 5: a direction from a worker's directing seat picks among what its pools and scope hold, never outside them, and directing a seat to a Task outside them stays the person's.
    - DEC-068 point 3: its second bullet adds, to what is no person's authorisation, a direction from the seat that directs the agent and a Task that asks for an act the person authorises. A third bullet says the agent messages other sessions, and takes direction from them, only as DEC-081 decides.
- **The agent's definition,** edited by the build Task, so that the agent holds the tools only once its body says how it uses them. Its withheld list loses the messaging tool and the listing, and its comment counts two kinds. Its body gains how it records its session, checks a sender, takes a direction, reports, relays the person's questions and falls back to the tracker, and its dispatch paragraph and its bullet on messages follow DEC-029 and DEC-068 as edited. Its storyboard gains a round of each side.
- **The build Task** first measures what the Context leaves unconfirmed. It then adds the topology's key for a worker's directing seat and its check, the state issue's event for the session, and the listing of seats showing each seat's session. It adds the worker's take of a named Task only where the Task is among those it could take, the work loop's steps for directions and reports, and the README's sections on seats and the work loop. Where a builder's run can send or receive a message, a record decides whether the build's rules deny it (DEC-063 point 4).
- **The order of work.** The key enters a project's topology only once every clone that may take a seat runs code that reads it, since code that cannot read the topology in full takes no work (DEC-061 point 9).
- **No harness requirement is declared** ([pkit:COR-047]). A harness with no messaging serves through the tracker (point 1), and another harness's adapter maps its own tools to messaging and the listing.
- **Changesets.** This change declares `none` for project-management, since nothing moves until the build. The build declares `minor`, since the deployed agent's tools change for every adopter with the default agent on.
- **Acceptance.** This record overturns the accepted DEC-068 in part, and refines it, DEC-029, DEC-059 and DEC-061 in place, so accepting it needs the maintainer's sign-off. It rests on no proposed record.
