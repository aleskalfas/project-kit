---
id: ADR-064
title: pkit upgrade pins an un-pinned project by default
status: proposed
date: 2026-10-11
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a project's pin is its `.pkit/version-pin` file, and the router runs the pkit version the pin names, whatever tool the machine has installed ([ADR-049](ADR-049-per-project-version-pin.md)). Under ADR-049 a project gets a pin only by asking for one with `pkit pin`. Under this record `pkit upgrade` writes it. An upgrade of an un-pinned project ends by pinning it at the version its content just reached. `--no-pin` skips the pin, and the project keeps following the installed tool. So after an upgrade the project's code and content match, with nothing to remember.

A pinned project keeps its version when the installed tool moves, while the router can fetch its pin. That is what makes it safe for `pkit upgrade` to update the shared tool ([ADR-063](ADR-063-upgrade-updates-the-tool.md)), which it does only outside any project and in an un-pinned one. The price is a `uvx` run per command whenever the installed tool and the pin differ. An upgrade never updates the tool for a pinned project, so they differ after every raise, until the tool is updated another way.

This record partially supersedes ADR-049. It overturns ADR-049's ruling that pinning is opt-in, and the parts of its reasoning that assume an upgrade never installs the tool. The pin file, the router's reading of it, the three gestures, the bypass a raise runs through, and writing the pin last stand as ADR-049 sets them.

## Context

ADR-049 makes the router's per-project pin real. A project-owned file, `.pkit/version-pin`, names the version a project runs. When it names a version other than the installed tool's, the router runs the command under `uvx` at that version ([ADR-039](ADR-039-pkit-entry-point-router.md)). `pkit pin` writes the file, `pkit unpin` removes it, and `pkit upgrade` raises a pin that exists. ADR-049 makes the pin opt-in. An un-pinned project's upgrade writes none, and the router runs the installed tool for that project.

The failure a pin prevents is drift: a newer tool running over older content that was never migrated to it. Reads suffer most, since validation and gates then apply rules the content does not follow (ADR-049, "Why route all commands"). Use on real projects shows that this drift is the common failure. A pin a project has to ask for is forgotten exactly when the tool moves.

ADR-049's case for a single raise mechanism rests on [ADR-044](ADR-044-upgrade-self-update-detect-instruct.md)'s upgrade, which prints the `uv` command and never installs the tool. In ADR-049's words, an un-pinned upgrade "instructs rather than acting", while a pinned one acts, because it changes nothing shared. ADR-063 supersedes ADR-044: outside any project and in an un-pinned one, the upgrade installs a stale tool. That premise falls, and the mechanism needs a reason of its own.

## Decision

**An upgrade leaves the project pinned, unless `--no-pin` is passed. In an un-pinned project, `pkit upgrade` ends by pinning the project at the version its content just reached.**

1. **The default pin.** In an un-pinned project, `pkit upgrade` writes `.pkit/version-pin` at the version of the running tool's bundle. That is the version the upgrade has just brought the content to. The tool reads it from its own bundle, so the pin needs no network. The upgrade writes the pin last, after the sync and the migrations, as ADR-049 point 1 orders every pin write. The write is atomic, so the router never reads a torn pin. The upgrade pins the project also when the content was already at that version. A sync that fails stops the upgrade before the pin. `--dry-run` says which pin it would write, and writes none.

2. **`--no-pin`.** The flag skips the pin. The project stays un-pinned and keeps following the installed tool. The opt-out holds for one upgrade only: nothing records it, so the next upgrade without the flag pins the project. `pkit unpin` removes a pin the default wrote (ADR-049 point 3), and it too lasts until the next upgrade without the flag. In a pinned project the flag changes nothing, since the upgrade raises the existing pin either way.

3. **What the default does not reach.** `init` and `sync` write no pin (ADR-049 point 2). The methodology's source repository is never pinned. Its upgrade hands over to sync, or refuses under code that is not the checkout's own, before any pin is written ([ADR-059](ADR-059-methodology-source-repository.md)).

4. **One raise mechanism, on its own reason.** `pkit pin <newer>` and a pinned `pkit upgrade` raise a pin the same way (ADR-049 point 5). Each resolves a target version, the argument or the latest release. Each runs the target's own upgrade through the router's bypass, then writes the pin. They share the mechanism because both need the target's code to bring the content to the target. The router runs before any command, so a run at the pin cannot load a newer pkit from inside. Neither raise touches the installed tool. Updating the tool is a separate step, ADR-063's, which runs only outside any project or in an un-pinned project.

5. **A specific version.** `pkit pin <version>` is the way to a specific newer version, and `pkit upgrade` takes no version target (ADR-049 point 7). Installing that version as the tool does not move a pinned project. The project keeps running its pin, whatever tool is installed.

### What this overturns in ADR-049, and what stands

Overturned:

- The ruling that pinning is opt-in. It is in the opening summary ("A project opts in …" and "Absent the file, nothing changes"), in the Decision's lead sentence, and in point 2, where only `pkit pin` creates a pin.
- In point 3, "This is the opt-in gesture and the only way a project acquires its first pin file", and the `pkit upgrade` bullet's sentence that an un-pinned upgrade writes no pin.
- The blast-radius premise, in three places. Point 5's second paragraph rests the shared mechanism on it: "They rest on the same premise … the blast-radius symmetry argued in the *Rationale*". Point 7 rests on it the reason a global install is not the way to a specific version: it "mutates the shared tool, which the blast-radius invariant argues against". The Rationale argues it in "Why both raises use one mechanism — blast-radius symmetry". This record's point 4 gives the shared mechanism its own reason, and its point 5 gives ADR-049 point 7 its own.
- The Rationale paragraph "Why opt-in", and in "Why three gestures" the clause that `pkit upgrade` only moves an existing pin forward.
- In the Implications:
  - the `Upgrade` bullet's case (b): an un-pinned upgrade that writes no pin unless `--pin` is passed
  - the pin-file bullet's "except via `pkit pin` / `pkit upgrade`'s deliberate raise"
  - the "Opt-in migration posture" bullet's "Existing adopters are unaffected until they create a pin file"

