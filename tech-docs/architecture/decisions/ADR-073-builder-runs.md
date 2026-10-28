---
id: ADR-073
title: The backbone's working run builds a Task in a sandboxed clone of its own
status: proposed
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** this record is how project-kit builds the build command of [project-management:DEC-062](../../../.pkit/capabilities/project-management/decisions/DEC-062-task-builder.md). The backbone's run command gains a third form of run, a **working run**:
- It runs in a clone the backbone makes and keeps for its caller, which the builder may edit and commit in.
- It loads no settings file. The runner passes the run's own settings, read from the default branch, never from the clone or the Task's branch.
- The operating system's sandbox holds everything the run runs. Writes go only to the clone, reads of the caller's clone are denied, and only the network hosts the project lets a build reach are open.
- Nothing asks: a call no rule allows is refused.

The build command starts the run detached and keeps its state in a file the seat polls. Each ending has an exit of its own, and a question is one of them. The project's checks run in the same sandbox, with no agent. Only checked commits come back, as the Task's branch, and each build is recorded on the Task, which lets the commands that open a pull request, move its Task to Review, ask for the reviews and merge refuse a commit no build produced.

## Context

DEC-062 decides that a fresh builder agent builds each of a worker's Tasks, in a sandboxed clone of its own, under rules that leave the seat's writes to the seat. Its Implications leave the realisation to an architecture record.

ADR-066 gives the backbone one way to start an agent, the runner the project's adapter registers, in two forms:
- **The unconfined form,** for the review command's runs (point 10): in the caller's folder, under the person's and the project's settings, in the mode those choose.
- **The confined form,** for the drift command's fixers (points 3 to 7): in a clone the backbone makes and checks, under only its own settings. Its shell writes only its workspace, and it allows no edit and no network.

Neither fits a build. The unconfined form runs where the builder reads the seat's workspace and can write what the seat's push runs, in whatever mode the settings choose, `auto` among them, which point 4 counts as a bypass. The confined form refuses the edits, the toolchain and the network a build needs.

**Probes on 28 October,** with Claude Code 2.1.303 on Linux, the software-engineering capability's producer agent, a clone of project-kit at `main`, and nothing that could ask:
- **An untrusted clone.** A clone is a folder Claude Code has not trusted, so it ignores the project's allow rules there, and every edit and shell call was refused. With the project's rules passed in a file outside the clone, the builder built a probe Task: one signed commit, tests passed, the clone checked clean.
- **No settings sources.** With no settings file loaded, the project's agents are not found, so the runner must pass the builder's definition.
- **The hook.** The project's permission hook ran, and judged the call as `agent:software-engineer`. A force-push by a refspec was refused as `vcs-history-rewrite`.
- **The run's denies.** Native denies in the run's settings refused `gh` and `git push` despite the project's broad allows.
- **The sandbox.** With it on (bubblewrap), a Python program the builder ran could not write outside the clone, a decoy repository's hooks folder among them. A `Read` deny on the seat's clone made the seat's files unreadable to such a program. A host on the run's list was reached through the platform's proxy, and `uv run pytest` ran once uv's cache sat inside the clone. Without the sandbox, the same program wrote outside the clone.
- **The question.** On a Task it could not build as written, the builder stopped with a question and committed nothing. Resumed in its own session with an answer, it built the Task with its own context of it.
- **The compound commands.** Shell commands outside the project's allows were refused, compound ones among them, and the builder went on with commands the rules allow.
- **The checks with no agent.** Claude Code's sandbox runtime ran the project's tests in the clone under the same rules, with no harness: a write outside the clone failed, the seat's clone and the signing key read as absent, a listed host was reached and another was not. Without bubblewrap it refused to run the command, and still exited 0.

## Decision

**The backbone's run command gains a working form: a run in a clone the backbone makes and keeps for its caller, under only the settings the runner passes from the default branch, inside the operating system's sandbox, in a mode that refuses what no rule allows. The build command starts it detached, gives each ending an exit of its own, brings back only commits the clone's check bears out, and records each build so its provenance can be checked.**

