---
id: ADR-090
title: pkit fetches its own releases over public HTTPS, and one script installs a fresh clone's version
status: accepted
date: 2026-11-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** pkit fetches its own releases from one URL compiled into it: the lookup of the latest release, the install of a newer one, the router's run of a project's pinned version and the raise of a pin. That URL is the repository's public HTTPS address, which needs no SSH key and no token. It is the install form the project record [PRJ-015](../../../.pkit/decisions/project/PRJ-015-https-install-form.md) makes canonical, so the tool's fetches work wherever its install worked. None of these fetches waits at a terminal for a credential.

A fresh clone on a machine where nobody answers a prompt, such as a pipeline's runner, a container or a hosted agent's machine, installs its project's pkit with a script the project already carries, the *install script*. It installs the version the project pins, or else the version its manifest records, and never `latest`. It installs only where it finds no pkit installed, so it leaves alone any tool it finds, which other projects on the machine may run. It then runs the project's own `pkit`, and succeeds only where that reports the project's version. Its install is the same `uv tool install`, from the same address, that a person runs, so it adds no installer.

## Context

pkit fetches its own releases from the distribution URL compiled into it ([ADR-063](ADR-063-upgrade-updates-the-tool.md) point 7), in four places, each with a path for a fetch that fails:

- `pkit upgrade` looks up the latest release. Where the lookup fails, it warns and goes on (ADR-063 point 1).
- When the tool is behind it, `pkit upgrade` installs that release. Where the install fails, it prints the command (ADR-063 points 2 and 3).
- The router runs a project's pinned version through `uvx`. Where the pin cannot be fetched, it runs the installed pkit and says so ([ADR-039](ADR-039-pkit-entry-point-router.md) route 2 and D2).
- A pin is raised through the router's bypass, under the target's code. Where the release source cannot be reached, the pin stays as it was ([ADR-049](ADR-049-per-project-version-pin.md) point 5).

The compiled URL is the SSH form, the one the distribution record recommends ([PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)). So each of those fetches needs an SSH key on the machine.

A machine with nobody at the keyboard, where no person answers a prompt, often has no key by design: a pipeline's runner, a container, a hosted agent's machine whose git reaches GitHub over HTTPS alone. The working note behind #3002 met it on a hosted agent platform whose machines hold no SSH key (the scratchpad note `2026-11-09-pkit-in-dam-containers`, its gap 4). There the lookup fails, a pinned project falls back to the installed pkit on every command whose pin differs from it, and no pin can be raised. The remedy the fallback names sends the operator to the HTTPS URL by hand ([ADR-065](ADR-065-upgrade-runs-the-transition.md) point 8).

The repository is public, so a fetch over HTTPS needs no credential. PRJ-015, accepted with this record, makes the HTTPS form the canonical install, and partly supersedes PRJ-004 on the form. This record decides the tool's side: the URL it compiles, how its fetches fail, and how a fresh clone gets its project's version.

Installing raises a second gap. The install the CLI reference recommends names the tag `latest`, which serves only a project already at the latest release. Elsewhere sync's guard stops the project's commands under another version (ADR-065 point 7), or the router fetches the pin on every command. A fresh clone needs its project's own version. And on a machine other projects share, an install made with nobody watching must not move the tool they run: that is why `pkit upgrade` installs only at a terminal (ADR-063 point 3). The in-tree dispatcher, the `pkit` that sits in each project's CLI area ([PRJ-001](../../../.pkit/decisions/project/PRJ-001-cli-binary-name.md)), runs before any pkit is installed, but in a project's clone it only names that install of `latest`.

A fresh clone with nobody at the keyboard may also be shallow. The commands that need history already detect a shallow clone, and name `git fetch --unshallow`.

## Decision

**pkit fetches every release of itself from one compiled URL, the canonical HTTPS form, and no such fetch waits at a terminal for a credential. A script each project carries in its CLI area installs a fresh clone's pkit with nobody at the keyboard: the version the project pins, or else the version it records, only where it finds no pkit installed, through `uv tool install` from that URL. It succeeds only where the project's own `pkit` then runs that version.**

### 1. The tool fetches its releases from one compiled URL, the canonical HTTPS form

The distribution URL compiled into the tool is the canonical install URL, the repository's public HTTPS URL (PRJ-015 point 1). Every fetch the tool makes of its own releases uses it.

