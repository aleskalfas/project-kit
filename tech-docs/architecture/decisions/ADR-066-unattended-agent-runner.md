---
id: ADR-066
title: Commands start agents through the adapter's runner, and an unwatched run holds only its own rules
status: proposed
date: 2026-10-18
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** some commands start an agent with nobody watching. The review command, `review-pr`, starts reviewers today, and the drift command will start fixers ([project-management:DEC-056-drift-fixers]). The review command calls the `claude` command line itself, and no record says how it should.

Under this record, no command calls a harness. A command asks the backbone to run an agent, and the backbone hands the request to the runner of the project's adapter. The backbone finds the runner by name, as the lifecycle finds the deploy primitives. Where the adapter ships no runner, no agent starts, and the command says why.

A run nobody watches is confined, as DEC-056 point 5 decides:
- It runs in a fresh working copy of the repository, at a pinned commit.
- It loads none of the person's or the project's settings, only its own rules from the permission model.
- A call those rules do not allow is refused, never asked.
- The operating-system sandbox bounds what its shell writes and reaches.
- No flag or setting that bypasses permissions is ever passed.
- After the run, the backbone checks the working copy, and only then hands back the run's files.

What the harness cannot hold is stated, not hidden (point 11). The review command's runs stay unconfined until a record decides otherwise. #1741 asked for this record, and #1742 moves the runner to the home it names.

## Context

Two commands start agents with nobody watching, so the runner has earned a home of its own ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)).
- **The review command** runs each required reviewer as `claude -p <brief> --agent <name>`, adding `--effort` where one is set. It runs in the person's checkout, under a wall-clock limit. Nothing confines the run, and the run gets no settings of its own. The tie to `claude` sits in a capability's script, and no record decided it.
- **The drift command** starts the fixers the person granted (DEC-056 point 3). Each run is bounded (point 4) and confined as far as the harness can hold it (point 5).

DEC-056's Implications leave three things to the methodology's architecture decisions:
- where the runner lives
- how the adapter realises each part of point 5, and the shape the permission model gives a rule scoped to a run
- what the permission layer sees, and the check after each run

The design was worked out in the retired note `2026-10-18-drift-starts-fixer`, and DEC-056 governs where the two differ. The architect's review on #1740 recommended an adapter primitive over project-management's library. It also found that a run on macOS needs ADR-014's sandbox exclusion.

**The permission layer today:**
- The permission model is the harness-neutral truth, and each adapter realises it ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) point 2).
- The Claude Code adapter's permission hook fails open. So a deny that must hold also sits in the harness's native rules ([ADR-002](ADR-002-permission-realizer-ownership.md) points 3 and 5).
- The hook names the subject it judges from the call's `agent_type`. Without one, it reads the `agent` key in `.claude/settings.json`, and then falls back to `operator` (the permissions README, "Default-agent subject resolution").
- The OS sandbox bounds what a shell reaches, and the hook does not ([ADR-004](ADR-004-autonomy-intent-confinement.md)). On macOS, `pkit` runs outside the sandbox while the installed `uv` needs it ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) and [ADR-027](ADR-027-required-sandbox-exclusion-auto-apply.md)).
- Mutable sandbox state lives in the gitignored local settings file ([ADR-029](ADR-029-move-mutable-sandbox-state-out-of-tracked-settings.md)). So a fresh working copy holds none of the person's exclusions.

**What the harness does, as observed.** These facts are Claude Code's, as its `claude --help` (2.1.302) and its documentation gave them on 18 October 2026. Point 12 lists the ones the live trial must confirm.
- **Starting a run:**
  - `-p` runs a session headless, and `--agent` runs it as a named agent.
  - `--settings` adds settings for one session. Its lists merge with the lists of the settings files, and do not replace them.
  - `--setting-sources` chooses which of the user, project and local files load. `--restricted` loads only the admin-managed settings and `--settings`, and refuses the bypass mode. Admin-managed settings always apply.
  - A `-p` run in a folder nobody trusted skips the project's allow rules. It still runs the hooks in the project's settings, and connects the servers in its `.mcp.json`.
  - The harness reads every `CLAUDE.md` in the folders above the one it starts in.
- **Rules and hooks:**
  - A hook's allow approves a call no rule allows. A deny rule refuses the call, whatever a hook answers.
  - A `-p` run skips a settings value it rejects, and runs on with the rest.