### 1. A working run runs in a clone the backbone makes, and keeps it for the caller

- **The clone** is made as the confined form's is (ADR-066 point 7): no object shared with the caller's repository, outside every working tree, in a folder of the backbone's that only the person's account writes. It is made from the caller's repository, on the branch and at the commit the caller names, and holds the default branch's head too, so a build can merge it.
- **Its only remote is the caller's repository,** which the run cannot read (point 2), so a fetch from it inside the run fails. It carries the caller's commit identity, and no signing settings: the builder commits unsigned, and the build command signs at the hand-back (point 8).
- **The run's folder** is a folder of the clone that version control ignores. The toolchain's caches and the shell's temp folder go in it, since the sandbox writes nothing outside the clone (point 3).
- **Recorded before the run:** its references, its git configuration, its hooks folder and its ignored files.
- **Nothing of the run, or of a check, is left before the check.** The runner ends every process of the run's sandbox, and of each check's (point 5), and confirms none is left, before the clone is checked, before each next check, and before each hand-back. Where it cannot confirm it, the build is not borne out (exit 5), its clone kept.
- **Checked after the run:** HEAD is on the branch the caller named, which descends from the start commit; no other reference moved; the git configuration and the hooks folder are unchanged; the working tree is clean; no ignored file appeared outside the run's folder. Git is read with the clone's own configuration ignored, and an error of git's is a breach (ADR-066 point 7).
- **Kept for the caller.** The clone outlives the run, unlike a confined run's, until the caller removes it.

### 2. A working run loads only the settings the runner passes, from the default branch

- **No settings file** of the person's, the project's or the clone's loads, as in a confined run (ADR-066 point 3). Nothing the builder writes in its clone, a settings file or a hook among them, shapes its own run or a later one.
- **Read from the default branch,** as the backbone resolves it (COR-054), at its head when the build starts, which the build's start event names (point 9), never from the Task's branch:
  - the project's native permission rules for the harness, the allows and the denies its settings file holds
  - the permission model that pkit's hook judges against, and the hook's own code, so the code that judges is never the clone's
  - the builder's agent definition, as the deploy resolves it (ADR-066 point 3)
  - the runner itself and the deploy's resolution of an agent, as a confined run reads them (ADR-066 point 3)
- **What the runner adds:**
  - the build's denies (DEC-062 point 4), as native denies, which fail closed
  - every deny of the settings files the run leaves out, and every deny the model holds for the builder or for every agent (ADR-066 point 3)
  - the denies of the credential files the project's sandbox settings name, to the shell and to the file tools (ADR-008)
  - a `Read` deny on the caller's clone, and on the person's signing key
  - the mode that refuses what no rule allows (`dontAsk` in Claude Code), always passed
  - the harness's own memory turned off
  - an environment that names no signing agent, and a sandbox deny on the signing agents' sockets where they lie, so nothing in the run signs (ADR-066 point 4)
- **Outside the clone.** The runner writes the run's settings, and the hook and model it reads, to a folder of the backbone's that the run does not write.
- **The project's instructions** to the harness are read from the clone, as a build needs them. They grant nothing (point 10).

### 3. The operating system's sandbox holds the run

