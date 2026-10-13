---
id: ADR-063
title: pkit upgrade updates a stale tool, and prints the command where it cannot or may not
status: accepted
date: 2026-10-11
author: Aleš Kalfas <kalfas.ales@gmail.com>
supersedes: ADR-044
---

## Summary

**In plain terms:** an upgrade can take a project no further than the pkit tool that runs it, and that tool is one install every project on the machine shares. So `pkit upgrade` first asks the release source whether a newer pkit exists. When the installed tool is behind, the upgrade installs the latest release with `uv` and runs itself again under the new tool. One command brings both the tool and the project up to date.

The upgrade installs only when the pkit running it is the installed tool. Where it cannot or may not install, it prints the command instead. That covers no terminal, `--no-self-update`, a dry run, a failed install, and a pkit other than the installed tool.

A failed lookup or install never fails the upgrade. When the install succeeds but the upgrade detects it cannot run again under the new tool, the upgrade stops before it syncs or pins. It names the command to re-run. The failed hand-overs it cannot detect are in the Implications.

The step runs outside any project, where it is the whole of `pkit upgrade`, and in an un-pinned project. A pinned project's upgrade never runs it: the pin moves through `uvx`, and the installed tool is left alone.

The install moves only projects that follow the tool. A pinned project keeps running its pin while the router can fetch it, at the cost of a `uvx` run per command whenever the pin and the tool differ ([ADR-064](ADR-064-upgrade-pins-by-default.md)).

This record supersedes [ADR-044](ADR-044-upgrade-self-update-detect-instruct.md), whose upgrade detects a stale tool and only prints the command.

## Context

Two things are upgraded, by two means. The **tool** is the `uv`-installed wheel with its bundled methodology content, version-locked to its code ([ADR-033](ADR-033-official-install-bundles-content.md)). It is one install, shared by every project on the machine. A **project's** `.pkit/` is brought up to what that tool bundles by `pkit upgrade` ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)). So an upgrade cannot take a project past its tool. Under a stale tool it reports nothing to upgrade, and the fix is a `uv` command the operator has to know.

ADR-044 has `pkit upgrade` detect a newer release and print that command. It does not run it. Its first reason is reach: replacing the shared tool moves every project on the machine at once, as a side effect of a command run in one of them. Its others: a sandbox gates the install anyway, the per-project pin would retire an install built first ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)), and printing cannot install from the wrong upstream. It names two later steps, a per-project pin the router serves through `uvx`, and an install pkit runs itself.

The pin exists. A project's `.pkit/version-pin` names the version the project runs, and the router runs that version through `uvx` whatever tool is installed ([ADR-039](ADR-039-pkit-entry-point-router.md), [ADR-049](ADR-049-per-project-version-pin.md)). An upgrade writes the pin by default (ADR-064).

Replacing the tool is a network write outside any one project. Where a sandbox confines the session, it confines that write as well.

## Decision

**When the installed tool runs `pkit upgrade` and is behind the latest release, the upgrade installs that release and runs again under it. Where it cannot or may not install, it prints the command. A failed lookup or install never fails the upgrade. Where the upgrade detects a failed hand-over, it stops with an error before it syncs or pins anything, and names the command to re-run.**

1. **Detect, best-effort.** The upgrade asks the release source for its highest release, read from its `v`-prefixed tags. It runs `git ls-remote --tags` against the distribution URL compiled into the tool, the URL the router fetches pins from, with a short time limit. A pre-release or dev release tag is skipped, even one above the latest release. When the running tool is at or above that version, the upgrade says the tool is current.

   Any failure — offline, no credentials, no `git`, the limit reached, no release tag — prints a warning on standard error. The upgrade then goes on with its own steps under the running tool, as if the tool were current. Those steps may find nothing to upgrade.

