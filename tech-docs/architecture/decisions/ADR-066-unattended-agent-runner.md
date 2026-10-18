---
id: ADR-066
title: Commands start agents only through the adapter's runner
status: proposed
date: 2026-10-18
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** some commands start an agent with nobody watching. The review command starts reviewers today, and the drift command will start fixers ([project-management:DEC-056-drift-fixers]). The review command calls the `claude` command line itself, and no record says how it should.

Under this record, no command calls a harness. A command asks the backbone to run an agent, and the backbone starts the runner the project's adapter registers. The runner starts the harness. Where no adapter registers a runner, no agent starts, and the command says why.

The drift command's runs are confined, as DEC-056 point 5 decides:
- Each runs in a fresh clone of the repository at a pinned commit, and its shell writes only the run's own workspace.
- It loads none of the person's or the project's settings, and no agent definition the runner has not checked.
- Its rules are denies in the permission model. The harness holds them by allowing only what proposing needs, and refusing the rest without asking.
- The operating-system sandbox bounds its shell, and no network host is allowed.
- After the run, the backbone checks the clone, and only then hands back the run's files.

No run, confined or not, is passed a flag that bypasses permissions. The review command's runs keep today's shape until a record decides otherwise, so they are not confined. What the harness cannot hold is stated, not hidden (point 11).

## Context

Two commands start agents with nobody watching, so the runner has earned a home of its own ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)).
- **The review command** runs each required reviewer as `claude -p <brief> --agent <name>`, with `--effort` where one is set. It runs in the person's checkout, under a wall-clock limit. Nothing confines the run, and the tie to `claude` sits in a capability's script that no record decided.
- **The drift command** starts the fixers the person granted. Each run is bounded, and confined as far as the harness can hold it (DEC-056 points 3 to 5).

DEC-056's Implications leave three things to the methodology's architecture decisions:
- where the runner lives
- how the adapter realises each part of point 5, and the shape the permission model gives a rule scoped to a run
- what the permission layer sees, and the check after each run

The design was worked out in the retired note `2026-10-18-drift-starts-fixer`, and DEC-056 governs where the two differ.

**The permission layer and the backbone today:**
- The permission model is the harness-neutral truth, and each adapter realises it ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) point 2).
- The Claude Code adapter's permission hook fails open. So a deny that must hold also sits in the harness's native rules ([ADR-002](ADR-002-permission-realizer-ownership.md) point 3).
- The hook judges the subject a call's `agent_type` names. Without one, it reads the `agent` key in `.claude/settings.json`, and then falls back to `operator` (the permissions README, "Default-agent subject resolution").
- The OS sandbox bounds what a shell reaches, and the hook does not ([ADR-004](ADR-004-autonomy-intent-confinement.md)). On macOS, `uv` cannot run inside it, so `pkit` runs outside it while the installed `uv` needs that ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) and [ADR-027](ADR-027-required-sandbox-exclusion-auto-apply.md)).
- A capability or an adapter registers the commands the backbone may run in its package's `commands:` tree. The backbone has one lookup of that tree, and one bounded run with a policy for each kind of command ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 5).

**What the harness does, as observed** in Claude Code's `claude --help` (2.1.302) and its documentation on 18 October 2026. A probe confirms these facts (point 12).
- **Configuration:**
  - `--settings` adds settings for one session. Its lists merge with the settings files' lists, and do not replace them.
  - `--restricted` loads only the admin-managed settings and `--settings`, and `--setting-sources` can leave out each settings file. Admin-managed settings always apply.
  - A `-p` run skips a settings value it rejects, and runs on with the rest.
  - A `-p` run in a folder nobody trusted still runs the project's hooks and its MCP servers.
  - An agent's definition can carry hooks, MCP servers, a permission mode and memory. A definition passed with `--agents` runs its hooks with no trust step. A skill can approve tools for itself.
- **Permissions:**
  - A hook's allow approves a call no rule allows. A deny rule refuses the call, whatever a hook answers.
  - `dontAsk` refuses every call that would ask. Reads in the working folder and the harness's own read-only commands still run with no rule.
  - `auto` lets a classifier approve calls, and `acceptEdits` approves edits and common filesystem commands. `bypassPermissions` skips the checks.
  - A `-p` run with no mode passed may start in `auto`, or in a mode the user's settings set.
