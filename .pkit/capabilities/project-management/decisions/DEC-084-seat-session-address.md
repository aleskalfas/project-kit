---
id: DEC-084
title: A worker knows its directing seat's session by the address its messages carry
status: accepted
date: 2026-11-23
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** The harness gives each running session a messaging address. The session can read it for itself, the harness puts it on every message the session sends as the address to reply to, and no other running session holds it.

- **What a seat records.** The session that runs a seat's loop records its messaging address and its process on the seat's state issue, beside its name.
- **When a worker acts on a message.** Only where all of these hold:
  - the message is meant for the worker's own seat;
  - the directing seat's recorded process still runs on the worker's machine;
  - the message's reply address is the one the directing seat recorded;
  - the worker itself is the session its own seat recorded.

  The list of sessions takes no part in the check.
- **When a loop records itself.** A loop records itself without asking in three cases: the seat has no recorded session, the recorded process has ended, or the recorded process is the loop's own. Otherwise it records only on the person's word. So a restart after the old session closed never asks, and a live session is never replaced without the person.
- **Where any of this cannot be read or compared,** no message counts as a directive, and the tracker carries the work. A loop that cannot read its address tells the person so, once in each session.

## Context

**What stands.** [project-management:DEC-081-delegation-between-seats] lets a worker's directing seat message it, to wake it or to name a ready Task it may take next. The worker counts a message as a directive only where it comes from the session the directing seat's state issue records (DEC-081 point 5), and any other message is information.

DEC-081 point 4 has each seat's state issue record the session that runs the seat's loop: its name, its machine and its folder, in a form the listing's rows can be compared with. The check then requires three things:
- the record names the worker's machine;
- exactly one listed session has the recorded name and folder;
- the message's reply address is that session's address in the listing, or, where the listing gives none, no other listed session holds the sender's name.

DEC-081 rested this on Claude Code's documentation, and had its build measure what the documentation left unconfirmed. Where a measurement did not hold, no message was to be a directive until a record decided again.