2. **Install when the tool is behind.** When the running pkit is the installed tool, the upgrade runs `uv tool install --force <distribution URL>@v<latest>`. The installed tool is the pkit that runs from the environment `uv tool install` made for it, under `uv tool dir`. pkit asks no question of its own before the install.

   When the install succeeds, the upgrade hands itself over, replacing its own process with the same command, run by the first `pkit` the `PATH` finds. That is the new tool when uv's tool directory comes first on the `PATH`. The new process carries `PKIT_SELF_UPDATED=1`. A process that carries it never installs the tool, whatever the versions say.

3. **Print the command where it cannot or may not install, and stop where the hand-over fails.** The upgrade installs nothing when standard input or standard output is not a terminal, when `--no-self-update` is passed, or when the process carries `PKIT_SELF_UPDATED=1`. It prints the install command instead, with a note to run `pkit upgrade` again, unless it stops as below. It prints the same when the install exits non-zero or cannot be started. A sandbox that refuses the install ends here.

   The upgrade installs only under the installed tool. A pkit run another way is not that tool: through `uv run`, a pip install or a `uvx` served from uv's cache. Such a pkit prints the newer release and its command, and the upgrade goes on under it. So does any pkit when `uv` cannot say where its tools live, unless a hand-over started it.

   When the install succeeds and the upgrade detects a failed hand-over, it stops with an error before it syncs or pins anything. It names the command to re-run once uv's tool directory comes first on the `PATH`. It detects two failed hand-overs:
   - **`pkit` cannot be started.** The process that ran the install stops.
   - **The `PATH` finds another pkit.** The new process carries `PKIT_SELF_UPDATED=1` and a terminal, and checks itself. It stops when it is behind the latest release, by its own lookup, and is not the installed tool by point 2's test. Where `uv` cannot say where its tools live, that test answers no. Where the lookup fails, the new process goes on, as point 1 says.

   Under `--dry-run` the upgrade runs nothing. The installed tool says which install it would run, with or without a terminal. A pkit run another way prints the command.

4. **Before the project's own steps.** The tool step comes before the upgrade compares the project's content with the tool. It also comes before the refusal to run under a pkit older than the project's content or pin (#1212). So a stale tool is reported, or replaced, even when the project has nothing to upgrade. Where the running pkit is too old for the project, the run under the new tool is the way past that refusal.

5. **Where the step runs.** The step runs in two places:
   - outside any project, with no git repository and no `.pkit/` above the working directory. There it is the whole of `pkit upgrade`, rather than an error about a missing project.
   - in an un-pinned project.

   A pinned project's upgrade never runs it. Its pin moves through the router's bypass, and the installed tool is left alone (ADR-064). The step does not run where routing is bypassed (`PKIT_NO_ROUTE`), whether a pin raise set it or an operator did. It is never reached in the methodology's source repository. There the upgrade hands over to sync under the checkout's own code, and refuses under any other code, both before this step ([ADR-059](ADR-059-methodology-source-repository.md)). Inside a git repository with no `.pkit/`, or a `.pkit/` with no manifest, the upgrade stops with an error before the step.

6. **What the run under the new tool does.** The new process routes like any `pkit` command. In an un-pinned project the router runs the new tool. Its upgrade finds the tool current, brings the content to the new bundle, and pins the project there unless `--no-pin` was passed (ADR-064). One command leaves the tool and the project at the latest release.

7. **The tool, from its compiled URL.** The step installs the tool from the distribution URL compiled into it. It touches no content a project takes from an external source ([COR-041](../../../.pkit/decisions/core/COR-041-external-source-distribution.md)). A fork that builds its own wheel compiles its own URL, so its tool updates from the fork. A tool installed from anywhere else — a local path, a mirror — is replaced by the compiled URL's release once that release is newer. `--no-self-update` keeps such an install. The step uses the router's URL and leaves the router's route decision as ADR-039 sets it.

## Rationale