- **Modes:**
  - `dontAsk` refuses every call that would ask. Reads in the working copy, the harness's own read-only commands, and calls a rule or a hook allows still run.
  - `auto` lets a classifier approve calls in place of a person. `acceptEdits` approves file edits and common filesystem commands.
  - `bypassPermissions` skips the checks, and lets a sandboxed command reach any host. `--dangerously-skip-permissions` starts in it, and `--allow-dangerously-skip-permissions` makes it available.
  - A `-p` run with no mode passed may start in `auto`, where the harness fetches no feature flags. A user's settings may set its starting mode too.
  - `--permission-prompts none` refuses whatever would ask, and tells the agent not to retry.
- **The sandbox:**
  - It wraps shell commands only. The harness itself, its file and web tools, hooks and MCP servers run outside it. Hooks and MCP servers run with the person's full access.
  - `failIfUnavailable` stops the harness at start when the sandbox cannot start. Without it, the harness runs commands unsandboxed.
  - `autoAllowBashIfSandboxed` is on by default, and approves every sandboxed command with no rule.
  - An `excludedCommands` entry runs a command outside the sandbox, with full access. The documentation warns that an entry covering a script in the working folder lets the agent change that script and run it outside.
  - `allowUnsandboxedCommands: false`, given through `--settings`, makes the sandbox admin-required. The repository's files can then no longer loosen it, their exclusions included.
  - By default a sandboxed command writes the working folder and a per-user temp folder. In a linked worktree, it also writes the repository's shared git folder. It reads most of the machine, and its allowed domains start empty.
  - `sandbox.credentials` withholds named variables and files from sandboxed commands.
- **Bare mode:** `--bare` skips hooks, agents, `CLAUDE.md` and plugins. It signs in with an API key, not the person's subscription. The documentation says it will become the default for `-p`.

## Decision

**A command starts an agent only through the backbone's run command, which hands the request to the runner the project's adapter ships. A run nobody watches is confined to a fresh working copy and to its own rules from the permission model. The harness's native rules hold those rules, a mode refuses what they do not allow, and the sandbox wraps the run's shell. No flag or setting that bypasses permissions is ever passed. The backbone checks each confined run, and what the harness cannot hold is stated.**

The points:
- Points 1 and 2 place the runner, and set what crosses its boundary.
- Points 3 to 8 confine a run: its rules, its mode, a rule's shape, its sandbox, its working copy and check, and its marker.
- Points 9 and 10 say what the hook sees, and what the review command's runs get.
- Points 11 to 13 state what stays open, what the trial confirms, and the harness requirement.

### 1. The runner is the adapter's, and commands reach it through the backbone

- **The adapter holds the tie to the harness.** Starting an agent turns harness-neutral content into one harness's terms, which is an adapter's work ([COR-005](../../../.pkit/decisions/core/COR-005-bundle-pattern.md) and [COR-013](../../../.pkit/decisions/core/COR-013-agent-architecture.md)). DEC-056 point 5 already puts the realisation of a run's rules there.
- **Found by name.** The runner is a primitive in the adapter's folder, found by one fixed name, as the deploy primitives are. The adapters README records that name beside theirs.
- **Reached through one backbone command.** A capability never calls a harness, and never looks for an adapter. It asks the backbone's run command to run an agent. That command finds the registered adapter's runner, and passes the request on.
- **What the backbone command does itself:**
  - it refuses inside a run (point 8)
  - it projects a confined run's rules from the model, through the shared decision core ([ADR-003](ADR-003-permission-core-code-home.md))
  - it makes, checks and removes a confined run's working copy (point 7)
- **What the runner does:** everything in its harness's terms. It turns the projected rules into the run's native settings, starts the harness, ends it at its limit, and reads back what the harness reports.
- **No runner.** Where no registered adapter ships one, the backbone command refuses and names the adapter. The calling command starts no agent and says why. Where more than one ships one, the backbone command refuses and names them. A later record says how a project names its harness, once a second adapter ships a runner.
- **What stays with the caller:** which agents start, their briefs, the commit, DEC-056 point 4's bounds, and what becomes of the run's files.

### 2. What a caller passes, what it gets back, and when a run is refused

**The caller passes:**
- the agent, by name
- the brief
- where the run happens: a commit for a confined run, or a folder for the review command's unconfined run (point 10)
- for a confined run, the command whose run it is, which selects the run's rules (point 5)
- limits: a wall-clock limit, and an effort level where the caller sets one
- for a confined run, the folder the run's files go to