**What the measurements found.** Measured on Claude Code 2.1.330 on macOS, and recorded on [project-kit#3461](https://github.com/aleskalfas/project-kit/issues/3461). The numbers are the Task's; its first six are DEC-081's list, and it adds remote control (7) and resuming a subagent by message (8).

- **The listing shows no folder and no messaging address.** Each row shows a session's name, a short reference, its kind, whether it is busy and when it started. That held for a session in a linked worktree, and for one whose shell had moved to a subfolder.
- **A message carries its sender's messaging address and name.** The reply address is the path of a local socket, named after the sending process. The name is the one the session was started with. This was seen on a delivered message.
- **The harness tells the two apart, on a held message.** The notice for a held message marked the address as checked against the sending process, and the name only as claimed. No delivered message showed such a mark.
- **Names repeat.** A second session started under a name already in use is listed beside the first.
- **What a session can read of itself:**
  - A command in its shell reads the session's messaging address, in the form a message carries less a prefix. It reads no name.
  - The session's agent reads its own name and short reference from the first line of the listing. The probe's own verdict said otherwise, since it read the listing's structured output as plain text.
- **On a restart, the address changes.** That includes a session continued or resumed in the same conversation. Its short reference changes too, and its name stays.

Whether a second session under the same name sends under an address of its own was inferred from the different addresses the sessions' shells held, not seen on a message. Linux, Windows and sessions under the harness's remote control were not measured.

**Where each measurement leaves DEC-081.** This is the record that decides again, measurement by measurement:

- **Tools held (1), names (2), and the build's run (6)** hold as DEC-081 reads them:
  - the agent holds both tools as the session's agent;
  - a session's agent can read its own name, which survives a restart;
  - a build's run holds both tools unless denied, so DEC-081 point 2's deny bears weight.
- **The reply address against the listing (3)** did not hold, which left DEC-081's fallback to the sender's name. This record rejects that fallback.
- **The listing's folder (4)** did not hold, so DEC-081 point 5's check cannot pass. This record replaces that check.
- **Held messages (5).** At a terminal, a message from a session in another permission mode was held for the person's approval. It stayed held past the minute the probe set as its deadline. In this measurement's headless cases, every send failed as "not reachable", so they measured nothing about holding; measurement 6 did deliver a message to a run with no terminal. A held or lost message costs only time (DEC-081 point 11), which bears on no check.
- **Remote control (7)** was not measured. A session on another machine fails this record's check, since its process does not run on the worker's machine (point 2).
- **Resume by messaging (8).** At a terminal, a message to a subagent's id resumed it. Headless, the subagent acted on neither of its two instructions, which measures nothing. This bears on DEC-081 point 2's resumes and [project-management:DEC-082-pace-of-subagents]'s count, not on the check.

**Terms.**
- **A session's messaging address** is the address at which the harness delivers messages to a session. The harness also puts it on each message the session sends, as the message's **reply address**. The session can read it for itself, and no other running session holds it.
- **A session's process** is the process the adapter's declaration names for the session, which ends when the session ends ([pkit:ADR-100] point 9). It is named by its id and the time it started, which tells a live process from an ended one, and from another that later took its id (ADR-100 point 6).
- Messaging, the listing, a directing seat and a directive are as DEC-081 defines them.

## Decision

**A seat's state issue records the session that runs the seat's loop by its messaging address and its process, beside its name. A worker counts a message as a directive only where four things hold: the message is meant for its seat, the directing seat's recorded process runs on its machine, the message's reply address is the recorded one, and the worker is its own seat's recorded session. The listing takes no part in the check. A loop records itself without asking only where the seat has no recorded session, or the recorded process has ended or is its own. Where anything cannot be read or compared, no message is a directive, and the tracker carries the work.**

### 1. The state issue records the session's messaging address and process

- **What it records.** The session that runs a seat's loop records, beside its name and machine as DEC-081 point 4 has them:
  - its messaging address;
  - its process.

  It records no folder. The name is the one the session's agent reads for itself, or, where it cannot, the one whoever starts the session gives it (DEC-081 point 4).
- **One form for an address.** A session reads its messaging address in one form, and a message carries it in another. The adapter's declaration brings both into one form before any comparison (Implications). That form names no user, since every reader of the tracker sees it.
- **No address to read.** A session that cannot read its messaging address records its name and machine only. Point 2's check cannot pass on any message from that session, nor on any message that session receives. The session tells the person so, once in each session.
- **Who records.** As DEC-081 point 4 says: only a take for the seat's loop records a session, every seat records its own, and the clone that holds the seat writes it under its claim.

### 2. A message is a directive only where it is meant for the seat and both sessions match their records

- **The check.** On each message, the worker reads its directing seat's recorded session and its own seat's. The message is a directive only where all of these hold:
  1. The message names the worker's seat as the one it is meant for.
  2. The directing seat's recorded process runs on the worker's machine.
  3. The message's reply address is the directing seat's recorded messaging address.
  4. The worker's own messaging address is the one its own seat records.

  The worker reads no listing for the check.
- **The check cannot pass** in these cases:
  - the worker's seat names no directing seat;
  - the directing seat is free;
  - no session is recorded for it, or the record holds no messaging address;
  - the recorded process does not run on the worker's machine, or the worker cannot tell;
  - the message carries no reply address;
  - the worker is not its own seat's recorded session;
  - the harness has no messaging.

  No message is then a directive, and the tracker carries the work (DEC-081 point 1).
- **A session that is not its seat's loop** takes no directive. Such a session is one the person opens in the clone to look at something, as DEC-081 point 4 describes. Its address is not the recorded one, so every message it receives is information.
- **Any other message is information,** as DEC-081 point 5 has it.

### 3. A loop records itself without asking only where no other live session holds the record

- **One rule, at each take for the loop and at each round.** The loop compares its seat's record with its own session. It records itself without asking where:
  - the record holds no session;
  - the recorded process has ended;
  - the recorded process is its own.

  Otherwise, it records itself only on the person's word, given in its own session. The record is then another live session's, and which of two live loops keeps the seat is the person's to settle (DEC-081 point 4).
- **Without that word,** the loop runs unrecorded, and tells the person so. It takes its work from the tracker, counts no message as a directive, and sends none. At each later round it applies the rule again, so it records itself once the other session's process has ended.
- **The log stays short.** A loop whose record already holds its own address and process posts nothing. So the seat's log grows by one comment only when the recorded session changes, as DEC-081 point 4 has it.

### 4. The same check the other way

- **Reports.** A directing seat counts a report as its worker's only where point 2's check passes with the roles swapped:
  1. the report names the directing seat's seat;
  2. the worker's recorded process runs on the directing seat's machine;
  3. the report's reply address is the worker's recorded messaging address;
  4. the directing seat is its own seat's recorded session.
- **Sending.** A directing seat sends only while it is its own seat's recorded session. Each directive names the worker's seat. It goes to the worker's recorded name, and only where the listing shows exactly one session under that name. A directive that reaches another session of that name is information to it, by point 2's first and fourth conditions.

### 5. A guard, not a boundary

The check catches the mistakes of sessions that follow the procedure, and the stray session that shares a name, like the guard on a claim ([project-management:DEC-035-instance-ownership] point 6). It stops no one who means to pass as another. These limits stand:
- The harness was seen checking an address only on a held message.
- Every clone reads the state issue.
- A subagent of a session may send under the session's own address, and a session that switches conversation within its process keeps its address.
- Nothing the harness documents stops a program run under the person's account from posing as another session, or a message's text from imitating the harness's frame.

## Rationale

**Why the messaging address.** The check needs something that passes three tests at once:
- the sending session can read it for itself;
- each message carries it;
- no other running session holds it.

The messaging address passes all three. The first two were seen, the second on one delivered message. The third is inferred from the different addresses the sessions held. The build confirms it, and this record is reopened where it does not hold, since a shared address would let the check pass for the wrong session. The name fails the third test, since names repeat and the harness marks a name only as claimed. The folder fails the second, since no message carries it, and the listing does not show it either.

**Why the process.** On the harness measured, an address is named after its process, and a machine reuses process ids. A record left by a loop that ended could match a later session that gets the same id. A session's process, named by its id and start time, tells a live process from an ended one and from another that took its id (ADR-100 point 6). So checking that the recorded process still runs closes that case, without naming a harness. It also tells the loop whether the record belongs to another live session, which is the only case that needs the person.

**Why one rule for recording, read off the record.** The rule depends only on what the record holds and on whether its process runs. It does not depend on what the agent remembers of earlier rounds, which a compaction can lose. Two live sessions of one seat, such as one conversation resumed in a second terminal, then never take the record from each other: each finds the other's live process, and only the person's word moves the record. A restart after the old session closed, the usual way a loop ends, finds an ended process and records without asking.

**Why a message names its seat.** A directing seat sends by name, and two workers' sessions may share a name. A worker that passes every other condition would otherwise act on a directive meant for its sibling.

**Why the worker checks its own address too.** A session the person opens in the worker's clone takes up the worker's seat (DEC-059 point 4), and may share its name. Without this condition, that session would act on a directive meant for the loop, and two sessions of one seat would take Tasks. The worker reads its own seat's record for the check, so the condition costs no further read.

**Why the record is in clear.** The claim on the same issue already says where the clone lies, by its machine and folder ([project-management:DEC-058-state-issues] point 5). A messaging address in a form that names no user, and a process's id and start time, tell a reader of the tracker nothing more. Hiding them would need a key kept on each machine, a new part of the backbone, for nothing a reader learns.

**Why failing closed is enough.** A message names only what the tracker holds (DEC-081 point 1). So a refused message costs only the time it would have saved. That holds on a platform where the address cannot be read, and where a worker cannot tell whether another clone's process runs. The notice to the person keeps that cost from going unseen.

### Alternatives considered

- **Keep DEC-081's check, and wait for the listing to show folders and addresses.** Rejected: until then no message is a directive, and the harness's documentation promises neither.
- **The sender's name alone,** where no other listed session holds it, DEC-081's fallback. Rejected: a second session can take any name at any time, and the harness marks the name as claimed.
- **The listing's short reference.** Rejected: a session can read its own reference, but no message carries it.
- **The conversation's id.** Rejected: no message carries it. It could tell a resumed loop from a new one, but the recorded process decides that from the record alone.
- **A token the directing seat records and quotes in each message.** Rejected: every clone reads the state issue, so any session can quote the token. The harness puts the messaging address on each message itself.
- **Fingerprints keyed by a secret kept on each machine.** Not taken, as "Why the record is in clear" says.
- **The name as well as the address.** Not taken: the live process closes the reuse of an address, which is what the name would guard.
- **Send to the worker's recorded messaging address.** Not taken: the harness's documentation names no recipient but a session's name or reference.
- **Ask the person before every replacement.** Rejected: a loop's address changes on each restart, and the person would confirm every restart by hand.
- **Record again without asking at a process's first round, where the record holds the same conversation.** Rejected: a resumed conversation in a second terminal would take the record from a live loop, and the rule would rest on the agent's memory of its earlier rounds.
- **Clear the record as the session ends.** Not taken: it would need a hook at the session's end, which may run none of the capability's code ([pkit:ADR-095] point 2). The end of the recorded process shows the same.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([pkit:COR-066] point 5).
  - **Overturned in part.** DEC-081 gains a top line, in one paragraph, and the words it overturns stay as they stood:

    > **Partially superseded by [DEC-084](DEC-084-seat-session-address.md).** A seat's state issue records its loop's session by its messaging address and its process, beside its name, and a worker counts a message as a directive only where it is meant for the worker's seat, the directing seat's recorded process runs on the worker's machine, its reply address is the recorded one, and the worker is its own seat's recorded session; DEC-084 point 2 holds the check whole, with the cases where it cannot pass. Overturned: in the plain-terms summary, "by the session's name and folder"; in the Context's "Where a measurement does not hold", "a reply address the listing does not show falls back to the sender's name (point 5)"; in point 4, "and the folder it runs in, a linked worktree's where it runs in one. They are written in a form the listing's rows can be compared with, in which the folder names no user", and "while the listing shows it"; in point 5, the bullets "The check", "The check cannot pass", "Two sessions or more match" and "The same check the other way"; in the Rationale, "Why a session's name and folder", and, in "Who messaging serves", "where the listing shows no folder"; in the alternative "A token the directing seat writes on its state issue", "so the token tells no more than the name and the folder"; and in the Implications, in the bullet on ADR-071, "names the session's name, machine and folder, in the form point 4 here asks" and "This record is the one editor of each sentence it edits there", and the sentence "No harness requirement is declared". Stands: the rest, among it point 5's "Any other message is information" and "A guard, not a boundary", and the name given by whoever starts a session that cannot read its own.
  - **Refined in place,** each with a forward refinement pointer to this record:
    - **ADR-071 point 5's payload bullet** ([pkit:ADR-071]).
      - It says a session's event names the session's name, machine and folder, in the form DEC-081 point 4 asks.
      - It will say that a session's event names the session's name and machine, its messaging address and its process, in the form DEC-084 point 1 asks.
      - Its pointer will name DEC-084 alone, since DEC-084 is that sentence's one editor.
      - This is a refinement, not an overturn. ADR-071 decides the seam, and its payload sentence carries what the capability's record asks. That decision of ADR-071's stands. The field list it carries is DEC-081's, which this record overturns in DEC-081.
    - **ADR-071 point 4's "What it returns".** It returns, beside the holder, the session the holder recorded. It will say "last recorded", since a loop records again at each restart. The sentence keeps DEC-081's pointer and gains one to DEC-084.
    - **ADR-100 point 9** ([pkit:ADR-100]). It gains a bullet after "The first fact of a live session an adapter declares":

      > **The session's messaging address.** The same declaration gives a command the messaging address the harness gives its session, and says how a message's reply address is brought into the form of that address. So a command of the capability compares them and names no harness (refinement per [project-management:DEC-084-seat-session-address]).

      Its sentence that it decides neither the anchor nor the session's own name stays true.
  - **A fact corrected,** with no pointer, since no decision changes. DEC-081's Terms say the listing lists "each session with its name, its folder and the address a message goes to". They will say "each session with its name, and what tells apart sessions that share one".
  - **No citation changes.** DEC-082 cites DEC-081 point 5's check in point 7, in its Implications and in its Acceptance. Those citations stand: the check keeps its place under DEC-081 point 5, whose top line leads to this record.
- **The harness requirement.** The build declares one ([pkit:COR-047]), as ADR-100 point 12 declares the finding of a session. It is worded so that any harness could meet it:

  > A session can read the address at which the harness delivers messages to it. The harness puts that address on each message the session sends, as the address to reply to. While a session's process runs, no other session holds its address.

  - **Observation point:** inside a session, where a command its shell runs reads the address, and in a message the session receives.
  - **Evidence:** this record's own design, a design dependency (COR-047 point 9). Points 2 and 3 rest on it.
  - **What depends on it:** the check (point 2), the records (point 3) and the reports (point 4).

  The adapter's answer is bounded to the version measured.
- **The build is [project-kit#3461](https://github.com/aleskalfas/project-kit/issues/3461),** DEC-081's build, which builds this record too.
  - **What it builds:** the adapter declaration's new fact, the session's event with its new fields, point 2's check, and point 3's rule in the work loop.
  - **What it measures first, with what follows where each does not hold:**
    - that a second session under the same name sends under a messaging address of its own. Where it does not, this record is reopened before the build goes on;
    - that the process the declaration names is the one the address belongs to. Where it is not, this record is reopened before the build goes on;
    - what reply address a subagent's message carries, which point 5 names as a limit;
    - that a command in one clone can tell whether another clone's session process runs, from where the command runs. Where it cannot, as may be the case inside a sandbox, point 2's second condition cannot pass, and the person is told.
  - **How it relates to #3462.** #3462 builds DEC-082 and depends on #3461. So #3461 also builds the part of ADR-100 point 9's declaration that names the session's process, where #3462 has not yet brought it.
- **Acceptance.** This record overturns the accepted DEC-081 in part, refines ADR-071 and ADR-100 in place, and corrects a fact in DEC-081, so accepting it needs the person's sign-off. That sign-off covers the refinements of the two architecture records.
