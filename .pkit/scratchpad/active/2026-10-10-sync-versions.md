---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-10
---

# Only an upgrade moves a project's versions

A design for #1429. It sets the shape of the maintainer's decision that `pkit sync` never moves a version and that every migration runs inside an upgrade.

- **The direction is decided:** by the maintainer on 10 October, on PR #1395. This note designs its shape and does not reopen it.
- **The starting point:** the critic's and the architect's reviews of that decision, kept as #1429's two comments. Their findings were checked against the code here, and the design corrects them where the code disagrees ("Corrections to the first reviews").
- **Read from main at `e2f0a533`:** the code, the records, the migrations and the tests below.
- **Citations:** records by id and point or section. Code by file and function. A line number, where one helps, is at `e2f0a533`.
- **Shared with #1394's design** (`.pkit/scratchpad/active/2026-10-09-content-upgrades.md`): COR-001's named-writer principle, COR-004's list of operations, COR-010, COR-017 and ADR-049. Each is written once. Whichever design's record lands first carries the principle, and the other adds its instance.
- **Its build** is ordered after #1410 and before #1444, as the maintainer set. Where it falls against #1435 to #1442 is question 8. It shares the version guard with #1435, the messages of upgrade and sync with #1438, and status with #1436 and #1440.
- **Reviewed:** by the critic and then the architect. Their findings and the answers are in "Review".
- **Decided so far:** questions 1 and 2, by the maintainer on 11 October. Each answer is under its question.

## The question

How does a project move from one version to the next so that every migration runs exactly where the move happens, and nothing else moves a version?

## In short

`pkit sync` keeps a project in line with the release it records. A *version transition*, run by `pkit upgrade`, is the one operation that moves the recorded versions, and it runs every migration.

- **One propagation step, two callers:** sync runs it at the project's version, and upgrade at its target. The stop on a version mismatch belongs to the sync command, never to the step.
- **What sync writes:** methodology files, state it regenerates from the project's own declarations, and two project-owned files through merge delivery. Never a version, the manifest, a seed or a migration (questions 5 and 6).
- **A version per component:** the backbone and each adapter and capability the methodology ships. Adapters move with the backbone. A capability's record moves under its `project/`, out of the copy's reach.
- **Two recorded states:** a transition records its target before it writes anything and its completion last. The next upgrade finishes an interrupted one, and a newer release's content stops an older pkit.
- **Recovery:** a project whose backbone migrations were stranded runs them all once, on its first upgrade under the new release, under a stronger script contract (question 3).
- **One release per project:** a transition moves every component together. A new collision is resolved inside it, or the transition refuses (question 4).
- **A stop that names the remedy:** each state of a mismatch has its own remedy. `pkit upgrade` is wrong in two of them.
- **Every migration inside the transition,** in COR-010's order: backbone, then adapters, then capabilities in dependency order.
- **Records:** a new core record holds the principle. It partially supersedes COR-017's sync paragraph and COR-004's compound-verb sentence. COR-001, COR-002, COR-004's operation list, COR-010 and COR-048 point 1 are refined, and ADR-049's recovery claim is corrected in place.
- **A stop-gap for the next release,** which ships backbone migrations a sync would strand (question 1).

## The direction, and what its wording claims

The maintainer's comment of 10 October on PR #1395 decided:

> Sync makes the project match the pkit that runs it at the project's version: it restores the methodology's files, re-wires the harness, recreates the workspace and provisions query commands. It runs no migration and writes no project-owned path, so COR-001's extension contract stays true as written. When the running pkit is newer than the project's content, sync stops and names pkit upgrade, as it already stops when pkit is older (#1212). Only upgrade moves versions, and every migration, backbone and capability, runs there. [...] Pinned projects, the default, see no change.

The direction stands. A later comment the same day left the wording of what sync writes to this design. Two claims in the wording do not hold:

- **"Writes no project-owned path":** sync writes `.claude/settings.json` and `CLAUDE.md` through the merge primitives, recreates missing seed paths and writes the manifest. The design takes out the manifest and the seeds. It keeps merge, since a project's settings workflow rests on it, and names merge as sync's one writer to project-owned paths (question 5). COR-001's extension contract is then refined, not kept as written.
- **"Pinned projects, the default, see no change":**
  - **Pinning is the default only after an upgrade.** `pkit init` writes no pin (ADR-049 point 2, `install.install_kit`). An upgrade pins by default (ADR-049's amendment).
  - **Some pinned projects do see a change,** and it is a fix. Under the router's offline fallback, or with content behind its pin, sync moves content past the pin today. After the change it stops ("On a mismatch").

## Today

### Every path that moves a version

- **`pkit sync`** (`sync.run_sync`):
  - copies the running pkit's methodology trees over the project's
  - refreshes each capability the methodology ships through `capabilities.refresh_capability`, which runs the capability's pending migrations, copies its tree and restamps its record
  - records the running pkit's version as `backbone_version` (`sync._update_recorded_backbone_version`)
  - runs no backbone migration and no adapter migration
- **`pkit upgrade`** (`upgrade.run_upgrade`) returns early when `backbone_version` equals the running version (line 190). Otherwise it runs `run_sync`, then the backbone migrations, then the adapters' (lines 213 to 217).
- **`pkit capabilities upgrade <name>`** (`cli.upgrade_capability_cmd`) refreshes one capability through the same `refresh_capability`, after its collision and dependency checks.
- **`pkit pin <newer>`** and a pinned upgrade run the target release's `upgrade` through the router's bypass (`upgrade.reconcile_forward_via_target`, `router.run_bypassed`).
- **`pkit capabilities install`** copies the running pkit's capability at whatever version it ships. It checks only that the capability's `requires_backbone` admits the project's recorded backbone (`cli._check_backbone_satisfied`).

### Where migrations strand

- **Backbone migrations strand after a sync.** Sync records the new `backbone_version` and runs none of them. A later upgrade finds the project at its target and returns early.
- **They strand inside an upgrade too.** `run_sync` records the version before the migrations run. An upgrade interrupted during its migrations leaves the project at its target, and the re-run returns early.
- **So ADR-049's recovery claim does not hold.** Point 1 says a re-run "is idempotent (sync re-applies content, migrations detect already-applied state and no-op per COR-010, and the pin flip is a no-op once it matches)". The CLI reference repeats it (`.pkit/cli/README.md`, `upgrade`). The re-run never reaches the migrations.
- **Adapter migrations have never run in an adopter.** Two causes, either enough:
  - `install._install_adapter` copies an adapter's README, package metadata, top-level scripts and `settings/`. It never copies `migrations/`, so `upgrade._run_component_migrations` finds no scripts in the project's copy.
  - No code writes an adapter's per-component manifest (`.pkit/adapters/<name>/project/manifest.yaml`). The runner skips an adapter without one.
  - The only adapter migration, claude-code's `0.5.0/001`, wires the `CLAUDE.md` include. `merge-claude-md.sh` does the same on every sync, so nothing visible broke.
- **A capability's migrations run before its files are copied,** inside sync (`refresh_capability`). COR-010's order puts propagation first and component migrations after the backbone's (COR-010, "Cross-tier upgrade requires explicit compatibility resolution").
- **Eight backbone scripts in seven version directories** ship today. Two in `1.150.0/` share the index `001`, so their order comes from their slugs.

### A capability's record

- **Where it is:** `.pkit/capabilities/<name>/manifest.yaml`, written by `capabilities._stamp_component_manifest`. That is outside the capability's `project/`, the only part the copy protects (`capabilities._capability_owned`).
- **What the copy does to it:** `treecopy.refresh_owned_tree` deletes every unprotected file the source does not ship. So each refresh deletes the record, and `refresh_capability` writes it again at once.
- **project-management ships one:** project-kit's own `manifest.yaml` for it is in the bundle, since the ownership predicates do not withhold it. A refresh copies it over the adopter's record, and the restamp then rewrites it.
- **The skips a project chose are never read back.** `capabilities._stamp_component_manifest` writes them to `manifest.yaml` under `backend_state.skipped`. `capabilities.read_prior_skipped_artifacts` reads `component-manifest.yaml` under `skipped_artifacts`, a file nothing writes. So every refresh copies the skipped artefacts back and restamps with no skips. COR-017's "The skipped-artifact records persist in the manifest so sync respects them" does not hold in the code.
- **A restamp replaces `backend_state` whole** (`manifest.write_component_manifest`), so it would lose the opaque identifiers COR-010 says a manifest keeps. No capability writes one yet.
- **Where it belongs:** COR-010's Implications put a per-component manifest in "its component's project-side directory", and `manifest.ComponentManifest`'s docstring names `.pkit/capabilities/<name>/project/manifest.yaml`. An adapter's record is placed there, a capability's is not.

### What sync writes

| What | Whose | How today |
|---|---|---|
| `.pkit/<area>/core/`, flat area files, adapters, `cli/pkit` | the methodology's | copied over (`install._install_area`) |
| each shipped capability's tree, except its `project/` | the methodology's | copied, after its migrations |
| a capability's `manifest.yaml` | the project's record, in a position the copy manages | deleted or overwritten by the copy, then restamped |
| `.claude/settings.json`, `CLAUDE.md` | the project's | merged on every sync (`install._ADAPTER_PRIMITIVES`) |
| a missing `project/` stub, a missing `.pkit/agents/project/overlay.yaml` | the project's | created (`_install_area`, tests `test_sync_stubs_project_dir_for_area_that_landed_after_install` and `test_sync_seeds_agents_overlay_if_missing`) |
| `.pkit/manifest.yaml` | the project's | `backbone_version` set, or a minimal manifest seeded where none exists |
| project-owned files a capability migration writes | the project's | e.g. project-management `0.55.0/004` writes `.pkit/project/config.yaml` |
| `.claude/skills`, `.claude/agents` deployments | derivable | deploy primitives |
| `.pkit/.gitignore` | rendered for each project by pkit and never shipped (ADR-009 rule 7) | rendered |
| `.agent-workspace/`, `.git/info/exclude` | clone-local | created where missing |
| query-command environments | outside the repository | provisioned |

- **Merge reads the project's own inputs.** `merge-settings.sh` unions the methodology's baseline with the project's additions (`settings/project/settings.json`), a `Skill(<name>)` grant for every skill under `.pkit/skills/project/` and every capability skill, and each capability's overlay. Core rule 6 sends a project's settings changes through it.
- **The shipped merge never prompts:** `merge-settings.sh` is "Tier-1 only at this stage (auto-add)".
- **Merge inside sync contradicts three texts:**
  - COR-004 keeps sync and merge apart for their consent profiles ("`sync` and `merge` stay separate").
  - COR-002 lists the points where merge runs: "First install", "Manually on demand" and "During upgrade flows". Sync is not among them.
  - The CLI reference says sync "Does **not** invoke seed [...] or merge". The claude-code adapter's README says the opposite.
- **The capability migrations make COR-048 point 1 false in sync,** and project-management's `0.55.0/004` claims "the upgrade being the consent" while sync runs it.

### The pinned flows

- **The routed child.** When a pinned project's `pkit upgrade` runs under its pin's code, `upgrade._auto_advance_pinned` compares the latest release with the pin only. At "latest equals pin" it returns, whatever the project's content holds (lines 553 to 555).
- **Content behind the pin** (a hand-edited pin, a bad merge): sync under the pin's code moves the content to the pin and runs no backbone migration. Upgrade there brings it forward only when a newer release exists.
- **The router's offline fallback** (`router._run_pinned`): when the pin cannot be fetched, the installed pkit runs instead. The router marks the run with `PKIT_PIN_UNRESOLVED` (`router._notice_pin_unresolved`).
  - **A newer installed pkit's sync** moves the content past the pin (`test_sync_newer_than_the_content_moves_it_forward`). That is the hazard ADR-049 named, and it stays possible.
  - **Its upgrade** is no routed child, so it takes the other path, which raises the pin to the installed version (`run_upgrade`, lines 224 and 225). ADR-049 point 3 has an upgrade raise a pin to the latest release, and point 5 leaves the pin unchanged when the latest cannot be resolved.
- **#1212 is not yet released.** Its changeset is in `.changes/unreleased/` (`backbone-patch-20261001-180000-older-pkit-refuses-downgrade.yaml`). Every released pkit, 1.149.0 included, writes its older content over a newer project without a word.

### Versions a release ships

- **Tagged installs:** a release's content is tied to its code (ADR-033). So a pkit at a tagged version ships one version of every adapter and capability.
- **Component-only releases cut no tag** (`.pkit/release/README.md`, "A component-only release (no backbone move) cuts no tag"). Under a tagged install such a release reaches a project only with the next backbone tag.
- **Untagged installs:** `pkit init` recommends `uv tool install git+ssh://…/project-kit.git` with no tag (`install._print_next_steps`, the CLI reference's "Installing pkit on PATH"). That installs main's head. Its `VERSION` is the last release's, while its files may be newer. Today main's head carries the `1.150.0/` backbone scripts beside a `VERSION` of 1.149.0.

## Forces

- **The maintainer's direction:** sync moves no version and runs no migration, and upgrade runs every migration.
- **COR-010's order:** compatibility, propagation, backbone migrations, component migrations, derivable state, recorded versions.
- **COR-004's consent rule:** one command, one operation. Upgrade today anchors to no operation on COR-004's list.
- **Older code meets newer state.** A pinned project's next command may run an older release's code over what a newer one left. Only state that older code already reads stops it.
- **Working workflows.** A project edits its settings additions and runs sync (core rule 6). A pipeline runs `pkit sync` on checkout, before its gate (the lifecycle README, "How dependencies are provisioned before an offline run").
- **Offline use.** "A degraded-but-running command beats a broken one" (ADR-039 D2).
- **COR-030's deadlock rule:** a dependency moving past a dependent's range is "never a hard block", since a hard block would deadlock.
- **Idempotence.** COR-010 promises "already-applied state is a no-op". Recovery that re-runs scripts leans on it, and on more.

## The design

### One propagation step, two callers

`run_sync` splits into a propagation step and the sync command. Upgrade calls the step, never the command, so the stop never fires inside an upgrade (the first critic's first red flag, removed by construction).

| | `pkit sync` | the version transition |
|---|---|---|
| Content | the running pkit's, which must be the project's recorded version | the running pkit's, which is the target |
| Guard | stops unless the running version is the recorded one and the last transition completed | refuses an older running pkit (#1212) |
| Methodology trees, adapters included | copied | copied |
| A shipped capability | copied when its bundled version is the recorded one, else skipped and reported | copied |
| A capability's record | out of the copy's reach, under its `project/` | out of the copy's reach, restamped after its migrations |
| Merge delivery | its auto-add tier (question 5) | its auto-add tier |
| Seeds | none (question 6) | created where missing |
| Migrations | never | backbone, adapters, capabilities |
| Recorded versions | none written | target first, completion last |
| `.pkit/.gitignore` | rendered | rendered after the copy, so migrations read the target's, and again at the end |
| Deploy, workspace, provisioning | at the end | at the end |

- **The self-host branch comes first in both,** as today (ADR-059 point 2). It runs the deploy and merge primitives, the ignore render, the workspace and provisioning.
- **The step checks no version and runs no migration.** Each caller does what the table says around it.
- **The stop's message names the remedy** for the state it finds ("On a mismatch").

### What sync writes

After the change, sync writes three kinds of thing and no other.

- **Methodology content:** the methodology's trees, adapters included, and each shipped capability at its recorded version, its `project/` left alone.
- **State it regenerates from the project's own declarations,** which COR-010 calls derivable ("Manifest content: non-derivable state only"): the deployed harness, `.pkit/.gitignore`, the agent workspace and its line in `.git/info/exclude`, and the query commands' environments.
- **Project-owned paths, through merge delivery only** (COR-002), in its auto-add tier, into `.claude/settings.json` and `CLAUDE.md`. COR-010 lists "merged-config permission entries" among derivable state. `merge-claude-md.sh` creates `CLAUDE.md` when none exists, so that one case is merge's too.
- **No longer:** a seed, any write to the manifest, any version, any migration.
- **A tier merge has not built,** COR-002's prompt-once tier, runs only where a person can answer: `pkit merge`, `pkit init`, and a transition run on a terminal. Without one it writes nothing, as COR-048 point 5 sets for a configuration key.
- **What this makes of COR-001:** "project-owned paths are not touched by sync" becomes "touched by sync only through merge delivery". #1432's named-writer principle carries it, with "never reads" dropped, since validation reads.

### The versions a project records, and what current means

| Component | Recorded in | Moved by |
|---|---|---|
| backbone, its files | `backbone_version` in `.pkit/manifest.yaml` | a transition, first |
| backbone, the transition | a new optional key, `completed_version` (name provisional) | a transition, last |
| each registered adapter | `.pkit/adapters/<name>/project/manifest.yaml`, written for the first time | a transition, after the adapter's migrations |
| each shipped capability | `.pkit/capabilities/<name>/project/manifest.yaml`, moved there from the capability's root | a transition, after the capability's migrations |
| an incubated capability | its own `package.yaml` | the project (COR-031) |
| an externally-sourced capability | its pin (COR-041) | an upgrade, by repointing the pin |

- **`backbone_version` names the methodology files the project holds,** or the target of a transition not yet complete. That second reading is new, and the lifecycle README and ADR-049 say so ("Settled positions this reopens").
- **A capability's record moves under its `project/`,** where every ownership predicate already places the project's files, and the bundle already withholds them (`capabilities._capability_owned`, `ownership._ADOPTER_TIER_DIRS`).
  - **The code that writes the record moves it.** It reads the root file when no record sits under `project/`, writes the new place, and rewrites the registry's `manifest:` path.
  - **Skips are read from where they are written,** and a restamp changes the version, the timestamp and the range only, keeping `backend_state`.
- **Every record is read before propagation.** A capability with no record falls back, as today, to its installed `package.yaml`, which the copy has not yet replaced.
- **Adapters move with the backbone.** Sync copies every adapter the methodology ships as part of the `adapters` area (`install._install_area`), and a tagged install fixes their versions. Their record only keys their migration window.
  - **A registered adapter with no record,** every project's state today, reads as at the backbone for sync. The first transition records it at its bundled version and runs no migration. No adapter migration has ever run, and the one that exists repeats what merge does.
  - **An adapter a release adds** is registered by the transition that brings it and recorded at its bundled version. Init already registers every adapter it copies, so this carries today's behaviour forward.
- **Current for sync:** the running pkit's version equals `backbone_version`, and `completed_version` equals it too. Anything else stops sync.
- **Inside a sync that proceeds, each shipped capability:**
  - bundled version equal to the recorded one: copied, no migration, no stamp
  - bundled newer: skipped and reported, "pending: run `pkit upgrade`"
  - bundled older: skipped and reported, with no override (today's #524 guard, without `--force`)
  - not in the bundle: the orphan warning, as today
  - incubated: skipped, with the collision report of COR-031, as today
  - externally-sourced: brought to its pin, once its fetch is built (COR-041). Until then it is skipped, never read as shipped, which `_sync_installed_capabilities` does today
  - no recorded version at all: skipped and reported
- **Current for upgrade, its early return:** `backbone_version` and `completed_version` both equal the target, and every registered adapter and shipped capability records its bundled version. Today only the backbone is compared (line 190).
- **What per-component records buy under tagged installs:** a component moves only with its backbone release, so they do not restore COR-010's "upgrade selectively". They key each component's migration window, and they matter for an interrupted transition, an untagged install and an externally-sourced capability.
- **What a version identifies:** content only for a tagged install (question 10).

### How a transition records its progress

A transition writes the target to `backbone_version` before it writes anything else, and writes `completed_version` last. The design settles this rather than asking: its alternative fails on the argument below.

1. **Compatibility** against the versions each component moves to, and COR-030's and COR-053 point 6's gates ("A new collision, and the gates").
2. **The target is recorded:** `backbone_version` becomes the target. `completed_version` keeps its value, or stays missing.
3. **Propagation** at the target, with `.pkit/.gitignore` rendered.
4. **Migrations:** the backbone's from `completed_version` to the target, then each adapter's and each capability's from the record read before propagation. Each component is restamped when its migrations finish.
5. **Merge delivery, deploy, the workspace and provisioning.**
6. **Completion:** `completed_version` becomes the target.
7. **The pin,** last, as ADR-049 point 1 sets.

- **The transition is complete when the two keys are equal.** A missing `completed_version` reads as incomplete with no lower bound. No project at the new release's content lacks it: the release's `init` and its upgrades write it.
- **An interrupted transition is finished by the next one.** It finds the two keys apart, runs the backbone migrations from `completed_version`, and each component's from its own record.
- **One completion mark, written last:** sync then never runs over a half-finished transition, a capability half-migrated included. Re-running the backbone window after a late interruption is idempotent and cheap.
- **A migration may now fail loudly.** The next upgrade runs it again. `1.150.0/001-untrack-runtime-ignored-files` never fails the upgrade because "sync has already recorded the new version", and that reason goes.
- **A migration that fails every time** leaves the project unable to sync, where today it strands silently. The stop names both ways out: fix the cause and re-run `pkit upgrade`, or roll back with `git checkout <ref> -- .pkit/`, which restores both keys. COR-004's forward-only failure gets its recovery entry point.
- **Why the target is written first:** an older pkit reading an interrupted transition.
  - **Written last,** the record would show the older pkit its own version. It would pass #1212's guard and copy its older files over a half-migrated tree.
  - **Written first,** the record shows a newer version. The older pkit refuses (#1212), and its message leads to the newer code.
  - **A marker the older code cannot read** would not stop it. That is why a second recorded state beats an "in progress" marker, and why this is settled, not asked.
- **The limit:** the protection starts with the release that ships #1212. A project pinned at 1.149.0 or earlier runs code without the guard. If its first upgrade out is interrupted, a `pkit sync` under the old pin copies 1.149.0's files back. The next `pkit upgrade` still recovers it.
- **A `completed_version` newer than `backbone_version`** is reachable the same way: a release without #1212 syncs over a finished transition. It reads as incomplete, and the next upgrade propagates again and runs migrations from `completed_version`.
- **No schema bump:** the key is optional, and no JSON schema describes the manifest. `manifest.write_backbone_manifest` has kept keys it does not know since the first published commit, `be3de58b` in v1.134.0, so every release leaves the key in place.
- **`pending_migration_scripts` takes `completed_version` as its lower bound** for the backbone, in place of `backbone_version`.
- **project-kit's own manifest:** the release step writes both keys (`release._sync_self_host_manifest_backbone`, PRJ-007). The guard and status's "incomplete" line do not apply in the methodology's source, as #1435 exempts it.

### Projects already stranded

A missing `completed_version` means the project's migration history is unknown. The first upgrade under the new release then runs every backbone migration up to its target, once (question 3).

- **What it leans on is more than idempotence.** A replay also runs scripts on states that never needed them, and on states a project changed after a script ran. COR-010's "already-applied state is a no-op" does not cover those.
- **The contract it needs:** a backbone script acts only on a positive sign that its change is needed, as project-management's `0.55.0/001` and `0.55.0/002` do for files they did not write. It never deletes by name or position alone.
- **Where the contract lives:** COR-010's migration rule, core rule 5, the lifecycle README's "Script contract" and the migration-author skill. It lands with R1 and the skill, so every script written before the replay ships meets it.
- **Its test:** fixtures that hold each failure the audit names, not only a fresh install. An overlay category deleted, the `process` block removed with journals on disk, a declared file forced back into git, a hand-written `.claude/agents/orchestrator.md`, a `bindings.yaml` under a capability's `project/`, and a `.pkit/workflow/project/` that holds something.
- **The audit of today's eight scripts:**
  - **No effect on any state:** `1.93.0/001` exits when the rules area exists, and `1.140.0/001` only prints guidance.
  - **Deletes by position, safe only because the path is retired:** `1.32.0/001` removes every `.pkit/workflow/project/*/`. Nothing else lives under the retired area, and a fixture holds that.
  - **Deletes by name, so it is rewritten before the replay ships:**
    - `1.31.0/001` deletes anything at `.claude/agents/product-manager.md` or `orchestrator.md`, a project's own agent of that name included.
    - `1.0.0/001` deletes every `schemas/bindings.yaml` four levels below `.pkit/capabilities/`, which reaches a capability's `project/` and an incubated capability.
  - **Can re-add what a project removed later,** a cost the changelog states:
    - `1.54.0/001` appends an overlay category the project deleted after the script ran.
    - `1.150.0/001-keep-process-journal-logging` writes `enabled: true` where the `process` block was removed while old journals stay on disk.
    - `1.150.0/001-untrack-runtime-ignored-files` stages again the untracking of a declared file a project forced back into git.
- **Capabilities are never replayed.** Their record is written at install and restamped after their migrations, so their history is known once the record is out of the copy's reach.
- **The dry run lists the replay,** and the changelog says why it runs once.

### A new collision, and the gates

COR-017 says sync refuses the upgrade of a capability that would bring a new collision, and names `pkit capabilities upgrade X --interactive`. Sync's refresh never built that, while `capabilities upgrade` did (`capabilities.detect_upgrade_collisions`). The transition takes it over (question 4).

- **A collision is resolved inside the transition,** with COR-017's install-time flow: override, skip or inspect, for each artefact. Skips are recorded in the capability's record.
- **With nobody to answer,** the transition refuses before it writes anything. It names two ways out: re-run it on a terminal, or rename the project's colliding artefact.
- **So every component stays at one release.** No capability is held back, and no mixed state needs gates of its own.
- **COR-030's and COR-053 point 6's gates run as `capabilities upgrade` runs them,** over the set the transition would leave. Within one release the moving capabilities agree, so a conflict involves a capability that does not move: an incubated or an externally-sourced one.
  - **A moving capability whose dependency is out of range** refuses, with a hint. The operator controls the dependency.
  - **A moving dependency that leaves a capability that does not move out of range** warns, and proceeds only with an explicit override. That is COR-030's "never a hard block", and the realising ADR names the override.
  - **#1410 changes the same check first.**

### On a mismatch

When the running version differs from the project's recorded version, or the last transition is incomplete, sync stops. It writes nothing, exits non-zero, refuses under `--dry-run` too, and takes no override, as #1212's refusal does.

- **The guard is one function,** `sync.refuse_content_downgrade` widened to the newer direction and to an incomplete transition.
- **Which commands call it, and how:**
  - **Both directions:** the sync command at its entry point, never inside the step, and the commands that copy methodology content: `capabilities install` and `upgrade` (question 7), and the conversion command (#1435).
  - **The older direction only:** `pkit upgrade`, which moves the project to the running version, as #1212 has it.
  - **Not guarded now:** commands that write a project's own files in the running release's format, such as `pkit new`, `pkit config set`, `pkit agents reconcile --write`, `pkit permissions apply` and `pkit visibility`. Status and validation report the mismatch (#1436). Whether they stop is a follow-up.
- **What the gate compares:** the running version with the recorded content version, and the transition's two keys. As #1212's guard does, it also refuses a pin newer than the running pkit. Beyond that, the pin only chooses the message.

| State | Sync | The message names |
|---|---|---|
| Unpinned, running pkit newer | stops | **Move:** `pkit upgrade`, which pins by default (`--no-pin` to stay unpinned) and on a terminal may first update the tool (`--no-self-update`). **Stay:** `pkit pin`, which pins at the content's version, so the router runs it. **A pipeline:** commit a pin, or install the project's version |
| Pinned, the router fell back to another installed pkit | stops | reconnect and re-run, since the router runs the pin when it can fetch it, or `uvx --from <url>@v<pin> project-kit sync`. Where SSH keys are what fail, install the pin's version from the repository's HTTPS URL, and the router then runs it with no fetch. To move on purpose, `pkit unpin` and then `pkit upgrade`. Not a bare `pkit upgrade` |
| Pinned, content behind the pin, the pin's code running | stops | `pkit upgrade` (with the routed child's fix below) |
| Transition incomplete | stops | `pkit upgrade`. If a migration fails every time: fix its cause and re-run, or roll back with `git checkout <ref> -- .pkit/` |
| No manifest, or a recorded version that is no version | stops | `pkit upgrade`, which seeds the manifest at its target and replays every backbone migration once |
| Running pkit older than the content or the pin | refuses, as #1212 does | unchanged. Content ahead of its pin also names `pkit upgrade`, which finishes the interrupted raise |

- **An unpinned project on a floating install meets the stop at every release,** until it pins. That is the stop working, and the changelog says so.
- **Upgrade under the router's fallback refuses too.** Today it raises the pin to whatever pkit is installed, not to the latest release (ADR-049 point 3).
  - **How a run knows:** the router's own mark, `PKIT_PIN_UNRESOLVED`, while the run is not bypassed (`PKIT_NO_ROUTE`). The mark is inherited, so the two go together.
  - **What it reopens:** ADR-049's amendment says "an unresolvable pin degrades loudly to running self, never a hard fail". #1212 already made sync and upgrade refuse under an older fallback, so the router still degrades while these two commands refuse ("Settled positions this reopens"). ADR-039 D2 governs the router, which does not change.
- **The routed child finishes its own pin before it looks at the latest release.**
  - **Latest is newer and resolvable:** it hands over to the latest, as today. The latest's upgrade finishes everything from the recorded states.
  - **Otherwise,** at latest, ahead of it, or offline: when the content is behind the pin or the transition incomplete, it runs the transition to its own pin in its own process. It already runs the pin's code.
  - **Content ahead of the pin and offline:** it says so, and names reconnecting.
  - **Its rollout:** the fix lives in the routed child's code, so a project pinned below the release that ships it gets it on its next raise past that release.
- **Messages that send an operator to sync to seed or repair the manifest** name upgrade instead: `run_upgrade` on a missing manifest, `upgrade._require_backbone_version`, `upgrade._pin_order`, `validate.py`'s missing-manifest diagnosis, and the CLI reference's `pin` entry.
- **Messages that name `pkit sync` as a routine fix stay.** Where sync can run, they are right. Where it stops, its own message names the remedy.
- **Pipelines:** a pipeline that runs another pkit than the project's already validates with the wrong code (ADR-049 point 4). The stop surfaces that.
  - **The router fetches over `git+ssh`** (`router.DISTRIBUTION_GIT_URL`). A pinned pipeline without SSH keys falls back, and meets the stop unless it installed the pin's version itself.
  - **project-kit's own pipelines are unaffected:** they run self-host sync (`.github/workflows/checks.yml`, `friction-report.yml`).
- **No deploy-only mode for now.** In the default shared visibility the deployed harness and `.pkit/.gitignore` are committed (ADR-009), and provisioning needs the network anyway. A fresh offline clone with another installed pkit lacks only its workspace and its exclude line. A `--deploy-only` mode waits for a case that asks for it (COR-007).

### Every migration inside the transition, and its order

The transition runs every migration, in COR-010's order. Sync runs none.

1. **Propagation:** the methodology's trees and every shipped component. `.pkit/.gitignore` is rendered, so a migration reads a render of the target's declarations.
2. **Backbone migrations,** from `completed_version`.
3. **Adapter migrations,** each from its record, read from the bundle as capability migrations are, since the project's copy has no `migrations/`.
4. **Capability migrations,** dependencies first by their `requires_capabilities` (COR-030). Today they run in the manifest's order.
5. **Merge delivery, deploy, the workspace and provisioning.**
6. **Completion,** then the pin.

- **A migration may read the render made after propagation,** as `1.150.0/001-untrack-runtime-ignored-files` does by design. A render only after every migration, as the first architect review placed derivable state, would hand it the previous release's.
- **A capability's files are copied before its migrations,** as COR-010's order sets. Today `refresh_capability` runs them first. The audit of the eleven capability scripts and the adapter's one:
  - **evidence's `0.2.0/001`** removes the old flat skill files ahead of the copy. The copy now removes them first, so the script finds nothing to do.
  - **project-management's `0.15.0/001`, `0.24.0/001` and `0.26.0/001`** read the shipped `schemas/workflow.yaml` and expect its `schema_version` to be theirs. Run before the copy, as today, they always find the old file and skip. Run after it, `0.26.0/001` checks real overrides as it was written to, and `0.15.0/001` and `0.24.0/001` warn wrongly on a jump of more than one version. Those two are fixed in the slice that reorders.
  - **project-management's `0.54.0/001`** stamps the installed `package.yaml`'s version. After the copy that is the new version, which its comment intends: "a grandfathered stamp does not immediately read as stale".
  - **The rest** handle either order: `0.12.0/001` and `0.55.0/001` say so, and the others read project-owned files or fixed checksums. The adapter's script edits only `CLAUDE.md`.
- **`pkit capabilities upgrade <name>`** becomes a transition of one component at the project's recorded backbone: copy, migrate, stamp. It finishes a capability left behind by an interrupted transition or an untagged install.
- **The dependency check reads the versions the transition installs,** not the installed ones (`upgrade._check_capability_dep_conflicts_for_upgrade`). #1410 changes this check first.

### Capability install, and other sources

- **`pkit capabilities install` and `upgrade` call sync's guard** (question 7). Every shipped file a project holds then comes from the release its backbone records.
- **`pkit capabilities register`** copies nothing, so it needs no guard.
- **An externally-sourced capability** already follows the principle: sync brings its copy to its pin, and an upgrade repoints the pin (COR-041). When sync stops, nothing is fetched.

### `sync --force` and dry runs

- **`--force`'s only effect, copying an older capability over a newer one, moves a version down,** so sync stops doing it. Settled, not asked:
  - sync accepts `--force` for one release, ignores it and says so
  - a flag whose meaning changes is one of COR-010's triggers, so that change ships a guidance migration, as `1.140.0/001` did for the router shim
  - a later change removes the flag
- **Dry runs:** sync's stop refuses under `--dry-run`, as #1212's does. Upgrade's dry run lists the target, the replay where the key is missing, each component's migrations, and any collision it would ask about.

### Messages and status

- **Status** shows an incomplete transition and each component a transition would move, beside the backbone line it has (`status._report_backbone_version`). #1436 and #1440 extend status too.
- **The CLI reference's upgrade entry** says migrations run "then runs `sync`". The code runs sync first. The rewrite follows the design.

### The records it changes

- **A new core record,** "A project stays at its version until a version transition moves it" (title provisional):
  - a project records a version for its backbone and for each component it installs
  - reconciliation runs at the recorded versions, moves none, and runs no migration
  - a version transition is the only operation that moves a recorded version, and every migration runs inside it
  - one consent covers a transition's parts, since every part follows from the target the person chose
  - COR-004's rule governs operations on a project, so a command may first update the tool that runs it
  - a transition records its target before it writes anything and its completion last, and the next transition finishes an incomplete one
  - a transition moves every component the methodology ships together, and resolves a new collision inside it or refuses
  - a command that copies methodology content under another version than the project records stops and names the remedy
  - why a conversion (#1394) stays out of the transition: a transition's consent is choosing a target, a conversion's is reviewing a diff
  - it cites COR-041 as precedent and uses core terms only
  - it partially supersedes COR-017's sync paragraph, COR-004's compound-verb sentence, and COR-001's seeding cadence for the transition
- **COR-004, refined:** its list of operations gains the version transition in place, with a pointer to the new record, beside #1432's conversion. Its sync-and-merge paragraph is question 5's.
- **COR-001, refined:** sync's writer, merge delivery, and the transition's migrations and seed creation, as instances of the named-writer principle. If #1432 has not landed, this states the principle.
- **COR-002, refined in place:** merge runs at four points, sync among them, in its auto-add tier.
- **COR-010, refined:**
  - Update runs at the recorded versions, and a transition records its target first and its completion last
  - its migration rule takes the stronger contract
  - its Implications on where per-component manifests live stay as written, now true for capabilities
- **COR-048 point 1,** refined in place: an upgrade does write the configuration file, through the migrations point 5 allows.
- **Core rule 5,** the migration-author skill and the lifecycle README's script contract take the stronger contract.
- **The realising ADR,** by the architect, once the core record is accepted: the split, the per-component table, the record's move under `project/`, the manifest key and its test, the replay and its fixtures, the collision flow and the gates' override, the routed child's order, the fallback refusal, the messages, the migration order and its render, `--force`, and the tagged install.
- **ADR-049, refined in place, not superseded.** Its decision stands: the pin flips last, and no two-phase commit. Its claim of how a re-run recovers was false, and the decisions README fixes a false fact in place. #1433 says "#1429's ADR partially supersedes ADR-049", which then needs rewording.
- **ADR-044:** its D1 and Implications say an offline upgrade goes on to "sync the project from the current bundle". They name the transition.
- **Unchanged:** COR-030, COR-031, COR-041, ADR-033, ADR-039 and ADR-059.

## Settled in the design, not asked

The architect's review moved four of the first draft's questions into the design. Each is still authorised through "Settled positions this reopens".

- **Two recorded states,** target first and completion last: an "in progress" marker fails on the design's own argument, since older code cannot read it.
- **A capability's record under its `project/`:** every ownership predicate already treats that place as the project's, and COR-010 already puts it there. Keeping it at the root would fork the ownership rules, as #813 and #823 did.
- **No deploy-only mode now:** COR-007 decides it.
- **`sync --force` ignored for one release, then removed:** mechanical.

## Questions for the maintainer

One decision each. Question 1 has a deadline and comes first. The rest are in order of consequence, and a question that depends on another comes after it.

### 1. Does the next release ship a stop-gap?

- **The question:** the next release ships two backbone migrations in `1.150.0/`. Should it also stop sync from stranding them, before the rest of this build lands?
- **Example:** an unpinned project at 1.149 runs `pkit sync` with the next release's pkit. Its manifest records the new version, `keep-process-journal-logging` never runs, and the project's journal logging stops without a word. Its next `pkit upgrade` finds nothing to do.
- **Recommended:** yes. One small change, ahead of the release: the sync command, at its entry point, refuses to move `backbone_version` past a version directory that holds backbone migrations, and names `pkit upgrade`. Upgrade's own call to sync is untouched, so the remedy works. The changelog says to run `pkit upgrade` for this release.
  - **Its cost:** an issue outside this design's slicing, and a refusal the full guard later replaces.
- **Alternative:** the changelog alone tells adopters to run `pkit upgrade` and not `pkit sync`.
  - **Its cost:** a project that syncs anyway loses its migrations until this build's replay recovers it.
- **Decided: yes,** as recommended, by the maintainer on 11 October. Filed as #1452, a High bug under #332, built before the next release is cut. It is B0 in "Slicing".

### 2. Is `pkit upgrade` one operation, a version transition, and where does that rule live?

- **The question:** COR-004 says a command performs one operation, and rejects as a compound "an "update" that does sync + merge + migrations". Should a version transition count as one operation, recorded in a new core record?
- **Example:** `pkit upgrade` from 1.149 to 1.150 copies 1.150's files, runs the migrations, merges the settings and pins the project. None of COR-004's operations names that.
- **Recommended:** yes. A version transition moves a project's recorded versions to a target. Every part follows from the target the person chose, so one consent covers them: the target's content, every pending migration with the writes COR-048 point 5 allows, merge delivery, the recorded versions and the pin.
  - **What it does in each part depends on what it finds,** as sync's copy does. What COR-004 rejects is a verb whose consent depends on what it finds, silent here and asking there.
  - **COR-004's list gains the operation in place,** beside #1432's conversion. The new core record partially supersedes only the compound-verb sentence and the rejected "smart `update`" alternative, and carries the principle ("The records it changes"). It also partially supersedes COR-017's sync paragraph.
  - **The tool's self-update** (ADR-044) acts on no project. The new record says COR-004's rule governs operations on a project, so a command may first update the tool that runs it.
  - `pkit upgrade`, `pkit capabilities upgrade <name>` and `pkit pin <newer>` anchor to it.
  - **Its cost:** a foundational record on the command surface is overturned in part, one command carries several parts, and one more core record exists.
- **Alternative:** COR-004 stays as it is, and the realising ADR records `pkit upgrade` as a named exception to it.
  - **Its cost:** a core rule with an exception only project-kit's own ADR knows of, so an adopter reading the core records finds a rule the tool breaks.
- **Decided: yes,** as recommended, by the maintainer on 11 October. A version transition is one operation on COR-004's list, and the new core record holds the principle. R1 carries it.

### 3. How do projects already stranded recover?

- **The question:** what does the first upgrade under the new release do for a project with no `completed_version`?
- **Example:** an unpinned project at 1.53 synced by a 1.60 pkit records 1.60 without `1.54.0/001`. Its overlay lacks the architect's categories, and every later upgrade starts from 1.60.
- **Recommended:** a missing key means unknown, and the first upgrade runs every backbone migration up to its target, once. Each script first meets a stronger contract: it acts only on a positive sign that its change is needed ("Projects already stranded").
  - Two scripts that delete by name are rewritten before the replay ships, and fixtures hold each failure the audit names.
  - The contract changes COR-010's migration rule and core rule 5, for every future script.
  - **Its cost:** every adopter's first upgrade runs eight scripts. Three of them can re-add what a project removed after they ran.
- **Alternative:** a missing key means complete. A stranded project recovers by a command that runs the backbone migrations from a version its operator names, which the changelog explains.
  - **Its cost:** a project stays stranded unless its operator learns it. Each script can tell its own state from the files, but nothing tells the operator which scripts to run.

### 4. How does a transition meet a new collision?

- **The question:** a release's capability ships a skill whose name a project's own skill already uses. What does the transition do?
- **Example:** a project wrote `.pkit/skills/project/release.md`, and the next release of project-management ships a skill named `release`. Today sync copies it in, and nothing asks.
- **Recommended:** the transition resolves it with COR-017's install-time flow, override, skip or inspect for each artefact, and records the skips. With nobody to answer, it refuses before writing anything and names a terminal re-run or a rename.
  - Every component stays at one release, and `pkit capabilities upgrade --interactive` is no longer needed for this.
  - **Its cost:** a transition in a pipeline refuses while a collision is open, and COR-017's sentence on sync's collision refusal is superseded by a different flow.
- **Alternative:** the transition holds that capability back at its old version and reports it, and the project resolves it later with `pkit capabilities upgrade X --interactive`.
  - **Its cost:** a project mixes two releases. Every gate needs COR-030's warn-and-override disposition to avoid a hard block. And the interactive upgrade must be allowed past sync's guard, or the two remedies point at each other.

### 5. Does merge stay in sync?

- **The question:** should sync keep running the merge primitives, which write `.claude/settings.json` and `CLAUDE.md`?
- **Example:** a project adds an allow entry to its settings additions, or writes a skill under `.pkit/skills/project/`, and runs `pkit sync`. Merge puts the entry, or the skill's `Skill(<name>)` grant, into `.claude/settings.json`.
- **Recommended:** merge stays in sync, in its auto-add tier, the only tier it has built. It is merge delivery (COR-002), a writer the named-writer principle names, and it regenerates what COR-010 calls derivable.
  - COR-002's list of merge points gains sync, refined in place.
  - COR-004's "`sync` and `merge` stay separate" decides they are different verbs "because they encode different consent". The new record partially supersedes it: sync carries merge's auto-add tier, which only appends, and a prompting tier runs only where a person can answer.
  - **Its cost:** sync writes two project-owned files, so the decision's "writes no project-owned path" is false for them, and COR-001, COR-002 and COR-004 change.
- **Alternative:** merge leaves sync, and runs at init, in a transition, at a capability's install or upgrade, and on `pkit merge`.
  - **Its cost:** every edit to a project's settings additions and every new project skill needs `pkit merge`, against core rule 6's workflow and the adapter's README. project-kit's maintainers need it for every new core skill.

### 6. Which command creates a missing seed path?

- **The question:** after install, which command may write a seed path the project does not have?
- **Example:** delete `.pkit/agents/project/overlay.yaml` and run `pkit sync`, and the seed comes back. COR-001 says a seeded path is written once, at first install, and "Subsequent syncs do not touch this path".
- **Recommended:** the transition creates a declared seed path that is missing, and never writes over one that exists. Sync creates none.
  - New areas and new seed paths arrive only with a transition, since sync runs at the recorded version. So all sync's seed creation would still do is repair a seed the project deleted.
  - A deleted seed is repaired by the command that needs it: `pkit agents reconcile --write` writes a missing overlay.
  - Sync then writes project-owned paths through merge alone, and COR-001's "Subsequent syncs do not touch this path" holds for sync.
  - **Its cost:** COR-001's seeding cadence is partially superseded for the transition, which also re-creates a seed the project deleted on purpose. COR-004's `init` rationale on resurfacing seeded content changes with it.
- **Alternative:** sync and the transition both create a missing seed path.
  - **Its cost:** COR-001's cadence is superseded for sync too, and a seed the project deleted on purpose returns on every sync.

### 7. Do `pkit capabilities install` and `upgrade` stop on a version mismatch?

- **The question:** should the two commands call sync's guard?
- **Example:** an unpinned project at 1.149 with a 1.152 pkit runs `pkit capabilities install living-docs`. It gets 1.152's living-docs beside 1.149's backbone, a mix no release shipped.
- **Recommended:** yes, with sync's remedies. Every shipped file a project holds then comes from one release.
  - **Its cost:** someone with a newer pkit pins or upgrades before installing a capability, and on a floating install meets it at every release.
- **Alternative:** they keep copying from the running pkit, checked only by `requires_backbone`.
  - **Its cost:** mixes no test covers, and a capability whose migrations assume a backbone the project never moved to.

### 8. Where does this build fall against the conversion build?

- **The question:** #1429's build comes after #1410 and before #1444. Does it also come before #1435 to #1442?
- **Example:** #1435 adds the newer direction to sync's guard if this build has not yet, and #1438 and #1440 edit upgrade's messages and status, which this build also edits.
- **Recommended:** before #1435. The conversion command, its status and its reports then build on settled sync and upgrade, and each pair's later issue depends on the earlier.
  - Each slice leaves adopters safe if a release is cut after it ("Slicing").
  - **Its cost:** the conversion build waits for this one.
- **Alternative:** the conversion build first, up to #1442, then this build, then #1444.
  - **Its cost:** #1435 builds the guard's newer direction itself, and three pairs of issues edit the same code twice.

### 9. Which changeset segments?

- **The question:** two slices change what adopters see. The sync change stops a command that worked, and the replay runs eight scripts on every adopter's first upgrade. Minor or major?
- **Example:** an unpinned project's pipeline runs `pkit sync` with the latest pkit. It passes today and fails after the change.
- **Recommended:** minor for each, with a changelog entry under "Changed" that names the pipeline impact and the recipe: commit a pin, or install the project's version in the pipeline.
  - Projects upgraded since 1.145.0 are pinned by default, and see no change while their pin can be fetched.
  - **Its cost:** a command that worked fails, under a minor number. That includes a pinned project whose pipeline installs a newer pkit over HTTPS: the router's fetch over SSH fails there, so the pipeline falls back and stops.
- **Alternative:** major for the sync change, since a working command now fails and COR-017's contract inverts.
  - **Its cost:** a major number for a change most adopters do not see.

### 10. What does a version name for an untagged install?

- **The question:** how is sync's check made honest when the running pkit was installed from no tag?
- **Example:** main's head carries the `1.150.0/` backbone scripts while its `VERSION` reads 1.149.0. A project upgraded with it gets 1.150-era files, and its migrations stop at 1.149.0, so `completed_version` reads 1.149.0 over files that need the 1.150 scripts.
- **Recommended:** the realising ADR states that a version identifies content only for a tagged install. The recommended install becomes tagged: init prints `@v<its own version>`, the CLI reference follows, and #1376's test keeps the two equal.
  - **Its cost:** the printed command names a version that ages, an untagged install stays possible and unchecked, and a component-only release reaches a tagged project only with the next backbone tag.
- **Alternative:** an untagged build stamps a development version, such as `1.149.0+g<sha>`, so it never equals a project's recorded version.
  - **Its cost:** every untagged install meets the stop in every project, and the router reads such a version as unordered.

## Settled positions this reopens

Each accepted sentence below changes, for the maintainer's authorisation. Items 8, 9 and 10 change under the recommended answers to questions 5 and 6, and the rest under the design itself.

1. **COR-017, "Lifecycle: install, sync, uninstall":** "**Sync** (`pkit sync`) auto-upgrades installed capabilities along with the rest of kit content." and "When sync would introduce a new collision [...], sync refuses to upgrade that specific capability and instructs the adopter to run `pkit capabilities upgrade X --interactive` to resolve."
   - **The change:** partially superseded. A version transition moves the capabilities and resolves a new collision with the install-time flow (question 4). Sync keeps a capability at its recorded version.
   - **With it:** the section's "Capabilities have an explicit install / sync / uninstall lifecycle", the implication "**Sync extension** — refreshes installed capabilities; surfaces no-longer-shipped capabilities; refuses upgrade on new collisions.", and the Rationale's "The skipped-artifact records persist in the manifest so sync respects them", which the code does not do today.
   - **Also:** its Implications list `pkit capabilities upgrade <name> [--interactive]`. Under question 7 it finishes one component at the project's recorded backbone.
2. **COR-004, "Each command anchors to one mechanism or operation":** "Compound verbs (e.g., an "update" that does sync + merge + migrations) hide which contract is being invoked, conflate consent profiles, and resist the manifest-level reasoning the install/sync runtime needs." Also its rejected alternative, "One smart `update` verb that picks sync / merge / migration as needed."
   - **The change:** partially superseded (question 2). What stays rejected is a verb whose consent depends on what it finds.
   - **With it, refined in place:** "A command performs one of: propagation, seed, merge, suspension management, validation, or read-only introspection." gains the version transition.
3. **COR-004, "Failure mode is forward-only":** "A failed run leaves the project at a known partial state, with `validate` as the recovery entry point." Also "`init` is one-shot": "Recovery from partial or broken state flows through `validate` plus targeted `sync` / `merge` instead."
   - **The change:** refined. An interrupted transition is finished by the next one, and sync names it.
4. **COR-010, "Lifecycle operations apply uniformly", item 3:** "**Update** — re-running the setup primitive reconciles installed state with the current version's spec."
   - **The change:** refined. The setup primitive runs at the recorded versions. It moves no recorded version and runs no migration.
5. **COR-010, "Cross-tier upgrade requires explicit compatibility resolution":** "The reconciliation order — compatibility resolution → propagation → backbone migrations → component migrations → derivable-state reconciliation → recorded-version updates".
   - **The change:** refined. A transition records its target before it writes anything and its completion last, and renders the ignore file after propagation.
6. **COR-010, "Two tiers":** independent versioning "lets adopters upgrade selectively".
   - **The change:** refined. A transition moves every component its release ships, and selective movement remains for an externally-sourced capability.
7. **COR-010, "Migrations are mandatory on adopter-breaking surface changes":** "The migration is idempotent (already-applied state is a no-op) so adopters can re-run safely." Also its Alternatives: "Recording the version plus idempotent re-runs prevents this." And core rule 5, "it must be safe to re-run on already-migrated state".
   - **The change:** refined. A backbone migration also acts only on a positive sign that its change is needed, so a replay over any state is safe (question 3).
8. **COR-004, "`sync` and `merge` stay separate":** "They are different verbs because they encode different consent."
   - **The change, under question 5:** partially superseded. Sync carries merge's auto-add tier, which only appends, and a prompting tier runs only where a person can answer.
9. **COR-002, "Merge runs at three points":** "First install", "Manually on demand", "During upgrade flows".
   - **The change, under question 5:** refined in place. Sync is a fourth point, in the auto-add tier.
10. **COR-001:**
    - "Extension": "project-owned paths are not touched by sync". **Under question 5,** refined: touched by sync only through merge delivery.
    - "Install-time seeding": "written exactly once, at first install. Subsequent syncs do not touch this path." Its Implications: "Subsequent syncs run propagation only." and "Seeded extension artifacts are project-owned after first install. Core makes no further claim on them." Its Rationale, "Why install-time seeding is not a fourth mechanism", rests on seeding being one event. **Under question 6,** partially superseded for the transition, which creates a missing seed. Sync still creates none.
    - **With it:** COR-004's "`init` is one-shot" rationale, that re-running first install would "resurface seeded content (violating COR-001's seed contract)".
11. **COR-048 point 1:** "It survives upgrade, sync, and uninstalling any capability or the tool itself, because none of them writes or removes it."
    - **The change:** refined in place. None of them removes it, and an upgrade writes it only through the migrations point 5 names. Sync no longer writes it at all.
12. **ADR-049 point 1:** "the recovery is to **re-run** the reconcile / `upgrade`, which is idempotent (sync re-applies content, migrations detect already-applied state and no-op per COR-010, and the pin flip is a no-op once it matches)". Also its Implications on upgrade, "a mid-migration interruption is recovered by an idempotent re-run", and "A raise runs the *target* version's sync".
    - **The change:** refined in place. A re-run finishes the transition the manifest shows incomplete. The pin still flips last, with no two-phase commit.
13. **ADR-049, Context and Rationale:** "`backbone_version` is written unconditionally by every `sync`", and "`backbone_version` is a **record** (a receipt of the last sync)". Also point 3: `pkit pin` with no argument "freezes the project at its current content version (`manifest.yaml`'s `backbone_version`)".
    - **The change:** refined in place. Sync no longer writes `backbone_version`. It is the receipt of the last transition's target, ahead of the files while a transition is incomplete. A pin frozen then names the target, whose code finishes the transition. The rejection of `backbone_version` as the pin still stands on its other reasons.
14. **ADR-049's amendment:** "an **unresolvable pin degrades loudly to running self**, never a hard fail — so a pinned project never bricks offline".
    - **The change:** refined by #1401's fold of the amendment, or by the ADR after it. The router still degrades, and sync and upgrade refuse to write under the pkit it degrades to, in both directions.
15. **ADR-044 D1:** an unreachable release source "degrades loudly and continues with today's behaviour — sync the project from the current bundle".
    - **The change:** wording only. It continues with the transition to the current bundle's version. Its Implications and its amendment say the same.
16. **The decisions README, "The no-shared-files invariant":** "project-owned paths are never read or written by sync." and "Sync **cannot** produce a conflict. You can run it whenever you like — it cannot break anything you wrote."
    - **The change:** sync writes project-owned paths only through merge delivery, and it reads the manifest. Sync still cannot produce a conflict, but it stops when the running pkit is not the project's. #1432 may make part of the change first.

## Corrections to the first reviews

The critic and the architect reviewed the bare direction on 10 October. Where this design's reading of the code differs:

- **The adapters' recovery:** the architect expected adapters to recover by a per-component check. No adapter has a record to check, and no adapter migration has ever run ("Where migrations strand").
- **Older code:** the architect's case for writing the target first rests on #1212's guard. It holds only from the release that ships #1212, since no released pkit has it.
- **A missing key:** the architect read a missing completion key as equal for sync. It reads as incomplete here. No project at the new release's content lacks it, and "equal" would let sync run over an interrupted first upgrade.
- **The replay:** both reviews rest it on idempotence. A replay also runs scripts on states that never needed them, so it needs a stronger contract. The audit found two scripts that delete a project's files by name, one that deletes by position, and three that can re-add a project's removals.
- **ADR-049:** the architect proposed partial supersession. Point 1's decision stands and only a fact was false, so the decisions README calls for a refinement in place. Its amendment is #1401's.
- **The migration order:** the architect put derivable state after every migration. `1.150.0/001-untrack-runtime-ignored-files` reads the render made after propagation, so the render comes then and again at the end.
- **Merge:** both reviews took merge out of sync. Merge reads the project's own settings additions and skills, so taking it out breaks a working workflow. Question 5 recommends keeping it.
- **Collision refusal:** the first critic found it unbuilt. It is unbuilt in sync's refresh only. `pkit capabilities upgrade` has it.
- **The scripts:** seven backbone version directories hold eight scripts.

## Alternatives weighed

- **Sync runs at the recorded version by fetching it** (`run_bypassed` from sync). Not taken: a fetch at sync time is what ADR-033 rejected, the pin already routes every command, and offline it still stops.
- **Sync moves content but records no version.** Not taken: it breaks ADR-033's tie of content to code, and a capability's files would move without their migrations.
- **Skip per component without the backbone stop.** Taken inside a sync that proceeds. Without the backbone stop, a newer pkit would still copy its backbone files over older ones.
- **A ledger of migrations that ran.** Not taken: it drifts from the files and conflicts across branches, and COR-010 keys migrations on versions.
- **The completion key written right after the backbone migrations,** with completion read from every component's record too. Not taken: sync could then run over a capability whose files moved and whose migrations had not, and re-running the backbone window is cheap.
- **A curated replay,** only the scripts each declares safe. Not taken now: with two scripts rewritten, all eight meet the contract, and a declaration format would carry one bit no script needs.
- **The transition names `pkit merge` and does not run it.** Not taken: new safety entries and baselines would arrive only when someone runs it.
- **A capability's record kept at its root, out of the copy by a new rule.** Not taken: a file-level exception inside a methodology-owned root forks the ownership predicates, and `project/` already answers.
- **Pin at `pkit init`.** Not proposed: it reopens ADR-049 point 2 and puts every new project on the router's `uvx` path from its first command. It would make the unpinned stop rarer.
- **A deploy-only mode by default on a mismatch.** Not taken: a zero exit would let a pipeline hide the skew the stop exists to show.

## Slicing

A draft of the build issues, for filing after the maintainer decides. Each record is accepted before the work that cites it, and each slice leaves adopters safe if a release is cut after it.

- **B0, [Task] the stop-gap, for the next release** (question 1), filed as #1452: the sync command, at its entry point, refuses to move `backbone_version` past a version directory holding backbone migrations, and names `pkit upgrade`. `run_upgrade`'s call to `run_sync` is not touched. Needs no record: COR-010's order already puts recorded versions after migrations.
- **R1, [Docs] the core record and the refinements:**
  - the new core record through the decision-author skill, partially superseding COR-017's sync paragraph, COR-004's compound-verb sentence and, as questions 5 and 6 decide, its sync-and-merge paragraph and COR-001's seeding cadence
  - COR-001, COR-002, COR-004's operation list, COR-010 and COR-048 point 1 refined, the decisions README's lines, core rule 5 and the migration-author skill's contract
  - a `none` changeset, as #1431's
  - **Shared with #1431 and #1432:** whichever lands first carries COR-001's principle, and the other adds its instance. COR-004's list gains both operations in place.
- **R2, [Docs] the realising ADR, by the architect,** after R1 only. No changeset.
- **R3, [Docs] ADR-049 and ADR-044 refined,** after #1401, which folds ADR-049's amendment, and in step with #1433, which refines ADR-049's rollback and whose text names a supersession this design does not make.
- **B1, [Task] a capability's record under its `project/`:**
  - the code that writes the record moves it, reads both places, and rewrites the registry path
  - skips read from where they are written, and a restamp that keeps `backend_state`
  - every record read before propagation
  - **Safe alone:** it fixes the lost skips today, and changes nothing else a project sees
- **B2, [Task] a transition records its target first and its completion last:**
  - the manifest key, written by init and by the release step in project-kit's own manifest
  - adapter records written at their bundled version, with no migration
  - the early return keyed on every recorded version
  - the backbone window from `completed_version`
  - a missing manifest or a broken version seeded by upgrade, and the messages that named sync
  - the replay for a missing key, with `1.31.0/001` and `1.0.0/001` rewritten first and the fixtures
  - status showing an incomplete transition. **Names #1436 and #1440,** which extend status too
  - **Safe alone:** a sync under this code still moves `backbone_version` and leaves the completion key, so the next upgrade finds them apart and finishes the migrations
  - **Docs:** the lifecycle README's manifest format and upgrade flow
- **B3, [Task] sync never moves a version:**
  - the propagation step split from the sync command
  - the guard on the sync command in both directions and on an incomplete transition, refusing under `--dry-run`, with a message per state. Upgrade keeps the older direction only
  - a capability copied at its recorded version only, others skipped and reported, an externally-sourced one skipped by origin, adapters copied with the backbone
  - no manifest write, no seed and no migration in sync
  - upgrade calls the step and runs each capability's migrations itself, after the copy, with project-management's `0.15.0/001` and `0.24.0/001` fixed for that order
  - `--force` accepted and ignored for one release, with a guidance migration
  - **Names #1435:** the shared guard. Whichever lands second depends on the first.
  - **Docs:** the CLI reference's `sync`, `init` recovery and `pin` entries, and the lifecycle README's "No path down". The changeset segment is question 9's.
- **B4, [Task] every migration in COR-010's order:**
  - backbone, then adapters from the bundle, then capabilities in dependency order, then merge and the rest
  - `install._install_adapter`'s copy set reviewed, `permission-enforcement.yaml` included, and a release's new adapter registered
  - a new collision resolved inside the transition, and the gates with their override
  - `pkit capabilities upgrade` as a transition of one component
  - the dependency check on the versions installed, after #1410
  - **Docs:** the lifecycle README's upgrade flow and per-component upgrade
- **B5, [Task] the pinned flows:** the routed child finishes its own pin, offline included, and upgrade refuses under the router's fallback. After R3. **Names #1438,** which rewrites upgrade's and sync's messages too.
- **B6, [Task] capability install and upgrade use sync's guard,** if question 7 is answered yes.
- **B7, [Task] the recommended install is tagged,** as question 10 decides.
- **Later:** `--force` removed, a release after B3.

**Order:** B0 in the next release. Then #1410, R1, R2, B1 to B4, R3, B5 to B7, and then, under question 8's recommendation, the conversion build from #1435 to #1444. B1 comes before B2 and B3, since both read a capability's record.

## Found on the way

1. **Adapter migrations have never run in an adopter.** `install._install_adapter` copies no `migrations/`, and no code writes an adapter's per-component manifest. Taken by B2 and B4.
2. **`install._install_adapter` never copies `permission-enforcement.yaml` either.** `permissions.py` reads it from the project, so in an adopter the line naming dimensions no native layer enforces is always empty. Taken by B4.
3. **A capability's record is deleted or overwritten by every refresh,** and project-management's bundle ships project-kit's own. The restamp hides it today. Taken by B1.
4. **A capability's skips are never read back:** written to `manifest.yaml` under `backend_state.skipped`, read from `component-manifest.yaml` under `skipped_artifacts`. Every sync copies skipped artefacts back in. Taken by B1.
5. **A restamp replaces a component's `backend_state` whole,** which would lose the opaque identifiers COR-010 says a manifest keeps. Taken by B1.
6. **The next release ships two `1.150.0/` migrations, and a sync strands them** for an unpinned project. The journal one matters: logging stops silently. Question 1.
7. **#1212 is unreleased.** Every released pkit writes its older content over a newer project. The protection this design leans on starts with the next release.
8. **Upgrade under the router's fallback raises the pin to the installed version,** not to the latest release ADR-049 point 3 names. Taken by B5.
9. **A pinned project whose installed pkit equals its pin** runs `pkit upgrade` as itself, not as the routed child. Without a terminal it reports "Already at backbone" and does not advance, while ADR-049 point 5 says a pinned upgrade advances with no `uv` step.
10. **COR-048 point 1 says an upgrade never writes the configuration file.** Point 5 lets an upgrade migration write it, and `1.150.0/001-keep-process-journal-logging` and project-management's `0.55.0/004` do.
11. **COR-010's Context says COR-004 "names the upgrade command".** COR-004 names no upgrade.
12. **The CLI reference contradicts the code and itself:**
    - its `upgrade` entry says migrations run "then runs `sync`", while the code runs sync first
    - it says an unpinned upgrade writes "no pin file", while upgrade pins by default
    - its `sync` entry says sync does not invoke merge, while the claude-code adapter's README and the code say it does
13. **`_sync_installed_capabilities` treats an externally-sourced registration as shipped.** It refreshes it from the bundle when the methodology ships a capability of that name, and reports it orphaned otherwise. Taken by B3.
14. **A capability refresh with no readable version runs every shipped migration,** when both its record and its installed `package.yaml` fail to read. project-management's `0.54.0/001` is among them, which grandfathers a bootstrap that may never have happened. B3 ends it in sync.
15. **The lifecycle README says "a corrupt `backbone_version` is one sync repairs".** Sync repairs it by recording the running pkit's version, whatever the files hold.
16. **Read-only commands under another release stay silent.** `pkit validate` with a newer pkit judges older content by newer rules, which ADR-049's Rationale calls the worst case. #1436 reports that mismatch in status and validation.
17. **Commands that write a project's files in the running release's format** (`pkit new`, `pkit config set`, `pkit agents reconcile --write`, `pkit permissions apply`, `pkit visibility`) are not guarded. A follow-up decides whether they stop.
18. **Stale texts the build rewrites:** `1.54.0/001`'s skip text, "install/sync seeds a complete one", and `1.150.0/001-untrack-runtime-ignored-files`'s header, which reasons from "sync has already recorded the new version".
19. **ADR-049's amendment says it owes a successor record,** "a successor record is owed", while #1401 plans to fold it in place. That is #1401's question, but R3 and settled position 14 depend on its answer.

## Review

### The critic, round 1

The critic found the design sound: the split, the target written first, and a remedy per state. Its three red flags were the capability's record lost to the copy, a false premise in the merge question, and deleting scripts the replay audit missed. Each finding below is answered, numbered as the critic numbered them. Where the architect's round then changed an answer, the answer says so.

**Red flags:**

1. **The copy deletes or overwrites a capability's record.** **Answer:** accepted, verified in `treecopy.refresh_owned_tree` and project-management's shipped `manifest.yaml`. The architect's round then moved the record under `project/` (its finding 9).
2. **Question 5's premise was false:** merge reads the project's settings additions, project skills and capability overlays. **Answer:** accepted. The recommendation flips: merge stays in sync in its auto-add tier, as a named writer.
3. **The replay audit missed two deleting scripts, and a fresh-install test catches none of the risks.** **Answer:** accepted. `1.31.0/001` and `1.0.0/001` are rewritten before the replay ships, the contract becomes "act only on a positive sign", and fixtures hold each failure.

**Factual errors:**

4. **The fallback upgrade takes "the path that is not the routed child", not the unpinned path.** **Answer:** fixed.
5. **The capability record's row said "the project's".** **Answer:** fixed: the project's record, in a position the copy manages.
6. **The capability-order audit was wrong for four scripts.** **Answer:** accepted. The audit names the three workflow scripts and `0.54.0/001`, and B3 fixes `0.15.0/001` and `0.24.0/001`.
7. **The first draft's claim that the two `1.150.0/` migrations interfere was overstated:** keep-journal removes the journal line itself. **Answer:** accepted, and the item is gone. The order still renders after propagation, since untrack reads that render.
8. **The unread-version replay needs both the record and `package.yaml` unreadable.** **Answer:** fixed, Found 14.
9. **The deploy-only cost:** `.pkit/.gitignore` is committed in shared mode. **Answer:** fixed. The architect's round then settled the mode in the design.
10. **ADR-049 point 5 governs the routed child, not the fallback.** **Answer:** accepted. The refusal rests on point 3, the raise to the latest release, and on #1212's precedent.
11. **The gate also reads the pin in the older direction.** **Answer:** fixed in "On a mismatch".
12. **The build order contradicted itself.** **Answer:** accepted. The order against #1435 to #1442 is question 8.

**Gaps:**

13. **Holding back was not traced against neighbours.** **Answer:** accepted at first, with gates for a held-back capability. The architect's round then found the hold deadlocks, and dropped it (its finding 1).
14. **The missing-record rules differed by layer, and new adapters and new seeds were undefined.** **Answer:** accepted. "Every adapter" means the registered ones, adapters move with the backbone, a missing adapter record is written at the bundled version with no migration, and a new seed arrives with the transition (question 6).
15. **The set of guarded commands was open-ended.** **Answer:** accepted. A criterion: commands that copy methodology content. The rest are a follow-up (Found 17).
16. **project-kit's own manifest would read incomplete for ever.** **Answer:** accepted. The release step writes both keys, and the source is exempt, as #1435 exempts it.
17. **Merge's tier inside the transition was unstated.** **Answer:** accepted. The auto-add tier, and a prompting tier only where a person can answer.
18. **The fallback refusal reopens the amendment's "never bricks offline", and the remedies were thin.** **Answer:** accepted. Settled position 14, the reason ADR-039 D2 is unchanged, and more remedies in the table.
19. **Writing the target first changes what `backbone_version` means.** **Answer:** accepted. Stated in the versions section, and settled position 13.
20. **The untagged-install question missed the concrete hazard.** **Answer:** accepted. Question 10's example is the `1.150.0/` scripts under a `VERSION` of 1.149.0.
21. **Two Found items were assigned to no slice.** **Answer:** fixed: B4 and B3.
22. **A test in new code cannot hold what released code does, and the completion key can be newer than `backbone_version`.** **Answer:** accepted. The writer's behaviour is traced to the first published commit, and the newer-key case is stated.
23. **The list of messages to change was incomplete.** **Answer:** accepted. The CLI reference's `pin` and `init` lines are in B3, and the two scripts' texts in Found 18.
24. **The stop recurs at every release for a floating install.** **Answer:** accepted. Stated in "On a mismatch" and in question 7's cost.

**Weak reasoning:**

25. **COR-004 should be partially superseded, not refined, and #1394's Decision 2 rationale was not reconciled.** **Answer:** accepted for COR-004's compound-verb sentence (settled position 2). #1394's decision stands. Its phrase that upgrade overwrites "what the methodology owns" understates the migrations, whose writes #1431 limits to carry-overs their owning record names, with running the upgrade as the consent (COR-048 point 5). The new record states why a conversion stays out of the transition.
26. **The reworded COR-004 alternative would reject the transition itself.** **Answer:** accepted. What stays rejected is a verb whose consent depends on what it finds, not one whose actions do.
27. **"Sync writes no project-owned path" rested on an unstated classification.** **Answer:** accepted. "What sync writes" states three kinds once. `.pkit/.gitignore` is described as rendered per project and never shipped, which is how `ownership.py` lists it.
28. **The replay question's alternative was weaker than it need be.** **Answer:** accepted. The alternative's cost now says each script can tell its own state, but nothing tells the operator which to run.

**Counter-alternatives:**

29. **A curated replay.** **Answer:** weighed, not taken now ("Alternatives weighed").
30. **The completion key written right after the backbone migrations.** **Answer:** weighed, not taken.
31. **Key the fallback refusal on `PKIT_PIN_UNRESOLVED`.** **Answer:** taken, with the bypass check.
32. **The transition names `pkit merge` instead of running it.** **Answer:** weighed, not taken. Its stronger form, merge kept in sync, is question 5's recommendation.
33. **A stop-gap in the next release.** **Answer:** taken as question 1 and slice B0.
34. **A development version for untagged builds.** **Answer:** taken as question 10's alternative.

**The questions:**

35. **The order was wrong.** **Answer:** accepted. Merge and seeds come before what depends on them. The architect's round then folded the placement question into question 2.
36. **The first question's alternative was a straw man.** **Answer:** accepted. The alternative is COR-004 unchanged, with a named exception in the realising ADR.
37. **The replay and merge questions presented false costs.** **Answer:** accepted, corrected with findings 2 and 3.
38. **Missing questions:** build order, the record's home, the fallback against "never bricks", one release for the slices, merge's tier. **Answer:** build order is question 8. The record's home was asked, then settled in the design after the architect's round. The fallback is settled position 14. Release safety is answered per slice. Merge's tier is answered in the design.
39. **The `--force` question is small enough for the design.** **Answer:** settled in the design after the architect's round.

**Settled positions:**

40. **Positions were missing.** **Answer:** accepted. Added: COR-004's compound sentence and its sync-and-merge paragraph, its recovery sentences, COR-001's seeding cadence, COR-010's selective upgrades, and ADR-049's Rationale, point 3 and amendment. #1433's text is named in the slicing. The lifecycle README's sentence is a document, rewritten by B4.

**Slicing:**

41. **A release can be cut between the slices.** **Answer:** accepted. Each slice leaves adopters safe, and B1 and B2 say why.
42. **Sync's change depended on the upgrade side.** **Answer:** accepted. The upgrade side, B2, comes before sync's change, B3.
43. **Both slices inherited the record's loss.** **Answer:** accepted. The record's fix is B1, before both.
44. **The acceptance gate is respected.** **Answer:** noted.

**Where the note is right (45 to 52)** and **categories with nothing to flag:** noted. #1432's named-writer principle carries merge delivery as sync's writer in question 5.

### The architect, round 1

The architect found the shape right: the split, target first and completion last, the replay under a stronger contract, a remedy per state, and COR-010's order with the render after propagation. Its three blocking findings were a deadlock in the hold-back, adapters left unsafe between slices, and a seed question that reopened more than it said. It flagged an escalation: COR-001, COR-002, COR-004, COR-010 and COR-017 change. Each finding is answered, numbered as the architect numbered them.

**Blocking:**

1. **The hold-back deadlocks against the capability guard, and its gates make hard blocks where COR-030 and COR-053 forbid them.** **Answer:** accepted. The hold is dropped. A collision is resolved inside the transition with COR-017's install-time flow, or the transition refuses and names a terminal re-run or a rename. The gates keep COR-030's and COR-053's dispositions. This is question 4.
2. **Adapters were unsafe between slices.** **Answer:** accepted. Adapters move with the backbone in sync, a missing adapter record reads as at the backbone, and B2 writes the records.
3. **The seed question reopened more than COR-001's cadence sentence, and its argument belonged to the transition.** **Answer:** accepted. Question 6 now recommends seeds in the transition only, so sync's one writer is merge. The three passages and COR-004's `init` rationale are in settled position 10.

**Should change:**

4. **COR-002 was missing.** **Answer:** accepted. Settled position 9, and "The records it changes".
5. **COR-004's operation list collides with #1394's.** **Answer:** accepted. The list is refined in place with both operations, and the new record supersedes only the compound-verb sentence and the "smart `update`" alternative. It states why a conversion stays out of the transition.
6. **COR-004's sync-and-merge paragraph is nearer a supersession.** **Answer:** accepted. Under question 5's recommendation it is partially superseded, settled position 8.
7. **The replay's stronger contract had no home.** **Answer:** accepted. COR-010's migration rule, core rule 5, the script contract and the skill, landed with R1. A migration may now fail loudly.
8. **Name the stuck state.** **Answer:** accepted. The "Transition incomplete" row names both ways out.
9. **The record's home: the alternative needs no ownership change.** **Answer:** accepted. The record moves under `project/`, and the question is settled in the design.
10. **Skips are never read back, and a restamp wipes `backend_state`.** **Answer:** accepted, verified. Found 4 and 5, slice B1, and COR-017's sentence on skips in settled position 1.
11. **The stop-gap must not fire inside upgrade.** **Answer:** accepted. B0 and B3's guard sit at the sync command's entry point. Upgrade keeps the older direction only.
12. **The boundary between B3 and B4 on capability order was unclear.** **Answer:** accepted. B3 runs capability migrations after the copy and carries the two script fixes.
13. **The core record should not say read-only commands still run.** **Answer:** accepted. It says only what stops.
14. **The tool self-update conflicts with COR-004 as the rejected alternative does.** **Answer:** accepted. The new record says COR-004's rule governs operations on a project, and a command may first update the tool that runs it.
15. **Settled positions still missing.** **Answer:** accepted. ADR-049's Context and Rationale, the decisions README's "cannot produce a conflict", and COR-017's `capabilities upgrade` implication are added.
16. **The fallback remedy was circular for a pipeline without keys, and the changeset cost was incomplete.** **Answer:** accepted. The row names the repository's HTTPS URL, and question 9's cost counts pinned pipelines that install over HTTPS.

**Could change:**

17. **Shorten and reorder the questions.** **Answer:** taken. Two recorded states, the record's home, deploy-only and `--force` are settled in the design. Placement is folded into question 2, the stop-gap is first, and the collision question is added. Ten questions remain.
18. **One rule for derivable state in a transition.** **Answer:** taken. Only the ignore render runs after propagation, and deploy, merge, the workspace and provisioning run at the end.
19. **`1.32.0/001` deletes by position.** **Answer:** taken, with a fixture.
20. **What per-component records buy under tagged installs.** **Answer:** taken, in the versions section and question 10's cost.
21. **Registering a release's new adapter carries today's behaviour.** **Answer:** taken, stated so.
22. **Ignoring `--force` changes the flag's meaning.** **Answer:** taken. B3 ships a guidance migration.
23. **Changesets per slice.** **Answer:** taken. Question 9 covers the sync change and the replay.
24. **Decouple R2.** **Answer:** taken. R2 is the new ADR after R1, and R3 refines ADR-049 and ADR-044 after #1401, with B5 after R3.
25. **Wording in the core record.** **Answer:** taken: "a component the methodology ships", "version transition" in the title, and `completed_version` as the key's provisional name.

**Escalations (26 to 31):** each is in "Settled positions this reopens", for the maintainer's authorisation. The ADR-049 amendment's successor is #1401's question, recorded as Found 19.

**Where the note is right (32 to 45):** noted.