- **The sandbox:**
  - It wraps shell commands only. The harness itself, its file tools, hooks and MCP servers run outside it, hooks and servers with the person's full access.
  - A sandboxed command writes its working folder and a per-user temp folder. In a linked worktree, it also writes the repository's shared git folder. It reads most of the machine.
  - `autoAllowBashIfSandboxed` is on by default, and approves every sandboxed command with no rule.
  - An excluded command runs outside the sandbox with full access. The documentation warns that an exclusion covering a script the agent can change lets the agent run that script outside.

## Decision

**A command starts an agent only through the backbone, which starts the runner the project's adapter registers. A confined run loads only its own settings and a checked agent definition. Its shell writes only the run's workspace, and the harness refuses whatever its settings do not allow. In the model the run's rules are denies, and no flag that bypasses permissions is passed to any run.**

The points:
- Points 1 and 2 place the runner, and set what crosses its boundary.
- Points 3 to 8 confine a run: its settings, the bypasses it never gets, its rules in the model, its sandbox, its clone and check, and its marker.
- Points 9 and 10 say what the permission layer sees, and what the review command's runs get.
- Points 11 to 13 state what stays open, the probe, and the harness requirement.

### 1. The runner is a command the adapter registers, and the backbone runs it

- **The adapter holds the tie to the harness.** Starting an agent turns harness-neutral content into one harness's terms, which is an adapter's work ([COR-005](../../../.pkit/decisions/core/COR-005-bundle-pattern.md) and [COR-013](../../../.pkit/decisions/core/COR-013-agent-architecture.md)). DEC-056 point 5 already puts the realisation of a run's rules there.
- **Registered, not found by file name.** The adapter registers its runner in its package's `commands:` tree, under one fixed reference. The backbone finds it with its one lookup, and runs it as a process with a policy for agent runs (ADR-057 point 5). No backbone code imports the adapter's ([ADR-003](ADR-003-permission-core-code-home.md)).
- **Reached through one backbone command.** A capability never calls a harness, and never looks for an adapter. It asks the backbone's run command to run an agent.
- **What the backbone's run command does:**
  - it refuses inside a run (point 8)
  - it makes, checks and removes a confined run's clone (point 7)
  - it reads the run's rules from the clone, and projects them through the shared decision core (ADR-003)
  - it judges which allowed commands the platform requires outside the sandbox, by ADR-027's test (point 6)
- **What the runner does,** in its harness's terms:
  - it checks the platform and the harness's version
  - it builds the run's settings and the agent's definition
  - it starts the harness, reads its start report, and ends it at its limit
- **No runner.** Where no registered adapter has one, the run command refuses and names the adapters. The calling command starts no agent and says why. Where more than one has one, it refuses too, until a record says how a project names its harness.
- **What stays with the caller:** which agents start, their briefs, the commit, the bounds of DEC-056 point 4, and what becomes of the run's files.

### 2. What a caller passes, what it gets back, and when a run is refused

**The caller passes:**
- the agent, by name, and the brief
- for a confined run, the commit, the command whose runs the rules name (point 5), and the folder the run's files go to
- for the review command's run, the folder it runs in (point 10)
- a wall-clock limit, and an effort level where it sets one

**The caller gets back:**
- how the run ended: finished with the harness's exit, could not start, stopped at its limit, or refused, with the reason
- the agent's output, and the calls the harness refused where it reports them
- for a confined run, the run's files as untrusted data, the check's verdict (point 7), and each command the run ran outside the sandbox (point 6)

**A run is refused before it starts when:**
- the marker of a run is set (point 8), or no runner is found, or more than one (point 1)
- the harness's command line or the agent is not found
- for a confined run, the harness cannot confine it:
  - the harness's version lies outside the range the adapter's author tested the confined form on. Only that author widens the range, after the probe passes on a newer harness (COR-047 point 2).
  - the platform offers no sandbox the harness can use, or the harness cannot run with only the run's settings (point 3)
  - the agent's definition carries a field outside the allowed set, or a deny that binds the run cannot be held natively (point 3)
  - the run's settings fail the harness's settings schema (point 3)
  - the clone, or the shell's temp folder inside the workspace, cannot be made (points 6 and 7)

