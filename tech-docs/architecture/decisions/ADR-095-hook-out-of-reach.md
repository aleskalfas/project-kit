---
id: ADR-095
title: A sandboxed command alone cannot change the permission hook or widen what it allows
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the permission hook decides, before each tool call, whether an agent may make it. It runs outside the sandbox, yet its code and the permission model it judges by sit in the project's checkout, which a sandboxed command can write. So a confined command could change what judges the calls after it.

This record keeps what a sandboxed command writes away from what judges it:

- **The rule:** code that runs outside the sandbox without a person choosing it never comes from a place a sandboxed command can write. Nothing it reads from such a place widens what it allows, unless a person, shown the widening, makes it.
- **The code:** the hooks the adapter registers, and the decision core, run from a copy of the installed release, in a folder of the person's that no sandboxed command writes.
- **The policy:** the model stays in the checkout, where people edit it. *Realizing* the model, the step that turns it into what the harness enforces, also keeps a snapshot of it out of reach. The hook allows no more than that snapshot. A change in the checkout that narrows the model takes effect at once, and one that widens it waits until a person realizes it.
- **Which snapshot binds** is found from the session's anchor, which the harness sets, through an index kept beside the snapshots. Nothing in the checkout chooses it.
- **With no snapshot,** the hook still gives the guardrail denies and its own asks. Where a snapshot binds but cannot be used, it also asks on every other call.
- **Shared build caches** leave the committed sandbox settings, since the person's later runs execute what lands in them.

**How far it holds.** A sandboxed command alone cannot change the hooks, the core or a snapshot, nor make the hook allow more than the snapshot. The bound does not hold against code that runs outside the sandbox and loads what a sandboxed command wrote, such as the methodology's own commands wherever they run outside it, nor against a command the sandbox exempts. Point 7 names each such gap, and the permission overview reports them.

**What it rests on.** The harness keeps its own settings files out of a sandboxed command's direct reach. Of the gestures that write those files from sources in the checkout, this record mends only realizing (points 3 and 7). A probe confirms the precondition with the other facts point 6 names. If it disproves the precondition, a later record supersedes this one whole.

## Context

**What prompted it.** [project-kit#3178](https://github.com/aleskalfas/project-kit/issues/3178) found that no part of the permission layer lies out of a sandboxed command's reach. The parts are:

- the hook, which the harness runs before each tool call, and the adapter's other hooks, which it runs the same way;
- the decision core, which the hook and the permission commands share ([ADR-003](ADR-003-permission-core-code-home.md));
- the model ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) point 1), and every other input from which the core reads a verdict.

All of them sit in the checkout, and a sandboxed command writes its working folder. The harness runs hooks outside the sandbox, with the person's full access, as it runs file tools and connected servers. Both facts come from the harness's documentation, as [ADR-066](ADR-066-unattended-agent-runner.md)'s Context records it.

**Why it matters.** A boundary is only as strong as what enforces it. Whatever changes the hook, the core or the model changes what every later call is judged by. The intent axis would then rest on a boundary the confinement axis lets the agent move: the boundary believed but absent that [ADR-004](ADR-004-autonomy-intent-confinement.md) point 4 forbids.

**What it builds on.**

- **The guardrails** all come from the backbone's catalog, since a capability may not define one ([ADR-021](ADR-021-capability-contributed-privilege-definitions.md) point 3). So a release's catalog holds every guardrail that release ships.
- **A folder only the person writes.** ADR-066 point 7 keeps a run's clone in a folder of the backbone's, outside every checkout, that only the person's account writes.
- **The session anchor** is set by the harness when a session starts, and no change of folder moves it ([ADR-034](ADR-034-foreign-repo-mutation-guard.md) point 1). A command line can clear it for the commands it starts (ADR-034 point 5).
- **The entry point** picks which release serves a command, by the checkout it runs in and by the project's pin ([ADR-039](ADR-039-pkit-entry-point-router.md)).