It is one value, kept once in the tool's code. Every fetch reads it from there, and so does every line the tool prints that names where pkit comes from. uv takes it with its `git+` prefix and git without, and both spellings derive from that one value.

Whatever form installed the tool, it fetches its later releases from the compiled URL, so its next tool step installs from the same repository and tag, over HTTPS. Each fetch goes through the machine's git and uv, so what the machine configures in them to send these fetches over SSH reaches the tool's fetches as it reaches a person's install (PRJ-015 point 2). A fork compiles its own URL (ADR-063 point 7), and puts the same URL in the install script (point 7).

### 2. No fetch of the tool's releases waits at a terminal

Over the public URL the server asks for no credential. Where a server does ask, as it does for a private repository or for one that does not exist, the fetch fails at once rather than wait at a terminal. It then takes the failure path its own record gives it, as the Context lists.

What the machine's own git configures is the choice of whoever runs the machine, and pkit neither adds such a setting nor turns one off:

- **A credential helper or an askpass program** may answer, or ask in its own way.
- **A URL rewrite** may send the fetch over SSH, whose passphrase and host-key prompts git's terminal switch does not reach. Where no terminal is attached, ssh fails rather than wait for an answer.

A *probe* is a run of a release's `pkit --version` through `uvx`, from the compiled URL, which shows that the release can be fetched before pkit runs it. The router already probes a pin before it runs the pin, which is how it degrades before the command starts (ADR-039 D2). The raise probes its target the same way before it runs the target.

- **Where pkit switches the prompt off:** in each process it starts only to fetch a release or to probe one. Each runs with git's terminal prompt off (`GIT_TERMINAL_PROMPT=0`). The install script's install and its check (point 5) run the same way.
- **Where it does not:** in a process that runs a release's code for the command the operator asked for, as the router's run of a pin and the raise's run of its target do. A switch set there would reach every git command that command runs for the project, so pkit sets none. Each such run follows a probe that fetched the same release, from the same URL, with the switch off. A URL that asks for a credential has failed that probe, and the run never starts. The run's own fetch is uv's, and uv runs its git fetches with the terminal prompt off.

### 3. An install script in the CLI area installs a fresh clone's pkit

The *install script* is one POSIX `sh` script, `.pkit/cli/install-pkit.sh`, in the CLI area that sync copies into each project. So every clone of a project that commits its `.pkit/` carries it, at the project's recorded release. Pipelines and *hosts*, the platforms that run machines such as containers and hosted agents' machines, name its path. So the path is part of its interface, and moving it is a change adopters can see. It runs as `sh .pkit/cli/install-pkit.sh`, and that form is its interface: it needs no executable bit on the file, and none is promised.

- **When it runs:** only when invoked: by a person, a pipeline's step, a host's setup command or an agent. No hook runs it, and no pkit command does.
- **Whose consent:** whoever invokes it gives it. A person's or a pipeline author's invocation is their consent. An agent runs it as it runs any command, where the permission layer lets the command through, and that grant stands for the consent a terminal stands for in the upgrade. The methodology adds no permission rule for it. Where a sandbox keeps writes out of uv's folders, the install fails, and the script says so.
- **Where it acts:** on the project it sits in, found from its own place in the tree, not from the working directory.
- **What it needs:** `uv`, which pkit requires anyway (PRJ-004), and `git`. Where `uv` is missing, it says so, installs nothing and fails (point 5).
- **Its result:** it exits zero only where its check finds that the project's commands run the project's version (point 5). Otherwise it gives the reason.
  - **The verdict holds in the script's own environment:** its `PATH`, the routing variables it inherits, such as `PKIT_NO_ROUTE`, and the project it sits in. A later step whose environment differs, such as a pipeline's next step or an agent's shell after a host's setup command, may find another `pkit` or none. A host's setup command may run in a shell whose `PATH` lacks uv's command folder, so whoever writes that command puts the folder on the `PATH`, and exports it, before running the script.
  - **Success names the version, not a whole state.** It says which version the project's commands run. Sync's guard still stops them over an unfinished upgrade or raise, and names the remedy (ADR-065 points 7 and 8).