Each refusal names its cause. A start report that does not match the run's settings ends the run at once (point 9). At the wall-clock limit, the runner ends the harness and every process it started.

### 3. A confined run loads only its own settings and a checked definition

- **No settings file of the person's or the project's.** The run loads its own settings and the admin-managed ones, which nothing drops. `--restricted` or `--setting-sources` does this today, and the probe picks which (point 12). So the project's hooks and MCP servers, which run with full access outside the sandbox, never start in a run.
- **The denies of those files come along.** The run's settings carry the deny rules of each settings file the run leaves out. They also carry each deny the model holds for the run's agent or for every agent, the baseline's guardrails among them. A deny the adapter cannot hold natively refuses the run.
- **Held in the harness's native rules, never in a hook.** Native rules fail closed, and the hook fails open (ADR-002 point 3). COR-028 point 2 puts a deny that must hold on such a mechanism.
- **Read at the pinned commit.** The run's rules, the project's grants, the catalog, the agent's definition, the candidate exclusions and the runner itself are read from the clone. So no unmerged change shapes a run nobody watches, as DEC-056 point 3 keeps for the agent.
- **A checked agent definition.** The runner always passes the definition itself, with `--agents`, built from the agent's file at the pinned commit.
  - It keeps only what a run needs: the description, the instructions, the tool list and the model.
  - A definition with any other field, such as hooks, MCP servers, a permission mode, memory, skills or isolation, is refused, not trimmed. So the agent's owner sees why.
  - The definition gets a name unique to the run. So no agent of the person's, the project's or the organisation's answers to it.
- **The settings are out of the run's reach.** They are passed inline, or from a file in no folder the run writes. The adapter first checks them against the harness's settings schema, since the harness skips a value it rejects.
- **No memory.** The run's settings turn the harness's own memory off. So a run leaves no note that loads into the person's later sessions.

### 4. No flag, setting, definition or variable bypasses the run's rules

DEC-056 point 5 rules out a flag that bypasses the permission rules. Here, anything that approves a call no rule of the run allows bypasses them. So does anything that loads configuration other than the run's own.
- **A closed set of flags.** The runner passes only flags from a closed set, which the adapter's README lists. No member of the set may approve a call, or load configuration other than the run's own.
- **Never passed, to any run:**
  - `--dangerously-skip-permissions` and `--allow-dangerously-skip-permissions`
  - `--permission-mode bypassPermissions`
  - `--permission-mode auto`, whose classifier approves calls in a person's place
  - `--permission-mode acceptEdits`, which approves edits and filesystem commands no rule names
  - `--permission-prompt-tool`, which answers prompts in a person's place
- **Never passed to a confined run:** `--allowedTools`, since the run's allows live in its settings alone, and `--add-dir`, which opens a folder to writes.
- **Never in a confined run's settings:** sandbox auto-approval, the retry outside the sandbox, weaker network isolation, or a mode other than `dontAsk`. Auto-approval is on by default, so the settings turn it off by name.
- **Never in its definition:** any field point 3 refuses.
- **Never in its environment.** The runner starts the harness from an environment that holds only what the harness and the run's commands need. No variable that changes the harness's permissions, its sandbox or the folder it reads its configuration from is on that list. The harness's own scrub keeps credential variables from every process it starts.
- **A call no rule allows is refused, not asked.** A confined run starts in `dontAsk`, with `--permission-prompts none`, and the mode is always passed. A run nobody watches cannot answer a prompt anyway.
- **The run's tools:** reading, searching, writing new files and the shell. No tool starts an agent, edits an existing file or reaches the web. No MCP server connects, and no skill or custom command runs, since a skill may approve tools for itself.

### 5. In the model, a run's rules are denies

