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
- **Its build** is ordered after #1410 and before #1444, as the maintainer set. Where it falls against #1435 to #1442 is question 10. It shares the version guard with #1435, the messages of upgrade and sync with #1438, and status with #1436 and #1440.
- **Reviewed:** by the critic, whose findings and answers are in "Review". The architect's review follows.

## The question

How does a project move from one version to the next so that every migration runs exactly where the move happens, and nothing else moves a version?

## In short

`pkit sync` keeps a project in line with the release it records. `pkit upgrade` is the one operation that moves the recorded versions, and it runs every migration.

- **One propagation step, two callers:** sync runs it at the project's version, and upgrade at its target. The stop on a version mismatch belongs to the sync command, never to the step.
- **What sync writes:** methodology files, state it regenerates from the project's own declarations, and, through the two writers records name, merge delivery and a missing seed. Never a version, the manifest or a migration (questions 5 and 6).
- **A version per component:** the backbone and each adapter and kit-shipped capability. Sync checks the backbone's, and skips and reports a component whose bundled version differs. A capability's record is kept out of the copy (question 3).
- **Two recorded states:** an upgrade records its target before it writes anything and its completion last. The next upgrade finishes an interrupted one, and a newer release's content stops an older pkit.
- **Recovery:** a project whose backbone migrations were stranded runs them all once, on its first upgrade under the new release, under a stronger script contract (question 4).
- **A stop that names the remedy:** each state of a mismatch has its own remedy. `pkit upgrade` is wrong in two of them.
- **Every migration inside the transition,** in COR-010's order: backbone, then adapters, then capabilities in dependency order.
- **Records:** a new core record holds the principle and partially supersedes COR-017 and COR-004's anchoring paragraph. COR-001, COR-010 and COR-048 point 1 are refined, and ADR-049's recovery claim is corrected in place.

## The direction, and what its wording claims

The maintainer's comment of 10 October on PR #1395 decided:

> Sync makes the project match the pkit that runs it at the project's version: it restores the methodology's files, re-wires the harness, recreates the workspace and provisions query commands. It runs no migration and writes no project-owned path, so COR-001's extension contract stays true as written. When the running pkit is newer than the project's content, sync stops and names pkit upgrade, as it already stops when pkit is older (#1212). Only upgrade moves versions, and every migration, backbone and capability, runs there. [...] Pinned projects, the default, see no change.

The direction stands. A later comment the same day left the wording of what sync writes to this design. Two claims in the wording do not hold:

- **"Writes no project-owned path":** sync writes `.claude/settings.json` and `CLAUDE.md` through the merge primitives, recreates missing seed paths and writes the manifest. The design takes out the manifest. It keeps merge and seed creation, since project workflows rest on them, and names them as writers (questions 5 and 6). COR-001's extension contract is then refined, not kept as written.
- **"Pinned projects, the default, see no change":**
  - **Pinning is the default only after an upgrade.** `pkit init` writes no pin (ADR-049 point 2, `install.install_kit`). An upgrade pins by default (ADR-049's amendment).
  - **Some pinned projects do see a change,** and it is a fix. Under the router's offline fallback, or with content behind its pin, sync moves content past the pin today. After the change it stops ("On a mismatch").

## Today

### Every path that moves a version

- **`pkit sync`** (`sync.run_sync`):
  - copies the running pkit's methodology trees over the project's
  - refreshes each kit-shipped capability through `capabilities.refresh_capability`, which runs the capability's pending migrations, copies its tree and restamps its record
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

### A capability's record sits inside the tree the copy refreshes

- **Where it is:** `.pkit/capabilities/<name>/manifest.yaml`, written by `capabilities._stamp_component_manifest`. That is outside the capability's `project/`, the only part the copy protects (`capabilities._capability_owned`).
- **What the copy does to it:** `treecopy.refresh_owned_tree` deletes every unprotected file the source does not ship. So each refresh deletes the record, and `refresh_capability` writes it again at once.
- **project-management ships one:** project-kit's own `manifest.yaml` for it is in the bundle, since the ownership predicates do not withhold it. A refresh copies it over the adopter's record, skipped artefacts included, and the restamp then rewrites it.
- **Why it matters here:** a copy that does not restamp, which is what sync's copy becomes, loses each capability's record and the skips `read_prior_skipped_artifacts` reads.
- **COR-010's Implications** say a per-component manifest lives in "its component's project-side directory". An adapter's does, a capability's does not.

### What sync writes

| What | Whose | How today |
|---|---|---|
| `.pkit/<area>/core/`, flat area files, adapters, `cli/pkit` | the methodology's | copied over (`install._install_area`) |
| each kit-shipped capability's tree, except its `project/` | the methodology's | copied, after its migrations |
| a capability's `manifest.yaml` | the project's record, in a position the methodology's copy manages | deleted or overwritten by the copy, then restamped |
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
- **Merge inside sync contradicts two documents.** COR-004 keeps sync and merge apart for their consent profiles ("`sync` and `merge` stay separate"). The CLI reference says sync "Does **not** invoke seed [...] or merge". The claude-code adapter's README says the opposite, that sync runs both merge primitives.
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
- **Component-only releases cut no tag** (`.pkit/release/README.md`, "A component-only release (no backbone move) cuts no tag").
- **Untagged installs:** `pkit init` recommends `uv tool install git+ssh://…/project-kit.git` with no tag (`install._print_next_steps`, the CLI reference's "Installing pkit on PATH"). That installs main's head. Its `VERSION` is the last release's, while its files may be newer. Today main's head carries the `1.150.0/` backbone scripts beside a `VERSION` of 1.149.0.

## Forces

- **The maintainer's direction:** sync moves no version and runs no migration, and upgrade runs every migration.
- **COR-010's order:** compatibility, propagation, backbone migrations, component migrations, derivable state, recorded versions.
- **COR-004's consent rule:** one command, one operation. Upgrade today anchors to no operation on COR-004's list.
- **Older code meets newer state.** A pinned project's next command may run an older release's code over what a newer one left. Only state that older code already reads stops it.
- **Working workflows.** A project edits its settings additions and runs sync (core rule 6). A pipeline runs `pkit sync` on checkout, before its gate (the lifecycle README, "How dependencies are provisioned before an offline run").
- **Offline use.** "A degraded-but-running command beats a broken one" (ADR-039 D2).
- **Idempotence.** COR-010 promises "already-applied state is a no-op". Recovery that re-runs scripts leans on it, and on more.

## The design

### One propagation step, two callers

`run_sync` splits into a propagation step and the sync command. Upgrade calls the step, never the command, so the stop never fires inside an upgrade (the first critic's first red flag, removed by construction).

| | `pkit sync` | the version transition's step |
|---|---|---|
| Content | the running pkit's, which must be the project's recorded version | the running pkit's, which is the target |
| Guard | stops unless the running version is the recorded one and the last transition completed | refuses an older running pkit (#1212) |
| Methodology trees | copied | copied |
| A kit-shipped capability | copied when its bundled version is the recorded one, else skipped and reported | copied, unless held back |
| A capability's record | never touched by the copy | never touched by the copy, restamped after its migrations |
| Merge delivery | its auto-add tier (question 5) | its auto-add tier |
| Seeds | created where missing (question 6) | created where missing |
| Migrations | never | backbone, adapters, capabilities |
| Recorded versions | none written | target first, completion last |
| Derivable state | regenerated | regenerated, after propagation and again at the end |

- **The self-host branch comes first in both,** as today (ADR-059 point 2). It runs the deploy and merge primitives, the ignore render, the workspace and provisioning.
- **The step checks no version and runs no migration.** Each caller does what the table says around it.
- **The stop's message names the remedy** for the state it finds ("On a mismatch").

### What sync writes

After the change, sync writes three kinds of thing and no other.

- **Methodology content:** the methodology's trees, and each kit-shipped capability at its recorded version, its `project/` and its record left alone.
- **State it regenerates from the project's own declarations,** which COR-010 calls derivable ("Manifest content: non-derivable state only"): the deployed harness, `.pkit/.gitignore`, the agent workspace and its line in `.git/info/exclude`, and the query commands' environments.
- **Project-owned paths, through two named writers only:**
  - **merge delivery** (COR-002), in its auto-add tier, into `.claude/settings.json` and `CLAUDE.md`. COR-010 lists "merged-config permission entries" among derivable state.
  - **a missing seed path,** created and never written over (question 6)
- **No longer:** any write to the manifest, any version, any migration.
- **A tier merge has not built,** COR-002's prompt-once tier, runs only where a person can answer: `pkit merge`, `pkit init`, and a transition run on a terminal. Without one it writes nothing, as COR-048 point 5 sets for a configuration key.
- **What this makes of COR-001:** its "project-owned paths are not touched by sync" becomes "touched by sync only through merge delivery and a missing seed". #1432's named-writer principle carries it, with "never reads" dropped, since validation reads.

### The versions a project records, and what current means

| Component | Recorded in | Moved by |
|---|---|---|
| backbone, its files | `backbone_version` in `.pkit/manifest.yaml` | a transition, first |
| backbone, its migrations | a new optional key, `migrated_version` (name provisional) | a transition, last |
| each registered adapter | its per-component manifest, written for the first time | a transition, after the adapter's migrations |
| each kit-shipped capability | its record, `.pkit/capabilities/<name>/manifest.yaml`, kept out of the copy | a transition, after the capability's migrations |
| an incubated capability | its own `package.yaml` | the project (COR-031) |
| an externally-sourced capability | its pin (COR-041) | an upgrade, by repointing the pin |

- **`backbone_version` names the methodology files the project holds,** or the target of a transition not yet complete. That second reading is new, and the lifecycle README and ADR-049's Rationale say so ("Settled positions this reopens").
- **Every record is read before propagation.** A capability whose record is missing falls back, as today, to its installed `package.yaml`, which the copy has not yet replaced.
- **Current for sync:** the running pkit's version equals `backbone_version`, and `migrated_version` equals it too. Anything else stops sync.
- **Inside a sync that proceeds, each component:**
  - bundled version equal to the recorded one: copied, no migration, no stamp
  - bundled newer: skipped and reported, "pending: run `pkit upgrade`". A capability the last transition held back for a collision names `pkit capabilities upgrade <name> --interactive` instead, which sync can tell with `capabilities.detect_upgrade_collisions`.
  - bundled older: skipped and reported, with no override (today's #524 guard, without `--force`)
  - not in the bundle: the orphan warning, as today
  - incubated: skipped, with the collision report of COR-031, as today
  - externally-sourced: brought to its pin, once its fetch is built (COR-041). Until then it is skipped, never read as kit-shipped, which `_sync_installed_capabilities` does today
  - no recorded version at all: skipped and reported
- **Current for upgrade, its early return:** `backbone_version` and `migrated_version` both equal the target, and every registered adapter and kit-shipped capability records its bundled version. Today only the backbone is compared (line 190).
  - **A capability held back** fails the test, so the next upgrade tries it again and reports it again. It writes nothing else.
- **Adapters:** "every adapter" means the registered ones, as COR-010's registry sets.
  - **A registered adapter with no record,** every project's state today, is recorded at its bundled version and runs no migration. No adapter migration has ever run, and the one that exists repeats what merge does.
  - **An adapter a release adds** is registered by the transition that brings it and recorded at its bundled version, as at install.
- **What a version identifies:** content only for a tagged install (question 12).

### How an upgrade records its progress

An upgrade writes the target to `backbone_version` before it writes anything else, and writes `migrated_version` last (question 2).

1. **Compatibility** against the versions each component moves to, holds included ("Holding a capability back").
2. **The target is recorded:** `backbone_version` becomes the target. `migrated_version` keeps its value, or stays missing.
3. **Propagation** at the target, with the ignore file rendered.
4. **Migrations:** the backbone's from `migrated_version` to the target, then each adapter's and each capability's from the record read before propagation. Each component is restamped when its migrations finish.
5. **Merge delivery and derivable state.**
6. **Completion:** `migrated_version` becomes the target.
7. **The pin,** last, as ADR-049 point 1 sets.

- **The transition is complete when the two keys are equal.** A missing `migrated_version` reads as incomplete with no lower bound. No project at the new release's content lacks it: the release's `init` and its upgrades write it.
- **An interrupted upgrade is finished by the next one.** It finds the two keys apart, runs the backbone migrations from `migrated_version`, and each component's from its own record.
- **One completion mark, written last:** sync then never runs over a half-finished transition, a capability half-migrated included. Re-running the backbone window after a late interruption is idempotent and cheap.
- **Why the target is written first:** an older pkit reading an interrupted upgrade.
  - **Written last,** the record would show the older pkit its own version. It would pass #1212's guard and copy its older files over a half-migrated tree.
  - **Written first,** the record shows a newer version. The older pkit refuses (#1212), and its message leads to the newer code.
  - **A marker the older code cannot read** would not stop it. That is why a second recorded state beats an "in progress" marker.
- **The limit:** the protection starts with the release that ships #1212. A project pinned at 1.149.0 or earlier runs code without the guard. If its first upgrade out is interrupted, a `pkit sync` under the old pin copies 1.149.0's files back. The next `pkit upgrade` still recovers it.
- **A `migrated_version` newer than `backbone_version`** is reachable the same way: a release without #1212 syncs over a finished transition. It reads as incomplete, and the next upgrade propagates again and runs migrations from `migrated_version`.
- **No schema bump:** the key is optional, and no JSON schema describes the manifest. `manifest.write_backbone_manifest` has kept keys it does not know since the first published commit, `be3de58b` in v1.134.0, so every release leaves the key in place.
- **`pending_migration_scripts` takes `migrated_version` as its lower bound** for the backbone, in place of `backbone_version`.
- **project-kit's own manifest:** the release step writes both keys (`release._sync_self_host_manifest_backbone`, PRJ-007). The guard and status's "incomplete" line do not apply in the methodology's source, as #1435 exempts it.

### Projects already stranded

A missing `migrated_version` means the project's migration history is unknown. The first upgrade under the new release then runs every backbone migration up to its target, once (question 4).

- **What it leans on is more than idempotence.** A replay also runs scripts on states that never needed them, and on states a project changed after a script ran. COR-010's "already-applied state is a no-op" does not cover those.
- **The contract it needs:** a backbone script acts only on a positive sign that its change is needed, as project-management's `0.55.0/001` and `0.55.0/002` do for files they did not write. It never deletes by name alone.
- **Its test:** fixtures that hold each failure the audit names, not only a fresh install: an overlay category deleted, the `process` block removed with journals on disk, a declared file forced back into git, a hand-written `.claude/agents/orchestrator.md`, a `bindings.yaml` under a capability's `project/`.
- **The audit of today's eight scripts:**
  - **No effect on any state:** `1.32.0/001` retires the bundle pattern, `1.93.0/001` exits when the rules area exists, and `1.140.0/001` only prints guidance.
  - **Deletes by name, so it is rewritten before the replay ships:**
    - `1.31.0/001` deletes anything at `.claude/agents/product-manager.md` or `orchestrator.md`, a project's own agent of that name included.
    - `1.0.0/001` deletes every `schemas/bindings.yaml` four levels below `.pkit/capabilities/`, a capability's `project/` and an incubated capability included.
  - **Can re-add what a project removed later,** a cost the changelog states:
    - `1.54.0/001` appends an overlay category the project deleted after the script ran.
    - `1.150.0/001-keep-process-journal-logging` writes `enabled: true` where the `process` block was removed while old journals stay on disk.
    - `1.150.0/001-untrack-runtime-ignored-files` stages again the untracking of a declared file a project forced back into git.
- **Capabilities are never replayed.** Their record is written at install and restamped after their migrations, so their history is known once the record is kept out of the copy.
- **The dry run lists the replay,** and the changelog says why it runs once.

### On a mismatch

When the running version differs from the project's recorded version, or the last transition is incomplete, sync stops. It writes nothing, exits non-zero, refuses under `--dry-run` too, and takes no override, as #1212's refusal does.

- **The guard is one function,** `sync.refuse_content_downgrade` widened to both directions and to an incomplete transition.
- **Which commands call it:** a command that copies methodology content from the running pkit into the project. That is sync, `capabilities install` and `upgrade` (question 8), and the conversion command (#1435).
  - **Not guarded now:** commands that write a project's own files in the running release's format, such as `pkit new`, `pkit config set`, `pkit agents reconcile --write`, `pkit permissions apply` and `pkit visibility`. Status and validation report the mismatch (#1436). Whether they stop is a follow-up.
- **What the gate compares:** the running version with the recorded content version, and the transition's two keys. As #1212's guard does, it also refuses a pin newer than the running pkit. Beyond that, the pin only chooses the message.

| State | Sync | The message names |
|---|---|---|
| Unpinned, running pkit newer | stops | **Move:** `pkit upgrade`, which pins by default (`--no-pin` to stay unpinned) and on a terminal may first update the tool (`--no-self-update`). **Stay:** `pkit pin`, which pins at the content's version, so the router runs it. **A pipeline:** commit a pin, or install the project's version, `uv tool install --force <url>@v<version>` |
| Pinned, the router fell back to another installed pkit | stops | reconnect and re-run, since the router runs the pin when it can fetch it. `uvx --from <url>@v<pin> project-kit sync`, or `uv tool install --force <url>@v<pin>` where `uvx`, keys or the tag are what fail. To move on purpose, `pkit unpin` and then `pkit upgrade`. Not a bare `pkit upgrade` |
| Pinned, content behind the pin, the pin's code running | stops | `pkit upgrade` (with the routed child's fix below) |
| Transition incomplete | stops | `pkit upgrade` |
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
  - **The distribution URL is `git+ssh`** (`router.DISTRIBUTION_GIT_URL`). A pinned pipeline without SSH keys falls back and meets the stop. Installing the pin's version makes the router run itself, with no fetch.
  - **project-kit's own pipelines are unaffected:** they run self-host sync (`.github/workflows/checks.yml`, `friction-report.yml`).

### Every migration inside the transition, and its order

The transition runs every migration, in COR-010's order. Sync runs none.

1. **Propagation:** the methodology's trees and every kit-shipped component, except one held back. The step renders `.pkit/.gitignore`, as sync does today, so a migration reads a render of the target's declarations.
2. **Backbone migrations,** from `migrated_version`.
3. **Adapter migrations,** each from its record, read from the bundle as capability migrations are, since the project's copy has no `migrations/`.
4. **Capability migrations,** dependencies first by their `requires_capabilities` (COR-030). Today they run in the manifest's order.
5. **Merge delivery, then derivable state,** regenerated again.
6. **Completion,** then the pin.

- **A migration may read the render made after propagation,** as `1.150.0/001-untrack-runtime-ignored-files` does by design. A render only after every migration, as the first architect review placed derivable state, would hand it the previous release's.
- **A capability's files are copied before its migrations,** as COR-010's order sets. Today `refresh_capability` runs them first. The audit of the eleven capability scripts and the adapter's one:
  - **evidence's `0.2.0/001`** removes the old flat skill files ahead of the copy. The copy now removes them first, so the script finds nothing to do.
  - **project-management's `0.15.0/001`, `0.24.0/001` and `0.26.0/001`** read the shipped `schemas/workflow.yaml` and expect its `schema_version` to be theirs. Run before the copy, as today, they always find the old file and skip. Run after it, `0.26.0/001` checks real overrides as it was written to, and `0.15.0/001` and `0.24.0/001` warn wrongly on a jump of more than one version. Those two are fixed in the same change.
  - **project-management's `0.54.0/001`** stamps the installed `package.yaml`'s version. After the copy that is the new version, which its comment intends: "a grandfathered stamp does not immediately read as stale".
  - **The rest** handle either order: `0.12.0/001` and `0.55.0/001` say so, and the others read project-owned files or fixed checksums. The adapter's script edits only `CLAUDE.md`.
- **`pkit capabilities upgrade <name>`** becomes a transition of one component: copy, migrate, stamp.
- **The dependency check reads the versions the transition installs,** not the installed ones (`upgrade._check_capability_dep_conflicts_for_upgrade`). #1410 changes this check first.

### Holding a capability back

COR-017 says sync refuses the upgrade of a capability that would bring a new collision, and names `pkit capabilities upgrade X --interactive`. Sync's refresh never built that, while `capabilities upgrade` did (`capabilities.detect_upgrade_collisions`). The transition takes it over.

- **The hold is decided before anything is written,** in step 1, and reported with the interactive upgrade it needs.
- **A held-back capability keeps its files and its installed range.** So the transition then judges the set it would leave, as `capabilities upgrade` judges one capability:
  - the held-back capability's installed `requires_backbone` must admit the target
  - COR-030's ranges, between it and the capabilities that move
  - COR-053 point 6's mandatory connections. The lifecycle README skips them for the backbone-wide upgrade, since "it moves every kit-shipped capability at once", which a hold makes untrue.
  - **A conflict in any of them refuses the whole transition,** naming the interactive upgrade first.

### Capability install, capability upgrade, and other sources

- **`pkit capabilities install` and `upgrade` call sync's guard** (question 8). Every kit-shipped file a project holds then comes from the release its backbone records, except a capability a transition held back.
- **`pkit capabilities register`** copies nothing, so it needs no guard.
- **An externally-sourced capability** already follows the principle: sync brings its copy to its pin, and an upgrade repoints the pin (COR-041). When sync stops, nothing is fetched.

### `sync --force` and dry runs

- **`--force`'s only effect, copying an older capability over a newer one, moves a version down.** Sync stops doing it (question 14).
- **Dry runs:** sync's stop refuses under `--dry-run`, as #1212's does. Upgrade's dry run lists the target, the replay where the key is missing, each component's migrations, and what it would hold back.

### Messages and status

- **Status** shows an incomplete transition and each component a transition would move or held back, beside the backbone line it has (`status._report_backbone_version`). #1436 and #1440 extend status too.
- **The CLI reference's upgrade entry** says migrations run "then runs `sync`". The code runs sync first. The rewrite follows the design.

### The records it changes

- **A new core record,** "A project stays at its version until an upgrade moves it" (title provisional):
  - a project records a version for its backbone and for each component it installs
  - reconciliation runs at the recorded versions, moves none, and runs no migration
  - a version transition is the only operation that moves a recorded version, and every migration runs inside it
  - one consent covers a transition's parts, since every part follows from the target the person chose
  - a transition records its target before it writes anything and its completion last, and the next transition finishes an incomplete one
  - a transition moves every kit-shipped component, except one it holds back for a reason it reports
  - a command that copies methodology content under another version than the project records stops and names the remedy, and read-only commands still run
  - it cites COR-041 as precedent and uses core terms only
  - it partially supersedes COR-017's sync paragraph and COR-004's anchoring paragraph (questions 1 and 7)
- **COR-001, refined:** sync's writers, merge delivery and a missing seed, and the transition's migrations, as instances of the named-writer principle. If #1432 has not landed, this states the principle.
- **COR-010, refined:** Update runs at the recorded versions. The transition records its target first and its completion last. A capability's record sits at its root, kept out of the copy (question 3).
- **COR-048 point 1,** refined in place: an upgrade does write the configuration file, through the migrations point 5 allows.
- **The realising ADR,** by the architect, once the core record is accepted: the split, the per-component table, the record kept out of the copy, the manifest key and its test, the replay and its test, the hold and its gates, the routed child's order, the fallback refusal, the messages, the migration order, `--force`, and the tagged install.
- **ADR-049, refined in place, not superseded.** Its decision stands: the pin flips last, and no two-phase commit. Its claim of how a re-run recovers was false, and the decisions README fixes a false fact in place. #1433 says "#1429's ADR partially supersedes ADR-049", which then needs rewording.
- **ADR-044:** its D1 and Implications say an offline upgrade goes on to "sync the project from the current bundle". They name the transition.
- **Unchanged:** COR-030, COR-031, COR-041, ADR-033, ADR-039 and ADR-059.

## Questions for the maintainer

One decision each, in order of consequence. A question that depends on another comes after it.

### 1. Is `pkit upgrade` one operation, a version transition?

- **The question:** COR-004 says a command performs one operation, and rejects as a compound "an "update" that does sync + merge + migrations". Should a version transition count as one operation?
- **Example:** `pkit upgrade` from 1.149 to 1.150 copies 1.150's files, runs the migrations, merges the settings and pins the project. None of COR-004's operations names that.
- **Recommended:** yes. A version transition moves a project's recorded versions to a target. Every part follows from the target the person chose, so one consent covers them: the target's content, every pending migration with the writes COR-048 point 5 allows, merge delivery, the recorded versions and the pin.
  - **What it does in each part depends on what it finds,** as sync's copy does. What COR-004 rejects is a verb whose consent depends on what it finds, silent here and asking there.
  - `pkit upgrade`, `pkit capabilities upgrade <name>` and `pkit pin <newer>` anchor to it.
  - The new core record partially supersedes COR-004's anchoring paragraph, whose example names this compound (question 7).
  - The tool's self-update (ADR-044) acts on no project, so it stays outside the operation. The realising ADR names it as a step before the transition.
  - **Its cost:** a foundational record on the command surface is overturned in part, and one command carries several parts.
- **Alternative:** COR-004 stays as it is, and the realising ADR records `pkit upgrade` as a named exception to it.
  - **Its cost:** a core rule with an exception only project-kit's own ADR knows of, so an adopter reading the core records finds a rule the tool breaks.

### 2. How does an upgrade record its progress?

- **The question:** how does the next run know whether the last upgrade finished?
- **Example:** an upgrade from 1.149 to 1.152 is interrupted during its migrations. Today the manifest already says 1.152, so the next `pkit upgrade` finds nothing to do.
- **Recommended:** two recorded states. `backbone_version` moves to the target first, and a new optional `migrated_version` is written last. The transition is complete when they are equal ("How an upgrade records its progress").
  - **Its cost:** a manifest key, a second meaning of `backbone_version` while a transition is incomplete, and a rule that a missing key means incomplete. Pinned releases up to 1.149.0 lack #1212, so they are not stopped either way.
- **Alternative:** write `backbone_version` last, as COR-010's order reads, with an "in progress" marker.
  - **Its cost:** an older pkit cannot read the marker. It sees its own version, passes #1212's guard and copies its files over a half-migrated tree.

### 3. Where does a capability's record live?

- **The question:** a capability's record, `.pkit/capabilities/<name>/manifest.yaml`, sits where the copy deletes or overwrites it. How is it kept?
- **Example:** after the change, sync copies a capability without restamping it. Its record is deleted, and with it the artefacts the project chose to skip. project-management's record is replaced with project-kit's own.
- **Recommended:** keep the record where it is and out of the copy. The copy's ownership test protects it, the bundle withholds it, and the transition restamps it after the capability's migrations. COR-010's Implications are refined to say where it sits.
  - **Its cost:** an accepted sentence on where component manifests live is refined, and adapters and capabilities keep their records in different places.
- **Alternative:** move the record under the capability's `project/`, beside where an adapter's lives.
  - **Its cost:** a file moved in every adopter's tree, so a migration, plus every reader and both ownership predicates changed.

### 4. How do projects already stranded recover?

- **The question:** what does the first upgrade under the new release do for a project with no `migrated_version`?
- **Example:** an unpinned project at 1.53 synced by a 1.60 pkit records 1.60 without `1.54.0/001`. Its overlay lacks the architect's categories, and every later upgrade starts from 1.60.
- **Recommended:** a missing key means unknown, and the first upgrade runs every backbone migration up to its target, once. Each script first meets a stronger contract: it acts only on a positive sign that its change is needed ("Projects already stranded").
  - Two scripts that delete by name are rewritten before the replay ships, and fixtures hold each failure the audit names.
  - **Its cost:** every adopter's first upgrade runs eight scripts. Three of them can re-add what a project removed after they ran. Every future backbone script carries the stronger contract.
- **Alternative:** a missing key means complete. A stranded project recovers by a command that runs the backbone migrations from a version its operator names, which the changelog explains.
  - **Its cost:** a project stays stranded unless its operator learns it. Each script can tell its own state from the files, but nothing tells the operator which scripts to run.

### 5. Does merge stay in sync?

- **The question:** should sync keep running the merge primitives, which write `.claude/settings.json` and `CLAUDE.md`?
- **Example:** a project adds an allow entry to its settings additions, or writes a skill under `.pkit/skills/project/`, and runs `pkit sync`. Merge puts the entry, or the skill's `Skill(<name>)` grant, into `.claude/settings.json`.
- **Recommended:** merge stays in sync, in its auto-add tier, the only tier it has built. It is merge delivery (COR-002), a writer the named-writer principle names, and it regenerates what COR-010 calls derivable.
  - COR-004's "`sync` and `merge` stay separate" is refined: sync runs merge's auto-add tier, and a prompting tier runs only where a person can answer.
  - **Its cost:** sync writes two project-owned files, so the decision's "writes no project-owned path" is false for them, and COR-001 and COR-004 change.
- **Alternative:** merge leaves sync, and runs at init, in a transition, at a capability's install or upgrade, and on `pkit merge`.
  - **Its cost:** every edit to a project's settings additions and every new project skill needs `pkit merge`, against core rule 6's workflow and the adapter's README. project-kit's maintainers need it for every new core skill.

### 6. Does sync create a missing seed path?

- **The question:** after install, may sync write a seed path the project does not have?
- **Example:** delete `.pkit/agents/project/overlay.yaml` and run `pkit sync`, and the seed comes back. COR-001 says a seeded path is written once, at first install, and "Subsequent syncs do not touch this path".
- **Recommended:** yes. The propagation step, in sync and in the transition, creates a declared seed path that is missing and never writes over one that exists. COR-001's seeding cadence is refined to say so.
  - It is how a seed a release adds to an existing area reaches a project.
  - **Its cost:** COR-001's seeding sentences change, and a seed the project deleted on purpose returns on every sync.
- **Alternative:** a seed is written only when the area or component that declares it first enters the project. A deleted seed stays deleted, and a command that needs it names its repair, as `pkit agents reconcile --write` writes a missing overlay.
  - **Its cost:** sync repairs no deleted seed. A seed a release adds to an existing area ships as a migration, and the transition must tell an area new to the project from a deleted seed.

### 7. Where does the principle live?

- **The question:** COR-017 says "Sync auto-upgrades installed capabilities", and COR-004 names this compound as one to reject. The design overturns both sentences, and the decisions README says an overturned decision is superseded by a new record. Which record carries the principle?
- **Example:** after the change, a reader of COR-017 learns that sync no longer moves a capability, and where the rule went.
- **Recommended:** a new core record carries the principle ("The records it changes"). It partially supersedes COR-017's sync paragraph and COR-004's anchoring paragraph. COR-001, COR-010 and COR-048 point 1 are refined and point to it.
  - **Its cost:** one more core record, and edits to four foundational ones.
- **Alternative:** COR-010 carries the principle as a refinement. A short new record only supersedes COR-017's and COR-004's sentences.
  - **Its cost:** one principle split across two records, and COR-010's refinement grows past the lifecycle's operations.

### 8. Do `pkit capabilities install` and `upgrade` stop on a version mismatch?

- **The question:** should the two commands call sync's guard?
- **Example:** an unpinned project at 1.149 with a 1.152 pkit runs `pkit capabilities install living-docs`. It gets 1.152's living-docs beside 1.149's backbone, a mix no release shipped.
- **Recommended:** yes, with sync's remedies. Every kit-shipped file a project holds then comes from one release, except a capability a transition held back.
  - **Its cost:** someone with a newer pkit pins or upgrades before installing a capability, and on a floating install meets it at every release.
- **Alternative:** they keep copying from the running pkit, checked only by `requires_backbone`.
  - **Its cost:** mixes no test covers, and a capability whose migrations assume a backbone the project never moved to.

### 9. Does the next release ship a stop-gap?

- **The question:** the next release ships two backbone migrations in `1.150.0/`. Should it also stop sync from stranding them, before the rest of this build lands?
- **Example:** an unpinned project at 1.149 runs `pkit sync` with the next release's pkit. Its manifest records the new version, `keep-process-journal-logging` never runs, and the project's journal logging stops without a word. Its next `pkit upgrade` finds nothing to do.
- **Recommended:** yes. One small change, ahead of the release: sync refuses to move `backbone_version` past a version directory that holds backbone migrations, and names `pkit upgrade`. The changelog says to run `pkit upgrade` for this release.
  - **Its cost:** an issue outside this design's slicing, and a refusal the full guard later replaces.
- **Alternative:** the changelog alone tells adopters to run `pkit upgrade` and not `pkit sync`.
  - **Its cost:** a project that syncs anyway loses its migrations until this build's replay recovers it.

### 10. Where does this build fall against the conversion build?

- **The question:** #1429's build comes after #1410 and before #1444. Does it also come before #1435 to #1442?
- **Example:** #1435 adds the newer direction to sync's guard if this build has not yet, and #1438 and #1440 edit upgrade's messages and status, which this build also edits.
- **Recommended:** before #1435. The conversion command, its status and its reports then build on settled sync and upgrade, and each pair's later issue depends on the earlier.
  - Each slice leaves adopters safe if a release is cut after it ("Slicing").
  - **Its cost:** the conversion build waits for this one.
- **Alternative:** the conversion build first, up to #1442, then this build, then #1444.
  - **Its cost:** #1435 builds the guard's newer direction itself, and three pairs of issues edit the same code twice.

### 11. Which changeset segment?

- **The question:** a minor or a major backbone changeset for the sync change?
- **Example:** an unpinned project's pipeline runs `pkit sync` with the latest pkit. It passes today and fails after the change.
- **Recommended:** minor, with a changelog entry under "Changed" that names the pipeline impact and the recipe: commit a pin, or install the project's version in the pipeline.
  - Projects upgraded since 1.145.0 are pinned by default, and see no change while their pin can be fetched.
  - **Its cost:** a command that worked fails, under a minor number.
- **Alternative:** major, since a working command now fails and COR-017's contract inverts.
  - **Its cost:** a major number for a change most adopters do not see.

### 12. What does a version name for an untagged install?

- **The question:** how is sync's check made honest when the running pkit was installed from no tag?
- **Example:** main's head carries the `1.150.0/` backbone scripts while its `VERSION` reads 1.149.0. A project upgraded with it gets 1.150-era files, and its migrations stop at 1.149.0, so `migrated_version` reads 1.149.0 over files that need the 1.150 scripts.
- **Recommended:** the realising ADR states that a version identifies content only for a tagged install. The recommended install becomes tagged: init prints `@v<its own version>`, the CLI reference follows, and #1376's test keeps the two equal.
  - **Its cost:** the printed command names a version that ages, and an untagged install stays possible and unchecked.
- **Alternative:** an untagged build stamps a development version, such as `1.149.0+g<sha>`, so it never equals a project's recorded version.
  - **Its cost:** every untagged install meets the stop in every project, and the router reads such a version as unordered.

### 13. Does sync only stop on a mismatch, or also offer a deploy-only mode?

- **The question:** should a stopped sync have a mode that still deploys from the project's own files?
- **Example:** a fresh offline clone of a project pinned at 1.150, on a machine whose pkit is 1.152. The router cannot fetch 1.150 and runs 1.152, and sync stops.
- **Recommended:** stop only, for now. In the default shared visibility the deployed harness and `.pkit/.gitignore` are committed (ADR-009), and provisioning needs the network anyway. An older installed pkit meets the same stop today (#1212). `--deploy-only` waits for a case that asks for it (COR-007).
  - **Its cost:** such a clone gets no agent workspace and no exclude line until it can run its pin.
- **Alternative:** `pkit sync --deploy-only` runs the self-host branch's steps on any project: the project's own deploy primitives, the ignore render, the workspace and provisioning. It copies and records nothing.
  - **Its cost:** a third mode of sync now, and one release's Python steps run over another release's tree.

### 14. What happens to `pkit sync --force`?

- **The question:** how is `--force` retired?
- **Example:** today `--force` lets sync copy an older capability over a newer installed one, which moves its version down.
- **Recommended:** sync accepts `--force` for one release, ignores it and says so. A later change removes it with a guidance migration, as `1.140.0/001` did for the router shim.
  - **Its cost:** one release of a flag that does nothing.
- **Alternative:** remove it now.
  - **Its cost:** a pipeline that passes `--force` fails at once.

## Settled positions this reopens

Each accepted sentence below changes, for the maintainer's authorisation. Items 7 to 9 change under the recommended answers to questions 5, 6 and 3, and stay under their alternatives.

1. **COR-017, "Lifecycle: install, sync, uninstall":** "**Sync** (`pkit sync`) auto-upgrades installed capabilities along with the rest of kit content." and "When sync would introduce a new collision [...], sync refuses to upgrade that specific capability and instructs the adopter to run `pkit capabilities upgrade X --interactive` to resolve."
   - **The change:** partially superseded. A version transition moves the capabilities, and a new collision holds a capability back there. Sync keeps a capability at its recorded version.
   - **With it:** the section's "Capabilities have an explicit install / sync / uninstall lifecycle", and the implication "**Sync extension** — refreshes installed capabilities; surfaces no-longer-shipped capabilities; refuses upgrade on new collisions."
2. **COR-004, "Each command anchors to one mechanism or operation":** "A command performs one of: propagation, seed, merge, suspension management, validation, or read-only introspection. It does not compound two of these into one verb. Compound verbs (e.g., an "update" that does sync + merge + migrations) hide which contract is being invoked, conflate consent profiles, and resist the manifest-level reasoning the install/sync runtime needs." Also its rejected alternative, "One smart `update` verb that picks sync / merge / migration as needed."
   - **The change:** partially superseded (question 1). The list gains the version transition, one operation under one consent. What stays rejected is a verb whose consent depends on what it finds.
3. **COR-004, "Failure mode is forward-only":** "A failed run leaves the project at a known partial state, with `validate` as the recovery entry point." Also "`init` is one-shot": "Recovery from partial or broken state flows through `validate` plus targeted `sync` / `merge` instead."
   - **The change:** refined. An interrupted transition is finished by the next one, and sync names it.
4. **COR-010, "Lifecycle operations apply uniformly", item 3:** "**Update** — re-running the setup primitive reconciles installed state with the current version's spec."
   - **The change:** refined. The setup primitive runs at the recorded versions. It moves no recorded version and runs no migration.
5. **COR-010, "Cross-tier upgrade requires explicit compatibility resolution":** "The reconciliation order — compatibility resolution → propagation → backbone migrations → component migrations → derivable-state reconciliation → recorded-version updates".
   - **The change:** refined. A transition records its target before it writes anything and its completion last, and the next transition finishes an incomplete one.
6. **COR-010, "Two tiers":** independent versioning "lets adopters upgrade selectively".
   - **The change:** refined. A transition moves every kit-shipped component its release ships, except one it holds back. Selective movement remains for a held-back capability and an externally-sourced one.
7. **COR-004, "`sync` and `merge` stay separate":** "Folding them into one verb either leaks the silent-overwrite contract onto project-owned files or makes routine refresh interactive."
   - **The change, under question 5's recommendation:** refined. Sync runs merge's auto-add tier, which writes nothing silently over a project's content, and a prompting tier runs only where a person can answer.
8. **COR-001, "Extension":** "project-owned paths are not touched by sync", and "Install-time seeding": "written exactly once, at first install. Subsequent syncs do not touch this path." Also "Seeded extension artifacts are project-owned after first install. Core makes no further claim on them."
   - **The change, under questions 5 and 6:** refined. Sync touches project-owned paths only through merge delivery and by creating a missing seed. #1432's named-writer principle carries the rest of COR-001's change.
9. **COR-010, Implications:** "**Per-component manifests live with their component's project-side directory.**"
   - **The change, under question 3:** refined. A capability's record sits at its root, kept out of the copy.
10. **COR-048 point 1:** "It survives upgrade, sync, and uninstalling any capability or the tool itself, because none of them writes or removes it."
    - **The change:** refined in place. None of them removes it, and an upgrade writes it only through the migrations point 5 names. Sync no longer writes it at all.
11. **ADR-049 point 1:** "the recovery is to **re-run** the reconcile / `upgrade`, which is idempotent (sync re-applies content, migrations detect already-applied state and no-op per COR-010, and the pin flip is a no-op once it matches)". Also its Implications on upgrade, "a mid-migration interruption is recovered by an idempotent re-run", and "A raise runs the *target* version's sync".
    - **The change:** refined in place. A re-run finishes the transition the manifest shows incomplete. The pin still flips last, with no two-phase commit.
12. **ADR-049, Rationale:** "`backbone_version` is a **record** (a receipt of the last sync)". Also point 3: `pkit pin` with no argument "freezes the project at its current content version (`manifest.yaml`'s `backbone_version`)".
    - **The change:** refined in place. `backbone_version` is the receipt of the last transition's target, and while a transition is incomplete it is ahead of the files. A pin frozen then names the target, whose code finishes the transition.
13. **ADR-049's amendment:** "an **unresolvable pin degrades loudly to running self**, never a hard fail — so a pinned project never bricks offline".
    - **The change:** refined by #1401's fold of the amendment, or by the ADR after it. The router still degrades, and sync and upgrade refuse to write under the pkit it degrades to, in both directions.
14. **ADR-044 D1:** an unreachable release source "degrades loudly and continues with today's behaviour — sync the project from the current bundle".
    - **The change:** wording only. It continues with the transition to the current bundle's version. Its Implications and its amendment say the same.
15. **The decisions README, "The no-shared-files invariant":** "project-owned paths are never read or written by sync."
    - **The change:** sync writes them only through merge delivery and a missing seed. It reads the manifest. #1432 may make part of the same change first.

## Corrections to the first reviews

The critic and the architect reviewed the bare direction on 10 October. Where this design's reading of the code differs:

- **The adapters' recovery:** the architect expected adapters to recover by a per-component check. No adapter has a record to check, and no adapter migration has ever run ("Where migrations strand").
- **Older code:** the architect's case for writing the target first rests on #1212's guard. It holds only from the release that ships #1212, since no released pkit has it.
- **A missing key:** the architect read a missing `migrated_version` as equal for sync. It reads as incomplete here. No project at the new release's content lacks it, and "equal" would let sync run over an interrupted first upgrade.
- **The replay:** both reviews rest it on idempotence. A replay also runs scripts on states that never needed them, so it needs a stronger contract. The audit found two scripts that delete a project's files by name, and three that can re-add a project's removals.
- **ADR-049:** the architect proposed partial supersession. Point 1's decision stands and only a fact was false, so the decisions README calls for a refinement in place. Its amendment is #1401's.
- **The migration order:** the architect put derivable state after every migration. `1.150.0/001-untrack-runtime-ignored-files` reads the render made after propagation, so the render comes then and again at the end.
- **Merge and seeds:** both reviews and this note's first draft took merge out of sync. Merge reads the project's own settings additions and skills, so taking it out breaks a working workflow. Question 5 now recommends keeping it.
- **Collision refusal:** the first critic found it unbuilt. It is unbuilt in sync's refresh only. `pkit capabilities upgrade` has it.
- **The scripts:** seven backbone version directories hold eight scripts.

## Alternatives weighed

- **Sync runs at the recorded version by fetching it** (`run_bypassed` from sync). Not taken: a fetch at sync time is what ADR-033 rejected, the pin already routes every command, and offline it still stops.
- **Sync moves content but records no version.** Not taken: it breaks ADR-033's tie of content to code, and a capability's files would move without their migrations.
- **Skip per component without the backbone stop.** Taken inside a sync that proceeds. Without the backbone stop, a newer pkit would still copy its backbone files over older ones.
- **A ledger of migrations that ran.** Not taken: it drifts from the files and conflicts across branches, and COR-010 keys migrations on versions.
- **`migrated_version` written right after the backbone migrations,** with completion read from every component's record too. Not taken: sync could then run over a capability whose files moved and whose migrations had not, and re-running the backbone window is cheap.
- **A curated replay,** only the scripts each declares safe. Not taken now: with two scripts rewritten, all eight meet the contract, and a declaration format would carry one bit no script needs.
- **The transition names `pkit merge` and does not run it.** Not taken: new safety entries and baselines would arrive only when someone runs it.
- **Pin at `pkit init`.** Not proposed: it reopens ADR-049 point 2 and puts every new project on the router's `uvx` path from its first command. It would make the unpinned stop rarer.
- **The deploy-only mode by default on a mismatch.** Not taken: a zero exit would let a pipeline hide the skew the stop exists to show.

## Slicing

A draft of the build issues, for filing after the maintainer decides. Each record is accepted before the work that cites it, and each slice leaves adopters safe if a release is cut after it.

- **B0, [Task] the stop-gap, for the next release** (question 9): sync refuses to move `backbone_version` past a version directory holding backbone migrations, naming `pkit upgrade`. Needs no record, since it extends #1212's guard on its own grounds.
- **R1, [Docs] the core record and the refinements:** the new core record through the decision-author skill, partially superseding COR-017's sync paragraph and COR-004's anchoring paragraph. COR-001, COR-010 and COR-048 point 1 refined, and the decisions README's line. A `none` changeset, as #1431's.
  - **Shared with #1431 and #1432:** whichever lands first carries COR-001's principle and the change to COR-004's list, and the other adds its instance.
- **R2, [Docs] the realising ADR, by the architect:** with ADR-049 refined in place and ADR-044's wording. No changeset.
  - **After #1401,** which folds ADR-049's amendment, and in step with #1433, which refines ADR-049's rollback and whose text names a supersession this design does not make.
- **B1, [Task] a capability's record kept out of the copy:** the copy's ownership test and the bundle's withholding, and every record read before propagation. Behaviour-preserving today, and needed by every slice after it.
- **B2, [Task] an upgrade records its target first and its completion last:**
  - the manifest key, written by init and by the release step in project-kit's own manifest
  - the early return keyed on every recorded version
  - the backbone window from `migrated_version`
  - a missing manifest or a broken version seeded by upgrade, and the messages that named sync
  - the replay for a missing key, with `1.31.0/001` and `1.0.0/001` rewritten first, the contract, and the fixtures
  - status showing an incomplete transition. **Names #1436 and #1440,** which extend status too
  - **Safe alone:** a sync under this code still moves `backbone_version` and leaves `migrated_version`, so the next upgrade finds them apart and finishes the migrations
  - **Docs:** the lifecycle README's manifest format and upgrade flow
- **B3, [Task] sync never moves a version:**
  - the propagation step split from the sync command
  - the guard in both directions and on an incomplete transition, refusing under `--dry-run`, with a message per state
  - a capability copied at its recorded version only, others skipped and reported, an externally-sourced one skipped by origin
  - no manifest write and no migration in sync
  - upgrade calls the step and runs each capability's migrations itself
  - `--force` accepted and ignored for one release
  - **Names #1435:** the shared guard. Whichever lands second depends on the first.
  - **Docs:** the CLI reference's `sync`, `init` recovery and `pin` entries, and the lifecycle README's "No path down". The changeset segment is question 11's.
- **B4, [Task] every migration in COR-010's order:**
  - copy, backbone, adapters, capabilities in dependency order, then merge and derivable state, with the render after propagation
  - adapter migrations from the bundle, adapter records written, a release's new adapter registered. `install._install_adapter`'s copy set reviewed, `permission-enforcement.yaml` included
  - project-management's `0.15.0/001` and `0.24.0/001` fixed for the new order
  - `pkit capabilities upgrade` as a transition of one component
  - the dependency check on the versions installed, after #1410
  - the hold and its gates
  - **Docs:** the lifecycle README's upgrade flow and per-component upgrade
- **B5, [Task] the pinned flows:** the routed child finishes its own pin, offline included, and upgrade refuses under the router's fallback. **Names #1438,** which rewrites upgrade's and sync's messages too.
- **B6, [Task] capability install and upgrade use sync's guard,** if question 8 is answered yes.
- **B7, [Task] the recommended install is tagged,** as question 12 decides.
- **Later:** `--force` removed with a guidance migration, a release after B3.

**Order:** B0 in the next release. Then #1410, R1, R2, B1 to B7, and then, under question 10's recommendation, the conversion build from #1435 to #1444. B1 comes before B2 and B3, since both read a capability's record.

## Found on the way

1. **Adapter migrations have never run in an adopter.** `install._install_adapter` copies no `migrations/`, and no code writes an adapter's per-component manifest. Taken by B4.
2. **`install._install_adapter` never copies `permission-enforcement.yaml` either.** `permissions.py` reads it from the project, so in an adopter the line naming dimensions no native layer enforces is always empty. Taken by B4.
3. **A capability's record is deleted or overwritten by every refresh,** and project-management's bundle ships project-kit's own. The restamp hides it today. Taken by B1.
4. **The next release ships two `1.150.0/` migrations, and a sync strands them** for an unpinned project. The journal one matters: logging stops silently. Question 9.
5. **#1212 is unreleased.** Every released pkit writes its older content over a newer project. The protection this design leans on starts with the next release.
6. **Upgrade under the router's fallback raises the pin to the installed version,** not to the latest release ADR-049 point 3 names. Taken by B5.
7. **A pinned project whose installed pkit equals its pin** runs `pkit upgrade` as itself, not as the routed child. Without a terminal it reports "Already at backbone" and does not advance, while ADR-049 point 5 says a pinned upgrade advances with no `uv` step.
8. **COR-048 point 1 says an upgrade never writes the configuration file.** Point 5 lets an upgrade migration write it, and `1.150.0/001-keep-process-journal-logging` and project-management's `0.55.0/004` do.
9. **COR-010's Context says COR-004 "names the upgrade command".** COR-004 names no upgrade.
10. **The CLI reference contradicts the code and itself:**
    - its `upgrade` entry says migrations run "then runs `sync`", while the code runs sync first
    - it says an unpinned upgrade writes "no pin file", while upgrade pins by default
    - its `sync` entry says sync does not invoke merge, while the claude-code adapter's README and the code say it does
11. **`_sync_installed_capabilities` treats an externally-sourced registration as kit-shipped.** It refreshes it from the bundle when the methodology ships a capability of that name, and reports it orphaned otherwise. Taken by B3.
12. **A capability refresh with no readable version runs every shipped migration,** when both its record and its installed `package.yaml` fail to read. project-management's `0.54.0/001` is among them, which grandfathers a bootstrap that may never have happened. B3 ends it in sync.
13. **The lifecycle README says "a corrupt `backbone_version` is one sync repairs".** Sync repairs it by recording the running pkit's version, whatever the files hold.
14. **Read-only commands under another release stay silent.** `pkit validate` with a newer pkit judges older content by newer rules. #1436 reports that mismatch in status and validation.
15. **Commands that write a project's files in the running release's format** (`pkit new`, `pkit config set`, `pkit agents reconcile --write`, `pkit permissions apply`, `pkit visibility`) are not guarded. A follow-up decides whether they stop.
16. **Stale texts the build rewrites:** `1.54.0/001`'s skip text, "install/sync seeds a complete one", and `1.150.0/001-untrack-runtime-ignored-files`'s header, which reasons from "sync has already recorded the new version".

## Review

### The critic, round 1

The critic found the design sound: the split, the target written first, and a remedy per state. Its three red flags were the capability's record lost to the copy, a false premise in the merge question, and deleting scripts the replay audit missed. Each finding below is answered, numbered as the critic numbered them.

**Red flags:**

1. **The copy deletes or overwrites a capability's record.** **Answer:** accepted, verified in `treecopy.refresh_owned_tree` and project-management's shipped `manifest.yaml`. New section "A capability's record sits inside the tree the copy refreshes", question 3, slice B1, and every record read before propagation.
2. **Question 5's premise was false:** merge reads the project's settings additions, project skills and capability overlays. **Answer:** accepted. The recommendation flips: merge stays in sync in its auto-add tier, as a named writer. The self-host contradiction goes with it.
3. **The replay audit missed two deleting scripts, and a fresh-install test catches none of the risks.** **Answer:** accepted. `1.31.0/001` and `1.0.0/001` are rewritten before the replay ships, the contract becomes "act only on a positive sign", and fixtures hold each failure.

**Factual errors:**

4. **The fallback upgrade takes "the path that is not the routed child", not the unpinned path.** **Answer:** fixed.
5. **The capability record's row said "the project's".** **Answer:** fixed: the project's record, in a position the copy manages.
6. **The capability-order audit was wrong for four scripts.** **Answer:** accepted. The audit now names the three workflow scripts and `0.54.0/001`, and B4 fixes `0.15.0/001` and `0.24.0/001`.
7. **Found 3 overstated the `1.150.0/` interference:** keep-journal removes the journal line itself. **Answer:** accepted. The item is gone. The order still renders after propagation, since untrack reads that render.
8. **Found 12 needs both the record and `package.yaml` unreadable.** **Answer:** fixed.
9. **Question 10's cost:** `.pkit/.gitignore` is committed in shared mode. **Answer:** fixed, now question 13.
10. **ADR-049 point 5 governs the routed child, not the fallback.** **Answer:** accepted. The refusal now rests on point 3, the raise to the latest release, and on #1212's precedent.
11. **The gate also reads the pin in the older direction.** **Answer:** fixed in "On a mismatch".
12. **The build order contradicted itself.** **Answer:** accepted. The relative order against #1435 to #1442 is now question 10.

**Gaps:**

13. **Holding back was not traced against neighbours.** **Answer:** accepted. New section "Holding a capability back": range, COR-030, mandatory connections, and sync's message for a held-back capability.
14. **The missing-record rules differed by layer, and new adapters and new seeds were undefined.** **Answer:** accepted. "Every adapter" means the registered ones. A missing adapter record is written at the bundled version with no migration, and a release's new adapter is registered by its transition. A new seed in an existing area reaches projects through seed creation (question 6).
15. **The set of guarded commands was open-ended.** **Answer:** accepted. A criterion: commands that copy methodology content. The rest are named as a follow-up (Found 15).
16. **project-kit's own manifest would read incomplete for ever.** **Answer:** accepted. The release step writes both keys, and the source is exempt, as #1435 exempts it.
17. **Merge's tier inside the transition was unstated.** **Answer:** accepted. The auto-add tier, and a prompting tier only where a person can answer.
18. **The fallback refusal reopens the amendment's "never bricks offline", and the remedies were thin.** **Answer:** accepted. Settled position 13, the reason ADR-039 D2 is unchanged, and two more remedies in the table.
19. **Writing the target first changes what `backbone_version` means.** **Answer:** accepted. Stated in the versions section, and settled position 12.
20. **Question 9 missed the concrete hazard of untagged installs.** **Answer:** accepted. Question 12's example is now the `1.150.0/` scripts under a `VERSION` of 1.149.0.
21. **Found 2 and Found 11 were assigned to no slice.** **Answer:** fixed: B4 and B3.
22. **A test in new code cannot hold what released code does, and `migrated_version` can be newer than `backbone_version`.** **Answer:** accepted. The writer's behaviour is traced to the first published commit, and the newer-key case is stated.
23. **The list of messages to change was incomplete.** **Answer:** accepted. The CLI reference's `pin` and `init` lines are in B3, and the two scripts' texts in Found 16.
24. **The stop recurs at every release for a floating install.** **Answer:** accepted. Stated in "On a mismatch" and in question 8's cost.

**Weak reasoning:**

25. **COR-004 should be partially superseded, not refined, and #1394's Decision 2 rationale was not reconciled.** **Answer:** accepted for COR-004: settled position 2 and question 7. #1394's decision stands. Its phrase that upgrade overwrites "what the methodology owns" understates the migrations, whose writes #1431 limits to carry-overs their owning record names, with running the upgrade as the consent (COR-048 point 5).
26. **The reworded COR-004 alternative would reject the transition itself.** **Answer:** accepted. What stays rejected is a verb whose consent depends on what it finds, not one whose actions do.
27. **"Sync writes no project-owned path" rested on an unstated classification.** **Answer:** accepted. "What sync writes" states three kinds once. `.pkit/.gitignore` is described as rendered per project and never shipped, which is how `ownership.py` lists it.
28. **Question 3's alternative was weaker than it need be.** **Answer:** accepted. The alternative's cost now says each script can tell its own state, but nothing tells the operator which to run.

**Counter-alternatives:**

29. **A curated replay.** **Answer:** weighed, not taken now ("Alternatives weighed").
30. **`migrated_version` written right after the backbone migrations.** **Answer:** weighed, not taken.
31. **Key the fallback refusal on `PKIT_PIN_UNRESOLVED`.** **Answer:** taken, with the bypass check.
32. **The transition names `pkit merge` instead of running it.** **Answer:** weighed, not taken. Its stronger form, merge kept in sync, is now question 5's recommendation.
33. **A stop-gap in the next release.** **Answer:** taken as question 9 and slice B0.
34. **A development version for untagged builds.** **Answer:** taken as question 12's alternative.

**The questions:**

35. **The order was wrong.** **Answer:** accepted. Merge and seeds now come before the placement question, which depends on them. The first question does not depend on them, since merge runs in a transition under either answer.
36. **Question 1's alternative was a straw man.** **Answer:** accepted. The alternative is now COR-004 unchanged, with a named exception in the realising ADR.
37. **Questions 3 and 5 presented false costs.** **Answer:** accepted, corrected with findings 2 and 3.
38. **Missing questions:** build order, the record's home, the fallback against "never bricks", one release for B1 to B4, merge's tier. **Answer:** the first two are questions 10 and 3. The fallback is settled position 13. Release safety is answered per slice. Merge's tier is answered in the design.
39. **Question 11 is small enough for the design.** **Answer:** kept as question 14, since it removes a flag.

**Settled positions:**

40. **Positions were missing.** **Answer:** accepted. Added: COR-004's compound sentence and its sync-and-merge paragraph, its recovery sentences, COR-001's seeding cadence, COR-010's manifest location and selective upgrades, ADR-049's Rationale, point 3 and amendment. #1433's text is named in the slicing. The lifecycle README's sentence is a document, rewritten by B4.

**Slicing:**

41. **A release can be cut between the slices.** **Answer:** accepted. Each slice now leaves adopters safe, and B2 says why it is safe alone.
42. **B1 depended on B2.** **Answer:** accepted. The upgrade side, B2, now comes before sync's change, B3.
43. **B1 and B3 inherited finding 1.** **Answer:** accepted. The record's fix is now B1, before both.
44. **The acceptance gate is respected.** **Answer:** noted.

**Where the note is right (45 to 52)** and **categories with nothing to flag:** noted. #1432's named-writer principle now carries merge delivery as sync's writer in question 5.
