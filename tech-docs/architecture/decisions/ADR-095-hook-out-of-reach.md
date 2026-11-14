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

- **The rule:** code that runs outside the sandbox without a person choosing it, such as a hook, never comes from a place a sandboxed command can write. Nothing such code reads from such a place widens what it allows.
- **The code:** the hook and its decision core run from a copy of the installed release, in a folder of the person's that no sandboxed command writes. The project's committed settings register that copy.
- **The policy:** the model stays in the checkout, where people edit it. *Realizing* the model, the step that turns it into what the harness enforces, also keeps a snapshot of it out of reach. The hook allows no more than that snapshot. A change in the checkout that narrows the model takes effect at once, and one that widens it waits until it is realized.
- **With no snapshot,** the hook allows nothing by the model, yet it denies the guardrails and puts its own asks.
- **Shared build caches** leave the committed sandbox, uv's among them, since the person's later runs execute what lands in them.

**How far it holds.** The bound holds against what a sandboxed command does alone, but for the members of the rule's class that this record leaves open (point 7). On Linux the methodology's own commands run inside the sandbox, so an agent's call of one of them reaches no further. Where they run outside it, as on macOS, the bound does not hold against a sandboxed command followed by such a call. The permission overview reports each gap.

**What it rests on.** The harness keeps its own settings files out of a sandboxed command's reach. A probe confirms this, with the other facts point 6 names, and the record is superseded whole if it does not hold.

## Context

**What prompted it.** [project-kit#3178](https://github.com/aleskalfas/project-kit/issues/3178) found that no part of the permission layer lies out of a sandboxed command's reach. The parts are:

- the hook, which the harness runs before each tool call;
- the decision core, which the hook and the permission commands share ([ADR-003](ADR-003-permission-core-code-home.md));
- the model ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) point 1), and every other input from which the core reads a verdict.

All of them sit in the checkout, and a sandboxed command writes its working folder. The hook runs outside the sandbox, as the harness runs hooks, file tools and connected servers outside it. Both facts come from the harness's documentation, as [ADR-066](ADR-066-unattended-agent-runner.md)'s Context records it.

**Why it matters.** A boundary is only as strong as what enforces it. Whatever changes the hook, the core or the model changes what every later call is judged by. The intent axis would then rest on a boundary the confinement axis lets the agent move: the boundary believed but absent that [ADR-004](ADR-004-autonomy-intent-confinement.md) point 4 forbids.

**What it builds on.**

- **The guardrails** all come from the backbone's catalog, since a capability may not define one ([ADR-021](ADR-021-capability-contributed-privilege-definitions.md) point 3). So a release's catalog holds every guardrail that release ships.
- **The backbone keeps per-person state** in a folder of its own that only the person's account writes, outside every checkout (ADR-066 point 7).
- **The entry point** picks which release serves a command, by the checkout it runs in and by the project's pin ([ADR-039](ADR-039-pkit-entry-point-router.md)).

