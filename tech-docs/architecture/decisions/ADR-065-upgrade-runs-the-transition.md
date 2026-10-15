---
id: ADR-065
title: pkit upgrade runs the version transition, and pkit sync stays at the project's version
status: accepted
date: 2026-10-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a project records which release of the methodology it holds. Today `pkit sync` under a newer pkit copies that release's files and records its version, but runs none of its backbone migrations. The next `pkit upgrade` then finds the project at its target and runs none either, so those migrations are lost.

Under this record `pkit sync` keeps a project at the release it records, and stops when the running pkit is another release. `pkit upgrade` is the one command that moves a project to a new release, and every migration runs inside it. It records where it is going before it writes anything, and records that it arrived only after its last migration. So the next upgrade finishes an interrupted one.

This record realises [COR-059](../../../.pkit/decisions/core/COR-059-version-transition.md) in project-kit's code, and #1458 to #1465 and #1572 build it. Its points say where each version is recorded, the order an upgrade runs in, and the remedy each stop names. They also stop a transition and sync on a clash of area names, and hold new core areas and adapters until #1600.

## Context

COR-059 decides that a project stays at the versions it records until a version transition moves it. Every migration runs inside a transition, and reconciliation, the sync operation, moves no version. COR-059's last Implication lists what the realising decision records:

- the commands (point 1)
- how a component with no manifest is read (point 2)
- where the completion is recorded (point 3)
- the remedies each stop names (point 8)
- how each version of the CLI is tied to one content, and how a release that moves only a component reaches a project (point 12)

The code today:

- **`pkit sync`** (`sync.run_sync`) copies the running pkit's content and records its version as `backbone_version`. It runs each shipped capability's migrations before that capability's copy, and no backbone or adapter migration.
- **`pkit upgrade`** (`upgrade.run_upgrade`) returns early when `backbone_version` equals the running version. Otherwise it runs `run_sync`, which records the target, and then the backbone migrations and the adapters'.
- **So backbone migrations strand** after a sync under a newer pkit, and after an upgrade interrupted during its migrations. Either way the next upgrade finds the project at its target and runs none. #1452's refusal (`sync.refuse_stranding_backbone_migrations`) stops the first case for now.
- **No adopter has ever run an adapter migration.** `install._install_adapter` copies no `migrations/`, and no code writes an adapter's manifest.
- **A capability's manifest** sits at the capability's root. There each refresh deletes or overwrites it, before `capabilities.refresh_capability` writes it again. Its skips are written where `capabilities.read_prior_skipped_artifacts` never reads them.

#1429's design sets the shape, and the maintainer decided its questions on 11 October. This record also settles five questions the design left open:

- where seed creation falls in a transition (point 4)
- how the target stays readable before the manifest-schema migrations run (point 3)
- who writes each project-owned path, and who owns each piece of derivable state (point 11)
- how a transition reports the replay (point 5)
- how a transition meets a clash of area names among published releases (point 13)

[ADR-049](ADR-049-per-project-version-pin.md), [ADR-063](ADR-063-upgrade-updates-the-tool.md) and [ADR-064](ADR-064-upgrade-pins-by-default.md) say how upgrade and the pin work today. #1457 refines them in place where this record changes what they say.

## Decision

**`pkit upgrade` is project-kit's version transition of the backbone, and `pkit capabilities upgrade <name>` is its transition of one capability. Both call the propagation step that `pkit sync` runs. In an adopting project, only they move a recorded version. Sync's guard stops each command that propagates content at the project's recorded version, when the running pkit is another version. An upgrade records its target first, as `backbone_version`, and its completion last, as `completed_version`.**

The points that follow:

- **Points 1 to 3** say what each command does, where each version is recorded, and where the completion is recorded.
- **Points 4 and 5** set a transition's order, and the replay that a missing completion runs.
- **Point 6** says how a transition settles a new collision and the dependency gates before it writes.
- **Points 7 to 9** say which commands stop, the remedy each stop names, and how a pinned project's upgrade moves.
- **Points 10 to 12** retire `sync --force`, name the writers of project-owned paths, and tie a version to a tagged install.
- **Point 13** stops a transition and sync's copy on a clash of area names, and holds new core areas and adapters until #1600.

### 1. Sync's propagation step has two callers

The code behind `pkit sync` splits in two: a propagation step, and the sync command that runs it. A transition calls the step, never the command, so the sync command's stop never fires inside an upgrade.

- **What the step does:** it copies from the bundle, the content the running pkit ships (ADR-033). It copies the methodology's trees, adapters included, and the shipped capabilities its caller names, with their skips. It checks no version, runs no migration, writes no manifest and creates no seed path. Before it writes the methodology's trees, it stops on a clash of area names (point 13).
- **What the sync command does around it:**
  - first, the guard (point 7), which lets the methodology's source pass
  - in the methodology's source, the self-host branch, and nothing else
  - elsewhere:
    - the step, naming each shipped capability that the bundle ships at its recorded version
    - then merge delivery in its auto-add tier, deploy, the `.pkit/.gitignore` render, the agent workspace and provisioning
    - no write to the manifest, no seed path and no migration