- **On, and failing closed.** The run's settings turn the sandbox on, and stop the harness at start where it cannot start (ADR-004 point 4). The runner checks the platform first, so a known gap is a refusal (exit 7).
- **Writes:** the clone only.
- **Reads:** the caller's clone and the person's signing key are denied. The rest is as the sandbox leaves it, which is most of the machine (ADR-066's harness observations).
- **Network:** only the hosts the project lets a build reach, a list in project-management's project configuration, read from the default branch. The list is empty by default, so a project names the hosts its toolchain needs. A list entry that reaches where the credentials of the project's remote or of its work tracker reach refuses the build, since a program the builder runs could push or write there with the platform's credentials. The adapter declares that set of hosts for its platform and remote, such as a code host's own host, its API and upload hosts, and an enterprise host's. An entry matches it where either one, a wildcard included, covers the other. Where the adapter declares no set for the project's remote or work tracker, any list that is not empty refuses the build (exit 7), so a host the adapter does not know fails closed.
- **No auto-approval, and no retry outside the sandbox** (ADR-066 point 6, ADR-028).
- **No excluded command.** A command the platform requires outside the sandbox (ADR-027) refuses the build instead, since outside the sandbox it would write the seat's clone. On macOS, where the installed uv cannot run inside the sandbox (ADR-014), a build that needs it is refused until a uv the sandbox hosts is installed.

### 4. What a working run keeps of ADR-066's confinement

| ADR-066 | In a working run |
|---|---|
| point 3, no settings file, a checked definition, no memory | kept, the definition and the rules read from the default branch (point 2) |
| point 4, no bypass: the closed set of flags, the environment, the tools | kept. The closed set gains the resume of a session (point 7). The tools are the builder's definition's, which point 3's check holds to the methodology's shape |
| point 5, the run's rules are denies in the model | kept, for the build's denies. The allows are the project's, not a closed list |
| point 6, the workspace is the only folder the shell writes | replaced: the clone is the folder the run writes, and the network is open to the project's list (point 3) |
| point 7, the clone and the check after the run | kept, and the clone is kept for the caller (point 1) |
| point 8, a run is a leaf, the marker | kept. The marker is set, and starting an agent is among the build's denies |
| point 9, the start report is checked | kept. The hook runs in a working run, registered from outside the clone (point 2) |

### 5. The build command starts the run detached, and the seat polls its state

- **Detached.** A build outlasts the seat's own shell call. So the build command starts a process of its own that asks the backbone for the run, and returns at once with the state `running`.
- **The state file** sits in the capability's git-ignored runtime folder of the seat's clone, and only that process writes it. It names the build's state, its start, the time of the builder's last event, the calls refused so far, the clone, and, once the run ends, the result or the question.
- **Progress.** The run command reports each event of the harness's stream, with its time, to a file the caller names. Where none comes for the run's idle limit, the runner ends the harness, as at its wall-clock limit (ADR-066 point 2).
- **The checks.** Once the run ends, that process runs the checks the project names for a build, in its project-management configuration read from the default branch, in the same clone, with no agent. The adapter's runner runs each inside the same operating-system sandbox with no harness, under the same write, read and network rules (point 3), through the sandbox the harness uses for its own shell (Claude Code's sandbox runtime). Their endings go into the state, and a check that fails where the builder said built is not borne out (exit 5).
- **The checks fail closed.** The runner confirms the sandbox's prerequisites before the first check, and a missing one refuses the build (exit 7). A check's ending is read from a result file that a command inside the sandbox writes in the run's folder, never from the sandbox's own exit. The file is named afresh for each check, after the builder's run has ended, and none of that name may exist before the check starts. So a sandbox that refuses to start reads as a check that did not run, which fails, and no file the builder left reads as a pass.
- **The checks' environment** is the run's: it names no signing agent, and the sandbox denies the signing agents' sockets (point 2).
- **The hand-back** is that process's, once the run and the checks end (point 8), or `--hand-back`'s where it could not sign. Each ending writes its event on the Task (point 9), then the final state.
- **Waiting.** `--wait <seconds>` reads the state, waits at most that long, and exits with the state's code. The seat waits in slices shorter than its own shell call's limit.
- **Recovery.** A session that starts in a clone with a build in its state file goes on from it: waits on a running one, or acts on a finished one. The state file names the process's id. A build whose process is gone while its state is not final is lost: not borne out (exit 5), its clone kept. The first command in the clone that reads the state finds it lost, before any other work, and posts its ending event: where the clone still holds the claim, with a renewal that names the claim's seat and key, as a command's work renews it (DEC-059 point 9, ADR-041), and otherwise with no renewal, so the build's record is complete. So its claim no longer waits, and its lapse limit runs from that renewal. A question stops counting as waiting once `--answer` resumes its build, by the resume event it posts (point 9), not when an answer is posted: the resumed build is a running build, renewed while it runs and lost if its process dies.
- **One build at a time** in a seat's clone. A build started while one runs is refused.
- **The claim.** That process renews the Task's claim while the run runs, renewal shipping no later than lapse (DEC-062's Implications), and stops when the run ends, which the wall-clock limit bounds. So a dead session's Task still returns to the pool, and the claim of a Task whose build waits, on a question or on its hand-back, does not lapse (DEC-062 point 6).

