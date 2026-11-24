---
id: ADR-103
title: The backbone alone reads whether a recorded process runs, and says so when it cannot tell
status: accepted
date: 2026-11-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** some parts of the methodology note a process they did not start, and ask later whether it still runs. A seat's loop asks it of the session recorded for a seat ([project-management:DEC-084-seat-session-address] points 2 and 3). The register of a clone's runs asks it of a run's processes ([ADR-100](ADR-100-runs-in-seat-clone.md) point 6). The run command asks it of the process that made a clone a killed run left, before it removes that clone ([ADR-066](ADR-066-unattended-agent-runner.md) point 7). Each asks the backbone, which names every such process one way and answers *running*, *ended* or *cannot tell*.

- **A name** holds the process's id, the start time the operating system fixed when it created the process, and its *process space*, the set of processes in which that id names that process: the machine for one boot or, where the machine has process namespaces, one namespace for one boot. Only the backbone writes names or compares them.
- **Ended** is answered only where the command that asks could have seen the process, from inside the same process space, or where the process belonged to an earlier boot of that command's own machine. Anything else is *cannot tell*.
- **By the id alone.** Where no start time can be compared, a *null signal*, which only tests whether a process with an id exists, may stand in: on a platform the adapter's declaration names, and only once the same signal finds the process of the session the asking command runs in.
- **Failing safe.** Each part says what *cannot tell* means for it, and none treats it as *ended* where that would end, replace or free what a live process holds.

## Context

**Who asks.**
- DEC-084 asks whether a seat's recorded session runs: before a worker counts a message from its directing seat as a directive (point 2), and before a loop records itself in another session's place (point 3).
- ADR-100 asks whether a run's processes live: an entry of the register counts while one does (point 6), a build of a Task whose earlier state names one is refused (point 1), and the run command's call that starts no agent ends nothing of a run whose caller lives (point 2, "A live caller").
- The run command removes a clone a killed run left, a confined run's (ADR-066 point 7) or a reviewer's ([ADR-102](ADR-102-reviews-in-own-clone.md) point 2), once the process that made it has ended.

ADR-100 point 6 names a process by its id and start time. DEC-084 point 2 reads one by its id alone where a null signal was measured to tell. The removal of a confined run's left clone, as built, reads the id alone wherever it runs. ADR-100 point 10 leaves open how a process whose start time cannot be read is read, until a record decides one reading for the register and for DEC-084 alike. This is that record, and it takes in every part that asks.

**What was measured.** On macOS, on Claude Code 2.1.331, recorded on [project-kit#3461](https://github.com/aleskalfas/project-kit/issues/3461):
- From a command inside the harness's sandbox, `ps` cannot run, so no start time is read. A null signal, sent only to test whether a process with an id exists, is refused for a running id and finds no process for a free one.
- From a command outside the sandbox, `ps` reads another session's process's start time, and a null signal is delivered to a running process.
- The session's process ends when the session ends: a null signal finds no process once the session has closed.

**What was not measured, and why it matters.**
- **A process space for each command.** On Linux the methodology's command runs inside the harness's sandbox ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) point 2 and its Implications), and that sandbox may give each command it runs a process space of its own. From inside such a space, an id read outside it names another process, or none. A reading that took "no process with this id" for *ended* would read every live process outside the space as ended, and a seat's loop would record itself over a live session without the person.
- **A start time read twice.** The start time `ps` prints follows the reader's locale and time zone. A start time derived from the boot time and the wall clock shifts when the clock is set. Either way, one process can read as started at two times, and a reader comparing by equality takes a live process for an ended one.
- **A reboot.** A process recorded before its machine restarted has surely ended. A reading that cannot tell the restart from another machine leaves the record unresolved for good.
- **A machine identity that repeats.** A machine's identity copied with a disk image names two machines. A reader that took a space recorded on the other machine for an earlier boot of its own would read a live process there as ended.