**uv's cache.** The uv toolkit's write allowance to uv's shared cache is classed narrowing. So setup applies it unasked ([ADR-008](ADR-008-confinement-allowances.md) point 3), and it lands in the committed settings ([ADR-029](ADR-029-move-mutable-sandbox-state-out-of-tracked-settings.md) point 1). Yet the person's later uv runs, outside any sandbox, execute what lands there (ADR-066's Rationale, "Why a command that starts `uv` fails on Linux"). On macOS, uv cannot run inside the sandbox at all ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) point 2), so the allowance serves no sandboxed uv there.

## Decision

**Nothing a sandboxed command can write becomes code that runs outside the sandbox unchosen, or widens what such code allows. So the permission hook runs from a copy of the installed release, out of reach, and allows no more than the model a person last realized.**

- **What this record mends:** the permission hook, its core and its model (points 2 to 4), and the write allowances the backbone ships (point 5). The rest of point 1's class stays open (point 7).
- **Its precondition.** The harness keeps its own settings files out of a sandboxed command's reach. They register the hook and hold the native denies that ADR-002 point 3 relies on. No accepted record establishes this, so the record states it as a precondition, which the probe confirms (point 6). A probe that disproves it supersedes this record whole.

### 1. What a sandboxed command can write is never trusted outside the sandbox

- **The rule.** Code that runs outside the sandbox without a person choosing to run it never comes from a place a sandboxed command can write. Policy or configuration that such code reads from such a place may narrow what it allows, and never widen it. Nor can a sandboxed command choose or redirect where such code writes.
- **Chosen and unchosen code.** A person chooses code when they run the agent's work in the checkout as that work, its tests or its build for instance. They do not choose the code a tool loads on its own, such as a hook, a tool's own configuration or a build it takes from a shared cache. Nor do they choose the code that a command the sandbox exempts runs on an agent's call.
- **A write allowance,** an allowance that opens a place to sandboxed writes, widens the boundary where it opens a place this rule keeps out of reach, however it was classed.

### 2. The hook and the decision core run from a copy of the installed release

- **The copy.** The harness runs the hook from a copy in the *backbone's state folder*, the folder of the person's where the backbone keeps its own state, which only the person's account writes (ADR-066 point 7). It lies outside every checkout and outside the folders a sandboxed command writes by itself (ADR-066's Context), and no allowance the backbone ships opens it.
- **What the copy holds:** the hook, the decision core, the release's catalog, and what the hook needs to start. It names an interpreter outside every checkout, and starts it so that it loads no code from the session's environment or working folder.
- **Who makes it.** The gesture that turns the hook on makes the copy from the release installed on the machine, and makes it anew each time it runs. It runs no code from the checkout. It makes the copy only outside the sandbox, and inside it makes nothing and says so. The entry point serves this gesture itself, never through a route that data in the checkout chooses (ADR-039 points 1 and 2).
- **The source stays where it is.** The core keeps the home ADR-003 gives it, and the hook its home in the adapter. The release bundles both from there ([ADR-033](ADR-033-official-install-bundles-content.md) point 1), and the copy is made from what the release bundles.
- **The registration.** The project's committed settings register the hook, since running it is the project's choice ([ADR-002](ADR-002-permission-realizer-ownership.md) point 2). They name the copy by a location each machine resolves for its own person, never by a path in the checkout.
- **A machine with no copy.** There the hook cannot start, which is the loud fault of ADR-002 point 4. The permission overview's self-check reports it (ADR-002's Implications), and names the gesture that makes the copy. The overview also reports a copy older than the installed release.
- **The permission commands** load the core from their own release, as the workspace removal command takes its code from the running backbone ([ADR-060](ADR-060-path-scoped-workspace-allow.md) point 8).
- **One verdict.** The core takes the two models of point 3 and gives the stricter verdict, and with no snapshot to trust it gives the guardrail deny alone. So every command that reports a verdict reports the one the hook acts on, which is why ADR-003 keeps the decision in the core. What turns on the harness stays in the adapter: how an ask meets the session's mode ([ADR-025](ADR-025-segment-conservative-bash-allow.md) point 7), the asks of point 4 that the adapter makes of its own, and its guard on itself.
- **Two copies of one source.** The hook's copy and the commands' release are each made from a release of the one core, and the shared conformance tests hold every caller to one verdict. Where the two releases differ, the overview says so.
- **What the hook reads, and from where.** Its code, the release's catalog and the snapshots of point 3 come from its copy's folder. The checkout is the one the session anchor lies in ([ADR-034](ADR-034-foreign-repo-mutation-guard.md) point 1), found as the backbone finds a project's root. With no anchor the hook has no checkout, and gives only point 4's verdicts.
- **What the hook writes,** it writes only into its copy's folder.
- **Its runtime** stays a zero-dependency script (ADR-014 point 1).

### 3. The hook allows no more than a person last realized