**Why install rather than print.** The friction is a stale tool the operator has to notice and fix with another command. A printed command names the fix. An install removes the step. ADR-044's first reason against installing is reach: replacing the shared tool moves every project that follows it. Pinning by default takes pinned projects out of that reach while the router can fetch their pins. They keep their versions, and pay a `uvx` run per command (ADR-064). The install moves only un-pinned projects. Some passed `--no-pin`, and asked to follow the tool. Others have not been pinned by any upgrade yet. They run the new tool over their older content, as they would after an install by hand, until their own upgrade pins them.

**Why the pin does not retire the install.** ADR-044 expects the per-project pin to make an install unnecessary, so building one first would be work the pin removes (COR-007). The pin does not remove it. An un-pinned project runs the installed tool. Outside any project there is only the tool to update. And a pinned project runs in-process only while its pin equals the tool. So the tool has to move.

**Why an un-pinned project installs rather than using the bypass.** A pinned raise gets the target's code through the bypass, because the router runs the pin. An un-pinned project runs whatever tool is installed. The bypass could bring its content to a newer release, but the tool it runs would stay behind, and code and content would part. That is the drift the pin exists to prevent. Moving an un-pinned project means moving the tool, or pinning the project, which ADR-064 does at the end.

**Why only at a terminal.** An install under automation — a pipeline, a piped call, a shell an agent drives without a terminal — is a network side effect nobody is there to see. It may land on a machine that serves other jobs. Printing the command there costs nothing, and leaves the choice to whoever reads the output. A terminal is a proxy for a person, not proof. Automation that allocates one, as `docker run -t`, `ssh -t` or an agent driving a terminal multiplexer do, passes the check. Such automation opts out with `--no-self-update`. Agent shells mostly lack a terminal, so the install runs mostly where a person typed the command. Where a sandbox confines that session and refuses the install, the upgrade prints the command, so a sandboxed operator loses nothing.

**Why only under the installed tool.** The install replaces the `uv`-installed tool, and the hand-over runs the first `pkit` the `PATH` finds. A pkit run another way has a version its operator chose, and a hand-over to the first `pkit` the `PATH` finds would override it. Point 2's test answers no when in doubt. That costs the printed command outside a hand-over, and a stop and a re-run inside one.

**Why pkit asks no question first.** pkit cannot list the projects an install moves: every un-pinned project, and every pinned project whose pin equals the tool, which switches to `uvx`. So a question could not say what it affects. The operator who runs `pkit upgrade` at a terminal has asked to be brought up to date, and `--no-self-update` declines the install in advance.

**Why run again under the new tool.** A release's content is locked to its code (ADR-033). Going on in the old process would bring the project to the old bundle and pin it there. Replacing the process lets the one command finish under the code it just installed.

**Why a failed hand-over stops.** Going on would bring the project to an older bundle and pin it there, the outcome "Why run again under the new tool" rules out. Stopping before the sync costs a fix to the `PATH` and one re-run, and the install stands.

**Why a guard of its own.** The router's loop guard, `PKIT_ROUTED`, marks a process the router started at a pin. It switches routing off, and it sends a pinned project's upgrade down the pinned path. Reusing it would mislabel the run under the new tool, which no router started at a pin. `PKIT_SELF_UPDATED` stops one thing, a second install. It stops it whatever the versions say, so an install that succeeds but leaves the reported version behind cannot loop.

**Why the wrong-upstream risk is accepted.** The step installs from the compiled URL. A tool installed from a local path or a mirror is replaced once the compiled URL has a newer release. The risk is narrow. The lookup asks the compiled URL too, so a machine that cannot reach it never gets as far as the install. Where it can, `--no-self-update` keeps such a tool, one run at a time.

**Why it sits above the router.** The step calls on the router's distribution URL and leaves its route decision alone. The guard belongs to the upgrade, not to the router. ADR-039 is not reopened.

### Alternatives considered