- **What a transition does around it:** everything point 4 orders, from compatibility to the pin.
- **The self-host branch** is all that either command runs in the methodology's source (ADR-059 point 2). It runs the deploy and merge primitives, the render, the workspace and provisioning, and copies nothing. Upgrade runs it before any of its checks.
- **Inside a sync that proceeds,** each installed capability is handled by the version it records, read as point 2 reads it:
  - bundled at its recorded version: copied, with no migration and no stamp
  - bundled newer, or its manifest still at the capability's root: skipped, and reported as pending `pkit upgrade`
  - bundled older: skipped and reported. The capability downgrade check (#524) takes no override.
  - no recorded version, from neither a manifest nor its `package.yaml`: skipped and reported
  - not in the bundle: COR-017's no-longer-shipped warning
  - incubated: skipped (COR-031)
  - externally-sourced: skipped, and never read as shipped. Once its fetch is built, sync brings it to its pin (COR-041).
- **The commands, each anchored to one operation** on COR-004's list, which COR-059 point 3 extends:
  - `pkit sync` is reconciliation (COR-059 point 2).
  - `pkit upgrade` is a transition of the backbone. `pkit pin <newer>` reaches the same transition by running the target's `upgrade` through the router's bypass.
  - `pkit capabilities upgrade <name>` is a transition of one shipped capability, to the version the project's recorded release ships. It finishes an interrupted transition of that capability, or a capability an untagged install left behind.
  - `pkit init` is first install. It records the two states in a transition's order (point 4).
  - `pkit capabilities install` propagates one capability at the recorded backbone, under the guard (point 7).

### 2. Each component records its own version, and only a transition moves it

| Component | Recorded in | Moved by |
|---|---|---|
| the backbone, its target | `backbone_version` in `.pkit/manifest.yaml` | a transition, before it writes anything else |
| the backbone, its completion | `completed_version` in the same file (point 3) | a transition, last |
| each registered adapter | `.pkit/adapters/<name>/project/manifest.yaml` | a transition, when the adapter's migrations finish |
| each shipped capability | `.pkit/capabilities/<name>/project/manifest.yaml` | a transition, when the capability's migrations finish. Its install writes it first. |
| an incubated capability | its own `package.yaml` | the project (COR-031) |
| an externally-sourced capability | its pin (COR-041) | a transition that repoints the pin, once its fetch is built |

- **A capability's manifest moves under its `project/`.** Every ownership predicate already treats that folder as the project's, so no copy deletes the manifest there.
  - **Who moves it:** a transition, before its copy. The transition of the backbone moves every root manifest in step 2, right after the target is recorded, and rewrites each registry path. A transition of one capability moves its own after its refusals (point 4).
  - **Who never moves it:** sync, which writes a project-owned path only through merge delivery (COR-059 point 2). A sync that meets a root manifest skips that capability (point 1). The guard stops sync anyway until the project's first transition under this release.
  - **The shipped tree:** project-kit's own root manifest of project-management moves, unchanged, under that capability's `project/`. So the bundle ships no capability manifest.
  - **So no copy writes or removes a recorded version** (COR-059 point 1), and the move needs no migration script.
- **Both places at once:** the root manifest wins, and the move replaces the one under `project/` with it. A root manifest sits beside one under `project/` only after one of these:
  - an interrupted move, which leaves two equal copies
  - a write that does not know the move, such as an older pkit's restamp, or a rollback of `.pkit/` to a commit before the move. Such a write leaves the root manifest naming the content the project holds.
- **Who writes and reads it:**
  - A capability's install and a transition write it under `project/`, and the capability's registry entry names that path.
  - Every reader of a capability's recorded version reads the root manifest where one exists, then the one under `project/`, then the installed `package.yaml`. Among those readers are the capability downgrade check, the dependency gates and upgrade's early return.
  - The skips are read from the same manifest's `backend_state.skipped`, where they are written.
- **A restamp changes the version, the timestamp and the range, and replaces `backend_state.skipped` with the skips in force.** It keeps every other key of `backend_state`.
- **Every manifest is read before propagation,** since the copy replaces a capability's installed `package.yaml`.
- **A component with no manifest is read as follows:**
  - **A registered adapter with no manifest** reads as at the backbone for sync. The first transition records it at its bundled version and runs no migration.
  - **An adapter a release adds** is registered and recorded at its bundled version by the transition that brings it, in step 3. First install registers every adapter it copies the same way.
  - **A shipped capability with no manifest** falls back to its installed `package.yaml`. With neither readable, the transition copies it, records its bundled version, runs none of its migrations and reports it.
  - **No backbone manifest, or a `backbone_version` that is no version:** sync stops. `pkit upgrade` writes the manifest at its target, as first install does, and replays (point 5).
- **When a project is current:**
  - **for sync:** the running pkit's version equals `backbone_version`, and `completed_version` equals it too.
  - **for upgrade's early return:** both keys equal the target, and every registered adapter and shipped capability records its bundled version.
- **Adapters move with the backbone.** Sync copies every adapter the bundle ships as part of the `adapters` area, and a tagged install fixes their versions (point 12). An adapter's manifest only keys the window of its migrations.

### 3. The completion is recorded as `completed_version`

- **The name:** `completed_version`, which #1429's design gave the key provisionally. It sits beside `backbone_version` in a manifest that is the backbone's alone, so it needs no prefix.
- **Who writes it:** a transition of the backbone, last (point 4), and first install, last. In project-kit's own manifest the release step writes it beside `backbone_version` (PRJ-007). The release step's in-place edit and its list of what a release may write cover both lines.
- **What reads it:**
  - sync's guard, which stops while it differs from `backbone_version` (point 7), and upgrade's older-direction check
  - the backbone's migration window, which takes it as its lower bound in place of `backbone_version`. A missing key leaves the window no lower bound, so it holds every script up to the target.
  - status, which shows an incomplete transition (point 8)
- **The key is optional, with no schema bump.** The backbone manifest's writer has kept keys it does not know since `be3de58b`, the first published commit, in v1.134.0. So every released pkit leaves the key in place, and a test holds the writer to that.
- **A `completed_version` newer than `backbone_version`** reads as incomplete. A release without #1212 reaches that state by syncing over a finished transition. The next upgrade propagates again, and runs backbone migrations from `completed_version`.
- **What is read before the manifest-schema migrations:** COR-010 runs those first among a transition's migrations, which is still after the target is recorded. Steps 1 to 3 read the backbone manifest's two keys and its registry, and each component's manifest. So:
  - the code that reads them reads every format a release has shipped
  - both keys stay top-level scalars in every `schema_version`, and no manifest-schema migration renames or moves them. An older pkit, which reads only `backbone_version`, still finds the target.
  - the target and the completion are each written by an in-place edit of their own line, as the release step edits `backbone_version`. Neither write re-serialises the manifest.
- **The methodology's source is exempt.** Its sync runs the self-host branch (ADR-059 point 2), so neither the guard nor status's incomplete line applies there.

### 4. A transition runs in COR-010's order, with seed paths after the migrations

A transition of the backbone runs after upgrade's own checks, which depend on the code that runs the upgrade:

- **a pinned project's upgrade under its pin's code:** the hand-over to a newer release, then the older-direction check (point 9)
- **any other upgrade:** the fallback refusal (point 9), then ADR-063's tool step where it runs, then the older-direction check (point 7)

A project already current returns after these checks, before step 1, and only writes or raises its pin (ADR-064 point 1). Otherwise these steps run in this order:

1. **Compatibility and collisions.** Each may refuse, and none writes:
   - the refusal of a component its bundle ships older (point 7)
   - the refusal of a clash of area names (point 13)
   - compatibility resolution (COR-010)
   - the dependency gates and the collision flow (point 6)
2. **The target is recorded:** `backbone_version` becomes the target. `completed_version` keeps its value, or stays missing. Then each capability manifest still at its root moves under `project/` (point 2). Each skip chosen in step 1 is recorded in its capability's manifest (point 6).
3. **Propagation at the target,** through the propagation step: the backbone's trees, every adapter, and every shipped capability with its skips. An adapter the target adds is registered here. Then `.pkit/.gitignore` is rendered, so a migration reads the target's render.
4. **Backbone migrations,** from `completed_version`, or every one when it is missing (point 5).
5. **Adapter migrations,** each from the version its manifest records. Their scripts are read from the bundle, as a capability's are, so the adapter copy carries no `migrations/`. Each adapter is recorded at its bundled version when its migrations finish.
6. **Capability migrations,** dependencies first by their `requires_capabilities` (COR-030). Each capability is restamped when its migrations finish.
7. **Seed paths are created where missing** (point 11), never over one that exists.
8. **Derivable state:** merge delivery, deploy, `.pkit/.gitignore` rendered again, the agent workspace and provisioning.
9. **The completion is recorded:** `completed_version` becomes the target.
10. **The pin,** last, as ADR-049 point 1 and ADR-064 point 1 set.

- **Why the render runs twice:** `1.150.0/001-untrack-runtime-ignored-files` reads the render of the target's declarations, so the first render follows propagation. The second is part of derivable state, which COR-010's order regenerates after every migration.
- **Why seed paths follow the migrations:** a migration that moves a project's file to a seed path would otherwise find a fresh seed there. COR-010 left this place open.
- **Why seed paths precede derivable state:** deploy reads `.pkit/agents/project/overlay.yaml`, and merge reads the adapter's `settings/project/settings.json`. Both are seed paths.
- **A capability's files are copied before its migrations,** as COR-010's order sets. Project-management's `0.15.0/001` and `0.24.0/001` are fixed for this order.
- **The adapter copy carries every file the core layer reads from the project's copy of an adapter.** One is the adapter's declaration of which permission dimensions its harness enforces.
- **Merge delivery runs its auto-add tier.** A tier that prompts runs only where a person can answer, and none is built (COR-002, COR-059 point 2).
- **Where a person can answer:** standard input and standard output are both terminals, as ADR-063 point 3 tests. The collision flow uses the same test.
- **A migration that exits non-zero stops the transition.** The completion is not recorded, and the next upgrade runs the migration again.
- **First install records the same two states.** It writes the target before it copies anything, registers the adapters after the copy, and writes `completed_version` last. The next `pkit upgrade` finishes an interrupted install. That upgrade also pins the project by ADR-064's default, while a finished init writes no pin (ADR-064 point 3).
- **A transition of one capability** (`pkit capabilities upgrade <name>`) runs in the same order for that capability alone (COR-010). It writes neither of the backbone's two keys. Its steps:
  1. the guard (point 7), then step 1 for that capability. Each may refuse, and none writes.
  2. its manifest moves under `project/` where it is still at the root, and each skip chosen in step 1 is recorded
  3. steps 3, 6 and 8, for that capability
- **What the report and the dry run show:**
  - the target, and each component's move
  - the replay, where `completed_version` is missing (point 5)
  - each component's migrations, and any collision the transition would ask about
  - in the report, each widening the settings merge brings: an added allow entry, or an added top-level key such as `hooks`. An `ask` rule in the project's additions brings the question back (#1454).

### 5. A missing completion runs every backbone migration once

- **When:** an upgrade finds no `completed_version`. The project's backbone migration history is then unknown (COR-059 point 6).
- **What runs:** every backbone migration up to the target, once. Each component's migrations still run from the version its manifest records.
- **The contract it needs** is COR-010's. A backbone migration acts only on a positive sign that its change is needed, and never deletes by a path's name or position alone. Three scripts break it, and are rewritten before the replay ships:
  - `1.31.0/001` deletes `.claude/agents/product-manager.md` and `orchestrator.md` by name, a project's own agent included.
  - `1.0.0/001` deletes every `schemas/bindings.yaml` four levels below `.pkit/capabilities/`. That reaches a capability's `project/` and an incubated capability's tree.
  - `1.32.0/001` deletes every folder under `.pkit/workflow/project/` by position, and `.pkit/manifests/components/github-issues.yaml` by name. Rewritten, it acts only on a positive sign that the content is the retired bundle's.
- **Fixtures hold each failure a replay risks,** beside a fresh install:
  - an overlay category deleted after `1.54.0/001` ran
  - the `process` block removed while old journals stay on disk
  - a declared file forced back into git
  - a hand-written `.claude/agents/orchestrator.md`, which survives
  - a `bindings.yaml` under a capability's `project/`, and one in an incubated capability's tree, which both survive
  - a project's own file under `.pkit/workflow/project/`, which survives
- **What a replay may restore:** `1.54.0/001`, `1.150.0/001-keep-process-journal-logging` and `1.150.0/001-untrack-runtime-ignored-files` can re-add what a project removed after they ran. The changelog says so, as COR-010 requires.
- **The report names the replay.** It says that no completion is recorded, so every backbone migration runs once, and lists them. The dry run says the same before anything runs.

### 6. A transition settles its collisions and its dependency gates before it writes

- **A new collision** is a skill or agent name that a shipped capability's target version ships and another installed artefact already uses. A name the capability's installed copy holds, or its manifest records as skipped, is not new.
- **The flow is COR-017's install-time flow.** In step 1 a person chooses, for each new collision, override, skip or inspect:
  - **skip:** the copy leaves the capability's artefact out. The capability's manifest records it in `backend_state.skipped` in step 2, before the copy, so an interrupted transition does not ask again.
  - **override:** the capability's artefact replaces the project's colliding one, which git can recover (COR-017). Nothing is recorded.
  - **inspect:** shows the diff and asks again
- **Two consent shapes:** a transition of the backbone asks where a person can answer (point 4). `pkit capabilities upgrade` asks only under `--interactive`, and without it refuses and names the flag.
- **With nobody to answer,** a transition of the backbone refuses before it writes anything. It names two ways on: run it again where a person can answer, or rename the project's artefact.
- **No capability is held back,** so the project stays at one release (COR-059 point 7).
- **What the flow covers:** COR-059 point 7's "shipped artefact" is read as a component's artefact, whose skips the component's manifest records. So the flow leaves out:
  - **a core skill or agent a release adds.** A project artefact of the same name suspends it, by deploy's name precedence (COR-001 and the agents README).
  - **a clash between two artefacts one release ships,** which is the release's to prevent
  - **a collision with externally-sourced content,** which surfaces, as COR-041 sets
  - **a core area whose name a project's own area takes.** Every project has every area, so none can be skipped (COR-011). Point 13 says how the transition meets it.
  - **a core adapter whose name an adapter of the project's own takes,** which point 13's hold keeps a release from adding until #1600
- **A capability the target no longer ships** stays installed, with COR-017's no-longer-shipped warning.
- **The gates run as `pkit capabilities upgrade` runs them,** over the set the transition would leave. That set holds every shipped capability at its bundled version, and every other at its installed version. A conflict therefore involves a capability that does not move: an incubated, externally-sourced or no-longer-shipped one.
  - **A moving capability whose dependency does not move and is out of range** refuses, with a hint (COR-030). The project controls that dependency.
  - **A moving dependency whose new version falls outside the range of a dependent that does not move** warns, naming each such dependent. So does one that leaves a dependent's mandatory connection unmet (COR-053 point 6). The transition proceeds only under `pkit upgrade --force`, so neither is a hard block.
- **`--force` on `pkit upgrade` overrides those two warnings and nothing else.** It overrides no guard, no compatibility refusal, no collision, no clash of area names and no refusal under the router's fallback. Point 9 says how it reaches a pinned project's transition.
- **`pkit capabilities upgrade <name>`** keeps its `--interactive` and `--force` flags, and its gates.

### 7. Sync's guard stops a command that would propagate under another version

- **One guard:** #1212's refusal of a pkit older than the project, widened to the newer direction and to an incomplete transition. Every command that copies methodology content into a project calls it. It replaces #1452's refusal.
- **When it stops,** in any of three states:
  - the running pkit's version is not `backbone_version`
  - `completed_version` differs from `backbone_version`, or is missing
  - the pin is newer than the running pkit, as #1212's refusal has it
- **The pin otherwise only chooses the message** (point 8).
- **How it stops:** it exits non-zero, writes nothing, stops under `--dry-run` too, and takes no override, `pkit upgrade --force` included.
- **Who calls it in both directions:**
  - the sync command, at its entry, never the propagation step
  - `pkit capabilities install` and `pkit capabilities upgrade`, before they write anything
- **A conversion command's use of it** is for #1433's ADR to say.
- **Who calls it in the older direction only:** `pkit upgrade`, which moves the project to the running version. It compares the running pkit with the largest of `backbone_version`, `completed_version` and the pin. It runs before the transition writes anything, where point 4 places it.
- **A component its bundle ships older:** a transition refuses in step 1 when its bundle ships an adapter or a capability older than that component's manifest records. This holds for a transition of the backbone and of one capability. The refusal takes no override. Its message names the component, both versions, and a pkit whose bundle ships that version or newer.
- **So a transition never moves a recorded state down** (COR-059 point 9).
- **Not called:** `pkit capabilities register`, which copies nothing. Commands that write a project's own files in the running release's format are not guarded. Examples are `pkit new`, `pkit config set` and `pkit agents reconcile --write`. Status and validation report the mismatch (#1436), and whether those commands stop is an open question.
- **Exempt:** the methodology's source repository (ADR-059 point 2). The guard runs at the command's entry, before the self-host branch, so it applies sync's self-host test itself.
- **A sound comparison needs one content per version,** which only a tagged install gives (point 12).

### 8. Each stop names the remedy for the state it finds

The guard's message, and upgrade's under the router's fallback, name the remedy for the state found. The first row that matches wins, in the table's order. The table gives each remedy, and the CLI reference gives the wording.

| State | The message names |
|---|---|
| Pinned, and the router fell back to another installed pkit | Reconnect and run again, since the router runs the pin whenever it can fetch it, or run the pin through `uvx`. Where SSH keys fail, install the pin's version from the repository's HTTPS URL, and the router then runs it with no fetch. To move on purpose, `pkit unpin` and then `pkit upgrade`. Not a bare `pkit upgrade`, which refuses here (point 9). |
| No manifest, or a recorded version that is no version | `pkit upgrade`, which writes the manifest at its target and replays (point 5) |
| The running pkit older than the content or the pin | the remedies #1212 gives. Content ahead of its pin also names `pkit upgrade`, which finishes the interrupted raise. |
| The transition incomplete | `pkit upgrade`. For a migration that fails every time, fix its cause and run again, or roll back as ADR-049 point 3 sets. |
| Pinned, the content behind the pin, the pin's code running | `pkit upgrade`, whose routed child finishes the pin (point 9) |
| Unpinned, the running pkit newer than the content | **Move:** `pkit upgrade`, which pins by default (`--no-pin` keeps it unpinned) and may first update the tool (`--no-self-update` declines). **Stay:** `pkit pin`, which pins at the content's version, so the router runs that version. **A pipeline:** commit a pin, or install the project's version. |

- **How sync knows the router fell back:** by the test point 9 sets, the router's fallback mark without `PKIT_NO_ROUTE`. The fallback only chooses the message. Sync stops under it only where its guard finds a mismatch.
- **An unpinned project whose installed pkit moves to each new release** meets the stop at every release, until it pins. The changelog says so.
- **Messages that sent an operator to sync to seed or repair the manifest name upgrade instead.**
- **Messages that name `pkit sync` as a routine fix stay.** Where sync can run they are right, and where it stops its own message names the remedy.
- **Status** shows an incomplete transition, and each component a transition would move, beside its backbone line. #1436 and #1440 extend status too.

### 9. A pinned project's upgrade runs under the code of its pin or of a newer release

- **The routed child,** the upgrade the router runs under the pin's code, checks three cases, in this order:
  1. **A newer latest release that resolves:** it hands over to the latest through the bypass.
  2. **A recorded state ahead of the pin,** in `backbone_version` or `completed_version`: upgrade's older-direction check refuses (point 7). Offline, its message names reconnecting, since the latest's upgrade finishes the interrupted raise. Online, no release is newer than the pin, and the message names #1212's remedies.
  3. **Otherwise,** at the latest, ahead of it or offline, the child runs the transition to its pin in its own process. It already runs the pin's code. A project already current at its pin returns before step 1 (point 4).
- **Handing over first still finishes the pin first.** The latest's upgrade runs from the recorded states, so it finishes the pin's interrupted transition on the way.
- **The older-direction check comes after the hand-over and before the child's own transition writes anything.** The hand-over is how a project whose content is ahead of its pin moves on.
- **Flags through the bypass:** a raise through the bypass passes `--dry-run` and `--force` to the target's upgrade. So a pinned dry run lists what the target's upgrade would do. `--no-pin` needs no passing, since a raise pins the project either way (ADR-064 point 2).
- **`pkit pin <newer>` takes `--force`,** with point 6's scope, and passes it on the same way. Its refusal of an older version still takes no override (ADR-049).
- **A pinned project whose installed pkit equals its pin** runs `pkit upgrade` in process, with no mark of a routed child. Its upgrade checks and advances as the routed child's does, and runs no tool step, as ADR-063 point 5 sets.
- **Its rollout:** this order lives in the routed child's code. A project pinned below the release that ships it gets the order on its next raise past that release.
- **Upgrade refuses under the router's fallback.** When the router cannot fetch the pin, it runs the installed pkit instead. It sets its fallback mark in that pkit's environment.
  - **The test:** the router's fallback mark is set, and `PKIT_NO_ROUTE` is not. `PKIT_NO_ROUTE` marks a deliberate bypass, by a raise or by an operator who asked for the running code.
  - **Where:** after the routed child's checks, so a routed child that inherited the mark never meets it. Before ADR-063's tool step, since a pinned project's upgrade never runs that step (ADR-063 point 5). Before anything is written.
  - **What it keeps:** the pin moves only to a release the upgrade resolved (ADR-049 point 3), except under a deliberate bypass.
  - **Its message** names the fallback's remedies (point 8).
- **The router does not change** (ADR-039 D2). It still degrades to the installed pkit. Upgrade refuses under it, and sync stops under it only where its guard finds a mismatch.

### 10. `sync --force` is ignored for one release, then removed

- **The flag's one effect, copying an older capability over a newer one, moves a version down.** So sync stops doing it (point 1).
- **For one release,** sync accepts `--force`, ignores it and says so. A flag whose meaning changes is one of COR-010's triggers, so that change ships a guidance migration, as `1.140.0/001` did for the router shim.
- **A later release removes the flag** (#1464), with a migration under the same trigger.
- **Note:** `pkit upgrade --force` (point 6) is another flag on another command, with its own scope.

### 11. Each writer of a project-owned path is named, and each owner of derivable state

The core layer writes a project-owned path only through a writer a record names (COR-001). Sync's one such writer is merge delivery (COR-059 point 2). This point names the lifecycle's writers, which COR-059 frames, and what regenerates each piece of derivable state.

| Project-owned path | Writer | Consent |
|---|---|---|
| `.pkit/manifest.yaml` | first install, a transition, capability install, register and uninstall, and the release step in project-kit's own source | the command's own |
| a component's manifest under its `project/` | first install, for each adapter it registers. Capability install, and uninstall, which removes it. A transition, which moves a capability's manifest there, records its skips and records each component's version (point 2). | the command's own |
| `.pkit/version-pin` | `pkit pin`, `pkit unpin` and `pkit upgrade` (ADR-049, ADR-064) | the command's own |
| `.claude/settings.json` and `CLAUDE.md` | merge delivery, run by init, sync, a transition and `pkit merge` (COR-002) | none asked, in the auto-add tier |
| `.claude/settings.json.pre-pkit` | first install, backing up a settings file that predates it | the command's own |
| a project artefact a capability's artefact collides with | the collision flow's override, in a capability's install or a transition (COR-017) | the person's answer |
| the seed paths below | first install, a capability's install for its own `project/` folder, and a transition of the backbone where one is missing (COR-059 point 8) | choosing the target (COR-059 point 4), or the command's own |
| `.pkit/agents/project/overlay.yaml` | also `pkit agents reconcile --write`, where the overlay is missing (COR-013) | its own `--write` |
| any file a migration writes | a migration, inside a transition, within what the owning record allows, such as COR-048 point 5 for the configuration file | choosing the target |

- **The seed paths** are what one seeding step creates, in first install and in a transition of the backbone alike. Sync creates none. Their kinds:
  - each area's `project/` folder, and the scratchpad's state folders
  - the agents' overlay, `.pkit/agents/project/overlay.yaml`
  - each adapter's `settings/project/` folder and its `settings.json`
  - each shipped capability's `project/` folder
- **A deleted overlay is repaired by the command that needs it.** `pkit agents reconcile --write` creates a missing overlay from the same seed. It is the one writer outside the lifecycle that the table names, since it creates a seed path. Whether it stops under a version mismatch is the open question of point 7.
- **Other writers outside the lifecycle,** such as `pkit new` or `pkit config set`, are not listed here. A full inventory of every command's writes is outside COR-059's frame.
- **A write with no named writer, until #1600:** a transition's copy over a project's own area that point 13's test cannot tell apart.

| Derivable state | Regenerated by |
|---|---|
| the deployed skills and agents | each adapter's deploy primitives |
| the merged entries in `.claude/settings.json`, and `CLAUDE.md`'s include | each adapter's merge primitives |
| `.pkit/.gitignore` | the core layer's render of the runtime-ignore declarations of the backbone and each installed component (ADR-009 rule 7) |
| `.agent-workspace/` and its line in the local exclude file | the core layer's workspace step |
| the query commands' environments | the core layer's provisioning of each registered query command |

- **First install, sync and a transition each regenerate every piece of derivable state.** None of it is recorded in a manifest (COR-010).
- **The local exclude file** (`.git/info/exclude`) belongs to the clone, not to the project's tree. Two writers keep apart in it: the workspace step adds one line, and `pkit visibility` keeps its own region (ADR-009).

### 12. A version identifies content only for a tagged install

- **A tagged install ties each pkit version to one content** (ADR-033). So sync's guard, which compares versions, is sound there and only there.
- **An untagged install, from main, is vouched for by no version.** Its `VERSION` names the last release, while its files may be newer. The guard compares its version like any other, so the comparison vouches for nothing.
- **A release that moves only a component** cuts no tag (the release README). Under a tagged install it reaches a project with the next backbone release, through that release's transition.

### 13. A transition and sync stop on a clash of area names, and no core area is added until #1600

A project may create its own area at `.pkit/<name>/` (COR-011). A later release may ship a core area of the same name, and its copy would write over the project's area. Among published releases one such clash can happen, and a test of the area's content stops the copy on that clash before writing. A hold keeps a release from adding another until #1600 builds the full check.

- **The clash that can happen:** a project's own area at `.pkit/lifecycle/`, made at a release before v1.149.0, which first shipped the core `lifecycle` area. Every other area a release propagates is in `install.PROPAGATED_AREAS` at the v1.134.0 tag, the first published release.
- **How the test tells the two apart:** the core `lifecycle` area holds `ownership.py`. A project's own area holds it only by chance, the first case below. The file came with the area's first propagation, in commit `3440f2a8`, and the core area has held it since.
- **A clash of area names:** the running pkit ships the core area, and something other than a folder holding the file `ownership.py` sits at `.pkit/lifecycle`. A link at that path is a clash too. An empty folder is no clash.
- **Every copy keeps the test true:** first install's copy and the propagation step write `ownership.py` first in that area. So an interrupted copy leaves the folder empty, or holding the file.
- **Where the test runs:**
  - a transition, in step 1, before anything is written
  - the propagation step, before it writes the methodology's trees. So sync meets the test too, on an untagged install as well (point 12).
- **A clash of area names stops the command.** It stops whether or not a person can answer, and under `--dry-run` too. It takes no override.
- **The message** names the path, and the running release, which ships the core area. It names the ways on:
  - **To move on:** move the project's area to another name, with what refers to it. Then run the command again.
  - **To stay,** after a transition's stop: an unpinned project pins its recorded release with `pkit pin`, point 8's Stay remedy. A project pinned at that release needs nothing, since the transition did not move its pin. The message names no way to stay for any other project, or after sync's stop, since sync already runs the recorded release.
  - **Where the folder is the methodology's own area and has lost `ownership.py`:** restore that file from git. Where git holds no copy of it, remove the folder, which holds none of the project's content. Then run the command again.
- **What the test cannot tell apart, until #1600:** a transition's copy writes over a project's own area in two cases:
  - a project's own `lifecycle` area that holds a file named `ownership.py`
  - a project's own area under a name core shipped before v1.134.0, in a project still at a release before core shipped that name

  This is a limit of this point, which #1600 removes. Sync meets neither case. Its guard keeps it at the release the project records, and a project at a release that carries the test already holds every core area.
- **The hold:** no release adds a core area or a core adapter until #1600 builds the full check. A test holds it, and its message names #1600. It fails on any change, a removal included, to these:
  - the areas a release propagates
  - the core adapters it ships
  - `ownership.py` in the core `lifecycle` area
- **Why the hold covers adapters:** a project's own adapter, made by `pkit new adapter`, meets the same overwrite under a core adapter of its name.
- **What the hold leaves to #1600:** other names core writes under `.pkit/`, such as `capabilities`, which a capability's install creates.
- **Commands that meet no clash of area names:** `pkit capabilities install` and `pkit capabilities upgrade` copy one capability and no area. An install may create `capabilities`, as above. First install refuses a project that already holds `.pkit/`.
- **Its rollout:** the test binds only code that carries it. A transition run by a release without it copies without it, whatever path reaches that release.

## Rationale

**Why a transition calls the step, not the command.** The sync command's stop would otherwise fire inside an upgrade, where the running pkit is newer than the project by design. With the stop on the command alone, no caller has to tell the guard who it is.

**Why the target is `backbone_version`, and the completion is a new key.** An older pkit reads only `backbone_version`. Written first, the target shows that pkit a newer version, and #1212's refusal stops it (COR-059). A key that older code ignores carries the completion without a schema bump.

**Why neither key ever moves.** A target written first protects a project only while every older pkit finds `backbone_version` where it always was. A manifest-schema migration runs after the target is written. Had it moved the key, an older pkit could no longer read the target, and would not stop.

**Why seed paths fall between the migrations and derivable state.** Before the migrations, a migration that moves a project's file to a seed path would meet a fresh seed there. After derivable state, deploy and merge would read a missing overlay or a missing settings file. Between the two, neither happens.

**Why an adapter with no manifest runs no migration.** No adopter has run an adapter migration, and the one that exists repeats what merge does. So recording the bundled version loses nothing.

**Why `1.32.0/001` is rewritten too.** #1429's audit judged it safe, since its path is retired. Accepted COR-010's rule has no such exception.

**Why a transition refuses a component its bundle ships older.** Copying it would move its recorded version down, under migrations that run forward only (COR-010). Skipping it would leave the project at two releases, which COR-059 point 7 rules out. A refusal keeps both rules.

**Why a new skip is recorded before the copy.** Recorded at the restamp, a skip is lost when a migration stops the transition. The next upgrade would then ask again, and with nobody to answer it would refuse its own recovery.

**Why a clash of area names stops the copy, with no choice offered.** Of COR-017's choices, inspect only asks again, and a skip does not fit an area, since every project has every area (COR-011). An override would make the copy the writer of a whole tree it knows is the project's, and that content would still have to move. So the copy stops before writing, the outcome COR-059 point 7 gives a collision nobody answers.

**Why `lifecycle` alone, told by `ownership.py`.** Every other area a release propagates has shipped since v1.134.0, so a project at a published release already holds it as core. `lifecycle` first shipped in v1.149.0, and `ownership.py` came with it. A file tells it apart, not a version, since an install from main held the area before v1.149.0 was tagged (point 12).

**Why two cases wait for #1600.** Telling them apart needs two things no release records: which areas each earlier release shipped, and what core wrote in them. Releases before v1.134.0 had adopters, and their history is not published. A stop on the names core shipped then would stop such a project on core content, with no override.

**Why a hold, and not the full check now.** The full check tells every core area apart under every release, and #1600 settles COR-011 and COR-001 with it. Only `lifecycle` can clash among published releases, so the stop covers it, and the hold keeps the case from widening. Its test fails on any change to the areas, the core adapters or the file, so whoever makes one meets the hold first.

**Why the hold's test fails on a removal, and on the file.** A release that moved `ownership.py` would stop every project on its own core area. A removed name could come back over content a retiring migration left there.

**Why `--force` names the gates' override.** COR-030 names the override `--force`, and `pkit capabilities upgrade --force` already overrides the same two gates. One name for one override across both transitions is learned once. Scoped to those gates, the flag loosens no stop that takes no override.

**Why the fallback refusal keys on the router's mark.** Under the fallback the versions can look fine: the installed pkit may be newer than both the content and the pin. Only the router's mark says that the run is not the pin's code. `PKIT_NO_ROUTE` marks a deliberate bypass, by a raise or by an operator who asked for the running code, so that run proceeds.

**Why the routed child finishes its own pin.** It already runs the pin's code, so finishing a transition to the pin needs no fetch. Handing over to a newer latest release still comes first, since the latest's upgrade finishes everything from the recorded states. A recorded state ahead of the pin is refused before the child's own transition, which would take it down to the pin.

**Why a capability's manifest moves under `project/`, and before the copy.** Every ownership predicate already treats that folder as the project's, and COR-010 puts a component's manifest in its project-side directory. A file-level exception at the capability's root would fork the predicates, as #813 and #823 did. Moved after the copy, the manifest would already be gone, since the copy prunes its root position.

**Why a tagged install.** A version names one content only where the install is tied to a tag. A development version stamped on every untagged build would stop every untagged install in every project.

### Alternatives considered

- **A transition calls the sync command, which exempts its caller.** Rejected: the guard would depend on knowing its caller, and a missed case would stop the remedy itself.
- **The completion as a marker in a file of its own.** Rejected: an older pkit cannot read a marker it does not know (COR-059).
- **A version bump of the manifest schema for the new key.** Not taken: the key is optional, and every released writer keeps it.
- **Seed paths before the migrations, or at the end.** Rejected, for the reasons above.
- **A name of its own for the gates' override on `pkit upgrade`, such as `--allow-desync`.** Not taken: one override would have two names, against COR-030's `--force`.
- **Upgrade under the fallback raises the pin to the installed pkit.** Rejected: ADR-049 point 3 raises a pin to the latest release, not to whatever is installed.
- **A capability with no readable version runs every migration it ships.** Rejected: the replay is the backbone's alone (COR-059 point 6). It would also run project-management's `0.54.0/001`, which grandfathers a bootstrap that may never have happened.
- **A migration script that moves a capability's manifest.** Not taken: the transition already moves it before its copy, so a script would repeat that code.
- **Sync moves a root manifest before its copy.** Rejected: sync writes a project-owned path only through merge delivery (COR-059 point 2). It skips that capability instead, and the guard stops sync anyway until the project's first transition.
- **The manifest under `project/` wins over a root one.** Rejected: a root manifest beside it comes from an interrupted move, or from a write that does not know the move. Either way the root one names the content the project holds.
- **A transition skips a component its bundle ships older, as sync does.** Rejected: the project would hold two releases (COR-059 point 7).
- **A new skip recorded at the restamp.** Rejected: an interrupted transition would ask again, and with nobody to answer would refuse its own recovery.
- **COR-017's flow for a clash of area names.** Rejected: every project has every area (COR-011). An override would make the copy a writer over a whole tree it knows is the project's (COR-001).
- **The transition renames the project's area.** Rejected: a rewrite of the project's own words needs a person to review its diff (COR-059 point 10).
- **The full check now:** each release lists its areas in its own content, with a table for the releases before the list. Not taken, as the maintainer decided for #1572 on 15 October. Only `lifecycle` can clash among published releases, and the hold keeps it so. #1600 builds the check before a release adds a core area.
- **`lifecycle` told by the version the project records.** Rejected: an install from main held the core area while it recorded v1.148.x (point 12).
- **The test in a transition alone.** Rejected: sync's copy on an untagged install meets the same case (point 12). Every copy passes the propagation step, so a test there meets each caller.
- **The transition's copy named the writer of what the test cannot tell apart (point 11).** Not taken: its consent would rest on what the copy reads, not on a person (COR-059 point 4). #1600 removes the two cases instead.
- **A development version stamped on untagged builds.** Rejected, as the maintainer decided for #1429 on 11 October.

## Implications

- **Records refined in place** (#1457): ADR-049, ADR-063 and ADR-064, where they say any of these:
  - that a re-run recovers an interrupted upgrade
  - that sync writes `backbone_version`
  - how upgrade acts under the router's fallback
  - that a pinned upgrade at the latest release changes nothing (ADR-049 point 5, ADR-064's Implications)
  - that upgrade runs sync (ADR-063 point 3, ADR-064 point 1)
  - that upgrade stops on a `.pkit/` with no manifest (ADR-063 point 5). It writes the manifest at its target instead (point 2).
  - that `pkit pin` refuses with the seed-the-manifest posture `upgrade` uses (ADR-049 point 3). Pin still refuses there, and names `pkit upgrade`.
- **PRJ-007 is refined in place** (#1459): the release step writes both keys. Its sentence that install and upgrade write `backbone_version` when an adopter syncs names the transition instead.
- **PRJ-004 is refined in place** (#1465): its canonical install names a release tag, `@v<version>` (point 12). `pkit init` ends by printing that install with its own version.
- **Where COR-011 and COR-001 do not hold, until #1600 settles them:**
  - COR-011 says an adopter cannot create an area under a name core already ships, so no project's area collides with a core one. COR-001 says an extension's names do not collide with core's. `lifecycle` collided when a later release shipped it. Point 13 stops on that clash, and its hold keeps a release from adding another.
  - COR-011 says sync never touches a project's own area, and a transition copies through sync's propagation step (point 1). COR-001 lets the core layer write a project-owned path only through a writer a record names. In the two cases point 13's test cannot tell apart, a transition's copy writes over a project's own area. No record names that copy as their writer.
- **This record supersedes nothing.**
- **Conversions stay out of the transition** (COR-059 point 10). #1433 realises them.
- **Docs:** each issue updates the lifecycle README and the CLI reference where it changes what they say.
- **Migrations:** ignoring `sync --force` and removing it each ship one (point 10). The new key and the manifest's move need none.
- **Where the code differs** from this record, beyond what the Context lists, at the time of writing:
  - `run_upgrade`'s early return compares `backbone_version` alone.
  - `install._install_adapter` leaves out `permission-enforcement.yaml`.
  - `capabilities` reads and writes a capability's manifest at its root, and `manifest.write_component_manifest` replaces `backend_state` whole.
  - `sync._sync_installed_capabilities` reads an externally-sourced capability as shipped.
  - `pkit upgrade` skips a capability its bundle ships older, through sync's capability downgrade check, where point 7 refuses.
  - `upgrade._check_capability_dep_conflicts_for_upgrade` reads the installed versions.
  - `upgrade._auto_advance_pinned` compares only the latest release with the pin, and returns when they are equal.
  - Under the router's fallback, upgrade raises the pin to the installed version.
  - `pkit agents reconcile --write` stops on a missing overlay, and names `pkit init`.
  - The install code's override copies the capability's artefact and leaves the project's in place, unlike point 6's. How the install code comes into line is an open question for a follow-up.
- **Stands on these records, all accepted:**
  - COR-001, COR-002, COR-004, COR-010, COR-011, COR-013, COR-017, COR-030, COR-031, COR-041, COR-048, COR-053 and COR-059
  - ADR-009, ADR-033, ADR-039, ADR-049, ADR-059, ADR-063, ADR-064, PRJ-004 and PRJ-007