### 6. Each ending has an exit of its own

| Exit | State | When |
|---|---|---|
| 0 | built | the builder's result says built, and the clone's check bears it out |
| 1 | refused | the seat; the Task not In Progress, or, for a fix round (`--fix`, with the verdicts' blocking findings) or a merge (`--merge`), not In Progress or in Review; its owner, its branch, in a project with a topology a seat's working tree not on the default branch, a working tree that is not clean, an agent run's marker, a build already running |
| 2 | usage | a usage error |
| 3 | tracker failed | the Task or its records could not be read or written |
| 4 | unfinished | the builder's result says unfinished, and no call was refused |
| 5 | not borne out | the clone's check found a breach, a check failed where the builder said built, the builder ended with no result and no question, or the harness exited non-zero |
| 6 | needs an answer | the builder's question; or a call the run's rules refused, on a run that ended unfinished, as a permission or a decision question (point 7); or the wall-clock or idle limit, as an environment question |
| 7 | cannot build here | no builder named, no runner, no sandbox, a required exclusion, the runner refused, or the backbone gave no answer, each with its reason |
| 8 | running | `--wait` returned before the run ended |
| 9 | built, not brought back | the hand-back could not sign (point 8) |

- **Precedence:** a breach (5) before anything else; then a question (6); then unfinished (4). A build that is built and whose hand-back could not sign is exit 9, and once a hand-back moves the branch, exit 0.
- **The grammar.** The builder ends its reply with one result block or one question block, whose fields DEC-062 point 5 names. The first block wins, as the review command's first verdict line does. The point's companion schema holds the grammar.
- **The refused calls** come from the harness's own report. The runner asks for its machine-readable output, and the run command's answer document gains the list.

### 7. A question waits on the Task, and the build resumes from it

- **Posted.** On exit 6 the build command posts the question on the Task through the audit-log facility ([project-management:DEC-044](../../../.pkit/capabilities/project-management/decisions/DEC-044-audit-log-facility.md)), with its kind.
- **The session's id.** The run command's answer document gains the harness session's id, and the state file keeps it.
- **`--answer <file>`** resumes the build: the runner resumes that session with the answer as its next message, under settings built again as point 2 builds them, from the default branch's head the build's start event names (point 9), so a resumed run runs under the rules its build began with. The answer is posted beside the question.
- **A refused call that one of the build's denies refused** (DEC-062 point 4) is asked as a decision, never as a permission, since no allow lifts a deny (COR-028 point 1) and the call is the seat's work (DEC-062 point 6).
- **A permission given once** for that build is an allow the runner adds to the resumed run's settings, outside the clone. The record of the answer names it, and the overview of the build command's rules shows it while the build lasts.
- **Advice.** The build command starts the advising agent through the runner in the confined form (ADR-066 points 3 to 7): a clone of its own at the default branch's head the build's start event names, never at the Task's branch, so no build's commit shapes its rules, its definition or its runner (ADR-066 point 3). It is read-only, with no network and nothing that asks. Its pinned commit, for ADR-066 point 3, is that head. Its brief is the build's brief, the question and what the builder found, which the command writes, and it reads the build's work only as the question gives it. The agent is the one project-management's project configuration names for advice, with no default. Where none is named, the person answers advice. Its answer is posted on the Task, and becomes the answer only once the person accepts it. Where the runner has no confined form, the person answers advice too.
- **The fallback.** Where the harness kept no such session, a fresh builder starts with the brief, the question and the answer.
- **Bounds.** The build command never starts a run again on its own. The number of questions a Task's builds may ask is a setting of project-management's project configuration, three by default. A question that reaches the limit is posted, and `--answer` refuses to resume from it until the person's audited override.

### 8. Only checked commits come back, as the Task's branch, never into the seat's working tree

- **After a run that ended built,** once the clone's check (point 1) and the checks (point 5) bear it out, and the seat's clone still holds the Task's claim (DEC-059 point 9), the build command fetches the clone's branch into a temporary reference of the seat's clone. Git's local transport runs no hook of the clone, and the check found the clone's configuration and hooks unchanged.
- **Pinned to what the check saw.** The ending event names the commit the check saw at the branch's head. Each hand-back, `--hand-back`'s included, checks the clone again right before it fetches, with no process of the run left, and moves nothing where the branch's head is not that commit or the check finds a breach (exit 5).
- **Signed at the hand-back.** Where the seat's clone signs its commits, the build command writes each fetched commit again with the same tree, message and author, signed by the seat's clone. Each parent maps through what the hand-back already wrote, the start commit standing for itself, and every other parent, such as the default branch's head under a merge, is kept as it is. The builder never held the key, so a signature says the command brought the commit back.
- **A signature that fails,** such as a key that is locked with nobody to unlock it, moves nothing: the build is built and not yet brought back, its clone kept (exit 9). Its ending event says so, names the commit the clone's check saw at the branch's head, and names no commit as brought back. The build waits on its hand-back. `--hand-back` makes the hand-back again from the seat's session, and posts the hand-back event once the branch moves.
- **The claim while a build waits on its hand-back** does not lapse, as while it waits on a question (point 7, DEC-062 point 6). A release of the seat still frees it. `--hand-back` on a claim the clone no longer holds is refused (exit 1), and the clone is kept.
- **A fast-forward only.** The Task's branch moves only to the commits the hand-back wrote, which descend from the build's start commit.
- **A reference, not a checkout.** The hand-back moves the Task's branch as a reference. In a project with a topology, the seat's working tree stays on the default branch: the commands that start a worker's Task cut its branch without checking it out, and the build command refuses a seat's clone whose working tree is not on the default branch or is not clean. So no tool, setting, hook or instruction the seat runs is a build's.
- **The clone** is removed by the hand-back that brings its commits back, `--hand-back` included. On any other ending it is kept, and the state names it.
- **Nothing is pushed here.** The seat pushes the Task's branch by its reference, with the remote's push hooks of the seat's clone skipped, since a hook that ran the pushed commits would run a build's code outside the sandbox. The project's continuous integration runs the checks again on the pushed head (DEC-062 point 7).

### 9. Each build is recorded on the Task, and provenance is checked

- **A build's record** is its events on the Task, through the audit-log facility, each naming the build:
  - **the start,** posted before the run starts: the start commit, the default branch's head whose rules the build runs under, the builder, and the brief, folded, with its fingerprint, the hash of its bytes;
  - **each ending,** at every exit but 8: how the build ended, the commit the clone's check saw at the branch's head where a check ran, and its question where it asks one (point 7). An exit-9 ending is followed by a hand-back event;
  - **a resume,** which `--answer` posts before the resumed run starts: the question it answers, so the build no longer waits on it. Where the resumed run then cannot start, the ending that follows closes the build;
  - **the hand-back,** once the Task's branch moves: the commits that came back as the Task's branch holds them, with the builder's own ids beside them as a trace.
- **The check.** In a project with a topology, the commands that open a worker's pull request, move its Task to Review, ask for the reviews and merge read the Task's build records. Every commit on the Task's branch that the default branch does not hold must be one a hand-back event names, so a merge build's default-branch commits are never asked for one. A merge of the default branch into the Task's branch is built through the build command (DEC-062 point 1), so it is named too.
- **The override.** Where the person directs a build in the seat's session (DEC-062 point 1), `--bypass-provenance "<reason>"` passes the check at the command it is given to, with an audit comment, and is given again at each of the four, in the override convention ([project-management:DEC-046](../../../.pkit/capabilities/project-management/decisions/DEC-046-override-flag-convention.md)).
- **No security boundary.** The seat writes the records under the account its clone uses, so a seat set on it can write one for work no build made (DEC-062 point 1).

### 10. What stays open

Each item says what holds the intent and what is left ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) point 3).
- **Network egress.** The sandbox checks the host a client names, so it is no control on data leaving (ADR-004). What the run reads, it can send to a host on the list. The platform's credentials for such a host reach the run, as they reach every process.
- **Reads.** The sandbox denies the caller's clone and the signing key, and leaves the rest of the machine readable: the person's other files, and other seats' clones on the same machine.
- **A listed host's credentials.** Where the platform gives every process its credentials for a listed host, a program the builder runs acts there as the account the clones share. The list refuses the remote's and the tracker's hosts (point 3), and the project chooses the rest.
- **The project's instructions** are read from the clone, earlier builds' changes among them. They shape the work, and grant nothing: the rules come from the default branch.
- **The person's own instructions, and an organisation's managed settings,** reach the run, as they reach every run (ADR-066 point 11).
- **The reviewers' runs** are unconfined, in the seat's clone (ADR-066 point 10). A reviewer that checks out the change and runs its code runs a build's commits outside a sandbox, with the seat's access, until a record confines the reviewers' runs.
- **A process the run leaves behind** past its limit, as ADR-066 point 11 states for every run. Started inside the sandbox, it stays inside it, and no check or hand-back runs while one is left (point 1).