**The caller gets back:**
- how the run ended: finished with the harness's exit, could not start, stopped at its limit, or refused, each with its reason
- the agent's output
- for a confined run, the run's files, copied where the caller asked, and the check's verdict (point 7)
- the calls the harness refused, where the harness reports them
- each command the run carried outside the sandbox (point 6)

**A run is refused before anything starts when:**
- the marker of a run is set (point 8)
- no runner is found, or more than one (point 1)
- the harness's command line is not found, or the agent is not deployed for it
- for a confined run, the harness cannot confine it:
  - the harness is older than the versions the adapter tested its confined form on
  - the platform offers no sandbox the harness can use
  - a deny that binds the run cannot be held natively (point 3)
  - the run's settings fail the harness's settings schema (point 3)

Each refusal names its cause. At the wall-clock limit, the runner ends the harness and every process it started.

### 3. A confined run loads only its own rules

- **No settings file of the person's or the project's.** The run loads its own settings, and the admin-managed ones it cannot drop. Observed today, `--restricted` does this, and `--setting-sources` can leave out each file. The adapter uses whichever the trial shows still starts the run's agent and signs the harness in (point 12).
- **So the run's allow list is the whole grant,** as DEC-056 point 5 asks. Settings lists merge, so a list beside the project's files could only add to them. With no file loaded, only the run's rules allow a call.
- **Every deny that binds the run is held as well.** The run's settings carry the run's own denies. They also carry each deny the model holds for the run's agent or for every agent, the shared baseline's guardrails among them. A deny that only repeats what the allow list refuses needs no rule. A deny the adapter cannot hold natively stops the run before it starts.
- **Held in the harness's native rules, never in the hook.** Native rules fail closed, and the hook fails open (ADR-002 point 3). That is where COR-028 point 2 puts a deny that must hold. A deny rule also refuses a call whatever a hook of the organisation's answers.
- **The run's workspace** is allowed by the narrowest path rule the harness offers. In a run the harness approves no write by itself, which is the case [ADR-060](ADR-060-path-scoped-workspace-allow.md) point 6 gives such a rule.
- **Checked before the run.** The adapter checks the run's settings against the harness's settings schema first. A run skips a value it rejects, and a skipped sandbox key would leave the run unconfined.
- **Out of the run's reach.** The run's settings are passed inline, or from a file in no folder the run writes. So the run cannot change the rules it runs under.
- **No memory.** The run's settings turn off the harness's own memory. So a run leaves no note that loads into the person's later sessions.
- **What dropping the files costs.** The run loses the project's hook, its native baseline, its sandbox floor and its environment block. The run's settings carry each deny and the floor themselves. The hook's view of the run is lost, and point 9 says what reads the run instead.
- **The fallback.** The trial may show that the harness cannot start the agent without the project's file. The adapter then loads that file, and turns off its hooks and its MCP servers for the run. The run is then held by its denies, as DEC-056 point 5 allows where the harness can only take away. The runner reports that the project's allows reach the run.

### 4. No flag or setting bypasses permissions

No flag or setting that bypasses permissions is passed to any run the runner starts. DEC-056 point 5 rules such a flag out, and this point makes the rule concrete. A flag, a mode or a setting bypasses the run's rules when it approves a call no rule allows.

- **Passed to a confined run, and nothing else:**
  - `-p` with the brief, `--agent`, and `--effort` where one is set
  - the run's settings, through `--settings`, and the flag that leaves out the settings files (point 3)
  - `--permission-mode dontAsk` and `--permission-prompts none`
  - the run's tool set, through `--tools`, and `--strict-mcp-config` with no server listed
  - an output format the runner reads the harness's report from
  - `--agents` with the agent's definition, only where the trial needs it (point 12)
- **Never passed, to any run:**
  - `--dangerously-skip-permissions`
  - `--allow-dangerously-skip-permissions`
  - `--permission-mode bypassPermissions`
  - `--permission-mode auto`, whose classifier approves calls in a person's place
  - `--permission-mode acceptEdits`, which approves edits and filesystem commands no rule names
  - `--permission-prompt-tool`, which answers prompts in a person's place