- **In the methodology's source repository,** where every adopter's copy comes from, it makes no exception. The router runs the checkout's own code there, whatever pkit is installed (ADR-039 route 1, [ADR-059](ADR-059-methodology-source-repository.md)). So what the script installs does not choose the code that runs, and its check reports the checkout's version, which the code reads from `.pkit/VERSION`. The release writes that file and the manifest's `backbone_version` together ([PRJ-007](../../../.pkit/decisions/project/PRJ-007-release-maintains-self-host-manifest.md)), so the two agree there. A developer's setup there is the contributing guide's, not the script's.

### 4. It installs the project's version, never `latest`

The version it installs is the project's pin (ADR-049 point 1). The script reads the pin as the router reads it: the whole file, with the whitespace around it stripped, a carriage return included, and an empty file as no pin. Where the project pins nothing, the version is the backbone version the project's manifest records, `backbone_version`. The script reads that key from its own line. That is sound because the key stays a top-level scalar in every manifest format, written by an in-place edit of its own line (ADR-065 point 3). The script never installs `latest`, and never prints its install.

- **A pin the router cannot route,** anything but a bare release version `MAJOR.MINOR.PATCH`, is refused. That includes `v1.2.3`: `pkit pin` strips a leading `v` (ADR-049 point 3), but the router compares the file's text as it stands, and would never match it. The script installs nothing, names the pin to mend, and does not fall back to the recorded version.
- **A recorded version that is missing, or is no version,** where nothing is pinned, is refused too. The script installs nothing, says what the manifest lacks, and names the CLI reference's section on installing pkit, for a person to choose a version.
- **An incomplete transition:** `backbone_version` names the transition's target, and the target's `pkit upgrade` finishes it (ADR-065 point 8). So the script installs that version, as it would any other.

### 5. It never replaces a pkit it finds installed, and checks the pkit the commands run

It installs only where, when it looks, it finds no pkit installed. A pkit counts as installed where uv lists it among its tools, or where the `PATH` finds a `pkit` other than the project's own dispatcher (point 8).

A refusal (point 4), a missing `uv` (point 3) or a failed install ends the run, non-zero, before the check, and says why. Otherwise, whether it installed or found a pkit installed, it checks the pkit the project's commands run: the `pkit` the `PATH` finds, run from the project's root, with git's terminal prompt off, and asked for its version. Its router routes that run as it routes any command. So the check fetches the pin wherever the router would, and reports the version the project's commands run.

- **It reports the project's version:** the script succeeds. That holds where the script installed that version, where it was installed already, and where another version's router runs the project's pin (ADR-039 route 2).
- **The `PATH` finds no `pkit`:** the script fails, and prints the folder uv put the command in (point 6).
- **The `PATH` finds the project's own dispatcher first,** in a project's clone: the script fails without running it. It says that the dispatcher shadows the installed pkit, and that uv's folder goes before it on the `PATH`. Run, the dispatcher would only name this script again (point 8). In the methodology's source repository the dispatcher runs the checkout's code, so the check runs it as it runs any `pkit`.
- **It reports another version, or none:** the script fails, and leaves any installed pkit as it is. The message names the pkit that ran, and how to run the project's version without moving the tool, through `uvx` from the script's own URL. It also names the forced install, for whoever owns the machine to run on purpose.

The script takes no lock. Another install can land between the script's look and its own install: a second run of the script for a project at another version, a person's own install, or `pkit upgrade`. The script's install may then replace it, and of two installs the later stands. A check made before the other install landed may not hold by the time the project's commands run. Even then the router runs a pinned project's pin wherever it can fetch it, and sync's guard stops an unpinned project's commands at another version (ADR-065 point 7). A machine that runs such installs at once gives each its own uv tool folder, or pins its projects.

So the script never replaces a pkit it found installed. That replacement, of the tool every project on the machine shares, with nobody watching, is the move ADR-063 point 3 keeps from automation.

### 6. It knows no host, and leaves the clone as it was

- **No host's folders.** The script names no folder of any host. uv chooses where the command goes, by uv's own configuration, which a host sets. Where the `PATH` does not find the installed `pkit`, the script prints the folder uv put it in, and says to add that folder to the `PATH`. It changes neither the `PATH` nor any shell profile.
- **No history.** It fetches no history and changes no remote. A shallow clone stays shallow, and each command that needs history names `git fetch --unshallow` when it meets one.
- **Nothing else.** It installs pkit alone: not `uv`, and no capability. It runs no pkit command but the version check (point 5).

### 7. Its install is the sanctioned one