- **The model stays in the checkout.** It is the source of truth that people edit, review and commit (COR-028 point 1).
- **Realizing keeps a snapshot.** Realizing turns the model into what the harness enforces (COR-028 point 2), through an operation the methodology's commands provide (COR-028's Implications). It also keeps a *snapshot* of the checkout's model in the backbone's state folder. The snapshot holds, as the checkout held it, every input from which the core reads a verdict, wherever the core reads it, the subject a call is judged for among them. It also records the version of its own layout.
- **Its tie to the checkout.** A snapshot is tied to its checkout by the checkout's root as the realizing command finds it, never by a variable a command line can set (ADR-060 point 10). The tie also records an identity of that root folder that no command inside the checkout can change. A snapshot whose recorded identity does not match its folder is never read.
- **A checkout with no snapshot of its own** takes the snapshot of the nearest realized checkout whose folder holds it, such as a worktree made inside a realized checkout. A clone made for an agent's run, outside every checkout, takes the snapshot of the checkout it was made from, where the command that makes the clone records that tie through the backbone (ADR-066 point 10). Any other checkout gets only point 4's verdicts.
- **Which checkout judges.** The hook judges each call by the checkout the session anchor lies in, whatever folder the call works in. Where a subagent works in a worktree under an anchor in its parent's checkout, the parent's snapshot and model judge its calls, and a narrowing that only the worktree holds does not reach them.
- **The verdict.** The core judges each call twice, by the snapshot and by the checkout's model, and the hook acts on the stricter verdict. Deny is the strictest, then ask, then abstain, then allow.
  - **A change in the checkout that narrows the model,** such as a revoked grant, takes effect at once.
  - **A change that widens it,** such as a new grant or a more permissive active profile, takes effect only once realized.
  - **A sandboxed command** can thus make the hook stricter, and never more permissive than the snapshot.
- **When the checkout's model fails.** Where it will not load, faults in the core, or overruns the hook's time budget, the hook judges by the snapshot alone. The budget is a share of the harness's limit for a hook, and the snapshot's judgement uses it first. Judging by the snapshot alone drops only a narrowing not yet realized, which holds only while the checkout holds it in any case.
- **The reason names realizing.** Whenever the snapshot refuses what the checkout's model would allow, the hook's reason says so, and names the realizing command.
- **Only realizing widens.** Only the realizing command writes a snapshot, and the gesture that turns the hook on where no snapshot exists yet. A command that writes the model realizes nothing, and says what it left unrealized. The realizing command:
  - shows each place where the checkout's model allows more than the snapshot, and counts as a widening any place it cannot compare;
  - runs no code from the checkout, and is served by the entry point itself, never through a route that data in the checkout chooses (ADR-039 points 1 and 2);
  - realizes only outside the sandbox, and inside it realizes nothing and says so.