### 11. The probe

Before the working form is built, a probe of the harness confirms, on the adapter's tested range and on each platform the adapter supports, the facts of the Context that rest on one run, and these:
- With no settings file loaded, the runner's settings and its definition, the builder starts, signs in and builds.
- The hook's code and the model read from outside the clone are the ones that judge, not the clone's.
- The `Read` deny on the caller's clone reaches a program the builder runs, on each platform.
- No signing agent's socket is reachable from the run, at its default path or one an environment names, and a program the builder runs cannot sign.
- A host in the set the adapter declares (point 3) is unreachable from the run, wildcards on either side included. A project whose remote the adapter declares no set for, with a list that is not empty, is refused.
- The harness's memory is off, and the run reads none of the person's earlier sessions' notes.
- The stream of events gives the time of each event, and the idle limit ends a run that sends none.
- A detached run outlives the shell call that started it, and the limits still end it.
- The runner ends every process of a run's sandbox and of a check's, and can confirm none is left, on each platform.
- A resumed session takes the settings built again, and keeps the run's denies.
- A sandbox that cannot start stops the harness at start.
- The checks' sandbox, with no harness, holds the same rules as the run's on each platform, and a check whose sandbox refused to start reads as failed.

A fact the probe disproves refines or supersedes this record.

## Rationale