**uv's cache.** The uv toolkit's write allowance to uv's shared cache is classed narrowing. So setup applies it unasked ([ADR-008](ADR-008-confinement-allowances.md) point 3), and it lands in the committed settings ([ADR-029](ADR-029-move-mutable-sandbox-state-out-of-tracked-settings.md) point 1). Yet the person's later uv runs, outside any sandbox, execute what lands there (ADR-066's Rationale, "Why a command that starts `uv` fails on Linux"). On macOS, uv cannot run inside the sandbox at all ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) point 2), so the allowance serves no sandboxed uv there.

## Decision

**Nothing a sandboxed command can write becomes code that runs outside the sandbox unchosen, or widens what such code allows unless a person shown the widening makes it. So the adapter's hooks run from a copy of the installed release, out of reach, and the permission hook allows no more than the model a person last realized.**

- **What this record mends:** the hooks the project's settings register, and the decision core (point 2); the snapshot the hook judges by, how it is chosen, and what realizing writes (points 3 and 4); and the write allowances the backbone writes (point 5). The rest of point 1's class stays open (point 7).
- **Its precondition.** The harness keeps its own settings files out of a sandboxed command's direct reach. They register the hooks and hold the native denies that [ADR-002](ADR-002-permission-realizer-ownership.md) point 3 relies on. No accepted record establishes this, so the record states it as a precondition, which the probe confirms (point 6). If the probe disproves it, a later record supersedes this one whole.

### 1. What a sandboxed command can write is never trusted outside the sandbox

- **The rule.** Code that runs outside the sandbox without a person choosing to run it never comes from a place a sandboxed command can write. Policy or configuration that such code reads from such a place may narrow what it allows, and widens it only where a person, shown the widening, makes it. Nor can a sandboxed command choose or redirect where such code writes.
- **Chosen and unchosen code.** A person chooses code only when they run the agent's work in the checkout as that work, its tests or its build for instance. All other code that runs outside the sandbox is unchosen: a hook, a tool's own configuration, a build a tool takes from a shared cache, and the methodology's own commands, whoever calls them, since a person who calls one means the methodology's code and not what a sandboxed command left in its place. The code that a command the sandbox exempts runs on an agent's call is unchosen too.
- **A write allowance,** an allowance that opens a place to sandboxed writes, widens the boundary where it opens a place this rule keeps out of reach, however it was classed.
- **Its reach.** The rule binds every later decision of the project's, and the members of its class that points 2 to 5 mend. Every other member stands as the record that decides it says, until a record applies the rule to it. Point 7 names each.

### 2. The hooks and the decision core run from a copy of the installed release

- **The copy.** The harness runs each hook the adapter registers from a copy in the *backbone's state folder*: a folder of the person's where the backbone keeps its own state, outside every checkout, which only the person's account writes, as ADR-066 point 7 keeps a run's clone. It lies outside the folders a sandboxed command writes by itself (ADR-066's Context), and no allowance the backbone writes opens it (point 5).
- **What the copy holds:** the adapter's hooks, the decision core, the release's catalog, and what they need to start. Each starts an interpreter named by a path fixed when the copy is made, never looked up on the session's path, so that it loads no code from the session's environment or working folder.
- **Who makes it.** The gesture that turns the hook on makes the copy from the release installed on the machine, anew each time it runs, and realizing makes it anew where it is older than that release (point 3). Each replaces the copy whole, and keeps the snapshots of point 3. Neither runs code from the checkout. Each makes the copy only outside the sandbox, and inside it makes nothing and says so.
- **The source stays where it is.** The core keeps the home ADR-003 gives it, and the hooks their home in the adapter. The release bundles both from there ([ADR-033](ADR-033-official-install-bundles-content.md) point 1), and the copy is made from what the release bundles.
- **The registration.** In a project that turns the hook on, the committed settings register each hook the adapter registers from the copy, since running the hook is the project's choice (ADR-002 point 2). They name the copy by a location each machine resolves for its own person, never by a path in the checkout.
- **A machine with no copy.** There the hooks cannot start, which for the permission hook is the loud fault of ADR-002 point 4. The permission overview's self-check reports it (ADR-002's Implications), and names the gesture that makes the copy. The overview also reports a copy older than the installed release.
- **Served from the installed release.** The entry point serves from the installed release, whatever the checkout or its pin say, each permission command that reports a verdict or the bound, realizes the model, or turns the hook on or off (ADR-039). Each loads the core from that release, as the workspace removal command takes its code from the running backbone ([ADR-060](ADR-060-path-scoped-workspace-allow.md) point 8). Every other permission command loads the core from the release that serves it, never from the project's tree.
- **Code at the release, content at the pin.** The code of those commands is the installed release's, while the model they read is the checkout's, at whatever version the checkout pins. So each reads the model only as far as its release reads it whole: a command that reports names what it could not read, and one that writes refuses.
- **One verdict.** The core chooses the snapshot that binds a session, judges each call by it and by the checkout's model, and combines the two verdicts (point 3). The hook acts on the core's verdict, and adds the adapter's own verdicts (point 4). So a command that reports a verdict reports the core's, which is why ADR-003 keeps the decision in the core. What turns on the harness stays in the adapter: how an ask meets the session's mode ([ADR-025](ADR-025-segment-conservative-bash-allow.md) point 7), the adapter's own asks, and its guard on itself.
- **Two copies of one source.** The hook's copy and the commands come from one installed release while the copy is current, which the gestures that make it keep, and the overview names a copy that is not. The shared conformance tests hold every caller of a release to one verdict.
- **What the hook reads, and from where.** Its code, the release's catalog, and point 3's index and snapshots come from the backbone's state folder. It takes the session anchor as the harness gives it, and reads the checkout's model from the folder the anchor names. With no anchor it reads no checkout, and gives only point 4's verdicts.
- **What the hook writes,** it writes only into the backbone's state folder.
- **Its runtime** stays a zero-dependency script (ADR-014 point 1).
- **Its scope.** This point governs the hooks the project's settings register. A working run's hook, which its runner registers from outside the run's clone, stays as [ADR-073](ADR-073-builder-runs.md) point 2 decides (point 7).

### 3. The hook allows no more than a person last realized

- **The model stays in the checkout.** It is the source of truth that people edit, review and commit (COR-028 point 1).
- **Realizing keeps a snapshot.** Realizing turns the model into what the harness enforces (COR-028 point 2), through an operation the methodology's commands provide (COR-028's Implications). It also keeps a *snapshot* of the model of the folder it realizes, in the backbone's state folder, and records that folder in an *index* there. The snapshot holds, as the checkout held it, every input from which the core reads a verdict, wherever the core reads it, the subject a call is judged for among them, and it records its own layout. Each write replaces a snapshot, or the index, whole.
- **The folder it realizes** is the one the person runs the realizing command in, or names to it, never a root it looks up. Realizing refuses a folder that holds no model, and shows the folder it realizes.
- **The folder's identity.** With each folder, the index records an identity of it that no command inside the folder can change, and that no later folder at its path shares.
- **Which snapshot binds.** A session is bound by the snapshot of the nearest realized folder that holds its anchor. The hook finds it through the index, by the anchor's path as the harness gives it, following no link, and reads nothing in the checkout to choose it.
  - So a bound realized for a folder holds every session anchored in it or below it, a worktree made inside it or a repository kept inside it among them, unless a nearer folder below is realized.
  - Where that folder's identity does not match the index, its snapshot cannot be used (point 4), and no folder further up stands in for it.
  - Where no realized folder holds the anchor, or there is no anchor, no snapshot binds (point 4).
