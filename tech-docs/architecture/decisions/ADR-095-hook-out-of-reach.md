---
id: ADR-095
title: A sandboxed command cannot change the permission hook or widen what it allows
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the permission hook decides, before each tool call, whether an agent may make it. The hook, the code it decides with and the permission model it reads all sit in the project's checkout. A command the sandbox confines may write the checkout, while the hook runs outside the sandbox. So a confined command could change the code and the policy that judge the calls after it. Claude Code keeps its own settings and hooks out of a sandboxed command's reach for this reason.

This record brings the permission layer under the same rule, with one rule and three parts:

- **The rule:** what a sandboxed command can write is never run outside the sandbox, and never widens what is allowed there.
- **The code:** the hook and its decision core run from the installed release, from a copy in a folder of the user's that no sandboxed command writes. The project's settings register the hook by that folder, never by a path in the checkout.
- **The policy:** the model stays in the checkout, where people edit it. The hook allows no more than the model a person last *realized*, kept as a snapshot out of reach. A change in the checkout that narrows the model takes effect at once. A change that widens it waits until it is realized.
- **The fallback:** where the hook has no model it can trust, it still denies the guardrails and still puts the asks it owns, the ask before a file tool writes outside the repository among them. It allows nothing by the model.

The rule also decides uv's shared cache. The committed sandbox lets every sandboxed command write it, and the person's later uv runs execute what lands there. So that grant widens the boundary, and it leaves the committed sandbox.

The rule reaches further than this record mends. Other code that runs outside the sandbox from the checkout, and configuration the harness loads from it, stay open work (point 7). Whether an agent may realize a wider model is decided with [project-kit#3179](https://github.com/aleskalfas/project-kit/issues/3179). Several facts this record rests on need a probe on a live harness before the build (point 6).

## Context

**What prompted it.** [project-kit#3178](https://github.com/aleskalfas/project-kit/issues/3178) found that no part of the permission layer lies out of a sandboxed command's reach. The parts are:

- the hook, which the harness runs before each tool call;
- the decision core, which the hook and the permission commands share ([ADR-003](ADR-003-permission-core-code-home.md));
- the model the core reads: the catalog, the grants, the profiles, the configuration and the active profile ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) point 1).

All of them sit in the checkout. The sandbox lets a command write its working folder ([ADR-004](ADR-004-autonomy-intent-confinement.md)).

**Where each part runs.**

- **The hook** runs outside the sandbox. The harness runs hooks, file tools and connected servers outside it, as its documentation states and [ADR-066](ADR-066-unattended-agent-runner.md)'s Context relies on. Some records say the hook runs inside the sandbox, after the macOS investigation that made it a zero-dependency script ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) point 1). That investigation showed what the hook needs to start, not where it runs. Point 6's probe settles it on each platform, and this record holds either way.
- **The permission commands** run outside the sandbox on macOS, where the commands that start uv are excluded from it (ADR-014 point 2). They load the core from the project's checkout, unlike the workspace removal command ([ADR-060](ADR-060-path-scoped-workspace-allow.md) point 8).
- **The model** is read from the checkout at every call.

**Why it matters.** A boundary is only as strong as what enforces it. A sandboxed command that changes the hook, the core or the model changes what every later call is judged by. The intent axis would then rest on a boundary that the confinement axis lets the agent move. ADR-004 forbids a boundary that is believed but absent.

**What already holds.**

- **An agent run's hook** runs out of reach. The runner registers it from outside the run's clone, with its code and its model read from the default branch ([ADR-073](ADR-073-builder-runs.md) point 2).
- **The harness's settings files** are out of a sandboxed command's reach, so the native rules and the guardrail denies they hold stand ([ADR-002](ADR-002-permission-realizer-ownership.md) point 3).
- **The guardrails** all come from the backbone's catalog, since a capability may not define one ([ADR-021](ADR-021-capability-contributed-privilege-definitions.md) point 3).

**What the hook does when its model will not load.** It abstains, as on a decision fault (ADR-002 points 3 and 4). It then puts neither of the asks it owns:

- the ask where a shell call may hide a guardrail ([ADR-025](ADR-025-segment-conservative-bash-allow.md) point 7);
- the ask before a file tool writes outside the session's repository ([ADR-034](ADR-034-foreign-repo-mutation-guard.md) point 2), which holds in every mode ([project-kit#2004](https://github.com/aleskalfas/project-kit/issues/2004)).

So a model that a sandboxed command broke silences both.

**uv's cache.** The uv toolkit's write grant to uv's shared cache is classed narrowing. So it is committed, and setup applies it unasked ([ADR-008](ADR-008-confinement-allowances.md) points 1 and 3). ADR-066 point 6 notes that a person's later uv runs execute what lands there. On macOS, uv cannot run inside the sandbox at all (ADR-014), so the grant serves no sandboxed uv there.

## Decision

**Nothing a sandboxed command can write is run outside the sandbox, or widens what is allowed there. The permission hook and its decision core run from the installed release, in a folder out of reach. The hook allows no more than the model a person last realized. Where it has no model it can trust, it keeps the guardrails and its own asks. uv's shared cache leaves the committed sandbox.**

### 1. What a sandboxed command can write is never trusted outside the sandbox

- **The rule.** Code that runs outside the sandbox never comes from a place a sandboxed command can write. Nor does anything such code reads as policy or configuration widen what it allows. Such input may narrow what is allowed, since narrowing cannot help a command reach further.
- **What it covers:** code that is run, with the interpreter that runs it and what that interpreter loads as it starts, and data read as policy or configuration.
- **A write grant** that opens such a place to sandboxed commands widens the boundary, however it was classed (point 5).
- **What this record mends:** the permission hook, its core and its model (points 2 to 4), and the write grants pkit ships (point 5). The rest of the class is open work (point 7).

### 2. The hook and the decision core run from the installed release

- **The copy.** The harness runs the hook from a copy in the backbone's state folder. That is the per-user folder where the backbone keeps its own state, agent-run clones among it (ADR-066 point 7). It lies outside every checkout, and no default write set or write grant pkit ships names it.
- **What the copy holds:** the hook, the decision core, the release's catalog, and what the hook needs to start. The copy names an interpreter outside every checkout, and starts it so that it loads no code from the session's environment or working folder.
- **Who makes it.** The gestures that install or upgrade pkit, and the gesture that turns the hook on, make the copy from the installed release, never from the checkout. They make it only outside the sandbox. Inside it, they make nothing and say so.
- **The registration.** The project's committed settings register the hook, since running it is the project's choice (ADR-002 point 2). They name the copy by a location each machine resolves for its own user, never by a path in the checkout.
- **A machine with no copy.** There the hook cannot start, which is the loud fault of ADR-002 point 4. The permission layer's overview, and the session's start, name the gesture that makes the copy.
- **The permission commands** load the core from their own release, as the workspace removal command loads its code from the running pkit (ADR-060 point 8). So the hook and the commands judge with one core (ADR-003). The overview reports a copy older than the running release.
- **What the hook reads from where.** It takes its code, the release's catalog and the snapshots of point 3 from its copy's folder. It takes the checkout from the session anchor ([ADR-034](ADR-034-foreign-repo-mutation-guard.md) point 1).
- **Out of the file tools' reach too.** The file tools run outside the sandbox. In every state, the fallback's included, the hook denies a file tool's write into its copy or its snapshots, whatever the model allows.
- **Its runtime** stays a zero-dependency script (ADR-014 point 1).

### 3. The hook allows no more than a person last realized

- **The model stays in the checkout.** It is the source of truth that people edit, review and commit (COR-028 point 1).
- **Realizing** (COR-028 point 2) keeps a *snapshot* of the checkout's model in the backbone's state folder. The snapshot holds every input the core reads as model, the active profile among them. It is keyed to the checkout by the checkout's path, and is never read for another checkout.
- **The verdict.** At each call the hook judges the call twice with the same core, by the snapshot and by the checkout's model, and acts on the stricter verdict. Deny is the strictest, then ask, then abstain, then allow.
  - **A change in the checkout that narrows the model,** such as a revoked grant, takes effect at once.
  - **A change that widens it,** such as a new grant or a more permissive active profile, takes effect only once realized.
  - **A sandboxed command** can thus make the hook stricter, and never more permissive than the snapshot.