- **Never passed to a confined run either:** `--allowedTools`, since the run's allows live in its settings alone, and `--add-dir`, which opens another folder to the run.
- **Never set in a run's settings:** sandbox auto-approval, the unsandboxed retry, weaker network isolation, or a starting mode other than `dontAsk`. The settings turn auto-approval and the retry off by name, since auto-approval is on by default.
- **A call no rule allows is refused.** A confined run starts in `dontAsk`, with `--permission-prompts none`. The harness then refuses whatever would ask, and tells the agent not to retry. The mode is always passed, since a `-p` run's starting mode may otherwise be `auto`, or a mode a settings file set.
- **The harness's read-only commands still run.** Under `dontAsk` they need no rule. They only read, which DEC-056 point 5 allows, and the run's denies still bind them.
- **The run's tools.** The run's tool set holds only what its rules use: reading, searching, writing new files, and the shell. It holds no tool that starts an agent, edits an existing file or reaches the web. A web tool runs outside the sandbox, and some documentation hosts need no approval.
- **No MCP server.** The run connects none, since a server runs outside the sandbox with the person's full access.

### 5. A rule scoped to a run

DEC-056 point 5 makes the run's rules the permission model's. In the model's terms (COR-028 point 1), such a rule reads:
- **Subject:** every agent. The drift command starts agents that other capabilities ship, so the capability that declares the rules cannot name them. The grant list already decides which agents start (DEC-056 point 2).
- **Privilege:** a privilege of the catalog, as in any rule.
- **Scope:** the runs a named command starts through the runner. COR-028 point 1 lets a scope say when a rule applies, and this scope says it.
- **Effect:** allow or deny.

**Who declares it:** the capability whose command starts the runs, in its permission fragment ([ADR-016](ADR-016-capability-contributed-intent-grants.md)). A project adds its own as it adds any rule.

**Who realises it:** the adapter, for that run only. It is never merged into the project's settings files. Outside a run it never applies, so the hook and the permissions CLI read it and set it aside.

**What COR-028 does not yet say.** COR-028 point 1 makes an agent's permissions the union of the shared baseline and its own grants. Inside a run, DEC-056 makes the run's allows the whole grant, and keeps every deny. That composition is not in COR-028, so a core record should refine point 1 to state it (Implications). Until then, the run's allow list is DEC-056's decision for the runs its command starts, and it changes no other subject's permissions.

### 6. The sandbox around the run's shell

- **On, and failing closed.** The run's settings enable the sandbox and set `failIfUnavailable`. A harness that cannot start the sandbox then stops, and no run goes on unconfined (ADR-004 point 4). The runner checks the platform first, so a known gap is a refusal, not a failed start.
- **No retry outside it.** The unsandboxed retry is off, as the autonomy posture seals it ([ADR-028](ADR-028-seal-unsandboxed-escape-under-autonomy-posture.md)). Given through the run's own settings, that setting also makes the sandbox admin-required.
- **Writes:** only the run's working copy. The harness's temp folder for the shell is placed inside the working copy, where the harness lets the adapter choose it. The working copy is no linked worktree, so the repository's shared git folder stays closed to it (point 7).
- **Network:** no domain is allowed. Under `dontAsk`, the harness refuses every host the shell asks for.
- **Reads:** the run's settings block reads outside the working copy. They also deny the credential files the project's sandbox floor denies ([ADR-008](ADR-008-confinement-allowances.md)).
- **Secrets:** the run's settings withhold the caller's credential variables from the run's shell. The runner also turns on the harness's scrub of credentials from every process it starts, which reaches an excluded command too.
- **On macOS, the exclusion.** The run's settings exclude each command the run's rules allow and the sandbox cannot host. ADR-027's verifier judges that, as it does for `setup autonomy`. Today that is `pkit`, while the installed `uv` needs it (ADR-014).
  - The exclusion names only the commands the run's rules allow, never `pkit` as a whole, where the harness's patterns can say so.
  - `gh` is not excluded, though [ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md) excludes it from a session's sandbox. The run's rules deny `gh` (DEC-056 point 5).
  - The runner reports each excluded command with the run's result, as a widening must be (ADR-008 point 4). No file of the project's holds it.
  - What an excluded command does is held by the run's rules alone (point 11).

### 7. The run's working copy, and the check after the run