- **Which checkout judges.** The hook reads the checkout's model from the folder the anchor names, whatever folder a call works in. Where a subagent works in a worktree under an anchor in its parent's checkout, the parent's snapshot and model judge its calls, and a narrowing that only the worktree holds does not reach them.
- **The verdict.** The core judges each call twice, by the snapshot and by the checkout's model, and gives the stricter verdict: deny is the strictest, then ask, then abstain, then allow. Where the snapshot allows a call and the checkout's model abstains on it, the core asks, as for a grant the checkout revoked. Where the two give one verdict, its reason names what each names.
  - **A change in the checkout that narrows the model** takes effect at once: a new deny denies, and a revoked grant asks until it is realized.
  - **A change that widens it,** such as a new grant or a more permissive active profile, takes effect only once realized.
  - **A sandboxed command** can thus make the hook stricter, and never less strict than the snapshot.
- **The order, and the budget.** The hook first gives what reads nothing in the checkout: its own verdicts by the copy's catalog (point 4), then the snapshot's judgement. Only then does it read the checkout: the model's judgement, and the guardrails of the checkout's catalog. All of it runs within a budget, a share of the harness's limit for a hook, and when the budget ends the hook gives the verdict it has.
- **When the checkout's model fails.** Where it will not load, faults in the core, or does not finish within the budget, the hook judges by the snapshot alone. That drops only a narrowing not yet realized, which holds only while the checkout holds it in any case.
- **The reason names realizing.** Whenever the snapshot refuses what the checkout's model would allow, the hook's reason says so, and names the realizing command.
- **Only realizing widens.** Only the realizing command writes a snapshot, and the gesture that turns the hook on where no snapshot exists yet, which shows what it writes as realizing does. A command that writes the model realizes nothing, and says what it left unrealized. The realizing command:
  - shows each place where what it would write, the snapshot or the harness's native rules, allows more than what is in place, and counts as a widening any place it cannot compare;
  - judges the conformance calls by the snapshot it would write, with the copy's core and within the budget, and writes nothing where that fails;
  - runs no code from the checkout, and is served from the installed release (point 2);
  - realizes only outside the sandbox, and inside it realizes nothing and says so.
- **An interlock on widening.** Two guards keep an agent from realizing unasked:
  - **In the gestures.** Where a session anchor is set at all, even empty, the realizing command and the gesture that turns the hook on write nothing that allows more than what is in place, and the gesture that turns the hook off does nothing. Each refuses so, and names the person's own terminal. A realizing that only narrows goes ahead.
  - **In the hook.** The hook asks before a shell call it recognizes as one of those three gestures, in every mode (point 4).
  - **An interlock, not a boundary,** as ADR-034 point 5 declares its guard: a command line can clear the anchor, and a form of the call the hook does not recognize passes its ask. Whether realizing a wider model takes a person's gesture, as a boundary, is decided with [project-kit#3179](https://github.com/aleskalfas/project-kit/issues/3179).
- **A narrowing not yet realized** holds only while the checkout holds it. The overview reads the snapshot back (COR-028 point 2), and names each place where it allows more than the checkout's model.
- **Across releases.** The copy's core reads snapshots in its own release's layout. Remaking the copy carries each snapshot into that layout, working from the snapshot alone, and names any it could not carry. Such a snapshot cannot be used (point 4) until its folder is realized again.

### 4. The hook's own verdicts hold in every state

