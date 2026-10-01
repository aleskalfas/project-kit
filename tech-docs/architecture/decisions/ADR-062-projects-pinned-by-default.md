---
id: ADR-062
title: A project runs at the pkit version its pin file names, and pkit upgrade pins by default
status: proposed
date: 2026-10-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
supersedes: ADR-049
---

## Summary

**In plain terms:** a project's pkit version is pinned in `.pkit/version-pin`, a one-line file the project owns and commits. When the file names a version other than the installed tool's, the router runs that version through `uvx`, so the project keeps running the code that matches its content whatever tool the machine has. `pkit upgrade` pins an un-pinned project by default, at the version its content just reached; `--no-pin` keeps it following the installed tool. In a pinned project, `pkit upgrade` raises the pin to the latest release, running the target version's own upgrade and never touching the installed tool. `pkit pin` locks a project at a version without moving it, or moves it forward to one; `pkit unpin` removes the pin. The pin is always written last, after content and migrations.

## Context

The entry-point router decides, before any command runs, which pkit serves it: a source checkout's own dispatcher; `uvx project-kit@<pin>` when the project pins a version other than the running tool's; otherwise the installed tool itself ([ADR-039](ADR-039-pkit-entry-point-router.md)). Where the pin is read from, ADR-039 left to the implementation.

A release's code and its bundled content come from one tag ([ADR-033](ADR-033-official-install-bundles-content.md)). A project's content sits at the version it last synced to; the tool on the machine is shared by every project and moves whenever anyone updates it. When they part, a newer tool runs over older content that was never migrated to it — and the commands that suffer most are the reads: validation and gate evaluation apply rules of a version the content does not follow. One machine routinely drives several projects held at different versions.

Two version records exist already, and neither fits. `.pkit/VERSION` is the source tree's own identity and exists only in the methodology's source repository. `manifest.yaml`'s `backbone_version` is a receipt of the last sync, written by every sync.

## Decision

**A project-owned pin file names the version a project runs; `pkit upgrade` writes it by default and raises it; the router honours it.**

1. **The pin file.** The pin lives in `.pkit/version-pin`: one line, a bare `MAJOR.MINOR.PATCH`. The project owns and commits it; `init` and `sync` never write it, and only the gestures below do.

2. **The router reads it.** When the file is present and names a version other than the running tool's, the router re-runs the command under `uvx project-kit@v<pin>`; absent, or equal, the installed tool serves the command in-process. A pin that cannot be resolved warns and falls back to the installed tool, never a hard failure. Every command routes — `sync` and the reads included. The route table, the loop guard and the fallback are ADR-039's, unchanged; this record supplies the pin source it left open.

3. **Upgrade pins by default.** In an un-pinned project, `pkit upgrade` syncs content from the tool's bundle, runs the migrations, and then writes the pin at the version the content reached — the local version, with no network lookup — and also when the content was already current. `--no-pin` skips the write, so the project keeps following the installed tool. A sync that fails writes no pin; `--dry-run` reports the pin it would write.

4. **A pinned upgrade raises the pin to the latest release.** When the router has re-run `pkit upgrade` at the pinned version, the upgrade asks the release source for the latest tag (the check [ADR-061](ADR-061-upgrade-updates-the-tool.md) point 1 defines) and compares it with the pin:
   - **newer** — it runs the target version's own `upgrade` through the router's bypass (`uvx` at the target, `PKIT_NO_ROUTE` set, the loop guard dropped), which syncs content and runs migrations under the target's code, then flips the pin;
   - **equal** — it says the project is at the latest release and changes nothing;
   - **older than the pin** — it says the project is pinned ahead of the newest release and leaves the pin;
   - **unknown** — the release source is unreachable, or the pin is not valid semver — it warns and leaves the pin.

   The installed tool is not touched on this path. A pinned project whose pin matches the installed tool runs in-process; its upgrade syncs from the tool's bundle and raises the pin to that version.

5. **`pkit pin` and `pkit unpin`.** `pkit pin` with no argument freezes the project at its current content version (`backbone_version`), in place. `pkit pin <version>` takes a version number only — a single leading `v` is stripped, and branch, commit, pre-release and build tokens are refused, since the router routes only a bare release tag — and compares it with the content version: **equal** freezes in place; **newer** reconciles content forward under the target's code through the bypass, then writes the pin; **older** is refused, writing nothing, because migrations run forward only ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)) — a project rolls back with `git checkout` of its `.pkit/` tree. Both forms need `manifest.yaml`. `pkit pin` is refused in the methodology's source repository, where the router runs the checkout's own code before any pin is read ([ADR-059](ADR-059-methodology-source-repository.md)). `pkit unpin` deletes the file, and does nothing when there is none. A specific newer version is reached with `pkit pin <version>`; `pkit upgrade` takes no version target.

6. **The pin is written last.** Every gesture that moves a project writes the pin after content sync and migrations, atomically (a temporary file renamed over it), so the pin is never ahead of the content it names. This is an ordering, not a transaction: a raise interrupted mid-migration can leave content ahead of the pin. That state is benign, and running the upgrade or the pin again recovers it — sync re-applies content, applied migrations do nothing, and the pin write does nothing once the pin matches.