- **A clone outside every working tree.** The backbone command makes the run's working copy as a clone of the repository at the caller's commit. The clone's git folder lies inside it, and the clone lies outside every working tree of the repository.
  - A linked worktree shares the repository's git folder, which the sandbox opens to writes. The run could then move the person's references.
  - Outside every working tree, the harness reads no `CLAUDE.md` of the person's checkout, which may hold changes that never merged.
- **Provisioned as the project's checks are** (DEC-056 point 3), so every anchor resolves there. The run's agent is the definition at that commit.
- **Before the run,** the backbone command records the working copy's references and its ignored files.
- **After the run, it checks three things** (DEC-056 point 5):
  - nothing changed in the working copy outside the run's workspace
  - no reference of the working copy moved
  - no ignored file appeared outside the run's workspace
- **After a failed start too.** So the caller knows whether a start that failed wrote anything, as DEC-056 point 4 asks before its retry.
- **A breach** comes back with what changed, and the caller sets the run's files aside (DEC-056 point 5).
- **A check, not a boundary.** It finds a breach after it happened, and only inside the working copy. Only an excluded command could write outside it (point 11).
- **Then the files, then the removal.** The backbone command copies the run's workspace to the folder the caller named. Then it removes the working copy. Each confined run first removes any working copy a killed run left behind.

### 8. A run is a leaf

DEC-056 point 5 makes a fixer start no other agent. A run could start one in two ways, and both are closed.
- **The harness's dispatch tool** is not in the run's tool set (point 4).
- **A command that starts agents** is denied by the run's rules. A marker is the second lock:
  - The backbone run command sets `PKIT_AGENT_RUN` in the harness's environment, for every run it starts. Every process the run starts inherits it.
  - The backbone run command refuses when it finds the marker set, before it does anything else. Any value but an empty one refuses, with no override.
  - So each command that starts agents through the runner refuses inside a run, the drift command and the review command included.
  - Nothing else sets or unsets the marker, as [ADR-065](ADR-065-upgrade-runs-the-transition.md) point 14 keeps its migration marker.

### 9. What the permission hook sees

- **In the session that runs the command,** the hook sees one shell call, the command itself. It judges that call for the session's subject.
- **Inside a confined run, it sees nothing.** The run loads no project settings, so the hook is not registered there. The run's settings are the model's realisation for that run.
- **What reads a confined run back** (COR-028 point 2): the harness's report of the calls it refused, which the runner returns, and the check of point 7.
- **Inside the review command's runs,** the hook runs as it does in the person's session. Which subject it judges there is not known (point 11).

### 10. What the review command's runs get

#1742 moves the review command onto the runner, and changes nothing it does. So its runs keep today's shape, as the runner's unconfined form:
- They run in the person's checkout, under the person's and the project's settings.
- They start in the mode those settings or the harness choose.
- The runner passes `-p`, `--agent`, and `--effort` where one is set. It ends a run at its wall-clock limit.
- Nothing confines them beyond the person's own sandbox settings, and no check follows them.

**Not decided here:** whether the review command's runs are confined. A confined review would run in a working copy at the pull request's head, under rules for reading it. That is a decision of its own. Until it is made, a new command that starts agents asks for a confined run, and the unconfined form serves the review command alone.

### 11. What stays open

Each item says what holds the intent and what is left, as COR-028 point 3 asks.
- **Network egress.** The run's shell reaches no host through the sandbox. What is left:
  - The sandbox checks the host a client names, so it is no control on data leaving (ADR-004).
  - An excluded command has the person's full network access.
  - The harness's own connection to its model carries what the run reads. The sandbox leaves that connection alone by design, so what the run may read, it may send.
  - A project closes this outside the harness: at the network, or by running the harness in a container or a virtual machine.
- **The macOS exclusion.** `pkit` runs outside the sandbox in each run, while the installed `uv` needs it (point 6). What is left:
  - Its writes and its egress are held by the run's rules alone, and the check sees only the working copy.
  - An excluded command may run code the working copy holds, such as a component's query command. The run's rules on writes, not the sandbox, keep that code as committed.
  - A `uv` release the sandbox can host closes it (ADR-014 point 4), and so does a container.
- **What the hook sees.** The hook sees the command, not each agent it starts (DEC-056 point 5). What is left:
  - In a confined run it sees nothing (point 9). The run's settings and the harness's report stand in for it.
  - In the review command's runs, `--agent` sets the session's agent without changing the file the hook reads. So the hook may judge a reviewer as the project's default agent, or as `operator`.
  - No per-agent grant counts in those runs until the trial shows which subject the hook judges.