Standing:

- the pin file, its ownership, and writing it last (point 1)
- the file's presence as the router's signal (point 2)
- the three gestures, and `pkit pin`'s freeze, raise and refusal (point 3)
- routing every command (point 4)
- the bypass, and the shared mechanism (point 5)
- sync routing as normal (point 6)
- no version target on `upgrade` (point 7). Its "unpinned: the installed bundle" stands too, since ADR-063's install may first move that bundle to the latest release.
- the Rationale for a file of its own, for the bypass over a router carve-out, for routing every command, and for separate gestures

Neither standing nor overturned here: the claim that a second run recovers an interrupted raise, in point 1 and in the `Upgrade` implication's case (a). It is wrong on a fact, which #1457 corrects in place.

## Rationale

**Why pin by default.** Drift between a newer tool and older content is the common failure, and a pin a project has to ask for is forgotten when the tool moves. With the pin as the outcome of an upgrade, the project's code and content match with nothing to remember. Whoever wants to follow the tool can, with `--no-pin` or `pkit unpin`. Each lasts one upgrade, and that is enough. Forgetting an opt-in pin costs drift. Forgetting `--no-pin` costs a pin, which keeps the project's version and which `pkit unpin` removes.

**Why the version the content reached.** The upgrade has just brought the content to the running tool's version, so a pin at that version names what is there. A pin at the latest release would name content the project does not have, and would need the network.

**Why the default makes the tool update safe.** ADR-044 withholds the install because replacing the shared tool moves every project that follows it. A pinned project runs its pin through the router, whatever tool is installed, while the router can fetch the pin. So when an upgrade replaces the tool (ADR-063), pinned projects keep their versions, and only un-pinned ones move.

**Why one raise mechanism, without ADR-049's premise.** ADR-049 rests the shared mechanism on a symmetry: an upgrade advances a project as far as it can without changing the shared tool. Under ADR-063 an upgrade does change the shared tool, outside any project and in an un-pinned one. The mechanism needs no such premise. Both raises need the target's code, and the bypass is how a run at the pin gets it (ADR-049, "Why the escape is the operator gesture"). That holds whatever the upgrade does to the installed tool.

**The cost, accepted.** Pinning changes how a project's commands run. While the pin equals the installed tool, they run in-process. When the two differ, each command runs through `uvx` at the pin: a probe that the pin resolves, then the command, two starts that uv's cache softens. They differ after every raise, since an upgrade never updates the tool for a pinned project (ADR-063). And they part all at once when the tool moves. An install, from an un-pinned project's upgrade, from outside any project or by hand, switches every pinned project at the old tool's version to `uvx`, and each then needs its pin fetchable. ADR-049 names this flip of every project at once as a reason against a default pin. This record accepts it as the price of matching code and content.

When the pin cannot be fetched, the router warns and runs the installed tool instead (ADR-039, D2). The project keeps working, under rules its content may not follow. Where that tool is older than the project's content or pin, `sync` and `upgrade` refuse under it, so an older tool never writes its content over newer (#1212).

### Alternatives considered

- **Opt-in pinning.** This is ADR-049's ruling: only `pkit pin` creates a pin, and an un-pinned upgrade writes none. Overturned: drift is the common failure, and an opt-in pin is forgotten when it matters. Following the tool is open as `--no-pin` or `pkit unpin`.
- **A `--pin` flag on `pkit upgrade`.** Not taken: it is opt-in in another place, and is forgotten the same way.
- **Pin at the latest release.** Rejected: it names content the project does not have, and needs the network.
- **A lasting opt-out of the pin,** a project setting or a pin value meaning "follow the tool". Not taken: a forgotten `--no-pin` costs only a pin, which `pkit unpin` removes, so a setting would add state for a slip that does little harm.

## Implications

- **The command.** `pkit upgrade` takes `--no-pin`. The CLI reference describes it (`.pkit/cli/README.md`, `upgrade`).
- **Projects move into the pinned model on their next upgrade.** A project gets the default with the first upgrade run by a tool that carries it. No migration: the behaviour lives in the upgrading code, and the pin file has ADR-049's format.
- **How a pinned project's upgrade runs.** It compares the latest release with the pin and raises the pin to a newer release through the bypass, with no tool step (ADR-049 point 5, ADR-063 point 5). At the latest release, or with the pin ahead of it, nothing changes. When the latest release cannot be found, the pin is left.
- **Where the code differs on pinned projects.** With a pin equal to the installed tool, the code runs the tool in-process and takes the tool step, and without a terminal the project does not advance. With a pin the router could not fetch, it takes the tool step and raises the pin to a newer installed tool's version, not to the latest release. #1462 tracks both. Under that fallback a newer tool's `sync` also brings the content past the pin, which #1460 tracks.
- **An interrupted upgrade is not finished by running it again.** The upgrade's sync records the target version in `.pkit/manifest.yaml` before the migrations run. So a second run finds nothing to upgrade. It writes the default pin, or raises the pin, over content whose migrations never ran. Writing the pin last keeps the pin from naming content that never landed, and no more. #1459 tracks the recovery.
- **The latest-release check is ADR-063's.** A pinned raise asks the release source the way the tool step does (ADR-063 point 1): one source, the distribution URL compiled into the tool.
- **Stands on** ADR-039, ADR-049 in the parts that stand, and ADR-059, all accepted, and on ADR-063, proposed with this record.