The script's install is `uv tool install` from the distribution URL at the release tag `v<version>`, run with git's terminal prompt off (point 2). That is the frontend, the channel and the tag form PRJ-004 sanctions, at the URL PRJ-015 makes canonical. So the script is no installer of its own (PRJ-015 point 4): it chooses the version and checks the machine, and uv installs.

The script holds its own copy of the URL, since it runs before any pkit exists to ask. A test holds that copy equal to the tool's compiled URL, so a fork's script carries the fork's URL.

### 8. The in-tree dispatcher sends a project's clone to the script

The in-tree dispatcher, the `pkit` that sits in each project's CLI area (PRJ-001), runs before any pkit is installed. In a project's clone, where it names how to install pkit, it names the install script, not an install of `latest`. It installs nothing itself.

## Rationale

**Why the tool fetches over the canonical form.** The tool's fetches reach the machines its install reached only if they use the URL the install used. A tool installed over HTTPS on a machine with no key, fetching over SSH, would fail every lookup, every pin fetch and every raise. With the compiled URL equal to the canonical form, the machines where the canonical install works are the machines where the tool's fetches work. A machine that reaches GitHub over SSH alone loses both together, and its own configuration of git and uv, which PRJ-015 point 2 leaves to it, restores both together.

**Why one URL, not a fallback.** One transport leaves one path to reason about, in the tool, in its remedies and in its tests. A fallback from SSH to HTTPS would double each failure, since an offline fetch fails on both. An SSH attempt can also stop on a passphrase or a host key, which git's terminal switch does not reach. SSH's batch mode would stop those too, at the cost of one more setting carried into every fetch.

**Why no prompt at a terminal.** A prompt with nobody to answer waits until a time limit, or for good. With the switch off, a fetch that needs a credential fails at once, onto paths the records already give. A person at a terminal whose fork asks for a credential gets the printed command, and running it by hand asks them, as git always does. A helper or a rewrite the machine configures is left alone, since its owner chose it, and how it asks.

**Why the switch is set on fetches only, with a probe before each run.** A process pkit starts only to fetch has nothing else to reach, so the switch costs nothing there, and the guarantee is pkit's own rather than uv's. The routed process is the operator's command, not a fetch. A switch set there would follow every git command that command runs for the project, a push among them, and take a prompt from a person who relies on it. The probe before the run fetches the same release under the switch, so a URL that asks for a credential stops at the probe. uv's own switch covers the run's fetch beyond that. The router's probe exists already. The raise's costs one start of the target and one more fetch of its tag, since uv fetches a tag afresh on each run, and the run then reuses the probe's build.

**Why the script is core's, in the CLI area.** A clone with nobody at the keyboard is no one host's case: a pipeline's runner, a container's setup and a hosted agent's first session all meet it. So the script does useful work in any project, the test for what core ships ([COR-014](../../../.pkit/decisions/core/COR-014-universal-applicability.md)).

- **No adapter carries it,** since an adapter holds what one harness needs, and the script needs no harness ([COR-005](../../../.pkit/decisions/core/COR-005-bundle-pattern.md), its adapter pattern).
- **No capability carries it,** since installing the tool is no discipline a project opts into.
- **No variant per host:** what differs between hosts, the folder a command goes in, reaches the script through uv's own configuration, which a host sets.
- **The CLI area** already holds how the CLI is reached, and sync carries it into every project.

**Why a script of its own, not the in-tree dispatcher.** The dispatcher also runs before any pkit is installed, so it was weighed as the script's home.

- **It is `pkit` itself,** at the path PRJ-001 fixes. An install command there is either one the installed tool lacks, so that `pkit` takes a command in a fresh clone that it refuses once installed, or one the tool has, where installing the tool is the upgrade's job, under ADR-063's terminal test.
- **Invoking it means "run pkit".** Installing from it would make a stray run in a fresh clone an install nobody asked for.
- **In the methodology's source repository** it runs the checkout's own code (ADR-039 route 1), where installing a version means nothing.
- **It is a bash script,** and a minimal container may have only `sh`.

The two share a folder and a moment, before pkit exists, and no logic worth extracting ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)). The dispatcher's part is to send a project's clone to the install script (point 8).

**Why a shell script.** It runs before pkit, where only `uv`, `git` and a shell are certain. POSIX `sh` is on every such machine.