- **Detect and print only, never install.** This is ADR-044's ruling, which this record supersedes. Not kept: it leaves the manual step. Its first reason, the install's reach over every project, does not hold for pinned projects, and its others are answered above. Printing is the fallback of point 3.
- **Ask `[y/N]` before installing.** ADR-044's planned next step. Not taken, for the reasons above.
- **Install in every session, with or without a terminal.** Rejected: a pipeline would replace its machine's tool with nobody watching.
- **Go on in the old process after the install.** Rejected: the project would be brought to the old bundle and pinned there.
- **Move the project first, install last.** Every upgrade that needs a newer release would raise the project through the bypass and pin it, then install the tool at that version, so the pin and the tool agree. A pinned project would advance without a terminal, and the install would only save the `uvx` start-up. Not taken: it fetches each release twice, a `--no-pin` project needs the install first anyway, and a pinned project's upgrade would update the shared tool, which point 5 keeps out. It is the shape to weigh if the `uvx` cost after each raise proves heavy.
- **A lasting opt-out of the install,** an environment variable or a user setting. Left open. Forgetting `--no-self-update` replaces a tool held back on purpose, which is harder to undo than a forgotten `--no-pin` (ADR-064). It is the first lasting opt-out to add if one is wanted.
- **Run the new tool by its path,** from `uv tool dir --bin`, rather than look `pkit` up on the `PATH`. Not taken: the lookup runs the `pkit` the operator's own shell runs next. Running uv's copy by path would finish the upgrade under a tool the shell does not run, and hide the mismatch.
- **A separate `pkit self-update` command.** Not taken: `pkit upgrade` run outside a project updates the tool alone, and a second command would split one intent, "bring me up to date", across two.
- **Reuse the router's loop guard.** Rejected, for the reason above.

## Implications

- **The command.** `pkit upgrade` may run `uv tool install --force`, at a terminal and under the installed tool only. `--no-self-update` keeps the printed command alone, for that run. The CLI reference describes the flags and the messages (`.pkit/cli/README.md`, `upgrade`).
- **`uv` only.** The printed command and the installed one are both `uv` commands, so the step rests on the `uv`-only install ([PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)).
- **Permissions.** The methodology adds no permission rule that lets the install past a sandbox. pkit works with the permission layer, not around it (core rules 14 and 15).
- **Pinned projects and the tool.** An upgrade never updates the tool for a pinned project. After each raise the pin is ahead of the tool, and the project runs every command through `uvx`. That lasts until the tool is updated another way: an upgrade outside any project, an upgrade in an un-pinned project, or an install by hand.
- **Where the code differs on pinned projects.** The code runs the step in two pinned cases: a pin equal to the installed tool, which the router runs in-process, and a pin the router could not fetch, where it falls back to the installed tool. #1462 tracks both.
- **What a failure leaves.** An install is not undone when the rest of the upgrade fails. An un-pinned project is then left un-pinned under the newer tool, until its upgrade runs again. A forced install that fails part-way can leave the shared tool unusable. The old process keeps running and prints the install command, and running that with `uv` repairs the tool.
- **What a failed hand-over leaves.** Where the upgrade detects it, the project's content and pin stay as they were, and the new tool stays installed. Two failed hand-overs go undetected, and the upgrade goes on, bringing the project to the running pkit's bundle and pinning it there. One is where the pkit that installs, or the first `pkit` the `PATH` finds, comes from a release without this stop. The other is where the new process cannot look up the latest release.
- **Pre-release tags.** The lookup skips them (point 1). So what the step installs, and what a pinned raise writes as the pin, is a release `pkit pin` and the release step's floors accept.
- **No migration.** The behaviour lives in the upgrading code. A machine gets it with the first upgrade run by a tool that carries it, and no installed state changes shape.
- **Stands on** ADR-033, ADR-039, ADR-049, ADR-059, ADR-064, COR-007, COR-010, COR-041 and PRJ-004, all accepted.