- **An interlock on widening.** Where a session anchor is set, neither of the two writes a snapshot that allows more than the one in place, or than none. Each refuses that part and names the person's own terminal, and a realizing that only narrows goes ahead. This is an interlock against an agent realizing unasked, not a boundary, as ADR-034 point 5 declares its guard: a command line can clear the anchor. Whether realizing a wider model takes a person's gesture, as a boundary, is decided with [project-kit#3179](https://github.com/aleskalfas/project-kit/issues/3179).
- **A narrowing not yet realized** holds only while the checkout holds it. The overview reads the snapshot back (COR-028 point 2), and names each place where it allows more than the checkout's model.
- **Across releases.** A snapshot the copy's core cannot read counts as none, so its checkout gets only point 4's verdicts until it is realized again, and the hook and the overview say so. When the gesture that turns the hook on makes the copy anew, it names each snapshot on the machine that the new release cannot read.

### 4. The hook's own verdicts hold in every state

- **What they are:** the verdicts the hook gives without a model.
  - **The guardrail deny,** the hook's half of the double lock (ADR-002 point 3), for every guardrail of the copy's catalog, and of the checkout's where it loads.
  - **Each ask the adapter makes of its own,** as the record that decides it says. Such are the ask where a shell call may hide a guardrail (ADR-025 point 7), sought among the same guardrails, and the ask before a file tool writes outside the session's repository, the adapter's realization of ADR-034 point 2, which holds in every mode ([project-kit#2004](https://github.com/aleskalfas/project-kit/issues/2004)).
  - **Its guard on itself.** The file tools run outside the sandbox. So the hook denies a file tool's write into its copy's folder, the snapshots included, and asks before a file tool writes a settings file that registers it. Both hold in every mode, whatever the model allows.
- **Apart from one another.** Each of these runs on its own, so a fault in one drops neither the others nor the model's verdict.
- **The fallback.** Where no snapshot can be trusted, the hook allows nothing by the model, gives its own verdicts, and abstains on every other call, so the harness's native rules decide it. No snapshot can be trusted where:
  - there is no anchor, or no snapshot for the checkout or for one it takes its snapshot from (point 3);
  - the snapshot will not load, or its judgement faults or overruns the hook's time budget.
- **What the fallback says.** Each ask and deny it gives says that the model is not in force, and names the realizing command.
- **Faults.** Where the model's judgement and every one of the hook's own verdicts fault, the hook abstains, as on a decision fault (ADR-002 point 3). A hook that cannot start stays the loud fault of ADR-002 point 4.

### 5. A write allowance is narrowing only where nothing outside the sandbox runs what it lets in

- **The test.** A write allowance is narrowing only where no code outside the sandbox later runs, or reads as configuration, what a sandboxed command writes through it, unless that code first checks it against a value no sandboxed command can write. Every other write allowance is widening, and ADR-008 point 4 governs it: never committed, never applied unasked, always reported.
- **A shared build cache fails it.** A tool builds and installs from its shared cache what the person's later runs execute, outside any sandbox, without such a check. On macOS the session's own uv runs outside the sandbox too. So no toolkit the backbone ships carries an allowance for a shared cache, uv's among them, and no gesture of the backbone applies one. The overview names such an allowance as a widening wherever it finds one.
- **A cache for each checkout passes it.** Where a tool runs inside the sandbox, setup gives each checkout's sandboxed runs of it a cache of their own, which nothing outside the sandbox runs from. It does so only where no command that starts that tool runs outside the sandbox. The setting is per machine ([ADR-032](ADR-032-per-machine-activation-routing-axis.md) Rule A).
- **On macOS** uv cannot run inside the sandbox, so losing its shared cache costs nothing there.

### 6. The tests, and the probe

- **Tests hold that a sandboxed command or a file tool, alone:**
  - cannot write the hook's copy, the core it runs or a snapshot;
  - can change or break any input of the checkout's model, and never make the hook allow more than the snapshot does;
  - meets, where no snapshot is trusted, the guardrail deny and the hook's own asks.
- **Tests also hold:**
  - every command that reports a verdict reports the one the hook acts on;
  - the realizing command and the gesture that makes the copy run no code from the checkout, and take no route that data in the checkout chooses;
  - no write allowance the backbone commits fails point 5's test.
- **The probe.** A probe confirms the facts below on each harness release and platform before the hook relies on them, as ADR-066 point 12 does for an agent's run. A fact no probe has confirmed rests on the harness's documentation.
  - the precondition: the harness keeps its settings files out of a sandboxed command's reach;
  - hooks run outside the sandbox;
  - the committed registration finds the person's copy at the checkout's root, in a subagent working in a worktree, and in a session started in a worktree;
  - which checkout the session anchor names in each of those three;
  - no folder a sandboxed command writes by itself, and no allowance the backbone ships, reaches the backbone's state folder or the installed release;
  - a tool that runs inside the sandbox works with a cache of its own for the checkout;
  - the two judgements of point 3 stay within the hook's time budget on the project's own model.
- **A fact the probe disproves** refines or supersedes this record, as the change to the decision requires. A disproved precondition supersedes it whole.

### 7. What stays open

Each gap below is reported rather than hidden, as COR-028 point 3 asks. The permission overview and the adapter's enforcement declaration state each one that bears on the bound, for each platform.

- **A sandboxed command followed by a call.** Where the methodology's own commands run outside the sandbox, as on macOS, the bound holds against a sandboxed command alone, and not against one followed by an agent's call of such a command.
- **Who realizes.** Until project-kit#3179 is decided and built, only point 3's interlock keeps an agent's call outside the sandbox from realizing a model that a sandboxed command widened.
- **Other code and configuration.** Point 1 binds the other code that the harness or the methodology's commands run outside the sandbox, and the configuration that the harness and other tools load on their own. This record mends none of it.
- **A runner's reads from the repository's history** ([ADR-073](ADR-073-builder-runs.md) point 2). Point 1 binds them, and this record leaves them as they stand.
- **A checkout at an older commit,** from before this record's build, registers the hook as it did then. The overview reports such a registration.
- **An install from source.** Where the methodology runs from a source checkout (ADR-033 point 2), the release the copy is made from is that checkout. There the bound holds only between the gestures that make the copy, and the checkout bears the loud faults and the realizing steps all the same. project-kit's own repository runs so.
- **What runs outside every sandbox,** such as the person's own terminal, can write the backbone's state folder. The sandbox bounds only what it confines.
- **A working folder or a write allowance over the backbone's state folder** opens it to sandboxed commands. The overview says so where it finds one.
- **The copies sync carries.** The hook and the core propagate into a project's tree with the trees they live in, and run nowhere there.
- **A narrowing that blocks.** A sandboxed command can narrow the checkout's model until the hook refuses every call, the calls that would repair it among them. Only the person's own terminal then recovers the session. It widens nothing.

Follow-up issues linked from project-kit#3178 hold the other code and configuration, the runner's reads, and whether sync goes on carrying the copies that run nowhere.

## Rationale

**Why the rule turns on who chose the code.** A person who runs the checkout's tests from their terminal runs what a sandboxed command may have written, and knows it: the checkout is the agent's work, which they review and run as such. A rule against all of that would bind no project. What the sandbox's bound needs is narrower: no code a person did not choose, such as the hook judging the agent, a tool's own configuration or a build from a shared cache, comes from where the agent can write. So point 1 draws its line there, and covers where such code writes as well as what it runs, since a write a sandboxed command can redirect changes a file it could not write itself.

**Why policy as well as code.** The model decides what the hook allows. A sandboxed command that could widen the model would gain what changing the code gains, without touching the code. So the rule covers both, and lets the checkout only narrow.

**Why the code runs from a copy of the release.** Three ways keep the code out of reach: deny writes to its files where they lie, read it from history, or run it from elsewhere.

- **Denying sandboxed writes where the files lie** fails each command that moves a working tree across a change to them, such as a branch switch, a pull or a rebase, and sync where sync runs inside the sandbox. Such a command may stop partway. The harness's own settings files bear the same cost, but they seldom differ between branches, while the permission layer's change with each upgrade and each new grant. The file tools, which run outside the sandbox, would still need a guard of the hook's own.
- **Reading from the default branch** reads a git folder that sandboxed commands can write (ADR-066's Context).
- **The release** is installed outside every checkout, by a person. The installed release itself serves the gestures that copy it and that realize the model, so data in the checkout cannot choose which release that is.
- **The cost:** a change to the hook or the core reaches a session only once it is released, installed and copied. Tests and CI still run the checkout's code, and in an install from source the release is the checkout.

**Why the entry point serves these gestures itself.** It picks a release by data in the checkout: a source checkout's own code, or the project's pin (ADR-039 points 1 and 2). For the gestures that make the copy and realize the model, that data would choose the code a person trusts to widen what the hook allows. Served by the installed release, the choice stays with the person who installed it.

**Why the core gives the hook's verdict.** ADR-003 keeps the decision in the core so that its callers never diverge. Judging by two models and taking the stricter is decision, so it lives there too, and the commands that report a verdict report the hook's. The hook's copy and the commands' release can be two releases, so the overview reports when they differ.

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
- **The snapshot alone, when the checkout's model fails.** The snapshot lies out of reach and the checkout does not, so a failure on the checkout's side may cost no more than what the checkout alone holds. Judging by the snapshot alone loses only a narrowing not yet realized, which the checkout can drop in any case, and keeps every deny and ask the snapshot holds.

**Why a snapshot's tie carries an identity, and why a checkout takes another's snapshot.** Tied by path alone, a snapshot would bound whatever later lies at that path, such as another repository cloned there. A worktree inside a realized checkout, or a clone made from it for a run, is that project's work, so the bound its person realized fits it. Any other checkout gets only the hook's own verdicts until it is realized.

**Why only one command widens, and why the interlock.** Each gesture that realized as a side effect would be one more path to widen that an agent can reach. One command, which shows each widening against the snapshot, lets a person see what they realize, even where the model changed between their review and their realizing. The interlock costs the person a terminal for each widening, and closes the plain way for an agent to realize unasked. A command line that clears the anchor passes it, so it is declared an interlock, as ADR-034 point 5 declares its guard.

**Why the hook's own verdicts hold in every state.** The guardrails are the catastrophic denies, and keeping the hook's half of their double lock costs nothing (ADR-002 point 3). The asks are the hook's own, and no native rule stands in for them. Kept apart, no one fault takes the others with it. Without a snapshot, asking on every call would flood the person with prompts approved unread ([project-kit#2002](https://github.com/aleskalfas/project-kit/issues/2002)), and denying every call would stop the session.

**Why a shared cache widens.** ADR-008 classed a build cache narrowing because it makes the box usable without enlarging the agent's reach. A cache whose contents the person's own runs later execute does enlarge it, since what a sandboxed command wrote there later runs unconfined. A cache for each checkout keeps the usability ADR-008 sought, at the cost of a download in each checkout's first run, and a cache shared by every project's sandboxed runs would carry one project's writes into another's. Point 5's test states the line that ADR-008's split was drawn to keep.

### Alternatives considered

- **Deny sandboxed writes to the permission files where they lie.** Rejected: each working-tree move across a change to them fails, as does sync inside the sandbox, and the file tools stay open.
- **Read the model and the code from the default branch's head.** Rejected: the git folder is open to sandboxed writes (ADR-066's Context), and a branch's own model would never apply.
- **Act on a snapshot of the model alone.** Rejected: a revoked grant stays in force until someone realizes.
- **Fall back on any difference between the snapshot and the checkout.** Rejected: every pull, sync and branch switch would drop the model.
- **Fall back whenever the checkout's model fails.** Rejected: a failure on the side a sandboxed command can write would then cost the bound kept out of its reach.
- **Start the hook through the methodology's command on the session's path.** Rejected: the path, and the entry point's routes, may lead into code the checkout chooses, and the hook would need the methodology's runtime, which ADR-014 point 1 keeps it free of.
- **Register the hook in each checkout's local settings.** Not taken: a fresh clone or a new worktree would run with no hook and no fault, and running the hook would stop being the project's committed choice (ADR-002 point 2).
- **Register the hook in the person's own harness settings, with the project's choice kept beside the snapshots.** Not taken: running the hook would become each person's choice, a collaborator who never turned it on would run with no hook and no fault, and the hook would run in every session on the machine.
- **Tie a snapshot to its checkout by path alone.** Rejected: another repository at a reused path would inherit the bound.
- **Realize a clone made for a run from the model it was cloned at.** Rejected: it adds a realizing nobody sees, of a model read from history.
- **Let every gesture that touches the model realize it.** Rejected: each would be another path to widen that an agent can reach.
- **No interlock, or a build that waits for project-kit#3179.** Not taken: the interlock closes the plain way for an agent to realize unasked at once, and the rest of the build need not wait.
- **Keep the fallback silent.** Rejected: whatever left the hook without a snapshot would silence its own asks.
- **Ask on every call, or deny every call, in the fallback.** Rejected: prompts approved unread, or a stopped session.
- **Keep shared caches committed, and report them.** Rejected: ADR-008 point 4 never commits a widening.
- **A cache for each machine, shared by every project's sandboxed runs.** Rejected: one project's sandboxed command would write what another project's runs use.
- **Point every session's uv at a cache inside the checkout, on every platform.** Rejected: on macOS the session's uv runs outside the sandbox, and would run what that cache holds.
- **Move the active profile out of the checkout.** Not taken: the snapshot covers it, as it covers every input from which the core reads a verdict.
- **Mend every member of the class here.** Not taken: each needs a choice of its own, and this record's question arose in the permission layer.
- **Land the record together with its build, rather than ahead of it.** Left to the person who accepts the record (Implications).

## Implications

**Records this record refines in place.** Each edit takes a `(refinement per ADR-095)` pointer on the point or sentence it refines, and leaves the record's decision standing.

- **ADR-002:**
  - **Its Context, on the hook file:** the hook file is realizer-owned in every mode and holds no adopter content. It reads the checkout's model at decision time, bounded by the model last realized, and what runs is a copy made from the installed release.
  - **Point 2:** the hook is the live authority that judges each call by the model last realized and by the checkout's, and acts on the stricter verdict. The registration names a copy of the hook in the backbone's state folder, made from the installed release, by a location each machine resolves.
  - **Point 3:** fail-open covers a fault in a model's judgement. The hook's own verdicts, which need no model, stand through such a fault, and a fault in one of them drops none of the rest.
  - **Point 4:** a third state, no snapshot the hook can trust, is neither fault class. There the hook gives its own verdicts and says so (ADR-095 point 4). Every realizer whose hook judges by a realized model keeps this state apart from both fault classes.
- **ADR-008:**
  - **Its Decision line and point 1:** an allowance is narrowing only where nothing outside the box later runs, or reads as configuration, what a confined command writes through it, unless it first checks it against a value no confined command can write.
  - **Its Context and Rationale,** where they give build caches as narrowing: a cache for each checkout is narrowing, and a shared cache whose contents later runs take unchecked is widening.
  - **Its Implications on uv:** on Linux, uv runs inside the box with a cache of its own for each checkout. On macOS no allowance lets uv run there, and the exclusion stands up autonomy.
- **ADR-014:** point 1's reason for a zero-dependency hook, its Rationale's "Why the hook must be zero-dep `python3`", and its alternative of a hook started through uv give this reason: a hook started through uv would read uv's configuration from the folder it starts in, which a sandboxed command can write (ADR-095 point 1), and would need uv wherever it runs.
- **ADR-039:** its Decision line and points 1 to 3 say that the entry point serves the gestures that make the permission hook's copy or realize the permission model by route 3, whatever the checkout or its pin say.
- **ADR-060 point 8:** the hook runs no git, since git would read configuration a sandboxed command can write (ADR-095 point 1), so it reads `.git` by hand.
- **ADR-066:**
  - **Point 9, on an unconfined run:** the hook's bound there is the snapshot of the checkout the run's folder lies in, or, for a clone the drift command makes, the snapshot of the checkout it was made from (ADR-095 point 3).
  - **Point 10, on the drift command's clone for an unconfined run:** the drift command records through the backbone that its clone takes the snapshot of the checkout it runs in. Where it cannot, as inside the sandbox, the run's hook gives only its own verdicts, and the run's result says so.

**A record this record overturns in part.** ADR-003 gains a first line: *Partially superseded by ADR-095*, for how the hook and the permission commands load the core when they run. Each loads it from a copy made from a release, and neither from the project's tree. So the core has one source rather than one place at run time, and its propagation into a project's tree serves no import. Its home in the backbone's tree, the direction of its imports, its recognizers as data and its catalog's tier stand. The rest of ADR-003 stays as it stood. Point 2 decides what replaces the overturned part: one source, each run-time copy made from a release of it, the conformance tests holding every caller to one verdict, and the overview reporting when the hook's release and the commands' differ.

**Edits that change no decision.** Each leaves every choice of its record as it stood, so it takes no refinement pointer. Some correct a fact the record had wrong, and others bring a sentence in line with what this record decides.

- **ADR-014:**
  - its title, point 1's title and point 1 say the hook runs under the system interpreter with no dependency, and that enforcement so keeps working on macOS, with no claim that the hook runs inside the sandbox;
  - its Rationale on supporting macOS, and its alternative of declaring macOS unsupported, drop the same claim;
  - its Context says the same-code invariant asks the hook to run the core without the methodology's runtime, with no claim that it runs in the project's tree;
  - its Implications on uv's cache say that on Linux uv runs confined with a cache of its own for each checkout (ADR-095 point 5).
- **ADR-025:** its Context says the hook runs outside the sandbox, from a copy of the installed release (ADR-095 point 2). Point 3, its Rationale "Why no shell parser (altitude)" and its alternative of a real shell parser drop the claim that the hook runs inside the sandbox, and keep their other reasons.
- **ADR-060 point 8:** the removal command takes its tests from the running backbone's own code, as the permission commands take the core from their own release (ADR-095 point 2).

**Records that hold with no edit.**

- **ADR-073 point 2** keeps a working run's hook and model as it decides.
- **ADR-029** routes allowances by class, and this record removes entries rather than adding one.
- **ADR-032** holds: the registration stays committed, and setup's cache for each checkout is per machine by its Rule A.
- **ADR-002's Implications** on enabling the hook with an empty model hold: an empty snapshot, or none, leaves the hook abstaining but for the guardrails and its own asks, as an empty model did.
- **ADR-004, ADR-021 and ADR-034** hold as they stand.

**The build:**

- **The backbone:** the permission commands' core from their release, and the core's judgement by two models; realizing with its snapshots, their ties and the interlock; the overview's reports; the entry point's service of the two gestures; toolkits with no shared cache, and setup's cache for each checkout.
- **The Claude Code adapter:** the copy and its registration, the hook's judgement through the core, its own verdicts and the fallback, its guard on itself, and its enforcement declaration.
- **project-management:** the drift command records its clone's tie to the snapshot of the checkout it runs in (ADR-066 point 10).
- **The documents:** the adapter's README on where the hook runs, what it does with no snapshot, and turning it on. The permissions README and the CLI reference follow.
- **A migration** ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)) rewrites the committed registration the backbone wrote, and makes the copy on a machine where it runs outside the sandbox. It realizes nothing. It removes from the committed sandbox each shared-cache allowance the backbone wrote, by its provenance (ADR-008 point 2), never one a person added.
- **The release's notes** say that other machines meet the loud fault until their person makes the copy, and that each checkout gets only the hook's own verdicts until its person realizes it. They also say that a checkout at an older commit registers the hook as it did then, and that until setup runs again a tool inside the sandbox has no cache it can write.
- **Changesets** declare each component's surface change ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)).

**When it lands.** Whether this record lands together with its build, or ahead of it, is the choice of the person who accepts it. Landing ahead puts on the default branch, before the build, both the gaps this record leaves open and those its build closes.

**Open work:** the follow-up issues linked from project-kit#3178 (point 7). project-kit#3179 builds on this record.

**What this record stands on:** COR-010, COR-028, PRJ-002, and ADR-002, ADR-003, ADR-004, ADR-008, ADR-014, ADR-021, ADR-025, ADR-029, ADR-032, ADR-033, ADR-034, ADR-039, ADR-060, ADR-066 and ADR-073, all accepted.
