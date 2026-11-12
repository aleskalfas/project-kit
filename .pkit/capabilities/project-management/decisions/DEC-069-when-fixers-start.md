---
id: DEC-069
title: A fixer starts where a person runs the drift command at a terminal, or where the project's switch is on
status: proposed
date: 2026-11-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the drift command starts the fixers the project granted where a person runs it at a terminal and watches. Each fixer then runs as a reviewer does, under the person's and the project's settings, in a clone of the repository at the pinned commit of the default branch. With nobody at a terminal, the command starts no fixer and lists what went stale with the command to run, unless the person turned on a switch of the project's. With the switch on, such a run is confined where the confined form is built and the harness holds it, and runs as a reviewer does otherwise. For example, after a merge the project manager's run prints each stale page and `pkit pm fix-drift`, and the person runs that command at a terminal and sees each fixer start and end.

## Context

[project-management:DEC-056-drift-fixers] decides that each fixer's run is confined (point 5), and that a harness unable to confine a run starts no fixer (its Rationale, "Fail closed"). It rejects having the person run the command each time, since nothing would then run after a merge. The probe of [pkit:ADR-066] point 12 found that Claude Code 2.1.310 cannot hold the confined form. With its scrub of credential variables on, it forced the run out of the mode that refuses without asking, and it loaded three plugins the run's settings did not name ([project-kit#2225](https://github.com/aleskalfas/project-kit/issues/2225)). So under DEC-056 no fixer starts on that harness.

The maintainer chose:
- **27 October 2026,** on [project-kit#2234](https://github.com/aleskalfas/project-kit/issues/2234): "b", fixers on request, watched, nothing unattended for now.
- **11 November 2026:** an agent a command starts in its unconfined form is to refuse settings that approve calls without asking. [project-kit#3041](https://github.com/aleskalfas/project-kit/issues/3041) is to build that refusal, and the record it rests on decides which modes count.
- **12 November 2026,** on #2234, of runs nobody watches: "I think that should be possible at some moment to switch it on to run it automatically like review panel. I don't want to change decision then." Asked whether a record should decide that switch now, he answered "yes rework the dec".

Terms:
- A run is *watched* where a person started the drift command at a terminal: its standard input and its standard output are both terminals, the test by which the drift command asks the fixers question (DEC-056 point 2).
- A run's *unconfined* and *confined* forms are the agent runner's two forms ([pkit:ADR-066] points 3 and 10).

## Decision

**The drift command starts the granted fixers where a person started it at a terminal, each in the unconfined form in a clone at the pinned commit, and with nobody at a terminal only where the person turned on the project's switch.**

### 1. A person starts the fixers at a terminal

- **The drift command starts a granted fixer only in a watched run, or where the switch of point 4 is on.**
- **With nobody at a terminal and the switch off,** as in the project manager's run after a merge, it starts no fixer, takes no lock and writes nothing. It lists each stale artefact a granted fixer would take, with its fixer, and the command a person runs at a terminal to start them.

### 2. A watched run is unconfined, in a clone at the pinned commit

- **It takes the form the review command's runs take** ([pkit:ADR-066] point 10), under the person's and the project's settings, in a clone of the repository at the commit DEC-056 point 3 pins, never in the person's checkout. The clone is not provisioned as a confined run's is, since the run's commands share the person's tools and network, as a session of theirs does. No flag that bypasses the permission rules is passed.
- **Its mode is the one those settings or the harness choose,** which may approve calls no rule allows. A call that would ask the person is refused, since nobody can answer it during the run.
- **Before the first fixer starts,** the command says that the fixers run under those settings, and how to stop the run.
- **Its brief says that a person watches the run,** names no temp folder, and tells the fixer to propose only: to keep to the command forms the run's rules allow (DEC-056 point 5), write nothing outside its workspace and run no writer. Those settings, not the run's rules, hold what it may do.
- **Its definition is the one at the pinned commit** (DEC-056 point 3). For a name some place of the methodology ships, the runner passes the definition it picks in the clone. For any other name, the run is refused where the commit deploys no copy of the fixer, since the harness would find the person's own.
- **Its files reach the queue through a guarded copy,** and an entry the copy refuses sets the fixer's proposals aside, as a breach does (DEC-056 point 5).
- **A leaf.** The command starts no fixer whose definition grants a tool that starts agents (DEC-056 point 1), and refuses to start inside a fixer's run.
- **A call its settings stopped is `refused`** (DEC-056 point 3), and those settings join the setup. The command does not read them, so a `none` they caused stands until the person forces the artefact's dispatch.

### 3. A grant counts for every watched run

- **The question** says what the agent does when a person runs the drift command at a terminal, and under whose settings. Where the switch is on, the question and the grant command say that the agent also starts whenever the drift command runs with nobody at a terminal.
- **Every grant counts for a watched run,** one given by command, with no question, included.
- **A grant counts toward a run nobody watches only where the switch is on.**

### 4. A switch of the project's starts fixers with nobody watching

- **Off by default.**
- **The person's to turn on.** The switch is a setting of this capability's project configuration. Only a change of the project's that the person authorises turns it on, and no install, upgrade or migration does.
- **On from the default branch, off at once.** Turning it on counts only from the default branch, at the commit the drift command's run is pinned to, as a grant does (DEC-056 point 2). Turning it off counts at once, from the default branch or from the copy of this capability's project configuration in the working tree of the checkout the run starts from, committed or not.
- **Held at every merge.** Each command of this capability that merges a change into the default branch holds a change that turns the switch on until the person authorises that merge themselves, which an authorisation of merges given up front does not cover. While the switch is on, each holds a change to the grant list the same way, and shows which fixers it grants. A change that turns the switch off is not held.
- **Turning it on is the consent** to runs nobody watches, for each fixer the project granted then or grants later.
- **With the switch on,** the drift command run with nobody at a terminal starts the granted fixers. A run takes the confined form, under DEC-056 point 5, where that form is built and the harness holds it. It takes the unconfined form, which turning the switch on consented to, where no confined form is built or the harness cannot hold one, for its version range, its sandbox, its native deny or its settings schema ([pkit:ADR-066] point 2). A run the confined form refuses for another cause, such as a definition its check refuses or a clone it cannot make, starts in neither form, and is reported.
- **An unconfined run nobody watches keeps point 2's rules,** save what a person watching sees. Every run keeps the bounds of DEC-056 point 4.
- **With several people.** The switch is the project's, so it holds for every person's sessions alike. An unconfined run nobody watches works in the drift command's clone at the pinned commit, under the project's settings there and those of the person whose session runs the command, as the review command's runs take the person's and the project's settings ([pkit:ADR-066] point 10).
- **Reports wait where the person meets them.** In a run nobody watches, the faults of the setup (DEC-056 point 3), the failures (DEC-056 point 4) and a refused copy (point 2) are written to the queue's index and to the count line the landing command shows (DEC-056 point 6, "Visible"). Each such run records there which form it took, or that neither started it.
- **The confined form is the later hardening** of a fixer's run nobody watches, as [pkit:ADR-066] decides that form.

### 5. What stays open is stated

As intent the harness cannot enforce is (COR-028 point 3):
- **An unconfined run** may do whatever its settings let a session do, such as writing outside its workspace, reaching the network, pushing, merging, changing a record's status, running a writer, or starting the harness from its shell. Nothing checks what it changed outside its workspace. A person watching sees which fixers start and how each ends, not each call, and nobody sees a run the switch starts.
- **A terminal tells that one is attached,** not that a person watches. A harness whose shell gives a command a terminal, or an agent that fakes one, can start fixers nobody watches. Only the permission layer can stop such a call, in a mode that asks about a call no rule allows, and no rule this capability ships names one.
- **The hold at the merge.** A direct commit to the default branch passes no merge, so nothing holds it, and only the commit's author vouches that the person turned the switch on. Inside a command, only a prompt at a terminal tells that the person authorised the merge themselves, and an agent can fake a terminal.
- **A proposal's words and a pull request's text** stay open as for a confined run (DEC-056 point 5).

## Rationale

**Point 1, a person at a terminal.** Until the harness holds the confined form, a fixer runs in the unconfined form or not at all. A person who runs the command at a terminal starts each run by their own act, sees which fixers start and how each ends, and can stop the run. The debt does not wait for someone to read the check, since the project manager's run after each merge lists it with the command to run. A terminal tells that a person is there, as the fixers question reads it. A flag would tell less, since an agent passes a flag as easily as a person does.

**Point 2, the reviewers' form, in a clone.** The review command's reviewers run in the unconfined form under the person's settings, so the runner keeps two forms, not three. A fixer still widens what runs, so the person grants it first (DEC-056 point 2), and its proposals stay data (DEC-056 point 6). It runs in a clone, since the person's checkout may be on another branch. Its brief tells it to propose only, since nothing else holds it to that. A harness loads a name no place ships by that name, so only a copy the commit deploys keeps that definition the commit's.

**Point 3, the grant.** The command says what the fixers run under before each watched run, and the person can stop it, so a grant carries no run the person does not see start. What the switch adds, running with nobody watching, is the same for every fixer. So one consent covers it, and the question tells each later grant that the switch is on.

**Point 4, the switch.** Unconfined, a run nobody watches may do whatever the project's settings let a session do, with nobody to stop it. A reviewer runs because someone asked for a review. A fixer would start on every merge with nobody asking for it, and what it proposes waits in a queue that is later applied. So whether a project takes that for the loop after a merge is the person's to judge. The rule is decided here and only the choice is the project's, so a setting carries it, and turning it on needs no new record, as the maintainer asked.
- **Held at the merge.** A change of the project's may be an agent's, and an authorisation given up front would carry it with nobody reading it. While the switch is on, a grant also widens what runs with nobody watching. Turning the switch off only narrows what runs, so it needs no hold, and is safe to read from the checkout's own configuration. COR-066 point 4's key is the like case: a key the default branch holds, with its writers named.
- **The unconfined form where no confined one holds.** DEC-056 fails closed because a run that is unconfined while it appears confined is worse than none. A run in the unconfined form claims no confinement, and turning the switch on consented to it. A run the confined form refuses for another cause shows a fault of its own, not the harness's, so it starts in neither form.
- **The reports.** Nobody watched the run, so its faults wait in the queue and in the count line of the command the person runs at each merge.

### Alternatives considered

- **Each run confined, as DEC-056 point 5 decides.** Not taken: the harness the probe tried cannot hold the confined form, so no fixer would start until one can.
- **Runs nobody watches only once the harness confines them.** Not taken: the loop after a merge would wait on the harness. The switch lets the person take the reviewers' form for it, and the confined form hardens it once held.
- **Watched runs only, with a later record for runs nobody watches.** Not taken: turning such runs on would need a new record, where the maintainer asked for a setting.
- **A flag that says a person started the run.** Not taken: an agent passes a flag as easily as a person does. A rule could deny the flag to agents, whereas none can deny every way of faking a terminal, so hardening the terminal test may weigh it.
- **A confirmation at the terminal before the fixers start.** Not taken: running the command at a terminal is the request, and the command says what the fixers run under before the first starts.
- **A switch for each fixer.** Not taken: what the switch adds is the same for every fixer, and each grant already names its agent and its types.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted. Accepting this record accepts them (COR-066 point 5):
  - **[project-management:DEC-056-drift-fixers]'s top line** reads *Partially superseded by [project-management:DEC-069-when-fixers-start]*. What this record overturns stays as it stands there: point 5's confinement of each run, the Rationale's refusal of every fixer where the harness cannot confine ("Fail closed"), the alternative "The person runs the command each time", and what the summary, the Decision, point 2's question, point 3's brief and point 3's provisioned copy say of when a fixer starts and how it runs.
  - **DEC-056 point 1's last bullet** says an agent with a shell is limited only by what holds its run (point 5, and this record's point 2), where it says by point 5's confinement.
  - **DEC-056 point 6's "A fixer runs no writer"** says a confined run is denied every writer and an unconfined run's brief forbids them (this record's point 2), where it says point 5 denies every fixer every writer.
  - **DEC-056's Rationale, "Why the person grants each fixer,"** says a fixer is an agent with a shell on input a contributor wrote, where it says an agent with a shell, unwatched.
  - **DEC-056's Rationale, "Why a consent, where events need none,"** says neither reason holds for a run the switch starts (this record's point 4), where it says for a fixer, and that no fixer's run meets the second.
  - **DEC-056's Rationale, "Why the brief carries the pull request," and its alternative "The run reads the pull request itself"** say a confined run reaches no network, where they say the run.
  - **[project-management:DEC-029-project-manager-agent-shape]'s "Invocation pattern"** says the backbone's run command starts a fixer in the run DEC-056 point 5 and this record set, where it says confined, with nobody watching, and its refinement pointer names this record beside DEC-056.
  - **[living-docs:DEC-001-living-docs-discipline] point 5** says a provider of the work-tracking role starts the fixer of pages in a run nobody can answer during, where it says in a run nobody watches, with this record beside DEC-056 in its refinement pointer. Its Rationale's heading reads "Why a run a command starts holds rather than guesses".
- **[pkit:ADR-066]** realises both forms for a fixer's run: point 10 says how the drift command makes an unconfined run's clone and copies its files, and points 3 to 8 how a confined run is held.
- **[project-kit#3050](https://github.com/aleskalfas/project-kit/issues/3050)** builds the switch: its setting, the drift command's runs with it on and where their reports go, the words of the question and the grant command while it is on, and each merge command's hold.
- **[project-kit#3041](https://github.com/aleskalfas/project-kit/issues/3041)** is to build the refusal of settings that approve calls without asking. A run the switch starts in the unconfined form is an agent a command starts in that form, so that refusal covers it as it covers a review.
- **The harness requirement DEC-056 names** binds only a confined run. An unconfined run asks nothing of it, watched or started by the switch.
- **This capability's README** lists the commands that merge a change into the default branch, which point 4's hold covers.
- **No migration.** Every change adds, and a project with no switch in its configuration has it off.