**Why a third form.** The unconfined form exists to keep what the review command's runs did before ADR-066 (point 10). A builder is new, and writes. Run in the caller's folder, it reads the seat's workspace, and can write a hook or a configuration that the seat's next push runs as the seat. The confined form holds a run to proposing, and a build needs edits, its toolchain and the network. The working form keeps what the confined form gives that a build can keep: the backbone's clone and its check, the run's own settings, the sandbox and nothing that asks.

**Why the sandbox, not the clone alone.** The run's rules see the commands the builder runs, not what a program it runs does. A probe's program wrote outside its clone until the sandbox was on, and the sandbox then held it, its writes and its reads of the seat's clone.

**Why the default branch.** The Task's branch carries earlier builds' commits, which nobody has reviewed. A build's rules, hook, model or definition read from there would let one build shape the next, which ADR-066 point 3 keeps out of a run nobody watches.

**Why no excluded command.** An excluded command runs outside the sandbox with the person's full access, so it would write the seat's clone. Refusing the build shows the gap, as a confined run's refusal does.

**Why detached, with a state file.** A seat calls commands through its harness's shell, whose calls have a limit far shorter than a build. A state file the seat polls works on every harness, and on every harness's limit. One process owns the file and the hand-back, so a build's commits come back once.

**Why exit codes for each ending.** The seat's loop acts on exits, as it does for every command of the capability. A question has an exit of its own, so the seat never reads the builder's prose to learn that it needs help.