- **What they are:** the verdicts the adapter's hook gives without a model.
  - **The guardrail deny,** the hook's half of the double lock (ADR-002 point 3), for every guardrail of the copy's catalog, and of the checkout's where it loads within the budget.
  - **Each ask the adapter makes of its own,** as the record that decides it says. Such are the ask where a shell call may hide a guardrail (ADR-025 point 7), sought among the same guardrails, and the ask before a file tool writes outside the session's repository, the adapter's realization of ADR-034 point 2, which holds in every mode ([project-kit#2004](https://github.com/aleskalfas/project-kit/issues/2004)). The ask before a shell call of a gesture of point 3's interlock is another.
  - **Its guard on itself.** The file tools run outside the sandbox. So the hook denies a file tool's write into the backbone's state folder or into the installed release the copy is made from, by whatever path reaches them, and asks before a file tool writes any settings file the harness loads. Each holds in every mode, whatever the model allows.
- **Apart from one another.** Each of these runs on its own, so a fault in one drops neither the others nor a model's verdict.
- **No snapshot.** Where no snapshot binds the session (point 3), the hook allows nothing by the model, gives its own verdicts, and abstains on every other call, so the harness's native rules decide it. Each ask and deny it gives says that the model is not in force, and names the realizing command.
- **A snapshot that cannot be used.** Where a snapshot binds the session but the hook cannot judge a call by it, the hook asks on the call, in every mode, unless one of its own verdicts denies it. Its reason says that the bound is not in force, and names the realizing command. The hook cannot judge by the snapshot where:
  - the folder's identity does not match the index, or the snapshot's layout is not the copy's (point 3);
  - the snapshot will not load, or judging the call by it faults or does not finish within the budget.
- **Faults.** A fault in judging by the checkout's model or in one of the hook's own verdicts, or a payload the hook cannot read, is a decision fault (ADR-002 point 4): what faulted gives no verdict, and the rest stand. Where none stands, the hook abstains (ADR-002 point 3). A snapshot the hook cannot judge by is no decision fault but the state above, since the snapshot is the bound. A hook that cannot start stays the loud fault of ADR-002 point 4.

### 5. A write allowance is narrowing only where nothing outside the sandbox runs what it lets in

- **The test.** A write allowance is narrowing only where no code outside the sandbox later runs, or reads as configuration, what a sandboxed command writes through it, unless that code first checks it against a value no sandboxed command can write. Every other write allowance is widening, and ADR-008 point 4 governs it: never committed, never applied unasked, always reported.
- **A shared build cache fails it.** A tool builds and installs from its shared cache what the person's later runs execute, outside any sandbox, without such a check. On macOS the session's own uv runs outside the sandbox too. So no toolkit carries an allowance for a shared cache, and no gesture of the backbone applies one. The overview names such an allowance as a widening wherever it finds one.
- **The state folder and the release.** No gesture of the backbone writes a write allowance that reaches the backbone's state folder or the installed release, whatever the data naming it says. The overview names one wherever it finds it.
- **A cache for each checkout passes it.** Where a tool runs inside the sandbox, setup gives each checkout's sandboxed runs of it a cache of their own, which nothing outside the sandbox runs from. It does so only where no command that starts that tool runs outside the sandbox. The setting is per machine ([ADR-032](ADR-032-per-machine-activation-routing-axis.md) Rule A).
- **On macOS** uv cannot run inside the sandbox, so losing its shared cache costs nothing there.

### 6. The tests, and the probe

- **Tests hold that a sandboxed command or a file tool, alone:**
  - cannot write the hooks' copy, the core it runs, a snapshot or the index;
  - cannot change which snapshot binds a session, by breaking, moving or redirecting what marks the checkout's root;
  - can change, break or stall any input of the checkout's model, and never make the hook give a verdict less strict than the snapshot's, nor keep it from judging by the snapshot within the budget;
  - meets, where no snapshot binds, the guardrail deny and the hook's own asks, and, where a snapshot binds but cannot be used, an ask.
- **Tests also hold:**
  - every command that reports a verdict reports the core's verdict, which the hook acts on;
  - the realizing command and the gestures that turn the hook on or off run no code from the checkout, take no route that data in the checkout chooses, and refuse under an anchor what point 3's interlock refuses;
  - the realizing command shows what it would write to the native rules, and writes no snapshot that the copy's core cannot judge within the budget;
  - no write allowance the backbone commits fails point 5's test, and none it writes reaches the backbone's state folder or the installed release.
- **The probe.** A probe confirms the facts below on each harness release and platform, as ADR-066 point 12 does for an agent's run. On a release or platform no probe has confirmed, they rest on the harness's documentation, and the overview reports the bound as unconfirmed there.
  - the precondition: the harness keeps its settings files out of a sandboxed command's reach, and whether it keeps those of a checkout nested in the command's working folder;
  - hooks run outside the sandbox;
  - the harness gives the hook the session anchor it set when the session started;
  - the committed registration finds the person's copy at the checkout's root, in a subagent working in a worktree, and in a session started in a worktree, and which anchor each has;
  - no folder a sandboxed command writes by itself, and no allowance the backbone ships, reaches the backbone's state folder or the installed release;
  - the platform gives each folder an identity that no later folder at its path shares;
  - a hook's ask prompts in every mode, whatever the native rules allow, and refuses a call where nobody can answer it;
  - a tool that runs inside the sandbox works with a cache of its own for the checkout;
  - the hook's judgements stay within its budget on the project's own model.
- **A fact the probe disproves** refines or supersedes this record, as the change to the decision requires. Where it disproves the precondition, a later record supersedes this one whole.

### 7. What stays open

Each member of point 1's class below stands as its record decides, until a record applies point 1 to it (point 1, "Its reach"). Each gap is reported rather than hidden, as COR-028 point 3 asks. The permission overview and the adapter's enforcement declaration state each one that bears on the bound, for each platform.

- **Code that runs outside the sandbox and loads what a sandboxed command wrote.** A sandboxed command followed by such code reaches past the bound, the copy and the snapshots included.
  - Such code includes the methodology's own commands, which load code and configuration from the checkout, wherever they run outside the sandbox: on the person's call on every platform, and on an agent's call where the platform exempts them, as on macOS.
  - It also includes the code and configuration the harness and other tools run or load on their own, the adapter's hooks among them in a project that has not turned the permission hook on.
- **A command the sandbox exempts.** An agent's call of it runs outside the sandbox, and the bound holds against that call only as far as the hook's judgement of it, which is no boundary (ADR-014 point 3).
- **The writers of the harness's settings.** The native rules decide every call the hook abstains on. The harness keeps its settings files from a sandboxed command's direct writes, and realizing shows and interlocks what it writes there (point 3). The other gestures that write those files from sources in the checkout, such as the settings merge and the sandbox settings writer applying the project's own lists, do not yet widen only as realizing does. ADR-008 point 3 states the second.
- **Who realizes.** Until project-kit#3179 is decided and built, only point 3's interlock keeps an agent's call outside the sandbox from realizing a model that a sandboxed command widened.
- **A working run's hook** is bounded by the model at the default branch's head, read from the repository's history, and not by a model a person realized (ADR-073 point 2). ADR-073 point 10 states it.
- **The entry point's other routes.** For every command that point 2 does not serve from the installed release, data in the checkout chooses the code (ADR-039 routes 1 and 2), which ADR-039 states.
- **A clone made for an agent's unconfined run,** such as the drift command's, lies outside every realized folder, so its hook gives only its own verdicts. Nothing keeps such a clone out of the folders sandboxed commands write. ADR-066 point 11 states both.
- **The session's environment.** The registration finds the copy, and the person's gestures find the installed release, through the environment the person's session or terminal starts with. Tooling of the person's that sets that environment from the checkout reaches both.
- **A checkout at an older commit,** from before this record's build, registers the hooks as it did then. The overview reports such a registration.
- **An install from source.** Where the methodology runs from a source checkout (ADR-033 point 2), the release the copy is made from is that checkout. There the bound holds only between the gestures that make the copy, and the checkout bears the loud faults and the realizing steps all the same.
- **What runs outside every sandbox,** such as the person's own terminal, can write the backbone's state folder. The sandbox bounds only what it confines.
- **A working folder or a write allowance over the backbone's state folder or the installed release,** by its path or through a file the platform shares between folders, opens it to sandboxed commands. The overview says so where it finds one.
- **A nested realized folder.** A sandboxed command writes every folder below its working folder, so a realized folder nested in another checkout lies in that checkout's reach. Replaced, it gets point 4's asks until it is realized again.
- **The copies sync carries.** The hooks and the core propagate into a project's tree with the trees they live in, and run nowhere there.
- **A narrowing that blocks.** A sandboxed command can narrow the checkout's model until the hook refuses or asks on every call, the calls that would repair it among them. Only the person's own terminal then recovers the session. It widens nothing.

Follow-up issues linked from project-kit#3178 hold the code and configuration of the first item, the writers of the harness's settings, a working run's hook, a clone made for an agent's run, and whether sync goes on carrying the copies that run nowhere.

## Rationale

**Why the rule turns on who chose the code.** A person who runs the checkout's tests from their terminal runs what a sandboxed command may have written, and knows it: the checkout is the agent's work, which they review and run as such. A rule against all of that would bind no project. What the sandbox's bound needs is narrower: no code a person did not choose to run as the agent's work comes from where the agent can write. A person who calls a methodology command means the methodology's code, so that code is unchosen even on their call. Point 1 covers where such code writes as well as what it runs, since a write a sandboxed command can redirect changes a file it could not write itself.

**Why policy as well as code.** The model decides what the hook allows. A sandboxed command that could widen the model would gain what changing the code gains, without touching the code. So the rule covers both: the checkout may narrow at once, and only a person shown the widening widens.

**Why the code runs from a copy of the release.** Three ways keep the code out of reach: deny writes to its files where they lie, read it from history, or run it from elsewhere.

- **Denying sandboxed writes where the files lie** fails each command that moves a working tree across a change to them, such as a branch switch, a pull or a rebase, and sync where sync runs inside the sandbox. Such a command may stop partway. The harness's own settings files bear the same cost, but they seldom differ between branches, while the permission layer's change with each upgrade and each new grant. The file tools, which run outside the sandbox, would still need a guard of the hook's own.
- **Reading from the default branch** reads a git folder that sandboxed commands can write (ADR-066's Context).
- **The release** is installed outside every checkout, by a person. The installed release itself serves the commands that copy it, realize the model and report the bound, so data in the checkout cannot choose which release that is, though the session's environment can (point 7).
- **The cost:** a change to the hook or the core reaches a session only once it is released, installed and copied. Tests and CI still run the checkout's code, and in an install from source the release is the checkout.

**Why every hook the adapter registers runs from the copy.** Each runs outside the sandbox with the person's access, so any of them left in the checkout could rewrite the copy and the snapshots. They are scripts with no dependency, so the copy takes them as it takes the permission hook. In a project that has not turned the permission hook on, there is no bound to keep, and its hooks stay where the project registers them (point 7).

**Why those commands are served from the installed release.** The entry point picks a release by data in the checkout: a source checkout's own code, or the project's pin (ADR-039 points 1 and 2). For the commands that make the copy and realize the model, that data would choose the code a person trusts to widen what the hook allows. For those that report the bound, it could choose a release that knows nothing of the copy or the snapshots, and so reports nothing. Served by the installed release, the choice stays with the person who installed it. The cost is ADR-039 D1's lock: the code is the installed release's while the model is the checkout's at its pin, so these commands read only what their release reads whole. The commands that only write the model keep the entry point's routes: they write the checkout, which a sandboxed command writes anyway, and nothing they write widens the hook until it is realized.

**Why the core gives the hook's verdict, and chooses its snapshot.** ADR-003 keeps the decision in the core so that its callers never diverge. Choosing the snapshot, judging by two models and combining the verdicts is decision, so it lives there too, and a command that reports a verdict reports the core's. The adapter adds only what turns on the harness. The hook's copy can lag the installed release, so the overview reports when it does.

**Why the registration stays committed.**

- **Committed,** it reaches every clone and worktree, and running the hook stays the project's choice (ADR-002 point 2). Where a machine has no copy, the hook's failure to start is loud.
- **The cost:** each collaborator who pulls it meets that loud fault on every call, until they install the methodology and make the copy.
- **In each checkout's local settings,** a fresh clone or a new worktree would run with no hook and no fault.
- **In the person's own harness settings, outside every checkout,** with the project's choice kept beside the snapshots. This covers every clone and worktree with no committed path to rewrite, and spares collaborators without the methodology the loud fault. But running the hook would become each person's choice on each machine, so a collaborator who never turned it on would run with no hook and no fault. The backbone would also write a file the person owns outside the project, and the hook would run in every session on the machine, in every project.

**Why the hook judges by both the snapshot and the checkout.**

- **The checkout alone** is the gap this record closes.
- **The snapshot alone** keeps a revoked grant in force until someone realizes. That is a boundary believed but absent (ADR-004 point 4).
- **Falling back on any difference between the two** would drop the model at each pull, sync and branch switch. A narrowing would wait for a gesture it does not need.
- **The stricter of the two verdicts** lets the checkout narrow at once and widen only through realizing.
- **A revoked grant asks.** Where the snapshot allows a call and the checkout no longer does, abstaining would hand the call to the harness's native rules, which may hold the grant as realized. Asking lets the revocation reach those rules at once, since the harness prompts on a hook's ask whatever its rules allow.
- **The snapshot alone, when the checkout's model fails.** The snapshot lies out of reach and the checkout does not, so a failure on the checkout's side may cost no more than what the checkout alone holds. Judging by the snapshot alone loses only a narrowing not yet realized, which the checkout can drop in any case, and keeps every deny and ask the snapshot holds. The order and the budget keep a stall in the checkout from costing the snapshot's judgement.

**Why the bound is found from the anchor.** Which snapshot binds must rest on nothing a sandboxed command can write. What marks a checkout's root, and the configuration that moves a working tree, lie in the checkout, so a lookup through them could be broken to reach no bound, or steered to a wider one. The harness sets the anchor and no command moves it, and the index lies out of reach, so the choice rests on neither. The identity guards a reused path: another repository cloned where a realized one stood does not inherit its bound. A bound covers whatever is anchored inside its folder because the person realized it for that folder. A worktree or a repository kept inside it is work started there, and its own model can only narrow the bound. A person who wants a folder inside it bounded otherwise realizes that folder on its own.

**Why a snapshot that cannot be used makes the hook ask.** With no snapshot, nothing was ever bounded, and giving only the hook's own verdicts keeps the session usable without flooding the person with prompts. Where a snapshot binds, the bound is what the person chose. Abstaining there would hand every call to the native rules and drop each deny and ask that only the hook holds. A state that a sandboxed command can bring about, such as a replaced folder or a realized model the core cannot judge, would then switch the bound off. Asking keeps the bound's absence loud, and refuses where nobody can answer. Realizing judges what it writes, so that a person does not put such a bound in place unawares.

**Why only one command widens, and why the interlock.** Each gesture that realized as a side effect would be one more path to widen that an agent can reach. One command, which shows each widening against what is in place, the native rules included, lets a person see what they realize, even where the model changed between their review and their realizing. Turning the hook off widens every call at once, so it takes the same interlock. The interlock costs the person a terminal for each widening, and closes the plain ways for an agent to realize unasked: the anchor in the gestures, and the ask in the hook. Each can be passed, so it is declared an interlock, as ADR-034 point 5 declares its guard.

**Why the hook's own verdicts hold in every state.** The guardrails are the catastrophic denies, and keeping the hook's half of their double lock costs nothing (ADR-002 point 3). The asks are the hook's own, and no native rule stands in for them. Kept apart, no one fault takes the others with it. With no snapshot, asking on every call would flood the person with prompts approved unread ([project-kit#2002](https://github.com/aleskalfas/project-kit/issues/2002)), and denying every call would stop the session.

**Why a clone made for a run gets only the hook's own verdicts.** Tying such a clone to the snapshot of the checkout it came from would give the clone a bound the hook would not otherwise hold. So only code out of the checkout's reach could record the tie, and only for a folder that code made. That means the backbone making such clones, which ADR-066 left to a follow-up and which would overturn part of its point 10. Such a run is held by the person's settings in any case, and a grant for one agent does not count in it yet (ADR-066 point 11), so the hook's own verdicts lose little there.

**Why a shared cache widens.** ADR-008 classed a build cache narrowing because it makes the box usable without enlarging the agent's reach. A cache whose contents the person's own runs later execute does enlarge it, since what a sandboxed command wrote there later runs unconfined. A cache for each checkout keeps the usability ADR-008 sought, at the cost of a download in each checkout's first run, and a cache shared by every project's sandboxed runs would carry one project's writes into another's. Point 5's test states the line that ADR-008's split was drawn to keep.

### Alternatives considered

- **Deny sandboxed writes to the permission files where they lie.** Rejected: each working-tree move across a change to them fails, as does sync inside the sandbox, and the file tools stay open.
- **Read the model and the code from the default branch's head.** Rejected: the git folder is open to sandboxed writes (ADR-066's Context), and a branch's own model would never apply.
- **Act on a snapshot of the model alone.** Rejected: a revoked grant stays in force until someone realizes.
- **Fall back on any difference between the snapshot and the checkout.** Rejected: every pull, sync and branch switch would drop the model.
- **Fall back whenever the checkout's model fails.** Rejected: a failure on the side a sandboxed command can write would then cost the bound kept out of its reach.
- **Let a revoked grant abstain until it is realized.** Rejected: the harness's native rules may hold the grant as realized, so the revocation would wait.
- **Find the bound through the checkout's root, as the backbone finds a project's root.** Rejected: what marks the root lies in the checkout, so a sandboxed command could break the lookup or steer it to a wider bound.
- **Let only the worktrees of a realized checkout take its bound,** tied by data out of reach. Not taken: the bound is the person's for a folder, the anchored checkout's own model narrows it, and a tie for each worktree would ask a gesture for every worktree.
- **On an identity that does not match, take the next realized folder up.** Rejected: a bound realized for another folder would stand in, wider wherever that one is wider.
- **Fall back quietly where a snapshot binds but cannot be used.** Rejected: a sandboxed command could bring that state about, and drop every deny and ask that only the hook holds.
- **Start the hook through the methodology's command on the session's path.** Rejected: the path, and the entry point's routes, may lead into code the checkout chooses, and the hook would need the methodology's runtime, which ADR-014 point 1 keeps it free of.
- **Register the hook in each checkout's local settings.** Not taken: a fresh clone or a new worktree would run with no hook and no fault, and running the hook would stop being the project's committed choice (ADR-002 point 2).
- **Register the hook in the person's own harness settings, with the project's choice kept beside the snapshots.** Not taken: running the hook would become each person's choice, a collaborator who never turned it on would run with no hook and no fault, and the hook would run in every session on the machine.
- **Tie a snapshot to its checkout by path alone.** Rejected: another repository at a reused path would inherit the bound.
- **Realize a clone made for a run from the model it was cloned at.** Rejected: it adds a realizing nobody sees, of a model read from history.
- **Tie a clone made for a run to its checkout's snapshot, recorded by the command that makes the clone.** Rejected: that command is code in the checkout, and a tie gives a folder a bound.
- **The backbone makes such clones in its state folder, and ties them itself.** Not taken here: it overturns part of ADR-066 point 10, which left it to a follow-up, and such a run's settings hold it in any case.
- **Serve every permission command from the installed release.** Not taken: a command that only writes the model writes the checkout, which a sandboxed command writes anyway, and served from another release than the pin's it could write the model in a layout the project's release does not read (ADR-039 D1).
- **Have the commands load the core from the hook's copy.** Not taken: a command's own code and an older copy's core may not fit, while the commands and the copy come from one installed release whenever the copy is current, and the overview reports when it is not.
- **Let the start hook carry the overview's reports too.** Not taken: what a start hook says reaches the agent, not the person, and the overview and the hook's own reasons carry them.
- **Let every gesture that touches the model realize it.** Rejected: each would be another path to widen that an agent can reach.
- **No interlock, or a build that waits for project-kit#3179.** Not taken: the interlock closes the plain ways for an agent to realize unasked at once, and the rest of the build need not wait.
- **Say nothing where no snapshot binds.** Rejected: whatever left the hook without a snapshot would leave the person unaware that the model is not in force.
- **Ask on every call, or deny every call, where no snapshot binds.** Rejected: prompts approved unread, or a stopped session.
- **Keep shared caches committed, and report them.** Rejected: ADR-008 point 4 never commits a widening.
- **A cache for each machine, shared by every project's sandboxed runs.** Rejected: one project's sandboxed command would write what another project's runs use.
- **Point every session's uv at a cache inside the checkout, on every platform.** Rejected: on macOS the session's uv runs outside the sandbox, and would run what that cache holds.
- **Move the active profile out of the checkout.** Not taken: the snapshot covers it, as it covers every input from which the core reads a verdict.
- **Mend every member of the class here.** Not taken: each other member needs a choice of its own, and this record's question arose in the permission layer. The adapter's other hooks take this record's mechanism unchanged, so point 2 mends them.

## Implications

**Records this record refines in place.** Each edit takes a `(refinement per ADR-095)` pointer on the point or sentence it refines, and leaves the record's decision standing.

- **ADR-002:**
  - **Its Context, on the hook file:** the hook file is realizer-owned in every mode and holds no adopter content. It reads the checkout's model at decision time, bounded by the model last realized, and what runs is a copy made from the installed release.
  - **Point 2:** the hook is the live authority that judges each call by the model last realized and by the checkout's (ADR-095 point 3). Its source is a propagated adapter file whose lifecycle sync owns, and what runs is a copy in the backbone's state folder, made from the installed release by the gesture that turns the hook on, which owns that copy's lifecycle. The registration names the copy by a location each machine resolves. The gestures that turn the hook on and off are served from the installed release, and take ADR-095 point 3's interlock.
  - **Point 3:** the hook fails open on a decision fault as point 4 defines it, each judgement apart: a judgement that faults gives no verdict, the others stand, and where none stands the call proceeds. Where the hook cannot judge a call by the snapshot of the model last realized, it asks instead (ADR-095 point 4). The double lock stands as it is.
  - **Point 4:** a decision fault is a fault in judging a call by the checkout's model or in one of the hook's own verdicts, or a payload the hook cannot read, and it fails open as point 3 says. The bound the hook judges by is apart from both fault classes. Where no snapshot of a realized model binds the session, the hook gives its own verdicts and abstains on the rest. Where one binds but the hook cannot judge a call by it, the hook asks (ADR-095 point 4). Every realizer whose hook judges by a realized model keeps these states apart from both fault classes.
- **ADR-008:**
  - **Its Decision line and point 1:** an allowance is narrowing only where nothing outside the box later runs, or reads as configuration, what a confined command writes through it, unless that code first checks it against a value no confined command can write. No allowance that reaches the backbone's state folder or the installed release is narrowing, whatever a toolkit's data classes it.
  - **Its Context and Rationale,** where they give build caches as narrowing: a cache for each checkout is narrowing, and a shared cache whose contents later runs take unchecked is widening.
  - **Its Implications on uv:** on Linux, uv runs inside the box with a cache of its own for each checkout. On macOS no allowance lets uv run there, and the exclusion stands up autonomy.
- **ADR-014:** point 1's reason for a zero-dependency hook, its Rationale's "Why the hook must be zero-dep `python3`", and its alternative of a hook started through uv give this reason: a hook started through uv would read uv's configuration from the folder it starts in, which a sandboxed command can write (ADR-095 point 1), and would need uv wherever it runs.
- **ADR-039:** its Summary, its Decision line, points 1 to 3 and D1 say that the entry point serves by route 3, whatever the checkout or its pin say, the permission commands that report a verdict or the bound, realize the permission model, or turn the permission hook on or off. For those commands D1's lock does not hold: their code is the installed release's while the content they read is the checkout's at its pin, so each reads only what its release reads whole (ADR-095 point 2). For every other command routes 1 and 2 stand, and the code they choose by data in the checkout is a gap that ADR-095 point 1 binds and leaves open.
- **ADR-060 point 8:** the hook runs no git, since git runs programs its configuration names, which a sandboxed command can write (ADR-066's Context; ADR-095 point 1), so the hook reads `.git` by hand.
- **ADR-066 point 9, on an unconfined run:** the hook's bound there is the snapshot of the nearest realized folder that holds the run's folder, which is the run's anchor, such as the person's checkout for a review. A clone a command makes for a run outside every realized folder, such as the drift command's, gets only the hook's own verdicts (ADR-095 point 3).

**A record this record overturns in part.** ADR-003 gains this first line, in the form the decisions README gives a record overturned in part:

> **Partially superseded by [ADR-095](ADR-095-hook-out-of-reach.md).** How the hook and the permission commands load the core when they run is overturned: the hook loads it from a copy made from the installed release, and each command from the release that serves it, neither from the project's tree. So the core has one source, not one place at run time, and its propagation into a project's tree serves no import, though it stands until a follow-up decides whether sync goes on carrying it. Everything else stands: the core's home in the backbone's tree, the direction of its imports, its recognizers as data and its catalog's tier.

The rest of ADR-003's body stays as it stood. ADR-095 point 2 decides what replaces the overturned part.

**Edits that change no decision.** Each leaves every choice of its record as it stood, so it takes no refinement pointer. Some correct a fact the record had wrong, others bring a sentence in line with what this record decides, and those to ADR-008 point 3, ADR-066 point 11 and ADR-073 point 10 state a gap where the record's readers will find it.

- **ADR-002's Implications,** on enabling the hook with an empty model: with an empty model, or with no snapshot, the hook gives only its own verdicts and abstains on every other call (ADR-095 point 4).
- **ADR-008 point 2:** its example of what provenance tells apart is a toolkit's entry and the same entry an operator added, with no shared build cache named.
- **ADR-008 point 3** gains a sentence: the project's chosen set, and a toolkit the project defines, are read from the checkout, which a sandboxed command can write, so their classing does not settle that an allowance is narrowing. ADR-095 point 1 binds the writer that applies them, and point 3 stands as it decides until a record applies that rule to it.
- **ADR-014:**
  - its title, point 1's title and point 1 say the hook runs under the system interpreter with no dependency, and that enforcement so keeps working on macOS, with no claim that the hook runs inside the sandbox;
  - its Rationale on supporting macOS, and its alternative of declaring macOS unsupported, drop the same claim;
  - its Context says the same-code invariant asks the hook to run the core without the methodology's runtime, with no claim that it runs in the project's tree, and names ADR-008's allowance as letting uv write a cache inside the box, without classing it narrowing;
  - its Implications on uv's cache say that on Linux uv runs confined with a cache of its own for each checkout (ADR-095 point 5).
- **ADR-025:** its Context says the hook runs outside the sandbox, from a copy of the installed release (ADR-095 point 2). Point 3, its Rationale "Why no shell parser (altitude)" and its alternative of a real shell parser drop the claim that the hook runs inside the sandbox, and keep their other reasons.
- **ADR-029's Context:** its examples of a narrowing allowance give a cache for each checkout, with no build cache shared between runs.
- **ADR-060 point 8:** the removal command takes its tests from the running backbone's own code, as the permission commands take the core from the release that serves them (ADR-095 point 2). Point 8's reason, that a branch or another checkout may hold that file changed, stays.
- **ADR-066 point 11** gains an item: a clone a command makes for an agent's unconfined run, such as the drift command's, lies outside every realized folder, so its hook gives only its own verdicts there (ADR-095 point 3). Nothing keeps such a clone out of the folders sandboxed commands write, so a run may load what they wrote there, which ADR-095 point 1 binds and leaves open.
- **ADR-073 point 10** gains an item: a working run's hook and model are read from the repository's history, which sandboxed commands in the caller's sessions can write, and are bounded by no model a person realized. ADR-095 point 1 binds this, and point 2 stands as it decides until a record applies that rule to it.

**Records whose decisions hold.**

- **ADR-029** routes allowances by class, and only its Context's examples change (above). Setup's cache for each checkout is a setting for one machine, which ADR-032's Rule A routes as such.
- **ADR-032** holds: the registration stays committed, and setup's cache for each checkout is per machine by its Rule A.
- **ADR-073 point 2** stands as it decides, and its point 10 states the gap (above).
- **ADR-004, ADR-021 and ADR-034** hold as they stand.

**The build:**

- **The backbone:** the permission commands served from the installed release, and every permission command's core from the release that serves it; the core's choice of a snapshot through the index, its judgement by two models, and its ask on a revoked grant; realizing with its snapshots, the index, the folder's identity, its display of the native rules, its judgement of what it writes, its remaking of the copy and the interlock; the interlock on turning the hook off; the overview's reports; toolkits with no shared cache, no allowance over the state folder or the installed release, and setup's cache for each checkout.
- **The Claude Code adapter:** the copy of its hooks and their registration, the hook's judgement through the core in its order and budget, its own verdicts, what it does where no snapshot binds and its asks where one cannot be used, its ask before the interlocked gestures, its guard on itself, and its enforcement declaration.
- **The documents:** the adapter's README on where the hooks run, what the hook does with no snapshot or one it cannot use, and turning it on. The permissions README and the CLI reference follow.
- **A migration** ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)) rewrites, where the permission hook is on, the committed registration of each hook the adapter registers, and makes the copy on a machine where it runs outside the sandbox. It realizes nothing. It removes from the committed sandbox settings each shared-cache allowance the backbone wrote, by its provenance (ADR-008 point 2), never one a person added.
- **The release's notes** say:
  - that other machines meet the loud fault until their person makes the copy, and that each checkout gets only the hook's own verdicts until its person realizes it;
  - that a checkout at an older commit registers the hooks as it did then, and that until setup runs again a tool inside the sandbox has no cache it can write;
  - that a branch switch, pull or rebase run inside the sandbox across the change to the committed registration may stop partway, since the harness keeps its settings files from sandboxed writes, so to run it outside;
  - that a person whose sandbox could write a shared build cache reinstalls the methodology from an emptied cache before making the copy.
- **Changesets** declare each component's surface change ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)).

**Open work:** the follow-up issues linked from project-kit#3178 (point 7). project-kit#3179 builds on this record.

**What this record stands on:** COR-010, COR-028, PRJ-002, and ADR-002, ADR-003, ADR-004, ADR-008, ADR-014, ADR-021, ADR-025, ADR-029, ADR-032, ADR-033, ADR-034, ADR-039, ADR-060, ADR-066 and ADR-073, all accepted.