DEC-056 point 5 reads the run's rules as denies, and this record keeps that reading. COR-028 then needs no change.
- **What a rule reads,** in the model's terms (COR-028 point 1):
  - Subject: every agent. The drift command starts agents that other capabilities ship, so the capability cannot name them. The grant list decides which start (DEC-056 point 2).
  - Privilege: a privilege of the catalog.
  - Scope: the runs a named command starts through the runner. A scope may say when a rule applies.
  - Effect: deny.
- **One deny covers what a run may not do.** Its privilege is every call that none of DEC-056 point 5's allowed privileges recognises. The capability defines that privilege ([ADR-021](ADR-021-capability-contributed-privilege-definitions.md)), and the catalog gains the form it needs. The other denies are the floor DEC-056 point 5 lists.
- **That holds a run to the allowed list.** A deny prevails over every allow, the shared baseline's included (COR-028 point 1). So whatever else allows, a run may do only what the first deny leaves open.
- **The native allow list is how the harness holds that deny.** No list of denies can name every call. So the adapter realises the first deny the other way round: the run's settings allow only what it leaves open, and `dontAsk` refuses the rest. The floor's denies become native deny rules.
- **Declared in a file of their own.** The capability declares a run's rules, and the privileges they name, beside its permission fragment ([ADR-016](ADR-016-capability-contributed-intent-grants.md)). No session's model composes that file. An older permission core would read a run's scope as a folder pattern, and deny ordinary calls in every session.
- **Shown, not hidden.** The permissions overview and explanation show a run's rules and the capability that contributed them (ADR-016 point 7).
- **Realised for that run only.** The adapter writes them into the run's own settings, never into a settings file of the project's.

### 6. The workspace is the only folder the shell writes

- **The harness starts in the run's workspace.** A sandboxed command writes its working folder, so the shell writes the workspace and nothing else of the clone. Rules of their own let the run read the clone. `--add-dir` would open the clone to writes, so it is never passed.
- **One session per run.** Each run is a harness session of its own, so its sandbox is that session's. A run starts no subagent, so confinement still never differs between the agents of one session (ADR-004 point 5).
- **On, and failing closed.** The run's settings turn the sandbox on, and stop the harness at start when the sandbox cannot start (ADR-004 point 4). The runner checks the platform first, so a known gap is a refusal.
- **No retry outside it.** The run's settings turn off the retry that reruns a failed command outside the sandbox, as the autonomy posture does ([ADR-028](ADR-028-seal-unsandboxed-escape-under-autonomy-posture.md)). Set there, it also stops the repository's settings from loosening the sandbox.
- **The temp folder.** The harness's temp folder for the shell lies in a folder of the workspace that is never copied back. Where the harness cannot place it there, the run is refused.
- **Network:** no host is allowed, and `dontAsk` refuses each host the shell asks for.
- **Reads.** The shell reads the system's own folders, the clone, and the installed tool the run's `pkit` runs. It reads none of the person's other files. The harness's block on reads outside the working folder is on, and rules of their own open the clone and the tool.
- **Credentials.** The credential files the project's sandbox settings deny are denied to the shell and to the file tools ([ADR-008](ADR-008-confinement-allowances.md)). No file-tool read rule reaches past the clone.
- **What runs inside, and what cannot:**
  - The backbone's reading commands run inside, with no `uv`. The run command puts a `pkit` first on the run's path, outside every folder the run writes. It runs the backbone's own code under its own interpreter, as the `pkit` of [ADR-065](ADR-065-upgrade-runs-the-transition.md) point 14 does for a migration.
  - A command whose work starts `uv`, such as a component's query script, writes a cache outside the clone. On macOS, `uv` cannot run inside the sandbox at all.
  - On Linux, the sandbox can host `uv` once its cache is writable, so ADR-027 requires no exclusion there (its condition 2). DEC-056 point 5 allows no second folder to write. So such a command fails inside the sandbox, and the runner reports it.
  - On macOS, such a command runs under the platform's required exclusion, below.