**Why only when invoked.** An install nobody asked for is the network write ADR-063 point 3 keeps from automation. A hook would make it at every session's start, resume, clear and compaction, and in every concurrent session at once. pkit's session start hook uses only the standard library and never blocks, so it cannot carry an install.

**Why an agent may run it.** ADR-063 point 3 keeps the upgrade's install to a terminal for two reasons. An install under automation is a network side effect nobody is there to see, and replacing the shared tool reaches every project that follows it, on a machine that may serve other jobs. An agent's shell mostly lacks a terminal. The script answers both reasons itself. Its install is one somebody asked for: whoever invokes it, under the permission layer that judges every write an agent makes outside its project (point 3). And it never replaces a pkit it finds installed (point 5). So a hosted agent's first session needs no person to install pkit, and a sandbox that refuses the write costs only the printed reason.

**Why the pin, then the recorded version, never `latest`.** In a pinned project the router runs the pin whatever is installed. With the pin installed, the router finds a match and runs it with no fetch (ADR-039 route 3). In an unpinned project the router runs the installed pkit, and sync's guard stops it at any version but the recorded one (ADR-065 point 7). `latest` serves only a project at the latest release. A pin the router cannot route is a directive the project must mend, so the script does not guess past it. Reading the pin as the router reads it keeps the two from disagreeing about a pin, as they would over `v1.2.3`. A manifest that records no version leaves the script no version to stand behind, so it sends a person to choose one rather than print `latest`.

**Why it never replaces an installed pkit.** ADR-063 point 3 installs only at a terminal because replacing the shared tool moves every project that follows it, on a machine that may serve other jobs. The script answers that reason itself, rather than by a terminal. Where nothing is installed, no project runs a pkit the install could move. Where the project's version is installed, nothing changes. Where another version is installed, the script leaves it. So an install with nobody at the keyboard never replaces a tool it found installed, and the upgrade's terminal test stands.

**Why it checks the pkit the commands run.** A pipeline gates its next steps on the script's exit status, so the status has to say whether the project's commands will run the project's version. Only the router decides that, and only the router of the `pkit` the `PATH` finds. Inferred from version numbers, the answer goes wrong in cases a machine meets: a pkit the `PATH` finds before the one uv lists, a version the script cannot order, a router whose URL this machine cannot reach, an offline runner whose image already holds a pkit. Running the project's own `pkit` asks that router itself. The check runs code the project's next command runs anyway. Beside another version in a pinned project, it fetches and builds the pin, as that next command would, and the command reuses the build. Failing wherever the router falls back keeps the status true, so a pipeline has no reason to ignore it, and a missing `uv` or a failed install stays visible.

Those two, and a refusal, end the run before the check. After a refusal the project's commands cannot run its version, and after a failed install there is nothing for the check to find. A machine without `uv` lacks what pkit requires, since the router runs every version but the installed one through `uvx`. So the script fails there even beside a pkit at the project's version, rather than pass a machine its next step may not run on. The dispatcher is named when it comes first on the `PATH`, since its own message names this script, and a reader sent there would go round in a circle.

**Why the race is named, not locked.** A lock would need a place every project's script shares, outside every project, such as uv's own folders, which the script leaves to uv. Nor would it hold back a person's own install or `pkit upgrade`, which take no lock of the script's. The race needs another install in the moment between the script's look and its own install. Its harm is bounded: the router still runs a pinned project's pin wherever it can fetch it, and sync's guard stops an unpinned project loudly.

**Why no host's folders.** A host's folder in what core ships would put that host's knowledge in every project (COR-014). uv already lets a host choose where commands go. So the script needs no list, and saying where uv put the command serves every host.

**Why no history.** Deepening a clone is a write to the repository that the install does not need, and a host may keep a clone shallow on purpose. The commands that need history already say so when they meet a shallow clone, where the history matters.

**Why this is no new installer.** PRJ-015 point 4 decides that a script a project carries, which runs `uv tool install` from the URL at a release tag, adds no install path, and its Rationale answers PRJ-004's reasons against a `curl … | bash` installer. This script is one such. Sync puts it in the project's files at the project's recorded release, and the project commits it with the rest. The install is uv's, from the git URL at a release tag. So the measure that no installer but `uv tool install` is supported still holds ([REQ-031](../../analysis/core/requirements/constraints/050-adopt/REQ-031-cli-from-distribution-url.md)).