- **The words a proposal carries.** A proposal is data, and each command is built from its fields (DEC-056 point 6). Its diff and its answers' words can still carry a contributor's steering. So the person reads every word before accepting it.
- **An organisation's managed settings.** They reach every run, and the run cannot drop them. They may allow more, run hooks of their own, or set the run's rules aside. The runner cannot always read them, so the organisation closes this gap.
- **The temp folder.** The harness may not let the adapter place the shell's temp folder inside the working copy. The shell then also writes a per-user temp folder, which the check does not see.
- **A harness that can only take away.** There, the project's allows outside the denied categories reach the run (DEC-056 point 5). This holds for Claude Code too, if the trial needs point 3's fallback. The runner then reports it.
- **The review command's runs.** They are unconfined (point 10). A reviewer runs in the person's checkout, and may write there. It runs under the person's settings, in a mode that may approve calls no rule allows. Nothing checks its run.

### 12. What the live trial confirms

The trial of DEC-056's build runs each fixer once, headless, on a seeded stale artefact. Until it does, these facts rest on the harness's documentation:
- With no settings file loaded, the run's agent loads and the harness signs in. Where the agent does not load, the adapter passes the agent's definition at the run's commit to the harness itself.
- A call the run's settings do not allow is refused, with no prompt, and the run goes on.
- Writes with the file tools land in the run's workspace, and nowhere else.
- With auto-approval off, a sandboxed command the run's rules do not allow is refused.
- A sandbox that cannot start stops the harness at start.
- On macOS, the run's own exclusion lets the allowed `pkit` commands run with the unsandboxed retry off, as ADR-028 point 3 asks of a session.
- A run started from inside a session's sandbox can start its own sandbox and reach its model.
- The marker reaches the run's shell, and the credential variables do not.
- The harness's report of refused calls reaches the runner.
- In a review command's run, the hook judges a subject the trial names.

A fact the trial disproves refines this record before the drift command ships.

### 13. The harness requirement

DEC-056's Implications name one requirement on the harness ([COR-047](../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md)). This record words it in terms any harness could meet:

> A process can start an agent with nobody attending. For that one run, the agent is confined to rules and a folder the process sets. A call those rules do not allow is refused, not asked. After the run, the process can read the run's files and its outcome.

- **Observation point:** outside a session, by starting a probe run.
- **Evidence:** DEC-056 point 5, a design dependency (COR-047 point 9). It is no transient defect, so it names no retirement condition.
- **Declared with the drift command.** That change adds it to the requirement set. The adapters' support declarations are not yet shipped (the adapters README, "Harness requirements"). Until they are, the runner's refusal of an untested harness (point 2) stands for the Claude Code adapter's answer.

## Rationale

**Why the adapter, reached through the backbone.** A harness's command line is that harness's, so it belongs in its adapter, as every other harness tie does (COR-005). A capability that calls `claude` ties its command to one harness, as the review command does today. A capability that looked for an adapter itself would tie its command to the backbone's registry. The lifecycle already finds an adapter's primitives by name, so the backbone finds the runner the same way.

**Why a confined run loads no settings file.** It gains three things:
- The allow list holds in the harness's native rules, which fail closed. Lists merge, so the run's list beside the project's could only add.
- The project's hooks and MCP servers never start in a run. Both run outside the sandbox with the person's full access, even in a folder nobody trusted. Otherwise a merged change could add one that runs unwatched.
- The person's own allows and starting mode never reach a run.

It costs the hook's view and the project's floors. The run's settings carry the floors themselves, and point 9 says what reads the run instead.

**Why `auto`, `acceptEdits` and sandbox auto-approval count as bypasses.** The run's rules are the whole grant only if nothing else approves a call. `auto` puts a classifier where a rule should be, and `acceptEdits` approves calls no rule names. Sandbox auto-approval approves every sandboxed command. Each would turn the allow list into a suggestion.

**Why `dontAsk`, passed every time.** A run nobody watches cannot answer a prompt, so a prompt can only stall or be refused. `dontAsk` makes the refusal the harness's own, and `--permission-prompts none` tells the agent not to retry. The mode is passed because a `-p` run's starting mode depends on the machine.