- **That `pkit` reads the clone, never the workspace.** Every call of it starts from the clone's root, and points git at the clone's own git folder. It starts `uv` with no configuration file, and with only the `uv` settings the runner sets. The run's rules allow it only as a bare call by name, so no call sets its own variables or reaches another `pkit`. So nothing the shell writes in the workspace becomes code or configuration that an excluded command runs.
- **The macOS exclusion.** A run's settings exclude the allowed commands whose work starts `uv`, while ADR-027's test shows the installed `uv` still needs it. No run excludes `gh`, since no rule of a run allows it. ADR-027's seven conditions, in a run:
  - Conditions 1 and 2 hold. The need is tested for each run, and only a required command is excluded.
  - Conditions 4 and 6 hold. The exclusion lives in the run's settings alone, and nothing outlives the run to heal.
  - Condition 3 has no banner or status line in a run. The run's result names each excluded command, and the calling command shows it, as a widening must be shown (ADR-008 point 4).
  - Condition 5 cannot use the project's sandbox writer (ADR-008 point 2), since the run's settings belong to no file of the project's. The runner writes them once, for that run.
  - Condition 7 still holds, since the sandbox still cannot host `uv`. But the threat is new: input nobody vetted, with nobody watching. Accepting this record brings the widening to every adopter on macOS, with no question of its own. A person's grant of a fixer does not name it (DEC-056 point 2), so the person learns of it from each run's result (condition 3).

### 7. The run's clone, and the check after the run

- **A clone that shares nothing.** The run command makes the run's working copy as a clone at the caller's commit. The clone shares no object file with the person's repository, by link or by reference. It lies outside every working tree, in a folder of the backbone's that only the person's account writes. It never lies in the harness's shared temp folder.
- **Where it cannot.** Inside a sandboxed session, the run command may be unable to write such a folder. The run is then refused.
- **Provisioned, then given a workspace.** The clone is provisioned as the project's checks are (DEC-056 point 3). Then the run command makes the run's workspace itself, and refuses when the commit holds anything at that path. With no hook in the run, it keeps ADR-060's guards itself ([ADR-060](ADR-060-path-scoped-workspace-allow.md) points 1 and 2). The workspace is no symbolic link, and nothing in it has more than one link.
- **Before the run,** it records the clone's references and its ignored files.
- **After the run, and after a failed start, it checks** (DEC-056 points 4 and 5):
  - nothing changed in the clone outside the workspace
  - no reference of the clone moved
  - no ignored file appeared outside the workspace
- **Git is read as hostile.** The check runs git with the clone's own configuration ignored. Any error of git's is a breach, so the check fails closed.
- **A breach** comes back with what changed, and the caller sets the run's files aside.
- **A check, not a boundary.** It finds a breach after it happened, and only inside the clone. There, only an excluded command can write outside the workspace. Outside the clone, an excluded command's writes go unseen (point 11).
- **Then the files, then the removal.** The run command copies the run's files from the workspace to the folder the caller named. It copies regular files only, follows no symbolic link, refuses a file with more than one link, and bounds the total size. It refuses any entry named `.git`, and never copies the temp folder. Then it removes the clone, and each confined run first removes any clone a killed run left behind.

### 8. A run is a leaf

DEC-056 point 5 makes a fixer start no other agent. A run could start one in two ways, and each is closed.
- **Through the harness.** No tool that starts an agent is in the run's tools, and no skill runs (point 4).
- **Through a command that starts agents.** The run's rules refuse it (point 5). A marker is the second lock:
  - The backbone's run command sets `PKIT_AGENT_RUN` in the harness's environment for every run it starts. Every process the run starts inherits it.
  - The run command refuses when the marker is set at all, even empty, before it does anything else. The runner refuses too, so no route around the run command starts an agent from a run.
  - Nothing else sets or unsets the marker, as ADR-065 point 14 keeps its migration marker.

### 9. What the permission layer sees