**Why a test holds the URLs equal.** The script cannot read the tool's compiled URL, and two copies of one URL drift. With the test, a fork that changes one copy and not the other fails its own tests.

### Alternatives considered

- **Keep SSH, and fall back to HTTPS where it fails.** Rejected, for the reasons above: two transports to reason about and test, each failure doubled, and an SSH prompt the switch does not reach without one more setting.
- **Rewrite git's URLs for the machine,** with an `insteadOf` rule pkit writes in the user's git configuration. Rejected: a write outside the project, to a file other tools share, that bends every repository's fetches to serve pkit's. Such a rule, written by whoever runs the machine, is part of the configuration PRJ-015 point 2 leaves to a machine that reaches GitHub over SSH alone.
- **A setting that chooses the URL,** such as an environment variable the router and the script both read, for a mirror or a network that blocks HTTPS. Not taken: the machine's own configuration of git and uv already serves a mirror and an SSH-only network, for every fetch at once, on the machine owner's authority. A second source of the URL inside pkit could disagree with the compiled one, and one pin would then fetch different code on different machines. A fork compiles its own. It is the shape to add if the need recurs (COR-007).
- **Switch the prompt off in the router's run of a pin.** Rejected: the switch would follow the operator's command into the project's own git. The probe before the run carries it instead.
- **Rely on uv's own switch for the router and the raise.** Not taken: uv sets the switch on its fetches, but the guarantee would then rest on how uv runs git, which pkit does not decide. A probe under pkit's own switch makes it pkit's, and the router's probe exists already.
- **Install `latest`.** Rejected: it serves only a project at the latest release.
- **Replace an installed pkit of another version.** Rejected: it is the move ADR-063 point 3 keeps from automation.
- **Judge the result from the installed version,** succeeding beside another version only in a pinned project whose pkit is at or after the recorded release. Not taken: it trusts what a version implies about a router, and misjudges a pkit the `PATH` finds before uv's, a version it cannot order, and a machine where the router cannot fetch the pin.
- **Probe the pin from the script's own URL** where another version is installed. Not taken: it asks the script's URL, not the router of the pkit the commands run, which may compile another URL, and it misses a pkit the `PATH` finds before uv's. Running that pkit asks its router, at about the same cost.
- **Succeed where uv installed pkit but the `PATH` does not find it.** Not taken: the project's commands, and each `pkit` a script of the project's calls, find pkit through the `PATH`. So the clone is not ready, and the printed folder is the fix.
- **Fail wherever another version stays installed.** Not taken: where the router runs the pin, the project's commands run its version, so the failure would be false, and would teach pipelines to ignore the script's status.
- **A distinct exit status for another version left in place.** Not taken: wherever the script exits non-zero, the machine is not ready to run the project's version, and the message says why, so a caller has nothing to tell apart that the message does not say.
- **A lock against another install.** Not taken, for the reasons above.
- **An install command in the in-tree dispatcher.** Rejected, for the reasons above.
- **Run the script from pkit's session start hook, or from a pkit command.** Rejected: no pkit exists to run before the install. The hook fires at every start, resume, clear and compaction, in every session at once, and never blocks.
- **Ship the script in a component for one host,** a capability or an adapter. Rejected: the need is every unattended clone's. An adapter is a harness's, and a capability a discipline's.
- **Deepen a shallow clone in the script.** Rejected: the install needs no history, and the commands that do already name the fix.
- **Put the command in a folder the script names.** Rejected: one host's folder in every project's script.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record (COR-066 point 5). Each sentence an edit adds or rewrites ends with a forward pointer, `(refinement per ADR-090 point N)`, naming the point it rests on.
  - **ADR-063, point 3.** A sentence closes its first paragraph: "This test governs the upgrade's replacement of the installed tool. The install script, `.pkit/cli/install-pkit.sh`, installs with nobody at a terminal, and only where it finds no pkit installed" (point 5).
  - **ADR-063, point 7.** Its fork sentence reads: "A fork that builds its own wheel compiles its own URL, and puts the same URL in the install script, where a test holds the two equal, so its tool updates from the fork" (points 1 and 7).
  - **ADR-065, point 8, the table's first row.** Its sentence "Where SSH keys fail, install the pin's version from the repository's HTTPS URL, and the router then runs it with no fetch." is removed. The router's fetch and an install by hand use one URL over one transport (point 1), so the install succeeds only where the router's fetch would. Point 9's refusal names this row's remedies, so it follows with no edit of its own.
  - **PRJ-004 takes no edit from this record.** PRJ-015 partly supersedes it on the install form, and names the passages it overturns. Its channel, its frontend and its tags, on which points 3 and 7 stand, are unchanged.
  - **Left as they stand,** each still true under this record:
    - **ADR-039:** route 2 fetches from the compiled URL, and D2 already lists missing auth among the failures it degrades on.
    - **ADR-049:** its raise fetches from the compiled URL, and a fetch refused for a credential is one it already calls unresolvable. The probe point 2 adds is how the raise finds that out before it runs.
    - **ADR-063, points 1 and 2:** their fetches use the compiled URL, and the switch point 2 sets changes how they fail, not what they decide.
    - **ADR-065, point 8, the table's last row:** its message is printed by an installed pkit of another version, where the install script would leave that pkit in place. The forced install the message names is what works on that machine.
    - **ADR-033:** its SSH example sits in its Context, which records the install of its day.