7. **The source repository is never pinned.** `pkit upgrade` there hands over to sync before any pin logic.

## Rationale

**Why a file of its own.** The pin is a *directive* — an operator's forward-looking control over which code runs; `backbone_version` is a *record* of what the last sync wrote ([COR-006](../../../.pkit/decisions/core/COR-006-artifact-roles.md)). Using the record as the directive fails three ways: every sync writes `backbone_version`, so an offline sync would rewrite the pin; it advances before migrations run, so it cannot be written last; and capability content moves independently of it. Shipping `.pkit/VERSION` to projects instead would set a second per-project version record beside `backbone_version`, two sources of one truth. A separate file that no sync writes is immune to all of it.

**Why pinned by default.** The failure that matters is a project running a newer global tool over older content, and a pin a project must opt into is forgotten exactly when that happens. Making the pin the outcome of every upgrade leaves a project locked and coherent with no gesture to remember; `--no-pin` and `pkit unpin` keep following the installed tool for whoever wants it. Pinning by default is also what makes updating the shared tool safe: a pinned project does not follow it.

**The cost, accepted.** A pinned project whose pin differs from the installed tool runs every command through a `uvx` re-run — a small start-up cost, softened by uv's cache — and depends on its pin resolving. Pinning by default puts every project into that model on its next upgrade. The safety net is the router's fallback: a pin that cannot be resolved warns and runs the installed tool, so a pinned project never stops working offline.

**Why upgrade pins at the local version.** The content just reached that version, so the pin names exactly what is there; looking up the latest release instead would pin a project ahead of its content, and would need the network.

**Why a raise escapes through the bypass.** The router runs before command dispatch, so a project pinned at one version cannot run a newer one from inside to rewrite its own pin. Teaching the router to leave pin-managing commands unrouted would reopen ADR-039's command-agnostic contract, require parsing arguments before the CLI loads, and fail both ways when a command is misclassified — a pin command that routes does nothing, a methodology command that does not route runs at the wrong version. The bypass already exists and costs the router nothing.

**Why a raise never touches the installed tool.** The target version is fetched per project by `uvx` and the pin file is the project's own, so a pinned project advances with no mutation outside it. `pkit pin <newer>` and a pinned `pkit upgrade` rest on the same two things — a target resolved online, and nothing shared changed — so they share one mechanism.

**Why every command routes.** For a methodology tool the reads are the most version-sensitive commands: a gate that passes under the wrong rules is worse than a write that refuses. Routing every command is what makes the pin a guarantee.

**Why separate gestures.** Locking a project where it is, moving it forward, and releasing it are three intents. The common one with several projects is the first — lock each at its known-good version without moving it — and only `pkit pin` does that; `pkit upgrade` moves and locks; `pkit unpin` releases. This is the lockfile model the design borrows: a lock is written, updated and removed by separate acts.

### Alternatives considered

- **Opt-in pinning: the router does nothing until a project commits the pin, and `pkit upgrade` never writes one** — the ruling of [ADR-049](ADR-049-per-project-version-pin.md), which this record supersedes. Overturned: the drift between a newer tool and older content is the common failure, and an opt-in pin is forgotten when it matters. It remains available as `--no-pin`.
- **A `--pin` flag on `pkit upgrade`.** Rejected: opt-in in another place, forgotten the same way.
- **Reuse `backbone_version` as the pin.** Rejected: a record taken for a directive, rewritten by every sync, advancing before migrations.
- **Ship `.pkit/VERSION` to projects.** Rejected: a second per-project version record beside `backbone_version`.
- **A router that leaves pin-managing commands unrouted.** Rejected: it reopens ADR-039 and fails both ways on a misread command.
- **Route only commands that write.** Rejected: the reads are the most version-sensitive.
- **A `--to <version>` flag on `pkit upgrade`.** Rejected: `pkit pin <version>` already reaches a specific newer version without changing the installed tool.
- **`pkit upgrade` as the only pin gesture.** Rejected: a project could not be locked without being moved.

## Implications

- The router's pin source is `.pkit/version-pin`. The commands are `pkit pin [<version>]`, `pkit unpin`, and `pkit upgrade` with `--no-pin`, described in the CLI reference (`.pkit/cli/README.md`).
- The pin file belongs to the project: the lifecycle's ownership list names it as project-owned, so no sync writes or overwrites it.
- A project moves into the pinned model on its first `pkit upgrade` run by a tool that carries the default. No migration: the behaviour lives in the upgrading code, and the file's format is fixed; a change to its name or format would need one (COR-010).
- The raise runs under the target's code, so the target's sync writes the target's content and runs its migrations (ADR-033). A project pinned below the release that carries a raise behaviour keeps the older code's behaviour until it is moved past it; `pkit pin <newer>` always moves it, with no `uv` step.
- The latest-release check is the one the tool update uses ([ADR-061](ADR-061-upgrade-updates-the-tool.md)): one source, the compiled distribution URL ([PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)).
- Stands on ADR-033, ADR-039, ADR-059, ADR-061, COR-006, COR-010 and PRJ-004, all accepted. ADR-039 is not reopened.