- **In the session that runs the command,** the hook sees one shell call, the command itself. It judges that call for the session's subject.
- **Inside a confined run, the hook sees nothing.** The run loads no project settings, so the hook is not registered there.
- **The runner reads the realised state back** (COR-028 point 2). The harness reports, at start, its mode, its tools, its MCP servers, its plugins, any hook it ran, and whether its sandbox started. Any of these that does not match the run's settings ends the run at once, and its files are set aside.
- **After the run,** the harness's report of the calls it refused, and the check of point 7, show what the run tried and what it changed.
- **Inside the review command's runs,** the hook runs as in the person's session. Which subject it judges there is not known (point 11).

### 10. What the review command's runs get

Moving the review command onto the runner keeps what its reviewers may do. Its runs take the runner's unconfined form:
- They run in the person's checkout, under the person's and the project's settings.
- They start in the mode those settings or the harness choose.
- The runner passes `-p`, `--agent`, and `--effort` where one is set.

**What changes around them:**
- A project whose registered adapters have no runner loses its reviews, as a project without `claude` loses them today.
- The wall-clock limit now ends the harness and every process it started.
- The review command needs the backbone that ships the run command, so project-management's changeset declares that need (PRJ-002).
- A project with another harness answers through its own adapter's runner, not by editing the review command's script.
- Once the marker is built, a reviewer cannot start agents through the runner.

**Not decided here:** whether the review command's runs are confined. A confined review would run in a clone at the pull request's head, under rules for reading it. The record that decides it first weighs a mode that cannot bypass, for these runs too.

### 11. What stays open

Each item says what holds the intent and what is left (COR-028 point 3).
- **Network egress.** The run's shell reaches no host. What is left:
  - The sandbox checks the host a client names, so it is no control on data leaving (ADR-004).
  - An excluded command has the person's full network access.
  - The harness's own connection to its model carries what the run reads. So what the run may read, it may send.
  - A person closes this outside the harness, by running their session, and so each run, in a container or a virtual machine.
- **Commands that start `uv`.** On macOS they run outside the sandbox, held by the run's rules alone (point 6). What is left:
  - They read their code and configuration from the clone, with their root pinned (point 6). But a steered agent chooses their arguments.
  - Their writes outside the clone, and their network access, go unseen.
  - On Linux they fail, so a fixer there gets no query that starts through `uv`.
  - A `uv` release the sandbox can host closes the macOS part (ADR-014 point 4).
- **The harness's read-only commands.** They run with no rule under `dontAsk`. They only read, but the set is the harness's, and it changes between releases.
- **What the hook sees.** The hook sees the command, not each agent it starts (DEC-056 point 5).
  - In a confined run, the start report and the check stand in for it (point 9).
  - In the review command's runs, `--agent` sets the session's agent without changing the file the hook reads. So the hook may judge a reviewer as the project's default agent, or as `operator`.
  - No grant for one agent counts in those runs until the probe shows which subject the hook judges.
- **The words a proposal carries.** Each command is built from a proposal's fields (DEC-056 point 6). Its diff and its answers' words can still carry a contributor's steering. So the person reads every word before accepting it.
- **The person's instructions.** The harness reads every `CLAUDE.md` above the folder it starts in, and the person's own. No file of the person's checkout reaches a run, but the person's own instructions may.
- **An organisation's managed settings.** They reach every run, and nothing drops them. They may allow more, run hooks of their own, or set the run's rules aside. The runner cannot always read them, so the organisation closes this.
- **The review command's runs** are unconfined (point 10). A reviewer runs in the person's checkout, may write there, and may start in a mode that approves calls no rule allows. Nothing checks its run.

### 12. The probe, and the trial

Before the confined form is built, a probe of the harness confirms the facts below. The live trial of the drift command's fixers then confirms them end to end. Until the probe runs, each rests on the harness's documentation.
- With only the run's settings and the passed definition, the run's agent starts and the harness signs in.
- The start report gives the mode, the tools, the MCP servers, the plugins and the hooks, and whether the sandbox started.
- A call outside the run's settings is refused, with no prompt, and the run goes on.
- The shell and the file tools write only the workspace, and the shell's temp folder lies there. A working folder below the clone's root opens neither the clone's git folder nor the per-user temp folder to writes.
- A call of the run's `pkit` from the workspace finds the clone as its root, and reads no git or `uv` configuration the workspace holds.
- With auto-approval off, a sandboxed command outside the run's allows is refused.
- A sandbox that cannot start stops the harness at start.
- The shell reads the clone, the system's folders and the installed tool, and none of the person's other files. The allowed commands still run under that block.
- On macOS, the exclusion lets the allowed commands that start `uv` run with the retry off (ADR-028 point 3).
- A run started from inside a sandboxed session starts its own sandbox and reaches its model.
- The marker reaches the run's shell, and the credential variables do not.
- In a review command's run, the hook judges a subject the probe names.
- A harness release that makes bare mode the default for `-p`, as announced, falls outside the tested range. Bare mode signs in with an API key only.