**Terms.**
- **A process space** is the set of processes in which one id names one process: on a machine without process namespaces, the machine for one boot; on a machine with them, one namespace for one boot. Its identity tells apart the machine, the boot and the namespace.
- **A null signal** is a signal sent only to test whether a process with an id exists. It delivers nothing.
- **A recorded process** is one a part of the methodology knows only by the name it recorded, not one it started and holds.
- **A part that asks** is any part of the methodology that asks whether a recorded process runs.
- **The reader** is the command whose process asks the backbone for a reading. A person who reads the tracker is *a reader of the tracker*.
- **A session's process** is as ADR-100 and DEC-084 define it: the process of the harness session whose shell runs a command, as the adapter's declaration names it, which ends when the session ends (ADR-100 point 9).

## Decision

**The backbone alone names a recorded process and reads whether it runs, for every part that asks: *running*, *ended* or *cannot tell*, and *ended* only where the reader could have seen the process or its machine has restarted since. Each part says what *cannot tell* means for it, and none acts on it as on *ended* where that would end, replace or free what a live process holds.**

### 1. One reading, in the backbone, of a recorded process

- **One reading.** A part that asks whether a recorded process runs asks the backbone, and reads no process's state for itself. A part that started a process and holds it, such as a runner waiting on its harness, learns its end by waiting on it.
- **Names are the backbone's alone.** Every other part stores and passes a name whole. Whether two names name one process, as a seat's loop asks of its own process and the recorded one (DEC-084 point 3), the backbone answers.
- **Many at once.** A command may ask about several processes in one call, and gets an answer for each.
- **Each answer** gives the state, the reading used (by start time, by the id alone, by an earlier boot, or none) and, for *cannot tell*, why.

### 2. A name holds the process space, the id and the start time

- **What it holds:**
  - the process space its id was read in, as an identity in three parts: the machine, its boot and, where the machine has process namespaces, the namespace. The identity stays the same through one boot, and differs between any two spaces;
  - the id;
  - the start time the operating system fixed when it created the process, never one derived from the boot time or the wall clock, so no locale, time zone or clock setting changes it.

  A part the backbone cannot read is left out of the name.
- **One producer.** The backbone alone writes a name. A part that learns of a process by its id, as from a runner's report or the adapter's declaration of a session, hands the backbone the id, and the backbone reads the rest from the operating system.
- **Tagged with its form.** Each name carries a tag for its form. The backbone keeps reading every form an earlier release wrote, and reads one it does not know as *cannot tell*. The forms are the build's.
- **The machine's identity** comes from a source the operating system keeps for the machine. Point 3's earlier-boot rule rests on that source never repeating across machines. The build measures on each platform whether it may repeat, and where it may, that rule does not apply.
- **Where other clones read it.** A name that goes on the tracker, as DEC-084's does, holds each part of its process space in a form derived for the repository, the same in every clone of it, with no secret key, so a reader in another clone of it on the same machine derives the same value. That form tells a reader of the tracker no more than the machine the claim already names ([project-management:DEC-058-state-issues] point 5), and nothing that stays the same across the person's repositories.

### 3. A reading says ended only where it could have seen the process, or the machine has restarted since

- **The reader's own space** is read first. Where the reader cannot read it, every answer is *cannot tell*.
- **Running:** the reader runs in the recorded space and finds there a process with the recorded id, which started at the recorded time and, where the operating system's table gives its state, has not exited. Where the recorded name holds no start time, or the reader cannot read the found process's, it is *running* only where point 4's reading by the id alone finds the id.
- **Ended:** any of these:
  - the reader runs in the recorded space, reads start times there, and finds no process with the recorded id, one that started at another time, or, where the operating system's table gives a process's state, one that has exited and waits only to be collected;
  - the reader runs in the recorded space, and point 4's reading by the id alone finds no process with the recorded id;
  - the recorded space belongs to another boot of the reader's own machine, which can only be an earlier one, where point 2 lets that rule apply.
- **Cannot tell:** anything else, among it a reader in another space of the same boot or on another machine; no name, or one in a form the reader does not know or without a space; a reading by the id alone that point 4 does not allow; and a read that fails.
- **Never ended by default.** No failed read, and no difference of form, reads as *ended*.
- **One process, two names.** Two names name one process where their spaces and ids are the same and, where both hold a start time, their start times are the same.