- **Other documents,** written once this record is accepted. The install line in each, and what a machine that reaches GitHub over SSH alone configures, are PRJ-015's to set; these are the edits this record adds.
  - **REQ-031.** Its measure reads: "The install the system recommends, which `pkit init` prints and the CLI reference gives, is `uv tool install` with that URL and the tag `latest`, which points at the highest release. Every other install the system runs or prints names a release tag: its upgrade's, the one a stop names, and the install script's. A pinned release runs through `uvx` from the same URL. That URL is the repository's public HTTPS URL, and none of these fetches waits at a terminal for a credential. No registry and no other installer is supported: the install script installs only through `uv tool install`." Its scope adds a fresh clone's install by the install script. Its verification adds the tests below, and its anchors add PRJ-015, this record and the script. The changed measure changes its obligation, so the change answers what the friction check asks of it.
  - **UC-048.**
    - **Its other actors** add the CI pipeline and the AI agent, `ACT-ci-pipeline` and `ACT-ai-agent`, each with an anchor, since either may run the install script. A host's setup command runs it too, and no actor the analysis holds plays that part, so the build either counts it as the pipeline's case or adds an actor for it.
    - **Its anchors** add this record and the script.
    - **Its minimal guarantee** that the system installs the CLI only at a terminal reads that the system *replaces* an installed CLI only there, and that the install script installs only where it finds no CLI installed. A guarantee is added that a refusal of the script installs nothing and says why. Its guarantee that the system installs from the URL compiled into it, and from no other source, adds the install script's copy of that URL, which a test holds equal to it.
    - **A new variant of step 1,** at a letter after every letter step 1 holds, so variant 1a keeps its letter: on a machine with nobody at the keyboard, the install script installs a fresh clone's CLI at the project's version, and succeeds only where the project's commands then run that version.
  - **JRN-006.** Step 1, on the script's path, needs from UC-049 the system committed for the team at a release that carries the script: a clone with no committed `.pkit/` (ADR-009), or one at an earlier release, has none. Step 2's seam says that a clone whose CLI the install script installed meets no stop for another version. Variant 2a stands, since the script leaves an installed CLI of another version in place. Its anchors add this record.
  - **UC-050** needs no edit. Its precondition from UC-048 holds once UC-048's new variant has run, and its variant 3b names the remedies of ADR-065's last row, which stands.
  - **ACT-operator, UC-051 and UC-052,** anchored on records this change edits, are revalidated through the answers the friction check asks.
  - **The CLI reference's section on installing pkit** documents the install script: what it installs, how it checks the pkit the commands run and when it succeeds, that its verdict holds in its own environment, when it refuses or fails before the check, the dispatcher shadowing an installed pkit, the race with another install, and that it never replaces a pkit it finds installed.
    - It shows the invocation with uv's command folder put first on the `PATH` and exported, `export PATH="$(uv tool dir --bin):$PATH"`, before `sh .pkit/cli/install-pkit.sh`.
    - It names `PKIT_NO_ROUTE=1 pkit pin <version>`, with a version at or after this release, for a project pinned below this release on a machine with no SSH key, and the command for a project whose content is ahead of such a pin (Limits).
  - **The CLI reference outside that section.**
    - Sync's first remedy, and upgrade's refusal under the router's fallback, lose their sentence on SSH keys, as ADR-065's first row does.
    - Sync's paragraph on a pipeline loses its sentence that the router fetches over SSH. For the stop an unpinned project meets under a pkit installed fresh in each run, it names the install script, which installs the version the project records.