A fact the probe or the trial disproves refines or supersedes this record, as the change to the decision requires.

### 13. The harness requirement

DEC-056's Implications name one requirement on the harness ([COR-047](../../../.pkit/decisions/core/COR-047-harness-requirement-declaration.md)). This record words it in terms any harness could meet:

> A process can start an agent with nobody attending. For that one run, the agent is confined to rules and a folder the process sets. A call those rules do not allow is refused, not asked. After the run, the process can read the run's files and its outcome.

- **Observation point:** outside a session, by starting a probe run.
- **Evidence:** DEC-056 point 5, a design dependency (COR-047 point 9). It is no transient defect, so it names no retirement condition.
- **Declared with the drift command.** That change adds it to the requirement set. The adapters' support declarations are not shipped yet (the adapters README, "Harness requirements"). Until they are, the tested version range (point 2) bounds where the Claude Code adapter starts a confined run.

## Rationale

**Why the adapter, through its registered commands.** A harness's command line belongs in its adapter, as every other harness tie does (COR-005). A capability that calls `claude` ties its command to one harness, as the review command does today. The backbone already has one lookup and one bounded run for registered commands (ADR-057 point 5), so the runner joins them.

**Why a confined run loads no settings file and no unchecked definition.** The run's allows then hold in native rules, which fail closed, since settings lists only add to each other. The project's hooks and MCP servers, and the hooks a definition can carry, run with full access outside the sandbox. Loading none of them means a merged change cannot add one that runs unwatched.

**Why the run's rules are denies.** DEC-056 point 5 places them in the model that way, and COR-028 point 1 already lets a deny prevail over every allow. So a run is held to its list with no change to the model. The native allow list is how a harness holds a deny that names everything else.

**Why `auto`, `acceptEdits` and sandbox auto-approval count as bypasses.** Each approves a call no rule of the run allows: by a classifier, for edits, or for every sandboxed command. Any of them would turn the run's list into a suggestion.

**Why the harness starts in the workspace.** The shell's writes are bounded by its working folder, not by the path rules the file tools obey. Started at the clone's root, a steered shell could rewrite a script that an excluded command then runs with full access. The run's `pkit` pins its root to the clone, so the folder the shell does write is never read as configuration.

**Why a clone that shares nothing, outside every working tree.** A linked worktree shares the repository's git folder, which the sandbox opens to writes. Shared references would also hide the run's moves among the person's own commits. A clone inside a checkout would read that checkout's `CLAUDE.md`, which may hold unmerged changes.

**Why a command that starts `uv` fails on Linux, rather than gaining a cache.** A writable cache is a second folder, which DEC-056 point 5 rules out. The person's later `uv` runs, outside any sandbox, would also execute what a steered run wrote there.

**Why the backbone owns the clone and the check.** The check is harness-neutral, so it is not the adapter's. Its before-state is the clone's state when made, so the part that makes the clone records it.

**Why a marker beside the rules.** The rules name commands, and a new command that starts agents could be missed. The marker refuses in the one place every such command passes, as ADR-065 point 14's marker does for a migration.

**Why the review command stays as it is.** The move is a move. Changing what reviewers may do inside it would hide a decision.

### Alternatives considered