**Why a clone outside every working tree.** In a linked worktree, the sandbox opens the shared git folder, so a run could move the person's references. The references are shared too, so the check could not tell the run's moves from the person's own commits. Inside a checkout, the harness would also read that checkout's `CLAUDE.md`, which may hold unmerged changes.

**Why the backbone owns the working copy and the check.** The check is harness-neutral, so it is not the adapter's. Its before-state is the working copy's state when made, so the part that makes the working copy records it. A command that starts a confined run then gets both without writing them again.

**Why a marker beside the rules.** The rules deny each command that starts agents, but a rule names commands, and a new one could be missed. The marker refuses in the one place every such command passes. ADR-065 point 14 keeps a migration from starting a lifecycle operation the same way.

**Why every agent is the subject.** The drift command starts agents that other capabilities ship. The capability that declares the run's rules cannot name them, and should not need to. The grant list already says which agents start.

**Why the review command stays as it is.** #1742 is a move, and a move that changed what reviewers may do would hide a decision in it. Confining a review needs a working copy at the pull request's head, and rules for reading it. That deserves its own record.

### Alternatives considered

- **The runner in project-management's library.** Rejected. It keeps the harness tie in a capability, and the next capability that starts agents would copy it. The architect's review on #1740 recommended against it.
- **The runner in the backbone, calling `claude` itself.** Rejected. The backbone would carry one harness's command line (COR-005).
- **The capability finds the adapter's runner itself.** Rejected. Each capability would depend on the backbone's registry and on the adapters' layout.
- **Keep the project's settings files, and add the run's denies.** Not taken as the default. The project's hooks and MCP servers would run unwatched with full access, and the hook's allows would approve calls the run's list does not name. It stays point 3's fallback.
- **`--bare`.** Rejected. It signs in with an API key only, and it stops loading the project's agents.
- **`auto` with `--permission-prompts none`,** the documentation's own example of an unattended run. Rejected. A classifier approves calls no rule allows.
- **The run's rules in the permission hook.** Rejected. The hook fails open (ADR-002), so a broken hook would leave a run unconfined while it looked confined.
- **A linked worktree for the run.** Rejected, for the reasons above.
- **A container or a virtual machine for each run.** Not taken now. It would close the egress and macOS gaps, but the methodology ships no such mechanism. A project may add one outside the harness (COR-028 point 3).
- **Confine the review command's runs in #1742.** Rejected. #1742 changes no behaviour.

## Implications

- **#1742 moves the runner.** It builds the backbone's run command, the Claude Code adapter's runner in its unconfined form, and the review command's call to it. The review command does what it did before. The new command and primitive are additions an adopter can see, so the change judges its changeset as PRJ-002 asks.
- **The drift command's change builds the rest:** the confined form, the working copy and its check, the marker, the run's rules in project-management's permission fragment, and their projection in the shared core.
- **A refinement of COR-028 point 1** should state that a grant scoped to a run is the whole grant inside it. Every deny still applies there (point 5). This record names the refinement, and a core record decides it. Whether the drift command's build waits for it is the maintainer's call.
- **ADR-027's carve-out reaches the runner.** The runner applies the platform's required exclusion to each run, with nobody watching, as `setup autonomy` applies it to a session. That widens who applies a widening, as ADR-030 widened what the carve-out covers. So accepting this record is the person's sign-off on it, as ADR-030's acceptance was.
- **The grants shape gains a scope that names a run.** Whether that bumps its schema is for the drift command's change to judge ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)).
- **Docs:**
  - the adapters README lists the runner beside the deploy primitives
  - the Claude Code adapter's README states the confined form's flags and settings
  - the adapter's enforcement declaration names what holds a run, and what stays open (COR-028 point 3)
  - the permissions README, "Default-agent subject resolution", says that `--agent` sets a session's agent without changing the file the hook reads
  - the CLI reference documents the backbone's run command
- **A follow-up record** decides whether the review command's runs are confined (point 10).
- **No migration.** Every change adds.
- **Supersedes nothing.** It realises DEC-056 point 5, and applies ADR-004, ADR-008, ADR-014, ADR-027, ADR-028 and ADR-029 to a run.
- **Stands on these records, all accepted:** COR-005, COR-007, COR-010, COR-013, COR-028, COR-046, COR-047, DEC-056, ADR-002, ADR-003, ADR-004, ADR-008, ADR-014, ADR-016, ADR-027, ADR-028, ADR-029, ADR-030, ADR-060 and ADR-065.