**Why records on the Task.** A build's provenance outlives the session and the clone. The Task is where the seat's work is already recorded, and the audit-log facility already writes there. The brief posted with the record lets every reader of the Task see what the builder was told.

### Alternatives considered

- **The unconfined form, in the seat's clone.** Rejected, as above.
- **A clone of its own with no sandbox.** Rejected: a probe's program wrote outside it.
- **A linked worktree for the builder.** Rejected: it shares the seat's git folder, its hooks and its configuration.
- **The rules, the hook or the definition from the Task's branch.** Rejected: an earlier build could widen a later one's.
- **The project's settings file in the clone, trusted.** Rejected: the builder could edit it.
- **An excluded command where the platform requires one.** Rejected: it runs outside the sandbox.
- **A trailer in each commit, as its provenance.** Rejected: the builder writes the commits, so it would write their provenance.
- **A synchronous wait.** Rejected: the seat's shell call ends first.

## Implications

- **The backbone's run command** gains the working form: the clone it keeps for the caller, its check, the run's settings read from the default branch, and the progress file. Its answer document gains the session's id and the refused calls. The CLI reference documents it.
- **The adapters' runner contract** gains the working form. The Claude Code adapter's runner realises it: no settings sources, the run's settings and definition, the hook from outside the clone, `dontAsk`, the sandbox, memory off, the stream of events and the idle limit, the resume, and the checks' run in the same sandbox with no harness. Its README lists the flags, and its enforcement declaration names what holds a working run and what stays open.
- **A harness requirement** joins the set ([COR-047](../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md)): a process can start an agent unattended in a folder it names, under only the settings it passes, inside a sandbox that bounds writes to that folder, in a mode that refuses what no rule allows. Each event of the run reaches the process with its time, and so do the calls it refused. The process can run a command with no agent inside the same sandbox. Evidence: DEC-062, a design dependency (COR-047 point 9). Each adapter answers it.
- **ADR-066, refined in place,** with a pointer to this record: the Decision's line on its points, point 1's list of what the run command does, point 2's of what a caller passes and gets back, point 9's for the hook in a working run, and point 11's open items.
- **ADR-041, refined in place:** the ownership fold takes from its caller whether a Task's build waits, on a question or on its hand-back, which the build command's events on the Task give, so such a claim does not lapse (DEC-062 point 6).
- **project-management** builds the build command, the point's companion schema with the result and question grammar, the run's rules for the build command, the list of a build's network hosts, its checks, its advising agent and the limit on questions in its project configuration, the state file, the build's events, the provenance check and its override. The commands that start a worker's Task cut its branch without checking it out, and the commands that ask for the reviews and merge gain the provenance check.
- **Each changeset declares its component's change** (PRJ-002): the backbone, the Claude Code adapter, project-management, and software-engineering, which contributes its producer to the point.
- **A platform without a sandbox** refuses builds. A Linux platform needs bubblewrap installed, as the harness's sandbox does. On macOS, a build whose toolchain needs uv is refused until a uv the sandbox hosts is installed (point 3), and the deny on the signing agents' sockets rests on the probe (point 11) on each platform.
- **The project's continuous integration** runs the checks on each pushed head, since the seat's push skips the push hooks (point 8).
- **No migration.** Every change adds.
- **Stands on:** ADR-066, ADR-004, ADR-008, ADR-014, ADR-027 and ADR-028; DEC-062, DEC-059, DEC-056, DEC-044 and DEC-046 of project-management; COR-028, COR-047, COR-053 and COR-054.