- **The runner in project-management's library.** Rejected. It keeps the harness tie in a capability, and the next capability that starts agents would copy it.
- **The runner in the backbone, calling `claude` itself.** Rejected. The backbone would carry one harness's command line (COR-005).
- **A primitive found by file name, beside the deploy primitives.** Rejected. Their contract is idempotent and driven by the lifecycle, and a run is neither. Registered commands already have one lookup and one run (ADR-057 point 5).
- **Run rules with an allow effect, and a refinement of COR-028.** Not taken. DEC-056 reads them as denies, and denies need no change to the model.
- **Run rules in the session's grants file.** Rejected. An older permission core would misread them, and deny ordinary calls in every session.
- **Keep the project's settings files, and add the run's denies.** Rejected. The project's hooks and MCP servers would run unwatched with full access, and a hook's allow would approve calls the run's list does not name.
- **The harness started at the clone's root.** Rejected. The shell could then change code an excluded command runs.
- **Refusing a run whose workspace holds a git or `uv` configuration file.** Rejected. It is a list over an open-ended set of files, and pinning the root closes the set.
- **Trimming a definition's extra fields.** Rejected. Refusing shows the agent's owner what a run would not accept.
- **A writable `uv` cache on Linux.** Rejected, for the reasons above.
- **`--bare`.** Rejected. It signs in with an API key only.
- **`auto` with `--permission-prompts none`,** the documentation's own example of an unattended run. Rejected. A classifier approves calls no rule allows.
- **The run's rules in the permission hook.** Rejected. The hook fails open (ADR-002), so a broken hook would leave a run unconfined while it looked confined.
- **A container or a virtual machine for each run.** Not taken now. It would close the network and macOS gaps, but the methodology ships no such mechanism.
- **A mode that cannot bypass for the review command's runs, now.** Not taken. The move keeps what reviewers do, and the record on confining them weighs it first.

## Implications

- **The review command's move** (#1742) builds the backbone's run command, the adapter's runner in its unconfined form, and the review command's call to it. Point 10 lists what changes around it. The backbone and the adapter each gain something an adopter can see, so each change declares it (PRJ-002).
- **The drift command's change builds the rest:** the probe first, then the confined form, the clone and its check, the marker, and the run's rules in project-management's file for them.
- **The catalog gains a form:** a privilege that is every call none of a set of privileges recognises. The change judges whether that moves the catalog schema's version ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)).
- **The command runner gains a policy for an agent run,** as ADR-057 point 5 gives each kind of command its own.
- **Refinements of accepted records.** When this record is accepted, each gains a pointer, "(refinement per ADR-066)":
  - ADR-060 point 6: in a run, the Claude Code adapter emits a path rule for the workspace, since the harness approves no write there by itself.
  - ADR-027: the runner, and not only the autonomy setup, applies the required exclusion, to a run, as point 6 walks its conditions.
  - ADR-008 point 4: that widening reaches a run with no person's gesture. It lands in no file of the project's, and the run's result reports it.
- **Docs:**
  - the adapters README gains a section on the runner's contract: a registered command, run once for each run, not idempotent, and refusing inside a run
  - the Claude Code adapter's README lists the closed set of flags and the run's settings
  - the adapter's enforcement declaration names what holds a run, and what stays open (COR-028 point 3)
  - the permissions README, "Default-agent subject resolution", says that `--agent` sets a session's agent without changing the file the hook reads
  - the CLI reference documents the backbone's run command
- **A follow-up record** decides whether the review command's runs are confined (point 10).
- **No migration.** Every change adds.
- **Supersedes nothing.** It changes no decision of DEC-056 or COR-028.
- **Stands on these accepted records:**
  - the drift fixers (DEC-056)
  - the permission model, harness requirements and pattern extraction (COR-028, COR-047 and COR-007)
  - adapters as a harness's translation (COR-005 and COR-013), and the rules for migrations and versions (COR-010 and PRJ-002)
  - the permission realiser and its shared core (ADR-002 and ADR-003), intent and confinement (ADR-004), and confinement allowances (ADR-008)
  - the macOS stance and its required exclusion (ADR-014 and ADR-027), and the sealed retry (ADR-028)
  - capability grants and privileges (ADR-016 and ADR-021), registered commands (ADR-057), the agent workspace (ADR-060), and the migration runner's `pkit` and marker (ADR-065)