- **What realizes.** Each permission command that writes the model realizes what it wrote. One command realizes the model as the checkout holds it, after a pull, a branch switch or an edit by hand. The gestures of point 2 realize it too.
- **Only outside the sandbox.** A command inside the sandbox realizes nothing. It says what it left unrealized, and names the gesture that realizes it. Whether realizing a wider model takes a person's gesture rather than an agent's call is [project-kit#3179](https://github.com/aleskalfas/project-kit/issues/3179)'s to decide.
- **A narrowing not yet realized** holds only while the checkout holds it. The snapshot is the bound a sandboxed command cannot pass, so a later write could restore what the snapshot allows. The overview reads the snapshot back (COR-028 point 2), and names each place where it allows more than the checkout's model.
- **A working run's hook** keeps its own arrangement. Its runner writes its model out of reach, and nothing the run writes changes it (ADR-073 point 2).

### 4. With no model it can trust, the hook keeps the guardrails and its own asks

- **When.** No snapshot exists for the checkout, or the snapshot or the checkout's model will not load.
- **What the hook then does:**
  - allows nothing by the model;
  - denies the guardrails of its copy's catalog, the hook's half of the double lock (ADR-002 point 3);
  - asks where a shell call may hide a guardrail, giving way to the mode as ADR-025 point 7 says;
  - asks before a file tool writes outside the session's repository, in every mode (ADR-034 point 2);
  - abstains on every other call, so the harness's native rules decide it.
- **What it says.** Each ask and each deny says that the model is not in force, and names the gesture that realizes it.
- **Faults.** A fault inside the fallback abstains, as a decision fault does (ADR-002 point 3). A hook that cannot start stays the loud fault of ADR-002 point 4.

### 5. A write grant is narrowing only where nothing outside the sandbox runs what it writes

- **The test.** A write grant is narrowing only where nothing outside the sandbox later runs, or reads as configuration, what a sandboxed command writes through it. Every other write grant is widening. ADR-008 point 4 governs it: never committed, never applied unasked, always reported.
- **uv's shared cache fails the test.** uv builds and installs from that cache what it later runs. The person's own uv runs use it on every platform. On macOS, so does the session's uv, which runs outside the sandbox. So the grant leaves the committed sandbox and setup's automatic step. A person may still apply it, as a widening.
- **Where uv runs inside the sandbox,** as on Linux, it gets a cache of its own that only sandboxed commands use. Setup sets that cache per machine ([ADR-032](ADR-032-per-machine-activation-routing-axis.md) Rule A). It does so only where no command that starts uv runs outside the sandbox.
- **On macOS** uv cannot run inside the sandbox, so removing the grant costs nothing there.
- **Every other write grant pkit ships,** the node toolkit's caches among them, is judged by the same test in the change that builds this record.

### 6. The tests, and the probe before the build

- **Tests hold that a sandboxed command:**
  - cannot write the hook's copy, the core it runs or a snapshot;
  - can change the checkout's grants, profiles, active profile, configuration or catalog, but never make the hook allow more than the snapshot does;
  - meets, where the model will not load, an ask before a file tool writes outside the repository, and a deny on a guardrail.
- **Tests also hold** that the permission commands load the core from their own release. They hold that no write grant pkit commits opens a place point 1 keeps out of reach.
- **The probe** runs on a live harness on each platform, and confirms what this record assumes:
  - hooks run outside the sandbox;
  - the committed registration finds the per-user copy at the checkout's root, in a subagent working in a worktree, and in a session started in a worktree;
  - which checkout the session anchor names in each of those three, and so which snapshot the hook reads;
  - the harness keeps its settings files out of a sandboxed command's reach;
  - no default write set reaches the backbone's state folder;
  - uv inside the Linux sandbox works with a cache that only sandboxed commands use;
  - judging each call twice adds an acceptable delay.
- **A fact the probe disproves** is mended by refining or superseding this record before the build rests on it.

### 7. What stays open

Each gap below is reported rather than hidden, as COR-028 point 3 asks.

- **Who realizes.** Until project-kit#3179 is decided and built, an agent's call that runs outside the sandbox can realize a model that a sandboxed command widened. On macOS the permission commands run there.
- **Other code run outside the sandbox from the checkout.** Point 1 binds the other hooks pkit registers from the checkout, and the code an excluded command runs from it. ADR-014 point 3 already reports the second on macOS. This record mends neither, and follow-up issues filed with this change hold them.
- **Configuration the harness loads from the checkout,** such as the agents and skills pkit deploys. The probe says which of these the harness protects, and point 1 binds the rest.
- **A runner's reads from the repository's history.** A working run reads its hook and model from the default branch (ADR-073 point 2). Point 1 binds that history where it lies in a folder a sandboxed command writes.
- **An install from source.** Where pkit runs from a source checkout ([ADR-033](ADR-033-official-install-bundles-content.md) point 2), the release that point 2 copies from is that checkout.
- **What runs outside every sandbox,** such as the person's own terminal or an excluded command, can write the backbone's state folder. The sandbox bounds only what it confines.
- **A working folder or a write grant over the backbone's state folder** opens it to sandboxed commands. The overview says so where it finds one.
- **A broken model is a nuisance.** A sandboxed command can force the fallback, which costs prompts and widens nothing.

## Rationale

**Why policy as well as code.** The model decides what the hook allows. A sandboxed command that could widen the model would gain what changing the code gains, without touching the code. So the rule covers both, and lets the checkout only narrow.

**Why the code comes from the release.** Three ways keep the code out of reach: deny writes to its files where they lie, read it from history, or run it from elsewhere.

- **Denying sandboxed writes in the checkout** breaks the commands that move a working tree, such as a branch switch, a pull or a rebase. It breaks sync too, where sync runs inside the sandbox. Such a command could fail partway, and leave a working tree half moved.
- **Reading from the default branch** reads a git folder that sandboxed commands write (ADR-066, Context).
- **The release** is installed outside every checkout, by a person. The runner's hook (ADR-073 point 2) and the workspace removal command (ADR-060 point 8) already keep their code off the checkout.
- **The cost:** a change to the hook or the core reaches a session only once it is released and installed. Tests and CI still run the checkout's code, and in an install from source the release is the checkout.

**Why the registration stays committed.** Running the hook is the project's choice (ADR-002 point 2), and a committed registration reaches every clone and worktree. Where a machine has no copy, the hook's failure to start is loud. A registration kept per machine would leave a fresh clone, or a new worktree, with no hook and no fault.

**Why the hook judges by both the snapshot and the checkout.**

- **The checkout alone** is the gap this record closes.
- **The snapshot alone** keeps a revoked grant in force until someone realizes. That is a boundary believed but absent (ADR-004).
- **Falling back on any difference between the two** would drop the model at each pull, sync and branch switch. A narrowing would wait for a gesture it does not need.
- **The stricter of the two verdicts** lets the checkout narrow at once and widen only through realizing. The core stays as it is, and runs twice.

**Why the fallback keeps these and no more.** The guardrails are the catastrophic denies, and keeping the hook's half of their double lock costs nothing (ADR-002 point 3). The two asks are the hook's own, and no native rule stands in for them. Asking on every call would flood the person with prompts approved unread ([project-kit#2002](https://github.com/aleskalfas/project-kit/issues/2002)). Denying every call would stop the session over a model that one command broke.

**Why uv's shared cache widens.** ADR-008 classed a build cache narrowing because it makes the box usable without enlarging the agent's reach. A cache whose contents the person's own runs later execute does enlarge it, since what a sandboxed command wrote later runs unconfined. Point 5's test states the line that ADR-008's split was drawn to keep.

### Alternatives considered

- **Deny sandboxed writes to the permission files where they lie.** Rejected: it breaks the commands that move a working tree, and sync where sync runs inside the sandbox.
- **Read the model from the default branch's head.** Rejected: the git folder is open to sandboxed writes (ADR-066, Context), and a branch's own model would never apply.
- **Act on a snapshot of the model alone.** Rejected: a revoked grant stays in force until someone realizes.
- **Fall back on any difference between the snapshot and the checkout.** Rejected: every pull, sync and branch switch would drop the model.
- **Start the hook through the pkit command found on the session's path.** Rejected: that path may lead into a folder a sandboxed command writes. The hook would also need pkit's runtime, which ADR-014 point 1 keeps it free of.
- **Register the hook in each machine's local settings.** Not taken: a fresh clone or a new worktree would run with no hook and no fault. Running the hook would stop being the project's committed choice (ADR-002 point 2).
- **Keep the fallback silent.** Rejected: a sandboxed command could then silence the hook's own asks.
- **Ask on every call, or deny every call, in the fallback.** Rejected: prompts approved unread, or a stopped session.
- **Keep uv's cache grant committed, and report it.** Rejected: ADR-008 point 4 never commits a widening. A person may still apply it.
- **Point every session's uv at a cache inside the checkout.** Rejected: on macOS the session's uv runs outside the sandbox, and would run what that cache holds.
- **Move the active profile out of the checkout.** Not taken: the snapshot covers it, as it covers every input the core reads.
- **Mend every member of the class here.** Not taken: each needs a choice of its own, and the permission layer is the one the Task found.

## Implications

**Records this record refines in place.** Each edit takes a `(refinement per ADR-095)` pointer. No record is overturned in part, and none is superseded.

- **ADR-002:**
  - **Point 2:** the hook the registration names is a copy made from the installed release, in the backbone's state folder. The registration names it by a location each machine resolves. The propagated hook file stays the source the release ships.
  - **Points 3 and 4:** a model that will not load is neither fault class. The hook falls back as ADR-095 point 4 says, rather than abstaining.
- **ADR-003, its dependency direction:** the hook imports the core from its copy, and the permission commands import it from their own release. The core's code home stays where ADR-003 puts it.
- **ADR-008:** its Decision line and point 1 state point 5's test for narrowing. Its account of uv's cache follows the test, and the uv toolkit's cache entry is classed widening.
- **ADR-014:** its title, point 1's title and point 1 say the hook runs under the system interpreter, with no claim that it runs inside the sandbox. Its Rationale and Alternatives follow. This edit corrects a fact, changes no decision, and waits for the probe to confirm where hooks run.
- **ADR-025:** its Context, point 3, its rationale on a shell parser's altitude and its shell-parser alternative get the same fact correction, on the same condition.
- **ADR-060 point 8:** the same fact correction, on the same condition. The permission commands load the core from their own release, as the removal command does.
- **ADR-066 point 9:** a run in the unconfined form acts on its folder's model only as realized. The command that makes such a run's clone realizes the clone's model where it runs outside the sandbox, as point 3 and project-kit#3179 allow. Otherwise the run meets the fallback, and the run's result says so.

**Records that hold with no edit.** ADR-073 point 2 already keeps a working run's hook out of reach. ADR-029 routes the reclassified uv entry by its own rule, and ADR-032 is unchanged, since the registration stays committed.

**The build:**

- **The backbone:** the permission commands' core from their release, realizing and its snapshots, the overview's read-back, and the uv toolkit's cache entry classed widening.
- **The Claude Code adapter:** the copy and its registration, the judgement by both models, the fallback, the hook's guard on its own folder, and its enforcement declaration.
- **The documents:** the adapter's README on where the hook runs, on what it does when its model will not load, and on turning it on. The permissions README and the CLI reference follow.
- **A migration** ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)) rewrites the committed registration pkit wrote, and makes the copy on a machine where it runs outside the sandbox. It removes from the committed sandbox the uv cache grant pkit wrote, by its provenance (ADR-008 point 2), never one a person added.
- **Other machines** of the project run with the loud fault until their person makes the gesture, and the release's notes say so.
- **Changesets** declare each component's surface change ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)).

**Open work filed with this change:** the other hooks pkit registers from the checkout, the code that excluded commands run from it, and a runner's reads from the repository's history (point 7). project-kit#3179 builds on this record.

**What this record stands on:** COR-010, COR-028, PRJ-002, and ADR-002, ADR-003, ADR-004, ADR-008, ADR-014, ADR-021, ADR-025, ADR-032, ADR-033, ADR-034, ADR-060, ADR-066 and ADR-073, all accepted.