### 4. By the id alone, only where declared and where the same signal finds the reader's session

- **Where.** The adapter's declaration names each platform where a null signal was measured to tell a running id from a free one. On any other platform, a reading that finds a process with the recorded id but cannot compare its start time answers *cannot tell*.
- **The guard at each reading.** A reading by the id alone first sends the same signal to the reader's own session's process, as the adapter's declaration names it (ADR-100 point 9). Where the signal does not find it, or the reader finds no session, the reading answers *cannot tell*. So a sandbox that hides processes outside it reads as *cannot tell*, on any platform and harness version.
- **What it answers.** Past the guard, and in the recorded space, it answers *running* where the signal finds a process with the recorded id, which may be another that took the id, and *ended* where it finds none.
- **Versions.** The adapter's answer to DEC-084's harness requirement keeps the versions measured, and the report resolves an answer so bounded *indeterminate*, since it reads no harness's version (the adapters README, "What the report says"). No command reads that version at a reading either, so there only the guard holds.
- **Never imposed.** A start time that can be read is always compared. The declaration permits the id alone, and never makes a command read by less than it can.

### 5. The declaration is data, and the session's values are checked where a reading rests on them

- **As data.** The backbone reads the adapter's declaration of a session as ADR-100 point 9 says: as data, running none of the adapter's code. It names no command to run.
- **The agent's call stands.** A command that finds a session runs on the agent's call, as ADR-100 point 9 has it, whatever the checks below find.
- **The session's process.** Before the backbone names a session's process for DEC-084, it confirms that a process with the declared id runs in the reader's process space, and point 4's guard finds it there by its signal. Where no such process runs there, DEC-084 gets no name, and the guard answers *cannot tell*.
- **The messaging address.** Before the backbone gives DEC-084's check the session's messaging address, it confirms that the address names that process as the declaration says the harness names it (DEC-084's Context, measurement 10). Where it does not, the check gets no address.
- **What it does not close.** The declaration lies in the checkout, which a sandboxed command can write. Rewritten, it could name another process as the session's, or a platform where a null signal was never measured to tell. That is configuration a sandboxed command can write that loosens a guard, a member of [ADR-095](ADR-095-hook-out-of-reach.md) point 1's class not yet mended (ADR-095 point 1, "Its reach"). It is the member ADR-100 point 5 names for what the methodology's commands load from the checkout ("The code they run"), not a new one, and it closes with that member.

### 6. Each part says what cannot tell means for it, within one floor

- **The floor.** No part that asks acts on *cannot tell* as on *ended* where acting on *ended* would end, replace or free what a live process holds.
- **Within it,** each part's own record says what *cannot tell* means for it, and the way out it gives.

## Rationale

**Why one reading.** A process one part records, another reads: a seat's session is recorded by one clone and read by another, a run's caller is named as the run starts and read by a later call of the run command, and a left clone's maker is recorded by one confined run and read by the next. Two readings would write names the other cannot compare, and would meet the hazards of "What was not measured" apart, or not at all. One reading meets them once. It sits in the backbone because the run command, which asks of a run's caller and of a left clone's maker, is the backbone's, and the backbone depends on no capability.

**Why names are the backbone's alone.** A name's form changes with the platform and the release (point 2). A part that compared names itself would compare forms it may not know. It could take one process for two, and have a loop ask the person about its own session, or two for one, and have a loop record itself over a live session.

**Why the process space is part of the name.** A process id means something only within one process space. A hostname does not tell spaces apart: a container and its host can share one, as can a Linux system running inside another operating system and that system. With the space in the name, a reader in another space answers *cannot tell* rather than misread an id, whether or not it knows it runs in a space of its own.

**Why an earlier boot reads as ended.** A process does not outlive its machine's restart. A reader that knows its own machine, and sees that the recorded space belongs to an earlier boot of it, knows the process ended. Without this, every record made before a restart would stay *cannot tell* for good: a seat's loop with nobody to ask would never record itself again, and a slot would stay held. The rule holds only where the machine's identity names one machine, which is why the build measures its source, and the rule does not apply where the source may repeat. On the tracker the identity is derived for the repository with no key, since a reader in every clone must derive the same value, and a key kept on each machine is what DEC-084 declines (its alternative "Fingerprints keyed by a secret kept on each machine").

**Why the start time fixed at creation.** A start time compared by equality must read the same from every reader, on every read, across releases. The operating system fixes a process's start time when it creates the process. Every value derived from the clock or printed for a locale can drift. Tagged with its form and kept readable across releases, a name never makes a live process read as ended because a release changed how it reads.

**Why the id alone needs the session's process to answer.** The null signal was measured to tell on one platform and one harness version. The adapter's answer is bounded to the versions measured, but nothing shows a newer version at a reading: the report resolves such an answer *indeterminate*, and a command in a sandbox cannot reliably read the version it runs under, nor tell from its settings whether it runs sandboxed, since what the settings say and what happens have been seen to differ. A signal sent to the reader's own session's process observes what a list could only claim: where it stops finding a process known to run, no reading by it says *ended*. The start-time reading needs no such guard, since the process space and a failed read already keep it from saying *ended* where it could not see.

**Why the session's values are checked only where a reading rests on them.** ADR-100 point 9's sign errs toward holding: a command that finds a session counts as the agent's. A check of the session's process there would pass the agent's calls as a person's wherever the check failed, as in a process space for each command. DEC-084's record and point 4's guard need the process in the reader's own space, and DEC-084's check needs the address to be that process's, so the checks bind there.

**Why each part decides, within one floor.** *Cannot tell* costs each part differently. A seat's loop pays a question to the person, or a message that does not count. A slot held longer slows a clone, a run left to its caller waits on it, and a kept clone costs disk. Each part knows its cost and its way out, so its own record decides. None of them can undo ending, replacing or freeing what a live process holds, so the floor binds them all.

### Alternatives considered

- **Each part reads for itself.** Rejected: each would write its own form and meet the hazards apart.
- **Trust "no process with this id" wherever a reading answers.** Rejected: from a process space of its own, every live process outside it reads as ended.
- **Guard every reading by finding the reader's own session's process.** Not taken: a command a person runs at their own terminal finds no session (ADR-100 point 9), and would never read *ended*. The process space and a failed read already guard the start-time reading.
- **Declare the places by platform and sandbox state, and trust the reading there.** Rejected: a command cannot reliably tell whether it runs sandboxed, and the label goes wrong silently where the harness's behaviour changes.
- **Check the harness's version at each reading.** Rejected: a sandboxed command may not reach the version, and the version on the path may not be the session's.
- **Read the start time from `ps`'s printed output, or from the boot time and the clock.** Rejected: its value follows the reader's locale, time zone or clock.
- **Treat a record that names the reader's hostname as the reader's machine.** Rejected: a container and its host, or a system inside another, share a hostname, and an id read in one space names another process in the other.
- **Derive the identity on the tracker for each clone.** Rejected: a reader in another clone could not derive the same value.
- **Derive it with a key kept on each machine.** Not taken, as DEC-084's "Why the record is in clear" says: a new part of the backbone, for nothing a reader of the tracker learns.
- **Read the declaration from the installed release only.** Not taken now: the code a command runs comes from the checkout too (ADR-100 point 5), so this alone closes nothing. It goes with that member.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md) point 5). Each refinement below is quoted with its pointer: `(refinement per [ADR-103](ADR-103-process-liveness-reading.md))` in an architecture record, `(refinement per [pkit:ADR-103])` in DEC-084, which cites ADR-100 the same way. A fact corrected takes no pointer.
  - **ADR-100, refined in place:**
    - **Point 2, "The detached process names itself":** its last sentence, which ends "as the runner starts each and reports its id and start time (point 6).", reads:

      > The detached process then names in the state the run's processes as the runner reaches them, the harness and each check's process: the runner reports each one's id as it starts it, and the backbone's run command names it (point 6) (refinement per [ADR-103](ADR-103-process-liveness-reading.md)).

    - **Point 2, "What it holds":** its clause "the run's caller, the detached process, by the id and start time the run command knows;" reads "the run's caller, the detached process, by the name the run command gives it (point 6) (refinement per [ADR-103](ADR-103-process-liveness-reading.md));".
    - **Point 6, "Named so it is not mistaken,"** reads:

      > **Named so it is not mistaken.** The backbone names a process by its process space, its id and, where it can read it, the start time the operating system fixed for it, so neither an id the system gives another process later nor the same id in another process space is taken for it, and the backbone reads whether it lives (refinement per [ADR-103](ADR-103-process-liveness-reading.md)).

    - **Point 9, the bullet "Whether a session's process runs, for DEC-084's check and record,"** reads:

      > **Whether a recorded process runs.** A command that asks whether a process recorded earlier runs, as DEC-084's check and record and the register of point 6 do, asks the backbone. The same declaration names the platforms where a null signal was measured to tell a running process id from a free one, on which the backbone may read a process by its id alone. It names no command to run, and never makes a command read by less than it can (refinement per [project-management:DEC-084-seat-session-address](../../../.pkit/capabilities/project-management/decisions/DEC-084-seat-session-address.md) and [ADR-103](ADR-103-process-liveness-reading.md)).

    - **Point 10, the item "A process whose start time cannot be read,"** gives way to:

      > **When a reading cannot tell.** A refinement of this record, accepted before the register is built ([project-kit#3462](https://github.com/aleskalfas/project-kit/issues/3462)), decides how the register of point 6, the run command's call that starts no agent (point 2, "A live caller") and point 1's refusal act where the backbone cannot tell whether a process lives, and the way out of each. Until then each reads it as a process that lives: the entry keeps its slot, the call ends nothing and a recovery or a hand-back that hears so marks nothing, and a build of the Task is refused, naming the process it cannot read, as "A slot and a Task held by a process that never ends" has it. On Linux, where the methodology's command runs inside the sandbox (ADR-014 point 2), the sandbox may give each command a process space of its own. Then every reading by one command of a process another started cannot tell, until the machine restarts, and each such slot and Task stays held until a person acts. ADR-103's build measures whether it does (refinement per [ADR-103](ADR-103-process-liveness-reading.md)).

    - **Point 11, its second item,** reads:

      > A process's name, as the backbone gives it, tells a live process from one that ended, from another that took its id, and from one in another process space, and two reads of one process's start time, by two processes and from inside and outside the sandbox where both can read it, give one value (refinement per [ADR-103](ADR-103-process-liveness-reading.md)).

    - **Implications, "The adapters' contract," its first sub-bullet,** reads:

      > during a run, the runner holds each process it starts, the harness and each check's, until the detached process has written it into the state, reports its id, which the backbone's run command names and relays by that name to the detached process, and records in the backbone's record of the run what identifies the run's sandbox and each check's (point 2) (refinement per [ADR-103](ADR-103-process-liveness-reading.md));

  - **ADR-066, refined in place:**
    - **Point 1, in what the backbone's run command does, the line on a reviewer's clone,** reads:

      > it makes, records and removes a reviewer's clone, and the folder that holds its run's rules, removing a clone a killed review left only once the process its record names reads as ended, and keeping it where the backbone cannot tell (refinement per [ADR-102](ADR-102-reviews-in-own-clone.md) and [ADR-103](ADR-103-process-liveness-reading.md))

    - **Point 2, in what the caller gets back, the line for a working run as it starts,** reads:

      > for a working run, as the run starts, the path of its progress file, which the run command writes in the run's settings folder under the name the caller gives, and, while the run runs, each process the runner starts, the harness and each check's, by the name the run command gives it from the id the runner reports, each held until the caller has written it into the build's state and lets it go, the run command letting it go only once the caller does, and ending it where the caller's end of the pipe closes (refinement per [ADR-100](ADR-100-runs-in-seat-clone.md) and [ADR-103](ADR-103-process-liveness-reading.md))

    - **Point 7, "Then the files, then the removal,"** its last sentence, "Then it removes the clone, and each confined run first removes any clone a killed run left behind.", reads:

      > Then it removes the clone. Each confined run first removes any clone a killed run left behind, once the process that made it reads as ended, and keeps it where the backbone cannot tell (refinement per [ADR-103](ADR-103-process-liveness-reading.md)).

  - **ADR-102, refined in place:** point 2's "Made, recorded and removed by the run command," its sentence "It removes a clone a killed review left only once the process its record names has ended, told by its id and start time (ADR-100 point 6).", reads:

    > It removes a clone a killed review left only once the process its record names reads as ended, and keeps it where the backbone cannot tell (refinement per [ADR-103](ADR-103-process-liveness-reading.md)).

  - **DEC-084, refined in place:**
    - **The plain-terms summary,** under "When a worker acts on a message": its sentences from "Whether a process runs is read by its id and start time" to "Elsewhere no one can tell." read:

      > Whether a process runs is read by the backbone, which answers that it runs, that it has ended, or that no one can tell (refinement per [pkit:ADR-103]).

    - **The Decision's bold statement:** its sentence "The listing takes no part in the check, and whether a process runs is read as the adapter's declaration says for where the check runs." reads:

      > The listing takes no part in the check, and whether a process runs is read by the backbone (refinement per [pkit:ADR-103]).

    - **Point 1, the bullet "The process's start time,"** reads:

      > **The process's name.** The session's process is recorded by the name the backbone gives it, which holds its process space, its id and, where the backbone can read it, its start time, and which every part but the backbone stores and passes whole (refinement per [pkit:ADR-103]).

    - **Point 2, the bullet "Whether the recorded process runs,"** with its three sub-bullets and its closing sentences, reads:

      > **Whether the recorded process runs** is read by the backbone, which answers that it runs, that it has ended, or that no one can tell. Where it finds a process with the recorded id and cannot compare its start time, it reads by the id alone only where the adapter's declaration names the platform (refinement per [pkit:ADR-103]).

    - **Point 3, the sub-bullet "the recorded process is its own,"** reads:

      > the recorded process is its own, which the backbone tells by comparing the recorded name with the name of the loop's own session's process (refinement per [pkit:ADR-103]).

    - **The Terms, "A session's process,"** reads as below, and its three sub-bullets, "It runs", "It has ended" and "No one can tell", go:

      > **A session's process** is the process the adapter's declaration names for the session, which ends when the session ends ([pkit:ADR-100] point 9). The backbone names it by its process space, its id and, where it can read it, the time it started, and answers whether it runs, has ended, or whether no one can tell (refinement per [pkit:ADR-103]).

    - **The Rationale, "Why the process":** its sentences "A session's process, named by its id and start time, tells a live process from an ended one and from another that took its id (ADR-100 point 6). So checking that the recorded process still runs closes that case wherever the start time can be read, without naming a harness." read:

      > A session's process, named by its process space, its id and its start time, tells a live process from an ended one and from another that took its id. So checking that the recorded process still runs closes that case wherever the start time can be read, without naming a harness (refinement per [pkit:ADR-103]).

    - **The Rationale, "Why the record is in clear":** its sentence "A messaging address in a form that names no user, and a process's id and start time, tell a reader of the tracker nothing more." reads:

      > A messaging address in a form that names no user, and a process's name, tell a reader of the tracker nothing more: the name holds the process's id and start time, and its process space in a form derived for the repository that tells no more than the machine the claim names (refinement per [pkit:ADR-103]).

    - **The alternative "Always read the start time from outside the sandbox,"** reads:

      > **Always read the start time from outside the sandbox.** Not taken: where the capability's command runs outside the sandbox, the backbone reads the start time anyway. Opening a way out of the sandbox for this one read buys little beside the address and the name (refinement per [pkit:ADR-103]).

    - **The Implications, "What it builds,"** reads:

      > **What it builds:** the adapter declaration's new facts, the address's form and the platforms where a process may be read by its id alone, the backbone's reading of a recorded process, the session's event with its new fields, point 2's check, and point 3's rule in the work loop (refinement per [pkit:ADR-103]).

    - **ADR-100 point 9, "A guard, not a boundary":** its sentence "It steers only counts and refusals, so point 5's rule binds it as it binds the folder, and none of it runs." reads:

      > Of what point 5's rule leaves to the folder, it steers counts and refusals, and none of it runs. Its list of the platforms where a process may be read by its id alone, and the session's process it names, which point 4 of ADR-103 signals as its guard, steer more: whether a reading may answer that a recorded process has ended, and so whether a slot frees, the run command ends what is left of a run, or a seat's loop records itself in another session's place. That list is configuration a sandboxed command can write that loosens a guard, a member of ADR-095 point 1's class not yet mended (ADR-095 point 1, "Its reach"), and the same member as the code point 5's "The code they run" names, since both are read from the checkout (refinement per [ADR-103](ADR-103-process-liveness-reading.md)).

    - **ADR-100 point 9, the bullet "The session's messaging address":** after its first sentence it gains "It also says how the harness names an address after the session's process, and the backbone gives a command the address only where it names that process (ADR-103 point 5).", and its pointer names ADR-103 beside DEC-084: "(refinement per [project-management:DEC-084-seat-session-address](../../../.pkit/capabilities/project-management/decisions/DEC-084-seat-session-address.md) and [ADR-103](ADR-103-process-liveness-reading.md))".
    - **DEC-084 point 1, the bullet "No address to read":** its first sentence "A session that cannot read its messaging address records its name and machine only." reads:

      > A session whose messaging address the backbone does not give, since it cannot be read or does not name the session's process ([pkit:ADR-103] point 5), records its name and machine only (refinement per [pkit:ADR-103]).

  - **Facts corrected,** with no pointer, since no decision changes:
    - **DEC-084's Context, measurement 12:** its sentence "The copy of the command that the probe meant to run outside the sandbox ran confined too, so what a command outside it reads was not measured." reads:

      > The copy of the command that the probe meant to run outside the sandbox ran confined too. Measured outside it, a command reads another session's process's start time with `ps`, and its null signal is delivered to a running process.

    - **DEC-084's Implications, "What it still measures,"** reads:

      > **What it measured outside the sandbox:** a command there reads another session's process's start time, and its null signal is delivered to a running process (measurement 12).

- **The build.** [project-kit#3461](https://github.com/aleskalfas/project-kit/issues/3461) builds the reading with DEC-084's check: the backbone's reader and its command, the name's forms, and the adapter declaration's fields for the session's process and messaging address, with its list of the platforms where a process may be read by its id alone. It rests on the backbone's reading, so it lands no earlier than this record. The check already built on its branch reads a process for itself, and gives way to the backbone's reading. [project-kit#3462](https://github.com/aleskalfas/project-kit/issues/3462) has the register and the run command read through it, with the refinement of ADR-100 that point 10's item names. Each part built before the reading, the removal of a confined run's left clone among them, is brought to it by a follow-up Task.
- **What the build measures first,** on each platform the adapter supports, from where the methodology's command runs:
  - that the process space and the start time are read from the operating system there, and that two reads of one process give one start time;
  - whether the source of the machine's identity may repeat across machines (point 2);
  - on Linux, whether the sandbox gives each command a process space of its own;
  - inside the macOS sandbox, whether the process space can be read, and whether the operating system's table gives a start time where `ps` cannot run. Where the space cannot be read there, every reading from inside the sandbox answers *cannot tell*, and DEC-084's check fails closed there. Where the start time can be read there, the id alone is needed nowhere on macOS, and the declaration names no platform for it.
- **No new harness requirement.** The reading rests on the session's process, which DEC-084's and ADR-100 point 12's requirements already name, and on the operating system.
- **Acceptance.** This record refines ADR-066, ADR-100, ADR-102 and the capability record DEC-084 in place, and corrects facts in ADR-100 and DEC-084, so accepting it needs the person's sign-off, which covers those refinements.
- **No changeset and no migration.** The record changes nothing an adopter runs until its build, and each build declares its own changes (PRJ-002).