- **Code.** The compiled URL becomes the canonical HTTPS form, and the separate HTTPS value the fallback's remedy uses retires. The lookup derives git's spelling from it. The raise probes its target before it runs it. The lookup, the upgrade's install and both probes run with git's terminal prompt off. The router's probe and its run each get an environment of their own, so the switch reaches the probe alone. The fallback's remedies lose their SSH sentence. The in-tree dispatcher names the install script in a project's clone (point 8). The install script is added.
- **Tests.** A test holds the install script's URL equal to the tool's compiled URL. Tests of the script find:
  - that it installs the pin, or the recorded version where nothing is pinned
  - that it reads a pin as the router does, and refuses `v1.2.3`
  - that it refuses a manifest with no recorded version, and prints no install of `latest`
  - that it installs nothing where uv lists a pkit or the `PATH` finds one, and counts the project's own dispatcher as none
  - that it succeeds where the `pkit` the `PATH` finds, run from the project, reports the project's version: with that version installed, and beside another version whose router runs the pin
  - that it fails, and leaves the installed pkit, where the router falls back, where the `PATH` finds another pkit before the one uv lists, and where the `PATH` finds none, naming in the last case the folder uv installed into
  - that it fails without running it where the `PATH` finds the project's own dispatcher first, and says the dispatcher shadows the installed pkit
  - that a refusal, a missing `uv` and a failed install each end the run non-zero before the check, with the reason

  Tests of the lookup, the install and both probes find the prompt switched off. Tests of the router's run and the raise's run find no switch that pkit set. A test finds that `PKIT_NO_ROUTE=1 pkit pin <version>`, run by this release's tool with a version at or after this release, raises a project pinned below it through this release's URL.
- **No migration.** No installed state changes shape. The script is a file added to an existing area, so the hold on new areas does not bite (ADR-065 point 13). uv caches each URL apart, so each pinned version is cloned and built once more from the new URL, and the changeset says so. A tool installed over SSH stays until its next tool step installs over HTTPS.
- **Limits.**
  - **A project kept private** commits no `.pkit/`, so its clone carries no script ([ADR-009](ADR-009-git-footprint-visibility.md)).
  - **A project at a release before the one that ships the script** has none until its next upgrade.
  - **A project pinned below this release.** Its pin is written last (ADR-049 point 1), so its content comes from before this release too, and it carries no install script, unless a raise was interrupted (the next limit). Every pinned project is in this state when this release ships. On a machine with no SSH key, a pkit of this release or later, installed by hand from the HTTPS URL, fetches the pin over HTTPS, and the project's commands run. The pinned code's own lookup and raise still fetch over SSH, so its `pkit upgrade` and `pkit pin <version>` cannot raise it there. `PKIT_NO_ROUTE=1 pkit pin <version>`, naming a release at or after this one, can: the installed tool then runs the raise itself, from its own URL, under a bypass ADR-065 point 9 treats as deliberate. A target below this release raises the pin, but leaves the project on code that fetches over SSH. One raise to this release or later, from any machine, ends the state.
  - **Content ahead of a pin below this release,** as an interrupted raise to this release or later leaves it. The content carries the script. The script installs the pin and succeeds, and sync's guard then stops the project's commands until the raise is finished (ADR-065 point 8, its third remedy). On a machine with no SSH key the pin's own code cannot finish it, since its lookup and its raise fetch over SSH, and the installed pkit the script put there is the pin's. The content's own release can: run through `uvx` from the HTTPS URL with routing bypassed, its `pin <content version>` raises the pin to the content.
  - **No time limit is added.** The lookup keeps its own (ADR-063 point 1). The router's probe and run, the raise, and the script's install and check have none, as before, so a stalled network holds an unattended job until its host's limit ends it.
- **Stands on** COR-005, COR-007, COR-014, COR-066, PRJ-001, PRJ-004, PRJ-007, ADR-009, ADR-039, ADR-049, ADR-059, ADR-063 and ADR-065, all accepted, and PRJ-015, accepted in this change.
